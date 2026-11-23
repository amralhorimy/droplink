"""Race-condition lab:  make race

Question: what happens when 200 people click a "max 10 downloads" link at the SAME instant?
Naive code (read count -> compare -> write count) lets many of them through.
DropLink claims a download with one atomic Lua script in Redis, so EXACTLY 10 get in.
"""
import asyncio
import sys
import tempfile
from collections import Counter
from pathlib import Path

import httpx

from labs.client import DropLinkClient

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"  # lab compose publishes the API directly
LIMIT, PEOPLE = 10, 200


async def main() -> None:
    client = DropLinkClient(BASE)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "race.txt"
        path.write_text("race me\n")
        file_id, token = client.upload(path)
        client.wait_until_done(file_id, token)
    slug = client.create_link(file_id, token, max_downloads=LIMIT, expires_in_seconds=300)["slug"]
    print(f"link {slug}: max_downloads={LIMIT}, firing {PEOPLE} simultaneous requests...")

    async with httpx.AsyncClient(base_url=BASE, timeout=30, limits=httpx.Limits(max_connections=PEOPLE)) as http:
        responses = await asyncio.gather(*(http.get(f"/d/{slug}", follow_redirects=False) for _ in range(PEOPLE)))
    counts = Counter(r.status_code for r in responses)
    print(f"results: {dict(counts)}")

    ok = counts.get(302, 0) == LIMIT and counts.get(410, 0) == PEOPLE - LIMIT
    print("PASS: exactly the allowed number got through." if ok else "FAIL: the counter is not atomic (or rate limits interfered).")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
