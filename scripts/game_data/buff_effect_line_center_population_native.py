"""Prove trail source-point transfer and compiled List<Vector3> append paths.

Creation calls and typed static contexts do not establish fresh runtime object
identity. Resizing, reference stability and actual execution retain explicit
conditions until their separate consumers and runtime inputs are established.
"""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
from scripts.game_data.il2cpp.context import unresolved_usage_index,method_spec_record,generic_method_candidates
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.integer_registers import decode_integer_register_instructions
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data import buff_effect_line_center_points_native as point_owner

SCHEMA='endfield.buff-effect-line-center-population-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_effect_line_center_population_native.json'
LABEL='buffEffectLineCenterPopulation'
TRAIL='HG.Rendering.Runtime.VFXTrailPointsTool'


def _fail(check,expected,actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} '
        f'expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _rip(g,row,prefix):
    raw=bytes.fromhex(row['bytes'])
    if len(raw)!=7 or raw[:len(prefix)]!=prefix:g.fail('rip-encoding',prefix.hex(),row)
    start=2 if len(prefix)==2 else 3
    return int(row['va'],16)+7+int.from_bytes(raw[start:start+4],'little',signed=True)


def _population(rows,pointers,points_offset):
    g=ProgramGrammar(rows,label=LABEL+'.getPoints')
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x40')
    guard=g.pattern(r'cmp \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x0')
    g.take('mov rsi, rdx','mov rdi, rcx');g.branch('jne','ready')
    for _ in range(3):
        g.pattern(r'lea rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]');g.call(pointers['metadataInit'])
    mark=g.pattern(r'mov \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x1')
    if _rip(g,guard,b'\x80\x3d')!=_rip(g,mark,b'\xc6\x05'):
        g.fail('same-initialization-guard','same byte cell',{'guard':guard,'store':mark})
    if bytes.fromhex(guard['bytes'])[-1]!=0 or bytes.fromhex(mark['bytes'])[-1]!=1:
        g.fail('initialization-guard-values','zero comparison and one write',{'guard':guard,'store':mark})
    g.mark('ready');g.pattern(r'mov ebx, 0x[0-9a-f]+')
    g.take('xor edx, edx','mov ecx, ebx');g.call(pointers['isPatched'])
    g.take('test al, al');g.branch('jne','patch');g.take('xor ebx, ebx')
    g.mark('loop');g.take(f'mov rax, [rdi+0x{points_offset:x}]','test rax, rax');g.branch('je','fatal')
    g.take('cmp ebx, [rax+0x18]');point_owner._branch(g,'jge','epilogue')
    item_context=g.pattern(r'mov r9, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('lea rcx, [rsp+0x20]','mov r8d, ebx','mov rdx, rax');item=g.call(pointers['getItem'])
    g.take('test rsi, rsi');g.branch('je','fatal')
    g.take('movsd xmm0, [rsp+0x20]','lea rdx, [rsp+0x30]','mov eax, [rsp+0x28]','mov rcx, rsi')
    add_context=g.pattern(r'mov r8, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('movsd [rsp+0x30], xmm0','mov [rsp+0x38], eax');add=g.call(pointers['addWrapper'])
    increment=g.row()
    if bytes.fromhex(increment['bytes'])!=b'\xff\xc3' or increment['text'] not in ('inc rbx','inc ebx'):
        g.fail('index-width','dword INC EBX',increment)
    g.branch('jmp','loop')
    g.mark('patch');g.take('xor edx, edx','mov ecx, ebx');g.call(pointers['getPatch'])
    g.take('test rax, rax');g.branch('jne','invoke-patch')
    g.mark('fatal');g.call(pointers['fatal']);g.take('int3')
    g.mark('invoke-patch');g.take('xor r9d, r9d','mov r8, rsi','mov rdx, rdi','mov rcx, rax');g.call(pointers['invokePopulationPatch'])
    g.mark('epilogue');g.take('mov rbx, [rsp+0x50]','mov rsi, [rsp+0x58]','add rsp, 0x40','pop rdi','ret');g.finish()
    return {'completeProgramChecked':True,'instructionsChecked':len(rows),'initialIndex':0,
        'sourceReference':'current this.points reloaded each iteration','destinationReference':'entry finalPoints held in RSI',
        'aggregateCopyBytes':12,'getItemCall':item,'addCall':add,
        'contexts':{'getItem':item_context,'add':add_context},
        'clearsDestination':False,'sourceAndDestinationReferencesEquated':False,
        'selection':'ordinary IFix false; initialized compatible metadata/context providers, valid source bounds and normal append returns',
        'finiteWholeSourceCopyRequires':'distinct source/destination storage, stable source reference and count, and compatible successful append/growth',
        'wholeSourcePopulationProved':False,'runtimeExecutionObserved':False}


def _add_wrapper(rows,pointer):
    g=ProgramGrammar(rows,label=LABEL+'.addWrapper')
    g.take('sub rsp, 0x38','movsd xmm0, [rdx]','mov eax, [rdx+0x8]',
        'lea rdx, [rsp+0x20]','movsd [rsp+0x20], xmm0','mov [rsp+0x28], eax')
    call=g.call(pointer);g.take('add rsp, 0x38','ret');g.finish()
    return {'completeProgramChecked':True,'valueCopyBytes':12,'receiverAndMethodInfoPreservedBeforeCall':True,'call':call}


def _append(rows,initialization_rows,pointers):
    g=ProgramGrammar(rows,label=LABEL+'.append')
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x30')
    version=g.take('inc [rcx+0x1c]')
    if bytes.fromhex(version['bytes'])!=b'\xff\x41\x1c':g.fail('version-width','dword increment',version)
    g.take('mov rsi, r8','mov r9, [rcx+0x10]','mov rdi, rdx','movsxd rax, [rcx+0x18]',
        'mov rbx, rcx','test r9, r9');g.branch('je','fatal')
    g.take('cmp eax, [r9+0x18]');point_owner._branch(g,'jae','resize')
    increment=g.take('lea rcx, [rax+0x1]')
    if bytes.fromhex(increment['bytes'])!=bytes.fromhex('8D4801'):g.fail('count-increment-width','dword LEA ECX',increment)
    g.take('mov [rbx+0x18], ecx','cmp eax, [r9+0x18]');point_owner._branch(g,'jae','array-index-failure')
    g.take('movsd xmm0, [rdx]','lea rax, [rax+rax*2]','lea rcx, [r9+rax*4]',
        'mov eax, [rdx+0x8]','movsd [rcx+0x20], xmm0','mov [rcx+0x28], eax',
        'mov rbx, [rsp+0x40]','mov rsi, [rsp+0x48]','add rsp, 0x30','pop rdi','ret')
    g.mark('resize');g.take('mov rax, [r8+0x20]','mov rcx, [rax+0xc0]','mov rax, [rcx+0x58]',
        'cmp [rax+0x20], 0x0');initialize=g.branch('je')
    g.mark('ready');g.take('mov eax, [rdi+0x8]','lea rdx, [rsp+0x20]','movsd xmm0, [rdi]',
        'mov rcx, rbx','mov [rsp+0x28], eax','mov rax, [rsi+0x20]',
        'movsd [rsp+0x20], xmm0','mov r8, [rax+0xc0]','mov r8, [r8+0x58]')
    resize=g.call(pointers['addWithResize'])
    g.take('mov rbx, [rsp+0x40]','mov rsi, [rsp+0x48]','add rsp, 0x30','pop rdi','ret')
    g.mark('fatal');g.call(pointers['fatal']);g.take('int3')
    g.mark('array-index-failure');g.call(pointers['arrayIndexFailure']);g.take('int3');g.finish()
    c=ProgramGrammar(initialization_rows,label=LABEL+'.append.initialize')
    c.take('mov rax, [r8+0x20]','mov rcx, [rax+0xc0]','mov rax, [rcx+0x58]','call [rax]','nop')
    edge=c.branch('jmp');c.finish()
    if initialize['target']!=int(initialization_rows[0]['va'],16) or edge['target']!=g.labels['ready']:
        g.fail('initialization-edges','checked cold initialization and resume label',{'branch':initialize,'resume':edge})
    return {'completeProgramAndInitializationWindowChecked':True,'fastAppendWriteBytes':12,'elementStride':12,
        'fastAppendIndex':'incoming compiled count slot','fastCountIncrement':1,'versionIncrementBeforePathSelection':True,
        'capacityPredicate':'unsigned incoming count < array length low dword','resizeCall':resize,
        'resizeValueCopyBytes':12,'runtimeResizeMethodInfoSelectionProved':False,'existingValuesPreservedAcrossResizeProved':False}


def _resize(rows,initialization_rows,pointers):
    g=ProgramGrammar(rows,label=LABEL+'.addWithResize')
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x20',
        'mov rax, [r8+0x20]','mov rbp, r8','movsxd rbx, [rcx+0x18]','mov rsi, rdx','mov rdi, rcx',
        'mov r9, [rax+0xc0]','mov rax, [r9+0x60]','cmp [rax+0x20], 0x0')
    initialize=g.branch('je');g.mark('ready')
    g.take('mov rax, [rbp+0x20]')
    minimum=g.row()
    if bytes.fromhex(minimum['bytes'])!=bytes.fromhex('8D5301') or minimum['text'] not in ('lea rdx, [rbx+0x1]','lea edx, [rbx+0x1]'):
        g.fail('minimum-width','dword LEA EDX',minimum)
    g.take('mov rcx, rdi',
        'mov r8, [rax+0xc0]','mov r8, [r8+0x60]');ensure=g.call(pointers['ensureCapacity'])
    g.take('mov rdx, [rdi+0x10]')
    increment=g.row()
    if bytes.fromhex(increment['bytes'])!=bytes.fromhex('8D4301') or increment['text'] not in ('lea rax, [rbx+0x1]','lea eax, [rbx+0x1]'):
        g.fail('count-increment-width','dword LEA EAX',increment)
    g.take('mov [rdi+0x18], eax','test rdx, rdx');g.branch('je','fatal')
    g.take('cmp ebx, [rdx+0x18]');point_owner._branch(g,'jae','array-index-failure')
    g.take('movsd xmm0, [rsi]','lea rcx, [rbx+rbx*2]','mov eax, [rsi+0x8]',
        'mov rbx, [rsp+0x30]','mov rbp, [rsp+0x38]','mov rsi, [rsp+0x40]',
        'movsd [rdx+0x20+rcx*4], xmm0','mov [rdx+0x28+rcx*4], eax',
        'add rsp, 0x20','pop rdi','ret')
    g.mark('fatal');g.call(pointers['fatal']);g.take('int3')
    g.mark('array-index-failure');g.call(pointers['arrayIndexFailure']);g.take('int3');g.finish()
    c=ProgramGrammar(initialization_rows,label=LABEL+'.resize.initialize')
    c.take('mov rax, [r8+0x20]','mov r9, [rax+0xc0]','mov rax, [r9+0x60]','call [rax]','nop')
    edge=c.branch('jmp');c.finish()
    if initialize['target']!=int(initialization_rows[0]['va'],16) or edge['target']!=g.labels['ready']:
        g.fail('initialization-edges','checked cold initialization and resume label',{'branch':initialize,'resume':edge})
    return {'completeProgramAndInitializationWindowChecked':True,'valueWriteBytes':12,'elementStride':12,
        'appendIndex':'count snapshot captured before EnsureCapacity','requestedMinimum':'int32 snapshot count + 1',
        'countWrittenAfterEnsureCapacity':True,'versionIncrementedHere':False,'ensureCapacityCall':ensure,
        'runtimeEnsureMethodInfoSelectionProved':False,'existingValuesPreservedAcrossResizeProved':False}


def _constructor(rows,pointers,offsets):
    g=ProgramGrammar(rows,label=LABEL+'.constructor')
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x20')
    guard=g.pattern(r'cmp \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x0')
    g.take('mov rbx, rcx');g.branch('jne','ready')
    for _ in range(2):
        g.pattern(r'lea rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]');g.call(pointers['metadataInit'])
    mark=g.pattern(r'mov \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x1')
    if _rip(g,guard,b'\x80\x3d')!=_rip(g,mark,b'\xc6\x05') or bytes.fromhex(guard['bytes'])[-1]!=0 or bytes.fromhex(mark['bytes'])[-1]!=1:
        g.fail('same-initialization-guard','same zero/one byte cell',{'guard':guard,'store':mark})
    g.mark('ready');g.take('xorps xmm2, xmm2')
    world=g.take(f'mov [rbx+0x{offsets["world"]:x}], 0x1')
    if bytes.fromhex(world['bytes'])[0]!=0xc6:g.fail('world-flag-width','byte assignment',world)
    g.take('xorps xmm0, xmm0','unpcklps xmm0, xmm2',f'movsd [rbx+0x{offsets["center"]:x}], xmm0',
        f'movss [rbx+0x{offsets["center"]+8:x}], xmm2')
    contexts={};allocation_calls=[]
    for role in ('points','temp'):
        contexts[role+'Type']=g.pattern(r'mov rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
        allocation_calls.append(g.call(pointers['allocateObject']))
        g.take('mov rdi, rax','test rax, rax');g.branch('je','fatal')
        contexts[role+'Constructor']=g.pattern(r'mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
        g.take('mov rcx, rax');g.call(pointers['listConstructor'])
        g.take(f'lea rcx, [rbx+0x{offsets[role]:x}]',f'mov [rbx+0x{offsets[role]:x}], rdi')
        g.call(pointers['writeBarrier'])
    g.take('xor edx, edx','mov [rbx+0x68], 0x1','mov rcx, rbx','mov rbx, [rsp+0x30]',
        'add rsp, 0x20','pop rdi');tail=g.branch('jmp')
    if tail['target']!=pointers['baseConstructor']:g.fail('base-constructor-tail',pointers['baseConstructor'],tail)
    g.mark('fatal');g.call(pointers['fatal']);g.take('int3');g.finish()
    return {'completeProgramChecked':True,'useWorldSpaceAssignedTrue':True,'centerOffsetInitializedToZeroBytes':12,
        'allocationCallSites':allocation_calls,'separateAllocationCalls':True,'sameReturnedObjectAssumed':False,
        'constructorThenReferenceStoreRoles':['points','temp'],'contexts':contexts,
        'baseConstructorTail':tail,'anonymousAncestorByteStore':{'offset':104,'value':1,'meaningProved':False},
        'allocatorFreshnessProved':False,'sourceTemporaryNonaliasingLifetimeProved':False,'runtimeExecutionObserved':False}


def _ensure_capacity(rows,initialization_rows,pointers,constants):
    g=ProgramGrammar(rows,label=LABEL+'.ensureCapacity')
    g.take('mov [rsp+0x10], rbx','push rdi','sub rsp, 0x20','mov rax, [rcx+0x10]',
        'mov rdi, r8','mov rbx, rcx','test rax, rax');g.branch('je','fatal')
    g.take('cmp [rax+0x18], edx');point_owner._branch(g,'jl','grow')
    g.take('mov rbx, [rsp+0x38]','add rsp, 0x20','pop rdi','ret')
    g.mark('grow');zero=g.take('cmp [rax+0x18], 0x0')
    if bytes.fromhex(zero['bytes'])!=bytes.fromhex('4883781800'):g.fail('array-empty-test-width','qword zero comparison',zero)
    g.take('mov [rsp+0x30], rsi');g.branch('je','empty-default')
    g.take('mov esi, [rax+0x18]');double=g.take('add esi, esi')
    if bytes.fromhex(double['bytes'])!=bytes.fromhex('03F6'):g.fail('capacity-double-width','dword ADD ESI, ESI',double)
    maximum=constants['maximum'];minimum=constants['emptyDefault']
    g.take(f'cmp esi, 0x{maximum:x}');g.branch('ja','ceiling')
    g.mark('compare-request');g.take('cmp esi, edx');point_owner._branch(g,'jl','request')
    g.mark('select-context');g.take('mov rax, [r8+0x20]','mov rcx, [rax+0xc0]',
        'mov rax, [rcx+0xc0]','cmp [rax+0x20], 0x0');initialize=g.branch('je')
    g.mark('ready');g.take('mov rax, [rdi+0x20]','mov edx, esi','mov rcx, rbx',
        'mov r8, [rax+0xc0]','mov r8, [r8+0xc0]','mov rsi, [rsp+0x30]',
        'mov rbx, [rsp+0x38]','add rsp, 0x20','pop rdi');tail=g.branch('jmp')
    if tail['target']!=pointers['setCapacity']:g.fail('capacity-tail',pointers['setCapacity'],tail)
    g.mark('empty-default');g.take(f'mov esi, 0x{minimum:x}');g.branch('jmp','compare-request')
    g.mark('request');g.take('mov esi, edx');g.branch('jmp','select-context')
    g.mark('ceiling');g.take(f'mov esi, 0x{maximum:x}');g.branch('jmp','compare-request')
    g.mark('fatal');g.call(pointers['fatal']);g.take('int3');g.finish()
    c=ProgramGrammar(initialization_rows,label=LABEL+'.ensure.initialize')
    c.take('mov rax, [r8+0x20]','mov rcx, [rax+0xc0]','mov rax, [rcx+0xc0]','call [rax]','nop')
    edge=c.branch('jmp');c.finish()
    if initialize['target']!=int(initialization_rows[0]['va'],16) or edge['target']!=g.labels['ready']:
        g.fail('initialization-edges','checked cold initialization and resume label',{'branch':initialize,'resume':edge})
    return {'completeProgramAndInitializationWindowChecked':True,'existingCapacityReadBits':32,'emptyArrayTestBits':64,
        'growthSelection':['if signed existingCapacity >= signed request: return',
            'candidate = emptyDefault when full array length equals zero; otherwise uint32(existingCapacity + existingCapacity)',
            'if unsigned candidate > maximum: candidate = maximum',
            'if signed candidate < signed request: candidate = request','tail set_Capacity(candidate)'],
        'constants':constants,'capacityTailCall':tail,'runtimeCapacityMethodInfoSelectionProved':False}


def _branch_le(g,label):
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)==2 and raw[0]==0x7e:relative=raw[1:]
    elif len(raw)==6 and raw[:2]==b'\x0f\x8e':relative=raw[2:]
    else:g.fail('branch-predicate','jle',row)
    target=at+len(raw)+int.from_bytes(relative,'little',signed=True)
    if row['text'] not in (f'jle 0x{target:x}',f'jcc 0x{target:x}'):g.fail('branch-decoding',hex(target),row)
    g.edges.append((target,label,row))


def _set_capacity(primary,cold,pointers):
    # The two windows are not contiguous. Prove their cross-window edges
    # explicitly instead of pretending that the intervening bytes belong here.
    g=ProgramGrammar(primary,label=LABEL+'.setCapacity')
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x30',
        'mov rsi, r8','mov edi, edx','mov rbx, rcx','cmp edx, [rcx+0x18]')
    insufficient=point_owner._branch(g,'jl')
    g.take('mov rax, [rcx+0x10]','test rax, rax');g.branch('je','fatal')
    g.take('cmp edi, [rax+0x18]');g.branch('je','epilogue')
    g.take('mov rcx, [r8+0x20]','mov rcx, [rcx+0xc0]','test edi, edi')
    zero=g.row();raw=bytes.fromhex(zero['bytes']);at=int(zero['va'],16)
    if len(raw)!=6 or raw[:2]!=b'\x0f\x8e':g.fail('capacity-zero-predicate','signed JLE',zero)
    zero_target=at+6+int.from_bytes(raw[2:],'little',signed=True)
    if zero['text'] not in (f'jle 0x{zero_target:x}',f'jcc 0x{zero_target:x}'):g.fail('capacity-zero-decoding',hex(zero_target),zero)
    g.take('mov rcx, [rcx+0x8]');g.call(pointers['resolveArrayClass'])
    g.take('mov edx, edi','mov rcx, rax');allocate=g.call(pointers['allocateArray'])
    g.take('cmp [rbx+0x18], 0x0','mov rdi, rax');_branch_le(g,'store-array')
    g.take('mov ecx, [rbx+0x18]','xor r9d, r9d')
    context=g.take('mov [rsp+0x28], 0x0')
    if bytes.fromhex(context['bytes'])!=bytes.fromhex('48C744242800000000'):
        g.fail('copy-context-width','zero qword trailing context argument',context)
    g.take('mov r8, rax','mov [rsp+0x20], ecx','xor edx, edx','mov rcx, [rbx+0x10]')
    copy=g.call(pointers['arrayCopy'])
    g.mark('store-array');g.take('mov [rbx+0x10], rdi')
    g.mark('write-barrier');g.take('lea rcx, [rbx+0x10]');g.call(pointers['writeBarrier'])
    g.mark('epilogue');g.take('mov rbx, [rsp+0x40]','mov rsi, [rsp+0x48]',
        'add rsp, 0x30','pop rdi','ret')
    g.mark('fatal');g.call(pointers['fatal']);g.take('int3');g.finish()
    c=ProgramGrammar(cold,label=LABEL+'.setCapacity.cold')
    c.mark('empty-array');c.take('mov rcx, [rcx]');c.call(pointers['resolveArrayClass'])
    c.take('cmp [rax+0xe0], 0x0');c.branch('jne','empty-class-ready')
    c.take('mov rcx, rax');c.call(pointers['classInit'])
    c.mark('empty-class-ready');c.take('mov rax, [rsi+0x20]','mov rcx, [rax+0xc0]','mov rcx, [rcx]')
    c.call(pointers['resolveArrayClass']);c.take('mov rcx, [rax+0xb8]','mov rax, [rcx]','mov [rbx+0x10], rax')
    resume=c.branch('jmp')
    c.mark('insufficient');c.take('xor r8d, r8d','mov edx, 0x15','mov ecx, 0xf')
    c.call(pointers['capacityOutOfRange']);c.take('int3');c.finish()
    if (zero_target!=c.labels['empty-array'] or insufficient['target']!=c.labels['insufficient']
            or resume['target']!=g.labels['write-barrier']):
        g.fail('cross-window-edges','checked zero-capacity, rejection and write-barrier targets',
            {'zero':zero_target,'insufficient':insufficient,'resume':resume})
    return {'completePrimaryAndColdWindowChecked':True,'capacityArgumentBits':32,
        'tooSmallPredicate':'signed requested capacity < current compiled count',
        'equalExistingCapacityReturns':True,'positiveCapacityAllocationCall':allocate,
        'existingPositiveCountCopyCall':copy,
        'arrayCopyArguments':{'source':'current list items','sourceIndex':0,'destination':'allocated array',
            'destinationIndex':0,'length':'current compiled list count'},
        'arrayCopyTrailingContext':{'slot':'caller RSP+0x28','value':0,'bits':64,'consumerReadProved':False},
        'arrayReferenceReplacedAfterCopyReturns':True,'countWritten':False,'versionWritten':False,
        'emptyStaticArraySelectionConditional':True,'allocatedArrayTypeAndFreshnessProved':False,
        'arrayCopyImplementationProved':False,'existingValuesPreservedAcrossResizeProved':False}


def _list_constructor(rows,pointers):
    g=ProgramGrammar(rows,label=LABEL+'.listConstructor')
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x20','mov rax, [rdx+0x20]',
        'mov rdi, rcx','mov rbx, rdx','mov rcx, [rax+0xc0]','mov rcx, [rcx]')
    g.call(pointers['resolveArrayClass']);g.take('cmp [rax+0xe0], 0x0');g.branch('je','initialize')
    g.mark('ready');g.take('mov rax, [rbx+0x20]','mov rcx, [rax+0xc0]','mov rcx, [rcx]')
    g.call(pointers['resolveArrayClass']);g.take('mov rcx, [rax+0xb8]','mov rax, [rcx]',
        'lea rcx, [rdi+0x10]','mov [rdi+0x10], rax','mov rbx, [rsp+0x30]',
        'add rsp, 0x20','pop rdi');tail=g.branch('jmp')
    if tail['target']!=pointers['writeBarrier']:g.fail('write-barrier-tail',pointers['writeBarrier'],tail)
    g.mark('initialize');g.take('mov rcx, rax');g.call(pointers['classInit']);g.branch('jmp','ready');g.finish()
    return {'completeProgramChecked':True,'itemsReferenceAssignedFromSelectedClassStaticStorage':True,
        'countWritten':False,'versionWritten':False,'zeroedAllocationAndEmptyArrayRequiresSeparateEvidence':True,
        'runtimeContextAndStaticArraySelectionProved':False}


