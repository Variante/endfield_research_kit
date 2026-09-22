"""Measure what each named MonoBehaviour class's serialized fields own.

[`monobehaviour_census.py`](monobehaviour_census.py) collapses the exported
corpus to a few hundred script identities and
[`monobehaviour_script_names.py`](monobehaviour_script_names.py) puts a managed
class name on each one. Neither says what an instance *owns*. A name is an
identity for the script; it is not evidence that a field points at an asset,
carries a table key, or is ever written at all.

This module supplies that missing layer, per field rather than per class, and
it does it by measuring the corpus instead of reading the field names. Two
independent kinds of evidence are recorded side by side and never merged:

``declared``
    What the serialized TypeTree says. ``m_Clips.Array.data.m_Asset`` is
    declared ``PPtr<$Object>`` and ``m_AnimClip`` is declared
    ``PPtr<$AnimationClip>``. This is exact: the type tree is the serialization
    contract the engine itself wrote, so a declared PPtr *is* a reference field
    whether or not any instance fills it.

``observed``
    What the 1.35M exported objects actually hold there. A field declared as a
    reference and null in every object is a different fact from one that is
    filled 200,000 times, and the declaration alone cannot tell them apart.
    Occupancy is counted over the whole corpus, not a sample, so the numbers
    are exact for the selected export rather than estimated from it.

Resolving a filled PPtr to its target is two questions, and the row keeps them
apart because they fail differently.

*Which container holds the target* is answered by the CABMap rule in
`cabmap.py`: ``m_FileID == 0`` is the referrer's own CAB, and any other value
names the ``m_FileID - 1`` slot of its ordered dependency list. This does not
need the target to be exported, which is the point -- most MonoBehaviour
references point at GameObjects, Transforms and MonoScripts the WebUI export
scope never writes, and naming their container is as far as the export can go.
A row that gets this far and no further is ``container_only``.

*Whether that answer is right* is asked only where the target **is** exported.
The resolved file records its own ``sourceFile``, so the check meets the
prediction with evidence from a different part of the export rather than
restating it. All-agree is ``exact``; any disagreement is ``contradicted`` and
carries the two names, because a rule worth using is one that can fail visibly.

Without the CABMap the container question has no answer and rows say
``unresolved``. They do not fall back to matching a PathID globally.

PathIDs are resolvable at all only because they are measured to be unique
across this export: 1,874,804 exported objects carry 1,874,804 distinct
PathIDs, with no collision in any type directory. That is a property of the
selected export, which is why the sweep records the count it observed rather
than assuming it.

A reference that lands on another MonoBehaviour is resolved one step further,
to the target's *class*. Resolving to "a MonoBehaviour" names a Unity type;
naming the class is what makes the row a binding between two named things, and
it costs nothing extra because the target's ``scriptPathId`` sits in the same
document head the container check already reads.

One deliberate refusal. This module never labels a field from its name.
``imgRefPath`` is reported as a string field whose values contain path
separators; calling it an asset path is a reading, and it belongs in the
owning memory topic once a consumer is found, not in a generated row.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from scripts.game_data import cabmap
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.monobehaviour-field-semantics.v1"

DEFAULT_EXPORT_ROOT = REPO_ROOT / "export_full"
UNITY_SUBPATH = Path("game") / "Unity"
MONOBEHAVIOUR_SUBPATH = UNITY_SUBPATH / "MonoBehaviour"

# AnimeStudio spells the PathID into every exported filename as upper-case hex
# of the unsigned 64-bit value. That is what makes a target lookup a dictionary
# hit instead of a second corpus sweep. The suffix after it is not always a
# single extension -- an Animator with no clips is written
# ``<name>_p<id>.fbx.empty.json`` -- so the match stops at the PathID and does
# not try to anchor on the file type.
PATH_ID_IN_FILENAME = re.compile(r"_p([0-9A-F]{16})(?=\.)")

# Caps. Each one bounds memory on a corpus this size; every row records whether
# its own cap was reached, because a capped set must not read as a complete one.
# The distinct cap is per field path, and the sweep holds one of these for every
# path of every class at once, so it is sized for that product rather than for
# how many values a single field could interestingly have.
DISTINCT_CAP = 64
SAMPLE_CAP = 8

# String values are emitted in full up to the distinct cap, not trimmed to
# SAMPLE_CAP. They are the input to the table-key join, and that join's strength
# is the number of values it could check: eight sorted values share a prefix
# often enough to match a key set by accident, where sixty-four do not.
STRING_SAMPLE_CAP = DISTINCT_CAP
PATHS_PER_CLASS_CAP = 4000

# A number field with few enough distinct integral values to be a closed domain
# is reported as bounded. This is a description of the observed values, not a
# claim that the managed field is an enum.
BOUNDED_NUMBER_CAP = 16


class FieldSemanticsError(RuntimeError):
    """The sweep could not read an input it was pointed at."""


@dataclass
class FieldStats:
    """Everything the corpus shows at one flattened field path of one class."""

    declared_type: str = ""
    objects_present: int = 0
    kinds: Counter = field(default_factory=Counter)

    pptr_null: int = 0
    pptr_local: int = 0
    pptr_cross_file: int = 0
    pptr_targets: set[int] = field(default_factory=set)
    pptr_targets_capped: bool = False
    # (target PathID, m_FileID, referring CAB, referring VFS root), bounded.
    # This is what makes a reference checkable rather than merely typed: the
    # CABMap rule turns the four into a predicted target container, and the
    # resolved file's own source CAB is the answer that prediction has to meet.
    pptr_samples: list[tuple[int, int, str, str]] = field(default_factory=list)

    string_empty: int = 0
    string_values: set[str] = field(default_factory=set)
    string_values_capped: bool = False
    string_with_separator: int = 0
    string_non_empty: int = 0

    number_values: set[float] = field(default_factory=set)
    number_values_capped: bool = False
    number_min: float | None = None
    number_max: float | None = None
    number_integral: bool = True

    array_count: int = 0
    array_empty: int = 0
    array_elements: int = 0
    array_max: int = 0

    def note_pptr(
        self, file_id: int, path_id: int, source_file: str, source_root: str
    ) -> None:
        self.kinds["pptr"] += 1
        if path_id == 0:
            self.pptr_null += 1
            return
        if file_id == 0:
            self.pptr_local += 1
        else:
            self.pptr_cross_file += 1
        if source_file and len(self.pptr_samples) < SAMPLE_CAP:
            self.pptr_samples.append((path_id, file_id, source_file, source_root))
        if len(self.pptr_targets) < DISTINCT_CAP:
            self.pptr_targets.add(path_id)
        else:
            self.pptr_targets_capped = True

    def note_string(self, value: str) -> None:
        if not value:
            self.string_empty += 1
            return
        self.string_non_empty += 1
        if "/" in value or "\\" in value:
            self.string_with_separator += 1
        if len(self.string_values) < DISTINCT_CAP:
            self.string_values.add(value[:200])
        else:
            self.string_values_capped = True

    def note_number(self, value: float) -> None:
        """Record one numeric observation. The caller owns the kind counter.

        ``bool`` is recorded here too, as 0 and 1, so a field serialized as
        ``UInt8`` and a field serialized as a JSON boolean produce the same
        bounded-domain evidence instead of two incomparable shapes.
        """

        if self.number_min is None or value < self.number_min:
            self.number_min = value
        if self.number_max is None or value > self.number_max:
            self.number_max = value
        if not _finite(value) or float(value) != int(value):
            self.number_integral = False
        if len(self.number_values) < DISTINCT_CAP:
            self.number_values.add(float(value))
        else:
            self.number_values_capped = True

    def note_array(self, length: int) -> None:
        self.kinds["array"] += 1
        self.array_count += 1
        self.array_elements += length
        if length == 0:
            self.array_empty += 1
        if length > self.array_max:
            self.array_max = length


def _finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


@dataclass
class ClassStats:
    """One script identity and the per-field evidence collected for it."""

    script_path_id: int | None
    layout_signature: str
    objects: int = 0
    fields: dict[str, FieldStats] = field(default_factory=dict)
    fields_capped: bool = False
    example_file: str = ""

    def stats_for(self, path: str, declared: str) -> FieldStats | None:
        existing = self.fields.get(path)
        if existing is not None:
            return existing
        if len(self.fields) >= PATHS_PER_CLASS_CAP:
            self.fields_capped = True
            return None
        created = FieldStats(declared_type=declared)
        self.fields[path] = created
        return created


def declared_types(field_paths: list[str]) -> dict[str, str]:
    """Map the flattened value path of each TypeTree node to its declared type.

    The type tree spells an array as ``field.Array.data``; a decoded object
    spells the same place as ``field[]``. Normalising the tree onto the
    document's shape is what lets a declared type meet an observed value
    without matching them up by position.
    """

    mapping: dict[str, str] = {}
    for entry in field_paths:
        if ":" not in entry:
            continue
        raw_path, declared = entry.split(":", 1)
        if raw_path.endswith(".Array") or raw_path.endswith(".Array.size"):
            continue
        path = raw_path.replace(".Array.data", "[]")
        if ".Array" in path:
            continue
        mapping.setdefault(path, declared)
    return mapping


def _as_pptr(value: dict[str, Any]) -> tuple[int, int] | None:
    if len(value) != 2:
        return None
    file_id = value.get("m_FileID")
    path_id = value.get("m_PathID")
    if isinstance(file_id, int) and isinstance(path_id, int):
        return file_id, path_id
    return None


def _walk(
    value: Any,
    path: str,
    declared: dict[str, str],
    stats: ClassStats,
    source_file: str,
    source_root: str,
) -> None:
    """Record one decoded value, then descend, keeping the flattened path."""

    entry = stats.stats_for(path, declared.get(path, ""))
    if entry is None:
        return
    entry.objects_present += 1

    if isinstance(value, bool):
        entry.kinds["bool"] += 1
        entry.note_number(1.0 if value else 0.0)
        return
    if isinstance(value, (int, float)):
        entry.kinds["number"] += 1
        entry.note_number(float(value))
        return
    if isinstance(value, str):
        entry.kinds["string"] += 1
        entry.note_string(value)
        return
    if value is None:
        entry.kinds["null"] += 1
        return
    if isinstance(value, list):
        entry.note_array(len(value))
        child = f"{path}[]"
        for element in value:
            _walk(element, child, declared, stats, source_file, source_root)
        return
    if isinstance(value, dict):
        pptr = _as_pptr(value)
        if pptr is not None:
            entry.note_pptr(pptr[0], pptr[1], source_file, source_root)
            return
        entry.kinds["object"] += 1
        for key, child_value in value.items():
            _walk(
                child_value,
                f"{path}.{key}" if path else key,
                declared,
                stats,
                source_file,
                source_root,
            )
        return
    entry.kinds["other"] += 1


def _object_paths(root: Path) -> Iterator[Path]:
    if not root.is_dir():
        raise FieldSemanticsError(f"exported MonoBehaviour root not found: {root}")
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith(".json"):
                yield Path(entry.path)


def build_path_id_index(export_root: Path) -> tuple[dict[int, tuple[str, str]], dict[str, Any]]:
    """Index every exported object's PathID to its type directory and filename.

    This reads directory entries only. It is the cheap half of target
    resolution, and its audit records the collision count, because the index is
    usable as a key exactly to the extent that the export has none.
    """

    unity_root = Path(export_root) / UNITY_SUBPATH
    if not unity_root.is_dir():
        raise FieldSemanticsError(f"exported Unity root not found: {unity_root}")

    index: dict[int, tuple[str, str]] = {}
    per_type: Counter = Counter()
    collisions = 0
    unkeyed = 0
    for type_dir in sorted(p for p in unity_root.iterdir() if p.is_dir()):
        with os.scandir(type_dir) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue
                match = PATH_ID_IN_FILENAME.search(entry.name)
                if match is None:
                    unkeyed += 1
                    continue
                path_id = _signed64(int(match.group(1), 16))
                per_type[type_dir.name] += 1
                if path_id in index:
                    collisions += 1
                    continue
                index[path_id] = (type_dir.name, entry.name)
    audit = {
        "objectsIndexed": sum(per_type.values()),
        "distinctPathIds": len(index),
        "pathIdCollisions": collisions,
        "filesWithoutPathIdInName": unkeyed,
        "byType": dict(sorted(per_type.items())),
    }
    return index, audit


def _signed64(value: int) -> int:
    return value - (1 << 64) if value >= (1 << 63) else value


def _target_identity(path: Path) -> tuple[str | None, int | None]:
    """One exported object's source CAB and script identity, from its head.

    Both come out of the same read because a reference is checked and named at
    the same moment: the CAB says whether the container prediction held, and
    the ``scriptPathId`` says which class the reference lands on. Resolving a
    reference to "a MonoBehaviour" is a type; resolving it to the class is what
    makes it a binding between two named things.
    """

    try:
        with path.open("rb") as handle:
            head = handle.read(4096)
    except OSError:
        return None, None
    source = re.search(rb'"sourceFile"\s*:\s*"([^"]*)"', head)
    script = re.search(rb'"scriptPathId"\s*:\s*(-?\d+)', head)
    return (
        source.group(1).decode("utf-8", "replace") if source else None,
        int(script.group(1)) if script else None,
    )


def sweep(
    export_root: Path = DEFAULT_EXPORT_ROOT,
    *,
    limit: int | None = None,
    progress: int = 0,
) -> tuple[dict[tuple[int | None, str], ClassStats], dict[str, Any]]:
    """Walk every exported MonoBehaviour and collect per-field evidence."""

    from scripts.game_data.monobehaviour.census import layout_signature

    root = Path(export_root) / MONOBEHAVIOUR_SUBPATH
    classes: dict[tuple[int | None, str], ClassStats] = {}
    scanned = 0
    unreadable = 0

    for path in _object_paths(root):
        if limit is not None and scanned >= limit:
            break
        scanned += 1
        if progress and scanned % progress == 0:
            print(f"  swept {scanned} objects", file=sys.stderr, flush=True)
        try:
            document = json.loads(path.read_bytes().decode("utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            unreadable += 1
            continue
        block = document.get("$animestudio")
        if not isinstance(block, dict):
            unreadable += 1
            continue

        field_paths = [
            entry for entry in block.get("typeTreeFieldPaths") or [] if isinstance(entry, str)
        ]
        script_path_id = block.get("scriptPathId")
        if not isinstance(script_path_id, int):
            script_path_id = None
        key = (script_path_id, layout_signature(field_paths))
        stats = classes.get(key)
        if stats is None:
            stats = ClassStats(script_path_id=key[0], layout_signature=key[1])
            stats.example_file = path.name
            classes[key] = stats
        stats.objects += 1

        declared = declared_types(field_paths)
        source_file = block.get("sourceFile")
        source = source_file if isinstance(source_file, str) else ""
        original = block.get("sourceOriginalPath")
        root = cabmap.vfs_root_of(original if isinstance(original, str) else "")
        for name, value in document.items():
            if name == "$animestudio":
                continue
            _walk(value, name, declared, stats, source, root)

    audit = {
        "objectsSwept": scanned,
        "objectsUnreadable": unreadable,
        "distinctScriptLayoutPairs": len(classes),
    }
    return classes, audit


def resolve_targets(
    export_root: Path,
    classes: dict[tuple[int | None, str], ClassStats],
    index: dict[int, tuple[str, str]],
    maps: dict[str, dict[str, tuple[str, ...]]] | None = None,
    names: dict[int, str] | None = None,
) -> dict[tuple[int | None, str], dict[str, dict[str, Any]]]:
    """Resolve each field's sampled PPtr targets to a container and a type.

    Two different questions are answered here and kept apart in the row.

    *Which container holds the target* is answered by the CABMap rule in
    `cabmap.resolve_pptr`: ``m_FileID == 0`` is the referrer's own CAB, and
    anything else is its dependency list's ``m_FileID - 1`` slot. That answer
    does not need the target to be exported, which matters because most
    MonoBehaviour references point at GameObjects and Transforms the export
    never writes.

    *Whether that answer is right* is asked only where the target **is**
    exported, and the check is not a restatement: the resolved file records its
    own ``sourceFile``, so the prediction is compared against evidence produced
    by a different part of the export. A disagreement is reported as
    ``contradicted`` rather than smoothed over, because the whole value of the
    rule is that it can fail visibly.

    Passing ``maps=None`` keeps the container question unanswered rather than
    guessing at it, and the rows then say ``unresolved`` with that reason.
    """

    unity_root = Path(export_root) / UNITY_SUBPATH
    names = names or {}
    resolved: dict[tuple[int | None, str], dict[str, dict[str, Any]]] = {}
    for key, stats in classes.items():
        per_field: dict[str, dict[str, Any]] = {}
        for path, entry in stats.fields.items():
            if not entry.pptr_targets:
                continue
            hits: Counter = Counter()
            misses = 0
            for target in sorted(entry.pptr_targets):
                found = index.get(target)
                if found is None:
                    misses += 1
                else:
                    hits[found[0]] += 1

            containers: Counter = Counter()
            target_classes: Counter = Counter()
            unresolved = 0
            checked = agreed = 0
            disagreements: list[str] = []
            for target, file_id, referrer, root in entry.pptr_samples:
                if maps is None:
                    unresolved += 1
                    continue
                prediction = cabmap.resolve_pptr(
                    maps,
                    source_cab=referrer,
                    source_root=root,
                    file_id=file_id,
                    path_id=target,
                )
                if prediction is None or prediction["tier"] != "exact":
                    unresolved += 1
                    continue
                containers[prediction["basis"]] += 1
                found = index.get(target)
                if found is None:
                    continue
                actual, target_script = _target_identity(
                    unity_root / found[0] / found[1]
                )
                if target_script is not None:
                    target_classes[target_script] += 1
                if actual is None:
                    continue
                checked += 1
                if actual == prediction["cab"]:
                    agreed += 1
                elif len(disagreements) < 3:
                    disagreements.append(
                        f"predicted {prediction['cab']} but the target names {actual}"
                    )

            row: dict[str, Any] = {
                "sampledTargets": len(entry.pptr_targets),
                "resolvedExportedTypes": dict(hits.most_common()),
                "unexportedTargets": misses,
                "containerResolved": sum(containers.values()),
                "containerUnresolved": unresolved,
                "containerBasis": dict(containers.most_common()),
            }
            if target_classes:
                # A reference resolved to "a MonoBehaviour" is a type. Naming
                # the class it lands on is what makes the row a binding between
                # two named things, which is the whole question this module was
                # built to answer.
                row["targetClasses"] = {
                    names.get(script) or f"scriptPathId:{script}": count
                    for script, count in target_classes.most_common(6)
                }
            if checked:
                row["containerChecked"] = checked
                row["containerAgreed"] = agreed
                row["tier"] = "exact" if agreed == checked else "contradicted"
                if disagreements:
                    row["contradictions"] = disagreements
            elif containers:
                # The rule resolved the container, and nothing exported sits at
                # that PathID to check it against. That is weaker than a
                # verified row and stronger than an unresolved one, so it is
                # named rather than folded into either.
                row["tier"] = "container_only"
            else:
                row["tier"] = "unresolved"
            per_field[path] = row
        if per_field:
            resolved[key] = per_field
    return resolved


def classify(entry: FieldStats) -> str:
    """Describe one field from its observed values, never from its name."""

    kinds = entry.kinds
    if not kinds:
        return "unobserved"
    dominant = kinds.most_common(1)[0][0]
    if dominant == "pptr":
        filled = entry.pptr_local + entry.pptr_cross_file
        if filled == 0:
            return "reference_always_null"
        if entry.pptr_cross_file == 0:
            return "reference_local"
        if entry.pptr_local == 0:
            return "reference_cross_file"
        return "reference_mixed"
    if dominant == "string":
        if entry.string_non_empty == 0:
            return "string_always_empty"
        if entry.string_with_separator == entry.string_non_empty:
            return "string_with_separators"
        if not entry.string_values_capped and len(entry.string_values) == 1:
            return "string_constant"
        if not entry.string_values_capped and len(entry.string_values) <= BOUNDED_NUMBER_CAP:
            return "string_bounded"
        return "string_free"
    if dominant in ("number", "bool"):
        if not entry.number_values_capped and len(entry.number_values) == 1:
            return "number_constant"
        if (
            entry.number_integral
            and not entry.number_values_capped
            and len(entry.number_values) <= BOUNDED_NUMBER_CAP
        ):
            return "number_bounded"
        return "number_continuous" if not entry.number_integral else "number_integral"
    if dominant == "array":
        return "array_always_empty" if entry.array_elements == 0 else "array"
    if dominant == "object":
        return "struct"
    return dominant


def field_row(path: str, entry: FieldStats, objects: int) -> dict[str, Any]:
    row: dict[str, Any] = {
        "path": path,
        "declaredType": entry.declared_type,
        "classification": classify(entry),
        "valuesSeen": entry.objects_present,
        "valueKinds": dict(entry.kinds.most_common()),
    }
    if entry.kinds.get("pptr"):
        filled = entry.pptr_local + entry.pptr_cross_file
        row["reference"] = {
            "null": entry.pptr_null,
            "local": entry.pptr_local,
            "crossFile": entry.pptr_cross_file,
            "filledShare": round(filled / entry.kinds["pptr"], 4),
            "distinctTargetsSampled": len(entry.pptr_targets),
            "distinctTargetsCapped": entry.pptr_targets_capped,
        }
    if entry.kinds.get("string"):
        samples = sorted(entry.string_values)[:STRING_SAMPLE_CAP]
        row["string"] = {
            "empty": entry.string_empty,
            "nonEmpty": entry.string_non_empty,
            "withSeparator": entry.string_with_separator,
            "distinctSampled": len(entry.string_values),
            "distinctCapped": entry.string_values_capped,
            "samples": samples,
        }
    if entry.kinds.get("number") or entry.kinds.get("bool"):
        row["number"] = {
            "min": entry.number_min,
            "max": entry.number_max,
            "integral": entry.number_integral,
            "distinctSampled": len(entry.number_values),
            "distinctCapped": entry.number_values_capped,
        }
    if entry.kinds.get("array"):
        row["array"] = {
            "arrays": entry.array_count,
            "empty": entry.array_empty,
            "elements": entry.array_elements,
            "maxLength": entry.array_max,
        }
    if entry.objects_present < objects:
        row["absentInObjects"] = objects - entry.objects_present
    return row


def build_report(
    export_root: Path = DEFAULT_EXPORT_ROOT,
    *,
    names_report: Path | None = None,
    limit: int | None = None,
    top: int | None = None,
    progress: int = 0,
) -> dict[str, Any]:
    """Sweep the corpus and render the per-class, per-field evidence."""

    index, index_audit = build_path_id_index(export_root)
    try:
        maps = cabmap.load_dependencies(Path(export_root) / "meta" / "cab_map")
        cab_map_audit: dict[str, Any] = {
            root: len(table) for root, table in sorted(maps.items())
        }
    except cabmap.CabMapError as exc:
        # Without the CABMap the container question has no answer, and a row
        # must say so rather than fall back to matching a PathID globally.
        maps = None
        cab_map_audit = {"unavailable": str(exc)}
    classes, sweep_audit = sweep(export_root, limit=limit, progress=progress)
    names = _load_names(names_report) if names_report else {}
    resolved = resolve_targets(export_root, classes, index, maps, names)

    ordered = sorted(classes.values(), key=lambda item: (-item.objects, item.layout_signature))
    if top is not None:
        ordered = ordered[:top]

    rows: list[dict[str, Any]] = []
    for stats in ordered:
        key = (stats.script_path_id, stats.layout_signature)
        per_field_targets = resolved.get(key, {})
        field_rows = []
        for path, entry in stats.fields.items():
            row = field_row(path, entry, stats.objects)
            target = per_field_targets.get(path)
            if target is not None:
                row["targets"] = target
            field_rows.append(row)
        rows.append(
            {
                "scriptPathId": stats.script_path_id,
                "layoutSignature": stats.layout_signature,
                "scriptClass": names.get(stats.script_path_id),
                "objects": stats.objects,
                "exampleFile": stats.example_file,
                "fieldPathsRecorded": len(stats.fields),
                "fieldPathsCapped": stats.fields_capped,
                "fields": field_rows,
            }
        )

    return {
        "schema": SCHEMA,
        "exportRoot": str(export_root),
        "namesReport": str(names_report) if names_report else None,
        "limit": limit,
        "pathIdIndex": index_audit,
        "cabMap": cab_map_audit,
        "summary": _summarise(rows, sweep_audit),
        "classes": rows,
    }


def _load_names(report: Path) -> dict[int, str]:
    try:
        document = json.loads(Path(report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FieldSemanticsError(f"unreadable names report {report}: {exc}") from exc
    names: dict[int, str] = {}
    for row in document.get("classes") or []:
        script_path_id = row.get("scriptPathId")
        name = row.get("scriptPathIdClass") or row.get("scriptClass")
        if isinstance(script_path_id, int) and isinstance(name, str):
            names[script_path_id] = name
    return names


def _summarise(rows: list[dict[str, Any]], sweep_audit: dict[str, Any]) -> dict[str, Any]:
    by_classification: Counter = Counter()
    reference_fields = 0
    filled_reference_fields = 0
    for row in rows:
        for entry in row["fields"]:
            by_classification[entry["classification"]] += 1
            if entry["classification"].startswith("reference"):
                reference_fields += 1
                if entry["classification"] != "reference_always_null":
                    filled_reference_fields += 1
    return {
        **sweep_audit,
        "classesReported": len(rows),
        "fieldPathsReported": sum(row["fieldPathsRecorded"] for row in rows),
        "fieldsByClassification": dict(by_classification.most_common()),
        "referenceFields": reference_fields,
        "referenceFieldsEverFilled": filled_reference_fields,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure, per named MonoBehaviour class, which serialized fields "
            "are references, what they resolve to, and how often they are filled."
        )
    )
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument(
        "--names-report",
        type=Path,
        help="monobehaviour_script_names report, to label rows with a class name",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="stop after this many objects; a bounded probe, not a census",
    )
    parser.add_argument(
        "--top",
        type=int,
        help="report only the N largest classes by object count",
    )
    parser.add_argument(
        "--progress",
        type=int,
        default=0,
        metavar="N",
        help="print progress to stderr every N objects",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        report = build_report(
            args.export_root,
            names_report=args.names_report,
            limit=args.limit,
            top=args.top,
            progress=args.progress,
        )
    except FieldSemanticsError as exc:
        print(f"MonoBehaviour field semantics unavailable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        summary = report["summary"]
        print(
            f"swept {summary['objectsSwept']} MonoBehaviour objects into "
            f"{summary['classesReported']} reported classes and "
            f"{summary['fieldPathsReported']} field paths -> {args.report}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.monobehaviour.field_semantics")
    raise SystemExit(main())
