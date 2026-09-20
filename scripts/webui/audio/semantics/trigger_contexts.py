"""Trigger-context catalog: what authored and native evidence says fires an Event.

Each collector answers one source of trigger evidence and returns compact context
rows. None of them establishes runtime execution, selection, or audibility."""

from __future__ import annotations
from scripts.source_paths import ExportLayout

import hashlib
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from scripts.webui.audio.semantics import managed_literals
from scripts.webui.audio.semantics import model_view_projection
from scripts.webui.audio.semantics import native_evidence
from scripts.webui.audio.semantics import table_contexts
from scripts.webui.audio.semantics.context_utils import load_json as load_json
from scripts.webui.audio.semantics.context_utils import normalize_posix as normalize_posix
from scripts.webui.audio.semantics.build_contracts import TIMELINE_AUDIO_RUNTIME_CONTRACTS as TIMELINE_AUDIO_RUNTIME_CONTRACTS

TRIGGER_CONTEXT_SCHEMA_VERSION = 39

def _trigger_media_ref(media: dict[str, Any] | None, *, fallback_id: str = "") -> dict[str, Any]:
    """Return a small media reference for the trigger-context shard.

    The event and media shards remain authoritative for full Wwise evidence.
    Trigger contexts only carry the identity needed to navigate to that media,
    plus the small amount of duration/speaker information useful when reading
    a situation without opening another shard.
    """

    media = media if isinstance(media, dict) else {}
    ref: dict[str, Any] = {}
    for key in (
        "id", "mediaId", "src", "rel", "format", "duration",
        "audioDialogPath", "speakerChannel", "audioCategory", "audioScope",
        "sourceLanguage",
    ):
        value = media.get(key)
        if value not in (None, "", []):
            ref[key] = value
    if fallback_id and not ref.get("id"):
        ref["id"] = fallback_id
    return ref

def _compact_trigger_action(context: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "action", "triggerRole", "levelScriptId", "sourceRoot", "sourcePath",
        "recordIndex", "recordStart", "recordUid", "recordLocalId",
        "actionMapRole", "unionTag", "serializedMemberCount", "nativeMappingId",
        "payloadShape", "sourceField", "fields", "runtimeActivationStatus",
    )
    return {
        key: context[key]
        for key in keys
        if context.get(key) not in (None, "", [])
    }

DIALOG_LIFECYCLE_PATH_RE = re.compile(
    r"^(?P<dialogId>[^.]+)\."
    r"(?P<phase>preloadEvents|preEnterEvents|postEnterEvents|preExitEvents|postExitEvents)"
    r"\[(?P<index>\d+)\]$"
)

DIALOG_LIFECYCLE_PHASES = {
    "preloadEvents": {
        "triggerRole": "DialogPreloadAudioEvent",
        "runtimeMethod": "_StartDialogEventPreload",
        "runtimeMethodToken": "0x060099ec",
    },
    "preEnterEvents": {
        "triggerRole": "DialogPreEnterAudioEvent",
        "runtimeMethod": "_OnPreEnterDialog",
        "runtimeMethodToken": "0x060099e7",
    },
    "postEnterEvents": {
        "triggerRole": "DialogPostEnterAudioEvent",
        "runtimeMethod": "_OnPostEnterDialog",
        "runtimeMethodToken": "0x060099e8",
    },
    "preExitEvents": {
        "triggerRole": "DialogPreExitAudioEvent",
        "runtimeMethod": "_OnPreExitDialog",
        "runtimeMethodToken": "0x060099e9",
    },
    "postExitEvents": {
        "triggerRole": "DialogPostExitAudioEvent",
        "runtimeMethod": "_OnPostExitDialog",
        "runtimeMethodToken": "0x060099ea",
    },
}

DIALOG_LIFECYCLE_RUNTIME_CONSUMER = {
    "type": "Beyond.Gameplay.Audio.AudioGameplayStatusSystem",
    "image": "Gameplay.Beyond.dll",
    "typeToken": "0x02001a6f",
    "source": "reports/story/recovery/options/option_flow_runtime_metadata.json",
    "fields": [
        "m_currentDialogId",
        "m_dialogEventStatus",
        "m_pendingDialogAudioEventIds",
        "m_pinnedDialogAudioEventIds",
    ],
    "methods": {
        "schedule": {
            "name": "_ScheduleDialogAudioEvent",
            "token": "0x060099eb",
        },
        "preload": {
            "name": "_StartDialogEventPreload",
            "token": "0x060099ec",
        },
        "preloadCompleted": {
            "name": "_OnDialogEventPreloadCompleted",
            "token": "0x060099ed",
        },
        "triggerPending": {
            "name": "_TriggerAllPendingDialogAudioEvents",
            "token": "0x060099ee",
        },
    },
    "evidenceBoundary": "staticTypeAndMethodMetadataOnly",
}

def _conversation_line_meanings(
    webui_root: Path,
    language: str,
    *,
    kinds: frozenset[str],
) -> dict[str, dict[str, Any]]:
    meanings: dict[str, dict[str, Any]] = {}
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    if not conv_root.is_dir():
        return meanings
    for path in sorted(conv_root.glob("*.json")):
        payload = load_json(path, {})
        if not isinstance(payload, dict) or str(payload.get("kind") or "") not in kinds:
            continue
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            line_id = str(line.get("id") or "").strip()
            if not line_id:
                continue
            meanings.setdefault(line_id, {
                key: line[key]
                for key in ("id", "actor", "aid", "text", "slot", "cid", "audio", "duration")
                if line.get(key) not in (None, "", [])
            })
    return meanings

def _build_radio_trigger_contexts(
    media_rows: Iterable[dict[str, Any]],
    line_meanings: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        media_ref = _trigger_media_ref(media)
        for occurrence_index, raw_context in enumerate(
            media.get("radioTriggerContexts") or []
        ):
            if not isinstance(raw_context, dict):
                continue
            line = raw_context.get("radioLine")
            line = line if isinstance(line, dict) else {}
            radio_id = str(raw_context.get("radioId") or line.get("radioId") or "").strip()
            line_id = str(line.get("lineId") or "").strip()
            source_path = str(raw_context.get("sourcePath") or "").strip()
            record_uid = str(raw_context.get("recordUid") or "").strip()
            trigger_id = ":".join((
                "radio",
                source_path,
                record_uid or str(raw_context.get("recordStart") or occurrence_index),
                radio_id,
                line_id or str(line.get("lineOrdinal") or 0),
            ))
            meaning = line_meanings.get(line_id, {})
            definition = raw_context.get("radioDefinition")
            definition = definition if isinstance(definition, dict) else {}
            action = _compact_trigger_action(raw_context)
            if radio_id and "radioId" not in action:
                action["radioId"] = radio_id
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "radio",
                "triggerRole": str(
                    raw_context.get("triggerRole")
                    or raw_context.get("action")
                    or "play"
                ),
                "situation": {
                    key: value
                    for key, value in {
                        "levelScriptId": raw_context.get("levelScriptId"),
                        "radioId": radio_id,
                        "lineId": line_id,
                        "lineOrdinal": line.get("lineOrdinal"),
                    }.items()
                    if value not in (None, "", [])
                },
                "meaning": meaning,
                "action": action,
                "owner": {
                    "radioId": radio_id,
                    "radioDefinition": definition,
                    "radioLine": line,
                },
                "selection": {
                    "triggerRole": raw_context.get("triggerRole"),
                    "fields": raw_context.get("fields") or {},
                    "lineSelectionStatus": "runtimeLineSelectionUnobserved",
                },
                "mediaRefs": [media_ref] if media_ref else [],
                "evidence": {
                    "definition": "exactLevelScriptRadioAction",
                    "owner": "exactRadioTableLine",
                    "media": raw_context.get("audioDialogMatchEvidence")
                    or "audioDialogMediaUnresolved",
                    "runtimeExecution": raw_context.get("runtimeActivationStatus")
                    or "levelScriptActionExecutionNotObserved",
                },
                "runtimeActivationStatus": raw_context.get(
                    "runtimeActivationStatus"
                ) or "levelScriptActionExecutionNotObserved",
                "sourceRefs": [
                    value
                    for value in (
                        source_path,
                        str(line.get("source") or ""),
                        str(media.get("audioDialogPath") or ""),
                    )
                    if value
                ],
            })
    return contexts

