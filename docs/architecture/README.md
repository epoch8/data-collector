# Архитектура — учебный блок

Презентация со схемами. Подробный текст — в markdown рядом.

## Сборка

```bash
python docs/architecture/generate_presentation.py
```

Выход: `Architecture.pptx` (локально; в git не коммитим — файл большой).  
Видео (`video/**/*.mp4`) тоже только локально.  
Перед сборкой закройте файл в PowerPoint.

## Слайды (14)

| # | Слайд |
| --- | --- |
| 1 | Обложка |
| 2 | Стек: 1 платформа · N проектов |
| 3 | Как устроено изнутри |
| 4 | От сценария до пакета на сервере |
| 5 | Протокол загрузки |
| 6 | Где что лежит (4 слоя) |
| 7 | БД проекта: таблицы |
| 8 | Кто куда заходит (роли) |
| 9 | Видео-сценарий: local run → пакет (`create_project.mp4`) |
| 10 | Datapipe: стадии 0–4 |
| 11 | Стадия 0: пакет → CVAT → БД |
| 12 | Видео-сценарий: пайплайны Datapipe (плейсхолдер) |
| 13 | Где искать сбой |
| 14 | Видео-сценарий: типичные ошибки (плейсхолдер) |

Видео (локально): `video/local run/create_project.mp4`

## Справочники

| Файл | Содержание |
| --- | --- |
| [`package-flow.md`](package-flow.md) | Mermaid потока |
| [`data-models-reference.ru.md`](data-models-reference.ru.md) | Payload, таблицы |
| [`korovas-broken/cases.md`](korovas-broken/cases.md) | Кейсы инцидентов |
| [`diagnostics-checklist.ru.md`](diagnostics-checklist.ru.md) | Чек-лист диагностики |
| [`local-run-demo.ru.md`](local-run-demo.ru.md) | Локальный демо: Git → Django → Postgres/MinIO → привязка |
| [`firebase-setup.ru.md`](firebase-setup.ru.md) | Firebase: проект, SDK, SA, Django auth, пользователи |
