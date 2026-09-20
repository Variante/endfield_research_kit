"""Summarize the exported MissionRuntimeAsset corpus.

``game/Json/MissionRuntimeAsset`` in the export root is the client's effective
view: for each logical file, the copy the newest VFS manifest selects
(Persistent over StreamingAssets). It is one coherent corpus, so nothing here
chooses between installed layers; consumers read that single folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def mission_runtime_file_names(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    return {path.name for path in root.glob("*.json")}


def mission_runtime_source_summary(root: Path) -> dict[str, Any]:
    return {
        "selectedRoot": root.as_posix(),
        "selection": "effective_vfs_view",
        "fileCount": len(mission_runtime_file_names(root)),
    }
