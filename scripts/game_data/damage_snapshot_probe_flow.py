"""Actual compiled probe: exact register/stack/page-write boundaries."""
import struct
import hashlib
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.damage_snapshot_cache_flow import _require


def check_probe_bytes(raw,*,pointer,end,program):
    frame=program['localFrameBytes'];gs=program['anonymousGsQwordOffset'];mask=program['lowWordMask'];step=program['pageStep']
    _require(type(frame) is int and 16<=frame<=112 and frame%16==0 and type(gs) is int and 0<=gs<=0x7fffffff
             and type(step) is int and 0<step<=0x10000 and step&(step-1)==0 and mask==(-step)&0xffff,
             'snapshot-probe-program','reviewed page/word/frame grammar',program)
    forms=[('subRsp',b'\x48\x83\xec'+bytes([frame])),('saveR10',b'\x4c\x89\x14\x24'),('saveR11',b'\x4c\x89\x5c\x24\x08'),
           ('zeroR11',b'\x4d\x33\xdb'),('callerRsp',b'\x4c\x8d\x54\x24'+bytes([frame+8])),('subtractInputRax',b'\x4c\x2b\xd0'),
           ('clampCarryR10',b'\x4d\x0f\x42\xd3'),('gsQword',b'\x65\x4c\x8b\x1c\x25'+struct.pack('<i',gs)),
           ('unsignedCompare',b'\x4d\x3b\xd3'),('fastReturnEdge',b'\x73\x16'),
           ('alignLowWord',b'\x66\x41\x81\xe2'+struct.pack('<H',mask)),('decrementPage',b'\x4d\x8d\x9b'+struct.pack('<i',-step)),
           ('zeroByte',b'\x41\xc6\x03\x00'),('pageCompare',b'\x4d\x3b\xd3'),('retryEdge',b'\x75\xf0'),
           ('restoreR10',b'\x4c\x8b\x14\x24'),('restoreR11',b'\x4c\x8b\x5c\x24\x08'),('addRsp',b'\x48\x83\xc4'+bytes([frame])),('ret',b'\xc3')]
    _require(end-pointer==len(raw),'snapshot-probe-owned-extent','exact raw owned extent',[end-pointer,len(raw)])
    offsets={};at=0
    for name,encoding in forms:
        _require(raw[at:at+len(encoding)]==encoding,'snapshot-probe-instruction',[name,encoding.hex()],[at,raw[at:at+len(encoding)].hex()])
        offsets[name]=at;at+=len(encoding)
    _require(at==len(raw),'snapshot-probe-full-coverage',len(raw),at)
    for edge,target in (('fastReturnEdge','restoreR10'),('retryEdge','decrementPage')):
        offset=offsets[edge];actual=offset+2+int.from_bytes(raw[offset+1:offset+2],'little',signed=True)
        _require(actual==offsets[target],'snapshot-probe-edge',[edge,offsets[target]],actual)
    return {'selectedInstructionCount':len(forms),'ownedBodyBytes':len(raw),'instructionOffsets':offsets,
            'raxWritten':False,'raxPreservedOnNormalReturn':True,'raxReadOnlyUse':'full64 source in SUB R10,RAX',
            'explicitCalls':[],'lowWordAlignmentBits':16,'alignInstructionBytes':6,
            'segmentRead':'actual GS base + anonymous offset, qword; segment prefix retained',
            'explicitWrites':[{'role':'saved R10 local','widthBytes':8},{'role':'saved R11 local','widthBytes':8},{'role':'derived page zero','widthBytes':1}],
            'explicitFrameSubAddBytes':frame,'retReturnAddressPopBytes':8,
            'allNormalReturnPathsChecked':True,'threadStorageOrPageAllocationExtentProved':False}


