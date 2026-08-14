"""InteractiveData audio component and ownership recovery."""

from __future__ import annotations

import hashlib
import struct
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from .context_utils import append_context as _append_context
from .context_utils import normalize_posix


if __package__ == "scripts.audio_semantics":
    from scripts.game_data.memorypack.interactive import (
        decode_interactive_template_memorypack,
        find_interactive_audio_property_maps,
        parse_interactive_audio_component,
        parse_interactive_trigger_zone_audio_property_component,
    )
    from scripts.story_builder.interactive_binary import decode_interactive_table
    from scripts.story_builder.levelscript_binary import (
        find_embedded_action_serialized_map_audio,
    )
elif __package__ == "audio_semantics":
    from game_data.memorypack.interactive import (
        decode_interactive_template_memorypack,
        find_interactive_audio_property_maps,
        parse_interactive_audio_component,
        parse_interactive_trigger_zone_audio_property_component,
    )
    from story_builder.interactive_binary import decode_interactive_table
    from story_builder.levelscript_binary import find_embedded_action_serialized_map_audio
else:  # pragma: no cover - only package imports are supported.
    raise ImportError(
        "import as scripts.audio_semantics.interactive_components or "
        "audio_semantics.interactive_components"
    )


def collect_interactive_component_contexts(
    export_root: Path,
    *,
    decoder: Any | None = None,
    table_decoder: Any | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Decode per-entity InteractiveAudioData state maps from MemoryPack.

    ``InteractiveData`` files are core-template definitions, while
    ``InteractiveTable`` maps those definitions to configured interactive
    identities.  The component body itself proves the request, but the file
    name is not by itself an entity owner.  When both table mirrors decode to
    the same exact mapping, add the template path and all configured consumer
    identities to each context.  A missing or ambiguous table mapping stays an
    explicit association gap rather than being guessed from the file stem.
    """

    if decoder is None:
        def decoder(_path: Path, data: bytes, _size: int) -> dict[str, Any]:
            components: list[dict[str, Any]] = []
            signature = bytes((0x5D, 0x02, 0, 0, 0, 0, 0x0D))
            cursor = 0
            while True:
                candidate = data.find(signature, cursor)
                if candidate < 0:
                    break
                cursor = candidate + 1
                try:
                    parsed, end = parse_interactive_audio_component(data, candidate + 2, 2)
                except (UnicodeDecodeError, struct.error, ValueError):
                    continue
                if end <= candidate + len(signature) or end > len(data):
                    continue
                components.append({
                    "index": len(components),
                    "sourceOffset": candidate,
                    **parsed,
                })
            property_components: list[dict[str, Any]] = []
            property_signature = bytes((0xF5, 0x03, 0xFF, 0xFF, 0xFF, 0xFF))
            cursor = 0
            while True:
                candidate = data.find(property_signature, cursor)
                if candidate < 0:
                    break
                cursor = candidate + 1
                try:
                    parsed, end = parse_interactive_trigger_zone_audio_property_component(
                        data,
                        candidate + 2,
                        3,
                    )
                except (UnicodeDecodeError, struct.error, ValueError):
                    continue
                if end <= candidate + len(property_signature) or end > len(data):
                    continue
                property_components.append({
                    "index": len(property_components),
                    "sourceOffset": candidate,
                    **parsed,
                })
            template = decode_interactive_template_memorypack(_path, data, len(data))
            template_body = template.get("decoded") if isinstance(template, dict) else None
            return {"decoded": {
                "componentAudioComponents": components,
                "componentAudioPropertyComponents": property_components,
                "standaloneAudioPropertyMaps": find_interactive_audio_property_maps(data),
                "templateConfigProperties": (
                    template_body.get("templateConfigProperties")
                    if isinstance(template_body, dict)
                    else None
                ),
                "templateActionMapAudio": (
                    template_body.get("templateActionMapAudio")
                    if isinstance(template_body, dict)
                    else None
                ),
                "embeddedActionMapAudioActions": (
                    find_embedded_action_serialized_map_audio(data)
                ),
            }}

    # InteractiveTable is an exact serialized ownership index.  Keep this
    # optional so focused callers/tests that only provide an InteractiveData
    # fixture retain their bounded component evidence without needing a table.
    template_ids_by_file_name: dict[str, list[str]] = defaultdict(list)
    template_paths_by_id: dict[str, str] = {}
    consumers_by_template: dict[str, list[str]] = defaultdict(list)
    table_source_paths: list[str] = []
    table_source_fingerprint = ""
    table: dict[str, Any] | None = None
    if table_decoder is None:
        table_decoder = decode_interactive_table
    table_versions: list[tuple[str, Path, bytes, str]] = []
    for source_root in ("Persistent", "StreamingAssets"):
        table_path = (
            export_root / "structured" / source_root
            / "Data/Json/Interactive/InteractiveTable.json"
        )
        if not table_path.is_file():
            continue
        try:
            table_data = table_path.read_bytes()
        except OSError:
            continue
        table_versions.append((
            source_root,
            table_path,
            table_data,
            hashlib.sha256(table_data).hexdigest(),
        ))
    if table_versions and len({row[3] for row in table_versions}) == 1:
        try:
            table = table_decoder(table_versions[0][2])
        except (UnicodeDecodeError, struct.error, ValueError):
            table = None
        if isinstance(table, dict):
            table_source_paths = [
                normalize_posix(path.relative_to(export_root))
                for _root, path, _data, _digest in table_versions
            ]
            table_source_fingerprint = table_versions[0][3]
            for template_id, template_path in (table.get("coreTemplatePaths") or {}).items():
                normalized_template_path = normalize_posix(str(template_path or ""))
                pure_template_path = PurePosixPath(normalized_template_path)
                if (
                    pure_template_path.is_absolute()
                    or ".." in pure_template_path.parts
                    or not normalized_template_path.startswith(
                        "Data/Json/Interactive/InteractiveData/"
                    )
                ):
                    continue
                template_id = str(template_id)
                template_paths_by_id[template_id] = normalized_template_path
                file_name = pure_template_path.name
                if file_name:
                    template_ids_by_file_name[file_name].append(template_id)
            for consumer_id, template_id in (table.get("objectToTemplate") or {}).items():
                consumers_by_template[str(template_id)].append(str(consumer_id))
    paths_by_identity: dict[str, list[Path]] = defaultdict(list)
    for source_root in ("Persistent", "StreamingAssets"):
        root = export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveData"
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            paths_by_identity[path.stem].append(path)

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for owner_id, paths in sorted(paths_by_identity.items()):
        paths_by_hash: dict[str, list[Path]] = defaultdict(list)
        data_by_hash: dict[str, bytes] = {}
        for path in paths:
            try:
                data = path.read_bytes()
            except OSError:
                continue
            digest = hashlib.sha256(data).hexdigest()
            paths_by_hash[digest].append(path)
            data_by_hash[digest] = data
        for digest, version_paths in sorted(paths_by_hash.items()):
            data = data_by_hash[digest]
            decoded = decoder(version_paths[0], data, len(data))
            body = decoded.get("decoded") if isinstance(decoded, dict) else None
            components = body.get("componentAudioComponents") if isinstance(body, dict) else None
            if not isinstance(components, list):
                components = []
            property_components = (
                body.get("componentAudioPropertyComponents") if isinstance(body, dict) else None
            )
            if not isinstance(property_components, list):
                property_components = []
            standalone_property_maps = (
                body.get("standaloneAudioPropertyMaps") if isinstance(body, dict) else None
            )
            if not isinstance(standalone_property_maps, list):
                standalone_property_maps = []
            template_config = (
                body.get("templateConfigProperties") if isinstance(body, dict) else None
            )
            if not isinstance(template_config, dict):
                template_config = {}
            template_action_map = (
                body.get("templateActionMapAudio") if isinstance(body, dict) else None
            )
            if not isinstance(template_action_map, dict):
                template_action_map = {}
            embedded_action_audio = (
                body.get("embeddedActionMapAudioActions")
                if isinstance(body, dict)
                else None
            )
            if not isinstance(embedded_action_audio, list):
                embedded_action_audio = []
            source_paths = [normalize_posix(path.relative_to(export_root)) for path in version_paths]
            template_file_name = f"{owner_id}.json"
            template_ids = sorted(set(template_ids_by_file_name.get(template_file_name, [])))
            template_path = ""
            if len(template_ids) == 1:
                # The current table has one path per template id.  Keep the
                # path exact and do not collapse a future ambiguous match.
                template_path = template_paths_by_id.get(template_ids[0], "")
            consumer_ids = sorted({
                consumer
                for template_id in template_ids
                for consumer in consumers_by_template.get(template_id, [])
            })
            if len(template_ids) == 1:
                association_status = "exactInteractiveTableTemplatePath"
            elif len(template_ids) > 1:
                association_status = "ambiguousInteractiveTableTemplatePath"
            elif table_versions:
                association_status = "interactiveTableTemplatePathUnresolved"
            else:
                association_status = "interactiveTableIndexUnavailable"
            for component in components:
                if not isinstance(component, dict):
                    continue
                component_index = component.get("index")
                for state_index, row in enumerate(component.get("audioRows") or []):
                    if not isinstance(row, dict):
                        continue
                    for event_index, event_id in enumerate(row.get("events") or []):
                        event_name = str(event_id or "").strip()
                        if not event_name:
                            continue
                        _append_context(contexts, seen, event_name, {
                            "kind": "interactiveComponentTrigger",
                            "table": "InteractiveData",
                            "semanticRole": "entityInteractiveLifecycleEvent",
                            "ownerKind": "interactiveEntityConfig",
                            "ownerId": owner_id,
                            "interactiveTemplateIds": template_ids,
                            "interactiveTemplatePath": template_path,
                            "interactiveConsumerIds": consumer_ids,
                            "templateAssociationStatus": association_status,
                            "interactiveTableSourcePaths": table_source_paths,
                            "interactiveTableSha256": table_source_fingerprint,
                            "componentIndex": component_index,
                            "sourceOffset": component.get("sourceOffset"),
                            "triggerStateId": row.get("state"),
                            "triggerStateName": str(row.get("stateName") or ""),
                            "triggerRequestEvidence": ["decodedInteractiveAudioComponentStateMap"],
                            "triggerRuntimeActivationStatuses": ["runtimeInteractiveStateEntryRequired"],
                            "path": f"componentAudioComponents[{component_index}].audioRows[{state_index}].events[{event_index}]",
                            "sourcePaths": source_paths,
                            "sourceFingerprint": digest,
                            "evidence": "exactDecodedMemoryPackInteractiveAudioData",
                        })
                for custom_index, row in enumerate(component.get("customRows") or []):
                    if not isinstance(row, dict):
                        continue
                    event_name = str(row.get("event") or "").strip()
                    if not event_name:
                        continue
                    context = {
                        "kind": "interactiveComponentTrigger",
                        "table": "InteractiveData",
                        "semanticRole": "entityInteractiveCustomStateEvent",
                        "ownerKind": "interactiveEntityConfig",
                        "ownerId": owner_id,
                        "interactiveTemplateIds": template_ids,
                        "interactiveTemplatePath": template_path,
                        "interactiveConsumerIds": consumer_ids,
                        "templateAssociationStatus": association_status,
                        "interactiveTableSourcePaths": table_source_paths,
                        "interactiveTableSha256": table_source_fingerprint,
                        "componentIndex": component_index,
                        "sourceOffset": component.get("sourceOffset"),
                        "triggerCustomState": str(row.get("name") or ""),
                        "triggerRequestEvidence": ["decodedInteractiveAudioComponentCustomStateMap"],
                        "triggerRuntimeActivationStatuses": ["runtimeInteractiveCustomStateEntryRequired"],
                        "path": f"componentAudioComponents[{component_index}].customRows[{custom_index}].event",
                        "sourcePaths": source_paths,
                        "sourceFingerprint": digest,
                        "evidence": "exactDecodedMemoryPackInteractiveAudioData",
                    }
                    note = str(row.get("note") or "").strip()
                    if note:
                        context["description"] = note
                    _append_context(contexts, seen, event_name, context)
            for component in property_components:
                if not isinstance(component, dict):
                    continue
                component_index = component.get("index")
                for property_index, row in enumerate(component.get("audioPropertyRows") or []):
                    if not isinstance(row, dict):
                        continue
                    if row.get("identityKind") != "wwiseEvent":
                        continue
                    property_key = str(row.get("key") or "")
                    for event_index, event_id in enumerate(row.get("events") or []):
                        event_name = str(event_id or "").strip()
                        if not event_name:
                            continue
                        _append_context(contexts, seen, event_name, {
                            "kind": "interactiveComponentPropertyAudio",
                            "table": "InteractiveData",
                            "semanticRole": "interactiveComponentAuthoredAudioProperty",
                            "ownerKind": "interactiveEntityConfig",
                            "ownerId": owner_id,
                            "interactiveTemplateIds": template_ids,
                            "interactiveTemplatePath": template_path,
                            "interactiveConsumerIds": consumer_ids,
                            "templateAssociationStatus": association_status,
                            "interactiveTableSourcePaths": table_source_paths,
                            "interactiveTableSha256": table_source_fingerprint,
                            "componentIndex": component_index,
                            "componentType": component.get("type"),
                            "componentTag": component.get("tag"),
                            "sourceOffset": component.get("sourceOffset"),
                            "propertyMapOffset": component.get("propertyMapOffset"),
                            "audioPropertyKey": property_key,
                            "triggerRequestEvidence": [
                                "exactDecodedInteractiveComponentAudioPropertyMap"
                            ],
                            "triggerRuntimeActivationStatuses": [
                                "runtimePropertyConsumerUnresolved",
                                "runtimeEventPostingNotObserved",
                            ],
                            "path": (
                                f"componentAudioPropertyComponents[{component_index}]"
                                f".audioPropertyRows[{property_index}].events[{event_index}]"
                            ),
                            "sourcePaths": source_paths,
                            "sourceFingerprint": digest,
                            "evidence": "exactDecodedMemoryPackInteractiveAudioProperty",
                        })
            component_property_events = {
                str(event_id)
                for component in property_components
                if isinstance(component, dict)
                for row in component.get("audioPropertyRows") or []
                if isinstance(row, dict)
                for event_id in row.get("events") or []
                if event_id
            }
            template_config_events: set[str] = set()
            for property_index, row in enumerate(template_config.get("audioPropertyRows") or []):
                if not isinstance(row, dict) or row.get("identityKind") != "wwiseEvent":
                    continue
                property_key = str(row.get("key") or "")
                for event_index, event_id in enumerate(row.get("events") or []):
                    event_name = str(event_id or "").strip()
                    if not event_name:
                        continue
                    template_config_events.add(event_name)
                    _append_context(contexts, seen, event_name, {
                        "kind": "interactiveTemplateConfigAudio",
                        "table": "InteractiveData",
                        "semanticRole": "interactiveTemplateAuthoredAudioProperty",
                        "ownerKind": "interactiveEntityConfig",
                        "ownerId": owner_id,
                        "interactiveTemplateIds": template_ids,
                        "interactiveTemplatePath": template_path,
                        "interactiveConsumerIds": consumer_ids,
                        "templateAssociationStatus": association_status,
                        "interactiveTableSourcePaths": table_source_paths,
                        "interactiveTableSha256": table_source_fingerprint,
                        "audioPropertyKey": property_key,
                        "propertyMapOffset": template_config.get("configPropertiesOffset"),
                        "propertyMapEndOffset": template_config.get("configPropertiesEndOffset"),
                        "triggerRequestEvidence": [
                            "exactDecodedInteractiveTemplateConfigProperties"
                        ],
                        "triggerRuntimeActivationStatuses": [
                            "runtimeTemplatePropertyConsumerUnresolved",
                            "runtimeEventPostingNotObserved",
                        ],
                        "path": (
                            "templateConfigProperties.audioPropertyRows"
                            f"[{property_index}].events[{event_index}]"
                        ),
                        "sourcePaths": source_paths,
                        "sourceFingerprint": digest,
                        "evidence": "exactDecodedMemoryPackInteractiveTemplateConfigProperty",
                    })
            template_action_events: set[str] = set()
            for action_index, action in enumerate(template_action_map.get("audioActions") or []):
                if not isinstance(action, dict):
                    continue
                fields = action.get("fields") if isinstance(action.get("fields"), dict) else {}
                stop_on_release = fields.get("stopOnRelease")
                target = fields.get("target") or fields.get("position")
                for binding_index, binding in enumerate(action.get("eventBindings") or []):
                    if not isinstance(binding, dict):
                        continue
                    event_name = str(binding.get("eventName") or "").strip()
                    if not event_name:
                        continue
                    template_action_events.add(event_name)
                    _append_context(contexts, seen, event_name, {
                        "kind": "interactiveTemplateActionAudio",
                        "table": "InteractiveData",
                        "semanticRole": "interactiveTemplateActionAudioRequest",
                        "ownerKind": "interactiveEntityConfig",
                        "ownerId": owner_id,
                        "interactiveTemplateIds": template_ids,
                        "interactiveTemplatePath": template_path,
                        "interactiveConsumerIds": consumer_ids,
                        "templateAssociationStatus": association_status,
                        "interactiveTableSourcePaths": table_source_paths,
                        "interactiveTableSha256": table_source_fingerprint,
                        "audioAction": action.get("action"),
                        "audioActionRole": binding.get("role"),
                        "audioSourceField": binding.get("sourceField"),
                        "actionMapRole": action.get("actionMapRole"),
                        "actionMapOffset": template_action_map.get("offset"),
                        "actionLocalId": action.get("localId"),
                        "actionUid": action.get("uid"),
                        "actionNextId": action.get("nextId"),
                        "actionUnionTag": action.get("unionTag"),
                        "actionSerializedMemberCount": action.get("serializedMemberCount"),
                        "actionRecordOffset": action.get("recordOffset"),
                        "actionPayloadOffset": action.get("payloadOffset"),
                        "stopOnRelease": (
                            stop_on_release.get("value")
                            if isinstance(stop_on_release, dict)
                            else None
                        ),
                        "targetBindingKind": (
                            target.get("bindingKind") if isinstance(target, dict) else None
                        ),
                        "targetParameterKind": (
                            "target" if "target" in fields else "position"
                        ),
                        "targetParamSource": (
                            target.get("paramSource") if isinstance(target, dict) else None
                        ),
                        "triggerRequestEvidence": [
                            "exactEmbeddedInteractiveActionSerializedMapActionList",
                            "exactTypedAudioActionPayload",
                        ],
                        "triggerRuntimeActivationStatuses": [
                            "runtimeActionActivationUnobserved",
                            "runtimeTargetResolutionRequired",
                            "runtimeEventPostingNotObserved",
                        ],
                        "path": (
                            f"templateActionMapAudio.audioActions[{action_index}]"
                            f".eventBindings[{binding_index}]"
                        ),
                        "sourcePaths": source_paths,
                        "sourceFingerprint": digest,
                        "evidence": "exactDecodedInteractiveTemplateActionAudio",
                    })
            for action_index, action in enumerate(embedded_action_audio):
                if not isinstance(action, dict):
                    continue
                fields = action.get("fields") if isinstance(action.get("fields"), dict) else {}
                stop_on_release = fields.get("stopOnRelease")
                target = fields.get("target") or fields.get("position")
                for binding_index, binding in enumerate(action.get("eventBindings") or []):
                    if not isinstance(binding, dict):
                        continue
                    event_name = str(binding.get("eventName") or "").strip()
                    if not event_name or event_name in template_action_events:
                        continue
                    template_action_events.add(event_name)
                    _append_context(contexts, seen, event_name, {
                        "kind": "interactiveEmbeddedActionAudio",
                        "table": "InteractiveData",
                        "semanticRole": "interactiveEmbeddedActionAudioRequest",
                        "ownerKind": "interactiveEntityConfig",
                        "ownerId": owner_id,
                        "interactiveTemplateIds": template_ids,
                        "interactiveTemplatePath": template_path,
                        "interactiveConsumerIds": consumer_ids,
                        "templateAssociationStatus": association_status,
                        "interactiveTableSourcePaths": table_source_paths,
                        "interactiveTableSha256": table_source_fingerprint,
                        "componentResolutionStatus": "containingSerializedFieldUnresolved",
                        "actionMapOffset": action.get("actionMapOffset"),
                        "actionMapListCounts": action.get("actionMapListCounts"),
                        "audioAction": action.get("action"),
                        "audioActionRole": binding.get("role"),
                        "audioSourceField": binding.get("sourceField"),
                        "actionMapRole": action.get("actionMapRole"),
                        "actionLocalId": action.get("localId"),
                        "actionUid": action.get("uid"),
                        "actionNextId": action.get("nextId"),
                        "actionUnionTag": action.get("unionTag"),
                        "actionSerializedMemberCount": action.get("serializedMemberCount"),
                        "actionRecordOffset": action.get("recordOffset"),
                        "actionPayloadOffset": action.get("payloadOffset"),
                        "stopOnRelease": (
                            stop_on_release.get("value")
                            if isinstance(stop_on_release, dict)
                            else None
                        ),
                        "targetBindingKind": (
                            target.get("bindingKind") if isinstance(target, dict) else None
                        ),
                        "targetParamSource": (
                            target.get("paramSource") if isinstance(target, dict) else None
                        ),
                        "targetParameterKind": (
                            "target" if "target" in fields else "position"
                        ),
                        "triggerRequestEvidence": [
                            "uniqueEmbeddedActionSerializedMapBoundary",
                            "exactPhysicalActionListMembership",
                            "exactTypedAudioActionPayload",
                        ],
                        "triggerRuntimeActivationStatuses": [
                            "runtimeActionActivationUnobserved",
                            "runtimeTargetResolutionRequired",
                            "runtimeEventPostingNotObserved",
                        ],
                        "path": (
                            f"embeddedActionMapAudioActions[{action_index}]"
                            f".eventBindings[{binding_index}]"
                        ),
                        "sourcePaths": source_paths,
                        "sourceFingerprint": digest,
                        "evidence": "exactDecodedInteractiveEmbeddedActionAudio",
                    })
            for property_map_index, property_map in enumerate(standalone_property_maps):
                if not isinstance(property_map, dict):
                    continue
                for property_index, row in enumerate(property_map.get("audioPropertyRows") or []):
                    if not isinstance(row, dict):
                        continue
                    property_key = str(row.get("key") or "")
                    for event_index, event_id in enumerate(row.get("events") or []):
                        event_name = str(event_id or "").strip()
                        if (
                            not event_name
                            or event_name in component_property_events
                            or event_name in template_config_events
                            or event_name in template_action_events
                        ):
                            continue
                        _append_context(contexts, seen, event_name, {
                            "kind": "interactivePropertyMapAudio",
                            "table": "InteractiveData",
                            "semanticRole": "interactiveAuthoredAudioProperty",
                            "ownerKind": "interactiveEntityConfig",
                            "ownerId": owner_id,
                            "interactiveTemplateIds": template_ids,
                            "interactiveTemplatePath": template_path,
                            "interactiveConsumerIds": consumer_ids,
                            "templateAssociationStatus": association_status,
                            "interactiveTableSourcePaths": table_source_paths,
                            "interactiveTableSha256": table_source_fingerprint,
                            "componentResolutionStatus": "containingComponentUnresolved",
                            "propertyMapOffset": property_map.get("propertyMapOffset"),
                            "propertyMapEndOffset": property_map.get("propertyMapEndOffset"),
                            "audioPropertyKey": property_key,
                            "triggerRequestEvidence": ["exactDecodedInteractiveAudioPropertyMap"],
                            "triggerRuntimeActivationStatuses": [
                                "runtimePropertyConsumerUnresolved",
                                "runtimeEventPostingNotObserved",
                            ],
                            "path": (
                                f"standaloneAudioPropertyMaps[{property_map_index}]"
                                f".audioPropertyRows[{property_index}].events[{event_index}]"
                            ),
                            "sourcePaths": source_paths,
                            "sourceFingerprint": digest,
                            "evidence": "exactDecodedMemoryPackInteractivePropertyMap",
                        })
    return dict(contexts)
