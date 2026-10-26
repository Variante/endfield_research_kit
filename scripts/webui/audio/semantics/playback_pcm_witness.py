"""Exact nonzero planar prefixes against an explicitly interleaved float stream.

Evidence and admission boundary:

Later source-output pairs retain constructed primary addresses and their
checked embedded-owner adjustment. This is conditional continuity: constructor
entries are retained, but unobserved destruction, other constructor families
and reuse remain lifetime gaps. Native single-descriptor selection also retains
complete voice paths beyond the shorter managed text field. Truncated managed
path text does not invalidate an intact Event/playing-ID pair; its text
identity stays incomplete. Complete native paths match full external-sector
keys through the selected-build hashing gate, while ordinary source words
remain sound-sector low-word candidates. Sampled route records link PCM
contexts with bus inputs, without proving a simultaneous complete mixer graph.

A finite nonzero live voice PCM prefix now exactly matches float bytes produced
by original native codec execution from the matching physical package WEM. This
establishes sampled content agreement under the named ownership and package
conditions. It does not establish the whole live buffer, allocation generation
or chosen backing occurrence. The isolated run supplies allocation and a setup
lock and covers a bounded decoded extent; it is not a live device run. Audio's
`playback_pcm_witness` domain performs byte-exact channel-plane comparisons and
rejects silence/nonfinite prefixes as identity witnesses. Device acceptance
still requires direct output-buffer and COM result observation: the original
sink ignores the release result, and a tolerated GetBuffer error can leave its
invalid flag unchanged.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct


def compare_prefix(path, prefix_hex, *, channels, channel_index=0, max_bytes=64<<20):
    """Only compare supplied bytes; codec execution and native admission are external.

    Positions are frames within the supplied decoded extent. Equal sparse bytes
    do not identify the live backing file or certify whole-stream equality.
    """
    if type(channels) is not int or not 1<=channels<=32 or type(channel_index) is not int or not 0<=channel_index<channels:
        raise ValueError('explicit bounded channel layout required')
    prefix=bytes.fromhex(prefix_hex)
    if not 4<=len(prefix)<=256 or len(prefix)%4:
        raise ValueError('prefix must contain 1..64 complete float32 samples')
    values=struct.unpack('<'+str(len(prefix)//4)+'f',prefix)
    if not all(math.isfinite(value) for value in values) or not any(values):
        raise ValueError('zero or nonfinite prefixes cannot witness content identity')
    path=Path(path);before=path.stat()
    if not 0<before.st_size<=max_bytes or before.st_size%(channels*4):
        raise ValueError('decoded stream exceeds bounds or ends within a frame')
    raw=path.read_bytes();after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('decoded stream changed during comparison')
    plane=b''.join(raw[at:at+4] for at in range(channel_index*4,len(raw),channels*4))
    positions=[];start=0
    while True:
        at=plane.find(prefix,start)
        if at<0:break
        if at%4==0:positions.append(at//4)
        start=at+1
    return dict(status='exactPrefixMatch' if positions else 'prefixNotEqual',channels=channels,channelIndex=channel_index,
        suppliedFrames=len(raw)//4//channels,decodedFloatSha256=hashlib.sha256(raw).hexdigest(),
        prefixBytes=len(prefix),prefixSha256=hashlib.sha256(prefix).hexdigest(),positions=positions,
        evidenceBoundary='Exact finite nonzero prefix equality within the supplied decoded extent only. Native admission, live allocation/file selection, whole PCM equality, mixing and device output are separate.')
