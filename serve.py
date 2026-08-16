"""Tiny static-file server for the WebUI.

Usage:
    python serve.py        # serves on http://localhost:8765
    python serve.py 9000   # custom port

Serves the `webui` app at `/`, raw current exported assets at
`/export_full/...`, raw StreamingAssets/Data and Persistent/Data files at `/export_data/...`, and
saved previous-export assets at `/export_previous/...`.
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
DATA_EXPORT_ROOT_ENV = "WEBUI_DATA_EXPORT_ROOT"
DEFAULT_DATA_EXPORT_ROOT = EXPORT_FULL_ROOT / "structured" / "StreamingAssets" / "Data"
STORY_ORDER_OVERRIDE_PATH = WEBUI_ROOT / "overrides" / "story_order.json"
CHARACTER_MERGES_OVERRIDE_PATH = WEBUI_ROOT / "overrides" / "character_merges.json"
CHARACTER_NAME_OVERRIDES_PATH = WEBUI_ROOT / "overrides" / "character_name_overrides.json"
AUDIO_NOTES_OVERRIDE_PATH = WEBUI_ROOT / "overrides" / "audio_notes.json"
MAX_WRITE_BYTES = 5 * 1024 * 1024


def resolve_data_export_root() -> Path:
    env_root = os.environ.get(DATA_EXPORT_ROOT_ENV)
    if env_root:
        root = Path(env_root)
        return root if root.is_absolute() else PROJECT_ROOT / root
    return DEFAULT_DATA_EXPORT_ROOT


def resolve_previous_export_root() -> Path:
    env_root = os.environ.get("WEBUI_PREVIOUS_EXPORT_ROOT")
    if env_root:
        root = Path(env_root)
        return root if root.is_absolute() else PROJECT_ROOT / root

    feed_path = WEBUI_ROOT / "data" / "updates" / "latest.json"
    try:
        payload = json.loads(feed_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    previous_root = (
        payload.get("previousSourceRoot")
        or (payload.get("tracker") or {}).get("previousSourceRoot")
        or "export_1d2"
    )
    root = Path(str(previous_root))
    return root if root.is_absolute() else PROJECT_ROOT / root


DATA_EXPORT_ROOT = resolve_data_export_root()


ERROR_PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(code)d %(message)s &middot; Endfield Story Browser</title>
<style>
  :root {
    --bg: #f5f5f5;
    --bg-3: #ffffff;
    --border: rgba(48, 56, 65, 0.18);
    --text: #303841;
    --muted: rgba(48, 56, 65, 0.62);
    --accent: #ff5722;
    --accent-rgb: 255, 87, 34;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; min-height: 100%%;
    background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    font-size: 14px; line-height: 1.5;
  }
  body { display: flex; flex-direction: column; min-height: 100vh; }
  header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    background:
      linear-gradient(180deg, rgba(var(--accent-rgb), 0.08), rgba(var(--accent-rgb), 0)),
      var(--bg);
    font-size: 14px; font-weight: 700; letter-spacing: 0.03em;
  }
  main {
    flex: 1; display: flex; align-items: center; justify-content: center;
    padding: 32px 16px;
  }
  .error-card {
    max-width: 560px; width: 100%%;
    background: var(--bg-3);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 28px 32px;
    box-shadow: 0 2px 8px rgba(48, 56, 65, 0.05);
  }
  .error-code {
    font-size: 48px; font-weight: 700; color: var(--accent);
    line-height: 1; margin: 0 0 4px;
  }
  .error-message {
    margin: 0 0 16px;
    font-size: 18px; font-weight: 600;
  }
  .error-explain {
    margin: 0 0 20px;
    color: var(--muted); font-size: 13px;
    word-break: break-word;
  }
  .error-actions a {
    color: var(--accent); text-decoration: none; font-weight: 600;
  }
  .error-actions a:hover { text-decoration: underline; }
</style>
</head>
<body>
<header>&#32456;&#26411;&#22320;&#23545;&#35805;&#27983;&#35272;&#22120; / Endfield Story Browser</header>
<main>
  <div class="error-card">
    <p class="error-code">%(code)d</p>
    <p class="error-message">%(message)s</p>
    <p class="error-explain">%(explain)s</p>
    <p class="error-actions"><a href="/">&larr; &#36820;&#22238;&#39318;&#39029; / Back to home</a></p>
  </div>
</main>
</body>
</html>
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    _range_remaining: int | None = None
    error_message_format = ERROR_PAGE_TEMPLATE
    error_content_type = "text/html; charset=utf-8"
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".flac": "audio/flac",
        ".wav": "audio/wav",
    }

    def _redirect_webui_alias(self) -> bool:
        """Redirect the common repo-relative WebUI URL to this server's root."""
        request = urlsplit(self.path)
        if request.path not in {"/webui", "/webui/", "/webui/index.html"}:
            return False
        location = "/"
        if request.query:
            location += f"?{request.query}"
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_GET(self) -> None:
        if not self._redirect_webui_alias():
            super().do_GET()

    def do_HEAD(self) -> None:
        if not self._redirect_webui_alias():
            super().do_HEAD()

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    WRITABLE_OVERRIDES = {
        "/overrides/story_order.json": (STORY_ORDER_OVERRIDE_PATH, "validate_story_order_payload"),
        "/overrides/character_merges.json": (CHARACTER_MERGES_OVERRIDE_PATH, "validate_character_merges_payload"),
        "/overrides/character_name_overrides.json": (CHARACTER_NAME_OVERRIDES_PATH, "validate_character_name_overrides_payload"),
        "/overrides/audio_notes.json": (AUDIO_NOTES_OVERRIDE_PATH, "validate_audio_notes_payload"),
    }

    def do_PUT(self) -> None:
        request_path = urlsplit(self.path).path or "/"
        entry = self.WRITABLE_OVERRIDES.get(request_path)
        if not entry:
            self.send_error(404, "Writable endpoint not found")
            return
        target, validator_name = entry
        validator = globals()[validator_name]

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

        error = validator(payload)
        if error:
            self._send_json(400, {"ok": False, "error": error})
            return

        target = target.resolve()
        overrides_root = (WEBUI_ROOT / "overrides").resolve()
        if target.parent != overrides_root:
            self._send_json(403, {"ok": False, "error": "Refusing to write outside webui/overrides"})
            return

        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=target.parent)
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
        # "no-cache" (revalidate), not "no-store" (never cache): the browser
        # keeps the copy and sends If-Modified-Since, so unchanged files come
        # back as a tiny 304 instead of re-downloading (the asset index alone is
        # ~32 MB). Freshness is preserved because SimpleHTTPRequestHandler emits
        # Last-Modified and answers conditional requests; a rebuild bumps mtime
        # and yields a 200 with new content.
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        request_path = urlsplit(path).path or "/"
        root = WEBUI_ROOT
        export_full = request_path.startswith("/export_full/") or request_path == "/export_full"
        export_previous = request_path.startswith("/export_previous/") or request_path == "/export_previous"
        export_data = request_path.startswith("/export_data/") or request_path == "/export_data"

        if export_full:
            root = EXPORT_FULL_ROOT
            request_path = "/" + request_path.removeprefix("/export_full").lstrip("/")
        elif export_data:
            request_path = "/" + request_path.removeprefix("/export_data").lstrip("/")
            first_segment = request_path.strip("/").split("/", 1)[0]
            if (
                first_segment in {"StreamingAssets", "Persistent"}
                and (EXPORT_FULL_ROOT / "structured" / first_segment / "Data").exists()
            ):
                root = EXPORT_FULL_ROOT / "structured"
            else:
                root = DATA_EXPORT_ROOT
        elif export_previous:
            # The Updates feed can be rebuilt while this server is running.
            # Resolve its previous-export root for every request so links do
            # not remain pinned to the feed that existed at startup.
            root = resolve_previous_export_root()
            request_path = "/" + request_path.removeprefix("/export_previous").lstrip("/")

        if not export_full and not export_previous and not export_data and request_path in ("", "/"):
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


