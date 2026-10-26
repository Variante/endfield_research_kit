"""Stored bool/nint GetAsType ordinary candidates; adjustors stay opaque.

The selected primitive MethodSpecs are kept distinct even when their argument
carrier is identical. Complete ordinary candidate programs request GetObject,
context-Type lookup and unboxing, then read byte->AL or qword->RAX. Incoming
runtime context, boxing compatibility, pointer validity, actual values and
generic sharing are not inferred from stored registration membership.
"""
from __future__ import annotations
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity
from scripts.game_data.ifix_vm_call_scalar_rules import _generic_definition
from scripts.game_data.ifix_vm_generic_bridge_rules import _body, validate_generic_bridge_rules


class GenericScalarGetRuleError(ValueError):
    """A scalar-context candidate lacks a bounded native witness."""


def _need(ok: bool,detail: str) -> None:
    if not ok:raise GenericScalarGetRuleError('generic-scalar-get.'+detail)


_REFS={'getObject':'genericBridgeRules.getObjectMethod','contextPrepare':'genericBridgeRules.helpers.contextPrepare',
 'contextType':'genericBridgeRules.helpers.contextType','unboxAddress':'objectConversionRules.helpers.unboxAddress'}
_KINDS={'bool':2,'nint':0x18}
_CLAIMS=dict(schema='endfield.ifix-vm-generic-scalar-get-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
 definitionRef='callScalarRules.genericDefinition',helperRefs=_REFS,argumentTypes=['bool','nint'],
 contextBoundary='exact-stored-nonbyref-primitive-MethodSpecs-kept-distinct;raw-byref-contexts-retained-separately-without-candidate-program-claim;incoming-runtime-context-and-sharing-unobserved',
 adjustorBoundary='nonnegative-index-retained-undereferenced;no-adjustor-table-extent-or-runtime-selection-claim',
 rules={'ordinaryProgram':'optional-context-prepare;GetObject(Call,int-offset,zero-hidden-context);save-object;contextType(first-context-word);unboxAddress(saved-object,queried-Type);bool-byte-to-AL-without-normalization-or-nint-qword-to-RAX'},
 helperBoundary='normal-request-return-with-valid-readable-returned-pointer-is-conditional;Type-unbox-boxing-compatibility-helper-mutation-native-EH-and-execution-unobserved',
 absenceBoundary='this-group-selects-stored-bool-and-nint-contexts-only;zero-other-exact-contexts-is-not-no-possible-runtime-code')


def _contexts(image: Any,definition: dict,selections: list) -> dict[str,int]:
    pe,md,reg=image.pe,image.metadata,image.registration
    _need(type(selections)is list and all(type(r)is dict for r in selections)
      and [r.get('argumentType')for r in selections]==list(_KINDS),'ordered selected primitive contexts required')
    for name in ('methodSpecsCount','genericMethodTableCount','genericInstsCount'):
        _need(type(reg[name])is int and 0<reg[name]<=2_000_000,'bounded registration count required: '+name)
    specs=pe.bytes_at_va(_rva(reg['methodSpecs']),reg['methodSpecsCount']*12)
    selected={n:[]for n in _KINDS};byref={n:[]for n in _KINDS}
    _need(len(specs)==reg['methodSpecsCount']*12,'MethodSpec extent differs')
    for i,(method,cls,inst)in enumerate(struct.iter_unpack('<iii',specs)):
        if method!=definition['methodIndex']:continue
        _need(cls==-1 and 0<=inst<reg['genericInstsCount'],'GetAsType context carrier differs')
        args=image.instantiations.resolve(inst).arguments;_need(len(args)==1,'GetAsType context arity differs')
        raw=bytes.fromhex(args[0].raw_type_record_hex);_need(len(raw)==16 and pe.bytes_at_va(args[0].type_pointer_va,16)==raw,'registered argument carrier differs')
        for name,kind in _KINDS.items():
            if raw[10]!=kind:continue
            _need(runtime_type_name(pe,md,args[0].type_pointer_va)==name,'primitive argument identity differs')
            (byref if raw[11]&0x20 else selected)[name].append(dict(methodSpecIndex=i,classInst=-1,methodInst=inst,
              methodSpecRawHex=specs[i*12:i*12+12].hex().upper(),argumentRawHex=raw.hex().upper()))
    for row in selections:
        name=row['argumentType']
        _need(row.get('contexts')==selected[name]and bool(row['contexts'])
          and row.get('byrefContexts')==byref[name],'complete distinct primitive context declarations differ: '+name)
    code=image.mapper.code_registration_summary(pe,image.code_registration)
    for name in ('genericMethodPointersCount','invokerPointersCount'):
        _need(type(code[name])is int and 0<=code[name]<=2_000_000,'bounded code registration count required: '+name)
    table=pe.bytes_at_va(_rva(reg['genericMethodTable']),reg['genericMethodTableCount']*16)
    _need(len(table)==reg['genericMethodTableCount']*16,'generic table extent differs');candidates={n:[]for n in _KINDS}
    owners={r['methodSpecIndex']:n for n,rows in selected.items()for r in rows}
    for i,(spec,method,invoker,adjustor)in enumerate(struct.iter_unpack('<iiii',table)):
        _need(0<=spec<reg['methodSpecsCount'],'generic table MethodSpec index outside extent')
        if spec not in owners:continue
        _need(0<=method<code['genericMethodPointersCount']and -1<=invoker<code['invokerPointersCount']and adjustor>=0,'ordinary pointer/invoker index or retained nonnegative adjustor differs')
        candidates[owners[spec]].append(dict(tableIndex=i,methodSpecIndex=spec,indices=[method,invoker,adjustor],tableRecordHex=table[i*16:i*16+16].hex().upper()))
    pointers={}
    for row in selections:
        name=row['argumentType'];_need(row.get('candidates')==candidates[name]and len(candidates[name])==1,'exact one ordinary candidate declaration differs: '+name)
        pointer=pe.u64_at_va(_rva(code['genericMethodPointers'])+candidates[name][0]['indices'][0]*8);_need(pointer!=0,'null ordinary candidate pointer');pointers[name]=pointer
    return pointers


