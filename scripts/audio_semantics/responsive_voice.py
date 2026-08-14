"""Responsive-dialog, AIBark, and voice-tone recovery.

This module owns table overlay parsing and exact authored response membership.
It receives validated native evidence explicitly; table rows remain available
when native binaries are missing, while build-locked dispatch claims fail closed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .context_utils import append_context as _append_context
from .context_utils import load_json as _load_json
from .context_utils import normalize_posix as _normalize_posix
from .native_evidence import (
    AI_BARK_NATIVE_RUNTIME,
    ENEMY_TRIGGER_VOICE_ACTION_NATIVE,
    NativeAudioEvidence,
)

def collect_ai_bark_trigger_rows(
    export_root: Path,
    *,
    native_context: NativeAudioEvidence,
) -> dict[str, list[dict[str, Any]]]:
    """Index exact AIBark rows by the response trigger key they dispatch."""

    merged: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for source_layer in ("StreamingAssets", "Persistent"):
        path = export_root / "structured" / source_layer / "Table" / "AIBark.json"
        payload = _load_json(path, {}) if path.is_file() else {}
        source = _normalize_posix(path.relative_to(export_root))
        for bark_id, group in (payload.items() if isinstance(payload, dict) else []):
            rows = group.get("array") if isinstance(group, dict) else None
            for row_index, raw_row in enumerate(rows or []):
                if not isinstance(raw_row, dict):
                    continue
                for raw_trigger_key in raw_row.get("triggerKey") or []:
                    trigger_key = str(raw_trigger_key or "").strip()
                    if not trigger_key:
                        continue
                    value = {
                        "barkId": str(raw_row.get("barkId") or bark_id),
                        "barkType": raw_row.get("type"),
                        "barkVoTypes": raw_row.get("voType") or [],
                        "speakerType": raw_row.get("speakerType"),
                        "triggerKey": trigger_key,
                        "triggerOdd": raw_row.get("triggerOdd"),
                        "barkOdds": raw_row.get("barkOdd") or [],
                        "delay": raw_row.get("delay"),
                        "isShuffle": raw_row.get("isShuffle"),
                        "isEnabled": raw_row.get("isEnabled"),
                        "rowIndex": row_index,
                        "sources": [source],
                        "evidence": "exactAIBarkRowTriggerKey",
                        "runtimeRoute": (
                            "BarkSystem.Bark -> GameAction.PostAIBarkEvent -> "
                            "AIBarkManager.PostAIBarkEvent -> _DoPostAIBarkVoiceEvent -> "
                            "VoiceManager.PostAIBarkVoiceEvent -> VoiceBarkProcessor.AIBark"
                        ),
                        "runtimeActivationStatus": (
                            "aiBarkTypeToBarkIdDictionarySelectionAndLiveExecutionUnobserved"
                            if native_context.validated
                            else "nativeAudioEvidenceUnavailable"
                        ),
                        **(AI_BARK_NATIVE_RUNTIME if native_context.validated else {}),
                    }
                    identity = json.dumps(
                        {key: value[key] for key in (
                            "barkId", "barkType", "barkVoTypes", "speakerType",
                            "triggerKey", "triggerOdd", "barkOdds", "delay",
                            "isShuffle", "isEnabled", "rowIndex",
                        )},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    previous = merged[trigger_key.casefold()].get(identity)
                    if previous is None:
                        merged[trigger_key.casefold()][identity] = value
                    elif source not in previous["sources"]:
                        previous["sources"].append(source)
    return {
        trigger_key: sorted(
            rows.values(),
            key=lambda row: (str(row.get("barkId") or ""), int(row.get("rowIndex") or 0)),
        )
        for trigger_key, rows in merged.items()
    }


def build_ai_bark_catalog(
    export_root: Path,
    audio_index: dict[str, Any],
    media: list[dict[str, Any]],
    *,
    native_context: NativeAudioEvidence,
) -> dict[str, Any]:
    """Summarize AIBark-authored response coverage, including absent media IDs."""

    bark_rows_by_trigger = collect_ai_bark_trigger_rows(
        export_root,
        native_context=native_context,
    )
    bark_ids = {
        str(row.get("barkId") or "")
        for rows in bark_rows_by_trigger.values()
        for row in rows
        if str(row.get("barkId") or "")
    }
    response_occurrences: dict[
        tuple[str, str, str, int, int], dict[str, Any]
    ] = {}
    source_response_occurrences = 0
    for source_layer in ("StreamingAssets", "Persistent"):
        path = (
            export_root / "structured" / source_layer / "Table"
            / "ResponsiveDialog.json"
        )
        payload = _load_json(path, {}) if path.is_file() else {}
        source = _normalize_posix(path.relative_to(export_root))
        for sentence_type, sentence_row in (
            payload.items() if isinstance(payload, dict) else []
        ):
            speakers = sentence_row.get("speakers") if isinstance(sentence_row, dict) else None
            for speaker_id, speaker_row in (
                speakers.items() if isinstance(speakers, dict) else []
            ):
                triggers = speaker_row.get("triggers") if isinstance(speaker_row, dict) else None
                for trigger_key, trigger_row in (
                    triggers.items() if isinstance(triggers, dict) else []
                ):
                    trigger_folded = str(trigger_key).casefold()
                    if trigger_folded not in bark_rows_by_trigger or not isinstance(trigger_row, dict):
                        continue
                    responses = trigger_row.get("response") or []
                    if not isinstance(responses, list):
                        continue
                    for response_index, raw_voice_id in enumerate(responses):
                        if not isinstance(raw_voice_id, int):
                            continue
                        source_response_occurrences += 1
                        voice_id = raw_voice_id & 0xFFFFFFFF
                        identity = (
                            str(sentence_type), str(speaker_id), str(trigger_key),
                            response_index, voice_id,
                        )
                        row = response_occurrences.setdefault(identity, {
                            "voiceId": voice_id,
                            "signedVoiceId": (
                                voice_id if voice_id < (1 << 31) else voice_id - (1 << 32)
                            ),
                            "sentenceType": str(sentence_type),
                            "speakerId": str(speaker_id),
                            "triggerKey": str(trigger_key),
                            "responseIndex": response_index,
                            "barkIds": sorted({
                                str(bark.get("barkId") or "")
                                for bark in bark_rows_by_trigger[trigger_folded]
                                if str(bark.get("barkId") or "")
                            }),
                            "sources": [],
                        })
                        if source not in row["sources"]:
                            row["sources"].append(source)

    occurrences_by_voice_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in response_occurrences.values():
        occurrences_by_voice_id[int(row["voiceId"])].append(row)

    direct_media_ids = {
        int(row.get("audioDialogKey")) & 0xFFFFFFFF
        for row in media
        if isinstance(row, dict) and isinstance(row.get("audioDialogKey"), int)
    }
    story_bound_ids = {
        int(row.get("audioDialogKey")) & 0xFFFFFFFF
        for row in media
        if isinstance(row, dict)
        and isinstance(row.get("audioDialogKey"), int)
        and int(row.get("storyLineBindingCount") or 0) > 0
    }
    event_aliases = {
        int(row.get("eventHash")) & 0xFFFFFFFF: str(row.get("name") or "")
        for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    response_ids = set(occurrences_by_voice_id)
    playable_ids = response_ids & (direct_media_ids | set(event_aliases))
    event_only_ids = sorted(response_ids & set(event_aliases) - direct_media_ids)
    unresolved_ids = sorted(response_ids - playable_ids)

    unresolved_rows = []
    for voice_id in unresolved_ids:
        occurrences = occurrences_by_voice_id[voice_id]
        unresolved_rows.append({
            "voiceId": voice_id,
            "signedVoiceId": (
                voice_id if voice_id < (1 << 31) else voice_id - (1 << 32)
            ),
            "sentenceTypes": sorted({row["sentenceType"] for row in occurrences}),
            "speakerIds": sorted({row["speakerId"] for row in occurrences}),
            "triggerKeys": sorted({row["triggerKey"] for row in occurrences}),
            "barkIds": sorted({
                bark_id for row in occurrences for bark_id in row["barkIds"]
            }),
            "sources": sorted({
                source for row in occurrences for source in row["sources"]
            }),
            "status": "authoredAIBarkResponseWithoutCurrentPlaybackObject",
            "evidence": (
                "exactResponsiveDialogResponseVoiceIdMissingFromCurrentAudioDialogMedia"
                "AndWwiseEventAliases"
            ),
        })

    return {
        "schemaVersion": 1,
        "counts": {
            "authoredBarkIds": len(bark_ids),
            "authoredRequestRows": sum(len(rows) for rows in bark_rows_by_trigger.values()),
            "triggerKeys": len(bark_rows_by_trigger),
            "responsiveSourceOccurrences": source_response_occurrences,
            "responsiveUniqueOccurrences": len(response_occurrences),
            "uniqueResponseVoiceIds": len(response_ids),
            "directDecodedMediaVoiceIds": len(response_ids & direct_media_ids),
            "exactStoryLineBoundVoiceIds": len(response_ids & story_bound_ids),
            "directMediaWithoutStoryLineBindingVoiceIds": len(
                response_ids & direct_media_ids - story_bound_ids
            ),
            "wwiseEventOnlyVoiceIds": len(event_only_ids),
            "playableVoiceIds": len(playable_ids),
            "unresolvedVoiceIds": len(unresolved_ids),
            "unresolvedSentenceType32AnyVoiceIds": sum(
                row["sentenceTypes"] == ["32"] and row["speakerIds"] == ["any"]
                for row in unresolved_rows
            ),
        },
        "eventOnlyResponses": [{
            "voiceId": voice_id,
            "eventName": event_aliases[voice_id],
            "status": "exactAudioDialogWwiseEventWithoutDirectDecodedMediaIdentity",
        } for voice_id in event_only_ids],
        "unresolvedResponses": unresolved_rows,
        "nativeRuntime": (
            AI_BARK_NATIVE_RUNTIME
            if native_context.validated
            else native_context.unavailable_contract(
                str(AI_BARK_NATIVE_RUNTIME["nativeMappingId"])
            )
        ),
        "evidenceBoundary": (
            "AIBark trigger rows and ResponsiveDialog response membership are exact; "
            "story-line-bound media are terminal purpose matches. Missing response IDs "
            "are retained as authored configuration, not inferred as playable media. "
            "Live bark-id choice, probability/cooldown/tone selection, and execution "
            "remain unobserved."
        ),
    }


def collect_responsive_voice_contexts(
    export_root: Path,
    audio_index: dict[str, Any],
    *,
    native_context: NativeAudioEvidence,
) -> dict[str, list[dict[str, Any]]]:
    """Attach authored responsive-voice routes to exact Wwise Event aliases.

    Alias rows have already passed the three-way AudioDialog path hash,
    signed voice-id, and complete type-4 Wwise Event-id equality gate.  The
    response table proves possible trigger membership; native selection,
    cooldown, probability, tone replacement, and the actually heard response
    remain unresolved.
    """

    aliases = {
        int(row.get("eventHash")) & 0xFFFFFFFF: row
        for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict)
        and isinstance(row.get("eventHash"), int)
        and str(row.get("name") or "").strip()
    }
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    if not aliases:
        return {}

    ai_bark_by_trigger = collect_ai_bark_trigger_rows(
        export_root,
        native_context=native_context,
    )
    enemy_action_by_trigger = {
        row["triggerKey"].casefold(): row
        for row in ENEMY_TRIGGER_VOICE_ACTION_NATIVE["voiceTypes"]
    } if native_context.validated else {}

    extra_by_hash: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for source_layer in ("StreamingAssets", "Persistent"):
        extra_path = (
            export_root / "structured" / source_layer / "Table"
            / "AudioVoiceExtraData.json"
        )
        payload = _load_json(extra_path, {}) if extra_path.is_file() else {}
        for raw_voice_id, raw_row in (payload.items() if isinstance(payload, dict) else []):
            if not isinstance(raw_row, dict):
                continue
            try:
                voice_hash = int(raw_voice_id) & 0xFFFFFFFF
            except (TypeError, ValueError):
                continue
            extra_by_hash[voice_hash].append({
                "sourceLayer": source_layer,
                "source": _normalize_posix(extra_path.relative_to(export_root)),
                "devStageCN": raw_row.get("devStageCN"),
                "devStageEN": raw_row.get("devStageEN"),
                "devStageJP": raw_row.get("devStageJP"),
                "devStageKR": raw_row.get("devStageKR"),
                "durationCN": raw_row.get("durationCN"),
                "durationEN": raw_row.get("durationEN"),
                "durationJP": raw_row.get("durationJP"),
                "durationKR": raw_row.get("durationKR"),
            })

    for event_hash, alias in sorted(aliases.items()):
        event_id = str(alias["name"]).strip().lower()
        _append_context(contexts, seen, event_id, {
            "kind": "audioDialogVoiceDefinition",
            "voiceId": alias.get("voiceId"),
            "eventHash": event_hash,
            "eventHashHex": f"0x{event_hash:08x}",
            "audioDialogPath": alias.get("name"),
            "codec": alias.get("codec"),
            "speakerChannel": alias.get("speakerChannel") or "",
            "voType": alias.get("voType"),
            "sources": alias.get("sources") or [],
            "voiceExtraData": extra_by_hash.get(event_hash) or [],
            "voiceExtraDataStatus": (
                "exactSignedVoiceIdTableRows"
                if extra_by_hash.get(event_hash) else "notPresent"
            ),
            "evidence": alias.get("evidence") or "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
            "playbackPlacementStatus": "definitionOnly",
        })

    responsive_paths = [
        export_root / "structured" / source / "Table" / "ResponsiveDialog.json"
        for source in ("StreamingAssets", "Persistent")
        if (export_root / "structured" / source / "Table" / "ResponsiveDialog.json").is_file()
    ]
    for responsive_path in responsive_paths:
        payload = _load_json(responsive_path, {})
        source = _normalize_posix(responsive_path.relative_to(export_root))
        for sentence_type, sentence_row in (payload.items() if isinstance(payload, dict) else []):
            speakers = sentence_row.get("speakers") if isinstance(sentence_row, dict) else None
            if not isinstance(speakers, dict):
                continue
            for speaker_id, speaker_row in speakers.items():
                triggers = speaker_row.get("triggers") if isinstance(speaker_row, dict) else None
                if not isinstance(triggers, dict):
                    continue
                for trigger_key, trigger_row in triggers.items():
                    if not isinstance(trigger_row, dict):
                        continue
                    responses = trigger_row.get("response") or []
                    weights = trigger_row.get("weight") or []
                    if not isinstance(responses, list):
                        continue
                    if not isinstance(weights, list):
                        weights = []
                    for response_index, raw_voice_id in enumerate(responses):
                        if not isinstance(raw_voice_id, int):
                            continue
                        event_hash = raw_voice_id & 0xFFFFFFFF
                        alias = aliases.get(event_hash)
                        if alias is None:
                            continue
                        event_id = str(alias["name"]).strip().lower()
                        ai_bark_requests = ai_bark_by_trigger.get(
                            str(trigger_key).casefold(), []
                        )
                        enemy_action_mapping = enemy_action_by_trigger.get(
                            str(trigger_key).casefold()
                        )
                        _append_context(contexts, seen, event_id, {
                            "kind": "responsiveDialogVoice",
                            "sentenceType": str(sentence_type),
                            "speakerId": str(speaker_id),
                            "triggerKey": str(trigger_key),
                            "triggerTypeId": trigger_row.get("triggerTypeId"),
                            "responseIndex": response_index,
                            "responseWeight": weights[response_index] if response_index < len(weights) else None,
                            "aiBarkRequests": ai_bark_requests,
                            "aiBarkRuntimeStatus": (
                                "exactAIBarkTableTriggerCandidate"
                                if ai_bark_requests and native_context.validated
                                else "authoredAIBarkTableTriggerNativeRouteUnavailable"
                                if ai_bark_requests
                                else "notAnAIBarkTableTrigger"
                            ),
                            "enemyTriggerVoiceAction": enemy_action_mapping,
                            "enemyTriggerVoiceActionStatus": (
                                "exactNativeVoiceTypeTriggerMapping"
                                if enemy_action_mapping else "notAnEnemyTriggerVoiceActionKey"
                            ),
                            "voiceId": raw_voice_id,
                            "eventHash": event_hash,
                            "audioDialogPath": alias.get("name"),
                            "source": source,
                            "evidence": "exactResponsiveDialogResponseVoiceId",
                            "runtimeRoute": "VoiceResponseProcessor._HandleSelection -> _QueueResponse -> VoiceSpeakChannelProcessor._PlayVoice -> VoicePlayer.PlayVoice",
                            "runtimeSelectionStatus": "probabilityCooldownBandLimitToneAndLiveChoiceUnobserved",
                            "playbackPlacementStatus": "authoredPossibleTrigger",
                        })

    tone_paths = [
        export_root / "structured" / source / "Table" / "AudioVoTone.json"
        for source in ("StreamingAssets", "Persistent")
        if (export_root / "structured" / source / "Table" / "AudioVoTone.json").is_file()
    ]
    for tone_path in tone_paths:
        payload = _load_json(tone_path, {})
        source = _normalize_posix(tone_path.relative_to(export_root))
        for raw_base_id, tone_row in (payload.items() if isinstance(payload, dict) else []):
            try:
                base_voice_id = int(raw_base_id)
            except (TypeError, ValueError):
                continue
            tone_list = tone_row.get("toneList") if isinstance(tone_row, dict) else None
            for variant_index, raw_voice_id in enumerate(tone_list or []):
                if not isinstance(raw_voice_id, int):
                    continue
                event_hash = raw_voice_id & 0xFFFFFFFF
                alias = aliases.get(event_hash)
                if alias is None:
                    continue
                event_id = str(alias["name"]).strip().lower()
                _append_context(contexts, seen, event_id, {
                    "kind": "voiceToneVariant",
                    "baseVoiceId": base_voice_id,
                    "variantVoiceId": raw_voice_id,
                    "variantIndex": variant_index,
                    "eventHash": event_hash,
                    "audioDialogPath": alias.get("name"),
                    "source": source,
                    "evidence": "exactAudioVoToneVariantVoiceId",
                    "runtimeRoute": "VoiceUtilsInternal.ApplyRandomVoiceTone -> TryReplaceVoiceIdWithTone",
                    "runtimeSelectionStatus": "liveVariantSelectionUnobserved",
                    "playbackPlacementStatus": "selectionTransformOnly",
                })

    # Compose exact response membership with exact tone substitution. A tone
    # row alone is not placement evidence, but a base voice that is an authored
    # response candidate makes every exact AudioVoTone replacement a candidate
    # for the same trigger family.
    aliases_by_voice_id = {
        int(row.get("voiceId")) & 0xFFFFFFFF: row
        for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict) and isinstance(row.get("voiceId"), int)
    }
    tone_rows = [
        (event_id, row)
        for event_id, event_contexts in list(contexts.items())
        for row in list(event_contexts)
        if isinstance(row, dict) and row.get("kind") == "voiceToneVariant"
    ]
    for variant_event_id, tone in tone_rows:
        base_alias = aliases_by_voice_id.get(int(tone.get("baseVoiceId") or 0) & 0xFFFFFFFF)
        if not isinstance(base_alias, dict):
            continue
        base_event_id = str(base_alias.get("name") or "").strip().lower()
        if not base_event_id:
            continue
        for response in list(contexts.get(base_event_id) or []):
            if not isinstance(response, dict) or response.get("kind") != "responsiveDialogVoice":
                continue
            _append_context(contexts, seen, variant_event_id, {
                "kind": "responsiveDialogToneVariant",
                "sentenceType": response.get("sentenceType"),
                "speakerId": response.get("speakerId"),
                "triggerKey": response.get("triggerKey"),
                "triggerTypeId": response.get("triggerTypeId"),
                "responseIndex": response.get("responseIndex"),
                "responseWeight": response.get("responseWeight"),
                "aiBarkRequests": response.get("aiBarkRequests") or [],
                "aiBarkRuntimeStatus": response.get("aiBarkRuntimeStatus"),
                "enemyTriggerVoiceAction": response.get("enemyTriggerVoiceAction"),
                "enemyTriggerVoiceActionStatus": response.get(
                    "enemyTriggerVoiceActionStatus"
                ),
                "baseVoiceId": tone.get("baseVoiceId"),
                "variantVoiceId": tone.get("variantVoiceId"),
                "variantIndex": tone.get("variantIndex"),
                "eventHash": tone.get("eventHash"),
                "audioDialogPath": tone.get("audioDialogPath"),
                "responsiveSource": response.get("source"),
                "toneSource": tone.get("source"),
                "evidence": "exactResponsiveDialogResponseVoiceIdComposedWithExactAudioVoToneVariantVoiceId",
                "runtimeRoute": (
                    "VoiceResponseProcessor response selection -> "
                    "VoiceUtilsInternal.ApplyRandomVoiceTone -> TryReplaceVoiceIdWithTone -> "
                    "VoiceSpeakChannelProcessor._PlayVoice -> VoicePlayer.PlayVoice"
                ),
                "runtimeSelectionStatus": "baseResponseToneProbabilityCooldownAndLiveChoiceUnobserved",
                "playbackPlacementStatus": "authoredPossibleTriggerViaToneTransform",
            })
    return dict(contexts)
