# API reference

[العربية](../ar/API.md) · [Back to README](../../README.md)

Base URL (local): `http://localhost:8080` · Interactive docs: `/docs`
Owner endpoints need the header **`X-Manage-Token`** (returned once when the file is created).

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/v1/files` | – (rate limited) | Register a file, get a signed upload form |
| POST | `/v1/files/{id}/complete` | token | Confirm the upload; processing starts (202) |
| GET | `/v1/files/{id}` | token | Current state and analysis result |
| GET | `/v1/files/{id}/events` | token | Live status (Server-Sent Events) |
| GET | `/v1/files/{id}/thumbnail` | token | 302 to the thumbnail (images only) |
| DELETE | `/v1/files/{id}` | token | Delete the file and its links now (204) |
| POST | `/v1/files/{id}/links` | token | Create a share link |
| GET | `/v1/files/{id}/links` | token | List links of a file |
| GET | `/v1/links/{slug}` | – | Public info for a download page |
| DELETE | `/v1/links/{slug}` | token of its file | Revoke a link (204) |
| GET | `/d/{slug}` | – (+password) | 302 to a 60-second signed URL |
| GET | `/health/live`, `/health/ready` | – | Liveness / dependency readiness |

## Walk-through

### 1. Register
```bash
curl -s -X POST localhost:8080/v1/files -H 'content-type: application/json' \
  -d '{"filename":"hello.txt","size":6,"content_type":"text/plain"}'
```
```json
{
  "file_id": "9f2c…",
  "manage_token": "Vq3…",
  "upload": {
    "url": "http://localhost:9000/droplink",
    "method": "POST",
    "fields": { "key": "files/9f2c…", "policy": "…", "x-amz-signature": "…" },
    "expires_at": "2026-11-23T12:15:00Z"
  },
  "expires_at": "2026-11-30T12:00:00Z"
}
```

### 2. Upload straight to storage
Send **every** entry of `fields` as a form field, and the file **last**, named `file`:
```bash
curl -X POST "$URL" -F key="$KEY" -F policy="$POLICY" … -F file=@hello.txt
```
(`python -m labs.dropctl` does all of this for you.) MinIO answers `204`. Uploading more than the declared `size` is rejected by MinIO.

### 3. Complete and watch
```bash
curl -X POST localhost:8080/v1/files/$ID/complete -H "X-Manage-Token: $TOKEN"
curl -N localhost:8080/v1/files/$ID/events      -H "X-Manage-Token: $TOKEN"
```
```
event: status
data: {"type":"status","file_id":"…","status":"uploaded", …}

event: status
data: {"type":"status","status":"processing", …}

event: status
data: {"type":"status","status":"ready","sha256":"…","detected_type":"text/plain", …}
```
The stream ends on `ready`, `failed` or `deleted` (or after 120 s with an `event: timeout`).

### 4. Create a link
```bash
curl -X POST localhost:8080/v1/files/$ID/links -H "X-Manage-Token: $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"expires_in_seconds":3600,"max_downloads":1,"password":"secret"}'
```
`max_downloads: 0` means unlimited. A link never outlives its file.

### 5. Download
```bash
curl -i -H "X-Link-Password: secret" localhost:8080/d/$SLUG    # or ?password=secret
```
`302 Location:` is a signed URL valid for 60 seconds.

## Errors

Every error has the same shape:
```json
{ "error": { "code": "link_expired", "message": "This link has expired.", "request_id": "a1b2c3d4e5f60718" } }
```
Quote the `request_id` when reporting a problem; it finds the exact log lines.

| HTTP | `code` | Meaning |
|---|---|---|
| 401 | `unauthorized`, `password_required` | management token or link password missing |
| 403 | `invalid_manage_token`, `wrong_password` | credentials wrong |
| 404 | `file_not_found`, `link_not_found`, `no_thumbnail` | does not exist (or was deleted) |
| 409 | `upload_missing`, `invalid_file_state`, `file_not_ready`, `file_unavailable` | wrong moment for this action |
| 410 | `link_expired`, `link_exhausted`, `link_revoked` | link no longer usable |
| 413 | `file_too_large` | above `MAX_FILE_SIZE_MB` |
| 422 | `validation_error` | invalid fields, listed in `details` |
| 429 | `too_many_requests` | rate limit; see `Retry-After` |
| 503 | `database_unavailable`, `cache_unavailable`, `storage_unavailable` | a dependency is down |
| 500 | `internal_error` | our bug; details only in logs |

## Configuration

All variables start with `DROPLINK_`. Full list with defaults: [`app/platform/shared/config.py`](../../app/platform/shared/config.py). The ones you will touch first:

| Variable | Default | Purpose |
|---|---|---|
| `MAX_FILE_SIZE_MB` | 100 | upload cap |
| `FILE_TTL_HOURS` | 168 | maximum life of any file |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | used to build share links |
| `MINIO_PUBLIC_ENDPOINT` / `_SECURE` | `localhost:9000` / false | host clients use for signed URLs |
| `RATE_LIMIT_DOWNLOAD_PER_MINUTE` | 30 | per IP |
| `LOG_JSON` | false | JSON logs for log collectors |
| `ENV` | dev | `prod` hides `/docs` |
