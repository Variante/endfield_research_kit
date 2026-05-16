#!/usr/bin/env python3
"""Recover authoritative cs_video (FMV) bindings without relying on filenames.

Two data graphs exist in the export that link cutscene/FMV videos to dialog
scenes and missions. Both are typed and reliable; the existing WebUI build only
uses heuristic filename matching.

  Graph A: Dialog Timeline -> FMV PlayableAsset -> video file.
    Each dialog scene has a Unity Timeline asset under
      assets/beyond/dynamicassets/gameplay/dialog/timeline/dlgtl_<scene>_sub_<n>/.
    The timeline contains a `Beyond FMV Track` whose clips reference a
    `BeyondFMVPlayableAsset` MonoBehaviour. The playable's `fmvId` field is
    the canonical id of the video file. The clip carries `m_Start`,
    `m_Duration`, `optionIndex`, and `m_DisplayName` for branch routing.

  Graph B: Mission Runtime -> CheckFMVFinish -> video file.
    Quest objectives in MissionRuntimeAsset/<mission>.json declare typed
    conditions `Beyond.Gameplay.CheckFMVFinish` whose `_fmvId.constValue`
    names the consumed video. This covers non-dialog cutscene videos.

This script joins:
  - Every `BeyondFMVPlayableAsset*.json` (and clones) under
    export_full/recovered/AnimeStudio-cli/timeline_extract/*/MonoBehaviour/.
  - The AssetEntries maps under
    export_full/recovered/AnimeStudio-cli/{StreamingAssets,Persistent}/maps/
    keyed by PathID to recover each playable's `dlgtl_<scene>_sub_<n>`
    container.
  - Every `Beyond FMV Track*.json` clip to capture timestamps and option
    routing.
  - Every `Beyond.Gameplay.CheckFMVFinish._fmvId.constValue` in
    `MissionRuntimeAsset/*.json`.

Output: export_full/recovered/video_bindings.json with the schema below.

Scene-to-mission rule: the mission id is the dialog scene id with its trailing
`_<digits>(d<digits>)?(letterSuffix)?` segment stripped. For standalone
(`cs_video_<mission>_<n>`) ids, the mission id is the part between
`cs_video_` and the trailing `_<n>`.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "export_full"
RECOVERED_DIR = EXPORT_ROOT / "recovered"
ANIMESTUDIO_CLI = RECOVERED_DIR / "AnimeStudio-cli"
TIMELINE_EXTRACT = ANIMESTUDIO_CLI / "timeline_extract"
ASSET_MAPS = (
    ANIMESTUDIO_CLI / "StreamingAssets" / "maps" / "endfield_streamingassets_assets.json",
    ANIMESTUDIO_CLI / "Persistent" / "maps" / "endfield_persistent_assets.json",
)

MRA_DIRS = (
    EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Json" / "MissionRuntimeAsset",
    EXPORT_ROOT / "structured" / "Persistent" / "Data" / "Json" / "MissionRuntimeAsset",
)

NARRATIVE_VIDEO_DIRS = (
    EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Video" / "PC" / "Narrative" / "Cutscene",
    EXPORT_ROOT / "structured" / "StreamingAssets" / "Data" / "Video" / "PC" / "Narrative" / "RemoteComm",
    EXPORT_ROOT / "structured" / "Persistent" / "Data" / "Video" / "PC" / "Narrative" / "Cutscene",
    EXPORT_ROOT / "structured" / "Persistent" / "Data" / "Video" / "PC" / "Narrative" / "RemoteComm",
)

DEFAULT_OUTPUT = RECOVERED_DIR / "video_bindings.json"
DEFAULT_REPORT = ROOT / "reports" / "video_bindings.md"

_DLGTL_FROM_CONTAINER = re.compile(
    r"timeline/(dlgtl_[a-z0-9]+(?:_[a-z0-9]+)*?_sub_\d+)/", re.IGNORECASE
)
_GENDER_PREFIX = re.compile(r"^(?P<g>f|m|fm)_(?P<rest>cs_video_.+)$", re.IGNORECASE)
_MISSION_FROM_DLG = re.compile(
    r"^(?P<mission>[a-z]+\d+m\d+(?:d\d+)?)_(?P<rest>.+)$", re.IGNORECASE
)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def load_asset_index() -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for map_path in ASSET_MAPS:
        if not map_path.is_file():
            continue
        try:
            payload = json.loads(map_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"warn: cannot read {map_path}: {exc}", file=sys.stderr)
            continue
        entries = payload.get("AssetEntries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            continue
        for entry in entries:
            pid = entry.get("PathID")
            if pid is None:
                continue
            try:
                pid_int = int(pid)
            except (TypeError, ValueError):
                continue
            index.setdefault(pid_int, entry)
    return index


def scene_from_container(container: str) -> str:
    if not container:
        return ""
    match = _DLGTL_FROM_CONTAINER.search(container)
    if not match:
        return ""
    folder = match.group(1)
    return folder.removeprefix("dlgtl_").rsplit("_sub_", 1)[0]


def strip_gender(fmv_id: str) -> tuple[str, str]:
    match = _GENDER_PREFIX.match(fmv_id or "")
    if not match:
        return "", fmv_id or ""
    return match.group("g").lower(), match.group("rest")


def scene_to_mission(scene: str) -> str:
    if not scene:
        return ""
    for prefix in ("dlg_", "cutscene_", "remotecomm_", "radio_", "black_"):
        if scene.startswith(prefix):
            scene = scene[len(prefix):]
            break
    match = _MISSION_FROM_DLG.match(scene)
    if match:
        return match.group("mission").lower()
    return scene.split("_", 1)[0].lower()


def fmv_id_to_base(fmv_id: str) -> str:
    _, base = strip_gender(fmv_id)
    return base


def fmv_id_scene_hint(fmv_id: str) -> str:
    base = fmv_id_to_base(fmv_id)
    if base.startswith("cs_video_dlg_"):
        return base[len("cs_video_"):]
    if base.startswith("cs_video_"):
        return base[len("cs_video_"):]
    return base


def fmv_id_mission_hint(fmv_id: str) -> str:
    scene_hint = fmv_id_scene_hint(fmv_id)
    return scene_to_mission(scene_hint)


def iter_video_files() -> list[Path]:
    out: list[Path] = []
    for d in NARRATIVE_VIDEO_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() == ".mp4":
                out.append(p)
    return out


def iter_playable_assets(extract_root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    if not extract_root.is_dir():
        return
    for sub in sorted(extract_root.iterdir()):
        mb_dir = sub / "MonoBehaviour"
        if not mb_dir.is_dir():
            continue
        for p in sorted(mb_dir.iterdir()):
            if not p.name.startswith("BeyondFMVPlayableAsset"):
                continue
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            yield p, payload


def iter_fmv_tracks(extract_root: Path) -> Iterable[tuple[Path, dict[str, Any]]]:
    if not extract_root.is_dir():
        return
    for sub in sorted(extract_root.iterdir()):
        mb_dir = sub / "MonoBehaviour"
        if not mb_dir.is_dir():
            continue
        for p in sorted(mb_dir.iterdir()):
            name = p.name
            if not (name.startswith("Beyond FMV Track") or name == "FMV.json"):
                continue
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                yield p, payload


def walk_check_fmv_finish(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        type_tag = str(node.get("$type") or "")
        if "CheckFMVFinish" in type_tag:
            fmv_id_node = node.get("_fmvId") or {}
            if isinstance(fmv_id_node, dict):
                value = fmv_id_node.get("constValue")
                if isinstance(value, str) and value:
                    yield value
        for value in node.values():
            yield from walk_check_fmv_finish(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk_check_fmv_finish(item)


def build_bindings(*, verbose: bool = False) -> dict[str, Any]:
    asset_index = load_asset_index()
    if verbose:
        print(f"asset entries indexed by PathID: {len(asset_index)}")

    fmv_records: list[dict[str, Any]] = []
    playable_by_pid: dict[int, dict[str, Any]] = {}

    for path, payload in iter_playable_assets(TIMELINE_EXTRACT):
        fmv_id = str(payload.get("fmvId") or "").strip()
        anime = payload.get("$animestudio") or {}
        try:
            pid = int(anime.get("pathId")) if anime.get("pathId") is not None else None
        except (TypeError, ValueError):
            pid = None
        entry = asset_index.get(pid) if pid is not None else None
        container = str(entry.get("Container") or "") if entry else ""
        scene = scene_from_container(container)
        record = {
            "fmvId": fmv_id,
            "pathId": pid,
            "container": container,
            "scene": scene,
            "duration": payload.get("m_clipDuration"),
            "asset": rel(path),
        }
        if pid is not None:
            playable_by_pid[pid] = record
        fmv_records.append(record)

    track_clips: list[dict[str, Any]] = []
    for path, payload in iter_fmv_tracks(TIMELINE_EXTRACT):
        for clip in payload.get("m_Clips") or []:
            if not isinstance(clip, dict):
                continue
            asset_pid = (clip.get("m_Asset") or {}).get("m_PathID")
            try:
                asset_pid_int = int(asset_pid) if asset_pid is not None else None
            except (TypeError, ValueError):
                asset_pid_int = None
            playable = playable_by_pid.get(asset_pid_int) if asset_pid_int is not None else None
            display = str(clip.get("m_DisplayName") or "").strip()
            fmv_id = (playable or {}).get("fmvId") or display
            scene = (playable or {}).get("scene") or ""
            track_clips.append({
                "fmvId": fmv_id,
                "displayName": display,
                "scene": scene,
                "start": clip.get("m_Start"),
                "duration": clip.get("m_Duration"),
                "optionIndex": clip.get("optionIndex"),
                "trackFile": rel(path),
                "playableAssetPathId": asset_pid_int,
            })

    mission_to_fmv: dict[str, list[dict[str, Any]]] = defaultdict(list)
    fmv_to_missions: dict[str, set[str]] = defaultdict(set)
    for mra_dir in MRA_DIRS:
        if not mra_dir.is_dir():
            continue
        for path in sorted(mra_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            stem = path.stem
            if stem.endswith("_meta"):
                continue
            mission_id = stem
            for fmv_id in walk_check_fmv_finish(payload):
                mission_to_fmv[mission_id].append({"fmvId": fmv_id, "source": rel(path)})
                fmv_to_missions[fmv_id].add(mission_id)

    bindings: dict[str, dict[str, Any]] = {}

    def get_or_create(canonical: str) -> dict[str, Any]:
        record = bindings.get(canonical)
        if record is None:
            record = {
                "fmvId": canonical,
                "baseFmvId": fmv_id_to_base(canonical),
                "gender": strip_gender(canonical)[0] or None,
                "scene": "",
                "mission": "",
                "videos": [],
                "clips": [],
                "missions": [],
                "sources": [],
                "fallbackSceneHint": fmv_id_scene_hint(canonical),
                "fallbackMissionHint": fmv_id_mission_hint(canonical),
            }
            bindings[canonical] = record
        return record

    for playable in fmv_records:
        fmv_id = playable["fmvId"]
        if not fmv_id:
            continue
        rec = get_or_create(fmv_id)
        if playable["scene"]:
            rec["scene"] = playable["scene"]
            rec["mission"] = scene_to_mission(playable["scene"])
        rec["sources"].append({
            "kind": "timelinePlayable",
            "asset": playable["asset"],
            "container": playable["container"],
            "pathId": playable["pathId"],
            "duration": playable["duration"],
        })

    for clip in track_clips:
        fmv_id = clip["fmvId"]
        if not fmv_id:
            continue
        rec = get_or_create(fmv_id)
        if clip["scene"] and not rec["scene"]:
            rec["scene"] = clip["scene"]
            rec["mission"] = scene_to_mission(clip["scene"])
        rec["clips"].append({
            "scene": clip["scene"],
            "start": clip["start"],
            "duration": clip["duration"],
            "optionIndex": clip["optionIndex"],
            "displayName": clip["displayName"],
            "trackFile": clip["trackFile"],
            "playableAssetPathId": clip["playableAssetPathId"],
        })

    for fmv_id, missions in fmv_to_missions.items():
        rec = get_or_create(fmv_id)
        for mission in sorted(missions):
            if mission not in rec["missions"]:
                rec["missions"].append(mission)
        rec["sources"].append({
            "kind": "missionRuntime",
            "missions": sorted(missions),
        })
        if not rec["scene"]:
            rec["mission"] = next(iter(sorted(missions)))

    video_files = iter_video_files()
    by_name: dict[str, list[Path]] = defaultdict(list)
    for p in video_files:
        by_name[p.stem].append(p)
        _, base = strip_gender(p.stem)
        if base != p.stem:
            by_name[base].append(p)

    for fmv_id, rec in bindings.items():
        _, base = strip_gender(fmv_id)
        candidates = []
        for key in (fmv_id, base):
            for vp in by_name.get(key, []):
                rec_path = rel(vp)
                if rec_path not in candidates:
                    candidates.append(rec_path)
        for vp in video_files:
            if vp.stem.endswith(base) and vp.stem not in (fmv_id, base):
                rec_path = rel(vp)
                if rec_path not in candidates:
                    candidates.append(rec_path)
        rec["videos"] = candidates

    for fmv_id in list(bindings.keys()):
        rec = bindings[fmv_id]
        if not rec["scene"] and rec["fallbackSceneHint"]:
            rec["sceneIsHint"] = True
            rec["scene"] = rec["fallbackSceneHint"]
            rec["mission"] = rec["fallbackMissionHint"]

    by_scene: dict[str, list[str]] = defaultdict(list)
    by_mission: dict[str, list[str]] = defaultdict(list)
    for fmv_id, rec in bindings.items():
        if rec["scene"]:
            by_scene[rec["scene"]].append(fmv_id)
        for mission in rec["missions"] or [rec["mission"]]:
            if mission:
                by_mission[mission].append(fmv_id)

    by_video: dict[str, list[str]] = defaultdict(list)
    for fmv_id, rec in bindings.items():
        for video in rec["videos"]:
            by_video[video].append(fmv_id)

    unbound_videos: list[str] = []
    bound_set = set(by_video)
    for p in video_files:
        rp = rel(p)
        if rp not in bound_set:
            unbound_videos.append(rp)

    summary = {
        "fmvIds": len(bindings),
        "withTimelineScene": sum(1 for r in bindings.values() if r.get("scene") and not r.get("sceneIsHint")),
        "withMissionRuntime": sum(1 for r in bindings.values() if r.get("missions")),
        "videoFiles": len(video_files),
        "videoFilesBound": len(by_video),
        "videoFilesUnbound": len(unbound_videos),
    }

    payload = {
        "generated": int(time.time()),
        "summary": summary,
        "bindings": dict(sorted(bindings.items())),
        "indexByScene": {k: sorted(set(v)) for k, v in sorted(by_scene.items())},
        "indexByMission": {k: sorted(set(v)) for k, v in sorted(by_mission.items())},
        "indexByVideo": {k: sorted(set(v)) for k, v in sorted(by_video.items())},
        "unboundVideos": sorted(unbound_videos),
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Video Bindings",
        "",
        "Authoritative cs_video / FMV -> dialog scene -> mission graph recovered from",
        "Unity Timeline playable assets and MissionRuntimeAsset.CheckFMVFinish nodes.",
        "",
        "## Summary",
        "",
        f"- fmvIds total: `{summary.get('fmvIds', 0)}`",
        f"- with timeline-resolved scene: `{summary.get('withTimelineScene', 0)}`",
        f"- with MissionRuntime CheckFMVFinish: `{summary.get('withMissionRuntime', 0)}`",
        f"- video files scanned: `{summary.get('videoFiles', 0)}`",
        f"- video files bound: `{summary.get('videoFilesBound', 0)}`",
        f"- video files unbound: `{summary.get('videoFilesUnbound', 0)}`",
        "",
        "## fmvIds",
        "",
        "| fmvId | scene | mission | source kinds |",
        "| --- | --- | --- | --- |",
    ]
    for fmv_id, rec in payload.get("bindings", {}).items():
        kinds = sorted({src.get("kind") for src in rec.get("sources") or [] if isinstance(src, dict)})
        scene_marker = "(hint)" if rec.get("sceneIsHint") else ""
        lines.append(
            f"| `{fmv_id}` | `{rec.get('scene', '')}`{scene_marker} | "
            f"`{rec.get('mission', '')}` | {', '.join(kinds) or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_bindings(verbose=args.verbose)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(payload), encoding="utf-8")
    s = payload["summary"]
    print(
        f"Video bindings: {s['fmvIds']} fmvIds, "
        f"{s['withTimelineScene']} via timeline, "
        f"{s['withMissionRuntime']} via MissionRuntime, "
        f"{s['videoFilesBound']}/{s['videoFiles']} files bound"
    )
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
