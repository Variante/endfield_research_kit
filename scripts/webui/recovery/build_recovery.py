#!/usr/bin/env python3
"""Build the WebUI Recovery-progress page data.

The page answers one question: how far has understanding of the installed game
data got. It publishes one volume per VFS block type and, under each block, the
declared logical-file families with their four per-level stages.

* Volumes (files, declared and profiled bytes, container chunks) are measured
  from the VFS payload profile under ``reports/``.
* Family path patterns and stages are declared in ``recovery_declarations.json``
  beside this module, each stage citing the memory topic it reads.
* The four level definitions are read from ``memory/game_data/README.md``.
* Under the Unity bundle family, objects per Unity type are measured from the
  export's AnimeStudio asset maps, joined to their block through the export's
  VFS index; each type's stages are declared like a family's.

There is no progress score: a stage is a state with a stated boundary, never a
number, and "framed and named" is never published as "understood".

Run from the repository root::

    python -m scripts.webui.recovery.build_recovery
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.recovery.build_recovery"
    )

from scripts.common import EXPORT_LAYOUT, OUT_DIR, REPORTS_DIR, ROOT, write_canonical_json
from scripts.source_paths import ExportLayout
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.recovery-progress.v5"
DECLARATIONS_SCHEMA = "endfield.recovery-progress-declarations.v4"

DECLARATIONS_PATH = Path(__file__).resolve().parent / "recovery_declarations.json"
MEMORY_INDEX_PATH = REPO_ROOT / "memory" / "game_data" / "README.md"
VFS_PROFILE_PATH = REPORTS_DIR / "animestudio" / "vfs_payload_profile_files_latest.jsonl.gz"
DEFAULT_OUTPUT = OUT_DIR / "recovery" / "index.json"

# Installed layers in overlay order: Persistent replaces StreamingAssets, so an
# object present in both is counted once, from Persistent.
ASSET_MAP_LAYERS = ("Persistent", "StreamingAssets")

# The profiler's row statuses (EndfieldVfsCorpusClassifier), mapped to what they
# mean for local availability. Only "profiled" rows had their payload read from
# a verified metadata selection. "excluded"/"unavailable" rows are declared by
# the catalog but their chunks are not installed, so their declared size was
# never read. A status outside this table means the profiler changed, and the
# build fails closed rather than guessing which side it belongs on.
PROFILE_STATUS_AVAILABILITY = {
    "profiled": "profiled",
    "excluded": "absent",
    "unavailable": "absent",
    "metadata_unverified": "unverified",
    "failed": "failed",
    "short_read": "failed",
    "input_missing": "failed",
}
AVAILABILITY_ORDER = ("profiled", "absent", "unverified", "failed")

# The family every block gets for paths no declared pattern matches. It is
# always published when non-empty, so an unexpected path shape stays visible.
OTHER_FAMILY_ID = "_other"

# Sample virtual paths kept per family, so a reviewer can see what a pattern (or
# the unclassified remainder) actually caught.
FAMILY_SAMPLE_PATHS = 3


class RecoveryInputError(RuntimeError):
    """A required input is missing, unreadable, or does not match its schema."""


# --------------------------------------------------------------------------
# input readers -- each one fails closed


def _require_file(path: Path, what: str) -> Path:
    if not path.is_file():
        raise RecoveryInputError(f"{what} is missing: {path}")
    return path


def _read_json_object(path: Path, what: str, expected_schema: str | None = None) -> dict[str, Any]:
    _require_file(path, what)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryInputError(f"{what} could not be read as JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RecoveryInputError(f"{what} is not a JSON object: {path}")
    if expected_schema is not None:
        found = payload.get("schema")
        if found != expected_schema:
            raise RecoveryInputError(
                f"{what} has schema {found!r}, expected {expected_schema!r}: {path}"
            )
    return payload


def load_declarations(path: Path = DECLARATIONS_PATH) -> dict[str, Any]:
    payload = _read_json_object(path, "recovery declarations", DECLARATIONS_SCHEMA)
    for key in (
        "lanes",
        "stageStates",
        "stageTemplates",
        "familySets",
        "vfsBlocks",
        "unreachableFromStaticData",
        "unityObjectTypes",
    ):
        if key not in payload:
            raise RecoveryInputError(f"recovery declarations are missing {key!r}: {path}")
    return payload


# --------------------------------------------------------------------------
# VFS block and family declarations -- validated before any byte is counted


def _require_text(node: dict[str, Any], key: str, where: str) -> str:
    value = node.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RecoveryInputError(f"{where} has no {key!r}")
    return value


def _resolve_stage_states(declarations: dict[str, Any]) -> dict[str, dict[str, Any]]:
    block = declarations["stageStates"]
    entries = block.get("entries") if isinstance(block, dict) else None
    order = block.get("order") if isinstance(block, dict) else None
    if not isinstance(entries, dict) or not isinstance(order, list) or set(order) != set(entries):
        raise RecoveryInputError("stageStates must list every entry in 'order' exactly once")
    states: dict[str, dict[str, Any]] = {}
    for name in order:
        entry = entries[name]
        where = f"stage state {name!r}"
        if not isinstance(entry, dict) or not isinstance(entry.get("rank"), int):
            raise RecoveryInputError(f"{where} has no integer rank")
        for key in ("label", "labelZh", "meaning", "meaningZh"):
            _require_text(entry, key, where)
        states[name] = {"id": name, **entry}
    return states


def _resolve_stage(
    raw: Any,
    *,
    templates: dict[str, Any],
    states: dict[str, dict[str, Any]],
    elimination_ids: set[str],
    repo_root: Path,
    where: str,
) -> dict[str, Any]:
    if isinstance(raw, dict) and "template" in raw:
        name = raw["template"]
        template = templates.get(name)
        if not isinstance(template, dict) or name.startswith("_"):
            raise RecoveryInputError(f"{where} references unknown stage template {name!r}")
        raw = template
    if not isinstance(raw, dict):
        raise RecoveryInputError(f"{where} is not an object")
    level = raw.get("level")
    state = raw.get("state")
    if level not in (1, 2, 3, 4):
        raise RecoveryInputError(f"{where} has level {level!r}, expected 1..4")
    if state not in states:
        raise RecoveryInputError(f"{where} has unknown state {state!r}")
    text = _require_text(raw, "text", where)
    text_zh = _require_text(raw, "textZh", where)
    source = _require_text(raw, "source", where)
    # A cited source that no longer exists is a stale declaration, not a
    # citation: fail rather than publish a dead reference.
    if not (repo_root / source.split("#", 1)[0]).is_file():
        raise RecoveryInputError(f"{where} cites a source that does not exist: {source}")
    eliminations = raw.get("eliminations", [])
    if not isinstance(eliminations, list) or any(item not in elimination_ids for item in eliminations):
        raise RecoveryInputError(
            f"{where} references an unknown elimination: {eliminations!r}"
        )
    return {
        "level": level,
        "state": state,
        "text": text,
        "textZh": text_zh,
        "source": source,
        "eliminations": list(eliminations),
    }


def _resolve_stages(
    raw_stages: Any,
    *,
    templates: dict[str, Any],
    states: dict[str, dict[str, Any]],
    elimination_ids: set[str],
    repo_root: Path,
    where: str,
) -> list[dict[str, Any]]:
    """Resolve and validate one family's four stages.

    Three rules are enforced because a violation would overclaim:

    * exactly one stage per level 1..4, so an unknown stage stays visible
      instead of silently missing;
    * no stage is stronger than the stage below it -- a level can only be
      answered once the one below is (``memory/game_data/README.md``);
    * level 4 is never ``closed``. What a whole family *means* is not
      established by one consumer, and no report measures it per family.
    """
    if not isinstance(raw_stages, list) or len(raw_stages) != 4:
        raise RecoveryInputError(f"{where} must declare exactly four stages")
    stages = [
        _resolve_stage(
            raw,
            templates=templates,
            states=states,
            elimination_ids=elimination_ids,
            repo_root=repo_root,
            where=f"{where} stage {index + 1}",
        )
        for index, raw in enumerate(raw_stages)
    ]
    if [stage["level"] for stage in stages] != [1, 2, 3, 4]:
        raise RecoveryInputError(f"{where} stages must be levels 1, 2, 3, 4 in order")
    for lower, upper in zip(stages, stages[1:]):
        if states[upper["state"]]["rank"] > states[lower["state"]]["rank"]:
            raise RecoveryInputError(
                f"{where} declares level {upper['level']} {upper['state']!r} above "
                f"level {lower['level']} {lower['state']!r}; a level cannot be "
                "answered further than the level below it"
            )
    if stages[3]["state"] == "closed":
        raise RecoveryInputError(
            f"{where} declares level 4 closed; whole-family meaning is never "
            "declared closed -- use 'partial' and name the consumer scope"
        )
    return stages


def resolve_vfs_blocks(
    declarations: dict[str, Any],
    *,
    lane_ids: set[str],
    repo_root: Path = REPO_ROOT,
) -> list[dict[str, Any]]:
    """Validate the declared VFS blocks and families and compile their patterns.

    Fails closed on every shape problem, so a malformed declaration never
    reaches the page as an empty or partial explorer.
    """
    states = _resolve_stage_states(declarations)
    templates = declarations["stageTemplates"]
    family_sets = declarations["familySets"]
    elimination_ids = {
        item.get("id")
        for item in declarations["unreachableFromStaticData"].get("items", [])
        if isinstance(item, dict)
    }
    vfs = declarations["vfsBlocks"]
    entries = vfs.get("entries") if isinstance(vfs, dict) else None
    if not isinstance(entries, list) or not entries:
        raise RecoveryInputError("vfsBlocks has no entries list")

    blocks: list[dict[str, Any]] = []
    seen_enum: set[str] = set()
    seen_raw: set[int] = set()
    seen_profile: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RecoveryInputError("a vfsBlocks entry is not an object")
        enum_name = _require_text(entry, "enumName", "a vfsBlocks entry")
        where = f"VFS block {enum_name!r}"
        raw_id = entry.get("rawId")
        if not isinstance(raw_id, int) or isinstance(raw_id, bool):
            raise RecoveryInputError(f"{where} has no integer rawId")
        profile_name = _require_text(entry, "profileName", where)
        for key, value, seen in (
            ("enumName", enum_name, seen_enum),
            ("rawId", raw_id, seen_raw),
            ("profileName", profile_name, seen_profile),
        ):
            if value in seen:
                raise RecoveryInputError(f"{where} repeats {key} {value!r}")
            seen.add(value)
        lane = entry.get("lane")
        if lane not in lane_ids:
            raise RecoveryInputError(f"{where} maps to undeclared lane {lane!r}")
        also = entry.get("alsoLanes", [])
        if not isinstance(also, list) or any(item not in lane_ids for item in also):
            raise RecoveryInputError(f"{where} has an undeclared alsoLanes entry: {also!r}")

        if "familySet" in entry:
            if "families" in entry:
                raise RecoveryInputError(f"{where} declares both familySet and families")
            raw_families = family_sets.get(entry["familySet"])
            if not isinstance(raw_families, list) or str(entry["familySet"]).startswith("_"):
                raise RecoveryInputError(
                    f"{where} references unknown family set {entry['familySet']!r}"
                )
        else:
            raw_families = entry.get("families")
            if not isinstance(raw_families, list):
                raise RecoveryInputError(f"{where} has no families list")

        families: list[dict[str, Any]] = []
        by_id: dict[str, dict[str, Any]] = {}
        for raw_family in raw_families:
            if not isinstance(raw_family, dict):
                raise RecoveryInputError(f"{where} has a family that is not an object")
            family_id = _require_text(raw_family, "id", f"a family of {where}")
            family_where = f"{where} family {family_id!r}"
            if family_id in by_id or family_id == OTHER_FAMILY_ID:
                raise RecoveryInputError(f"{family_where} repeats or reserves its id")
            pattern_text = _require_text(raw_family, "pathRegex", family_where)
            try:
                pattern = re.compile(pattern_text)
            except re.error as exc:
                raise RecoveryInputError(f"{family_where} has an invalid pathRegex: {exc}") from exc
            if "stagesFrom" in raw_family:
                if "stages" in raw_family:
                    raise RecoveryInputError(f"{family_where} declares both stages and stagesFrom")
                donor = by_id.get(raw_family["stagesFrom"])
                if donor is None:
                    raise RecoveryInputError(
                        f"{family_where} takes stages from {raw_family['stagesFrom']!r}, "
                        "which is not an earlier family of the same block"
                    )
                stages = [dict(stage) for stage in donor["stages"]]
            else:
                stages = _resolve_stages(
                    raw_family.get("stages"),
                    templates=templates,
                    states=states,
                    elimination_ids=elimination_ids,
                    repo_root=repo_root,
                    where=family_where,
                )
            family = {
                "id": family_id,
                "label": _require_text(raw_family, "label", family_where),
                "labelZh": _require_text(raw_family, "labelZh", family_where),
                "description": _require_text(raw_family, "description", family_where),
                "descriptionZh": _require_text(raw_family, "descriptionZh", family_where),
                "pathRegex": pattern_text,
                "stagesFrom": raw_family.get("stagesFrom"),
                "stages": stages,
                "objectTypes": raw_family.get("objectTypes") is True,
                "_pattern": pattern,
            }
            by_id[family_id] = family
            families.append(family)

        blocks.append(
            {
                "enumName": enum_name,
                "rawId": raw_id,
                "profileName": profile_name,
                "lane": lane,
                "alsoLanes": list(also),
                "holds": _require_text(entry, "holds", where),
                "holdsZh": _require_text(entry, "holdsZh", where),
                "familySet": entry.get("familySet"),
                "families": families,
            }
        )
    return blocks


def resolve_object_types(
    declarations: dict[str, Any], *, repo_root: Path = REPO_ROOT
) -> dict[str, dict[str, Any]]:
    """Validate the declared Unity object types and their four stages each."""
    states = _resolve_stage_states(declarations)
    elimination_ids = {
        item.get("id")
        for item in declarations["unreachableFromStaticData"].get("items", [])
        if isinstance(item, dict)
    }
    entries = declarations["unityObjectTypes"].get("entries")
    if not isinstance(entries, list) or not entries:
        raise RecoveryInputError("unityObjectTypes has no entries list")
    types: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RecoveryInputError("a unityObjectTypes entry is not an object")
        type_id = _require_text(entry, "id", "a unityObjectTypes entry")
        where = f"Unity object type {type_id!r}"
        if type_id in types:
            raise RecoveryInputError(f"{where} is declared twice")
        types[type_id] = {
            "id": type_id,
            "declared": True,
            "description": _require_text(entry, "description", where),
            "descriptionZh": _require_text(entry, "descriptionZh", where),
            "stages": _resolve_stages(
                entry.get("stages"),
                templates=declarations["stageTemplates"],
                states=states,
                elimination_ids=elimination_ids,
                repo_root=repo_root,
                where=where,
            ),
        }
    return types


def _classify_path(block: dict[str, Any], virtual_path: str) -> str:
    """Return the one family whose pattern full-matches ``virtual_path``.

    Two matches is a declaration error, not a tie to break by order: an
    ambiguous pattern would let one file count under whichever family happens to
    be listed first.
    """
    matched = [
        family["id"] for family in block["families"] if family["_pattern"].fullmatch(virtual_path)
    ]
    if len(matched) > 1:
        raise RecoveryInputError(
            f"VFS path {virtual_path!r} in block {block['enumName']!r} matches "
            f"several families {matched}; make the declared patterns disjoint"
        )
    return matched[0] if matched else OTHER_FAMILY_ID


_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_LEVEL_ROW_RE = re.compile(r"^\*\*(?P<level>\d)\.\s*(?P<name>.+?)\*\*$")


def parse_levels(path: Path) -> list[dict[str, Any]]:
    """Read the four level definitions out of ``memory/game_data/README.md``.

    They are maintained there, so they are read rather than copied. A table
    that does not parse to exactly levels 1..4 is a hard error.
    """
    _require_file(path, "memory/game_data level index")
    levels: list[dict[str, Any]] = []
    in_levels = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            in_levels = line.strip() == "## The four levels"
            continue
        match = _TABLE_ROW_RE.match(line)
        if not in_levels or not match:
            continue
        cells = [cell.strip() for cell in match.group(1).split("|")]
        if len(cells) < 2 or cells[0].lower() == "level" or set(cells[0]) <= set("-: "):
            continue
        level = _LEVEL_ROW_RE.match(cells[0])
        if not level:
            raise RecoveryInputError(f"unrecognised level row in {path}: {cells[0]!r}")
        levels.append(
            {"level": int(level.group("level")), "name": level.group("name").strip(), "question": cells[1]}
        )
    levels.sort(key=lambda row: row["level"])
    if [row["level"] for row in levels] != [1, 2, 3, 4]:
        raise RecoveryInputError(f"levels in {path} are not 1..4: {levels}")
    return levels


class _Tally:
    """Measured volume for one block or one family."""

    __slots__ = ("files", "declared_bytes", "bytes_read", "chunks", "availability", "statuses", "samples")

    def __init__(self) -> None:
        self.files = 0
        self.declared_bytes = 0
        self.bytes_read = 0
        self.chunks: set[str] = set()
        self.availability: dict[str, list[int]] = {}
        self.statuses: Counter[str] = Counter()
        self.samples: list[str] = []

    def add(self, *, size: int, read: int, chunk: str, status: str, availability: str, path: str) -> None:
        self.files += 1
        self.declared_bytes += size
        self.bytes_read += read
        self.chunks.add(chunk)
        bucket = self.availability.setdefault(availability, [0, 0])
        bucket[0] += 1
        bucket[1] += size
        self.statuses[status] += 1
        if len(self.samples) < FAMILY_SAMPLE_PATHS:
            self.samples.append(path)

    def publish(self, *, samples: bool = False) -> dict[str, Any]:
        by_availability = {
            name: {"files": self.availability[name][0], "declaredBytes": self.availability[name][1]}
            for name in AVAILABILITY_ORDER
            if name in self.availability
        }
        row: dict[str, Any] = {
            "evidence": "measured",
            "files": self.files,
            "declaredBytes": self.declared_bytes,
            # Declared bytes of rows whose payload was actually read. Absent,
            # unverified and failed rows never contribute here.
            "profiledBytes": by_availability.get("profiled", {}).get("declaredBytes", 0),
            "bytesRead": self.bytes_read,
            "containerChunks": len(self.chunks),
            "byAvailability": by_availability,
            "profilerStatuses": dict(sorted(self.statuses.items())),
            "availability": availability_summary(by_availability),
        }
        if samples:
            row["samplePaths"] = list(self.samples)
        return row


def availability_summary(by_availability: dict[str, dict[str, int]]) -> str:
    """One word for a tally: ``profiled``, ``absent``, ``mixed`` or ``none``.

    ``mixed`` is anything short of all-profiled or all-absent, including any
    unverified or failed row, so a partly readable block cannot pass for a
    locally available one.
    """
    present = [name for name, bucket in by_availability.items() if bucket.get("files")]
    if not present:
        return "none"
    if present == ["profiled"]:
        return "profiled"
    if present == ["absent"]:
        return "absent"
    return "mixed"


def _profile_field(record: dict[str, Any], key: str, kind: type, lineno: int, path: Path) -> Any:
    value = record.get(key)
    if not isinstance(value, kind) or isinstance(value, bool):
        raise RecoveryInputError(
            f"VFS payload profile line {lineno} has no {kind.__name__} {key!r}: {path}"
        )
    return value


def read_vfs_profile(path: Path, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Measure the installed corpus by VFS block type and logical-file family.

    Each profile row is one logical file. The row's ``blockTypeRawId`` selects
    the declared enum entry and its ``blockTypeName`` must equal that entry's
    exporter name, so a renamed or new block type cannot be absorbed silently.
    The family comes from ``virtualPath`` alone; the profiler's own coarse
    ``pathFamily`` is not used, because it lumps unrelated files together.
    """
    _require_file(path, "VFS payload profile")
    by_raw = {block["rawId"]: block for block in blocks}
    block_tally: dict[str, _Tally] = {}
    family_tally: dict[tuple[str, str], _Tally] = {}
    total = _Tally()
    rows = 0

    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} is not JSON: {path}: {exc}"
                    ) from exc
                if not isinstance(record, dict):
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} is not an object: {path}"
                    )
                name = record.get("blockTypeName")
                if not isinstance(name, str) or not name:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has no blockTypeName: {path}"
                    )
                raw_id = _profile_field(record, "blockTypeRawId", int, lineno, path)
                block = by_raw.get(raw_id)
                if block is None:
                    raise RecoveryInputError(
                        f"VFS block type {name!r} (raw id {raw_id}) is not declared. Add it "
                        f"to {DECLARATIONS_PATH.name} (vfsBlocks) before publishing."
                    )
                if name != block["profileName"]:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno}: raw id {raw_id} is named "
                        f"{name!r}, but the declaration for {block['enumName']} expects "
                        f"{block['profileName']!r}"
                    )
                virtual_path = _profile_field(record, "virtualPath", str, lineno, path)
                if not virtual_path:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has an empty virtualPath: {path}"
                    )
                size = _profile_field(record, "declaredSize", int, lineno, path)
                read = _profile_field(record, "bytesRead", int, lineno, path)
                chunk = _profile_field(record, "chunkFileName", str, lineno, path)
                if not chunk.lower().endswith(".chk") or not chunk:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has no .chk file name: {path}"
                    )
                status = _profile_field(record, "status", str, lineno, path)
                if size < 0 or read < 0:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has a negative size: {path}"
                    )
                availability = PROFILE_STATUS_AVAILABILITY.get(status)
                if availability is None:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has unknown status {status!r}; "
                        f"known: {sorted(PROFILE_STATUS_AVAILABILITY)}"
                    )
                if availability == "profiled" and read != size:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} is 'profiled' but read {read} "
                        f"of {size} declared bytes: {virtual_path}"
                    )
                family_id = _classify_path(block, virtual_path)
                fields = {
                    "size": size,
                    "read": read,
                    "chunk": chunk,
                    "status": status,
                    "availability": availability,
                    "path": virtual_path,
                }
                rows += 1
                total.add(**fields)
                block_tally.setdefault(block["enumName"], _Tally()).add(**fields)
                family_tally.setdefault((block["enumName"], family_id), _Tally()).add(**fields)
    except OSError as exc:
        raise RecoveryInputError(f"VFS payload profile could not be read: {path}: {exc}") from exc

    if not rows:
        raise RecoveryInputError(f"VFS payload profile is empty: {path}")

    return {"total": total, "blocks": block_tally, "families": family_tally}


