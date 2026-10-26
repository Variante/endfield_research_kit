"""Authenticate finite IFix VM table accessors without runtime storage reads.

Five getters load a selected named field to RAX and RET. Eight setters first
store incoming RDX to that field, adjust RCX to its address, then tail-request
the existing write barrier. No entry locally checks the receiver or input,
allocates, clears table elements, clones, casts or updates another VM field.

The proof checks exact registered entries through RET/tail transfer, not a
fabricated pdata function extent. Metadata verifies instance/nongeneric raw
signatures and non-byref reference/array/constructed-generic field carriers;
layouts and the barrier are reused from their existing catalog owners. The
nontrivial ExternMethods/StaticFieldTypes setters retain vmConstructionRules.
Stable valid receiver storage, source identity, aliases, table contents, GC
completion, helper mutation, exceptions and actual invocation stay conditional.
Per-build addresses/hashes are declarations in JSON, behind explicit gates.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _type
from scripts.game_data.ifix_vm_vm_construction_rules import _signature, _carrier
from scripts.game_data.ifix_vm_reference_helper_rules import _address


class VmTableAccessorRuleError(ValueError):
    """A VM accessor declaration lacks its selected entry witness."""


def _need(ok: bool,detail: str) -> None:
    if not ok:raise VmTableAccessorRuleError('vm-table-accessor.'+detail)


_FIELDS={'exceptionHandlers':'IFix.Core.ExceptionHandler[][]','externTypes':'System.Type[]',
 'externMethods':'System.Reflection.MethodBase[]','internStrings':'string[]','fieldInfos':'System.Reflection.FieldInfo[]',
 'newFieldInfos':'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>',
 'anonymousStoreyInfos':'IFix.Core.AnonymousStoreyInfo[]','cctors':'int[]','wrappersManager':'IFix.Core.WrappersManager'}
_FIELD_REFS={'exceptionHandlers':'exceptionDispatchRules.fieldLayouts.vm.fields.exceptionHandlers',
 'externTypes':'anonymousStoreyRules.fieldLayouts',
 'externMethods':'functionPointerRules.runtimeFields',
 'internStrings':'stringOpcodeRules.field','fieldInfos':'referenceAddressRules.fieldLayouts.vm.fields.fieldInfos',
 'newFieldInfos':'referenceAddressRules.fieldLayouts.vm.fields.newFieldInfos',
 'anonymousStoreyInfos':'callOpcodeRules.fieldLayouts',
 'cctors':'negativeFieldRules.vmFields.fields.cctors',
 'wrappersManager':'anonymousStoreyRules.fieldLayouts'}
_FIELD_ROUTES={'externTypes':['IFix.Core.VirtualMachine','fields','externTypes'],
 'externMethods':['IFix.Core.VirtualMachine','externMethods'],
 'anonymousStoreyInfos':['IFix.Core.VirtualMachine','fields','anonymousStoreyInfos'],
 'wrappersManager':['IFix.Core.VirtualMachine','fields','wrappersManager']}
_GETTERS={'get_ExceptionHandlers':'exceptionHandlers','get_ExternTypes':'externTypes','get_ExternMethods':'externMethods',
 'get_InternStrings':'internStrings','get_WrappersManager':'wrappersManager'}
_SETTERS={'set_ExceptionHandlers':'exceptionHandlers','set_ExternTypes':'externTypes','set_InternStrings':'internStrings',
 'set_FieldInfos':'fieldInfos','set_NewFieldInfos':'newFieldInfos','set_AnonymousStoreyInfos':'anonymousStoreyInfos',
 'set_Cctors':'cctors','set_WrappersManager':'wrappersManager'}
_METHODS={**{n:('IFix.Core.VirtualMachine',n,[],_FIELDS[f],False)for n,f in _GETTERS.items()},
 **{n:('IFix.Core.VirtualMachine',n,[_FIELDS[f]],'void',False)for n,f in _SETTERS.items()}}
_EFFECTS={**{n:'return-current-qword:'+f+';no-local-store-or-helper-request'for n,f in _GETTERS.items()},
 **{n:'store-incoming-RDX:'+f+';tail-writeBarrier(address-of-'+f+');no-other-local-field-store'for n,f in _SETTERS.items()}}
_CLAIMS={'schema':'endfield.ifix-vm-vm-table-accessor-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'fieldRefs':_FIELD_REFS,'fieldRoutes':_FIELD_ROUTES,'barrierRef':'delegateBridgeRules.referenceWriteBarrier','effects':_EFFECTS,
 'constructionRefs':{'ExternMethodsSetter':'vmConstructionRules.methods.externMethods','StaticFieldTypesSetter':'vmConstructionRules.methods.staticFieldTypes'},
 'entryBoundary':'finite-registered-entry-through-RET-or-barrier-tail-without-pdata-function-extent',
 'getterBoundary':'native-RAX-return-is-current-field-qword;object-identity-table-contents-and-selected-receiver-unobserved',
 'setterBoundary':'physical-qword-store-before-barrier-tail;no-local-receiver-or-input-null-check;GC-completion-and-helper-mutation-unobserved',
 'storageBoundary':'normal-effects-require-valid-stable-VM-instance-field-storage;actual-aliases-mutation-and-invocation-unobserved',
 'tableBoundary':'stored-reference-only;no-local-allocation-element-initialization-conversion-cache-clear-or-other-field-update',
 'nativeExceptionBoundary':'no-local-null-guard;runtime-fault-delivery-and-native-EH-unobserved'}


def _fields(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    md=image.metadata;owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.VirtualMachine']
    _need(len(owners)==1 and not owners[0].bitfield&1,'VM reference owner differs')
    owner=owners[0];definitions={md.string(f.name_index):f for f in md.fields_for(owner)}
    offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index);result={}
    for name,typ in _FIELDS.items():
        row=_ref(contract,spec['fieldRefs'][name])
        for key in spec['fieldRoutes'].get(name,[]):row=row[key]
        offset=row.get('offset');field=definitions.get(name)
        _need(field is not None and row.get('type')==typ and type(offset)is int and 16<=offset<=4096
              and offsets.get(name)==offset and _type(image,field.type_index)==typ,'field name/type/offset differs: '+name)
        if 'static'in row:_need(row['static']is False,'declared static field differs: '+name)
        ptr=image.pe.u64_at_va(_rva(image.registration['types'])+field.type_index*8);raw=image.pe.bytes_at_va(ptr,16);_carrier(image,ptr,typ)
        _need(not int.from_bytes(raw[8:10],'little')&16,'raw static field differs: '+name)
        if 'rawTypeHex'in row:_need(raw==bytes.fromhex(row['rawTypeHex']),'declared raw field carrier differs: '+name)
        result[name]=offset
    _need(len(set(result.values()))==len(result),'table field offsets overlap')
    return result


def _program(name: str,at: int,offset: int,barrier: int) -> bytes:
    small=offset<128;disp=offset.to_bytes(1 if small else 4,'little')
    if name in _GETTERS:return bytes.fromhex('488b41'if small else'488b81')+disp+b'\xc3'
    raw=bytes.fromhex('488951'if small else'488991')+disp
    raw+=bytes.fromhex('4883c1'if small else'4881c1')+disp+b'\xe9'
    return raw+(barrier-at-len(raw)-4).to_bytes(4,'little',signed=True)


def validate_vm_table_accessor_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    _need(all(type(spec.get(k))is type(v) and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/effect/boundary')
    _need(set(spec.get('methods',{}))==set(_METHODS),'complete accessor method set differs')
    fields=_fields(image,spec,contract);barrier=_ref(contract,spec['barrierRef']);barrier_at=_address(barrier['rva'],'barrier')
    count=barrier['byteCount'];_need(type(count)is int and 0<count<=4096,'barrier window size differs')
    _hash(image.pe.bytes_at_va(image.pe.image_base+barrier_at,count),barrier,'barrier')
    entries=[]
    for name,identity in _METHODS.items():
        row=spec['methods'][name];_need(row.get('entryBoundary')==spec['entryBoundary'] and 'bodyBytes'not in row,'finite entry boundary differs: '+name)
        count=row.get('byteCount');_need(type(count)is int and 0<count<=64,'finite entry count differs: '+name)
        m=_signature(image,row,identity);pointer=image.method_pointer_va(m);at=_address(row['rva'],name)
        _need(pointer==image.pe.image_base+at and pointer not in extents,'registered entry/pdata boundary differs: '+name)
        raw=image.pe.bytes_at_va(pointer,count);_hash(raw,row,name)
        _expect(raw,_program(name,at,fields[(_GETTERS|_SETTERS)[name]],barrier_at),'finite '+name);entries.append((at,raw))
    return dict(status='validated_conditional_vm_table_accessor_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
        finiteEntryCount=len(entries),getterCount=len(_GETTERS),setterCount=len(_SETTERS),declaredEntryBytes=sum(len(b)for _,b in entries),
        effects=spec['effects'],entryBoundary=spec['entryBoundary'],storageBoundary=spec['storageBoundary'],setterBoundary=spec['setterBoundary'])


def validate_selected_vm_table_accessor_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.vm-table-accessors')
    return validate_vm_table_accessor_rules(image,contract['vmTableAccessorRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
