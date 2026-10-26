"""Same-task post-mix transitions; no pointer-only Event or lifetime joins."""
from __future__ import annotations
from collections import Counter
from scripts.webui.audio.semantics.master_gain_witness import compare_master_prefix
from scripts.webui.audio.semantics import biquad_capture

REPORT_ROW_LIMIT=100000


def storage(facts, *, master=False, mix=False):
    names = ('busInputs','firstInputSamplePointer','firstInputOwner','firstInputFormat','firstInputCapacity','firstInputValidFrames') if master else (
        'busFirstDescriptor','busSamplePointer','busFormat','busCapacity','busValidFrames') if mix else (
        'busInputs','samplePointer','owner','format','capacity','validFrames')
    return {k:facts.get(n) for k,n in zip(('descriptor','sample','owner','format','capacity','valid'),names)} if not mix else dict(
        descriptor=facts.get('busFirstDescriptor'),sample=facts.get('busSamplePointer'),format=facts.get('busFormat'),capacity=facts.get('busCapacity'),valid=facts.get('busValidFrames'))


def same_storage(a,b):
    return all(a.get(k) is not None and a[k]==b.get(k) for k in ('descriptor','sample','format','capacity','valid'))


def selected(s, selection):
    return all(s.get(k)==selection[v] for k,v in [('format','format'),('capacity','capacity'),('valid','validFrames')]) and bool(s.get('descriptor')) and bool(s.get('sample'))


def link_task_device(bus, handoff):
    """Only the already admitted master invocation can carry a task to device."""
    if bus.get('status')!='conditionalTaskPrefixes':return []
    tasks={(r['windowId'],r['masterCaptureId']):r for r in bus['rows'] if r['status']=='sameTaskMixProcessingMasterPrefixes'}
    result=[]
    for link in handoff.get('masterConversionDeviceLinks',[]):
        task=tasks.get((link['windowId'],link['masterCaptureId']))
        if task and task['threadId']==link['threadId'] and link['finiteNonzeroPrefix']:
            result.append(dict(windowId=link['windowId'],taskCaptureId=task['taskCaptureId'],mixCaptureId=task['mixCaptureId'],
                processingCaptureId=task['processingCaptureId'],masterCaptureId=link['masterCaptureId'],sinkCaptureId=link['sinkCaptureId'],
                getCaptureId=link['getCaptureId'],releaseCaptureId=link['releaseCaptureId'],comparedDevicePrefixBytes=link['comparedPrefixBytes'],wholeEventToDeviceClaim=False))
    return result


