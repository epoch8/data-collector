> **Language / Язык:** [English](10-project-multiple-forms.md) · **Русский**

# 10 — Несколько форм в одном проекте

Статус: **planned** (июль 2026). Пока не реализовано. Контекст: [docs/mobile-revisions-2026-07-17/README.md](../docs/mobile-revisions-2026-07-17/README.md) §2–5.

**Связанные документы:** [git-backed-projects.ru.md](git-backed-projects.ru.md), [09-server-project-config-delivery.ru.md](09-server-project-config-delivery.ru.md), [02-data-models-schema.ru.md](02-data-models-schema.ru.md), [07-package-payload-structure.ru.md](07-package-payload-structure.ru.md), [collector-vis-config.ru.md](collector-vis-config.ru.md), [03-user-journey-screens.ru.md](03-user-journey-screens.ru.md).

---

## 1. Цели

- Сохранить **один проект** = одно хозяйство / инициатива = **одна** БД пакетов + **одно** blob-хранилище (`database_uri` / `storage_uri`).
- Внутри проекта — **несколько форм сбора** (разные поля / flow), без ветвления `show_if` внутри формы.
- Оператор **выбирает форму** после входа в проект; выбор формы = выбор сценария (например тип животного).
- У каждого пакета зафиксировано, **какой формой** он собран; в админке фильтр и правка по схеме этой формы.
- Визуализации / пайплайны могут быть привязаны к **одной или нескольким** формам.

Вне scope этой фичи (v1):

- Условные поля / ветвление flow (`show_if`) внутри формы.
- Сразу резать контент КРС на бык / молодняк / корова — сначала **механизм**; текущий одиночный config → одна форма (`default`).
- Отдельные ACL на формы (доступ как у проекта целиком).

---

## 2. Термины

| Термин | Смысл |
|--------|--------|
| **Проект** | Каталог + Git + storage (как сейчас). |
| **Форма** | Один сценарий сбора: свой `config.json` (`fields` + `flow` + опционально `ui`). Идентификатор: `form_id`. |
| **Выбор формы** | Экран мобилки после выбора проекта: только **названия** форм. |
| **Форма по умолчанию** | `form_id = "default"`. Для legacy-репо с одним config и пакетов без `form_id`. |

---

## 3. Решения

| # | Вопрос | Решение |
|---|--------|---------|
| 1 | Хранение форм | **Отдельные файлы** `collector/forms/{form_id}/config.json` |
| 2 | Старый один файл | `collector/config.json` читается → форма `default` |
| 3 | Идентичность формы | `form_id`: slug (`[a-z0-9_]+`); отображаемое имя — root `name` JSON |
| 4 | UX оператора | Проект → **выбор формы (только имена)** → дальше scroll_form / review как сейчас |
| 5 | Смена формы mid-session | **Нельзя**; форма фиксируется при создании пакета/черновика |
| 6 | Черновик | Продолжение черновика project+form; новый сбор снова через picker |
| 7 | Привязка пакета | В манифесте обязателен **`form_id`** (желательно `form_name` / `form_version`) |
| 8 | Уникальность полей | `field_id` уникален **в рамках формы**; между формами можно повторять |
| 9 | Старые пакеты | Нет `form_id` → **`default`** |
| 10 | Админка пакетов | В рамках `project_id`; фильтр/колонка формы; Data tab по схеме **этой** формы |
| 11 | Визуализации | Несколько viz; у каждой `form_ids` (одна viz → несколько форм допустимо) |
| 12 | Пайплайны | Аналогично: конфиг указывает `form_id`(s) |
| 13 | Ветвление | **Вне scope** — разные сценарии = разные формы |
| 14 | Шкалы оценки | Контент полей в формах, не новый виджет платформы в этой спеке |

---

## 4. Структура Git-репозитория

```text
my-project/
  collector/
    forms/
      default/
        config.json
    media/
    visualizations/
      keypoints.json
    # LEGACY (чтение поддерживается):
    # config.json
    # viz.json
```

### 4.1 Form `config.json`

Тот же формат, что текущий project JSON ([02-data-models-schema.ru.md](02-data-models-schema.ru.md)):

```json
{
  "id": "krs-label",
  "name": "Бык-производитель",
  "version": "1.0",
  "config": {
    "fields": [ ],
    "flow": { "steps": [ ] },
    "ui": { }
  }
}
```

Правила:

- Root **`id`** = Django `project_id`.
- Root **`name`** — **имя формы** в picker (не обязательно имя проекта в каталоге).
- Имя проекта в каталоге — по-прежнему Django `Project.name`.
- Валидация каждой формы: как у текущего `validate_project_payload`.

### 4.2 Обнаружение форм

Сервер сканирует `collector/forms/*/config.json`.

Совместимость:

1. Есть ≥1 валидная форма в `forms/` → используем их.
2. Иначе есть `collector/config.json` → одна форма `{ form_id: "default", ... }`.
3. Иначе → ошибка.

Порядок в v1: `default` первым (если есть), далее по `form_id` по алфавиту. Позже можно добавить `forms/index.json`.

---

## 5. Пакет (manifest)

