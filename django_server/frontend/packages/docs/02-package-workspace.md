# 02 — Экран пакета (Package Workspace)

## Страницы

| URL | Что |
|-----|-----|
| `/packages` | Список пакетов, фильтр по проекту и phase |
| `/projects/{project_id}/packages/{package_id}` | Работа с одним пакетом |

Список: `package_id`, проект, phase, дата, кто загрузил. По желанию — бейджи «есть inference / cvat» (если в manifest есть `pipeline_results`).

## Экран пакета

**Шапка:** id пакета, проект, phase, uploader, дата. Кнопки: назад к списку, сохранить, откатить правки.

**Вкладки:**

| Вкладка | Содержание |
|---------|------------|
| **Data** | Поля из `data` — по `config.fields` (текст, числа, кадры) |
| **Pipelines** | Inference, CVAT, кратко по `pipeline_results` |
| **Media** | Все `blobs/*` — превью и скачивание |
| **JSON** | Весь manifest целиком (для отладки и правок «в лоб») |

Слева можно дерево путей (`data` → `pose_1` → …) — клик скроллит к полю на вкладке Data / Media.

## Сохранение

- Правки уходят в manifest через API (см. [05-api-contract.md](05-api-contract.md)).
- Перед сохранением платформа проверяет, что все `blobs/...` из JSON реально есть в пакете.
- Если пакет ещё не `completed` — только просмотр (или явно оговорённый QA-режим).

## GT vs inference

На вкладке **Pipelines** — таблица «поле | значение с формы (`data`) | inference».

Строки задаются в project config, например:

```json
"admin_ui": {
  "metric_mappings": [
    { "label": "Высота холки, см", "gt_path": "data.withers_height_cm", "inference_key": "withers_height_cm" }
  ]
}
```

Если mapping нет — показываем пересечение числовых полей в `data` и `pipeline_results.inference.runs[].metrics`.

## Пустые состояния

- Нет manifest — «манифест не загружен».
- Нет `pipeline_results` — «обработка ещё не запускалась».
- Битая ссылка на blob — не грузим картинку, показываем путь.
