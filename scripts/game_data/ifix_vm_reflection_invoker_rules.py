"""Complete selected ReflectionMethodInvoker.Invoke caller recipe.

This proves authored native requests, local branch/loop programs and captured
frame addresses. Framework reflection, conversions, Call.UpdateReference's
thread-stack join, cleanup callback effects and native EH entry remain opaque.
The Call parameter is authenticated as a byref value type with unboxed fields.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
from scripts.game_data.il2cpp.protocol import runtime_type_name,runtime_type_field_offsets
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity,_type


class ReflectionInvokerRuleError(ValueError):
    """A selected reflection caller claim lacks its finite witness."""


def _need(ok: bool,detail: str) -> None:
    if not ok:raise ReflectionInvokerRuleError('reflection-invoker.'+detail)


_METHOD_REF='reflectionDispatch.methods.reflectionInvoke'
_FIELD_REF='reflectionInvokerConstructorRules.fieldLayout'
_HELPER_REFS={
 'nullCheck':'negativeFieldRules.helpers.nullCheck','classInitialize':'objectConversionRules.helpers.classInitialize',
 'classPrepare':'chainFieldRules.helpers.classPrepare','returnQuery':'genericDelegateFactoryRules.helpers.returnQueryHelper',
 'boundsStop':'objectConversionRules.helpers.boundsStop','throwStop':'objectConversionRules.helpers.throwStop',
 'exceptionPropagate':'newFieldRules.helpers.exceptionPropagate','arrayAllocate':'objectConversionRules.helpers.arrayAllocate',
 'boxRequest':'objectConversionRules.helpers.boxRequest','allocateObject':'objectConversionRules.helpers.allocationThunk',
 'nameQuery':'virtualDispatchRules.helpers.nameInvoke','managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
 'assignmentCheck':'functionPointerRules.helpers.assignmentCheck','typeInitialize':'referenceUpdateRules.helpers.typeInitialize',
 'unboxAddress':'objectConversionRules.helpers.unboxAddress','usageResolve':'objectConversionRules.helpers.usageResolveThunk',
 'nullStop':'objectConversionRules.helpers.nullStop'}
_METHOD_REFS={
 'isConstructor':'reflectionDispatch.methods.isConstructor','isStatic':'reflectionDispatch.methods.isStatic',
 'pushResult':'reflectionDispatch.methods.pushResult','toObject':'constrainedTypeOperand.stackEffect.toObjectMethod',
 'pointerBox':'objectConversionRules.methods.pointerBox','pointerUnbox':'objectConversionRules.methods.pointerUnbox'}
_METHODS={
 'isConstructor':('System.Reflection.MethodBase','get_IsConstructor',[],'bool',False),
 'isStatic':('System.Reflection.MethodBase','get_IsStatic',[],'bool',False),
 'pushResult':('IFix.Core.Call','PushObjectAsResult',['object','System.Type'],'void',False),
 'toObject':('IFix.Core.EvaluationStackOperation','ToObject',['IFix.Core.Value*','IFix.Core.Value*','object[]','System.Type','IFix.Core.VirtualMachine','bool'],'object',True),
 'pointerBox':('System.Reflection.Pointer','Box',['void*','System.Type'],'object',True),
 'pointerUnbox':('System.Reflection.Pointer','Unbox',['object'],'void*',True),
 'updateReference':('IFix.Core.Call','UpdateReference',['int','object','IFix.Core.VirtualMachine','System.Type'],'void',False),
 'stringFormat':('System.String','Format',['string','object','object'],'string',True),
 'targetExceptionCtor':('System.Reflection.TargetException','.ctor',['string'],'void',False),
 'innerException':('System.Exception','get_InnerException',[],'System.Exception',False)}
_VIRTUAL_REFS={'declaringType':'referenceAddressRules.virtualMethods.declaringType','name':'virtualDispatchRules.virtualMethods.name'}
_VIRTUALS={
 'declaringType':('System.Reflection.MemberInfo','get_DeclaringType',[],'System.Type',False,9),
 'name':('System.Reflection.MemberInfo','get_Name',[],'string',False,8),
 'isPointer':('System.Type','IsPointerImpl',[],'bool',False,45),
 'isValueType':('System.Type','IsValueTypeImpl',[],'bool',False,97),
 'methodInvoke':('System.Reflection.MethodBase','Invoke',['object','System.Reflection.BindingFlags','System.Reflection.Binder','object[]','System.Globalization.CultureInfo'],'object',False,34),
 'ctorInvoke':('System.Reflection.ConstructorInfo','Invoke',['System.Reflection.BindingFlags','System.Reflection.Binder','object[]','System.Globalization.CultureInfo'],'object',False,42)}
_CELL_REFS={
 'boolType':'objectConversionRules.usageCells.class_bool','intPtrType':'objectConversionRules.usageCells.class_nint',
 'uintPtrType':'objectConversionRules.usageCells.class_nuint','objectArray':'objectConversionRules.usageCells.class_objectArray',
 'marshalType':'objectOpcodeRules.usageCells.cell01','invokeContext':'callOpcodeRules.usageCells.reflectionMethod'}
_CELLS={'boolType':(1,'bool',2),'intPtrType':(1,'nint',0x18),'uintPtrType':(1,'nuint',0x19),
 'objectArray':(1,'object[]',0x1d),'marshalType':(1,'System.Runtime.InteropServices.Marshal',0x12),
 'invokeContext':(3,'IFix.Core.ReflectionMethodInvoker.Invoke',None),
 'targetExceptionType':(1,'System.Reflection.TargetException',0x12),
 'nullInstanceLiteral':(5,'can not invoke method [{0}.{1}], Non-static method require instance but got null.',None)}
_OWN_HELPERS={'methodInvoke','ctorInvoke','structureFromPointer','cleanupNormal','cleanupCaptured','contextPop','contextRead'}
_INVOKER_FIELDS={'paramCount':('int',8),'hasThis':('bool',2),'hasReturn':('bool',2),'refFlags':('bool[]',0x1d),
 'outFlags':('bool[]',0x1d),'rawTypes':('System.Type[]',0x1d),'method':('System.Reflection.MethodBase',0x12),
 'ctor':('System.Reflection.ConstructorInfo',0x12),'returnType':('System.Type',0x12),
 'isNullableHasValue':('bool',2),'isNullableValue':('bool',2)}
_CALL_FIELDS={'argumentBase':('IFix.Core.Value*',0x0f),'evaluationStackBase':('IFix.Core.Value*',0x0f),
 'managedStack':('object[]',0x1d),'currentTop':('IFix.Core.Value*',0x0f),'topWriteBack':('IFix.Core.Value**',0x0f)}
_BOUNDS={
 'schema':'endfield.ifix-vm-reflection-invoker-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'methodRef':_METHOD_REF,'fieldLayoutRef':_FIELD_REF,'callBoxedHeaderBytes':16,'slotBytes':12,
 'callBoundary':'raw-byref-Call-value-type-parameter;boxed-field-offsets-minus16-are-native-payload-offsets;storage-validity-unobserved',
 'reflectionBoundary':'selected-typed-virtual-and-direct-request-callers;framework-results-dispatch-sharing-and-invocation-unobserved',
 'writebackBoundary':'Call.UpdateReference-named-body-request-only;current-thread-stack-versus-Call-saved-evaluation-base-identity-and-mutations-unobserved',
 'cleanupBoundary':'captured-frame-addresses-and-normal-or-resumed-cleanup-requests-only;callback-effects-EH-entry-and-frame-validity-unobserved',
 'loopBoundary':'signed-Int32-parameter-and-reference-counters;wrap-termination-capacity-and-helper-mutation-unobserved',
 'aliasBoundary':'reference-type-object-identities-stack-overlap-and-helper-mutated-local-or-managed-storage-unobserved',
 'stopBoundary':'canonical-stop-requests;native-EH-delivery-and-failure-route-abnormal-transfer-unobserved'}
_RULES={
 'setup':'save-inputs;conditional-metadata-initialize-six-cells;request-object-array-of-paramCount;capture21-native-local-home-addresses-and-copy168-bytes-after-cleanup-frame-prefix-qword',
 'receiverSkip':'if-hasThis-byte-nonzero-and-isInstantiate-byte-zero:parameter-slot=Call.argumentBase+12,receiverSkip=1;otherwise-argumentBase,skip0',
 'parameterLoop':'signed-Int32-i-from0-while-i<paramCount;outFlags[i]!=0-skips-conversion-and-array-store;each-normal-step-slot-plus12-and-i-plus1',
 'parameterObject':'ToObject(Call.evaluationStackBase,parameterSlot,saved-managedStack,rawTypes[i],VM,true);assignmentCheck-and-managedStore(argumentArray,signed-i,result)',
 'pointerParameter':'if-rawTypes[i]-IsPointerImpl-slot45-query-AL!=0-and-argumentArray[i]!=null:exact-class-intPtr-or-uintPtr->unboxAddress-qword-read;otherwise-Pointer.Unbox-request;box-as-intPtr-and-replace-array-entry',
 'receiver':'when-hasThis:ToObject(Call.evaluationStackBase,Call.argumentBase,saved-managedStack,DeclaringType-slot9-query,VM,false);value-type-query-slot97-may-request-pointer-structure-conversion-and-save-original-pointer',
 'invocation':'isInstantiate-or-value-type-constructor-request:ctor-helper-slot42(flags512,null-binder,argumentArray,null-culture);ordinary-method-helper-slot34(target,flags0,null-binder,argumentArray,null-culture);nullableHasValue-boxes-receiver-nonnull;nullableValue-skips-invocation-and-retains-receiver',
 'nullInstance':'ordinary-method-IsStatic-query-AL==0-and-target-null:DeclaringType/name-query-requests;String.Format-stored-literal;TargetException-constructor;throwStop-with-resolved-stored-Invoke-context',
 'referenceLoop':'signed-Int32-i-from0-while-i<paramCount;if-refFlags[i]!=0:Call.UpdateReference(Int32(i+receiverSkip),argumentArray[i],VM,rawTypes[i]);then-i-plus1',
 'result':'if-hasReturn-or-isInstantiate:constructor-and-declaring-type-IsValueTypeImpl-query-AL!=0-and-isInstantiate-zero->Call.UpdateReference(0,result,VM,DeclaringType);otherwise-PushObjectAsResult(result,returnType)-then-store-resultPushed-byte1',
 'cleanup':'request-cleanupNormal(&local-frame);resumed-local-cleanup-request-is-not-proved-EH-entry;normalReturn-RET-after-cleanup-request;failure-requests-and-stored-exception-read/stop-paths-remain-conditional'}


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _BOUNDS.items())and spec.get('helperRefs')==_HELPER_REFS
      and spec.get('methodRefs')==_METHOD_REFS and spec.get('virtualRefs')==_VIRTUAL_REFS and spec.get('cellRefs')==_CELL_REFS
      and spec.get('rules')==_RULES,'unsupported schema/reference/conditional rules')
    _need(set(spec['methods'])==set(_METHODS)-set(_METHOD_REFS)and set(spec['helpers'])==_OWN_HELPERS
      and set(spec['virtualMethods'])==set(_VIRTUALS)-set(_VIRTUAL_REFS),'owned named/helper set differs')


def _raw_type(image: Any,index: int,kind: int,*,byref: bool=False,instance: bool=False) -> bytes:
    _need(type(index)is int and 0<=index<image.registration['typesCount'],'registered type index differs')
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8);raw=image.pe.bytes_at_va(pointer,16)
    _need(len(raw)==16 and raw[10]==kind and bool(raw[11]&0x20)==byref
      and(not instance or not int.from_bytes(raw[8:10],'little')&0x10),'raw type kind/byref/static carrier differs')
    return raw


def _carrier_at(image: Any,pointer: int,name: str,*,byref: bool=False,instance: bool=False,depth: int=0) -> bytes:
    """Check this caller's primitive/class/value/pointer/array carrier tree."""
    _need(depth<=4,'nested carrier depth differs')
    md=image.metadata;primitive={'void':1,'bool':2,'int':8,'string':0x0e,'nint':0x18,'nuint':0x19,'object':0x1c}
    child_name=name[:-2]if name.endswith('[]')else name[:-1]if name.endswith('*')else None
    if child_name is not None:kind=0x1d if name.endswith('[]')else 0x0f
    elif name in primitive:kind=primitive[name]
    else:
        owners=[t for t in md.types if md.type_full_name(t)==name]
        _need(len(owners)==1,'named carrier owner differs: '+name);kind=0x11 if owners[0].bitfield&1 else 0x12
    raw=image.pe.bytes_at_va(pointer,16)
    _need(len(raw)==16 and raw[10]==kind and bool(raw[11]&0x20)==byref
      and(not instance or not int.from_bytes(raw[8:10],'little')&0x10),'named raw kind/byref/static carrier differs: '+name)
    _need(runtime_type_name(image.pe,md,pointer)==name,'named carrier identity differs: '+name)
    if child_name is not None:
        _carrier_at(image,int.from_bytes(raw[:8],'little'),child_name,depth=depth+1)
    return raw


