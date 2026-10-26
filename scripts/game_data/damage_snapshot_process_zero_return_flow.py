"""Bool proxy zero branch and complete actual raw epilogue."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check_zero_branch(raw,pointer,bool_slot):
    prefix=b'\x0f\x28\xfe\x80\x7c\x24'+bytes([bool_slot])+b'\x00\x0f\x84'
    _require(len(raw)==14 and raw[:10]==prefix,'process-zero-proxy-branch','XMM6 bits->XMM7/CMP local byte0/JE',raw.hex())
    return {'zeroTarget':pointer+14+int.from_bytes(raw[10:14],'little',signed=True),'nonzeroFallthrough':pointer+14,
            'boolReadWidthBytes':1,'boolLocalDisp8':bool_slot,'xmmTemporaryCopy':'XMM6 full128 -> XMM7 before out-byte selection'}

def check_zero_return(raw,pointer):
    _require(len(raw)==4 and raw[:3]==b'\x32\xc0\xeb','process-zero-al','XOR AL,AL/direct short JMP',raw.hex())
    return {'epilogueTarget':pointer+4+int.from_bytes(raw[3:4],'little',signed=True),'returnedAl':0,'upperRaxBitsZeroProved':False}

def check_epilogue(raw,pointer,frame):
    forms=[b'\x4c\x8d\x9c\x24'+struct.pack('<i',frame)]
    forms.extend(bytes.fromhex(s) for s in ('410f2873f0','410f287be0','450f2843d0','450f284bc0','450f2853b0','450f285ba0','450f286390','450f286b80','450f28b370ffffff','450f28bb60ffffff',
                                            '498be3','415f','415e','415d','415c','5f','5e','5b','c3'))
    at=0
    for encoding in forms:
        _require(raw[at:at+len(encoding)]==encoding,'process-zero-epilogue',encoding.hex(),raw[at:at+len(encoding)].hex());at+=len(encoding)
    _require(len(raw)==at,'process-zero-epilogue-full-coverage',at,len(raw))
    return {'selectedReturnEnd':pointer+at,'frameBaseAdvanceBytes':frame,'popNonvolatileBytes':56,'retReturnAddressPopBytes':8,
            'explicitRaxOrAlDestinations':[],'xmmLoadRegisters':list(range(6,16)),
            'conditions':'valid aligned XMM save ranges, valid GPR pop/return ranges containing appropriate saved bits, unchanged actual frame and no interference',
            'originalSavedBitsOrWholeCallerFrameContinuityProved':False}


def check_process_zero_return(index,normal_proof,probe_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(normal_proof.get('claim')=='snapshotProcessLocalIndexNormalRequestAndTemporary' and probe_proof.get('claim')=='snapshotActualProcessProbeRaxAndConditionalFrame',
             'process-zero-fresh-dependencies','fresh normal request and actual entry probe',[normal_proof.get('claim'),probe_proof.get('claim')])
    body=index.body(spec['type'],spec['method'])
    _require(body.symbol==normal_proof['symbol']==probe_proof['symbol'],'process-zero-same-caller','same Process caller',body.symbol)
    selected=NativeReferenceContext(index.image,index=index)
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==body.symbol]
    _require(bool(methods) and all(not m.flags&0x10 for m in methods),'process-zero-instance-definition','ordinary instance Process',body.symbol)
    for method in methods:require_ordinary_type(selected,method.return_type,'bool','Process.zero.return')
    _require(body.pointer in index.extents,'process-zero-owned-caller','exact caller owned extent',hex(body.pointer));end=index.extents[body.pointer]
    def scoped(pointer,size):
        _require(body.pointer<=pointer and pointer+size<=end,'process-zero-owned-span','complete selected fragment within caller',[hex(pointer),size])
        return index.pe.bytes_at_va(pointer,size)
    branch_pointer=int(normal_proof['temporaryContinuation'],16)
    branch=check_zero_branch(scoped(branch_pointer,14),branch_pointer,normal_proof['anonymousOutBoolLocalDisp8'])
    zero_pointer=branch['zeroTarget'];zero=check_zero_return(scoped(zero_pointer,4),zero_pointer)
    epilogue_pointer=zero['epilogueTarget'];epilogue=check_epilogue(scoped(epilogue_pointer,79),epilogue_pointer,probe_proof['requestedAllocationBytes'])
    return {'symbol':body.symbol,'claim':'snapshotProcessBoolProxyZeroToCompleteFalseReturn',
            'branchEntry':hex(branch_pointer),'zeroEntry':hex(zero_pointer),'epilogueEntry':hex(epilogue_pointer),
            **branch,**zero,**epilogue,'ordinaryBoolReturnProved':True,
            'boundary':'The fresh normal-request temporary continuation directly reaches a complete raw XMM temporary copy and one-byte comparison of the same explicit Bool ref proxy local. Selected zero reaches XOR AL,AL and its exact short jump to a complete actual raw epilogue: XMM6..15 loads, frame-base SP transfer, all nonvolatile GPR pops and RET. Ordinary Process Bool return type is independently gated; AL remains zero through the epilogue, while upper RAX zero is not inferred. The epilogue frame advance equals the independently checked entry allocation request, but matching arithmetic does not prove continuous frame or original saved bits. Normal request/selected byte read, valid aligned save/pop/return storage, appropriate saved bits, no intervening out-local/frame write or external interference remain conditions. Nonzero byte branch, whole Process execution, Bool provider write semantics, final damage output and snapshot compact-index correspondence stay excluded or unresolved.'}
