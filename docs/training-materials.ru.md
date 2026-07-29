# Презентации

Легенда готовности: 🟢 готово · 🟡 частично / черновик · 🔴 не готово

---

| Артефакт | Краткое описание | Готовность | Путь в репо | Ссылка |
| --- | --- | --- | --- | --- |
| Архитектура + видеокасты | Схемы стека, потока данных, ролей, хранилищ, БД проекта, datapipe; слайды-сценарии под видео (14 слайдов). Рядом справочники: модели, поток пакета, диагностика | 🟡 Основной контент готов. Видеокаст local run встроен; datapipe и «типичные ошибки» — плейсхолдеры | `docs/architecture/Architecture.pptx` | https://github.com/epoch8/data-collector/blob/chore/repo-cleanup/docs/architecture/Architecture.pptx |
| E2E пайплайн коров | Сквозной сценарий Korovas: форма → съёмка → upload → datapipe → viz → протокол | 🟡 Основной контент и часть видеокастов/скринов готовы. Datapipe-каст и часть стадий — нет | `docs/e2e-korovas/Korovas-E2E.pptx` | https://github.com/epoch8/data-collector/blob/chore/repo-cleanup/docs/e2e-korovas/Korovas-E2E.pptx |
| CV / Datapipe | CV-пайплайны: стадии, CVAT, inference, метрики (PCK и др.), bad cases | 🔴 Не начато |  |  |

---

## Инструкции

| Артефакт | Краткое описание | Готовность | Путь в репо | Ссылка |
| --- | --- | --- | --- | --- |
| Локальный запуск data-collector | Git → Django → Postgres/MinIO → проект в админке → мобилка / API | 🟡 Черновик готов | `docs/architecture/local-run-demo.ru.md` |  |
| Firebase | Проект, SDK-конфиги, SA, Django auth, пользователи, чек-лист, типовые сбои | 🟡 Черновик готов (плейсхолдеры под свои значения + слоты под скрины) | `docs/architecture/firebase-setup.ru.md` |  |
| Локальный запуск datapipe | Env, триггеры / `on_commit`, стадии, логи, прогон учебного пакета | 🔴 Нет |  |  |
| Продакшен-развёртывание | Runbook: Flutter Web, Django, datapipe, хранилища, env, мониторинг, чек-лист staging/prod | 🟡 Частично (есть куски по Flutter Web; полный runbook нет) | `docs/deploy-flutter-web.ru.md` |  |
| Типичные ошибки и как их решать | Симптом → слой → диагностика → фикс (связка со слайдом/кейсами) | 🟡 Частично: чек-лист + кейсы; цельный runbook нет | `docs/architecture/diagnostics-checklist.ru.md`, `docs/architecture/korovas-broken/cases.md` |  |
|  |  |  |  |  |

---

## Обучающие материалы

| Артефакт | Краткое описание | Готовность | Путь в репо | Ссылка |
| --- | --- | --- | --- | --- |
| Скилы, гайды, лайфхаки AI | Работа с агентом в Cursor/Claude: скиллы, чтение доков, разбор кода на примере Korovas | 🔴 Нет |  |  |
| Задания на стендах | Практикумы: карточки задач (формы, пакеты, деплой / метрики, разметка, триггеры) + кейсы `korovas-broken` | 🟡 Кейсы есть; карточки практикумов — нет | `docs/architecture/korovas-broken/cases.md` |  |
| Ноутбуки для CV-задач | Jupyter: данные, train/eval/export, метрики и bad cases | 🔴 Нет |  |  |
| Справочник: модели данных | Payload, таблицы БД проекта, роли | 🟢 Готово | `docs/architecture/data-models-reference.ru.md` |  |
| Справочник: поток пакета | Mermaid / описание package flow | 🟢 Готово | `docs/architecture/package-flow.md` |  |
| Гайды продукта (админка / мобилка) | Путь оператора и staff в UI | 🟢 Готово (продуктовые README) | `docs/admin-panel/README.ru.md`, `docs/mobile-app/README.ru.md` |  |
| План / дорожная карта обучения | Объём программы, блоки, форматы | 🟢 Готово (внутренний план) | `docs/business/training-plan-300h.md`, `docs/business/training-implementation-roadmap.md` |  |

---

## Видеоматериалы

| Название | Краткое описание | Готовность | Путь в репо | Ссылка |
| --- | --- | --- | --- | --- |
| Создание формы бонитировки (проект коровы) | Админка / Git: форма и сценарий съёмки | 🟡 Частично (есть материалы в E2E-блоке) | `docs/e2e-korovas/` |  |
| Сбор и отправка пакета в МП | Мобилка: съёмка → пакет → вкладка «Сервер» | 🟡 Частично (E2E) | `docs/e2e-korovas/` |  |
| Datapipe суть | Что такое datapipe, зачем, как устроен граф | 🔴 Нет |  |  |
| Datapipe в проекте коров | Инференс + CVAT на Korovas, связь с collector | 🔴 Нет (плейсхолдер на слайде 12 Architecture) |  |  |
| Datapipe CV обучение моделей | Train / eval / метрики / bad cases | 🔴 Нет |  |  |
| Data Collector на локальном стенде | От Git до пакета в админке (простой пример) | 🟢 Готово | `docs/architecture/video/local run/create_project.mp4` |  |
| Разбор типичных ошибок и как их чинить | Нарезка по слоям + UI | 🔴 Нет (плейсхолдер на слайде 14 Architecture) |  |  |

---
