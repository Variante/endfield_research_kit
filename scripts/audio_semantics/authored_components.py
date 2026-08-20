"""Authored PhysicsAudio and ModelViewState audio recovery."""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from . import identifiers
from .context_utils import append_context as _append_context
from .context_utils import normalize_posix


if __package__ == "scripts.audio_semantics":
    from scripts.story_builder.interactive_binary import (
        decode_interactive_table,
        decode_model_view_state_controller,
        find_physics_audio_components,
    )
elif __package__ == "audio_semantics":
    from story_builder.interactive_binary import (
        decode_interactive_table,
        decode_model_view_state_controller,
        find_physics_audio_components,
    )
else:  # pragma: no cover - only package imports are supported.
    raise ImportError(
        "import as scripts.audio_semantics.authored_components or "
        "audio_semantics.authored_components"
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
    StreamingAssets/Persistent mirrors must agree byte-for-byte before either
    table or template data is accepted.
    """
    if component_decoder is None or table_decoder is None:
        component_decoder = component_decoder or find_physics_audio_components
        table_decoder = table_decoder or decode_interactive_table

    source_roots = ("StreamingAssets", "Persistent")
    table_paths = [
        export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
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
            path = export_root / "structured" / source_root / Path(*pure_path.parts)
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
    export_root: Path,
    *,
    controller_decoder: Any | None = None,
    table_decoder: Any | None = None,
) -> dict[str, Any]:
    """Recover exact ModelView state Event, position, RTPC, and spatial rows.

    The controller decoder must consume the complete MemoryPack object before
    any audio member is accepted. InteractiveData joins are exact serialized
    controller-id references, but their property slot is not yet decoded; they
    therefore remain authored template associations rather than runtime owners.
    """
    if controller_decoder is None or table_decoder is None:
        controller_decoder = controller_decoder or decode_model_view_state_controller
        table_decoder = table_decoder or decode_interactive_table

    source_roots = ("StreamingAssets", "Persistent")
    controller_rel = PurePosixPath(
        "Data/Json/Interactive/ModelViewStateControllerData"
    )
    failures: list[dict[str, Any]] = []
    physical_files = 0
    files_by_name: dict[str, list[tuple[str, Path, bytes, str]]] = defaultdict(list)
    for source_root in source_roots:
        directory = export_root / "structured" / source_root / Path(*controller_rel.parts)
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                data = path.read_bytes()
            except OSError as exc:
                failures.append({"source": normalize_posix(path.relative_to(export_root)), "error": str(exc)})
                continue
            physical_files += 1
            files_by_name[path.name].append(
                (source_root, path, data, hashlib.sha256(data).hexdigest())
            )

    boundary = (
        "Exact complete ModelViewStateControllerData decoding proves authored state-bound "
        "Event/position requests and RTPC/spatial controls, including behavior time and the "
        "model/layer/state/behavior owner chain. InteractiveData matches prove only an exact "
        "serialized controller-id association because the containing property slot is unresolved. "
        "State entry, behavior execution, Event posting, RTPC/spatial application, and Wwise "
        "branch playback were not observed. CustomAudioId strings remain unresolved controls, "
        "not Wwise Events."
    )
    empty = {
        "status": "unavailable" if not files_by_name else "failed",
        "controllerPhysicalFiles": physical_files,
        "controllerLogicalFiles": len(files_by_name),
        "controllersDecoded": 0,
        "controllersWithAudio": 0,
        "audioBehaviorCount": 0,
        "eventBehaviorCount": 0,
        "positionEventBehaviorCount": 0,
        "positionDirectEventBehaviorCount": 0,
        "positionCustomStateSwitchCount": 0,
        "positionEntityStateSwitchCount": 0,
        "rtpcBehaviorCount": 0,
        "spatialBehaviorCount": 0,
        "customAudioControlCount": 0,
        "controllersWithTemplateAssociations": 0,
        "templateAssociationCount": 0,
        "interactiveConsumerIdentityCount": 0,
        "failureSamples": failures[:16],
        "evidenceBoundary": boundary,
    }
    if not files_by_name:
        return {
            "eventContexts": {}, "rtpcParameters": [], "spatialControls": [],
            "customAudioControls": [], "positionedControls": [],
            "stats": empty, "evidenceBoundary": boundary,
        }

    decoded_controllers: list[dict[str, Any]] = []
    for file_name, versions in sorted(files_by_name.items()):
        decoded_versions: list[tuple[str, Path, str, dict[str, Any]]] = []
        for source_root, path, data, digest in versions:
            try:
                decoded = controller_decoder(data)
            except (UnicodeDecodeError, struct.error, ValueError) as exc:
                if len(failures) < 16:
                    failures.append({
                        "source": normalize_posix(path.relative_to(export_root)),
                        "error": str(exc),
                        "sha256": digest,
                    })
                continue
            if not isinstance(decoded, dict):
                if len(failures) < 16:
                    failures.append({
                        "source": normalize_posix(path.relative_to(export_root)),
                        "error": "ModelView decoder returned no object",
                    })
                continue
            decoded_versions.append((source_root, path, digest, decoded))
        if len(decoded_versions) != len(versions):
            continue

        def audio_projection(decoded: dict[str, Any]) -> str:
            rows = []
            for raw in decoded.get("audioBehaviors") or []:
                if not isinstance(raw, dict):
                    continue
                rows.append({
                    key: value for key, value in raw.items()
                    if key not in {"sourceOffset", "endOffset", "byteLength"}
                })
            return json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

        projections = {audio_projection(row[3]) for row in decoded_versions}
        if len(projections) != 1:
            if len(failures) < 16:
                failures.append({
                    "source": normalize_posix(controller_rel / file_name),
                    "error": "StreamingAssets/Persistent decoded audio projections differ",
                    "sha256": sorted(row[2] for row in decoded_versions),
                })
            continue
        preferred = next(
            (row for row in decoded_versions if row[0] == "Persistent"),
            decoded_versions[0],
        )
        decoded = preferred[3]
        decoded_controllers.append({
            "fileName": file_name,
            "controllerId": str(decoded.get("modelId") or Path(file_name).stem),
            "decoded": decoded,
            "sourcePaths": [
                normalize_posix(path.relative_to(export_root))
                for _root, path, _digest, _decoded in decoded_versions
            ],
            "sourceRoots": [row[0] for row in decoded_versions],
            "sourceFingerprints": sorted(set(row[2] for row in decoded_versions)),
        })

    # Recover the bounded external association without pretending the still
    # unresolved InteractiveData property slot is a runtime activation edge.
    references_by_controller: dict[str, set[str]] = defaultdict(set)
    template_paths_by_id: dict[str, str] = {}
    consumers_by_template: dict[str, list[str]] = defaultdict(list)
    table_source_paths: list[str] = []
    table_sha256 = ""
    table_versions: list[tuple[str, Path, bytes, str]] = []
    for source_root in source_roots:
        table_path = export_root / "structured" / source_root / "Data/Json/Interactive/InteractiveTable.json"
        if not table_path.is_file():
            continue
        try:
            data = table_path.read_bytes()
        except OSError as exc:
            if len(failures) < 16:
                failures.append({"source": normalize_posix(table_path.relative_to(export_root)), "error": str(exc)})
            continue
        table_versions.append((source_root, table_path, data, hashlib.sha256(data).hexdigest()))
    if table_versions and len({row[3] for row in table_versions}) == 1:
        try:
            table = table_decoder(table_versions[0][2])
        except (UnicodeDecodeError, struct.error, ValueError) as exc:
            table = None
            if len(failures) < 16:
                failures.append({
                    "source": normalize_posix(table_versions[0][1].relative_to(export_root)),
                    "error": str(exc),
                })
        if isinstance(table, dict):
            table_source_paths = [
                normalize_posix(path.relative_to(export_root))
                for _root, path, _data, _digest in table_versions
            ]
            table_sha256 = table_versions[0][3]
            template_paths_by_id = {
                str(key): normalize_posix(str(value or ""))
                for key, value in (table.get("coreTemplatePaths") or {}).items()
            }
            for consumer_id, template_id in (table.get("objectToTemplate") or {}).items():
                consumers_by_template[str(template_id)].append(str(consumer_id))
            anchors = {
                row["controllerId"]: struct.pack("<I", len(row["controllerId"].encode("utf-8")))
                + row["controllerId"].encode("utf-8")
                for row in decoded_controllers
                if row.get("controllerId")
            }
            for template_id, template_path in sorted(template_paths_by_id.items()):
                pure_path = PurePosixPath(template_path)
                if (
                    pure_path.is_absolute()
                    or ".." in pure_path.parts
                    or not template_path.startswith("Data/Json/Interactive/InteractiveData/")
                ):
                    continue
                candidates: list[bytes] = []
                for source_root in reversed(source_roots):
                    path = export_root / "structured" / source_root / Path(*pure_path.parts)
                    if path.is_file():
                        try:
                            candidates.append(path.read_bytes())
                        except OSError:
                            pass
                if not candidates:
                    continue
                # Associations must agree semantically across available mirrors.
                matches = [
                    {controller_id for controller_id, anchor in anchors.items() if data.find(anchor) >= 0}
                    for data in candidates
                ]
                if len({tuple(sorted(row)) for row in matches}) != 1:
                    if len(failures) < 16:
                        failures.append({
                            "source": template_path,
                            "error": "StreamingAssets/Persistent controller-id reference sets differ",
                        })
                    continue
                for controller_id in matches[0]:
                    references_by_controller[controller_id].add(template_id)
    elif table_versions:
        if len(failures) < 16:
            failures.append({
                "source": "Data/Json/Interactive/InteractiveTable.json",
                "error": "StreamingAssets/Persistent content hashes differ",
                "sha256": sorted(row[3] for row in table_versions),
            })

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    rtpc_parameters: list[dict[str, Any]] = []
    spatial_controls: list[dict[str, Any]] = []
    custom_controls: list[dict[str, Any]] = []
    positioned_controls: list[dict[str, Any]] = []
    tag_counts: Counter[int] = Counter()
    controllers_with_audio = 0
    associated_controllers: set[str] = set()
    associated_templates: set[str] = set()
    associated_consumers: set[str] = set()
    for controller in decoded_controllers:
        decoded = controller["decoded"]
        audio_rows = [row for row in decoded.get("audioBehaviors") or [] if isinstance(row, dict)]
        if audio_rows:
            controllers_with_audio += 1
        controller_id = str(controller.get("controllerId") or "")
        template_ids = sorted(references_by_controller.get(controller_id, set()))
        consumer_ids = sorted({
            consumer
            for template_id in template_ids
            for consumer in consumers_by_template.get(template_id, [])
        })
        if audio_rows and template_ids:
            associated_controllers.add(controller_id)
            associated_templates.update(template_ids)
            associated_consumers.update(consumer_ids)
        common = {
            "ownerId": controller_id,
            "controllerId": controller_id,
            "ownerKind": "modelViewStateController",
            "sourceFile": str(controller.get("fileName") or ""),
            "sourcePaths": controller.get("sourcePaths") or [],
            "sourceRoots": controller.get("sourceRoots") or [],
            "sourceFingerprints": controller.get("sourceFingerprints") or [],
            "schemaMappingId": str(decoded.get("schemaMappingId") or ""),
            "runtimeMappingId": str(decoded.get("runtimeMappingId") or ""),
            "schemaStatus": str(decoded.get("schemaStatus") or ""),
            "interactiveTemplateIds": template_ids,
            "interactiveTemplatePaths": [template_paths_by_id.get(value, "") for value in template_ids],
            "interactiveConsumerIds": consumer_ids,
            "interactiveTableSourcePaths": table_source_paths,
            "interactiveTableSha256": table_sha256,
            "templateAssociationStatus": (
                "exactSerializedControllerIdReferencePropertyUnresolved"
                if template_ids else "unlinked"
            ),
            "runtimeActivationStatus": "modelViewStateBehaviorExecutionNotObserved",
        }
        for row in audio_rows:
            tag = int(row.get("unionTag") or 0)
            tag_counts[tag] += 1
            row_common = {
                **common,
                "modelAnimatorIndex": row.get("modelAnimatorIndex"),
                "modelAnimatorName": str(row.get("modelAnimatorName") or ""),
                "layerIndex": row.get("layerIndex"),
                "layerFsmIndex": row.get("layerFsmIndex"),
                "layerName": str(row.get("layerName") or ""),
                "stateIndex": row.get("stateIndex"),
                "stateName": str(row.get("stateName") or ""),
                "stateType": row.get("stateType"),
                "behaviorIndex": row.get("behaviorIndex"),
                "behaviorTag": tag,
                "behaviorTagHex": str(row.get("unionTagHex") or f"0x{tag:04x}"),
                "serializedMemberCount": row.get("memberCount"),
                "behaviorType": row.get("behaviorType"),
                "behaviorKind": str(row.get("behaviorKind") or ""),
                "behaviorTime": row.get("time"),
                "timeFlowSwitch": row.get("timeFlowSwitch"),
                "canLoopActive": row.get("canLoopActive"),
                "needForceExecute": row.get("needForceExecute"),
                "normalizedTimeFlowBasedActive": row.get("normalizedTimeFlowBasedActive"),
                "sourceOffset": row.get("sourceOffset"),
                "behaviorEndOffset": row.get("endOffset"),
                "semanticPath": (
                    f"modelAnimatorDatas[{row.get('modelAnimatorIndex')}].layerFsmDatas"
                    f"[{row.get('layerIndex')}].stateDatas[{row.get('stateIndex')}]"
                    f".behaviors[{row.get('behaviorIndex')}]"
                ),
            }
            if tag in (1, 2):
                event_fields = {
                    **row_common,
                    "audioNodeName": str(row.get("audioNodeName") or ""),
                    "customAudioId": str(row.get("customAudioId") or ""),
                    "eAudioTriggerState": row.get("eAudioTriggerState"),
                    "isCustom": bool(row.get("isCustom")),
                    "isDirectlyPlay": bool(row.get("isDirectlyPlay")),
                    "normalAudioId": row.get("normalAudioId"),
                    "stopOnEnd": bool(row.get("stopOnEnd")),
                    "transitionTime": row.get("transitionTime"),
                }
                # Positioned data has a different native branch model from
                # normal tag-0x0001 audio.  A direct position request is the
                # only tag-0x0002 row that owns a normalAudioId Event.  Both
                # control branches retain their authored values but never
                # enter eventContexts or the Event/media graph.
                if tag == 2 and row.get("isDirectlyPlay"):
                    signed_id = row.get("normalAudioId")
                    if not isinstance(signed_id, int) or isinstance(signed_id, bool) or signed_id == 0:
                        positioned_controls.append({
                            **event_fields,
                            "kind": "modelViewStatePositionedEventMissingAudioId",
                            "semanticRole": "authoredModelViewStatePositionedEventRequestMissingAudioId",
                            "wwiseEventStatus": "unresolvedMissingNormalAudioId",
                            "controlBranch": "directPositionEvent",
                            "evidence": "exactDecodedModelViewStatePositionedDirectBranch",
                        })
                        continue
                elif tag == 2 and row.get("isCustom"):
                    positioned_controls.append({
                        **event_fields,
                        "kind": "modelViewStatePositionedCustomStateSwitch",
                        "controlValue": str(row.get("customAudioId") or ""),
                        "controlBranch": "customStateSwitch",
                        "semanticRole": "unresolvedModelViewStatePositionedCustomAudioId",
                        "wwiseEventStatus": "notPromotedToEvent",
                        "nativeControlMethod": "TrySwitchAudioCustomState",
                        "evidence": "exactDecodedModelViewStatePositionedCustomBranch",
                    })
                    continue
                elif tag == 2:
                    positioned_controls.append({
                        **event_fields,
                        "kind": "modelViewStatePositionedEntityStateSwitch",
                        "controlValue": row.get("eAudioTriggerState"),
                        "stateValue": row.get("eAudioTriggerState"),
                        "controlBranch": "entityStateSwitch",
                        "modelLevel": 1,
                        "semanticRole": "unresolvedModelViewStatePositionedEntityAudioState",
                        "wwiseEventStatus": "notPromotedToEvent",
                        "nativeControlMethod": "TrySwitchAudioState",
                        "nativeControlChain": [
                            "TrySwitchAudioState",
                            "InteractiveAudioComponent.SwitchAudioState",
                            "InteractiveAudioComponent._SwitchState",
                        ],
                        "evidence": "exactDecodedModelViewStatePositionedEntityStateBranch",
                    })
                    continue
                if row.get("isCustom"):
                    custom_controls.append({
                        **event_fields,
                        "kind": "modelViewStateCustomAudioControl",
                        "controlValue": str(row.get("customAudioId") or ""),
                        "semanticRole": "unresolvedModelViewCustomAudioId",
                        "wwiseEventStatus": "notPromotedToEvent",
                        "evidence": "exactDecodedModelViewStateCustomAudioBranch",
                    })
                    continue
                signed_id = row.get("normalAudioId")
                if not isinstance(signed_id, int) or isinstance(signed_id, bool) or signed_id == 0:
                    continue
                event_hash = signed_id & 0xFFFFFFFF
                _append_context(contexts, seen, identifiers.event_hash_context_key(event_hash), {
                    **event_fields,
                    "kind": (
                        "modelViewStateAudioEvent" if tag == 1
                        else "modelViewStatePositionAudioEvent"
                    ),
                    "semanticRole": (
                        "authoredModelViewStateEventRequest" if tag == 1
                        else "authoredModelViewStatePositionedEventRequest"
                    ),
                    "signedValue": signed_id,
                    "eventHash": event_hash,
                    "eventHex": f"0x{event_hash:08x}",
                    "confidence": "direct",
                    "evidence": "exactDecodedModelViewStateAudioBehavior",
                    "triggerRequestEvidence": [
                        "exactModelViewStateBehaviorUnion",
                        "exactModelLayerStateBehaviorOwnerChain",
                    ],
                    "triggerRuntimeActivationStatuses": [
                        "modelViewStateEntryAndBehaviorTimeRequired",
                        "modelViewStateBehaviorExecutionNotObserved",
                    ],
                })
            elif tag == 3:
                rtpc_parameters.append({
                    **row_common,
                    "kind": "modelViewStateRtpcParameter",
                    "parameterName": str(row.get("audioRTPCValue") or ""),
                    "audioNodeName": str(row.get("audioNodeName") or ""),
                    "setValue": row.get("audioRTPCSetValue"),
                    "rtpcBehaviourType": row.get("rtpcBehaviourType"),
                    "continuousTick": row.get("continuousTick"),
                    "dependBlackBoard": row.get("dependBlackBoard"),
                    "dependFloatKey": str(row.get("dependFloatKey") or ""),
                    "semanticRole": "authoredModelViewStateRtpcControl",
                    "wwiseEventStatus": "notApplicable",
                    "evidence": "exactDecodedModelViewStateRtpcBehavior",
                })
            elif tag == 4:
                spatial_controls.append({
                    **row_common,
                    "kind": "modelViewStateSpatialAudioControl",
                    "continuous": row.get("continuous"),
                    "dependBlackBoard": row.get("dependBlackBoard"),
                    "dependFloatKey": str(row.get("dependFloatKey") or ""),
                    "directSet": row.get("directSet"),
                    "targetClosePercentage": row.get("targetClosePercentage"),
                    "totalTime": row.get("totalTime"),
                    "semanticRole": "authoredModelViewStateSpatialControl",
                    "wwiseEventStatus": "notApplicable",
                    "evidence": "exactDecodedModelViewStateSpatialAudioBehavior",
                })

    # Keep the historical normal-event stats tag-0x0001-only. Positioned
    # direct Events share eventContexts for downstream Event joins, but must
    # be counted independently from normal ModelView semantics.
    normal_event_context_count = sum(
        1 for rows in contexts.values() for row in rows
        if isinstance(row, dict) and row.get("behaviorTag") == 1
    )
    normal_event_hash_count = sum(
        any(isinstance(row, dict) and row.get("behaviorTag") == 1 for row in rows)
        for rows in contexts.values()
    )
    stats = {
        "status": "complete" if not failures else "partial",
        "controllerPhysicalFiles": physical_files,
        "controllerLogicalFiles": len(files_by_name),
        "controllersDecoded": len(decoded_controllers),
        "controllersWithAudio": controllers_with_audio,
        "audioBehaviorCount": sum(tag_counts.values()),
        "eventBehaviorCount": tag_counts.get(1, 0),
        "positionEventBehaviorCount": tag_counts.get(2, 0),
        "rtpcBehaviorCount": tag_counts.get(3, 0),
        "spatialBehaviorCount": tag_counts.get(4, 0),
        "normalEventContextCount": normal_event_context_count,
        "distinctNormalEventHashes": normal_event_hash_count,
        "customAudioControlCount": len(custom_controls),
        "positionDirectEventBehaviorCount": sum(
            1 for rows in contexts.values() for row in rows
            if isinstance(row, dict) and row.get("behaviorTag") == 2
        ),
        "positionCustomStateSwitchCount": sum(
            row.get("controlBranch") == "customStateSwitch" for row in positioned_controls
        ),
        "positionEntityStateSwitchCount": sum(
            row.get("controlBranch") == "entityStateSwitch" for row in positioned_controls
        ),
        "positionedControlCount": len(positioned_controls),
        "controllersWithTemplateAssociations": len(associated_controllers),
        "templateAssociationCount": len(associated_templates),
        "interactiveConsumerIdentityCount": len(associated_consumers),
        "failureSamples": failures[:16],
        "evidenceBoundary": boundary,
    }
    return {
        "eventContexts": dict(contexts),
        "rtpcParameters": rtpc_parameters,
        "spatialControls": spatial_controls,
        "customAudioControls": custom_controls,
        "positionedControls": positioned_controls,
        "stats": stats,
        "evidenceBoundary": boundary,
    }
