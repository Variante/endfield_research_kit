#!/usr/bin/env python3
"""Decode story audio into export_full and link playable files into WebUI data."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import wave
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from struct import unpack_from
from typing import Any

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.audio.build_audio"
    )

from scripts.common import resolve_installed_game_data_root, sha256_file as file_sha256
from scripts.webui.audio.semantics.identifiers import (
    audio_hash_generator_compute,
    collect_metadata_audio_literals,
    hashed_event_key,
    is_rtpc_parameter_name,
)
from scripts.webui.audio.semantics import name_recovery
from scripts.webui.audio.semantics.table_contexts import collect_table_audio_events
from scripts.webui.audio.semantics.event_projection import HIRC_OBJECT_TYPE_LABELS
from scripts.webui.audio.semantics.rtpc_contract import CANONICAL_RTPC_ENTRIES
from scripts.webui.audio.semantics.context_utils import SELECTION_HIRC_TYPES, json_dump, load_json_strict, normalize_posix, iter_asset_map_objects, display_path
from scripts.webui.audio.semantics.event_aliases import collect_audio_dialog_wwise_event_aliases, collect_skill_id_dictionary_wwise_event_aliases, collect_sns_voice_wwise_event_aliases, collect_typed_ui_table_wwise_event_aliases, collect_voice_table_wwise_event_aliases
from scripts.webui.audio.semantics.cutscene_audio import collect_fmv_cutscene_audio_events, collect_levelseq_cutscene_audio_events, collect_timeline_cutscene_audio_events, collect_video_binding_audio_containers, mono_behaviour_json_by_path_id, story_key_from_fmv_id, story_key_from_video_binding, strip_fmv_gender_prefix, timeline_audio_container_for
from scripts.webui.audio.semantics.projectile_audio import projectile_event_key, projectile_sound_hashes, projectile_sound_references, write_projectile_audio_sidecar
from scripts.webui.audio.semantics.gameplay_audio import animation_clip_action_kind, animation_clip_audio_events, animation_clip_context, animation_clip_path_id, animation_clip_reachability_status, animation_controller_contexts, animation_override_contexts, animation_override_reachability_status, animator_controller_state_clip_refs, animestudio_storage_root, annotate_play_sound_action_owner_links, collect_animation_controller_index, collect_animation_override_index, collect_buff_play_sound_actions, collect_gameplay_animation_audio, collect_gameplay_audio_references, collect_gameplay_profile_voices, compact_gameplay_audio_link, enemy_template_animation_tokens, enemy_template_skill_references, enemy_template_source_files, gameplay_buff_audio, gameplay_character_token_owners, gameplay_config_records, iter_json_strings, length_prefixed_matches, link_gameplay_audio, play_sound_action_marker, profile_voice_action_kind, seed_buff_play_sound_events
from scripts.webui.audio.semantics.hirc_v150 import HIRC_EFFECT_PARAMETER_CONTRACT, add_hirc_bus_definition_candidate, add_hirc_effect_definition_candidate, collect_hirc_decoded_sound_definitions, decode_hirc_v150_effect_parameters, finalize_hirc_post_process_catalog, hirc_action_target_id, hirc_action_type, hirc_bus_parent_path, hirc_event_action_ids, hirc_object_parent_id, hirc_reciprocal_child_list, hirc_v150_bus_processing, hirc_v150_control_action, hirc_v150_effect_definition, hirc_v150_empty_music_children, hirc_v150_layer_child_candidate, hirc_v150_layer_tail, hirc_v150_music_random_sequence_structure, hirc_v150_music_segment_structure, hirc_v150_music_structure, hirc_v150_music_switch_structure, hirc_v150_music_track, hirc_v150_node_processing, hirc_v150_playback_action, hirc_v150_random_sequence_properties, hirc_v150_sound_source, hirc_v150_switch_mapping, iter_bnk_sections, parse_hirc_objects, refine_hirc_v150_music_switch_selector_ownership, resolve_hirc_post_process_summary, summarize_hirc_action_dispatch, summarize_hirc_node_processing, summarize_hirc_object_types, traverse_hirc_event
from scripts.webui.audio.build_audio_semantics import build_audio_semantic_data
from scripts.game_data.extraction.animestudio_index_io import ObjectIndexUnavailable, iter_published_objects, raw_json_path_for_object


from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_ANIMESTUDIO = ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"
DEFAULT_AUDIO_DUMPER = DEFAULT_ANIMESTUDIO
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_WEBUI_ROOT = ROOT / "webui"
DEFAULT_AUDIO_ROOT = DEFAULT_EXPORT_ROOT / "structured" / "Audio"
LUA_AUDIO_REFERENCE_CACHE_REL = Path("recovered/audio/lua_audio_references.json")
LUA_AUDIO_REFERENCE_SCHEMA_VERSION = 1
LUA_AUDIO_NAME_RE = re.compile(r"(?i)\bau_[a-z0-9_]+")
LUA_FILE_REGEX = r"(?i)\.lua(?:\.enc)*$"
LUA_AUDIO_CALL_RE = re.compile(
    r"(?i)\b(?:AudioAdapter|AudioManager)\s*\.\s*"
    r"(?P<method>PostEvent|SetRtpc|PostAudioCue)\s*\("
)
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

AUDIO_EXTENSIONS = {".flac", ".wav", ".wem"}
AUDIO_EXTENSION_PRIORITY = {".flac": 0, ".wav": 1, ".wem": 2}
AUDIO_OUTPUT_FORMAT = "flac"
EVENT_CATEGORY_PREFIXES = {
    "au_sfx_": "au_sfx",
    "au_vo_": "au_vo",
    "au_voice_": "au_vo",
    "au_music_": "au_music",
    "au_cue_": "au_cue",
    "au_amb_": "au_amb",
    "au_ui_": "au_ui",
}
EVENT_PREFIXES = tuple(EVENT_CATEGORY_PREFIXES)
WWISE_EVENT_CATEGORY_FOLDERS = {
    "au_sfx": "sfx",
    "au_vo": "voice_events",
    "au_music": "music",
    "au_cue": "cues",
    "au_amb": "ambience",
    "au_ui": "ui",
}
WWISE_EVENT_CATEGORY_BY_FOLDER = {
    folder: category
    for category, folder in WWISE_EVENT_CATEGORY_FOLDERS.items()
}
WWISE_UNKNOWN_FOLDER = "unknown"
SHARED_AUDIO_BLOCKS = ("audio", "initial-audio", "audit-audio")
OPTIONAL_SHARED_AUDIO_BLOCKS = ("hotfix-audio",)
SHARED_AUDIO_STORAGE_BLOCKS = (*SHARED_AUDIO_BLOCKS, *OPTIONAL_SHARED_AUDIO_BLOCKS)
EVENT_BANK_VFS_BLOCK_TYPES = (
    "audio",
    "initial-audio",
    "audit-audio",
    "hotfix-audio",
    "audio-chinese",
    "audio-english",
    "audio-japanese",
    "audio-korean",
)
EVENT_BANK_FILE_REGEX = r"(^|[\\/])(?:[^\\/]*banks|hotfix[^\\/]*)\.pck$"
EVENT_EVIDENCE_SCHEMA_VERSION = 43
HASHED_EVENT_KEY_RE = re.compile(r"^hashed-event:0x([0-9a-f]{8})$", re.IGNORECASE)

# Wwise 2024.1 / bank version 150 HIRC action operations.  The serialized
# value is a little-endian U16 whose high byte is the operation and low byte is
# the action scope.  Only Play and PlayEvent introduce downward playback
# edges; Stop and the other control actions must not be followed as media.
# A small set of GameParameter names recovered from the installed client's
# IL2CPP metadata and cross-matched against serialized HIRC RTPC IDs.  Keep
# these separate from Wwise property labels: these are game-side parameter
# symbols, not DSP/property names.  The metadata hash pins this catalog to the
# audited client build; an absent HIRC match is intentionally not invented.
HIRC_GAME_PARAMETER_NAME_EVIDENCE = {
    "source": "il2cpp_data/Metadata/global-metadata.dat",
    "metadataSha256": (
        "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
    ),
    "evidence": "exactStaticFieldValueCrossMatchedToSerializedHircRtpcId",
    "entries": CANONICAL_RTPC_ENTRIES,
    "evidenceBoundary": (
        "The six field names and 32-bit values are exact for the pinned metadata "
        "file and each value is present in the exported HIRC RTPC inventory. "
        "This catalog does not name Wwise property IDs 6146/6148, and it does "
        "not infer runtime setter order, live values, or audibility."
    ),
}
# v150 InitialParams uses AkPropID, whose numbering is distinct from the
# RTPC/state parameter IDs above.  Keep this table separate so authored base
# values are not mislabeled as runtime RTPC targets.

# Encoded Wwise plug-in class IDs use the low nibble for AkPluginType, the
# following 12 bits for company ID, and the high 16 bits for plug-in ID.  The
# built-in effect names below are pinned by the registration records and
# factory source paths embedded in the shipped AkSoundEngine.dll.  Unknown or
# third-party IDs remain numeric instead of being guessed from parameter size.

# Exact current-client SetParamsBlock contracts for the effect payloads below.
# The RVAs are recorded against the shipped AkSoundEngine.dll SHA-256 and are
# evidence for field order/type, not code that is invoked by the builder.
# Every decoder also requires the exact serialized size and rejects non-finite
# floats or invalid booleans/enums.  Raw payload hashes remain available even
# when a later or unsupported plug-in schema stays opaque.

LANGUAGE_AUDIO_BLOCKS = ("voice",)
SHARED_AUDIO_STORAGE = "shared"
SHARED_AUDIO_LANGUAGE = "CN"
SPLIT_AUDIO_BLOCKS = (*SHARED_AUDIO_BLOCKS, *LANGUAGE_AUDIO_BLOCKS)
SHARED_AUDIO_BLOCK_LABELS = {
    "audio": "Audio",
    "initial-audio": "InitAudio",
    "audit-audio": "AuditAudio",
    "hotfix-audio": "HotfixAudio",
}
AUDIO_META_KEYS = (
    "audioDialogKey",
    "audioDialogPath",
    "audioDialogSource",
    "speakerChannel",
    "voType",
    "duration",
    "format",
    "bytes",
    "audioScope",
    "sourceBlock",
    "sourceBlockLabel",
    "sourceLanguage",
    "storageRoot",
    "sourceBank",
    "eventCategory",
    "audioCategory",
    "audioCategoryDetail",
)




def audio_rel_with_extension(rel: str | Path, extension: str) -> str:
    suffix = str(extension or "").strip().lower()
    if suffix and not suffix.startswith("."):
        suffix = "." + suffix
    path = PurePosixPath(normalize_posix(rel))
    return normalize_posix(path.with_suffix(suffix)) if suffix else normalize_posix(path)


AUDIO_STAGE_TIMINGS: list[tuple[str, float]] = []


class AudioStageTimer:
    """Time each ``build_audio`` stage and report it on stderr.

    The pipeline report records only the total for the whole task, so the
    per-stage wall times are the only evidence available for deciding where
    the time goes.  They are written to stderr so the existing stdout summary
    lines stay machine-parsable.
    """

    def __init__(self) -> None:
        self.last = time.perf_counter()

    def mark(self, label: str) -> None:
        now = time.perf_counter()
        elapsed = now - self.last
        self.last = now
        AUDIO_STAGE_TIMINGS.append((label, elapsed))
        print(f"Audio stage [{label}]: {elapsed:.2f}s", file=sys.stderr, flush=True)


def print_audio_stage_summary() -> None:
    if not AUDIO_STAGE_TIMINGS:
        return
    width = max(len(label) for label, _ in AUDIO_STAGE_TIMINGS)
    total = sum(seconds for _, seconds in AUDIO_STAGE_TIMINGS)
    print("Audio stage summary (wall seconds):", file=sys.stderr)
    for label, seconds in sorted(AUDIO_STAGE_TIMINGS, key=lambda row: -row[1]):
        share = (seconds / total * 100.0) if total else 0.0
        print(f"  {label.ljust(width)}  {seconds:9.2f}  {share:5.1f}%", file=sys.stderr)
    print(f"  {'TOTAL'.ljust(width)}  {total:9.2f}  100.0%", file=sys.stderr, flush=True)












































































def normalize_video_override_stem(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    text = text.rsplit("/", 1)[-1]
    return re.sub(r"\.[^.]+$", "", text, flags=re.IGNORECASE).lower()


def load_narrative_video_attach_overrides(webui_root: Path) -> dict[str, str]:
    """Return `{video_stem: target_story_key}` for manual inline video attachments."""
    path = webui_root / "overrides" / NARRATIVE_VIDEO_OVERRIDES_NAME
    payload = load_json_strict(path, {})
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


def _normalize_story_key(value: object) -> str:
    return str(value or "").strip()


def _listish_values(value: object) -> list[object]:
    if isinstance(value, (str, int, float)):
        return [value]
    if isinstance(value, list):
        return value
    return []


def load_narrative_video_audio_source_overrides(webui_root: Path) -> dict[str, list[str]]:
    """Return `{target_story_key: [source_cutscene_key]}` audio inheritance rules."""
    path = webui_root / "overrides" / NARRATIVE_VIDEO_OVERRIDES_NAME
    payload = load_json_strict(path, {})
    if not isinstance(payload, dict):
        return {}

    raw_rules = payload.get("attachInline") or payload.get("attachTo")
    out: dict[str, list[str]] = {}

    def add_rule(target_key: object, raw_rule: object) -> None:
        key = _normalize_story_key(target_key)
        if not key or not isinstance(raw_rule, dict):
            return
        raw_sources = (
            raw_rule.get("audioFrom")
            or raw_rule.get("audioSourceKeys")
            or raw_rule.get("audioSources")
            or raw_rule.get("audioSourceKey")
            or raw_rule.get("inheritAudioFrom")
            or raw_rule.get("copyAudioFrom")
            or []
        )
        normalized_sources: list[str] = []
        seen = {
            source.lower()
            for source in out.get(key, [])
        }
        for raw_source in _listish_values(raw_sources):
            source = _normalize_story_key(raw_source)
            source_key = source.lower()
            if source and source_key not in seen:
                seen.add(source_key)
                normalized_sources.append(source)
        if normalized_sources:
            out.setdefault(key, []).extend(normalized_sources)

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


def find_audio_dialog_tables(export_root: Path) -> list[Path]:
    candidates = [
        export_root / "structured" / "StreamingAssets" / "Table" / "AudioDialog.json",
        export_root / "structured" / "Persistent" / "Table" / "AudioDialog.json",
    ]
    paths = [candidate for candidate in candidates if candidate.exists()]
    if paths:
        return paths
    raise SystemExit(
        "AudioDialog.json not found under export_full/structured. "
        "Run export.bat first, or pass --export-root."
    )






def lua_audio_source_fingerprints(args: argparse.Namespace) -> list[dict[str, Any]]:
    rows = []
    for source, root in (
        ("Persistent", args.fallback_assets),
        ("StreamingAssets", args.streaming_assets),
    ):
        if root is None:
            continue
        path = root / "index_main.json"
        if not path.is_file():
            continue
        rows.append({
            "source": source,
            "path": display_path(path),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        })
    return rows


def collect_lua_audio_references(
    lua_root: Path,
    source_root: str = "",
    include_rel_paths: set[str] | None = None,
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    if not lua_root.exists():
        return references
    for path in sorted(lua_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".lua":
            continue
        rel_source = normalize_posix(path.relative_to(lua_root))
        if include_rel_paths is not None and rel_source not in include_rel_paths:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        source = (
            normalize_posix(PurePosixPath("structured", source_root, "Lua", rel_source))
            if source_root
            else rel_source
        )
        for line_number, line in enumerate(text.splitlines(), 1):
            names = list(LUA_AUDIO_NAME_RE.finditer(line))
            if not names:
                continue
            call = LUA_AUDIO_CALL_RE.search(line)
            method = call.group("method") if call else "Literal"
            kind = {
                "postevent": "luaPostEvent",
                "setrtpc": "luaRtpcParameter",
                "postaudiocue": "luaAudioCue",
            }.get(method.lower(), "luaAudioLiteral")
            for match in names:
                name = match.group(0).lower().rstrip("_")
                row = {
                    "kind": kind,
                    "name": name,
                    "hash": fnv1_32(name),
                    "hashHex": f"0x{fnv1_32(name):08x}",
                    "method": method,
                    "source": source,
                    "line": line_number,
                    "expression": line.strip()[:500],
                    "evidence": (
                        "exactLuaAudioCallLiteral"
                        if call
                        else "luaAudioLiteralWithoutDirectCallProof"
                    ),
                }
                references.append(row)
    return references


def summarize_lua_audio_references(references: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind = Counter(str(row.get("kind") or "unknown") for row in references)
    names_by_kind: dict[str, set[str]] = defaultdict(set)
    for row in references:
        names_by_kind[str(row.get("kind") or "unknown")].add(str(row.get("name") or ""))
    return {
        "references": len(references),
        "sourceFiles": len({str(row.get("source") or "") for row in references}),
        "byKind": dict(sorted(by_kind.items())),
        "uniqueNamesByKind": {
            kind: len(names)
            for kind, names in sorted(names_by_kind.items())
        },
    }


def refresh_lua_audio_reference_cache(args: argparse.Namespace) -> dict[str, Any]:
    if not args.audio_dumper.is_file():
        raise SystemExit(f"audio dumper not found for Lua audio refresh: {args.audio_dumper}")
    with tempfile.TemporaryDirectory(prefix="endfield_audio_lua_") as raw_temp:
        temp_root = Path(raw_temp)
        outputs: dict[str, Path] = {}
        for source_root, primary, fallback in (
            ("StreamingAssets", args.streaming_assets, args.fallback_assets),
            ("Persistent", args.fallback_assets, args.streaming_assets),
        ):
            if primary is None or not primary.exists():
                continue
            output = temp_root / source_root
            command = [
                str(args.audio_dumper),
                "dump",
                "--streaming-assets",
                str(primary),
                "--output",
                str(output),
                "--block-type",
                "lua",
                "--file-regex",
                LUA_FILE_REGEX,
            ]
            if fallback and fallback.exists():
                command.extend(["--fallback-assets", str(fallback)])
            print(f"Running [{source_root} Lua audio references]:", " ".join(
                f'"{part}"' if " " in part else part for part in command
            ))
            subprocess.run(command, cwd=ROOT, check=True)
            outputs[source_root] = output / "Lua"

        selected_source_by_rel: dict[str, str] = {}
        for source_root in ("StreamingAssets", "Persistent"):
            lua_root = outputs.get(source_root)
            if lua_root is None:
                continue
            for path in lua_root.rglob("*.lua"):
                selected_source_by_rel[normalize_posix(path.relative_to(lua_root))] = source_root
        references = []
        for source_root, lua_root in outputs.items():
            include = {
                rel for rel, selected_source in selected_source_by_rel.items()
                if selected_source == source_root
            }
            references.extend(collect_lua_audio_references(lua_root, source_root, include))
    payload = {
        "schemaVersion": LUA_AUDIO_REFERENCE_SCHEMA_VERSION,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sourceFingerprints": lua_audio_source_fingerprints(args),
        "summary": summarize_lua_audio_references(references),
        "references": references,
        "evidenceBoundary": (
            "Exact decrypted Lua string literals and callsite lines; they do not prove that the Lua branch ran. "
            "Only luaPostEvent rows are promoted to Wwise Event-name candidates."
        ),
    }
    cache_path = args.export_root / LUA_AUDIO_REFERENCE_CACHE_REL
    json_dump(cache_path, payload)
    print(
        "Lua audio references:"
        f" {payload['summary']['references']:,} occurrences from"
        f" {payload['summary']['sourceFiles']:,} files"
    )
    return payload


def load_lua_audio_reference_cache(
    args: argparse.Namespace,
    *,
    refresh: bool = False,
) -> dict[str, Any]:
    if refresh:
        return refresh_lua_audio_reference_cache(args)
    cache_path = args.export_root / LUA_AUDIO_REFERENCE_CACHE_REL
    payload = load_json_strict(cache_path, {})
    if not isinstance(payload, dict) or int(payload.get("schemaVersion") or 0) != LUA_AUDIO_REFERENCE_SCHEMA_VERSION:
        return {}
    current = lua_audio_source_fingerprints(args)
    cached = payload.get("sourceFingerprints") or []
    if current and cached != current:
        print(
            "Lua audio references: cached installed-source fingerprints are stale; "
            "rerun without --skip-decode or pass --refresh-lua-audio"
        )
        return {}
    return payload


def same_resolved_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def audio_vfs_sources(args: argparse.Namespace) -> list[tuple[str, Path, Path | None]]:
    """Return the fallback-aware installed VFS source used for audio work.

    Endfield installs can keep patch/update tables and PCKs under Persistent.
    AnimeStudio resolves missing block metadata and chunks through the fallback.
    Running the roots again in reverse decodes the same logical PCK set twice on
    current installs, so audio extraction and bank streaming use one primary
    source with Persistent configured as its fallback.
    """
    primary = args.streaming_assets
    fallback = args.fallback_assets if args.fallback_assets and args.fallback_assets.exists() else None
    return [("StreamingAssets", primary, fallback)]


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


def decrypt_akpk_bytes(raw_data: bytes, label: str) -> bytes:
    data = bytearray(raw_data)
    if data[:4] == b":)xD":
        header_size = int.from_bytes(data[4:8], "little")
        decrypt_vfs_bytes(data, 12, header_size - 4, header_size)
        data[:4] = b"AKPK"
        data[8:12] = (1).to_bytes(4, "little")
    if data[:4] != b"AKPK":
        raise ValueError(f"invalid AKPK magic: {label}")
    return bytes(data)


def iter_akpk_bank_payloads_from_bytes(raw_data: bytes, label: str) -> list[tuple[int, bytes]]:
    data = decrypt_akpk_bytes(raw_data, label)
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


def iter_akpk_media_ids_from_bytes(raw_data: bytes, label: str) -> list[int]:
    """Every WEM media id in an AKPK package (banks DIDX + sounds + externals sectors)."""
    data = decrypt_akpk_bytes(raw_data, label)
    ids: list[int] = []
    if len(data) < 28:
        return ids
    header_size = unpack_from("<I", data, 4)[0]
    language_size = unpack_from("<I", data, 12)[0]
    banks_size = unpack_from("<I", data, 16)[0]
    sounds_size = unpack_from("<I", data, 20)[0]
    has_externals = language_size + banks_size + sounds_size + 0x10 < header_size
    externals_size = unpack_from("<I", data, 24)[0] if has_externals else 0
    pos = (28 if has_externals else 24) + language_size

    def parse_bnk(offset: int, size: int) -> None:
        if size < 8 or offset + size > len(data) or data[offset : offset + 4] != b"BKHD":
            return
        bkhd = unpack_from("<I", data, offset + 4)[0]
        p = offset + 8 + bkhd
        end = offset + size
        if p + 8 > end or data[p : p + 4] != b"DIDX":
            return
        didx = unpack_from("<I", data, p + 4)[0]
        p += 8
        for _ in range(didx // 12):
            if p + 12 > end:
                return
            ids.append(unpack_from("<I", data, p)[0])
            p += 12

    def parse_sector(start: int, sector_size: int, is_sounds: bool, is_externals: bool) -> None:
        if sector_size == 0 or start + 4 > len(data):
            return
        count = unpack_from("<I", data, start)[0]
        if count == 0:
            return
        entry_size = (sector_size - 4) // count
        alt = entry_size == 0x18
        p = start + 4
        for _ in range(count):
            if p + entry_size > len(data):
                break
            file_id_low = unpack_from("<I", data, p)[0]
            q = p + 4
            file_id_high: int | None = None
            if alt and is_externals:
                file_id_high = unpack_from("<I", data, q)[0]
                q += 4
            block_size = unpack_from("<I", data, q)[0]
            q += 4
            if alt and is_externals:
                size = unpack_from("<I", data, q)[0]
                q += 4
            elif alt:
                size = unpack_from("<Q", data, q)[0]
                q += 8
            else:
                size = unpack_from("<I", data, q)[0]
                q += 4
            offset = unpack_from("<I", data, q)[0]
            if block_size:
                offset *= block_size
            if is_sounds:
                ids.append((file_id_high << 32) | file_id_low if file_id_high is not None else file_id_low)
            else:
                parse_bnk(offset, size)
            p += entry_size

    parse_sector(pos, banks_size, False, False)
    pos += banks_size
    parse_sector(pos, sounds_size, True, False)
    pos += sounds_size
    if externals_size:
        parse_sector(pos, externals_size, True, True)
    return ids






















































































































VOICE_BATCH_PREFIX_REGEX = re.compile(r"^v\d+d\d+/", re.IGNORECASE)


def strip_voice_batch_prefix(path: str) -> str:
    """Drop a leading v<major>d<minor> batch folder (e.g. v1d0..v1d3) when present."""
    return VOICE_BATCH_PREFIX_REGEX.sub("", path, count=1)


def story_voice_group_for_bucket(bucket: str) -> str:
    normalized = str(bucket or "").strip().lower()
    if normalized.startswith("episode_"):
        return "main_episodes"
    if normalized.startswith("hs_part"):
        return "hongshan"
    if normalized == "submission":
        return "side_missions"
    if normalized == "subchar":
        return "character_stories"
    if normalized == "subfac":
        return "facility_base"
    if normalized == "commonextra":
        return "common_extras"
    if normalized == "fragment":
        return "fragments_archives"
    return "other"


def canonical_voice_rel(rel: str) -> str:
    normalized = normalize_posix(rel).lower()
    parts = PurePosixPath(normalized).parts
    if not parts or parts[0] != "voice":
        return normalized
    if len(parts) == 1:
        return normalized
    section = parts[1]
    if section in {"story", "characters", "enemies", "other"}:
        return normalized
    if section == "narrating":
        bucket = parts[2] if len(parts) >= 3 else "unknown"
        return normalize_posix(PurePosixPath("voice", "story", story_voice_group_for_bucket(bucket), *parts[2:]))
    if section == "enemy":
        return normalize_posix(PurePosixPath("voice", "enemies", *parts[2:]))
    if section == "characters":
        return normalized
    return normalize_posix(PurePosixPath("voice", "other", *parts[1:]))


def wwise_folder_for_event_category(event_category: Any) -> str:
    category = str(event_category or "").strip().lower().rstrip("_")
    return WWISE_EVENT_CATEGORY_FOLDERS.get(category, WWISE_UNKNOWN_FOLDER)


def event_category_for_wwise_folder(folder: str) -> str:
    return WWISE_EVENT_CATEGORY_BY_FOLDER.get(str(folder or "").strip().lower(), "")


def audio_path_tags_for_rel(rel: str) -> dict[str, str]:
    normalized = normalize_posix(rel).lower()
    parts = PurePosixPath(normalized).parts
    tags: dict[str, str] = {}
    if not parts:
        return tags
    if parts[0] == "unmapped":
        if len(parts) >= 3:
            tags["sourceBank"] = parts[1]
        if len(parts) >= 4 and parts[2] in WWISE_EVENT_CATEGORY_FOLDERS:
            tags["eventCategory"] = parts[2]
    elif parts[0] == "wwise" and len(parts) >= 2:
        category = event_category_for_wwise_folder(parts[1])
        if category:
            tags["eventCategory"] = category
    return tags


def audio_category_for_rel(rel: str, event_category: Any = None) -> tuple[str, str]:
    """Return a stable browser category plus an optional useful subcategory."""
    parts = PurePosixPath(normalize_posix(rel).lower()).parts
    if not parts:
        return "unknown", ""
    if parts[0] == "voice":
        section = parts[1] if len(parts) >= 2 else "other"
        if section == "story":
            return "story_voice", parts[2] if len(parts) >= 3 else "other"
        if section == "characters":
            return "character_voice", parts[2] if len(parts) >= 3 else ""
        if section == "enemies":
            return "enemy_voice", parts[2] if len(parts) >= 3 else ""
        return "other_voice", section
    if parts[0] == "wwise":
        folder = wwise_folder_for_event_category(event_category) if event_category else (
            parts[1] if len(parts) >= 2 else WWISE_UNKNOWN_FOLDER
        )
        return folder if folder in WWISE_EVENT_CATEGORY_BY_FOLDER or folder == WWISE_UNKNOWN_FOLDER else "unknown", ""
    return "unknown", parts[0]


def apply_audio_category(entry: dict[str, Any]) -> None:
    category, detail = audio_category_for_rel(
        str(entry.get("rel") or ""),
        entry.get("eventCategory"),
    )
    entry["audioCategory"] = category
    if detail:
        entry["audioCategoryDetail"] = detail
    else:
        entry.pop("audioCategoryDetail", None)


def canonical_audio_rel(rel: str, event_category: Any = None) -> str:
    normalized = normalize_posix(rel).lower()
    parts = PurePosixPath(normalized).parts
    if not parts:
        return normalized
    if parts[0] == "voice":
        return canonical_voice_rel(normalized)
    if parts[0] == "unmapped":
        file_name = parts[-1] if len(parts) >= 2 else ""
        path_category = parts[2] if len(parts) >= 4 and parts[2] in WWISE_EVENT_CATEGORY_FOLDERS else ""
        category_folder = wwise_folder_for_event_category(event_category or path_category)
        return normalize_posix(PurePosixPath("wwise", category_folder, file_name)) if file_name else normalize_posix(PurePosixPath("wwise", category_folder))
    if parts[0] == "wwise":
        if len(parts) == 1:
            return normalized
        folder = wwise_folder_for_event_category(event_category) if event_category else WWISE_EVENT_CATEGORY_FOLDERS.get(parts[1], parts[1])
        return normalize_posix(PurePosixPath("wwise", folder, *parts[2:]))
    return normalized


def audio_rel_for_dialog_path(dialog_path: str, extension: str) -> str:
    # The language is encoded in the per-language output root, so the rel path drops
    # the language segment; the leading v1dN batch folder is merged away to match the
    # decoded layout before the exporter folds it into the browser-facing voice tree.
    path = dialog_path.replace("\\", "/")
    path = audio_rel_with_extension(path, extension)
    return canonical_audio_rel(
        normalize_posix(Path("voice") / strip_voice_batch_prefix(path.lower()))
    )


def audio_dialog_external_media_id(dialog_path: str, dumper_language: str) -> int:
    """Return the AKPK externals-sector id for an authored voice path."""

    value = f"voice/{dumper_language}/{dialog_path}".replace("\\", "/").lower()
    result = 0xCBF29CE484222325
    for byte in value.encode("utf-8"):
        result = (result * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        result ^= byte
    return result


def storage_root_for_block(block: str, language: str) -> str:
    if block in SHARED_AUDIO_STORAGE_BLOCKS:
        return SHARED_AUDIO_STORAGE
    return language


def audio_file_path(audio_root: Path, storage_root: str, relative_audio_path: str) -> Path:
    return audio_root / storage_root / Path(*PurePosixPath(relative_audio_path).parts)


def served_audio_href(audio_root: Path, webui_root: Path, storage_root: str, relative_audio_path: str) -> str:
    audio_path = audio_file_path(audio_root, storage_root, relative_audio_path)
    if audio_path.is_relative_to(webui_root):
        return normalize_posix(audio_path.relative_to(webui_root))
    if audio_path.is_relative_to(ROOT):
        return "/" + normalize_posix(audio_path.relative_to(ROOT))
    raise SystemExit(
        "Audio root must be under the WebUI root or project root so generated "
        f"audioSrc links are servable: {audio_root}"
    )


def entry_storage_root(entry: dict[str, Any], language: str) -> str:
    storage = str(entry.get("storageRoot") or "").strip()
    if storage:
        return storage
    if str(entry.get("audioScope") or "").strip().lower() == "shared":
        return SHARED_AUDIO_STORAGE
    return language


def entry_audio_path(audio_root: Path, language: str, entry: dict[str, Any]) -> Path:
    rel = str(entry.get("rel") or "").strip()
    if not rel:
        return Path()
    return audio_file_path(audio_root, entry_storage_root(entry, language), rel)


def has_decoded_audio_in_roots(*roots: Path) -> bool:
    return any(has_decoded_audio(root) for root in roots)

def selected_audio_blocks(block_mode: str) -> tuple[str, ...]:
    if block_mode == "all":
        return (*SPLIT_AUDIO_BLOCKS, *OPTIONAL_SHARED_AUDIO_BLOCKS)
    return (block_mode,)


def source_scope_for_block(block: str) -> str:
    if block in SHARED_AUDIO_STORAGE_BLOCKS:
        return "shared"
    if block in LANGUAGE_AUDIO_BLOCKS:
        return "language"
    return "unknown"


def source_label_for_block(block: str, language_info: dict[str, str]) -> str:
    if block in SHARED_AUDIO_BLOCK_LABELS:
        return SHARED_AUDIO_BLOCK_LABELS[block]
    if block == "voice":
        return f"Audio{language_info['label']}"
    return block


def audio_source_metadata(block: str, language: str, language_info: dict[str, str]) -> dict[str, str]:
    metadata = {
        "audioScope": source_scope_for_block(block),
        "sourceBlock": block,
        "sourceBlockLabel": source_label_for_block(block, language_info),
    }
    if metadata["audioScope"] == "language":
        metadata["sourceLanguage"] = language
    return metadata


def combined_decode_source_block(storage_root: str, language: str, rel: str) -> str:
    if storage_root == language:
        return "voice"
    source_bank = audio_path_tags_for_rel(rel).get("sourceBank")
    return {
        "initial": "initial-audio",
        "audit": "audit-audio",
        "hotfix": "hotfix-audio",
    }.get(source_bank, "audio")


def legacy_audio_source_metadata(rel: str, language: str, language_info: dict[str, str]) -> dict[str, str]:
    normalized = normalize_posix(rel).lower()
    if normalized.startswith("voice/"):
        return audio_source_metadata("voice", language, language_info)
    if normalized.startswith("wwise/"):
        return audio_source_metadata("voice", language, language_info)
    if normalized.startswith("unmapped/"):
        return {
            "audioScope": "unknown",
            "sourceBlock": "legacy-all",
            "sourceBlockLabel": "LegacyAllAudio",
        }
    return {
        "audioScope": "unknown",
        "sourceBlock": "unknown",
        "sourceBlockLabel": "Unknown",
    }


def clean_source_metadata(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, str] = {}
    for key in (
        "audioScope",
        "sourceBlock",
        "sourceBlockLabel",
        "sourceLanguage",
        "storageRoot",
        "sourceBank",
        "eventCategory",
        "audioCategory",
        "audioCategoryDetail",
    ):
        text = str(value.get(key) or "").strip()
        if text:
            out[key] = text
    return out


def existing_shared_audio_metadata() -> dict[str, str]:
    return {
        "audioScope": "shared",
        "sourceBlock": "shared-existing",
        "sourceBlockLabel": "SharedAudio",
        "storageRoot": SHARED_AUDIO_STORAGE,
    }


def prior_source_metadata_by_rel(
    language_root: Path,
    language: str,
) -> dict[tuple[str, str], dict[str, str]]:
    payload = load_json_strict(language_root / "index.json", {})
    if not isinstance(payload, dict):
        return {}
    out: dict[tuple[str, str], dict[str, str]] = {}
    for collection_name in ("entries", "events"):
        for entry in payload.get(collection_name) or []:
            if not isinstance(entry, dict):
                continue
            rel = normalize_posix(str(entry.get("rel") or "").strip())
            if not rel:
                continue
            storage_root = entry_storage_root(entry, language)
            key = (storage_root, rel)
            if key in out:
                continue
            metadata = clean_source_metadata(entry)
            if metadata:
                metadata.setdefault("storageRoot", storage_root)
                out[key] = metadata
    return out


def merge_source_metadata_by_rel(
    target: dict[tuple[str, str], dict[str, str]],
    updates: dict[tuple[str, str], dict[str, str]],
) -> None:
    for key, metadata in updates.items():
        current = target.setdefault(key, {})
        for meta_key, value in clean_source_metadata(metadata).items():
            current.setdefault(meta_key, value)


def canonicalized_source_metadata_by_rel(
    source_by_rel: dict[tuple[str, str], dict[str, str]],
) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for (storage_root, rel), metadata in source_by_rel.items():
        normalized = normalize_posix(rel)
        enriched = clean_source_metadata(metadata)
        enriched.setdefault("storageRoot", storage_root)
        for key, value in audio_path_tags_for_rel(normalized).items():
            enriched.setdefault(key, value)
        canonical_rel = canonical_audio_rel(normalized, enriched.get("eventCategory"))
        out[(storage_root, normalized)] = dict(enriched)
        out.setdefault((storage_root, canonical_rel), dict(enriched))
    return out


def source_metadata_for_rel(
    storage_root: str,
    rel: str,
    language: str,
    language_info: dict[str, str],
    decoded_source_by_rel: dict[tuple[str, str], dict[str, str]],
    prior_source_by_rel: dict[tuple[str, str], dict[str, str]],
) -> dict[str, str]:
    normalized = normalize_posix(rel)
    key = (storage_root, normalized)
    metadata = (
        clean_source_metadata(decoded_source_by_rel.get(key))
        or clean_source_metadata(prior_source_by_rel.get(key))
    )
    if metadata:
        metadata.setdefault("storageRoot", storage_root)
        return metadata
    if storage_root == SHARED_AUDIO_STORAGE:
        return existing_shared_audio_metadata()
    metadata = legacy_audio_source_metadata(normalized, language, language_info)
    metadata.setdefault("storageRoot", storage_root)
    return metadata

def summarize_audio_sources(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_scope: dict[str, int] = defaultdict(int)
    by_block: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    for entry in entries:
        scope = str(entry.get("audioScope") or "unknown")
        block = str(entry.get("sourceBlock") or "unknown")
        by_scope[scope] += 1
        by_block[block] += 1
        by_category[str(entry.get("audioCategory") or "unknown")] += 1
    return {
        "byScope": dict(sorted(by_scope.items())),
        "bySourceBlock": dict(sorted(by_block.items())),
        "byCategory": dict(sorted(by_category.items())),
    }


def backfill_event_source_metadata(
    event_entries: list[dict[str, Any]],
    audio_by_id: dict[str, dict[str, Any]],
    audio_by_rel: dict[tuple[str, str], dict[str, Any]],
    language: str,
) -> None:
    for entry in event_entries:
        if any(str(entry.get(key) or "").strip() for key in ("audioScope", "sourceBlock", "sourceBlockLabel")):
            continue
        source_entry = None
        media_id = entry.get("mediaId")
        if media_id is not None:
            source_entry = audio_by_id.get(str(media_id).lower())
        if source_entry is None:
            rel = normalize_posix(str(entry.get("rel") or "").strip())
            storage_root = entry_storage_root(entry, language)
            source_entry = audio_by_rel.get((storage_root, rel)) or audio_by_rel.get((SHARED_AUDIO_STORAGE, rel))
        metadata = clean_source_metadata(source_entry)
        if not metadata:
            continue
        entry.update(metadata)


def scan_audio_files(language_root: Path) -> list[tuple[Path, str, os.stat_result]]:
    """Return ``(path, rel, stat)`` for every decoded media under ``language_root``.

    ``Path.rglob("*")`` pays one extra ``stat`` syscall per entry for
    ``is_file()`` and every caller then stats the file again for its size.
    ``os.scandir`` carries both in the directory entry it already read, so
    reusing it removes roughly two syscalls per file — about 190k of them per
    walk over the ~93k decoded media.  The ordering is the one the published
    index depends on and is reproduced exactly.
    """

    if not language_root.exists():
        return []
    prefix_length = len(str(language_root)) + 1
    rows: list[tuple[Path, str, os.stat_result]] = []
    stack: list[str] = [str(language_root)]
    while stack:
        with os.scandir(stack.pop()) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                if os.path.splitext(entry.name)[1].lower() not in AUDIO_EXTENSIONS:
                    continue
                rows.append(
                    (
                        Path(entry.path),
                        normalize_posix(entry.path[prefix_length:]),
                        entry.stat(),
                    )
                )
    rows.sort(
        key=lambda row: (
            row[1].rsplit(".", 1)[0].lower(),
            AUDIO_EXTENSION_PRIORITY.get(row[0].suffix.lower(), 99),
            row[1].lower(),
        )
    )
    return rows


def iter_audio_files(language_root: Path) -> list[Path]:
    return [path for path, _rel, _stat in scan_audio_files(language_root)]


def has_decoded_audio(language_root: Path) -> bool:
    if not language_root.exists():
        return False
    stack: list[str] = [str(language_root)]
    while stack:
        with os.scandir(stack.pop()) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif (
                    os.path.splitext(entry.name)[1].lower() in AUDIO_EXTENSIONS
                    and entry.is_file()
                ):
                    return True
    return False


def audio_file_metrics(path: Path, file_size: int | None = None) -> dict[str, Any]:
    """Read bounded container metadata used by the WebUI media inventory."""
    duration = 0.0
    try:
        suffix = path.suffix.lower()
        if suffix == ".flac":
            with path.open("rb") as handle:
                header = handle.read(42)
            if (
                len(header) >= 42
                and header[:4] == b"fLaC"
                and header[4] & 0x7F == 0
                and int.from_bytes(header[5:8], "big") >= 34
            ):
                packed = int.from_bytes(header[18:26], "big")
                sample_rate = (packed >> 44) & 0xFFFFF
                total_samples = packed & ((1 << 36) - 1)
                if sample_rate and total_samples:
                    duration = total_samples / sample_rate
        elif suffix == ".wav":
            with wave.open(str(path), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()
                if sample_rate and frame_count:
                    duration = frame_count / sample_rate
    except (EOFError, OSError, ValueError, wave.Error):
        return {}
    if not duration or not isinstance(duration, (int, float)):
        return {}
    size = int(file_size if file_size is not None else path.stat().st_size)
    return {
        "duration": round(float(duration), 6),
        "bitrate": round(size * 8 / duration) if size > 0 else 0,
    }


def audio_file_metrics_bulk(
    rows: list[tuple[Path, str, os.stat_result]],
) -> list[dict[str, Any]]:
    """Read the container header of every row, overlapping the file opens.

    Each call reads 42 bytes from a different file, so the ~93k decoded media
    cost one storage round trip each and the walk is latency bound, not CPU
    bound.  ``ThreadPoolExecutor.map`` keeps the results in row order, so the
    produced index is identical to the serial read.
    """

    if not rows:
        return []
    workers = min(16, max(1, (os.cpu_count() or 4) * 2), len(rows))
    if workers <= 1:
        return [audio_file_metrics(path, stat.st_size) for path, _rel, stat in rows]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda row: audio_file_metrics(row[0], row[2].st_size), rows))


def collect_audio_files(
    audio_root: Path,
    webui_root: Path,
    source_root: Path,
    storage_root: str,
    language: str,
    language_info: dict[str, str],
    decoded_source_by_rel: dict[tuple[str, str], dict[str, str]] | None = None,
    prior_source_by_rel: dict[tuple[str, str], dict[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    decoded_source_by_rel = decoded_source_by_rel or {}
    prior_source_by_rel = prior_source_by_rel or {}
    by_id: dict[str, dict[str, Any]] = {}
    seen_occurrences: set[str] = set()
    # Resolve the surviving occurrence set first so the container headers of
    # the files that are about to be dropped are never read.
    selected: list[tuple[Path, str, os.stat_result]] = []
    for row in scan_audio_files(source_root):
        occurrence_key = normalize_posix(PurePosixPath(row[1]).with_suffix("")).lower()
        # Keep the preferred FLAC/WAV/WEM for one physical path stem while
        # preserving same-media-id occurrences in distinct folders or banks.
        if occurrence_key in seen_occurrences:
            continue
        seen_occurrences.add(occurrence_key)
        selected.append(row)
    metrics_by_row = audio_file_metrics_bulk(selected)
    for (path, rel, stat), metrics in zip(selected, metrics_by_row):
        audio_id = path.stem.lower()
        metadata = source_metadata_for_rel(
            storage_root,
            rel,
            language,
            language_info,
            decoded_source_by_rel,
            prior_source_by_rel,
        )
        entry = {
            "id": audio_id,
            "rel": rel,
            "storageRoot": storage_root,
            "src": served_audio_href(audio_root, webui_root, storage_root, rel),
            "format": path.suffix.lower().lstrip("."),
            "bytes": stat.st_size,
            **metrics,
            **metadata,
        }
        for key, value in audio_path_tags_for_rel(rel).items():
            entry.setdefault(key, value)
        apply_audio_category(entry)
        lookup_key = audio_id
        if lookup_key in by_id:
            entry["duplicateAudioId"] = audio_id
            lookup_key = f"{audio_id}@{storage_root}:{rel.lower()}"
        by_id[lookup_key] = entry
    return by_id


def merge_audio_file_indexes(
    *indexes: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge lookup indexes without dropping cross-scope physical files.

    Later indexes retain the canonical media-id key (language voice therefore
    keeps the historical lookup priority), while an earlier collision is moved
    to a stable occurrence key for inventory and debug-page use.
    """

    merged: dict[str, dict[str, Any]] = {}
    for index in indexes:
        for key, entry in index.items():
            if key in merged:
                previous = merged.pop(key)
                previous_rel = normalize_posix(str(previous.get("rel") or "")).lower()
                previous_storage = str(previous.get("storageRoot") or "")
                previous_id = str(previous.get("id") or key)
                previous["duplicateAudioId"] = previous_id
                merged[f"{previous_id}@{previous_storage}:{previous_rel}"] = previous
            merged[key] = entry
    return merged


