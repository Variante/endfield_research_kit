"""Audit authored EffectActionCfg enum values in exact SkillData/BuffData.

The whole-record derived plans identify each nested EffectActionCfg by its
wrapper reference and consume its bytes to EOF. This audit joins fifteen of
its stored scalar members to the selected build's declaring field types and
enum defaults. It does not observe effect spawning, runtime overrides, or
which branch executes.
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


DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/memorypack_effect_config_enums.json"
EFFECT_TYPE = "Beyond.Gameplay.EffectActionCfg"
ENUM_FIELDS = (
    "alertType", "cameraScreenSizeScaleMode", "directionRef", "fxType",
    "modifyType", "mountPoint", "moveType", "offsetDir", "positionRef",
    "rotMountPoint", "rotRef", "rotType", "rotWeaponMountPoint",
    "visibleWithEntityType", "weaponMountPoint",
)
FAMILIES = {
    SKILLDATA_DIRECTORY: SKILLDATA_TYPE,
    BUFFDATA_DIRECTORY: BUFFDATA_TYPE,
}
MAX_FAILURES = 20


def effect_definition(registry: PlanRegistry) -> int:
    matches = [definition for definition, name in registry.wrapped_names.items()
               if name == EFFECT_TYPE and definition in registry.plans]
    if len(matches) != 1:
        raise ValueError(f"effect-config-plan-count={len(matches)}")
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
        "schema": "endfield.memorypack-effect-config-enums.v1",
        "nativeGate": gate,
        "exportRoot": str(layout.root),
        "families": {},
        "enumFields": {},
        "valueCounts": {},
        "summary": {"status": gate.get("status", "unavailable")},
    }
    if gate.get("status") != "validated":
        _write_report(output, report)
        return report
    try:
        definition = effect_definition(registry)
        image = NativeImage(gameassembly, metadata, label="effect-config-corpus")
        enum_names, enum_audit = selected_enum_fields(
            image, registry, definition,
            owner_type=EFFECT_TYPE, enum_fields=ENUM_FIELDS,
        )
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report["failures"] = [{"gate": "selected-effect-enum-fields", "detail": str(error)}]
        report["summary"] = {"status": "incomplete", "gate": "selected-effect-enum-fields"}
        _write_report(output, report)
        return report
    report["plannedWrapperDefinition"] = definition
    report["enumFields"] = enum_audit
    failures: list[dict[str, Any]] = []
    failure_count = 0
    counts: dict[str, Counter[int]] = {name: Counter() for name in ENUM_FIELDS}
    examples: dict[str, dict[int, dict[str, Any]]] = {name: {} for name in ENUM_FIELDS}
    source_digest = hashlib.sha256()
    total_files = total_configs = total_null = 0
    for family, type_name in FAMILIES.items():
        directory = layout.json_dir / family
        root_definition = registry.named_roots.get(type_name)
        paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
        family_row = {"files": len(paths), "exact": 0,
                      "effectConfigs": 0, "nullEffectConfigs": 0}
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
                # The generic plan walker was first used for TargetSettings;
                # here its target definition is EffectActionCfg.
                found = list(walk_targets(value, registry, root_definition, definition))
            except (Unsupported, ValueError, KeyError, IndexError, TypeError,
                    struct.error, UnicodeDecodeError, RecursionError) as error:
                failure_count += 1
                if len(failures) < MAX_FAILURES:
                    failures.append({"family": family, "source": path.name,
                                     "gate": "exact-decode-or-plan-walk", "detail": str(error)})
                continue
            family_row["exact"] += 1
            for action_path, config, context in found:
                if config is None:
                    family_row["nullEffectConfigs"] += 1
                    total_null += 1
                    continue
                family_row["effectConfigs"] += 1
                total_configs += 1
                for name in ENUM_FIELDS:
                    stored = config[name]
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
    report["failures"] = failures
    report["summary"] = {
        "status": "validated" if not failure_count and total_configs else "incomplete",
        "files": total_files,
        "exactFiles": sum(row["exact"] for row in report["families"].values()),
        "effectConfigs": total_configs,
        "nullEffectConfigs": total_null,
        "enumFields": len(ENUM_FIELDS),
        "failureCount": failure_count,
        "failureExamples": len(failures),
        "evidenceBoundary": (
            "Exact authored EffectActionCfg scalar values and selected native enum names; "
            "no runtime effect, branch selection, spawn, or override is observed."
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
