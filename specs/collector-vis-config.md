> **Language / Язык:** **English** · [Русский](collector-vis-config.ru.md)

# collector/viz.json — package visualization

Status: **current** (June 2026). Separate config in the project Git repository (not in `collector/config.json`).

## Path

```
collector/viz.json
```

Django reads the file from Git cache after `pull` (like `collector/config.json`).

## Schema (v1)

```json
{
  "version": 1,
  "join_key": "manifest_blob_key",
  "layers": [
    {
      "id": "gt",
      "label": "GT",
      "plugin": "keypoint_korovas",
      "table": "cow_keypoint_annotation",
      "palette": "gt",
      "default_visible": false
    },
    {
      "id": "inference",
      "label": "Inference",
      "plugin": "keypoint_korovas",
      "table": "cow_inference_result",
      "palette": "inference",
      "default_visible": true
    },
    {
      "id": "cvat",
      "label": "CVAT",
      "plugin": "cvat_link",
      "table": "cvat_link",
      "default_visible": true
    },
    {
      "id": "depth",
      "label": "Depth",
      "plugin": "depth_map",
      "table": "depth_map",
      "default_visible": false
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `version` | Only `1` for now |
| `join_key` | Fixed: `manifest_blob_key` — links table row to package blob |
| `layers[].id` | Unique layer id in UI |
| `layers[].plugin` | Built-in plugin id (see below) |
| `layers[].table` | Project DB table (SQLAlchemy / SQLite or Postgres) |
| `layers[].palette` | For `keypoint_korovas`: `gt` \| `inference` (overlay colors) |
| `layers[].default_visible` | Whether layer is enabled when opening the tab |

## Plugins (implemented in django_server)

| plugin | table | Behavior |
|--------|-------|----------|
| `keypoint_korovas` | `cow_keypoint_annotation` | GT: `annotation.points` |
| `keypoint_korovas` | `cow_inference_result` | Inference: keypoints, bbox, segments, metrics |
| `cvat_link` | `cvat_link` | CVAT task URL per frame (`import_cvat_link`) |
| `depth_map` | `depth_map` | Path to `.npy` in package (`depth_path` → `depth_url`; `import_depth_map`) |
| `yolo_detection` | `yolo_detection` | BBox from `detections.boxes` (YOLO `.txt` import) |

Plugin code: `django_server/api/viz_plugins/<plugin_id>/plugin.py` (registry in `viz_plugins/__init__.py`).

The plugin knows the row format; config specifies the table and **class options** (see below).

### Comments in `collector/viz.json`

Line comments `//` are supported (outside quoted strings). Template with explanations: `django_server/examples/collector/viz_yolo.json`.

### `yolo_detection` layer — unified field schema

Common layer fields (as for all plugins): `id`, `label`, `plugin`, `table`, `palette`, `default_visible`.

Additionally **only** for `yolo_detection`:

| Field | Description |
|-------|-------------|
| `include_classes` | `[0, 1]` — which class ids from YOLO `.txt` to draw; omit field = all |
| `classes` | `{"0": "name"}` or `{"0": {"name": "…", "color": "#hex"}}` — labels and colors by id |

Deprecated (validation error): `class_names`, `class_colors` — everything in `classes`.

Example for another project (same `yolo_detection` table, different names):

```json
{
  "id": "det",
  "label": "Detections",
  "plugin": "yolo_detection",
  "table": "yolo_detection",
  "palette": "yolo",
  "default_visible": true,
  "include_classes": [0, 1],
  "classes": {
    "0": { "name": "Udder", "color": "#06b6d4" },
    "1": { "name": "Teat", "color": "#a855f7" }
  }
}
```

Example for YOLO project: `django_server/examples/collector/viz_yolo.json`. Label import:

```bash
python manage.py import_yolo_labels <project_id> <package_id> path/to/labels.txt --blob blobs/img_0001.jpg
```

## When the Visualization tab is shown

1. Valid `collector/viz.json` exists in the repo
2. Project DB has at least one row for `package_id` in any layer table

## API

`GET /ui/projects/{project_id}/packages/{package_id}/viz-data/`

```json
{
  "version": 1,
  "join_key": "manifest_blob_key",
  "layers": [ … ],
  "data": {
    "gt": [ … ],
    "inference": [ … ]
  }
}
```

Example file: `django_server/examples/collector/viz.json`.
