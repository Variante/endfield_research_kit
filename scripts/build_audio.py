#!/usr/bin/env python3
"""Decode story audio into export_full and link playable files into WebUI data."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import time
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath
from struct import unpack_from
from typing import Any

try:
    from convert_audio_to_flac import convert_audio_root
except ImportError:  # Imported as scripts.build_audio from repository-root tests.
    from scripts.convert_audio_to_flac import convert_audio_root


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
GAMEPLAY_AUDIO_EVENT_BYTES_RE = re.compile(rb"\b(?:au|bark|radio)_[A-Za-z0-9_]{2,160}\b")
GAMEPLAY_BUFF_BYTES_RE = re.compile(rb"\bbuff_[A-Za-z0-9_]{2,160}\b")
GAMEPLAY_AUDIO_LINK_FIELDS = (
    "src", "mediaId", "format", "bytes", "audioScope", "audioCategory",
    "audioCategoryDetail", "sourceBlock", "sourceBlockLabel", "sourceBank",
    "bankId", "bank",
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
    owners: list[dict[str, Any]] = []
    event_names: set[str] = set()
    owned_skill_ids: set[str] = set()

    for skill_id, record in sorted(skill_records.items()):
        owner_kind = ""
        owner_id = ""
        group_id = ""
        confidence = ""
        if skill_id in character_skills:
            owner_kind = "character"
            owner_id, group_id = character_skills[skill_id]
            confidence = "direct"
        else:
            character_match = next(
                (candidate for candidate in character_skill_ids if skill_id.startswith(candidate + "_")),
                None,
            )
            if character_match:
                owner_kind = "character"
                owner_id, group_id = character_skills[character_match]
                confidence = "inferred"
            enemy_match = next(
                ((candidate, enemy_id) for candidate, enemy_id in enemy_ids if skill_id == candidate or skill_id.startswith(candidate + "_")),
                None,
            )
            if not owner_kind and enemy_match:
                owner_kind = "enemy"
                owner_id = enemy_match[1]
                confidence = "inferred"
        if not owner_kind or not owner_id:
            continue

        event_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event_id in sorted(record.get("events") or set()):
            event_evidence[event_id].append({"kind": "skillData", "skillId": skill_id})
        for event_id, buff_ids in gameplay_buff_audio(set(record.get("buffs") or set()), buff_records).items():
            event_evidence[event_id].append({
                "kind": "skillBuffData",
                "skillId": skill_id,
                "buffIds": sorted(buff_ids),
            })
        if not event_evidence:
            continue
        owned_skill_ids.add(skill_id)
        event_names.update(event_evidence)
        owners.append({
            "ownerKind": owner_kind,
            "ownerId": owner_id,
            "groupId": group_id,
            "skillId": skill_id,
            "confidence": confidence,
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
            "sources": [],
            "events": {
                event_id: [{"kind": "enemyBornBuffData", "buffIds": sorted(buff_ids)}]
                for event_id, buff_ids in sorted(buff_events.items())
            },
        })

    return {
        "eventNames": event_names,
        "owners": owners,
        "counts": {
            "gameplayCharacterSkills": len(character_skills),
            "audioOwnedSkills": len(owned_skill_ids),
            "audioReferences": sum(len(owner.get("events") or {}) for owner in owners),
            "audioEventNames": len(event_names),
        },
    }


def compact_gameplay_audio_link(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: entry[key]
        for key in GAMEPLAY_AUDIO_LINK_FIELDS
        if entry.get(key) is not None
    }


def link_gameplay_audio(
    webui_root: Path,
    language: str,
    references: dict[str, Any],
    event_audio_by_id: dict[str, list[dict[str, Any]]],
    event_evidence: list[dict[str, Any]],
) -> dict[str, int]:
    """Write compact character-skill/enemy SFX sidecar with playable candidates."""

    found_events = {
        str(row.get("eventId") or "").strip().lower()
        for row in event_evidence
        if isinstance(row, dict) and str(row.get("eventId") or "").strip()
    }
    event_cache: dict[str, dict[str, Any] | None] = {}

    def linked_event(event_id: str) -> dict[str, Any] | None:
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
        if not media:
            event_cache[event_key] = None
            return None
        value = {
            "id": event_id,
            "foundInWwise": event_key in found_events,
            "playableCandidates": len(media),
            "runtimeSelection": "unresolved" if len(media) > 1 else "singleCandidate",
            "audio": media,
        }
        event_cache[event_key] = value
        return value

    characters: dict[str, dict[str, Any]] = {}
    enemies: dict[str, dict[str, Any]] = {}
    discovered_refs = 0
    linked_refs = 0
    candidate_count = 0
    for owner in references.get("owners") or []:
        event_rows: list[dict[str, Any]] = []
        for event_id, evidence in sorted((owner.get("events") or {}).items()):
            discovered_refs += 1
            linked = linked_event(event_id)
            if not linked:
                continue
            linked_refs += 1
            candidate_count += int(linked.get("playableCandidates") or 0)
            event_rows.append({**linked, "evidence": evidence})
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
            existing = {str(row.get("id") or ""): row for row in group["events"]}
            for event in event_rows:
                event_id = str(event.get("id") or "")
                if event_id not in existing:
                    event["sourceSkillIds"] = [skill_id] if skill_id else []
                    group["events"].append(event)
                    existing[event_id] = event
                elif skill_id and skill_id not in existing[event_id].setdefault("sourceSkillIds", []):
                    existing[event_id]["sourceSkillIds"].append(skill_id)
        elif owner_kind == "enemy":
            skill_id = str(owner.get("skillId") or "")
            record = enemies.setdefault(owner_id, {
                "skillIds": [],
                "ownershipConfidence": [],
                "includesSpawnBuffAudio": False,
                "events": [],
            })
            if skill_id and skill_id not in record["skillIds"]:
                record["skillIds"].append(skill_id)
            if not skill_id:
                record["includesSpawnBuffAudio"] = True
            record["ownershipConfidence"].append(owner.get("confidence") or "inferred")
            existing = {str(row.get("id") or ""): row for row in record["events"]}
            for event in event_rows:
                event_id = str(event.get("id") or "")
                if event_id not in existing:
                    record["events"].append(event)
                    existing[event_id] = event
                else:
                    existing[event_id].setdefault("evidence", []).extend(event.get("evidence") or [])

    for value in characters.values():
        for group in value.get("groups", {}).values():
            group["skillIds"].sort()
            group["ownershipConfidence"] = "inferred" if "inferred" in group.pop("ownershipConfidence", []) else "direct"
            group["events"].sort(key=lambda row: str(row.get("id") or ""))
    for value in enemies.values():
        value["skillIds"].sort()
        value["events"].sort(key=lambda row: str(row.get("id") or ""))
        value["ownershipConfidence"] = "inferred" if "inferred" in value.pop("ownershipConfidence", []) else "direct"

    stats = {
        **(references.get("counts") or {}),
        "gameplayAudioRefs": discovered_refs,
        "gameplayAudioRefsLinked": linked_refs,
        "gameplayAudioCandidates": candidate_count,
        "charactersWithPlayableSfx": len(characters),
        "enemiesWithPlayableSfx": len(enemies),
    }
    path = webui_root / Path(str(GAMEPLAY_SFX_REL).format(language=language))
    json_dump(path, {
        "schemaVersion": 1,
        "language": language,
        "counts": stats,
        "characters": characters,
        "enemies": enemies,
        "scope": {
            "source": "Exact length-prefixed SkillData/BuffData event references plus Wwise HIRC event traversal",
            "characterOwnership": "direct gameplay skill id",
            "characterFamilyOwnership": "longest playable skill id prefix inferred for authored child SkillData",
            "enemyOwnership": "enemy id prefix inferred unless attached through an exact born-buff field",
            "runtimeSelection": "Switch/random container selection remains unresolved when an event has multiple candidates.",
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
    """Attach exact HIRC event-to-media candidates to projectile sound fields."""

    path = webui_root / PROJECTILE_DATA_REL
    payload = load_json(path, {})
    entries = payload.get("entries") or []
    if not isinstance(payload, dict) or not isinstance(entries, list):
        return {"projectileSoundRefs": 0, "projectileSoundEvents": 0, "projectileSoundRefsLinked": 0, "projectileAudioCandidates": 0}

    evidence_by_hash: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in event_evidence:
        if not isinstance(row, dict):
            continue
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        if str(row.get("eventId") or "").startswith(PROJECTILE_EVENT_PREFIX):
            evidence_by_hash[event_hash].append(row)

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
            for audio in event_audio_by_id.get(key, []):
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
        "note": "Playable files are event media candidates; runtime switch/container selection is not recovered.",
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


def u32_values(data: bytes) -> list[int]:
    values: list[int] = []
    for pos in range(0, max(0, len(data) - 3)):
        values.append(unpack_from("<I", data, pos)[0])
    return values


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
    for path in iter_audio_files(source_root):
        rel = normalize_posix(path.relative_to(source_root))
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
        by_id.setdefault(audio_id, entry)
    return by_id

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
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    explicit_event_hashes = {
        int(value) & 0xFFFFFFFF
        for value in (explicit_event_hashes or set())
        if int(value) & 0xFFFFFFFF
    }
    if not event_names and not explicit_event_hashes:
        return {}, []

    wanted_by_hash: dict[int, str] = {
        fnv1_32(name.lower()): name
        for name in event_names
    }
    for event_hash in explicit_event_hashes:
        wanted_by_hash.setdefault(event_hash, projectile_event_key(event_hash))
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

    for bank_name, bank_data in event_bank_payloads(args):
        try:
            bank_payloads = iter_akpk_bank_payloads_from_bytes(bank_data, bank_name)
        except ValueError:
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
                    "bank": bank_name,
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
                        "eventHash": event_hash,
                        "mediaId": media_id,
                        "bankId": bank_id,
                        "bank": bank_name,
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
        for value in (payload.get("projectileEventHashes") or [])
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
    generic_audio = {**shared_audio, **language_audio}
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
    cached_event_index = (
        load_cached_event_audio_index(
            language_root,
            event_names,
            args.audio_root,
            args.webui_root,
            language,
            projectile_event_hashes,
            expected_format=output_format,
        )
        if args.skip_decode
        else None
    )
    if cached_event_index is not None:
        event_audio_by_id, event_evidence = cached_event_index
        print("Audio events: reused existing event-media index")
    else:
        event_audio_by_id, event_evidence = collect_event_audio_index(
            event_names,
            audio_by_id,
            args,
            projectile_event_hashes,
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
    )

    index_payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "language": language,
        "dumperLanguage": language_info["dumper"],
        "format": output_format,
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
        "eventEvidence": event_evidence,
        "events": sorted(event_entries, key=lambda item: (str(item.get("eventId") or ""), int(item.get("mediaId") or 0))),
        "entries": sorted(audio_by_id.values(), key=lambda item: (str(item.get("id") or ""), str(item.get("rel") or ""))),
    }
    json_dump(language_root / "index.json", index_payload)

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
        f" {gameplay_link_stats['gameplayAudioRefsLinked']:,}/{gameplay_link_stats['gameplayAudioRefs']:,} gameplay skill/enemy sound refs linked,"
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