class BusProcessingCapture:
    def __init__(self, selection, return_sites, collection_effect=None, effect_classes=(), biquad=None):
        self.selection=selection;self.return_sites=return_sites
        self.collection_effect=collection_effect or {}
        self.effect_classes=effect_classes
        self.biquad=biquad
        self.tasks={};self.rows=[];self.counts=Counter()

    def root(self,row,pending):
        parent=row['parentCaptureId'];seen=set()
        while parent and parent not in seen and len(seen)<64:
            seen.add(parent);entry=pending.get((row['windowId'],parent))
            if not entry or entry[0]['threadId']!=row['threadId']:return None
            if entry[0]['hook'].endswith('.busOutputTask'):return (row['windowId'],parent)
            parent=entry[0]['parentCaptureId']
        return None

    def entry(self,row):
        if row['phase']==1 and row['hook'].endswith('.busOutputTask'):
            if len(self.tasks)>=100000:raise ValueError('bus task bound exceeded')
            key=row['windowId'],row['captureId']
            if key in self.tasks:raise ValueError('duplicate bus output task')
            self.tasks[key]=dict(entry=row,mixes=[],processing=[],effects=[],gains=[],masters=[],filters=[],eq=[],closed=True)

    def completed(self,before,row,initial,final,pending,*,closed):
        name=row['hook'];key=(row['windowId'],row['captureId'])
        if name.endswith('.busOutputTask'):
            task=self.tasks.pop(key,None)
            if task is None:raise ValueError('bus task return lacks entry')
            result=self.evaluate(task,row,closed)
            self.counts[result['status']]+=1
            self.counts['processingChangedPrefixes']+=bool(result.get('processingChangedPrefix'))
            # Most tasks feed another bus and never invoke master output. Count
            # them without storing an empty row for every bus in every frame.
            if result['status']!='taskBranchNotSelected':
                if len(self.rows)<REPORT_ROW_LIMIT:self.rows.append(result)
                else:self.counts['reportRowsOmitted']+=1
            return
        root=self.root(row,pending)
        if root is None:return
        task=self.tasks[root];task['closed'] &= closed and row['phase']==2
        item=dict(captureId=row['captureId'],parentCaptureId=before['parentCaptureId'],bus=before['args'][0],
            entrySequence=before['sequence'],returnSequence=row['sequence'],callerRva=before['returnAddress']-before['moduleBase'],
            beforePrefix=before['spanHex'][:32] if before['spanBytes']>=16 else None,
            afterPrefix=row['spanHex'][:32] if row['spanBytes']>=16 else None)
        if name.endswith('.busRouteMix'):
            item['storage']=storage(final,mix=True);task['mixes'].append(item)
        elif name.endswith('.busPostMixProcessing'):
            item.update(initial=storage(initial),final=storage(final),inputCount=initial.get('busInputCount'))
            task['processing'].append(item)
        elif name.endswith('.masterBusOutput'):
            item.update(initial=storage(initial,master=True));task['masters'].append(item)
        elif name.endswith('.busEffectConsume'):
            item.update(bus=before['args'][3],initial=storage(initial),final=storage(final),
                selectedDescriptor=initial.get('selectedDescriptor'),selectedCount=initial.get('selectedCount'),
                inputCollection=initial.get('inputCollection'),
                objectCount=initial.get('objectCount'),multiObjectMode=initial.get('multiObjectMode'),inPlaceMode=initial.get('inPlaceMode'),
                finalObjectCount=final.get('objectCount'),
                skipGainBake=initial.get('skipGainBake'),previousControl=initial.get('previousControl'),currentControl=initial.get('currentControl'),
                effectObject=initial.get('firstEffectObject'),executeTarget=initial.get('firstEffectExecuteTarget'),
                executeRva=initial['firstEffectExecuteTarget']-before['moduleBase'] if initial.get('firstEffectExecuteTarget') else None,
                vtableRva=initial['firstEffectVtable']-before['moduleBase'] if initial.get('firstEffectVtable') else None,
                executeTargetStable=bool(initial.get('firstEffectExecuteTarget')) and all(initial.get(k)==final.get(k) for k in ('firstEffectObject','firstEffectVtable','firstEffectExecuteTarget')),
                finalPreviousGainBits=final.get('previousGainBits'),finalTargetGainBits=final.get('targetGainBits'))
            task['effects'].append(item)
        elif name.endswith('.sourceFrameGain'):
            s=storage(initial);s['descriptor']=before['args'][0]
            z=storage(final);z['descriptor']=before['args'][0]
            item.update(initial=s,final=z,previousGainBits=initial.get('incomingPreviousGainBits'),targetGainBits=initial.get('incomingTargetGainBits'))
            status='gainPathNotSelected'
            if (selected(s,self.selection) and same_storage(s,z) and s.get('owner') and s['owner']==z.get('owner') and
                all(initial.get(k)==final.get(k) for k in ('previousGainBits','targetGainBits')) and before.get('roundingModeSampled') is True and
                initial.get('includeLfe')==1 and initial.get('incomingPreviousGainBits')==initial.get('previousGainBits') and
                initial.get('incomingTargetGainBits')==initial.get('targetGainBits') and item['beforePrefix'] and item['afterPrefix']):
                result=compare_master_prefix(item['beforePrefix'],item['afterPrefix'],previous_gain_bits=item['previousGainBits'],target_gain_bits=item['targetGainBits'],mxcsr=before['mxcsr'])
                # Shared arithmetic, but these operands belong to the observed
                # frame-gain call before effects, not to master output.
                result['schema']='endfield.frame-first-plane-gain-prefix.v1'
                if result['status']=='exactFiniteNonzeroMasterGainPrefix':result['status']='exactFiniteNonzeroFrameGainPrefix'
                result['evidenceBoundary']='Observed constant frame-gain arguments explain four first-plane values under nearest rounding. Effect-entry parent/return-site admission, other channels, whole buffers and later effect arithmetic are separate.'
                item['comparison']=result;status=result['status']
            item['status']=status;task['gains'].append(item)
        elif name.endswith('.biquadProcessing'):
            task['filters'].append(biquad_capture.snapshot(before,row,initial,final,self.selection))
        elif name.endswith('.collectionEqExecute'):
            item.update(instance=before['args'][0],collection=before['args'][1],moduleBase=before['moduleBase'],initial=dict(initial),final=dict(final))
            task['eq'].append(item)

    def evaluate(self,task,row,closed):
        result=dict(windowId=row['windowId'],taskCaptureId=row['captureId'],threadId=row['threadId'],
            status='taskBranchNotSelected',wholeEventToDeviceClaim=False)
        if row['phase']!=2 or not closed or not task['closed']:
            result['status']='taskNotClosedNormally';return result
        if row['returnValue']!=row['args'][1]:
            result['status']='taskResultStorageDiffers';return result
        if len(task['masters'])!=1:return result
        master=task['masters'][0];s=master['initial']
        if not selected(s,self.selection) or master['callerRva']!=int(self.return_sites['taskMasterCallReturnRva'],16) or master['parentCaptureId']!=row['captureId']:return result
        processes=[p for p in task['processing'] if p['bus']==master['bus'] and p['callerRva']==int(self.return_sites['taskProcessingCallReturnRva'],16) and p['parentCaptureId']==row['captureId']]
        if len(processes)!=1:return result
        p=processes[0]
        mixes=[m for m in task['mixes'] if m['bus']==master['bus'] and m['returnSequence']<p['entrySequence']]
        if not mixes:return result
        mix=max(mixes,key=lambda m:m['returnSequence'])
        if not (p['returnSequence']<master['entrySequence'] and same_storage(mix['storage'],p['initial']) and
                same_storage(p['initial'],p['final']) and same_storage(p['final'],s) and
                p['initial'].get('owner') and p['initial']['owner']==p['final'].get('owner')==s.get('owner')):
            result['status']='taskStorageTransitionUnsupported';return result
        if not (mix['afterPrefix'] and mix['afterPrefix']==p['beforePrefix'] and p['afterPrefix'] and p['afterPrefix']==master['beforePrefix']):
            result['status']='taskContentTransitionDiffers';return result
        result.update(status='sameTaskMixProcessingMasterPrefixes',bus=master['bus'],mixCaptureId=mix['captureId'],
            processingCaptureId=p['captureId'],masterCaptureId=master['captureId'],storage=s,
            processingChangedPrefix=p['beforePrefix']!=p['afterPrefix'],effects=[],gainComparisons=[])
        result.update(self.describe_effects(task,p,s))
        return result

    def describe_effects(self,task,p,s):
        """Use the same admitted effect/gain rules for master or child buses."""
        result=dict(effects=[],gainComparisons=[])
        for fx in task['effects']:
            if fx['parentCaptureId']!=p['captureId'] or fx['bus']!=p['bus'] or fx['callerRva']!=int(self.return_sites['effectConsumeCallReturnRva'],16) or not p['entrySequence']<fx['entrySequence']<fx['returnSequence']<p['returnSequence']:continue
            if not (same_storage(fx['initial'],fx['final']) and same_storage(fx['initial'],s) and fx['selectedCount']==1 and fx['selectedDescriptor']==s['descriptor'] and fx['beforePrefix'] and fx['afterPrefix'] and fx['initial'].get('owner')==fx['final'].get('owner')==s.get('owner')):continue
            exact=[]
            kernel=bool(self.collection_effect and fx.get('executeRva')==int(self.collection_effect['entryRva'],16) and fx.get('executeTargetStable') and
                fx['objectCount']==1 and fx['multiObjectMode']==1 and fx['inPlaceMode']==1 and fx['skipGainBake']==1)
            for gain in task['gains']:
                prepass=gain['callerRva']==int(self.return_sites['gainCallReturnRva'],16) and fx['skipGainBake']==0
                kernel_gain=kernel and gain['callerRva']==int(self.collection_effect['gainCallReturnRva'],16)
                if (gain['parentCaptureId']==fx['captureId'] and (prepass or kernel_gain) and
                    fx['entrySequence']<gain['entrySequence']<gain['returnSequence']<fx['returnSequence'] and
                    same_storage(gain['initial'],s) and gain['initial'].get('owner')==s.get('owner') and gain['final'].get('owner')==s.get('owner') and
                    gain['status']=='exactFiniteNonzeroFrameGainPrefix'):
                    gain['gainPath']='driverPrepass' if prepass else 'nativeCollectionKernel'
                    exact.append(gain);result['gainComparisons'].append(gain)
            ordinary=fx['objectCount']==1 and fx['multiObjectMode']==0 and fx['inPlaceMode']==1 and fx['currentControl']==0 and fx['previousControl']==0
            class_id=next((b['classId'] for b in self.effect_classes if fx.get('executeTargetStable') and fx.get('executeRva')==int(b['executeRva'],16) and fx.get('vtableRva')==int(b['vtableRva'],16)),None)
            result['effects'].append(dict(captureId=fx['captureId'],effectObject=fx['effectObject'],executeTarget=fx.get('executeTarget'),executeTargetStable=fx.get('executeTargetStable',False),ordinarySingleInPlace=ordinary,
                objectCount=fx['objectCount'],finalObjectCount=fx.get('finalObjectCount'),
                effectBranch='emptyEffectCollectionSnapshots' if fx['objectCount']==fx.get('finalObjectCount')==0 else 'registeredEffectInstance' if class_id else 'effectInstanceUnresolved',
                driverModes=dict(multiObject=fx['multiObjectMode'],inPlace=fx['inPlaceMode'],skipGainBake=fx['skipGainBake'],previousControl=fx['previousControl'],currentControl=fx['currentControl']),
                registeredEffectClassId=class_id,
                biquad=biquad_capture.effect_steps(task,fx,self.biquad) if self.biquad and class_id==self.biquad['eqClassId'] else None,
                changedPrefix=fx['beforePrefix']!=fx['afterPrefix'],gainResetToUnity=any(g['gainPath']=='driverPrepass' for g in exact) and fx['finalPreviousGainBits']==fx['finalTargetGainBits']==0x3f800000,
                nativeCollectionGainObserved=any(g['gainPath']=='nativeCollectionKernel' for g in exact),
                retainedGainsAfterEffect=dict(previousBits=fx['finalPreviousGainBits'],targetBits=fx['finalTargetGainBits']),
                residualChangeAfterGain=bool((ordinary or kernel) and exact and fx['afterPrefix'] and exact[-1]['afterPrefix']!=fx['afterPrefix'])))
        return result

    def publish(self,diagnostics):
        if diagnostics:
            return dict(schema='endfield.audio-bus-processing-witness.v1',status='captureDiagnosticsPresent',rows=[],diagnostics=diagnostics,
                unacceptedTaskStatusCounts=dict(self.counts),openTasks=len(self.tasks),wholeEventToDeviceClaim=False)
        return dict(schema='endfield.audio-bus-processing-witness.v1',status='conditionalTaskPrefixes',counts=dict(self.counts),rows=self.rows,
            openTasks=len(self.tasks),wholeEventToDeviceClaim=False,
            evidenceBoundary='Paired scoped task calls and matching descriptor/content snapshots connect a saved mix through observed post-processing into master entry. Gain equations cover bounded first-plane values. Observed vtables/Execute targets identify registered effect kernels; empty collection snapshots are separate from unresolved instances. EQ service operand/numerical comparisons, gain materialization and remaining prefix changes are separate. Whole-effect DSP, whole-buffer generation and Event contribution are not inferred.')
