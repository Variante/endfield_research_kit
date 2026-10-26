"""Conservative sink write/consume intervals over authenticated observations.

This ledger does not read memory or establish endpoint coverage. Its caller must
authenticate the selected layout and all observations, and supply a complete,
loss-free endpoint scope. Saved recipes without frame-end cannot enable it.

Evidence and admission boundary:

The native sink handoff is also more specific: conversion writes an inline
descriptor and sets input-present. On the non-ring, non-resampling path,
frame-end submits that descriptor when valid frames exist, then clears
input-present. The resampled path uses a different descriptor; the no-input
path submits silent COM buffers outside the observed sink-submit call. These
branches must remain distinct. Field displacements, masks and call witnesses
are native-bound in the mixer-frame contract. `sink_handoff_capture` implements
the corresponding observed write/consume ledger. It requires complete
sink-write and frame-end endpoint coverage, matching checked descriptors,
same-thread parent nesting, successful paired returns and the consumed flag.
Overlaps, intervening writes, unsupported modes and descriptor changes withhold
the join. A retained submit capture ID can connect to a same-invocation device
copy; it does not identify the upstream Event or a global allocation
generation. Both saved frame recipes fail this coverage gate, including the
loss-free recipe, because frame-end is absent and sink writes are sampled. No
generation join has been recovered from them.

A bounded offline replay of original callback records preserves all serialized
JSON values through the current worker writer and measures serialization and
file-write throughput. The measured rates and corpus are generated report data.
This excludes game contention, provider callback cost and the worker's other
tasks; it does not prove loss-free gameplay. The recorder still needs an
explicit bounded observation policy and the missing consumer/frame-end
endpoints; this measurement alone does not justify another capture.

The separate `audio-handoff` profile now supplies the sink-write/frame-end/
submission endpoints for a narrower question: does a completed master
conversion's saved PCM prefix reach a later same-sink device copy through a
checked write/consume interval? It observes every sink write, frame-end and
submission in an explicitly selected native window. Loading-time native roots
are excluded before observational memory reads. Paired returns and nested
device children retain the window ID acquired by their parent; a closure flag
prevents a late return from admitting an interval, including when timestamps
share the same coarse tick. Numpad and console toggles close the window, and
bounded drain batches keep those controls responsive under continuous traffic.
The user controls duration; the earlier fixed short cutoff has been removed.
The handoff preset starts the overlay automatically and retains host-stop
closure and the existing window/record bounds. Outside-window counters remain
distinct from intentional sampling skips and queue loss. The offline importer
checks the frozen activation, window IDs, closure flags, complete endpoint
scope, descriptor/mode/client addresses and same-thread parent nesting. It
joins completed master conversions and accepted device copies only through
their checked write and submit capture IDs, with converted-to-submitted prefix
equality. The new endpoints and controls are built and regression-tested; both
historical frame sessions retain their prior evidence boundaries on replay. A
loss-free handoff capture now supplies this conditional prefix witness:
completed master output contains the checked output consumer and sink
conversion; the completed sink write is consumed by a nested direct frame-end
submission before another observed write/consume; its device calls receive
successful HRESULTs and copy the same nonzero prefix. Independent inspection of
the original phase rows confirms the nesting, descriptor/mode/ client fields,
call order and byte equality. The first input plane also explains the
corresponding converted first-channel prefix under its recorded constant gain.
These observations connect master conversion to actual render-client buffer
submission. They cover saved prefixes and observed intervals, not whole
buffers, unobserved writers, audibility or an individual Event's contribution
to mixed output. Last-observed same-bus mixes agree with the master input's
descriptor while their saved prefixes differ from the later conversion input.
The native matching-layout master branch can pad the descriptor and apply
retained per-frame gains before the output consumer; these saved rows lack all
intervening operands. Sampled bus-mix endpoints also leave possible intervening
writers. Descriptor matches remain discovery candidates, not a proved buffer
generation, numerical explanation or an Event-to-master join.
"""
from __future__ import annotations

from collections import Counter


def coverage_diagnostics(hooks, *, native_status, complete, dropped, skipped):
    issues=[]
    if native_status!='validated':issues.append('selectedNativeInputsNotValidated')
    if complete is not True or type(dropped) is not int or dropped!=0:
        issues.append('endpointStreamNotCompleteAndLossFree')
    for kind in ('sinkInput','sinkFrameEnd','sinkSubmit'):
        matching=[h for h in hooks if h.get('sourceKind')==kind]
        if len(matching)!=1:issues.append('missingOrAmbiguousEndpoint:'+kind)
        elif type(skipped.get(kind)) is not int or skipped[kind]!=0:
            issues.append('endpointNotFullySelected:'+kind)
    return issues


