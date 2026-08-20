"""Static identity joins for Wwise External Source playback."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from . import identifiers


EXTERNAL_SOURCE_KIND = "externalSourceCodec"


def _structured_table_payloads(
    export_root: Path | None,
    table_name: str,
    cache: dict[str, list[tuple[str, Any]] | None],
) -> list[tuple[str, Any]] | None:
    """Load one structured table once for all External Source joins.

    The override and channel joins both consume ``AudioDialog``. Keeping the
    layer/payload list in a per-build cache avoids a second disk scan while
    retaining the source layer on every candidate row.
    """

    if export_root is None:
        return None
    if table_name in cache:
        return cache[table_name]
    payloads: list[tuple[str, Any]] = []
    found_table = False
    for layer in ("StreamingAssets", "Persistent"):
        table_path = export_root / "structured" / layer / "Table" / table_name
        if not table_path.is_file():
            continue
        found_table = True
        try:
            payload = json.loads(table_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            # A partial layer is not safe evidence for an identity join. The
            # caller will publish the source as unavailable rather than
            # treating the other layer as a complete table.
            cache[table_name] = None
            return None
        if not isinstance(payload, dict):
            cache[table_name] = None
            return None
        payloads.append((layer, payload))
    value = payloads if found_table else None
    cache[table_name] = value
    return value


def _audio_dialog_override_paths(
    export_root: Path | None,
    external_hashes: set[int],
    *,
    table_cache: dict[str, list[tuple[str, Any]] | None] | None = None,
) -> dict[int, dict[str, Any]] | None:
    """Collect typed AudioDialog override-event -> authored path candidates.

    An ``overrideWwiseEvent`` is a voice route/template, while the same row's
    ``path`` is the localized ``VoiceData.data`` candidate consumed by the
    managed external-source helper.  Keep this as a candidate join: a route
    Event may be shared by many rows and does not prove which row ran.
    """

    if export_root is None:
        return None
    result: dict[int, dict[str, Any]] = {}
    payloads = _structured_table_payloads(
        export_root,
        "AudioDialog.json",
        table_cache if table_cache is not None else {},
    )
    if payloads is None:
        return None
    for layer, payload in payloads:
        if not isinstance(payload, dict):
            continue
        for raw_row_id, raw_row in payload.items():
            if not isinstance(raw_row, dict):
                continue
            event_name = str(raw_row.get("overrideWwiseEvent") or "").strip()
            authored_path = str(raw_row.get("path") or "").strip()
            if not event_name or not authored_path:
                continue
            event_hash = identifiers.audio_hash_generator_compute(event_name)
            if event_hash not in external_hashes:
                continue
            row = result.setdefault(event_hash, {
                "overrideWwiseEvent": event_name,
                "rowCount": 0,
                "rows": set(),
                "paths": set(),
                "layers": set(),
            })
            # Conflicting names for one hash are not promoted to a named
            # mapping; retain the path evidence but make the name explicit.
            if str(row.get("overrideWwiseEvent") or "").casefold() != event_name.casefold():
                row["overrideWwiseEvent"] = ""
            row["rowCount"] += 1
            row["rows"].add(f"{layer}:{raw_row_id}")
            row["paths"].add(authored_path)
            row["layers"].add(layer)
    return result


def _audio_dialog_channel_paths(
    export_root: Path | None,
    external_hashes: set[int],
    *,
    table_cache: dict[str, list[tuple[str, Any]] | None] | None = None,
) -> dict[int, dict[str, Any]] | None:
    """Collect speaker-channel Event -> AudioDialog path candidates.

    ``AudioDialogChannel`` supplies the typed narrating/radio Event for a
    speaker channel. Joining that channel to AudioDialog rows recovers a broad
    candidate set for route Events that have no per-row override. It remains
    weaker than the same-row override join because live narration/radio choice
    is not evaluated here.
    """

    if export_root is None:
        return None
    channel_events: dict[int, dict[str, Any]] = {}
    channel_payloads = _structured_table_payloads(
        export_root,
        "AudioDialogChannel.json",
        table_cache if table_cache is not None else {},
    )
    if channel_payloads is None:
        return None
    for _layer, payload in channel_payloads:
        if not isinstance(payload, dict):
            continue
        for channel_name, raw_row in payload.items():
            if not isinstance(raw_row, dict):
                continue
            for field in ("narratingWwiseEvent", "radioWwiseEvent"):
                event_name = str(raw_row.get(field) or "").strip()
                if not event_name:
                    continue
                event_hash = identifiers.audio_hash_generator_compute(event_name)
                if event_hash not in external_hashes:
                    continue
                row = channel_events.setdefault(event_hash, {
                    "eventName": event_name,
                    "channels": set(),
                    "fields": set(),
                })
                if str(row.get("eventName") or "").casefold() != event_name.casefold():
                    row["eventName"] = ""
                row["channels"].add(str(channel_name))
                row["fields"].add(field)
    paths_by_channel: dict[str, set[str]] = {}
    rows_by_channel: Counter[str] = Counter()
    dialog_payloads = _structured_table_payloads(
        export_root,
        "AudioDialog.json",
        table_cache if table_cache is not None else {},
    )
    if dialog_payloads is None:
        return None
    for _layer, payload in dialog_payloads:
        if not isinstance(payload, dict):
            continue
        for raw_row in payload.values():
            if not isinstance(raw_row, dict):
                continue
            channel_name = str(raw_row.get("speakerChannel") or "").strip()
            authored_path = str(raw_row.get("path") or "").strip()
            if not channel_name or not authored_path:
                continue
            paths_by_channel.setdefault(channel_name, set()).add(authored_path)
            rows_by_channel[channel_name] += 1

    for row in channel_events.values():
        channels = set(row.get("channels") or ())
        row["paths"] = set().union(*(paths_by_channel.get(channel, set()) for channel in channels))
        row["rowCount"] = sum(rows_by_channel.get(channel, 0) for channel in channels)
    return channel_events


def _decoded_audio_dialog_entries(
    audio_index: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    entries_by_path: dict[str, list[dict[str, Any]]] = {}
    for row in audio_index.get("entries") or []:
        if not isinstance(row, dict):
            continue
        value = str(row.get("audioDialogPath") or "").strip()
        if value:
            key = value.replace("\\", "/").casefold()
            entries_by_path.setdefault(key, []).append(row)
    return entries_by_path


def _event_hashes(rows: Any) -> set[int]:
    return {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in rows or []
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }


def collect_event_identity_audit(
    audio_index: dict[str, Any],
    *,
    language: str,
    export_root: Path | None = None,
) -> dict[str, Any]:
    """Compare External Source Event ids with authored voice identities.

    ``voiceTableWwiseEventAliases`` contains authored routing/template Event
    names recovered from typed voice fields.  ``audioDialogWwiseEventAliases``
    is deliberately narrower: it only admits the three-way equality where an
    AudioDialog path hash is also a current Wwise Event id.  Keeping these sets
    separate makes a useful negative join explicit: an External Source Event
    can select a voice route without being the per-file AudioDialog identity.
    """

    inventory = audio_index.get("wwiseEventInventory")
    if not isinstance(inventory, list):
        return {
            "schemaVersion": 5,
            "language": str(language or "").upper(),
            "status": "degraded",
            "reason": "The Wwise Event inventory was unavailable.",
            "externalSourceEventCount": 0,
            "externalSourceReferenceCount": 0,
            "externalSourceIds": [],
            "voiceTableAliasCount": 0,
            "audioDialogAliasCount": 0,
            "externalEventsWithVoiceTableAlias": 0,
            "externalEventsWithAudioDialogAlias": 0,
            "externalEventsWithoutVoiceTableAlias": 0,
            "externalEventsWithDecodedMedia": 0,
            "externalEventsWithMediaRelations": 0,
            "externalEventsWithZeroResolvedMedia": 0,
            "externalOverridePathAuditStatus": "unavailable",
            "externalEventsWithOverridePathCandidates": 0,
            "externalEventsWithUniqueOverridePath": 0,
            "externalOverridePathRowCount": 0,
            "externalOverridePathCandidateCount": 0,
            "externalOverridePathCandidatesWithDecodedMedia": 0,
            "externalOverridePathCandidatesWithoutDecodedMedia": 0,
            "externalOverridePathMappings": [],
            "externalChannelPathAuditStatus": "unavailable",
            "externalEventsWithChannelPathCandidates": 0,
            "externalChannelPathRowCount": 0,
            "externalChannelPathCandidateCount": 0,
            "externalChannelPathUniqueCandidateCount": 0,
            "externalChannelPathCandidatesWithDecodedMedia": 0,
            "externalChannelPathUniqueCandidatesWithDecodedMedia": 0,
            "externalChannelPathMappings": [],
            "evidenceBoundary": (
                "No current Wwise Event inventory was available, so no External "
                "Source-to-voice identity join was emitted."
            ),
        }

    external_events: list[dict[str, Any]] = []
    external_media_by_hash: dict[int, bool] = {}
    external_relation_by_hash: dict[int, bool] = {}
    event_id_by_hash: dict[int, str] = {}
    event_row_by_hash: dict[int, dict[str, Any]] = {}
    source_ids: Counter[int] = Counter()
    external_reference_count = 0
    for event in inventory:
        if not isinstance(event, dict):
            continue
        external_rows = [
            row
            for row in event.get("nonMediaSourceEvidence") or []
            if isinstance(row, dict) and row.get("sourceKind") == EXTERNAL_SOURCE_KIND
        ]
        if not external_rows:
            continue
        external_reference_count += len(external_rows)
        for row in external_rows:
            source_id = row.get("sourceId")
            if isinstance(source_id, int):
                source_ids[int(source_id) & 0xFFFFFFFF] += 1
        event_hash = event.get("eventHash")
        if not isinstance(event_hash, int):
            continue
        normalized_event_hash = int(event_hash) & 0xFFFFFFFF
        event_id = str(event.get("eventId") or "")
        if normalized_event_hash not in event_id_by_hash:
            event_id_by_hash[normalized_event_hash] = event_id
            row = {
                "eventHash": normalized_event_hash,
                "eventId": event_id,
            }
            external_events.append(row)
            event_row_by_hash[normalized_event_hash] = row
        elif event_id and not event_id_by_hash[normalized_event_hash]:
            event_id_by_hash[normalized_event_hash] = event_id
            event_row_by_hash[normalized_event_hash]["eventId"] = event_id
        elif event_id and event_id_by_hash[normalized_event_hash] != event_id:
            # Wwise bank occurrences can repeat one Event hash. Conflicting
            # labels are not safe to publish as a named identity.
            event_id_by_hash[normalized_event_hash] = ""
            event_row_by_hash[normalized_event_hash]["eventId"] = ""
        # ``mediaIds`` belongs to the whole Event graph and may describe an
        # ordinary codec source alongside an External Source record. Do not
        # promote that mixed graph to External Source decoded-media evidence;
        # only an explicitly typed external-media field is admissible here.
        media_reachable = bool(
            event.get("externalMediaIds")
            or event.get("externalSourceMediaIds")
        )
        try:
            media_reachable = media_reachable or int(
                event.get("externalResolvedMediaCount") or 0
            ) > 0
        except (TypeError, ValueError):
            pass
        external_media_by_hash[normalized_event_hash] = (
            external_media_by_hash.get(normalized_event_hash, False) or media_reachable
        )
        external_relation_by_hash[normalized_event_hash] = (
            external_relation_by_hash.get(normalized_event_hash, False)
            or bool(event.get("externalMediaRelationTypes"))
        )

    external_hashes = {row["eventHash"] for row in external_events}
    voice_alias_hashes = _event_hashes(audio_index.get("voiceTableWwiseEventAliases"))
    dialog_alias_hashes = _event_hashes(audio_index.get("audioDialogWwiseEventAliases"))
    voice_matches = external_hashes & voice_alias_hashes
    dialog_matches = external_hashes & dialog_alias_hashes
    without_voice = sorted(external_hashes - voice_alias_hashes)
    external_events_with_decoded_media = sum(external_media_by_hash.values())
    external_events_with_media_relations = sum(external_relation_by_hash.values())
    named_events = [
        row for row in external_events
        if row["eventId"] and not row["eventId"].casefold().startswith("hashed-event:")
    ]
    table_cache: dict[str, list[tuple[str, Any]] | None] = {}
    override_paths = _audio_dialog_override_paths(
        export_root,
        external_hashes,
        table_cache=table_cache,
    )
    channel_paths = _audio_dialog_channel_paths(
        export_root,
        external_hashes,
        table_cache=table_cache,
    )
    decoded_entries = _decoded_audio_dialog_entries(audio_index)
    override_path_mappings: list[dict[str, Any]] = []
    override_path_row_count = 0
    override_path_candidate_count = 0
    override_paths_with_decoded_media = 0
    if override_paths is not None:
        for event_hash, row in sorted(override_paths.items()):
            paths = sorted(str(value) for value in row.get("paths") or ())
            decoded_count = sum(
                path.replace("\\", "/").casefold() in decoded_entries
                for path in paths
            )
            decoded_audio_ids = sorted({
                str(entry.get("id") or "")
                for path in paths
                for entry in decoded_entries.get(path.replace("\\", "/").casefold(), ())
                if str(entry.get("id") or "")
            })
            override_path_row_count += int(row.get("rowCount") or 0)
            override_path_candidate_count += len(paths)
            override_paths_with_decoded_media += decoded_count
            override_path_mappings.append({
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "eventId": event_id_by_hash.get(event_hash, ""),
                "overrideWwiseEvent": str(row.get("overrideWwiseEvent") or ""),
                "rowCount": int(row.get("rowCount") or 0),
                "pathCount": len(paths),
                "decodedPathCount": decoded_count,
                "decodedAudioIdCount": len(decoded_audio_ids),
                "decodedAudioIdSamples": decoded_audio_ids[:12],
                "decodedAudioIdSamplesTruncated": len(decoded_audio_ids) > 12,
                "layers": sorted(str(value) for value in row.get("layers") or ()),
                # Full path inventories belong in generated reports; the
                # semantic index keeps a bounded deterministic sample.
                "pathSamples": paths[:12],
                "pathSamplesTruncated": len(paths) > 12,
            })
    override_event_count = len(override_path_mappings)
    unique_override_event_count = sum(
        row["pathCount"] == 1 for row in override_path_mappings
    )
    override_status = "complete" if override_paths is not None else "unavailable"
    channel_path_mappings: list[dict[str, Any]] = []
    channel_path_row_count = 0
    channel_path_candidate_count = 0
    channel_path_unique_candidates: set[str] = set()
    channel_paths_with_decoded_media = 0
    if channel_paths is not None:
        for event_hash, row in sorted(channel_paths.items()):
            paths = sorted(str(value) for value in row.get("paths") or ())
            if not paths:
                continue
            decoded_count = sum(
                path.replace("\\", "/").casefold() in decoded_entries
                for path in paths
            )
            channel_path_row_count += int(row.get("rowCount") or 0)
            channel_path_candidate_count += len(paths)
            channel_path_unique_candidates.update(paths)
            channel_paths_with_decoded_media += decoded_count
            channel_path_mappings.append({
                "eventHash": event_hash,
                "eventHashHex": f"0x{event_hash:08x}",
                "eventId": event_id_by_hash.get(event_hash, ""),
                "eventName": str(row.get("eventName") or ""),
                "rowCount": int(row.get("rowCount") or 0),
                "pathCount": len(paths),
                "decodedPathCount": decoded_count,
                "channelCount": len(row.get("channels") or ()),
                "channelSamples": sorted(str(value) for value in row.get("channels") or ())[:12],
                "channelSamplesTruncated": len(row.get("channels") or ()) > 12,
                "fields": sorted(str(value) for value in row.get("fields") or ()),
            })
    channel_status = "complete" if channel_paths is not None else "unavailable"
    decoded_channel_unique_count = sum(
        path.replace("\\", "/").casefold() in decoded_entries
        for path in channel_path_unique_candidates
    )
    return {
        "schemaVersion": 5,
        "language": str(language or "").upper(),
        "status": "complete",
        "source": (
            f"export_full/structured/Audio/{str(language or '').upper()}"
            "/index.json:wwiseEventInventory"
        ),
        "externalSourceEventCount": len(external_hashes),
        "externalSourceReferenceCount": external_reference_count,
        "externalSourceIds": [
            {"sourceId": source_id, "sourceIdHex": f"0x{source_id:08x}", "referenceCount": count}
            for source_id, count in sorted(source_ids.items())
        ],
        "voiceTableAliasCount": len(voice_alias_hashes),
        "audioDialogAliasCount": len(dialog_alias_hashes),
        "externalEventsWithVoiceTableAlias": len(voice_matches),
        "externalEventsWithAudioDialogAlias": len(dialog_matches),
        "externalEventsWithoutVoiceTableAlias": len(without_voice),
        "externalEventsWithDecodedMedia": external_events_with_decoded_media,
        "externalEventsWithMediaRelations": external_events_with_media_relations,
        "externalEventsWithZeroResolvedMedia": len(external_hashes) - external_events_with_decoded_media,
        "externalOverridePathAuditStatus": override_status,
        "externalEventsWithOverridePathCandidates": override_event_count,
        "externalEventsWithUniqueOverridePath": unique_override_event_count,
        "externalOverridePathRowCount": override_path_row_count,
        "externalOverridePathCandidateCount": override_path_candidate_count,
        "externalOverridePathCandidatesWithDecodedMedia": override_paths_with_decoded_media,
        "externalOverridePathCandidatesWithoutDecodedMedia": (
            override_path_candidate_count - override_paths_with_decoded_media
        ),
        "externalOverridePathMappings": override_path_mappings,
        "externalChannelPathAuditStatus": channel_status,
        "externalEventsWithChannelPathCandidates": len(channel_path_mappings),
        "externalChannelPathRowCount": channel_path_row_count,
        "externalChannelPathCandidateCount": channel_path_candidate_count,
        "externalChannelPathUniqueCandidateCount": len(channel_path_unique_candidates),
        "externalChannelPathCandidatesWithDecodedMedia": channel_paths_with_decoded_media,
        "externalChannelPathUniqueCandidatesWithDecodedMedia": decoded_channel_unique_count,
        "externalChannelPathMappings": channel_path_mappings,
        "externalEventsWithoutVoiceTableAliasSamples": [
            f"0x{value:08x}" for value in without_voice[:12]
        ],
        "namedExternalEventCount": len(named_events),
        "hashedExternalEventCount": len(external_hashes) - len(named_events),
        "namedExternalEventSamples": [
            row["eventId"] for row in sorted(named_events, key=lambda item: item["eventId"].casefold())[:12]
        ],
        "evidenceBoundary": (
            f"The current {str(language or '').upper()} Wwise inventory contains "
            f"{len(external_hashes):,} External Source Events ({external_reference_count:,} "
            f"source references). {len(voice_matches):,} Event ids join the typed "
            f"voice-table routing aliases, while {len(dialog_matches):,} join the "
            "narrow AudioDialog path-hash/Event-id aliases. "
            f"{external_events_with_decoded_media:,} External Source Events have a "
            "static decoded-media leaf or media relation. The zero/positive split "
            "shows that the External Source Event selects a voice route/template, "
            "whereas the per-request media identity remains the managed "
            "externalSourceKey path; this does not prove a live branch or file open. "
            + (
                f"Typed AudioDialog override fields add {override_event_count:,} route "
                f"Event -> {override_path_candidate_count:,} authored path candidates "
                f"({override_paths_with_decoded_media:,} currently decoded); shared "
                "routes remain candidates rather than a per-request selection."
                if override_paths is not None
                else "AudioDialog override/path sources were unavailable, so no route-to-path candidate join was emitted."
            )
            + (
                f" Typed channel routes additionally cover {len(channel_path_mappings):,} Events "
                f"with {channel_path_candidate_count:,} candidate paths "
                f"({decoded_channel_unique_count:,} unique paths decoded); this broader join "
                "is channel/radio-selection evidence, not a selected row."
                if channel_paths is not None
                else " AudioDialog channel sources were unavailable, so no channel-to-path candidate join was emitted."
            )
        ),
    }
