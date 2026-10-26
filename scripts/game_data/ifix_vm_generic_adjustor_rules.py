"""Prove selected registration-addressed cells and finite Call adjustor leaves.

The registration ABI exposes an adjustor pointer without a count. This module
does not invent a table extent or relax the shared no-adjustor decoder. After
the exact object/bool/nint ordinary candidates have been authenticated, it
reads only the raw-backed qword at registration pointer + retained index*8.
Each selected cell names a nine-byte entry program: add the boxed header to
RCX, then transfer directly to the corresponding ordinary candidate.

Those are exact stored cells and conditional register programs, not a runtime
adjustor-table bounds proof, a selected invocation, or a valid boxed receiver.
Adjacent padding and the following function are excluded. The programs have
no selected pdata extent and are proved only from entry to unconditional tail.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect
from scripts.game_data.ifix_vm_generic_reference_get_rules import validate_generic_reference_get_rules
from scripts.game_data.ifix_vm_generic_scalar_get_rules import validate_generic_scalar_get_rules


class GenericAdjustorRuleError(ValueError):
    """A selected raw cell or finite adjustor entry differs."""


_SOURCES={'object':'genericReferenceGetRules','bool':'genericScalarGetRules','nint':'genericScalarGetRules'}
_CLAIMS=dict(schema='endfield.ifix-vm-generic-adjustor-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
    sourceGroups=_SOURCES,callLayoutRef='delegateBridgeRules.fieldLayouts.call',boxedHeaderBytes=16,
    cellBoundary='selected-raw-backed-registration-addressed-qwords-only;logical-adjustor-table-extent-and-runtime-index-validity-unobserved',
    leafBoundary='finite-entry-through-unconditional-tail-without-pdata-function-extent;adjacent-padding-and-functions-excluded',
    receiverRecipe='RCX=wrapping-u64(RCX+boxedHeaderBytes);other-argument-registers-preserved;flags-affected;tail-ordinary-candidate',
    runtimeBoundary='incoming-boxed-receiver-validity-context-sharing-invoker-or-adjustor-selection-and-execution-unobserved')


def _need(ok: bool,detail: str) -> None:
    if not ok:raise GenericAdjustorRuleError('generic-adjustor.'+detail)


def _source(contract: dict,name: str) -> tuple[dict,dict]:
    group=contract[_SOURCES[name]];rows=[r for r in group['selections']if r.get('argumentType')==name]
    _need(len(rows)==1,'exact source context required: '+name);row=rows[0]
    if name=='object':return row,group['candidateProgram']
    candidates=row['candidates'];_need(len(candidates)==1,'exact scalar source candidate required: '+name)
    return candidates[0],row['candidateProgram']


def validate_generic_adjustor_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    """Check selected cells without claiming the global table's extent."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/claim/boundary')
    validate_generic_reference_get_rules(image,contract['genericReferenceGetRules'],contract,extents)
    validate_generic_scalar_get_rules(image,contract['genericScalarGetRules'],contract,extents)
    layout=_ref(contract,spec['callLayoutRef']);_need(layout['fieldOffsets']['argumentBase']==spec['boxedHeaderBytes'],'boxed Call header differs')
    pe=image.pe;code=image.mapper.code_registration_summary(pe,image.code_registration);table=_rva(code['genericAdjustorThunks'])
    _need(type(table)is int and 0<table<1<<64,'non-null registration adjustor pointer required')
    rows=spec.get('cells',[]);_need([r.get('argumentType')for r in rows]==['object','bool','nint'],'complete ordered selected cells required')
    for row in rows:
        name=row['argumentType'];source,program=_source(contract,name);index=source['indices'][2]
        _need(type(index)is int and 0<=index<(1<<64)//8 and table<=(1<<64)-8-index*8,'selected address would wrap')
        at=table+index*8;_need(at==pe.image_base+_rva(row['cellRva']),'selected registration address differs: '+name)
        raw=pe.bytes_at_va(at,8);_need(len(raw)==8 and raw.hex().upper()==row['cellRawHex'],'selected cell bytes differ: '+name)
        pointer=int.from_bytes(raw,'little');entry=row['entry'];where=pe.image_base+_rva(entry['rva'])
        _need(pointer==where and pointer!=0 and pointer not in extents,'finite entry pointer/pdata boundary differs: '+name)
        _need(entry.get('byteCount')==9,'only finite nine-byte entry admitted')
        body=pe.bytes_at_va(pointer,9);_hash(body,entry,'adjustor.'+name)
        target=_rva(program['rva']);expected=bytes.fromhex('4883c1')+bytes([spec['boxedHeaderBytes']])+b'\xe9'+(target-_rva(entry['rva'])-9).to_bytes(4,'little',signed=True)
        _expect(body,expected,'adjustor.'+name)
    return dict(status='validated_conditional_selected_generic_adjustor_cells',evidenceBoundary='conditional',executionBoundary='unobserved',
        selectedCellCount=len(rows),finiteEntryProgramBytes=9*len(rows),receiverRecipe=spec['receiverRecipe'],cellBoundary=spec['cellBoundary'],
        leafBoundary=spec['leafBoundary'],unresolved=['logical-adjustor-table-extent-and-runtime-index-validity',
            'incoming-boxed-receiver-context-and-generic-sharing','runtime-invoker-or-adjustor-selection-and-execution'])


def validate_selected_generic_adjustor_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    """Gate the explicit pair before opening native tables."""
    if gameassembly is None or metadata is None:return dict(status='missing',evidenceBoundary='unresolved',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.generic-adjustor')
    return validate_generic_adjustor_rules(image,contract['genericAdjustorRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
