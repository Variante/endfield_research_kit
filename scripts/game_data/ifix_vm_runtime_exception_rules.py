"""Authenticate IFix exception wrapping and stop requests without native EH.

The two complete IFix callers select by the low wrap byte, construct a
RuntimeException conditionally, store its named Real backing field, and
request the canonical stop wrapper. Its constructor requests inherited
System.Exception.Init without supplying a message. Allocation, metadata
resolution, framework initialization and abnormal transfer remain opaque.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity,_type


class RuntimeExceptionRuleError(ValueError):
    """A conditional exception declaration lacks a selected witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok:raise RuntimeExceptionRuleError('runtime-exception.'+detail)


_METHOD_REF='delegateConstruction.methodCalls.nullFallbackException'
_HELPER_REFS={
 'usageResolve':'objectConversionRules.helpers.usageResolveThunk',
 'throwStop':'objectConversionRules.helpers.throwStop',
 'allocateObject':'stackReferenceRules.nullObjectHelper',
 'nullFailure':'referenceUpdateRules.helpers.nullFailure',
 'referenceBarrier':'delegateBridgeRules.referenceWriteBarrier',
 'typeInitialize':'referenceUpdateRules.helpers.typeInitialize',
 'classInitialize':'anonymousStoreyRules.helpers.classInitialize'}
_CELL_REFS={'exceptionType':'exceptionDispatchRules.usageCells.exceptionType'}
_METHODS={
 'runtimeException':('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False),
 'constructor':('IFix.Core.RuntimeException','.ctor',[],'void',False),
 'exceptionInit':('System.Exception','Init',[],'void',False)}
_BOUNDS={
 'schema':'endfield.ifix-vm-runtime-exception-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'methodRef':_METHOD_REF,
 'inputBoundary':'incoming-RDX-exception-saved-in-RDI;test-low8-R8-wrap-byte;VM-receiver-not-read',
 'storageBoundary':'valid-allocated-object-and-class-storage;normal-helper-return-and-native-ABI;alias-and-helper-mutation-unobserved',
 'stopBoundary':'canonical-throwStop-request-followed-by-INT3;no-normal-return-tail;native-EH-delivery-unobserved',
 'messageBoundary':'IFix-constructor-supplies-no-message-argument;named-System.Exception.Init-tail-request-only;framework-message-and-exception-state-unobserved',
 'contextBoundary':'stored-MethodDef-is-throwRuntimeException;usageResolve-returned-context-unobserved'}
_RULES={
 'wrapZero':'resolve-stored-method-context;request-throwStop(incoming-exception,returned-context);INT3',
 'wrapNonzero':'resolve-RuntimeException-type;allocateObject-request;null-result-requests-nullFailure-then-INT3;nonnull-result-requests-constructor',
 'realStore':'after-normal-constructor-return-store-incoming-exception-in-named-Real-backing-field;request-referenceBarrier-at-field-address',
 'wrappedStop':'resolve-stored-method-context;request-throwStop(allocated-wrapper,returned-context);INT3',
 'constructor':'if-lazy-byte-zero-request-typeInitialize(Exception-cell-address)-then-store-one;load-Exception-cell-class-word;if-class-word-plus224-is-zero-request-classInitialize;tail-request-System.Exception.Init(wrapper,null-context)'}


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k)) is type(v) and spec.get(k)==v for k,v in _BOUNDS.items())
      and spec.get('helperRefs')==_HELPER_REFS and spec.get('cellRefs')==_CELL_REFS
      and spec.get('rules')==_RULES,'unsupported schema/reference/conditional rules')
    _need(set(spec['methods'])=={'constructor','exceptionInit'},'named method set differs')


def _carrier(image: Any,index: int,kind: int,*,instance_field: bool=False) -> bytes:
    _type(image,index)
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
    raw=image.pe.bytes_at_va(pointer,16)
    _need(raw[10]==kind and (not instance_field or not int.from_bytes(raw[8:10],'little')&0x10),
          'raw type kind/static carrier differs')
    return raw


