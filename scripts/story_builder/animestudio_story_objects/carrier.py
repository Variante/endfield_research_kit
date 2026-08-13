#!/usr/bin/env python3
"""Find exact same-object Story/owner/runtime identifiers in an object index.

This audit consumes only a completed, hash-validated AnimeStudio merged object
index. It produces review candidates, not Story ownership or order edges:
serialized field co-membership still needs native consumer semantics before it
can be promoted into the Mission Pipeline or source partial order.

This is the builder-owned carrier stage used by ``audit_story_objects.py``.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
try:
    from animestudio_object_index import MergeError, validate_identity
    from common import md_escape, read_json
    from export_full_from_game import (
        animestudio_object_index_dir,
        load_animestudio_object_index_summary,
    )
except ModuleNotFoundError:  # imported as ``scripts.story_builder``
    from scripts.animestudio_object_index import MergeError, validate_identity
    from scripts.common import md_escape, read_json
    from scripts.export_full_from_game import (
        animestudio_object_index_dir,
        load_animestudio_object_index_summary,
    )
SCHEMA = "animestudioStoryCarrierAudit.v3"
DEFAULT_GAP_QUEUE = (
    ROOT / "reports" / "mission_order" / "source_story_gap_queue_CN.json"
)
DEFAULT_SOURCES = ("StreamingAssets", "Persistent")

STORY_ID_FIELDS = frozenset({
    "blackid",
    "contentid",
    "cutsceneid",
    "dialogid",
    "langkey",
    "radioid",
    "remotecommid",
    "snsid",
    "storyid",
    "storykey",
    "textid",
})
OWNER_ID_FIELDS = frozenset({
    "linkmissionid",
    "missionid",
    "questid",
    "relatedmissionid",
})
RUNTIME_ID_FIELDS = frozenset({
    "levelscriptid",
    "sceneid",
    "scenenumid",
    "scriptid",
})
ARRAY_SUFFIX_RE = re.compile(r"\[[0-9]+\]$")
GENDERED_CUTSCENE_TARGET_RE = re.compile(
    r"^(?:f|m|fm)_(cutscene_.+)$",
    re.IGNORECASE,
)


class AuditError(RuntimeError):
    pass


def normalized_leaf(path: str) -> str:
    leaf = str(path or "").rsplit(".", 1)[-1]
    while ARRAY_SUFFIX_RE.search(leaf):
        leaf = ARRAY_SUFFIX_RE.sub("", leaf)
    return re.sub(r"[^a-z0-9]", "", leaf.lower())


def scalar_field_class(path: str) -> str:
    leaf = normalized_leaf(path)
    if leaf in STORY_ID_FIELDS:
        return "story_identifier"
    if leaf in OWNER_ID_FIELDS:
        return "owner_identifier"
    if leaf in RUNTIME_ID_FIELDS:
        return "runtime_identifier"
    return "untyped_scalar"


def meaningful_identifier_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return bool(value.strip())
    return False


def load_gap_targets(path: Path) -> dict[str, set[str]]:
    payload = read_json(path, {})
    missions = payload.get("missions") if isinstance(payload, dict) else None
    if not isinstance(missions, list):
        raise AuditError(f"{path}: missing missions array")
    targets: dict[str, set[str]] = defaultdict(set)
    for row in missions:
        if not isinstance(row, dict):
            continue
        mission = str(row.get("mission") or "").strip()
        if not mission:
            continue
        for key in row.get("coreIsolatedSceneKeys") or []:
            story_key = str(key or "").strip()
            if story_key:
                targets[story_key].add(mission)
    if not targets:
        raise AuditError(f"{path}: no core-isolated Story keys")
    return dict(targets)


def target_set_sha256(target_missions: dict[str, set[str]]) -> str:
    """Hash the exact key/mission target set independently of queue scoring."""
    canonical = {
        key: sorted(target_missions[key])
        for key in sorted(target_missions)
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def scalar_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for index, item in enumerate(row.get("scalars") or []):
        shape_valid = (
            isinstance(item, list)
            and len(item) == 3
            and isinstance(item[0], str)
            and item[1] in {"s", "i", "b"}
        )
        value_valid = bool(
            shape_valid
            and (
                (item[1] == "s" and isinstance(item[2], str))
                or (
                    item[1] == "i"
                    and isinstance(item[2], int)
                    and not isinstance(item[2], bool)
                )
                or (item[1] == "b" and isinstance(item[2], bool))
            )
        )
        if not value_valid:
            identity = row.get("object")
            identity = identity if isinstance(identity, dict) else {}
            raise AuditError(
                "malformed scalar row: "
                f"source={identity.get('source')!r} "
                f"serializedFile={identity.get('serializedFile')!r} "
                f"pathId={identity.get('pathId')!r} index={index}; "
                "expected [path, type, value] with "
                "s:string, i:integer, or b:boolean; "
                f"actual={item!r}"
            )
        values.append({
            "path": item[0],
            "type": item[1],
            "value": item[2],
            "fieldClass": scalar_field_class(item[0]),
        })
    return values


def canonical_target_story_key(
    value: Any,
    target_missions: dict[str, set[str]],
) -> str:
    """Resolve an exact scalar value to the audited canonical Story key.

    Gendered root Timeline assets serialize ``f_cutscene_*``,
    ``m_cutscene_*``, or ``fm_cutscene_*`` while the Story builder
    intentionally groups them under the canonical ``cutscene_*`` key. This
    matcher strips only that exact gender prefix; component suffixes, locale
    suffixes, hashes, and fuzzy spellings are deliberately not normalized.
    """
    if not isinstance(value, str):
        return ""
    story_value = value.strip()
    if story_value in target_missions:
        return story_value
    match = GENDERED_CUTSCENE_TARGET_RE.fullmatch(story_value)
    canonical = match.group(1) if match else ""
    return canonical if canonical in target_missions else ""


def mission_from_quest_id(value: str) -> str:
    text = str(value or "").strip()
    if "_q#" in text:
        return text.split("_q#", 1)[0]
    return ""


def owner_missions(owner_fields: list[dict[str, Any]]) -> set[str]:
    missions: set[str] = set()
    for field in owner_fields:
        value = str(field.get("value") or "").strip()
        leaf = normalized_leaf(str(field.get("path") or ""))
        if not value:
            continue
        if leaf == "questid":
            mission = mission_from_quest_id(value)
            if mission:
                missions.add(mission)
        else:
            missions.add(value)
    return missions


def object_type_identity(row: dict[str, Any]) -> dict[str, Any]:
    script = row.get("script")
    script = script if isinstance(script, dict) else {}
    script_name = str(script.get("fullName") or "").strip()
    assembly = str(script.get("assembly") or "").strip()
    object_type = str(row.get("type") or "").strip()
    typed = bool(script_name) or (object_type and object_type != "MonoBehaviour")
    return {
        "objectType": object_type,
        "scriptFullName": script_name,
        "scriptAssembly": assembly,
        "typed": typed,
    }


def audit_object_row(
    row: dict[str, Any],
    target_missions: dict[str, set[str]],
    source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    counts: Counter[str] = Counter()
    if row.get("recordType") != "object":
        return [], [], counts
    counts["objectsScanned"] += 1
    if row.get("schemaVersion") != 1:
        raise AuditError("object row uses unsupported schemaVersion")
    identity = row.get("object")
    try:
        validate_identity(identity, "object-index row")
    except MergeError as exc:
        raise AuditError(str(exc)) from exc
    scalars = scalar_rows(row)
    matches = [
        (field, story_key)
        for field in scalars
        if (
            story_key := canonical_target_story_key(
                field["value"],
                target_missions,
            )
        )
    ]
    if not matches:
        return [], [], counts
    counts["objectsWithExactTargetValue"] += 1

    owner_fields = [
        field for field in scalars
        if field["fieldClass"] == "owner_identifier"
        and meaningful_identifier_value(field["value"])
    ]
    runtime_fields = [
        field for field in scalars
        if field["fieldClass"] == "runtime_identifier"
        and meaningful_identifier_value(field["value"])
    ]
    type_identity = object_type_identity(row)
    fully_decoded = (
        row.get("decodeStatus") == "decoded"
        and row.get("scalarsTruncated") is not True
        and isinstance(row.get("schemaId"), str)
        and bool(row.get("schemaId"))
    )
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for match, story_key in matches:
        expected_missions = set(target_missions[story_key])
        recovered_owner_missions = owner_missions(owner_fields)
        if not recovered_owner_missions:
            agreement = "no_owner_identifier"
        elif recovered_owner_missions & expected_missions:
            agreement = (
                "owner_agrees_with_gap_mission"
                if recovered_owner_missions <= expected_missions
                else "mixed_owner_missions"
            )
        else:
            agreement = "owner_conflicts_with_gap_mission"

        reasons: list[str] = []
        if match["fieldClass"] != "story_identifier":
            reasons.append("story_value_is_not_in_a_typed_story_identifier_field")
        if not fully_decoded:
            reasons.append("object_is_not_a_complete_decoded_schema_row")
        if not type_identity["typed"]:
            reasons.append("object_type_or_monoscript_identity_is_unresolved")
        if not owner_fields and not runtime_fields:
            reasons.append("no_owner_or_runtime_identifier_in_same_object")

        candidate = {
            "storyKey": story_key,
            "sourceStoryValue": str(match["value"]),
            "storyValueNormalization": (
                "exact"
                if str(match["value"]) == story_key
                else "canonical_cutscene_variant"
            ),
            "expectedGapMissions": sorted(expected_missions),
            "source": source,
            "object": identity,
            "type": type_identity,
            "storyField": match,
            "ownerFields": owner_fields,
            "runtimeFields": runtime_fields,
            "ownerMissionAgreement": agreement,
            "evidenceBoundary": (
                "exact same serialized object and typed scalar fields only; "
                "native consumer semantics are still required before ownership "
                "or order promotion"
            ),
            "edgeStatus": "no_edge_candidate_only",
        }
        scene_context = row.get("sceneContext")
        if isinstance(scene_context, dict):
            candidate["sceneContext"] = scene_context
            counts["exactValueMatchesWithSceneContext"] += 1
            if scene_context.get("worldPositionStatus") == "exact_transform_hierarchy":
                counts["exactValueMatchesWithExactWorldPosition"] += 1
        if reasons:
            candidate["rejectionReasons"] = reasons
            rejected.append(candidate)
            counts["rejectedExactValueMatches"] += 1
        else:
            candidate["candidateStatus"] = (
                "exact_same_object_story_owner_and_runtime_identifiers"
                if owner_fields and runtime_fields
                else (
                    "exact_same_object_story_and_owner_identifiers"
                    if owner_fields
                    else "exact_same_object_story_and_runtime_identifiers"
                )
            )
            accepted.append(candidate)
            counts["typedCarrierCandidates"] += 1
            counts[candidate["candidateStatus"]] += 1
            counts[agreement] += 1
    return accepted, rejected, counts


def audit_object_rows(
    rows: Iterable[dict[str, Any]],
    target_missions: dict[str, set[str]],
    source: str,
    *,
    rejected_limit: int = 100,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    mono_scripts = 0
    for row in rows:
        if not isinstance(row, dict):
            raise AuditError("object-index row is not an object")
        if row.get("recordType") == "monoScript":
            mono_scripts += 1
            continue
        accepted_rows, rejected_rows, row_counts = audit_object_row(
            row,
            target_missions,
            source,
        )
        counts.update(row_counts)
        candidates.extend(accepted_rows)
        remaining = max(0, rejected_limit - len(rejected))
        rejected.extend(rejected_rows[:remaining])
    candidates.sort(key=lambda row: (
        row["storyKey"],
        row["source"],
        row["object"]["serializedFile"],
        row["object"]["source"],
        row["object"]["sourceOffset"],
        row["object"]["pathId"],
        row["storyField"]["path"],
    ))
    rejected.sort(key=lambda row: (
        row["storyKey"],
        row["source"],
        row["object"]["serializedFile"],
        row["object"]["sourceOffset"],
        row["object"]["pathId"],
    ))
    counts["monoScriptsScanned"] = mono_scripts
    for key in (
        "objectsScanned",
        "objectsWithExactTargetValue",
        "typedCarrierCandidates",
        "rejectedExactValueMatches",
    ):
        counts.setdefault(key, 0)
    return {
        "counts": dict(sorted(counts.items())),
        "candidates": candidates,
        "rejectedExactValueMatchSamples": rejected,
    }


def iter_gzip_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise AuditError(f"{path}:{line_number}: row is not an object")
                yield value
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"{path}: cannot read merged object index: {exc}") from exc


def scan_published_source(
    output_root: Path,
    source: str,
    target_missions: dict[str, set[str]],
) -> dict[str, Any]:
    summary = load_animestudio_object_index_summary(output_root, source)
    if summary is None:
        raise AuditError(
            f"{source}: no published object index; run an explicit installed-game "
            "Story/all export with --animestudio-object-index"
        )
    if summary.get("complete") is not True:
        errors = "; ".join(str(value) for value in summary.get("errors") or [])
        raise AuditError(f"{source}: published object index is invalid: {errors}")
    output = (summary.get("outputs") or {}).get("objects") or {}
    relative_name = str(output.get("path") or "")
    if not relative_name or Path(relative_name).name != relative_name:
        raise AuditError(f"{source}: merged objects output path is invalid")
    index_dir = animestudio_object_index_dir(output_root, source)
    object_path = index_dir / relative_name
    result = audit_object_rows(
        iter_gzip_jsonl(object_path),
        target_missions,
        source,
    )
    expected_objects = int((summary.get("counts") or {}).get("objects") or 0)
    if result["counts"].get("objectsScanned", 0) != expected_objects:
        raise AuditError(
            f"{source}: merged object count mismatch: "
            f"{result['counts'].get('objectsScanned', 0)} parsed, "
            f"{expected_objects} published"
        )
    result["index"] = {
        "source": source,
        "summary": str(index_dir / "summary.json"),
        "objects": str(object_path),
        "mergeContract": summary.get("mergeContract"),
        "stageSignatureSha256": (
            (summary.get("stageSignature") or {}).get("sha256")
        ),
    }
    return result


def build_report(
    output_root: Path,
    sources: Iterable[str],
    gap_queue: Path,
) -> dict[str, Any]:
    target_missions = load_gap_targets(gap_queue)
    source_results = [
        scan_published_source(output_root, source, target_missions)
        for source in sources
    ]
    totals: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for result in source_results:
        totals.update(result["counts"])
        candidates.extend(result["candidates"])
        rejected.extend(result["rejectedExactValueMatchSamples"])
    candidates.sort(key=lambda row: (
        row["storyKey"],
        row["source"],
        row["object"]["serializedFile"],
        row["object"]["pathId"],
    ))
    candidate_story_keys = sorted({
        row["storyKey"]
        for row in candidates
    })
    target_story_key_missions = {
        key: sorted(target_missions[key])
        for key in sorted(target_missions)
    }
    return {
        "_schema": SCHEMA,
        "gapQueue": str(gap_queue),
        "targetField": "coreIsolatedSceneKeys",
        "targetSetSha256": target_set_sha256(target_missions),
        "targetStoryKeys": len(target_missions),
        "targetStoryKeyMissions": target_story_key_missions,
        "sources": [result["index"] for result in source_results],
        "summary": {
            **dict(sorted(totals.items())),
            "typedCarrierCandidates": len(candidates),
            "candidateStoryKeys": len(candidate_story_keys),
            "noCandidateStoryKeys": (
                len(target_missions) - len(candidate_story_keys)
            ),
        },
        "candidateStoryKeys": candidate_story_keys,
        "noCandidateStoryKeys": sorted(
            set(target_missions) - set(candidate_story_keys)
        ),
        "candidates": candidates,
        "rejectedExactValueMatchSamples": rejected[:100],
        "evidencePolicy": {
            "accepted": (
                "exact target Story value, or an exact f_/m_/fm_ root "
                "cutscene variant canonicalized by the Story builder, in a typed "
                "Story-id field; complete decoded schema row; resolved "
                "object/script type; and a typed owner or runtime id in the "
                "same serialized object"
            ),
            "notAccepted": (
                "partial/truncated objects, unresolved MonoScript identity, "
                "untyped scalar fields, substrings, names, neighboring objects, "
                "PathID proximity, filenames, OCR, or manual overrides"
            ),
            "promotionBoundary": (
                "this audit emits candidates only; native consumer semantics "
                "must independently prove ownership or playback, and a separate "
                "serialized control relation is required for any order edge"
            ),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# AnimeStudio Story Carrier Audit",
        "",
        (
            f"- Target core-isolated Story keys: `{report['targetStoryKeys']}`"
        ),
        (
            f"- Object rows scanned: "
            f"`{summary.get('objectsScanned', 0)}`"
        ),
        (
            f"- Typed same-object carrier candidates: "
            f"`{summary.get('typedCarrierCandidates', 0)}` across "
            f"`{summary.get('candidateStoryKeys', 0)}` Story keys"
        ),
        (
            f"- Keys with no typed same-object candidate: "
            f"`{summary.get('noCandidateStoryKeys', 0)}`"
        ),
        "",
        "This is a candidate audit, not an ownership or ordering graph. "
        "Every row still requires independently recovered native consumer "
        "semantics; no candidate creates an edge.",
        "",
        "## Candidates",
        "",
    ]
    candidates = report.get("candidates") or []
    if not candidates:
        lines.append("_No typed same-object carrier candidates._")
    else:
        lines.extend([
            "| Story | Type | Owner agreement | Source object |",
            "|---|---|---|---|",
        ])
        for row in candidates:
            identity = row["object"]
            type_name = (
                row["type"].get("scriptFullName")
                or row["type"].get("objectType")
                or "unknown"
            )
            object_text = (
                f"{identity['serializedFile']} / "
                f"{identity['source']}@{identity['sourceOffset']} / "
                f"PathID {identity['pathId']}"
            )
            lines.append(
                f"| `{md_escape(row['storyKey'])}` | "
                f"`{md_escape(type_name)}` | "
                f"`{md_escape(row['ownerMissionAgreement'])}` | "
                f"`{md_escape(object_text)}` |"
            )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        f"- Accepted: {report['evidencePolicy']['accepted']}.",
        f"- Rejected: {report['evidencePolicy']['notAccepted']}.",
        f"- Promotion: {report['evidencePolicy']['promotionBoundary']}.",
        "",
    ])
    return "\n".join(lines)
