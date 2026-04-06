# Data Models & Config Schema

## 1. Project Schema
```json
{
  "id": "proj_123",
  "name": "Vehicle Walkaround",
  "version": "1.0",
  "config": { /* See Config Collection Schema */ }
}
```

## 2. Config Collection Schema (Draft)
The `config` defines a declarative list of fields that must be collected. The order and display (e.g., a wizard versus an open "to-do list") are orchestrated by the App based on the field's `priority`. This supports both strict sequential guided flows and flexible, out-of-order data collection scenarios.

```json
{
  "fields": [
    {
      "field_id": "vin",
      "priority": 10,
      "type": "text_input",
      "title": "Enter VIN",
      "instructions": "Locate the VIN on the dashboard.",
      "validation": { "min_length": 17, "max_length": 17 }
    },
    {
      "field_id": "front_photo",
      "priority": 20,
      "type": "camera_photo",
      "title": "Front Photo",
      "instructions": "Take a clear photo of the front of the vehicle. Ensure license plate is visible.",
      "validation": { "required": true }
    },
    {
      "field_id": "damage_dropdown",
      "priority": 30,
      "type": "dropdown",
      "title": "Damage Seen?",
      "instructions": "Select any visible damage types.",
      "options": ["None", "Scratch", "Dent", "Broken Glass"],
      "multiple": true
    }
  ]
}
```

## 3. Package Payload (Output)
When the user goes through the flow, the output is bundled into a `Package` that gets stored locally and then shipped to the backend API.

```json
{
  "package_id": "pkg_abc987",
  "project_id": "proj_123",
  "status": "completed",
  "created_at": "2023-10-25T14:22:00Z",
  "data": {
    "vin": "1HGCM82633A000XXX",
    "front_photo": {
      "local_path": "/data/user/0/com.app/photos/img_001.jpg",
      "uploaded_url": null
    },
    "damage_dropdown": ["Scratch", "Dent"]
  }
}
```