class SinkHandoffCapture:
    """Track observed writes, not allocation generations or Event contribution.

    Rows use the existing capture phase, window, invocation, parent and sequence
    keys. Facts are a successfully read normalized descriptor plus address map;
    the upstream observer validator owns read states and argument forwarding.
    """
    def __init__(self, layout, *, coverage_issues):
        self.layout=dict(layout);self.coverage_issues=list(coverage_issues)
        self.writes={};self.calls={};self.active={};self.ordinals={}
        self.joins=[];self.counts=Counter();self.last_sequence={}

    def _bounded(self, collection):
        if len(collection)>=100000:raise ValueError('sink handoff observation bound exceeded')

    def _snapshot(self, row, facts, *, submit=False, consumed=False):
        sink=row['args'][0];layout=self.layout
        descriptor=sink+layout['descriptorOffset']
        if type(sink) is not int or not 0<sink<descriptor<0x800000000000:
            return None
        if submit and row['args'][1]!=descriptor:return None
        offsets=dict(renderClient=layout['renderClientOffset'],samplePointer=layout['descriptorOffset'],
            channelConfiguration=layout['descriptorOffset']+layout['formatOffset'],
            capacityFrames=layout['descriptorOffset']+layout['capacityOffset'],
            validFrames=layout['descriptorOffset']+layout['validFramesOffset'])
        if not submit:offsets.update(inputFlags=layout['inputFlagsOffset'],resamplerCapacity=layout['resamplerCapacityOffset'])
        addresses=facts.get('readAddresses',{})
        if any(type(facts.get(name)) is not int or addresses.get(name)!=sink+offset for name,offset in offsets.items()):
            return None
        pointer=facts['samplePointer'];capacity=facts['capacityFrames'];valid=facts['validFrames']
        if not 0<pointer<0x800000000000 or not 0<facts['renderClient']<0x800000000000 or not 0<valid<=capacity<65536 or not 0<facts['channelConfiguration']<2**32:
            return None
        if not submit:
            flags=facts['inputFlags']
            if not 0<=flags<256 or bool(flags&layout['inputPresentMask'])==consumed or flags&layout['excludedModesMask'] or facts['resamplerCapacity']!=0:
                return None
        return dict(descriptor=descriptor,samplePointer=pointer,renderClient=facts['renderClient'],channelConfiguration=facts['channelConfiguration'],capacityFrames=capacity,validFrames=valid)

    def _prefix(self, row, snapshot):
        if not snapshot or not row.get('spanBytes'):return None
        raw=bytes.fromhex(row['spanHex'])
        if len(raw)!=row['spanBytes'] or not 0<len(raw)<=256 or row['spanAddress']!=snapshot['samplePointer']:
            raise ValueError('sink handoff PCM prefix address or extent differs')
        return row['spanHex']

    def _invalidate(self, key):
        self.writes.pop(key,None)
        for call_id in self.active.get(key,()):self.calls[call_id]['invalidated']=True

    def observe(self, kind, row, facts):
        if self.coverage_issues:return
        if kind not in ('sinkInput','sinkFrameEnd','sinkSubmit'):return
        window=row['windowId'];sequence=row['sequence']
        if type(sequence) is not int or sequence<=self.last_sequence.get(window,-1):
            raise ValueError('sink handoff requires ordered unique capture sequences')
        self.last_sequence[window]=sequence
        call_id=(window,row['captureId']);key=(window,row['args'][0]);phase=row['phase']
        if phase==1:
            self._bounded(self.calls)
            if call_id in self.calls:raise ValueError('duplicate sink handoff invocation')
            closed=row.get('observationWindowOpen') is False
            if closed:self._invalidate(key)
            record=dict(kind=kind,key=key,entry=dict(row),invalidated=closed)
            if kind=='sinkInput':
                overlapping=bool(self.active.get(key))
                self._invalidate(key)
                self._bounded(self.ordinals)
                self.ordinals[key]=self.ordinals.get(key,0)+1
                record.update(ordinal=self.ordinals[key],invalidated=overlapping or closed)
            elif kind=='sinkFrameEnd':
                candidate=self.writes.pop(key,None)
                overlapping=bool(self.active.get(key))
                if overlapping:self._invalidate(key)
                snapshot=self._snapshot(row,facts)
                matched=bool(candidate and not overlapping and not closed and candidate['threadId']==row['threadId'] and candidate['snapshot']==snapshot)
                record.update(candidate=candidate if matched else None,snapshot=snapshot,submits=[])
            else:
                parent=self.calls.get((window,row['parentCaptureId']))
                snapshot=self._snapshot(row,facts,submit=True)
                eligible=bool(parent and parent['kind']=='sinkFrameEnd' and parent['key']==key and
                    parent['entry']['threadId']==row['threadId'] and not parent['invalidated'] and parent['candidate'] and
                    parent['snapshot']==snapshot)
                # Any other submission is an observed intervening consume.
                # Even equal descriptor fields cannot carry the old write past it.
                if not eligible:self._invalidate(key)
                record.update(parent=parent if eligible else None,snapshot=snapshot,prefix=self._prefix(row,snapshot))
            self.calls[call_id]=record
            self.active.setdefault(key,set()).add(call_id)
            return
        record=self.calls.pop(call_id,None)
        if not record:raise ValueError('sink handoff return lacks its entry')
        self.active[key].discard(call_id)
        if not self.active[key]:self.active.pop(key)
        if record['kind']!=kind or record['key']!=key or record['entry']['threadId']!=row['threadId'] or record['entry']['invocationStartNs']!=row['invocationStartNs']:
            raise ValueError('sink handoff return identity differs')
        if phase!=2 or record['invalidated'] or row.get('observationWindowOpen') is False:
            self.counts['unwoundOrInvalidatedCalls']+=1
            self.writes.pop(key,None)
            if kind=='sinkSubmit' and record.get('parent'):record['parent']['invalidated']=True
            return
        if kind=='sinkInput':
            snapshot=self._snapshot(row,facts)
            if snapshot:
                self._bounded(self.writes)
                self.writes[key]=dict(writeCaptureId=row['captureId'],writeOrdinal=record['ordinal'],threadId=row['threadId'],snapshot=snapshot,prefix=self._prefix(row,snapshot))
                self.counts['completedDirectWrites']+=1
            else:self.counts['unsupportedWriteReturns']+=1
        elif kind=='sinkSubmit':
            parent=record['parent']
            if parent and not parent['invalidated'] and record['snapshot']==self._snapshot(row,facts,submit=True):
                parent['submits'].append(dict(captureId=row['captureId'],prefix=record['prefix']))
            elif parent:parent['invalidated']=True
        else:
            addresses=facts.get('readAddresses',{})
            flags=facts.get('inputFlags')
            consumed=bool(type(flags) is int and 0<=flags<256 and not flags&self.layout['inputPresentMask'] and
                not flags&self.layout['excludedModesMask'] and addresses.get('inputFlags')==key[1]+self.layout['inputFlagsOffset'])
            # One direct submit only; no resampling/repeated consume is inferred.
            if consumed and not self.active.get(key) and record['candidate'] and len(record['submits'])==1 and record['snapshot']==self._snapshot(row,facts,consumed=True):
                self._bounded(self.joins)
                self.joins.append(dict(windowId=window,sink=key[1],threadId=row['threadId'],
                    writeCaptureId=record['candidate']['writeCaptureId'],writeOrdinal=record['candidate']['writeOrdinal'],
                    frameEndCaptureId=row['captureId'],sinkCaptureId=record['submits'][0]['captureId'],
                    descriptor=record['snapshot']['descriptor'],samplePointer=record['snapshot']['samplePointer'],
                    renderClient=record['snapshot']['renderClient'],
                    convertedPrefixMatchesSubmission=bool(record['candidate']['prefix'] and record['candidate']['prefix']==record['submits'][0]['prefix']),
                    comparedPrefixBytes=len(record['candidate']['prefix'])//2 if record['candidate']['prefix'] and record['candidate']['prefix']==record['submits'][0]['prefix'] else 0,
                    evidenceBoundary='conditionalObservedWriteConsumeInterval',wholeEventToDeviceClaim=False))
            else:self.counts['withheldFrameEnds']+=1

    def report(self):
        return dict(schema='endfield.sink-write-consume-intervals.v1',
            status='coverageWithheld' if self.coverage_issues else 'openCalls' if self.calls else 'reviewedObservedIntervals',
            diagnostics=list(self.coverage_issues),openCalls=len(self.calls),counts=dict(self.counts),joins=list(self.joins),
            evidenceBoundary='Native validation and complete endpoint scope are supplied by the caller. These same-thread nested intervals exclude observed sink writes and consumption, not unobserved writers or allocation reuse. Device copies join only by the retained same-invocation sinkCaptureId; Event/bus attribution remains separate.')

    def withhold(self, diagnostics):
        self.coverage_issues.extend(diagnostics)
        self.writes.clear();self.joins.clear()
