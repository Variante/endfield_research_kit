"""Current pooled LevelSequence ID candidates; compiled triggers remain unproved."""
from __future__ import annotations
import hashlib
from collections import Counter,defaultdict
from pathlib import Path,PurePosixPath
from typing import Any,Iterable
from scripts.source_paths import ExportLayout
from scripts.game_data.levelscript_union_tags import short_name
from scripts.webui.audio.semantics.context_utils import append_context as _append_context,normalize_posix
from scripts.webui.audio.semantics.levelscript_source import CurrentAudioSource,require,COMMON

ACTION_NAMES={'PlayLevelSequenceAction':'PlayLevelSequence',
              'PlayLevelSequenceAndControlSceneObjectsAction':'PlayLevelSequenceAndControlSceneObjects'}


def _levelsequence_fields_from_decoded_detail(detail):
    """Pure typed projection only; historical tagged-string scans are refused."""
    if not isinstance(detail,dict) or 'typedFields' not in detail:return []
    value=detail.get('levelSequenceId')
    return [dict(value=value,offset=detail.get('payloadStart'))] if isinstance(value,str) and value else []


def project_source_rows(decoded,source):
    rows=[];unresolved=[]
    for row in decoded.get('rows',[]):
        record=row['record'];node=record['typedNode'];name=short_name(node['wrapperName'])
        require(name in ACTION_NAMES,'typed-LevelSequence-action',source,actual=name)
        kind=node['fieldTypes'].get('levelSeqId');param=node['fields'].get('levelSeqId')
        require(kind=='Param<string>' and (param is None or isinstance(param,dict)),
                'typed-LevelSequence-id',source,expected='Param<string>',actual=kind)
        literal=param.get('value') if isinstance(param,dict) and type(param.get('paramSource')) is int and param['paramSource']==0 else None
        base=dict(record=record,action=ACTION_NAMES[name],levelSequenceFieldOffset=node['fieldRanges']['levelSeqId'][0],
                  parameter=param,triggerConsumerProved=False,eventRequestsProved=False)
        if isinstance(literal,str) and literal:rows.append(dict(base,levelSequenceId=literal))
        else:unresolved.append(dict(base,reason='null-dynamic-or-empty-stored-LevelSequence-id'))
    return dict(targetCount=decoded['targetCount'],rows=rows,unresolvedBindings=unresolved)


def project_sequence_owner(data,frame,source):
    require(frame.get('schemaStatus')=='named_exact' and type(frame.get('bytesConsumed')) is int and frame['bytesConsumed']==len(data),
            'complete-named-eof-required',source)
    asset=frame.get('ranges',{}).get('actionMap',{})
    if asset.get('value','present') is None:return dict(targetCount=0,rows=[],unresolvedBindings=[])
    mapping=asset.get('dataMap',{});nodes=mapping.get('actionList',[])
    require(type(mapping.get('actionListCount')) is int and mapping['actionListCount']==len(nodes),
            'complete-typed-action-list-required',source)
    selected=[]
    for node in nodes:
        if short_name(node['wrapperName']) not in ACTION_NAMES:continue
        fields=node['fields'];spans=node['fieldRanges'];start,end=node['sourceOffset'],node['endOffset']
        require(tuple(fields)[:8]==COMMON and node['memberCount']==len(fields),
                'current-LevelSequence-common-fields',source)
        payload=spans[COMMON[-1]][1];span=spans.get('levelSeqId')
        require(type(start) is int and type(end) is int and isinstance(span,(list,tuple)) and len(span)==2
                and all(type(n) is int for n in span) and 0<=start<payload<=span[0]<span[1]<=end<=len(data),
                'current-LevelSequence-field-range',source,actual=span)
        selected.append(dict(record=dict(start=start,end=end,payloadStart=payload,localId=fields['ID'],uid=fields['uid'],
            unionTag=node['unionTag'],serializedMemberCount=node['memberCount'],family='ActionBase',typedNode=node)))
    return project_source_rows(dict(targetCount=len(selected),rows=selected),source)