Расширение [07-package-payload-structure.ru.md](07-package-payload-structure.ru.md).

Корень `payload.json` / загружаемого манифеста:

| Поле | Обязательно | Примечание |
|------|-------------|------------|
| `project_id` | да | Как сейчас; совпадает с URL |
| `form_id` | да (новые пакеты) | Slug; для legacy без поля сервер/клиент считают `default` |
| `form_name` | рекомендуется | Снимок имени формы на момент сбора |
| `form_version` | рекомендуется | Снимок `version` формы |
| `created_at` | да | Без изменений |
| `data` | да | Значения полей **только этой** формы |

Валидация upload:

- Неизвестный `form_id` → **`422`** `unknown_form_id` (после обязательного multi-form layout).
- В URL `form_id` в v1 не требуется; форма только из манифеста.

Локально (Drift): хранить `form_id` (и опционально `form_name`) рядом с `projectId`.

---

## 6. API и синк клиента

### 6.1 Каталог `GET /v1/projects`

В элементе проекта:

```json
{
  "project_id": "krs-label",
  "name": "Korovas Scan",
  "config_version": "abc123def456",
  "forms": [
    { "form_id": "default", "name": "Korovas Scan", "version": "1.0" }
  ]
}
```

ETag / `config_version` по-прежнему = Git SHA репозитория проекта.

### 6.2 Бандл форм (предпочтительно для мобилки)

`GET /v1/projects/{project_id}/forms`

```json
{
  "project_id": "krs-label",
  "config_version": "abc123def456",
  "forms": [
    {
      "form_id": "default",
      "config": { }
    }
  ]
}
```

- ETag = `last_synced_sha`.
- Кэш на устройстве: все формы проекта сразу (offline-first).

### 6.3 Одна форма (опционально)

`GET /v1/projects/{project_id}/forms/{form_id}/config` — для админки/превью. Мобильный синк — через §6.2.

### 6.4 Legacy

`GET /v1/projects/{project_id}/config` на один релиз:

- multi-form → отдать конфиг формы `default` (с deprecation);
- клиенты переходят на `/forms`.

---

## 7. Визуализации

Вместо единственного обязательного `collector/viz.json`:

```text
collector/visualizations/{viz_id}.json
```

Пример:

```json
{
  "id": "keypoints",
  "title": "Keypoints",
  "form_ids": ["default"],
  "layers": [ ]
}
```

- `form_ids`: непустой список slug форм.
- Одна viz → много форм; много viz → одна форма.
- Вкладка Visualization у пакета: только viz, у которых в `form_ids` есть `form_id` пакета (legacy → `default`).
- Legacy: один `collector/viz.json` → `{ id: "default", form_ids: ["default"], ... }`.

Пайплайны / импорты: в конфиге указывать `form_ids` / `form_id`.

---

## 8. Пользовательские сценарии

### 8.1 Мобилка

1. Вход → список проектов.
2. Проект → **выбор формы** (имена).
3. Если форма **одна** → picker можно пропустить (но `form_id` в пакет всё равно пишется).
4. Сбор → review → локальный пакет с `form_id`.
5. Очередь / история: проект + имя формы.

### 8.2 Билдер в админке

- Список форм проекта; каждая открывает текущий визуальный редактор на `forms/{form_id}/config.json`.
- Добавить / переименовать / удалить форму.
- Seed нового проекта: `forms/default/config.json` (больше не писать корневой `config.json` для новых).

### 8.3 Пакеты в админке

- Колонка + фильтр по форме внутри проекта.
- Data tab: поля из конфига формы пакета.
- Visualization: фильтр по §7.

---

## 9. Миграция

| Шаг | Действие |
|-----|----------|
| 1 | Сервер: discovery форм + legacy fallback (§4.2) |
| 2 | Пилот (напр. `krs-label`): `config.json` → `forms/default/config.json` |
| 3 | `viz.json` → `visualizations/default.json` с `form_ids: ["default"]` |
| 4 | Клиент: picker + `form_id` в манифесте |
| 5 | Админка: список форм + фильтр пакетов |
| 6 | Убрать запись в корневой `config.json` / `viz.json` |

Пакеты без `form_id`: отображение и правка как `default`.

---

## 10. Набросок реализации (не норматив)

| Зона | Точки |
|------|--------|
| Git / Django | `project_git.py`, load/validate, seed, путь сохранения билдера |
| API | summary в каталоге; `GET .../forms`; legacy `/config` |
| Flutter | кэш; роут picker; `formId` на draft/package; подписи в истории |
| Admin UI | список форм; фильтр; discovery viz |
| Обновить при релизе | `git-backed-projects`, `09`, `07`, `collector-vis-config`, `03`, `01` |

---

## 11. Открытые пункты (дефолты v1)

| Тема | Дефолт |
|------|--------|
| Порядок форм | `default` первым, далее `form_id` ascending |
| Удаление формы при существующих пакетах | Предупреждение в UI; разрешить; у пакетов остаётся строка `form_id` |
| Пропуск picker при одной форме | **Да** |
| `form_name` в манифесте | **Да**, снимок при submit |
