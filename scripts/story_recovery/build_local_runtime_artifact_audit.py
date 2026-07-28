#!/usr/bin/env python3
"""Audit normal-play local artifacts for exact Story/runtime identity carriers.

This is an offline alternative to process injection. It scans only Unity
Player logs and ClientData JSON under the game's persistent-data directory.
Matches are observational candidates, never authored ownership or order edges.

Outputs:

    reports/story/recovery/local_runtime_artifact_audit.json
    reports/story/recovery/local_runtime_artifact_audit.md
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402


SCHEMA = "localRuntimeArtifactAudit.v1"
DEFAULT_STORY_INDEX = ROOT / "webui" / "data" / "lang" / "CN" / "index.json"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_#]*")
LEVELSCRIPT_ERROR_RE = re.compile(
    r"(?P<error>ErrSceneLevelScript[A-Za-z0-9_]+).*?"
    r"\[scene\s+(?P<scene>[A-Za-z0-9_]+)",
)
ARRAY_SUFFIX_RE = re.compile(r"\[[0-9]+\]$")

STORY_FIELDS = frozenset({
    "blackid",
    "contentid",
    "cutsceneid",
    "dialogid",
    "radioid",
    "remotecommid",
    "snsid",
    "storyid",
    "storykey",
    "textid",
})
OWNER_FIELDS = frozenset({
    "linkmissionid",
    "missionid",
    "questid",
    "relatedmissionid",
})
RUNTIME_FIELDS = frozenset({
    "levelid",
    "levelscriptid",
    "sceneid",
    "scenename",
    "scenenumid",
    "scriptid",
})


class AuditError(RuntimeError):
    pass


def default_local_root() -> Path:
    profile = os.environ.get("USERPROFILE")
    if not profile:
        raise AuditError("USERPROFILE is unavailable; pass --local-root")
    return Path(profile) / "AppData" / "LocalLow" / "Hypergryph" / "Endfield"


def normalized_leaf(value: str) -> str:
    leaf = str(value or "").rsplit(".", 1)[-1]
    while ARRAY_SUFFIX_RE.search(leaf):
        leaf = ARRAY_SUFFIX_RE.sub("", leaf)
    return re.sub(r"[^a-z0-9]", "", leaf.lower())


def load_story_vocabulary(path: Path) -> tuple[set[str], set[str]]:
    payload = read_json(path, {})
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise AuditError(f"{path}: missing entries array")
    story_keys: set[str] = set()
    mission_ids: set[str] = set()
    for row in entries:
        if not isinstance(row, dict):
            continue
        story_key = str(row.get("k") or "").strip()
        mission_id = str(row.get("m") or "").strip()
        if story_key:
            story_keys.add(story_key)
        if mission_id:
            mission_ids.add(mission_id)
    if not story_keys:
        raise AuditError(f"{path}: no Story keys")
    return story_keys, mission_ids


def exact_known_tokens(
    text: str,
    vocabulary: set[str],
) -> list[str]:
    return sorted(set(TOKEN_RE.findall(text)) & vocabulary)


def meaningful_scalar(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return isinstance(value, str) and bool(value.strip())


def typed_fields(row: dict[str, Any], names: frozenset[str]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for key, value in row.items():
        if normalized_leaf(key) not in names or not meaningful_scalar(value):
            continue
        values.append({"field": str(key), "value": value})
    return values


def audit_json_object(
    value: Any,
    *,
    story_keys: set[str],
    mission_ids: set[str],
    relative_file: str,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    exact_story_values: set[str] = set()
    exact_mission_values: set[str] = set()
    candidates: list[dict[str, Any]] = []

    def walk(item: Any, path: str) -> None:
        if isinstance(item, dict):
            story_fields = typed_fields(item, STORY_FIELDS)
            owner_fields = typed_fields(item, OWNER_FIELDS)
            runtime_fields = typed_fields(item, RUNTIME_FIELDS)
            typed_story = sorted({
                str(field["value"])
                for field in story_fields
                if str(field["value"]) in story_keys
            })
            typed_missions = sorted({
                str(field["value"]).split("_q#", 1)[0]
                for field in owner_fields
                if (
                    str(field["value"]) in mission_ids
                    or "_q#" in str(field["value"])
                )
            })
            for scalar in item.values():
                if not isinstance(scalar, str):
                    continue
                exact_story_values.update(exact_known_tokens(scalar, story_keys))
                exact_mission_values.update(exact_known_tokens(scalar, mission_ids))
            if typed_story:
                counts["objectsWithTypedStoryId"] += 1
            if owner_fields:
                counts["objectsWithTypedOwnerId"] += 1
            if runtime_fields:
                counts["objectsWithTypedRuntimeId"] += 1
            if typed_story and (owner_fields or runtime_fields):
                candidates.append({
                    "sourceFile": relative_file,
                    "jsonPath": path or "$",
                    "storyKeys": typed_story,
                    "ownerFields": owner_fields,
                    "ownerMissions": typed_missions,
                    "runtimeFields": runtime_fields,
                    "status": "observational_same_object_candidate_no_edge",
                })
            for key, child in item.items():
                child_path = f"{path}.{key}" if path else f"$.{key}"
                walk(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]")

    walk(value, "$")
    counts["exactStoryValues"] = len(exact_story_values)
    counts["exactMissionValues"] = len(exact_mission_values)
    counts["sameObjectCandidates"] = len(candidates)
    return {
        "counts": dict(counts),
        "storyKeys": sorted(exact_story_values),
        "missionIds": sorted(exact_mission_values),
        "candidates": candidates,
    }


def audit_log_lines(
    lines: Iterable[str],
    *,
    story_keys: set[str],
    mission_ids: set[str],
    relative_file: str,
) -> dict[str, Any]:
    story_matches: list[dict[str, Any]] = []
    levelscript_errors: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        matched_story = exact_known_tokens(line, story_keys)
        matched_missions = exact_known_tokens(line, mission_ids)
        if matched_story:
            story_matches.append({
                "sourceFile": relative_file,
                "line": line_number,
                "storyKeys": matched_story,
                "missionIdsOnSameLine": matched_missions,
                "status": "observational_log_line_no_edge",
            })
        error_match = LEVELSCRIPT_ERROR_RE.search(line)
        if error_match:
            levelscript_errors.append({
                "sourceFile": relative_file,
                "line": line_number,
                "error": error_match.group("error"),
                "scene": error_match.group("scene"),
                "status": "runtime_error_context_no_story_or_mission_owner",
            })
    return {
        "storyMatches": story_matches,
        "levelScriptErrors": levelscript_errors,
    }


def discover_inputs(local_root: Path) -> list[Path]:
    files = [
        path
        for path in local_root.glob("Player*.log")
        if path.is_file()
    ]
    client_data = local_root / "ClientData"
    if client_data.is_dir():
        files.extend(path for path in client_data.rglob("*.json") if path.is_file())
    return sorted(set(files), key=lambda path: path.as_posix().lower())


def report_relative_path(path: Path, local_root: Path) -> str:
    parts = list(path.relative_to(local_root).parts)
    if (
        len(parts) >= 3
        and parts[0].lower() == "clientdata"
        and parts[1].lower() == "user"
    ):
        parts[2] = "<account>"
    return "/".join(parts)


def build_audit(
    local_root: Path,
    story_index: Path,
) -> dict[str, Any]:
    if not local_root.is_dir():
        raise AuditError(f"local runtime root does not exist: {local_root}")
    story_keys, mission_ids = load_story_vocabulary(story_index)
    inputs = discover_inputs(local_root)
    file_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    story_log_matches: list[dict[str, Any]] = []
    levelscript_errors: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for path in inputs:
        relative = report_relative_path(path, local_root)
        row: dict[str, Any] = {
            "sourceFile": relative,
            "bytes": path.stat().st_size,
        }
        counts["filesScanned"] += 1
        counts["bytesScanned"] += row["bytes"]
        if path.suffix.lower() == ".json":
            counts["jsonFiles"] += 1
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                row["status"] = "unreadable_json"
                row["errorType"] = type(exc).__name__
                counts["unreadableFiles"] += 1
            else:
                result = audit_json_object(
                    payload,
                    story_keys=story_keys,
                    mission_ids=mission_ids,
                    relative_file=relative,
                )
                row["status"] = "scanned_json"
                row["counts"] = result["counts"]
                row["storyKeys"] = result["storyKeys"]
                row["missionIds"] = result["missionIds"]
                candidates.extend(result["candidates"])
        else:
            counts["logFiles"] += 1
            try:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    result = audit_log_lines(
                        handle,
                        story_keys=story_keys,
                        mission_ids=mission_ids,
                        relative_file=relative,
                    )
            except OSError as exc:
                row["status"] = "unreadable_log"
                row["errorType"] = type(exc).__name__
                counts["unreadableFiles"] += 1
            else:
                row["status"] = "scanned_log"
                row["storyMatchLines"] = len(result["storyMatches"])
                row["levelScriptErrorLines"] = len(result["levelScriptErrors"])
                story_log_matches.extend(result["storyMatches"])
                levelscript_errors.extend(result["levelScriptErrors"])
        file_rows.append(row)

    counts["knownStoryVocabulary"] = len(story_keys)
    counts["knownMissionVocabulary"] = len(mission_ids)
    counts["observedStoryLogLines"] = len(story_log_matches)
    counts["sameObjectCandidates"] = len(candidates)
    counts["levelScriptRuntimeErrors"] = len(levelscript_errors)
    classification = (
        "observational_candidates_require_manual_schema_review"
        if candidates or story_log_matches
        else "no_local_story_or_typed_identity_carrier"
    )
    return {
        "_schema": SCHEMA,
        "_generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "kind": "unity_persistent_data",
            "label": "Hypergryph/Endfield",
            "absolutePathRecorded": False,
            "inputPolicy": "Player*.log and ClientData/**/*.json only",
        },
        "storyIndex": story_index.relative_to(ROOT).as_posix()
        if story_index.is_relative_to(ROOT)
        else story_index.name,
        "classification": classification,
        "edgeStatus": "no_ownership_or_order_edges",
        "counts": dict(counts),
        "observationalCandidates": candidates,
        "storyLogMatches": story_log_matches,
        "levelScriptRuntimeErrors": levelscript_errors,
        "files": file_rows,
        "evidencePolicy": {
            "acceptedCandidate": (
                "exact known Story id in a typed JSON Story field beside a typed "
                "owner/runtime field, or an exact known Story id in one Player log line"
            ),
            "rejected": (
                "substrings, UI preference names, filename mission fragments, "
                "timestamps, neighboring JSON objects, and LevelScript errors without "
                "a Story plus mission/quest identity"
            ),
            "promotionBoundary": (
                "normal-play local artifacts are observational; no candidate creates "
                "authored ownership, playback, branch, completion, or order evidence"
            ),
            "privacy": (
                "reports retain relative filenames, exact game identifiers, counts, "
                "and line numbers only; arbitrary log text and account identifiers "
                "are not copied"
            ),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    counts = payload["counts"]
    lines = [
        "# Local Runtime Artifact Audit",
        "",
        f"- Classification: `{md_escape(payload['classification'])}`",
        f"- Files / bytes scanned: `{counts.get('filesScanned', 0)}` / "
        f"`{counts.get('bytesScanned', 0)}`",
        f"- Player logs / ClientData JSON: `{counts.get('logFiles', 0)}` / "
        f"`{counts.get('jsonFiles', 0)}`",
        f"- Exact Story-bearing log lines: "
        f"`{counts.get('observedStoryLogLines', 0)}`",
        f"- Typed same-object candidates: "
        f"`{counts.get('sameObjectCandidates', 0)}`",
        f"- LevelScript runtime errors without Story ownership: "
        f"`{counts.get('levelScriptRuntimeErrors', 0)}`",
        "- Story ownership/order edges added: `0`",
        "",
        "## Result",
        "",
    ]
    if payload["observationalCandidates"] or payload["storyLogMatches"]:
        lines.append(
            "Exact normal-play observations exist, but remain candidate-only until "
            "their runtime schema and session context are independently validated."
        )
    else:
        lines.append(
            "The current normal-play Player logs and ClientData JSON contain no exact "
            "known Story id in a log line and no typed same-object Story plus "
            "mission/quest/runtime carrier."
        )
    lines.extend([
        "",
        "## Runtime diagnostics",
        "",
    ])
    errors = payload["levelScriptRuntimeErrors"]
    if not errors:
        lines.append("_No LevelScript runtime errors matched._")
    else:
        lines.extend([
            "| file | line | error | scene |",
            "| --- | ---: | --- | --- |",
        ])
        for row in errors:
            lines.append(
                f"| `{md_escape(row['sourceFile'])}` | {row['line']} | "
                f"`{md_escape(row['error'])}` | `{md_escape(row['scene'])}` |"
            )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        payload["evidencePolicy"]["promotionBoundary"].capitalize() + ". "
        + payload["evidencePolicy"]["privacy"].capitalize() + ".",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-root", type=Path)
    parser.add_argument("--story-index", type=Path, default=DEFAULT_STORY_INDEX)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    local_root = args.local_root or default_local_root()
    try:
        payload = build_audit(local_root, args.story_index)
    except AuditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.report_root.mkdir(parents=True, exist_ok=True)
    json_path = args.report_root / "local_runtime_artifact_audit.json"
    md_path = args.report_root / "local_runtime_artifact_audit.md"
    write_report_json(json_path, payload)
    write_text_if_changed(md_path, render_markdown(payload))
    print(
        "Local runtime artifact audit: "
        f"{payload['counts'].get('filesScanned', 0)} files, "
        f"{payload['counts'].get('observedStoryLogLines', 0)} Story log lines, "
        f"{payload['counts'].get('sameObjectCandidates', 0)} typed candidates"
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
