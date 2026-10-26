"""Authenticate IFix's selected negative instance-field paths offline.

Ldfld/Stfld decode a negative Operand as ~Operand and select AnonymousStorey.
Ldfld uses the managed object at top-minus-one.Value1, replaces that Value slot
in place, and leaves the top unchanged. Stfld converts top-minus-two through
ToObject using a temporary ValueType-tag carrier's GetType result, casts the
result, and passes top-minus-one to AnonymousStorey.Stfld. It removes two slots
on normal return. Its negative route bypasses the positive route's consumed
managed-slot clearing block: no explicit consumed-reference clear is proved.

Both storey methods copy all 12 Value bytes. For tags >= Object, Ldfld rebases
Value1 to the destination evaluation slot and copies managedFields[fieldIndex]
there; Stfld rebases the stored Value1 to fieldIndex and copies the source
managed reference into managedFields[fieldIndex]. Lower tags keep copied bits.
Get/Set address unmanagedFields[0]+fieldIndex*12 and forward the supplied Type
and VM to ToObject/PushObject. Their pointer calculation performs no additional
per-field bounds check after obtaining element zero.

The local finite dispatcher admits one reviewed SUB ECX,ESI with ESI equal to
the authenticated 12-byte slot width. It does not broaden the shared resolver.
The caller supplies the selected native gate and full Execute authentication;
the standalone wrapper enforces explicit paths. All effects are conditional on
normal return and valid storage. Receiver tags, conversion results, aliasing,
runtime array contents/bounds, later reference cleanup, invocation and the raw
anonymousStoreyInfos framing/file-table join remain unresolved.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_delegate_rules import _method
from scripts.game_data.ifix_vm_negative_field_rules import _ref, _rva, _slice, _hash, _relative, _EXECUTE_TYPES


class InstanceFieldRuleError(ValueError):
    """An instance-field declaration lacks its selected native witness."""


_HELPER_REFS = {
    'int32Add': 'negativeFieldRules.helpers.int32Add', 'nullCheck': 'negativeFieldRules.helpers.nullCheck',
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'typeTest': 'functionPointerRules.helpers.typeTest',
}
_TAIL_REFS = {
    'slotWidth': 'basicOpcodeRules.sharedWindows.slotWidth',
    'zeroRegister': 'basicOpcodeRules.sharedWindows.zeroRegister',
    'loopState': 'basicOpcodeRules.sharedWindows.loopState',
    'pcAdvance': 'basicOpcodeRules.sharedWindows.pcAdvance',
    'slotPcTail': 'functionPointerRules.slotPcTail',
}
_METHOD_REFS = {
    'toObject': ('constrainedTypeOperand.stackEffect.toObjectMethod', 'IFix.Core.EvaluationStackOperation', 'ToObject',
                 ['IFix.Core.Value*','IFix.Core.Value*','object[]','System.Type','IFix.Core.VirtualMachine','bool']),
    'pushObject': ('reflectionDispatch.methods.evaluationPush', 'IFix.Core.EvaluationStackOperation', 'PushObject',
                   ['IFix.Core.Value*','IFix.Core.Value*','object[]','object','System.Type']),
    'objectGetType': ('functionPointerRules.helpers.objectGetType', 'System.Object', 'GetType', []),
}
_METHOD_TYPES = {
    'Ldfld': ['int','IFix.Core.Value*','IFix.Core.Value*','object[]'],
    'Stfld': ['int','IFix.Core.Value*','IFix.Core.Value*','object[]'],
    'Get': ['int','System.Type','IFix.Core.VirtualMachine','bool'],
    'Set': ['int','object','System.Type','IFix.Core.VirtualMachine'],
}
_CLAIMS = {
    'Ldfld': ('managed-receiver-at-top-minus-one', 'replace-top-minus-one-with-storey-field', 0),
    'Stfld': ('ToObject-converted-receiver-at-top-minus-two', 'store-top-minus-one-into-storey-field-and-remove-two-slots', -2),
}
# Complete checked method grammars. Branch displacements are local to each
# finite program; every external call and named object-field load is resolved.
_BLOCKS = {
    'Ldfld': (
        '48895c240848896c24104889742418574883ec20488bf14863fa', ('field','488b49','unmanagedFields'),
        '498be9498bd84885c90f84a8000000488bd7', ('call','valueArrayElement'),
        'f20f10008b5008f20f114500895508', ('field','488b4e','unmanagedFields'),
        '4885c90f8484000000488bd7', ('call','valueArrayElement'),
        '8338087c62488bcd48b8abaaaaaaaaaaaa2a482bcb48f7e9488bda48d1fb488bc348c1e83f4803d8895d04',
        ('field','488b4e','managedFields'), '4885c974483b79187206', ('call','boundsFailure'),
        'cc488b74f920488b7c24504885ff742e488bd6488bcf', ('call','assignmentCheck'),
        '4863d34c8bc6488bcf', ('call','managedStore'),
        '488b5c2430488b6c2438488b7424404883c4205fc3', ('call','nullFailure'), 'cc'),
    'Stfld': (
        '488bc4488958104889681848897020574883ec20488bf94863f2', ('field','488b49','unmanagedFields'),
        '498be94885c90f8492000000f2410f1001488bd6f20f114008418b5908', ('call','valueArrayElement'),
        'f20f10442430f20f1100895808837d00087c54', ('field','488b4f','unmanagedFields'),
        '4885c97460488bd6', ('call','valueArrayElement'), '488b4c2450897004', ('field','488b5f','managedFields'),
        '486345044885c974433b41187206', ('call','boundsFailure'),
        'cc488b7cc1204885db742e488bd7488bcb', ('call','assignmentCheck'),
        '488bd64c8bc7488bcb', ('call','managedStore'),
        '488b5c2438488b6c2440488b7424484883c4205fc3', ('call','nullFailure'), 'cc'),
    'Get': (
        '48895c240848896c24104889742418574883ec40488bd94863ea', ('field','488b49','unmanagedFields'),
        '498bf9498bf04885c97506', ('call','nullFailure'), 'cc33d2', ('call','valueArrayElement'),
        '488364243000488d146d000000008a4c24704803d5', ('field','4c8b43','managedFields'),
        '4c8bce884c2428488bc848897c2420488d1490', ('call','toObject'),
        '488b5c2450488b6c2458488b7424604883c4405fc3'),
    'Set': (
        '48895c240848896c24104889742418574883ec30488bd94863ea', ('field','488b49','unmanagedFields'),
        '498bf9498bf04885c97506', ('call','nullFailure'), 'cc33d2', ('call','valueArrayElement'),
        '488364242800488d146d00000000', ('field','4c8b43','managedFields'),
        '4803d54c8bce48897c2420488bc8488d1490', ('call','pushObject'),
        '488b5c2440488b6c2448488b7424504883c4305fc3'),
}


def _fail(label: str, detail: str) -> None:
    raise InstanceFieldRuleError(f'instance-field.{label}: {detail}')


def _expect(raw: bytes, expected: bytes, label: str) -> None:
    if raw != expected:
        offset = next((i for i,pair in enumerate(zip(raw,expected)) if pair[0]!=pair[1]), min(len(raw),len(expected)))
        _fail(label,f'program differs offset={offset:#x} expectedBytes={len(expected)} actualBytes={len(raw)}')


def _declarations(spec: dict[str,Any]) -> dict[str,dict[str,Any]]:
    expected = dict(schema='endfield.ifix-vm-instance-field-rules.v1', evidenceBoundary='conditional', executionBoundary='unobserved',
        scope='negative-instance-fields-only', slotBytes=12,instructionBytes=8,
        dispatchBoundary='selected-ESI-equals-authenticated-slot-width', fileTableJoinBoundary='not-asserted',
        consumedManagedClear='none-explicit-in-selected-negative-route',
        conversionBoundary='receiver-ToObject-and-GetType-result-unobserved',
        getSetIndexBoundary='element-zero-base-then-unchecked-field-pointer-index')
    if any(spec.get(key)!=value for key,value in expected.items()):
        _fail('claims','unsupported schema, scope or boundary')
    rows=spec.get('rules',[])
    result={row.get('opcode'):row for row in rows}
    if len(rows)!=len(result) or set(result)!=set(_CLAIMS):
        _fail('rules','missing, duplicate or unsupported opcode rule')
    for name,row in result.items():
        if ((row.get('receiver'),row.get('effect'),row.get('stackDeltaSlots'))!=_CLAIMS[name]
                or row.get('selectedWhen')!='signed-Operand-negative' or row.get('operandMeaning')!='bitwise-complement-storey-field-index'
                or row.get('nonnegativeTargetRef')!='tableOperandClaims.'+name):
            _fail(name,'unsupported operand, receiver or stack claim')
    return result


def _dispatch(body: bytes,base: int,start: int,opcode: int,sub_esi: int,slot_width: int) -> int:
    """Finite selected walk with one position-bound SUB ECX,ESI extension."""
    if type(opcode) is not int or not 0<=opcode<=0x7fffffff or slot_width!=12:
        _fail('dispatch','unsupported opcode or ESI selection')
    pc,value,flags,seen=start,opcode,None,set()
    for _ in range(64):
        if pc in seen: _fail('dispatch',f'repeated rva={pc:#x}')
        seen.add(pc)
        prefix=_slice(body,base,pc,2,'instance-dispatch')
        if prefix in (b'\x83\xf9',b'\x83\xe9',b'\x81\xf9',b'\x81\xe9',b'\x2b\xce'):
            if prefix==b'\x2b\xce':
                if pc!=sub_esi: _fail('dispatch','SUB ECX,ESI at an unsupported site')
                immediate,size=slot_width,2
            else:
                width=1 if prefix[0]==0x83 else 4
                immediate=int.from_bytes(_slice(body,base,pc+2,width,'instance-dispatch-immediate'),'little',signed=True)
                size=width+2
            flags=(value==immediate,value>immediate)
            if prefix[1] in (0xe9,0xce): value=((value-immediate+0x80000000)&0xffffffff)-0x80000000
            pc+=size
        elif prefix in (b'\x0f\x84',b'\x0f\x85',b'\x0f\x8f',b'\x0f\x8e') or prefix[0] in (0x74,0x75,0x7f,0x7e):
            if flags is None: _fail('dispatch','branch before comparison')
            near=prefix[0]==0x0f
            condition=({0x84:flags[0],0x85:not flags[0],0x8f:flags[1],0x8e:not flags[1]}[prefix[1]] if near else
                       {0x74:flags[0],0x75:not flags[0],0x7f:flags[1],0x7e:not flags[1]}[prefix[0]])
            size=6 if near else 2
            disp=int.from_bytes(_slice(body,base,pc+(2 if near else 1),4 if near else 1,'instance-dispatch-branch'),'little',signed=True)
            pc=pc+size+disp if condition else pc+size
        elif prefix in (b'\x49\x8b',b'\x48\x8b',b'\x8b\xd6',b'\x4c\x8b'):
            return pc
        else: _fail('dispatch',f'unsupported instruction rva={pc:#x} bytes={prefix.hex()}')
    _fail('dispatch','step bound exceeded')


def _fields(image: Any,spec: dict[str,Any],contract: dict[str,Any]) -> dict[str,int]:
    row=spec['fieldLayout']
    if row.get('type')!='IFix.Core.AnonymousStorey' or set(row.get('fields',{}))!={'unmanagedFields','managedFields'}:
        _fail('fields','unsupported owner or field set')
    md,pe=image.metadata,image.pe
    owners=[owner for owner in md.types if md.type_full_name(owner)==row['type']]
    if len(owners)!=1: _fail('fields',f'owner count differs actual={len(owners)}')
    owner=owners[0]
    offsets=runtime_type_field_offsets(md,pe,image.registration,owner.index)
    fields={md.string(f.name_index):f for f in md.fields_for(owner)}
    result={}
    for name,expected in {'unmanagedFields':'IFix.Core.Value[]','managedFields':'object[]'}.items():
        declaration=row['fields'][name]
        field=fields.get(name)
        if field is None or declaration.get('type')!=expected or offsets.get(name)!=declaration.get('offset'):
            _fail('fields.'+name,f"layout differs expected={declaration.get('offset')} actual={offsets.get(name)}")
        pointer=pe.u64_at_va(_rva(image.registration['types'])+field.type_index*8)
        _nonbyref(image,field.type_index,'fields.'+name)
        if runtime_type_name(pe,md,pointer)!=expected: _fail('fields.'+name,'metadata field type differs')
        if type(declaration['offset']) is not int or not 0<=declaration['offset']<=127: _fail('fields.'+name,'unsupported byte offset')
        result[name]=declaration['offset']
    if spec.get('valueLayoutRef')!='constrainedTypeOperand.stackEffect.valueLayout': _fail('Value','unsupported layout reference')
    value=_ref(contract,spec['valueLayoutRef'])
    owners=[owner for owner in md.types if md.type_full_name(owner)==value['type']]
    if value['type']!='IFix.Core.Value' or len(owners)!=1 or runtime_type_field_offsets(md,pe,image.registration,owners[0].index)!=value['fieldOffsets']:
        _fail('Value','metadata field layout differs')
    if value['fieldOffsets']!={'Type':16,'Value1':20,'Value2':24}: _fail('Value','unsupported boxed Value layout')
    members=enum_members(md,field_defaults(md),'IFix.Core.ValueType')
    if [m['id'] for m in members if m['name']=='Object']!=[8]: _fail('Value','Object tag differs from managed threshold')
    return result


def _nonbyref(image: Any,index: int,label: str) -> None:
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
    record=image.pe.bytes_at_va(pointer,16)
    if len(record)!=16 or record[11]&0x20:
        _fail(label,'by-reference type carrier differs')


def _checked_method(image: Any,row: dict[str,Any],extents: dict[int,int],*,result: str,static: bool,complete: bool=True) -> int:
    """Strengthen shared body authentication with local exact carrier rules."""
    md,pe=image.metadata,image.pe
    selected=[]
    for owner in md.types:
        if md.type_full_name(owner)!=row['type']: continue
        for method in md.methods_for(owner):
            if md.string(method.name_index)!=row['method'] or method.parameter_count!=row['parameterCount']: continue
            parameters=md.parameters_for(method)
            names=[runtime_type_name(pe,md,pe.u64_at_va(_rva(image.registration['types'])+p.type_index*8)) for p in parameters]
            if names==row['parameterTypes']: selected.append(method)
    label='methods.'+row['method']
    if len(selected)!=1: _fail(label,f'exact overload count differs actual={len(selected)}')
    method=selected[0]
    for parameter in md.parameters_for(method): _nonbyref(image,parameter.type_index,label+'.parameter')
    _nonbyref(image,method.return_type,label+'.return')
    return_pointer=pe.u64_at_va(_rva(image.registration['types'])+method.return_type*8)
    actual=runtime_type_name(pe,md,return_pointer)
    declaration=row.get('returnTypeName')
    if actual!=result or (declaration is not None and {'System.Object':'object','System.Void':'void'}.get(declaration,declaration)!=result):
        _fail(label,f'return type differs expected={result} actual={actual}')
    if bool(method.flags&0x10)!=static or method.generic_container_index!=-1:
        _fail(label,'static/instance or generic kind differs')
    if complete: return _method(image,row,extents)
    pointer=image.method_pointer_va(method)
    if method.token!=_rva(row['token']) or pointer-pe.image_base!=_rva(row['rva']): _fail(label,'token or registered pointer differs')
    _hash(pe.bytes_at_va(pointer,row['byteCount']),row,'instance.'+label)
    return pointer-pe.image_base


def _program(base: int,items: tuple,targets: dict[str,int],fields: dict[str,int]) -> bytes:
    p=_Program(base)
    for item in items:
        if isinstance(item,str): p.add(item)
        elif item[0]=='call': p.call(targets[item[1]])
        else: p.add(item[1]);p.byte(fields[item[2]])
    return p.finish()


def _load_program(base: int,nonnegative: int,targets: dict[str,int],cell: int,pc_tail: int) -> bytes:
    p=_Program(base)
    p.add('8bd6498bcc');p.call(targets['subtractSlot']);p.add('4c8be8498bce');p.call(targets['nullCheck'])
    p.add('4d637e044c8b742468453bfe')
    disp=nonnegative-(p.base+len(p.raw)+2)
    if not -128<=disp<=127: _fail('Ldfld','unsupported short selector distance')
    p.add(b'\x7d'+disp.to_bytes(1,'little',signed=True))
    p.add('ba01000000418bcf');p.call(targets['int32Add']);p.add('8bf8f7df498bcd');p.call(targets['nullCheck'])
    p.add('49635d04488bb42408040000488bce');p.call(targets['nullCheck'])
    p.add('488bd3488bce');p.call(targets['arrayFetch']);_relative(p,'488b15',cell)
    p.add('488bc8');p.call(targets['typeTest']);p.add('488bd8488bc8');p.call(targets['nullCheck'])
    p.add('4c8974242848897424204d8bcd4c8b8424100400008bd7488bcb');p.call(targets['Ldfld'])
    p.add('4c8b6c2468');_relative(p,'e9',pc_tail)
    return p.finish()


def _store_program(base: int,nonnegative: int,targets: dict[str,int],enum_cell: int,storey_cell: int,join: int) -> bytes:
    p=_Program(base)
    p.add('8bd6498bcc');p.call(targets['subtractSlot']);p.add('8bd6488bc8');p.call(targets['subtractSlot'])
    p.add('488bf048898424b00000004889842418020000498bce');p.call(targets['nullCheck'])
    p.add('458b6e044489ac2418040000443b6c2468');_relative(p,'0f8d',nonnegative)
    p.add('ba01000000418bcd');p.call(targets['int32Add']);p.add('8bf8f7df488bce');p.call(targets['nullCheck'])
    p.add('4c8bc6');_relative(p,'488b15',enum_cell);p.add('488d8c24d8020000');p.call(targets['typeCarrier'])
    p.add('33d2488d8c24d8020000');p.call(targets['objectGetType'])
    p.add('4c8b6c24684c896c243044886c2428488b8c24f003000048894c24204c8bc84d8bc7488bd6488bcb')
    p.call(targets['toObject']);_relative(p,'488b15',storey_cell)
    p.add('488bc8');p.call(targets['typeTest']);p.add('488bd8488bc8');p.call(targets['nullCheck'])
    p.add('ba0c000000498bcc');p.call(targets['subtractSlot'])
    p.add('4c896c24284c897c24204c8bc84c8b8424100400008bd7488bcb');p.call(targets['Stfld']);_relative(p,'e9',join)
    return p.finish()


def validate_instance_field_rules(image: Any,spec: dict[str,Any],body: bytes,body_rva: int,opcode_ids: dict[str,int],
                                  contract: dict[str,Any],extents: dict[int,int]) -> dict[str,Any]:
    """Authenticate selected instance routes after the explicit full-body gate."""
    declarations=_declarations(spec)
    if spec.get('helperRefs')!=_HELPER_REFS or spec.get('tailRefs')!=_TAIL_REFS or spec.get('methodRefs')!={n:r[0] for n,r in _METHOD_REFS.items()}:
        _fail('references','unsupported parent references')
    fields=_fields(image,spec,contract)
    targets=dict(spec['failureTargets'])
    if set(targets)!={'boundsFailure','nullFailure'}: _fail('helpers','unsupported failure target set')
    targets={name:_rva(value) for name,value in targets.items()}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path)
        raw=image.pe.bytes_at_va(image.pe.image_base+_rva(row['rva']),row['byteCount'])
        _hash(raw,row,'instance.helpers.'+name)
        targets[name]=_rva(row['rva'])
    helpers={row.get('name'):row for row in spec['helpers']}
    if len(helpers)!=len(spec['helpers']) or set(helpers)!={'valueArrayElement','typeCarrier'}: _fail('helpers','unsupported helpers')
    for name,row in helpers.items():
        raw=image.pe.bytes_at_va(image.pe.image_base+_rva(row['rva']),row['byteCount'])
        _hash(raw,row,'instance.helpers.'+name)
        if name=='typeCarrier':
            _expect(raw,bytes.fromhex('48891148c74108ffffffff418b00894110488bc1c3'),name)
        else:
            p=_Program(_rva(row['rva']));p.add('4883ec283b51187206');p.call(targets['boundsFailure'])
            p.add('cc488d4204488d0442488d04814883c428c3');_expect(raw,p.finish(),name)
        targets[name]=_rva(row['rva'])
    for role,(path,owner,name,params) in _METHOD_REFS.items():
        row=dict(_ref(contract,path),parameterTypes=params)
        if (row.get('type'),row.get('method'),row.get('parameterCount'))!=(owner,name,len(params)):
            _fail('methods.'+role,'unsupported method identity')
        # GetType is an inherited entry window that forwards a shared body;
        # its return remains unresolved, and no complete pdata claim is added.
        targets[role]=_checked_method(image,row,extents,
            result={'toObject':'object','pushObject':'void','objectGetType':'System.Type'}[role],
            static=role!='objectGetType',complete=role!='objectGetType')
    if set(spec.get('methods',{}))!=set(_METHOD_TYPES): _fail('methods','missing or unsupported storey methods')
    for name,params in _METHOD_TYPES.items():
        row=spec['methods'][name]
        if (row.get('type'),row.get('method'),row.get('parameterTypes'),row.get('parameterCount'))!=('IFix.Core.AnonymousStorey',name,params,len(params)):
            _fail('methods.'+name,'unsupported method identity')
        targets[name]=_checked_method(image,row,extents,result='object' if name=='Get' else 'void',static=False)
    for name in _METHOD_TYPES:
        row=spec['methods'][name]
        raw=image.pe.bytes_at_va(image.pe.image_base+targets[name],row['bodyBytes'])
        _expect(raw,_program(targets[name],_BLOCKS[name],targets,fields),'storey.'+name)
    if spec.get('anonymousStoreyTypeRef')!='functionPointerRules.anonymousStoreyType': _fail('types','unsupported storey type reference')
    type_rows={'storey':_ref(contract,spec['anonymousStoreyTypeRef']),'carrier':spec['valueTypeCarrier']}
    cells={}
    for name,row in type_rows.items():
        cell=_rva(row['cellRva'])
        raw=image.pe.bytes_at_va(image.pe.image_base+cell,8)
        expected='IFix.Core.AnonymousStorey' if name=='storey' else 'IFix.Core.ValueType'
        if int.from_bytes(raw,'little')!=_rva(row['encodedWord']) or row.get('usageTag')!=1 or row.get('typeName')!=expected:
            _fail('types.'+name,'encoded selected type differs')
        index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='instance-fields',offset=cell)
        _nonbyref(image,index,'types.'+name)
        pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
        if index!=row['registeredTypeIndex'] or runtime_type_name(image.pe,image.metadata,pointer)!=expected:
            _fail('types.'+name,'metadata selected type differs')
        cells[name]=cell
    tails={name:_ref(contract,path) for name,path in _TAIL_REFS.items()}
    for name,row in tails.items(): _hash(_slice(body,body_rva,_rva(row['rva']),row['byteCount'],'instance.tail.'+name),row,'instance.tail.'+name)
    for name in ('slotWidth','slotPcTail'):
        _expect(_slice(body,body_rva,_rva(tails[name]['rva']),5,name),bytes.fromhex('be0c000000'),name)
    _expect(_slice(body,body_rva,_rva(tails['zeroRegister']['rva']),3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    if _rva(tails['slotPcTail']['rva'])+5!=_rva(tails['pcAdvance']['rva']): _fail('tails','slot/PC tail adjacency differs')
    join=spec['storeTopJoin']
    raw=_slice(body,body_rva,_rva(join['rva']),join['byteCount'],'storeTopJoin');_hash(raw,join,'instance.storeTopJoin')
    p=_Program(_rva(join['rva']));p.add('4c8be648897424584889742460');_relative(p,'e9',_rva(tails['slotPcTail']['rva']))
    _expect(raw,p.finish(),'storeTopJoin')
    if spec.get('dispatchStartRef')!='basicOpcodeRules.dispatchStartRva': _fail('dispatch','unsupported start reference')
    checked=[]
    for name,row in declarations.items():
        if row['opcodeId']!=opcode_ids.get(name): _fail(name,'opcode enum ID differs')
        entry=_dispatch(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],_rva(spec['subEsiRva']),spec['slotBytes'])
        if entry!=_rva(row['entryRva']): _fail(name,f"dispatch differs expected={row['entryRva']} actual={entry:#x}")
        positive=_ref(contract,row['nonnegativeTargetRef'])
        if positive.get('selectedWhen')!='nonnegativeOperand' or positive.get('opcodeId')!=row['opcodeId']:
            _fail(name,'parent nonnegative selection differs')
        nonnegative=_rva(row['nonnegativeTargetRva'])
        read=_rva(positive['tableReadRva'])
        if name=='Ldfld':
            _expect(_slice(body,body_rva,nonnegative,4,'Ldfld.nonnegativeVmRestore'),bytes.fromhex('488b5f58'),'Ldfld.nonnegativeVmRestore')
            if read!=nonnegative: _fail(name,'parent table read target differs')
        else:
            _expect(_slice(body,body_rva,nonnegative,4,'Stfld.nonnegativeVmRestore'),bytes.fromhex('488b5f58'),'Stfld.nonnegativeVmRestore')
            if read!=nonnegative: _fail(name,'parent table read target differs')
        window=row['window']
        if _rva(window['rva'])!=entry: _fail(name,'window does not start at dispatch entry')
        raw=_slice(body,body_rva,entry,window['byteCount'],name);_hash(raw,window,'instance.'+name)
        expected=(_load_program(entry,nonnegative,targets,cells['storey'],_rva(tails['slotPcTail']['rva'])) if name=='Ldfld' else
                  _store_program(entry,nonnegative,targets,cells['carrier'],cells['storey'],_rva(join['rva'])))
        _expect(raw,expected,name)
        checked.append(dict(opcode=name,opcodeId=row['opcodeId'],entryRva=hex(entry),stackDeltaSlots=row['stackDeltaSlots']))
    return dict(status='validated_conditional_instance_field_rules',entries=checked,
        storeyMethods=list(_METHOD_TYPES),dispatchEsi=spec['slotBytes'],managedTagThreshold=8,
        consumedManagedClear=spec['consumedManagedClear'],getSetIndexBoundary=spec['getSetIndexBoundary'],
        evidenceBoundary='conditional',executionBoundary='unobserved',fileTableJoinBoundary='not-asserted',
        unresolved=['runtime-receiver-tags-and-cast-results','GetType-and-ToObject-results','runtime-field-and-managed-array-bounds-and-contents',
                    'alias-and-lower-reference-tag-semantics','later-consumed-managed-reference-cleanup','stack-availability',
                    'actual-execution','anonymousStoreyInfos-framing-and-loader-file-order-join'])


def project_instance_field_rules(decoded: dict[str,Any],spec: dict[str,Any]) -> list[dict[str,Any]]:
    """Project authored negative indices and conditional storage expressions."""
    declarations=_declarations(spec)
    result=[]
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name=instruction['name']
            if name not in declarations: continue
            rule=declarations[name]
            operand=instruction['operandUnsigned']
            if type(operand) is not int or not 0<=operand<=0xffffffff or instruction['opcode']!=rule['opcodeId']:
                _fail(name,'malformed unsigned Int32 operand or opcode')
            signed=operand if operand<0x80000000 else operand-0x100000000
            if 'operandSigned' in instruction and (type(instruction['operandSigned']) is not int or instruction['operandSigned']!=signed):
                _fail(name,f"inconsistent signed Int32 operand expected={signed} actual={instruction['operandSigned']}")
            if signed>=0: continue
            result.append(dict(vmMethodIndex=method['index'],instructionIndex=instruction['index'],offset=instruction['offset'],
                opcode=name,operandUnsigned=operand,operandSigned=signed,storeyFieldIndex=-signed-1,
                receiver=rule['receiver'],effect=rule['effect'],stackDeltaSlots=rule['stackDeltaSlots'],normalNextInstructionDelta=1,
                initialValueCopy='all-12-source-Value-bytes',managedReferenceRule='rebase-Value1-and-copy-managed-reference-when-tag-at-least-Object',
                lowerTagRule='preserve-copied-Value-bits-without-managed-transfer',consumedManagedClear=spec['consumedManagedClear'],
                fieldStorage='AnonymousStorey.unmanagedFields[index]-and-managedFields[index]',
                evidenceBoundary='conditional',executionBoundary='unobserved',fileTableJoinBoundary='not-asserted',
                conversionBoundary=spec['conversionBoundary'],aliasBoundary='runtime-source-destination-overlap-unobserved'))
    return result


def validate_selected_instance_field_rules(contract: dict[str,Any],*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    """Gate only explicit selected inputs, including the complete interpreter."""
    if gameassembly is None or metadata is None:
        return dict(status='missing',evidenceBoundary='unresolved',detail='explicit GameAssembly and metadata paths are required')
    inputs=contract['nativeInputs']
    if not inputs.get('gameAssemblySha256') or not inputs.get('globalMetadataSha256'): _fail('nativeInputs','selected native hashes are required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated': return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.instanceFields')
    extents=image.mapper.pdata_function_extents(image.pe)
    row=dict(contract['consumer'],parameterTypes=_EXECUTE_TYPES)
    if (row.get('type'),row.get('method'),row.get('parameterCount'))!=('IFix.Core.VirtualMachine','Execute',8): _fail('consumer','unsupported interpreter identity')
    base=_checked_method(image,row,extents,result='IFix.Core.Value*',static=False)
    body=image.pe.bytes_at_va(image.pe.image_base+base,row['bodyBytes'])
    ids={row['name']:row['id'] for row in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_instance_field_rules(image,contract['instanceFieldRules'],body,base,ids,contract,extents)
