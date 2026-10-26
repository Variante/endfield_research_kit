"""Retain completed master-output conversion children without inventing frame joins.

Evidence and admission boundary:

Further caller review corrects the mixer-array boundary. `busRouteMix` receives
caller result storage in the second integer register and its selected
row-pointer array in the fourth. The array contains mixer rows, not top-level
route objects. Older playback/device recipes sampled result-storage bytes under
an incorrect route-array label. Their raw bytes remain historical, but the
current review excludes that array interpretation. Independently read route
source/bus fields and the same-invocation sink/device copy witnesses remain
valid. The corrected playback contract authenticates argument retention and the
subsequent indexed row read inside the existing complete routing body.

The primary owner constructor also copies the queued playback serial and
retained external allocation from its parameter blob into owner storage,
alongside the selected source pointer. These are direct native stores, not
lifetime inferred from matching constructor addresses. The prepared
`audio-mixer` preset, owned by `wwise_mixer_capture_native.json`, reads that
current identity alongside source PCM and retains the actual mixer-row prefix
plus its first descriptor, format, gain and matrix fields. Read addresses must
agree with the recorded owner/row/descriptor to reject changed pointer chains.
A stored serial remains a managed Event candidate without observed queue
generation and atomic ownership; the preset cannot retrospectively add these
fields to saved captures.

The preset pairs master output, output-consumer and sink-input conversion
calls. The latter consumers take a raw stack gain pair in addition to their
register arguments; their reviewed native loads establish that calling surface.
Original calls execute once. Only completed same-thread master/consumer/sink
nesting with matching node, sink and descriptor contributes a conversion
witness. Output children keep their parent's recorder and window through normal
stop. Native worker callers confirm that source publication, bus output and bus
reset are separate work stages; a result-storage pointer alone does not
identify a whole frame generation. A later device submission still needs a
proved buffer/frame join. The mixer capture now supplies actual row
arrays/first descriptors and completed master/consumer/sink conversion chains
with successful device submissions. The source sample descriptor agrees with
the authenticated context PCM field. Some first-row descriptors share recorded
source sample storage, format and frame extent; some converted prefixes also
share exact nonzero content and storage with submitted prefixes. These remain
candidates without observed reset/write generations, rather than same-frame
Event contribution.

The initial owner-ID declaration read a neighboring parameter word. Its native
load/store were real, but the load did not use the selector's declared serial
field. The corrected mixer contract binds each copied serial/allocation load
back to the owned selector-blob field as well as checking the owner store. The
streaming review excludes the old ID label and preserves other current
owner/source reads with an explicit partial identity and unavailable serial.
Zero values from that old field are not zero playing IDs. The corrected repeat
now observes nonzero current owner serials beside completed PCM. Every sampled
current serial has one saved managed Event candidate. A subset also matches a
complete owner/serial/source/allocation tuple from one recorded local
Action/selector/constructor chain, including finite nonzero PCM. These current
reads replace latest-constructor proximity for identity comparison; they remain
non-atomic stored identity and lifetime-conditional transport, not allocation
generations. Do not request another identical capture to re-prove the serial.
Some observations have no recorded local transport tuple, and others retain the
same owner address and serial but a different stored source from the
constructor input. Exclude both from the complete tuple join. A serial-only
match cannot explain source replacement, owner reuse or a different constructor
family; those alternatives remain open until their native mutation/lifetime
endpoints are observed.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from scripts.webui.audio.semantics.sink_pcm_witness import compare_first_plane
from scripts.webui.audio.semantics.master_gain_witness import admitted_master_comparison


class MixerCapture:
    def __init__(self, master_selection=None):
        self.master_selection=master_selection
        self.scopes={}
        self.completed_scopes=[]
        self.counts=Counter()
        self.consumer_children={}

    def completed(self, before, row, facts, pending, input_facts=None, *, inside_closed_window=True):
        if row['hook'].endswith('.outputConsumer'):
            for item in self.consumer_children.pop((row['windowId'],row['captureId']),[]):
                item['outputConsumerNormalReturn']=row['phase']==2
            return
        if row['hook'].endswith('.masterBusOutput'):
            children=self.scopes.pop((row['windowId'],row['captureId']),[])
            self.counts['normalMasterOutput' if row['phase']==2 else 'unwoundMasterOutput']+=1
            children=[c for c in children if c.get('outputConsumerNormalReturn')]
            if row['phase']==2 and children:
                if self.master_selection:
                    for child in children:
                        child['masterInputGainComparison']=admitted_master_comparison(before,row,input_facts or {},facts,child,self.master_selection) if inside_closed_window else dict(status='outsideClosedWindow',wholeEventToDeviceClaim=False)
                if len(self.completed_scopes)>=100000:raise ValueError('master output scope bound exceeded')
                self.completed_scopes.append(dict(windowId=row['windowId'],masterCaptureId=row['captureId'],threadId=row['threadId'],
                    bus=before['args'][0],outputNode=before['args'][1],conversions=children))
            return
        if row['phase']!=2 or not row['hook'].endswith('.sinkInput'):return
        parent=pending.get((row['windowId'],row['parentCaptureId']))
        if not parent or not parent[0]['hook'].endswith('.outputConsumer'):return
        consumer,consumer_facts=parent
        ancestor=consumer['parentCaptureId'];root=None;seen=set()
        while ancestor and ancestor not in seen and len(seen)<64:
            seen.add(ancestor);entry=pending.get((row['windowId'],ancestor))
            if not entry or entry[0]['threadId']!=row['threadId']:break
            if entry[0]['hook'].endswith('.masterBusOutput'):root=entry[0];break
            ancestor=entry[0]['parentCaptureId']
        if root is None:return
        if (consumer['threadId']!=row['threadId'] or root['args'][1]!=consumer['args'][0] or
                consumer['args'][1]!=before['args'][1] or consumer_facts.get('sinkInterface')!=before['args'][0]):
            raise ValueError('master/output-consumer/sink conversion input identity differs')
        if any(facts.get(k) is None for k in ('samplePointer','channelConfiguration','validFrames','renderClient')):
            return
        if row['spanBytes'] and row['spanAddress']!=facts['samplePointer']:
            raise ValueError('converted sink prefix address differs from its sample pointer')
        if input_facts is not None and before['spanBytes'] and before['spanAddress']!=input_facts.get('samplePointer'):
            raise ValueError('sink input prefix address differs from its sample pointer')
        key=(row['windowId'],root['captureId'])
        if key not in self.scopes:
            if len(self.scopes)>=100000:raise ValueError('pending master output bound exceeded')
            self.scopes[key]=[]
        if len(self.scopes[key])>=4096:raise ValueError('master output child bound exceeded')
        item=dict(outputConsumerCaptureId=consumer['captureId'],sinkInputCaptureId=row['captureId'],
            inputDescriptor=before['args'][1],sink=before['args'][0],renderClient=facts['renderClient'],
            inputSamplePointer=(input_facts or {}).get('samplePointer'),inputPrefixFirst16Hex=before['spanHex'][:32],
            convertedSamplePointer=facts['samplePointer'],convertedFormat=facts['channelConfiguration'],convertedFrames=facts['validFrames'],
            outputConsumerIncomingGainPairBits=consumer['extraArgument'],sinkIncomingGainPairBits=before['extraArgument'],
            inputPrefixBytes=before['spanBytes'],inputPrefixSha256=hashlib.sha256(bytes.fromhex(before['spanHex'])).hexdigest(),
            convertedPrefixBytes=row['spanBytes'],convertedPrefixSha256=hashlib.sha256(bytes.fromhex(row['spanHex'])).hexdigest())
        if input_facts is not None and all(input_facts.get(k) is not None for k in ('channelConfiguration','validFrames')):
            item['firstPlaneGainComparison']=compare_first_plane(before['spanHex'],row['spanHex'],
                input_format=input_facts['channelConfiguration'],output_format=facts['channelConfiguration'],
                input_frames=input_facts['validFrames'],output_frames=facts['validFrames'],gain_pair_bits=before['extraArgument'])
        self.scopes[key].append(item)
        self.consumer_children.setdefault((row['windowId'],consumer['captureId']),[]).append(item)

    def publish(self):
        return dict(schema='endfield.audio-mixer-conversion-witness.v3',completedMasterScopes=self.completed_scopes,
            counters=dict(self.counts),openMasterScopes=len(self.scopes),wholeEventToDeviceClaim=False,
            evidenceBoundary=dict(direct='Completed same-thread master output contains output-consumer and sink-conversion calls with the same node, sink and input descriptor; raw gain pairs and converted prefix bytes are retained.',
                unresolved='A later sink submission needs an observed buffer/frame generation join. Mixed output is not attributed to an Event using pointer reuse, prefix proximity or a previous constructor. Whole buffers, asynchronous task lifetimes and topology remain open.'))

    def withhold_master_comparisons(self):
        if self.master_selection:
            for scope in self.completed_scopes:
                for child in scope['conversions']:
                    child['masterInputGainComparison']=dict(status='captureDiagnosticsPresent',wholeEventToDeviceClaim=False)
