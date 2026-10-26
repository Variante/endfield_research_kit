"""Collect local Action transport and conditional owner continuity in one scan."""
from __future__ import annotations

from collections import Counter
import hashlib
import math
import struct

REPORT_ROW_LIMIT=100000


class PlaybackLineage:
    def __init__(self, transport, stored_identity=None, hooks=None):
        self.transport=transport
        self.actions={};self.latest_owners={};self.owner_cohorts=[]
        self.counts=Counter();self.routes={};self.buses={};self.examples={}
        self.stored_identity=stored_identity or {}
        self.hooks=hooks or {}
        self.current_owner_pcm={}
        self.mix_row_observations=[]

    def validate_source_reads(self,row,facts,fields):
        spans=[field for field in fields if field['kind']=='bytes']
        if row.get('spanBytes') and spans and not any(facts.get(field['name']) is not None for field in spans):
            raise ValueError('source PCM span lacks a successful declared read')
        for i,field in enumerate(fields):
            value=facts.get(field['name'])
            if value is None or field['kind'] in ('argument','argumentU32'):continue
            chain=field.get('pointerOffsets',[])
            if not chain:base=row['args'][field['argIndex']]
            elif field['name'].startswith('owner'):base=facts.get('primaryOwner')
            elif field['name']=='object':base=facts.get('embeddedOwner')
            elif field['kind']=='bytes' or field['name'].startswith('secondPlaneWord'):base=facts.get('samplePointer')
            else:raise ValueError('unresolved source read indirection')
            if type(base) is not int or not 0<base+field['offset']<0x800000000000 or row['addresses'][i]!=base+field['offset']:
                raise ValueError('source read address disagrees with recorded storage: '+field['name'])
            if field['kind']=='bytes' and row['spanBytes'] and row['spanAddress']!=base+field['offset']:
                raise ValueError('source PCM span address differs from sampled source storage')

    def action_parent(self,row,pending):
        parent=row['parentCaptureId'];seen=set()
        while parent and parent not in seen and len(seen)<64:
            seen.add(parent);entry=pending.get((row['windowId'],parent))
            if not entry or entry[0]['threadId']!=row['threadId']: return None
            before,_=entry
            if before['hook'].endswith('normalActionExecute'):
                return self.actions.get((row['windowId'],parent))
            parent=before['parentCaptureId']
        return None

    def entry(self,row,facts,pending):
        name=row['hook']
        if row['phase']==1 and name.endswith('normalActionExecute'):
            key=(row['windowId'],row['captureId'])
            if len(self.actions)>=100000: raise ValueError('Action observation bound exceeded')
            self.actions[key]=dict(captureId=row['captureId'],threadId=row['threadId'],windowId=row['windowId'],
                serial=facts.get('queuedPlaybackSerial'),allocation=facts.get('retainedExternalAllocation'),
                selectors=[],setters=[],constructors=[],completed=False)
            return
        if row['phase']==4 or (row['phase']==1 and name.endswith('busRouteMix')):
            action=self.action_parent(row,pending)
            if name.endswith('anonymousSourceSelector') and action:
                text=None
                if facts.get('descriptor0WideText') is not None:
                    text=b''.join(n.to_bytes(2,'little') for n in row['textUnits']).decode('utf-16-le')
                action['selectors'].append(dict(captureId=row['captureId'],blob=row['args'][2],source=row['args'][1],
                    serial=facts.get('playbackSerialWord'),allocation=facts.get('externalDescriptorAllocationPointer'),
                    lookup=facts.get('originalSourceLookupWord'),matchWord=facts.get('originalSourceStoredWord4'),
                    argument=facts.get('originalSourceArgumentWord24'),descriptorCount=facts.get('externalDescriptorCount'),
                    descriptorMatch=facts.get('descriptor0MatchWord'),descriptorArgument=facts.get('descriptor0ArgumentWord'),
                    descriptorPathPointer=facts.get('descriptor0WideTextPointer'),descriptorPath=text))
            elif name.endswith('anonymousWideTextSourceSetter') and action:
                action['setters'].append(dict(captureId=row['captureId'],source=row['args'][0],
                    lookup=row['args'][1],argument=row['args'][2],pathPointer=row['args'][3]))
            elif name.endswith('anonymousPrimaryOwnerConstructor'):
                owner=row['args'][self.transport['constructor']['ownerArgument']['index']]
                source=row['args'][self.transport['constructor']['sourceArgument']['index']]
                if len(self.owner_cohorts)>=100000: raise ValueError('owner construction bound exceeded')
                generation=dict(primaryOwner=owner,source=source,blob=row['args'][self.transport['constructor']['parameterArgumentIndex']],constructorCaptureId=row['captureId'],
                    threadId=row['threadId'],windowId=row['windowId'],sequence=row['sequence'],
                    actionCaptureId=action['captureId'] if action else None,serial=action['serial'] if action else None,
                    pcmObservations=0,nonzeroFinitePrefixes=0,sameThreadPcm=0)
                self.latest_owners[owner]=generation;self.owner_cohorts.append(generation)
                if action: action['constructors'].append(generation)
            elif name.endswith('routeMatrixPreparation'):
                route=row['args'][0]
                if len(self.routes)>=100000 and route not in self.routes: raise ValueError('route address bound exceeded')
                self.routes[route]=dict(route=route,sourceAddress=facts.get('routeSource'),bus=facts.get('routeBus'),
                    rowsAddress=facts.get('routeRows'),captureId=row['captureId'])
            elif name.endswith('busRouteMix'):
                for i,field in enumerate(self.hooks.get(name,{}).get('memory',[])):
                    if field['kind'] in ('argument','argumentU32') or field.get('pointerOffsets') or facts.get(field['name']) is None:continue
                    argument=row['args'][field['argIndex']] if field['argIndex']<4 else row['extraArgument']
                    if row['addresses'][i]!=argument+field['offset']:
                        raise ValueError('mixer direct read address disagrees with its observed argument')
                count=facts.get('mixRowCount')
                span=bytes.fromhex(row['spanHex']) if facts.get('mixRowPointerPrefix') is not None else b''
                pointers=list(struct.unpack('<'+str(len(span)//8)+'Q',span)) if span and len(span)%8==0 else []
                if len(self.buses)>=100000 and row['args'][0] not in self.buses: raise ValueError('bus address bound exceeded')
                self.buses[row['args'][0]]=dict(bus=row['args'][0],mixRowCount=count,mixRowPointerPrefix=pointers,
                    prefixComplete=count is not None and len(pointers)==count,captureId=row['captureId'])
                first=facts.get('firstMixRow')
                if first:
                    if not pointers or pointers[0]!=first:
                        raise ValueError('first mixer row disagrees with the actual row-array prefix')
                    fields=self.hooks[name]['memory']
                    descriptor=facts.get('firstRowDescriptor')
                    for i,field in enumerate(fields):
                        if not field['name'].startswith('first') or facts.get(field['name']) is None:continue
                        chain=field.get('pointerOffsets',[])
                        # The second dereference belongs to the declared row
                        # member. Matrix coefficients do not use the descriptor.
                        if not chain:base=row['args'][3]
                        elif len(chain)==1:base=first
                        else:
                            member=next((f['name'] for f in fields if f.get('pointerOffsets')==chain[:1] and f['offset']==chain[1] and f['kind']=='pointer'),None)
                            base=facts.get(member)
                            if base is None:raise ValueError('mixer row indirection lacks its recorded pointer')
                        if row['addresses'][i]!=base+field['offset']:
                            raise ValueError('mixer row read address disagrees with its recorded row/descriptor')
                    self.counts['observedMixRows']+=1
                    if len(self.mix_row_observations)>=REPORT_ROW_LIMIT:
                        self.counts['reportRowsOmitted']+=1;return
                    self.mix_row_observations.append(dict(windowId=row['windowId'],captureId=row['captureId'],threadId=row['threadId'],sequence=row['sequence'],
                        bus=row['args'][0],rowArray=row['args'][3],mixRowCount=count,rowPointerPrefix=pointers,
                        firstRow={k:v for k,v in facts.items() if k.startswith('first')}))

    def completed(self,before,row,facts,pending):
        name=row['hook']
        if name.endswith('normalActionExecute'):
            action=self.actions.get((row['windowId'],row['captureId']))
            if action:
                action['completed']=row['phase']==2;action['result']=row['returnValue']
            return
        if row['phase']!=2:return
        if name.endswith('contextSourceSampleBuffer'):
            self.validate_source_reads(row,facts,self.hooks.get(name,{}).get('resultMemory',[]))
            owner=facts.get('primaryOwner');generation=self.latest_owners.get(owner)
            available={k for k in self.stored_identity if facts.get(k) is not None}
            if owner and available:
                fields=self.hooks[name]['resultMemory']
                for key,declaration in self.stored_identity.items():
                    if key not in available:continue
                    index=next(i for i,f in enumerate(fields) if f['name']==key)
                    if row['addresses'][index]!=owner+declaration['offset']:
                        raise ValueError('current owner identity read address disagrees with sampled primary owner')
                span=bytes.fromhex(row['spanHex'])
                floats=struct.unpack('<'+str(len(span)//4)+'f',span) if span and len(span)%4==0 else ()
                item=dict(captureId=row['captureId'],windowId=row['windowId'],threadId=row['threadId'],
                    sequence=row.get('sequence'),identityStatus='completeStoredOwnerIdentity' if len(available)==len(self.stored_identity) else 'partialStoredOwnerIdentity',
                    context=before['args'][0],descriptor=before['args'][1],primaryOwner=owner,
                    serial=facts.get('ownerPlaybackSerial'),externalAllocation=facts.get('ownerExternalAllocation'),storedSource=facts.get('ownerStoredSource'),
                    samplePointer=facts.get('samplePointer'),format=facts.get('channelConfiguration'),validFrames=facts.get('validFrames'),
                    prefixBytes=len(span),prefixSha256=hashlib.sha256(span).hexdigest(),
                    finiteNonzeroPrefix=bool(floats and all(math.isfinite(x) for x in floats) and any(floats)))
                right=[facts.get(f['name']) for f in fields if f['name'].startswith('secondPlaneWord')]
                if any(value is not None for value in right):
                    for i,field in enumerate(fields):
                        if field['name'].startswith('secondPlaneWord') and facts.get(field['name']) is not None and row['addresses'][i]!=facts['samplePointer']+field['offset']:
                            raise ValueError('second plane read address differs from sampled source storage')
                    item['secondPlanePrefixWords']=right
                key=(item['windowId'],item['primaryOwner'],item['serial'],item['externalAllocation'],item['storedSource'],item['identityStatus'])
                if key not in self.current_owner_pcm:
                    if len(self.current_owner_pcm)>=100000:raise ValueError('current owner identity bound exceeded')
                    self.current_owner_pcm[key]=dict(observations=0,nonzeroObservations=0,first=[],last=None,firstNonzero=None)
                cohort=self.current_owner_pcm[key];cohort['observations']+=1;cohort['nonzeroObservations']+=item['finiteNonzeroPrefix']
                if len(cohort['first'])<2:cohort['first'].append(item)
                if item['finiteNonzeroPrefix'] and cohort['firstNonzero'] is None:cohort['firstNonzero']=item
                cohort['last']=item
            if generation and generation['windowId']==row['windowId'] and generation['sequence']<before['sequence']:
                if facts.get('embeddedOwner')!=owner+self.transport['consumerOwnerOffset']:
                    self.counts['ownerAdjustmentDisagrees']+=1;return
                generation['pcmObservations']+=1;generation['sameThreadPcm']+=generation['threadId']==row['threadId']
                span=bytes.fromhex(row['spanHex'])
                floats=struct.unpack('<'+str(len(span)//4)+'f',span) if span and len(span)%4==0 else ()
                nonzero=bool(floats and all(math.isfinite(x) for x in floats) and any(floats))
                generation['nonzeroFinitePrefixes']+=nonzero
                generation.setdefault('firstPcm',dict(captureId=row['captureId'],context=before['args'][0],
                    sourceWrapper=facts.get('sourceWrapper'),object=facts.get('object'),
                    format=facts.get('channelConfiguration'),validFrames=facts.get('validFrames'),routeHead=facts.get('routeHead')))
                if nonzero:
                    generation.setdefault('firstNonzeroPcm',dict(captureId=row['captureId'],context=before['args'][0],
                        format=facts.get('channelConfiguration'),validFrames=facts.get('validFrames'),samplePrefixHex=row['spanHex']))
                if nonzero and 'ownerPcm' not in self.examples:
                    self.examples['ownerPcm']=dict(constructor=generation.copy(),enter=before,result=row)
        elif name.endswith('ownerRoutingConsumer'):
            self.counts['completedRoutingCalls']+=1
        elif name.endswith('sinkSubmit'):
            self.counts['completedSinkCalls']+=1

    def publish(self,managed):
        selected=[]
        for action in self.actions.values():
            if not action['completed']:continue
            for selector in action['selectors']:
                if selector['serial'] is None or selector['serial']!=action['serial'] or selector['allocation']!=action['allocation']:
                    self.counts['actionSelectorTransportDisagrees']+=1;continue
                self.counts['matchingActionSelectorTransport']+=1
                for owner in action['constructors']:
                    if owner['blob']!=selector['blob']:continue
                    unchanged=owner['source']==selector['source']
                    setter=next((s for s in action['setters'] if s['source']==owner['source'] and s['pathPointer']==selector['descriptorPathPointer'] and s['lookup']==selector['descriptorMatch']),None)
                    if not unchanged and not (selector['descriptorCount']==1 and setter):continue
                    self.counts['matchingSelectorConstructorInputs']+=1
                    candidates=managed.get(action['serial'],[])
                    row=dict(serial=action['serial'],managedCandidates=candidates,actionCaptureId=action['captureId'],
                        actionResult=action['result'],selector=selector,constructor=owner,
                        selection='unchangedSourceInput' if unchanged else 'singleDescriptorWideSetterInput')
                    selected.append(row)
                    if owner['nonzeroFinitePrefixes'] and 'eventSourceOwnerPcm' not in self.examples:
                        self.examples['eventSourceOwnerPcm']=row
        retained=[];aggregates=[];totals=Counter()
        for cohort in self.current_owner_pcm.values():
            last=cohort['last'];candidates=managed.get(last['serial'],[])
            totals['observations']+=cohort['observations'];totals['finiteNonzeroObservations']+=cohort['nonzeroObservations']
            totals['uniqueManagedCandidateObservations']+=cohort['observations'] if len(candidates)==1 else 0
            totals['completeIdentityObservations']+=cohort['observations'] if last['identityStatus']=='completeStoredOwnerIdentity' else 0
            aggregates.append(dict(windowId=last['windowId'],primaryOwner=last['primaryOwner'],serial=last['serial'],
                externalAllocation=last['externalAllocation'],storedSource=last['storedSource'],identityStatus=last['identityStatus'],
                observations=cohort['observations'],finiteNonzeroObservations=cohort['nonzeroObservations'],managedCandidates=candidates))
            seen=set()
            for item in cohort['first']+[cohort['firstNonzero'],last]:
                if item is not None and item['captureId'] not in seen:
                    seen.add(item['captureId']);retained.append(dict(item,managedCandidates=candidates))
        return dict(localTransport=selected,ownerConstructionCohorts=self.owner_cohorts,
            currentStoredOwnerPcm=retained,currentStoredOwnerPcmAggregates=aggregates,currentStoredOwnerPcmTotals=dict(totals),
            currentStoredOwnerPcmRetention='First two, first finite nonzero and last observations per exact window/owner/serial/allocation/source/identity-status tuple; every read is checked and counted. Retained examples are not every buffer or a lifetime generation.',
            mixRowObservations=self.mix_row_observations,
            counters=dict(self.counts),routes=list(self.routes.values()),buses=list(self.buses.values()),examples=self.examples,
            evidenceBoundary=dict(direct='Completed Action calls contain selector serial/allocation reads and constructor inputs with matching playback-blob identity under same-thread recorded nesting.',
                conditional='Later PCM reads retain the most recently observed constructed primary address and the checked embedded-owner adjustment. A mixer recipe additionally reads the current owner serial/allocation/source storage at addresses agreeing with that sampled primary owner; these remain non-atomic reads and serial candidates without queue generations. External setter inputs describe the chosen descriptor path, not backing-file reads. Historical RDX busRouteMix bytes are excluded from mix-row interpretation.',
                unresolved='Asynchronous allocation lifetime, uncaptured constructor families, source/owner releases, complete mixer frame topology, actual stream selection and device acceptance.'))
