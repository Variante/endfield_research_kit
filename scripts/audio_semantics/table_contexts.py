"""Authored table, cue, and runtime-configuration Audio contexts."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from . import audio_cue_native, identifiers, interactive_components
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


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys instead of silently accepting the last value."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result

def _build_remote_common_event_contexts(
    export_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Expose exact RemoteCommon Event requests in event rows.

    ``audioId`` is the authored SFX/Wwise Event request. ``startAudioEvent``
    and ``endAudioEvent`` are authored lifecycle requests on the same row.
    ``voiceId`` is a separate dialogue identity and remains separate from the
    Event/media route. These low-level contexts prevent authored RemoteCommon
    Events from being synthesized as a Timeline ownership gap.
    """

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    table_paths = [
        export_root / "structured" / source_root / "Table" / "RemoteCommonTable.json"
        for source_root in ("Persistent", "StreamingAssets")
    ]
    table_sources: list[tuple[str, Path, dict[str, Any], str]] = []
    malformed_source = False
    for source_root, table_path in zip(("Persistent", "StreamingAssets"), table_paths):
        if not table_path.is_file():
            continue
        try:
            table_data = table_path.read_bytes()
            payload = json.loads(
                table_data,
                object_pairs_hook=_reject_duplicate_json_keys,
            )
        except (OSError, UnicodeError, ValueError):
            malformed_source = True
            continue
        if not isinstance(payload, dict):
            malformed_source = True
            continue
        try:
            source_ref = normalize_posix(table_path.relative_to(export_root))
        except ValueError:
            source_ref = normalize_posix(table_path)
        table_sources.append((
            source_root,
            table_path,
            payload,
            hashlib.sha256(table_data).hexdigest(),
        ))
    # A malformed mirror makes the table overlay unverifiable.  Do not let a
    # valid sibling silently turn into an apparently complete ownership index.
    if malformed_source:
        return {}

    if len({digest for _source_root, _path, _payload, digest in table_sources}) != 1:
        # Persistent/Streaming are duplicate table mirrors for this contract.
        # A differing mirror is not an overlay we can safely reconcile field by
        # field: reject the complete RemoteCommon contribution instead of
        # publishing an apparently exact lifecycle or auto-play request.
        return {}

    # Preserve the repository-wide Persistent-over-Streaming source rule while
    # avoiding duplicate evidence rows when both physical mirrors are present.
    _source_root, _table_path, payload, _digest = next(
        row for row in table_sources if row[0] == "Persistent"
    ) if any(row[0] == "Persistent" for row in table_sources) else table_sources[0]
    source_ref = normalize_posix(_table_path.relative_to(export_root))
    for remote_id, row in sorted(payload.items(), key=lambda item: str(item[0])):
        if not isinstance(row, dict):
            continue
        remote_id = str(remote_id or "").strip()
        if not remote_id:
            continue
        for field, lifecycle_phase in (
            ("startAudioEvent", "start"),
            ("endAudioEvent", "end"),
        ):
            event_name = str(row.get(field) or "").strip()
            if event_name:
                _append_context(contexts, seen, event_name, {
                    "kind": "remoteCommonLifecycleAudio",
                    "semanticRole": "remoteCommonLifecycleAudioEvent",
                    "confidence": "exact",
                    "ownershipEvidenceLevel": "exactRemoteCommonLifecycleField",
                    "triggerEvidenceLevel": "exact",
                    "triggerBindingStatus": f"exactRemoteCommon{lifecycle_phase.title()}AudioEvent",
                    "triggerRole": f"RemoteCommonTable{lifecycle_phase.title()}AudioEvent",
                    "remoteCommonId": remote_id,
                    "lifecyclePhase": lifecycle_phase,
                    "field": field,
                    "authoredEventId": event_name,
                    "source": source_ref,
                    "sourcePath": source_ref,
                    "evidence": "exactRemoteCommonTableLifecycleAudioField",
                    "triggerRequestEvidence": [
                        "exactRemoteCommonTableLifecycleAudioField",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "remoteCommonLifecycleExecutionNotObserved",
                    ],
                    "triggerOwnershipMethods": [
                        f"RemoteCommonTable.{field}",
                    ],
                    "runtimeActivationStatus": "remoteCommonLifecycleExecutionNotObserved",
                    "evidenceBoundary": (
                        "RemoteCommonTable lifecycle audio fields and their exact row key "
                        "prove an authored Event request and lifecycle role. The row does "
                        "not prove RemoteCommon selection, execution, PostEvent, or an "
                        "audible Wwise media leaf."
                    ),
                })
        if row.get("autoPlay") is not True:
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


