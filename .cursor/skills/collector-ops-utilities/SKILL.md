---
name: collector-ops-utilities
description: >-
  Runs Data Collector ops utilities: photo export from S3/MinIO, project
  backup/restore, and manual datapipe stage triggers. Use when the user asks
  to export photos, backup a project, restore a backup into local test_dev,
  dump blobs, re-run pipeline stages, on_commit, or follow course guide
  utilities.md / tools/photo-export / tools/project-backup / lab-restore-backup.
  Also when the user says "по скиллу collector-ops-utilities".
---

# Collector ops utilities

Course guide (if nearby): `korovas-ops-course/03-demo/guides/utilities.md`  
Tool docs: `tools/photo-export/README.md`, `tools/project-backup/README.md`  
Datapipe local run: `docs/architecture/local-run-korovas-datapipe.ru.md`

## Hard rules

- Prefer read-only export/backup. Do not run restore / `--wipe` / `purge_packages` unless the user explicitly asks.
- Never commit `.env`, AWS keys, or service account JSON.
- Ask for missing: `DATABASE_URL`, S3 endpoint/bucket/creds, `project_id`, Git remote, output directory.

## Pick a workflow

| User intent | Workflow |
| --- | --- |
| Скачать фото по животным/ракурсам | A. Photo export |
| Полная копия проекта локально | B. Backup |
| Восстановить бэкап на локальный стенд | C. Restore (explicit; localhost only) |
| Перезапустить datapipe stage | D. Pipeline trigger |

---

### A. Photo export

```
- [ ] 1. cd tools/photo-export && pip install -r requirements.txt
- [ ] 2. Ensure DATABASE_URL + S3 creds (.env or env vars)
- [ ] 3. Optional: python download_photos_from_s3.py list --endpoint-url … --bucket …
- [ ] 4. python export_manifests.py -o manifests.jsonl --all-phases
- [ ] 5. python download_photos_from_s3.py download --manifests manifests.jsonl --output <dir> --animal-field cow_name --skip-existing
- [ ] 6. Show user output path + _export_index.csv
```

Default animal field for Korovas: `cow_name` (confirm if other project).

---

### B. Backup

```
- [ ] 1. cd tools/project-backup && pip install -r requirements.txt
- [ ] 2. Collect DATABASE_URL, bucket, endpoint, git-remote, output dir
- [ ] 3. Dry-run: python backup_project.py backup … --dry-run
- [ ] 4. Full: same without --dry-run, add --skip-existing
- [ ] 5. python backup_project.py verify <output>
```

Backup = project Postgres + S3 prefix + shallow Git. Not Django users/ACLs.

---

### C. Restore (only if asked; localhost only)

Training case: backup folder from Yandex Disk / local path → `restore_project.py` into `test_dev` Postgres + MinIO.

```
- [ ] 1. verify backup: python backup_project.py verify <backup_dir>
- [ ] 2. docker compose -f test_dev/docker-compose.yml up -d
- [ ] 3. dry-run restore (no --yes)
- [ ] 4. Confirm target is localhost (refuse cloud without --allow-remote + explicit user OK)
- [ ] 5. restore with --wipe --yes only after user confirms
- [ ] 6. Print admin URIs; remind user to set project storage in Django UI and open packages
```

`--wipe --yes` clears target project tables. Never point at prod.  
Course lab: `korovas-ops-course/04-engineering/labs/lab-restore-backup.md` (if nearby).

---

### D. Pipeline trigger

1. Confirm Datapipe URL (local demo often `http://localhost:8010`).
2. Prefer UI run if user is learning; else:

```bash
curl -X POST http://localhost:8010/api/run-with-labels \
  -H "Content-Type: application/json" \
  -d "{\"labels\":[[\"stage\",\"packages\"]]}"
```

3. Common stages: `packages`, `annotation`, `train` (match `collector/pipeline.json` / Ops UI).
4. Auto path: package commit + `on_commit` in `collector/pipeline.json`.
5. CVAT annotations come via datapipe stages (no separate export CLI in data-collector).

If the whole stack needs bring-up, point to `docs/architecture/local-run-korovas-datapipe.ru.md` and the korovas datapipe skill. Do not reinvent compose here.

## Aftercare

- Summarize what was run and where files landed.
- Remind: secrets stay out of git.
