"""Authenticate the named CreateBridge receiver dispatcher and slot fallback.

The dispatcher reads an anonymous class word, subtracts its reviewed selector
base and uses an unsigned range check before its jump table. Every admitted
route is a complete direct-call arm: receiver, field count, field Types and
type index retain their register arguments; vTable, slots and VM are copied
from the input stack in their declared order; the hidden MethodInfo is zero.
All arms join the same return epilogue. Table order, all intervening bytes and
the complete native function extent are authenticated.

Each direct target is identified by metadata image, named type, declaration,
token and registered method pointer. Its unique static interface-offset row
and effective vtable entry must select that same CreateBridge method. Nested
array carriers, primitive/class kinds, byref flags and static/generic flags
are checked; repeated generated type names cannot select a target alone.

The out-of-range arm forwards the same authored arguments to the complete
slot-one fallback. That program prepares the receiver class, scans its live
interface-offset records for the named WrappersManager type, and either forms
the vtable pair using signed Int32(offset+1), or requests slot one from an
opaque resolver. Both paths join the same pair load. The first pair word is
called and the second becomes the hidden MethodInfo argument; all six authored
arguments are restored before this call and the saved registers are restored
afterward. The interface preparation and resolver are requests only.

Static declarations and local forwarding do not identify a live manager,
class selector, interface array, pair, or generated bridge result. Valid
stable storage, normal helper returns, framework outcomes, aliases, generated
bridge execution and runtime selection remain conditional. Native addresses,
hashes and implementation inventories belong to the reviewed contract.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect
from scripts.game_data.ifix_vm_wrapper_dispatch_rules import _raw,_rel,_slice,_interface_slot
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier


class BridgeDispatchRuleError(ValueError):
    """A bridge dispatcher declaration lacks its selected native witness."""


_PARAMS=['int','int[]','int','int[]','int[]','IFix.Core.VirtualMachine']
_NAMES=['fieldNum','fieldTypes','typeIndex','vTable','slots','virtualMachine']
_RETURN='IFix.Core.AnonymousStorey'
_CLAIMS=dict(schema='endfield.ifix-vm-bridge-dispatch-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
    dispatcherRef='anonymousStoreyRules.helpers.bridgeRequest',interfaceMethodRef='anonymousStoreyRules.bridgeMethod',
    interfaceRef='wrapperDelegateDispatch.interface',selectorRef='wrapperDelegateDispatch.selection',
    classPrepareRef='chainFieldRules.helpers.classPrepare',resolverRef='wrapperDelegateDispatch.fallback',
    interfaceSlot=1,argumentOrder=['receiver']+_NAMES,
    directRecipe='preserve-register-arguments;copy-vTable-slots-VM-in-order;hidden-MethodInfo-zero;common-return-join',
    fallbackRecipe='named-interface-offset-or-slot-one-resolver;pair-first-word-call;pair-second-word-hidden-MethodInfo;restore-six-authored-arguments',
    selectorMeaning='anonymous-runtime-class-word',runtimeSelection='unobserved',
    storageBoundary='valid-stable-receiver-class-interface-records-stack-and-pair-storage;normal-helper-returns-without-unmodelled-mutation',
    runtimeBoundary='class-preparation-resolver-pair-selection-generated-bridge-result-aliases-and-execution-unobserved')


def _need(ok: bool,detail: str) -> None:
    if not ok:raise BridgeDispatchRuleError('bridgeDispatch.'+detail)


def _type(image: Any,index: int,expected: str) -> None:
    _need(type(index)is int and 0<=index<image.registration['typesCount'],'registered carrier index differs')
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
    _carrier(image,pointer,expected)
    _need(runtime_type_name(image.pe,image.metadata,pointer)==expected,'named carrier differs: '+expected)


def _method(image: Any,row: dict,*,interface: bool=False) -> Any:
    md=image.metadata
    _need(row.get('method')=='CreateBridge' and row.get('parameterTypes')==_PARAMS and row.get('parameterNames')==_NAMES
        and row.get('returnType')==_RETURN,'unsupported named method declaration')
    index=row['definitionIndex'];_need(type(index)is int and 0<=index<len(md.types),'definition outside metadata')
    owner=md.types[index]
    _need(md.type_full_name(owner)==row['type'] and md.string(md.images[image.owners[index]].name_index)==row['image']
        and not owner.bitfield&1 and owner.generic_container_index==-1,'image-qualified reference owner differs')
    methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='CreateBridge' and m.parameter_count==len(_PARAMS)]
    _need(len(methods)==1,'one image-qualified CreateBridge declaration required');m=methods[0]
    params=md.parameters_for(m)
    _need([md.string(p.name_index)for p in params]==_NAMES and m.index==row['methodIndex'] and m.token==_rva(row['token'])
        and type(row['slot'])is int and m.slot==row['slot'] and not m.flags&0x10 and m.flags&0x40 and m.generic_container_index==-1,
        'named argument order/token/slot/static/generic differs')
    for param,typ in zip(params,_PARAMS):_type(image,param.type_index,typ)
    _type(image,m.return_type,_RETURN);pointer=image.method_pointer_va(m)
    if interface:
        _need(owner.flags&0x20 and m.flags&0x400 and pointer==0 and row['type']=='IFix.Core.WrappersManager' and row['slot']==1,
            'abstract named interface slot differs')
    else:
        _need(not owner.flags&0x20 and not m.flags&0x400 and row['type']=='IFix.WrappersManagerImpl'
            and pointer==image.pe.image_base+_rva(row['rva']),'registered implementation pointer differs')
    return m


def _fallback_program(at: int,cell: int,prepare: int,resolver: int) -> bytes:
    return (bytes.fromhex('48895c240848896c24104889742418574883ec40498b18418be9')
        +_rel(bytes.fromhex('488b35'),at+26,cell)+bytes.fromhex('488bcb498bf8')+_rel(b'\xe8',at+39,prepare)
        +bytes.fromhex('440fb7833001000033c9448d490166413bc8731d488b93b00000000fb7c14803c0483934c27472664103c966413bc872ea458bc1488bd6488bcf')
        +_rel(b'\xe8',at+102,resolver)
        +bytes.fromhex('4c8b108bd5488b4008488bcf448b4c24784c8b4424704889442438488b8424900000004889442430488b8424880000004889442428488b842480000000488944242041ffd2488b5c2450488b6c2458488b7424604883c4405fc30fb7c94803c98b44ca084103c148984883c01448c1e0044803c3eb8a'))


def validate_bridge_dispatch_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    _need(all(type(spec.get(k))is type(v) and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/claim/boundary')
    parent=_ref(contract,spec['dispatcherRef']);d=_raw(image,parent,extents);db=_rva(parent['rva'])
    fallback=spec['fallback'];_need(fallback['name']=='slotOneFallback','fallback label differs');f=_raw(image,fallback,extents);fb=_rva(fallback['rva'])
    inherited=_ref(contract,spec['interfaceRef']);interface=spec['interface'];_method(image,interface['method'],interface=True)
    cell=inherited['typeCell'];at=_rva(cell['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
    _need(raw==bytes.fromhex(cell['rawHex']),'named interface usage bytes differ')
    index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='ifix.bridge.interface',offset=at)
    _need(index==inherited['registeredTypeIndex']==interface['registeredTypeIndex'],'interface registered index differs');_type(image,index,'IFix.Core.WrappersManager')
    pointer=image.pe.u64_at_va(_rva(image.registration['types'])+index*8)
    _need(image.pe.u64_at_va(pointer)==interface['method']['definitionIndex']==inherited['method']['definitionIndex'],'interface definition differs')
    method=_ref(contract,spec['interfaceMethodRef'])
    _need(method.get('type')=='IFix.Core.WrappersManager' and method.get('method')=='CreateBridge' and method.get('parameterCount')==6
        and method.get('parameterTypes')==_PARAMS and method.get('returnTypeName')==_RETURN and method.get('static')is False
        and method.get('generic')is False and method.get('virtualSlot')==1 and _rva(method['token'])==_rva(interface['method']['token']),
        'inherited named method differs')
    selection=spec['selection'];inherited_selection=_ref(contract,spec['selectorRef'])
    _need(all(type(selection.get(k))is int and selection[k]==inherited_selection[k] for k in ('classWordOffset','firstSelectorWord','entryCount')),
        'selector differs from inherited anonymous word')
    count,first,offset=selection['entryCount'],selection['firstSelectorWord'],selection['classWordOffset']
    _need(1<=count<=128 and 0<=first<(1<<31) and 0<=offset<(1<<31),'bounded anonymous selector differs')
    table,out,join=map(_rva,(selection['tableRva'],selection['fallbackRva'],selection['joinRva']))
    prefix=(bytes.fromhex('4055488bec4883ec50488b01448b90')+struct.pack('<I',offset)+bytes.fromhex('4181c2')+struct.pack('<i',-first)
        +bytes.fromhex('4183fa')+bytes([count-1])+_rel(bytes.fromhex('0f87'),db+30,out)+bytes.fromhex('4963c2')
        +_rel(bytes.fromhex('4c8d1d'),db+39,0)+bytes.fromhex('458b9483')+struct.pack('<I',table)+bytes.fromhex('4d03d341ffe2'))
    _need(_slice(d,db,db,len(prefix))==prefix,'receiver/range/table program differs')
    cases=spec['cases'];_need(len(cases)==count and len({r['methodIndex']for r in cases})==count,'missing/duplicate implementation cases')
    cursor=db+len(prefix);table_bytes=_slice(d,db,table,count*4)
    for ordinal,row in enumerate(cases):
        target=struct.unpack_from('<I',table_bytes,ordinal*4)[0]
        _need(type(row['selectorWord'])is int and row['selectorWord']==first+ordinal and _rva(row['caseRva'])==target==cursor,'case/table order differs')
        _method(image,row);_interface_slot(image,row,interface)
        arm=bytes.fromhex('488364243800488b45404889442430488b45384889442428488b45304889442420')+_rel(b'\xe8',cursor+33,_rva(row['rva']))
        _need(_slice(d,db,cursor,len(arm))==arm,'direct hidden argument/stack forwarding/call differs');cursor+=len(arm)
        if _slice(d,db,cursor,1)==b'\xeb':
            delta=join-cursor-2;_need(-128<=delta<=127 and _slice(d,db,cursor,2)==b'\xeb'+struct.pack('<b',delta),'short return join differs');cursor+=2
        else:
            _need(_slice(d,db,cursor,5)==_rel(b'\xe9',cursor,join),'near return join differs');cursor+=5
    _need(cursor==out,'unreviewed code between cases and fallback')
    shuffle=bytes.fromhex('488b45404889442440488b45384889442438488b4530488944243044894c2428448bca4c894424204c8bc1')+_rel(b'\xe8',out+43,fb)
    _need(out+len(shuffle)==join and _slice(d,db,out,len(shuffle))==shuffle,'fallback argument order/shuffle differs')
    _need(table==join+7 and _slice(d,db,join,7)==bytes.fromhex('4883c4505dc390') and table+count*4==db+len(d),'return/table/full extent differs')
    prepare=_ref(contract,spec['classPrepareRef']);_hash(image.pe.bytes_at_va(image.pe.image_base+_rva(prepare['rva']),prepare['byteCount']),prepare,'classPrepare')
    resolver=_ref(contract,spec['resolverRef'])['helpers']['slotResolver']
    _expect(f,_fallback_program(fb,at,_rva(prepare['rva']),_rva(resolver)),'slotOneFallback')
    return dict(status='validated_conditional_bridge_dispatch',evidenceBoundary='conditional',executionBoundary='unobserved',
        method='IFix.Core.WrappersManager.CreateBridge',interfaceSlot=1,directImplementationCount=count,argumentOrder=spec['argumentOrder'],
        directRecipe=spec['directRecipe'],fallbackRecipe=spec['fallbackRecipe'],storageBoundary=spec['storageBoundary'],runtimeBoundary=spec['runtimeBoundary'],
        unresolved=['runtime-wrapper-manager-and-anonymous-class-selector','live-interface-records-and-resolver-pair','generated-bridge-bodies-result-aliases-and-execution'])


def validate_selected_bridge_dispatch_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256')) and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.bridge-dispatch')
    return validate_bridge_dispatch_rules(image,contract['bridgeDispatchRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))
