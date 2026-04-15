# Data Models & Config Schema

## 1. Project Schema
```json
{
  "id": "proj_123",
  "name": "Korovas RGB-D Capture",
  "version": "1.0",
  "config": {
    "collection_flow": "korovas",
    "fields": [ /* See §2; omit collection_flow for a single-scroll wizard */ ]
  }
}
```

- **`collection_flow`** (optional): приложение выбирает сценарий UI. Значение `korovas` — пошаговый поток (анкета → справка → N ракурсов `camera_photo` → проверка), при этом поля по-прежнему задаются в `fields` с приоритетами (см. §2.2).

## 2. Config Collection Schema (Draft)
The `config` defines a declarative list of fields that must be collected. The order and display (e.g., a wizard versus an open "to-do list") are orchestrated by the App based on the field's `priority`. This supports both strict sequential guided flows and flexible, out-of-order data collection scenarios.

### 2.1 Basic Fields & Collections (Sub-Datas)
Fields can either be basic types (text, numbers, generic photos) or complex `collection` types that define an array of complex objects requiring their own `sub_fields`.

**JSON keys** в конфиге: `field_id`, `sub_fields`, `collection_flow` (snake_case), остальные поля — как в примерах ниже.

### 2.2 Korovas flow & extra types (app)
Для `collection_flow: "korovas"` приложение интерпретирует:

| `type` | `priority` (типично) | Назначение |
|--------|----------------------|------------|
| `datetime` | 1–99 | Дата/время скана |
| `text_input` | 1–99 | Текстовые поля анкеты |
| `instruction` | 100–199 | Экран справки (без записи в payload) |
| `camera_photo` | 200–399 | Ракурс съёмки; значение в state — массив путей к файлам |

Порядок шагов съёмки = сортировка `camera_photo` по `priority`. Имена полей в сохранённом `data` совпадают с `field_id` (например `cow_identifier`, `pose_1`).

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
