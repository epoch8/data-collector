# 05 — API (client-admin ↔ платформа)

Платформа = `django_server` (пакеты, blobs, manifest, config).  
client-admin только читает/пишет через HTTP. Префикс для staff: **`/admin-api/v1/`** (мобилка по-прежнему `/v1/...`, spec 08).

## Чтение

**Список пакетов**

```http
GET /admin-api/v1/projects/{project_id}/packages?phase=completed
```

Ответ: массив `{ package_id, phase, created_at, uploader_email, has_inference?, has_cvat? }`.

**Один пакет (всё для экрана)**

```http
GET /admin-api/v1/projects/{project_id}/packages/{package_id}/workspace
```

Ответ:

- `session` — phase, даты, uploader
- `manifest` — полный JSON
- `layers` — уже разложенный `{ data, pipeline_results, _ui_meta }`
- `blobs[]` — `logical_path`, `size_bytes`, `preview_url`
- `project_config` — config проекта (fields, pipelines, admin_ui)

**Превью картинки**

```http
GET .../blobs/{blob_id}/preview
```

inline image.

**Конфиг проекта** — тот же JSON, что мобилке: `GET /admin-api/v1/projects/{project_id}/config`.

## Запись manifest

```http
PATCH /admin-api/v1/projects/{project_id}/packages/{package_id}/manifest
```

Тело: целый обновлённый manifest (v1 — проще всего).  
Ответ `200` или `422` (битые ссылки на blobs), `409` при конфликте версий — если позже введём `manifest_revision`.

Правки в основном в `data.*` и `pipeline_results.annotations`; `pipeline_results.inference` с платформы лучше не трогать руками.

## Позже (не v1)

```http
POST .../packages/{package_id}/pipelines/{pipeline_id}/run
```

Повторный запуск inference / cvat из UI.

## Ошибки

```json
{ "error": { "code": "missing_blobs", "message": "...", "details": {} } }
```
