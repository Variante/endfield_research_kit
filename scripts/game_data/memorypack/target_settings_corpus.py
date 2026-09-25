"""Audit exact TargetSettings values against the selected build's enum fields.

This follows the same derived plans that decoded each whole record. A matching
dictionary shape alone cannot identify a TargetSettings instance: the plan's
object reference must name its wrapper. Enum names are selected from the
explicit GameAssembly/metadata pair only after their declaring fields agree
with that wrapper's member plan. The report describes stored authored values,
not a runtime target selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import (
    field_defaults,
    native_enum_members,
    runtime_type_name,
)
from scripts.game_data.memorypack.buff_actions import Unsupported
from scripts.game_data.memorypack.derived_plans import (
    BUFFDATA_DIRECTORY,
    BUFFDATA_TYPE,
    SKILLDATA_DIRECTORY,
    SKILLDATA_TYPE,
    PlanRegistry,
    load_registry,
)
from scripts.game_data.memorypack.derived_schema import LIST, MAP, OBJECT, UNION, MemberPlan
from scripts.game_data.memorypack.derived_values import decode_file, find_identifier
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout


DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/memorypack_target_settings.json"
TARGET_TYPE = "Beyond.Gameplay.Core.TargetSettings"
ENUM_FIELDS = (
    "centerType", "selectorDirection", "selectorOwner", "target", "targetSource",
)
FAMILIES = {
    SKILLDATA_DIRECTORY: SKILLDATA_TYPE,
    BUFFDATA_DIRECTORY: BUFFDATA_TYPE,
}
MAX_FAILURES = 20
MAX_EXAMPLES = 3
MAX_DEPTH = 512


def target_definition(registry: PlanRegistry) -> int:
    matches = [definition for definition, name in registry.wrapped_names.items()
               if name == TARGET_TYPE and definition in registry.plans]
    if len(matches) != 1:
        raise ValueError(f"target-settings-plan-count={len(matches)}")
    return matches[0]


def selected_enum_fields(
    image: NativeImage, registry: PlanRegistry, definition: int,
    *, owner_type: str = TARGET_TYPE, enum_fields: tuple[str, ...] = ENUM_FIELDS,
) -> tuple[dict[str, dict[int, str]], dict[str, Any]]:
    """Join one planned object's enum members to selected runtime field types."""
    metadata, pe = image.metadata, image.pe
    owners = [item for item in metadata.types if metadata.type_full_name(item) == owner_type]
    if len(owners) != 1:
        raise ValueError(f"selected-enum-runtime-type-count={owner_type}:{len(owners)}")
    runtime_fields = list(metadata.fields_for(owners[0]))
    members = {member.name: member for member in registry.plans[definition]}
    type_table = int(image.registration["types"], 16)
    type_count = int(image.registration["typesCount"])
    defaults = field_defaults(metadata)
    names: dict[str, dict[int, str]] = {}
    audit: dict[str, Any] = {}
    for name in enum_fields:
        member = members.get(name)
        fields = [item for item in runtime_fields
                  if metadata.string(item.name_index) == name]
        if member is None or len(fields) != 1 or member.kind != "fixed" or member.width != 4:
            raise ValueError(f"selected-enum-field-unavailable={owner_type}.{name}")
        field = fields[0]
        if not 0 <= field.type_index < type_count:
            raise ValueError(f"selected-enum-type-index={owner_type}.{name}:{field.type_index}")
        type_va = pe.u64_at_va(type_table + field.type_index * 8)
        if not type_va:
            raise ValueError(f"selected-enum-type-pointer={owner_type}.{name}")
        enum_type = runtime_type_name(pe, metadata, type_va)
        rows = native_enum_members(metadata, defaults, pe, image.registration, enum_type)
        by_id: dict[int, str] = {}
        for row in rows:
            value = int(row["id"])
            if value in by_id:
                raise ValueError(f"selected-enum-duplicate-id={enum_type}:{value}")
            by_id[value] = str(row["name"])
        if not by_id:
            raise ValueError(f"selected-enum-empty={enum_type}")
        names[name] = by_id
        audit[name] = {
            "runtimeFieldToken": f"0x{field.token:08x}",
            "enumType": enum_type,
            "serializedWidth": member.width,
            "members": rows,
        }
    return names, audit


