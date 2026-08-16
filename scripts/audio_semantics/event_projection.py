"""Projection of recovered Audio events into compact WebUI rows."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from typing import Any, Iterable

from . import identifiers, purpose

EVENT_CATEGORY_PREFIXES = (
    ("au_sfx_", "sfx"),
    ("au_chr_", "sfx"),
    ("au_eny_", "sfx"),
    ("au_npc_", "sfx"),
    ("au_monster_", "sfx"),
    ("au_int_", "sfx"),
    ("au_item_", "sfx"),
    ("au_gameplay_", "sfx"),
    ("au_weekraid_", "sfx"),
    ("au_music_", "music"),
    ("au_cue_", "cue"),
    ("au_amb_", "ambience"),
    ("au_env_", "ambience"),
    ("au_fac_amb_", "ambience"),
    ("au_ui_", "ui"),
    ("au_ul_", "ui"),
    ("au_vo_", "voice"),
    ("au_voice_", "voice"),
    ("au_radio_", "voice"),
    ("au_dlg_", "voice"),
    ("au_fac_announcement_", "voice"),
    ("au_global_", "control"),
    ("au_trigger_", "control"),
    ("au_rtpc_", "control"),
    ("au_motion_", "control"),
    ("au_vibration_", "control"),
    ("bark_", "voice"),
    ("radio_", "voice"),
    ("player_fol_", "sfx"),
    ("projectile-event:", "sfx"),
)

HIRC_OBJECT_TYPE_LABELS = {
    2: "sound",
    3: "action",
    4: "event",
    5: "randomSequenceContainer",
    6: "switchContainer",
    7: "actorMixer",
    9: "layer",
    10: "musicSegment",
    11: "musicTrack",
    12: "musicSwitchContainer",
    13: "musicRandomSequenceContainer",
    14: "attenuation",
    16: "effectShareSet",
    17: "customPlugin",
    18: "auxiliaryBus",
    19: "lfoModulator",
    20: "envelopeModulator",
    21: "audioDevice",
    22: "timeModulator",
    8: "audioBus",
}

CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD = 0.5
CUSTOM_FOOTSTEP_SIDE_VALUES = {0x00: "Left", 0x01: "Right", 0x03: "Invalid"}
CUSTOM_FOOTSTEP_VFX_VALUES = {0x00: "None", 0x04: "Step", 0x08: "Jump", 0x0C: "Land"}
CUSTOM_FOOTSTEP_FILTER_VALUES = {
    0x00: "IsMaxWeight",
    0x20: "IsComposeMaxWeight",
    0x40: "CustomWeight",
    0xE0: "ForcePlay",
}


def decode_custom_footstep_parameters(raw_int: Any, raw_float: Any) -> dict[str, Any] | None:
    """Decode the exact current-build OnCustomFootStep packed parameters."""

    if isinstance(raw_int, bool) or not isinstance(raw_int, int):
        return None
    if isinstance(raw_float, bool) or not isinstance(raw_float, (int, float)):
        return None
    float_value = float(raw_float)
    if not math.isfinite(float_value):
        return None
    side_bits = raw_int & 0x03
    vfx_bits = raw_int & 0x1C
    filter_bits = raw_int & 0xE0
    foot_side = CUSTOM_FOOTSTEP_SIDE_VALUES.get(side_bits)
    vfx_type = CUSTOM_FOOTSTEP_VFX_VALUES.get(vfx_bits)
    playback_filter = CUSTOM_FOOTSTEP_FILTER_VALUES.get(filter_bits)
    exact = all(value is not None for value in (foot_side, vfx_type, playback_filter))
    is_custom_weight = playback_filter == "CustomWeight"
    return {
        "rawInt": raw_int,
        "rawFloat": float_value,
        "footSide": foot_side or f"Unknown(0x{side_bits:02x})",
        "vfxType": vfx_type or f"Unknown(0x{vfx_bits:02x})",
        "playbackFilter": playback_filter or f"Unknown(0x{filter_bits:02x})",
        "customWeightThreshold": float_value if is_custom_weight else None,
        "runtimeVfxWeightThreshold": CUSTOM_FOOTSTEP_RUNTIME_VFX_WEIGHT_THRESHOLD,
        "inactiveFloat": not is_custom_weight,
        "floatParameterStatus": (
            "customWeightThreshold" if is_custom_weight else "inactiveForPlaybackFilter"
        ),
        "decodeStatus": "exactCurrentBuild" if exact else "unsupportedMaskedValue",
    }


def aggregate_custom_footstep_parameter_variants(
    evidence_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Count exact callback parameter variants without retaining every clip row."""

    counts: Counter[tuple[int, float]] = Counter()
    for evidence in evidence_rows:
        if not isinstance(evidence, dict) or evidence.get("function") != "OnCustomFootStep":
            continue
        decoded = decode_custom_footstep_parameters(
            evidence.get("intParameter"), evidence.get("floatParameter")
        )
        if decoded is None:
            continue
        counts[(decoded["rawInt"], decoded["rawFloat"])] += 1
    variants = []
    for (raw_int, raw_float), occurrence_count in sorted(counts.items()):
        decoded = decode_custom_footstep_parameters(raw_int, raw_float)
        assert decoded is not None
        variants.append({**decoded, "occurrenceCount": occurrence_count})
    return variants


