# Datapipe: обзор

Учебный артефакт блока Datapipe. Коротко: зачем фреймворк, что делает Datapipe UI, как это стыкуется с Data Collector и CVAT.

## Зачем

Data Collector принимает пакеты (съёмка → upload → storage). Дальше нужны повторяемые шаги:

- вытащить кадры и разметку;
- собрать обучающий набор;
- обучить модель;
- посчитать метрики;
- вернуть результат в контур (viz, CVAT, prod).

Datapipe держит это как **инкрементальный граф**: каждый шаг знает входы/выходы на уровне записей и пересчитывает только изменившееся.

## Три слоя, которые не путать

| Слой | Роль | Где смотреть |
| --- | --- | --- |
| **Data Collector** | Пакеты, project DB, blobs, админка /viz | Django `:8000`, project DB, MinIO/S3 |
| **CVAT** | Разметка боксов и ключевых точек | `:8080` |
| **Datapipe** | Стадии пайплайна, freeze, train, метрики | Datapipe UI / API (часто `:8010`) |

В презентациях и гайдах интерфейс пайплайна называем **Datapipe UI** (в коде/скриншотах иногда ещё встречается старое имя Ops).

## Что умеет Datapipe UI

- **Overview / Graph** — картина пайплайна и статусы.
- **Runs** — история запусков, логи, шаги стадии.
- **Image / Ground truth** — кадры и эталонная разметка.
- **Frozen Datasets** — снимок данных перед обучением.
- **Training** — модели и запросы на train.
- **Metrics** — таблицы качества (в т.ч. по тегам / subset).

Спека для коров: `cow_keypoints` (`ops_specs.py` в пайплайне keypoints).

## Два типичных входа данных

1. **Пакеты из collector** (стадия packages): `package_session` / `uploaded_blob` → задачи в CVAT, ссылки `cvat_link`, опционально инференс.
2. **Уже размеченные проекты CVAT** (стадия annotation и дальше): выгрузка GT → сплит/теги → freeze → train → метрики / FiftyOne.

На учебном walkthrough часто показывают второй путь: разметка уже есть, пайплайн забирает её и ведёт к обучению.

## Связь с презентациями

| Презентация | Фокус |
| --- | --- |
| `Datapipe.pptx` | Идея фреймворка, record-level, UI в общем виде |
| `Datapipe-Cow-Keypoints-Walkthrough.pptx` | Живой стенд ключевых точек |

## Дальше читать

- [pipeline-flow.ru.md](pipeline-flow.ru.md) — схемы потока
- [stages-reference.ru.md](stages-reference.ru.md) — labels стадий
- [datapipe-ui.ru.md](datapipe-ui.ru.md) — разделы UI
- [cow-keypoints-walkthrough.ru.md](cow-keypoints-walkthrough.ru.md) — сценарий демо
- Architecture: [`local-run-korovas-datapipe.ru.md`](../architecture/local-run-korovas-datapipe.ru.md)
