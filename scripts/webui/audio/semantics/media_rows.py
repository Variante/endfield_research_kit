"""Media row projection and post-process route annotation.

Builds the compact media rows the Audio page shards, and annotates each row with
its post-process effect chain and trigger/event context. A route is a serialized
relation, not evidence that the media played."""

from __future__ import annotations

import json
from . import event_projection
from . import managed_literals
from collections import defaultdict
from typing import Any, Iterable

MEDIA_DETAIL_FIELDS = (
    "animationCallbackClipResolutions",
    "postProcessProperties",
    "postProcessEffectChain",
    "postProcessBusControls",
    "postProcessAuxSends",
    "postProcessRanges",
    "postProcessBusPaths",
    "postProcessRtpcControls",
)

def split_media_row(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split one media row into its list projection and its detail projection.

    The detail row is empty when the media carries none of the heavy fields, so
    those rows stay complete in the list shard and never trigger a fetch.
    """
    detail_row = {field: row[field] for field in MEDIA_DETAIL_FIELDS if row.get(field)}
    if not detail_row:
        return dict(row), {}
    summary_row = {key: value for key, value in row.items() if key not in detail_row}
    detail_row["id"] = row.get("id")
    return summary_row, detail_row

def _media_route_marker(media: dict[str, Any]) -> str:
    return str(
        media.get("src")
        or media.get("rel")
        or media.get("mediaId")
        or media.get("id")
        or ""
    )

def _media_post_process_routes(
    events: Iterable[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Project exact Event output-bus paths onto their possible media leaves.

    The serialized Wwise graph proves that an Event branch reaches the listed
    output bus.  It does not prove which random/switch/sequence branch was
    selected at runtime, so this projection remains a possible-route summary.
    Bus definitions stay in the top-level HIRC catalog; media rows carry only
    stable IDs and resolution statuses to avoid duplicating plug-in payloads.
    The compact State/RTPC rows below are the exception: they preserve the
    authored control shape that explains a media leaf's processing without
    copying the full Event evidence graph.
    """

    by_marker: dict[str, dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            continue
        selection_status = str(event.get("runtimeSelection") or "unresolved")
        for candidate in event.get("media") or ():
            if not isinstance(candidate, dict):
                continue
            marker = _media_route_marker(candidate)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "routeKeys": set(),
                "busPaths": set(),
                "outputBusIds": set(),
                "effectBusIds": set(),
                "unresolvedBusIds": set(),
                "selectionStatuses": set(),
                "routeStatuses": set(),
                "evidenceKeys": set(),
                "parsedNodeCount": 0,
                "outputBusNodeCount": 0,
                "directEffects": {},
                "directEffectOccurrences": 0,
                "rtpcControls": {},
                "stateControls": {},
                "stateGroupIds": set(),
                "auxSends": {},
                "auxSendOccurrences": 0,
                "auxBusRoutes": {},
                "properties": {},
                "propertyOccurrences": 0,
                "rangedProperties": {},
                "rangedPropertyOccurrences": 0,
                "mediaRelationTypes": set(),
                "mediaSelectionPaths": set(),
                "mediaRootActionIds": set(),
            })
            target["selectionStatuses"].add(selection_status)
            # ``wwiseMediaEvidence`` is copied from the typed HIRC traversal
            # and retains the exact edge shape to this leaf.  Project only the
            # compact relation/path identity here; full container payloads
            # remain lazy Event-detail evidence.
            for media_evidence in candidate.get("wwiseMediaEvidence") or ():
                if not isinstance(media_evidence, dict):
                    continue
                target["mediaRelationTypes"].update(
                    str(value)
                    for value in media_evidence.get("relationTypes") or ()
                    if str(value)
                )
                for raw_path in media_evidence.get("selectionPaths") or ():
                    if not isinstance(raw_path, (list, tuple)):
                        continue
                    path = tuple(str(value) for value in raw_path if str(value))
                    if path:
                        target["mediaSelectionPaths"].add(path)
                for value in media_evidence.get("rootActionIds") or ():
                    try:
                        target["mediaRootActionIds"].add(int(value))
                    except (TypeError, ValueError):
                        continue
            for evidence in event.get("evidence") or ():
                if not isinstance(evidence, dict):
                    continue
                post_process = evidence.get("postProcessSummary") or {}
                if not isinstance(post_process, dict):
                    continue
                try:
                    bank_id = int(evidence.get("bankId") or 0)
                except (TypeError, ValueError):
                    bank_id = 0
                target["evidenceKeys"].add((event_id, bank_id))
                target["parsedNodeCount"] += int(
                    post_process.get("parsedNodeCount") or 0
                )
                for auxiliary_bus in post_process.get("auxiliaryBuses") or ():
                    if not isinstance(auxiliary_bus, dict):
                        continue
                    aux_bus_id = str(
                        auxiliary_bus.get("busIdHex")
                        or auxiliary_bus.get("busId")
                        or ""
                    ).lower()
                    if not aux_bus_id:
                        continue
                    route = {
                        "sendKind": auxiliary_bus.get("sendKind"),
                        "busIdHex": aux_bus_id,
                        "resolutionStatus": auxiliary_bus.get("resolutionStatus"),
                        "busPathIdHexes": [
                            str(value).lower()
                            for value in auxiliary_bus.get("busPathIdHexes") or ()
                            if str(value)
                        ][:16],
                        "busPathResolutionStatus": auxiliary_bus.get(
                            "busPathResolutionStatus"
                        ),
                        "effectBusIdHexes": [
                            str(value).lower()
                            for value in auxiliary_bus.get("effectBusIdHexes") or ()
                            if str(value)
                        ][:16],
                        "unresolvedBusProcessingIdHexes": [
                            str(value).lower()
                            for value in auxiliary_bus.get(
                                "unresolvedBusProcessingIdHexes"
                            ) or ()
                            if str(value)
                        ][:16],
                    }
                    route = {
                        key: value for key, value in route.items()
                        if value not in (None, "", [])
                    }
                    route_key = tuple(
                        (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                        for key, value in sorted(route.items())
                    )
                    target["auxBusRoutes"].setdefault(aux_bus_id, {})[
                        route_key
                    ] = route
                output_buses = list(post_process.get("outputBuses") or ())
                target["outputBusNodeCount"] += int(
                    post_process.get("outputBusNodeCount") or 0
                )
                for effect_node in post_process.get("effectNodes") or ():
                    if not isinstance(effect_node, dict):
                        continue
                    for slot in effect_node.get("effects") or ():
                        if not isinstance(slot, dict):
                            continue
                        effect_id = int(slot.get("effectId") or 0)
                        if not effect_id:
                            continue
                        target["directEffectOccurrences"] += 1
                        effect_id_hex = str(
                            slot.get("effectIdHex") or f"0x{effect_id:08x}"
                        ).lower()
                        effect_row = {
                            "effectIdHex": effect_id_hex,
                            "slotIndex": slot.get("slotIndex"),
                            "objectId": effect_node.get("objectId"),
                            "pluginName": slot.get("pluginName"),
                            "pluginClassIdHex": slot.get("pluginClassIdHex"),
                            "parameterSummary": slot.get("parameterSummary"),
                            "effectBypass": slot.get("effectBypass"),
                            "effectShareSet": slot.get("effectShareSet"),
                            "effectRendered": slot.get("effectRendered"),
                            "resolutionStatus": slot.get("resolutionStatus"),
                        }
                        effect_row = {
                            key: value for key, value in effect_row.items()
                            if value not in (None, "", [])
                        }
                        effect_key = tuple(
                            (key, str(value))
                            for key, value in sorted(effect_row.items())
                        )
                        target["directEffects"].setdefault(effect_key, effect_row)
                for property_node in post_process.get("propertyNodes") or ():
                    if not isinstance(property_node, dict):
                        continue
                    source_type = str(property_node.get("objectTypeLabel") or "")
                    for property_row in property_node.get("properties") or ():
                        if not isinstance(property_row, dict):
                            continue
                        target["propertyOccurrences"] += 1
                        property_key = tuple(
                            str(property_row.get(key) or "")
                            for key in (
                                "propertyIdHex", "propertyLabel", "rawHex",
                                "rawU32", "floatValue", "valueEncoding",
                            )
                        )
                        compact_property = target["properties"].setdefault(
                            property_key,
                            {
                                "propertyIdHex": property_row.get("propertyIdHex"),
                                "propertyLabel": property_row.get("propertyLabel"),
                                "rawHex": property_row.get("rawHex"),
                                "rawU32": property_row.get("rawU32"),
                                "floatValue": property_row.get("floatValue"),
                                "valueEncoding": property_row.get("valueEncoding"),
                                "sourceOccurrenceCount": 0,
                                "sourceObjectTypeLabels": set(),
                            },
                        )
                        compact_property["sourceOccurrenceCount"] += 1
                        if source_type:
                            compact_property["sourceObjectTypeLabels"].add(source_type)
                    for range_row in property_node.get("rangedProperties") or ():
                        if not isinstance(range_row, dict):
                            continue
                        target["rangedPropertyOccurrences"] += 1
                        range_key = tuple(
                            str(range_row.get(key) or "")
                            for key in (
                                "propertyIdHex", "propertyLabel", "minimumRawHex",
                                "maximumRawHex", "minimumFloat", "maximumFloat",
                                "valueEncoding",
                            )
                        )
                        compact_range = target["rangedProperties"].setdefault(
                            range_key,
                            {
                                "propertyIdHex": range_row.get("propertyIdHex"),
                                "propertyLabel": range_row.get("propertyLabel"),
                                "minimumRawHex": range_row.get("minimumRawHex"),
                                "minimumRawU32": range_row.get("minimumRawU32"),
                                "minimumFloat": range_row.get("minimumFloat"),
                                "maximumRawHex": range_row.get("maximumRawHex"),
                                "maximumRawU32": range_row.get("maximumRawU32"),
                                "maximumFloat": range_row.get("maximumFloat"),
                                "valueEncoding": range_row.get("valueEncoding"),
                                "sourceOccurrenceCount": 0,
                                "sourceObjectTypeLabels": set(),
                            },
                        )
                        compact_range["sourceOccurrenceCount"] += 1
                        if source_type:
                            compact_range["sourceObjectTypeLabels"].add(source_type)
                # StateChunk and InitialRTPC controls are exact serialized
                # authored values on the Event's processing nodes.  Keep a
                # bounded, deduplicated projection on each possible media
                # leaf; this is not a claim about live setters or branch
                # selection.
                for control_node in post_process.get("stateRtpcNodes") or ():
                    if not isinstance(control_node, dict):
                        continue
                    node_identity = {
                        "objectId": control_node.get("objectId"),
                        "objectType": control_node.get("objectType"),
                        "objectTypeLabel": control_node.get("objectTypeLabel"),
                    }
                    for raw_curve in control_node.get("rtpcCurves") or ():
                        if not isinstance(raw_curve, dict):
                            continue
                        points = [
                            {
                                key: point.get(key)
                                for key in (
                                    "pointIndex", "from", "to",
                                    "interpolation", "interpolationLabel",
                                )
                                if point.get(key) is not None
                            }
                            for point in (raw_curve.get("points") or ())
                            if isinstance(point, dict)
                        ]
                        point_limit = 8
                        curve_row = {
                            **node_identity,
                            "rtpcId": raw_curve.get("rtpcId"),
                            "rtpcIdHex": raw_curve.get("rtpcIdHex"),
                            "parameterId": raw_curve.get("parameterId"),
                            "parameterLabel": raw_curve.get("parameterLabel"),
                            "rtpcType": raw_curve.get("rtpcType"),
                            "rtpcTypeLabel": raw_curve.get("rtpcTypeLabel"),
                            "accum": raw_curve.get("accum"),
                            "accumLabel": raw_curve.get("accumLabel"),
                            "scaling": raw_curve.get("scaling"),
                            "scalingLabel": raw_curve.get("scalingLabel"),
                            "pointCount": raw_curve.get("pointCount")
                            if raw_curve.get("pointCount") is not None
                            else len(points),
                            "points": points[:point_limit],
                            "pointsTruncated": len(points) > point_limit,
                        }
                        curve_row = {
                            key: value for key, value in curve_row.items()
                            if value not in (None, "", [])
                        }
                        curve_key = tuple(
                            (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                            for key, value in sorted(curve_row.items())
                        )
                        target["rtpcControls"].setdefault(curve_key, curve_row)
                    for group in control_node.get("stateGroups") or ():
                        if not isinstance(group, dict):
                            continue
                        group_hex = str(
                            group.get("groupIdHex")
                            or (
                                f"0x{int(group.get('groupId')):08x}"
                                if group.get("groupId") is not None else ""
                            )
                        ).lower()
                        if group_hex:
                            target["stateGroupIds"].add(group_hex)
                        for state in group.get("states") or ():
                            if not isinstance(state, dict):
                                continue
                            for raw_value in state.get("values") or ():
                                if not isinstance(raw_value, dict):
                                    continue
                                state_row = {
                                    **node_identity,
                                    "groupId": group.get("groupId"),
                                    "groupIdHex": group_hex,
                                    "syncType": group.get("syncType"),
                                    "syncTypeLabel": group.get("syncTypeLabel"),
                                    "stateId": state.get("stateId"),
                                    "stateIdHex": state.get("stateIdHex"),
                                    "parameterId": raw_value.get("parameterId"),
                                    "parameterLabel": raw_value.get("parameterLabel"),
                                    "value": raw_value.get("value"),
                                }
                                state_row = {
                                    key: value for key, value in state_row.items()
                                    if value not in (None, "", [])
                                }
                                state_key = tuple(
                                    (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                                    for key, value in sorted(state_row.items())
                                )
                                target["stateControls"].setdefault(state_key, state_row)
                for aux_node in post_process.get("auxSendNodes") or ():
                    if not isinstance(aux_node, dict):
                        continue
                    for send in aux_node.get("userDefinedAuxSends") or ():
                        if not isinstance(send, dict):
                            continue
                        bus_id = str(
                            send.get("busIdHex") or send.get("busId") or ""
                        ).lower()
                        if not bus_id:
                            continue
                        target["auxSendOccurrences"] += 1
                        slot_index = send.get("slotIndex")
                        aux_key = (bus_id, str(slot_index or 0))
                        aux_row = target["auxSends"].setdefault(aux_key, {
                            "busIdHex": bus_id,
                            "slotIndex": slot_index,
                            "sourceObjectIds": set(),
                            "sourceObjectTypeLabels": set(),
                            "auxFlagsRawValues": set(),
                            "overrideUserDefinedAuxSends": set(),
                            "useGameDefinedAuxSends": set(),
                            "serializationStatuses": set(),
                            "gameDefinedAssignmentBoundaries": set(),
                            "rootActionIds": set(),
                        })
                        if aux_node.get("objectId") is not None:
                            aux_row["sourceObjectIds"].add(int(aux_node["objectId"]))
                        object_type_label = str(aux_node.get("objectTypeLabel") or "")
                        if object_type_label:
                            aux_row["sourceObjectTypeLabels"].add(object_type_label)
                        if aux_node.get("auxFlagsRaw") is not None:
                            aux_row["auxFlagsRawValues"].add(int(aux_node["auxFlagsRaw"]))
                        for field in (
                            "overrideUserDefinedAuxSends", "useGameDefinedAuxSends"
                        ):
                            if aux_node.get(field) is not None:
                                aux_row[field].add(bool(aux_node[field]))
                        status = str(send.get("serializationStatus") or "")
                        if status:
                            aux_row["serializationStatuses"].add(status)
                        boundary = str(
                            aux_node.get("gameDefinedAssignmentBoundary") or ""
                        )
                        if boundary:
                            aux_row["gameDefinedAssignmentBoundaries"].add(boundary)
                        aux_row["rootActionIds"].update(
                            int(value)
                            for value in aux_node.get("rootActionIds") or ()
                            if isinstance(value, int)
                        )
                if output_buses:
                    target["routeStatuses"].add("exactSerializedOutputBusPath")
                elif int(post_process.get("outputBusNodeCount") or 0) > 0:
                    target["routeStatuses"].add("outputBusNodeUnresolved")
                elif post_process.get("parserStatus"):
                    target["routeStatuses"].add("noExplicitOutputBusSerialized")
                for bus in output_buses:
                    if not isinstance(bus, dict):
                        continue
                    path = tuple(
                        str(value).lower()
                        for value in (
                            bus.get("busPathIdHexes")
                            or ([bus.get("busIdHex")] if bus.get("busIdHex") else [])
                        )
                        if str(value)
                    )
                    if not path:
                        continue
                    route_key = (event_id, bank_id, path)
                    target["routeKeys"].add(route_key)
                    target["busPaths"].add(path)
                    output_bus = str(bus.get("busIdHex") or "").lower()
                    if output_bus:
                        target["outputBusIds"].add(output_bus)
                    target["effectBusIds"].update(
                        str(value).lower()
                        for value in bus.get("effectBusIdHexes") or ()
                        if str(value)
                    )
                    target["unresolvedBusIds"].update(
                        str(value).lower()
                        for value in bus.get("unresolvedBusProcessingIdHexes") or ()
                        if str(value)
                    )

    output: dict[str, dict[str, Any]] = {}
    for marker, row in by_marker.items():
        paths = sorted(row["busPaths"])
        direct_effects = sorted(
            row["directEffects"].values(),
            key=lambda value: (
                str(value.get("pluginName") or ""),
                str(value.get("effectIdHex") or ""),
                int(value.get("objectId") or 0),
                int(value.get("slotIndex") or 0),
                str(value.get("parameterSummary") or ""),
            ),
        )
        rtpc_controls = sorted(
            row["rtpcControls"].values(),
            key=lambda value: (
                str(value.get("parameterLabel") or ""),
                str(value.get("rtpcIdHex") or ""),
                int(value.get("objectId") or 0),
                int(value.get("parameterId") or 0),
            ),
        )
        state_controls = sorted(
            row["stateControls"].values(),
            key=lambda value: (
                str(value.get("groupIdHex") or ""),
                str(value.get("stateIdHex") or ""),
                str(value.get("parameterLabel") or ""),
                int(value.get("objectId") or 0),
            ),
        )
        aux_sends = sorted(
            row["auxSends"].values(),
            key=lambda value: (
                str(value.get("busIdHex") or ""),
                int(value.get("slotIndex") or 0),
            ),
        )
        properties = sorted(
            row["properties"].values(),
            key=lambda value: (
                str(value.get("propertyLabel") or ""),
                str(value.get("propertyIdHex") or ""),
                str(value.get("rawHex") or ""),
            ),
        )
        ranged_properties = sorted(
            row["rangedProperties"].values(),
            key=lambda value: (
                str(value.get("propertyLabel") or ""),
                str(value.get("propertyIdHex") or ""),
                str(value.get("minimumRawHex") or ""),
                str(value.get("maximumRawHex") or ""),
            ),
        )
        compact_properties = []
        for property_row in properties:
            compact = {
                key: value for key, value in property_row.items()
                if key not in {"sourceObjectTypeLabels", "rawU32"}
            }
            # Float values are already losslessly represented by the decoded
            # scalar plus encoding tag; retain rawHex for ID/typed-union rows.
            if compact.get("valueEncoding") == "float":
                compact.pop("rawHex", None)
            compact_properties.append(compact)
        compact_ranges = [
            {
                key: value for key, value in range_row.items()
                if key not in {
                    "sourceObjectTypeLabels", "minimumRawU32", "maximumRawU32"
                }
            }
            for range_row in ranged_properties
        ]
        compact_aux_sends = []
        for aux in aux_sends:
            bus_routes = sorted(
                row["auxBusRoutes"].get(aux["busIdHex"], {}).values(),
                key=lambda value: (
                    str(value.get("busPathIdHexes") or []),
                    str(value.get("resolutionStatus") or ""),
                ),
            )
            compact_aux_sends.append({
                "busIdHex": aux["busIdHex"],
                "slotIndex": aux.get("slotIndex"),
                "sourceObjectCount": len(aux["sourceObjectIds"]),
                "sourceObjectIds": sorted(aux["sourceObjectIds"])[:8],
                "sourceObjectIdsTruncated": len(aux["sourceObjectIds"]) > 8,
                "sourceObjectTypeLabels": sorted(aux["sourceObjectTypeLabels"])[:8],
                "auxFlagsRawValues": sorted(aux["auxFlagsRawValues"]),
                "overrideUserDefinedAuxSends": sorted(
                    aux["overrideUserDefinedAuxSends"]
                ),
                "useGameDefinedAuxSends": sorted(aux["useGameDefinedAuxSends"]),
                "serializationStatuses": sorted(aux["serializationStatuses"]),
                "gameDefinedAssignmentBoundaries": sorted(
                    aux["gameDefinedAssignmentBoundaries"]
                ),
                "rootActionIds": sorted(aux["rootActionIds"])[:8],
                "rootActionIdsTruncated": len(aux["rootActionIds"]) > 8,
                "busRoutes": bus_routes[:4],
                "busRoutesTruncated": len(bus_routes) > 4,
            })
        media_relation_types = sorted(row["mediaRelationTypes"])
        media_selection_paths = sorted(row["mediaSelectionPaths"])
        media_root_action_ids = sorted(row["mediaRootActionIds"])
        output[marker] = {
            "postProcessRouteCount": len(row["routeKeys"]),
            "postProcessBusPathCount": len(paths),
            "postProcessBusPaths": [list(path) for path in paths[:32]],
            "postProcessBusPathsTruncated": len(paths) > 32,
            "postProcessOutputBusIds": sorted(row["outputBusIds"]),
            "postProcessEffectBusIds": sorted(row["effectBusIds"]),
            "postProcessUnresolvedBusProcessingIds": sorted(row["unresolvedBusIds"]),
            "postProcessSelectionStatuses": sorted(row["selectionStatuses"]),
            "postProcessRouteStatuses": sorted(row["routeStatuses"]),
            "postProcessEvidenceEventCount": len(row["evidenceKeys"]),
            "postProcessParsedNodeCount": row["parsedNodeCount"],
            "postProcessOutputBusNodeCount": row["outputBusNodeCount"],
            "postProcessDirectEffectCount": len(direct_effects),
            "postProcessDirectEffects": direct_effects[:32],
            "postProcessDirectEffectsTruncated": len(direct_effects) > 32,
            "postProcessDirectEffectOccurrences": row["directEffectOccurrences"],
            "postProcessDirectEffectEvidence": (
                "exactSerializedEventNodeEffectJoin"
                if direct_effects else None
            ),
            "postProcessRtpcControlCount": len(rtpc_controls),
            "postProcessRtpcControls": rtpc_controls[:32],
            "postProcessRtpcControlsTruncated": len(rtpc_controls) > 32,
            "postProcessStateGroupIds": sorted(row["stateGroupIds"]),
            "postProcessStateControlCount": len(state_controls),
            "postProcessStateControls": state_controls[:32],
            "postProcessStateControlsTruncated": len(state_controls) > 32,
            "postProcessControlEvidence": (
                "exactSerializedEventNodeStateRtpcJoin"
                if rtpc_controls or state_controls else None
            ),
            "postProcessAuxSendCount": len(aux_sends),
            "postProcessAuxSends": compact_aux_sends[:32],
            "postProcessAuxSendsTruncated": len(aux_sends) > 32,
            "postProcessAuxSendOccurrences": row["auxSendOccurrences"],
            "postProcessAuxSendEvidence": (
                "exactSerializedEventNodeUserDefinedAuxSendJoin"
                if aux_sends else None
            ),
            "postProcessPropertyCount": len(properties),
            "postProcessProperties": compact_properties[:32],
            "postProcessPropertiesTruncated": len(properties) > 32,
            "postProcessPropertyOccurrences": row["propertyOccurrences"],
            "postProcessRangeCount": len(ranged_properties),
            "postProcessRanges": compact_ranges[:32],
            "postProcessRangesTruncated": len(ranged_properties) > 32,
            "postProcessRangeOccurrences": row["rangedPropertyOccurrences"],
            "postProcessPropertyEvidence": (
                "exactSerializedEventNodePropertyJoin"
                if properties or ranged_properties else None
            ),
            "wwiseMediaRelationTypes": media_relation_types[:32],
            "wwiseMediaRelationTypesTruncated": len(media_relation_types) > 32,
            "wwiseMediaSelectionPathCount": len(media_selection_paths),
            "wwiseMediaSelectionPaths": [
                list(path) for path in media_selection_paths[:32]
            ],
            "wwiseMediaSelectionPathsTruncated": len(media_selection_paths) > 32,
            "wwiseMediaRootActionIds": media_root_action_ids[:32],
            "wwiseMediaRootActionIdsTruncated": len(media_root_action_ids) > 32,
            "wwiseMediaGraphEvidence": (
                "exactSerializedWwiseEventMediaJoin"
                if media_relation_types or media_selection_paths or media_root_action_ids
                else None
            ),
            "postProcessRouteEvidence": "exactSerializedEventOutputBusJoin",
        }
    return output

def annotate_media_post_process_effect_chains(
    media_rows: Iterable[dict[str, Any]],
    audio_index: dict[str, Any],
    *,
    limit: int = 64,
) -> dict[str, int]:
    """Attach a bounded authored direct-node + Bus effect chain to media.

    ``postProcessBusPaths`` are serialized from the leaf/output Bus toward its
    parent.  Direct node slots are emitted first because an Actor-Mixer/Blend
    node's own effects precede the output-bus route in the authored graph;
    Bus slots then follow each path in the serialized leaf-to-root order.
    This is a compact explanation of authored processing evidence, not a
    runtime DSP order claim: inherited platform values, live setters, branch
    selection, and audibility remain unobserved.
    """

    post_process = (audio_index.get("hircSummary") or {}).get(
        "postProcessSummary"
    ) or {}
    bus_definitions = {
        str(row.get("busIdHex") or row.get("busId") or "").lower(): row
        for row in post_process.get("busDefinitions") or ()
        if isinstance(row, dict)
        and str(row.get("busIdHex") or row.get("busId") or "")
    }

    attached = 0
    chain_count = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        chain: list[dict[str, Any]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        control_rows_by_bus: dict[str, dict[str, Any]] = {}
        duck_rows_by_bus: dict[str, dict[str, Any]] = {}

        # Direct node effects are already deduplicated and bounded on the
        # media row.  Retain node/slot identity so two authored effect nodes
        # with the same plug-in settings do not collapse together.
        direct_effects = sorted(
            (
                direct for direct in media.get("postProcessDirectEffects") or ()
                if isinstance(direct, dict)
            ),
            key=lambda direct: (
                int(direct.get("objectId") or 0),
                int(direct.get("slotIndex") or 0),
                str(direct.get("effectIdHex") or ""),
            ),
        )
        for direct in direct_effects:
            row = {
                "stage": "directNode",
                "objectId": direct.get("objectId"),
                "slotIndex": direct.get("slotIndex"),
                "effectIdHex": direct.get("effectIdHex"),
                "pluginName": direct.get("pluginName"),
                "pluginClassIdHex": direct.get("pluginClassIdHex"),
                "parameterSummary": direct.get("parameterSummary"),
                "effectBypass": direct.get("effectBypass"),
                "effectShareSet": direct.get("effectShareSet"),
                "effectRendered": direct.get("effectRendered"),
                "resolutionStatus": direct.get("resolutionStatus"),
            }
            row = {
                key: value for key, value in row.items()
                if value not in (None, "", [])
            }
            key = tuple(
                (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                for key, value in sorted(row.items())
            )
            if key not in seen:
                seen.add(key)
                chain.append(row)

        # The path list is already deterministic and serialized leaf-to-root;
        # preserve that order and the slot order inside each Bus definition.
        for path_index, raw_path in enumerate(media.get("postProcessBusPaths") or ()):
            if not isinstance(raw_path, (list, tuple)):
                continue
            for path_depth, raw_bus_id in enumerate(raw_path):
                bus_id = str(raw_bus_id or "").lower()
                if not bus_id:
                    continue
                definition = bus_definitions.get(bus_id)
                state_rtpc = (definition or {}).get("serializedStateAndRtpc") or {}
                if int((definition or {}).get("serializedDuckCount") or 0):
                    duck_row = duck_rows_by_bus.setdefault(bus_id, {
                        "busIdHex": bus_id,
                        "pathIndexes": set(),
                        "pathDepths": set(),
                        "duckCount": int((definition or {}).get("serializedDuckCount") or 0),
                        "maxDuckVolumeDb": (definition or {}).get("serializedMaxDuckVolumeDb"),
                        "ducks": list((definition or {}).get("serializedDucks") or ()),
                    })
                    duck_row["pathIndexes"].add(path_index)
                    duck_row["pathDepths"].add(path_depth)
                if (
                    int(state_rtpc.get("rtpcCurveCount") or 0)
                    or int(state_rtpc.get("stateGroupCount") or 0)
                ):
                    control_row = control_rows_by_bus.setdefault(bus_id, {
                        "busIdHex": bus_id,
                        "pathIndexes": set(),
                        "pathDepths": set(),
                        "rtpcCurveCount": int(state_rtpc.get("rtpcCurveCount") or 0),
                        "rtpcPointCount": int(state_rtpc.get("rtpcPointCount") or 0),
                        "rtpcControls": [],
                        "stateGroupCount": int(state_rtpc.get("stateGroupCount") or 0),
                        "stateCount": int(state_rtpc.get("stateCount") or 0),
                        "stateValueCount": int(state_rtpc.get("stateValueCount") or 0),
                        "stateControls": [],
                        "parserStatus": state_rtpc.get("parserStatus"),
                    })
                    control_row["pathIndexes"].add(path_index)
                    control_row["pathDepths"].add(path_depth)
                    if not control_row["rtpcControls"]:
                        for curve in state_rtpc.get("rtpcCurves") or ():
                            if not isinstance(curve, dict):
                                continue
                            points = [
                                {
                                    key: point.get(key)
                                    for key in (
                                        "pointIndex", "from", "to",
                                        "interpolation", "interpolationLabel",
                                    )
                                    if point.get(key) is not None
                                }
                                for point in (curve.get("points") or ())
                                if isinstance(point, dict)
                            ]
                            control_row["rtpcControls"].append({
                                key: value for key, value in {
                                    "rtpcIdHex": curve.get("rtpcIdHex"),
                                    "parameterId": curve.get("parameterId"),
                                    "parameterLabel": curve.get("parameterLabel"),
                                    "rtpcTypeLabel": curve.get("rtpcTypeLabel"),
                                    "accumLabel": curve.get("accumLabel"),
                                    "scalingLabel": curve.get("scalingLabel"),
                                    "pointCount": curve.get("pointCount")
                                    if curve.get("pointCount") is not None
                                    else len(points),
                                    "points": points[:8],
                                    "pointsTruncated": len(points) > 8,
                                }.items()
                                if value not in (None, "", [])
                            })
                    if not control_row["stateControls"]:
                        for group in state_rtpc.get("stateGroups") or ():
                            if not isinstance(group, dict):
                                continue
                            group_hex = str(
                                group.get("groupIdHex")
                                or group.get("groupId")
                                or ""
                            ).lower()
                            for state in group.get("states") or ():
                                if not isinstance(state, dict):
                                    continue
                                state_hex = str(
                                    state.get("stateIdHex")
                                    or state.get("stateId")
                                    or ""
                                ).lower()
                                for value in state.get("values") or ():
                                    if not isinstance(value, dict):
                                        continue
                                    control_row["stateControls"].append({
                                        key: item for key, item in {
                                            "groupIdHex": group_hex,
                                            "syncTypeLabel": group.get("syncTypeLabel"),
                                            "stateIdHex": state_hex,
                                            "parameterId": value.get("parameterId"),
                                            "parameterLabel": value.get("parameterLabel"),
                                            "value": value.get("value"),
                                        }.items()
                                        if item not in (None, "", [])
                                    })
                for slot in (definition or {}).get("effects") or ():
                    if not isinstance(slot, dict):
                        continue
                    # The top-level Bus catalog is the canonical payload for
                    # plug-in names, parameters, and flags.  Media rows keep
                    # only the stable slot/path reference to avoid copying a
                    # long authored parameter summary for every possible leaf.
                    row = {
                        "stage": "bus",
                        "busIdHex": bus_id,
                        "pathIndex": path_index,
                        "pathDepth": path_depth,
                        "slotIndex": slot.get("slotIndex"),
                        "effectIdHex": slot.get("effectIdHex"),
                    }
                    row = {
                        key: value for key, value in row.items()
                        if value not in (None, "", [])
                    }
                    key = tuple(
                        (key, json.dumps(value, sort_keys=True, ensure_ascii=False))
                        for key, value in sorted(row.items())
                    )
                    if key not in seen:
                        seen.add(key)
                        chain.append(row)

        if not chain:
            if not control_rows_by_bus and not duck_rows_by_bus:
                continue
        if chain:
            attached += 1
            chain_count += len(chain)
            media["postProcessEffectChainCount"] = len(chain)
            media["postProcessEffectChain"] = chain[:limit]
            media["postProcessEffectChainTruncated"] = len(chain) > limit
            media["postProcessEffectChainEvidence"] = (
                "exactSerializedEventNodeAndBusEffectJoin"
            )
        control_rows = []
        for row in control_rows_by_bus.values():
            rtpc_ids = sorted({
                str(curve.get("rtpcIdHex") or "").lower()
                for curve in row["rtpcControls"]
                if str(curve.get("rtpcIdHex") or "")
            })
            rtpc_parameter_labels = sorted({
                str(curve.get("parameterLabel") or "")
                for curve in row["rtpcControls"]
                if str(curve.get("parameterLabel") or "")
            })
            state_controls = [
                {
                    key: value for key, value in state.items()
                    if key in {
                        "groupIdHex", "stateIdHex", "parameterLabel", "value"
                    }
                }
                for state in row["stateControls"][:16]
            ]
            control_rows.append({
                "busIdHex": row["busIdHex"],
                "pathIndexes": sorted(row["pathIndexes"])[:32],
                "pathDepths": sorted(row["pathDepths"])[:32],
                "rtpcCurveCount": row["rtpcCurveCount"],
                "rtpcPointCount": row["rtpcPointCount"],
                "rtpcIds": rtpc_ids,
                "rtpcParameterLabels": rtpc_parameter_labels,
                "rtpcControlsTruncated": len(row["rtpcControls"]) > 8,
                "stateGroupCount": row["stateGroupCount"],
                "stateCount": row["stateCount"],
                "stateValueCount": row["stateValueCount"],
                "stateControls": state_controls,
                "stateControlsTruncated": len(row["stateControls"]) > 16,
            })
        control_rows.sort(key=lambda row: (
            row["pathIndexes"][0] if row["pathIndexes"] else 0,
            row["pathDepths"][0] if row["pathDepths"] else 0,
            row["busIdHex"],
        ))
        if control_rows:
            media["postProcessBusControlCount"] = len(control_rows)
            media["postProcessBusControls"] = control_rows[:32]
            media["postProcessBusControlsTruncated"] = len(control_rows) > 32
            media["postProcessBusControlEvidence"] = (
                "exactSerializedBusInitialRtpcAndStateJoin"
            )
        duck_rows = []
        for row in duck_rows_by_bus.values():
            ducks = []
            for duck in row["ducks"][:8]:
                if not isinstance(duck, dict):
                    continue
                ducks.append({
                    key: value for key, value in {
                        "duckIndex": duck.get("duckIndex"),
                        "targetBusIdHex": str(
                            duck.get("busIdHex") or duck.get("busId") or ""
                        ).lower(),
                        "duckVolumeDb": duck.get("duckVolumeDb"),
                        "fadeOutMs": duck.get("fadeOutMs"),
                        "fadeInMs": duck.get("fadeInMs"),
                        "fadeCurve": duck.get("fadeCurve"),
                        "targetPropertyIdHex": duck.get("targetPropertyIdHex"),
                        "targetPropertyLabel": duck.get("targetPropertyLabel"),
                    }.items()
                    if value not in (None, "", [])
                })
            duck_rows.append({
                "busIdHex": row["busIdHex"],
                "pathIndexes": sorted(row["pathIndexes"])[:32],
                "pathDepths": sorted(row["pathDepths"])[:32],
                "duckCount": row["duckCount"],
                "maxDuckVolumeDb": row["maxDuckVolumeDb"],
                "ducks": ducks,
                "ducksTruncated": len(row["ducks"]) > 8,
            })
        duck_rows.sort(key=lambda row: (
            row["pathIndexes"][0] if row["pathIndexes"] else 0,
            row["pathDepths"][0] if row["pathDepths"] else 0,
            row["busIdHex"],
        ))
        if duck_rows:
            media["postProcessBusDuckCount"] = len(duck_rows)
            media["postProcessBusDucks"] = duck_rows[:32]
            media["postProcessBusDucksTruncated"] = len(duck_rows) > 32
            media["postProcessBusDuckEvidence"] = (
                "exactSerializedBusDuckingJoin"
            )

    return {
        "mediaWithPostProcessEffectChain": attached,
        "mediaPostProcessEffectChainCount": chain_count,
    }

def annotate_media_trigger_contexts(
    media_rows: Iterable[dict[str, Any]],
    trigger_context_catalog: dict[str, Any] | None,
    *,
    limit: int = 32,
) -> dict[str, int]:
    """Attach compact exact trigger-context summaries to media leaves.

    Trigger contexts already carry full situation/owner/evidence records in
    ``trigger_contexts.json``.  This pass only joins their serialized
    ``mediaRefs`` back to the media shard, so a reader can understand why a
    decoded leaf is present without loading the trigger catalog first.  It
    deliberately preserves the context's runtime-selection and activation
    boundaries; it does not turn an authored request into observed playback.
    """

    if not isinstance(trigger_context_catalog, dict):
        return {"mediaWithTriggerContextSummary": 0, "triggerContextMediaRefs": 0}
    by_marker: dict[str, dict[str, Any]] = {}
    for index, context in enumerate(trigger_context_catalog.get("contexts") or ()):
        if not isinstance(context, dict):
            continue
        trigger_id = str(context.get("triggerId") or f"context:{index}")
        semantic_kind = str(context.get("semanticKind") or "unknown")
        trigger_role = str(context.get("triggerRole") or "unknown")
        runtime_status = str(context.get("runtimeActivationStatus") or "")
        selection = context.get("selection") or {}
        selection_statuses = {
            str(selection.get(key) or "")
            for key in (
                "runtimeSelectionStatus", "eventSelectionStatus",
                "mediaSelectionStatus",
            )
            if str(selection.get(key) or "")
        }
        owner = context.get("owner") or {}
        owner_values = {
            str(owner.get(key) or "")
            for key in ("ownerId", "configId", "voiceId", "speakerActorId")
            if str(owner.get(key) or "")
        }
        situation = context.get("situation") or {}
        situation_values = {
            str(situation.get(key) or "")
            for key in (
                "eventId", "dialogId", "dialogKey", "lineId", "triggerKey",
                "remoteCommonId", "singleId", "levelScriptId",
            )
            if str(situation.get(key) or "")
        }
        for media_ref in context.get("mediaRefs") or ():
            if not isinstance(media_ref, dict):
                continue
            marker = _media_route_marker(media_ref)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "triggerIds": set(),
                "semanticKinds": set(),
                "triggerRoles": set(),
                "selectionStatuses": set(),
                "runtimeStatuses": set(),
                "ownerValues": set(),
                "situationValues": set(),
            })
            target["triggerIds"].add(trigger_id)
            target["semanticKinds"].add(semantic_kind)
            target["triggerRoles"].add(trigger_role)
            target["selectionStatuses"].update(selection_statuses)
            if runtime_status:
                target["runtimeStatuses"].add(runtime_status)
            target["ownerValues"].update(owner_values)
            target["situationValues"].update(situation_values)

    attached = 0
    ref_count = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        marker = _media_route_marker(media)
        target = by_marker.get(marker)
        if not target:
            continue
        attached += 1
        ref_count += len(target["triggerIds"])
        fields = {
            "triggerContextCount": len(target["triggerIds"]),
            "triggerSemanticKinds": sorted(target["semanticKinds"])[:limit],
            "triggerRoles": sorted(target["triggerRoles"])[:limit],
            "triggerSelectionStatuses": sorted(target["selectionStatuses"])[:limit],
            "triggerRuntimeActivationStatuses": sorted(target["runtimeStatuses"])[:limit],
            "triggerOwnerValues": sorted(target["ownerValues"])[:limit],
            "triggerSituationValues": sorted(target["situationValues"])[:limit],
            "triggerContextSummaryEvidence": "exactSerializedTriggerContextMediaJoin",
        }
        media.update(fields)
        media["triggerContextSummaryTruncated"] = any(
            len(target[key]) > limit
            for key in (
                "semanticKinds", "triggerRoles", "selectionStatuses",
                "runtimeStatuses", "ownerValues", "situationValues",
            )
        )
    return {
        "mediaWithTriggerContextSummary": attached,
        "triggerContextMediaRefs": ref_count,
    }

def annotate_media_trigger_semantic_categories(
    media_rows: Iterable[dict[str, Any]],
    trigger_context_catalog: dict[str, Any] | None,
) -> dict[str, int]:
    """Recover semantic categories from exact trigger-context ownership.

    The physical Wwise path can remain ``unknown`` even when an authored
    trigger context identifies the Event's category or an exact serialized
    MonoBehaviour field role.  This pass adds a separate semantic label only
    when the evidence is unambiguous.  It never rewrites ``audioCategory`` and
    never resolves a random/switch branch or runtime activation.
    """

    if not isinstance(trigger_context_catalog, dict):
        return {
            "mediaWithSemanticCategoryFromTriggerContext": 0,
            "mediaSemanticCategoryFromTriggerEventCategory": 0,
            "mediaSemanticCategoryFromMonoBehaviourSfxField": 0,
        }

    by_marker: dict[str, dict[str, Any]] = {}
    for index, context in enumerate(trigger_context_catalog.get("contexts") or ()):
        if not isinstance(context, dict):
            continue
        trigger_id = str(context.get("triggerId") or f"context:{index}")
        meaning = context.get("meaning") or {}
        category = str(meaning.get("category") or "").strip().lower()
        if category in {"", "unknown"}:
            category = ""
        semantic_kind = str(context.get("semanticKind") or "")
        trigger_role = str(context.get("triggerRole") or "")
        situation = context.get("situation")
        situation = situation if isinstance(situation, dict) else {}
        mono_sfx_role = (
            semantic_kind == "monoBehaviourAudioIdField"
            and managed_literals.is_mono_behaviour_audio_sfx_role(
                trigger_role,
                raw_field=(
                    context.get("authoredFieldNameRaw")
                    or situation.get("authoredFieldNameRaw")
                ),
                serialized_field_path=(
                    context.get("serializedFieldPath")
                    or situation.get("serializedFieldPath")
                ),
                serialized_field_path_status=(
                    context.get("serializedFieldPathStatus")
                    or situation.get("serializedFieldPathStatus")
                ),
            )
        )
        for media_ref in context.get("mediaRefs") or ():
            if not isinstance(media_ref, dict):
                continue
            marker = _media_route_marker(media_ref)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "triggerIds": set(),
                "categories": set(),
                "monoSfxRoles": set(),
            })
            target["triggerIds"].add(trigger_id)
            if category:
                target["categories"].add(category)
            if mono_sfx_role:
                target["monoSfxRoles"].add(trigger_role)

    attached = 0
    from_event_category = 0
    from_mono_sfx_field = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        marker = _media_route_marker(media)
        target = by_marker.get(marker)
        if not target:
            continue
        if str(media.get("audioCategory") or "unknown") != "unknown":
            continue
        if media.get("semanticCategory"):
            continue
        categories = sorted(target["categories"])
        semantic_category = ""
        evidence = ""
        if len(categories) == 1:
            semantic_category = categories[0]
            evidence = "exactSerializedTriggerContextEventCategory"
            from_event_category += 1
            media["semanticCategoryContextCategories"] = categories
        elif not categories and target["monoSfxRoles"]:
            semantic_category = "sfx"
            evidence = "exactSerializedMonoBehaviourAudioIdFieldRole"
            from_mono_sfx_field += 1
            media["semanticCategoryFieldRoles"] = sorted(target["monoSfxRoles"])
        if not semantic_category:
            continue
        media["semanticCategory"] = semantic_category
        media["semanticCategoryEvidence"] = evidence
        attached += 1

    return {
        "mediaWithSemanticCategoryFromTriggerContext": attached,
        "mediaSemanticCategoryFromTriggerEventCategory": from_event_category,
        "mediaSemanticCategoryFromMonoBehaviourSfxField": from_mono_sfx_field,
    }

def annotate_media_event_contexts(
    media_rows: Iterable[dict[str, Any]],
    event_rows: Iterable[dict[str, Any]],
    *,
    limit: int = 32,
) -> dict[str, int]:
    """Attach Event-level authored contexts to their possible media leaves.

    Unlike ``trigger_contexts.json`` mediaRefs, this join starts from the
    Event's complete candidate media set.  It therefore explains who/what
    authored the Event while explicitly retaining the runtime branch boundary:
    a context can apply to several random/switch/sequence leaves.
    """

    by_marker: dict[str, dict[str, Any]] = {}
    for event_index, event in enumerate(event_rows or ()):
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or event.get("eventId") or "").strip()
        if not event_id:
            continue
        contexts = [
            context for context in event.get("contexts") or ()
            if isinstance(context, dict)
        ]
        if not contexts:
            continue
        for candidate in event.get("media") or ():
            if not isinstance(candidate, dict):
                continue
            marker = _media_route_marker(candidate)
            if not marker:
                continue
            target = by_marker.setdefault(marker, {
                "contextKeys": set(),
                "eventIds": set(),
                "kinds": set(),
                "roles": set(),
                "ownerValues": set(),
                "situationValues": set(),
                "selectionStatuses": set(),
            })
            target["eventIds"].add(event_id)
            for context_index, context in enumerate(contexts):
                target["contextKeys"].add((event_id, event_index, context_index))
                kind = str(context.get("kind") or "unknown")
                target["kinds"].add(kind)
                role = str(context.get("triggerRole") or "").strip()
                if role:
                    target["roles"].add(role)
                for key in (
                    "ownerId", "configId", "voiceId", "speakerActorId",
                    "skillId", "enemyId", "characterId",
                ):
                    value = str(context.get(key) or "").strip()
                    if value:
                        target["ownerValues"].add(f"{key}={value}")
                for key in (
                    "dialogId", "dialogKey", "lineId", "triggerKey",
                    "remoteCommonId", "singleId", "levelScriptId",
                    "path", "table", "source",
                ):
                    value = str(context.get(key) or "").strip()
                    if value:
                        target["situationValues"].add(f"{key}={value}")
                for key in (
                    "runtimeSelectionStatus", "eventSelectionStatus",
                    "mediaSelectionStatus", "runtimeActivationStatus",
                    "triggerBindingStatus",
                ):
                    value = str(context.get(key) or "").strip()
                    if value:
                        target["selectionStatuses"].add(value)

    attached = 0
    context_count = 0
    for media in media_rows:
        if not isinstance(media, dict):
            continue
        target = by_marker.get(_media_route_marker(media))
        if not target:
            continue
        attached += 1
        context_count += len(target["contextKeys"])
        fields = {
            "eventContextCount": len(target["contextKeys"]),
            "eventContextEventIds": sorted(target["eventIds"])[:limit],
            "eventContextKinds": sorted(target["kinds"])[:limit],
            "eventContextRoles": sorted(target["roles"])[:limit],
            "eventContextOwnerValues": sorted(target["ownerValues"])[:limit],
            "eventContextSituationValues": sorted(target["situationValues"])[:limit],
            "eventContextSelectionStatuses": sorted(target["selectionStatuses"])[:limit],
            "eventContextSummaryEvidence": "exactSerializedEventContextToPossibleMediaJoin",
        }
        media.update(fields)
        media["eventContextSummaryTruncated"] = any(
            len(target[key]) > limit
            for key in (
                "eventIds", "kinds", "roles", "ownerValues",
                "situationValues", "selectionStatuses",
            )
        )
    return {
        "mediaWithEventContextSummary": attached,
        "mediaEventContextSummaryCount": context_count,
    }

