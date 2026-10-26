"""Authenticate explicit AnonymousStoreyInfo defaults and barrier requests.

The complete IFix constructor writes its three Int32 fields and three array
references as zero. It issues a barrier after each reference write, ending
with a tail request. The loader's complete array-store helper writes the
supplied pointer before its own tail barrier. Allocation, live storage, barrier completion and aliases
remain conditional. The owning anonymous-storey contract supplies all native
declarations; this group introduces no duplicate method or field catalog.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity,_type
from scripts.game_data.ifix_vm_object_opcode_rules import _method_declaration,_signature
from scripts.game_data.ifix_vm_anonymous_storey_rules import _named_carrier
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program,_barrier_program


class AnonymousInfoConstructorRuleError(ValueError):
    """The complete constructor lacks its selected native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok:raise AnonymousInfoConstructorRuleError('anonymous-info-constructor.'+detail)


_CLAIMS=dict(schema='endfield.ifix-vm-anonymous-info-constructor-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
    methodRef='anonymousStoreyRules.methods.infoCtor',layoutRef='anonymousStoreyRules.fieldLayouts',layoutOwner='IFix.Core.AnonymousStoreyInfo',
    barrierRef='delegateBridgeRules.referenceWriteBarrier',
    arrayStoreRef='anonymousStoreyRules.helpers.infoArrayStore',boundsFailureRef='referenceUpdateRules.helpers.boundsFailure',
    integerEffect='FieldNum=0;one-qword-store-clears-adjacent-CtorId-and-CtorParamNum',
    referenceEffect='FieldTypes=null;barrier;Slots=null;barrier;VTable=null;tail-barrier',
    arrayStoreEffect='unsigned-low32-index-bounds;store-R8-at-array+32+full64-RDX*8;tail-barrier-at-written-cell',
    indexBoundary='compatible-full64-index-required;bounds-guard-alone-does-not-normalize-index',
    storageBoundary='valid-stable-receiver-array-and-barrier-global-storage;no-address-wrap;barrier-storage-does-not-alias-receiver-or-written-array-cell',
    outcomeBoundary='normal-native-barrier-completion;allocation-GC-concurrency-and-execution-unobserved')
_FIELDS=dict(FieldNum='int',FieldTypes='int[]',CtorId='int',CtorParamNum='int',Slots='int[]',VTable='int[]')
_IDENTITY=('IFix.Core.AnonymousStoreyInfo','.ctor',[],'void',False)


def _layout(image: Any, spec: dict, contract: dict) -> dict[str,int]:
    row=_ref(contract,spec['layoutRef'])[spec['layoutOwner']];md=image.metadata
    owners=[t for t in md.types if md.type_full_name(t)==_IDENTITY[0]]
    _need(len(owners)==1 and not owners[0].bitfield&1 and row['type']==_IDENTITY[0] and set(row['fields'])==set(_FIELDS),'complete reference owner/layout differs')
    owner=owners[0];actual=runtime_type_field_offsets(md,image.pe,image.registration,owner.index)
    fields={md.string(f.name_index):f for f in md.fields_for(owner)}
    _need(set(fields)==set(_FIELDS) and set(actual)==set(_FIELDS),'complete field set differs')
    offsets={}
    for name,typ in _FIELDS.items():
        f=fields[name];declared=row['fields'][name];offset=declared['offset']
        _need(type(offset)is int and 16<=offset<128 and declared['type']==_type(image,f.type_index)==typ and actual[name]==offset,'named field/type/offset differs: '+name)
        pointer=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8);raw=image.pe.bytes_at_va(pointer,16)
        _named_carrier(image,pointer,typ);_need(not int.from_bytes(raw[8:10],'little')&16,'static field differs: '+name);offsets[name]=offset
    _need(offsets['CtorParamNum']==offsets['CtorId']+4,'qword integer fields are not adjacent')
    return offsets


def _program(at: int, fields: dict[str,int], barrier: int) -> bytes:
    p=_Program(at);p.add('4883ec284533d24c8bc9448951');p.byte(fields['FieldNum'])
    p.add('4c8951');p.byte(fields['FieldTypes']);p.add('4883c1');p.byte(fields['FieldTypes']);p.call(barrier)
    p.add('498d49');p.byte(fields['Slots']);p.add('4d8951');p.byte(fields['CtorId']);p.add('4d8951');p.byte(fields['Slots']);p.call(barrier)
    p.add('498d49');p.byte(fields['VTable']);p.add('4d8951');p.byte(fields['VTable']);p.add('4883c428');p.rip('e9',barrier)
    return p.finish()


def _array_store_program(at: int, barrier: int, bounds: int) -> bytes:
    p=_Program(at);p.add('4883ec283b5118');p.branch(0x72,'store');p.call(bounds);p.add('cc');p.mark('store')
    p.add('4c8944d120488d0cd14883c1204883c428');p.rip('e9',barrier)
    return p.finish()


def validate_anonymous_info_constructor_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    _need(all(type(spec.get(k))is type(v) and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported conditional declaration')
    fields=_layout(image,spec,contract);row=_ref(contract,spec['methodRef']);_method_declaration(row,_IDENTITY);_signature(image,_IDENTITY)
    at=_identity(image,row,_IDENTITY,'anonymousInfoConstructor',extents)
    barrier=_ref(contract,spec['barrierRef']);raw=image.pe.bytes_at_va(image.pe.image_base+_rva(barrier['rva']),barrier['byteCount'])
    _hash(raw,barrier,'referenceWriteBarrier');_expect(raw,_barrier_program(barrier),'referenceWriteBarrier')
    _expect(image.pe.bytes_at_va(image.pe.image_base+at,row['bodyBytes']),_program(at,fields,_rva(barrier['rva'])),'anonymousInfoConstructor')
    store=_ref(contract,spec['arrayStoreRef']);bounds=_ref(contract,spec['boundsFailureRef']);store_at=_rva(store['rva']);count=store['byteCount']
    _need(type(count)is int and extents.get(image.pe.image_base+store_at)==image.pe.image_base+store_at+count,'array-store complete extent differs')
    raw=image.pe.bytes_at_va(image.pe.image_base+store_at,count);_hash(raw,store,'infoArrayStore')
    _hash(image.pe.bytes_at_va(image.pe.image_base+_rva(bounds['rva']),bounds['byteCount']),bounds,'boundsFailure')
    _expect(raw,_array_store_program(store_at,_rva(barrier['rva']),_rva(bounds['rva'])),'infoArrayStore')
    return dict(status='validated_conditional_anonymous_info_constructor_rules',evidenceBoundary='conditional',executionBoundary='unobserved',
        methodRef=spec['methodRef'],integerEffect=spec['integerEffect'],referenceEffect=spec['referenceEffect'],
        arrayStoreEffect=spec['arrayStoreEffect'],indexBoundary=spec['indexBoundary'],
        barrierEffect='complete-canonical-program-preserves-R9-receiver-and-R10-zero;conditional-card-bitmap-mutation',
        storageBoundary=spec['storageBoundary'],outcomeBoundary=spec['outcomeBoundary'])


def validate_selected_anonymous_info_constructor_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256')) and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.anonymous-info-constructor')
    return validate_anonymous_info_constructor_rules(image,contract['anonymousInfoConstructorRules'] if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