class LevelSequenceActions:
    """Accumulate independent pure projections inside one caller-owned operation."""
    def __init__(self,export_root):
        self.root=Path(export_root).resolve();self.actions=defaultdict(list);self.unresolved=[];self.failures=[]
        self.files=self.targets=self.decoded=self.files_with_actions=0
    def refuse(self,path,error):
        self.files+=1
        self.failures.append(getattr(error,'diagnostic',dict(validator='audioLevelSequenceSource',check='owner-refused',source=str(path),detail=str(error)[:1000])))
    def project(self,path,data,frame):
        path=Path(path).resolve();relative=normalize_posix(path.relative_to(self.root))
        try:result=project_sequence_owner(data,frame,relative)
        except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:
            self.refuse(relative,error);return
        self.files+=1;self.targets+=result['targetCount'];self.files_with_actions+=bool(result['rows'])
        identity=dict(levelScriptId=path.relative_to(self.root/'game/Json/LevelScriptData').with_suffix('').as_posix(),sourceRoot='game',sourcePath=relative,sourceSha256=hashlib.sha256(data).hexdigest().upper())
        for row in result['rows']:
            record=row['record'];self.decoded+=1
            self.actions[row['levelSequenceId']].append(dict(identity,action=row['action'],levelSequenceId=row['levelSequenceId'],
                recordStart=record['start'],recordUid=record['uid'],recordLocalId=record['localId'],
                unionTag=record['unionTag'],serializedMemberCount=record['serializedMemberCount'],
                serializedField='_levelSeqId',levelSequenceFieldOffset=row['levelSequenceFieldOffset'],parameter=row['parameter'],
                evidence='current-native-owned-stored-LevelSequence-id-candidate',triggerConsumerProved=False,eventRequestsProved=False,
                runtimeActivationStatus='playLevelSequenceActionExecutionNotObserved'))
        self.unresolved.extend(dict(identity,recordStart=row['record']['start'],parameter=row['parameter'],reason=row['reason'])for row in result['unresolvedBindings'])
    def result(self,audit=None,*,error=None):
        if error is not None:
            return dict(actionsByLevelSequenceId={},unresolvedBindings=[],sourceAudit=dict(status='unavailable_fail_closed',audioActionAbsenceProved=False),
                sourceDiagnostics=[getattr(error,'diagnostic',dict(validator='audioLevelSequenceSource',check='source-operation-refused',detail=str(error)[:1400]))],
                stats=dict(status='unavailable_fail_closed',sourceFiles=self.files,playLevelSequenceActionRecords=0,playLevelSequenceTargetRecords=0,
                    uniquePlayLevelSequenceIds=0,decodeFailures=max(1,len(self.failures)),audioActionAbsenceProved=False,eventRequestsProved=False),
                evidenceBoundary='Current LevelSequence source operation refused; zero emitted rows prove neither absence nor Event requests.')
        return dict(actionsByLevelSequenceId=dict(self.actions),unresolvedBindings=self.unresolved,sourceAudit=audit,sourceDiagnostics=self.failures[:16],
            stats=dict(status='partial'if self.failures else'current-authenticated-known-action-profile',sourceFiles=self.files,
                sourceFilesWithPlayLevelSequenceActions=self.files_with_actions,playLevelSequenceActionRecords=self.decoded,
                playLevelSequenceTargetRecords=self.targets,uniquePlayLevelSequenceIds=len(self.actions),decodeFailures=len(self.failures),
                unresolvedLevelSequenceBindings=len(self.unresolved),audioActionAbsenceProved=False,eventRequestsProved=False),
            evidenceBoundary='Current native-owned typed LevelScript fields and named-owner EOF establish stored ID candidates. Effective Param selection, compiled Director activation and Wwise posting remain unproved.')


def collect_levelsequence_play_actions(export_root:Path,*,gameassembly=None,metadata=None,family_receipt_path=None):
    """Standalone collection opens its own fresh operation."""
    options=dict(gameassembly=gameassembly,metadata=metadata,action_names=set(ACTION_NAMES));projection=LevelSequenceActions(export_root)
    if family_receipt_path is not None:options['receipt_path']=family_receipt_path
    try:
        with CurrentAudioSource(export_root,**options) as source:
            root=ExportLayout(export_root).game/'Json/LevelScriptData'
            for path in sorted(root.rglob('*.json'),key=lambda p:p.as_posix().lower()):
                if not path.is_file():continue
                try:data=path.read_bytes();frame=source.frame(path,data)
                except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:
                    projection.refuse(path,error);continue
                projection.project(path,data,frame)
            audit=source.audit()
        return projection.result(audit)
    except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:return projection.result(error=error)


