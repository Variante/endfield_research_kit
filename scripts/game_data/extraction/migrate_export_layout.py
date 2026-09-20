"""Convert a layout-v1 export root to layout v2 in place.

v1 kept both installed layers side by side (``structured/<Layer>``,
``recovered/AnimeStudio-cli/<Layer>``) and mixed extraction metadata, run
intermediates, and WebUI builder output into the export root. v2 keeps one
effective ``game/`` tree plus per-layer ``meta/`` (see scripts/source_paths.py).

Every change is a same-volume rename, so nothing is copied and nothing is
deleted. Data that has no place in v2 moves to a quarantine folder outside the
export root:

* the StreamingAssets structured dump (the Persistent dump already holds the
  effective set, because it was dumped with StreamingAssets as fallback);
* Unity outputs from bundles the Persistent manifest replaced or deleted;
* run intermediates (object-index parts, filters, the Timeline re-export);
* WebUI builder output, which the next WebUI build regenerates.

Each move is appended to a manifest before it happens, so ``--rollback``
restores the v1 tree exactly. Unknown entries, unproven Unity outputs, and
name collisions abort before anything moves.

    python -m scripts.game_data.extraction.migrate_export_layout --export-root export_full --dry-run
    python -m scripts.game_data.extraction.migrate_export_layout --export-root export_full
    python -m scripts.game_data.extraction.migrate_export_layout --export-root export_full --rollback
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


if __package__ in {None, ""}:
    raise SystemExit("Run as: python -m scripts.game_data.extraction.migrate_export_layout")

from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import INSTALLED_LAYERS, ExportLayout, ExportLayoutError
from scripts.game_data.extraction.unity_overlay import (
    EFFECTIVE,
    NO_IDENTITY_REASON,
    STALE,
    SUPERSEDED,
    UNPROVEN,
    OverlayError,
    build_path_id_slots,
    classify_output,
    load_overlay_catalog,
)

PLAN_SCHEMA = "endfield.export-layout-migration-plan.v1"
MANIFEST_NAME = "moves.jsonl"
V1_TOP_LEVEL = ("structured", "recovered", "unresolved")
STRUCTURED_GAME_FOLDERS = {"Json": "json_dir", "Video": "video_dir", "Terrain": "terrain_dir"}
UNITY_STAGES = ("convert_by_type", "json_by_type")
ANIME = ("recovered", "AnimeStudio-cli")
# Builder output and run intermediates that v1 kept in the export root.
QUARANTINED_RECOVERED_FILES = (
    "dialog_id_table_index.json",
    "story_source_links.json",
    "video_bindings.json",
)
QUARANTINED_RECOVERED_DIRS = ("audio", "audio_semantics", "WebUI", "il2cpp")
QUARANTINED_ANIME_ENTRIES = (
    "filters",
    "timeline_extract",
    "timeline_line_orders.json",
    "timeline_action_evidence.json",
)
QUARANTINED_LAYER_ENTRIES = ("map_streaming_instances", "region3d")
# Types an older exporter wrote through both stages. The current exporter writes
# them through one stage only (TextAsset: JSON through the asset-map filter), so
# the other stage's files are a second decoded copy of the same objects and go
# to the quarantine rather than into game/Unity.
SINGLE_STAGE_TYPES = {"TextAsset": "json_by_type"}


class MigrationError(RuntimeError):
    pass


@dataclass
class Move:
    src: str
    dst: str
    reason: str


def default_quarantine_root(root: Path) -> Path:
    """Repo tmp/ when it shares the export's volume, else beside the export.

    Every migration move must be a rename; a quarantine on another volume
    would turn it into a copy (or an outright failure on Windows).
    """
    identity = os.path.normcase(os.path.abspath(root))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    in_repo = REPO_ROOT / "tmp" / "game_data" / "export_v1_quarantine" / f"{root.name or 'root'}-{digest}"
    if root.exists() and _same_volume(root, in_repo):
        return in_repo
    return root.parent / f"{root.name or 'root'}.v1-quarantine"


def _same_bytes(a: Path, b: Path) -> bool:
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
        return hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
    except OSError:
        return False


_OBJECT_STEM_RE = re.compile(r"^(.*_p[0-9A-Fa-f]{16})(?=\.|$)")


def _object_stem(name: str) -> str:
    """One object's identity in an output name: through its `_p<PathID>`,
    else the name without its final extension. Embedded dots are kept."""
    match = _OBJECT_STEM_RE.match(name)
    return match.group(1) if match else Path(name).stem


def _children(path: Path) -> list[Path]:
    return sorted(path.iterdir(), key=lambda p: p.name.lower()) if path.is_dir() else []


class Planner:
    def __init__(self, root: Path, quarantine: Path, jobs: int) -> None:
        self.root = root
        self.layout = ExportLayout(root)
        self.quarantine = quarantine
        self.jobs = jobs
        self.moves: list[Move] = []
        self.unknown: list[str] = []
        self.unproven: list[dict] = []
        self.collisions: list[str] = []
        self.counts: Counter = Counter()
        self._claimed: dict[str, str] = {}

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def move(self, src: Path, dst: Path, reason: str) -> None:
        key = os.path.normcase(os.path.abspath(dst))
        if key in self._claimed:
            self.collisions.append(f"{self.rel(src)} and {self._claimed[key]} -> {dst}")
            return
        self._claimed[key] = self.rel(src)
        self.moves.append(Move(str(src), str(dst), reason))
        self.counts[reason] += 1

    def to_quarantine(self, src: Path, reason: str) -> None:
        self.move(src, self.quarantine / self.rel(src), reason)

    # -- structured/ ----------------------------------------------------------
    def plan_structured(self) -> None:
        structured = self.root / "structured"
        for entry in _children(structured):
            if entry.name == "Persistent":
                self.plan_effective_structured(entry)
            elif entry.name == "StreamingAssets":
                self.plan_base_structured(entry, structured / "Persistent")
            elif entry.name == "Audio":
                self.move(entry, self.layout.audio_dir, "game/Audio")
            else:
                self.unknown.append(self.rel(entry))

    def plan_base_structured(self, base: Path, effective: Path) -> None:
        """Quarantine the base dump only when the effective dump covers it.

        The Persistent dump was taken with StreamingAssets as fallback, so it
        normally holds every base file. A base-only file (for example one a
        base-only dump mode wrote) has no v2 copy and blocks the migration.
        """
        missing = 0
        for dirpath, _dirnames, filenames in os.walk(base):
            for name in filenames:
                relative = Path(dirpath, name).relative_to(base)
                if not (effective / relative).is_file():
                    missing += 1
                    if missing <= 20:
                        self.unproven.append({
                            "path": self.rel(Path(dirpath, name)),
                            "reason": "base-layer structured file absent from the effective dump",
                        })
        if missing > 20:
            self.unproven.append({"path": self.rel(base), "reason": f"{missing - 20} more base-only structured files"})
        if not missing:
            self.to_quarantine(base, "base-layer structured dump")

    def plan_effective_structured(self, persistent: Path) -> None:
        for entry in _children(persistent):
            if entry.name == "Table":
                self.move(entry, self.layout.table_dir, "game/Table")
            elif entry.name == "Lua":
                self.move(entry, self.layout.lua_dir, "game/Lua")
            elif entry.name == "Data":
                for data_entry in _children(entry):
                    attribute = STRUCTURED_GAME_FOLDERS.get(data_entry.name)
                    if attribute is None:
                        self.unknown.append(self.rel(data_entry))
                    else:
                        self.move(data_entry, getattr(self.layout, attribute), f"game/{data_entry.name}")
            else:
                self.unknown.append(self.rel(entry))

    # -- recovered/ -----------------------------------------------------------
    def plan_recovered(self) -> None:
        recovered = self.root / "recovered"
        for entry in _children(recovered):
            if entry.name == "AnimeStudio-cli":
                self.plan_animestudio(entry)
            elif entry.name in QUARANTINED_RECOVERED_FILES or entry.name in QUARANTINED_RECOVERED_DIRS:
                self.to_quarantine(entry, "WebUI builder output")
            else:
                self.unknown.append(self.rel(entry))

    def plan_animestudio(self, anime: Path) -> None:
        for entry in _children(anime):
            if entry.name in INSTALLED_LAYERS:
                self.plan_layer_meta(entry.name, entry)
            elif entry.name == "Maps":
                for item in _children(entry):
                    self.move(item, self.layout.cab_map_dir / item.name, "meta/cab_map")
            elif entry.name == "local_incremental":
                for item in _children(entry):
                    self.move(item, self.layout.extraction_incremental_dir / item.name, "meta/extraction/incremental")
            elif entry.name in QUARANTINED_ANIME_ENTRIES:
                self.to_quarantine(entry, "run intermediate or builder output")
            else:
                self.unknown.append(self.rel(entry))

    def plan_layer_meta(self, layer: str, layer_dir: Path) -> None:
        for entry in _children(layer_dir):
            if entry.name in UNITY_STAGES:
                continue  # planned by plan_unity once every layer's catalogue is known
            if entry.name == "maps":
                target = self.layout.asset_map_dir(layer)
            elif entry.name == "vfs_index":
                target = self.layout.vfs_index_dir(layer)
            elif entry.name == "asset_status":
                target = self.layout.asset_status_dir(layer)
            elif entry.name == "renderer_index":
                target = self.layout.renderer_index_dir(layer)
            elif entry.name == "object_index":
                for item in _children(entry):
                    if item.name == "parts":
                        self.to_quarantine(item, "object-index merge input")
                    else:
                        self.move(item, self.layout.object_index_dir(layer) / item.name, "meta/object_index")
                continue
            elif entry.name in QUARANTINED_LAYER_ENTRIES:
                self.to_quarantine(entry, "WebUI builder output")
                continue
            else:
                self.unknown.append(self.rel(entry))
                continue
            for item in _children(entry):
                self.move(item, target / item.name, f"meta/{entry.name}")

    # -- Unity outputs --------------------------------------------------------
    def plan_unity(self) -> dict:
        anime = self.root.joinpath(*ANIME)
        base, effective = INSTALLED_LAYERS[0], INSTALLED_LAYERS[-1]
        catalog = load_overlay_catalog(anime / base / "vfs_index", anime / effective / "vfs_index")
        type_owner: dict[str, str] = {}
        # Newest layer first, so a base-layer copy of the same output name meets
        # the newer layer's claim and is compared against it.
        for layer in reversed(INSTALLED_LAYERS):
            maps = sorted((anime / layer / "maps").glob("*.json"))
            if not maps:
                raise MigrationError(f"{layer} has no asset map under {anime / layer / 'maps'}")
            self.mapped_types = set()
            path_id_slots = build_path_id_slots(maps, self.mapped_types)
            for stage in UNITY_STAGES:
                for type_dir in _children(anime / layer / stage):
                    kept_stage = SINGLE_STAGE_TYPES.get(type_dir.name)
                    if kept_stage is not None and kept_stage != stage:
                        self.plan_second_representation(type_dir, anime / layer / kept_stage / type_dir.name)
                        continue
                    owner = type_owner.setdefault(type_dir.name, stage)
                    if owner != stage:
                        raise MigrationError(f"Unity type {type_dir.name} is exported by both {owner} and {stage}")
                    self.plan_unity_type(layer, type_dir, catalog, path_id_slots)
        return {
            "blocks": catalog.block_evidence,
            "supersededBaseSlots": len(catalog.superseded_base_slots()),
            "deletedLogicalFiles": sorted(catalog.deleted_logical_files()),
        }

    def plan_second_representation(self, type_dir: Path, kept_dir: Path) -> None:
        """Quarantine a file only when the kept stage holds the same object.

        The same object is the same name up to the extension. A file with no
        kept sibling is its object's only copy, so it blocks the migration.
        """
        kept_stems = {_object_stem(entry.name) for entry in _children(kept_dir)}
        for entry in _children(type_dir):
            if _object_stem(entry.name) in kept_stems:
                self.to_quarantine(entry, f"second representation of a {kept_dir.parent.name} {type_dir.name} output")
            else:
                self.unproven.append({
                    "path": self.rel(entry),
                    "reason": f"only copy of this object is in the retired {type_dir.parent.name} stage",
                })

    def plan_unity_type(self, layer: str, type_dir: Path, catalog, path_id_slots) -> None:
        mapped_types = self.mapped_types
        files = [entry for entry in _children(type_dir)]
        dirs = [entry for entry in files if entry.is_dir()]
        if dirs:
            self.unknown.extend(self.rel(entry) for entry in dirs)
            return

        def verdict(path: Path) -> tuple[Path, str, str]:
            return (path, *classify_output(path, catalog, path_id_slots))

        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            results = list(pool.map(verdict, files, chunksize=256))
        target = self.layout.unity_type_dir(type_dir.name)
        effective_layer = INSTALLED_LAYERS[-1]
        effective_names = {
            entry.name for stage in UNITY_STAGES
            for entry in _children(self.root.joinpath(*ANIME, effective_layer, stage, type_dir.name))
        }
        for path, result, reason in results:
            no_identity = reason == NO_IDENTITY_REASON or (
                # The asset maps index only some Unity types; a type they do
                # not cover (AnimatorOverrideController) has no slot to prove.
                reason.endswith("is not in the asset maps") and type_dir.name not in mapped_types
            )
            if result == UNPROVEN and no_identity:
                # Exporter companions (FBX textures) and identity-less JSON
                # carry no source slot. For this one-time bridge the newer
                # layer wins by name; the next export records real identity.
                result = SUPERSEDED if layer != effective_layer and path.name in effective_names else EFFECTIVE
                reason = "no recorded identity; newer layer wins by name"
                self.counts[f"unity {layer}/{type_dir.name} nameOnly {result}"] += 1
            self.counts[f"unity {layer}/{type_dir.name} {result}"] += 1
            if result == EFFECTIVE:
                claimed = self._claimed.get(os.path.normcase(os.path.abspath(target / path.name)))
                if claimed is not None and _same_bytes(self.root / claimed, path):
                    # One asset packed into a live base bundle and a newer
                    # bundle: the newer layer's identical file already covers it.
                    self.to_quarantine(path, "identical copy of a newer-layer output")
                    continue
                self.move(path, target / path.name, "game/Unity")
            elif result == SUPERSEDED:
                self.to_quarantine(path, "Unity output from a replaced or deleted bundle")
            elif result == STALE:
                self.to_quarantine(path, "stale Unity output: its chunk belongs to an older build")
            else:
                self.unproven.append({"path": self.rel(path), "reason": reason})

    # -- entry point ----------------------------------------------------------
    def plan(self) -> dict:
        if not self.root.is_dir():
            raise MigrationError(f"export root does not exist: {self.root}")
        if self.layout.layout_file.exists():
            raise MigrationError(f"{self.root} already has {self.layout.layout_file.name}; it is not a v1 root")
        for entry in _children(self.root):
            if entry.name not in V1_TOP_LEVEL:
                self.unknown.append(self.rel(entry))
        self.plan_structured()
        self.plan_recovered()
        overlay = self.plan_unity()
        for entry in _children(self.root / "unresolved"):
            self.move(entry, self.layout.extraction_failures_dir / entry.name, "meta/extraction/failures")
        return {
            "schema": PLAN_SCHEMA,
            "exportRoot": str(self.root),
            "quarantineRoot": str(self.quarantine),
            "generatedAt": int(time.time()),
            "overlay": overlay,
            "counts": dict(sorted(self.counts.items())),
            "unknownEntries": self.unknown,
            "unprovenOutputCount": len(self.unproven),
            "unprovenSamples": self.unproven[:200],
            "collisions": self.collisions[:200],
            "moveCount": len(self.moves),
        }


def _same_volume(a: Path, b: Path) -> bool:
    probe = b
    while not probe.exists():
        probe = probe.parent
    return os.stat(a).st_dev == os.stat(probe).st_dev


def execute(root: Path, quarantine: Path, moves: list[Move]) -> None:
    layout = ExportLayout(root)
    if not _same_volume(root, quarantine):
        raise MigrationError(f"quarantine {quarantine} is on another volume than {root}; renames would copy")
    quarantine.mkdir(parents=True, exist_ok=True)
    manifest = quarantine / MANIFEST_NAME
    if manifest.exists():
        raise MigrationError(f"{manifest} exists; roll back or remove the previous migration first")
    layout.begin_write(migratedFrom="v1", quarantineRoot=str(quarantine))
    with manifest.open("a", encoding="utf-8") as handle:
        for index, move in enumerate(moves, 1):
            src, dst = Path(move.src), Path(move.dst)
            if not src.exists():
                raise MigrationError(f"planned source vanished: {src}")
            if dst.exists():
                raise MigrationError(f"target already exists: {dst}")
            handle.write(json.dumps({"src": move.src, "dst": move.dst}, ensure_ascii=False) + "\n")
            handle.flush()
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src, dst)
            if index % 100000 == 0:
                print(f"  moved {index}/{len(moves)}", flush=True)
    for top in V1_TOP_LEVEL:
        _remove_empty_tree(root / top)
    leftovers = [name for name in V1_TOP_LEVEL if (root / name).exists()]
    if leftovers:
        raise MigrationError(f"v1 folders still hold files after migration: {leftovers}")
    layout.finish_write(migratedFrom="v1", quarantineRoot=str(quarantine), migratedAt=int(time.time()))


def _remove_empty_tree(path: Path) -> None:
    if not path.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        if not filenames and not os.listdir(dirpath):
            os.rmdir(dirpath)


def rollback(root: Path, quarantine: Path) -> int:
    manifest = quarantine / MANIFEST_NAME
    if not manifest.is_file():
        raise MigrationError(f"no migration manifest at {manifest}")
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    skipped: list[str] = []
    for row in reversed(rows):
        src, dst = Path(row["src"]), Path(row["dst"])
        if dst.exists() and not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            os.replace(dst, src)
        elif src.exists() and not dst.exists():
            # Logged but never performed (an interrupted run, whose last row
            # is written before its rename), or already restored by an
            # earlier rollback attempt: nothing to undo.
            continue
        else:
            # Both present or both missing: a real conflict; keep the manifest.
            skipped.append(f"{dst} -> {src}")
    if skipped:
        raise MigrationError(
            f"rollback could not restore {len(skipped)} of {len(rows)} move(s); the manifest is kept. "
            f"First: {skipped[:3]}"
        )
    layout_file = ExportLayout(root).layout_file
    if layout_file.exists():
        layout_file.unlink()
    for folder in ("game", "meta"):
        _remove_empty_tree(root / folder)
    manifest.rename(manifest.with_name(f"{MANIFEST_NAME}.rolled-back-{int(time.time())}"))
    return len(rows)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--quarantine-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Plan and report; move nothing.")
    parser.add_argument("--rollback", action="store_true", help="Undo a migration from its manifest.")
    parser.add_argument("--jobs", type=int, default=16, help="Parallel readers while classifying Unity outputs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = ExportLayout(args.export_root).root
    quarantine = args.quarantine_root or default_quarantine_root(root)
    try:
        if args.rollback:
            restored = rollback(root, quarantine)
            print(f"rolled back {restored} move(s); {root} is a v1 root again")
            return 0
        planner = Planner(root, quarantine, args.jobs)
        report = planner.plan()
        report_path = ExportLayout(root).work_dir / "migration_plan.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k not in ("unprovenSamples",)}, ensure_ascii=False, indent=2))
        print(f"plan written to {report_path}")
        blocking = report["unknownEntries"] or report["unprovenOutputCount"] or report["collisions"]
        if blocking:
            print("migration blocked: resolve unknown entries, unproven outputs, and collisions first", file=sys.stderr)
            return 1
        if args.dry_run:
            return 0
        execute(root, quarantine, planner.moves)
        print(f"migrated {len(planner.moves)} entries; quarantine at {quarantine}")
        return 0
    except (MigrationError, OverlayError, ExportLayoutError) as exc:
        print(f"migrate_export_layout: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
