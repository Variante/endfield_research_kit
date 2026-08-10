#!/usr/bin/env python3
"""Decode story audio into export_full and link playable files into WebUI data."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import time
from collections import Counter, defaultdict, deque
from pathlib import Path, PurePosixPath
from struct import unpack_from
from typing import Any

try:
    from convert_audio_to_flac import convert_audio_root
except ImportError:  # Imported as scripts.build_audio from repository-root tests.
    from scripts.convert_audio_to_flac import convert_audio_root

try:
    from build_audio_semantics import (
        HIRC_OBJECT_TYPE_LABELS,
        SELECTION_HIRC_TYPES,
        build_audio_semantic_data,
        collect_metadata_audio_literals,
        collect_table_audio_event_hashes,
        collect_table_audio_event_names,
        hashed_event_key,
        is_rtpc_parameter_name,
    )
except ImportError:  # Imported as scripts.build_audio from repository-root tests.
    from scripts.build_audio_semantics import (
        HIRC_OBJECT_TYPE_LABELS,
        SELECTION_HIRC_TYPES,
        build_audio_semantic_data,
        collect_metadata_audio_literals,
        collect_table_audio_event_hashes,
        collect_table_audio_event_names,
        hashed_event_key,
        is_rtpc_parameter_name,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_ANIMESTUDIO = ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"
DEFAULT_AUDIO_DUMPER = DEFAULT_ANIMESTUDIO
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_WEBUI_ROOT = ROOT / "webui"
DEFAULT_AUDIO_ROOT = DEFAULT_EXPORT_ROOT / "structured" / "Audio"
NARRATIVE_VIDEO_OVERRIDES_NAME = "narrative_videos.json"
PROJECTILE_DATA_REL = Path("data/gameplay/projectiles.json")
PROJECTILE_EVENT_PREFIX = "projectile-event:"
GAMEPLAY_INDEX_REL = Path("data/lang/{language}/gameplay/index.json")
GAMEPLAY_SFX_REL = Path("data/lang/{language}/gameplay/sound_effects.json")
GAMEPLAY_SFX_ANIMATION_CATALOG_NAME = "sound_effects_animation_catalog.json"
GAMEPLAY_SFX_ANIMATION_EVIDENCE_NAME = "sound_effects_animation_evidence.json"
GAMEPLAY_SFX_ANIMATION_EVIDENCE_SCHEMA_VERSION = 2
GAMEPLAY_AUDIO_EVENT_BYTES_RE = re.compile(rb"\b(?:au|bark|radio)_[A-Za-z0-9_]{2,160}\b")
GAMEPLAY_BUFF_BYTES_RE = re.compile(rb"\bbuff_[A-Za-z0-9_]{2,160}\b")
ANIMATION_CLIP_HASH_SUFFIX_RE = re.compile(r"_p[0-9a-f]{16}$", re.IGNORECASE)
ANIMATION_CLIP_PATH_ID_SUFFIX_RE = re.compile(r"_p(?P<path_id>[0-9a-f]{16})$", re.IGNORECASE)
ANIMATION_ACTOR_RE = re.compile(r"^A_(actor|monster)_([^_]+)_", re.IGNORECASE)
ENEMY_ID_TOKEN_RE = re.compile(r"^eny_\d+_([^_]+)", re.IGNORECASE)
CHARACTER_ID_TOKEN_RE = re.compile(r"^chr_\d+_([^_]+)", re.IGNORECASE)
ENEMY_ANIM_CONFIG_RE = re.compile(r"anim_cfg_eny_\d+_([^./\\]+)\.asset$", re.IGNORECASE)
ANIMATION_AUDIO_FUNCTIONS = frozenset({
    "PostAudioEvent",
    "PostAudioEventAdvance",
    "PostAudioEventAtPosition",
    "OnCustomFootStep",
})
ANIMATOR_CONTROLLER_REL = Path(
    "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController"
)
GAMEPLAY_PROFILE_VOICE_RE = re.compile(r"(?:_combat_|_mono_(?:attack|skill))", re.IGNORECASE)
GAMEPLAY_AUDIO_LINK_FIELDS = (
    "src", "mediaId", "format", "bytes", "audioScope", "audioCategory",
    "audioCategoryDetail", "sourceBlock", "sourceBlockLabel", "sourceBank",
    "bankId", "bank", "wwiseMediaEvidence", "contentSha256",
)
PROJECTILE_SOUND_FIELDS = (
    "launchSound",
    "loopSound",
    "reachSound",
    "hitSound",
    "blockSound",
    "finishedSound",
    "sizzleSound",
)

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
EVENT_BANK_FILE_REGEX = r"(^|[\\/])[^\\/]*banks\.pck$"
EVENT_EVIDENCE_SCHEMA_VERSION = 11

# Wwise 2024.1 / bank version 150 HIRC action operations.  The serialized
# value is a little-endian U16 whose high byte is the operation and low byte is
# the action scope.  Only Play and PlayEvent introduce downward playback
# edges; Stop and the other control actions must not be followed as media.
HIRC_ACTION_OPERATION_LABELS = {
    0x0100: "stop",
    0x0400: "play",
    0x2100: "playEvent",
}
HIRC_PLAYBACK_ACTION_OPERATIONS = frozenset({0x0400, 0x2100})
HIRC_ACTION_PROPERTY_LABELS = {
    0x39: "delayTime",
    0x3A: "transitionTime",
    0x3B: "probability",
}
HIRC_FADE_CURVE_LABELS = {
    0: "Log3",
    1: "Sine",
    2: "Log1",
    3: "InvSCurve",
    4: "Linear",
    5: "SCurve",
    6: "Exp1",
    7: "SineRecip",
    8: "Exp3",
    9: "Constant",
}
HIRC_BANK_TYPE_LABELS = {
    0: "User",
    30: "Event",
    31: "Bus",
}
HIRC_MUSIC_NODE_TYPES = frozenset({10, 11, 12, 13})
HIRC_MUSIC_PARENT_NODE_TYPES = frozenset({10, 12, 13})
HIRC_MUSIC_CHILD_TYPES = {
    10: frozenset({11}),
    12: frozenset({10, 12, 13}),
    13: frozenset({10, 12, 13}),
}
HIRC_TYPED_CHILD_CONTAINER_TYPES = frozenset({5, 6, 7, 9, *HIRC_MUSIC_PARENT_NODE_TYPES})
HIRC_AUDIO_NODE_TYPES = frozenset({2, 5, 6, 7, 9, *HIRC_MUSIC_NODE_TYPES})

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


def normalize_posix(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix()


def audio_output_format(args: argparse.Namespace) -> str:
    """Return the browser-facing format while preserving legacy WEM calls."""
    source_format = str(getattr(args, "format", "wav") or "wav").lower()
    requested = str(getattr(args, "audio_format", "") or "").lower()
    output_format = requested or ("flac" if source_format == "wav" else source_format)
    if output_format not in {"flac", "wav", "wem"}:
        raise SystemExit(f"Unsupported browser audio format: {output_format}")
    if source_format == "wem" and output_format != "wem":
        raise SystemExit(
            "WEM decoding can only keep WEM output; omit --format wem for "
            "browser-playable WAV/FLAC output."
        )
    if source_format == "wav" and output_format == "wem":
        raise SystemExit(
            "WEM output requires --format wem; use the default FLAC output for "
            "browser-playable audio."
        )
    return output_format


def audio_rel_with_extension(rel: str | Path, extension: str) -> str:
    suffix = str(extension or "").strip().lower()
    if suffix and not suffix.startswith("."):
        suffix = "." + suffix
    path = PurePosixPath(normalize_posix(rel))
    return normalize_posix(path.with_suffix(suffix)) if suffix else normalize_posix(path)


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def projectile_event_key(event_hash: int) -> str:
    return f"{PROJECTILE_EVENT_PREFIX}0x{event_hash & 0xFFFFFFFF:08x}"


def length_prefixed_matches(data: bytes, pattern: re.Pattern[bytes]) -> set[str]:
    """Return exact MemoryPack UTF-8 strings matching ``pattern``.

    Gameplay config strings are encoded as a four-byte byte length followed by
    UTF-8.  Requiring that boundary prevents incidental ASCII fragments from
    being promoted to authored references.
    """

    values: set[str] = set()
    for match in pattern.finditer(data):
        start = match.start()
        if start < 4 or unpack_from("<I", data, start - 4)[0] != len(match.group(0)):
            continue
        try:
            values.add(match.group(0).decode("ascii"))
        except UnicodeDecodeError:
            continue
    return values


def gameplay_config_records(export_root: Path, family: str) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for source in ("StreamingAssets", "Persistent"):
        root = export_root / "structured" / source / "Data" / "Json" / family
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                data = path.read_bytes()
            except OSError:
                continue
            events = length_prefixed_matches(data, GAMEPLAY_AUDIO_EVENT_BYTES_RE)
            buffs = length_prefixed_matches(data, GAMEPLAY_BUFF_BYTES_RE)
            if not events and not buffs:
                continue
            record = records.setdefault(path.stem, {"events": set(), "buffs": set(), "sources": set()})
            record["events"].update(events)
            record["buffs"].update(buffs)
            record["sources"].add(normalize_posix(path.relative_to(export_root)))
    return records


def iter_json_strings(value: Any):
    """Yield scalar strings from a decoded JSON value."""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_json_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_strings(child)


def enemy_template_source_files(export_root: Path) -> dict[str, list[Path]]:
    """Index recovered EnemyData MonoBehaviours once for focused lookups."""

    result: dict[str, list[Path]] = defaultdict(list)
    seen: set[Path] = set()
    for source in ("Persistent", "StreamingAssets"):
        root = export_root / "recovered" / "AnimeStudio-cli" / source / "json_by_type" / "MonoBehaviour"
        if not root.exists():
            continue
        for path in root.glob("data_eny_*_p*.json"):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            prefix, separator, suffix = path.stem.rpartition("_p")
            if not separator or not suffix or not re.fullmatch(r"[0-9a-f]+", suffix, re.IGNORECASE):
                continue
            identity = prefix.removeprefix("data_")
            result[identity].append(path)
    return {identity: sorted(paths) for identity, paths in sorted(result.items())}


def enemy_template_skill_references(
    export_root: Path,
    enemies: list[dict[str, Any]],
    known_skill_ids: set[str],
    source_files: dict[str, list[Path]] | None = None,
) -> dict[str, dict[str, set[str]]]:
    """Return enemy -> SkillData ids recovered inside AbilitySystemData.

    Enemy variants frequently execute SkillData authored under a different
    canonical enemy id.  Matching only the current enemy-id prefix therefore
    hides otherwise playable attack audio.  The recovered EnemyData
    MonoBehaviours preserve the exact SkillData identifiers in their
    AbilitySystemData payload (including partially decoded string-hint tails),
    so require an exact match to an exported SkillData id before accepting the
    relationship.
    """

    indexed_files = source_files if source_files is not None else enemy_template_source_files(export_root)
    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    seen_paths: set[Path] = set()
    for enemy in enemies:
        owner_id = str(enemy.get("id") or "").strip()
        if not owner_id:
            continue
        identities = {
            str(value or "").strip()
            for value in (enemy.get("id"), enemy.get("templateId"), *(enemy.get("variantIds") or []))
            if str(value or "").strip()
        }
        for identity in sorted(identities):
            for path in indexed_files.get(identity) or []:
                resolved = path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                payload = load_json(path, {})
                references = ((payload.get("references") or {}).get("RefIds") or []) if isinstance(payload, dict) else []
                matched: set[str] = set()
                for reference in references:
                    if not isinstance(reference, dict):
                        continue
                    type_info = reference.get("type") or {}
                    if str(type_info.get("class") or "") != "AbilitySystemData":
                        continue
                    matched.update(
                        value
                        for value in iter_json_strings(reference.get("data") or {})
                        if value in known_skill_ids
                    )
                if not matched:
                    continue
                try:
                    source = normalize_posix(path.relative_to(export_root))
                except ValueError:
                    source = normalize_posix(path)
                for skill_id in matched:
                    result[owner_id][skill_id].add(source)
    return {
        owner_id: {skill_id: sources for skill_id, sources in sorted(skills.items())}
        for owner_id, skills in sorted(result.items())
    }


def enemy_template_animation_tokens(
    export_root: Path,
    enemies: list[dict[str, Any]],
    source_files: dict[str, list[Path]] | None = None,
) -> dict[str, dict[str, set[str]]]:
    """Return enemy -> animation actor tokens with exact source files."""

    indexed_files = source_files if source_files is not None else enemy_template_source_files(export_root)
    result: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for enemy in enemies:
        owner_id = str(enemy.get("id") or "").strip()
        if not owner_id:
            continue
        identities = {
            str(value or "").strip()
            for value in (enemy.get("id"), enemy.get("templateId"), *(enemy.get("variantIds") or []))
            if str(value or "").strip()
        }
        for identity in sorted(identities):
            direct = ENEMY_ID_TOKEN_RE.match(identity)
            if direct:
                result[owner_id][direct.group(1).lower()].add("EnemyTable identity")
            seen_paths: set[Path] = set()
            for path in indexed_files.get(identity) or []:
                resolved = path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                payload = load_json(path, {})
                try:
                    source = normalize_posix(path.relative_to(export_root))
                except ValueError:
                    source = normalize_posix(path)
                for value in iter_json_strings(payload):
                    match = ENEMY_ANIM_CONFIG_RE.search(value)
                    if match:
                        result[owner_id][match.group(1).lower()].add(source)
    return {
        owner_id: {token: sources for token, sources in sorted(tokens.items())}
        for owner_id, tokens in sorted(result.items())
    }


def animation_clip_action_kind(clip_name: str) -> str:
    value = clip_name.lower()
    if re.search(r"(?:^|_)(?:attack\d*|atk\d*|normal_attack|power_attack)(?:_|$)", value):
        return "attack"
    if re.search(r"(?:^|_)(?:skill\d*|combo|ultimate)(?:_|$)", value):
        return "skill"
    if re.search(r"(?:^|_)(?:damage|damaged|hit|death|die|down|break)(?:_|$)", value):
        return "reaction"
    if re.search(r"(?:^|_)(?:walk|run|move|turn|land|jump|fall|dash|sprint|idle)(?:_|$)", value):
        return "movement"
    return "action"


def animation_clip_context(clip_name: str) -> str:
    value = clip_name.lower()
    for token in ("battle", "dialog", "customized", "ui", "interact", "idle", "relax"):
        if re.search(rf"(?:^|_){token}(?:_|$)", value):
            return token
    return "other"


def gameplay_character_token_owners(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    token_owners: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("kind") != "character":
            continue
        owner_id = str(entry.get("id") or "").strip()
        if not owner_id:
            continue
        direct = CHARACTER_ID_TOKEN_RE.match(owner_id)
        if direct:
            token_owners[direct.group(1).lower()].add(owner_id)
        for group in entry.get("skillGroups") or []:
            for skill_id in group.get("actionSkillIds") or []:
                match = CHARACTER_ID_TOKEN_RE.match(str(skill_id or ""))
                if match:
                    token_owners[match.group(1).lower()].add(owner_id)
    return {token: sorted(owners) for token, owners in sorted(token_owners.items())}


def profile_voice_action_kind(vo_id: str) -> str:
    value = vo_id.lower()
    if "_mono_attack" in value:
        return "attackVoice"
    if "_mono_skill" in value or "_combat_skill" in value:
        return "skillVoice"
    if "_combat_hurt" in value or "_combat_dead" in value:
        return "reactionVoice"
    return "combatVoice"


def collect_gameplay_profile_voices(
    export_root: Path,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Collect exact CharacterTable combat/profile voice ownership."""

    character_table = {}
    character_source = ""
    for source in ("Persistent", "StreamingAssets"):
        path = export_root / "structured" / source / "Table" / "CharacterTable.json"
        payload = load_json(path, {})
        if isinstance(payload, dict) and payload:
            character_table = payload
            try:
                character_source = normalize_posix(path.relative_to(export_root))
            except ValueError:
                character_source = normalize_posix(path)
            break

    trigger_keys: set[str] = set()
    for source in ("Persistent", "StreamingAssets"):
        path = export_root / "structured" / source / "Table" / "AIBark.json"
        payload = load_json(path, {})
        if not isinstance(payload, dict):
            continue
        for value in payload.values():
            rows = value.get("array") if isinstance(value, dict) else None
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                trigger_keys.update(str(key or "").strip() for key in row.get("triggerKey") or [] if str(key or "").strip())
        if trigger_keys:
            break
    sorted_triggers = sorted(trigger_keys, key=lambda value: (-len(value), value))

    token_owners = gameplay_character_token_owners(entries)
    owners: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for character_id, row in sorted(character_table.items()):
        if not isinstance(row, dict):
            continue
        match = CHARACTER_ID_TOKEN_RE.match(str(character_id or ""))
        if not match:
            continue
        for owner_id in token_owners.get(match.group(1).lower()) or []:
            for voice in row.get("profileVoice") or []:
                if not isinstance(voice, dict):
                    continue
                vo_id = str(voice.get("voId") or "").strip()
                if not vo_id or not GAMEPLAY_PROFILE_VOICE_RE.search(vo_id):
                    continue
                key = (owner_id, vo_id.lower())
                if key in seen:
                    continue
                seen.add(key)
                tail = vo_id[len(str(character_id)) + 1:] if vo_id.lower().startswith(str(character_id).lower() + "_") else vo_id
                trigger_key = next(
                    (candidate for candidate in sorted_triggers if tail == candidate or tail.startswith(candidate + "_")),
                    "",
                )
                owners[owner_id].append({
                    "id": vo_id,
                    "actionKind": profile_voice_action_kind(vo_id),
                    "characterId": character_id,
                    "profileVoiceIndex": voice.get("voiceIndex"),
                    "triggerKey": trigger_key,
                    "source": character_source,
                })
    return {
        "owners": [
            {"ownerId": owner_id, "voices": sorted(voices, key=lambda row: str(row.get("id") or ""))}
            for owner_id, voices in sorted(owners.items())
        ],
        "counts": {
            "profileVoiceRefs": sum(len(voices) for voices in owners.values()),
            "profileVoiceOwners": len(owners),
            "profileVoiceRefsWithTrigger": sum(
                1 for voices in owners.values() for voice in voices if voice.get("triggerKey")
            ),
        },
    }


def animation_clip_audio_events(data: bytes) -> tuple[str, list[dict[str, Any]]]:
    """Read the small scalar event portion of an exported Unity .anim YAML."""

    clip_name = ""
    current: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    in_events = False
    event_index = -1

    def finish() -> None:
        nonlocal current
        if current and current.get("function") in ANIMATION_AUDIO_FUNCTIONS and current.get("eventId"):
            events.append(current)
        current = None

    for raw_line in data.splitlines():
        line = raw_line.decode("utf-8", errors="replace")
        if not clip_name and line.startswith("  m_Name: "):
            clip_name = line.removeprefix("  m_Name: ").strip().strip("'\"")
        elif line == "  m_Events:":
            in_events = True
        elif in_events and line.startswith("  - time: "):
            finish()
            event_index += 1
            raw_time = line.removeprefix("  - time: ").strip()
            try:
                time_value: float | str = float(raw_time)
            except ValueError:
                time_value = raw_time
            current = {"index": event_index, "time": time_value}
        elif current is not None and line.startswith("    functionName: "):
            current["function"] = line.removeprefix("    functionName: ").strip().strip("'\"")
        elif current is not None and line.startswith("    data: "):
            current["eventId"] = line.removeprefix("    data: ").strip().strip("'\"")
        elif current is not None and line.startswith("    floatParameter: "):
            raw_value = line.removeprefix("    floatParameter: ").strip()
            try:
                current["floatParameter"] = float(raw_value)
            except ValueError:
                current["floatParameter"] = raw_value
        elif current is not None and line.startswith("    intParameter: "):
            raw_value = line.removeprefix("    intParameter: ").strip()
            try:
                current["intParameter"] = int(raw_value)
            except ValueError:
                current["intParameter"] = raw_value
    finish()
    return clip_name, events


def animation_clip_path_id(path: Path) -> int | None:
    """Recover the signed Unity PathID encoded in an exported clip filename."""

    match = ANIMATION_CLIP_PATH_ID_SUFFIX_RE.search(path.stem)
    if not match:
        return None
    try:
        value = int(match.group("path_id"), 16)
    except (TypeError, ValueError):
        return None
    return value - (1 << 64) if value >= (1 << 63) else value


