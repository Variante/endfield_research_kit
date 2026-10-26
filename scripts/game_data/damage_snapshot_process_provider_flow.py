"""Actual eight-byte provider normal return, anonymous slots."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target

def check_provider_bytes(raw,pointer,end,slots):
    count,array,length,payload=[slots[k] for k in ('countDword','arrayReference','arrayLengthDword','arrayPayload')]
    _require(all(type(v) is int and 0<=v<128 for v in (count,array,length,payload)),
             'process-provider-slots','anonymous disp8',slots)
    forms=[b'\x48\x83\xec\x28',b'\x3b\x51'+bytes([count]),'count-edge',
           b'\x48\x8b\x41'+bytes([array]),b'\x48\x85\xc0','null-edge',b'\x3b\x50'+bytes([length]),'array-edge',
           b'\x48\x63\xca',b'\x48\x8b\x44\xc8'+bytes([payload]),b'\x48\x83\xc4\x28',b'\xc3',
           'throw-one',b'\xcc','throw-two',b'\xcc',b'\x33\xc9','throw-three',b'\xcc']
    at=0;boundaries=[];edges={};calls={};ret_end=None
    for form in forms:
        boundaries.append(pointer+at)
        if isinstance(form,bytes):
            _require(raw[at:at+len(form)]==form,'process-provider-instruction',form.hex(),raw[at:at+len(form)].hex());at+=len(form)
            if form==b'\xc3':ret_end=pointer+at
        elif form.endswith('edge'):
            opcode=0x74 if form=='null-edge' else 0x73
            part=raw[at:at+2];_require(len(part)==2 and part[0]==opcode,'process-provider-edge',form,part.hex())
            edges[form]=pointer+at+2+int.from_bytes(part[1:],'little',signed=True);at+=2
        else:
            part=raw[at:at+5];_require(len(part)==5 and part[0]==0xe8,'process-provider-excluded-call',form,part.hex())
            calls[form]=relative_branch_target(part,pointer+at,source='processActualProvider');at+=5
    _require(at==len(raw) and pointer+at==end,'process-provider-full-extent',[end-pointer,at],len(raw))
    _require(all(ret_end<=target<end and target in boundaries for target in edges.values()),
             'process-provider-excluded-target-boundaries','owned instruction start beyond selected RET',edges)
    return {'selectedRetEnd':ret_end,'ownedEnd':end,'allOwnedBytesPartitioned':True,'excludedGuardTargets':edges,'excludedCalls':calls,
            'normalConditions':['UInt32(EDX)<UInt32(anonymous receiver count)','nonnull anonymous array','UInt32(EDX)<UInt32(anonymous array bound)'],
            'normalRead':'anonymous array + payload displacement + signExtend(Int32 EDX)*8',
            'normalReadWidthBytes':8,'returnRegister':'rax','frameAllocationBytes':40,
            'excludedThrowPathsProvedNormallyReturning':False,'heapArrayLayoutOrUnitReferenceIdentityProved':False}


def provider_address(array,index_bits,payload):
    _require(type(array) is int and type(index_bits) is int and 0<=index_bits<1<<32 and type(payload) is int,
             'process-provider-address-inputs','raw array address/uint32 index/integer payload',[array,index_bits,payload])
    signed=index_bits if index_bits<1<<31 else index_bits-(1<<32)
    address=array+payload+signed*8
    return {'signedIndex':signed,'address':address,'validNonwrappingEightByteRange':0<=array<1<<64 and 0<=address and address+8<=1<<64}


def check_process_provider(index,loop_proof,spec):
    import hashlib
    _require(loop_proof.get('claim')=='snapshotProcessLocalIncrementGuardAndProviderRequest',
             'process-provider-fresh-request','fresh raw loop/request proof',loop_proof.get('claim'))
    pointer=loop_proof['guard']['providerTarget']
    _require(pointer in index.extents and 0<index.extents[pointer]-pointer<=512,
             'process-provider-owned-entry','bounded exact actual provider pdata extent',hex(pointer))
    end=index.extents[pointer];raw=index.pe.bytes_at_va(pointer,end-pointer)
    proof=check_provider_bytes(raw,pointer,end,spec['anonymousSlots'])
    return {**proof,'symbol':loop_proof['symbol'],'claim':'snapshotProcessActualProviderEightByteNormalReturn',
            'actualProviderEntry':hex(pointer),'ownedBodySha256':hashlib.sha256(raw).hexdigest(),
            'observedRegisteredNames':index.names_by_pointer.get(pointer,[]),
            'registeredClosedUnitIdentityProved':False,
            'boundary':'The actual fresh Process collection request target has an exact complete owned raw byte partition. Its selected unsigned count/array bounds and nonnull branch sign-extend EDX, read exactly eight bytes from the anonymous array/payload/index-derived address into full RAX, restore its local SP and RET; fresh caller bytes then overwrite R13 with that returned full64 value. Every other guard targets a checked owned excluded CALL/INT3 branch; no normal return or throw meaning is proved there. Registered names are provenance only, with no closed Unit/runtime-class parity inferred. UInt32 guards do not independently imply a nonnegative signed index or managed array layout. Valid nonwrapping derived read/local/return storage, actual compatible receiver/class context and noninterference remain conditions. No live returned Unit identity, provider generic semantics, continuous full Process frame or snapshot compact-index equality follows.'}
