"""Cutscene audio events: FMV, LevelSequence, Timeline, and video bindings.

Collects the audio events each cutscene carrier declares, so conversation
relinking can attach playable media. A declared event is authored, not played."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any
from .context_utils import iter_asset_map_objects
from .context_utils import load_json_strict
from .context_utils import normalize_posix

from scripts.animestudio_index_io import ObjectIndexUnavailable
from scripts.animestudio_index_io import iter_published_objects
from scripts.animestudio_index_io import raw_json_path_for_object

def mono_behaviour_json_by_path_id(
    export_root: Path,
    wanted_path_ids: set[int] | None = None,
) -> dict[int, Path]:
    """Resolve raw object JSON paths for published path ids.

    Resolving a row costs one ``is_file`` probe, and the published index holds
    every exported object, while each caller looks up only the handful of audio
    playables it found in the asset map.  ``wanted_path_ids`` restricts the
    probe to those ids; the entries returned for them are unchanged.
    """

    out: dict[int, Path] = {}
    try:
        for row in iter_published_objects(export_root, "StreamingAssets"):
            identity = row.get("object") if isinstance(row.get("object"), dict) else {}
            try:
                path_id = int(identity.get("pathId"))
            except (TypeError, ValueError):
                continue
            if wanted_path_ids is not None and path_id not in wanted_path_ids:
                continue
            path = raw_json_path_for_object(export_root, "StreamingAssets", row)
            if path is not None:
                out[path_id] = path
        return out
    except ObjectIndexUnavailable:
        pass

    # Explicit compatibility path for old exports without a complete index.
    root = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "json_by_type"
        / "MonoBehaviour"
    )
    if not root.exists():
        return out
    for path in root.glob("*.json"):
        stem = path.stem
        marker = "_p"
        if marker not in stem:
            continue
        hex_text = stem.rsplit(marker, 1)[-1]
        try:
            unsigned = int(hex_text, 16)
        except ValueError:
            continue
        path_id = unsigned if unsigned < (1 << 63) else unsigned - (1 << 64)
        if wanted_path_ids is not None and path_id not in wanted_path_ids:
            continue
        out[path_id] = path
    return out

def collect_fmv_cutscene_audio_events(
    export_root: Path,
    language_info: dict[str, Any],
    fmv_attach_overrides: dict[str, str] | None = None,
    by_path_id: dict[int, Path] | None = None,
) -> dict[str, list[str]]:
    """Recover FMV cutscene audio events from language-specific subtitle playables."""
    suffix = str(language_info.get("fmvSuffix") or "").lower()
    if not suffix:
        return {}
    fmv_attach_overrides = fmv_attach_overrides or {}
    asset_map = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "maps"
        / "endfield_streamingassets_assets.json"
    )
    wanted_tail = f"_others_au_{suffix}.playable"
    containers: dict[str, dict[str, Any]] = {}
    event_path_ids: dict[int, str] = {}

    for entry in iter_asset_map_objects(asset_map):
        if not isinstance(entry, dict) or entry.get("Type") != "MonoBehaviour":
            continue
        container = normalize_posix(str(entry.get("Container") or "")).lower()
        if not container.endswith(wanted_tail):
            continue
        name = str(entry.get("Name") or "")
        path_id = entry.get("PathID")
        if not isinstance(path_id, int):
            continue
        file_stem = PurePosixPath(container).stem
        if not file_stem.endswith(wanted_tail[:-9]):
            continue
        base = file_stem[: -len(wanted_tail[:-9])]
        gender = None
        if base.startswith("f_cs_video_") or base.startswith("m_cs_video_"):
            gender = base[0]
            video_stem = strip_fmv_gender_prefix(base).lower()
            story_key = fmv_attach_overrides.get(video_stem) or story_key_from_fmv_id(base)
        elif base.startswith("cs_video_"):
            video_stem = base.lower()
            story_key = fmv_attach_overrides.get(video_stem) or story_key_from_fmv_id(base)
        else:
            continue
        if not story_key.startswith("cutscene_"):
            continue
        cutscene_key = story_key
        info = containers.setdefault(container, {"cutscene": cutscene_key, "events": []})
        if gender:
            info["gender"] = gender
        if name.startswith(("AudioEventPlayable", "AudioMusicPlayable")):
            event_path_ids[path_id] = container

    if not event_path_ids:
        return {}

    if by_path_id is None:
        by_path_id = mono_behaviour_json_by_path_id(export_root, set(event_path_ids))
    cutscene_events: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path_id, container in event_path_ids.items():
        path = by_path_id.get(path_id)
        if not path:
            continue
        payload = load_json_strict(path, {})
        event_key = str(payload.get("_audioEventKey") or "").strip()
        if not event_key:
            continue
        cutscene_key = str(containers.get(container, {}).get("cutscene") or "")
        if not cutscene_key:
            continue
        marker = (cutscene_key, event_key.lower())
        if marker in seen:
            continue
        seen.add(marker)
        cutscene_events[cutscene_key].append(event_key)

    return dict(cutscene_events)

def timeline_audio_container_for(container: str) -> str:
    normalized = normalize_posix(container).lower()
    if not normalized.endswith(".playable"):
        return ""
    name = PurePosixPath(normalized).name
    if name.endswith("_audio.playable"):
        return normalized
    if name.endswith("_actor.playable"):
        return normalized[: -len("_actor.playable")] + "_audio.playable"
    return ""

def strip_fmv_gender_prefix(value: str) -> str:
    match = re.match(r"^(?:f|m|fm)_(cs_video_.+)$", str(value or ""), flags=re.IGNORECASE)
    return match.group(1) if match else str(value or "")

def story_key_from_fmv_id(fmv_id: str, scene: str = "", fallback_hint: str = "") -> str:
    base = strip_fmv_gender_prefix(str(fmv_id or "").strip())
    if base.startswith("cs_video_dlg_"):
        return f"dlg_{base[len('cs_video_dlg_'):]}"
    if base.startswith("cs_video_remotecomm_"):
        return f"remotecomm_{base[len('cs_video_remotecomm_'):]}"
    if base.startswith("cs_video_cutscene_"):
        return f"cutscene_{base[len('cs_video_cutscene_'):]}"
    if base.startswith("cs_video_"):
        return f"cutscene_{base[len('cs_video_'):]}"

    for candidate in (fallback_hint, scene):
        value = str(candidate or "").strip()
        if value.startswith(("dlg_", "cutscene_", "remotecomm_")):
            return value
    scene_value = str(scene or "").strip()
    return f"cutscene_{scene_value}" if scene_value else ""

def story_key_from_video_binding(binding: dict[str, Any]) -> str:
    return story_key_from_fmv_id(
        str(binding.get("baseFmvId") or binding.get("fmvId") or ""),
        str(binding.get("scene") or ""),
        str(binding.get("fallbackSceneHint") or ""),
    )

def collect_video_binding_audio_containers(export_root: Path) -> dict[str, str]:
    path = export_root / "recovered" / "video_bindings.json"
    payload = load_json_strict(path, {})
    bindings = payload.get("bindings") if isinstance(payload, dict) else {}
    out: dict[str, str] = {}
    if not isinstance(bindings, dict):
        return out

    for binding in bindings.values():
        if not isinstance(binding, dict):
            continue
        story_key = story_key_from_video_binding(binding)
        if not story_key.startswith("cutscene_"):
            continue
        for source in binding.get("sources") or []:
            if not isinstance(source, dict):
                continue
            container = timeline_audio_container_for(str(source.get("container") or ""))
            if container:
                out[container] = story_key
    return out

def collect_timeline_cutscene_audio_events(
    export_root: Path,
    by_path_id: dict[int, Path] | None = None,
) -> dict[str, list[str]]:
    container_to_cutscene = collect_video_binding_audio_containers(export_root)
    if not container_to_cutscene:
        return {}
    asset_map = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "maps"
        / "endfield_streamingassets_assets.json"
    )

    event_path_ids: dict[int, str] = {}
    for entry in iter_asset_map_objects(asset_map):
        if not isinstance(entry, dict) or entry.get("Type") != "MonoBehaviour":
            continue
        container = normalize_posix(str(entry.get("Container") or "")).lower()
        if container not in container_to_cutscene:
            continue
        name = str(entry.get("Name") or "")
        path_id = entry.get("PathID")
        if isinstance(path_id, int) and name.startswith(
            ("AudioDlgEventPlayable", "AudioEventPlayable", "AudioMusicPlayable")
        ):
            event_path_ids[path_id] = container

    if not event_path_ids:
        return {}

    if by_path_id is None:
        by_path_id = mono_behaviour_json_by_path_id(export_root, set(event_path_ids))
    cutscene_events: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path_id, container in event_path_ids.items():
        path = by_path_id.get(path_id)
        if not path:
            continue
        payload = load_json_strict(path, {})
        event_key = str(payload.get("_audioEventKey") or "").strip()
        if not event_key or event_key == "au_music_dlg_empty":
            continue
        cutscene_key = container_to_cutscene.get(container) or ""
        marker = (cutscene_key, event_key.lower())
        if not cutscene_key or marker in seen:
            continue
        seen.add(marker)
        cutscene_events[cutscene_key].append(event_key)

    return dict(cutscene_events)

def collect_levelseq_cutscene_audio_events(
    export_root: Path,
    by_path_id: dict[int, Path] | None = None,
) -> dict[str, list[str]]:
    asset_map = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "maps"
        / "endfield_streamingassets_assets.json"
    )
    event_path_ids: dict[int, str] = {}
    container_to_cutscene: dict[str, str] = {}

    for entry in iter_asset_map_objects(asset_map):
        if not isinstance(entry, dict) or entry.get("Type") != "MonoBehaviour":
            continue
        container = normalize_posix(str(entry.get("Container") or "")).lower()
        parts = PurePosixPath(container).parts
        if len(parts) < 4:
            continue
        name = str(entry.get("Name") or "")
        path_id = entry.get("PathID")
        filename = parts[-1]
        folder = parts[-3] if len(parts) >= 3 else ""
        if (
            "gameplay" not in parts
            or "levelseq" not in parts
            or not folder.startswith("levelseq_")
            or filename != f"{folder}_audio.playable"
        ):
            continue
        cutscene_key = "cutscene_" + folder[len("levelseq_") :]
        container_to_cutscene[container] = cutscene_key
        if isinstance(path_id, int) and name.startswith(
            ("AudioDlgEventPlayable", "AudioEventPlayable", "AudioMusicPlayable")
        ):
            event_path_ids[path_id] = container

    if not event_path_ids:
        return {}

    if by_path_id is None:
        by_path_id = mono_behaviour_json_by_path_id(export_root, set(event_path_ids))
    cutscene_events: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path_id, container in event_path_ids.items():
        path = by_path_id.get(path_id)
        if not path:
            continue
        payload = load_json_strict(path, {})
        event_key = str(payload.get("_audioEventKey") or "").strip()
        if not event_key or event_key == "au_music_dlg_empty":
            continue
        cutscene_key = container_to_cutscene.get(container) or ""
        marker = (cutscene_key, event_key.lower())
        if not cutscene_key or marker in seen:
            continue
        seen.add(marker)
        cutscene_events[cutscene_key].append(event_key)

    return dict(cutscene_events)
