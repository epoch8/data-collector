# Скриншоты для слайдов datapipe

Положите `.png` / `.gif` в папку стадии. Имя `screenshot.gif` / `screenshot.png` имеет приоритет.

| Папка | Слайд | Сейчас |
| --- | --- | --- |
| `stage-0-packages/` | Стадия 0 | `UI_pipeline.png` |
| `stage-1-annotation/` | Стадия 1 | `pipeline inference UI.png` |
| `stage-2-train/` | Стадия 2 | `screenshot.gif` (сборка из 3 скринов) |
| `stage-4-prod/` | Стадия 3 prod | *(пусто)* |

Собрать GIF обучения:

```bash
python docs/e2e-korovas/make_datapipe_train_gif.py
```

Исходники GIF: `run train.png` → `metrix.png` → `annotation image preview.png`.
