"""Чтение/запись конфига проекта из Git."""

from __future__ import annotations

import json
from typing import Any

from django.http import JsonResponse

from .models import GitCredential, Project
from .project_config_validate import validate_project_payload
from .project_git import (
    GitProjectError,
    generate_ssh_key_pair,
    normalize_git_remote,
    normalize_private_key,
    public_key_from_private,
    read_config_dict,
    read_config_file,
    seed_config_if_missing,
    test_remote,
    write_config_dict,
)
from .views import _err


def seed_project_json(project_id: str, name: str) -> dict[str, Any]:
    return {
        "id": project_id,
        "name": name or project_id,
        "version": "1",
        "config": {
            "fields": [
                {
                    "field_id": "demo_text",
                    "priority": 1,
                    "type": "text_input",
                    "title": "Пример текста",
                    "instructions": "Заполните поле",
                    "validation": {},
                },
            ],
            "flow": {
                "steps": [
                    {"id": "form1", "screen": "form", "field_ids": ["demo_text"]},
                ],
            },
            "ui": {},
        },
    }


def create_credential(*, label: str, private_key: str) -> GitCredential:
    if not (private_key or "").strip():
        raise GitProjectError("Укажите приватный SSH-ключ или сгенерируйте пару.", "missing_key")
    from .git_credential_crypto import encrypt_private_key

    normalized = normalize_private_key(private_key)
    try:
        public_key = public_key_from_private(normalized)
    except GitProjectError:
        raise
    except Exception as e:
        raise GitProjectError(f"Не удалось прочитать публичный ключ: {e}", "invalid_key") from e
    return GitCredential.objects.create(
        label=label,
        public_key=public_key,
        private_key_encrypted=encrypt_private_key(normalized),
    )


def update_credential_private_key(credential: GitCredential, private_key: str) -> str:
    """Обновить приватный ключ; возвращает public key."""
    from .git_credential_crypto import encrypt_private_key

    normalized = normalize_private_key(private_key)
    public_key = public_key_from_private(normalized)
    credential.public_key = public_key
    credential.private_key_encrypted = encrypt_private_key(normalized)
    credential.save(update_fields=["public_key", "private_key_encrypted"])
    return public_key


def create_credential_generated(*, label: str) -> tuple[GitCredential, str, str]:
    private_key, public_key = generate_ssh_key_pair()
    from .git_credential_crypto import encrypt_private_key

    cred = GitCredential.objects.create(
        label=label,
        public_key=public_key,
        private_key_encrypted=encrypt_private_key(private_key),
    )
    return cred, public_key, private_key


def git_error_response(exc: GitProjectError, *, status: int = 502) -> JsonResponse:
    return JsonResponse(
        _err(exc.code, exc.message),
        status=status,
    )


def load_config_dict(project_id: str) -> tuple[dict[str, Any] | None, JsonResponse | None]:
    project = Project.objects.filter(project_id=project_id).select_related("git_credential").first()
    if not project:
        return None, JsonResponse(_err("not_found", "Unknown project"), status=404)
    if not project.git_remote:
        return None, JsonResponse(_err("git_not_configured", "Project has no Git remote"), status=503)
    try:
        return read_config_dict(project, fetch_remote=True, force_pull=False), None
    except GitProjectError as e:
        return None, git_error_response(e)


def load_config_body(project_id: str) -> tuple[str | None, str | None, JsonResponse | None]:
    """Тело JSON для API и ETag (sha)."""
    project = Project.objects.filter(project_id=project_id).select_related("git_credential").first()
    if not project:
        return None, None, JsonResponse(_err("not_found", "Unknown project"), status=404)
    try:
        raw = read_config_file(project, fetch_remote=True, force_pull=False)
        project.refresh_from_db(fields=["last_synced_sha"])
        return raw, project.last_synced_sha or None, None
    except GitProjectError as e:
        return None, None, git_error_response(e)


def save_config_to_git(
    project: Project,
    project_id: str,
    data: dict[str, Any],
    *,
    commit_message: str = "config: update from data-collector admin",
) -> list[str]:
    data["id"] = project_id
    errs = validate_project_payload(data, project_id)
    if errs:
        return errs
    try:
        write_config_dict(project, data, commit_message=commit_message)
        name = (data.get("name") or project.name)[:512]
        if name != project.name:
            project.name = name
            project.save(update_fields=["name", "updated_at"])
    except GitProjectError as e:
        return [e.message]
    return []


def bootstrap_new_project(
    project: Project,
    *,
    seed: dict[str, Any],
    try_seed_push: bool = True,
) -> list[str]:
    """Проверка доступа и при необходимости seed commit. Возвращает предупреждения (не фатальные)."""
    warnings: list[str] = []
    try:
        test_remote(project)
    except GitProjectError as e:
        warnings.append(
            f"Подключение к Git пока не работает: {e.message}. "
            "Добавьте deploy key на GitHub и нажмите «Проверить Git»."
        )
        project.sync_error = e.message[:2000]
        project.save(update_fields=["sync_error", "updated_at"])
        return warnings
    if not try_seed_push:
        return warnings
    try:
        seed_config_if_missing(project, seed)
    except GitProjectError as e:
        warnings.append(f"Не удалось записать начальный config.json: {e.message}")
    return warnings
