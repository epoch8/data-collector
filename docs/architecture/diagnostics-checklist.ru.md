# Чек-лист диагностики

Таблица для разбора сбоев на стенде Korovas / Data Collector. Согласована с кейсами [`korovas-broken/cases.md`](korovas-broken/cases.md) и потоком [`package-flow.md`](package-flow.md).

| Тип сбоя | Симптом | Где смотреть | Что делать |
| --- | --- | --- | --- |
| **Auth / доступ** | Нет проекта в мобилке; 401/403 на `/v1/*` | Firebase user; `CollectorUser.mobile_projects`; staff → права | Выдать проект, перелогин, обновить каталог |
| **Auth / админка** | Client-admin не видит пакеты | `admin_projects`; сессия `ui_collector_pk` | Назначить проекты в client-admin |
| **Upload — blobs** | Manifest `422 missing_blobs` | `uploaded_blob` vs `payload.json` links; phase | Догрузить blobs, повторить manifest |
| **Upload — сеть** | `failed` / завис `uploading` | Drift `serverDeliveryState`; частичные blobs | Retry с «Сервер» (тот же `package_id`) |
| **Upload — идемпотентность** | POST → `409` | GET пакета; phase `completed` | Пометить локально completed |
| **Upload — commit** | Не уходит в `completed` | phase `ready_to_commit` / `failed`; `failure_reason` | Исправить манифест / blobs; повторить commit |
| **Storage — URI** | Файлов нет при строках в БД | `storage_uri`, encrypted options; «Проверить хранилище» | Починить URI/креды, trailing slash |
| **Storage — project DB** | Пакет «пропал» в одном UI, есть в другом | Не путать catalog Django и project DB; `database_uri` | Смотреть project DB проекта, не `db.sqlite3` каталога |
| **Config / Git** | В мобилке старый сценарий | `last_synced_sha`; Git cache; `collector/config.json` | Sync Git на сервере, обновить клиент |
| **Datapipe — webhook** | Commit есть, пайплайн молчит | `pipeline.json`; логи webhook / stage 0 | Починить webhook; ручной рестарт стадии |
| **Datapipe — blobs** | Stage 0 падает на download | storage + `uploaded_blob.storage_path` | Как S1 + права bucket |
| **Datapipe — CVAT** | Нет задачи / GT | `cvat_link`, `cow_keypoint_annotation` | Доступ CVAT, пересоздать задачу |
| **Viz — пустой inference** | Слой «Инференс» пуст | `cow_inference_result`; prod stage | Перезапуск инференса; сверка blob key |
| **Viz — конфиг** | Данные есть, UI пустой | `viz.json`, viz plugins, консоль `/ui/` | Sync Git, исправить плагин |
| **Клиент — draft** | Пакет не в очереди upload | Drift `status` ≠ `completed` | Закончить сценарий (submit / materialize) |

## Быстрый маршрут «пакет не виден в админке»

1. Клиент: `status` = completed, `serverDeliveryState` = completed?
2. Сервер: `package_session.phase` = completed?
3. Есть ли строки в `uploaded_blob` и объекты по `storage_uri`?
4. Права: staff видит всё; client-admin — только `admin_projects`.
5. Если пакет есть, а viz пустая → таблицы ML + `viz.json`, не upload.

## Ссылки

- Спеки: [`06-upload-lifecycle.ru.md`](../../specs/06-upload-lifecycle.ru.md), [`08-server-api-package-upload.ru.md`](../../specs/08-server-api-package-upload.ru.md), [`project-storage-uris.ru.md`](../../specs/project-storage-uris.ru.md)
- Справочник: [data-models-reference.ru.md](data-models-reference.ru.md)