def _carrier(image: Any,index: int,name: str,*,byref: bool=False,instance: bool=False) -> bytes:
    _need(type(index)is int and 0<=index<image.registration['typesCount'],'registered carrier index differs')
    return _carrier_at(image,image.pe.u64_at_va(_rva(image.registration['types'])+index*8),name,byref=byref,instance=instance)


def _method_carriers(image: Any,row: dict,signature: tuple) -> None:
    md=image.metadata
    matches=[m for t in md.types if md.type_full_name(t)==signature[0]for m in md.methods_for(t)
      if m.token==_rva(row['token'])and md.string(m.name_index)==signature[1]]
    _need(len(matches)==1,'named method carrier token differs');method=matches[0];params=image.metadata.parameters_for(method)
    _need(len(params)==len(signature[2]),'named method carrier parameter count differs')
    for p,name in zip(params,signature[2]):_carrier(image,p.type_index,name)
    _carrier(image,method.return_type,signature[3])


def _invoke_identity(image: Any,contract: dict,extents: dict) -> tuple[int,bytes,int]:
    row=_ref(contract,_METHOD_REF);md=image.metadata;owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.ReflectionMethodInvoker']
    _need(len(owners)==1 and not owners[0].bitfield&1,'Invoke owner differs')
    matches=[m for m in md.methods_for(owners[0])if md.string(m.name_index)=='Invoke'and m.parameter_count==3]
    _need(len(matches)==1,'Invoke named overload differs');m=matches[0];params=md.parameters_for(m)
    _need(len(params)==3 and not m.flags&0x10 and m.generic_container_index==-1 and m.token==_rva(row['token'])
      and(row.get('type'),row.get('method'),row.get('parameterCount'))==('IFix.Core.ReflectionMethodInvoker','Invoke',3),'Invoke static/generic/token/declaration differs')
    expected=[('IFix.Core.VirtualMachine',0x12,False),('IFix.Core.Call',0x11,True),('bool',2,False)]
    for p,(name,kind,byref)in zip(params,expected):
        _raw_type(image,p.type_index,kind,byref=byref);_carrier(image,p.type_index,name,byref=byref)
    _raw_type(image,m.return_type,1);_need(_type(image,m.return_type)=='void','Invoke return differs')
    pointer=image.method_pointer_va(m);at=pointer-image.pe.image_base
    _need(at==_rva(row['rva'])and type(row.get('bodyBytes'))is int and extents.get(pointer)==pointer+row['bodyBytes'],'Invoke registered pointer/extent differs')
    raw=image.pe.bytes_at_va(pointer,row['bodyBytes']);_hash(raw,row,'reflection-invoker.Invoke',method=True);return at,raw,m.token


