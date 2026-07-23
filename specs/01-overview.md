> **Language / Язык:** **English** · [Русский](01-overview.ru.md)

# Data Collector — Product Overview

Status: **current** (June 2026). Implementation: Flutter client + Django backend (`django_server/`).

## 1. Purpose

**Data Collector** is a data collection **framework**: a mobile app (Flutter, Android/iOS, optionally Web) for collecting structured data and media according to a **dynamic project config**. Packages are saved locally and uploaded to the server. The Django web admin (`/ui/`) lets you manage projects, view packages, and visualize pipeline data (ML, depth, CVAT).

The core is domain-agnostic: concrete scenarios (e.g. cattle capture) are **projects built on the framework** — see [`examples/`](../examples/) and neutral demos in `assets/config/`.

Example deployed instance (korovas project): `https://data-collector-app.korovas.ml.epoch8.dev` — API `/v1/*`, admin `/ui/`. Domain and image names in `Makefile` are values for that specific deployment, not part of the framework.

## 2. Core Entities

| Entity | Description |
|--------|-------------|
| **User** | Data collector. Authenticated via **Firebase Email/Password**; on the server — `CollectorUser` linked to projects. |
| **Project** | Collection initiative. Catalog in Django DB; **config** in a Git repo (`collector/config.json`). See [git-backed-projects.md](git-backed-projects.md). |
| **Config** | JSON schema: `config.fields` + `config.flow.steps` — what to collect and in what order. Guide: [config/09-project-json-builder-guide.md](config/09-project-json-builder-guide.md). |
| **Package** | Work unit: JSON manifest + binary blobs. Locally — Drift + filesystem; on the server — per-project DB + fsspec storage. |
| **Enriched data** | Pipeline results (keypoints, YOLO, depth, CVAT) in the project DB; visualized in admin via `collector/viz.json`. |

## 3. Key Features (implemented)

### 3.1 Authentication

- Firebase Email/Password on the client; `Authorization: Bearer <ID token>` on `/v1/*`.
- Web admin: Django staff (login without `@`) or Firebase client-admin (assigned projects only).
- Offline mode without `API_BASE_URL`: bundled `assets/config/` with no auth.

### 3.2 Projects and configs

- Catalog `GET /v1/projects` with ETag; full config `GET /v1/projects/{id}/config` (source — Git, ETag = `last_synced_sha`).
- Device cache: `ApplicationSupport/server_project_cache/`.
- Instruction media: `GET /v1/projects/{id}/assets/{path}` from `collector/media/` in Git.

### 3.3 Data collection

- UI built from `config.flow.steps`: **`scroll_form`** steps (all step fields on one screen) and optional **`review`**.
- Field types: `text_input`, `single_choice`, `datetime`, `instruction`, `camera_photo`.
- Local draft and materialization into the package directory on submit.
- Camera metadata: `camera_session`, `camera_debug`, `frame_camera`, `camera_supplement` (see [07-package-payload-structure.md](07-package-payload-structure.md)).

### 3.4 Server upload

- Protocol: `POST` session → `PUT` blobs → `PUT` manifest → `POST` commit ([08-server-api-package-upload.md](08-server-api-package-upload.md)).
- Upload is **manual** from the **Server** tab (`ServerSyncTab`); background workmanager — not implemented.
- Delivery statuses in Drift: `pending` / `uploading` / `completed` / `failed`.

### 3.5 History and admin

- Local package history with server delivery status indication.
- Django `/ui/packages/`: list, workspace (Data / Media / Visualization / Changelog), filters, manifest editing.

## 4. Architecture

```text
┌─────────────────┐     HTTPS /v1/*      ┌──────────────────────────────────┐
│  Flutter app    │ ◄──────────────────► │  django_server                   │
│  Riverpod+Drift │     Firebase Bearer    │  API + /ui/ (Django templates)   │
└─────────────────┘                        │  Catalog DB (Postgres/SQLite)    │
                                           │  Per-project: SQLAlchemy + fsspec│
                                           │  Config: Git cache               │
                                           └──────────────────────────────────┘
```

- **Client:** Flutter, Riverpod, Drift (SQLite), Dio, GoRouter, Firebase Auth.
- **Catalog server:** Django 5.x ORM — `Project`, `CollectorUser`, `GitCredential`.
- **Project data:** SQLAlchemy 2.x + Alembic (`database_uri`); blobs via fsspec (`storage_uri`). See [project-storage-uris.md](project-storage-uris.md).
- **Project config:** Git SSH deploy key → `collector/config.json`, `collector/media/`, `collector/viz.json`.

## 5. Client operating modes

| Mode | Condition | Project source |
|------|-----------|----------------|
| Offline / demo | `API_BASE_URL` not set | `assets/config/projects.json` + bundled JSON |
| Online | `--dart-define=API_BASE_URL=...` | Server only (`ServerProjectCatalog`) |

## 6. Known limitations and backlog

See [todo](todo). In brief:

- No background auto-upload of packages (workmanager).
- Web client: known issue with Firebase credentials.
- Admin: no package deletion, raw JSON view, or linking photos to form fields.
- Enriched data in the mobile app — not implemented (web admin only).

## 7. Related documents

| Topic | File |
|------|------|
| Models and JSON schema | [02-data-models-schema.md](02-data-models-schema.md) |
| App screens | [03-user-journey-screens.md](03-user-journey-screens.md) |
| Stack and code structure | [04-tech-stack-architecture.md](04-tech-stack-architecture.md) |
| MVP (history) | [05-stage-1-mvp.md](05-stage-1-mvp.md) |
| Package upload | [06-upload-lifecycle.md](06-upload-lifecycle.md), [08-server-api-package-upload.md](08-server-api-package-upload.md) |
| Config delivery | [09-server-project-config-delivery.md](09-server-project-config-delivery.md) |
| Git config | [git-backed-projects.md](git-backed-projects.md) |
| Project storage | [project-storage-uris.md](project-storage-uris.md) |
