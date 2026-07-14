# Скриншоты для слайдов datapipe

Положите файл `screenshot.png` (или `.gif`) в нужную папку — генератор подхватит автоматически.

| Папка | Слайд | Что снять |
| --- | --- | --- |
| `stage-0-packages/` | Стадия 0: пакеты | ingest пакетов, Gradio inference, задачи CVAT, cvat_link в БД |
| `stage-1-annotation/` | Стадия 1: аннотация | выгрузка CVAT, детектор bbox, merge keypoints → GT |
| `stage-2-train/` | Стадия 2: обучение | train YOLOv8-pose, метрики, best model |
| `stage-3-fiftyone/` | Стадия 3: FiftyOne | публикация GT и предсказаний в FiftyOne |
| `stage-4-prod/` | Стадия 4: prod-модель | инференс prod-модели, fiftyone_predictions_prod |
| `vlm/` | VLM (будущее) | когда появится контур — скрин анализа |

Можно несколько файлов — приоритет: `screenshot.png`, `screenshot.gif`, любой первый `.png`/`.gif` в папке.
