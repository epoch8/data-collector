# Медиа: Cow Keypoints walkthrough

Скрины для `generate_cow_keypoints_walkthrough.py`.

| Папка | Назначение | Ожидаемые файлы |
| --- | --- | --- |
| `ui/` | Datapipe UI | `01-overview.png`, `02-graph-annotation.png` (run annotation), `03-runs.png`, `04-run-train-logs.png`, `05-images.png`, `06-frozen.png`, `07-training.png`, `08-metrics.png` |
| `cvat/` | CVAT | `project.png`, `task.png`, `job.png` |
| `gt/` | Эталон | `01.jpg` … `04.jpg`, опц. `hero-collage.jpg` |
| `train/` | Батчи обучения | `batch0.jpg`, `batch1.jpg`, `batch2.jpg`, `labels.jpg` |

Подписи в презентации на русском. В интерфейсе на скринах может оставаться английский UI / старое имя Ops: в устной части говорим **Datapipe UI**.

Обновить презентацию:

```bash
python docs/datapipe/generate_cow_keypoints_walkthrough.py
```
