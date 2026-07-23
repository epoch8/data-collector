> **Language / Язык:** [English](09-project-json-builder-guide.md) · **Русский**

# Гайд: JSON проекта

Как собрать конфиг под текущее приложение. Детали реализации: `collection_flow_resolver.dart`, `scroll_form_flow_step.dart`, пайплайн в [json-driven-collection-ui.ru.md](json-driven-collection-ui.ru.md).

---

## Принцип сборки

1. **`config.fields`** — справочник всех полей: `field_id`, `type`, `title`, `instructions`, при необходимости `validation`, `multiple` (камера), `options` (`single_choice`). Типы: `text_input`, `single_choice`, `datetime`, `instruction`, `camera_photo`.
2. **`config.flow.steps`** — сценарий по порядку. Поддерживаются только **`scroll_form`** и **`review`**. Шаг **`scroll_form`** — один экран со скроллом; список **`field_ids`** задаёт, какие поля на нём и в каком порядке. **Каждое поле из `fields` должно встретиться ровно в одном шаге `scroll_form`.**
3. **`review`** — по желанию, финальный экран проверки перед отправкой. Подписи блоков на нём задаёт **`form_title`** у шага `scroll_form` (человекочитаемое имя формы).
4. **`config.ui`** — по желанию: вложенные строки для подписей в приложении (`ProjectUi`). Блок **`ui.shooting_guide`** клиентом не используется.
5. **Картинки в инструкциях** — в Markdown в поле `instruction` пути должны указывать на файлы, **загруженные в медиа проекта** в админке (страница «Файлы» у проекта). Клиент подтягивает их через API проекта.

Корневые **`id`**, **`name`**, **`version`** обязательны; **`id`** совпадает с идентификатором проекта на сервере / в манифесте.

---

## Минимальный каркас

```json
{
  "id": "my-project-2026",
  "name": "Имя в UI",
  "version": "1.0",
  "config": {
    "flow": { "steps": [] },
    "fields": []
  }
}
```

`config.ui` добавляйте при необходимости.

---

## Поля (`config.fields`)

| Ключ | Роль |
|------|------|
| `field_id` | Ключ в состоянии мастера и в payload. |
| `type` | Виджет и тип данных. |
| `title`, `instructions` | Подписи; у `instruction` в `instructions` допускается Markdown. |
| `validation` | Для типов с вводом/камерой: например `required`. У **`instruction` обязательность не используется** приложением. |
| `multiple`, `validation.min_items` | Только у `camera_photo` (несколько снимков). |

---

## Сценарий (`config.flow.steps`)

У шага: **`id`** (технический код), **`screen`**: `scroll_form` или `review`.

У **`scroll_form`** обязательны непустые **`field_ids`**. Опционально: **`form_title`**, **`cow_id_hints`**, **`cow_id_field_id`**.

У **`review`** отдельных полей нет.

---

## Валидация и UI на сервере

В админке Django: визуальный редактор проекта и проверка JSON перед сохранением (`project_config_validate.py`) согласованы с клиентом.

---

## Чеклист

- [ ] Валидный JSON, уникальный `id`.
- [ ] Каждый `field_id` из шагов есть в `fields`, типы соответствуют экрану.
- [ ] Ни одно поле не пропущено и не продублировано между шагами `scroll_form`.
- [ ] Медиа для картинок в инструкциях загружены на странице «Файлы» проекта.

При смене поведения в коде обновляйте этот файл и **json-driven-collection-ui.ru.md**.
