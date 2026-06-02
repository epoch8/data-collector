# datapipe_test — заглушка для client-admin

Сейчас это **не продакшен-источник данных**. Реальные GT / inference / depth должны приходить с платформы (`django_server` или пайплайн); здесь только файлы для локальной демо вкладки «Визуализация».

## Файлы в репозитории

| Файл | Назначение |
|------|------------|
| `mock_datapipe_annotations.json` | Таблица GT keypoints → `getCowKeypointAnnotationsForPackage` |
| `mock_datapipe_inference.json` | Таблица inference + ссылки на depth / export |
| `4875_mp4-0003_jpg.json` … | Сырой экспорт пайплайна (вкладка «Экспорт», `source_export`) |
| `*.npy` (3 шт.) | Карты глубины для слоя «Глубина» |
| `field_changelog.json` | *Не коммитится* — история правок полей в `npm run dev` |

Привязка к демо-пакету: `project_id` = `korovas-2026`, `package_id` = `pkg_1779969797246` (см. mock в `client-admin`).

## Не хранить здесь

- `cvat_cow/` — исходник разметки CVAT  
- `depth_maps/*.png` — превью, не используются UI  
- большие архивы и лишние кадры
