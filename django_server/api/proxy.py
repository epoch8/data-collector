"""Прокси запросов api/urls.py на внешний сервер (DATAPIPE_PROXY_URL).

Включается, только если задан DATAPIPE_PROXY_URL. Путь, метод, query и тело
передаются как есть; Authorization клиента заменяется на серверный
`Bearer DATAPIPE_API_TOKEN`. Локальная авторизация (ApiV1AuthMiddleware)
отрабатывает до прокси.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

log = logging.getLogger(__name__)

# Hop-by-hop и заголовки, которые выставляются заново.
_SKIP_REQUEST_HEADERS = frozenset(
    {
        "host",
        "authorization",
        "content-length",
        "connection",
        "keep-alive",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "cookie",
    }
)
_SKIP_RESPONSE_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "transfer-encoding",
        "content-length",
        "content-encoding",
        "set-cookie",
    }
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Редиректы отдаём клиенту, а не следуем им с серверным токеном."""

    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


@csrf_exempt
def proxy_view(request: HttpRequest, **_route_kwargs: str) -> HttpResponse:
    base = settings.DATAPIPE_PROXY_URL.rstrip("/")
    url = base + request.get_full_path()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in _SKIP_REQUEST_HEADERS
    }
    if settings.DATAPIPE_API_TOKEN:
        headers["Authorization"] = f"Bearer {settings.DATAPIPE_API_TOKEN}"

    body = request.body if request.method not in ("GET", "HEAD", "OPTIONS") else None
    upstream_request = urllib.request.Request(  # noqa: S310 — url из env сервера
        url,
        data=body,
        headers=headers,
        method=request.method,
    )
    try:
        upstream = _opener.open(upstream_request, timeout=settings.DATAPIPE_PROXY_TIMEOUT_SEC)
    except urllib.error.HTTPError as e:
        # 4xx/5xx (и 3xx без follow) — тоже валидный ответ апстрима.
        upstream = e
    except (urllib.error.URLError, OSError) as e:
        log.warning("proxy %s %s: %s", request.method, url, e)
        return JsonResponse({"error": "upstream_unavailable", "detail": str(e)}, status=502)

    with upstream:
        response = HttpResponse(upstream.read(), status=upstream.status)
        for key, value in upstream.headers.items():
            if key.lower() not in _SKIP_RESPONSE_HEADERS:
                response[key] = value
    return response
