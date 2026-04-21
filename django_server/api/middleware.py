from django.conf import settings
from django.http import JsonResponse


class OptionalBearerAuthMiddleware:
    """If settings.API_BEARER_TOKEN is set, require matching Bearer on /v1/."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = getattr(settings, "API_BEARER_TOKEN", None)
        if token and request.path.startswith("/v1/"):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:].strip() != token:
                return JsonResponse(
                    {
                        "error": {
                            "code": "unauthorized",
                            "message": "Missing or invalid bearer token",
                        }
                    },
                    status=401,
                )
        return self.get_response(request)
