> **Language / Язык:** **English** · [Русский](08-server-api-package-upload.ru.md)

# 8 — Package upload to server (client and API)

Status: **current** (June 2026). Reference: `django_server/api/views.py`, `project_db.py`, `project_media.py`.

A single spec describing **how** the app sends a package to a **specific project** on a **specific server**, what the user sees (queue, history), and the **HTTP contract** (step order, status codes, idempotency).

**Related documents:** [06-upload-lifecycle.md](06-upload-lifecycle.md) (device lifecycle and retries), [07-package-payload-structure.md](07-package-payload-structure.md) (`payload.json`, `blobs/`), [02-data-models-schema.md](02-data-models-schema.md) (identifiers).

**Diagram:** [main-scheme/03_server_api.drawio](main-scheme/03_server_api.drawio) — step order, client ↔ server, outbox and history.

Traffic is initiated by the **client only** (push).

---

## 1. Goals

- Reliable delivery over an unstable network.
- On the server, **do not mark a package as "ready"** for external consumers until **all blobs** and the **JSON manifest** are consistent (no dangling references).
- **Idempotency** for repeated requests with the same identifiers.
- On the client — per-**blob** and per-**package** status; **Upload** screen and **history** (accepted on server / local only).

---

## 2. What is a package

A **package** is one logical collection: a directory on the device with `blobs/*` and **`payload.json`** (see `07`). The same set goes to the server: many binary objects + one JSON; paths in JSON look like `blobs/...`.

**`package_id`** is assigned by the client (e.g. UUID). **`project_id`** in the URL and in JSON must match the configuration project.

A package **without files** is allowed if the project schema permits a manifest with no `blobs/` references.

---

## 3. Required server order

1. Upload **all blobs** (one HTTP request per file; path matches what will appear in the manifest).
2. Upload the **manifest** (JSON as in `07`, only references to already accepted `blobs/...`).
3. Call **`commit`**. After a successful response the client may treat the package as accepted and, per policy in `06`, clean up local heavy files.

A minimal variant without a separate `commit` is possible only if the product explicitly agrees that "success after manifest" = full acceptance for external systems.

---

## 4. Idempotency (client and server)

- Repeat **`PUT`** of the same blob (same path within `package_id` and project) with the same content → success, no duplicate in storage.
- Repeat manifest / **`commit`** for an already accepted package → predictable response (`200` with the same result or `409` per policy), without double enqueueing for processing (key — at least `package_id`).
- Parallel **`PUT`** of different blobs is allowed; two **`commit`** calls — serialize; the second is an idempotent success.

---

## 5. Client: state tracking

- **Per blob:** uploaded / not / error (for resume after disconnect).
- **Per package:** queued, uploading, accepted by server (after `commit` and optionally `GET` verification), error with retry.

Unuploaded packages appear when upload **immediately after collection** is not possible (network, error) — the package is saved locally and enters the outbox.

---

## 6. Upload screen (outbox)

**Condition:** at least one package waiting to be sent to the server.

**Behavior:** list of packages; **Upload all** and/or **selection** + **Send selected**; progress per blob and JSON/`commit` stage; on error — message, package stays in queue (retries — `06`).

A dedicated screen is acceptable in MVP; later — background upload with the same state model.

---

## 7. History: indication

| Visual | Meaning |
|--------|---------|
| **Green** (or "on server") | Package **accepted by server** (criterion: successful `commit`, or `GET` if uncertain). |
| **Yellow** ("device only") | Package **exists locally**, **not delivered** to server or delivery incomplete. |

UI details — in [03-user-journey-screens.md](03-user-journey-screens.md).

---

## 8. Deleting a package from the device

Delete blobs and the package directory **only after** confirmed full server acceptance (aligned with `06` §2), to avoid data loss on disconnect. Whether history entries remain after file deletion is a separate product decision.

---

## 9. Server: terms

| Term | Meaning |
|------|---------|
| Server | Backend with a base URL; in production — **HTTPS** (TLS 1.2+). A version prefix is desirable, e.g. `/v1/`. |
| Project | No project / no write access / read-only → reject upload. |
| Package | `package_id` from client — stable key for session, resume, and idempotency. |

Choice of central config host and upload URL is out of scope; paths like `/v1/projects/{project_id}/...` must remain valid.

---

## 10. Server: package states

| Status | Meaning |
|--------|---------|
| `created` / `awaiting_blobs` | Session exists; `PUT` on blobs accepted. |
| `awaiting_manifest` | *(Optional.)* Waiting for manifest; may merge with previous. |
| `ready_to_commit` | Manifest valid; every `blobs/...` reference resolves to an accepted object. |
| `completed` | After `commit`. Repeat of same `package_id` — idempotent success or `409`. |
| `failed` | Terminal. |
| `abandoned` | *(Optional.)* TTL, draft cleanup. |

Transitions are **monotonic** — no rollback from `completed` / `failed` without an administrator.

**Django reference** (`django_server/api`): sessions and blobs stored in **per-project DB** (SQLAlchemy, `database_uri`), files via **fsspec** (`storage_uri`). Phases: `awaiting_blobs`, `ready_to_commit`, `completed`, `failed` (no `created`, `awaiting_manifest`, `abandoned`). Model has `failure_reason`; not yet returned in `GET …/packages/{package_id}`.

---

