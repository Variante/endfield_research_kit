#!/usr/bin/env python3
"""Audit AudioDialog + Timeline + speaker evidence per inferredOptionResponse.

For each scene/group with the live `inferredOptionResponse` warning in
`webui/data/lang/<lang>/conv/`, this audit gathers original-data evidence
for each candidate response line:

- `AudioDialog.path` row, speaker channel, audio dialog key (integer hash)
- DialogTextTable speaker / actor id and line text
- DialogTrunkPlayableAsset clip Timeline `start` and `duration` (from
  `timelineTiming` on the conv line)
- monotonic-by-Timeline-start check across the candidate set
- speaker-consistency check across the candidate set
- relative AudioDialog key ordering and gap pattern

The audit also captures the anchor line (the option group's authored
`after`) and the option rows themselves so a reviewer can cross-check
whether the Timeline order of the candidates aligns with the option
index order.

Output:

    reports/option_response_audio_evidence_<lang>.json
    reports/option_response_audio_evidence_<lang>.md

This is **diagnostic only**. Promotion to a strong `optionResponse`
edge requires either:

- a positive Runtime Jump route (already audited separately), or
- per-candidate authored evidence beyond Timeline adjacency (e.g.
  decoded `+0x18` runtime field on `DialogOptionPlayableAsset`).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

TABLE_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
AUDIO_DIALOG_TABLE_PATH = TABLE_ROOT / "AudioDialog.json"


def load_audio_dialog_index() -> dict[str, dict[str, Any]]:
    payload = read_json(AUDIO_DIALOG_TABLE_PATH, {})
    if not isinstance(payload, dict):
        return {}
    by_audio_name: dict[str, dict[str, Any]] = {}
    for key, row in payload.items():
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        if not path:
            continue
        # path is like v1d0/Narrating/SubChar/c13m2/au_dlg_c13m2_20_002.wem
        stem = os.path.basename(path)
        if stem.lower().endswith(".wem"):
            stem = stem[:-4]
        if not stem:
            continue
        by_audio_name[stem.lower()] = {
            "audioDialogKey": int(key) if str(key).lstrip("-").isdigit() else key,
            "path": path,
            "speakerChannel": row.get("speakerChannel") or "",
            "voType": row.get("voType"),
            "codec": row.get("codec"),
            "wavDuration": row.get("wavDuration"),
        }
    return by_audio_name


def find_line(conv: dict[str, Any], line_id: str) -> dict[str, Any] | None:
    if not line_id:
        return None
    for line in conv.get("lines") or []:
        if not isinstance(line, dict):
            continue
        if line.get("id") == line_id or (line.get("_debug") or {}).get("rowId") == line_id:
            return line
    return None


def line_evidence(line: dict[str, Any] | None, audio_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not line:
        return {"missing": True}
    debug = line.get("_debug") or {}
    timing = debug.get("timelineTiming") or {}
    audio_name = str(line.get("audio") or "")
    audio_meta = audio_index.get(audio_name.lower(), {})
    return {
        "lineId": line.get("id"),
        "audioName": audio_name,
        "speaker": line.get("aid") or "",
        "actorDisplay": line.get("actor") or "",
        "emotion": line.get("emo"),
        "ts": line.get("ts"),
        "duration": line.get("dur"),
        "timeline": timing.get("timeline") or "",
        "timelineStart": timing.get("start"),
        "timelineDuration": timing.get("duration"),
        "audioDialogKey": audio_meta.get("audioDialogKey"),
        "audioDialogPath": audio_meta.get("path") or "",
        "audioSpeakerChannel": audio_meta.get("speakerChannel") or "",
        "audioVoType": audio_meta.get("voType"),
        "audioWavDuration": audio_meta.get("wavDuration"),
    }


def is_strictly_monotonic(values: list[Any]) -> bool:
    floats = [v for v in values if isinstance(v, (int, float))]
    if len(floats) < 2 or len(floats) != len(values):
        return False
    if all(floats[i] < floats[i + 1] for i in range(len(floats) - 1)):
        return True
    if all(floats[i] > floats[i + 1] for i in range(len(floats) - 1)):
        return True
    return False


def audit_group(conv: dict[str, Any], warning_group: dict[str, Any], audio_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidates_ids = list(warning_group.get("candidateLineIds") or [])
    anchor_id = warning_group.get("after") or ""
    common_id = warning_group.get("commonLineId") or ""

    candidates = [line_evidence(find_line(conv, lid), audio_index) for lid in candidates_ids]
    anchor = line_evidence(find_line(conv, anchor_id), audio_index)
    common = line_evidence(find_line(conv, common_id), audio_index) if common_id else None

    # Locate the option group payload itself to surface the option rows
    options: list[dict[str, Any]] = []
    g = warning_group.get("group")
    for grp in conv.get("optionGroups") or []:
        if grp.get("g") == g:
            for opt in grp.get("options") or []:
                row_id = (opt.get("source") or {}).get("rowId") or opt.get("id")
                options.append({
                    "optionId": opt.get("id"),
                    "rowId": row_id,
                    "text": opt.get("text"),
                })
            break

    timeline_starts = [c.get("timelineStart") for c in candidates]
    audio_keys = [c.get("audioDialogKey") for c in candidates]
    speakers = [c.get("speaker") or c.get("audioSpeakerChannel") or "" for c in candidates]

    return {
        "scene": conv.get("key") or "",
        "mission": conv.get("mission") or "",
        "group": g,
        "anchorLineId": anchor_id,
        "anchor": anchor,
        "commonLineId": common_id,
        "common": common,
        "candidateLineIds": candidates_ids,
        "candidates": candidates,
        "options": options,
        "checks": {
            "candidateCount": len(candidates),
            "optionCount": len(options),
            "timelineStartMonotonic": is_strictly_monotonic(timeline_starts),
            "audioDialogKeyMonotonic": is_strictly_monotonic(audio_keys),
            "candidatesAllAfterAnchor": all(
                isinstance(c.get("timelineStart"), (int, float))
                and isinstance(anchor.get("timelineStart"), (int, float))
                and c["timelineStart"] >= anchor["timelineStart"]
                for c in candidates
            ),
            "candidateSpeakers": list(dict.fromkeys(s for s in speakers if s)),
            "speakerConsistent": len({s for s in speakers if s}) <= 1,
            "anchorSpeaker": anchor.get("speaker") or anchor.get("audioSpeakerChannel") or "",
            "anchorIsDifferentSpeaker": (
                anchor.get("speaker") not in speakers if anchor.get("speaker") else False
            ),
            "timelinesSameAsAnchor": all(
                c.get("timeline") == anchor.get("timeline")
                for c in candidates
                if c.get("timeline") and anchor.get("timeline")
            ),
        },
    }


def collect_groups(conv_dir: Path, audio_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(conv_dir.glob("*.json")):
        try:
            conv = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(conv, dict):
            continue
        for warning in conv.get("warnings") or []:
            if not isinstance(warning, dict) or warning.get("code") != "inferredOptionResponse":
                continue
            for group in warning.get("groups") or []:
                if not isinstance(group, dict):
                    continue
                rows.append(audit_group(conv, group, audio_index))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    monotonic_starts = sum(1 for r in rows if r["checks"]["timelineStartMonotonic"])
    monotonic_keys = sum(1 for r in rows if r["checks"]["audioDialogKeyMonotonic"])
    all_after_anchor = sum(1 for r in rows if r["checks"]["candidatesAllAfterAnchor"])
    speaker_consistent = sum(1 for r in rows if r["checks"]["speakerConsistent"])
    anchor_diff = sum(1 for r in rows if r["checks"]["anchorIsDifferentSpeaker"])
    timeline_same = sum(1 for r in rows if r["checks"]["timelinesSameAsAnchor"])
    by_mission: Counter[str] = Counter(r["mission"] for r in rows)
    return {
        "groupCount": len(rows),
        "groupsWithMonotonicTimelineStart": monotonic_starts,
        "groupsWithMonotonicAudioDialogKey": monotonic_keys,
        "groupsWithAllCandidatesAfterAnchor": all_after_anchor,
        "groupsWithConsistentCandidateSpeaker": speaker_consistent,
        "groupsWithAnchorSpeakerDifferentFromCandidates": anchor_diff,
        "groupsWhereCandidatesShareAnchorTimeline": timeline_same,
        "perMissionGroupCounts": dict(by_mission),
    }


def markdown_report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# Option Response Audio / Timeline Evidence Audit",
        "",
        f"Generated: {payload['generated']}",
        f"Language: `{payload['language']}`",
        "",
        "## Summary",
        "",
        f"- Live `inferredOptionResponse` groups: `{s['groupCount']}`",
        f"- Candidates monotonic by Timeline start: `{s['groupsWithMonotonicTimelineStart']}`",
        f"- Candidates monotonic by AudioDialog key: `{s['groupsWithMonotonicAudioDialogKey']}`",
        f"- All candidates after the anchor on the Timeline: `{s['groupsWithAllCandidatesAfterAnchor']}`",
        f"- Candidate speaker consistent across candidates: `{s['groupsWithConsistentCandidateSpeaker']}`",
        f"- Anchor speaker differs from candidate speakers: `{s['groupsWithAnchorSpeakerDifferentFromCandidates']}`",
        f"- Candidates share the anchor's Timeline asset: `{s['groupsWhereCandidatesShareAnchorTimeline']}`",
        f"- Per-mission group counts: `{s['perMissionGroupCounts']}`",
        "",
        "## Evidence Per Group",
        "",
    ]

    for row in payload["rows"]:
        c = row["checks"]
        lines.append(f"### `{row['scene']}` group `{row['group']}` (mission `{row['mission']}`)")
        lines.append("")
        lines.append(f"- Anchor: `{row.get('anchorLineId') or ''}` "
                     f"speaker=`{row['anchor'].get('speaker') or ''}` "
                     f"timeline=`{row['anchor'].get('timeline') or ''}` "
                     f"start=`{row['anchor'].get('timelineStart')}` "
                     f"dur=`{row['anchor'].get('timelineDuration')}`")
        if row.get("commonLineId"):
            lines.append(f"- Common: `{row['commonLineId']}` "
                         f"speaker=`{(row.get('common') or {}).get('speaker') or ''}`")
        lines.append("- Candidates:")
        lines.append("  | line | speaker | timeline | start | dur | audioKey | wav | path |")
        lines.append("  | --- | --- | --- | ---: | ---: | ---: | ---: | --- |")
        for cand in row["candidates"]:
            lines.append(
                f"  | `{md_escape(cand.get('lineId') or '')}` "
                f"| `{md_escape(cand.get('speaker') or cand.get('audioSpeakerChannel') or '')}` "
                f"| `{md_escape(cand.get('timeline') or '')}` "
                f"| {cand.get('timelineStart')} "
                f"| {cand.get('timelineDuration')} "
                f"| {cand.get('audioDialogKey')} "
                f"| {cand.get('audioWavDuration')} "
                f"| `{md_escape(cand.get('audioDialogPath') or '')}` |"
            )
        if row.get("options"):
            lines.append("- Options:")
            for opt in row["options"]:
                opt_text = (opt.get("text") or "").strip()
                if len(opt_text) > 80:
                    opt_text = opt_text[:80] + "..."
                lines.append(f"  - `{opt.get('optionId') or ''}` -> {md_escape(opt_text)}")
        lines.append("- Checks: "
                     f"timelineStartMonotonic=`{c['timelineStartMonotonic']}`, "
                     f"audioDialogKeyMonotonic=`{c['audioDialogKeyMonotonic']}`, "
                     f"allCandidatesAfterAnchor=`{c['candidatesAllAfterAnchor']}`, "
                     f"speakerConsistent=`{c['speakerConsistent']}`, "
                     f"anchorDifferentSpeaker=`{c['anchorIsDifferentSpeaker']}`, "
                     f"sharedTimeline=`{c['timelinesSameAsAnchor']}`")
        lines.append("")

    lines.extend([
        "## Decision",
        "",
        "This audit is diagnostic only. Promotion to a strong `optionResponse`",
        "edge needs either a positive Runtime Jump route (separate audit) or a",
        "decoded `DialogOptionPlayableAsset +0x18` runtime field. The",
        "Timeline-start + speaker evidence in this report is necessary but not",
        "sufficient: it shows the candidates form a coherent authored cohort",
        "after the anchor, but does not bind each candidate to a specific",
        "option index.",
    ])

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports" / "story" / "recovery" / "options")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    conv_dir = ROOT / "webui" / "data" / "lang" / args.language / "conv"
    if not conv_dir.is_dir():
        print(f"missing {conv_dir}", file=sys.stderr)
        return 1
    audio_index = load_audio_dialog_index()
    rows = collect_groups(conv_dir, audio_index)
    summary = summarize(rows)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "language": args.language,
        "convDir": str(conv_dir),
        "audioDialogTable": str(AUDIO_DIALOG_TABLE_PATH),
        "summary": summary,
        "rows": rows,
    }
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.reports_dir / f"option_response_audio_evidence_{args.language}.json"
    out_md = args.reports_dir / f"option_response_audio_evidence_{args.language}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(
        f"Groups: {summary['groupCount']}; "
        f"monotonic-timeline: {summary['groupsWithMonotonicTimelineStart']}; "
        f"monotonic-audioKey: {summary['groupsWithMonotonicAudioDialogKey']}; "
        f"speaker-consistent: {summary['groupsWithConsistentCandidateSpeaker']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
