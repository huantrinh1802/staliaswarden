import asyncio
from typing import cast
from config import Config
from async_server import get, post, delete, Response, Request, handle_client, JsonResponse

from alias import generate_alias
from logger import Logger
from stalwart import add_alias_to_stalwart, delete_aliases_from_stalwart, get_aliases_for

logger = Logger(__name__)


@get("/testing")
async def handle_testing(req: Request):
    return Response(200, b'{"message": "OK"}', {"Content-Type": "application/json"})


@get("/api/v1/aliases/{email}")
async def handle_list_aliases(request: Request) -> Response:
    emails: list[str] = await get_aliases_for(request.params["email"])
    return JsonResponse(200, {"data": emails})


@delete("/api/v1/principal/{user}/aliases/{aliases}")
async def handle_delete_specific_aliases(request: Request) -> Response:
    result = await delete_aliases_from_stalwart(request.params["user"], request.params["aliases"])
    if not result:
        return JsonResponse(500, {"error": "Failed to delete aliases"})
    return JsonResponse(200, {"result": result})


@delete("/api/v1/principal/{user}/aliases")
async def handle_delete_aliases(request: Request) -> Response:
    result = await delete_aliases_from_stalwart(request.params["user"])
    if not result:
        return JsonResponse(500, {"error": "Failed to delete aliases"})
    return JsonResponse(200, {"result": result})


@post("/api/v1/aliases")
async def handle_create_alias(request: Request) -> Response:
    if isinstance(request.body, dict) is False:
        return JsonResponse(500, {"error": "Failed to delete alias"})
    body = cast(dict[str, str], request.body)
    user, root_domain = body["domain"].split("@")
    alias = generate_alias(root_domain)
    added_alias: bool = await add_alias_to_stalwart(user, alias)
    if not added_alias:
        return JsonResponse(500, {"error": "Failed to create alias"})

    now = int(asyncio.get_event_loop().time() * 1000)
    local_part, domain_part = alias.split("@")

    return JsonResponse(
        201,
        {
            "data": {
                "id": now,
                "email": alias,
                "local_part": local_part,
                "domain": domain_part,
                "description": None,
                "enabled": True,
            }
        },
    )


# ---------------------------
# Run Server
# ---------------------------
async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", Config.port)
    logger.info("Async server running", {"port": Config.port})
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