def validate_character_merges_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return "Character merges payload must be a JSON object"
    merges = payload.get("merges")
    if not isinstance(merges, dict):
        return "Character merges payload must contain a merges object"
    for source_id, target_id in merges.items():
        if not isinstance(source_id, str) or not source_id.strip():
            return "Character merge source ids must be non-empty strings"
        if not isinstance(target_id, str) or not target_id.strip():
            return f"Character merge target for {source_id!r} must be a non-empty string"
        if source_id == target_id:
            return f"Character merge source {source_id!r} cannot target itself"
    for start in merges:
        seen: set[str] = set()
        current = start
        while current in merges:
            if current in seen:
                return f"Character merge chain starting at {start!r} contains a cycle"
            seen.add(current)
            current = merges[current]
    flagged = payload.get("flagged", [])
    if not isinstance(flagged, list):
        return "Character merges payload's flagged field must be a list"
    for flagged_id in flagged:
        if not isinstance(flagged_id, str) or not flagged_id.strip():
            return "Flagged ids must be non-empty strings"
    return ""


def validate_character_name_overrides_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return "Character name overrides payload must be a JSON object"
    names = payload.get("names")
    if not isinstance(names, dict):
        return "Character name overrides payload must contain a names object"
    for character_id, name in names.items():
        if not isinstance(character_id, str) or not character_id.strip():
            return "Character name override ids must be non-empty strings"
        if not isinstance(name, str) or not name.strip():
            return f"Character name override for {character_id!r} must be a non-empty string"
    return ""


def validate_audio_notes_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return "Audio notes payload must be a JSON object"
    notes = payload.get("notes")
    if not isinstance(notes, dict):
        return "Audio notes payload must contain a notes object"
    for record_key, note in notes.items():
        if not isinstance(record_key, str) or not record_key.strip():
            return "Audio note record keys must be non-empty strings"
        if len(record_key) > 1024:
            return f"Audio note record key is too long: {record_key[:80]!r}"
        if not isinstance(note, str) or not note.strip():
            return f"Audio note for {record_key!r} must be a non-empty string"
        if len(note) > 10000:
            return f"Audio note for {record_key!r} exceeds 10000 characters"
    return ""


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv
    port = int(argv[1]) if len(argv) > 1 else DEFAULT_PORT

    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/"
        print(
            f"Serving {WEBUI_ROOT}, {EXPORT_FULL_ROOT}, {DATA_EXPORT_ROOT}, "
            f"and {resolve_previous_export_root()} at {url}"
        )
        print("Press Ctrl-C to stop.")
        if os.environ.get("WEBUI_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
