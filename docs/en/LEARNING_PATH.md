# Learning path

[العربية](../ar/LEARNING_PATH.md) · [Back to README](../../README.md)

Read the project in this order. Each step says **what to read**, **what to notice**, and a **small exercise**.

## Step 0 — Run it (15 min)
Run `make up`, open `/docs`, upload a file with `python -m labs.dropctl upload <file>`, then watch `make logs`.
*Notice:* the same `request_id` appears on every log line of one request.

## Step 1 — Configuration & errors (30 min)
Read `app/platform/shared/config.py`, `errors.py`, `handlers.py`.
*Notice:* an error has **two** messages: one for logs, one for the client.
*Exercise:* add a new error `FileLocked(Conflict)` with its own `code` and raise it from a service.

## Step 2 — One feature, top to bottom (1 h)
Read `app/modules/links/` in this order: `schemas.py → routes.py → service.py → repo.py → policy.py`.
*Notice:* `policy.py` has no I/O, so `tests/unit/test_policy.py` needs no database.
*Exercise:* add a rule "a link may not be created for a file that is still `processing`" and write its test.

## Step 3 — Infrastructure wrappers (1 h)
Read `app/platform/mongo/`, `redis/`, `minio/`, then `infra.py` and `container.py`.
*Notice:* the `with translate_mongo_errors("…"):` pattern, and that nothing creates clients as hidden globals.
*Exercise:* stop Redis (`docker compose stop redis`) and call the API. Read the log and the client response side by side.

## Step 4 — State machine & atomicity (1 h)
Read `app/modules/files/domain.py` and `repo.transition`. Then read `app/platform/redis/scripts.py` and run **`make race`**.
*Notice:* why 200 simultaneous requests still produce exactly 10 downloads.
*Exercise:* in `scripts.py` replace the Lua with "GET, compare in Python, INCR" and run `make race` again. Watch it fail.

## Step 5 — Background work (1.5 h)
Read `app/platform/redis/jobs.py`, `workers/processor/`, then `workers/janitor/`.
*Notice:* the job is copied to a "processing" list before work starts and removed only after it finishes.
*Exercise:* kill the processor during a job (`docker compose kill processor`), restart it, and watch the job recover.

## Step 6 — Real time (45 min)
Read `app/modules/events/service.py` and `labs/client.py → wait_until_done`.
*Notice:* subscribe first, snapshot second.
*Exercise:* call the events endpoint with `curl -N -H "X-Manage-Token: …"` while uploading another file.

## Step 7 — Deployment (45 min)
Read `deploy/docker/Dockerfile`, `docker-compose.yml`, `deploy/nginx/nginx.conf`.
*Notice:* healthchecks, non-root user, one image with three commands, SSE-specific Nginx settings.

## Challenges
1. Add a `GET /v1/files/{id}/links/{slug}/stats` endpoint.
2. Add `DROPLINK_ALLOWED_TYPES` and reject other types in the processor (mark `failed`).
3. Replace the fixed-window limiter with a sliding window.
4. Add Prometheus metrics (`/metrics`) for queue length and downloads.
5. Add an `s3`-compatible provider switch (MinIO ↔ AWS S3).
