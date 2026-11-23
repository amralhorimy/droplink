"""End-to-end smoke test against a RUNNING stack:  make up && make e2e

Walks the whole story: upload -> live processing -> link -> password -> download -> limit -> delete.
"""
import hashlib
import sys
import tempfile
from pathlib import Path

import httpx

from labs.client import DropLinkClient

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"


def check(condition: bool, label: str) -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    client = DropLinkClient(BASE)
    payload = b"hello from DropLink\n" * 50
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "hello.txt"
        path.write_bytes(payload)

        print("1) upload + live processing")
        file_id, token = client.upload(path)
        state = client.wait_until_done(file_id, token)
        check(state["status"] == "ready", "file reached 'ready' through the SSE stream")
        info = client.file_state(file_id, token)
        check(info["processing"]["sha256"] == hashlib.sha256(payload).hexdigest(), "worker computed the right sha256")
        check(info["processing"]["detected_type"] == "text/plain", "worker detected the real type")

        print("2) link with password + 2 downloads")
        link = client.create_link(file_id, token, max_downloads=2, password="s3cret", expires_in_seconds=300)
        slug = link["slug"]
        check(client.download(slug).status_code == 401, "no password -> 401")
        check(client.download(slug, headers={"X-Link-Password": "nope"}).status_code == 403, "wrong password -> 403")
        good = {"X-Link-Password": "s3cret"}
        for n in (1, 2):
            r = client.download(slug, headers=good)
            check(r.status_code == 302, f"download {n} -> 302 redirect to a signed URL")
            body = httpx.get(r.headers["location"], timeout=30)
            check(body.content == payload, f"download {n} returned the exact bytes")
        check(client.download(slug, headers=good).status_code == 410, "3rd download refused (limit reached) -> 410")

        print("3) delete")
        deleted = client.http.delete(f"/v1/files/{file_id}", headers={"X-Manage-Token": token})
        check(deleted.status_code == 204, "file deleted")
        check(client.http.get(f"/v1/links/{slug}").status_code in (404, 410), "link is gone with its file")
    print("\nAll good.")


if __name__ == "__main__":
    main()
