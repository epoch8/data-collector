"""Git: clone/pull, чтение/запись collector/config.json, commit+push."""

from __future__ import annotations

import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterator

from django.conf import settings
from django.utils import timezone as dj_tz

from .git_credential_crypto import decrypt_private_key
from .models import GitCredential, Project

CONFIG_REL_PATH = "collector/config.json"
FORMS_REL_DIR = "collector/forms"
DEFAULT_FORM_ID = "default"
DEFAULT_FORM_CONFIG_REL_PATH = f"{FORMS_REL_DIR}/{DEFAULT_FORM_ID}/config.json"
MEDIA_REL_DIR = "collector/media"


class GitProjectError(Exception):
    def __init__(self, message: str, code: str = "git_error"):
        self.message = message
        self.code = code
        super().__init__(message)


def cache_root() -> Path:
    return Path(settings.PROJECT_GIT_CACHE_ROOT)


def repo_dir(project_id: str) -> Path:
    return cache_root() / project_id


def normalize_private_key(private_key: str) -> str:
    """OpenSSH ключ: только LF, без BOM/CR — иначе на Windows ssh пишет error in libcrypto."""
    text = (private_key or "").strip().lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "PuTTY-User-Key-File" in text:
        raise GitProjectError(
            "Формат .ppk не поддерживается. В PuTTYgen: Conversions → Export OpenSSH key.",
            "invalid_key",
        )
    if "BEGIN OPENSSH PRIVATE KEY" not in text and "BEGIN RSA PRIVATE KEY" not in text:
        raise GitProjectError(
            "Нужен приватный ключ OpenSSH (строка BEGIN OPENSSH PRIVATE KEY).",
            "invalid_key",
        )
    if not text.endswith("\n"):
        text += "\n"
    return text


def _windows_key_owner() -> str:
    user = os.environ.get("USERNAME") or getpass.getuser()
    domain = os.environ.get("USERDOMAIN", "")
    computer = os.environ.get("COMPUTERNAME", "")
    if domain and domain.upper() != computer.upper():
        return f"{domain}\\{user}"
    return user


def _restrict_private_key_permissions(path: Path) -> None:
    """OpenSSH на Windows отклоняет ключ, если ACL Temp даёт доступ другим пользователям."""
    if sys.platform == "win32":
        path_str = str(path)
        owner = _windows_key_owner()
        for args in (
            ["icacls", path_str, "/inheritance:r"],
            ["icacls", path_str, "/grant:r", f"{owner}:(R)"],
        ):
            try:
                subprocess.run(args, check=True, capture_output=True, text=True, timeout=15)
            except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
                pass
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def write_private_key_file(path: Path, private_key: str) -> None:
    path.write_bytes(normalize_private_key(private_key).encode("utf-8"))
    _restrict_private_key_permissions(path)