def build_levelsequence_audio_contexts(
    event_ids: Iterable[str],
    ownership: dict[str, Any],
    play_actions: dict[str, Any],
) -> dict[str, Any]:
    """Build bounded exact/inferred/gap context rows for target Events."""

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    occurrences_by_event = ownership.get("occurrencesByEvent") or {}
    actions_by_id = play_actions.get("actionsByLevelSequenceId") or {}
    stats = Counter()
    context_event_ids: set[str] = set()
    inferred_trigger_event_ids: set[str] = set()
    target_ids = sorted({str(value or "").strip().lower() for value in event_ids if str(value or "").strip()})
    for event_id in target_ids:
        occurrences = [row for row in occurrences_by_event.get(event_id) or [] if isinstance(row, dict)]
        if not occurrences:
            _append_context(contexts, seen, event_id, {
                "kind": "levelSequenceAudio",
                "semanticRole": "timelineAudioOwnershipGap",
                "confidence": "gap",
                "ownershipEvidenceLevel": "gap",
                "triggerEvidenceLevel": "gap",
                "timelineOwnershipStatus": "timelineCarrierMissingFromCurrentObjectIndex",
                "triggerBindingStatus": "timelineCarrierMissingFromCurrentObjectIndex",
                "triggerRole": "PlayLevelSequence",
                "runtimeActivationStatus": "timelineAudioCarrierNotFound",
                "triggerRuntimeActivationStatuses": [
                    "timelineCarrierMissingFromCurrentObjectIndex",
                    "playLevelSequenceTriggerUnresolved",
                    "audioEventRuntimePlaybackUnobserved",
                ],
                "triggerRequestEvidence": [
                    "canonicalEventWithPossibleWwiseMedia",
                    "currentObjectIndexCarrierSearch",
                ],
                "triggerEvidenceKinds": ["levelSequenceAudioOwnershipGap"],
                "evidenceBoundary": "No AudioEventPlayable/Track carrier was found in the current object index; no Timeline or Director owner is claimed.",
            })
            stats["eventsWithoutTimelineCarrier"] += 1
            context_event_ids.add(event_id)
            continue
        for occurrence in occurrences:
            sequence_id = str(occurrence.get("timelineAssetNameBase") or "")
            action_rows = [row for row in actions_by_id.get(sequence_id) or [] if isinstance(row, dict)]
            director_rows = [row for row in occurrence.get("playableDirectors") or [] if isinstance(row, dict)]
            has_director = bool(director_rows)
            has_candidate = bool(action_rows)
            confidence = "inferred"
            trigger_status = (
                "storedLevelSequenceIdCandidateJoin" if has_candidate
                else "timelineParentNotLevelSequence" if not sequence_id
                else "timelineDirectorPlaybackTriggerUnresolved"
            )
            ownership_status = (
                "exactTimelineDirectorOwner" if has_director
                else "exactTimelineOwnerDirectorUnresolved"
            )
            context = {
                "kind": "levelSequenceAudio",
                "semanticRole": "authoredTimelineAudioEvent",
                "confidence": confidence,
                "ownershipEvidenceLevel": "exactSerializedTimelineCarrier",
                "triggerEvidenceLevel": "structuralOnly" if has_candidate else "inferred",
                "eventRequestsProved": False,
                "levelSequenceConsumerStatus": "current-compiled-Param-to-Director-unproved",
                "timelineOwnershipStatus": ownership_status,
                "triggerBindingStatus": trigger_status,
                "triggerRole": "PlayLevelSequence" if sequence_id else "TimelineAssetPlayback",
                "runtimeActivationStatus": "playableDirectorRuntimeExecutionNotObserved",
                "triggerRuntimeActivationStatuses": [
                    "playLevelSequenceCompiledConsumerUnproved" if has_candidate else (
                        "playLevelSequenceTriggerUnresolved" if sequence_id
                        else "timelineParentTriggerUnresolved"
                    ),
                    "playableDirectorRuntimeExecutionNotObserved" if has_director else "playableDirectorLinkUnresolved",
                    "audioEventRuntimePlaybackUnobserved",
                ],
                "triggerRequestEvidence": [
                    (
                        "exactDialogAudioEventPlayableAudioIdScalar"
                        if occurrence.get("audioPlayableKeyStatus") == "exactDialogAudioEventPlayableAudioIdScalar"
                        else "exactAudioEventPlayableScalar"
                        if occurrence.get("audioPlayableKeyStatus") == "exactAudioEventPlayableScalar"
                        else "exactTimelineTrackDisplayName"
                    ),
                    (
                        "exactTimelineDisplayNameHashEqualsSerializedAudioId"
                        if occurrence.get("authoredEventNameEvidence")
                        else "authoredEventNameNotRecovered"
                    ),
                    "exactTimelineTrackPPtr",
                    "exactTimelineParentPPtr",
                    "exactPlayableDirectorPlayableAssetPPtr" if has_director else "playableDirectorPPtrUnresolved",
                    "storedLevelScriptLevelSequenceIdCandidate" if has_candidate else (
                        "levelScriptPlayLevelSequenceIdUnresolved" if sequence_id
                        else "notALevelSequenceParent"
                    ),
                ],
                "triggerEvidenceKinds": [
                    "AudioEventPlayable",
                    "TimelineTrack",
                    "PlayableDirector" if has_director else "PlayableDirectorUnresolved",
                    "LevelScriptStoredLevelSequenceCandidate" if has_candidate else (
                        "LevelScriptPlayLevelSequenceUnresolved" if sequence_id
                        else "NonLevelSequenceTimelineParent"
                    ),
                ],
                "levelSequenceId": sequence_id,
                "timelineParentNameStatus": occurrence.get("timelineParentNameStatus") or (
                    "exactLevelSequenceAudioSuffix" if sequence_id else "nonLevelSequenceTimelineParent"
                ),
                "levelScriptActionCount": len(action_rows),
                "levelScriptStoredCandidateCount": len(action_rows),
                "levelScriptIds": sorted({
                    str(row.get("levelScriptId") or "")
                    for row in action_rows
                    if str(row.get("levelScriptId") or "")
                }),
                "levelScriptSourcePaths": sorted({
                    str(row.get("sourcePath") or "")
                    for row in action_rows
                    if str(row.get("sourcePath") or "")
                }),
                "levelSequenceFieldOffsets": sorted({
                    str(row.get("levelSequenceFieldOffset") or "")
                    for row in action_rows
                    if str(row.get("levelSequenceFieldOffset") or "")
                }),
                "levelScriptEvidence": action_rows,
                "timelineAssetName": occurrence.get("timelineAssetName"),
                "timelineAssetNameBase": sequence_id,
                "timelineAssetSerializedFile": occurrence.get("timelineAssetSerializedFile"),
                "timelineAssetPathId": occurrence.get("timelineAssetPathId"),
                "timelineAssetSource": occurrence.get("timelineAssetSource"),
                "timelineAssetSourceOffset": occurrence.get("timelineAssetSourceOffset"),
                "timelineTrackName": occurrence.get("timelineTrackName"),
                "timelineClipIndex": occurrence.get("timelineClipIndex"),
                "timelineTrackSerializedFile": occurrence.get("timelineTrackSerializedFile"),
                "timelineTrackPathId": occurrence.get("timelineTrackPathId"),
                "timelineTrackSource": occurrence.get("timelineTrackSource"),
                "timelineTrackSourceOffset": occurrence.get("timelineTrackSourceOffset"),
                "audioPlayableType": occurrence.get("audioPlayableType"),
                "audioPlayableRuntimeContractId": occurrence.get(
                    "audioPlayableRuntimeContractId"
                ),
                "audioPlayableKeyStatus": occurrence.get("audioPlayableKeyStatus"),
                "authoredEventName": occurrence.get("authoredEventName"),
                "authoredEventNameEvidence": occurrence.get("authoredEventNameEvidence"),
                "audioPlayableSerializedFile": occurrence.get("audioPlayableSerializedFile"),
                "audioPlayablePathId": occurrence.get("audioPlayablePathId"),
                "timelineClipDisplayName": occurrence.get("timelineClipDisplayName"),
                "timelineClipStartSec": occurrence.get("timelineClipStartSec"),
                "timelineClipDurationSec": occurrence.get("timelineClipDurationSec"),
                "timelineClipEndSec": occurrence.get("timelineClipEndSec"),
                "timelineClipInSec": occurrence.get("timelineClipInSec"),
                "timelineClipTimeScale": occurrence.get("timelineClipTimeScale"),
                "timelineClipEaseInDurationSec": occurrence.get("timelineClipEaseInDurationSec"),
                "timelineClipEaseOutDurationSec": occurrence.get("timelineClipEaseOutDurationSec"),
                "timelineClipBlendInDurationSec": occurrence.get("timelineClipBlendInDurationSec"),
                "timelineClipBlendOutDurationSec": occurrence.get("timelineClipBlendOutDurationSec"),
                "timelineClipOptionIndex": occurrence.get("timelineClipOptionIndex"),
                "timelineClipTimingEvidence": occurrence.get("timelineClipTimingEvidence"),
                "timelineTrackRawJsonPath": occurrence.get("timelineTrackRawJsonPath"),
                "audioPlayableIsCue": occurrence.get("audioPlayableIsCue"),
                "audioPlayableStopEventAtClipEnd": occurrence.get("audioPlayableStopEventAtClipEnd"),
                "audioPlayableStopEventAtClipEndKey": occurrence.get("audioPlayableStopEventAtClipEndKey"),
                "audioPlayableFadeOutMs": occurrence.get("audioPlayableFadeOutMs"),
                "audioPlayableEnableSeek": occurrence.get("audioPlayableEnableSeek"),
                "audioPlayableUseBindingObject": occurrence.get("audioPlayableUseBindingObject"),
                "audioPlayableIs2D": occurrence.get("audioPlayableIs2D"),
                "audioPlayableStopOnDisable": occurrence.get("audioPlayableStopOnDisable"),
                "audioMusicActionType": occurrence.get("audioMusicActionType"),
                "audioMusicActionTypeLabel": occurrence.get("audioMusicActionTypeLabel"),
                "audioMusicTriggerOnSkip": occurrence.get("audioMusicTriggerOnSkip"),
                "audioMusicTriggerOnSkipLabel": occurrence.get("audioMusicTriggerOnSkipLabel"),
                "audioPlayableControlEvidence": occurrence.get("audioPlayableControlEvidence"),
                "audioPlayableRawJsonPath": occurrence.get("audioPlayableRawJsonPath"),
                "playableDirectorCount": len(director_rows),
                "playableDirectorNames": [
                    str(row.get("playableDirectorName") or "")
                    for row in director_rows
                    if str(row.get("playableDirectorName") or "")
                ],
                "playableDirectorPathIds": [
                    row.get("playableDirectorPathId")
                    for row in director_rows
                    if row.get("playableDirectorPathId") is not None
                ],
                "directorEvidence": director_rows,
                "timelineEvidence": [
                    occurrence.get("evidence"),
                    occurrence.get("audioPlayableKeyStatus"),
                    occurrence.get("timelineClipTimingEvidence"),
                    occurrence.get("audioPlayableControlEvidence"),
                ],
                "evidence": "exactSerializedTimelineDirectorChain" if has_director else "exactSerializedTimelineCarrier",
                "evidenceBoundary": (
                    "Serialized Timeline/Director ownership remains separate from stored LevelScript "
                    "ID candidates. Effective Param values, the compiled Director trigger and "
                    "Wwise posting remain unproved; runtime execution is unobserved."
                ),
            }
            _append_context(contexts, seen, event_id, context)
            stats["timelineContexts"] += 1
            context_event_ids.add(event_id)
            inferred_trigger_event_ids.add(event_id)
            if has_director:
                stats["contextsWithPlayableDirector"] += 1
            else:
                stats["contextsWithoutPlayableDirector"] += 1
        if len(occurrences) > 1:
            stats["eventsWithMultipleTimelineOccurrences"] += 1
    stats["targetEvents"] = len(target_ids)
    stats["eventsWithTimelineContext"] = len(context_event_ids)
    stats["eventsWithExactLevelSequenceAction"] = 0
    stats["eventsWithInferredTimelineTrigger"] = len(inferred_trigger_event_ids)
    stats["eventsWithAnyTimelineCarrier"] = sum(bool(occurrences_by_event.get(event_id)) for event_id in target_ids)
    stats["eventsWithAnyContext"] = sum(bool(contexts.get(event_id)) for event_id in target_ids)
    return {
        "eventContexts": dict(contexts),
        "stats": dict(stats),
        "evidenceBoundary": (
            "Exact serialized Timeline ownership is separated from stored LevelScript ID candidates. "
            "Rows without a carrier remain an explicit gap; inferred rows never claim runtime execution "
            "or selected Wwise media."
        ),
    }
