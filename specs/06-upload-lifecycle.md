> **Language / Язык:** **English** · [Русский](06-upload-lifecycle.ru.md)

# Upload Lifecycle & Fault Tolerance

Status: **current** (June 2026).

HTTP contract and server phases — [08-server-api-package-upload.md](08-server-api-package-upload.md). Payload structure — [07-package-payload-structure.md](07-package-payload-structure.md).

## 1. Problem

Data collection often happens without a stable network. A single multipart request for the whole package (JSON + 10×5 MB photos) is unreliable. Solution — **multi-step protocol**: blobs one at a time, then manifest, then commit.

## 2. Device-side states

### Local package status (`status` in Drift)

| Status | Meaning |
|--------|-------|
| `draft` | Collection in progress (auto-save) |
| `completed` | User pressed submit; package materialized on disk |

### Server delivery status (`serverDeliveryState`)

| Status | Meaning |
|--------|-------|
| `pending` | Ready to send, not started yet |
| `uploading` | Upload protocol in progress |
| `completed` | Successful `commit` (or `GET` confirmed `completed` after `409` on create) |
| `failed` | Error; package stays in queue for retry |

Upload is **not automatic** after submit — user initiates from the **Server** tab (`ServerSyncTab`).

## 3. Upload protocol (client)

Code: `lib/features/collection/logic/package_server_upload_io.dart` (and `_web.dart`).

### Phase 1: Initialize session

`POST /v1/projects/{project_id}/packages` with `{ "package_id": "..." }`.

- `201` / `200` → `awaiting_blobs` or resume.
- `409` if already `completed` → client does `GET` and marks locally `completed`.

### Phase 2: Blob upload

For each file in `blobs/`:

`PUT /v1/projects/{project_id}/packages/{package_id}/blobs/{encoded_path}`

- Body: raw bytes (`application/octet-stream`).
- Idempotent retry of the same file — OK.
- Network drop → resume from the unuploaded blob.

### Phase 3: Manifest

`PUT .../manifest` — JSON as `payload.json`.

- Server checks all `blobs/...` references → `ready_to_commit` or `422 missing_blobs`.
- `project_id` in JSON must match the URL.

### Phase 4: Commit

`POST .../commit` → `completed`.

Repeat `commit` for a completed package → `200` with `idempotent: true`.

### Local file cleanup

Policy: delete heavy blobs **after** confirmed `completed`. Current implementation **keeps** local files (deletion — future product decision).

## 4. Server storage

After commit:

- Metadata — per-project DB (`package_session`, `uploaded_blob`) via SQLAlchemy.
- Files — fsspec at `storage_uri`: `packages/{package_id}/blobs/...`.

## 5. Retry and background

| Mechanism | Status |
|----------|--------|
| Manual retry from **Server** | **Implemented** |
| `connectivity_plus` for UI | Partial |
| Exponential backoff | Basic Dio error handling in upload code |
| `workmanager` / background when app closed | **Not implemented** |

## 6. UX

- **Server** tab: pending/failed list, "Upload all".
- **History**: border color by `serverDeliveryState` (`package_delivery_style.dart`).