AudioCueExpressionNode = dict[str, Any]

# Keep this version independent from the much larger Audio semantic schema.  A
# reader may use the AST without having to understand Event/media projections.
AUDIO_CUE_EXPRESSION_SCHEMA_VERSION = 1
_AUDIO_CUE_EXPRESSION_KNOWN_TYPES = frozenset(range(0, 9))
_AUDIO_CUE_EXPRESSION_KEYS = frozenset({
    "boolValue", "children", "exprType", "floatValue", "intValue", "stringValue",
})
_AUDIO_CUE_MAX_DIAGNOSTICS = 64
_AUDIO_CUE_MAX_DIAGNOSTIC_TEXT = 240
_AUDIO_CUE_MAX_DEPTH = 1024
_AUDIO_CUE_MAX_NODES = 10000
_AUDIO_CUE_MAX_HANDLERS = 2048
_AUDIO_CUE_MAX_STRING = 1024
_AUDIO_CUE_MAX_LEVEL = 128
_AUDIO_CUE_MAX_PATH = 8192
_AUDIO_CUE_MAX_CHILDREN = 10000
_AUDIO_CUE_SIGNED32_MIN = -(2 ** 31)
_AUDIO_CUE_SIGNED32_MAX = (2 ** 31) - 1
_AUDIO_CUE_MAX_INT = _AUDIO_CUE_SIGNED32_MAX
_AUDIO_CUE_MAX_FLOAT = 3.4028234663852886e38


def _audio_cue_diagnostic(
    diagnostics: list[dict[str, Any]],
    *,
    code: str,
    path: str,
    detail: str,
) -> None:
    """Append one bounded, deterministic AST validation diagnostic."""

    if len(diagnostics) >= _AUDIO_CUE_MAX_DIAGNOSTICS:
        return
    diagnostics.append({
        "code": str(code),
        "path": str(path)[:_AUDIO_CUE_MAX_DIAGNOSTIC_TEXT],
        "detail": str(detail)[:_AUDIO_CUE_MAX_DIAGNOSTIC_TEXT],
    })


def _audio_cue_scalar_valid(field: str, value: Any) -> bool:
    if field == "exprType":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and _AUDIO_CUE_SIGNED32_MIN <= value <= _AUDIO_CUE_SIGNED32_MAX
        )
    if field == "boolValue":
        return isinstance(value, bool)
    if field == "intValue":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and _AUDIO_CUE_SIGNED32_MIN <= value <= _AUDIO_CUE_SIGNED32_MAX
        )
    if field == "floatValue":
        if not isinstance(value, float):
            return False
        # ``float(10**10000)`` raises OverflowError.  Validation must never
        # turn hostile serialized input into a parser exception.
        try:
            numeric = float(value)
        except (OverflowError, ValueError, TypeError):
            return False
        return math.isfinite(numeric) and abs(numeric) <= _AUDIO_CUE_MAX_FLOAT
    if field == "stringValue":
        return isinstance(value, str)
    return True


def _audio_cue_safe_scalar(field: str, value: Any) -> Any:
    """Return a bounded scalar suitable for AST/debug payloads."""

    if field == "stringValue":
        return value[:_AUDIO_CUE_MAX_STRING] if isinstance(value, str) else None
    if field in {"exprType", "intValue"}:
        return value if _audio_cue_scalar_valid(field, value) else None
    if field == "floatValue":
        return value if _audio_cue_scalar_valid(field, value) else None
    if field == "boolValue":
        return value if isinstance(value, bool) else None
    return None


def _audio_cue_raw_scalars(value: dict[str, Any]) -> dict[str, Any]:
    """Retain exact scalar keys while bounding every value."""

    return {
        str(key): _audio_cue_safe_scalar(str(key), item)
        for key, item in value.items()
        if key in _AUDIO_CUE_EXPRESSION_KEYS
        and key != "children"
    }


