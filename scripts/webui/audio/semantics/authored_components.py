"""Authored PhysicsAudio and ModelViewState audio recovery."""

from __future__ import annotations
from scripts.source_paths import ExportLayout

import hashlib
import json
import struct
from collections import Counter, defaultdict
from functools import partial
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.webui.audio.semantics import identifiers
from scripts.webui.audio.semantics.context_utils import append_context as _append_context
from scripts.webui.audio.semantics.context_utils import normalize_posix


from scripts.game_data.string_pool import export_string_pool
from scripts.game_data.interactive_binary import (
    decode_interactive_table,
    find_physics_audio_components,
)


def collect_physics_audio_semantics(
    export_root: Path,
    *,
    component_decoder: Any | None = None,
    table_decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact PhysicsAudio Event/RTPC contexts and consumer aliases.

    ``InteractiveTable`` is the ownership boundary: its core-template path
    identifies the one serialized definition, while ``interactiveDataDict``
    identifies every configured object id that consumes that definition.
    Both are read from the export's single effective game/ tree.
    """
    if component_decoder is None or table_decoder is None:
        strings = export_string_pool(ExportLayout(export_root).game / "Json")
        component_decoder = component_decoder or partial(find_physics_audio_components, strings=strings)
        table_decoder = table_decoder or partial(decode_interactive_table, strings=strings)

    source_roots = ("game",)
    table_paths = [
        ExportLayout(export_root).game / "Json/Interactive/InteractiveTable.json"
        for source_root in source_roots
    ]
    table_versions: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    table_data: dict[str, bytes] = {}
    failures: list[dict[str, Any]] = []
    for source_root, path in zip(source_roots, table_paths):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            failures.append({"source": normalize_posix(path.relative_to(export_root)), "error": str(exc)})
            continue
        digest = hashlib.sha256(data).hexdigest()
        table_versions[digest].append((source_root, path))
        table_data[digest] = data

    empty_stats = {
        "status": "unavailable" if not table_versions else "failed",
        "interactiveTablePhysicalFiles": sum(len(rows) for rows in table_versions.values()),
        "interactiveTableContentVersions": len(table_versions),
        "templateDefinitionsScanned": 0,
        "templatePhysicalFiles": 0,
        "physicsAudioDefinitions": 0,
        "physicsAudioComponents": 0,
        "physicsAudioEventContexts": 0,
        "distinctPhysicsAudioEvents": 0,
        "physicsAudioRtpcControls": 0,
        "physicsAudioConsumerIdentities": 0,
        "physicsAudioAliasIdentities": 0,
        "failureSamples": failures[:16],
    }
    boundary = (
        "The exact tag-0x00BE/member-1, 21-key PhysicsAudio dynamic-property map and "
        "InteractiveTable ownership/alias rows prove authored movement, impact, rotation, "
        "and RTPC configuration. They do not prove component instantiation, physics state "
        "changes, RTPC updates, Event posting, or a selected Wwise playback branch."
    )
    if not table_versions:
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }
    if len(table_versions) != 1:
        empty_stats["status"] = "conflictingMirrors"
        empty_stats["failureSamples"] = [{
            "source": "InteractiveTable.json",
            "error": "StreamingAssets/Persistent content hashes differ",
            "sha256": sorted(table_versions),
        }]
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }

    table_sha256 = next(iter(table_versions))
    table_sources = table_versions[table_sha256]
    table_source_paths = [
        normalize_posix(path.relative_to(export_root)) for _root, path in table_sources
    ]
    try:
        table = table_decoder(table_data[table_sha256])
    except (UnicodeDecodeError, struct.error, ValueError) as exc:
        empty_stats["failureSamples"] = [{
            "source": table_source_paths[0], "error": str(exc), "sha256": table_sha256,
        }]
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }
    if not isinstance(table, dict):
        empty_stats["failureSamples"] = [{
            "source": table_source_paths[0], "error": "InteractiveTable decoder returned no object",
        }]
        return {
            "eventContexts": {}, "rtpcParameters": [], "definitions": [],
            "stats": empty_stats, "evidenceBoundary": boundary,
        }

    core_paths = table.get("coreTemplatePaths") or {}
    object_to_template = table.get("objectToTemplate") or {}
    consumers_by_template: dict[str, list[str]] = defaultdict(list)
    for consumer_id, template_id in object_to_template.items():
        consumers_by_template[str(template_id)].append(str(consumer_id))

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    rtpc_parameters: list[dict[str, Any]] = []
    definitions: list[dict[str, Any]] = []
    template_physical_files = 0
    template_definitions_scanned = 0
    component_count = 0
    consumer_ids: set[str] = set()
    alias_ids: set[str] = set()
    accepted_template_versions = 0

    for template_id, raw_template_path in sorted(core_paths.items()):
        template_path = normalize_posix(str(raw_template_path or ""))
        pure_path = PurePosixPath(template_path)
        if (
            pure_path.is_absolute()
            or ".." in pure_path.parts
            or not template_path.startswith("Data/Json/Interactive/InteractiveData/")
        ):
            continue
        existing: list[tuple[str, Path, bytes, str]] = []
        for source_root in source_roots:
            path = ExportLayout(export_root).game_file(template_path)
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError as exc:
                if len(failures) < 16:
                    failures.append({"source": normalize_posix(path.relative_to(export_root)), "error": str(exc)})
                continue
            existing.append((source_root, path, data, hashlib.sha256(data).hexdigest()))
        if not existing:
            continue
        template_definitions_scanned += 1
        template_physical_files += len(existing)
        version_hashes = {digest for _root, _path, _data, digest in existing}
        if len(version_hashes) != 1:
            relevant_components = False
            relevant_decode_error = ""
            for _source_root, _path, version_data, _digest in existing:
                try:
                    relevant_components = bool(component_decoder(version_data)) or relevant_components
                except (UnicodeDecodeError, struct.error, ValueError) as exc:
                    relevant_decode_error = str(exc)
            # Overlay differences in unrelated Interactive definitions do not
            # weaken this bounded PhysicsAudio audit.  A differing definition
            # is a blocker only when at least one version contains the exact
            # PhysicsAudio anchor or fails after reaching that anchor.
            if (relevant_components or relevant_decode_error) and len(failures) < 16:
                failures.append({
                    "source": template_path,
                    "error": (
                        "StreamingAssets/Persistent PhysicsAudio template content hashes differ"
                        + (f": {relevant_decode_error}" if relevant_decode_error else "")
                    ),
                    "sha256": sorted(version_hashes),
                })
            continue
        template_sha256 = existing[0][3]
        source_paths = [
            normalize_posix(path.relative_to(export_root)) for _root, path, _data, _digest in existing
        ]
        try:
            components = component_decoder(existing[0][2])
        except (UnicodeDecodeError, struct.error, ValueError) as exc:
            if len(failures) < 16:
                failures.append({
                    "source": source_paths[0], "error": str(exc), "sha256": template_sha256,
                })
            continue
        if not isinstance(components, list) or not components:
            continue
        accepted_template_versions += 1
        configured_consumers = sorted(set(consumers_by_template.get(str(template_id), [])))
        consumer_ids.update(configured_consumers)
        alias_ids.update(value for value in configured_consumers if value != str(template_id))
        for component_occurrence_index, component in enumerate(components):
            if not isinstance(component, dict):
                continue
            component_count += 1
            properties = [row for row in component.get("properties") or [] if isinstance(row, dict)]
            definition = {
                "kind": "physicsAudioDefinition",
                "definitionOwnerId": str(template_id),
                "templatePath": template_path,
                "consumerIds": configured_consumers,
                "consumerAliasIds": [value for value in configured_consumers if value != str(template_id)],
                "componentOccurrenceIndex": component_occurrence_index,
                "componentTag": component.get("unionTag"),
                "componentTagHex": str(component.get("unionTagHex") or ""),
                "serializedMemberCount": component.get("memberCount"),
                "propertyCount": component.get("propertyCount"),
                "sourceOffset": component.get("sourceOffset"),
                "propertyMapOffset": component.get("propertyMapOffset"),
                "endOffset": component.get("endOffset"),
                "sourcePaths": source_paths,
                "sourceRoots": [root for root, _path, _data, _digest in existing],
                "sourceSha256": template_sha256,
                "interactiveTableSourcePaths": table_source_paths,
                "interactiveTableSha256": table_sha256,
                "schemaMappingId": str(component.get("schemaMappingId") or ""),
                "runtimeMappingId": str(component.get("runtimeMappingId") or ""),
                "schemaStatus": str(component.get("schemaStatus") or ""),
                "properties": properties,
            }
            definitions.append(definition)
            common = {
                "ownerId": str(template_id),
                "definitionOwnerId": str(template_id),
                "ownerKind": "interactivePhysicsAudioDefinition",
                "consumerIds": configured_consumers,
                "consumerAliasIds": definition["consumerAliasIds"],
                "confidence": "direct",
                "table": "InteractiveTable",
                "templatePath": template_path,
                "componentOccurrenceIndex": component_occurrence_index,
                "componentTag": component.get("unionTag"),
                "componentTagHex": str(component.get("unionTagHex") or ""),
                "serializedMemberCount": component.get("memberCount"),
                "propertyCount": component.get("propertyCount"),
                "sourceOffset": component.get("sourceOffset"),
                "componentEndOffset": component.get("endOffset"),
                "sourcePaths": source_paths,
                "sourceRoots": definition["sourceRoots"],
                "sourceFingerprint": template_sha256,
                "sourceSha256": template_sha256,
                "interactiveTableSourcePaths": table_source_paths,
                "interactiveTableSha256": table_sha256,
                "schemaMappingId": definition["schemaMappingId"],
                "runtimeMappingId": definition["runtimeMappingId"],
                "schemaStatus": definition["schemaStatus"],
                "runtimeActivationStatus": "physicsAudioRuntimeExecutionNotObserved",
            }
            for row in properties:
                value = row.get("value")
                event_role = str(row.get("eventRole") or "")
                rtpc_role = str(row.get("rtpcRole") or "")
                row_common = {
                    **common,
                    "authoredProperty": str(row.get("authoredKey") or ""),
                    "runtimeField": str(row.get("runtimeField") or ""),
                    "propertySourceOffset": row.get("propertySourceOffset", row.get("sourceOffset")),
                    "propertyValueSourceOffset": row.get("valueSourceOffset"),
                    "valueType": row.get("valueType"),
                    "valueTypeName": str(row.get("valueTypeName") or ""),
                    "semanticPath": (
                        "PhysicsAudioComponentData.propertyList["
                        + str(row.get("authoredKey") or "")
                        + "]"
                    ),
                }
                if event_role and isinstance(value, str) and value.strip():
                    event_name = value.strip()
                    _append_context(contexts, seen, event_name, {
                        **row_common,
                        "kind": "physicsAudioComponentEvent",
                        "semanticRole": "authoredInteractivePhysicsAudioEvent",
                        "eventName": event_name,
                        "triggerRole": event_role,
                        "triggerRequestEvidence": [
                            "exactPhysicsAudioComponentDynamicProperty",
                            "exactInteractiveTableTemplateOwnership",
                        ],
                        "triggerRuntimeActivationStatuses": [
                            "physicsAudioComponentInstantiationAndThresholdStateRequired"
                        ],
                    })
                if rtpc_role and isinstance(value, str) and value.strip():
                    rtpc_parameters.append({
                        **row_common,
                        "kind": "physicsAudioRtpcParameter",
                        "parameterName": value.strip(),
                        "controlRole": rtpc_role,
                        "semanticRole": "authoredInteractivePhysicsAudioRtpc",
                        "wwiseEventStatus": "notApplicable",
                        "evidence": "exactPhysicsAudioComponentDynamicProperty",
                    })

    event_context_count = sum(len(rows) for rows in contexts.values())
    stats = {
        "status": "complete" if not failures else "partial",
        "interactiveTablePhysicalFiles": sum(len(rows) for rows in table_versions.values()),
        "interactiveTableContentVersions": len(table_versions),
        "interactiveTableSourcePaths": table_source_paths,
        "interactiveTableSha256": table_sha256,
        "coreTemplateCount": int(table.get("coreTemplateCount") or len(core_paths)),
        "interactiveDataCount": int(table.get("interactiveDataCount") or len(object_to_template)),
        "templateDefinitionsScanned": template_definitions_scanned,
        "templatePhysicalFiles": template_physical_files,
        "physicsAudioTemplateVersions": accepted_template_versions,
        "physicsAudioDefinitions": len(definitions),
        "physicsAudioComponents": component_count,
        "physicsAudioEventContexts": event_context_count,
        "distinctPhysicsAudioEvents": len(contexts),
        "physicsAudioRtpcControls": len(rtpc_parameters),
        "physicsAudioConsumerIdentities": len(consumer_ids),
        "physicsAudioAliasIdentities": len(alias_ids),
        "failureSamples": failures[:16],
        "evidenceBoundary": boundary,
    }
    return {
        "eventContexts": dict(contexts),
        "rtpcParameters": rtpc_parameters,
        "definitions": definitions,
        "stats": stats,
        "evidenceBoundary": boundary,
    }


def collect_model_view_state_audio_semantics(
    export_root: Path, *, controller_decoder=None, gameassembly=None, metadata=None,
) -> dict[str, Any]:
    """Retain current stored audio fields; their consumer and playback joins remain open."""
    from scripts.game_data.model_view_state_controller_binary import model_view_operation
    directory = ExportLayout(export_root).game / "Json/Interactive/ModelViewStateControllerData"
    boundary = ("Current native-gated frames preserve stored ModelView audio behavior fields and "
                "model/layer/state owners. Bank IDs and names do not prove an Event, native sink, "
                "activation, or playback; unavailable/refused sources do not establish absence.")
    empty = {"eventContexts": {}, "rtpcParameters": [], "spatialControls": [],
             "customAudioControls": [], "positionedControls": [], "storedBehaviors": [],
             "evidenceBoundary": boundary}
    if controller_decoder is None:
        if not directory.is_dir():
            return dict(empty, stats={"status": "unavailable", "failureSamples": []})
        try:
            with model_view_operation(export_string_pool(ExportLayout(export_root).game / "Json"),
                                      gameassembly=gameassembly, metadata=metadata) as reader:
                return collect_model_view_state_audio_semantics(export_root, controller_decoder=reader)
        except ValueError as error:
            return dict(empty, stats={"status": "unavailable", "failureSamples": [{"error": str(error)}]})
    def sources():
        return {path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(directory.glob("*.json"))}
    before = sources(); failures = []; rows = []; decoded_count = 0; with_audio = 0
    for path, digest in before.items():
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"ModelView source changed while reading: {path}")
        try:
            decoded = controller_decoder(data)
            if (not isinstance(decoded, dict) or decoded.get('endOffset') != len(data)
                    or decoded.get('wholeSchemaExact') is not True
                    or decoded.get('status') != 'exact_current_model_view_frame'):
                raise ValueError('ModelView complete current frame required')
        except (ValueError, struct.error) as error:
            failures.append({"source": normalize_posix(path.relative_to(export_root)),
                             "sha256": digest, "error": str(error)})
            continue
        decoded_count += 1; audio = decoded.get('audioBehaviors') or []; with_audio += bool(audio)
        for row in audio:
            rows.append(dict(row, controllerId=decoded.get('modelId'),
                sourceFile=path.name, sourcePath=normalize_posix(path.relative_to(export_root)),
                sourceSha256=digest, schemaMappingId=decoded.get('schemaMappingId'),
                schemaStatus=decoded.get('schemaStatus'), evidenceBoundary=decoded.get('evidenceBoundary'),
                runtimeMappingId=None, semanticRole='storedModelViewAudioBehavior',
                wwiseEventStatus='unresolvedCurrentConsumer', runtimeActivationStatus='unobserved'))
    if sources() != before:
        raise ValueError('ModelView source set or bytes changed during collection')
    return dict(empty, storedBehaviors=rows, stats={
        "status": 'partial' if failures else 'completeStoredFrames' if before else 'unavailable',
        "controllerPhysicalFiles": len(before), "controllerLogicalFiles": len(before),
        "controllersDecoded": decoded_count, "controllersWithAudio": with_audio,
        "audioBehaviorCount": len(rows), "storedBehaviorCount": len(rows),
        "consumerJoinStatus": 'unresolved', "failureSamples": failures[:16], "evidenceBoundary": boundary})
