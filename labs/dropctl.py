"""Tiny CLI:  python -m labs.dropctl upload ./photo.jpg --max-downloads 3 --ttl 600"""
import argparse
from pathlib import Path

from labs.client import DropLinkClient


def main() -> None:
    parser = argparse.ArgumentParser(description="DropLink command line")
    parser.add_argument("--base", default="http://localhost:8080")
    sub = parser.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("upload", help="upload a file and print a share link")
    up.add_argument("path", type=Path)
    up.add_argument("--ttl", type=int, default=3600, help="link lifetime in seconds")
    up.add_argument("--max-downloads", type=int, default=0)
    up.add_argument("--password")
    args = parser.parse_args()

    client = DropLinkClient(args.base)
    file_id, token = client.upload(args.path)
    print(f"uploaded. file_id={file_id}")
    state = client.wait_until_done(file_id, token)
    if state["status"] != "ready":
        raise SystemExit(f"processing ended with status {state['status']}")
    options = {"expires_in_seconds": args.ttl, "max_downloads": args.max_downloads}
    if args.password:
        options["password"] = args.password
    link = client.create_link(file_id, token, **options)
    print(f"\nshare link : {link['url']}")
    print(f"manage token (keep it secret): {token}")


if __name__ == "__main__":
    main()
