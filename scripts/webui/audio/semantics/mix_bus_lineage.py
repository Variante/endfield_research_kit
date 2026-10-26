"""Observed bus PCM handoffs within reset/write intervals, not lifetimes."""
from __future__ import annotations
from collections import Counter
from scripts.webui.audio.semantics.bus_processing_capture import storage,same_storage

LIMIT=100000


class MixBusLineage:
    def __init__(self,return_sites):
        self.return_sites=return_sites;self.tasks={};self.nodes={};self.active={};self.by_sample={};self.reset_sequence={};self.write_sequence={};self.sample_write_sequence={};self.sample_writers={};self.counts=Counter()

    def remove(self,key):
        node=self.active.pop(key,None)
        if node:
            sample_key=node['windowId'],node['threadId'],node['storage']['sample']
            candidates=self.by_sample.get(sample_key,{})
            candidates.pop(key,None)
            if not candidates:self.by_sample.pop(sample_key,None)

    def entry(self,row,facts,pending,ancestor):
        if row['phase']!=1:return
        kind=row['hook'].rsplit('.',1)[-1];key=row['windowId'],row['captureId']
        if kind=='busOutputTask':
            if len(self.tasks)>=LIMIT:raise ValueError('bus contribution task bound exceeded')
            self.tasks[key]=dict(entry=row,mixes=[],processing=[],closed=True)
        elif kind in ('busRouteMix','busPostMixProcessing','busFrameReset'):
            bus_key=row['windowId'],row['threadId'],row['args'][0]
            self.remove(bus_key)
            if bus_key not in self.write_sequence and len(self.write_sequence)>=LIMIT:raise ValueError('bus contribution writer bound exceeded')
            self.write_sequence[bus_key]=row['sequence']
            if kind=='busFrameReset':self.reset_sequence[bus_key]=row['sequence']
        if kind in ('busPostMixProcessing','unfilteredMatrixConsumer','sourceFrameGain','busEffectConsume','collectionEqExecute','biquadProcessing','contextSourceSampleBuffer'):
            pointer=facts.get('outputPlane' if kind=='biquadProcessing' else 'outputSamplePointer' if kind=='unfilteredMatrixConsumer' else 'samplePointer')
            if pointer:
                sample_key=row['windowId'],row['threadId'],pointer
                if sample_key not in self.sample_write_sequence and len(self.sample_write_sequence)>=LIMIT:raise ValueError('bus contribution sample writer bound exceeded')
                self.sample_write_sequence[sample_key]=row['sequence']
                self.sample_writers[sample_key]=dict(sequence=row['sequence'],captureId=row['captureId'],kind=kind)
            for bus_key in tuple(self.by_sample.get((row['windowId'],row['threadId'],pointer),{})):self.remove(bus_key)

    def match(self,row,source_pointer,prefix):
        candidates=[n for n in self.by_sample.get((row['windowId'],row['threadId'],source_pointer),{}).values()
            if n['taskReturnSequence']<row['sequence'] and n['processedPrefix']==prefix and n['storage']['capacity']==n['storage']['valid']==512]
        if len(candidates)!=1:return None
        n=candidates[0]
        return dict(taskCaptureId=n['taskCaptureId'],mixCaptureId=n['mixCaptureId'],processingCaptureId=n['processingCaptureId'],
            bus=n['bus'],descriptor=n['storage']['descriptor'],samplePointer=source_pointer,resetEntrySequence=n['resetEntrySequence'],
            taskReturnSequence=n['taskReturnSequence'],consumerEntrySequence=row['sequence'],prefix=prefix,
            evidenceBoundary='conditionalObservedBusWriteResetInterval')

    def completed(self,before,row,initial,final,pending,ancestor,*,closed,mix_output=None):
        kind=row['hook'].rsplit('.',1)[-1];key=row['windowId'],row['captureId']
        if kind=='busOutputTask':
            task=self.tasks.pop(key,None)
            if task is None:raise ValueError('bus contribution task return lacks entry')
            normal=row['phase']==2 and closed and task['closed'] and before.get('observationWindowOpen') is True and row['returnValue']==before['args'][1]
            if not normal:self.counts['taskNotClosedNormally']+=1;return
            processes=[p for p in task['processing'] if p['parentCaptureId']==row['captureId'] and p['callerRva']==int(self.return_sites['taskProcessingCallReturnRva'],16)]
            if len(processes)!=1:self.counts['processingBranchNotSelected']+=1;return
            p=processes[0];mixes=[m for m in task['mixes'] if m['bus']==p['bus'] and m['returnSequence']<p['entrySequence']]
            if len(mixes)!=1:self.counts['mixProcessingOrderNotSelected']+=1;return
            m=mixes[0];s=p['final']
            if not (same_storage(m['storage'],p['initial']) and same_storage(p['initial'],s) and s.get('owner') and s['owner']==p['initial'].get('owner') and
                    s.get('format')==12546 and s.get('capacity')==s.get('valid')==512 and m['prefix'] and m['prefix']==p['beforePrefix'] and p['afterPrefix']):
                self.counts['processingStorageOrContentNotSelected']+=1;return
            bus_key=row['windowId'],row['threadId'],p['bus']
            # A nested reset/new writer invalidates the staged output too.
            reset=self.reset_sequence.get(bus_key,0)
            if reset>m['entrySequence'] or self.write_sequence.get(bus_key)!=p['entrySequence']:
                self.counts['resetOrWriterDuringTask']+=1;return
            sample_key=row['windowId'],row['threadId'],s['sample']
            later_writer=self.sample_writers.get(sample_key) if self.sample_write_sequence.get(sample_key,0)>p['returnSequence'] else None
            node=dict(windowId=row['windowId'],threadId=row['threadId'],taskCaptureId=row['captureId'],bus=p['bus'],storage=s,
                mixCaptureId=m['captureId'],processingCaptureId=p['captureId'],taskReturnSequence=row['sequence'],resetEntrySequence=reset,
                mixedPrefix=m['prefix'],processedPrefix=p['afterPrefix'],processingPrefixUnchanged=m['prefix']==p['afterPrefix'],
                numericalMixAdmitted=bool(m['numerical']),eligibleForLaterBusRead=later_writer is None,laterObservedWriter=later_writer,wholeEventToDeviceClaim=False)
            if len(self.nodes)>=LIMIT:self.counts['reportRowsOmitted']+=1;return
            self.nodes[key]=node;self.remove(bus_key)
            if later_writer is None:
                self.active[bus_key]=node;self.by_sample.setdefault(sample_key,{})[bus_key]=node
            else:self.counts['stagedPrefixHasLaterWriter']+=1
            self.counts['completedMixProcessingNodes']+=1
        elif kind in ('busRouteMix','busPostMixProcessing'):
            root=ancestor(row,pending,'busOutputTask')
            task=self.tasks.get((row['windowId'],root['captureId'])) if root else None
            if task is None:return
            task['closed'] &= row['phase']==2 and closed and before.get('observationWindowOpen') is True
            if kind=='busRouteMix':
                task['closed'] &= row['returnValue']==before['args'][1]
                task['mixes'].append(dict(captureId=row['captureId'],bus=before['args'][0],storage=storage(final,mix=True),
                    entrySequence=before['sequence'],returnSequence=row['sequence'],prefix=row['spanHex'][:32] if row['spanBytes']>=16 else None,
                    numerical=bool(mix_output and mix_output['finalMixedPrefixMatches'])))
            else:
                task['processing'].append(dict(captureId=row['captureId'],bus=before['args'][0],initial=storage(initial),final=storage(final),
                    parentCaptureId=before['parentCaptureId'],callerRva=before['returnAddress']-before['moduleBase'],entrySequence=before['sequence'],returnSequence=row['sequence'],
                    beforePrefix=before['spanHex'][:32] if before['spanBytes']>=16 else None,afterPrefix=row['spanHex'][:32] if row['spanBytes']>=16 else None))

    def publish(self,mixes,diagnostics):
        if diagnostics:return dict(schema='endfield.audio-mix-bus-lineage.v1',status='captureDiagnosticsPresent',nodes=[],edges=[],eventDeviceCandidates=[],counts=dict(self.counts),wholeEventToDeviceClaim=False)
        by_mix={(m['windowId'],m['mixCaptureId']):m for m in mixes};nodes=[dict(n) for n in self.nodes.values()];edges=[];leaves={};parents={};counts=Counter(self.counts)
        for node in nodes:
            m=by_mix.get((node['windowId'],node['mixCaptureId']))
            if not m or not node['numericalMixAdmitted']:continue
            node['taskDeviceLink']=m.get('taskDeviceLink');first=set(m['firstPlaneCaptureIds'])
            # A staged prefix with a later writer cannot supply a future bus
            # read. A separately admitted processing/master/device invocation
            # can still use that earlier snapshot as its terminal node.
            if not node['eligibleForLaterBusRead'] and not node['taskDeviceLink']:continue
            for call in m['calls']:
                if call['captureId'] not in first or call['status']!='exactAccumulationPrefix':continue
                parent_key=node['windowId'],node['taskCaptureId'];up=call.get('upstreamBusCandidate')
                if up:
                    child_key=node['windowId'],up['taskCaptureId'];child=self.nodes.get(child_key)
                    if child and child['numericalMixAdmitted']:
                        edge=dict(windowId=node['windowId'],producerTaskCaptureId=up['taskCaptureId'],consumerTaskCaptureId=node['taskCaptureId'],consumerCallCaptureId=call['captureId'],handoff=up)
                        edges.append(edge);parents.setdefault(parent_key,[]).append(edge)
                if call.get('managedEventCandidate'):
                    leaves.setdefault(parent_key,[]).append(dict(sourceTaskCaptureId=node['taskCaptureId'],sourceMixCaptureId=node['mixCaptureId'],sourceCallCaptureId=call['captureId'],
                        sourceCandidate=call['sourceCandidate'],managedEventCandidate=call['managedEventCandidate'],externalPathCandidate=call.get('observedExternalPathCandidate'),
                        sourcePrefixNonzero=bool(call.get('nonzeroSource')),additionChangedPrefix=call.get('beforeDestination')!=call.get('afterDestination')))
        candidates=[]
        for terminal in nodes:
            if not terminal.get('taskDeviceLink'):continue
            stack=[((terminal['windowId'],terminal['taskCaptureId']),[],set())]
            while stack:
                key,path,seen=stack.pop()
                if key in seen or len(path)>32:counts['pathCycleOrDepthLimit']+=1;continue
                for leaf in leaves.get(key,()):
                    if len(candidates)>=10000:counts['candidatePathsOmitted']+=1;continue
                    path_nodes=[self.nodes[key]]+[self.nodes[(e['windowId'],e['consumerTaskCaptureId'])] for e in reversed(path)]
                    candidates.append(dict(windowId=terminal['windowId'],source=leaf,busHops=list(reversed(path)),
                        deviceLink=terminal['taskDeviceLink'],intermediateProcessingPrefixesUnchanged=all(n['processingPrefixUnchanged'] for n in path_nodes[:-1]),
                        wholeEventToDeviceClaim=False,evidenceBoundary='conditionalSourceBusDevicePrefixPath'))
                for edge in parents.get(key,()):stack.append(((edge['windowId'],edge['producerTaskCaptureId']),path+[edge],seen|{key}))
        counts.update(busToBusPrefixEdges=len(edges),eventSourceDeviceCandidatePaths=len(candidates),
            nonzeroEventSourceDeviceCandidatePaths=sum(p['source']['sourcePrefixNonzero'] and p['source']['additionChangedPrefix'] for p in candidates))
        return dict(schema='endfield.audio-mix-bus-lineage.v1',status='conditionalObservedBusPrefixPaths',nodes=nodes,edges=edges,eventDeviceCandidates=candidates,counts=dict(counts),wholeEventToDeviceClaim=False,
            evidenceBoundary='Completed same-thread tasks connect mixed prefixes through observed post-processing into later actual accumulator source pointers/content before an observed reset or new writer. Every node requires stable descriptor/sample/owner/format/extents and exact mix-to-processing content. Edges retain completed task ordering and observed reset intervals. Event paths use the admitted first-plane additions and existing owner/source/serial/allocation candidates. Unobserved writers, cross-thread/true allocation generations, second planes, isolated Event arithmetic after nonlinear DSP and full buffers remain unresolved.')
