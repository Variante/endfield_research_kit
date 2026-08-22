"""Compact list-row projection for detailed Audio events."""

from __future__ import annotations

from collections import Counter
from typing import Any

def semantic_context_group(kind: Any) -> str:
    value = str(kind or "")
    if value in {
        "characterSkill", "enemySkill", "buffPlaySoundAction",
        "projectileSoundField", "gameplayConfigAudioReference",
        "abilityVoiceTriggerAction", "nativeVoiceTriggerCallsite",
    }:
        return "gameplay"
    if value == "cutsceneTimeline":
        return "cutscene"
    if value in {
        "characterAnimation", "enemyAnimation", "animationCallbackOwnerUnresolved",
        "npcAnimation", "animationCallbackNpcOwner", "animationVoiceTrigger",
    }:
        return "animation"
    if value in {"levelSequenceAudio", "timelineAudioCueBehaviorEvent"}:
        return "timeline"
    if value in {"levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent"}:
        return "scripted"
    if value in {
        "table", "tableEventHash", "dialogLifecycle", "interactiveAudioTrigger", "interactiveComponentTrigger",
        "interactiveComponentPropertyAudio", "interactivePropertyMapAudio",
        "interactiveTemplateConfigAudio", "interactiveTemplateActionAudio",
        "interactiveEmbeddedActionAudio",
        "binaryManagedLiteralCallsite", "nativeCustomStateCallsite",
        "audioGlobalConfigEvent", "audioGlobalConfigEventHash",
        "audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent",
        "spawnerPreWarnAudio", "patrolSubActionPlayAudio", "charInteractAudioEvent", "physicsAudioComponentEvent",
        "audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant",
        "responsiveDialogToneVariant", "nativeVoiceTriggerCallsite",
        "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent",
        "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent",
        "responsiveVoiceEventTemplate", "voiceTableWwiseEvent",
        "uiAnimationOpenEvent", "activityPushPopupBgmEvent",
        "activityCenterBgmEvent", "uiVideoAudioEvent",
        "domainRegionSwitchEvent", "domainUpgradeAnimationEvent",
        "typedUiTableWwiseEvent", "snsVoiceMessageEvent",
        "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent",
        "remoteCommonAudio", "monoBehaviourAudioIdField",
    }:
        return "authoredConfig"
    if value == "binaryManagedLiteral":
        return "managedRuntime"
    if value == "luaPostEvent":
        return "luaRuntime"
    return ""


def _has_exact_npc_animation_owner(row: dict[str, Any]) -> bool:
    owner_ids = {str(value).strip() for value in row.get("animationCallbackNpcOwnerIds") or () if str(value).strip()}
    if len(owner_ids) != 1:
        return False
    resolution_statuses = [
        str(value).strip()
        for value in row.get("animationCallbackResolutionStatuses") or ()
        if str(value).strip()
    ]
    if resolution_statuses:
        return all(value.startswith("exactNpc") for value in resolution_statuses)
    return str(row.get("animationCallbackOwnershipStatus") or "").strip() in {
        "exactNpcTableToken",
        "exactNpcInfoAndTemplateGroup",
        "exactNpcOwnerAgreement",
    }


