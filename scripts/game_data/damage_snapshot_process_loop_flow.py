"""Local index increment, shared signed guard, anonymous provider request."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target

def check_increment(raw,pointer,index_disp):
    prefix=b'\x44\x8b\xac\x24'+struct.pack('<i',index_disp)+b'\x41\xff\xc5'+b'\x44\x89\xac\x24'+struct.pack('<i',index_disp)
    _require(len(raw)==len(prefix)+5 and raw[:len(prefix)]==prefix and raw[len(prefix)]==0xe9,
             'process-loop-increment','load32/inc32/store32/direct jump',raw.hex())
    return {'guardTarget':relative_branch_target(raw[-5:],pointer+len(prefix),source='processLocalIncrement'),
            'arithmetic':'stored Int32 bits = (old bits + 1) modulo 2^32',
            'signedNonoverflowCondition':'old signed index < INT32_MAX',
            'storeWidthBytes':4,'indexSlotDisp32':index_disp}

def increment_bits(old):
    _require(type(old) is int and 0<=old<1<<32,'process-loop-bits','uint32',old)
    signed=old if old<1<<31 else old-(1<<32)
    return {'newBits':(old+1)&0xffffffff,'signedNonoverflow':signed<(1<<31)-1}


def check_guard_request(raw,pointer,bound_disp):
    forms=[b'\x44\x3b\xac\x24'+struct.pack('<i',bound_disp),'signed-exit',b'\xc6\x44\x24\x70\x00',
           b'\x49\x8b\x5f\x20',b'\x48\x85\xdb','nonnull-one',b'\x48\x8b\x5b\x38',b'\x48\x85\xdb','nonnull-two',
           'anonymous-context',b'\x41\x8b\xd5',b'\x48\x8b\xcb','provider-call',b'\x4c\x8b\xe8']
    at=0;edges={};context=None;target=None
    for form in forms:
        if isinstance(form,bytes):
            _require(raw[at:at+len(form)]==form,'process-loop-guard-instruction',form.hex(),raw[at:at+len(form)].hex());at+=len(form)
        elif form in ('signed-exit','nonnull-one','nonnull-two'):
            opcode=b'\x0f\x8d' if form=='signed-exit' else b'\x0f\x84'
            part=raw[at:at+6];_require(len(part)==6 and part[:2]==opcode,'process-loop-guard-edge',form,part.hex())
            edges[form]=pointer+at+6+int.from_bytes(part[2:],'little',signed=True);at+=6
        elif form=='anonymous-context':
            part=raw[at:at+7];_require(len(part)==7 and part[:3]==b'\x4c\x8b\x05','process-loop-context','R8 RIP qword',part.hex())
            context=pointer+at+7+int.from_bytes(part[3:],'little',signed=True);at+=7
        else:
            part=raw[at:at+5];_require(len(part)==5 and part[0]==0xe8,'process-loop-provider','direct call',part.hex())
            target=relative_branch_target(part,pointer+at,source='processLoopProvider');at+=5
    _require(len(raw)==at and all(not pointer<=edge<pointer+at for edge in edges.values()),'process-loop-complete-fragment','complete bytes and excluded edges outside',[len(raw),at,edges])
    return {'guardEntry':pointer,'selectedFragmentEnd':pointer+at,'boundLocalDisp32':bound_disp,'providerTarget':target,'anonymousContextQword':context,'excludedTargets':edges,
            'selectedCondition':'signed Int32 current R13D < signed Int32 anonymous bound local',
            'indexRequest':'precall R13D full32 -> EDX; RCX anonymous collection; R8 anonymous context',
            'postCallR13':'RAX full64 -> R13; prior index32 origin ends at this write',
            'providerSemanticsAndReturnReferenceIdentityProved':False}


def check_process_loop(index,local_proof,spec):
    _require(local_proof.get('claim')=='snapshotProcessLocalIndexNormalRequestAndTemporary',
             'process-loop-fresh-local','fresh independently checked local normal request',local_proof.get('claim'))
    body=index.body(spec['type'],spec['method'])
    _require(body.symbol==local_proof['symbol'],'process-loop-same-body',local_proof['symbol'],body.symbol)
    _require(body.pointer in index.extents and 0<index.extents[body.pointer]-body.pointer<=65536,
             'process-loop-owned-search','bounded exact owned extent',hex(body.pointer))
    raw=index.pe.bytes_at_va(body.pointer,index.extents[body.pointer]-body.pointer)
    slot=spec['indexLocalDisp32'];bound=spec['boundLocalDisp32']
    _require(local_proof.get('anonymousIndexLocalDisp32')==slot,'process-loop-local-slot-identity',slot,local_proof.get('anonymousIndexLocalDisp32'))
    prefix=b'\x44\x8b\xac\x24'+struct.pack('<i',slot)+b'\x41\xff\xc5'+b'\x44\x89\xac\x24'+struct.pack('<i',slot)
    positions=[at for at in range(len(raw)) if raw.startswith(prefix,at)];increments=[]
    for at in positions:
        proof=check_increment(raw[at:at+len(prefix)+5],body.pointer+at,slot)
        increments.append({'entry':hex(body.pointer+at),**proof})
    _require(len(increments)==spec['selectedIncrementCount'],'process-loop-increment-multiplicity',spec['selectedIncrementCount'],len(increments))
    targets={proof['guardTarget'] for proof in increments}
    _require(len(targets)==1,'process-loop-same-guard','one identical actual direct target',sorted(targets))
    target=next(iter(targets));at=target-body.pointer
    _require(0<=at and at+66<=len(raw),'process-loop-guard-owned-span','complete in same owned caller',hex(target))
    # Complete raw fragment ends immediately after RAX overwrites R13.
    guard=check_guard_request(raw[at:at+66],target,bound)
    return {'symbol':body.symbol,'claim':'snapshotProcessLocalIncrementGuardAndProviderRequest',
            'increments':increments,'guard':guard,'localSlotIdentityUnderSameCurrentSp':True,
            'producerConsumerCompactIndexJoinProved':False,
            'boundary':'Three exact raw load32/INC32/store32/JMP fragments write the same anonymous displacement as the fresh local normal-request index and directly target one exact signed Int32 guard. Selected signed-less-than fallthrough and nonnull anonymous receiver guards transfer pre-call R13D full32 into EDX for an unnamed actual provider call; actual RIP context and all excluded targets are recorded. Full RAX subsequently overwrites R13, ending the index32 origin. Increment is modulo 2^32; signed arithmetic recurrence additionally requires old signed index below INT32_MAX. No nonnegative origins/bound, provider semantics or returned reference type are inferred. Slot identity requires same current-SP/frame/storage across the independently entered fragments with no interfering writer. Complete Process CFG/frame continuity, all local writers/initialization and snapshot compact-index correspondence remain unresolved.'}
