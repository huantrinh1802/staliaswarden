import concurrent.futures
import http.client
import json
import os
import random
import re
import string
import time
import urllib.parse
from pathlib import Path

LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def parse_value(raw: str) -> str:
    """Parse a .env value similar to python-dotenv."""
    raw = raw.strip()

    # Remove surrounding single/double quotes
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
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


load_env(".env")
SERVER = f"http://127.0.0.1:{os.environ['PORT']}"  # Change if needed
TOTAL_REQUESTS = 5000
CONCURRENCY = 200


def random_alias():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def send_request(method, path, body=None):
    parsed = urllib.parse.urlparse(SERVER)
    conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['API_TOKEN']}",
    }

    try:
        start = time.time()

        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        print(response.status, response.reason)

        latency = time.time() - start
        status = response.status

        conn.close()
        return status < 500, latency

    except Exception as e:
        print("Failed to make request", e)
        return False, 0


def make_request():
    endpoints = [
        ("/testing", "GET"),
    ]

    path, method = random.choice(endpoints)

    body = None
    if method == "POST":
        body = json.dumps({"alias": random_alias()})

    return send_request(method, path, body)


def main():
    print(f"Running performance test: {TOTAL_REQUESTS} requests @ {CONCURRENCY} concurrency")
    start = time.time()

    success = 0
    failure = 0
    latencies = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(make_request) for _ in range(TOTAL_REQUESTS)]

        for f in concurrent.futures.as_completed(futures):
            ok, latency = f.result()
            if ok:
                success += 1
                latencies.append(latency)
            else:
                failure += 1

    duration = time.time() - start
    rps = TOTAL_REQUESTS / duration

    print("\n--- RESULTS ---")
    print(f"Total time: {duration:.2f}s")
    print(f"Requests/sec: {rps:.2f}")
    print(f"Success: {success}")
    print(f"Failures: {failure}")

    if latencies:
        print(f"Avg latency: {sum(latencies) / len(latencies):.4f}s")
        print(f"Max latency: {max(latencies):.4f}s")
        print(f"Min latency: {min(latencies):.4f}s")


if __name__ == "__main__":
    main()
