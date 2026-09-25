"""Render a serialized export payload as the text a diff can read.

Most of the export's ``game/Json`` tree is not JSON text. LevelData,
LevelScriptData and LevelScriptTemplateData carry MemoryPack payloads under a
``.json`` name, and so does ``GameplayConfig/DialogIdTable.json``. Decoding
those bytes as UTF-8 with replacement characters and diffing the result
produces mojibake that says nothing about what changed, so this module routes a
path to the maintained ``scripts.game_data`` reader that already owns it and
renders the reader's own result instead.

A path no reader routes returns ``None``. That is the honest outcome for an
opaque payload: no text, rather than noise that looks like text. The reader is
never widened here -- routing only reaches readers that exist.

The page builders keep their own routing tables where a record needs page
shape (``scripts.webui.data_inspector`` carries a kind and a lane per table).
This module exists for the consumers that only need the payload rendered as
comparable text, and both reach the same ``scripts.game_data`` readers.
"""

from __future__ import annotations

import dataclasses
import json
import struct
from typing import Any, Callable

from scripts.game_data.leveldata_binary import frame_leveldata_named_prefix
from scripts.game_data.levelscript_binary import decode_levelscript_binary_summary
from scripts.game_data.levelscript_template_binary import frame_levelscript_template
from scripts.game_data.memorypack.tables import (
    DIALOG_ID_TABLE_REL,
    decode_dialog_id_table_memorypack,
)


# What a reader raises when the payload is not the shape it proves. Anything
# else is a defect in the reader and must not be swallowed here.
READER_ERRORS = (IndexError, KeyError, TypeError, ValueError, struct.error)

JSON_ROOT = "game/Json/"


@dataclasses.dataclass(frozen=True, slots=True)
class DecodedText:
    """One payload rendered as diffable text, with its own evidence bounds."""

    text: str
    decoder: str
    coverage: str  # "whole_file" or "partial"


def _leveldata(rel_path: str, data: bytes) -> dict[str, Any]:
    return frame_leveldata_named_prefix(data)


def _levelscript(rel_path: str, data: bytes) -> dict[str, Any]:
    # The summary is keyed by the script id, which is the file's own stem.
    stem = rel_path.rsplit("/", 1)[-1].removesuffix(".json")
    return decode_levelscript_binary_summary(data, int(stem))


def _levelscript_template(rel_path: str, data: bytes) -> dict[str, Any]:
    return frame_levelscript_template(data)


def _dialog_id_table(rel_path: str, data: bytes) -> dict[str, Any]:
    return decode_dialog_id_table_memorypack(DIALOG_ID_TABLE_REL, data, len(data))


# Export-relative path prefix -> (dotted reader name, call). A prefix ending in
# ``/`` routes a whole family; one ending in ``.json`` routes a single file.
ROUTES: tuple[tuple[str, str, Callable[[str, bytes], dict[str, Any]]], ...] = (
    (
        JSON_ROOT + "LevelData/",
        "scripts.game_data.leveldata_binary.frame_leveldata_named_prefix",
        _leveldata,
    ),
    (
        JSON_ROOT + "LevelScriptData/",
        "scripts.game_data.levelscript_binary.decode_levelscript_binary_summary",
        _levelscript,
    ),
    (
        JSON_ROOT + "LevelScriptTemplateData/",
        "scripts.game_data.levelscript_template_binary.frame_levelscript_template",
        _levelscript_template,
    ),
    (
        JSON_ROOT + "GameplayConfig/DialogIdTable.json",
        "scripts.game_data.memorypack.tables.decode_dialog_id_table_memorypack",
        _dialog_id_table,
    ),
)


def _route(rel_path: str) -> tuple[str, Callable[[str, bytes], dict[str, Any]]] | None:
    normalized = rel_path.replace("\\", "/")
    for prefix, decoder, call in ROUTES:
        if normalized.startswith(prefix):
            return decoder, call
    return None


def render_decoded_payload(rel_path: str, data: bytes) -> DecodedText | None:
    """Render ``data`` through the reader that owns ``rel_path``.

    Returns ``None`` when no reader routes the path, when the reader rejects
    the payload, or when it decodes nothing. The first line of the rendered
    text names the reader and how much of the file it read, so a reader that
    covers only part of a payload cannot be mistaken for a complete view of it.
    """

    route = _route(rel_path)
    if route is None:
        return None
    decoder, call = route
    try:
        result = call(rel_path, data)
    except READER_ERRORS:
        return None
    if not isinstance(result, dict) or not result:
        return None
    consumed = result.get("bytesConsumed")
    whole = isinstance(consumed, int) and consumed == len(data)
    coverage = "whole_file" if whole else "partial"
    read = (
        f"{consumed} of {len(data)} bytes read"
        if isinstance(consumed, int)
        else f"{len(data)} bytes, read extent not recorded"
    )
    header = f"# {decoder}: {coverage}, {read}"
    body = json.dumps(result, indent=2, ensure_ascii=False, default=str, sort_keys=True)
    return DecodedText(text=f"{header}\n{body}", decoder=decoder, coverage=coverage)
