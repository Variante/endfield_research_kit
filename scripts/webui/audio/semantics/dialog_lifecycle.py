"""Project exact dialog lifecycle audio hooks onto Story conversations."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def project_story_lifecycle_audio(
    trigger_context_rows: Iterable[dict[str, Any]],
    conversation_ids: Iterable[str],
) -> dict[str, Any]:
    """Return playable lifecycle hooks for exact current conversation ids."""

    known = {str(value).strip() for value in conversation_ids if str(value).strip()}
    conversations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unique_media: set[tuple[str, str]] = set()
    missing_conversation_contexts = 0
    seen: set[tuple[str, str, str, int]] = set()
    for context in trigger_context_rows:
        if not isinstance(context, dict) or context.get("semanticKind") != "dialogLifecycle":
            continue
        situation = context.get("situation") or {}
        event_id = str(situation.get("eventId") or "").strip()
        media_refs = [{
            key: media[key]
            for key in (
                "mediaId", "src", "rel", "format", "duration", "contentSha256",
                "audioCategory", "audioScope", "sourceLanguage",
            )
            if media.get(key) not in (None, "", [])
        } for media in context.get("mediaRefs") or () if isinstance(media, dict) and media.get("src")]
        if not event_id or not media_refs:
            continue
        dialog_id = str(situation.get("dialogId") or "").strip()
        phase = str(situation.get("lifecyclePhase") or "").strip()
        array_index = int(situation.get("arrayIndex") or 0)
        action = context.get("action") or {}
        owner = context.get("owner") or {}
        selection = context.get("selection") or {}
        evidence = context.get("evidence") or {}
        identity = (dialog_id, phase, event_id.casefold(), array_index)
        if not dialog_id or identity in seen:
            continue
        seen.add(identity)
        if dialog_id not in known:
            missing_conversation_contexts += 1
            continue
        conversations[dialog_id].append({
            "eventId": event_id,
            "eventHash": situation.get("eventHash"),
            "lifecyclePhase": phase,
            "arrayIndex": array_index,
            "triggerRole": str(context.get("triggerRole") or ""),
            "runtimeMethod": str(action.get("runtimeMethod") or ""),
            "runtimeMethodToken": str(action.get("runtimeMethodToken") or ""),
            "ownerStatus": str(owner.get("ownerStatus") or ""),
            "triggerBindingStatus": str(selection.get("triggerBindingStatus") or ""),
            "runtimeActivationStatus": (
                context.get("runtimeActivationStatus")
                or "dialogLifecycleRuntimeExecutionNotObserved"
            ),
            "requestEvidence": list(evidence.get("requestEvidence") or ()),
            "sourceRefs": list(context.get("sourceRefs") or ()),
            "tablePath": str(situation.get("tablePath") or ""),
            "mediaRefs": media_refs,
        })
        unique_media.update((str(row.get("src") or ""), str(row.get("mediaId") or "")) for row in media_refs)
    for rows in conversations.values():
        rows.sort(key=lambda row: (row["lifecyclePhase"], row["arrayIndex"], row["eventId"].casefold()))
    return {
        "schemaVersion": 1,
        "conversations": dict(sorted(conversations.items())),
        "counts": {
            "conversations": len(conversations),
            "contexts": sum(map(len, conversations.values())),
            "uniqueEvents": len({row["eventId"].casefold() for rows in conversations.values() for row in rows}),
            "playableMediaRefs": sum(len(row["mediaRefs"]) for rows in conversations.values() for row in rows),
            "uniquePlayableMedia": len(unique_media),
            "missingConversationContexts": missing_conversation_contexts,
        },
        "evidenceBoundary": (
            "Each row is an exact AudioDialogCustomEventTable dialogId and lifecycle "
            "array member attached only when that Story conversation exists. Preload "
            "and post-enter are authored scheduling hooks; runtime dialog dispatch, "
            "Wwise branch selection, playback, and audibility remain unobserved."
        ),
    }
