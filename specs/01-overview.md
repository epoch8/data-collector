# Data Collector — обзор продукта

Статус: **актуально** (июнь 2026). Реализация: Flutter-клиент + Django-бэкенд (`django_server/`).

## 1. Назначение

**Data Collector** — мобильное приложение (Flutter, Android/iOS, опционально Web) для сбора структурированных данных и медиа по **динамическому конфигу проекта**. Пакеты сохраняются локально и загружаются на сервер. Веб-админка Django (`/ui/`) позволяет управлять проектами, просматривать пакеты и визуализировать pipeline-данные (ML, depth, CVAT).

Продакшен: `https://data-collector-app.korovas.ml.epoch8.dev` — API `/v1/*`, админка `/ui/`.

## 2. Основные сущности

| Сущность | Описание |
|----------|----------|
| **User** | Сборщик данных. Аутентификация через **Firebase Email/Password**; на сервере — `CollectorUser` с привязкой к проектам. |
| **Project** | Инициатива сбора. Каталог в Django DB; **конфиг** — в Git-репозитории (`collector/config.json`). См. [git-backed-projects.md](git-backed-projects.md). |
| **Config** | JSON-схема: `config.fields` + `config.flow.steps` — что и в каком порядке собирать. Гайд: [config/09-project-json-builder-guide.md](config/09-project-json-builder-guide.md). |
| **Package** | Единица работы: JSON-манифест + бинарные blobs. Локально — Drift + файловая система; на сервере — per-project DB + fsspec-хранилище. |
| **Enriched data** | Результаты pipeline (keypoints, YOLO, depth, CVAT) в project DB; визуализация в админке через `collector/viz.json`. |

## 3. Ключевые возможности (реализовано)

### 3.1 Аутентификация

- Firebase Email/Password на клиенте; `Authorization: Bearer <ID token>` на `/v1/*`.
- Веб-админка: Django staff (логин без `@`) или Firebase client-admin (только назначенные проекты).
- Офлайн-режим без `API_BASE_URL`: bundled `assets/config/` без авторизации.

### 3.2 Проекты и конфиги

- Каталог `GET /v1/projects` с ETag; полный конфиг `GET /v1/projects/{id}/config` (источник — Git, ETag = `last_synced_sha`).
- Кэш на устройстве: `ApplicationSupport/server_project_cache/`.
- Медиа инструкций: `GET /v1/projects/{id}/assets/{path}` из `collector/media/` в Git.

### 3.3 Сбор данных

- UI строится из `config.flow.steps`: шаги **`scroll_form`** (все поля шага на одном экране) и опционально **`review`**.
- Типы полей: `text_input`, `datetime`, `instruction`, `camera_photo`.
- Локальный черновик и materialization в каталог пакета при submit.
- Метаданные камеры: `camera_session`, `camera_debug`, `frame_camera`, `camera_supplement` (см. [07-package-payload-structure.md](07-package-payload-structure.md)).

### 3.4 Загрузка на сервер

- Протокол: `POST` сессия → `PUT` blobs → `PUT` manifest → `POST` commit ([08-server-api-package-upload.md](08-server-api-package-upload.md)).
- Отправка **вручную** с вкладки «Сервер» (`ServerSyncTab`); фоновый workmanager — не реализован.
- Статусы доставки в Drift: `pending` / `uploading` / `completed` / `failed`.

### 3.5 История и админка

- Локальная история пакетов с индикацией статуса доставки на сервер.
- Django `/ui/packages/`: список, workspace (Данные / Медиа / Визуализация / Changelog), фильтры, редактирование манифеста.

## 4. Архитектура

```text
┌─────────────────┐     HTTPS /v1/*      ┌──────────────────────────────────┐
│  Flutter app    │ ◄──────────────────► │  django_server                   │
│  Riverpod+Drift │     Firebase Bearer    │  API + /ui/ (Django templates)   │
└─────────────────┘                        │  Catalog DB (Postgres/SQLite)    │
                                           │  Per-project: SQLAlchemy + fsspec│
                                           │  Config: Git cache               │
                                           └──────────────────────────────────┘
```

- **Клиент:** Flutter, Riverpod, Drift (SQLite), Dio, GoRouter, Firebase Auth.
- **Сервер каталога:** Django 5.x ORM — `Project`, `CollectorUser`, `GitCredential`.
- **Данные проекта:** SQLAlchemy 2.x + Alembic (`database_uri`); blobs через fsspec (`storage_uri`). См. [project-storage-uris.md](project-storage-uris.md).
- **Конфиг проекта:** Git SSH deploy key → `collector/config.json`, `collector/media/`, `collector/viz.json`.

## 5. Режимы работы клиента

| Режим | Условие | Источник проектов |
|-------|---------|-------------------|
| Офлайн / демо | `API_BASE_URL` не задан | `assets/config/projects.json` + bundled JSON |
| Онлайн | `--dart-define=API_BASE_URL=...` | Только сервер (`ServerProjectCatalog`) |

## 6. Известные ограничения и backlog

См. [todo](todo). Кратко:

- Нет фоновой автозагрузки пакетов (workmanager).
- Web-клиент: известная проблема с Firebase credentials.
- Админка: нет удаления пакетов, просмотра сырого JSON, привязки фото к полям формы.
- Enriched data в мобильном приложении — не реализован (только в веб-админке).

## 7. Связанные документы

| Тема | Файл |
|------|------|
| Модели и JSON-схема | [02-data-models-schema.md](02-data-models-schema.md) |
| Экраны приложения | [03-user-journey-screens.md](03-user-journey-screens.md) |
| Стек и структура кода | [04-tech-stack-architecture.md](04-tech-stack-architecture.md) |
| MVP (история) | [05-stage-1-mvp.md](05-stage-1-mvp.md) |
| Загрузка пакетов | [06-upload-lifecycle.md](06-upload-lifecycle.md), [08-server-api-package-upload.md](08-server-api-package-upload.md) |
| Доставка конфигов | [09-server-project-config-delivery.md](09-server-project-config-delivery.md) |
| Git-конфиг | [git-backed-projects.md](git-backed-projects.md) |
| Хранилища проекта | [project-storage-uris.md](project-storage-uris.md) |
