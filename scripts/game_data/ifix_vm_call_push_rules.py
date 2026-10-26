"""Authenticate complete Call object and result push bridge callers.

PushObject writes Object and the low Int32 physical managed index at current
top, requests assignment/store, then advances currentTop by twelve bytes.
Value2 is preserved. PushObjectAsResult instead forwards argumentBase as the
destination to the typed evaluation pusher and sets currentTop=argumentBase+12
on normal return. Live bounds, overlap, helper outcomes and invocation remain
unobserved. Named bodies and layouts are inherited from the reviewed contract.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_object_opcode_rules import _carrier,_signature,_method_declaration


class CallPushRuleError(ValueError):
    """A Call bridge declaration lacks its native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok:raise CallPushRuleError('call-push.'+detail)


def _program(role: str, at: int, targets: dict[str,int]) -> bytes:
    p=_Program(at)
    if role=='pushObject':
        p.add('48895c240848896c24104889742418574883ec204c8b411848b8abaaaaaaaaaaaa2a4c2b4108488bea49f7e8488bd9488bf248d1fe488bc648c1e83f4803f0488b41184885c0');p.branch(0x74,'null')
        p.add('c70008000000488b41184885c0');p.branch(0x74,'null')
        p.add('897004488b79104885ff');p.branch(0x74,'null')
        p.add('488bd5488bcf');p.call(targets['assignmentCheck']);p.add('4863d64c8bc5488bcf');p.call(targets['managedStore'])
        p.add('488343180c488b5c2430488b6c2438488b7424404883c4205fc3');p.mark('null');p.call(targets['nullFailure']);p.add('cc')
    elif role=='pushResult':
        p.add('40534883ec304c8bca48c744242800000000488b11488bd94c894424204c8b4110488b4908');p.call(targets['evaluationPush']);p.add('488b034883c00c488943184883c4305bc3')
    else:_need(False,'unknown finite program')
    return p.finish()


def _layout(image: Any, spec: dict, contract: dict) -> None:
    row=_ref(contract,spec['callLayoutRef']);md=image.metadata;owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.Call']
    _need(row.get('type')=='IFix.Core.Call'and row.get('isValueType')is True and len(owners)==1 and owners[0].bitfield&1,'Call value owner differs')
    owner=owners[0];offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index);fields={md.string(f.name_index):f for f in md.fields_for(owner)}
    expected={n:o for n,(_,o)in _FIELDS.items()};_need(row['fieldOffsets']==offsets==expected and set(fields)==set(expected),'complete Call layout differs')
    for name,(typ,_)in _FIELDS.items():
        f=fields[name];_need(_type(image,f.type_index)==typ,'field type differs: '+name);pointer=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8);_carrier(image,pointer,typ)
        _need(not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&16,'static Call field differs')


def validate_call_push_rules(image: Any, spec: dict, contract: dict, extents: dict[int,int]) -> dict:
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported declaration');_layout(image,spec,contract);targets={};rows={}
    for role,identity in _METHODS.items():
        row=dict(_ref(contract,spec['methodRefs'][role]));row.setdefault('parameterCount',len(identity[2]));_method_declaration(row,identity);_signature(image,identity);targets[role]=_identity(image,row,identity,role,extents);rows[role]=row
    for role,path in spec['helperRefs'].items():
        row=_ref(contract,path);count=row['byteCount'];_need(type(count)is int and 0<count<=4096,'helper extent differs');at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,count),row,role);targets[role]=at
    for role in ('pushObject','pushResult'):
        raw=image.pe.bytes_at_va(image.pe.image_base+targets[role],rows[role]['bodyBytes']);_expect(raw,_program(role,targets[role],targets),role)
    return dict(status='validated_conditional_call_push_rules',evidenceBoundary='conditional',executionBoundary='unobserved',methodCount=2,
                pushObject=spec['pushObject'],pushResult=spec['pushResult'],storageBoundary=spec['storageBoundary'],calleeBoundary=spec['calleeBoundary'])


def validate_selected_call_push_rules(contract: dict, *, gameassembly: Path|None, metadata: Path|None, spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.call-push')
    return validate_call_push_rules(image,contract['callPushRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))


_CLAIMS=dict(schema='endfield.ifix-vm-call-push-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
    methodRefs=dict(pushObject='delegateBridgeRules.methods.pushObject',pushResult='reflectionDispatch.methods.pushResult',evaluationPush='reflectionDispatch.methods.evaluationPush'),
    helperRefs=dict(assignmentCheck='functionPointerRules.helpers.assignmentCheck',managedStore='constrainedTypeOperand.stackEffect.managedStackStoreHelper',nullFailure='referenceUpdateRules.helpers.nullFailure'),
    callLayoutRef='delegateBridgeRules.fieldLayouts.call',
    pushObject='currentTop-evaluationBase-signed-byte-distance-divided-by12;write-Object-and-low32-physical-index;preserve-Value2;assignment-and-managed-store;currentTop+=12',
    pushResult='EvaluationStackOperation.PushObject(evaluationBase,argumentBase,managedStack,object,Type);normal-currentTop=argumentBase+12',
    storageBoundary='valid-stable-Call-Value-and-managed-storage;no-address-wrap;overlap-and-live-contents-unobserved',
    calleeBoundary='normal-helper-returns-without-other-Call-or-Value-storage-mutation;typed-push-conversion-assignment-GC-and-exception-outcomes-unobserved')
_FIELDS=dict(argumentBase=('IFix.Core.Value*',16),evaluationStackBase=('IFix.Core.Value*',24),managedStack=('object[]',32),currentTop=('IFix.Core.Value*',40),topWriteBack=('IFix.Core.Value**',48))
_METHODS=dict(pushObject=('IFix.Core.Call','PushObject',['object'],'void',False),pushResult=('IFix.Core.Call','PushObjectAsResult',['object','System.Type'],'void',False),evaluationPush=('IFix.Core.EvaluationStackOperation','PushObject',['IFix.Core.Value*','IFix.Core.Value*','object[]','object','System.Type'],'void',True))
