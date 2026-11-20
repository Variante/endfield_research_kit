"""Remove Assets selection folders that no published index references.

Each optional Assets projection stages its files in a fresh
``<owned folder>/selection-*`` directory and publishes that path only after the
whole selection validated, so a failed build never leaves the page reading a
half-written folder. The cost is that every successful build leaves the
previous selection behind. Once the index naming the new selection is written,
the older folders are unreachable from the page and are deleted here.

Only direct ``selection-*`` children of an owned folder are touched. When the
published path is not such a child, the current selection cannot be told apart
from the stale ones, so that folder is left untouched. The index is already
written by then, so pruning never fails a build; it only deletes less.
"""
from __future__ import annotations

from pathlib import Path
import shutil

# Asset index ``sourceRoots`` key -> folder under the Assets data directory.
INDEX_SELECTION_FOLDERS = {
    "Collision": "collision",
    "CollisionPrefab": "collision_prefabs",
    "StoredRender": "stored_render",
}


def prune_superseded_selections(folder: Path, keep: Path | None) -> list[Path]:
    """Delete every ``selection-*`` directory in ``folder`` except ``keep``."""
    folder = folder.resolve()
    if keep is not None:
        keep = keep.resolve()
        if keep.parent != folder or not keep.name.startswith("selection-"):
            return []
    if not folder.is_dir():
        return []
    removed = []
    for child in sorted(folder.iterdir()):
        if child.name.startswith("selection-") and child.is_dir() and not child.is_symlink() and child != keep:
            shutil.rmtree(child)
            removed.append(child)
    return removed


def prune_index_selections(payload: dict, *, root: Path, asset_dir: Path) -> list[Path]:
    """Keep only the selections the just-written Assets index publishes."""
    source_roots = payload.get("sourceRoots", {})
    removed = []
    for key, name in INDEX_SELECTION_FOLDERS.items():
        published = source_roots.get(key)
        removed += prune_superseded_selections(asset_dir / name, root / published if published else None)
    return removed
