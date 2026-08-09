#!/usr/bin/env python3
"""Recover Timeline-embedded Story presentation from general runtime shape.

The audit discovers serialized text-carrying PlayableAsset families from the
installed IL2CPP metadata, validates their common CreatePlayable/localization
call chain in the installed GameAssembly, and then scans exported Timeline
objects by exact PathID references. It contains no Story-key, mission, dialog,
Timeline, CAB, or PathID allowlist.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "endfield-il2cpp"
for import_root in (ROOT, ROOT / "scripts"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_METADATA = (
    Path(r"D:\Program Files\Endfield Game\Endfield_Data")
    / "il2cpp_data" / "Metadata" / "global-metadata.dat"
)
DEFAULT_STORY_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
DEFAULT_OUTPUT_ROOT = ROOT / "export_full"
DEFAULT_EXTRACT_DIR = (
    DEFAULT_OUTPUT_ROOT / "recovered" / "AnimeStudio-cli" / "timeline_extract"
)
DEFAULT_GAME_ROOT = Path(
    os.environ.get(
        "ENDFIELD_GAME_ROOT",
        r"D:\Program Files\Endfield Game\Endfield_Data",
    )
)
DEFAULT_ANIMESTUDIO_CLI = (
    ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin"
    / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"
)
DEFAULT_JSON = (
    ROOT / "reports" / "story" / "recovery"
    / "timeline_embedded_story_runtime_audit.json"
)
DEFAULT_MD = DEFAULT_JSON.with_suffix(".md")


def _story_recovery_modules() -> tuple[Any, Any, Any]:
    """Load the shared native topology and LevelData host recoveries lazily.

    Keeping these imports lazy avoids making the Timeline object scanner own a
    second copy of either parser.  Both helpers are corpus-driven and validate
    current serialized shapes; no dialog, mission, level, or script identifiers
    are declared here.
    """
    try:
        from scripts.story_builder import context as story_context
        from scripts.story_builder import level_bindings
        from scripts.story_recovery import build_levelscript_header_chain_audit
    except ModuleNotFoundError:
        from story_builder import context as story_context
        from story_builder import level_bindings
        from story_recovery import build_levelscript_header_chain_audit
    return story_context, level_bindings, build_levelscript_header_chain_audit


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolved_targets(row: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(target.get("type") or ""), str(target.get("method") or ""))
        for call in row.get("directCalls") or []
        for target in call.get("resolved") or []
    }


def validation_failure(
    gate: str,
    expected: Any,
    actual: Any,
    source: str,
) -> dict[str, Any]:
    return {
        "validator": "timeline_embedded_story_runtime",
        "gate": gate,
        "sourceFile": source,
        "expected": expected,
        "actual": actual,
    }


def analyze_runtime_contract(
    catalog: dict[str, Any],
    body_map: dict[str, Any],
) -> dict[str, Any]:
    """Find all text PlayableAsset families by fields/methods/call shape."""
    body_rows = body_map.get("bodyTargets") or []
    body_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in body_rows:
        body_by_key[(str(row.get("type") or ""), str(row.get("method") or ""))].append(row)

    candidates = []
    for row in catalog.get("matchedTypes") or []:
        full_name = str(row.get("fullName") or "")
        if not full_name.endswith("PlayableAsset"):
            continue
        fields = sorted({
            str(field.get("name") or "")
            for field in row.get("fields") or []
            if re.fullmatch(r"_textId(?:_\d+)?", str(field.get("name") or ""))
        })
        methods = {str(method.get("name") or "") for method in row.get("methods") or []}
        if fields and {"CreatePlayable", "_GetText"}.issubset(methods):
            candidates.append((row, fields))

    failures: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    if not candidates:
        failures.append(validation_failure(
            "structural_type_discovery",
            "one_or_more PlayableAsset types with _textId field(s), CreatePlayable, and _GetText",
            0,
            "global-metadata.dat",
        ))

    for type_row, text_fields in sorted(candidates, key=lambda item: item[0]["fullName"]):
        full_name = str(type_row["fullName"])
        create_rows = body_by_key.get((full_name, "CreatePlayable"), [])
        get_text_rows = body_by_key.get((full_name, "_GetText"), [])
        if len(create_rows) != 1 or create_rows[0].get("mappingStatus") != "mapped":
            failures.append(validation_failure(
                "create_playable_body",
                "one mapped CreatePlayable",
                len([row for row in create_rows if row.get("mappingStatus") == "mapped"]),
                full_name,
            ))
            continue
        if len(get_text_rows) != 1 or get_text_rows[0].get("mappingStatus") != "mapped":
            failures.append(validation_failure(
                "localization_body",
                "one mapped _GetText",
                len([row for row in get_text_rows if row.get("mappingStatus") == "mapped"]),
                full_name,
            ))
            continue

        create_targets = resolved_targets(create_rows[0])
        get_text_targets = resolved_targets(get_text_rows[0])
        init_targets = sorted(
            f"{type_name}::{method}"
            for type_name, method in create_targets
            if type_name.endswith("Behaviour")
            and method.startswith("Init")
        )
        localization_targets = {
            ("Beyond.I18n.I18nUtils", "TryGetText"),
            ("Beyond.Gameplay.GameplayUIUtils", "ResolveOriginalText"),
        }
        if not init_targets:
            failures.append(validation_failure(
                "playable_behaviour_initialization",
                "CreatePlayable -> Behaviour::Init*",
                sorted(f"{a}::{b}" for a, b in create_targets),
                full_name,
            ))
            continue
        missing_localization = sorted(
            f"{a}::{b}" for a, b in localization_targets - get_text_targets
        )
        if missing_localization:
            failures.append(validation_failure(
                "localized_text_resolution",
                sorted(f"{a}::{b}" for a, b in localization_targets),
                sorted(f"{a}::{b}" for a, b in get_text_targets),
                full_name,
            ))
            continue

        families.append({
            "type": full_name,
            "serializedAssetType": full_name.rsplit(".", 1)[-1],
            "textIdFields": text_fields,
            "createPlayable": {
                "methodIndex": create_rows[0].get("methodIndex"),
                "va": create_rows[0].get("methodPointerVa"),
                "behaviourInitializers": init_targets,
            },
            "localizedTextResolver": {
                "methodIndex": get_text_rows[0].get("methodIndex"),
                "va": get_text_rows[0].get("methodPointerVa"),
                "calls": sorted(f"{a}::{b}" for a, b in localization_targets),
            },
        })

    return {
        "validation": {
            "status": "validated" if families and not failures else "failed",
            "failures": failures,
        },
        "families": families,
    }


def analyze_npc_proxy_dialog_runtime_contract(
    catalog: dict[str, Any],
    body_map: dict[str, Any],
) -> dict[str, Any]:
    """Validate the general mission-scoped NPC dialog selection shape.

    The contract is discovered from managed field/method names and native body
    flow. It intentionally contains no authored mission, quest, proxy, dialog,
    address, or token allowlist. A patch that changes the carrier or selection
    shape therefore fails closed instead of silently inheriting old semantics.
    """
    wanted_types = {
        "Beyond.Gameplay.Core.NpcRuntimeProxyExData",
        "Beyond.Gameplay.Core.NpcInteractComponent",
        "Beyond.Gameplay.Core.NpcProxy",
    }
    types = {
        str(row.get("fullName") or ""): row
        for row in catalog.get("matchedTypes") or []
        if str(row.get("fullName") or "") in wanted_types
    }
    bodies: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in body_map.get("bodyTargets") or []:
        key = (str(row.get("type") or ""), str(row.get("method") or ""))
        bodies[key].append(row)

    failures: list[dict[str, Any]] = []

    def fail(gate: str, expected: Any, actual: Any) -> None:
        failures.append(validation_failure(
            gate,
            expected,
            actual,
            str(body_map.get("source") or "installed metadata/GameAssembly"),
        ))

    carrier = types.get("Beyond.Gameplay.Core.NpcRuntimeProxyExData") or {}
    carrier_fields = {
        str(field.get("name") or "") for field in carrier.get("fields") or []
    }
    expected_carrier_fields = {"dialogId", "missionId"}
    if not expected_carrier_fields.issubset(carrier_fields):
        fail(
            "npc_proxy_dialog_carrier_fields",
            sorted(expected_carrier_fields),
            sorted(carrier_fields),
        )

    proxy = types.get("Beyond.Gameplay.Core.NpcProxy") or {}
    proxy_fields = {
        str(field.get("name") or "") for field in proxy.get("fields") or []
    }
    if "m_activeCondIndex" not in proxy_fields:
        fail("npc_proxy_active_index_field", "m_activeCondIndex", sorted(proxy_fields))

    method_specs = {
        ("Beyond.Gameplay.Core.NpcProxy", "ChangeActiveCondition"): (
            "newActiveCondIndex",
        ),
        ("Beyond.Gameplay.Core.NpcProxy", "get_activeCondIndex"): (),
        (
            "Beyond.Gameplay.Core.NpcInteractComponent",
            "_TryGetNpcProxyInteractDialogId",
        ): ("dialogId",),
        ("Beyond.Gameplay.Core.NpcProxy", "_IsMissionConflict"): ("missionId",),
    }
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for key, expected_parameters in method_specs.items():
        matches = [
            row for row in bodies.get(key) or []
            if row.get("mappingStatus") == "mapped" and row.get("methodPointerVa")
        ]
        if len(matches) != 1:
            fail(
                "npc_proxy_native_method_mapping",
                {"type": key[0], "method": key[1], "mappedCount": 1},
                {"mappedCount": len(matches)},
            )
            continue
        row = matches[0]
        actual_parameters = tuple(
            str(parameter.get("name") or "")
            for parameter in row.get("parameterDetails") or []
        )
        if actual_parameters != expected_parameters:
            fail(
                "npc_proxy_native_method_parameters",
                {"type": key[0], "method": key[1], "parameters": expected_parameters},
                {"parameters": actual_parameters},
            )
            continue
        selected[key] = row

    change = selected.get(("Beyond.Gameplay.Core.NpcProxy", "ChangeActiveCondition")) or {}
    change_accesses = (change.get("methodBodySummary") or {}).get("fieldAccesses") or []
    one_based_read = any(
        row.get("origin") == "param:newActiveCondIndex-0x1"
        for row in change_accesses
    )
    active_index_writes = {
        str(row.get("origin") or "")
        for row in change_accesses
        if row.get("kind") == "write"
    }
    getter = selected.get(("Beyond.Gameplay.Core.NpcProxy", "get_activeCondIndex")) or {}
    getter_reads = {
        str(row.get("origin") or "")
        for row in (getter.get("methodBodySummary") or {}).get("fieldAccesses") or []
        if row.get("kind") == "read"
    }
    shared_active_storage = sorted(active_index_writes & getter_reads)
    if not one_based_read or not shared_active_storage:
        fail(
            "npc_proxy_one_based_active_row_selection",
            {"subtractOne": True, "sharedStoredField": True},
            {
                "subtractOne": one_based_read,
                "sharedStoredFieldOrigins": shared_active_storage,
            },
        )

    interact = selected.get((
        "Beyond.Gameplay.Core.NpcInteractComponent",
        "_TryGetNpcProxyInteractDialogId",
    )) or {}
    interact_summary = interact.get("methodBodySummary") or {}
    if not any(
        row.get("origin") == "param:dialogId" and row.get("kind") == "write"
        for row in interact_summary.get("fieldAccesses") or []
    ):
        fail(
            "npc_proxy_dialog_output_flow",
            "native write through dialogId output parameter",
            interact_summary.get("fieldAccesses") or [],
        )

    conflict = selected.get(("Beyond.Gameplay.Core.NpcProxy", "_IsMissionConflict")) or {}
    conflict_calls = {
        (str(target.get("type") or ""), str(target.get("method") or ""))
        for call in conflict.get("directCalls") or []
        for target in call.get("resolved") or []
    }
    if ("Beyond.Gameplay.MissionSystem", "GetMissionData") not in conflict_calls:
        fail(
            "npc_proxy_mission_conflict_consumer",
            "Beyond.Gameplay.MissionSystem.GetMissionData",
            sorted(f"{type_name}.{method}" for type_name, method in conflict_calls),
        )

    compact_methods = []
    for key in method_specs:
        row = selected.get(key)
        if not row:
            continue
        compact_methods.append({
            "type": key[0],
            "method": key[1],
            "token": row.get("token"),
            "va": row.get("methodPointerVa"),
        })
    return {
        "validation": {
            "status": "validated" if not failures else "failed",
            "failures": failures,
        },
        "nativeMappingId": "npc-proxy-dialog-selection-native-v2",
        "carrierType": "Beyond.Gameplay.Core.NpcRuntimeProxyExData",
        "carrierFields": sorted(expected_carrier_fields & carrier_fields),
        "activeIndexField": "m_activeCondIndex" if "m_activeCondIndex" in proxy_fields else "",
        "activeRowSelection": "one_based_external_index_stored_zero_based",
        "methods": compact_methods,
        "evidenceBoundary": {
            "missionDialogConfigurationCarrier": True,
            "oneBasedActiveRowSelection": True,
            "serverSelectionObserved": False,
            "questActivation": False,
            "branchSelection": False,
            "storyOrderEvidence": False,
        },
    }


def analyze_control_runtime_contract(
    catalog: dict[str, Any],
    body_map: dict[str, Any],
) -> dict[str, Any]:
    """Validate the general nested-director control path in the retail binary."""
    body_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in body_map.get("bodyTargets") or []:
        body_by_key[(str(row.get("type") or ""), str(row.get("method") or ""))].append(row)

    control_fields = {
        "sourceGameObject", "prefabGameObject", "updateDirector",
        "directorControlPath",
    }
    control_methods = {
        "CreatePlayable", "ResolveSourceGameObject", "GetControllableDirectors",
        "SearchHierarchyAndConnectDirector", "ConnectPlayablesToMixer",
        "ConnectMixerAndPlayable", "CreateActivationPlayable",
    }
    root_fields = {"_director", "_timelineName"}
    root_methods = {"get_topDirector"}

    control_candidates = []
    root_candidates = []
    for row in catalog.get("matchedTypes") or []:
        fields = {str(value.get("name") or "") for value in row.get("fields") or []}
        methods = {str(value.get("name") or "") for value in row.get("methods") or []}
        if control_fields.issubset(fields) and control_methods.issubset(methods):
            control_candidates.append(row)
        if root_fields.issubset(fields) and root_methods.issubset(methods):
            root_candidates.append(row)

    failures: list[dict[str, Any]] = []
    if len(control_candidates) != 1:
        failures.append(validation_failure(
            "control_playable_type_discovery", 1,
            [row.get("fullName") for row in control_candidates],
            "global-metadata.dat",
        ))
    if len(root_candidates) != 1:
        failures.append(validation_failure(
            "cutscene_root_type_discovery", 1,
            [row.get("fullName") for row in root_candidates],
            "global-metadata.dat",
        ))
    if failures:
        return {"validation": {"status": "failed", "failures": failures}}

    control_type = str(control_candidates[0]["fullName"])
    root_type = str(root_candidates[0]["fullName"])
    mapped_methods: dict[str, dict[str, Any]] = {}
    for method in sorted(control_methods):
        rows = body_by_key.get((control_type, method), [])
        mapped = [row for row in rows if row.get("mappingStatus") == "mapped"]
        if len(mapped) != 1:
            failures.append(validation_failure(
                "control_playable_method_body", f"one mapped {method}",
                len(mapped), control_type,
            ))
            continue
        mapped_methods[method] = mapped[0]

    top_rows = [
        row for row in body_by_key.get((root_type, "get_topDirector"), [])
        if row.get("mappingStatus") == "mapped"
    ]
    if len(top_rows) != 1:
        failures.append(validation_failure(
            "cutscene_root_top_director_body", "one mapped get_topDirector",
            len(top_rows), root_type,
        ))
    else:
        final_rax = str(
            ((top_rows[0].get("methodBodySummary") or {})
             .get("finalRegisterOrigins") or {}).get("rax") or ""
        )
        if final_rax != "this+0x20":
            failures.append(validation_failure(
                "cutscene_root_director_field", "get_topDirector returns this+0x20",
                final_rax, root_type,
            ))

    required_create_targets = {
        (control_type, "ResolveSourceGameObject"),
        (control_type, "GetControllableDirectors"),
        (control_type, "SearchHierarchyAndConnectDirector"),
        (control_type, "ConnectPlayablesToMixer"),
    }
    create_targets = (
        resolved_targets(mapped_methods["CreatePlayable"])
        if "CreatePlayable" in mapped_methods else set()
    )
    missing_targets = sorted(
        f"{a}::{b}" for a, b in required_create_targets - create_targets
    )
    if missing_targets:
        failures.append(validation_failure(
            "control_playable_create_chain",
            sorted(f"{a}::{b}" for a, b in required_create_targets),
            sorted(f"{a}::{b}" for a, b in create_targets),
            control_type,
        ))

    helper_targets = {
        "SearchHierarchyAndConnectDirector": {
            ("UnityEngine.Timeline.DirectorControlPlayable", "Create"),
        },
        "ConnectPlayablesToMixer": {
            (control_type, "ConnectMixerAndPlayable"),
        },
        "ConnectMixerAndPlayable": {
            ("UnityEngine.Playables.PlayableExtensions", "SetInputWeight"),
        },
    }
    for method, required in helper_targets.items():
        actual = resolved_targets(mapped_methods[method]) if method in mapped_methods else set()
        if not required.issubset(actual):
            failures.append(validation_failure(
                "control_playable_helper_chain",
                sorted(f"{a}::{b}" for a, b in required),
                sorted(f"{a}::{b}" for a, b in actual),
                f"{control_type}::{method}",
            ))

    def compact_method(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "token": row.get("token"),
            "methodIndex": row.get("methodIndex"),
            "va": row.get("methodPointerVa"),
            "calls": sorted(
                f"{a}::{b}" for a, b in resolved_targets(row)
            ),
        }

    return {
        "validation": {
            "status": "validated" if not failures else "failed",
            "failures": failures,
        },
        "controlPlayableAsset": {
            "type": control_type,
            "serializedFields": sorted(control_fields),
            "methods": {
                name: compact_method(row)
                for name, row in sorted(mapped_methods.items())
            },
        },
        "cutsceneRoot": {
            "type": root_type,
            "serializedFields": sorted(root_fields),
            "getTopDirector": compact_method(top_rows[0]) if len(top_rows) == 1 else {},
            "directorFieldOrigin": "this+0x20" if len(top_rows) == 1 else "",
        },
    }


def story_line_index(story_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    owners: dict[str, set[str]] = defaultdict(set)
    files = sorted(story_root.glob("*.json"))
    failures: list[dict[str, Any]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(validation_failure(
                "story_bundle_json", "valid JSON", str(exc), repo_path(path)
            ))
            continue
        key = str(payload.get("key") or "") if isinstance(payload, dict) else ""
        if not key:
            failures.append(validation_failure(
                "story_bundle_key", "non-empty key", key, repo_path(path)
            ))
            continue
        for line in payload.get("lines") or []:
            line_id = str(line.get("id") or "") if isinstance(line, dict) else ""
            if line_id:
                owners[line_id].add(key)
    ambiguous = {
        line_id: sorted(values) for line_id, values in owners.items()
        if len(values) != 1
    }
    index = {
        line_id: next(iter(values))
        for line_id, values in owners.items()
        if len(values) == 1
    }
    return index, {
        "status": "validated" if files and not failures else "failed",
        "sourceRoot": repo_path(story_root),
        "storyFiles": len(files),
        "lineIds": len(index),
        "excludedAmbiguousLineIds": len(ambiguous),
        "ambiguousLineOwners": ambiguous,
        "failures": failures,
        "evidenceBoundary": (
            "Generated Story bundles provide only the exact emitted line-to-Story-key join; "
            "runtime and containment evidence comes from installed binary and serialized Unity data."
        ),
    }


def original_file_record(path_value: str, role: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    meta = payload.get("$animestudio") or {}
    return {
        "role": role,
        "path": repo_path(path),
        # Unity PathIDs are signed 64-bit values and exceed JavaScript's safe
        # integer range. Publish their exact decimal spelling, never a JSON
        # number that the static WebUI would silently round.
        "pathId": str(meta["pathId"]) if isinstance(meta.get("pathId"), int) else meta.get("pathId"),
        "sourceFile": meta.get("sourceFile"),
        "sourceOriginalPath": meta.get("sourceOriginalPath"),
        "sourceOffset": meta.get("sourceOffset"),
        "byteSize": meta.get("byteSize"),
        "rawDataSha256": meta.get("rawDataSha256"),
        "exportedJsonSha256": sha256_path(path),
    }


def hashed_source_record(path_value: Path | str, role: str) -> dict[str, Any]:
    """Describe an exact original binary/serialized input with its live hash."""
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise RuntimeError(
            "validator=timeline_embedded_story_runtime failed: "
            "gate=related_original_file; "
            f"source={path}; expected=existing file; actual=missing"
        )
    return {
        "role": role,
        "path": repo_path(path),
        "byteSize": path.stat().st_size,
        "sha256": sha256_path(path),
    }


def discover_parent_dialog_candidate_levels(
    dialog_keys: set[str],
    levelscript_root: Path,
) -> list[str]:
    """Find only levels whose original LevelScript bytes carry a target key."""
    needles = tuple(
        value.encode("utf-8")
        for value in sorted(dialog_keys)
        if value
    )
    if not needles or not levelscript_root.is_dir():
        return []
    levels: set[str] = set()
    for path in sorted(levelscript_root.glob("*/*.json")):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if any(needle in data for needle in needles):
            levels.add(path.parent.name)
    return sorted(levels)


def _compact_mission_host(host: dict[str, Any]) -> dict[str, Any]:
    return {
        "missionId": host.get("missionId"),
        "levelDataFile": host.get("levelDataFile"),
        "byteOffsets": host.get("byteOffsets") or [],
        "entryEndOffsets": host.get("entryEndOffsets") or [],
        "encoding": host.get("encoding"),
        "nativeSchema": host.get("nativeSchema"),
        "briefData": [
            {
                key: row.get(key)
                for key in (
                    "scriptId", "keyOffset", "endOffset", "dataPathHash",
                    "levelScriptType", "maxStage", "parentLevelScriptId",
                    "dictionaryCountOffset", "dictionaryEntryCount",
                )
            }
            for row in host.get("briefData") or []
            if isinstance(row, dict)
        ],
    }


def _compact_local_trigger_context(context: dict[str, Any]) -> dict[str, Any]:
    """Keep the exact selector/geometry proof without copying parser noise."""
    return {
        "status": context.get("status"),
        "selectorSlotIds": context.get("selectorSlotIds") or [],
        "matchedSlotIds": context.get("matchedSlotIds") or [],
        "missingSlotIds": context.get("missingSlotIds") or [],
        "ambiguousSlotIds": context.get("ambiguousSlotIds") or [],
        "triggerVolumesStatus": context.get("triggerVolumesStatus"),
        "triggerVolumesParseStatus": context.get("triggerVolumesParseStatus"),
        "triggerVolumesOffsetHex": context.get("triggerVolumesOffsetHex"),
        "scriptIdVerified": context.get("scriptIdVerified") is True,
        "schemaMappingId": (context.get("schema") or {}).get("mappingId"),
        "foreignKeyBridgeFound": context.get("foreignKeyBridgeFound") is True,
        "missionGraphAction": context.get("missionGraphAction"),
        "triggerVolumes": [
            {
                "slotId": volume.get("slotId"),
                "keySlotId": volume.get("keySlotId"),
                "triggerVolumeType": volume.get("triggerVolumeType"),
                "offset": volume.get("offset"),
                "triggerCountLimit": volume.get("triggerCountLimit"),
                "enterCheckOnGround": volume.get("enterCheckOnGround"),
                "isImportant": volume.get("isImportant"),
                "triggerOnPole": volume.get("triggerOnPole"),
                "waitSrvRes": volume.get("waitSrvRes"),
                "shapes": [
                    {
                        key: shape.get(key)
                        for key in (
                            "offset", "shapeType", "position", "radius",
                            "rotation", "size",
                        )
                    }
                    for shape in (volume.get("shapeList") or {}).get("shapes") or []
                    if isinstance(shape, dict)
                ],
            }
            for volume in context.get("triggerVolumes") or []
            if isinstance(volume, dict)
        ],
    }


EXACT_NATIVE_CONTROL_PATH_STATUSES = {
    "exact_serialized_control_path",
    "exact_serialized_control_path_equivalent_duplicates",
    "exact_serialized_control_path_runtime_shadowing",
}


def _activation_control_decisions(path: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain typed branch semantics along one exact native control path.

    A path step stores the incoming edge on the target action.  The control
    kind and runtime proof belong to the preceding source action.  Joining the
    two by their position in this already-validated path is therefore a typed
    control-flow interpretation, not serialized-record adjacency.
    """
    decisions: list[dict[str, Any]] = []
    for index in range(1, len(path)):
        source = path[index - 1]
        target = path[index]
        control_kind = str(source.get("controlKind") or "")
        if control_kind not in {
            "parallel_fanout", "conditional_choice", "conditional_loop",
        }:
            continue
        decisions.append({
            key: value
            for key, value in {
                "controlKind": control_kind,
                "sourceLocalId": source.get("localId"),
                "sourceActionName": source.get("actionName"),
                "selectedEdge": target.get("edge"),
                "targetLocalId": target.get("localId"),
                "branchPredicate": source.get("branchPredicate") or None,
                "controlRuntimeMappingId": source.get("controlRuntimeMappingId"),
                "siblingOrder": (
                    "unordered"
                    if control_kind == "parallel_fanout"
                    else None
                ),
                "selectionObserved": False,
            }.items()
            if value not in (None, "", [], {})
        })
    return decisions


