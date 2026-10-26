"""Retain same-invocation render-buffer copies without inferring audibility.

Evidence and admission boundary:

The prepared `audio-device` preset extends these playback phases with actual
render-client calls. Its reviewed `wwise_device_capture_native.json` borrows
the complete sink caller, interface identity and virtual slots from the
voice-pipeline owner. Preparation checks the virtual-call instructions against
the explicitly selected native image. Caller return sites identify eligible
observations; they are not static hook targets. The runtime discovers the
retained client's implementation addresses, installs bounded SDK-typed hooks on
the worker, and preserves each original call and result. GetBuffer captures
HRESULT and reads the returned pointer only on success. ReleaseBuffer carries
that same-client, same-sink GetBuffer identity, samples the copied bytes before
forwarding and retains the actual release result. Late children remain in their
sampled parent's window during normal stop. Bootstrap skips and target-capacity
limits remain visible. Disabled trampolines and bounded target-module
references remain resident until process exit. The device capture now supplies
completed same-sink, same-client GetBuffer and ReleaseBuffer calls. Successful
GetBuffer results return readable nonnull buffers, and the bytes sampled there
before release exactly equal the sampled sink-input bytes. The observed
releases succeed, while the sink retains its non-invalid state. This
establishes the sampled interleaved PCM copy and Windows API submission result,
beyond a normal native sink return. These invocations exercise the matched
stereo format; other formats and failures remain uncovered. Audio's
`device_capture` domain checks selected caller sites, ready implementation
targets, parent/thread/window identity, the successful buffer link, frame
bounds, declared reads, prefix equality and HRESULT bits in the existing
streaming review. It preserves API errors without promoting them to accepted
copies, and rejects missing or changed links. Prefixes and successful release
results cannot prove whole buffers, endpoint processing, complete asynchronous
lifetime or audibility. Individual Event contribution to a mixed device frame
remains unresolved; an earlier source prefix or matching context address does
not supply a frame join.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import math
import struct


class DeviceCapture:
    def __init__(self, hooks, summary):
        self.hooks = hooks
        self.summary = summary.get('deviceOutput', {})
        if not self.summary or type(self.summary.get('hookError')) is not bool:
            raise ValueError('device output summary is missing')
        self.targets = {}
        for target in self.summary.get('targets', []):
            slot = target['slot']
            method = target['method']
            if (type(slot) is not int or not 0 <= slot < 8 or
                    method != ('GetBuffer' if slot < 4 else 'ReleaseBuffer') or
                    not target['readyDuringCapture'] or not target['modulePath'] or
                    not 0 < target['moduleBase'] <= target['target'] < 0x800000000000 or
                    target['moduleBase'] % 4096 or
                    target['target'] != target['moduleBase'] + target['targetRva'] or
                    (method, target['target']) in self.targets):
                raise ValueError('invalid observed device target summary')
            self.targets[(method, target['target'])] = target
        self.sinks = {}
        self.counts = Counter()
        self.get_results = Counter()
        self.release_results = Counter()
        self.copies = []
        self.examples = {}

    def validate_row(self, row):
        hook = self.hooks[row['hook']]
        if hook.get('hookBinding') != 'observedRenderClientVtable':
            return False
        method = row['hook'].rsplit('.', 1)[-1]
        if row['returnAddress'] != row['moduleBase'] + int(hook['rva'], 16):
            raise ValueError('device caller differs from selected native return site')
        if (method, row['deviceTarget']) not in self.targets:
            raise ValueError('device implementation absent from ready target summary')
        return True

    def parent(self, row, pending):
        key = (row['windowId'], row['parentCaptureId'])
        parent = pending.get(key)
        if not parent or not parent[0]['hook'].endswith('.sinkSubmit'):
            raise ValueError('device call lacks an active sampled sink parent')
        before, facts = parent
        if (before['threadId'] != row['threadId'] or
                before['args'][0] != row['deviceSink'] or
                before['invocationStartNs'] != row['windowInvocationStartNs'] or
                before['sequence'] >= row['sequence'] or
                facts.get('renderClient') != row['args'][0]):
            raise ValueError('device client, sink or parent invocation differs')
        if key not in self.sinks:
            if len(self.sinks) >= 100000:
                raise ValueError('device sink observation bound exceeded')
            self.sinks[key] = dict(gets={}, releases=[])
        return before, facts, self.sinks[key]

    def entry(self, row, facts, pending):
        if row['phase'] != 1 or not self.validate_row(row):
            return
        before, sink_facts, scope = self.parent(row, pending)
        if row['hook'].endswith('.GetBuffer'):
            if (facts.get('getBufferTarget') != row['deviceTarget'] or
                    ('ReleaseBuffer', facts.get('releaseBufferTarget')) not in self.targets or
                    facts.get('requestedFrames') != row['args'][1] or
                    facts.get('outputPointerReference') != row['args'][2] or
                    row['args'][1] != sink_facts.get('validFrames') or
                    row['linkedCaptureId'] or row['extraArgument']):
                raise ValueError('GetBuffer inputs differ from sink request or target')
            return
        get = scope['gets'].get(row['linkedCaptureId'])
        if not get:
            raise ValueError('ReleaseBuffer lacks a completed same-sink GetBuffer')
        enter, result, get_facts = get
        buffer = get_facts.get('returnedBuffer')
        if (result['returnValue'] != 0 or not buffer or
                enter['args'][0] != row['args'][0] or
                result['sequence'] >= row['sequence'] or
                enter['values'][1] != row['deviceTarget'] or
                row['extraArgument'] != buffer or facts.get('bufferPointer') != buffer or
                facts.get('releasedFrames') != row['args'][1] or
                row['args'][1] > enter['args'][1] or
                row['args'][1] != sink_facts.get('validFrames') or
                facts.get('releaseFlags') != row['args'][2] or row['args'][2] != 0 or
                row['spanAddress'] != buffer or facts.get('copiedPrefix') != row['spanBytes']):
            raise ValueError('ReleaseBuffer identity, frames, flags or copied address differs')
        if any(item['linkedCaptureId'] == row['linkedCaptureId'] for item in scope['releases']):
            raise ValueError('successful GetBuffer linked to repeated ReleaseBuffer')

    def completed(self, before, row, facts, pending):
        if row['hook'].endswith('.sinkSubmit'):
            scope = self.sinks.pop((row['windowId'], row['captureId']), None)
            if not scope:
                return
            self.counts['completedSinkScopes' if row['phase'] == 2 else 'unwoundSinkScopes'] += 1
            if row['phase'] != 2:
                return
            for item in scope['releases']:
                if len(self.copies) >= 100000:
                    raise ValueError('device copy observation bound exceeded')
                item['sinkInvalidFlag'] = facts.get('invalidFlag')
                item['sinkReturnPrefixUnchanged'] = before['spanHex'] == row['spanHex']
                self.copies.append(item)
            return
        if not self.validate_row(row):
            return
        parent, sink_facts, scope = self.parent(row, pending)
        method = row['hook'].rsplit('.', 1)[-1]
        if row['phase'] != 2:
            self.counts[method + 'Unwind'] += 1
            return
        if facts.get('hresultBits') != row['returnValue']:
            raise ValueError('device HRESULT read differs from actual return value')
        if method == 'GetBuffer':
            if row['returnValue'] == 0 and row['addresses'][1] != row['args'][2]:
                raise ValueError('GetBuffer output pointer read address differs')
            self.get_results[row['returnValue']] += 1
            scope['gets'][row['captureId']] = (before, row, facts)
            return
        self.release_results[row['returnValue']] += 1
        # Validate the entry again here so a rejected entry cannot produce a witness.
        entry_facts = dict(releasedFrames=before['values'][0], releaseFlags=before['values'][1],
                           bufferPointer=before['values'][2], copiedPrefix=before['values'][3])
        if before['states'] != [1, 1, 1, 1]:
            raise ValueError('ReleaseBuffer copy fields were not successfully read')
        self.entry(before, entry_facts, pending)
        equal = bool(before['spanBytes'] and before['spanHex'] == parent['spanHex'])
        span = bytes.fromhex(before['spanHex'])
        floats = struct.unpack('<' + str(len(span) // 4) + 'f', span) if span and len(span) % 4 == 0 else ()
        finite_nonzero = bool(floats and all(math.isfinite(n) for n in floats) and any(floats))
        item = dict(windowId=row['windowId'], threadId=row['threadId'],
                    sinkCaptureId=parent['captureId'], getCaptureId=row['linkedCaptureId'],
                    releaseCaptureId=row['captureId'], sink=row['deviceSink'], client=row['args'][0],
                    inputBuffer=sink_facts.get('samplePointer'), renderBuffer=before['extraArgument'],
                    frames=before['args'][1], channelConfiguration=sink_facts.get('channelConfiguration'),
                    releaseHresultBits=row['returnValue'], copiedPrefixBytes=len(span),
                    copiedPrefixSha256=hashlib.sha256(span).hexdigest(),
                    sinkPrefixByteEqual=equal, finiteNonzeroPrefix=finite_nonzero,
                    linkedCaptureId=row['linkedCaptureId'])
        scope['releases'].append(item)
        self.examples.setdefault('sameInvocationCopy', dict(sink=parent, releaseEnter=before, releaseResult=row,
                                                            get=scope['gets'][row['linkedCaptureId']]))

    def publish(self):
        accepted = [r for r in self.copies if r['releaseHresultBits'] == 0 and r['sinkPrefixByteEqual']]
        return dict(schema='endfield.audio-device-copy-witness.v1',
                    status='sampledSinkCopyAccepted' if accepted else 'noAcceptedCopyWitness',
                    getHresultCounts={str(k): v for k, v in self.get_results.items()},
                    releaseHresultCounts={str(k): v for k, v in self.release_results.items()},
                    completedSinkCopies=len(self.copies), acceptedByteEqualCopies=len(accepted),
                    acceptedFiniteNonzeroCopies=sum(r['finiteNonzeroPrefix'] for r in accepted),
                    openSinkScopes=len(self.sinks), counters=dict(self.counts),
                    coverage=self.summary, copies=self.copies, examples=self.examples,
                    evidenceBoundary=dict(direct='Same sampled native sink invocation requests a buffer from its retained client, copies byte-equal prefixes and receives the recorded release HRESULT.',
                        conditional='Only completed observed invocations with successful field reads and matching selected caller, client, buffer and frame bounds contribute witnesses. Prefix agreement covers the saved bytes.',
                        unresolved='Unobserved bootstrap calls, complete buffers, endpoint processing and audibility; individual Events cannot be assigned a mixed device prefix without a proved source-to-mixer frame path.'))
