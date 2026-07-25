#!/usr/bin/env python3
"""Find exact same-object Story/owner/runtime identifiers in an object index.

This audit consumes only a completed, hash-validated AnimeStudio merged object
index. It produces review candidates, not Story ownership or order edges:
serialized field co-membership still needs native consumer semantics before it
can be promoted into the Mission Pipeline or source partial order.

Outputs:

    reports/story/recovery/animestudio_story_carrier_audit.json
    reports/story/recovery/animestudio_story_carrier_audit.md
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from animestudio_object_index import MergeError, validate_identity  # noqa: E402
from common import md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402
from export_full_from_game import (  # noqa: E402
    animestudio_object_index_dir,
    load_animestudio_object_index_summary,
)


SCHEMA = "animestudioStoryCarrierAudit.v1"
DEFAULT_OUTPUT_ROOT = ROOT / "export_full"
DEFAULT_GAP_QUEUE = (
    ROOT / "reports" / "mission_order" / "source_story_gap_queue_CN.json"
)
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
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
        for key in row.get("actionableCoreIsolatedSceneKeys") or []:
            story_key = str(key or "").strip()
            if story_key:
                targets[story_key].add(mission)
    if not targets:
        raise AuditError(f"{path}: no actionable Story keys")
    return dict(targets)


def scalar_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for index, item in enumerate(row.get("scalars") or []):
        if (
            not isinstance(item, list)
            or len(item) != 3
            or not isinstance(item[0], str)
            or item[1] not in {"s", "i"}
            or isinstance(item[2], bool)
            or not isinstance(item[2], (str, int))
        ):
            raise AuditError(f"malformed scalar row at index {index}")
        values.append({
            "path": item[0],
            "type": item[1],
            "value": item[2],
            "fieldClass": scalar_field_class(item[0]),
        })
    return values


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
        field
        for field in scalars
        if isinstance(field["value"], str)
        and field["value"] in target_missions
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
    for match in matches:
        story_key = str(match["value"])
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
    return {
        "_schema": SCHEMA,
        "gapQueue": str(gap_queue),
        "targetStoryKeys": len(target_missions),
        "sources": [result["index"] for result in source_results],
        "summary": {
            **dict(sorted(totals.items())),
            "typedCarrierCandidates": len(candidates),
            "candidateStoryKeys": len({
                row["storyKey"] for row in candidates
            }),
        },
        "candidates": candidates,
        "rejectedExactValueMatchSamples": rejected[:100],
        "evidencePolicy": {
            "accepted": (
                "exact target Story value in a typed Story-id field, complete "
                "decoded schema row, resolved object/script type, and a typed "
                "owner or runtime id in the same serialized object"
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
            f"- Target actionable Story keys: `{report['targetStoryKeys']}`"
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--gap-queue", type=Path, default=DEFAULT_GAP_QUEUE)
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Published AnimeStudio source index to scan; repeat as needed.",
    )
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    sources = tuple(args.sources or DEFAULT_SOURCES)
    try:
        report = build_report(
            args.output_root.resolve(),
            sources,
            args.gap_queue.resolve(),
        )
    except AuditError as exc:
        raise SystemExit(f"AnimeStudio Story carrier audit failed: {exc}") from exc
    json_path = args.report_root / "animestudio_story_carrier_audit.json"
    markdown_path = args.report_root / "animestudio_story_carrier_audit.md"
    write_report_json(json_path, report)
    write_text_if_changed(markdown_path, render_markdown(report))
    print(f"AnimeStudio Story carrier audit: {markdown_path.relative_to(ROOT)}")
    print(f"AnimeStudio Story carrier data: {json_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
