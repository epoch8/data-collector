import logging

from django.conf import settings
from django.http import JsonResponse

from .collector_user_defaults import assign_default_collector_project
from .firebase_verify import firebase_auth_enabled, verify_id_token
from .models import CollectorUser

logger = logging.getLogger(__name__)


def _unauthorized(code: str, message: str, status: int = 401):
    return JsonResponse(
        {"error": {"code": code, "message": message}},
        status=status,
    )


def _parse_bearer(auth_header: str) -> str | None:
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _legacy_bearer_ok(request) -> bool:
    token = getattr(settings, "API_BEARER_TOKEN", None)
    if not token:
        return True
    got = _parse_bearer(request.headers.get("Authorization", ""))
    return got == token


class ApiV1AuthMiddleware:
    """
    /v1/*:
    - Если включён Firebase: Bearer = ID token, привязка к CollectorUser, пустой доступ = пустой каталог.
    - Иначе если задан API_BEARER_TOKEN — как раньше общий секрет.
    - Иначе — без проверки (локальная разработка).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/v1/"):
            return self.get_response(request)

        if firebase_auth_enabled():
            raw = _parse_bearer(request.headers.get("Authorization", ""))
            if not raw:
                return _unauthorized("unauthorized", "Missing Firebase ID token (Authorization: Bearer <token>)")
            try:
                claims = verify_id_token(raw)
            except Exception as e:
                logger.info("Firebase token rejected: %s", e)
                return _unauthorized("unauthorized", "Invalid or expired Firebase ID token")

            uid = claims.get("uid") or ""
            if not uid:
                return _unauthorized("unauthorized", "Token has no uid")

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
            return self.get_response(request)

        if not _legacy_bearer_ok(request):
            return _unauthorized("unauthorized", "Missing or invalid bearer token")

        request.collector_user = None
        request.firebase_uid = None
        request.firebase_email = None
        return self.get_response(request)
