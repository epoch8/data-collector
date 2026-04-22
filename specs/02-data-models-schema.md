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

### 2.1 Basic fields
Поля задаются в `fields` с типом `type` (см. таблицу ниже). Поддерживаются только **`text_input`**, **`datetime`**, **`instruction`**, **`camera_photo`**.

**JSON keys** в конфиге: `field_id`, `collection_flow` (snake_case), остальные поля — как в примерах ниже.

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
      "field_id": "scan_notes",
      "priority": 20,
      "type": "text_input",
      "title": "Notes",
      "instructions": "Optional short notes.",
      "validation": {}
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
    "scan_notes": ""
  }
}
```

**Notes on Blob Resolution:**
- Photo paths in `data` reference *relative paths* inside the local `/blobs/` subdirectory of the package where applicable.
