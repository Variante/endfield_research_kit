"""Authenticate conditional exception-adjacent native programs, offline only.

Each complete function copies incoming RDX to its frame register, reads the
pointer stored at a declared frame home, dereferences that pointer, and reads
the candidate object's first word through an exact anonymous leaf. A stored
named class-type usage cell is passed to the inherited usage resolver. The
resolver result is the first argument of an anonymous relation request, with
the candidate's saved first word second. AL selects the continuation. This is
not a registered Object.GetType or System.Type.IsAssignableFrom invocation;
the relation's concrete runtime result remains unobserved.

The first program tests System.Exception. A nonzero AL requests a push into
the container at the declared frame offset and returns literal zero. The
second tests IFix.Core.RuntimeException first, returning zero on its push
path; a failed first query rereads the candidate and tests System.Exception,
returning one on that push path. Both mismatch paths reread the pointer,
store it in the declared scratch home, and request an anonymous transfer with
the address of that home and an uninterpreted stored context address. On a
normal return they retain the transfer's RAX; transfer and unwinding are open.

The exact push leaf reads a signed Int32 depth, stores its pointer argument at
container+signExtend(depth)*8, then increments the depth storage as Int32. The
increment occurs after the pointer store: if these locations overlap, an
old-depth-plus-one interpretation is unsupported. It clears no element.

Finite programs cover both complete function ranges, branches, calls and
returns. Native range adjacency is checked against the named Execute body;
adjacency does not establish catch delivery or the incoming frame association.
Named type carriers reject byref and nonclass records. Runtime selection,
class resolution/relation, valid storage, read stability, alias effects,
exception delivery, return-code interpretation and execution stay unobserved.
Per-build native declarations live in the reviewed contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity
from scripts.game_data.ifix_vm_reference_update_rules import _type_pointer
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class ExceptionFuncletRuleError(ValueError):
    """An adjacent native continuation lacks its conditional witness."""


_HELPER_REFS={'usageResolve':'objectConversionRules.helpers.usageResolveThunk'}
_CELL_REFS={'exceptionType':'exceptionDispatchRules.usageCells.exceptionType',
    'runtimeExceptionType':'runtimeExceptionRules.usageCells.runtimeExceptionType'}
_CELL_TYPES={'exceptionType':'System.Exception','runtimeExceptionType':'IFix.Core.RuntimeException'}
_OWN_HELPERS={'objectWordRead','relationThunk','relationRequest','exceptionStorePush','unmatchedTransfer'}
_FRAME_HOMES={'singlePointer','doublePointer','container','singleScratch','doubleScratch'}
_CLAIMS={'schema':'endfield.ifix-vm-exception-funclet-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
    'executeRef':'consumer','helperRefs':_HELPER_REFS,'usageRefs':_CELL_REFS,
    'placementBoundary':'adjacent-native-ranges-only;incoming-frame-association-and-EH-delivery-unobserved',
    'candidateRecipe':'incoming-RDX-frame;read-pointer-home;dereference-pointer;read-object-first-word',
    'queryRecipe':'usageResolve(address-of-named-class-type-cell);relationRequest(resolver-result,saved-object-first-word);test-AL',
    'singleRecipe':'Exception-query;nonzero-AL:push-reread-pointer-and-return-zero;zero-AL:unmatched-transfer',
    'doubleRecipe':'RuntimeException-query;nonzero-AL:push-reread-pointer-and-return-zero;zero-AL:reread-and-Exception-query;nonzero-AL:push-reread-pointer-and-return-one;zero-AL:unmatched-transfer',
    'pushRecipe':'signed-Int32-depth-read;store-pointer-at-container+signExtend(depth)*8;increment-depth-storage-as-Int32-after-store;no-element-clear',
    'unmatchedRecipe':'reread-pointer;store-scratch;transfer(address-of-scratch,address-of-uninterpreted-context);normal-return-keeps-transfer-RAX',
    'queryBoundary':'anonymous-object-word-read-and-anonymous-relation-request;registered-Object.GetType-or-Type.IsAssignableFrom-not-inferred',
    'storageBoundary':'valid-frame-pointer-home-candidate-container-and-scratch-storage;normal-helper-returns-without-unmodelled-mutation',
    'aliasBoundary':'repeated-pointer-reads-not-atomic;pointer-store-may-alias-depth-before-increment;storage-overlap-and-helper-mutation-unobserved',
    'runtimeBoundary':'class-resolution-relation-and-transfer-outcomes-EH-entry-return-code-interpretation-and-execution-unobserved',
    'contextBoundary':'uninterpreted-stored-native-transfer-context-address;framework-format-and-delivery-unobserved',
    'pointerBytes':8,'depthBytes':4}


def _need(ok: bool,detail: str) -> None:
    if not ok:raise ExceptionFuncletRuleError('exceptionFunclets.'+detail)


def _anchor(image: Any,contract: dict,extents: dict[int,int]) -> int:
    row=_ref(contract,'consumer');at=_identity(image,row,('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    md=image.metadata;methods=[m for t in md.types if md.type_full_name(t)=='IFix.Core.VirtualMachine'
        for m in md.methods_for(t)if m.token==_rva(row['token'])];_need(len(methods)==1,'one owner-qualified Execute token required');method=methods[0]
    for index,typ in [(p.type_index,t)for p,t in zip(md.parameters_for(method),_EXECUTE_TYPES)]+[(method.return_type,'IFix.Core.Value*')]:
        _carrier(image,_type_pointer(image,index),typ)
    return at+row['bodyBytes']


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    result={}
    for name,path in _CELL_REFS.items():
        row=_ref(contract,path);at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(type(row.get('usageTag'))is int and row['usageTag']==1 and row.get('identity')==_CELL_TYPES[name]
            and raw==bytes.fromhex(row['rawHex']),'named usage declaration/bytes differ: '+name)
        index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='ifix.funclet.type',offset=at)
        _carrier(image,_type_pointer(image,index),_CELL_TYPES[name]);result[name]=at
    row=spec['unmatchedContext'];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
    _need(set(row)=={'cellRva','rawHex','evidenceBoundary'}and row['evidenceBoundary']=='structuralOnly'
        and len(raw)==8 and raw==bytes.fromhex(row['rawHex']),'opaque context bytes/boundary differ')
    result['unmatchedContext']=at;return result


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int],spec: dict) -> bytes:
    p=_Program(at)
    for token in _PROGRAMS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='home':p.add(args[0]);p.add(spec['frameHomes'][args[1]].to_bytes(4,'little',signed=True))
        else:_need(False,'unknown finite token')
    return p.finish()


def validate_exception_funclet_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    """Authenticate selected ranges after the parent's explicit native gate."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/boundary')
    _need(set(spec['functions'])==set(_PROGRAMS)and set(spec['helpers'])==_OWN_HELPERS,'function/helper declaration set differs')
    homes=spec['frameHomes'];_need(set(homes)==_FRAME_HOMES and all(type(x)is int and 0<=x<=0x7fffffff for x in homes.values()),'frame home declaration differs')
    depth=spec['pushDepthOffset'];_need(type(depth)is int and 0<=depth<128,'push depth declaration differs')
    adjacent=_anchor(image,contract,extents);targets={};bodies={}
    for name,row in spec['functions'].items():
        at=_rva(row['rva']);count=row['byteCount'];_need(type(count)is int and count>0 and extents.get(image.pe.image_base+at)==image.pe.image_base+at+count,'exact adjacent extent differs')
        raw=image.pe.bytes_at_va(image.pe.image_base+at,count);_hash(raw,row,name);targets[name]=at;bodies[name]=raw
    _need(targets['single']==adjacent and targets['double']==targets['single']+len(bodies['single']),'range adjacency differs')
    for name,row in {**spec['helpers'],**{n:_ref(contract,path)for n,path in _HELPER_REFS.items()}}.items():
        at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,name);targets[name]=at
        if name in ('relationRequest','unmatchedTransfer'):_need(row.get('evidenceBoundary')=='unresolved-runtime-result','request outcome promoted')
        elif name=='objectWordRead':_expect(raw,bytes.fromhex('488b01c3'),'objectWordRead')
        elif name=='exceptionStorePush':_expect(raw,bytes.fromhex('486341')+bytes([depth])+bytes.fromhex('488914c1ff41')+bytes([depth])+bytes.fromhex('c3'),'exceptionStorePush')
    thunk=spec['helpers']['relationThunk'];at=targets['relationThunk']
    _expect(image.pe.bytes_at_va(image.pe.image_base+at,thunk['byteCount']),bytes.fromhex('e9')+(targets['relationRequest']-at-5).to_bytes(4,'little',signed=True),'relationThunk')
    cells=_cells(image,spec,contract)
    for name,raw in bodies.items():_expect(raw,_program(name,targets[name],targets,cells,spec),name+'.full-finite-program')
    return {'status':'validated_conditional_exception_funclet_recipes','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        **{k:spec[k]for k in ('candidateRecipe','queryRecipe','singleRecipe','doubleRecipe','pushRecipe','unmatchedRecipe',
            'placementBoundary','queryBoundary','storageBoundary','aliasBoundary','runtimeBoundary','contextBoundary')},
        'frameHomes':homes,'pushDepthOffset':depth,'unresolved':['incoming-frame-association-and-native-EH-delivery',
            'runtime-class-resolution-and-relation-AL','runtime-transfer-throw-unwind-and-return-RAX',
            'container-depth-pointer-store-alias-and-bounds','repeated-read-stability-and-helper-mutation','return-code-interpretation-and-execution']}


