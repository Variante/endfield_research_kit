"""Selected EffectLineCenter storage ownership and conditional native flow.

The ordinary preparation grammar proves target/result forwarding and the
configuration write. Callee branch selection and actual execution remain open.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, single_reference_generic_field
from scripts.game_data.il2cpp.vector_arithmetic import validate_vector3_subtraction_leaf
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.conditional_moves import decode_with_conditional_moves
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.context import unresolved_usage_index

SCHEMA = 'endfield.buff-effect-line-center-consumer-native-contract.v3'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_consumer_native.json'
LABEL = 'buffEffectLineCenterConsumer'


def _fail(check: str, expected: Any, actual: Any) -> None:
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} '
                     f'expected={str(expected)[:512]} actual={str(actual)[:512]}')


def _contract() -> dict:
    contract, _digest = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA,
        status='exact-current-build', label=LABEL)
    if (contract.get('scope') != 'conditional-preparation-and-configuration-cache-flow'
            or not isinstance(contract.get('fields'), list) or len(contract['fields']) != 9
            or not isinstance(contract.get('declarations'), list) or len(contract['declarations']) != 5
            or not isinstance(contract.get('programs'), dict)
            or set(contract['programs']) != {'preparation','referenceFilter','positionGetter','configurationCache'}
            or not isinstance(contract.get('targetHandle'), dict)
            or contract.get('callerArgumentOwnershipProved') is not True
            or contract.get('centerOffsetWriteProved') is not True):
        _fail('contract-shape', 'nine layout fields and four conditional flow programs', contract.get('scope'))
    return contract


def _validate_image(image: Any, contract: dict) -> dict:
    selected = NativeReferenceContext(image)
    slot = contract['dataSlot']
    layout = single_reference_generic_field(selected, owner=slot['closedOwner'], field=slot['field'],
        witness=slot['witnessType'], concrete_instance_suffix=True)
    if (layout['fieldOffset'] != slot['offset'] or layout['fieldType'] != slot['type']
            or layout['concreteWitness']['instanceBytes'] != slot['witnessInstanceBytes']):
        _fail('closed-data-slot', slot, {key: layout[key] for key in ('fieldOffset', 'fieldType')})
    receiver = contract['receiver']; td = selected.index.types.get(receiver['type'])
    if (td is None or selected.parent(receiver['type']) != slot['witnessType']
            or td.generic_container_index >= 0 or not td.bitfield & 0x800 or td.flags & 0x18 == 0x10
            or any(not selected.field_attributes(f.type_index) & 0x10 for f in image.metadata.fields_for(td))):
        _fail('fieldless-derived-receiver', receiver, None if td is None else td.index)
    if not 0 <= td.index < image.registration['typeDefinitionsSizesCount']:
        _fail('receiver-size-index', 'selected type size table entry', td.index)
    pointer = image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16) + td.index * 8)
    sizes = image.pe.bytes_at_va(pointer,16) if pointer else b''
    if (len(sizes) != 16 or int.from_bytes(sizes[:4],'little') != receiver['instanceBytes']
            or receiver['instanceBytes'] != layout['concreteWitness']['instanceBytes']):
        _fail('receiver-instance-size', receiver['instanceBytes'], sizes.hex().upper())
    fields = []
    for row in contract['fields']:
        actual = selected.field(row['field'])
        expected = (row['owner'], row['type'], row['offset'])
        if actual != expected:
            _fail('named-field:' + row['field'], expected, actual)
        fields.append(dict(row))
    ancestry = []; current = 'Beyond.Gameplay.Core.AbilitySystem'
    while current and current not in ('object', 'System.Object'):
        if current in ancestry or len(ancestry) >= 32:
            _fail('ability-system-ancestry', 'bounded selected reference ancestry', ancestry)
        ancestry.append(current); current = selected.parent(current)
    if 'Beyond.Gameplay.Core.BaseComponent' not in ancestry:
        _fail('ability-system-entity-owner', 'BaseComponent ancestor', ancestry)
    for row in contract['methods']:
        image.validate_method_row(row, label=LABEL)
    for declaration in contract['declarations']:
        method = image.metadata.methods[declaration['methodIndex']]
        actual = {'methodIndex':method.index, 'type':image.type_name(method.declaring_type),
            'method':image.metadata.string(method.name_index), 'flags':method.flags,
            'returnType':selected.type_name(method.return_type),
            'returnNativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(method.return_type),16).hex().upper(),
            'parameters':[{'name':image.metadata.string(p.name_index), 'type':selected.type_name(p.type_index),
                'nativeTypeHex':image.pe.bytes_at_va(selected.type_pointer(p.type_index),16).hex().upper()}
                for p in image.metadata.parameters_for(method)]}
        if actual != declaration:
            _fail('typed-method-declaration:' + declaration['method'], declaration, actual)
    preparation = contract['methods'][0]
    method = image.metadata.methods[preparation[0]]
    if (preparation[1] != receiver['type'] or preparation[2] != 'PreExecuteInternal'
            or method.flags & 0x10 or method.generic_container_index >= 0
            or selected.type_name(method.return_type) != 'void'
            or [selected.type_name(p.type_index) for p in image.metadata.parameters_for(method)]
            != ['Beyond.Gameplay.Core.TargetHandleView']):
        _fail('preparation-declaration', 'selected void instance preparation with input handle', preparation)
    image.check_windows(contract['codeWindows'],label=LABEL)
    leaf = contract['vectorLeaf']
    vector = validate_vector3_subtraction_leaf(image, image.pe.image_base + leaf['entryRva'])
    if (vector['methodIndex'] != leaf['methodIndex'] or vector['programBytes'] != leaf['programBytes']
            or vector['programSha256'] != leaf['programSha256']):
        _fail('vector-leaf-entry', leaf, vector)
    flow = _validate_flow(image, contract) if 'programs' in contract else {}
    return {'dataLayout': layout, 'receiver': dict(receiver), 'fields': fields,
        'abilitySystemAncestry': ancestry, 'vectorLeaf': vector,
        'callerArgumentOwnershipProved': bool(flow), 'centerOffsetWriteProved': bool(flow),
        'targetSelectionObserved': False, 'runtimeExecutionObserved': False, **flow}


def _owned_program(image: Any, index: Any, spec: dict, role: str) -> list[dict]:
    window = spec['window']; start = image.pe.image_base + window['startRva']
    end = image.pe.image_base + window['endRva']
    if index.extents.get(start) != end:
        _fail('owned-program:' + role, 'complete selected unwind extent', window)
    if 'method' in spec:
        image.validate_method_row(spec['method'], label=LABEL)
        if image.method_pointer_va(image.metadata.methods[spec['method'][0]]) != start:
            _fail('program-entry:' + role, spec['method'], window)
    image.check_windows([window], label=LABEL)
    raw = image.pe.bytes_at_va(start,end-start)
    return decode_with_conditional_moves(image.mapper, raw, start)


def _reference_filter(rows: list[dict], compatibility: int) -> dict:
    """Both complete returns preserve the input reference or return null.

    The called class predicate is deliberately opaque. Its Boolean result
    controls CMOVE; this proof assigns no class-compatibility semantics to it.
    """
    g = ProgramGrammar(rows,label=LABEL + '.reference-filter')
    g.take('push rbx','sub rsp, 0x20','mov rbx, rcx','test rcx, rcx')
    g.branch('je','null'); g.take('mov rcx, [rcx]'); g.call(compatibility)
    g.take('xor ecx, ecx','test al, al','cmove rbx, rcx','mov rax, rbx',
           'add rsp, 0x20','pop rbx','ret')
    g.mark('null'); g.take('xor eax, eax','add rsp, 0x20','pop rbx','ret'); g.finish()
    return {'returnedOriginalReferenceOrNull':True,'predicateMeaningProved':False,
            'nullInputReturnsNull':True,'predicateFalseClearsReference':True}


def _position_getter(rows: list[dict], backing: int, value_offset: int) -> dict:
    """Check entry through the primary fallthrough aggregate return.

    Lazy initialization, IFix and fatal branches are excluded by the stated
    selection. They are not assumed to choose this path at a caller invocation.
    """
    g = ProgramGrammar(rows,label=LABEL + '.position-getter')
    g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x30')
    g.pattern(r'mov rax, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take('mov rbx, rdx','mov rdi, rcx','cmp [rax+0xe0], 0x0'); g.branch('je')
    g.take('mov r8, [rax+0xb8]','mov rcx, [r8]','test rcx, rcx'); g.branch('je')
    g.pattern(r'cmp \[rcx\+0x18\], 0x[0-9a-f]+'); g.branch('jg')
    g.take(f'mov rbx, [rbx+0x{backing:x}]','test rbx, rbx'); g.branch('je')
    g.take('cmp [rax+0xe0], 0x0'); g.branch('je')
    g.take('mov rcx, [rax+0xb8]','mov rdx, [rcx]','test rdx, rdx'); g.branch('je')
    g.pattern(r'cmp \[rdx\+0x18\], 0x[0-9a-f]+'); g.branch('jg')
    g.take(f'movsd xmm0, [rbx+0x{value_offset:x}]',f'mov ecx, [rbx+0x{value_offset+8:x}]',
        'movsd [rdi], xmm0','mov [rdi+0x8], ecx','mov rbx, [rsp+0x40]',
        'mov rax, rdi','add rsp, 0x30','pop rdi','ret'); g.finish(prefix=True)
    return {'selection':'entry-to-primary-fallthrough-return',
        'abi':{'output':'rcx','entity':'rdx','returnedOutput':'rax'},
        'outputBytes':12,'completeReturnChecked':True,'otherGetterPathsProved':False}


def _configuration_cache(rows: list[dict], pointers: dict, data: int, cfg: int, cache: int) -> dict:
    g = ProgramGrammar(rows,label=LABEL + '.configuration-cache')
    g.take('push rbx','sub rsp, 0x20','mov rbx, rcx','xor edx, edx')
    g.pattern(r'mov ecx, 0x[0-9a-f]+'); g.call(pointers['isPatched'])
    g.take('xor edx, edx','test al, al'); g.branch('jne')
    g.take('mov rcx, rbx'); g.call(pointers['baseOnCreate'])
    g.take(f'mov rax, [rbx+0x{data:x}]','test rax, rax'); g.branch('je','fatal')
    g.take(f'mov rax, [rax+0x{cfg:x}]',f'lea rcx, [rbx+0x{cache:x}]',
           f'mov [rbx+0x{cache:x}], rax','add rsp, 0x20','pop rbx')
    edge = g.branch('jmp')
    if edge['target'] != pointers['writeBarrier']:
        g.fail('reference-write-barrier',hex(pointers['writeBarrier']),edge)
    g.take('add rsp, 0x20','pop rbx','ret')
    g.mark('fatal'); g.call(pointers['fatal']); g.take('int3'); g.finish()
    return {'selection':'ordinary-unpatched-OnCreate', 'cachedSameLoadedReference':True,
        'clonedByThisAssignment':False,'source':'current Data.effectActionCfg after base OnCreate',
        'destination':'this.m_effectActionCfg','laterReferenceStabilityProved':False}


def _preparation(rows: list[dict], pointers: dict, offsets: dict) -> dict:
    """Complete caller grammar, including local branches and whole epilogue.

    Reloads of m_data are kept distinct. The proof neither assumes callees
    cannot mutate objects nor joins later Data loads with an earlier cached
    configuration reference. Each field offset is independently metadata-owned.
    """
    g = ProgramGrammar(rows,label=LABEL + '.preparation')
    d,s,c,f,e,a,b = (offsets[k] for k in ('data','source','center','force','entity','cfg','centerOffset'))
    env = offsets['environment']
    g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rsi','push rbp','push rdi','push r14',
           'mov rbp, rsp','sub rsp, 0x60')
    flag = g.pattern(r'cmp \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x0')
    g.take('mov rbx, rdx','mov rdi, rcx'); g.branch('jne','initialized')
    init = g.pattern(r'lea rcx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.call(pointers['initialize'])
    flag_write = g.pattern(r'mov \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x1')
    def rip_target(row):
        raw=bytes.fromhex(row['bytes']); displacement=int.from_bytes(raw[-4:],'little',signed=True)
        # CMP/MOV memory immediates place the displacement before the final byte.
        if raw[0] in (0x80,0xc6): displacement=int.from_bytes(raw[-5:-1],'little',signed=True)
        return int(row['va'],16)+len(raw)+displacement
    if rip_target(flag) != rip_target(flag_write): g.fail('initialization-flag',flag,flag_write)
    g.mark('initialized'); _zero_reference_slot(g,'and [rbp+0x38], 0x0')
    patch_id = g.pattern(r'mov esi, 0x[0-9a-f]+')
    _zero_reference_slot(g,'and [rbp-0x40], 0x0'); g.take('mov ecx, esi','xor edx, edx')
    g.call(pointers['isPatched']); g.take('test al, al'); g.branch('jne','patch')
    cast_type = g.pattern(r'mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    if rip_target(init) != rip_target(cast_type): g.fail('cast-type-initialization',init,cast_type)
    g.take(f'mov rcx, [rdi+0x{d:x}]'); cast = g.call(pointers['referenceFilter'])
    g.take(f'mov rdx, [rdi+0x{d:x}]','mov r14, rax','test rdx, rdx'); g.branch('je','fatal')
    g.take(f'mov rdx, [rdx+0x{s:x}]','xor r9d, r9d','mov r8, rbx','mov rcx, rdi')
    source_call = g.call(pointers['getFirstTarget'])
    g.take(f'mov rcx, [rdi+0x{d:x}]','mov rsi, rax','test rcx, rcx'); g.branch('je','fatal')
    _byte_zero_compare(g,f'cmp [rcx+0x{f:x}], 0x0'); g.branch('jne','source-selected')
    source_remap = _remap(g,pointers,env,'rsi','+0x38')
    g.mark('source-selected'); g.take('test r14, r14'); g.branch('je','fatal')
    g.take(f'mov rdx, [r14+0x{c:x}]','xor r9d, r9d','mov r8, rbx','mov rcx, rdi')
    center_call = g.call(pointers['getFirstTarget'])
    g.take('mov rbx, rax',f'mov rax, [rdi+0x{d:x}]','test rax, rax'); g.branch('je','fatal')
    _byte_zero_compare(g,f'cmp [rax+0x{f:x}], 0x0'); g.branch('jne','center-selected')
    center_remap = _remap(g,pointers,env,'rbx','-0x40')
    g.mark('center-selected'); g.take('test rsi, rsi'); g.branch('je','epilogue')
    g.take('test rbx, rbx'); g.branch('je','epilogue')
    g.take(f'mov rdi, [rdi+0x{d:x}]','test rdi, rdi'); g.branch('je','fatal')
    g.take(f'mov rdx, [rbx+0x{e:x}]',f'mov rdi, [rdi+0x{a:x}]','test rdx, rdx')
    g.branch('je','fatal'); g.take('xor r8d, r8d','lea rcx, [rbp-0x20]')
    center_position = g.call(pointers['position'])
    g.take(f'mov rdx, [rsi+0x{e:x}]','movsd xmm0, [rax]','mov ebx, [rax+0x8]',
           'movsd [rbp-0x30], xmm0','test rdx, rdx'); g.branch('je','fatal')
    g.take('xor r8d, r8d','lea rcx, [rbp-0x10]')
    source_position = g.call(pointers['position'])
    g.take('lea r8, [rbp-0x20]','mov [rbp-0x28], ebx','lea rdx, [rbp-0x30]',
           'lea rcx, [rbp-0x10]','movsd xmm0, [rax]','mov eax, [rax+0x8]',
           'movsd [rbp-0x20], xmm0','movsd xmm0, [rbp-0x30]',
           'movsd [rbp-0x30], xmm0','mov [rbp-0x18], eax')
    subtraction = g.call(pointers['subtract'])
    g.take('mov ecx, [rax+0x8]','test rdi, rdi'); g.branch('je','fatal')
    g.take('movsd xmm0, [rax]',f'movsd [rdi+0x{b:x}], xmm0',f'mov [rdi+0x{b+8:x}], ecx')
    g.branch('jmp','epilogue')
    g.mark('patch'); g.take('xor edx, edx','mov ecx, esi'); g.call(pointers['getPatch'])
    g.take('test rax, rax'); g.branch('jne','invoke-patch')
    g.mark('fatal'); g.call(pointers['fatal']); g.take('int3')
    g.mark('invoke-patch'); g.take('xor r9d, r9d','mov r8, rbx','mov rdx, rdi','mov rcx, rax')
    g.call(pointers['invokePatch'])
    g.mark('epilogue'); g.take('lea r11, [rsp+0x60]','mov rbx, [r11+0x20]',
        'mov rsi, [r11+0x28]','mov rsp, r11','pop r14','pop rdi','pop rbp','ret'); g.finish()
    return {'instructionsChecked':len(rows),'completeCallerProgramChecked':True,
        'castTypeLoad':cast_type,'castCall':cast,'sourceTargetCall':source_call,'centerTargetCall':center_call,
        'sourceRemap':source_remap,'centerRemap':center_remap,
        'centerPositionCall':center_position,'sourcePositionCall':source_position,'subtractionCall':subtraction,
        'aggregateBuffers':{'centerPosition':-32,'sourcePosition':-16,'left':-48,'right':-32,'output':-16,
            'valueBytes':12,'allThreeComponentsCopiedBeforeReuse':True,'subtractionBuffersDisjoint':True},
        'centerOffsetWrite':{'source':'center entity position minus source entity position',
            'destination':'effectActionCfg from the final current m_data reload','bytes':12,
            'field':'Beyond.Gameplay.EffectActionCfg::centerOffset','storedPositionOffsetWritten':False},
        'selection':'caller IFix false; both Entity.get_position calls select their validated primary fallthrough return',
        'dataReloadsEquatedAcrossCalls':False,'patchIdInstruction':patch_id}


def _remap(g: ProgramGrammar, pointers: dict, env: int, target: str, stack: str) -> dict:
    g.take(f'mov rcx, [rdi+0x{env:x}]','test rcx, rcx'); g.branch('je','fatal')
    context = g.call(pointers['context'])
    g.take('test rax, rax'); g.branch('je','fatal')
    g.take('xor r9d, r9d',f'lea r8, [rbp{stack}]',f'mov rdx, {target}','mov rcx, rax')
    call = g.call(pointers['remap']); g.take('test al, al',f'cmovne {target}, [rbp{stack}]')
    return {'call':call,'contextCall':context,'onlyEnteredWhenCurrentForceMainBodyIsZero':True,
        'outSlot':'rbp'+stack,'slotInitializedToNull':True,'returnTrueSelectsOutSlot':True,
        'returnFalsePreservesOriginalTarget':True,'outValueOrTargetSelectionObserved':False}


def _zero_reference_slot(g: ProgramGrammar, text: str) -> None:
    row=g.take(text);raw=bytes.fromhex(row['bytes'])
    if raw[:2]!=b'\x48\x83' or raw[-1:]!=b'\0':
        g.fail('out-slot-full-width','64-bit AND zero',row)


def _byte_zero_compare(g: ProgramGrammar, text: str) -> None:
    row=g.take(text);raw=bytes.fromhex(row['bytes'])
    if raw[:1]!=b'\x80' or raw[-1:]!=b'\0':
        g.fail('force-field-byte-width','8-bit CMP zero',row)


def _input_handle(image: Any, selected: Any, handle: dict) -> dict:
    handle_type=handle['type'];td=selected.index.types.get(handle_type)
    if (handle_type!='Beyond.Gameplay.Core.TargetHandleView' or td is None
            or not selected.is_value_type(handle_type) or td.generic_container_index>=0
            or td.flags & 0x18 == 0x10):
        _fail('input-handle-value-layout','selected non-explicit nongeneric handle value',handle)
    members=[f for f in image.metadata.fields_for(td) if not selected.field_attributes(f.type_index)&0x10]
    field=selected.field(handle['field'])
    if (len(members)!=1 or field!=(handle_type,'Beyond.Gameplay.Core.TargetHandle',16)
            or selected.is_value_type(field[1]) or handle['instanceBytes']!=24):
        _fail('input-handle-single-reference','sole reference at boxed object-header boundary',handle)
    type_raw=image.pe.bytes_at_va(selected.type_pointer(members[0].type_index),16)
    size_pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    sizes=image.pe.bytes_at_va(size_pointer,16)
    if (len(type_raw)!=16 or type_raw[10]!=0x12 or type_raw[11]!=0
            or len(sizes)!=16 or int.from_bytes(sizes[:4],'little')!=24):
        _fail('input-handle-selected-size','one native reference in eight unboxed bytes',sizes.hex())
    return {'type':handle_type,'unboxedBytes':8,'singleReferenceField':handle['field'],
            'incomingRegister':'rdx','getFirstTargetArgumentRegister':'r8'}


def _callee_abi(declarations: list[dict]) -> None:
    by_name={r['method']:r for r in declarations}
    first=by_name['GetFirstTarget'];remap=by_name['ResolveEnemyPartTransferTarget'];position=by_name['get_position']
    if (not first['flags'] & 0x10 or first['returnType']!='Beyond.Gameplay.Core.AbilitySystem'
            or [p['type'] for p in first['parameters']] != ['Beyond.Gameplay.Core.AbilityAction',
                'Beyond.Gameplay.Core.TargetSettings','Beyond.Gameplay.Core.TargetHandleView']
            or remap['flags'] & 0x10 or remap['returnType']!='bool'
            or [p['type'] for p in remap['parameters']] != ['Beyond.Gameplay.Core.AbilitySystem']*2
            or position['flags'] & 0x10 or position['returnType']!='UnityEngine.Vector3' or position['parameters']):
        _fail('callee-abi-declarations','typed reference/bool byref and Vector3 getter',by_name)
    def representation(row: dict, kind: int, byref: bool, key: str) -> None:
        raw=bytes.fromhex(row[key])
        if len(raw)!=16 or raw[10]!=kind or bool(raw[11]&0x20)!=byref:
            _fail('callee-abi-representation',{'kind':kind,'byref':byref},row)
    representation(first,0x12,False,'returnNativeTypeHex')
    for n,p in enumerate(first['parameters']):representation(p,0x11 if n==2 else 0x12,False,'nativeTypeHex')
    representation(remap,0x02,False,'returnNativeTypeHex')
    for n,p in enumerate(remap['parameters']):representation(p,0x12,n==1,'nativeTypeHex')
    representation(position,0x11,False,'returnNativeTypeHex')


def _validate_flow(image: Any, contract: dict) -> dict:
    index = BodyIndex(image); specs = contract['programs']; base = image.pe.image_base
    programs = {role:_owned_program(image,index,spec,role) for role,spec in specs.items()}
    pointers = {role:base+rva for role,rva in contract['callTargets'].items()}
    for role,method in contract['namedCallTargets'].items():
        if index.names_of(pointers[role]) != [method]:
            _fail('named-call:' + role, [method], index.names_of(pointers[role]))
    for role in ('referenceFilter','positionGetter','configurationCache'):
        expected = base+specs[role]['window']['startRva']
        key = {'referenceFilter':'referenceFilter','positionGetter':'position','configurationCache':'onCreate'}[role]
        if pointers[key] != expected: _fail('callee-owned-entry:' + role,expected,pointers[key])
    offsets = {'data':contract['dataSlot']['offset']}
    for role,name in contract['fieldRoles'].items():
        matches = [r for r in contract['fields'] if r['field']==name]
        if len(matches)!=1: _fail('field-role:' + role,name,matches)
        offsets[role]=matches[0]['offset']
    reference = _reference_filter(programs['referenceFilter'],pointers['compatibility'])
    getter = _position_getter(programs['positionGetter'],contract['getterBackingOffset'],contract['getterValueOffset'])
    preparation = _preparation(programs['preparation'],pointers,offsets)
    row = preparation['castTypeLoad']; raw=bytes.fromhex(row['bytes'])
    cell=int(row['va'],16)+len(raw)+int.from_bytes(raw[3:7],'little',signed=True)
    usage=image.pe.bytes_at_va(cell,8)
    type_index=unresolved_usage_index(usage,image.registration['typesCount'],tag=1,
        source=str(image.gameassembly),offset=cell)
    selected = NativeReferenceContext(image,index=index)
    expected = contract['fields'][0]['owner']
    if selected.type_name(type_index) != expected:
        _fail('cast-type-usage',expected,selected.type_name(type_index))
    handle=_input_handle(image,selected,contract['targetHandle'])
    # The declaration is not an observed target, but its byref and aggregate
    # representation must agree with the ABI grammar used above.
    _callee_abi(contract['declarations'])
    cache=_configuration_cache(programs['configurationCache'],pointers,offsets['data'],offsets['cfg'],offsets['cache'])
    return {'preparationFlow':preparation,'referenceFilter':reference,'positionGetter':getter,
        'configurationCache':cache,'castTypeUsage':{'cellRva':cell-base,'registeredTypeIndex':type_index,
            'type':expected,'usageRawHex':usage.hex().upper()},
        'inputHandleValue':handle,
        'conditionalTargetSubstitutionProved':True,'ordinaryOnCreateReferenceCacheProved':True,
        'downstreamExecutionConsumptionProved':False,'runtimeExecutionObserved':False}


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict:
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches() -> bool:
        if not unity.is_file(): return False
        with unity.open('rb') as stream:
            return hashlib.file_digest(stream,'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched', 'detail': 'Selected UnityPlayer input missing or different', 'nativeInputs': pins}
    for spec in contract['dependencies'].values():
        name = spec['contract']
        dependency, _digest = read_reviewed_contract(CONTRACTS_DIR / name,
            schema=spec['schema'], status='exact-current-build', label=LABEL)
        if dependency.get('nativeInputs') != pins:
            _fail('dependency-build:' + name, pins, dependency.get('nativeInputs'))
    result = _validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': 'mismatched', 'detail': 'Selected inputs changed during consumer layout validation', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, **result, 'evidenceBoundary': contract['evidenceBoundary']}