def _void_list_method(image,selected,method,parameters):
    definition=selected.index.types['System.Collections.Generic.List`1']
    if (method.declaring_type!=definition.index or definition.generic_container_index<0
            or method.generic_container_index>=0 or method.flags&0x10):
        _fail('generic-list-instance','selected instance method of open List<T>',method.index)
    section=image.metadata.sections['genericContainers'];at=section.offset+definition.generic_container_index*16
    if not section.offset<=at<=section.offset+section.size-16:_fail('generic-list-container-bound','complete class container',at)
    owner,count,is_method,parameter=struct.unpack_from('<iiii',image.metadata.buf,at)
    if (owner,count,is_method)!=(definition.index,1,0) or parameter<0:
        _fail('generic-list-container','one selected class parameter',(owner,count,is_method,parameter))
    args=list(image.metadata.parameters_for(method))
    if len(args)!=len(parameters) or method.parameter_count!=len(parameters):_fail('list-argument-count',len(parameters),len(args))
    records=[]
    for type_index,kind in [(method.return_type,0x01),*[(p.type_index,kind) for p,kind in zip(args,parameters)]]:
        raw=image.pe.bytes_at_va(selected.type_pointer(type_index),16)
        if len(raw)!=16 or raw[10]!=kind or raw[11]&0x7f or kind==0x13 and int.from_bytes(raw[:8],'little')!=parameter:
            _fail('list-void-value-signature','undecorated void/Int32/same class T',raw.hex())
        records.append(raw.hex().upper())
    return {'methodIndex':method.index,'selectedClassParameterIndex':parameter,'instanceMethod':True,
        'returnNativeTypeHex':records[0],'parameterNativeTypeHex':records[1:]}


