import http.client
import json
from contextlib import contextmanager

from config import Config
from logger import Logger

logger = Logger(__name__)


url = Config.stalwart_url
if url.startswith("http://"):
    url = url[len("http://") :]
    use_ssl = False
elif url.startswith("https://"):
    url = url[len("https://") :]
    use_ssl = True
else:
    use_ssl = False
# Connect HTTP(S)
if "/" in url:
    host, base_path = url.split("/", 1)
    base_path = "/" + base_path
else:
    host = url
    base_path = ""


@contextmanager
def get_connection():
    conn = http.client.HTTPSConnection(host) if use_ssl else http.client.HTTPConnection(host)
    yield conn
    conn.close()


async def get_aliases_for(email: str, exclude: list[str] = ["trigger"]) -> list[str]:
    user, _ = email.split("@")
    exclude.append(user)
    try:
        with get_connection() as conn:
            conn.request(
                "GET",
                f"{base_path}/principal/{user}",
                headers={
                    "Authorization": Config.stalwart_token,
                    "Content-Type": "application/json",
                },
            )
            response = conn.getresponse()
            response_data = response.read()
    except Exception:
        logger.error("Failed to get aliases from Stalwart")
        return []

    if 200 <= response.status < 300:
        principal = json.loads(response_data.decode("utf-8"))
        emails = [e for e in principal["data"]["emails"] if all([excluded_item not in e for excluded_item in exclude])]
        return emails
    else:
        # Try to decode JSON error if possible
        try:
            err = json.loads(response_data.decode("utf-8"))
        except:
            err = response_data.decode("utf-8", errors="ignore")

        logger.error("Failed to get aliases from Stalwart:", {"error": err})
    return []


async def add_alias_to_stalwart(user: str, alias: str) -> bool:
    path = f"{base_path}/principal/{user}"
    body = json.dumps([{"action": "addItem", "field": "emails", "value": alias}]).encode("utf-8")
    try:
        with get_connection() as conn:
            conn.request(
                "PATCH",
                path,
                body=body,
                headers={
                    "Authorization": Config.stalwart_token,
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                },
            )

            response = conn.getresponse()
            response_data = response.read()

            if 200 <= response.status < 300:
                return True
            else:
                # Try to decode JSON error if possible
                try:
                    err = json.loads(response_data.decode("utf-8"))
                except:
                    err = response_data.decode("utf-8", errors="ignore")

                logger.error("Failed to add alias to Stalwart:", {"error": err})
    except Exception:
        logger.error("Failed to add alias to Stalwart")
    return False


async def delete_aliases_from_stalwart(user: str, aliases_str: str | None = None) -> bool:
    path = f"{base_path}/principal/{user}"
    if aliases_str:
        aliases = aliases_str.split(",")
    else:
        aliases = await get_aliases_for(user)
    body = json.dumps([{"action": "removeItem", "field": "emails", "value": alias} for alias in aliases]).encode("utf-8")
    try:
        with get_connection() as conn:
            conn.request(
                "PATCH",
                path,
                body=body,
                headers={
                    "Authorization": Config.stalwart_token,
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                },
            )

            response = conn.getresponse()
            response_data = response.read()
            if 200 <= response.status < 300:
                logger.info("Aliases removed from Stalwart", {"aliases": aliases})
                return True
            else:
                # Try to decode JSON error if possible
                try:
                    err = json.loads(response_data.decode("utf-8"))
                except:
                    err = response_data.decode("utf-8", errors="ignore")
                logger.error(
                    "Failed to remove aliases from Stalwart:",
                    {"alieas": aliases, "error": err},
                )
    except Exception:
        logger.error("Failed to remove aliases from Stalwart", {"aliases": aliases})
    return False
