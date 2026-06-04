from .firebase_verify import firebase_auth_enabled
from .request_auth import authenticate_collector_request, parse_bearer


class ApiV1AuthMiddleware:
    """
    /v1/*, /admin-api/* и /ui/api/*:
    - /ui/api/*: Django session (staff/client) или Firebase Bearer (admin_projects).
    - /v1/*, /admin-api/*: как раньше (Firebase / dev bearer).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not (
            path.startswith("/v1/")
            or path.startswith("/admin-api/")
            or path.startswith("/ui/api/")
        ):
            return self.get_response(request)

        if request.method == "OPTIONS":
            return self.get_response(request)

        if path.startswith("/ui/api/"):
            if request.user.is_authenticated:
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