_JSON_STRING = r'"((?:[^"\\]|\\.)*)"'
_CHUNK_BLOCK_RE = re.compile(r'^\s*"blockTypeValue": (\d+),?$')
_CHUNK_NAME_RE = re.compile(r'^\s*"fileName": ' + _JSON_STRING + r',?$')
_MAP_SOURCE_RE = re.compile(r'^\s*"Source": ' + _JSON_STRING + r',?$')
_MAP_PATH_ID_RE = re.compile(r'^\s*"PathID": (-?\d+),?$')
_MAP_TYPE_RE = re.compile(r'^\s*"Type": ' + _JSON_STRING + r',?$')


def _layer_files(directory: Path, pattern: str, what: str) -> list[Path]:
    files = sorted(directory.glob(pattern))
    if not files:
        raise RecoveryInputError(f"{what} is missing: {directory / pattern}")
    return files


def read_chunk_blocks(export_root: Path) -> dict[str, int]:
    """Map each .chk name in the export's VFS index to its raw block id.

    The index is the one written by the same export as the asset maps, so a
    chunk added by a client update after the payload profile still resolves.
    A chunk-level ``fileName`` follows its ``blockTypeValue``; file rows use
    ``name``, so a line scan keeps the 380 MB index out of memory.
    """
    chunks: dict[str, int] = {}
    for layer in ASSET_MAP_LAYERS:
        directory = ExportLayout(export_root).vfs_index_dir(layer)
        for path in _layer_files(directory, "*_vfs_index.json", f"{layer} VFS index"):
            raw_id = None
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    block = _CHUNK_BLOCK_RE.match(line)
                    if block:
                        raw_id = int(block.group(1))
                        continue
                    name = _CHUNK_NAME_RE.match(line)
                    if name and name.group(1).lower().endswith(".chk"):
                        if raw_id is None:
                            raise RecoveryInputError(f"chunk {name.group(1)} has no block id: {path}")
                        chunks[name.group(1).upper()] = raw_id
    if not chunks:
        raise RecoveryInputError(f"no .chk chunks found in the VFS indexes under {export_root}")
    return chunks


