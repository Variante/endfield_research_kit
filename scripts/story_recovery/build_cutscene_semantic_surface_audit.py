#!/usr/bin/env python3
"""Classify the generated Story cutscene surface by exact evidence shape.

The Story UI intentionally groups Unity Timeline cutscenes, independently
played narrative FMVs, and text-only candidates under one ``cutscene`` kind.
This audit keeps those presentation-compatible rows separated by their
underlying evidence. It consumes generated Story payloads only and does not
infer playback, mission ownership, or chronology.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cutsceneSemanticSurfaceAudit.v1"
DEFAULT_STORY_INDEX = ROOT / "webui" / "data" / "lang" / "CN" / "index.json"
DEFAULT_CONVERSATION_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"


class AuditError(RuntimeError):
    """Raised when generated Story inputs do not support an exact result."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read JSON {path}: {exc}") from exc


def classify_cutscene(key: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("key") != key:
        raise AuditError(
            f"{key}: conversation key mismatch; actual={payload.get('key')!r}"
        )
    if payload.get("kind") != "cutscene":
        raise AuditError(
            f"{key}: expected kind='cutscene'; actual={payload.get('kind')!r}"
        )
    cutscene = payload.get("cutscene")
    if not isinstance(cutscene, dict):
        raise AuditError(f"{key}: cutscene payload is missing or not an object")

    variants = [
        row for row in (cutscene.get("variants") or [])
        if isinstance(row, dict)
    ]
    parts = Counter(str(row.get("part") or "") for row in variants)
    has_components = bool(variants)
    has_root = parts["root"] > 0

    fmv_bindings = [
        row for row in (cutscene.get("levelscriptFmvBindings") or [])
        if isinstance(row, dict)
    ]
    exact_fmv_bindings = []
    for binding_index, binding in enumerate(fmv_bindings):
        sources = [
            row for row in (binding.get("sources") or [])
            if isinstance(row, dict)
        ]
        exact_sources = [
            row for row in sources
            if row.get("kind") == "levelscriptFmvAction"
            and row.get("sourceFile")
            and row.get("actionName")
            and row.get("nativeMappingId")
        ]
        if not binding.get("fmvId") or not exact_sources:
            raise AuditError(
                f"{key}: FMV binding {binding_index} lacks an exact "
                "levelscriptFmvAction source"
            )
        exact_fmv_bindings.append(binding)
    has_fmv_action = bool(exact_fmv_bindings)
    text_only_unconfirmed = bool(cutscene.get("textOnlyUnconfirmed"))

    if text_only_unconfirmed and (has_components or has_fmv_action):
        raise AuditError(
            f"{key}: textOnlyUnconfirmed conflicts with authored asset evidence"
        )
    if has_root and has_fmv_action:
        classification = "unity_timeline_plus_levelscript_fmv"
    elif has_root:
        classification = "unity_timeline_root"
    elif has_components:
        classification = "unity_timeline_components_without_root"
    elif has_fmv_action:
        classification = "levelscript_fmv_only"
    elif text_only_unconfirmed:
        classification = "text_table_only_unconfirmed"
    else:
        raise AuditError(
            f"{key}: no Unity Timeline, exact LevelScript FMV, or explicit "
            "text-only evidence classification"
        )

    return {
        "key": key,
        "mission": str(payload.get("mission") or ""),
        "classification": classification,
        "variantCount": len(variants),
        "componentAssetCounts": dict(sorted(parts.items())),
        "levelscriptFmvBindingCount": len(exact_fmv_bindings),
        "fmvIds": sorted({
            str(row.get("fmvId")) for row in exact_fmv_bindings
            if row.get("fmvId")
        }),
        "lineCount": len([
            row for row in (payload.get("lines") or [])
            if isinstance(row, dict)
        ]),
        "hasAuthoredSubtitleTrack": bool(cutscene.get("hasSubtitleTrack")),
        "audioEventCount": len(cutscene.get("audioEvents") or []),
        "playableAudioFileCount": len([
            row for row in (cutscene.get("audioFiles") or [])
            if isinstance(row, dict) and row.get("src")
        ]),
        "videoReferenceCount": len([
            row for row in (cutscene.get("videoRefs") or [])
            if isinstance(row, dict)
        ]),
        "isTransition": bool(cutscene.get("isTransition")),
        "useBlackScreen": bool(cutscene.get("useBlackScreen")),
    }


def build_report(story_index: Path, conversation_root: Path) -> dict[str, Any]:
    index = read_json(story_index)
    entries = index.get("entries") if isinstance(index, dict) else None
    if not isinstance(entries, list):
        raise AuditError(f"{story_index}: entries is not a list")
    keys = [
        str(row.get("k"))
        for row in entries
        if isinstance(row, dict) and row.get("d") == "cutscene" and row.get("k")
    ]
    if len(keys) != len(set(keys)):
        duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
        raise AuditError(f"duplicate cutscene index keys: {duplicates[:8]}")

    rows = []
    for key in keys:
        path = conversation_root / f"{key}.json"
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise AuditError(f"{path}: conversation payload is not an object")
        rows.append(classify_cutscene(key, payload))
    rows.sort(key=lambda row: row["key"])
    classifications = Counter(row["classification"] for row in rows)
    return {
        "_schema": SCHEMA,
        "storyIndex": str(story_index),
        "conversationRoot": str(conversation_root),
        "summary": {
            "cutsceneRows": len(rows),
            "classifications": dict(sorted(classifications.items())),
            "withLocalizedText": sum(row["lineCount"] > 0 for row in rows),
            "withAuthoredSubtitleTrack": sum(
                row["hasAuthoredSubtitleTrack"] for row in rows
            ),
            "withAudioEventIdentity": sum(
                row["audioEventCount"] > 0 for row in rows
            ),
            "withPlayableAudio": sum(
                row["playableAudioFileCount"] > 0 for row in rows
            ),
            "withVideoReferences": sum(
                row["videoReferenceCount"] > 0 for row in rows
            ),
            "transitions": sum(row["isTransition"] for row in rows),
            "blackScreenConfigured": sum(row["useBlackScreen"] for row in rows),
        },
        "rows": rows,
        "evidencePolicy": {
            "unityTimelineAssets": "authored serialized composition",
            "levelscriptFmvAction": "exact authored playback request path",
            "textTableOnly": "localized text candidate only",
            "playbackObserved": False,
            "missionOwnership": False,
            "chronology": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    labels = {
        "unity_timeline_root": "Unity Timeline root",
        "unity_timeline_plus_levelscript_fmv": "Unity Timeline + independent LevelScript FMV",
        "unity_timeline_components_without_root": "Timeline components without root definition",
        "levelscript_fmv_only": "LevelScript FMV only",
        "text_table_only_unconfirmed": "TextTable-only unconfirmed",
    }
    lines = [
        "# Cutscene semantic surface audit",
        "",
        f"- Story cutscene rows: `{summary['cutsceneRows']}`",
        f"- With localized text rows: `{summary['withLocalizedText']}`",
        "- With an authored subtitle track: "
        f"`{summary['withAuthoredSubtitleTrack']}`",
        f"- With audio Event identity: `{summary['withAudioEventIdentity']}`",
        f"- With playable recovered audio: `{summary['withPlayableAudio']}`",
        f"- With video references: `{summary['withVideoReferences']}`",
        f"- Transition-configured: `{summary['transitions']}`",
        f"- Black-screen configured: `{summary['blackScreenConfigured']}`",
        "",
        "## Evidence-shape classification",
        "",
        "| shape | rows | meaning |",
        "| --- | ---: | --- |",
    ]
    meanings = {
        "unity_timeline_root": "Root plus serialized Timeline component assets.",
        "unity_timeline_plus_levelscript_fmv": "A Unity cutscene definition and a separate exact PlayFmvAction coexist; this does not prove one contains the other.",
        "unity_timeline_components_without_root": "Component Timeline assets exist, but the canonical root definition is absent from the current export.",
        "levelscript_fmv_only": "No Unity cutscene asset; an exact native-mapped LevelScript PlayFmvAction supplies the playback request.",
        "text_table_only_unconfirmed": "Only localized cutscene-named text is present; no asset, source link, or narrative video confirms a playable scene.",
    }
    for key, label in labels.items():
        lines.append(
            f"| {label} | `{summary['classifications'].get(key, 0)}` | "
            f"{meanings[key]} |"
        )

    exceptional = [
        row for row in report["rows"]
        if row["classification"] != "unity_timeline_root"
    ]
    lines.extend([
        "",
        "## Non-standard rows",
        "",
        "| Story key | classification | component assets | FMV ids | lines |",
        "| --- | --- | ---: | --- | ---: |",
    ])
    for row in exceptional:
        lines.append(
            f"| `{row['key']}` | `{row['classification']}` | "
            f"`{row['variantCount']}` | "
            f"{', '.join(f'`{value}`' for value in row['fmvIds']) or ''} | "
            f"`{row['lineCount']}` |"
        )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "- `Actor`, `Audio`, `Effect`, `Light`, and `Others` counts are "
        "serialized Timeline asset groups, not counts of characters, shots, "
        "clips, or inner tracks.",
        "- A LevelScript FMV row proves an authored playback request and its "
        "local control path; it does not prove execution in a session.",
        "- Localized TextTable rows are not subtitle-placement evidence unless "
        "an authored subtitle track independently links them.",
        "- This classification creates no mission ownership or Story-order edge.",
        "",
    ])
    return "\n".join(lines)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--story-index", type=Path, default=DEFAULT_STORY_INDEX)
    parser.add_argument(
        "--conversation-root", type=Path, default=DEFAULT_CONVERSATION_ROOT
    )
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(
            args.story_index.resolve(), args.conversation_root.resolve()
        )
    except AuditError as exc:
        raise SystemExit(f"Cutscene semantic surface audit failed: {exc}") from exc
    json_path = args.report_root / "cutscene_semantic_surface_audit.json"
    markdown_path = args.report_root / "cutscene_semantic_surface_audit.md"
    write_json(json_path, report)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Cutscene semantic surface audit: {markdown_path.relative_to(ROOT)}")
    print(f"Cutscene semantic surface data: {json_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
