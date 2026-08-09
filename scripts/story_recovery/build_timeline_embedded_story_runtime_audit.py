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


def join_parent_dialog_activation_routes(
    rows: list[dict[str, Any]],
    header_report: dict[str, Any],
    mission_hosts: dict[tuple[str, str], dict[str, Any]],
    mission_area_hosts: dict[tuple[str, str], dict[str, Any]],
    *,
    gameassembly: Path,
    metadata: Path,
    mission_runtime_root: Path,
) -> dict[str, Any]:
    """Join native event roots to Timeline parents by exact dialog identity.

    The general shape is:

    ``active header slot -> nextId action chain -> StartDialog(dialog key)``
    ``-> dialog registry Timeline -> PlayableDirector/ControlPlayableAsset``.

    A fully decoded LevelData member-22 host can additionally prove the owning
    mission shell.  It never proves a quest activator, selected branch, or
    chronology inside/between missions.
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

    for header_row in header_report.get("headerRows") or []:
        if not isinstance(header_row, dict):
            continue
        dialogs = sorted(
            wanted.intersection(
                str(value) for value in header_row.get("sceneTexts") or []
            )
        )
        if not dialogs:
            continue
        level_id = str(header_row.get("levelId") or "")
        script_id = str(header_row.get("sourceScript") or "")
        source_file = str(header_row.get("file") or "")
        strict_common = (
            bool(expected_slot_mapping)
            and
            header_row.get("runtimeSlotStatus") == "active-final-serialized-slot"
            and str(header_row.get("runtimeSlotMappingId") or "")
            == expected_slot_mapping
            and header_row.get("targetStatus") == "action-list"
            and header_row.get("chainStatus") == "complete"
            and bool(header_row.get("headerName"))
            and level_id
            and script_id.isdigit()
            and source_file
        )
        for dialog_key in dialogs:
            play_actions = [
                action
                for action in header_row.get("playActions") or []
                if isinstance(action, dict)
                and action.get("class") == "play_dialog"
                and dialog_key in {
                    str(value) for value in action.get("texts") or []
                }
            ]
            if not strict_common or len(play_actions) != 1:
                failures.append(validation_failure(
                    "parent_dialog_event_action_path",
                    "one active named header -> complete action-list chain -> exact play_dialog",
                    {
                        "runtimeSlotStatus": header_row.get("runtimeSlotStatus"),
                        "runtimeSlotMappingId": header_row.get("runtimeSlotMappingId"),
                        "expectedRuntimeSlotMappingId": expected_slot_mapping,
                        "targetStatus": header_row.get("targetStatus"),
                        "chainStatus": header_row.get("chainStatus"),
                        "playDialogMatches": len(play_actions),
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
            play_action = play_actions[0]
            route_id = (
                f"{level_id}/{script_id}/"
                f"{header.get('localId')}/{dialog_key}"
            )
            routes.append({
                "id": route_id,
                "dialogKey": dialog_key,
                "storyKeys": sorted(dialog_to_story[dialog_key]),
                "levelId": level_id,
                "scriptId": script_id,
                "headerName": header_row.get("headerName"),
                "headerLocalId": header.get("localId"),
                "headerOffset": header.get("offset"),
                "headerOpcode": header.get("opcode"),
                "targetSource": header_row.get("targetSource"),
                "targetLocalId": header_row.get("targetLocalId"),
                "playActionLocalId": play_action.get("localId"),
                "playActionOffset": play_action.get("offset"),
                "playActionOpcode": play_action.get("opcode"),
                "actionChain": header_row.get("chain") or [],
                "chainStatus": header_row.get("chainStatus"),
                "runtimeSlotStatus": header_row.get("runtimeSlotStatus"),
                "runtimeSlotMappingId": header_row.get("runtimeSlotMappingId"),
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
    return {
        "validation": {
            "status": "validated" if not failures else "failed",
            "failures": failures,
        },
        "routes": routes,
        "counts": {
            "parentDialogKeys": len(wanted),
            "candidateHeaderRows": sum(
                1
                for header_row in header_report.get("headerRows") or []
                if isinstance(header_row, dict) and wanted.intersection(
                    str(value) for value in header_row.get("sceneTexts") or []
                )
            ),
            "exactActivationRoutes": len(routes),
            "parentDialogsWithExactActivation": len(matched_dialogs),
            "parentDialogsWithoutExactActivation": len(wanted - matched_dialogs),
            "storyKeysWithExactActivation": len(story_keys_with_routes),
            "uniqueMissionShells": len(mission_shell_ids),
            "missionOwnedRoutes": sum(
                bool(route.get("missionShellOwnership")) for route in routes
            ),
        },
        "evidenceBoundary": {
            "eventToActionTopology": True,
            "parentDialogPlayback": True,
            "missionShellOwnership": "unique_validated_leveldata_hosts_only",
            "questActivation": False,
            "branchSelection": False,
            "crossTimelineOrder": False,
            "ocrOrManualOverrideUsed": False,
        },
    }


def recover_parent_dialog_activation_routes(
    rows: list[dict[str, Any]],
    *,
    gameassembly: Path,
    metadata: Path,
    levelscript_root: Path | None = None,
) -> dict[str, Any]:
    """Run the exact activation join over every discovered parent dialog."""
    story_context, level_bindings, header_audit = _story_recovery_modules()
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
        (str(row.get("levelId") or ""), str(row.get("sourceScript") or ""))
        for row in header_report.get("headerRows") or []
        if dialog_keys.intersection(
            str(value) for value in row.get("sceneTexts") or []
        )
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
    result = join_parent_dialog_activation_routes(
        rows,
        header_report,
        mission_hosts,
        mission_area_hosts,
        gameassembly=gameassembly,
        metadata=metadata,
        mission_runtime_root=story_context.MRA_DIR,
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
    edges = local_order_edges(rows)
    return {
        "schemaVersion": "timelineEmbeddedStoryRuntimeAudit.v3",
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
            "storyLineIndex": line_validation,
        },
        "runtimeContract": contract,
        "controlRuntimeContract": control_contract,
        "directorHosts": director_hosts,
        "parentDialogActivation": activation,
        "activationRoutes": activation["routes"],
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
            "branchSelectionEdges": 0,
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
            "missionOwnership": "unique_validated_leveldata_hosts_only",
            "questActivation": False,
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
        "activator, selected branch, or any order across Timeline roots. OCR and manual "
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
        lines.append(
            f"- `{route['headerName']}` in `{route['levelId']}/{route['scriptId']}` "
            f"-> `#{route['playActionLocalId']}` `{route['dialogKey']}` -> "
            f"`{', '.join(route['storyKeys'])}`; mission shell `{missions}`; "
            "quest activation and branch selection unresolved"
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
