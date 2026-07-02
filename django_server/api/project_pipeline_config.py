"""Чтение и валидация collector/pipeline.json из Git-кэша проекта.

Отдельный от формы (collector/config.json) конфиг для серверных пайплайнов и
интеграций. Сейчас поддерживается один блок — `on_commit`: исходящий webhook,
который дёргается при commit пакета.

Файл опционален: если его нет в репозитории проекта — ничего не происходит.

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
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Project
from .project_git import GitProjectError, pull, repo_dir

PIPELINE_CONFIG_REL_PATH = "collector/pipeline.json"
ALLOWED_HOOK_METHODS = frozenset({"POST", "PUT", "PATCH", "GET", "DELETE"})


def pipeline_config_path(project: Project) -> Path:
    return repo_dir(project.project_id) / PIPELINE_CONFIG_REL_PATH


def read_pipeline_config_raw(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> str | None:
    if fetch_remote:
        pull(project, force=force_pull)
    path = pipeline_config_path(project)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def read_pipeline_config_dict(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> dict[str, Any] | None:
    raw = read_pipeline_config_raw(project, fetch_remote=fetch_remote, force_pull=force_pull)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GitProjectError(
            f"Невалидный JSON в {PIPELINE_CONFIG_REL_PATH}: {e}",
            "invalid_pipeline_json",
        ) from e
    if not isinstance(data, dict):
        raise GitProjectError(
            f"Корень {PIPELINE_CONFIG_REL_PATH} должен быть объектом.",
            "invalid_pipeline_json",
        )
    return data


def validate_on_commit(hook: Any) -> list[str]:
    """Опциональный блок on_commit — исходящий webhook при commit пакета."""
    if hook is None:
        return []
    errs: list[str] = []
    if not isinstance(hook, dict):
        return ["on_commit, если задан, должен быть объектом."]

    enabled = hook.get("enabled")
    if enabled is not None and not isinstance(enabled, bool):
        errs.append("on_commit.enabled должен быть true/false.")

    # url обязателен, только если ручка включена (enabled != false).
    url = hook.get("url")
    if enabled is not False:
        if not isinstance(url, str) or not url.strip():
            errs.append("on_commit.url обязателен и должен быть непустой строкой.")
        elif not (url.strip().startswith("http://") or url.strip().startswith("https://")):
            errs.append("on_commit.url должен начинаться с http:// или https://.")
    elif url is not None and not isinstance(url, str):
        errs.append("on_commit.url должен быть строкой.")

    method = hook.get("method")
    if method is not None and (
        not isinstance(method, str) or method.strip().upper() not in ALLOWED_HOOK_METHODS
    ):
        errs.append(f"on_commit.method должен быть одним из {sorted(ALLOWED_HOOK_METHODS)}.")

    headers = hook.get("headers")
    if headers is not None:
        if not isinstance(headers, dict):
            errs.append("on_commit.headers, если задан, должен быть объектом строк.")
        else:
            for key, value in headers.items():
                if not isinstance(key, str) or not isinstance(value, (str, int, float, bool)):
                    errs.append("on_commit.headers: ключи — строки, значения — строки/числа.")
                    break

    timeout = hook.get("timeout_seconds")
    if timeout is not None and (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)):
        errs.append("on_commit.timeout_seconds должен быть числом.")

    return errs


def validate_pipeline_config(data: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    version = data.get("version")
    if version is not None and version != 1:
        errs.append("version должен быть 1 или опущен.")
    errs.extend(validate_on_commit(data.get("on_commit")))
    return errs


def load_pipeline_config(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> dict[str, Any] | None:
    """Валидный pipeline-конфиг или None, если файла нет."""
    data = read_pipeline_config_dict(
        project,
        fetch_remote=fetch_remote,
        force_pull=force_pull,
    )
    if data is None:
        return None
    errs = validate_pipeline_config(data)
    if errs:
        raise GitProjectError(
            f"{PIPELINE_CONFIG_REL_PATH}: " + "; ".join(errs),
            "invalid_pipeline_config",
        )
    return data


def load_on_commit_hook(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> dict[str, Any] | None:
    """Блок on_commit из pipeline-конфига или None, если не задан/файла нет."""
    data = load_pipeline_config(project, fetch_remote=fetch_remote, force_pull=force_pull)
    if not data:
        return None
    hook = data.get("on_commit")
    return hook if isinstance(hook, dict) else None