def _context(image,selected,row,spec,role):
    prefixes={'getItem':b'\x4c\x8b\x0d','add':b'\x4c\x8b\x05',
        'pointsType':b'\x48\x8b\x0d','tempType':b'\x48\x8b\x0d',
        'pointsConstructor':b'\x48\x8b\x15','tempConstructor':b'\x48\x8b\x15'}
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)!=7 or raw[:3]!=prefixes[role]:_fail('context-register:'+role,prefixes[role].hex(),row)
    cell=at+7+int.from_bytes(raw[3:],'little',signed=True);word=image.pe.bytes_at_va(cell,8)
    tag=1 if role.endswith('Type') else 6
    if spec['tag']!=tag or spec['usageRawHex']!=word.hex().upper():_fail('context-tag-or-word:'+role,spec,word.hex())
    result={'role':role,'cellRva':cell-image.pe.image_base,'usageRawHex':word.hex().upper(),'runtimeInitializationProved':False}
    if tag==1:
        ti=unresolved_usage_index(word,image.registration['typesCount'],tag=1,source=str(image.gameassembly),offset=cell)
        typ=selected.type_name(ti);native=image.pe.bytes_at_va(selected.type_pointer(ti),16).hex().upper()
        if ti!=spec['typeIndex'] or typ!='System.Collections.Generic.List`1<UnityEngine.Vector3>' or native!=spec['nativeTypeHex']:
            _fail('typed-allocation-context:'+role,spec,{'typeIndex':ti,'type':typ,'nativeTypeHex':native})
        representation=closed_generic_reference_extent(selected,ti)
        result.update(typeIndex=ti,type=typ,referenceRepresentation=representation)
    else:
        si=unresolved_usage_index(word,image.registration['methodSpecsCount'],tag=6,source=str(image.gameassembly),offset=cell)
        record_at=int(image.registration['methodSpecs'],16)+si*12;record=image.pe.bytes_at_va(record_at,12)
        definition,ci,mi=method_spec_record(record,len(image.metadata.methods),image.registration['genericInstsCount'],source=str(image.gameassembly),offset=record_at)
        method=image.metadata.methods[definition];actual=[definition,image.type_name(method.declaring_type),image.metadata.string(method.name_index)]
        args=image.instantiations.resolve(ci).arguments;names=[runtime_type_name(image.pe,image.metadata,a.type_pointer_va) for a in args]
        method_args=image.instantiations.resolve(mi).arguments
        name='get_Item' if role=='getItem' else 'Add' if role=='add' else '.ctor'
        if (actual[1:]!=['System.Collections.Generic.List`1',name] or names!=['UnityEngine.Vector3'] or method_args
                or si!=spec['methodSpecIndex'] or actual!=spec['definition'] or record.hex().upper()!=spec['recordRawHex']
                or [a.raw_type_record_hex for a in args]!=spec['classArgumentRawHex']):
            _fail('typed-method-context:'+role,spec,{'methodSpecIndex':si,'definition':actual,'classArguments':names})
        vector=selected.index.types['UnityEngine.Vector3'];value=bytes.fromhex(args[0].raw_type_record_hex)
        if len(value)!=16 or value[10]!=0x11 or value[11]&0x7f or int.from_bytes(value[:8],'little')!=vector.index:
            _fail('closed-vector-value','selected undecorated Vector3',value.hex())
        declaration=(point_owner._list_declaration(image,selected,method,'getItem') if role=='getItem' else
            _void_list_method(image,selected,method,[0x13] if role=='add' else []))
        result.update(methodSpecIndex=si,definition=actual,classArguments=names,declaration=declaration)
    return result


