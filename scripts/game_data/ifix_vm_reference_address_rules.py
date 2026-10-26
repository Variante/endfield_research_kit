"""Authenticate IFix reference-address construction, without reading VM memory.

Ldarga stores a signed-operand-selected argument pointer across Value1/Value2.
Ldsflda retains the authored operand and requests internal initialization only
for a negative operand. Ldelema rewrites the lower of two slots to an array
descriptor, preserving Value1 and copying the upper slot's low word to Value2.
Ldflda either requests ToObject and constructs a FieldReference or constructs
an initial/appended FieldAddr chain for a selected value-type field.

Complete finite caller grammars prove the requests, branch conditions, native
stores and top/PC tails. They do not prove runtime conversion, allocation,
reflection/dictionary results, descriptor validity, or helper alias mutation.
The caller owns prior native/prerequisite authentication; the standalone entry
authenticates explicit selected inputs and the complete interpreter itself.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import literal_record, unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_reference_update_rules import _usage as _dictionary_usage, _dictionary_target


class ReferenceAddressRuleError(ValueError):
    """A reference-address claim lacks its selected native witness."""


_HELPER_REFS = {
    'slotMultiply': 'arithmeticWindows.signedSlotMultiply', 'pointerAdd': 'arithmeticWindows.pointerAdd',
    'pointerDifference': 'arithmeticWindows.stackPointerSubtract',
    'subtractSlot': 'constrainedTypeOperand.stackEffect.priorPointerHelper',
    'int32Add': 'negativeFieldRules.helpers.int32Add', 'nullCheck': 'negativeFieldRules.helpers.nullCheck',
    'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
    'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'cast': 'referenceUpdateRules.helpers.cast',
    'virtualTypeQuery': 'genericDelegateFactoryRules.helpers.returnQueryHelper',
    'dictionaryItem': 'referenceUpdateRules.helpers.dictionaryItem',
    'advancePointer': 'basicOpcodeRules.helpers.advancePointer',
}
_METHOD_REFS = {
    'checkCctor': 'negativeFieldRules.checkCctorMethod',
    'fieldEqual': 'referenceUpdateRules.methods.fieldEqual',
    'runtimeException': 'delegateConstruction.methodCalls.nullFallbackException',
    'toObject': 'constrainedTypeOperand.stackEffect.toObjectMethod',
    'typeFromHandle': 'genericDelegateFactoryRules.methods.getTypeFromHandle',
}
_METHODS = {
    'checkCctor': ('IFix.Core.VirtualMachine', 'checkCctorExecute', ['int','IFix.Core.Value*','object[]','IFix.Core.Value*'], 'void', False),
    'fieldEqual': ('System.Reflection.FieldInfo','op_Equality',['System.Reflection.FieldInfo','System.Reflection.FieldInfo'],'bool',True),
    'runtimeException': ('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False),
    'toObject': ('IFix.Core.EvaluationStackOperation','ToObject',['IFix.Core.Value*','IFix.Core.Value*','object[]','System.Type','IFix.Core.VirtualMachine','bool'],'object',True),
    'isValueType': ('System.Type','get_IsValueType',[],'bool',False),
    'fieldAddrCtor': ('IFix.Core.FieldAddr','.ctor',[],'void',False),
    'arrayCopy': ('System.Array','Copy',['System.Array','System.Array','int'],'void',True),
    'notSupportedCtor': ('System.NotSupportedException','.ctor',['string'],'void',False),
    'typeFromHandle': ('System.Type','GetTypeFromHandle',['System.RuntimeTypeHandle'],'System.Type',True),
}
_VIRTUALS = {'fieldType': ('System.Reflection.FieldInfo','get_FieldType',19),
             'declaringType': ('System.Reflection.MemberInfo','get_DeclaringType',9)}
_TAIL_REFS = {name: 'basicOpcodeRules.sharedWindows.'+name for name in
              ('loopState','zeroRegister','slotWidth','pcAdvance','pushAdvance','pushTopCommit','integerStore')}
_TAG_IDS = {'StackReference':4,'StaticFieldReference':5,'FieldReference':6,'ChainFieldReference':7,'ArrayReference':10}
_FIELDS = {'vm': ('IFix.Core.VirtualMachine', {'fieldInfos':'System.Reflection.FieldInfo[]',
             'newFieldInfos':'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>'}),
    'chain': ('IFix.Core.FieldAddr', {'Object':'object','FieldIdList':'int[]'}),
    'newField': ('IFix.Core.NewFieldInfo', {'FieldType':'System.Type','DeclaringType':'System.Type'})}
_CELLS = {'dictionaryContext':(6,'get_Item'), 'notSupportedType':(1,'System.NotSupportedException'),
    'unsupportedLiteral':(5,'ref of compiler generated object field ref!'), 'fieldAddrType':(1,'IFix.Core.FieldAddr'),
    'intArrayType':(1,'int[]'), 'anonymousHandle':(2,'IFix.Core.AnonymousStorey'), 'systemType':(1,'System.Type')}
_HELPERS = ('allocateObject','allocateArray','int32ArrayStore','referenceBarrier','initializeClass','dictionaryWrapper')
_CLAIMS = {
    'Ldarga': ('signed-Operand-argument-slot-address', 'push-StackReference-pointer',1),
    'Ldsflda': ('authored-signed-Operand-field-selector', 'push-StaticFieldReference',1),
    'Ldelema': ('Operand-unused-upper-slot-Value1-is-index', 'replace-two-slots-with-ArrayReference',-1),
    'Ldflda': ('authored-signed-Operand-field-selector', 'replace-receiver-with-FieldReference-or-ChainFieldReference',0),
}
_CHAINS = {
    'Ldarga': ('Ldarga',), 'addressCommit': ('addressCommit',),
    'Ldsflda': ('Ldsflda','staticCommit'), 'Ldelema': ('Ldelema',),
    'Ldflda': ('Ldflda','positiveField','receiver','newField','tagSelect','chainEligible','chainSelect','newChain',
               'constructChain','appendChain','chainCommit','ordinary','ordinaryType'),
}

_BLOCKS = {'Ldarga': ('498bcc',
            ('call', 'nullCheck'),
            '498bce',
            ('call', 'nullCheck'),
            '49634e048bd6',
            ('call', 'slotMultiply'),
            '488b8c2400040000',
            ('edge', 'e9', 'addressCommit')),
 'addressCommit': ('488bd0',
                   ('call', 'pointerAdd'),
                   '4989442404498bcc',
                   ('call', 'nullCheck'),
                   '41c7042404000000',
                   ('edge', 'e9', 'pushForward')),
 'Ldsflda': ('498bce',
             ('call', 'nullCheck'),
             '45396e04',
             ('edge', '7d', 'staticCommit'),
             '498bce',
             ('call', 'nullCheck'),
             'ba01000000418b4e04',
             ('call', 'int32Add'),
             'f7d84c896c242848895c24204d8bcf4d8bc48bd0488bcf',
             ('call', 'checkCctor')),
 'staticCommit': ('498bcc',
                  ('call', 'nullCheck'),
                  '41c7042405000000498bce',
                  ('call', 'nullCheck'),
                  '418b5e04498bcc',
                  ('call', 'nullCheck'),
                  '41895c2404',
                  ('edge', 'e9', 'pushForward')),
 'Ldelema': ('8bd6498bcc',
             ('call', 'subtractSlot'),
             '8bd6488bc8',
             ('call', 'subtractSlot'),
             '488bd8488bc8',
             ('call', 'nullCheck'),
             'c7030a0000008bd6498bcc',
             ('call', 'subtractSlot'),
             '488bc8',
             ('call', 'nullCheck'),
             '8bd6498bcc',
             ('call', 'subtractSlot'),
             '8b7804488bcb',
             ('call', 'nullCheck'),
             '897b08',
             ('edge', 'e9', 'popForward')),
 'Ldflda': ('498bce',
            ('call', 'nullCheck'),
            '45396e04',
            ('edge', '7d', 'positiveField'),
            '498bdd',
            ('edge', 'eb', 'receiver')),
 'positiveField': (('field', '488b5f', 'vm', 'fieldInfos'),
                   '498bce',
                   ('call', 'nullCheck'),
                   '49637e04488bcb',
                   ('call', 'nullCheck'),
                   '488bd7488bcb',
                   ('call', 'arrayFetch'),
                   '488bd8'),
 'receiver': ('498bfd498bf5ba0c000000498bcc',
              ('call', 'subtractSlot'),
              '4c8be0498bce',
              ('call', 'nullCheck'),
              '45396e04',
              ('edge', '0f8c', 'tagSelect'),
              '4533c033d2488bcb',
              ('call', 'fieldEqual'),
              '413ac5',
              ('edge', '75', 'newField'),
              '488bcb',
              ('call', 'nullCheck'),
              ('slot', 'fieldType'),
              '488bd3',
              ('call', 'virtualTypeQuery'),
              '488bf0488bcb',
              ('call', 'nullCheck'),
              ('slot', 'declaringType'),
              '488bd3',
              ('call', 'virtualTypeQuery'),
              '488bf8',
              ('edge', 'e9', 'tagSelect')),
 'newField': ('488b8424f0030000',
              ('field', '488b58', 'vm', 'newFieldInfos'),
              '498bce',
              ('call', 'nullCheck'),
              '418b7e04488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '8bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              ('field', '488b73', 'newField', 'FieldType'),
              '488b8424f0030000',
              ('field', '488b58', 'vm', 'newFieldInfos'),
              '498bce',
              ('call', 'nullCheck'),
              '418b7e04488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '8bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              ('field', '488b7b', 'newField', 'DeclaringType')),
 'tagSelect': ('498bcc',
               ('call', 'nullCheck'),
               '41833c2406',
               ('edge', '74', 'chainEligible'),
               '498bcc',
               ('call', 'nullCheck'),
               '41833c2407',
               ('edge', '74', 'chainEligible'),
               '498bcc',
               ('call', 'nullCheck'),
               '41833c240a',
               ('edge', '0f85', 'ordinary')),
 'chainEligible': ('498bce',
                   ('call', 'nullCheck'),
                   '45396e04',
                   ('edge', '0f8c', 'ordinary'),
                   '488bce',
                   ('call', 'nullCheck'),
                   '33d2488bce',
                   ('call', 'isValueType'),
                   '413ac5',
                   ('edge', '0f84', 'ordinary')),
 'chainSelect': ('498bcc', ('call', 'nullCheck'), '498bcc41833c2407', ('edge', '0f84', 'appendChain')),
 'newChain': (('call', 'nullCheck'),
              '45396c2408',
              ('edge', '7d', 'constructChain'),
              ('rip', '488b0d', 'notSupportedType'),
              ('call', 'allocateObject'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c0',
              ('rip', '488b15', 'unsupportedLiteral'),
              '488bcb',
              ('call', 'notSupportedCtor'),
              '4533c941b001488bd3488b8c24f0030000',
              ('call', 'runtimeException')),
 'constructChain': ('488b942410040000498bcc',
                    ('call', 'pointerDifference'),
                    '488bc848b8abaaaaaaaaaaaa2a48f7e94c8bf249d1fe498bc648c1e83f4c03f0',
                    ('rip', '488b0d', 'fieldAddrType'),
                    ('call', 'allocateObject'),
                    '488bf8488bc8',
                    ('call', 'nullCheck'),
                    '33d2488bcf',
                    ('call', 'fieldAddrCtor'),
                    '498bcc',
                    ('call', 'nullCheck'),
                    '49635c2404498bcf',
                    ('call', 'nullCheck'),
                    '488bd3498bcf',
                    ('call', 'arrayFetch'),
                    '488bd8488bcf',
                    ('call', 'nullCheck'),
                    ('field', '48895f', 'chain', 'Object'),
                    ('field', '488d4f', 'chain', 'Object'),
                    '488bd3',
                    ('call', 'referenceBarrier'),
                    'ba02000000',
                    ('rip', '488b0d', 'intArrayType'),
                    ('call', 'allocateArray'),
                    '488bd8498bcc',
                    ('call', 'nullCheck'),
                    '418b742408488bcb',
                    ('call', 'nullCheck'),
                    '448bc633d2488bcb',
                    ('call', 'int32ArrayStore'),
                    '488b742450488bce',
                    ('call', 'nullCheck'),
                    '8b7604488bcb',
                    ('call', 'nullCheck'),
                    '448bc6ba01000000488bcb',
                    ('call', 'int32ArrayStore'),
                    '488bcf',
                    ('call', 'nullCheck'),
                    ('field', '48895f', 'chain', 'FieldIdList'),
                    ('field', '488d4f', 'chain', 'FieldIdList'),
                    '488bd3',
                    ('call', 'referenceBarrier'),
                    '498bcf',
                    ('call', 'nullCheck'),
                    '488bd7498bcf',
                    ('call', 'assignmentCheck'),
                    '4c8bc7498bd6498bcf',
                    ('call', 'managedStore'),
                    '498bcc',
                    ('call', 'nullCheck'),
                    '418b042483e806f7d81bdbffcb498bcc',
                    ('call', 'nullCheck'),
                    '41895c2408',
                    ('edge', 'e9', 'chainCommit')),
 'appendChain': ('488b942410040000',
                 ('call', 'pointerDifference'),
                 '488bc848b8abaaaaaaaaaaaa2a48f7e94c8bfa49d1ff498bc748c1e83f4c03f8488b9c2408040000488bcb',
                 ('call', 'nullCheck'),
                 '498bd7488bcb',
                 ('call', 'arrayFetch'),
                 ('rip', '488b15', 'fieldAddrType'),
                 '488bc8',
                 ('call', 'cast'),
                 '4c8bf0488bc8',
                 ('call', 'nullCheck'),
                 ('field', '498b5e', 'chain', 'FieldIdList'),
                 '488bcb',
                 ('call', 'nullCheck'),
                 'ba010000008b4b18',
                 ('call', 'int32Add'),
                 '8bd0',
                 ('rip', '488b0d', 'intArrayType'),
                 ('call', 'allocateArray'),
                 '488bf0488bcb',
                 ('call', 'nullCheck'),
                 '4533c9448b4318488bd6488bcb',
                 ('call', 'arrayCopy'),
                 '488bcb',
                 ('call', 'nullCheck'),
                 '488b7c2450488bcf',
                 ('call', 'nullCheck'),
                 '8b7f04488bce',
                 ('call', 'nullCheck'),
                 '48635318448bc7488bce',
                 ('call', 'int32ArrayStore'),
                 ('rip', '488b0d', 'fieldAddrType'),
                 ('call', 'allocateObject'),
                 '488bd8488bc8',
                 ('call', 'nullCheck'),
                 '33d2488bcb',
                 ('call', 'fieldAddrCtor'),
                 '498bce',
                 ('call', 'nullCheck'),
                 ('field', '498b7e', 'chain', 'Object'),
                 '488bcb',
                 ('call', 'nullCheck'),
                 ('field', '48897b', 'chain', 'Object'),
                 ('field', '488d4b', 'chain', 'Object'),
                 '488bd7',
                 ('call', 'referenceBarrier'),
                 '488bcb',
                 ('call', 'nullCheck'),
                 ('field', '488973', 'chain', 'FieldIdList'),
                 ('field', '488d4b', 'chain', 'FieldIdList'),
                 '488bd6',
                 ('call', 'referenceBarrier'),
                 '488bbc2408040000488bcf',
                 ('call', 'nullCheck'),
                 '488bd3488bcf',
                 ('call', 'assignmentCheck'),
                 '4c8bc3498bd7488bcf',
                 ('call', 'managedStore')),
 'chainCommit': ('498bcc', ('call', 'nullCheck'), '41c7042407000000', ('edge', 'e9', 'restoreTop')),
 'ordinary': ('498bce',
              ('call', 'nullCheck'),
              '45396e04',
              ('edge', '7d', 'ordinaryType'),
              ('rip', '488b1d', 'anonymousHandle'),
              ('rip', '488b0d', 'systemType'),
              ('call', 'initializeClass'),
              '33d2488bcb',
              ('call', 'typeFromHandle'),
              '488bf8'),
 'ordinaryType': ('4c896c243044886c2428488b8424f003000048894424204c8bcf4d8bc7498bd4488b9c2410040000488bcb',
                  ('call', 'toObject'),
                  '488bf8498bcc',
                  ('call', 'nullCheck'),
                  '41c7042406000000498bcc',
                  ('call', 'nullCheck'),
                  '488bd3498bcc',
                  ('call', 'pointerDifference'),
                  '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04189542404498bcc',
                  ('call', 'nullCheck'),
                  '49635c2404498bcf',
                  ('call', 'nullCheck'),
                  '488bd7498bcf',
                  ('call', 'assignmentCheck'),
                  '488bd34c8bc7498bcf',
                  ('call', 'managedStore'),
                  '498bce',
                  ('call', 'nullCheck'),
                  '418b5e04498bcc',
                  ('call', 'nullCheck'),
                  '41895c2408',
                  ('edge', 'e9', 'restoreTop'))}


def _rva(value: Any) -> int:
    return int(value,0) if isinstance(value,str) else int(value)


def _need(ok: bool, label: str) -> None:
    if not ok: raise ReferenceAddressRuleError('reference-address.'+label)


def _named(rows: list[dict], names: Any, label: str) -> dict[str,dict]:
    result={row.get('name'):row for row in rows}
    _need(len(result)==len(rows) and set(result)==set(names),label+': missing/duplicate/unknown declarations')
    return result


def _ref(contract: dict, path: str) -> dict:
    row: Any=contract
    for key in path.split('.'):
        if isinstance(row,list):
            selected=[r for r in row if r.get('name',r.get('role',r.get('opcode')))==key]
            _need(len(selected)==1,'references: missing/ambiguous '+path); row=selected[0]
        else:
            _need(isinstance(row,dict) and key in row,'references: missing '+path); row=row[key]
    _need(isinstance(row,dict),'references: invalid '+path)
    return row


def _slice(raw: bytes, base: int, at: int, count: int, label: str) -> bytes:
    _need(type(count) is int and count>0 and 0<=at-base<=len(raw)-count,label+': outside selected body')
    return raw[at-base:at-base+count]


def _hash(raw: bytes, row: dict, label: str, *, method: bool=False) -> None:
    count,key=('bodyBytes','bodySha256') if method else ('byteCount','sha256')
    actual=hashlib.sha256(raw).hexdigest().upper()
    _need(len(raw)==row[count] and actual==row[key].upper() and ('hex' not in row or raw==bytes.fromhex(row['hex'])),
          label+f': native bytes differ expectedSha256={row[key]} actualSha256={actual}')


def _expect(raw: bytes, expected: bytes, label: str) -> None:
    if raw!=expected:
        off=next((i for i,(a,b) in enumerate(zip(raw,expected)) if a!=b),min(len(raw),len(expected)))
        _need(False,label+f': finite program differs offset={off:#x} expectedBytes={len(expected)} actualBytes={len(raw)}')


def _type(image: Any,index: int) -> str:
    _need(type(index) is int and 0<=index<image.registration['typesCount'],'metadata: registered type index out of range')
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
    raw=image.pe.bytes_at_va(pointer,16)
    _need(len(raw)==16 and not raw[11]&0x20,'metadata: malformed/by-reference type carrier')
    return runtime_type_name(image.pe,image.metadata,pointer)


def _identity(image: Any,row: dict,identity: tuple,label: str,extents: dict[int,int], *, virtual_slot: int|None=None, body_required: bool=True) -> int:
    owner,name,params,returned,static=identity
    _need((row.get('type'),row.get('method'),row.get('parameterCount'))==(owner,name,len(params)),label+': unsupported named method')
    if 'parameterTypes' in row: _need(row['parameterTypes']==params,label+': declared parameters differ')
    md=image.metadata
    matches=[m for t in md.types if md.type_full_name(t)==owner for m in md.methods_for(t)
             if md.string(m.name_index)==name and m.parameter_count==len(params)
             and [_type(image,p.type_index) for p in md.parameters_for(m)]==params]
    _need(len(matches)==1,label+': expected one named overload'); method=matches[0]
    _need(_type(image,method.return_type)==returned and bool(method.flags&0x10)==static
          and method.generic_container_index==-1 and method.token==_rva(row['token']),label+': return/static/generic/token differs')
    if virtual_slot is not None:
        _need(method.flags&0x40 and method.slot==row.get('virtualSlot')==virtual_slot,label+': virtual slot differs')
        return virtual_slot
    pointer=image.method_pointer_va(method);at=pointer-image.pe.image_base
    _need(at==_rva(row['rva']),label+': registered pointer differs')
    if 'bodyBytes' in row:
        _need(extents.get(pointer)==pointer+row['bodyBytes'],label+': exact method extent differs')
        _hash(image.pe.bytes_at_va(pointer,row['bodyBytes']),row,label,method=True)
    elif 'byteCount' in row:
        _need(row.get('bodyBoundary')=='entry-window-callee-outcome-unresolved',label+': partial-body boundary missing')
        _hash(image.pe.bytes_at_va(pointer,row['byteCount']),row,label)
    else:
        _need(not body_required,label+': native body declaration missing')
    return at


def _layouts(image: Any,spec: dict,contract: dict) -> dict[str,dict[str,int]]:
    rows=spec['fieldLayouts'];_need(set(rows)==set(_FIELDS),'layouts: unsupported owner set')
    md=image.metadata;result={}
    for role,(name,fields) in _FIELDS.items():
        row=rows[role];owners=[t for t in md.types if md.type_full_name(t)==name]
        _need(row.get('type')==name and len(owners)==1 and set(row.get('fields',{}))==set(fields),'layouts.'+role+': owner/fields differ')
        owner=owners[0];offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
        definitions={md.string(f.name_index):f for f in md.fields_for(owner)};result[role]={}
        for field,typ in fields.items():
            declaration=row['fields'][field];definition=definitions.get(field)
            _need(definition is not None and declaration.get('type')==typ and _type(image,definition.type_index)==typ
                  and offsets.get(field)==declaration.get('offset') and type(declaration['offset']) is int
                  and 0<=declaration['offset']<128,'layouts.'+role+'.'+field+': named layout differs')
            # These constructor routes select instance storage, never a static field table.
            pointer=image.pe.u64_at_va(_rva(image.registration['types'])+definition.type_index*8)
            _need(not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&0x10,'layouts.'+role+'.'+field+': static field carrier')
            result[role][field]=declaration['offset']
    value=_ref(contract,spec['valueLayoutRef']);owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.Value']
    _need(value.get('type')=='IFix.Core.Value' and len(owners)==1 and owners[0].bitfield&1,'Value: value-type owner differs')
    _need(runtime_type_field_offsets(md,image.pe,image.registration,owners[0].index)==value['fieldOffsets']=={'Type':16,'Value1':20,'Value2':24},'Value: 12-byte payload layout differs')
    definitions={md.string(f.name_index):f for f in md.fields_for(owners[0])}
    _need(all(n in definitions and _type(image,definitions[n].type_index)==t for n,t in
              {'Type':'IFix.Core.ValueType','Value1':'int','Value2':'int'}.items()),'Value: field carriers differ')
    return result


def _cells(image: Any,spec: dict,targets: dict[str,int]) -> dict[str,int]:
    rows=_named(spec['usageCells'],_CELLS,'usageCells');result={}
    for name,(tag,identity) in _CELLS.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(raw==bytes.fromhex(row['rawHex']) and row.get('usageTag')==tag and row.get('identity')==identity,name+': stored usage differs')
        result[name]=at
        if tag in (1,2):
            index=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='reference-address.'+name,offset=at)
            _need(_type(image,index)==identity,name+': selected non-byref type differs')
        elif tag==5:
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData']
            index=unresolved_usage_index(raw,table.size//8,tag=5,source='reference-address.literal',offset=at)
            off=table.offset+index*8;start,size=literal_record(md.buf[off:off+8],pool.size,source='reference-address.literal',offset=off)
            _need(md.buf[pool.offset+start:pool.offset+start+size]==identity.encode(),'unsupportedLiteral: stored message differs')
        else:
            definition=_dictionary_usage(image,dict(row,name='instanceDictionary'))
            _dictionary_target(image,definition,targets['dictionaryItem'])
    return result


def _program(name: str,base: int,targets: dict[str,int],cells: dict[str,int],fields: dict[str,dict[str,int]],slots: dict[str,int]) -> bytes:
    p=_Program(base)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='field':p.add(args[0]);p.byte(fields[args[1]][args[2]])
        elif kind=='slot':p.add(b'\xb9'+slots[args[0]].to_bytes(4,'little'))
        elif kind=='edge':
            prefix=bytes.fromhex(args[0]);width=1 if prefix[0] in (0x74,0x75,0x7d,0xeb) else 4
            displacement=targets[args[1]]-(base+len(p.raw)+len(prefix)+width)
            _need(-(1<<(width*8-1))<=displacement<(1<<(width*8-1)),'program: branch displacement outside finite width')
            p.add(prefix+displacement.to_bytes(width,'little',signed=True))
        else:_need(False,'program: unsupported token')
    return p.finish()


def _claims(spec: dict) -> dict[str,dict]:
    expected={'schema':'endfield.ifix-vm-reference-address-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
      'slotBytes':12,'instructionBytes':8,'pointerBytes':8,'pointerPayloadOffset':4,
      'pointerBoundary':'encoded-native-address-validity-and-target-memory-unobserved',
      'storageBoundary':'valid-stable-slots-arrays-and-normal-helper-return',
      'aliasBoundary':'runtime-helper-mutation-and-overlap-unobserved',
      'chainBoundary':'caller-construction-requests-allocation-and-Array.Copy-outcome-unobserved',
      'fileTableJoinBoundary':'not-asserted','valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout',
      'dispatchStartRef':'basicOpcodeRules.dispatchStartRva','helperRefs':_HELPER_REFS,'methodRefs':_METHOD_REFS,'tailRefs':_TAIL_REFS,
      'tagMembers':_TAG_IDS,'consumedManagedClear':'none-explicit-in-selected-address-construction-routes'}
    _need(all(spec.get(k)==v for k,v in expected.items()),'claims: unsupported schema/reference/effect boundary')
    rows={row.get('opcode'):row for row in spec.get('rules',[])}
    _need(len(rows)==len(spec.get('rules',[])) and set(rows)==set(_CLAIMS),'rules: missing/duplicate/unknown opcode')
    for name,(meaning,effect,delta) in _CLAIMS.items():
        row=rows[name];_need((row.get('operandMeaning'),row.get('effect'),row.get('stackDeltaSlots'))==(meaning,effect,delta),name+': unsupported operand/effect')
    return rows


def validate_reference_address_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],
                                     contract: dict,extents: dict[int,int]) -> dict:
    """Validate a gated native image after the parent's prerequisite groups."""
    rules=_claims(spec);fields=_layouts(image,spec,contract)
    members={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(members.get(n)==v for n,v in _TAG_IDS.items()),'ValueType: descriptor tags differ')
    targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,'helper.'+name);targets[name]=at
    leaf_shapes={'slotMultiply':'4863c2480fafc1c3','pointerAdd':'488d0411c3',
        'pointerDifference':'482bca488bc1c3','subtractSlot':'4863c2482bc8488bc1c3','int32Add':'8d0411c3'}
    for name,hexadecimal in leaf_shapes.items():
        _expect(image.pe.bytes_at_va(image.pe.image_base+targets[name],_ref(contract,_HELPER_REFS[name])['byteCount']),bytes.fromhex(hexadecimal),'helper.'+name)
    methods=_named(spec['methods'],set(_METHODS)-set(_METHOD_REFS),'methods')
    for name,identity in _METHODS.items():
        row=_ref(contract,_METHOD_REFS[name]) if name in _METHOD_REFS else methods[name]
        targets[name]=_identity(image,row,identity,name,extents,body_required=name!='typeFromHandle')
    virtuals=_named(spec['virtualMethods'],_VIRTUALS,'virtualMethods');slots={}
    for name,(owner,method,slot) in _VIRTUALS.items():
        slots[name]=_identity(image,virtuals[name],(owner,method,[],'System.Type',False),name,extents,virtual_slot=slot)
    helpers=_named(spec['helpers'],_HELPERS,'helpers')
    for name,row in helpers.items():
        at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'helper.'+name);targets[name]=at
        _need(row.get('effectBoundary')==('checked-int32-element-store' if name=='int32ArrayStore' else 'opaque-callee-request-only'),name+': helper outcome promoted')
    cells=_cells(image,spec,targets)
    wrapper=helpers['dictionaryWrapper'];p=_Program(targets['dictionaryWrapper']);p.rip('4c8b05',cells['dictionaryContext']);p.rip('e9',targets['dictionaryItem'])
    _expect(image.pe.bytes_at_va(image.pe.image_base+p.base,wrapper['byteCount']),p.finish(),'dictionaryWrapper.same-stored-context')
    store=helpers['int32ArrayStore'];raw=image.pe.bytes_at_va(image.pe.image_base+targets['int32ArrayStore'],store['byteCount'])
    _need(len(raw)==25 and raw[:20]==bytes.fromhex('4883ec283b5118730a44894491204883c428c3e8') and raw[-1]==0xcc,'int32ArrayStore: checked index/value store differs')
    # Authenticate metadata's virtual-slot selection prefix, without claiming a runtime implementation or returned Type.
    query=_ref(contract,_HELPER_REFS['virtualTypeQuery']);query_raw=image.pe.bytes_at_va(image.pe.image_base+targets['virtualTypeQuery'],query['byteCount'])
    _need(query_raw[23:30]==bytes.fromhex('0fb7d9488b0ae8') and query_raw[34:48]==bytes.fromhex('488d431448c1e0044803074c8b00'), 'virtualTypeQuery: uint16-slot/vtable selection differs')
    blocks=_named(spec['blocks'],_BLOCKS,'blocks');targets.update({name:_rva(row['rva']) for name,row in blocks.items()})
    tails={name:_ref(contract,path) for name,path in _TAIL_REFS.items()}
    for name,row in tails.items():_hash(_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name),row,'tail.'+name);targets[name]=_rva(row['rva'])
    pc_tail=_ref(contract,'functionPointerRules.slotPcTail');at=_rva(pc_tail['rva'])
    _hash(_slice(body,body_rva,at,pc_tail['byteCount'],'slotPcTail'),pc_tail,'tail.slotPcTail')
    _expect(_slice(body,body_rva,at,pc_tail['byteCount'],'slotPcTail'),bytes.fromhex('be0c000000'),'tail.slotPcTail')
    _need(at+pc_tail['byteCount']==targets['pcAdvance'],'tail.slotPcTail: PC tail adjacency differs')
    p=_Program(targets['pushAdvance']);p.add('8bd6');p.call(targets['advancePointer']);p.rip('e9',targets['pushTopCommit'])
    _expect(_slice(body,body_rva,p.base,len(p.raw),'pushAdvance'),p.finish(),'tail.pushAdvance')
    p=_Program(targets['pushTopCommit']);p.add('4c8be048894424584889442460');p.rip('e9',targets['pcAdvance'])
    _expect(_slice(body,body_rva,p.base,len(p.raw),'pushTopCommit'),p.finish(),'tail.pushTopCommit')
    joins=_named(spec['joins'],('pushForward','popForward','restoreTop','argumentBinding'),'joins')
    targets.update({name:_rva(row['rva']) for name,row in joins.items()})
    for name,row in joins.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'join.'+name);p=_Program(targets[name])
        if name=='pushForward':p.add('498bcc');p.rip('e9',targets['pushAdvance'])
        elif name=='popForward':p.add('8bd6498bcc');p.call(targets['subtractSlot']);p.rip('e9',targets['pushTopCommit'])
        elif name=='restoreTop':p.add('4c8b642458');p.rip('e9',_rva(_ref(contract,'functionPointerRules.slotPcTail')['rva']))
        else:p.add('488bc44c8948204c8940184889480853565741544155415641574881ecb0030000')
        _expect(raw,p.finish(),'join.'+name)
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'block.'+name)
        _expect(raw,_program(name,targets[name],targets,cells,fields,slots),'block.'+name)
    for name,chain in _CHAINS.items():
        for a,b in zip(chain,chain[1:]):_need(targets[a]+blocks[a]['byteCount']==targets[b],name+': effect blocks not contiguous')
    start=_rva(contract['basicOpcodeRules']['dispatchStartRva']);checked=[]
    for name,row in rules.items():
        _need(type(row['opcodeId']) is int and row['opcodeId']==opcode_ids.get(name),name+': opcode enum differs')
        entry=resolve_dispatch_entry(body,body_rva,start,row['opcodeId'])
        _need(entry==_rva(row['entryRva'])==targets[name],name+': selected entry differs')
        checked.append({'opcode':name,'opcodeId':row['opcodeId'],'entryRva':hex(entry),'stackDeltaSlots':row['stackDeltaSlots']})
    return {'status':'validated_conditional_reference_address_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved',
      'entries':checked,'valuePayloadBytes':12,'pointerBytes':8,'consumedManagedClear':spec['consumedManagedClear'],
      'dictionaryBoundary':'stored-typed-context-registered-MethodDef-family-runtime-sharing-unresolved',
      'unresolved':['runtime-address-and-descriptor-values','argument-slot-count-and-stack-capacity','array-and-field-storage-validity',
        'ToObject-reflection-dictionary-and-IsValueType-results','allocation-cast-Array.Copy-and-initializer-outcomes',
        'runtime-helper-alias-mutation','later-managed-reference-cleanup','actual-execution']}


