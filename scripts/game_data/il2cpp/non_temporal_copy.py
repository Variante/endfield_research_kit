"""Selected non-temporal store values and fence ordering, not load visibility.

MOVNTDQ retains its architectural register-to-memory value transfer and
alignment constraint. Projecting those values onto an existing byte proof
does not project its weak store ordering onto temporal-store semantics.
"""
from __future__ import annotations
import copy
from .aligned_copy_loops import prove_aligned_loop_payload,prove_rebased_vector_tail


def _fail(label,check,expected,actual):
    raise ValueError(f'{label}.{check}: expected={str(expected)[:256]} actual={str(actual)[:384]}')


def project_loop_store_values(operations,*,width,chunk,label='non-temporal-loop'):
    if width not in (16,32) or type(chunk) is not int or chunk<width or chunk%width:
        _fail(label,'loop-domain','positive whole-vector chunk',(width,chunk))
    projected=copy.deepcopy(operations);stores=0
    for op in projected:
        if op.get('direction')=='store':
            if op.get('nonTemporalHint') is not True or op.get('requiredAlignmentBytes')!=width:
                _fail(label,'loop-store','aligned non-temporal vector store',op)
            op['nonTemporalHint']=False;stores+=1
        elif op.get('direction')!='load' or op.get('nonTemporalHint') is not False:
            _fail(label,'loop-load','ordinary exact vector source load',op)
    proof=prove_aligned_loop_payload(projected,width=width,chunk=chunk,label=label+'.values')
    return projected,{'allChunkStoreBytesEqualInitialSourceProved':True,
        'alignedNonTemporalStores':stores,'byteValueProof':proof,
        'valueProjectionOnly':True,'nonTemporalOrderingProjectedAsTemporal':False,
        'allStoresGloballyVisibleAtReturnProved':False,'runtimeExecutionObserved':False}


def prove_tail_store_values(operations,*,width,chunk,remaining,label='non-temporal-tail'):
    if width not in (16,32) or type(chunk) is not int or chunk<width or chunk%width or type(remaining) is not int or not 0<=remaining<chunk:
        _fail(label,'tail-domain','reachable post-loop remainder in [0,chunk)',(width,chunk,remaining))
    projected=copy.deepcopy(operations);rounded=(remaining+width-1)&-width;nt=0;ordinary=0
    for op in projected:
        if op.get('direction')=='load':
            if op.get('nonTemporalHint') is not False or op.get('requiredAlignmentBytes')!=1:
                _fail(label,'tail-load','ordinary unaligned vector source load',op)
        elif op.get('direction')=='store':
            address=op.get('address',{});base=address.get('base');index=address.get('index');d=address.get('displacement')
            if op.get('nonTemporalHint') is True:
                if (op.get('requiredAlignmentBytes')!=width or base!='rcx' or index not in (None,'r9')
                        or type(d) is not int or d%width or (d+(rounded if index=='r9' else 0))%width):
                    _fail(label,'tail-store-alignment','current aligned destination plus whole-vector offset',op)
                op['nonTemporalHint']=False;op['requiredAlignmentBytes']=1;nt+=1
            elif op.get('nonTemporalHint') is False:
                head=base=='rax' and index is None and d==0 and op.get('backingRegister')=='vector0'
                last=base=='rcx' and index=='r8' and d==-width and op.get('backingRegister')=='vector5'
                if op.get('requiredAlignmentBytes')!=1 or not (head or last):
                    _fail(label,'cached-temporal-store','only saved original head or endpoint vector',op)
                ordinary+=1
            else:_fail(label,'tail-store-hint','explicit temporal or non-temporal transfer',op)
        else:_fail(label,'tail-direction','load or store',op)
    proof=prove_rebased_vector_tail(projected,width=width,chunk=chunk,remaining=remaining,label=label+'.values')
    return {'allRemainderStoreBytesEqualInitialSourceProved':True,'byteValueProof':proof,
        'alignedNonTemporalStores':nt,'savedTemporalStores':ordinary,
        'overlappingWritesHaveIdenticalByteValuesProved':True,
        'valueProjectionOnly':True,'nonTemporalOrderingProjectedAsTemporal':False,
        'allStoresGloballyVisibleAtReturnProved':False,'runtimeExecutionObserved':False}


def prove_store_fence(raw,*,label='store-fence'):
    if raw!=b'\x0f\xae\xf8':_fail(label,'exact-selected-encoding','unprefixed SFENCE',raw.hex())
    return {'exactSelectedStoreFenceProved':True,
        'precedingStoresGloballyVisibleBeforeFollowingStoresProved':True,
        'orderedAgainstLoads':False,'allStoresGloballyVisibleAtReturnProved':False,
        'selection':'supported instruction state, normal complete execution and compatible valid memory; no intervening unproved memory-type change or concurrent payload modification',
        'runtimeExecutionObserved':False}