def _layout(image: Any,spec: dict) -> int:
    md=image.metadata;row=spec['fieldLayout'];owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.RuntimeException']
    _need(len(owners)==1 and row.get('type')=='IFix.Core.RuntimeException'
      and row.get('parentType')=='System.Exception' and set(row['fields'])=={'<Real>k__BackingField'},'layout owner/declaration differs')
    owner=owners[0];_need(not owner.bitfield&1 and _type(image,owner.parent_index)=='System.Exception','RuntimeException class/parent differs')
    _carrier(image,owner.byval_type_index,0x12);_carrier(image,owner.parent_index,0x12)
    fields=[f for f in md.fields_for(owner) if md.string(f.name_index)=='<Real>k__BackingField'];r=row['fields']['<Real>k__BackingField']
    _need(len(fields)==1 and r.get('type')=='System.Exception' and _type(image,fields[0].type_index)=='System.Exception',
          'Real field identity/carrier differs')
    _carrier(image,fields[0].type_index,0x12,instance_field=True)
    offset=r['offset'];offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
    _need(type(offset) is int and 16<=offset<=0x7fffffff and offsets.get('<Real>k__BackingField')==offset,'Real field offset differs')
    return offset


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    rows={r['name']:r for r in spec['usageCells']}
    _need(len(rows)==len(spec['usageCells']) and set(rows)=={'runtimeExceptionType','methodContext'},'owned usage set differs')
    rows['exceptionType']=_ref(contract,_CELL_REFS['exceptionType']);result={};md=image.metadata
    for name,(tag,identity) in {'runtimeExceptionType':(1,'IFix.Core.RuntimeException'),
        'exceptionType':(1,'System.Exception'),'methodContext':(3,'IFix.Core.VirtualMachine.throwRuntimeException')}.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(type(row.get('usageTag')) is int and row['usageTag']==tag and row.get('identity')==identity
          and raw==bytes.fromhex(row['rawHex']),'stored usage declaration/bytes differ: '+name)
        index=unresolved_usage_index(raw,image.registration['typesCount']if tag==1 else len(md.methods),tag=tag,source='runtime-exception.'+name,offset=at)
        if tag==1:_need(_type(image,index)==identity,'stored type identity differs: '+name);_carrier(image,index,0x12)
        else:
            method=md.methods[index];owner,method_name,params,returned,static=_METHODS['runtimeException'];r=_ref(contract,_METHOD_REF)
            _need(md.type_full_name(md.types[method.declaring_type])==owner and md.string(method.name_index)==method_name
              and method.token==_rva(r['token']) and method.parameter_count==len(params)
              and [_type(image,p.type_index)for p in md.parameters_for(method)]==params
              and _type(image,method.return_type)==returned and bool(method.flags&0x10)==static
              and method.generic_container_index==-1 and image.method_pointer_va(method)==image.pe.image_base+_rva(r['rva']),
              'stored MethodDef context differs')
        result[name]=at
    row=spec['lazyFlag'];at=_rva(row['rva']);section=row['section']
    _need(type(row.get('byteCount'))is int and row['byteCount']==1
      and row.get('storage')=='unbacked-PE-virtual-tail-runtime-state-unobserved' and 'hex'not in row and 'sha256'not in row,
      'lazy flag boundary differs')
    matches=[s for s in image.pe.sections if s['name']==section['name'] and s['virtualAddress']<=at<s['virtualAddress']+s['virtualSize']]
    _need(len(matches)==1 and matches[0]==section and at>=section['virtualAddress']+section['rawSize'],'lazy flag is not selected unbacked virtual tail')
    result['lazyFlag']=at;return result


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int],field: int) -> tuple[bytes,dict[str,int]]:
    tokens=_PROGRAMS[name];offset=0;labels={}
    def size(token):
        if isinstance(token,str):return len(bytes.fromhex(token))
        kind,*args=token
        if kind=='label':return 0
        if kind in ('call','jump'):return 5
        if kind=='edge':return len(bytes.fromhex(args[0]))+1
        if kind=='field':return len(bytes.fromhex(args[0]))+4
        if kind=='rip':return len(bytes.fromhex(args[0]))+4+len(bytes.fromhex(args[2]))
        _need(False,'unknown finite token')
    for token in tokens:
        if not isinstance(token,str) and token[0]=='label':_need(token[1]not in labels,'duplicate finite label');labels[token[1]]=at+offset
        offset+=size(token)
    out=bytearray()
    for token in tokens:
        if isinstance(token,str):out.extend(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':continue
        if kind=='field':out.extend(bytes.fromhex(args[0])+struct.pack('<i',field));continue
        if kind in ('call','jump'):prefix=b'\xe8'if kind=='call'else b'\xe9';target=targets[args[0]];width=4;suffix=b''
        elif kind=='edge':prefix=bytes.fromhex(args[0]);target=labels[args[1]];width=1;suffix=b''
        else:prefix=bytes.fromhex(args[0]);target=cells[args[1]];width=4;suffix=bytes.fromhex(args[2])
        disp=target-(at+len(out)+len(prefix)+width+len(suffix));out.extend(prefix+disp.to_bytes(width,'little',signed=True)+suffix)
    _need(len(out)==offset,'finite extent differs');return bytes(out),labels


def validate_runtime_exception_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    """Validate the two complete IFix programs inside an already gated image."""
    _claims(spec);rows={'runtimeException':_ref(contract,_METHOD_REF),**spec['methods']};targets={};checked=[]
    for name,identity in _METHODS.items():
        row=rows[name];targets[name]=_identity(image,row,identity,'runtime-exception.'+name,extents)
        _need('bodyBytes'in row,'complete named method required')
        checked.append(dict(method=name,rva=hex(targets[name]),bodyBytes=row['bodyBytes'],
                            effectBoundary='complete-IFix-caller'if name!='exceptionInit'else 'named-framework-request-only'))
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);count=row.get('byteCount',row.get('bodyBytes'))
        _need(type(count)is int and 0<count<=256,'helper witness width differs: '+name)
        raw=image.pe.bytes_at_va(image.pe.image_base+at,count);_hash(raw,row,'runtime-exception.'+name,method='bodyBytes'in row);targets[name]=at
        if name=='throwStop':_need(raw[:14]==bytes.fromhex('4883ec2833c04889413848894140')and raw[14:15]==b'\xe8'and raw[-1:]==b'\xcc','stop wrapper shape differs')
    field=_layout(image,spec);cells=_cells(image,spec,contract);labels={};program_bytes=0
    for name in _PROGRAMS:
        row=rows[name];raw=image.pe.bytes_at_va(image.pe.image_base+targets[name],row['bodyBytes'])
        expected,points=_program(name,targets[name],targets,cells,field);_expect(raw,expected,'runtime-exception.'+name)
        labels[name]={n:hex(v)for n,v in points.items()};program_bytes+=len(raw)
    return dict(status='validated_conditional_runtime_exception_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
      methods=checked,completeProgramCount=2,completeProgramBytes=program_bytes,labels=labels,rules=spec['rules'],
      messageBoundary=spec['messageBoundary'],stopBoundary=spec['stopBoundary'],
      unresolved=['actual-wrap-byte-incoming-exception-and-VM-call','allocation-and-metadata-resolution-results',
        'framework-Exception.Init-message-state-and-helper-mutation','object-class-storage-validity-and-aliases',
        'runtime-lazy-flag-and-class-word','native-EH-selection-exception-delivery-and-throwStop-abnormal-transfer'])


