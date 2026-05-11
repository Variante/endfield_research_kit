"""Small shared helpers for WebUI builder scripts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "export_full"
OUT_DIR = ROOT / "webui" / "data"
LANG_DIR = OUT_DIR / "lang"
ASSET_DIR = OUT_DIR / "assets"
REPORTS_DIR = ROOT / "reports"


def normalize_posix(value: str | Path) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def display_extension(value: str) -> str:
    return str(value or "").strip() or "[no extension]"


def read_json(path: Path, *, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(
    path: Path,
    payload: Any,
    *,
    indent: int | None = None,
    compact: bool = True,
    trailing_newline: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    separators = (",", ":") if compact and indent is None else None
    text = json.dumps(payload, ensure_ascii=False, indent=indent, separators=separators)
    if trailing_newline:
        text += "\n"
    path.write_text(text, encoding="utf-8")
