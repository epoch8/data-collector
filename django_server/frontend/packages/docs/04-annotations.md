# 04 — Разметка и spatial-редакторы

## 1. Задача

Показать и при необходимости **изменить** пространственную разметку (keypoints, bbox, polygons), связанную с кадром `blobs/...`.

Источники данных в manifest:

- `pipeline_results.annotations` — основной канал для UI;
- опционально синхронизация из CVAT через платформенный пайплайн.


## 2. UX-поток

1. Пользователь на вкладке **Media** или **Pipelines** выбирает кадр.
2. Открывается **Annotation panel** (modal или split pane).
3. Canvas рисует image + overlay points/shapes.
4. Save → PATCH `pipeline_results.annotations[blob_path]`.
5. (Позже) опционально «Push to CVAT» — POST platform API.

## 3. Стратегии реализации

### 3.1. A — Inline canvas (рекомендуется для MVP+1)

- **Библиотека:** Konva.js или Fabric.js.
- **Вход:** signed URL blob с платформы, JSON annotation.
- **Формат:** `coco_keypoints` (массив `[x, y, visibility]`).
- **Skeleton:** из `config.admin_ui.skeletons[id]` — рёбра для отрисовки линий.

Плюсы: нет внешних сервисов, полный контроль PATCH manifest.  
Минусы: нужно поддерживать свой UX для сложной таксономии.

### 3.2. B — Embed Label Studio

- iframe или [Label Studio Frontend SDK](https://labelstud.io/guide/frontend).
- Импорт task: image URL + pre-annotations из `pipeline_results.inference`.
- Export callback → merge в `annotations`.

Плюсы: зрелый UX keypoints, теги, QA.  
Минусы: отдельный деплой LS, лицензия, синхронизация пользователей.

### 3.3. C — CVAT deep link (как сейчас)

- Кнопка **Open in CVAT**; правка только в CVAT.
- Платформа по webhook/cron подтягивает export → обновляет `annotations`.

Плюсы: уже есть в cowmetric pipeline.  
Минусы: контекст-switch, задержка sync.


## 4. Конфиг скелета (Korovas example)

```json
{
  "config": {
    "admin_ui": {
      "skeletons": {
        "korovas_v1": {
          "points": [
            { "id": "withers", "label": "Холка" },
            { "id": "hook", "label": "Крючок" }
          ],
          "edges": [["withers", "hook"]]
        }
      },
      "annotation_defaults": {
        "format": "coco_keypoints",
        "skeleton_id": "korovas_v1"
      }
    }
  }
}
```


