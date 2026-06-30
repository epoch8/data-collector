> **Language / Язык:** [English](05-stage-1-mvp.md) · **Русский**

# Stage 1: MVP Scope

Статус: **завершён** (исторический документ). Текущее состояние продукта — см. [01-overview.ru.md](01-overview.ru.md).

## Что было в scope Stage 1 (выполнено)

1. ~~Mock Authentication~~ → **Firebase Email/Password** + опциональный офлайн-режим без API.
2. ~~Mock Projects & Configs~~ → bundled `assets/config/` + **серверный каталог** `GET /v1/projects`.
3. **Dynamic UI from config:** `scroll_form` + `review`; типы `text_input`, `datetime`, `instruction`, `camera_photo`.
4. **Local saving:** materialization в `packages/{id}/`, Drift index, `serverDeliveryState`.
5. **History view:** список локальных пакетов со статусом доставки.

## Что было out of scope Stage 1 и текущий статус

| Было out of scope | Сейчас |
|-------------------|--------|
| Real backend API | **Реализовано:** Django `/v1/*`, Git-backed config |
| Enriched data viewer (mobile) | **Не реализовано** (только админка `/ui/`) |
| Video capture | **Не реализовано** |
| Background workers | **Не реализовано** (ручная загрузка с вкладки «Сервер») |

## Текущий scope (после MVP)

**В продакшене:**

- Flutter Android (+ Web с ограничениями)
- Django API + веб-админка (staff + client-admin)
- Git-backed project config, per-project storage URIs
- Package upload protocol (blobs → manifest → commit)
- Admin visualization (`collector/viz.json`, pipeline plugins)

**Backlog:** см. [todo](todo).
