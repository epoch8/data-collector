> **Language / Язык:** **English** · [Русский](web-vs-android.ru.md)

# Web vs Android: key differences

A brief comparison of the same Flutter app on **Web** and **Android**. Business logic and API are the same; the platform and conditional compilation entry points differ (`import …_io.dart` / `…_web.dart`, `kIsWeb`).

## Package data and files

| Topic | Android | Web |
|------|---------|-----|
| **Database (Drift)** | Native SQLite (`sqlite3` + `sqlite3_flutter_libs`) | SQLite in WASM (`web/sqlite3.wasm`, `web/drift_worker.js`) |
| **On-disk package ([spec 07](../../specs/07-package-payload-structure.md))** | Directory `packages/<id>/` with `blobs/` and `payload.json` | Full on-disk layout is **not** built; envelope JSON is stored in the DB, binaries remain as `blob:` / `data:image/…` until upload |
| **`dart:io`** | Available (files, directories) | Not available; separate web implementations |

### Why on-disk packages cannot match Android on web

This is not an arbitrary code difference, but **platform constraints**:

- The browser has **no `dart:io`** — you cannot create directories, `File.copy`, and a `packages/<id>/blobs/` tree the same way as [spec 07](../../specs/07-package-payload-structure.md) on the phone.
- **No equivalent filesystem model** to the Android app: a shot arrives as **`blob:`** / **`data:image/…`** or a file picker selection, not as a stable path in the app directory.
- So on web, the DB stores **envelope JSON** with the same field semantics, and binaries before API upload live in **browser references**, not in a mirror of the on-disk layout.

Making web **fully identical** to the native on-disk directory without different storage (OPFS / IndexedDB and separate code) is **not possible** — that would be a different implementation, not a copy of `dart:io` + `path_provider`.

## Capture and camera metadata

| Topic | Android | Web |
|------|---------|-----|
| **Native intrinsics** | `MethodChannel` → Camera2 / iOS | No channel; block is empty |
| **EXIF** | Read from file after capture (`exif` from file bytes) | Read from shot bytes (`XFile` / `readExifFromBytes`); depends on what the browser provides |
| **Frame quality check** | Enabled (local analysis) | Skipped (`kIsWeb`) |
| **Source selection in `image_picker`** | Camera on mobile platforms | Usually gallery / file picker (browser limits) |

### Native intrinsics in Chrome on a phone

Even if you open the app **in Chrome on a phone**, it is still **web**, not a native APK:

- **Does not pull** the same data as **Camera2 / AVFoundation** via your `MethodChannel` — there is no such bridge for web in this project, so `native_back_camera` is empty.
- **You can rely on something else:** **EXIF and dimensions from the JPEG itself** (if the browser did not strip metadata) — focal length, frame size, orientation, etc. These are **file metadata**, not a "live" OS camera report.
- A separate layer on **MediaDevices / getUserMedia** could be built, but it would not give the same intrinsics set in one call as Camera2 without custom math and without cross-browser guarantees.

## Django sync

| Topic | Android | Web |
|------|---------|-----|
| **Base URL** | Emulator: `http://10.0.2.2:8000`; LAN device: PC IP | Same IP/host as the page is opened from; not `localhost` for a phone on the network |
| **CORS** | Not relevant for native client | Django CORS settings needed for app origin |
| **Package upload to server** | Files from disk via manifest paths (`blobs/…`) | Bytes via `XFile.readAsBytes()`; blob candidates are only real web shot references (not scanning all JSON for strings with `/`) |
| **Instruction images (`/v1/.../assets/...`)** | Disk cache + `Dio` / network | Often `Dio` + `Image.memory` (Firebase Bearer), otherwise 401/`Image.network` limits |

### Images in markdown instructions (same API as the app)

A request to `/v1/projects/.../assets/...` requires the **same Bearer** as the rest of the API (Firebase ID token via `Dio`). **`Image.network`** does not get this token by default (only static `API_BEARER_TOKEN` if set), so without a separate `Dio` fetch you may get **401**. If the first request returns **404** (file not in `project_assets` on the server), do **not** make a second unauthenticated fallback to the same host — otherwise Django logs will show **404 + 401** for one URL.

## Build and debugging

| Topic | Android | Web |
|------|---------|-----|
| **Command** | `flutter run` / `flutter build apk` | `flutter build web` / `flutter run -d web-server` |
| **LAN access to web** | — | `--web-hostname 0.0.0.0`, firewall on web port; for debugging from another device often `--release` due to WebSocket debugging on `127.0.0.1` |

## What's the same

- Collection scenario routes, `wizardStateProvider`, Drift drafts, manifest upload to the same API **after** web-upload implementation.
- Project config, Firebase Auth (if enabled), package spec and form fields.

In summary: **Android** relies on **filesystem and native camera**; **web** on **browser storage/WASM, blob URLs, and network/CORS limits**, with one repository and shared form logic.
