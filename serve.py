"""Tiny static-file server for the WebUI.

Usage:
    python serve.py        # serves on http://localhost:8765
    python serve.py 9000   # custom port

Serves the `webui` app at `/` and raw exported assets at `/export_full/...`.
"""
from __future__ import annotations

import http.server
import os
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_PORT = 8765
PROJECT_ROOT = Path(__file__).parent
WEBUI_ROOT = PROJECT_ROOT / "webui"
EXPORT_FULL_ROOT = PROJECT_ROOT / "export_full"


class Handler(http.server.SimpleHTTPRequestHandler):
    _range_remaining: int | None = None

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Accept-Ranges", "bytes")
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

    def send_head(self):
        range_header = self.headers.get("Range")
        if not range_header:
            return super().send_head()

        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()

        try:
            size = os.path.getsize(path)
        except OSError:
            self.send_error(404, "File not found")
            return None

        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match:
            self.send_error(416, "Invalid range")
            return None

        start_text, end_text = match.groups()
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else size - 1
        else:
            suffix_length = int(end_text or "0")
            start = max(size - suffix_length, 0)
            end = size - 1

        if start >= size or end < start:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        end = min(end, size - 1)
        content_length = end - start + 1
        ctype = self.guess_type(path)
        file = open(path, "rb")
        file.seek(start)
        self._range_remaining = content_length
        self.send_response(206)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(content_length))
        self.send_header("Last-Modified", self.date_time_string(os.path.getmtime(path)))
        self.end_headers()
        return file

    def copyfile(self, source, outputfile) -> None:
        remaining = self._range_remaining
        if remaining is None:
            return super().copyfile(source, outputfile)

        self._range_remaining = None
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


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
