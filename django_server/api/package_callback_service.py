"""Исходящий webhook при commit пакета.

Конфиг хранится в Git проекта в ОТДЕЛЬНОМ файле `collector/pipeline.json`
(не в форме `collector/config.json`), блок `on_commit`. Файл опционален: если его
нет, блок выключен (`enabled: false`), не задан `url` или у проекта нет git-remote —
ничего не дёргается.

Пример collector/pipeline.json:

    {
        "version": 1,
        "on_commit": {
            "enabled": true,
            "url": "http://localhost:18080/api/run-with-labels",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": {"labels": [["stage", "packages"]]},
            "timeout_seconds": 10
        }
    }

Вызов best-effort: любые ошибки логируются и НЕ ломают commit пакета.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from .models import Project
from .project_git import GitProjectError
from .project_pipeline_config import load_on_commit_hook

log = logging.getLogger(__name__)

ALLOWED_METHODS = frozenset({"POST", "PUT", "PATCH", "GET", "DELETE"})
DEFAULT_TIMEOUT_SEC = 10.0
MAX_TIMEOUT_SEC = 60.0


def _load_on_commit_hook(project_id: str) -> dict[str, Any] | None:
    """Прочитать блок on_commit из collector/pipeline.json проекта или None."""
    project = (
        Project.objects.filter(project_id=project_id)
        .select_related("git_credential")
        .first()
    )
    if not project or not project.git_remote:
        return None
    try:
        return load_on_commit_hook(project, fetch_remote=True, force_pull=False)
    except GitProjectError as e:
        log.warning("on_commit: не удалось прочитать pipeline-конфиг %s: %s", project_id, e.message)
        return None


def _resolve_timeout(raw: Any) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SEC
    if value <= 0:
        return DEFAULT_TIMEOUT_SEC
    return min(value, MAX_TIMEOUT_SEC)


def _build_headers(hook: dict[str, Any], project_id: str, package_id: str) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    raw = hook.get("headers")
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(key, str) and isinstance(value, (str, int, float, bool)):
                headers[key] = str(value)
    # Идентификаторы пакета всегда доступны получателю, даже если тело статичное.
    headers["X-Data-Collector-Project-Id"] = project_id
    headers["X-Data-Collector-Package-Id"] = package_id
    return headers


def dispatch_on_commit(project_id: str, package_id: str) -> None:
    """Best-effort вызов ручки, настроенной в config.on_commit. Не бросает исключений."""
    try:
        hook = _load_on_commit_hook(project_id)
        if not hook or hook.get("enabled") is False:
            return
        url = hook.get("url")
        if not isinstance(url, str) or not url.strip():
            return
        method = str(hook.get("method") or "POST").upper()
        if method not in ALLOWED_METHODS:
            method = "POST"

        if "body" in hook:
            body_obj = hook.get("body")
        else:
            body_obj = {
                "event": "package.committed",
                "project_id": project_id,
                "package_id": package_id,
            }

        headers = _build_headers(hook, project_id, package_id)
        timeout = _resolve_timeout(hook.get("timeout_seconds"))
        payload = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310 — url из доверенного git-конфига
            url.strip(),
            data=payload,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
            log.info("on_commit -> %s %s: %s", method, url, getattr(resp, "status", "ok"))
    except urllib.error.HTTPError as e:
        log.warning("on_commit -> %s: HTTP %s", package_id, e.code)
    except (urllib.error.URLError, OSError) as e:
        log.warning("on_commit -> %s: %s", package_id, e)
    except Exception:  # noqa: BLE001 — hook не должен ломать commit
        log.exception("on_commit: непредвиденная ошибка для %s", package_id)
