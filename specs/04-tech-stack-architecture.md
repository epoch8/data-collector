# Tech Stack & Architecture

## 1. Core Stack
* **Framework:** Flutter (Mobile - Android, iOS).
* **Language:** Dart.

## 2. Global State Management
* **Library: Riverpod** (`flutter_riverpod` with code generation `riverpod_generator`).
* **Why:** Safest compile-time state management, widely adopted, natively handles caching, asynchronous dependencies, and dependency injection seamlessly. Good for separating UI from business logic.

## 3. Local Data Storage
* **Relational Database: drift** (SQLite wrapper).
* **Why:** The app deals with structured, relational data (Projects -> Configs -> Packages). SQLite offers robust querying to filter by status (Draft vs. Uploaded), robust transactions, and type-safe Dart APIs via drift.
* **Binary Data:** `path_provider` for saving photos/videos directly to the application documents directory.

## 4. Networking & API
* **Library: Dio** (`dio`).
* **Why:** Built-in support for interceptors (adding auth tokens automatically, handling 401 token refreshes), and excellent support for chunking and monitoring multipart form file uploads.

## 5. Background Processing
* **Library: `workmanager` or `flutter_background_service`.**
* **Why:** Ensures reliable offline-to-online syncing. If a user finishes a collection deep in a warehouse without WiFi, the app must auto-upload the package when they return to connectivity, even if the app is closed.

## 6. Directory Structure (Proposed)
```text
lib/
├── main.dart
├── core/
│   ├── network/       (Dio setup, interceptors)
│   ├── storage/       (Drift DB definitions)
│   ├── theme/
│   └── utils/
├── models/            (Freezed / JSON Serializable generated models)
├── features/          (Feature-first architecture)
│   ├── auth/          (Login UI, Providers)
│   ├── projects/      (List, Detail, Sync logic)
│   ├── collection/    (Dynamic Wizard, Camera, Forms)
│   └── viewer/        (History, Enriched ML read-only view)
```
