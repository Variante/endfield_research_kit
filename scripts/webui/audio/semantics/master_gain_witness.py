"""Bounded first-plane gain equation inside a completed master invocation.

Evidence and admission boundary:

The `audio-master-stage` observation adds the first master input descriptor,
retained gain pair, output format/mode/processed flags, entry rounding and
before/after PCM to the accepted consumer/device observations. Its reviewed
contract borrows authenticated master, padding and gain bodies from the
existing pipeline owner. A constant first-plane comparison requires one
matching stereo descriptor, ordinary unprocessed entry, unchanged input/gain
fields, completed processing, identical conversion input and closed loss-free
recording. The recipe distinguishes an intervening transformation before master
entry from the master gain itself. A completed loss-free recording now admits
the bounded first-plane equation and successful sink/device prefix chains. The
retained master gains in this cohort are unity: observed input prefixes remain
unchanged through master processing and match its nested conversion input.
Independent original-row checks confirm descriptor/storage identity, processing
flags, entry rounding, ordered nesting and byte-equal successful render-client
handoffs. Unlinked master scopes remain unattributed. Last sampled same-bus
mixes have matching descriptor/sample storage but different prefixes already at
master entry. The differences therefore precede this master gain stage;
sampling still prevents a complete generation join or attribution to a
particular upstream writer or effect. The next offline review belongs to the
post-mix bus task, descriptor/effect processing and its path into master entry,
before another recipe is requested. Extended paths, ramps and incomplete reads
remain withheld with named reasons. Full filters, all channels, concurrent
allocation lifetimes and individual Event-to-device contribution remain open;
accepted master and sink handoffs are reused without another identical run.
"""
from __future__ import annotations

import math
import struct


def compare_master_prefix(before, after, *, previous_gain_bits, target_gain_bits, mxcsr):
    base=dict(schema='endfield.master-first-plane-gain-prefix.v1',wholeEventToDeviceClaim=False,coveredChannels=[0],comparedFrames=0)
    def withheld(status):return dict(base,status=status)
    if type(mxcsr) is not int or not 0<=mxcsr<2**32 or mxcsr&0x6000:return withheld('nearestRoundingNotObserved')
    if any(type(w) is not int or not 0<=w<2**32 for w in (previous_gain_bits,target_gain_bits)):return withheld('gainWordsInvalid')
    gains=struct.unpack('<2f',struct.pack('<2I',previous_gain_bits,target_gain_bits))
    if not all(math.isfinite(g) for g in gains):return withheld('nonfiniteGain')
    if gains[0]!=gains[1]:return withheld('gainRampUnsupported')
    if any(0<abs(g)<2**-126 for g in gains):return withheld('subnormalPolicyUnsupported')
    a,b=bytes.fromhex(before),bytes.fromhex(after)
    if not 0<len(a)==len(b)<=16 or len(a)%4:return withheld('boundedPrefixesIncomplete')
    mismatches=[];nonzero=False;signed_zero=0
    for i in range(len(a)//4):
        source,actual=struct.unpack_from('<f',a,i*4)[0],struct.unpack_from('<f',b,i*4)[0]
        if not math.isfinite(source) or not math.isfinite(actual):return withheld('nonfiniteSamples')
        if 0<abs(source)<2**-126:return withheld('subnormalPolicyUnsupported')
        try:expected=struct.unpack('<f',struct.pack('<f',source*gains[0]))[0]
        except OverflowError:return withheld('floatRangeUnsupported')
        if not math.isfinite(expected) or 0<abs(expected)<2**-126:return withheld('floatRangeUnsupported')
        nonzero=nonzero or expected!=0 or actual!=0
        if expected!=actual:mismatches.append(dict(frame=i,expected=expected,actual=actual))
        elif expected==0 and struct.pack('<f',expected)!=b[i*4:i*4+4]:signed_zero+=1
    return dict(base,status='prefixDiffers' if mismatches else 'exactFiniteNonzeroMasterGainPrefix' if nonzero else 'zeroPrefixOnly',
        comparedFrames=len(a)//4,gain=gains[0],mismatches=mismatches,signedZeroDifferenceCount=signed_zero,
        evidenceBoundary='Observed first master input times its observed constant per-frame gain explains these first-plane values under admitted nearest rounding. Native path/descriptor/call admission, other channels, whole buffers and upstream Event contribution remain separate.')


def admitted_master_comparison(before, row, initial, final, child, selection):
    base=dict(wholeEventToDeviceClaim=False)
    def withheld(status, **detail):return dict(base,status=status,**detail)
    required=('busInputs','busInputCount','firstInputOwner','firstInputSamplePointer','firstInputFormat','firstInputCapacity','firstInputValidFrames',
        'firstInputPreviousGainBits','firstInputTargetGainBits','outputNodeFormat','outputNodeExtended','outputNodeProcessed')
    if row['phase']!=2:return withheld('unwoundMaster')
    if not before.get('observationWindowOpen') or not row.get('observationWindowOpen'):return withheld('outsideClosedWindow')
    if before.get('roundingModeSampled') is not True:return withheld('masterRoundingNotObserved')
    missing=[k for k in required if initial.get(k) is None]
    if missing:return withheld('masterInputReadsIncomplete',fields=missing)
    if initial['busInputCount']!=1 or initial['outputNodeExtended']!=0 or initial['outputNodeProcessed']!=0:return withheld('masterPathNotSelected')
    if any(initial[k]!=selection[v] for k,v in [('firstInputFormat','format'),('outputNodeFormat','format'),('firstInputCapacity','capacityFrames'),('firstInputValidFrames','validFrames')]):return withheld('masterFormatOrExtentUnsupported')
    changed=[k for k in required if k!='outputNodeProcessed' and final.get(k)!=initial[k]]
    if changed:return withheld('masterFieldsChanged',fields=changed)
    if final.get('outputNodeProcessed')!=1:return withheld('masterProcessingNotCompleted')
    if (child['inputDescriptor'],child['inputSamplePointer'])!=(initial['busInputs'],initial['firstInputSamplePointer']):return withheld('masterConversionDescriptorDiffers')
    if before['spanAddress']!=initial['firstInputSamplePointer'] or before['spanBytes']!=16 or row['spanBytes']!=16:return withheld('masterInputPrefixIncomplete')
    if row['spanAddress']!=initial['firstInputSamplePointer'] or row['spanHex']!=child['inputPrefixFirst16Hex']:return withheld('masterConvertedInputPrefixDiffers')
    return compare_master_prefix(before['spanHex'],child['inputPrefixFirst16Hex'],previous_gain_bits=initial['firstInputPreviousGainBits'],
        target_gain_bits=initial['firstInputTargetGainBits'],mxcsr=before['mxcsr'])
