# client-admin

Веб-админка для просмотра и правки **принятых пакетов** data-collector.

**Платформа** (`django_server`) — приём пакетов, пайплайны (inference, CVAT), дописывает `pipeline_results` в manifest.  
**client-admin** — UI: `data` с формы, результаты пайплайнов, разметка, правки JSON.

## Документы

| Файл | О чём |
|------|--------|
| [00-overview.md](docs/00-overview.md) | Зачем и общая схема |
| [01-manifest-and-pipelines.md](docs/01-manifest-and-pipelines.md) | JSON пакета, пайплайны в config |
| [02-package-workspace.md](docs/02-package-workspace.md) | Экран пакета, вкладки |
| [03-field-widgets.md](docs/03-field-widgets.md) | Виджеты и плагины |
| [04-annotations.md](docs/04-annotations.md) | Keypoints, canvas / CVAT / LS |
| [05-api-contract.md](docs/05-api-contract.md) | HTTP API |
| [06-roadmap.md](docs/06-roadmap.md) | План работ |

См. также в монорепе: [07-package-payload-structure.md](../specs/07-package-payload-structure.md), [08-server-api-package-upload.md](../specs/08-server-api-package-upload.md).

## Статус

Спеки — да. Код UI — ещё нет (см. roadmap).
