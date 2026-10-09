"""Authenticate trail point arithmetic and its compiled per-iteration writeback.

The complete caller is checked, while Unity internal-call geometry, initial
list population, compatible runtime objects and renderer submission retain
separate evidence boundaries. A successful arithmetic proof is not observed
execution or an unconditional end-to-end deformation proof.
"""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import unresolved_usage_index, method_spec_record, generic_method_candidates
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.sse_lanes import decode_lane_transfer_instructions
from scripts.game_data.il2cpp.vector3_value_leaves import validate_vector3_value_leaf
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar

SCHEMA = 'endfield.buff-effect-line-center-points-native-contract.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_points_native.json'
LABEL = 'buffEffectLineCenterPoints'
TRAIL = 'HG.Rendering.Runtime.VFXTrailPointsTool'


def _fail(check, expected, actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} '
                     f'expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _branch(g, condition, label=None):
    if condition not in ('jl', 'jge', 'jae'):
        return g.branch(condition, label)
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    code = {'jl':12, 'jge':13, 'jae':3}[condition]
    if len(raw) == 2 and raw[0] == 0x70+code:
        relative = raw[1:]
    elif len(raw) == 6 and raw[:2] == bytes((0x0f, 0x80+code)):
        relative = raw[2:]
    else:
        g.fail('branch-predicate', condition, row)
    target = at+len(raw)+int.from_bytes(relative, 'little', signed=True)
    if row['text'] not in (f'{condition} 0x{target:x}', f'jcc 0x{target:x}'):
        g.fail('branch-decoding', hex(target), row)
    if label is not None: g.edges.append((target, label, row))
    return {**row, 'target':target, 'predicate':condition}


def _counter(g, operation, register):
    # The selected subset mapper spells the no-REX FF forms with 64-bit
    # registers. Original bytes establish the actual 32-bit counter width.
    raw = {'dec-eax':'FFC8', 'inc-edi':'FFC7'}[operation+'-'+register]
    row = g.row()
    if bytes.fromhex(row['bytes']) != bytes.fromhex(raw):
        g.fail('signed-int32-counter', raw, row)
    if row['text'] not in (f'{operation} {register}', f'{operation} r'+register[1:]):
        g.fail('counter-decoding', operation+' '+register, row)


