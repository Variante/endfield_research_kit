#!/usr/bin/env python3
"""Census nested managed mission/quest and Story/runtime identity carriers.

The direct managed-field census deliberately stops at one object.  This audit
uses the installed MetadataRegistration runtime type table to resolve generic
container arguments and follows custom managed fields to depth three.  Every
candidate is then assigned to an already recovered context, a bounded negative,
an aggregate runtime manager, or a non-carrier registry/catalog.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import re
import struct
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import md_escape, write_report_json, write_text_if_changed  # noqa: E402


METADATA_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
)
MAPPER_HELPER = (
    ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
)
PROTOCOL_AUDIT = (
    ROOT / "scripts" / "story_recovery" / "build_protocol_registry_audit.py"
)
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_IFIX_AUDIT = (
    ROOT / "reports" / "story" / "recovery" / "current_ifix_mission_graph_audit.json"
)
DEFAULT_OUT = (
    ROOT / "reports" / "story" / "recovery"
    / "nested_managed_identity_carrier_census.json"
)
DEFAULT_MARKDOWN = (
    ROOT / "reports" / "story" / "recovery"
    / "nested_managed_identity_carrier_census.md"
)

EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_IFIX_SHA256 = (
    "737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21"
)
MAX_DEPTH = 3


CLASSIFICATIONS = {
    "Beyond.Gameplay.Actions.ParamSource": (
        "closed_implicit_current_mission_context",
        "CURRENT_MISSION_ID is absent from LevelScripts and occurs only in "
        "already-owned MissionRuntime self-property checks.",
    ),
    "Beyond.Gameplay.AirWallManager": (
        "recovered_airwall_state_gated_context",
        "Exact AirWall group mission checks, script identity, and pushback radio "
        "playback are already represented as bounded non-owning context.",
    ),
    "Beyond.Gameplay.AirWallManager+<>c__DisplayClass104_0": (
        "recovered_airwall_state_gated_context",
        "The closure carries the selected pushback radio for the already recovered "
        "AirWall manager route; it adds no second ownership relation.",
    ),
    "Beyond.Gameplay.CheckLevelScriptTaskFinished": (
        "closed_objective_progress_callback",
        "The nested parentQuestId belongs to a task condition; the proven callback "
        "updates MissionSystem objective progress and does not play Story.",
    ),
    "Beyond.Gameplay.Core.DialogManager": (
        "closed_inactive_pending_item_submitter",
        "The pending item submitter could forward questId with dialog finish, but "
        "the installed fallback has no constructor or registration caller.",
    ),
    "Beyond.Gameplay.Core.DialogManager+<>c__DisplayClass674_0": (
        "closed_global_dialog_manager_closure",
        "The closure's current dialog id reaches the global DialogManager; unrelated "
        "manager caches do not become quest ownership.",
    ),
    "Beyond.Gameplay.Core.FocusGameMode": (
        "recovered_focus_mode_context",
        "The nested FocusModeInstanceData mission/radio pair is already emitted as "
        "non-owning focus-mode interaction context.",
    ),
    "Beyond.Gameplay.Core.FocusModeInstanceData": (
        "recovered_focus_mode_context",
        "Thirteen authored mission/radio rows are already represented with their "
        "bounded focus-mode semantics.",
    ),
    "Beyond.Gameplay.Core.NpcRuntimeProxyData": (
        "recovered_npc_proxy_context",
        "NpcProxyEx mission/dialog rows and the one exact lazy-destroy tracking "
        "context are already represented without promoting server-selected state.",
    ),
    "Beyond.Gameplay.Core.NpcRuntimeProxyExData": (
        "recovered_npc_proxy_context",
        "The mission and dialog fields have separate native consumers; authored "
        "non-empty mission rows are already represented on their mission shell.",
    ),
    "Beyond.Gameplay.Core.SubGameInstanceData": (
        "recovered_subgame_runtime_shell",
        "Twenty dungeonMissionId/bindScriptId rows are already represented as "
        "SubGame runtime shells with zero inferred Story edge.",
    ),
    "Beyond.Gameplay.DataManager": (
        "closed_global_table_registry",
        "DataManager holds independent global tables; a dialog table and a nested "
        "mission-bearing config table do not identify the same authored record.",
    ),
    "Beyond.Gameplay.DomainDepotSystem": (
        "recovered_domain_depot_context",
        "The exact f1m25 delivery-table and target-dialog route is already recovered; "
        "the system-wide wait dialog and nested unlock rows add no new owner.",
    ),
    "Beyond.Gameplay.LevelFunctionAreaData+RadioTriggerZoneData": (
        "recovered_radio_trigger_zone_context",
        "Four exact LevelData radio rows and their hide-before/after/complete mission "
        "roles are already represented as non-owning state/playback context.",
    ),
    "Beyond.Gameplay.LevelScriptData": (
        "closed_level_aggregate",
        "LevelScriptData aggregates many independent level subsystems; nested quest "
        "locks and NPC dialogs are not co-record ownership.",
    ),
    "Beyond.Gameplay.MissionOptionData": (
        "closed_mutually_exclusive_actions",
        "missionId and callDialogId select mutually exclusive native action branches, "
        "and the current authored-instance census is empty.",
    ),
    "Beyond.Gameplay.MissionRuntimeAsset": (
        "closed_mission_property_script_pointer",
        "The apparent propertyDic to ParamVariable.m_scriptPtr path has no authored "
        "script pointer and no native mission-to-LevelScript writer.",
    ),
    "Beyond.Gameplay.MissionSystem": (
        "closed_global_mission_manager",
        "MissionSystem combines mission state, HUD tracking, and synchronized "
        "properties; its nested caches are separate runtime concerns.",
    ),
    "Beyond.Gameplay.MissionSystem+<>c__DisplayClass70_0": (
        "closed_global_mission_manager_closure",
        "The closure captures a quest id while retaining the whole MissionSystem; "
        "the global SNS tracking cache is not that quest's Story owner.",
    ),
    "Beyond.Gameplay.MissionSystem+<>c__DisplayClass78_0": (
        "closed_global_mission_manager_closure",
        "The closure captures a mission id while retaining the whole MissionSystem; "
        "the global SNS tracking cache supplies HUD context only.",
    ),
    "Beyond.Gameplay.MissionSystem+MissionData": (
        "closed_mission_property_script_pointer",
        "The synchronized propertyDict uses ParamVariable values but no audited "
        "writer attaches it to a LevelScript.",
    ),
    "Beyond.Gameplay.TeleportParam": (
        "closed_unused_mission_field",
        "Current producers do not co-populate missionId and levelScriptId, and "
        "audited consumers do not read missionId.",
    ),
    "Beyond.IdPickerAttribute+StringIdType": (
        "not_a_carrier_enum",
        "The names are editor picker alternatives, not values resident on one "
        "serialized or runtime object.",
    ),
    "Beyond.MemoryPack.MemoryPackDeSerializerRegister": (
        "not_a_carrier_formatter_registry",
        "The fields are independent static formatter initialization flags, not "
        "mission/Story identity values.",
    ),
    "Beyond.PropertyKeys": (
        "not_a_carrier_static_key_catalog",
        "The fields are independent global property-key constants, not values "
        "resident on one object.",
    ),
}

ITEM_SUBMITTER_TARGETS = {
    "InventoryItemSubmitter..ctor": {
        "methodIndex": 20718,
        "token": "0x060050ef",
        "address": "0x1873b0234",
    },
    "InventoryItemSubmitter.TryGetSubmitMsg": {
        "methodIndex": 20719,
        "token": "0x060050f0",
        "address": "0x1873b0144",
    },
    "DialogManager.RegisterPendingSubmission": {
        "methodIndex": 63357,
        "token": "0x0600f77e",
        "address": "0x186e17bc8",
    },
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
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


def scan_direct_callers(
    pe: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    method_pointers: list[int],
    targets: dict[int, str],
) -> dict[str, list[dict[str, Any]]]:
    callers = {name: [] for name in targets.values()}
    for section in pe.sections:
        if section["name"] not in {".text", "il2cpp"} or not section["rawSize"]:
            continue
        data = pe.buf[
            section["rawPointer"]:section["rawPointer"] + section["rawSize"]
        ]
        position = data.find(b"\xe8")
        while position >= 0:
            if position + 5 <= len(data):
                call_va = pe.image_base + section["virtualAddress"] + position
                relative = struct.unpack_from("<i", data, position + 1)[0]
                target_name = targets.get(call_va + 5 + relative)
                if target_name is not None:
                    pointer_pos = bisect.bisect_right(method_pointers, call_va) - 1
                    method_pointer = (
                        method_pointers[pointer_pos] if pointer_pos >= 0 else None
                    )
                    callers[target_name].append({
                        "callAddress": f"0x{call_va:x}",
                        "callerAddress": (
                            f"0x{method_pointer:x}"
                            if method_pointer is not None
                            else None
                        ),
                        "resolved": method_by_pointer.get(method_pointer, []),
                    })
            position = data.find(b"\xe8", position + 1)
    return callers


def build_report(
    *,
    game_assembly: Path,
    metadata_path: Path,
    ifix_audit_path: Path,
) -> dict[str, Any]:
    metadata_module = load_module("nested_carrier_metadata", METADATA_HELPER)
    mapper = load_module("nested_carrier_mapper", MAPPER_HELPER)
    protocol = load_module("nested_carrier_protocol", PROTOCOL_AUDIT)
    metadata = metadata_module.Metadata(metadata_path)
    pe = mapper.PeImage(game_assembly)
    metadata_registration = mapper.find_metadata_registration(
        pe, mapper.DEFAULT_CODE_REGISTRATION
    )
    if metadata_registration is None:
        raise RuntimeError("could not derive MetadataRegistration")
    registration = mapper.metadata_registration_summary(pe, metadata_registration)
    runtime_types_va = int(registration["types"], 16)
    runtime_type_count = int(registration["typesCount"])

    type_names = {
        metadata.type_full_name(type_def): type_def
        for type_def in metadata.types
    }
    custom_type_names = {
        name
        for name in type_names
        if not name.startswith((
            "System.",
            "Microsoft.",
            "Google.",
            "UnityEngine.",
            "Unity.",
            "Proto.",
        ))
    }
    token_re = re.compile(r"[A-Za-z_][A-Za-z0-9_.+`]*")

    @lru_cache(maxsize=None)
    def runtime_field_type(type_index: int) -> str:
        if not 0 <= type_index < runtime_type_count:
            return f"<type-index:{type_index}>"
        type_va = pe.u64_at_va(runtime_types_va + type_index * 8)
        return protocol.runtime_type_name(pe, metadata, type_va)

    @lru_cache(maxsize=None)
    def dependencies(runtime_name: str) -> tuple[str, ...]:
        return tuple(sorted({
            token
            for token in token_re.findall(runtime_name)
            if token in custom_type_names
        }))

    fields_by_type: dict[str, list[dict[str, Any]]] = {}
    for type_name, type_def in type_names.items():
        if type_name.startswith("Proto."):
            continue
        fields_by_type[type_name] = [{
            "name": metadata.string(field.name_index),
            "token": f"0x{field.token:08x}",
            "runtimeType": runtime_field_type(field.type_index),
            "dependencies": list(dependencies(runtime_field_type(field.type_index))),
            "classes": sorted(
                protocol.protobuf_identity_field_classes(
                    metadata.string(field.name_index)
                )
            ),
        } for field in metadata.fields_for(type_def)]

    @lru_cache(maxsize=None)
    def evidence(
        type_name: str,
        identity_class: str,
        depth: int,
        trail: tuple[str, ...] = (),
    ) -> tuple[tuple[dict[str, Any], ...], bool]:
        if type_name in trail:
            return (), False
        found: list[dict[str, Any]] = []
        direct = False
        for field in fields_by_type.get(type_name, []):
            if identity_class in field["classes"]:
                direct = True
                found.append({
                    "path": f"{type_name}.{field['name']}",
                    "ownerType": type_name,
                    "field": field["name"],
                    "runtimeType": field["runtimeType"],
                    "depth": 0,
                })
            if depth <= 0:
                continue
            for dependency in field["dependencies"]:
                child_rows, _ = evidence(
                    dependency,
                    identity_class,
                    depth - 1,
                    (*trail, type_name),
                )
                for child in child_rows:
                    found.append({
                        **child,
                        "path": f"{type_name}.{field['name']} -> {child['path']}",
                        "depth": child["depth"] + 1,
                    })
        unique = {
            (row["path"], row["ownerType"], row["field"]): row
            for row in found
        }
        return tuple(unique.values()), direct

    candidates = []
    for type_name in sorted(fields_by_type):
        mission, mission_direct = evidence(
            type_name, "mission_or_quest", MAX_DEPTH
        )
        level_script, level_script_direct = evidence(
            type_name, "level_script", MAX_DEPTH
        )
        story, story_direct = evidence(type_name, "story", MAX_DEPTH)
        if not mission or not (level_script or story):
            continue
        if not (mission_direct or level_script_direct or story_direct):
            continue
        status, finding = CLASSIFICATIONS.get(
            type_name,
            ("unreviewed", "No current classification."),
        )
        candidates.append({
            "type": type_name,
            "image": metadata.image_name_by_type_index.get(
                type_names[type_name].index, ""
            ),
            "directClasses": sorted(
                identity_class
                for identity_class, present in (
                    ("mission_or_quest", mission_direct),
                    ("level_script", level_script_direct),
                    ("story", story_direct),
                )
                if present
            ),
            "minimumDepth": {
                "mission_or_quest": min(row["depth"] for row in mission),
                "level_script": (
                    min(row["depth"] for row in level_script)
                    if level_script
                    else None
                ),
                "story": (
                    min(row["depth"] for row in story)
                    if story
                    else None
                ),
            },
            "representativePaths": {
                "mission_or_quest": min(
                    mission, key=lambda row: (row["depth"], row["path"])
                )["path"],
                "level_script": (
                    min(
                        level_script,
                        key=lambda row: (row["depth"], row["path"]),
                    )["path"]
                    if level_script
                    else None
                ),
                "story": (
                    min(story, key=lambda row: (row["depth"], row["path"]))[
                        "path"
                    ]
                    if story
                    else None
                ),
            },
            "status": status,
            "finding": finding,
        })

    modules = mapper.parse_codegen_modules(pe, mapper.DEFAULT_CODE_REGISTRATION)
    ranges = mapper.image_method_ranges(metadata)
    pointers_by_image, method_by_pointer = mapper.build_pointer_indexes(
        pe, metadata, modules, ranges
    )
    generic_index = mapper.build_generic_method_index(
        pe,
        metadata,
        mapper.DEFAULT_CODE_REGISTRATION,
        metadata_registration,
    )
    for pointer, rows in generic_index.items():
        method_by_pointer.setdefault(pointer, rows)
    method_pointers = sorted(
        set(method_by_pointer)
        | {
            pointer
            for pointers in pointers_by_image.values()
            for pointer in pointers
            if pointer
        }
    )
    target_by_va = {
        int(row["address"], 16): name
        for name, row in ITEM_SUBMITTER_TARGETS.items()
    }
    direct_callers = scan_direct_callers(
        pe, method_by_pointer, method_pointers, target_by_va
    )
    ifix_audit = json.loads(ifix_audit_path.read_text(encoding="utf-8"))
    fixed_signatures = [
        str(row.get("signature") or "")
        for row in ifix_audit.get("fixedMethods", [])
    ]
    submitter_ifix_matches = [
        signature
        for signature in fixed_signatures
        if "InventoryItemSubmitter" in signature
        or "RegisterPendingSubmission" in signature
        or "SendFinishDialog" in signature
    ]

    candidate_types = {row["type"] for row in candidates}
    expected_types = set(CLASSIFICATIONS)
    unreviewed = [
        row["type"] for row in candidates if row["status"] == "unreviewed"
    ]
    errors = []
    if candidate_types != expected_types:
        errors.append(
            "candidate type set changed: "
            f"missing={sorted(expected_types - candidate_types)} "
            f"added={sorted(candidate_types - expected_types)}"
        )
    if unreviewed:
        errors.append(f"unreviewed candidates: {unreviewed}")
    expected_caller_counts = {
        "InventoryItemSubmitter..ctor": 0,
        "InventoryItemSubmitter.TryGetSubmitMsg": 1,
        "DialogManager.RegisterPendingSubmission": 0,
    }
    caller_counts = {
        name: len(direct_callers[name]) for name in ITEM_SUBMITTER_TARGETS
    }
    if caller_counts != expected_caller_counts:
        errors.append(
            f"item submitter direct caller counts changed: {caller_counts}"
        )
    game_sha = sha256_file(game_assembly)
    metadata_sha = sha256_file(metadata_path)
    ifix_sha = str(ifix_audit.get("source", {}).get("patchSha256") or "")
    if game_sha != EXPECTED_GAME_ASSEMBLY_SHA256:
        errors.append("GameAssembly SHA256 changed")
    if metadata_sha != EXPECTED_METADATA_SHA256:
        errors.append("global-metadata SHA256 changed")
    if ifix_sha != EXPECTED_IFIX_SHA256:
        errors.append("IFix SHA256 changed")
    if submitter_ifix_matches:
        errors.append(
            f"item submitter IFix targets appeared: {submitter_ifix_matches}"
        )

    direct_exact_count = sum(
        "mission_or_quest" in row["directClasses"]
        and (
            "level_script" in row["directClasses"]
            or "story" in row["directClasses"]
        )
        for row in candidates
    )
    return {
        "schemaVersion": 1,
        "source": {
            "gameAssembly": str(game_assembly.resolve()),
            "gameAssemblySha256": game_sha,
            "metadata": str(metadata_path.resolve()),
            "metadataSha256": metadata_sha,
            "codeRegistration": f"0x{mapper.DEFAULT_CODE_REGISTRATION:x}",
            "metadataRegistration": f"0x{metadata_registration:x}",
            "runtimeTypesTable": f"0x{runtime_types_va:x}",
            "runtimeTypeCount": runtime_type_count,
            "ifixAudit": str(ifix_audit_path.resolve()),
            "ifixSha256": ifix_sha,
        },
        "census": {
            "maxDepth": MAX_DEPTH,
            "metadataTypeRecords": len(metadata.types),
            "uniqueTypeDefinitions": len(type_names),
            "customTypeDefinitions": len(custom_type_names),
            "candidateTypes": len(candidates),
            "directExactCandidateTypes": direct_exact_count,
            "nestedDependentCandidateTypes": len(candidates) - direct_exact_count,
            "reviewedCandidateTypes": len(candidates) - len(unreviewed),
            "unreviewedCandidateTypes": len(unreviewed),
            "classificationCounts": dict(sorted(
                Counter(row["status"] for row in candidates).items()
            )),
        },
        "candidates": candidates,
        "pendingItemSubmitterClosure": {
            "managedLayout": {
                "DialogManager.m_pendingItemSubmitter": {
                    "token": "0x0400b304",
                    "offset": "0x200",
                },
                "InventoryItemSubmitter.scope": {
                    "token": "0x04004754",
                    "offset": "0x10",
                },
                "InventoryItemSubmitter.chapterId": {
                    "token": "0x04004755",
                    "offset": "0x14",
                },
                "InventoryItemSubmitter.submitId": {
                    "token": "0x04004758",
                    "offset": "0x18",
                },
                "InventoryItemSubmitter.questId": {
                    "token": "0x04004759",
                    "offset": "0x20",
                },
                "InventoryItemSubmitter.objId": {
                    "token": "0x0400475a",
                    "offset": "0x28",
                },
            },
            "methods": {
                name: {
                    **row,
                    "directCallerCount": caller_counts[name],
                    "directCallers": direct_callers[name],
                }
                for name, row in ITEM_SUBMITTER_TARGETS.items()
            },
            "sendFinishDialog": {
                "symbol": "Beyond.Gameplay.CinematicSystem.SendFinishDialog",
                "token": "0x06004027",
                "address": "0x1872f0d88",
                "finding": (
                    "DialogManager._SendServer passes the current dialog id and "
                    "m_pendingItemSubmitter. SendFinishDialog is the sole direct "
                    "caller of TryGetSubmitMsg."
                ),
            },
            "installedPatchMatches": submitter_ifix_matches,
            "classification": "inactive_current_fallback_producer",
            "finding": (
                "The object shape could carry questId into a dialog-finish item "
                "submission, but the installed fallback has zero direct callers of "
                "both InventoryItemSubmitter..ctor and "
                "DialogManager.RegisterPendingSubmission. The sole "
                "TryGetSubmitMsg caller is SendFinishDialog, and the current IFix "
                "replaces none of the path."
            ),
        },
        "finding": (
            "All 25 current managed identity candidates reachable through generic "
            "or custom typed fields to depth three are reviewed. Productive AirWall, "
            "FocusMode, NpcProxy, SubGame, DomainDepot, and RadioTriggerZone contexts "
            "were already recovered; the remaining nested joins are inactive "
            "producers, global aggregate managers, previously closed property/task "
            "paths, or static registries rather than new mission graph edges."
        ),
        "boundary": (
            "Reflection/XLua construction, native-only opaque objects, server-only "
            "state, paths deeper than three custom-type hops, unexported asset kinds, "
            "future IFix, and future builds remain outside the bound."
        ),
        "classification": "all_nested_managed_identity_carriers_reviewed",
        "storyBindingsAdded": 0,
        "missionOrderEdgesAdded": 0,
        "validationErrors": errors,
        "valid": not errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    census = report["census"]
    closure = report["pendingItemSubmitterClosure"]
    lines = [
        "# Nested managed identity carrier census",
        "",
        f"- Valid: `{report['valid']}`",
        f"- Metadata type records: `{census['metadataTypeRecords']}`",
        f"- Runtime type entries: `{report['source']['runtimeTypeCount']}`",
        f"- Candidate types: `{census['candidateTypes']}`",
        f"- Direct exact candidates: `{census['directExactCandidateTypes']}`",
        f"- Nested-dependent candidates: `{census['nestedDependentCandidateTypes']}`",
        f"- Unreviewed candidates: `{census['unreviewedCandidateTypes']}`",
        f"- Story bindings added: `{report['storyBindingsAdded']}`",
        f"- Mission-order edges added: `{report['missionOrderEdgesAdded']}`",
        "",
        "## Pending item submitter closure",
        "",
        closure["finding"],
        "",
        "| Method | Token | Address | Direct callers |",
        "| --- | --- | --- | ---: |",
    ]
    for name, row in closure["methods"].items():
        lines.append(
            f"| `{md_escape(name)}` | `{row['token']}` | `{row['address']}` | "
            f"{row['directCallerCount']} |"
        )
    lines.extend([
        "",
        "## Candidate classifications",
        "",
        "| Type | Direct classes | Minimum depth M/L/S | Status |",
        "| --- | --- | --- | --- |",
    ])
    for row in report["candidates"]:
        depth = row["minimumDepth"]
        depths = "/".join(
            "-" if depth[key] is None else str(depth[key])
            for key in ("mission_or_quest", "level_script", "story")
        )
        lines.append(
            f"| `{md_escape(row['type'])}` | "
            f"`{md_escape(', '.join(row['directClasses']))}` | `{depths}` | "
            f"`{md_escape(row['status'])}` |"
        )
    lines.extend([
        "",
        "## Finding",
        "",
        report["finding"],
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
    ])
    if report["validationErrors"]:
        lines.extend([
            "## Validation errors",
            "",
            *[f"- {error}" for error in report["validationErrors"]],
            "",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--ifix-audit", type=Path, default=DEFAULT_IFIX_AUDIT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    report = build_report(
        game_assembly=args.gameassembly,
        metadata_path=args.metadata,
        ifix_audit_path=args.ifix_audit,
    )
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(
        "nested managed identity carrier census: "
        f"{report['census']['candidateTypes']} candidates, "
        f"{report['census']['nestedDependentCandidateTypes']} nested-dependent, "
        f"{report['census']['unreviewedCandidateTypes']} unreviewed, "
        f"valid={report['valid']}"
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
