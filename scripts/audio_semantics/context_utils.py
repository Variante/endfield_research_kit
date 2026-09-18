"""Small shared primitives for Audio semantic evidence collectors."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


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


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


AUDIO_SEMANTIC_SCHEMA_VERSION = 132


SELECTION_HIRC_TYPES = frozenset({5, 6, 12, 13})


def load_json_strict(path: Path, fallback: Any) -> Any:
    """Like ``load_json`` but raises on malformed JSON instead of falling back."""
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_asset_map_objects(path: Path, required_text: str | None = None) -> Any:
    """Yield asset-map entries, optionally only those containing ``required_text``.

    The map is hundreds of megabytes and ``json.loads`` dominates a scan, so a
    caller that wants one narrow object kind can name a literal its raw block
    must contain.  The filter only skips blocks that could not have matched the
    caller's own predicate anyway.
    """

    if not path.exists():
        return
    block: list[str] = []
    depth = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not block and not line.startswith("    {"):
                continue
            block.append(line)
            depth += line.count("{") - line.count("}")
            if block and depth == 0:
                text = "".join(block)
                block = []
                if '"Container"' not in text or '"PathID"' not in text:
                    continue
                if required_text is not None and required_text not in text:
                    continue
                try:
                    yield json.loads(text.rstrip(",\r\n"))
                except json.JSONDecodeError:
                    continue
