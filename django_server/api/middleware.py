from .request_auth import authenticate_collector_request


class ApiV1AuthMiddleware:
    """
    /v1/* и /admin-api/*:
    - Firebase: Bearer = ID token, CollectorUser; mobile_projects для /v1/*, admin_projects для /admin-api/*.
    - Иначе API_BEARER_TOKEN или без проверки (локальная разработка).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not (path.startswith("/v1/") or path.startswith("/admin-api/")):
            return self.get_response(request)

        if request.method == "OPTIONS":
            return self.get_response(request)

        err = authenticate_collector_request(request)
        if err is not None:
            return err

        return self.get_response(request)
