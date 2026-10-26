"""Actual per-channel additions, ordered snapshots and conditional source joins."""
from __future__ import annotations
from collections import Counter
import struct
from scripts.game_data.wwise_biquad_arithmetic import evaluate_accumulation_prefix,UnsupportedArithmetic
from scripts.webui.audio.semantics.mix_bus_lineage import MixBusLineage

KINDS=('matrixAccumulateConstant','matrixAccumulateRamp')
LIMIT=100000


def words(facts,prefix):
    result=[facts.get(prefix+str(i)) for i in range(4)]
    return result if all(type(w) is int and 0<=w<2**32 for w in result) else None


def hex_words(value):return struct.pack('<4I',*value).hex()


class MixContributionsCapture:
    def __init__(self,config,return_sites):
        self.config=config;self.mixes={};self.consumers={};self.rows=[];self.counts=Counter()
        self.bus_lineage=MixBusLineage(return_sites)

    def ancestor(self,row,pending,kind):
        parent=row['parentCaptureId'];seen=set()
        while parent and parent not in seen and len(seen)<64:
            seen.add(parent);entry=pending.get((row['windowId'],parent))
            if not entry or entry[0]['threadId']!=row['threadId']:return None
            if entry[0]['hook'].endswith('.'+kind):return entry[0]
            parent=entry[0]['parentCaptureId']
        return None

    def entry(self,row,facts,frame,pending):
        self.bus_lineage.entry(row,facts,pending,self.ancestor)
        if row['phase']!=1:return
        if row['hook'].endswith('.unfilteredMatrixConsumer'):
            if len(self.consumers)>=LIMIT:raise ValueError('mix contribution consumer bound exceeded')
            mix=self.ancestor(row,pending,'busRouteMix')
            self.consumers[(row['windowId'],row['captureId'])]=dict(mixCaptureId=mix['captureId'] if mix else None,calls=[])
            return
        if not row['hook'].endswith('.busRouteMix'):return
        if len(self.mixes)>=LIMIT:raise ValueError('mix contribution pending bound exceeded')
        task=self.ancestor(row,pending,'busOutputTask')
        candidates={}
        if frame.interval_joins_enabled:
            for (window,_),s in frame.source_intervals.items():
                if window==row['windowId'] and s['threadId']==row['threadId']:candidates[s['sampleCaptureId']]=dict(s)
            bus_key=row['windowId'],row['args'][0]
            for key in frame.bus_rows.get(bus_key,()):
                p=frame.published_rows.get(key)
                if p and p['busKey']==bus_key and p['resetOrdinal']==frame.bus_ordinals.get(bus_key) and bus_key not in frame.bus_resets:
                    s=p['sourceCandidate']
                    if s['threadId']==row['threadId']:candidates[s['sampleCaptureId']]=dict(s,publicationCaptureId=p['publicationCaptureId'],releaseObservedAfterPublication=p['releaseObservedAfterPublication'])
        planes={}
        for s in candidates.values():
            if s['validFrames']!=self.config['selection']['frames']:continue
            planes.setdefault(s['samplePointer'],[]).append(dict(source=s,channel=0,prefix=s.get('prefixFirst16Hex')))
            if s['format']&255==2:
                planes.setdefault(s['samplePointer']+self.config['selection']['frames']*4,[]).append(dict(source=s,channel=1,prefix=s.get('secondPlaneFirst16Hex')))
        self.mixes[(row['windowId'],row['captureId'])]=dict(entry=row,sourceRowCount=facts.get('mixRowCount'),taskCaptureId=task['captureId'] if task else None,planes=planes,calls=[])

    def compare(self,before,row,initial,final,closed):
        kind=row['hook'].rsplit('.',1)[-1]
        item=dict(captureId=row['captureId'],entrySequence=before['sequence'],returnSequence=row['sequence'],kind=kind,
            sourcePointer=before['args'][1],destinationPointer=before['args'][0],sourcePrefix=before['spanHex'][:32],
            beforeDestination=hex_words(words(initial,'destinationWord')) if words(initial,'destinationWord') else None,
            afterDestination=row['spanHex'][:32],coefficientBits=initial.get('coefficientBits'),stepBits=initial.get('stepBits'),sourceCandidate=None)
        def reject(status):item['status']=status;return item
        if row['phase']!=2 or not closed or before.get('observationWindowOpen') is not True:return reject('accumulationNotClosedNormally')
        if before['returnAddress']-before['moduleBase']!=int(self.config['callerReturnRvas'][kind],16):return reject('accumulationCallerNotSelected')
        if initial.get('frames')!=self.config['selection']['frames'] or final.get('frames')!=initial.get('frames'):return reject('accumulationExtentNotSelected')
        coefficient=before['args'][2]&0xffffffff
        step=before['args'][3]&0xffffffff if kind=='matrixAccumulateRamp' else None
        if initial.get('coefficientBits')!=coefficient or final.get('coefficientBits')!=coefficient or step is not None and (initial.get('stepBits')!=step or final.get('stepBits')!=step):return reject('accumulationCoefficientChanged')
        source=words(initial,'sourceWord');dest=words(initial,'destinationWord');after=words(final,'destinationWord')
        if not source or not dest or not after or before['spanBytes']!=16 or row['spanBytes']!=16:return reject('accumulationOperandsIncomplete')
        if before['spanHex']!=hex_words(source) or row['spanHex']!=hex_words(after):return reject('accumulationOperandSpanDiffers')
        if words(final,'sourceWord')!=source:return reject('accumulationSourcePrefixChanged')
        if abs(before['args'][0]-before['args'][1])<self.config['selection']['frames']*4:return reject('accumulationStorageOverlaps')
        if before.get('roundingModeSampled') is not True:return reject('accumulationRoundingNotObserved')
        try:expected=evaluate_accumulation_prefix(source_words=source,destination_words=dest,coefficient=coefficient,step=step,lane_words=self.config['rampLaneWords'],mxcsr=before.get('mxcsr'))
        except UnsupportedArithmetic as error:return reject(str(error))
        item.update(expected=expected,actual=after,nonzeroInitialDestination=any(w&0x7fffffff for w in dest),nonzeroSource=any(w&0x7fffffff for w in source))
        return reject('exactAccumulationPrefix' if expected==after else 'accumulationArithmeticMismatch')

    def completed(self,before,row,initial,final,pending,*,closed):
        old_count=len(self.rows)
        self._completed(before,row,initial,final,pending,closed=closed)
        mix_output=self.rows[-1] if len(self.rows)>old_count and row['hook'].endswith('.busRouteMix') else None
        self.bus_lineage.completed(before,row,initial,final,pending,self.ancestor,closed=closed,mix_output=mix_output)

    def _completed(self,before,row,initial,final,pending,*,closed):
        kind=row['hook'].rsplit('.',1)[-1];key=row['windowId'],row['captureId']
        if kind in KINDS:
            mix=self.ancestor(row,pending,'busRouteMix');consumer=self.ancestor(row,pending,'unfilteredMatrixConsumer')
            saved=self.mixes.get((row['windowId'],mix['captureId'])) if mix else None
            if saved is None or consumer is None or saved['taskCaptureId'] is None:
                self.counts['accumulationNestingNotSelected']+=1;return
            item=self.compare(before,row,initial,final,closed);item['consumerCaptureId']=consumer['captureId']
            cf=pending[(row['windowId'],consumer['captureId'])][1];output=cf.get('outputSamplePointer')
            geometry=consumer['args'][2]==self.config['selection']['frames'] and cf.get('outputFormat')==12546 and cf.get('outputCapacity')==cf.get('outputValidFrames')==self.config['selection']['frames'] and bool(output)
            item['consumerOutputPlane']=next((p for p in (0,1) if geometry and item['destinationPointer']==output+p*self.config['selection']['frames']*4),None)
            item['consumerReturnMatches']=False
            item['upstreamBusCandidate']=self.bus_lineage.match(before,item['sourcePointer'],item['sourcePrefix']) if item['status']=='exactAccumulationPrefix' else None
            scope=self.consumers.get((row['windowId'],consumer['captureId']))
            if scope is not None:scope['calls'].append(item)
            matching=[p for p in saved['planes'].get(item['sourcePointer'],()) if p['prefix']==item['sourcePrefix'] and p['source']['sampleSequence']<before['sequence']]
            if item['status']=='exactAccumulationPrefix' and len(matching)==1:item['sourceCandidate']=matching[0]
            self.counts[item['status']]+=1
            self.counts['exactNonzeroInitialDestination']+=item['status']=='exactAccumulationPrefix' and bool(item.get('nonzeroInitialDestination'))
            if len(saved['calls'])>=LIMIT:raise ValueError('mix contribution call bound exceeded')
            saved['calls'].append(item)
        elif kind=='unfilteredMatrixConsumer':
            scope=self.consumers.pop(key,None)
            if scope is None:raise ValueError('mix contribution consumer return lacks entry')
            calls=[c for c in scope['calls'] if c['consumerOutputPlane']==0]
            geometry=all(initial.get(k) is not None and initial[k]==final.get(k) for k in ('outputDescriptor','outputSamplePointer','outputFormat','outputCapacity','outputValidFrames'))
            first=words(initial,'initialOutputWord')
            joined=bool(calls and first) and row['phase']==2 and closed and before.get('observationWindowOpen') is True and geometry and calls[0]['beforeDestination']==hex_words(first) and row['spanBytes']==16 and calls[-1]['afterDestination']==row['spanHex']
            for c in calls:c['consumerReturnMatches']=joined
            self.counts['consumerReturnedPrefixJoins']+=joined
        elif kind=='busRouteMix':
            mix=self.mixes.pop(key,None)
            if mix is None:raise ValueError('mix contribution return lacks entry')
            selected=[c for c in mix['calls'] if c['destinationPointer']==final.get('busSamplePointer')]
            if not mix['calls']:self.counts['mixWithoutSelectedAccumulation']+=1;return
            normal=row['phase']==2 and closed and before.get('observationWindowOpen') is True and row['returnValue']==before['args'][1]
            continuous=bool(selected) and all(c['status']=='exactAccumulationPrefix' and c['consumerReturnMatches'] for c in selected) and all(a['returnSequence']<b['entrySequence'] and a['afterDestination']==b['beforeDestination'] for a,b in zip(selected,selected[1:]))
            joined=normal and continuous and row['spanBytes']>=16 and selected[-1]['afterDestination']==row['spanHex'][:32] and final.get('busFormat')==12546 and final.get('busCapacity')==final.get('busValidFrames')==self.config['selection']['frames']
            item=dict(windowId=row['windowId'],threadId=row['threadId'],mixCaptureId=row['captureId'],taskCaptureId=mix['taskCaptureId'],sourceRowCount=mix['sourceRowCount'],
                calls=mix['calls'],firstPlaneCaptureIds=[c['captureId'] for c in selected],orderedFirstPlanePrefixes=continuous,finalMixedPrefixMatches=joined,wholeEventToDeviceClaim=False)
            self.counts['orderedMixedPrefixJoins']+=joined
            if len(self.rows)<LIMIT:self.rows.append(item)
            else:self.counts['reportRowsOmitted']+=1

    def publish(self,diagnostics,bus,lineage):
        result=[] if diagnostics else self.rows;counts=Counter(self.counts)
        transports={}
        for t in (lineage or {}).get('localTransport',[]):
            c=t['constructor'];transports.setdefault((c['windowId'],c['threadId'],c['primaryOwner'],c['source'],t['serial']),[]).append(t)
        links={(l['windowId'],l['taskCaptureId'],l['mixCaptureId']):l for l in (bus or {}).get('taskDeviceLinks',())}
        for mix in result:
            mix['taskDeviceLink']=links.get((mix['windowId'],mix['taskCaptureId'],mix['mixCaptureId'])) if mix['finalMixedPrefixMatches'] else None
            first=set(mix['firstPlaneCaptureIds'])
            for call in mix['calls']:
                plane=call['sourceCandidate']
                if plane:
                    s=plane['source'];key=(mix['windowId'],mix['threadId'],s['primaryOwner'],s['storedSource'],s['serial'])
                    ts=[t for t in transports.get(key,()) if t['constructor']['sequence']<s['sampleSequence'] and t['selector']['allocation']==s['allocation']]
                    if len(ts)==1:
                        call['sourceTransportCandidate']=ts[0]
                        if len(ts[0]['managedCandidates'])==1:
                            call['managedEventCandidate']=ts[0]['managedCandidates'][0];counts['uniqueManagedEventCandidates']+=1
                        if ts[0]['selection']=='singleDescriptorWideSetterInput' and ts[0]['selector'].get('descriptorPath'):
                            call['observedExternalPathCandidate']=ts[0]['selector']['descriptorPath'];counts['observedExternalPathCandidates']+=1
                    counts['sourcePrefixCandidates']+=1
                    counts['sourceCandidatesInDeviceLinkedFirstPlane']+=bool(mix['taskDeviceLink'] and call['captureId'] in first)
        return dict(schema='endfield.audio-mix-contributions-witness.v2',rows=result,counts=dict(counts),diagnostics=list(diagnostics),openMixes=len(self.mixes),openConsumers=len(self.consumers),
            busLineage=self.bus_lineage.publish(result,diagnostics),wholeEventToDeviceClaim=False,
            evidenceBoundary='Exact four-lane AVX additions include the observed initial destination and constant/ramped coefficient. Ordered snapshot continuity and final mixed-prefix equality join saved additions to an admitted task/device path. Source candidates require observed source-plane pointer/content and current sample/publication records; managed candidates also require owner/source/serial/allocation and constructor-before-sample ordering. No allocation generation, every cohort member, complete-buffer coverage or individual contribution after nonlinear processing is inferred.')
