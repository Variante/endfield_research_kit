"""Authenticate complete selected IFix object-conversion programs offline.

ToObject dispatches all eleven ValueType tags. Integer/Long request boxing with
the named primitive class and selected payload width when the supplied Type
matches; Boolean boxing tests Integer==1. Float/Double accept only their named
Type. Integer/Long otherwise request Enum.ToObject if the Type enum predicate
is true, and return null on a normal non-enum mismatch. StackReference reads
the qword at Value1 and recursively calls ToObject with the same arguments.
This differs from the one-hop mutating resolveStackReference program.

Object reads managedStack[Value1], optionally requesting Pointer conversion.
ValueType reads that object directly, or requests VM.objectClone.Clone for a
non-null value when valueTypeClone is true. ArrayReference forwards Value2 to
Array.GetValue. Field/StaticFieldReference select reflected/new fields or the
negative AnonymousStorey/staticFields route. ChainFieldReference selects
FieldAddr at the descriptor's own base-relative slot position and forwards
its root, IDs, last layer and Value2!=-1 to the separately owned mGet program.

PushObject sends non-null primitives to UnboxPrimitive and enums to Convert
with an Integer/Long tag selected from their underlying Type. Other objects
are stored at the base-relative slot position; null uses Object, and non-null
objects select ValueType versus Object through IsValueTypeImpl. UnboxPrimitive
optionally requests ChangeType for an actual enum object, then selects the
boxed object's class. Boolean unboxing normalizes any nonzero byte to one;
small signed/unsigned widths extend to Int32, Long/native-pointer widths copy
eight bytes, and Float/Double copy their payload bits. Integer/Float writes do
not clear Value2. Neither conversion program advances an interpreter top.

The finite relocatable grammars check every body byte, including unsupported
routes and external exception landing blocks. Raw metadata carriers reject
byref signatures/types and require named static/non-generic identities. Caller
field/table layouts and stored Dictionary context reuse their owning catalogs.
Boxing/unboxing requests, Type dispatch, reflection, cloning, runtime sharing,
exception-handler selection, recursion depth/storage stability and actual
execution remain conditional or unobserved. Runtime helper outcomes are not
emulated. Raw anonymousStoreyInfos framing/file-table joins remain refused.
The caller must supply the selected input gate; the standalone wrapper below
requires explicit native paths and fails closed before producing rules.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_field_offsets, runtime_type_name
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_negative_field_rules import _ref
from scripts.game_data import ifix_vm_reference_update_rules as reference_rules


class ObjectConversionRuleError(ValueError):
    """A conversion claim lacks its selected native witness."""


_METHOD_REFS = {
    'toObject':'constrainedTypeOperand.stackEffect.toObjectMethod',
    'pushObject':'reflectionDispatch.methods.evaluationPush',
    'getTypeFromHandle':'genericDelegateFactoryRules.methods.getTypeFromHandle',
    'objectGetType':'functionPointerRules.helpers.objectGetType',
    'fieldEqual':'referenceUpdateRules.methods.fieldEqual',
    'storeyGet':'instanceFieldRules.methods.Get', 'clone':'slotCopyRules.methods.clone',
    'chainGet':'chainFieldRules.methods.chainGet', 'newFieldGet':'chainFieldRules.methods.newFieldGet',
    'checkInit':'newFieldRules.methods.checkInit', 'arrayGet':'chainFieldRules.methods.arrayGet',
}
_HELPER_REFS = {
    'typeInitialize':'referenceUpdateRules.helpers.typeInitialize', 'nonnull':'negativeFieldRules.helpers.nullCheck',
    'typeTest':'functionPointerRules.helpers.typeTest', 'assignmentCheck':'functionPointerRules.helpers.assignmentCheck',
    'managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'dictionaryItem':'referenceUpdateRules.helpers.dictionaryItem',
    'fieldGetDispatch':'chainFieldRules.helpers.fieldGetDispatch', 'opaqueObject':'stackReferenceRules.nullObjectHelper',
    'nullPrimitive':'referenceUpdateRules.helpers.nullFailure',
}
_USAGE_REFS = {
    'anonymousType':'referenceUpdateRules.usageCells.anonymousType', 'arrayType':'referenceUpdateRules.usageCells.arrayType',
    'chainType':'referenceUpdateRules.usageCells.chainType', 'instanceDictionary':'referenceUpdateRules.usageCells.instanceDictionary',
}
_METHODS = {
    'toObject':('IFix.Core.EvaluationStackOperation','ToObject',['IFix.Core.Value*','IFix.Core.Value*','object[]','System.Type','IFix.Core.VirtualMachine','bool'],'object',True),
    'pushObject':('IFix.Core.EvaluationStackOperation','PushObject',['IFix.Core.Value*','IFix.Core.Value*','object[]','object','System.Type'],'void',True),
    'unboxPrimitive':('IFix.Core.EvaluationStackOperation','UnboxPrimitive',['IFix.Core.Value*','object','System.Type'],'void',True),
    'getTypeFromHandle':('System.Type','GetTypeFromHandle',['System.RuntimeTypeHandle'],'System.Type',True),
    'objectGetType':('System.Object','GetType',[],'System.Type',False),
    'fieldEqual':('System.Reflection.FieldInfo','op_Equality',['System.Reflection.FieldInfo','System.Reflection.FieldInfo'],'bool',True),
    'storeyGet':('IFix.Core.AnonymousStorey','Get',['int','System.Type','IFix.Core.VirtualMachine','bool'],'object',False),
    'clone':('IFix.Core.ObjectClone','Clone',['object'],'object',False),
    'chainGet':('IFix.Core.EvaluationStackOperation','mGet',['bool','object','int','int[]','System.Reflection.FieldInfo[]','System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>'],'object',True),
    'newFieldGet':('IFix.Core.NewFieldInfo','GetValue',['object'],'object',False),
    'checkInit':('IFix.Core.NewFieldInfo','CheckInit',['IFix.Core.VirtualMachine','object'],'void',False),
    'changeType':('System.Convert','ChangeType',['object','System.Type'],'object',True),
    'toInt32':('System.Convert','ToInt32',['object'],'int',True),
    'toInt64':('System.Convert','ToInt64',['object'],'long',True),
    'toUInt64':('System.Convert','ToUInt64',['object'],'ulong',True),
    'enumUnderlying':('System.Enum','GetUnderlyingType',['System.Type'],'System.Type',True),
    'enumInt':('System.Enum','ToObject',['System.Type','int'],'object',True),
    'enumLong':('System.Enum','ToObject',['System.Type','long'],'object',True),
    'uintPtrCtor':('System.UIntPtr','.ctor',['ulong'],'void',False),
    'arrayGet':('System.Array','GetValue',['int'],'object',False),
    'pointerBox':('System.Reflection.Pointer','Box',['void*','System.Type'],'object',True),
    'pointerUnbox':('System.Reflection.Pointer','Unbox',['object'],'void*',True),
    'concatPair':('System.String','Concat',['object','object'],'string',True),
    'concatArray':('System.String','Concat',['object[]'],'string',True),
    'unsupportedCtor':('System.NotImplementedException','.ctor',['string'],'void',False),
}
_HELPERS = {'typePredicate','classInitialize','boxRequest','unboxAddress','enumBoxThunk',
            'usageResolveThunk','allocationThunk','arrayAllocate','throwStop','nullStop','boundsStop'}
_PREDICATES = {'isPointer':('IsPointerImpl',45), 'isEnum':('get_IsEnum',91),
               'isPrimitive':('IsPrimitiveImpl',95), 'isValueType':('IsValueTypeImpl',97)}
_TAGS = {'Integer':0,'Long':1,'Float':2,'Double':3,'StackReference':4,'StaticFieldReference':5,
         'FieldReference':6,'ChainFieldReference':7,'Object':8,'ValueType':9,'ArrayReference':10}
_TO_OBJECT = {
    'Integer':'named-int32-width-box-request;bool=(Value1==1);enum-int-request-or-null',
    'Long':'named-int64-or-native-pointer-box-request;enum-long-request-or-null',
    'Float':'matching-float-Type:box-raw32;other-Type:null',
    'Double':'matching-double-Type:box-raw64;other-Type:null',
    'StackReference':'ToObject(base,qword-at-Value1,managed,type,VM,valueTypeClone)',
    'StaticFieldReference':'Value1<0:staticFields[~Value1];else:fieldInfos-or-newFieldInfos[Value1],owner=null',
    'FieldReference':'Value2<0:AnonymousStorey.Get(~Value2,type,VM,clone);else:fieldInfos-or-newFieldInfos[Value2],owner=managed[Value1]',
    'ChainFieldReference':'mGet(Value2!=-1,FieldAddr.Object,FieldIdList.Length-1,FieldIdList,fieldInfos,newFieldInfos)',
    'Object':'managed[Value1];pointer-Type:conditional-Pointer-request;otherwise:selected-object',
    'ValueType':'managed[Value1];clone-flag-and-nonnull:VM.objectClone.Clone(selected-object)',
    'ArrayReference':'cast-Array(managed[Value1]).GetValue(Value2)',
}
_PRIMITIVE_BOX = {
    'Integer':{'int':'raw32','uint':'raw32','bool':'Value1==1','byte':'low8','sbyte':'low8',
               'short':'low16','char':'low16','ushort':'low16'},
    'Long':{'long':'raw64','ulong':'raw64','nint':'raw64','nuint':'UIntPtr.ctor(raw64)'},
    'Float':{'float':'raw32'}, 'Double':{'double':'raw64'},
}
_UNBOX = {'int':('Integer','raw32'), 'uint':('Integer','raw32'), 'bool':('Integer','byte!=0'),
          'byte':('Integer','zero-extend8'), 'sbyte':('Integer','sign-extend8'),
          'char':('Integer','zero-extend16'), 'ushort':('Integer','zero-extend16'), 'short':('Integer','sign-extend16'),
          'long':('Long','raw64'), 'ulong':('Long','raw64'), 'nint':('Long','raw64'), 'nuint':('Long','raw64'),
          'float':('Float','raw32'), 'double':('Double','raw64')}
_PUSH = {
    'null':'store-managed-at-slot-position;Value1=position;Type=Object;Value2-preserved',
    'primitive':'UnboxPrimitive(slot,obj,type)',
    'enum':'underlying-long-or-ulong:Long+Convert64;other-underlying:Integer+ConvertInt32',
    'pointer':'IntPtr-or-UIntPtr-payload-or-Pointer.Unbox;nonzero:Pointer.Box(bits,type);zero:retain-object',
    'other':'store-managed-at-slot-position;Value1=position;Type=IsValueTypeImpl(type)?ValueType:Object;Value2-preserved',
}
_BOUNDARIES = {
    'schema':'endfield.ifix-vm-object-conversion-rules.v1', 'evidenceBoundary':'conditional', 'executionBoundary':'unobserved',
    'scope':'complete-ToObject-PushObject-UnboxPrimitive-programs', 'slotBytes':12,'pointerBytes':8,
    'valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout', 'fieldLayoutsRef':'referenceUpdateRules.fieldLayouts',
    'dictionaryUsageRef':'referenceUpdateRules.usageCells.instanceDictionary',
    'recursiveReferenceBoundary':'recursive-ToObject-unbounded-runtime-depth-stability-unobserved',
    'helperResultBoundary':'boxing-unboxing-type-dispatch-reflection-clone-and-runtime-sharing-results-unobserved',
    'exceptionalFlowBoundary':'complete-bytes-including-landing-blocks-external-handler-selection-unresolved',
    'fileTableJoinBoundary':'anonymousStoreyInfos-raw-framing-not-asserted',
}


def _fail(label: str, detail: str) -> None:
    raise ObjectConversionRuleError(f'object-conversion.{label}: {detail}')


def _number(value: str | int) -> int:
    if isinstance(value,bool) or not isinstance(value,(str,int)): _fail('number','expected integer or encoded integer')
    return int(value,0) if isinstance(value,str) else value


def _expect(ok: bool,label: str,detail: str) -> None:
    if not ok: _fail(label,detail)


def _claims(spec: dict) -> None:
    _expect(all(type(spec.get(k)) is type(v) and spec.get(k)==v for k,v in _BOUNDARIES.items()),'claims','unsupported schema/scope/boundary')
    for name,expected in [('methodRefs',_METHOD_REFS),('helperRefs',_HELPER_REFS),('usageRefs',_USAGE_REFS),
                          ('tagMembers',_TAGS),('toObjectRules',_TO_OBJECT),('primitiveBoxRules',_PRIMITIVE_BOX),
                          ('unboxRules',{k:list(v) for k,v in _UNBOX.items()}),('pushRules',_PUSH)]:
        _expect(spec.get(name)==expected,name,'unsupported declarations')
    _expect(set(spec.get('methods',{}))==set(_METHODS)-set(_METHOD_REFS),'methods','missing/unsupported method role')
    _expect(set(spec.get('helpers',{}))==_HELPERS,'helpers','missing/unsupported helper role')
    _expect(all(type(value) is int for value in spec['tagMembers'].values()),'tags','Boolean/non-integer tag ID')


def _type(image: Any,index: int,label: str) -> str:
    _expect(type(index) is int and 0<=index<image.registration['typesCount'],label,'type index outside registration')
    pointer=image.pe.u64_at_va(_number(image.registration['types'])+index*8)
    raw=image.pe.bytes_at_va(pointer,16)
    _expect(len(raw)==16 and not raw[11]&0x20,label,'malformed/by-reference raw type carrier')
    return runtime_type_name(image.pe,image.metadata,pointer)


def _hash(raw: bytes,row: dict,label: str,complete: bool=False) -> None:
    expected=row.get('bodySha256' if complete else 'sha256')
    _expect(isinstance(expected,str) and hashlib.sha256(raw).hexdigest().upper()==expected.upper(),label,'selected native bytes/hash differ')


def _identity(image: Any,row: dict,role: str,extents: dict[int,int]) -> int:
    owner,name,params,result,static=_METHODS[role];md=image.metadata
    count=row.get('parameterCount',len(row['parameterTypes']) if isinstance(row.get('parameterTypes'),list) else None)
    _expect(type(count) is int and (row.get('type'),row.get('method'),count)==(owner,name,len(params)),role,'named method differs')
    if 'parameterTypes' in row: _expect(row['parameterTypes']==params,role,'declared parameters differ')
    if 'returnTypeName' in row:
        _expect({'System.Object':'object','System.Void':'void'}.get(row['returnTypeName'],row['returnTypeName'])==result,role,'declared return differs')
    for key,value in [('static',static),('generic',False)]:
        if key in row:_expect(type(row[key]) is bool and row[key]==value,role,'declared method kind differs')
    selected=[m for t in md.types if md.type_full_name(t)==owner for m in md.methods_for(t)
              if md.string(m.name_index)==name and m.parameter_count==len(params)
              and [_type(image,p.type_index,role+'.parameter') for p in md.parameters_for(m)]==params]
    _expect(len(selected)==1,role,f'exact overload count differs actual={len(selected)}')
    method=selected[0]
    _expect(_type(image,method.return_type,role+'.return')==result and bool(method.flags&0x10)==static
            and method.generic_container_index==-1,role,'return/static/generic metadata kind differs')
    pointer=image.method_pointer_va(method);rva=pointer-image.pe.image_base
    _expect(method.token==_number(row['token']) and rva==_number(row['rva']),role,'metadata token/registered pointer differs')
    if 'bodyBytes' in row:
        _expect(type(row['bodyBytes']) is int and 0<row['bodyBytes']<=20000 and extents.get(pointer)==pointer+row['bodyBytes'],role,'complete extent differs')
        _hash(image.pe.bytes_at_va(pointer,row['bodyBytes']),row,role,True)
    elif 'byteCount' in row:
        _expect(type(row['byteCount']) is int and 0<row['byteCount']<=1024,role,'unsupported entry window')
        _hash(image.pe.bytes_at_va(pointer,row['byteCount']),row,role)
    return rva


def _body(base: int,name: str,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(base)
    for token in _PROGRAMS[name]:
        if isinstance(token,str):p.add(token)
        elif token[0]=='call':p.call(targets[token[1]])
        else:p.rip(token[1],cells[token[2]],bytes.fromhex(token[3]))
    return p.finish()


def _cell(image: Any,name: str,row: dict) -> int:
    address=_number(row['cellRva']);label='cells.'+name
    if name.endswith('InitRead'):
        _expect(row.get('identityBoundary')=='unbacked-runtime-init-flag-value-unobserved'
                and set(row)=={'cellRva','identityBoundary'},label,'runtime init flag value must remain unobserved')
        return address
    raw=image.pe.bytes_at_va(image.pe.image_base+address,8)
    _expect(int.from_bytes(raw,'little')==_number(row['encodedWord']),label,'encoded usage word differs')
    if name.startswith(('class_','handle_')):
        expected=name.split('_',1)[1].replace('System_','System.').replace('IFix_Core_','IFix.Core.').replace('Array','[]')
        tag=1 if name.startswith('class_') else 2
        index=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='object-conversion.'+name,offset=address)
        _expect(row.get('usageTag')==tag and row.get('registeredTypeIndex')==index and row.get('typeName')==expected
                and _type(image,index,label)==expected,label,'named non-byref stored type differs')
        pointer=image.pe.u64_at_va(_number(image.registration['types'])+index*8)
        _expect(image.pe.bytes_at_va(pointer,16).hex()==row.get('rawTypeHex'),label,'raw selected type record differs')
    else:
        tag=3 if name.startswith('exceptionMethod') else 5
        _expect(row.get('identityBoundary')=='encoded-only' and row.get('usageTag')==tag
                and int.from_bytes(raw,'little')<=0xffffffff and raw[0]&1 and int.from_bytes(raw,'little')>>29==tag,
                label,'opaque stored usage must remain unresolved with its reviewed tag')
    return address


def _predicates(image: Any,rows: dict) -> None:
    _expect(set(rows)==set(_PREDICATES),'typePredicates','unsupported virtual predicate set')
    md=image.metadata;owners=[t for t in md.types if md.type_full_name(t)=='System.Type']
    _expect(len(owners)==1,'typePredicates','expected one System.Type owner')
    for role,(name,slot) in _PREDICATES.items():
        row=rows[role]
        _expect((row.get('type'),row.get('method'),row.get('slot'),row.get('returnTypeName'),row.get('parameterTypes'),row.get('static'),row.get('generic'))
                ==('System.Type',name,slot,'bool',[],False,False) and row.get('static') is False and row.get('generic') is False,
                role,'predicate declaration differs')
        methods=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==name and m.slot==slot and m.parameter_count==0]
        _expect(len(methods)==1,role,'expected one named Type implementation slot')
        m=methods[0]
        _expect(m.token==_number(row['token']) and m.flags&0x40 and not m.flags&0x10 and m.generic_container_index==-1
                and _type(image,m.return_type,role+'.return')=='bool',role,'predicate raw return/static/generic identity differs')


def validate_object_conversion_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    """Authenticate after a caller's explicit selected native-input gate."""
    _claims(spec);targets={};method_rows={}
    for role in _METHODS:
        row=_ref(contract,_METHOD_REFS[role]) if role in _METHOD_REFS else spec['methods'][role]
        targets[role]=_identity(image,row,role,extents);method_rows[role]=row
    for role in _HELPERS|set(_HELPER_REFS):
        row=_ref(contract,_HELPER_REFS[role]) if role in _HELPER_REFS else spec['helpers'][role]
        count=row['byteCount'];_expect(type(count) is int and 0<count<=1024,role,'unsupported helper window')
        raw=image.pe.bytes_at_va(image.pe.image_base+_number(row['rva']),count);_hash(raw,row,'helpers.'+role)
        targets[role]=_number(row['rva'])
    # TypePredicate's full dispatch outcomes remain runtime-dependent; its
    # selected slot operands are checked against exact non-byref metadata.
    _predicates(image,spec['typePredicates'])
    value=_ref(contract,spec['valueLayoutRef']);layouts=contract['referenceUpdateRules']['fieldLayouts']
    reference_rules._layouts(image,layouts,value)
    _expect({r['type']:{n:f['offset'] for n,f in r['fields'].items()} for r in layouts}==
            {'IFix.Core.VirtualMachine':{'fieldInfos':88,'newFieldInfos':96,'staticFields':128},
             'IFix.Core.FieldAddr':{'Object':16,'FieldIdList':24}},'fields','selected conversion field offsets differ')
    clone=spec['objectCloneField'];md=image.metadata
    _expect(clone==dict(type='IFix.Core.VirtualMachine',field='objectClone',fieldType='IFix.Core.ObjectClone',offset=16),'objectClone','unsupported field declaration')
    owner=next(t for t in md.types if md.type_full_name(t)==clone['type'])
    definitions=[f for f in md.fields_for(owner) if md.string(f.name_index)==clone['field']]
    _expect(len(definitions)==1 and _type(image,definitions[0].type_index,'objectClone')==clone['fieldType']
            and runtime_type_field_offsets(md,image.pe,image.registration,owner.index).get('objectClone')==clone['offset'],
            'objectClone','non-byref named field/layout differs')
    actual={r['name']:r['id'] for r in enum_members(md,field_defaults(md),'IFix.Core.ValueType')}
    _expect(actual==_TAGS,'tags','complete ValueType enum differs')
    required_cells={t[2] for p in _PROGRAMS.values() for t in p if not isinstance(t,str) and t[0]=='rip'}
    _expect(set(spec['usageCells'])==required_cells-set(_USAGE_REFS),'cells','missing/unsupported usage role')
    cells={name:_cell(image,name,row) for name,row in spec['usageCells'].items()}
    for name,path in _USAGE_REFS.items():
        row=_ref(contract,path);definition=reference_rules._usage(image,row)
        if name=='instanceDictionary':reference_rules._dictionary_target(image,definition,targets['dictionaryItem'])
        cells[name]=_number(row['cellRva'])
    for name,role in [('ToObject','toObject'),('PushObject','pushObject'),('UnboxPrimitive','unboxPrimitive')]:
        row=method_rows[role]
        _expect('bodyBytes' in row,name,'complete conversion body is required')
        raw=image.pe.bytes_at_va(image.pe.image_base+targets[role],row['bodyBytes'])
        expected=_body(targets[role],name,targets,cells)
        if raw!=expected:
            offset=next((i for i,pair in enumerate(zip(raw,expected)) if pair[0]!=pair[1]),min(len(raw),len(expected)))
            _fail(name,f'finite program differs offset={offset:#x} expectedBytes={len(expected)} actualBytes={len(raw)}')
    return dict(status='validated_conditional_object_conversion_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
        completePrograms=list(_PROGRAMS),toObjectTagCount=len(_TO_OBJECT),unboxClassCount=len(_UNBOX),
        recursiveReferenceBoundary=spec['recursiveReferenceBoundary'],helperResultBoundary=spec['helperResultBoundary'],
        exceptionalFlowBoundary=spec['exceptionalFlowBoundary'],fileTableJoinBoundary=spec['fileTableJoinBoundary'],
        rules=project_object_conversion_rules(spec))


