"""Импорт пользователей из Firebase Authentication в модель CollectorUser (админка, назначение проектов)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from django.conf import settings

from .collector_user_defaults import assign_default_collector_project
from .firebase_verify import ensure_firebase_app
from .models import CollectorUser


@dataclass(frozen=True)
class FirebaseUserSyncResult:
    total_firebase: int
    created: int
    updated_email: int
    unchanged: int


def sync_collector_users_from_firebase() -> FirebaseUserSyncResult:
    """
    Обходит всех пользователей Firebase Auth (Admin SDK) и upsert в CollectorUser.
    Назначение проектов в админке не затирается (только firebase_uid + email).
    """
    if not (
        getattr(settings, "FIREBASE_SERVICE_ACCOUNT_PATH", None)
        or os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    ):
        raise RuntimeError(
            "Нет учётных данных Firebase Admin SDK. Варианты: "
            "(1) положите файл django_server/firebase-service-account.json (скачайте в Firebase Console → "
            "Project settings → Service accounts → Generate new private key); "
            "(2) или задайте FIREBASE_SERVICE_ACCOUNT_PATH к этому JSON; "
            "(3) или FIREBASE_SERVICE_ACCOUNT_JSON; "
            "(4) или GOOGLE_APPLICATION_CREDENTIALS."
        )

    from firebase_admin import auth

    ensure_firebase_app()

    created = 0
    updated_email = 0
    unchanged = 0
    total = 0

    for rec in auth.list_users().iterate_all():
        total += 1
        email = (rec.email or "").strip()[:254]
        obj, was_created = CollectorUser.objects.get_or_create(
            firebase_uid=rec.uid,
            defaults={"email": email},
        )
        if was_created:
            created += 1
            assign_default_collector_project(obj)
            continue
        if obj.email != email:
            obj.email = email
            obj.save(update_fields=["email", "updated_at"])
            updated_email += 1
        else:
            unchanged += 1

    return FirebaseUserSyncResult(
        total_firebase=total,
        created=created,
        updated_email=updated_email,
        unchanged=unchanged,
    )
