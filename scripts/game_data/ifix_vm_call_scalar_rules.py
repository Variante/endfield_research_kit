"""Finite Call scalar push/read programs and leaf tail adapters.

Call's instance receiver is used as an unboxed value-type payload address.
Normal-return effects assume valid stable storage, no Call/slot overlap and
nonmutating helper requests. The native request programs do not observe VM
storage, managed assignment, pointer validity, EH delivery or generic sharing.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.il2cpp.protocol import field_defaults,native_enum_members,runtime_type_field_offsets
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_reflection_invoker_rules import _raw_type,_carrier


class CallScalarRuleError(ValueError):
    """A scalar Call claim lacks its selected finite witness."""


def _need(ok: bool,detail: str) -> None:
    if not ok:raise CallScalarRuleError('call-scalar.'+detail)


_HELPER_REFS={'nullFailure':'referenceUpdateRules.helpers.nullFailure',
 'assignmentCheck':'functionPointerRules.helpers.assignmentCheck','managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper'}
_SCALARS={'bool':2,'byte':5,'short':6,'char':3,'ushort':7,'int':8,'uint':9,'long':10,'ulong':11,'float':12,'double':13,'nint':0x18,'object':0x1c,'void':1}
_PUSH_TYPES={'PushBoolean':'bool','PushByte':'byte','PushInt16':'short','PushChar':'char','PushUInt16':'ushort',
 'PushInt32':'int','PushUInt32':'uint','PushInt64':'long','PushUInt64':'ulong','PushSingle':'float','PushDouble':'double','PushIntPtr':'nint','PushValueType':'object','PushRef':'int'}
_GET_TYPES={'GetBoolean':'bool','GetByte':'byte','GetInt16':'short','GetChar':'char','GetUInt16':'ushort',
 'GetInt32':'int','GetUInt32':'uint','GetInt64':'long','GetUInt64':'ulong','GetSingle':'float','GetDouble':'double','GetIntPtr':'nint'}
_SIGNATURES={**{n:('IFix.Core.Call',n,[t],'void',False)for n,t in _PUSH_TYPES.items()},
 **{n:('IFix.Core.Call',n,['int'],t,False)for n,t in _GET_TYPES.items()}}
_LEAVES={'PushByte','PushInt16','PushChar','PushUInt16','PushUInt32','PushUInt64','PushIntPtr',
 'GetByte','GetInt16','GetChar','GetUInt16','GetUInt32','GetUInt64','GetIntPtr'}
_TAGS={'Integer':0,'Long':1,'Float':2,'Double':3,'StackReference':4,'ValueType':9}
_CALL_FIELDS={'argumentBase':'IFix.Core.Value*','evaluationStackBase':'IFix.Core.Value*','managedStack':'object[]','currentTop':'IFix.Core.Value*','topWriteBack':'IFix.Core.Value**'}
_BOUNDS={'schema':'endfield.ifix-vm-call-scalar-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'callLayoutRef':'delegateBridgeRules.fieldLayouts.call','valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout',
 'boxedHeaderBytes':16,'slotBytes':12,'pointerBytes':8,
 'receiverBoundary':'instance-Call-value-type;native-RCX-is-unboxed-payload-address;implicit-receiver-has-no-separate-raw-byref-parameter-carrier',
 'storageBoundary':'normal-effects-require-valid-stable-storage-and-nonoverlapping-Call-payload-selected-slots;overlap-validity-and-observed-values-unresolved',
 'helperBoundary':'normal-helper-return-without-mutation-is-conditional;managed-assignment-storage-and-native-EH-delivery-unobserved',
 'leafBoundary':'exact-registered-entry-through-tail-transfer;no-selected-pdata-function-extent;no-invented-complete-method-body',
 'getterBoundary':'signed-Int32-authored-runtime-offset;computed-slot-null-guard;no-Value-tag-check-or-capacity-check;return-register-width-is-proved',
 'genericBoundary':'GetAsType-MethodDef-null-native-pointer-does-not-supply-a-native-program;runtime-generic-sharing-and-generated-caller-selection-unobserved'}
_RULES={
 'PushBoolean':'write-Value1=zeroextend-DL-byte;then-Type=Integer;preserve-Value2;currentTop+=12',
 'PushInt32':'write-Value1=EDX-low32;then-Type=Integer;preserve-Value2;currentTop+=12',
 'PushInt64':'write-qword-at-Value1=RDX;then-Type=Long;currentTop+=12',
 'PushSingle':'write-dword-at-Value1=XMM1-low32;then-Type=Float;preserve-Value2;currentTop+=12',
 'PushDouble':'write-qword-at-Value1=XMM1-low64;then-Type=Double;currentTop+=12',
 'PushValueType':'signed-wrap64-distance=currentTop-evaluationStackBase;quotient=trunc-signed-distance-div12-via-multiply-high-shift-sign-correction;write-Type=ValueType-then-Value1=low32-quotient;preserve-Value2;assignmentCheck-and-managedStore(managedStack,signextend-low32-quotient,object);currentTop+=12',
 'PushRef':'pointer=argumentBase+12*signextend-EDX-modulo64;write-pointer-qword-at-Value1;then-Type=StackReference;currentTop+=12',
 'PushByte':'zeroextend-DL-to-EDX;zero-R8D-context;tail-PushInt32',
 'PushInt16':'signextend-DX-to-EDX;zero-R8D-context;tail-PushInt32',
 'PushChar':'zeroextend-DX-to-EDX;zero-R8D-context;tail-PushInt32',
 'PushUInt16':'zeroextend-DX-to-EDX;zero-R8D-context;tail-PushInt32',
 'PushUInt32':'preserve-EDX-bits;zero-R8D-context;tail-PushInt32',
 'PushUInt64':'preserve-RDX-bits;zero-R8D-context;tail-PushInt64',
 'PushIntPtr':'two-byte-NOP;preserve-RDX-bits;zero-R8D-context;tail-PushInt64',
 'GetBoolean':'slot=argumentBase+12*signextend-EDX-modulo64;guard-computed-slot-nonzero;AL=(dword-at-Value1!=0);no-stores',
 'GetInt32':'slot=argumentBase+12*signextend-EDX-modulo64;guard-computed-slot-nonzero;EAX=dword-at-Value1;no-stores',
 'GetInt64':'slot=argumentBase+12*signextend-EDX-modulo64;guard-computed-slot-nonzero;RAX=qword-at-Value1;no-stores',
 'GetSingle':'slot=argumentBase+12*signextend-EDX-modulo64;guard-computed-slot-nonzero;XMM0-low32=dword-at-Value1;no-stores',
 'GetDouble':'slot=argumentBase+12*signextend-EDX-modulo64;guard-computed-slot-nonzero;XMM0-low64=qword-at-Value1;no-stores',
 **{n:'zero-R8D-context;tail-GetInt32;EAX-bits-returned-without-local-narrowing;declared-return-'+_GET_TYPES[n]for n in ('GetByte','GetInt16','GetChar','GetUInt16','GetUInt32')},
 **{n:'zero-R8D-context;tail-GetInt64;RAX-bits-returned;declared-return-'+_GET_TYPES[n]for n in ('GetUInt64','GetIntPtr')}}
_PROGRAMS={
 'PushBoolean':('4883ec284c8b41184d85c0741d0fb6c241894004488b41184885c0740d832000488341180c4883c428c3',('call','nullFailure'),'cc'),
 'PushInt32':('4883ec28488b41184885c0741c895004488b41184885c07410c70000000000488341180c4883c428c3',('call','nullFailure'),'cc'),
 'PushInt64':('4883ec28488b41184885c0741d48895004488b41184885c07410c70001000000488341180c4883c428c3',('call','nullFailure'),'cc'),
 'PushSingle':('4883ec28488b41184885c07415f30f114804c70002000000488341180c4883c428c3',('call','nullFailure'),'cc'),
 'PushDouble':('4883ec28488b41184885c07415f20f114804c70003000000488341180c4883c428c3',('call','nullFailure'),'cc'),
 'PushRef':('4883ec284c8b41184d85c0742b4863c2488d1440488b01488d149049895004488b41184885c07410c70004000000488341180c4883c428c3',('call','nullFailure'),'cc'),
 'PushValueType':('48895c240848896c24104889742418574883ec204c8b411848b8abaaaaaaaaaaaa2a4c2b4108488bea49f7e8488bd9488bf248d1fe488bc648c1e83f4803f0488b41184885c0744ec70009000000488b41184885c0743f897004488b79104885ff7433488bd5488bcf',('call','assignmentCheck'),'4863d64c8bc5488bcf',('call','managedStore'),'488343180c488b5c2430488b6c2438488b7424404883c4205fc3',('call','nullFailure'),'cc'),
 **{n:('4883ec284c8b014863c2488d0c40498d04884885c07506',('call','nullFailure'),'cc',tail,'4883c428c3')for n,tail in {
  'GetBoolean':'4863c2488d0c4041837c8804000f95c0','GetInt32':'4863ca488d0449418b448004',
  'GetInt64':'4863ca488d0449498b448004','GetSingle':'4863c2488d0c40f3410f10448804','GetDouble':'4863c2488d0c40f2410f10448804'}.items()},
 'PushByte':('0fb6d24533c0',('tail','PushInt32')),'PushInt16':('0fbfd24533c0',('tail','PushInt32')),
 'PushChar':('0fb7d24533c0',('tail','PushInt32')),'PushUInt16':('0fb7d24533c0',('tail','PushInt32')),
 'PushUInt32':('4533c0',('tail','PushInt32')),'PushUInt64':('4533c0',('tail','PushInt64')),
 'PushIntPtr':('66904533c0',('tail','PushInt64')),
 **{n:('4533c0',('tail','GetInt32'))for n in ('GetByte','GetInt16','GetChar','GetUInt16','GetUInt32')},
 **{n:('4533c0',('tail','GetInt64'))for n in ('GetUInt64','GetIntPtr')}}


def _program(name: str,at: int,targets: dict) -> bytes:
    out=bytearray()
    for part in _PROGRAMS[name]:
        if isinstance(part,str):out.extend(bytes.fromhex(part));continue
        kind,target=part;out.append(0xe8 if kind=='call'else 0xe9);out.extend((targets[target]-(at+len(out)+4)).to_bytes(4,'little',signed=True))
    return bytes(out)


def _layouts(image: Any,spec: dict,contract: dict) -> dict:
    md=image.metadata;layouts={}
    for role,name,fields,path in [('call','IFix.Core.Call',_CALL_FIELDS,spec['callLayoutRef']),
      ('value','IFix.Core.Value',{'Type':'IFix.Core.ValueType','Value1':'int','Value2':'int'},spec['valueLayoutRef'])]:
        row=_ref(contract,path);owners=[t for t in md.types if md.type_full_name(t)==name]
        _need(len(owners)==1 and owners[0].bitfield&1 and row.get('type')==name,'value-type layout owner differs: '+role)
        owner=owners[0];definitions={md.string(f.name_index):f for f in md.fields_for(owner)}
        _need(set(definitions)==set(fields),'layout field set differs: '+role)
        for n,t in fields.items():_carrier(image,definitions[n].type_index,t,instance=True)
        actual=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
        _need(actual==row['fieldOffsets'],'raw field offsets differ: '+role);layouts[role]=actual
    _need(layouts['call']==dict(argumentBase=16,evaluationStackBase=24,managedStack=32,currentTop=40,topWriteBack=48)
      and layouts['value']==dict(Type=16,Value1=20,Value2=24),'unboxed operand layout differs')
    tags={r['name']:r['id']for r in native_enum_members(md,field_defaults(md),image.pe,image.registration,'IFix.Core.ValueType')}
    _need(spec.get('valueTypeMembers')==_TAGS and all(tags.get(n)==v for n,v in _TAGS.items()),'native ValueType tags differ')
    return {n:v-16 for n,v in layouts['call'].items()}


def _generic_definition(image: Any,row: dict) -> None:
    md=image.metadata;matches=[m for t in md.types if md.type_full_name(t)=='IFix.Core.Call'for m in md.methods_for(t)if md.string(m.name_index)=='GetAsType'and m.parameter_count==1]
    _need(len(matches)==1,'GetAsType definition differs');m=matches[0];params=md.parameters_for(m)
    _need((row.get('type'),row.get('method'),row.get('parameterCount'),row.get('parameterTypes'))==('IFix.Core.Call','GetAsType',1,['int'])
      and m.index==row.get('methodIndex')and m.token==_rva(row['token'])and not m.flags&0x10
      and m.generic_container_index==row.get('genericContainerIndex')and m.generic_container_index>=0 and len(params)==1,'GetAsType declaration identity differs')
    _raw_type(image,params[0].type_index,8);_need(_type(image,params[0].type_index)=='int','GetAsType offset carrier differs')
    raw=_raw_type(image,m.return_type,0x1e);_need(raw.hex()==row['returnRawHex'].lower(),'GetAsType MVAR raw carrier differs')
    owner=method_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),[x.generic_container_index for x in md.methods],source='call-scalar.GetAsType')
    _need(owner==row['mvarOwner']and owner['methodIndex']==m.index and owner['ordinal']==0
      and int.from_bytes(bytes.fromhex(owner['containerRawHex'])[4:8],'little',signed=True)==1,'GetAsType reciprocal MVAR owner differs')
    _need(image.method_pointer_va(m)==_rva(row['nativePointerVa'])==0,'GetAsType MethodDef no-body pointer differs')


def validate_call_scalar_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    """Prove all finite scalar entry programs; runtime values stay unresolved."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _BOUNDS.items())and spec.get('rules')==_RULES
      and spec.get('helperRefs')==_HELPER_REFS and set(spec.get('methods',{}))==set(_SIGNATURES),'unsupported schema/rules/method set')
    offsets=_layouts(image,spec,contract);_generic_definition(image,spec['genericDefinition']);targets={};selected={};md=image.metadata
    for n,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);count=row['byteCount'];_need(type(count)is int and 0<count<=128,'helper extent differs: '+n)
        _hash(image.pe.bytes_at_va(image.pe.image_base+at,count),row,'call-scalar.'+n);targets[n]=at
    for n,signature in _SIGNATURES.items():
        row=spec['methods'][n];leaf=n in _LEAVES
        _need(('bodyBytes'in row)==(not leaf)and row.get('entryBoundary')==('finite-tail-entry-without-pdata-function-extent'if leaf else 'complete-selected-pdata-function'),'entry extent boundary differs: '+n)
        at=_identity(image,row,signature,'call-scalar.'+n,extents);targets[n]=at
        matches=[m for t in md.types if md.type_full_name(t)=='IFix.Core.Call'for m in md.methods_for(t)if m.token==_rva(row['token'])and md.string(m.name_index)==n]
        _need(len(matches)==1,'method carrier token differs: '+n);m=matches[0];params=md.parameters_for(m);_need(len(params)==1,'parameter count differs: '+n)
        _raw_type(image,params[0].type_index,_SCALARS[signature[2][0]]);_raw_type(image,m.return_type,_SCALARS[signature[3]])
        count=row['byteCount']if leaf else row['bodyBytes'];_need(type(count)is int and 0<count<=256,'entry program width differs: '+n)
        if leaf:_need(image.pe.image_base+at not in extents,'leaf unexpectedly has selected pdata function extent: '+n)
        selected[n]=(at,image.pe.bytes_at_va(image.pe.image_base+at,count))
    for n,(at,raw)in selected.items():_expect(raw,_program(n,at,targets),'call-scalar.'+n)
    return dict(status='validated_conditional_call_scalar_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
      completeMethodCount=len(selected)-len(_LEAVES),finiteTailEntryCount=len(_LEAVES),methodDeclarationCount=len(selected),
      declaredProgramBytes=sum(len(raw)for _,raw in selected.values()),uniqueEntryProgramCount=len(set(selected.values())),
      uniqueEntryProgramBytes=sum(len(raw)for _,raw in set(selected.values())),callPayloadOffsets=offsets,rules=spec['rules'],
      storageBoundary=spec['storageBoundary'],getterBoundary=spec['getterBoundary'],genericBoundary=spec['genericBoundary'],
      unresolved=['Call-and-slot-storage-validity-overlap-and-actual-values','managed-assignment-and-helper-mutation',
        'actual-primitive-ABI-caller-narrowing','native-EH-delivery','generic-GetAsType-runtime-selection'])


def validate_selected_call_scalar_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    """Gate explicit selected inputs without a default game root or fallback."""
    if gameassembly is None or metadata is None:return dict(status='missing',evidenceBoundary='unresolved',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.call-scalar');extents=image.mapper.pdata_function_extents(image.pe)
    return validate_call_scalar_rules(image,contract['callScalarRules']if spec is None else spec,contract,extents)
