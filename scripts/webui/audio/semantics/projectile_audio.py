"""The projectile audio sidecar.

Publishes playable Wwise candidates for projectile sound fields. Authored event
hashes stay immutable in the Gameplay data; this sidecar only adds media links."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
from scripts.webui.audio.semantics.context_utils import json_dump
from scripts.webui.audio.semantics.context_utils import load_json_strict

PROJECTILE_DATA_REL = Path("data/gameplay/projectiles.json")

PROJECTILE_AUDIO_REL = Path("data/lang/{language}/gameplay/projectile_audio.json")

PROJECTILE_EVENT_PREFIX = "projectile-event:"

PROJECTILE_SOUND_FIELDS = (
    "launchSound",
    "loopSound",
    "reachSound",
    "hitSound",
    "blockSound",
    "finishedSound",
    "sizzleSound",
)

PROJECTILE_AUDIO_LINK_FIELDS = (
    "src", "mediaId", "format", "bytes", "audioScope", "audioCategory",
    "audioCategoryDetail", "sourceBlock", "sourceBlockLabel", "sourceBank",
    "bankId", "bank",
)

def projectile_event_key(event_hash: int) -> str:
    return f"{PROJECTILE_EVENT_PREFIX}0x{event_hash & 0xFFFFFFFF:08x}"

def projectile_sound_references(webui_root: Path) -> list[dict[str, Any]]:
    payload = load_json_strict(webui_root / PROJECTILE_DATA_REL, {})
    references: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        projectile_id = str(entry.get("id") or "").strip()
        if not projectile_id:
            continue
        sounds = entry.get("sounds") or {}
        for field in PROJECTILE_SOUND_FIELDS:
            value = sounds.get(field)
            raw = value.get("value") if isinstance(value, dict) else value
            if isinstance(raw, int) and raw:
                event_hash = raw & 0xFFFFFFFF
                key = (projectile_id, field, event_hash)
                if key in seen:
                    continue
                seen.add(key)
                references.append({
                    "projectileId": projectile_id,
                    "field": field,
                    "eventHash": event_hash,
                })
    references.sort(key=lambda row: (
        str(row["projectileId"]).casefold(),
        str(row["field"]),
        int(row["eventHash"]),
    ))
    return references

def projectile_sound_hashes(webui_root: Path) -> set[int]:
    return {
        int(row["eventHash"])
        for row in projectile_sound_references(webui_root)
    }

def write_projectile_audio_sidecar(
    webui_root: Path,
    language: str,
    event_audio_by_id: dict[str, list[dict[str, Any]]],
    event_evidence: list[dict[str, Any]],
) -> dict[str, int]:
    """Publish projectile media links without mutating projectile behavior."""

    references = projectile_sound_references(webui_root)

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
    links: list[dict[str, Any]] = []
    for reference in references:
        refs += 1
        event_hash = int(reference["eventHash"])
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
                    field: audio[field]
                    for field in PROJECTILE_AUDIO_LINK_FIELDS
                    if audio.get(field) is not None
                })
        event_found = bool(evidence)
        if event_found:
            resolved_hashes.add(event_hash)
        if media:
            linked_refs += 1
            candidates += len(media)
        link = {
            **reference,
            "event": {
                "hash": event_hash,
                "hex": f"0x{event_hash:08x}",
                "foundInWwise": event_found,
                "playableCandidates": len(media),
                "source": "wwiseHirc" if event_found else "unresolved",
                "runtimeSelection": "unresolved" if len(media) > 1 else "singleCandidate" if media else "none",
                "canonicalEventIds": canonical_event_ids,
            },
        }
        if media:
            link["audio"] = media
        links.append(link)

    stats = {
        "projectileSoundRefs": refs,
        "projectileSoundEvents": len(resolved_hashes),
        "projectileSoundRefsLinked": linked_refs,
        "projectileAudioCandidates": candidates,
    }
    payload = {
        "schemaVersion": 1,
        "language": language,
        "source": "Wwise HIRC event traversal",
        "note": "Playable files are typed possible media leaves; Play roots and runtime switch/container selection remain unresolved.",
        "counts": stats,
        "links": links,
    }
    path = webui_root / Path(
        str(PROJECTILE_AUDIO_REL).format(language=language)
    )
    json_dump(path, payload)
    return stats
