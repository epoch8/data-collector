# Upload Lifecycle & Fault Tolerance

## 1. The Challenge
Data collection scenarios often happen in environments with flaky, slow, or completely absent cellular networks. When a user submits a `Package` that contains a JSON payload alongside ten 5MB photos, attempting a single 50MB multipart request is highly prone to failure. If it fails at 99%, the entire payload is lost and must be retried.

Server-side ordering, HTTP contract, and client upload/history UX (Russian) are defined in [08-server-api-package-upload.md](08-server-api-package-upload.md) (blobs before manifest, then commit).

## 2. Package States
To manage this properly, a Package in the local SQLite database cycles through specific states:
*   **Draft:** In progress. Changes are auto-saved locally.
*   **Queued / Pending Upload:** User has finalized the package. It is persisted on disk (`07`) and in the outbox waiting for a network connection.
*   **Uploading:** Actively communicating with the server (per-blob and manifest steps).
*   **Completed (local):** The server has fully acknowledged receipt after **`commit`** (and optionally confirmed via `GET` if the client reconciles). Only then should the app delete large local blobs to free storage (see `08-server-api-package-upload.md` §8).

## 3. The Upload Strategy (Multi-Step Protocol)
To ensure reliable delivery, the upload process must be decoupled from a single HTTP call. We use a **file-by-file** upload for binaries, then a **separate** manifest request, then **commit**.

**Product decision:** send **all blobs first**, then the **JSON manifest** (`payload.json` semantics), so the server never holds a manifest that references missing files. The client **pushes** every request when connectivity allows; the server does not pull from the device.

### Phase 1: Initialize Session
*   The app's upload worker picks up a `Queued` package.
*   It calls the backend to create/resume the package session (e.g. `POST /v1/projects/{project_id}/packages` with `package_id`).
*   **Server response:** session id / status `awaiting_blobs` (see `08`).

### Phase 2: File-by-File Blob Upload
The worker uploads each file under `/blobs/` with one HTTP request per file (many requests per package).
*   The worker takes Photo 1 and `PUT`s it to the server using the **same relative path** that will later appear in the manifest (e.g. `blobs/item_001_image.jpg`).
*   The worker records the successful upload of Photo 1 in the local database (per-blob ledger).
*   **If the connection drops during Photo 7:**
    *   The app catches the network exception.
    *   Photos 1 through 6 are already safely stored on the backend.
    *   When the network is restored, the worker resumes at Photo 7 (idempotent `PUT`).

*(For massive files like videos, this phase could further implement a resumable chunked protocol like `tus`, but atomic file-by-file is generally sufficient for photos.)*

### Phase 3: Upload Manifest (JSON)
*   After all required blobs for that package are uploaded, the worker sends the structured JSON manifest (equivalent to `payload.json` in `07`).
*   The server validates that every `blobs/...` reference in the JSON exists server-side; otherwise the client receives `422` and must fix/retry.

### Phase 4: Commit / Finalize
*   The app calls `POST .../commit` (see `08`).
*   The server performs final validation and marks the package completed server-side.
*   **Only after a successful `commit` response** (and consistent policy with `GET` if used), the app may delete high-res local media for that package to free device storage.

## 4. Background Execution & Retry Logic
*   **Foreground vs. Background:** When possible, uploads happen in the foreground for speed. However, if the user forcefully closes the app, a background task orchestrator (e.g., `workmanager` for Flutter) guarantees the queue will eventually be processed.
*   **Network Listeners:** The app monitors OS-level network states. The upload queue pauses immediately upon losing connection and resumes automatically upon connecting to WiFi or Cellular.
*   **Exponential Backoff:** If the server returns 5xx errors or the connection is extremely poor (failing repeatedly), the worker will apply exponential backoff (retry in 1m, 5m, 15m) to preserve battery life.

## 5. MVP UX (from planning)
*   An **outbox / upload** screen with a manual **Send** action is acceptable for an intermediate stage to validate the API path end-to-end; later, automatic upload when online can be enabled.
*   Showing per-package upload status on **history** (e.g. queued vs uploaded) is desirable; exact visuals live in screen specs.
