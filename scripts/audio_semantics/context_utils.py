"""Small shared primitives for Audio semantic evidence collectors."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


def normalize_posix(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix()


def load_json(path: Path, fallback: Any) -> Any:
    if not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def append_context(
    contexts: dict[str, list[dict[str, Any]]],
    seen: dict[str, set[str]],
    event_id: Any,
    context: dict[str, Any],
) -> None:
    key = str(event_id or "").strip().lower()
    if not key:
        return
    marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if marker in seen[key]:
        return
    seen[key].add(marker)
    contexts[key].append(context)
