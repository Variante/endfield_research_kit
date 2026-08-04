#!/usr/bin/env python3
"""Census direct native callers that consume multiple recovery subsystems.

The scan is intentionally corpus-driven.  It maps every current IL2CPP method
pointer, scans both executable GameAssembly sections for direct ``E8 rel32``
calls, and reports callers that cross MissionSystem, DynamicScene, LevelScript,
or Story API families.  No mission, quest, Story, scene, or object id is seeded.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
CATALOG_PATH = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_JSON = ROOT / "reports" / "story" / "recovery" / "native_cross_system_consumer_census.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "story" / "recovery" / "native_cross_system_consumer_census.md"
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
MAX_POINTER_ALIASES = 8
EXPECTED_CLASS_COUNTS = {
    "mission_state_controls_dynamic_component_availability": 4,
    "shared_trigger_geometry_adapter": 3,
    "global_level_load_synchronization": 1,
    "story_dynamic_scene_visual_context": 8,
    "mission_or_dialog_alternate_action_consumer": 1,
}


class AuditError(RuntimeError):
    """Raised when the build-locked census cannot be validated safely."""


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot load required helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def method_symbol(row: dict[str, Any]) -> str:
    return f"{row.get('type', '')}.{row.get('method', '')}"


def api_families(row: dict[str, Any]) -> set[str]:
    """Classify APIs by managed namespace/type semantics, never content ids."""
    type_name = str(row.get("type") or "")
    method_name = str(row.get("method") or "")
    result: set[str] = set()
    if type_name == "Beyond.Gameplay.MissionSystem":
        result.add("mission_system")
    if type_name.startswith("Beyond.Gameplay.Core.DynamicScene."):
        result.add("dynamic_scene")
    if "LevelScript" in type_name or "LevelScript" in method_name:
        result.add("level_script")
    if any(token in type_name or token in method_name for token in (
        "Dialog", "Radio", "Cinematic", "Cutscene",
    )):
        result.add("story")
    return result


def admissible_pointer_aliases(aliases: Iterable[dict[str, Any]]) -> bool:
    rows = list(aliases)
    families = {family for row in rows for family in api_families(row)}
    return (
        bool(rows)
        and len(rows) <= MAX_POINTER_ALIASES
        and len(families) <= 1
        and any(str(row.get("type") or "").startswith("Beyond.Gameplay") for row in rows)
    )


def classify_candidate(families: Iterable[str], target_symbols: Iterable[str]) -> str:
    """Classify a cross-family caller by API behavior; unknown shapes fail closed."""
    family_set = frozenset(families)
    symbols = tuple(target_symbols)
    joined = "\n".join(symbols)
    if family_set == {"dynamic_scene", "mission_system"}:
        if ("MissionSystem.GetMissionState" in joined or "MissionSystem.GetQuestState" in joined):
            return "mission_state_controls_dynamic_component_availability"
    elif family_set == {"dynamic_scene", "level_script"}:
        if "DynamicStreamingScene.WaitIdle" in joined and "LevelScriptManager." in joined:
            return "global_level_load_synchronization"
        geometry_tokens = (
            "get_position", "get_rotation", "get_scale", "get_shapeOffset",
            "get_shapeSize", "get_shapeType",
        )
        if symbols and all(any(token in symbol for token in geometry_tokens) for symbol in symbols):
            return "shared_trigger_geometry_adapter"
    elif family_set == {"dynamic_scene", "story"}:
        dynamic_visual = any(token in joined for token in (
            "SetOverrideEnable", "RemoveOverride", "RefreshEntity", "ReleaseEntity",
            "GetEntity", "get_entitySys", "get_view",
        ))
        story_visual = any(token in joined for token in (
            "Dialog", "Cinematic", "Decoration", "Actor", "HideSceneObject",
            "SceneRecover", "InteractiveVisibility",
        ))
        if dynamic_visual and story_visual:
            return "story_dynamic_scene_visual_context"
    elif family_set == {"mission_system", "story"}:
        if "MissionSystem.AcceptMission" in joined and "StopAndPlayDialogById" in joined:
            return "mission_or_dialog_alternate_action_consumer"
    return "unreviewed_cross_system_call_shape"


def validate_counts(rows: list[dict[str, Any]], source_file: str) -> list[dict[str, Any]]:
    actual = Counter(str(row.get("classification") or "") for row in rows)
    failures: list[dict[str, Any]] = []
    for classification, expected in EXPECTED_CLASS_COUNTS.items():
        observed = actual.get(classification, 0)
        if observed != expected:
            failures.append({
                "validator": "nativeCrossSystemConsumerCensus",
                "gate": "expectedClassificationCount",
                "classification": classification,
                "expected": expected,
                "actual": observed,
                "sourceFile": source_file,
            })
    unknown = actual.get("unreviewed_cross_system_call_shape", 0)
    if unknown:
        failures.append({
            "validator": "nativeCrossSystemConsumerCensus",
            "gate": "allCrossSystemCallShapesReviewed",
            "expected": 0,
            "actual": unknown,
            "sourceFile": source_file,
        })
    expected_total = sum(EXPECTED_CLASS_COUNTS.values())
    if len(rows) != expected_total:
        failures.append({
            "validator": "nativeCrossSystemConsumerCensus",
            "gate": "expectedCrossSystemCallerCount",
            "expected": expected_total,
            "actual": len(rows),
            "sourceFile": source_file,
        })
    return failures


def build_report(gameassembly: Path, metadata_path: Path) -> dict[str, Any]:
    if not gameassembly.is_file() or not metadata_path.is_file():
        raise AuditError(f"missing original binary input: {gameassembly} / {metadata_path}")
    game_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata_path)
    if game_hash != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise AuditError(
            "GameAssembly hash changed; expected "
            f"{EXPECTED_GAME_ASSEMBLY_SHA256}, actual {game_hash}; revalidate family rules"
        )
    if metadata_hash != EXPECTED_METADATA_SHA256:
        raise AuditError(
            "global metadata hash changed; expected "
            f"{EXPECTED_METADATA_SHA256}, actual {metadata_hash}; revalidate method mapping"
        )

    mapper = load_module("native_cross_system_mapper", MAPPER_PATH)
    catalog = load_module("native_cross_system_catalog", CATALOG_PATH)
    metadata = catalog.Metadata(metadata_path)
    pe = mapper.PeImage(gameassembly)
    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    _pointers_by_image, methods_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    registration = mapper.find_metadata_registration(pe, mapper.DEFAULT_CODE_REGISTRATION)
    if registration is None:
        raise AuditError("could not derive MetadataRegistration from current GameAssembly")
    generic = mapper.build_generic_method_index(
        pe, metadata, mapper.DEFAULT_CODE_REGISTRATION, registration
    )
    for pointer, aliases in generic.items():
        methods_by_pointer.setdefault(pointer, aliases)

    method_pointers = sorted(methods_by_pointer)
    family_by_pointer: dict[int, tuple[str, ...]] = {}
    for pointer, aliases in methods_by_pointer.items():
        families = tuple(sorted({family for row in aliases for family in api_families(row)}))
        if len(families) == 1 and admissible_pointer_aliases(aliases):
            family_by_pointer[pointer] = families

    calls_by_caller: dict[int, list[dict[str, Any]]] = defaultdict(list)
    family_call_counts: Counter[str] = Counter()
    section_call_candidates: Counter[str] = Counter()
    for section in pe.sections:
        section_name = str(section["name"])
        if section_name not in {".text", "il2cpp"}:
            continue
        data = pe.buf[section["rawPointer"]:section["rawPointer"] + section["rawSize"]]
        position = data.find(b"\xe8")
        while position >= 0:
            if position + 5 <= len(data):
                section_call_candidates[section_name] += 1
                call_va = pe.image_base + section["virtualAddress"] + position
                relative = struct.unpack_from("<i", data, position + 1)[0]
                target_va = call_va + 5 + relative
                families = family_by_pointer.get(target_va)
                if families:
                    caller_pos = bisect.bisect_right(method_pointers, call_va) - 1
                    if caller_pos >= 0:
                        caller_va = method_pointers[caller_pos]
                        next_va = (
                            method_pointers[caller_pos + 1]
                            if caller_pos + 1 < len(method_pointers)
                            else caller_va + 0x10000
                        )
                        if call_va < min(next_va, caller_va + 0x10000):
                            targets = methods_by_pointer[target_va]
                            calls_by_caller[caller_va].append({
                                "callVa": f"0x{call_va:x}",
                                "targetVa": f"0x{target_va:x}",
                                "families": list(families),
                                "targets": sorted({method_symbol(row) for row in targets}),
                            })
                            family_call_counts.update(families)
            position = data.find(b"\xe8", position + 1)

    rows: list[dict[str, Any]] = []
    for caller_va, calls in calls_by_caller.items():
        families = sorted({family for call in calls for family in call["families"]})
        family_set = set(families)
        relevant = (
            "mission_system" in family_set and len(family_set) >= 2
        ) or (
            "dynamic_scene" in family_set
            and bool({"level_script", "story"} & family_set)
        )
        aliases = methods_by_pointer[caller_va]
        if not relevant or not admissible_pointer_aliases(aliases):
            continue
        target_symbols = sorted({symbol for call in calls for symbol in call["targets"]})
        rows.append({
            "callerVa": f"0x{caller_va:x}",
            "callers": sorted({method_symbol(alias) for alias in aliases}),
            "families": families,
            "classification": classify_candidate(families, target_symbols),
            "targets": target_symbols,
            "callSites": calls,
        })
    rows.sort(key=lambda row: (row["families"], row["callerVa"]))

    failures = validate_counts(rows, source_path(gameassembly))
    if failures:
        first = failures[0]
        raise AuditError(
            f"{first['validator']} failed {first['gate']} for "
            f"{first.get('classification', 'all callers')}: expected "
            f"{first['expected']}, actual {first['actual']}; source={first['sourceFile']}"
        )
    class_counts = Counter(row["classification"] for row in rows)
    family_sets = Counter("+".join(row["families"]) for row in rows)
    return {
        "schemaVersion": "nativeCrossSystemConsumerCensus.v1",
        "source": {
            "gameAssembly": source_path(gameassembly),
            "gameAssemblySha256": game_hash,
            "globalMetadata": source_path(metadata_path),
            "globalMetadataSha256": metadata_hash,
            "sections": [".text", "il2cpp"],
        },
        "method": {
            "selection": "all direct E8 rel32 calls to unambiguous current managed API-family pointers",
            "idSeeds": 0,
            "maximumPointerAliases": MAX_POINTER_ALIASES,
            "mappedMethodPointers": len(methods_by_pointer),
            "familyTargetPointers": len(family_by_pointer),
            "rawCallOpcodeCandidatesBySection": dict(sorted(section_call_candidates.items())),
            "mappedFamilyCalls": dict(sorted(family_call_counts.items())),
        },
        "summary": {
            "crossSystemCallers": len(rows),
            "classificationCounts": dict(sorted(class_counts.items())),
            "familyCombinationCounts": dict(sorted(family_sets.items())),
            "missionLevelScriptCallers": sum(
                set(row["families"]) == {"mission_system", "level_script"} for row in rows
            ),
            "tripleOrGreaterFamilyCallers": sum(len(row["families"]) >= 3 for row in rows),
            "unreviewedCallers": class_counts.get("unreviewed_cross_system_call_shape", 0),
            "storyBindingsAdded": 0,
            "missionOrderEdgesAdded": 0,
        },
        "rows": rows,
        "finding": (
            "The current binary exposes mission-state consumers for DynamicScene component "
            "availability, but no direct MissionSystem/LevelScript caller and no caller that "
            "joins mission state, DynamicScene, and Story or LevelScript. Other cross-system "
            "callers are shared geometry, global loading, or Story visual context."
        ),
        "boundary": (
            "Direct mapped calls only: virtual/interface dispatch, reflection, XLua, server-only "
            "logic, runtime-created delegates, and future builds remain outside this census. "
            "The MissionOption mission/dialog row relies on its separate pinned control-flow "
            "audit before interpreting the two calls as alternate actions."
        ),
        "validation": {"status": "passed", "failures": []},
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Native Cross-System Consumer Census",
        "",
        f"- Cross-system callers: **{summary['crossSystemCallers']}**",
        f"- Mission + LevelScript callers: **{summary['missionLevelScriptCallers']}**",
        f"- Three-or-more-family callers: **{summary['tripleOrGreaterFamilyCallers']}**",
        f"- Unreviewed callers: **{summary['unreviewedCallers']}**",
        f"- GameAssembly SHA-256: `{report['source']['gameAssemblySha256']}`",
        f"- Metadata SHA-256: `{report['source']['globalMetadataSha256']}`",
        "",
        report["finding"],
        "",
        "## Classification counts",
        "",
    ]
    for key, value in summary["classificationCounts"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Callers", ""])
    for row in report["rows"]:
        lines.append(
            f"- `{row['callerVa']}` `{row['classification']}`: "
            + ", ".join(f"`{caller}`" for caller in row["callers"])
        )
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(args.gameassembly, args.metadata)
    except AuditError as exc:
        print(f"native cross-system consumer census failed: {exc}", file=sys.stderr)
        return 1
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(report), encoding="utf-8")
    print(
        "Native cross-system consumer census passed: "
        f"{report['summary']['crossSystemCallers']} callers, "
        f"{report['summary']['unreviewedCallers']} unreviewed, "
        f"{report['summary']['missionOrderEdgesAdded']} order edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
