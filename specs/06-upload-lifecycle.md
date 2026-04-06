# Upload Lifecycle & Fault Tolerance

## 1. The Challenge
Data collection scenarios often happen in environments with flaky, slow, or completely absent cellular networks. When a user submits a `Package` that contains a JSON payload alongside ten 5MB photos, attempting a single 50MB multipart request is highly prone to failure. If it fails at 99%, the entire payload is lost and must be retried.

## 2. Package States
To manage this properly, a Package in the local SQLite database cycles through specific states:
*   **Draft:** In progress. Changes are auto-saved locally.
*   **Queued / Pending Upload:** User has finalized the package. It is in the outbox waiting for a network connection.
*   **Uploading:** Actively communicating with the server.
*   **Completed:** The server has fully acknowledged receipt of all JSON data and binary media.

## 3. The Upload Strategy (Three-Phase Protocol)
To ensure reliable delivery, the upload process must be decoupled from a single HTTP call. We use a file-by-file upload approach.

### Phase 1: Initialize Session & Upload JSON
*   The app's upload worker picks up a `Queued` package.
*   It sends the lightweight structured JSON data to the backend (e.g., `POST /api/packages`).
*   **Server response:** The server saves the structured data, marks its status as "Awaiting Media", and returns a unique `upload_session_id` (or expected upload URLs/IDs for the corresponding media files).

### Phase 2: File-by-File Upload
Instead of sending all ten 5MB photos at once, the worker uploads them sequentially one-by-one.
*   The worker takes Photo 1 and PUTs it to the server.
*   The worker records the successful upload of Photo 1 in the local SQLite database.
*   **If the connection drops during Photo 7:** 
    *   The app catches the network exception.
    *   Photos 1 through 6 are already safely stored on the backend.
    *   The worker sleeps. When the network is restored, the worker simply picks back up at Photo 7.

*(For massive files like videos, this phase could further implement a resumable chunked protocol like `tus`, but atomic file-by-file is generally sufficient for photos).*

### Phase 3: Commit / Finalize
*   Once the local SQLite database registers that all media files associated with the Package have been uploaded successfully, the app calls `POST /api/packages/{id}/commit`.
*   The server performs a final validation, ensuring all required media is present, and shifts the server-side status to `Completed` (or triggers the ML processing pipeline).
*   The app deletes the high-res local media files to free up device storage.

## 4. Background Execution & Retry Logic
*   **Foreground vs. Background:** When possible, uploads happen in the foreground for speed. However, if the user forcefully closes the app, a background task orchestrator (e.g., `workmanager` for Flutter) guarantees the queue will eventually be processed.
*   **Network Listeners:** The app monitors OS-level network states. The upload queue pauses immediately upon losing connection and resumes automatically upon connecting to WiFi or Cellular.
*   **Exponential Backoff:** If the server returns 5xx errors or the connection is extremely poor (failing repeatedly), the worker will apply exponential backoff (retry in 1m, 5m, 15m) to preserve battery life.