def join_parent_dialog_activation_routes(
    rows: list[dict[str, Any]],
    header_report: dict[str, Any],
    playback_index: dict[str, list[dict[str, Any]]],
    mission_hosts: dict[tuple[str, str], dict[str, Any]],
    mission_area_hosts: dict[tuple[str, str], dict[str, Any]],
    *,
    gameassembly: Path,
    metadata: Path,
    mission_runtime_root: Path,
    mission_tracking_rows: list[dict[str, Any]] | None = None,
    tracking_context_matcher: Any | None = None,
) -> dict[str, Any]:
    """Join native event roots to Timeline parents by exact dialog identity.

    The general shape is:

    ``active header slot -> typed action-control path -> StartDialog(dialog key)``
    ``-> dialog registry Timeline -> PlayableDirector/ControlPlayableAsset``.

    A fully decoded LevelData member-22 host can additionally prove the owning
    mission shell. Typed quest tracking points inside the event-selected
    trigger shape are retained as spatial context only. Neither relation proves
    a quest activator, selected branch, or chronology inside/between missions.
    """
    dialog_to_story: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        dialog_key = str(row.get("dialogKey") or "")
        story_key = str(row.get("key") or "")
        if dialog_key and story_key:
            dialog_to_story[dialog_key].add(story_key)
    wanted = set(dialog_to_story)
    expected_slot_mapping = str(
        (header_report.get("summary") or {}).get("runtimeSlotMappingId") or ""
    )
    failures: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    header_rows_by_key: dict[tuple[str, str, int], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for header_row in header_report.get("headerRows") or []:
        if not isinstance(header_row, dict):
            continue
        header = header_row.get("header") or {}
        header_local_id = header.get("localId")
        if isinstance(header_local_id, int):
            header_rows_by_key[(
                str(header_row.get("levelId") or ""),
                str(header_row.get("sourceScript") or ""),
                header_local_id,
            )].append(header_row)

    playback_actions = [
        (dialog_key, occurrence)
        for dialog_key in sorted(wanted)
        for occurrence in playback_index.get(dialog_key) or []
        if isinstance(occurrence, dict)
        and occurrence.get("recordClass") == "play_dialog"
        and occurrence.get("actionName")
    ]
    dialogs_with_playback = {dialog_key for dialog_key, _row in playback_actions}
    candidate_owner_count = 0
    mission_tracking_rows = mission_tracking_rows or []

    for dialog_key, occurrence in playback_actions:
        level_id = str(occurrence.get("levelId") or "")
        script_id = str(occurrence.get("scriptId") or "")
        source_file = str(occurrence.get("sourceFile") or "")
        owners = occurrence.get("nativeEventOwners") or []
        candidate_owner_count += len(owners)
        for owner in owners:
            if not isinstance(owner, dict):
                continue
            header_local_id = owner.get("headerLocalId")
            path = owner.get("path") or []
            header_matches = (
                header_rows_by_key.get((level_id, script_id, header_local_id), [])
                if isinstance(header_local_id, int)
                else []
            )
            header_row = header_matches[0] if len(header_matches) == 1 else {}
            header_source_file = str(header_row.get("file") or "")
            final_step = path[-1] if path and isinstance(path[-1], dict) else {}
            strict_common = (
                owner.get("status") in EXACT_NATIVE_CONTROL_PATH_STATUSES
                and len(header_matches) == 1
                and bool(expected_slot_mapping)
                and header_row.get("runtimeSlotStatus")
                == "active-final-serialized-slot"
                and str(header_row.get("runtimeSlotMappingId") or "")
                == expected_slot_mapping
                and header_row.get("targetStatus") == "action-list"
                and header_row.get("headerName") == owner.get("headerName")
                and (header_row.get("eventDetail") or {})
                == (owner.get("eventDetail") or {})
                and header_row.get("targetLocalId") == owner.get("targetLocalId")
                and bool(level_id)
                and script_id.isdigit()
                and bool(source_file)
                and header_source_file == source_file
                and bool(path)
                and final_step.get("localId") == occurrence.get("localId")
                and final_step.get("recordClass") == "play_dialog"
                and dialog_key in {
                    str(value) for value in final_step.get("texts") or []
                }
            )
            if not strict_common:
                failures.append(validation_failure(
                    "parent_dialog_event_action_path",
                    {
                        "nativeOwnerStatus": sorted(EXACT_NATIVE_CONTROL_PATH_STATUSES),
                        "headerMatches": 1,
                        "runtimeSlotStatus": "active-final-serialized-slot",
                        "runtimeSlotMappingId": expected_slot_mapping,
                        "targetStatus": "action-list",
                        "sourceFileMatches": True,
                        "eventDetailMatches": True,
                        "pathTargetLocalId": occurrence.get("localId"),
                        "pathTargetClass": "play_dialog",
                        "pathTargetDialog": dialog_key,
                    },
                    {
                        "nativeOwnerStatus": owner.get("status"),
                        "headerMatches": len(header_matches),
                        "runtimeSlotStatus": header_row.get("runtimeSlotStatus"),
                        "runtimeSlotMappingId": header_row.get("runtimeSlotMappingId"),
                        "targetStatus": header_row.get("targetStatus"),
                        "sourceFileMatches": header_source_file == source_file,
                        "eventDetailMatches": (
                            (header_row.get("eventDetail") or {})
                            == (owner.get("eventDetail") or {})
                        ),
                        "pathTargetLocalId": final_step.get("localId"),
                        "pathTargetClass": final_step.get("recordClass"),
                        "pathTargetTexts": final_step.get("texts") or [],
                    },
                    source_file or f"{level_id}/{script_id}",
                ))
                continue

            event_detail = header_row.get("eventDetail") or {}
            trigger_slot_id = (
                event_detail.get("triggerSlotIdFilter")
                if isinstance(event_detail, dict)
                else None
            )
            local_trigger_context = header_row.get("localTriggerVolumeContext") or {}
            if isinstance(trigger_slot_id, int) and not isinstance(trigger_slot_id, bool):
                schema = local_trigger_context.get("schema") or {}
                volume_matches = local_trigger_context.get("triggerVolumes") or []
                valid_trigger_context = (
                    event_detail.get("type") == header_row.get("headerName")
                    and event_detail.get("payloadSchemaStatus")
                    == "exact_current_build_memorypack_fields"
                    and local_trigger_context.get("status")
                    == "exact_local_levelscript_trigger_volume_without_foreign_identity"
                    and local_trigger_context.get("selectorSlotIds") == [trigger_slot_id]
                    and local_trigger_context.get("matchedSlotIds") == [trigger_slot_id]
                    and local_trigger_context.get("missingSlotIds") in ([], None)
                    and local_trigger_context.get("ambiguousSlotIds") in ([], None)
                    and local_trigger_context.get("scriptIdVerified") is True
                    and local_trigger_context.get("triggerVolumesStatus") == "present"
                    and local_trigger_context.get("triggerVolumesParseStatus") == "decoded"
                    and local_trigger_context.get("foreignKeyBridgeFound") is False
                    and local_trigger_context.get("missionGraphAction") == "none"
                    and schema.get("mappingId")
                    == "current-global-metadata-levelscript-trigger-volume-data-fields"
                    and len(volume_matches) == 1
                    and volume_matches[0].get("slotId") == trigger_slot_id
                    and volume_matches[0].get("keySlotId") == trigger_slot_id
                )
                if not valid_trigger_context:
                    failures.append(validation_failure(
                        "parent_dialog_trigger_volume_selector",
                        {
                            "eventType": header_row.get("headerName"),
                            "selectorSlotId": trigger_slot_id,
                            "contextStatus": (
                                "exact_local_levelscript_trigger_volume_"
                                "without_foreign_identity"
                            ),
                            "matchedSlotIds": [trigger_slot_id],
                        },
                        {
                            "eventType": event_detail.get("type"),
                            "selectorSlotId": trigger_slot_id,
                            "contextStatus": local_trigger_context.get("status"),
                            "matchedSlotIds": (
                                local_trigger_context.get("matchedSlotIds") or []
                            ),
                            "missingSlotIds": (
                                local_trigger_context.get("missingSlotIds") or []
                            ),
                            "ambiguousSlotIds": (
                                local_trigger_context.get("ambiguousSlotIds") or []
                            ),
                        },
                        source_file or f"{level_id}/{script_id}",
                    ))
                    continue

            pair = (level_id, script_id)
            host = mission_hosts.get(pair) or {}
            host_ids = sorted({
                str(value) for value in host.get("hostMissionIds") or [] if value
            })
            mission_shell_ownership = (
                host.get("status") == "unique" and len(host_ids) == 1
            )
            area_host = mission_area_hosts.get(pair) or {}
            eligible_tracking_rows = [
                tracking
                for tracking in mission_tracking_rows
                if isinstance(tracking, dict)
                and mission_shell_ownership
                and str(tracking.get("missionId") or "") in host_ids
                and str(tracking.get("scene") or "") == level_id
                and isinstance(tracking.get("position"), dict)
            ]
            quest_spatial_contexts: list[dict[str, Any]] = []
            if callable(tracking_context_matcher):
                for tracking in eligible_tracking_rows:
                    matches = tracking_context_matcher(occurrence, tracking)
                    if len(matches) != 1:
                        continue
                    match = matches[0]
                    quest_spatial_contexts.append({
                        "status": match.get("status"),
                        "spatialRelation": (
                            "tracking_target_point_inside_event_selected_"
                            "trigger_shape"
                        ),
                        "missionId": tracking.get("missionId"),
                        "questId": tracking.get("questId"),
                        "objectiveIndex": tracking.get("objectiveIndex"),
                        "trackingIndex": tracking.get("trackingIndex"),
                        "trackingType": tracking.get("type"),
                        "sourceType": tracking.get("sourceType"),
                        "missionAreaId": tracking.get("missionAreaId"),
                        "npcProxyId": tracking.get("npcProxyId"),
                        "trackingPosition": match.get("trackingPosition"),
                        "triggerSlotId": match.get("triggerSlotId"),
                        "triggerShapeOffset": match.get("triggerShapeOffset"),
                        "triggerShape": match.get("triggerShape"),
                        "containmentMethod": match.get("containmentMethod"),
                        "localPoint": match.get("localPoint"),
                        "distanceToCenter": match.get("distanceToCenter"),
                        "boundaryMargin": match.get("boundaryMargin"),
                        "boundaryMargins": match.get("boundaryMargins"),
                        "missionRuntimeSourceFile": tracking.get(
                            "missionRuntimeSourceFile"
                        ),
                        "missionRuntimeSourcePath": tracking.get(
                            "missionRuntimeSourcePath"
                        ),
                        "positionSourceFiles": tracking.get(
                            "positionSourceFiles"
                        ) or [],
                        "questActivation": False,
                        "branchSelection": False,
                        "storyOrderEvidence": False,
                    })
            quest_spatial_contexts = list({
                (
                    str(context.get("missionId") or ""),
                    str(context.get("questId") or ""),
                    context.get("objectiveIndex"),
                    context.get("trackingIndex"),
                    context.get("triggerShapeOffset"),
                ): context
                for context in quest_spatial_contexts
            }.values())
            quest_spatial_contexts.sort(key=lambda context: (
                str(context.get("missionId") or ""),
                str(context.get("questId") or ""),
                int(context.get("objectiveIndex") or 0),
                int(context.get("trackingIndex") or 0),
                str(context.get("triggerShapeOffset") or ""),
            ))
            related_files = [
                hashed_source_record(source_file, "levelscript_event_action_source"),
                hashed_source_record(gameassembly, "original_game_binary"),
                hashed_source_record(metadata, "original_game_metadata"),
            ]
            compact_hosts = [
                _compact_mission_host(value)
                for value in host.get("hosts") or []
                if isinstance(value, dict)
            ]
            for compact_host in compact_hosts:
                leveldata_file = str(compact_host.get("levelDataFile") or "")
                if leveldata_file:
                    related_files.append(hashed_source_record(
                        leveldata_file, "mission_leveldata_script_host"
                    ))
            for mission_id in host_ids:
                mission_path = mission_runtime_root / f"{mission_id}.json"
                if mission_path.is_file():
                    related_files.append(hashed_source_record(
                        mission_path, "mission_runtime_shell_identity"
                    ))
            tracking_source_roles = {
                "MissionAreaTable.json": "quest_tracking_mission_area_table",
                "LevelBasicInfoTable.json": "quest_tracking_level_table",
                "NpcProxyTable.json": "quest_tracking_npc_proxy_table",
            }
            for context in quest_spatial_contexts:
                for tracking_source in context.get("positionSourceFiles") or []:
                    source_name = Path(str(tracking_source)).name
                    role = tracking_source_roles.get(
                        source_name,
                        "quest_tracking_mission_runtime",
                    )
                    related_files.append(hashed_source_record(
                        str(tracking_source), role
                    ))
            area_references: list[dict[str, Any]] = []
            for area_shell in area_host.get("hosts") or []:
                if not isinstance(area_shell, dict):
                    continue
                for reference in area_shell.get("missionAreaReferences") or []:
                    if not isinstance(reference, dict):
                        continue
                    area_references.append({
                        key: reference.get(key)
                        for key in (
                            "missionId", "questId", "missionAreaId",
                            "subDataParentId", "trackingType", "sourceFile",
                        )
                    })
                    reference_file = str(reference.get("sourceFile") or "")
                    if reference_file:
                        related_files.append(hashed_source_record(
                            reference_file, "mission_area_tracking_context"
                        ))
            deduped_files = {
                (str(file.get("role") or ""), str(file.get("path") or "")): file
                for file in related_files
            }
            header = header_row.get("header") or {}
            control_decisions = _activation_control_decisions(path)
            path_signature = hashlib.sha256(json.dumps(
                [
                    [str(step.get("edge") or ""), step.get("localId")]
                    for step in path if isinstance(step, dict)
                ],
                separators=(",", ":"),
            ).encode("utf-8")).hexdigest()[:12]
            route_id = (
                f"{level_id}/{script_id}/{header.get('localId')}/"
                f"{occurrence.get('localId')}/{dialog_key}/{path_signature}"
            )
            routes.append({
                "id": route_id,
                "dialogKey": dialog_key,
                "storyKeys": sorted(dialog_to_story[dialog_key]),
                "levelId": level_id,
                "scriptId": script_id,
                "headerName": header_row.get("headerName"),
                "eventDetail": event_detail,
                "headerLocalId": header.get("localId"),
                "headerOffset": header.get("offset"),
                "headerOpcode": header.get("opcode"),
                "targetSource": header_row.get("targetSource"),
                "targetLocalId": header_row.get("targetLocalId"),
                "playActionLocalId": occurrence.get("localId"),
                "playActionOffset": occurrence.get("recordOffset"),
                "playActionOpcode": (
                    f"{occurrence.get('actionCode')}/{occurrence.get('actionKind')}"
                    if occurrence.get("actionCode") and occurrence.get("actionKind")
                    else ""
                ),
                "playActionName": occurrence.get("actionName"),
                "actionChain": path,
                "chainStatus": owner.get("status"),
                "controlDecisions": control_decisions,
                "parallelFanout": any(
                    row.get("controlKind") == "parallel_fanout"
                    for row in control_decisions
                ),
                "conditionalActivation": any(
                    row.get("controlKind") in {
                        "conditional_choice", "conditional_loop",
                    }
                    for row in control_decisions
                ),
                "runtimeSlotStatus": header_row.get("runtimeSlotStatus"),
                "runtimeSlotMappingId": header_row.get("runtimeSlotMappingId"),
                "localTriggerVolumeContext": (
                    _compact_local_trigger_context(local_trigger_context)
                    if local_trigger_context else {}
                ),
                "missionShellStatus": host.get("status") or "unresolved",
                "missionShellIds": host_ids,
                "missionShellOwnership": mission_shell_ownership,
                "missionLevelDataHosts": compact_hosts,
                "missionAreaContextStatus": area_host.get("status") or "unresolved",
                "missionAreaReferences": sorted(
                    area_references,
                    key=lambda value: (
                        str(value.get("missionId") or ""),
                        str(value.get("questId") or ""),
                        str(value.get("missionAreaId") or ""),
                    ),
                ),
                "questSpatialContextStatus": (
                    "exact_tracking_points_inside_trigger_shape"
                    if quest_spatial_contexts
                    else (
                        "checked_no_containment"
                        if mission_shell_ownership and eligible_tracking_rows
                        else "not_applicable"
                    )
                ),
                "questSpatialTrackingRowsChecked": len(eligible_tracking_rows),
                "questSpatialContexts": quest_spatial_contexts,
                "questActivation": False,
                "branchSelection": False,
                "crossTimelineOrder": False,
                "relatedOriginalFiles": sorted(
                    deduped_files.values(),
                    key=lambda value: (
                        str(value.get("role") or ""),
                        str(value.get("path") or ""),
                    ),
                ),
            })

    routes.sort(key=lambda route: route["id"])
    route_ids_by_dialog: dict[str, list[str]] = defaultdict(list)
    for route in routes:
        route_ids_by_dialog[str(route["dialogKey"])].append(str(route["id"]))
    story_keys_with_routes: set[str] = set()
    mission_shell_ids: set[str] = set()
    for row in rows:
        route_ids = route_ids_by_dialog.get(str(row.get("dialogKey") or ""), [])
        row["parentDialogActivationRouteIds"] = route_ids
        if route_ids:
            story_keys_with_routes.add(str(row.get("key") or ""))
        row_routes = [route for route in routes if route["id"] in route_ids]
        owned_missions = sorted({
            mission_id
            for route in row_routes
            if route.get("missionShellOwnership")
            for mission_id in route.get("missionShellIds") or []
        })
        row["missionOwnership"] = bool(owned_missions)
        row["missionShellIds"] = owned_missions
        mission_shell_ids.update(owned_missions)

    matched_dialogs = {str(route["dialogKey"]) for route in routes}
    unresolved_dialogs = [
        {
            "dialogKey": dialog_key,
            "reason": (
                "no_exact_native_playback_action"
                if dialog_key not in dialogs_with_playback
                else "no_validated_native_event_control_path"
            ),
        }
        for dialog_key in sorted(wanted - matched_dialogs)
    ]
    return {
        "validation": {
            "status": "validated" if not failures else "failed",
            "failures": failures,
        },
        "routes": routes,
        "unresolvedParentDialogs": unresolved_dialogs,
        "counts": {
            "parentDialogKeys": len(wanted),
            "exactPlaybackActions": len(playback_actions),
            "candidateEventControlPaths": candidate_owner_count,
            "candidateHeaderRows": len({
                (
                    str(route.get("levelId") or ""),
                    str(route.get("scriptId") or ""),
                    route.get("headerLocalId"),
                )
                for route in routes
            }),
            "exactActivationRoutes": len(routes),
            "parentDialogsWithExactActivation": len(matched_dialogs),
            "parentDialogsWithoutExactActivation": len(wanted - matched_dialogs),
            "storyKeysWithExactActivation": len(story_keys_with_routes),
            "uniqueMissionShells": len(mission_shell_ids),
            "missionOwnedRoutes": sum(
                bool(route.get("missionShellOwnership")) for route in routes
            ),
            "exactLocalTriggerVolumeRoutes": sum(
                bool(route.get("localTriggerVolumeContext")) for route in routes
            ),
            "routesWithQuestSpatialContext": sum(
                bool(route.get("questSpatialContexts")) for route in routes
            ),
            "questSpatialContextRows": sum(
                len(route.get("questSpatialContexts") or []) for route in routes
            ),
            "questSpatialContextQuestIds": len({
                str(context.get("questId") or "")
                for route in routes
                for context in route.get("questSpatialContexts") or []
                if context.get("questId")
            }),
        },
        "evidenceBoundary": {
            "eventToActionTopology": True,
            "typedBranchSemantics": True,
            "parallelFanoutSiblingOrder": False,
            "conditionalRouteSelectionObserved": False,
            "parentDialogPlayback": True,
            "missionShellOwnership": "unique_validated_leveldata_hosts_only",
            "localTriggerVolumeGeometry": (
                "exact_event_selector_to_same_levelscript_memorypack_volume"
            ),
            "questSpatialContext": (
                "typed_original_tracking_point_inside_exact_event_selected_"
                "trigger_shape_only"
            ),
            "questActivation": False,
            "branchSelection": False,
            "crossTimelineOrder": False,
            "ocrOrManualOverrideUsed": False,
        },
    }


def join_parent_dialog_configuration_contexts(
    rows: list[dict[str, Any]],
    native_contract: dict[str, Any],
    *,
    npc_proxy_ex_path: Path,
    mission_runtime_root: Path,
    gameassembly: Path,
    metadata: Path,
    mission_tracking_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Join Timeline parents to mission-scoped NPC dialog configuration.

    This general join follows identities authored in the original corpus:

    ``Timeline child -> parent dialog key``
    ``NpcProxyEx data[proxy].dialogId + missionId``
    ``MissionRuntime typed NpcProxyTrackingInfo.npcProxyId``

    The authored mission/dialog pair always establishes mission configuration
    context. A quest-navigation context is published only when the exact proxy
    is tracked by one quest in that same mission. Neither relation is promoted
    to parent playback, activation, branch selection, or Story order.
    """
    failures = list((native_contract.get("validation") or {}).get("failures") or [])
    if (native_contract.get("validation") or {}).get("status") != "validated":
        return {
            "validation": {"status": "failed", "failures": failures},
            "contexts": [],
            "counts": {},
        }
    try:
        raw = json.loads(npc_proxy_ex_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(validation_failure(
            "npc_proxy_ex_source",
            "readable JSON object with data mapping",
            f"{type(error).__name__}: {error}",
            repo_path(npc_proxy_ex_path),
        ))
        return {
            "validation": {"status": "failed", "failures": failures},
            "contexts": [],
            "counts": {},
        }
    proxy_groups = raw.get("data") if isinstance(raw, dict) else None
    if not isinstance(proxy_groups, dict):
        failures.append(validation_failure(
            "npc_proxy_ex_schema",
            "top-level data object",
            type(proxy_groups).__name__,
            repo_path(npc_proxy_ex_path),
        ))
        return {
            "validation": {"status": "failed", "failures": failures},
            "contexts": [],
            "counts": {},
        }

    dialog_to_story: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        dialog_key = str(row.get("dialogKey") or "").strip()
        story_key = str(row.get("key") or "").strip()
        if dialog_key and story_key:
            dialog_to_story[dialog_key].add(story_key)
    wanted = set(dialog_to_story)

    tracking_by_mission_proxy: dict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for tracking in mission_tracking_rows:
        if not isinstance(tracking, dict):
            continue
        tracking_type = str(tracking.get("type") or "").rsplit(".", 1)[-1]
        mission_id = str(tracking.get("missionId") or "").strip()
        proxy_id = str(tracking.get("npcProxyId") or "").strip()
        if tracking_type == "NpcProxyTrackingInfo" and mission_id and proxy_id:
            tracking_by_mission_proxy[(mission_id, proxy_id)].append(tracking)

    shared_files = [
        hashed_source_record(npc_proxy_ex_path, "npc_proxy_dialog_configuration"),
        hashed_source_record(gameassembly, "original_game_binary"),
        hashed_source_record(metadata, "original_global_metadata"),
    ]
    contexts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_proxy_id, raw_rows in sorted(proxy_groups.items()):
        proxy_id = str(raw_proxy_id or "").strip()
        proxy_rows = raw_rows if isinstance(raw_rows, list) else [raw_rows]
        for row_index, proxy_row in enumerate(proxy_rows):
            if not proxy_id or not isinstance(proxy_row, dict):
                continue
            dialog_key = str(proxy_row.get("dialogId") or "").strip()
            mission_id = str(proxy_row.get("missionId") or "").strip()
            if dialog_key not in wanted or not mission_id:
                continue
            matching_tracking = tracking_by_mission_proxy.get(
                (mission_id, proxy_id), []
            )
            quest_ids = sorted({
                str(tracking.get("questId") or "").strip()
                for tracking in matching_tracking
                if tracking.get("questId")
            })
            unique_quest = len(quest_ids) == 1
            context_id = (
                f"npc-proxy-dialog:{mission_id}:{proxy_id}:{dialog_key}:{row_index}"
            )
            if context_id in seen_ids:
                continue
            seen_ids.add(context_id)
            mission_source = mission_runtime_root / f"{mission_id}.json"
            related_files = list(shared_files)
            if mission_source.is_file():
                related_files.append(hashed_source_record(
                    mission_source,
                    "quest_tracking_mission_runtime",
                ))
            compact_tracking = [{
                key: tracking.get(key)
                for key in (
                    "missionId", "questId", "objectiveIndex", "trackingIndex",
                    "type", "scene", "npcProxyId", "position",
                    "missionRuntimeSourceFile", "missionRuntimeSourcePath",
                )
                if tracking.get(key) not in (None, "", [], {})
            } for tracking in matching_tracking]
            contexts.append({
                "id": context_id,
                "dialogKey": dialog_key,
                "storyKeys": sorted(dialog_to_story[dialog_key]),
                "missionId": mission_id,
                "npcProxyId": proxy_id,
                "npcProxyExRowIndex": row_index,
                "sourcePath": f"$.data.{proxy_id}[{row_index}]",
                "nativeMappingId": native_contract.get("nativeMappingId"),
                "activeRowSelection": native_contract.get("activeRowSelection"),
                "questNavigationContext": unique_quest,
                "questNavigationStatus": (
                    "exact_unique_typed_npc_proxy_tracking_quest"
                    if unique_quest else (
                        "ambiguous_multiple_tracking_quests"
                        if quest_ids else "no_typed_tracking_quest"
                    )
                ),
                "candidateQuestIds": quest_ids,
                "trackingRows": compact_tracking,
                "missionConfigurationContext": True,
                "parentDialogPlayback": False,
                "questActivation": False,
                "branchSelection": False,
                "storyOrderEvidence": False,
                "serverSelectionObserved": False,
                "relatedOriginalFiles": sorted(
                    related_files,
                    key=lambda value: (
                        str(value.get("role") or ""),
                        str(value.get("path") or ""),
                    ),
                ),
            })

    contexts.sort(key=lambda value: value["id"])
    ids_by_dialog: dict[str, list[str]] = defaultdict(list)
    mission_ids: set[str] = set()
    quest_ids: set[str] = set()
    for context in contexts:
        ids_by_dialog[str(context["dialogKey"])].append(str(context["id"]))
        mission_ids.add(str(context["missionId"]))
        quest_ids.update(str(value) for value in context["candidateQuestIds"])
    for row in rows:
        context_ids = ids_by_dialog.get(str(row.get("dialogKey") or ""), [])
        row["parentDialogConfigurationContextIds"] = context_ids
        row["missionConfigurationContext"] = bool(context_ids)

    matched_dialogs = set(ids_by_dialog)
    return {
        "validation": {"status": "validated", "failures": []},
        "nativeContract": native_contract,
        "contexts": contexts,
        "unresolvedParentDialogs": [{
            "dialogKey": dialog_key,
            "reason": "no_exact_mission_scoped_npc_proxy_dialog_configuration",
        } for dialog_key in sorted(wanted - matched_dialogs)],
        "counts": {
            "parentDialogKeys": len(wanted),
            "configurationContexts": len(contexts),
            "parentDialogsWithConfigurationContext": len(matched_dialogs),
            "missionConfigurationContexts": len(contexts),
            "uniqueMissionIds": len(mission_ids),
            "questNavigationContexts": sum(
                bool(context.get("questNavigationContext")) for context in contexts
            ),
            "uniqueQuestIds": len(quest_ids),
            "parentDialogPlaybackEdges": 0,
            "questActivationEdges": 0,
            "branchSelectionEdges": 0,
            "storyOrderEdges": 0,
        },
        "evidenceBoundary": {
            "missionConfigurationContext": True,
            "questNavigationContext": "unique_typed_same_mission_proxy_only",
            "parentDialogPlayback": False,
            "questActivation": False,
            "branchSelection": False,
            "storyOrderEvidence": False,
            "serverSelectionObserved": False,
            "ocrOrManualOverrideUsed": False,
        },
    }


def recover_parent_dialog_configuration_contexts(
    rows: list[dict[str, Any]],
    native_contract: dict[str, Any],
    *,
    gameassembly: Path,
    metadata: Path,
    npc_proxy_ex_path: Path | None = None,
    mission_runtime_root: Path | None = None,
) -> dict[str, Any]:
    """Run the corpus-wide NPC configuration join for all parent dialogs."""
    story_context, level_bindings, _header_audit = _story_recovery_modules()
    npc_proxy_ex_path = npc_proxy_ex_path or story_context.NPC_PROXY_EX_PATH
    mission_runtime_root = mission_runtime_root or story_context.MRA_DIR
    relevant_missions: set[str] = set()
    wanted = {
        str(row.get("dialogKey") or "").strip()
        for row in rows if row.get("dialogKey")
    }
    try:
        proxy_groups = (
            json.loads(npc_proxy_ex_path.read_text(encoding="utf-8-sig")).get("data")
            or {}
        )
    except (OSError, json.JSONDecodeError, AttributeError):
        proxy_groups = {}
    if isinstance(proxy_groups, dict):
        for raw_rows in proxy_groups.values():
            for proxy_row in raw_rows if isinstance(raw_rows, list) else [raw_rows]:
                if (
                    isinstance(proxy_row, dict)
                    and str(proxy_row.get("dialogId") or "").strip() in wanted
                    and str(proxy_row.get("missionId") or "").strip()
                ):
                    relevant_missions.add(
                        str(proxy_row.get("missionId") or "").strip()
                    )
    tracking_rows = level_bindings.build_resolved_mission_tracking_context_rows(
        relevant_missions,
        mission_runtime_root=mission_runtime_root,
    ) if relevant_missions else []
    return join_parent_dialog_configuration_contexts(
        rows,
        native_contract,
        npc_proxy_ex_path=npc_proxy_ex_path,
        mission_runtime_root=mission_runtime_root,
        gameassembly=gameassembly,
        metadata=metadata,
        mission_tracking_rows=tracking_rows,
    )


def recover_parent_dialog_activation_routes(
    rows: list[dict[str, Any]],
    *,
    gameassembly: Path,
    metadata: Path,
    levelscript_root: Path | None = None,
) -> dict[str, Any]:
    """Run the exact activation join over every discovered parent dialog."""
    story_context, level_bindings, header_audit = _story_recovery_modules()
    use_default_levelscript_root = levelscript_root is None
    levelscript_root = levelscript_root or story_context.LEVELSCRIPT_DIR
    dialog_keys = {
        str(row.get("dialogKey") or "") for row in rows if row.get("dialogKey")
    }
    if not dialog_keys:
        empty = join_parent_dialog_activation_routes(
            rows,
            {"summary": {}, "headerRows": []},
            {},
            {},
            {},
            gameassembly=gameassembly,
            metadata=metadata,
            mission_runtime_root=story_context.MRA_DIR,
        )
        empty["source"] = {
            "candidateLevels": [],
            "levelScriptRoot": repo_path(levelscript_root),
            "runtimeSlotMappingId": "",
        }
        return empty
    if use_default_levelscript_root:
        playback_index = level_bindings.build_levelscript_native_story_playback_index()
    else:
        playback_index = {
            story_key: [
                occurrence
                for occurrence in occurrences
                if occurrence.get("actionName") and occurrence.get("recordClass")
            ]
            for story_key, occurrences in (
                level_bindings.build_levelscript_action_story_occurrences(
                    levelscript_root
                ).items()
            )
        }
    levels = discover_parent_dialog_candidate_levels(dialog_keys, levelscript_root)
    header_report = header_audit.build_report(SimpleNamespace(
        level=levels,
        mapping=header_audit.DEFAULT_MAPPING,
        chain_preview=64,
        samples_per_event=0,
        play_samples=0,
        unresolved_samples=0,
    ))
    script_pairs = {
        (str(occurrence.get("levelId") or ""), str(occurrence.get("scriptId") or ""))
        for dialog_key in dialog_keys
        for occurrence in playback_index.get(dialog_key) or []
        if occurrence.get("recordClass") == "play_dialog"
    }
    mission_runtime_ids = {
        path.stem
        for path in story_context.MRA_DIR.glob("*.json")
        if not path.stem.endswith("_meta")
    }
    mission_hosts = level_bindings.build_leveldata_mission_script_host_index(
        script_pairs, mission_runtime_ids
    )
    mission_area_hosts = level_bindings.build_leveldata_mission_area_script_host_index(
        script_pairs
    )
    tracking_mission_ids = {
        str(mission_id)
        for host in mission_hosts.values()
        for mission_id in host.get("hostMissionIds") or []
        if mission_id
    }
    mission_tracking_rows = (
        level_bindings.build_resolved_mission_tracking_context_rows(
            tracking_mission_ids,
            mission_runtime_root=story_context.MRA_DIR,
        )
        if tracking_mission_ids
        else []
    )
    result = join_parent_dialog_activation_routes(
        rows,
        header_report,
        playback_index,
        mission_hosts,
        mission_area_hosts,
        gameassembly=gameassembly,
        metadata=metadata,
        mission_runtime_root=story_context.MRA_DIR,
        mission_tracking_rows=mission_tracking_rows,
        tracking_context_matcher=(
            level_bindings.match_tracking_point_inside_leader_trigger_context
        ),
    )
    result["source"] = {
        "candidateLevels": levels,
        "levelScriptRoot": repo_path(levelscript_root),
        "runtimeSlotMappingId": (
            (header_report.get("summary") or {}).get("runtimeSlotMappingId")
        ),
    }
    return result


def enrich_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched = []
    for row in rows:
        related = [
            original_file_record(str(row[field]), role)
            for field, role in (
                ("assetPath", "text_playable_asset"),
                ("trackPath", "timeline_track"),
                ("rootPath", "timeline_actor_root"),
            )
        ]
        compact = dict(row)
        for field_name in ("assetPathId", "trackPathId", "rootPathId"):
            if isinstance(compact.get(field_name), int):
                compact[field_name] = str(compact[field_name])
        compact["runtimePresentation"] = True
        compact["missionOwnership"] = False
        compact["questActivation"] = False
        compact["branchSelection"] = False
        compact["relatedOriginalFiles"] = related
        enriched.append(compact)
    return enriched


class ExportedObjectResolver:
    """Resolve extracted Unity objects by exact serialized-file/PathID identity."""

    def __init__(self, extract_dir: Path) -> None:
        self.extract_dir = extract_dir
        self.paths_by_suffix: dict[str, list[Path]] = defaultdict(list)
        self.payload_cache: dict[Path, dict[str, Any]] = {}
        suffix_re = re.compile(r"_p([0-9A-Fa-f]{16})\.json$")
        for type_name in ("MonoBehaviour", "PlayableDirector"):
            for path in extract_dir.glob(f"*/{type_name}/*.json"):
                match = suffix_re.search(path.name)
                if match:
                    self.paths_by_suffix[match.group(1).upper()].append(path)

    def load(self, path: Path) -> dict[str, Any]:
        if path not in self.payload_cache:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                raise RuntimeError(f"expected object JSON: {path}")
            self.payload_cache[path] = payload
        return self.payload_cache[path]

    def resolve(
        self,
        source_file: str,
        path_id: int,
    ) -> tuple[Path, dict[str, Any]] | None:
        suffix = f"{path_id & 0xFFFFFFFFFFFFFFFF:016X}"
        matches = []
        for path in self.paths_by_suffix.get(suffix, []):
            payload = self.load(path)
            meta = payload.get("$animestudio") or {}
            if (
                str(meta.get("sourceFile") or "") == source_file
                and int(meta.get("pathId") or 0) == path_id
            ):
                matches.append((path, payload))
        if len(matches) > 1:
            raise RuntimeError(
                "validator=timeline_embedded_story_runtime failed: "
                "gate=unique_exported_object_identity; "
                f"source={source_file}; expected=1; actual={len(matches)}; "
                f"pathId={path_id}"
            )
        return matches[0] if matches else None


def resolved_pointer_identity(
    payload: dict[str, Any],
    pointer_path: str,
) -> tuple[str, int] | None:
    meta = payload.get("$animestudio") or {}
    for pointer in meta.get("pptrReferences") or []:
        if (
            isinstance(pointer, dict)
            and pointer.get("path") == pointer_path
            and str(pointer.get("resolutionStatus") or "").startswith("resolved")
        ):
            source_file = str(
                pointer.get("targetSourceFile")
                or pointer.get("expectedTargetSourceFile")
                or meta.get("sourceFile")
                or ""
            )
            path_id = pointer.get("targetPathId", pointer.get("pathId"))
            if source_file and isinstance(path_id, int) and path_id:
                return source_file, path_id
    return None


def director_records(
    resolver: ExportedObjectResolver,
) -> list[dict[str, Any]]:
    records = []
    for path in sorted(resolver.extract_dir.glob("*/PlayableDirector/*.json")):
        payload = resolver.load(path)
        meta = payload.get("$animestudio") or {}
        playable = resolved_pointer_identity(payload, "$.m_PlayableAsset")
        game_object = resolved_pointer_identity(payload, "$.m_GameObject")
        if playable is None or game_object is None:
            continue
        exposed = []
        references = ((payload.get("m_ExposedReferences") or {}).get("m_References") or [])
        for index, item in enumerate(references):
            if not isinstance(item, dict):
                continue
            key = str(item.get("Key") or "")
            pointer = resolved_pointer_identity(
                payload,
                f"$.m_ExposedReferences.m_References[{index}].second",
            )
            if pointer is None:
                value = item.get("Value") or {}
                path_id = value.get("m_PathID") if isinstance(value, dict) else None
                if isinstance(path_id, int) and path_id and int(value.get("m_FileID") or 0) == 0:
                    pointer = (str(meta.get("sourceFile") or ""), path_id)
            if key and pointer is not None:
                exposed.append({"key": key, "target": pointer})
        records.append({
            "path": path,
            "payload": payload,
            "identity": (str(meta.get("sourceFile") or ""), int(meta.get("pathId") or 0)),
            "gameObject": game_object,
            "playableAsset": playable,
            "exposedReferences": exposed,
            "sourceOffset": int(meta.get("sourceOffset") or 0),
        })
    return records


def same_serialized_file_component_paths(
    resolver: ExportedObjectResolver,
    directors: list[dict[str, Any]],
) -> list[Path]:
    """Use extraction provenance to bound component scans to exact files."""
    wanted_by_chunk: dict[Path, dict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for director in directors:
        chunk_root = director["path"].parent.parent
        wanted_by_chunk[chunk_root][director["sourceOffset"]].add(
            director["identity"][0]
        )
    candidates: set[Path] = set()
    for chunk_root, wanted_offsets in wanted_by_chunk.items():
        filter_path = chunk_root / "filter_data.json"
        try:
            inventory = json.loads(filter_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                "validator=timeline_embedded_story_runtime failed: "
                "gate=timeline_filter_inventory; "
                f"source={filter_path}; expected=valid JSON; actual={exc}"
            ) from exc
        for row in inventory if isinstance(inventory, list) else []:
            if not isinstance(row, dict) or row.get("Type") != "MonoBehaviour":
                continue
            offset = row.get("Offset")
            path_id = row.get("PathID")
            if not isinstance(offset, int) or not isinstance(path_id, int):
                continue
            for source_file in wanted_offsets.get(offset, set()):
                resolved = resolver.resolve(source_file, path_id)
                if resolved is not None:
                    candidates.add(resolved[0])
    return sorted(candidates)


def cutscene_root_records(
    resolver: ExportedObjectResolver,
    wanted_directors: set[tuple[str, int]],
    candidate_paths: list[Path],
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    roots: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    director_tokens = tuple(str(path_id).encode("ascii") for _, path_id in wanted_directors)
    if not director_tokens:
        return roots
    paths = candidate_paths

    def is_candidate(path: Path) -> bool:
        try:
            raw = path.read_bytes()
        except OSError:
            return False
        return (
            b'"_timelineName"' in raw
            and b'"_director"' in raw
            and any(token in raw for token in director_tokens)
        )

    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as pool:
        candidates = [
            path for path, matched in zip(paths, pool.map(is_candidate, paths))
            if matched
        ]
    for path in candidates:
        payload = resolver.load(path)
        timeline_name = payload.get("_timelineName")
        director = resolved_pointer_identity(payload, "$._director")
        if not isinstance(timeline_name, str) or not timeline_name or director not in wanted_directors:
            continue
        roots[director].append({
            "path": path,
            "payload": payload,
            "timelineName": timeline_name,
            "identity": (
                str((payload.get("$animestudio") or {}).get("sourceFile") or ""),
                int((payload.get("$animestudio") or {}).get("pathId") or 0),
            ),
        })
    return roots


def parent_control_clips(
    resolver: ExportedObjectResolver,
    parent_director: dict[str, Any],
    exposed_key: str,
) -> list[dict[str, Any]]:
    parent_timeline_identity = parent_director["playableAsset"]
    resolved_timeline = resolver.resolve(*parent_timeline_identity)
    if resolved_timeline is None:
        return []
    timeline_path, timeline_payload = resolved_timeline
    matches = []
    for track_index, _ in enumerate(timeline_payload.get("m_Tracks") or []):
        track_identity = resolved_pointer_identity(
            timeline_payload, f"$.m_Tracks[{track_index}]"
        )
        if track_identity is None:
            continue
        resolved_track = resolver.resolve(*track_identity)
        if resolved_track is None:
            continue
        track_path, track_payload = resolved_track
        for clip_index, clip in enumerate(track_payload.get("m_Clips") or []):
            if not isinstance(clip, dict):
                continue
            asset_identity = resolved_pointer_identity(
                track_payload, f"$.m_Clips[{clip_index}].m_Asset"
            )
            if asset_identity is None:
                continue
            resolved_asset = resolver.resolve(*asset_identity)
            if resolved_asset is None:
                continue
            asset_path, asset_payload = resolved_asset
            source = asset_payload.get("sourceGameObject") or {}
            if (
                str(source.get("exposedName") or "") != exposed_key
                or int(asset_payload.get("updateDirector") or 0) != 1
            ):
                continue
            matches.append({
                "parentTimelineIdentity": parent_timeline_identity,
                "parentTimelinePath": timeline_path,
                "trackIdentity": track_identity,
                "trackPath": track_path,
                "controlAssetIdentity": asset_identity,
                "controlAssetPath": asset_path,
                "clipIndex": clip_index,
                "clipStart": clip.get("m_Start"),
                "clipDuration": clip.get("m_Duration"),
                "clipOptionIndex": clip.get("optionIndex"),
                "useAutoBinding": bool(asset_payload.get("useAutoBinding")),
                "autoBindingPath": str(asset_payload.get("autoBindingPath") or ""),
                "directorControlPath": str(asset_payload.get("directorControlPath") or ""),
                "active": bool(asset_payload.get("active")),
            })
    return matches


def recover_director_hosts(
    rows: list[dict[str, Any]],
    extract_dir: Path,
) -> dict[str, Any]:
    """Close exact reverse PPtrs through director and ControlPlayableAsset data."""
    resolver = ExportedObjectResolver(extract_dir)
    directors = director_records(resolver)
    targets: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in rows:
        targets[(str(row["sourceFile"]), int(row["rootPathId"]))].add(str(row["key"]))
    child_directors = [row for row in directors if row["playableAsset"] in targets]
    child_by_game_object: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in child_directors:
        child_by_game_object[row["gameObject"]].append(row)

    parent_candidates = []
    for parent in directors:
        for exposed in parent["exposedReferences"]:
            children = child_by_game_object.get(exposed["target"], [])
            if not children:
                continue
            controls = parent_control_clips(resolver, parent, exposed["key"])
            for child in children:
                for control in controls:
                    parent_candidates.append({
                        "child": child,
                        "parent": parent,
                        "exposed": exposed,
                        "control": control,
                    })

    wanted_directors = {
        row["identity"] for row in child_directors
    } | {
        row["parent"]["identity"] for row in parent_candidates
    }
    relevant_directors = [
        row for row in directors if row["identity"] in wanted_directors
    ]
    roots_by_director = cutscene_root_records(
        resolver,
        wanted_directors,
        same_serialized_file_component_paths(resolver, relevant_directors),
    )
    host_rows = []
    for child in child_directors:
        story_keys = sorted(targets[child["playableAsset"]])
        direct_roots = roots_by_director.get(child["identity"], [])
        related = [original_file_record(str(child["path"]), "story_playable_director")]
        for root in direct_roots:
            related.append(original_file_record(str(root["path"]), "cutscene_root"))
        host_rows.append({
            "storyKeys": story_keys,
            "timelineIdentity": {
                "sourceFile": child["playableAsset"][0],
                "pathId": str(child["playableAsset"][1]),
            },
            "directorIdentity": {
                "sourceFile": child["identity"][0],
                "pathId": str(child["identity"][1]),
            },
            "directorGameObjectIdentity": {
                "sourceFile": child["gameObject"][0],
                "pathId": str(child["gameObject"][1]),
            },
            "relation": (
                "cutscene_root_director_playback"
                if direct_roots else "playable_director_instance"
            ),
            "cutsceneRoots": [
                {
                    "timelineName": root["timelineName"],
                    "sourceFile": root["identity"][0],
                    "pathId": str(root["identity"][1]),
                }
                for root in direct_roots
            ],
            "controlChains": [],
            "relatedOriginalFiles": related,
        })

    host_by_child = {
        (row["directorIdentity"]["sourceFile"], int(row["directorIdentity"]["pathId"])): row
        for row in host_rows
    }
    for candidate in parent_candidates:
        child = candidate["child"]
        parent = candidate["parent"]
        control = candidate["control"]
        parent_roots = roots_by_director.get(parent["identity"], [])
        related_paths = (
            (parent["path"], "parent_playable_director"),
            (control["parentTimelinePath"], "parent_timeline_asset"),
            (control["trackPath"], "parent_control_track"),
            (control["controlAssetPath"], "control_playable_asset"),
        )
        chain_files = [original_file_record(str(path), role) for path, role in related_paths]
        chain_files.extend(
            original_file_record(str(root["path"]), "cutscene_root")
            for root in parent_roots
        )
        chain = {
            "relation": "exposed_reference_controlled_director_playback",
            "exposedReferenceKey": candidate["exposed"]["key"],
            "resolvedGameObjectIdentity": {
                "sourceFile": candidate["exposed"]["target"][0],
                "pathId": str(candidate["exposed"]["target"][1]),
            },
            "parentDirectorIdentity": {
                "sourceFile": parent["identity"][0],
                "pathId": str(parent["identity"][1]),
            },
            "parentTimelineIdentity": {
                "sourceFile": control["parentTimelineIdentity"][0],
                "pathId": str(control["parentTimelineIdentity"][1]),
            },
            "controlTrackIdentity": {
                "sourceFile": control["trackIdentity"][0],
                "pathId": str(control["trackIdentity"][1]),
            },
            "controlAssetIdentity": {
                "sourceFile": control["controlAssetIdentity"][0],
                "pathId": str(control["controlAssetIdentity"][1]),
            },
            "clipIndex": control["clipIndex"],
            "clipStart": control["clipStart"],
            "clipDuration": control["clipDuration"],
            "clipOptionIndex": control["clipOptionIndex"],
            "useAutoBinding": control["useAutoBinding"],
            "autoBindingPath": control["autoBindingPath"],
            "directorControlPath": control["directorControlPath"],
            "active": control["active"],
            "cutsceneRoots": [
                {
                    "timelineName": root["timelineName"],
                    "sourceFile": root["identity"][0],
                    "pathId": str(root["identity"][1]),
                }
                for root in parent_roots
            ],
            "relatedOriginalFiles": chain_files,
            "missionOwnership": False,
            "branchSelection": False,
            "crossTimelineOrder": False,
        }
        host = host_by_child[child["identity"]]
        host["controlChains"].append(chain)
        host["relation"] = "exposed_reference_controlled_director_playback"
        known = {(file["role"], file["path"]) for file in host["relatedOriginalFiles"]}
        for file in chain_files:
            identity = (file["role"], file["path"])
            if identity not in known:
                host["relatedOriginalFiles"].append(file)
                known.add(identity)

    for host in host_rows:
        host["controlChains"].sort(key=lambda row: (
            str(row["parentDirectorIdentity"]["sourceFile"]),
            int(row["parentDirectorIdentity"]["pathId"]),
            int(row["clipIndex"]),
        ))
        host["relatedOriginalFiles"].sort(key=lambda row: (row["role"], row["path"]))
    host_rows.sort(key=lambda row: (
        row["storyKeys"], row["directorIdentity"]["sourceFile"],
        int(row["directorIdentity"]["pathId"]),
    ))
    roots_with_directors = {row["playableAsset"] for row in child_directors}
    missing_roots = [
        {
            "sourceFile": source_file,
            "pathId": str(path_id),
            "storyKeys": sorted(targets[(source_file, path_id)]),
        }
        for source_file, path_id in sorted(targets)
        if (source_file, path_id) not in roots_with_directors
    ]
    return {
        "validation": {
            "status": "validated",
            "missingDirectorRoots": missing_roots,
        },
        "rows": host_rows,
        "counts": {
            "timelineRoots": len(targets),
            "rootsWithDirectorInstances": len(roots_with_directors),
            "rootsWithoutDirectorInstances": len(missing_roots),
            "directorInstances": len(host_rows),
            "directCutsceneRootInstances": sum(
                bool(row["cutsceneRoots"]) for row in host_rows
            ),
            "controlledDirectorInstances": sum(
                bool(row["controlChains"]) for row in host_rows
            ),
            "controlChains": sum(len(row["controlChains"]) for row in host_rows),
            "storyKeysWithDirectorInstances": len({
                key for row in host_rows for key in row["storyKeys"]
            }),
        },
        "evidenceBoundary": {
            "playableDirectorReferencesTimeline": True,
            "exposedReferenceResolvesDirectorGameObject": True,
            "controlPlayableTargetsResolvedGameObject": True,
            "runtimeDirectorControl": True,
            "cutsceneRootScope": "same_serialized_file_as_director",
            "missionOwnership": False,
            "questActivation": False,
            "branchSelection": False,
            "crossTimelineOrder": False,
        },
    }


def local_order_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(
            row.get("sourceFile"), row.get("timeline"), row.get("trackPathId"),
            row.get("clipOptionIndex"),
        )].append(row)
    edges: dict[tuple[Any, ...], dict[str, Any]] = {}
    for group_key, group_rows in groups.items():
        ordered = sorted(group_rows, key=lambda row: (
            float(row.get("clipStart") or 0), int(row.get("clipIndex") or 0),
            str(row.get("textId") or ""),
        ))
        for left, right in zip(ordered, ordered[1:]):
            if left.get("key") == right.get("key"):
                continue
            left_end = float(left.get("clipStart") or 0) + float(left.get("clipDuration") or 0)
            right_start = float(right.get("clipStart") or 0)
            if left_end > right_start:
                continue
            identity = (left.get("key"), right.get("key"), *group_key)
            edges[identity] = {
                "from": left.get("key"),
                "to": right.get("key"),
                "timeline": left.get("timeline"),
                "sourceFile": left.get("sourceFile"),
                "trackPathId": left.get("trackPathId"),
                "optionIndex": left.get("clipOptionIndex"),
                "fromClipStart": left.get("clipStart"),
                "fromClipDuration": left.get("clipDuration"),
                "toClipStart": right.get("clipStart"),
                "evidence": "exact_non_overlapping_serialized_clip_time",
                "scope": "same_timeline_track_option_lane",
                "missionOrder": False,
            }
    return sorted(edges.values(), key=lambda row: (
        str(row["timeline"]), float(row["fromClipStart"] or 0), str(row["from"])
    ))


def mapper_args(
    args: argparse.Namespace,
    metadata_path: Path,
    catalog_path: Path,
) -> SimpleNamespace:
    return SimpleNamespace(
        gameassembly=args.gameassembly,
        metadata=metadata_path,
        catalog=catalog_path,
        code_registration=args.code_registration,
        # Timeline control helpers call generic PlayableExtensions methods.
        # Excluding generic instantiations would turn a mapped retail call into
        # a false unresolved edge and must fail closed instead of weakening the
        # runtime contract.
        include_generic_instantiations=True,
        metadata_registration="",
        head_bytes=32,
        max_scan_bytes=0x6000,
        arg_context_window=96,
        body_summary_method_regex=r".*",
        body_summary_max_instructions=500,
        include_unresolved_calls=True,
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if not args.gameassembly.is_file() or not args.metadata.is_file():
        raise RuntimeError(
            "validator=timeline_embedded_story_runtime failed: gate=installed_sources "
            f"expected=GameAssembly+metadata actual={args.gameassembly},{args.metadata}"
        )
    catalog_module = load_module(
        "endfield_timeline_text_catalog",
        TOOLS / "catalog_option_flow_metadata.py",
    )
    mapper = load_module(
        "endfield_timeline_text_mapper",
        TOOLS / "map_body_targets_to_gameassembly.py",
    )
    metadata = catalog_module.Metadata(args.metadata)
    catalog = catalog_module.build_catalog(
        metadata,
        re.compile(r"PlayableAsset$"),
        re.compile(r"(?!)"),
        re.compile(r"^(?:CreatePlayable|_GetText)$"),
        re.compile(r"PlayableAsset$"),
        re.compile(r"Beyond", re.IGNORECASE),
        only_focus=False,
        include_all_members=True,
        body_context=0,
    )
    control_catalog = catalog_module.build_catalog(
        metadata,
        re.compile(r"(?:ControlPlayableAsset|CutsceneRootComponent)$"),
        re.compile(r"(?!)"),
        re.compile(
            r"^(?:CreatePlayable|ResolveSourceGameObject|GetControllableDirectors|"
            r"SearchHierarchyAndConnectDirector|ConnectPlayablesToMixer|"
            r"ConnectMixerAndPlayable|CreateActivationPlayable|get_topDirector)$"
        ),
        re.compile(r"(?:ControlPlayableAsset|CutsceneRootComponent)$"),
        re.compile(r".*"),
        only_focus=False,
        include_all_members=True,
        body_context=0,
    )
    npc_proxy_type_pattern = re.compile(
        r"^Beyond\.Gameplay\.Core\."
        r"(?:NpcRuntimeProxyExData|NpcInteractComponent|NpcProxy)$"
    )
    npc_proxy_catalog = catalog_module.build_catalog(
        metadata,
        npc_proxy_type_pattern,
        re.compile(r"(?!)"),
        re.compile(
            r"^(?:ChangeActiveCondition|get_activeCondIndex|"
            r"_TryGetNpcProxyInteractDialogId|_IsMissionConflict)$"
        ),
        npc_proxy_type_pattern,
        re.compile(r".*"),
        only_focus=False,
        include_all_members=True,
        body_context=0,
    )
    wanted_npc_methods = {
        ("Beyond.Gameplay.Core.NpcProxy", "ChangeActiveCondition"),
        ("Beyond.Gameplay.Core.NpcProxy", "get_activeCondIndex"),
        (
            "Beyond.Gameplay.Core.NpcInteractComponent",
            "_TryGetNpcProxyInteractDialogId",
        ),
        ("Beyond.Gameplay.Core.NpcProxy", "_IsMissionConflict"),
    }
    npc_proxy_catalog["bodyTargets"] = [
        row for row in npc_proxy_catalog.get("bodyTargets") or []
        if (str(row.get("type") or ""), str(row.get("method") or ""))
        in wanted_npc_methods
    ]
    # Map the control and NPC methods in one native pass. The analyzers select
    # their own typed targets, so adding a new carrier family stays a catalog
    # operation rather than a per-object address patch.
    combined_targets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in [
        *(control_catalog.get("bodyTargets") or []),
        *(npc_proxy_catalog.get("bodyTargets") or []),
    ]:
        identity = (
            str(row.get("type") or ""),
            str(row.get("method") or ""),
            str(row.get("token") or ""),
        )
        combined_targets[identity] = row
    control_catalog["bodyTargets"] = list(combined_targets.values())
    with tempfile.TemporaryDirectory(prefix="endfield-timeline-text-") as temp:
        catalog_path = Path(temp) / "catalog.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        body_map = mapper.build_report(mapper_args(args, args.metadata, catalog_path))
        control_catalog_path = Path(temp) / "control_catalog.json"
        control_catalog_path.write_text(
            json.dumps(control_catalog), encoding="utf-8"
        )
        control_body_map = mapper.build_report(
            mapper_args(args, args.metadata, control_catalog_path)
        )
    contract = analyze_runtime_contract(catalog, body_map)
    if contract["validation"]["status"] != "validated":
        failure = (contract["validation"]["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline embedded Story runtime validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )
    control_contract = analyze_control_runtime_contract(
        control_catalog, control_body_map
    )
    if control_contract["validation"]["status"] != "validated":
        failure = (control_contract["validation"]["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline controlled-director runtime validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )
    npc_proxy_contract = analyze_npc_proxy_dialog_runtime_contract(
        npc_proxy_catalog,
        control_body_map,
    )
    if npc_proxy_contract["validation"]["status"] != "validated":
        failure = (npc_proxy_contract["validation"]["failures"] or [{}])[0]
        raise RuntimeError(
            "NPC proxy dialog runtime validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )

    line_index, line_validation = story_line_index(args.story_root)
    if line_validation["status"] != "validated":
        failure = (line_validation["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline embedded Story line index validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )

    try:
        from scripts.story_builder.timeline_recovery import (
            recover_timeline_text_attachments,
        )
    except ModuleNotFoundError:
        from story_builder.timeline_recovery import recover_timeline_text_attachments
    families = tuple(
        str(row["serializedAssetType"]) for row in contract["families"]
    )
    rows = enrich_rows(recover_timeline_text_attachments(
        line_id_to_story_key=line_index,
        playable_asset_type_names=families,
    ))
    director_hosts = recover_director_hosts(rows, args.extract_dir)
    hosts_by_timeline: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for host in director_hosts["rows"]:
        identity = host["timelineIdentity"]
        hosts_by_timeline[(
            str(identity["sourceFile"]), str(identity["pathId"])
        )].append(host)
    for row in rows:
        hosts = [
            host for host in hosts_by_timeline.get(
                (str(row["sourceFile"]), str(row["rootPathId"])), []
            )
            if row["key"] in host["storyKeys"]
        ]
        row["directorHosts"] = hosts
        row["directorPlaybackComposition"] = any(
            host["relation"] != "playable_director_instance" for host in hosts
        )
        known_files = {
            (file["role"], file["path"])
            for file in row["relatedOriginalFiles"]
        }
        for host in hosts:
            for file in host["relatedOriginalFiles"]:
                identity = (file["role"], file["path"])
                if identity not in known_files:
                    row["relatedOriginalFiles"].append(file)
                    known_files.add(identity)
        row["relatedOriginalFiles"].sort(key=lambda file: (file["role"], file["path"]))
    activation = recover_parent_dialog_activation_routes(
        rows,
        gameassembly=args.gameassembly,
        metadata=args.metadata,
    )
    if activation["validation"]["status"] != "validated":
        failure = (activation["validation"]["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline parent-dialog activation validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )
    configuration = recover_parent_dialog_configuration_contexts(
        rows,
        npc_proxy_contract,
        gameassembly=args.gameassembly,
        metadata=args.metadata,
    )
    if configuration["validation"]["status"] != "validated":
        failure = (configuration["validation"]["failures"] or [{}])[0]
        raise RuntimeError(
            "timeline parent-dialog configuration validation failed: "
            f"validator={failure.get('validator')}; gate={failure.get('gate')}; "
            f"source={failure.get('sourceFile')}; expected={failure.get('expected')!r}; "
            f"actual={failure.get('actual')!r}"
        )
    edges = local_order_edges(rows)
    return {
        "schemaVersion": "timelineEmbeddedStoryRuntimeAudit.v6",
        "source": {
            "gameAssembly": str(args.gameassembly),
            "gameAssemblySha256": sha256_path(args.gameassembly),
            "metadata": str(args.metadata),
            "metadataSha256": sha256_path(args.metadata),
            "codeRegistration": body_map.get("codeRegistration"),
        },
        "validation": {
            "status": "validated",
            "runtimeContract": contract["validation"],
            "controlRuntimeContract": control_contract["validation"],
            "directorHosts": director_hosts["validation"],
            "parentDialogActivation": activation["validation"],
            "parentDialogConfiguration": configuration["validation"],
            "storyLineIndex": line_validation,
        },
        "runtimeContract": contract,
        "controlRuntimeContract": control_contract,
        "directorHosts": director_hosts,
        "parentDialogActivation": activation,
        "activationRoutes": activation["routes"],
        "parentDialogConfiguration": configuration,
        "configurationContexts": configuration["contexts"],
        "counts": {
            "runtimeCarrierFamilies": len(contract["families"]),
            "serializedClipRows": len(rows),
            "uniqueStoryKeys": len({row["key"] for row in rows}),
            "timelines": len({row["timeline"] for row in rows}),
            "localOrderEdges": len(edges),
            "directorInstances": director_hosts["counts"]["directorInstances"],
            "controlledDirectorInstances": (
                director_hosts["counts"]["controlledDirectorInstances"]
            ),
            "controlChains": director_hosts["counts"]["controlChains"],
            "parentDialogActivationRoutes": activation["counts"]["exactActivationRoutes"],
            "parentDialogsWithExactActivation": (
                activation["counts"]["parentDialogsWithExactActivation"]
            ),
            "storyKeysWithExactActivation": (
                activation["counts"]["storyKeysWithExactActivation"]
            ),
            "missionOwnershipEdges": activation["counts"]["missionOwnedRoutes"],
            "questSpatialContextRoutes": (
                activation["counts"]["routesWithQuestSpatialContext"]
            ),
            "questSpatialContextRows": (
                activation["counts"]["questSpatialContextRows"]
            ),
            "questSpatialContextQuestIds": (
                activation["counts"]["questSpatialContextQuestIds"]
            ),
            "parentDialogConfigurationContexts": (
                configuration["counts"]["configurationContexts"]
            ),
            "parentDialogsWithConfigurationContext": (
                configuration["counts"]["parentDialogsWithConfigurationContext"]
            ),
            "questNavigationContexts": (
                configuration["counts"]["questNavigationContexts"]
            ),
            "branchSelectionEdges": 0,
            "parallelFanoutActivationRoutes": sum(
                bool(route.get("parallelFanout")) for route in activation["routes"]
            ),
            "conditionalActivationRoutes": sum(
                bool(route.get("conditionalActivation"))
                for route in activation["routes"]
            ),
        },
        "rows": rows,
        "localOrderEdges": edges,
        "evidenceBoundary": {
            "runtimePresentation": True,
            "serializedTimelineContainment": True,
            "sameTrackNonOverlappingClipOrder": True,
            "playableDirectorInstances": True,
            "exposedReferenceControlChains": True,
            "parentDialogEventActionChains": True,
            "typedBranchSemantics": True,
            "parallelFanoutSiblingOrder": False,
            "conditionalRouteSelectionObserved": False,
            "missionOwnership": "unique_validated_leveldata_hosts_only",
            "questSpatialContext": (
                "typed_tracking_point_inside_exact_selected_trigger_shape_only"
            ),
            "questActivation": False,
            "missionConfigurationContext": (
                "exact_npc_proxy_ex_mission_dialog_pair_only"
            ),
            "questNavigationContext": (
                "unique_typed_same_mission_npc_proxy_tracking_only"
            ),
            "branchSelection": False,
            "crossTimelineOrder": False,
            "ocrOrManualOverrideUsed": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = [
        "# Timeline-Embedded Story Runtime Audit",
        "",
        f"- status: `{report['validation']['status']}`",
        f"- runtime carrier families: `{counts['runtimeCarrierFamilies']}`",
        f"- exact serialized clip rows: `{counts['serializedClipRows']}`",
        f"- unique Story keys: `{counts['uniqueStoryKeys']}`",
        f"- Timeline roots: `{counts['timelines']}`",
        f"- proven same-track local-order edges: `{counts['localOrderEdges']}`",
        f"- exact PlayableDirector instances: `{counts['directorInstances']}`",
        "- exposed-reference controlled director instances: "
        f"`{counts['controlledDirectorInstances']}`",
        f"- exact nested control chains: `{counts['controlChains']}`",
        "- exact parent-dialog event/action activation routes: "
        f"`{counts['parentDialogActivationRoutes']}`",
        "- parent dialogs with exact activation: "
        f"`{counts['parentDialogsWithExactActivation']}`",
        "- Story keys reached through exact parent activation: "
        f"`{counts['storyKeysWithExactActivation']}`",
        f"- unique mission-shell ownership edges: `{counts['missionOwnershipEdges']}`",
        "- parent routes with exact quest spatial context: "
        f"`{counts['questSpatialContextRoutes']}`",
        "- exact quest tracking-point containment rows: "
        f"`{counts['questSpatialContextRows']}`",
        "- distinct spatial-context quest ids: "
        f"`{counts['questSpatialContextQuestIds']}`",
        f"- GameAssembly SHA-256: `{report['source']['gameAssemblySha256']}`",
        f"- metadata SHA-256: `{report['source']['metadataSha256']}`",
        "",
        "## General Runtime Contract",
        "",
    ]
    for family in report["runtimeContract"]["families"]:
        lines.append(
            f"- `{family['type']}` fields "
            f"{', '.join(f'`{value}`' for value in family['textIdFields'])}; "
            f"CreatePlayable `{family['createPlayable']['va']}` -> "
            f"{', '.join(f'`{value}`' for value in family['createPlayable']['behaviourInitializers'])}"
        )
    control = report["controlRuntimeContract"]["controlPlayableAsset"]
    lines.append(
        f"- `{control['type']}` CreatePlayable "
        f"`{control['methods']['CreatePlayable']['va']}` resolves the source "
        "GameObject, discovers/directs PlayableDirectors, and connects them to "
        "the playable mixer."
    )
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "The installed binary proves that these serialized text fields are resolved and "
        "passed into live Timeline behaviours. Exact PathID links prove the playable, "
        "clip, track, Actor root, PlayableDirector instances, and any published "
        "ExposedReference/ControlPlayableAsset chain. An active LevelScript event-to-action "
        "path can prove parent-dialog playback; a unique validated LevelData member-22 host "
        "can additionally prove only the mission shell. Non-overlapping clip times prove only "
        "local order inside one track and option lane. These joins do not prove the quest "
        "activator or any order across Timeline roots. A typed conditional edge proves that "
        "the authored route exists but not that runtime selected it; Split siblings remain "
        "unordered. OCR and manual "
        "overrides are not used.",
        "",
        "## Recovered Rows",
        "",
    ])
    for row in report["rows"]:
        lines.append(
            f"- `{row['key']}` / `{row['textId']}` in `{row['timeline']}` at "
            f"`{row['clipStart']}`s for `{row['clipDuration']}`s; "
            f"dialog `{row.get('dialogKey') or 'unresolved'}`; CAB `{row['sourceFile']}`"
        )
    lines.extend(["", "## Controlled Director Hosts", ""])
    for host in report["directorHosts"]["rows"]:
        lines.append(
            f"- `{', '.join(host['storyKeys'])}`: `{host['relation']}`; "
            f"director `{host['directorIdentity']['sourceFile']}` / "
            f"`{host['directorIdentity']['pathId']}`; "
            f"control chains `{len(host['controlChains'])}`"
        )
    lines.extend(["", "## Parent Dialog Activation", ""])
    for route in report.get("activationRoutes") or []:
        missions = ", ".join(route.get("missionShellIds") or []) or "unresolved"
        decisions = "; ".join(
            f"{decision.get('controlKind')}: {decision.get('selectedEdge')}"
            for decision in route.get("controlDecisions") or []
        ) or "linear"
        lines.append(
            f"- `{route['headerName']}` in `{route['levelId']}/{route['scriptId']}` "
            f"-> `#{route['playActionLocalId']}` `{route['dialogKey']}` -> "
            f"`{', '.join(route['storyKeys'])}`; mission shell `{missions}`; "
            f"typed control `{decisions}`; quest activation unresolved"
        )
    for unresolved in (
        report.get("parentDialogActivation", {}).get("unresolvedParentDialogs") or []
    ):
        lines.append(
            f"- unresolved `{unresolved.get('dialogKey')}`: "
            f"`{unresolved.get('reason')}`"
        )
    lines.extend(["", "## Parent Dialog Configuration Context", ""])
    for context in report.get("configurationContexts") or []:
        quests = ", ".join(context.get("candidateQuestIds") or []) or "unresolved"
        lines.append(
            f"- `{context['dialogKey']}` -> mission `{context['missionId']}` / "
            f"proxy `{context['npcProxyId']}`; quest navigation `{quests}`; "
            "parent playback, activation, branch selection, and Story order unresolved"
        )
    lines.append("")
    return "\n".join(lines)


def build_default_report() -> dict[str, Any]:
    """Build the canonical current-install audit for pipeline integration."""
    return build_report(SimpleNamespace(
        gameassembly=DEFAULT_GAMEASSEMBLY,
        metadata=DEFAULT_METADATA,
        story_root=DEFAULT_STORY_ROOT,
        extract_dir=DEFAULT_EXTRACT_DIR,
        code_registration="0x18b9217d0",
    ))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--story-root", type=Path, default=DEFAULT_STORY_ROOT)
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--code-registration", default="0x18b9217d0")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    counts = report["counts"]
    print(
        "Timeline embedded Story runtime audit: "
        f"{counts['uniqueStoryKeys']} Story keys, "
        f"{counts['serializedClipRows']} clips, "
        f"{counts['localOrderEdges']} local-order edges -> {args.json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