def validate_selected_exception_funclet_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths required'}
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.exceptionFunclets')
    return validate_exception_funclet_rules(image,contract['exceptionFuncletRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))


_PROGRAMS={
 'single':['48895424105355574883ec50488bea',('home','488b9d','singlePointer'),'488b0b',('call','objectWordRead'),
    '488bf8',('rip','488d0d','exceptionType'),('call','usageResolve'),'488bd7488bc8',('call','relationThunk'),
    '84c0741c488b13',('home','488d8d','container'),('call','exceptionStorePush'),'9048b80000000000000000eb1e488b03',
    ('home','488985','singleScratch'),('rip','488d15','unmatchedContext'),('home','488d8d','singleScratch'),
    ('call','unmatchedTransfer'),'904883c4505f5d5bc3cc'],
 'double':['48895424105355574883ec50488bea',('home','488bbd','doublePointer'),'488b0f',('call','objectWordRead'),
    '488bd8',('rip','488d0d','runtimeExceptionType'),('call','usageResolve'),'488bd3488bc8',('call','relationThunk'),
    '84c0741c488b17',('home','488d8d','container'),('call','exceptionStorePush'),'9048b80000000000000000eb60488b0f',
    ('call','objectWordRead'),'488bd8',('rip','488d0d','exceptionType'),('call','usageResolve'),'488bd3488bc8',
    ('call','relationThunk'),'84c0741c488b17',('home','488d8d','container'),('call','exceptionStorePush'),
    '9048b80100000000000000eb1e488b07',('home','488985','doubleScratch'),('rip','488d15','unmatchedContext'),
    ('home','488d8d','doubleScratch'),('call','unmatchedTransfer'),'904883c4505f5d5bc3cc']}
