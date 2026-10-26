"""Complete selected constructor store programs and ready wrapper callbacks.

The proof is conditional on typed returning allocations, ready class flags and
disabled barriers. Engine factory returns remain opaque. No unwritten field
is assigned a default merely because an allocation is expected to be zeroed.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.memorypack.buffered_owned_sources import _memory
from scripts.game_data.memorypack.buffered_wrapper_lifecycle_sources import _match, _branch, _call
from scripts.game_data.memorypack.reference_conversion_sources import validate_program


def _profile(image: Any, record: dict, expected: list, *, fail: Callable) -> list:
    extra={}
    for at,h in record.get('classFlagTests',[]):
        raw=bytes.fromhex(h)
        if len(raw)!=7 or raw[:2] not in (b'\xf6\x83',b'\xf6\x05'):
            fail('constructor-class-test','TEST byte [rbx+disp32] or [rip+disp32], imm8',[at,h])
        base='rbx' if raw[1]==0x83 else 'rip'
        extra[h]=f'test byte [{base}+{int.from_bytes(raw[2:6],"little",signed=True)}], {raw[-1]}'
    validate_program(image,record['proof'],fail=fail,extra_opcodes=extra)
    rr=record['proof']['program'];_match(rr,expected,fail=fail)
    return rr


def _usage(image: Any, record: dict, row: list, wanted: str, opcode: str, *, fail: Callable) -> None:
    candidates=[u for u in record['typedUsages'] if u['instructionRva']==row[0]]
    if len(candidates)!=1 or candidates[0]['instructionHex']!=row[1] or not row[1].startswith(opcode) or candidates[0]['typeName']!=wanted:
        fail('constructor-typed-argument',{'instruction':row,'type':wanted,'registerOpcode':opcode},candidates)
    validate_typed_usage_context(image,candidates[0],label='runtimeConstructorSource')


def _rip_zero_flag(row: list, expected: int, *, fail: Callable) -> None:
    at,h=row;raw=bytes.fromhex(h)
    actual=at+len(raw)+int.from_bytes(raw[2:6],'little',signed=True) if len(raw)==7 else None
    if raw[:2]!=b'\x83\x3d' or raw[-1]!=0 or actual!=expected:
        fail('constructor-inline-barrier-flag',expected,{'instruction':row,'actual':actual})


def _field(record: dict, offset: int, wanted: str, *, fail: Callable) -> str:
    candidates=[r for r in record['fields'] if r['field'][2]==offset and r['field'][1]==wanted]
    if len(candidates)!=1:fail('constructor-field-owner',{'offset':offset,'type':wanted},candidates)
    return candidates[0]['qualified']


def scalar_constructors(image: Any, records: dict, *, value_offset: int, carrier: str, fail: Callable) -> dict:
    o=f'{value_offset:02X}'
    r=_profile(image,records['blackboardZero'],['4053','4883EC20','488BD9',None,'83B9E000000000',None,
        '33C0',f'8943{o}','4883C420','5B','C3'],fail=fail)
    _usage(image,records['blackboardZero'],r[3],carrier,'488B0D',fail=fail)
    _branch(r,5,b'\x74',False,fail=fail)
    r=_profile(image,records['blackboardSingle'],['4053','4883EC30','488BD9','0F29742420',None,'0F28F1',
        '83B9E000000000',None,f'F30F1173{o}','0F28742420','4883C430','5B','C3'],fail=fail)
    _usage(image,records['blackboardSingle'],r[4],carrier,'488B0D',fail=fail)
    _branch(r,7,b'\x74',False,fail=fail)
    return {'zeroStoredRawHex':'00000000','singleParameterBitsPreserved':True,'storedBits':32,
            'otherFieldsDefaulted':False,'completeReturns':2}


def class_initializer_ready(image: Any, proof: dict, entry: int, *, fail: Callable) -> dict:
    r=_profile(image,{'proof':proof},['48895C2418','4889742420','55','57','4154','4156','4157',
        '488BEC','4883EC70','0F29742460','488BF1','4533F6','44897530','4439B1E0000000',None,
        '4C8D5C2470','498B5B40','498B7348','0F28742460','498BE3','415F','415E','415C','5F','5D','C3'],fail=fail)
    if r[0][0]!=entry:fail('constructor-class-initializer-entry',entry,r[0])
    _branch(r,14,b'\x75',True,fail=fail)
    return {'classWordNonZeroRequired':True,'heapOrGlobalWrites':0,'calls':0,'completeReturnProved':True,
            'slowPathEffectsProved':False}


def curve_constructor(image: Any, record: dict, *, fail: Callable) -> dict:
    r=_profile(image,record,['4053','4883EC20',None,'488BD9','4885C0',None,'33C9','FFD0',
        '48894310','4883C420','5B','C3'],fail=fail)
    _branch(r,5,b'\x74',False,fail=fail)
    raw=bytes.fromhex(r[2][1])
    if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x05':fail('constructor-curve-cache-load','RIP-relative RAX load',r[2])
    return {'field':_field(record,16,'nint',fail=fail),'cachedFunctionCellRva':r[2][0]+7+int.from_bytes(raw[3:],'little',signed=True),
            'factoryArgumentIsNull':True,'storedOpaqueReturnBits':64,'actualFactoryTargetKnown':False,
            'engineFactoryEffectsProved':False,'allocationCalls':0,'opaqueFactoryCalls':1}


def target_constructor(image: Any, record: dict, direction_fields: list, calls: dict, barrier_flag: int, *, fail: Callable) -> dict:
    r=_profile(image,record,['48895C2410','57','4883EC20','488BF9','C7412001000000',None,None,
        '4885C0',None,None,'C6403101','48894758',None,'488B5C2438','4883C420','5F','C3'],fail=fail)
    _usage(image,record,r[5],'Beyond.Gameplay.Core.DirectionSettings','488B0D',fail=fail)
    _call(r,6,calls['allocation'],fail=fail);_branch(r,8,b'\x74',False,fail=fail)
    _rip_zero_flag(r[9],barrier_flag,fail=fail);_branch(r,12,b'\x74',True,fail=fail)
    direction={'fields':direction_fields}
    owner=[f for f in record['fields'] if f['field'][2]==32]
    if len(owner)!=1:fail('constructor-target-owner','one owned selector-owner enum',owner)
    return {'allocationCalls':1,'opaqueFactoryCalls':0,'explicitDefaults':[
        {'field':owner[0]['qualified'],'rawHex':'01000000'},
        {'field':_field(direction,49,'bool',fail=fail),'rawHex':'01'}],
        'referenceField':_field(record,88,'Beyond.Gameplay.Core.DirectionSettings',fail=fail),
        'otherFieldsDefaulted':False}


def vector_constructor(image: Any, record: dict, calls: dict, barrier_flag: int, value_offset: int, carrier: str, *, fail: Callable) -> dict:
    o=f'{value_offset:02X}'
    expected=['48895C2410','48896C2418','4889742420','57','4883EC70','0F29742460','0F297C2450',
        '440F29442440','0F28F3','0F28FA','440F28C1','488BF1',None,None,'488BD8','4885C0',None,None,
        '83B9E000000000',None,f'C743{o}00000000','48895E10',None,None,None,
        None,None,'488BD8','4885C0',None,None,'83B9E000000000',None,f'C743{o}00000000','48895E18',None,None,
        None,'F6833801000002',None,'48837B6000',None,'F6833801000020',None,'488BCB',None,None,
        '488BF8','F6833901000002',None,None,None,'488BCB',None,'4885FF',None,None,'83B9E000000000',None,
        f'C747{o}00000000','48897E20',None,None,'488B4610','4885C0',None,f'F3440F1140{o}',
        '488B4618','4885C0',None,f'F30F1178{o}','488B4620','4885C0',None,f'F30F1170{o}',
        '4C8D5C2470','498B5B18','498B6B20','498B7328','0F28742460','0F287C2450','450F2843D0','498BE3','5F','C3']
    r=_profile(image,record,expected,fail=fail)
    base_load=bytes.fromhex(r[22][1])
    if len(base_load)!=7 or base_load[:3]!=b'\x48\x8d\x2d':
        fail('constructor-vector-address-only-load','RIP-relative LEA into RBP without a memory write',r[22])
    profiling_test=bytes.fromhex(r[50][1])
    if len(profiling_test)!=7 or profiling_test[:2]!=b'\xf6\x05' or profiling_test[-1]!=0x80:
        fail('constructor-vector-profiling-test','TEST byte [RIP+disp32], 0x80',r[50])
    if record['classFlagTests']!=[r[n] for n in (38,42,48,50)]:
        fail('constructor-vector-class-tests',[r[n] for n in (38,42,48,50)],record['classFlagTests'])
    for n,op in ((12,'488B0D'),(25,'488B0D'),(37,'488B1D')):
        _usage(image,record,r[n],'Beyond.Blackboard+BlackboardDouble',op,fail=fail)
    for n in (17,30,56):_usage(image,record,r[n],carrier,'488B0D',fail=fail)
    for n in (13,26):_call(r,n,calls['allocation'],fail=fail)
    _call(r,45,calls['inlineAllocation'],fail=fail)
    _call(r,53,calls['classInitializer'],fail=fail)
    for n in (16,29,55):_branch(r,n,b'\x0f\x84',False,fail=fail)
    for n in (19,32,39,58):_branch(r,n,b'\x75',True,fail=fail)
    for n in (24,36,41,49,51,62):_branch(r,n,b'\x74',True,fail=fail)
    _branch(r,43,b'\x75',False,fail=fail)
    for n in (65,69,73):_branch(r,n,b'\x74',False,fail=fail)
    for n in (23,35,61):_rip_zero_flag(r[n],barrier_flag,fail=fail)
    return {'allocationCalls':3,'opaqueFactoryCalls':0,'componentFields':[
        _field(record,offset,'Beyond.Blackboard+BlackboardDouble',fail=fail) for offset in (16,24,32)],
        'finalComponentValueSources':['parameter0-float32-bits','parameter1-float32-bits','parameter2-float32-bits'],
        'completeFrameAndXmmPreservationProved':True,'inlineAllocationEffectsProved':False,'otherFieldsDefaulted':False}


def sub_speed_constructor(image: Any, record: dict, curve: dict, calls: dict, barrier: dict, value_offset: int, carrier: str, *, fail: Callable) -> dict:
    o=f'{value_offset:02X}'
    expected=['48895C2408','57','4883EC20','488BD9',None,None,'488BF8','4885C0',None,None,
        '83B9E000000000',None,'488D4B18',f'C747{o}00000000','48897B18',None,
        None,None,'488BF8','4885C0',None,None,'4885C0',None,'33C9','FFD0','48894710',
        '488D4B20','48897B20',None,None,None,'488BF8','4885C0',None,None,'83B9E000000000',None,
        f'C747{o}0000803F','488D4B30','48897B30','488B5C2430','4883C420','5F',None,
        *[z[1] for z in barrier['program']]]
    r=_profile(image,record,expected,fail=fail)
    for n in (4,30):_usage(image,record,r[n],'Beyond.Blackboard+BlackboardDouble','488B0D',fail=fail)
    for n in (9,35):_usage(image,record,r[n],carrier,'488B0D',fail=fail)
    _usage(image,record,r[16],'UnityEngine.AnimationCurve','488B0D',fail=fail)
    for n in (5,17,31):_call(r,n,calls['allocation'],fail=fail)
    for n,op in ((8,b'\x0f\x84'),(11,b'\x0f\x84'),(20,b'\x74'),(23,b'\x0f\x84'),(34,b'\x74'),(37,b'\x74')):
        _branch(r,n,op,False,fail=fail)
    raw=bytes.fromhex(r[21][1])
    if (len(raw)!=7 or raw[:3]!=b'\x48\x8b\x05' or
            r[21][0]+7+int.from_bytes(raw[3:],'little',signed=True)!=curve['cachedFunctionCellRva']):
        fail('constructor-same-curve-factory-cache',curve['cachedFunctionCellRva'],r[21])
    for n in (15,29):_call(r,n,calls['barrier'],fail=fail)
    _call(r,44,calls['barrier'],tail=True,fail=fail)
    if r[45:]!=barrier['program']:fail('constructor-sub-speed-barrier-tail',barrier['program'],r[45:])
    return {'allocationCalls':3,'opaqueFactoryCalls':1,'explicitDefaults':[
        {'field':_field(record,24,'Beyond.Blackboard+BlackboardDouble',fail=fail),'valueRawHex':'00000000'},
        {'field':_field(record,48,'Beyond.Blackboard+BlackboardDouble',fail=fail),'valueRawHex':'0000803F'}],
        'curveField':_field(record,32,'UnityEngine.AnimationCurve',fail=fail),'unwrittenFieldsAreNotDefaults':True}


def parent_constructor(image: Any, record: dict, records: dict, calls: dict, *, fail: Callable) -> dict:
    rr=record['proof']['program'];validate_program(image,record['proof'],fail=fail)
    _match(rr[:4],['48895C2408','57','4883EC30','488BD9'],fail=fail)
    n=4;allocations=[];literal_map={r['instructionRva']:r for r in record['literals']}
    while n<len(rr) and rr[n][1].startswith('488B0D'):
        begin=n
        _match(rr[n:n+5],[None,None,'488BF8','4885C0',None],fail=fail)
        _call(rr,n+1,calls['allocation'],fail=fail)
        branch=bytes.fromhex(rr[n+4][1]);_branch(rr,n+4,b'\x0f\x84' if len(branch)==6 else b'\x74',False,fail=fail)
        usage=next((u for u in record['typedUsages'] if u['instructionRva']==rr[n][0]),None)
        if usage is None:fail('constructor-parent-type-load','one current type usage',rr[n])
        type_name=usage['typeName'];_usage(image,record,rr[n],type_name,'488B0D',fail=fail)
        n+=5;value=None
        if rr[n][1]=='0F57DB':
            key='vector';wanted=['0F57DB','48C744242000000000','0F57D2','0F57C9','488BC8',None]
            _match(rr[n:n+6],wanted,fail=fail);_call(rr,n+5,records[key]['method'][3],fail=fail)
            value=['00000000']*3;n+=6
        elif rr[n][1].startswith('F30F100D'):
            key='blackboardSingle';_match(rr[n:n+4],[None,'4533C0','488BC8',None],fail=fail)
            literal=literal_map.get(rr[n][0]);raw=bytes.fromhex(rr[n][1])
            if literal is None or len(raw)!=8 or literal['instructionHex']!=rr[n][1] or (
                    rr[n][0]+8+int.from_bytes(raw[4:],'little',signed=True)!=literal['dataRva']):
                fail('constructor-parent-single-literal','same complete RIP float load',literal)
            actual=image.pe.bytes_at_va(image.pe.image_base+literal['dataRva'],4).hex().upper()
            if actual!=literal['rawHex']:fail('constructor-parent-literal-bits',literal['rawHex'],actual)
            _call(rr,n+3,records[key]['method'][3],fail=fail);value=actual;n+=4
        else:
            _match(rr[n:n+3],['33D2','488BC8',None],fail=fail)
            keys=[key for key in ('blackboardZero','target','subSpeed','curve') if records[key]['method'][1]==type_name]
            if len(keys)!=1:fail('constructor-parent-callee','one current typed parameterless constructor',keys)
            key=keys[0];_call(rr,n+2,records[key]['method'][3],fail=fail)
            if key=='blackboardZero':value='00000000'
            n+=3
        if records[key]['method'][1]!=type_name:fail('constructor-parent-callee-type',type_name,records[key]['method'])
        lea=_memory(bytes.fromhex(rr[n][1]),b'\x8d');store=_memory(bytes.fromhex(rr[n+1][1]),b'\x89')
        if (lea is None or store is None or lea['base']!='rbx' or lea['register']!='rcx' or lea['rex']&8==0 or
                store['base']!='rbx' or store['register']!='rdi' or store['rex']&8==0 or lea['offset']!=store['offset']):
            fail('constructor-parent-allocation-store','same saved allocation into the same owned parent slot',rr[n:n+2])
        field=_field(record,store['offset'],type_name,fail=fail);_call(rr,n+2,calls['barrier'],fail=fail)
        allocations.append({'field':field,'constructor':key,'typeName':type_name,'explicitValueRawHex':value,
                            'sourceInstructionRva':rr[begin][0]});n+=3
    booleans=[]
    while n<len(rr) and rr[n][1].startswith('C6'):
        raw=bytes.fromhex(rr[n][1]);mem=_memory(raw[:-1],b'\xc6')
        if mem is None or mem['base']!='rbx' or mem['registerIndex']!=0:
            fail('constructor-parent-byte-store','one owned C6 byte store',rr[n])
        booleans.append({'field':_field(record,mem['offset'],'bool',fail=fail),'rawHex':raw[-1:].hex().upper()});n+=1
    _match(rr[n:],['488B5C2440','4883C430','5F','C3'],fail=fail)
    if not allocations or len({r['field'] for r in allocations})!=len(allocations):
        fail('constructor-parent-allocation-coverage','nonempty distinct reference fields',allocations)
    return {'directAllocationCalls':len(allocations),'referenceDefaults':allocations,'explicitByteDefaults':booleans,
            'unwrittenFieldsAreNotDefaults':True,'completeConditionalReturnProved':True}


def preparation(image: Any, record: dict, calls: dict, data_type: str, *, fail: Callable) -> dict:
    prefix=['48895C2408','57','4883EC20','33DB','488BF9',None,None]
    tail=['488B5C2430','4883C420','5F','C3'];first_flag=None
    for name,count in (('cacheNonNull',9),('baseNull',11),('refresh',21)):
        proof=record['proofs'][name];validate_program(image,proof,fail=fail);r=proof['program']
        middle=['48395F18',None]
        if name!='cacheNonNull':middle+=['48395F10',None]
        if name=='refresh':middle+=['488B5F10',None,'488BCB',None,'48894718','488BCB',None,None,'488D4F18',None]
        _match(r,prefix+middle+tail,fail=fail)
        raw=bytes.fromhex(r[5][1])
        if len(raw)!=6 or raw[:2]!=b'\x38\x1d':fail('constructor-preparation-ready-flag','CMP byte [RIP], BL=0',r[5])
        flag=r[5][0]+6+int.from_bytes(raw[2:],'little',signed=True)
        if first_flag is not None and flag!=first_flag:fail('constructor-preparation-common-flag',first_flag,flag)
        first_flag=flag
        _branch(r,6,b'\x75',True,fail=fail);_branch(r,8,b'\x75',name=='cacheNonNull',fail=fail)
        if name!='cacheNonNull':_branch(r,10,b'\x74',name=='baseNull',fail=fail)
        if name=='refresh':
            for n in (12,17):_usage(image,record,r[n],data_type,'488B15',fail=fail)
            for n in (14,18):_call(r,n,calls['getterCast'],fail=fail)
            _call(r,20,calls['barrier'],fail=fail)
    return {'completeReadyReturns':3,'refreshOnlyWhenCacheNullAndBaseNonNull':True,
            'nonNullCacheEqualityWithBaseChecked':False,'selectedHeapWrites':{'cacheNonNull':0,'baseNull':0,'refresh':1},
            'initializationFlagRva':first_flag,'initializationSlowPathEffectsProved':False,'runtimeInvocationObserved':False}
