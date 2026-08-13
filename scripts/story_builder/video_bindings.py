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

  Graph C: Gameplay Cutscene Timeline -> FMV PlayableAsset -> video file.
    Full AnimeStudio MonoBehaviour exports can contain cutscene playables under
      assets/beyond/dynamicassets/gameplay/cutscene/<cutscene>/playable/.
    These use the same `Beyond FMV Track` -> `BeyondFMVPlayableAsset.fmvId`
    link as dialog Timelines, but they are not always present in the smaller
    `timeline_extract/` diagnostic tree.

  Graph D: LevelScript PlayFmvAction -> video file.
    The exact decoded native `_moviePath` / `_fmvId` field names the canonical
    video id. The typed action occurrence normalizes that same value to its
    `cutscene_*` Story key, providing an authoritative binding even when no
    Timeline playable was exported.

This script joins:
  - Every `BeyondFMVPlayableAsset*.json` (and clones) under
    export_full/recovered/AnimeStudio-cli/timeline_extract/*/MonoBehaviour/.
  - Every matching `BeyondFMVPlayableAsset*.json` / `Beyond FMV Track*.json`
    under the story-scoped AnimeStudio `json_by_type/MonoBehaviour` export.
  - The AssetEntries maps under
    export_full/recovered/AnimeStudio-cli/{StreamingAssets,Persistent}/maps/
    keyed by PathID to recover each playable's `dlgtl_<scene>_sub_<n>` or
    gameplay `cutscene_<scene>` container.
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
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import fast_glob_files, path_id_export_base_stem

EXPORT_ROOT = ROOT / "export_full"
RECOVERED_DIR = EXPORT_ROOT / "recovered"
ANIMESTUDIO_CLI = RECOVERED_DIR / "AnimeStudio-cli"
TIMELINE_EXTRACT = ANIMESTUDIO_CLI / "timeline_extract"
MONOBEHAVIOUR_DIRS = (
    ANIMESTUDIO_CLI / "StreamingAssets" / "json_by_type" / "MonoBehaviour",
    ANIMESTUDIO_CLI / "Persistent" / "json_by_type" / "MonoBehaviour",
)
ASSET_MAPS = (
    ANIMESTUDIO_CLI / "StreamingAssets" / "maps" / "endfield_streamingassets_assets.json",
    ANIMESTUDIO_CLI / "Persistent" / "maps" / "endfield_persistent_assets.json",
)
FMV_ID_TABLES = (
    EXPORT_ROOT / "structured" / "StreamingAssets" / "Table" / "NumIdStrTable.json",
    EXPORT_ROOT / "structured" / "Persistent" / "Table" / "NumIdStrTable.json",
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
DEFAULT_REPORT = ROOT / "reports" / "story" / "build" / "video_bindings.md"

_DLGTL_FROM_CONTAINER = re.compile(
    r"timeline/(dlgtl_[a-z0-9]+(?:_[a-z0-9]+)*?_sub_\d+)/", re.IGNORECASE
)
_CUTSCENE_FROM_CONTAINER = re.compile(
    r"(?:^|/)gameplay/cutscene/(?P<folder>(?:(?:f|m|fm)_)?cutscene_[^/]+)/playable/",
    re.IGNORECASE,
)
_GENDER_PREFIX = re.compile(r"^(?P<g>f|m|fm)_(?P<rest>cs_video_.+)$", re.IGNORECASE)
_MISSION_FROM_DLG = re.compile(
    r"^(?P<mission>[a-z]+\d+m\d+(?:d\d+)?)_(?P<rest>.+)$", re.IGNORECASE
)


def anime_export_base_stem(path: Path) -> str:
    return path_id_export_base_stem(path.stem)


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
    normalized = container.replace("\\", "/")
    match = _DLGTL_FROM_CONTAINER.search(normalized)
    if not match:
        match = _CUTSCENE_FROM_CONTAINER.search(normalized)
        if not match:
            return ""
        folder = match.group("folder").lower()
        gender_match = re.match(r"^(?:f|m|fm)_(cutscene_.+)$", folder, flags=re.IGNORECASE)
        return (gender_match.group(1) if gender_match else folder).lower()
    folder = match.group(1)
    return folder.removeprefix("dlgtl_").rsplit("_sub_", 1)[0].lower()


def strip_gender(fmv_id: str) -> tuple[str, str]:
    match = _GENDER_PREFIX.match(fmv_id or "")
    if not match:
        return "", fmv_id or ""
    return match.group("g").lower(), match.group("rest")


def scene_to_mission(scene: str) -> str:
    if not scene:
        return ""
    removed_prefix = True
    while removed_prefix:
        removed_prefix = False
        for prefix in (
            "dlg_",
            "cutscene_",
            "remotecomm_",
            "radio_",
            "black_",
        ):
            if scene.startswith(prefix):
                scene = scene[len(prefix):]
                removed_prefix = True
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


def fmv_to_webui_story_key(fmv_id: str) -> str:
    """Map one canonical FMV id to the generated conversation key."""
    value = str(fmv_id or "").strip()
    if value.startswith(("f_", "m_")):
        value = value[2:]
    if not value.startswith("cs_video_"):
        return value
    rest = value[len("cs_video_"):]
    if rest.startswith((
        "dlg_",
        "sns_",
        "cutscene_",
        "black_",
        "radio_",
        "remotecomm_",
    )):
        return rest
    return f"cutscene_{rest}"


def fmv_clips_by_story(
    bindings: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    mappings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fmv_id, binding in bindings.items():
        story_key = fmv_to_webui_story_key(fmv_id)
        if not story_key:
            continue
        for clip in binding.get("clips") or []:
            if not isinstance(clip, dict) or clip.get("start") is None:
                continue
            mappings[story_key].append({
                "fmvId": fmv_id,
                "clipStart": clip.get("start"),
                "clipDuration": clip.get("duration"),
                "assetClipDuration": clip.get("assetClipDuration"),
                "trackFile": clip.get("trackFile"),
            })
    return {
        key: sorted(
            rows,
            key=lambda row: (
                float(row.get("clipStart") or 0),
                str(row.get("fmvId") or ""),
            ),
        )
        for key, rows in sorted(mappings.items())
    }


def iter_video_files() -> list[Path]:
    out: list[Path] = []
    for d in NARRATIVE_VIDEO_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() == ".mp4":
                out.append(p)
    return out


def _iter_timeline_mono_behaviour_dirs(extract_root: Path) -> Iterable[Path]:
    if not extract_root.is_dir():
        return
    for sub in sorted(extract_root.iterdir()):
        mb_dir = sub / "MonoBehaviour"
        if not mb_dir.is_dir():
            continue
        yield mb_dir


def _iter_mono_behaviour_dirs() -> Iterable[Path]:
    yield from _iter_timeline_mono_behaviour_dirs(TIMELINE_EXTRACT)
    for mb_dir in MONOBEHAVIOUR_DIRS:
        if mb_dir.is_dir():
            yield mb_dir


def iter_playable_assets() -> Iterable[tuple[Path, dict[str, Any]]]:
    for mb_dir in _iter_mono_behaviour_dirs():
        for p in fast_glob_files(mb_dir, "BeyondFMVPlayableAsset*.json"):
            base_stem = anime_export_base_stem(p)
            if not base_stem or not base_stem.startswith("BeyondFMVPlayableAsset"):
                continue
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            yield p, payload


def iter_fmv_tracks() -> Iterable[tuple[Path, dict[str, Any]]]:
    for mb_dir in _iter_mono_behaviour_dirs():
        paths = fast_glob_files(mb_dir, "Beyond FMV Track*.json")
        paths.extend(fast_glob_files(mb_dir, "FMV_p*.json"))
        for p in sorted(set(paths)):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                yield p, payload


def iter_fmv_definitions() -> Iterable[tuple[Path, dict[str, Any]]]:
    """Yield authored FMV config objects without treating them as consumers."""
    seen: set[tuple[str, int | None]] = set()
    for mb_dir in _iter_mono_behaviour_dirs():
        paths: list[Path] = []
        for pattern in (
            "cs_video_*.json",
            "f_cs_video_*.json",
            "m_cs_video_*.json",
            "fmv_*.json",
        ):
            paths.extend(fast_glob_files(mb_dir, pattern))
        for path in sorted(set(paths)):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            fmv_id = str(payload.get("fmvId") or "").strip()
            config = payload.get("config")
            if not fmv_id or not isinstance(config, dict):
                continue
            anime = (
                payload.get("$animestudio")
                if isinstance(payload.get("$animestudio"), dict)
                else {}
            )
            try:
                path_id = (
                    int(anime.get("pathId"))
                    if anime.get("pathId") is not None
                    else None
                )
            except (TypeError, ValueError):
                path_id = None
            identity = (fmv_id, path_id)
            if identity in seen:
                continue
            seen.add(identity)
            yield path, payload


def load_fmv_numeric_ids() -> dict[str, list[int]]:
    """Load the exact NumIdStrTable `fmv_id` dictionary in both source roots."""
    out: dict[str, set[int]] = defaultdict(set)
    for path in FMV_ID_TABLES:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        fmv_table = payload.get("fmv_id") if isinstance(payload, dict) else None
        values = fmv_table.get("dic") if isinstance(fmv_table, dict) else None
        if not isinstance(values, dict):
            continue
        for raw_id, raw_name in values.items():
            name = str(raw_name or "").strip()
            try:
                numeric_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if name:
                out[name].add(numeric_id)
    return {
        name: sorted(numeric_ids)
        for name, numeric_ids in sorted(out.items())
    }


def _path_id_hex(path_id: Any) -> str:
    try:
        value = int(path_id)
    except (TypeError, ValueError):
        return ""
    return f"{value & ((1 << 64) - 1):016X}"


def _definition_resource_dirs(definition: dict[str, Any]) -> tuple[Path, ...]:
    sources = definition.get("sources") or []
    asset_paths = [
        str(source.get("asset") or "")
        for source in sources
        if isinstance(source, dict)
    ]
    if any("/Persistent/" in path.replace("\\", "/") for path in asset_paths):
        return (MONOBEHAVIOUR_DIRS[1],)
    return (MONOBEHAVIOUR_DIRS[0],)


def collect_definition_timeline_evidence(
    definition: dict[str, Any],
    *,
    object_cache: dict[tuple[str, int], list[tuple[Path, dict[str, Any]]]]
    | None = None,
) -> dict[str, Any]:
    """Trace a definition's exact playable, tracks, and clip payloads.

    This is definition provenance only. It deliberately does not synthesize a
    scene, mission, playback binding, or localized subtitle text.
    """
    cache = object_cache if object_cache is not None else {}
    resource_dirs = _definition_resource_dirs(definition)

    def find_objects(
        path_id: Any,
        expected_source_file: str = "",
    ) -> list[tuple[Path, dict[str, Any]]]:
        try:
            numeric_path_id = int(path_id)
        except (TypeError, ValueError):
            return []
        cache_key = ("|".join(str(path) for path in resource_dirs), numeric_path_id)
        if cache_key not in cache:
            suffix = _path_id_hex(numeric_path_id)
            found: list[tuple[Path, dict[str, Any]]] = []
            for resource_dir in resource_dirs:
                for path in fast_glob_files(
                    resource_dir,
                    f"*_p{suffix}.json",
                ):
                    try:
                        payload = json.loads(
                            path.read_text(encoding="utf-8")
                        )
                    except (
                        OSError,
                        UnicodeDecodeError,
                        json.JSONDecodeError,
                    ):
                        continue
                    if isinstance(payload, dict):
                        found.append((path, payload))
            cache[cache_key] = found
        rows = cache[cache_key]
        if not expected_source_file:
            return rows
        exact = [
            row
            for row in rows
            if str(
                (
                    row[1].get("$animestudio")
                    if isinstance(
                        row[1].get("$animestudio"), dict
                    )
                    else {}
                ).get("sourceFile")
                or ""
            )
            == expected_source_file
        ]
        return exact or rows

    tracks: list[dict[str, Any]] = []
    subtitle_text_ids: list[str] = []
    audio_event_keys: list[str] = []
    playable_assets: list[str] = []
    total_clips = 0

    for source in definition.get("sources") or []:
        if not isinstance(source, dict):
            continue
        playable_path_id = source.get("defaultPlayablePathId")
        expected_source_file = str(
            source.get("defaultPlayableSourceFile") or ""
        )
        for playable_path, playable in find_objects(
            playable_path_id,
            expected_source_file,
        ):
            playable_rel = rel(playable_path)
            if playable_rel not in playable_assets:
                playable_assets.append(playable_rel)
            playable_anime = (
                playable.get("$animestudio")
                if isinstance(playable.get("$animestudio"), dict)
                else {}
            )
            playable_source_file = str(
                playable_anime.get("sourceFile") or expected_source_file
            )
            for track_index, track_pointer in enumerate(
                playable.get("m_Tracks") or []
            ):
                if not isinstance(track_pointer, dict):
                    continue
                track_path_id = track_pointer.get("m_PathID")
                for track_path, track in find_objects(
                    track_path_id,
                    playable_source_file,
                ):
                    clips = [
                        clip
                        for clip in (track.get("m_Clips") or [])
                        if isinstance(clip, dict)
                    ]
                    total_clips += len(clips)
                    track_record = {
                        "index": track_index,
                        "name": str(track.get("m_Name") or ""),
                        "pathId": track_path_id,
                        "asset": rel(track_path),
                        "clipCount": len(clips),
                    }
                    clip_records: list[dict[str, Any]] = []
                    for clip_index, clip in enumerate(clips):
                        asset_pointer = clip.get("m_Asset")
                        asset_path_id = (
                            asset_pointer.get("m_PathID")
                            if isinstance(asset_pointer, dict)
                            else None
                        )
                        for clip_path, clip_asset in find_objects(
                            asset_path_id,
                            playable_source_file,
                        ):
                            clip_record = {
                                "index": clip_index,
                                "asset": rel(clip_path),
                                "pathId": asset_path_id,
                                "start": clip.get("m_Start"),
                                "duration": clip.get("m_Duration"),
                            }
                            text_ids: list[str] = []
                            for field_name, raw_value in clip_asset.items():
                                if not (
                                    field_name == "_textId"
                                    or re.fullmatch(
                                        r"_textId_\d+",
                                        str(field_name),
                                    )
                                ):
                                    continue
                                text_id = str(raw_value or "").strip()
                                if text_id and text_id not in text_ids:
                                    text_ids.append(text_id)
                                if (
                                    text_id
                                    and text_id not in subtitle_text_ids
                                ):
                                    subtitle_text_ids.append(text_id)
                            audio_event = str(
                                clip_asset.get("_audioEventKey") or ""
                            ).strip()
                            if text_ids:
                                clip_record["subtitleTextIds"] = text_ids
                            if audio_event:
                                clip_record["audioEventKey"] = audio_event
                                if audio_event not in audio_event_keys:
                                    audio_event_keys.append(audio_event)
                            clip_records.append(clip_record)
                    if clip_records:
                        track_record["clips"] = clip_records
                    tracks.append(track_record)

    return {
        "playableAssets": playable_assets,
        "trackCount": len(tracks),
        "clipCount": total_clips,
        "subtitleClipCount": sum(
            1
            for track in tracks
            for clip in track.get("clips") or []
            if clip.get("subtitleTextIds")
        ),
        "subtitleTextIds": subtitle_text_ids,
        "audioEventKeys": audio_event_keys,
        "tracks": tracks,
        "placementEvidence": False,
    }


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


def collect_levelscript_fmv_actions(
    occurrences: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Return exact native LevelScript FMV target fields and Story keys."""
    if occurrences is None:
        from story_builder.level_bindings import (  # noqa: PLC0415
            build_levelscript_action_story_occurrences,
        )

        occurrences = build_levelscript_action_story_occurrences()
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for story_key, story_occurrences in sorted(occurrences.items()):
        for occurrence in story_occurrences or []:
            if (
                not isinstance(occurrence, dict)
                or occurrence.get("recordClass") != "play_fmv"
            ):
                continue
            fmv_action = (
                occurrence.get("fmvAction")
                if isinstance(occurrence.get("fmvAction"), dict)
                else {}
            )
            fmv_id = str(fmv_action.get("fmvId") or "").strip()
            expected_story_key = (
                f"cutscene_{fmv_id[len('cs_video_') :]}"
                if fmv_id.startswith("cs_video_")
                else ""
            )
            if (
                not fmv_id
                or story_key != expected_story_key
                or not fmv_action.get("sourceField")
                or not fmv_action.get("nativeMappingId")
            ):
                continue
            source_file = str(occurrence.get("sourceFile") or "")
            record_offset = int(occurrence.get("recordOffset") or 0)
            identity = (
                fmv_id,
                story_key,
                source_file,
                record_offset,
            )
            if identity in seen:
                continue
            seen.add(identity)
            rows.append({
                "fmvId": fmv_id,
                "storyKey": story_key,
                "levelId": str(occurrence.get("levelId") or ""),
                "scriptId": str(occurrence.get("scriptId") or ""),
                "sourceFile": source_file,
                "actionMapRole": str(
                    occurrence.get("actionMapRole") or ""
                ),
                "recordOffset": record_offset,
                "localId": occurrence.get("localId"),
                "actionName": str(occurrence.get("actionName") or ""),
                "nativeMappingId": str(
                    occurrence.get("nativeMappingId") or ""
                ),
                "fmvAction": {
                    key: fmv_action[key]
                    for key in (
                        "action",
                        "sourceField",
                        "fieldOffset",
                        "payloadShape",
                        "nativeMappingId",
                    )
                    if fmv_action.get(key) not in (None, "")
                },
            })
    return rows


def build_bindings(*, verbose: bool = False) -> dict[str, Any]:
    asset_index = load_asset_index()
    if verbose:
        print(f"asset entries indexed by PathID: {len(asset_index)}")

    fmv_records: list[dict[str, Any]] = []
    playable_by_pid: dict[int, dict[str, Any]] = {}

    seen_playable_path_ids: set[int] = set()
    for path, payload in iter_playable_assets():
        fmv_id = str(payload.get("fmvId") or "").strip()
        anime = payload.get("$animestudio") or {}
        try:
            pid = int(anime.get("pathId")) if anime.get("pathId") is not None else None
        except (TypeError, ValueError):
            pid = None
        if pid is not None:
            if pid in seen_playable_path_ids:
                continue
            seen_playable_path_ids.add(pid)
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
    seen_track_path_ids: set[int] = set()
    for path, payload in iter_fmv_tracks():
        anime = payload.get("$animestudio") if isinstance(payload.get("$animestudio"), dict) else {}
        try:
            track_pid = int(anime.get("pathId")) if anime.get("pathId") is not None else None
        except (TypeError, ValueError):
            track_pid = None
        if track_pid is not None:
            if track_pid in seen_track_path_ids:
                continue
            seen_track_path_ids.add(track_pid)
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
                "assetClipDuration": (playable or {}).get("duration"),
            })

    numeric_ids = load_fmv_numeric_ids()
    definitions: dict[str, dict[str, Any]] = {}
    for path, payload in iter_fmv_definitions():
        fmv_id = str(payload.get("fmvId") or "").strip()
        if not fmv_id:
            continue
        anime = (
            payload.get("$animestudio")
            if isinstance(payload.get("$animestudio"), dict)
            else {}
        )
        config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        default_playable = (
            config.get("defaultPlayable")
            if isinstance(config.get("defaultPlayable"), dict)
            else {}
        )
        default_playable_source_file = ""
        for pointer in anime.get("pptrReferences") or []:
            if (
                isinstance(pointer, dict)
                and pointer.get("path") == "$.config.defaultPlayable"
            ):
                default_playable_source_file = str(
                    pointer.get("expectedTargetSourceFile") or ""
                )
                break
        source = {
            "kind": "fmvConfigDefinition",
            "asset": rel(path),
            "pathId": anime.get("pathId"),
            "sourceFile": str(anime.get("sourceFile") or ""),
            "version": str(payload.get("version") or ""),
            "defaultPlayablePathId": default_playable.get("m_PathID"),
            "defaultPlayableSourceFile": default_playable_source_file,
        }
        source = {
            key: value
            for key, value in source.items()
            if value not in (None, "")
        }
        record = definitions.setdefault(
            fmv_id,
            {
                "fmvId": fmv_id,
                "numericIds": list(numeric_ids.get(fmv_id) or []),
                "videos": [],
                "sources": [],
                "placementEvidence": False,
            },
        )
        if source not in record["sources"]:
            record["sources"].append(source)

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
            "assetClipDuration": clip["assetClipDuration"],
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

    for action in collect_levelscript_fmv_actions():
        fmv_id = action["fmvId"]
        story_key = action["storyKey"]
        rec = get_or_create(fmv_id)
        if not rec["scene"]:
            rec["scene"] = story_key
            rec["mission"] = scene_to_mission(story_key)
        elif rec["scene"] != story_key:
            conflicts = rec.setdefault("sceneConflicts", [])
            if story_key not in conflicts:
                conflicts.append(story_key)
        rec["sources"].append({
            "kind": "levelscriptFmvAction",
            **{
                key: action[key]
                for key in (
                    "levelId",
                    "scriptId",
                    "sourceFile",
                    "actionMapRole",
                    "recordOffset",
                    "localId",
                    "actionName",
                    "nativeMappingId",
                    "fmvAction",
                )
                if action.get(key) not in (None, "", {})
            },
        })

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

    for fmv_id, rec in definitions.items():
        _, base = strip_gender(fmv_id)
        candidates: list[str] = []
        for key in (fmv_id, base):
            for video_path in by_name.get(key, []):
                video_rel = rel(video_path)
                if video_rel not in candidates:
                    candidates.append(video_rel)
        rec["videos"] = candidates
        if fmv_id in bindings:
            rec["authoritativeBindingFmvId"] = fmv_id
        elif base in bindings:
            rec["authoritativeBindingFmvId"] = base

    definition_object_cache: dict[
        tuple[str, int],
        list[tuple[Path, dict[str, Any]]],
    ] = {}
    for definition in definitions.values():
        if definition.get("authoritativeBindingFmvId"):
            continue
        definition["timelineEvidence"] = (
            collect_definition_timeline_evidence(
                definition,
                object_cache=definition_object_cache,
            )
        )

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
        "withResolvedScene": sum(
            1
            for record in bindings.values()
            if record.get("scene") and not record.get("sceneIsHint")
        ),
        "withTimelineScene": sum(
            1
            for record in bindings.values()
            if any(
                isinstance(source, dict)
                and source.get("kind") == "timelinePlayable"
                for source in record.get("sources") or []
            )
        ),
        "withMissionRuntime": sum(1 for r in bindings.values() if r.get("missions")),
        "withLevelScriptFmvAction": sum(
            1
            for record in bindings.values()
            if any(
                isinstance(source, dict)
                and source.get("kind") == "levelscriptFmvAction"
                for source in record.get("sources") or []
            )
        ),
        "fmvDefinitions": len(definitions),
        "definitionOnlyFmvIds": sum(
            1
            for definition in definitions.values()
            if not definition.get("authoritativeBindingFmvId")
        ),
        "videoFiles": len(video_files),
        "videoFilesBound": len(by_video),
        "videoFilesUnbound": len(unbound_videos),
    }

    payload = {
        "generated": int(time.time()),
        "summary": summary,
        "bindings": dict(sorted(bindings.items())),
        "definitions": dict(sorted(definitions.items())),
        "indexByScene": {k: sorted(set(v)) for k, v in sorted(by_scene.items())},
        "indexByMission": {k: sorted(set(v)) for k, v in sorted(by_mission.items())},
        "indexByVideo": {k: sorted(set(v)) for k, v in sorted(by_video.items())},
        "fmvClipsByStory": fmv_clips_by_story(bindings),
        "unboundVideos": sorted(unbound_videos),
    }
    return payload


def render_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Video Bindings",
        "",
        "Authoritative cs_video / FMV -> dialog scene -> mission graph recovered from",
        "Unity Timeline playable assets, MissionRuntimeAsset.CheckFMVFinish nodes,",
        "and exact native LevelScript FMV target fields.",
        "",
        "## Summary",
        "",
        f"- fmvIds total: `{summary.get('fmvIds', 0)}`",
        f"- with authoritative scene: `{summary.get('withResolvedScene', 0)}`",
        f"- with timeline-resolved scene: `{summary.get('withTimelineScene', 0)}`",
        f"- with MissionRuntime CheckFMVFinish: `{summary.get('withMissionRuntime', 0)}`",
        f"- with LevelScript FMV action: `{summary.get('withLevelScriptFmvAction', 0)}`",
        f"- exported FMV definitions: `{summary.get('fmvDefinitions', 0)}`",
        f"- definition-only FMV ids: `{summary.get('definitionOnlyFmvIds', 0)}`",
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
    lines.extend([
        "## Definition-only FMVs",
        "",
        "These rows have exported FMV configuration provenance but no exact",
        "Timeline, MissionRuntime, LevelScript, or gender/base binding. They are",
        "not scene, mission, ownership, or playback edges.",
        "",
        "| fmvId | numeric ids | videos | tracks | clips | subtitle ids | audio events |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for fmv_id, definition in payload.get("definitions", {}).items():
        if not isinstance(definition, dict) or definition.get(
            "authoritativeBindingFmvId"
        ):
            continue
        timeline = (
            definition.get("timelineEvidence")
            if isinstance(definition.get("timelineEvidence"), dict)
            else {}
        )
        numeric_ids = ", ".join(
            str(value) for value in definition.get("numericIds") or []
        )
        lines.append(
            f"| `{fmv_id}` | `{numeric_ids}` | "
            f"{len(definition.get('videos') or [])} | "
            f"{timeline.get('trackCount', 0)} | "
            f"{timeline.get('clipCount', 0)} | "
            f"{len(timeline.get('subtitleTextIds') or [])} | "
            f"{len(timeline.get('audioEventKeys') or [])} |"
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
        f"{s['withLevelScriptFmvAction']} via LevelScript, "
        f"{s['fmvDefinitions']} definitions, "
        f"{s['videoFilesBound']}/{s['videoFiles']} files bound"
    )
    print(f"Wrote {args.output}")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
