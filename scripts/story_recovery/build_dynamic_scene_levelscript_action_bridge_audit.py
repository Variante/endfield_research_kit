#!/usr/bin/env python3
"""Audit typed LevelScript actions that address DynamicScene identity roots.

This is a deliberately narrow follow-up to
``build_dynamic_scene_mission_control_audit.py``. It admits only current-build
``ShowSceneDecorationNew`` and ``ShowSceneDecorationWithHandle`` action rows
whose two authored parameters decode completely as:

``Param<DynamicSceneEntityPtr> target`` + ``Param<bool> visible``

The exact target join proves that a LevelScript action addresses the same
DynamicScene logic id. A shared serialized header/action path can additionally
prove that the decoration action and Story playback share local LevelScript
control flow. Neither fact proves that the DynamicScene mission condition
activates the LevelScript, so this audit never emits mission ownership/order
edges.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from common import write_report_json, write_text_if_changed  # noqa: E402
from story_builder.level_bindings import (  # noqa: E402
    _levelscript_native_control_paths_to_record,
    _prepare_levelscript_native_control_context,
)
from story_builder.levelscript_binary import (  # noqa: E402
    _decode_bool_param,
    _decode_u64_param,
    _record_payload_window,
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
)


DEFAULT_IDENTITY_AUDIT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "dynamic_scene_mission_control_audit.json"
)
DEFAULT_STREAMING_ROOT = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "LevelScriptData"
)
DEFAULT_PERSISTENT_ROOT = (
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "LevelScriptData"
)
DEFAULT_OUT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "dynamic_scene_levelscript_action_bridge_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")


ACTION_SCHEMAS = {
    0x0485: {
        "name": "ShowSceneDecorationNew",
        "serializedMemberCount": 10,
    },
    0x0486: {
        "name": "ShowSceneDecorationWithHandle",
        "serializedMemberCount": 10,
    },
}
MAPPING_ID = "current-global-metadata-dynamic-scene-decoration-action-fields"


def _safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def repo_rel(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _is_constant_param(param: dict[str, Any]) -> bool:
    return (
        param.get("idRef") == -1
        and param.get("paramSource") == 0
        and param.get("path") is None
    )


def decode_decoration_action(
    data: bytes,
    record: dict[str, Any],
    *,
    next_start: int | None,
    action_map_role: str,
) -> tuple[dict[str, Any] | None, str]:
    """Decode one fully consumed, constant current-build decoration action."""
    union_tag = record.get("unionTag")
    schema = ACTION_SCHEMAS.get(union_tag)
    if schema is None:
        return None, "not_target_action"
    if record.get("serializedMemberCount") != schema["serializedMemberCount"]:
        return None, "wrong_serialized_member_count"
    if not action_map_role.startswith("actionList#"):
        return None, "outside_action_list"

    payload_start, payload = _record_payload_window(data, record, next_start)
    target_result = _decode_u64_param(payload, 0)
    if target_result is None:
        return None, "target_param_decode_failed"
    target, cursor = target_result
    visible_result = _decode_bool_param(payload, cursor)
    if visible_result is None:
        return None, "visible_param_decode_failed"
    visible, cursor = visible_result
    if not _is_constant_param(target) or not _is_constant_param(visible):
        return None, "nonconstant_param"
    if cursor != len(payload):
        return None, "unclassified_trailing_bytes"

    return {
        "actionName": schema["name"],
        "unionTag": f"0x{union_tag:04x}",
        "serializedMemberCount": schema["serializedMemberCount"],
        "mappingId": MAPPING_ID,
        "recordOffset": int(record.get("start") or 0),
        "payloadOffset": payload_start,
        "actionMapRole": action_map_role,
        "localId": record.get("localId"),
        "nextId": record.get("nextId"),
        "targetDynamicEntityLogicId": _safe_text(target.get("value")),
        "visible": bool(visible.get("value")),
        "payloadFullyConsumed": True,
        "targetParam": target,
        "visibleParam": visible,
    }, "exact"


def _path_identity(path: dict[str, Any]) -> tuple[Any, ...]:
    return (
        path.get("headerLocalId"),
        path.get("headerName"),
        path.get("headerOpcode"),
        path.get("headerUnionTag"),
    )


def shared_control_paths(
    story_paths: list[dict[str, Any]],
    action_paths: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return exact shared-header relationships between two action records."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for story_path in story_paths:
        story_ids = list(story_path.get("pathLocalIds") or [])
        for action_path in action_paths:
            if _path_identity(story_path) != _path_identity(action_path):
                continue
            action_ids = list(action_path.get("pathLocalIds") or [])
            if not story_ids or not action_ids:
                continue
            relation = "shared_header_divergent_paths"
            if action_ids[: len(story_ids)] == story_ids:
                relation = (
                    "same_action"
                    if len(action_ids) == len(story_ids)
                    else "decoration_follows_story_on_same_path"
                )
            elif story_ids[: len(action_ids)] == action_ids:
                relation = "story_follows_decoration_on_same_path"
            signature = (
                *_path_identity(story_path),
                tuple(story_ids),
                tuple(action_ids),
                relation,
            )
            if signature in seen:
                continue
            seen.add(signature)
            out.append({
                "status": "exact_serialized_shared_control_path",
                "relation": relation,
                "headerName": story_path.get("headerName"),
                "headerOpcode": story_path.get("headerOpcode"),
                "headerUnionTag": story_path.get("headerUnionTag"),
                "headerSerializedMemberCount": story_path.get(
                    "headerSerializedMemberCount"
                ),
                "headerLocalId": story_path.get("headerLocalId"),
                "headerTexts": story_path.get("headerTexts") or [],
                "eventDetail": story_path.get("eventDetail") or {},
                "storyPathLocalIds": story_ids,
                "decorationPathLocalIds": action_ids,
                "storyPath": story_path.get("path") or [],
                "decorationPath": action_path.get("path") or [],
            })
    return out


def _effective_path(
    level_id: str,
    script_id: str,
    *,
    streaming_root: Path,
    persistent_root: Path,
) -> Path | None:
    relative = Path(level_id) / f"{script_id}.json"
    persistent = persistent_root / relative
    if persistent.is_file():
        return persistent
    streaming = streaming_root / relative
    if streaming.is_file():
        return streaming
    return None


def _parse_script(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    records = extract_levelscript_uid_records(data)
    _action_map, membership = levelscript_action_map_membership(data, records)
    context = _prepare_levelscript_native_control_context(data, records, membership)
    ordered = sorted(records, key=lambda row: int(row.get("start") or 0))
    next_starts = {
        int(record.get("start") or 0): (
            int(ordered[index + 1].get("start") or len(data))
            if index + 1 < len(ordered)
            else len(data)
        )
        for index, record in enumerate(ordered)
    }
    by_start = {int(record.get("start") or 0): record for record in records}
    exact_actions: list[tuple[dict[str, Any], dict[str, Any]]] = []
    rejected = Counter()
    for record in records:
        if record.get("unionTag") not in ACTION_SCHEMAS:
            continue
        start = int(record.get("start") or 0)
        decoded, status = decode_decoration_action(
            data,
            record,
            next_start=next_starts.get(start),
            action_map_role=_safe_text(membership.get(start)),
        )
        if decoded is None:
            rejected[status] += 1
            continue
        exact_actions.append((record, decoded))
    return {
        "data": data,
        "records": records,
        "membership": membership,
        "context": context,
        "byStart": by_start,
        "exactActions": exact_actions,
        "rejected": rejected,
    }


def build_audit(
    identity: dict[str, Any],
    *,
    identity_path: Path,
    streaming_root: Path,
    persistent_root: Path,
) -> dict[str, Any]:
    candidates = list(identity.get("storyIdentityCandidates") or [])
    parsed_cache: dict[Path, dict[str, Any]] = {}
    bridge_rows: list[dict[str, Any]] = []
    missing_files: list[dict[str, str]] = []
    missing_story_records = 0

    for candidate in candidates:
        logic_id = _safe_text(candidate.get("logicId"))
        candidate_actions: list[tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
        candidate_story_rows: list[
            tuple[Path, dict[str, Any], dict[str, Any], list[dict[str, Any]]]
        ] = []
        matches = list(candidate.get("levelScriptMatches") or [])
        for match in matches:
            level_id = _safe_text(match.get("levelId"))
            script_id = _safe_text(match.get("scriptId"))
            path = _effective_path(
                level_id,
                script_id,
                streaming_root=streaming_root,
                persistent_root=persistent_root,
            )
            if path is None:
                missing_files.append({"levelId": level_id, "scriptId": script_id})
                continue
            if path not in parsed_cache:
                parsed_cache[path] = _parse_script(path)
            parsed = parsed_cache[path]
            for record, action in parsed["exactActions"]:
                if action["targetDynamicEntityLogicId"] == logic_id:
                    candidate_actions.append((path, parsed, record, action))

            for story in candidate.get("storyOccurrences") or []:
                if (
                    _safe_text(story.get("levelId")) != level_id
                    or _safe_text(story.get("scriptId")) != script_id
                ):
                    continue
                record = parsed["byStart"].get(story.get("recordOffset"))
                if record is None:
                    missing_story_records += 1
                    continue
                paths = _levelscript_native_control_paths_to_record(
                    parsed["data"],
                    parsed["records"],
                    parsed["membership"],
                    record,
                    prepared=parsed["context"],
                )
                candidate_story_rows.append((path, parsed, story, paths))

        if not candidate_actions:
            continue

        action_rows: list[dict[str, Any]] = []
        shared_story_keys: set[str] = set()
        for path, parsed, record, action in candidate_actions:
            action_paths = _levelscript_native_control_paths_to_record(
                parsed["data"],
                parsed["records"],
                parsed["membership"],
                record,
                prepared=parsed["context"],
            )
            story_links: list[dict[str, Any]] = []
            for story_path, _story_parsed, story, story_paths in candidate_story_rows:
                if story_path != path:
                    continue
                shared = shared_control_paths(story_paths, action_paths)
                if not shared:
                    continue
                story_key = _safe_text(story.get("storyKey"))
                if story_key:
                    shared_story_keys.add(story_key)
                story_links.append({
                    "storyKey": story_key,
                    "storyRecordOffset": story.get("recordOffset"),
                    "storyActionName": story.get("actionName"),
                    "sharedControlPaths": shared,
                })
            action_rows.append({
                **action,
                "sourceFile": repo_rel(path),
                "sourceSha256": _sha256(path),
                "controlPaths": action_paths,
                "storyControlPathLinks": story_links,
            })

        bridge_rows.append({
            "scene": candidate.get("scene"),
            "logicId": logic_id,
            "missionControls": candidate.get("missionControls") or [],
            "storyOccurrences": candidate.get("storyOccurrences") or [],
            "exactTargetActions": action_rows,
            "sharedStoryKeys": sorted(shared_story_keys),
            "classification": (
                "exact_dynamic_scene_target_and_shared_levelscript_control_path"
                if shared_story_keys
                else "exact_dynamic_scene_target_same_script_only"
            ),
            "missionOwnerStatus": "unresolved",
            "storyBinding": False,
            "orderEvidence": False,
            "missionGraphAction": "none",
        })

    exact_actions_in_candidate_scripts = sum(
        len(parsed["exactActions"]) for parsed in parsed_cache.values()
    )
    rejected = Counter()
    for parsed in parsed_cache.values():
        rejected.update(parsed["rejected"])

    bridge_rows.sort(key=lambda row: (int(row["logicId"]), _safe_text(row["scene"])))
    shared_rows = [row for row in bridge_rows if row.get("sharedStoryKeys")]
    shared_story_keys = sorted({
        story_key
        for row in shared_rows
        for story_key in row.get("sharedStoryKeys") or []
    })
    identity_source = identity.get("sources") or {}
    return {
        "schemaVersion": 1,
        "policy": (
            "Only fully consumed constant current-build decoration actions in "
            "the serialized actionList are admitted. Exact DynamicScene target "
            "identity and shared local LevelScript control paths remain context "
            "evidence, not mission activation, ownership, or chronology."
        ),
        "sources": {
            "identityAudit": {
                "path": repo_rel(identity_path),
                "sha256": _sha256(identity_path),
                "schemaVersion": identity.get("schemaVersion"),
            },
            "dynamicStreaming": identity_source.get("dynamicStreaming") or {},
            "il2cppMetadata": identity_source.get("il2cppMetadata") or {},
            "streamingLevelScriptRoot": repo_rel(streaming_root),
            "persistentLevelScriptRoot": repo_rel(persistent_root),
            "overlayRule": "Persistent file wins; StreamingAssets is fallback.",
        },
        "actionSchemas": [
            {
                "actionName": schema["name"],
                "unionTag": f"0x{union_tag:04x}",
                "serializedMemberCount": schema["serializedMemberCount"],
                "serializedFields": [
                    "Param<DynamicSceneEntityPtr> _targetDynamicEntity",
                    "Param<bool> _visible",
                ],
                "admission": (
                    "actionList member; both constant params decode; payload "
                    "is fully consumed"
                ),
                "mappingId": MAPPING_ID,
            }
            for union_tag, schema in ACTION_SCHEMAS.items()
        ],
        "counts": {
            "storyIdentityRootsInspected": len(candidates),
            "storyOccurrencesInspected": sum(
                len(candidate.get("storyOccurrences") or [])
                for candidate in candidates
            ),
            "candidateScriptFilesDecoded": len(parsed_cache),
            "exactDecorationActionsInCandidateScripts":
                exact_actions_in_candidate_scripts,
            "candidateRootsWithExactTargetAction": len(bridge_rows),
            "candidateRootsWithSharedStoryControlPath": len(shared_rows),
            "storyOccurrencesWithSharedControlPath": len(shared_story_keys),
            "missingScriptFiles": len(missing_files),
            "missingStoryRecords": missing_story_records,
            "rejectedTargetActionRecords": sum(rejected.values()),
        },
        "rejectedTargetActionReasons": dict(sorted(rejected.items())),
        "missingScriptFiles": missing_files,
        "bridgeRows": bridge_rows,
        "boundary": {
            "dynamicSceneTargetBridgeFound": bool(bridge_rows),
            "sharedLevelScriptControlPathFound": bool(shared_rows),
            "missionActivationBridgeFound": False,
            "classification":
                "exact_local_context_without_mission_activation_edge",
            "missionGraphAction": "none",
            "promotionRequirement": (
                "a typed serialized or runtime edge must show that the "
                "DynamicScene mission condition activates the matched "
                "LevelScript header/action chain"
            ),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    boundary = report.get("boundary") or {}
    lines = [
        "# DynamicScene to LevelScript Action Bridge Audit",
        "",
        "## Result",
        "",
        (
            f"- Story-bearing identity roots inspected: "
            f"`{counts.get('storyIdentityRootsInspected', 0)}`"
        ),
        (
            f"- Roots with an exact typed DynamicScene target action: "
            f"`{counts.get('candidateRootsWithExactTargetAction', 0)}`"
        ),
        (
            f"- Roots sharing an exact LevelScript control path with Story: "
            f"`{counts.get('candidateRootsWithSharedStoryControlPath', 0)}`"
        ),
        (
            f"- Story occurrences on those shared paths: "
            f"`{counts.get('storyOccurrencesWithSharedControlPath', 0)}`"
        ),
        (
            f"- Mission activation bridge found: "
            f"`{str(bool(boundary.get('missionActivationBridgeFound'))).lower()}`"
        ),
        f"- Mission graph action: `{boundary.get('missionGraphAction', 'none')}`",
        "",
        "## Exact bridge rows",
        "",
        "| Scene | Logic id | Mission conditions | Typed action | Story on shared path | Classification |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    rows = report.get("bridgeRows") or []
    if not rows:
        lines.append("| — | — | — | — | — | — |")
    for row in rows:
        condition_bits: list[str] = []
        for control in row.get("missionControls") or []:
            for condition in control.get("conditions") or []:
                operator = "=" if condition.get("isSame") else "!="
                condition_bits.append(
                    f"{condition.get('identifier')} {operator} {condition.get('state')}"
                )
        action_bits = [
            (
                f"{action.get('actionName')}@{action.get('recordOffset')} "
                f"visible={str(bool(action.get('visible'))).lower()}"
            )
            for action in row.get("exactTargetActions") or []
        ]
        lines.append(
            "| "
            + " | ".join(
                str(value).replace("|", "\\|")
                for value in (
                    row.get("scene") or "—",
                    row.get("logicId") or "—",
                    ", ".join(condition_bits) or "—",
                    ", ".join(action_bits) or "—",
                    ", ".join(row.get("sharedStoryKeys") or []) or "—",
                    row.get("classification") or "—",
                )
            )
            + " |"
        )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        (
            "The target parameter is an authored "
            "`DynamicSceneEntityPtr`, so an admitted equality is a direct "
            "LevelScript-to-DynamicScene identity edge. When both actions share "
            "one serialized event/action path, the Story and decoration action "
            "also share exact local LevelScript control flow."
        ),
        "",
        (
            "The DynamicScene `MissionControlComp` still controls the root's "
            "state/availability. No decoded field or runtime call yet proves "
            "that this mission condition starts the LevelScript event header. "
            "Therefore mission owner, Story binding, and order remain unresolved."
        ),
        "",
        (
            f"Promotion requirement: {boundary.get('promotionRequirement', '')}"
        ),
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--identity-audit",
        type=Path,
        default=DEFAULT_IDENTITY_AUDIT,
    )
    parser.add_argument(
        "--streaming-level-script-root",
        type=Path,
        default=DEFAULT_STREAMING_ROOT,
    )
    parser.add_argument(
        "--persistent-level-script-root",
        type=Path,
        default=DEFAULT_PERSISTENT_ROOT,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    identity = json.loads(args.identity_audit.read_text(encoding="utf-8"))
    report = build_audit(
        identity,
        identity_path=args.identity_audit,
        streaming_root=args.streaming_level_script_root,
        persistent_root=args.persistent_level_script_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(json.dumps(report["counts"], indent=2))
    print(f"wrote {args.out}")
    print(f"wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