def collect_animation_controller_index(export_root: Path) -> dict[str, Any]:
    """Index resolved AnimatorController->AnimationClip PPtrs fail-closed.

    The exported ``$animestudio.pptrReferences`` records are the only accepted
    evidence here.  Name matching, raw controller payload guesses, and
    AnimatorOverrideController pairs are deliberately excluded until their
    serialized-file context can be resolved without ambiguity.
    """

    root = export_root / ANIMATOR_CONTROLLER_REL
    by_clip_path_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    counts = {
        "status": "unavailable" if not root.is_dir() else "complete",
        "sourceRoot": normalize_posix(ANIMATOR_CONTROLLER_REL),
        "filesScanned": 0,
        "filesWithDirectReferences": 0,
        "malformedFiles": 0,
        "directReferenceCount": 0,
        "uniqueReferencedClipPathIds": 0,
        "controllerCount": 0,
        "overrideControllersExcluded": True,
    }
    if not root.is_dir():
        return {"byClipPathId": {}, "summary": counts}

    seen_controllers: set[tuple[str, str, str]] = set()
    seen_references: set[tuple[int, str, str, str]] = set()
    for path in sorted(root.glob("*.json"), key=lambda value: value.name.lower()):
        counts["filesScanned"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            counts["malformedFiles"] += 1
            continue
        if not isinstance(payload, dict):
            counts["malformedFiles"] += 1
            continue
        metadata = payload.get("$animestudio")
        if not isinstance(metadata, dict) or metadata.get("type") != "AnimatorController":
            # A valid JSON file without the exporter identity envelope is not
            # safe to use as a direct-reference source.
            counts["malformedFiles"] += 1
            continue
        references = metadata.get("pptrReferences")
        if not isinstance(references, list):
            counts["malformedFiles"] += 1
            continue
        controller_name = str(
            payload.get("m_Name") or metadata.get("name") or path.stem
        ).strip()
        controller_source_file = str(metadata.get("sourceFile") or "").strip()
        controller_path_id = metadata.get("pathId")
        controller_key = (
            controller_source_file,
            str(controller_path_id) if isinstance(controller_path_id, int) else "",
            normalize_posix(path.relative_to(export_root)),
        )
        direct_file_reference_count = 0
        for reference in references:
            if not isinstance(reference, dict):
                continue
            target = reference.get("target")
            target = target if isinstance(target, dict) else {}
            target_type = str(
                reference.get("targetType") or target.get("type") or ""
            )
            resolution_status = str(reference.get("resolutionStatus") or "")
            if target_type != "AnimationClip" or not resolution_status.startswith("resolved"):
                continue
            target_path_id = reference.get("targetPathId")
            if not isinstance(target_path_id, int) or isinstance(target_path_id, bool):
                target_path_id = target.get("pathId")
            target_source_file = str(
                reference.get("targetSourceFile") or target.get("serializedFile") or ""
            ).strip()
            if (
                not isinstance(target_path_id, int)
                or isinstance(target_path_id, bool)
                or not target_source_file
            ):
                continue
            reference_key = (
                target_path_id,
                target_source_file,
                controller_key[2],
                controller_key[0],
            )
            if reference_key in seen_references:
                continue
            seen_references.add(reference_key)
            if controller_key not in seen_controllers:
                seen_controllers.add(controller_key)
                counts["controllerCount"] += 1
            context = {
                "name": controller_name,
                "sourcePath": controller_key[2],
                "sourceFile": controller_source_file,
                "pathId": controller_path_id,
                "targetSourceFile": target_source_file,
                "resolutionStatus": resolution_status,
            }
            by_clip_path_id[target_path_id].append(context)
            direct_file_reference_count += 1
            counts["directReferenceCount"] += 1
        if direct_file_reference_count:
            counts["filesWithDirectReferences"] += 1

    for path_id, contexts in by_clip_path_id.items():
        by_clip_path_id[path_id] = sorted(
            contexts,
            key=lambda row: (
                str(row.get("name") or ""),
                str(row.get("sourcePath") or ""),
                str(row.get("targetSourceFile") or ""),
            ),
        )
    counts["uniqueReferencedClipPathIds"] = len(by_clip_path_id)
    if counts["malformedFiles"] and counts["filesWithDirectReferences"]:
        counts["status"] = "partial"
    return {"byClipPathId": dict(by_clip_path_id), "summary": counts}


def animation_controller_contexts(
    controller_index: dict[str, Any], path: Path
) -> list[dict[str, Any]]:
    """Return direct controller contexts for one exported AnimationClip."""

    path_id = animation_clip_path_id(path)
    if path_id is None:
        return []
    contexts = controller_index.get(path_id) or {}
    return [dict(row) for row in contexts if isinstance(row, dict)]


def animation_clip_reachability_status(
    evidence: Iterable[dict[str, Any]],
) -> str:
    """Classify one Event's clip rows without promoting unresolved evidence."""

    rows = [row for row in evidence if isinstance(row, dict)]
    direct = sum(bool(row.get("animatorControllerCount")) for row in rows)
    if not direct:
        return "unresolved"
    if direct == len(rows):
        return "directAnimatorController"
    return "mixedAnimatorControllerReachability"


def collect_gameplay_animation_audio(
    export_root: Path,
    entries: list[dict[str, Any]],
    enemies: list[dict[str, Any]],
    enemy_source_files: dict[str, list[Path]] | None = None,
) -> dict[str, Any]:
    """Collect exact AnimationClip audio callbacks with bounded actor ownership."""

    token_owners: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for token, owner_ids in gameplay_character_token_owners(entries).items():
        for owner_id in owner_ids:
            token_owners[("actor", token)].append({
                "ownerKind": "character",
                "ownerId": owner_id,
                "ownershipSources": ["Gameplay character/action identifiers"],
            })

    enemy_tokens = enemy_template_animation_tokens(export_root, enemies, enemy_source_files)
    for owner_id, tokens in enemy_tokens.items():
        for token, sources in tokens.items():
            token_owners[("monster", token)].append({
                "ownerKind": "enemy",
                "ownerId": owner_id,
                "ownershipSources": sorted(sources),
            })

    root = (
        export_root
        / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
    )
    owners: dict[tuple[str, str], dict[str, Any]] = {}
    unowned_events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    controller_index_data = collect_animation_controller_index(export_root)
    controller_index = controller_index_data.get("byClipPathId") or {}
    controller_reachable_clips = 0
    controller_unresolved_clips = 0
    controller_reachable_callback_rows = 0
    controller_unresolved_callback_rows = 0
    scanned_clips = 0
    matched_clips = 0
    unowned_clips = 0
    owned_callback_rows = 0
    unowned_callback_rows = 0
    if root.exists():
        candidate_paths = sorted([
            *root.glob("A_actor_*.anim"),
            *root.glob("A_monster_*.anim"),
        ])
        for path in candidate_paths:
            scanned_clips += 1
            filename_clip_name = ANIMATION_CLIP_HASH_SUFFIX_RE.sub("", path.stem)
            filename_match = ANIMATION_ACTOR_RE.match(filename_clip_name)
            matched_owners = (
                token_owners.get(
                    (filename_match.group(1).lower(), filename_match.group(2).lower())
                ) or []
                if filename_match
                else []
            )
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if b"functionName: PostAudio" not in data and b"functionName: OnCustomFootStep" not in data:
                continue
            clip_name, clip_events = animation_clip_audio_events(data)
            if not clip_events:
                continue
            clip_kind = animation_clip_action_kind(clip_name)
            clip_context = animation_clip_context(clip_name)
            controller_contexts = animation_controller_contexts(controller_index, path)
            clip_reachability = (
                "directAnimatorController" if controller_contexts else "unresolved"
            )
            if controller_contexts:
                controller_reachable_clips += 1
                controller_reachable_callback_rows += len(clip_events)
            else:
                controller_unresolved_clips += 1
                controller_unresolved_callback_rows += len(clip_events)
            try:
                clip_source = normalize_posix(path.relative_to(export_root))
            except ValueError:
                clip_source = normalize_posix(path)
            base_evidence = {
                "kind": "animationClipEvent",
                "clip": clip_name,
                "clipSource": clip_source,
                "actionKind": clip_kind,
                "clipContext": clip_context,
                "clipReachability": clip_reachability,
                "animatorControllerCount": len(controller_contexts),
                "animatorControllerContexts": controller_contexts,
            }
            if matched_owners:
                matched_clips += 1
                owned_callback_rows += len(clip_events)
                for owner in matched_owners:
                    owner_key = (owner["ownerKind"], owner["ownerId"])
                    record = owners.setdefault(owner_key, {
                        **owner,
                        "events": defaultdict(list),
                    })
                    for event in clip_events:
                        authored_event_id = str(event.get("eventId") or "").strip()
                        event_key = authored_event_id.lower()
                        if not event_key:
                            continue
                        record["events"][event_key].append({
                            **base_evidence,
                            "authoredEventId": authored_event_id,
                            "eventIndex": event.get("index"),
                            "time": event.get("time"),
                            "function": event.get("function"),
                            "floatParameter": event.get("floatParameter"),
                            "intParameter": event.get("intParameter"),
                        })
            else:
                unowned_clips += 1
                unowned_callback_rows += len(clip_events)
                for event in clip_events:
                    authored_event_id = str(event.get("eventId") or "").strip()
                    event_key = authored_event_id.lower()
                    if not event_key:
                        continue
                    unowned_events[event_key].append({
                        **base_evidence,
                        "authoredEventId": authored_event_id,
                        "ownerStatus": "unresolved",
                        "actorKindToken": filename_match.group(1).lower() if filename_match else "",
                        "actorIdentityToken": filename_match.group(2).lower() if filename_match else "",
                        "eventIndex": event.get("index"),
                        "time": event.get("time"),
                        "function": event.get("function"),
                        "floatParameter": event.get("floatParameter"),
                        "intParameter": event.get("intParameter"),
                    })

    event_names = {
        event_key
        for owner in owners.values()
        for event_key in owner["events"]
    }.union(unowned_events)
    normalized_owners: list[dict[str, Any]] = []
    for owner in owners.values():
        normalized_owners.append({
            **owner,
            "events": {
                event_key: sorted(
                    evidence,
                    key=lambda row: (str(row.get("clip") or ""), float(row.get("time") or 0), str(row.get("function") or "")),
                )
                for event_key, evidence in sorted(owner["events"].items())
            },
        })
    return {
        "eventNames": event_names,
        "owners": sorted(normalized_owners, key=lambda row: (row["ownerKind"], row["ownerId"])),
        "unownedEvents": {
            event_key: sorted(
                evidence,
                key=lambda row: (
                    str(row.get("clip") or ""),
                    float(row.get("time") or 0),
                    str(row.get("function") or ""),
                ),
            )
            for event_key, evidence in sorted(unowned_events.items())
        },
        "counts": {
            "animationAudioClipsScanned": scanned_clips,
            "animationAudioClipsOwned": matched_clips,
            "animationAudioClipsOwnerUnresolved": unowned_clips,
            "animationAudioCallbackRows": owned_callback_rows + unowned_callback_rows,
            "animationAudioOwnedCallbackRows": owned_callback_rows,
            "animationAudioOwnerUnresolvedCallbackRows": unowned_callback_rows,
            "animationAudioEventNames": len(event_names),
            "animationAudioOwnerEventRefs": sum(len(owner["events"]) for owner in owners.values()),
            "animationAudioOwnerUnresolvedEventRefs": len(unowned_events),
            "animationAudioControllerReachableClips": controller_reachable_clips,
            "animationAudioControllerUnresolvedClips": controller_unresolved_clips,
            "animationAudioControllerReachableCallbackRows": controller_reachable_callback_rows,
            "animationAudioControllerUnresolvedCallbackRows": controller_unresolved_callback_rows,
            "animationAudioControllerReferences": int(
                (controller_index_data.get("summary") or {}).get("directReferenceCount") or 0
            ),
        },
        "animationControllerIndex": controller_index_data.get("summary") or {},
    }


def gameplay_buff_audio(
    initial_buff_ids: set[str],
    buff_records: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    """Return event -> contributing BuffData ids through exact buff references."""

    events: dict[str, set[str]] = defaultdict(set)
    queue: deque[str] = deque(sorted(initial_buff_ids))
    visited: set[str] = set()
    while queue:
        buff_id = queue.popleft()
        if not buff_id or buff_id in visited:
            continue
        visited.add(buff_id)
        record = buff_records.get(buff_id) or {}
        for event_id in record.get("events") or set():
            events[event_id].add(buff_id)
        for linked_id in sorted(record.get("buffs") or set()):
            if linked_id not in visited:
                queue.append(linked_id)
    return events


def play_sound_action_marker(row: dict[str, Any]) -> tuple[Any, ...]:
    """Stable identity for one decoded BuffData PlaySound timeline action."""

    return tuple(
        row.get(key)
        for key in (
            "buffId", "eventId", "timelineActionIndex", "actionDataIndex",
            "startFrame", "endFrame", "serverActionIndex",
        )
    )


def seed_buff_play_sound_events(
    buff_records: dict[str, dict[str, Any]],
    by_buff_event: dict[str, dict[str, list[dict[str, Any]]]],
) -> int:
    """Add exact typed PlaySound Events to their owning BuffData records.

    PlaySoundActionData uses a typed MemoryPack string slot that is not always
    visible to the generic length-prefixed string inventory.  Seeding only the
    exact decoder rows lets the existing BuffData dependency traversal carry
    those requests to gameplay owners without inventing an owner for an
    otherwise unreachable BuffData record.
    """

    seeded = 0
    for buff_id, events in sorted((by_buff_event or {}).items()):
        record = buff_records.get(str(buff_id))
        if not isinstance(record, dict):
            continue
        record_events = record.setdefault("events", set())
        for event_key, actions in sorted((events or {}).items()):
            authored_ids = {
                str(action.get("eventId") or "").strip()
                for action in actions or []
                if isinstance(action, dict) and str(action.get("eventId") or "").strip()
            }
            if not authored_ids and str(event_key or "").strip():
                authored_ids.add(str(event_key).strip())
            for event_id in sorted(authored_ids):
                if event_id in record_events:
                    continue
                record_events.add(event_id)
                seeded += 1
    return seeded


def annotate_play_sound_action_owner_links(
    actions: list[dict[str, Any]],
    owners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Keep every decoded action while explicitly marking unresolved owners."""

    linked_markers: set[tuple[Any, ...]] = set()
    for owner in owners:
        for evidence_rows in (owner.get("events") or {}).values():
            for evidence in evidence_rows or []:
                if not isinstance(evidence, dict):
                    continue
                for action in evidence.get("playSoundActions") or []:
                    if isinstance(action, dict):
                        linked_markers.add(play_sound_action_marker(action))
    annotated = []
    linked = 0
    for action in actions:
        has_link = play_sound_action_marker(action) in linked_markers
        linked += int(has_link)
        annotated.append({
            **action,
            "ownerLinkStatus": "linkedThroughBuffDependency" if has_link else "unresolved",
        })
    return annotated, {
        "buffPlaySoundActionsLinkedToGameplayOwner": linked,
        "buffPlaySoundActionsOwnerUnresolved": len(annotated) - linked,
    }


def collect_buff_play_sound_actions(
    export_root: Path,
    buff_records: dict[str, dict[str, Any]],
    *,
    decoder: Any | None = None,
) -> dict[str, Any]:
    """Decode exact current-build PlaySound timeline actions from BuffData.

    The generic string scan proves only that a BuffData dependency contains an
    event id.  The MemoryPack action decoder additionally recovers the authored
    timeline frame window and the PlaySoundActionData lifetime/routing controls.
    TargetSettings remains a bounded opaque envelope, so these rows deliberately
    stop short of claiming that the runtime condition or target was selected.
    """

    if decoder is None:
        try:
            from build_data_index import (
                BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS,
                BUFF_PLAY_SOUND_ACTION_TAG,
                MEMORYPACK_UNION_WIDE_TAG,
                consume_buff_play_sound_action,
            )
        except ImportError:  # Imported as scripts.build_audio from repository-root tests.
            from scripts.build_data_index import (
                BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS,
                BUFF_PLAY_SOUND_ACTION_TAG,
                MEMORYPACK_UNION_WIDE_TAG,
                consume_buff_play_sound_action,
            )

        member_count = BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS[BUFF_PLAY_SOUND_ACTION_TAG]
        signature = bytes([MEMORYPACK_UNION_WIDE_TAG]) + int(BUFF_PLAY_SOUND_ACTION_TAG).to_bytes(2, "little") + bytes([member_count])

        def decoder(_path: Path, data: bytes, _size: int) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
            """Find locally self-bounded single-item PlaySound timeline records.

            This deliberately does not depend on the broad BuffData schema or
            tail parser.  The current records have a one-item SequenceActionData
            envelope immediately before the typed union item and the two guard
            booleans/startFrame/ForceSyncAnimData boundary immediately after it.
            """

            rows: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
            position = data.find(signature)
            while position >= 0:
                record_start = position - 10
                try:
                    if (
                        record_start < 0
                        or data[record_start] != 4
                        or data[position - 5] != 3
                        or unpack_from("<I", data, position - 4)[0] != 1
                    ):
                        raise ValueError("not-single-item-timeline-envelope")
                    end_frame = unpack_from("<i", data, record_start + 1)[0]
                    action, action_end = consume_buff_play_sound_action(
                        data,
                        position,
                        len(data),
                        3,
                        member_count,
                    )
                    if action_end + 7 > len(data):
                        raise ValueError("truncated-timeline-suffix")
                    only_guard = data[action_end]
                    only_main_char = data[action_end + 1]
                    if only_guard not in (0, 1) or only_main_char not in (0, 1):
                        raise ValueError("invalid-timeline-guard-bool")
                    start_frame = unpack_from("<i", data, action_end + 2)[0]
                    if data[action_end + 6] != 4:
                        raise ValueError("missing-force-sync-boundary")
                    rows.append((
                        {"index": len(rows), "startFrame": start_frame, "endFrame": end_frame},
                        {
                            "onlyExecuteWhenSourceIsGuard": bool(only_guard),
                            "onlyExecuteWhenSourceIsMainChar": bool(only_main_char),
                        },
                        action,
                    ))
                except (IndexError, ValueError):
                    pass
                position = data.find(signature, position + 1)
            return rows

    merged: dict[tuple[Any, ...], dict[str, Any]] = {}
    decoded_files = 0
    decode_failures = 0
    for buff_id, record in sorted(buff_records.items()):
        for source in sorted(record.get("sources") or set()):
            path = export_root / PurePosixPath(str(source))
            try:
                data = path.read_bytes()
                decoded_actions = decoder(path, data, len(data)) or []
            except (OSError, ValueError):
                decode_failures += 1
                continue
            if not decoded_actions:
                continue
            source_has_play_sound = False
            for action_index, (timeline, sequence, action) in enumerate(decoded_actions):
                event_id = str(action.get("soundEvent") or "").strip()
                if not event_id:
                    continue
                source_has_play_sound = True
                prefix = action.get("prefix") or {}
                target = action.get("targetSettingsEnvelopePartial") or {}
                row = {
                    "buffId": buff_id,
                    "eventId": event_id,
                    "timelineActionIndex": timeline.get("index"),
                    "actionDataIndex": action_index,
                    "startFrame": timeline.get("startFrame"),
                    "endFrame": timeline.get("endFrame"),
                    "onlyExecuteWhenSourceIsGuard": bool(sequence.get("onlyExecuteWhenSourceIsGuard")),
                    "onlyExecuteWhenSourceIsMainChar": bool(sequence.get("onlyExecuteWhenSourceIsMainChar")),
                    "isEnabled": bool(prefix.get("isEnable")),
                    "priorityLevel": prefix.get("priorityLevel"),
                    "priorityOffset": prefix.get("priorityOffset"),
                    "serverActionIndex": prefix.get("serverActionIndex"),
                    "canInterruptTimeMs": action.get("canInterruptTimeMs"),
                    "interruptFadeDurationMs": action.get("intrptFadeDurationMs"),
                    "jumpToWhenPlayMs": action.get("jumpToWhenPlayMs"),
                    "stopFadeDurationMs": action.get("stopFadeDurationMs"),
                    "stopOnEnd": bool(action.get("stopOnEnd")),
                    "useTempEmitter": bool(action.get("useTempEmitter")),
                    "followMountPoint": bool(action.get("followMountPoint")),
                    "mountPoint": str(action.get("mountPoint") or ""),
                    "targetSettingsStatus": str(target.get("semanticStatus") or "unresolved"),
                    "targetSettingsShape": str(target.get("shape") or ""),
                    "targetSelector": str(target.get("stringSlotValue") or ""),
                    "timeDilationFadeInDurationMs": action.get("timeDilationFadeInDurationMs"),
                    "timeDilationFadeOutDurationMs": action.get("timeDilationFadeOutDurationMs"),
                    "timeDilationPauseThreshold": action.get("timeDilationPauseThreshold"),
                    "timeDilationSeekThreshold": action.get("timeDilationSeekThreshold"),
                    "useTimeDilationPauseAndSeek": bool(action.get("useTimeDilationPauseAndSeek")),
                    "useWeaponMountPoint": bool(action.get("useWeaponMountPoint")),
                    "weaponIndex": action.get("weaponIndex"),
                    "weaponMountPoint": str(action.get("weaponMountPoint") or ""),
                    "sourcePaths": [str(source)],
                    "evidence": "memoryPackPlaySoundActionData",
                    "runtimeConditionStatus": "unresolved",
                }
                marker = tuple(
                    json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for key, value in row.items()
                    if key not in {"sourcePaths"}
                )
                existing = merged.get(marker)
                if existing is None:
                    merged[marker] = row
                else:
                    existing["sourcePaths"] = sorted(set(existing["sourcePaths"]).union(row["sourcePaths"]))
            if source_has_play_sound:
                decoded_files += 1

    by_buff_event: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in merged.values():
        by_buff_event[str(row["buffId"])][str(row["eventId"]).lower()].append(row)
    return {
        "byBuffEvent": {
            buff_id: {
                event_id: sorted(
                    rows,
                    key=lambda row: (
                        int(row.get("startFrame") or 0),
                        int(row.get("endFrame") or 0),
                        int(row.get("serverActionIndex") or 0),
                    ),
                )
                for event_id, rows in sorted(events.items())
            }
            for buff_id, events in sorted(by_buff_event.items())
        },
        "counts": {
            "buffPlaySoundDecodedSourceFiles": decoded_files,
            "buffPlaySoundDecodeFailures": decode_failures,
            "buffPlaySoundActionOccurrences": len(merged),
            "buffPlaySoundUniqueEvents": len({str(row["eventId"]).lower() for row in merged.values()}),
        },
    }


def collect_gameplay_audio_references(
    webui_root: Path,
    export_root: Path,
    language: str,
) -> dict[str, Any]:
    """Collect evidence-backed SkillData/BuffData audio ownership for Gameplay."""

    gameplay_path = webui_root / Path(str(GAMEPLAY_INDEX_REL).format(language=language))
    gameplay = load_json(gameplay_path, {})
    entries = (gameplay.get("entries") or []) if isinstance(gameplay, dict) else []
    character_skills: dict[str, tuple[str, str]] = {}
    enemies: list[dict[str, Any]] = []
    enemy_ids: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind") or "")
        owner_id = str(entry.get("id") or "")
        if kind == "character":
            for group in entry.get("skillGroups") or []:
                if not isinstance(group, dict):
                    continue
                group_id = str(group.get("id") or "")
                skills = group.get("skills") or [
                    {"id": value}
                    for value in group.get("actionSkillIds") or []
                ]
                for skill in skills:
                    skill_id = str((skill or {}).get("id") or "") if isinstance(skill, dict) else ""
                    if skill_id:
                        character_skills[skill_id] = (owner_id, group_id)
        elif kind == "enemy" and owner_id:
            enemies.append(entry)
            for value in (entry.get("id"), entry.get("templateId"), *(entry.get("variantIds") or [])):
                key = str(value or "").strip()
                if key:
                    enemy_ids.append((key, owner_id))
    enemy_ids = sorted(set(enemy_ids), key=lambda row: (-len(row[0]), row[0], row[1]))
    character_skill_ids = sorted(character_skills, key=lambda value: (-len(value), value))

    skill_records = gameplay_config_records(export_root, "SkillData")
    buff_records = gameplay_config_records(export_root, "BuffData")
    buff_play_sound = collect_buff_play_sound_actions(export_root, buff_records)
    buff_play_sound_by_id = buff_play_sound.get("byBuffEvent") or {}
    seeded_play_sound_events = seed_buff_play_sound_events(
        buff_records,
        buff_play_sound_by_id,
    )

    def play_sound_rows(event_id: str, buff_ids: set[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        event_key = event_id.lower()
        for buff_id in sorted(buff_ids):
            rows.extend((buff_play_sound_by_id.get(buff_id) or {}).get(event_key) or [])
        return rows

    enemy_source_files = enemy_template_source_files(export_root)
    enemy_template_skills = enemy_template_skill_references(
        export_root,
        enemies,
        set(skill_records),
        enemy_source_files,
    )
    template_owners_by_skill: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    for enemy_id, skills in enemy_template_skills.items():
        for skill_id, sources in skills.items():
            template_owners_by_skill[skill_id].append((enemy_id, sources))
    owners: list[dict[str, Any]] = []
    authored_play_sound_actions = [
        row
        for events in (buff_play_sound.get("byBuffEvent") or {}).values()
        for rows in events.values()
        for row in rows
    ]
    event_names: set[str] = {
        str(row.get("eventId") or "").lower()
        for row in authored_play_sound_actions
        if str(row.get("eventId") or "")
    }
    owned_skill_ids: set[str] = set()

    for skill_id, record in sorted(skill_records.items()):
        matched_owners: list[dict[str, Any]] = []
        if skill_id in character_skills:
            owner_id, group_id = character_skills[skill_id]
            matched_owners.append({
                "ownerKind": "character",
                "ownerId": owner_id,
                "groupId": group_id,
                "confidence": "direct",
                "ownershipMethod": "gameplaySkillId",
                "ownershipSources": [],
            })
        else:
            character_match = next(
                (candidate for candidate in character_skill_ids if skill_id.startswith(candidate + "_")),
                None,
            )
            if character_match:
                owner_id, group_id = character_skills[character_match]
                matched_owners.append({
                    "ownerKind": "character",
                    "ownerId": owner_id,
                    "groupId": group_id,
                    "confidence": "inferred",
                    "ownershipMethod": "playableSkillFamilyPrefix",
                    "ownershipSources": [],
                })

        for enemy_id, ownership_sources in template_owners_by_skill.get(skill_id) or []:
            matched_owners.append({
                "ownerKind": "enemy",
                "ownerId": enemy_id,
                "groupId": "",
                "confidence": "inferred",
                "ownershipMethod": "enemyTemplateAbilitySystemSkill",
                "ownershipSources": sorted(ownership_sources),
            })

        if not any(owner["ownerKind"] == "enemy" for owner in matched_owners):
            enemy_match = next(
                ((candidate, enemy_id) for candidate, enemy_id in enemy_ids if skill_id == candidate or skill_id.startswith(candidate + "_")),
                None,
            )
            if enemy_match:
                matched_owners.append({
                    "ownerKind": "enemy",
                    "ownerId": enemy_match[1],
                    "groupId": "",
                    "confidence": "inferred",
                    "ownershipMethod": "enemyIdPrefix",
                    "ownershipSources": [],
                })
        if not matched_owners:
            continue

        event_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event_id in sorted(record.get("events") or set()):
            event_evidence[event_id].append({"kind": "skillData", "skillId": skill_id})
        for event_id, buff_ids in gameplay_buff_audio(set(record.get("buffs") or set()), buff_records).items():
            evidence = {
                "kind": "skillBuffData",
                "skillId": skill_id,
                "buffIds": sorted(buff_ids),
            }
            actions = play_sound_rows(event_id, buff_ids)
            if actions:
                evidence["playSoundActions"] = actions
            event_evidence[event_id].append(evidence)
        if not event_evidence:
            continue
        owned_skill_ids.add(skill_id)
        event_names.update(event_evidence)
        seen_owner_keys: set[tuple[str, str, str]] = set()
        for matched_owner in matched_owners:
            owner_key = (
                str(matched_owner.get("ownerKind") or ""),
                str(matched_owner.get("ownerId") or ""),
                str(matched_owner.get("groupId") or ""),
            )
            if owner_key in seen_owner_keys:
                continue
            seen_owner_keys.add(owner_key)
            owners.append({
                **matched_owner,
                "skillId": skill_id,
                "sources": sorted(record.get("sources") or set()),
                "events": dict(event_evidence),
            })

    for enemy in enemies:
        owner_id = str(enemy.get("id") or "")
        born_buffs = {str(value or "").strip() for value in enemy.get("bornBuffs") or [] if str(value or "").strip()}
        buff_events = gameplay_buff_audio(born_buffs, buff_records)
        if not buff_events:
            continue
        event_names.update(buff_events)
        owners.append({
            "ownerKind": "enemy",
            "ownerId": owner_id,
            "groupId": "",
            "skillId": "",
            "confidence": "direct",
            "ownershipMethod": "enemyBornBuffField",
            "ownershipSources": [],
            "sources": [],
            "events": {
                event_id: [{
                    "kind": "enemyBornBuffData",
                    "buffIds": sorted(buff_ids),
                    **(
                        {"playSoundActions": play_sound_rows(event_id, buff_ids)}
                        if play_sound_rows(event_id, buff_ids)
                        else {}
                    ),
                }]
                for event_id, buff_ids in sorted(buff_events.items())
            },
        })

    animation_audio = collect_gameplay_animation_audio(
        export_root,
        entries,
        enemies,
        enemy_source_files,
    )
    profile_voices = collect_gameplay_profile_voices(export_root, entries)
    event_names.update(animation_audio.get("eventNames") or set())
    authored_play_sound_actions, play_sound_owner_counts = (
        annotate_play_sound_action_owner_links(authored_play_sound_actions, owners)
    )
    return {
        "eventNames": event_names,
        "owners": owners,
        "authoredPlaySoundActions": authored_play_sound_actions,
        "animationOwners": animation_audio.get("owners") or [],
        "unownedAnimationEvents": animation_audio.get("unownedEvents") or {},
        "profileVoiceOwners": profile_voices.get("owners") or [],
        "counts": {
            "gameplayCharacterSkills": len(character_skills),
            "audioOwnedSkills": len(owned_skill_ids),
            "audioReferences": sum(len(owner.get("events") or {}) for owner in owners),
            "audioEventNames": len(event_names),
            "enemyTemplatesWithSkillReferences": len(enemy_template_skills),
            "enemyTemplateSkillReferences": sum(len(skills) for skills in enemy_template_skills.values()),
            **(buff_play_sound.get("counts") or {}),
            "buffPlaySoundSeededEventRefs": seeded_play_sound_events,
            **play_sound_owner_counts,
            **(animation_audio.get("counts") or {}),
            **(profile_voices.get("counts") or {}),
        },
        "animationControllerIndex": animation_audio.get("animationControllerIndex") or {},
    }


def compact_gameplay_audio_link(entry: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: entry[key]
        for key in GAMEPLAY_AUDIO_LINK_FIELDS
        if entry.get(key) is not None
    }
    if compact.get("wwiseMediaEvidence"):
        compact["wwiseMediaEvidence"] = [
            {
                key: row[key]
                for key in (
                    "rootActionIds", "soundObjectCount", "relationTypes",
                    "selectionPaths", "bankId", "bankPackage",
                )
                if row.get(key) not in (None, "", [])
            }
            for row in compact["wwiseMediaEvidence"]
            if isinstance(row, dict)
        ]
    return compact


def link_gameplay_audio(
    webui_root: Path,
    language: str,
    references: dict[str, Any],
    event_audio_by_id: dict[str, list[dict[str, Any]]],
    event_evidence: list[dict[str, Any]],
    dialog_audio_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, int]:
    """Write compact Gameplay SFX sidecar with typed possible media leaves."""

    event_evidence_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in event_evidence:
        event_key = str(row.get("eventId") or "").strip().lower() if isinstance(row, dict) else ""
        if event_key:
            event_evidence_by_id[event_key].append(row)
    found_events = set(event_evidence_by_id)
    event_cache: dict[str, dict[str, Any]] = {}

    def gameplay_trigger_binding(owner: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
        owner_kind = str(owner.get("ownerKind") or "")
        confidence = str(owner.get("confidence") or "inferred")
        method = str(owner.get("ownershipMethod") or "")
        evidence_kinds = sorted({str(row.get("kind") or "") for row in evidence if isinstance(row, dict) and row.get("kind")})
        relation_types: list[str] = []
        if "skillData" in evidence_kinds:
            relation_types.append("skillDataEventReference")
        if "skillBuffData" in evidence_kinds:
            relation_types.append("skillBuffChain")
        if "enemyBornBuffData" in evidence_kinds:
            relation_types.append("enemyBornBuffChain")
        play_sound_actions = [
            action
            for row in evidence
            if isinstance(row, dict)
            for action in row.get("playSoundActions") or []
            if isinstance(action, dict)
        ]
        if play_sound_actions:
            relation_types.append("buffPlaySoundAction")
        if owner_kind == "character" and confidence == "direct" and method == "gameplaySkillId":
            status = "exactSkillConfig"
        elif owner_kind == "enemy" and confidence == "direct" and method == "enemyBornBuffField":
            status = "exactEnemyBornBuffConfig"
        else:
            status = "inferredSkillConfigOwner"
        if play_sound_actions:
            request_evidence = (
                "exactAuthoredPlaySoundAction"
                if status != "inferredSkillConfigOwner"
                else "inferredOwnerExactAuthoredPlaySoundAction"
            )
            activation_status = "authoredFrameWindowRecoveredConditionUnresolved"
        else:
            request_evidence = (
                "exactAuthoredDependency"
                if status != "inferredSkillConfigOwner"
                else "inferredOwnerExactAuthoredDependency"
            )
            activation_status = "conditionAndTimingUnresolved"
        binding = {
            "status": status,
            "requestEvidence": request_evidence,
            "runtimeActivationStatus": activation_status,
            "ownerKind": owner_kind,
            "ownerId": str(owner.get("ownerId") or ""),
            "groupId": str(owner.get("groupId") or ""),
            "skillId": str(owner.get("skillId") or ""),
            "confidence": confidence,
            "ownershipMethod": method,
            "relationTypes": relation_types,
            "evidenceKinds": evidence_kinds,
            "buffIds": sorted({
                str(buff_id)
                for row in evidence
                if isinstance(row, dict)
                for buff_id in row.get("buffIds") or []
                if str(buff_id)
            }),
            "sourcePaths": sorted(set(filter(None, [
                *(owner.get("sources") or []),
                *(owner.get("ownershipSources") or []),
                *(
                    source_path
                    for action in play_sound_actions
                    for source_path in action.get("sourcePaths") or []
                ),
            ]))),
        }
        if play_sound_actions:
            binding["playSoundActions"] = play_sound_actions
        return binding

    def linked_event(event_id: str) -> dict[str, Any]:
        event_key = event_id.lower()
        if event_key in event_cache:
            return event_cache[event_key]
        media: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for entry in event_audio_by_id.get(event_key) or []:
            compact = compact_gameplay_audio_link(entry)
            key = (str(compact.get("src") or ""), str(compact.get("mediaId") or ""))
            if not key[0] or key in seen:
                continue
            seen.add(key)
            media.append(compact)
        content_counts = Counter(
            str(row.get("contentSha256") or "")
            for row in media
            if row.get("contentSha256")
        )
        for row in media:
            content_hash = str(row.get("contentSha256") or "")
            if content_hash and content_counts[content_hash] > 1:
                row["contentEquivalentCount"] = content_counts[content_hash]
        evidence_rows = event_evidence_by_id.get(event_key, [])
        selector_containers: dict[str, dict[str, int]] = {}
        seen_selector_nodes: set[tuple[int, int]] = set()
        for definition_index, evidence_row in enumerate(evidence_rows):
            bank_id = int(evidence_row.get("bankId") or definition_index)
            for container in evidence_row.get("containerEvidence") or []:
                if not isinstance(container, dict):
                    continue
                object_id = int(container.get("objectId") or 0)
                node_key = (bank_id, object_id)
                if object_id and node_key in seen_selector_nodes:
                    continue
                if object_id:
                    seen_selector_nodes.add(node_key)
                object_type = int(container.get("objectType") or 0)
                if object_type == 5:
                    selector_kind = "sequenceItem" if int(container.get("mode") or 0) == 1 else "randomAlternative"
                else:
                    selector_kind = {
                        6: "switchCandidate",
                        7: "groupChild",
                        9: "layerChild",
                    }.get(object_type, str(container.get("edgeKind") or "unknown"))
                counts = selector_containers.setdefault(selector_kind, {"nodeCount": 0, "childEdgeCount": 0})
                counts["nodeCount"] += 1
                counts["childEdgeCount"] += int(container.get("childCount") or 0)
        selector_evidence = {
            "bankDefinitionCount": len(evidence_rows),
            "rootStopActionCount": sum(int(row.get("rootStopActionCount") or 0) for row in evidence_rows),
            "containers": selector_containers,
        }
        action_dispatch_evidence: list[dict[str, Any]] = []
        for evidence_row in evidence_rows:
            dispatch = evidence_row.get("actionDispatchEvidence") or {}
            if not isinstance(dispatch, dict) or not dispatch:
                continue
            actions: list[dict[str, Any]] = []
            for action in evidence_row.get("actionEvidence") or []:
                if not isinstance(action, dict) or action.get("operation") not in {"play", "playEvent"}:
                    continue
                actions.append({
                    "actionId": action.get("actionId"),
                    "eventActionOrdinal": action.get("eventActionOrdinal"),
                    "operation": action.get("operation"),
                    "actionParserStatus": action.get("actionParserStatus"),
                    "delay": action.get("delay") or {},
                    "transition": action.get("transition") or {},
                    "probability": action.get("probability") or {},
                })
            action_dispatch_evidence.append({
                "bankId": evidence_row.get("bankId"),
                "bankVersion": evidence_row.get("bankVersion"),
                "timingClass": dispatch.get("timingClass"),
                "playbackActionCount": int(dispatch.get("playbackActionCount") or 0),
                "typedPlaybackActionCount": int(dispatch.get("typedPlaybackActionCount") or 0),
                "failedPlaybackActionCount": int(dispatch.get("failedPlaybackActionCount") or 0),
                "multiPlayback": bool(dispatch.get("multiPlayback")),
                "simultaneityCandidate": bool(dispatch.get("simultaneityCandidate")),
                "explicitDelayActionCount": int(dispatch.get("explicitDelayActionCount") or 0),
                "explicitTransitionActionCount": int(dispatch.get("explicitTransitionActionCount") or 0),
                "probabilityGatedActionCount": int(dispatch.get("probabilityGatedActionCount") or 0),
                "evidenceBoundary": dispatch.get("evidenceBoundary"),
                "actions": actions,
            })
        root_action_ids = sorted({
            int(root_action_id)
            for item in media
            for row in item.get("wwiseMediaEvidence") or []
            for root_action_id in row.get("rootActionIds") or []
            if isinstance(root_action_id, int)
        })
        relation_types = sorted({
            str(relation)
            for item in media
            for row in item.get("wwiseMediaEvidence") or []
            for relation in row.get("relationTypes") or []
            if str(relation)
        })
        traversal_status = (
            "partial" if any(row.get("traversalStatus") == "partial" for row in evidence_rows)
            else "complete" if evidence_rows else "unresolved"
        )
        value = {
            "id": event_id,
            "foundInWwise": event_key in found_events,
            "hasPlayableMedia": bool(media),
            "possibleMediaCount": len(media),
            "playableCandidates": len(media),
            "playRootCount": len(root_action_ids) or max(
                (int(row.get("rootPlayActionCount") or 0) for row in evidence_rows),
                default=0,
            ),
            "playRootActionIds": root_action_ids,
            "mediaRelationTypes": relation_types,
            "traversalStatus": traversal_status,
            "unresolvedNodeCount": sum(len(row.get("unresolvedNodes") or []) for row in evidence_rows),
            "selectorEvidence": selector_evidence,
            "actionDispatchEvidence": action_dispatch_evidence,
            "runtimeSelection": (
                "eventNotFoundInWwise" if event_key not in found_events
                else "noDecodedPossibleMedia" if not media
                else "runtimeBranchUnresolved" if any(value != "directSound" for value in relation_types)
                else "multiplePlayRootsTimingUnresolved" if len(root_action_ids) > 1
                else "singlePossibleMedia" if len(media) == 1
                else "multiplePossibleMediaUnresolved"
            ),
            "audio": media,
        }
        event_cache[event_key] = value
        return value

    characters: dict[str, dict[str, Any]] = {}
    enemies: dict[str, dict[str, Any]] = {}
    animation_event_catalog: dict[str, dict[str, Any]] = {}
    discovered_refs = 0
    linked_refs = 0
    candidate_count = 0
    animation_linked_refs = 0
    animation_candidate_count = 0
    profile_voice_linked_refs = 0
    profile_voice_media_keys: set[str] = set()

    def normalized_animation_events(owner: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
        merged: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for authored_event_id, evidence_rows in (owner.get("events") or {}).items():
            authored = str(authored_event_id or "").strip()
            event_key = authored.lower()
            if not event_key:
                continue
            for evidence in evidence_rows or []:
                row = dict(evidence) if isinstance(evidence, dict) else {"value": evidence}
                row.setdefault("authoredEventId", authored)
                merged[event_key].append(row)
        return sorted(merged.items())

    animation_owner_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    for owner in references.get("animationOwners") or []:
        owner_kind = str(owner.get("ownerKind") or "")
        owner_id = str(owner.get("ownerId") or "")
        if owner_kind not in {"character", "enemy"} or not owner_id:
            continue
        for event_key, _evidence in normalized_animation_events(owner):
            animation_owner_ids[(owner_kind, event_key)].add(owner_id)
    for owner in references.get("owners") or []:
        event_rows: list[dict[str, Any]] = []
        for event_id, evidence in sorted((owner.get("events") or {}).items()):
            discovered_refs += 1
            linked = linked_event(event_id)
            candidates = int(linked.get("playableCandidates") or 0)
            if candidates:
                linked_refs += 1
                candidate_count += candidates
            event_rows.append({
                **linked,
                "evidence": evidence,
                "triggerBindings": [gameplay_trigger_binding(owner, evidence)],
            })
        if not event_rows:
            continue
        owner_kind = str(owner.get("ownerKind") or "")
        owner_id = str(owner.get("ownerId") or "")
        if owner_kind == "character":
            group_id = str(owner.get("groupId") or "")
            groups = characters.setdefault(owner_id, {"groups": {}})["groups"]
            group = groups.setdefault(group_id, {"skillIds": [], "events": []})
            skill_id = str(owner.get("skillId") or "")
            if skill_id and skill_id not in group["skillIds"]:
                group["skillIds"].append(skill_id)
            group.setdefault("ownershipConfidence", []).append(owner.get("confidence") or "direct")
            group.setdefault("ownershipMethods", []).append(owner.get("ownershipMethod") or "")
            group.setdefault("ownershipSources", []).extend(owner.get("ownershipSources") or [])
            existing = {str(row.get("id") or ""): row for row in group["events"]}
            for event in event_rows:
                event_id = str(event.get("id") or "")
                if event_id not in existing:
                    event["sourceSkillIds"] = [skill_id] if skill_id else []
                    group["events"].append(event)
                    existing[event_id] = event
                else:
                    existing[event_id].setdefault("evidence", []).extend(event.get("evidence") or [])
                    bindings = existing[event_id].setdefault("triggerBindings", [])
                    binding_markers = {
                        json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        for binding in bindings
                    }
                    for binding in event.get("triggerBindings") or []:
                        marker = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        if marker not in binding_markers:
                            binding_markers.add(marker)
                            bindings.append(binding)
                    if skill_id and skill_id not in existing[event_id].setdefault("sourceSkillIds", []):
                        existing[event_id]["sourceSkillIds"].append(skill_id)
        elif owner_kind == "enemy":
            skill_id = str(owner.get("skillId") or "")
            record = enemies.setdefault(owner_id, {
                "skillIds": [],
                "ownershipConfidence": [],
                "ownershipMethods": [],
                "ownershipSources": [],
                "includesSpawnBuffAudio": False,
                "events": [],
            })
            if skill_id and skill_id not in record["skillIds"]:
                record["skillIds"].append(skill_id)
            if not skill_id:
                record["includesSpawnBuffAudio"] = True
            record["ownershipConfidence"].append(owner.get("confidence") or "inferred")
            record["ownershipMethods"].append(owner.get("ownershipMethod") or "")
            record["ownershipSources"].extend(owner.get("ownershipSources") or [])
            existing = {str(row.get("id") or ""): row for row in record["events"]}
            for event in event_rows:
                event_id = str(event.get("id") or "")
                if event_id not in existing:
                    event["sourceSkillIds"] = [skill_id] if skill_id else []
                    record["events"].append(event)
                    existing[event_id] = event
                else:
                    existing[event_id].setdefault("evidence", []).extend(event.get("evidence") or [])
                    bindings = existing[event_id].setdefault("triggerBindings", [])
                    binding_markers = {
                        json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        for binding in bindings
                    }
                    for binding in event.get("triggerBindings") or []:
                        marker = json.dumps(binding, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        if marker not in binding_markers:
                            binding_markers.add(marker)
                            bindings.append(binding)
                    if skill_id and skill_id not in existing[event_id].setdefault("sourceSkillIds", []):
                        existing[event_id]["sourceSkillIds"].append(skill_id)

    for owner in references.get("animationOwners") or []:
        owner_kind = str(owner.get("ownerKind") or "")
        owner_id = str(owner.get("ownerId") or "")
        if owner_kind not in {"character", "enemy"}:
            continue
        resolved_events: list[dict[str, Any]] = []
        for event_id, evidence in normalized_animation_events(owner):
            discovered_refs += 1
            linked = linked_event(event_id)
            candidates = int(linked.get("playableCandidates") or 0)
            if candidates:
                linked_refs += 1
                animation_linked_refs += 1
                candidate_count += candidates
                animation_candidate_count += candidates
            action_kinds = sorted({str(row.get("actionKind") or "action") for row in evidence})
            clips = sorted({str(row.get("clip") or "") for row in evidence if row.get("clip")})
            functions = sorted({str(row.get("function") or "") for row in evidence if row.get("function")})
            clip_contexts = sorted({str(row.get("clipContext") or "other") for row in evidence})
            animator_controller_contexts: list[dict[str, Any]] = []
            animator_controller_seen: set[str] = set()
            for row in evidence:
                for context in row.get("animatorControllerContexts") or []:
                    if not isinstance(context, dict):
                        continue
                    marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    if marker in animator_controller_seen:
                        continue
                    animator_controller_seen.add(marker)
                    animator_controller_contexts.append(dict(context))
            animator_controller_contexts.sort(
                key=lambda row: (
                    str(row.get("name") or ""),
                    str(row.get("sourcePath") or ""),
                    str(row.get("targetSourceFile") or ""),
                )
            )
            animator_controller_reachable_clip_count = len({
                str(row.get("clip") or "")
                for row in evidence
                if row.get("clip") and row.get("animatorControllerCount")
            })
            animator_controller_unresolved_clip_count = len({
                str(row.get("clip") or "")
                for row in evidence
                if row.get("clip") and not row.get("animatorControllerCount")
            })
            authored_event_ids = sorted({
                str(row.get("authoredEventId") or event_id)
                for row in evidence
                if str(row.get("authoredEventId") or event_id)
            })
            owner_count = len(animation_owner_ids.get((owner_kind, event_id.lower()), set())) or 1
            owner_scope = (
                "sharedPlayableCharacters" if owner_kind == "character" and owner_count > 1
                else "singlePlayableCharacter" if owner_kind == "character"
                else "sharedEnemyTemplates" if owner_count > 1
                else "singleEnemyTemplate"
            )
            event = {
                "id": event_id,
                "foundInWwise": linked.get("foundInWwise"),
                "possibleMediaCount": linked.get("possibleMediaCount"),
                "playableCandidates": linked.get("playableCandidates"),
                "playRootCount": linked.get("playRootCount"),
                "mediaRelationTypes": linked.get("mediaRelationTypes") or [],
                "selectorEvidence": linked.get("selectorEvidence") or {},
                "actionDispatchEvidence": linked.get("actionDispatchEvidence") or [],
                "traversalStatus": linked.get("traversalStatus"),
                "runtimeSelection": linked.get("runtimeSelection"),
                "evidence": evidence,
                "actionKinds": action_kinds,
                "animationFunctions": functions,
                "animationClipContexts": clip_contexts,
                "clipReachability": animation_clip_reachability_status(evidence),
                "animatorControllerCount": len(animator_controller_contexts),
                "animatorControllerContexts": animator_controller_contexts,
                "animatorControllerReachableClipCount": animator_controller_reachable_clip_count,
                "animatorControllerUnresolvedClipCount": animator_controller_unresolved_clip_count,
                "authoredEventIds": authored_event_ids,
                "eventAliases": [value for value in authored_event_ids if value != event_id],
                "sourceAnimationClips": clips,
                "animationOwnerCount": owner_count,
                "animationOwnershipScope": owner_scope,
                "possibleMediaScope": "sharedEventGraph" if owner_count > 1 else "singleOwnerEventGraph",
            }
            animation_event_catalog.setdefault(event_id.lower(), linked)
            resolved_events.append(event)
        if not resolved_events:
            continue
        if owner_kind == "character":
            record = characters.setdefault(owner_id, {"groups": {}})
        else:
            record = enemies.setdefault(owner_id, {
                "skillIds": [],
                "ownershipConfidence": [],
                "ownershipMethods": [],
                "ownershipSources": [],
                "includesSpawnBuffAudio": False,
                "events": [],
            })
        record["animationOwnershipConfidence"] = "inferred"
        record["animationOwnershipMethod"] = "animationClipActorToken"
        record.setdefault("animationOwnershipSources", []).extend(owner.get("ownershipSources") or [])
        animation_events = record.setdefault("animationEvents", [])
        existing = {str(row.get("id") or "").lower(): row for row in animation_events}
        for event in resolved_events:
            event_id = str(event.get("id") or "")
            event_key = event_id.lower()
            if event_key not in existing:
                animation_events.append(event)
                existing[event_key] = event
            else:
                current = existing[event_key]
                current.setdefault("evidence", []).extend(event.get("evidence") or [])
                current["actionKinds"] = sorted(
                    set(current.get("actionKinds") or []).union(event.get("actionKinds") or [])
                )
                current["animationFunctions"] = sorted(
                    set(current.get("animationFunctions") or []).union(event.get("animationFunctions") or [])
                )
                current["animationClipContexts"] = sorted(
                    set(current.get("animationClipContexts") or []).union(event.get("animationClipContexts") or [])
                )
                current["authoredEventIds"] = sorted(
                    set(current.get("authoredEventIds") or []).union(event.get("authoredEventIds") or [])
                )
                current["sourceAnimationClips"] = sorted(
                    set(current.get("sourceAnimationClips") or []).union(event.get("sourceAnimationClips") or [])
                )
                if event_id != current.get("id"):
                    current["eventAliases"] = sorted(
                        set(current.get("eventAliases") or []).union({event_id})
                    )

    for owner in references.get("profileVoiceOwners") or []:
        owner_id = str(owner.get("ownerId") or "")
        if not owner_id:
            continue
        resolved_voices: list[dict[str, Any]] = []
        for voice in owner.get("voices") or []:
            voice_id = str(voice.get("id") or "")
            if not voice_id:
                continue
            discovered_refs += 1
            audio = (dialog_audio_by_id or {}).get(voice_id.lower())
            if not audio:
                continue
            compact = compact_gameplay_audio_link(audio)
            if not compact.get("src"):
                continue
            linked_refs += 1
            profile_voice_linked_refs += 1
            candidate_count += 1
            profile_voice_media_keys.add(str(compact.get("src") or compact.get("mediaId") or voice_id))
            resolved_voices.append({
                "id": voice_id,
                "actionKinds": [voice.get("actionKind") or "combatVoice"],
                "runtimeSelection": "profileVoiceEntry",
                "playableCandidates": 1,
                "audio": [compact],
                "evidence": [{
                    "kind": "characterProfileVoice",
                    "characterId": voice.get("characterId"),
                    "profileVoiceIndex": voice.get("profileVoiceIndex"),
                    "triggerKey": voice.get("triggerKey") or "",
                    "source": voice.get("source") or "",
                }],
            })
        if resolved_voices:
            record = characters.setdefault(owner_id, {"groups": {}})
            record.setdefault("profileVoices", []).extend(resolved_voices)

    def finalize_trigger_event(event: dict[str, Any]) -> None:
        bindings = event.get("triggerBindings") or []
        statuses = {str(binding.get("status") or "") for binding in bindings if isinstance(binding, dict)}
        if "exactSkillConfig" in statuses:
            event["triggerBindingStatus"] = "exactSkillConfig"
        elif "exactEnemyBornBuffConfig" in statuses:
            event["triggerBindingStatus"] = "exactEnemyBornBuffConfig"
        elif bindings:
            event["triggerBindingStatus"] = "inferredSkillConfigOwner"
        event["triggerRelationTypes"] = sorted({
            str(relation)
            for binding in bindings
            if isinstance(binding, dict)
            for relation in binding.get("relationTypes") or []
            if str(relation)
        })

    for value in characters.values():
        for group in value.get("groups", {}).values():
            group["skillIds"].sort()
            group["ownershipConfidence"] = "inferred" if "inferred" in group.pop("ownershipConfidence", []) else "direct"
            group["ownershipMethods"] = sorted(set(filter(None, group.get("ownershipMethods") or [])))
            group["ownershipSources"] = sorted(set(filter(None, group.get("ownershipSources") or [])))
            for event in group["events"]:
                finalize_trigger_event(event)
            group["events"].sort(key=lambda row: str(row.get("id") or ""))
        value["animationOwnershipSources"] = sorted(set(filter(None, value.get("animationOwnershipSources") or [])))
        value.get("animationEvents", []).sort(key=lambda row: str(row.get("id") or ""))
        value.get("profileVoices", []).sort(key=lambda row: str(row.get("id") or ""))
    for value in enemies.values():
        value["skillIds"].sort()
        for event in value["events"]:
            finalize_trigger_event(event)
        value["events"].sort(key=lambda row: str(row.get("id") or ""))
        value["ownershipConfidence"] = "inferred" if "inferred" in value.pop("ownershipConfidence", []) else "direct"
        value["ownershipMethods"] = sorted(set(filter(None, value.get("ownershipMethods") or [])))
        value["ownershipSources"] = sorted(set(filter(None, value.get("ownershipSources") or [])))
        value["animationOwnershipSources"] = sorted(set(filter(None, value.get("animationOwnershipSources") or [])))
        value.get("animationEvents", []).sort(key=lambda row: str(row.get("id") or ""))

    def possible_media_count(event: dict[str, Any]) -> int:
        return len([row for row in event.get("audio") or [] if row.get("src")]) or int(
            event.get("possibleMediaCount") or event.get("playableCandidates") or 0
        )

    def character_audio_metrics(value: dict[str, Any]) -> dict[str, int]:
        skill_events = [
            event
            for group in (value.get("groups") or {}).values()
            for event in group.get("events") or []
        ]
        animation_events = list(value.get("animationEvents") or [])
        profile_voices = list(value.get("profileVoices") or [])
        wwise_event_keys = {
            str(event.get("id") or "").lower()
            for event in [*skill_events, *animation_events]
            if event.get("id")
        }
        event_media_pairs: set[tuple[str, str]] = set()
        media_ids: set[str] = set()
        content_hashes: set[str] = set()
        for event_key in wwise_event_keys:
            linked = event_cache.get(event_key)
            if not isinstance(linked, dict):
                continue
            for media in linked.get("audio") or []:
                media_key = str(media.get("mediaId") or media.get("src") or "")
                if not media_key:
                    continue
                event_media_pairs.add((event_key, media_key))
                media_ids.add(media_key)
                if media.get("contentSha256"):
                    content_hashes.add(str(media["contentSha256"]))
        for voice in profile_voices:
            for media in voice.get("audio") or []:
                media_key = str(media.get("mediaId") or media.get("src") or "")
                if media_key:
                    media_ids.add(media_key)
                if media.get("contentSha256"):
                    content_hashes.add(str(media["contentSha256"]))
        shared_animation = [
            event for event in animation_events
            if int(event.get("animationOwnerCount") or 0) > 1
        ]
        single_owner_animation = [
            event for event in animation_events
            if int(event.get("animationOwnerCount") or 0) <= 1
        ]
        return {
            "skillEventAssociationCount": len(skill_events),
            "skillUniqueEventCount": len({str(event.get("id") or "").lower() for event in skill_events if event.get("id")}),
            "skillPossibleMediaAssociationCount": sum(possible_media_count(event) for event in skill_events),
            "exactSkillTriggerEventCount": sum(event.get("triggerBindingStatus") == "exactSkillConfig" for event in skill_events),
            "inferredSkillTriggerEventCount": sum(event.get("triggerBindingStatus") != "exactSkillConfig" for event in skill_events),
            "animationEventCount": len(animation_events),
            "animationCallbackOccurrenceCount": sum(int(event.get("animationOccurrenceCount") or len(event.get("evidence") or [])) for event in animation_events),
            "animationPossibleMediaAssociationCount": sum(possible_media_count(event) for event in animation_events),
            "sharedAnimationEventCount": len(shared_animation),
            "sharedAnimationPossibleMediaAssociationCount": sum(possible_media_count(event) for event in shared_animation),
            "singleOwnerAnimationEventCount": len(single_owner_animation),
            "singleOwnerAnimationPossibleMediaAssociationCount": sum(possible_media_count(event) for event in single_owner_animation),
            "footstepSystemEventCount": sum("OnCustomFootStep" in (event.get("animationFunctions") or []) for event in animation_events),
            "directProfileFileCount": sum(possible_media_count(event) for event in profile_voices),
            "eventAssociationCount": len(skill_events) + len(animation_events),
            "candidateAssociationCount": sum(possible_media_count(event) for event in [*skill_events, *animation_events, *profile_voices]),
            "uniqueWwiseEventCount": len(wwise_event_keys),
            "uniqueEventMediaPairCount": len(event_media_pairs),
            "uniqueMediaIdCount": len(media_ids),
            "knownUniqueContentSha256Count": len(content_hashes),
        }

    for value in characters.values():
        value["metrics"] = character_audio_metrics(value)

    unique_event_media_pairs = sum(
        len(value.get("audio") or [])
        for value in event_cache.values()
        if isinstance(value, dict)
    )
    unique_playable_files = {
        str(audio.get("src") or audio.get("mediaId") or "")
        for value in event_cache.values()
        if isinstance(value, dict)
        for audio in value.get("audio") or []
        if audio.get("src") or audio.get("mediaId")
    }
    unique_playable_files.update(profile_voice_media_keys)
    character_animation_event_keys = {
        str(event.get("id") or "").lower()
        for owner in characters.values()
        for event in owner.get("animationEvents") or []
        if event.get("id")
    }
    character_animation_shared_event_keys = {
        key for key in character_animation_event_keys
        if len(animation_owner_ids.get(("character", key), set())) > 1
    }
    character_animation_shared_associations = sum(
        1
        for owner in characters.values()
        for event in owner.get("animationEvents") or []
        if int(event.get("animationOwnerCount") or 0) > 1
    )
    character_animation_single_owner_possible_media = sum(
        int(event.get("possibleMediaCount") or event.get("playableCandidates") or 0)
        for owner in characters.values()
        for event in owner.get("animationEvents") or []
        if int(event.get("animationOwnerCount") or 0) <= 1
    )
    character_animation_shared_graph_possible_media = sum(
        int((animation_event_catalog.get(key) or {}).get("possibleMediaCount") or 0)
        for key in character_animation_shared_event_keys
    )
    serialized_skill_events = [
        event
        for owner in characters.values()
        for group in (owner.get("groups") or {}).values()
        for event in group.get("events") or []
    ] + [
        event
        for owner in enemies.values()
        for event in owner.get("events") or []
    ]
    serialized_animation_events = [
        event
        for bucket in (characters, enemies)
        for owner in bucket.values()
        for event in owner.get("animationEvents") or []
    ]
    serialized_profile_voices = [
        event
        for owner in characters.values()
        for event in owner.get("profileVoices") or []
    ]
    serialized_refs = len(serialized_skill_events) + len(serialized_animation_events) + len(serialized_profile_voices)
    serialized_playable_refs = sum(
        possible_media_count(event) > 0
        for event in [*serialized_skill_events, *serialized_animation_events, *serialized_profile_voices]
    )
    serialized_candidate_associations = sum(
        possible_media_count(event)
        for event in [*serialized_skill_events, *serialized_animation_events, *serialized_profile_voices]
    )
    serialized_animation_candidates = sum(possible_media_count(event) for event in serialized_animation_events)
    serialized_exact_skill_triggers = sum(
        event.get("triggerBindingStatus") == "exactSkillConfig"
        for event in serialized_skill_events
    )
    serialized_exact_enemy_born_triggers = sum(
        event.get("triggerBindingStatus") == "exactEnemyBornBuffConfig"
        for event in serialized_skill_events
    )
    serialized_inferred_skill_triggers = sum(
        event.get("triggerBindingStatus") == "inferredSkillConfigOwner"
        for event in serialized_skill_events
    )
    stats = {
        **(references.get("counts") or {}),
        "gameplayAudioRefs": discovered_refs,
        "gameplayAudioRefsDiscovered": discovered_refs,
        "gameplayAudioRefsLinked": serialized_playable_refs,
        "gameplaySerializedAudioRefs": serialized_refs,
        "gameplayReferenceOnlyAudioRefs": serialized_refs - serialized_playable_refs,
        "gameplayRawAudioRefsLinked": linked_refs,
        "gameplayAudioCandidates": unique_event_media_pairs + len(profile_voice_media_keys),
        "gameplayPossibleMediaAssociations": serialized_candidate_associations,
        "gameplaySerializedPossibleMediaAssociations": serialized_candidate_associations,
        "gameplayRawPossibleMediaAssociations": candidate_count,
        "exactSkillConfigTriggerRefs": serialized_exact_skill_triggers,
        "exactEnemyBornBuffTriggerRefs": serialized_exact_enemy_born_triggers,
        "inferredSkillConfigOwnerRefs": serialized_inferred_skill_triggers,
        "gameplayUniqueEventMediaPairs": unique_event_media_pairs,
        "gameplayUniquePlayableFiles": len(unique_playable_files),
        "animationAudioRefsLinked": sum(possible_media_count(event) > 0 for event in serialized_animation_events),
        "animationAudioRefsSerialized": len(serialized_animation_events),
        "animationAudioRawRefsLinked": animation_linked_refs,
        "animationAudioPossibleMediaAssociations": serialized_animation_candidates,
        "animationAudioRawPossibleMediaAssociations": animation_candidate_count,
        "characterAnimationUniqueEvents": len(character_animation_event_keys),
        "characterAnimationSharedEvents": len(character_animation_shared_event_keys),
        "characterAnimationSharedEventAssociations": character_animation_shared_associations,
        "characterAnimationSingleOwnerPossibleMediaAssociations": character_animation_single_owner_possible_media,
        "characterAnimationSharedGraphPossibleMedia": character_animation_shared_graph_possible_media,
        "profileVoiceRefsLinked": profile_voice_linked_refs,
        "charactersWithPlayableSfx": len(characters),
        "enemiesWithPlayableSfx": len(enemies),
    }
    path = webui_root / Path(str(GAMEPLAY_SFX_REL).format(language=language))
    animation_evidence: dict[str, Any] = {
        "characters": {},
        "enemies": {},
    }
    for bucket_name, bucket in (("characters", characters), ("enemies", enemies)):
        for owner_id, owner in bucket.items():
            evidence_events: list[dict[str, Any]] = []
            for event in owner.get("animationEvents") or []:
                evidence_events.append({
                    "id": event.get("id"),
                    "actionKinds": event.get("actionKinds") or [],
                    "animationFunctions": event.get("animationFunctions") or [],
                    "animationClipContexts": event.get("animationClipContexts") or [],
                    "clipReachability": event.get("clipReachability") or "unresolved",
                    "animatorControllerCount": int(event.get("animatorControllerCount") or 0),
                    "animatorControllerContexts": event.get("animatorControllerContexts") or [],
                    "animatorControllerReachableClipCount": int(
                        event.get("animatorControllerReachableClipCount") or 0
                    ),
                    "animatorControllerUnresolvedClipCount": int(
                        event.get("animatorControllerUnresolvedClipCount") or 0
                    ),
                    "sourceAnimationClips": event.get("sourceAnimationClips") or [],
                    "animationOwnerCount": event.get("animationOwnerCount"),
                    "animationOwnershipScope": event.get("animationOwnershipScope"),
                    "possibleMediaScope": event.get("possibleMediaScope"),
                    "authoredEventIds": event.get("authoredEventIds") or [],
                    "eventAliases": event.get("eventAliases") or [],
                    "evidence": event.get("evidence") or [],
                })
                clips = event.get("sourceAnimationClips") or []
                event["animationClipCount"] = len(clips)
                event["sourceAnimationClips"] = clips[:4]
                event["animationOccurrenceCount"] = len(event.get("evidence") or [])
                event.pop("evidence", None)
            if evidence_events:
                animation_evidence[bucket_name][owner_id] = evidence_events
    unresolved_animation_events: list[dict[str, Any]] = []
    for event_id, evidence in sorted((references.get("unownedAnimationEvents") or {}).items()):
        rows = [row for row in evidence or [] if isinstance(row, dict)]
        controller_contexts: list[dict[str, Any]] = []
        controller_context_seen: set[str] = set()
        for row in rows:
            for context in row.get("animatorControllerContexts") or []:
                if not isinstance(context, dict):
                    continue
                marker = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                if marker in controller_context_seen:
                    continue
                controller_context_seen.add(marker)
                controller_contexts.append(dict(context))
        controller_contexts.sort(
            key=lambda row: (
                str(row.get("name") or ""),
                str(row.get("sourcePath") or ""),
                str(row.get("targetSourceFile") or ""),
            )
        )
        controller_reachable_clips = len({
            str(row.get("clip") or "")
            for row in rows
            if row.get("clip") and row.get("animatorControllerCount")
        })
        controller_unresolved_clips = len({
            str(row.get("clip") or "")
            for row in rows
            if row.get("clip") and not row.get("animatorControllerCount")
        })
        unresolved_animation_events.append({
            "id": event_id,
            "actionKinds": sorted({str(row.get("actionKind") or "action") for row in rows}),
            "animationFunctions": sorted({str(row.get("function") or "") for row in rows if row.get("function")}),
            "animationClipContexts": sorted({str(row.get("clipContext") or "other") for row in rows}),
            "clipReachability": animation_clip_reachability_status(rows),
            "animatorControllerCount": len(controller_contexts),
            "animatorControllerContexts": controller_contexts,
            "animatorControllerReachableClipCount": controller_reachable_clips,
            "animatorControllerUnresolvedClipCount": controller_unresolved_clips,
            "sourceAnimationClips": sorted({str(row.get("clip") or "") for row in rows if row.get("clip")}),
            "authoredEventIds": sorted({
                str(row.get("authoredEventId") or event_id)
                for row in rows
                if str(row.get("authoredEventId") or event_id)
            }),
            "ownerStatus": "unresolved",
            "evidence": rows,
        })
    if unresolved_animation_events:
        animation_evidence["ownerUnresolved"] = unresolved_animation_events
    json_dump(path.with_name(GAMEPLAY_SFX_ANIMATION_CATALOG_NAME), {
        "schemaVersion": 1,
        "language": language,
        "events": animation_event_catalog,
    })
    json_dump(path.with_name(GAMEPLAY_SFX_ANIMATION_EVIDENCE_NAME), {
        "schemaVersion": GAMEPLAY_SFX_ANIMATION_EVIDENCE_SCHEMA_VERSION,
        "language": language,
        "animationControllerIndex": references.get("animationControllerIndex") or {},
        **animation_evidence,
    })
    json_dump(path, {
        "schemaVersion": 4,
        "language": language,
        "counts": stats,
        "animationEventCatalogPath": GAMEPLAY_SFX_ANIMATION_CATALOG_NAME,
        "animationEvidencePath": GAMEPLAY_SFX_ANIMATION_EVIDENCE_NAME,
        "authoredPlaySoundActions": references.get("authoredPlaySoundActions") or [],
        "characters": characters,
        "enemies": enemies,
        "scope": {
            "source": "SkillData/BuffData event references, decoded BuffData PlaySound actions, EnemyData ability bundles, AnimationClip audio callbacks, CharacterTable profile voices, and Wwise HIRC traversal",
            "playSoundActionBoundary": "Current MemoryPack PlaySoundActionData yields exact event, frame window, stop/fade, routing, and time-dilation controls. TargetSettings semantics and runtime activation conditions remain unresolved.",
            "characterOwnership": "direct gameplay skill id",
            "characterFamilyOwnership": "longest playable skill id prefix inferred for authored child SkillData",
            "enemyOwnership": "exact SkillData identifiers recovered from enemy-template AbilitySystemData, with enemy-id prefix fallback and exact born-buff fields",
            "enemyTemplateBoundary": "AbilitySystemData containment is exact, while identifiers preserved only in partially decoded string-hint tails remain ownership-inferred.",
            "animationOwnership": "exact AnimationClip callback, timestamp, and payload; actor ownership inferred from exact character/enemy animation tokens and recovered enemy animation-config reuse; direct resolved AnimatorController PPtrs now annotate clip reachability, while override-controller pairs and runtime state reachability remain unresolved",
            "animationControllerBoundary": "A direct resolved AnimationClip PPtr in an exported AnimatorController proves authored controller membership only. AnimatorOverrideController pairs, Timeline/Playable bindings, controller state selection, and live Animator execution remain unresolved; no animation callback is promoted into a skill trigger by this evidence.",
            "unownedAnimationBoundary": "Every actor/monster AnimationClip callback with a supported audio function is retained. Clips without a bounded playable-character or enemy-template token stay owner-unresolved and appear only in the debug Audio evidence surface; generic non-actor clip indexing remains a separate exporter gap.",
            "animationMediaBoundary": "An owned clip proves that its callback requests the Event. Shared playable-character Events expose a shared Wwise selector graph; its reachable leaves are not attributed to one character until switch/state values are decoded.",
            "profileVoiceOwnership": "direct CharacterTable.profileVoice ownership linked to the exact AudioDialog path stem; bark/random selection remains unresolved",
            "referenceOnlyBoundary": "Exact SkillData/BuffData and owned AnimationClip trigger contexts remain serialized when the Event is absent from current Wwise banks or has no decoded possible media; Gameplay only renders records with playable files.",
            "runtimeSelection": "Possible media files come from typed Wwise v150 edges and are grouped by Play root and selector relation; the live branch selected by switches, states, random/sequence containers, and layers remains unresolved.",
            "actionDispatchBoundary": "Typed v150 Event Action ordinals and serialized DelayTime, TransitionTime, and Probability properties are preserved. They prove authored dispatch membership and controls, not live action execution, evaluated probability, or sample-accurate audible simultaneity.",
        },
    })
    return stats


def projectile_sound_hashes(webui_root: Path) -> set[int]:
    payload = load_json(webui_root / PROJECTILE_DATA_REL, {})
    hashes: set[int] = set()
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        sounds = entry.get("sounds") or {}
        for field in PROJECTILE_SOUND_FIELDS:
            value = sounds.get(field)
            raw = value.get("value") if isinstance(value, dict) else value
            if isinstance(raw, int) and raw:
                hashes.add(raw & 0xFFFFFFFF)
    return hashes


def link_projectile_audio(
    webui_root: Path,
    event_audio_by_id: dict[str, list[dict[str, Any]]],
    event_evidence: list[dict[str, Any]],
) -> dict[str, int]:
    """Attach typed HIRC event-to-media leaves to projectile sound fields."""

    path = webui_root / PROJECTILE_DATA_REL
    payload = load_json(path, {})
    entries = payload.get("entries") or []
    if not isinstance(payload, dict) or not isinstance(entries, list):
        return {"projectileSoundRefs": 0, "projectileSoundEvents": 0, "projectileSoundRefsLinked": 0, "projectileAudioCandidates": 0}

    evidence_by_hash: dict[int, list[dict[str, Any]]] = defaultdict(list)
    event_ids_by_hash: dict[int, set[str]] = defaultdict(set)
    for row in event_evidence:
        if not isinstance(row, dict):
            continue
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        event_id = str(row.get("eventId") or "").strip()
        if not event_id:
            continue
        evidence_by_hash[event_hash].append(row)
        event_ids_by_hash[event_hash].add(event_id)

    refs = 0
    linked_refs = 0
    candidates = 0
    resolved_hashes: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        sounds = entry.get("sounds") or {}
        if not isinstance(sounds, dict):
            continue
        for field in PROJECTILE_SOUND_FIELDS:
            value = sounds.get(field)
            if not isinstance(value, dict):
                continue
            value.pop("event", None)
            value.pop("audio", None)
            raw = value.get("value")
            if not isinstance(raw, int) or not raw:
                continue
            refs += 1
            event_hash = raw & 0xFFFFFFFF
            key = projectile_event_key(event_hash)
            evidence = evidence_by_hash.get(event_hash) or []
            media: list[dict[str, Any]] = []
            seen_media: set[tuple[str, str]] = set()
            canonical_event_ids = sorted(event_ids_by_hash.get(event_hash) or {key})
            for canonical_event_id in canonical_event_ids:
                for audio in event_audio_by_id.get(canonical_event_id, []):
                    src = str(audio.get("src") or "")
                    media_id = str(audio.get("mediaId") or audio.get("id") or "")
                    dedupe_key = (src, media_id)
                    if not src or dedupe_key in seen_media:
                        continue
                    seen_media.add(dedupe_key)
                    media.append({
                        key: audio[key]
                        for key in (
                            "src", "mediaId", "format", "bytes", "audioScope",
                            "audioCategory", "audioCategoryDetail", "sourceBlock",
                            "sourceBlockLabel", "sourceBank", "bankId", "bank",
                        )
                        if audio.get(key) is not None
                    })
            event_found = bool(evidence)
            if event_found:
                resolved_hashes.add(event_hash)
            if media:
                linked_refs += 1
                candidates += len(media)
            value["event"] = {
                "hash": event_hash,
                "hex": f"0x{event_hash:08x}",
                "foundInWwise": event_found,
                "playableCandidates": len(media),
                "source": "wwiseHirc" if event_found else "unresolved",
                "runtimeSelection": "unresolved" if len(media) > 1 else "singleCandidate" if media else "none",
                "canonicalEventIds": canonical_event_ids,
            }
            if media:
                value["audio"] = media

    stats = {
        "projectileSoundRefs": refs,
        "projectileSoundEvents": len(resolved_hashes),
        "projectileSoundRefsLinked": linked_refs,
        "projectileAudioCandidates": candidates,
    }
    payload["audioLinks"] = {
        **stats,
        "source": "Wwise HIRC event traversal",
        "note": "Playable files are typed possible media leaves; Play roots and runtime switch/container selection remain unresolved.",
    }
    json_dump(path, payload)
    return stats


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
    payload = load_json(path, {})
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


def display_path(path: Path) -> str:
    return normalize_posix(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


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


def read_decrypted_akpk(path: Path) -> bytes:
    return decrypt_akpk_bytes(path.read_bytes(), str(path))


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


def iter_akpk_bank_payloads(path: Path) -> list[tuple[int, bytes]]:
    return iter_akpk_bank_payloads_from_bytes(path.read_bytes(), normalize_posix(path))


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


def hirc_action_type(data: bytes) -> int | None:
    if len(data) < 2:
        return None
    return unpack_from("<H", data, 0)[0]


def _hirc_v150_action_property_value(property_id: int, raw: bytes) -> dict[str, Any]:
    row: dict[str, Any] = {
        "rawHex": raw.hex(),
        "rawU32": unpack_from("<I", raw, 0)[0],
    }
    if property_id in {0x39, 0x3A}:
        row.update({
            "encoding": "signedInt32Milliseconds",
            "value": unpack_from("<i", raw, 0)[0],
            "unit": "ms",
        })
    elif property_id == 0x3B:
        row.update({
            "encoding": "float32Percent",
            "value": unpack_from("<f", raw, 0)[0],
            "unit": "percent",
        })
    else:
        row["encoding"] = "rawUnion32"
    return row


def _hirc_v150_action_property_summary(
    property_id: int,
    properties: list[dict[str, Any]],
    ranged_modifiers: list[dict[str, Any]],
) -> dict[str, Any]:
    scalar_values = [
        row["value"]
        for row in properties
        if row["propertyId"] == property_id and "value" in row
    ]
    modifier_ranges = [
        {
            "minimum": row["minimum"]["value"],
            "maximum": row["maximum"]["value"],
        }
        for row in ranged_modifiers
        if row["propertyId"] == property_id
        and "value" in row["minimum"]
        and "value" in row["maximum"]
    ]
    if scalar_values and modifier_ranges:
        status = "explicitBaseAndRange"
    elif scalar_values:
        status = "explicitBase"
    elif modifier_ranges:
        status = "explicitRangeOnly"
    else:
        status = "implicitDefaultNotSerialized"
    suffix = "Percent" if property_id == 0x3B else "Ms"
    summary: dict[str, Any] = {
        "serializationStatus": status,
        f"baseValues{suffix}": scalar_values,
        f"modifierRanges{suffix}": modifier_ranges,
    }
    if modifier_ranges:
        summary["runtimeSelection"] = "boundedModifierUnresolved"
    if property_id == 0x3B:
        summary["runtimeSelection"] = "actionGateNotEvaluated"
    return summary


def hirc_v150_playback_action(data: bytes, bank_version: int | None) -> dict[str, Any]:
    """Decode exact v150 Play/PlayEvent Action evidence without creating edges.

    The target helpers above deliberately remain independent: a failed evidence
    parse must never suppress an otherwise valid typed playback target.  This
    decoder returns no property/timing claims unless the complete Action body is
    consumed according to its operation-specific v150 layout.
    """

    def failed(reason: str, offset: int = 0, expected_bytes: int | None = None) -> dict[str, Any]:
        failure: dict[str, Any] = {
            "reason": reason,
            "offset": offset,
            "dataSize": len(data),
            "remainingBytes": max(0, len(data) - offset),
        }
        if expected_bytes is not None:
            failure["expectedBytes"] = expected_bytes
        return {
            "actionParserStatus": "failedClosed",
            "actionParserFailure": failure,
        }

    if bank_version != 150:
        result = failed("unsupportedBankVersion")
        result["actionParserFailure"]["bankVersion"] = bank_version
        return result
    if len(data) < 7:
        return failed("truncatedActionHeader", 0, 7)

    action_type = unpack_from("<H", data, 0)[0]
    operation = action_type & 0xFF00
    if operation not in HIRC_PLAYBACK_ACTION_OPERATIONS:
        result = failed("unsupportedPlaybackOperation")
        result["actionParserFailure"]["operation"] = operation
        return result

    def read_count(offset: int, reason: str) -> tuple[int, int] | dict[str, Any]:
        if offset >= len(data):
            return failed(reason, offset, 1)
        return data[offset], offset + 1

    pos = 7
    scalar_count_row = read_count(pos, "truncatedScalarPropertyCount")
    if isinstance(scalar_count_row, dict):
        return scalar_count_row
    scalar_count, pos = scalar_count_row
    if pos + scalar_count > len(data):
        return failed("truncatedScalarPropertyIds", pos, scalar_count)
    scalar_ids = list(data[pos : pos + scalar_count])
    pos += scalar_count
    scalar_bytes = scalar_count * 4
    if pos + scalar_bytes > len(data):
        return failed("truncatedScalarPropertyValues", pos, scalar_bytes)
    properties: list[dict[str, Any]] = []
    for property_id in scalar_ids:
        value = _hirc_v150_action_property_value(property_id, data[pos : pos + 4])
        properties.append({
            "propertyId": property_id,
            "propertyName": HIRC_ACTION_PROPERTY_LABELS.get(
                property_id, f"property0x{property_id:02x}"
            ),
            **value,
        })
        pos += 4

    range_count_row = read_count(pos, "truncatedRangePropertyCount")
    if isinstance(range_count_row, dict):
        return range_count_row
    range_count, pos = range_count_row
    if pos + range_count > len(data):
        return failed("truncatedRangePropertyIds", pos, range_count)
    range_ids = list(data[pos : pos + range_count])
    pos += range_count
    range_bytes = range_count * 8
    if pos + range_bytes > len(data):
        return failed("truncatedRangePropertyValues", pos, range_bytes)
    ranged_modifiers: list[dict[str, Any]] = []
    for property_id in range_ids:
        minimum = _hirc_v150_action_property_value(property_id, data[pos : pos + 4])
        maximum = _hirc_v150_action_property_value(property_id, data[pos + 4 : pos + 8])
        ranged_modifiers.append({
            "propertyId": property_id,
            "propertyName": HIRC_ACTION_PROPERTY_LABELS.get(
                property_id, f"property0x{property_id:02x}"
            ),
            "encoding": minimum["encoding"],
            "minimum": minimum,
            "maximum": maximum,
            "runtimeSelection": "boundedModifierUnresolved",
        })
        pos += 8

    evidence: dict[str, Any] = {
        "actionParserStatus": "typedExactV150",
        "targetFlagsRaw": data[6],
        "targetIsBus": bool(data[6] & 0x01),
        "properties": properties,
        "rangedModifiers": ranged_modifiers,
        "delay": _hirc_v150_action_property_summary(0x39, properties, ranged_modifiers),
        "transition": _hirc_v150_action_property_summary(0x3A, properties, ranged_modifiers),
        "probability": _hirc_v150_action_property_summary(0x3B, properties, ranged_modifiers),
    }
    remaining = len(data) - pos
    if operation == 0x0400:
        if remaining < 9:
            return failed("truncatedPlayTail", pos, 9)
        if remaining > 9:
            return failed("unexpectedPlayTrailingBytes", pos + 9, 0)
        fade_flags = data[pos]
        curve_id = fade_flags & 0x1F
        bank_id = unpack_from("<I", data, pos + 1)[0]
        bank_type = unpack_from("<I", data, pos + 5)[0]
        evidence["fade"] = {
            "flagsRaw": fade_flags,
            "curveId": curve_id,
            "curveLabel": HIRC_FADE_CURVE_LABELS.get(curve_id, f"curve{curve_id}"),
            "bankId": bank_id,
            "bankType": bank_type,
            "bankTypeLabel": HIRC_BANK_TYPE_LABELS.get(bank_type, f"bankType{bank_type}"),
        }
    elif remaining:
        return failed("unexpectedPlayEventTrailingBytes", pos, 0)
    return evidence


def hirc_sound_media_id(data: bytes) -> int | None:
    """Return the v150 AkBankSourceData source ID from a Sound object.

    The current banks serialize U32 plugin ID at offset 0, U8 stream type at
    offset 4, and U32 source/media ID at offset 5.  The U32 at offset 22 in
    current Sound objects is the parent node and must never be traversed as a
    child reference.
    """

    if len(data) < 9:
        return None
    return unpack_from("<I", data, 5)[0]


def _hirc_v150_u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("truncated v150 U32")
    return unpack_from("<I", data, offset)[0], offset + 4


def _hirc_v150_node_base_parent(data: bytes, offset: int) -> tuple[int, int]:
    """Decode the v150 NodeBase prefix through its DirectParentID field.

    FX and metadata lists are variable length.  Reading their authored counts is
    required before the bus and parent IDs; treating the parent as an arbitrary
    U32 at a guessed offset would make reciprocal child proof circular.
    """

    if offset < 0 or offset + 2 > len(data):
        raise ValueError("truncated v150 initial FX header")
    offset += 1  # bIsOverrideParentFX
    effect_count = data[offset]
    offset += 1
    if effect_count:
        offset += 1  # bBypassAll
        effect_bytes = effect_count * 6  # U8 index + U32 ID + U8 flags
        if offset + effect_bytes > len(data):
            raise ValueError("truncated v150 initial FX list")
        offset += effect_bytes

    if offset + 2 > len(data):
        raise ValueError("truncated v150 metadata header")
    offset += 1  # bIsOverrideParentMetadata
    metadata_count = data[offset]
    offset += 1
    metadata_bytes = metadata_count * 6  # U8 index + U32 ID + U8 share-set flag
    if offset + metadata_bytes > len(data):
        raise ValueError("truncated v150 metadata list")
    offset += metadata_bytes

    _override_bus_id, offset = _hirc_v150_u32(data, offset)
    parent_id, offset = _hirc_v150_u32(data, offset)
    return parent_id, offset


def hirc_v150_music_track(data: bytes) -> dict[str, Any] | None:
    """Decode the typed prefix of a v150 MusicTrack.

    This reaches every AkBankSourceData row and the NodeBase parent without
    interpreting the later property/RTPC payload.  Every variable-length list
    is bounded against the enclosing HIRC object's bytes and failures return
    ``None`` rather than searching for media-looking integers.
    """

    try:
        if len(data) < 5:
            raise ValueError("truncated v150 MusicTrack header")
        flags = data[0]
        source_count, offset = _hirc_v150_u32(data, 1)
        sources: list[dict[str, Any]] = []
        for _ in range(source_count):
            plugin_id, offset = _hirc_v150_u32(data, offset)
            if offset + 10 > len(data):
                raise ValueError("truncated v150 MusicTrack source")
            stream_type = data[offset]
            media_id = unpack_from("<I", data, offset + 1)[0]
            memory_size = unpack_from("<I", data, offset + 5)[0]
            source_bits = data[offset + 9]
            offset += 10
            plugin_parameter_size = 0
            if plugin_id & 0x0F == 2:
                plugin_parameter_size, offset = _hirc_v150_u32(data, offset)
                if offset + plugin_parameter_size > len(data):
                    raise ValueError("truncated v150 MusicTrack plugin parameters")
                offset += plugin_parameter_size
            sources.append({
                "mediaId": media_id,
                "pluginId": plugin_id,
                "pluginType": plugin_id & 0x0F,
                "streamType": stream_type,
                "inMemoryMediaSize": memory_size,
                "sourceBits": source_bits,
                "pluginParameterSize": plugin_parameter_size,
            })

        playlist_count, offset = _hirc_v150_u32(data, offset)
        playlist_items: list[dict[str, Any]] = []
        for _ in range(playlist_count):
            if offset + 44 > len(data):
                raise ValueError("truncated v150 MusicTrack playlist")
            playlist_items.append({
                "trackId": unpack_from("<I", data, offset)[0],
                "mediaId": unpack_from("<I", data, offset + 4)[0],
                "eventId": unpack_from("<I", data, offset + 8)[0],
            })
            offset += 44  # IDs above + four F64 clip timing values.
        subtrack_count = None
        if playlist_count:
            subtrack_count, offset = _hirc_v150_u32(data, offset)

        automation_count, offset = _hirc_v150_u32(data, offset)
        automation_point_count = 0
        for _ in range(automation_count):
            if offset + 12 > len(data):
                raise ValueError("truncated v150 MusicTrack automation header")
            point_count = unpack_from("<I", data, offset + 8)[0]
            offset += 12
            point_bytes = point_count * 12  # F32 From + F32 To + U32 interpolation.
            if offset + point_bytes > len(data):
                raise ValueError("truncated v150 MusicTrack automation points")
            offset += point_bytes
            automation_point_count += point_count

        node_base_offset = offset
        parent_id, _parent_end = _hirc_v150_node_base_parent(data, node_base_offset)
        return {
            "flags": flags,
            "parentId": parent_id,
            "nodeBaseOffset": node_base_offset,
            "sourceCount": source_count,
            "sources": sources,
            "playlistItemCount": playlist_count,
            "playlistItems": playlist_items,
            "subtrackCount": subtrack_count,
            "automationCount": automation_count,
            "automationPointCount": automation_point_count,
        }
    except (ValueError, OverflowError):
        return None


def _hirc_v150_music_parent_id(data: bytes) -> int | None:
    try:
        # v150 MusicSegment/Switch/RanSeq begin with a U8 MIDI override flag,
        # followed by the common NodeBase prefix.
        parent_id, _offset = _hirc_v150_node_base_parent(data, 1)
        return parent_id
    except (ValueError, OverflowError):
        return None


def hirc_object_parent_id(object_type: int, data: bytes) -> int | None:
    if object_type == 2:
        offset = 22
    elif object_type == 11:
        track = hirc_v150_music_track(data)
        return int(track["parentId"]) if track else None
    elif object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
        return _hirc_v150_music_parent_id(data)
    elif object_type in HIRC_TYPED_CHILD_CONTAINER_TYPES:
        offset = 8
    else:
        return None
    if len(data) < offset + 4:
        return None
    return unpack_from("<I", data, offset)[0]


def hirc_reciprocal_child_list(
    object_id: int,
    object_type: int,
    data: bytes,
    objects: dict[int, dict[str, Any]],
) -> tuple[list[int], int] | None:
    """Locate one v150 Children array and prove it through parent backlinks.

    Parameter-node headers have variable-length property blocks, so the child
    count is not at one fixed byte offset.  We scan only for a bounded
    ``U32 count`` + contiguous ``count * U32 child IDs`` structure, then
    require every referenced same-bank HIRC object to expose the reciprocal
    parent ID at its type-defined field.  The earliest reciprocal block is the
    authored Children array; later repetitions are switch maps/playlists.
    """

    if object_type not in HIRC_TYPED_CHILD_CONTAINER_TYPES:
        return None
    allowed_child_types = HIRC_MUSIC_CHILD_TYPES.get(object_type, HIRC_AUDIO_NODE_TYPES)
    for offset in range(0, max(0, len(data) - 7)):
        count = unpack_from("<I", data, offset)[0]
        if count <= 0 or count > (len(data) - offset - 4) // 4:
            continue
        children = [
            unpack_from("<I", data, offset + 4 + index * 4)[0]
            for index in range(count)
        ]
        if any(child_id not in objects for child_id in children):
            continue
        if any(
            int(objects[child_id].get("type") or 0) not in allowed_child_types
            or hirc_object_parent_id(
                int(objects[child_id].get("type") or 0),
                objects[child_id].get("data") or b"",
            ) != object_id
            for child_id in children
        ):
            continue
        return children, offset
    return None


def hirc_v150_switch_mapping(
    data: bytes,
    children_offset: int,
    child_count: int,
    *,
    bank_version: int | None,
) -> dict[str, Any]:
    """Decode the bounded flat mapping tail of a v150 type-6 container.

    The current flat layout places ``groupType``, ``groupId``,
    ``defaultValueId``, and the continuous-validation byte immediately before
    the already-proven Children array. Children are followed by variable value
    packages and fixed-size 14-byte association rows containing child id,
    flags, switch mode, fade-out time, and fade-in time. Some current type-6
    objects use a distinct tail; those fail closed with offsets while normal
    child traversal remains unchanged.
    """

    tail_start = children_offset + 4 + child_count * 4

    def unresolved(reason: str, offset: int) -> dict[str, Any]:
        bounded_offset = max(0, min(offset, len(data)))
        return {
            "parserStatus": "unresolvedV150SwitchTail",
            "failureReason": reason,
            "unresolvedTailOffset": bounded_offset,
            "unresolvedTailByteLength": len(data) - bounded_offset,
            "runtimeSelection": "groupValueUnobservedAllChildrenRemainPossible",
        }

    if bank_version != 150:
        return {
            "parserStatus": "unsupportedBankVersion",
            "bankVersion": bank_version,
            "unresolvedTailOffset": tail_start,
            "unresolvedTailByteLength": max(0, len(data) - tail_start),
            "runtimeSelection": "groupValueUnobservedAllChildrenRemainPossible",
        }
    if children_offset < 10:
        return unresolved("selectorHeaderBeforeObjectStart", children_offset)
    if tail_start + 4 > len(data):
        return unresolved("truncatedPackageCount", tail_start)

    group_type_raw = data[children_offset - 10]
    if group_type_raw not in (0, 1):
        return unresolved("invalidGroupType", children_offset - 10)
    group_id = unpack_from("<I", data, children_offset - 9)[0]
    default_value_id = unpack_from("<I", data, children_offset - 5)[0]
    continuous_raw = data[children_offset - 1]
    if continuous_raw not in (0, 1):
        return unresolved("invalidContinuousValidation", children_offset - 1)

    package_count = unpack_from("<I", data, tail_start)[0]
    if package_count == 0:
        return unresolved("noValuePackages", tail_start)
    offset = tail_start + 4
    if package_count > (len(data) - offset) // 8:
        return unresolved("invalidPackageCount", tail_start)
    packages: list[dict[str, Any]] = []
    mapped_child_ids: set[int] = set()
    for package_index in range(package_count):
        if offset + 8 > len(data):
            return unresolved("truncatedPackageHeader", offset)
        value_id, mapped_child_count = unpack_from("<II", data, offset)
        offset += 8
        if mapped_child_count > (len(data) - offset) // 4:
            return unresolved("invalidMappedChildCount", offset - 4)
        child_ids = [
            unpack_from("<I", data, offset + index * 4)[0]
            for index in range(mapped_child_count)
        ]
        offset += mapped_child_count * 4
        mapped_child_ids.update(child_ids)
        packages.append({
            "packageIndex": package_index,
            "valueId": value_id,
            "isDefaultValue": value_id == default_value_id,
            "mappedChildCount": mapped_child_count,
            "childIds": child_ids,
        })

    if offset + 4 > len(data):
        return unresolved("truncatedAssociationCount", offset)
    association_count = unpack_from("<I", data, offset)[0]
    offset += 4
    association_bytes = association_count * 14
    if association_count > (len(data) - offset) // 14:
        return unresolved("invalidAssociationCount", offset - 4)
    if offset + association_bytes != len(data):
        return unresolved("unexpectedAssociationTrailingBytes", offset + association_bytes)
    associations: list[dict[str, Any]] = []
    for association_index in range(association_count):
        child_id = unpack_from("<I", data, offset)[0]
        flags_raw = data[offset + 4]
        switch_mode_byte = data[offset + 5]
        switch_mode_raw = switch_mode_byte & 0x07
        fade_out_time = unpack_from("<i", data, offset + 6)[0]
        fade_in_time = unpack_from("<i", data, offset + 10)[0]
        associations.append({
            "associationIndex": association_index,
            "childId": child_id,
            "flagsRaw": flags_raw,
            "isFirstOnly": bool(flags_raw & 0x01),
            "continuePlayback": bool(flags_raw & 0x02),
            "flagsUnknownMask": flags_raw & 0xFC,
            "onSwitchMode": {0: "playToEnd", 1: "stop"}.get(
                switch_mode_raw, "unknown"
            ),
            "onSwitchModeRaw": switch_mode_raw,
            "onSwitchModeRawByte": switch_mode_byte,
            "onSwitchModeUnknownMask": switch_mode_byte & 0xF8,
            "fadeOutTimeMs": fade_out_time,
            "fadeInTimeMs": fade_in_time,
        })
        offset += 14

    authored_children = {
        unpack_from("<I", data, children_offset + 4 + index * 4)[0]
        for index in range(child_count)
    }
    association_child_ids = {row["childId"] for row in associations}
    return {
        "parserStatus": "typedExactV150FlatPackages",
        "selectionStructure": "flatValuePackages",
        "groupType": "switch" if group_type_raw == 0 else "state",
        "groupTypeRaw": group_type_raw,
        "groupId": group_id,
        "defaultValueId": default_value_id,
        "continuousValidation": bool(continuous_raw),
        "continuousValidationRaw": continuous_raw,
        "packageCount": package_count,
        "packages": packages,
        "associationCount": association_count,
        "associations": associations,
        "mappedChildIdsOutsideChildren": sorted(mapped_child_ids - authored_children),
        "unmappedChildIds": sorted(authored_children - mapped_child_ids),
        "associationChildIdsOutsideChildren": sorted(
            association_child_ids - authored_children
        ),
        "decisionTreeStatus": "noSeparateBytesAfterTypedFlatPackagesAndAssociations",
        "runtimeSelection": "groupValueUnobservedAllChildrenRemainPossible",
    }


def _hirc_v150_music_common_tail(
    data: bytes,
    children_offset: int,
    child_count: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the fixed v150 music meter/stinger tail after Children."""

    try:
        offset = children_offset + 4 + child_count * 4
        if offset + 27 > len(data):
            raise ValueError("truncated v150 music meter")
        grid_period = unpack_from("<d", data, offset)[0]
        grid_offset = unpack_from("<d", data, offset + 8)[0]
        tempo = unpack_from("<f", data, offset + 16)[0]
        time_signature_numerator = data[offset + 20]
        time_signature_beat = data[offset + 21]
        meter_override = bool(data[offset + 22])
        stinger_count = unpack_from("<I", data, offset + 23)[0]
        offset += 27
        stinger_bytes = stinger_count * 24
        if offset + stinger_bytes > len(data):
            raise ValueError("truncated v150 music stingers")
        stingers = [
            {
                "triggerId": unpack_from("<I", data, offset + index * 24)[0],
                "segmentId": unpack_from("<I", data, offset + index * 24 + 4)[0],
                "syncType": unpack_from("<I", data, offset + index * 24 + 8)[0],
                "cueFilterHash": unpack_from("<I", data, offset + index * 24 + 12)[0],
            }
            for index in range(stinger_count)
        ]
        offset += stinger_bytes
        return ({
            "gridPeriod": grid_period,
            "gridOffset": grid_offset,
            "tempo": tempo,
            "timeSignatureNumerator": time_signature_numerator,
            "timeSignatureBeat": time_signature_beat,
            "meterOverride": meter_override,
            "stingerCount": stinger_count,
            "stingers": stingers,
        }, offset)
    except (ValueError, OverflowError):
        return None


def _hirc_v150_music_transition_tail(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode v150 MusicTransAware rules far enough to reach selector data."""

    try:
        rule_count, offset = _hirc_v150_u32(data, offset)
        rules: list[dict[str, Any]] = []
        for _ in range(rule_count):
            source_count, offset = _hirc_v150_u32(data, offset)
            source_bytes = source_count * 4
            if offset + source_bytes > len(data):
                raise ValueError("truncated v150 music transition sources")
            source_ids = [unpack_from("<I", data, offset + index * 4)[0] for index in range(source_count)]
            offset += source_bytes
            destination_count, offset = _hirc_v150_u32(data, offset)
            destination_bytes = destination_count * 4
            if offset + destination_bytes > len(data):
                raise ValueError("truncated v150 music transition destinations")
            destination_ids = [
                unpack_from("<I", data, offset + index * 4)[0]
                for index in range(destination_count)
            ]
            offset += destination_bytes
            if offset + 48 > len(data):
                raise ValueError("truncated v150 music transition rule")
            # Source rule is 21 bytes; destination rule is 26 bytes in v150.
            offset += 47
            has_transition_segment = bool(data[offset])
            offset += 1
            transition_segment_id = None
            if has_transition_segment:
                if offset + 30 > len(data):
                    raise ValueError("truncated v150 music transition segment")
                transition_segment_id = unpack_from("<I", data, offset)[0]
                offset += 30
            rules.append({
                "sourceIds": source_ids,
                "destinationIds": destination_ids,
                "transitionSegmentId": transition_segment_id,
            })
        return ({"transitionRuleCount": rule_count, "transitionRules": rules}, offset)
    except (ValueError, OverflowError):
        return None


def hirc_v150_music_segment_structure(
    data: bytes,
    children_offset: int,
    child_count: int,
) -> dict[str, Any] | None:
    common = _hirc_v150_music_common_tail(data, children_offset, child_count)
    if not common:
        return None
    common_row, offset = common
    try:
        if offset + 12 > len(data):
            raise ValueError("truncated v150 MusicSegment")
        duration = unpack_from("<d", data, offset)[0]
        marker_count = unpack_from("<I", data, offset + 8)[0]
        offset += 12
        markers: list[dict[str, Any]] = []
        for _ in range(marker_count):
            if offset + 12 > len(data):
                raise ValueError("truncated v150 MusicSegment marker")
            marker_id = unpack_from("<I", data, offset)[0]
            position = unpack_from("<d", data, offset + 4)[0]
            offset += 12
            name_end = data.find(b"\x00", offset)
            if name_end < 0:
                raise ValueError("unterminated v150 MusicSegment marker")
            marker_name = data[offset:name_end].decode("utf-8", errors="replace")
            offset = name_end + 1
            markers.append({"id": marker_id, "position": position, "name": marker_name})
        if offset != len(data):
            raise ValueError("unexpected v150 MusicSegment trailing bytes")
        return {**common_row, "duration": duration, "markerCount": marker_count, "markers": markers}
    except (ValueError, OverflowError):
        return None


def hirc_v150_music_switch_structure(
    data: bytes,
    children_offset: int,
    child_count: int,
    child_ids: list[int] | None = None,
) -> dict[str, Any] | None:
    """Decode a v150 MusicSwitch decision tree and check its child backlinks."""
    common = _hirc_v150_music_common_tail(data, children_offset, child_count)
    if not common:
        return None
    common_row, offset = common
    transitions = _hirc_v150_music_transition_tail(data, offset)
    if not transitions:
        return None
    transition_row, offset = transitions
    try:
        if offset + 5 > len(data):
            raise ValueError("truncated v150 MusicSwitch header")
        continue_playback = bool(data[offset])
        tree_depth = unpack_from("<I", data, offset + 1)[0]
        offset += 5
        argument_bytes = tree_depth * 4
        if offset + argument_bytes + tree_depth > len(data):
            raise ValueError("truncated v150 MusicSwitch arguments")
        group_ids = [unpack_from("<I", data, offset + index * 4)[0] for index in range(tree_depth)]
        offset += argument_bytes
        group_types = list(data[offset:offset + tree_depth])
        offset += tree_depth
        tree_size, offset = _hirc_v150_u32(data, offset)
        if offset + 1 + tree_size != len(data) or tree_size % 12:
            raise ValueError("invalid v150 MusicSwitch decision tree size")
        tree_mode = data[offset]
        offset += 1
        tree_data = data[offset:offset + tree_size]
        raw_nodes = [
            {
                "key": unpack_from("<I", tree_data, index)[0],
                "value": unpack_from("<I", tree_data, index + 4)[0],
                "weight": unpack_from("<H", tree_data, index + 8)[0],
                "probability": unpack_from("<H", tree_data, index + 10)[0],
            }
            for index in range(0, tree_size, 12)
        ]
        leaves: list[dict[str, Any]] = []
        visited: set[int] = set()

        def visit(index: int, depth: int, path: tuple[int, ...]) -> None:
            if index < 0 or index >= len(raw_nodes) or index in visited:
                raise ValueError("invalid v150 MusicSwitch tree topology")
            visited.add(index)
            node = raw_nodes[index]
            current_path = (*path, int(node["key"]))
            if depth >= tree_depth:
                leaves.append({
                    "audioNodeId": int(node["value"]),
                    "pathKeys": list(current_path),
                    "weight": int(node["weight"]),
                    "probability": int(node["probability"]),
                })
                return
            child_index = int(node["value"]) & 0xFFFF
            child_count_value = (int(node["value"]) >> 16) & 0xFFFF
            if not child_count_value or child_index + child_count_value > len(raw_nodes):
                raise ValueError("invalid v150 MusicSwitch child range")
            for child in range(child_index, child_index + child_count_value):
                visit(child, depth + 1, current_path)

        if raw_nodes:
            visit(0, 0, ())
        if len(visited) != len(raw_nodes):
            raise ValueError("unreachable v150 MusicSwitch tree nodes")
        tree_leaf_ids = [int(row["audioNodeId"]) for row in leaves]
        if child_ids is None:
            selector_validation = {
                "status": "notCheckedNoReciprocalChildren",
                "treeLeafIds": sorted(set(tree_leaf_ids)),
                "reciprocalChildIds": None,
                "treeLeafIdsOutsideReciprocalChildren": [],
                "reciprocalChildrenWithoutTreeLeaf": [],
            }
        else:
            tree_leaf_id_set = set(tree_leaf_ids)
            reciprocal_child_id_set = set(int(child_id) for child_id in child_ids)
            outside = sorted(tree_leaf_id_set - reciprocal_child_id_set)
            missing = sorted(reciprocal_child_id_set - tree_leaf_id_set)
            if outside:
                status = "treeLeafOutsideReciprocalChildren"
            elif missing:
                status = "reciprocalChildNotInDecisionTree"
            else:
                status = "reciprocalChildrenCovered"
            selector_validation = {
                "status": status,
                "treeLeafIds": sorted(tree_leaf_id_set),
                "reciprocalChildIds": sorted(reciprocal_child_id_set),
                "treeLeafIdsOutsideReciprocalChildren": outside,
                "reciprocalChildrenWithoutTreeLeaf": missing,
            }
        return {
            **common_row,
            **transition_row,
            "continuePlayback": continue_playback,
            "treeDepth": tree_depth,
            "arguments": [
                {"groupId": group_id, "groupType": group_types[index]}
                for index, group_id in enumerate(group_ids)
            ],
            "treeMode": tree_mode,
            "treeNodeCount": len(raw_nodes),
            "treeLeafCount": len(leaves),
            "treeLeaves": leaves,
            "selectorValidation": selector_validation,
        }
    except (ValueError, OverflowError):
        return None


def hirc_v150_music_random_sequence_structure(
    data: bytes,
    children_offset: int,
    child_count: int,
    child_ids: list[int] | None = None,
) -> dict[str, Any] | None:
    common = _hirc_v150_music_common_tail(data, children_offset, child_count)
    if not common:
        return None
    common_row, offset = common
    transitions = _hirc_v150_music_transition_tail(data, offset)
    if not transitions:
        return None
    transition_row, offset = transitions
    try:
        playlist_count, offset = _hirc_v150_u32(data, offset)
        items: list[dict[str, Any]] = []

        def read_item(depth: int, parent_index: int | None) -> None:
            nonlocal offset
            if len(items) >= playlist_count or offset + 30 > len(data):
                raise ValueError("truncated v150 MusicRanSeq playlist")
            segment_id = unpack_from("<I", data, offset)[0]
            playlist_item_id = unpack_from("<I", data, offset + 4)[0]
            nested_count = unpack_from("<I", data, offset + 8)[0]
            selection_type = unpack_from("<I", data, offset + 12)[0]
            row = {
                "index": len(items),
                "parentIndex": parent_index,
                "depth": depth,
                "segmentId": segment_id,
                "playlistItemId": playlist_item_id,
                "childCount": nested_count,
                "selectionType": selection_type,
                "selectionTypeLabel": {
                    0: "continuousSequence",
                    1: "stepSequence",
                    2: "continuousRandom",
                    3: "stepRandom",
                    0xFFFFFFFF: "none",
                }.get(selection_type, f"type{selection_type}"),
                "loop": unpack_from("<h", data, offset + 16)[0],
                "loopMin": unpack_from("<h", data, offset + 18)[0],
                "loopMax": unpack_from("<h", data, offset + 20)[0],
                "weight": unpack_from("<I", data, offset + 22)[0],
                "avoidRepeatCount": unpack_from("<H", data, offset + 26)[0],
                "usesWeight": bool(data[offset + 28]),
                "shuffle": bool(data[offset + 29]),
            }
            offset += 30
            item_index = len(items)
            items.append(row)
            for _ in range(nested_count):
                read_item(depth + 1, item_index)

        if playlist_count:
            read_item(0, None)
        if len(items) != playlist_count or offset != len(data):
            raise ValueError("invalid v150 MusicRanSeq playlist size")
        terminal_items = [
            row for row in items if int(row.get("childCount") or 0) == 0
        ]
        terminal_segment_ids = [
            int(row["segmentId"])
            for row in terminal_items
            if int(row.get("segmentId") or 0) not in {0, 0xFFFFFFFF}
        ]
        if child_ids is None:
            selector_validation = {
                "status": "notCheckedNoReciprocalChildren",
                "playlistTerminalSegmentIds": sorted(set(terminal_segment_ids)),
                "reciprocalChildIds": None,
                "playlistTerminalSegmentIdsOutsideReciprocalChildren": [],
                "reciprocalChildrenWithoutPlaylistTerminal": [],
                "terminalPlaylistItemCount": len(terminal_items),
                "terminalItemsWithSentinelSegmentId": len(terminal_items) - len(terminal_segment_ids),
            }
        else:
            terminal_segment_id_set = set(terminal_segment_ids)
            reciprocal_child_id_set = set(int(child_id) for child_id in child_ids)
            outside = sorted(terminal_segment_id_set - reciprocal_child_id_set)
            missing = sorted(reciprocal_child_id_set - terminal_segment_id_set)
            if outside:
                status = "terminalSegmentOutsideReciprocalChildren"
            elif missing:
                status = "reciprocalChildNotInPlaylist"
            else:
                status = "reciprocalChildrenCovered"
            selector_validation = {
                "status": status,
                "playlistTerminalSegmentIds": sorted(terminal_segment_id_set),
                "reciprocalChildIds": sorted(reciprocal_child_id_set),
                "playlistTerminalSegmentIdsOutsideReciprocalChildren": outside,
                "reciprocalChildrenWithoutPlaylistTerminal": missing,
                "terminalPlaylistItemCount": len(terminal_items),
                "terminalItemsWithSentinelSegmentId": len(terminal_items) - len(terminal_segment_ids),
            }
        return {
            **common_row,
            **transition_row,
            "playlistItemCount": playlist_count,
            "playlistItems": items,
            "selectionTypeLabels": sorted({str(row["selectionTypeLabel"]) for row in items}),
            "selectorValidation": selector_validation,
        }
    except (ValueError, OverflowError, RecursionError):
        return None


def hirc_v150_music_structure(
    object_type: int,
    data: bytes,
    children_offset: int,
    child_count: int,
    child_ids: list[int] | None = None,
) -> dict[str, Any] | None:
    parser = {
        10: hirc_v150_music_segment_structure,
        12: hirc_v150_music_switch_structure,
        13: hirc_v150_music_random_sequence_structure,
    }.get(object_type)
    if not parser:
        return None
    if object_type in {12, 13}:
        return parser(data, children_offset, child_count, child_ids)
    return parser(data, children_offset, child_count)


def hirc_v150_empty_music_children(
    object_type: int,
    data: bytes,
) -> tuple[list[int], int, dict[str, Any]] | None:
    """Prove an empty music Children array through a unique typed tail parse.

    Empty lists have no child parent backlinks.  A zero count is accepted only
    when exactly one offset lets the complete type-specific meter/transition/
    selector tail consume the HIRC object to its exact end.
    """

    matches: list[tuple[list[int], int, dict[str, Any]]] = []
    for offset in range(0, max(0, len(data) - 3)):
        if unpack_from("<I", data, offset)[0] != 0:
            continue
        structure = hirc_v150_music_structure(object_type, data, offset, 0, [])
        if structure:
            matches.append(([], offset, structure))
            if len(matches) > 1:
                return None
    return matches[0] if len(matches) == 1 else None


def hirc_media_relation_types(path_object_types: list[int]) -> list[str]:
    relations: list[str] = []
    for object_type, label in (
        (5, "randomOrSequenceBranch"),
        (6, "switchOrStateBranch"),
        (9, "layerBranch"),
        (7, "actorMixerBranch"),
    ):
        if object_type in path_object_types:
            relations.append(label)
    return relations or ["directSound"]


def hirc_v150_random_sequence_properties(
    data: bytes,
    children_offset: int,
    child_ids: list[int],
    *,
    bank_version: int | None,
) -> dict[str, Any]:
    """Decode a bounded v150 Random/Sequence container policy and playlist.

    The fixed 24-byte policy block precedes the reciprocal Children array. A
    U16 playlist count and ``childId, weight`` rows follow Children. Playlist
    order is authored selection order and may differ from Children order, so
    Sequence semantics must never be reconstructed from Children alone.
    """

    tail_start = children_offset + 4 + len(child_ids) * 4
    policy: dict[str, Any] = {}

    def unresolved(reason: str, offset: int) -> dict[str, Any]:
        bounded_offset = max(0, min(offset, len(data)))
        return {
            **policy,
            "selectorParserStatus": "unresolvedV150RandomSequenceTail",
            "selectorParserFailureReason": reason,
            "selectorUnresolvedOffset": bounded_offset,
            "selectorUnresolvedByteLength": len(data) - bounded_offset,
            "runtimeSelection": "randomHistoryOrSequenceCursorUnobservedAllChildrenRemainPossible",
        }

    if bank_version != 150:
        return {
            "selectorParserStatus": "unsupportedBankVersion",
            "bankVersion": bank_version,
            "selectorUnresolvedOffset": max(0, tail_start),
            "selectorUnresolvedByteLength": max(0, len(data) - tail_start),
            "runtimeSelection": "randomHistoryOrSequenceCursorUnobservedAllChildrenRemainPossible",
        }
    if children_offset < 24:
        return unresolved("selectorHeaderBeforeObjectStart", children_offset)
    if tail_start + 2 > len(data):
        return unresolved("truncatedPlaylistCount", tail_start)

    loop_count, loop_min, loop_max = unpack_from("<HHH", data, children_offset - 24)
    transition_time, transition_min, transition_max = unpack_from(
        "<fff", data, children_offset - 18
    )
    avoid_repeat_count = unpack_from("<H", data, children_offset - 6)[0]
    transition_mode = data[children_offset - 4]
    random_mode = data[children_offset - 3]
    mode = data[children_offset - 2]
    flags = data[children_offset - 1]
    if mode not in (0, 1):
        return unresolved("invalidRandomSequenceMode", children_offset - 2)
    if random_mode not in (0, 1):
        return unresolved("invalidRandomMode", children_offset - 3)
    if transition_mode not in range(6):
        return unresolved("invalidTransitionMode", children_offset - 4)
    transition_labels = {
        0: "disabled",
        1: "crossFadeAmplitude",
        2: "crossFadePower",
        3: "delay",
        4: "sampleAccurate",
        5: "triggerRate",
    }
    policy.update({
        "mode": mode,
        "modeLabel": "random" if mode == 0 else "sequence",
        "randomMode": random_mode,
        "randomModeLabel": "standard" if random_mode == 0 else "shuffle",
        "loopCount": loop_count,
        "loopModifierMin": loop_min,
        "loopModifierMax": loop_max,
        "transitionTime": transition_time,
        "transitionModifierMin": transition_min,
        "transitionModifierMax": transition_max,
        "avoidRepeatCount": avoid_repeat_count,
        "transitionMode": transition_mode,
        "transitionModeLabel": transition_labels[transition_mode],
        "flags": flags,
        "weightFlagRaw": bool(flags & 0x01),
        "resetPlaylistAtEachPlay": bool(flags & 0x02),
        "restartBackward": bool(flags & 0x04),
        "continuous": bool(flags & 0x08),
        "globalScope": bool(flags & 0x10),
        "flagsUnknownMask": flags & 0xE0,
        "flagLabels": [
            label
            for bit, label in (
                (0, "weightFlagSet"),
                (1, "resetPlaylistAtEachPlay"),
                (2, "restartBackward"),
                (3, "continuous"),
                (4, "global"),
            )
            if flags & (1 << bit)
        ],
    })

    playlist_count = unpack_from("<H", data, tail_start)[0]
    playlist_offset = tail_start + 2
    playlist_bytes = playlist_count * 8
    if playlist_offset + playlist_bytes != len(data):
        return unresolved("unexpectedPlaylistTailLength", playlist_offset + playlist_bytes)
    if playlist_count != len(child_ids):
        return unresolved("playlistChildCountMismatch", tail_start)

    playlist_items = [
        {
            "playlistOrdinal": index,
            "childId": unpack_from("<I", data, playlist_offset + index * 8)[0],
            "weight": unpack_from("<I", data, playlist_offset + index * 8 + 4)[0],
        }
        for index in range(playlist_count)
    ]
    playlist_child_ids = [row["childId"] for row in playlist_items]
    if len(set(playlist_child_ids)) != len(playlist_child_ids):
        return unresolved("duplicatePlaylistChild", playlist_offset)
    if set(playlist_child_ids) != set(child_ids):
        return unresolved("playlistChildrenMismatch", playlist_offset)
    weights = [row["weight"] for row in playlist_items]
    return {
        **policy,
        "selectorParserStatus": "typedExactV150PlaylistWeights",
        "playlistItemCount": playlist_count,
        "playlistItems": playlist_items,
        "playlistChildOrder": playlist_child_ids,
        "childrenOrderMatchesPlaylist": playlist_child_ids == child_ids,
        "nonDefaultWeightCount": sum(weight != 50000 for weight in weights),
        "uniformWeights": len(set(weights)) <= 1,
        "weightUsageStatus": "playlistWeightsPreservedWeightFlagNotUsedAsGate",
        "runtimeSelection": "randomHistoryOrSequenceCursorUnobservedAllChildrenRemainPossible",
    }


def summarize_hirc_action_dispatch(
    event_id: int,
    root_action_ids: list[int],
    action_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Describe serialized Event dispatch without claiming runtime sequence."""

    root_rows = sorted(
        (
            row
            for row in action_evidence
            if row.get("dispatchEventId") == event_id and row.get("isRootEventAction")
        ),
        key=lambda row: int(row.get("eventActionOrdinal") or 0),
    )
    playback_rows = [
        row
        for row in root_rows
        if row.get("operation") in {"play", "playEvent"}
    ]
    playback_count = len(playback_rows)
    if not playback_count:
        timing_class = "noPlayback"
    elif playback_count == 1:
        timing_class = "singlePlayback"
    elif any(row.get("actionParserStatus") != "typedExactV150" for row in playback_rows):
        timing_class = "coDispatchActionTimingUnresolved"
    elif any(
        (row.get("delay") or {}).get("modifierRangesMs")
        for row in playback_rows
    ):
        timing_class = "dynamicDelayRangeUnresolved"
    else:
        delay_signatures = {
            tuple((row.get("delay") or {}).get("baseValuesMs") or [])
            for row in playback_rows
        }
        if delay_signatures == {()}:
            timing_class = "coDispatchNoExplicitDelay"
        elif len(delay_signatures) > 1:
            timing_class = "coDispatchWithAuthoredDelayDifference"
        else:
            timing_class = "coDispatchUniformExplicitDelay"

    def explicit_property_count(name: str) -> int:
        return sum(
            (row.get(name) or {}).get("serializationStatus")
            not in {None, "implicitDefaultNotSerialized"}
            for row in playback_rows
        )

    return {
        "serializedActionCount": len(root_action_ids),
        "serializedActionIds": root_action_ids,
        "playbackActionCount": playback_count,
        "playbackActionOrdinals": [row["eventActionOrdinal"] for row in playback_rows],
        "typedPlaybackActionCount": sum(
            row.get("actionParserStatus") == "typedExactV150" for row in playback_rows
        ),
        "failedPlaybackActionCount": sum(
            row.get("actionParserStatus") == "failedClosed" for row in playback_rows
        ),
        "multiPlayback": playback_count > 1,
        "timingClass": timing_class,
        "simultaneityCandidate": timing_class == "coDispatchNoExplicitDelay",
        "explicitDelayActionCount": explicit_property_count("delay"),
        "explicitTransitionActionCount": explicit_property_count("transition"),
        "probabilityGatedActionCount": explicit_property_count("probability"),
        "evidenceBoundary": (
            "Action ordinals prove serialized Event membership, not sequential "
            "execution or sample-accurate simultaneous audible onset."
        ),
    }


def traverse_hirc_event(
    event_id: int,
    objects: dict[int, dict[str, Any]],
    decoded_media_ids: set[int] | None = None,
    bank_version: int | None = 150,
) -> dict[str, Any]:
    """Traverse one Event using only typed, downward v150 HIRC edges."""

    decoded_media_ids = decoded_media_ids or set()
    event_object = objects.get(event_id) or {}
    root_action_ids = hirc_event_action_ids(event_object.get("data") or b"")
    queue: deque[
        tuple[int, int, tuple[int, ...], tuple[int, ...], tuple[str, ...], int | None, int | None]
    ] = deque(
        (action_id, action_id, (event_id,), (4,), (), ordinal, event_id)
        for ordinal, action_id in enumerate(root_action_ids)
    )
    visited: set[int] = {event_id}
    visited_paths: set[tuple[int, int, int | None, int | None]] = set()
    source_media_ids: list[int] = []
    resolved_media_ids: list[int] = []
    media_evidence_by_id: dict[int, dict[str, Any]] = {}
    action_evidence: list[dict[str, Any]] = []
    container_evidence: list[dict[str, Any]] = []
    music_node_evidence: list[dict[str, Any]] = []
    unresolved_nodes: list[dict[str, Any]] = []

    def record_media(
        media_id: int,
        object_id: int,
        object_type: int,
        root_action_id: int,
        relations: tuple[str, ...],
    ) -> None:
        if media_id not in source_media_ids:
            source_media_ids.append(media_id)
        if media_id in decoded_media_ids and media_id not in resolved_media_ids:
            resolved_media_ids.append(media_id)
        media_row = media_evidence_by_id.setdefault(media_id, {
            "mediaId": media_id,
            "decoded": media_id in decoded_media_ids,
            "soundObjectIds": set(),
            "musicTrackObjectIds": set(),
            "rootActionIds": set(),
            "relationTypes": set(),
            "selectionPaths": set(),
        })
        if object_type == 2:
            media_row["soundObjectIds"].add(object_id)
        elif object_type == 11:
            media_row["musicTrackObjectIds"].add(object_id)
        media_row["rootActionIds"].add(root_action_id)
        media_row["relationTypes"].update(relations)
        media_row["selectionPaths"].add(relations)

    while queue:
        (
            object_id,
            root_action_id,
            path_ids,
            path_types,
            path_relations,
            event_action_ordinal,
            dispatch_event_id,
        ) = queue.popleft()
        visit_key = (object_id, root_action_id, dispatch_event_id, event_action_ordinal)
        if visit_key in visited_paths:
            continue
        visited_paths.add(visit_key)
        visited.add(object_id)
        obj = objects.get(object_id)
        if not obj:
            unresolved_nodes.append({
                "objectId": object_id,
                "rootActionId": root_action_id,
                "reason": "missingSameBankObject",
            })
            continue
        object_type = int(obj.get("type") or 0)
        data = obj.get("data") or b""
        current_path_ids = (*path_ids, object_id)
        current_path_types = (*path_types, object_type)

        if object_type in HIRC_MUSIC_NODE_TYPES and bank_version != 150:
            unresolved_nodes.append({
                "objectId": object_id,
                "objectType": object_type,
                "rootActionId": root_action_id,
                "reason": "unsupportedMusicBankVersion",
                "bankVersion": bank_version,
            })
            continue

        if object_type == 4:
            for ordinal, action_id in enumerate(hirc_event_action_ids(data)):
                queue.append((
                    action_id,
                    root_action_id,
                    current_path_ids,
                    current_path_types,
                    path_relations,
                    ordinal,
                    object_id,
                ))
            continue

        if object_type == 3:
            action_type = hirc_action_type(data)
            operation = (action_type & 0xFF00) if action_type is not None else None
            target_id = hirc_action_target_id(data)
            target_type = int((objects.get(target_id) or {}).get("type") or 0) if target_id is not None else 0
            traversed = operation in HIRC_PLAYBACK_ACTION_OPERATIONS and target_id is not None
            action_row = {
                "actionId": object_id,
                "rootActionId": root_action_id,
                "dispatchEventId": dispatch_event_id,
                "eventActionOrdinal": event_action_ordinal,
                "isRootEventAction": len(path_ids) == 1 and dispatch_event_id == event_id,
                "actionType": action_type,
                "operation": HIRC_ACTION_OPERATION_LABELS.get(operation, f"operation0x{operation:04x}" if operation is not None else "truncated"),
                "scope": (action_type & 0x00FF) if action_type is not None else None,
                "targetId": target_id,
                "targetType": target_type or None,
                "traversed": traversed,
            }
            if operation in HIRC_PLAYBACK_ACTION_OPERATIONS:
                action_row.update(hirc_v150_playback_action(data, bank_version))
            action_evidence.append(action_row)
            if traversed:
                queue.append((
                    target_id,
                    root_action_id,
                    current_path_ids,
                    current_path_types,
                    path_relations,
                    event_action_ordinal,
                    dispatch_event_id,
                ))
            continue

        if object_type == 2:
            media_id = hirc_sound_media_id(data)
            if media_id is None:
                unresolved_nodes.append({
                    "objectId": object_id,
                    "objectType": object_type,
                    "rootActionId": root_action_id,
                    "reason": "truncatedSoundSource",
                })
                continue
            relations = tuple(path_relations) or ("directSound",)
            record_media(media_id, object_id, object_type, root_action_id, relations)
            continue

        if object_type == 11:
            track = hirc_v150_music_track(data)
            if not track:
                unresolved_nodes.append({
                    "objectId": object_id,
                    "objectType": object_type,
                    "rootActionId": root_action_id,
                    "reason": "musicTrackPrefixUnresolved",
                })
                continue
            music_node_evidence.append({
                "objectId": object_id,
                "objectType": object_type,
                "rootActionId": root_action_id,
                "nodeKind": "musicTrack",
                "parentId": track["parentId"],
                "sourceCount": track["sourceCount"],
                "sources": track["sources"],
                "playlistItemCount": track["playlistItemCount"],
                "playlistItems": track["playlistItems"],
                "subtrackCount": track["subtrackCount"],
                "automationCount": track["automationCount"],
                "automationPointCount": track["automationPointCount"],
                "parserConfidence": "typedExactV150",
            })
            relations = (*path_relations, "musicTrackSource")
            for source in track["sources"]:
                media_id = int(source.get("mediaId") or 0)
                if media_id:
                    record_media(media_id, object_id, object_type, root_action_id, relations)
            continue

        if object_type in HIRC_TYPED_CHILD_CONTAINER_TYPES:
            parsed = hirc_reciprocal_child_list(object_id, object_type, data, objects)
            structure = None
            parser_confidence = "reciprocalParentExact"
            if not parsed and object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
                empty_music = hirc_v150_empty_music_children(object_type, data)
                if empty_music:
                    child_ids, offset, structure = empty_music
                    parsed = (child_ids, offset)
                    parser_confidence = "typedTailExactEmpty"
            if not parsed:
                unresolved_nodes.append({
                    "objectId": object_id,
                    "objectType": object_type,
                    "rootActionId": root_action_id,
                    "reason": "childrenListUnresolved",
                })
                continue
            child_ids, offset = parsed
            container_row = {
                "objectId": object_id,
                "objectType": object_type,
                "rootActionId": root_action_id,
                "childrenOffset": offset,
                "childCount": len(child_ids),
                "parserConfidence": parser_confidence,
            }
            if object_type == 5:
                container_row.update(hirc_v150_random_sequence_properties(
                    data,
                    offset,
                    child_ids,
                    bank_version=bank_version,
                ))
                relation = "sequenceItem" if container_row.get("mode") == 1 else "randomAlternative"
            elif object_type == 6:
                container_row["switchMappingEvidence"] = hirc_v150_switch_mapping(
                    data,
                    offset,
                    len(child_ids),
                    bank_version=bank_version,
                )
                relation = "switchCandidate"
            elif object_type == 9:
                relation = "layerChild"
            elif object_type == 10:
                relation = "musicTrack"
                structure = structure or hirc_v150_music_structure(
                    object_type, data, offset, len(child_ids), child_ids
                )
                node_kind = "musicSegment"
            elif object_type == 12:
                relation = "musicSwitchCandidate"
                structure = structure or hirc_v150_music_structure(
                    object_type, data, offset, len(child_ids), child_ids
                )
                node_kind = "musicSwitchContainer"
            elif object_type == 13:
                relation = "musicPlaylistCandidate"
                structure = structure or hirc_v150_music_structure(
                    object_type, data, offset, len(child_ids), child_ids
                )
                node_kind = "musicRandomSequenceContainer"
            else:
                relation = "groupChild"
            container_row["edgeKind"] = relation
            container_evidence.append(container_row)
            if object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
                music_row = {
                    **container_row,
                    "nodeKind": node_kind,
                    "childIds": child_ids,
                }
                if structure:
                    music_row.update(structure)
                    selector_status = (structure.get("selectorValidation") or {}).get("status")
                    music_row["structureStatus"] = (
                        "typedExactV150"
                        if selector_status in {None, "reciprocalChildrenCovered"}
                        else "typedExactV150SelectorBoundaryUnresolved"
                    )
                    if selector_status not in {None, "reciprocalChildrenCovered"}:
                        unresolved_nodes.append({
                            "objectId": object_id,
                            "objectType": object_type,
                            "rootActionId": root_action_id,
                            "reason": "musicSelectorReciprocalMismatch",
                            "selectorValidation": structure["selectorValidation"],
                        })
                else:
                    music_row["structureStatus"] = "structureTailUnresolved"
                    unresolved_nodes.append({
                        "objectId": object_id,
                        "objectType": object_type,
                        "rootActionId": root_action_id,
                        "reason": "musicStructureTailUnresolved",
                    })
                music_node_evidence.append(music_row)
                if not structure:
                    # Reciprocal parent proof identifies a likely Children block,
                    # but music edges are traversed only when the serialized tail
                    # starting at that exact boundary also parses to object end.
                    continue
            child_relations = (*path_relations, relation)
            for child_id in child_ids:
                queue.append((
                    child_id,
                    root_action_id,
                    current_path_ids,
                    current_path_types,
                    child_relations,
                    event_action_ordinal,
                    dispatch_event_id,
                ))
            continue

        unresolved_nodes.append({
            "objectId": object_id,
            "objectType": object_type,
            "rootActionId": root_action_id,
            "reason": "unsupportedTypedNode",
        })

    media_evidence = [
        {
            "mediaId": media_id,
            "decoded": bool(row["decoded"]),
            **({
                "soundObjectCount": len(row["soundObjectIds"]),
                "soundObjectIds": sorted(row["soundObjectIds"]),
            } if row["soundObjectIds"] else {}),
            **({
                "musicTrackObjectCount": len(row["musicTrackObjectIds"]),
                "musicTrackObjectIds": sorted(row["musicTrackObjectIds"]),
            } if row["musicTrackObjectIds"] else {}),
            "rootActionIds": sorted(row["rootActionIds"]),
            "relationTypes": sorted(row["relationTypes"]),
            "selectionPaths": [list(path) for path in sorted(row["selectionPaths"])],
        }
        for media_id, row in sorted(media_evidence_by_id.items())
    ]
    action_dispatch_evidence = summarize_hirc_action_dispatch(
        event_id, root_action_ids, action_evidence
    )
    return {
        "actionIds": root_action_ids,
        "rootPlayActionCount": action_dispatch_evidence["playbackActionCount"],
        "rootStopActionCount": sum(
            row.get("isRootEventAction") and row.get("operation") == "stop"
            for row in action_evidence
        ),
        "visitedObjectIds": sorted(visited),
        "sourceMediaIds": source_media_ids,
        "mediaIds": resolved_media_ids,
        "mediaEvidence": media_evidence,
        "actionEvidence": action_evidence,
        "actionDispatchEvidence": action_dispatch_evidence,
        "containerEvidence": container_evidence,
        "musicNodeEvidence": music_node_evidence,
        "unresolvedNodes": unresolved_nodes,
        "traversalStatus": "partial" if unresolved_nodes else "complete",
    }


def summarize_hirc_object_types(
    objects: dict[int, dict[str, Any]],
    visited: set[int],
) -> tuple[dict[str, int], dict[str, str], list[int]]:
    """Return raw HIRC family counts plus labels and selection containers.

    Raw type numbers remain authoritative.  Names are presentation labels for
    the families observed in Endfield's current banks; their presence proves a
    possible runtime selector, not which branch was selected.
    """

    counts = Counter(
        int(objects[object_id].get("type") or 0)
        for object_id in visited
        if object_id in objects
    )
    return (
        {str(object_type): count for object_type, count in sorted(counts.items())},
        {
            str(object_type): HIRC_OBJECT_TYPE_LABELS.get(object_type, f"type{object_type}")
            for object_type in sorted(counts)
        },
        sorted(object_type for object_type in counts if object_type in SELECTION_HIRC_TYPES),
    )


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
        return SPLIT_AUDIO_BLOCKS
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
    output_format: str | None = None,
) -> dict[tuple[str, str], dict[str, str]]:
    payload = load_json(language_root / "index.json", {})
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
            if output_format:
                rel = audio_rel_with_extension(rel, output_format)
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


def iter_audio_files(language_root: Path) -> list[Path]:
    if not language_root.exists():
        return []
    return sorted(
        [
            path
            for path in language_root.rglob("*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        ],
        key=lambda path: (
            normalize_posix(path.relative_to(language_root)).rsplit(".", 1)[0].lower(),
            AUDIO_EXTENSION_PRIORITY.get(path.suffix.lower(), 99),
            normalize_posix(path.relative_to(language_root)).lower(),
        ),
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
    for path in iter_audio_files(source_root):
        rel = normalize_posix(path.relative_to(source_root))
        occurrence_key = normalize_posix(PurePosixPath(rel).with_suffix("")).lower()
        # Keep the preferred FLAC/WAV/WEM for one physical path stem while
        # preserving same-media-id occurrences in distinct folders or banks.
        if occurrence_key in seen_occurrences:
            continue
        seen_occurrences.add(occurrence_key)
        audio_id = path.stem.lower()
        stat = path.stat()
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
    out: dict[str, dict[str, Any]] = {}
    for audio_dialog_path in audio_dialog_paths:
        rows = load_json(audio_dialog_path, {})
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
            selected = next(
                ((rel, file_path) for _, rel, file_path in candidates if file_path.exists()),
                None,
            )
            if selected is None:
                continue
            rel, file_path = selected
            duration = row.get(duration_field)
            entry = {
                "id": audio_id,
                "rel": rel,
                "storageRoot": language,
                "src": served_audio_href(audio_root, webui_root, language, rel),
                "format": file_path.suffix.lower().lstrip("."),
                "bytes": file_path.stat().st_size,
                "audioDialogKey": int(row_key) if str(row_key).lstrip("-").isdigit() else row_key,
                "audioDialogPath": dialog_path,
                "audioDialogSource": source_path,
                "speakerChannel": str(row.get("speakerChannel") or ""),
                "voType": row.get("voType"),
                "duration": duration if isinstance(duration, (int, float)) else None,
                **audio_source_metadata("voice", language, language_info),
            }
            apply_audio_category(entry)
            out[audio_id] = entry
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
    for source_label, streaming_assets, fallback_assets in audio_vfs_sources(args):
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
        wanted_by_hash.setdefault(fnv1_32(name.lower()), name)
    for event_hash in explicit_event_hashes:
        wanted_by_hash.setdefault(
            event_hash,
            (explicit_event_names_by_hash or {}).get(event_hash) or hashed_event_key(event_hash),
        )
    numeric_audio_ids = {
        int(audio_id)
        for audio_id in audio_by_id
        if audio_id.isdigit()
    }
    if not numeric_audio_ids:
        return {}, []

    event_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_evidence: dict[tuple[str, int], dict[str, Any]] = {}
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
    for bank_name, bank_data in package_payloads:
        try:
            bank_payloads = iter_akpk_bank_payloads_from_bytes(bank_data, bank_name)
        except ValueError:
            continue
        for bank_id, bank_payload in bank_payloads:
            embedded_bank_count += 1
            bank_version: int | None = None
            for tag, body in iter_bnk_sections(bank_payload):
                if tag == b"BKHD" and len(body) >= 4:
                    bank_version = unpack_from("<I", body, 0)[0]
                    summary_bank_versions[bank_version] += 1
                    break
            objects = parse_hirc_objects(bank_payload)
            if not objects:
                continue
            hirc_object_count += len(objects)
            summary_type_counts.update(
                int(obj.get("type") or 0) for obj in objects.values()
            )
            for event_hash in sorted(set(objects).intersection(wanted_by_hash)):
                event_name = wanted_by_hash[event_hash]
                event_object = objects[event_hash]
                if not event_object or event_object.get("type") != 4:
                    continue
                traversal = traverse_hirc_event(
                    event_hash,
                    objects,
                    numeric_audio_ids,
                    bank_version=bank_version,
                )
                action_ids = traversal["actionIds"]
                visited = set(traversal["visitedObjectIds"])
                media_ids = traversal["mediaIds"]

                evidence_key = (event_name.lower(), bank_id)
                object_type_counts, object_type_labels, selection_object_types = (
                    summarize_hirc_object_types(objects, visited)
                )
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
                    "actionParser": "wwise150TypedPlaybackActionBundles",
                    "rootPlayActionCount": traversal["rootPlayActionCount"],
                    "rootStopActionCount": traversal["rootStopActionCount"],
                    "visitedObjectIds": sorted(visited),
                    "objectTypeCounts": object_type_counts,
                    "objectTypeLabels": object_type_labels,
                    "selectionObjectTypes": selection_object_types,
                    "containerEvidence": traversal["containerEvidence"],
                    "musicNodeEvidence": traversal["musicNodeEvidence"],
                    "mediaEvidence": traversal["mediaEvidence"],
                    "sourceMediaIds": traversal["sourceMediaIds"],
                    "mediaIds": media_ids,
                    "resolvedMediaCount": len(media_ids),
                    "unresolvedNodes": traversal["unresolvedNodes"],
                    "traversalStatus": traversal["traversalStatus"],
                    "edgeParser": "wwise150TypedReciprocalChildrenSwitchMappingAndMusic",
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
                            )
                            if row.get(key) not in (None, "", [])
                        })
                for media_id in media_ids:
                    audio_entry = audio_by_id.get(str(media_id))
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

    if hirc_summary is not None:
        hirc_summary.clear()
        hirc_summary.update({
            "source": "wwiseBankHircInventory",
            "packageCount": len(package_payloads),
            "embeddedBankCount": embedded_bank_count,
            "hircObjectCount": hirc_object_count,
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
        payload = load_json(conv_path, {})
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

def load_cached_event_audio_index(
    language_root: Path,
    event_names: set[str],
    audio_root: Path,
    webui_root: Path,
    language: str,
    explicit_event_hashes: set[int] | None = None,
    expected_format: str | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]] | None:
    """Reuse event-to-media links from the last audio index when complete."""
    payload = load_json(language_root / "index.json", {})
    if not isinstance(payload, dict):
        return None
    if expected_format and str(payload.get("format") or "").lower() != expected_format.lower():
        return None
    if int(payload.get("eventEvidenceSchemaVersion") or 0) < EVENT_EVIDENCE_SCHEMA_VERSION:
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
        normalize_posix(path.relative_to(source_root)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in iter_audio_files(source_root)
    }


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
        args.format,
        "--block",
        block,
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
    storages = (
        (SHARED_AUDIO_STORAGE, language)
        if block == "all"
        else (storage_root_for_block(block, language),)
    )
    for storage_root in storages:
        (args.audio_root / storage_root).mkdir(parents=True, exist_ok=True)

    output_root = args.audio_root / language if block in {"all", "voice"} else args.audio_root / SHARED_AUDIO_STORAGE
    shared_output_root = args.audio_root / SHARED_AUDIO_STORAGE if block == "all" else None
    dumper_language_info = language_info if block in {"all", "voice"} else LANGUAGES[SHARED_AUDIO_LANGUAGE]
    for source_label, streaming_assets, fallback_assets in audio_vfs_sources(args):
        before_by_storage = {
            storage_root: snapshot_audio_file_stats(args.audio_root / storage_root)
            for storage_root in storages
        }
        run_audio_dumper_once(
            args,
            dumper_language_info,
            output_root,
            block,
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
                    if block == "all"
                    else block
                )
                metadata = audio_source_metadata(metadata_block, language, language_info)
                metadata["storageRoot"] = storage_root
                source_by_rel[(storage_root, rel)] = metadata
                changed += 1
            summary_block = "voice" if storage_root == language else (
                "audio" if block == "all" else block
            )
            summary_metadata = audio_source_metadata(summary_block, language, language_info)
            print(
                f"Audio source map [{source_label}]: {changed:,} files tagged as "
                f"{summary_metadata['audioScope']} from {summary_metadata['sourceBlockLabel']} "
                f"under {storage_root}"
            )
    return source_by_rel


def remap_audio_metadata_extension(
    source_by_rel: dict[tuple[str, str], dict[str, str]],
    output_format: str,
) -> dict[tuple[str, str], dict[str, str]]:
    """Move source provenance keys from decoded WAV paths to WebUI paths."""
    if output_format == "wav":
        return source_by_rel
    out: dict[tuple[str, str], dict[str, str]] = {}
    for (storage_root, rel), metadata in source_by_rel.items():
        normalized = normalize_posix(rel)
        remapped = audio_rel_with_extension(normalized, output_format)
        out[(storage_root, remapped)] = metadata
    return out


def convert_audio_for_webui(
    args: argparse.Namespace,
    language: str,
    output_format: str,
) -> dict[str, int]:
    """Convert the selected decoded storage roots to the browser format."""
    if output_format != "flac":
        return {"scanned": 0, "converted": 0, "skipped": 0, "planned": 0, "failed": 0}

    storage_names = (
        (SHARED_AUDIO_STORAGE, language)
        if args.block == "all"
        else (storage_root_for_block(args.block, language),)
    )
    total = {"scanned": 0, "converted": 0, "skipped": 0, "planned": 0, "failed": 0}
    for storage_name in dict.fromkeys(storage_names):
        stats = convert_audio_root(
            args.audio_root / storage_name,
            ffmpeg=getattr(args, "ffmpeg", None),
            jobs=getattr(args, "audio_conversion_jobs", None) or 1,
            delete_source=True,
        )
        for key, value in stats.items():
            total[key] = total.get(key, 0) + int(value)
        if stats["scanned"]:
            print(
                f"Audio FLAC conversion [{storage_name}]: "
                f"{stats['converted']:,} converted, {stats['skipped']:,} skipped"
            )
    return total

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
    if not root.exists():
        return 0
    removed = 0
    dirs = [path for path in root.rglob("*") if path.is_dir()]
    for folder in sorted(dirs, key=lambda item: len(item.parts), reverse=True):
        try:
            folder.rmdir()
            removed += 1
        except OSError:
            continue
    return removed


def canonicalize_audio_layout(audio_root: Path, storage: str) -> dict[str, int]:
    """Move legacy decoded audio files into the browser-facing folder layout."""
    storage_root = audio_root / storage
    if not storage_root.exists():
        return {}
    counts: dict[str, int] = defaultdict(int)
    for path in iter_audio_files(storage_root):
        rel = normalize_posix(path.relative_to(storage_root))
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


def build_audio(args: argparse.Namespace) -> int:
    args.export_root = args.export_root.resolve()
    args.webui_root = args.webui_root.resolve()
    args.audio_root = args.audio_root.resolve()
    language = args.language.upper()
    language_info = LANGUAGES[language]
    output_format = audio_output_format(args)
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
    prior_source_by_rel = prior_source_metadata_by_rel(language_root, language, output_format)
    decoded_source_by_rel = run_audio_dumper(args, language, language_info)
    convert_audio_for_webui(args, language, output_format)
    if output_format == "flac":
        decoded_source_by_rel = remap_audio_metadata_extension(
            decoded_source_by_rel,
            output_format,
        )

    for regroup_storage in (SHARED_AUDIO_STORAGE, language):
        bank_counts, bank_metadata = regroup_unmapped_by_bank(args.audio_root, regroup_storage, args.export_root)
        merge_source_metadata_by_rel(decoded_source_by_rel, bank_metadata)
        if bank_counts:
            summary = ", ".join(f"{bank}:{count:,}" for bank, count in sorted(bank_counts.items()))
            print(f"Audio source-bank tagging [{regroup_storage}]: {summary}")

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

    audio_dialog_paths = find_audio_dialog_tables(args.export_root)
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
    generic_audio = merge_audio_file_indexes(shared_audio, language_audio)
    dialog_audio = build_dialog_audio_index(
        audio_dialog_paths,
        args.audio_root,
        args.webui_root,
        language_root,
        language,
        language_info,
        "." + output_format.lower(),
    )
    audio_by_id = {**generic_audio, **dialog_audio}

    conv_dir = args.webui_root / "data" / "lang" / language / "conv"
    if not conv_dir.exists():
        raise SystemExit(f"Conversation directory not found: {conv_dir}")
    event_names = collect_audio_event_names(conv_dir, args.export_root)
    event_names.update(collect_table_audio_event_names(args.export_root))
    metadata_path = args.game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    if not metadata_path.is_file():
        cached_metadata_path = args.export_root / "recovered" / "il2cpp" / "global-metadata.dat"
        metadata_path = cached_metadata_path if cached_metadata_path.is_file() else None
    binary_managed_event_names = {
        name for name in collect_metadata_audio_literals(metadata_path)
        if not is_rtpc_parameter_name(name)
    }
    event_names.update(binary_managed_event_names)
    fmv_attach_overrides = load_narrative_video_attach_overrides(args.webui_root)
    audio_source_overrides = load_narrative_video_audio_source_overrides(args.webui_root)
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
    apply_cutscene_audio_source_overrides(
        cutscene_audio_events,
        conv_dir,
        audio_source_overrides,
    )
    for events in cutscene_audio_events.values():
        event_names.update(str(event or "").strip() for event in events if str(event or "").strip())
    gameplay_audio_references = collect_gameplay_audio_references(
        args.webui_root,
        args.export_root,
        language,
    )
    event_names.update(gameplay_audio_references.get("eventNames") or set())
    projectile_event_hashes = projectile_sound_hashes(args.webui_root)
    table_event_hashes = collect_table_audio_event_hashes(args.export_root)
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
            expected_format=output_format,
        )
        if args.skip_decode
        else None
    )
    hirc_summary: dict[str, Any] = {}
    if cached_event_index is not None:
        event_audio_by_id, event_evidence = cached_event_index
        prior_index = load_json(language_root / "index.json", {})
        if isinstance(prior_index, dict) and isinstance(prior_index.get("hircSummary"), dict):
            hirc_summary = dict(prior_index["hircSummary"])
        print("Audio events: reused existing event-media index")
    else:
        event_audio_by_id, event_evidence = collect_event_audio_index(
            event_names,
            audio_by_id,
            args,
            explicit_event_hashes,
            explicit_event_names_by_hash,
            hirc_summary,
        )
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
    category_moved = regroup_unmapped_by_category(
        args.audio_root, args.webui_root, audio_by_id, event_entries, language
    )
    if category_moved:
        print(f"Audio layout [{language}]: {category_moved:,} Wwise files filed under event-category folders")
    source_summary = summarize_audio_sources(list(generic_audio.values()))
    link_stats = link_conversation_audio(conv_dir, audio_by_id, event_audio_by_id, cutscene_audio_events)
    projectile_link_stats = link_projectile_audio(args.webui_root, event_audio_by_id, event_evidence)
    gameplay_link_stats = link_gameplay_audio(
        args.webui_root,
        language,
        gameplay_audio_references,
        event_audio_by_id,
        event_evidence,
        dialog_audio,
    )

    index_payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": language,
        "dumperLanguage": language_info["dumper"],
        "format": output_format,
        "eventEvidenceSchemaVersion": EVENT_EVIDENCE_SCHEMA_VERSION,
        "sourceFormat": args.format,
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
            **projectile_link_stats,
            **gameplay_link_stats,
            **link_stats,
        },
        "eventNames": sorted(event_names),
        "projectileEventHashes": sorted(projectile_event_hashes),
        "tableEventHashes": sorted(table_event_hashes),
        "explicitEventHashes": sorted(explicit_event_hashes),
        "binaryManagedEventNames": sorted(binary_managed_event_names),
        "hircSummary": hirc_summary,
        "eventEvidence": event_evidence,
        "events": sorted(event_entries, key=lambda item: (str(item.get("eventId") or ""), int(item.get("mediaId") or 0))),
        "entries": sorted(audio_by_id.values(), key=lambda item: (str(item.get("id") or ""), str(item.get("rel") or ""))),
    }
    json_dump(language_root / "index.json", index_payload)
    semantic_payload = build_audio_semantic_data(
        index_payload,
        language=language,
        export_root=args.export_root,
        webui_root=args.webui_root,
        metadata_path=metadata_path,
        cutscene_events=cutscene_audio_events,
    )

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
        "--format",
        choices=("wav", "wem"),
        default="wav",
        help="AnimeStudio decode format before WebUI conversion (default: wav).",
    )
    parser.add_argument(
        "--audio-format",
        choices=("flac", "wav", "wem"),
        default=None,
        help=(
            "Browser-facing output format. WAV decodes default to lossless FLAC; "
            "explicit --format wem keeps legacy WEM output."
        ),
    )
    parser.add_argument(
        "--block",
        choices=("all", "voice", "audio", "initial-audio", "audit-audio", "hotfix-audio"),
        default="all",
    )
    parser.add_argument("--skip-decode", action="store_true", help="Only rebuild the audio index and story links.")
    parser.add_argument(
        "--audio-dumper",
        type=Path,
        default=DEFAULT_AUDIO_DUMPER,
        help="Path to AnimeStudio CLI for audio extraction.",
    )
    parser.add_argument("--fluffy", dest="audio_dumper", help=argparse.SUPPRESS)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--streaming-assets", type=Path, default=None)
    parser.add_argument("--fallback-assets", type=Path, default=None)
    parser.add_argument("--ffmpeg", type=Path, default=None, help="Path to ffmpeg for WAV-to-FLAC conversion.")
    parser.add_argument(
        "--audio-conversion-jobs",
        type=int,
        default=1,
        help="Concurrent ffmpeg FLAC encoders (default: 1).",
    )
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
    return args


if __name__ == "__main__":
    raise SystemExit(build_audio(parse_args()))
