"""Retain completed master-output conversion children without inventing frame joins."""
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
