"""Authenticate the nonnegative field operand routes of the selected IFix VM.

FieldInfo[] is indexed by the authored nonnegative Operand. A null selected row
requests newFieldInfos lookups with the stored, typed Dictionary context. All
four routes retain full ordinary caller grammars and their existing negative
branch owners. Named slots prove requested Name, DeclaringType, FieldType and
GetValue identities; concrete reflection implementation/results are conditional.

Ldfld converts the preceding receiver with clone=false, rejects its null result,
requests the selected getter, then PushObject in that same slot. Ldsfld requests
a getter with null target and pushes one slot. The new-field branches request
CheckInit before their get. Loads perform no explicit managed clear in these
owned paths; helper effects remain separately conditional.

Stfld converts the lower receiver with clone=false and upper value with
clone=true. If IsPointer returns true and the converted value is non-null, its
selected native paths probe boxed nint/nuint, conditionally request Pointer.Unbox,
read a shared qword payload leaf, construct an IntPtr carrier and box nint.
The leaf is cataloged as UIntPtr.ToUInt64 because its registered native body is
shared; the call does not prove a unique source MethodDef choice. Stfld requests
the setter, conditionally UpdateReference for descriptor tags 5/6/7/10 when the
declaring type reports value type, clears both consumed managed indices and
rewinds two slots. Stsfld converts clone=true, requests a setter with null target,
clears one consumed managed index and rewinds one slot.

Each instance route's null receiver path constructs a NullReferenceException
request and reaches the separately authenticated INT3-terminated throw helper.
Selected raw metadata rejects byref and wrong return/static/generic/virtual
flags. No actual receiver, field value, pointer validity, runtime type selection,
callee mutation, alias/overlap, dictionary sharing, EH outcome or VM invocation
is observed. No anonymousStoreyInfos file-table framing is widened. Build anchors
belong only in contract rows; programs below are relocatable native grammars.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults,runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_slice,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_reference_update_rules import _usage as _dictionary_usage,_dictionary_target
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_indirect_opcode_rules import _carrier_label


class PositiveFieldRuleError(ValueError):
    """A nonnegative field claim lacks its selected native witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise PositiveFieldRuleError('positive-fields.'+label)


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _BOUNDARIES.items()),'unsupported schema/scope/boundary')
    for key,expected in [('methodRefs',_METHOD_REFS),('helperRefs',_HELPER_REFS),('usageRefs',_USAGE_REFS),('virtualRefs',_VIRTUAL_REFS),('tailRefs',_TAIL_REFS)]:
        _need(spec.get(key)==expected,'unsupported '+key)
    _need(set(spec.get('methods',{}))=={'fieldNotEqual','isPointer','nullCtor'}and set(spec.get('helpers',{}))=={'typeProbe'},'own catalog set differs')
    _need(set(spec.get('usageCells',{}))==set(_CELL_TYPES)|set(_OPAQUE),'stored usage set differs')
    _need(set(spec.get('blocks',{}))==set(_PROGRAMS)and set(spec.get('rules',{}))==set(_RULES),'block/rule set differs')
    for name,(entry,positive,negative,delta)in _RULES.items():
        row=spec['rules'][name]
        _need(type(row.get('opcodeId'))is int and row.get('entryBlock')==entry and row.get('positiveBlock')==positive
              and row.get('negativeRef')==negative and row.get('negativeRouteName')==name+'Negative'
              and type(row.get('stackDeltaSlots'))is int and row['stackDeltaSlots']==delta
              and row.get('selectedWhen')=='signed-Operand-nonnegative'
              and row.get('operandMeaning')=='fieldInfos-index-with-null-row-selecting-newFieldInfos','unsupported rule: '+name)


def _program(tokens: tuple,at: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in tokens:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='branch':
            prefix=bytes.fromhex(args[0]);width=1 if len(prefix)==1 and prefix!=b'\xe9'else 4
            p.add(prefix+(targets[args[1]]-(at+len(p.raw)+len(prefix)+width)).to_bytes(width,'little',signed=True))
        else:_need(False,'unknown finite grammar token')
    return p.finish()


def _layouts(image: Any,spec: dict,contract: dict) -> None:
    md=image.metadata;_need(set(spec.get('fieldLayouts',{}))==set(_FIELDS),'field owner set differs')
    fields={**_FIELDS,'IFix.Core.Value':{'Type':(16,'IFix.Core.ValueType'),'Value1':(20,'int'),'Value2':(24,'int')}}
    for ownername,selected in fields.items():
        owners=[t for t in md.types if md.type_full_name(t)==ownername];_need(len(owners)==1,'field owner differs: '+ownername)
        owner=owners[0];offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index);defs={md.string(f.name_index):f for f in md.fields_for(owner)}
        if ownername=='IFix.Core.Value':
            value=_ref(contract,'constrainedTypeOperand.stackEffect.valueLayout')
            _need(owner.bitfield&1 and value.get('type')==ownername and value.get('fieldOffsets')==offsets=={k:v[0]for k,v in selected.items()},'Value layout differs')
        else:
            rows=spec['fieldLayouts'][ownername];_need(set(rows)==set(selected),'field selection differs: '+ownername)
        for name,(offset,typ)in selected.items():
            definition=defs.get(name)
            _need(definition is not None and offsets.get(name)==offset and _type(image,definition.type_index)==typ,'raw named field differs: '+ownername+'.'+name)
            if ownername!='IFix.Core.Value':_need(type(rows[name].get('offset'))is int and rows[name]['offset']==offset and rows[name].get('type')==typ,'field declaration differs: '+name)
            pointer=image.pe.u64_at_va(_rva(image.registration['types'])+definition.type_index*8)
            _need(not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&0x10,'static field carrier: '+name)
    tags={r['name']:r['id']for r in enum_members(md,field_defaults(md),'IFix.Core.ValueType')}
    _need(all(type(tags.get(k))is int and tags[k]==v for k,v in {'StaticFieldReference':5,'FieldReference':6,'ChainFieldReference':7,'ArrayReference':10}.items()),'descriptor enum differs')


