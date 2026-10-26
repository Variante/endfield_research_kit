"""Complete selected vector-distance byte program with explicit packed math.

Single subtraction/squares/adds feed CVTPS2PD, packed SQRTPD and CVTPD2PS.
Initialization and the negative-sum helper remain opaque normal-call edges.
Callers authenticate byte ownership, typed buffers and selected native inputs.
"""
from __future__ import annotations

import hashlib
from .context import relative_branch_target, rip_qword_load_target


def prove_vector3_distance_program(raw: bytes, *, entry_va: int,
                                  initialize_helper_va: int, negative_sqrt_helper_va: int) -> dict:
    if (not isinstance(raw,bytes) or any(type(v) is not int or not 0<v<1<<64
            for v in (entry_va,initialize_helper_va,negative_sqrt_helper_va)) or entry_va+len(raw)>=1<<64):
        raise ValueError('vector3-distance-program.input: original bytes and bounded addresses required')
    rows=[];offset=0
    def literal(hexed,meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:
            raise ValueError(f'vector3-distance-program.instruction: offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    def call(target,meaning):
        nonlocal offset
        actual=raw[offset:offset+5]
        if len(actual)!=5 or actual[0]!=0xe8 or relative_branch_target(actual,entry_va+offset,source=meaning)!=target:
            raise ValueError(f'vector3-distance-program.call: offset={offset} selected target differs')
        rows.append({'offset':offset,'rawHex':actual.hex().upper(),'operation':meaning,'targetVa':target});offset+=5
    for h,m in [('4883EC58','allocate eighty-eight-byte frame'),('0F29742440','save xmm6'),
        ('F30F107104','load y-left; clear higher lanes of xmm6'),('F30F5C7204','Single y difference'),
        ('0F297C2430','save xmm7'),('F30F1039','load x-left; clear higher lanes of xmm7'),
        ('F30F5C3A','Single x difference'),('440F29442420','save xmm8'),
        ('F3440F104108','load z-left; clear higher lanes of xmm8')]:literal(h,m)
    carrier=raw[offset:offset+7]
    if len(carrier)!=7 or carrier[:3]!=bytes.fromhex('488B0D'):
        raise ValueError('vector3-distance-program.carrier: complete RIP load into rcx required')
    cell=rip_qword_load_target(carrier,entry_va+offset,source='distance initialization carrier')
    if not 0<cell<1<<64:raise ValueError('vector3-distance-program.carrier: address overflow')
    rows.append({'offset':offset,'rawHex':carrier.hex().upper(),'operation':'load anonymous initialization carrier pointer','cellVa':cell});offset+=7
    for h,m in [('F3440F5C4208','Single z difference'),('83B9E000000000','compare carrier DWORD at +224 with zero'),
        ('743F','zero guard branches to init call at offset 129'),('F30F59F6','Single y square'),
        ('0F57C0','zero every xmm0 bit'),('F30F59FF','Single x square'),('F3450F59C0','Single z square'),
        ('F30F58F7','Single sum y-square plus x-square'),('F3410F58F0','Single sum plus z-square'),
        ('0F5ACE','CVTPS2PD: Double pair from Single sum and zero lane'),
        ('660F2EC1','UCOMISD: zero against Double low sum'),
        ('7724','ordered zero-greater branches to helper path at offset 136'),
        ('660F51C1','SQRTPD: both Double lanes, including the zero high lane'),
        ('660F5AC0','CVTPD2PS: return Single low square-root; clear bits 127..64'),
        ('0F28742440','restore xmm6'),('0F287C2430','restore xmm7'),
        ('440F28442420','restore xmm8'),('4883C458','restore allocated frame'),('C3','normal return')]:literal(h,m)
    call(initialize_helper_va,'call opaque initialization helper with carrier in rcx')
    literal('EBBA','join square computation at offset 66')
    literal('0F28C1','move Double pair into negative-path argument register xmm0')
    call(negative_sqrt_helper_va,'call opaque negative-path helper')
    literal('F20F5AC0','CVTSD2SS: narrow returned Double low lane')
    literal('EBD6','join common register/frame restoration at offset 108')
    if offset!=len(raw):
        raise ValueError(f'vector3-distance-program.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    return {'status':'complete-vector3-distance-subtract-squares-packed-sqrt-program-proved',
        'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,
        'leftRegister':'rcx','rightRegister':'rdx','inputValueBytes':12,'returnedSingleRegister':'xmm0.low32',
        'componentReadOffsets':[0,4,8],'singleSumOrder':'(dy*dy+dx*dx)+dz*dz',
        'sumConversion':'CVTPS2PD','inlineSquareRoot':'SQRTPD','inlineResultConversion':'CVTPD2PS',
        'convertedHighDoubleLaneZero':True,'inlineLowExpression':'Single(DoubleSqrt(Double(SingleSum)))',
        'negativeHelperEdge':'ordered Double sum below zero only; equality and unordered use inline path after normal compare',
        'initializationCarrierCellVa':cell,'initializationGuardDwordOffset':224,
        'savedAndRestoredNonvolatileSimd':['xmm6','xmm7','xmm8'],
        'initializationHelperEffectsProved':False,'negativeHelperAlgorithmProved':False,
        'namedUnityDistanceEntryIdentityProved':False,'runtimeExecutionKnown':False,
        'conditions':['Current caller authenticates full exception-owned bytes and typed twelve-byte input buffers',
            'Valid frame/carrier/buffer memory; init helper returns normally and preserves Win64 nonvolatile SIMD lanes',
            'SSE2 operations complete normally under the selected MXCSR; nonnegative low sum selects the independently decoded packed square-root path',
            'Negative-path helper is opaque; its return is narrowed but not proved to implement square root'],
        'evidenceBoundary':'Every byte and branch, input coordinates, Single arithmetic order, packed conversions/square root, frame and saved SIMD restoration. Current helper is anonymous rather than the registered Unity Distance entry; init/fallback effects and gameplay values remain unresolved.'}
