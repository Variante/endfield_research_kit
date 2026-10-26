"""Complete selected concrete scalar consumers, with explicit dispatch guards.

The independently proved scalar cells supply displacements. These programs
prove loads, lower-lane conversion, output copies and delegated call arguments;
they do not observe dispatch state, lookup results, MXCSR or game execution.
"""
from __future__ import annotations

from typing import Any,Callable
from scripts.game_data.memorypack import inherited_reference_sources as types
from scripts.game_data.memorypack import inline_utf8_sources as paths
from scripts.game_data.memorypack import reference_conversion_sources as programs

LABEL='closedScalarConsumers'
MODE='concrete-key-cast-and-guarded-try-double-programs'
LOCAL_OPS={'0F5AC0':'cvtps2pd xmm0, xmm0'}


def signature(image: Any,method: list,result: tuple,parameters: list,*,static: bool,fail: Callable) -> None:
    image.validate_method_row(method,label=LABEL)
    m=image.metadata.methods[method[0]]
    rows=[types._type_row(image,m.return_type)]+[types._type_row(image,p.type_index) for p in image.metadata.parameters_for(m)]
    wanted=[(*result,False)]+parameters
    actual=[(r['kind'],r['name'],bool(bytes.fromhex(r['rawHex'])[11]&0x20)) for r in rows]
    if bool(m.flags&0x10)!=static or m.generic_container_index>=0 or actual!=wanted:
        fail('scalar-consumer-signature',{'static':static,'types':wanted},actual)


def _profile(image: Any,proof: dict,expected: list,branches: dict,fail: Callable) -> list:
    rows=proof['program']
    programs.validate_program(image,proof,extra_opcodes=LOCAL_OPS,fail=fail)
    if len(rows)!=len(expected):fail('scalar-consumer-program-size',len(expected),rows)
    for i,(row,wanted) in enumerate(zip(rows,expected,strict=True)):
        raw=bytes.fromhex(row[1])
        if wanted is not None and row[1]!=wanted:fail('scalar-consumer-program-instruction',[i,wanted],row)
        if i in branches:
            opcode,taken=branches[i]
            op=bytes.fromhex(opcode)
            if len(raw)!=len(op)+(1 if len(op)==1 else 4) or not raw.startswith(op):
                fail('scalar-consumer-branch-opcode',opcode,row)
            following=paths._target(row) if taken else row[0]+len(raw)
            if rows[i+1][0]!=following:fail('scalar-consumer-selected-edge',following,rows[i+1])
    return rows


def _call(row: list,method: list,fail: Callable) -> None:
    raw=bytes.fromhex(row[1])
    if len(raw)!=5 or raw[0]!=0xe8 or programs._target(row[0],raw)!=method[3]:
        fail('scalar-consumer-call-identity',method,row)


def _patch_index(row: list,fail: Callable) -> int:
    raw=bytes.fromhex(row[1])
    if len(raw)!=5 or raw[0]!=0xb9:fail('scalar-consumer-patch-argument','MOV ECX, Int32 dispatch index',row)
    return int.from_bytes(raw[1:],'little',signed=True)


