# Диагностика: keypoints Datapipe

Таблица для разбора сбоев на стенде ключевых точек. Согласована с
[stages-reference.ru.md](stages-reference.ru.md) и
[`../architecture/diagnostics-checklist.ru.md`](../architecture/diagnostics-checklist.ru.md).

| Тип сбоя | Симптом | Где смотреть | Что делать |
| --- | --- | --- | --- |
| **UI не открывается** | Таймаут / connection refused | Порт API, процесс `datapipe … api`, firewall | Поднять API; сверить `PORT` / `:8010` |
| **CVAT 404 / пусто** | UI CVAT странно себя ведёт | Заходите как `localhost`, не `127.0.0.1` (Traefik Host) | Открыть `http://localhost:8080` |
| **Annotation пустой** | Нет кадров / GT после run | Runs → Steps; `CVAT_PROJECTS`; доступы CVAT | Проверить проекты и креды; перезапуск `annotation` |
| **Нет картинок** | Image пустой, download падает | S3 профиль, endpoint, локальная копия | Починить AWS profile / положить локальный источник |
| **Split / tags пустые** | Нет деления, tag-метрики пустые | `split.json`, стадия annotation | Прогнать annotation до конца; ключи = имена проектов |
| **Freeze не создаётся** | Нет frozen dataset в UI | Runs `train-prepare`; логи | Перезапуск freeze; проверить, что GT уже есть |
| **Train «успех», модели нет** | CLI exit 0, в UI пусто | Статус обучения, Training, логи эпох | Смотреть статус/таблицы, не только exit code |
| **Train падает на GPU / torch** | CUDA / sm_xx ошибки | Версия torch, драйвер | Подобрать сборку torch под железо |
| **Metrics пустые** | Таблица без строк | `count-metrics`, filter subset; связь model↔freeze | Дождаться train-after/metrics; фильтр `val` |
| **Tag metrics пустые** | Есть общие метрики, нет по тегам | `tag` / `image__tag` | Сначала annotation с тегами, потом train |
| **Packages молчит после commit** | Пакет completed, CVAT пуст | `pipeline.json` on_commit; webhook; Datapipe up | См. architecture local-run; ручной `stage=packages` |
| **Webhook 405** | CVAT не дергает пайплайн | URL без `/api/…` или неверный path | Использовать полный path webhook |
| **FiftyOne старый** | Датасет не обновляется | FO meta | Очистка FO + rerun `fiftyone-annotations` / `fiftyone` |

## Быстрый маршрут «в Metrics пусто»

1. Annotation completed? Есть кадры и GT в UI?
2. Frozen dataset создан?
3. Train run completed (или хотя бы дошёл до count-metrics)?
4. В Metrics фильтр subset = `val` (или нужный)?
5. Смотрите Runs → Steps падающего шага, не только Overview.

## Быстрый маршрут «CVAT есть, пайплайн не видит»

1. Имя/ID проекта совпадает с `CVAT_PROJECTS` / `UPLOADED_PACKAGES_*`?
2. Логин CVAT в `.env` верный?
3. Annotation run: какой шаг красный в Steps?
4. Для packages: жив ли `REMOTE_DB_URL` и бакет upload-packages?

## Логи с отладкой

```bash
datapipe --debug step --labels=stage=annotation run > /tmp/dp_debug.log 2>&1
# дальше искать error / traceback в файле, не лить всё в чат
```

## Связанные документы

- [local-run-keypoints.ru.md](local-run-keypoints.ru.md)
- [pipeline-flow.ru.md](pipeline-flow.ru.md)
- [`../architecture/korovas-broken/cases.md`](../architecture/korovas-broken/cases.md)
- Скилл `setup-key-points-regression-datapipe`
