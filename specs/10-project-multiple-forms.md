> **Language / Язык:** **English** · [Русский](10-project-multiple-forms.ru.md)

# 10 — Multiple forms per project

Status: **in progress** (July 2026). MVP: form discovery, `/forms` API, mobile picker, `form_id` in manifest, admin package filter. Product context: [docs/mobile-revisions-2026-07-17/README.md](../docs/mobile-revisions-2026-07-17/README.md) §2–5.

**Related:** [git-backed-projects.md](git-backed-projects.md), [09-server-project-config-delivery.md](09-server-project-config-delivery.md), [02-data-models-schema.md](02-data-models-schema.md), [07-package-payload-structure.md](07-package-payload-structure.md), [collector-vis-config.md](collector-vis-config.md), [03-user-journey-screens.md](03-user-journey-screens.md).

---

## 1. Goals

- Keep **one project** = one farm / initiative = **one** package DB + **one** blob storage (`database_uri` / `storage_uri`).
- Allow **several collection forms** inside that project (different field sets / flows), without `show_if` branching inside a form.
- Operator **chooses a form** after opening the project; choice of form = choice of scenario (e.g. animal type).
- Every package records **which form** produced it; admin can filter and edit by that form’s schema.
- Visualizations / pipelines can target **one or many** forms.

Non-goals (v1 of this feature):

- Conditional fields / flow branching (`show_if`) inside a form.
- Splitting cattle (bull / young / cow) content into three forms yet — first ship the **mechanism**; migrate today’s single config to one form (`default`).
- Per-form user ACL (all forms of a project inherit project mobile access).

---

## 2. Terms

| Term | Meaning |
|------|---------|
| **Project** | Catalog + Git repo + storage (unchanged). |
| **Form** | One collectible scenario: its own `config.json` (`fields` + `flow` + optional `ui`). Identified by `form_id`. |
| **Form picker** | Mobile screen after project selection: list of form **names** only. |
| **Default form** | `form_id = "default"`. Used for legacy single-config repos and packages without `form_id`. |

---

## 3. Decisions

| # | Question | Decision |
|---|----------|----------|
| 1 | Storage of forms | **Separate files** under `collector/forms/{form_id}/config.json` |
| 2 | Legacy single file | `collector/config.json` still readable → treat as form `default` |
| 3 | Form identity | `form_id`: slug (`[a-z0-9_]+`), stable; display `name` from JSON root `name` (or optional `form_title`) |
| 4 | Operator UX | Project → **form picker (names only)** → same scroll_form / review flow as today |
| 5 | Mid-session switch | **Not allowed**; form fixed when package/draft is created |
| 6 | Draft resume | Resume existing draft for that project+form; starting new collection shows picker again |
| 7 | Package binding | Manifest must include **`form_id`** (and should include `form_name` / `form_version` for display) |
| 8 | Field uniqueness | `field_id` unique **within a form**; different forms may reuse the same `field_id` |
| 9 | Old packages | Missing `form_id` → treat as **`default`** |
| 10 | Admin packages | Still scoped by `project_id`; add form filter + column; edit Data tab using **that form’s** fields |
| 11 | Visualizations | Multiple viz configs; each lists `form_ids` (one viz may bind to several forms) |
| 12 | Pipelines | Same idea: job/config declares which `form_id`(s) it applies to |
| 13 | Branching | **Out of scope** — different scenarios = different forms |
| 14 | Scoring scales | Product content inside forms (fields), not a new platform widget in this spec |

---

## 4. Git repository layout

```text
my-project/
  collector/
    forms/
      default/
        config.json       # full Project JSON (id/name/version/config.fields|flow|ui)
      # later examples:
      # bull/config.json
      # young/config.json
      # cow/config.json
    media/                # shared instruction assets (unchanged)
    visualizations/
      keypoints.json      # see §7
    # LEGACY (still supported for read):
    # config.json
    # viz.json
```

### 4.1 Form `config.json`

Same shape as today’s project JSON ([02-data-models-schema.md](02-data-models-schema.md)):

```json
{
  "id": "krs-label",
  "name": "Bull producer",
  "version": "1.0",
  "config": {
    "fields": [ /* ... */ ],
    "flow": { "steps": [ /* ... */ ] },
    "ui": { }
  }
}
```

Rules:

- Root **`id`** should match Django `project_id` (same as today).
- Root **`name`** is the **form display name** in the picker (not necessarily the project catalog name).
- Project catalog display name remains Django `Project.name` (or a future project-level metadata file — out of scope).
- Validation of each form file: same rules as current `validate_project_payload` (fields, flow, `review` last, etc.).

### 4.2 Discovery

Server lists forms by scanning `collector/forms/*/config.json`.

Compatibility:

1. If `forms/` has ≥1 valid form → use that set.
2. Else if `collector/config.json` exists → one form `{ form_id: "default", config: <file> }`.
3. Else → error (no config).

Optional later: `collector/forms/index.json` ordering/titles; v1 order = alphabetical by `form_id`, with `default` first if present.

---

## 5. Package payload

Extend [07-package-payload-structure.md](07-package-payload-structure.md).

Root of `payload.json` / uploaded manifest:

