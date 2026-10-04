"""Complete re-enumerated inputs for canonical LevelScript reader receipts.

The broad raw-format package scope includes negative dependencies: adding a
route or contract can change an earlier refusal. The development import scan
only supplements that scope with external shared sources; it never narrows it.
NativeImage's path-loaded helpers and their Python helper directory are
explicit additional dependencies, including newly added helper files.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.game_data.dependency_snapshot import local_dependency_paths
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, NATIVE_MAPPER_PATH
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.levelscript-complete-reader-inputs.v1"


def complete_reader_input_paths() -> list[Path]:
    """Discover current paths afresh, including newly added schema inputs."""
    raw_root = REPO_ROOT / "scripts/game_data"
    paths = {path.resolve() for path in raw_root.rglob("*")
             if path.is_file() and path.suffix in {".py", ".json"}}
    paths.update(path.resolve() for path in local_dependency_paths(["scripts.game_data.levelscript_binary"]))
    paths.update((METADATA_HELPER_PATH.resolve(), NATIVE_MAPPER_PATH.resolve()))
    for folder in {METADATA_HELPER_PATH.parent, NATIVE_MAPPER_PATH.parent}:
        paths.update(path.resolve() for path in folder.rglob("*.py") if path.is_file())
    for path in paths:
        path.relative_to(REPO_ROOT.resolve())
        if not path.is_file():
            raise ValueError(f"levelscript-reader-inputs:missing-source:{path}")
    return sorted(paths)


def snapshot_complete_reader_inputs() -> dict[str, Any]:
    """Hash the entire current path set; saved path lists never define scope."""
    rows = []
    for path in complete_reader_input_paths():
        raw = path.read_bytes()
        rows.append({"path": path.as_posix(), "length": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest().upper()})
    return {"schema": SCHEMA, "scope": "complete-raw-package-plus-external-reader-dependencies",
            "files": rows}


def reader_input_changes(before: dict[str, Any], after: dict[str, Any], *, limit: int = 8) -> dict[str, Any]:
    """Describe a failed snapshot join with deterministic, bounded file identities."""
    previous = {row["path"]: row for row in before["files"]}
    current = {row["path"]: row for row in after["files"]}
    changes = []
    for path in sorted(previous.keys() | current.keys()):
        expected, actual = previous.get(path), current.get(path)
        if expected != actual:
            changes.append({"path": path,
                            "change": "added" if expected is None else "removed" if actual is None else "modified",
                            "expected": expected, "actual": actual})
    return {"changedFiles": len(changes), "changes": changes[:limit],
            "expectedMetadata": {key: before.get(key) for key in ("schema", "scope")},
            "actualMetadata": {key: after.get(key) for key in ("schema", "scope")}}


def require_current_reader_inputs(recorded: Any) -> dict[str, Any]:
    current = snapshot_complete_reader_inputs()
    if recorded != current:
        raise ValueError("levelscript-reader-inputs:complete-current-snapshot-mismatch")
    return current
