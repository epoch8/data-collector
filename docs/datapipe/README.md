# Datapipe — вводная презентация

Презентация по фреймворку: зачем, как устроен граф, UI, связь с Data Collector.
CV-глубина (train/eval, PCK, bad cases) — отдельный артефакт «CV / Datapipe».

## Сборка

```bash
python docs/datapipe/generate_presentation.py
```

Выход: `Datapipe.pptx` (локально; в git не коммитим — файл большой).  
Перед сборкой закройте файл в PowerPoint.

## Слайды (11)

| # | Слайд |
| --- | --- |
| 1 | Обложка + Ops |
| 2 | Проблема |
| 3 | Что такое Datapipe |
| 4 | Три поверхности: Python · Skills · UI |
| 5 | Python: Catalog + Pipeline |
| 6 | Datapipe Ops: граф |
| 7 | Runs и логи |
| 8 | Метрики без логов |
| 9 | Интеграции |
| 10 | Связь с Data Collector |
| 11 | Видео-сценарий: Datapipe суть (плейсхолдер) |

## Медиа

| Папка | Содержание |
| --- | --- |
| `img/pitch/` | Скрины Datapipe Ops из `legacy/datapipe_presentation-2.pptx` |
| `img/tags-demo/` | Код Catalog/Pipeline и UI из `legacy/Datapipe + tags demo.pptx` |
| `legacy/` | Старые драфты (не пересобирать — источник скринов) |
| `video/` | `datapipe-overview.mp4` — ещё нет |

## Связанные материалы

- Architecture: стадии 0–4 и stage 0 — `docs/architecture/`
- E2E Korovas: стадии на коровах — `docs/e2e-korovas/`
- План артефактов — `docs/training-materials.ru.md`