def aggregate_custom_footstep_context_variants(
    contexts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: Counter[tuple[int, float]] = Counter()
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for variant in context.get("customFootstepParameterVariants") or []:
            decoded = decode_custom_footstep_parameters(
                variant.get("rawInt"), variant.get("rawFloat")
            )
            if decoded is None:
                continue
            counts[(decoded["rawInt"], decoded["rawFloat"])] += int(
                variant.get("occurrenceCount") or 0
            )
    variants = []
    for (raw_int, raw_float), occurrence_count in sorted(counts.items()):
        decoded = decode_custom_footstep_parameters(raw_int, raw_float)
        assert decoded is not None
        variants.append({**decoded, "occurrenceCount": occurrence_count})
    return variants


def _direct_event_category(value: str) -> str:
    for prefix, category in EVENT_CATEGORY_PREFIXES:
        if value.startswith(prefix):
            return category
    return "unknown"


def event_category_with_evidence(event_id: Any) -> tuple[str, str]:
    """Classify an authored Event name without claiming its runtime caller.

    The normal ``au_*`` prefixes are the primary contract. A few shipped bank
    naming families omit that prefix; their labels are only promoted when the
    complete family marker is explicit (enemy, actor/UI, LevelSequence, or
    the documented ``Play_au_*`` alias). The returned evidence string keeps
    these conservative name-pattern classifications distinct from recovered
    consumer contexts.
    """
    value = str(event_id or "").strip().lower()
    # Preserve the authored id verbatim elsewhere, but tolerate a serialized
    # Timeline display-name delimiter when assigning the broad audio category.
    value = value.lstrip(":")
    category = _direct_event_category(value)
    if category != "unknown":
        return category, "namePrefix"
    if value.startswith("play_au_"):
        nested_category = _direct_event_category(value[5:])
        if nested_category != "unknown":
            return nested_category, "authoredPlayAliasNamePattern"
    if value.startswith("eny_"):
        return "sfx", "authoredEnemyEventNamePattern"
    if value.startswith(("a_actor_", "au_actor_")):
        if "_ui_" in value:
            return "ui", "authoredActorUiEventNamePattern"
        return "sfx", "authoredActorEventNamePattern"
    if value.startswith("levelseq_"):
        return "cue", "authoredLevelSequenceEventNamePattern"
    if value.startswith("stop_au_global_"):
        return "control", "authoredGlobalStopEventNamePattern"
    if value.startswith("au_gacha_"):
        return "ui", "authoredGachaUiEventNamePattern"
    if value.startswith((
        "au_abilityentity_", "au_buff_", "au_effect_", "au_event_",
        "au_fs_", "au_impact_", "au_reset_", "au_special_",
        "general_foley_", "int_",
    )):
        return "sfx", "authoredGameplaySfxEventNamePattern"
    return "unknown", "unclassified"


def event_category(event_id: Any) -> str:
    return event_category_with_evidence(event_id)[0]


def compact_media(entry: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "id", "mediaId", "rel", "src", "format", "bytes", "storageRoot",
        "audioScope", "audioCategory", "audioCategoryDetail", "sourceBlock",
        "sourceBlockLabel", "sourceLanguage", "sourceBank", "bankId", "bank",
        "audioDialogKey", "audioDialogPath", "speakerChannel", "voType", "duration", "bitrate",
        "storyLineBindingCount", "purposeKnowledgeStatus",
        "wwiseMediaEvidence", "contentSha256",
        "hotfixMediaReplacement", "mediaResolutionEvidence",
        "externalMediaIdentityStatus", "externalAuthoredAudioId",
        "externalAuthoredPath", "externalIdentityEvidence",
        "identityOnlyPlaybackPlacementStatus",
    )
    compact = {key: entry[key] for key in keys if entry.get(key) not in (None, "", [])}
    if compact.get("wwiseMediaEvidence"):
        compact["wwiseMediaEvidence"] = [
            {
                key: row[key]
                for key in (
                    "rootActionIds", "soundObjectCount", "relationTypes",
                    "musicTrackObjectCount", "selectionPaths", "bankId", "bankPackage",
                    "sourceKinds", "pluginIds", "pluginNames", "streamTypes", "sourceBits",
                )
                if row.get(key) not in (None, "", [])
            }
            for row in compact["wwiseMediaEvidence"]
            if isinstance(row, dict)
        ]
    return compact


def _selector_id_hex(value: Any) -> str:
    """Normalize a serialized Wwise selector id without assigning a name."""

    if value in (None, ""):
        return ""
    try:
        if isinstance(value, str):
            text = value.strip().lower()
            if text.startswith("0x"):
                number = int(text, 16)
            else:
                number = int(text, 10)
        else:
            number = int(value)
    except (TypeError, ValueError):
        return str(value).strip().lower()
    return f"0x{number & 0xFFFFFFFF:08x}"


def _selector_group_catalog(
    selector_groups: Iterable[dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for raw_group in selector_groups or ():
        if not isinstance(raw_group, dict):
            continue
        key = _selector_id_hex(raw_group.get("groupIdHex") or raw_group.get("groupId"))
        if key:
            catalog.setdefault(key, raw_group)
    return catalog


def _compact_selector_group(raw_group: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "groupId", "groupIdHex", "groupType", "semanticRole", "semanticLabel",
        "semanticEvidence", "recoveredName", "nameEvidence",
        "authoredGroupNameStatus", "runtimeScope", "runtimeObservationStatus",
    )
    return {
        key: raw_group[key]
        for key in keys
        if raw_group.get(key) not in (None, "", [])
    }


def _selector_value_ids(raw_value: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("valueIdHex", "resolvedValueIdHex", "valueId", "resolvedValueId"):
        value = _selector_id_hex(raw_value.get(key))
        if value:
            ids.add(value)
    return ids


def _compact_selector_value(raw_value: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "valueId", "valueIdHex", "resolvedValueId", "resolvedValueIdHex",
        "semanticName", "resolvedValueName", "semanticEvidence",
        "resolutionEvidence", "semanticNameStatus", "member", "hashInput",
        "resolution",
    )
    compact = {
        key: raw_value[key]
        for key in keys
        if raw_value.get(key) not in (None, "", [])
    }
    # Metadata enum rows use ``member`` while native selector rows use
    # ``semanticName``.  The member is an exact enum identity, not a Wwise
    # authored-name guess, so expose it through the common display field.
    if not compact.get("semanticName") and compact.get("member"):
        compact["semanticName"] = compact["member"]
    if not compact.get("semanticEvidence") and compact.get("resolution"):
        compact["semanticEvidence"] = compact["resolution"]
    return compact


def _has_selector_value_semantics(raw_value: dict[str, Any]) -> bool:
    compact = _compact_selector_value(raw_value)
    return bool(compact.get("semanticName") or compact.get("resolvedValueName"))


def compact_container_evidence(
    rows: Iterable[Any],
    selector_groups: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    summary: dict[tuple[int, str, str], dict[str, Any]] = {}
    selector_catalog = _selector_group_catalog(selector_groups)
    for row in rows:
        if not isinstance(row, dict):
            continue
        object_type = int(row.get("objectType") or 0)
        edge_kind = str(row.get("edgeKind") or "unknown")
        mode_label = str(row.get("modeLabel") or "")
        key = (object_type, edge_kind, mode_label)
        target = summary.setdefault(key, {
            "objectType": object_type,
            "edgeKind": edge_kind,
            "modeLabel": mode_label,
            "nodeCount": 0,
            "childCount": 0,
            "parserConfidence": row.get("parserConfidence"),
        })
        target["nodeCount"] += 1
        target["childCount"] += int(row.get("childCount") or 0)
        if object_type == 5 and row.get("selectorParserStatus"):
            target["randomSequenceNodeCount"] = int(
                target.get("randomSequenceNodeCount") or 0
            ) + 1
            random_status = str(row.get("selectorParserStatus") or "unknown")
            target.setdefault("_randomSequenceParserStatuses", Counter())[random_status] += 1
            if random_status == "typedExactV150PlaylistWeights":
                target["typedRandomSequenceNodeCount"] = int(
                    target.get("typedRandomSequenceNodeCount") or 0
                ) + 1
                target.setdefault("_randomSequenceModes", Counter())[
                    str(row.get("modeLabel") or "unknown")
                ] += 1
                target.setdefault("_randomModes", Counter())[
                    str(row.get("randomModeLabel") or "unknown")
                ] += 1
                target.setdefault("_randomTransitionModes", Counter())[
                    str(row.get("transitionModeLabel") or "unknown")
                ] += 1
                target["randomSequencePlaylistItemCount"] = int(
                    target.get("randomSequencePlaylistItemCount") or 0
                ) + int(row.get("playlistItemCount") or 0)
                membership_status = str(
                    row.get("playlistMembershipStatus") or "unknown"
                )
                target.setdefault("_randomSequenceMembershipStatuses", Counter())[
                    membership_status
                ] += 1
                target["randomSequenceOwnedChildNotInPlaylistCount"] = int(
                    target.get("randomSequenceOwnedChildNotInPlaylistCount") or 0
                ) + len(row.get("ownedChildIdsNotInPlaylist") or [])
                target["randomSequenceDuplicatePlaylistItemCount"] = int(
                    target.get("randomSequenceDuplicatePlaylistItemCount") or 0
                ) + int(row.get("duplicatePlaylistItemCount") or 0)
                if membership_status == "emptyPlaylistOwnedChildrenPreserved":
                    target["randomSequenceEmptyPlaylistNodeCount"] = int(
                        target.get("randomSequenceEmptyPlaylistNodeCount") or 0
                    ) + 1
                if not row.get("childrenOrderMatchesPlaylist", True):
                    target["playlistOrderDiffersFromChildrenCount"] = int(
                        target.get("playlistOrderDiffersFromChildrenCount") or 0
                    ) + 1
                non_default_weights = int(row.get("nonDefaultWeightCount") or 0)
                target["nonDefaultWeightItemCount"] = int(
                    target.get("nonDefaultWeightItemCount") or 0
                ) + non_default_weights
                if non_default_weights:
                    target["nonDefaultWeightNodeCount"] = int(
                        target.get("nonDefaultWeightNodeCount") or 0
                    ) + 1
                if not row.get("uniformWeights", True):
                    target["nonUniformWeightNodeCount"] = int(
                        target.get("nonUniformWeightNodeCount") or 0
                    ) + 1
                avoid_repeat = int(row.get("avoidRepeatCount") or 0)
                target["maxAvoidRepeatCount"] = max(
                    int(target.get("maxAvoidRepeatCount") or 0), avoid_repeat
                )
                if avoid_repeat != 1:
                    target["nonDefaultAvoidRepeatNodeCount"] = int(
                        target.get("nonDefaultAvoidRepeatNodeCount") or 0
                    ) + 1
                if int(row.get("loopCount") or 0) != 1:
                    target["nonDefaultLoopNodeCount"] = int(
                        target.get("nonDefaultLoopNodeCount") or 0
                    ) + 1
                if row.get("globalScope"):
                    target["globalScopeRandomSequenceNodeCount"] = int(
                        target.get("globalScopeRandomSequenceNodeCount") or 0
                    ) + 1
                if row.get("continuous"):
                    target["continuousRandomSequenceNodeCount"] = int(
                        target.get("continuousRandomSequenceNodeCount") or 0
                    ) + 1
                if row.get("resetPlaylistAtEachPlay"):
                    target["resetPlaylistNodeCount"] = int(
                        target.get("resetPlaylistNodeCount") or 0
                    ) + 1
            else:
                target["unresolvedRandomSequenceNodeCount"] = int(
                    target.get("unresolvedRandomSequenceNodeCount") or 0
                ) + 1
        if object_type == 9 and isinstance(row.get("layerTailEvidence"), dict):
            layer = row["layerTailEvidence"]
            target["layerNodeCount"] = int(target.get("layerNodeCount") or 0) + 1
            layer_status = str(layer.get("layerTailParserStatus") or "unknown")
            target.setdefault("_layerParserStatuses", Counter())[layer_status] += 1
            if layer_status == "typedExactV150LayerTail":
                target["typedLayerNodeCount"] = int(
                    target.get("typedLayerNodeCount") or 0
                ) + 1
                confidence = str(row.get("parserConfidence") or "unknown")
                target.setdefault("_layerProofStatuses", Counter())[confidence] += 1
                assignment = str(layer.get("layerAssignmentStatus") or "unknown")
                target.setdefault("_layerAssignmentStatuses", Counter())[assignment] += 1
                target["layerDefinitionCount"] = int(
                    target.get("layerDefinitionCount") or 0
                ) + int(layer.get("layerCount") or 0)
                target["layerInitialRtpcCurveCount"] = int(
                    target.get("layerInitialRtpcCurveCount") or 0
                ) + int(layer.get("initialRtpcCurveCount") or 0)
                target["layerAssociationCount"] = int(
                    target.get("layerAssociationCount") or 0
                ) + int(layer.get("associationCount") or 0)
                target["layerCurvePointCount"] = int(
                    target.get("layerCurvePointCount") or 0
                ) + int(layer.get("curvePointCount") or 0)
                if layer.get("continuousValidation"):
                    target["continuousLayerNodeCount"] = int(
                        target.get("continuousLayerNodeCount") or 0
                    ) + 1
                target["layerAssociationOutsideChildrenCount"] = int(
                    target.get("layerAssociationOutsideChildrenCount") or 0
                ) + len(layer.get("associationChildIdsOutsideChildren") or [])
                for layer_row in layer.get("layers") or []:
                    if not isinstance(layer_row, dict):
                        continue
                    try:
                        target.setdefault("_layerRtpcIds", set()).add(
                            int(layer_row.get("rtpcId")) & 0xFFFFFFFF
                        )
                    except (TypeError, ValueError):
                        pass
                    target.setdefault("_layerRtpcTypes", Counter())[
                        str(layer_row.get("rtpcTypeLabel") or "unknown")
                    ] += 1
            else:
                target["unresolvedLayerNodeCount"] = int(
                    target.get("unresolvedLayerNodeCount") or 0
                ) + 1
        selector = row.get("switchMappingEvidence")
        if not isinstance(selector, dict):
            continue
        target["selectorNodeCount"] = int(target.get("selectorNodeCount") or 0) + 1
        parser_status = str(selector.get("parserStatus") or "unknown")
        parser_counts = target.setdefault("_selectorParserStatuses", Counter())
        parser_counts[parser_status] += 1
        if parser_status != "typedExactV150FlatPackages":
            target["unresolvedSelectorNodeCount"] = int(
                target.get("unresolvedSelectorNodeCount") or 0
            ) + 1
            continue

        target["typedSelectorNodeCount"] = int(
            target.get("typedSelectorNodeCount") or 0
        ) + 1
        group_type = str(selector.get("groupType") or "unknown")
        group_type_counts = target.setdefault("_selectorGroupTypes", Counter())
        group_type_counts[group_type] += 1
        try:
            group_id = int(selector.get("groupId")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            group_id = None
        if group_id is not None:
            target.setdefault("_selectorGroupIds", set()).add(group_id)
        group_key = _selector_id_hex(group_id)
        semantic_group = selector_catalog.get(group_key)
        if semantic_group is not None:
            target["selectorSemanticGroupMatchCount"] = int(
                target.get("selectorSemanticGroupMatchCount") or 0
            ) + 1
            target.setdefault("_selectorGroupSemantics", {})[group_key] = (
                _compact_selector_group(semantic_group)
            )
        if selector.get("continuousValidation"):
            target["continuousValidationNodeCount"] = int(
                target.get("continuousValidationNodeCount") or 0
            ) + 1

        packages = [
            package for package in selector.get("packages") or []
            if isinstance(package, dict)
        ]
        target["selectorPackageCount"] = int(
            target.get("selectorPackageCount") or 0
        ) + len(packages)
        authored_child_count = int(row.get("childCount") or 0)
        package_value_ids: set[int] = set()
        for package in packages:
            child_ids = [
                value for value in package.get("childIds") or []
                if isinstance(value, int)
            ]
            try:
                package_value_ids.add(int(package.get("valueId")) & 0xFFFFFFFF)
            except (TypeError, ValueError):
                pass
            if semantic_group is not None:
                package_value_key = _selector_id_hex(package.get("valueId"))
                semantic_value = next(
                    (
                        value
                        for value in semantic_group.get("values") or ()
                        if isinstance(value, dict)
                        and package_value_key in _selector_value_ids(value)
                    ),
                    None,
                )
                if semantic_value is not None and _has_selector_value_semantics(
                    semantic_value
                ):
                    target["selectorSemanticValueMatchCount"] = int(
                        target.get("selectorSemanticValueMatchCount") or 0
                    ) + 1
                    target.setdefault("_selectorValueSemantics", {})[
                        f"{group_key}:{package_value_key}"
                    ] = {
                        "groupIdHex": group_key,
                        "valueIdHex": package_value_key,
                        **_compact_selector_value(semantic_value),
                    }
            if child_ids:
                target["nonEmptySelectorPackageCount"] = int(
                    target.get("nonEmptySelectorPackageCount") or 0
                ) + 1
                target["selectorPackageChildReferenceCount"] = int(
                    target.get("selectorPackageChildReferenceCount") or 0
                ) + len(child_ids)
                if authored_child_count and len(set(child_ids)) < authored_child_count:
                    target["strictSubsetSelectorPackageCount"] = int(
                        target.get("strictSubsetSelectorPackageCount") or 0
                    ) + 1
        try:
            default_value_id = int(selector.get("defaultValueId")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            default_value_id = None
        if default_value_id is not None and default_value_id not in package_value_ids:
            target["defaultValueMissingPackageCount"] = int(
                target.get("defaultValueMissingPackageCount") or 0
            ) + 1

        associations = [
            association for association in selector.get("associations") or []
            if isinstance(association, dict)
        ]
        target["selectorAssociationCount"] = int(
            target.get("selectorAssociationCount") or 0
        ) + len(associations)
        switch_mode_counts = target.setdefault("_selectorSwitchModes", Counter())
        for association in associations:
            switch_mode_counts[str(association.get("onSwitchMode") or "unknown")] += 1
            if association.get("isFirstOnly"):
                target["isFirstOnlyAssociationCount"] = int(
                    target.get("isFirstOnlyAssociationCount") or 0
                ) + 1
            if association.get("continuePlayback"):
                target["continuePlaybackAssociationCount"] = int(
                    target.get("continuePlaybackAssociationCount") or 0
                ) + 1
            if int(association.get("fadeOutTimeMs") or 0):
                target["nonzeroFadeOutAssociationCount"] = int(
                    target.get("nonzeroFadeOutAssociationCount") or 0
                ) + 1
            if int(association.get("fadeInTimeMs") or 0):
                target["nonzeroFadeInAssociationCount"] = int(
                    target.get("nonzeroFadeInAssociationCount") or 0
                ) + 1
        for source_key, target_key in (
            ("mappedChildIdsOutsideChildren", "mappedChildOutsideChildrenCount"),
            ("unmappedChildIds", "unmappedSelectorChildCount"),
            ("associationChildIdsOutsideChildren", "associationChildOutsideChildrenCount"),
        ):
            target[target_key] = int(target.get(target_key) or 0) + len(
                selector.get(source_key) or []
            )

    compact_rows: list[dict[str, Any]] = []
    for row in summary.values():
        random_status_counts = row.pop("_randomSequenceParserStatuses", None)
        random_sequence_modes = row.pop("_randomSequenceModes", None)
        random_modes = row.pop("_randomModes", None)
        random_transition_modes = row.pop("_randomTransitionModes", None)
        random_membership_statuses = row.pop(
            "_randomSequenceMembershipStatuses", None
        )
        layer_parser_statuses = row.pop("_layerParserStatuses", None)
        layer_proof_statuses = row.pop("_layerProofStatuses", None)
        layer_assignment_statuses = row.pop("_layerAssignmentStatuses", None)
        layer_rtpc_types = row.pop("_layerRtpcTypes", None)
        layer_rtpc_ids = sorted(row.pop("_layerRtpcIds", set()))
        parser_counts = row.pop("_selectorParserStatuses", None)
        group_type_counts = row.pop("_selectorGroupTypes", None)
        switch_mode_counts = row.pop("_selectorSwitchModes", None)
        group_ids = sorted(row.pop("_selectorGroupIds", set()))
        group_semantics = row.pop("_selectorGroupSemantics", None)
        value_semantics = row.pop("_selectorValueSemantics", None)
        if random_status_counts:
            row["randomSequenceParserStatuses"] = dict(
                sorted(random_status_counts.items())
            )
        if random_sequence_modes:
            row["randomSequenceModes"] = dict(sorted(random_sequence_modes.items()))
        if random_modes:
            row["randomModes"] = dict(sorted(random_modes.items()))
        if random_transition_modes:
            row["randomTransitionModes"] = dict(
                sorted(random_transition_modes.items())
            )
        if random_membership_statuses:
            row["randomSequenceMembershipStatuses"] = dict(
                sorted(random_membership_statuses.items())
            )
        if layer_parser_statuses:
            row["layerParserStatuses"] = dict(sorted(layer_parser_statuses.items()))
        if layer_proof_statuses:
            row["layerProofStatuses"] = dict(sorted(layer_proof_statuses.items()))
        if layer_assignment_statuses:
            row["layerAssignmentStatuses"] = dict(
                sorted(layer_assignment_statuses.items())
            )
        if layer_rtpc_types:
            row["layerRtpcTypes"] = dict(sorted(layer_rtpc_types.items()))
        if layer_rtpc_ids:
            row["layerRtpcIdCount"] = len(layer_rtpc_ids)
            row["layerRtpcIdsHex"] = [f"0x{value:08x}" for value in layer_rtpc_ids[:24]]
            row["layerRtpcIdsTruncated"] = len(layer_rtpc_ids) > 24
        if parser_counts:
            row["selectorParserStatuses"] = dict(sorted(parser_counts.items()))
        if group_type_counts:
            row["selectorGroupTypes"] = dict(sorted(group_type_counts.items()))
        if switch_mode_counts:
            row["selectorSwitchModes"] = dict(sorted(switch_mode_counts.items()))
        if group_ids:
            row["selectorGroupIdCount"] = len(group_ids)
            row["selectorGroupIdsHex"] = [f"0x{value:08x}" for value in group_ids[:24]]
            row["selectorGroupIdsTruncated"] = len(group_ids) > 24
        if group_semantics:
            row["selectorGroupSemantics"] = [
                group_semantics[key] for key in sorted(group_semantics)
            ]
        if value_semantics:
            values = [value_semantics[key] for key in sorted(value_semantics)]
            row["selectorSemanticValueCount"] = len(values)
            row["selectorSemanticValues"] = values[:24]
            row["selectorSemanticValuesTruncated"] = len(values) > 24
        compact_rows.append({
            key: value for key, value in row.items()
            if value not in (None, "", [], {})
        })
    return compact_rows


def exact_wwise_event_aliases(audio_index: dict[str, Any]) -> list[dict[str, Any]]:
    """Return cross-source aliases only when one hash has one exact name."""

    by_hash: dict[int, dict[str, Any]] = {}
    conflicts: set[int] = set()
    for source_key in (
        "audioDialogWwiseEventAliases",
        "voiceTableWwiseEventAliases",
        "typedUiTableWwiseEventAliases",
        "snsVoiceWwiseEventAliases",
        "skillIdDictionaryWwiseEventAliases",
    ):
        for raw_row in audio_index.get(source_key) or []:
            if not isinstance(raw_row, dict):
                continue
            try:
                event_hash = int(raw_row.get("eventHash")) & 0xFFFFFFFF
            except (TypeError, ValueError):
                continue
            name = str(raw_row.get("name") or "").strip()
            if not name:
                continue
            previous = by_hash.get(event_hash)
            if previous is not None and str(previous.get("name") or "").casefold() != name.casefold():
                conflicts.add(event_hash)
                continue
            by_hash.setdefault(event_hash, raw_row)
    for event_hash in conflicts:
        by_hash.pop(event_hash, None)
    return sorted(
        by_hash.values(),
        key=lambda row: (str(row.get("name") or "").casefold(), int(row.get("eventHash") or 0)),
    )


def _annotate_initial_rtpc_semantics(
    post_process_summary: Any,
    rtpc_names_by_hex: dict[str, str] | None,
) -> dict[str, Any]:
    """Attach exact metadata-literal names to serialized InitialRTPC rows."""

    if not isinstance(post_process_summary, dict):
        return {}
    names = {
        _selector_id_hex(key): str(value).strip()
        for key, value in (rtpc_names_by_hex or {}).items()
        if _selector_id_hex(key) and str(value).strip()
    }

    def annotate_row(raw_row: Any) -> dict[str, Any]:
        if not isinstance(raw_row, dict):
            return {}
        row = dict(raw_row)
        rtpc_hex = _selector_id_hex(row.get("rtpcIdHex") or row.get("rtpcId"))
        name = names.get(rtpc_hex)
        if name:
            row.update({
                "parameterName": name,
                "semanticNameStatus": "exactManagedStringLiteralFNV1Utf16Hash",
                "semanticEvidence": "exactInitialRtpcIdAndManagedStringLiteral",
            })
        return row

    output = dict(post_process_summary)
    if isinstance(output.get("rtpcIds"), list):
        output["rtpcIds"] = [
            annotate_row(row) for row in output["rtpcIds"]
            if isinstance(row, dict)
        ]
    if isinstance(output.get("stateRtpcNodes"), list):
        nodes: list[dict[str, Any]] = []
        for raw_node in output["stateRtpcNodes"]:
            if not isinstance(raw_node, dict):
                continue
            node = dict(raw_node)
            curves = []
            for raw_curve in raw_node.get("rtpcCurves") or ():
                curve = annotate_row(raw_curve)
                if curve:
                    curves.append(curve)
            if isinstance(raw_node.get("rtpcCurves"), list):
                node["rtpcCurves"] = curves
            nodes.append(node)
        output["stateRtpcNodes"] = nodes
    return output


def build_initial_rtpc_parameter_catalog(
    events: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate exact named InitialRTPC curves with authored Event context."""

    catalog: dict[str, dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or "").strip()
        for evidence in event.get("evidence") or ():
            if not isinstance(evidence, dict):
                continue
            post_process = evidence.get("postProcessSummary") or {}
            if not isinstance(post_process, dict):
                continue
            rtpc_rows = [
                row for row in post_process.get("rtpcIds") or ()
                if isinstance(row, dict) and row.get("parameterName")
            ]
            if not rtpc_rows:
                continue
            context_rows = [
                context for context in event.get("contexts") or ()
                if isinstance(context, dict)
            ]
            context_kinds = {
                str(context.get("kind") or "unknown")
                for context in context_rows
                if str(context.get("kind") or "")
            }
            trigger_roles = {
                str(context.get("triggerRole") or "")
                for context in context_rows
                if str(context.get("triggerRole") or "")
            }
            detailed_curves = [
                curve
                for node in post_process.get("stateRtpcNodes") or ()
                if isinstance(node, dict)
                for curve in node.get("rtpcCurves") or ()
                if isinstance(curve, dict)
            ]
            for row in rtpc_rows:
                rtpc_hex = _selector_id_hex(
                    row.get("rtpcIdHex") or row.get("rtpcId")
                )
                if not rtpc_hex:
                    continue
                target = catalog.setdefault(rtpc_hex, {
                    "rtpcId": row.get("rtpcId"),
                    "rtpcIdHex": rtpc_hex,
                    "parameterName": row.get("parameterName"),
                    "semanticNameStatus": row.get("semanticNameStatus"),
                    "semanticEvidence": row.get("semanticEvidence"),
                    "runtimeRole": "authoredInitialRtpcCurveParameter",
                    "curveCount": 0,
                    "pointCount": 0,
                    "eventIds": set(),
                    "contextKinds": set(),
                    "triggerRoles": set(),
                    "controlledProperties": Counter(),
                    "interpolationLabels": Counter(),
                })
                target["curveCount"] += int(row.get("curveCount") or 0)
                if event_id:
                    target["eventIds"].add(event_id)
                target["contextKinds"].update(context_kinds)
                target["triggerRoles"].update(trigger_roles)
                matching_curves = [
                    curve for curve in detailed_curves
                    if _selector_id_hex(
                        curve.get("rtpcIdHex") or curve.get("rtpcId")
                    ) == rtpc_hex
                ]
                for curve in matching_curves:
                    target["pointCount"] += len(curve.get("points") or [])
                    property_label = str(curve.get("parameterLabel") or "").strip()
                    if property_label:
                        target["controlledProperties"][property_label] += 1
                    interpolation_labels = target["interpolationLabels"]
                    for point in curve.get("points") or ():
                        label = str(point.get("interpolationLabel") or "").strip()
                        if label:
                            interpolation_labels[label] += 1

    output: list[dict[str, Any]] = []
    for rtpc_hex, row in sorted(catalog.items()):
        output.append({
            "rtpcId": row["rtpcId"],
            "rtpcIdHex": rtpc_hex,
            "parameterName": row["parameterName"],
            "semanticNameStatus": row["semanticNameStatus"],
            "semanticEvidence": row["semanticEvidence"],
            "runtimeRole": row["runtimeRole"],
            "curveCount": row["curveCount"],
            "pointCount": row["pointCount"],
            "eventCount": len(row["eventIds"]),
            "eventIds": sorted(row["eventIds"])[:24],
            "eventIdsTruncated": len(row["eventIds"]) > 24,
            "contextKinds": sorted(row["contextKinds"]),
            "triggerRoles": sorted(row["triggerRoles"]),
            "controlledProperties": dict(sorted(row["controlledProperties"].items())),
            "interpolationLabels": dict(sorted(row["interpolationLabels"].items())),
            "evidenceBoundary": (
                "Exact metadata-literal hash and serialized InitialRTPC curve rows; "
                "Event/context ownership is authored placement, not live parameter "
                "updates, selected media, or audible DSP output."
            ),
        })
    return output


def _evidence_object_types(evidence: dict[str, Any]) -> dict[str, int]:
    raw = evidence.get("objectTypeCounts")
    if isinstance(raw, dict):
        return {str(key): int(value) for key, value in raw.items() if isinstance(value, int)}
    return {}


def wwise_event_action_profile(evidence_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify complete current-bank Action objects by playback effect.

    Wwise v150 Play and Post Event are the only operations that introduce a
    downward playback edge. Every other typed Action is library control; the
    v150 bank reader now preserves its exact control tail when supported, while
    unknown/truncated tails remain visibly fail-closed. An Event with a
    completely parsed zero-length Action list is an inert library definition,
    not unknown audio playback.
    """
    playback_operation_types = {0x0400, 0x2100}
    operation_types: list[int] = []
    operation_labels: list[str] = []
    operation_labels_by_type: dict[int, set[str]] = defaultdict(set)
    untyped_action_count = 0
    for evidence in evidence_rows:
        for action in evidence.get("actionEvidence") or []:
            if not isinstance(action, dict):
                continue
            operation_label = str(action.get("operation") or "")
            try:
                operation_type = int(action.get("actionType")) & 0xFF00
            except (TypeError, ValueError):
                untyped_action_count += 1
                if operation_label:
                    operation_labels.append(operation_label)
                continue
            operation_types.append(operation_type)
            resolved_label = operation_label or f"operation0x{operation_type:04x}"
            operation_labels.append(resolved_label)
            operation_labels_by_type[operation_type].add(resolved_label)
    has_playback = any(value in playback_operation_types for value in operation_types) or any(
        int(evidence.get("rootPlayActionCount") or 0) > 0 for evidence in evidence_rows
    )
    has_control = any(value not in playback_operation_types for value in operation_types)
    if has_playback and has_control:
        role = "mixedPlaybackAndControl"
    elif has_playback:
        role = "playback"
    elif has_control and untyped_action_count == 0:
        role = "controlOnly"
    else:
        complete_empty_definition = bool(evidence_rows) and all(
            str(evidence.get("traversalStatus") or "") == "complete"
            and isinstance(evidence.get("actionDispatchEvidence"), dict)
            and isinstance(
                (evidence.get("actionDispatchEvidence") or {}).get("serializedActionCount"),
                int,
            )
            and int((evidence.get("actionDispatchEvidence") or {})["serializedActionCount"]) == 0
            and not (evidence.get("actionEvidence") or [])
            for evidence in evidence_rows
        )
        role = "emptyEventDefinition" if complete_empty_definition else "unresolved"
    return {
        "role": role,
        "operationTypes": sorted(set(operation_types)),
        "operationTypesHex": [f"0x{value:04x}" for value in sorted(set(operation_types))],
        "operationLabels": sorted(set(operation_labels)),
        "operationRows": [
            {
                "operationType": value,
                "operationTypeHex": f"0x{value:04x}",
                "operationLabels": sorted(operation_labels_by_type[value]),
            }
            for value in sorted(operation_labels_by_type)
        ],
        "untypedActionCount": untyped_action_count,
    }


def annotate_wwise_action_control_evidence(
    evidence_by_event: dict[str, list[dict[str, Any]]],
    selector_groups: Iterable[dict[str, Any]] | None,
    rtpc_names_by_hex: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Attach conservative semantic names to serialized State/Switch actions.

    The HIRC parser owns the raw IDs.  This join only uses selector groups and
    values already backed by current-build native evidence; an absent group or
    value remains explicitly unresolved rather than being guessed from an
    event name.
    """

    groups_by_hex = _selector_group_catalog(selector_groups)
    rtpc_names_by_hex = {
        _selector_id_hex(key): str(value).strip()
        for key, value in (rtpc_names_by_hex or {}).items()
        if _selector_id_hex(key) and str(value).strip()
    }
    action_count = 0
    typed_count = 0
    group_reference_count = 0
    group_match_count = 0
    value_reference_count = 0
    value_match_count = 0
    shared_rtpc_parameter_id_match_count = 0
    shared_rtpc_parameter_ids: set[int] = set()
    named_initial_rtpc_match_count = 0
    referenced_groups: dict[str, dict[str, Any]] = {}

    for evidence_rows in evidence_by_event.values():
        for evidence in evidence_rows:
            raw_actions = evidence.get("actionEvidence") or []
            if not isinstance(raw_actions, list):
                continue
            action_rows: list[dict[str, Any]] = []
            for raw_action in raw_actions:
                if not isinstance(raw_action, dict):
                    continue
                action = dict(raw_action)
                operation = str(action.get("operation") or "")
                if operation not in {"play", "playEvent"}:
                    action_count += 1
                    if action.get("actionControlParserStatus") == "typedExactV150":
                        typed_count += 1
                if operation in {"setState", "setSwitch"}:
                    group_reference_count += 1
                    group_hex = _selector_id_hex(
                        action.get("groupIdHex") or action.get("groupId")
                    )
                    group = groups_by_hex.get(group_hex)
                    if group is None:
                        action["controlGroupSemanticStatus"] = "unresolvedGroupId"
                    else:
                        group_match_count += 1
                        referenced_groups.setdefault(group_hex, {
                            key: group.get(key)
                            for key in (
                                "groupId", "groupIdHex", "groupType", "semanticRole",
                                "semanticLabel", "semanticEvidence",
                                "authoredGroupNameStatus", "runtimeScope",
                                "runtimeObservationStatus",
                            )
                            if group.get(key) is not None
                        })
                        action["controlGroupSemantic"] = _compact_selector_group(group)
                        value_hex = _selector_id_hex((
                            action.get("stateIdHex")
                            if operation == "setState"
                            else action.get("switchIdHex")
                        ))
                        if value_hex:
                            value_reference_count += 1
                            value_match = next(
                                (
                                    raw_value
                                    for raw_value in group.get("values") or ()
                                    if isinstance(raw_value, dict)
                                    and value_hex in _selector_value_ids(raw_value)
                                    and _has_selector_value_semantics(raw_value)
                                ),
                                None,
                            )
                            if value_match is None:
                                action["controlValueSemanticStatus"] = "unresolvedValueId"
                            else:
                                value_match_count += 1
                                action["controlValueSemantic"] = _compact_selector_value(
                                    value_match
                                )
                if operation in {"setGameParameter", "resetGameParameter"}:
                    parameter_hex = _selector_id_hex(
                        action.get("idExtHex") or action.get("idExt")
                    )
                    post_process = evidence.get("postProcessSummary") or {}
                    if not isinstance(post_process, dict):
                        post_process = {}
                    rtpc_match = next(
                        (
                            row for row in post_process.get("rtpcIds") or ()
                            if isinstance(row, dict)
                            and _selector_id_hex(
                                row.get("rtpcIdHex") or row.get("rtpcId")
                            ) == parameter_hex
                        ),
                        None,
                    )
                    if parameter_hex and rtpc_match is not None:
                        shared_rtpc_parameter_id_match_count += 1
                        try:
                            shared_rtpc_parameter_ids.add(
                                int(rtpc_match.get("rtpcId")) & 0xFFFFFFFF
                            )
                        except (TypeError, ValueError):
                            pass
                        parameter_name = rtpc_names_by_hex.get(parameter_hex)
                        if parameter_name:
                            named_initial_rtpc_match_count += 1
                        action["initialRtpcSemantic"] = {
                            "rtpcId": rtpc_match.get("rtpcId"),
                            "rtpcIdHex": parameter_hex,
                            "curveCount": int(rtpc_match.get("curveCount") or 0),
                            "parameterName": parameter_name,
                            "semanticNameStatus": (
                                "exactManagedStringLiteralFNV1Utf16Hash"
                                if parameter_name else "unresolvedGameParameterName"
                            ),
                            "semanticEvidence": (
                                "sameEventInitialRtpcIdAndExactManagedStringLiteral"
                                if parameter_name else "sameEventInitialRtpcId"
                            ),
                            "runtimeRole": "authoredInitialRtpcCurveTarget",
                        }
                action_rows.append(action)
            evidence["actionEvidence"] = action_rows

    return {
        "schemaVersion": 1,
        "actionCount": action_count,
        "typedExactActionCount": typed_count,
        "groupReferenceCount": group_reference_count,
        "groupSemanticMatchCount": group_match_count,
        "valueReferenceCount": value_reference_count,
        "valueSemanticMatchCount": value_match_count,
        "sharedRtpcParameterIdMatchCount": shared_rtpc_parameter_id_match_count,
        "sharedRtpcParameterIdCount": len(shared_rtpc_parameter_ids),
        "namedInitialRtpcMatchCount": named_initial_rtpc_match_count,
        "referencedGroupCount": len(referenced_groups),
        "referencedGroups": [
            referenced_groups[key] for key in sorted(referenced_groups)
        ],
        "evidenceBoundary": (
            "Group/value labels are joined only from current-build native selector "
            "evidence; an unresolved ID remains numeric. Set/Reset GameParameter "
            "rows may join the same event's exact InitialRTPC ID. A parameter name "
            "is attached only when its FNV-1/UTF-16 hash matches an exact current "
            "metadata literal; live values remain unresolved. Static catalog joins "
            "do not observe live setter calls, selected branches, or runtime state."
        ),
    }


def build_event_rows(
    audio_index: dict[str, Any],
    contexts: dict[str, list[dict[str, Any]]],
    selector_groups: Iterable[dict[str, Any]] | None = None,
    rtpc_names_by_hex: dict[str, str] | None = None,
    metadata_event_symbols: Iterable[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, Any]]]:
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_name_sources = {
        str(key).strip().lower(): sorted({str(value) for value in values if str(value)})
        for key, values in (audio_index.get("eventNameSources") or {}).items()
        if str(key).strip() and isinstance(values, list)
    }
    candidate_seen: dict[str, set[tuple[str, str]]] = defaultdict(set)
    hashes: dict[str, int] = {}
    authored_name_keys = {
        str(value or "").strip().casefold()
        for value in audio_index.get("eventNames") or []
        if str(value or "").strip()
    }
    metadata_alias_by_hash: dict[int, dict[str, Any]] = {}
    for raw_alias in metadata_event_symbols or ():
        if not isinstance(raw_alias, dict):
            continue
        try:
            event_hash = int(raw_alias.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        name = str(raw_alias.get("name") or raw_alias.get("metadataField") or "").strip()
        if not name:
            continue
        previous = metadata_alias_by_hash.get(event_hash)
        if previous is not None and str(previous.get("name") or "").casefold() != name.casefold():
            # The catalog is expected to have already failed closed, but keep
            # this projection boundary defensive if called independently.
            metadata_alias_by_hash.pop(event_hash, None)
            continue
        metadata_alias_by_hash[event_hash] = dict(raw_alias)
    for entry in audio_index.get("events") or []:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("eventId") or entry.get("id") or "").strip().lower()
        if not key:
            continue
        try:
            hashes[key] = int(entry.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            pass
        compact = compact_media(entry)
        marker = (str(compact.get("mediaId") or compact.get("id") or ""), str(compact.get("src") or ""))
        if marker in candidate_seen[key]:
            continue
        candidate_seen[key].add(marker)
        candidates[key].append(compact)

    evidence_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bank_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for evidence in audio_index.get("eventEvidence") or []:
        if not isinstance(evidence, dict):
            continue
        key = str(evidence.get("eventId") or "").strip().lower()
        if not key:
            continue
        try:
            event_hash = int(evidence.get("eventHash")) & 0xFFFFFFFF
            hashes.setdefault(key, event_hash)
        except (TypeError, ValueError):
            event_hash = 0
        object_types = _evidence_object_types(evidence)
        selection_types = [
            HIRC_OBJECT_TYPE_LABELS.get(int(type_id), f"type{type_id}")
            for type_id in evidence.get("selectionObjectTypes") or []
            if isinstance(type_id, int)
        ]
        compact_evidence = {
            "bankId": evidence.get("bankId"),
            "bankVersion": evidence.get("bankVersion"),
            "bank": evidence.get("bank"),
            "edgeParser": evidence.get("edgeParser"),
            "traversalStatus": evidence.get("traversalStatus") or "unknown",
            "actionIds": evidence.get("actionIds") or [],
            "actionEvidence": evidence.get("actionEvidence") or [],
            "actionDispatchEvidence": evidence.get("actionDispatchEvidence") or {},
            "rootPlayActionCount": int(evidence.get("rootPlayActionCount") or 0),
            "rootStopActionCount": int(evidence.get("rootStopActionCount") or 0),
            "visitedObjectCount": len(evidence.get("visitedObjectIds") or []),
            "mediaIds": evidence.get("mediaIds") or [],
            "objectTypeCounts": object_types,
            "selectionContainerTypes": selection_types,
            "containerEvidence": compact_container_evidence(
                evidence.get("containerEvidence") or [],
                selector_groups,
            ),
            "musicNodeEvidence": evidence.get("musicNodeEvidence") or [],
            "postProcessSummary": _annotate_initial_rtpc_semantics(
                evidence.get("postProcessSummary") or {},
                rtpc_names_by_hex,
            ),
            "sourceObjectSummary": evidence.get("sourceObjectSummary") or {},
            "nonMediaSourceEvidence": evidence.get("nonMediaSourceEvidence") or [],
            "unresolvedNodes": evidence.get("unresolvedNodes") or [],
            "source": evidence.get("source") or "wwiseHirc",
            "nestedReferenceConfidence": evidence.get("nestedReferenceConfidence") or "unknown",
        }
        evidence_by_event[key].append(compact_evidence)
        bank_name = str(evidence.get("bank") or "")
        try:
            bank_id = int(evidence.get("bankId") or 0)
        except (TypeError, ValueError):
            bank_id = 0
        bank_key = (bank_name, bank_id)
        bank = bank_rows.setdefault(bank_key, {
            "bank": bank_name,
            "bankId": bank_id,
            "eventIds": set(),
            "mediaIds": set(),
            "selectionEventIds": set(),
            "visitedObjectTypeOccurrences": Counter(),
        })
        bank["eventIds"].add(key)
        bank["mediaIds"].update(str(value) for value in evidence.get("mediaIds") or [])
        if selection_types:
            bank["selectionEventIds"].add(key)
        bank["visitedObjectTypeOccurrences"].update(object_types)

    current_wwise_event_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in audio_index.get("wwiseEventInventory") or []
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    binary_managed_literal_keys = {
        str(value or "").strip().lower()
        for value in audio_index.get("binaryManagedEventNames") or []
        if str(value or "").strip()
    }
    managed_literals_without_event_or_consumer = {
        key
        for key in binary_managed_literal_keys
        if identifiers.audio_hash_generator_compute(key) not in current_wwise_event_hashes
        and key not in contexts
        and key not in candidates
        and key not in evidence_by_event
    }

    # Seed every authored Event name before consuming the compact raw HIRC
    # inventory.  ``audio_index.events`` contains only Event/media rows, so an
    # authored control Event or an Event whose decoded leaves are absent may
    # otherwise exist twice: once under its authored name as falsely missing,
    # and once under ``hashed-event:0x...`` as a resolved Wwise object.
    for value in audio_index.get("eventNames") or []:
        display = str(value or "").strip()
        if not display:
            continue
        key = display.lower()
        if key in managed_literals_without_event_or_consumer:
            continue
        hashes.setdefault(key, identifiers.audio_hash_generator_compute(display))
    # Exact metadata field symbols are static Event identities. Seed them at
    # the same stage as authored names so hash-only HIRC rows canonicalize to
    # the symbol without pretending that a trigger/caller was recovered.
    for event_hash, alias in metadata_alias_by_hash.items():
        display = str(alias.get("name") or alias.get("metadataField") or "").strip()
        if not display:
            continue
        key = display.lower()
        hashes.setdefault(key, event_hash)
        sources = event_name_sources.setdefault(key, [])
        source = "il2cppMetadataFieldName"
        if source not in sources:
            sources.append(source)
            sources.sort()
    for value in contexts:
        display = str(value or "").strip()
        if (
            not display
            or display.startswith("#0x")
            or display.lower().startswith("hashed-event:0x")
        ):
            continue
        key = display.lower()
        hashes.setdefault(key, identifiers.audio_hash_generator_compute(display))
    context_authored_display_names: dict[str, str] = {}
    for context_key, context_rows in contexts.items():
        expected_hash = None
        if str(context_key).lower().startswith("hashed-event:0x"):
            try:
                expected_hash = int(str(context_key).rsplit("0x", 1)[1], 16) & 0xFFFFFFFF
            except ValueError:
                expected_hash = None
        for context in context_rows or []:
            if not isinstance(context, dict):
                continue
            display = str(context.get("authoredEventName") or "").strip()
            if not display:
                continue
            event_hash = identifiers.audio_hash_generator_compute(display)
            if expected_hash is not None and event_hash != expected_hash:
                continue
            key = display.lower()
            hashes.setdefault(key, event_hash)
            context_authored_display_names.setdefault(key, display)
            sources = event_name_sources.setdefault(key, [])
            source = str(context.get("authoredEventNameEvidence") or "typedTriggerContext")
            if source not in sources:
                sources.append(source)
                sources.sort()

    # Wwise banks also contain Event objects whose uint32 identity has no
    # recovered string or gameplay callsite yet. Keep those objects visible
    # under a stable hash key and use their typed HIRC traversal to recover
    # media relations without inventing a trigger name or ownership location.
    known_key_by_hash = {event_hash: key for key, event_hash in hashes.items()}
    authored_inventory_hashes = set(known_key_by_hash)
    for alias in exact_wwise_event_aliases(audio_index):
        if not isinstance(alias, dict):
            continue
        try:
            event_hash = int(alias.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        event_name = str(alias.get("name") or "").strip()
        if not event_name or event_hash in authored_inventory_hashes:
            continue
        key = event_name.lower()
        known_key_by_hash.setdefault(event_hash, key)
        hashes[key] = event_hash

    # Older/base audio indexes may already contain a hash-only Event evidence
    # row before LevelScript, Timeline, or table semantics recover its exact
    # authored name. Move that evidence and any media candidates onto the
    # canonical named key so one uint32 Wwise Event is emitted only once.
    for old_key in list(hashes):
        if not old_key.startswith("hashed-event:0x"):
            continue
        event_hash = hashes.get(old_key)
        target_key = known_key_by_hash.get(event_hash) if event_hash is not None else None
        if not target_key or target_key == old_key:
            continue
        for evidence in evidence_by_event.pop(old_key, []):
            marker = (
                str(evidence.get("bank") or ""),
                int(evidence.get("bankId") or 0),
            )
            if any(
                (
                    str(existing.get("bank") or ""),
                    int(existing.get("bankId") or 0),
                ) == marker
                for existing in evidence_by_event.get(target_key, [])
            ):
                continue
            evidence_by_event[target_key].append(evidence)
        for candidate in candidates.pop(old_key, []):
            marker = (
                str(candidate.get("mediaId") or candidate.get("id") or ""),
                str(candidate.get("src") or ""),
            )
            if marker in candidate_seen[target_key]:
                continue
            candidate_seen[target_key].add(marker)
            candidates[target_key].append(candidate)
        candidate_seen.pop(old_key, None)
        hashes.pop(old_key, None)
    entry_by_media_id: dict[int, dict[str, Any]] = {}
    hotfix_entries_by_media_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry in audio_index.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        raw_id = entry.get("mediaId") or entry.get("id")
        try:
            media_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        entry_by_media_id.setdefault(media_id, entry)
        if (
            not entry.get("eventId")
            and str(entry.get("sourceBlock") or "") == "hotfix-audio"
        ):
            hotfix_entries_by_media_id[media_id].append(entry)
    for inventory in audio_index.get("wwiseEventInventory") or []:
        if not isinstance(inventory, dict):
            continue
        try:
            event_hash = int(inventory.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        key = known_key_by_hash.setdefault(event_hash, identifiers.hashed_event_key(event_hash))
        hashes[key] = event_hash
        object_types = _evidence_object_types(inventory)
        selection_types = [
            HIRC_OBJECT_TYPE_LABELS.get(int(type_id), f"type{type_id}")
            for type_id in inventory.get("selectionObjectTypes") or []
            if isinstance(type_id, int)
        ]
        compact_evidence = {
            "bankId": inventory.get("bankId"),
            "bankVersion": inventory.get("bankVersion"),
            "bank": inventory.get("bank"),
            "edgeParser": "wwise150TypedCompactObjectInventory",
            "traversalStatus": inventory.get("traversalStatus") or "unknown",
            "actionIds": inventory.get("actionIds") or [],
            "actionEvidence": inventory.get("actionEvidence") or [],
            "actionDispatchEvidence": inventory.get("actionDispatchEvidence") or {},
            "rootPlayActionCount": int(inventory.get("rootPlayActionCount") or 0),
            "rootStopActionCount": int(inventory.get("rootStopActionCount") or 0),
            "visitedObjectCount": int(inventory.get("visitedObjectCount") or 0),
            "mediaIds": inventory.get("mediaIds") or [],
            "objectTypeCounts": object_types,
            "selectionContainerTypes": selection_types,
            "postProcessSummary": inventory.get("postProcessSummary") or {},
            "sourceObjectSummary": inventory.get("sourceObjectSummary") or {},
            "nonMediaSourceEvidence": inventory.get("nonMediaSourceEvidence") or [],
            "unresolvedNodes": inventory.get("unresolvedNodeSamples") or [],
            "unresolvedNodeCount": int(inventory.get("unresolvedNodeCount") or 0),
            "source": "wwiseHircObjectInventory",
            "nestedReferenceConfidence": (
                "typedExact"
                if inventory.get("traversalStatus") == "complete"
                else "typedPartial"
            ),
            "eventIdentityStatus": "wwiseObjectWithoutRecoveredTriggerName",
        }
        evidence_marker = (
            str(compact_evidence.get("bank") or ""),
            int(compact_evidence.get("bankId") or 0),
        )
        if not any(
            (
                str(existing.get("bank") or ""),
                int(existing.get("bankId") or 0),
            ) == evidence_marker
            for existing in evidence_by_event.get(key, [])
        ):
            evidence_by_event[key].append(compact_evidence)
        root_action_ids = sorted({
            int(row.get("rootActionId"))
            for row in inventory.get("actionEvidence") or []
            if isinstance(row, dict) and isinstance(row.get("rootActionId"), int)
        })
        relation_types = [
            str(value)
            for value in inventory.get("mediaRelationTypes") or []
            if str(value)
        ]
        for media_id in inventory.get("mediaIds") or []:
            try:
                media_id = int(media_id)
            except (TypeError, ValueError):
                continue
            entry = entry_by_media_id.get(media_id)
            if not entry:
                continue
            compact = compact_media(entry)
            compact.update({
                "id": key,
                "eventId": key,
                "eventHash": event_hash,
                "mediaId": media_id,
                "bankId": inventory.get("bankId"),
                "bank": inventory.get("bank"),
                "source": "wwiseHircObjectInventory",
                "wwiseMediaEvidence": [{
                    "mediaId": media_id,
                    "rootActionIds": root_action_ids,
                    "relationTypes": relation_types,
                    "bankId": inventory.get("bankId"),
                    "bankPackage": PurePosixPath(str(inventory.get("bank") or "").replace("\\", "/")).name,
                }],
            })
            marker = (str(media_id), str(compact.get("src") or ""))
            if marker in candidate_seen[key]:
                continue
            candidate_seen[key].add(marker)
            candidates[key].append(compact)
        bank_name = str(inventory.get("bank") or "")
        bank_id = int(inventory.get("bankId") or 0)
        bank = bank_rows.setdefault((bank_name, bank_id), {
            "bank": bank_name,
            "bankId": bank_id,
            "eventIds": set(),
            "mediaIds": set(),
            "selectionEventIds": set(),
            "visitedObjectTypeOccurrences": Counter(),
        })
        bank["eventIds"].add(key)
        bank["mediaIds"].update(str(value) for value in inventory.get("mediaIds") or [])
        if selection_types:
            bank["selectionEventIds"].add(key)
        bank["visitedObjectTypeOccurrences"].update(object_types)

    display_names: dict[str, str] = {}
    for value in audio_index.get("eventNames") or []:
        display = str(value or "").strip()
        if not display:
            continue
        key = display.lower()
        if key in managed_literals_without_event_or_consumer:
            continue
        display_names.setdefault(key, display)
    for alias in metadata_alias_by_hash.values():
        display = str(alias.get("name") or alias.get("metadataField") or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
    for alias in exact_wwise_event_aliases(audio_index):
        if not isinstance(alias, dict):
            continue
        display = str(alias.get("name") or "").strip()
        if display:
            display_names.setdefault(display.lower(), display)
    for key, display in context_authored_display_names.items():
        display_names.setdefault(key, display)
    for entry in audio_index.get("events") or []:
        if not isinstance(entry, dict):
            continue
        display = str(entry.get("eventId") or entry.get("id") or "").strip()
        if not display:
            continue
        key = display.lower()
        try:
            event_hash = int(entry.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            event_hash = None
        if (
            key.startswith("hashed-event:0x")
            and event_hash is not None
            and known_key_by_hash.get(event_hash, key) != key
        ):
            continue
        display_names.setdefault(key, display)
    exact_alias_by_hash = {
        int(alias.get("eventHash")) & 0xFFFFFFFF: alias
        for alias in exact_wwise_event_aliases(audio_index)
        if isinstance(alias, dict) and isinstance(alias.get("eventHash"), int)
    }
    all_names = set(display_names)
    all_names.update(candidates)
    all_names.update(evidence_by_event)
    for context_key in contexts:
        if context_key.startswith("#0x"):
            continue
        if context_key.startswith("hashed-event:0x"):
            try:
                context_hash = int(context_key.rsplit("0x", 1)[1], 16) & 0xFFFFFFFF
            except ValueError:
                context_hash = None
            if (
                context_hash is not None
                and known_key_by_hash.get(context_hash, context_key) != context_key
            ):
                continue
        all_names.add(context_key)
    # Numeric contexts attach to whichever named or hash-only Event already
    # owns that uint32.  Emit a synthetic row only for an authored hash absent
    # from every available bank, rather than duplicating it as a #0x... row.
    known_hashes = set(hashes.values())
    for context_key in contexts:
        if not context_key.startswith("#0x"):
            continue
        try:
            event_hash = int(context_key[1:], 16) & 0xFFFFFFFF
        except ValueError:
            continue
        if event_hash in known_hashes:
            continue
        synthetic_key = identifiers.hashed_event_key(event_hash)
        all_names.add(synthetic_key)
        hashes[synthetic_key] = event_hash
        known_hashes.add(event_hash)
    rows: list[dict[str, Any]] = []
    media_to_events: dict[str, list[str]] = defaultdict(list)
    bank_inventory = audio_index.get("hircSummary") or {}
    bank_package_count = int(bank_inventory.get("packageCount") or 0)
    bank_package_fingerprint = str(bank_inventory.get("packageFingerprint") or "")
    for key in sorted(all_names):
        event_candidates = list(candidates.get(key, []))
        candidate_sources = {
            str(candidate.get("src") or candidate.get("rel") or "")
            for candidate in event_candidates
        }
        # A HotfixAudio package replaces media by numeric Wwise media id. If
        # the replacement bytes differ from the base package, both decoded
        # occurrences must remain visible, but both inherit the exact Event
        # relation already proven for that media id. Do this only for typed
        # HotfixAudio provenance; generic cross-bank id collisions are not
        # merged.
        for base_candidate in list(event_candidates):
            try:
                media_id = int(base_candidate.get("mediaId") or base_candidate.get("id"))
            except (TypeError, ValueError):
                continue
            for replacement_entry in hotfix_entries_by_media_id.get(media_id, []):
                replacement = compact_media(replacement_entry)
                replacement_src = str(replacement.get("src") or replacement.get("rel") or "")
                if not replacement_src or replacement_src in candidate_sources:
                    continue
                replacement.update({
                    "id": key,
                    "eventId": key,
                    "eventHash": hashes.get(key),
                    "mediaId": media_id,
                    "hotfixMediaReplacement": True,
                    "mediaResolutionEvidence": "hotfixPackageMediaIdReplacesBaseMediaId",
                    "wwiseMediaEvidence": base_candidate.get("wwiseMediaEvidence") or [],
                })
                event_candidates.append(replacement)
                candidate_sources.add(replacement_src)
        event_candidates = sorted(
            event_candidates,
            key=lambda row: (int(row.get("mediaId") or 0), str(row.get("src") or "")),
        )
        content_counts = Counter(
            str(row.get("contentSha256") or "")
            for row in event_candidates
            if row.get("contentSha256")
        )
        for candidate in event_candidates:
            content_hash = str(candidate.get("contentSha256") or "")
            if content_hash and content_counts[content_hash] > 1:
                candidate["contentEquivalentCount"] = content_counts[content_hash]
        unique_content_keys = {
            str(row.get("contentSha256") or row.get("src") or row.get("mediaId") or "")
            for row in event_candidates
            if row.get("contentSha256") or row.get("src") or row.get("mediaId")
        }
        for candidate in event_candidates:
            marker = str(candidate.get("src") or candidate.get("rel") or candidate.get("mediaId") or "")
            if marker and key not in media_to_events[marker]:
                media_to_events[marker].append(key)
        event_contexts = list(contexts.get(key, []))
        event_hash = hashes.get(key)
        authored_event_hash = (
            event_hash
            if event_hash is not None
            else identifiers.audio_hash_generator_compute(display_names.get(key, key))
        )
        if event_hash is not None:
            event_contexts.extend(contexts.get(identifiers.event_hash_context_key(event_hash), []))
            hash_only_key = identifiers.hashed_event_key(event_hash)
            if hash_only_key != key:
                event_contexts.extend(contexts.get(hash_only_key, []))
        authored_custom_states = {
            str(context.get("triggerCustomState") or "").casefold()
            for context in event_contexts
            if isinstance(context, dict)
            and context.get("kind") == "interactiveComponentTrigger"
            and context.get("triggerCustomState")
        }
        event_contexts = [
            context for context in event_contexts
            if not (
                isinstance(context, dict)
                and context.get("kind") == "nativeCustomStateCallsite"
                and str(context.get("customStateName") or "").casefold()
                not in authored_custom_states
            )
        ]
        evidence_rows = evidence_by_event.get(key, [])
        action_profile = wwise_event_action_profile(evidence_rows)
        playback_role = str(action_profile["role"])
        identity_alias = exact_alias_by_hash.get(event_hash) if event_hash is not None else None
        metadata_alias = metadata_alias_by_hash.get(event_hash) if event_hash is not None else None
        character_animation_owner_ids = sorted({
            str(context.get("ownerId") or "")
            for context in event_contexts
            if context.get("kind") == "characterAnimation" and context.get("ownerId")
        })
        enemy_animation_owner_ids = sorted({
            str(context.get("ownerId") or "")
            for context in event_contexts
            if context.get("kind") == "enemyAnimation" and context.get("ownerId")
        })
        animation_functions = sorted({
            str(value)
            for context in event_contexts
            for value in context.get("animationFunctions") or []
            if str(value)
        })
        custom_footstep_variants = aggregate_custom_footstep_context_variants(event_contexts)
        animation_context_scope = (
            "sharedPlayableCharacters" if len(character_animation_owner_ids) > 1
            else "singlePlayableCharacter" if character_animation_owner_ids
            else "sharedEnemyTemplates" if len(enemy_animation_owner_ids) > 1
            else "singleEnemyTemplate" if enemy_animation_owner_ids
            else ""
        )
        selection_types = sorted({
            value
            for evidence in evidence_rows
            for value in evidence.get("selectionContainerTypes") or []
        })
        media_relation_types = sorted({
            str(relation)
            for candidate in event_candidates
            for media_evidence in candidate.get("wwiseMediaEvidence") or []
            for relation in media_evidence.get("relationTypes") or []
            if str(relation)
        })
        play_root_ids = sorted({
            int(root_action_id)
            for candidate in event_candidates
            for media_evidence in candidate.get("wwiseMediaEvidence") or []
            for root_action_id in media_evidence.get("rootActionIds") or []
            if isinstance(root_action_id, int)
        })
        traversal_status = (
            "partial" if any(row.get("traversalStatus") == "partial" for row in evidence_rows)
            else "complete" if evidence_rows else "unresolved"
        )
        branch_relations = [value for value in media_relation_types if value != "directSound"]
        if branch_relations or selection_types:
            runtime_selection = "runtimeBranchUnresolved"
        elif len(play_root_ids) > 1:
            runtime_selection = "multiplePlayRootsTimingUnresolved"
        elif len(event_candidates) == 1:
            runtime_selection = "singlePossibleMedia"
        elif event_candidates:
            runtime_selection = "multiplePossibleMediaUnresolved"
        else:
            runtime_selection = "unresolved"
        category, category_evidence = event_category_with_evidence(key)
        if metadata_alias and category != "unknown" and category_evidence in {
            "namePrefix", "normalizedNamePrefix",
        }:
            category_evidence = "exactIl2CppMetadataFieldNamePrefix"
        category_name_evidence = (
            category_evidence
            if category_evidence.startswith(("authored", "normalizedAuthored"))
            else ""
        )
        if str(key).lstrip().startswith(":") and category != "unknown":
            category_evidence = (
                "normalizedNamePrefix"
                if category_evidence == "namePrefix"
                else f"normalized{category_evidence[0].upper()}{category_evidence[1:]}"
            )
        if (
            (category == "unknown" or category_name_evidence)
            and (identity_alias or {}).get("dictionaryKind") == "skill_id"
        ):
            category = "sfx"
            category_evidence = "exactSkillIdDictionaryEventIdentity"
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") == "projectileSoundField"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactProjectileSoundField"
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") == "spawnerPreWarnAudio"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactSpawnerPreWarnAudioField"
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") == "patrolSubActionPlayAudio"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactPatrolSubPlayAudioData"
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") == "charInteractAudioEvent"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactCharInteractAudioEventField"
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") == "physicsAudioComponentEvent"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactPhysicsAudioComponentEventField"
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") in {
                "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent"
            }
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "sfx"
            category_evidence = "exactModelViewStateAudioBehavior"
        if (
            category == "unknown" or category_name_evidence
        ) and any(
            context.get("kind") in {
                "audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant",
                "responsiveDialogToneVariant",
                "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent",
                "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent",
                "responsiveVoiceEventTemplate", "voiceTableWwiseEvent", "snsVoiceMessageEvent",
            }
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "voice"
            category_evidence = (
                "exactTypedVoiceTableWwiseEventField"
                if any(
                    context.get("kind") in {
                        "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent",
                        "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent",
                        "responsiveVoiceEventTemplate", "voiceTableWwiseEvent", "snsVoiceMessageEvent",
                    }
                    for context in event_contexts
                    if isinstance(context, dict)
                )
                else "exactAudioDialogVoiceIdentity"
            )
        if (category == "unknown" or category_name_evidence) and any(
            context.get("kind") == "tableEventHash"
            and context.get("table") == "AudioDialogCustomEventTable"
            for context in event_contexts
            if isinstance(context, dict)
        ):
            category = "control"
            category_evidence = "exactAudioDialogLifecycleEventField"
        if key.startswith("hashed-event:0x"):
            event_identity_status = (
                "authoredHashMatchedWwiseObject"
                if event_contexts
                else "wwiseObjectWithoutRecoveredTriggerName"
            )
        else:
            event_identity_status = (
                "recoveredIl2CppMetadataEventSymbol"
                if (
                    metadata_alias
                    and not identity_alias
                    and key not in authored_name_keys
                    and key not in context_authored_display_names
                )
                else "recoveredAuthoredName"
            )
        (
            purpose_knowledge_status,
            purpose_investigation_priority,
            playback_location_status,
        ) = purpose.classify_event_purpose(
            event_contexts,
            playback_role,
            identity_alias,
        )
        rows.append({
            "id": key,
            "name": display_names.get(key, key),
            "hash": event_hash,
            "category": category,
            "categoryEvidence": category_evidence,
            "categoryNameEvidence": category_name_evidence,
            "foundInWwise": bool(evidence_rows),
            "audioLibraryResolutionStatus": (
                "resolvedWwiseEventObject"
                if evidence_rows
                else "eventHashAbsentFromScannedBankSet"
            ),
            "eventIdentityStatus": event_identity_status,
            "eventNameEvidence": (
                (identity_alias or {}).get("evidence")
                or (metadata_alias or {}).get("evidence")
            ),
            "eventNameSourceKind": (
                "skillIdDictionary"
                if (identity_alias or {}).get("dictionaryKind") == "skill_id"
                else "il2CppMetadataField"
                if metadata_alias
                else None
            ),
            "eventNameCollectionSources": event_name_sources.get(key, []),
            "eventNameMetadataField": (metadata_alias or {}).get("metadataField"),
            "eventNameMetadataDeclaringType": (metadata_alias or {}).get("metadataDeclaringType"),
            "eventNameMetadataFieldToken": (metadata_alias or {}).get("metadataFieldToken"),
            "identityOnlyPlaybackPlacementStatus": (identity_alias or {}).get("playbackPlacementStatus"),
            "identityNumericSkillIds": (identity_alias or {}).get("numericSkillIds") or [],
            "identityTableSources": (identity_alias or {}).get("tableSources") or [],
            "identitySkillDataSources": (identity_alias or {}).get("skillDataSources") or [],
            "playbackRole": playback_role,
            "wwiseActionOperationTypes": action_profile["operationTypes"],
            "wwiseActionOperationTypesHex": action_profile["operationTypesHex"],
            "wwiseActionOperations": action_profile["operationLabels"],
            "wwiseActionOperationRows": action_profile["operationRows"],
            "wwiseUntypedActionCount": action_profile["untypedActionCount"],
            "authoredEventHash": authored_event_hash,
            "authoredEventHashHex": f"0x{authored_event_hash:08x}",
            "scannedBankPackageCount": bank_package_count,
            "scannedBankPackageFingerprint": bank_package_fingerprint,
            "possibleMediaCount": len(event_candidates),
            "uniqueDecodedContentCount": len(unique_content_keys),
            "contentEquivalentLeafCount": sum(max(0, count - 1) for count in content_counts.values()),
            "candidateCount": len(event_candidates),
            "playRootCount": len(play_root_ids) or max(
                (int(row.get("rootPlayActionCount") or 0) for row in evidence_rows),
                default=0,
            ),
            "playRootActionIds": play_root_ids,
            "runtimeSelection": runtime_selection,
            "mediaRelationTypes": media_relation_types,
            "selectionContainerTypes": selection_types,
            "traversalStatus": traversal_status,
            "unresolvedNodeCount": sum(len(row.get("unresolvedNodes") or []) for row in evidence_rows),
            "contextCount": len(event_contexts),
            "playbackLocationStatus": playback_location_status,
            "purposeKnowledgeStatus": purpose_knowledge_status,
            "purposeInvestigationPriority": purpose_investigation_priority,
            "contextStoredCount": len(event_contexts),
            "contextsTruncated": False,
            "playableCharacterAnimationOwnerCount": len(character_animation_owner_ids),
            "enemyAnimationOwnerCount": len(enemy_animation_owner_ids),
            "animationContextScope": animation_context_scope,
            "animationFunctions": animation_functions,
            "customFootstepOccurrenceCount": sum(
                int(variant.get("occurrenceCount") or 0)
                for variant in custom_footstep_variants
            ),
            "customFootstepParameterVariants": custom_footstep_variants,
            "contexts": event_contexts,
            "evidence": evidence_rows,
            "media": event_candidates,
        })

    banks = []
    for bank in bank_rows.values():
        named_event_count = sum(
            not event_id.startswith("hashed-event:0x")
            for event_id in bank["eventIds"]
        )
        banks.append({
            "bank": bank["bank"],
            "bankId": bank["bankId"],
            "eventCount": len(bank["eventIds"]),
            "namedEventCount": named_event_count,
            "mediaCount": len(bank["mediaIds"]),
            "selectionEventCount": len(bank["selectionEventIds"]),
            "visitedObjectTypeOccurrences": dict(sorted(bank["visitedObjectTypeOccurrences"].items())),
        })
    banks.sort(key=lambda row: (str(row.get("bank") or ""), int(row.get("bankId") or 0)))
    return rows, media_to_events, banks