| Field | Required | Notes |
|-------|----------|--------|
| `project_id` | yes | Unchanged; must match URL |
| `form_id` | yes (new packages) | Slug; server may default missing → `default` for legacy |
| `form_name` | recommended | Snapshot of form display name at collect time |
| `form_version` | recommended | Snapshot of form JSON `version` |
| `created_at` | yes | Unchanged |
| `data` | yes | Field values for **this form only** |

Upload validation:

- Unknown `form_id` for project → **`422`** `unknown_form_id` (after forms layout is mandatory in prod; during migration, missing form may map to `default` only if legacy file exists).
- `form_id` in URL is **not** required in v1 (project-scoped upload paths stay as today); form comes from manifest.

Local Drift row: store `form_id` (and optionally `form_name`) alongside `projectId` for history/upload queue UI.

---

## 6. API and client sync

### 6.1 Catalog `GET /v1/projects`

Each project entry gains:

```json
{
  "project_id": "krs-label",
  "name": "Korovas Scan",
  "config_version": "abc123def456",
  "forms": [
    { "form_id": "default", "name": "Korovas Scan", "version": "1.0" }
  ]
}
```

- `forms` is summary only (no full fields/flow).
- ETag / `config_version` still tracks Git SHA of the project repo (any form or viz change bumps sync).

### 6.2 Forms bundle (preferred for mobile)

`GET /v1/projects/{project_id}/forms`

Response:

```json
{
  "project_id": "krs-label",
  "config_version": "abc123def456",
  "forms": [
    {
      "form_id": "default",
      "config": { /* full Project JSON */ }
    }
  ]
}
```

- ETag = `last_synced_sha`.
- Client caches under `server_project_cache/forms/<project_id>/` (or one `forms.json` bundle).
- Offline: use last cached bundle.

### 6.3 Single form (optional)

`GET /v1/projects/{project_id}/forms/{form_id}/config`

Same body as one form’s JSON; useful for admin preview. Mobile sync should use §6.2.

### 6.4 Legacy

`GET /v1/projects/{project_id}/config` remains for one release:

- If multi-form layout → return **default** form config (or 300-style deprecation header).
- Prefer clients migrate to `/forms`.

---

## 7. Visualizations

Replace single mandatory `collector/viz.json` with:

```text
collector/visualizations/{viz_id}.json
```

Each file:

```json
{
  "id": "keypoints",
  "title": "Keypoints",
  "form_ids": ["default"],
  "layers": [ /* same layer model as today’s viz.json */ ]
}
```

Rules:

- `form_ids`: non-empty list of form slugs this viz applies to.
- One viz may list many forms; many viz files may reference the same form.
- Admin package Visualization tab: show viz entries whose `form_ids` contain the package’s `form_id` (legacy package → `default`).
- Legacy: if only `collector/viz.json` exists → treat as `{ id: "default", form_ids: ["default"], ...contents }`.

Pipelines / imports (out of detailed scope here): configuration should similarly declare `form_ids` (or a single `form_id`) so metrics land in the right interpretation context.

---

## 8. User journeys

### 8.1 Mobile

1. Sign in → project list (as today).
2. Open project → **Form picker** (names from cached `forms` summary).
3. If project has **exactly one** form → skip picker (optional UX optimization; still write that `form_id` on the package).
4. Collect → review → local package with `form_id`.
5. Upload queue / history: show project name + form name.

### 8.2 Admin builder

- Project config UI becomes a **list of forms**; each opens the existing visual builder against `forms/{form_id}/config.json`.
- Actions: add form, rename display name, delete form (block delete if `form_id` still referenced by packages — product policy TBD; v1 may allow delete with warning).
- Seed new project: create `forms/default/config.json` (stop writing root `config.json` for new seeds).

### 8.3 Admin packages

- List: column + filter `form_id` / form name (within selected project).
- Workspace Data tab: resolve field definitions from that package’s form config.
- Visualization: filter viz by package `form_id` (§7).

---

## 9. Migration

| Step | Action |
|------|--------|
| 1 | Server: discover forms with legacy fallback (§4.2) |
| 2 | For a pilot repo (e.g. `krs-label`): move `collector/config.json` → `collector/forms/default/config.json`; keep a short-lived copy or redirect note in docs |
| 3 | Move `viz.json` → `visualizations/default.json` with `form_ids: ["default"]` |
| 4 | Client: form picker + manifest `form_id` |
| 5 | Admin: form list + package filter |
| 6 | Deprecate root `config.json` / `viz.json` writers |

Existing packages without `form_id`: display and edit as `default`.

---

## 10. Implementation sketch (non-normative)

| Area | Touch points |
|------|----------------|
| Git / Django | `project_git.py`, config load/validate, seed, builder save path |
| API | Catalog forms summary; `GET .../forms`; legacy `/config` |
| Flutter | Cache model; form picker route; bind `formId` on draft/package; review/history labels |
| Admin UI | Form list; package filter; viz discovery |
| Specs to update when shipping | `git-backed-projects`, `09`, `07`, `collector-vis-config`, `03`, `01` |

---

## 11. Open points (v1 acceptable defaults)

| Topic | Default if unspecified |
|-------|------------------------|
| Form list order | `default` first, then `form_id` ascending |
| Delete form with existing packages | Warn in UI; allow; packages keep stale `form_id` string |
| Skip picker when one form | **Yes** |
| `form_name` on manifest | **Yes**, snapshot at submit |