def build_media_rows(
    audio_index: dict[str, Any],
    media_to_events: dict[str, list[str]],
    event_categories: dict[str, str] | None = None,
    event_rows: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    event_categories = event_categories or {}
    seen: set[tuple[str, str]] = set()
    event_rows = list(event_rows or ())
    post_process_routes = _media_post_process_routes(event_rows)
    definition_evidence_by_media_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    authored_event_ids_by_bank: dict[tuple[str, int], set[str]] = defaultdict(set)
    for inventory in audio_index.get("wwiseEventInventory") or []:
        if not isinstance(inventory, dict):
            continue
        event_id = str(inventory.get("eventId") or "").strip()
        bank = str(inventory.get("bank") or "").strip()
        try:
            bank_id = int(inventory.get("bankId"))
        except (TypeError, ValueError):
            continue
        if event_id and bank and not event_id.lower().startswith("hashed-event:"):
            authored_event_ids_by_bank[(bank, bank_id)].add(event_id)
    for evidence in (audio_index.get("hircSummary") or {}).get("definitionOnlyDecodedSoundObjects") or []:
        if not isinstance(evidence, dict):
            continue
        try:
            media_id = int(evidence.get("mediaId"))
        except (TypeError, ValueError):
            continue
        definition_evidence_by_media_id[media_id].append(evidence)
    for entry in audio_index.get("entries") or []:
        if not isinstance(entry, dict) or entry.get("eventId"):
            continue
        compact = event_projection.compact_media(entry)
        rel = str(compact.get("rel") or "")
        storage = str(compact.get("storageRoot") or "")
        marker = (storage, rel)
        if not rel or marker in seen:
            continue
        seen.add(marker)
        reverse_key = str(compact.get("src") or rel or compact.get("mediaId") or "")
        event_ids = media_to_events.get(reverse_key, [])
        compact["eventCount"] = len(event_ids)
        if event_ids:
            compact["eventIds"] = event_ids
            related_categories = sorted({
                str(event_categories.get(event_id) or "unknown")
                for event_id in event_ids
            })
            compact["relatedEventCategories"] = related_categories
            unique_known_categories = sorted({
                value for value in related_categories if value not in {"", "unknown"}
            })
            if (
                str(compact.get("audioCategory") or "unknown") == "unknown"
                and len(unique_known_categories) == 1
            ):
                compact["semanticCategory"] = unique_known_categories[0]
                compact["semanticCategoryEvidence"] = (
                    "exactUniqueRelatedWwiseEventCategory"
                )
        route = post_process_routes.get(reverse_key)
        if route:
            compact.update(route)
        try:
            media_id = int(compact.get("mediaId") or compact.get("id"))
        except (TypeError, ValueError):
            media_id = 0
        definition_evidence = definition_evidence_by_media_id.get(media_id, [])
        if definition_evidence and not event_ids:
            compact["audioLibraryObjectStatus"] = "wwiseSoundDefinitionWithoutEventPath"
            compact["wwiseDefinitionEvidence"] = definition_evidence
            bank_event_ids = sorted({
                event_id
                for evidence in definition_evidence
                for event_id in authored_event_ids_by_bank.get((
                    str(evidence.get("bank") or ""),
                    int(evidence.get("bankId") or 0),
                ), set())
            })
            if bank_event_ids:
                compact["audioLibraryBankEventIds"] = bank_event_ids
                compact["purposeHintStatus"] = "authoredEventBankColocationOnly"
        rows.append(compact)
    annotate_media_event_contexts(rows, event_rows)
    annotate_media_post_process_effect_chains(rows, audio_index)
    rows.sort(key=lambda row: (
        str(row.get("audioCategory") or "unknown"),
        str(row.get("id") or ""),
        str(row.get("rel") or ""),
    ))
    return rows
