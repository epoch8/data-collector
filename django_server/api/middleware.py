from .firebase_verify import firebase_auth_enabled
from .models import CollectorUser
from .request_auth import authenticate_collector_request, parse_bearer


class UiCollectorSessionMiddleware:
    """Сессия Firebase-клиента для Django-шаблонов /ui (не /ui/api)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith("/ui/") and not path.startswith("/ui/api/"):
            pk = request.session.get("ui_collector_pk")
            if pk:
                request.collector_user = (
                    CollectorUser.objects.filter(pk=pk)
                    .prefetch_related("admin_projects")
                    .first()
                )
            else:
                request.collector_user = None
        return self.get_response(request)


class ApiV1AuthMiddleware:
    """
    /v1/* и /ui/api/*:
    - /ui/api/*: Django session (staff/client) или Firebase Bearer (admin_projects).
    - /v1/*: Firebase / dev bearer (мобильное приложение).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not (path.startswith("/v1/") or path.startswith("/ui/api/")):
            return self.get_response(request)

        if request.method == "OPTIONS":
            return self.get_response(request)

        if path.startswith("/ui/api/"):
            if request.user.is_authenticated:
                return self.get_response(request)
            pk = request.session.get("ui_collector_pk")
            if pk and not getattr(request, "collector_user", None):
                request.collector_user = (
                    CollectorUser.objects.filter(pk=pk)
                    .prefetch_related("admin_projects")
                    .first()
                )
            if getattr(request, "collector_user", None) is not None:
                return self.get_response(request)
            if parse_bearer(request.headers.get("Authorization", "")):
                err = authenticate_collector_request(request)
                if err is not None:
                    return err
                return self.get_response(request)
            if not firebase_auth_enabled():
                return self.get_response(request)
            return self.get_response(request)

        err = authenticate_collector_request(request)
        if err is not None:
            return err

        return self.get_response(request)