def _layouts(image: Any,spec: dict,contract: dict) -> dict:
    md=image.metadata;result={}
    for role,owner_name,fields,row in [('invoker','IFix.Core.ReflectionMethodInvoker',_INVOKER_FIELDS,_ref(contract,_FIELD_REF)),
        ('call','IFix.Core.Call',_CALL_FIELDS,spec['callFieldLayout'])]:
        owners=[t for t in md.types if md.type_full_name(t)==owner_name]
        _need(len(owners)==1 and row.get('type')==owner_name and set(row['fields'])==set(fields),'named field owner/set differs: '+role)
        owner=owners[0];_need(bool(owner.bitfield&1)==(role=='call'),'field owner class/value-kind differs')
        definitions={md.string(f.name_index):f for f in md.fields_for(owner)};offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index);result[role]={}
        for name,(typ,kind)in fields.items():
            r=row['fields'][name];f=definitions.get(name)
            _need(f is not None and r.get('type')==typ and _type(image,f.type_index)==typ,'field type differs: '+role+'.'+name)
            _raw_type(image,f.type_index,kind,instance=True);_carrier(image,f.type_index,typ,instance=True)
            offset=r['offset'];_need(type(offset)is int and offsets.get(name)==offset and 16<=offset<128,'field offset differs: '+role+'.'+name);result[role][name]=offset
        inherited=contract['reflectionDispatch']['fieldOffsets'][owner_name]
        _need(all(result[role].get(name)==offset for name,offset in inherited.items()),'inherited reflection layout differs: '+role)
    _need(result['call']==dict(argumentBase=16,evaluationStackBase=24,managedStack=32,currentTop=40,topWriteBack=48),'five-word Call payload layout differs')
    _need(result['invoker']==dict(paramCount=16,hasThis=20,hasReturn=21,refFlags=24,outFlags=32,rawTypes=40,method=48,ctor=56,returnType=64,isNullableHasValue=72,isNullableValue=73),'selected invoker field operand grammar differs')
    return {name:offset-16 for name,offset in result['call'].items()}


