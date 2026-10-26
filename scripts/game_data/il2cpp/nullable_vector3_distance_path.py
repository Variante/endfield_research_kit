"""Complete ordinary distance continuation of a caller-proved tagged return.

The caller binds the incoming aliases/frame, typed fields, helper programs and
hot output tag. The count helper remains an opaque provider; repeated corner
calculation means a single stable path cannot be inferred from these bytes.
"""
from __future__ import annotations

import hashlib


def prove_nullable_vector3_distance_path(raw: bytes, *, entry_va: int,
        calculate_corners_va: int, count_helper_va: int, array_element_va: int,
        distance_helper_va: int, straight_line_va: int, null_failure_va: int,
        hot_return_va: int, corners_offset: int, data_reference_offset: int,
        max_distance_offset: int) -> dict:
    addresses=(entry_va,calculate_corners_va,count_helper_va,array_element_va,
        distance_helper_va,straight_line_va,null_failure_va,hot_return_va)
    if (not isinstance(raw,bytes) or any(type(v) is not int or not 0<v<1<<64 for v in addresses)
            or entry_va+len(raw)>=1<<64):
        raise ValueError('nullable-vector3-distance.input: original bytes and bounded addresses required')
    if any(type(v) is not int or not 0<v<128 for v in (corners_offset,data_reference_offset,max_distance_offset)):
        raise ValueError('nullable-vector3-distance.field: positive byte field offsets required')
    rows=[];offset=0
    def literal(hexed,meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:
            raise ValueError(f'nullable-vector3-distance.instruction: offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    def branch(prefix,target,meaning,*,short=False):
        nonlocal offset
        opcode=bytes.fromhex(prefix);size=len(opcode)+(1 if short else 4);actual=raw[offset:offset+size]
        if len(actual)!=size or actual[:len(opcode)]!=opcode:
            raise ValueError(f'nullable-vector3-distance.branch-opcode: offset={offset} expected={prefix} actual={actual.hex().upper()}')
        destination=entry_va+offset+size+int.from_bytes(actual[len(opcode):],'little',signed=True)
        if destination!=target:
            raise ValueError(f'nullable-vector3-distance.branch-target: offset={offset} expected={target:#x} actual={destination:#x}')
        rows.append({'offset':offset,'rawHex':actual.hex().upper(),'operation':meaning,'targetVa':target});offset+=size
    literal('4533ED','initialize r13d loop counter and full r13 to zero')
    literal('33D2','zero optional calculation context')
    literal('488BCB','rcx = saved path reference')
    branch('E8',calculate_corners_va,'recalculate corners before count-provider call')
    context=raw[offset:offset+7]
    if len(context)!=7 or context[:3]!=bytes.fromhex('488B15'):
        raise ValueError('nullable-vector3-distance.context: complete original RIP load into rdx required')
    cell=entry_va+offset+7+int.from_bytes(context[3:],'little',signed=True)
    if not 0<cell<1<<64:raise ValueError('nullable-vector3-distance.context: address overflow')
    rows.append({'offset':offset,'rawHex':context.hex().upper(),'operation':'load original static count-provider context','cellVa':cell});offset+=7
    literal('488B4B'+f'{corners_offset:02X}','rcx = freshly loaded typed corners-array reference')
    branch('E8',count_helper_va,'call opaque count provider')
    literal('448D60FF','r12d = low32(rax - 1); zero-extend full r12')
    literal('4585E4','test signed r12d loop limit')
    branch('0F8E',entry_va+177,'nonpositive signed limit skips the segment loop')
    literal('33D2','zero optional first calculation context')
    literal('488BCB','rcx = saved path reference')
    branch('E8',calculate_corners_va,'recalculate before first element of each pair')
    literal('488B4B'+f'{corners_offset:02X}','reload first corners-array reference')
    literal('4885C9','test first array reference')
    branch('0F84',null_failure_va,'null first array enters selected failure block')
    literal('4D63C5','r8 = signExtend32(r13d)')
    literal('488D55CF','rdx = twelve-byte first-element output at rbp-49')
    branch('E8',array_element_va,'copy indexed first element through exact helper')
    literal('33D2','zero optional second calculation context')
    literal('488BCB','rcx = saved path reference')
    branch('E8',calculate_corners_va,'recalculate before second element of each pair')
    literal('488B4B'+f'{corners_offset:02X}','reload second corners-array reference')
    literal('4885C9','test second array reference')
    branch('0F84',null_failure_va,'null second array enters selected failure block')
    literal('418D4501','eax = low32(r13 + 1), zero-extending rax')
    literal('4C63C0','r8 = signExtend32(eax)')
    literal('488D55BF','rdx = twelve-byte second-element output at rbp-65')
    branch('E8',array_element_va,'copy indexed second element through exact helper')
    for h,m in [('8B45C7','load second vector final dword'),('488D55DF','rdx = right-vector clone at rbp-33'),
        ('F20F1045BF','load second vector first eight bytes'),('488D4DEF','rcx = left-vector clone at rbp-17'),
        ('F20F1145DF','store right clone first eight bytes'),('F20F1045CF','load first vector first eight bytes'),
        ('8945E7','store right clone final dword'),('8B45D7','load first vector final dword'),
        ('F20F1145EF','store left clone first eight bytes'),('8945F7','store left clone final dword')]:literal(h,m)
    branch('E8',distance_helper_va,'call exact anonymous distance program with cloned pair')
    literal('41FFC5','increment r13d, zero-extending full r13')
    literal('F30F58F0','Single accumulation xmm6.low32 plus returned xmm0.low32')
    literal('453BEC','signed comparison r13d against fixed r12d limit')
    branch('0F8C',entry_va+42,'continue while signed counter is below fixed limit')
    literal('488B46'+f'{data_reference_offset:02X}','reload selected receiver data reference')
    literal('4885C0','test data reference')
    branch('0F84',null_failure_va,'null receiver data enters selected failure block')
    literal('F30F1040'+f'{max_distance_offset:02X}','load named maxDistance Single once')
    literal('0F2FC6','COMISS: named limit against accumulated Single')
    branch('73',entry_va+298,'ordered limit >= accumulation uses recalculated last element',short=True)
    for h,m in [('418B4608','load expected-position final dword'),('4C8D45EF','r8 = expected-position clone at rbp-17'),
        ('F2410F1006','load expected-position first eight bytes'),('488D55DF','rdx = source-position clone at rbp-33'),
        ('448B4D77','r9d = saved sixth incoming navmeshArea argument'),('488BCE','rcx = saved receiver'),
        ('8945F7','store expected clone final dword'),('418B4708','load source-position final dword'),
        ('8945E7','store source clone final dword'),('488D45AF','rax = straight-line out slot at rbp-81'),
        ('F20F1145EF','store expected clone first eight bytes'),('F2410F1007','load source-position first eight bytes'),
        ('48C744242800000000','zero sixth outgoing optional method context'),
        ('4889442420','supply fifth outgoing out-vector pointer'),('F20F1145DF','store source clone first eight bytes')]:literal(h,m)
    branch('E8',straight_line_va,'call selected instance straight-line checker')
    literal('84C0','test returned Boolean byte')
    branch('75',entry_va+288,'nonzero result selects complete out-vector copy',short=True)
    literal('0F57C0','zero every xmm0 bit on false result')
    literal('0F1145FF','zero entire sixteen-byte tagged return including tag and padding')
    branch('E9',hot_return_va,'return the all-zero tagged result through hot return')
    literal('F20F1045AF','load successful out-vector first eight bytes')
    literal('8B45B7','load successful out-vector final dword')
    branch('EB',entry_va+346,'join shared tagged payload stores',short=True)
    literal('33D2','zero optional final calculation context')
    literal('488BCB','rcx = saved path reference')
    branch('E8',calculate_corners_va,'recalculate before ordered-in-range last-element selection')
    literal('488B4B'+f'{corners_offset:02X}','reload final corners-array reference')
    literal('4885C9','test final array reference')
    branch('0F84',null_failure_va,'null final array enters selected failure block')
    literal('8B4118','eax = final array count DWORD at +24')
    literal('488D55EF','rdx = last-element out-vector at rbp-17')
    literal('FFC8','decrement eax as 32-bit arithmetic; zero-extend rax')
    literal('4C63C0','r8 = signExtend32(eax) for the current last-element index')
    branch('E8',array_element_va,'copy the independently reloaded array last element')
    literal('F20F1045EF','load last vector first eight bytes')
    literal('8B45F7','load last vector final dword')
    literal('89450B','store final dword at tagged output+12')
    literal('F20F114503','store first eight value bytes at tagged output+4')
    branch('E9',hot_return_va,'preserve prior nonzero tag and return replaced payload')
    if offset!=len(raw):raise ValueError(f'nullable-vector3-distance.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    return {'status':'complete-ordinary-nullable-vector3-distance-continuation-proved',
        'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,
        'countContextCellVa':cell,'loopLimitExpression':'signed32(low32(countProviderRax-1))',
        'counterBits':32,'loopComparisonsSigned':True,'arrayIndicesSignExtended32To64':True,
        'loopDistanceArguments':{'left':'first recalculation element i','right':'second recalculation element i+1'},
        'fixedPositiveLoopIterationCount':'L where L=signed32(low32(countProviderRax-1)); zero when L<=0',
        'accumulation':'sequential Single ADDSS from entry xmm6.low32, assumed zero by independently checked hot path',
        'limitReads':1,'limitComparedDirectlyWithoutSquaring':True,
        'limitBranch':'ordered maxDistance >= sum selects current last corner; ordered less or unordered selects straight-line fallback after normal COMISS',
        'fallbackArguments':{'receiver':'rsi -> rcx','sourcePosition':'r15 clone -> rdx',
            'expectPosition':'r14 clone -> r8','navmeshArea':'rbp+119 -> r9d','outPosition':'rbp-81 -> outgoing rsp+32',
            'optionalMethodContext':'zero qword at outgoing rsp+40'},
        'fallbackFalseClearsEntireTaggedResultBytes':16,'normalTrueAndLastPayloadCopyBytes':12,
        'normalTrueAndLastPreserveHotTag':True,'calculateCornersCallSites':4,
        'singleStablePathLengthProved':False,'countProviderReturnOrDispatchProved':False,
        'wholeManagedMethodOrPatchedPathProved':False,'runtimeExecutionKnown':False,
        'conditions':['Independent hot proof binds saved receiver/path/positions, frame, zero accumulator and tag-one return buffer',
            'Selected helper/callee bytes and typed declarations independently authenticated; calls complete normally and preserve required nonvolatile registers',
            'Valid field/frame/array/output buffers without incompatible callee writes; each indexed helper completes under its own low-DWORD bound and full-index conditions',
            'A single-path length interpretation additionally needs count-provider equality to array length and stable corner arrays/contents across every recalculation',
            'Normal Single accumulation and COMISS completion with explicit MXCSR; results are static conditional programs, not observed gameplay'],
        'evidenceBoundary':'Every ordinary continuation byte, signed loop arithmetic, repeated array/provider reads, direct Single threshold, cloned straight-line arguments and both tagged result paths. Count interface dispatch, a stable single navigation path, IFix/cold initialization and actual effects remain unresolved.'}
