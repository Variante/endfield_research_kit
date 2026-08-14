"""Authored table, cue, and runtime-configuration Audio contexts."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import identifiers, interactive_components
from .context_utils import append_context as _append_context
from .context_utils import load_json
from .context_utils import normalize_posix


NARRATIVE_AUDIO_TABLE_NAMES = (
    "RemoteCommonTable.json", "AudioCueTable.json", "AudioVoiceExtraData.json",
    "EmotionVoiceConfig.json", "AudioDialogCustomEventTable.json", "AudioDialogConfigs.json",
    "AudioRadioContinueTable.json", "RadioTable.json",
)
AUDIO_CONFIG_TABLE_NAMES = (
    "AudioBattleBuildings.json", "AudioCollection.json", "AudioDrop.json",
    "AudioFactory.json", "AudioFactoryAnnouncement.json", "AudioItemDragAndDrop.json",
    "AudioItemTypeDragAndDrop.json", "AudioLevel.json", "SpaceshipMusicTable.json",
    "SpaceshipAlbumMusicTable.json",
)
AUDIO_TABLE_NAMES = tuple(dict.fromkeys((*NARRATIVE_AUDIO_TABLE_NAMES, *AUDIO_CONFIG_TABLE_NAMES)))
AUDIO_HASH_FIELD_RE = re.compile(
    r"(?:^audio[A-Z_]|(?:Audio|Music)?Event(?:s|Ids?)?$|levelInitEvent$|battleMusicTriggerEvent$)",
    re.IGNORECASE,
)

def _build_remote_common_event_contexts(
    export_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Expose exact RemoteCommon auto-play Event requests in event rows.

    ``audioId`` is the authored SFX/Wwise Event request. ``voiceId`` is a
    separate dialogue identity and remains separate from the Event/media
    route. These low-level contexts prevent an authored RemoteCommon Event
    from being synthesized as a Timeline ownership gap.
    """

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    table_paths = [
        export_root / "structured" / source_root / "Table" / "RemoteCommonTable.json"
        for source_root in ("Persistent", "StreamingAssets")
    ]
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
                _append_context(contexts, seen, audio_id, {
                    "kind": "remoteCommonAudio",
                    "semanticRole": "remoteCommonAutoPlayAudioEvent",
                    "confidence": "exact",
                    "ownershipEvidenceLevel": "exactRemoteCommonSingleDataListRow",
                    "triggerEvidenceLevel": "exact",
                    "triggerBindingStatus": "exactRemoteCommonAudioId",
                    "triggerRole": "RemoteCommonTableAutoPlay",
                    "remoteCommonId": remote_id,
                    "singleId": single_id,
                    "index": line.get("index", line_index + 1),
                    "middleId": line.get("middleId"),
                    "actorList": line.get("actorList") or [],
                    "voiceId": line.get("voiceId"),
                    "voiceLinkStatus": "separateRemoteCommonVoiceId",
                    "authoredEventId": audio_id,
                    "autoPlay": True,
                    "autoPlayTime": line.get("autoPlayTime"),
                    "startAudioEvent": row.get("startAudioEvent"),
                    "endAudioEvent": row.get("endAudioEvent"),
                    "source": source_ref,
                    "sourcePath": source_ref,
                    "evidence": "exactRemoteCommonTableAutoPlay",
                    "triggerRequestEvidence": [
                        "exactRemoteCommonTableAutoPlay",
                        "exactRemoteCommonAudioId",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "remoteCommonAutoPlayExecutionNotObserved",
                    ],
                    "triggerOwnershipMethods": [
                        "RemoteCommonTable.remoteCommSingleDataList",
                    ],
                    "runtimeActivationStatus": "remoteCommonAutoPlayExecutionNotObserved",
                    "evidenceBoundary": (
                        "RemoteCommonTable autoPlay and the exact single-data audioId "
                        "prove an authored Event request. The row does not prove "
                        "RemoteCommon selection, execution, PostEvent, or an audible "
                        "Wwise media leaf; voiceId remains a separate dialogue identity."
                    ),
                })
    return dict(contexts)


