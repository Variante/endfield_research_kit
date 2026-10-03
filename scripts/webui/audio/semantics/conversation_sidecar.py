"""Audio's per-conversation sidecars, which the Story page merges.

Audio never edits Story's published conversations
(``lang/<code>/conv/<key>.json``). What it links to one -- the voice file of
each line, the files behind its conversation and cutscene audio events, its
dialog lifecycle hooks -- goes into ``lang/<code>/audio/conv/<key>.json``, and
the Story page merges that file when it opens the conversation. A Story rebuild
therefore keeps its voice lines, and Story builds without Audio.

A line row names the line by position and id (``index``, ``id``); the page
applies it to the line at that position when the id still matches, else to the
first line with that id, so a Story rebuild that moves a line does not
misattach its voice.

Each Audio stage owns some top-level fields and replaces only those, so the
relink and the semantic refresh can each run alone. ``index.json`` beside the
sidecars lists the conversations that have one, so the page fetches only those.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from scripts.webui.audio.semantics.context_utils import json_dump, load_json
from scripts.webui.search import linked_file_search_text

SCHEMA_VERSION = 1
INDEX_NAME = "index.json"
#: Written by the relink in build_audio.py.
LINK_FIELDS = ("lines", "audioFiles", "cutscene")
#: Written by the semantic refresh in build_audio_semantics.py.
LIFECYCLE_FIELDS = ("dialogLifecycleAudio",)


def sidecar_dir(webui_root: Path, language: str) -> Path:
    return webui_root / "data" / "lang" / language.upper() / "audio" / "conv"


def load_sidecar(directory: Path, key: str) -> dict[str, Any]:
    payload = load_json(directory / f"{key}.json", {})
    return payload if isinstance(payload, dict) else {}


def line_rows_by_index(sidecar: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        row["index"]: row
        for row in sidecar.get("lines") or ()
        if isinstance(row, dict) and isinstance(row.get("index"), int)
    }


def line_audio(rows: Mapping[int, Mapping[str, Any]], index: int, line: Mapping[str, Any]) -> Mapping[str, Any]:
    """The sidecar row for ``line`` at ``index``, or ``{}`` when the ids differ."""
    row = rows.get(index) or {}
    return row if str(row.get("id") or "") == str(line.get("id") or "") else {}


def update_sidecars(directory: Path, fields: tuple[str, ...], payload_by_key: Mapping[str, Mapping[str, Any]]) -> int:
    """Replace ``fields`` in every sidecar with ``payload_by_key``'s values.

    A conversation missing from ``payload_by_key`` loses those fields, and a
    sidecar left without any field is removed; fields other stages own are
    kept. Returns the number of sidecars written or removed.
    """
    directory.mkdir(parents=True, exist_ok=True)
    existing = {path.stem for path in directory.glob("*.json") if path.name != INDEX_NAME}
    changed = 0
    kept: list[str] = []
    file_search: dict[str, str] = {}
    for key in sorted(existing | set(payload_by_key)):
        current = load_sidecar(directory, key) if key in existing else {}
        updated = {name: value for name, value in current.items() if name not in fields and name != "schemaVersion"}
        updated.update(
            (name, value)
            for name, value in (payload_by_key.get(key) or {}).items()
            if name in fields and value not in (None, [], {})
        )
        path = directory / f"{key}.json"
        if not updated:
            if key in existing:
                path.unlink()
                changed += 1
            continue
        payload = {"schemaVersion": SCHEMA_VERSION, **dict(sorted(updated.items()))}
        kept.append(key)
        text = linked_file_search_text(payload)
        if text:
            file_search[key] = text
        if payload != current:
            json_dump(path, payload)
            changed += 1
    index = {"schemaVersion": SCHEMA_VERSION, "conversations": kept, "linkedFileSearch": file_search}
    if load_json(directory / INDEX_NAME, None) != index:
        json_dump(directory / INDEX_NAME, index)
    return changed
