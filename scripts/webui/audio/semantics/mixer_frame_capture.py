"""Retain observed source-write, publication and bus-reset intervals.

Evidence and admission boundary:

The same source descriptor/sample/format/frame storage can have different saved
serial candidates within a capture. This is observed reuse, so an
entire-session storage join cannot identify the mixer frame's Event. The
prepared `wwise_mixer_frame_native.json` extension pairs actual bus mixing with
completed first output descriptor/PCM reads, and observes every source
sample/release, native descriptor publication and bus reset endpoint while
recording is active. Its bus wrapper forwards all six integer/pointer arguments
and preserves the caller result-storage return; publication and reset wrappers
retain raw return-register bits without assigning an object meaning. Native
publication supplies the exact context descriptor to route rows; completed
reset clears retained bus input PCM and valid frames. The extension must be
selected by its frame manifest. A newer recorder DLL with the earlier mixer
manifest retains the earlier sampled observer, without the publication/reset
endpoints. Use the frozen manifest, activation roster and endpoint counters to
establish selection; loss-free transport is independent. The offline reviewer
retains bounded reset examples and observed reset ordinals, checks
source-write/release intervals, current publication identity and same-call
input/output addresses, and rejects intentional endpoint skips. These ordinals
are observed intervals rather than a native global frame counter. Other
writers, concurrent ownership, all rows/channels/effects and device-frame
attribution stay conditional or unresolved. A completion after stop cannot
admit an interval join. The frame observer is now captured: completed native
publication reads the same current owner/serial/source/allocation as the
sampled PCM, and a subset of actual mix rows retains that published
descriptor/sample/format/frame identity within the observed write/reset
interval. A selected physical voice WEM reproduces a finite source prefix; its
current identity also occurs in nonzero bus-mix output observations. This
extends the conditional file/source-to-mixer-input path, without proving the
gain/matrix/filter equation or later device-frame identity. Source and
bus-output prefixes differ even for single-row scopes, so pointer continuity
must not be described as an unchanged PCM copy.

Return-storage leaf review establishes only anonymous word initialization and
move/clear operations. These leaves neither schedule nor wait for work, and the
returned caller storage is not evidence of an asynchronous task or dependency.
The numeric declaration now captures incoming gain pairs, the previous/target
matrix pointers and first words, and a filter target beside the mix call. It
also reads a few second-plane words only under explicit stereo-format, capacity
and valid-frame guards. Stored matrix words still need their selected
consumer/layout and filter history before they can explain effective channel
output. The native mix body multiplies each incoming previous/target gain by
the corresponding row gain and writes the products back into the gain-pair
array before filter/matrix dispatch. Entry reads precede those mutations.
Independent IEEE nearest float32 products describe these captured operands, not
observed effective output; the integer-only wrapper does not observe native
MXCSR. Two matrix words are not a complete stereo matrix, and a zero filter
target does not prove bypass or empty history.

The numeric capture overflowed the recorder queue. Keep its completed
same-invocation matrix/gain reads, source identities and sink-copy pairs as
local observations, but withhold every source-write/publication/reset interval
join from that session. The earlier loss-free frame scopes remain accepted
separately. The reviewer now resolves coefficient reads through their recorded
matrix pointers and accepts guarded-out argument fields without replacing the
actual call register. It checks incoming gains against fifth-argument storage;
stream diagnostics also invalidate previously retained absence-of-intervening
write/reset claims. The recorder now buffers each JSON row through the shared
worker writer instead of formatting each scalar and hex digit separately. A
shorter repeat still needs zero losses; a successful build does not prove that
transport condition.

Code review withdraws the unchanged numeric repeat. The recipe's mix entry span
contains row pointers rather than PCM at the native filter/matrix boundary; it
reads only the first row, limited matrix words and a few second-plane samples.
It also leaves master conversion and later sink submission as separate observed
scopes without a carried buffer generation. Loss-free repetition alone cannot
close either the numerical equation or Event-to-device attribution. Prove the
native consumer read order and a sufficient bounded comparison offline first.
The reviewer corrections now invalidate previous context/row projections on
publication entry, require completed publication identity to agree with its
entry and source write, and bind source ordinals to individual invocations.
Overlapping, released, superseded and late calls cannot create a source
interval. Primary descriptor and PCM span addresses are checked before counting
source observations; guarded-out or failed reads cannot supply copied bytes.
Bounded regression cases cover the reproduced failures. Both saved frame
sessions have been replayed: the clean session retains its prior conditional
candidates with no diagnostics, and the lossy session still withholds
intervals. Those tests demonstrate corrected reader behavior, not that the
fabricated failure cases occurred in the game. Native calls and waveform data
were not changed. Keep direct call/storage and sink-copy witnesses separate.
The dense endpoint policy runs throughout the provider lifetime, and automatic
recording starts at runtime readiness; a short gameplay instruction does not
bound loading-time observation or prove sufficient queue/drain capacity.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import math
import struct

REPORT_ROW_LIMIT=100000


def combined_first_row_gains(facts):
    """Model the witnessed MULSS operands with IEEE nearest float32 rounding."""
    products=[]
    for phase in ('Previous','Target'):
        words=[facts.get('firstRow'+phase+'GainBits'),facts.get('incoming'+phase+'GainBits')]
        if any(type(word) is not int or not 0<=word<2**32 for word in words):return None
        values=[struct.unpack('<f',struct.pack('<I',word))[0] for word in words]
        if not all(math.isfinite(value) for value in values):return None
        try:bits=struct.unpack('<I',struct.pack('<f',values[0]*values[1]))[0]
        except OverflowError:return None
        if not math.isfinite(struct.unpack('<f',struct.pack('<I',bits))[0]):return None
        products.append(bits)
    return dict(previousBits=products[0],targetBits=products[1],status='modeledIeeeNearestProducts',
        scope='First row operand products only, not observed effective output. Native MXCSR rounding/FTZ/DAZ, filter/matrix interpolation and accumulation remain unresolved by this integer-only call.')


def endpoint_coverage_diagnostics(summary, hooks, kinds, counts):
    sampling=summary.get('playbackSampling',{})
    issues=[]
    if sampling.get('allSourcePublicationResetEndpoints') is not True:
        issues.append(dict(check='mixerFrameEndpointMode',expected=True,actual=sampling.get('allSourcePublicationResetEndpoints')))
    for kind in kinds:
        index=next(i for i,h in enumerate(hooks) if h['sourceKind']==kind)
        hook=hooks[index]
        observed=counts[(hook['name'],4 if hook['abiId']=='win64.transparent_entry_snapshot.v1' else 1)]
        if index>=len(sampling.get('selected',[])) or index>=len(sampling.get('skipped',[])) or type(sampling['selected'][index]) is not int or sampling['skipped'][index] or sampling['selected'][index]<observed:
            issues.append(dict(check='mixerFrameEndpointCoverage',hook=hook['name'],observed=observed,
                selected=sampling.get('selected',[])[index:index+1],skipped=sampling.get('skipped',[])[index:index+1]))
    return issues


def endpoint_selection_scope(summary, hooks, kinds, counts, *, key_field='sourceKind'):
    """Provider counters and closed-window serialization have different extents.

    The worker discards records whose recorded invocation does not belong to a
    requested window, including callbacks queued during quiescence. A positive
    difference is kept unattributed; it is not a proof of window completeness.
    """
    sampling=summary.get('playbackSampling',{})
    scope=sampling.get('nativeSelectionScope','providerLifetime')
    result=[]
    for kind in kinds:
        index=next(i for i,h in enumerate(hooks) if h.get(key_field)==kind);hook=hooks[index]
        selected=sampling.get('selected',[])[index:index+1]
        observed=counts[(hook['name'],4 if hook['abiId']=='win64.transparent_entry_snapshot.v1' else 1)]
        result.append(dict(hook=hook['name'],reviewedWindowEntries=observed,**{
            'nativeWindowSelected' if scope=='explicitWindowIds' else 'providerLifetimeSelected':selected[0] if selected else None,
            'unattributedWindowSelections' if scope=='explicitWindowIds' else 'unattributedProviderSelections':selected[0]-observed if selected and type(selected[0]) is int else None}))
    return dict(counterScope=scope,observationScope='closedRecordedWindows',hooks=result,provesWindowCompleteness=False)


class MixerFrameCapture:
    def __init__(self, descriptor_offset, *, interval_joins_enabled=True):
        self.descriptor_offset=descriptor_offset
        self.interval_joins_enabled=interval_joins_enabled
        self.source_intervals={};self.source_ordinals={}
        self.publication_ordinals={};self.context_calls={};self.context_active={}
        self.bus_ordinals={};self.bus_resets={};self.mix_inputs={}
        self.published_rows={};self.context_rows={};self.bus_rows={}
        self.publications=[];self.mixes=[];self.resets=[];self.counts=Counter()

    def append(self, collection, item):
        if len(collection)<REPORT_ROW_LIMIT:collection.append(item)
        else:self.counts['reportRowsOmitted']+=1

    def validate_addresses(self, row, facts, fields):
        name=row['hook']
        if not name.endswith(('.busFrameReset','.routingPublication')) and not (name.endswith('.busRouteMix') and row['phase']==2):return
        for i,field in enumerate(fields):
            if facts.get(field['name']) is None:continue
            chain=field.get('pointerOffsets',[])
            if not chain:base=row['args'][field['argIndex']]
            elif name.endswith('.routingPublication'):
                base=facts['primaryOwner'] if field['name'].startswith('owner') else facts['routeHead'] if len(chain)==1 else facts['routeRows']
            else:
                base=facts['busSamplePointer'] if field['kind']=='bytes' else facts['busFirstDescriptor']
            if row['addresses'][i]!=base+field['offset']:
                raise ValueError('mixer frame read address differs from retained storage')
            if field['kind']=='bytes' and row['spanBytes'] and row['spanAddress']!=row['addresses'][i]:
                raise ValueError('mixer frame span address differs from retained storage')

    def entry(self, row, facts):
        name=row['hook'];context=row['args'][0];key=(row['windowId'],context)
        if name.endswith('.contextSourceSampleBuffer') and row['phase']==1:
            if not self.interval_joins_enabled:return
            self.begin_context_call('source',key,row)
            self.source_intervals.pop(key,None)
            self.clear_published_context(key)
        elif name.endswith('.routingPublication') and row['phase']==1:
            self.clear_published_context(key)
            row_key=(row['windowId'],facts.get('routeRows'))
            self.remove_published_row(row_key)
            if self.interval_joins_enabled:
                self.begin_context_call('publication',key,row)
        elif name.endswith('.contextFrameRelease'):
            self.source_intervals.pop(key,None)
            for call_key in self.context_active.get(('source',key),()):
                self.context_calls[call_key]['invalidated']=True
            for row_key in self.context_rows.get(key,()):
                if row_key in self.published_rows:self.published_rows[row_key]['releaseObservedAfterPublication']=True
            self.counts['observedSourceReleaseEntries']+=1
        elif name.endswith('.busFrameReset') and row['phase']==1:
            if not self.interval_joins_enabled:return
            if len(self.bus_resets)>=100000:raise ValueError('bus reset interval bound exceeded')
            if key in self.bus_resets:raise ValueError('overlapping reset of the same bus')
            self.bus_resets[key]=row['captureId']
            self.clear_published_bus(key)
        elif name.endswith('.busRouteMix') and row['phase']==1:
            if len(self.mix_inputs)>=100000:raise ValueError('pending bus mix bound exceeded')
            descriptor=facts.get('firstRowDescriptor')
            source=self.source_intervals.get((row['windowId'],descriptor-self.descriptor_offset)) if descriptor else None
            matched=bool(source and source['threadId']==row['threadId'] and source['descriptor']==descriptor and
                (source['samplePointer'],source['format'],source['validFrames'])==
                (facts.get('firstRowSamplePointer'),facts.get('firstRowFormat'),facts.get('firstRowValidFrames')))
            publication=self.published_rows.get((row['windowId'],facts.get('firstMixRow')))
            projected=publication['sourceCandidate'] if publication else None
            publication_matches=bool(projected and publication['busKey']==key and projected['threadId']==row['threadId'] and
                (projected['descriptor'],projected['samplePointer'],projected['format'],projected['validFrames'])==
                (descriptor,facts.get('firstRowSamplePointer'),facts.get('firstRowFormat'),facts.get('firstRowValidFrames')))
            self.mix_inputs[(row['windowId'],row['captureId'])]=dict(bus=key,
                resetOrdinal=self.bus_ordinals.get(key),resetInProgress=key in self.bus_resets,
                firstRow=dict(facts),sourceCandidate=dict(source) if matched else None,
                publishedSourceCandidate=dict(publication) if publication_matches else None)

    def clear_published_bus(self, key):
        for row_key in self.bus_rows.pop(key,set()):
            publication=self.published_rows.pop(row_key,None)
            if publication:self.context_rows.get(publication['contextKey'],set()).discard(row_key)

    def remove_published_row(self, row_key):
        publication=self.published_rows.pop(row_key,None)
        if publication:
            self.context_rows.get(publication['contextKey'],set()).discard(row_key)
            self.bus_rows.get(publication['busKey'],set()).discard(row_key)

    def clear_published_context(self, key):
        for row_key in tuple(self.context_rows.pop(key,set())):
            self.remove_published_row(row_key)

    def begin_context_call(self, kind, key, row):
        ordinals=self.source_ordinals if kind=='source' else self.publication_ordinals
        call_key=(row['windowId'],row['captureId']);active_key=(kind,key)
        if (key not in ordinals and len(ordinals)>=100000) or len(self.context_calls)>=100000:
            raise ValueError('context invocation bound exceeded')
        if call_key in self.context_calls:raise ValueError('duplicate context invocation')
        ordinals[key]=ordinals.get(key,0)+1
        active=self.context_active.setdefault(active_key,set())
        for previous in active:self.context_calls[previous]['overlapping']=True
        self.context_calls[call_key]=dict(kind=kind,contextKey=key,ordinal=ordinals[key],
            overlapping=bool(active),invalidated=False,
            sourceCandidate=dict(self.source_intervals[key]) if kind=='publication' and key in self.source_intervals else None)
        active.add(call_key)

    def finish_context_call(self, kind, key, row):
        call_key=(row['windowId'],row['captureId'])
        call=self.context_calls.pop(call_key,None)
        if call is None or call['kind']!=kind or call['contextKey']!=key:
            raise ValueError('context completion lacks its invocation entry')
        active_key=(kind,key);active=self.context_active[active_key]
        active.remove(call_key)
        if not active:self.context_active.pop(active_key)
        ordinals=self.source_ordinals if kind=='source' else self.publication_ordinals
        if call['overlapping'] or call['invalidated'] or call['ordinal']!=ordinals[key]:
            self.counts[kind+'IntervalsWithheld']+=1
            return None
        return call

    def withhold_interval_joins(self):
        """A later stream diagnostic also invalidates earlier absence claims."""
        self.interval_joins_enabled=False
        self.source_intervals.clear();self.published_rows.clear()
        self.context_rows.clear();self.bus_rows.clear()
        self.publications.clear()
        self.counts['withheldPublicationIntervalCandidates']=self.counts.pop('publicationCurrentSourceCandidates',0)
        for mix in self.mixes:
            mix.update(sourceCandidate=None,publishedSourceCandidate=None,
                sourceIntervalUnchangedDuringMix=False,noObservedResetDuringMix=False)

    def completed(self, before, row, facts, input_facts, *, inside_closed_window=True):
        name=row['hook'];key=(row['windowId'],before['args'][0])
        if name.endswith('.contextSourceSampleBuffer'):
            call=self.finish_context_call('source',key,row) if self.interval_joins_enabled else None
            if row['phase']!=2:return
            if before['args'][1]!=before['args'][0]+self.descriptor_offset:
                raise ValueError('source sample descriptor differs from owned context layout')
            if not self.interval_joins_enabled:return
            if call is None or not inside_closed_window:return
            if not all(facts.get(k) for k in ('primaryOwner','ownerPlaybackSerial','ownerStoredSource','samplePointer','channelConfiguration','validFrames')) or facts.get('ownerExternalAllocation') is None:
                self.counts['incompleteOrEmptySourceSamples']+=1
                return
            self.source_intervals[key]=dict(context=before['args'][0],descriptor=before['args'][1],threadId=row['threadId'],
                writeOrdinal=call['ordinal'],sampleCaptureId=row['captureId'],sampleSequence=row.get('sequence'),
                primaryOwner=facts.get('primaryOwner'),serial=facts.get('ownerPlaybackSerial'),
                storedSource=facts.get('ownerStoredSource'),allocation=facts.get('ownerExternalAllocation'),
                samplePointer=facts.get('samplePointer'),format=facts.get('channelConfiguration'),validFrames=facts.get('validFrames'),
                prefixSha256=hashlib.sha256(bytes.fromhex(row['spanHex'])).hexdigest(),prefixFirst16Hex=row['spanHex'][:32],
                secondPlaneFirst16Hex=b''.join(struct.pack('<I',facts['secondPlaneWord'+str(i)]) for i in range(4)).hex()
                    if all(facts.get('secondPlaneWord'+str(i)) is not None for i in range(4)) else None)
        elif name.endswith('.routingPublication'):
            call=self.finish_context_call('publication',key,row) if self.interval_joins_enabled else None
            if row['phase']!=2:return
            descriptor=facts.get('publishedFirstDescriptor')
            if facts.get('routeRowCount') and descriptor is not None and descriptor!=before['args'][0]+self.descriptor_offset:
                raise ValueError('publication differs from the native context descriptor address')
            candidate=call['sourceCandidate'] if call else None
            current=self.source_intervals.get(key)
            identity=('primaryOwner','ownerPlaybackSerial','ownerStoredSource','ownerExternalAllocation')
            if current and any(facts.get(k)!=current[v] for k,v in zip(identity,('primaryOwner','serial','storedSource','allocation'))):
                self.source_intervals.pop(key,None);current=None
            matched=bool(inside_closed_window and facts.get('routeRowCount') and candidate and current and current['writeOrdinal']==candidate['writeOrdinal'] and
                all(input_facts.get(k)==facts.get(k) for k in identity) and candidate['threadId']==row['threadId'] and candidate['descriptor']==descriptor and
                (candidate['primaryOwner'],candidate['serial'],candidate['storedSource'],candidate['allocation'])==
                (facts.get('primaryOwner'),facts.get('ownerPlaybackSerial'),facts.get('ownerStoredSource'),facts.get('ownerExternalAllocation')))
            self.counts['completedPublications']+=1
            self.counts['publicationCurrentSourceCandidates']+=matched
            if matched:
                if len(self.publications)<128:
                    self.publications.append(dict(publicationCaptureId=row['captureId'],sourceCandidate=dict(candidate),firstRouteReads=dict(facts)))
                row_key=(row['windowId'],facts.get('routeRows'));bus_key=(row['windowId'],facts.get('routeBus'))
                if row_key[1] and bus_key[1] and bus_key not in self.bus_resets and inside_closed_window:
                    if row_key not in self.published_rows and len(self.published_rows)>=100000:raise ValueError('published route row bound exceeded')
                    previous=self.published_rows.get(row_key)
                    if previous:
                        self.context_rows.get(previous['contextKey'],set()).discard(row_key)
                        self.bus_rows.get(previous['busKey'],set()).discard(row_key)
                    self.published_rows[row_key]=dict(publicationCaptureId=row['captureId'],contextKey=key,busKey=bus_key,
                        sourceCandidate=dict(candidate),releaseObservedAfterPublication=False,resetOrdinal=self.bus_ordinals.get(bus_key))
                    self.context_rows.setdefault(key,set()).add(row_key);self.bus_rows.setdefault(bus_key,set()).add(row_key)
        elif name.endswith('.busFrameReset'):
            if self.interval_joins_enabled and self.bus_resets.pop(key,None)!=row['captureId']:
                raise ValueError('bus reset completion lacks its active interval')
            self.clear_published_bus(key)
            if row['phase']!=2:
                self.bus_ordinals.pop(key,None)
                self.counts['unwoundResets']+=1
                return
            if facts.get('busInputCount') and (facts.get('busSamplePointer')!=0 or facts.get('busValidFrames')!=0):
                raise ValueError('completed retained first bus input was not cleared')
            if key not in self.bus_ordinals and len(self.bus_ordinals)>=100000:raise ValueError('bus reset ordinal bound exceeded')
            self.bus_ordinals[key]=self.bus_ordinals.get(key,0)+1
            self.counts['completedBusResets']+=1
            if len(self.resets)<128:
                self.resets.append(dict(resetCaptureId=row['captureId'],bus=key[1],resetOrdinal=self.bus_ordinals[key],
                    before=dict(input_facts),after=dict(facts)))
        elif name.endswith('.busRouteMix'):
            entry=self.mix_inputs.pop((row['windowId'],row['captureId']),None)
            if not entry:raise ValueError('bus mix completion lacks its input interval')
            if row['phase']!=2:return
            if row['returnValue']!=before['args'][1]:raise ValueError('bus mix returned different caller result storage')
            raw=bytes.fromhex(row['spanHex'])
            values=struct.unpack('<'+str(len(raw)//4)+'f',raw) if raw and len(raw)%4==0 else ()
            unchanged=self.interval_joins_enabled and inside_closed_window and not entry['resetInProgress'] and key not in self.bus_resets and entry['resetOrdinal']==self.bus_ordinals.get(key)
            source=entry['sourceCandidate']
            current=self.source_intervals.get((row['windowId'],source['context'])) if source else None
            source_unchanged=inside_closed_window and current is not None and current['writeOrdinal']==source['writeOrdinal']
            publication=entry['publishedSourceCandidate']
            retained=self.published_rows.get((row['windowId'],entry['firstRow'].get('firstMixRow'))) if publication else None
            published_unchanged=unchanged and retained is not None and retained['publicationCaptureId']==publication['publicationCaptureId']
            self.append(self.mixes,dict(windowId=row['windowId'],mixCaptureId=row['captureId'],bus=key[1],resultStoragePointer=row['returnValue'],
                gainPairArray=before['extraArgument'],sixthArgument=before['sixthArgument'],
                combinedFirstRowGains=combined_first_row_gains(entry['firstRow']),
                firstInput=entry['firstRow'],sourceCandidate=source if source_unchanged else None,resetOrdinal=entry['resetOrdinal'],
                publishedSourceCandidate=dict(retained) if published_unchanged else None,sourceIntervalUnchangedDuringMix=source_unchanged,
                noObservedResetDuringMix=unchanged,output=dict(facts),outputPrefixBytes=len(raw),
                outputPrefixFirst16Hex=raw[:16].hex(),
                outputPrefixSha256=hashlib.sha256(raw).hexdigest(),finiteNonzeroOutput=bool(values and all(math.isfinite(x) for x in values) and any(values))))

    def publish(self):
        return dict(schema='endfield.audio-mixer-frame-witness.v7',intervalJoinsEnabled=self.interval_joins_enabled,publications=self.publications,mixes=self.mixes,resets=self.resets,
            counts=dict(self.counts),publicationExamplesBound=128,resetExamplesBound=128,busResetOrdinals=[dict(windowId=k[0],bus=k[1],completedResets=v) for k,v in self.bus_ordinals.items()],
            openMixCalls=len(self.mix_inputs),openResetCalls=len(self.bus_resets),openContextCalls=len(self.context_calls),wholeEventToDeviceClaim=False,
            evidenceBoundary=dict(direct='Completed same-invocation mixer inputs/output and caller result-storage return, native descriptor publication and first retained bus-input reset observations. Return storage is not a proved task or asynchronous dependency.',
                conditional='Current source candidates require a same-thread observed write/release interval and identical descriptor/sample/format/frame fields. Separate published candidates require a completed native first-row publication with current owner identity, matching bus/row/descriptor/sample fields and no observed new source write or bus reset. Source release after publication is explicit and does not certify continued allocation validity. Reset ordinals count observed resets, not global native frames. Unsampled endpoints and a loss-free closed stream are prerequisites; other writers and concurrent lifetimes remain conditions.',
                unresolved='Whole Event contribution, full rows/channels/effects, allocation/task generations, cross-thread handoffs, other descriptor writers and device frame identity.'))
