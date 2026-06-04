# 03 — Виджеты и плагины

UI не знает домен «коровы» напрямую. Для каждого куска JSON выбирается виджет по **типу значения** и по **метаданным поля** из `config.fields` (тот же config, что у мобилки).

## Виджеты

| Виджет | Когда |
|--------|--------|
| Поле ввода | строка, число, дата в `data` |
| Группа полей | объект в `data` |
| Галерея | путь `blobs/...` или блок с несколькими кадрами |
| Карточка кадра | фото + `frame_camera` (intrinsics) |
| Таблица метрик | вкладка Pipelines, GT vs inference |
| Статус пайплайна | блоки в `pipeline_results` |
| Canvas разметки | `pipeline_results.annotations` — см. [04-annotations.md](04-annotations.md) |
| JSON как текст | сырой фрагмент, readonly |

Соответствие типам полей мобилки:

| `field.type` | Виджет |
|--------------|--------|
| `text_input` | поле ввода |
| `datetime` | дата/время |
| `instruction` | текст из config, без правки |
| `camera_photo` | карточка кадра + превью |

Путь в manifest для поля с `field_id` обычно `data.{field_id}`; для pose — `data.pose_N` как map «путь blob → метаданные».

## Плагины проекта

Доп. UI без переделки ядра — в config, например интеграция с АИС по `cow_identifier`:

```json
"admin_plugins": [
  { "id": "korovas_ais", "hooks": ["package_header", "data.cow_identifier"] }
]
```

Плагин только рисует кнопки/блоки и ходит в API платформы, не в БД напрямую.

## Стек (v1)

Django templates + немного JS (`package_viewer.js`), как сейчас `/ui` в `django_server`. Отдельный SPA — не в первой версии.
