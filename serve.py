"""Tiny static-file server for the WebUI.

Usage:
    python serve.py        # serves on http://localhost:8765
    python serve.py 9000   # custom port

Serves the `webui` app at `/` and raw exported assets at `/export_full/...`.
"""
from __future__ import annotations

import http.server
import json
import os
import re
import sys
import tempfile
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_PORT = 8765
PROJECT_ROOT = Path(__file__).parent
WEBUI_ROOT = PROJECT_ROOT / "webui"
EXPORT_FULL_ROOT = PROJECT_ROOT / "export_full"
STORY_ORDER_OVERRIDE_PATH = WEBUI_ROOT / "overrides" / "story_order.json"
MAX_WRITE_BYTES = 5 * 1024 * 1024


class Handler(http.server.SimpleHTTPRequestHandler):
    _range_remaining: int | None = None

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self) -> None:
        request_path = urlsplit(self.path).path or "/"
        if request_path != "/overrides/story_order.json":
            self.send_error(404, "Writable endpoint not found")
            return

        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._send_json(411, {"ok": False, "error": "Missing or invalid Content-Length"})
            return
        if length <= 0 or length > MAX_WRITE_BYTES:
            self._send_json(413, {"ok": False, "error": "Request body is empty or too large"})
            return

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"ok": False, "error": f"Invalid JSON: {exc}"})
            return

        error = validate_story_order_payload(payload)
        if error:
            self._send_json(400, {"ok": False, "error": error})
            return

        target = STORY_ORDER_OVERRIDE_PATH.resolve()
        overrides_root = (WEBUI_ROOT / "overrides").resolve()
        if target.parent != overrides_root:
            self._send_json(403, {"ok": False, "error": "Refusing to write outside webui/overrides"})
            return

        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".story_order.", suffix=".tmp", dir=target.parent)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            os.replace(tmp_path, target)
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass
        self._send_json(200, {"ok": True})

    do_POST = do_PUT

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


def validate_story_order_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return "Story order payload must be a JSON object"
    missions = payload.get("missions")
    if not isinstance(missions, dict):
        return "Story order payload must contain a missions object"
    for mission_id, mission in missions.items():
        if not isinstance(mission_id, str) or not mission_id.strip():
            return "Mission ids must be non-empty strings"
        if not isinstance(mission, dict):
            return f"Mission {mission_id} must be an object with an order array"
        order = mission.get("order")
        if not isinstance(order, list):
            return f"Mission {mission_id} is missing an order array"
        seen: set[str] = set()
        for value in order:
            if not isinstance(value, str) or not value.strip():
                return f"Mission {mission_id} order contains a non-empty string requirement violation"
            if value in seen:
                return f"Mission {mission_id} order contains duplicate key {value}"
            seen.add(value)
        levels = mission.get("levels")
        if levels is not None and (
            not isinstance(levels, list)
            or any(not isinstance(value, str) or not value.strip() for value in levels)
        ):
            return f"Mission {mission_id} levels must be non-empty strings"
        level = mission.get("level")
        if level is not None and not isinstance(level, str):
            return f"Mission {mission_id} level must be a string"
        locked = mission.get("locked")
        if locked is not None and not isinstance(locked, bool):
            return f"Mission {mission_id} locked must be a boolean"
    return ""


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