def _first_recovered_mono_behaviour(export_root: Path, stem: str) -> Path | None:
    root = export_root / "recovered/AnimeStudio-cli"
    for source_root in ("Persistent", "StreamingAssets"):
        matches = sorted((root / source_root / "json_by_type/MonoBehaviour").glob(f"{stem}_p*.json"))
        if matches:
            return matches[0]
    return None


def _inflate_object_index_scalars(scalars: Iterable[Any]) -> dict[str, Any]:
    """Rebuild the represented portion of a compact object-index scalar tree."""

    root: dict[str, Any] = {}
    for scalar in scalars:
        if not isinstance(scalar, list) or len(scalar) < 3:
            continue
        scalar_path = str(scalar[0] or "")
        if not scalar_path.startswith("$."):
            continue
        tokens: list[str | int] = []
        for field, index in re.findall(r"([^.\[\]]+)|\[(\d+)\]", scalar_path[2:]):
            tokens.append(int(index) if index else field)
        if not tokens:
            continue
        current: Any = root
        valid = True
        for token_index, token in enumerate(tokens):
            is_last = token_index == len(tokens) - 1
            next_is_index = not is_last and isinstance(tokens[token_index + 1], int)
            if isinstance(token, str):
                if not isinstance(current, dict):
                    valid = False
                    break
                if is_last:
                    current[token] = scalar[2]
                    break
                expected_type = list if next_is_index else dict
                child = current.get(token)
                if not isinstance(child, expected_type):
                    child = expected_type()
                    current[token] = child
                current = child
                continue
            if not isinstance(current, list) or token < 0:
                valid = False
                break
            while len(current) <= token:
                current.append(None)
            if is_last:
                current[token] = scalar[2]
                break
            expected_type = list if next_is_index else dict
            child = current[token]
            if not isinstance(child, expected_type):
                child = expected_type()
                current[token] = child
            current = child
        if not valid:
            continue
    return root