def _array_copy_declaration(image,index,selected,pointer):
    aliases=index.names_by_pointer.get(pointer,[])
    if len(aliases)!=1 or (aliases[0]['type'],aliases[0]['method'])!=('System.Array','Copy'):
        _fail('array-copy-owner','one selected named Array.Copy entry',aliases)
    method=image.metadata.methods[aliases[0]['methodIndex']]
    args=list(image.metadata.parameters_for(method))
    names=[selected.type_name(p.type_index) for p in args]
    expected=['System.Array','int','System.Array','int','int']
    if (not method.flags&0x10 or method.generic_container_index>=0 or method.parameter_count!=5
            or names!=expected or selected.type_name(method.return_type)!='void'
            or image.method_pointer_va(method)!=pointer):
        _fail('array-copy-static-abi','void static Copy(Array,int,Array,int,int)',
            {'parameters':names,'parameterCount':method.parameter_count,'flags':method.flags,
             'genericContainerIndex':method.generic_container_index,'returnType':selected.type_name(method.return_type),
             'actualPointer':image.method_pointer_va(method),'expectedPointer':pointer})
    records=[]
    for ti,kind in [(method.return_type,1),*[(p.type_index,kind) for p,kind in zip(args,[0x12,8,0x12,8,8])]]:
        raw=image.pe.bytes_at_va(selected.type_pointer(ti),16)
        if len(raw)!=16 or raw[10]!=kind or raw[11]&0x7f or kind==0x12 and int.from_bytes(raw[:8],'little')!=index.types['System.Array'].index:
            _fail('array-copy-undecorated-signature','selected Array/Int32/Boolean/void values',raw.hex())
        records.append(raw.hex().upper())
    return {'methodIndex':method.index,'returnType':'void','parameterTypes':names,
        'returnNativeTypeHex':records[0],'parameterNativeTypeHex':records[1:],
        'abi':{'source':'rcx','sourceIndex':'edx','destination':'r8','destinationIndex':'r9d',
            'length':'caller RSP+0x20'},
        'trailingContextArgument':{'slot':'caller RSP+0x28','managedParameter':False,
            'il2cppMethodInfoConvention':True,'consumerReadProved':False},'implementationProved':False}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    expected={'getPoints','constructor','addWrapper','append','resize','ensureCapacity','setCapacity','listConstructor'}
    if (contract.get('scope')!='conditional-initial-source-transfer-and-construction-grow-flow'
            or set(contract.get('programs',{}))!=expected or len(contract.get('fields',[]))!=4
            or len(contract.get('declarations',[]))!=2 or len(contract.get('contexts',{}))!=6):
        _fail('contract-shape','eight programs, four fields, two declarations and six static contexts',contract.get('scope'))
    return contract


