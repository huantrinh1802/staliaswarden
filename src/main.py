import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio
from typing import Any
from config import Config
from alias import generate_alias
from stalwart import add_alias_to_stalwart
from logger import Logger

logger = Logger(__name__)


# ---------------------------
# Utility helpers
# ---------------------------

def send_json(handler: BaseHTTPRequestHandler, status: int, obj: dict[str, Any]):
    body = json.dumps(obj).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


async def create_alias(domain):
    user, root = domain.split("@")
    logger.info("Creating alias", {"user": user, "domain": root})
    alias = generate_alias(root)
    if not alias:
        return None
    await add_alias_to_stalwart(user, alias)   # must be async-compatible
    return alias


# ---------------------------
# Main Handler
# ---------------------------

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        asyncio.run(self.handle_get())

    def do_POST(self):
        asyncio.run(self.handle_post())

    async def handle_get(self):
        match self.path:
            case "/testing":
                send_json(self, 200, {"message": "OK"})
            case _:
                send_json(self, 404, {"error": "Not Found"})
                return
    async def handle_post(self):
        # ---- Routing ----
        match self.path:
            case "/api/v1/aliases":
                await self.handle_create_alias()
            case _:
                send_json(self, 404, {"error": "Not Found"})
                return
    # ---------------------------
    # Endpoint: POST /api/v1/aliases
    # ---------------------------

    async def handle_create_alias(self):
        # ---- Auth ----
        auth_header = self.headers.get("Authorization", "")
        token = auth_header.split(" ")[1] if " " in auth_header else None

        if not token or token != Config.api_token:
            send_json(self, 401, {"error": "Unauthorized"})
            return

        # ---- Parse JSON body ----
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            send_json(self, 400, {"error": "Invalid JSON"})
            return

        domain = body.get("domain")
        alias = await create_alias(domain)
        if not alias:
            send_json(self, 500, {"error": "Failed to create alias"})
            return

        now = int(asyncio.get_event_loop().time() * 1000)
        local_part, domain_part = alias.split("@")

        send_json(self, 201, {
            "data": {
                "id": now,
                "email": alias,
                "local_part": local_part,
                "domain": domain_part,
                "description": None,
                "enabled": True
            }
        })


# ---------------------------
# Server
# ---------------------------

def run():
    server = HTTPServer(("0.0.0.0", int(Config.port) if Config.port else 8000), Handler)
    logger.info("Alias service running", {"port": Config.port})
    server.serve_forever()


if __name__ == "__main__":
    run()