def _build_envtalk_trigger_contexts(
    webui_root: Path,
    language: str,
    media_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    media_by_id = {
        str(row.get("id") or "").casefold(): row
        for row in media_rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    used_trigger_ids: set[str] = set()
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    if not conv_root.is_dir():
        return contexts
    for path in sorted(conv_root.glob("env_*.json")):
        payload = load_json(path, {})
        if not isinstance(payload, dict):
            continue
        env_id = str(payload.get("title") or payload.get("key") or "").strip()
        if not env_id:
            continue
        is_greeting = env_id.casefold().startswith("greetenvtalk_")
        if payload.get("kind") != "env" and not is_greeting:
            continue
        semantic_kind = "envTalkGreeting" if is_greeting else "envTalk"
        cooldown = payload.get("cooldown")
        payload_debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
        payload_source = payload_debug.get("source") if isinstance(payload_debug.get("source"), dict) else {}
        for line_index, line in enumerate(payload.get("lines") or []):
            if not isinstance(line, dict):
                continue
            audio_id = str(line.get("audio") or "").strip()
            line_debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            debug = line_debug or payload_debug
            source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
            if not source:
                source = payload_source
            hints = debug.get("speakerHints") if isinstance(debug.get("speakerHints"), list) else []
            if not hints and isinstance(payload_debug.get("speakerHints"), list):
                hints = payload_debug["speakerHints"]
            proxy_rows: list[dict[str, Any]] = []
            for hint in hints:
                if not isinstance(hint, dict):
                    continue
                hint_source = hint.get("source") if isinstance(hint.get("source"), dict) else {}
                fields = hint_source.get("fields") if isinstance(hint_source.get("fields"), dict) else {}
                proxy_info = fields.get("proxyInfoData") if isinstance(fields.get("proxyInfoData"), dict) else {}
                if not proxy_info:
                    proxy_info = hint.get("proxyInfoData") if isinstance(hint.get("proxyInfoData"), dict) else {}
                proxy_id = str(hint.get("proxyId") or fields.get("proxyId") or "").strip()
                if not proxy_id:
                    continue
                proxy_row = {
                    key: value
                    for key, value in {
                        "proxyId": proxy_id,
                        "levelId": fields.get("levelId"),
                        "npcId": proxy_info.get("npcId"),
                        "npcNameId": proxy_info.get("npcNameId"),
                        "npcProxyType": proxy_info.get("npcProxyType"),
                    }.items()
                    if value not in (None, "", [])
                }
                if proxy_row not in proxy_rows:
                    proxy_rows.append(proxy_row)
            media = media_by_id.get(audio_id.casefold(), {})
            media_ref = _trigger_media_ref(media, fallback_id=audio_id)
            if not media_ref.get("src") and line.get("audioSrc"):
                media_ref["src"] = line.get("audioSrc")
            audio_meta = line.get("audioMeta") if isinstance(line.get("audioMeta"), dict) else {}
            for key in ("duration", "audioDialogPath", "speakerChannel", "audioCategory"):
                if media_ref.get(key) in (None, "") and audio_meta.get(key) not in (None, ""):
                    media_ref[key] = audio_meta[key]
            proxy_ids = sorted({str(row.get("proxyId")) for row in proxy_rows})
            level_ids = sorted({
                str(row.get("levelId"))
                for row in proxy_rows
                if str(row.get("levelId") or "")
            })
            slot_id = line.get("slot")
            line_id = str(line.get("id") or env_id).strip()
            slot_actor_id = str(line.get("aid") or "").strip()
            slot_actor_match_status = (
                "exactProxyIdMatch"
                if slot_actor_id and slot_actor_id.casefold() in {
                    str(value.get("proxyId") or "").casefold()
                    for value in proxy_rows
                }
                else (
                    "proxyHintDoesNotMatchLineActor"
                    if proxy_rows and slot_actor_id
                    else "lineActorOrProxyOwnerUnresolved"
                )
            )
            base_trigger_id = ":".join((
                "envTalk",
                env_id,
                str(line.get("cid") or line_index + 1),
                str(slot_id if slot_id is not None else "unknown"),
                audio_id or line_id,
            ))
            trigger_id = base_trigger_id
            if trigger_id in used_trigger_ids:
                trigger_id = f"{base_trigger_id}:line{line_index}"
                suffix = 2
                while trigger_id in used_trigger_ids:
                    trigger_id = f"{base_trigger_id}:line{line_index}:{suffix}"
                    suffix += 1
            used_trigger_ids.add(trigger_id)
            owner_status = "exactNpcProxyTableSpeakerHint" if proxy_rows else "envTalkOwnerUnresolved"
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": semantic_kind,
                "triggerRole": (
                    "NpcProxyEnvTalkGreeting"
                    if is_greeting and proxy_rows
                    else "EnvTalkGreetingOwnerUnresolved"
                    if is_greeting
                    else "NpcProxyEnvTalk"
                    if proxy_rows
                    else "EnvTalkOwnerUnresolved"
                ),
                "situation": {
                    "envTalkId": env_id,
                    "envTalkVariant": "greetEnvTalk" if is_greeting else "envTalk",
                    "mission": payload.get("mission"),
                    "levelIds": level_ids,
                    "proxyIds": proxy_ids,
                    "cooldown": cooldown,
                },
                "meaning": {
                    key: line[key]
                    for key in ("id", "actor", "aid", "text", "audio", "slot", "cid", "duration")
                    if line.get(key) not in (None, "", [])
                },
                "action": {
                    "action": "EnvTalkGreetingRuntimeSelection" if is_greeting else "EnvTalkRuntimeSelection",
                    "runtimeActivationStatus": "envTalkRuntimeExecutionNotObserved",
                },
                "owner": {
                    "proxyRows": proxy_rows,
                    "slotActorId": line.get("aid"),
                    "slotActorMatchStatus": slot_actor_match_status,
                    "speakerChannel": media_ref.get("speakerChannel") or audio_meta.get("speakerChannel"),
                },
                "selection": {
                    "slotId": slot_id,
                    "lineIndex": line_index,
                    "slotSelectionStatus": "runtimeSlotSelectionUnobserved",
                    "triggerDistanceStatus": "authoredTriggerDistanceNotRecoveredInConversationRow",
                },
                "mediaRefs": [media_ref] if media_ref else [],
                "evidence": {
                    "definition": (
                        "exactEnvTalkTableGreeting"
                        if is_greeting
                        else str(source.get("envTalkId") or env_id)
                    ),
                    "owner": owner_status,
                    "media": "playable" if media_ref.get("src") else "audioDialogMediaUnresolved",
                    "runtimeExecution": "envTalkRuntimeExecutionNotObserved",
                },
                "runtimeActivationStatus": "envTalkRuntimeExecutionNotObserved",
                "sourceRefs": [
                    normalize_posix(path.relative_to(webui_root)),
                    str(
                        debug.get("table")
                        or (source.get("table") if isinstance(source, dict) else "")
                        or ""
                    ),
                    str(source.get("envTalkId") or env_id),
                ],
            })
    return contexts

def _build_remote_common_trigger_contexts(
    export_root: Path,
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact RemoteCommonTable Event requests.

    ``audioId`` is the SFX/Wwise Event used by the automatic remote-communication
    surface.  Lifecycle ``startAudioEvent``/``endAudioEvent`` fields are
    published separately from auto-play rows. ``voiceId`` is a separate
    dialogue voice identity and is retained as such; it is never merged into
    the Event/media candidate.
    """

    event_by_id = {
        str(event.get("id") or "").casefold(): event
        for event in event_rows
        if isinstance(event, dict) and str(event.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    table_paths = [ExportLayout(export_root).game / "Table" / "RemoteCommonTable.json"]
    for table_path in table_paths:
        payload = load_json(table_path, {})
        if not isinstance(payload, dict):
            continue
        try:
            source_ref = normalize_posix(table_path.relative_to(export_root))
        except ValueError:
            source_ref = normalize_posix(table_path)
        for remote_id, row in sorted(payload.items(), key=lambda item: str(item[0])):
            if not isinstance(row, dict) or row.get("autoPlay") is not True:
                continue
            remote_id = str(remote_id or "").strip()
            if not remote_id:
                continue
            for line_index, line in enumerate(row.get("remoteCommSingleDataList") or []):
                if not isinstance(line, dict):
                    continue
                audio_id = str(line.get("audioId") or "").strip()
                if not audio_id:
                    continue
                single_id = str(line.get("singleId") or f"{remote_id}:{line_index + 1}").strip()
                identity = (remote_id.casefold(), single_id.casefold(), audio_id.casefold())
                if identity in seen:
                    continue
                seen.add(identity)
                event = event_by_id.get(audio_id.casefold(), {})
                media_refs = [
                    _trigger_media_ref(media, fallback_id=audio_id)
                    for media in event.get("media") or []
                    if isinstance(media, dict)
                ]
                media_refs = [media for media in media_refs if media]
                found_in_wwise = event.get("foundInWwise") is True
                if media_refs and any(media.get("src") for media in media_refs):
                    media_status = "directWwiseMediaCandidate"
                    media_evidence = "exactWwiseEventDirectSound"
                elif found_in_wwise:
                    media_status = "wwiseEventHasNoDecodedMedia"
                    media_evidence = "wwiseEventHasNoDecodedMediaLeaf"
                else:
                    media_status = "audioEventUnresolved"
                    media_evidence = "audioIdMissingFromCurrentWwiseIndex"
                event_hash = event.get("hash")
                if isinstance(event_hash, int):
                    event_hash &= 0xFFFFFFFF
                event_meaning = {
                    key: event.get(key)
                    for key in (
                        "category", "foundInWwise", "possibleMediaCount", "playRootCount",
                        "runtimeSelection", "mediaRelationTypes", "traversalStatus",
                    )
                    if event.get(key) not in (None, "", [])
                }
                if event_hash is not None:
                    event_meaning["eventHash"] = event_hash
                contexts.append({
                    "triggerId": ":".join(("remoteCommonAudio", remote_id, single_id, audio_id)),
                    "semanticKind": "remoteCommonAudio",
                    "triggerRole": "RemoteCommonTableAutoPlay",
                    "situation": {
                        "remoteCommonId": remote_id,
                        "singleId": single_id,
                        "index": line.get("index", line_index + 1),
                        "middleId": line.get("middleId"),
                        "autoPlay": True,
                        "autoPlayTime": line.get("autoPlayTime"),
                        "startAudioEvent": row.get("startAudioEvent"),
                        "endAudioEvent": row.get("endAudioEvent"),
                        "eventId": audio_id,
                        "eventHash": event_hash,
                    },
                    "meaning": {
                        "id": single_id,
                        "audio": audio_id,
                        "eventId": audio_id,
                        **event_meaning,
                    },
                    "action": {
                        "action": "RemoteCommonAutoPlay",
                        "triggerRole": "RemoteCommonTableAutoPlay",
                        "sourcePath": source_ref,
                        "runtimeActivationStatus": "remoteCommonAutoPlayExecutionNotObserved",
                    },
                    "owner": {
                        "remoteCommonId": remote_id,
                        "singleId": single_id,
                        "middleId": line.get("middleId"),
                        "actorList": line.get("actorList") or [],
                        "voiceId": line.get("voiceId"),
                        "voiceLinkStatus": "separateRemoteCommonVoiceId",
                    },
                    "selection": {
                        "autoPlay": True,
                        "autoPlayTime": line.get("autoPlayTime"),
                        "audioSelectionStatus": "exactRemoteCommonAudioId",
                        "mediaSelectionStatus": media_status,
                        "runtimeSelectionStatus": "remoteCommonAutoPlaySelectionUnobserved",
                    },
                    "mediaRefs": media_refs,
                    "evidence": {
                        "definition": "exactRemoteCommonTableAutoPlay",
                        "owner": "exactRemoteCommonSingleDataListRow",
                        "media": media_evidence,
                        "runtimeExecution": "remoteCommonAutoPlayExecutionNotObserved",
                        "voice": "voiceId remains a separate dialogue identity",
                    },
                    "runtimeActivationStatus": "remoteCommonAutoPlayExecutionNotObserved",
                    "sourceRefs": [
                        source_ref,
                        remote_id,
                        single_id,
                        audio_id,
                        str(line.get("voiceId") or ""),
                    ],
                })
    for event_id, lifecycle_rows in table_contexts.collect_remote_common_event_contexts(
        export_root
    ).items():
        for raw_context in lifecycle_rows:
            if (
                not isinstance(raw_context, dict)
                or raw_context.get("kind") != "remoteCommonLifecycleAudio"
            ):
                continue
            remote_id = str(raw_context.get("remoteCommonId") or "").strip()
            lifecycle_phase = str(raw_context.get("lifecyclePhase") or "").strip().lower()
            field = str(raw_context.get("field") or "").strip()
            event_name = str(raw_context.get("authoredEventId") or event_id).strip()
            if not remote_id or lifecycle_phase not in {"start", "end"} or not event_name:
                continue
            identity = (
                remote_id.casefold(), lifecycle_phase, event_name.casefold()
            )
            if identity in seen:
                continue
            seen.add(identity)
            event = event_by_id.get(event_name.casefold(), {})
            media_refs = [
                _trigger_media_ref(media, fallback_id=event_name)
                for media in event.get("media") or []
                if isinstance(media, dict)
            ]
            media_refs = [media for media in media_refs if media]
            found_in_wwise = event.get("foundInWwise") is True
            if media_refs and any(media.get("src") for media in media_refs):
                media_status = "directWwiseMediaCandidate"
                media_evidence = "exactWwiseEventDirectSound"
            elif found_in_wwise:
                media_status = "wwiseEventHasNoDecodedMedia"
                media_evidence = "wwiseEventHasNoDecodedMediaLeaf"
            else:
                media_status = "audioEventUnresolved"
                media_evidence = "audioEventMissingFromCurrentWwiseIndex"
            event_hash = event.get("hash")
            if isinstance(event_hash, int):
                event_hash &= 0xFFFFFFFF
            event_meaning = {
                key: event.get(key)
                for key in (
                    "category", "foundInWwise", "possibleMediaCount", "playRootCount",
                    "runtimeSelection", "mediaRelationTypes", "traversalStatus",
                )
                if event.get(key) not in (None, "", [])
            }
            if event_hash is not None:
                event_meaning["eventHash"] = event_hash
            trigger_role = str(
                raw_context.get("triggerRole")
                or f"RemoteCommonTable{lifecycle_phase.title()}AudioEvent"
            )
            binding_status = str(
                raw_context.get("triggerBindingStatus")
                or f"exactRemoteCommon{lifecycle_phase.title()}AudioEvent"
            )
            runtime_status = str(
                raw_context.get("runtimeActivationStatus")
                or "remoteCommonLifecycleExecutionNotObserved"
            )
            source_ref = str(raw_context.get("source") or raw_context.get("sourcePath") or "")
            contexts.append({
                "triggerId": ":".join((
                    "remoteCommonLifecycleAudio", remote_id, lifecycle_phase, event_name,
                )),
                "semanticKind": "remoteCommonLifecycleAudio",
                "triggerRole": trigger_role,
                "situation": {
                    "remoteCommonId": remote_id,
                    "lifecyclePhase": lifecycle_phase,
                    "field": field,
                    "autoPlay": raw_context.get("autoPlay") is True,
                    "eventId": event_name,
                    "eventHash": event_hash,
                },
                "meaning": {
                    "id": event_name,
                    "audio": event_name,
                    "eventId": event_name,
                    **event_meaning,
                },
                "action": {
                    "action": "RemoteCommonLifecycleAudio",
                    "triggerRole": trigger_role,
                    "sourcePath": source_ref,
                    "runtimeActivationStatus": runtime_status,
                },
                "owner": {
                    "remoteCommonId": remote_id,
                    "lifecyclePhase": lifecycle_phase,
                    "field": field,
                },
                "selection": {
                    "autoPlay": raw_context.get("autoPlay") is True,
                    "audioSelectionStatus": binding_status,
                    "mediaSelectionStatus": media_status,
                    "runtimeSelectionStatus": "remoteCommonLifecycleSelectionUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactRemoteCommonTableLifecycleAudioField",
                    "owner": "exactRemoteCommonLifecycleField",
                    "media": media_evidence,
                    "runtimeExecution": runtime_status,
                },
                "runtimeActivationStatus": runtime_status,
                "sourceRefs": [
                    value for value in (source_ref, remote_id, field, event_name)
                    if value
                ],
            })
    return contexts

def _build_dialog_timeline_trigger_contexts(
    webui_root: Path,
    language: str,
    media_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose authored DialogTrunk timeline voice placements.

    These rows are deliberately separate from Wwise Event/Timeline carrier
    rows.  A dialog line can have an exact serialized timeline schedule and a
    playable AudioDialog file without being a Wwise Event at all.
    """

    media_by_id = {
        str(row.get("id") or "").casefold(): row
        for row in media_rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    conv_root = webui_root / f"data/lang/{language.upper()}/conv"
    if not conv_root.is_dir():
        return contexts
    for path in sorted(conv_root.glob("dlg_*.json")):
        payload = load_json(path, {})
        if not isinstance(payload, dict) or payload.get("kind") != "dlg":
            continue
        dialog_key = str(payload.get("key") or path.stem).strip()
        payload_debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
        line_order = payload_debug.get("lineOrder") if isinstance(payload_debug.get("lineOrder"), dict) else {}
        timeline_sources = [
            source
            for source in line_order.get("sources") or []
            if isinstance(source, dict)
        ]
        source_refs = [
            str(value)
            for source in timeline_sources
            for value in (source.get("sourceKey"), source.get("file"))
            if value
        ]
        for line_index, line in enumerate(payload.get("lines") or []):
            if not isinstance(line, dict):
                continue
            line_debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            timing = line_debug.get("timelineTiming") if isinstance(line_debug.get("timelineTiming"), dict) else {}
            timeline_id = str(timing.get("timeline") or line.get("timeline") or "").strip()
            if not timeline_id:
                continue
            line_id = str(line.get("id") or f"{dialog_key}:{line_index}").strip()
            audio_id = str(line.get("audio") or "").strip()
            media = media_by_id.get(audio_id.casefold(), {})
            media_ref = _trigger_media_ref(media, fallback_id=audio_id)
            if not media_ref.get("src") and line.get("audioSrc"):
                media_ref["src"] = line.get("audioSrc")
            audio_meta = line.get("audioMeta") if isinstance(line.get("audioMeta"), dict) else {}
            for key in (
                "duration", "audioDialogPath", "speakerChannel", "audioCategory",
            ):
                if media_ref.get(key) in (None, "") and audio_meta.get(key) not in (None, ""):
                    media_ref[key] = audio_meta[key]
            line_source_refs = list(source_refs)
            line_source_refs.extend(
                value
                for value in (
                    normalize_posix(path.relative_to(webui_root)),
                    timeline_id,
                    str(line_debug.get("table") or ""),
                )
                if value
            )
            trigger_id = ":".join((
                "dialogTimeline",
                dialog_key,
                timeline_id,
                line_id,
            ))
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "dialogTimeline",
                "triggerRole": "DialogTimelineVoice",
                "situation": {
                    "dialogKey": dialog_key,
                    "timelineId": timeline_id,
                    "lineId": line_id,
                    "timelineStartSec": timing.get("start"),
                    "timelineDurationSec": timing.get("duration"),
                },
                "meaning": {
                    key: line[key]
                    for key in (
                        "id", "actor", "aid", "text", "audio", "slot", "cid", "duration",
                    )
                    if line.get(key) not in (None, "", [])
                },
                "action": {
                    "action": "DialogTimelineVoice",
                    "timelineId": timeline_id,
                    "runtimeActivationStatus": "dialogTimelineRuntimeExecutionNotObserved",
                },
                "owner": {
                    "dialogKey": dialog_key,
                    "timelineId": timeline_id,
                    "speakerActorId": line.get("aid"),
                    "speakerChannel": media_ref.get("speakerChannel") or audio_meta.get("speakerChannel"),
                },
                "selection": {
                    "lineIndex": line_index,
                    "timelineStartSec": timing.get("start"),
                    "timelineDurationSec": timing.get("duration"),
                    "lineScheduleStatus": "exactDialogTimelineTiming",
                    "mediaSelectionStatus": "audioDialogIdentityJoined",
                },
                "mediaRefs": [media_ref] if media_ref else [],
                "evidence": {
                    "definition": "exactDialogTimelineTiming",
                    "owner": "exactDialogTimelineSource",
                    "media": "playable" if media_ref.get("src") else "audioDialogMediaUnresolved",
                    "runtimeExecution": "dialogTimelineRuntimeExecutionNotObserved",
                },
                "runtimeActivationStatus": "dialogTimelineRuntimeExecutionNotObserved",
                "sourceRefs": sorted(set(line_source_refs)),
            })
    return contexts

