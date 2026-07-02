"""Простой приёмочный сервис для проверки on_commit-webhook из django_server.

Принимает любой POST/PUT/PATCH (по умолчанию путь `/api/run-with-labels`),
логирует тело и заголовки, хранит последние запросы в памяти.

Эндпоинты:
  POST/PUT/PATCH <любой путь>  — принять webhook, вернуть 200 {"ok": true}
  GET  /health                 — проверка живости
  GET  /requests               — последние принятые запросы (JSON)

Только стандартная библиотека Python — без зависимостей.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("ACCEPTANCE_PORT", "8080"))
MAX_HISTORY = int(os.environ.get("ACCEPTANCE_HISTORY", "100"))

_history: deque[dict] = deque(maxlen=MAX_HISTORY)


class Handler(BaseHTTPRequestHandler):
    server_version = "acceptance/1.0"

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/health", ""):
            self._send_json(200, {"status": "ok"})
            return
        if self.path.rstrip("/") == "/requests":
            self._send_json(200, {"count": len(_history), "requests": list(_history)})
            return
        self._send_json(404, {"error": "not_found", "path": self.path})

    def _handle_webhook(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = None
        record = {
            "received_at": datetime.now(timezone.utc).isoformat(),
            "method": self.command,
            "path": self.path,
            "project_id": self.headers.get("X-Data-Collector-Project-Id"),
            "package_id": self.headers.get("X-Data-Collector-Package-Id"),
            "content_type": self.headers.get("Content-Type"),
            "body": parsed if parsed is not None else raw,
        }
        _history.appendleft(record)
        print(
            f"[acceptance] {record['method']} {record['path']} "
            f"project={record['project_id']} package={record['package_id']} "
            f"body={json.dumps(record['body'], ensure_ascii=False)}",
            flush=True,
        )
        self._send_json(200, {"ok": True, "received": record})

    def do_POST(self) -> None:  # noqa: N802
        self._handle_webhook()

    def do_PUT(self) -> None:  # noqa: N802
        self._handle_webhook()

    def do_PATCH(self) -> None:  # noqa: N802
        self._handle_webhook()

    def log_message(self, *args) -> None:  # noqa: D401 - тише встроенный лог
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[acceptance] listening on :{PORT} (history={MAX_HISTORY})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
