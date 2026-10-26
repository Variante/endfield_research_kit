"""Complete split array-count program and its caller-bound rank accessor.

Rank, bounds and length names require independently selected getter/type joins.
Stored coordinates and conditional dimension products do not certify a full
array header, allocation or actual interface selection.
"""
from __future__ import annotations

import hashlib


def prove_array_rank_accessor(raw: bytes, *, rank_offset: int) -> dict:
    if type(rank_offset) is not int or not 0<=rank_offset<1<<31 or not isinstance(raw,bytes):
        raise ValueError('array-rank.input: exact bytes and bounded offset required')
    expected=bytes.fromhex('488B010FB680')+rank_offset.to_bytes(4,'little')+b'\xc3'
    if raw!=expected:raise ValueError('array-rank.program: complete class-pointer byte-read and return required')
    return {'status':'complete-array-rank-accessor-proved','programBytes':len(raw),
        'programSha256':hashlib.sha256(raw).hexdigest().upper(),'arrayRegister':'rcx',
        'classPointerOffset':0,'classByteOffset':rank_offset,'rankReadBits':8,
        'resultZeroExtendedIntoEaxAndRax':True,'fullClassLayoutOrRuntimeRankProved':False}


def prove_array_collection_count(main: bytes, failure: bytes, loop: bytes, *, entry_va: int,
        failure_va: int, loop_va: int, rank_error_va: int, raise_va: int,
        class_error_va: int, dimension_length_va: int, rank_offset: int,
        bounds_offset: int, length_offset: int) -> dict:
    addresses=(entry_va,failure_va,loop_va,rank_error_va,raise_va,class_error_va,dimension_length_va)
    if (any(not isinstance(x,bytes) for x in (main,failure,loop))
            or any(type(v) is not int or not 0<v<1<<64 for v in addresses)
            or any(a+len(b)>=1<<64 for a,b in ((entry_va,main),(failure_va,failure),(loop_va,loop)))
            or type(rank_offset) is not int or not 0<=rank_offset<1<<31
            or any(type(v) is not int or not 0<v<128 for v in (bounds_offset,length_offset))):
        raise ValueError('array-count.input: exact complete fragments, bounded addresses and offsets required')
    rows=[];raw=b'';start=0;offset=0;region=''
    def select(data,va,name):
        nonlocal raw,start,offset,region
        raw,start,offset,region=data,va,0,name
    def literal(hexed,meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:
            raise ValueError(f'array-count.instruction: region={region} offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'region':region,'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    def branch(op,target,meaning,short=False):
        nonlocal offset
        prefix=bytes.fromhex(op);size=len(prefix)+(1 if short else 4);actual=raw[offset:offset+size]
        if len(actual)!=size or actual[:len(prefix)]!=prefix:
            raise ValueError(f'array-count.branch-opcode: region={region} offset={offset} expected={op} actual={actual.hex().upper()}')
        destination=start+offset+size+int.from_bytes(actual[len(prefix):],'little',signed=True)
        if destination!=target:
            raise ValueError(f'array-count.branch-target: region={region} offset={offset} expected={target:#x} actual={destination:#x}')
        rows.append({'region':region,'offset':offset,'rawHex':actual.hex().upper(),'operation':meaning,'targetVa':target});offset+=size
    def end():
        if offset!=len(raw):raise ValueError(f'array-count.terminal: region={region} expectedBytes={offset} actualBytes={len(raw)}')
    rank=rank_offset.to_bytes(4,'little').hex().upper()
    select(main,entry_va,'main')
    literal('4053','push incoming rbx')
    literal('4883EC30','allocate 48 bytes; rsp = entry rsp -56')
    literal('48833900','compare array first-qword class pointer with zero')
    literal('488BD9','save array reference in rbx')
    branch('0F84',failure_va,'zero class pointer enters separate failure fragment')
    literal('488B01','rax = current array class pointer')
    literal('80B8'+rank+'00','compare class rank byte with zero')
    branch('76',entry_va+91,'unsigned rank <= zero enters error fragment',True)
    literal('488379'+f'{bounds_offset:02X}'+'00','compare optional bounds pointer with zero')
    literal('4889742440','save incoming rsi at entry rsp+8')
    literal('48897C2448','save incoming rdi at entry rsp+16')
    branch('75',entry_va+107,'nonnull bounds selects its first length address',True)
    literal('488D79'+f'{length_offset:02X}','rdi = direct array length address')
    literal('488B3F','rdi = first length qword read through selected address')
    literal('BE01000000','initialize esi and full rsi to dimension one')
    literal('4038B0'+rank,'compare current class rank byte with sil one')
    branch('0F87',loop_va,'unsigned rank > one enters remaining-dimension loop')
    literal('488B742440','restore incoming rsi from entry home +8')
    literal('8BC7','eax = low32(rdi), zero extending full rax')
    literal('488B7C2448','restore incoming rdi from entry home +16')
    literal('4883C430','release local allocation')
    literal('5B','restore incoming rbx and original entry rsp')
    literal('C3','return the low DWORD dimension product')
    branch('E8',rank_error_va,'call opaque rank-error producer')
    literal('488BC8','rcx = returned error object')
    literal('33D2','zero optional raise context')
    branch('E8',raise_va,'call selected opaque raise helper')
    literal('CC','trap if raise helper returns')
    literal('488B79'+f'{bounds_offset:02X}','rdi = nonnull bounds length address')
    branch('EB',entry_va+52,'rejoin the same qword length dereference',True)
    end()
    select(failure,failure_va,'zero-class')
    literal('33C0','zero full rax')
    literal('488D4C2420','rcx = local error payload address')
    literal('4889442420','zero first eight local payload bytes')
    literal('4889442428','zero next eight local payload bytes')
    branch('E8',class_error_va,'call opaque zero-class error producer')
    literal('488BC8','rcx = returned error object')
    literal('33D2','zero optional raise context')
    branch('E8',raise_va,'call the same selected opaque raise helper')
    literal('CC','trap if raise helper returns')
    end()
    select(loop,loop_va,'dimensions')
    literal('8BD6','edx = current dimension esi')
    literal('488BCB','rcx = original array rbx')
    branch('E8',dimension_length_va,'call opaque dimension-length helper')
    literal('488B0B','rcx = reloaded original array class pointer')
    literal('FFC6','increment esi as DWORD, zero extending full rsi')
    literal('0FAFF8','edi = low32(edi * eax), zero extending full rdi')
    literal('0FB691'+rank,'edx = zero-extended reloaded class rank byte')
    literal('3BF2','signed comparison of esi with zero-extended rank edx')
    branch('7C',loop_va,'continue while signed dimension counter < reloaded rank',True)
    branch('E9',entry_va+73,'rejoin common low-DWORD product return')
    end()
    return {'status':'complete-split-array-collection-count-program-proved','program':rows,
        'programBytes':len(main)+len(failure)+len(loop),
        'fragmentSha256':{k:hashlib.sha256(v).hexdigest().upper() for k,v in (('main',main),('zeroClass',failure),('dimensions',loop))},
        'arrayRegister':'rcx','classPointerOffset':0,'rankByteOffset':rank_offset,'rankReadBits':8,
        'boundsPointerOffset':bounds_offset,'directLengthOffset':length_offset,'initialLengthReadBits':64,
        'nonnullBoundsRejoinsSameLengthDereference':True,'initialProductBits':32,'multiplyBits':32,
        'loopCounterBits':32,'loopRankReloadedAfterEachHelper':True,'loopComparisonSigned':True,
        'normalReturnBits':32,'normalRaxZeroExtendedFromEax':True,
        'rankOneDirectResult':'low32(qword at array+lengthOffset) when bounds pointer is zero',
        'rankOneBoundsResult':'low32(qword at bounds pointer) when bounds pointer is nonzero',
        'fixedRankDimensionProduct':'low32(firstLengthQword * each dimension helper eax), for stable rank >=2 and normal helper returns',
        'errorHelperEffectsProved':False,'dimensionHelperAlgorithmProved':False,
        'completeArrayHeaderOrAllocationProved':False,'actualInterfaceSelectionOrExecutionKnown':False,
        'conditions':['Current complete owned fragments, metadata getter declaration and independent rank accessor/coordinate joins',
            'Valid readable nonnull array/class and chosen length/bounds memory, writable frame/home slots',
            'Dimension helper completes normally and preserves Win64 nonvolatile rbx/rsi/rdi and required frame memory',
            'A fixed-dimensional product additionally requires stable class/rank and valid dimension helper results',
            'Error callees remain opaque; stored coordinates and the selected named getter do not prove interface selection or allocation'],
        'evidenceBoundary':'All owned main/error/dimension bytes and transfers, unsigned rank guards, shared qword length dereference, DWORD multiply/counter, reloaded rank and full normal frame return. Actual interface dispatch, allocation and dimension/error helper effects remain separate.'}
