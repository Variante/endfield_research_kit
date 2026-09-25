"""Audit authored DamageUnit enums in exact SkillData and BuffData records.

This follows selected-build derived plans through whole records to EOF. It
names stored enum values, not runtime damage computation or branch execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.memorypack.buff_actions import Unsupported
from scripts.game_data.memorypack.derived_plans import (
    BUFFDATA_DIRECTORY,
    BUFFDATA_TYPE,
    SKILLDATA_DIRECTORY,
    SKILLDATA_TYPE,
    PlanRegistry,
    load_registry,
)
from scripts.game_data.memorypack.derived_values import decode_file, find_identifier
from scripts.game_data.memorypack.target_settings_corpus import selected_enum_fields, walk_targets
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout


DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/memorypack_damage_unit_enums.json"
DAMAGE_UNIT_TYPE = "Beyond.Gameplay.Core.DamageAction+DamageUnit"
ENUM_FIELDS = (
    "damageAttributeType", "damageType", "damageVisualImportance",
    "ignoreDamageImmuneLevel",
)
CALCULATION_FIELDS = ("atkCalculation", "poiseCalculation")
CALCULATION_ENUM_FIELDS = {
    "Beyond.Gameplay.Core.MultiplyAttributeCalculation": (
        "attributeType", "valueSource",
    ),
    "Beyond.Gameplay.Core.PrimaryAttrCalculation": (
        "type", "valueSource",
    ),
}
FAMILIES = {
    SKILLDATA_DIRECTORY: SKILLDATA_TYPE,
    BUFFDATA_DIRECTORY: BUFFDATA_TYPE,
}
MAX_FAILURES = 20


def damage_unit_definition(registry: PlanRegistry) -> int:
    matches = [definition for definition, name in registry.wrapped_names.items()
               if name == DAMAGE_UNIT_TYPE and definition in registry.plans]
    if len(matches) != 1:
        raise ValueError(f"damage-unit-plan-count={len(matches)}")
    return matches[0]


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


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
        "schema": "endfield.memorypack-damage-unit-enums.v2",
        "nativeGate": gate,
        "exportRoot": str(layout.root),
        "families": {},
        "enumFields": {},
        "valueCounts": {},
        "calculationTypes": {},
        "calculationEnumFields": {},
        "calculationEnumValueCounts": {},
        "summary": {"status": gate.get("status", "unavailable")},
    }
    if gate.get("status") != "validated":
        _write_report(output, report)
        return report
    try:
        definition = damage_unit_definition(registry)
        image = NativeImage(gameassembly, metadata, label="damage-unit-corpus")
        enum_names, enum_audit = selected_enum_fields(
            image, registry, definition,
            owner_type=DAMAGE_UNIT_TYPE, enum_fields=ENUM_FIELDS,
        )
        calc_enum_names: dict[str, dict[str, dict[int, str]]] = {}
        calc_enum_audit: dict[str, dict[str, Any]] = {}
        for type_name, field_names in CALCULATION_ENUM_FIELDS.items():
            matches = [item for item, name in registry.wrapped_names.items()
                       if name == type_name and item in registry.plans]
            if len(matches) != 1:
                raise ValueError(f"calculation-plan-count={type_name}:{len(matches)}")
            calc_enum_names[type_name], calc_enum_audit[type_name] = selected_enum_fields(
                image, registry, matches[0],
                owner_type=type_name, enum_fields=field_names,
            )
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report["failures"] = [{"gate": "selected-damage-or-calculation-enum-fields", "detail": str(error)}]
        report["summary"] = {"status": "incomplete", "gate": "selected-damage-or-calculation-enum-fields"}
        _write_report(output, report)
        return report
    report["plannedWrapperDefinition"] = definition
    report["enumFields"] = enum_audit
    report["calculationEnumFields"] = calc_enum_audit
    failures: list[dict[str, Any]] = []
    failure_count = 0
    counts: dict[str, Counter[int]] = {name: Counter() for name in ENUM_FIELDS}
    examples: dict[str, dict[int, dict[str, Any]]] = {name: {} for name in ENUM_FIELDS}
    calc_counts: dict[str, Counter[str]] = {name: Counter() for name in CALCULATION_FIELDS}
    calc_examples: dict[str, dict[str, dict[str, Any]]] = {
        name: {} for name in CALCULATION_FIELDS
    }
    calc_enum_counts = {
        type_name: {field: Counter() for field in fields}
        for type_name, fields in CALCULATION_ENUM_FIELDS.items()
    }
    calc_enum_examples: dict[str, dict[str, dict[int, dict[str, Any]]]] = {
        type_name: {field: {} for field in fields}
        for type_name, fields in CALCULATION_ENUM_FIELDS.items()
    }
    source_digest = hashlib.sha256()
    total_files = total_units = total_null = 0
    for family, type_name in FAMILIES.items():
        directory = layout.json_dir / family
        root_definition = registry.named_roots.get(type_name)
        paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
        family_row = {"files": len(paths), "exact": 0,
                      "damageUnits": 0, "nullDamageUnits": 0}
        report["families"][family] = family_row
        if root_definition is None or not paths:
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
                value, reached = decode_file(raw, root_definition, registry, source=path.name)
                if reached != len(raw):
                    raise ValueError(f"cursor={reached}, length={len(raw)}")
                identifier = find_identifier(value)
                if identifier != path.stem:
                    raise ValueError(f"identifier={identifier!r}, filename={path.stem!r}")
                found = list(walk_targets(value, registry, root_definition, definition))
            except (Unsupported, ValueError, KeyError, IndexError, TypeError,
                    struct.error, UnicodeDecodeError, RecursionError) as error:
                failure_count += 1
                if len(failures) < MAX_FAILURES:
                    failures.append({"family": family, "source": path.name,
                                     "gate": "exact-decode-or-plan-walk", "detail": str(error)})
                continue
            family_row["exact"] += 1
            for action_path, unit, context in found:
                if unit is None:
                    family_row["nullDamageUnits"] += 1
                    total_null += 1
                    continue
                family_row["damageUnits"] += 1
                total_units += 1
                for name in CALCULATION_FIELDS:
                    calculation = unit.get(name)
                    if name not in unit or (calculation is not None and (
                        not isinstance(calculation, dict)
                        or not isinstance(calculation.get("$type"), str)
                        or type(calculation.get("$tag")) is not int
                    )):
                        failure_count += 1
                        if len(failures) < MAX_FAILURES:
                            failures.append({
                                "family": family, "source": path.name,
                                "path": action_path, "field": name,
                                "gate": "planned-calculation-subtype",
                            })
                        continue
                    type_name = "null" if calculation is None else calculation["$type"]
                    calc_counts[name][type_name] += 1
                    calc_examples[name].setdefault(type_name, {
                        "family": family, "source": path.name,
                        "path": action_path, "enclosingType": context,
                    })
                    if type_name in CALCULATION_ENUM_FIELDS:
                        payload = calculation.get("$value")
                        for field in CALCULATION_ENUM_FIELDS[type_name]:
                            stored = payload.get(field) if isinstance(payload, dict) else None
                            if type(stored) is not int or stored not in calc_enum_names[type_name][field]:
                                failure_count += 1
                                if len(failures) < MAX_FAILURES:
                                    failures.append({
                                        "family": family, "source": path.name,
                                        "path": action_path, "calculation": name,
                                        "type": type_name, "field": field,
                                        "gate": "selected-calculation-enum-member",
                                        "value": stored,
                                    })
                                continue
                            calc_enum_counts[type_name][field][stored] += 1
                            calc_enum_examples[type_name][field].setdefault(stored, {
                                "family": family, "source": path.name,
                                "path": f"{action_path}.{name}",
                            })
                for name in ENUM_FIELDS:
                    stored = unit.get(name)
                    if type(stored) is not int or stored not in enum_names[name]:
                        failure_count += 1
                        if len(failures) < MAX_FAILURES:
                            failures.append({
                                "family": family, "source": path.name,
                                "path": action_path, "field": name,
                                "gate": "selected-enum-member", "value": stored,
                            })
                        continue
                    counts[name][stored] += 1
                    examples[name].setdefault(stored, {
                        "family": family, "source": path.name,
                        "path": action_path, "enclosingType": context,
                    })
    report["sourceSetSha256"] = source_digest.hexdigest()
    report["valueCounts"] = {
        name: [
            {"id": number, "name": enum_names[name][number], "count": count,
             "example": examples[name][number]}
            for number, count in sorted(counts[name].items())
        ]
        for name in ENUM_FIELDS
    }
    report["calculationTypes"] = {
        name: [
            {"type": type_name, "count": count,
             "example": calc_examples[name][type_name]}
            for type_name, count in sorted(calc_counts[name].items())
        ]
        for name in CALCULATION_FIELDS
    }
    report["calculationEnumValueCounts"] = {
        type_name: {
            field: [
                {"id": number, "name": calc_enum_names[type_name][field][number],
                 "count": count,
                 "example": calc_enum_examples[type_name][field][number]}
                for number, count in sorted(calc_enum_counts[type_name][field].items())
            ]
            for field in fields
        }
        for type_name, fields in CALCULATION_ENUM_FIELDS.items()
    }
    report["failures"] = failures
    report["summary"] = {
        "status": "validated" if not failure_count and total_units else "incomplete",
        "files": total_files,
        "exactFiles": sum(row["exact"] for row in report["families"].values()),
        "damageUnits": total_units,
        "nullDamageUnits": total_null,
        "enumFields": len(ENUM_FIELDS),
        "calculationFields": len(CALCULATION_FIELDS),
        "calculationEnumFields": sum(map(len, CALCULATION_ENUM_FIELDS.values())),
        "failureCount": failure_count,
        "failureExamples": len(failures),
        "evidenceBoundary": (
            "Exact authored DamageUnit scalar values, selected native enum names, "
            "planned calculation subtype identities and selected calculation enum names; "
            "no runtime calculation, branch selection, mitigation, or damage event is observed."
        ),
    }
    _write_report(output, report)
    return report


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
