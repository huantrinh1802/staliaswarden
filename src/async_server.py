import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Callable
from collections.abc import Coroutine
from urllib.parse import parse_qs, urlparse, unquote

from config import Config

# ---------------------------
# Dataclasses
# ---------------------------


@dataclass
class Request:
    method: str
    path: str
    query: dict[str, str | list[str]]
    headers: dict[str, str]
    body: str | dict[str, Any]
    params: dict[str, str]


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict[str, str] | None = None


class JsonResponse(Response):
    def __init__(self, status: int, data: dict[str, Any], headers: dict[str, str] | None = None):
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/json"
        super().__init__(status, json.dumps(data).encode(), headers)


# ---------------------------
# Router
# ---------------------------

HandlerType = Callable[
    [
        Request,
    ],
    Coroutine[None, None, Response],
]  # async handler returning Response
MiddlewareType = Callable[[Request], Coroutine[None, None, Response | None]]  # may return Response to short-circuit
ConfigType = dict[str, str]


class Router:
    def __init__(self) -> None:
        # Each route: (pattern, list[middlewares], config, handler)
        self.routes: dict[str, list[tuple[re.Pattern[str], list[MiddlewareType], ConfigType, HandlerType]]] = {"GET": [], "POST": [], "DELETE": []}

    def add(self, method: str, pattern: str, middlewares: list[MiddlewareType] | None, config: ConfigType | None, handler: HandlerType) -> None:
        regex = self._compile_pattern(pattern)
        self.routes[method.upper()].append((regex, middlewares or [], config or {}, handler))

    def _compile_pattern(self, pattern: str) -> re.Pattern[str]:
        pattern = re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", pattern)
        return re.compile(f"^{pattern}$")

    def match(self, method: str, path: str) -> tuple[HandlerType | None, dict[str, str] | None, list[MiddlewareType] | None, ConfigType | None]:
        for regex, middlewares, config, handler in self.routes.get(method.upper(), []):
            m = regex.match(path)
            params: dict[str, str] = {}
            if m:
                for param in m.groupdict().items():
                    params[param[0]] = unquote(param[1])
                return handler, params, middlewares, config
        return None, None, None, None


router = Router()

# ---------------------------
# Middleware (API key)
# ---------------------------


async def api_key_middleware(request: Request) -> Response | None:
    auth_header = request.headers.get("authorization", "")
    key = auth_header.split(" ")[1] if " " in auth_header else ""
    if key != f"Bear {Config.api_token}" and key != Config.api_token:
        return Response(401, b'{"error": "Unauthorized"}', {"Content-Type": "application/json"})
    return None


global_middleware: list[MiddlewareType] = [api_key_middleware]

# ---------------------------
# Decorators for HTTP methods
# ---------------------------


def get(path: str, middlewares: list[MiddlewareType] | None = None, config: ConfigType | None = None):
    def decorator(func: HandlerType) -> HandlerType:
        router.add("GET", path, middlewares, config, func)
        return func

    return decorator


def post(path: str, middlewares: list[MiddlewareType] | None = None, config: ConfigType | None = None):
    def decorator(func: HandlerType) -> HandlerType:
        router.add("POST", path, middlewares, config, func)
        return func

    return decorator


def delete(path: str, middlewares: list[MiddlewareType] | None = None, config: ConfigType | None = None):
    def decorator(func: HandlerType) -> HandlerType:
        router.add("DELETE", path, middlewares, config, func)
        return func

    return decorator


# ---------------------------
# HTTP Response Helpers
# ---------------------------


async def send_response(writer: asyncio.StreamWriter, response: Response) -> None:
    if response.headers is None:
        headers = {}
    else:
        headers = response.headers.copy()
    headers["Content-Length"] = str(len(response.body))

    head = f"HTTP/1.1 {response.status} OK\r\n"
    head += "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    head += "\r\n"

    writer.write(head.encode() + response.body)
    await writer.drain()


# ---------------------------
# HTTP Parsing
# ---------------------------


async def read_http_request(reader: asyncio.StreamReader) -> tuple[str, str, dict[str, str], str | dict[str, Any]] | None:
    request_line = await reader.readline()
    if not request_line:
        return None

    method, target, _ = request_line.decode().rstrip().split()

    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b""):
            break
        k, v = line.decode().split(":", 1)
        headers[k.lower()] = v.strip()

    body: bytes = b""
    if "content-length" in headers:
        length = int(headers["content-length"])
        body = await reader.readexactly(length)
    if "content-type" in headers:
        if headers["content-type"] == "application/json":
            body_output = json.loads(body.decode("utf-8"))
        else:
            body_output = body.decode("utf-8")
    else:
        body_output = body.decode("utf-8")

    return method, target, headers, body_output


# ---------------------------
# Request Handler
# ---------------------------


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    req_data = await read_http_request(reader)
    if not req_data:
        writer.close()
        await writer.wait_closed()
        return

    method, target, headers, body = req_data

    parsed = urlparse(target)
    path = parsed.path
    query: dict[str, str | list[str]] = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}

    handler, params, middlewares, config = router.match(method, path)
    if not handler:
        await send_response(writer, Response(404, b'{"error": "Not Found"}', {"Content-Type": "application/json"}))
        writer.close()
        await writer.wait_closed()
        return

    request = Request(
        method=method,
        path=path,
        query=query,
        headers=headers,
        body=body,
        params=params or {},
    )

    # Global middleware
    for middleware in global_middleware:
        resp = await middleware(request)
        if resp:
            await send_response(writer, resp)
            writer.close()
            await writer.wait_closed()
            return

    # Route-specific middleware
    if middlewares:
        for middleware in middlewares:
            resp = await middleware(request)
            if resp:
                await send_response(writer, resp)
                writer.close()
                await writer.wait_closed()
                return

    response = await handler(request)
    await send_response(writer, response)

    writer.close()
    await writer.wait_closed()
