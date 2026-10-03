"""Publish the maintained LevelScript template reader without changing its tier.

The builder authenticates the selected native inputs before decoding or cache
reuse. Exact named fields and bounded endpoint ranges remain the reader's own
payload; a terminal template ID alone does not close an opaque middle.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.game_data.levelscript_template_binary import (
    LevelScriptTemplateFramingError,
    frame_levelscript_template,
)
from scripts.webui.data_inspector.contract import source_descriptor


def levelscript_template_record(path: Path, export_root: Path) -> dict[str, Any]:
    relative = path.relative_to(export_root).as_posix()
    base = {
        "id": relative, "title": path.stem,
        "tags": ["level", "levelscript", "template", "memorypack"],
    }
    try:
        base["source"] = source_descriptor(
            path, export_root=export_root, media_type="application/octet-stream",
        )
        decoded = frame_levelscript_template(path.read_bytes())
    except (OSError, LevelScriptTemplateFramingError, ValueError) as exc:
        diagnostic = f"{relative}: {exc}"[:1200]
        return {
            **base, "status": "decode_error", "summary": diagnostic,
            "tags": [*base["tags"], "decode_error"], "diagnostic": diagnostic,
        }
    status = str(decoded.get("schemaStatus") or decoded.get("status") or "unknown")
    fields = decoded.get("fields") if isinstance(decoded.get("fields"), dict) else {}
    terminal = decoded.get("templateId")
    template_id = terminal.get("value") if isinstance(terminal, dict) else None
    opaque = decoded.get("opaqueMiddle")
    opaque_length = opaque.get("length") if isinstance(opaque, dict) else None
    action_map = decoded.get("actionMap")
    stop = action_map.get("unresolvedReason") if isinstance(action_map, dict) else None
    parts = [f"named fields={len(fields)}"]
    if template_id is not None:
        parts.append(f"templateId={template_id}")
    if opaque_length is not None:
        parts.append(f"opaque bytes={opaque_length}")
    return {
        **base, "status": status, "summary": "; ".join(parts),
        "tags": [*base["tags"], status],
        "searchTerms": [*fields, *([str(template_id)] if template_id is not None else [])],
        "facts": {
            "reader": "scripts.game_data.levelscript_template_binary.frame_levelscript_template",
            "decodedFieldNames": list(fields),
            "templateId": template_id,
            "serializedMemberCount": decoded.get("serializedMemberCount"),
            "bytesConsumed": decoded.get("bytesConsumed"),
            "opaqueMiddleLength": opaque_length,
            "unresolvedReason": stop,
        },
        "payload": decoded, "payloadKind": "reader",
    }
