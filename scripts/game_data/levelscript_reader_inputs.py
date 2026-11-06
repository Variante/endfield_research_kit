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
from scripts.game_data.string_pool import PAGE_RE
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.levelscript-complete-reader-inputs.v1"


def snapshot_string_pool_inputs(json_dir: Path) -> dict[str, Any]:
    """Bind saved path resolutions to the complete selected exported page set."""
    root=(Path(json_dir)/'StringPool').resolve();rows=[]
    for path in sorted(root.glob('StringPool*.byte')):
        if not PAGE_RE.fullmatch(path.name):continue
        raw=path.read_bytes()
        rows.append({'path':path.as_posix(),'length':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()})
    return {'schema':'endfield.levelscript-string-pool-inputs.v1','root':root.as_posix(),'files':rows}


def complete_reader_input_paths() -> list[Path]:
    """Discover current paths afresh, including newly added schema inputs."""
    repo_root = REPO_ROOT.resolve()
    raw_root = repo_root / "scripts/game_data"
    paths = {path.resolve() for path in raw_root.rglob("*")
             if path.suffix in {".py", ".json"} and path.is_file()}
    # The dependency collector already returns resolved paths. Re-resolving
    # each path and the repository root costs thousands of Windows stat calls.
    paths.update(local_dependency_paths(["scripts.game_data.levelscript_binary"]))
    paths.update((METADATA_HELPER_PATH.resolve(), NATIVE_MAPPER_PATH.resolve()))
    for folder in {METADATA_HELPER_PATH.parent, NATIVE_MAPPER_PATH.parent}:
        paths.update(path.resolve() for path in folder.rglob("*.py") if path.is_file())
    for path in paths:
        path.relative_to(repo_root)
        if not path.is_file():
            raise ValueError(f"levelscript-reader-inputs:missing-source:{path}")
    return sorted(paths)


def snapshot_complete_reader_inputs() -> dict[str, Any]:
    """Hash current paths, or delegate an owned pending operation's identity.

    Only a direct selected validator call may use the enclosing operation's
    fresh entry identity. Independent/direct/nested validators, path discovery
    and every outer entry/exit retain full fresh enumeration and byte hashing.
    Delegated results confer no completed receipt before those outer checks.
    """
    from scripts.game_data.memorypack.operation_native_validation import _owned_reader_snapshot
    return _owned_reader_snapshot(_snapshot_complete_reader_inputs_fresh)


def _snapshot_complete_reader_inputs_fresh() -> dict[str, Any]:
    """Hash the entire current path set; saved path lists never define scope."""
    rows = []
    for path in complete_reader_input_paths():
        digest = hashlib.sha256()
        length = 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                length += len(block)
        rows.append({"path": path.as_posix(), "length": length,
                     "sha256": digest.hexdigest().upper()})
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
        valid_rows = isinstance(recorded, dict) and isinstance(recorded.get("files"), list) and all(
            isinstance(row, dict) and isinstance(row.get("path"), str) for row in recorded["files"]
        )
        changes = reader_input_changes(recorded, current) if valid_rows else {
            "recordedShape": type(recorded).__name__, "expected": "complete reader snapshot with file rows"
        }
        diagnostic = {"validator": "levelscript-reader-inputs",
                      "check": "complete-current-snapshot-mismatch", **changes}
        detail = f"changedFiles={changes.get('changedFiles', 'invalid-recorded-snapshot')}"
        first = next(iter(changes.get("changes", [])), None)
        if first:
            detail += (f"; first={first['path']}; change={first['change']}; "
                       f"expectedSha256={(first['expected'] or {}).get('sha256')}; "
                       f"actualSha256={(first['actual'] or {}).get('sha256')}")
        error = ValueError("levelscript-reader-inputs:complete-current-snapshot-mismatch: " + detail)
        error.diagnostic = diagnostic
        raise error
    return current