def _cells(image: Any,spec: dict,contract: dict,targets: dict[str,int]) -> dict[str,int]:
    rows={**spec['usageCells'],**{k:_ref(contract,p)for k,p in _USAGE_REFS.items()}};result={}
    for name,row in rows.items():
        at=_rva(row['cellRva']);result[name]=at;raw=image.pe.bytes_at_va(image.pe.image_base+at,8);word=int.from_bytes(raw,'little')
        _need(raw==bytes.fromhex(row['rawHex'])if 'rawHex'in row else word==_rva(row['encodedWord']),'stored usage bytes differ: '+name)
        if name=='dictionaryContext':
            definition=_dictionary_usage(image,dict(row,name='instanceDictionary'));_dictionary_target(image,definition,targets['dictionaryItem']);continue
        if name in _CELL_TYPES or name in _REF_TYPES:
            tag,typ=(_CELL_TYPES|_REF_TYPES)[name];index=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='positive-fields.'+name,offset=at)
            _need(type(row.get('usageTag'))is int and row['usageTag']==tag and row.get('identity',row.get('typeName'))==typ and _type(image,index)==typ,'named non-byref usage differs: '+name)
            _need(type(row.get('registeredTypeIndex'))is int and row['registeredTypeIndex']==index,'usage type index differs: '+name)
            pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
            _need(row.get('rawTypeHex')==image.pe.bytes_at_va(pointer,16).hex(),'raw usage record differs: '+name)
        else:_need(row.get('usageTag')==_OPAQUE[name]and row.get('identityBoundary')=='encoded-only'and word<=0xffffffff and word&1 and word>>29==_OPAQUE[name],'opaque usage promoted/malformed: '+name)
    return result