def _audio_global_config_from_object_index(
    export_root: Path,
) -> tuple[dict[str, Any], str, dict[str, Any]] | None:
    """Recover retained AudioGlobalConfig scalars when raw JSON was not exported."""

    root = export_root / "recovered/AnimeStudio-cli"
    for source_root in ("Persistent", "StreamingAssets"):
        path = (
            root / source_root / "object_index" / "parts"
            / f"{source_root}_animestudio_json_by_type_MonoBehaviour.jsonl"
        )
        if not path.is_file():
            continue
        rows: Iterable[str]
        rg = shutil.which("rg")
        if rg:
            process = subprocess.run(
                [
                    rg, "--no-filename", "--no-line-number", "--fixed-strings",
                    "Beyond.Gameplay.Audio.AudioGlobalConfig", str(path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if process.returncode not in (0, 1):
                raise RuntimeError(
                    f"rg AudioGlobalConfig object-index lookup failed for {path}: "
                    f"{process.stderr.strip() or f'exit {process.returncode}'}"
                )
            rows = process.stdout.splitlines()
        else:
            rows = path.open("r", encoding="utf-8", errors="replace")
        try:
            for line in rows:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                script = row.get("script") if isinstance(row.get("script"), dict) else {}
                if (
                    row.get("recordType") != "object"
                    or script.get("fullName") != "Beyond.Gameplay.Audio.AudioGlobalConfig"
                ):
                    continue
                payload = _inflate_object_index_scalars(row.get("scalars") or [])
                if not payload:
                    continue
                obj = row.get("object") if isinstance(row.get("object"), dict) else {}
                provenance = {
                    "sourceRoot": source_root,
                    "serializedFile": obj.get("serializedFile"),
                    "pathId": obj.get("pathId"),
                    "scalarsTruncated": bool(row.get("scalarsTruncated")),
                }
                return payload, normalize_posix(path.relative_to(export_root)), provenance
        finally:
            if not rg and hasattr(rows, "close"):
                rows.close()
    return None


def collect_authored_runtime_config_contexts(
    export_root: Path,
    runtime_model: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Recover exact interactive-state and global lifecycle Event requests."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for event_id, rows in interactive_components.collect_interactive_component_contexts(
        export_root
    ).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    trigger_state_names: dict[int, str] = {}
    for system in (runtime_model or {}).get("systems") or []:
        if not isinstance(system, dict) or not str(system.get("type") or "").endswith("+EAudioTriggerState"):
            continue
        trigger_state_names = {
            int(value): str(name)
            for name, value in (system.get("enumValues") or {}).items()
            if isinstance(value, int)
        }
        break

    interactive_path = _first_recovered_mono_behaviour(export_root, "InteractiveAudioSetting")
    interactive = load_json(interactive_path, {}) if interactive_path else {}
    if isinstance(interactive, dict) and interactive_path is not None:
        source = normalize_posix(interactive_path.relative_to(export_root))
        for row_index, row in enumerate(interactive.get("subTemplateList") or []):
            if not isinstance(row, dict):
                continue
            model_id = str(row.get("modelId") or "")
            sub_template_id = str(row.get("subTemplateId") or "")
            for state_index, state_row in enumerate(row.get("audioList") or []):
                if not isinstance(state_row, dict):
                    continue
                try:
                    trigger_state_id = int(state_row.get("state"))
                except (TypeError, ValueError):
                    continue
                for event_index, event_id in enumerate(state_row.get("audio") or []):
                    event_name = str(event_id or "").strip()
                    if not event_name:
                        continue
                    context = {
                        "kind": "interactiveAudioTrigger",
                        "table": "InteractiveAudioSetting",
                        "semanticRole": "interactiveLifecycleEvent",
                        "modelId": model_id,
                        "subTemplateId": sub_template_id,
                        "triggerStateId": trigger_state_id,
                        "triggerRequestEvidence": ["serializedInteractiveAudioStateMap"],
                        "triggerRuntimeActivationStatuses": ["runtimeInteractiveStateEntryRequired"],
                        "path": f"subTemplateList[{row_index}].audioList[{state_index}].audio[{event_index}]",
                        "source": source,
                        "evidence": "exactSerializedInteractiveAudioSetting",
                    }
                    if trigger_state_id in trigger_state_names:
                        context["triggerStateName"] = trigger_state_names[trigger_state_id]
                    _append_context(contexts, seen, event_name, context)
            for custom_index, custom_row in enumerate(row.get("customAudioList") or []):
                if not isinstance(custom_row, dict):
                    continue
                event_name = str(custom_row.get("audioEvent") or "").strip()
                if not event_name:
                    continue
                context = {
                    "kind": "interactiveAudioTrigger",
                    "table": "InteractiveAudioSetting",
                    "semanticRole": "interactiveCustomStateEvent",
                    "modelId": model_id,
                    "subTemplateId": sub_template_id,
                    "triggerCustomState": str(custom_row.get("audioState") or ""),
                    "triggerRequestEvidence": ["serializedInteractiveAudioCustomStateMap"],
                    "triggerRuntimeActivationStatuses": ["runtimeInteractiveCustomStateEntryRequired"],
                    "path": f"subTemplateList[{row_index}].customAudioList[{custom_index}].audioEvent",
                    "source": source,
                    "evidence": "exactSerializedInteractiveAudioSetting",
                }
                description = str(custom_row.get("desc") or "").strip()
                if description:
                    context["description"] = description
                _append_context(contexts, seen, event_name, context)

    global_path = _first_recovered_mono_behaviour(export_root, "AudioGlobalConfig")
    global_config = load_json(global_path, {}) if global_path else {}
    global_provenance: dict[str, Any] = {}
    global_evidence = "exactSerializedAudioGlobalConfig"
    if not isinstance(global_config, dict) or global_path is None:
        indexed_global_config = _audio_global_config_from_object_index(export_root)
        if indexed_global_config is not None:
            global_config, source, global_provenance = indexed_global_config
            global_evidence = "exactSerializedAudioGlobalConfigObjectIndexScalar"
        else:
            global_config = {}
            source = ""
    else:
        source = normalize_posix(global_path.relative_to(export_root))
    if isinstance(global_config, dict) and source:

        def global_context_base() -> dict[str, Any]:
            return {
                "source": source,
                "evidence": global_evidence,
                **{
                    key: value for key, value in global_provenance.items()
                    if value not in (None, "", [])
                },
            }

        def append_named(value: Any, path: str, semantic_role: str) -> None:
            event_name = str(value or "").strip()
            if not event_name:
                return
            _append_context(contexts, seen, event_name, {
                "kind": "audioGlobalConfigEvent",
                "table": "AudioGlobalConfig",
                "semanticRole": semantic_role,
                "path": path,
                **global_context_base(),
                "triggerRequestEvidence": ["serializedGlobalAudioPolicy"],
                "triggerRuntimeActivationStatuses": ["runtimeLifecycleConditionRequired"],
            })

        def append_hash(value: Any, path: str, semantic_role: str, **extra: Any) -> None:
            raw = value.get("_id") if isinstance(value, dict) else value
            if not isinstance(raw, int) or isinstance(raw, bool) or raw == 0:
                return
            event_hash = raw & 0xFFFFFFFF
            context = {
                "kind": "audioGlobalConfigEventHash",
                "table": "AudioGlobalConfig",
                "semanticRole": semantic_role,
                "path": path,
                "signedValue": raw,
                "eventHash": event_hash,
                **global_context_base(),
                "triggerRequestEvidence": ["serializedGlobalAudioPolicy"],
                "triggerRuntimeActivationStatuses": ["runtimeLifecycleConditionRequired"],
            }
            context.update({key: value for key, value in extra.items() if value not in (None, "", [])})
            _append_context(contexts, seen, identifiers.event_hash_context_key(event_hash), context)

        for field, role in (
            ("loginMusicStartEvent", "loginMusicStartEvent"),
            ("metaMusicStartEvent", "metaMusicStartEvent"),
            ("gameplayMusicStartEvent", "gameplayMusicStartEvent"),
            ("rushWindEventName", "rushWindStartEvent"),
            ("rushWindStopEventName", "rushWindStopEvent"),
        ):
            append_named(global_config.get(field), field, role)
        for field, role in (
            ("initEvents", "audioEngineInitEvent"),
            ("preloadEvents", "audioPreloadEvent"),
            ("onLoginEvents", "loginLifecycleEvent"),
        ):
            for index, value in enumerate(global_config.get(field) or []):
                append_named(value, f"{field}[{index}]", role)
        for field, role in (
            ("globalEventLocal", "globalLocalEvent"),
            ("globalEventRemote", "globalRemoteEvent"),
            ("globalEventLeaveMainGame", "leaveMainGameEvent"),
            ("musicEventCutsceneForceEmpty", "cutsceneForceEmptyMusicEvent"),
            ("specialGameplayGenderSelectIn", "genderSelectEnterEvent"),
            ("specialGameplayGenderSelectOut", "genderSelectExitEvent"),
        ):
            append_hash(global_config.get(field), field, role)
        for field, role in (
            ("persistantPreparedEvents", "persistentPreparedEvent"),
            ("musicCommonEventList", "commonMusicEvent"),
        ):
            for index, value in enumerate(global_config.get(field) or []):
                append_hash(value, f"{field}[{index}]", role)
        for field, owner_kind in (
            ("charInitEvent", "character"),
            ("npcInitEvent", "npc"),
            ("enemyInitEvent", "enemy"),
        ):
            mapping = global_config.get(field) or {}
            keys = mapping.get("_keyData") or [] if isinstance(mapping, dict) else []
            values = mapping.get("_valueData") or [] if isinstance(mapping, dict) else []
            for index, (owner_id, value) in enumerate(zip(keys, values)):
                append_hash(
                    value,
                    f"{field}._valueData[{index}]",
                    "entityInitEvent",
                    ownerKind=owner_kind,
                    ownerId=str(owner_id or ""),
                )
        for field, direction in (("audioStatesIn", "enter"), ("audioStatesOut", "exit")):
            mapping = global_config.get(field) or {}
            masks = mapping.get("_keyData") or [] if isinstance(mapping, dict) else []
            values = mapping.get("_valueData") or [] if isinstance(mapping, dict) else []
            for state_index, (state_mask, value) in enumerate(zip(masks, values)):
                ids = value.get("_ids") or [] if isinstance(value, dict) else []
                for event_index, event_id in enumerate(ids):
                    append_hash(
                        event_id,
                        f"{field}._valueData[{state_index}]._ids[{event_index}]",
                        "audioStateTransitionEvent",
                        stateDirection=direction,
                        audioStateMask=state_mask,
                    )
    return dict(contexts)


def _iter_audio_cue_expression_nodes(value: Any, path: str) -> Iterable[tuple[dict[str, Any], str]]:
    if not isinstance(value, dict):
        return
    yield value, path
    for index, child in enumerate(value.get("children") or []):
        if isinstance(child, dict):
            yield from _iter_audio_cue_expression_nodes(child, f"{path}.children[{index}]")


def collect_audio_cue_semantics(export_root: Path) -> dict[str, Any]:
    """Split AudioCue Event requests from runtime expression operands."""

    table_path = next((
        export_root / "structured" / source_root / "Table" / "AudioCueTable.json"
        for source_root in ("Persistent", "StreamingAssets")
        if (export_root / "structured" / source_root / "Table" / "AudioCueTable.json").is_file()
    ), None)
    payload = load_json(table_path, {}) if table_path else {}
    source = normalize_posix(table_path.relative_to(export_root)) if table_path else ""
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    operands: list[dict[str, Any]] = []
    definitions: dict[int, dict[str, Any]] = {}

    for raw_cue_id, row in sorted((payload.items() if isinstance(payload, dict) else []), key=lambda item: str(item[0])):
        if not isinstance(row, dict):
            continue
        try:
            cue_signed_id = int(raw_cue_id)
        except (TypeError, ValueError):
            continue
        cue_id = cue_signed_id & 0xFFFFFFFF
        definition = {
            "cueSignedId": cue_signed_id,
            "cueId": cue_id,
            "cueHex": f"0x{cue_id:08x}",
            "source": source,
            "handlerCount": 0,
            "directHandlerCount": 0,
            "levelHandlerCount": 0,
            "behaviorEvents": [],
            "expressionOperands": [],
        }

        handlers: list[tuple[str, str, int, dict[str, Any]]] = []
        for handler_index, handler in enumerate(row.get("directHandlers") or []):
            if isinstance(handler, dict):
                handlers.append(("direct", "", handler_index, handler))
        level_map = row.get("levelHandlerMap") if isinstance(row.get("levelHandlerMap"), dict) else {}
        for level_id, wrapper in sorted(level_map.items(), key=lambda item: str(item[0])):
            level_handlers = wrapper.get("handlers") if isinstance(wrapper, dict) else wrapper
            if not isinstance(level_handlers, list):
                continue
            for handler_index, handler in enumerate(level_handlers):
                if isinstance(handler, dict):
                    handlers.append(("level", str(level_id), handler_index, handler))

        for handler_scope, level_id, handler_index, handler in handlers:
            definition["handlerCount"] += 1
            definition[f"{handler_scope}HandlerCount"] += 1
            handler_base = (
                f"{raw_cue_id}.directHandlers[{handler_index}]"
                if handler_scope == "direct"
                else f"{raw_cue_id}.levelHandlerMap[{level_id}].handlers[{handler_index}]"
            )
            for expression_side, root_name in (("behavior", "behaviourExpr"), ("condition", "conditionExpr")):
                for node, expression_path in _iter_audio_cue_expression_nodes(
                    handler.get(root_name),
                    f"{handler_base}.{root_name}",
                ):
                    try:
                        expr_type = int(node.get("exprType"))
                    except (TypeError, ValueError):
                        continue
                    string_value = str(node.get("stringValue") or "").strip()
                    common = {
                        "cueSignedId": cue_signed_id,
                        "cueId": cue_id,
                        "cueHex": f"0x{cue_id:08x}",
                        "handlerScope": handler_scope,
                        "handlerIndex": handler_index,
                        "expressionSide": expression_side,
                        "expressionPath": expression_path,
                        "exprType": expr_type,
                        "boolValue": bool(node.get("boolValue")),
                        "intValue": node.get("intValue"),
                        "floatValue": node.get("floatValue"),
                        "stringValue": string_value,
                        "source": source,
                    }
                    if level_id:
                        common["levelId"] = level_id
                    if expression_side == "behavior" and expr_type == 3 and string_value:
                        context = {
                            "kind": "audioCueBehaviorEvent",
                            "table": "AudioCueTable",
                            "semanticRole": "cueBehaviorEventRequest",
                            "evidence": "exactAudioCueBehaviorExpression",
                            "triggerRequestEvidence": ["audioCueBehaviorExprType3"],
                            "triggerRuntimeActivationStatuses": ["cueInvocationAndExpressionEvaluationRequired"],
                            **common,
                        }
                        _append_context(contexts, seen, string_value, context)
                        definition["behaviorEvents"].append({"eventId": string_value, **context})
                    elif expr_type == 8 and string_value:
                        operand = {
                            "kind": "audioCueExpressionOperand",
                            "semanticRole": "runtimeCueVariable",
                            "wwiseEventStatus": "notApplicable",
                            "evidence": "exactAudioCueExpressionOperand",
                            **common,
                        }
                        operands.append(operand)
                        definition["expressionOperands"].append(operand)
        definitions[cue_id] = definition

    return {
        "eventContexts": dict(contexts),
        "expressionOperands": operands,
        "cueDefinitions": definitions,
        "source": source,
    }


def collect_audio_global_control_semantics(
    export_root: Path,
    cue_semantics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recover Global cue references and RTPC parameters without making Event claims."""

    cue_semantics = cue_semantics or collect_audio_cue_semantics(export_root)
    cue_definitions = cue_semantics.get("cueDefinitions") or {}
    global_path = _first_recovered_mono_behaviour(export_root, "AudioGlobalConfig")
    global_config = load_json(global_path, {}) if global_path else {}
    source = normalize_posix(global_path.relative_to(export_root)) if global_path else ""
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    cue_refs: list[dict[str, Any]] = []
    rtpc_parameters: list[dict[str, Any]] = []
    if not isinstance(global_config, dict):
        global_config = {}

    for field, value in global_config.items():
        if not str(field).startswith("musicCue"):
            continue
        raw = value.get("_id") if isinstance(value, dict) else value
        if not isinstance(raw, int) or isinstance(raw, bool) or raw == 0:
            continue
        cue_id = raw & 0xFFFFFFFF
        definition = cue_definitions.get(cue_id)
        ref = {
            "kind": "audioGlobalMusicCueRef",
            "field": str(field),
            "cueSignedId": raw,
            "cueId": cue_id,
            "cueHex": f"0x{cue_id:08x}",
            "definitionStatus": "resolved" if definition else "missing",
            "source": source,
            "evidence": "exactSerializedAudioGlobalConfigCueId",
            "wwiseEventStatus": "notApplicable",
        }
        if definition:
            ref["handlerCount"] = definition.get("handlerCount", 0)
            ref["behaviorEventCount"] = len(definition.get("behaviorEvents") or [])
            ref["expressionOperandCount"] = len(definition.get("expressionOperands") or [])
            for behavior in definition.get("behaviorEvents") or []:
                event_name = str(behavior.get("eventId") or "").strip()
                if not event_name:
                    continue
                _append_context(contexts, seen, event_name, {
                    "kind": "audioGlobalMusicCueBehaviorEvent",
                    "table": "AudioGlobalConfig",
                    "semanticRole": "globalLifecycleMusicCueBehaviorEvent",
                    "globalMusicCueField": str(field),
                    "cueSignedId": raw,
                    "cueId": cue_id,
                    "cueHex": f"0x{cue_id:08x}",
                    "handlerScope": behavior.get("handlerScope"),
                    "levelId": behavior.get("levelId"),
                    "handlerIndex": behavior.get("handlerIndex"),
                    "expressionPath": behavior.get("expressionPath"),
                    "exprType": 3,
                    "source": source,
                    "evidence": "exactGlobalMusicCueToAudioCueBehaviorChain",
                    "triggerRequestEvidence": ["serializedGlobalMusicCueReference", "audioCueBehaviorExprType3"],
                    "triggerRuntimeActivationStatuses": ["globalLifecycleCueInvocationAndExpressionEvaluationRequired"],
                })
        cue_refs.append(ref)

    for field in (
        "rtpcGlobalVol", "rtpcMusicVol", "rtpcSfxVol", "rtpcVoiceVol",
        "rtpcControllerSpeakerVol", "rtpcVibrationVol",
        "listenerSpeedRtpcName", "listenerAccelerationRtpcName",
    ):
        parameter_name = str(global_config.get(field) or "").strip()
        if not parameter_name:
            continue
        rtpc_parameters.append({
            "kind": "rtpcParameter",
            "parameterName": parameter_name,
            "field": field,
            "source": source,
            "evidence": "exactSerializedAudioGlobalConfigParameter",
            "wwiseEventStatus": "notApplicable",
        })
    return {
        "eventContexts": dict(contexts),
        "audioGlobalMusicCueRefs": cue_refs,
        "rtpcParameters": rtpc_parameters,
    }


def collect_table_contexts(
    export_root: Path,
    runtime_model: dict[str, Any] | None = None,
    *,
    cue_semantics: dict[str, Any] | None = None,
    global_controls: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    prefix_re = re.compile(r"^(?:au_|bark_|radio_)", re.IGNORECASE)
    named_event_field_re = re.compile(
        r"(?:event(?:s|ids?)?$|musicEventSample$|^audio(?:collect|die|hit|pick|drag|drop)$)",
        re.IGNORECASE,
    )

    def visit(value: Any, path: str, table: str, source: str) -> None:
        if isinstance(value, str) and prefix_re.match(value.strip()):
            field_path = re.sub(r"\[\d+\]$", "", path)
            field_name = field_path.rsplit(".", 1)[-1]
            semantic_role = ""
            if named_event_field_re.search(field_name):
                semantic_role = "authoredEventName"
            # Voice IDs, audioOverride values, radio row IDs, and continuation
            # IDs are media/dialog identities rather than Wwise Events.  Do
            # not flatten them into this Event inventory.
            if semantic_role:
                _append_context(contexts, seen, value, {
                    "kind": "table",
                    "table": table,
                    "path": path,
                    "source": source,
                    "semanticRole": semantic_role,
                    "evidence": "exactTableField",
                })
        elif isinstance(value, int) and not isinstance(value, bool) and value:
            # List indices belong to the containing authored field.  Preserve
            # that field name so arrays such as levelInitEvent[] are recovered
            # as event ids without promoting adjacent music-state integers.
            field_path = re.sub(r"\[\d+\]$", "", path)
            field_name = field_path.rsplit(".", 1)[-1]
            if AUDIO_HASH_FIELD_RE.search(field_name):
                event_hash = value & 0xFFFFFFFF
                _append_context(contexts, seen, identifiers.event_hash_context_key(event_hash), {
                    "kind": "tableEventHash",
                    "table": table,
                    "path": path,
                    "source": source,
                    "signedValue": value,
                    "eventHash": event_hash,
                    "evidence": "authoredUint32EventId",
                })
        elif isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                visit(child, child_path, table, source)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]", table, source)

    for table_name in AUDIO_TABLE_NAMES:
        if table_name == "AudioCueTable.json":
            continue
        path = next((
            export_root / "structured" / source_root / "Table" / table_name
            for source_root in ("Persistent", "StreamingAssets")
            if (export_root / "structured" / source_root / "Table" / table_name).is_file()
        ), None)
        if path is None:
            continue
        payload = load_json(path, None)
        if payload is not None:
            visit(payload, "", path.stem, normalize_posix(path.relative_to(export_root)))
    cue_semantics = cue_semantics or collect_audio_cue_semantics(export_root)
    global_controls = global_controls or collect_audio_global_control_semantics(export_root, cue_semantics)
    for event_id, rows in cue_semantics.get("eventContexts", {}).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    for event_id, rows in global_controls.get("eventContexts", {}).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    for event_id, rows in collect_authored_runtime_config_contexts(export_root, runtime_model).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    # RemoteCommon audioId is an authored Wwise Event request, unlike the
    # adjacent voiceId/audioOverride identities that the generic table walker
    # intentionally leaves out. Keep this route explicit so Event summaries
    # do not manufacture a Timeline-carrier gap for it.
    for event_id, rows in _build_remote_common_event_contexts(export_root).items():
        for row in rows:
            _append_context(contexts, seen, event_id, row)
    return dict(contexts)


def collect_table_audio_events(export_root: Path) -> tuple[set[str], set[int]]:
    """Return authored Event names and hashes from one table/config scan."""

    contexts = collect_table_contexts(export_root)
    hashes: set[int] = set()
    for key in contexts:
        if not key.startswith("#0x"):
            continue
        try:
            hashes.add(int(key[1:], 16) & 0xFFFFFFFF)
        except ValueError:
            continue
    names = {
        key
        for key, rows in contexts.items()
        if key
        and not key.startswith("#0x")
        and rows
    }
    return names, hashes
