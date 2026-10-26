"""Returned carrier bits store and independent unit temporary reload."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require

def check_unit_store(raw,slot):
    expected=b'\x48\x89\x84\x24'+struct.pack('<i',slot)
    _require(raw==expected,'process-unit-return-store','full64 RAX -> anonymous local',raw.hex())
    return {'storeWidthBytes':8,'source':'normally returned RAX full64, immediately after its R13 transfer','localDisp32':slot}

def check_unit_reload(raw,pointer,slot):
    prefix=b'\xff\xc3\x41\x3b\xdf\x48\x8b\xb4\x24'+struct.pack('<i',slot)
    _require(len(raw)==len(prefix)+6 and raw[:len(prefix)]==prefix and raw[len(prefix):len(prefix)+2]==b'\x0f\x8c',
             'process-unit-exit-reload','INC EBX/CMP EBX,R15D/full64 local -> RSI/signed JL',raw.hex())
    target=pointer+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)
    _require(not pointer<=target<pointer+len(raw),'process-unit-reload-excluded-edge','outside exact fragment',hex(target))
    return {'readWidthBytes':8,'destination':'RSI full64','localDisp32':slot,'excludedSignedLessTarget':hex(target),
            'selectedFallthroughCondition':'signed Int32 incremented EBX >= signed Int32 R15D; neither role is inferred as damage index'}


def check_process_unit_slot(index,loop_proof,provider_proof,normal_proof,spec):
    _require(loop_proof.get('claim')=='snapshotProcessLocalIncrementGuardAndProviderRequest' and provider_proof.get('claim')=='snapshotProcessActualProviderEightByteNormalReturn' and normal_proof.get('claim')=='snapshotProcessLocalIndexNormalRequestAndTemporary',
             'process-unit-slot-fresh-dependencies','fresh request/physical provider/local normal request',[loop_proof.get('claim'),provider_proof.get('claim'),normal_proof.get('claim')])
    _require(loop_proof['symbol']==provider_proof['symbol']==normal_proof['symbol'],'process-unit-slot-same-caller','same independently proved caller',loop_proof['symbol'])
    _require(loop_proof['guard']['providerTarget']==int(provider_proof['actualProviderEntry'],16),'process-unit-slot-same-provider','fresh actual provider',provider_proof['actualProviderEntry'])
    body=index.body(spec['type'],spec['method']);slot=spec['anonymousUnitLocalDisp32']
    _require(body.symbol==loop_proof['symbol'] and body.pointer in index.extents and 0<index.extents[body.pointer]-body.pointer<=65536,
             'process-unit-slot-owned-caller','same bounded owned caller',body.symbol)
    end=index.extents[body.pointer];store=loop_proof['guard']['selectedFragmentEnd']
    _require(body.pointer<=store and store+8<=end,'process-unit-slot-store-span','immediately following fresh RAX->R13 fragment',hex(store))
    stored=check_unit_store(index.pe.bytes_at_va(store,8),slot)
    raw=index.pe.bytes_at_va(body.pointer,end-body.pointer);prefix=b'\xff\xc3\x41\x3b\xdf\x48\x8b\xb4\x24'+struct.pack('<i',slot)
    positions=[at for at in range(len(raw)) if raw.startswith(prefix,at)];matches=[]
    for at in positions:
        proof=check_unit_reload(raw[at:at+19],body.pointer+at,slot)
        matches.append({'fragmentEntry':hex(body.pointer+at),**proof})
    _require(len(matches)==1,'process-unit-slot-unique-reload','one complete signed exit temporary reload',len(matches))
    return {'symbol':body.symbol,'claim':'snapshotProcessProviderBitsToUnitTemporaryAndReload',
            'storeEntry':hex(store),'store':stored,'reload':matches[0],'normalRequestUnitSource':normal_proof['unitSource'],
            'conditionalSameAddressBitTransferProved':True,'liveUnitReferenceIdentityProved':False,
            'boundary':'The fresh actual collection provider normal RAX full64 passes through its checked immediate R13 transfer into an adjacent exact eight-byte anonymous current-SP store. An independent complete fragment increments unrelated EBX bits, compares signed EBX/R15D, reloads that same displacement into full RSI and excludes its actual signed-less-than backedge. Under selected fallthrough, same current-SP/local storage with no intervening write and RSI/frame preservation to the independently selected normal request, those carrier bits reach R9. These are explicit composition conditions, not a proved whole Process CFG or continuous frame; intervening getter writes to RSI are not ignored. EBX/R15D are not promoted to damage/snapshot indices, returned bits are not promoted to live Unit reference identity, and all local writer/lifetime/runtime layout/cache compact-index joins remain unresolved.'}
