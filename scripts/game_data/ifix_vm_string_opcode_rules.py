"""Authenticate Ldstr's conditional string-table push request.

The selected caller reads VM.internStrings with the signed Int32 operand.
It loads a typed string RuntimeTypeHandle cell and requests the named static
GetTypeFromHandle. That returned Type and the selected table object are
forwarded to PushObject with the incoming evaluation base, top and managed
array. The ordinary push tail advances one slot and commits top before the
inherited PC tail. No managed clear is issued in this caller.

The finite programs establish all caller instructions and joins. Named
metadata authenticates string[] storage, the nested non-byref string carrier,
the handle usage, GetTypeFromHandle and PushObject signatures. The parent
owns loader table order and PushObject semantics. Actual table contents and
bounds, incoming loop state/storage, Type/helper outcomes, aliases, GC and
execution remain unobserved. A table index is not a receipt that the patch's
stored string was loaded or that the destination tag became Object.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults,runtime_type_field_offsets,runtime_type_name
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_slice,_identity
from scripts.game_data.ifix_vm_object_opcode_rules import _carrier,_signature
from scripts.game_data.ifix_vm_conversion_opcode_rules import _value_layout
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry


class StringOpcodeRuleError(ValueError):
    """A selected string caller lacks its reviewed native witness."""


_HELPER_REFS={'nullCheck':'negativeFieldRules.helpers.nullCheck','arrayFetch':'initobjTypeOperand.consumerRowFetchHelper',
 'classInitialize':'objectConversionRules.helpers.classInitialize','advancePointer':'basicOpcodeRules.helpers.advancePointer'}
_METHOD_REFS={'typeFromHandle':'genericDelegateFactoryRules.methods.getTypeFromHandle','pushObject':'reflectionDispatch.methods.evaluationPush'}
_METHODS={'typeFromHandle':('System.Type','GetTypeFromHandle',['System.RuntimeTypeHandle'],'System.Type',True),
 'pushObject':('IFix.Core.EvaluationStackOperation','PushObject',['IFix.Core.Value*','IFix.Core.Value*','object[]','object','System.Type'],'void',True)}
_TAIL_REFS={n:'basicOpcodeRules.sharedWindows.'+n for n in ('pushAdvance','pushTopCommit','pcAdvance','loopState','slotWidth')}
_CLAIMS={'schema':'endfield.ifix-vm-string-opcode-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'opcode':'Ldstr','helperRefs':_HELPER_REFS,'methodRefs':_METHOD_REFS,'tailRefs':_TAIL_REFS,
 'systemTypeRef':'referenceAddressRules.usageCells.systemType','pushForwardRef':'referenceAddressRules.joins.pushForward',
 'runtimeField':'internStrings','operandMeaning':'signed-runtime-internStrings-index',
 'effect':'fetch-internStrings;GetTypeFromHandle(string-handle);PushObject(base,top,managed,selected-object,returned-Type);advance-and-commit-top',
 'stackDeltaSlots':1,'normalNextInstructionDelta':1,'managedClearBoundary':'no-explicit-managed-clear-in-selected-caller',
 'typeBoundary':'stored-string-handle-and-named-static-request;returned-Type-and-PushObject-result-unobserved',
 'storageBoundary':'consistent-loop-state-valid-stable-storage-and-normal-nonmutating-helper-return',
 'aliasBoundary':'runtime-storage-overlap-table-contents-helper-mutation-and-GC-unobserved',
 'fileTableBoundary':'parent-authenticated-loader-table-order;runtime-table-object-row-and-string-materialization-unobserved'}
_PROGRAMS={'Ldstr':('488b5f50498bce',('call','nullCheck'),'49637e04488bcb',('call','nullCheck'),'488bd7488bcb',('call','arrayFetch'),
 '488bf8',('rip','488b1d','stringHandle'),('jump','pushRequest')),
 'pushRequest':(('rip','488b0d','systemType'),('call','classInitialize'),'33d2488bcb',('call','typeFromHandle'),
 '4c896c242848894424204c8bcf4d8bc7498bd4488b8c2410040000',('call','pushObject'),('jump','pushForward'))}


def _need(ok: bool,detail: str) -> None:
    if not ok:raise StringOpcodeRuleError('stringOpcode.'+detail)


def _field(image: Any,spec: dict) -> None:
    md=image.metadata;owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.VirtualMachine']
    _need(len(owners)==1 and not owners[0].bitfield&1 and spec['field']=={'type':'string[]','offset':80,'static':False},'field declaration/owner differs')
    fields=[f for f in md.fields_for(owners[0])if md.string(f.name_index)=='internStrings'];_need(len(fields)==1,'named internStrings field differs')
    offsets=runtime_type_field_offsets(md,image.pe,image.registration,owners[0].index);f=fields[0]
    ptr=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8);_carrier(image,ptr,'string[]')
    _need(offsets.get('internStrings')==80 and runtime_type_name(image.pe,md,ptr)=='string[]'
        and not int.from_bytes(image.pe.bytes_at_va(ptr,16)[8:10],'little')&0x10,'internStrings carrier/layout differs')


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    result={}
    for name,row,tag,typ in [('stringHandle',spec['stringHandle'],2,'string'),('systemType',_ref(contract,spec['systemTypeRef']),1,'System.Type')]:
        at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(raw==bytes.fromhex(row['rawHex']) and row.get('usageTag')==tag and row.get('identity')==typ,'typed cell declaration differs: '+name)
        index=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='stringOpcode.'+name,offset=at)
        ptr=image.pe.u64_at_va(_rva(image.registration['types'])+index*8);_carrier(image,ptr,typ)
        _need(runtime_type_name(image.pe,image.metadata,ptr)==typ,'named cell differs: '+name);result[name]=at
    return result


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in _PROGRAMS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='jump':p.rip('e9',targets[args[0]])
        else:_need(False,'unknown finite token')
    return p.finish()


def validate_string_opcode_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Parent authenticates complete Execute, dispatcher and dependency groups."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/boundary')
    _need(set(spec['blocks'])==set(_PROGRAMS) and type(spec['opcodeId'])is int and spec['opcodeId']==opcode_ids['Ldstr'],'block/opcode declaration differs')
    _field(image,spec);_value_layout(image,contract);targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name);targets[name]=at
    for name,path in _METHOD_REFS.items():
        row=dict(_ref(contract,path));row.setdefault('parameterCount',len(_METHODS[name][2]));_signature(image,_METHODS[name])
        targets[name]=_identity(image,row,_METHODS[name],name,extents,body_required=False)
    cells=_cells(image,spec,contract)
    for name,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);_hash(_slice(body,body_rva,at,row['byteCount'],name),row,name);targets[name]=at
    row=_ref(contract,spec['pushForwardRef']);targets['pushForward']=_rva(row['rva']);raw=_slice(body,body_rva,targets['pushForward'],row['byteCount'],'pushForward');_hash(raw,row,'pushForward')
    p=_Program(targets['pushForward']);p.add('498bcc');p.rip('e9',targets['pushAdvance']);_expect(raw,p.finish(),'Ldstr.push-forward')
    p=_Program(targets['pushAdvance']);p.add('8bd6');p.call(targets['advancePointer']);p.rip('e9',targets['pushTopCommit'])
    row=_ref(contract,_TAIL_REFS['pushAdvance']);_expect(_slice(body,body_rva,targets['pushAdvance'],row['byteCount'],'pushAdvance'),p.finish(),'Ldstr.push-advance')
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'Ldstr.slot-width')
    for name,row in spec['blocks'].items():targets[name]=_rva(row['rva'])
    _need(spec['entryRva']==spec['blocks']['Ldstr']['rva'],'entry/block join differs')
    for name,row in spec['blocks'].items():
        at=targets[name];raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,name);_expect(raw,_program(name,at,targets,cells),name+'.full-finite-program')
    d=contract['dispatchRules'];actual=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),opcode_ids['Ldstr'],
        zero_compare_rva=_rva(d['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(d['extensions']['subEsi']['rva']),entry_rvas={_rva(r['entryRva'])for r in d['entryPoints']})
    _need(actual==targets['Ldstr'],'selected dispatch route differs')
    return {'status':'validated_conditional_string_push_request','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        **{k:spec[k]for k in ('operandMeaning','effect','stackDeltaSlots','normalNextInstructionDelta','managedClearBoundary','typeBoundary','storageBoundary','aliasBoundary','fileTableBoundary')},
        'unresolved':['runtime-internStrings-object-row-bounds-and-values','runtime-Type-and-PushObject-outcomes','storage-overlap-helper-mutation-and-GC','actual-execution']}


def project_string_opcode_rules(decoded: dict,spec: dict) -> list[dict]:
    """Project authored indices after selected validation; never materialize strings."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items())and type(spec['opcodeId'])is int,'unsupported projection schema/reference/boundary');out=[]
    for method in decoded['methods']:
        for instruction in method['instructions']:
            if instruction['name']!='Ldstr':continue
            operand=instruction['operandUnsigned'];_need(type(operand)is int and 0<=operand<=0xffffffff and instruction['opcode']==spec['opcodeId'],'malformed operand/opcode')
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned'not in instruction or type(instruction['operandSigned'])is int and instruction['operandSigned']==signed,'inconsistent signed operand')
            out.append({'vmMethodIndex':method['index'],'instructionIndex':instruction['index'],'offset':instruction['offset'],'opcode':'Ldstr','operandUnsigned':operand,'operandSigned':signed,
                'runtimeStringIndex':signed,'evidenceBoundary':'conditional','executionBoundary':'unobserved',
                **{k:spec[k]for k in ('effect','stackDeltaSlots','normalNextInstructionDelta','typeBoundary','storageBoundary','aliasBoundary','fileTableBoundary')}})
    return out


def validate_selected_string_opcode_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths are required'}
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'selected native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.stringOpcode');ext=image.mapper.pdata_function_extents(image.pe)
    row=dict(contract['consumer'],parameterTypes=_EXECUTE_TYPES);at=_identity(image,row,('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',ext)
    body=image.pe.bytes_at_va(image.pe.image_base+at,row['bodyBytes']);ids={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_string_opcode_rules(image,contract['stringOpcodeRules']if spec is None else spec,body,at,ids,contract,ext)