def _audio_cue_safe_segment(value: Any) -> str | None:
    """Encode an authored level key so it cannot inject path syntax."""

    text = str(value)
    if len(text) <= _AUDIO_CUE_MAX_LEVEL and re.fullmatch(r"[A-Za-z0-9_.-]*", text):
        return text
    encoded = text.encode("utf-8", "backslashreplace").hex()
    # Keep the complete bounded input encoding.  A prefix would allow two
    # distinct level IDs to collapse to one path.
    if len(encoded) > _AUDIO_CUE_MAX_LEVEL * 2:
        return None
    return f"hex_{encoded}"


def _audio_cue_bounded_path(value: str) -> str | None:
    """Keep a path only when complete; never truncate path coordinates."""

    return value if isinstance(value, str) and len(value) <= _AUDIO_CUE_MAX_PATH else None


def _audio_cue_compact_path(root_path: str, indices: tuple[int, ...]) -> str | None:
    """Encode a complete bounded child-index tuple without string truncation."""

    if any(index < 0 or index >= _AUDIO_CUE_MAX_CHILDREN for index in indices):
        return None
    # Delimit every decimal index explicitly.  Concatenated fixed-width-ish
    # encodings can collide as soon as an index exceeds the assumed width
    # (for example (4097, 564) versus (256, 4660)).
    value = f"{root_path}#children/" + "/".join(str(index) for index in indices)
    return _audio_cue_bounded_path(value)


