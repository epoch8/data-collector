# Гайд: JSON проекта (как в приложении сейчас)

Что класть в файл проекта и как `flow` ссылается на `fields`. Пайплайн в коде: [json-driven-collection-ui.md](json-driven-collection-ui.md). Схема: [json-ui-flow.drawio](json-ui-flow.drawio).

Корневой `collection_flow` и прочее в [../02-data-models-schema.md](../02-data-models-schema.md) для сбора **не** опирайтесь — ориентир **`config.flow.steps`** и этот документ.

---

## 1. Подключить проект

1. Файл в **`assets/config/`** (или другой путь из `pubspec.yaml` → `flutter.assets`).
2. Путь в **`assets/config/projects.json`** → массив `projects`.
3. **`id`** уникален среди всех JSON манифеста.
4. После смены assets — **полный перезапуск** приложения.

---

## 2. Каркас

```json
{
  "id": "my-project-2026",
  "name": "Имя в UI",
  "version": "1.0",
  "config": {
    "flow": { "steps": [] },
    "fields": [],
    "ui": {}
  }
}
```

| Ключ | Обяз. | Роль |
|------|--------|------|
| `id`, `name`, `version` | да | `id` — роутер и БД; `name` — заголовки. |
| `config.fields` | да | Справочник полей. |
| `config.flow` | да | `steps` — сценарий. |
| `config.ui` | нет | Тексты `ProjectUi`. |

---

## 3. `config.fields`

Словарь **`field_id` → поле** строится при загрузке; при дубликатах **`field_id`** побеждает **последний** — дубли не используйте.

### Общие ключи

| Ключ | Назначение |
|------|------------|
| `field_id` | Ключ в state и в payload. |
| `priority` | Порядок (меньше — выше на скролле). |
| `type` | Виджет и тип данных (ниже). |
| `title`, `instructions` | Подписи. |
| `validation` | Минимум `required`; камера и «Далее». |
| `multiple` | У `camera_photo`: один путь vs список. |
| `options` | У `dropdown` на scroll. |
| `sub_fields` | У `collection` на scroll. |

### Типы на одном экране `scroll_form`

Экран рендерит **все** `fields` по `priority`. **`datetime` на scroll не поддержан** — используйте пошаговый `form` или доработку кода.

| `type` | Scroll |
|--------|--------|
| `text_input`, `dropdown`, `camera_photo`, `collection` | да |
| `datetime` | нет |
| `instruction` | нет отдельного блока |

### Шаг `form` (мастер)

В **`field_ids`** только **`text_input`** и **`datetime`**. Камера, `instruction`, `dropdown` — отдельными шагами.

### `instruction`

В `fields` — поле с `"type": "instruction"`. В `flow` — шаг с `"screen": "instruction"` и **`field_id`**. Экран справки; в payload обычно не как «ответ».

### `camera_pose`

В `fields` — `camera_photo`. В `flow` — шаг `"screen": "camera_pose"` и **`field_id`**.

Несколько ракурсов = несколько полей + несколько шагов по порядку. Динамическое N ракурсов одним шагом без дублирования в JSON **не** поддержано; много кадров в одном поле — **`multiple: true`**.

### Подсказки по ID (Korovas)

На шаге `form`: опционально `"cow_id_hints": true` и `"cow_id_field_id": "…"` (поле должно быть в `field_ids`). История: `shouldGroupHistoryBySubject` в `collection_flow_resolver.dart`.

---

## 4. `config.flow.steps`

Порядок массива = порядок шагов. У шага: **`id`**, **`screen`**.

### Режим UI

| Условие | UI |
|---------|-----|
| Ровно **1** шаг и `screen` = **`scroll_form`** | Один скролл, все поля §3 по `priority`. |
| Иначе | Мастер: `form` / `instruction` / `camera_pose` / `review`. |

**Не совмещать:** при **> 1** шаге **`scroll_form`** быть не должно → `FormatException`.

### Таблица шагов

| `screen` | Доп. поля | Связь с `fields` |
|----------|-----------|------------------|
| `scroll_form` | `field_ids` опционально | Экран всё равно показывает **все** `config.fields`. Узкий набор — только выкидыванием полей из JSON или мастером `form`. |
| `form` | **`field_ids`** обязателен, не пустой | Только `text_input`, `datetime`. |
| `instruction` | **`field_id`** | Тип `instruction`. |
| `camera_pose` | **`field_id`** | Тип `camera_photo`. |
| `review` | — | Собирает поля из всех `form` и `camera_pose`. |

Алиасы: `scrollform`, `cameraphoto` (регистр, дефисы).

### `review` по умолчанию

Есть **`camera_pose`**, нет шага **`review`** → приложение **добавит** `review` в конец.

### Индексы камеры

Номер позы 1…N среди только `camera_pose` уходит в `camera_capture_context`. Детали: `CameraMetadataCollector`, `collection_flow_screen.dart`.

---

## 5. `validation`

`configFieldRequired(field)` ≈ `validation.required == true`.

| Где | Эффект |
|-----|--------|
| `form` | «Далее» с учётом обязательных полей. |
| `camera_pose` | `required: true` — без кадров нельзя дальше / неполный пакет на review. |
| `scroll_form` | См. `scroll_form_screen.dart` и `submitLocalPackage`. |

**`min_items`** для камеры отдельно **не** проверяется.

---

## 6. `config.ui`

Корень **`config.ui`**. Путь — цепочка ключей, например `flow.ribbon.form` → `ProjectUi.str(['flow','ribbon','form'], fallback)`.

**Ветка `ui.flow`:** `continue` (`next`, `to_briefing`, `to_capture`), `app_bar`, `ribbon`, `form`, `camera_pose`, `review`, `camera_meta` — полный перечень имён в коде: `project_ui.dart`.

**`ui.shooting_guide`:** строки + `general_tips` + массив **`pose_cards`** (поля карточки — в `shooting_guide.dart`).

Нет ключа или пустая строка → fallback из Dart.

---

## 7. Рецепты

- **Заметка + фото, один экран:** один `scroll_form`, в `fields` например `text_input` + `camera_photo`. Пример: `simple-photo-notes.json`.
- **Мастер как Korovas:** `form` → `instruction` → несколько `camera_pose` → `review`. Пример: `korovas-2026.json`.
- **Несколько камер без субъекта:** несколько `camera_pose`, без `cow_id_hints` / `cow_identifier`, если группировка истории не нужна. Пример: `product-shelf-shoot-2026.json`.

---

## 8. Частые сбои

| Симптом | Частая причина |
|---------|----------------|
| Открывается «не тот» проект | Дубль `id` в другом файле манифеста. |
| Поля нет | Нет в `fields`; для мастера — нет в `field_ids` / `field_id` шага. |
| `FormatException` | Неверный `screen`, пустой `field_ids` у `form`, несовпадение типа шага и поля, `scroll_form` не единственный шаг. |
| Камера «обязательна» при `required: false` | `validation` не на том поле. |
| Тексты не меняются | Опечатка в пути `ui`; пустая строка → fallback. |

---

## 9. Чеклист перед коммитом

- [ ] Валидный JSON.  
- [ ] Уникальный `id`, путь в `projects.json`.  
- [ ] Каждый `field_id` из `flow` есть в `fields` и тип подходит шагу.  
- [ ] В мастере нет второго `scroll_form`.  
- [ ] Опциональные камеры: `required: false` проверен до review.

Любое новое поведение в коде — обновить этот гайд и **json-driven-collection-ui.md**.
