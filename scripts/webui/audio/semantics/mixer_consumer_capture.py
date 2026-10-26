"""Same-call first-output equation at the original matrix consumer boundary."""
from __future__ import annotations

from collections import Counter
import struct
from scripts.webui.audio.semantics.mixer_pcm_witness import compare_constant_first_output

REPORT_ROW_LIMIT=100000


def words_hex(facts, prefix, count=4):
    return b''.join(struct.pack('<I',facts[prefix+str(i)]) for i in range(count)).hex()


class MixerConsumerCapture:
    def __init__(self, selection, input_boundary):
        self.selection=selection; self.input_boundary=input_boundary
        self.rows=[];self.counts=Counter()

    def validate_addresses(self, row, facts, fields):
        if not row['hook'].endswith('.unfilteredMatrixConsumer') or row['phase']==3:return
        addresses={f['name']:row['addresses'][i] for i,f in enumerate(fields) if facts.get(f['name']) is not None}
        direct={'cohortCount':row['args'][0]+self.selection['cohortCountOffset'],'sourceDescriptor':row['args'][3],
            'outputDescriptor':row['extraArgument'],'previousGainBits':row.get('sixthArgument',0),'targetGainBits':row.get('sixthArgument',0)+4}
        for name, expected in direct.items():
            if name in addresses and addresses[name]!=expected:raise ValueError('matrix consumer '+name+' read address differs')
        for domain in ('source','output'):
            descriptor=facts.get(domain+'Descriptor')
            if descriptor is not None:
                for suffix,offset in self.selection['descriptorOffsets'].items():
                    name=domain+suffix
                    if name in addresses and addresses[name]!=descriptor+offset:raise ValueError('matrix consumer descriptor field address differs')
        for i in range(4):
            for prefix,base in [('sourceSecondWord',facts.get('sourceSamplePointer')),('initialOutputWord',facts.get('outputSamplePointer'))]:
                name=prefix+str(i)
                if name in addresses and (base is None or addresses[name]!=base+(self.selection['secondPlaneStrideBytes'] if prefix=='sourceSecondWord' else 0)+i*4):
                    raise ValueError('matrix consumer planar word address differs')
        for prefix in ('previous','target'):
            base=addresses.get(prefix+'MatrixWord0')
            stride=self.selection['matrixRowAlignmentFloats']
            for index in (1,stride,stride+1):
                name=prefix+'MatrixWord'+str(index)
                # In an unsupported output layout the first matrix word is
                # guarded out, while the stereo-source tail reads remain raw.
                # No equation admits that call; absence of the guarded anchor
                # is not a malformed receipt or a captured null pointer.
                if name in addresses and base is not None and addresses[name]!=base+index*4:raise ValueError('matrix consumer padded matrix row address differs')
        sample_pointer=facts.get(('source' if row['phase']==1 else 'output')+'SamplePointer')
        if row['spanBytes'] and sample_pointer is not None and row['spanAddress']!=sample_pointer:
            raise ValueError('matrix consumer PCM prefix address differs')

    def completed(self, before, row, facts, initial, pending, *, inside_closed_window):
        if not row['hook'].endswith('.unfilteredMatrixConsumer'):return
        self.counts['unwound' if row['phase']==3 else 'completed']+=1
        item=dict(windowId=row['windowId'],consumerCaptureId=row['captureId'],threadId=row['threadId'],
            inputBoundary=self.input_boundary,wholeEventToDeviceClaim=False,parentMixCaptureId=None)
        def withheld(reason):
            item['status']=reason;self.save(item)
        if row['phase']!=2:return withheld('unwoundConsumer')
        if not inside_closed_window or not before.get('observationWindowOpen'):return withheld('outsideClosedWindow')
        required=('cohortCount','cohortFirstIndex','frameCapacity','sourceDescriptor','sourceCapacity','sourceValidFrames','sourceFormat',
            'sourceSamplePointer','outputDescriptor','outputCapacity','outputValidFrames','outputFormat','outputSamplePointer')
        if any(initial.get(k) is None or facts.get(k) is None for k in required):return withheld('consumerGeometryNotSelected')
        if any(initial[k]!=facts[k] for k in required):return withheld('consumerGeometryChanged')
        s=self.selection
        if initial['cohortCount']!=1 or initial['cohortFirstIndex']!=0:return withheld('sourceCohortNotSingleFirstRow')
        if any(initial[k]!=s[k] for k in ('frameCapacity','sourceCapacity','sourceValidFrames','outputCapacity','outputValidFrames','outputFormat')):
            return withheld('consumerExtentUnsupported')
        if initial['sourceFormat'] not in s['sourceFormats']:return withheld('channelLayoutUnsupported')
        if before.get('roundingModeSampled') is not True or type(before.get('mxcsr')) is not int:return withheld('roundingNotObserved')
        channels=initial['sourceFormat']&255
        # The original source and output must be distinct bounded planar allocations.
        a=initial['sourceSamplePointer'];b=initial['outputSamplePointer']
        if max(a,b)<min(a+initial['sourceCapacity']*channels*4,b+initial['outputCapacity']*2*4):return withheld('sourceOutputStorageOverlaps')
        needed=['previousGainBits','targetGainBits']+['initialOutputWord'+str(i) for i in range(4)]
        stride=s['matrixRowAlignmentFloats']
        indices=(0,1,stride,stride+1) if channels==2 else (0,1)
        needed += [p+'MatrixWord'+str(i) for p in ('previous','target') for i in indices]
        if channels==2:needed+=['sourceSecondWord'+str(i) for i in range(4)]
        if any(initial.get(k) is None for k in needed) or before['spanBytes']!=16 or row['spanBytes']!=16:return withheld('consumerInputsIncomplete')
        planes=[before['spanHex']]
        if channels==2:planes.append(words_hex(initial,'sourceSecondWord'))
        matrices={}
        for prefix in ('previous','target'):
            words=[0]*((channels-1)*stride+2)
            for i in indices:words[i]=initial[prefix+'MatrixWord'+str(i)]
            matrices[prefix]=words
        result=compare_constant_first_output(planes,words_hex(initial,'initialOutputWord'),row['spanHex'],
            input_boundary=self.input_boundary,cohort_indices=[0],source_channels=channels,output_channels=2,
            frame_capacity=initial['frameCapacity'],valid_frames=initial['sourceValidFrames'],
            previous_gain_bits=initial['previousGainBits'],target_gain_bits=initial['targetGainBits'],
            previous_matrix_words=matrices['previous'],target_matrix_words=matrices['target'],matrix_stride=stride,mxcsr=before['mxcsr'])
        item.update(status=result['status'],equation=result,input=initial,sourcePlanes=planes,
            initialOutput=words_hex(initial,'initialOutputWord'),output=row['spanHex'],mxcsr=before['mxcsr'])
        ancestor=before['parentCaptureId'];seen=set()
        while ancestor and ancestor not in seen and len(seen)<64:
            seen.add(ancestor);entry=pending.get((row['windowId'],ancestor))
            if not entry or entry[0]['threadId']!=row['threadId']:break
            if entry[0]['hook'].endswith('.busRouteMix'):
                if entry[1].get('firstRowDescriptor')==initial['sourceDescriptor'] and entry[1].get('mixRowCount')==1:
                    item['parentMixCaptureId']=ancestor
                break
            ancestor=entry[0]['parentCaptureId']
        self.save(item)

    def save(self, item):
        self.counts[item['status']]+=1
        if len(self.rows)<REPORT_ROW_LIMIT:self.rows.append(item)
        else:self.counts['reportRowsOmitted']+=1

    def publish(self, *, diagnostics=(), frame=None, lineage=None):
        rows=[] if diagnostics else self.rows
        mixes={(m.get('windowId'),m['mixCaptureId']):m for m in frame['mixes']} if frame else {}
        transports={}
        for t in (lineage or {}).get('localTransport',[]):
            c=t['constructor'];key=(c['windowId'],c['threadId'],c['primaryOwner'],c['source'],t['serial'])
            transports.setdefault(key,[]).append(t)
        counts=Counter(self.counts)
        for row in rows:
            mix=mixes.get((row['windowId'],row['parentMixCaptureId']))
            if mix:
                row['parentMixNormalReturn']=True
                output=mix['output'];initial=row['input']
                row['parentOutputPrefixMatches']=all(output.get(a)==initial.get(b) for a,b in
                    (('busFirstDescriptor','outputDescriptor'),('busSamplePointer','outputSamplePointer'),('busFormat','outputFormat'),
                     ('busCapacity','outputCapacity'),('busValidFrames','outputValidFrames'))) and mix.get('outputPrefixFirst16Hex')==row['output']
                if row['parentOutputPrefixMatches']:counts['sameParentOutputPrefixes']+=1
                source=mix['sourceCandidate'] or mix['publishedSourceCandidate']
                if source and source['descriptor']==row['input']['sourceDescriptor'] and source['samplePointer']==row['input']['sourceSamplePointer']:
                    row['sourceIntervalCandidate']=dict(source)
                    row['sourcePrefixContinuity']=source.get('prefixFirst16Hex')==row['sourcePlanes'][0] and (len(row['sourcePlanes'])==1 or source.get('secondPlaneFirst16Hex')==row['sourcePlanes'][1])
                    if row['sourcePrefixContinuity']:counts['sourcePrefixContinuities']+=1
                    key=(row['windowId'],row['threadId'],source['primaryOwner'],source['storedSource'],source['serial'])
                    selected=[t for t in transports.get(key,[]) if type(source.get('sampleSequence')) is int and t['constructor']['sequence']<source['sampleSequence'] and t['selector']['allocation']==source['allocation']]
                    if row['sourcePrefixContinuity'] and len(selected)==1:
                        t=selected[0];row['sourceTransportCandidate']=t
                        if len(t['managedCandidates'])==1:
                            row['managedEventCandidate']=t['managedCandidates'][0];counts['uniqueManagedEventCandidates']+=1
                        if t['selection']=='singleDescriptorWideSetterInput' and t['selector']['descriptorPath']:
                            row['observedExternalPath']=t['selector']['descriptorPath'];counts['observedExternalPathCandidates']+=1
        return dict(schema='endfield.matrix-consumer-capture-witness.v2',rows=rows,counts=dict(counts),
            diagnostics=list(diagnostics),wholeEventToDeviceClaim=False,
            evidenceBoundary='Same-call four first-output samples use observed original-consumer input PCM, gain/matrix and initial output with entry MXCSR. Parent output joins require completed nesting, descriptor/PCM/format/extents and prefix equality. Source content and completed Action/selector/constructor candidates additionally require plane-prefix continuity, current owner/source/serial/allocation identity and constructor-before-sample ordering. They do not establish an allocation generation, complete bus output or individual Event contribution to device PCM.')
