"""Authenticate stored reference-context GetAsType pointer candidates.

The generic MethodDef has no ordinary entry pointer. Its exact, non-byref
object MethodSpec nevertheless has a stored ordinary pointer candidate.
This component bounds the method/invoker indices and retains a nonnegative
adjustor index without dereferencing that separate table or claiming its
extent. It deliberately does not use the shared no-adjustor decoder.

The complete candidate program preserves Call and signed offset, optionally
requests context preparation, requests GetObject with zero hidden context,
then obtains the first context word through contextType and tail-requests
referenceCast(savedObject, queriedType). GetObject's read/physical-clear
program is authenticated by genericBridgeRules. The incoming context is not
proven to be the stored MethodSpec, and the adjustor, sharing, Type/cast result,
storage, exceptions and actual invocation remain unobserved.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.ifix_vm_generic_bridge_rules import _body, validate_generic_bridge_rules
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect
from scripts.game_data.ifix_vm_call_scalar_rules import _generic_definition


class GenericReferenceGetRuleError(ValueError):
    """A stored generic candidate lacks its bounded native witness."""


_CLAIMS=dict(schema='endfield.ifix-vm-generic-reference-get-rules.v1',evidenceBoundary='conditional',
    executionBoundary='unobserved',definitionRef='callScalarRules.genericDefinition',
    helperRefs={'getObject':'genericBridgeRules.getObjectMethod',
        'contextPrepare':'genericBridgeRules.helpers.contextPrepare',
        'contextType':'genericBridgeRules.helpers.contextType',
        'referenceCast':'genericBridgeRules.helpers.referenceCast'},
    argumentTypes=['object'],
    contextBoundary='stored-exact-nonbyref-object-MethodSpec-and-ordinary-pointer-candidate;incoming-runtime-context-and-sharing-unobserved',
    adjustorBoundary='nonnegative-index-retained-undereferenced;no-adjustor-table-extent-or-runtime-selection-claim',
    programRecipe='optional-context-prepare;GetObject(Call,signed-offset,zero-hidden-context);save-object;contextType(first-context-word);tail-referenceCast(saved-object,queried-Type)',
    helperBoundary='typed-request-program-only;Type-query-cast-helper-mutation-native-EH-and-execution-unobserved')


def _need(ok: bool,detail: str) -> None:
    if not ok:raise GenericReferenceGetRuleError('generic-reference-get.'+detail)


def _candidate(image: Any,definition: dict,selection: dict) -> int:
    """Bound ordinary pointer membership without selecting an adjustor."""
    pe,reg=image.pe,image.registration
    wanted=selection.get('argumentType')
    _need(wanted=='object','unsupported reference context')
    counts={n:reg[n]for n in ('methodSpecsCount','genericMethodTableCount')}
    _need(all(type(n)is int and 0<n<=2_000_000 for n in counts.values()),'bounded table counts required')
    spec_at=_rva(reg['methodSpecs']);specs=pe.bytes_at_va(spec_at,counts['methodSpecsCount']*12)
    _need(len(specs)==counts['methodSpecsCount']*12,'MethodSpec extent differs')
    selected=[]
    for index,(method,cls,inst)in enumerate(struct.iter_unpack('<iii',specs)):
        if method!=definition['methodIndex']:continue
        _need(cls==-1 and type(inst)is int and 0<=inst<reg['genericInstsCount'],'GetAsType static context carrier differs')
        args=image.instantiations.resolve(inst).arguments
        _need(len(args)==1,'GetAsType context arity differs')
        raw=bytes.fromhex(args[0].raw_type_record_hex)
        _need(len(raw)==16,'context Type carrier extent differs')
        if not raw[11]&0x20 and runtime_type_name(pe,image.metadata,args[0].type_pointer_va)==wanted:
            _need(raw[10]==0x1c,'named reference raw carrier differs')
            selected.append((index,inst,raw))
    _need(len(selected)==1,'one exact nonbyref reference MethodSpec required')
    index,inst,raw=selected[0]
    _need(selection.get('methodSpecIndex')==index and selection.get('methodInst')==inst
        and selection.get('classInst')==-1 and selection.get('methodSpecRawHex')==specs[index*12:index*12+12].hex().upper()
        and selection.get('argumentRawHex')==raw.hex().upper(),'stored reference context declaration differs')
    code=image.mapper.code_registration_summary(pe,image.code_registration)
    _need(type(code['genericMethodPointersCount'])is int and 0<code['genericMethodPointersCount']<=2_000_000
        and type(code['invokerPointersCount'])is int and 0<=code['invokerPointersCount']<=2_000_000,
        'bounded ordinary method/invoker counts required')
    table=pe.bytes_at_va(_rva(reg['genericMethodTable']),counts['genericMethodTableCount']*16)
    _need(len(table)==counts['genericMethodTableCount']*16,'generic table extent differs')
    candidates=[]
    for table_index,(spec,method,invoker,adjustor)in enumerate(struct.iter_unpack('<iiii',table)):
        _need(0<=spec<counts['methodSpecsCount'],'generic table MethodSpec index outside extent')
        if spec!=index:continue
        _need(0<=method<code['genericMethodPointersCount'] and -1<=invoker<code['invokerPointersCount']
            and adjustor>=0,'ordinary method/invoker index or retained nonnegative adjustor differs')
        candidates.append((table_index,method,invoker,adjustor))
    _need(len(candidates)==1,'one stored ordinary pointer candidate required')
    table_index,method,invoker,adjustor=candidates[0]
    _need(selection.get('tableIndex')==table_index and selection.get('indices')==[method,invoker,adjustor]
        and selection.get('tableRecordHex')==table[table_index*16:table_index*16+16].hex().upper(),'candidate declaration differs')
    pointer=pe.u64_at_va(_rva(code['genericMethodPointers'])+method*8)
    _need(pointer!=0,'ordinary pointer candidate is null')
    return pointer


def _program(at: int,targets: dict) -> bytes:
    out=bytearray()
    for part in ('48895c24084889742410574883ec204983783800498bf88bda488bf17508498bc8',
        ('call','contextPrepare'),'4533c08bd3488bce',('call','getObject'),
        '488b4f38488bd8488b09',('call','contextType'),
        '488bd0488bcb488b5c2430488b7424384883c4205f',('tail','referenceCast')):
        if isinstance(part,str):out.extend(bytes.fromhex(part));continue
        kind,name=part;out.append(0xe8 if kind=='call'else 0xe9)
        out.extend((targets[name]-at-len(out)-4).to_bytes(4,'little',signed=True))
    return bytes(out)


def validate_generic_reference_get_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    """Authenticate a complete stored candidate, without runtime selection."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/claim/boundary')
    # The selected wrapper must authenticate the named GetObject program and
    # context helper boundaries too, rather than rely on parent call order.
    validate_generic_bridge_rules(image,contract['genericBridgeRules'],contract,extents)
    definition=_ref(contract,spec['definitionRef']);_generic_definition(image,definition)
    selections=spec.get('selections',[])
    _need([r.get('argumentType')for r in selections]==spec['argumentTypes'],'complete ordered reference contexts required')
    pointers=[_candidate(image,definition,row)for row in selections]
    at,raw=_body(image,spec['candidateProgram'],extents,'GetAsType-reference-candidate')
    _need(all(pointer==image.pe.image_base+at for pointer in pointers),'stored pointers and complete shared program differ')
    targets={}
    for name,path in spec['helperRefs'].items():
        row=_ref(contract,path);where=_rva(row['rva']);count=row.get('bodyBytes',row.get('byteCount'))
        _need(type(count)is int and 0<count<=65536,'helper request extent differs')
        _hash(image.pe.bytes_at_va(image.pe.image_base+where,count),row,'GetAsType.'+name,method='bodyBytes'in row);targets[name]=where
    _expect(raw,_program(at,targets),'GetAsType-reference-candidate')
    return dict(status='validated_conditional_stored_generic_reference_get_candidates',evidenceBoundary='conditional',executionBoundary='unobserved',
        programRecipe=spec['programRecipe'],contextBoundary=spec['contextBoundary'],adjustorBoundary=spec['adjustorBoundary'],
        completeProgramBytes=len(raw),unresolved=['runtime-context-and-generic-sharing','adjustor-table-selection-and-program',
            'Type-query-cast-results-and-helper-mutation','Call-storage-native-EH-and-actual-execution'])


def validate_selected_generic_reference_get_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    """Gate the explicit pair before opening native tables."""
    if gameassembly is None or metadata is None:return dict(status='missing',evidenceBoundary='unresolved',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.generic-reference-get')
    return validate_generic_reference_get_rules(image,contract['genericReferenceGetRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
