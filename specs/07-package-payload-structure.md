# 07 - Package Payload Structure (To-Be)

## 1. Overview
The "Collected Package" is the atomic unit of data collected by the application and uploaded to the server. While Stage 1 implemented a simple, flat map (`Map<String, dynamic>`) for data fields, the future architecture requires a robust, hierarchical structure capable of modeling complex relationships, sub-datasets, and massive binary payloads (like photos, depth maps, and videos).

This document outlines the **To-Be** design for package payloads.

## 2. Structure Philosophy
To support both structured data and heavy binaries efficiently (especially on flaky mobile connections):
- **Data vs. Blobs**: Structured data is kept completely distinct from binary blobs.
- **No Base64**: Binaries are strictly explicitly forbidden from being Base64-encoded into the JSON. They are treated as separate physical files.
- **Referencing**: The JSON data acts like a manifest. It contains relative pointers (URI/Paths) pointing to the specific binary files belonging to the package.

## 3. Directory Representation
A complete package on the local device (in queued/completed state ready for upload) will mimic a strict directory structure:
```text
/packages/<package_uuid>/
  ├── payload.json            # The structured data containing metadata and answers
  └── blobs/
      ├── side_photo_1.jpg    
      ├── rgb_angle_1.png     
      └── depth_angle_1.raw   
```

## 4. The JSON Payload (`payload.json`)
The JSON structure will support hierarchical scoping. Instead of just root-level mappings, fields can be complex objects or arrays of complex objects.

### 4.1. Core Package Metadata
The root of the JSON should contain standard tracking info:
- `package_id`: A universally unique identifier.
- `project_id`: The identifier of the governing configuration schema.
- `created_at`: Timestamp of package creation.
- `data`: The actual nested payload captured by the dynamic form fields.

### 4.2. Complex Sub-Datas (Object Arrays)
To address complex collection scenarios—like collecting multiple photos of an object where each capture needs its own associated comment—the schema introduces **Object Arrays** (or Collections).

Instead of treating a field like `camera_photo` simply as an array of strings (paths), a "Collection Widget" will output an array of rich objects tying multiple input parameters together per item.

**Scenario**: Collect multiple photos of a cow, and for each capture, explicitly attach a typed comment.

**To-Be Data Representation:**
```json
{
  "package_id": "pkg_1234567890",
  "project_id": "korovas-2026",
  "data": {
    "cow_identifier": "Bessie-99",
    "annotated_photos": [
      {
        "item_id": "item_001",
        "image": "blobs/item_001_image.jpg",
        "comment": "Focus on the left flank.",
        "timestamp": 1718045123
      },
      {
        "item_id": "item_002",
        "image": "blobs/item_002_image.jpg",
        "comment": "Scratch identified here.",
        "timestamp": 1718045185
      }
    ]
  }
}
```

## 5. Binary Blob Handling Lifecycle
How binary properties like `"image": "blobs/item_001_image.jpg"` are resolved efficiently across the user session:

1. **Draft Phase (Local Capture):**
   - When a user actively takes a photo in the form, the plugin (`image_picker`) saves it to a generic temporary OS cache (`/data/user/0/com.app/cache/xyz.jpg`).
   - The immediate Riverpod state temporarily stores this absolute local path so it can be previewed seamlessly on screen.
2. **Submit Phase ("Save Package"):**
   - The app dynamically builds a permanent package directory (`/documents/packages/<package_id>`).
   - It scaffolds a `/blobs/` subfolder.
   - It **moves/copies** all temporary files designated by the complex object logic into the `/blobs/` directory, normalizing their names (e.g., `blobs/item_001_image.jpg`).
   - The nested JSON tree is walked, and absolute cache paths are scrubbed and replaced with their *strictly relative blob paths*.
   - The `payload.json` file is securely written. (Note: SQLite could still independently hold an index of `package_id` and its `status` string for ultra-fast dashboard rendering).
3. **Upload Phase (Networking):**
   - Working cohesively with `06-upload-lifecycle.md` and [08-server-api-package-upload.md](08-server-api-package-upload.md), a background queue **first** uploads each file under `/blobs/` (one HTTP request per file, with a per-blob progress ledger), **then** uploads the JSON manifest derived from `payload.json`, **then** calls `commit`. This order avoids server-side manifests that reference missing blobs; uploads are **push** from the client when connectivity exists.
