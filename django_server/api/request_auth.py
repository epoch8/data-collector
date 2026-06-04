"""Общая авторизация CollectorUser (Firebase / dev bearer) для /v1/*."""

from __future__ import annotations

import logging
from typing import Literal

from django.conf import settings
from django.http import JsonResponse

from .collector_user_defaults import assign_default_collector_project
from .firebase_verify import firebase_auth_enabled, verify_id_token
from .models import CollectorUser, Project

logger = logging.getLogger(__name__)

ProjectAccessScope = Literal["mobile", "admin"]


def auth_error(code: str, message: str, status: int = 401) -> JsonResponse:
    return JsonResponse(
        {"error": {"code": code, "message": message}},
        status=status,
    )


def parse_bearer(auth_header: str) -> str | None:
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def legacy_bearer_ok(request) -> bool:
    token = getattr(settings, "API_BEARER_TOKEN", None)
    if not token:
        return True
    got = parse_bearer(request.headers.get("Authorization", ""))
    return got == token


def project_ids_for_request(
    request,
    *,
    scope: ProjectAccessScope = "mobile",
) -> set[str] | None:
    """
    Firebase-режим: project_id из M2M CollectorUser (mobile_projects или admin_projects).
    Dev без Firebase: None = все проекты.
    """
    user = getattr(request, "collector_user", None)
    if user is not None:
        rel = user.admin_projects if scope == "admin" else user.mobile_projects
        return set(rel.values_list("project_id", flat=True))
    return None


def forbid_if_no_project_access(
    request,
    project_id: str,
    *,
    scope: ProjectAccessScope = "mobile",
) -> JsonResponse | None:
    if not Project.objects.filter(project_id=project_id).exists():
        return auth_error("not_found", "Unknown project", status=404)
    allowed = project_ids_for_request(request, scope=scope)
    if allowed is not None and project_id not in allowed:
        return auth_error("forbidden", "No access to this project", status=403)
    return None


def authenticate_collector_request(request) -> JsonResponse | None:
    """
    Заполняет request.collector_user / firebase_uid / firebase_email.
    Возвращает JsonResponse при ошибке авторизации.
    """
    if firebase_auth_enabled():
        raw = parse_bearer(request.headers.get("Authorization", ""))
        if not raw:
            return auth_error(
                "unauthorized",
                "Missing Firebase ID token (Authorization: Bearer <token>)",
            )
        try:
            claims = verify_id_token(raw)
        except Exception as e:
            logger.info("Firebase token rejected: %s", e)
            return auth_error("unauthorized", "Invalid or expired Firebase ID token")

        uid = claims.get("uid") or ""
        if not uid:
            return auth_error("unauthorized", "Token has no uid")

        email = str(claims.get("email") or "").strip()[:254]

        user, created = CollectorUser.objects.get_or_create(
            firebase_uid=uid,
            defaults={"email": email},
        )
        if created:
            assign_default_collector_project(user)
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email", "updated_at"])

        request.collector_user = user
        request.firebase_uid = uid
        request.firebase_email = email
        return None

    if not legacy_bearer_ok(request):
        return auth_error("unauthorized", "Missing or invalid bearer token")

    request.collector_user = None
    request.firebase_uid = None
    request.firebase_email = None
    return None
