# Архитектура — учебный блок

Презентация со схемами. Подробный текст — в markdown рядом.

## Сборка

```bash
python docs/architecture/generate_presentation.py
```

Выход: [`Architecture.pptx`](Architecture.pptx)

## Слайды (11)

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
| 9 | Datapipe: стадии 0–4 |
| 10 | Стадия 0: пакет → CVAT → БД |
| 11 | Где искать сбой |

Убраны: дублирующий E2E-поток и слайд «Интеграции».

## Справочники

| Файл | Содержание |
| --- | --- |
| [`package-flow.md`](package-flow.md) | Mermaid потока |
| [`data-models-reference.ru.md`](data-models-reference.ru.md) | Payload, таблицы |
| [`korovas-broken/cases.md`](korovas-broken/cases.md) | Кейсы инцидентов |
| [`diagnostics-checklist.ru.md`](diagnostics-checklist.ru.md) | Чек-лист диагностики |
