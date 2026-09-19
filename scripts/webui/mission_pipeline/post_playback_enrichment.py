"""Enrich already-classified post-playback controls for publication.

Native action classification and source contracts remain owned by their original
modules and are injected here. This module only indexes and attaches exact source
identities and publishes bounded audit projections.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any


def attach_post_playback_callserver_contracts(
    runtime_nodes: list[dict[str, Any]],
    callback_audit: dict[str, Any],
    *,
    contract_projector: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Attach complete-corpus CallServer rows by exact source/local identity.

    The join is intentionally generic across all missions, maps, and Story
    actions. It fails closed on duplicate or disagreeing rows and never treats
    an event name or argument path as a mission/quest foreign key.
    """
    audit_rows: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in callback_audit.get("rows") or []:
        source_file = str(row.get("sourceFile") or "").replace("\\", "/")
        local_id = row.get("callServerLocalId")
        if source_file and isinstance(local_id, int):
            audit_rows[(source_file, local_id)].append(row)

    counts: Counter[str] = Counter()
    event_identities: Counter[str] = Counter()
    argument_paths: Counter[str] = Counter()
    flag_combinations: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    for node in runtime_nodes:
        for control in node.get("postPlaybackControls") or []:
            source_file = str(control.get("sourceFile") or "").replace("\\", "/")
            for handoff in control.get("serverHandoffs") or []:
                counts["handoffs"] += 1
                local_id = handoff.get("localId")
                candidates = audit_rows.get((source_file, local_id), [])
                if len(candidates) != 1:
                    counts["unresolvedContracts"] += 1
                    failures.append({
                        "gate": "post_playback_callserver_exact_identity",
                        "source": source_file,
                        "localId": local_id,
                        "expectedCandidateCount": 1,
                        "actualCandidateCount": len(candidates),
                    })
                    continue
                audit_contract = contract_projector(
                    candidates[0].get("serializedContract") or {}
                )
                path_contract = contract_projector(
                    handoff.get("serializedContract") or {}
                )
                if path_contract and path_contract != audit_contract:
                    counts["contractMismatches"] += 1
                    failures.append({
                        "gate": "post_playback_callserver_contract_match",
                        "source": source_file,
                        "localId": local_id,
                        "expected": audit_contract,
                        "actual": path_contract,
                    })
                    continue
                handoff["serializedContract"] = audit_contract
                handoff["contractStatus"] = "exact_source_local_id_match"
                handoff["missionOwnershipEvidence"] = False
                counts["exactContracts"] += 1
                event_identities[
                    str(audit_contract.get("eventNameIdentity") or "other")
                ] += 1
                event_args = audit_contract.get("eventArgsPtr") or {}
                argument_paths[
                    str(event_args.get("path") or "<null>")
                ] += 1
                flag_combinations[
                    "custom={custom},wait={wait},args={args}".format(
                        custom=int(bool(audit_contract.get("useCustomEvent"))),
                        wait=int(bool(audit_contract.get("waitForCallback"))),
                        args=int(bool(audit_contract.get("withEventArgs"))),
                    )
                ] += 1
    return {
        "status": "validated" if not failures else "validation_failed",
        "summary": {
            **dict(sorted(counts.items())),
            "eventNameIdentityDistribution": dict(sorted(event_identities.items())),
            "eventArgsParamPathDistribution": dict(sorted(argument_paths.items())),
            "flagDistribution": dict(sorted(flag_combinations.items())),
        },
        "validationFailures": failures,
        "missionOwnershipEvidence": False,
        "evidenceBoundary": (
            "Every post-playback CallServer is joined to the complete original-data "
            "action audit by exact source file and local action id. Serialized event "
            "names, argument parameters, flags, and callback UIDs describe the client "
            "handoff contract; absent an independent original-data foreign key, they "
            "do not identify a mission/quest owner or order another Story file."
        ),
    }