def walk_audio_cue_expression(
    value: Any,
    *,
    cue_signed_id: int,
    cue_id: int,
    cue_hex: str,
    handler_scope: str,
    level_id: str,
    handler_index: int,
    expression_side: str,
    root_field: str,
    root_path: str,
    source: str,
    native_contract: dict[str, Any] | None = None,
) -> tuple[list[AudioCueExpressionNode], list[dict[str, Any]]]:
    """Validate and flatten one AudioCue expression tree.

    This is deliberately a projection, not an evaluator.  Every emitted node
    carries its source coordinates and the six serialized scalar fields.  A
    malformed node is retained as an opaque node with a validation status; it
    is never eligible to create an Event or a runtime branch claim.
    """

    nodes: list[AudioCueExpressionNode] = []
    diagnostics: list[dict[str, Any]] = []

    if (
        not isinstance(cue_signed_id, int)
        or isinstance(cue_signed_id, bool)
        or not (_AUDIO_CUE_SIGNED32_MIN <= cue_signed_id <= _AUDIO_CUE_SIGNED32_MAX)
    ):
        _audio_cue_diagnostic(
            diagnostics, code="cueSignedIdOutOfRange", path="expressionRoot",
            detail="cueSignedId must be a signed 32-bit integer",
        )
        return [], diagnostics
    if (
        not isinstance(cue_id, int)
        or isinstance(cue_id, bool)
        or not (0 <= cue_id <= 0xFFFFFFFF)
    ):
        _audio_cue_diagnostic(
            diagnostics, code="cueIdOutOfRange", path="expressionRoot",
            detail="cueId must be an unsigned 32-bit integer",
        )
        return [], diagnostics
    if not isinstance(level_id, str) or len(level_id) > _AUDIO_CUE_MAX_LEVEL:
        _audio_cue_diagnostic(
            diagnostics, code="levelIdTooLong", path="expressionRoot",
            detail="handler level ID exceeds bounded length",
        )
        return [], diagnostics
    if not isinstance(cue_hex, str) or len(cue_hex) > _AUDIO_CUE_MAX_LEVEL:
        _audio_cue_diagnostic(
            diagnostics, code="cueHexTooLong", path="expressionRoot",
            detail="cue hex identifier exceeds bounded length",
        )
        return [], diagnostics
    if not isinstance(handler_index, int) or isinstance(handler_index, bool) or handler_index < 0 or handler_index >= _AUDIO_CUE_MAX_HANDLERS:
        _audio_cue_diagnostic(
            diagnostics, code="handlerIndexOutOfRange", path="expressionRoot",
            detail="handler index exceeds bounded range",
        )
        return [], diagnostics

    native_validated = (native_contract or {}).get("status") == "validated"
    # Names are build-specific native evidence.  Keep them fail-closed unless
    # the caller supplied the exact validated contract from audio_cue_native.
    expression_names = (
        (native_contract or {}).get("expressionTypes") or {}
        if native_validated else {}
    )
    operator_names = (
        (native_contract or {}).get("operatorTypes") or {}
        if native_validated else {}
    )
    bounded_root_path = _audio_cue_bounded_path(root_path)
    if bounded_root_path is None:
        _audio_cue_diagnostic(diagnostics, code="pathLimit", path="expressionRoot", detail="expression path exceeds bounded length")
        return [], diagnostics
    stack: list[tuple[Any, str, str, int, bool, int | None, tuple[int, ...]]] = [
        (value, bounded_root_path, "", 0, True, None, ())
    ]
    while stack:
        current, path, parent_path, depth, ancestor_valid, parent_operator, path_indices = stack.pop()
        if len(nodes) >= _AUDIO_CUE_MAX_NODES:
            _audio_cue_diagnostic(diagnostics, code="nodeLimit", path=path, detail="expression node limit reached")
            break
        if not isinstance(current, dict):
            _audio_cue_diagnostic(diagnostics, code="nonDictNode", path=path, detail="expression node is not an object")
            continue

        status = "validated"
        issues: list[str] = []
        keys = set(current)
        if keys != _AUDIO_CUE_EXPRESSION_KEYS:
            status = "invalidShape"
            issues.append("keys")
            _audio_cue_diagnostic(
                diagnostics, code="invalidShape", path=path,
                detail="expression node keys must exactly be boolValue,children,exprType,floatValue,intValue,stringValue",
            )
        expr_type = current.get("exprType")
        if not _audio_cue_scalar_valid("exprType", expr_type):
            status = "badScalar"
            issues.append("exprType")
            _audio_cue_diagnostic(diagnostics, code="badScalar", path=f"{path}.exprType", detail="exprType must be a non-bool integer")
        elif expr_type not in _AUDIO_CUE_EXPRESSION_KNOWN_TYPES:
            status = "unknownExprType"
            issues.append("exprType")
            _audio_cue_diagnostic(diagnostics, code="unknownExprType", path=f"{path}.exprType", detail=f"unsupported exprType {expr_type!r}")
        for field in ("boolValue", "intValue", "floatValue", "stringValue"):
            if not _audio_cue_scalar_valid(field, current.get(field)):
                if status == "validated":
                    status = "badScalar"
                issues.append(field)
                _audio_cue_diagnostic(diagnostics, code="badScalar", path=f"{path}.{field}", detail=f"{field} has an invalid scalar type")
        string_value = current.get("stringValue")
        if isinstance(string_value, str) and len(string_value) > _AUDIO_CUE_MAX_STRING:
            status = "badScalar"
            issues.append("stringLength")
            _audio_cue_diagnostic(diagnostics, code="stringTooLong", path=f"{path}.stringValue", detail="stringValue exceeds bounded length")
            string_value = string_value[:_AUDIO_CUE_MAX_STRING]
        children = current.get("children")
        child_paths: list[str] = []
        if not isinstance(children, list):
            if status == "validated":
                status = "invalidShape"
            issues.append("children")
            _audio_cue_diagnostic(diagnostics, code="childrenNotListOfDict", path=f"{path}.children", detail="children must be a list of objects")
        elif len(children) > _AUDIO_CUE_MAX_CHILDREN:
            # Admit no child entries before the bounded length decision.  In
            # particular, do not scan or project a hostile oversized list.
            status = "childrenLimit"
            issues.append("childrenLength")
            _audio_cue_diagnostic(
                diagnostics, code="childrenLimit", path=f"{path}.children",
                detail="child list exceeds bounded length",
            )
            # Do not construct or traverse any child projection after the
            # bounded admission gate.  This prevents a malformed oversized
            # parent from manufacturing Event/variable descendants.
            children = []
        elif any(not isinstance(child, dict) for child in children):
            if status == "validated":
                status = "invalidShape"
            issues.append("children")
            _audio_cue_diagnostic(diagnostics, code="childrenNotListOfDict", path=f"{path}.children", detail="children must be a list of objects")
        if depth >= _AUDIO_CUE_MAX_DEPTH and isinstance(children, list) and children:
            if status == "validated":
                status = "depthLimit"
            issues.append("depth")
            _audio_cue_diagnostic(diagnostics, code="depthLimit", path=path, detail="expression depth limit reached")
            children = []
        current_valid = ancestor_valid and status == "validated"
        # Function-call operators govern their argument subtrees.  Preserve
        # the nearest exact operator through transparent binary/unary
        # composites, but clear it for an unknown nested function call rather
        # than attributing a child to an unrelated ancestor.
        child_operator = parent_operator
        if current_valid and native_validated and expr_type == 2:
            child_operator = (
                current.get("intValue")
                if isinstance(current.get("intValue"), int)
                and not isinstance(current.get("intValue"), bool)
                and current.get("intValue") in operator_names
                else None
            )
        if current_valid and native_validated and isinstance(expr_type, int) and expr_type in expression_names:
            expr_type_name = expression_names[expr_type]
        else:
            expr_type_name = None
        if current_valid and native_validated and parent_operator in operator_names:
            operator_name = operator_names[parent_operator]
        else:
            operator_name = None
        canonical_node_class = "opaque"
        if current_valid and expression_side == "behavior" and expr_type == 3 and isinstance(string_value, str) and string_value.strip() and not children:
            canonical_node_class = "authoredEventRequest"
        elif current_valid and expr_type == 8 and isinstance(string_value, str) and string_value.strip() and not children:
            canonical_node_class = "runtimeCueVariable"
        elif current_valid and isinstance(children, list) and children:
            canonical_node_class = "compositeOpaque"

        # Keep the historical nodeClass spelling for existing build/UI
        # consumers while exposing the strict canonical role separately.  A
        # runtime variable is an authored-variable *candidate* only when the
        # exact native parent function operator proves that context.
        node_class = (
            "authoredVariableNameCandidate"
            if canonical_node_class == "runtimeCueVariable"
            and operator_name in {"SetBoolVar", "GetBoolVar", "CleanBoolVar"}
            else "stringLiteral"
            if canonical_node_class == "runtimeCueVariable"
            else canonical_node_class
        )
        semantic_role = (
            "runtimeCueVariable"
            if canonical_node_class == "runtimeCueVariable"
            else None
        )

        raw_scalars = _audio_cue_raw_scalars(current)
        safe_expr_type = _audio_cue_safe_scalar("exprType", expr_type)
        safe_int_value = _audio_cue_safe_scalar("intValue", current.get("intValue"))
        safe_float_value = _audio_cue_safe_scalar("floatValue", current.get("floatValue"))
        safe_bool_value = _audio_cue_safe_scalar("boolValue", current.get("boolValue"))
        node: AudioCueExpressionNode = {
            "cueSignedId": cue_signed_id,
            "cueId": cue_id,
            "cueU32": cue_id,
            "cueHex": cue_hex,
            "handlerScope": handler_scope,
            "handlerLevel": level_id,
            "levelId": level_id,
            "handlerIndex": handler_index,
            "expressionSide": expression_side,
            "rootField": root_field,
            "expressionRootField": root_field,
            "expressionPath": path,
            "path": path,
            "parentPath": parent_path,
            "depth": depth,
            "exprType": safe_expr_type,
            "exprTypeName": expr_type_name,
            "exprOperatorType": operator_name,
            "nativeEnumStatus": "validated" if native_validated else str((native_contract or {}).get("status") or "missing"),
            "semanticRole": semantic_role,
            "canonicalNodeClass": canonical_node_class,
            "boolValue": safe_bool_value,
            "intValue": safe_int_value,
            "floatValue": safe_float_value,
            "stringValue": string_value,
            "rawScalars": raw_scalars,
            "rawScalar": raw_scalars,
            "childPaths": child_paths,
            "nodeClass": node_class,
            "validationStatus": status if ancestor_valid else "ancestorInvalid",
            "validationIssues": issues[:8],
            "source": source[:_AUDIO_CUE_MAX_PATH],
        }
        nodes.append(node)
        if not isinstance(children, list):
            children = []
        for index in range(min(len(children), _AUDIO_CUE_MAX_CHILDREN) - 1, -1, -1):
            child = children[index]
            child_indices = path_indices + (index,)
            child_path = (
                _audio_cue_compact_path(root_path, child_indices)
                if "#children/" in path
                else _audio_cue_bounded_path(f"{path}.children[{index}]")
            )
            if child_path is None:
                child_path = _audio_cue_compact_path(root_path, child_indices)
            if child_path is None:
                _audio_cue_diagnostic(
                    diagnostics, code="pathLimit", path=path,
                    detail="child expression path exceeds bounded length",
                )
                continue
            child_paths.insert(0, child_path)
            if isinstance(child, dict):
                stack.append((child, child_path, path, depth + 1, current_valid, child_operator, child_indices))
    return nodes, diagnostics