def _cells(image: Any,spec: dict,contract: dict,invoke_token: int) -> dict:
    rows={r['name']:r for r in spec['usageCells']};_need(len(rows)==len(spec['usageCells'])and set(rows)=={'targetExceptionType','nullInstanceLiteral'},'own usage cell set differs')
    rows.update({n:_ref(contract,path)for n,path in _CELL_REFS.items()});result={};md=image.metadata
    for name,(tag,identity,kind)in _CELLS.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        declared=bytes.fromhex(row['rawHex'])if 'rawHex'in row else _rva(row['encodedWord']).to_bytes(8,'little')
        _need(raw==declared and type(row.get('usageTag'))is int and row['usageTag']==tag,'stored usage bytes/tag differ: '+name)
        count=image.registration['typesCount']if tag==1 else len(md.methods)if tag==3 else md.sections['stringLiteral'].size//8
        index=unresolved_usage_index(raw,count,tag=tag,source='reflection-invoker.'+name,offset=at)
        if tag==1:_need(_type(image,index)==identity,'stored type identity differs: '+name);_raw_type(image,index,kind)
        elif tag==3:
            m=md.methods[index];_need(m.token==invoke_token and md.type_full_name(md.types[m.declaring_type])=='IFix.Core.ReflectionMethodInvoker'
              and md.string(m.name_index)=='Invoke'and image.method_pointer_va(m)==image.pe.image_base+_rva(_ref(contract,_METHOD_REF)['rva']),'stored Invoke MethodDef context differs')
        else:
            table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData'];position=table.offset+index*8
            start,count=literal_record(md.buf[position:position+8],pool.size,source='reflection-invoker.literal',offset=position)
            _need(md.buf[pool.offset+start:pool.offset+start+count]==identity.encode(),'stored null-instance literal differs')
        if name in rows and name not in _CELL_REFS:_need(row.get('identity')==identity,'owned usage identity differs')
        result[name]=at
    flag=spec['lazyFlag'];at=_rva(flag['rva']);section=flag['section']
    _need(type(flag.get('byteCount'))is int and flag['byteCount']==1 and flag.get('storage')=='unbacked-PE-virtual-tail-runtime-state-unobserved'
      and 'hex'not in flag and 'sha256'not in flag,'lazy runtime flag boundary differs')
    matches=[s for s in image.pe.sections if s['name']==section['name']and s['virtualAddress']<=at<s['virtualAddress']+s['virtualSize']]
    _need(len(matches)==1 and matches[0]==section and at>=section['virtualAddress']+section['rawSize'],'lazy flag is not selected unbacked virtual tail');result['lazyFlag']=at;return result


