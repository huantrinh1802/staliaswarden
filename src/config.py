import base64
import os
import re
from pathlib import Path

LINE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$')

def parse_value(raw: str) -> str:
    """Parse a .env value similar to python-dotenv."""
    raw = raw.strip()

    # Remove surrounding single/double quotes
    if (
        (raw.startswith('"') and raw.endswith('"')) or
        (raw.startswith("'") and raw.endswith("'"))
    ):
        raw = raw[1:-1]

    return raw


def load_env(file_path: str = ".env", override: bool = False):
    """
    Load a .env file into os.environ.

    :param file_path: path to .env file
    :param override: if True, override existing environment variables
    :return: dict of loaded key/value pairs
    """

    env_file = Path(file_path)
    if not env_file.is_file():
        raise FileNotFoundError(file_path)     
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = LINE_RE.match(line)
        if not match:
            continue  # Invalid line format

        key, raw_val = match.groups()
        value = parse_value(raw_val)

        if override or key not in os.environ:
            os.environ[key] = value

        os.environ[key] = value
if os.environ.get('IS_DOCKER') != '1':
    load_env('.env')


class Config(object):
    alias_domain: str = os.environ["ALIAS_DOMAIN"]
    api_token: str | None = os.environ.get("API_TOKEN")
    forward_to: str | None = os.environ.get("FORWARD_TO")
    port: str | None = os.environ.get("PORT")
    if 'STALWART_TOKEN' in os.environ:
        stalwart_token: str = f'Bearer {os.environ.get("STALWART_TOKEN")}'
    else:
        creds = f"{os.environ['STALWART_USERNAME']}:{os.environ['STALWART_PASSWORD']}".encode("utf-8")
        stalwart_token = "Basic " + str(base64.b64encode(creds).decode("utf-8"))
    stalwart_url: str | None = os.environ.get("STALWART_URL")
