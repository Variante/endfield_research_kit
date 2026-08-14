"""Purpose-recovery classification for Wwise Events and decoded media."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def has_authored_playback_context(contexts: Iterable[dict[str, Any]]) -> bool:
    """Return whether a context says more than identity/definition alone."""
    return any(
        str(row.get("playbackPlacementStatus") or "")
        not in {
            "definitionOnly",
            "selectionTransformOnly",
            "identityOnlyManagedStringLiteral",
        }
        for row in contexts
        if isinstance(row, dict)
    )


def classify_event_purpose(
    contexts: Iterable[dict[str, Any]],
    playback_role: str,
    identity_alias: dict[str, Any] | None,
) -> tuple[str, str, str]:
    """Return knowledge, investigation priority, and placement for an Event."""

    context_rows = list(contexts)
    if has_authored_playback_context(context_rows):
        return "authoredContextKnown", "resolved", "authoredContext"
    if playback_role == "controlOnly":
        return (
            "audioLibraryControlKnown",
            "secondary",
            "libraryControlOnlyExternalCallerUnknown",
        )
    if playback_role == "emptyEventDefinition":
        return (
            "audioLibraryEmptyEventKnown",
            "secondary",
            "libraryEmptyEventExternalCallerUnknown",
        )
    if (
        (identity_alias or {}).get("dictionaryKind") == "skill_id"
        and (identity_alias or {}).get("playbackPlacementStatus")
        == "identityOnlyNoAudioConsumer"
    ):
        return "identityOnlyNoConsumer", "highest", "unknown"
    return (
        "identityOnlyNoConsumer" if context_rows else "unknownUse",
        "highest",
        "unknown",
    )


def wwise_play_target_signatures(event: dict[str, Any]) -> list[tuple[str, tuple[int, ...]]]:
    """Return exact per-bank sets of Wwise targets reached by Play Actions."""
    signatures: list[tuple[str, tuple[int, ...]]] = []
    for evidence in event.get("evidence") or []:
        if not isinstance(evidence, dict):
            continue
        targets = tuple(sorted({
            int(action["targetId"])
            for action in evidence.get("actionEvidence") or []
            if isinstance(action, dict)
            and action.get("operation") == "play"
            and isinstance(action.get("targetId"), int)
        }))
        if targets:
            signatures.append((str(evidence.get("bank") or ""), targets))
    return signatures


def annotate_shared_wwise_play_targets(events: list[dict[str, Any]]) -> int:
    """Attach library-output equivalence without inventing a shared trigger.

    Different Wwise Event objects may contain different Action objects that
    reach the exact same complete Play-target set.  A named Event with an
    authored consumer can then classify the anonymous Event's library output,
    but cannot identify who posts the anonymous Event.
    """
    known_by_signature: dict[tuple[str, tuple[int, ...]], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        event_id = str(event.get("id") or "")
        if (
            event.get("purposeKnowledgeStatus") != "authoredContextKnown"
            or event_id.startswith("hashed-event:0x")
            or event.get("category") == "unknown"
        ):
            continue
        for signature in wwise_play_target_signatures(event):
            known_by_signature[signature].append(event)

    annotated = 0
    for event in events:
        if event.get("purposeInvestigationPriority") != "highest":
            continue
        matches: dict[str, dict[str, Any]] = {}
        matched_signatures: set[tuple[str, tuple[int, ...]]] = set()
        for signature in wwise_play_target_signatures(event):
            rows = known_by_signature.get(signature) or []
            if rows:
                matched_signatures.add(signature)
            for row in rows:
                matches[str(row.get("id") or "")] = row
        matches.pop(str(event.get("id") or ""), None)
        if not matches:
            continue
        categories = sorted({str(row.get("category") or "") for row in matches.values()} - {"", "unknown"})
        event["audioLibraryPlaybackTargetStatus"] = "exactSharedPlayTargetSetWithAuthoredEvent"
        event["audioLibraryEquivalentEventIds"] = sorted(matches)[:24]
        event["audioLibraryEquivalentEventCount"] = len(matches)
        event["audioLibraryEquivalentCategories"] = categories
        event["audioLibrarySharedPlayTargetSets"] = [
            {
                "bank": bank,
                "targetIds": list(targets),
                "targetIdsHex": [f"0x{target:08x}" for target in targets],
            }
            for bank, targets in sorted(matched_signatures)
        ][:8]
        event["audioLibraryPurposeHintStatus"] = "libraryOutputEquivalentOnlyExternalTriggerUnknown"
        if event.get("category") == "unknown" and len(categories) == 1:
            event["category"] = categories[0]
            event["categoryEvidence"] = "exactSharedWwisePlayTargetSet"
        annotated += 1
    return annotated


def wwise_media_leaf_signature(event: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    """Return the complete decoded Wwise media-ID set, scoped by PCK."""
    leaves: set[tuple[str, int]] = set()
    for media in event.get("media") or []:
        if not isinstance(media, dict):
            continue
        media_id = media.get("mediaId")
        if not isinstance(media_id, int):
            continue
        bank = Path(str(media.get("bank") or "")).name.lower()
        if not bank:
            evidence = next((
                row for row in media.get("wwiseMediaEvidence") or []
                if isinstance(row, dict) and row.get("bankPackage")
            ), {})
            bank = str(evidence.get("bankPackage") or "").lower()
        leaves.add((bank, media_id))
    return tuple(sorted(leaves))


def annotate_shared_wwise_media_leaves(events: list[dict[str, Any]]) -> int:
    """Record exact final-media equivalence while leaving trigger purpose open.

    Matching every decoded Wwise media ID inside the same PCK proves that two
    Events can reach the same final audio leaves.  It does not prove that their
    intervening containers, conditions, timing, ownership, or callers match.
    """
    known_by_signature: dict[tuple[tuple[str, int], ...], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        event_id = str(event.get("id") or "")
        signature = wwise_media_leaf_signature(event)
        if (
            not signature
            or event.get("purposeKnowledgeStatus") != "authoredContextKnown"
            or event_id.startswith("hashed-event:0x")
        ):
            continue
        known_by_signature[signature].append(event)

    annotated = 0
    for event in events:
        if (
            event.get("purposeInvestigationPriority") != "highest"
            or event.get("audioLibraryPlaybackTargetStatus")
        ):
            continue
        signature = wwise_media_leaf_signature(event)
        matches = {
            str(row.get("id") or ""): row
            for row in known_by_signature.get(signature, [])
        } if signature else {}
        matches.pop(str(event.get("id") or ""), None)
        if not matches:
            continue
        event["audioLibraryMediaLeafStatus"] = "exactCompleteWwiseMediaIdSetWithAuthoredEvent"
        event["audioLibraryMediaEquivalentEventIds"] = sorted(matches)[:24]
        event["audioLibraryMediaEquivalentEventCount"] = len(matches)
        event["audioLibraryMediaEquivalentCategories"] = sorted({
            str(row.get("category") or "") for row in matches.values()
        } - {"", "unknown"})
        event["audioLibrarySharedMediaIds"] = [media_id for _bank, media_id in signature][:64]
        event["audioLibrarySharedMediaPackages"] = sorted({bank for bank, _media_id in signature if bank})
        event["audioLibraryMediaPurposeHintStatus"] = (
            "completeMediaLeafSetEquivalentOnlyContainersAndExternalTriggerUnknown"
        )
        annotated += 1
    return annotated


def annotate_media_playback_locations(
    media: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> Counter[str]:
    """Classify recovered placement without inventing a runtime playback edge."""

    event_has_context: dict[str, bool] = {}
    for event in events:
        context_rows = [
            row for row in event.get("contexts") or [] if isinstance(row, dict)
        ]
        has_context = has_authored_playback_context(context_rows)
        if not context_rows:
            has_context = bool(int(event.get("contextCount") or 0))
        for value in (event.get("id"), event.get("eventId"), event.get("name")):
            key = str(value or "").strip().casefold()
            if key:
                event_has_context[key] = event_has_context.get(key, False) or has_context

    counts: Counter[str] = Counter()
    for row in media:
        event_ids = [
            str(value or "").strip().casefold()
            for value in row.get("eventIds") or []
            if str(value or "").strip()
        ]
        if row.get("audioDialogKey") or row.get("audioDialogPath"):
            status = "directDialogMedia"
        elif any(event_has_context.get(event_id, False) for event_id in event_ids):
            status = "authoredEventContext"
        elif event_ids:
            status = "eventRelationOnly"
        else:
            status = "unknown"
        row["playbackLocationStatus"] = status
        if int(row.get("storyLineBindingCount") or 0) > 0:
            row["purposeKnowledgeStatus"] = "exactStoryLineBinding"
            row["purposeInvestigationPriority"] = "resolvedTerminal"
        elif status == "unknown":
            row["purposeKnowledgeStatus"] = "unknownUse"
            row["purposeInvestigationPriority"] = "highest"
        elif status == "eventRelationOnly":
            row["purposeKnowledgeStatus"] = "eventGraphOnly"
            row["purposeInvestigationPriority"] = "secondary"
        else:
            row["purposeKnowledgeStatus"] = "authoredContextKnown"
            row["purposeInvestigationPriority"] = "resolved"
        counts[status] += 1
    return counts
