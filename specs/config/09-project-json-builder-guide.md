> **Language / Язык:** **English** · [Русский](09-project-json-builder-guide.ru.md)

# Guide: project JSON

How to build config for the current app. Implementation details: `collection_flow_resolver.dart`, `scroll_form_flow_step.dart`, pipeline in [json-driven-collection-ui.md](json-driven-collection-ui.md).

---

## Assembly principles

1. **`config.fields`** — catalog of all fields: `field_id`, `type`, `title`, `instructions`, optionally `validation` and `multiple` (camera). Types: `text_input`, `datetime`, `instruction`, `camera_photo`.
2. **`config.flow.steps`** — scenario in order. Only **`scroll_form`** and **`review`** are supported. A **`scroll_form`** step is one scrollable screen; **`field_ids`** list defines which fields appear and in what order. **Every field from `fields` must appear in exactly one `scroll_form` step.**
3. **`review`** — optional, final review screen before submit. Block labels on it come from **`form_title`** on the `scroll_form` step (human-readable form name).
4. **`config.ui`** — optional: nested strings for app labels (`ProjectUi`). Block **`ui.shooting_guide`** is not used by the client.
5. **Images in instructions** — Markdown in the `instruction` field must reference files **uploaded to project media** in admin (project "Files" page). The client fetches them via the project API.

Root **`id`**, **`name`**, **`version`** are required; **`id`** matches the project identifier on the server / in the manifest.

---

## Minimal skeleton

```json
{
  "id": "my-project-2026",
  "name": "Name in UI",
  "version": "1.0",
  "config": {
    "flow": { "steps": [] },
    "fields": []
  }
}
```

Add `config.ui` as needed.

---

## Fields (`config.fields`)

| Key | Role |
|-----|------|
| `field_id` | Key in wizard state and payload. |
| `type` | Widget and data type. |
| `title`, `instructions` | Labels; `instruction` type allows Markdown in `instructions`. |
| `validation` | For input/camera types: e.g. `required`. **`instruction` requiredness is not used** by the app. |
| `multiple`, `validation.min_items` | Only for `camera_photo` (multiple shots). |

---

## Scenario (`config.flow.steps`)

Each step has **`id`** (technical code), **`screen`**: `scroll_form` or `review`.

For **`scroll_form`**, non-empty **`field_ids`** are required. Optional: **`form_title`**, **`cow_id_hints`**, **`cow_id_field_id`**.

**`review`** has no separate fields.

---

## Validation and UI on server

In Django admin: visual project editor and JSON validation before save (`project_config_validate.py`) aligned with the client.

---

## Checklist

- [ ] Valid JSON, unique `id`.
- [ ] Every `field_id` from steps exists in `fields`, types match the screen.
- [ ] No field skipped or duplicated across `scroll_form` steps.
- [ ] Media for instruction images uploaded on project "Files" page.

When behavior changes in code, update this file and **json-driven-collection-ui.md**.
