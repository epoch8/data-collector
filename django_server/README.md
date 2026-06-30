> **Language / Язык:** **English** · [Русский](README.ru.md)

# django_server

Monolith: mobile API and web admin on **Django templates** (Bootstrap + `admin.css`).

## Roles

| Role | Sign-in | Where projects are assigned | UI |
|------|---------|-------------------------------|-----|
| **Admin** | `/ui/login/` — **Admin access** checkbox, login without `@`, Django **staff** | — | Projects, Users, Packages |
| **Client** | `/ui/login/` — no checkbox, **email** + Firebase | Users → **Client-admin** checkboxes | Packages |

There are no separate Django "web users" — only Firebase + Client-admin column in the users table.

## Launch

```bash
cd django_server
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- Sign-in: http://127.0.0.1:8000/ui/login/
- Projects (staff): http://127.0.0.1:8000/ui/projects/

### Projects and Git

Project config is **not stored in the DB** — only in a GitHub repository: `collector/config.json` (see `specs/git-backed-projects.md`).

- When creating a project: repo URL + SSH deploy key (generated on server or paste private key).
- Public key → GitHub → Deploy keys (**Allow write access**).
- "Test Git" button on project card — `git pull` and seed `config.json` if needed.
- Saving in JSON editor = `git commit` + `git push`.
- Clone cache: `project_git_cache/` (or `PROJECT_GIT_CACHE_ROOT`).
- Requires **git** and **ssh-keygen** in PATH; `pip install -r requirements.txt` (`cryptography` package).

Migration `0006_git_backed_projects` removes old `Project` records from the DB (clean start).
- Packages: http://127.0.0.1:8000/ui/packages/

Packages are fully on **Django templates + Bootstrap**, no frontend build required:

- **List** — `ui/packages/list.html`: project selector, status chips, search by field (text/datetime) or ID/email, dynamic column, `package_id` copy. Server-side filtering (GET params).
- **Workspace** — `ui/packages/workspace.html`: sidebar package switcher, tabs **Data / Media / Visualization / Change history**, change tracking and save via POST (`package_manifest_save` + changelog in project SQLite).
- **Visualization** — config in Git: `collector/viz.json` (layers → `table` in project SQLite + `plugin`). Plugins: `keypoint_korovas`, `depth_map`, `cvat_link`, `yolo_detection`. Import: `import_yolo_labels`, `import_depth_map`, `import_cvat_link`. UI: `packages_viz.js` → `/viz-data/`. Example config: `examples/collector/viz.json`; install to git cache: `install_vis_config_example`. Spec: `specs/collector-vis-config.md`.

### Package storage (per project)

Metadata and pipeline — **per-project DB** (`database_uri`, default SQLite in `project_db/{project_id}/`). Blobs — **fsspec** (`storage_uri`, default `project_media/{project_id}/`). See `specs/project-storage-uris.md`.

- Tables: `package_session`, `uploaded_blob`, `package_field_change` + pipeline (yolo, depth, …).
- Blob path: `packages/{package_id}/blobs/...` relative to `storage_uri`.
- Legacy `media_bucket` deprecated → `storage_uri` (`gs://…`).
- Migration from Django ORM: `migrate_packages_to_project_storage`, `recover_legacy_packages`.

Server logic — `api/packages_ui.py` and `api/views_ui.py`.

## Static assets

- `api/static/ui/admin.css` — shared theme
- `api/static/ui/packages.css`, `packages_viz.css` — package styles
- `api/static/ui/packages_list.js`, `packages_workspace.js`, `packages_viz.js` — package logic
- `api/static/ui/project_builder.js` — visual config editor
- `api/static/ui/login.js` — Firebase sign-in on login page (without "Admin access" checkbox)
