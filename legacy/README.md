> **Language / Язык:** **English** · [Русский](README.ru.md)

# legacy/

Everything that **does not participate in the main pipeline** of data_collector
(Flutter client + `django_server/`) but is kept for history and reference.

The move was done as part of repository cleanup. Main application behavior was not changed.

## What's here

| Folder/file | What it is | Moved from |
|-------------|------------|------------|
| `cowmetric/` | Separate ML project (pipeline/minio/cvat/core server-app). Nested git repository with its own history. | repo root (was a gitlink) |
| `korovas/` | Separate ML project (jetson-web-ui, depth/keypoints experiments, demo_app). Nested git repository with its own history. | repo root (was a gitlink) |
| `client-admin/` | Planned separate "Client Admin" web portal. Git only had accidental Windows binaries from `node_modules`/`.vite`, no source code. Role covered by Django `/ui` Packages tab. | repo root |
| `mock_server/` | Reference Shelf server for specs 08–09 (Dart). Not production. | repo root |
| `samples/` | Heavy sample images (visualizations) that lived in repo root. | repo root |
| `presentation-archive/` | Old product presentation versions. Canonical — `specs/presentation/Data-Collector-Canva-Template-v4.pptx`. | `specs/presentation/` |

## About `cowmetric/` and `korovas/`

They were previously connected as **gitlinks** (mode `160000`) without `.gitmodules`,
so on a clean clone they appeared empty. Now they are regular local folders,
not tracked by the main repository (see `.gitignore`). Their own
git history is preserved inside their `.git`. If version control is needed —
manage them as separate repositories or set up proper submodules.
