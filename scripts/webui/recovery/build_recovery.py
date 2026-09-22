#!/usr/bin/env python3
"""Build the WebUI Recovery-progress page data.

The page answers one question: how far has understanding of the installed game
data actually got, level by level and lane by lane, and how much data sits
behind each answer.

Every figure it publishes is either

* ``evidence: "measured"`` -- read out of a generated report under ``reports/``
  or out of the tracked ``memory/game_data/README.md`` lane index, or
* ``evidence: "declared"`` -- taken from ``recovery_declarations.json`` beside
  this module, where each entry carries its own ``_why`` stating why no report
  can supply it.

Nothing in between. A derived figure is never dressed up as a measurement, and
"framed and named" is never published as "understood": the two live in
different fields and the page renders them differently.

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

from scripts.common import OUT_DIR, REPORTS_DIR, ROOT, write_canonical_json
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.recovery-progress.v1"

DECLARATIONS_PATH = Path(__file__).resolve().parent / "recovery_declarations.json"
MEMORY_INDEX_PATH = REPO_ROOT / "memory" / "game_data" / "README.md"
VFS_PROFILE_PATH = REPORTS_DIR / "animestudio" / "vfs_payload_profile_files_latest.jsonl.gz"
JSONDATA_COVERAGE_PATH = REPORTS_DIR / "game_data" / "jsondata_schema_coverage_declared.json"
FIELD_SEMANTICS_PATH = REPORTS_DIR / "assets" / "monobehaviour_field_semantics.json"
TABLE_KEYS_PATH = REPORTS_DIR / "assets" / "monobehaviour_table_keys.json"

DEFAULT_OUTPUT = OUT_DIR / "recovery" / "index.json"

# The four base MonoBehaviour fields every serialized script carries. Unity
# writes them on every object, so they are engine plumbing and never
# class-specific evidence. Counting them as signal makes 1,044 of 1,045 classes
# look understood, which is why they are excluded before anything is counted.
MONOBEHAVIOUR_BASE_FIELDS = frozenset({"m_GameObject", "m_Enabled", "m_Script", "m_Name"})

# Public engine and middleware namespaces. Their semantics are documented
# outside this repository, so "nothing recovered from this corpus" would not
# mean "unidentified" for them. Prefix matching, not a namespace-root match:
# game namespaces such as `ScriptAnimation.*` stay in the measured set.
PUBLIC_ENGINE_NAMESPACE_PREFIXES = (
    "UnityEngine.",
    "Cinemachine",
    "Rewired",
    "TMPro",
    "Unity.",
    "MagicaCloth",
    "AK.",
)

# A string field whose sampled values are drawn from an exported Table's key set
# is class-specific evidence, at these join strengths.
MONOBEHAVIOUR_KEYED_TABLE_STATUSES = ("key_of", "key_of_several", "mostly_key_of")

# Exported asset types a reference can land on and thereby say something. A
# reference resolving to another anonymous MonoBehaviour names nothing, so it is
# evidence that the field *is* a reference and no evidence about what it means.
EXPLANATORY_ASSET_TARGET_TYPES = frozenset(
    {
        "Texture2D",
        "Sprite",
        "Material",
        "Mesh",
        "AnimationClip",
        "Animator",
        "AnimatorController",
        "AnimatorOverrideController",
        "PlayableDirector",
        "TextAsset",
    }
)


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
    payload = _read_json_object(
        path, "recovery declarations", "endfield.recovery-progress-declarations.v1"
    )
    for key in (
        "memoryIndexSections",
        "lanes",
        "blockTypeLanes",
        "unreachableFromStaticData",
        "levelCaveats",
    ):
        if key not in payload:
            raise RecoveryInputError(f"recovery declarations are missing {key!r}: {path}")
    return payload


_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_BOLD_HEAD_RE = re.compile(r"^\*\*(.+?)\*\*")
_TOPIC_LINK_RE = re.compile(r"\[`(?P<file>[^`]+\.md)`\]\((?P<href>[^)]+)\)(?P<rest>.*)$")
_LEVEL_ROW_RE = re.compile(r"^\*\*(?P<level>\d)\.\s*(?P<name>.+?)\*\*$")


def _table_cells(line: str) -> list[str] | None:
    match = _TABLE_ROW_RE.match(line.rstrip())
    if not match:
        return None
    return [cell.strip() for cell in match.group(1).split("|")]


def parse_memory_index(path: Path, sections: dict[str, Any]) -> dict[str, Any]:
    """Read the levels and the lane/topic index out of ``memory/game_data/README.md``.

    The level definitions and each topic file's level are maintained there, so
    they are read rather than copied. Parsing failures are hard errors: a
    silently empty index would make the page claim less recovery than exists.
    """
    _require_file(path, "memory/game_data lane index")
    text = path.read_text(encoding="utf-8")

    levels: list[dict[str, Any]] = []
    topics: list[dict[str, Any]] = []

    section: dict[str, Any] | None = None
    columns: list[str] | None = None
    in_levels_table = False

    for raw in text.splitlines():
        line = raw.rstrip()
        cells = _table_cells(line)

        if cells is None:
            if line.startswith("## "):
                in_levels_table = line.strip() == "## The four levels"
                section = None
                columns = None
                continue
            bold = _BOLD_HEAD_RE.match(line)
            if bold:
                key = bold.group(1).strip()
                declared = sections.get(key)
                if isinstance(declared, dict):
                    section = {"key": key, **declared}
                else:
                    section = None
                columns = None
            elif not line:
                columns = None
            continue

        if all(set(cell) <= set("-: ") and cell for cell in cells):
            continue  # the |---|---| separator

        header = [cell.lower() for cell in cells]
        if header and header[0] in {"level", "file", "block type"}:
            columns = header
            continue

        if in_levels_table and columns == ["level", "question it answers"]:
            match = _LEVEL_ROW_RE.match(cells[0])
            if not match:
                raise RecoveryInputError(
                    f"unrecognised level row in {path}: {cells[0]!r}"
                )
            levels.append(
                {
                    "level": int(match.group("level")),
                    "name": match.group("name").strip(),
                    "question": cells[1],
                }
            )
            continue

        if section is None or columns is None or columns[0] != "file":
            continue

        link = _TOPIC_LINK_RE.match(cells[0])
        if not link:
            raise RecoveryInputError(f"unrecognised topic row in {path}: {cells[0]!r}")
        title = link.group("rest").strip()
        if title.startswith("--"):
            title = title[2:].strip()

        row = dict(zip(columns, cells))
        level_text = row.get("level")
        if level_text:
            try:
                level = int(level_text)
            except ValueError as exc:
                raise RecoveryInputError(
                    f"unrecognised level {level_text!r} for {link.group('file')} in {path}"
                ) from exc
        elif "defaultLevel" in section:
            level = int(section["defaultLevel"])
        else:
            raise RecoveryInputError(
                f"{link.group('file')} has no level column and section "
                f"{section['key']!r} declares no defaultLevel"
            )

        lines_text = row.get("lines")
        try:
            lines = int(lines_text) if lines_text else None
        except ValueError:
            lines = None

        topics.append(
            {
                "file": link.group("file"),
                "title": title,
                "lane": section["lane"],
                "level": level,
                "lines": lines,
                "path": f"memory/game_data/{link.group('file')}",
            }
        )

    if len(levels) != 4:
        raise RecoveryInputError(
            f"expected four level definitions in {path}, parsed {len(levels)}"
        )
    if not topics:
        raise RecoveryInputError(f"no topic rows parsed from {path}")

    levels.sort(key=lambda row: row["level"])
    if [row["level"] for row in levels] != [1, 2, 3, 4]:
        raise RecoveryInputError(f"levels in {path} are not 1..4: {levels}")

    return {"levels": levels, "topics": topics}


def read_vfs_block_totals(path: Path) -> dict[str, Any]:
    """Aggregate the complete installed-corpus inventory by VFS block type."""
    _require_file(path, "VFS payload profile")
    files: Counter[str] = Counter()
    payload_bytes: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    families: dict[str, Counter[str]] = {}
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
                block = record.get("blockTypeName")
                if not isinstance(block, str) or not block:
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has no blockTypeName: {path}"
                    )
                size = record.get("declaredSize")
                if not isinstance(size, int):
                    raise RecoveryInputError(
                        f"VFS payload profile line {lineno} has a non-integer "
                        f"declaredSize: {path}"
                    )
                rows += 1
                files[block] += 1
                payload_bytes[block] += size
                statuses[str(record.get("status"))] += 1
                family = record.get("pathFamily")
                if isinstance(family, str) and family:
                    families.setdefault(block, Counter())[family] += 1
    except OSError as exc:
        raise RecoveryInputError(f"VFS payload profile could not be read: {path}: {exc}") from exc

    if not rows:
        raise RecoveryInputError(f"VFS payload profile is empty: {path}")

    blocks = []
    for block in sorted(files, key=lambda name: (-payload_bytes[name], name)):
        top = families.get(block, Counter()).most_common(6)
        blocks.append(
            {
                "blockType": block,
                "files": files[block],
                "bytes": payload_bytes[block],
                "topPathFamilies": [{"pathFamily": name, "files": count} for name, count in top],
            }
        )

    return {
        "blocks": blocks,
        "totals": {
            "files": rows,
            "bytes": sum(payload_bytes.values()),
            "blockTypes": len(files),
        },
        "observationStatuses": dict(sorted(statuses.items())),
    }


def read_jsondata_coverage(path: Path) -> dict[str, Any]:
    """Per-family named-byte coverage for the JsonData block."""
    payload = _read_json_object(
        path, "JsonData schema coverage", "endfield.jsondata-schema-coverage.v1"
    )
    raw_families = payload.get("families")
    if not isinstance(raw_families, dict) or not raw_families:
        raise RecoveryInputError(f"JsonData schema coverage has no families: {path}")

    families = []
    total_files = 0
    total_bytes = 0
    total_named = 0
    fully_named = 0
    for name, entry in raw_families.items():
        if not isinstance(entry, dict):
            raise RecoveryInputError(f"JsonData family {name!r} is not an object: {path}")
        for key in ("files", "bytes", "namedBytes"):
            if not isinstance(entry.get(key), int):
                raise RecoveryInputError(
                    f"JsonData family {name!r} has no integer {key!r}: {path}"
                )
        family_bytes = entry["bytes"]
        named = entry["namedBytes"]
        share = entry.get("namedShare")
        if not isinstance(share, (int, float)):
            share = (named / family_bytes) if family_bytes else 0.0
        families.append(
            {
                "family": name,
                "files": entry["files"],
                "bytes": family_bytes,
                "namedBytes": named,
                "unnamedBytes": max(family_bytes - named, 0),
                "namedShare": float(share),
                "buckets": [
                    {
                        "status": bucket.get("status"),
                        "files": bucket.get("files"),
                        "size": bucket.get("size"),
                        "named": bucket.get("named"),
                        "opaque": bucket.get("opaque"),
                        "unreached": bucket.get("unreached"),
                    }
                    for bucket in entry.get("buckets", [])
                    if isinstance(bucket, dict)
                ],
            }
        )
        total_files += entry["files"]
        total_bytes += family_bytes
        total_named += named
        if family_bytes and named >= family_bytes:
            fully_named += 1

    families.sort(key=lambda row: (-row["bytes"], row["family"]))
    return {
        "evidenceTier": payload.get("evidenceTier"),
        "method": payload.get("method"),
        "families": families,
        "totals": {
            "families": len(families),
            "familiesFullyNamed": fully_named,
            "files": total_files,
            "bytes": total_bytes,
            "namedBytes": total_named,
            "namedShare": (total_named / total_bytes) if total_bytes else 0.0,
        },
    }


def reference_lands_on_a_name(field: dict[str, Any]) -> bool:
    """True when a filled reference field resolves to something named.

    Either a named target class, or an exported asset type rather than another
    anonymous MonoBehaviour. This is the single difference between the two
    not-understood bounds.
    """
    targets = field.get("targets") if isinstance(field.get("targets"), dict) else {}
    if targets.get("targetClasses"):
        return True
    resolved = targets.get("resolvedExportedTypes") or {}
    if not isinstance(resolved, dict):
        return False
    return any(name in EXPLANATORY_ASSET_TARGET_TYPES for name in resolved)


def is_public_engine_class(script_class: str | None) -> bool:
    """True for a public engine/middleware type, by namespace prefix.

    ``None`` becomes ``""``, which matches no prefix: the one unnamed class in
    the census is game data whose script could not be named, so it belongs in
    the measured not-understood set rather than being excluded as engine code.
    """
    name = script_class or ""
    return any(name.startswith(prefix) for prefix in PUBLIC_ENGINE_NAMESPACE_PREFIXES)


def read_monobehaviour_semantics(
    path: Path,
    *,
    keyed_table_classes: frozenset[str] | set[str] = frozenset(),
    top_classes: int = 25,
) -> dict[str, Any]:
    """MonoBehaviour class/field evidence from the exported-object census.

    Besides the census totals this measures the honest not-understood set: the
    game-specific classes for which nothing class-specific has been recovered.
    A class has class-specific signal when, ignoring the four universal engine
    fields, it has a qualifying reference field, a path-shaped string field, or
    a string field whose values join an exported Table's key set
    (``keyed_table_classes``, from the table-key report).

    "Qualifying reference" is the only thing the two published bounds disagree
    about, so both are measured and neither is presented alone:

    * ``floor`` accepts any reference field that is ever filled;
    * ``strict`` accepts one only when it lands on a name
      (:func:`reference_lands_on_a_name`).

    A filled reference that resolves to nothing named is evidence that the field
    *is* a reference and no evidence about what it means, which is why the two
    bounds are far apart. The classes between them are published too.
    """
    payload = _read_json_object(
        path, "MonoBehaviour field semantics", "endfield.monobehaviour-field-semantics.v1"
    )
    summary = payload.get("summary")
    classes = payload.get("classes")
    if not isinstance(summary, dict) or not isinstance(classes, list):
        raise RecoveryInputError(f"MonoBehaviour field semantics is malformed: {path}")
    for key in ("objectsSwept", "classesReported", "fieldPathsReported"):
        if not isinstance(summary.get(key), int):
            raise RecoveryInputError(
                f"MonoBehaviour field semantics summary has no integer {key!r}: {path}"
            )

    ranked = []
    base_only_classes = 0
    base_only_objects = 0
    filled_reference_fields = 0
    container_resolved = 0
    container_unresolved = 0
    keyed = set(keyed_table_classes)
    considered: list[dict[str, Any]] = []
    no_signal_floor: list[dict[str, Any]] = []
    no_signal_strict: list[dict[str, Any]] = []
    between_bounds: list[dict[str, Any]] = []
    public_engine_classes = 0
    for entry in classes:
        if not isinstance(entry, dict):
            continue
        objects = entry.get("objects")
        if not isinstance(objects, int):
            continue
        script_class = entry.get("scriptClass")
        fields = entry.get("fields") if isinstance(entry.get("fields"), list) else []
        beyond_base = [
            field
            for field in fields
            if isinstance(field, dict) and field.get("path") not in MONOBEHAVIOUR_BASE_FIELDS
        ]
        if not beyond_base:
            base_only_classes += 1
            base_only_objects += objects
        for field in fields:
            if not isinstance(field, dict):
                continue
            reference = field.get("reference")
            if not isinstance(reference, dict):
                continue
            if (reference.get("local") or 0) + (reference.get("crossFile") or 0) <= 0:
                continue
            filled_reference_fields += 1
            targets = field.get("targets") if isinstance(field.get("targets"), dict) else {}
            # A field counts as container-resolved only when every sampled target
            # reached a container. One unresolved target keeps it out.
            if (targets.get("containerUnresolved") or 0) == 0 and (targets.get("containerResolved") or 0) > 0:
                container_resolved += 1
            else:
                container_unresolved += 1

        # The not-understood measurement. The universal engine fields are
        # skipped first; without that every class looks referenced.
        if is_public_engine_class(script_class):
            public_engine_classes += 1
        else:
            filled_references = 0
            named_references = 0
            signal_paths = 0
            for field in beyond_base:
                classification = str(field.get("classification") or "")
                if classification.startswith("reference") and classification != "reference_always_null":
                    filled_references += 1
                    if reference_lands_on_a_name(field):
                        named_references += 1
                if classification == "string_with_separators":
                    signal_paths += 1
            row = {
                "scriptClass": script_class,
                "objects": objects,
                "filledReferenceFields": filled_references,
                "referenceFieldsLandingOnAName": named_references,
            }
            considered.append(row)
            other_signal = bool(signal_paths) or (script_class or "") in keyed
            if not other_signal and not filled_references:
                no_signal_floor.append(row)
            if not other_signal and not named_references:
                no_signal_strict.append(row)
                if filled_references:
                    between_bounds.append(row)

        ranked.append(
            {
                "scriptClass": entry.get("scriptClass"),
                "objects": objects,
                "fieldPaths": entry.get("fieldPathsRecorded"),
                "fieldsBeyondBase": len(beyond_base),
            }
        )

    ranked.sort(key=lambda row: (-row["objects"], str(row["scriptClass"])))
    reference_fields = summary.get("referenceFields")
    ever_filled = summary.get("referenceFieldsEverFilled")

    return {
        "objectsSwept": summary["objectsSwept"],
        "objectsUnreadable": summary.get("objectsUnreadable"),
        "classes": summary["classesReported"],
        "fieldPaths": summary["fieldPathsReported"],
        "fieldsByClassification": dict(
            sorted(
                (summary.get("fieldsByClassification") or {}).items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "referenceFields": reference_fields,
        "referenceFieldsEverFilled": ever_filled,
        "referenceFieldsFilled": filled_reference_fields,
        "referenceFieldsResolvingToContainer": container_resolved,
        "referenceFieldsWithUnresolvedContainer": container_unresolved,
        "baseFieldsOnlyClasses": base_only_classes,
        "baseFieldsOnlyObjects": base_only_objects,
        "topClassesByObjects": ranked[:top_classes],
        "noClassSpecificSignal": _no_class_specific_signal(
            considered=considered,
            floor=no_signal_floor,
            strict=no_signal_strict,
            between=between_bounds,
            public_engine_classes=public_engine_classes,
            top_classes=top_classes,
        ),
    }


def _bound(
    rows: list[dict[str, Any]],
    *,
    considered: int,
    reference_rule: str,
    top_classes: int,
) -> dict[str, Any]:
    return {
        "classes": len(rows),
        "objects": sum(row["objects"] for row in rows),
        "shareOfClassesConsidered": (len(rows) / considered) if considered else 0.0,
        "unnamedClasses": sum(1 for row in rows if not row["scriptClass"]),
        "referenceRule": reference_rule,
        "topClassesByObjects": sorted(
            rows, key=lambda row: (-row["objects"], str(row["scriptClass"]))
        )[:top_classes],
    }


def _no_class_specific_signal(
    *,
    considered: list[dict[str, Any]],
    floor: list[dict[str, Any]],
    strict: list[dict[str, Any]],
    between: list[dict[str, Any]],
    public_engine_classes: int,
    top_classes: int,
) -> dict[str, Any]:
    """Publish the not-understood set as a measured range, never one bound alone.

    ``strict`` is the headline: it is what the evidence supports. ``floor`` is
    the looser reading, kept visible so the range is honest in both directions.
    """
    total = len(considered)
    return {
        "evidence": "measured",
        "classesConsidered": total,
        "objectsConsidered": sum(row["objects"] for row in considered),
        "publicEngineClassesExcluded": public_engine_classes,
        "headlineBound": "strict",
        "whyBoundsDiffer": (
            "A filled reference is evidence that the field is a reference, and no "
            "evidence about what it means. The floor accepts any filled reference "
            "as class-specific signal; the strict bound accepts one only when it "
            "lands on a name."
        ),
        "strict": _bound(
            strict,
            considered=total,
            reference_rule="a filled reference field that resolves to a named target class or an exported asset type",
            top_classes=top_classes,
        ),
        "floor": _bound(
            floor,
            considered=total,
            reference_rule="any reference field that is ever filled",
            top_classes=top_classes,
        ),
        "betweenBounds": {
            "classes": len(between),
            "objects": sum(row["objects"] for row in between),
            "means": (
                "their only recovered signal is a reference that resolves to "
                "nothing named"
            ),
            # Two orderings, because the two interesting cases are different:
            # the classes this affects most by instance count, and the classes
            # carrying the most references that land nowhere.
            "topClassesByObjects": sorted(
                between, key=lambda row: (-row["objects"], str(row["scriptClass"]))
            )[:top_classes],
            "topClassesByUnnamedReferences": sorted(
                between,
                key=lambda row: (-row["filledReferenceFields"], -row["objects"], str(row["scriptClass"])),
            )[:top_classes],
        },
        "sharedSignalKinds": [
            "a path-shaped string field (string_with_separators)",
            "a string field whose values join an exported Table's key set",
        ],
        "universalFieldsExcluded": sorted(MONOBEHAVIOUR_BASE_FIELDS),
        "publicNamespacePrefixes": list(PUBLIC_ENGINE_NAMESPACE_PREFIXES),
        "keyedTableStatuses": list(MONOBEHAVIOUR_KEYED_TABLE_STATUSES),
        "explanatoryAssetTargetTypes": sorted(EXPLANATORY_ASSET_TARGET_TYPES),
    }


def read_table_key_joins(path: Path) -> dict[str, Any]:
    """How many MonoBehaviour string fields hold exported Table keys."""
    payload = _read_json_object(
        path, "MonoBehaviour table keys", "endfield.monobehaviour-table-keys.v1"
    )
    summary = payload.get("summary")
    ownership = payload.get("keyOwnership")
    if not isinstance(summary, dict) or not isinstance(ownership, dict):
        raise RecoveryInputError(f"MonoBehaviour table keys is malformed: {path}")
    fields = payload.get("fields")
    if not isinstance(fields, list):
        raise RecoveryInputError(f"MonoBehaviour table keys has no fields list: {path}")
    # Classes with at least one string field whose sampled values are drawn from
    # a Table's key set. This is class-specific signal for the not-understood
    # measurement, so it is published rather than recomputed downstream.
    keyed_classes = sorted(
        {
            str(row.get("scriptClass"))
            for row in fields
            if isinstance(row, dict) and row.get("status") in MONOBEHAVIOUR_KEYED_TABLE_STATUSES
        }
    )
    return {
        "keyedClasses": keyed_classes,
        "stringFieldsConsidered": summary.get("stringFieldsConsidered"),
        "byStatus": dict(sorted((summary.get("byStatus") or {}).items())),
        "reportedFields": summary.get("reportedFields"),
        "evidenceBoundary": summary.get("evidenceBoundary"),
        "keyOwnership": {
            "tables": ownership.get("tables"),
            "distinctKeys": ownership.get("distinctKeys"),
            "numericKeys": ownership.get("numericKeys"),
            "namedKeys": ownership.get("namedKeys"),
            "namedKeysUniqueToOneTable": ownership.get("namedKeysUniqueToOneTable"),
        },
    }


# --------------------------------------------------------------------------
# assembly


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


CORPUS_LEVEL_DEPTH_BASIS = (
    "A block type is counted at level N when its lane has at least one documented "
    "conclusion at level N, plus the levels of any lane the index heads "
    "'all lanes'. This is the depth of the lane's documentation, not per-byte "
    "understanding: a counted byte is not an understood byte, and one conclusion "
    "does not cover a lane's whole payload."
)


def _corpus_level_depth(
    blocks: list[dict[str, Any]],
    lanes: list[dict[str, Any]],
    totals: dict[str, Any],
) -> list[dict[str, Any]]:
    """Split the measured corpus by how deep its lane's documentation goes.

    One row per level, so the whole corpus can be shown as a single segmented
    bar and then broken down level by level. The rows are cumulative downward by
    construction: a lane documented at level 3 was necessarily documented at the
    levels below it only if those files exist, so each level is evaluated on its
    own rather than inferred from a deeper one.
    """
    reached: dict[str, set[int]] = {}
    all_lane_levels: set[int] = set()
    for lane in lanes:
        levels_here = {
            row["level"] for row in lane["documentedTopics"]["perLevel"] if row["reached"]
        }
        reached[lane["id"]] = levels_here
        # A lane the index heads "all lanes" holds for every block type, so its
        # levels are credited everywhere instead of to a lane with no block.
        if lane.get("appliesToAllLanes"):
            all_lane_levels |= levels_here
    for lane_id in reached:
        reached[lane_id] |= all_lane_levels

    total_bytes = totals.get("bytes") or 0
    total_files = totals.get("files") or 0
    rows: list[dict[str, Any]] = []
    for level in (1, 2, 3, 4):
        at_level = [block for block in blocks if level in reached.get(block["lane"], set())]
        level_bytes = sum(block["bytes"] for block in at_level)
        level_files = sum(block["files"] for block in at_level)
        rows.append(
            {
                "level": level,
                "basis": "laneDocumentedAtThisLevel",
                "blockTypes": [block["blockType"] for block in at_level],
                "blockTypesCounted": len(at_level),
                "blockTypesTotal": len(blocks),
                "files": level_files,
                "bytes": level_bytes,
                "byteShare": (level_bytes / total_bytes) if total_bytes else 0.0,
                "fileShare": (level_files / total_files) if total_files else 0.0,
                "segments": [
                    {
                        "blockType": block["blockType"],
                        "lane": block["lane"],
                        "bytes": block["bytes"],
                        "files": block["files"],
                    }
                    for block in at_level
                ],
            }
        )
    return rows


def build_payload(
    *,
    declarations_path: Path = DECLARATIONS_PATH,
    memory_index_path: Path = MEMORY_INDEX_PATH,
    vfs_profile_path: Path = VFS_PROFILE_PATH,
    jsondata_coverage_path: Path = JSONDATA_COVERAGE_PATH,
    field_semantics_path: Path = FIELD_SEMANTICS_PATH,
    table_keys_path: Path = TABLE_KEYS_PATH,
    generated_at: str | None = None,
) -> dict[str, Any]:
    # Cheap inputs first: the corpus sweep reads a 450k-row profile, so a
    # missing or malformed report should fail before paying for it.
    declarations = load_declarations(declarations_path)
    index = parse_memory_index(memory_index_path, declarations["memoryIndexSections"])
    jsondata = read_jsondata_coverage(jsondata_coverage_path)
    table_keys = read_table_key_joins(table_keys_path)
    monobehaviour = read_monobehaviour_semantics(
        field_semantics_path,
        keyed_table_classes=frozenset(table_keys["keyedClasses"]),
    )
    corpus = read_vfs_block_totals(vfs_profile_path)

    lane_decl = declarations["lanes"]
    lane_entries = lane_decl["entries"]
    lane_order = [lane for lane in lane_decl["order"] if lane in lane_entries]

    block_lanes = {
        key: value
        for key, value in declarations["blockTypeLanes"].items()
        if not key.startswith("_")
    }

    # Attribute measured volume to lanes. An unmapped block type fails closed so
    # a client update that adds one is noticed instead of silently vanishing.
    lane_files: Counter[str] = Counter()
    lane_bytes: Counter[str] = Counter()
    blocks: list[dict[str, Any]] = []
    for block in corpus["blocks"]:
        name = block["blockType"]
        mapping = block_lanes.get(name)
        if mapping is None:
            raise RecoveryInputError(
                f"VFS block type {name!r} has no declared lane. Add it to "
                f"{declarations_path.name} (blockTypeLanes) before publishing."
            )
        lane = mapping["lane"]
        if lane not in lane_entries:
            raise RecoveryInputError(
                f"block type {name!r} maps to undeclared lane {lane!r}"
            )
        also = [item for item in mapping.get("alsoLanes", []) if item in lane_entries]
        lane_files[lane] += block["files"]
        lane_bytes[lane] += block["bytes"]
        blocks.append({**block, "lane": lane, "alsoLanes": also})

    topics_by_lane: dict[str, list[dict[str, Any]]] = {}
    for topic in index["topics"]:
        topics_by_lane.setdefault(topic["lane"], []).append(topic)

    unknown_lanes = sorted(set(topics_by_lane) - set(lane_entries))
    if unknown_lanes:
        raise RecoveryInputError(
            f"memory index sections declare undeclared lanes: {unknown_lanes}"
        )

    open_items = declarations["unreachableFromStaticData"]["items"]
    open_by_lane: dict[str, list[dict[str, Any]]] = {}
    for item in open_items:
        open_by_lane.setdefault(item.get("lane", ""), []).append(item)

    lanes: list[dict[str, Any]] = []
    for lane_id in lane_order:
        entry = lane_entries[lane_id]
        lane_topics = sorted(
            topics_by_lane.get(lane_id, []), key=lambda row: (row["level"], row["file"])
        )
        per_level = []
        for level in (1, 2, 3, 4):
            at_level = [topic for topic in lane_topics if topic["level"] == level]
            per_level.append(
                {
                    "level": level,
                    "topics": len(at_level),
                    "reached": bool(at_level),
                    "files": [topic["file"] for topic in at_level],
                }
            )
        lanes.append(
            {
                "id": lane_id,
                "label": entry.get("label", lane_id),
                "labelZh": entry.get("labelZh"),
                "blurb": entry.get("blurb"),
                "blurbZh": entry.get("blurbZh"),
                "documentedHere": bool(entry.get("documentedHere")),
                "ownedElsewhere": entry.get("ownedElsewhere"),
                "noBlockOfItsOwn": bool(entry.get("noBlockOfItsOwn")),
                "appliesToAllLanes": bool(entry.get("appliesToAllLanes")),
                "volume": {
                    "files": lane_files.get(lane_id, 0),
                    "bytes": lane_bytes.get(lane_id, 0),
                    "evidence": "measured",
                    "blockTypes": [
                        block["blockType"] for block in blocks if block["lane"] == lane_id
                    ],
                },
                "documentedTopics": {
                    "evidence": "measured",
                    "source": "memory/game_data/README.md",
                    "total": len(lane_topics),
                    "deepestLevel": max((t["level"] for t in lane_topics), default=None),
                    "perLevel": per_level,
                    "topics": lane_topics,
                },
                "openItems": open_by_lane.get(lane_id, []),
            }
        )

    # Annotate each block with how deep its lane's documentation goes, so the
    # single corpus bar can be coloured and read without a second join.
    lane_depth = {lane["id"]: lane["documentedTopics"]["deepestLevel"] for lane in lanes}
    for block in blocks:
        block["laneDeepestDocumentedLevel"] = lane_depth.get(block["lane"])

    levels = []
    for level in index["levels"]:
        number = level["level"]
        lanes_at_level = [
            lane["id"]
            for lane in lanes
            if any(row["level"] == number and row["reached"] for row in lane["documentedTopics"]["perLevel"])
        ]
        levels.append(
            {
                **level,
                "evidence": "measured",
                "source": "memory/game_data/README.md",
                "topics": sum(1 for topic in index["topics"] if topic["level"] == number),
                "lanesWithAtLeastOneTopic": lanes_at_level,
                "openItems": [item for item in open_items if item.get("level") == number],
            }
        )

    return {
        "schema": SCHEMA,
        "generatedAt": generated_at
        or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sources": [
            _source_row(memory_index_path, "laneIndex"),
            _source_row(vfs_profile_path, "installedCorpus"),
            _source_row(jsondata_coverage_path, "jsonDataCoverage"),
            _source_row(field_semantics_path, "monoBehaviourFieldSemantics"),
            _source_row(table_keys_path, "monoBehaviourTableKeys"),
            _source_row(declarations_path, "declarations"),
        ],
        "evidenceKinds": {
            "measured": "read out of a generated report or the tracked lane index named in sources",
            "declared": "no report carries it; see the declaration's own reason",
        },
        "caveats": {
            **declarations["levelCaveats"],
            "corpusLevelDepth": {"text": CORPUS_LEVEL_DEPTH_BASIS},
        },
        "levels": levels,
        "lanes": lanes,
        "corpus": {
            "evidence": "measured",
            "totals": corpus["totals"],
            "observationStatuses": corpus["observationStatuses"],
            "blocks": blocks,
            "levelDepth": _corpus_level_depth(blocks, lanes, corpus["totals"]),
        },
        "jsonData": {
            "evidence": "measured",
            "level": 3,
            "meaning": "bytes that fall inside a framed, named field",
            **jsondata,
        },
        "monoBehaviour": {"evidence": "measured", **monobehaviour},
        "tableKeys": {"evidence": "measured", **table_keys},
        "openItems": {
            "evidence": "declared",
            "why": declarations["unreachableFromStaticData"]["_why"],
            "kind": "unreachableFromStaticData",
            "items": open_items,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build webui/data/recovery/index.json from generated reports."
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
        help="print the headline measured figures after writing",
    )
    args = parser.parse_args(argv)

    try:
        # Named explicitly so the module-level paths are resolved at call time
        # rather than frozen into build_payload's defaults.
        payload = build_payload(
            declarations_path=DECLARATIONS_PATH,
            memory_index_path=MEMORY_INDEX_PATH,
            vfs_profile_path=VFS_PROFILE_PATH,
            jsondata_coverage_path=JSONDATA_COVERAGE_PATH,
            field_semantics_path=FIELD_SEMANTICS_PATH,
            table_keys_path=TABLE_KEYS_PATH,
        )
    except RecoveryInputError as exc:
        raise SystemExit(f"recovery build failed closed: {exc}") from exc

    output = args.output
    if not output.is_absolute():
        output = ROOT / output
    write_canonical_json(output, payload)

    totals = payload["corpus"]["totals"]
    print(
        f"recovery: {totals['files']:,} logical files, {totals['bytes'] / 1e9:.2f} GB "
        f"across {totals['blockTypes']} block types -> {output}"
    )
    if args.print_summary:
        json_totals = payload["jsonData"]["totals"]
        print(
            f"  JsonData: {json_totals['familiesFullyNamed']}/{json_totals['families']} "
            f"families fully named ({json_totals['namedShare'] * 100:.2f}% of bytes)"
        )
        mono = payload["monoBehaviour"]
        print(
            f"  MonoBehaviour: {mono['classes']:,} classes, {mono['objectsSwept']:,} objects, "
            f"{mono['fieldPaths']:,} field paths"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
