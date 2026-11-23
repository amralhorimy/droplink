"""A small, readable client for DropLink. Used by the labs and handy as API usage documentation."""
import json
import mimetypes
from pathlib import Path

import httpx

TERMINAL = {"ready", "failed", "deleted"}


class DropLinkClient:
    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self.base_url = base_url.rstrip("/")
        self.http = httpx.Client(base_url=self.base_url, timeout=30)

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"X-Manage-Token": token}

    def upload(self, path: Path) -> tuple[str, str]:
        """Steps 1 + 2: register, push the bytes straight to MinIO, then confirm. Returns (file_id, token)."""
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        created = self.http.post(
            "/v1/files", json={"filename": path.name, "size": path.stat().st_size, "content_type": content_type}
        )
        created.raise_for_status()
        body = created.json()
        target = body["upload"]
        with path.open("rb") as fh:  # form fields first, the file LAST: that is what S3 requires
            sent = httpx.post(target["url"], data=target["fields"], files={"file": (path.name, fh, content_type)}, timeout=120)
        sent.raise_for_status()
        done = self.http.post(f"/v1/files/{body['file_id']}/complete", headers=self._auth(body["manage_token"]))
        done.raise_for_status()
        return body["file_id"], body["manage_token"]

    def wait_until_done(self, file_id: str, token: str, timeout: float = 60) -> dict:
        """Follow the live Server-Sent Events stream until the file is ready/failed."""
        last: dict = {}
        with httpx.stream(
            "GET", f"{self.base_url}/v1/files/{file_id}/events", headers=self._auth(token), timeout=timeout
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data:"):
                    last = json.loads(line[5:])
                    print(f"   event -> {last['status']}")
                    if last["status"] in TERMINAL:
                        break
        return last

    def create_link(self, file_id: str, token: str, **options) -> dict:
        r = self.http.post(f"/v1/files/{file_id}/links", json=options, headers=self._auth(token))
        r.raise_for_status()
        return r.json()

    def file_state(self, file_id: str, token: str) -> dict:
        r = self.http.get(f"/v1/files/{file_id}", headers=self._auth(token))
        r.raise_for_status()
        return r.json()

    def download(self, slug: str, **kwargs) -> httpx.Response:
        """First hop only: returns the 302 (or the error) without following the redirect."""
        return self.http.get(f"/d/{slug}", follow_redirects=False, **kwargs)
