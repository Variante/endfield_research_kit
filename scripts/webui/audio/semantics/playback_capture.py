"""Stream a playback capture without promoting partial phases into audible Events.

Evidence and admission boundary:

The loaded authored bus ancestry remains a parameter/control graph. The mixer
still uses a supplied single bus, identity channel matrix, ordered worker
dispatch and finite endpoint interfaces. Special parameter bindings and
State/Switch selection are excluded. Those offline conditions do not establish
current object-specific parameters, game-created emitter/listener association,
actual bus/effect topology or real device acceptance. The phase captures below
partially address live selection. Existing saved source-entry profiles lack
component/listener selection, later frame/mixer reads and output completion;
replaying them cannot recover those phases. The concrete next capture and
representative actions live in
`runtime_capture_requirements.md#audio-event-owner-listener-and-output-selection`.
The prepared `audio-playback` preset now uses the reviewed
`wwise_playback_capture_native.json` declarations. It adds paired
component/listener returns and bounded owner, parameter, route and source/sink
buffer phases to the existing source-entry surface. Transparent consumers
preserve their incoming integer/vector arguments; paired consumers use only
reviewed pointer/integer prototypes, including the parameter lookup's fifth
stack argument. Original calls execute once and exception unwinds remain
separate from normal returns. Periodic pointer-bucket sampling and byte
prefixes are explicit partial coverage; same-call results do not establish a
complete cross-thread generation or an uncaptured device result. The preset
opens a window automatically, closes it through normal stop, and uses existing
loss accounting, stable drain and retained cleanup on nonquiescent callbacks.
Saved phase captures now supply completed default and held-component getter
calls, a nonempty listener selection, finite nonzero source PCM prefixes and
normal sink-submit returns. A completed sink call does not expose each internal
COM result or prove device acceptance. Audio queue loss and orphan phases kept
the first session incomplete. The corrected session has a clean drain, closed
native pairs and readable declared fields. Its periodic coverage remains
conditional rather than a whole playback witness.

Selector playback serials also match managed Event return IDs under the
reviewed queue transport in `wwise_source_queue_native.json`. The corrected
Action fields now match selector serial/allocation reads under completed
same-thread Action nesting. Selector playback-blob identity and source input
also match constructor inputs; the independently reviewed factory retains the
parameter blob and forwards it into the constructor. The borrowed argument
instructions and their register roles are authenticated by the playback
declaration, without duplicating the complete source-owner body catalog. This
narrows live Event/source ownership without observing the intervening queue
allocation generation. One Event can retain several selected source words; keep
those choices instead of replacing them with the last source. Matching
sound-sector package key low words are supplied-corpus candidates with checked
current headers, not proof of live package/language precedence or backing file
selection. The generated phase review and package comparison are owned by
Audio's `playback_capture` and `playback_package_candidates` domains.
"""
from __future__ import annotations

import argparse
import copy
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics.runtime_capture_import import (
    decode_payload, FLAG_HOOK_NAME_TRUNCATED, FLAG_KEY_OR_PATH_TRUNCATED,
)
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads
from scripts.webui.audio.semantics.playback_lineage import PlaybackLineage
from scripts.webui.audio.semantics.device_capture import DeviceCapture
from scripts.webui.audio.semantics.mixer_capture import MixerCapture
from scripts.webui.audio.semantics.mixer_frame_capture import MixerFrameCapture, endpoint_coverage_diagnostics, endpoint_selection_scope
from scripts.webui.audio.semantics.sink_handoff_capture import SinkHandoffCapture, coverage_diagnostics as handoff_coverage_diagnostics
from scripts.webui.audio.semantics.mixer_consumer_capture import MixerConsumerCapture
from scripts.webui.audio.semantics.master_stage_observer_profile import validate_addresses as validate_master_addresses
from scripts.webui.audio.semantics.bus_processing_capture import BusProcessingCapture, link_task_device
from scripts.webui.audio.semantics.bus_processing_observer_profile import validate_addresses as validate_bus_addresses
from scripts.webui.audio.semantics.mix_contributions_capture import MixContributionsCapture,KINDS as CONTRIBUTION_KINDS
from scripts.webui.audio.semantics.mix_contributions_observer_profile import validate_addresses as validate_contribution_addresses
from scripts.webui.audio.semantics.room_wet_capture import RoomWetCapture,KINDS as ROOM_WET_KINDS
from scripts.webui.audio.semantics.room_configuration_capture import RoomConfigurationCapture
from scripts.webui.audio.semantics.room_history_capture import RoomHistoryCapture,KINDS as ROOM_HISTORY_KINDS
from scripts.webui.audio.semantics.room_input_capture import RoomInputCapture,KINDS as ROOM_INPUT_KINDS
from scripts.webui.audio.semantics.room_blend_capture import RoomBlendCapture,KINDS as ROOM_KINDS
from scripts.webui.story_recovery.prepare_audio_playback import prepare


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest.hexdigest())