def probe_conditions(entry_rsp,allocation,gs_word,program):
    frame=program['localFrameBytes'];step=program['pageStep']
    valid=all(type(v) is int and 0<=v<1<<64 for v in (entry_rsp,allocation,gs_word)) and entry_rsp>=frame and entry_rsp+8<1<<64
    if not valid:return {'validNonwrappingInputs':False,'savedFrameAndReturnPreserved':False}
    caller_rsp=entry_rsp+8;target=caller_rsp-allocation if allocation<=caller_rsp else 0
    fast=target>=gs_word;aligned_target=target&~(step-1)
    loop_finite=fast or (gs_word%step==0 and gs_word>aligned_target and (gs_word-aligned_target)%step==0)
    count=0 if fast else (gs_word-aligned_target)//step if loop_finite else None
    protected={'savedR10':(entry_rsp-frame,8),'savedR11':(entry_rsp-frame+8,8),'returnAddress':(entry_rsp,8)}
    def hit(address,width):
        if fast:return False
        if not loop_finite:return None
        # Writes are aligned_target + j*step, j in [0,count-1].
        lo=max(0,(address-aligned_target+step-1)//step)
        hi=min(count-1,(address+width-1-aligned_target)//step)
        return lo<=hi
    overlap={role:hit(address,width) for role,(address,width) in protected.items()}
    return {'validNonwrappingInputs':True,'clampedTarget':target,'loopAlignedTarget':None if fast else aligned_target,'fastReturnSelected':fast,
            'finiteNonwrappingLoopCondition':loop_finite,'pageWriteCount':count,
            'pageWriteAddressFormula':'GS qword - k*pageStep, k=1..pageWriteCount',
            'protectedActualRanges':{k:{'address':a,'widthBytes':n} for k,(a,n) in protected.items()},
            'derivedPageWriteOverlaps':overlap,'savedFrameAndReturnPreserved':loop_finite and all(value is False for value in overlap.values()),
            'conditionsRemain':'valid readable GS qword and local/page storage, normal returning execution, no external/concurrent interference'}


def check_process_probe_prologue(raw,*,pointer):
    fixed=[b'\x4c\x89\x4c\x24\x20',b'\x48\x89\x54\x24\x10',b'\x48\x89\x4c\x24\x08',
           b'\x53',b'\x56',b'\x57',b'\x41\x54',b'\x41\x55',b'\x41\x56',b'\x41\x57']
    at=0
    for encoding in fixed:
        _require(raw[at:at+len(encoding)]==encoding,'snapshot-probe-prologue-instruction',encoding.hex(),raw[at:at+len(encoding)].hex());at+=len(encoding)
    _require(raw[at:at+1]==b'\xb8' and len(raw)>=at+13,'snapshot-probe-allocation-request','MOV EAX imm32/CALL/SUB RSP,RAX',raw[at:].hex())
    allocation=int.from_bytes(raw[at+1:at+5],'little');at+=5
    call=raw[at:at+5];_require(call[:1]==b'\xe8','snapshot-probe-actual-call','direct CALL',call.hex())
    helper=relative_branch_target(call,pointer+at,source='processFrameProbe');at+=5
    _require(raw[at:at+3]==b'\x48\x2b\xe0','snapshot-probe-caller-sp-sub','full64 SUB RSP,RAX',raw[at:at+3].hex());at+=3
    return {'prologueByteCount':at,'savedIncomingThisEntryStackOffset':8,'requestedAllocationBytes':allocation,
            'allocationMoveZeroExtendsRax':True,'actualProbeHelper':hex(helper),'nonvolatilePushBytes':56,
            'spDeltaAfterNormallyReturningPreservedRaxProbe':56+allocation,
            'savedThisCurrentStackOffsetUnderUnchangedFrame':64+allocation,
            'normalHelperReturnAndUnchangedFrameObserved':False}


def check_snapshot_probe(index,spec):
    body=index.body(spec['type'],spec['method'])
    selected=NativeReferenceContext(index.image,index=index)
    _require(not selected.is_value_type(spec['type']) and index.parameter_location(body.pointer,body.symbol,'this')==('register','rcx'),
             'snapshot-probe-process-this-abi','ordinary instance action this in RCX',body.symbol)
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==body.symbol]
    _require(bool(methods) and all(not m.flags&0x10 for m in methods),'snapshot-probe-process-instance','named instance definition',body.symbol)
    prologue=check_process_probe_prologue(index.pe.bytes_at_va(body.pointer,64),pointer=body.pointer)
    pointer=int(prologue['actualProbeHelper'],16)
    _require(pointer in index.extents and 0<index.extents[pointer]-pointer<=512,'snapshot-probe-helper-owned-entry','exact bounded pdata helper',hex(pointer))
    end=index.extents[pointer];raw=index.pe.bytes_at_va(pointer,end-pointer)
    proof=check_probe_bytes(raw,pointer=pointer,end=end,program=spec['anonymousProgram'])
    return {**proof,**prologue,'helperEntry':hex(pointer),'helperOwnedEnd':hex(end),'helperBodySha256':hashlib.sha256(raw).hexdigest(),
            'symbol':body.symbol,'claim':'snapshotActualProcessProbeRaxAndConditionalFrame',
            'boundary':'The ProcessDamage raw entry prologue requests an immediate zero-extended RAX allocation, calls the actual compiled helper and performs full64 SUB RSP,RAX. The helper has a complete exact owned instruction graph with no RAX destination on any path; it reads RAX only to derive an unsigned/clamped target. Its actual GS-prefixed anonymous qword read, true six-byte low-word AND, derived one-byte page stores, all edges and restoring RET are checked independently of generic decoder text. Normal plain execution preserves RAX; SP add/sub and RET are complete. Restored saved R10/R11 bits and original return control additionally require every actual derived page-write range disjoint from saved locals/return storage, valid readable/writable nonwrapping GS/local/page storage and no interference. Page-loop finite/aligned threshold and storage/backing meanings are conditions or unresolved. Under those conditions the caller allocation/frame arithmetic is exact; frame continuity to a later ProcessDamage fragment, its local index writers and snapshot compact-index equality are not inferred.'}
