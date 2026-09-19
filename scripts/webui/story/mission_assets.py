"""Resolve the effective exported MissionRuntimeAsset corpus.

The installed VFS can expose a complete Persistent MissionRuntimeAsset mirror
beside StreamingAssets. When that mirror contains every StreamingAssets JSON
file, it is the current authored override and must win as one coherent corpus.
An incomplete Persistent directory is not merged implicitly: callers fall back
to StreamingAssets so a partial patch tree cannot silently create a hybrid
mission graph.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def mission_runtime_file_names(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    return {path.name for path in root.glob("*.json")}


def mission_runtime_changed_file_names(
    streaming_root: Path,
    persistent_root: Path,
) -> list[str]:
    """Return common mission filenames whose override bytes differ."""
    common_names = (
        mission_runtime_file_names(streaming_root)
        & mission_runtime_file_names(persistent_root)
    )
    return sorted(
        name
        for name in common_names
        if (streaming_root / name).read_bytes()
        != (persistent_root / name).read_bytes()
    )


def select_complete_mission_runtime_root(
    streaming_root: Path,
    persistent_root: Path,
) -> Path:
    """Prefer Persistent only when it covers the complete base file set."""
    streaming_names = mission_runtime_file_names(streaming_root)
    persistent_names = mission_runtime_file_names(persistent_root)
    if streaming_names and streaming_names <= persistent_names:
        return persistent_root
    return streaming_root


def mission_runtime_source_summary(
    streaming_root: Path,
    persistent_root: Path,
) -> dict[str, Any]:
    streaming_names = mission_runtime_file_names(streaming_root)
    persistent_names = mission_runtime_file_names(persistent_root)
    selected = select_complete_mission_runtime_root(
        streaming_root,
        persistent_root,
    )
    changed_names = mission_runtime_changed_file_names(
        streaming_root,
        persistent_root,
    )
    return {
        "selectedRoot": selected.as_posix(),
        "selection": (
            "complete_persistent_override"
            if selected == persistent_root
            else "streaming_assets_fallback"
        ),
        "streamingFileCount": len(streaming_names),
        "persistentFileCount": len(persistent_names),
        "persistentMissingBaseFiles": sorted(
            streaming_names - persistent_names
        ),
        "persistentExtraFiles": sorted(
            persistent_names - streaming_names
        ),
        "persistentChangedBaseFileCount": len(changed_names),
        "persistentChangedBaseFiles": changed_names,
    }
