> **Language / Язык:** **English** · [Русский](09-server-project-config-delivery.ru.md)

# 9 — Server delivery of project configs (catalog, first launch, package binding)

Status: **current** (June 2026). Config is **Git** (`collector/config.json`), not Django DB. See [git-backed-projects.md](git-backed-projects.md).

This document describes **where the mobile app gets the project list and full JSON configs**, how that aligns with **creating intake tables on the server**, and **how the server unambiguously identifies the project** when accepting a package from the client.

**Related documents:** [08-server-api-package-upload.md](08-server-api-package-upload.md) (package upload, `project_id` in URL), [07-package-payload-structure.md](07-package-payload-structure.md) (`project_id` in `payload.json`), [config/json-driven-collection-ui.md](config/json-driven-collection-ui.md) (`Project` model and JSON parsing on client), [config/09-project-json-builder-guide.md](config/09-project-json-builder-guide.md) (how to build project JSON).

**Diagram:** [09_server_project_config.drawio](09_server_project_config.drawio) — admin/server, client first launch, config delivery, package intake.

---

## 1. Goals

- On **first app open** (and on updates) the user sees an **up-to-date project list** allowed on the server, **without manually building** `assets/config/`.
- Project config on the server is the **source of truth** for collection UI (same fields as local JSON in `json-driven-collection-ui`).
- Creating/changing config on the server is **aligned** with the **accepted package storage schema** (table or equivalent for that `project_id`).
- On **package intake** the server **always** knows the target project: from route, manifest body, and subject access rights.

---

## 2. Terms

| Term | Meaning |
|------|---------|
| **Project catalog** | List of entries `{ project_id, name, config_version, updated_at, … }` for the project picker screen. |
| **Full config** | JSON document parseable into `Project` on the client (like a `*.json` file from `assets/config/`). |
| **config_version** | In catalog — short Git SHA prefix (`last_synced_sha[:12]`). Field `version` in JSON — for display in the app. |
| **Package intake** | Sequence from spec `08`: session, blobs, manifest, `commit`. |

---

## 3. First launch and project list display

1. User opens the app after install.
2. Client performs **authentication** (if enabled): token limits accessible `project_id` (as for upload in `08` §12).
3. Client requests **project catalog** from server (see §6).
4. Response saved in **local cache** (e.g. SQLite / files in `ApplicationSupport`): list for UI + version metadata.
5. For each project in the catalog the client ensures a **full config** exists (see §7): if missing or stale — download, then parse into `Project`.
6. **Dashboard** built from **cached** `Project` (analog of current `projectsProvider`, but source is server, not only `rootBundle`). In this repo: `ServerProjectCatalog` (`lib/features/projects/server_project_catalog.dart`), cache in `ApplicationSupport/server_project_cache/` (`catalog.json`, `configs/<project_id>.json`, ETag in metadata).

**Offline after first successful sync:** show last cached catalog and configs; indicate "data may be stale" if no network and time since last sync elapsed (product details).

---

## 4. Server: from config to intake storage

Chain (implemented):

1. **Project** in Django: `project_id`, Git remote, deploy key, `database_uri` / `storage_uri`.
2. **Config** — commit in Git (`collector/config.json`); `git push` updates `last_synced_sha`.
3. **Intake schema** — fixed SQLAlchemy tables (`package_session`, `uploaded_blob`, …) in per-project DB; Alembic `upgrade head` on first access / "Verify storage".
4. **Publication:** `GET …/config` after `git pull` into cache; **ETag** = full SHA; client — `If-None-Match` → `304`.

No automatic projection of config fields into DB columns — manifest stored as JSON; pipeline tables filled by separate imports.

---

## 5. Package intake: which project receives data

Server determines project in **three layers** (all must agree):

| Layer | Where | Requirement |
|-------|-------|-------------|
| **Route** | `…/projects/{project_id}/packages/…` | `project_id` from path — primary key for session routing and storage. |
| **Manifest** | `payload.json` root | Field **`project_id`** (see `07` §4.1) **must match** `project_id` in URL. |
| **Authorization** | Token / session | Subject has **write** right to this `project_id`. |

On **`project_id` mismatch** between URL and JSON → **`422`** with explicit code (e.g. `project_id_mismatch`).  
If `project_id` missing in JSON when product requires double check → **`422`**.  
Result: processing queue and intake table writes always in context of **one** `project_id` from path; manifest is integrity control.

Additionally the client when creating a package locally **binds** the draft to the selected project (same `project_id`) so outbox scenarios do not mix.

---

## 6. API: project catalog (list for UI)

**Purpose:** lightweight response for first screen without heavy JSON.

Recommended form: `GET /v1/projects` or `GET /v1/me/projects`.