def _iter_audio_cue_expression_nodes(value: Any, path: str) -> Iterable[tuple[dict[str, Any], str]]:
    """Compatibility iterator for callers that only need valid object nodes."""

    if not isinstance(value, dict):
        return
    stack: list[tuple[dict[str, Any], str]] = [(value, path)]
    while stack:
        current, current_path = stack.pop()
        yield current, current_path
        children = current.get("children")
        if not isinstance(children, list):
            continue
        for index in range(len(children) - 1, -1, -1):
            child = children[index]
            if isinstance(child, dict):
                stack.append((child, f"{current_path}.children[{index}]"))


def collect_audio_cue_semantics(
    export_root: Path,
    *,
    native_context: Any | None = None,
) -> dict[str, Any]:
    """Project AudioCue definitions without evaluating their expressions."""

    table_path = next((
        export_root / "structured" / source_root / "Table" / "AudioCueTable.json"
        for source_root in ("Persistent", "StreamingAssets")
        if (export_root / "structured" / source_root / "Table" / "AudioCueTable.json").is_file()
    ), None)
    payload = load_json(table_path, {}) if table_path else {}
    source = normalize_posix(table_path.relative_to(export_root)) if table_path else ""
    native_contract = audio_cue_native.exact_native_audio_cue_contract(native_context)
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    operands: list[dict[str, Any]] = []
    definitions: dict[int, dict[str, Any]] = {}
    all_diagnostics: list[dict[str, Any]] = []

    for raw_cue_id, row in sorted((payload.items() if isinstance(payload, dict) else []), key=lambda item: str(item[0])):
        if not isinstance(row, dict):
            continue
        try:
            cue_signed_id = int(raw_cue_id)
        except (TypeError, ValueError):
            continue
        if not (_AUDIO_CUE_SIGNED32_MIN <= cue_signed_id <= _AUDIO_CUE_SIGNED32_MAX):
            _audio_cue_diagnostic(
                all_diagnostics,
                code="cueSignedIdOutOfRange",
                path="AudioCueTable.cueId",
                detail="cueSignedId must be a signed 32-bit integer",
            )
            continue
        cue_id = cue_signed_id & 0xFFFFFFFF
        cue_hex = f"0x{cue_id:08x}"
        cue_path_id = str(cue_signed_id)
        definition: dict[str, Any] = {
            "cueSignedId": cue_signed_id,
            "cueId": cue_id,
            "cueU32": cue_id,
            "cueHex": cue_hex,
            "source": source[:_AUDIO_CUE_MAX_PATH],
            "handlerCount": 0,
            "directHandlerCount": 0,
            "levelHandlerCount": 0,
            "behaviorEvents": [],
            "expressionOperands": [],
            "expressionAst": [],
            "expressionDiagnostics": [],
        }

        handlers: list[tuple[str, str, int, dict[str, Any]]] = []
        handler_limit_hit = False
        direct_handlers = row.get("directHandlers", [])
        if not isinstance(direct_handlers, list):
            _audio_cue_diagnostic(
                definition["expressionDiagnostics"], code="directHandlersNotList",
                path=f"{raw_cue_id}.directHandlers", detail="directHandlers must be a list",
            )
            direct_handlers = []
        for handler_index, handler in enumerate(direct_handlers):
            if handler_index >= _AUDIO_CUE_MAX_HANDLERS or len(handlers) >= _AUDIO_CUE_MAX_HANDLERS:
                handler_limit_hit = True
                break
            if isinstance(handler, dict):
                handlers.append(("direct", "", handler_index, handler))
            else:
                _audio_cue_diagnostic(
                    definition["expressionDiagnostics"], code="nonDictHandler",
                    path=f"{raw_cue_id}.directHandlers[{handler_index}]", detail="handler must be an object",
                )

        raw_level_map = row.get("levelHandlerMap")
        level_map = raw_level_map if isinstance(raw_level_map, dict) else {}
        if raw_level_map not in (None, {}) and not isinstance(raw_level_map, dict):
            _audio_cue_diagnostic(
                definition["expressionDiagnostics"], code="levelHandlerMapNotObject",
                path=f"{raw_cue_id}.levelHandlerMap", detail="levelHandlerMap must be an object",
            )
        for level_id, wrapper in sorted(level_map.items(), key=lambda item: str(item[0])):
            level_key = str(level_id)
            safe_level = _audio_cue_safe_segment(level_key)
            if safe_level is None:
                _audio_cue_diagnostic(
                    definition["expressionDiagnostics"], code="levelIdTooLong",
                    path=f"{cue_path_id}.levelHandlerMap", detail="levelId exceeds bounded length",
                )
                continue
            level_path = _audio_cue_bounded_path(
                f"{cue_path_id}.levelHandlerMap[{safe_level}]"
            )
            if level_path is None:
                _audio_cue_diagnostic(
                    definition["expressionDiagnostics"], code="pathLimit",
                    path=f"{cue_path_id}.levelHandlerMap", detail="level handler path exceeds bounded length",
                )
                continue
            level_handlers = wrapper.get("handlers") if isinstance(wrapper, dict) else wrapper
            if isinstance(wrapper, dict) and "handlers" not in wrapper:
                _audio_cue_diagnostic(
                    definition["expressionDiagnostics"], code="levelHandlersMissing",
                    path=f"{level_path}.handlers", detail="level handler wrapper has no handlers list",
                )
                level_handlers = []
            if not isinstance(level_handlers, list):
                _audio_cue_diagnostic(
                    definition["expressionDiagnostics"], code="levelHandlersNotList",
                    path=f"{level_path}.handlers", detail="level handlers must be a list",
                )
                continue
            for handler_index, handler in enumerate(level_handlers):
                if handler_index >= _AUDIO_CUE_MAX_HANDLERS or len(handlers) >= _AUDIO_CUE_MAX_HANDLERS:
                    handler_limit_hit = True
                    break
                if isinstance(handler, dict):
                    handlers.append(("level", level_key, handler_index, handler))
                else:
                    _audio_cue_diagnostic(
                        definition["expressionDiagnostics"], code="nonDictHandler",
                        path=f"{level_path}.handlers[{handler_index}]", detail="handler must be an object",
                    )

        if handler_limit_hit or len(handlers) > _AUDIO_CUE_MAX_HANDLERS:
            _audio_cue_diagnostic(
                definition["expressionDiagnostics"], code="handlerLimit",
                path=str(cue_signed_id), detail="AudioCue handler limit reached",
            )
        for handler_scope, level_id, handler_index, handler in handlers[:_AUDIO_CUE_MAX_HANDLERS]:
            definition["handlerCount"] += 1
            definition[f"{handler_scope}HandlerCount"] += 1
            handler_base = (
                f"{cue_path_id}.directHandlers[{handler_index}]"
                if handler_scope == "direct"
                else f"{cue_path_id}.levelHandlerMap[{_audio_cue_safe_segment(level_id)}].handlers[{handler_index}]"
            )
            for expression_side, root_name in (("behavior", "behaviourExpr"), ("condition", "conditionExpr")):
                root_path = f"{handler_base}.{root_name}"
                if root_name not in handler:
                    _audio_cue_diagnostic(
                        definition["expressionDiagnostics"], code="missingRoot",
                        path=root_path, detail="expression root is absent",
                    )
                    continue
                nodes, diagnostics = walk_audio_cue_expression(
                    handler.get(root_name),
                    cue_signed_id=cue_signed_id, cue_id=cue_id, cue_hex=cue_hex,
                    handler_scope=handler_scope, level_id=level_id,
                    handler_index=handler_index, expression_side=expression_side,
                    root_field=root_name, root_path=root_path, source=source,
                    native_contract=native_contract,
                )
                definition["expressionAst"].extend(nodes)
                for diagnostic in diagnostics:
                    _audio_cue_diagnostic(
                        definition["expressionDiagnostics"],
                        code=diagnostic.get("code", "invalidNode"),
                        path=diagnostic.get("path", root_path),
                        detail=diagnostic.get("detail", "invalid expression node"),
                    )
                for node in nodes:
                    string_value = node.get("stringValue") if isinstance(node.get("stringValue"), str) else ""
                    common = {
                        key: node.get(key)
                        for key in (
                            "cueSignedId", "cueId", "cueU32", "cueHex", "handlerScope", "handlerLevel",
                            "levelId", "handlerIndex", "expressionSide", "rootField", "expressionRootField",
                            "expressionPath", "path", "parentPath", "depth", "exprType", "boolValue",
                            "intValue", "floatValue", "stringValue", "childPaths", "nodeClass",
                            "validationStatus", "exprTypeName", "exprOperatorType", "nativeEnumStatus",
                            "semanticRole", "canonicalNodeClass", "source",
                        )
                    }
                    if node.get("nodeClass") == "authoredEventRequest":
                        event_id = string_value.strip()
                        context = {
                            "kind": "audioCueBehaviorEvent", "table": "AudioCueTable",
                            "semanticRole": "cueBehaviorEventRequest",
                            "expressionNodeClass": "authoredEventRequest",
                            "evidence": "exactAudioCueBehaviorExpression",
                            "triggerRequestEvidence": ["audioCueBehaviorExprType3"],
                            "triggerRuntimeActivationStatuses": [
                                "cueInvocationAndExpressionEvaluationRequired", "audioEventRuntimePlaybackUnobserved",
                            ],
                            **common, "expressionNodeClass": "authoredEventRequest", "eventName": event_id,
                        }
                        _append_context(contexts, seen, event_id, context)
                        definition["behaviorEvents"].append({"eventId": event_id, **context})
                    elif node.get("semanticRole") == "runtimeCueVariable":
                        operand = {
                            "kind": "audioCueExpressionOperand", "semanticRole": "runtimeCueVariable",
                            "wwiseEventStatus": "notApplicable", "runtimeObservationStatus": "unobserved",
                            "evidence": "exactAudioCueExpressionOperand", **common,
                        }
                        operands.append(operand)
                        definition["expressionOperands"].append(operand)

        definition["expressionNodeCount"] = len(definition["expressionAst"])
        definition["expressionDiagnosticCount"] = len(definition["expressionDiagnostics"])
        # Count the published legacy classes exactly once.  The canonical
        # role is available on each node, but must not create a second or
        # fabricated class-count alias for build/UI consumers.
        class_counts: Counter[str] = Counter(
            str(node.get("nodeClass") or "opaque")
            for node in definition["expressionAst"]
        )
        definition["expressionNodeClassCounts"] = dict(sorted(class_counts.items()))
        all_diagnostics.extend(definition["expressionDiagnostics"])
        definitions[cue_id] = definition

    return {
        "audioCueExpressionSchemaVersion": AUDIO_CUE_EXPRESSION_SCHEMA_VERSION,
        "audioCueNativeContract": native_contract,
        "eventContexts": dict(contexts),
        "expressionOperands": operands,
        "cueDefinitions": definitions,
        "diagnostics": all_diagnostics[:_AUDIO_CUE_MAX_DIAGNOSTICS],
        "source": source,
    }


