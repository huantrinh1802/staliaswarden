import http.client
import json

from config import Config
from logger import Logger

logger = Logger(__name__)


async def add_alias_to_stalwart(user, alias: str):
    # Extract host + path from config.stalwartUrl
    # e.g. "http://localhost:8080/api" → host="localhost:8080", base_path="/api"
    url = Config.stalwart_url
    if url is None:
        return
    if url.startswith("http://"):
        url = url[len("http://") :]
        use_ssl = False
    elif url.startswith("https://"):
        url = url[len("https://") :]
        use_ssl = True
    else:
        use_ssl = False

    # Split host and optional base path
    if "/" in url:
        host, base_path = url.split("/", 1)
        base_path = "/" + base_path
    else:
        host = url
        base_path = ""

    # Result path
    path = f"{base_path}/principal/{user}"

    # Build request body
    body = json.dumps(
        [{"action": "addItem", "field": "emails", "value": alias}]
    ).encode("utf-8")

    # Connect HTTP(S)
    conn = (
        http.client.HTTPSConnection(host)
        if use_ssl
        else http.client.HTTPConnection(host)
    )
    try:
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
            print(f"Alias {alias} added to Stalwart")
        else:
            # Try to decode JSON error if possible
            try:
                err = json.loads(response_data.decode("utf-8"))
            except:
                err = response_data.decode("utf-8", errors="ignore")

            logger.error("Failed to add alias to Stalwart:", {'error': err})

    except Exception:
        logger.error("Failed to add alias to Stalwart")
    finally:
        conn.close()
