import contextlib
import inspect
import json
import logging
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from typing import Any, override

correlation_id: ContextVar[str] = ContextVar("correlation_id")
start_time: ContextVar[datetime] = ContextVar("start_time")
extras: ContextVar[dict[str, Any]] = ContextVar("extras", default={})


class Logger(logging.Logger):
    EXCEPTION_LEVEL: int = 60
    name: str

    def __init__(self, name: str):  # pyright: ignore[reportMissingSuperCall]
        FORMAT = "%(message)s"
        console_handler = logging.StreamHandler()
        file_handler = TimedRotatingFileHandler("sync.log", when="W0")
        logging.basicConfig(format=FORMAT, handlers=[console_handler, file_handler], level=logging.INFO)
        if name:
            self.name = name
            self.logger = logging.getLogger(name)
        else:
            self.logger = logging.getLogger()

    def build_log(self, level: int, message: str, data: dict[str, Any], frame_level: int):
        level_map = {60: "EXCEPTION", 50: "CRITICAL", 40: "ERROR", 30: "WARNING", 20: "INFO", 10: "DEBUG", 0: "NOTSET"}
        aFrame = sys._getframe(frame_level)
        info = inspect.getframeinfo(aFrame)
        log = {
            "level": level_map[level],
        }
        if message:
            log["message"] = message
        log["timestamp"] = datetime.now(timezone.utc).isoformat()
        log["path"] = f"{info.filename}:{info.lineno}"
        if id := correlation_id.get(None):
            log["correlation_id"] = id
        if start_time.get(None):
            log['duration'] = str(datetime.now(timezone.utc) - start_time.get())
        if self.name:
            log["module"] = self.name
        if extras_data := extras.get(None):
            log.update(extras_data)
        if data:
            log.update(data)
        if level > logging.WARNING:
            log.update({"traceback": traceback.format_exc()})
        return log

    def _exception(self, message: str, data: dict[str, Any] | None = None):
        self._log(self.EXCEPTION_LEVEL, message, data)

    @override
    def _log(self, level: int, msg: str, args: dict[str, Any], exc_info=None, extra=None, stack_info=False, stacklevel=2, frame_level=2): # type: ignore # pyright: ignore
        self.logger.log(level, json.dumps(self.build_log(level, msg, args, frame_level), default=str))

    @override
    def info(self, msg, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs['data']
            del kwargs['data']
        elif len(args) > 0 and isinstance(args[0], dict):
            data = args[0]
            args = args[1:]
        else:
            data = {}
        self._log(logging.INFO, msg, data, frame_level=3)

    @override
    def warn(self, msg, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs['data']
            del kwargs['data']
        elif len(args) > 0 and isinstance(args[0], dict):
            data = args[0]
            args = args[1:]
        else:
            data = {}
        self._log(logging.WARNING, msg, data, frame_level=3)

    def warning(self, msg, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs['data']
            del kwargs['data']
        elif len(args) > 0 and isinstance(args[0], dict):
            data = args[0]
            args = args[1:]
        else:
            data = {}
        self._log(logging.WARNING, msg, data, frame_level=3)

    @override
    def error(self, msg, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs['data']
            del kwargs['data']
        elif len(args) > 0 and isinstance(args[0], dict):
            data = args[0]
            args = args[1:]
        else:
            data = {}
        self._log(logging.ERROR, msg, data, frame_level=3)

    @override
    def exception(self, msg, *args, **kwargs):
        if 'data' in kwargs:
            data = kwargs['data']
            del kwargs['data']
        elif len(args) > 0 and isinstance(args[0], dict):
            data = args[0]
            args = args[1:]
        else:
            data = {}
        self._log(self.EXCEPTION_LEVEL, msg, data, frame_level=3)

    def add_extras(self, extras_data):
        return extras.set({**extras.get({}), **extras_data})

    def extract_args(self, func, args, kwargs):
        args_name = inspect.signature(func).parameters.keys()
        return {**dict(zip(args_name, args)), **kwargs}

    def attach_logger(self, attach_correlation_id: bool = True, attached_fields={}, log_endpoint: bool = False):
        def decorator_attach_logger(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                args_dict = self.extract_args(func, args, kwargs)
                local_extras = {}
                if attach_correlation_id:
                    id = correlation_id.set(uuid4())
                if len(attached_fields) > 0:
                    local_extras.update(dict({value: args_dict[field] if args_dict.get(field, None) else (inspect.signature(func).parameters[field].default if inspect.signature(func).parameters[field].default != inspect._empty else None) for field, value in attached_fields.items()}))
                if log_endpoint:
                    pass
                if len(local_extras) > 0:
                    self.add_extras(local_extras)
                result = func(*args, **kwargs)
                if attach_correlation_id:
                    correlation_id.reset(id)
                return result

            return wrapper

        return decorator_attach_logger

    @contextlib.contextmanager
    def logger_context(self, attach_correlation_id: bool = True, extras_data: dict | None = None):
        if attach_correlation_id:
            id = correlation_id.set(str(uuid4()))
        if extras_data:
            extras_token = self.add_extras(extras_data)
        try:
            yield
        finally:
            if attach_correlation_id:
                correlation_id.reset(id)
            if extras_data:
                extras.reset(extras_token)

    def record_time(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            time_token = start_time.set(datetime.now(timezone.utc))
            cur_func = func(*args, **kwargs)
            start_time.reset(time_token)
            return cur_func

        return wrapper

    @contextlib.contextmanager
    def record_time_context(self):
        time_token = start_time.set(datetime.now(timezone.utc))
        yield
        start_time.reset(time_token)

