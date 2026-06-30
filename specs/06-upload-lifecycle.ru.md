> **Language / Язык:** [English](06-upload-lifecycle.md) · **Русский**

# Upload Lifecycle & Fault Tolerance

Статус: **актуально** (июнь 2026).

HTTP-контракт и серверные фазы — [08-server-api-package-upload.ru.md](08-server-api-package-upload.ru.md). Структура payload — [07-package-payload-structure.ru.md](07-package-payload-structure.ru.md).

## 1. Проблема

Сбор данных часто идёт без стабильной сети. Один multipart-запрос на весь пакет (JSON + 10×5 MB фото) ненадёжен. Решение — **многошаговый протокол**: блобы по одному, затем манифест, затем commit.

## 2. Состояния на устройстве

### Локальный статус пакета (`status` в Drift)

| Статус | Смысл |
|--------|-------|
| `draft` | Сбор в процессе (auto-save) |
| `completed` | Пользователь нажал submit; пакет materialized на диске |

### Статус доставки на сервер (`serverDeliveryState`)

| Статус | Смысл |
|--------|-------|
| `pending` | Готов к отправке, ещё не начинали |
| `uploading` | Идёт протокол upload |
| `completed` | Успешный `commit` (или `GET` подтвердил `completed` после `409` на create) |
| `failed` | Ошибка; пакет остаётся в очереди для повтора |

Отправка **не автоматическая** после submit — пользователь инициирует с вкладки **«Сервер»** (`ServerSyncTab`).

## 3. Протокол upload (клиент)

Код: `lib/features/collection/logic/package_server_upload_io.dart` (и `_web.dart`).

### Phase 1: Initialize session

`POST /v1/projects/{project_id}/packages` с `{ "package_id": "..." }`.

- `201` / `200` → `awaiting_blobs` или resume.
- `409` если уже `completed` → клиент делает `GET` и помечает локально `completed`.

### Phase 2: Blob upload

Для каждого файла в `blobs/`:

`PUT /v1/projects/{project_id}/packages/{package_id}/blobs/{encoded_path}`

- Тело: raw bytes (`application/octet-stream`).
- Идемпотентный повтор того же файла — OK.
- Обрыв сети → resume с незагруженного блоба.

### Phase 3: Manifest

`PUT .../manifest` — JSON как `payload.json`.

- Сервер проверяет все `blobs/...` ссылки → `ready_to_commit` или `422 missing_blobs`.
- `project_id` в JSON должен совпадать с URL.

### Phase 4: Commit

`POST .../commit` → `completed`.

Повтор `commit` для завершённого пакета → `200` с `idempotent: true`.

### Очистка локальных файлов

Политика: удалять тяжёлые blobs **после** подтверждённого `completed`. Текущая реализация **сохраняет** локальные файлы (удаление — продуктовое решение на будущее).

## 4. Серверное хранение

После commit:

- Метаданные — per-project DB (`package_session`, `uploaded_blob`) через SQLAlchemy.
- Файлы — fsspec по `storage_uri`: `packages/{package_id}/blobs/...`.

## 5. Retry и фон

| Механизм | Статус |
|----------|--------|
| Ручной retry с «Сервер» | **Реализовано** |
| `connectivity_plus` для UI | Частично |
| Exponential backoff | В коде upload — базовая обработка ошибок Dio |
| `workmanager` / фон при закрытом приложении | **Не реализовано** |

## 6. UX

- Вкладка **«Сервер»**: список pending/failed, «Загрузить все».
- **История**: цвет рамки по `serverDeliveryState` (`package_delivery_style.dart`).
