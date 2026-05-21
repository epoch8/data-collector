# Stage 1: MVP Scope

To avoid feature bloat, we strictly limit Stage 1.

## What is IN scope for Stage 1:
1. **Mock Authentication:** A simple dummy login screen (no real API call) that routes to the Dashboard.
2. **Mock Projects & Configs:** Hardcode a realistic project Config into the app (e.g., loaded from a local JSON asset, bypassing backend sync for now).
3. **Dynamic Wizard Logic (Basic Types):**
   * Support field types such as `text_input`, `datetime`, and `camera_photo` (see project config schema).
   * Basic required validations.
4. **Local Saving:** 
   * Collect the data.
   * Save media to disk.
   * Serialize the results into a `Package` JSON and save it to the local SQLite database.
5. **History View (Basic):** 
   * Be able to see a list of locally collected Draft/Completed packages.

## What is OUT of scope for Stage 1:
* **No Real Backend API Integration:** No syncing of configs from servers, and no uploading of packages.
* **No Enriched Data Viewer:** No ML feedback UI yet.
* **No Video Capture:** Videos are complex to handle and chunk; stick to photos first.
* **No Background Workers:** Offline/online queued background syncing is deferred.

*The goal of Stage 1 is strictly to validate the "Dynamic UI Driven by Config" architecture and the user interaction with the step-by-step wizard.*
