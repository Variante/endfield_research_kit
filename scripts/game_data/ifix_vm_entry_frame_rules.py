"""Authenticate Execute's conditional initial header and frame construction.

The adjacent prelude clears three five-word scratch frames and several stored
homes, then requests an exact container initializer that writes only its
Int32 depth to zero. Container elements and capacity are not initialized by
that leaf. The inherited ABI and zero-scratch programs establish the selected
input bindings; entry after the one-time resolver block remains conditional.

Execute checks the first instruction's Code against StackSpace. A mismatch
requests InvalidProgramException("invalid code!") and throwRuntimeException
with wrap selected by topWriteBack being null. The native continuation still
exists if that call returns. It resets pending/current exception homes, reads
the signed upper16 local count and unsigned lower16 evaluation reserve, and
computes the signed Int64 byte distance from argumentBase to evaluationBase,
truncated toward zero by the authenticated division program.

The capacity comparison first truncates the position to Int32, then performs
three wrapping Int32 additions of argsCount, signed locals and reserve. Only
a signed sum above the declared limit requests StackOverflowException and
the same conditional wrapping error call. This guard does not reject negative
counts or overflowed sums and does not establish actual allocated capacity.

On the selected native continuation, localBase is argumentBase plus signed
argsCount times descriptor width; top is localBase plus signed locals times
that width. The program writes their selected frame homes and advances the
saved initial PC by instruction width. It does not clear local descriptors or
managed elements. Full finite programs authenticate null branches, calls,
helper leaves, frame stores and the joins to inherited header sites. Valid
storage, nonmutating normal helpers, aliases, actual capacity, initializer
outcome, EH frame identity, error transfer and execution remain unobserved.
Native addresses, frame-home offsets, counts and hashes live in the contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_slice,_identity
from scripts.game_data.ifix_vm_reference_update_rules import _type_pointer
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier,_program as _call_program,_PROGRAMS as _CALL_PROGRAMS
from scripts.game_data.ifix_vm_stack_construction_rules import _signature
from scripts.game_data.ifix_vm_exception_funclet_rules import _anchor


class EntryFrameRuleError(ValueError):
    """An initial frame claim lacks its selected caller program."""


_METHOD_REFS={'invalidConstructor':'stackReferenceRules.nullConstructor','runtimeException':'delegateConstruction.methodCalls.nullFallbackException'}
_METHODS={'invalidConstructor':('System.InvalidProgramException','.ctor',['string'],'void',False),
    'capacityConstructor':('System.StackOverflowException','.ctor',[],'void',False),
    'runtimeException':('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False)}
_HELPER_REFS={'nullCheck':'negativeFieldRules.helpers.nullCheck','int32Add':'negativeFieldRules.helpers.int32Add',
    'pointerDifference':'arithmeticWindows.stackPointerSubtract','slotMultiply':'arithmeticWindows.signedSlotMultiply',
    'pointerAdd':'arithmeticWindows.pointerAdd','advancePointer':'basicOpcodeRules.helpers.advancePointer',
    'allocateException':'objectConversionRules.helpers.allocationThunk','nullFailure':'referenceUpdateRules.helpers.nullFailure'}
_CELL_REFS={'invalidType':'callOpcodeRules.usageCells.invalidProgramType'}
_CELLS={'invalidType':(1,'System.InvalidProgramException'),'capacityType':(1,'System.StackOverflowException'),'invalidLiteral':(5,'invalid code!')}
_ABI_REFS={n:'callOpcodeRules.blocks.'+n for n in ('abiPrelude','zeroScratch')}
_HOMES={'stateZero','scratchZero','callA0','callA16','callA32','callB0','callB16','callB32','callC0','callC16','callC32',
    'zeroPointerA','zeroPointerB','zeroPointerC','zeroPointerD','container','pendingLeave','currentException','savedException','savedHeaderPC',
    'localCount','evaluationBaseInput','positionInt64','positionInt32','argsCountInput','topWriteBackInput','localBase','top','savedTop','codeBase','PC','savedPC'}
_SITES={'headerCheck':'headerCheckRva','localCountRead':'localCountReadRva','evaluationReserveRead':'evaluationReserveReadRva',
    'localBase':'localBaseRva','evaluationBase':'evaluationBaseRva','firstInstructionAdvance':'firstInstructionAdvanceRva'}
_CLAIMS={'schema':'endfield.ifix-vm-entry-frame-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
    'headerRef':'entryHeader','methodRefs':_METHOD_REFS,'helperRefs':_HELPER_REFS,'usageRefs':_CELL_REFS,'abiRefs':_ABI_REFS,
    'allocationRef':'stackConstructionRules.allocationRequests','headerOpcode':'StackSpace','slotBytes':12,'instructionBytes':8,
    'initializationBoundary':'post-one-time-resolver-entry-with-inherited-ABI-bindings-and-zero-R13;resolver-entry-outcome-and-helper-mutation-unobserved',
    'preludeRecipe':'clear-three-five-word-scratch-frames-and-selected-homes;initialize-only-container-Int32-depth-zero',
    'headerRecipe':'initial-Code!=StackSpace:InvalidProgramException-invalid-code-message-and-runtimeException-request;native-continuation-if-returned',
    'countRecipe':'signed-upper16-locals;unsigned-lower16-reserve;position=trunc(signed-Int64(argumentBase-evaluationBase)/12)',
    'capacityRecipe':'signed-i32(wrapping-add-i32(position),argsCount,locals,reserve)>declared-limit:StackOverflowException-and-runtimeException-request',
    'frameRecipe':'localBase=argumentBase+signExtend(argsCount)*12;top=localBase+signExtend(locals)*12;write-frame-homes;PC=initial-PC+8',
    'errorWrapRecipe':'wrap=topWriteBack-is-null;constructor-and-runtimeException-requests-only;native-continuation-if-callee-returned',
    'capacityBoundary':'guard-limit-equals-declared-managed-slot-request;actual-capacity-negative-counts-wrapping-sums-pointer-bounds-and-storage-unobserved',
    'containerBoundary':'depth-zero-only;elements-capacity-and-EH-frame-association-unobserved',
    'storageBoundary':'valid-stable-instruction-frame-and-value-storage;normal-native-ABI-and-nonmutating-helper-returns',
    'aliasBoundary':'frame-home-overlap-and-helper-alias-mutation-unobserved;no-explicit-local-or-managed-element-clear',
    'runtimeBoundary':'one-time-resolution-allocation-constructor-error-transfer-EH-entry-capacity-and-execution-unobserved'}


def _need(ok: bool,detail: str) -> None:
    if not ok:raise EntryFrameRuleError('entryFrame.'+detail)


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    _need(set(spec['usageCells'])==set(_CELLS)-set(_CELL_REFS),'usage declaration set differs');rows=dict(spec['usageCells'])
    rows.update({n:_ref(contract,path)for n,path in _CELL_REFS.items()});result={}
    for name,(tag,identity)in _CELLS.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8);result[name]=at
        _need(type(row.get('usageTag'))is int and row['usageTag']==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'typed usage declaration/bytes differ')
        if tag==1:
            index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='ifix.entry.type',offset=at);_carrier(image,_type_pointer(image,index),identity)
        else:
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData'];idx=unresolved_usage_index(raw,table.size//8,tag=5,source='ifix.entry.literal',offset=at);off=table.offset+idx*8
            start,size=literal_record(md.buf[off:off+8],pool.size,source='ifix.entry.literal',offset=off)
            _need(md.buf[pool.offset+start:pool.offset+start+size]==identity.encode(),'invalid-code literal differs')
    return result


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int],spec: dict,header_id: int) -> tuple[bytes,dict[str,int]]:
    p=_Program(at)
    for token in _PROGRAMS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='home':
            prefix,home,width=args;value=spec['frameHomes'][home];_need(width!=1 or value<128,'frame home outside signed short displacement')
            p.add(prefix);p.add(value.to_bytes(width,'little',signed=True))
        elif kind=='limit':p.add(args[0]);p.add(spec['capacityLimit'].to_bytes(4,'little',signed=True))
        elif kind=='header':p.add(args[0]);p.add(bytes([header_id]))
        elif kind=='mark':p.mark(args[0])
        else:_need(False,'unknown finite token')
    return p.finish(),{name:at+offset for name,offset in p.labels.items()}


def validate_entry_frame_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Parent supplies selected inputs, complete Execute and dependency groups."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/boundary')
    _need(set(spec['blocks'])==set(_PROGRAMS)and set(spec['methods'])=={'capacityConstructor'}and set(spec['helpers'])=={'containerInitialize'},'declaration set differs')
    homes=spec['frameHomes'];_need(set(homes)==_HOMES and all(type(v)is int and 0<=v<=0x7fffffff for v in homes.values()),'frame home declaration differs')
    for name in ('callA','callB','callC'):_need(homes[name+'16']==homes[name+'0']+16 and homes[name+'32']==homes[name+'0']+32,'five-word clear partition differs')
    limit=spec['capacityLimit'];_need(type(limit)is int and 0<limit<=0x7fffffff and limit==_ref(contract,spec['allocationRef'])['managedSlotCount'],'capacity request/guard limit differs')
    depth=spec['containerDepthOffset'];_need(type(depth)is int and 0<=depth<128,'container depth declaration differs')
    header=_ref(contract,spec['headerRef']);header_id=opcode_ids.get('StackSpace');_need(type(header_id)is int and 0<=header_id<=127
        and header.get('opcode')=='StackSpace'and header.get('opcodeId')==header_id and header.get('slotBytes')==12
        and header.get('localCountHalf')=='signedUpper16'and header.get('evaluationReserveHalf')=='unsignedLower16','inherited header differs')
    abi={}
    for name,path in _ABI_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,name)
        _expect(raw,_call_program(at,_CALL_PROGRAMS[name],{},{}),name+'.inherited-finite-program');abi[name]=(at,raw)
    _need(abi['abiPrelude'][0]==body_rva and abi['zeroScratch'][0]==body_rva+len(abi['abiPrelude'][1]),'ABI/zero entry join differs')
    pre=abi['abiPrelude'][1];allocation=pre.index(bytes.fromhex('4881ec'));stack_depth=7*8+int.from_bytes(pre[allocation+3:allocation+7],'little')
    code_home=pre[pre.index(bytes.fromhex('48895424'))+4]
    _need(homes['evaluationBaseInput']==stack_depth+40 and homes['argsCountInput']==stack_depth+48
        and homes['topWriteBackInput']==stack_depth+72 and homes['codeBase']==code_home,'ABI input homes differ')
    targets={};cells=_cells(image,spec,contract)
    for name,identity in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[name])if name in _METHOD_REFS else spec['methods'][name]);row.setdefault('parameterCount',len(identity[2]));_signature(image,identity)
        targets[name]=_identity(image,row,identity,name,extents)
    for name,row in {**spec['helpers'],**{n:_ref(contract,path)for n,path in _HELPER_REFS.items()}}.items():
        at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,name);targets[name]=at
        leaves={'int32Add':'8d0411c3','pointerDifference':'482bca488bc1c3','slotMultiply':'4863c2480fafc1c3','pointerAdd':'488d0411c3','advancePointer':'4863c24803c1c3'}
        if name in leaves:_expect(raw,bytes.fromhex(leaves[name]),name)
        elif name=='containerInitialize':_expect(raw,bytes.fromhex('c741')+bytes([depth])+bytes.fromhex('00000000488bc1c3'),'containerInitialize')
    p=_Program(targets['nullCheck']);p.add('4883ec284885c974054883c428c3');p.call(targets['nullFailure']);p.add('cc')
    row=_ref(contract,_HELPER_REFS['nullCheck']);_expect(image.pe.bytes_at_va(image.pe.image_base+targets['nullCheck'],row['byteCount']),p.finish(),'nullCheck')
    checked={}
    for name,row in spec['blocks'].items():
        at=_rva(row['rva']);raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,name)
        expected,labels=_program(name,at,targets,cells,spec,header_id);_expect(raw,expected,name+'.full-finite-program');checked[name]=(at,len(raw),labels)
    _need(checked['prelude'][0]+checked['prelude'][1]==checked['entry'][0],'prelude/header adjacency differs')
    for label,key in _SITES.items():_need(checked['entry'][2][label]==_rva(header[key]),'inherited header site join differs: '+label)
    return {'status':'validated_conditional_entry_frame_recipes','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        **{k:spec[k]for k in ('preludeRecipe','headerRecipe','countRecipe','capacityRecipe','frameRecipe','errorWrapRecipe',
            'initializationBoundary','capacityBoundary','containerBoundary','storageBoundary','aliasBoundary','runtimeBoundary')},
        'capacityLimit':limit,'frameHomes':homes,'containerDepthOffset':depth,
        'unresolved':['one-time-initialization-entry-and-normal-helper-outcomes','actual-capacity-negative-counts-Int32-overflow-and-pointer-bounds',
            'frame-home-aliases-and-helper-mutation','container-elements-capacity-and-EH-frame-identity','error-transfer-unwinding-and-actual-execution']}


def validate_selected_entry_frame_rules(contract: dict,*,gameassembly: Path|None,metadata: Path|None,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths required'}
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.entryFrame');extents=image.mapper.pdata_function_extents(image.pe);_anchor(image,contract,extents)
    row=contract['consumer'];at=_rva(row['rva']);body=image.pe.bytes_at_va(image.pe.image_base+at,row['bodyBytes'])
    ids={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_entry_frame_rules(image,contract['entryFrameRules']if spec is None else spec,body,at,ids,contract,extents)
_PROGRAMS = {'prelude': [('home', '44896c24', 'stateZero', 1),
             ('home', '4c89ac24', 'scratchZero', 4),
             '0f57c033c0',
             ('home', '0f118424', 'callA0', 4),
             ('home', '0f118424', 'callA16', 4),
             ('home', '48898424', 'callA32', 4),
             '0f57c9',
             ('home', '0f118c24', 'callB0', 4),
             ('home', '0f118c24', 'callB16', 4),
             ('home', '48898424', 'callB32', 4),
             ('home', '0f118424', 'callC0', 4),
             ('home', '0f118424', 'callC16', 4),
             ('home', '48898424', 'callC32', 4),
             ('home', '4c89ac24', 'zeroPointerA', 4),
             ('home', '4c89ac24', 'zeroPointerB', 4),
             ('home', '4c89ac24', 'zeroPointerC', 4),
             ('home', '4c89ac24', 'zeroPointerD', 4),
             ('home', '488d8c24', 'container', 4),
             ('call', 'containerInitialize')],
 'entry': ['498bcc',
           ('call', 'nullCheck'),
           ('mark', 'headerCheck'),
           ('header', '41833c24'),
           '7443',
           ('rip', '488b0d', 'invalidType'),
           ('call', 'allocateException'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '4533c0',
           ('rip', '488b15', 'invalidLiteral'),
           '488bcb',
           ('call', 'invalidConstructor'),
           ('home', '4c39ac24', 'topWriteBackInput', 4),
           '410f94c04533c9488bd3488bce',
           ('call', 'runtimeException'),
           ('home', '44896c24', 'pendingLeave', 1),
           '498bc5',
           ('home', '48898424', 'currentException', 4),
           ('home', '48898424', 'savedException', 4),
           ('home', '4c89a424', 'savedHeaderPC', 4),
           '498bcc',
           ('call', 'nullCheck'),
           '418b7c2404',
           ('mark', 'localCountRead'),
           'c1ff10',
           ('home', '89bc24', 'localCount', 4),
           '498bcc',
           ('call', 'nullCheck'),
           ('mark', 'evaluationReserveRead'),
           '410fb75c2404',
           ('home', '488b9424', 'evaluationBaseInput', 4),
           '498bce',
           ('call', 'pointerDifference'),
           '488bc848b8abaaaaaaaaaaaa2a48f7e9488bca48d1f9488bc148c1e83f4803c8',
           ('home', '48898c24', 'positionInt64', 4),
           ('home', '898c24', 'positionInt32', 4),
           ('home', '8b9424', 'argsCountInput', 4),
           ('call', 'int32Add'),
           '8bc88bd7',
           ('call', 'int32Add'),
           '8bc88bd3',
           ('call', 'int32Add'),
           ('limit', '3d'),
           '7e3b',
           ('rip', '488b0d', 'capacityType'),
           ('call', 'allocateException'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '33d2488bcb',
           ('call', 'capacityConstructor'),
           ('home', '4c39ac24', 'topWriteBackInput', 4),
           '410f94c04533c9488bd3488bce',
           ('call', 'runtimeException'),
           ('home', '48638c24', 'argsCountInput', 4),
           'be0c0000008bd6',
           ('call', 'slotMultiply'),
           '488bd0498bce',
           ('mark', 'localBase'),
           ('call', 'pointerAdd'),
           '488bd8',
           ('home', '48898424', 'localBase', 4),
           '4863cf8bd6',
           ('call', 'slotMultiply'),
           '488bd0488bcb',
           ('mark', 'evaluationBase'),
           ('call', 'pointerAdd'),
           '4c8be0',
           ('home', '48894424', 'top', 1),
           ('home', '48894424', 'savedTop', 1),
           '8d56fc',
           ('home', '488b4c24', 'codeBase', 1),
           ('mark', 'firstInstructionAdvance'),
           ('call', 'advancePointer'),
           '4c8bf0',
           ('home', '48894424', 'PC', 1),
           ('home', '48898424', 'savedPC', 4)]}