def _validate_image(image:Any,contract:dict)->dict:
    index=BodyIndex(image);selected=NativeReferenceContext(image,index=index);base=image.pe.image_base
    point_contract=point_owner._contract()
    if contract['nativeInputs']!=point_contract['nativeInputs']:_fail('same-point-build',point_contract['nativeInputs'],contract['nativeInputs'])
    point_proof=point_owner._validate_image(image,point_contract)
    offsets={};expected_fields={'points':('points','System.Collections.Generic.List`1<UnityEngine.Vector3>'),
        'temp':('m_tempPoints','System.Collections.Generic.List`1<UnityEngine.Vector3>'),
        'center':('centerOffset','UnityEngine.Vector3'),'world':('useWorldSpace','bool')}
    for field in contract['fields']:
        role=field['role']
        if role not in expected_fields or role in offsets:_fail('field-role',list(expected_fields),role)
        name,typ=expected_fields[role]
        if field['field']!=TRAIL+'::'+name or field['owner']!=TRAIL or field['type']!=typ:
            _fail('typed-field',expected_fields[role],field)
        actual=selected.field(field['field'])
        if actual!=(field['owner'],field['type'],field['offset']):_fail('field:'+field['field'],field,actual)
        offsets[role]=field['offset']
    for role in ('points','temp','center'):
        previous=next(f for f in point_proof['fields'] if f['role']==role)
        if offsets[role]!=previous['offset']:_fail('same-point-field:'+role,previous['offset'],offsets[role])
    programs={}
    for role,program in contract['programs'].items():
        pointer=base+program['entryRva']
        owned=sorted(set([(pointer,index.extents.get(pointer,0))]+
            [(at,at+size) for at,size in index.chained_fragments.get(pointer,())]))
        windows=program['windows'];actual=[(base+w['startRva'],base+w['endRva']) for w in windows]
        if actual!=owned:_fail('complete-owned-program:'+role,actual,owned)
        image.check_windows(windows,label=LABEL)
        programs[role]=[decode_integer_register_instructions(image.mapper,image.window_bytes(w),base+w['startRva']) for w in windows]
    for declaration in contract['declarations']:
        method=image.metadata.methods[declaration['method'][0]]
        actual={'method':[method.index,image.type_name(method.declaring_type),image.metadata.string(method.name_index),image.method_pointer_va(method)-base],
            'flags':method.flags,'returnType':selected.type_name(method.return_type),
            'returnNativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(method.return_type),16).hex().upper(),
            'parameters':[{'name':image.metadata.string(p.name_index),'type':selected.type_name(p.type_index),
                'nativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(p.type_index),16).hex().upper()} for p in image.metadata.parameters_for(method)]}
        if actual!=declaration or method.flags&0x10 or method.generic_container_index>=0:
            _fail('instance-declaration',declaration,actual)
        role='getPoints' if declaration['method'][2]=='_GetPoints' else 'constructor'
        expected_parameters=['System.Collections.Generic.List`1<UnityEngine.Vector3>'] if role=='getPoints' else []
        if (actual['method'][1:3]!=[TRAIL,'_GetPoints' if role=='getPoints' else '.ctor'] or actual['returnType']!='void'
                or [p['type'] for p in actual['parameters']]!=expected_parameters
                or actual['method'][3]!=contract['programs'][role]['entryRva']):
            _fail('trail-program-declaration',role,actual)
        ret=bytes.fromhex(actual['returnNativeTypeHex'])
        if len(ret)!=16 or ret[10]!=0x01 or ret[11]&0x7f:_fail('void-instance-abi','selected undecorated void',ret.hex())
        if role=='getPoints':
            p=next(iter(image.metadata.parameters_for(method)))
            representation=closed_generic_reference_extent(selected,p.type_index)
            if representation['type']!=expected_parameters[0]:_fail('population-reference-argument',expected_parameters[0],representation)
    if contract['programs']['getPoints']['entryRva']!=point_contract['callTargets']['getPoints']:
        _fail('called-population-entry',point_contract['callTargets']['getPoints'],contract['programs']['getPoints']['entryRva'])
    pointers={role:base+rva for role,rva in contract['callTargets'].items()}
    for role,names in contract['namedCallTargets'].items():
        if index.names_of(pointers[role])!=names:_fail('named-call:'+role,names,index.names_of(pointers[role]))
    expected_window_counts={'getPoints':1,'constructor':1,'addWrapper':1,'append':2,'resize':2,'ensureCapacity':5,'setCapacity':2,'listConstructor':1}
    for role,n in expected_window_counts.items():
        if len(programs[role])!=n:_fail('checked-window-count:'+role,n,len(programs[role]))
    population=_population(programs['getPoints'][0],pointers,offsets['points'])
    constructor=_constructor(programs['constructor'][0],pointers,offsets)
    wrapper=_add_wrapper(programs['addWrapper'][0],pointers['append'])
    append=_append(programs['append'][0],programs['append'][1],pointers)
    resize=_resize(programs['resize'][0],programs['resize'][1],pointers)
    ensure=_ensure_capacity([row for w in programs['ensureCapacity'][:4] for row in w],programs['ensureCapacity'][4],pointers,contract['capacityConstants'])
    capacity=_set_capacity(programs['setCapacity'][0],programs['setCapacity'][1],pointers)
    list_constructor=_list_constructor(programs['listConstructor'][0],pointers)
    array_copy_declaration=_array_copy_declaration(image,index,selected,pointers['arrayCopy'])
    for role,target in [('addWrapper','addWrapper'),('append','append'),('resize','addWithResize'),
            ('ensureCapacity','ensureCapacity'),('setCapacity','setCapacity'),('listConstructor','listConstructor')]:
        if pointers[target]!=base+contract['programs'][role]['entryRva']:_fail('called-program:'+role,contract['programs'][role]['entryRva'],pointers[target])
    if pointers['getItem']!=base+point_contract['programs']['getItem']['entryRva']:_fail('same-checked-vector-getter',point_contract['programs']['getItem']['entryRva'],pointers['getItem'])
    context_rows={**population['contexts'],**constructor['contexts']}
    if set(context_rows)!=set(contract['contexts']):_fail('context-roles',list(context_rows),list(contract['contexts']))
    contexts=[_context(image,selected,context_rows[role],spec,role) for role,spec in contract['contexts'].items()]
    code=image.mapper.code_registration_summary(image.pe,image.code_registration)
    table_at=int(image.registration['genericMethodTable'],16);table_raw=image.pe.bytes_at_va(table_at,image.registration['genericMethodTableCount']*16)
    matches=generic_method_candidates(table_raw,image.registration['genericMethodTableCount'],image.registration['methodSpecsCount'],
        {c['methodSpecIndex'] for c in contexts if 'methodSpecIndex' in c},code['genericMethodPointersCount'],code['invokerPointersCount'],source=str(image.gameassembly),offset=table_at)
    for match in matches:match['methodPointerRva']=image.pe.u64_at_va(int(code['genericMethodPointers'],16)+match['indices'][0]*8)-base
    current=[{k:r[k] for k in ('tableIndex','methodSpecIndex','rawHex','indices','methodPointerRva')} for r in matches]
    if current!=contract['genericMethodTableMatches']:_fail('all-static-context-table-matches',contract['genericMethodTableMatches'],current)
    for role,target in [('getItem','getItem'),('pointsConstructor','listConstructor'),('tempConstructor','listConstructor')]:
        si=next(c['methodSpecIndex'] for c in contexts if c['role']==role)
        targets={m['methodPointerRva'] for m in current if m['methodSpecIndex']==si}
        if targets!={contract['callTargets'][target]}:_fail('direct-static-provider:'+role,contract['callTargets'][target],targets)
    return {'fields':contract['fields'],'population':population,'constructor':constructor,'addWrapper':wrapper,
        'append':append,'addWithResize':resize,'ensureCapacity':ensure,'setCapacity':capacity,'listConstructor':list_constructor,
        'staticContexts':contexts,'selectedGenericMethodTableMatches':current,'arrayCopyDeclaration':array_copy_declaration,
        'pointArithmeticAndWritebackRevalidated':True,'originalSourceToAppendValueTransferProved':True,
        'conditionalWholeSourceCopyWithoutResizeProved':True,
        'conditionalWholeSourceCopyWithoutResizeSelection':'ordinary paths; initially zero destination count, stable nonnegative source count/reference/values, distinct source/destination headers, valid nonoverlapping or same-index storage, and sufficient destination array capacity for every append',
        'ordinaryConstructorReferenceStoresProved':True,
        'compiledGrowthSelectionAndFinalAppendProved':True,'initialPointPopulationProved':False,
        'existingValuesPreservedAcrossResizeProved':False,'allocationFreshnessProved':False,
        'sourceTemporaryNonaliasingLifetimeProved':False,'rendererSubmissionProved':False,'runtimeExecutionObserved':False}


def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None)->dict:
    contract=_contract();pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched','detail':'Selected UnityPlayer missing or different','nativeInputs':pins}
    result=_validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():return {'status':'mismatched','detail':'Selected native inputs changed during population validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