def walk_targets(
    value: Any, registry: PlanRegistry, definition: int, target: int,
    path: str = "$", depth: int = 0, context: str | None = None,
) -> Iterator[tuple[str, dict[str, Any] | None, str | None]]:
    """Visit TargetSettings objects by plan reference, including nulls."""
    if depth > MAX_DEPTH:
        raise ValueError(f"target-settings-walk-depth={path}")
    if value is None:
        return
    if not isinstance(value, dict):
        raise ValueError(f"planned-object-not-dict={path}")
    members = registry.plans[definition]
    if set(value) != {member.name for member in members}:
        raise ValueError(f"planned-object-member-mismatch={path}")
    if definition == target:
        yield path, value, context
    for member in members:
        yield from _walk_member(
            value[member.name], member, registry, target,
            f"{path}.{member.name}", depth + 1, context,
        )


def _walk_member(
    value: Any, member: MemberPlan, registry: PlanRegistry, target: int,
    path: str, depth: int, context: str | None,
) -> Iterator[tuple[str, dict[str, Any] | None, str | None]]:
    if depth > MAX_DEPTH:
        raise ValueError(f"target-settings-walk-depth={path}")
    if member.kind == OBJECT:
        if member.ref == target and value is None:
            yield path, None, context
        elif value is not None:
            yield from walk_targets(value, registry, member.ref, target, path, depth, context)
    elif member.kind == LIST and value is not None:
        if not isinstance(value, list) or member.element is None:
            raise ValueError(f"planned-list-mismatch={path}")
        for index, item in enumerate(value):
            yield from _walk_member(item, member.element, registry, target,
                                    f"{path}[{index}]", depth + 1, context)
    elif member.kind == MAP and value is not None:
        if not isinstance(value, list):
            raise ValueError(f"planned-map-mismatch={path}")
        for index, item in enumerate(value):
            if member.key is not None and member.value is not None:
                yield from _walk_member(item["key"], member.key, registry, target,
                                        f"{path}[{index}].key", depth + 1, context)
                yield from _walk_member(item["value"], member.value, registry, target,
                                        f"{path}[{index}].value", depth + 1, context)
    elif member.kind == UNION and value is not None:
        if not isinstance(value, dict) or member.ref is None:
            raise ValueError(f"planned-union-mismatch={path}")
        subtype = registry.union_tag_maps[member.ref].get(value.get("$tag"))
        if subtype is None:
            raise ValueError(f"planned-union-tag-mismatch={path}:{value.get('$tag')}")
        yield from walk_targets(
            value.get("$value"), registry, subtype, target,
            path + ".$value", depth + 1, str(value.get("$type") or context),
        )