def build_level_sequence_textasset_index(
    root: Path,
    *,
    compact_projector: Callable[[dict[str, Any]], dict[str, Any]],
    repo_path_projector: Callable[[Path], str],
) -> dict[str, Any]:
    """Index original LevelSequence TextAssets by three-way exact identity.

    A filename is only an enumeration aid. A row is eligible for a join when
    the exported Unity ``m_Name`` and ``Name`` fields and the decoded payload's
    ``cutsceneName`` all agree. This keeps the resolver reusable across maps,
    missions, and sequence ids while failing closed on malformed or ambiguous
    exports.
    """
    assets_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failures: list[dict[str, Any]] = []
    source_files = sorted(root.glob("levelseq_*.json")) if root.is_dir() else []
    for source_path in source_files:
        try:
            raw = source_path.read_bytes()
            outer = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(outer, dict):
                raise ValueError("outer JSON is not an object")
            unity_name = str(outer.get("m_Name") or "")
            exported_name = str(outer.get("Name") or "")
            encoded_payload = outer.get("m_Script")
            if not unity_name or unity_name != exported_name:
                raise ValueError(
                    f"outer identity mismatch m_Name={unity_name!r} Name={exported_name!r}"
                )
            if not isinstance(encoded_payload, str) or not encoded_payload:
                raise ValueError("m_Script is not a non-empty base64 string")
            decoded = base64.b64decode(encoded_payload, validate=True)
            payload = json.loads(decoded.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("decoded m_Script JSON is not an object")
            payload_name = str(payload.get("cutsceneName") or "")
            if payload_name != unity_name:
                raise ValueError(
                    f"payload identity mismatch cutsceneName={payload_name!r} m_Name={unity_name!r}"
                )
            path_id_match = re.search(r"_p([0-9A-Fa-f]+)\.json$", source_path.name)
            assets_by_id[unity_name].append(compact_projector({
                "levelSequenceId": unity_name,
                "sourceFile": repo_path_projector(source_path),
                "pathId": (
                    f"0x{path_id_match.group(1).upper()}"
                    if path_id_match
                    else ""
                ),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "payloadPath": str(payload.get("path") or ""),
                "payloadVersion": payload.get("version"),
                "targetFrameRate": payload.get("targetFrameRate"),
                "identityStatus": "exact_m_name_name_cutscene_name_match",
            }))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
            failures.append({
                "validator": "levelSequenceTextAssetIdentity",
                "gate": "m_Name_equals_Name_equals_decoded_cutsceneName",
                "sourceFile": repo_path_projector(source_path),
                "actual": str(error)[:400],
            })

    ambiguous_ids = sorted(
        sequence_id
        for sequence_id, rows in assets_by_id.items()
        if len(rows) != 1
    )
    exact_assets = {
        sequence_id: rows[0]
        for sequence_id, rows in sorted(assets_by_id.items())
        if len(rows) == 1
    }
    return {
        "schema": "exactLevelSequenceTextAssetIndex.v1",
        "root": repo_path_projector(root),
        "status": (
            "exact_complete"
            if source_files and not failures and not ambiguous_ids
            else "degraded_fail_closed"
        ),
        "assetsById": exact_assets,
        "summary": {
            "sourceFilesScanned": len(source_files),
            "exactUniqueIdentities": len(exact_assets),
            "validationFailures": len(failures),
            "ambiguousIdentities": len(ambiguous_ids),
        },
        "validationFailures": failures,
        "ambiguousLevelSequenceIds": ambiguous_ids,
    }


def attach_exact_level_sequence_assets(
    runtime_nodes: list[dict[str, Any]],
    asset_index: dict[str, Any],
) -> dict[str, Any]:
    """Attach exact original files to typed LevelSequence control actions.

    Action classes come from the installed ActionBase formatter table. The
    family test is intentionally type-based (``LevelSeq`` in that recovered
    class name); no mission, map, object, or sequence identifier is hardcoded.
    """
    assets_by_id = asset_index.get("assetsById") or {}
    action_placements = 0
    exact_placements = 0
    serialized_ids: set[str] = set()
    exact_ids: set[str] = set()
    unresolved_ids: set[str] = set()
    related_files: set[str] = set()
    for node in runtime_nodes:
        for control in node.get("postPlaybackControls") or []:
            for action in control.get("actions") or []:
                action_name = str(action.get("actionName") or "")
                if "LevelSeq" not in action_name:
                    continue
                sequence_ids = sorted({
                    str(value)
                    for value in action.get("texts") or []
                    if str(value).startswith("levelseq_")
                })
                if not sequence_ids:
                    continue
                action_placements += 1
                references = []
                for sequence_id in sequence_ids:
                    serialized_ids.add(sequence_id)
                    asset = assets_by_id.get(sequence_id)
                    if isinstance(asset, dict):
                        exact_placements += 1
                        exact_ids.add(sequence_id)
                        related_files.add(str(asset.get("sourceFile") or ""))
                        references.append({
                            **asset,
                            "relation": "exact_serialized_action_id_to_textasset_identity",
                            "missionOwnershipEvidence": False,
                            "crossStoryOrderEvidence": False,
                        })
                    else:
                        unresolved_ids.add(sequence_id)
                        references.append({
                            "levelSequenceId": sequence_id,
                            "identityStatus": "no_exact_validated_textasset",
                            "missionOwnershipEvidence": False,
                            "crossStoryOrderEvidence": False,
                        })
                action["levelSequenceReferences"] = references

    return {
        "schema": "postPlaybackLevelSequenceAssetAudit.v1",
        "status": (
            "exact_matches_with_unresolved_ids"
            if unresolved_ids
            else "all_serialized_ids_resolved"
        ),
        "sourceIndex": {
            key: asset_index.get(key)
            for key in (
                "schema", "root", "status", "summary",
                "validationFailures", "ambiguousLevelSequenceIds",
            )
        },
        "summary": {
            "typedActionPlacements": action_placements,
            "serializedLevelSequenceIds": len(serialized_ids),
            "exactAssetPlacements": exact_placements,
            "exactResolvedLevelSequenceIds": len(exact_ids),
            "unresolvedLevelSequenceIds": len(unresolved_ids),
            "relatedOriginalFiles": len({value for value in related_files if value}),
        },
        "unresolvedLevelSequenceIds": sorted(unresolved_ids),
        "usesOcrOrManualOrder": False,
        "missionOwnershipEvidence": False,
        "crossStoryOrderEvidence": False,
        "evidenceBoundary": (
            "The installed formatter type and serialized action id identify a local "
            "LevelSequence reference; the original TextAsset is attached only after "
            "m_Name, Name, and decoded cutsceneName agree. This does not identify a "
            "mission owner or order separate Story files."
        ),
    }


def build_post_playback_action_name_audit(
    runtime_nodes: list[dict[str, Any]],
    *,
    formatter_names: dict[int, str],
    formatter_audit: dict[str, Any],
) -> dict[str, Any]:
    """Measure binary formatter naming across the complete control surface."""
    shape_counts: Counter[tuple[str, str]] = Counter()
    formatter_named_actions = 0
    fallback_named_actions = 0
    unresolved_actions = 0
    mismatches: list[dict[str, Any]] = []
    opcode_pattern = re.compile(r"^0x([0-9a-f]+)/0x([0-9a-f]+)$", re.IGNORECASE)
    for node in runtime_nodes:
        for control in node.get("postPlaybackControls") or []:
            for action in control.get("actions") or []:
                opcode = str(action.get("opcode") or "")
                action_name = str(action.get("actionName") or "")
                shape_counts[(opcode, action_name)] += 1
                match = opcode_pattern.match(opcode)
                union_tag_text = str(action.get("unionTag") or "")
                try:
                    union_tag = int(union_tag_text, 16)
                except ValueError:
                    union_tag = int(match.group(1), 16) if match else -1
                serialized_member_count = action.get("serializedMemberCount")
                if not isinstance(serialized_member_count, int):
                    serialized_member_count = (
                        int(match.group(2), 16) if match else 0
                    )
                if union_tag < 0:
                    unresolved_actions += 1
                    continue
                formatter_name = (
                    str(formatter_names.get(union_tag) or "")
                    if serialized_member_count > 0
                    else ""
                )
                if formatter_name:
                    if action_name == formatter_name:
                        formatter_named_actions += 1
                    else:
                        mismatches.append({
                            "validator": "postPlaybackActionFormatterName",
                            "gate": "action_name_equals_formatter_tag",
                            "sourceFile": str(control.get("sourceFile") or ""),
                            "storyKey": str(control.get("storyKey") or ""),
                            "actionLocalId": action.get("localId"),
                            "expected": {
                                "opcode": opcode,
                                "unionTag": f"0x{union_tag:04x}",
                                "serializedMemberCount": serialized_member_count,
                                "actionName": formatter_name,
                            },
                            "actual": {"actionName": action_name},
                        })
                elif action_name:
                    fallback_named_actions += 1
                else:
                    unresolved_actions += 1
    total_actions = sum(shape_counts.values())
    unresolved_shapes = [
        {"opcode": opcode, "count": count}
        for (opcode, action_name), count in sorted(shape_counts.items())
        if not action_name
    ]
    source_failures = list(formatter_audit.get("validationFailures") or [])
    failures = source_failures + mismatches
    return {
        "schema": "postPlaybackActionNameAudit.v1",
        "status": (
            "validated_complete_actionbase_surface"
            if not failures and not unresolved_actions
            else "validated_actionbase_complete_outside_families_retained"
            if not failures
            else "validation_failed"
        ),
        "formatterTable": formatter_audit,
        "summary": {
            "actionPlacements": total_actions,
            "formatterNamedActionPlacements": formatter_named_actions,
            "fallbackNamedActionPlacements": fallback_named_actions,
            "unresolvedOutsideActionBasePlacements": unresolved_actions,
            "distinctActionShapes": len(shape_counts),
            "unresolvedOutsideActionBaseShapes": len(unresolved_shapes),
            "validationFailures": len(failures),
        },
        "unresolvedActionShapes": unresolved_shapes,
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
        "missionOwnershipEvidence": False,
        "crossStoryOrderEvidence": False,
        "evidenceBoundary": (
            "The installed ActionBase MemoryPack formatter names action classes "
            "from the compact unionTag plus serializedMemberCount. Legacy combined "
            "raw opcodes remain display provenance and are never used as the tag. "
            "A class name does not identify a mission owner, select a branch, or "
            "order separate Story files."
        ),
    }

