"""Package-safe access to shared script infrastructure.

Source-gap domain modules import this adapter instead of mutating ``sys.path``.
The fallback supports the maintained direct-script entry points while the
package migration is completed across the rest of ``scripts``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.common import (
    combined_non_mission_content_keys,
    md_escape,
    non_mission_content_keys,
    resolve_installed_native_inputs,
    safe_key,
    sha256_file,
    write_report_json,
    write_text_if_changed,
)
from scripts.webui.story.unity_documents import read_document_text


def read_json(path: Path, default: Any = None) -> Any:
    """``scripts.common.read_json`` that also reads game/Unity/<Type>/<name> documents.

    Source-gap inputs mix loose export files with Unity object documents, which
    live in the export's object store under their former path.
    """
    try:
        return json.loads(read_document_text(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


__all__ = [
    "combined_non_mission_content_keys",
    "md_escape",
    "non_mission_content_keys",
    "read_json",
    "resolve_installed_native_inputs",
    "safe_key",
    "sha256_file",
    "write_report_json",
    "write_text_if_changed",
]