def validate_selected_runtime_exception_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    """Fail closed before opening inputs; no default game root or execution."""
    if gameassembly is None or metadata is None:return dict(status='missing',evidenceBoundary='unresolved',detail='explicit native paths required')
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256'))and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.runtime-exception');extents=image.mapper.pdata_function_extents(image.pe)
    return validate_runtime_exception_rules(image,contract['runtimeExceptionRules']if spec is None else spec,contract,extents)


_PROGRAMS={
 'runtimeException':('48895c2408574883ec20488bfa4584c0',('edge','75','wrap'),
    ('rip','488d0d','methodContext',''),('call','usageResolve'),'488bd0488bcf',('call','throwStop'),'cc',
    ('label','wrap'),('rip','488d0d','runtimeExceptionType',''),('call','usageResolve'),'488bc8',('call','allocateObject'),
    '488bd84885c0',('edge','75','nonnull'),('call','nullFailure'),'cc',('label','nonnull'),'33d2488bcb',('call','constructor'),
    ('field','488d8b'),('field','4889bb'),('call','referenceBarrier'),('rip','488d0d','methodContext',''),('call','usageResolve'),
    '488bd0488bcb',('call','throwStop'),'cc'),
 'constructor':('40534883ec20',('rip','803d','lazyFlag','00'),'488bd9',('edge','75','initialized'),
    ('rip','488d0d','exceptionType',''),('call','typeInitialize'),('rip','c605','lazyFlag','01'),
    ('label','initialized'),('rip','488b0d','exceptionType',''),'83b9e000000000',('edge','75','classReady'),('call','classInitialize'),
    ('label','classReady'),'33d2488bcb4883c4205b',('jump','exceptionInit'))}
