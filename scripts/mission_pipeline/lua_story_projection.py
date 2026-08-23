"""Load and project canonical shipped-Lua Story playback evidence."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

if __package__ and __package__.startswith("scripts."):
    from scripts.common import sha256_file as _sha256_path
    from scripts.story_builder.lua_consumer_references import (
        read_index as read_lua_consumer_reference_index,
    )
    from scripts.story_builder.native_contracts.cutscene_case_resolution import (
        load_cutscene_case_resolution_contract,
        matches_reviewed_lua_playback,
    )
else:
    from common import sha256_file as _sha256_path
    from story_builder.lua_consumer_references import (
        read_index as read_lua_consumer_reference_index,
    )
    from story_builder.native_contracts.cutscene_case_resolution import (
        load_cutscene_case_resolution_contract,
        matches_reviewed_lua_playback,
    )


ROOT = Path(__file__).resolve().parents[2]


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def _lua_phase(module: str) -> str:
    parts = Path(module).as_posix().split("/")
    if len(parts) >= 2 and parts[0].casefold() == "phase":
        return re.sub(r"(?<!^)(?=[A-Z])", "_", parts[1]).lower()
    scope = parts[-2] if len(parts) >= 2 else Path(module).stem
    return re.sub(r"(?<!^)(?=[A-Z])", "_", scope).lower()


def load_lua_story_playback_evidence(
    lua_audit_path: Path,
    *,
    lua_consumer_reference_schema: str,
    native_game_action_type: str,
    case_resolution_contract_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and normalize corpus-scanned shipped-Lua Story playback.

    This is deliberately data-driven: every accepted/rejected row comes from
    the complete Lua audit. Exact spelling is admitted; a spelling mismatch is
    rejected only when the reviewed native contract matches that exact call and
    the installed binaries plus IFix source still match its build boundary.
    """
    validator = "lua_story_playback_evidence"
    lua_audit_path = lua_audit_path.resolve()
    if not lua_audit_path.is_file():
        raise RuntimeError(
            f"validator={validator} failed: gate=audit_exists expected=file "
            f"actual=missing source={_repo_path(lua_audit_path)}"
        )
    audit_sha = _sha256_path(lua_audit_path)
    audit = read_lua_consumer_reference_index(lua_audit_path)
    schema = str(audit.get("schemaVersion") or "")
    if schema != lua_consumer_reference_schema:
        raise RuntimeError(
            f"validator={validator} failed: gate=schema expected={lua_consumer_reference_schema} "
            f"actual={schema or '<missing>'} source={_repo_path(lua_audit_path)}"
        )
    summary = audit.get("summary") or {}
    if int(summary.get("readErrorCount") or 0):
        raise RuntimeError(
            f"validator={validator} failed: gate=complete_scan expected=readErrorCount:0 "
            f"actual={summary.get('readErrorCount')} source={_repo_path(lua_audit_path)}"
        )

    calls = list((audit.get("gameActionAudit") or {}).get("storyPlaybackCalls") or [])
    malformed: list[str] = []
    for index, row in enumerate(calls):
        required = {
            "module": row.get("module"),
            "sourcePath": row.get("sourcePath"),
            "sourceSha256": row.get("sourceSha256"),
            "line": row.get("line"),
            "method": row.get("method"),
            "argumentSemantics": row.get("argumentSemantics"),
            "registryStatus": row.get("registryStatus"),
        }
        missing = [key for key, value in required.items() if value in (None, "")]
        source_sha = str(row.get("sourceSha256") or "")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", source_sha):
            missing.append("sourceSha256:sha256")
        if missing:
            malformed.append(f"row={index} missing={','.join(missing)}")
            continue
        source_path = ROOT / str(row["sourcePath"])
        if source_path.is_file():
            actual_sha = _sha256_path(source_path)
            if actual_sha.casefold() != source_sha.casefold():
                malformed.append(
                    f"row={index} sourceHash expected={source_sha} actual={actual_sha} "
                    f"source={_repo_path(source_path)}"
                )
        table_resolution = row.get("tableFieldResolution")
        if isinstance(table_resolution, dict):
            table_required = {
                "table": table_resolution.get("table"),
                "tableSourcePath": table_resolution.get("tableSourcePath"),
                "tableSourceSha256": table_resolution.get("tableSourceSha256"),
                "field": table_resolution.get("field"),
            }
            table_missing = [
                key for key, value in table_required.items()
                if value in (None, "")
            ]
            table_sha = str(table_resolution.get("tableSourceSha256") or "")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", table_sha):
                table_missing.append("tableSourceSha256:sha256")
            candidates = table_resolution.get("candidateRows") or []
            if row.get("literalResolution") == "table_field_singleton":
                if len(candidates) != 1 or not table_resolution.get("exactSingleton"):
                    table_missing.append("candidateRows:exact_singleton")
            if table_missing:
                malformed.append(
                    f"row={index} tableResolution={','.join(table_missing)}"
                )
                continue
            table_source = ROOT / str(table_resolution["tableSourcePath"])
            if table_source.is_file():
                actual_table_sha = _sha256_path(table_source)
                if actual_table_sha.casefold() != table_sha.casefold():
                    malformed.append(
                        f"row={index} tableSourceHash expected={table_sha} "
                        f"actual={actual_table_sha} source={_repo_path(table_source)}"
                    )
    if malformed:
        raise RuntimeError(
            f"validator={validator} failed: gate=row_provenance expected=complete_exact_rows "
            f"actual={malformed[0]} source={_repo_path(lua_audit_path)}"
        )

    mismatch_calls = [
        row for row in calls
        if row.get("registryStatus") == "case_mismatch_registry_match"
    ]
    if mismatch_calls and case_resolution_contract_audit is None:
        case_resolution_contract_audit = (
            load_cutscene_case_resolution_contract()
        )
    case_resolution_contract_audit = case_resolution_contract_audit or {
        "status": "not_required",
        "sourceFile": "",
        "sourceSha256": "",
        "nativeContract": {},
        "validationFailures": [],
    }

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in calls:
        status = str(row.get("registryStatus") or "")
        method = str(row.get("method") or "")
        native_entry = f"{native_game_action_type}::{method}"
        if status == "exact_registry_match":
            story_key = str(row.get("canonicalStoryKey") or "")
            if (
                not story_key
                or row.get("argumentSemantics") != "story_id"
                or row.get("resolvedLiteral") != story_key
            ):
                continue
            module = str(row["module"])
            virtual_lua_file = f"Lua/Data/LuaScripts/{module}"
            table_resolution = row.get("tableFieldResolution") or {}
            table_candidates = table_resolution.get("candidateRows") or []
            table_candidate = (
                table_candidates[0]
                if len(table_candidates) == 1
                and row.get("literalResolution") == "table_field_singleton"
                else {}
            )
            row_fields = table_candidate.get("rowFields") or {}
            mission_id = str(row_fields.get("missionId") or "") or None
            quest_id = str(row_fields.get("questId") or "") or None
            table_source_path = str(
                table_resolution.get("tableSourcePath") or ""
            )
            is_table_carrier = bool(table_candidate)
            accepted.append({
                "storyKey": story_key,
                "luaFile": virtual_lua_file,
                "luaSourcePath": str(row["sourcePath"]),
                "luaSourceSha256": str(row["sourceSha256"]).lower(),
                "luaLine": int(row["line"]),
                "luaSymbol": str(row.get("firstArgument") or ""),
                "luaCall": f"GameAction.{method}",
                "nativeEntry": native_entry,
                "phase": _lua_phase(module),
                "playbackKind": row.get("playbackKind"),
                "literalResolution": str(row.get("literalResolution") or ""),
                "missionId": mission_id,
                "questId": quest_id,
                "table": str(table_resolution.get("table") or ""),
                "tableKey": str(table_candidate.get("tableKey") or ""),
                "tableField": str(table_resolution.get("field") or ""),
                "tableLookupKeyExpression": str(
                    table_resolution.get("lookupKeyExpression") or ""
                ),
                "tableSourcePath": table_source_path,
                "tableSourceSha256": str(
                    table_resolution.get("tableSourceSha256") or ""
                ).lower(),
                "auditReport": _repo_path(lua_audit_path),
                "auditSha256": audit_sha,
                "note": (
                    (
                        "The complete shipped-Lua census traced this typed GameAction "
                        "call through one exact current-table row. That same row "
                        "co-carries the published mission/quest identity."
                    )
                    if is_table_carrier and (mission_id or quest_id)
                    else (
                        "The complete shipped-Lua census found an exact-case literal at "
                        "this typed GameAction playback call. The Lua controller owns "
                        "playback; no mission or quest identity is serialized."
                    )
                ),
            })
            continue
        if status != "case_mismatch_registry_match":
            continue
        if not matches_reviewed_lua_playback(
            row,
            case_resolution_contract_audit,
        ):
            continue
        contract = case_resolution_contract_audit["nativeContract"]
        source = contract["sources"]
        association = contract["recoveryAssociationPolicy"]
        accepted.append({
            "storyKey": str(row.get("canonicalStoryKey") or ""),
            "luaLiteral": str(row.get("resolvedLiteral") or ""),
            "luaFile": f"Lua/Data/LuaScripts/{row['module']}",
            "luaSourcePath": str(row["sourcePath"]),
            "luaSourceSha256": str(row["sourceSha256"]).lower(),
            "luaLine": int(row["line"]),
            "luaSymbol": str(row.get("firstArgument") or ""),
            "luaCall": f"GameAction.{method}",
            "nativeEntry": native_entry,
            "phase": _lua_phase(str(row.get("module") or "")),
            "playbackKind": row.get("playbackKind"),
            "literalResolution": "official_ascii_case_insensitive_association",
            "missionId": None,
            "questId": None,
            "table": "",
            "tableKey": "",
            "tableField": "",
            "tableLookupKeyExpression": "",
            "tableSourcePath": "",
            "tableSourceSha256": "",
            "runtimeLookupStatus": "case_sensitive_case_mismatch",
            "recoveryAssociationStatus": "accepted_unique_ascii_case_insensitive",
            "confidence": "official_case_insensitive_recovery_policy_plus_binary_runtime_boundary",
            "auditReport": str(case_resolution_contract_audit["sourceFile"]),
            "auditSha256": str(
                case_resolution_contract_audit["sourceSha256"]
            ).lower(),
            "gameAssemblySha256": str(source["gameAssemblySha256"]).lower(),
            "metadataSha256": str(source["metadataSha256"]).lower(),
            "note": (
                "The official recovery policy associates the unique ASCII-case-insensitive "
                "Story key. The installed runtime lookup remains case-sensitive; this "
                "association supplies playback evidence but no ownership or spatial evidence."
            ),
            "recoveryAssociationPolicy": association["comparison"],
        })

    accepted.sort(key=lambda row: (_natural_quest_key(row["storyKey"]), row["luaFile"], row["luaLine"]))
    rejected.sort(key=lambda row: (_natural_quest_key(row["storyKey"]), row["luaFile"], row["luaLine"]))
    runtime_dispatchers = [
        row for row in calls
        if row.get("playbackRole") == "runtime_queue_dispatcher"
    ]
    runtime_contract = (audit.get("gameActionAudit") or {}).get(
        "runtimeHandleContract"
    ) or {}
    action_producer_routes = runtime_contract.get("actionProducerRoutes") or []
    if runtime_dispatchers and (
        not runtime_contract.get("report")
        or not re.fullmatch(
            r"[0-9a-fA-F]{64}",
            str(runtime_contract.get("sha256") or ""),
        )
        or not {
            str(row.get("method") or "") for row in runtime_dispatchers
        }.issubset(set(runtime_contract.get("dispatcherMethods") or []))
        or not action_producer_routes
        or any(
            not row.get("actionType")
            or not row.get("producerMethod")
            or not row.get("actionToken")
            for row in action_producer_routes
        )
    ):
        raise RuntimeError(
            f"validator={validator} failed: gate=runtime_handle_contract "
            f"expected=complete_binary_dispatch_family actual=invalid "
            f"source={_repo_path(lua_audit_path)}"
        )
    case_insensitive_associations = [{
        "storyKey": str(row.get("storyKey") or ""),
        "luaLiteral": str(row.get("luaLiteral") or ""),
        "luaFile": str(row.get("luaFile") or ""),
        "luaLine": row.get("luaLine"),
        "wouldResolvePlaybackResource": bool(
            row.get("storyKey")
            and str(row.get("storyKey")).casefold()
            == str(row.get("luaLiteral") or "").casefold()
        ),
        "suppliesSpatialEvidence": False,
        "suppliesMissionOrQuestOwnership": False,
    } for row in accepted if row.get("recoveryAssociationStatus")]
    return {
        "validator": validator,
        "status": "validated",
        "schemaVersion": lua_consumer_reference_schema,
        "auditReport": _repo_path(lua_audit_path),
        "auditSha256": audit_sha,
        "scannedPlaybackCalls": len(calls),
        "acceptedExactPlaybackCalls": accepted,
        "rejectedCaseMismatchCalls": rejected,
        "runtimeHandleDispatcherCalls": runtime_dispatchers,
        "runtimeHandleDispatcherCallCount": len(runtime_dispatchers),
        "runtimeHandleDispatcherFamilyCount": 1 if runtime_dispatchers else 0,
        "runtimeHandleContract": runtime_contract,
        "unresolvedPlaybackCalls": (
            len(calls) - len(accepted) - len(rejected) - len(runtime_dispatchers)
        ),
        "acceptedTableCarrierCalls": sum(
            1 for row in accepted if row.get("literalResolution") == "table_field_singleton"
        ),
        "caseResolutionContract": {
            field: case_resolution_contract_audit.get(field)
            for field in (
                "schema",
                "status",
                "sourceFile",
                "sourceSha256",
                "validationFailures",
            )
            if case_resolution_contract_audit.get(field) not in (None, "")
        },
        "caseInsensitiveResourceNameAssociation": {
            "status": "official_recovery_policy",
            "associationPolicy": "ascii_case_insensitive_unique_story_key",
            "playbackResourceCandidateCount": sum(
                1 for row in case_insensitive_associations
                if row["wouldResolvePlaybackResource"]
            ),
            "spatialMapCandidateCount": 0,
            "candidates": case_insensitive_associations,
            "boundary": (
                "This offline association policy changes only resource-name equality for the "
                "reviewed unique case-mismatch call; native runtime lookup remains case-sensitive. "
                "Lua playback calls carry no authored trigger geometry, "
                "entity transform, mission owner, quest owner, or Story order evidence."
            ),
        },
        "evidenceBoundary": (
            "Exact shipped-Lua bytes and typed GameAction calls prove controller "
            "playback. A mission/quest attachment is admitted only when the same "
            "resolved original table row co-carries that identity; otherwise Lua "
            "does not supply mission ownership or Story order. "
            "Binary-proven cinematic-handle calls are one polymorphic runtime "
            "dispatcher family and are not counted as unresolved authored references. "
            "A binary-discovered typed action-to-producer route can annotate an exact "
            "LevelScript playback route and attach its audit file, but cannot supply "
            "mission ownership or order by itself. "
            "A unique case-folded match creates a playback-only route under the official "
            "recovery policy while preserving the binary-proven case-sensitive runtime note."
        ),
    }