def validate_consumers(image: Any,contract: dict,data_transfer: dict,*,fail: Callable) -> dict:
    if contract.get('mode')!=MODE or data_transfer.get('closedArguments')!=['float','double']:
        fail('scalar-consumer-scope',MODE,contract.get('mode'))
    cells={r['fieldName']:r['destinationOffset'] for r in data_transfer['fields']}
    if set(cells)!={'blackboardKey','useBlackboardKey','value'} or data_transfer.get('runtimeGenericTemplateOffsetsUsed') is not False:
        fail('scalar-consumer-cells','independently proved closed scalar cells',data_transfer)
    if any(type(v)is not int or not 16<=v<128 for v in cells.values()):
        fail('scalar-consumer-cell-width','actual bounded disp8 destinations',cells)
    declared='Beyond.Blackboard+BlackboardDouble'
    method=contract['patchCheckMethod']
    if method[1:3]!=['IFix.WrappersManagerImpl','IsPatched']:fail('scalar-consumer-patch-name','actual IsPatched definition',method)
    signature(image,method,(2,'bool'),[(8,'int',False)],static=True,fail=fail)
    lookup=contract['numberLookupMethod']
    if lookup[1:3]!=['Beyond.Blackboard','_TryGetNumber']:fail('scalar-consumer-lookup-name','actual _TryGetNumber definition',lookup)
    signature(image,lookup,(2,'bool'),[(14,'string',False),(13,'double',True)],static=False,fail=fail)
    results={}
    for name,result in [('keyGetter',(14,'string')),('castValue',(13,'double'))]:
        record=contract['records'][name];m=record['method']
        if m[1]!=declared or m[2]!=('get_blackboardFloatKey' if name=='keyGetter' else 'CastSerializeValueToReturnValue'):
            fail('scalar-consumer-method-name',name,m)
        signature(image,m,result,[],static=False,fail=fail)
        rows=record['program'];field=cells['blackboardKey' if name=='keyGetter' else 'value']
        expected=['4053','4883EC20','488BD9','33D2',None,None,'84C0',None,
                  ('488B43' if name=='keyGetter' else 'F30F1043')+f'{field:02X}']
        if name=='castValue':expected+=['0F5AC0']
        expected+=['4883C420','5B','C3']
        _profile(image,record,expected,{7:('75',False)},fail)
        if rows[0][0]!=m[3]:fail('scalar-consumer-entry',m[3],rows[0])
        dispatch_index=_patch_index(rows[4],fail);_call(rows[5],method,fail)
        results[name]={'fieldName':'blackboardKey' if name=='keyGetter' else 'value','sourceOffset':field,
            'readBytes':8 if name=='keyGetter' else 4,'resultRegister':'rax' if name=='keyGetter' else 'xmm0.low64',
            'dispatchCheckMethod':method,'dispatchIndex':dispatch_index,'dispatchResultCondition':False,
            'completeSelectedReturnProved':True,'coherentReadableScalarInstanceRequired':True,
            'ordinaryWin64ReturningCallsRequired':True}
        if name=='castValue':results[name].update(conversionInstruction='CVTPS2PD xmm0,xmm0',
            sourceLaneBits=32,resultLaneBits=64,mxcsrAndCpuExecutionObserved=False,
            concreteNumericResultOrExceptionOutcomeProved=False)
    record=contract['records']['tryValue'];m=record['method']
    if m[1:3]!=[declared,'TryGetValueInternal']:fail('scalar-consumer-try-name','current concrete TryGetValueInternal',m)
    signature(image,m,(2,'bool'),[(18,'Beyond.Blackboard',False),(13,'double',True)],static=False,fail=fail)
    prefix=['48895C2408','4889742410','57','4883EC40','488BD9','498BF0',None,'488BFA',
        '83B9E000000000',None,'488B81B8000000','4C8B00','4D85C0',None,None,None,
        '4885FF',None,'83B9E000000000','0F57C0','F20F11442430',None,
        '488B81B8000000','488B10','4885D2',None,None,None,'83B9E000000000',None,
        '488B81B8000000','488B10','4885D2',None,None,None,'4885DB',None,
        '807B'+f'{cells["useBlackboardKey"]:02X}'+'00',None]
    guards={i:(op,False) for i,op in [(9,'0F84'),(13,'0F84'),(15,'0F8F'),(17,'0F84'),
        (21,'0F84'),(25,'0F84'),(27,'0F8F'),(29,'0F84'),(33,'0F84'),(35,'0F8F'),(37,'0F84')]}
    suffix=['F20F1106','488B5C2450','488B742458','4883C440','5F','C3']
    for name,keyed in [('direct',False),('keyed',True)]:
        proof=record[name];rows=proof['program']
        middle=(['488B53'+f'{cells["blackboardKey"]:02X}','4C8D442430','4533C9','488BCF',None,'F20F10442430',None] if keyed else
                ['F30F1043'+f'{cells["value"]:02X}','B001','0F5AC0'])
        branches={**guards,39:('75',keyed)}
        if keyed:branches[46]=('EB',True)
        _profile(image,proof,prefix+middle+suffix,branches,fail)
        if rows[0][0]!=m[3]:fail('scalar-consumer-try-entry',m[3],rows[0])
        # The raw class/array guard representation is authenticated, not given an invented owner name.
        global_row=rows[6];raw=bytes.fromhex(global_row[1])
        if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x0d':fail('scalar-consumer-guard-cell','actual RIP-relative class cell load',global_row)
        comparisons=[]
        for at,prefix_bytes in [(14,b'\x41\x81\x78\x18'),(26,b'\x81\x7a\x18'),(34,b'\x81\x7a\x18')]:
            raw=bytes.fromhex(rows[at][1])
            if len(raw)!=len(prefix_bytes)+4 or not raw.startswith(prefix_bytes):
                fail('scalar-consumer-array-count-guard','exact count comparison with Int32 index',rows[at])
            comparisons.append(int.from_bytes(raw[-4:],'little',signed=True))
        if keyed:_call(rows[44],lookup,fail)
        results['try'+name.title()]={'selectorField':'useBlackboardKey','selectorOffset':cells['useBlackboardKey'],
            'selectorNonzeroCondition':keyed,'completeSelectedReturnProved':True,'outputRefRegister':'rsi',
            'outputWriteBytes':8,'guardedClassCellRva':global_row[0]+7+int.from_bytes(bytes.fromhex(global_row[1])[3:],'little',signed=True),
            'normalClassAndArrayGuardSelectionRequired':True,'guardSignedDwordAtMostComparedIndices':comparisons,
            'guardOwnerSemanticsProved':False,'runtimeGuardValuesObserved':False,
            'blackboardNonNullRequired':True,'coherentReadableScalarInstanceRequired':True,
            'writableOutputReferenceRequired':True,'ordinaryWin64ReturningCallsRequired':True}
        if keyed:results['tryKeyed'].update(keyField='blackboardKey',keyOffset=cells['blackboardKey'],
            lookupMethod=lookup,lookupReceiver='incoming blackboard',lookupKey='stored key reference',
            lookupOutput='distinct zero-initialized stack Double slot',lookupCompanionIsNull=True,
            returnedBoolean='actual lookup AL preserved by caller',lookupDoubleCopiedToOriginalOutput=True,
            lookupBodyOrFoundValueProved=False)
        else:results['tryDirect'].update(valueField='value',valueOffset=cells['value'],storedReadBytes=4,
            conversionInstruction='CVTPS2PD xmm0,xmm0',returnedBoolean=True,
            concreteNumericResultOrExceptionOutcomeProved=False)
    return {'records':results,'selectedConcreteConsumerFieldFlowProved':True,
        'runtimeGenericTemplateOffsetsUsed':False,'evidenceBoundary':'conditional',
        'runtimeExecutionKnown':False,'providerSelectionProved':False,'lookupBodyOrFoundValueProved':False,
        'alternateDispatchAndFailureParityKnown':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