def audio_cue_expression_detail_for_contexts(
    contexts: Iterable[dict[str, Any]],
    cue_semantics: dict[str, Any],
) -> dict[str, Any] | None:
    """Return full AST detail for a lazy Event detail row.

    Definitions are selected only from exact cue IDs carried by Event
    contexts.  A missing definition intentionally returns no AST; callers can
    retain their invocation context without turning it into an Event.
    """

    definitions = cue_semantics.get("cueDefinitions") if isinstance(cue_semantics, dict) else {}
    if not isinstance(definitions, dict):
        return None
    cue_ids: set[int] = set()
    for context in contexts or ():
        if not isinstance(context, dict):
            continue
        for key in ("cueId", "cueU32"):
            value = context.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                cue_ids.add(value & 0xFFFFFFFF)
    rows: list[dict[str, Any]] = []
    for cue_id in sorted(cue_ids):
        definition = definitions.get(cue_id)
        if not isinstance(definition, dict):
            continue
        rows.append({
            key: definition.get(key)
            for key in (
                "cueSignedId", "cueId", "cueU32", "cueHex", "source",
                "handlerCount", "directHandlerCount", "levelHandlerCount",
                "expressionNodeCount", "expressionDiagnosticCount",
                "expressionNodeClassCounts", "expressionAst", "expressionDiagnostics",
            )
            if key in definition
        })
    if not rows:
        return None
    return {
        "audioCueExpressionSchemaVersion": int(
            cue_semantics.get("audioCueExpressionSchemaVersion")
            or AUDIO_CUE_EXPRESSION_SCHEMA_VERSION
        ),
        "definitions": rows,
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
