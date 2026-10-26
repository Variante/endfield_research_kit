"""Typed count result to the independently proved Process signed bound."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.damage_snapshot_count_flow import _count_request
from scripts.game_data.il2cpp.context import relative_branch_target


def check_bound_bytes(raw,pointer,bound_disp,child_disp):
    _require(len(raw)==32 and raw[:3]==b'\x48\x85\xdb' and raw[3:5]==b'\x0f\x84',
             'process-bound-entry','complete TEST RBX/JZ/count request/store',raw.hex())
    excluded=pointer+9+int.from_bytes(raw[5:9],'little',signed=True)
    _require(not pointer<=excluded<pointer+32,'process-bound-excluded-edge','outside scoped fragment',hex(excluded))
    _require(raw[9:12]==b'\x48\x8b\x15' and raw[16:20]==b'\x48\x8b\x4b'+bytes([child_disp]) and raw[20]==0xe8,
             'process-bound-request','RDX RIP qword/RCX child/direct CALL',raw.hex())
    _require(raw[25:32]==b'\x89\x84\x24'+struct.pack('<i',bound_disp),
             'process-bound-result-store','normally returned EAX -> local four bytes',raw[25:].hex())
    target=relative_branch_target(raw[20:25],pointer+20,source='processBoundCount')
    return {'fragmentEntry':hex(pointer),'excludedNullRootTarget':hex(excluded),'actualCountTarget':hex(target),
            'boundLocalDisp32':bound_disp,'returnedResultStoreWidthBytes':4,
            'usageLoad':{'va':hex(pointer+9),'bytes':raw[9:16].hex()}}


def signed_guard_from_bits(index_bits,bound_bits):
    _require(all(type(v) is int and 0<=v<1<<32 for v in (index_bits,bound_bits)),
             'process-bound-int32-bits','uint32 input bits',[index_bits,bound_bits])
    signed=lambda v:v if v<1<<31 else v-(1<<32)
    return {'signedIndex':signed(index_bits),'signedBound':signed(bound_bits),'jgeExcludedSelected':signed(index_bits)>=signed(bound_bits)}


def check_process_bound(index,loop_proof,count_proof,count_spec,spec):
    _require(loop_proof.get('claim')=='snapshotProcessLocalIncrementGuardAndProviderRequest' and count_proof.get('claim')=='snapshotCountRequestNullHelperToProducerReturn',
             'process-bound-fresh-dependencies','fresh Process guard and actual count null helper',[loop_proof.get('claim'),count_proof.get('claim')])
    body=index.body(spec['type'],spec['method'])
    _require(body.symbol==loop_proof['symbol'],'process-bound-same-caller',loop_proof['symbol'],body.symbol)
    bound=loop_proof['guard']['boundLocalDisp32']
    _require(body.pointer in index.extents and 0<index.extents[body.pointer]-body.pointer<=65536,
             'process-bound-owned-search','bounded exact caller extent',hex(body.pointer))
    raw=index.pe.bytes_at_va(body.pointer,index.extents[body.pointer]-body.pointer);matches=[]
    for at in range(len(raw)):
        if raw[at:at+5]!=b'\x48\x85\xdb\x0f\x84':continue
        try:proof=check_bound_bytes(raw[at:at+32],body.pointer+at,bound,spec['anonymousChildDisp8'])
        except ValueError:continue
        matches.append(proof)
    _require(len(matches)==1,'process-bound-unique-program','one complete typed request/result store',len(matches))
    proof=matches[0];request=_count_request(index,proof.pop('usageLoad'),count_spec)
    _require(proof['actualCountTarget']==count_proof['physicalHelper'],'process-bound-same-actual-count-helper',count_proof['physicalHelper'],proof['actualCountTarget'])
    return {**proof,**request,'symbol':body.symbol,'claim':'snapshotProcessCountResultToSignedBound',
            'actualCountTargetMatchesFreshNullHelper':True,'registeredIdentityProved':False,
            'boundary':'The exact selected nonnull-root Process fragment requests a typed ordinary Int32 SafeCount<Unit> context and stores normally returned EAX as four bytes into the same anonymous current-SP displacement used by the fresh signed guard. Its actual physical target matches the independently proved count null-helper entry, with registered request identity still separate. Under that helper selected context/null-collection normal return, zero reaches the bound store. If the same stored bits reach the guard without frame/storage interference, the actual signed Int32 comparison chooses JGE only when current signed index is at least signed bound; zero bound does not exclude a negative index by itself. Static request/context resolution, ordinary normal-call preservation and valid storage remain conditions. No whole Process CFG/frame continuity, all bound/index writers, nonnull count semantics, initialization or snapshot compact-index equality follows.'}
