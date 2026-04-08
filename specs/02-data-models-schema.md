# Data Models & Config Schema

## 1. Project Schema
```json
{
  "id": "proj_123",
  "name": "Korovas RGB-D Capture",
  "version": "1.0",
  "config": { /* See Config Collection Schema */ }
}
```

## 2. Config Collection Schema (Draft)
The `config` defines a declarative list of fields that must be collected. The order and display (e.g., a wizard versus an open "to-do list") are orchestrated by the App based on the field's `priority`. This supports both strict sequential guided flows and flexible, out-of-order data collection scenarios.

### 2.1 Basic Fields & Collections (Sub-Datas)
Fields can either be basic types (text, numbers, generic photos) or complex `collection` types that define an array of complex objects requiring their own `sub_fields`.

```json
{
  "fields": [
    {
      "field_id": "cow_identifier",
      "priority": 10,
      "type": "text_input",
      "title": "Cow Identifier",
      "instructions": "Enter the unique string identifier for the cow.",
      "validation": { "required": true }
    },
    {
      "field_id": "damage_dropdown",
      "priority": 20,
      "type": "dropdown",
      "title": "Damage Seen?",
      "instructions": "Select any visible damage types.",
      "options": ["None", "Scratch", "Dent", "Broken Glass"],
      "multiple": true
    },
    {
      "field_id": "annotated_photos",
      "priority": 30,
      "type": "collection",
      "title": "Annotated Photos",
      "instructions": "Take photos of the cow and add a comment for each.",
      "multiple": true,
      "validation": { "min_items": 1 },
      "sub_fields": [
        {
          "field_id": "image",
          "type": "camera_photo",
          "title": "Photo"
        },
        {
          "field_id": "comment",
          "type": "text_input",
          "title": "Comment"
        }
      ]
    }
  ]
}
```

## 3. Package Payload (Output)
As outlined deeply in `07-package-payload-structure.md`, the output payload strictly separates structured JSON data from binary blobs. The `payload.json` inside the permanent package directory behaves as a manifest:

```json
{
  "package_id": "pkg_1234567890",
  "project_id": "korovas-2026",
  "status": "completed",
  "created_at": "2026-04-08T14:22:00Z",
  "data": {
    "cow_identifier": "Bessie-99",
    "damage_dropdown": ["Scratch", "Dent"],
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

**Notes on Blob Resolution:**
- Object arrays like `annotated_photos` bundle multiple inputs.
- Variables like `image` inside the output strictly reference *relative paths* inside the local `/blobs/` subdirectory of the package.
- Auto-generated tracking metadata (like `item_id` and `timestamp` inside a collection item) are injected implicitly by the app architecture upon capture, not configured by schema inputs.