def read_asset_map_types(export_root: Path, blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Count Unity objects per block and type from the export's asset maps.

    Each entry names its source chunk, PathID and Unity type. Layers are read
    in overlay order and an object is keyed by (type, PathID) -- PathIDs are
    measured unique across the export -- so a bundle that Persistent replaces
    is not counted twice. The asset map lists only the types AnimeStudio maps;
    GameObject, Transform and renderer components are not in it.
    """
    by_raw = {block["rawId"]: block["enumName"] for block in blocks}
    chunk_blocks = read_chunk_blocks(export_root)
    seen: set[tuple[str, int]] = set()
    counts: Counter[tuple[str, str]] = Counter()
    for layer in ASSET_MAP_LAYERS:
        directory = ExportLayout(export_root).asset_map_dir(layer)
        for path in _layer_files(directory, "*.json", f"{layer} asset map"):
            source = path_id = None
            with path.open(encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, start=1):
                    if match := _MAP_SOURCE_RE.match(line):
                        source = re.split(r"[\\/]+", match.group(1))[-1].upper()
                    elif match := _MAP_PATH_ID_RE.match(line):
                        path_id = int(match.group(1))
                    elif match := _MAP_TYPE_RE.match(line):
                        if source is None or path_id is None:
                            raise RecoveryInputError(
                                f"asset map entry at line {lineno} has no Source or PathID: {path}"
                            )
                        key = (match.group(1), path_id)
                        if key not in seen:
                            seen.add(key)
                            raw_id = chunk_blocks.get(source)
                            if raw_id is None or raw_id not in by_raw:
                                raise RecoveryInputError(
                                    f"asset map entry at line {lineno} names chunk {source}, "
                                    f"which no VFS index assigns to a declared block: {path}"
                                )
                            counts[(by_raw[raw_id], match.group(1))] += 1
                        source = path_id = None
    if not counts:
        raise RecoveryInputError(f"the asset maps under {export_root} list no objects")
    return {"counts": counts}


def _source_row(path: Path, role: str) -> dict[str, Any]:
    stat = path.stat()
    try:
        rel = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = path.as_posix()
    return {
        "role": role,
        "path": rel,
        "bytes": stat.st_size,
        "modified": dt.datetime.fromtimestamp(stat.st_mtime, dt.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def _publish_object_types(
    block_name: str,
    declared: dict[str, dict[str, Any]],
    asset_types: dict[str, Any],
) -> list[dict[str, Any]]:
    """Declared types at their measured count, plus any undeclared type seen."""
    counts = {
        type_id: objects
        for (name, type_id), objects in asset_types["counts"].items()
        if name == block_name
    }
    rows = []
    for type_id in sorted(set(declared) | set(counts)):
        entry = declared.get(type_id) or {
            "id": type_id,
            "declared": False,
            "description": "An asset-map type with no declaration, so no stage is claimed.",
            "descriptionZh": "没有声明的资源映射类型，因此不声明任何阶段。",
            "stages": [
                {
                    "level": level,
                    "state": "notAssessed",
                    "text": "No declaration covers this type.",
                    "textZh": "没有声明覆盖此类型。",
                    "source": None,
                    "eliminations": [],
                }
                for level in (1, 2, 3, 4)
            ],
        }
        rows.append({**entry, "measured": {"evidence": "measured", "objects": counts.get(type_id, 0)}})
    rows.sort(key=lambda row: (-row["measured"]["objects"], row["id"]))
    return rows


def _publish_blocks(
    blocks: list[dict[str, Any]],
    measured: dict[str, Any],
    object_types: dict[str, dict[str, Any]],
    asset_types: dict[str, Any],
) -> list[dict[str, Any]]:
    """Join declared blocks and families to their measured tallies.

    Every declared block is published, observed or not, so an enum value with
    no current file is visible as such. Every declared family is published even
    at zero files, and the unclassified remainder whenever it is non-empty.
    """
    published = []
    for block in blocks:
        name = block["enumName"]
        tally = measured["blocks"].get(name)
        families = []
        for family in block["families"]:
            family_tally = measured["families"].get((name, family["id"])) or _Tally()
            families.append(
                {
                    "id": family["id"],
                    "declared": True,
                    "label": family["label"],
                    "labelZh": family["labelZh"],
                    "description": family["description"],
                    "descriptionZh": family["descriptionZh"],
                    "pathRegex": family["pathRegex"],
                    "stagesFrom": family["stagesFrom"],
                    "stages": family["stages"],
                    "measured": family_tally.publish(samples=True),
                    **(
                        {"objectTypes": _publish_object_types(name, object_types, asset_types)}
                        if family["objectTypes"]
                        else {}
                    ),
                }
            )
        other = measured["families"].get((name, OTHER_FAMILY_ID))
        if other is not None and other.files:
            families.append(
                {
                    "id": OTHER_FAMILY_ID,
                    "declared": False,
                    "label": "Other / unclassified",
                    "labelZh": "其他 / 未分类",
                    "description": "Paths in this block that no declared family pattern matches.",
                    "descriptionZh": "本数据块中没有任何已声明家族模式匹配的路径。",
                    "pathRegex": None,
                    "stagesFrom": None,
                    "stages": [
                        {
                            "level": level,
                            "state": "notAssessed",
                            "text": "No family declaration covers these paths, so no stage is claimed.",
                            "textZh": "没有家族声明覆盖这些路径，因此不声明任何阶段。",
                            "source": None,
                            "eliminations": [],
                        }
                        for level in (1, 2, 3, 4)
                    ],
                    "measured": other.publish(samples=True),
                }
            )
        published.append(
            {
                "enumName": name,
                "rawId": block["rawId"],
                "lane": block["lane"],
                "holds": block["holds"],
                "holdsZh": block["holdsZh"],
                "observed": tally is not None,
                "measured": (tally or _Tally()).publish(),
                "families": families,
            }
        )
    # Largest locally read payload first, then declared-only volume, then name.
    published.sort(
        key=lambda row: (
            -row["measured"]["profiledBytes"],
            -row["measured"]["declaredBytes"],
            row["enumName"],
        )
    )
    return published


def build_payload(
    *,
    declarations_path: Path = DECLARATIONS_PATH,
    memory_index_path: Path = MEMORY_INDEX_PATH,
    vfs_profile_path: Path = VFS_PROFILE_PATH,
    export_root: Path | None = None,
    generated_at: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    # Cheap inputs first: the corpus sweep reads a 450k-row profile, so a
    # malformed declaration should fail before paying for it.
    declarations = load_declarations(declarations_path)
    levels = parse_levels(memory_index_path)
    lane_entries = declarations["lanes"]["entries"]
    vfs_blocks = resolve_vfs_blocks(
        declarations, lane_ids=set(lane_entries), repo_root=repo_root
    )
    stage_states = _resolve_stage_states(declarations)
    object_types = resolve_object_types(declarations, repo_root=repo_root)
    export_root = EXPORT_LAYOUT.root if export_root is None else export_root
    measured = read_vfs_profile(vfs_profile_path, vfs_blocks)
    asset_types = read_asset_map_types(export_root, vfs_blocks)
    blocks = _publish_blocks(vfs_blocks, measured, object_types, asset_types)

    return {
        "schema": SCHEMA,
        "generatedAt": generated_at
        or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sources": [
            _source_row(vfs_profile_path, "installedCorpus"),
            _source_row(declarations_path, "declarations"),
            _source_row(memory_index_path, "levelIndex"),
            *(
                _source_row(path, f"assetMap{layer}")
                for layer in ASSET_MAP_LAYERS
                for path in sorted(ExportLayout(export_root).asset_map_dir(layer).glob("*.json"))
            ),
        ],
        "levels": levels,
        "stageStates": list(stage_states.values()),
        "lanes": [
            {"id": lane_id, "label": entry.get("label", lane_id), "labelZh": entry.get("labelZh")}
            for lane_id, entry in lane_entries.items()
            if not lane_id.startswith("_")
        ],
        # Titles for the evidence limits a stage cites by id.
        "evidenceLimits": declarations["unreachableFromStaticData"]["items"],
        "vfs": {
            "totals": measured["total"].publish(),
            "blocks": blocks,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build webui/data/recovery/index.json from the VFS payload profile."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output JSON path (default: {DEFAULT_OUTPUT.relative_to(ROOT).as_posix()})",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="print the per-block family stages after writing",
    )
    args = parser.parse_args(argv)

    try:
        # Named explicitly so the module-level paths are resolved at call time
        # rather than frozen into build_payload's defaults.
        payload = build_payload(
            declarations_path=DECLARATIONS_PATH,
            memory_index_path=MEMORY_INDEX_PATH,
            vfs_profile_path=VFS_PROFILE_PATH,
        )
    except RecoveryInputError as exc:
        raise SystemExit(f"recovery build failed closed: {exc}") from exc

    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    write_canonical_json(output, payload)

    totals = payload["vfs"]["totals"]
    blocks = payload["vfs"]["blocks"]
    print(
        f"recovery: {totals['files']:,} logical files, {totals['profiledBytes'] / 1e9:.2f} GB "
        f"profiled locally across {sum(1 for b in blocks if b['observed'])}/{len(blocks)} "
        f"block types -> {output}"
    )
    if args.print_summary:
        for block in blocks:
            for family in block["families"]:
                stages = " ".join(stage["state"] for stage in family["stages"])
                print(
                    f"  {block['enumName']}/{family['id']}: {family['measured']['files']:,} files; {stages}"
                )
                for row in family.get("objectTypes", []):
                    print(f"    {row['id']}: {row['measured']['objects']:,} objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
