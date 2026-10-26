"""Authenticate inline literals, Starg, packed Switch and Volatile requests.

Ldc_I8/Ldc_R8 read the next physical eight-byte record as raw bits, push one
slot and advance PC twice. Ldc_R4 copies the operand bits, preserves Value2
and pushes a Float. Starg stores the top value into the signed argument slot
and clears the physical source managed position after that store, as Stloc
does. The inherited store helper owns tag-dependent copy/clone behavior.

Switch reads top-1's Value1 without changing top or clearing it. In-range
nonnegative indexes select a signed Int32 table entry relative to current PC.
Other indexes use ((Operand+1)>>1)+1 with Int32 addition and arithmetic shift.
The optional offline framing requires a nonnegative bounded table count,
reserves ceil(count/2) physical eight-byte records, and preserves padding bits.
It cannot prove incoming PC selection or a jump target's runtime validity.

Volatile reaches the common PC-advance caller: advance eight bytes, load a
stored float constant and request the later loop/exception join. No memory
ordering operation is explicit in this proved caller. Subsequent loop and
exception control, runtime register state and actual execution remain open.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect, _slice, _identity
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class LiteralControlRuleError(ValueError):
    """A literal/control declaration lacks its finite native witness."""


_CLAIMS = {'schema':'endfield.ifix-vm-literal-control-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
    'inlineBoundary':'authored-sequential-storage-only;nonnegative-bounded-switch-count;incoming-PC-and-control-target-validity-unobserved',
    'literalRecipe':'I8-R8:next-qword-bits,push-one,PC-plus-two;R4:operand-bits,preserve-Value2,push-one,PC-plus-one',
    'stargRecipe':'top-minus-one;signed-argument-index;store;clear-source-physical-managed-position;pop-one',
    'switchRecipe':'read-top-minus-one-Value1;top-unchanged;in-range:current-PC-plus-table-int32;otherwise:current-PC-plus-((int32(Operand+1)>>1)+1)',
    'volatileRecipe':'common-PC-advance-eight-bytes;load-stored-float-constant;request-loop-join;no-explicit-ordering-op-in-proved-caller',
    'runtimeBoundary':'valid-stable-code-slots-and-managed-storage;nonmutating-normal-helper-return;alias-clone-hardware-state-and-execution-unobserved'}
_REFS={'nullCheck':'negativeFieldRules.helpers.nullCheck','advancePointer':'basicOpcodeRules.helpers.advancePointer',
    'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper','slotMultiply':'arithmeticWindows.signedSlotMultiply',
    'pointerAdd':'arithmeticWindows.pointerAdd','pointerDifference':'arithmeticWindows.stackPointerSubtract',
    'int32Add':'negativeFieldRules.helpers.int32Add','assignmentCheck':'functionPointerRules.helpers.assignmentCheck',
    'managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper','store':'slotCopyRules.methods.store',
    'pcAdvance':'basicOpcodeRules.sharedWindows.pcAdvance','pushForward':'referenceAddressRules.joins.pushForward',
    'loopState':'basicOpcodeRules.sharedWindows.loopState','vmRegister':'slotCopyRules.blocks.vmRegister'}
_RULES={'Ldc_I8':(1,2),'Ldc_R4':(1,1),'Ldc_R8':(1,2),'Starg':(-1,1),'Switch':(0,None),'Volatile':(0,1)}
_INLINE={'Ldc_I8':'qword-next-record','Ldc_R8':'qword-next-record','Switch':'packed-signed-int32-relative-targets'}


def _need(ok: bool, label: str) -> None:
    if not ok:raise LiteralControlRuleError('literalControl.'+label)


def inline_data_rules(spec: dict) -> dict[str,dict]:
    """Validate the reviewed framing declaration; the native caller owns gating."""
    _need(all(spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/boundary')
    rules=spec['inlineDataRules'];_need(set(rules)==set(_INLINE),'inline rule set differs')
    for name,kind in _INLINE.items():
        row=rules[name];_need(row.get('kind')==kind and type(row.get('opcodeId'))is int and 0<=row['opcodeId']<=0x7fffffff,'inline declaration differs: '+name)
    return rules


def _claims(spec: dict) -> dict[str,dict]:
    inline=inline_data_rules(spec);rows={r['opcode']:r for r in spec['rules']}
    _need(spec.get('helperRefs')==_REFS and len(rows)==len(spec['rules']) and set(rows)==set(_RULES),'rule/reference set differs')
    for name,row in rows.items():
        _need(row.get('entryBlock')==name and type(row.get('opcodeId'))is int and 0<=row['opcodeId']<=0x7fffffff,'entry rule differs')
        if name in inline:_need(row['opcodeId']==inline[name]['opcodeId'],'inline opcode differs')
    return rows


def _program(name: str,base: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(base)
    for token in _PATTERNS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='jump':p.rip('e9',targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        else:_need(False,'unknown finite token')
    return p.finish()


def validate_literal_control_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Authenticate one selected image; inherited semantics remain with owners."""
    rules=_claims(spec);targets={}
    for name,path in _REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);targets[name]=at
        _hash(image.pe.bytes_at_va(image.pe.image_base+at,row.get('byteCount',row.get('bodyBytes'))),row,name,method='bodyBytes'in row)
    blocks={r['name']:r for r in spec['blocks']};_need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_PATTERNS),'block set differs')
    targets.update({name:_rva(row['rva'])for name,row in blocks.items()})
    row=spec['loopRequest'];_need(row.get('boundary')=='caller-edge-only;subsequent-loop-and-exception-control-unresolved','loop outcome promoted')
    targets['loopRequest']=_rva(row['rva']);_hash(_slice(body,body_rva,targets['loopRequest'],row['byteCount'],'loopRequest'),row,'loopRequest')
    row=spec['floatConstant'];_need(row.get('byteCount')==4 and row.get('boundary')=='stored-constant-only;hardware-register-and-exception-state-unobserved','constant boundary differs')
    cells={'loopFloatConstant':_rva(row['cellRva'])};_expect(image.pe.bytes_at_va(image.pe.image_base+cells['loopFloatConstant'],4),bytes.fromhex(row['hex']),'loopFloatConstant')
    for name,row in blocks.items():
        actual=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(actual,row,name);_expect(actual,_program(name,targets[name],targets,cells),name)
    _need(targets['Ldc_R8']+blocks['Ldc_R8']['byteCount']==targets['literalTail'],'literal tail adjacency differs')
    # Starg's shared store and physical clear are the already-proved Stloc suffix.
    stloc=_ref(contract,'slotCopyRules.blocks.stloc');clear=_ref(contract,'basicOpcodeRules.sharedWindows.managedClear')
    _need(targets['stargStore']==_rva(stloc['rva'])+50 and targets['stargStore']+35==_rva(clear['rva'])
        and blocks['stargStore']['byteCount']==35+clear['byteCount'],'shared store/clear suffix differs')
    _need(targets['Volatile']==targets['pcAdvance'],'Volatile does not select common PC caller')
    for path in ('slotCopyRules.blocks.entryHomes','slotCopyRules.blocks.managedArgument','slotCopyRules.blocks.vmRegister'):
        row=_ref(contract,path);_hash(_slice(body,body_rva,_rva(row['rva']),row['byteCount'],path),row,path)
    _expect(_slice(body,body_rva,_rva(_ref(contract,'basicOpcodeRules.sharedWindows.slotWidth')['rva']),5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    _expect(_slice(body,body_rva,_rva(_ref(contract,'basicOpcodeRules.sharedWindows.zeroRegister')['rva']),3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    d=contract['dispatchRules'];extensions=d['extensions'];entries={_rva(r['entryRva'])for r in d['entryPoints']}
    for name,row in rules.items():
        _need(opcode_ids.get(name)==row['opcodeId'],'enum differs: '+name)
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],
            zero_compare_rva=_rva(extensions['zeroCompare']['rva']),sub_esi_rva=_rva(extensions['subEsi']['rva']),entry_rvas=entries)
        _need(entry==targets[name],'selected entry differs: '+name)
    return {'status':'validated_conditional_literal_control_rules','ruleCount':len(rules),'evidenceBoundary':'conditional','executionBoundary':'unobserved',
        'inlineBoundary':spec['inlineBoundary'],'unresolved':['incoming-PC-and-inline-target-selection','negative-or-overflowing-switch-count-runtime','Starg-aliases-store-and-clone-outcomes',
        'later-loop-and-exception-control','hardware-state-and-actual-execution']}


def project_literal_control_rules(decoded: dict,spec: dict) -> list[dict]:
    rules=_claims(spec);result=[]
    for method in decoded['methods']:
        for ins in method['instructions']:
            name=ins['name']
            if name not in rules:continue
            _need(ins['opcode']==rules[name]['opcodeId'],'authored opcode differs')
            row={'vmMethodIndex':method['index'],'instructionIndex':ins['index'],'offset':ins['offset'],'opcode':name,
                'operandSigned':ins['operandSigned'],'stackDeltaSlots':_RULES[name][0],'normalInstructionDelta':_RULES[name][1],
                'evidenceBoundary':'conditional','executionBoundary':'unobserved','runtimeBoundary':spec['runtimeBoundary']}
            if name in ('Ldc_I8','Ldc_R8'):row['payloadRawHex']=ins.get('inlineDataRawHex');row['resultTag']='Long'if name=='Ldc_I8'else'Double'
            elif name=='Ldc_R4':row.update(resultTag='Float',resultPayloadBits=ins['operandUnsigned'],resultValue2='preserved')
            elif name=='Starg':row.update(argumentIndex=ins['operandSigned'],aliasBoundary='inherited-store-then-source-physical-clear;actual-aliases-unobserved')
            elif name=='Switch':
                row.update(tableEntries=ins.get('inlineDataEntries'),runtimeSelectedTarget='unobserved',consumedManagedClear='none-explicit',inspectedValueRemainsOnStack=True)
            result.append(row)
    return result


def validate_selected_literal_control_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.literalControl');extents=image.mapper.pdata_function_extents(image.pe)
    at=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+at,contract['consumer']['bodyBytes']);ids={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_literal_control_rules(image,contract['literalControlRules']if spec is None else spec,body,at,ids,contract,extents)


_PATTERNS = {'Ldc_I8': ('498bcc',
            ('call', 'nullCheck'),
            'ba08000000498bce',
            ('call', 'advancePointer'),
            '488b004989442404498bcc',
            ('call', 'nullCheck'),
            '41c7042401000000',
            ('jump', 'literalTail')),
 'Ldc_R4': ('498bcc',
            ('call', 'nullCheck'),
            '498bce',
            ('call', 'nullCheck'),
            '418b46044189442404498bcc',
            ('call', 'nullCheck'),
            '41c7042402000000',
            ('jump', 'pushForward')),
 'Ldc_R8': ('498bcc',
            ('call', 'nullCheck'),
            'ba08000000498bce',
            ('call', 'advancePointer'),
            '488b004989442404498bcc',
            ('call', 'nullCheck'),
            '41c7042403000000'),
 'literalTail': ('8bd6498bcc',
                 ('call', 'advancePointer'),
                 '4c8be048894424584889442460ba08000000498bce',
                 ('call', 'advancePointer'),
                 '488944245048898424f8030000',
                 ('jump', 'Volatile')),
 'Starg': ('8bd6498bcc',
           ('call', 'subtractSlot'),
           '4c8be048894424584889442460498bce',
           ('call', 'nullCheck'),
           '49634e048bd6',
           ('call', 'slotMultiply'),
           '488b8c2400040000',
           ('jump', 'stargStore')),
 'stargStore': ('488bd0',
                ('call', 'pointerAdd'),
                '4c896c24284c897c24204d8bcc4c8bc0488bd3488bcf',
                ('call', 'store'),
                '488bd3498bcc',
                ('call', 'pointerDifference'),
                '498bcf',
                ('call', 'nullCheck'),
                '33d2498bcf',
                ('call', 'assignmentCheck'),
                '488bd3498bcc',
                ('call', 'pointerDifference'),
                '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
                ('call', 'managedStore'),
                ('jump', 'Volatile')),
 'Switch': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '488bc8',
            ('call', 'nullCheck'),
            '8bd6498bcc',
            ('call', 'subtractSlot'),
            '48635804413bdd7c3e498bce',
            ('call', 'nullCheck'),
            '413b5e047d30ba08000000498bce',
            ('call', 'advancePointer'),
            '488bf8488bcbba04000000',
            ('call', 'slotMultiply'),
            '488bd0488bcf',
            ('call', 'pointerAdd'),
            '486308',
            ('jump', 'switchTaken'),
            '498bce',
            ('call', 'nullCheck'),
            'bb010000008bd3418b4e04',
            ('call', 'int32Add'),
            'd1f88bd38bc8',
            ('call', 'int32Add'),
            '4863c88d5307',
            ('call', 'slotMultiply'),
            '488bd0498bce',
            ('call', 'pointerAdd'),
            ('jump', 'switchCommit')),
 'switchTaken': ('ba08000000',
                 ('call', 'slotMultiply'),
                 '498bce488bd0',
                 ('call', 'pointerAdd'),
                 '4c8bf0488944245048898424f8030000',
                 ('jump', 'vmRegister')),
 'switchCommit': ('4c8bf0488944245048898424f8030000', ('jump', 'loopState')),
 'Volatile': ('4c8b742450ba08000000498bce',
              ('call', 'advancePointer'),
              '4c8bf0488944245048898424f8030000',
              ('rip', 'f30f1035', 'loopFloatConstant'),
              ('jump', 'loopRequest'))}
