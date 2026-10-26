"""Strict raw Mission/Audio composition and synchronous link consistency.

All inputs are retained local files. This reader establishes neither producer
origin nor a fresh native ABI, async ownership, callback effects or playback.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import re
import struct

COMPOSITION_SCHEMA='endfieldCapture.missionAudioComposition.v1'
AUDIO_SCHEMA='audioRuntimeTrace.hooks.v2'
MISSION_SCHEMA='endfieldCapture.missionTraceBuild.v2'
LINK_SCHEMA='endfieldCapture.observationLink.v1'
LINK_SUMMARY='endfieldCapture.observationLinkSummary.v1'
# Typed runtime adapter selectors, never installed addresses or source hashes.
AUDIO_HOOKS={
 'AudioAdapter._PostEventWithExternalSource':('GameAssembly.dll','win64.il2cpp_post_event_external_source.v2'),
 'AudioAdapter._PostEvent':('GameAssembly.dll','win64.il2cpp_post_event.v2'),
 'AkSoundEngine.SourceMediaLookup':('AkSoundEngine.dll','win64.source_media_lookup.v2'),
 'AkSoundEngine.SourceProviderPreparation':('AkSoundEngine.dll','win64.source_provider_preparation.v2'),
 'AkSoundEngine.DefaultIoOpenDispatch':('AkSoundEngine.dll','win64.default_io_open_dispatch.v1'),
}

def api():
    from scripts.game_data import mission_trace_inspect
    return mission_trace_inspect

def rva(value):
    m=api()
    if isinstance(value,str):
        m.require(re.fullmatch(r'0x[0-9a-fA-F]{1,8}',value)is not None,'audio hook RVA syntax')
        value=int(value,16)
    m.require(type(value)is int and 0<value<2**32,'audio hook RVA bounds')
    return value

def mission_projection(profile):
    """Accept one finite composed declaration, not an arbitrary provider mask."""
    m=api();need=m.require
    if profile.get('schema')!=AUDIO_SCHEMA:
        need('observerComposition'not in profile,'composition requires exact AudioV2 top schema')
        return profile,False
    composition=profile.get('observerComposition')
    need(isinstance(composition,dict)and set(composition)=={'schema','missionBuildSchema','observerProviders','providerMask','missionBuild'},'combined observer composition shape')
    need(composition['schema']==COMPOSITION_SCHEMA and composition['missionBuildSchema']==MISSION_SCHEMA
         and composition['observerProviders']==['mission-trace','audio'] and type(composition['providerMask'])is int and composition['providerMask']==130,
         'combined observer declaration must exactly select mission-trace/audio130')
    mission=composition['missionBuild']
    need(isinstance(mission,dict)and mission.get('schema')==MISSION_SCHEMA and mission.get('recipeSchema')=='endfield.mission-trace-capture-recipe.v15'
         and mission.get('observerProviders')==['mission-trace']and type(mission.get('providerMask'))is int and mission['providerMask']==128
         and mission.get('profile')=='mission-trace','combined nested MissionBuild2 declaration')
    extras={'hooks','observerComposition','moduleName','nativeModuleName'}
    changed={'schema','observerProviders','providerMask','files'}
    need(set(profile)==set(mission)|extras,'combined top profile has missing or unknown fields')
    need(all(profile[k]==v for k,v in mission.items()if k not in changed),'combined Mission projection differs')
    need(profile.get('observerProviders')==['mission-trace','audio']and type(profile.get('providerMask'))is int and profile['providerMask']==130
         and profile.get('processName')=='Endfield.exe'and profile.get('moduleName')=='GameAssembly.dll'
         and profile.get('nativeModuleName')=='AkSoundEngine.dll','combined provider/module declaration differs')
    files=profile.get('files');base=mission.get('files')
    need(isinstance(files,dict)and isinstance(base,dict)and set(files)==set(base)|{'akSoundEngine'}
         and all(files[k]==v for k,v in base.items()),'combined selected native file projection differs')
    for key in ('executable','gameAssembly','metadata','akSoundEngine'):
        row=files.get(key)
        need(isinstance(row,dict)and set(row)=={'relativePath','bytes','sha256'}
             and isinstance(row['relativePath'],str)and 0<len(row['relativePath'])<=512
             and type(row['bytes'])is int and row['bytes']>0
             and isinstance(row['sha256'],str)and re.fullmatch('[0-9a-f]{64}',row['sha256'])is not None,
             'combined native file row invalid: '+key)
    hooks=profile.get('hooks');need(isinstance(hooks,list)and len(hooks)==5,'combined requires exact five Audio hooks')
    need([h.get('name')for h in hooks if isinstance(h,dict)]==list(AUDIO_HOOKS),'Audio hooks must follow exact host canonical order')
    names=set();sites=set();mission_sites={rva(h['rva'])for h in mission.get('missionTraceHooks',[])}
    for hook in hooks:
        need(isinstance(hook,dict)and hook.get('name')in AUDIO_HOOKS and hook['name']not in names,'Audio hook selector missing/duplicate')
        name=hook['name'];module,abi=AUDIO_HOOKS[name];target=rva(hook.get('rva'))
        need(hook.get('module')==module and hook.get('abiId')==abi and hook.get('required')is True,'Audio typed hook ABI differs: '+name)
        need((module,target)not in sites and (module!='GameAssembly.dll'or target not in mission_sites),'Audio/Mission hook target overlap')
        names.add(name);sites.add((module,target))
        prefix=hook.get('expectedBytes');window=hook.get('sourceWindow')
        need(isinstance(prefix,str)and re.fullmatch('(?:[0-9a-f]{2}){16,256}',prefix)is not None
             and isinstance(window,dict)and set(window)=={'module','rva','bytes','sha256'}
             and window['module']==module and rva(window['rva'])==target and window['bytes']==prefix
             and window['sha256']==hashlib.sha256(bytes.fromhex(prefix)).hexdigest(),'Audio retained source prefix/window differs: '+name)
        need(all(hook.get(k,'')==''for k in ('readProgram','resultProgram','scopeTests'))and hook.get('scopeParentMask',0)==0,
             'combined fixed Audio hooks cannot select source-owner programs')
    need(names==set(AUDIO_HOOKS),'combined Audio selector set differs')
    return mission,True

def rows(artifacts,name,limits):
    m=api();m.require(name in artifacts and artifacts[name]['bytes']<=limits.journal_bytes,'missing or oversized combined journal: '+name)
    digest=hashlib.sha256();length=0;count=0
    with artifacts[name]['path'].open('rb')as source:
        while line:=source.readline(limits.input_line_bytes+1):
            count+=1;length+=len(line);digest.update(line)
            m.require(count<=limits.rows and length<=limits.journal_bytes and len(line)<=limits.input_line_bytes and line.endswith(b'\n'),'combined journal bounds: '+name)
            row=m.parse_json(line,name+':'+str(count));m.require(isinstance(row,dict),'combined journal object required: '+name)
            yield row
    m.require(length==artifacts[name]['bytes']and digest.hexdigest()==artifacts[name]['sha256'],'combined journal changed: '+name)

def audio_activation(profile):
    return {'schema':'audioRuntimeTrace.activation.v1','gameBuild':profile['gameBuild'],'processName':'Endfield.exe','moduleName':'GameAssembly.dll',
            'files':profile['files'],'hooks':[dict(name=h['name'],module=h['module'],rva=hex(rva(h['rva'])),abiId=h['abiId'],
                readProgram='',resultProgram='',scopeTests='',scopeParentMask=0,required=True)for h in profile['hooks']]}

def verify_audio_inputs(artifacts,profile,session,limits):
    m=api();need=m.require
    need(m.bound_object(artifacts,'private/audio-activation.json',limits)==audio_activation(profile),'combined Audio activation/profile differs')
    audio=m.bound_object(artifacts,'audio/summary.json',limits)
    need(audio.get('schema')=='endfieldCapture.audioSummary.v2'and audio.get('complete')is True
         and audio.get('hooksQuiescent')is True and audio.get('sourceOwnerSelected')is False
         and audio.get('sourceOwnerWriteComplete')is True and audio.get('windowActiveAtSessionStop')is False,'Audio completeness/window/stop gate')
    for key in ('dropped','unresolvedResults'):
        need(type(audio.get(key))is int and audio[key]==0,'Audio nonzero/invalid '+key)
    for key in ('attempted','enqueued','windowsStarted','windowsCompleted'):
        m.integer(audio.get(key),'Audio '+key)
    need(audio['attempted']==audio['enqueued']and 0<audio['windowsStarted']==audio['windowsCompleted'],'Audio queue/window accounting')
    opened=None;finished=0;last_end=0;spans=[]
    for row in rows(artifacts,'audio/windows.jsonl',limits):
        need(row.get('schema')=='endfieldCapture.audioWindow.v2','Audio window schema')
        start=m.integer(row.get('startNs'),'Audio window start');end=m.integer(row.get('endNs'),'Audio window end')
        if row.get('action')=='start':
            need(opened is None and start>last_end and end==0,'Audio window overlapping start');opened=start
        else:
            need(row.get('action')=='stop'and opened==start and end>=start,'Audio window unmatched stop');opened=None;finished+=1;last_end=end;spans.append((start,end))
    need(opened is None and finished==audio['windowsCompleted'],'Audio windows journal incomplete')
    writer=m.bound_object(artifacts,'collected/summary.json',limits)
    need(writer.get('schema')=='endfieldCapture.summary.v1'and writer.get('complete')is True and writer.get('writerError')is False
         and type(writer.get('dropped'))is int and writer['dropped']==0 and type(writer.get('invalidRecords'))is int and writer['invalidRecords']==0,
         'global event writer incomplete')
    m.integer(writer.get('records'),'global writer records')
    return audio,writer,spans

def inspect_links(artifacts,profile,mission_summary,hooks,session,limits):
    m=api();context=''
    def need(condition,detail):
        m.require(condition,'mission_audio_links: '+context+detail)
    mission,combined=mission_projection(profile);need(combined,'combined link inspection requires explicit composition')
    need(session.get('providers')==130 and type(session.get('providers'))is int,'combined session mask differs')
    numeric=m.integer(session.get('numericSessionId'),'numeric session ID');need(numeric>0,'zero numeric session ID')
    audio,writer,spans=verify_audio_inputs(artifacts,profile,session,limits)
    summary=m.bound_object(artifacts,'mission-trace/observation-links-summary.json',limits)
    need(summary.get('schema')==LINK_SUMMARY and summary.get('complete')is True and summary.get('writeComplete')is True
         and summary.get('windowClosed')is True and summary.get('synchronousEnclosureOnly')is True
         and all(summary.get(k)is False for k in ('asynchronousOwnershipProved','callbackEffectsProved','playbackProved','unlinkedAbsenceClaimed','requiresProcessRestart')),
         'observation link boundary/completeness gate')
    for key in ('queueFullDrops','contentionDrops','scopeFailures','scopeUnwinds','audioUnwinds','audioPairFailures','activeAudioCalls','activeMissionScopes','activeWriters','pending','unrecorded'):
        need(type(summary.get(key))is int and summary[key]==0,'observation link nonzero/invalid '+key)
    need(summary.get('queueCapacity')==8192 and type(summary.get('queueCapacity'))is int
         and summary.get('unlinkedSampleLimit')==256 and type(summary.get('unlinkedSampleLimit'))is int,'observation link fixed bounds differ')
    generation=m.integer(summary.get('generation'),'link generation');need(generation>0,'zero link generation')
    expected={'schema':LINK_SUMMARY,'journal':'observation-links.jsonl','summary':'observation-links-summary.json','synchronousEnclosureOnly':True,'complete':True}
    need(mission_summary.get('schema')=='endfieldCapture.missionTraceSummary.v5'and mission_summary.get('complete')is True
         and mission_summary.get('observationLinks')==expected,'Mission/link final summary projection differs')
    linked={};pairs={};counts=Counter();sequence=0;required_mission=set()
    unsigned_fields=('generation','sequence','timestampNs','threadId','entryThreadId','audioCaptureId','audioParentCaptureId','audioHookIndex','missionInvocationId','missionParentInvocationId','missionRootInvocationId','missionDepth','returnValue','resultCode')
    fact_fields={'kind','eventId','audioObjectId','callbackType','callbackPointer','cookiePointer','methodInfoPointer','externalSourcePointer','externalCookie','codec'}
    for row in rows(artifacts,'mission-trace/observation-links.jsonl',limits):
        context='link row '+str(sequence+1)+' capture '+str(row.get('audioCaptureId'))[:32]+': '
        need(set(row)==set(unsigned_fields)|{'schema','phase','linked','scopeValid','scopeMatchesAtReturn','audioPairResolved','typedFacts'}and row.get('schema')==LINK_SCHEMA,'link row shape/schema')
        for key in unsigned_fields:m.integer(row[key],'link '+key,2**32-1 if key in {'threadId','entryThreadId','audioHookIndex','missionDepth','resultCode'}else 2**64-1)
        sequence+=1;need(row['sequence']==sequence and row['generation']==generation and row['audioCaptureId']>0,'link sequence/generation/capture ID')
        need(row['threadId']==row['entryThreadId']and row['threadId']>0 and row['scopeValid']is True and row['scopeMatchesAtReturn']is True,'link thread/scope mismatch')
        need(type(row['linked'])is bool and row['linked']==bool(row['missionInvocationId'])and type(row['audioPairResolved'])is bool,'link enclosure declaration')
        need(row['audioHookIndex']<len(profile['hooks'])and row['missionDepth']<64,'link selected hook/depth')
        facts=row['typedFacts'];need(isinstance(facts,dict)and set(facts)==fact_fields,'link typed facts shape')
        for key,value in facts.items():m.integer(value,'link fact '+key,2**32-1 if key in {'kind','eventId','callbackType','externalCookie','codec'}else 2**64-1)
        hook=profile['hooks'][row['audioHookIndex']]
        kind=1 if hook['name']=='AudioAdapter._PostEvent'else 2 if hook['name']=='AudioAdapter._PostEventWithExternalSource'else 0
        need(facts['kind']==kind if row['phase']!='native-entry'else facts['kind']==0,'link fact kind/actual hook differs')
        if kind==0:need(all(v==0 for v in facts.values()),'untyped hook has fabricated typed facts')
        if row['linked']:
            need(row['missionRootInvocationId']>0,'linked root missing');required_mission.add(row['missionInvocationId'])
        else:need(row['missionParentInvocationId']==row['missionRootInvocationId']==row['missionDepth']==0,'unlinked row claims Mission ancestry')
        identity=row['audioCaptureId'];phase=row['phase'];counts[('linked'if row['linked']else'unlinked',phase)]+=1
        need(phase in {'entry','result','native-entry'},'unwind/unknown link phase')
        if phase=='entry':
            need(identity not in pairs and not row['audioPairResolved']and row['returnValue']==row['resultCode']==0,'link duplicate/invalid entry');pairs[identity]=row
        elif phase=='native-entry':
            need(identity not in pairs and not row['audioPairResolved'],'native link duplicates pair');pairs[identity]=row
        else:
            entered=pairs.get(identity);need(entered is not None and entered['phase']=='entry'and row['audioPairResolved'],'link unmatched result')
            keys=set(row)-{'sequence','phase','timestampNs','returnValue','resultCode','audioPairResolved'}
            need(all(row[k]==entered[k]for k in keys)and row['timestampNs']>=entered['timestampNs'],'link result identity/facts differ');pairs[identity]=row
        if row['linked']:linked[(identity,phase)]=row
    context='link summary: '
    need(all(row['phase']!='entry'for row in pairs.values()),'link unfinished entry')
    for key in ('attempted','enqueued','popped','written'):need(type(summary.get(key))is int and summary[key]==sequence,'link row accounting: '+key)
    need(summary.get('bytesWritten')==artifacts['mission-trace/observation-links.jsonl']['bytes'],'link byte accounting')
    for label,phase,key in [('linked','entry','linkedEntries'),('linked','result','linkedResults')]:need(summary.get(key)==counts[label,phase]and type(summary.get(key))is int,'link count '+key)
    for phase,key,excluded in [('entry','unlinkedEntries','unlinkedExcludedEntries'),('result','unlinkedResults','unlinkedExcludedResults')]:
        m.integer(summary.get(excluded),excluded);need(summary.get(key)==counts['unlinked',phase]+summary[excluded]and type(summary.get(key))is int,'unlinked sample accounting')
    need(summary['unlinkedExcludedEntries']==summary['unlinkedExcludedResults'],'unlinked excluded call unfinished')
    m.integer(summary.get('nativeExcluded'),'nativeExcluded')
    need(summary.get('nativeEntries')==counts['linked','native-entry']+counts['unlinked','native-entry']+summary['nativeExcluded'],'native sample accounting')
    need(counts['unlinked','entry']+counts['unlinked','native-entry']<=256,'unlinked sample exceeds bound')
    # Independently parse full explicit Mission pairs; no temporal-nearness join.
    from scripts.game_data.mission_trace_invocations import Invocations
    invocations=Invocations();owners={};stacks={}
    for row in rows(artifacts,'mission-trace/events.jsonl',limits):
        context='Mission invocation '+str(row.get('invocationId'))[:32]+': '
        index=m.integer(row.get('hookIndex'),'Mission hook index',len(hooks)-1)
        invocations.observe(row,hooks[index]);thread=row['threadId'];stack=stacks.setdefault(thread,[])
        if row['phase']=='enter':
            root=stack[0]if stack else row['invocationId'];stack.append(root)
            if row['invocationId']in required_mission:owners[row['invocationId']]=(thread,row['parentInvocationId'],root,row['depth'],False)
        elif row['phase']in {'return','unwind'}:
            if stack:stack.pop()
            if row['invocationId']in owners:owners[row['invocationId']]=(*owners[row['invocationId']][:4],row['phase']=='return')
    invocations.finish(True)
    for row in linked.values():
        context='link capture '+str(row['audioCaptureId'])+': '
        need(owners.get(row['missionInvocationId'])==(row['threadId'],row['missionParentInvocationId'],row['missionRootInvocationId'],row['missionDepth'],True),'link/Mission explicit invocation/root/parent/depth differs')
    found=set();total=0
    for row in rows(artifacts,'events.jsonl',limits):
        context='Audio/global writer row '+str(total+1)+': '
        total+=1;need(type(row.get('writerSequence'))is int and row['writerSequence']==total and row.get('sessionId')==numeric,'global event sequence/session mismatch')
        if row.get('provider')!=2 or row.get('type')!=10:continue
        need(type(row.get('provider'))is int and type(row.get('type'))is int,'Audio provider/type integer required')
        raw=row.get('payloadHex');need(row.get('payloadBytes')==208 and isinstance(raw,str)and re.fullmatch('[0-9a-fA-F]{416}',raw)is not None,'Audio exact payload shape')
        data=bytes.fromhex(raw);capture,parent,result,fact0,fact1=struct.unpack_from('<5Q',data);nesting,index,code,flags=struct.unpack_from('<4I',data,40);kind=data[56]
        need(kind in {0,1},'combined fixed Audio callback kind');phase='entry'if kind==0 else'result';key=(capture,phase)
        if key not in linked:continue
        need(key not in found,'duplicate linked Audio journal phase');found.add(key);target=linked[key]
        need(row.get('threadId')==target['threadId']and parent==target['audioParentCaptureId']and index==target['audioHookIndex'],'Audio/sidecar actual ID/thread/hook/parent differs')
        need(not flags&((1<<30)|(1<<31)|(1<<1))and (kind==0 or flags&4),'Audio linked truncation/drop/pair failure')
        name=data[57:105].split(b'\0',1)[0].decode('ascii','strict');need(name==profile['hooks'][index]['name'],'Audio actual hook name differs')
        need(row.get('timestampNs')==target['timestampNs'],'Audio/sidecar same-call timestamp differs')
        need(any(start<=target['timestampNs']<=end for start,end in spans),'linked Audio phase outside recorded publication window')
        if phase=='result':need(result==target['returnValue']and code==target['resultCode'],'Audio/sidecar actual result differs')
        elif target['typedFacts']['kind']in {1,2}:
            facts=target['typedFacts'];need(fact0==facts['eventId']and fact1==facts['audioObjectId'],'Audio/sidecar typed request facts differ')
    context='final accounting: '
    need(total==writer['records'],'global writer journal row accounting')
    need(found==set(linked),'linked sidecar call missing actual Audio phase (audio window off or record loss)')
    return {'schema':'endfield.mission-audio-link-analysis.v1','status':'analyzed','linkedRows':len(linked),'linkedCalls':counts['linked','entry'],
            'linkedNativeEntries':counts['linked','native-entry'],'unlinkedSampledCalls':counts['unlinked','entry'],
            'unlinkedExcludedCalls':summary['unlinkedExcludedEntries'],'sameActualCaptureIdsBound':True,
            'nativeValidationReproved':False,'producerOriginAuthenticated':False,'asynchronousOwnershipProved':False,
            'callbackEffectsProved':False,'playbackProved':False,'boundary':'Explicit same-thread synchronous enclosure and raw record equality only; no timestamp-nearness association or unlinked absence claim.'}

def package_exit(artifacts,session,inventory_hash,limits):
    m=api()
    for name,row in sorted(artifacts.items()):
        digest=hashlib.sha256();size=0
        with row['path'].open('rb')as source:
            while block:=source.read(1024*1024):
                size+=len(block);m.require(size<=row['bytes'],'combined package grew: '+name);digest.update(block)
        m.require(size==row['bytes']and digest.hexdigest()==row['sha256'],'combined package changed at exit: '+name)
    data=m.read_bytes(session/'collected/inventory.json',limits.json_bytes)
    m.require(hashlib.sha256(data).hexdigest()==inventory_hash,'combined inventory changed at exit')
