"""Tiny static-file server for the WebUI.

Usage:
    python serve.py        # serves on http://localhost:8765
    python serve.py 9000   # custom port

Serves the `webui` app at `/` and raw exported assets at `/export_full/...`.
"""
from __future__ import annotations

import http.server
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_PORT = 8765
PROJECT_ROOT = Path(__file__).parent
WEBUI_ROOT = PROJECT_ROOT / "webui"
EXPORT_FULL_ROOT = PROJECT_ROOT / "export_full"


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        request_path = urlsplit(path).path or "/"
        root = WEBUI_ROOT
        export_full = request_path.startswith("/export_full/") or request_path == "/export_full"

        if export_full:
            root = EXPORT_FULL_ROOT
            request_path = "/" + request_path.removeprefix("/export_full").lstrip("/")

        if not export_full and request_path in ("", "/"):
            request_path = "/index.html"

        self.directory = str(root)
        return super().translate_path(request_path)

    def log_message(self, fmt, *args):
        # Quiet down access logs (keep errors).
        if args and isinstance(args[0], str) and args[0].startswith(("4", "5")):
            super().log_message(fmt, *args)


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv
    port = int(argv[1]) if len(argv) > 1 else DEFAULT_PORT

    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/"
        print(f"Serving {WEBUI_ROOT} and {EXPORT_FULL_ROOT} at {url}")
        print("Press Ctrl-C to stop.")
        if os.environ.get("WEBUI_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
