# Local run: keypoints Datapipe (учебный стенд)

Инструкция для демо / отладки пайплайна ключевых точек.
Bring-up сервисов удобно отдавать агенту по скиллу `setup-key-points-regression-datapipe`.

Если нужен полный путь **collector → packages → CVAT**, сначала см.
[`../architecture/local-run-korovas-datapipe.ru.md`](../architecture/local-run-korovas-datapipe.ru.md).

Этот файл фокусируется на контуре **annotation → freeze → train → metrics** в Datapipe UI.

---

## Карта сервисов

| Сервис | URL (типично) | Зачем |
| --- | --- | --- |
| **Datapipe UI + API** | `http://localhost:8010` | Запуски, freeze, train, метрики |
| OpenAPI | `http://localhost:8010/docs` | Опц. |
| **CVAT** | `http://localhost:8080` | Разметка (Host: `localhost`, не `127.0.0.1` за Traefik) |
| Postgres Datapipe | порт из `.env` / compose | Состояние пайплайна |
| MinIO / S3 | по профилю AWS CLI | Кадры пакетов / датасетов |

Порты на разных стендах могут отличаться (compose по умолчанию иногда `:8000`). Смотрите `.env` / `PORT`.

---

## Каталог пайплайна

```text
korovas/experiments/key_points_regression_datapipe/
```

```bash
cd experiments/key_points_regression_datapipe
cp .env.example .env   # заполнить, проверить с человеком
uv sync
```

Ключевые переменные (детали в readme пайплайна):

| Переменная | Смысл |
| --- | --- |
| `DB_URL` | Postgres состояния Datapipe |
| `CVAT_*` | Доступ к CVAT |
| `UPLOADED_PACKAGES_CVAT_PROJECT_ID` / `_NAME` | Проект upload-packages |
| `S3_*` / `UPLOAD_PACKAGES_*` | Бакеты через AWS CLI-профили |
| `REMOTE_DB_URL` | Admin/project DB collector (для packages) |

Константы keypoints, списки проектов, веса: `config.py`.

---

## Поднять API + UI

С compose:

```bash
docker compose up --build
```

Без compose (уже есть Postgres):

```bash
datapipe db create-all
datapipe --pipeline datapipe_api:app api --host 0.0.0.0 --port 8010
```

Открыть UI → спека **Cow Keypoints**.

---

## Минимальный прогон для walkthrough

Предпосылка: в CVAT есть размеченные проекты из `CVAT_PROJECTS` (и/или upload-packages).

```bash
datapipe step --labels=stage=annotation run
datapipe step --labels=stage=train-prepare run
datapipe step --labels=stage=train-without-freeze run
```

Или из UI:

1. Дождаться/запустить annotation (если ещё не гоняли).
2. Frozen Datasets → freeze (`train-prepare`).
3. Training → запрос обучения (`train-without-freeze`).
4. Metrics → таблица на `val` / `test`.

Через API:

```bash
curl -X POST http://localhost:8010/api/run-with-labels \
  -H "Content-Type: application/json" \
  -d "{\"labels\":[[\"stage\",\"annotation\"]]}"
```

---

## Картинки на учебном стенде

Если S3 с хоста недоступен (порт занят, профиль, сеть), кадры иногда кладут локальной копией.
В рассказе достаточно: «могут лежать в S3/MinIO, CVAT или локально».
Не фиксируйте локальные counts как продакшен.

---

## GPU / обучение

Train и SAM-fallback обычно хотят GPU. На Windows/новых картах версия torch должна совпадать с железом (см. заметки стенда / скилл).
Если обучение «тихо» не пишет модель: смотрите статус в UI и таблицы train, не только код выхода CLI.

---

## Скилл для агента

```text
korovas/.claude/skills/setup-key-points-regression-datapipe/SKILL.md
```

Пример промпта:

> Возьми скилл `setup-key-points-regression-datapipe` и подними
> annotation → freeze → train для учебного стенда. Datapipe UI на 8010,
> CVAT на 8080. Покажи логи стадий и что изменилось после каждой.

---

## Связанные документы

- [cow-keypoints-walkthrough.ru.md](cow-keypoints-walkthrough.ru.md)
- [stages-reference.ru.md](stages-reference.ru.md)
- [diagnostics-keypoints.ru.md](diagnostics-keypoints.ru.md)
- [`../architecture/local-run-demo.ru.md`](../architecture/local-run-demo.ru.md)
- [`../architecture/local-run-korovas-datapipe.ru.md`](../architecture/local-run-korovas-datapipe.ru.md)
