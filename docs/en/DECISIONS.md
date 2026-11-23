# Design decisions (the "why")

[العربية](../ar/DECISIONS.md) · [Back to README](../../README.md)

Good code explains *what*. This file explains *why*, and what you would do differently in production.

### 1. Files bypass the API
**Decision:** clients upload to and download from MinIO using signed URLs.
**Why:** the API stays small and fast; a 100 MB upload never occupies a worker or memory. The URL is signed with the **public** MinIO hostname because a signature covers the host.
**Trade-off:** MinIO must be reachable by clients. In production put it behind its own domain + TLS (`DROPLINK_MINIO_PUBLIC_ENDPOINT`).

### 2. POST policy instead of a presigned PUT
**Decision:** uploads use a signed *form* (POST policy).
**Why:** a presigned PUT cannot limit size. A POST policy lets MinIO itself reject anything outside `1…declared_size` bytes and any other object key.

### 3. No user accounts — a secret `manage_token`
**Decision:** creating a file returns a random token (shown once); only its SHA-256 hash is stored.
**Why:** keeps the project focused on infrastructure, and the token is enough to demonstrate authorization. Comparison is constant-time.
**Production:** add real authentication (OAuth/JWT) and attach files to users.

### 4. Redis Lua for download counting
**Decision:** one Lua script checks the limit and increments.
**Why:** "read → compare → write" is a race. With 200 simultaneous requests it lets many extra downloads through. A Lua script is one indivisible step. Prove it yourself: `make race`.
**Self-healing:** if Redis loses the key (restart without persistence, eviction), the script re-seeds it from the count stored in Mongo. Redis also runs with AOF persistence in the compose file.
**Known gap:** a download is "spent" when the redirect is issued, not when the bytes finish. That is the standard trade-off of signed URLs.

### 5. A queue on Redis lists (not Celery, not Streams)
**Decision:** `LPUSH` + `BLMOVE` + `LREM`, with recovery on start-up.
**Why:** readable in 40 lines, so beginners can *see* how a queue works. It gives at-least-once delivery; handlers are idempotent (state machine + deterministic outputs).
**Limit:** recovery assumes one live worker per `WORKER_ID`. For many workers use Redis Streams with consumer groups, or a dedicated broker.

### 6. Pub/Sub for live status
**Decision:** workers `PUBLISH`, the SSE endpoint `SUBSCRIBE`s.
**Why:** instant updates with no polling. Pub/Sub is fire-and-forget, so the endpoint **subscribes first and then reads the current status** — a client that connects late still gets the truth.
**Limit:** `EventSource` in browsers cannot send headers, so the stream needs `X-Manage-Token`; use `fetch()` streaming or a short-lived stream ticket in a real front end.

### 7. One image, three roles
**Decision:** API, processor and janitor share one Docker image and one codebase; only the command differs.
**Why:** one build, one dependency set, shared models. Scale roles independently with `docker compose up --scale processor=3` (give each a unique `DROPLINK_WORKER_ID` when you do).

### 8. `platform/` vs `modules/`
**Decision:** infrastructure wrappers (with their own `errors.py`) are separate from business features.
**Why:** swapping MinIO for S3, or Mongo for Postgres, touches one folder. Business rules stay readable because no driver exceptions leak into them.

### 9. Central error system with two paths
**Decision:** every error is an `AppError`; one handler logs the detail and returns a safe envelope.
**Why:** developers get full context and a `request_id`; users never see internals. Stable `code` values are a contract clients can rely on.

### 10. Mongo TTL index for purging
**Decision:** deleting a file marks the record `deleted` and sets `purge_at`; a TTL index removes the record later.
**Why:** a short audit window and zero cleanup code for the last step.

### 11. Fixed-window rate limiting
**Decision:** `INCR` + `EXPIRE` in Lua, per IP.
**Why:** simple and cheap. **Limit:** bursts at window edges. For production consider a sliding window or token bucket, and rate limit at the CDN too. Nginx adds a second, coarser layer.

### 12. scrypt from the standard library
**Decision:** passwords for links are hashed with `hashlib.scrypt`, run in a thread (`asyncio.to_thread`).
**Why:** no extra dependency, memory-hard, and the thread keeps the event loop responsive. Attempts are also rate limited per link and IP.

### 13. What a production version would add
Authentication and quotas · antivirus scanning in the processor · object-store lifecycle rules as a second safety net · metrics and tracing (Prometheus, OpenTelemetry) · migrations strategy · a managed Redis/Mongo with backups · TLS everywhere.
