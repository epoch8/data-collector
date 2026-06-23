# User Journey & Screens

Статус: **актуально** (июнь 2026). Код: `lib/main.dart` (GoRouter), `lib/features/*/presentation/`.

## 1. Аутентификация

| Режим | Поведение |
|-------|-----------|
| **Онлайн** (`API_BASE_URL` задан) | `LoginScreen`: email + password → Firebase Auth. Токен автоматически в Dio (`dio_provider.dart`). |
| **Офлайн** | Логин пропускается; проекты из bundled assets. |

Ошибки входа — snackbar. После успеха → Dashboard.

## 2. Dashboard (главный экран)

`main.dart` — нижняя навигация с вкладками:

| Вкладка | Экран | Содержимое |
|---------|-------|------------|
| **Проекты** | Список `Project` из `projectsProvider` | Карточки проектов; tap → начало сбора |
| **История** | `HistoryTab` | Локальные пакеты всех проектов; цвет рамки по `serverDeliveryState` |
| **Сервер** | `ServerSyncTab` | Очередь на загрузку; «Загрузить все» / по одному |
| **Справка** | `HelpTab` | Статическая справка |

Индикатор синхронизации конфигов — при pull-to-refresh / перезапуске `projectsProvider`.

## 3. Сбор данных

**Вход:** tap на проект → `CollectionFlowScreen(projectId)`.

### 3.1 Один шаг `scroll_form`

Если в конфиге единственный шаг и он `scroll_form` → сразу `ScrollFormCollectionScreen` (все поля шага на одном скролле).

### 3.2 Несколько шагов

`CollectionFlowScreen` + `_FlowStepShell`:

1. Один или несколько шагов **`scroll_form`** — поля из `field_ids` шага.
2. Опционально **`review`** — сводка перед submit.

Типы виджетов по `field.type`: текст, дата/время, Markdown-инструкция, камера (`camera_photo`).

### 3.3 Submit

- Валидация required-полей.
- `submitLocalPackage` → materialization (`blobs/` + payload) → Drift, `status: completed`, `serverDeliveryState: pending`.
- **Автозагрузка на сервер не запускается** — пользователь идёт на вкладку «Сервер».

## 4. Вкладка «Сервер» (outbox)

`ServerSyncTab`:

- Список пакетов с `serverDeliveryState != completed` и `status != draft`.
- Кнопки массовой и поштучной отправки.
- Прогресс: `uploading` / `failed` с текстом ошибки.
- Протокол: см. [08-server-api-package-upload.md](08-server-api-package-upload.md).

## 5. История

`HistoryTab` / детальный просмотр пакета:

| `serverDeliveryState` | Индикация |
|----------------------|-----------|
| `pending` | Жёлтый — только на устройстве |
| `uploading` | В процессе |
| `completed` | Зелёный — принят сервером |
| `failed` | Ошибка, можно повторить с вкладки «Сервер» |

Экспорт manifest (share) — `history/` feature.

## 6. Веб-админка (`/ui/`)

Не часть Flutter-приложения; Django templates:

| Роль | Доступ |
|------|--------|
| Staff | Проекты, пользователи, все пакеты |
| Client-admin (Firebase) | Только пакеты назначенных проектов |

Workspace пакета: **Данные / Медиа / Визуализация / История изменений**.

## 7. Не реализовано в мобильном клиенте

- Enriched / ML viewer (bounding boxes на устройстве) — только в админке.
- Фоновая загрузка при появлении сети.
- Видеозахват.
