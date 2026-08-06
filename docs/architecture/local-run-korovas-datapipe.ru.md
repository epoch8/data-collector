# Local run: data-collector → Datapipe → CVAT

Инструкция для демо / съёмки: что открыть, по каким ссылкам ходить, что нажать.
Bring-up сервисов — через агента по скиллу (не руками по длинному чек-листу).

Предпосылка: уже пройден `[local-run-demo.ru.md](local-run-demo.ru.md)`
(Django, Postgres+MinIO, проект с Git, storage OK).

Пример стенда ниже — **dc-demo** / `demo-local`. Если у вас другие id — подставьте свои.

---

## Карта сервисов (что где открывается)


| Сервис                           | URL                                                                      | Логин                       | Зачем в демо                                  |
| -------------------------------- | ------------------------------------------------------------------------ | --------------------------- | --------------------------------------------- |
| **Админка data-collector**       | [http://127.0.0.1:8000/ui/login/](http://127.0.0.1:8000/ui/login/)       | staff (без `@`)             | Проекты, пакеты, слои GT / CVAT               |
| Список пакетов                   | [http://127.0.0.1:8000/ui/packages/](http://127.0.0.1:8000/ui/packages/) | —                           | Показать пакеты до/после пайплайна            |
| Проекты                          | [http://127.0.0.1:8000/ui/projects/](http://127.0.0.1:8000/ui/projects/) | —                           | Карточка `demo-local`, storage, Git           |
| **Datapipe API + ML Ops UI**     | [http://localhost:8010](http://localhost:8010)                           | —                           | Запуск `stage=packages`, граф, логи           |
| OpenAPI Datapipe                 | [http://localhost:8010/docs](http://localhost:8010/docs)                 | —                           | Опц. показать API                             |
| **CVAT**                         | [http://localhost:8080](http://localhost:8080)                           | `admin` / `admin`           | Разметка, acceptance, webhook                 |
| MinIO Console                    | [http://localhost:9001](http://localhost:9001)                           | `minioadmin` / `minioadmin` | Опц. показать blobs в `dc-packages`           |
| Postgres                         | `localhost:55432`                                                        | `collector` / `collector`   | БД `proj_demo_local`, `korovas_datapipe_demo` |
| Gradio (опц., не для этого демо) | [http://localhost:7860](http://localhost:7860)                           | —                           | Только если позже включите inference          |


**Порты не путать:** Django = **8000**, Datapipe = **8010**, CVAT = **8080**.

Webhook из CVAT (Docker → хост):

```text
http://host.docker.internal:8010/api/cvat-webhook
```

(обязательно `/api/…`, иначе 405)

---

## Два автотриггера (не путать)

| Триггер | Когда | Куда | Файл / настройка |
| --- | --- | --- | --- |
| **A. Commit пакета** | Пакет впервые становится `completed` в data-collector | Datapipe `stage=packages` → задачи в CVAT + `cvat_link` | `collector/pipeline.json` → `on_commit` |
| **B. Разметка принята** | Job в CVAT: `acceptance` + `completed` | Снова Datapipe `stage=packages` → экспорт GT в `cow_keypoint_annotation` | Webhook в CVAT (§4 сценария) |

Без **A** после загрузки пакета packages надо жать руками.  
Без **B** после разметки GT не вернётся сам.

---

## `collector/pipeline.json` (автозапуск после commit)

Файл лежит в **Git-репо проекта** (не в Django DB), рядом с `config.json` / `viz.json`:

```text
dc-demo/collector/pipeline.json
```

Содержимое для этого стенда (Datapipe на **8010**, не заглушка `:18080` из demo-гайда):

```json
{
  "version": 1,
  "on_commit": {
    "enabled": true,
    "url": "http://localhost:8010/api/run-with-labels",
    "method": "POST",
    "headers": { "Content-Type": "application/json" },
    "body": { "labels": [["stage", "packages"]] },
    "timeout_seconds": 30
  }
}
```

Что сделать:

1. Добавить файл в репо `dc-demo` (локально уже можно положить как выше).
2. `git add collector/pipeline.json && git commit && git push`.
3. В админке проекта → **Проверить Git** (подтянуть конфиг).
4. Datapipe на `:8010` должен быть запущен **до** commit пакета.
5. Снять/залить новый пакет → **commit** → Django best-effort дергает URL; в логах Django: `on_commit -> POST …`.
6. В Datapipe UI / логах должен стартовать `stage=packages`.

Заголовки, которые Django всегда добавляет к запросу:

- `X-Data-Collector-Project-Id`
- `X-Data-Collector-Package-Id`

Тело из `body` статичное (как в примере) — Datapipe гоняет весь label `packages` по инкременту meta.

Проверка без мобилки:

```bash
curl -X POST http://localhost:8010/api/run-with-labels \
  -H "Content-Type: application/json" \
  -d "{\"labels\":[[\"stage\",\"packages\"]]}"
```

Если `on_commit` молчит: нет файла / `enabled: false` / Git не sync / Datapipe не на том порту / Django не достучался до `localhost:8010`.

---

## Скилл для агента (bring-up)

```
korovas/.claude/skills/setup-key-points-regression-datapipe/SKILL.md
```

Имя: `setup-key-points-regression-datapipe`.

Промпт перед съёмкой (или off-camera):

> Возьми скилл `setup-key-points-regression-datapipe`  
> и подними packages→CVAT для **dc-demo** / `demo-local`:  
> Postgres+MinIO из `data-collector/test_dev`, БД `proj_demo_local`,  
> S3 `s3://dc-packages/demo-local/`, Datapipe на **8010**,  
> без Gradio — только CVAT + `cvat_link` / `cow_keypoint_annotation`.  
> Убедись, что в Git проекта есть `collector/pipeline.json` с on_commit  
> на `http://localhost:8010/api/run-with-labels` и сделан **Проверить Git**.

Агент предложит план и `.env` → ваш OK → поднимет CVAT/API и прогонит стадии.

Справка по стадиям: `korovas/experiments/key_points_regression_datapipe/readme.md`.

---

## Перед камерой: что должно уже работать

| # | Проверка | Как убедиться |
| --- | --- | --- |
| 1 | Django | [http://127.0.0.1:8000/ui/login/](http://127.0.0.1:8000/ui/login/) открывается |
| 2 | `pipeline.json` в Git | Файл в репо; в админке **Проверить Git** OK; `on_commit` → `:8010` |
| 3 | Datapipe | [http://localhost:8010](http://localhost:8010) открывается |
| 4 | CVAT | [http://localhost:8080](http://localhost:8080) — проект **dc-demo packages** |
| 5 | Webhook CVAT | Ping → `pong` |
| 6 | Пакет для демо | Либо уже есть completed, либо готовы залить новый (для показа `on_commit`) |

Если чего-то нет — агент по скиллу + запушить `pipeline.json`, потом съёмка.

---

## Сценарий съёмки (что делать по шагам)

### 0. (Опц.) Показать `pipeline.json`

1. IDE / GitHub: `collector/pipeline.json` → URL `http://localhost:8010/api/run-with-labels`, labels `stage=packages`.
2. Админка → проект → **Проверить Git**.

**Говорить:** при commit пакета Django сам дергает Datapipe — tasks в CVAT без ручного run.

---

### 1. Админка: пакет → автозапуск packages

1. [http://127.0.0.1:8000/ui/login/](http://127.0.0.1:8000/ui/login/) → войти.
2. [http://127.0.0.1:8000/ui/packages/](http://127.0.0.1:8000/ui/packages/).
3. **Для триггера A:** залить новый пакет и сделать **commit** → Django шлёт `on_commit` → Datapipe стартует `packages`.
4. Открыть пакет → слои: **CVAT** (ссылки после packages), **GT** (выключен по умолчанию), Inference не трогаем.

**Говорить:** пакеты в Postgres+MinIO; `pipeline.json` запускает packages.

---

### 2. Datapipe UI: подтвердить run

1. [http://localhost:8010](http://localhost:8010) — логи / граф после commit.
2. Если `pipeline.json` ещё нет — руками:

```bash
curl -X POST http://localhost:8010/api/run-with-labels \
  -H "Content-Type: application/json" \
  -d "{\"labels\":[[\"stage\",\"packages\"]]}"
```

`packages` = без Gradio. Инференс — `packages-inference`.

**Ожидание:** в CVAT появились task/job.

---

### 3. CVAT: разметка

1. [http://localhost:8080](http://localhost:8080) → `admin` / `admin`.
2. Проект **dc-demo packages** → job.
3. Разметить: rectangle **`cow`**, skeleton **`cow_keypoints`** (иначе `points: []`).
4. **Acceptance → Completed** (`stage=acceptance` + `state=completed`).

---

### 4. Webhook CVAT (триггер B)

1. Setup webhooks → URL `http://host.docker.internal:8010/api/cvat-webhook`.
2. Events: **job** → `update:job`, SSL выкл, Active вкл.
3. **Ping** → `{"status":"pong"}`.

После acceptance+completed → снова `packages` → GT в `cow_keypoint_annotation`.

---

### 5. Админка: результат

1. [http://127.0.0.1:8000/ui/packages/](http://127.0.0.1:8000/ui/packages/) → тот же пакет.
2. Слой **CVAT** — ссылки; слой **GT** — **включить** → boxes/points.
3. Клик по ссылке CVAT — обратно в кадр job.

---

### 6. (Опц.) MinIO

[http://localhost:9001](http://localhost:9001) → `dc-packages` / `demo-local/`.

---

## Чек-лист перед записью

| # | Шаг | Ок |
| --- | --- | --- |
| 1 | [`local-run-demo.ru.md`](local-run-demo.ru.md) пройден | ☐ |
| 2 | `collector/pipeline.json` запушен, **Проверить Git** OK | ☐ |
| 3 | Datapipe `:8010` + CVAT подняты (скилл) | ☐ |
| 4 | Webhook CVAT Ping → pong | ☐ |
| 5 | Вкладки: packages, Datapipe, CVAT | ☐ |
| 6 | Помните: GT слой выключен по умолчанию | ☐ |

---

## Чек-лист «на камере получилось»

| # | Кадр | Ок |
| --- | --- | --- |
| 1 | `pipeline.json` / Git sync | ☐ |
| 2 | Commit пакета → авто `packages` (или ручной curl) | ☐ |
| 3 | Tasks/Jobs в CVAT | ☐ |
| 4 | Разметка + Acceptance → Completed | ☐ |
| 5 | Webhook / повторный packages | ☐ |
| 6 | Слои CVAT + GT с разметкой | ☐ |

---

## Ссылки на доки

- [`local-run-demo.ru.md`](local-run-demo.ru.md) — Git → Django → Postgres/MinIO → пакеты
- `korovas/.claude/skills/setup-key-points-regression-datapipe/SKILL.md` — bring-up агентом
- `korovas/experiments/key_points_regression_datapipe/readme.md` — стадии пайплайна
- [`package-flow.md`](package-flow.md) — схема потока пакета

