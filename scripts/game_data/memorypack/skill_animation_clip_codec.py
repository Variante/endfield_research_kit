"""Raw36 clip bytes without an object header, null marker or MC7 wrapper.

The owning source proves physical slices and selected nominal layout. This
driver preserves arbitrary IEEE, Boolean and padding bits. Stored clip hashes
are not asset resolution/playback proof, and no enclosing EOF is admitted.
"""
from scripts.game_data.memorypack import skill_animation_clip_raw_sources as owner


def need(check,condition):
    if not condition:raise ValueError('skillAnimationClipCodec.'+check)


def require_capability(cap):
    need('own-selected-raw36-source',cap.get('schema')==owner.SCHEMA and cap.get('status')=='validated'
        and cap.get('typeName')==owner.TYPE and type(cap.get('typeDefinition'))is int
        and cap.get('readMethod')=='ReadUnmanaged'and type(cap.get('readerMethodDefinition'))is int
        and cap['readerMethodDefinition']>=0 and type(cap.get('targetRva'))is int and cap['targetRva']>0
        and all(type(cap.get(k))is int and cap[k]==v for k,v in(('wireBytes',36),('managedBytes',36),('nativeAbiBytes',40)))
        and cap.get('resultAbi')=='hidden-local'and cap.get('contextRegister')=='r8'
        and cap.get('referenceLaneOffsets')==[]and cap.get('paddingByteRanges')==owner.PADDING
        and all(cap.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','fullFrameAndNonvolatilesRestored'))
        and all(cap.get(k)is False for k in('wrapperWireUsed','pointerAliasClaimed','boolBytesNormalized','parentFieldAdmitted','wholeOwnerAdmitted')))
    return cap


def read(reader,capability=owner.CAPABILITY,depth=0):
    need('finite-domain',capability==owner.CAPABILITY)
    need('literal-depth',type(depth)is int and 0<=depth<=64);r=reader;require_capability(r.operation.child(capability))
    need('physical-raw36',r.pos+36<=r.limit);start=r.pos;raw=r.take(36,capability)
    row=dict(kind=capability,start=start,end=r.pos,wireBytes=36,rawHex=raw.hex(),
        fields=dict(montagePathHashBits=raw[:8].hex(),lengthBits=raw[8:12].hex(),framerateBits=raw[12:16].hex(),
            averageSpeedBits=[raw[i:i+4].hex()for i in(16,20,24)],averageAngularSpeedBits=raw[28:32].hex(),
            isHumanoidByte=raw[32],isLoopingByte=raw[33]),paddingHex=raw[34:36].hex(),
        wrapperFramingUsed=False,runtimePlaybackProved=False)
    r.records.append(row);return row