def _program(name: str,at: int,targets: dict) -> bytes:
    out=bytearray()
    parts=('48895c24084889742410574883ec204983783800498bf88bda488bf17508498bc8',
      ('call','contextPrepare'),'4533c08bd3488bce',('call','getObject'),'488b4f38488bd8488b09',
      ('call','contextType'),'488bd0488bcb',('call','unboxAddress'),'488b5c2430488b742438',
      '8a00'if name=='bool'else '488b00','4883c4205fc3')
    for part in parts:
        if isinstance(part,str):out.extend(bytes.fromhex(part));continue
        _,target=part;out.append(0xe8);out.extend((targets[target]-(at+len(out)+4)).to_bytes(4,'little',signed=True))
    return bytes(out)


def validate_generic_scalar_get_rules(image: Any,spec: dict,contract: dict,extents: dict) -> dict:
    """Authenticate ordinary membership/programs without selecting adjustors."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/claims/boundaries')
    validate_generic_bridge_rules(image,contract['genericBridgeRules'],contract,extents)
    definition=_ref(contract,spec['definitionRef']);_generic_definition(image,definition)
    selections=spec.get('selections');pointers=_contexts(image,definition,selections);targets={}
    for name,path in _REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);count=row.get('bodyBytes',row.get('byteCount'));_need(type(count)is int and 0<count<=65536,'helper request extent differs')
        _hash(image.pe.bytes_at_va(image.pe.image_base+at,count),row,'generic-scalar-get.'+name,method='bodyBytes'in row);targets[name]=at
        if name=='getObject':_identity(image,row,('IFix.Core.Call','GetObject',['int'],'object',False),'generic-scalar-get.GetObject',extents)
    programs=[]
    for row in selections:
        name=row['argumentType'];at,raw=_body(image,row['candidateProgram'],extents,'GetAsType-'+name)
        _need(pointers[name]==image.pe.image_base+at,'ordinary pointer and complete program differ: '+name);_expect(raw,_program(name,at,targets),'GetAsType-'+name)
        programs.append(dict(argumentType=name,storedContextCount=len(row['contexts']),excludedByrefContextCount=len(row['byrefContexts']),
          ordinaryCandidateCount=len(row['candidates']),completeProgramBytes=len(raw)))
    return dict(status='validated_conditional_stored_generic_scalar_get_candidates',evidenceBoundary='conditional',executionBoundary='unobserved',
      programs=programs,rules=spec['rules'],contextBoundary=spec['contextBoundary'],adjustorBoundary=spec['adjustorBoundary'],
      unresolved=['incoming-runtime-context-versus-stored-MethodSpecs-and-generic-sharing','nonnegative-adjustor-table-and-selection',
        'GetObject-Type-query-unbox-result-boxing-compatibility-and-returned-pointer-validity','helper-mutation-native-EH-and-actual-values'])


def validate_selected_generic_scalar_get_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',evidenceBoundary='unresolved',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,evidenceBoundary='unresolved',detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.generic-scalar-get')
    return validate_generic_scalar_get_rules(image,contract['genericScalarGetRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