def numeric_audio_entries_by_media_id(
    audio_index: dict[str, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Return decoded uint32 Wwise media by the entry's actual media id.

    Occurrence keys deliberately gain an ``@storage:path`` suffix when the
    same id exists more than once.  After an obsolete unknown-path occurrence
    is suppressed, that suffixed row can be the only surviving canonical
    media.  HIRC resolution must therefore inspect ``entry['id']`` rather than
    assuming every dictionary key is the numeric media id.
    """

    out: dict[int, dict[str, Any]] = {}
    for lookup_key, entry in audio_index.items():
        raw_id = str(entry.get("id") or "").strip().lower()
        if not raw_id.isdigit():
            continue
        media_id = int(raw_id)
        if media_id > 0xFFFFFFFF:
            continue
        # Preserve the historical direct-key preference when a genuine
        # same-id collision remains, but recover an occurrence-key-only row.
        if media_id not in out or str(lookup_key).lower() == raw_id:
            out[media_id] = entry
    return out

def build_dialog_audio_index(
    audio_dialog_paths: list[Path],
    audio_root: Path,
    webui_root: Path,
    language_root: Path,
    language: str,
    language_info: dict[str, str],
    preferred_extension: str,
) -> dict[str, dict[str, Any]]:
    duration_field = language_info["durationField"]
    # One directory walk answers the per-candidate existence probes and carries
    # each file's size, replacing roughly four syscalls per AudioDialog row.
    # A candidate the walk did not report still falls back to the filesystem so
    # a name that differs only by case resolves exactly as it did before.
    stat_by_rel = {rel: stat for _path, rel, stat in scan_audio_files(language_root)}
    out: dict[str, dict[str, Any]] = {}
    resolved: list[tuple[str, str, Path, os.stat_result, Any, Any, str, str]] = []
    for audio_dialog_path in audio_dialog_paths:
        rows = load_json_strict(audio_dialog_path, {})
        if not isinstance(rows, dict):
            raise SystemExit(f"AudioDialog table has unexpected shape: {audio_dialog_path}")
        source_path = display_path(audio_dialog_path)
        for row_key, row in rows.items():
            if not isinstance(row, dict):
                continue
            dialog_path = str(row.get("path") or "")
            if not dialog_path:
                continue
            audio_id = audio_id_from_path(dialog_path)
            candidates = []
            for extension in (
                preferred_extension,
                ".flac",
                ".wav",
                ".wem",
            ):
                normalized_extension = str(extension).lower()
                if not normalized_extension.startswith("."):
                    normalized_extension = "." + normalized_extension
                if normalized_extension in {item[0] for item in candidates}:
                    continue
                candidate_rel = audio_rel_for_dialog_path(dialog_path, normalized_extension)
                candidate_path = language_root / Path(*PurePosixPath(candidate_rel).parts)
                candidates.append((normalized_extension, candidate_rel, candidate_path))
            selected = None
            for _extension, candidate_rel, candidate_path in candidates:
                stat = stat_by_rel.get(candidate_rel)
                if stat is None:
                    if not candidate_path.exists():
                        continue
                    stat = candidate_path.stat()
                selected = (candidate_rel, candidate_path, stat)
                break
            if selected is None:
                continue
            rel, file_path, stat = selected
            resolved.append(
                (audio_id, rel, file_path, stat, row, row_key, source_path, dialog_path)
            )
    metrics_by_row = audio_file_metrics_bulk(
        [
            (file_path, rel, stat)
            for _id, rel, file_path, stat, _row, _key, _src, _dialog in resolved
        ]
    )
    for (
        audio_id,
        rel,
        file_path,
        stat,
        row,
        row_key,
        source_path,
        dialog_path,
    ), metrics in zip(resolved, metrics_by_row):
        authored_duration = row.get(duration_field)
        duration = authored_duration if isinstance(authored_duration, (int, float)) else metrics.get("duration")
        bitrate = round(stat.st_size * 8 / duration) if isinstance(duration, (int, float)) and duration > 0 else metrics.get("bitrate")
        entry = {
            "id": audio_id,
            "rel": rel,
            "storageRoot": language,
            "src": served_audio_href(audio_root, webui_root, language, rel),
            "format": file_path.suffix.lower().lstrip("."),
            "bytes": stat.st_size,
            "audioDialogKey": int(row_key) if str(row_key).lstrip("-").isdigit() else row_key,
            "audioDialogPath": dialog_path,
            "audioDialogSource": source_path,
            "speakerChannel": str(row.get("speakerChannel") or ""),
            "voType": row.get("voType"),
            "duration": duration if isinstance(duration, (int, float)) else None,
            "bitrate": bitrate,
            **audio_source_metadata("voice", language, language_info),
        }
        apply_audio_category(entry)
        out[audio_id] = entry
    return out





# Current AudioChinese sub_d4 externals contains one media entry whose exact
# authored path is absent from the current AudioDialog table. The path is the
# unique exact preimage in the bounded v1d4 C35 mission voice namespace; this
# recovers media identity only, not a dialog row, speaker, trigger, or playback
# location.
RECOVERED_EXTERNAL_MEDIA_IDENTITIES = {
    "CN": {
        955778167792087661: {
            "audioId": "au_voice_c35m3_3_001",
            "path": "v1d4/Narrating/HS_Part04/c35m3/au_voice_c35m3_3_001.wem",
            "evidence": "boundedD4MissionVoiceNamespaceUniqueFNV1a64Preimage",
            "playbackPlacementStatus": "identityOnlyNoCurrentAudioDialogOrTrigger",
        },
    },
}












def collect_audio_event_names(conv_dir: Path, export_root: Path) -> set[str]:
    names: set[str] = set()

    for conv_path in sorted(conv_dir.glob("*.json")):
        payload = load_json_strict(conv_path, {})
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
            payload = load_json_strict(path, {})
            if payload:
                visit(payload)

    return names






CUTSCENE_AUDIO_PLAYABLE_NAME_PREFIXES = (
    "AudioDlgEventPlayable",
    "AudioEventPlayable",
    "AudioMusicPlayable",
)


def cutscene_audio_playable_path_ids(export_root: Path) -> set[int]:
    """Every audio-playable path id the cutscene collectors can ask about.

    The three cutscene collectors each resolve a subset of these ids through
    the published object index, and one index pass reads a multi-gigabyte
    stream.  Resolving their union once keeps the result for each collector
    identical while paying for that stream a single time.
    """

    asset_map = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "maps"
        / "endfield_streamingassets_assets.json"
    )
    out: set[int] = set()
    for entry in iter_asset_map_objects(asset_map, '"Name": "Audio'):
        if not isinstance(entry, dict) or entry.get("Type") != "MonoBehaviour":
            continue
        path_id = entry.get("PathID")
        if isinstance(path_id, int) and str(entry.get("Name") or "").startswith(
            CUTSCENE_AUDIO_PLAYABLE_NAME_PREFIXES
        ):
            out.add(path_id)
    return out


















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


def event_bank_payloads_from_export(export_root: Path) -> list[tuple[str, bytes]]:
    payloads: list[tuple[str, bytes]] = []
    for bank_file in event_bank_files(export_root):
        try:
            payloads.append((normalize_posix(bank_file.relative_to(export_root)), bank_file.read_bytes()))
        except OSError:
            continue
    return payloads


def event_bank_payloads_from_vfs(args: argparse.Namespace) -> list[tuple[str, bytes]]:
    if not args.audio_dumper.exists() or not args.streaming_assets.exists():
        return []

    payloads: list[tuple[str, bytes]] = []
    seen_payloads: set[tuple[str, str, int, bytes, bytes]] = set()
    stream_failed = False
    sources = list(audio_vfs_sources(args))
    if (
        args.fallback_assets
        and args.fallback_assets.exists()
        and not same_resolved_path(args.streaming_assets, args.fallback_assets)
    ):
        sources.append(("Persistent", args.fallback_assets, args.streaming_assets))
    for source_label, streaming_assets, fallback_assets in sources:
        command = [
            str(args.audio_dumper),
            "stream",
            "--streaming-assets",
            str(streaming_assets),
            "--file-regex",
            EVENT_BANK_FILE_REGEX,
        ]
        for block_type in EVENT_BANK_VFS_BLOCK_TYPES:
            command.extend(["--block-type", block_type])
        if fallback_assets and fallback_assets.exists():
            command.extend(["--fallback-assets", str(fallback_assets)])

        try:
            result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"Audio events: VFS bank stream unavailable for {source_label} ({exc})")
            stream_failed = True
            continue

        stderr_text = result.stderr.strip()
        if stderr_text:
            print(f"Audio events VFS stream [{source_label}]: {stderr_text}")

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                block_type = str(payload.get("blockType") or "unknown")
                file_name = normalize_posix(str(payload.get("fileName") or "unknown.pck"))
                raw_data = base64.b64decode(str(payload.get("dataBase64") or ""))
            except (ValueError, TypeError):
                continue
            if not raw_data:
                continue
            payload_key = (block_type, file_name, len(raw_data), raw_data[:16], raw_data[-16:])
            if payload_key in seen_payloads:
                continue
            seen_payloads.add(payload_key)
            payloads.append((f"vfs/{source_label}/{block_type}/{file_name}", raw_data))
    if payloads:
        print(f"Audio events: streamed {len(payloads):,} bank PCK file(s) from VFS")
    elif stream_failed:
        print("Audio events: VFS bank stream unavailable; falling back to exported bank files")
    return payloads


def event_bank_payloads(args: argparse.Namespace) -> list[tuple[str, bytes]]:
    payloads = event_bank_payloads_from_vfs(args)
    if payloads:
        return payloads
    payloads = event_bank_payloads_from_export(args.export_root)
    if payloads:
        print(f"Audio events: using {len(payloads):,} exported bank PCK file(s)")
    return payloads

def collect_event_audio_index(
    event_names: set[str],
    audio_by_id: dict[str, dict[str, Any]],
    args: argparse.Namespace,
    explicit_event_hashes: set[int] | None = None,
    explicit_event_names_by_hash: dict[int, str] | None = None,
    hirc_summary: dict[str, Any] | None = None,
    wwise_event_inventory: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    explicit_event_hashes = {
        int(value) & 0xFFFFFFFF
        for value in (explicit_event_hashes or set())
        if int(value) & 0xFFFFFFFF
    }
    if not event_names and not explicit_event_hashes:
        return {}, []

    wanted_by_hash: dict[int, str] = {}
    for name in sorted(event_names, key=lambda value: (value.lower(), value)):
        synthetic = HASHED_EVENT_KEY_RE.fullmatch(name.strip())
        event_hash = int(synthetic.group(1), 16) if synthetic else fnv1_32(name.lower())
        wanted_by_hash.setdefault(event_hash, name)
    for event_hash in explicit_event_hashes:
        wanted_by_hash.setdefault(
            event_hash,
            (explicit_event_names_by_hash or {}).get(event_hash) or hashed_event_key(event_hash),
        )
    numeric_audio_entries = numeric_audio_entries_by_media_id(audio_by_id)
    numeric_audio_ids = set(numeric_audio_entries)
    if not numeric_audio_ids:
        return {}, []

    event_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_evidence: dict[tuple[str, str, int], dict[str, Any]] = {}
    linked_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    content_hash_by_path: dict[str, str] = {}

    def content_sha256(entry: dict[str, Any]) -> str:
        path = entry_audio_path(args.audio_root, str(args.language or "CN").upper(), entry)
        path_key = str(path)
        if path_key in content_hash_by_path:
            return content_hash_by_path[path_key]
        if not path.is_file():
            content_hash_by_path[path_key] = ""
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        value = digest.hexdigest()
        content_hash_by_path[path_key] = value
        entry["contentSha256"] = value
        return value

    package_payloads = event_bank_payloads(args)
    summary_type_counts: Counter[int] = Counter()
    summary_bank_versions: Counter[int] = Counter()
    embedded_bank_count = 0
    hirc_object_count = 0
    package_inventory: list[dict[str, Any]] = []
    decoded_sound_definitions: list[dict[str, Any]] = []
    event_reached_media_ids: set[int] = set()
    effect_definition_candidates: dict[
        int, dict[tuple[Any, ...], dict[str, Any]]
    ] = {}
    bus_definition_types: dict[int, Counter[int]] = defaultdict(Counter)
    bus_definition_candidates: dict[
        int, dict[tuple[int, str], dict[str, Any]]
    ] = {}
    corpus_processing_counts: Counter[str] = Counter()
    corpus_effect_reference_counts: Counter[tuple[str, int, int]] = Counter()
    corpus_output_bus_counts: Counter[int] = Counter()
    corpus_aux_parser_status_counts: Counter[str] = Counter()
    corpus_aux_flag_counts: Counter[int] = Counter()
    corpus_user_aux_bus_counts: Counter[int] = Counter()
    corpus_reflections_aux_bus_counts: Counter[int] = Counter()
    corpus_state_rtpc_parser_status_counts: Counter[str] = Counter()
    corpus_state_group_counts: Counter[int] = Counter()
    corpus_state_id_counts: Counter[int] = Counter()
    corpus_state_parameter_counts: Counter[str] = Counter()
    corpus_rtpc_id_counts: Counter[int] = Counter()
    corpus_rtpc_type_counts: Counter[str] = Counter()
    corpus_rtpc_parameter_counts: Counter[str] = Counter()
    corpus_property_counts: Counter[str] = Counter()
    corpus_ranged_property_counts: Counter[str] = Counter()
    corpus_action_control_status_counts: Counter[str] = Counter()
    corpus_action_control_operation_counts: Counter[str] = Counter()
    corpus_action_control_failure_counts: Counter[str] = Counter()
    corpus_action_control_typed_count = 0
    corpus_action_control_count = 0
    corpus_property_node_count = 0
    corpus_effect_flag_counts: Counter[int] = Counter()
    post_process_summaries: list[tuple[str, int, dict[str, Any]]] = []
    for bank_name, bank_data in package_payloads:
        package_row: dict[str, Any] = {
            "source": bank_name,
            "fileName": PurePosixPath(bank_name.replace("\\", "/")).name,
            "bytes": len(bank_data),
            "sha256": hashlib.sha256(bank_data).hexdigest(),
            "embeddedBankCount": 0,
            "hircObjectCount": 0,
            "eventObjectCount": 0,
            "bankVersions": {},
            "parseStatus": "complete",
        }
        source_parts = PurePosixPath(bank_name.replace("\\", "/")).parts
        if len(source_parts) >= 4 and source_parts[0] == "vfs":
            package_row["vfsSource"] = source_parts[1]
            package_row["blockType"] = source_parts[2]
        try:
            bank_payloads = iter_akpk_bank_payloads_from_bytes(bank_data, bank_name)
        except ValueError as exc:
            package_row["parseStatus"] = "invalidAkpk"
            package_row["diagnostic"] = str(exc)
            package_inventory.append(package_row)
            continue
        for bank_id, bank_payload in bank_payloads:
            embedded_bank_count += 1
            package_row["embeddedBankCount"] += 1
            bank_version: int | None = None
            for tag, body in iter_bnk_sections(bank_payload):
                if tag == b"BKHD" and len(body) >= 4:
                    bank_version = unpack_from("<I", body, 0)[0]
                    summary_bank_versions[bank_version] += 1
                    versions = package_row["bankVersions"]
                    versions[str(bank_version)] = int(versions.get(str(bank_version)) or 0) + 1
                    break
            objects = parse_hirc_objects(bank_payload)
            if not objects:
                continue
            hirc_object_count += len(objects)
            package_row["hircObjectCount"] += len(objects)
            package_row["eventObjectCount"] += sum(
                int(obj.get("type") or 0) == 4 for obj in objects.values()
            )
            summary_type_counts.update(
                int(obj.get("type") or 0) for obj in objects.values()
            )
            for object_id, obj in objects.items():
                object_type = int(obj.get("type") or 0)
                data = obj.get("data") or b""
                if object_type in (8, 18):
                    bus_definition_types[int(object_id)][object_type] += 1
                    add_hirc_bus_definition_candidate(
                        bus_definition_candidates,
                        int(object_id),
                        object_type,
                        data,
                        bank_id=bank_id,
                        bank_name=bank_name,
                    )
                effect_definition = hirc_v150_effect_definition(
                    object_type, data
                )
                if effect_definition is not None:
                    add_hirc_effect_definition_candidate(
                        effect_definition_candidates,
                        int(object_id),
                        effect_definition,
                        bank_id=bank_id,
                        bank_name=bank_name,
                    )
                node_processing = hirc_v150_node_processing(object_type, data)
                if node_processing is None:
                    continue
                corpus_processing_counts["parsedNodeCount"] += 1
                if node_processing.get("overrideParentFx"):
                    corpus_processing_counts["overrideParentFxNodeCount"] += 1
                effects = node_processing.get("effects") or []
                if effects:
                    corpus_processing_counts["effectNodeCount"] += 1
                    corpus_processing_counts["effectSlotCount"] += len(effects)
                if node_processing.get("bypassAll"):
                    corpus_processing_counts["bypassAllNodeCount"] += 1
                for effect in effects:
                    effect_id = int(effect.get("effectId") or 0)
                    flags_raw = int(effect.get("flagsRaw") or 0)
                    corpus_effect_flag_counts[flags_raw] += 1
                    if effect.get("effectBypass"):
                        corpus_processing_counts["effectBypassSlotCount"] += 1
                    if effect.get("effectShareSet"):
                        corpus_processing_counts["effectShareSetSlotCount"] += 1
                    if effect.get("effectRendered"):
                        corpus_processing_counts["effectRenderedSlotCount"] += 1
                    if int(effect.get("unknownFlagBits") or 0):
                        corpus_processing_counts[
                            "effectUnknownFlagBitsCount"
                        ] += 1
                    if effect_id:
                        corpus_processing_counts["effectReferenceCount"] += 1
                        corpus_effect_reference_counts[
                            (bank_name, bank_id, effect_id)
                        ] += 1
                    else:
                        corpus_processing_counts["emptyEffectSlotCount"] += 1
                if node_processing.get("overrideParentMetadata"):
                    corpus_processing_counts["overrideParentMetadataNodeCount"] += 1
                metadata = node_processing.get("metadata") or []
                if metadata:
                    corpus_processing_counts["metadataNodeCount"] += 1
                    corpus_processing_counts["metadataSlotCount"] += len(metadata)
                aux_sends = node_processing.get("auxSends") or {}
                aux_parser_status = str(
                    aux_sends.get("parserStatus") or "notParsed"
                )
                corpus_aux_parser_status_counts[aux_parser_status] += 1
                if aux_parser_status == "typedExactV150NodeAuxParams":
                    if aux_sends.get("properties") or aux_sends.get("rangedProperties"):
                        corpus_property_node_count += 1
                    for prop in aux_sends.get("properties") or []:
                        corpus_property_counts[
                            str(prop.get("propertyLabel") or "unknown")
                        ] += 1
                    for prop in aux_sends.get("rangedProperties") or []:
                        corpus_ranged_property_counts[
                            str(prop.get("propertyLabel") or "unknown")
                        ] += 1
                    aux_flags_raw = int(aux_sends.get("auxFlagsRaw") or 0)
                    corpus_aux_flag_counts[aux_flags_raw] += 1
                    if aux_sends.get("useGameDefinedAuxSends"):
                        corpus_processing_counts[
                            "gameDefinedAuxSendUseBitNodeCount"
                        ] += 1
                    if aux_sends.get("overrideGameDefinedAuxSends"):
                        corpus_processing_counts[
                            "gameDefinedAuxSendOverrideBitNodeCount"
                        ] += 1
                    if aux_sends.get("hasUserDefinedAuxSendSlots"):
                        corpus_processing_counts[
                            "userDefinedAuxSlotNodeCount"
                        ] += 1
                    if aux_sends.get("overrideUserDefinedAuxSends"):
                        corpus_processing_counts[
                            "userDefinedAuxSendOverrideBitNodeCount"
                        ] += 1
                    for user_send in aux_sends.get("userDefinedAuxSends") or []:
                        bus_id = int(user_send.get("busId") or 0)
                        if bus_id:
                            corpus_user_aux_bus_counts[bus_id] += 1
                    reflections_bus_id = int(
                        aux_sends.get("reflectionsAuxBusId") or 0
                    )
                    if reflections_bus_id:
                        corpus_reflections_aux_bus_counts[
                            reflections_bus_id
                        ] += 1
                state_rtpc = node_processing.get("stateAndRtpc") or {}
                state_rtpc_status = str(
                    state_rtpc.get("parserStatus") or "notParsed"
                )
                corpus_state_rtpc_parser_status_counts[state_rtpc_status] += 1
                if state_rtpc_status == "typedExactV150NodeStateAndRtpc":
                    if state_rtpc.get("stateGroups") or state_rtpc.get("rtpcCurves"):
                        corpus_processing_counts["stateRtpcNodeCount"] += 1
                    for group in state_rtpc.get("stateGroups") or []:
                        group_id = int(group.get("groupId") or 0)
                        corpus_state_group_counts[group_id] += 1
                        for state in group.get("states") or []:
                            corpus_state_id_counts[int(state.get("stateId") or 0)] += 1
                            for value in state.get("values") or []:
                                corpus_processing_counts["stateValueCount"] += 1
                                corpus_state_parameter_counts[
                                    str(value.get("parameterLabel") or "unknown")
                                ] += 1
                    for curve in state_rtpc.get("rtpcCurves") or []:
                        rtpc_id = int(curve.get("rtpcId") or 0)
                        corpus_rtpc_id_counts[rtpc_id] += 1
                        corpus_rtpc_type_counts[
                            str(curve.get("rtpcTypeLabel") or "unknown")
                        ] += 1
                        corpus_rtpc_parameter_counts[
                            str(curve.get("parameterLabel") or "unknown")
                        ] += 1
                        corpus_processing_counts["rtpcPointCount"] += len(
                            curve.get("points") or []
                        )
                override_bus_id = int(node_processing.get("overrideBusId") or 0)
                if override_bus_id:
                    corpus_processing_counts["outputBusNodeCount"] += 1
                    corpus_output_bus_counts[override_bus_id] += 1
            decoded_sound_definitions.extend(collect_hirc_decoded_sound_definitions(
                objects,
                numeric_audio_ids,
                bank_name=bank_name,
                bank_id=bank_id,
                bank_version=bank_version,
            ))
            event_hashes = sorted(
                object_id
                for object_id, obj in objects.items()
                if int(obj.get("type") or 0) == 4
            )
            for event_hash in event_hashes:
                event_name = wanted_by_hash.get(event_hash) or hashed_event_key(event_hash)
                traversal = traverse_hirc_event(
                    event_hash,
                    objects,
                    numeric_audio_ids,
                    bank_version=bank_version,
                )
                for action in traversal["actionEvidence"]:
                    if action.get("operation") in {"play", "playEvent"}:
                        continue
                    corpus_action_control_count += 1
                    operation_label = str(action.get("operation") or "unknown")
                    corpus_action_control_operation_counts[operation_label] += 1
                    status = str(
                        action.get("actionControlParserStatus") or "missing"
                    )
                    corpus_action_control_status_counts[status] += 1
                    if status == "typedExactV150":
                        corpus_action_control_typed_count += 1
                    failure = action.get("actionControlParserFailure") or {}
                    if isinstance(failure, dict) and failure.get("reason"):
                        corpus_action_control_failure_counts[
                            str(failure["reason"])
                        ] += 1
                post_process_summaries.append((
                    bank_name, bank_id, traversal["postProcessSummary"]
                ))
                action_ids = traversal["actionIds"]
                visited = set(traversal["visitedObjectIds"])
                media_ids = traversal["mediaIds"]
                event_reached_media_ids.update(
                    int(media_id) for media_id in traversal["sourceMediaIds"]
                )

                evidence_key = (event_name.lower(), bank_name, bank_id)
                object_type_counts, object_type_labels, selection_object_types = (
                    summarize_hirc_object_types(objects, visited)
                )
                if wwise_event_inventory is not None:
                    wwise_event_inventory.append({
                        "schemaVersion": 1,
                        "eventId": event_name,
                        "eventHash": event_hash,
                        "eventHashHex": f"0x{event_hash:08x}",
                        "eventIdentityStatus": (
                            "recoveredAuthoredIdentity"
                            if event_hash in wanted_by_hash
                            else "wwiseObjectWithoutRecoveredTriggerName"
                        ),
                        "bankId": bank_id,
                        "bankVersion": bank_version,
                        "bank": bank_name,
                        "actionIds": action_ids,
                        "actionEvidence": traversal["actionEvidence"],
                        "actionDispatchEvidence": traversal["actionDispatchEvidence"],
                        "rootPlayActionCount": traversal["rootPlayActionCount"],
                        "rootStopActionCount": traversal["rootStopActionCount"],
                        "visitedObjectCount": len(visited),
                        "objectTypeCounts": object_type_counts,
                        "objectTypeLabels": object_type_labels,
                        "selectionObjectTypes": selection_object_types,
                        "mediaRelationTypes": sorted({
                            str(relation)
                            for row in traversal["mediaEvidence"]
                            for relation in row.get("relationTypes") or []
                            if str(relation)
                        }),
                        "sourceObjectSummary": traversal["sourceObjectSummary"],
                        "postProcessSummary": traversal["postProcessSummary"],
                        "nonMediaSourceEvidence": traversal["nonMediaSourceEvidence"],
                        "sourceMediaIds": traversal["sourceMediaIds"],
                        "mediaIds": media_ids,
                        "resolvedMediaCount": len(media_ids),
                        "unresolvedNodeCount": len(traversal["unresolvedNodes"]),
                        "unresolvedNodeSamples": traversal["unresolvedNodes"][:20],
                        "traversalStatus": traversal["traversalStatus"],
                        "source": "wwiseHircObjectInventory",
                    })
                if event_hash not in wanted_by_hash:
                    continue
                event_evidence[evidence_key] = {
                    "schemaVersion": EVENT_EVIDENCE_SCHEMA_VERSION,
                    "eventId": event_name,
                    "eventHash": event_hash,
                    "bankId": bank_id,
                    "bankVersion": bank_version,
                    "bank": bank_name,
                    "actionIds": action_ids,
                    "actionEvidence": traversal["actionEvidence"],
                    "actionDispatchEvidence": traversal["actionDispatchEvidence"],
                    "actionParser": "wwise150TypedPlaybackAndControlActionPayloads",
                    "rootPlayActionCount": traversal["rootPlayActionCount"],
                    "rootStopActionCount": traversal["rootStopActionCount"],
                    "visitedObjectIds": sorted(visited),
                    "objectTypeCounts": object_type_counts,
                    "objectTypeLabels": object_type_labels,
                    "selectionObjectTypes": selection_object_types,
                    "containerEvidence": traversal["containerEvidence"],
                    "musicNodeEvidence": traversal["musicNodeEvidence"],
                    "postProcessSummary": traversal["postProcessSummary"],
                    "sourceObjectSummary": traversal["sourceObjectSummary"],
                    "nonMediaSourceEvidence": traversal["nonMediaSourceEvidence"],
                    "mediaEvidence": traversal["mediaEvidence"],
                    "sourceMediaIds": traversal["sourceMediaIds"],
                    "mediaIds": media_ids,
                    "resolvedMediaCount": len(media_ids),
                    "unresolvedNodes": traversal["unresolvedNodes"],
                    "traversalStatus": traversal["traversalStatus"],
                    "edgeParser": "wwise150TypedReciprocalChildrenSelectorsMusicAndSources",
                    "source": "wwiseHirc",
                    "nestedReferenceConfidence": "typedExact" if not traversal["unresolvedNodes"] else "typedPartial",
                }
                media_evidence_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
                for row in traversal["mediaEvidence"]:
                    if row.get("decoded"):
                        media_evidence_by_id[int(row["mediaId"])].append({
                            key: row[key]
                            for key in (
                                "mediaId", "soundObjectCount", "soundObjectIds",
                                "musicTrackObjectCount", "musicTrackObjectIds",
                                "rootActionIds", "relationTypes", "selectionPaths",
                                "sourceKinds", "pluginIds", "pluginNames",
                                "streamTypes", "sourceBits",
                            )
                            if row.get(key) not in (None, "", [])
                        })
                for media_id in media_ids:
                    audio_entry = numeric_audio_entries.get(media_id)
                    if not audio_entry:
                        continue
                    link_key = (event_name.lower(), str(media_id))
                    if link_key in linked_by_key:
                        existing = linked_by_key[link_key]
                        existing_evidence = existing.setdefault("wwiseMediaEvidence", [])
                        for row in media_evidence_by_id.get(media_id, []):
                            bank_row = {**row, "bankId": bank_id, "bankPackage": PurePosixPath(bank_name.replace("\\", "/")).name}
                            if bank_row not in existing_evidence:
                                existing_evidence.append(bank_row)
                        continue
                    linked = {
                        **audio_entry,
                        "id": event_name,
                        "eventId": event_name,
                        "eventHash": event_hash,
                        "mediaId": media_id,
                        "bankId": bank_id,
                        "bank": bank_name,
                        "source": "wwiseHirc",
                        "contentSha256": content_sha256(audio_entry),
                        "wwiseMediaEvidence": [
                            {**row, "bankId": bank_id, "bankPackage": PurePosixPath(bank_name.replace("\\", "/")).name}
                            for row in media_evidence_by_id.get(media_id, [])
                        ],
                    }
                    event_links[event_name.lower()].append(linked)
                    linked_by_key[link_key] = linked
        package_inventory.append(package_row)

    effect_catalog, bus_catalog = finalize_hirc_post_process_catalog(
        effect_definition_candidates,
        bus_definition_types,
        bus_definition_candidates,
    )
    for definition in bus_catalog.values():
        definition.update(hirc_bus_parent_path(
            int(definition.get("busId") or 0), bus_catalog
        ))
    for summary_bank_name, summary_bank_id, post_process_summary in post_process_summaries:
        resolve_hirc_post_process_summary(
            post_process_summary,
            effect_catalog,
            bus_catalog,
            bank_id=summary_bank_id,
            bank_name=summary_bank_name,
        )

    corpus_plugin_reference_counts: Counter[str] = Counter()
    corpus_effect_resolution_counts: Counter[str] = Counter()
    corpus_parameter_schema_reference_counts: Counter[str] = Counter()
    corpus_decoded_parameter_reference_count = 0
    corpus_partial_parameter_reference_count = 0
    for (
        reference_bank_name, reference_bank_id, effect_id
    ), reference_count in corpus_effect_reference_counts.items():
        definition = effect_catalog.get(effect_id)
        status = str(
            (definition or {}).get("resolutionStatus")
            or "effectDefinitionNotFound"
        )
        if status == "ambiguousPluginDefinitions":
            same_bank = [
                row
                for row in definition.get("definitions") or []
                if any(
                    int(scope.get("bankId") or 0) == reference_bank_id
                    and str(scope.get("bank") or "") == reference_bank_name
                    for scope in row.get("bankScopes") or []
                    if isinstance(scope, dict)
                )
            ]
            if len(same_bank) == 1:
                definition = {
                    **same_bank[0],
                    "resolutionStatus": "exactSameBankPackagePluginDefinition",
                }
                status = "exactSameBankPackagePluginDefinition"
        corpus_effect_resolution_counts[status] += reference_count
        if status in {
            "exactUniquePluginDefinition",
            "exactSameBankPackagePluginDefinition",
        }:
            plugin_key = str(
                definition.get("pluginName")
                or definition.get("pluginClassIdHex")
                or "unknown"
            )
            corpus_plugin_reference_counts[plugin_key] += reference_count
            parameter_schema = str(definition.get("parameterSchema") or "")
            if parameter_schema:
                corpus_decoded_parameter_reference_count += reference_count
                corpus_parameter_schema_reference_counts[parameter_schema] += reference_count
                if str(definition.get("parameterParserStatus") or "").startswith(
                    "typedExactLayoutPartialSemantics"
                ):
                    corpus_partial_parameter_reference_count += reference_count
    corpus_bus_resolution_counts: Counter[str] = Counter()
    for bus_id, node_count in corpus_output_bus_counts.items():
        status = str(
            (bus_catalog.get(bus_id) or {}).get("resolutionStatus")
            or "audioBusDefinitionNotFound"
        )
        corpus_bus_resolution_counts[status] += node_count
    corpus_aux_bus_resolution_counts: Counter[str] = Counter()
    for bus_id, reference_count in (
        corpus_user_aux_bus_counts + corpus_reflections_aux_bus_counts
    ).items():
        status = str(
            (bus_catalog.get(bus_id) or {}).get("resolutionStatus")
            or "auxiliaryBusDefinitionNotFound"
        )
        corpus_aux_bus_resolution_counts[status] += reference_count

    unique_effect_definitions = [
        definition
        for definitions in effect_definition_candidates.values()
        for definition in definitions.values()
    ]
    effect_definition_plugin_counts: Counter[str] = Counter()
    effect_parameter_schema_counts: Counter[str] = Counter()
    partial_effect_parameter_definition_count = 0
    plugin_media_dependency_plugin_counts: Counter[str] = Counter()
    plugin_media_dependency_definition_count = 0
    plugin_media_dependency_occurrence_count = 0
    plugin_media_dependency_reference_occurrence_count = 0
    unique_plugin_media_dependencies: dict[
        tuple[int, int, int], dict[str, Any]
    ] = {}
    for definition in unique_effect_definitions:
        plugin_key = str(
            definition.get("pluginName")
            or definition.get("pluginClassIdHex")
            or "unknown"
        )
        effect_definition_plugin_counts[plugin_key] += 1
        parameter_schema = str(definition.get("parameterSchema") or "")
        if parameter_schema:
            effect_parameter_schema_counts[parameter_schema] += 1
            if str(definition.get("parameterParserStatus") or "").startswith(
                "typedExactLayoutPartialSemantics"
            ):
                partial_effect_parameter_definition_count += 1
        dependencies = definition.get("pluginMediaDependencies") or []
        if dependencies:
            occurrence_count = int(
                definition.get("definitionOccurrenceCount") or 1
            )
            plugin_media_dependency_definition_count += 1
            plugin_media_dependency_occurrence_count += occurrence_count
            plugin_media_dependency_reference_occurrence_count += (
                len(dependencies) * occurrence_count
            )
            plugin_media_dependency_plugin_counts[plugin_key] += len(dependencies)
            for dependency in dependencies:
                key = (
                    int(definition.get("pluginClassId") or 0),
                    int(dependency.get("pluginDataIndex") or 0),
                    int(dependency.get("mediaId") or 0),
                )
                unique_plugin_media_dependencies.setdefault(key, {
                    "pluginClassIdHex": definition.get("pluginClassIdHex"),
                    "pluginName": definition.get("pluginName"),
                    **dependency,
                })

    bus_parent_resolution_counts: Counter[str] = Counter()
    bus_effect_parser_counts: Counter[str] = Counter()
    bus_effect_plugin_counts: Counter[str] = Counter()
    bus_effect_slot_count = 0
    bus_effect_parameter_count = 0
    bus_effect_bypass_slot_count = 0
    bus_effect_share_set_slot_count = 0
    bus_effect_rendered_slot_count = 0
    bus_effect_unknown_flag_bits_count = 0
    bus_state_rtpc_parser_counts: Counter[str] = Counter()
    bus_rtpc_curve_count = 0
    bus_rtpc_point_count = 0
    bus_state_property_count = 0
    bus_state_group_count = 0
    bus_state_count = 0
    bus_state_value_count = 0
    bus_rtpc_id_counts: Counter[int] = Counter()
    bus_rtpc_parameter_counts: Counter[str] = Counter()
    bus_state_parameter_counts: Counter[str] = Counter()
    bus_state_group_id_counts: Counter[int] = Counter()
    bus_state_id_counts: Counter[int] = Counter()
    for definition in bus_catalog.values():
        bus_parent_resolution_counts[str(
            definition.get("parentResolutionStatus") or "unknown"
        )] += 1
        bus_effect_parser_counts[str(
            definition.get("effectParserStatus") or "notParsed"
        )] += 1
        for slot in definition.get("effects") or []:
            bus_effect_slot_count += 1
            bus_effect_bypass_slot_count += bool(slot.get("effectBypass"))
            bus_effect_share_set_slot_count += bool(slot.get("effectShareSet"))
            bus_effect_rendered_slot_count += bool(slot.get("effectRendered"))
            bus_effect_unknown_flag_bits_count += bool(
                int(slot.get("unknownFlagBits") or 0)
            )
            plugin_key = str(
                slot.get("pluginName")
                or slot.get("pluginClassIdHex")
                or slot.get("effectIdHex")
                or "unknown"
            )
            bus_effect_plugin_counts[plugin_key] += 1
            if slot.get("parameterSchema"):
                bus_effect_parameter_count += 1
        serialized_state_rtpc = definition.get("serializedStateAndRtpc") or {}
        parser_status = str(
            serialized_state_rtpc.get("parserStatus") or "notParsed"
        )
        bus_state_rtpc_parser_counts[parser_status] += 1
        if parser_status != "typedExactV150BusInitialRtpcAndState":
            continue
        bus_rtpc_curve_count += int(
            serialized_state_rtpc.get("rtpcCurveCount") or 0
        )
        bus_rtpc_point_count += int(
            serialized_state_rtpc.get("rtpcPointCount") or 0
        )
        bus_state_property_count += int(
            serialized_state_rtpc.get("statePropertyCount") or 0
        )
        bus_state_group_count += int(
            serialized_state_rtpc.get("stateGroupCount") or 0
        )
        bus_state_count += int(serialized_state_rtpc.get("stateCount") or 0)
        bus_state_value_count += int(
            serialized_state_rtpc.get("stateValueCount") or 0
        )
        for curve in serialized_state_rtpc.get("rtpcCurves") or []:
            bus_rtpc_id_counts[int(curve.get("rtpcId") or 0)] += 1
            bus_rtpc_parameter_counts[str(
                curve.get("parameterLabel") or "unknown"
            )] += 1
        for prop in serialized_state_rtpc.get("stateProperties") or []:
            bus_state_parameter_counts[str(
                prop.get("parameterLabel") or "unknown"
            )] += 1
        for group in serialized_state_rtpc.get("stateGroups") or []:
            bus_state_group_id_counts[int(group.get("groupId") or 0)] += 1
            for state in group.get("states") or []:
                bus_state_id_counts[int(state.get("stateId") or 0)] += 1

    public_bus_definitions = []
    for definition in sorted(
        bus_catalog.values(), key=lambda row: int(row.get("busId") or 0)
    ):
        public_bus_definitions.append({
            key: definition[key]
            for key in (
                "busId", "busIdHex", "objectType", "objectTypeLabel",
                "objectTypes", "objectTypeLabels", "payloadByteLength",
                "payloadSha256", "definitionOccurrenceCount",
                "resolutionStatus", "parentBusId", "parentBusIdHex",
                "parentParserStatus", "parentResolutionStatus", "parserStatus",
                "effectParserStatus", "effectChunkOffset",
                "effectChunkByteLength", "bypassAllRaw", "bypassAll",
                "effectSlotCount", "effects", "effectChunkCandidateCount",
                "nestedSuffixCandidateCount", "effectEvidenceBoundary",
                "serializedBusParserStatus", "serializedDeviceShareSetId",
                "serializedDeviceShareSetIdHex", "serializedPropertyCount",
                "serializedProperties", "serializedPositioningBitsRaw",
                "serializedPositioning3dBitsRaw", "serializedAuxFlagsRaw",
                "serializedUserAuxBusIds", "serializedUserAuxBusIdHexes",
                "serializedReflectionsAuxBusId",
                "serializedReflectionsAuxBusIdHex", "serializedBusFlagsRaw",
                "serializedMaxInstances", "serializedChannelConfig",
                "serializedBusStateFlagsRaw", "serializedRecoveryTimeMs",
                "serializedMaxDuckVolumeDb", "serializedDuckCount",
                "serializedDucks", "metadataChunkOffset", "metadataSlotCount",
                "metadata", "remainingSubtypeByteLength",
                "serializedStateAndRtpc",
                "emptyEffectSchemaFingerprint", "emptyEffectSchemaSiblingCount",
                "busPathIds", "busPathIdHexes", "busPathResolutionStatus",
                "effectBusIds", "effectBusIdHexes",
                "unresolvedBusProcessingIds",
                "unresolvedBusProcessingIdHexes",
            )
            if definition.get(key) is not None
        })

    game_parameter_name_evidence = []
    for source_row in HIRC_GAME_PARAMETER_NAME_EVIDENCE["entries"]:
        row = dict(source_row)
        parameter_id = int(row["parameterId"])
        row["nodeRtpcCurveCount"] = int(
            corpus_rtpc_id_counts.get(parameter_id, 0)
        )
        row["busRtpcCurveCount"] = int(
            bus_rtpc_id_counts.get(parameter_id, 0)
        )
        row["serializedHircMatch"] = bool(
            row["nodeRtpcCurveCount"] or row["busRtpcCurveCount"]
        )
        game_parameter_name_evidence.append(row)

    if hirc_summary is not None:
        definition_only_media_objects = [
            row for row in decoded_sound_definitions
            if int(row.get("mediaId") or 0) not in event_reached_media_ids
        ]
        hirc_summary.clear()
        hirc_summary.update({
            "source": "wwiseBankHircInventory",
            "packageCount": len(package_payloads),
            "packageInventorySchemaVersion": 1,
            "packageInventory": package_inventory,
            "packageFingerprint": hashlib.sha256(
                json.dumps(
                    [
                        {key: row.get(key) for key in ("source", "bytes", "sha256")}
                        for row in package_inventory
                    ],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "embeddedBankCount": embedded_bank_count,
            "hircObjectCount": hirc_object_count,
            "decodedSoundDefinitionCount": len(decoded_sound_definitions),
            "definitionOnlyDecodedSoundObjectCount": len(definition_only_media_objects),
            "definitionOnlyDecodedMediaCount": len({
                int(row["mediaId"]) for row in definition_only_media_objects
            }),
            "definitionOnlyDecodedSoundObjects": definition_only_media_objects,
            "postProcessSummary": {
                "parserStatus": (
                    "typedExactV150NodeBaseAuxSendsBusHierarchyBusStateRtpcAndSelectedPluginParameters"
                ),
                **dict(sorted(corpus_processing_counts.items())),
                "uniqueEffectObjectIds": len(effect_catalog),
                "uniqueEffectDefinitionCount": len(unique_effect_definitions),
                "ambiguousEffectObjectIdCount": sum(
                    row.get("resolutionStatus") == "ambiguousPluginDefinitions"
                    for row in effect_catalog.values()
                ),
                "effectDefinitionPluginCounts": dict(
                    sorted(effect_definition_plugin_counts.items())
                ),
                "decodedEffectParameterDefinitionCount": sum(
                    effect_parameter_schema_counts.values()
                ),
                "exactEffectParameterDefinitionCount": (
                    sum(effect_parameter_schema_counts.values())
                    - partial_effect_parameter_definition_count
                ),
                "partialEffectParameterDefinitionCount": (
                    partial_effect_parameter_definition_count
                ),
                "opaqueEffectParameterDefinitionCount": (
                    len(unique_effect_definitions)
                    - sum(effect_parameter_schema_counts.values())
                ),
                "decodedEffectParameterReferenceCount": (
                    corpus_decoded_parameter_reference_count
                ),
                "exactEffectParameterReferenceCount": (
                    corpus_decoded_parameter_reference_count
                    - corpus_partial_parameter_reference_count
                ),
                "partialEffectParameterReferenceCount": (
                    corpus_partial_parameter_reference_count
                ),
                "effectParameterSchemaCounts": dict(
                    sorted(effect_parameter_schema_counts.items())
                ),
                "effectParameterSchemaReferenceCounts": dict(
                    sorted(corpus_parameter_schema_reference_counts.items())
                ),
                "pluginMediaDependencyDefinitionCount": (
                    plugin_media_dependency_definition_count
                ),
                "pluginMediaDependencyDefinitionOccurrenceCount": (
                    plugin_media_dependency_occurrence_count
                ),
                "pluginMediaDependencyReferenceOccurrenceCount": (
                    plugin_media_dependency_reference_occurrence_count
                ),
                "uniquePluginMediaIdCount": len({
                    int(row.get("mediaId") or 0)
                    for row in unique_plugin_media_dependencies.values()
                }),
                "pluginMediaDependencyPluginCounts": dict(
                    sorted(plugin_media_dependency_plugin_counts.items())
                ),
                "pluginMediaDependencies": [
                    unique_plugin_media_dependencies[key]
                    for key in sorted(unique_plugin_media_dependencies)
                ],
                "effectParameterBinaryContract": HIRC_EFFECT_PARAMETER_CONTRACT,
                "effectPluginReferenceCounts": dict(
                    sorted(corpus_plugin_reference_counts.items())
                ),
                "effectResolutionCounts": dict(
                    sorted(corpus_effect_resolution_counts.items())
                ),
                "effectSlotFlagCounts": {
                    str(key): value
                    for key, value in sorted(corpus_effect_flag_counts.items())
                },
                "uniqueOutputBusIds": len(corpus_output_bus_counts),
                "auxSendParserStatusCounts": dict(
                    sorted(corpus_aux_parser_status_counts.items())
                ),
                "auxSendFlagCounts": {
                    f"0x{key:02x}": value
                    for key, value in sorted(corpus_aux_flag_counts.items())
                },
                "userDefinedAuxBusReferenceCount": sum(
                    corpus_user_aux_bus_counts.values()
                ),
                "uniqueUserDefinedAuxBusIds": len(corpus_user_aux_bus_counts),
                "reflectionsAuxBusReferenceCount": sum(
                    corpus_reflections_aux_bus_counts.values()
                ),
                "uniqueReflectionsAuxBusIds": len(
                    corpus_reflections_aux_bus_counts
                ),
                "auxiliaryBusResolutionCounts": dict(
                    sorted(corpus_aux_bus_resolution_counts.items())
                ),
                "stateRtpcParserStatusCounts": dict(
                    sorted(corpus_state_rtpc_parser_status_counts.items())
                ),
                "stateGroupReferenceCount": sum(corpus_state_group_counts.values()),
                "uniqueStateGroupIds": len(corpus_state_group_counts),
                "uniqueStateIds": len(corpus_state_id_counts),
                "stateParameterCounts": dict(
                    sorted(corpus_state_parameter_counts.items())
                ),
                "authoredPropertyValueCount": sum(corpus_property_counts.values()),
                "authoredRangedPropertyValueCount": sum(
                    corpus_ranged_property_counts.values()
                ),
                "authoredPropertyNodeCount": corpus_property_node_count,
                "eventActionControlCount": corpus_action_control_count,
                "eventActionControlTypedExactCount": corpus_action_control_typed_count,
                "eventActionControlStatusCounts": dict(
                    sorted(corpus_action_control_status_counts.items())
                ),
                "eventActionControlOperationCounts": dict(
                    sorted(corpus_action_control_operation_counts.items())
                ),
                "eventActionControlFailureCounts": dict(
                    sorted(corpus_action_control_failure_counts.items())
                ),
                "authoredPropertyCounts": dict(
                    sorted(corpus_property_counts.items())
                ),
                "authoredRangedPropertyCounts": dict(
                    sorted(corpus_ranged_property_counts.items())
                ),
                "rtpcCurveCount": sum(corpus_rtpc_id_counts.values()),
                "uniqueRtpcIds": len(corpus_rtpc_id_counts),
                "rtpcTypeCounts": dict(sorted(corpus_rtpc_type_counts.items())),
                "rtpcParameterCounts": dict(
                    sorted(corpus_rtpc_parameter_counts.items())
                ),
                "gameParameterNameEvidence": {
                    "source": HIRC_GAME_PARAMETER_NAME_EVIDENCE["source"],
                    "metadataSha256": HIRC_GAME_PARAMETER_NAME_EVIDENCE[
                        "metadataSha256"
                    ],
                    "evidence": HIRC_GAME_PARAMETER_NAME_EVIDENCE["evidence"],
                    "entries": game_parameter_name_evidence,
                    "evidenceBoundary": HIRC_GAME_PARAMETER_NAME_EVIDENCE[
                        "evidenceBoundary"
                    ],
                },
                "knownBusObjectIds": len(bus_catalog),
                "busDefinitionCount": len(public_bus_definitions),
                "busParentResolutionCounts": dict(
                    sorted(bus_parent_resolution_counts.items())
                ),
                "busEffectParserCounts": dict(
                    sorted(bus_effect_parser_counts.items())
                ),
                "busEffectSlotCount": bus_effect_slot_count,
                "decodedBusEffectParameterCount": bus_effect_parameter_count,
                "busEffectBypassSlotCount": bus_effect_bypass_slot_count,
                "busEffectShareSetSlotCount": bus_effect_share_set_slot_count,
                "busEffectRenderedSlotCount": bus_effect_rendered_slot_count,
                "busEffectUnknownFlagBitsCount": bus_effect_unknown_flag_bits_count,
                "busEffectPluginCounts": dict(
                    sorted(bus_effect_plugin_counts.items())
                ),
                "busStateRtpcParserStatusCounts": dict(
                    sorted(bus_state_rtpc_parser_counts.items())
                ),
                "busRtpcCurveCount": bus_rtpc_curve_count,
                "busRtpcPointCount": bus_rtpc_point_count,
                "busStatePropertyCount": bus_state_property_count,
                "busStateGroupCount": bus_state_group_count,
                "busStateCount": bus_state_count,
                "busStateValueCount": bus_state_value_count,
                "busUniqueRtpcIds": len(bus_rtpc_id_counts),
                "busRtpcParameterCounts": dict(
                    sorted(bus_rtpc_parameter_counts.items())
                ),
                "busStateParameterCounts": dict(
                    sorted(bus_state_parameter_counts.items())
                ),
                "busUniqueStateGroupIds": len(bus_state_group_id_counts),
                "busUniqueStateIds": len(bus_state_id_counts),
                "busDefinitions": public_bus_definitions,
                "outputBusResolutionCounts": dict(
                    sorted(corpus_bus_resolution_counts.items())
                ),
                "pluginNameEvidence": (
                    "Built-in class IDs are pinned by registration objects and "
                    "factory source paths embedded in the shipped AkSoundEngine.dll."
                ),
                "evidenceBoundary": (
                    "The bank proves ordered direct effect slots, plug-in class "
                    "identity, parameter bytes, exact plug-in media dependency IDs, "
                    "explicit output-bus IDs, and the complete reciprocal Audio/Aux "
                    "Bus parent hierarchy. It also proves serialized User-Defined "
                    "Aux slots, Early Reflections bus IDs, and authored Game-Defined "
                    "use/override bits. Runtime Game-Defined bus IDs/control values "
                    "are not serialized. Current v150 Bus objects are consumed "
                    "through the typed CAkBus field order through InitialFX and the "
                    "InitialRTPC-before-StateChunk suffix, which proves explicit "
                    "zero-count/non-empty arrays plus authored Bus control curves "
                    "and State overrides; "
                    "the legacy sibling prefix/suffix correlation remains only for "
                    "non-v150 or synthetic payloads. Fourteen "
                    "current-client SetParamsBlock schemas decode authored base "
                    "values; the v150 AkPropID bundle also preserves exact raw U32 "
                    "and finite-float base-property values. Initial BypassFX/"
                    "BypassAllFX property IDs are absent in this corpus; direct "
                    "NodeBase bypass remains a separate field. Other plug-in "
                    "payloads remain opaque. Plug-in media IDs are not treated as "
                    "playable Sound WEM leaves. Effective inherited "
                    "sends, live RTPC/State/modulator values, effective inherited "
                    "properties, bypass decisions, platform DSP, and audibility are "
                    "not observed."
                ),
            },
            "bankVersions": {
                str(version): count
                for version, count in sorted(summary_bank_versions.items())
            },
            "objectTypeCounts": {
                str(object_type): count
                for object_type, count in sorted(summary_type_counts.items())
            },
            "objectTypeLabels": {
                str(object_type): HIRC_OBJECT_TYPE_LABELS.get(object_type, f"type{object_type}")
                for object_type in sorted(summary_type_counts)
            },
            "evidenceBoundary": (
                "Exact serialized HIRC object-family counts. Event, Action, Sound, and "
                "types 5/6/7/9 use typed downward edges with reciprocal parent proof; "
                "type-6 flat value packages are emitted only when their complete v150 "
                "mapping and association tail consumes exactly, while distinct tails stay unresolved. "
                "Version-150 MusicSegment/Track/Switch/RanSeq nodes use bounded typed "
                "prefixes, exact track sources, and reciprocal music children; truncated, "
                "non-v150, and unresolved structures fail closed. Runtime switch, random, "
                "sequence, transition, and layer selection is not evaluated, and switch "
                "mapping evidence never prunes possible children without a runtime group value."
            ),
        })

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


def collect_existing_cutscene_audio_events(conv_dir: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for conv_path in sorted(conv_dir.glob("*.json")):
        payload = load_json_strict(conv_path, {})
        if not isinstance(payload, dict):
            continue
        cutscene = payload.get("cutscene")
        if not isinstance(cutscene, dict):
            continue
        key = str(payload.get("key") or conv_path.stem).strip()
        if not key:
            continue
        events: list[str] = []
        seen: set[str] = set()
        for raw_event in cutscene.get("audioEvents") or []:
            event = str(raw_event or "").strip()
            event_key = event.lower()
            if event and event_key not in seen:
                seen.add(event_key)
                events.append(event)
        if events:
            out[key] = events
    return out


def apply_cutscene_audio_source_overrides(
    cutscene_audio_events: dict[str, list[str]],
    conv_dir: Path,
    audio_source_overrides: dict[str, list[str]],
) -> dict[str, list[str]]:
    if not audio_source_overrides:
        return cutscene_audio_events

    source_events_by_key = collect_existing_cutscene_audio_events(conv_dir)
    merge_event_map(source_events_by_key, cutscene_audio_events)
    source_events_by_lower_key = {
        key.lower(): events
        for key, events in source_events_by_key.items()
    }

    override_events: dict[str, list[str]] = {}
    for target_key, source_keys in audio_source_overrides.items():
        target = str(target_key or "").strip()
        if not target:
            continue
        for source_key in source_keys:
            source = str(source_key or "").strip().lower()
            events = source_events_by_lower_key.get(source) or []
            if events:
                override_events.setdefault(target, []).extend(events)

    return merge_event_map(cutscene_audio_events, override_events)


def _event_name_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {
        str(value or "").strip().lower()
        for value in values
        if str(value or "").strip()
    }


def _audio_entry_file_exists(audio_root: Path, language: str, entry: dict[str, Any]) -> bool:
    path = entry_audio_path(audio_root, language, entry)
    return bool(str(path)) and path.is_file()


def event_media_inventory_fingerprint(
    audio_by_id: dict[str, dict[str, Any]],
) -> str:
    """Fingerprint decoded uint32 codec media used by HIRC traversal.

    AKPK External Source sectors use uint64 FNV path identities. They are
    instantiated by the External Source playback route and cannot be a fixed
    HIRC Sound media id, so their layout must not invalidate Event traversal.
    """
    rows = []
    for lookup_key, entry in audio_by_id.items():
        media_id = str(entry.get("id") or lookup_key).strip().lower()
        if not media_id.isdigit() or int(media_id) > 0xFFFFFFFF:
            continue
        rows.append({
            "id": media_id,
            "storageRoot": str(entry.get("storageRoot") or ""),
            "rel": normalize_posix(str(entry.get("rel") or "")).lower(),
            "bytes": int(entry.get("bytes") or 0),
        })
    encoded = json.dumps(
        sorted(rows, key=lambda row: (row["id"], row["storageRoot"], row["rel"])),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_cached_event_audio_index(
    language_root: Path,
    event_names: set[str],
    audio_root: Path,
    webui_root: Path,
    language: str,
    explicit_event_hashes: set[int] | None = None,
    expected_format: str | None = None,
    expected_media_inventory_fingerprint: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]] | None:
    """Reuse event-to-media links from the last audio index when complete."""
    payload = load_json_strict(language_root / "index.json", {})
    if not isinstance(payload, dict):
        return None
    if expected_format and str(payload.get("format") or "").lower() != expected_format.lower():
        return None
    if int(payload.get("eventEvidenceSchemaVersion") or 0) < EVENT_EVIDENCE_SCHEMA_VERSION:
        return None
    raw_inventory = payload.get("wwiseEventInventory")
    expected_inventory_count = int(
        (payload.get("counts") or {}).get("wwiseEventObjectOccurrences") or 0
    )
    if (
        not isinstance(raw_inventory, list)
        or expected_inventory_count <= 0
        or len(raw_inventory) != expected_inventory_count
    ):
        return None
    if (
        expected_media_inventory_fingerprint
        and str(payload.get("eventMediaInventoryFingerprint") or "")
        != expected_media_inventory_fingerprint
    ):
        # Schema migration: older fingerprints included uint64 External
        # Source path ids. Recompute the codec-only fingerprint from the
        # authoritative cached entries before rejecting the Event cache.
        cached_entries = payload.get("entries") or []
        if not isinstance(cached_entries, list):
            return None
        cached_codec_fingerprint = event_media_inventory_fingerprint({
            f"cached:{index}": entry
            for index, entry in enumerate(cached_entries)
            if isinstance(entry, dict) and not entry.get("eventId")
        })
        if cached_codec_fingerprint != expected_media_inventory_fingerprint:
            return None
    wanted_names = {
        str(name or "").strip().lower()
        for name in event_names
        if str(name or "").strip()
    }
    wanted_hashes = {
        int(value) & 0xFFFFFFFF
        for value in (explicit_event_hashes or set())
        if int(value) & 0xFFFFFFFF
    }
    cached_names = _event_name_set(payload.get("eventNames"))
    cached_hashes = {
        int(value) & 0xFFFFFFFF
        for value in (
            payload.get("explicitEventHashes")
            or payload.get("projectileEventHashes")
            or []
        )
        if isinstance(value, int)
    }
    if wanted_names and (not cached_names or not wanted_names.issubset(cached_names)):
        return None
    if wanted_hashes and not wanted_hashes.issubset(cached_hashes):
        return None
    if not wanted_names and not wanted_hashes:
        return None

    event_audio_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in payload.get("events") or []:
        if not isinstance(entry, dict):
            continue
        event_key = str(entry.get("eventId") or entry.get("id") or "").strip().lower()
        try:
            event_hash = int(entry.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            event_hash = 0
        if event_key not in wanted_names and event_hash not in wanted_hashes:
            continue
        cached = dict(entry)
        cached.setdefault("storageRoot", entry_storage_root(cached, language))
        rel = normalize_posix(str(cached.get("rel") or ""))
        if rel:
            cached["rel"] = canonical_audio_rel(
                rel,
                cached.get("eventCategory") or event_audio_category(event_key),
            )
            apply_audio_category(cached)
        if not _audio_entry_file_exists(audio_root, language, cached):
            continue
        cached["src"] = served_audio_href(audio_root, webui_root, cached["storageRoot"], str(cached.get("rel") or ""))
        event_audio_by_id[event_key].append(cached)

    if not any(event_audio_by_id.values()):
        return None

    event_evidence = [
        entry
        for entry in (payload.get("eventEvidence") or [])
        if isinstance(entry, dict)
        and (
            str(entry.get("eventId") or "").strip().lower() in wanted_names
            or (
                isinstance(entry.get("eventHash"), int)
                and (int(entry.get("eventHash")) & 0xFFFFFFFF) in wanted_hashes
            )
        )
    ]
    return dict(event_audio_by_id), event_evidence


def snapshot_audio_file_stats(source_root: Path) -> dict[str, tuple[int, int]]:
    return {
        rel: (stat.st_size, stat.st_mtime_ns)
        for _path, rel, stat in scan_audio_files(source_root)
    }


def decode_jobs(args: argparse.Namespace) -> int:
    """Worker count for the WEM→FLAC decode pass."""
    requested = int(getattr(args, "decode_jobs", 0) or 0)
    return requested if requested > 0 else max(1, os.cpu_count() or 1)


def run_audio_dumper_once(
    args: argparse.Namespace,
    language_info: dict[str, str],
    output_root: Path,
    block: str,
    shared_output_root: Path | None,
    source_label: str,
    streaming_assets: Path,
    fallback_assets: Path | None,
) -> None:
    command = [
        str(args.audio_dumper),
        "audio",
        "--streaming-assets",
        str(streaming_assets),
        "--output",
        str(output_root),
        "--language",
        language_info["dumper"],
        "--format",
        AUDIO_OUTPUT_FORMAT,
        "--block",
        block,
        # The dumper's own default caps decoding at 8 workers regardless of the
        # host. Each worker is one vgmstream process plus an in-process FLAC
        # encoder, so the pass scales with the real core count.
        "--jobs",
        str(decode_jobs(args)),
    ]
    if shared_output_root is not None:
        command.extend(["--shared-output", str(shared_output_root)])
    if fallback_assets and fallback_assets.exists():
        command.extend(["--fallback-assets", str(fallback_assets)])

    print(f"Running [{source_label}]:", " ".join(f'"{part}"' if " " in part else part for part in command))
    subprocess.run(command, cwd=ROOT, check=True)


def run_audio_dumper(
    args: argparse.Namespace,
    language: str,
    language_info: dict[str, str],
) -> dict[tuple[str, str], dict[str, str]]:
    if args.skip_decode:
        return {}
    if not args.audio_dumper.exists():
        raise SystemExit(f"audio dumper not found: {args.audio_dumper}")
    if not args.streaming_assets.exists():
        raise SystemExit(f"StreamingAssets not found: {args.streaming_assets}")

    source_by_rel: dict[tuple[str, str], dict[str, str]] = {}
    block = args.block
    all_storages = (
        (SHARED_AUDIO_STORAGE, language)
        if block == "all"
        else (storage_root_for_block(block, language),)
    )
    for storage_root in all_storages:
        (args.audio_root / storage_root).mkdir(parents=True, exist_ok=True)

    persistent = args.fallback_assets if args.fallback_assets and args.fallback_assets.exists() else None
    if block == "all":
        decode_passes = [("all", "StreamingAssets", args.streaming_assets, persistent)]
        if persistent is not None and not same_resolved_path(persistent, args.streaming_assets):
            decode_passes.append(
                ("hotfix-audio", "Persistent HotfixAudio", persistent, args.streaming_assets)
            )
    elif block == "hotfix-audio" and persistent is not None:
        decode_passes = [(block, "Persistent HotfixAudio", persistent, args.streaming_assets)]
    else:
        decode_passes = [
            (block, source_label, streaming_assets, fallback_assets)
            for source_label, streaming_assets, fallback_assets in audio_vfs_sources(args)
        ]

    for pass_block, source_label, streaming_assets, fallback_assets in decode_passes:
        storages = (
            (SHARED_AUDIO_STORAGE, language)
            if pass_block == "all"
            else (storage_root_for_block(pass_block, language),)
        )
        output_root = (
            args.audio_root / language
            if pass_block in {"all", "voice"}
            else args.audio_root / SHARED_AUDIO_STORAGE
        )
        shared_output_root = args.audio_root / SHARED_AUDIO_STORAGE if pass_block == "all" else None
        dumper_language_info = (
            language_info
            if pass_block in {"all", "voice"}
            else LANGUAGES[SHARED_AUDIO_LANGUAGE]
        )
        before_by_storage = {
            storage_root: snapshot_audio_file_stats(args.audio_root / storage_root)
            for storage_root in storages
        }
        run_audio_dumper_once(
            args,
            dumper_language_info,
            output_root,
            pass_block,
            shared_output_root,
            source_label,
            streaming_assets,
            fallback_assets,
        )
        for storage_root in storages:
            after = snapshot_audio_file_stats(args.audio_root / storage_root)
            changed = 0
            for rel, stat in after.items():
                if before_by_storage[storage_root].get(rel) == stat:
                    continue
                metadata_block = (
                    combined_decode_source_block(storage_root, language, rel)
                    if pass_block == "all"
                    else pass_block
                )
                metadata = audio_source_metadata(metadata_block, language, language_info)
                metadata["storageRoot"] = storage_root
                source_by_rel[(storage_root, rel)] = metadata
                changed += 1
            summary_block = "voice" if storage_root == language else (
                "audio" if pass_block == "all" else pass_block
            )
            summary_metadata = audio_source_metadata(summary_block, language, language_info)
            print(
                f"Audio source map [{source_label}]: {changed:,} files tagged as "
                f"{summary_metadata['audioScope']} from {summary_metadata['sourceBlockLabel']} "
                f"under {storage_root}"
            )
    return source_by_rel


def append_audio_id_candidate(ids: list[str], seen: set[str], value: object) -> None:
    if isinstance(value, (list, tuple, set)):
        for item in value:
            append_audio_id_candidate(ids, seen, item)
        return
    audio_id = audio_id_from_path(str(value or "").strip())
    if audio_id and audio_id not in seen:
        seen.add(audio_id)
        ids.append(audio_id)


def line_audio_ids(line: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for field in ("voice", "audio", "voId", "audioId", "audioPath", "audioPaths", "audioDialogPath", "audioDialogPaths"):
        append_audio_id_candidate(ids, seen, line.get(field))
    debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
    source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
    for field in ("voId", "audioOverride", "audio", "audioId", "audioPath", "audioPaths", "audioDialogPath", "audioDialogPaths"):
        append_audio_id_candidate(ids, seen, source.get(field))
    return ids

def attach_audio_to_line(line: dict[str, Any], audio_entry: dict[str, Any]) -> bool:
    changed = False
    src = audio_entry.get("src") or ""
    if src and line.get("audioSrc") != src:
        line["audioSrc"] = src
        changed = True
    meta = {
        key: audio_entry.get(key)
        for key in AUDIO_META_KEYS
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
            for key in AUDIO_META_KEYS
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
        payload = load_json_strict(conv_path, {})
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
                "audioScope": entry.get("audioScope"),
                "sourceBlock": entry.get("sourceBlock"),
                "sourceBlockLabel": entry.get("sourceBlockLabel"),
                "sourceLanguage": entry.get("sourceLanguage"),
                "audioCategory": entry.get("audioCategory"),
                "audioCategoryDetail": entry.get("audioCategoryDetail"),
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
        payload = load_json_strict(conv_path, {})
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
                    entry["storyLineBindingCount"] = int(entry.get("storyLineBindingCount") or 0) + 1
                    entry["purposeKnowledgeStatus"] = "exactStoryLineBinding"
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
                    for variant in variants.values():
                        variant["storyLineBindingCount"] = int(variant.get("storyLineBindingCount") or 0) + 1
                        variant["purposeKnowledgeStatus"] = "exactStoryLineBinding"
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


# --- Wwise audio grouping ----------------------------------------------------
# Raw Wwise media start as hashed files. We keep source-bank provenance in
# metadata, but the exported browser-facing folders group by useful category:
# wwise/<sfx|voice_events|music|ambience|ui|cues|unknown>/<id>.

UNMAPPED_BANK_PRIORITY = ("main", "initial", "audit", "external", "hotfix")
UNMAPPED_SCOPE_PCK_PARENTS = {
    SHARED_AUDIO_STORAGE: ("main", "initial", "audit"),
    "CN": ("chinese",),
    "EN": ("english",),
    "JP": ("japanese",),
    "KR": ("korean",),
}


def unmapped_bank_for_pck_name(name: str) -> str:
    lower = PurePosixPath(str(name).replace("\\", "/")).name.lower()
    if "external_source" in lower:
        return "external"
    if lower.startswith("init"):
        return "initial"
    if lower.startswith("audit"):
        return "audit"
    if lower.startswith("hotfix"):
        return "hotfix"
    return "main"


def event_audio_category(event_id: Any) -> str:
    name = str(event_id or "").strip().lower()
    for prefix, category in EVENT_CATEGORY_PREFIXES.items():
        if name.startswith(prefix):
            return category
    return ""


def all_audio_pck_files(export_root: Path) -> list[Path]:
    roots = [
        export_root / "structured" / "Persistent" / "Data" / "Audio" / "PCK" / "Windows",
        export_root / "structured" / "StreamingAssets" / "Data" / "Audio" / "PCK" / "Windows",
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.pck")):
            key = normalize_posix(path.relative_to(root)).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
    return out


def build_media_bank_map(export_root: Path, scope_parents: tuple[str, ...]) -> dict[str, str]:
    """Map media-id -> source-bank folder by reading the AKPK indexes of the scope's PCKs."""
    parents = {parent.lower() for parent in scope_parents}
    out: dict[str, str] = {}
    for pck in all_audio_pck_files(export_root):
        if pck.parent.name.lower() not in parents:
            continue
        bank = unmapped_bank_for_pck_name(pck.name)
        rank = UNMAPPED_BANK_PRIORITY.index(bank)
        try:
            ids = iter_akpk_media_ids_from_bytes(pck.read_bytes(), normalize_posix(pck))
        except (OSError, ValueError):
            continue
        for media_id in ids:
            key = str(media_id)
            current = out.get(key)
            if current is None or rank < UNMAPPED_BANK_PRIORITY.index(current):
                out[key] = bank
    return out


def flat_unmapped_files(folder: Path) -> list[Path]:
    """Unmapped media sitting directly under unmapped/ (not yet in a bank subfolder)."""
    if not folder.exists():
        return []
    return [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ]


def prune_empty_audio_dirs(root: Path) -> int:
    """Remove folders left empty by a layout move, deepest first.

    ``os.walk`` bottom-up already reports each folder's remaining children, so
    only the folders that are actually empty are touched.  The previous
    ``rglob("*")`` scan stat-ed every one of the ~93k decoded media just to
    discard them, then issued a failing ``rmdir`` for every populated folder.
    """

    if not root.exists():
        return 0
    root_str = str(root)
    removed_dirs: set[str] = set()
    for current, dirnames, filenames in os.walk(root_str, topdown=False):
        if current == root_str or filenames:
            continue
        # ``os.walk`` listed the children before this pass deleted the empty
        # ones, so a folder that now holds only just-removed folders is empty
        # too.  Bottom-up order guarantees they were already visited.
        if any(os.path.join(current, name) not in removed_dirs for name in dirnames):
            continue
        try:
            os.rmdir(current)
        except OSError:
            continue
        removed_dirs.add(current)
    return len(removed_dirs)


def canonicalize_audio_layout(audio_root: Path, storage: str) -> dict[str, int]:
    """Move legacy decoded audio files into the browser-facing folder layout."""
    storage_root = audio_root / storage
    if not storage_root.exists():
        return {}
    counts: dict[str, int] = defaultdict(int)
    for path, rel, _stat in scan_audio_files(storage_root):
        canonical_rel = canonical_audio_rel(rel)
        if canonical_rel == rel:
            continue
        dest = audio_file_path(audio_root, storage, canonical_rel)
        if same_resolved_path(path, dest):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            counts["replaced"] += 1
        else:
            counts["moved"] += 1
        path.replace(dest)
    removed_dirs = prune_empty_audio_dirs(storage_root)
    if removed_dirs:
        counts["removedDirs"] = removed_dirs
    return dict(counts)


def regroup_unmapped_by_bank(
    audio_root: Path,
    storage: str,
    export_root: Path,
    dry_run: bool = False,
) -> tuple[dict[str, int], dict[tuple[str, str], dict[str, str]]]:
    """Tag flat unmapped/<id> media with source-bank provenance before canonicalizing paths."""
    folder = audio_root / storage / "unmapped"
    flat = flat_unmapped_files(folder)
    if not flat:
        return {}, {}
    scope_parents = UNMAPPED_SCOPE_PCK_PARENTS.get(storage, ())
    bank_map = build_media_bank_map(export_root, scope_parents) if scope_parents else {}
    counts: dict[str, int] = defaultdict(int)
    metadata_by_rel: dict[tuple[str, str], dict[str, str]] = {}
    storage_root = audio_root / storage
    for path in flat:
        bank = bank_map.get(path.stem) or "unknown"
        dest = folder / bank / path.name
        old_rel = normalize_posix(path.relative_to(storage_root))
        new_rel = normalize_posix(dest.relative_to(storage_root))
        metadata = {"storageRoot": storage, "sourceBank": bank}
        metadata_by_rel[(storage, old_rel)] = metadata
        metadata_by_rel[(storage, new_rel)] = metadata
        counts[bank] += 1
        if dry_run or dest == path:
            continue
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        path.rename(dest)
    return dict(counts), metadata_by_rel


def regroup_unmapped_by_category(
    audio_root: Path,
    webui_root: Path,
    audio_by_id: dict[str, dict[str, Any]],
    event_entries: list[dict[str, Any]],
    language: str,
) -> int:
    """Move event-resolved Wwise media into wwise/<category>/<id> and tag entries."""
    media_category: dict[str, str] = {}
    entries_by_media: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in event_entries:
        media_id = entry.get("mediaId")
        if media_id is None:
            continue
        key = str(media_id)
        entries_by_media[key].append(entry)
        category = event_audio_category(entry.get("eventId") or entry.get("id"))
        if category:
            media_category.setdefault(key, category)
    if not media_category:
        return 0

    moved = 0
    for media_id, category in media_category.items():
        targets = list(entries_by_media.get(media_id) or [])
        canonical = audio_by_id.get(media_id)
        if canonical is not None and canonical not in targets:
            targets.append(canonical)
        ref = canonical or (targets[0] if targets else None)
        if ref is None:
            continue
        rel = normalize_posix(str(ref.get("rel") or ""))
        parts = PurePosixPath(rel).parts
        if not parts:
            continue

        bank = str(ref.get("sourceBank") or "")
        if parts[0] == "wwise" and len(parts) >= 3:
            new_rel = canonical_audio_rel(rel, category)
            needs_move = new_rel != rel
        elif parts[0] == "unmapped" and len(parts) >= 3:
            bank = bank or parts[1]
            file_name = parts[-1]
            new_rel = normalize_posix(PurePosixPath("wwise", wwise_folder_for_event_category(category), file_name))
            needs_move = True
        else:
            continue

        storage = entry_storage_root(ref, language)
        if needs_move:
            src_path = audio_file_path(audio_root, storage, rel)
            dst_path = audio_file_path(audio_root, storage, new_rel)
            if not src_path.exists():
                continue
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if not same_resolved_path(src_path, dst_path):
                src_path.replace(dst_path)
                moved += 1
        new_src = served_audio_href(audio_root, webui_root, storage, new_rel)
        for entry in targets:
            entry["rel"] = new_rel
            entry["src"] = new_src
            entry["eventCategory"] = category
            if bank:
                entry["sourceBank"] = bank
            apply_audio_category(entry)
    return moved


def suppress_redundant_unknown_audio_occurrences(
    audio_root: Path,
    generic_audio: dict[str, dict[str, Any]],
    dialog_audio: dict[str, dict[str, Any]],
    language: str,
) -> dict[str, int]:
    """Drop byte-identical pre-category copies from the generated index.

    Repeated decode runs may recreate ``wwise/unknown/<mediaId>`` after an
    earlier run filed the same bytes under a resolved category or AudioDialog
    path. Keep the files recoverable on disk, but index one logical media
    occurrence. Same-id rows with different bytes, storage roots, or no
    stronger categorized/authored peer are preserved as real collisions.
    """

    grouped: dict[tuple[str, str], list[tuple[str, dict[str, Any], bool]]] = defaultdict(list)
    for key, entry in generic_audio.items():
        grouped[(entry_storage_root(entry, language), str(entry.get("id") or ""))].append((key, entry, False))
    for key, entry in dialog_audio.items():
        grouped[(entry_storage_root(entry, language), str(entry.get("id") or ""))].append((key, entry, True))
    digest_cache: dict[Path, str] = {}

    def digest(entry: dict[str, Any], storage: str) -> str:
        path = audio_file_path(audio_root, storage, normalize_posix(str(entry.get("rel") or "")))
        if not path.is_file():
            return ""
        if path not in digest_cache:
            digest_cache[path] = file_sha256(path)
        return digest_cache[path]

    suppressed = 0
    compared = 0
    for (storage, _media_id), rows in grouped.items():
        if len(rows) < 2:
            continue
        preferred = [
            row for row in rows
            if row[2]
            or str(row[1].get("audioCategory") or "unknown") != "unknown"
            or "/unknown/" not in f"/{normalize_posix(str(row[1].get('rel') or '')).lower()}"
        ]
        if not preferred:
            continue
        preferred.sort(key=lambda row: (
            not row[2],
            str(row[1].get("audioCategory") or "unknown") == "unknown",
            normalize_posix(str(row[1].get("rel") or "")),
        ))
        reference = preferred[0][1]
        reference_bytes = int(reference.get("bytes") or -1)
        reference_digest = ""
        for key, entry, is_dialog in rows:
            if is_dialog or entry is reference:
                continue
            rel = f"/{normalize_posix(str(entry.get('rel') or '')).lower()}"
            if str(entry.get("audioCategory") or "unknown") != "unknown" or "/unknown/" not in rel:
                continue
            if int(entry.get("bytes") or -2) != reference_bytes:
                continue
            compared += 1
            if not reference_digest:
                reference_digest = digest(reference, storage)
            if not reference_digest or digest(entry, storage) != reference_digest:
                continue
            if key in generic_audio:
                generic_audio.pop(key)
                suppressed += 1
    external_dialog_compared = 0
    external_dialog_suppressed = 0
    dialog_by_external_id: dict[tuple[str, int], dict[str, Any]] = {}
    dumper_language = str(LANGUAGES.get(language, {}).get("dumper") or language.lower())
    for entry in dialog_audio.values():
        dialog_path = str(entry.get("audioDialogPath") or "").strip()
        if not dialog_path:
            continue
        storage = entry_storage_root(entry, language)
        dialog_by_external_id[(storage, audio_dialog_external_media_id(dialog_path, dumper_language))] = entry
    for key, entry in list(generic_audio.items()):
        raw_id = str(entry.get("id") or "")
        # Externals-sector ids are uint64 FNV path hashes. Older generated
        # wwise/unknown paths may predate sourceBank tagging, so the exact
        # AudioDialog hash join is authoritative; do not require that mutable
        # layout metadata to still be present.
        if not raw_id.isdigit() or int(raw_id) <= 0xFFFFFFFF:
            continue
        storage = entry_storage_root(entry, language)
        reference = dialog_by_external_id.get((storage, int(raw_id)))
        if reference is None:
            continue
        if int(entry.get("bytes") or -1) != int(reference.get("bytes") or -2):
            continue
        external_dialog_compared += 1
        if digest(entry, storage) != digest(reference, storage):
            continue
        generic_audio.pop(key, None)
        external_dialog_suppressed += 1
    recovered_external_identities = 0
    for entry in generic_audio.values():
        raw_id = str(entry.get("id") or "")
        if not raw_id.isdigit() or int(raw_id) <= 0xFFFFFFFF:
            continue
        identity = (RECOVERED_EXTERNAL_MEDIA_IDENTITIES.get(language) or {}).get(int(raw_id))
        if not identity:
            continue
        authored_path = str(identity["path"])
        if audio_dialog_external_media_id(authored_path, dumper_language) != int(raw_id):
            raise SystemExit(
                f"Recovered External Source path hash mismatch for media {raw_id}: {authored_path}"
            )
        entry.update({
            "externalMediaIdentityStatus": "recoveredAuthoredPathHash",
            "externalAuthoredAudioId": identity["audioId"],
            "externalAuthoredPath": authored_path,
            "externalIdentityEvidence": identity["evidence"],
            "identityOnlyPlaybackPlacementStatus": identity["playbackPlacementStatus"],
            "audioCategory": "story_voice",
            "audioCategoryDetail": "hongshan",
        })
        recovered_external_identities += 1
    return {
        "contentIdenticalDuplicateOccurrencesCompared": compared,
        "contentIdenticalUnknownOccurrencesSuppressed": suppressed,
        "audioDialogExternalCopiesCompared": external_dialog_compared,
        "audioDialogExternalCopiesSuppressed": external_dialog_suppressed,
        "recoveredOrphanExternalMediaIdentities": recovered_external_identities,
    }


def build_audio(args: argparse.Namespace) -> int:
    args.export_root = args.export_root.resolve()
    args.webui_root = args.webui_root.resolve()
    args.audio_root = args.audio_root.resolve()
    language = args.language.upper()
    language_info = LANGUAGES[language]
    shared_root = args.audio_root / SHARED_AUDIO_STORAGE
    language_root = args.audio_root / language
    if args.skip_decode and not has_decoded_audio_in_roots(shared_root, language_root):
        print(
            f"Audio build [{language}]: skipped "
            f"(no decoded audio files at {shared_root} or {language_root})"
        )
        return 0
    language_root.mkdir(parents=True, exist_ok=True)

    started = time.time()
    stage = AudioStageTimer()
    lua_audio_payload = load_lua_audio_reference_cache(
        args,
        refresh=bool(args.refresh_lua_audio or not args.skip_decode),
    )
    lua_audio_references = [
        row
        for row in lua_audio_payload.get("references") or []
        if isinstance(row, dict)
    ]
    lua_post_event_names = {
        str(row.get("name") or "").strip().lower()
        for row in lua_audio_references
        if row.get("kind") == "luaPostEvent" and str(row.get("name") or "").strip()
    }
    stage.mark("luaAudioReferenceCache")
    prior_source_by_rel = prior_source_metadata_by_rel(language_root, language)
    stage.mark("priorSourceMetadata")
    decoded_source_by_rel = run_audio_dumper(args, language, language_info)
    stage.mark("decode")

    for regroup_storage in (SHARED_AUDIO_STORAGE, language):
        bank_counts, bank_metadata = regroup_unmapped_by_bank(args.audio_root, regroup_storage, args.export_root)
        merge_source_metadata_by_rel(decoded_source_by_rel, bank_metadata)
        if bank_counts:
            summary = ", ".join(f"{bank}:{count:,}" for bank, count in sorted(bank_counts.items()))
            print(f"Audio source-bank tagging [{regroup_storage}]: {summary}")

    stage.mark("regroupUnmappedByBank")
    prior_source_by_rel = canonicalized_source_metadata_by_rel(prior_source_by_rel)
    decoded_source_by_rel = canonicalized_source_metadata_by_rel(decoded_source_by_rel)
    for layout_storage in (SHARED_AUDIO_STORAGE, language):
        layout_counts = canonicalize_audio_layout(args.audio_root, layout_storage)
        moved = int(layout_counts.get("moved", 0))
        replaced = int(layout_counts.get("replaced", 0))
        removed_dirs = int(layout_counts.get("removedDirs", 0))
        if moved or replaced or removed_dirs:
            print(
                f"Audio layout [{layout_storage}]: {moved:,} moved, "
                f"{replaced:,} replaced, {removed_dirs:,} old empty folders removed"
            )

    stage.mark("canonicalizeAudioLayout")
    audio_dialog_paths = find_audio_dialog_tables(args.export_root)
    stage.mark("findAudioDialogTables")
    shared_audio = collect_audio_files(
        args.audio_root,
        args.webui_root,
        shared_root,
        SHARED_AUDIO_STORAGE,
        language,
        language_info,
        decoded_source_by_rel,
        prior_source_by_rel,
    )
    language_audio = collect_audio_files(
        args.audio_root,
        args.webui_root,
        language_root,
        language,
        language,
        language_info,
        decoded_source_by_rel,
        prior_source_by_rel,
    )
    stage.mark("collectAudioFiles")
    generic_audio = merge_audio_file_indexes(shared_audio, language_audio)
    dialog_audio = build_dialog_audio_index(
        audio_dialog_paths,
        args.audio_root,
        args.webui_root,
        language_root,
        language,
        language_info,
        ".flac",
    )
    # Normalize the logical media inventory before computing the Event-cache
    # fingerprint. Otherwise the cache compares an unsuppressed physical scan
    # with the suppressed inventory stored by the previous build and needlessly
    # reparses every Wwise bank on every --skip-decode run.
    stage.mark("buildDialogAudioIndex")
    duplicate_suppression_stats = suppress_redundant_unknown_audio_occurrences(
        args.audio_root,
        generic_audio,
        dialog_audio,
        language,
    )
    if duplicate_suppression_stats["contentIdenticalUnknownOccurrencesSuppressed"]:
        print(
            "Audio index: suppressed "
            f"{duplicate_suppression_stats['contentIdenticalUnknownOccurrencesSuppressed']:,} "
            "byte-identical unknown-path duplicates"
        )
    if duplicate_suppression_stats["audioDialogExternalCopiesSuppressed"]:
        print(
            "Audio index: suppressed "
            f"{duplicate_suppression_stats['audioDialogExternalCopiesSuppressed']:,} "
            "exact AudioDialog external-id path copies"
        )
    stage.mark("suppressRedundantOccurrences")
    audio_by_id = {**generic_audio, **dialog_audio}
    media_inventory_fingerprint = event_media_inventory_fingerprint(audio_by_id)
    stage.mark("mediaInventoryFingerprint")

    conv_dir = args.webui_root / "data" / "lang" / language / "conv"
    if not conv_dir.exists():
        raise SystemExit(f"Conversation directory not found: {conv_dir}")
    table_event_names, table_event_hashes = collect_table_audio_events(args.export_root)
    stage.mark("collectTableAudioEvents")
    event_name_source_sets: dict[str, set[str]] = {
        "storyOrCoreAudioTable": collect_audio_event_names(conv_dir, args.export_root),
        "typedAudioTableOrConfig": table_event_names,
        "luaPostEvent": set(lua_post_event_names),
    }
    stage.mark("collectAudioEventNames")
    event_names = set().union(*event_name_source_sets.values())
    metadata_path = args.game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    if not metadata_path.is_file():
        cached_metadata_path = args.export_root / "recovered" / "il2cpp" / "global-metadata.dat"
        metadata_path = cached_metadata_path if cached_metadata_path.is_file() else None
    binary_managed_event_names = {
        name for name in collect_metadata_audio_literals(metadata_path)
        if not is_rtpc_parameter_name(name)
    }


    stage.mark("collectMetadataAudioLiterals")
    event_name_source_sets["managedStringLiteral"] = set(binary_managed_event_names)
    event_names.update(binary_managed_event_names)
    fmv_attach_overrides = load_narrative_video_attach_overrides(args.webui_root)
    audio_source_overrides = load_narrative_video_audio_source_overrides(args.webui_root)
    # The three cutscene collectors resolve disjoint subsets of the same audio
    # playables, so their union is resolved once against the published object
    # index instead of streaming that index three times.
    # An export without any audio playable leaves every collector empty anyway,
    # so fall back to their own resolution rather than hand them an empty map.
    cutscene_playable_ids = cutscene_audio_playable_path_ids(args.export_root)
    cutscene_playable_json = (
        mono_behaviour_json_by_path_id(args.export_root, cutscene_playable_ids)
        if cutscene_playable_ids
        else None
    )
    cutscene_audio_events = collect_fmv_cutscene_audio_events(
        args.export_root,
        language_info,
        fmv_attach_overrides,
        by_path_id=cutscene_playable_json,
    )
    merge_event_map(
        cutscene_audio_events,
        collect_timeline_cutscene_audio_events(args.export_root, cutscene_playable_json),
        collect_levelseq_cutscene_audio_events(args.export_root, cutscene_playable_json),
    )
    apply_cutscene_audio_source_overrides(
        cutscene_audio_events,
        conv_dir,
        audio_source_overrides,
    )
    cutscene_event_names = {
        str(event or "").strip()
        for events in cutscene_audio_events.values()
        for event in events
        if str(event or "").strip()
    }
    stage.mark("collectCutsceneAudioEvents")
    event_name_source_sets["cutsceneTimeline"] = cutscene_event_names
    event_names.update(cutscene_event_names)
    gameplay_audio_references = collect_gameplay_audio_references(
        args.webui_root,
        args.export_root,
        language,
    )
    stage.mark("collectGameplayAudioReferences")
    gameplay_event_names = set(gameplay_audio_references.get("eventNames") or set())
    event_name_source_sets["gameplayReference"] = gameplay_event_names
    event_names.update(gameplay_event_names)
    projectile_event_hashes = projectile_sound_hashes(args.webui_root)
    explicit_event_hashes = projectile_event_hashes | table_event_hashes
    explicit_event_names_by_hash = {
        event_hash: (
            projectile_event_key(event_hash)
            if event_hash in projectile_event_hashes
            else hashed_event_key(event_hash)
        )
        for event_hash in explicit_event_hashes
    }
    cached_event_index = (
        load_cached_event_audio_index(
            language_root,
            event_names,
            args.audio_root,
            args.webui_root,
            language,
            explicit_event_hashes,
            expected_format=AUDIO_OUTPUT_FORMAT,
            expected_media_inventory_fingerprint=media_inventory_fingerprint,
        )
        if args.skip_decode and not args.refresh_hirc
        else None
    )
    stage.mark("loadCachedEventAudioIndex")
    hirc_summary: dict[str, Any] = {}
    wwise_event_inventory: list[dict[str, Any]] = []
    if cached_event_index is not None:
        event_audio_by_id, event_evidence = cached_event_index
        prior_index = load_json_strict(language_root / "index.json", {})
        if isinstance(prior_index, dict) and isinstance(prior_index.get("hircSummary"), dict):
            hirc_summary = dict(prior_index["hircSummary"])
        if isinstance(prior_index, dict) and isinstance(prior_index.get("wwiseEventInventory"), list):
            wwise_event_inventory = list(prior_index["wwiseEventInventory"])
        print("Audio events: reused existing event-media index")
    else:
        event_audio_by_id, event_evidence = collect_event_audio_index(
            event_names,
            audio_by_id,
            args,
            explicit_event_hashes,
            explicit_event_names_by_hash,
            hirc_summary,
            wwise_event_inventory,
        )
    stage.mark("eventAudioIndex")
    audio_dialog_wwise_event_aliases = collect_audio_dialog_wwise_event_aliases(
        audio_dialog_paths,
        wwise_event_inventory,
    )
    voice_table_wwise_event_aliases = collect_voice_table_wwise_event_aliases(
        args.export_root,
        wwise_event_inventory,
    )
    typed_ui_table_wwise_event_aliases = collect_typed_ui_table_wwise_event_aliases(
        args.export_root,
        wwise_event_inventory,
    )
    sns_voice_wwise_event_aliases = collect_sns_voice_wwise_event_aliases(
        args.export_root,
        wwise_event_inventory,
    )
    skill_id_dictionary_wwise_event_aliases = collect_skill_id_dictionary_wwise_event_aliases(
        args.export_root,
        wwise_event_inventory,
    )
    recovered_alias_rows = [
        *audio_dialog_wwise_event_aliases,
        *voice_table_wwise_event_aliases,
        *typed_ui_table_wwise_event_aliases,
        *sns_voice_wwise_event_aliases,
        *skill_id_dictionary_wwise_event_aliases,
    ]
    audio_dialog_alias_hashes = {
        int(row["eventHash"]) for row in audio_dialog_wwise_event_aliases
    }
    recovered_alias_hashes = set(audio_dialog_alias_hashes)
    recovered_alias_hashes.update(
        int(row["eventHash"]) for row in voice_table_wwise_event_aliases
    )
    typed_ui_alias_hashes = {
        int(row["eventHash"]) for row in typed_ui_table_wwise_event_aliases
    }
    recovered_alias_hashes.update(typed_ui_alias_hashes)
    sns_voice_alias_hashes = {
        int(row["eventHash"]) for row in sns_voice_wwise_event_aliases
    }
    recovered_alias_hashes.update(sns_voice_alias_hashes)
    skill_id_dictionary_alias_hashes = {
        int(row["eventHash"]) for row in skill_id_dictionary_wwise_event_aliases
    }
    recovered_alias_hashes.update(skill_id_dictionary_alias_hashes)
    event_names.update(
        str(row["name"]) for row in recovered_alias_rows
    )
    event_name_source_sets["recoveredCurrentWwiseAlias"] = {
        str(row["name"]) for row in recovered_alias_rows
    }
    event_name_sources: dict[str, list[str]] = defaultdict(list)
    for source_kind, names in event_name_source_sets.items():
        for name in names:
            event_name_sources[str(name).strip().lower()].append(source_kind)
    for row in wwise_event_inventory:
        if (
            isinstance(row, dict)
            and isinstance(row.get("eventHash"), int)
            and (int(row["eventHash"]) & 0xFFFFFFFF) in recovered_alias_hashes
        ):
            event_hash = int(row["eventHash"]) & 0xFFFFFFFF
            row["eventIdentityStatus"] = (
                "audioDialogPathNameRecovered"
                if event_hash in audio_dialog_alias_hashes
                else "typedUiTableEventNameRecovered"
                if event_hash in typed_ui_alias_hashes
                else "snsVoiceEventNameRecovered"
                if event_hash in sns_voice_alias_hashes
                else "skillIdDictionaryEventNameRecovered"
                if event_hash in skill_id_dictionary_alias_hashes
                else "typedVoiceTableEventNameRecovered"
            )
    # Every observed-string source is exhausted by this point, so the Events
    # still without a name are regenerated from the grammar those names share.
    stage.mark("wwiseEventAliases")
    grammar_event_name_recovery = name_recovery.recover_event_names(
        event_names,
        wwise_event_inventory,
        # Only alias hashes are excluded: they already carry a proven name.
        # Projectile/table hashes have a known caller but still no spelling,
        # so they stay in the target set.
        named_event_hashes=recovered_alias_hashes,
    )
    grammar_recovered_wwise_event_names = list(
        grammar_event_name_recovery.get("entries") or []
    )
    grammar_recovered_name_hashes = {
        int(row["eventHash"]) for row in grammar_recovered_wwise_event_names
    }
    event_names.update(
        str(row["name"]) for row in grammar_recovered_wwise_event_names
    )
    event_name_source_sets["grammarHashPreimage"] = {
        str(row["name"]) for row in grammar_recovered_wwise_event_names
    }
    for name in event_name_source_sets["grammarHashPreimage"]:
        event_name_sources[name.strip().lower()].append("grammarHashPreimage")
    for row in wwise_event_inventory:
        if (
            isinstance(row, dict)
            and isinstance(row.get("eventHash"), int)
            and (int(row["eventHash"]) & 0xFFFFFFFF) in grammar_recovered_name_hashes
        ):
            row["eventIdentityStatus"] = "grammarHashPreimageNameRecovered"
    stage.mark("grammarEventNameRecovery")
    event_entries = [
        entry
        for entries in event_audio_by_id.values()
        for entry in entries
    ]
    audio_by_rel = {
        (entry_storage_root(entry, language), normalize_posix(str(entry.get("rel") or ""))): entry
        for entry in generic_audio.values()
        if entry.get("rel")
    }
    backfill_event_source_metadata(event_entries, audio_by_id, audio_by_rel, language)
    audio_by_id.update({
        str(entry.get("eventId") or entry.get("id") or "").lower(): entry
        for entry in event_entries
        if entry.get("eventId") or entry.get("id")
    })
    stage.mark("backfillEventSourceMetadata")
    category_moved = regroup_unmapped_by_category(
        args.audio_root, args.webui_root, audio_by_id, event_entries, language
    )
    if category_moved:
        print(f"Audio layout: {category_moved:,} Wwise files filed under event-category folders")
    # Category filing mutates canonical generic entries and their paths. Store
    # the post-layout fingerprint so the next --skip-decode run does not
    # invalidate an otherwise complete Event cache merely because this same
    # build moved a media occurrence to its recovered category.
    media_inventory_fingerprint = event_media_inventory_fingerprint({
        **generic_audio,
        **dialog_audio,
    })
    stage.mark("regroupUnmappedByCategory")
    source_summary = summarize_audio_sources(list(generic_audio.values()))
    link_stats = link_conversation_audio(conv_dir, audio_by_id, event_audio_by_id, cutscene_audio_events)
    stage.mark("linkConversationAudio")
    projectile_link_stats = write_projectile_audio_sidecar(
        args.webui_root,
        language,
        event_audio_by_id,
        event_evidence,
    )
    gameplay_link_stats = link_gameplay_audio(
        args.webui_root,
        language,
        gameplay_audio_references,
        event_audio_by_id,
        event_evidence,
        dialog_audio,
    )

    stage.mark("linkGameplayAudio")
    index_payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": language,
        "dumperLanguage": language_info["dumper"],
        "format": AUDIO_OUTPUT_FORMAT,
        "eventEvidenceSchemaVersion": EVENT_EVIDENCE_SCHEMA_VERSION,
        "eventMediaInventoryFingerprint": media_inventory_fingerprint,
        "block": args.block,
        "decodeBlocks": list(selected_audio_blocks(args.block)),
        "sourceSummary": source_summary,
        "audioDialogTable": display_path(audio_dialog_paths[0]),
        "audioDialogTables": [display_path(path) for path in audio_dialog_paths],
        "counts": {
            "files": len(generic_audio),
            "sharedFiles": int(source_summary.get("byScope", {}).get("shared", 0)),
            "languageFiles": int(source_summary.get("byScope", {}).get("language", 0)),
            "unknownSourceFiles": int(source_summary.get("byScope", {}).get("unknown", 0)),
            "dialogAudio": len(dialog_audio),
            "eventNames": len(event_names),
            "eventAudio": len(event_entries),
            "eventEvidence": len(event_evidence),
            "wwiseEventObjectOccurrences": len(wwise_event_inventory),
            "wwiseEventObjectHashes": len({
                int(row.get("eventHash") or 0)
                for row in wwise_event_inventory
                if int(row.get("eventHash") or 0)
            }),
            "wwiseEventObjectsWithoutRecoveredTriggerName": len({
                int(row.get("eventHash") or 0)
                for row in wwise_event_inventory
                if row.get("eventIdentityStatus") == "wwiseObjectWithoutRecoveredTriggerName"
                and int(row.get("eventHash") or 0)
            }),
            "audioDialogWwiseEventAliases": len(audio_dialog_wwise_event_aliases),
            "voiceTableWwiseEventAliases": len(voice_table_wwise_event_aliases),
            "typedUiTableWwiseEventAliases": len(typed_ui_table_wwise_event_aliases),
            "snsVoiceWwiseEventAliases": len(sns_voice_wwise_event_aliases),
            "skillIdDictionaryWwiseEventAliases": len(skill_id_dictionary_wwise_event_aliases),
            "grammarRecoveredWwiseEventNames": len(grammar_recovered_wwise_event_names),
            "grammarRecoveredWwiseEventNameCandidates": int(
                grammar_event_name_recovery.get("candidateCount") or 0
            ),
            "grammarRecoveredWwiseEventNameIsolatedPreimages": int(
                grammar_event_name_recovery.get("isolatedCount") or 0
            ),
            "grammarRecoveredWwiseEventNameAmbiguousHashes": int(
                grammar_event_name_recovery.get("ambiguousHashCount") or 0
            ),
            "grammarRecoveredWwiseEventNameExpectedCoincidences": float(
                grammar_event_name_recovery.get("expectedCoincidentalPreimages") or 0.0
            ),
            **duplicate_suppression_stats,
            "luaPostEventNames": len(lua_post_event_names),
            "luaPostEventContexts": sum(
                row.get("kind") == "luaPostEvent" for row in lua_audio_references
            ),
            "luaRtpcParameterContexts": sum(
                row.get("kind") == "luaRtpcParameter" for row in lua_audio_references
            ),
            "luaAudioCueContexts": sum(
                row.get("kind") == "luaAudioCue" for row in lua_audio_references
            ),
            **projectile_link_stats,
            **gameplay_link_stats,
            **link_stats,
        },
        "eventNames": sorted(event_names),
        "eventNameSources": {
            name: sorted(set(sources))
            for name, sources in sorted(event_name_sources.items())
        },
        "projectileEventHashes": sorted(projectile_event_hashes),
        "tableEventHashes": sorted(table_event_hashes),
        "explicitEventHashes": sorted(explicit_event_hashes),
        "binaryManagedEventNames": sorted(binary_managed_event_names),
        "audioDialogWwiseEventAliases": audio_dialog_wwise_event_aliases,
        "voiceTableWwiseEventAliases": voice_table_wwise_event_aliases,
        "typedUiTableWwiseEventAliases": typed_ui_table_wwise_event_aliases,
        "snsVoiceWwiseEventAliases": sns_voice_wwise_event_aliases,
        "skillIdDictionaryWwiseEventAliases": skill_id_dictionary_wwise_event_aliases,
        "grammarRecoveredWwiseEventNames": grammar_recovered_wwise_event_names,
        # ``entries`` are published separately above as the alias list; keep the
        # summary, the statistics, and the uncorroborated preimages that are
        # deliberately not promoted to an Event name.
        "grammarEventNameRecovery": {
            key: value
            for key, value in grammar_event_name_recovery.items()
            if key != "entries"
        },
        "luaAudioReferenceSummary": lua_audio_payload.get("summary") or {},
        "luaAudioReferences": lua_audio_references,
        # Persist the exact Timeline/LevelSequence/FMV evidence used by the
        # semantic build. Story cards intentionally do not contain every raw
        # cutscene placement, so rebuilding semantics from their published
        # audioEvents alone would silently discard valid playback contexts.
        "cutsceneAudioEvents": {
            key: list(events)
            for key, events in sorted(cutscene_audio_events.items())
        },
        "hircSummary": hirc_summary,
        "eventEvidence": event_evidence,
        "wwiseEventInventory": wwise_event_inventory,
        "events": sorted(event_entries, key=lambda item: (str(item.get("eventId") or ""), int(item.get("mediaId") or 0))),
        "entries": sorted(audio_by_id.values(), key=lambda item: (str(item.get("id") or ""), str(item.get("rel") or ""))),
    }
    stage.mark("buildIndexPayload")
    json_dump(language_root / "index.json", index_payload)
    stage.mark("writeIndexJson")
    semantic_payload = build_audio_semantic_data(
        index_payload,
        language=language,
        export_root=args.export_root,
        webui_root=args.webui_root,
        metadata_path=metadata_path,
        gameassembly_path=args.game_root.parent / "GameAssembly.dll",
        cutscene_events=cutscene_audio_events,
    )

    stage.mark("buildAudioSemanticData")
    print_audio_stage_summary()
    elapsed = time.time() - started
    scope_counts = source_summary.get("byScope", {})
    print(
        "Audio index:"
        f" {len(generic_audio):,} files,"
        f" {int(scope_counts.get('shared', 0)):,} shared/"
        f"{int(scope_counts.get('language', 0)):,} language/"
        f"{int(scope_counts.get('unknown', 0)):,} unknown-source,"
        f" {len(dialog_audio):,} AudioDialog matches,"
        f" {len(event_entries):,} event media links,"
        f" {projectile_link_stats['projectileSoundRefsLinked']:,}/{projectile_link_stats['projectileSoundRefs']:,} projectile sound refs linked,"
        f" {gameplay_link_stats['gameplayAudioRefsLinked']:,}/{gameplay_link_stats['gameplayAudioRefs']:,} gameplay audio refs emitted/discovered,"
        f" {link_stats['lineAudioLinked']:,}/{link_stats['lineAudioRefs']:,} line refs linked,"
        f" {link_stats['conversationAudioEventsLinked']:,}/{link_stats['conversationAudioEvents']:,} conversation event refs linked,"
        f" {link_stats['cutsceneAudioEventsLinked']:,}/{link_stats['cutsceneAudioEvents']:,} cutscene event refs linked,"
        f" {link_stats['conversationFilesChanged']:,} conv files updated,"
        f" {semantic_payload['counts']['runtimeSystems']:,} binary-validated runtime systems"
        f" in {elapsed:.1f}s"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=sorted(LANGUAGES), default="CN")
    parser.add_argument(
        "--block",
        choices=("all", "voice", "audio", "initial-audio", "audit-audio", "hotfix-audio"),
        default="all",
    )
    parser.add_argument("--skip-decode", action="store_true", help="Only rebuild the audio index and story links.")
    parser.add_argument(
        "--refresh-hirc",
        action="store_true",
        help=(
            "Reparse original Wwise bank HIRC evidence while reusing decoded "
            "audio files; requires --skip-decode."
        ),
    )
    parser.add_argument(
        "--refresh-lua-audio",
        action="store_true",
        help="Refresh decrypted Lua audio-call evidence even when --skip-decode is used.",
    )
    parser.add_argument(
        "--audio-dumper",
        type=Path,
        default=DEFAULT_AUDIO_DUMPER,
        help="Path to AnimeStudio CLI for audio extraction.",
    )
    parser.add_argument(
        "--decode-jobs",
        type=int,
        default=0,
        help=(
            "Parallel WEM decode workers passed to the AnimeStudio audio "
            "dumper. Default: one per logical CPU."
        ),
    )
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--streaming-assets", type=Path, default=None)
    parser.add_argument("--fallback-assets", type=Path, default=None)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--webui-root", type=Path, default=DEFAULT_WEBUI_ROOT)
    parser.add_argument(
        "--audio-root",
        type=Path,
        default=None,
        help="Decoded audio root containing shared and per-language folders. Default: <export-root>/structured/Audio.",
    )
    args = parser.parse_args(argv)
    if args.streaming_assets is None:
        args.streaming_assets = args.game_root / "StreamingAssets"
    if args.fallback_assets is None:
        args.fallback_assets = args.game_root / "Persistent"
    if args.audio_root is None:
        args.audio_root = args.export_root / "structured" / "Audio"
    if args.refresh_hirc and not args.skip_decode:
        parser.error("--refresh-hirc requires --skip-decode")
    return args


if __name__ == "__main__":
    raise SystemExit(build_audio(parse_args()))
