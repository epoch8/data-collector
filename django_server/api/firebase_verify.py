from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_app_initialized = False
_init_lock = threading.Lock()


def firebase_auth_enabled() -> bool:
    return bool(getattr(settings, "FIREBASE_AUTH_ENABLED", False))


def ensure_firebase_app() -> None:
    """Инициализирует firebase_admin (токены API и синхронизация пользователей)."""
    _ensure_firebase_app()


def _ensure_firebase_app() -> None:
    global _app_initialized
    if _app_initialized:
        return
    import firebase_admin
    from firebase_admin import credentials

    with _init_lock:
        if _app_initialized:
            return
        if firebase_admin._apps:
            _app_initialized = True
            return

        path = (getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", None) or "").strip()
        json_raw = (os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()

        if json_raw:
            cred = credentials.Certificate(json.loads(json_raw))
        elif path and Path(path).is_file():
            cred = credentials.Certificate(path)
        else:
            adc = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            if adc and Path(adc).is_file():
                cred = credentials.Certificate(adc)
            else:
                cred = credentials.ApplicationDefault()

        try:
            firebase_admin.initialize_app(cred)
        except ValueError as e:
            if "already exists" not in str(e).lower():
                raise
            logger.debug("firebase_admin default app already initialized: %s", e)
        _app_initialized = True


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Проверяет Firebase ID token; возвращает payload (uid, email, …)."""
    from firebase_admin import auth

    ensure_firebase_app()
    check_revoked = bool(getattr(settings, "FIREBASE_CHECK_REVOKED", False))
    clock_skew = int(getattr(settings, "FIREBASE_CLOCK_SKEW_SECONDS", 60))
    return auth.verify_id_token(
        id_token,
        check_revoked=check_revoked,
        clock_skew_seconds=clock_skew,
    )
