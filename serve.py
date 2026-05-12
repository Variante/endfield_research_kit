"""Tiny static-file server for the unified browser.

Usage:
    python serve.py        # serves on http://localhost:8765
    python serve.py 9000   # custom port

Serves the `webui` app at `/` and raw exported assets at `/exported/...`.
Opens your default browser automatically.
"""
from __future__ import annotations

import http.server
import socketserver
import sys
import webbrowser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

DEFAULT_PORT = 8765
PROJECT_ROOT = Path(__file__).resolve().parent
WEBUI_ROOT = PROJECT_ROOT / "webui"
EXPORTED_ROOT = PROJECT_ROOT / "export_full"


def safe_join(base: Path, raw_path: str) -> Path:
    """Resolve a URL path under a fixed base directory."""
    cur = base.resolve()
    for part in PurePosixPath(raw_path).parts:
        if part in ("", "."):
            continue
        if part == "..":
            return base.resolve()
        cur = cur / part
    resolved = cur.resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError:
        return base.resolve()
    return resolved


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        request_path = unquote(urlsplit(path).path or "/")

        if request_path.startswith("/exported/") or request_path == "/exported":
            rel = request_path[len("/exported/"):] if request_path != "/exported" else ""
            return str(safe_join(EXPORTED_ROOT, rel))

        if request_path in ("", "/"):
            request_path = "/index.html"
        return str(safe_join(WEBUI_ROOT, request_path.lstrip("/")))

    def log_message(self, fmt, *args):
        # Quiet down access logs (keep errors).
        if args and isinstance(args[0], str) and args[0].startswith(("4", "5")):
            super().log_message(fmt, *args)


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def parse_port(argv: list[str]) -> int:
    if len(argv) <= 1:
        return DEFAULT_PORT
    try:
        return int(argv[1])
    except ValueError as exc:
        raise SystemExit(f"Invalid port: {argv[1]!r}") from exc


def main(argv: list[str] | None = None) -> None:
    port = parse_port(argv or sys.argv)
    story_index = WEBUI_ROOT / "data" / "index.json"
    asset_index = WEBUI_ROOT / "data" / "assets" / "index.json"

    if not WEBUI_ROOT.exists():
        print(f"webui/ directory not found: {WEBUI_ROOT}")
        sys.exit(1)

    if not story_index.exists():
        print("Required story build output not found:")
        print(" -", story_index)
        print("Run the preprocessor first:  python scripts/webui/build_story.py")
        sys.exit(1)

    if not EXPORTED_ROOT.exists():
        print(f"exported/ directory not found: {EXPORTED_ROOT}")
        sys.exit(1)

    if not asset_index.exists():
        print("Warning: asset index not found.")
        print("The story browser will still work.")
        print("Build the asset index when needed:  python scripts/webui/build_assets.py")

    with ReusableThreadingTCPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/"
        print(f"Serving {WEBUI_ROOT} and {EXPORTED_ROOT} at {url}")
        print("Press Ctrl-C to stop.")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
