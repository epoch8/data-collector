# Data Collector App - Specification Document

## 1. Overview
The **Data Collector** is a Flutter-based mobile application designed to securely and efficiently collect rich data (photos, videos, and structured metadata) based on dynamic, project-specific configurations. The app packages the collected assets and uploads them to a central backend server. It also allows users to review previously collected data and inspect enriched results (such as ML predictions) returned by the backend.

## 2. Core Concepts
* **User:** Ground-truth data collector who logs into the system.
* **Project:** A specific collection initiative. Users are assigned to one or more projects.
* **Config:** A dynamic schema attached to a project that dictates *what* data must be collected (e.g., "Take 3 photos of an item, 1 video of it rotating, and enter its serial number"). Authoring reference: [config/09-project-json-builder-guide.md](config/09-project-json-builder-guide.md).
* **Package:** A compiled unit of work containing the specific media and structured info collected for a single instance according to the Config.
* **Enriched Data:** Results, annotations, or ML predictions provided by the backend after a Package has been successfully uploaded and processed.

## 3. Key Features

### 3.1 Authentication & User Management
* Secure login (email/password, SSO, etc.).
* Token-based authentication with secure local storage.
* Graceful handling of expired sessions.

### 3.2 Projects Dashboard
* View a list of assigned/available Projects.
* Display high-level stats (e.g., packages collected today, pending uploads).
* Sync and cache project definitions and Configs for offline use.

### 3.3 Dynamic Data Collection Flow
* UI dynamically generated based on the Project's Config.
* **Guided Collection & Instructions:**
  * Step-by-step guided flow to walk the user sequentially through the exact data required for a new package.
  * Clear user instructions and hints can be displayed for each collection step (driven by the project config).
* **Media Capture:**
  * Integrated custom camera for photos and videos.
  * Real-time validation (e.g., length of video, number of required photos).
* **Structured Info:**
  * Forms supporting text inputs, numerical values, dropdowns, and checkboxes.
* Local auto-save/draft functionality to prevent data loss during active collection.

### 3.4 Packaging & Upload Management
* Bundling of media files and JSON metadata into a structured payload (Package).
* Reliable background uploader:
  * Chunked file uploads for large video files (if supported by backend).
  * Auto-resume capabilities for lost network connections.
  * Visual queue showing the status of uploads (Pending, Uploading, Failed, Completed).

### 3.5 History & Enriched Data Viewer
* Browse history of collected Packages within a specific Project.
* Filter packages by status (Draft, Uploaded, Processed).
* **Enriched View:** Upon backend processing, the app can fetch ML predictions (e.g., detected objects, OCR results, validation failures) and display them alongside the original package data. This could include drawing bounding boxes over the original uploaded images or showing parsed text.

## 4. Technical Architecture (Proposed)

* **Framework:** Flutter (Targeting Android/iOS).
* **State Management:** Riverpod, BLoC, or Provider (depending on team preference and complexity).
* **Local Storage & Database:** 
  * *Relational Data:* drift or sqflite for caching Projects, Configs, and metadata.
  * *Binary Data:* Local file system for staging photos/videos.
  * *Key-Value:* `flutter_secure_storage` for auth tokens.
* **Networking:** `dio` for handling standard REST APIs and complex multipart background uploads with interceptors for auth and retry logic.
* **Camera:** `camera` plugin for low-level control, or `image_picker` / `record` if standard OS UI is sufficient.

## 5. Security & Offline Capabilities
* **Offline-First Data Entry:** Projects and Configs are cached. Data can be entirely collected and saved locally without an internet connection.
* **Secure Storage:** Sensitive data and credentials are encrypted.

## 6. Open Questions / Next Steps
* **Config Format:** What does the exact JSON schema for the UI Config look like? (e.g., forms rendering engine like JSON Schema).
* **Enriched Data Tools:** The app will eventually provide a suite of tools for both read-only visualization and active tweaking/correction of the enriched ML data (e.g., modifying bounding boxes). For Stage 1, the app will strictly focus on read-only visualization.
* **Backend API Approach:** The Backend API will be developed in parallel with the app. The app's needs and network payloads (e.g., chunked uploads, JSON syncing) will dictate and shape the exact API contract.