## 11. Server: endpoints (logic)

Path form: `/v1/projects/{project_id}/packages/...`. Exact contracts — in **OpenAPI**.

### 11.1. `POST …/packages` — session

Body: at minimum `package_id`; optionally `client_version`, `device_id`, `created_at`; optionally `blob_inventory` → early quota check (`422`).

Response `201` (new session) or `200` (session already existed): at minimum `package_id`, `status` (`awaiting_blobs` | `ready_to_commit` | `completed` | `failed`). Optional in product: `upload_session_id`, `expires_at`.

Repeat with same `package_id` → `200`/`201` with same state or `409` if package already completed. **In Django reference:** for already `completed`, repeat `POST` returns **`409`**; idempotent success without side effects is on **`POST …/commit`** (see §11.4).

### 11.2. `PUT …/packages/{package_id}/blobs/{blob_path}` — one file

`blob_path` — **URL-encoded**, as in manifest (or presigned URL / `blob_id` — fix in product).

Headers: `Content-Type`, `Content-Length` (if not chunked); optionally `Content-MD5` / `Digest`.

Response `200`/`201`: confirmation. **In Django reference:** body `{"path": "<logical path>", "size": <bytes>}`. Resumable (tus, `Content-Range`) — only if explicitly in spec.

**Reference note:** if session is already in `ready_to_commit` phase, repeat blob `PUT` **resets** saved manifest and returns phase to `awaiting_blobs` (repeat cycle "blobs → manifest → commit" allowed).

### 11.3. `PUT` or `POST …/manifest` — JSON after blobs

Body as `payload.json` per `07`. Server: schema and domain rules; all `blobs/…` references must point to accepted objects — otherwise **`422`** with list of missing paths → `ready_to_commit`.

**In Django reference** only **`PUT`** on `…/manifest` is implemented (no `POST`). Invalid JSON body — **`400`** (`invalid_json`). Missing blobs: error code `missing_blobs`, paths in `error.details`. `project_id` mismatch between JSON and URL — **`422`**, code `project_id_mismatch`. If package already `completed`, manifest `PUT` returns **`200`** with `status: completed` (idempotent, no data change).

### 11.4. `POST …/commit`

Manifest accepted, required blobs present, hashes/sizes (if set). Success → `completed`. Otherwise **`409`** / **`422`**.

Repeat `commit` for `completed` → **`200`** without duplicating queue side effects.

### 11.5. `GET …/packages/{package_id}` — status

After crash: `status`, list of accepted blobs, optionally `expires_at`, `failed` reason.

**In Django reference:** JSON `{"package_id", "status", "blobs": [<logical paths>]}`; `expires_at` and `failed` reason not yet in response.

### 11.6. `DELETE …/packages/{package_id}` *(optional)*

Cancel draft while not `completed` (or separate role). **In Django reference:** success — **`204`**, for `completed` — **`409`**.

### 11.7. Flutter client in this repository

Sequence `POST` session → `PUT` all files from `blobs/` (path in URL with `Uri.encodeComponent` per segment) → `PUT` manifest → `POST` `commit`: see `lib/features/collection/logic/package_server_upload.dart`. On **`409`** for session `POST`, performs status `GET`; if `completed`, local delivery state is marked done without re-sending blobs.

---

## 12. Authentication

Bearer / OAuth2 / mTLS — explicit in OpenAPI. Token limits accessible `project_id`. Audit: `project_id`, `package_id`, subject, `commit` result (GDPR for IP/UA).

**In Django reference** (`ApiV1AuthMiddleware`): with Firebase enabled — header `Authorization: Bearer <Firebase ID token>`, `project_id` access via `CollectorUser` project assignment; with Firebase disabled and `API_BEARER_TOKEN` set — shared secret; otherwise locally `/v1/*` without token check. Endpoint **`GET /health`** (outside `/v1/`) — text `ok` for liveness.

---

## 13. HTTP status codes

| Situation | Code |
|-----------|------|
| Missing / expired token | `401` |
| No permission | `403` |
| Resource not found | `404` (preferably without leaking existence) |
| Wrong phase / idempotency conflict | `409` |
| Manifest, validation, missing blob reference | `422` |
| Size / quota / rate limit | `413` / `429` |
| Internal error | `500` (client — backoff) |

Error body: e.g. `{ "error": { "code", "message", "details" } }`.

---

## 14. Client request order

`POST` session → all blob **`PUT`**s → manifest → **`commit`**. Manifest may arrive on the network before blobs, but reference validation will fail.

---

## 15. Server non-functional requirements

- Durable storage for manifest and blobs (not ephemeral disk only).
- `commit` atomic for external observers.
- TTL and cleanup of incomplete sessions and orphan blobs.
- Limits: file size, total package size, file count, RPS.
- Upload routes: long proxy timeouts, streaming without full RAM buffering.
- TLS, body limit on gateway, `blob_path` validation (no `..`, not absolute path).
- Metrics, logs with `X-Request-Id`, `GET /health`, API version and manifest migrations.

---

## 16. Open decisions

1. Blob identification: manifest path only vs presigned URL / `blob_id`.
2. Large files: single `PUT` vs mandatory resumable (tus).
3. Post-processing: in `commit` transaction vs queue; separate processing status endpoint.

After decisions — **OpenAPI 3.1** and example full sequence for one `project_id` and `package_id`.
