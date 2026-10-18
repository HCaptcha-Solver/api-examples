"""Run from the repository root; see README.md. Paid calls require a request ID."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError

from client import ApiError, Client, require_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("balance")
    browser = sub.add_parser("browser")
    browser.add_argument("--url", required=True)
    browser.add_argument("--sitekey", required=True)
    browser.add_argument("--idempotency-key", required=True)
    image = sub.add_parser("image")
    image.add_argument("request", type=Path)
    image.add_argument("--idempotency-key", required=True)
    get = sub.add_parser("get")
    get.add_argument("id")
    args = parser.parse_args()
    client = Client(os.environ.get("HCAPTCHA_API_KEY", ""))
    capture_id = None
    if args.command == "balance":
        print(json.dumps(client.balance(), indent=2))
        return
    if args.command == "browser":
        task = client.create_browser_task(args.url, args.sitekey, idempotency_key=args.idempotency_key)
    elif args.command == "image":
        body = json.loads(args.request.read_text(encoding="utf-8-sig"))
        capture_id = body["challenge_id"]
        task = client.solve_image(body, idempotency_key=args.idempotency_key)
    else:
        task = client.get_task(args.id)
    print(f"Operation: {task['id']}", file=sys.stderr)
    task = client.wait(task)
    print(json.dumps(task, indent=2))
    require_result(task, challenge_id=capture_id)


if __name__ == "__main__":
    try:
        main()
    except (ApiError, ValueError, KeyError, OSError, URLError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        if isinstance(error, ApiError) and error.retry_after:
            print(f"Retry-After: {error.retry_after} seconds", file=sys.stderr)
        print("If a paid call was interrupted, keep its original JSON and Idempotency-Key.", file=sys.stderr)
        sys.exit(1)
