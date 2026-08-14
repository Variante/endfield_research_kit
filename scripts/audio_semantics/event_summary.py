"""Compact list-row projection for detailed Audio events."""

from __future__ import annotations

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
        "animationVoiceTrigger",
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
        "binaryManagedLiteralCallsite",
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


def event_summary_row(row: dict[str, Any], detail_shard: str) -> dict[str, Any]:
    contexts = row.get("contexts") or []
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
        "id", "name", "hash", "category", "categoryEvidence", "foundInWwise",
        "audioLibraryResolutionStatus", "eventIdentityStatus", "eventNameEvidence",
        "eventNameSourceKind", "identityOnlyPlaybackPlacementStatus",
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
        "playableCharacterAnimationOwnerCount", "enemyAnimationOwnerCount",
        "animationContextScope", "animationFunctions", "customFootstepOccurrenceCount",
        "customFootstepParameterVariants",
        "timelineContextCount", "timelineAssetCount", "playableDirectorCount",
        "levelScriptPlayLevelSequenceActionCount", "timelineExactContextCount",
        "timelineInferredContextCount", "timelineOwnershipGapCount",
    )
    summary = {key: row[key] for key in keys if row.get(key) not in (None, "", [])}
    summary.update({
        "contextGroups": sorted({semantic_context_group(context.get("kind")) for context in contexts if isinstance(context, dict)} - {""}),
        "contextKinds": sorted({
            str(context.get("kind") or "")
            for context in contexts
            if isinstance(context, dict) and context.get("kind")
        }),
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
