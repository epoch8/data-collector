# 07 — Package Payload Structure

Статус: **актуально** (июнь 2026). Реализация materializer: `lib/features/collection/logic/materialize_local_package.dart`.

## 1. Overview

**Package** — атомарная единица сбора: JSON-манифест + бинарные файлы. Структурированные данные отделены от blobs; Base64 в JSON **запрещён**.

## 2. Directory layout (на устройстве и на сервере)

```text
packages/<package_id>/
  ├── payload.json       # манифест (на сервере — PUT manifest)
  └── blobs/
      ├── pose_front.jpg
      └── ...
```

На сервере корень — `storage_uri`; относительный путь в БД: `packages/{package_id}/blobs/...`.

## 3. JSON payload (`payload.json`)

### 3.1 Корневые поля

| Поле | Описание |
|------|----------|
| `package_id` | UUID от клиента |
| `project_id` | Должен совпадать с URL API |
| `status` | `completed` при submit |
| `created_at` | ISO 8601 |
| `data` | Ответы полей конфига + метаданные камеры |

### 3.2 Значения полей в `data`

| Тип поля | Формат в `data` |
|----------|-----------------|
| `text_input` | строка |
| `datetime` | ISO строка |
| `camera_photo` | `Map<relativePath, shotMetadata>` |

`instruction` в payload **не попадает**.

### 3.3 Camera metadata (реализовано)

После materialization:

- **`data.camera_session`** — компактный снимок сессии: `device`, `native_back_camera` без тяжёлого `camera2_characteristics`.
- **`data.camera_debug`** — полный `camera_capture_context` для отладки.

**Per photo** (каждая запись в map поля `camera_photo`):

- **`frame_camera`** — intrinsics для сохранённого файла: `image_width_px`, `image_height_px`, `fx_px`, `fy_px`, `cx_px`, `cy_px`, `focal_length_mm`, `intrinsics_source`, …
- **`camera_supplement`** — `exif`, `derived`, `notes`.
- **`collected_at`** — время съёмки.

До submit черновик может держать `camera_capture_context`; materializer переписывает в финальную структуру.

## 4. Lifecycle

### Draft

- Фото во временном кэше ОС / app storage.
- Riverpod wizard state хранит абсолютные пути для превью.

### Submit (`materializeLocalPackage`)

1. Создать `packages/<package_id>/blobs/`.
2. Скопировать/переместить файлы, нормализовать имена.
3. Заменить абсолютные пути на относительные `blobs/...`.
4. Записать `payload.json`; обновить Drift (`status: completed`, `serverDeliveryState: pending`).

### Upload

См. [06-upload-lifecycle.md](06-upload-lifecycle.md): blobs → manifest → commit.

Сервер при `PUT manifest` добавляет:

```json
"submitted_by": { "firebase_uid": "...", "email": "..." }
```

## 5. Будущее (не реализовано)

**Object arrays** — коллекции с несколькими полями на элемент (фото + комментарий в одном объекте):

```json
"annotated_photos": [
  {
    "item_id": "item_001",
    "image": "blobs/item_001_image.jpg",
    "comment": "Focus on the left flank."
  }
]
```

Текущие конфиги используют плоские `camera_photo` поля по одному ракурсу.
