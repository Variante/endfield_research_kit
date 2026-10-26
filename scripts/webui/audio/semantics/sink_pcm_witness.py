"""Compare the recorded first planar channel with a packed constant-gain prefix."""
from __future__ import annotations

import math
import struct


def compare_first_plane(input_hex, output_hex, *, input_format, output_format,
                        input_frames, output_frames, gain_pair_bits):
    """This is a bounded value equation, not a native branch or whole-frame claim."""
    before, after = bytes.fromhex(input_hex), bytes.fromhex(output_hex)
    if any(len(raw)>256 or len(raw)%4 for raw in (before,after)):
        raise ValueError('sink prefixes must contain bounded complete float32 words')
    if type(gain_pair_bits) is not int or not 0<=gain_pair_bits<1<<64:
        raise ValueError('explicit raw gain-pair bits required')
    base=dict(schema='endfield.sink-first-plane-gain-prefix.v1',wholeOutputClaim=False,
              coveredChannels=[0],inputFrames=input_frames,outputFrames=output_frames)
    if input_format!=output_format or input_frames!=output_frames:
        return dict(base,status='formatOrFrameExtentDiffers',comparedFrames=0)
    channels=input_format&255
    if not 1<=channels<=32 or len(after)%(channels*4):
        return dict(base,status='packedPrefixLayoutUnresolved',comparedFrames=0)
    start,end=struct.unpack('<2f',gain_pair_bits.to_bytes(8,'little'))
    if not math.isfinite(start) or not math.isfinite(end):
        return dict(base,status='nonfiniteGain',comparedFrames=0)
    if start!=end:
        return dict(base,status='gainRampNotCompared',comparedFrames=0)
    count=min(len(before)//4,len(after)//(channels*4),input_frames)
    if count<=0:return dict(base,status='noSamples',comparedFrames=0)
    mismatches=[];nonzero=False
    for frame in range(count):
        source=struct.unpack_from('<f',before,frame*4)[0]
        observed=after[frame*channels*4:frame*channels*4+4]
        value=struct.unpack('<f',observed)[0]
        if not math.isfinite(source) or not math.isfinite(value):
            return dict(base,status='nonfinitePrefix',comparedFrames=frame)
        nonzero=nonzero or source!=0 or value!=0
        try: expected=struct.pack('<f',source*start)
        except OverflowError:return dict(base,status='expectedFloat32Overflow',comparedFrames=frame)
        if expected!=observed and len(mismatches)<8:
            mismatches.append(dict(frame=frame,inputHex=before[frame*4:frame*4+4].hex(),expectedHex=expected.hex(),observedHex=observed.hex()))
    return dict(base,status='prefixDiffers' if mismatches else 'exactFiniteNonzeroFirstPlaneGainPrefixMatch' if nonzero else 'zeroPrefixOnly',
                comparedFrames=count,gain=start,mismatches=mismatches,
                evidenceBoundary='Recorded first-plane input times recorded constant gain, rounded to float32, equals the saved packed first-channel samples. Other channels, complete buffers, actual native branch selection, frame generations and device attribution are separate.')
