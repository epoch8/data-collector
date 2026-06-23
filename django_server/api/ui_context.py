"""Контекст шаблонов /ui (навигация, Firebase для входа)."""

import json

from django.conf import settings

from .firebase_verify import firebase_auth_enabled
from .ui_access import get_ui_collector, is_ui_staff


def ui_template_context(request):
    cu = get_ui_collector(request)
    firebase_cfg = getattr(settings, "FIREBASE_WEB_CONFIG", None) or {}
    return {
        "ui_is_staff": is_ui_staff(request),
        "ui_collector_user": cu,
        "ui_collector_label": (
            (cu.email or cu.firebase_uid) if cu else ""
        ),
        "firebase_auth_enabled": firebase_auth_enabled(),
        "firebase_web_config_json": json.dumps(firebase_cfg),
    }