def verify_private_key_file(path: Path) -> None:
    try:
        subprocess.run(
            ["ssh-keygen", "-y", "-f", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or "").strip()
        raise GitProjectError(
            f"SSH-ключ не читается ({err or 'libcrypto'}). "
            "Вставьте ключ заново (OpenSSH, без .ppk) или сгенерируйте новый на странице проекта.",
            "invalid_key",
        ) from e


def normalize_git_remote(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise GitProjectError("Укажите URL репозитория GitHub.", "invalid_url")
    if url.startswith("git@"):
        return url if url.endswith(".git") else f"{url}.git"
    m = re.match(
        r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        url,
        re.IGNORECASE,
    )
    if m:
        return f"git@github.com:{m.group(1)}/{m.group(2)}.git"
    raise GitProjectError(
        "Поддерживается GitHub: https://github.com/org/repo или git@github.com:org/repo.git",
        "invalid_url",
    )


def generate_ssh_key_pair() -> tuple[str, str]:
    """Возвращает (private_pem_openssh, public_openssh)."""
    with tempfile.TemporaryDirectory() as tmp:
        key_path = Path(tmp) / "deploy_key"
        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(key_path),
                "-N",
                "",
                "-q",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        private_key = normalize_private_key(key_path.read_text(encoding="utf-8"))
        pub = subprocess.run(
            ["ssh-keygen", "-y", "-f", str(key_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return private_key, pub.stdout.strip()


def public_key_from_private(private_key: str) -> str:
    fd, path_str = tempfile.mkstemp(prefix="dc_git_chk_", suffix="_key")
    os.close(fd)
    path = Path(path_str)
    try:
        write_private_key_file(path, private_key)
        verify_private_key_file(path)
        out = subprocess.run(
            ["ssh-keygen", "-y", "-f", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return out.stdout.strip()
    finally:
        path.unlink(missing_ok=True)


@contextmanager
def _ssh_key_file(credential: GitCredential) -> Iterator[Path]:
    private_key = normalize_private_key(decrypt_private_key(credential.private_key_encrypted))
    fd, path_str = tempfile.mkstemp(prefix="dc_git_", suffix="_key")
    os.close(fd)
    path = Path(path_str)
    try:
        write_private_key_file(path, private_key)
        verify_private_key_file(path)
        yield path
    finally:
        path.unlink(missing_ok=True)


def _git_env(credential: GitCredential, key_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    key_ref = key_path.resolve().as_posix()
    env["GIT_SSH_COMMAND"] = (
        f'ssh -i "{key_ref}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new'
    )
    return env


def _run_git(
    args: list[str],
    *,
    credential: GitCredential,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    with _ssh_key_file(credential) as key_path:
        env = _git_env(credential, key_path)
        if extra_env:
            env.update(extra_env)
        try:
            return subprocess.run(
                ["git", *args],
                cwd=cwd,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or str(e)).strip()
            raise GitProjectError(err or "Ошибка git", "git_failed") from e
        except FileNotFoundError as e:
            raise GitProjectError(
                "git не найден в PATH — установите Git на сервер.",
                "git_missing",
            ) from e
        except subprocess.TimeoutExpired as e:
            raise GitProjectError("Таймаут операции git.", "git_timeout") from e


def _git_commit_env() -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": "data-collector",
        "GIT_AUTHOR_EMAIL": "admin@data-collector.local",
        "GIT_COMMITTER_NAME": "data-collector",
        "GIT_COMMITTER_EMAIL": "admin@data-collector.local",
    }


_cfg_request_cache: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar(
    "project_config_request_cache",
    default=None,
)


def pull_min_interval_sec() -> int:
    return max(0, int(getattr(settings, "PROJECT_GIT_PULL_MIN_INTERVAL_SEC", 300)))


def _local_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        raise GitProjectError(err or "Ошибка git", "git_failed") from e


def _local_head_sha(dest: Path) -> str:
    return _local_git(dest, "rev-parse", "HEAD").stdout.strip()


def _cache_has_config(project: Project) -> bool:
    dest = repo_dir(project.project_id)
    if not (dest / ".git").is_dir():
        return False
    if config_path(project).is_file():
        return True
    forms_root = dest / FORMS_REL_DIR
    if not forms_root.is_dir():
        return False
    for child in forms_root.iterdir():
        if child.is_dir() and (child / "config.json").is_file():
            return True
    return False


def _should_fetch_remote(project: Project, *, force: bool) -> bool:
    if force:
        return True
    if not _cache_has_config(project):
        return True
    if not project.last_synced_at:
        return True
    age = (dj_tz.now() - project.last_synced_at).total_seconds()
    return age >= pull_min_interval_sec()


def test_remote(project: Project) -> None:
    _run_git(
        ["ls-remote", project.git_remote, project.git_default_ref],
        credential=project.git_credential,
    )


def _remote_urls_match(cached_url: str, expected: str) -> bool:
    """Сравнивает URL кэша и настройки проекта (https ↔ ssh нормализуются)."""
    try:
        a = normalize_git_remote(cached_url)
    except GitProjectError:
        a = (cached_url or "").strip().rstrip("/")
    try:
        b = normalize_git_remote(expected)
    except GitProjectError:
        b = (expected or "").strip().rstrip("/")
    return bool(a) and a == b


def _ensure_origin(project: Project, dest: Path) -> None:
    """Clone при отсутствии кэша; если origin указывает на другой remote — пересоздать кэш."""
    if (dest / ".git").is_dir():
        try:
            current = _local_git(dest, "remote", "get-url", "origin").stdout.strip()
        except GitProjectError:
            current = ""
        if _remote_urls_match(current, project.git_remote):
            return
        remove_cache(project.project_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run_git(
        [
            "clone",
            "--origin",
            "origin",
            "--branch",
            project.git_default_ref,
            project.git_remote,
            str(dest),
        ],
        credential=project.git_credential,
    )


def pull(project: Project, *, force: bool = False) -> str:
    """Fetch + reset to origin/ref. С кэшем — без сети, если недавно уже pull."""
    dest = repo_dir(project.project_id)
    try:
        if not _should_fetch_remote(project, force=force):
            return _local_head_sha(dest) or project.last_synced_sha or ""

        _ensure_origin(project, dest)
        remote_ref = f"origin/{project.git_default_ref}"
        _run_git(["fetch", "origin", project.git_default_ref], credential=project.git_credential, cwd=dest)
        # Локальный install_vis_config_example кладёт untracked collector/viz.json — мешает checkout.
        _local_git(dest, "clean", "-fd")
        try:
            _local_git(dest, "checkout", "-B", project.git_default_ref, remote_ref)
        except GitProjectError:
            _local_git(dest, "reset", "--hard", remote_ref)
            _local_git(dest, "checkout", "-B", project.git_default_ref, remote_ref)
        sha = _local_head_sha(dest)
        project.last_synced_sha = sha
        project.last_synced_at = dj_tz.now()
        project.sync_error = ""
        project.save(update_fields=["last_synced_sha", "last_synced_at", "sync_error", "updated_at"])
        _invalidate_config_cache(project.project_id)
        return sha
    except GitProjectError as e:
        project.sync_error = e.message[:2000]
        project.save(update_fields=["sync_error", "updated_at"])
        raise


def _invalidate_config_cache(project_id: str) -> None:
    cache = _cfg_request_cache.get()
    if cache is not None and project_id in cache:
        del cache[project_id]


def config_path(project: Project) -> Path:
    return repo_dir(project.project_id) / CONFIG_REL_PATH


def read_config_file(project: Project, *, fetch_remote: bool = True, force_pull: bool = False) -> str:
    if fetch_remote:
        pull(project, force=force_pull)
    elif not _cache_has_config(project):
        pull(project, force=True)
    dest = repo_dir(project.project_id)
    # Multi-form: forms/default, затем legacy collector/config.json.
    for rel in (DEFAULT_FORM_CONFIG_REL_PATH, CONFIG_REL_PATH):
        path = dest / rel
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise GitProjectError(
        f"В репозитории нет {DEFAULT_FORM_CONFIG_REL_PATH} и нет {CONFIG_REL_PATH}.",
        "config_missing",
    )


def read_config_dict(
    project: Project,
    *,
    fetch_remote: bool = True,
    force_pull: bool = False,
) -> dict[str, Any]:
    pid = project.project_id
    cache = _cfg_request_cache.get()
    if cache is not None and pid in cache:
        return cache[pid]

    raw = read_config_file(project, fetch_remote=fetch_remote, force_pull=force_pull)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GitProjectError(f"Невалидный JSON в {CONFIG_REL_PATH}: {e}", "invalid_json") from e
    if not isinstance(data, dict):
        raise GitProjectError("Корень config.json должен быть объектом.", "invalid_json")

    if cache is None:
        cache = {}
        _cfg_request_cache.set(cache)
    cache[pid] = data
    return data


def commit_text_files(
    project: Project,
    files: dict[str, str],
    *,
    commit_message: str,
) -> str:
    """Записать относительные пути → UTF-8 текст, commit + push. keys: repo-relative."""
    if not files:
        return project.last_synced_sha or ""
    pull(project, force=True)
    dest = repo_dir(project.project_id)
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        _run_git(["add", rel], credential=project.git_credential, cwd=dest)
    status = _run_git(["status", "--porcelain"], credential=project.git_credential, cwd=dest)
    if not status.stdout.strip():
        return project.last_synced_sha or ""
    _run_git(
        ["commit", "-m", commit_message],
        credential=project.git_credential,
        cwd=dest,
        extra_env=_git_commit_env(),
    )
    _run_git(
        ["push", "origin", f"HEAD:{project.git_default_ref}"],
        credential=project.git_credential,
        cwd=dest,
    )
    return pull(project, force=True)


def write_config_dict(
    project: Project,
    data: dict[str, Any],
    *,
    commit_message: str = "config: update from data-collector admin",
) -> str:
    """Пишет форму default: forms/default/config.json + legacy collector/config.json."""
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    return commit_text_files(
        project,
        {
            DEFAULT_FORM_CONFIG_REL_PATH: text,
            CONFIG_REL_PATH: text,
        },
        commit_message=commit_message,
    )


def seed_config_if_missing(project: Project, seed: dict[str, Any]) -> str:
    dest = repo_dir(project.project_id)
    try:
        pull(project, force=True)
    except GitProjectError:
        if not (dest / ".git").is_dir():
            _ensure_origin(project, dest)
        else:
            raise
    if _cache_has_config(project):
        return project.last_synced_sha or ""
    return write_config_dict(project, seed, commit_message="config: initial seed from data-collector")


def remove_cache(project_id: str) -> None:
    shutil.rmtree(repo_dir(project_id), ignore_errors=True)


def media_dir(project: Project) -> Path:
    return repo_dir(project.project_id) / MEDIA_REL_DIR


def normalize_media_rel(rel: str) -> str | None:
    """Путь относительно `collector/media/` (без префикса каталога)."""
    s = (rel or "").strip().replace("\\", "/").strip("/")
    if not s or ".." in Path(s).parts:
        return None
    prefix = f"{MEDIA_REL_DIR}/"
    if s.startswith(prefix):
        s = s[len(prefix) :]
    elif s.startswith("assets/"):
        s = s[len("assets/") :]
    return s


def media_config_path(rel_under_media: str) -> str:
    rel = normalize_media_rel(rel_under_media) or rel_under_media.strip().replace("\\", "/")
    return f"{MEDIA_REL_DIR}/{rel}"


def list_media_files(project: Project) -> list[tuple[str, int]]:
    root = media_dir(project)
    if not root.is_dir():
        return []
    out: list[tuple[str, int]] = []
    for f in sorted(root.rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(root)).replace("\\", "/")
            out.append((rel, f.stat().st_size))
    return out


def resolve_media_file(project_id: str, asset_path: str) -> Path | None:
    """Файл в git-кэше `collector/media/…`."""
    rel = normalize_media_rel(asset_path)
    if not rel:
        return None
    git_path = repo_dir(project_id) / MEDIA_REL_DIR / rel
    return git_path if git_path.is_file() else None


def _git_add_commit_push(project: Project, git_paths: list[str], commit_message: str) -> str:
    # ВАЖНО: не делаем здесь pull(force=True). Вызывающие (write_media_file /
    # delete_media_file) уже синхронизировали репозиторий ДО изменения файлов.
    # Повторный pull выполнил бы `git clean -fd` + `reset --hard`, что стёрло бы
    # только что записанный untracked-файл (отсюда "pathspec did not match")
    # и восстановило бы удалённый файл при delete.
    dest = repo_dir(project.project_id)
    for p in git_paths:
        _run_git(["add", "--", p], credential=project.git_credential, cwd=dest)
    status = _run_git(["status", "--porcelain"], credential=project.git_credential, cwd=dest)
    if not status.stdout.strip():
        return project.last_synced_sha or ""
    _run_git(
        ["commit", "-m", commit_message],
        credential=project.git_credential,
        cwd=dest,
        extra_env=_git_commit_env(),
    )
    _run_git(
        ["push", "origin", f"HEAD:{project.git_default_ref}"],
        credential=project.git_credential,
        cwd=dest,
    )
    return pull(project, force=True)


def write_media_file(
    project: Project,
    rel_under_media: str,
    data: bytes,
    *,
    commit_message: str | None = None,
) -> str:
    rel = normalize_media_rel(rel_under_media)
    if not rel:
        raise GitProjectError("Некорректный путь к файлу.", "invalid_path")
    pull(project, force=True)
    dest = media_dir(project) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    git_path = f"{MEDIA_REL_DIR}/{rel}"
    msg = commit_message or f"media: add {rel}"
    return _git_add_commit_push(project, [git_path], msg)


def delete_media_file(
    project: Project,
    rel_under_media: str,
    *,
    commit_message: str | None = None,
) -> str:
    rel = normalize_media_rel(rel_under_media)
    if not rel:
        raise GitProjectError("Некорректный путь к файлу.", "invalid_path")
    pull(project, force=True)
    path = media_dir(project) / rel
    if not path.is_file():
        raise GitProjectError("Файл не найден в репозитории.", "not_found")
    path.unlink()
    git_path = f"{MEDIA_REL_DIR}/{rel}"
    msg = commit_message or f"media: delete {rel}"
    return _git_add_commit_push(project, [git_path], msg)
