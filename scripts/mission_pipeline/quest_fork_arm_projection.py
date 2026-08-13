"""Publish hash-verified Story evidence onto Mission fork-arm projections."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

if __package__ and __package__.startswith("scripts."):
    from scripts.common import compact_dict as _compact_dict
    from scripts.common import sha256_file as _sha256_path
else:
    from common import compact_dict as _compact_dict
    from common import sha256_file as _sha256_path


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def _iter_hashed_source_references(
    value: Any,
    path: tuple[str, ...] = (),
) -> Iterable[dict[str, Any]]:
    """Yield source references that carry their own byte-identity proof.

    Recovery publishers use several evidence schemas, but their durable source
    boundary is uniform: an object names ``sourceFile`` and carries either
    ``sha256``, ``sourceSha256``, or ``rawDataSha256``.  Walking that shape keeps
    branch attachment independent of particular action, condition, dialog, or
    mission ids while excluding unverified path-like diagnostic strings.
    """
    if isinstance(value, dict):
        source_file = value.get("sourceFile")
        source_hash = (
            value.get("sha256")
            or value.get("sourceSha256")
            or value.get("rawDataSha256")
        )
        if isinstance(source_file, str) and source_file and source_hash:
            yield {
                "sourceFile": source_file,
                "sha256": str(source_hash),
                "kind": str(
                    value.get("kind")
                    or value.get("evidenceKind")
                    or value.get("sourceType")
                    or "hashed_source_reference"
                ),
                "relationship": str(
                    value.get("relationship")
                    or value.get("evidenceKind")
                    or "arm_hashed_source_reference"
                ),
                "evidencePath": ".".join(path),
            }
        for key, child in value.items():
            yield from _iter_hashed_source_references(child, (*path, str(key)))
    elif isinstance(value, list):
        for child in value:
            yield from _iter_hashed_source_references(child, path)


def publish_quest_fork_arm_evidence(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
    *,
    actionbase_formatter_name_audit: dict[str, Any],
) -> dict[str, Any]:
    """Attach exact Story evidence to sibling-exclusive authored fork arms.

    The corridor membership comes only from MissionRuntime predecessor topology.
    Story rows come from the generated typed mission sidecar, whose action names
    are backed by the complete installed-binary ActionBase formatter audit. The
    exact MissionRuntime questDic and every nested, hash-bearing source reference
    on a corridor quest are validated and attached by their shared data shape.
    OCR and manual order are deliberately absent.
    """
    validator = "quest_fork_arm_evidence"
    validation_scope = {"missionId": "", "questId": ""}

    def validation_failure(
        gate: str,
        expected: Any,
        actual: Any,
        source: str,
        source_hashes: dict[str, str] | None = None,
    ) -> RuntimeError:
        failure = _compact_dict({
            "validator": validator,
            "gate": gate,
            **validation_scope,
            "expected": expected,
            "actual": actual,
            "sourceFile": str(source),
            "sourceHashes": source_hashes or {},
        })
        index["questForkArmEvidence"] = {
            "schema": "missionQuestForkArmEvidence.v2",
            "validation": {
                "status": "validation_failed",
                "failures": [failure],
            },
        }
        _write_json(output_root / "index.json", index)
        return RuntimeError(
            f"validator={validator} gate={gate} "
            f"mission={validation_scope['missionId'] or '-'} "
            f"quest={validation_scope['questId'] or '-'} "
            f"expected={expected!r} actual={actual!r} source={source} "
            f"sourceHashes={source_hashes or {}}"
        )

    audit = actionbase_formatter_name_audit
    audit_source = str(audit.get("sourceFile") or "")
    if audit.get("status") != "validated" or not audit_source:
        raise validation_failure(
            "binaryActionNameAudit",
            {"status": "validated", "sourceFile": "nonempty"},
            {"status": audit.get("status"), "sourceFile": audit_source},
            "scripts/story_builder/level_bindings.py",
        )
    audit_path = (ROOT / audit_source).resolve()
    expected_audit_hash = str(audit.get("sourceSha256") or "").upper()
    if not audit_path.is_relative_to(ROOT) or not audit_path.is_file():
        raise validation_failure(
            "binaryActionNameAuditSource",
            "fileWithinRepo",
            str(audit_path),
            audit_source,
        )
    actual_audit_hash = _sha256_path(audit_path).upper()
    if actual_audit_hash != expected_audit_hash:
        raise validation_failure(
            "binaryActionNameAuditHash",
            expected_audit_hash,
            actual_audit_hash,
            audit_source,
            {"actualSha256": actual_audit_hash},
        )
    audit_payload = _read_json(audit_path)
    audit_metadata = (
        audit_payload.get("metadata")
        if isinstance(audit_payload, dict)
        and isinstance(audit_payload.get("metadata"), dict)
        else {}
    )

    sidecar_root = story_data_root / language.upper() / "mission"
    file_cache: dict[str, dict[str, Any]] = {}

    def related_original_file(
        source_file: str,
        relationship: str,
        expected_hash: str = "",
        kind: str = "original_authored_source",
    ) -> dict[str, Any]:
        normalized = str(source_file or "").replace("\\", "/")
        cache_key = f"{normalized}\0{relationship}\0{kind}"
        cached = file_cache.get(cache_key)
        if cached is not None:
            return cached
        source_path = Path(normalized)
        if not source_path.is_absolute():
            source_path = ROOT / source_path
        source_path = source_path.resolve()
        if not source_path.is_relative_to(ROOT) and not expected_hash:
            raise validation_failure(
                "relatedOriginalFileBoundary",
                "fileWithinRepoOrPrehashedAbsolute",
                str(source_path),
                normalized,
            )
        if not source_path.is_file():
            raise validation_failure(
                "relatedOriginalFile",
                "file",
                str(source_path),
                normalized,
            )
        actual_hash = _sha256_path(source_path)
        if expected_hash and actual_hash.upper() != expected_hash.upper():
            raise validation_failure(
                "relatedOriginalFileHash",
                expected_hash.upper(),
                actual_hash.upper(),
                normalized,
                {"actualSha256": actual_hash},
            )
        row = {
            "kind": kind,
            "sourceFile": _repo_path(source_path),
            "relationship": relationship,
            "sha256": actual_hash,
        }
        file_cache[cache_key] = row
        return row

    missions = 0
    forks = 0
    arms = 0
    arms_with_story = 0
    story_placements = 0
    binary_named_action_placements = 0
    authored_source_placements = 0
    arms_with_related_files = 0
    non_story_arms_with_related_files = 0
    story_keys: set[str] = set()
    distinct_original_files: set[str] = set()
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        validation_scope["missionId"] = mission_id
        validation_scope["questId"] = ""
        mission_path = output_root / str(summary.get("file") or "")
        if not mission_path.is_file():
            continue
        payload = _read_json(mission_path)
        topology = payload.get("questTopology") if isinstance(payload, dict) else None
        mission_forks = topology.get("forks") if isinstance(topology, dict) else None
        if not mission_forks:
            continue
        sidecar_path = sidecar_root / f"{mission_id}.json"
        if not sidecar_path.is_file():
            raise validation_failure(
                "missionSidecar", "file", "missing", str(sidecar_path)
            )
        sidecar = _read_json(sidecar_path)
        flow = sidecar.get("flow") if isinstance(sidecar, dict) else None
        quest_rows = flow.get("quests") if isinstance(flow, dict) else None
        if isinstance(quest_rows, dict):
            quest_rows = list(quest_rows.values())
        if not isinstance(quest_rows, list):
            raise validation_failure(
                "missionSidecarQuests",
                "list",
                type(quest_rows).__name__,
                str(sidecar_path),
            )
        sidecar_quests = {
            str(row.get("id") or row.get("questId") or ""): row
            for row in quest_rows
            if isinstance(row, dict) and (row.get("id") or row.get("questId"))
        }
        nodes = {
            str(row.get("id") or ""): row
            for row in payload.get("nodes") or []
            if isinstance(row, dict) and row.get("id")
        }
        mission = payload.get("mission") if isinstance(payload, dict) else None
        mission_source = str(mission.get("source") or "") if isinstance(mission, dict) else ""
        if not mission_source:
            raise validation_failure(
                "missionRuntimeSource", "nonempty", mission_source, str(mission_path)
            )
        mission_source_path = Path(mission_source)
        if not mission_source_path.is_absolute():
            mission_source_path = ROOT / mission_source_path
        mission_source_path = mission_source_path.resolve()
        if not mission_source_path.is_file():
            raise validation_failure(
                "missionRuntimeSourceFile",
                "file",
                str(mission_source_path),
                mission_source,
            )
        mission_source_hash = _sha256_path(mission_source_path)
        mission_runtime = _read_json(mission_source_path)
        authored_quest_dic = (
            mission_runtime.get("questDic")
            if isinstance(mission_runtime, dict)
            else None
        )
        if (
            not isinstance(authored_quest_dic, dict)
            or str(mission_runtime.get("missionId") or "") != mission_id
        ):
            raise validation_failure(
                "missionRuntimeQuestDictionary",
                {"missionId": mission_id, "questDic": "dict"},
                {
                    "missionId": (
                        mission_runtime.get("missionId")
                        if isinstance(mission_runtime, dict) else None
                    ),
                    "questDic": type(authored_quest_dic).__name__,
                },
                mission_source,
                {"missionRuntimeSha256": mission_source_hash},
            )
        mission_story_placements = 0
        for fork in mission_forks:
            if not isinstance(fork, dict):
                continue
            forks += 1
            for arm in fork.get("arms") or []:
                if not isinstance(arm, dict):
                    continue
                arms += 1
                validation_scope["questId"] = str(fork.get("questId") or "")
                corridor = arm.get("siblingExclusiveQuestIds")
                if not isinstance(corridor, list):
                    raise validation_failure(
                        "siblingExclusiveCorridor",
                        "list",
                        "missing",
                        str(mission_path),
                    )
                arm_quest_id = str(arm.get("questId") or "")
                source_quest_ids = corridor or ([arm_quest_id] if arm_quest_id else [])
                missing_quests = [
                    quest_id for quest_id in source_quest_ids
                    if quest_id not in sidecar_quests or quest_id not in nodes
                ]
                if missing_quests:
                    raise validation_failure(
                        "corridorQuestsResolve",
                        [],
                        missing_quests[:16],
                        str(sidecar_path),
                    )
                missing_authored_quests = [
                    quest_id for quest_id in source_quest_ids
                    if quest_id not in authored_quest_dic
                ]
                if missing_authored_quests:
                    raise validation_failure(
                        "corridorQuestsInOriginalQuestDic",
                        [],
                        missing_authored_quests[:16],
                        mission_source,
                        {"missionRuntimeSha256": mission_source_hash},
                    )
                evidence_by_signature: dict[tuple[str, ...], dict[str, Any]] = {}
                related_by_file: dict[str, dict[str, Any]] = {}
                authored_source_evidence: list[dict[str, Any]] = []
                for quest_id in source_quest_ids:
                    sidecar_quest = sidecar_quests[quest_id]
                    node = nodes[quest_id]
                    quest_related_by_file: dict[str, dict[str, Any]] = {}
                    authored_mission_file = related_original_file(
                        mission_source,
                        "exact_fork_arm_quest_definition",
                        mission_source_hash,
                        "mission_runtime",
                    )
                    quest_related_by_file[authored_mission_file["sourceFile"]] = (
                        authored_mission_file
                    )
                    related_by_file[authored_mission_file["sourceFile"]] = (
                        authored_mission_file
                    )
                    evidence_kinds = {"mission_runtime_quest_definition"}
                    for source_reference in _iter_hashed_source_references(node):
                        related = related_original_file(
                            str(source_reference["sourceFile"]),
                            str(source_reference["relationship"]),
                            str(source_reference["sha256"]),
                            str(source_reference["kind"]),
                        )
                        quest_related_by_file[related["sourceFile"]] = related
                        related_by_file[related["sourceFile"]] = related
                        evidence_kinds.add(str(source_reference["relationship"]))
                    raw_rows: list[dict[str, Any]] = []
                    if quest_id in corridor:
                        raw_rows = [
                            row for row in sidecar_quest.get("storyConnections") or []
                            if isinstance(row, dict) and row.get("key")
                        ]
                        raw_rows.extend(
                            row for row in node.get("storyScopeContexts") or []
                            if isinstance(row, dict) and row.get("key")
                        )
                    for raw in raw_rows:
                        raw_source_files = raw.get("sourceFiles")
                        if not isinstance(raw_source_files, list):
                            raw_source_files = []
                        source_files = sorted({
                            str(value).replace("\\", "/")
                            for value in [
                                raw.get("file"),
                                raw.get("sourceFile"),
                                *raw_source_files,
                            ]
                            if isinstance(value, str) and value
                        })
                        evidence = _compact_dict({
                            "questId": quest_id,
                            "key": str(raw.get("key") or ""),
                            "kind": raw.get("kind") or "",
                            "relation": raw.get("relation") or "",
                            "direction": raw.get("direction") or "",
                            "phase": raw.get("phase") or "",
                            "confidence": raw.get("confidence") or "",
                            "actionType": raw.get("actionType") or raw.get("actionName") or "",
                            "conditionType": raw.get("conditionType") or "",
                            "finishId": raw.get("finishId"),
                            "evidenceTier": raw.get("evidenceTier") or "",
                            "ownership": raw.get("ownership") or raw.get("ownershipStatus") or "",
                            "questTriggerStatus": raw.get("questTriggerStatus") or "",
                            "nativeMappingId": raw.get("nativeMappingId") or "",
                            "source": raw.get("source") or "",
                            "sourceFiles": source_files,
                        })
                        signature = tuple(str(evidence.get(key) or "") for key in (
                            "questId", "key", "relation", "direction", "phase",
                            "confidence", "source",
                        ))
                        evidence_by_signature[signature] = evidence
                        for source_file in source_files:
                            related = related_original_file(
                                source_file,
                                "fork_arm_typed_story_relation",
                            )
                            related_by_file[related["sourceFile"]] = related
                            quest_related_by_file[related["sourceFile"]] = related
                            evidence_kinds.add("fork_arm_typed_story_relation")
                    evidence_keys = {
                        str(row.get("key") or "")
                        for row in raw_rows
                    }
                    for definition in node.get("dialogTreeDefinitions") or []:
                        if not isinstance(definition, dict):
                            continue
                        scene_key = str(definition.get("sceneKey") or "")
                        if scene_key not in evidence_keys:
                            continue
                        source_file = str(definition.get("sourceFile") or "")
                        if not source_file:
                            continue
                        related = related_original_file(
                            source_file,
                            "fork_arm_observed_dialog_tree_definition",
                            str(definition.get("sourceSha256") or ""),
                        )
                        related_by_file[related["sourceFile"]] = related
                        quest_related_by_file[related["sourceFile"]] = related
                    tracking_types = sorted({
                        str(tracking.get("type") or "")
                        for objective in node.get("objectives") or []
                        if isinstance(objective, dict)
                        for tracking in objective.get("tracking") or []
                        if isinstance(tracking, dict) and tracking.get("type")
                    })
                    authored_source_evidence.append(_compact_dict({
                        "questId": quest_id,
                        "armMembership": (
                            "sibling_exclusive_corridor"
                            if quest_id in corridor
                            else "direct_successor_boundary"
                        ),
                        "evidenceKinds": sorted(evidence_kinds),
                        "conditionTypes": sorted({
                            str(value) for value in node.get("conditionTypes") or []
                            if value
                        }),
                        "clientActionTypes": sorted({
                            str(action.get("type") or "")
                            for action in node.get("clientActions") or []
                            if isinstance(action, dict) and action.get("type")
                        }),
                        "trackingTypes": tracking_types,
                        "relatedOriginalFiles": sorted(
                            quest_related_by_file.values(),
                            key=lambda row: (row["sourceFile"], row["relationship"]),
                        ),
                    }))
                evidence_rows = sorted(
                    evidence_by_signature.values(),
                    key=lambda row: (
                        _natural_quest_key(str(row.get("questId") or "")),
                        str(row.get("key") or ""),
                        str(row.get("relation") or ""),
                        str(row.get("source") or ""),
                    ),
                )
                arm["storyEvidence"] = evidence_rows
                arm["authoredSourceEvidence"] = authored_source_evidence
                arm["relatedOriginalFiles"] = sorted(
                    related_by_file.values(),
                    key=lambda row: (row["sourceFile"], row["relationship"]),
                )
                arm["storyEvidenceBoundary"] = (
                    "Every corridor quest is validated against the exact original "
                    "MissionRuntime questDic. Additional files are admitted only from "
                    "nested hash-bearing source records. Story context remains non-owning; "
                    "even direct playback or completion does not prove server arm "
                    "selection, exclusivity, or a total order."
                )
                authored_source_placements += len(authored_source_evidence)
                story_placements += len(evidence_rows)
                binary_named_action_placements += sum(
                    bool(row.get("actionType")) for row in evidence_rows
                )
                mission_story_placements += len(evidence_rows)
                if evidence_rows:
                    arms_with_story += 1
                    story_keys.update(str(row.get("key") or "") for row in evidence_rows)
                if related_by_file:
                    arms_with_related_files += 1
                    if not evidence_rows:
                        non_story_arms_with_related_files += 1
                distinct_original_files.update(related_by_file)
        order_branches = (
            (payload.get("storyOrder") or {}).get("branches")
            if isinstance(payload.get("storyOrder"), dict)
            else None
        )
        if isinstance(order_branches, dict) and order_branches.get("questForks"):
            forks_by_id = {
                str(row.get("questId") or ""): row
                for row in mission_forks
                if isinstance(row, dict) and row.get("questId")
            }
            order_branches["questForks"] = [
                forks_by_id[str(row.get("questId") or "")]
                for row in order_branches["questForks"]
                if isinstance(row, dict)
                and str(row.get("questId") or "") in forks_by_id
            ]
        summary["questForkArmStoryEvidenceCount"] = mission_story_placements
        _write_json(mission_path, payload)
        missions += 1

    result = {
        "schema": "missionQuestForkArmEvidence.v2",
        "validation": {"status": "validated", "failures": []},
        "language": language.upper(),
        "binaryActionTypeAuthority": {
            **audit,
            "gameAssemblySha256": audit_metadata.get("gameAssemblySha256"),
            "metadataSha256": audit_metadata.get("metadataSha256"),
        },
        "counts": {
            "missions": missions,
            "forks": forks,
            "arms": arms,
            "armsWithStoryEvidence": arms_with_story,
            "armsWithRelatedOriginalFiles": arms_with_related_files,
            "nonStoryArmsWithRelatedOriginalFiles": non_story_arms_with_related_files,
            "authoredQuestSourcePlacements": authored_source_placements,
            "storyEvidencePlacements": story_placements,
            "uniqueStoryKeys": len(story_keys),
            "binaryNamedActionPlacements": binary_named_action_placements,
            "distinctRelatedOriginalFiles": len(distinct_original_files),
        },
        "evidencePolicy": {
            "classification": "typed_sibling_relative_fork_arm_context",
            "ownershipPromotion": False,
            "orderPromotion": False,
            "usesOcrOrManualOrder": False,
            "boundary": (
                "MissionRuntime predecessor reachability defines each corridor. "
                "Every corridor identity must also exist in the exact original questDic. "
                "The MissionRuntime file and nested hash-bearing source records are "
                "attached generically. Empty exclusive corridors retain only their direct "
                "successor boundary identity. Arms with no Story placement remain visible "
                "without "
                "claiming server selection, exclusivity, or a total order."
            ),
        },
    }
    index["questForkArmEvidence"] = result
    _write_json(output_root / "index.json", index)
    return result

