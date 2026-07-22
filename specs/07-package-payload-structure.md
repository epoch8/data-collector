> **Language / Язык:** **English** · [Русский](07-package-payload-structure.ru.md)

# 07 — Package Payload Structure

Status: **current** (June 2026). Materializer implementation: `lib/features/collection/logic/materialize_local_package.dart`.

## 1. Overview

**Package** — atomic collection unit: JSON manifest + binary files. Structured data is separate from blobs; Base64 in JSON is **forbidden**.

## 2. Directory layout (on device and server)

```text
packages/<package_id>/
  ├── payload.json       # manifest (on server — PUT manifest)
  └── blobs/
      ├── pose_front.jpg
      └── ...
```

On the server the root is `storage_uri`; relative path in DB: `packages/{package_id}/blobs/...`.

## 3. JSON payload (`payload.json`)

### 3.1 Root fields

| Field | Description |
|------|----------|
| `package_id` | UUID from client |
| `project_id` | Must match API URL |
| `status` | `completed` on submit |
| `created_at` | ISO 8601 |
| `data` | Config field answers + camera metadata |

### 3.2 Field values in `data`

| Field type | Format in `data` |
|----------|-----------------|
| `text_input` | string |
| `single_choice` | string (selected option `value`) |
| `datetime` | ISO string |
| `camera_photo` | `Map<relativePath, shotMetadata>` |

`instruction` is **not included** in the payload.

### 3.3 Camera metadata (implemented)

After materialization:

- **`data.camera_session`** — compact session snapshot: `device`, `native_back_camera` without heavy `camera2_characteristics`.
- **`data.camera_debug`** — full `camera_capture_context` for debugging.

**Per photo** (each entry in a `camera_photo` field map):

- **`frame_camera`** — intrinsics for the saved file: `image_width_px`, `image_height_px`, `fx_px`, `fy_px`, `cx_px`, `cy_px`, `focal_length_mm`, `intrinsics_source`, …
- **`camera_supplement`** — `exif`, `derived`, `notes`.
- **`collected_at`** — capture time.

Before submit the draft may hold `camera_capture_context`; the materializer rewrites to the final structure.

## 4. Lifecycle

### Draft

- Photos in OS temp cache / app storage.
- Riverpod wizard state holds absolute paths for preview.

### Submit (`materializeLocalPackage`)

1. Create `packages/<package_id>/blobs/`.
2. Copy/move files, normalize names.
3. Replace absolute paths with relative `blobs/...`.
4. Write `payload.json`; update Drift (`status: completed`, `serverDeliveryState: pending`).

### Upload

See [06-upload-lifecycle.md](06-upload-lifecycle.md): blobs → manifest → commit.

On `PUT manifest` the server adds:

```json
"submitted_by": { "firebase_uid": "...", "email": "..." }
```

## 5. Future (not implemented)

**Object arrays** — collections with multiple fields per item (photo + comment in one object):

```json
"annotated_photos": [
  {
    "item_id": "item_001",
    "image": "blobs/item_001_image.jpg",
    "comment": "Focus on the left flank."
  }
]
```

Current configs use flat `camera_photo` fields per pose/view.
