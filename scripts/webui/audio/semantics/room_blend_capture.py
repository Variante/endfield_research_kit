"""Actual RoomVerb instance nesting and separately rounded three-buffer sums."""
from __future__ import annotations
from collections import Counter
import struct
from scripts.game_data.wwise_room_blend_arithmetic import evaluate_prefix,UnsupportedArithmetic

KINDS=('roomVerbExecute','roomVerbBlend')
LIMIT=100000

def words(facts,prefix):
    result=[facts.get(prefix+str(i)) for i in range(4)]
    return result if all(type(w) is int and 0<=w<2**32 for w in result) else None


class RoomBlendCapture:
    def __init__(self,config):self.config=config;self.instances={};self.effects={};self.rows=[];self.counts=Counter()

    def entry(self,row,facts,pending,ancestor):
        if row['phase']!=1 or not row['hook'].endswith('.roomVerbExecute'):return
        if len(self.instances)>=LIMIT:raise ValueError('room instance bound exceeded')
        fx=ancestor(row,pending,'busEffectConsume');task=ancestor(row,pending,'busOutputTask');processing=ancestor(row,pending,'busPostMixProcessing')
        fx_facts=pending[(row['windowId'],fx['captureId'])][1] if fx else {}
        full_input=fx_facts.get('validFrames')==self.config['selection']['validFrames']
        sample_witness=bool(facts.get('samplePointer')) and (fx_facts.get('samplePointer')==facts['samplePointer'] and fx_facts.get('owner') if full_input else
            fx_facts.get('validFrames')==0 and fx_facts.get('samplePointer') is None and fx_facts.get('owner') is None)
        admitted=bool(fx and task and processing and fx['parentCaptureId']==processing['captureId'] and fx_facts.get('firstEffectObject')==row['args'][0] and fx_facts.get('firstEffectExecuteTarget')==row['moduleBase']+int(self.config['executeRva'],16) and
            fx_facts.get('firstEffectVtable')==row['moduleBase']+int(self.config['vtableRva'],16) and
            fx_facts.get('selectedDescriptor')==facts.get('buffer') and sample_witness and
            all(fx_facts.get(k)==1 for k in ('selectedCount','objectCount','inPlaceMode')) and
            all(fx_facts.get(k)==self.config['selection'][k] for k in ('format','capacity')))
        self.instances[(row['windowId'],row['captureId'])]=dict(entry=row,initial=facts,fxCaptureId=fx['captureId'] if fx else None,taskCaptureId=task['captureId'] if task else None,
            processingCaptureId=processing['captureId'] if processing else None,owner=fx_facts.get('owner'),admitted=admitted,calls=[])

    def validate_addresses(self,row,facts,fields):
        if row['phase']==3:return
        for i,f in enumerate(fields):
            if facts.get(f['name']) is None or f['kind'] in ('argument','argumentU32'):continue
            base=facts.get('samplePointer') if f['kind']=='bytes' and row['hook'].endswith('.roomVerbExecute') else row['args'][f['argIndex']]
            if f.get('pointerOffsets') and f['kind']!='bytes':
                if not row['hook'].endswith('.roomVerbExecute') or f['kind']!='u32' or f['pointerOffsets']!=[self.config['layout']['parameterObject']]:raise ValueError('room parameter projection lacks original instance pointer')
                base=facts.get('parameterObject')
            if base is None or row['addresses'][i]!=base+f['offset']:raise ValueError('room blend operand address differs')
        pointer=facts.get('samplePointer') if row['hook'].endswith('.roomVerbExecute') else row['args'][0]
        if row['spanBytes'] and row['spanAddress']!=pointer:raise ValueError('room blend span address differs')

    def compare(self,before,row,initial,final,closed):
        result=dict(captureId=row['captureId'],entrySequence=before['sequence'],returnSequence=row['sequence'],destinationPointer=before['args'][0],
            wetPointers=before['args'][1:3],beforePrefix=before['spanHex'],afterPrefix=row['spanHex'],frames=initial.get('frames'))
        def reject(status):result['status']=status;return result
        if row['phase']!=2 or not closed or not before.get('observationWindowOpen'):return reject('roomBlendNotClosedNormally')
        if before['returnAddress']-before['moduleBase'] not in [int(x,16) for x in self.config['callerReturnRvas']]:return reject('roomBlendCallerNotSelected')
        frames=initial.get('frames')
        if frames not in self.config['selection']['blendFrameCounts'] or final.get('frames')!=frames:return reject('roomBlendExtentNotSelected')
        names=('dryPreviousBits','wetAPreviousBits','wetBPreviousBits','dryTargetBits','wetATargetBits','wetBTargetBits')
        gains=[initial.get(k) for k in names]
        if any(type(w) is not int or final.get(k)!=w for k,w in zip(names,gains)):return reject('roomBlendGainWordsIncompleteOrChanged')
        a,b=words(initial,'wetAWord'),words(initial,'wetBWord')
        if a is None or b is None or before['spanBytes']!=16 or row['spanBytes']!=16:return reject('roomBlendOperandsIncomplete')
        if words(final,'wetAWord')!=a or words(final,'wetBWord')!=b:return reject('roomBlendWetInputChanged')
        if any(abs(before['args'][0]-p)<frames*4 for p in before['args'][1:3]):return reject('roomBlendStorageOverlaps')
        if not before.get('roundingModeSampled'):return reject('roomBlendRoundingNotObserved')
        dry=list(struct.unpack('<4I',bytes.fromhex(before['spanHex'])));actual=list(struct.unpack('<4I',bytes.fromhex(row['spanHex'])))
        try:expected=evaluate_prefix(dry,a,b,gains[:3],gains[3:],frames,before.get('mxcsr'))
        except UnsupportedArithmetic as e:return reject(str(e))
        result.update(expected=expected,actual=actual,previousGains=gains[:3],targetGains=gains[3:],wetWords=[a,b],
            gainMode='constant' if all(a==b or not(a&0x7fffffff) and not(b&0x7fffffff) for a,b in zip(gains[:3],gains[3:])) else 'transition',nonzeroWetPrefix=any(w&0x7fffffff for w in a+b),changedPrefix=before['spanHex']!=row['spanHex'])
        return reject('exactRoomBlendPrefix' if expected==actual else 'roomBlendArithmeticMismatch')

    def completed(self,before,row,initial,final,pending,ancestor,*,closed):
        kind=row['hook'].rsplit('.',1)[-1];key=row['windowId'],row['captureId']
        if kind=='busEffectConsume':
            for result in self.effects.pop(key,[]):
                stable=all(initial.get(k) and initial.get(k)==final.get(k) for k in ('firstEffectObject','firstEffectVtable','firstEffectExecuteTarget','selectedDescriptor','samplePointer','owner')) and all(initial.get(k)==final.get(k)==self.config['selection'][k] for k in ('format','capacity','validFrames'))
                result['effectReturnedPrefixMatches']=bool(result['roomReturnedPrefixMatches'] and stable and row['phase']==2 and closed and row['spanBytes']>=16 and
                    result['roomReturnSequence']<row['sequence'] and result['roomReturnedPrefix']==row['spanHex'][:32] and initial.get('firstEffectObject')==result['instance'] and
                    initial.get('selectedDescriptor')==result['buffer'] and initial.get('samplePointer')==result['samplePointer'])
                self.counts['effectReturnedPrefixJoins']+=result['effectReturnedPrefixMatches']
            return
        if kind=='roomVerbBlend':
            parent=ancestor(row,pending,'roomVerbExecute');scope=self.instances.get((row['windowId'],parent['captureId'])) if parent else None
            if not scope or not scope['admitted']:self.counts['roomBlendInstanceNotSelected']+=1;return
            if len(scope['calls'])>=LIMIT:raise ValueError('room blend call bound exceeded')
            item=self.compare(before,row,initial,final,closed);scope['calls'].append(item);self.counts[item['status']]+=1
        elif kind=='roomVerbExecute':
            scope=self.instances.pop(key,None)
            if scope is None:raise ValueError('room instance return lacks entry')
            s=self.config['selection'];geometry=all(initial.get(k)==s[k] and final.get(k)==s[k] for k in ('format','capacity','validFrames')) and all(initial.get(k) and initial[k]==final.get(k) for k in ('instance','buffer','samplePointer','parameterObject'))
            first=[c for c in scope['calls'] if c['destinationPointer']==initial.get('samplePointer')]
            joined=bool(first) and scope['admitted'] and geometry and row['phase']==2 and closed and before.get('observationWindowOpen') and before['spanBytes']==row['spanBytes']==16 and first[0]['beforePrefix']==before['spanHex'] and first[-1]['afterPrefix']==row['spanHex'] and all(c['status']=='exactRoomBlendPrefix' for c in first) and all(a['returnSequence']<b['entrySequence'] and a['afterPrefix']==b['beforePrefix'] for a,b in zip(first,first[1:]))
            result=dict(windowId=row['windowId'],threadId=row['threadId'],roomCaptureId=row['captureId'],taskCaptureId=scope['taskCaptureId'],effectCaptureId=scope['fxCaptureId'],instance=before['args'][0],
                buffer=initial.get('buffer'),samplePointer=initial.get('samplePointer'),owner=scope['owner'],processingCaptureId=scope['processingCaptureId'],roomReturnSequence=row['sequence'],roomReturnedPrefix=row['spanHex'],effectReturnedPrefixMatches=False,
                initialValidFrames=initial.get('validFrames'),finalValidFrames=final.get('validFrames'),instanceAdmitted=scope['admitted'],
                calls=scope['calls'],firstPlaneCaptureIds=[c['captureId'] for c in first],roomReturnedPrefixMatches=joined,wholeEventToDeviceClaim=False)
            if len(self.rows)<LIMIT:
                self.rows.append(result)
                if scope['fxCaptureId'] is not None:self.effects.setdefault((row['windowId'],scope['fxCaptureId']),[]).append(result)
            else:self.counts['reportRowsOmitted']+=1
            self.counts['roomReturnedPrefixJoins']+=joined

    def publish(self,diagnostics,contributions):
        rows=[] if diagnostics else self.rows
        graph=(contributions or {}).get('busLineage',{});nodes={(n['windowId'],n['taskCaptureId']):n for n in graph.get('nodes',())}
        path_counts=Counter()
        for p in graph.get('eventDeviceCandidates',()):
            tasks={p['source']['sourceTaskCaptureId']}|{h['consumerTaskCaptureId'] for h in p['busHops']}
            for task in tasks:path_counts[(p['windowId'],task)]+=1
        for r in rows:
            n=nodes.get((r['windowId'],r['taskCaptureId']))
            admitted=n and r['effectReturnedPrefixMatches'] and n['threadId']==r['threadId'] and n['processingCaptureId']==r['processingCaptureId'] and all(n['storage'][k]==r[v] for k,v in [('descriptor','buffer'),('sample','samplePointer'),('owner','owner')])
            r['busProcessingNode']=dict(taskCaptureId=n['taskCaptureId'],mixCaptureId=n['mixCaptureId'],processingCaptureId=n['processingCaptureId'],
                effectReturnMatchesProcessedPrefix=r['roomReturnedPrefix']==n['processedPrefix']) if admitted else None
            r['conditionalEventDevicePathCount']=path_counts[(r['windowId'],r['taskCaptureId'])] if admitted else 0
        return dict(schema='endfield.audio-room-blend-witness.v2',rows=rows,counts=dict(self.counts),openInstances=len(self.instances),diagnostics=list(diagnostics),wholeEventToDeviceClaim=False,
            evidenceBoundary='Original three-buffer sums use observed dry/output and two wet prefixes, three gain pairs, frame count and entry rounding inside the actual registered RoomVerb instance. Per-call arithmetic does not require a full input frame at Room entry. First-plane Room/effect/bus chains additionally require a full unchanged input/return extent, instance/descriptor stability, original entry prefix, all observed first-prefix blends and matching normal return. Zero-input extent expansion is reported separately and cannot supply that chain. Wet-buffer generation, whole RoomVerb DSP/history, isolated Event wet contribution and full buffers remain unresolved.')
