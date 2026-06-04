# 06 — План работ

## Сейчас

- [x] Спеки в `client-admin`
- [x] Fixture `fixtures/sample_manifest_korovas.json`
- [ ] Git init + первый коммит

## Дальше по порядку

**1. Платформа (`django_server`)**

- Разбор manifest на `data` / `pipeline_results`
- `GET .../workspace` и preview blob
- `PATCH manifest` для staff

**2. UI — каркас**

- Список пакетов + вкладки Data / Pipelines / Media / JSON
- Превью фото, raw JSON как сейчас, но структурированно

**3. UI — правки**

- Редактирование полей в `data`
- Сохранение manifest
- Таблица GT vs inference

**4. Разметка**

- Просмотр keypoints на кадре, потом правка (canvas или CVAT / Label Studio — см. [04-annotations.md](04-annotations.md))

**5. Плагины и пайплайны**

- Хуки типа АИС монолит
- Реальные воркеры inference/cvat в платформе (перенос из cowmetric — отдельно)

## Не в этом репозитории

- Upload с мобилки, ETL, DataPipe
- Миграция старых CowScan в пакеты