def build(
    output: Path, export_root: Path, gameassembly: Path, metadata: Path,
) -> dict[str, Any]:
    output = output.resolve()
    reports = (REPO_ROOT / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    layout = ExportLayout(export_root).require()
    registry, gate = load_registry(gameassembly=gameassembly, metadata=metadata)
    report: dict[str, Any] = {
        "schema": "endfield.memorypack-target-settings-corpus.v1",
        "nativeGate": gate,
        "exportRoot": str(layout.root),
        "families": {},
        "enumFields": {},
        "summary": {"status": gate.get("status", "unavailable")},
    }
    if gate.get("status") != "validated":
        _write_report(output, report)
        return report
    try:
        target = target_definition(registry)
        image = NativeImage(gameassembly, metadata, label="target-settings-corpus")
        enum_names, enum_audit = selected_enum_fields(image, registry, target)
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report["failures"] = [{"gate": "selected-target-enum-fields", "detail": str(error)}]
        report["summary"] = {"status": "incomplete", "gate": "selected-target-enum-fields"}
        _write_report(output, report)
        return report
    report["enumFields"] = enum_audit
    failures: list[dict[str, Any]] = []
    counts: dict[str, Counter[int]] = {name: Counter() for name in ENUM_FIELDS}
    examples: dict[str, dict[int, list[dict[str, Any]]]] = {
        name: {} for name in ENUM_FIELDS
    }
    source_contexts: dict[int, dict[str, Any]] = {}
    total_files = total_targets = total_null = 0
    failure_count = 0
    source_digest = hashlib.sha256()
    for family, type_name in FAMILIES.items():
        directory = layout.json_dir / family
        definition = registry.named_roots.get(type_name)
        paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
        family_row = {"files": len(paths), "exact": 0, "targetSettings": 0,
                      "nullTargetSettings": 0}
        report["families"][family] = family_row
        if definition is None or not paths:
            failure_count += 1
            failures.append({"family": family, "gate": "missing-plan-or-files",
                             "directory": str(directory)})
            continue
        total_files += len(paths)
        for path in paths:
            raw = path.read_bytes()
            source_digest.update(f"{family}/{path.name}\t{len(raw)}\t".encode("utf-8"))
            source_digest.update(hashlib.sha256(raw).digest())
            try:
                value, reached = decode_file(raw, definition, registry, source=path.name)
                if reached != len(raw):
                    raise ValueError(f"cursor={reached}, length={len(raw)}")
                identifier = find_identifier(value)
                if identifier != path.stem:
                    raise ValueError(f"identifier={identifier!r}, filename={path.stem!r}")
                found = list(walk_targets(value, registry, definition, target))
            except (Unsupported, ValueError, KeyError, IndexError, TypeError,
                    struct.error, UnicodeDecodeError, RecursionError) as error:
                failure_count += 1
                if len(failures) < MAX_FAILURES:
                    failures.append({"family": family, "source": path.name,
                                     "gate": "exact-decode-or-plan-walk", "detail": str(error)})
                continue
            family_row["exact"] += 1
            for action_path, target_value, context in found:
                if target_value is None:
                    family_row["nullTargetSettings"] += 1
                    total_null += 1
                    continue
                family_row["targetSettings"] += 1
                total_targets += 1
                source_value = target_value["targetSource"]
                if isinstance(source_value, int) and source_value in enum_names["targetSource"]:
                    source_row = source_contexts.setdefault(source_value, {
                        "selectorDataPresent": 0,
                        "selectorDataNull": 0,
                        "finderDataPresent": 0,
                        "finderDataNull": 0,
                        "finderTypes": Counter(),
                        "targetGroupKeyNonempty": 0,
                        "targetContextKeyNonempty": 0,
                        "withoutGroupKeyExamples": [],
                        "withoutFinderExamples": [],
                    })
                    selector = target_value["selectorData"]
                    if selector is None:
                        source_row["selectorDataNull"] += 1
                        source_row["finderDataNull"] += 1
                    else:
                        source_row["selectorDataPresent"] += 1
                        finder = selector.get("finderData") if isinstance(selector, dict) else None
                        if isinstance(finder, dict):
                            source_row["finderDataPresent"] += 1
                            source_row["finderTypes"][str(finder.get("$type"))] += 1
                        else:
                            source_row["finderDataNull"] += 1
                            if len(source_row["withoutFinderExamples"]) < MAX_EXAMPLES:
                                source_row["withoutFinderExamples"].append(
                                    {"family": family, "source": path.name,
                                     "path": action_path, "enclosingType": context}
                                )
                    for key in ("targetGroupKey", "targetContextKey"):
                        if target_value[key]:
                            source_row[key + "Nonempty"] += 1
                    if not target_value["targetGroupKey"] and len(source_row["withoutGroupKeyExamples"]) < MAX_EXAMPLES:
                        source_row["withoutGroupKeyExamples"].append(
                            {"family": family, "source": path.name,
                             "path": action_path, "enclosingType": context}
                        )
                for name in ENUM_FIELDS:
                    stored = target_value[name]
                    if not isinstance(stored, int) or isinstance(stored, bool) or stored not in enum_names[name]:
                        failure_count += 1
                        if len(failures) < MAX_FAILURES:
                            failures.append({
                                "family": family, "source": path.name,
                                "path": action_path, "field": name,
                                "gate": "selected-enum-member", "value": stored,
                            })
                        continue
                    counts[name][stored] += 1
                    sample = examples[name].setdefault(stored, [])
                    if len(sample) < MAX_EXAMPLES:
                        sample.append({"family": family, "source": path.name,
                                       "path": action_path, "enclosingType": context})
    report["sourceSetSha256"] = source_digest.hexdigest().upper()
    report["values"] = {
        name: [
            {"id": value, "name": enum_names[name][value], "occurrences": count,
             "examples": examples[name][value]}
            for value, count in sorted(counts[name].items())
        ] for name in ENUM_FIELDS
    }
    report["targetSourceContexts"] = [
        {
            "id": value,
            "name": enum_names["targetSource"][value],
            **{key: number for key, number in row.items() if key != "finderTypes"},
            "finderTypes": dict(sorted(row["finderTypes"].items())),
        }
        for value, row in sorted(source_contexts.items())
    ]
    report["failures"] = failures
    report["summary"] = {
        "status": "validated" if not failure_count and total_targets else "incomplete",
        "files": total_files,
        "exactFiles": sum(row["exact"] for row in report["families"].values()),
        "targetSettings": total_targets,
        "nullTargetSettings": total_null,
        "failureCount": failure_count,
        "failureExamples": len(failures),
        "evidenceBoundary": (
            "Exact authored TargetSettings values and selected enum names. "
            "No runtime target, branch selection, or execution is observed."
        ),
    }
    _write_report(output, report)
    return report


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-root", type=Path, default=ExportLayout.configured().root)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args.output, args.export_root, args.gameassembly, args.metadata)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