def project_reference_address_rules(decoded: dict,spec: dict) -> list[dict]:
    """Retain authored selectors; expose conditional descriptor constructions."""
    rules=_claims(spec);result=[]
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name=instruction['name']
            if name not in rules:continue
            row=rules[name];operand=instruction['operandUnsigned']
            _need(type(operand) is int and 0<=operand<=0xffffffff and instruction['opcode']==row['opcodeId'],name+': malformed operand/opcode')
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned' not in instruction or type(instruction['operandSigned']) is int and instruction['operandSigned']==signed,name+': inconsistent signed operand')
            out={'vmMethodIndex':method['index'],'instructionIndex':instruction['index'],'offset':instruction['offset'],
              'opcode':name,'operandUnsigned':operand,'operandSigned':signed,'operandMeaning':row['operandMeaning'],
              'effect':row['effect'],'stackDeltaSlots':row['stackDeltaSlots'],'normalNextInstructionDelta':1,
              'evidenceBoundary':'conditional','executionBoundary':'unobserved','storageBoundary':spec['storageBoundary'],
              'aliasBoundary':spec['aliasBoundary'],'fileTableJoinBoundary':spec['fileTableJoinBoundary'],
              'consumedManagedClear':spec['consumedManagedClear']}
            if name=='Ldarga':out.update(argumentSlotIndex=signed,argumentSlotBoundary='argument-count-and-slot-validity-unobserved',
                pointerExpression='argumentBase+12*signedOperand',pointerWordOrder=['Value1-low32','Value2-high32'],
                resultTag='StackReference',pointerBoundary=spec['pointerBoundary'])
            elif name=='Ldsflda':out.update(resultTag='StaticFieldReference',Value1='authored-signed-Operand',Value2='preserved',
                initializerRequest={'selected':signed<0,'internalStaticFieldIndex':-signed-1 if signed<0 else None,
                    'callee':'checkCctorExecute','outcome':'unobserved'})
            elif name=='Ldelema':out.update(resultTag='ArrayReference',Value1='preserved-lower-slot-Value1',Value2='upper-slot-Value1',
                indexBoundary='runtime-index-value-and-array-validity-unobserved',operandUse='ignored')
            else:out.update(fieldSelector=signed,fieldSelectorBoundary='runtime-field-table-or-internal-storey-index-unobserved',
                constructions={'ordinary':'ToObject-return -> managed[destination-position]; tag=6; Value1=position; Value2=Operand',
                  'newChain':'tags6/10,Operand>=0,fieldType.IsValueType -> requested FieldAddr(Object=managed[Value1],FieldIdList=[oldValue2,Operand]); tag=7; Value2=-1/-2',
                  'appendChain':'tag7,Operand>=0,fieldType.IsValueType -> requested FieldAddr(Object=old.Object,FieldIdList=Array.Copy-request(old-list)+Operand); tag=7; Value2-preserved'},
                negativeOldFieldRequest='NotSupportedException/throwRuntimeException; construction continues only if call returns normally',
                chainBoundary=spec['chainBoundary'])
            result.append(out)
    return result


def validate_selected_reference_address_rules(contract: dict, *, gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Fail closed on missing/mismatched explicit native paths before projection."""
    if gameassembly is None or metadata is None:
        return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths are required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'nativeInputs: selected hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.referenceAddress');extents=image.mapper.pdata_function_extents(image.pe)
    row=contract['consumer'];identity=('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False)
    base=_identity(image,row,identity,'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,row['bodyBytes'])
    ids={row['name']:row['id'] for row in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_reference_address_rules(image,contract['referenceAddressRules'] if spec is None else spec,body,base,ids,contract,extents)
