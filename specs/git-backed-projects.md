> **Language / Язык:** **English** · [Русский](git-backed-projects.ru.md)

# Git-backed projects (project config in repository)

Status: **implemented** (June 2026). Code: `django_server/api/project_git.py`, `project_config_service.py`, migration `0006_git_backed_projects`.

## Decisions (v1)

| # | Question | Decision |
|---|----------|----------|
| 1 | Repository ↔ project | **1 repository = 1 project** |
| 2 | Connection | SSH deploy key; private key Fernet-encrypted in `GitCredential` |
| 3 | Keys | **Separate deploy key per project** |
| 4 | Config path | **`collector/config.json`** (constant `CONFIG_REL_PATH`) |
| 5 | Example media | **`collector/media/`** in the same repo |
| 6 | Git failure | **Hard error** — no serving stale config from Django |
| 7 | Who changes config | **Django UI** → `git commit` + `git push` |

## Django DB (catalog)

**Project** model — pointer to Git, **without** `raw_json`.

| Field | Purpose |
|-------|---------|
| `project_id` (PK) | = `id` in `collector/config.json` |
| `name` | For lists |
| `git_remote` | SSH URL (`git@github.com:org/repo.git`) |
| `git_default_ref` | Branch, default `main` |
| `git_credential` | FK → `GitCredential` |
| `last_synced_sha`, `last_synced_at`, `sync_error` | Sync diagnostics |
| `database_uri`, `storage_uri`, `*_options_encrypted` | Per-project data storage (see [project-storage-uris.md](project-storage-uris.md)) |
| `media_bucket` | **Deprecated** → `storage_uri` |

**Not in Git:** packages, blobs, Firebase users, `CollectorUser` permissions.

## Repository layout

```
my-project/
  collector/
    config.json       # Project JSON (fields, flow, ui)
    media/            # static assets for instructions
    viz.json          # admin visualization (optional)
```

## Server cache

```
{PROJECT_GIT_CACHE_ROOT}/{project_id}/
```

Default: `django_server/project_git_cache/`.

- Before read/write: `git fetch` + hard reset to `origin/{ref}`.
- Pull rate limit: `PROJECT_GIT_PULL_MIN_INTERVAL_SEC` (default 300s), `force=True` in admin.
- On error — 502/503, **no** fallback to old JSON.

## Flows

### Project creation (staff)

`/ui/projects/new/`: `project_id`, name, GitHub URL → SSH, deploy key (generate or paste OpenSSH; `.ppk` rejected).

1. `GitCredential` + `Project`.
2. `git ls-remote` / shallow clone — access check.
3. Seed `collector/config.json` if missing (with write key).
4. Optional: "Data storage" block (Postgres / S3 / GCS).

### Read (mobile, admin)

1. Pull into cache.
2. Read + validate `collector/config.json`.
3. API: raw JSON; **ETag** = `last_synced_sha`.

Media: `GET /v1/projects/{id}/assets/{path}` from `collector/media/`.

### Config change

`/ui/projects/{id}/config/` (JSON editor) or `/config/builder/` (visual):

1. Pull.
2. Write file + validate (`project_config_validate.py`).
3. `git add` → `commit` → `push origin HEAD:{ref}`.
4. Update `last_synced_sha`.

Non-fast-forward conflict → error to user (merge UI — backlog).

### Media in Git

`/ui/projects/{id}/media/` — upload/delete → commit in `collector/media/`.

## API

| Endpoint | Behavior |
|----------|----------|
| `GET /v1/projects` | Catalog; `config_version` = SHA prefix |
| `GET /v1/projects/{id}/config` | Raw JSON; ETag = SHA; `304` |
| `GET /v1/projects/{id}/assets/{path}` | Binary from git cache |

Admin JSON API: `/ui/api/v1/projects/{id}/config`.

## Migration from legacy

- `0006_git_backed_projects` — removes old `Project` without Git.
- Bundled `assets/config/` — client offline fallback only, not server source of truth.

## Backlog (outside v1)

- GitHub webhook for auto-pull.
- Pin `config_git_sha` on `PackageSession`.
- Monorepo (multiple projects in one repo).
- HTTPS + PAT instead of SSH.
