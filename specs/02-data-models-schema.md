> **Language / Язык:** **English** · [Русский](02-data-models-schema.ru.md)

# Data Models & Config Schema

Status: **current** (June 2026). Source of truth for client parsing: `lib/models/project_config.dart`, `collection_flow_resolver.dart`.

## 1. Project JSON (file root)

File `collector/config.json` in the project Git repo (or bundled `assets/config/*.json` for offline demo).

```json
{
  "id": "korovas-2026",
  "name": "Korovas RGB-D Capture",
  "version": "1.0",
  "config": {
    "fields": [ /* see §2 */ ],
    "flow": {
      "steps": [ /* see §3 */ ]
    },
    "ui": { /* optional, see json-driven-collection-ui.md */ }
  }
}
```

- **`id`** — matches `project_id` in Django and in API URLs.
- **`version`** — semantic version for display; server "config version" for cache — Git SHA (`last_synced_sha` → `config_version` in the catalog).

## 2. Fields (`config.fields`)

Registry of all collection fields. JSON keys: **`field_id`**, **`type`**, **`title`**, **`instructions`**, optionally **`validation`**, **`multiple`** (for `camera_photo`), **`options`** (for `single_choice`).

Supported types:

| `type` | Value in payload | Notes |
|--------|-------------------|------------|
| `text_input` | string | `validation.required` |
| `single_choice` | string (`value` of selected option) | Required non-empty `options`: `[{ "value", "label" }]` or strings |
| `datetime` | ISO 8601 string | |
| `instruction` | not written to payload | Markdown in `instructions`; images from `collector/media/` |
| `camera_photo` | map path → metadata | `multiple` + `min_items`; see §5 |

```json
{
  "field_id": "cow_identifier",
  "type": "text_input",
  "title": "Identifier",
  "instructions": "Unique cow code.",
  "validation": { "required": true }
}
```

```json
{
  "field_id": "cow_sex",
  "type": "single_choice",
  "title": "Sex",
  "instructions": "",
  "options": [
    { "value": "bull", "label": "Bull" },
    { "value": "cow", "label": "Cow" }
  ],
  "validation": { "required": true }
}
```

## 3. Flow (`config.flow.steps`)

**Only two screen types** (legacy `form` / `instruction` / `camera_pose` removed):

| `screen` | Purpose |
|----------|---------|
| `scroll_form` | Single scroll screen; fields set via **`field_ids`** (order = on-screen order). |
| `review` | Final check before saving the package. |

Validation rules (server + client):

- Every field from `fields` must appear in **exactly one** `scroll_form` step.
- `scroll_form` must have a non-empty `field_ids`.
- Optional step fields: `form_title` (label on review), `cow_id_hints`, `cow_id_field_id`.

```json
{
  "flow": {
    "steps": [
      {
        "id": "main",
        "screen": "scroll_form",
        "form_title": "Form",
        "field_ids": ["cow_identifier", "scan_notes", "pose_front"]
      },
      {
        "id": "check",
        "screen": "review"
      }
    ]
  }
}
```

Author guide: [config/09-project-json-builder-guide.md](config/09-project-json-builder-guide.md).

## 4. Django ORM (platform catalog)

`django_server/api/models.py`:

| Model | Purpose |
|--------|------------|
| **CollectorUser** | `firebase_uid`, `email`; M2M `mobile_projects` (API `/v1/*`), M2M `admin_projects` (client-admin `/ui/packages/`) |
| **GitCredential** | SSH deploy key (Fernet-encrypted private key) |
| **Project** | `project_id` (PK), `name`, `git_remote`, `git_default_ref`, `git_credential`, `last_synced_sha`, `database_uri`, `database_options_encrypted`, `storage_uri`, `storage_options_encrypted`, deprecated `media_bucket` |

Project config is **not stored** in Django ORM.

## 5. Per-project DB (SQLAlchemy)

Tables in the project DB (`api/project_db.py`, Alembic migrations):

**Package intake:**

- `package_session` — phases `awaiting_blobs` / `ready_to_commit` / `completed` / `failed`
- `uploaded_blob` — logical path + `storage_path` relative to `storage_uri`
- `package_field_change` — changelog of manifest edits in admin

**Pipeline (filled by import / external jobs, not mobile upload):**

- `cow_keypoint_annotation`, `cow_inference_result`, `yolo_detection`, `depth_map`, `cvat_link`

## 6. Flutter local models

| Layer | File | Contents |
|------|------|------------|
| Config | `project_config.dart` | `Project`, `ProjectConfig`, `ConfigField`, `CollectionFlowDecl` |
| Package (DTO) | `package.dart` | `CollectedPackage` |
| Local index | `core/storage/database.dart` (Drift) | `packages`: `id`, `projectId`, `status`, `dataJson`, `serverDeliveryState`, `serverDeliveryError` (schema v3) |

## 7. Package payload (manifest)

Directory structure and JSON — [07-package-payload-structure.md](07-package-payload-structure.md).

Minimal `payload.json` example:

```json
{
  "package_id": "pkg_1234567890",
  "project_id": "korovas-2026",
  "status": "completed",
  "created_at": "2026-04-08T14:22:00Z",
  "data": {
    "cow_identifier": "Bessie-99",
    "scan_notes": ""
  }
}
```

Photo paths in `data` are **relative** (`blobs/...`) after materialization. On the server, `PUT manifest` adds `submitted_by: { firebase_uid, email }`.