def project_object_conversion_rules(spec: dict) -> list[dict]:
    """Project static conditional programs only after successful validation."""
    _claims(spec)
    return [dict(method='ToObject',tag=name,tagId=_TAGS[name],effect=effect,evidenceBoundary='conditional',
                 executionBoundary='unobserved') for name,effect in _TO_OBJECT.items()]


def validate_selected_object_conversion_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    """Fail closed on explicit missing/mismatched selected native inputs."""
    if gameassembly is None or metadata is None:
        return dict(status='missing',detail='object-conversion requires explicit GameAssembly.dll and global-metadata.dat paths',rules=[])
    inputs=contract['nativeInputs']
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],
                                       gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail,rules=[])
    try:
        image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.objectConversion')
        return validate_object_conversion_rules(image,spec if spec is not None else contract['objectConversionRules'],contract,
                                                image.mapper.pdata_function_extents(image.pe))
    except (ValueError,RuntimeError,OSError,KeyError,StopIteration) as error:
        return dict(status='validation_failed',detail=str(error),rules=[])

_PROGRAMS = {'ToObject': ('48895c24084c894c242056574154415641574883ec60498bf1498bd84c8bf24c8be14c8bbc24b000000033ff',
              ('rip', '40383d', 'ToObjectInitRead', ''),
              '0f85ab010000',
              ('rip', '488d0d', 'anonymousType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_bool', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_bool', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_byte', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_byte', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_char', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_char', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'instanceDictionary', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_double', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_double', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_System_Enum', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'exceptionMethodA', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'chainType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_short', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_short', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_int', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_int', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_long', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_long', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_nint', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_nint', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'arrayType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_sbyte', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_sbyte', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_float', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_float', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_System_Type', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_ushort', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_ushort', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_uint', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_uint', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_ulong', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_ulong', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'handle_nuint', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'class_nuint', ''),
              ('call', 'typeInitialize'),
              ('rip', 'c605', 'ToObjectInitRead', '01'),
              '4d85f60f8410090000418b0e83f9050f8f730500000f849404000085c90f845002000083e9010f84e500000083e9010f849300000083e901744583f9010f85dc08000048897c24308a8424b8000000884424284c897c24204c8bce4c8bc3498b5604498bcc',
              ('call', 'toObject'),
              '488b9c24900000004883c460415f415e415c5f5ec3',
              ('rip', '488b1d', 'handle_double', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f8514030000f2410f104604f20f11842498000000488d942498000000',
              ('rip', '488b0d', 'class_double', ''),
              'e9dd030000',
              ('rip', '488b1d', 'handle_float', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f85cb020000f3410f104604f30f11842498000000488d942498000000',
              ('rip', '488b0d', 'class_float', ''),
              'e9940300004d8b7604',
              ('rip', '488b1d', 'handle_long', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f841c010000',
              ('rip', '488b1d', 'handle_ulong', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f84da000000',
              ('rip', '488b1d', 'handle_nint', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f8498000000',
              ('rip', '488b1d', 'handle_nuint', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf0743d4885f60f8467070000b95b000000488bd6',
              ('call', 'typePredicate'),
              '84c00f84f2010000',
              ('rip', '488b0d', 'class_System_Enum', ''),
              ('call', 'classInitialize'),
              '4533c0498bd6488bce',
              ('call', 'enumLong'),
              'e984feffff4889bc24980000004533c0498bd6488d8c2498000000',
              ('call', 'uintPtrCtor'),
              '488b8424980000004889442440488d542440',
              ('rip', '488b0d', 'class_nuint', ''),
              'e9860200004c89b42498000000488d942498000000',
              ('rip', '488b0d', 'class_nint', ''),
              'e96a0200004c89b42498000000488d942498000000',
              ('rip', '488b0d', 'class_ulong', ''),
              'e94e0200004c89b42498000000488d942498000000',
              ('rip', '488b0d', 'class_long', ''),
              'e932020000458b7604',
              ('rip', '488b1d', 'handle_int', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f84f1010000',
              ('rip', '488b1d', 'handle_bool', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f84ae010000',
              ('rip', '488b1d', 'handle_sbyte', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f846f010000',
              ('rip', '488b1d', 'handle_byte', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f8430010000',
              ('rip', '488b1d', 'handle_char', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f84f0000000',
              ('rip', '488b1d', 'handle_short', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf00f84ad000000',
              ('rip', '488b1d', 'handle_ushort', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf0746e',
              ('rip', '488b1d', 'handle_uint', ''),
              ('rip', '488b0d', 'class_System_Type', ''),
              ('call', 'classInitialize'),
              '33d2488bcb',
              ('call', 'getTypeFromHandle'),
              '483bf074404885f60f8471050000b95b000000488bd6',
              ('call', 'typePredicate'),
              '84c0750733c0e9aafcffff',
              ('rip', '488b0d', 'class_System_Enum', ''),
              ('call', 'classInitialize'),
              '4533c0418bd6488bce',
              ('call', 'enumInt'),
              'e98bfcffff',
              ('rip', '488b0d', 'class_uint', ''),
              'e9aa000000664489b42498000000488d942498000000',
              ('rip', '488b0d', 'class_ushort', ''),
              'e99d000000664489b42498000000488d942498000000',
              ('rip', '488b0d', 'class_short', ''),
              'e980000000664489b42498000000488d942498000000',
              ('rip', '488b0d', 'class_char', ''),
              'eb664488b42498000000488d942498000000',
              ('rip', '488b0d', 'class_byte', ''),
              'eb4d4488b42498000000488d942498000000',
              ('rip', '488b0d', 'class_sbyte', ''),
              'eb344183fe010f94842498000000488d942498000000',
              ('rip', '488b0d', 'class_bool', ''),
              'eb17',
              ('rip', '488b0d', 'class_int', ''),
              '488d9424980000004489b42498000000',
              ('call', 'boxRequest'),
              'e9bbfbffff49635e044d85ff0f845d04000085db7928498b8f800000004885c90f8449040000f7d33b59180f83d70400004863c3488b44c120e982fbffff498b4f584885c90f84240400003b59180f83b4040000488b74d9204533c033d2488bce',
              ('call', 'fieldEqual'),
              '84c075114885f60f84fc0300004533c0e9e5020000498b4f604885c90f84e7030000',
              ('rip', '4c8b05', 'instanceDictionary', ''),
              '8bd3',
              ('call', 'dictionaryItem'),
              '4885c00f84d00300004533c94533c0498bd7488bc8',
              ('call', 'checkInit'),
              '498b4f604885c90f84b2030000',
              ('rip', '4c8b05', 'instanceDictionary', ''),
              '8bd3',
              ('call', 'dictionaryItem'),
              '4885c00f849b0300004533c033d2e9f702000083e9060f84b001000083e9010f84a701000083e9010f84c500000083e901744d83f9010f856e0300004885db0f845f030000496346043b43180f83eb030000',
              ('rip', '488b15', 'arrayType', ''),
              '488b4cc320',
              ('call', 'typeTest'),
              '4885c00f84380300004533c0418b5608488bc8',
              ('call', 'arrayGet'),
              'e975faffff4038bc24b800000074494885db0f8411030000496346043b43180f839d03000048397cc320742c4d85ff0f84f4020000498b4f10496346044885c90f84e30200004533c0488b54c320',
              ('call', 'clone'),
              'e922faffff4885db0f84c8020000496346043b43180f8354030000488b44c320e902faffff496346044885db0f84a40200003b43180f8334030000488b5cc32048895c24404885f60f8488020000b92d000000488bd6',
              ('call', 'typePredicate'),
              '84c00f84930000004885db0f848a0000004889bc2498000000',
              ('rip', '488b15', 'class_nint', ''),
              '4839137453',
              ('rip', '488b15', 'class_nuint', ''),
              '483913742e33d2488bcb',
              ('call', 'pointerUnbox'),
              '4c8bf04889842498000000eb3b488bb424a8000000488b5c24404c8bb42498000000eb24488bcb',
              ('call', 'unboxAddress'),
              '4c8b30',
              ('rip', '488b0d', 'class_nuint', ''),
              ('call', 'classInitialize'),
              'eb0b488bcb',
              ('call', 'unboxAddress'),
              '4c8b304d85f674134533c0488bd6498bce',
              ('call', 'pointerBox'),
              'e931f9ffff488bc3e929f9ffff41833e070f844101000041397e087d594885db0f84bf010000496346043b43180f834b020000',
              ('rip', '488b15', 'anonymousType', ''),
              '488b4cc320',
              ('call', 'typeTest'),
              '4885c00f8498010000418b5608f7d248897c24288a8c24b8000000884c24204d8bcf4c8bc6488bc8',
              ('call', 'storeyGet'),
              'e9c0f8ffff4d85ff0f8466010000498b4f584885c90f8459010000496346083b41180f83e5010000488b74c1204885db0f843e010000496346043b43180f83ca010000488b5cc3204533c033d2488bce',
              ('call', 'fieldEqual'),
              '84c0751e4885f60f84120100004c8bc3b91b000000488bd6',
              ('call', 'fieldGetDispatch'),
              'e94ef8ffff498b4f604885c90f84f0000000',
              ('rip', '4c8b05', 'instanceDictionary', ''),
              '418b5608',
              ('call', 'dictionaryItem'),
              '4885c00f84d70000004533c94c8bc3498bd7488bc8',
              ('call', 'checkInit'),
              '498b4f604885c90f84b9000000',
              ('rip', '4c8b05', 'instanceDictionary', ''),
              '418b5608',
              ('call', 'dictionaryItem'),
              '4885c00f84a00000004533c0488bd3488bc8',
              ('call', 'newFieldGet'),
              'e9def7ffff4885db0f8484000000498bce492bcc48b8abaaaaaaaaaaaa2a48f7e9488bca48d1f9488bc148c1e83f4803c83b4b180f83f1000000',
              ('rip', '488b15', 'chainType', ''),
              '488b4ccb20',
              ('call', 'typeTest'),
              '4885c074424c8b48184d85c974394d85ff7434498b57584d8b5760458b411841ffc841837e08ff0f95c148897c24304c895424284889542420488b5010',
              ('call', 'chainGet'),
              'e951f7ffff',
              ('call', 'nullStop'),
              'cc498bce',
              ('call', 'nonnull'),
              '418b0689842498000000',
              ('rip', '488d0d', 'class_IFix_Core_ValueType', ''),
              ('call', 'usageResolveThunk'),
              '488bc8488d942498000000',
              ('call', 'enumBoxThunk'),
              '488bd8',
              ('rip', '488d0d', 'unsupportedTagLiteral', ''),
              ('call', 'usageResolveThunk'),
              '488bc84533c0488bd3',
              ('call', 'concatPair'),
              '488bd8',
              ('rip', '488d0d', 'class_System_NotImplementedException', ''),
              ('call', 'usageResolveThunk'),
              '488bc8',
              ('call', 'allocationThunk'),
              '488bf8488bc8',
              ('call', 'nonnull'),
              '4533c0488bd3488bcf',
              ('call', 'unsupportedCtor'),
              ('rip', '488d0d', 'exceptionMethodA', ''),
              ('call', 'usageResolveThunk'),
              '488bd0488bcf',
              ('call', 'throwStop'),
              'cc',
              ('call', 'boundsStop'),
              'cc'),
 'PushObject': ('488bc44c8948204c89401848895010488948085356574154415641574883ec48498bf94d8bf8488bf24c8be1',
                ('rip', '803d', 'PushObjectInitRead', '00'),
                '755b',
                ('rip', '488d0d', 'class_System_Convert', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'class_System_Enum', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'handle_long', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'class_nint', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'class_System_Type', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'handle_ulong', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'class_nuint', ''),
                ('call', 'typeInitialize'),
                ('rip', 'c605', 'PushObjectInitRead', '01'),
                '488b9c24a00000004885ff0f84e30000004885db0f845f020000b95f000000488bd3',
                ('call', 'typePredicate'),
                '84c00f8534020000b95b000000488bd3',
                ('call', 'typePredicate'),
                '84c00f853b010000b92d000000488bd3',
                ('call', 'typePredicate'),
                '84c00f849b000000488364242000',
                ('rip', '488b15', 'class_nint', ''),
                '4839177468',
                ('rip', '488b15', 'class_nuint', ''),
                '483917744333d2488bcf',
                ('call', 'pointerUnbox'),
                '4c8bf04889442420eb53488b9c24a0000000488bbc24980000004c8bbc2490000000488bb424880000004c8ba424800000004c8b742420eb24488bcf',
                ('call', 'unboxAddress'),
                '4c8b30',
                ('rip', '488b0d', 'class_nuint', ''),
                ('call', 'classInitialize'),
                'eb0b488bcf',
                ('call', 'unboxAddress'),
                '4c8b304d85f674114533c0488bd3498bce',
                ('call', 'pointerBox'),
                '488bf8488bce492bcc48b8abaaaaaaaaaaaa2a48f7e94c8bf249d1fe498bc648c1e83f4c03f04885f60f8459010000448976044d85ff0f844c010000488bd7498bcf',
                ('call', 'assignmentCheck'),
                '4963d64c8bc7498bcf',
                ('call', 'managedStore'),
                '4885ff741f4885db0f8425010000b961000000488bd3',
                ('call', 'typePredicate'),
                '84c0b8090000007505b80800000089064883c448415f415e415c5f5e5bc3',
                ('rip', '488b0d', 'class_System_Enum', ''),
                ('call', 'classInitialize'),
                '33d2488bcb',
                ('call', 'enumUnderlying'),
                '4c8bf0',
                ('rip', '488b1d', 'handle_long', ''),
                ('rip', '488b0d', 'class_System_Type', ''),
                ('call', 'classInitialize'),
                '33d2488bcb',
                ('call', 'getTypeFromHandle'),
                '4c3bf0744c',
                ('rip', '488b1d', 'handle_ulong', ''),
                ('rip', '488b0d', 'class_System_Type', ''),
                ('call', 'classInitialize'),
                '33d2488bcb',
                ('call', 'getTypeFromHandle'),
                '4c3bf0742a4885f60f8494000000832600',
                ('rip', '488b0d', 'class_System_Convert', ''),
                ('call', 'classInitialize'),
                '33d2488bcf',
                ('call', 'toInt32'),
                '894604e96bffffff4885f6746ec70601000000',
                ('rip', '488b1d', 'handle_long', ''),
                ('rip', '488b0d', 'class_System_Type', ''),
                ('call', 'classInitialize'),
                '33d2488bcb',
                ('call', 'getTypeFromHandle'),
                ('rip', '488b0d', 'class_System_Convert', ''),
                '4c3bf07411',
                ('call', 'classInitialize'),
                '33d2488bcf',
                ('call', 'toUInt64'),
                'eb0f',
                ('call', 'classInitialize'),
                '33d2488bcf',
                ('call', 'toInt64'),
                '48894604e90effffff4533c94c8bc3488bd7488bce',
                ('call', 'unboxPrimitive'),
                'e9f8feffff',
                ('call', 'nullStop'),
                'cc'),
 'UnboxPrimitive': ('488bc44889580848896810488970184889782041564883ec2033f6498be8',
                    ('rip', '403835', 'UnboxPrimitiveInitRead', ''),
                    '488bda488bf9448d76010f85bb000000',
                    ('rip', '488d0d', 'class_bool', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_byte', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_char', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_System_Convert', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_double', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_short', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_int', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_long', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_nint', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_sbyte', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_float', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_ushort', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_uint', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_ulong', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '488d0d', 'class_nuint', ''),
                    ('call', 'typeInitialize'),
                    ('rip', '448835', 'UnboxPrimitiveInitRead', ''),
                    '4885db0f84d403000033d2488bcb',
                    ('call', 'objectGetType'),
                    '4885c00f84c1030000b95b000000488bd0',
                    ('call', 'typePredicate'),
                    '84c07426',
                    ('rip', '488b0d', 'class_System_Convert', ''),
                    ('call', 'classInitialize'),
                    '4533c0488bd5488bcb',
                    ('call', 'changeType'),
                    '488bd84885c00f842a020000',
                    ('rip', '488b05', 'class_int', ''),
                    '488bcb4839030f84640300004885db0f840e020000',
                    ('rip', '488b05', 'class_float', ''),
                    '483903753b4885ff0f8459030000c70702000000',
                    ('rip', '488b15', 'class_float', ''),
                    ('call', 'unboxAddress'),
                    '8b08894f04488b5c2430488b6c2438488b742440488b7c24484883c420415ec3',
                    ('rip', '488b05', 'class_bool', ''),
                    '48390375234885ff0f84120300008937',
                    ('rip', '488b15', 'class_bool', ''),
                    ('call', 'unboxAddress'),
                    '403830400f95c6897704ebb6',
                    ('rip', '488b05', 'class_double', ''),
                    '48390375244885ff0f84e3020000c70703000000',
                    ('rip', '488b15', 'class_double', ''),
                    ('call', 'unboxAddress'),
                    '488b0848894f04eb86',
                    ('rip', '488b05', 'class_long', ''),
                    '48390375154885ff0f84b3020000448937',
                    ('rip', '488b15', 'class_long', ''),
                    'ebd1',
                    ('rip', '488b05', 'class_byte', ''),
                    '483903751f4885ff0f84920200008937',
                    ('rip', '488b15', 'class_byte', ''),
                    ('call', 'unboxAddress'),
                    '0fb608e937ffffff',
                    ('rip', '488b05', 'class_uint', ''),
                    '48390375174885ff0f84670200008937',
                    ('rip', '488b15', 'class_uint', ''),
                    'e90dffffff',
                    ('rip', '488b05', 'class_ushort', ''),
                    '483903751f4885ff0f84440200008937',
                    ('rip', '488b15', 'class_ushort', ''),
                    ('call', 'unboxAddress'),
                    '0fb708e9e9feffff',
                    ('rip', '488b05', 'class_short', ''),
                    '483903751f4885ff0f84190200008937',
                    ('rip', '488b15', 'class_short', ''),
                    ('call', 'unboxAddress'),
                    '0fbf08e9befeffff',
                    ('rip', '488b05', 'class_char', ''),
                    '48390375144885ff0f84ee0100008937',
                    ('rip', '488b15', 'class_char', ''),
                    'eba8',
                    ('rip', '488b05', 'class_ulong', ''),
                    '48390375184885ff0f84ce010000448937',
                    ('rip', '488b15', 'class_ulong', ''),
                    'e9e9feffff',
                    ('rip', '488b05', 'class_sbyte', ''),
                    '483903751f4885ff0f84aa0100008937',
                    ('rip', '488b15', 'class_sbyte', ''),
                    ('call', 'unboxAddress'),
                    '0fbe08e94ffeffff',
                    ('rip', '488b05', 'class_nint', ''),
                    '48390375184885ff0f847f010000448937',
                    ('rip', '488b15', 'class_nint', ''),
                    'e99afeffff',
                    ('rip', '488b05', 'class_nuint', ''),
                    '4839030f8421010000',
                    ('rip', '488d0d', 'class_objectArray', ''),
                    ('call', 'usageResolveThunk'),
                    'ba04000000488bc8',
                    ('call', 'arrayAllocate'),
                    '488bf84885c00f843b010000',
                    ('rip', '488d0d', 'unsupportedObjectLiteral', ''),
                    ('call', 'usageResolveThunk'),
                    '488bd0488bcf',
                    ('call', 'assignmentCheck'),
                    ('rip', '488d0d', 'unsupportedObjectLiteral', ''),
                    ('call', 'usageResolveThunk'),
                    '4c8bc033d2488bcf',
                    ('call', 'managedStore'),
                    '4885db0f840201000033d2488bcb',
                    ('call', 'objectGetType'),
                    '488bd0488bcf488bd8',
                    ('call', 'assignmentCheck'),
                    '4c8bc3498bd6488bcf',
                    ('call', 'managedStore'),
                    ('rip', '488d0d', 'unsupportedPrimitiveLiteral', ''),
                    ('call', 'usageResolveThunk'),
                    '488bd0488bcf',
                    ('call', 'assignmentCheck'),
                    ('rip', '488d0d', 'unsupportedPrimitiveLiteral', ''),
                    ('call', 'usageResolveThunk'),
                    '4c8bc0ba02000000488bcf',
                    ('call', 'managedStore'),
                    '488bd5488bcf',
                    ('call', 'assignmentCheck'),
                    '4c8bc5ba03000000488bcf',
                    ('call', 'managedStore'),
                    '33d2488bcf',
                    ('call', 'concatArray'),
                    ('rip', '488d0d', 'class_System_NotImplementedException', ''),
                    '488bf8',
                    ('call', 'usageResolveThunk'),
                    '488bc8',
                    ('call', 'opaqueObject'),
                    '488bd84885c074654533c0488bd7488bc8',
                    ('call', 'unsupportedCtor'),
                    ('rip', '488d0d', 'exceptionMethodB', ''),
                    ('call', 'usageResolveThunk'),
                    '488bd0488bcb',
                    ('call', 'throwStop'),
                    'cc4885ff743a448937',
                    ('rip', '488b15', 'class_nuint', ''),
                    ('call', 'unboxAddress'),
                    ('rip', '488b0d', 'class_nuint', ''),
                    '488b18',
                    ('call', 'classInitialize'),
                    '48895f04e9d1fcffff4885ff740e8937',
                    ('rip', '488b15', 'class_int', ''),
                    'e9b4fcffff',
                    ('call', 'nullPrimitive'),
                    'cc')}