def event_summary_row(row: dict[str, Any], detail_shard: str) -> dict[str, Any]:
    contexts = row.get("contexts") or []
    exact_npc_animation_owner = _has_exact_npc_animation_owner(row)
    raw_context_kinds = {
        str(context.get("kind") or "")
        for context in contexts
        if isinstance(context, dict) and context.get("kind")
    }
    display_context_kinds = set(raw_context_kinds)
    if exact_npc_animation_owner:
        display_context_kinds.discard("animationCallbackOwnerUnresolved")
        display_context_kinds.update({"npcAnimation", "animationCallbackNpcOwner"})
    timeline_contexts = [
        context for context in contexts
        if isinstance(context, dict) and context.get("kind") == "levelSequenceAudio"
    ]
    timeline_asset_ids = {
        (
            str(context.get("timelineAssetSerializedFile") or ""),
            str(context.get("timelineAssetPathId") or ""),
        )
        for context in timeline_contexts
        if context.get("timelineAssetSerializedFile") or context.get("timelineAssetPathId")
    }
    director_count = sum(
        int(context.get("playableDirectorCount") or 0)
        for context in timeline_contexts
    )
    exact_timeline_count = sum(
        context.get("confidence") == "exact" for context in timeline_contexts
    )
    inferred_timeline_count = sum(
        context.get("confidence") == "inferred" for context in timeline_contexts
    )
    timeline_gap_count = sum(
        context.get("confidence") == "gap" for context in timeline_contexts
    )
    levelsequence_action_count = sum(
        int(context.get("levelScriptActionCount") or 0)
        for context in timeline_contexts
    )
    mono_behaviour_contexts = [
        context for context in contexts
        if isinstance(context, dict) and context.get("kind") == "monoBehaviourAudioIdField"
    ]
    mono_field_role_counts = Counter(
        str(context.get("authoredFieldRole") or "componentSerializedAudioField")
        for context in mono_behaviour_contexts
    )
    mono_component_layout_counts = Counter(
        str(context.get("componentLayout") or "unknown")
        for context in mono_behaviour_contexts
    )
    context_search: set[str] = set()
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for key in (
            "kind", "ownerId", "groupId", "storyKey", "table", "path",
            "semanticRole", "confidence", "skillId", "actionKind", "clip",
            "animationOwnershipScope", "possibleMediaScope", "triggerBindingStatus",
            "modelId", "subTemplateId", "triggerStateId", "triggerStateName",
            "triggerCustomState", "ownerKind", "stateDirection", "audioStateMask",
            "componentIndex", "sourceOffset", "sourceFingerprint",
            "projectileId", "projectileKey", "soundField", "triggerPhase",
            "runtimeActivationStatus", "sourceRoot", "sourcePathId", "sourceJsonPath",
            "signedValue", "eventHex", "sourceFile", "sourceVfsPath", "semanticPath",
            "authoredFieldRole", "authoredFieldNameRaw", "serializedFieldPath",
            "serializedFieldPathRaw", "serializedFieldPathStatus", "serializedFieldName",
            "componentLayout", "componentType", "componentName",
            "sizzleSoundTriggerDistance", "ringProjectileSoundSmoothFactor",
            "cueName", "cueSignedId", "cueId", "cueHex", "cueHashEvidence",
            "definitionStatus", "handlerScope", "levelId",
            "handlerIndex", "expressionSide", "expressionPath", "exprType",
            "controllerId", "modelAnimatorIndex", "modelAnimatorName",
            "layerIndex", "layerFsmIndex", "layerName", "stateIndex", "stateName",
            "stateType", "behaviorIndex", "behaviorTag", "behaviorTagHex",
            "behaviorType", "behaviorKind", "behaviorTime", "timeFlowSwitch",
            "normalAudioId", "audioNodeName", "eAudioTriggerState",
            "templateAssociationStatus",
            "globalMusicCueField",
            "authoredEventId", "spawnerConfigId", "enemyLibraryIndex", "enemyId",
            "bornTemplateId", "enemyLevel", "spawnerEnemyKey", "preWarnTime",
            "preWarnEffectKey", "schemaMappingId", "schemaStatus",
            "remoteCommonId", "singleId", "middleId", "index", "autoPlay",
            "autoPlayTime", "voiceId", "voiceLinkStatus", "startAudioEvent",
            "endAudioEvent",
            "patrolId", "patrolIndex", "pointIndex", "patrolSubActionType",
            "subActionUnionTag", "subActionUnionTagHex", "nativeConsumer",
            "charInteractPerformId", "actionPhase", "actionIndex", "logicId",
            "delay", "duration", "devOnly", "useEvent", "attachedActorType",
            "charIndex", "endStop", "is2D", "runtimeOwnerStatus",
            "attachedActorResolutionStatus", "unionMappingId", "endOffset",
            "action", "levelScriptId", "sourcePath", "sourceSha256",
            "recordIndex", "recordStart", "recordUid", "recordLocalId",
            "actionMapRole", "unionTag", "serializedMemberCount",
            "nativeMappingId", "payloadShape", "eventName", "triggerRole",
            "customStateName", "switchMethod", "switchMethodVa", "callsiteVa",
            "staticArgumentVa", "metadataUsageWord", "metadataStringLiteralIndex",
            "sourceField", "definitionOwnerId", "templatePath", "componentTag",
            "componentTagHex", "componentEndOffset", "propertyCount",
            "componentOccurrenceIndex",
            "authoredProperty", "runtimeField", "propertySourceOffset",
            "propertyValueSourceOffset", "valueType", "valueTypeName",
            "runtimeMappingId", "interactiveTableSha256",
            "customFootstepOccurrenceCount",
            "levelSequenceId", "timelineAssetName", "timelineAssetNameBase",
            "timelineAssetSerializedFile", "timelineAssetPathId", "timelineTrackName",
            "timelineTrackPathId", "timelineClipIndex", "timelineClipDisplayName",
            "timelineClipStartSec", "timelineClipDurationSec", "timelineClipEndSec",
            "timelineClipTimingEvidence", "timelineTrackRawJsonPath", "audioPlayableType",
            "audioPlayableRuntimeContractId", "audioPlayablePathId",
            "audioPlayableKeyStatus", "authoredEventName", "authoredEventNameEvidence",
            "audioPlayableIsCue",
            "audioPlayableStopEventAtClipEnd", "audioPlayableFadeOutMs",
            "audioPlayableEnableSeek", "audioPlayableUseBindingObject", "audioPlayableIs2D",
            "audioPlayableStopOnDisable",
            "audioPlayableControlEvidence", "audioPlayableRawJsonPath",
            "playableDirectorName", "playableDirectorPathId",
            "ownershipEvidenceLevel", "triggerEvidenceLevel", "timelineOwnershipStatus",
            "levelScriptActionCount", "playableDirectorCount", "evidenceBoundary",
            "lifecyclePhase", "arrayIndex", "runtimeMethod", "runtimeMethodToken",
            "runtimeDispatchStatus", "mediaSelectionStatus", "ownerStatus",
        ):
            value = context.get(key)
            if value not in (None, "", []):
                context_search.add(str(value))
        for key in (
            "skillIds", "actionKinds", "animationClips", "animationFunctions",
            "animationClipContexts", "authoredEventIds", "triggerRequestEvidence",
            "triggerRuntimeActivationStatuses", "triggerRelationTypes",
            "triggerOwnershipMethods", "triggerEvidenceKinds", "triggerBuffIds",
            "triggerSourcePaths",
            "sourcePaths",
            "sourceRoots", "sourceFingerprints", "consumerIds", "consumerAliasIds",
            "interactiveTableSourcePaths",
            "interactiveTemplateIds", "interactiveTemplatePaths", "interactiveConsumerIds",
            "authoredSkillIds",
            "bornBuffIds", "preWarnEffectFixedRotation",
            "actorList",
            "playableDirectorNames", "playableDirectorPathIds",
            "levelScriptIds", "levelScriptSourcePaths",
            "levelSequenceFieldOffsets",
        ):
            context_search.update(str(value) for value in context.get(key) or [] if str(value))
        for variant in context.get("customFootstepParameterVariants") or []:
            if not isinstance(variant, dict):
                continue
            for value in variant.values():
                if isinstance(value, (str, int, float, bool)):
                    context_search.add(str(value))
        for action in context.get("triggerPlaySoundActions") or []:
            if not isinstance(action, dict):
                continue
            for value in action.values():
                if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                    context_search.add(str(value))
                elif isinstance(value, list):
                    context_search.update(str(item) for item in value if str(item))
        for field_name, field in (context.get("fields") or {}).items():
            context_search.add(str(field_name))
            if not isinstance(field, dict):
                continue
            for value in field.values():
                if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                    context_search.add(str(value))
    if exact_npc_animation_owner:
        context_search.discard("animationCallbackOwnerUnresolved")
        context_search.update({"npcAnimation", "animationCallbackNpcOwner"})
    context_search.update(
        str(value)
        for key in ("sceneGlobalSceneIds", "sceneGlobalSemanticRoles")
        for value in row.get(key) or ()
        if value not in (None, "")
    )
    if row.get("sceneGlobalContextStatus"):
        context_search.add(str(row["sceneGlobalContextStatus"]))
    media = row.get("media") or []
    scopes = sorted({str(value.get("audioScope") or value.get("storageRoot") or "") for value in media if value.get("audioScope") or value.get("storageRoot")})
    banks = sorted({str(value.get("bankPackage") or "") for evidence in media for value in evidence.get("wwiseMediaEvidence") or [] if value.get("bankPackage")})
    source_kinds: set[str] = set()
    source_plugin_ids: set[str] = set()
    non_media_source_count = 0
    for evidence in row.get("evidence") or []:
        if not isinstance(evidence, dict):
            continue
        source_summary = evidence.get("sourceObjectSummary") or {}
        source_kinds.update(str(value) for value in (source_summary.get("sourceKindCounts") or {}))
        source_plugin_ids.update(str(value) for value in (source_summary.get("pluginCounts") or {}))
        for source in evidence.get("nonMediaSourceEvidence") or []:
            if not isinstance(source, dict):
                continue
            non_media_source_count += 1
            for key in (
                "pluginIdHex", "pluginName", "pluginTypeLabel", "streamTypeLabel",
                "sourceKind", "mediaLocationStatus",
            ):
                if source.get(key) not in (None, ""):
                    context_search.add(str(source[key]))
    keys = (
        "id", "name", "hash", "category", "categoryEvidence", "categoryNameEvidence", "foundInWwise",
        "audioLibraryResolutionStatus", "eventIdentityStatus", "eventNameEvidence",
        "eventNameSourceKind", "identityOnlyPlaybackPlacementStatus",
        "eventNameMetadataField", "eventNameMetadataDeclaringType",
        "eventNameMetadataFieldToken",
        "identityNumericSkillIds", "identityTableSources", "identitySkillDataSources", "playbackRole",
        "wwiseActionOperationTypes", "wwiseActionOperationTypesHex",
        "wwiseActionOperations", "wwiseActionOperationRows", "wwiseUntypedActionCount",
        "authoredEventHash", "authoredEventHashHex",
        "eventNameCollectionSources",
        "scannedBankPackageCount", "scannedBankPackageFingerprint",
        "possibleMediaCount", "candidateCount", "uniqueDecodedContentCount",
        "contentEquivalentLeafCount", "playRootCount", "playRootActionIds",
        "runtimeSelection", "mediaRelationTypes", "selectionContainerTypes",
        "traversalStatus", "unresolvedNodeCount", "contextCount",
        "playbackLocationStatus", "purposeKnowledgeStatus", "purposeInvestigationPriority",
        "audioLibraryPlaybackTargetStatus", "audioLibraryEquivalentEventIds",
        "audioLibraryEquivalentEventCount", "audioLibraryEquivalentCategories",
        "audioLibrarySharedPlayTargetSets", "audioLibraryPurposeHintStatus",
        "audioLibraryMediaLeafStatus", "audioLibraryMediaEquivalentEventIds",
        "audioLibraryMediaEquivalentEventCount", "audioLibraryMediaEquivalentCategories",
        "audioLibrarySharedMediaIds", "audioLibrarySharedMediaPackages",
        "audioLibraryMediaPurposeHintStatus",
        "contextStoredCount", "contextsTruncated",
        "sceneGlobalSceneIds", "sceneGlobalSemanticRoles", "sceneGlobalContextStatus",
        "playableCharacterAnimationOwnerCount", "enemyAnimationOwnerCount",
        "animationContextScope", "animationFunctions", "customFootstepOccurrenceCount",
        "animationActionNameMatchStatus", "animationActionMatchingClips",
        "animationActionOwnerIds", "animationActionFunctions",
        "animationActionOwnershipDomains", "animationActionNameMatchEvidence",
        "characterAudioIdentityStatus", "characterAudioOwnerIds",
        "characterAudioOwnerTokens", "characterAudioNameMatchEvidence",
        "characterAudioContextOwnerIds", "characterAudioContextRelationshipStatus",
        "animationCallbackLinkStatus", "animationCallbackClips",
        "animationCallbackOwnerIds", "animationCallbackFunctions",
        "animationCallbackOwnerKinds", "animationCallbackNpcOwnerIds",
        "animationCallbackNpcOwnerTemplates", "animationCallbackNpcActorTokens",
        "animationCallbackNpcOccurrenceOwnerIds",
        "animationCallbackNpcOccurrenceOwnerTemplates",
        "animationCallbackNpcOccurrenceActorTokens",
        "animationCallbackContextKinds", "animationCallbackActionKinds",
        "animationCallbackReachabilityStatuses",
        "animationCallbackAnimatorControllerNames",
        "animationCallbackOwnershipStatus", "animationCallbackTokenResolutionStatus",
        "animationCallbackResolutionStatuses", "animationCallbackResolvedEntityIds",
        "animationCallbackCandidateEntityIds",
        "animationCallbackOccurrenceCount", "animationCallbackLinkEvidence",
        "animationCallbackLinkTruncated",
        "customFootstepParameterVariants",
        "timelineContextCount", "timelineAssetCount", "playableDirectorCount",
        "levelScriptPlayLevelSequenceActionCount", "timelineExactContextCount",
        "timelineInferredContextCount", "timelineOwnershipGapCount",
        "monoBehaviourAudioIdFieldCount", "monoBehaviourAudioIdFieldRoleCounts",
        "monoBehaviourAudioIdFieldComponentLayoutCounts",
    )
    summary = {key: row[key] for key in keys if row.get(key) not in (None, "", [])}
    summary.update({
        "contextGroups": sorted({semantic_context_group(kind) for kind in display_context_kinds} - {""}),
        "contextKinds": sorted(display_context_kinds),
        "triggerBindingStatuses": sorted({
            str(context.get("triggerBindingStatus") or "")
            for context in contexts
            if isinstance(context, dict) and context.get("triggerBindingStatus")
        }),
        "contextSearch": sorted(context_search),
        "scope": scopes[0] if len(scopes) == 1 else "mixed" if scopes else "unknown",
        "source": "wwiseHirc" if row.get("foundInWwise") else "authoredContext",
        "bankPackages": banks,
        "detailShard": detail_shard,
    })
    if timeline_contexts:
        summary.update({
            "timelineContextCount": len(timeline_contexts),
            "timelineAssetCount": len(timeline_asset_ids),
            "playableDirectorCount": director_count,
            "levelScriptPlayLevelSequenceActionCount": levelsequence_action_count,
            "timelineExactContextCount": exact_timeline_count,
            "timelineInferredContextCount": inferred_timeline_count,
            "timelineOwnershipGapCount": timeline_gap_count,
        })
    if mono_behaviour_contexts:
        summary.update({
            "monoBehaviourAudioIdFieldCount": len(mono_behaviour_contexts),
            "monoBehaviourAudioIdFieldRoleCounts": dict(sorted(mono_field_role_counts.items())),
            "monoBehaviourAudioIdFieldComponentLayoutCounts": dict(sorted(mono_component_layout_counts.items())),
        })
    if source_kinds:
        summary["sourceKinds"] = sorted(source_kinds)
    if source_plugin_ids:
        summary["sourcePluginIds"] = sorted(source_plugin_ids)
    if non_media_source_count:
        summary["nonMediaSourceCount"] = non_media_source_count
    canonical_play_sound_contexts = [
        context for context in contexts
        if isinstance(context, dict) and context.get("kind") == "buffPlaySoundAction"
    ]
    trigger_play_sound_action_count = sum(
        int(context.get("triggerPlaySoundActionCount") or 0)
        for context in (canonical_play_sound_contexts or contexts)
        if isinstance(context, dict)
    )
    if trigger_play_sound_action_count:
        summary["triggerPlaySoundActionCount"] = trigger_play_sound_action_count
    return summary