def _program(at: int,targets: dict,cells: dict) -> tuple[bytes,dict]:
    labels={};offset=0
    for token in _INVOKE_PROGRAM:
        if isinstance(token,str):offset+=len(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':_need(args[0]not in labels,'duplicate finite label');labels[args[0]]=at+offset
        elif kind=='call':offset+=5
        elif kind=='edge':offset+=len(bytes.fromhex(args[0]))+args[2]
        elif kind=='rip':offset+=len(bytes.fromhex(args[0]))+4+len(bytes.fromhex(args[2]))
        else:_need(False,'unknown finite token')
    out=bytearray()
    for token in _INVOKE_PROGRAM:
        if isinstance(token,str):out.extend(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':continue
        if kind=='call':prefix=b'\xe8';target=targets[args[0]];width=4;suffix=b''
        elif kind=='edge':prefix=bytes.fromhex(args[0]);target=labels[args[1]];width=args[2];suffix=b''
        else:prefix=bytes.fromhex(args[0]);target=cells[args[1]];width=4;suffix=bytes.fromhex(args[2])
        out.extend(prefix+(target-(at+len(out)+len(prefix)+width+len(suffix))).to_bytes(width,'little',signed=True)+suffix)
    _need(len(out)==offset,'finite caller extent differs');return bytes(out),labels


def _request_program(name: str,at: int,targets: dict,row: dict) -> bytes:
    """Finite typed request wrappers; constructor sharing outcomes stay opaque."""
    prepare=(targets['classPrepare']-(at+(41 if name=='methodInvoke'else 32))).to_bytes(4,'little',signed=True)
    if name=='methodInvoke':
        return bytes.fromhex('48895c2408488974241048897c241841564883ec400fb7d9418bf9488b0a498bf04c8bf2e8')+prepare+bytes.fromhex(
          '4c8b4c2470488d431448c1e004448bc7490306488bd6498bce4c8b10488b40084889442430488b8424800000004889442428488b442478488944242041ffd2488b5c2450488b742458488b7c24604883c440415ec3')
    routes=row['dispatchTargets'];_need(set(routes)=={'comparedCandidate','unequalRoute','equalRequest'}
      and row.get('dispatchBoundary')=='stored-slot42-pair;candidate-address-comparison-and-outside-request-only;runtime-sharing-unobserved','constructor request route boundary differs')
    return (bytes.fromhex('48895c24084889742410574883ec40488b0a498bf9418bf0488bdae8')+prepare
      +bytes.fromhex('488b034c8b90e0030000488b88e8030000488d05')
      +(_rva(routes['comparedCandidate'])-(at+56)).to_bytes(4,'little',signed=True)
      +bytes.fromhex('4c3bd0488b4424780f85')+(_rva(routes['unequalRoute'])-(at+70)).to_bytes(4,'little',signed=True)
      +bytes.fromhex('48c7442430000000004c8bcf4889442428448bc6488b44247033d2488bcb4889442420e8')
      +(_rva(routes['equalRequest'])-(at+110)).to_bytes(4,'little',signed=True)
      +bytes.fromhex('488b5c2450488b7424584883c4405fc3'))


def validate_reflection_invoker_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    """Authenticate full caller and metadata; no reflection or native execution."""
    _claims(spec);at,body,token=_invoke_identity(image,contract,extents);payload=_layouts(image,spec,contract);targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);where=_rva(row['rva']);count=row.get('byteCount',row.get('bodyBytes'));_need(type(count)is int and 0<count<=2048,'inherited helper width differs')
        _hash(image.pe.bytes_at_va(image.pe.image_base+where,count),row,'reflection-invoker.'+name,method='bodyBytes'in row);targets[name]=where
    for name,identity in _METHODS.items():
        row=_ref(contract,_METHOD_REFS[name])if name in _METHOD_REFS else spec['methods'][name]
        targets[name]=_identity(image,row,identity,'reflection-invoker.'+name,extents);_method_carriers(image,row,identity)
    for name,signature in _VIRTUALS.items():
        row=_ref(contract,_VIRTUAL_REFS[name])if name in _VIRTUAL_REFS else spec['virtualMethods'][name]
        _identity(image,row,signature[:5],'reflection-invoker.virtual.'+name,extents,virtual_slot=signature[5]);_method_carriers(image,row,signature)
    for name,row in spec['helpers'].items():
        where=_rva(row['rva']);count=row['byteCount'];_need(type(count)is int and 0<count<=2048
          and row.get('effectBoundary')=='selected-native-request-only;callee-result-alias-and-mutation-unobserved','own request boundary differs: '+name)
        raw=image.pe.bytes_at_va(image.pe.image_base+where,count);_hash(raw,row,'reflection-invoker.'+name);targets[name]=where
        if name in ('contextPop','contextRead'):_expect(raw,bytes.fromhex('486351188d42ff894118488b44d1f8c3'if name=='contextPop'else '48634118488b44c1f8c3'),name)
        else:_need(extents.get(image.pe.image_base+where)==image.pe.image_base+where+count,'own request complete extent differs: '+name)
        if name in ('methodInvoke','ctorInvoke'):_expect(raw,_request_program(name,where,targets,row),'typed '+name+' request')
    inner=spec['methods']['innerException'];_expect(image.pe.bytes_at_va(image.pe.image_base+targets['innerException'],inner['byteCount']),bytes.fromhex('488b4128c3'),'shared innerException raw field leaf')
    cells=_cells(image,spec,contract,token);expected,labels=_program(at,targets,cells);_expect(body,expected,'reflection-invoker.Invoke')
    return dict(status='validated_conditional_reflection_invoker_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
      completeCallerBytes=len(body),conditionalLabelCount=len(labels),labels={n:hex(v)for n,v in labels.items()},callPayloadOffsets=payload,
      rules=spec['rules'],writebackBoundary=spec['writebackBoundary'],cleanupBoundary=spec['cleanupBoundary'],
      unresolved=['actual-invoker-fields-and-Call-storage','framework-reflection-and-pointer-conversion-results','parameter-out-entry-initial-values',
        'current-thread-stack-versus-Call-saved-evaluation-base-and-writeback-mutation','cleanup-callback-effects-and-native-EH-entry',
        'runtime-local-counter-aliases-helper-mutation-and-loop-termination','virtual-dispatch-sharing-and-actual-invocation'])


def validate_selected_reflection_invoker_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    """Gate explicit selected inputs; request-only proof has no runtime fallback."""
    if gameassembly is None or metadata is None:return dict(status='missing',evidenceBoundary='unresolved',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.reflection-invoker');extents=image.mapper.pdata_function_extents(image.pe)
    return validate_reflection_invoker_rules(image,contract['reflectionInvokerRules']if spec is None else spec,contract,extents)


_INVOKE_PROGRAM = ['488bc4448848204c894018488950104889480853565741544155415641574881ec800200004c8be233db',
 ('rip', '381d', 'lazyFlag', ''),
 ('edge', '75', 'metadataReady', 1),
 ('rip', '488d0d', 'boolType', ''),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'intPtrType', ''),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'marshalType', ''),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'objectArray', ''),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'invokeContext', ''),
 ('call', 'typeInitialize'),
 ('rip', '488d0d', 'uintPtrType', ''),
 ('call', 'typeInitialize'),
 ('rip', 'c605', 'lazyFlag', '01'),
 '4c8b8424d0020000488b8c24c0020000',
 ('label', 'metadataReady'),
 '48899c24c8000000895c2478895c2470899c24b8000000895c247c899c2480000000899c2484000000899c2488000000899c248c000000899c2490000000899c2494000000899c2498000000899c249c000000498b401048898424a8000000885c24418b5110',
 ('rip', '488b0d', 'objectArray', ''),
 ('call', 'arrayAllocate'),
 '488bf048898424b000000048895c2448885c244048899c24c0000000488d8424d002000048898424f8000000488d8424c80000004889842400010000488d4424414889842408010000488d8424b80000004889842410010000488d4424784889842418010000488d8424a80000004889842420010000488d8424c00200004889842428010000488d44247c4889842430010000488d8424800000004889842438010000488d8424840000004889842440010000488d8424880000004889842448010000488d8424d80200004889842450010000488d84248c0000004889842458010000488d8424900000004889842460010000488d8424940000004889842468010000488d8424980000004889842470010000488d84249c0000004889842478010000488d4424404889842480010000488d8424c00000004889842488010000488d4424484889842490010000488d442458488984249801000048899c24d0010000488d8c24d8010000488d8424f80000000f10000f11010f1048100f1149100f1040200f1141200f1048300f1149300f1040400f1141400f1048500f1149500f1040600f114160ba800000004803ca0f1040700f1141f00f100c100f11090f104410100f114110488b44102048894120488b8424d00200004c8b304c89b424a0000000895c2454488b8c24c0020000385914',
 ('edge', '74', 'branch1', 1),
 '389c24d8020000',
 ('edge', '75', 'branch1', 1),
 'c7442454010000004983c60c4c89b424a0000000',
 ('label', 'branch1'),
 '8bfb',
 ('label', 'parameterLoop'),
 '897c24503b7910',
 ('edge', '0f8d', 'afterParameters', 4),
 '488b41204885c0',
 ('edge', '0f84', 'branch49', 4),
 '4863d73b7818',
 ('edge', '0f83', 'branch33', 4),
 '385c0220',
 ('edge', '0f85', 'parameterNext', 4),
 '488b8424d00200004c8b50084c8b49284d85c9',
 ('edge', '0f84', 'branch48', 4),
 '4863c7413b7918',
 ('edge', '0f83', 'branch34', 4),
 '48895c2430c6442428014c896424204d8b4cc1204c8b8424a8000000498bd6498bca',
 ('call', 'toObject'),
 '4c8bf84885f6',
 ('edge', '0f84', 'branch47', 4),
 '488bd0488bce',
 ('call', 'assignmentCheck'),
 '4863d74d8bc7488bce',
 ('call', 'managedStore'),
 '488b8424c00200004c8b78284d85ff',
 ('edge', '0f84', 'branch46', 4),
 '4863c7413b7f18',
 ('edge', '0f83', 'branch35', 4),
 '4d8b7cc7204d85ff',
 ('edge', '0f84', 'branch45', 4),
 '498b0f',
 ('call', 'classPrepare'),
 '498b17488b8210040000488b9218040000498bcfffd084c0',
 ('edge', '0f84', 'branch6', 4),
 '4863c73b7e18',
 ('edge', '0f83', 'branch36', 4),
 '48395cc620',
 ('edge', '0f84', 'branch6', 4),
 '4863c73b7e18',
 ('edge', '0f83', 'branch37', 4),
 '488b44c6204885c0',
 ('edge', '74', 'branch3', 1),
 ('rip', '488b15', 'intPtrType', ''),
 '483910',
 ('edge', '75', 'branch3', 1),
 '4863cf3b7e18',
 ('edge', '0f83', 'branch38', 4),
 '488b4cce20',
 ('call', 'unboxAddress'),
 '4c8b38',
 ('edge', 'eb', 'pointerParsed', 1),
 ('label', 'branch3'),
 '4863c73b7e18',
 ('edge', '0f83', 'branch39', 4),
 '488b44c6204885c0',
 ('edge', '74', 'branch4', 1),
 ('rip', '488b15', 'uintPtrType', ''),
 '483910',
 ('edge', '75', 'branch4', 1),
 '4863cf3b7e18',
 ('edge', '0f83', 'branch40', 4),
 '488b4cce20',
 ('call', 'unboxAddress'),
 '4c8b38',
 ('rip', '488b0d', 'uintPtrType', ''),
 ('call', 'classInitialize'),
 ('edge', 'eb', 'pointerParsed', 1),
 ('label', 'branch4'),
 '4863cf3b7e18',
 ('edge', '0f83', 'branch41', 4),
 '33d2488b4cce20',
 ('call', 'pointerUnbox'),
 '4c8bf8',
 ('label', 'pointerParsed'),
 '4c89bc24d0000000488d9424d0000000',
 ('rip', '488b0d', 'intPtrType', ''),
 ('call', 'boxRequest'),
 '4c8bf8488bd0488bce',
 ('call', 'assignmentCheck'),
 '4863d74d8bc7488bce',
 ('call', 'managedStore'),
 '90',
 ('label', 'branch6'),
 '488b8c24c0020000',
 ('label', 'parameterNext'),
 '4983c60c4c89b424a0000000ffc7',
 ('edge', 'e9', 'parameterLoop', 4),
 '48637c2450488bb424b00000003b7e18',
 ('edge', '0f83', 'branch42', 4),
 '33d2488b4cfe20',
 ('call', 'pointerUnbox'),
 '488b8c24c0020000488b512833db4885d2',
 ('edge', '0f84', 'branch44', 4),
 '3b7a18',
 ('edge', '0f83', 'branch43', 4),
 '4533c0488b54fa20488bc8',
 ('call', 'pointerBox'),
 '4c8bf0488bd0488bce',
 ('call', 'assignmentCheck'),
 '488bd74d8bc6488bce',
 ('call', 'managedStore'),
 '908b442470',
 ('edge', 'eb', 'branch8', 1),
 '8b442470ffc833db488bb424b00000008b7c2450',
 ('label', 'branch8'),
 'ffc8894424704c8ba424c8020000488b8c24c00200004c8bb424a0000000',
 ('edge', 'e9', 'parameterNext', 4),
 ('label', 'afterParameters'),
 '389c24d8020000',
 ('edge', '0f85', 'branch22', 4),
 '488b49304885c9',
 ('edge', '0f84', 'branch59', 4),
 '33d2',
 ('call', 'isConstructor'),
 '84c0',
 ('edge', '74', 'branch10', 1),
 '488b8424c0020000488b50304885d2',
 ('edge', '0f84', 'branch51', 4),
 '41bf09000000418bcf',
 ('call', 'returnQuery'),
 '488bf84885c0',
 ('edge', '0f84', 'branch50', 4),
 '488b08',
 ('call', 'classPrepare'),
 '488b17488b8250070000488b9258070000488bcfffd084c0',
 ('edge', '74', 'ordinaryReceiver', 1),
 '488b8c24c0020000',
 ('edge', 'e9', 'constructorRequest', 4),
 ('label', 'branch10'),
 '41bf09000000',
 ('label', 'ordinaryReceiver'),
 '488b8c24c0020000385914',
 ('edge', '0f84', 'noReceiver', 4),
 '488b8424d0020000488b78084c8b304c8bac24a8000000488b51304885d2',
 ('edge', '0f84', 'branch56', 4),
 '418bcf',
 ('call', 'returnQuery'),
 '48895c2430885c24284c896424204c8bc84d8bc5498bd6488bcf',
 ('call', 'toObject'),
 '488bf848894424484885c0',
 ('edge', '0f84', 'branch15', 4),
 '488b8424c0020000488b50304885d2',
 ('edge', '0f84', 'branch55', 4),
 '418bcf',
 ('call', 'returnQuery'),
 '488bf84885c0',
 ('edge', '0f84', 'branch54', 4),
 '488b08',
 ('call', 'classPrepare'),
 '488b17488b8250070000488b9258070000488bcfffd084c0',
 ('edge', '0f84', 'branch18', 4),
 '488b4c24484885c9',
 ('edge', '74', 'branch13', 1),
 ('rip', '488b15', 'intPtrType', ''),
 '483911',
 ('edge', '75', 'branch12', 1),
 '4885c9',
 ('edge', '74', 'branch13', 1),
 ('call', 'unboxAddress'),
 '488b38',
 ('edge', 'eb', 'branch14', 1),
 ('label', 'branch12'),
 '4885c9',
 ('edge', '74', 'branch13', 1),
 ('rip', '488b15', 'uintPtrType', ''),
 '483911',
 ('edge', '75', 'branch13', 1),
 '4885c9',
 ('edge', '74', 'branch13', 1),
 ('call', 'unboxAddress'),
 '488b38',
 ('rip', '488b0d', 'uintPtrType', ''),
 ('call', 'classInitialize'),
 ('edge', 'eb', 'branch14', 1),
 ('label', 'branch13'),
 '33d2',
 ('call', 'pointerUnbox'),
 '488bf8',
 ('label', 'branch14'),
 'c6442440014889bc24c0000000488b8424c0020000488b50304885d2',
 ('edge', '0f84', 'branch52', 4),
 '418bcf',
 ('call', 'returnQuery'),
 '4c8bf0',
 ('rip', '488b0d', 'marshalType', ''),
 ('call', 'classInitialize'),
 '498bd6488bcf',
 ('call', 'structureFromPointer'),
 '488bf84889442448',
 ('label', 'branch15'),
 '488b8c24c0020000',
 ('edge', 'eb', 'receiverPrepared', 1),
 'ff4c247033db448d7b094c8ba424c8020000488b8c24c0020000488bb424b0000000',
 ('label', 'noReceiver'),
 '488b7c2448',
 ('label', 'receiverPrepared'),
 '385948',
 ('edge', '75', 'nullableHasValue', 1),
 '385949',
 ('edge', '0f85', 'branch25', 4),
 '488b49304885c9',
 ('edge', '0f84', 'branch58', 4),
 '33d2',
 ('call', 'isStatic'),
 '4c8b44244884c0',
 ('edge', '75', 'methodRequest', 1),
 '4d85c0',
 ('edge', '0f84', 'nullInstance', 4),
 ('edge', 'eb', 'methodRequest', 1),
 ('label', 'branch18'),
 '488b8c24c0020000',
 ('edge', 'eb', 'noReceiver', 1),
 ('label', 'methodRequest'),
 '488b8424c0020000488b50304885d2',
 ('edge', '0f84', 'branch57', 4),
 'b92200000048895c2430488974242848895c24204533c9',
 ('call', 'methodInvoke'),
 ('label', 'branch20'),
 '488bf8',
 ('edge', 'eb', 'invocationJoin', 1),
 ('label', 'nullableHasValue'),
 '4885ff0f95442442488d542442',
 ('rip', '488b0d', 'boolType', ''),
 ('call', 'boxRequest'),
 ('edge', 'eb', 'branch20', 1),
 ('label', 'branch22'),
 '41bf09000000',
 ('label', 'constructorRequest'),
 '488b51384885d2',
 ('edge', '0f84', 'branch70', 4),
 '48895c242848897424204533c941b800020000',
 ('call', 'ctorInvoke'),
 '488bf8',
 ('label', 'invocationJoin'),
 '488b8c24c0020000',
 ('label', 'branch25'),
 '448bf3',
 ('label', 'referenceLoop'),
 '443b7110',
 ('edge', '0f8d', 'returnTest', 4),
 '488b41184885c0',
 ('edge', '0f84', 'branch65', 4),
 '4963d6443b7018',
 ('edge', '0f83', 'branch60', 4),
 '385c0220',
 ('edge', '74', 'branch27', 1),
 '4885f6',
 ('edge', '0f84', 'branch64', 4),
 '4963c6443b7618',
 ('edge', '0f83', 'branch61', 4),
 '4c8b44c620488b49284885c9',
 ('edge', '0f84', 'branch63', 4),
 '4963c6443b7118',
 ('edge', '0f83', 'branch62', 4),
 '488b4cc1208b5424544103d648895c242848894c24204d8bcc488b8c24d0020000',
 ('call', 'updateReference'),
 '488b8c24c0020000',
 ('label', 'branch27'),
 '41ffc6',
 ('edge', 'e9', 'referenceLoop', 4),
 ('label', 'returnTest'),
 '385915',
 ('edge', '75', 'returnDeclared', 1),
 '389c24d8020000',
 ('edge', '0f84', 'cleanup', 4),
 ('label', 'returnDeclared'),
 '488b49304885c9',
 ('edge', '0f84', 'branch69', 4),
 '33d2',
 ('call', 'isConstructor'),
 '84c0',
 ('edge', '0f84', 'pushResult', 4),
 '488b8424c0020000488b50304885d2',
 ('edge', '0f84', 'branch68', 4),
 '418bcf',
 ('call', 'returnQuery'),
 '488bf04885c0',
 ('edge', '0f84', 'branch67', 4),
 '488b08',
 ('call', 'classPrepare'),
 '488b16488b8250070000488b9258070000488bceffd084c0',
 ('edge', '74', 'pushResult', 1),
 '389c24d8020000',
 ('edge', '75', 'pushResult', 1),
 '488bb424d0020000488b8424c0020000488b50304885d2',
 ('edge', '0f84', 'branch66', 4),
 '418bcf',
 ('call', 'returnQuery'),
 '48895c242848894424204d8bcc4c8bc733d2488bce',
 ('call', 'updateReference'),
 ('edge', 'eb', 'cleanup', 1),
 ('label', 'pushResult'),
 '488b8424c00200004533c94c8b4040488bd7488b8c24d0020000',
 ('call', 'pushResult'),
 'c644244101',
 ('label', 'cleanup'),
 '488d8c24d0010000',
 ('call', 'cleanupNormal'),
 ('edge', 'eb', 'normalReturn', 1),
 '488d8c24d8010000',
 ('call', 'cleanupCaptured'),
 '488b8c24d00100004885c9',
 ('edge', '0f85', 'propagate', 4),
 ('label', 'normalReturn'),
 '4881c480020000415f415e415d415c5f5e5bc3',
 ('label', 'branch33'),
 ('call', 'boundsStop'),
 '90',
 ('label', 'branch34'),
 ('call', 'boundsStop'),
 ('label', 'branch35'),
 ('call', 'boundsStop'),
 ('label', 'branch36'),
 ('call', 'boundsStop'),
 '90',
 ('label', 'branch37'),
 ('call', 'boundsStop'),
 ('label', 'branch38'),
 ('call', 'boundsStop'),
 ('label', 'branch39'),
 ('call', 'boundsStop'),
 ('label', 'branch40'),
 ('call', 'boundsStop'),
 ('label', 'branch41'),
 ('call', 'boundsStop'),
 '90',
 ('label', 'branch42'),
 ('call', 'boundsStop'),
 ('label', 'branch43'),
 ('call', 'boundsStop'),
 ('label', 'branch44'),
 ('call', 'nullStop'),
 '90',
 ('label', 'branch45'),
 ('call', 'nullStop'),
 ('label', 'branch46'),
 ('call', 'nullStop'),
 ('label', 'branch47'),
 ('call', 'nullStop'),
 ('label', 'branch48'),
 ('call', 'nullStop'),
 ('label', 'branch49'),
 ('call', 'nullStop'),
 ('label', 'branch50'),
 ('call', 'nullStop'),
 ('label', 'branch51'),
 ('call', 'nullStop'),
 '90',
 ('label', 'branch52'),
 ('call', 'nullStop'),
 '90',
 ('label', 'nullInstance'),
 '488b8424c0020000488b5830488bcb',
 ('call', 'nullCheck'),
 '418bcf488bd3',
 ('call', 'returnQuery'),
 '488bf8488b8c24c0020000488b5930488bcb',
 ('call', 'nullCheck'),
 'b908000000488bd3',
 ('call', 'nameQuery'),
 '488bd8',
 ('rip', '488d0d', 'nullInstanceLiteral', ''),
 ('call', 'usageResolve'),
 '4533c94c8bc3488bd7488bc8',
 ('call', 'stringFormat'),
 '488bf8',
 ('rip', '488d0d', 'targetExceptionType', ''),
 ('call', 'usageResolve'),
 '488bc8',
 ('call', 'allocateObject'),
 '488bd8488bc8',
 ('call', 'nullCheck'),
 '4533c0488bd7488bcb',
 ('call', 'targetExceptionCtor'),
 ('rip', '488d0d', 'invokeContext', ''),
 ('call', 'usageResolve'),
 '488bd0488bcb',
 ('call', 'throwStop'),
 ('label', 'branch54'),
 ('call', 'nullStop'),
 ('label', 'branch55'),
 ('call', 'nullStop'),
 ('label', 'branch56'),
 ('call', 'nullStop'),
 ('label', 'branch57'),
 ('call', 'nullStop'),
 ('label', 'branch58'),
 ('call', 'nullStop'),
 ('label', 'branch59'),
 ('call', 'nullStop'),
 ('label', 'branch60'),
 ('call', 'boundsStop'),
 ('label', 'branch61'),
 ('call', 'boundsStop'),
 ('label', 'branch62'),
 ('call', 'boundsStop'),
 ('label', 'branch63'),
 ('call', 'nullStop'),
 ('label', 'branch64'),
 ('call', 'nullStop'),
 ('label', 'branch65'),
 ('call', 'nullStop'),
 ('label', 'branch66'),
 ('call', 'nullStop'),
 ('label', 'branch67'),
 ('call', 'nullStop'),
 ('label', 'branch68'),
 ('call', 'nullStop'),
 ('label', 'branch69'),
 ('call', 'nullStop'),
 ('label', 'branch70'),
 ('call', 'nullStop'),
 '90488d4c2458',
 ('call', 'contextPop'),
 '488bc8',
 ('call', 'exceptionPropagate'),
 '488d4c2458',
 ('call', 'contextRead'),
 '488bd8488bc8',
 ('call', 'nullCheck'),
 '488bcb',
 ('call', 'innerException'),
 '488bd8488d4c2458',
 ('call', 'contextPop'),
 ('rip', '488d0d', 'invokeContext', ''),
 ('call', 'usageResolve'),
 '488bd0488bcb',
 ('call', 'throwStop'),
 '90',
 ('label', 'propagate'),
 ('call', 'exceptionPropagate'),
 'cc']