**Response (logic):**

- List items: at minimum each has `project_id`, `name`, `config_version`, `updated_at` (ISO 8601). Convenient wrapper for parsing — object **`{"projects": [ … ]}`** (as Django reference server returns; raw array also acceptable in product).
- Optional: `description`, icon URL, read-only flags, quotas.

**In Django reference:** single route **`GET /v1/projects`**. With Firebase enabled list **filtered** by projects assigned to `CollectorUser` (no separate `GET /v1/me/projects`). Field `config_version` stored as **string**.

**Caching:** **`ETag`** or **`If-None-Match`** headers on full list; on `304` client does not re-download list but may still check individual configs by version.

**Codes:** `401` / `403` as in `08` §13; empty list — valid `200` (no accessible projects).

---

## 7. API: full project config

**Purpose:** response body must be **compatible** with `Project.fromJson` parser (see `json-driven-collection-ui`).

Recommended form: `GET /v1/projects/{project_id}/config`.

**Response headers:** `ETag` (hash or `"{config_version}"`), optionally `Last-Modified`.

**Client request:** `If-None-Match` — on match **`304`**, local cache remains valid.

**Body:** one project JSON object (root with `id`, `name`, `version` / `config_version`, `config` with `fields`, `flow`, `ui` — as in guide `09-project-json-builder-guide`).

**Consistency:** `id` in JSON **must** match `{project_id}` in path; otherwise client rejects config as corrupt (`422` on server preferable to mismatch on device).

**In Django reference:** on config save via admin UI server validation runs (`api/project_config_validate.py`); on `GET …/config` body is saved `raw_json` without re-checking `id` (client must still reconcile with path).

### 7.1. Media by relative paths from config *(optional)*

If project JSON has links to example files (not embedded in app asset bundle), a separate **binary** read route on server is convenient, e.g.:

`GET /v1/projects/{project_id}/assets/{asset_path}`

where `asset_path` — relative path without `..` (as files copied from repository into server storage). **In Django reference** implemented in `ProjectAssetGetView`; client URL building — `lib/features/collection/presentation/flow/project_example_image.dart`.

---

## 8. Alternative: one bundle for weak network

`GET /v1/catalog` — combined response: project list + embedded full configs **or** list only with URL per config. Useful for single round-trip on first launch; response size and timeouts must be limited.

---

## 9. Client: how config is fetched and stored

1. After `GET /v1/projects` client compares `config_version` with cache per `project_id`.
2. For new or changed — `GET /v1/projects/{id}/config` with `If-None-Match`.
3. Successful response → write to local storage (file per project or single DB table `project_id → json + etag + fetched_at`).
4. Parse into `Project` — same code as asset path. With `API_BASE_URL` set **server only** (`project_providers.dart`); bundled assets — only without API.

---

## 10. Interaction order (brief)

1. **Admin** saves config to Git via `/ui/projects/{id}/config/` → push → new SHA / ETag.
2. **Client** on start: auth → catalog → config download → UI.
3. **Collection:** user picks project from list → package formed with that project's `project_id`.
4. **Upload:** all requests under `/v1/projects/{project_id}/packages/…`; manifest contains same `project_id`.

---

## 11. Non-functional requirements

- TLS, API version in path prefix (`/v1/`), JSON config size limits.
- Audit: who changed config, `config_version`, publication time.
- Protection from too frequent full downloads: `ETag`, CDN (optional).

---

## 12. Open decisions (fix in OpenAPI)

1. Separate endpoint for **draft config preview** in admin before publication.
2. **Migration** strategy on field type change (strict vs new packages only).
3. Mandatory **`project_id` in manifest body** when URL is already unambiguous (recommended **mandatory** for duplicate control and offline queue).

After decisions — **OpenAPI 3.1** for `GET /v1/projects`, `GET /v1/projects/{project_id}/config` and cross-references with `08`.

---

## 13. Repository reference (summary)

| Area | Code location |
|------|---------------|
| API routes | `django_server/api/urls.py` |
| Catalog, config, assets | `django_server/api/views.py` — `ProjectsCatalogView`, `ProjectConfigView`, `ProjectAssetGetView` |
| Import from `assets/config/` to DB | **removed** — projects only via `/ui/projects/new/` + Git |
| Git sync | `api/project_git.py`, `project_config_service.py` |
| Per-project storage | `api/project_storage_config.py` — see `project-storage-uris.md` |
| Client: catalog and config sync, ETag / 304 | `lib/features/projects/server_project_catalog.dart` |
| Client: package upload by `project_id` from URL and manifest | `lib/features/collection/logic/package_server_upload.dart` (see spec `08`) |
