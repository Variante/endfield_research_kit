#!/usr/bin/env python3
"""Decode story audio into export_full and link playable files into WebUI data."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath
from struct import unpack_from
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_FLUFFY = ROOT / "tools" / "fluffy-dumper-src" / "target" / "release" / "fluffy-dumper.exe"
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_WEBUI_ROOT = ROOT / "webui"
DEFAULT_AUDIO_ROOT = DEFAULT_EXPORT_ROOT / "structured" / "Audio"
NARRATIVE_VIDEO_OVERRIDES_NAME = "narrative_videos.json"

LANGUAGES = {
    "CN": {
        "dumper": "chinese",
        "fmvSuffix": "cn",
        "durationField": "wavDuration",
        "label": "Chinese",
    },
    "EN": {
        "dumper": "english",
        "fmvSuffix": "en",
        "durationField": "wavDurationEN",
        "label": "English",
    },
    "JP": {
        "dumper": "japanese",
        "fmvSuffix": "jp",
        "durationField": "wavDurationJP",
        "label": "Japanese",
    },
    "KR": {
        "dumper": "korean",
        "fmvSuffix": "ko",
        "durationField": "wavDurationKR",
        "label": "Korean",
    },
}

AUDIO_EXTENSIONS = {".wav", ".wem"}
EVENT_PREFIXES = ("au_sfx_", "au_vo_", "au_music_", "au_cue_", "au_amb_", "au_ui_")


def normalize_posix(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_video_override_stem(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    text = text.rsplit("/", 1)[-1]
    return re.sub(r"\.[^.]+$", "", text, flags=re.IGNORECASE).lower()


def load_narrative_video_attach_overrides(webui_root: Path) -> dict[str, str]:
    """Return `{video_stem: target_story_key}` for manual inline video attachments."""
    path = webui_root / "overrides" / NARRATIVE_VIDEO_OVERRIDES_NAME
    payload = load_json(path, {})
    if not isinstance(payload, dict):
        return {}

    raw_rules = payload.get("attachInline") or payload.get("attachTo")
    out: dict[str, str] = {}

    def add_rule(target_key: object, raw_rule: object) -> None:
        key = str(target_key or "").strip()
        if not key:
            return
        raw_stems: object = []
        if isinstance(raw_rule, dict):
            raw_stems = (
                raw_rule.get("stems")
                or raw_rule.get("videoStems")
                or raw_rule.get("stem")
                or raw_rule.get("videoStem")
                or []
            )
        elif isinstance(raw_rule, list):
            raw_stems = raw_rule
        elif raw_rule:
            raw_stems = [raw_rule]
        if isinstance(raw_stems, (str, int, float)):
            raw_stems = [raw_stems]
        for raw_stem in raw_stems or []:
            stem = normalize_video_override_stem(raw_stem)
            if stem:
                out[stem] = key

    if isinstance(raw_rules, dict):
        for target_key, raw_rule in raw_rules.items():
            add_rule(target_key, raw_rule)
    elif isinstance(raw_rules, list):
        for raw_rule in raw_rules:
            if not isinstance(raw_rule, dict):
                continue
            target_key = (
                raw_rule.get("targetKey")
                or raw_rule.get("key")
                or raw_rule.get("resolvedKey")
                or raw_rule.get("attachTo")
            )
            add_rule(target_key, raw_rule)

    return out


def find_audio_dialog_table(export_root: Path) -> Path:
    candidates = [
        export_root / "structured" / "StreamingAssets" / "Table" / "AudioDialog.json",
        export_root / "structured" / "Persistent" / "Table" / "AudioDialog.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(
        "AudioDialog.json not found under export_full/structured. "
        "Run export.bat first, or pass --export-root."
    )


def audio_id_from_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).stem.lower()


def fnv1_32(value: str) -> int:
    hash_value = 0x811C9DC5
    for byte in value.encode("utf-8"):
        hash_value = (hash_value * 0x01000193) & 0xFFFFFFFF
        hash_value ^= byte
    return hash_value


def derive_vfs_key(seed: int) -> int:
    key = ((seed & 0xFF) ^ 0x9C5A0B29) * 81861667
    key &= 0xFFFFFFFF
    for shift in (8, 16, 24):
        key = (key ^ ((seed >> shift) & 0xFF)) * 81861667
        key &= 0xFFFFFFFF
    return key


def decrypt_vfs_bytes(data: bytearray, start: int, length: int, seed: int, data_offset: int = 0) -> None:
    key_index = (seed + (data_offset >> 2)) & 0xFFFFFFFF
    pos = start
    remaining = length
    alignment = data_offset & 3
    if alignment:
        key = derive_vfs_key(key_index)
        to_align = min(4 - alignment, remaining)
        for i in range(to_align):
            data[pos] ^= (key >> ((alignment + i) * 8)) & 0xFF
            pos += 1
        remaining -= to_align
        key_index = (key_index + 1) & 0xFFFFFFFF

    for _ in range(remaining // 4):
        key = derive_vfs_key(key_index)
        value = int.from_bytes(data[pos : pos + 4], "little") ^ key
        data[pos : pos + 4] = value.to_bytes(4, "little")
        pos += 4
        key_index = (key_index + 1) & 0xFFFFFFFF

    trailing = remaining & 3
    if trailing:
        key = derive_vfs_key(key_index)
        for i in range(trailing):
            data[pos + i] ^= (key >> (i * 8)) & 0xFF


def read_decrypted_akpk(path: Path) -> bytes:
    data = bytearray(path.read_bytes())
    if data[:4] == b":)xD":
        header_size = int.from_bytes(data[4:8], "little")
        decrypt_vfs_bytes(data, 12, header_size - 4, header_size)
        data[:4] = b"AKPK"
        data[8:12] = (1).to_bytes(4, "little")
    if data[:4] != b"AKPK":
        raise ValueError(f"invalid AKPK magic: {path}")
    return bytes(data)


def iter_akpk_bank_payloads(path: Path) -> list[tuple[int, bytes]]:
    data = read_decrypted_akpk(path)
    if len(data) < 28:
        return []
    header_size = unpack_from("<I", data, 4)[0]
    language_size = unpack_from("<I", data, 12)[0]
    banks_size = unpack_from("<I", data, 16)[0]
    sounds_size = unpack_from("<I", data, 20)[0]
    has_externals = language_size + banks_size + sounds_size + 0x10 < header_size
    pos = 28 if has_externals else 24
    pos += language_size
    if banks_size < 4 or pos + banks_size > len(data):
        return []
    count = unpack_from("<I", data, pos)[0]
    if not count:
        return []
    entry_size = (banks_size - 4) // count
    if entry_size not in (20, 24):
        return []
    pos += 4
    banks: list[tuple[int, bytes]] = []
    for _ in range(count):
        file_id = unpack_from("<I", data, pos)[0]
        block_size = unpack_from("<I", data, pos + 4)[0]
        if entry_size == 24:
            size = unpack_from("<Q", data, pos + 8)[0]
            offset = unpack_from("<I", data, pos + 16)[0]
        else:
            size = unpack_from("<I", data, pos + 8)[0]
            offset = unpack_from("<I", data, pos + 12)[0]
        real_offset = offset * (block_size or 1)
        pos += entry_size
        if size <= 0 or real_offset + size > len(data):
            continue
        payload = bytearray(data[real_offset : real_offset + size])
        decrypt_vfs_bytes(payload, 0, len(payload), file_id)
        if payload[:4] == b"BKHD":
            banks.append((file_id, bytes(payload)))
    return banks


def iter_bnk_sections(bank_payload: bytes) -> list[tuple[bytes, bytes]]:
    sections: list[tuple[bytes, bytes]] = []
    pos = 0
    while pos + 8 <= len(bank_payload):
        tag = bank_payload[pos : pos + 4]
        size = unpack_from("<I", bank_payload, pos + 4)[0]
        body_start = pos + 8
        body_end = body_start + size
        if body_end > len(bank_payload) or not tag.isalpha():
            break
        sections.append((tag, bank_payload[body_start:body_end]))
        pos = body_end
    return sections


def parse_hirc_objects(bank_payload: bytes) -> dict[int, dict[str, Any]]:
    objects: dict[int, dict[str, Any]] = {}
    for tag, body in iter_bnk_sections(bank_payload):
        if tag != b"HIRC" or len(body) < 4:
            continue
        count = unpack_from("<I", body, 0)[0]
        pos = 4
        for _ in range(count):
            if pos + 9 > len(body):
                break
            object_type = body[pos]
            object_size = unpack_from("<I", body, pos + 1)[0]
            object_id = unpack_from("<I", body, pos + 5)[0]
            data_start = pos + 9
            data_end = pos + 1 + 4 + object_size
            if data_end > len(body):
                break
            objects[object_id] = {
                "type": object_type,
                "data": body[data_start:data_end],
            }
            pos = data_end
    return objects


def hirc_event_action_ids(data: bytes) -> list[int]:
    if not data:
        return []
    count = data[0]
    ids: list[int] = []
    pos = 1
    for _ in range(count):
        if pos + 4 > len(data):
            break
        ids.append(unpack_from("<I", data, pos)[0])
        pos += 4
    return ids


def hirc_action_target_id(data: bytes) -> int | None:
    if len(data) < 6:
        return None
    return unpack_from("<I", data, 2)[0]


def u32_values(data: bytes) -> list[int]:
    values: list[int] = []
    for pos in range(0, max(0, len(data) - 3)):
        values.append(unpack_from("<I", data, pos)[0])
    return values


def audio_rel_for_dialog_path(language_info: dict[str, str], dialog_path: str, extension: str) -> str:
    path = dialog_path.replace("\\", "/")
    if extension.lower() == ".wav":
        path = str(PurePosixPath(path).with_suffix(".wav"))
    return normalize_posix(Path("voice") / language_info["dumper"] / path.lower())


def served_audio_href(audio_root: Path, webui_root: Path, language: str, relative_audio_path: str) -> str:
    audio_path = audio_root / language / Path(*PurePosixPath(relative_audio_path).parts)
    if audio_path.is_relative_to(webui_root):
        return normalize_posix(audio_path.relative_to(webui_root))
    if audio_path.is_relative_to(ROOT):
        return "/" + normalize_posix(audio_path.relative_to(ROOT))
    raise SystemExit(
        "Audio root must be under the WebUI root or project root so generated "
        f"audioSrc links are servable: {audio_root}"
    )


def iter_audio_files(language_root: Path) -> list[Path]:
    if not language_root.exists():
        return []
    return sorted(
        path
        for path in language_root.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )


def has_decoded_audio(language_root: Path) -> bool:
    if not language_root.exists():
        return False
    for path in language_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            return True
    return False


def collect_audio_files(
    audio_root: Path,
    webui_root: Path,
    language_root: Path,
    language: str,
) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in iter_audio_files(language_root):
        rel = normalize_posix(path.relative_to(language_root))
        audio_id = path.stem.lower()
        stat = path.stat()
        entry = {
            "id": audio_id,
            "rel": rel,
            "src": served_audio_href(audio_root, webui_root, language, rel),
            "format": path.suffix.lower().lstrip("."),
            "bytes": stat.st_size,
        }
        by_id.setdefault(audio_id, entry)
    return by_id


def build_dialog_audio_index(
    audio_dialog_path: Path,
    audio_root: Path,
    webui_root: Path,
    language_root: Path,
    language: str,
    language_info: dict[str, str],
    preferred_extension: str,
) -> dict[str, dict[str, Any]]:
    rows = load_json(audio_dialog_path, {})
    if not isinstance(rows, dict):
        raise SystemExit(f"AudioDialog table has unexpected shape: {audio_dialog_path}")

    duration_field = language_info["durationField"]
    out: dict[str, dict[str, Any]] = {}
    for row_key, row in rows.items():
        if not isinstance(row, dict):
            continue
        dialog_path = str(row.get("path") or "")
        if not dialog_path:
            continue
        audio_id = audio_id_from_path(dialog_path)
        rel = audio_rel_for_dialog_path(language_info, dialog_path, preferred_extension)
        file_path = language_root / Path(*PurePosixPath(rel).parts)
        if not file_path.exists() and preferred_extension.lower() == ".wav":
            rel = audio_rel_for_dialog_path(language_info, dialog_path, ".wem")
            file_path = language_root / Path(*PurePosixPath(rel).parts)
        if not file_path.exists():
            continue
        duration = row.get(duration_field)
        out[audio_id] = {
            "id": audio_id,
            "rel": rel,
            "src": served_audio_href(audio_root, webui_root, language, rel),
            "format": file_path.suffix.lower().lstrip("."),
            "bytes": file_path.stat().st_size,
            "audioDialogKey": int(row_key) if str(row_key).lstrip("-").isdigit() else row_key,
            "audioDialogPath": dialog_path,
            "speakerChannel": str(row.get("speakerChannel") or ""),
            "voType": row.get("voType"),
            "duration": duration if isinstance(duration, (int, float)) else None,
        }
    return out


def collect_audio_event_names(conv_dir: Path, export_root: Path) -> set[str]:
    names: set[str] = set()

    for conv_path in sorted(conv_dir.glob("*.json")):
        payload = load_json(conv_path, {})
        if not isinstance(payload, dict):
            continue
        for value in payload.get("audioEvents") or []:
            text = str(value or "").strip()
            if text:
                names.add(text)
        cutscene = payload.get("cutscene")
        if isinstance(cutscene, dict):
            for value in cutscene.get("audioEvents") or []:
                text = str(value or "").strip()
                if text:
                    names.add(text)

    table_roots = [
        export_root / "structured" / "StreamingAssets" / "Table",
        export_root / "structured" / "Persistent" / "Table",
    ]
    table_files = [
        "AudioCueTable.json",
        "AudioDialogCustomEventTable.json",
        "RemoteCommonTable.json",
    ]

    def visit(value: Any) -> None:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.lower().startswith(EVENT_PREFIXES):
                names.add(stripped)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for table_root in table_roots:
        for table_file in table_files:
            path = table_root / table_file
            payload = load_json(path, {})
            if payload:
                visit(payload)

    return names


def path_id_hex(path_id: int) -> str:
    return f"{path_id & ((1 << 64) - 1):016X}"


def mono_behaviour_json_by_path_id(export_root: Path) -> dict[int, Path]:
    root = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "json_by_type"
        / "MonoBehaviour"
    )
    out: dict[int, Path] = {}
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
        out[path_id] = path
    return out


def iter_asset_map_objects(path: Path) -> Any:
    if not path.exists():
        return
    block: list[str] = []
    depth = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not block and not line.startswith("    {"):
                continue
            block.append(line)
            depth += line.count("{") - line.count("}")
            if block and depth == 0:
                text = "".join(block)
                block = []
                if '"Container"' not in text or '"PathID"' not in text:
                    continue
                try:
                    yield json.loads(text.rstrip(",\r\n"))
                except json.JSONDecodeError:
                    continue


def collect_fmv_cutscene_audio_events(
    export_root: Path,
    language_info: dict[str, Any],
    fmv_attach_overrides: dict[str, str] | None = None,
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

    by_path_id = mono_behaviour_json_by_path_id(export_root)
    cutscene_events: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path_id, container in event_path_ids.items():
        path = by_path_id.get(path_id)
        if not path:
            continue
        payload = load_json(path, {})
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
    payload = load_json(path, {})
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


def collect_timeline_cutscene_audio_events(export_root: Path) -> dict[str, list[str]]:
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

    by_path_id = mono_behaviour_json_by_path_id(export_root)
    cutscene_events: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path_id, container in event_path_ids.items():
        path = by_path_id.get(path_id)
        if not path:
            continue
        payload = load_json(path, {})
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


def collect_levelseq_cutscene_audio_events(export_root: Path) -> dict[str, list[str]]:
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

    by_path_id = mono_behaviour_json_by_path_id(export_root)
    cutscene_events: dict[str, list[str]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path_id, container in event_path_ids.items():
        path = by_path_id.get(path_id)
        if not path:
            continue
        payload = load_json(path, {})
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


def event_bank_files(export_root: Path) -> list[Path]:
    roots = [
        export_root / "structured" / "Persistent" / "Data" / "Audio" / "PCK" / "Windows",
        export_root / "structured" / "StreamingAssets" / "Data" / "Audio" / "PCK" / "Windows",
    ]
    files: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*banks.pck")):
            key = normalize_posix(path.relative_to(export_root))
            if key in seen:
                continue
            seen.add(key)
            files.append(path)
    return files


def collect_event_audio_index(
    event_names: set[str],
    audio_by_id: dict[str, dict[str, Any]],
    export_root: Path,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    if not event_names:
        return {}, []

    wanted_by_hash: dict[int, str] = {
        fnv1_32(name.lower()): name
        for name in event_names
    }
    numeric_audio_ids = {
        int(audio_id)
        for audio_id in audio_by_id
        if audio_id.isdigit()
    }
    if not numeric_audio_ids:
        return {}, []

    event_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_evidence: dict[tuple[str, int], dict[str, Any]] = {}
    seen_links: set[tuple[str, str]] = set()

    for bank_file in event_bank_files(export_root):
        try:
            bank_payloads = iter_akpk_bank_payloads(bank_file)
        except (OSError, ValueError):
            continue
        for bank_id, bank_payload in bank_payloads:
            objects = parse_hirc_objects(bank_payload)
            if not objects:
                continue
            for event_hash, event_name in wanted_by_hash.items():
                event_object = objects.get(event_hash)
                if not event_object or event_object.get("type") != 4:
                    continue
                action_ids = hirc_event_action_ids(event_object.get("data") or b"")
                queue: deque[int] = deque(action_ids)
                visited: set[int] = {event_hash}
                media_ids: list[int] = []
                while queue:
                    object_id = queue.popleft()
                    if object_id in visited:
                        continue
                    visited.add(object_id)
                    obj = objects.get(object_id)
                    if not obj:
                        continue
                    object_type = int(obj.get("type") or 0)
                    data = obj.get("data") or b""
                    if object_id in numeric_audio_ids:
                        media_ids.append(object_id)
                    if object_type == 3:
                        target = hirc_action_target_id(data)
                        if target is not None:
                            queue.append(target)
                    for value in u32_values(data):
                        if value in numeric_audio_ids and value not in media_ids:
                            media_ids.append(value)
                        if value in objects and value not in visited:
                            queue.append(value)

                evidence_key = (event_name.lower(), bank_id)
                event_evidence[evidence_key] = {
                    "eventId": event_name,
                    "eventHash": event_hash,
                    "bankId": bank_id,
                    "bank": normalize_posix(bank_file.relative_to(export_root)),
                    "actionIds": action_ids,
                    "visitedObjectIds": sorted(visited),
                    "mediaIds": media_ids,
                    "resolvedMediaCount": len(media_ids),
                    "source": "wwiseHirc",
                }
                for media_id in media_ids:
                    audio_entry = audio_by_id.get(str(media_id))
                    if not audio_entry:
                        continue
                    link_key = (event_name.lower(), str(media_id))
                    if link_key in seen_links:
                        continue
                    seen_links.add(link_key)
                    linked = {
                        **audio_entry,
                        "id": event_name,
                        "eventId": event_name,
                        "mediaId": media_id,
                        "bankId": bank_id,
                        "bank": normalize_posix(bank_file.relative_to(export_root)),
                        "source": "wwiseHirc",
                    }
                    event_links[event_name.lower()].append(linked)

    return dict(event_links), sorted(
        event_evidence.values(),
        key=lambda item: (str(item.get("eventId") or ""), int(item.get("bankId") or 0)),
    )


def merge_event_map(target: dict[str, list[str]], *sources: dict[str, list[str]]) -> dict[str, list[str]]:
    for source in sources:
        for cutscene_key, events in source.items():
            merged = target.setdefault(cutscene_key, [])
            seen = {str(event or "").strip().lower() for event in merged}
            for event in events:
                event_key = str(event or "").strip().lower()
                if event_key and event_key not in seen:
                    seen.add(event_key)
                    merged.append(event)
    return target


def _event_name_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {
        str(value or "").strip().lower()
        for value in values
        if str(value or "").strip()
    }


def _audio_entry_file_exists(language_root: Path, entry: dict[str, Any]) -> bool:
    rel = str(entry.get("rel") or "").strip()
    if not rel:
        return False
    return (language_root / Path(*PurePosixPath(rel).parts)).is_file()


def load_cached_event_audio_index(
    language_root: Path,
    event_names: set[str],
    audio_root: Path,
    webui_root: Path,
    language: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]] | None:
    """Reuse event-to-media links from the last audio index when complete."""
    payload = load_json(language_root / "index.json", {})
    if not isinstance(payload, dict):
        return None
    wanted_names = {
        str(name or "").strip().lower()
        for name in event_names
        if str(name or "").strip()
    }
    cached_names = _event_name_set(payload.get("eventNames"))
    if not wanted_names or not cached_names or not wanted_names.issubset(cached_names):
        return None

    event_audio_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in payload.get("events") or []:
        if not isinstance(entry, dict):
            continue
        event_key = str(entry.get("eventId") or entry.get("id") or "").strip().lower()
        if event_key not in wanted_names or not _audio_entry_file_exists(language_root, entry):
            continue
        cached = dict(entry)
        cached["src"] = served_audio_href(audio_root, webui_root, language, str(cached.get("rel") or ""))
        event_audio_by_id[event_key].append(cached)

    event_evidence = [
        entry
        for entry in (payload.get("eventEvidence") or [])
        if isinstance(entry, dict)
        and str(entry.get("eventId") or "").strip().lower() in wanted_names
    ]
    return dict(event_audio_by_id), event_evidence


def run_fluffy_dumper(args: argparse.Namespace, language_info: dict[str, str], language_root: Path) -> None:
    if args.skip_decode:
        return
    if not args.fluffy.exists():
        raise SystemExit(f"fluffy-dumper not found: {args.fluffy}")
    if not args.streaming_assets.exists():
        raise SystemExit(f"StreamingAssets not found: {args.streaming_assets}")

    command = [
        str(args.fluffy),
        "audio",
        "--streaming-assets",
        str(args.streaming_assets),
        "--output",
        str(language_root),
        "--language",
        language_info["dumper"],
        "--format",
        args.format,
        "--block",
        args.block,
    ]
    if args.fallback_assets and args.fallback_assets.exists():
        command.extend(["--fallback-assets", str(args.fallback_assets)])

    print("Running:", " ".join(f'"{part}"' if " " in part else part for part in command))
    subprocess.run(command, cwd=ROOT, check=True)


def line_audio_ids(line: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for field in ("voice", "audio"):
        audio_id = str(line.get(field) or "").strip().lower()
        if audio_id and audio_id not in seen:
            seen.add(audio_id)
            ids.append(audio_id)
    return ids


def attach_audio_to_line(line: dict[str, Any], audio_entry: dict[str, Any]) -> bool:
    changed = False
    src = audio_entry.get("src") or ""
    if src and line.get("audioSrc") != src:
        line["audioSrc"] = src
        changed = True
    meta = {
        key: audio_entry.get(key)
        for key in ("audioDialogKey", "audioDialogPath", "speakerChannel", "voType", "duration", "format", "bytes")
        if audio_entry.get(key) not in (None, "")
    }
    if meta and line.get("audioMeta") != meta:
        line["audioMeta"] = meta
        changed = True
    return changed


def attach_audio_variants_to_line(line: dict[str, Any], variants: dict[str, dict[str, Any]]) -> bool:
    changed = False
    payload: dict[str, Any] = {}
    for gender in ("f", "m"):
        entry = variants.get(gender)
        if not entry or not entry.get("src"):
            continue
        meta = {
            key: entry.get(key)
            for key in ("audioDialogKey", "audioDialogPath", "speakerChannel", "voType", "duration", "format", "bytes")
            if entry.get(key) not in (None, "")
        }
        payload[gender] = {
            "id": entry.get("id"),
            "src": entry.get("src"),
            "meta": meta,
        }
    if payload and line.get("audioVariants") != payload:
        line["audioVariants"] = payload
        changed = True
    return changed


def cutscene_line_signature(payload: dict[str, Any]) -> tuple[str, ...]:
    lines = payload.get("lines") or []
    ids = {
        str(line.get("id") or "").strip().lower()
        for line in lines
        if isinstance(line, dict) and str(line.get("id") or "").strip()
    }
    return tuple(sorted(ids))


def collect_cutscene_audio_events_by_line_signature(conv_dir: Path) -> dict[tuple[str, ...], list[str]]:
    by_signature: dict[tuple[str, ...], list[str]] = {}
    seen_by_signature: dict[tuple[str, ...], set[str]] = {}
    for conv_path in sorted(conv_dir.glob("*.json")):
        payload = load_json(conv_path, {})
        if not isinstance(payload, dict) or not isinstance(payload.get("cutscene"), dict):
            continue
        signature = cutscene_line_signature(payload)
        if not signature:
            continue
        events = payload["cutscene"].get("audioEvents") or []
        if not events:
            continue
        out = by_signature.setdefault(signature, [])
        seen = seen_by_signature.setdefault(signature, set())
        for event in events:
            event_text = str(event or "").strip()
            event_key = event_text.lower()
            if not event_text or event_key in seen:
                continue
            seen.add(event_key)
            out.append(event_text)
    return by_signature


def linked_audio_files_for_events(
    event_ids: list[Any],
    audio_by_id: dict[str, dict[str, Any]],
    event_audio_by_id: dict[str, list[dict[str, Any]]],
    stats: dict[str, int],
    event_stat_key: str,
    linked_stat_key: str,
) -> list[dict[str, Any]]:
    linked_events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event_id in event_ids or []:
        event_key = str(event_id or "").strip().lower()
        if not event_key:
            continue
        stats[event_stat_key] += 1
        entries = event_audio_by_id.get(event_key) or []
        if not entries:
            direct = audio_by_id.get(event_key)
            entries = [direct] if direct else []
        for entry in entries:
            if not entry:
                continue
            linked_key = f"{event_key}:{entry.get('mediaId') or entry.get('rel') or entry.get('src')}"
            if linked_key in seen:
                continue
            seen.add(linked_key)
            linked_events.append({
                "id": event_id,
                "src": entry.get("src"),
                "format": entry.get("format"),
                "bytes": entry.get("bytes"),
                "mediaId": entry.get("mediaId"),
                "bank": entry.get("bank"),
                "source": entry.get("source"),
            })
            stats[linked_stat_key] += 1
    return linked_events


def link_conversation_audio(
    conv_dir: Path,
    audio_by_id: dict[str, dict[str, Any]],
    event_audio_by_id: dict[str, list[dict[str, Any]]] | None = None,
    cutscene_audio_events: dict[str, list[str]] | None = None,
) -> dict[str, int]:
    event_audio_by_id = event_audio_by_id or {}
    cutscene_audio_events = cutscene_audio_events or {}
    stats = {
        "conversationFiles": 0,
        "conversationFilesChanged": 0,
        "lineAudioRefs": 0,
        "lineAudioLinked": 0,
        "conversationAudioEvents": 0,
        "conversationAudioEventsLinked": 0,
        "cutsceneAudioEvents": 0,
        "cutsceneAudioEventsLinked": 0,
        "cutsceneAudioEventsInherited": 0,
    }
    cutscene_events_by_line_signature = collect_cutscene_audio_events_by_line_signature(conv_dir)

    for conv_path in sorted(conv_dir.glob("*.json")):
        payload = load_json(conv_path, {})
        if not isinstance(payload, dict):
            continue
        stats["conversationFiles"] += 1
        changed = False
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            audio_ids = line_audio_ids(line)
            if not audio_ids:
                continue
            stats["lineAudioRefs"] += 1
            for audio_id in audio_ids:
                entry = audio_by_id.get(audio_id)
                if entry:
                    if attach_audio_to_line(line, entry):
                        changed = True
                    stats["lineAudioLinked"] += 1
                    break
                variants = {
                    gender: audio_by_id.get(f"{audio_id}_{gender}")
                    for gender in ("f", "m")
                }
                variants = {gender: variant for gender, variant in variants.items() if variant}
                if variants:
                    if attach_audio_variants_to_line(line, variants):
                        changed = True
                    stats["lineAudioLinked"] += 1
                    break

        root_audio_events = payload.get("audioEvents") if isinstance(payload.get("audioEvents"), list) else []
        if root_audio_events:
            linked_root_events = linked_audio_files_for_events(
                root_audio_events,
                audio_by_id,
                event_audio_by_id,
                stats,
                "conversationAudioEvents",
                "conversationAudioEventsLinked",
            )
            if linked_root_events and payload.get("audioFiles") != linked_root_events:
                payload["audioFiles"] = linked_root_events
                changed = True
            elif not linked_root_events and payload.get("audioFiles"):
                payload.pop("audioFiles", None)
                changed = True

        cutscene = payload.get("cutscene")
        if isinstance(cutscene, dict):
            cutscene_key = str(payload.get("key") or conv_path.stem)
            recovered_events = cutscene_audio_events.get(cutscene_key) or []
            existing_events = list(cutscene.get("audioEvents") or [])
            if not existing_events and not recovered_events:
                inherited_events = cutscene_events_by_line_signature.get(cutscene_line_signature(payload)) or []
                if inherited_events:
                    recovered_events = inherited_events
                    stats["cutsceneAudioEventsInherited"] += len(inherited_events)
            if recovered_events:
                merged_events: list[str] = []
                seen_events: set[str] = set()
                for event_id in existing_events + recovered_events:
                    event_text = str(event_id or "").strip()
                    event_key = event_text.lower()
                    if not event_text or event_key in seen_events:
                        continue
                    seen_events.add(event_key)
                    merged_events.append(event_text)
                if cutscene.get("audioEvents") != merged_events:
                    cutscene["audioEvents"] = merged_events
                    changed = True
            linked_events = linked_audio_files_for_events(
                cutscene.get("audioEvents") or [],
                audio_by_id,
                event_audio_by_id,
                stats,
                "cutsceneAudioEvents",
                "cutsceneAudioEventsLinked",
            )
            if linked_events and cutscene.get("audioFiles") != linked_events:
                cutscene["audioFiles"] = linked_events
                changed = True
            elif not linked_events and cutscene.get("audioFiles"):
                cutscene.pop("audioFiles", None)
                changed = True

        if changed:
            json_dump(conv_path, payload)
            stats["conversationFilesChanged"] += 1

    return stats


def build_audio(args: argparse.Namespace) -> int:
    args.export_root = args.export_root.resolve()
    args.webui_root = args.webui_root.resolve()
    args.audio_root = args.audio_root.resolve()
    language = args.language.upper()
    language_info = LANGUAGES[language]
    language_root = args.audio_root / language
    if args.skip_decode and not has_decoded_audio(language_root):
        print(f"Audio build [{language}]: skipped (no decoded audio files at {language_root})")
        return 0
    if not args.skip_decode:
        language_root.mkdir(parents=True, exist_ok=True)

    started = time.time()
    run_fluffy_dumper(args, language_info, language_root)

    audio_dialog_path = find_audio_dialog_table(args.export_root)
    generic_audio = collect_audio_files(args.audio_root, args.webui_root, language_root, language)
    dialog_audio = build_dialog_audio_index(
        audio_dialog_path,
        args.audio_root,
        args.webui_root,
        language_root,
        language,
        language_info,
        "." + args.format.lower(),
    )
    audio_by_id = {**generic_audio, **dialog_audio}

    conv_dir = args.webui_root / "data" / "lang" / language / "conv"
    if not conv_dir.exists():
        raise SystemExit(f"Conversation directory not found: {conv_dir}")
    event_names = collect_audio_event_names(conv_dir, args.export_root)
    fmv_attach_overrides = load_narrative_video_attach_overrides(args.webui_root)
    cutscene_audio_events = collect_fmv_cutscene_audio_events(
        args.export_root,
        language_info,
        fmv_attach_overrides,
    )
    merge_event_map(
        cutscene_audio_events,
        collect_timeline_cutscene_audio_events(args.export_root),
        collect_levelseq_cutscene_audio_events(args.export_root),
    )
    for events in cutscene_audio_events.values():
        event_names.update(str(event or "").strip() for event in events if str(event or "").strip())
    cached_event_index = (
        load_cached_event_audio_index(
            language_root,
            event_names,
            args.audio_root,
            args.webui_root,
            language,
        )
        if args.skip_decode
        else None
    )
    if cached_event_index is not None:
        event_audio_by_id, event_evidence = cached_event_index
        print("Audio events: reused existing event-media index")
    else:
        event_audio_by_id, event_evidence = collect_event_audio_index(event_names, audio_by_id, args.export_root)
    event_entries = [
        entry
        for entries in event_audio_by_id.values()
        for entry in entries
    ]
    audio_by_id.update({
        str(entry.get("eventId") or entry.get("id") or "").lower(): entry
        for entry in event_entries
        if entry.get("eventId") or entry.get("id")
    })
    link_stats = link_conversation_audio(conv_dir, audio_by_id, event_audio_by_id, cutscene_audio_events)

    index_payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": language,
        "dumperLanguage": language_info["dumper"],
        "format": args.format,
        "block": args.block,
        "audioDialogTable": normalize_posix(audio_dialog_path.relative_to(ROOT))
        if audio_dialog_path.is_relative_to(ROOT)
        else str(audio_dialog_path),
        "counts": {
            "files": len(generic_audio),
            "dialogAudio": len(dialog_audio),
            "eventNames": len(event_names),
            "eventAudio": len(event_entries),
            "eventEvidence": len(event_evidence),
            **link_stats,
        },
        "eventNames": sorted(event_names),
        "eventEvidence": event_evidence,
        "events": sorted(event_entries, key=lambda item: (str(item.get("eventId") or ""), int(item.get("mediaId") or 0))),
        "entries": sorted(audio_by_id.values(), key=lambda item: (str(item.get("id") or ""), str(item.get("rel") or ""))),
    }
    json_dump(language_root / "index.json", index_payload)

    elapsed = time.time() - started
    print(
        "Audio index:"
        f" {len(generic_audio):,} files,"
        f" {len(dialog_audio):,} AudioDialog matches,"
        f" {len(event_entries):,} event media links,"
        f" {link_stats['lineAudioLinked']:,}/{link_stats['lineAudioRefs']:,} line refs linked,"
        f" {link_stats['conversationAudioEventsLinked']:,}/{link_stats['conversationAudioEvents']:,} conversation event refs linked,"
        f" {link_stats['cutsceneAudioEventsLinked']:,}/{link_stats['cutsceneAudioEvents']:,} cutscene event refs linked,"
        f" {link_stats['conversationFilesChanged']:,} conv files updated"
        f" in {elapsed:.1f}s"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=sorted(LANGUAGES), default="CN")
    parser.add_argument("--format", choices=("wav", "wem"), default="wav")
    parser.add_argument("--block", choices=("all", "voice", "audio", "initial-audio", "audit-audio"), default="all")
    parser.add_argument("--skip-decode", action="store_true", help="Only rebuild the audio index and story links.")
    parser.add_argument("--fluffy", type=Path, default=DEFAULT_FLUFFY)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--streaming-assets", type=Path, default=None)
    parser.add_argument("--fallback-assets", type=Path, default=None)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--webui-root", type=Path, default=DEFAULT_WEBUI_ROOT)
    parser.add_argument(
        "--audio-root",
        type=Path,
        default=None,
        help="Decoded audio root containing per-language folders. Default: <export-root>/structured/Audio.",
    )
    args = parser.parse_args(argv)
    if args.streaming_assets is None:
        args.streaming_assets = args.game_root / "StreamingAssets"
    if args.fallback_assets is None:
        args.fallback_assets = args.game_root / "Persistent"
    if args.audio_root is None:
        args.audio_root = args.export_root / "structured" / "Audio"
    return args


if __name__ == "__main__":
    raise SystemExit(build_audio(parse_args()))