def _apply_offset(rows: list[dict], pointers: dict, offsets: dict) -> dict:
    g = ProgramGrammar(rows, label=LABEL+'.applyOffset')
    points, temp, center = (offsets[k] for k in ('points','temp','center'))
    g.take('mov rax, rsp','mov [rax+0x8], rbx','mov [rax+0x10], rsi',
        'mov [rax+0x18], rdi','mov [rax+0x20], r14','push rbp',
        'lea rbp, [rax-0x98]','sub rsp, 0x190','mov rbx, rcx','movaps [rax-0x18], xmm6')
    patch_id = g.pattern(r'mov edi, 0x[0-9a-f]+')
    g.take('xor edx, edx','mov ecx, edi'); g.call(pointers['isPatched'])
    g.take('test al, al'); g.branch('jne','patch')
    g.take(f'mov rax, [rbx+0x{points:x}]','test rax, rax'); g.branch('je','fatal')
    g.take('cmp [rax+0x18], 0x2'); _branch(g,'jl','epilogue')
    g.take(f'mov rcx, [rbx+0x{temp:x}]','test rcx, rcx'); g.branch('je','fatal')
    version = g.take('inc [rcx+0x1c]')
    if bytes.fromhex(version['bytes']) != bytes.fromhex('FF411C'):
        g.fail('clear-version-width','dword increment',version)
    clear = g.take('and [rcx+0x18], 0x0')
    if bytes.fromhex(clear['bytes']) != bytes.fromhex('83611800'):
        g.fail('clear-count-width','dword AND zero',clear)
    g.take('xor edx, edx','mov rcx, rbx'); g.call(pointers['zeroPredicate'])
    g.take('test al, al'); g.branch('je','epilogue')
    g.take(f'mov rdx, [rbx+0x{temp:x}]','xor r8d, r8d','mov rcx, rbx')
    populate = g.call(pointers['getPoints']); g.take('mov edi, 0x1')
    g.mark('loop'); g.take(f'mov rax, [rbx+0x{temp:x}]','test rax, rax'); g.branch('je','fatal')
    g.take('cmp edi, [rax+0x18]'); _branch(g,'jge','epilogue')
    item_context = g.pattern(r'mov r9, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('lea rcx, [rsp+0x20]','mov r8d, edi','mov rdx, rax'); item = g.call(pointers['getItem'])
    g.take('xor edx, edx','mov rcx, rbx'); g.call(pointers['getTransform'])
    g.take('test rax, rax'); g.branch('je','fatal')
    g.take('mov ecx, [rsp+0x28]','lea r8, [rsp+0x30]','movsd xmm0, [rsp+0x20]',
        'xor r9d, r9d','mov [rsp+0x38], ecx','mov rdx, rax','lea rcx, [rbp-0x20]',
        'movsd [rsp+0x30], xmm0'); transform = g.call(pointers['transformPoint'])
    g.take(f'mov r8, [rbx+0x{temp:x}]','mov r10, rax','test r8, r8'); g.branch('je','fatal')
    g.take('lea rcx, [rbp-0x10]','mov r9, r8'); g.call(pointers['right'])
    g.take('movd xmm2, edi','lea rdx, [rsp+0x40]','cvtdq2ps xmm2, xmm2',
        'mov ecx, [rax+0x8]','mov [rsp+0x48], ecx','lea rcx, [rbp+0x0]',
        'movsd xmm1, [rax]','movsd [rsp+0x40], xmm1'); g.call(pointers['multiply'])
    g.take(f'movss xmm2, [rbx+0x{center:x}]','lea rdx, [rsp+0x50]',
        'lea rcx, [rbp+0x10]','movsd xmm3, [rax]','mov eax, [rax+0x8]',
        'mov [rsp+0x58], eax','mov eax, [r8+0x18]'); _counter(g,'dec','eax')
    g.take('movsd [rsp+0x50], xmm3','movd xmm0, eax','cvtdq2ps xmm0, xmm0','divss xmm2, xmm0')
    g.call(pointers['multiply'])
    g.take('movsd xmm0, [r10]','lea r8, [rsp+0x60]','lea rdx, [rsp+0x70]',
        'movsd [rsp+0x70], xmm0','lea rcx, [rbp+0x20]','movsd xmm3, [rax]',
        'mov eax, [rax+0x8]','mov [rsp+0x68], eax','mov eax, [r10+0x8]',
        'mov [rsp+0x78], eax','movsd [rsp+0x60], xmm3'); g.call(pointers['addition'])
    g.take('lea rcx, [rbp+0x30]','mov r8, rax'); g.call(pointers['forward'])
    g.take('movd xmm2, edi','lea rdx, [rbp-0x80]','cvtdq2ps xmm2, xmm2',
        'mov ecx, [rax+0x8]','mov [rbp-0x78], ecx','lea rcx, [rbp+0x40]',
        'movsd xmm3, [rax]','movsd [rbp-0x80], xmm3'); g.call(pointers['multiply'])
    g.take(f'movss xmm2, [rbx+0x{center+8:x}]','lea rdx, [rbp-0x70]',
        'lea rcx, [rbp+0x50]','movsd xmm3, [rax]','mov eax, [rax+0x8]',
        'mov [rbp-0x68], eax','mov eax, [r9+0x18]'); _counter(g,'dec','eax')
    g.take('movsd [rbp-0x70], xmm3','movd xmm0, eax','cvtdq2ps xmm0, xmm0','divss xmm2, xmm0')
    g.call(pointers['multiply'])
    g.take('movsd xmm0, [r8]','lea rdx, [rbp-0x50]','lea rcx, [rbp+0x60]',
        'movsd [rbp-0x50], xmm0','movsd xmm3, [rax]','mov eax, [rax+0x8]',
        'mov [rbp-0x58], eax','mov eax, [r8+0x8]','lea r8, [rbp-0x60]',
        'movsd [rbp-0x60], xmm3','mov [rbp-0x48], eax'); g.call(pointers['addition'])
    g.take('xor edx, edx','mov rcx, rbx','mov rsi, r9','movsd xmm6, [rax]',
        'mov r14d, [rax+0x8]'); g.call(pointers['getTransform'])
    g.take('test rax, rax'); g.branch('je','fatal')
    g.take('xor r9d, r9d','movsd [rbp-0x40], xmm6','lea r8, [rbp-0x40]',
        'mov [rbp-0x38], r14d','mov rdx, rax','lea rcx, [rbp+0x70]')
    inverse = g.call(pointers['inverseTransformPoint'])
    g.take('test rsi, rsi'); g.branch('je','fatal')
    g.take('movsd xmm0, [rax]','lea r8, [rbp-0x30]','mov eax, [rax+0x8]','mov edx, edi')
    setter_context = g.pattern(r'mov r9, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('mov rcx, rsi','movsd [rbp-0x30], xmm0','mov [rbp-0x28], eax')
    setter = g.call(pointers['setItemWrapper']); _counter(g,'inc','edi'); g.branch('jmp','loop')
    g.mark('patch'); g.take('xor edx, edx','mov ecx, edi'); g.call(pointers['getPatch'])
    g.take('test rax, rax'); g.branch('jne','invoke-patch')
    g.mark('fatal'); g.call(pointers['fatal']); g.take('int3')
    g.mark('invoke-patch'); g.take('xor r8d, r8d','mov rdx, rbx','mov rcx, rax')
    g.call(pointers['invokeVoid'])
    g.mark('epilogue'); g.take('lea r11, [rsp+0x190]','mov rbx, [r11+0x10]',
        'mov rsi, [r11+0x18]','mov rdi, [r11+0x20]','mov r14, [r11+0x28]',
        'movaps xmm6, [r11-0x10]','mov rsp, r11','pop rbp','ret'); g.finish()
    return {'completeProgramChecked':True,'instructionsChecked':len(rows),
        'ordinaryEntryMinimumSourceCount':2,'temporaryCountClearedBeforeZeroPredicate':True,
        'clearingRemovesArrayReferencesProved':False,'populationCall':populate,'populationSemanticsProved':False,
        'initialIndex':1,'loopPredicate':'signed int32 i < current temporary-list count',
        'directOffsetOperands':['x','z'],'directYOffsetOperand':False,
        'floatOrder':['q=CVTDQ2PS(int32 i)', 'd=CVTDQ2PS(int32 currentCount-1)',
            'right1=Vector3.op_Multiply(right,q)', 'right2=Vector3.op_Multiply(right1,DIVSS(offset.x,d))',
            'sum1=Vector3.op_Addition(TransformPointOutput,right2)',
            'forward1=Vector3.op_Multiply(forward,q)', 'forward2=Vector3.op_Multiply(forward1,DIVSS(offset.z,d))',
            'sum2=Vector3.op_Addition(sum1,forward2)', 'result=InverseTransformPointOutput(sum2)',
            'temporaryList.set_Item(i,result)'],
        'multiplyNativeOperandOrder':'scalar low lane times corresponding vector component',
        'stackRelation':'RBP = post-prologue RSP + 0x100',
        'aggregateBytes':12,'operandAndOutputBuffersDistinct':True,
        'heldListSnapshot':'temporary list reloaded after TransformPoint; held in R9 then RSI',
        'listReferencesAcrossOpaqueCallsEquated':False,
        'firstPointNotOverwrittenByThisLoop':True,'originalFirstPointPreservationProved':False,
        'getItemCall':item,'transformCall':transform,'inverseTransformCall':inverse,'setItemCall':setter,
        'contexts':{'getItem':item_context,'setItem':setter_context},'patchIdInstruction':patch_id,
        'selection':'ordinary IFix false, nonnull compatible objects, checked list/array bounds and ABI-conforming normal helper returns; temporary list count and storage stable across arithmetic leaves',
        'geometricCoordinateSemanticsProved':False,'rendererSubmissionProved':False,'runtimeExecutionObserved':False}


def _transform_wrapper(rows, failure_rows, pointers, *, label):
    g = ProgramGrammar(rows,label=LABEL+'.'+label)
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rdi','sub rsp, 0x20',
        'xor eax, eax','mov rdi, r8','mov [rcx], rax','mov rsi, rdx',
        'mov [rcx+0x8], eax','mov rbx, rcx')
    load = g.pattern(r'mov rax, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('test rax, rax'); g.branch('je','resolve')
    g.mark('call'); g.take('mov r8, rbx','mov rdx, rdi','mov rcx, rsi')
    indirect = g.take('call rax')
    if bytes.fromhex(indirect['bytes']) != b'\xff\xd0':
        g.fail('internal-indirect-call','CALL RAX',indirect)
    g.take('mov rsi, [rsp+0x38]','mov rax, rbx','mov rbx, [rsp+0x30]',
        'add rsp, 0x20','pop rdi','ret')
    g.mark('resolve'); string = g.pattern(r'lea rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.call(pointers['resolveInternal']); g.take('test rax, rax'); failure = g.branch('je')
    store = g.pattern(r'mov \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], rax')
    g.branch('jmp','call'); g.finish()
    def cell(row):
        raw=bytes.fromhex(row['bytes'])
        if len(raw)!=7: g.fail('pointer-cell-width','complete RIP-relative qword operation',row)
        return int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)
    if bytes.fromhex(load['bytes'])[:3]!=b'\x48\x8b\x05' or bytes.fromhex(store['bytes'])[:3]!=b'\x48\x89\x05' or cell(load)!=cell(store):
        g.fail('same-internal-call-cache','one loaded/stored qword cell',{'load':load,'store':store})
    f=ProgramGrammar(failure_rows,label=LABEL+'.'+label+'.missingInternal')
    other_string=f.pattern(r'lea rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    if bytes.fromhex(string['bytes'])[:3]!=b'\x48\x8d\x0d' or cell(string)!=cell(other_string):
        f.fail('same-internal-name','same address on resolution and failure',other_string)
    f.call(pointers['missingInternal']); f.take('mov rcx, rax','xor edx, edx')
    f.call(pointers['throw']); f.take('int3'); f.finish()
    if failure['target']!=int(failure_rows[0]['va'],16):
        g.fail('missing-internal-edge',failure_rows[0]['va'],failure)
    return {'completeProgramAndFailureWindowChecked':True,'aggregateBytes':12,
        'abi':{'output':'rcx','receiver':'rdx','input':'r8','returnedOutput':'rax'},
        'internalCallAbi':{'receiver':'rcx','input':'rdx','output':'r8'},
        'outputInitializedToZero':True,'returnedBufferIdentityProved':True,
        'internalCacheCell':cell(load),'internalNameAddress':cell(string),
        'internalImplementationProved':False,'coordinateMeaningProved':False,'runtimeExecutionObserved':False}


def _list_get_item(rows,pointers):
    g=ProgramGrammar(rows,label=LABEL+'.getItem')
    g.take('sub rsp, 0x28','mov r9, rcx','cmp r8d, [rdx+0x18]'); _branch(g,'jae','list-index-failure')
    g.take('mov rax, [rdx+0x10]','test rax, rax'); g.branch('je','null-array')
    g.take('cmp r8d, [rax+0x18]'); _branch(g,'jae','array-index-failure')
    g.take('movsxd rcx, r8d','lea rdx, [rcx+rcx*2]','movsd xmm0, [rax+0x20+rdx*4]',
        'mov eax, [rax+0x28+rdx*4]','movsd [r9], xmm0','mov [r9+0x8], eax',
        'mov rax, r9','add rsp, 0x28','ret')
    g.mark('null-array');g.call(pointers['fatal']);g.take('int3')
    g.mark('array-index-failure');g.call(pointers['arrayIndexFailure']);g.take('int3')
    g.mark('list-index-failure');g.take('xor ecx, ecx');g.call(pointers['listIndexFailure']);g.take('int3');g.finish()
    return {'completeProgramChecked':True,'arrayElementStride':12,'arrayDataOffset':32,
        'listCountOffset':24,'listItemsOffset':16,'outputBytes':12,'returnedOutput':'incoming RCX',
        'selection':'unsigned index below list count and array length; nonnull compatible list/items'}


def _list_set_wrapper(rows,pointer):
    g=ProgramGrammar(rows,label=LABEL+'.setItemWrapper')
    g.take('sub rsp, 0x38','movsd xmm0, [r8]','mov eax, [r8+0x8]',
        'lea r8, [rsp+0x20]','movsd [rsp+0x20], xmm0','mov [rsp+0x28], eax')
    call=g.call(pointer);g.take('add rsp, 0x38','ret');g.finish()
    return {'completeProgramChecked':True,'valueCopyBytes':12,'thisIndexAndMethodInfoPreservedBeforeCall':True,'call':call}


def _list_set_item(rows,pointers):
    g=ProgramGrammar(rows,label=LABEL+'.setItem')
    g.take('sub rsp, 0x28','mov r9, rcx','cmp edx, [rcx+0x18]');_branch(g,'jae','list-index-failure')
    g.take('mov rax, [rcx+0x10]','test rax, rax');g.branch('je','null-array')
    g.take('cmp edx, [rax+0x18]');_branch(g,'jae','array-index-failure')
    g.take('movsd xmm0, [r8]','movsxd rcx, edx','lea rdx, [rcx+rcx*2]',
        'lea rcx, [rax+rdx*4]','mov eax, [r8+0x8]',
        'movsd [rcx+0x20], xmm0','mov [rcx+0x28], eax')
    version=g.take('inc [r9+0x1c]')
    if bytes.fromhex(version['bytes'])!=bytes.fromhex('41FF411C'):g.fail('version-width','dword increment',version)
    g.take('add rsp, 0x28','ret')
    g.mark('null-array');g.call(pointers['fatal']);g.take('int3')
    g.mark('array-index-failure');g.call(pointers['arrayIndexFailure']);g.take('int3')
    g.mark('list-index-failure');g.take('xor ecx, ecx');g.call(pointers['listIndexFailure']);g.take('int3');g.finish()
    return {'completeProgramChecked':True,'arrayElementStride':12,'arrayDataOffset':32,
        'listCountOffset':24,'listItemsOffset':16,'valueWriteBytes':12,'countWritten':False,
        'versionIncrementedAsInt32':True,'methodInfoReadOnOrdinaryStoragePath':False,
        'selection':'unsigned index below list count and array length; nonnull compatible list/items'}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (contract.get('scope')!='conditional-per-iteration-arithmetic-and-writeback'
            or set(contract.get('programs',{}))!={'applyOffset','getItem','setItemWrapper','setItem','transformPoint','inverseTransformPoint'}
            or set(contract.get('leaves',{}))!={'addition','vector-times-scalar','right','forward'}
            or set(contract.get('genericContexts',{}))!={'getItem','setItem'}
            or len(contract.get('fields',[]))!=3 or len(contract.get('declarations',[]))!=7):
        _fail('contract-shape','six programs, four leaves, two contexts, three fields and seven declarations',contract.get('scope'))
    return contract


def _list_declaration(image,selected,method,role):
    """Join a closed Vector3 MethodSpec to the exact open List<T> signature."""
    definition=selected.index.types['System.Collections.Generic.List`1']
    if (method.declaring_type!=definition.index or definition.generic_container_index<0
            or method.generic_container_index>=0 or method.flags&0x10):
        _fail('list-instance-declaration:'+role,'nongeneric instance method of selected generic List<T>',method.index)
    section=image.metadata.sections['genericContainers']
    at=section.offset+definition.generic_container_index*16
    if not section.offset<=at<=section.offset+section.size-16:
        _fail('list-generic-container-bound','complete selected container',at)
    owner,count,is_method,parameter=struct.unpack_from('<iiii',image.metadata.buf,at)
    if (owner,count,is_method)!=(definition.index,1,0) or parameter<0:
        _fail('list-generic-container','one selected class parameter',(owner,count,is_method,parameter))
    parameters=list(image.metadata.parameters_for(method))
    expected=[('index',0x08)] if role=='getItem' else [('index',0x08),('value',0x13)]
    if role not in ('getItem','setItem') or len(parameters)!=len(expected) or method.parameter_count!=len(expected):
        _fail('list-parameter-count:'+role,len(expected),len(parameters))
    def record(type_index,kind,meaning):
        raw=image.pe.bytes_at_va(selected.type_pointer(type_index),16)
        if len(raw)!=16 or raw[10]!=kind or raw[11]&0x7f or kind==0x13 and int.from_bytes(raw[:8],'little')!=parameter:
            _fail('list-signature:'+role+':'+meaning,'selected undecorated Int32/class T/void',raw.hex())
        return raw.hex().upper()
    return_raw=record(method.return_type,0x13 if role=='getItem' else 0x01,'return')
    argument_raw=[record(p.type_index,kind,meaning) for p,(meaning,kind) in zip(parameters,expected)]
    return {'methodIndex':method.index,'selectedClassParameterIndex':parameter,
        'instanceMethod':True,'returnNativeTypeHex':return_raw,'parameterNativeTypeHex':argument_raw,
        'closedValueSelection':'same class parameter selected as undecorated Vector3 by the checked MethodSpec'}


def _validate_image(image:Any,contract:dict)->dict:
    index=BodyIndex(image);selected=NativeReferenceContext(image,index=index);base=image.pe.image_base
    field_roles={
        'points':(TRAIL+'::points','System.Collections.Generic.List`1<UnityEngine.Vector3>'),
        'temp':(TRAIL+'::m_tempPoints','System.Collections.Generic.List`1<UnityEngine.Vector3>'),
        'center':(TRAIL+'::centerOffset','UnityEngine.Vector3')}
    offsets={}
    for field in contract['fields']:
        role=field['role']
        if role not in field_roles or role in offsets: _fail('field-role',list(field_roles),role)
        name,typ=field_roles[role]
        if field['field']!=name or typ is not None and field['type']!=typ:
            _fail('field-identity',field_roles[role],field)
        actual=selected.field(name)
        if actual!=(field['owner'],field['type'],field['offset']):_fail('field:'+name,field,actual)
        offsets[role]=field['offset']
    # Physical slots are established by complete closed-context consumers,
    # not by the placeholder layout of the open List<T> metadata definition.
    representation={'itemsPointerSlot':16,'countSlot':24,'versionSlot':28,
        'arrayLengthSlot':24,'arrayDataOffset':32,'elementStride':12,
        'openGenericFieldOffsetsUsed':False,'namedGenericFieldLayoutProved':False}
    if contract['listRepresentation']!=representation:
        _fail('compiled-list-representation',representation,contract['listRepresentation'])
    for declaration in contract['declarations']:
        method=image.metadata.methods[declaration['method'][0]]
        actual={'method':[method.index,image.type_name(method.declaring_type),image.metadata.string(method.name_index),
                image.method_pointer_va(method)-base],
            'flags':method.flags,'returnType':selected.type_name(method.return_type),
            'returnNativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(method.return_type),16).hex().upper(),
            'parameters':[{'name':image.metadata.string(p.name_index),'type':selected.type_name(p.type_index),
                'nativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(p.type_index),16).hex().upper()}
                for p in image.metadata.parameters_for(method)]}
        if actual!=declaration:_fail('declaration:'+declaration['method'][2],declaration,actual)
        if method.generic_container_index>=0:_fail('nongeneric-declaration',-1,method.generic_container_index)
    programs={}
    for role,program in contract['programs'].items():
        expected_windows=2 if role in ('transformPoint','inverseTransformPoint') else 1
        if len(program['windows'])!=expected_windows:
            _fail('checked-window-count:'+role,expected_windows,len(program['windows']))
        pointer=base+program['entryRva']
        owned=sorted(set([(pointer,index.extents.get(pointer,0))]+
            [(at,at+size) for at,size in index.chained_fragments.get(pointer,())]))
        actual=[(base+w['startRva'],base+w['endRva']) for w in program['windows']]
        if actual!=owned:_fail('complete-owned-program:'+role,actual,owned)
        image.check_windows(program['windows'],label=LABEL)
        programs[role]=[decode_lane_transfer_instructions(image.mapper,image.window_bytes(w),base+w['startRva']) for w in program['windows']]
    for role,name in [('applyOffset','_ApplyCenterOffset'),('transformPoint','TransformPoint'),('inverseTransformPoint','InverseTransformPoint')]:
        owner=TRAIL if role=='applyOffset' else 'UnityEngine.Transform'
        declaration=next((d for d in contract['declarations'] if d['method'][1:3]==[owner,name]),None)
        if declaration is None or declaration['method'][3]!=contract['programs'][role]['entryRva']:
            _fail('program-declaration:'+role,owner+'.'+name,declaration)
        if declaration['flags']&0x10:_fail('instance-declaration:'+role,'instance method',declaration['flags'])
        expected_args=[] if role=='applyOffset' else ['UnityEngine.Vector3']
        expected_return='void' if role=='applyOffset' else 'UnityEngine.Vector3'
        if [p['type'] for p in declaration['parameters']]!=expected_args or declaration['returnType']!=expected_return:
            _fail('program-value-signature:'+role,(expected_return,expected_args),declaration)
        if role!='applyOffset':
            vector=index.types['UnityEngine.Vector3']
            for raw_hex in [declaration['returnNativeTypeHex'],declaration['parameters'][0]['nativeTypeHex']]:
                raw=bytes.fromhex(raw_hex)
                if len(raw)!=16 or raw[10]!=0x11 or raw[11]&0x7f or int.from_bytes(raw[:8],'little')!=vector.index:
                    _fail('transform-value-signature','undecorated selected Vector3 value',raw_hex)
    pointers={role:base+rva for role,rva in contract['callTargets'].items()}
    for role,names in contract['namedCallTargets'].items():
        if index.names_of(pointers[role])!=names:_fail('named-call:'+role,names,index.names_of(pointers[role]))
    leaves={}
    for operation,spec in contract['leaves'].items():
        proof=validate_vector3_value_leaf(image,base+spec['entryRva'],operation=operation)
        for key in ('entryRva','methodIndex','programBytes','programSha256'):
            if proof[key]!=spec[key]:_fail('leaf:'+operation+':'+key,spec[key],proof[key])
        role={'vector-times-scalar':'multiply','addition':'addition','right':'right','forward':'forward'}[operation]
        if pointers[role]!=base+proof['entryRva']:_fail('called-leaf:'+operation,proof['entryRva'],contract['callTargets'][role])
        leaves[operation]=proof
    apply=_apply_offset(programs['applyOffset'][0],pointers,offsets)
    transforms={role:_transform_wrapper(programs[role][0],programs[role][1],pointers,label=role)
        for role in ('transformPoint','inverseTransformPoint')}
    for role in transforms:
        if pointers[role]!=base+contract['programs'][role]['entryRva']:_fail('called-transform:'+role,contract['programs'][role]['entryRva'],pointers[role])
    getter=_list_get_item(programs['getItem'][0],pointers)
    wrapper=_list_set_wrapper(programs['setItemWrapper'][0],pointers['setItem'])
    setter=_list_set_item(programs['setItem'][0],pointers)
    for role in ('getItem','setItemWrapper','setItem'):
        if pointers[role]!=base+contract['programs'][role]['entryRva']:_fail('called-list-program:'+role,contract['programs'][role]['entryRva'],pointers[role])
    contexts=[]
    for role,spec in contract['genericContexts'].items():
        row=apply['contexts'][role];raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
        if len(raw)!=7 or raw[:3]!=b'\x4c\x8b\x0d':_fail('method-info-load:'+role,'RIP qword into R9',row)
        cell=at+7+int.from_bytes(raw[3:],'little',signed=True);word=image.pe.bytes_at_va(cell,8)
        si=unresolved_usage_index(word,image.registration['methodSpecsCount'],tag=6,source=str(image.gameassembly),offset=cell)
        record_at=int(image.registration['methodSpecs'],16)+si*12;record=image.pe.bytes_at_va(record_at,12)
        definition,ci,mi=method_spec_record(record,len(image.metadata.methods),image.registration['genericInstsCount'],source=str(image.gameassembly),offset=record_at)
        method=image.metadata.methods[definition]
        declaration=_list_declaration(image,selected,method,role)
        actual=[definition,image.type_name(method.declaring_type),image.metadata.string(method.name_index)]
        class_args=image.instantiations.resolve(ci).arguments;method_args=image.instantiations.resolve(mi).arguments
        class_names=[runtime_type_name(image.pe,image.metadata,a.type_pointer_va) for a in class_args]
        expected_name='get_Item' if role=='getItem' else 'set_Item'
        if (actual[1:]!=['System.Collections.Generic.List`1',expected_name]
                or class_names!=['UnityEngine.Vector3'] or method_args
                or si!=spec['methodSpecIndex'] or actual!=spec['definition']
                or record.hex().upper()!=spec['recordRawHex']
                or [a.raw_type_record_hex for a in class_args]!=spec['classArgumentRawHex']):
            _fail('typed-list-context:'+role,spec,{'definition':actual,'classArguments':class_names,'methodArguments':method_args,'methodSpecIndex':si})
        value=class_args[0].raw_type_record_hex;value_raw=bytes.fromhex(value)
        if value_raw[10]!=0x11 or value_raw[11]&0x7f or int.from_bytes(value_raw[:8],'little')!=index.types['UnityEngine.Vector3'].index:
            _fail('closed-list-vector-value','selected undecorated Vector3',value)
        contexts.append({'role':role,'methodSpecIndex':si,'definition':actual,'classArguments':class_names,
            'cellRva':cell-base,'usageRawHex':word.hex().upper(),'declaration':declaration,
            'runtimeMethodInfoInitializationProved':False})
    code=image.mapper.code_registration_summary(image.pe,image.code_registration)
    table_at=int(image.registration['genericMethodTable'],16)
    table_raw=image.pe.bytes_at_va(table_at,image.registration['genericMethodTableCount']*16)
    matches=generic_method_candidates(table_raw,image.registration['genericMethodTableCount'],image.registration['methodSpecsCount'],
        {c['methodSpecIndex'] for c in contexts},code['genericMethodPointersCount'],code['invokerPointersCount'],source=str(image.gameassembly),offset=table_at)
    for match in matches:
        match['methodPointerRva']=image.pe.u64_at_va(int(code['genericMethodPointers'],16)+match['indices'][0]*8)-base
    current=[{k:r[k] for k in ('tableIndex','methodSpecIndex','rawHex','indices','methodPointerRva')} for r in matches]
    if current!=contract['genericMethodTableMatches']:_fail('all-selected-generic-table-matches',contract['genericMethodTableMatches'],current)
    for role in ('getItem','setItem'):
        spec=contract['genericContexts'][role]
        targets={r['methodPointerRva'] for r in current if r['methodSpecIndex']==spec['methodSpecIndex']}
        if targets!={contract['programs'][role]['entryRva']}:
            _fail('compiled-list-context-route:'+role,contract['programs'][role]['entryRva'],targets)
    return {'fields':contract['fields'],'listRepresentation':representation,'applyOffset':apply,'vectorLeaves':leaves,'transformWrappers':transforms,
        'getItem':getter,'setItemWrapper':wrapper,'setItem':setter,'staticListContexts':contexts,
        'selectedGenericMethodTableMatches':current,'perIterationPointArithmeticProved':True,
        'twelveBytePointWritebackProved':True,'initialPointPopulationProved':False,
        'geometricCoordinateSemanticsProved':False,'parentExecutionConfigurationJoinProved':False,
        'rendererSubmissionProved':False,'runtimeExecutionObserved':False}


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
    if after.status!='validated' or not unity_matches():return {'status':'mismatched','detail':'Selected native inputs changed during point validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