def json_input(path, inputs):
    raw = path.read_bytes()
    inputs.append(dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    return json.loads(raw)


def rows(path, inputs):
    digest = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        for number, line in enumerate(stream, 1):
            digest.update(line); size += len(line)
            if len(line) > 65536:
                raise ValueError(f'{path.name}:{number}: row exceeds 65536 bytes')
            yield number, json.loads(line)
    inputs.append(dict(path=str(path.resolve()), bytes=size, sha256=digest.hexdigest()))


def geometry(field):
    return (field['name'], field['kind'], field['argIndex'], field['offset'],
            tuple(field.get('pointerOffsets', [])),field.get('baseField'),field.get('indexField'),field.get('lengthField'),tuple(field.get('projectionOffsets',[])),field.get('maxTaps'),field.get('prefixWords'))


def review(session, expected, *, configuration_oracle=None):
    """Expected recipe must come from preparation against explicit selected inputs.

    Frozen session reads may differ from the corrected recipe. Only fields with
    the same name, width and address geometry contribute interpreted facts.
    Historical mislabeled fields are retained solely in bounded raw examples.
    """
    session = Path(session).resolve(); inputs = []
    identity = json_input(session/'session.json', inputs)
    manifest = json_input(session/'private/source-owner-build-manifest.json', inputs)
    summary = json_input(session/'audio/summary.json', inputs)
    activation = json_input(session/'private/audio-activation.json', inputs)
    runtime = fingerprint(session/'private/EndfieldCapture.dll'); inputs.append(runtime)
    if runtime['sha256'] != identity['runtimeSha256'].lower() or runtime['bytes'] != identity['runtimeBytes']:
        raise ValueError('staged runtime differs from the session identity')
    is_configuration=manifest['schema']=='endfieldCapture.audioRoomConfigurationBuild.v1'
    is_wet=is_configuration or manifest['schema']=='endfieldCapture.audioRoomWetBuild.v1'
    is_history=is_wet or manifest['schema']=='endfieldCapture.audioRoomHistoryBuild.v1'
    is_input=is_history or manifest['schema']=='endfieldCapture.audioRoomInputBuild.v1'
    is_room=is_input or manifest['schema']=='endfieldCapture.audioRoomBlendBuild.v1'
    is_contributions=is_room or manifest['schema']=='endfieldCapture.audioMixContributionsBuild.v1'
    is_bus=manifest['schema'] in ('endfieldCapture.audioBusProcessingBuild.v1','endfieldCapture.audioBusProcessingBuild.v2','endfieldCapture.audioBusProcessingBuild.v3','endfieldCapture.audioMixContributionsBuild.v1','endfieldCapture.audioRoomBlendBuild.v1','endfieldCapture.audioRoomInputBuild.v1','endfieldCapture.audioRoomHistoryBuild.v1','endfieldCapture.audioRoomWetBuild.v1','endfieldCapture.audioRoomConfigurationBuild.v1')
    sampled_bus=is_bus and manifest['schema']!='endfieldCapture.audioBusProcessingBuild.v1'
    is_biquad=is_contributions or manifest['schema']=='endfieldCapture.audioBusProcessingBuild.v3'
    is_master=is_bus or manifest['schema']=='endfieldCapture.audioMasterStageBuild.v1'
    is_consumer=is_master or manifest['schema']=='endfieldCapture.audioMixerConsumerBuild.v1'
    is_handoff=is_consumer or manifest['schema']=='endfieldCapture.audioSinkHandoffBuild.v1'
    # Historical all-root bus recordings retain their old activation policy;
    # interpreting their unchanged reads does not relabel them as sampled.
    compatible_schema=manifest['schema']==expected['schema'] or is_bus and not is_contributions and expected['schema'] in ('endfieldCapture.audioBusProcessingBuild.v2','endfieldCapture.audioBusProcessingBuild.v3')
    if manifest['schema'] not in ('endfieldCapture.audioPlaybackBuild.v1', 'endfieldCapture.audioDeviceBuild.v1', 'endfieldCapture.audioMixerBuild.v1', 'endfieldCapture.audioMixerFrameBuild.v1','endfieldCapture.audioSinkHandoffBuild.v1','endfieldCapture.audioMixerConsumerBuild.v1','endfieldCapture.audioMasterStageBuild.v1','endfieldCapture.audioBusProcessingBuild.v1','endfieldCapture.audioBusProcessingBuild.v2','endfieldCapture.audioBusProcessingBuild.v3','endfieldCapture.audioMixContributionsBuild.v1','endfieldCapture.audioRoomBlendBuild.v1','endfieldCapture.audioRoomInputBuild.v1','endfieldCapture.audioRoomHistoryBuild.v1','endfieldCapture.audioRoomWetBuild.v1','endfieldCapture.audioRoomConfigurationBuild.v1') or not compatible_schema or manifest['files'] != expected['files']:
        raise ValueError('saved playback recipe differs from selected native inputs')
    if manifest['schema']=='endfieldCapture.audioDeviceBuild.v1' and activation.get('schema')!='audioRuntimeTrace.activation.v10':
        raise ValueError('device activation schema differs from the selected observer')
    if manifest['schema']=='endfieldCapture.audioMixerBuild.v1' and activation.get('schema')!='audioRuntimeTrace.activation.v11':
        raise ValueError('mixer activation schema differs from the selected observer')
    if manifest['schema']=='endfieldCapture.audioMixerFrameBuild.v1' and activation.get('schema')!='audioRuntimeTrace.activation.v12':
        raise ValueError('mixer frame activation schema differs from the selected observer')
    if sampled_bus and (manifest.get('busProcessingTaskSelection')!='sampledRootsAllDescendants' or manifest.get('busProcessingTaskKeyField')!='taskIndex'):
        raise ValueError('sampled bus task selection declaration differs')
    if is_handoff and (activation.get('schema')!=('audioRuntimeTrace.activation.v23' if is_configuration else 'audioRuntimeTrace.activation.v22' if is_wet else 'audioRuntimeTrace.activation.v21' if is_history else 'audioRuntimeTrace.activation.v20' if is_input else 'audioRuntimeTrace.activation.v19' if is_room else 'audioRuntimeTrace.activation.v18' if is_contributions else 'audioRuntimeTrace.activation.v17' if is_biquad else 'audioRuntimeTrace.activation.v16' if sampled_bus else 'audioRuntimeTrace.activation.v15' if is_bus else 'audioRuntimeTrace.activation.v14' if is_consumer else 'audioRuntimeTrace.activation.v13') or manifest.get('nativeSelectionScope')!='explicitWindowIds' or manifest.get('automaticWindow') is not False):
        raise ValueError('sink handoff activation or explicit window selection differs')
    approved = {h['name']: h for h in expected['nativeHooks'] if is_biquad or not is_bus or h['sourceKind'] not in ('biquadProcessing','collectionEqExecute')}
    hooks = {h['name']: h for h in manifest['nativeHooks']}
    if len(hooks) != len(manifest['nativeHooks']) or set(hooks) != set(approved):
        raise ValueError('saved hook roster differs from the selected recipe')
    managed_hooks={h['name']:h for h in manifest['hooks']}
    if set(managed_hooks)!={h['name'] for h in expected['hooks']} or any(any(managed_hooks[h['name']].get(k)!=h.get(k) for k in ('rva','module','abiId')) for h in expected['hooks']):
        raise ValueError('saved managed sites or ABIs differ from selected recipe')
    for name, hook in hooks.items():
        if any(hook.get(k) != approved[name].get(k) for k in ('rva', 'module', 'abiId')):
            raise ValueError(f'{name}: saved site or ABI differs from selected recipe')
        if hook.get('hookBinding') != approved[name].get('hookBinding'):
            raise ValueError(f'{name}: saved hook binding differs from selected recipe')
        if hook.get('hookBinding') == 'observedRenderClientVtable' and any(hook.get(k) != approved[name].get(k) for k in ('rvaRole', 'memory', 'resultMemory', 'readProgram', 'resultProgram')):
            raise ValueError(f'{name}: saved device declarations differ from selected recipe')
        if (hook.get('sourceKind')=='unfilteredMatrixConsumer' or is_master and hook.get('sourceKind')=='masterBusOutput') and any(hook.get(k)!=approved[name].get(k) for k in ('memory','resultMemory','readProgram','resultProgram')):
            raise ValueError('saved matrix consumer reads differ from selected recipe')
        if is_bus and hook.get('sourceKind') in ('busOutputTask','busPostMixProcessing','busEffectConsume','sourceFrameGain','biquadProcessing','collectionEqExecute',*CONTRIBUTION_KINDS,*ROOM_KINDS,*ROOM_INPUT_KINDS,*ROOM_HISTORY_KINDS,*ROOM_WET_KINDS) and any(hook.get(k)!=approved[name].get(k) for k in ('memory','resultMemory','readProgram','resultProgram')):
            raise ValueError('saved bus processing reads differ from selected recipe')
    activated = {h['name']:h for h in activation['hooks']}
    if any(name not in activated or any(activated[name].get(k,'')!=hook.get(k,'') for k in ('rva','abiId','readProgram','resultProgram')) for name,hook in hooks.items()):
        raise ValueError('activated hooks differ from the frozen build manifest')
    windows = {}
    windows_path=session/'audio/windows.jsonl'
    if windows_path.is_file():
        for _,row in rows(windows_path, inputs):
            if row['action']=='stop': windows[row['requestId']] = (row['startNs'],row['endNs'])
    if not windows:
        native_path=session/'audio/source_owner.jsonl'
        if native_path.is_file():inputs.append(fingerprint(native_path))
        return dict(schema='endfield.audio-playback-capture-review.v8',status='noObservationWindow',
            session=str(session),inputs=inputs,summary=summary,rows=0,rawRowsDeclared=summary.get('sourceOwnerRows'),
            wholeEventToDeviceClaim=False,
            diagnostics=[dict(check='closedAudioObservationWindow',expected='at least one closed window',
                actual=dict(windowsFilePresent=windows_path.is_file(),windowsStarted=summary.get('windowsStarted'),windowsCompleted=summary.get('windowsCompleted'),
                    nativeBytes=native_path.stat().st_size if native_path.is_file() else None))],
            nativeLineage=None,deviceOutput=None,mixerOutput=None,mixerFrameOutput=None,sinkHandoffOutput=None,
            evidenceBoundary='No closed audio observation window was recorded. Native data, if present, is left uninterpreted. Provider readiness, zero losses and complete=true do not establish that recording started.')
    plans = {}; mapped_extent = None
    hook_indices={h['name']:i+2 for i,h in enumerate(manifest['nativeHooks'])}
    for name, hook in hooks.items():
        for phase in (1,2,4):
            fields=hook.get('resultMemory',[]) if phase==2 else hook['memory']
            allowed={geometry(f) for f in approved[name].get('resultMemory' if phase==2 else 'memory',[])}
            program=hook.get('resultProgram','') if phase==2 else hook['readProgram']
            normalized=copy.deepcopy(fields)
            for field in normalized:
                guard=field.get('requireArgument')
                if isinstance(guard,dict):
                    field['requireArgument']=hook['args'][guard['name']]['index']
            if program!=(compile_reads(normalized) if normalized else ''):
                raise ValueError(f'{name}: read program differs from frozen field declarations')
            compiled=[list(map(int,part.split(','))) for part in program.split(';') if part]
            if len(compiled)!=len(fields) or any(len(words)!=8 for words in compiled):
                raise ValueError(f'{name}: frozen read program shape differs')
            plans[(name,phase)]=(fields,[geometry(f) in allowed for f in fields],compiled)

    managed_pending = {}; managed = {}; managed_errors = 0; truncated_paths=[]
    for _, row in rows(session/'events.jsonl', inputs):
        if row.get('sessionId') != identity['numericSessionId']:
            raise ValueError('event row belongs to a different session')
        if row.get('provider') != 2 or row.get('type') != 10:
            continue
        event = decode_payload(bytes.fromhex(row['payloadHex']))
        if event['hookName'] not in {h['name'] for h in expected['hooks']}:
            continue
        key = (event['captureId'], row['threadId'], event['hookName'])
        if event['kind'] == 0:
            if key in managed_pending: managed_errors += 1
            managed_pending[key] = event
        elif event['kind'] == 1:
            call = managed_pending.pop(key, None)
            if not call or (event['flags']|call['flags'])&FLAG_HOOK_NAME_TRUNCATED:
                managed_errors += 1; continue
            path_complete=not ((event['flags']|call['flags'])&FLAG_KEY_OR_PATH_TRUNCATED)
            if not path_complete:
                truncated_paths.append(dict(captureId=event['captureId'],hook=event['hookName'],prefix=call['keyOrPath']))
            serial = event['returnValue']
            if serial:
                request=dict(eventId=call['pointerFact0'],objectId=call['pointerFact1'],captureId=event['captureId'],threadId=row['threadId'],hook=event['hookName'])
                if event['hookName'].endswith('_PostEventWithExternalSource'):
                    request.update(sourcePath=call['keyOrPath'],sourcePathComplete=path_complete,
                        externalCookie=event['pointerFact0'],rawCodecArgument=event['pointerFact1'])
                managed.setdefault(serial, []).append(request)
        else:
            managed_errors += 1

    pending = {}; examples = {}; counts = Counter(); fields_failed = Counter()
    lineage=PlaybackLineage(expected['playbackOwnerTransport'],expected.get('storedOwnerIdentity'),hooks) if expected.get('playbackOwnerTransport') else None
    device=DeviceCapture(hooks,summary) if is_handoff or manifest['schema'] in ('endfieldCapture.audioDeviceBuild.v1','endfieldCapture.audioMixerBuild.v1','endfieldCapture.audioMixerFrameBuild.v1') else None
    mixer=MixerCapture(expected['masterStageSelection'] if is_master else None) if is_handoff or manifest['schema'] in ('endfieldCapture.audioMixerBuild.v1','endfieldCapture.audioMixerFrameBuild.v1') else None
    interval_joins_enabled=summary.get('dropped')==0 and summary.get('complete') is True and summary.get('hooksQuiescent') is True and summary.get('sourceOwnerWriteComplete') is True and not endpoint_coverage_diagnostics(summary,manifest['nativeHooks'],expected.get('mixerFrameUnsampledHookKinds',[]),Counter())
    frame=MixerFrameCapture(expected['contextDescriptorOffset'],interval_joins_enabled=interval_joins_enabled) if is_handoff or manifest['schema']=='endfieldCapture.audioMixerFrameBuild.v1' else None
    handoff=None
    if is_handoff:
        sampling=summary.get('playbackSampling',{});skipped=sampling.get('skipped',[])
        skips={h['sourceKind']:skipped[i] for i,h in enumerate(manifest['nativeHooks']) if i<len(skipped)}
        issues=handoff_coverage_diagnostics(manifest['nativeHooks'],native_status='validated',complete=summary.get('complete'),dropped=summary.get('dropped'),skipped=skips)
        if sampling.get('nativeSelectionScope')!='explicitWindowIds' or sampling.get('allSinkWriteFrameEndEndpoints') is not True:
            issues.append('sinkHandoffExplicitEndpointModeMissing')
        handoff=SinkHandoffCapture(expected['sinkHandoffLayout'],coverage_issues=issues)
    consumer=MixerConsumerCapture(expected['mixerConsumerSelection'],expected['mixerConsumerInputBoundary']) if is_consumer else None
    bus=BusProcessingCapture(expected['busProcessingSelection'],expected['busProcessingReturnSites'],expected.get('busProcessingCollectionEffect'),expected.get('busProcessingEffectClasses',()),expected.get('busProcessingBiquad') if is_biquad else None) if is_bus else None
    contributions=MixContributionsCapture(expected['mixContributions'],expected['busProcessingReturnSites']) if is_contributions else None
    room=RoomBlendCapture(expected['roomBlend']) if is_room else None
    room_input=RoomInputCapture(expected['roomInput']) if is_input else None
    room_history=RoomHistoryCapture(expected['roomHistory']) if is_history else None
    room_wet=RoomWetCapture(expected['roomWet']) if is_wet else None
    room_configuration=RoomConfigurationCapture(expected['roomConfiguration']) if is_configuration else None
    pairs = Counter(); orphans = Counter(); branches = Counter(); pcm = Counter()
    serials = {}; excluded = set(); errors = []; previous = 0; row_count = 0

    def remember(name, value):
        if name not in examples: examples[name] = value

    for number, row in rows(session/'audio/source_owner.jsonl', inputs):
        row_count = number
        try:
            name, phase = row['hook'], row['phase']; hook = hooks[name]
            is_device=hook.get('hookBinding')=='observedRenderClientVtable'
            if row['schema'] != ('endfieldCapture.audioDeviceObservation.v1' if is_device else 'endfieldCapture.audioPlaybackObservation.v2' if hook['sourceKind']=='roomVerbBlend' else 'endfieldCapture.audioPlaybackObservation.v1') or phase not in ((1,2,3) if is_device else (1,2,3,4)):
                raise ValueError('schema or phase differs')
            if row['sequence'] <= previous or not row['captureId'] or len(row['args']) != 4:
                raise ValueError('invalid sequence, identity or arguments')
            previous = row['sequence']
            if row['hookIndex'] != hook_indices[name]:
                raise ValueError('hook index differs from frozen activation')
            if is_handoff and (row.get('observationWindowId')!=row['windowId'] or type(row.get('observationWindowOpen')) is not bool):
                raise ValueError('sink handoff native window ID or closure state differs')
            override=row.get('windowInvocationStartNs',0)
            if override and not is_device:
                if (not is_handoff and manifest['schema'] not in ('endfieldCapture.audioMixerBuild.v1','endfieldCapture.audioMixerFrameBuild.v1')) or hook['sourceKind'] not in ('sinkInput','outputConsumer'):
                    raise ValueError('undeclared parent window override')
                ancestor=row['parentCaptureId'];seen=set();root=None
                while ancestor and ancestor not in seen and len(seen)<64:
                    seen.add(ancestor);entry=pending.get((row['windowId'],ancestor))
                    if not entry or entry[0]['threadId']!=row['threadId']:break
                    if entry[0]['hook'].endswith('.masterBusOutput'):root=entry[0];break
                    ancestor=entry[0]['parentCaptureId']
                if not root or root['invocationStartNs']!=override:raise ValueError('mixer child lacks its active master output window')
            window=windows.get(row['windowId']); stamp=override or row['invocationStartNs'] or row['timestampNs']
            if not window or (not is_handoff and not window[0]<=stamp<=window[1]) or (is_handoff and stamp<window[0]):
                raise ValueError('invocation entry outside closed window')
            extent=(row['moduleBase'],row['moduleBytes'])
            if not extent[0] or extent[0]%4096 or not 0<extent[1]<2**32 or extent[0]+extent[1]>=0x800000000000:
                raise ValueError('invalid module extent')
            if mapped_extent is None: mapped_extent=extent
            elif mapped_extent!=extent: raise ValueError('module extent changed')
            fields,allowed,program=plans[(name,2 if phase==2 else 1)]
            facts = {}
            if phase != 3:
                if any(len(row[k]) != len(fields) for k in ('values','states','addresses')):
                    raise ValueError('field shape differs from frozen recipe')
                for i,(field, value, state, accept,words) in enumerate(zip(fields,row['values'],row['states'],allowed,program)):
                    if state not in (0,1,2): raise ValueError('unknown field read state')
                    if type(value) is not int or not 0<=value<2**64 or (state==0 and value):
                        raise ValueError('invalid scalar or guarded-out value')
                    if field['kind'] in ('u8','u16','u32','argumentU32','indexedU32','ringU32','ringPairU32') and value>=2**{'u8':8,'u16':16,'u32':32,'argumentU32':32,'indexedU32':32,'ringU32':32,'ringPairU32':32}[field['kind']]:
                        raise ValueError('scalar exceeds declared width')
                    if field['kind'] in ('argument','argumentU32'):
                        ref=field['argIndex']
                        argument=row['args'][ref] if ref<4 else row[{4:'returnValue',5:'moduleBase',6:'extraArgument',7:'sixthArgument',8:'seventhArgument',9:'eighthArgument',10:'ninthArgument',11:'tenthArgument'}[ref]]
                        if (state==1 and value != (argument & 0xffffffff if field['kind']=='argumentU32' else argument)) or row['addresses'][i] or state==2:
                            raise ValueError('argument field differs from observed call register')
                    mode,ref,wanted=words[5:]; enabled=True
                    if mode in (1,2):
                        if ref>=i: raise ValueError('forward field guard')
                        enabled=row['states'][ref]==1 and (row['values'][ref]!=0 if mode==1 else row['values'][ref]==wanted)
                    elif mode==3:
                        argument=row['args'][ref] if ref<4 else row[{4:'returnValue',5:'moduleBase',6:'extraArgument',7:'sixthArgument',8:'seventhArgument',9:'eighthArgument',10:'ninthArgument',11:'tenthArgument'}[ref]]
                        enabled=argument!=0
                    if enabled!=(state!=0): raise ValueError('field guard disagrees with receipt')
                    if state == 2: fields_failed[name+'.'+field['name']] += 1
                    if accept:
                        facts[field['name']] = value if state == 1 else None
                    else:
                        excluded.add(name+'.'+field['name'])
            span = bytes.fromhex(row['spanHex'])
            if len(span) != row['spanBytes'] or not 0 <= len(span) <= min(row['spanRequested'],5120 if is_wet and hook['sourceKind']=='roomEarlyReflectionKernel' else 256):
                raise ValueError('span size differs or exceeds bound')
            span_fields=[(i,w) for i,w in enumerate(program) if w[1] in (6,13)]
            if phase!=3 and span_fields:
                i,w=span_fields[0]
                if row['states'][i]==0 and (span or row['spanRequested'] or row['spanAddress']):
                    raise ValueError('inactive span contains copied bytes or storage metadata')
                if row['states'][i]==2 and span:
                    raise ValueError('failed span read contains copied bytes')
                if row['states'][i]==1:
                    valid_span=(row['spanRequested']==len(span)==row['values'][i] and len(span)<=32+2*(w[7]>>16)*32) if w[1]==13 else (row['spanRequested']==row['values'][w[6]]*(w[7]>>16) and len(span)==min(row['spanRequested'],w[7]&65535))
                    if not valid_span:raise ValueError('span requested/copied length differs from declaration')
            elif span or row['spanRequested']: raise ValueError('undeclared span')
            if frame and phase!=3:frame.validate_addresses(row,facts,fields)
            if consumer:consumer.validate_addresses(row,facts,fields)
            if is_master:validate_master_addresses(row,facts,fields,expected['masterStageLayout'],expected['sinkHandoffLayout'])
            if is_bus:validate_bus_addresses(row,facts,fields,expected['busProcessingLayout'],expected['sinkHandoffLayout'],expected.get('busProcessingBiquad'))
            if contributions and hook['sourceKind'] in CONTRIBUTION_KINDS:validate_contribution_addresses(row,facts,fields)
            if room and hook['sourceKind'] in ROOM_KINDS:room.validate_addresses(row,facts,fields)
            if room_input and hook['sourceKind'] in ROOM_INPUT_KINDS:room_input.validate_addresses(row,facts,fields,pending=pending,ancestor=contributions.ancestor,room=room)
            if room_history and hook['sourceKind'] in ROOM_HISTORY_KINDS:room_history.validate_addresses(row,facts,fields)
            if room_wet and hook['sourceKind'] in ROOM_WET_KINDS:room_wet.validate_addresses(row,facts,fields)
            if room_configuration and hook['sourceKind']=='roomVerbExecute':room_configuration.validate_addresses(row,facts,fields)
            if handoff:
                observed=dict(facts,readAddresses={f['name']:row['addresses'][i] for i,f in enumerate(fields) if phase!=3 and facts.get(f['name']) is not None})
                handoff.observe(hook['sourceKind'],row,observed)
            counts[(name,phase)] += 1
            if lineage: lineage.entry(row,facts,pending)
            if device: device.entry(row,facts,pending)
            if frame: frame.entry(row,facts)
            if bus:bus.entry(row)
            if contributions:contributions.entry(row,facts,frame,pending)
            if room:room.entry(row,facts,pending,contributions.ancestor)
            if room_wet:room_wet.entry(row,facts,pending,contributions.ancestor,room,room_input)
            if room_history:room_history.entry(row,facts,pending,contributions.ancestor,room,room_input)
            if room_input:room_input.entry(row,facts,pending,contributions.ancestor,room)
            key = (row['windowId'],row['captureId'])
            if phase == 1:
                if key in pending or len(pending) >= 100000:
                    raise ValueError('duplicate pair entry or pending-pair bound exceeded')
                pending[key] = (row,facts)
            elif phase in (2,3):
                entry = pending.pop(key,None)
                if not entry: orphans[name] += 1; continue
                before, input_facts = entry
                if any(before.get(k) != row.get(k) for k in ('hook','args','threadId','invocationStartNs','parentCaptureId','returnAddress')):
                    raise ValueError('paired invocation identity differs')
                if before.get('windowInvocationStartNs')!=row.get('windowInvocationStartNs'):
                    raise ValueError('paired invocation parent window differs')
                if hook['abiId'] in ('win64.void_integer5_result.v1','win64.pointer_integer6_result.v1') and before['extraArgument']!=row['extraArgument']:
                    raise ValueError('paired fifth stack argument differs')
                if hook['abiId']=='win64.pointer_integer6_result.v1' and before['sixthArgument']!=row['sixthArgument']:
                    raise ValueError('paired sixth stack argument differs')
                if hook['abiId']=='win64.void_integer8_result.v1' and any(before.get(k)!=row.get(k) for k in ('extraArgument','sixthArgument','seventhArgument','eighthArgument','mxcsr','roundingModeSampled','parentCaptureId','returnAddress')):
                    raise ValueError('paired matrix consumer arguments or entry rounding differ')
                if hook['abiId']=='win64.void_pointer_float2_u8_result.v1' and any(before.get(k)!=row.get(k) for k in ('mxcsr','roundingModeSampled','parentCaptureId','returnAddress')):
                    raise ValueError('paired floating gain arguments or entry rounding differ')
                if hook['sourceKind'] in CONTRIBUTION_KINDS and any(before.get(k)!=row.get(k) for k in ('extraArgument','mxcsr','roundingModeSampled')):
                    raise ValueError('paired accumulation stack argument or entry rounding differs')
                if room_wet and hook['sourceKind'] in ROOM_WET_KINDS and any(before.get(k)!=row.get(k) for k in ('extraArgument','mxcsr','roundingModeSampled')):
                    raise ValueError('room wet stack/rounding snapshot differs')
                if room_history and hook['sourceKind'] in ROOM_HISTORY_KINDS and any(before.get(k)!=row.get(k) for k in ('extraArgument','mxcsr','roundingModeSampled')):
                    raise ValueError('room history stack/rounding snapshot differs')
                if hook['sourceKind']=='roomInputFold' and any(before.get(k)!=row.get(k) for k in ('extraArgument','sixthArgument','mxcsr','roundingModeSampled')):
                    raise ValueError('paired room fold floating arguments or rounding differ')
                if hook['sourceKind']=='roomVerbBlend' and any(before.get(k)!=row.get(k) for k in ('extraArgument','sixthArgument','seventhArgument','eighthArgument','ninthArgument','tenthArgument','mxcsr','roundingModeSampled')):
                    raise ValueError('paired room blend stack arguments or entry rounding differ')
                if is_device and any(before[k] != row[k] for k in ('deviceSink','deviceTarget','linkedCaptureId','parentCaptureId','windowInvocationStartNs','returnAddress','extraArgument')):
                    raise ValueError('paired device invocation identity differs')
                pairs[(name,phase)] += 1
                if bus:bus.completed(before,row,input_facts,facts,pending,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if contributions:contributions.completed(before,row,input_facts,facts,pending,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if room_wet:room_wet.completed(before,row,input_facts,facts,pending,contributions.ancestor,room,room_input,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if room_configuration:room_configuration.completed(before,row,input_facts,facts,room,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if room_history:room_history.completed(before,row,input_facts,facts,pending,contributions.ancestor,room,room_input,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if room_input:room_input.completed(before,row,input_facts,facts,pending,contributions.ancestor,room,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if room:room.completed(before,row,input_facts,facts,pending,contributions.ancestor,closed=before.get('observationWindowOpen') is True and row.get('observationWindowOpen') is True and row['timestampNs']<=window[1])
                if lineage: lineage.completed(before,row,facts,pending)
                if device: device.completed(before,row,facts,pending)
                if mixer: mixer.completed(before,row,facts,pending,input_facts,inside_closed_window=row['timestampNs']<=window[1] and (not is_handoff or row['observationWindowOpen']))
                if frame: frame.completed(before,row,facts,input_facts,inside_closed_window=row['timestampNs']<=window[1] and (not is_handoff or row['observationWindowOpen']))
                if consumer:consumer.completed(before,row,facts,input_facts,pending,inside_closed_window=row['timestampNs']<=window[1] and row['observationWindowOpen'])
                if phase == 3: continue
                if name.endswith('objectComponentGetter'):
                    held = input_facts.get('heldComponent'); result = row['returnValue']
                    branch = 'nullToDefault' if held == 0 and result else 'heldToSame' if held and held == result else 'other'
                    branches[branch] += 1
                    remember('component-'+branch,dict(enter=before,result=row))
                elif name.endswith('componentListenerSelector'):
                    remember('listenerSelection',dict(enter=before,result=row))
                elif name.endswith('contextSourceSampleBuffer'):
                    floats = struct.unpack('<'+str(len(span)//4)+'f',span) if span and len(span)%4 == 0 else ()
                    kind = 'nonzeroFinitePrefix' if floats and all(math.isfinite(x) for x in floats) and any(floats) else 'zeroOrAbsentPrefix'
                    pcm[kind] += 1; remember('source-'+kind,dict(enter=before,result=row))
                elif name.endswith('sinkSubmit'):
                    remember('sinkNormalReturn',dict(enter=before,result=row))
            elif phase == 4 and name.endswith('anonymousSourceSelector'):
                serial = facts.get('playbackSerialWord')
                parent = pending.get((row['windowId'],row['parentCaptureId']))
                synchronous = bool(parent and parent[0]['hook'].endswith('normalActionExecute') and parent[0]['threadId']==row['threadId'])
                candidates = managed.get(serial,[])
                if serial not in serials:
                    if len(serials)>=100000: raise ValueError('selector serial bound exceeded')
                    serials[serial]=dict(serial=serial,managedCandidates=candidates,observations=0,synchronousActionObservations=0,sourceChoices=[])
                cohort=serials[serial];cohort['observations']+=1;cohort['synchronousActionObservations']+=synchronous
                choice=dict(sourceLookup=facts.get('originalSourceLookupWord'),sourceMatchWord=facts.get('originalSourceStoredWord4'),sourceArgument=facts.get('originalSourceArgumentWord24'))
                if choice not in cohort['sourceChoices']:
                    if len(cohort['sourceChoices'])>=4096: raise ValueError('per-serial source-choice bound exceeded')
                    cohort['sourceChoices'].append(choice)
                if len(candidates)==1:
                    remember('selectorSerialCandidate',dict(selector=row,managed=candidates[0],actionEntry=parent[0] if synchronous else None))
        except (KeyError,ValueError,TypeError,struct.error) as error:
            if len(errors)<20: errors.append(dict(row=number,check=str(error)))

    reasons = []
    if summary.get('dropped',0): reasons.append(dict(check='audioQueueLoss',actual=summary['dropped'],expected=0))
    if not summary.get('complete') or not summary.get('hooksQuiescent') or not summary.get('sourceOwnerWriteComplete'):
        reasons.append(dict(check='audioCompletion',actual={k:summary.get(k) for k in ('complete','hooksQuiescent','sourceOwnerWriteComplete')}))
    if row_count != summary.get('sourceOwnerRows'):
        reasons.append(dict(check='sourceRowCount',actual=row_count,expected=summary.get('sourceOwnerRows')))
    if pending or orphans: reasons.append(dict(check='phasePairs',unmatchedEntries=len(pending),orphanResults=dict(orphans)))
    if managed_pending or managed_errors: reasons.append(dict(check='managedPairs',unmatchedEntries=len(managed_pending),errors=managed_errors))
    if errors: reasons.append(dict(check='rowShape',failures=errors))
    # A report bound limits retained witnesses, never phase-pair processing.
    # Keep actual counts and diagnose truncation without inventing orphan calls.
    for label,observer in [('busProcessing',bus),('mixContributions',contributions),('roomBlend',room),('roomInput',room_input),('roomHistory',room_history),('roomWet',room_wet),('roomConfiguration',room_configuration),('mixBusLineage',contributions.bus_lineage if contributions else None),('mixerConsumer',consumer),('mixerFrame',frame),('playbackLineage',lineage)]:
        if observer and observer.counts.get('reportRowsOmitted'):
            reasons.append(dict(check='reportWitnessLimit',observer=label,omitted=observer.counts['reportRowsOmitted']))
    if bus:
        sampling=summary.get('playbackSampling',{})
        i=next(i for i,h in enumerate(manifest['nativeHooks']) if h['sourceKind']=='busOutputTask')
        chosen=sampling.get('selected',[]);skipped=sampling.get('skipped',[])
        entries=counts[(manifest['nativeHooks'][i]['name'],1)]
        policy_ok=sampling.get('busOutputTaskSelection')=='sampledRootsAllDescendants' if sampled_bus else i<len(skipped) and skipped[i]==0
        if sampling.get('allBusOutputTaskDescendants') is not True or not policy_ok or i>=len(chosen) or i>=len(skipped) or type(skipped[i]) is not int or skipped[i]<0 or type(chosen[i]) is not int or chosen[i]<entries:
            reasons.append(dict(check='busOutputTaskEndpointCoverage',observed=entries,selected=chosen[i:i+1],skipped=skipped[i:i+1]))
        if bus.tasks:reasons.append(dict(check='busOutputTaskCompletion',openTasks=len(bus.tasks)))
        bus_selection_scope=dict(mode='sampledRootsAllDescendants' if sampled_bus else 'allRootsAllDescendants',
            observedEntries=entries,selected=chosen[i:i+1],skipped=skipped[i:i+1],provesGlobalBusCoverage=False)
    if contributions and (contributions.mixes or contributions.consumers or contributions.bus_lineage.tasks):reasons.append(dict(check='mixContributionsCompletion',openMixes=len(contributions.mixes),openConsumers=len(contributions.consumers),openBusTasks=len(contributions.bus_lineage.tasks)))
    if room_input and (room_input.preps or room_input.stages or room_input.delay_inputs):reasons.append(dict(check='roomInputCompletion',openPreparations=len(room_input.preps),openInstances=len(room_input.stages),openDelayInputs=len(room_input.delay_inputs)))
    if room_wet and (room_wet.inputs or room_wet.by_room):reasons.append(dict(check='roomWetCompletion',openCalls=len(room_wet.inputs),openRoomReturns=len(room_wet.by_room)))
    if room_history and room_history.inputs:reasons.append(dict(check='roomHistoryCompletion',openCalls=len(room_history.inputs)))
    if room and room.instances:reasons.append(dict(check='roomBlendCompletion',openInstances=len(room.instances)))
    device_result=device.publish() if device else None
    mixer_result=mixer.publish() if mixer else None
    frame_result=frame.publish() if frame else None
    if device and (device.summary.get('hookError') or device_result['openSinkScopes']):
        reasons.append(dict(check='deviceCompletion',hookError=device.summary.get('hookError'),openSinkScopes=device_result['openSinkScopes']))
    if device:
        selected=summary.get('playbackSampling',{}).get('selected',[])
        for i,hook in enumerate(manifest['nativeHooks']):
            if hook.get('hookBinding')=='observedRenderClientVtable' and (i>=len(selected) or type(selected[i]) is not int or selected[i]<counts[(hook['name'],1)]):
                reasons.append(dict(check='deviceSelectedCount',hook=hook['name'],actual=counts[(hook['name'],1)],expected=selected[i] if i<len(selected) else None))
    if mixer_result and mixer_result['openMasterScopes']:
        reasons.append(dict(check='mixerCompletion',openMasterScopes=mixer_result['openMasterScopes']))
    if frame_result:
        if frame_result['openMixCalls'] or frame_result['openResetCalls'] or frame_result['openContextCalls']:
            reasons.append(dict(check='mixerFrameCompletion',openMixCalls=frame_result['openMixCalls'],openResetCalls=frame_result['openResetCalls'],openContextCalls=frame_result['openContextCalls']))
        reasons.extend(endpoint_coverage_diagnostics(summary,manifest['nativeHooks'],expected['mixerFrameUnsampledHookKinds'],counts))
        if reasons:
            frame.withhold_interval_joins()
            frame_result=frame.publish()
        frame_result['endpointSelectionScope']=endpoint_selection_scope(summary,manifest['nativeHooks'],expected['mixerFrameUnsampledHookKinds'],counts)
    handoff_result=None
    if handoff:
        sampling=summary.get('playbackSampling',{});selected=sampling.get('selected',[])
        checks=[]
        for kind in expected['sinkHandoffUnsampledHookKinds']:
            index=next(i for i,h in enumerate(manifest['nativeHooks']) if h['sourceKind']==kind);hook=manifest['nativeHooks'][index]
            if index>=len(selected) or type(selected[index]) is not int or selected[index]<counts[(hook['name'],1)]:
                checks.append(dict(check='sinkHandoffSelectedCount',hook=hook['name'],actual=counts[(hook['name'],1)],selected=selected[index:index+1]))
        if handoff.calls:checks.append(dict(check='sinkHandoffOpenCalls',actual=len(handoff.calls)))
        reasons.extend(checks)
        if reasons:handoff.withhold(['captureDiagnosticsPresent'])
        handoff_result=handoff.report()
        handoff_result['masterConversionDeviceLinks']=link_master_device(handoff_result,mixer_result,device_result)
    if is_master and reasons:
        mixer.withhold_master_comparisons();mixer_result=mixer.publish()
    device_selection_scope=endpoint_selection_scope(summary,manifest['nativeHooks'],[h['name'] for h in manifest['nativeHooks'] if h.get('hookBinding')=='observedRenderClientVtable'],counts,key_field='name') if device else None
    lineage_result=lineage.publish(managed) if lineage else None
    bus_result=bus.publish(reasons) if bus else None
    if bus_result:
        bus_result['taskDeviceLinks']=link_task_device(bus_result,handoff_result)
        bus_result['taskSelectionScope']=bus_selection_scope
        eq_chains=[fx['biquad'] for task in bus_result['rows'] for fx in task.get('effects',[]) if fx.get('biquad',{} ) and fx['biquad']['status']=='eqBiquadOperandChain']
        device_tasks={(link['windowId'],link['taskCaptureId']) for link in bus_result['taskDeviceLinks']}
        device_eq_chains=[fx['biquad'] for task in bus_result['rows'] if (task['windowId'],task['taskCaptureId']) in device_tasks for fx in task.get('effects',[]) if fx.get('biquad') and fx['biquad']['status']=='eqBiquadOperandChain']
        comparisons=[step.get('comparison',{}) for chain in eq_chains for step in chain['steps']]
        device_comparisons=[step.get('comparison',{}) for chain in device_eq_chains for step in chain['steps']]
        bus_result['questionCoverage']=dict(taskDevicePrefixJoins=len(bus_result['taskDeviceLinks']),eqOperandChains=len(eq_chains),
            eqOperandChainsToDevice=len(device_eq_chains),eqPrefixChangesToDevice=sum(any(s['changedPrefix'] for s in chain['steps']) for chain in device_eq_chains),
            eqPrefixChanges=sum(any(s['changedPrefix'] for s in chain['steps']) for chain in eq_chains),
            dspComparisonStatusCounts=dict(Counter(c.get('status','notCompared') for c in comparisons)),
            exactNonzeroDspPrefixesToDevice=sum(c.get('status')=='exactFiniteNonzeroBiquadPrefix' for c in device_comparisons),
            eqChainsAllDspPrefixesExactToDevice=sum(all(s.get('comparison',{}).get('status') in ('exactFiniteNonzeroBiquadPrefix','zeroPrefixOnly') for s in chain['steps']) and any(s.get('comparison',{}).get('status')=='exactFiniteNonzeroBiquadPrefix' for s in chain['steps']) for chain in device_eq_chains),
            dspReplay='boundedPrefixesCompared' if comparisons else 'operandsNotAdmitted',wholeEventContribution='unresolved',wholeBuffers='notCaptured')
    contribution_result=contributions.publish(reasons,bus_result,lineage_result) if contributions else None
    room_result=room.publish(reasons,contribution_result) if room else None
    input_result=room_input.publish(reasons,room_result) if room_input else None
    history_result=room_history.publish(reasons,room_result,input_result) if room_history else None
    wet_result=room_wet.publish(reasons,room_result,history_result) if room_wet else None
    configuration_result=room_configuration.publish(reasons,room_result,history_result,wet_result,configuration_oracle,input_result=input_result) if room_configuration else None
    return dict(schema='endfield.audio-playback-capture-review.v8',status='incompleteCapture' if reasons else 'partialCoverage',
        session=str(session),inputs=inputs,summary=summary,rows=row_count,diagnostics=reasons,
        wholeEventToDeviceClaim=False,
        evidenceBoundary=dict(conditional='Completed local pairs and matching declared reads are retained individually despite session loss. Serial matches are candidates under reviewed queue transport, not observed allocation generations.',
            unresolved='Queued allocation lifetime, complete source-to-context continuity, every mixer frame, whole PCM buffers, unobserved COM HRESULTs and audible device output.'),
        excludedHistoricalFields=sorted(excluded),fieldReadFailures=dict(fields_failed),
        hookPhases=[dict(hook=n,phase=p,count=c) for (n,p),c in counts.items()],
        pairs=[dict(hook=n,phase=p,count=c) for (n,p),c in pairs.items()],
        componentBranches=dict(branches),sourcePcmPrefixes=dict(pcm),
        managedSerials=len(managed),managedTextTruncations=truncated_paths,selectorSerialCandidates=list(serials.values()),
        nativeLineage=lineage_result,deviceOutput=device_result,deviceSelectionScope=device_selection_scope,mixerOutput=mixer_result,mixerFrameOutput=frame_result,sinkHandoffOutput=handoff_result,
        mixerConsumerOutput=consumer.publish(diagnostics=reasons,frame=frame_result,lineage=lineage_result) if consumer else None,
        busProcessingOutput=bus_result,**(dict(mixContributionsOutput=contribution_result) if contributions else {}),**(dict(roomBlendOutput=room_result) if room else {}),**(dict(roomInputOutput=input_result) if room_input else {}),**(dict(roomHistoryOutput=history_result) if room_history else {}),**(dict(roomWetOutput=wet_result) if room_wet else {}),**(dict(roomConfigurationOutput=configuration_result) if room_configuration else {}),examples=examples)


def link_master_device(handoff, mixer, device):
    """Join only checked write/consume IDs and completed same-submit device copies."""
    conversions={(scope['windowId'],c['sinkInputCaptureId']):(scope,c) for scope in mixer['completedMasterScopes'] for c in scope['conversions']}
    copies={}
    for copy in device['copies']:
        if copy['releaseHresultBits']==0 and copy['sinkPrefixByteEqual']:
            copies.setdefault((copy['windowId'],copy['sinkCaptureId']),[]).append(copy)
    links=[]
    for row in handoff['joins']:
        conversion=conversions.get((row['windowId'],row['writeCaptureId']))
        if not conversion or not row['convertedPrefixMatchesSubmission']:continue
        scope,child=conversion
        for copy in copies.get((row['windowId'],row['sinkCaptureId']),[]):
            if scope['threadId']!=row['threadId'] or copy['threadId']!=row['threadId']:continue
            if (child['sink'],child['renderClient'],child['convertedSamplePointer'])!=(row['sink'],row['renderClient'],row['samplePointer']):continue
            if (copy['sink'],copy['client'],copy['inputBuffer'])!=(row['sink'],row['renderClient'],row['samplePointer']):continue
            links.append(dict(row,masterCaptureId=scope['masterCaptureId'],outputConsumerCaptureId=child['outputConsumerCaptureId'],
                getCaptureId=copy['getCaptureId'],releaseCaptureId=copy['releaseCaptureId'],
                comparedPrefixBytes=min(row['comparedPrefixBytes'],copy['copiedPrefixBytes']),finiteNonzeroPrefix=copy['finiteNonzeroPrefix'],
                evidenceBoundary='conditionalCompletedMasterConversionWriteConsumeAndSameSubmissionDeviceCopy'))
    return links


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path); parser.add_argument('--game-root',type=Path,required=True)
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--device',action='store_true',help='interpret the selected audio-device recipe and same-sink COM pairs')
    modes.add_argument('--mixer',action='store_true',help='interpret stored owner identity and paired mixer output conversion')
    modes.add_argument('--mixer-frame',action='store_true',help='interpret paired bus mixing/publication/reset intervals')
    modes.add_argument('--sink-handoff',action='store_true',help='interpret explicit sink-write/frame-end/submission windows and device copies')
    modes.add_argument('--mixer-consumer',action='store_true',help='compare original unfiltered consumer PCM/gain/matrix and initial/returned output')
    modes.add_argument('--master-stage',action='store_true',help='compare admitted master input/gain and paired conversion/device output')
    modes.add_argument('--room-configuration',action='store_true',help='compare captured Room settings and original owned derived configuration')
    modes.add_argument('--room-wet',action='store_true',help='compare early taps, four-ring late feedback and final wet damping')
    modes.add_argument('--room-history',action='store_true',help='compare live tone matrices and paired diffusion history')
    modes.add_argument('--room-input',action='store_true',help='compare original RoomVerb stereo fold and circular history')
    modes.add_argument('--room-blend',action='store_true',help='compare original RoomVerb three-buffer blend and actual instance return')
    modes.add_argument('--mix-contributions',action='store_true',help='compare original per-channel AVX contributions, ordered mixed prefixes and conditional source/device joins')
    modes.add_argument('--bus-processing',action='store_true',help='compare same-task mix/post-processing/master transitions and floating frame-gain calls')
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/audio/playback_capture_current.json')
    args=parser.parse_args()
    try:
        if REPO_ROOT/'reports' not in args.output.resolve().parents:
            raise ValueError('playback audit output must live under reports/')
        recipe=args.output.with_name(args.output.stem+'_recipe.json')
        expected=prepare(args.game_root,recipe,device=args.device,mixer=args.mixer,mixer_frame=args.mixer_frame,sink_handoff=args.sink_handoff,mixer_consumer=args.mixer_consumer,master_stage=args.master_stage,bus_processing=args.bus_processing,mix_contributions=args.mix_contributions,room_blend=args.room_blend,room_input=args.room_input,room_history=args.room_history,room_wet=args.room_wet,room_configuration=args.room_configuration)
        oracle=None
        if args.room_configuration:
            import shutil
            from scripts.game_data.wwise_room_configuration_host import OriginalRoomConfiguration
            private=REPO_ROOT/'tmp/audio/room_configuration_host/AkSoundEngine.dll';private.parent.mkdir(parents=True,exist_ok=True)
            source=args.game_root/'Endfield_Data/Plugins/x86_64/AkSoundEngine.dll'
            if not private.is_file() or hashlib.sha256(private.read_bytes()).hexdigest()!=expected['files']['akSoundEngine']['sha256']:shutil.copyfile(source,private)
            oracle=OriginalRoomConfiguration(gameassembly=args.game_root/'GameAssembly.dll',metadata=args.game_root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',ak_sound_engine=source,original_ak=private)
        result=review(args.session,expected,configuration_oracle=oracle)
        result['inputs'].append(fingerprint(recipe))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('Playback capture interpretation withheld: '+str(error)); return 2
    print(f"Playback capture: {result['status']}; {result['rows']} rows; Event-to-device claim withheld -> {args.output}")
    for issue in result['diagnostics']: print('  '+json.dumps(issue))
    return 0


if __name__=='__main__': raise SystemExit(main())