def validate_positive_field_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Authenticate within an already gated image and authenticated Execute."""
    _claims(spec);_layouts(image,spec,contract);targets={}
    for role,identity in _METHODS.items():
        row=_ref(contract,_METHOD_REFS[role])if role in _METHOD_REFS else spec['methods'][role];normalized=dict(row);normalized.setdefault('parameterCount',len(identity[2]))
        _need(type(normalized['parameterCount'])is int,'method count differs: '+role)
        for key,value in [('returnTypeName',identity[3]),('static',identity[4]),('generic',False)]:
            if key in row:_need(type(row[key])is type(value)and _carrier_label(row[key])==value,'method declaration differs: '+role)
        if 'returnType'in row:
            carrier=row['returnType'];_need(type(carrier)is str and _carrier_label(carrier)==identity[3]or type(carrier)is int and _type(image,carrier)==identity[3],'declared return carrier differs: '+role)
        targets[role]=_identity(image,normalized,identity,role,extents)
    for role,expected in _VIRTUALS.items():
        row=dict(_ref(contract,_VIRTUAL_REFS[role]));identity=expected[:5];slot=expected[5];row.setdefault('virtualSlot',row.get('slot'))
        _need(type(row.get('parameterCount'))is int and type(row.get('virtualSlot'))is int,'virtual declaration differs: '+role)
        for key,value in [('returnTypeName',identity[3]),('returnType',identity[3]),('static',False),('generic',False)]:
            if key in row:_need(type(row[key])is type(value)and _carrier_label(row[key])==value,'virtual signature declaration differs: '+role)
        _identity(image,row,identity,role,extents,virtual_slot=slot,body_required=False)
    for role in set(_HELPER_REFS)|set(spec['helpers']):
        row=_ref(contract,_HELPER_REFS[role])if role in _HELPER_REFS else spec['helpers'][role];count=row['byteCount']
        _need(type(count)is int and 0<count<=4096,'helper extent differs: '+role);at=_rva(row['rva']);targets[role]=at
        _hash(image.pe.bytes_at_va(image.pe.image_base+at,count),row,'helper.'+role)
    _need(spec['helpers']['typeProbe'].get('effectBoundary')=='opaque-callee-request-only','typeProbe outcome promoted')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['throwStop'],20),bytes.fromhex('4883ec2833c04889413848894140e87d030000cc'),'throwStop')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['subtractSlot'],10),bytes.fromhex('4863c2482bc8488bc1c3'),'subtractSlot')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['intPtrCtor'],4),bytes.fromhex('488911c3'),'intPtrCtor shared leaf')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['pointerPayload'],4),bytes.fromhex('488b01c3'),'pointerPayload shared leaf')
    for role,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);targets[role]=at;_hash(_slice(body,body_rva,at,row['byteCount'],role),row,role)
    for role,shape in [('zeroRegister','4533ed'),('slotWidth','be0c000000')]:
        row=_ref(contract,'basicOpcodeRules.sharedWindows.'+role);at=_rva(row['rva']);_hash(_slice(body,body_rva,at,row['byteCount'],role),row,role)
        _expect(_slice(body,body_rva,at,row['byteCount'],role),bytes.fromhex(shape),role)
        if role=='zeroRegister':_expect(_slice(body,body_rva,at,8,'saved zero'),bytes.fromhex('4533ed4c896c2468'),'saved zero')
    cells=_cells(image,spec,contract,targets)
    wrapper=_Program(targets['dictionaryWrapper']);wrapper.rip('4c8b05',cells['dictionaryContext']);wrapper.rip('e9',targets['dictionaryItem'])
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['dictionaryWrapper'],12),wrapper.finish(),'dictionaryWrapper')
    targets.update({k:_rva(v['rva'])for k,v in spec['blocks'].items()})
    for name,row in spec['rules'].items():
        negative=_ref(contract,row['negativeRef']);window=negative['window'];at=_rva(window['rva']);raw=_slice(body,body_rva,at,window['byteCount'],name+'.negativeWindow');_hash(raw,window,name+'.negativeWindow')
        _need(targets[row['entryBlock']]==at==_rva(negative['entryRva'])and targets[row['positiveBlock']]==_rva(negative['nonnegativeTargetRva']),'inherited field selection differs: '+name)
        neg=_rva(row['negativeRouteRva']);_need(at<neg<at+window['byteCount'],'negative boundary escapes inherited route: '+name)
        targets[row['negativeRouteName']]=neg
    for name,row in spec['blocks'].items():
        at=targets[name];raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,name);_expect(raw,_program(_PROGRAMS[name],at,targets,cells),'positive.'+name)
        _need(row.get('next')==_NEXT[name],'graph continuation differs: '+name)
        if _NEXT[name]and _FALLTHROUGH[name]:_need(at+len(raw)==targets[_NEXT[name]],'noncontiguous fallthrough: '+name)
    actual={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')};_need(actual==opcode_ids,'Code enum differs')
    dispatch=contract['dispatchRules'];extensions=dispatch['extensions'];entries={_rva(r['entryRva'])for r in dispatch['entryPoints']}
    for name,row in spec['rules'].items():
        _need(row['opcodeId']==actual[name],'Code ID differs: '+name)
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),actual[name],zero_compare_rva=_rva(extensions['zeroCompare']['rva']),sub_esi_rva=_rva(extensions['subEsi']['rva']),entry_rvas=entries)
        _need(entry==targets[row['entryBlock']],'selected field entry differs: '+name)
    return dict(status='validated_conditional_positive_field_rules',ruleCount=4,finiteBlockCount=len(_PROGRAMS),rules=project_positive_field_rules(None,spec),evidenceBoundary='conditional',executionBoundary='unobserved')


def project_positive_field_rules(instructions: list[dict]|None,spec: dict) -> list[dict]:
    """Project only nonnegative operands; other field selectors retain owners."""
    _claims(spec);result=[]
    selected=[dict(opcode=k,**v)for k,v in spec['rules'].items()]if instructions is None else instructions
    for instruction in selected:
        name=instruction.get('opcode')
        if name not in spec['rules']:continue
        row=spec['rules'][name];_need(type(instruction.get('opcodeId'))is int and instruction['opcodeId']==row['opcodeId'],'authored Code ID differs: '+name)
        signed=None
        if instructions is not None:
            operand=instruction.get('operand');_need(type(operand)is int and 0<=operand<=0xffffffff,'invalid authored Int32 operand: '+name)
            signed=operand if operand<0x80000000 else operand-0x100000000
            if 'operandSigned'in instruction:_need(type(instruction['operandSigned'])is int and instruction['operandSigned']==signed,'inconsistent signed operand: '+name)
            if signed<0:continue
        result.append(dict(opcode=name,opcodeId=row['opcodeId'],fieldIndex=signed,selectedWhen=row['selectedWhen'],normalTopDelta=row['stackDeltaSlots'],
            operandMeaning=row['operandMeaning'],evidenceBoundary='conditional',executionBoundary='unobserved',clearBoundary=spec['clearBoundary'],writebackBoundary=spec['writebackBoundary']))
    return result


def validate_selected_positive_field_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit GameAssembly.dll and metadata paths are required',rules=[])
    inputs=contract['nativeInputs'];gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail,rules=[])
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.positive-fields');extents=image.mapper.pdata_function_extents(image.pe)
    at=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents);body=image.pe.bytes_at_va(image.pe.image_base+at,contract['consumer']['bodyBytes'])
    ids={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_positive_field_rules(image,spec if spec is not None else contract['positiveFieldRules'],body,at,ids,contract,extents)


# Relocatable selected programs; contract rows supply provenance.
_BOUNDARIES = {'schema': 'endfield.ifix-vm-positive-field-rules.v1',
 'evidenceBoundary': 'conditional',
 'executionBoundary': 'unobserved',
 'scope': 'nonnegative-Ldfld-Stfld-Ldsfld-Stsfld',
 'slotBytes': 12,
 'conversionBoundary': 'receiver-clone-false;store-value-clone-true;results-and-runtime-sharing-unobserved',
 'writebackBoundary': 'Stfld-descriptor-tags-5-6-7-10-and-value-type-declaring-type-request-UpdateReference',
 'clearBoundary': 'Stfld-clears-two-consumed-managed-indices;Stsfld-clears-one;loads-no-explicit-clear-in-owned-route',
 'pointerBoundary': 'Stfld-IsPointer-result-and-nonnull-value-select-native-pointer-conversion-and-nint-box-request;actual-class-callee-outcomes-unobserved',
 'storageBoundary': 'valid-stable-slots-arrays-field-dictionary-targets-and-normal-return-required',
 'aliasBoundary': 'runtime-storage-aliases-overlap-and-callee-mutation-unobserved',
 'exceptionBoundary': 'null-receiver-requests-NullReferenceException-and-throwStop-INT3;external-EH-unobserved',
 'fileTableJoinBoundary': 'anonymousStoreyInfos-raw-framing-not-asserted'}

_METHOD_REFS = {'fieldSet': 'referenceUpdateRules.methods.fieldSet',
 'fieldEqual': 'referenceUpdateRules.methods.fieldEqual',
 'concatTriple': 'dispatchRules.methods.concat',
 'isValueType': 'referenceAddressRules.methods.isValueType',
 'pushObject': 'reflectionDispatch.methods.evaluationPush',
 'toObject': 'constrainedTypeOperand.stackEffect.toObjectMethod',
 'updateReference': 'initobjStackEffect.updateReferenceMethod',
 'checkInit': 'newFieldRules.methods.checkInit',
 'newFieldGet': 'chainFieldRules.methods.newFieldGet',
 'newFieldSet': 'referenceUpdateRules.methods.newFieldSet',
 'pointerUnbox': 'objectConversionRules.methods.pointerUnbox',
 'intPtrCtor': 'arrayRules.methods.intPtrCtor',
 'pointerPayload': 'arrayRules.methods.uintPtrUInt64'}

_HELPER_REFS = {'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
 'nullCheck': 'negativeFieldRules.helpers.nullCheck',
 'classInitialize': 'objectConversionRules.helpers.classInitialize',
 'typeDispatch': 'genericDelegateFactoryRules.helpers.returnQueryHelper',
 'throwStop': 'objectConversionRules.helpers.throwStop',
 'allocateObject': 'objectConversionRules.helpers.allocationThunk',
 'nameDispatch': 'virtualDispatchRules.helpers.nameInvoke',
 'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
 'assignmentCheck': 'functionPointerRules.helpers.assignmentCheck',
 'boxValue': 'objectConversionRules.helpers.enumBoxThunk',
 'unboxAddress': 'objectConversionRules.helpers.unboxAddress',
 'fieldGetDispatch': 'chainFieldRules.helpers.fieldGetDispatch',
 'usageResolve': 'objectConversionRules.helpers.usageResolveThunk',
 'pointerDifference': 'arithmeticWindows.stackPointerSubtract',
 'subtractSlot': 'basicOpcodeRules.helpers.subtractSlot',
 'dictionaryWrapper': 'referenceAddressRules.helpers.dictionaryWrapper',
 'dictionaryItem': 'referenceUpdateRules.helpers.dictionaryItem'}

_USAGE_REFS = {'dictionaryContext': 'referenceAddressRules.usageCells.dictionaryContext',
 'class_nint': 'objectConversionRules.usageCells.class_nint',
 'class_nuint': 'objectConversionRules.usageCells.class_nuint'}

_VIRTUAL_REFS = {'fieldName': 'virtualDispatchRules.virtualMethods.name',
 'declaringType': 'referenceAddressRules.virtualMethods.declaringType',
 'fieldType': 'referenceAddressRules.virtualMethods.fieldType',
 'fieldGet': 'chainFieldRules.fieldGet'}

_TAIL_REFS = {'slotPcTail': 'functionPointerRules.slotPcTail',
 'pushTopCommit': 'basicOpcodeRules.sharedWindows.pushTopCommit',
 'pushAdvance': 'basicOpcodeRules.sharedWindows.pushAdvance'}

_METHODS = {'fieldSet': ('System.Reflection.FieldInfo', 'SetValue', ['object', 'object'], 'void', False),
 'intPtrCtor': ('System.IntPtr', '.ctor', ['long'], 'void', False),
 'fieldEqual': ('System.Reflection.FieldInfo',
                'op_Equality',
                ['System.Reflection.FieldInfo', 'System.Reflection.FieldInfo'],
                'bool',
                True),
 'fieldNotEqual': ('System.Reflection.FieldInfo',
                   'op_Inequality',
                   ['System.Reflection.FieldInfo', 'System.Reflection.FieldInfo'],
                   'bool',
                   True),
 'concatTriple': ('System.String', 'Concat', ['object', 'object', 'object'], 'string', True),
 'pointerPayload': ('System.UIntPtr', 'ToUInt64', [], 'ulong', False),
 'isValueType': ('System.Type', 'get_IsValueType', [], 'bool', False),
 'isPointer': ('System.Type', 'get_IsPointer', [], 'bool', False),
 'pushObject': ('IFix.Core.EvaluationStackOperation',
                'PushObject',
                ['IFix.Core.Value*', 'IFix.Core.Value*', 'object[]', 'object', 'System.Type'],
                'void',
                True),
 'toObject': ('IFix.Core.EvaluationStackOperation',
              'ToObject',
              ['IFix.Core.Value*',
               'IFix.Core.Value*',
               'object[]',
               'System.Type',
               'IFix.Core.VirtualMachine',
               'bool'],
              'object',
              True),
 'updateReference': ('IFix.Core.EvaluationStackOperation',
                     'UpdateReference',
                     ['IFix.Core.Value*',
                      'IFix.Core.Value*',
                      'object[]',
                      'object',
                      'IFix.Core.VirtualMachine',
                      'System.Type'],
                     'void',
                     True),
 'checkInit': ('IFix.Core.NewFieldInfo',
               'CheckInit',
               ['IFix.Core.VirtualMachine', 'object'],
               'void',
               False),
 'newFieldGet': ('IFix.Core.NewFieldInfo', 'GetValue', ['object'], 'object', False),
 'newFieldSet': ('IFix.Core.NewFieldInfo', 'SetValue', ['object', 'object'], 'void', False),
 'pointerUnbox': ('System.Reflection.Pointer', 'Unbox', ['object'], 'void*', True),
 'nullCtor': ('System.NullReferenceException', '.ctor', ['string'], 'void', False)}

_FIELDS = {'IFix.Core.VirtualMachine': {'fieldInfos': (88, 'System.Reflection.FieldInfo[]'),
                              'newFieldInfos': (96,
                                                'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>')},
 'IFix.Core.NewFieldInfo': {'Name': (16, 'string'),
                            'DeclaringType': (24, 'System.Type'),
                            'FieldType': (32, 'System.Type')}}

_RULES = {'Ldfld': ('block002', 'block004', 'instanceFieldRules.rules.Ldfld', 0),
 'Stfld': ('block013', 'block014', 'instanceFieldRules.rules.Stfld', -2),
 'Ldsfld': ('block039', 'block040', 'negativeFieldRules.rules.Ldsfld', 1),
 'Stsfld': ('block044', 'block045', 'negativeFieldRules.rules.Stsfld', -1)}

_CELL_TYPES = {'usage01': (1, 'System.NullReferenceException')}

_REF_TYPES = {'class_nint': (1, 'nint'), 'class_nuint': (1, 'nuint')}

_OPAQUE = {'usage00': 5, 'usage02': 3}

_VIRTUALS = {'fieldName': ('System.Reflection.MemberInfo', 'get_Name', [], 'string', False, 8),
 'declaringType': ('System.Reflection.MemberInfo', 'get_DeclaringType', [], 'System.Type', False, 9),
 'fieldType': ('System.Reflection.FieldInfo', 'get_FieldType', [], 'System.Type', False, 19),
 'fieldGet': ('System.Reflection.FieldInfo', 'GetValue', ['object'], 'object', False, 27)}

_NEXT = {'block000': None,
 'block001': 'block002',
 'block002': 'LdfldNegative',
 'block003': 'block004',
 'block004': 'block005',
 'block005': 'block006',
 'block006': 'block007',
 'block007': 'block008',
 'block008': 'block009',
 'block009': 'block010',
 'block010': 'block011',
 'block011': None,
 'block012': None,
 'block013': 'StfldNegative',
 'block014': 'block015',
 'block015': 'block016',
 'block016': 'block017',
 'block017': 'block018',
 'block018': 'block019',
 'block019': 'block020',
 'block020': 'block021',
 'block021': 'block022',
 'block022': 'block023',
 'block023': 'block024',
 'block024': 'block025',
 'block025': 'block026',
 'block026': 'block027',
 'block027': 'block028',
 'block028': None,
 'block029': 'block030',
 'block030': 'block031',
 'block031': 'block032',
 'block032': 'block033',
 'block033': 'block034',
 'block034': 'block035',
 'block035': 'block036',
 'block036': 'block037',
 'block037': 'block038',
 'block038': None,
 'block039': 'LdsfldNegative',
 'block040': 'block041',
 'block041': 'block042',
 'block042': 'block043',
 'block043': 'block044',
 'block044': 'StsfldNegative',
 'block045': 'block046',
 'block046': 'block047',
 'block047': 'block048',
 'block048': 'block049',
 'block049': 'block050',
 'block050': 'block051',
 'block051': None,
 'block052': None,
 'block053': None}

_FALLTHROUGH = {'block000': False,
 'block001': False,
 'block002': True,
 'block003': False,
 'block004': True,
 'block005': False,
 'block006': True,
 'block007': True,
 'block008': True,
 'block009': False,
 'block010': True,
 'block011': False,
 'block012': False,
 'block013': True,
 'block014': True,
 'block015': False,
 'block016': True,
 'block017': True,
 'block018': True,
 'block019': True,
 'block020': True,
 'block021': True,
 'block022': False,
 'block023': True,
 'block024': False,
 'block025': True,
 'block026': True,
 'block027': True,
 'block028': False,
 'block029': True,
 'block030': True,
 'block031': True,
 'block032': True,
 'block033': True,
 'block034': True,
 'block035': False,
 'block036': True,
 'block037': True,
 'block038': False,
 'block039': True,
 'block040': True,
 'block041': False,
 'block042': True,
 'block043': False,
 'block044': True,
 'block045': True,
 'block046': False,
 'block047': True,
 'block048': True,
 'block049': False,
 'block050': True,
 'block051': False,
 'block052': False,
 'block053': False}

_PROGRAMS = {'block000': ('8bd6498bcc', ('call', 'subtractSlot'), ('branch', 'e9', 'pushTopCommit')),
 'block001': ('498bcc', ('branch', 'e9', 'pushAdvance')),
 'block002': ('8bd6498bcc',
              ('call', 'subtractSlot'),
              '4c8be8498bce',
              ('call', 'nullCheck'),
              '4d637e044c8b742468453bfe',
              ('branch', '7d', 'block004')),
 'block003': ('4c8b6c2468', ('branch', 'e9', 'slotPcTail')),
 'block004': ('488b5f58488bcb',
              ('call', 'nullCheck'),
              '498bd7488bcb',
              ('call', 'arrayFetch'),
              '488bf84533c033d2488bc8',
              ('call', 'fieldEqual'),
              '413ac6',
              ('branch', '75', 'block006')),
 'block005': ('488bcf',
              ('call', 'nullCheck'),
              'b908000000488bd7',
              ('call', 'nameDispatch'),
              '488bf0488bcf',
              ('call', 'nullCheck'),
              'b913000000488bd7',
              ('call', 'typeDispatch'),
              '4c8be0488bcf',
              ('call', 'nullCheck'),
              'b909000000488bd7',
              ('call', 'typeDispatch'),
              '488bd8',
              ('branch', 'e9', 'block007')),
 'block006': ('4c8ba424f0030000498b5c2460488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '488b7310498b5c2460488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4c8b6320488b8424f0030000488b5860488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '488b5b18'),
 'block007': ('4c897424304488742428488b8424f003000048894424204c8bcb4c8b842408040000498bd5488b8c2410040000',
              ('call', 'toObject'),
              '4c8bf0483b442468',
              ('branch', '0f84', 'block052')),
 'block008': ('4533c033d2488bcf', ('call', 'fieldEqual'), '488b742468403ac6', ('branch', '75', 'block010')),
 'block009': ('488bcf',
              ('call', 'nullCheck'),
              'b91b0000004d8bc6488bd7',
              ('call', 'fieldGetDispatch'),
              ('branch', 'eb', 'block011')),
 'block010': ('488bbc24f0030000488b5f60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c94d8bc6488bd7488bcb',
              ('call', 'checkInit'),
              '488b5f60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c0498bd6488bcb',
              ('call', 'newFieldGet')),
 'block011': ('48897424284c896424204c8bc84c8b842408040000498bd5488b8c2410040000',
              ('call', 'pushObject'),
              '4c8b642458',
              ('branch', 'e9', 'block003')),
 'block012': ('be0c000000', ('branch', 'e9', 'block001')),
 'block013': ('8bd6498bcc',
              ('call', 'subtractSlot'),
              '8bd6488bc8',
              ('call', 'subtractSlot'),
              '488bf048898424b00000004889842418020000498bce',
              ('call', 'nullCheck'),
              '458b6e044489ac2418040000443b6c2468',
              ('branch', '0f8d', 'block014')),
 'block014': ('488b5f58498bce',
              ('call', 'nullCheck'),
              '49637e04488bcb',
              ('call', 'nullCheck'),
              '488bd7488bcb',
              ('call', 'arrayFetch'),
              '4c8bf048898424200200004533c033d2488bc8',
              ('call', 'fieldEqual'),
              '488b5c24683ac3',
              ('branch', '75', 'block016')),
 'block015': ('498bce',
              ('call', 'nullCheck'),
              'b908000000498bd6',
              ('call', 'nameDispatch'),
              '488bf8498bce',
              ('call', 'nullCheck'),
              'b913000000498bd6',
              ('call', 'typeDispatch'),
              '488bf0498bce',
              ('call', 'nullCheck'),
              'b909000000498bd6',
              ('call', 'typeDispatch'),
              '4c8bf848898424b0010000',
              ('branch', 'e9', 'block017')),
 'block016': ('4c8bbc24f0030000498b5f60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd5488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '488b7b10498b5f60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd5488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '488b7320498b5f60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd5488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4c8b7b184c89bc24b0010000488b5c2468'),
 'block017': ('48895c2430885c2428488b8424f003000048894424204d8bcf4c8b842408040000488b9424b0000000488b8c2410040000',
              ('call', 'toObject'),
              '4c8be04889842428020000483bc3',
              ('branch', '0f84', 'block053')),
 'block018': ('ba0c000000488b4c2458',
              ('call', 'subtractSlot'),
              '48895c2430c644242801488b8c24f003000048894c24204c8bce4c8b842408040000488bd0488b8c2410040000',
              ('call', 'toObject'),
              '488bf84889842430020000488bce',
              ('call', 'nullCheck'),
              '33d2488bce',
              ('call', 'isPointer'),
              '3ac3',
              ('branch', '0f84', 'block027')),
 'block019': ('483bfb', ('branch', '0f84', 'block027')),
 'block020': (('rip', '488b15', 'class_nint'),
              '488bcf',
              ('call', 'typeProbe'),
              '488bcf483bc3',
              ('branch', '75', 'block025')),
 'block021': (('rip', '488b15', 'class_nuint'),
              ('call', 'typeProbe'),
              '488bcf483bc3',
              ('branch', '75', 'block023')),
 'block022': ('33d2', ('call', 'pointerUnbox'), ('branch', 'eb', 'block024')),
 'block023': (('rip', '488b15', 'class_nuint'),
              ('call', 'unboxAddress'),
              '488b004889842498010000',
              ('rip', '488b0d', 'class_nuint'),
              ('call', 'classInitialize'),
              '33d2488d8c2498010000',
              ('call', 'pointerPayload')),
 'block024': (('branch', 'eb', 'block026'),),
 'block025': (('rip', '488b15', 'class_nint'),
              ('call', 'unboxAddress'),
              '488b0048898424a001000033d2488d8c24a0010000',
              ('call', 'pointerPayload')),
 'block026': ('48899c24a80100004533c0488bd0488d8c24a8010000',
              ('call', 'intPtrCtor'),
              '488b8424a80100004889842410020000488d942410020000',
              ('rip', '488b0d', 'class_nint'),
              ('call', 'boxValue'),
              '488bf8'),
 'block027': ('488bb424b00000004533c033d2498bce',
              ('call', 'fieldNotEqual'),
              '3ac3',
              ('branch', '0f85', 'block029')),
 'block028': ('4c8bb424f0030000498b5e60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd5488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c94c8bc7498bd4488bcb',
              ('call', 'newFieldSet'),
              ('branch', 'e9', 'block030')),
 'block029': ('498bce',
              ('call', 'nullCheck'),
              '4533c94c8bc7498bd4498bce',
              ('call', 'fieldSet'),
              '4c8bb424f0030000'),
 'block030': ('488bce', ('call', 'nullCheck'), '833e06', ('branch', '74', 'block034')),
 'block031': ('488bce', ('call', 'nullCheck'), '833e07', ('branch', '74', 'block034')),
 'block032': ('488bce', ('call', 'nullCheck'), '833e05', ('branch', '74', 'block034')),
 'block033': ('488bce', ('call', 'nullCheck'), '833e0a', ('branch', '75', 'block036')),
 'block034': ('498bcf',
              ('call', 'nullCheck'),
              '33d2498bcf',
              ('call', 'isValueType'),
              '4c8b6c2468413ac5',
              ('branch', '74', 'block037')),
 'block035': ('4c896c24304c897c24284c897424204d8bcc4c8bbc24080400004d8bc7488bd64c8bb42410040000498bce',
              ('call', 'updateReference'),
              ('branch', 'eb', 'block038')),
 'block036': ('4c8b6c2468',),
 'block037': ('4c8bb424100400004c8bbc2408040000',),
 'block038': ('498bd6488bce',
              ('call', 'pointerDifference'),
              '498bcf',
              ('call', 'nullCheck'),
              '33d2498bcf',
              ('call', 'assignmentCheck'),
              '498bd6488bce',
              ('call', 'pointerDifference'),
              '488bc849bcabaaaaaaaaaaaa2a498bc448f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
              ('call', 'managedStore'),
              'bf0c0000008bd7488b5c2458488bcb',
              ('call', 'subtractSlot'),
              '498bd6488bc8',
              ('call', 'pointerDifference'),
              '498bcf',
              ('call', 'nullCheck'),
              '33d2498bcf',
              ('call', 'assignmentCheck'),
              '8bd7488bcb',
              ('call', 'subtractSlot'),
              '498bd6488bc8',
              ('call', 'pointerDifference'),
              '488bc8498bc448f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
              ('call', 'managedStore'),
              '4c8be648897424584889742460',
              ('branch', 'e9', 'slotPcTail')),
 'block039': ('498bce', ('call', 'nullCheck'), '49637e04413bfd', ('branch', '0f8d', 'block040')),
 'block040': ('4c8bb424f0030000498b5e58488bcb',
              ('call', 'nullCheck'),
              '488bd7488bcb',
              ('call', 'arrayFetch'),
              '488bd84533c033d2488bc8',
              ('call', 'fieldEqual'),
              '413ac5',
              ('branch', '75', 'block042')),
 'block041': ('488bcb',
              ('call', 'nullCheck'),
              'b913000000488bd3',
              ('call', 'typeDispatch'),
              '488bf0488bcb',
              ('call', 'nullCheck'),
              'b91b0000004533c0488bd3',
              ('call', 'fieldGetDispatch'),
              ('branch', 'e9', 'block043')),
 'block042': ('498b5e60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '8bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c94533c0498bd6488bcb',
              ('call', 'checkInit'),
              '498b5e60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '8bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '488b7320498b5e60488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '8bd7488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c033d2488bcb',
              ('call', 'newFieldGet')),
 'block043': ('4c896c242848897424204c8bc84d8bc7498bd4488b8c2410040000',
              ('call', 'pushObject'),
              ('branch', 'e9', 'block012')),
 'block044': ('498bce', ('call', 'nullCheck'), '4d637604453bf5', ('branch', '0f8d', 'block045')),
 'block045': ('488b5f58488bcb',
              ('call', 'nullCheck'),
              '498bd6488bcb',
              ('call', 'arrayFetch'),
              '488bf84533c033d2488bc8',
              ('call', 'fieldEqual'),
              '413ac5',
              ('branch', '75', 'block047')),
 'block046': ('488bcf',
              ('call', 'nullCheck'),
              'b913000000488bd7',
              ('call', 'typeDispatch'),
              '488bd8',
              ('branch', 'eb', 'block048')),
 'block047': ('488b8424f0030000488b5860488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd6488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '488b5b20'),
 'block048': ('8bd6498bcc',
              ('call', 'subtractSlot'),
              '4c896c2430c644242801488b8c24f003000048894c24204c8bcb4d8bc7488bd0488b8c2410040000',
              ('call', 'toObject'),
              '488bf04533c033d2488bcf',
              ('call', 'fieldEqual'),
              '413ac5',
              ('branch', '75', 'block050')),
 'block049': ('488bcf',
              ('call', 'nullCheck'),
              '4533c94c8bc633d2488bcf',
              ('call', 'fieldSet'),
              ('branch', 'eb', 'block051')),
 'block050': ('488b8424f0030000488b5860488bcb',
              ('call', 'nullCheck'),
              ('rip', '4c8b05', 'dictionaryContext'),
              '418bd6488bcb',
              ('call', 'dictionaryWrapper'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c94c8bc633d2488bcb',
              ('call', 'newFieldSet')),
 'block051': ('be0c0000008bd6498bcc',
              ('call', 'subtractSlot'),
              '488b9c2410040000488bd3488bc8',
              ('call', 'pointerDifference'),
              '498bcf',
              ('call', 'nullCheck'),
              '33d2498bcf',
              ('call', 'assignmentCheck'),
              '8bd6498bcc',
              ('call', 'subtractSlot'),
              '488bd3488bc8',
              ('call', 'pointerDifference'),
              '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
              ('call', 'managedStore'),
              ('branch', 'e9', 'block000')),
 'block052': (('rip', '488d0d', 'usage00'),
              ('call', 'usageResolve'),
              '4533c94c8bc6488bd0488bcb',
              ('call', 'concatTriple'),
              '488bf8',
              ('rip', '488d0d', 'usage01'),
              ('call', 'usageResolve'),
              '488bc8',
              ('call', 'allocateObject'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c0488bd7488bcb',
              ('call', 'nullCtor'),
              ('rip', '488d0d', 'usage02'),
              ('call', 'usageResolve'),
              '488bd0488bcb',
              ('call', 'throwStop')),
 'block053': (('rip', '488d0d', 'usage00'),
              ('call', 'usageResolve'),
              '4533c94c8bc7488bd0498bcf',
              ('call', 'concatTriple'),
              '488bf8',
              ('rip', '488d0d', 'usage01'),
              ('call', 'usageResolve'),
              '488bc8',
              ('call', 'allocateObject'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '4533c0488bd7488bcb',
              ('call', 'nullCtor'),
              ('rip', '488d0d', 'usage02'),
              ('call', 'usageResolve'),
              '488bd0488bcb',
              ('call', 'throwStop'))}