def _build_dialog_lifecycle_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact AudioDialogCustomEventTable lifecycle hooks.

    The table binds a dialog id and a phase array slot to a uint32 Wwise Event
    id.  The event/media shards remain authoritative for Wwise traversal; this
    catalog only adds the authored dialog-state situation and the static
    ``AudioGameplayStatusSystem`` method shape.  It deliberately does not
    claim that the dialog state transition or the Wwise event was executed.
    """

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        found_in_wwise = event.get("foundInWwise") is True
        if found_in_wwise and media_refs:
            media_selection_status = "wwiseEventMediaCandidates"
            media_evidence = "wwiseEventMediaCandidate"
        elif found_in_wwise:
            media_selection_status = "wwiseEventHasNoDecodedMedia"
            media_evidence = "wwiseEventHasNoDecodedMediaLeaf"
        else:
            media_selection_status = "authoredEventUnresolved"
            media_evidence = "authoredEventMissingFromCurrentWwiseIndex"
        for occurrence_index, raw_context in enumerate(event.get("contexts") or []):
            if not isinstance(raw_context, dict):
                continue
            if raw_context.get("kind") != "tableEventHash":
                continue
            if raw_context.get("table") != "AudioDialogCustomEventTable":
                continue
            match = DIALOG_LIFECYCLE_PATH_RE.fullmatch(
                str(raw_context.get("path") or "")
            )
            if not match:
                continue
            phase = match.group("phase")
            phase_info = DIALOG_LIFECYCLE_PHASES[phase]
            dialog_id = match.group("dialogId")
            array_index = int(match.group("index"))
            event_hash = raw_context.get("eventHash")
            if not isinstance(event_hash, int):
                event_hash = event.get("hash")
            if isinstance(event_hash, int):
                event_hash &= 0xFFFFFFFF
            authored_value = raw_context.get("signedValue")
            event_key = event_id or (
                f"0x{event_hash:08x}" if isinstance(event_hash, int) else "unknown"
            )
            trigger_id = ":".join((
                "dialogLifecycle",
                dialog_id,
                phase,
                str(array_index),
                event_key,
            ))
            meaning = {
                key: event.get(key)
                for key in (
                    "id", "name", "hash", "category", "foundInWwise",
                    "possibleMediaCount", "playRootCount", "runtimeSelection",
                    "mediaRelationTypes", "traversalStatus", "unresolvedNodeCount",
                )
                if event.get(key) not in (None, "", [])
            }
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "dialogLifecycle",
                "triggerRole": phase_info["triggerRole"],
                "situation": {
                    "dialogId": dialog_id,
                    "lifecyclePhase": phase,
                    "arrayIndex": array_index,
                    "eventId": event_id,
                    "eventHash": event_hash,
                    "authoredSignedValue": authored_value,
                    "tablePath": raw_context.get("path"),
                },
                "meaning": meaning,
                "action": {
                    "action": "DialogLifecycleAudioEvent",
                    "lifecyclePhase": phase,
                    "runtimeMethod": phase_info["runtimeMethod"],
                    "runtimeMethodToken": phase_info["runtimeMethodToken"],
                    "runtimeActivationStatus": "dialogLifecycleRuntimeExecutionNotObserved",
                },
                "owner": {
                    "dialogId": dialog_id,
                    "sourceTable": "AudioDialogCustomEventTable",
                    "lifecycleField": phase,
                    "ownerStatus": "exactDialogIdAndLifecycleField",
                },
                "selection": {
                    "triggerBindingStatus": "exactAudioDialogCustomEventTable",
                    "mediaSelectionStatus": media_selection_status,
                    "runtimeDispatchStatus": "dialogLifecycleDispatchUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactAudioDialogCustomEventTable",
                    "owner": "exactAudioDialogCustomEventTableDialogIdAndPhase",
                    "media": media_evidence,
                    "runtimeExecution": "dialogLifecycleRuntimeExecutionNotObserved",
                    "requestEvidence": [
                        "exactAudioDialogCustomEventTableField",
                        "exactDialogLifecycleRuntimeMethodMetadata",
                    ],
                },
                "runtimeActivationStatus": "dialogLifecycleRuntimeExecutionNotObserved",
                "sourceRefs": [
                    value
                    for value in (
                        str(raw_context.get("source") or ""),
                        str(raw_context.get("path") or ""),
                        event_id,
                    )
                    if value
                ],
            })
    return contexts

def _build_timeline_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    event_rows = list(event_rows)
    contexts: list[dict[str, Any]] = []
    event_ids_with_serialized_carrier = {
        str(event.get("id") or "").strip()
        for event in event_rows
        if isinstance(event, dict)
        and str(event.get("id") or "").strip()
        and any(
            isinstance(context, dict)
            and context.get("kind") in {"levelSequenceAudio", "cutsceneTimeline"}
            and context.get("audioPlayableRuntimeContractId")
            for context in event.get("contexts") or []
        )
    }
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if not isinstance(context, dict) or context.get("kind") not in {
                "levelSequenceAudio",
                "cutsceneTimeline",
            }:
                continue
            context_kind = str(context.get("kind") or "")
            asset = str(context.get("timelineAssetName") or "")
            serialized_file = str(context.get("timelineAssetSerializedFile") or "")
            path_id = context.get("timelineAssetPathId")
            playable_path_id = context.get("audioPlayablePathId")
            story_key = str(context.get("storyKey") or "")
            trigger_id = ":".join((
                "timeline",
                event_id,
                context_kind,
                serialized_file or "unknown",
                str(path_id if path_id is not None else occurrence_index),
                str(playable_path_id if playable_path_id is not None else "unknown"),
            ))
            owner = {
                key: context[key]
                for key in (
                    "timelineAssetName", "timelineAssetSerializedFile", "timelineAssetPathId",
                    "timelineAssetSource", "timelineAssetSourceOffset", "timelineTrackName",
                    "timelineClipIndex", "timelineClipDisplayName", "timelineClipStartSec",
                    "timelineClipDurationSec", "timelineClipEndSec", "timelineClipInSec",
                    "timelineClipTimeScale", "timelineClipEaseInDurationSec",
                    "timelineClipEaseOutDurationSec", "timelineClipBlendInDurationSec",
                    "timelineClipBlendOutDurationSec", "timelineClipOptionIndex",
                    "timelineClipTimingEvidence", "timelineTrackRawJsonPath",
                    "timelineTrackSerializedFile", "timelineTrackPathId",
                    "timelineTrackSource", "timelineTrackSourceOffset", "audioPlayableType",
                    "audioPlayableRuntimeContractId",
                    "audioPlayableKeyStatus", "authoredEventName",
                    "authoredEventNameEvidence",
                    "audioPlayableSerializedFile", "audioPlayablePathId", "audioPlayableIsCue",
                    "audioPlayableStopEventAtClipEnd", "audioPlayableStopEventAtClipEndKey",
                    "audioPlayableFadeOutMs", "audioPlayableEnableSeek",
                    "audioPlayableUseBindingObject", "audioPlayableIs2D",
                    "audioPlayableStopOnDisable",
                    "audioMusicActionType", "audioMusicActionTypeLabel",
                    "audioMusicTriggerOnSkip", "audioMusicTriggerOnSkipLabel",
                    "audioPlayableControlEvidence", "audioPlayableRawJsonPath",
                    "playableDirectorCount",
                    "playableDirectorNames", "playableDirectorPathIds", "directorEvidence",
                    "storyKey", "evidence",
                )
                if context.get(key) not in (None, "", [])
            }
            if context_kind == "cutsceneTimeline" and not context.get(
                "audioPlayableRuntimeContractId"
            ):
                owner["runtimeCarrierStatus"] = (
                    "eventIdAlsoHasSerializedTimelineCarrier"
                    if event_id in event_ids_with_serialized_carrier
                    else "storyCutsceneAudioReferenceOnly"
                )
            source_refs = [
                str(value)
                for value in (
                    context.get("timelineAssetSource"),
                    context.get("timelineTrackSource"),
                )
                if value
            ]
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "timelineAudio",
                "triggerRole": context.get("triggerRole") or (
                    "CutsceneTimelineAudio"
                    if context_kind == "cutsceneTimeline"
                    else "TimelineAssetPlayback"
                ),
                "situation": {
                    "eventId": event_id,
                    "contextKind": context_kind,
                    "storyKey": story_key,
                    "timelineAssetName": asset,
                    "timelineClipDisplayName": context.get("timelineClipDisplayName"),
                    "timelineStartSec": context.get("timelineClipStartSec"),
                    "timelineDurationSec": context.get("timelineClipDurationSec"),
                    "timelineEndSec": context.get("timelineClipEndSec"),
                    "timelineParentNameStatus": context.get("timelineParentNameStatus"),
                    "levelSequenceId": context.get("levelSequenceId"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "authoredTimelineKeyStatus": (
                        "matchedCurrentWwiseEvent"
                        if event.get("foundInWwise")
                        else "authoredTimelineKeyNotInCurrentWwiseIndex"
                    ),
                    "mediaRelationTypes": event.get("mediaRelationTypes") or [],
                },
                "action": {
                    key: context[key]
                    for key in (
                        "triggerRole", "levelSequenceId", "levelScriptActionCount",
                        "levelScriptIds", "levelScriptSourcePaths", "levelSequenceFieldOffsets",
                    )
                    if context.get(key) not in (None, "", [])
                },
                "owner": owner,
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "confidence": context.get("confidence"),
                    "contextKind": context_kind,
                    "runtimeSelection": event.get("runtimeSelection"),
                    "mediaSelectionStatus": (
                        "wwiseSelectionUnobserved"
                        if event.get("foundInWwise")
                        else "authoredTimelineMediaUnresolved"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerEvidenceLevel")
                    or context.get("evidence")
                    or "inferred",
                    "owner": context.get("ownershipEvidenceLevel")
                    or (
                        "authoredTimelineOrLevelSequence"
                        if context_kind == "cutsceneTimeline"
                        else "exactSerializedTimelineCarrier"
                    ),
                    "media": (
                        "wwiseEventMediaCandidate"
                        if event.get("foundInWwise")
                        else "authoredTimelineKeyNotInCurrentWwiseIndex"
                    ),
                    "runtimeExecution": context.get("runtimeActivationStatus")
                        or (
                        "cutsceneTimelineRuntimeExecutionNotObserved"
                        if context_kind == "cutsceneTimeline"
                        else "audioEventRuntimePlaybackUnobserved"
                    ),
                    "requestEvidence": [
                        value
                        for value in (
                            (
                                "exactDialogAudioEventPlayableAudioIdScalar"
                                if context.get("audioPlayableKeyStatus")
                                == "exactDialogAudioEventPlayableAudioIdScalar"
                                else "exactAudioEventPlayableScalar"
                                if context.get("audioPlayableKeyStatus")
                                == "exactAudioEventPlayableScalar"
                                else "exactTimelineTrackDisplayName"
                            )
                            if context.get("audioPlayableKeyStatus")
                            or context.get("timelineTrackPathId") is not None
                            else (
                                "storyCutsceneAudioEventList"
                                if context_kind == "cutsceneTimeline"
                                else None
                            ),
                            (
                                "exactTimelineTrackPPtr"
                                if context.get("timelineTrackPathId") is not None
                                else None
                            ),
                            (
                                "exactTimelineParentPPtr"
                                if context.get("timelineAssetPathId") is not None
                                else None
                            ),
                            context.get("timelineClipTimingEvidence"),
                            context.get("authoredEventNameEvidence"),
                            context.get("audioPlayableControlEvidence"),
                        )
                        if value
                    ],
                },
                "runtimeActivationStatus": context.get(
                    "runtimeActivationStatus"
                ) or (
                    "cutsceneTimelineRuntimeExecutionNotObserved"
                    if context_kind == "cutsceneTimeline"
                    else "audioEventRuntimePlaybackUnobserved"
                ),
                "sourceRefs": source_refs,
            })
    return contexts

def _build_lua_post_event_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        for occurrence_index, raw_context in enumerate(event.get("contexts") or []):
            if not isinstance(raw_context, dict) or raw_context.get("kind") != "luaPostEvent":
                continue
            source = str(raw_context.get("source") or "")
            line = int(raw_context.get("line") or 0)
            contexts.append({
                "triggerId": f"luaPostEvent:{source}:{line}:{occurrence_index}:{event_id}",
                "semanticKind": "luaPostEvent",
                "triggerRole": "scriptedEventRequest",
                "situation": {
                    "eventId": event_id,
                    "eventHash": raw_context.get("eventHash"),
                    "luaSource": source,
                    "line": line,
                    "expression": raw_context.get("expression"),
                },
                "meaning": {
                    key: event.get(key)
                    for key in (
                        "id", "name", "hash", "category", "foundInWwise",
                        "possibleMediaCount", "runtimeSelection", "traversalStatus",
                    )
                    if event.get(key) not in (None, "", [])
                },
                "action": {
                    "action": "AudioAdapter.PostEvent",
                    "runtimeActivationStatus": "luaBranchExecutionNotObserved",
                },
                "owner": {
                    "luaSource": source,
                    "ownerStatus": "exactLuaFileAndLine",
                },
                "selection": {
                    "triggerBindingStatus": "exactDecryptedLuaPostEventLiteral",
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates"
                        if media_refs
                        else "noDecodedMediaCandidate"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactDecryptedLuaPostEventLiteral",
                    "owner": "exactLuaFileAndLine",
                    "media": (
                        "wwiseEventMediaCandidate"
                        if media_refs
                        else "noDecodedMediaLeaf"
                    ),
                    "runtimeExecution": "luaBranchExecutionNotObserved",
                },
                "runtimeActivationStatus": "luaBranchExecutionNotObserved",
                "sourceRefs": [value for value in (source, f"line:{line}", event_id) if value],
            })
    return contexts

def _build_levelscript_voice_trigger_contexts(
    media_rows: Iterable[dict[str, Any]],
    invocations: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join PlayVoice* ``_voId`` values to AudioDialog media identities.

    The native actions route this field through the voice player.  It is an
    AudioDialog path-stem selection id, not a Wwise Event name, so keep this
    evidence out of the authored Event universe.
    """

    media_by_id = {
        str(row.get("id") or "").strip().casefold(): row
        for row in media_rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    contexts: list[dict[str, Any]] = []
    for invocation_index, invocation in enumerate(invocations):
        if not isinstance(invocation, dict):
            continue
        voice_id = str(invocation.get("voiceId") or "").strip()
        if not voice_id:
            continue
        media = media_by_id.get(voice_id.casefold(), {})
        media_ref = _trigger_media_ref(media, fallback_id=voice_id)
        story_line_count = int(media.get("storyLineBindingCount") or 0)
        contexts.append({
            "triggerId": (
                f"levelScriptVoice:{invocation.get('levelScriptId') or 'unknown'}:"
                f"{invocation.get('recordStart') or 0}:{invocation_index}:{voice_id}"
            ),
            "semanticKind": "levelScriptVoice",
            "triggerRole": str(invocation.get("triggerRole") or "voice"),
            "situation": {
                "voiceId": voice_id,
                "voiceIdentityKind": "AudioDialogPathStem",
                "levelScriptId": invocation.get("levelScriptId"),
            },
            "meaning": {
                "audioCategory": media.get("audioCategory"),
                "audioDialogPath": media.get("audioDialogPath"),
                "storyLineBindingCount": story_line_count,
                "purposeKnowledgeStatus": media.get("purposeKnowledgeStatus"),
            },
            "action": _compact_trigger_action(invocation),
            "owner": {
                "levelScriptId": invocation.get("levelScriptId"),
                "sourcePath": invocation.get("sourcePath"),
                "ownerStatus": "exactLevelScriptActionRecord",
            },
            "selection": {
                "voiceSelectionStatus": (
                    "exactAudioDialogPathStem" if media else "audioDialogPathStemMissing"
                ),
                "mediaSelectionStatus": (
                    "exactDecodedAudioDialogMedia" if media_ref.get("src")
                    else "decodedMediaMissing"
                ),
                "wwiseEventStatus": "notApplicable",
            },
            "mediaRefs": [media_ref] if media_ref else [],
            "evidence": {
                "definition": "exactLevelScriptPlayVoiceUnionAndVoIdField",
                "owner": "exactLevelScriptActionRecord",
                "media": (
                    "exactAudioDialogPathStem" if media else "audioDialogPathStemMissing"
                ),
                "runtimeExecution": "levelScriptActionExecutionNotObserved",
            },
            "runtimeActivationStatus": "levelScriptActionExecutionNotObserved",
            "sourceRefs": [
                value for value in (
                    invocation.get("sourcePath"),
                    invocation.get("levelScriptId"),
                    voice_id,
                    media.get("audioDialogPath") if media else "",
                ) if value
            ],
        })
    return contexts

def _build_gameplay_config_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose owner-unresolved SkillData/BuffData audio references.

    The exact MemoryPack string boundary and source object identify an authored
    gameplay-config request. They do not identify its still-undecoded member,
    runtime actor, activation condition, or live Event execution.
    """

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            _trigger_media_ref(row)
            for row in event.get("media") or []
            if isinstance(row, dict)
        ]
        media_refs = [row for row in media_refs if row]
        for occurrence_index, raw_context in enumerate(event.get("contexts") or []):
            if (
                not isinstance(raw_context, dict)
                or raw_context.get("kind") != "gameplayConfigAudioReference"
            ):
                continue
            config_kind = str(raw_context.get("configKind") or "")
            config_id = str(raw_context.get("configId") or "")
            source_refs = [
                str(value)
                for value in raw_context.get("triggerSourcePaths") or []
                if str(value)
            ]
            contexts.append({
                "triggerId": (
                    f"gameplayConfigAudio:{config_kind}:{config_id}:"
                    f"{occurrence_index}:{event_id}"
                ),
                "semanticKind": "gameplayConfigAudioReference",
                "triggerRole": "authoredGameplayConfigAudioReference",
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "configKind": config_kind,
                    "configId": config_id,
                },
                "meaning": {
                    key: event.get(key)
                    for key in (
                        "id", "name", "hash", "category", "foundInWwise",
                        "playbackRole", "possibleMediaCount",
                    )
                    if event.get(key) not in (None, "", [])
                },
                "action": {
                    "runtimeActivationStatus": "configRuntimeExecutionNotObserved",
                },
                "owner": {
                    "configKind": config_kind,
                    "configId": config_id,
                    "ownerStatus": "gameplayOwnerUnresolved",
                },
                "selection": {
                    "triggerBindingStatus": "exactMemoryPackLengthPrefixedAudioEventString",
                    "memberFieldStatus": "undecodedConfigMember",
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates"
                        if media_refs
                        else "noDecodedMediaCandidate"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": "exactMemoryPackLengthPrefixedAudioEventString",
                    "owner": "exactGameplayConfigBinaryOwnerUnresolved",
                    "media": (
                        "wwiseEventMediaCandidate"
                        if media_refs
                        else "noDecodedMediaLeaf"
                    ),
                    "runtimeExecution": "configRuntimeExecutionNotObserved",
                },
                "runtimeActivationStatus": "configRuntimeExecutionNotObserved",
                "sourceRefs": source_refs,
            })
    return contexts

def _build_ability_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact SkillData response-trigger actions without inventing playback."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if (
                not isinstance(context, dict)
                or context.get("kind") != "abilityVoiceTriggerAction"
            ):
                continue
            contexts.append({
                "triggerId": (
                    f"abilityVoiceTrigger:{context.get('configId')}:"
                    f"{context.get('actionOffsetHex')}:{event_id}"
                ),
                "semanticKind": "abilityVoiceTriggerAction",
                "triggerRole": "authoredAbilityVoiceResponseTrigger",
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "ownerId": context.get("ownerId"),
                    "configId": context.get("configId"),
                    "triggerKey": context.get("triggerKey"),
                    "speakerType": context.get("speakerType"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                    "eventSelectionStatus": context.get("eventSelectionStatus"),
                },
                "action": {
                    "action": "VoiceTriggerAction",
                    "unionTag": context.get("actionUnionTag"),
                    "serializedMemberCount": context.get("serializedMemberCount"),
                    "canInterruptTimeMs": context.get("canInterruptTimeMs"),
                    "serverActionIndex": context.get("serverActionIndex"),
                    "runtimeRoute": context.get("runtimeRoute"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    "configKind": context.get("configKind"),
                    "configId": context.get("configId"),
                    "ownerId": context.get("ownerId"),
                    "sourcePath": context.get("sourcePath"),
                    "sourceSha256": context.get("sourceSha256"),
                    "actionOffset": context.get("actionOffset"),
                    "nativeMappingId": context.get("nativeMappingId"),
                },
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "eventSelectionStatus": context.get("eventSelectionStatus"),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs
                        else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": (
                        "responsiveRuntimeSelectionUnobserved"
                    ),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerRequestEvidence") or [],
                    "owner": "exactSkillDataAbilityActionRecord",
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": context.get("runtimeActivationStatus"),
                },
                "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                "sourceRefs": context.get("sourcePaths") or [],
            })
    return contexts

def _build_responsive_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose authored ResponsiveDialog choices as possible trigger rows."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row) for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") not in {
                "responsiveDialogVoice", "responsiveDialogToneVariant",
            }:
                continue
            is_tone_variant = context.get("kind") == "responsiveDialogToneVariant"
            source_path = str(context.get("responsiveSource") or context.get("source") or "")
            tone_source_path = str(context.get("toneSource") or "")
            source_layer = (
                "Persistent" if "/Persistent/" in source_path
                else "StreamingAssets" if "/StreamingAssets/" in source_path
                else "unknown"
            )
            tone_source_layer = (
                "Persistent" if "/Persistent/" in tone_source_path
                else "StreamingAssets" if "/StreamingAssets/" in tone_source_path
                else "none"
            )
            contexts.append({
                "triggerId": (
                    f"responsiveVoice:{source_layer}:{tone_source_layer}:"
                    f"{context.get('sentenceType')}:"
                    f"{context.get('speakerId')}:{context.get('triggerKey')}:"
                    f"{context.get('responseIndex')}:"
                    f"{context.get('variantIndex') if is_tone_variant else 'base'}:{event_id}"
                ),
                "semanticKind": str(context.get("kind")),
                "triggerRole": (
                    "authoredResponsiveToneVariantCandidate"
                    if is_tone_variant else "authoredResponsiveVoiceCandidate"
                ),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "sentenceType": context.get("sentenceType"),
                    "speakerId": context.get("speakerId"),
                    "triggerKey": context.get("triggerKey"),
                    "triggerTypeId": context.get("triggerTypeId"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                    "responseWeight": context.get("responseWeight"),
                    "baseVoiceId": context.get("baseVoiceId"),
                    "variantVoiceId": context.get("variantVoiceId"),
                    "variantIndex": context.get("variantIndex"),
                },
                "action": {
                    "responseIndex": context.get("responseIndex"),
                    "voiceId": context.get("voiceId"),
                    "runtimeRoute": context.get("runtimeRoute"),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                    "aiBarkRequests": context.get("aiBarkRequests") or [],
                    "aiBarkRuntimeStatus": context.get("aiBarkRuntimeStatus"),
                    "enemyTriggerVoiceAction": context.get("enemyTriggerVoiceAction"),
                    "enemyTriggerVoiceActionStatus": context.get(
                        "enemyTriggerVoiceActionStatus"
                    ),
                },
                "owner": {
                    "table": "ResponsiveDialog",
                    "source": source_path,
                    "sourcePath": source_path,
                    "sourceLayer": source_layer,
                    "toneSource": tone_source_path,
                    "toneSourceLayer": tone_source_layer,
                    "speakerId": context.get("speakerId"),
                    "aiBarkSources": sorted({
                        str(source)
                        for request in context.get("aiBarkRequests") or []
                        if isinstance(request, dict)
                        for source in request.get("sources") or []
                        if str(source)
                    }),
                },
                "selection": {
                    "triggerBindingStatus": (
                        "exactResponsiveDialogResponseVoiceIdComposedWithExactAudioVoToneVariantVoiceId"
                        if is_tone_variant else "exactResponsiveDialogResponseVoiceId"
                    ),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "aiBark": (
                        "exactAIBarkRowTriggerKeyAndFingerprintLockedNativeDispatch"
                        if context.get("aiBarkRequests") else None
                    ),
                    "enemyTriggerVoiceAction": (
                        "exactCurrentBinaryVoiceTypeToTriggerKeyDictionaryAndResponseOnEntityCall"
                        if context.get("enemyTriggerVoiceAction") else None
                    ),
                    "owner": (
                        "exactResponsiveDialogSpeakerTriggerAndAudioVoToneVariantComposition"
                        if is_tone_variant
                        else "exactResponsiveDialogSpeakerTriggerResponseMembership"
                    ),
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": "liveResponseSelectionUnobserved",
                },
                "runtimeActivationStatus": "liveResponseSelectionUnobserved",
                "sourceRefs": [value for value in (source_path, tone_source_path) if value],
            })
    return contexts

def _build_native_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row) for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "nativeVoiceTriggerCallsite":
                continue
            contexts.append({
                "triggerId": f"nativeVoiceTrigger:{context.get('triggerKey')}:{event_id}",
                "semanticKind": "nativeVoiceTriggerCallsite",
                "triggerRole": context.get("triggerRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "triggerKey": context.get("triggerKey"),
                    "targetBinding": context.get("targetBinding"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "runtimeRoute": context.get("runtimeRoute"),
                    "literalLoadVa": context.get("literalLoadVa"),
                    "playbackCall": context.get("playbackCall"),
                    "playbackInvocationVa": context.get("playbackInvocationVa"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    "methodIndex": context.get("methodIndex"),
                    "methodVa": context.get("methodVa"),
                    "nativeMappingId": context.get("nativeMappingId"),
                },
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerRequestEvidence") or [],
                    "owner": "exactCurrentBuildNativeVoiceResponseCallsite",
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": context.get("runtimeActivationStatus"),
                },
                "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                "sourceRefs": [
                    value for value in (
                        context.get("methodVa"), context.get("literalLoadVa"),
                        context.get("playbackInvocationVa"),
                    ) if value
                ],
            })
    return contexts

def _build_animation_voice_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row) for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "animationVoiceTrigger":
                continue
            contexts.append({
                "triggerId": (
                    f"animationVoice:{context.get('sourceLayer')}:"
                    f"{context.get('clip')}:{context.get('eventIndex')}:{event_id}"
                ),
                "semanticKind": "animationVoiceTrigger",
                "triggerRole": "authoredAnimationVoiceResponseTrigger",
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": context.get("ownerId"),
                    "triggerKey": context.get("triggerKey"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                },
                "meaning": {
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                    "intParameter": context.get("intParameter"),
                },
                "action": {
                    "function": context.get("function"),
                    "eventIndex": context.get("eventIndex"),
                    "time": context.get("time"),
                    "floatParameter": context.get("floatParameter"),
                    "intParameter": context.get("intParameter"),
                    "runtimeRoute": context.get("runtimeRoute"),
                    "playbackCall": context.get("playbackCall"),
                    "playbackCallVa": context.get("playbackCallVa"),
                    "playbackInvocationVa": context.get("playbackInvocationVa"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": context.get("ownerId"),
                    "ownerCandidateIds": context.get("ownerCandidateIds") or [],
                    "animationOwnerCandidateCount": context.get("animationOwnerCandidateCount"),
                    "animationOwnershipScope": context.get("animationOwnershipScope"),
                    "identityToken": context.get("identityToken"),
                    "clip": context.get("clip"),
                    "sourcePath": context.get("clipSource"),
                    "sourceLayer": context.get("sourceLayer"),
                    "methodIndex": context.get("methodIndex"),
                    "methodVa": context.get("methodVa"),
                    "additionalMethodIndex": context.get("additionalMethodIndex"),
                    "additionalMethodVa": context.get("additionalMethodVa"),
                    "nativeMappingId": context.get("nativeMappingId"),
                },
                "selection": {
                    "triggerBindingStatus": context.get("triggerBindingStatus"),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": context.get("runtimeSelectionStatus"),
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("triggerRequestEvidence") or [],
                    "owner": "exactAnimationClipAndAudioDialogOwnerIdentity",
                    "media": "exactCurrentAudioDialogWwiseEventIdentity",
                    "runtimeExecution": context.get("runtimeActivationStatus"),
                },
                "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                "sourceRefs": [
                    value for value in (
                        context.get("clipSource"), context.get("methodVa"),
                        context.get("playbackInvocationVa"),
                    ) if value
                ],
            })
    return contexts

def _build_interactive_property_audio_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact InteractiveData audio-key placements without runtime guesses."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if (
                not isinstance(context, dict)
                or context.get("kind") not in {
                    "interactiveComponentPropertyAudio",
                    "interactivePropertyMapAudio",
                    "interactiveTemplateConfigAudio",
                    "interactiveTemplateActionAudio",
                    "interactiveEmbeddedActionAudio",
                }
            ):
                continue
            is_action = context.get("kind") in {
                "interactiveTemplateActionAudio",
                "interactiveEmbeddedActionAudio",
            }
            owner_id = str(context.get("ownerId") or "unknown")
            property_key = str(
                context.get("audioPropertyKey")
                or context.get("audioSourceField")
                or "unknown"
            )
            contexts.append({
                "triggerId": (
                    f"{'interactiveActionAudio' if is_action else 'interactivePropertyAudio'}:"
                    f"{owner_id}:{property_key}:"
                    f"{occurrence_index}:{event_id}"
                ),
                "semanticKind": str(context.get("kind")),
                "triggerRole": (
                    "authoredInteractiveActionAudioRequest"
                    if is_action
                    else "authoredInteractiveAudioProperty"
                ),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "contextKind": "InteractiveData",
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": owner_id,
                    "audioPropertyKey": property_key,
                    "audioAction": context.get("audioAction"),
                    "audioActionRole": context.get("audioActionRole"),
                    "actionLocalId": context.get("actionLocalId"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "action": context.get("audioAction"),
                    "role": context.get("audioActionRole"),
                    "sourceField": context.get("audioSourceField"),
                    "actionMapRole": context.get("actionMapRole"),
                    "localId": context.get("actionLocalId"),
                    "uid": context.get("actionUid"),
                    "nextId": context.get("actionNextId"),
                    "unionTag": context.get("actionUnionTag"),
                    "stopOnRelease": context.get("stopOnRelease"),
                    "targetBindingKind": context.get("targetBindingKind"),
                    "targetParamSource": context.get("targetParamSource"),
                    "targetParameterKind": context.get("targetParameterKind"),
                    "runtimeActivationStatus": (
                        "runtimeActionActivationUnobserved"
                        if is_action
                        else "runtimePropertyConsumerUnresolved"
                    ),
                },
                "owner": {
                    "ownerId": owner_id,
                    "componentType": context.get("componentType"),
                    "componentTag": context.get("componentTag"),
                    "componentResolutionStatus": context.get("componentResolutionStatus"),
                    "interactiveTemplatePath": context.get("interactiveTemplatePath"),
                    "templateAssociationStatus": context.get("templateAssociationStatus"),
                    "propertyMapOffset": context.get("propertyMapOffset"),
                    "audioPropertyKey": property_key,
                    "sourceOffset": context.get("sourceOffset"),
                    "actionRecordOffset": context.get("actionRecordOffset"),
                    "actionPayloadOffset": context.get("actionPayloadOffset"),
                    "actionMapOffset": context.get("actionMapOffset"),
                },
                "selection": {
                    "triggerBindingStatus": str(context.get("evidence")),
                    "memberFieldStatus": (
                        "exactActionListAndTypedAudioActionEventField"
                        if is_action
                        else "exactDynamicPropertyKeyAndEventValue"
                    ),
                    "mediaSelectionStatus": (
                        "wwiseEventMediaCandidates" if media_refs else "noDecodedMediaCandidate"
                    ),
                    "runtimeSelectionStatus": "runtimeEventPostingNotObserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": (
                        "exactInteractiveDataTemplateActionMapMembership"
                        if is_action
                        else "exactInteractiveDataTemplateAndComponentProperty"
                    ),
                    "media": "wwiseEventMediaCandidate" if media_refs else "noDecodedMediaLeaf",
                    "runtimeExecution": (
                        "runtimeActionActivationTargetResolutionAndEventPostingNotObserved"
                        if is_action
                        else "runtimePropertyConsumerAndEventPostingNotObserved"
                    ),
                },
                "runtimeActivationStatus": (
                    "runtimeActionActivationUnobserved"
                    if is_action
                    else "runtimePropertyConsumerUnresolved"
                ),
                "sourceRefs": [
                    value for value in context.get("sourcePaths") or []
                    if isinstance(value, str) and value
                ],
            })
    return contexts

def _build_mono_behaviour_audio_id_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            )
            if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if not isinstance(context, dict) or context.get("kind") != "monoBehaviourAudioIdField":
                continue
            serialized_file = str(context.get("serializedFile") or "unknown")
            path_id = context.get("pathId")
            field_path = str(context.get("serializedFieldPath") or "")
            trigger_id = ":".join((
                "mono-behaviour-audio-id",
                event_id,
                str(context.get("sourceRoot") or "unknown"),
                serialized_file,
                str(path_id if path_id is not None else occurrence_index),
                hashlib.sha1(field_path.encode("utf-8")).hexdigest()[:12],
            ))
            contexts.append({
                "triggerId": trigger_id,
                "semanticKind": "monoBehaviourAudioIdField",
                "triggerRole": context.get("authoredFieldRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "componentName": context.get("componentName"),
                    "componentType": context.get("componentType") or context.get("scriptFullName"),
                    "componentLayout": context.get("componentLayout"),
                    "authoredFieldRole": context.get("authoredFieldRole"),
                    "authoredFieldNameRaw": context.get("authoredFieldNameRaw"),
                    "gameObjectName": context.get("gameObjectName"),
                    "serializedFieldPath": field_path,
                    "serializedFieldPathRaw": context.get("serializedFieldPathRaw") or field_path,
                    "serializedFieldPathStatus": context.get("serializedFieldPathStatus"),
                    "hierarchyPath": context.get("hierarchyPath") or [],
                    "worldPosition": context.get("worldPosition"),
                    "worldPositionStatus": context.get("worldPositionStatus"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "triggerRole": context.get("authoredFieldRole"),
                    "runtimeActivationStatus": context.get("runtimeActivationStatus"),
                },
                "owner": {
                    key: context[key]
                    for key in (
                        "sourceRoot", "serializedFile", "sourceAssetFile", "sourceOffset",
                        "pathId", "componentName", "scriptPathId", "scriptFullName",
                        "componentType", "componentLayout", "authoredFieldNameRaw",
                        "serializedFieldPathRaw", "serializedFieldPathStatus", "serializedFieldName",
                        "gameObjectName", "worldPositionStatus", "managedReferenceClass",
                        "managedReferenceNamespace", "managedReferenceAssembly",
                        "managedReferenceLayout", "managedReferencePayloadLength",
                        "managedReferenceDecodeStatus",
                    )
                    if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactSerializedAudioIdField",
                    "mediaSelectionStatus": "wwiseSelectionUnobserved",
                    "runtimeSelectionStatus": "componentStateOrCallbackExecutionNotObserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactSerializedMonoBehaviourAndSceneContext",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "monoBehaviourComponentExecutionNotObserved",
                    "requestEvidence": context.get("triggerRequestEvidence") or [],
                },
                "runtimeActivationStatus": "monoBehaviourComponentExecutionNotObserved",
                "sourceRefs": [
                    value for value in (
                        context.get("objectIndexSource"),
                        context.get("sourceAssetFile"),
                        field_path,
                    ) if isinstance(value, str) and value
                ],
            })
    return contexts

def _build_audio_global_config_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact global lifecycle AudioId placements in the trigger catalog."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for occurrence_index, context in enumerate(event.get("contexts") or []):
            if not isinstance(context, dict) or context.get("kind") != "audioGlobalConfigEventHash":
                continue
            field_path = str(context.get("path") or "")
            contexts.append({
                "triggerId": ":".join((
                    "audio-global-config",
                    event_id,
                    str(context.get("sourceRoot") or "unknown"),
                    str(context.get("pathId") or occurrence_index),
                    hashlib.sha1(field_path.encode("utf-8")).hexdigest()[:12],
                )),
                "semanticKind": "audioGlobalConfigEventHash",
                "triggerRole": context.get("semanticRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "serializedFieldPath": field_path,
                    "stateDirection": context.get("stateDirection"),
                    "audioStateMask": context.get("audioStateMask"),
                    "ownerKind": context.get("ownerKind"),
                    "ownerId": context.get("ownerId"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "triggerRole": context.get("semanticRole"),
                    "runtimeActivationStatus": "runtimeLifecycleConditionRequired",
                },
                "owner": {
                    key: context[key]
                    for key in ("sourceRoot", "serializedFile", "pathId", "table")
                    if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactSerializedGlobalAudioPolicyAudioId",
                    "mediaSelectionStatus": "wwiseSelectionUnobserved",
                    "runtimeSelectionStatus": "runtimeLifecycleConditionRequired",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactSerializedAudioGlobalConfigField",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "runtimeLifecycleConditionRequired",
                    "requestEvidence": context.get("triggerRequestEvidence") or [],
                },
                "runtimeActivationStatus": "runtimeLifecycleConditionRequired",
                "sourceRefs": [
                    value for value in (context.get("source"), field_path)
                    if isinstance(value, str) and value
                ],
            })
    return contexts

def _build_managed_literal_callsite_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose fingerprint-locked managed native playback callsites."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "binaryManagedLiteralCallsite":
                continue
            contexts.append({
                "triggerId": ":".join((
                    "managed-audio-callsite",
                    event_id,
                    str(context.get("methodIndex") or "unknown"),
                    str(context.get("playbackCallVa") or "unknown"),
                )),
                "semanticKind": "binaryManagedLiteralCallsite",
                "triggerRole": context.get("triggerRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                    "triggerRole": context.get("triggerRole"),
                    "targetBinding": context.get("targetBinding"),
                    "branchCondition": context.get("branchCondition"),
                    "selectorType": context.get("selectorType"),
                    "selectorMethod": context.get("selectorMethod"),
                    "selectorMethodIndex": context.get("selectorMethodIndex"),
                    "selectorMethodVa": context.get("selectorMethodVa"),
                    "selectorCallVa": context.get("selectorCallVa"),
                    "selectorLoadVa": context.get("selectorLoadVa"),
                    "selectorField": context.get("selectorField"),
                    "selectorFieldOffset": context.get("selectorFieldOffset"),
                    "additionalConsumerMethod": context.get("additionalConsumerMethod"),
                    "additionalMethodVa": context.get("additionalMethodVa"),
                    "additionalSelectorLoadVa": context.get("additionalSelectorLoadVa"),
                    "additionalSelectorCallVa": context.get("additionalSelectorCallVa"),
                    "additionalPlaybackCallVa": context.get("additionalPlaybackCallVa"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "playbackCall": context.get("playbackCall"),
                    "playbackCallVa": context.get("playbackCallVa"),
                    "playbackParameter": context.get("playbackParameter"),
                    "literalArgumentRegister": context.get("literalArgumentRegister"),
                    "literalArgumentInstruction": context.get("literalArgumentInstruction"),
                    "playbackHashCall": context.get("playbackHashCall"),
                    "playbackHashCallVa": context.get("playbackHashCallVa"),
                    "playbackHashInvocationVa": context.get("playbackHashInvocationVa"),
                    "playbackSink": context.get("playbackSink"),
                    "playbackSinkVa": context.get("playbackSinkVa"),
                    "playbackSinkInvocationVa": context.get("playbackSinkInvocationVa"),
                    "playbackInvocationVa": context.get("playbackInvocationVa"),
                    "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                },
                "owner": {
                    key: context[key]
                    for key in (
                        "consumerType", "consumerMethod", "methodIndex", "methodVa",
                        "literalLoadVa", "metadataSha256", "gameAssemblySha256",
                    ) if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactCurrentBuildManagedNativePlaybackCallsite",
                    "mediaSelectionStatus": "wwiseEventMediaCandidates",
                    "runtimeSelectionStatus": "runtimeBranchExecutionUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactManagedMethodAndLiteralHandleXref",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "runtimeBranchExecutionUnobserved",
                },
                "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                "sourceRefs": [
                    value for value in (
                        context.get("source"), context.get("methodVa"),
                        context.get("selectorMethodVa"), context.get("selectorLoadVa"),
                        context.get("selectorCallVa"), context.get("additionalMethodVa"),
                        context.get("additionalSelectorLoadVa"), context.get("additionalSelectorCallVa"),
                        context.get("literalLoadVa"), context.get("playbackCallVa"),
                        context.get("additionalPlaybackCallVa"),
                        context.get("playbackInvocationVa"), context.get("playbackSinkInvocationVa"),
                    ) if isinstance(value, str) and value
                ],
            })
    return contexts

def _build_native_custom_state_trigger_contexts(
    event_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Expose exact native custom-state calls joined to authored Events."""

    contexts: list[dict[str, Any]] = []
    for event in event_rows:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        media_refs = [
            ref for ref in (
                _trigger_media_ref(row)
                for row in event.get("media") or []
                if isinstance(row, dict)
            ) if ref
        ]
        for context in event.get("contexts") or []:
            if not isinstance(context, dict) or context.get("kind") != "nativeCustomStateCallsite":
                continue
            callsite = str(context.get("callsiteVa") or "unknown")
            contexts.append({
                "triggerId": ":".join((
                    "native-custom-state",
                    event_id,
                    str(context.get("methodIndex") or "unknown"),
                    callsite,
                )),
                "semanticKind": "nativeCustomStateCallsite",
                "triggerRole": context.get("triggerRole"),
                "situation": {
                    "eventId": event_id,
                    "eventHash": event.get("hash"),
                    "consumerType": context.get("consumerType"),
                    "consumerMethod": context.get("consumerMethod"),
                    "triggerRole": context.get("triggerRole"),
                    "customStateName": context.get("customStateName"),
                    "switchMethod": context.get("switchMethod"),
                    "switchMethodVa": context.get("switchMethodVa"),
                    "branchCondition": context.get("branchCondition"),
                },
                "meaning": {
                    "eventId": event_id,
                    "category": event.get("category"),
                    "foundInWwise": bool(event.get("foundInWwise")),
                    "playbackRole": event.get("playbackRole"),
                    "possibleMediaCount": event.get("possibleMediaCount"),
                },
                "action": {
                    "switchMethod": context.get("switchMethod"),
                    "switchMethodVa": context.get("switchMethodVa"),
                    "customStateName": context.get("customStateName"),
                    "staticArgumentVa": context.get("staticArgumentVa"),
                    "metadataUsageWord": context.get("metadataUsageWord"),
                    "metadataStringLiteralIndex": context.get("metadataStringLiteralIndex"),
                    "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                },
                "owner": {
                    key: context[key]
                    for key in (
                        "consumerType", "consumerMethod", "methodIndex", "methodVa",
                        "callsiteVa", "staticArgumentVa", "metadataSha256", "gameAssemblySha256",
                    ) if context.get(key) not in (None, "", [])
                },
                "selection": {
                    "triggerBindingStatus": "exactCurrentBuildNativeCustomStateCallsite",
                    "mediaSelectionStatus": "wwiseEventMediaCandidates",
                    "runtimeSelectionStatus": "runtimeBranchExecutionUnobserved",
                },
                "mediaRefs": media_refs,
                "evidence": {
                    "definition": context.get("evidence"),
                    "owner": "exactNativeSwitchAudioCustomStateCallsiteAndAuthoredInteractiveConfig",
                    "media": "wwiseEventMediaCandidate",
                    "runtimeExecution": "runtimeBranchExecutionUnobserved",
                },
                "runtimeActivationStatus": "runtimeBranchExecutionUnobserved",
                "sourceRefs": [
                    value for value in (
                        context.get("source"), context.get("methodVa"),
                        context.get("callsiteVa"), context.get("staticArgumentVa"),
                        context.get("switchMethodVa"),
                    ) if isinstance(value, str) and value
                ],
            })
    return contexts

def build_trigger_context_catalog(
    event_rows: Iterable[dict[str, Any]],
    media_rows: Iterable[dict[str, Any]],
    webui_root: Path,
    language: str,
    export_root: Path | None = None,
    levelscript_semantics: dict[str, Any] | None = None,
    mono_behaviour_audio_id_contexts: dict[str, list[dict[str, Any]]] | None = None,
    model_view_semantics: dict[str, Any] | None = None,
    native_context: native_evidence.NativeAudioEvidence | None = None,
) -> dict[str, Any]:
    """Build one navigable trigger -> situation -> media surface.

    This is intentionally a reference layer over the existing event/media
    shards. It does not merge authored ownership with runtime execution and it
    does not invent a trigger for a media file that has only a table identity.
    """

    event_rows = list(event_rows)
    media_rows = list(media_rows)
    line_meanings = _conversation_line_meanings(
        webui_root,
        language,
        kinds=frozenset({"radio"}),
    )
    mono_event_rows: list[dict[str, Any]] = []
    events_by_hash = {
        int(event["hash"]) & 0xFFFFFFFF: event
        for event in event_rows
        if isinstance(event, dict) and isinstance(event.get("hash"), int)
    }
    for context_key, rows in (mono_behaviour_audio_id_contexts or {}).items():
        match = re.fullmatch(r"#0x([0-9a-fA-F]{8})", str(context_key))
        if not match:
            continue
        event = events_by_hash.get(int(match.group(1), 16))
        if not isinstance(event, dict):
            continue
        mono_event_rows.append({**event, "contexts": list(rows or [])})
    remote_common_contexts = (
        _build_remote_common_trigger_contexts(export_root, event_rows)
        if export_root is not None
        else []
    )
    grouped = {
        "radio": _build_radio_trigger_contexts(media_rows, line_meanings),
        "envTalk": _build_envtalk_trigger_contexts(webui_root, language, media_rows),
        "remoteCommonAudio": (
            [
                row for row in remote_common_contexts
                if row.get("semanticKind") == "remoteCommonAudio"
            ]
        ),
        "remoteCommonLifecycleAudio": (
            [
                row for row in remote_common_contexts
                if row.get("semanticKind") == "remoteCommonLifecycleAudio"
            ]
        ),
        "dialogTimeline": _build_dialog_timeline_trigger_contexts(
            webui_root,
            language,
            media_rows,
        ),
        "dialogLifecycle": _build_dialog_lifecycle_trigger_contexts(event_rows),
        "levelScriptVoice": _build_levelscript_voice_trigger_contexts(
            media_rows,
            (levelscript_semantics or {}).get("voiceInvocations") or [],
        ),
        "timelineAudio": _build_timeline_trigger_contexts(event_rows),
        "luaPostEvent": _build_lua_post_event_trigger_contexts(event_rows),
        "gameplayConfigAudio": _build_gameplay_config_trigger_contexts(event_rows),
        "abilityVoiceTrigger": _build_ability_voice_trigger_contexts(event_rows),
        "responsiveVoiceTrigger": _build_responsive_voice_trigger_contexts(event_rows),
        "nativeVoiceTrigger": _build_native_voice_trigger_contexts(event_rows),
        "animationVoiceTrigger": _build_animation_voice_trigger_contexts(event_rows),
        "interactivePropertyAudio": _build_interactive_property_audio_trigger_contexts(event_rows),
        "managedLiteralCallsite": _build_managed_literal_callsite_trigger_contexts(event_rows),
        "nativeCustomStateCallsite": _build_native_custom_state_trigger_contexts(event_rows),
        "monoBehaviourAudioId": _build_mono_behaviour_audio_id_trigger_contexts(
            mono_event_rows or event_rows
        ),
        "audioGlobalConfig": _build_audio_global_config_trigger_contexts(event_rows),
        "modelViewStateAudio": model_view_projection.project_model_view_state_audio_trigger_contexts(
            model_view_semantics,
            event_rows,
            native_context=native_context,
        ),
    }
    contexts = [row for rows in grouped.values() for row in rows]
    contexts.sort(key=lambda row: (str(row.get("semanticKind") or ""), str(row.get("triggerId") or "")))
    counts = Counter(str(row.get("semanticKind") or "unknown") for row in contexts)
    coverage = {
        "radio": {
            "source": "media.radioTriggerContexts",
            "conversationLineIds": len(line_meanings),
            "storedTriggerContextRows": len(grouped["radio"]),
            "unresolvedRowsRemainIn": "triggerCatalog.levelScriptRadio.unresolvedRadioLines",
        },
        "envTalk": {
            "source": "conv/env_*.json lines",
            "storedTriggerContextRows": len(grouped["envTalk"]),
            "greetingRows": sum(
                str(row.get("semanticKind") or "") == "envTalkGreeting"
                for row in grouped["envTalk"]
                if isinstance(row, dict)
            ),
        },
        "remoteCommonAudio": {
            "source": "RemoteCommonTable.remoteCommSingleDataList[*].audioId where autoPlay=true",
            "storedTriggerContextRows": len(grouped["remoteCommonAudio"]),
            "rowsWithPlayableMedia": sum(
                any(
                    isinstance(media_ref, dict) and media_ref.get("src")
                    for media_ref in row.get("mediaRefs") or []
                )
                for row in grouped["remoteCommonAudio"]
                if isinstance(row, dict)
            ),
            "voiceIdKeptSeparate": True,
        },
        "remoteCommonLifecycleAudio": {
            "source": (
                "RemoteCommonTable.startAudioEvent/endAudioEvent with fail-closed "
                "Persistent-over-Streaming row overlay"
            ),
            "storedTriggerContextRows": len(grouped["remoteCommonLifecycleAudio"]),
            "rowsWithPlayableMedia": sum(
                any(
                    isinstance(media_ref, dict) and media_ref.get("src")
                    for media_ref in row.get("mediaRefs") or []
                )
                for row in grouped["remoteCommonLifecycleAudio"]
                if isinstance(row, dict)
            ),
            "runtimeExecutionObserved": 0,
        },
        "luaPostEvent": {
            "source": "decrypted VFS Lua AudioAdapter/AudioManager.PostEvent string literals",
            "storedTriggerContextRows": len(grouped["luaPostEvent"]),
            "runtimeExecutionObserved": 0,
        },
        "gameplayConfigAudio": {
            "source": "exact MemoryPack length-prefixed au_* strings in SkillData/BuffData",
            "storedTriggerContextRows": len(grouped["gameplayConfigAudio"]),
            "runtimeExecutionObserved": 0,
            "ownerStatus": "gameplayOwnerUnresolved",
        },
        "abilityVoiceTrigger": {
            "source": "exact SkillData AbilityActionData VoiceTriggerAction records",
            "storedTriggerContextRows": len(grouped["abilityVoiceTrigger"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "responsiveRuntimeSelectionUnobserved",
        },
        "nativeVoiceTrigger": {
            "source": "fingerprint-locked current metadata literal handles and GameAssembly voice response callsites",
            "storedTriggerContextRows": len(grouped["nativeVoiceTrigger"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "speakerCooldownProbabilityToneAndLiveChoiceUnobserved",
        },
        "responsiveVoiceTrigger": {
            "source": "merged StreamingAssets/Persistent ResponsiveDialog response arrays plus exact AudioVoTone compositions",
            "storedTriggerContextRows": len(grouped["responsiveVoiceTrigger"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "probabilityCooldownBandLimitToneAndLiveChoiceUnobserved",
        },
        "monoBehaviourAudioId": {
            "source": "AnimeStudio MonoBehaviour object-index exact AudioId scalar paths",
            "storedTriggerContextRows": len(grouped["monoBehaviourAudioId"]),
            "authoredFieldRoleCounts": dict(sorted(Counter(
                str(row.get("triggerRole") or managed_literals.MONO_BEHAVIOUR_AUDIO_GENERIC_ROLE)
                for row in grouped["monoBehaviourAudioId"]
                if isinstance(row, dict)
            ).items())),
            "componentLayoutCounts": dict(sorted(Counter(
                str((row.get("situation") or {}).get("componentLayout") or "unknown")
                for row in grouped["monoBehaviourAudioId"]
                if isinstance(row, dict)
            ).items())),
            "rowsWithExactPlacement": sum(
                bool((row.get("situation") or {}).get("worldPosition"))
                and (row.get("situation") or {}).get("worldPositionStatus") == "exact_transform_hierarchy"
                for row in grouped["monoBehaviourAudioId"]
                if isinstance(row, dict)
            ),
            "runtimeExecutionObserved": 0,
        },
        "audioGlobalConfig": {
            "source": "AudioGlobalConfig raw JSON or complete MonoBehaviour object index",
            "storedTriggerContextRows": len(grouped["audioGlobalConfig"]),
            "runtimeExecutionObserved": 0,
        },
        "modelViewStateAudio": {
            "source": "ModelViewStateControllerData tag-0x0001 normal Event plus tag-0x0002 positioned direct/control branches",
            "storedTriggerContextRows": len(grouped["modelViewStateAudio"]),
            "runtimeExecutionObserved": 0,
            "runtimeSelectionStatus": "wwiseEventAndPositionedBranchSelectionUnobserved",
            "ownerStatus": "modelViewStateControllerOwnerOnlyInteractiveAssociationNotOwner",
            "nativeRouteStatus": (
                "exactCurrentBuildPositionedAndNormalRoutes"
                if any(row.get("nativeRoute") for row in grouped["modelViewStateAudio"])
                else "nativeRouteUnavailable"
            ),
            "positionedDirectEventRows": sum(
                row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                for row in grouped["modelViewStateAudio"]
                if isinstance(row, dict)
            ),
            "positionedEndpointAuditStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("endpointAuditStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedPostAndForgetToAudioAdapterConnectionStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("postAndForgetToAudioAdapterConnectionStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unresolved",
            ),
            "positionedPostEventRuntimeStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("postEventRuntimeStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedAsyncBoundaryStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("asyncBoundaryStatus")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedAudioHandleWriteStatus": next(
                (
                    (row.get("nativeRoute") or {}).get("fieldContract", {}).get("audioHandleWrite", {}).get("status")
                    for row in grouped["modelViewStateAudio"]
                    if isinstance(row, dict) and row.get("semanticKind") == "modelViewStatePositionAudioEvent"
                ),
                "unavailable",
            ),
            "positionedControlRows": sum(
                str(row.get("semanticKind") or "").startswith("modelViewStatePositioned")
                and row.get("semanticKind") != "modelViewStatePositionAudioEvent"
                for row in grouped["modelViewStateAudio"]
                if isinstance(row, dict)
            ),
        },
        "managedLiteralCallsite": {
            "source": "fingerprint-locked current metadata literal handles and GameAssembly native callsites",
            "storedTriggerContextRows": len(grouped["managedLiteralCallsite"]),
            "runtimeExecutionObserved": 0,
        },
        "dialogTimeline": {
            "source": "conv/dlg_*.json line._debug.timelineTiming",
            "storedTriggerContextRows": len(grouped["dialogTimeline"]),
        },
        "dialogLifecycle": {
            "source": (
                "AudioDialogCustomEventTable dialogId + preloadEvents / "
                "preEnterEvents / postEnterEvents / preExitEvents / postExitEvents"
            ),
            "storedTriggerContextRows": len(grouped["dialogLifecycle"]),
            "rowsWithCurrentWwiseEvent": sum(
                bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ),
            "rowsWithNoDecodedMediaLeaf": sum(
                row.get("selection", {}).get("mediaSelectionStatus")
                == "wwiseEventHasNoDecodedMedia"
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ),
            "phaseCounts": dict(sorted(Counter(
                str((row.get("situation") or {}).get("lifecyclePhase") or "unknown")
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ).items())),
            "runtimeConsumer": DIALOG_LIFECYCLE_RUNTIME_CONSUMER,
        },
        "levelScriptVoice": {
            "source": "LevelScript PlayVoice/PlayVoiceNarrative constant _voId",
            "storedTriggerContextRows": len(grouped["levelScriptVoice"]),
            "rowsWithExactAudioDialogMedia": sum(
                row.get("selection", {}).get("voiceSelectionStatus")
                == "exactAudioDialogPathStem"
                for row in grouped["levelScriptVoice"]
                if isinstance(row, dict)
            ),
            "wwiseEventStatus": "notApplicable",
        },
        "timelineAudio": {
            "source": (
                "event contexts kind levelSequenceAudio or cutsceneTimeline, including "
                "Persistent and StreamingAssets serialized Timeline carriers"
            ),
            "storedTriggerContextRows": len(grouped["timelineAudio"]),
            "rowsWithCurrentWwiseEvent": sum(
                bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "rowsWithAuthoredKeyMissingFromCurrentWwiseIndex": sum(
                not bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "rowsByRuntimeContract": dict(sorted(Counter(
                str((row.get("owner") or {}).get("audioPlayableRuntimeContractId") or "unknown")
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ).items())),
            "rowsByCarrierEvidence": dict(sorted(Counter(
                (
                    "serializedPlayableCarrier"
                    if (row.get("owner") or {}).get("audioPlayableRuntimeContractId")
                    else (row.get("owner") or {}).get("runtimeCarrierStatus")
                    or "unresolved"
                )
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ).items())),
            "rowsByMusicActionType": dict(sorted(Counter(
                str((row.get("owner") or {}).get("audioMusicActionTypeLabel") or "unknown")
                for row in grouped["timelineAudio"]
                if (row.get("owner") or {}).get("audioPlayableRuntimeContractId")
                == "timelineMusicEventKey.audioMusic"
            ).items())),
            "rowsByMusicSkipPolicy": dict(sorted(Counter(
                str((row.get("owner") or {}).get("audioMusicTriggerOnSkipLabel") or "unknown")
                for row in grouped["timelineAudio"]
                if (row.get("owner") or {}).get("audioPlayableRuntimeContractId")
                == "timelineMusicEventKey.audioMusic"
            ).items())),
            "runtimeContracts": TIMELINE_AUDIO_RUNTIME_CONTRACTS,
        },
    }
    return {
        "schemaVersion": TRIGGER_CONTEXT_SCHEMA_VERSION,
        "language": language.upper(),
        "counts": {
            "total": len(contexts),
            "bySemanticKind": dict(sorted(counts.items())),
            "withPlayableMedia": sum(
                any(
                    isinstance(media_ref, dict) and media_ref.get("src")
                    for media_ref in row.get("mediaRefs") or []
                )
                for row in contexts
            ),
            "runtimeExecutionObserved": 0,
            "runtimeExecutionUnobserved": len(contexts),
            "timelineAudioRowsWithAuthoredKeyMissingFromCurrentWwiseIndex": sum(
                not bool((row.get("meaning") or {}).get("foundInWwise"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "timelineAudioRowsWithStaticRuntimeContract": sum(
                bool((row.get("owner") or {}).get("audioPlayableRuntimeContractId"))
                for row in grouped["timelineAudio"]
                if isinstance(row, dict)
            ),
            "dialogLifecycleRowsWithNoDecodedMediaLeaf": sum(
                row.get("selection", {}).get("mediaSelectionStatus")
                == "wwiseEventHasNoDecodedMedia"
                for row in grouped["dialogLifecycle"]
                if isinstance(row, dict)
            ),
        },
        "coverage": coverage,
        "contexts": contexts,
        "evidenceBoundary": (
            "Each row joins an authored trigger/owner/selection surface to zero or more "
            "media references. Definition, media availability, and runtime execution "
            "are independent evidence states. The shard never claims that a LevelScript, "
            "NpcProxy, dialog lifecycle state transition, Timeline Director, Wwise branch, "
            "RemoteCommon auto-play or lifecycle row, or selected line/slot actually ran. "
            "AudioDialogCustomEventTable lifecycle rows identify a static request/scheduling "
            "hook; RemoteCommon voiceId remains separate from its audioId; neither proves "
            "PostEvent or an audible media leaf. ModelView normal Event rows keep the "
            "serialized definition, possible Wwise media leaves, unresolved runtime branch, "
            "and unobserved activation as separate evidence fields; InteractiveTable "
            "associations are not promoted to owners."
        ),
    }
