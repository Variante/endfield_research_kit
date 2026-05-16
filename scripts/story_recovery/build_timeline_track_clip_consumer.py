#!/usr/bin/env python3
"""Extract per-track clip windows from recovered Timeline MonoBehaviour files.

The PlayableDirector bridge already aggregates per-Timeline track-type
counts via `m_SceneBindings`. The next layer of evidence is per-track
clip *windows*: the recovered Timeline MonoBehaviour JSONs carry
`m_Clips` arrays with authored `m_Start` and `m_Duration` for every
clip on every track. This script walks the recovered Timeline track
JSONs under `export_full/recovered/AnimeStudio-cli/timeline_extract/`
and emits one record per (track type, clip) for the high-value track
types:

- `Beyond FMV Track`: clips reference `BeyondFMVPlayableAsset` whose
  `fmvId` resolves to a `cs_video_*` story key. Provides authored
  cutscene FMV timing inside a parent Timeline.
- `Subtitle Track`: subtitle clips. Currently 0 clips in the export
  (auto-binding-only); recorded as a presence flag.
- `Dialog Trunk Track`: high-volume per-line dialog clips, already
  captured by `scripts/story_builder/timeline_recovery.py` into
  `timeline_line_orders.json` — re-summarized here for parity.

Output:

    reports/playable_director/timeline_track_clips.json
    reports/playable_director/timeline_track_clips.md

This is diagnostic evidence for follow-up scene-order promotion. The
report does not change the WebUI; it provides a per-clip audit trail
for FMV/Subtitle/Trunk timing across the export.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

TIMELINE_EXTRACT_ROOT = ROOT / "export_full" / "recovered" / "AnimeStudio-cli" / "timeline_extract"
TARGET_TRACK_TYPES = (
    "Beyond FMV Track",
    "Subtitle Track",
    "Dialog Trunk Track",
)


def normalize_track_name(name: str) -> str:
    name = (name or "").strip()
    for suffix in (" (1)", " (2)", " (3)", " (4)", " (5)"):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name


def _fmv_path_id_index(folder: Path) -> dict[int, Path]:
    """Index ONLY BeyondFMVPlayableAsset files in one folder by PathID."""
    by_id: dict[int, Path] = {}
    mb_dir = folder / "MonoBehaviour"
    if not mb_dir.is_dir():
        return by_id
    for path in mb_dir.glob("BeyondFMVPlayableAsset*.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(doc, dict):
            continue
        meta = doc.get("$animestudio") or {}
        path_id = meta.get("pathId")
        if isinstance(path_id, int):
            by_id[path_id] = path
    return by_id


def resolve_pptr(pptr: Any, by_id: dict[int, Path]) -> Path | None:
    if not isinstance(pptr, dict):
        return None
    pid = pptr.get("m_PathID")
    if not isinstance(pid, int) or pid == 0:
        return None
    return by_id.get(pid)


def collect_clips(track_doc: dict[str, Any]) -> list[dict[str, Any]]:
    clips = track_doc.get("m_Clips") or []
    if not isinstance(clips, list):
        return []
    out: list[dict[str, Any]] = []
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        out.append({
            "start": clip.get("m_Start"),
            "duration": clip.get("m_Duration"),
            "optionIndex": clip.get("optionIndex"),
            "easeInDuration": clip.get("m_EaseInDuration"),
            "easeOutDuration": clip.get("m_EaseOutDuration"),
            "displayName": clip.get("m_DisplayName") or "",
            "assetPathId": (clip.get("m_Asset") or {}).get("m_PathID"),
        })
    return out


def find_parent_playable_director(folder: Path) -> dict[str, Any] | None:
    mb_dir = folder / "MonoBehaviour"
    if not mb_dir.is_dir():
        return None
    candidates = list(mb_dir.glob("PlayableDirector*.json"))
    candidates += list(mb_dir.glob("Playable Director*.json"))
    for path in candidates:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = doc.get("$animestudio") or {}
        return {
            "container": meta.get("container") or "",
            "sourceFile": meta.get("sourceFile") or "",
            "playableDirectorJson": str(path.relative_to(ROOT)).replace("\\", "/"),
        }
    return None


def story_name_from_container(container: str) -> tuple[str, str]:
    """Extract (kind, storyName) from a PlayableDirector container path."""
    if not container:
        return "", ""
    parts = container.replace("\\", "/").split("/")
    story_prefixes = (
        "cutscene_",
        "cutscenetransition_",
        "cs_",
        "dlgtl_",
        "dlg_",
        "levelseq_",
        "lvlseq_",
        "fmv_",
        "sns_",
    )
    for part in parts:
        lower = part.lower()
        for prefix in story_prefixes:
            if lower.startswith(prefix):
                kind = prefix.rstrip("_")
                return kind, part
    return "", ""


def walk_timeline_folders(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not root.is_dir():
        return records
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        mb_dir = folder / "MonoBehaviour"
        if not mb_dir.is_dir():
            continue
        path_id_index = _fmv_path_id_index(folder)
        playable_director = find_parent_playable_director(folder)
        container = (playable_director or {}).get("container") or ""
        kind, story_name = story_name_from_container(container)

        candidate_files: list[Path] = []
        for prefix in ("Beyond FMV Track", "Subtitle Track", "Dialog Trunk Track"):
            candidate_files.extend(mb_dir.glob(f"{prefix}*.json"))
        for path in candidate_files:
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            track_name_raw = (doc.get("$animestudio") or {}).get("name") or ""
            normalized = normalize_track_name(track_name_raw)
            if normalized not in TARGET_TRACK_TYPES:
                continue

            clips = collect_clips(doc)
            for clip in clips:
                fmv_id = ""
                fmv_asset_path = ""
                clip_duration_runtime = None
                if normalized == "Beyond FMV Track":
                    asset_path = resolve_pptr({"m_PathID": clip.get("assetPathId")}, path_id_index)
                    if asset_path:
                        fmv_asset_path = str(asset_path.relative_to(ROOT)).replace("\\", "/")
                        try:
                            fmv_doc = json.loads(asset_path.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            fmv_doc = None
                        if isinstance(fmv_doc, dict):
                            fmv_id = fmv_doc.get("fmvId") or ""
                            clip_duration_runtime = fmv_doc.get("m_clipDuration")
                records.append({
                    "folder": folder.name,
                    "trackName": normalized,
                    "trackJson": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "trackAutoBindingPath": doc.get("autoBindingPath") or "",
                    "trackPathId": (doc.get("$animestudio") or {}).get("pathId"),
                    "containerStoryName": story_name,
                    "containerStoryKind": kind,
                    "playableDirectorJson": (playable_director or {}).get("playableDirectorJson") or "",
                    "clipStart": clip["start"],
                    "clipDuration": clip["duration"],
                    "clipOptionIndex": clip["optionIndex"],
                    "clipDisplayName": clip["displayName"],
                    "fmvId": fmv_id,
                    "fmvAssetJson": fmv_asset_path,
                    "fmvAssetClipDuration": clip_duration_runtime,
                })

            if not clips:
                records.append({
                    "folder": folder.name,
                    "trackName": normalized,
                    "trackJson": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "trackAutoBindingPath": doc.get("autoBindingPath") or "",
                    "trackPathId": (doc.get("$animestudio") or {}).get("pathId"),
                    "containerStoryName": story_name,
                    "containerStoryKind": kind,
                    "playableDirectorJson": (playable_director or {}).get("playableDirectorJson") or "",
                    "clipCount": 0,
                })
    return records


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    track_counts: Counter[str] = Counter()
    clips_by_track: Counter[str] = Counter()
    fmv_records = []
    fmv_story_links: Counter[str] = Counter()
    subtitle_track_empty = 0
    subtitle_track_with_clips = 0
    trunk_track_clip_count = 0
    folders: set[str] = set()

    for r in records:
        track_counts[r["trackName"]] += 1
        folders.add(r["folder"])
        if r.get("clipStart") is not None:
            clips_by_track[r["trackName"]] += 1
            if r["trackName"] == "Beyond FMV Track":
                fmv_records.append(r)
                if r.get("fmvId"):
                    fmv_story_links[r["fmvId"]] += 1
            elif r["trackName"] == "Subtitle Track":
                subtitle_track_with_clips += 1
            elif r["trackName"] == "Dialog Trunk Track":
                trunk_track_clip_count += 1
        else:
            if r["trackName"] == "Subtitle Track":
                subtitle_track_empty += 1

    return {
        "folderCount": len(folders),
        "trackRecordCount": len(records),
        "trackCounts": dict(track_counts.most_common()),
        "clipCountsByTrack": dict(clips_by_track.most_common()),
        "fmvClipCount": len(fmv_records),
        "fmvDistinctIds": len(fmv_story_links),
        "fmvIdHistogram": dict(fmv_story_links.most_common(20)),
        "subtitleTrackEmpty": subtitle_track_empty,
        "subtitleTrackWithClips": subtitle_track_with_clips,
        "dialogTrunkClipCount": trunk_track_clip_count,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# Timeline Track Clip Consumer",
        "",
        f"Generated: {payload['generated']}",
        f"Source root: `{payload['sourceRoot']}`",
        "",
        "## Summary",
        "",
        f"- Timeline folders scanned: `{s['folderCount']}`",
        f"- Track records (target types only): `{s['trackRecordCount']}`",
        f"- Track counts: `{s['trackCounts']}`",
        f"- Clip counts by track: `{s['clipCountsByTrack']}`",
        f"- Beyond FMV clips: `{s['fmvClipCount']}` ({s['fmvDistinctIds']} distinct fmvIds)",
        f"- Subtitle Track empty: `{s['subtitleTrackEmpty']}`, with clips: `{s['subtitleTrackWithClips']}`",
        f"- Dialog Trunk Track clips: `{s['dialogTrunkClipCount']}`",
        "",
        "## Beyond FMV Clip Detail",
        "",
        "| story | kind | fmvId | start | duration | runtimeDur | folder |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    fmv_rows = [
        r for r in payload["records"]
        if r["trackName"] == "Beyond FMV Track" and r.get("clipStart") is not None
    ]
    fmv_rows.sort(key=lambda r: (r["containerStoryName"], r.get("clipStart") or 0))
    if not fmv_rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |")
    else:
        for r in fmv_rows[:80]:
            lines.append(
                f"| `{md_escape(r['containerStoryName'])}` "
                f"| `{md_escape(r['containerStoryKind'])}` "
                f"| `{md_escape(r['fmvId'])}` "
                f"| {r['clipStart']} "
                f"| {r['clipDuration']} "
                f"| {r.get('fmvAssetClipDuration')} "
                f"| `{md_escape(r['folder'])}` |"
            )

    lines.extend([
        "",
        "## FMV ID Histogram (top 20)",
        "",
        "| fmvId | clip count |",
        "| --- | ---: |",
    ])
    for fmv_id, count in s["fmvIdHistogram"].items():
        lines.append(f"| `{md_escape(fmv_id)}` | {count} |")

    lines.extend([
        "",
        "## Notes",
        "",
        "- Subtitle Track is currently auto-binding-only with no clips in the",
        "  export (every Subtitle Track `m_Clips` array is empty). The track",
        "  exists and auto-binds to `CinematicPanel/SubtitlePanel`, but the",
        "  per-line subtitle data lives elsewhere (likely on the Dialog Trunk",
        "  Track or on a Beyond FMV Track's parent prefab).",
        "- Beyond FMV Track clips bind by `m_Asset` PPtr to a",
        "  `BeyondFMVPlayableAsset` whose `fmvId` resolves to a `cs_video_*`",
        "  story key. This is the authored bridge from cutscene Timeline to",
        "  FMV asset.",
        "- Dialog Trunk Track clip detail is already covered by",
        "  `timeline_line_orders.json`; counts here are for cross-validation",
        "  only.",
    ])

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports" / "playable_director",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    records = walk_timeline_folders(TIMELINE_EXTRACT_ROOT)
    summary = summarize_records(records)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRoot": str(TIMELINE_EXTRACT_ROOT),
        "summary": summary,
        "records": records,
    }
    out_json = args.reports_dir / "timeline_track_clips.json"
    out_md = args.reports_dir / "timeline_track_clips.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(
        f"Track records: {summary['trackRecordCount']} across "
        f"{summary['folderCount']} folders; "
        f"FMV clips: {summary['fmvClipCount']} ({summary['fmvDistinctIds']} ids)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
