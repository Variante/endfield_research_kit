"""Selected arithmetic callers and finite scalar/overflow predicates, offline.

The lower slot's tag selects a width; the upper slot's tag is not checked.
Normal completion preserves that tag, replaces its payload and pops one slot.
Integer division uses native DIV/IDIV, with processor faults outside this proof.
Floating remainder authenticates the selected anonymous helper and returned
XMM0 store, without assigning that helper a mathematical remainder definition.
Overflow requests end at the inherited checked stop wrapper. Runtime storage,
helper mutations, floating state and exception transfer remain unobserved.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_comparison_rules import _value_layout
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_slice,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class ArithmeticRuleError(ValueError):
    """An arithmetic declaration lacks its selected finite witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise ArithmeticRuleError('ifix-arithmetic.'+label)


_HELPER_REFS={'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper','nullCheck':'negativeFieldRules.helpers.nullCheck',
 'intAdd':'negativeFieldRules.helpers.int32Add','longAdd':'arithmeticWindows.pointerAdd',
 'intSub':'indirectOpcodeRules.helpers.intSubtract','longSub':'arithmeticWindows.stackPointerSubtract',
 'allocateObject':'objectConversionRules.helpers.allocationThunk','throwStop':'objectConversionRules.helpers.throwStop',
 'overflowRequest':'conversionOpcodeRules.helpers.overflowRequest','advancePointer':'basicOpcodeRules.helpers.advancePointer'}
_METHOD_REFS={'runtimeException':'delegateConstruction.methodCalls.nullFallbackException'}
_METHODS={'runtimeException':('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False),
 'notImplementedCtor':('System.NotImplementedException','.ctor',[],'void',False)}
_TAIL_REFS={name:'basicOpcodeRules.sharedWindows.'+name for name in ('zeroRegister','slotWidth','loopState','pcAdvance','pushAdvance','pushTopCommit')}
_TAGS={'Integer':0,'Long':1,'Float':2,'Double':3}
_CELLS={'notImplementedType':(1,'System.NotImplementedException'),'executeContext':(3,'IFix.Core.VirtualMachine.Execute')}
_LEAVES={'intMul':'0fafca8bc1c3','longMul':'480fafca488bc1c3','floatAdd':'f30f58c1c3','doubleAdd':'f20f58c1c3',
 'floatSub':'f30f5cc1c3','doubleSub':'f20f5cc1c3','floatMul':'f30f59c1c3','doubleMul':'f20f59c1c3',
 'unsignedMulGuard':'4c8bc24885d2741433d2488bc1490fafc049f7f0483bc17403b001c332c0c3',
 'signedMulGuard':'4c8bc94c8bd249f7d94c0f48c949f7da4c0f48d24533c04885c97e2f4885d27f2f48b900000000000000804d85c97417488bc148f7d8480f48c133d249f7f14c3bd0760341b001418ac0c34885d27fd148b9ffffffffffffff7febcf'}
_BOUNDS={'schema':'endfield.ifix-vm-arithmetic-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'slotBytes':12,'instructionBytes':8,'operandUse':'ignored','resultTag':'preserved','resultSlot':'incoming-top-2',
 'managedClear':'none-explicit-in-selected-caller-routes','dispatchProofRef':'dispatchRules',
 'valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout','storageBoundary':'valid-stable-12-byte-slots',
 'helperBoundary':'normal-selected-helper-return-and-no-helper-slot-mutation-assumed',
 'aliasBoundary':'runtime-helper-mutation-and-slot-overlap-unobserved',
 'divisionBoundary':'native-DIV-IDIV; zero-and-signed-minimum-over-minus-one-fault-outcomes-unobserved',
 'floatingBoundary':'native-ADD-SUB-MUL-DIV-low-lanes; MXCSR-and-exception-state-unobserved',
 'floatingRemainderBoundary':'selected-anonymous-helper-request-and-XMM0-return-store; numeric-semantics-unresolved',
 'stopBoundary':'checked-wrapper-opaque-call-followed-by-INT3; abnormal-transfer-outcome-unobserved'}
_RULES={
 'Add':{'entryProgram':'Add','Integer':'low32 addition modulo 2^32; Value2-preserved','Long':'raw64 addition modulo 2^64',
        'Float':'ADDSS lower,upper; Value2-preserved','Double':'ADDSD lower,upper','otherTags':'NotImplementedException-request/runtimeException-wrap-true; unchanged-payload-pop-on-normal-return'},
 'Sub':{'entryProgram':'Sub','Integer':'low32 subtraction modulo 2^32; Value2-preserved','Long':'raw64 subtraction modulo 2^64',
        'Float':'SUBSS lower,upper; Value2-preserved','Double':'SUBSD lower,upper','otherTags':'NotImplementedException-request/runtimeException-wrap-true; unchanged-payload-pop-on-normal-return'},
 'Mul':{'entryProgram':'Mul','Integer':'low32 product modulo 2^32; Value2-preserved','Long':'raw64 product modulo 2^64',
        'Float':'MULSS lower,upper; Value2-preserved','Double':'MULSD lower,upper','otherTags':'payload-unchanged-normal-pop-one'},
 'Div':{'entryProgram':'Div','Integer':'signed IDIV32 quotient; Value2-preserved','Long':'signed IDIV64 quotient',
        'Float':'DIVSS lower,upper; Value2-preserved','Double':'DIVSD lower,upper','otherTags':'payload-unchanged-normal-pop-one'},
 'Div_Un':{'entryProgram':'Div_Un','Integer':'unsigned DIV32 quotient; Value2-preserved','Long':'unsigned DIV64 quotient','otherTags':'payload-unchanged-normal-pop-one'},
 'Rem':{'entryProgram':'Rem','Integer':'signed IDIV32 remainder; Value2-preserved','Long':'signed IDIV64 remainder',
        'Float':'selected float helper(lower,upper); returned low32(XMM0); Value2-preserved','Double':'selected double helper(lower,upper); returned low64(XMM0)',
        'otherTags':'payload-unchanged-normal-pop-one'},
 'Rem_Un':{'entryProgram':'Rem_Un','Integer':'unsigned DIV32 remainder; Value2-preserved','Long':'unsigned DIV64 remainder','otherTags':'payload-unchanged-normal-pop-one'},
 'Add_Ovf':{'entryProgram':'checkedAdd','Integer':'signed32 sum outside [-2^31,2^31-1] requests stop; otherwise low32 sum; Value2-preserved',
        'Long':'signed64 sum outside [-2^63,2^63-1] requests stop; otherwise raw64 sum','Float':'ADDSS lower,upper; Value2-preserved',
        'Double':'ADDSD lower,upper','otherTags':'payload-unchanged-normal-pop-one'},
 'Add_Ovf_Un':{'entryProgram':'checkedAdd','Integer':'unsigned32 sum greater than 2^32-1 requests stop; otherwise low32 sum; Value2-preserved',
        'Long':'unsigned64 lower greater than (2^64-1 - upper) requests stop; otherwise raw64 sum','Float':'ADDSS lower,upper; Value2-preserved',
        'Double':'ADDSD lower,upper','otherTags':'payload-unchanged-normal-pop-one'},
 'Mul_Ovf':{'entryProgram':'Mul_Ovf','Integer':'signed32 product outside [-2^31,2^31-1] requests stop; otherwise low32 product; Value2-preserved',
        'Long':'signed64 product outside [-2^63,2^63-1] requests stop; otherwise raw64 product','Float':'MULSS lower,upper; Value2-preserved',
        'Double':'MULSD lower,upper','otherTags':'payload-unchanged-normal-pop-one'},
 'Mul_Ovf_Un':{'entryProgram':'Mul_Ovf_Un','Integer':'unsigned32 product greater than 2^32-1 requests stop; otherwise low32 product; Value2-preserved',
        'Long':'unsigned64 product greater than 2^64-1 requests stop; otherwise raw64 product','otherTags':'payload-unchanged-normal-pop-one'},
}


def _claims(spec: dict) -> dict[str,dict]:
    _need(all(spec.get(k)==v for k,v in _BOUNDS.items()) and type(spec.get('slotBytes')) is int and type(spec.get('instructionBytes')) is int
        and spec.get('helperRefs')==_HELPER_REFS and spec.get('methodRefs')==_METHOD_REFS and spec.get('tailRefs')==_TAIL_REFS
        and spec.get('tagMembers')==_TAGS,'unsupported schema/reference/layout/boundary')
    rows={row['opcode']:row for row in spec['rules']};_need(len(rows)==len(spec['rules']) and set(rows)==set(_RULES),'arithmetic family differs')
    for name,row in rows.items():
        _need(type(row.get('normalStackDeltaSlots')) is int and row['normalStackDeltaSlots']==-1 and row.get('typeSelection')=='lower-tag-only-upper-tag-unchecked'
              and all(row.get(k)==v for k,v in _RULES[name].items()),'operator claims differ: '+name)
    return rows


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int],ids: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='opcodeCmp':
            _need(type(ids[args[0]]) is int and 0<=ids[args[0]]<128,'saved-Code signed-byte comparison unsupported');p.add('837c2470');p.add(bytes([ids[args[0]]]))
        elif kind=='rel':
            prefix,target,size=args;raw=bytes.fromhex(prefix);disp=targets[target]-(at+len(p.raw)+len(raw)+size);p.add(raw+disp.to_bytes(size,'little',signed=True))
        else:_need(False,'unknown finite arithmetic token')
    return p.finish()


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    rows={row['name']:row for row in spec['usageCells']};_need(len(rows)==len(spec['usageCells']) and set(rows)==set(_CELLS),'usage set differs');result={}
    for name,(tag,identity) in _CELLS.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(type(row.get('usageTag')) is int and row['usageTag']==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'stored usage differs: '+name);result[name]=at
        if tag==1:
            idx=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='ifix-arithmetic.type',offset=at);_need(_type(image,idx)==identity,'raw nonbyref carrier differs: '+name)
        else:
            idx=unresolved_usage_index(raw,len(image.metadata.methods),tag=tag,source='ifix-arithmetic.context',offset=at);md=image.metadata;method=md.methods[idx]
            owners=[t for t in md.types if t.method_start<=idx<t.method_start+t.method_count]
            _need(len(owners)==1 and md.type_full_name(owners[0])=='IFix.Core.VirtualMachine' and md.string(method.name_index)=='Execute'
              and method.token==_rva(contract['consumer']['token']) and method.parameter_count==len(_EXECUTE_TYPES)
              and [_type(image,p.type_index) for p in md.parameters_for(method)]==_EXECUTE_TYPES and _type(image,method.return_type)=='IFix.Core.Value*'
              and not method.flags&0x10 and method.generic_container_index==-1
              and image.method_pointer_va(method)==image.pe.image_base+_rva(contract['consumer']['rva']),'stored Execute MethodDef context differs')
    return result


def _helpers(image: Any,spec: dict,targets: dict[str,int],extents: dict[int,int]) -> None:
    rows=spec['helpers'];_need(set(rows)==set(_LEAVES)|{'signedAddGuard','signedAddCold','doubleRem','floatRem'},'scalar helper set differs')
    targets.update({n:_rva(row['rva']) for n,row in rows.items()})
    for name,row in rows.items():
        at=targets[name];raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'helper.'+name)
        if name in _LEAVES:_expect(raw,bytes.fromhex(_LEAVES[name]),'helper.'+name)
        elif name=='signedAddGuard':
            p=_Program(at);p.add('4885d2781248b8ffffffffffffff7f482bc2483bc87f0c4885c9');p.rip('0f88',targets['signedAddCold']);p.add('32c0c3b001c3');_expect(raw,p.finish(),name)
        elif name=='signedAddCold':
            p=_Program(at);p.add('48b80000000000000080482bc1483bd0');p.rip('0f8d',targets['signedAddGuard']+32);p.rip('e9',targets['signedAddGuard']+35);_expect(raw,p.finish(),name)
        else:
            _need(extents.get(image.pe.image_base+at)==image.pe.image_base+at+len(raw),'floating helper complete extent differs: '+name)
            _need(row.get('effectBoundary')=='opaque-numeric-helper-XMM0-return-store-only','floating helper claim differs: '+name)


def validate_arithmetic_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Authenticate finite caller programs; no runtime arithmetic evaluation."""
    rules=_claims(spec);_value_layout(image,contract)
    tags={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(tags.get(n)==v for n,v in _TAGS.items()),'actual ValueType enum differs')
    for name,row in rules.items():_need(type(row['opcodeId']) is int and row['opcodeId']==opcode_ids.get(name),'Code enum differs: '+name)
    targets={};expected={'subtractSlot':'4863c2482bc8488bc1c3','intAdd':'8d0411c3','longAdd':'488d0411c3',
        'intSub':'2bca8bc1c3','longSub':'482bca488bc1c3','advancePointer':'4863c24803c1c3'}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'inherited helper.'+name);targets[name]=at
        if name in expected:_expect(raw,bytes.fromhex(expected[name]),'helper.'+name)
        elif name=='throwStop':_need(len(raw)==20 and raw[:14]==bytes.fromhex('4883ec2833c04889413848894140') and raw[14]==0xe8 and raw[19]==0xcc,'stop wrapper shape differs')
    _helpers(image,spec,targets,extents)
    for name,identity in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[name]) if name in _METHOD_REFS else spec['methods'][name]);row.setdefault('parameterCount',len(identity[2]));targets[name]=_identity(image,row,identity,name,extents)
    _need(set(spec['methods'])=={'notImplementedCtor'},'method catalog differs')
    for name,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,'tail.'+name);targets[name]=at
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    p=_Program(targets['loopState']);p.add('488b9c2410040000498bce');p.call(targets['nullCheck']);p.add('418b0e894c2470')
    _expect(_slice(body,body_rva,p.base,len(p.raw),'loopState'),p.finish(),'saved Code binding')
    p=_Program(targets['pushAdvance']);p.add('8bd6');p.call(targets['advancePointer']);p.rip('e9',targets['pushTopCommit']);_expect(_slice(body,body_rva,p.base,len(p.raw),'pushAdvance'),p.finish(),'pushAdvance')
    p=_Program(targets['pushTopCommit']);p.add('4c8be048894424584889442460');p.rip('e9',targets['pcAdvance']);_expect(_slice(body,body_rva,p.base,len(p.raw),'pushTopCommit'),p.finish(),'pushTopCommit')
    cells=_cells(image,spec,contract);blocks={row['name']:row for row in spec['blocks']};_need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_BLOCKS),'arithmetic block set differs')
    targets.update({n:_rva(r['rva']) for n,r in blocks.items()})
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'block.'+name);_expect(raw,_program(name,targets[name],targets,cells,opcode_ids),'block.'+name)
    dispatch=contract['dispatchRules'];_need(dispatch.get('schema')=='endfield.ifix-vm-dispatch-rules.v1','reviewed dispatch prerequisite missing')
    for name,shape in [('zeroCompare','413bcd'),('subEsi','2bce')]:
        row=dispatch['extensions'][name];raw=_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name);_hash(raw,row,'dispatch.'+name);_expect(raw,bytes.fromhex(shape),'dispatch.'+name)
    entries={_rva(row['entryRva']) for row in dispatch['entryPoints']};checked=[]
    for name,row in rules.items():
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],
            zero_compare_rva=_rva(dispatch['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(dispatch['extensions']['subEsi']['rva']),entry_rvas=entries)
        _need(entry==_rva(row['entryRva'])==targets[row['entryProgram']],'selected arithmetic entry differs: '+name);checked.append({'opcode':name,'opcodeId':row['opcodeId'],'entryRva':hex(entry),'normalStackDeltaSlots':-1})
    return {'status':'validated_conditional_arithmetic_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved','entries':checked,
        'divisionBoundary':spec['divisionBoundary'],'floatingRemainderBoundary':spec['floatingRemainderBoundary'],'stopBoundary':spec['stopBoundary'],
        'unresolved':['runtime-tags-payloads-and-storage','floating-remainder-helper-numeric-semantics','FP-state-and-processor-fault-transfer',
                      'helper-alias-mutation-and-exception-outcomes','actual-execution']}


def project_arithmetic_rules(decoded: dict,spec: dict) -> list[dict]:
    """Project authored opcode recipes; preserve ignored operands verbatim."""
    rules=_claims(spec);result=[]
    for method in decoded['methods']:
        for ins in method['instructions']:
            name=ins['name']
            if name not in rules:continue
            row=rules[name];operand=ins['operandUnsigned'];_need(type(operand) is int and 0<=operand<=0xffffffff and type(ins['opcode']) is int and ins['opcode']==row['opcodeId'],'malformed operand/opcode: '+name)
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned' not in ins or type(ins['operandSigned']) is int and ins['operandSigned']==signed,'inconsistent signed operand: '+name)
            result.append({'vmMethodIndex':method['index'],'instructionIndex':ins['index'],'offset':ins['offset'],'opcode':name,
                'operandUnsigned':operand,'operandSigned':signed,'operandUse':'ignored','resultSlot':spec['resultSlot'],'resultTag':'preserved',
                'normalStackDeltaSlots':-1,'normalNextInstructionDelta':1,'typeSelection':'lower-tag-only-upper-tag-unchecked',**_RULES[name],
                **{k:spec[k] for k in ('managedClear','storageBoundary','helperBoundary','aliasBoundary','divisionBoundary','floatingBoundary','floatingRemainderBoundary','stopBoundary')},
                'runtimeResult':'unobserved','evidenceBoundary':'conditional','executionBoundary':'unobserved'})
    return result


def validate_selected_arithmetic_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Gate explicit selected inputs and authenticate complete Execute bytes."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.arithmetic');extents=image.mapper.pdata_function_extents(image.pe)
    base=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,contract['consumer']['bodyBytes']);ids={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_arithmetic_rules(image,contract['arithmeticRules'] if spec is None else spec,body,base,ids,contract,extents)


_BLOCKS = {'Add': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8bf08bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd84889442460488bc8',
         ('call', 'nullCheck'),
         '8b0b413bcd0f84a000000083e901746e83e901743983f901',
         ('rel', '0f85', 'unsupportedAddSub', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bce',
         ('call', 'nullCheck'),
         'f2410f104e040f28c6',
         ('call', 'doubleAdd'),
         ('rel', 'e9', 'doubleStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bce',
         ('call', 'nullCheck'),
         'f3410f104e040f28c6',
         ('call', 'floatAdd'),
         ('rel', 'e9', 'floatStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bce',
         ('call', 'nullCheck'),
         '498b5604488bcf',
         ('call', 'longAdd'),
         ('rel', 'e9', 'longStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7304498bce',
         ('call', 'nullCheck'),
         '418b7e04488bcb',
         ('call', 'nullCheck'),
         '8bd78bce',
         ('call', 'intAdd'),
         ('rel', 'e9', 'intStore', 4)),
 'Sub': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8bf08bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd84889442460488bc8',
         ('call', 'nullCheck'),
         '8b0b413bcd0f84e400000083e9010f84ad00000083e901747683f901743c',
         ('rip', '488b0d', 'notImplementedType'),
         ('call', 'allocateObject'),
         '488bf8488bc8',
         ('call', 'nullCheck'),
         '33d2488bcf',
         ('call', 'notImplementedCtor'),
         '4533c941b001488bd7488b8c24f0030000',
         ('call', 'runtimeException'),
         'e9c5000000488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bce',
         ('call', 'nullCheck'),
         'f2410f104e040f28c6',
         ('call', 'doubleSub'),
         'f20f114304e990000000488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bce',
         ('call', 'nullCheck'),
         'f3410f104e040f28c6',
         ('call', 'floatSub'),
         'f30f114304eb5e488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bce',
         ('call', 'nullCheck'),
         '498b5604488bcf',
         ('call', 'longSub'),
         '48894304eb30488bcb',
         ('call', 'nullCheck'),
         '8b7304498bce',
         ('call', 'nullCheck'),
         '418b7e04488bcb',
         ('call', 'nullCheck'),
         '8bd78bce',
         ('call', 'intSub'),
         '894304be0c000000488bcb',
         ('rel', 'e9', 'pushAdvance', 4)),
 'Mul': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8bf08bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd84889442460488bc8',
         ('call', 'nullCheck'),
         '8b0b413bcd0f84a000000083e901746e83e901743983f901',
         ('rel', '0f85', 'normalCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bce',
         ('call', 'nullCheck'),
         'f2410f104e040f28c6',
         ('call', 'doubleMul'),
         ('rel', 'e9', 'doubleStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bce',
         ('call', 'nullCheck'),
         'f3410f104e040f28c6',
         ('call', 'floatMul'),
         ('rel', 'e9', 'floatStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bce',
         ('call', 'nullCheck'),
         '498b5604488bcf',
         ('call', 'longMul'),
         ('rel', 'e9', 'longStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7304498bce',
         ('call', 'nullCheck'),
         '418b7e04488bcb',
         ('call', 'nullCheck'),
         '8bd78bce',
         ('rel', 'e9', 'mulIntTail', 4)),
 'Div': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8bf08bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd84889442460488bc8',
         ('call', 'nullCheck'),
         '8b0b413bcd0f849700000083e901746883e901743683f901',
         ('rel', '0f85', 'normalCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bce',
         ('call', 'nullCheck'),
         'f2410f5e7604f20f117304',
         ('rel', 'e9', 'normalCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bce',
         ('call', 'nullCheck'),
         'f3410f5e7604f30f117304',
         ('rel', 'e9', 'normalCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bce',
         ('call', 'nullCheck'),
         '488bc7489949f77e04',
         ('rel', 'e9', 'longStore', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7304498bce',
         ('call', 'nullCheck'),
         '418b7e04488bcb',
         ('call', 'nullCheck'),
         '8bc699f7ff',
         ('rel', 'e9', 'intStore', 4)),
 'Div_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '4c8bf08bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '488bd84889442460488bc8',
            ('call', 'nullCheck'),
            '833b01752a488bcb',
            ('call', 'nullCheck'),
            '488bcb',
            ('call', 'nullCheck'),
            '488b7b04498bce',
            ('call', 'nullCheck'),
            '33d2488bc749f77604',
            ('rel', 'e9', 'longStore', 4),
            '44392b',
            ('rel', '0f85', 'normalCommit', 4),
            '488bcb',
            ('call', 'nullCheck'),
            '8b7304498bce',
            ('call', 'nullCheck'),
            '418b7e04488bcb',
            ('call', 'nullCheck'),
            '33d28bc6f7f7',
            ('rel', 'e9', 'intStore', 4)),
 'Rem': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8be048894424588bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd8488bc8',
         ('call', 'nullCheck'),
         '8b03413bc50f84aa00000083e801747a83e801743f83f801',
         ('rel', '0f85', 'remTopCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bcc',
         ('call', 'nullCheck'),
         'f2410f104c24040f28c6',
         ('call', 'doubleRem'),
         'f20f114304',
         ('rel', 'e9', 'remTopCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bcc',
         ('call', 'nullCheck'),
         'f3410f104c24040f28c6',
         ('call', 'floatRem'),
         'f30f114304',
         ('rel', 'e9', 'remTopCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bcc',
         ('call', 'nullCheck'),
         '488bc7489949f77c2404',
         ('rel', 'e9', 'rem64Store', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7304498bcc',
         ('call', 'nullCheck'),
         '418b7c2404488bcb',
         ('call', 'nullCheck'),
         '8bc699f7ff',
         ('rel', 'e9', 'rem32Store', 4)),
 'Rem_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '4c8be048894424588bd6488bc8',
            ('call', 'subtractSlot'),
            '488bd8488bc8',
            ('call', 'nullCheck'),
            '44392b7530488bcb',
            ('call', 'nullCheck'),
            '8b7304498bcc',
            ('call', 'nullCheck'),
            '418b7c2404488bcb',
            ('call', 'nullCheck'),
            '33d28bc6f7f7895304be0c000000eb2f833b01752a488bcb',
            ('call', 'nullCheck'),
            '488bcb',
            ('call', 'nullCheck'),
            '488b7b04498bcc',
            ('call', 'nullCheck'),
            '33d2488bc749f7742404488953044c89642460',
            ('rel', 'e9', 'pcAdvance', 4)),
 'checkedAdd': ('8bd6498bcc',
                ('call', 'subtractSlot'),
                '488bf0bb0c0000008bd3498bcc',
                ('call', 'subtractSlot'),
                '8bd3488bc8',
                ('call', 'subtractSlot'),
                '488bd84889442460488bc8',
                ('call', 'nullCheck'),
                '8b0b413bcd0f84eb00000083e901746c83e901743883f901',
                ('rel', '0f85', 'widthRestore', 4),
                '488bcb',
                ('call', 'nullCheck'),
                '488bcb',
                ('call', 'nullCheck'),
                'f20f107304488bce',
                ('call', 'nullCheck'),
                'f20f104e040f28c6',
                ('call', 'doubleAdd'),
                ('rel', 'e9', 'mulDoubleStore', 4),
                '488bcb',
                ('call', 'nullCheck'),
                '488bcb',
                ('call', 'nullCheck'),
                'f30f107304488bce',
                ('call', 'nullCheck'),
                'f30f104e040f28c6',
                ('call', 'floatAdd'),
                ('rel', 'e9', 'mulFloatStore', 4),
                '488bcb',
                ('opcodeCmp', 'Add_Ovf'),
                '742f',
                ('call', 'nullCheck'),
                '488bcb',
                ('call', 'nullCheck'),
                '488b7b04488bce',
                ('call', 'nullCheck'),
                '488b56044883c8ff482bc2483bf8',
                ('rel', '0f87', 'unsignedAdd64Fail', 4),
                'eb34',
                ('call', 'nullCheck'),
                '488bcb',
                ('call', 'nullCheck'),
                '488b7b04488bce',
                ('call', 'nullCheck'),
                '488b7604488bd6488bcf',
                ('call', 'signedAddGuard'),
                '413ac5',
                ('rel', '0f85', 'signedAdd64Fail', 4),
                '488bd6488bcf',
                ('call', 'longAdd'),
                ('rel', 'e9', 'mul64Store', 4),
                '488bcb',
                ('opcodeCmp', 'Add_Ovf'),
                '743b',
                ('call', 'nullCheck'),
                '8b7b04488bce',
                ('call', 'nullCheck'),
                '8b7604488d0c37b8ffffffff483bc8',
                ('rel', '0f87', 'unsignedAdd32Fail', 4),
                '488bcb',
                ('call', 'nullCheck'),
                '8bd68bcf',
                ('call', 'intAdd'),
                ('rel', 'e9', 'intStore', 4),
                ('call', 'nullCheck'),
                '48637b04488bce',
                ('call', 'nullCheck'),
                '486376044c8d04374981f800000080',
                ('rel', '0f8c', 'signedAdd32Fail', 4),
                '4c8d04374981f8ffffff7f',
                ('rel', '0f8f', 'signedAdd32Fail', 4),
                '488bcb',
                ('call', 'nullCheck'),
                '8bd68bcf',
                ('rel', 'e9', 'addIntTail', 4)),
 'Mul_Ovf': ('8bd6498bcc',
             ('call', 'subtractSlot'),
             '488bf0bb0c0000008bd3498bcc',
             ('call', 'subtractSlot'),
             '8bd3488bc8',
             ('call', 'subtractSlot'),
             '488bd84889442460488bc8',
             ('call', 'nullCheck'),
             '8b0b413bcd0f84c800000083e901747683e901743d83f901',
             ('rel', '0f85', 'widthRestore', 4),
             '488bcb',
             ('call', 'nullCheck'),
             '488bcb',
             ('call', 'nullCheck'),
             'f20f107304488bce',
             ('call', 'nullCheck'),
             'f20f104e040f28c6',
             ('call', 'doubleMul'),
             'f20f114304',
             ('rel', 'e9', 'widthRestore', 4),
             '488bcb',
             ('call', 'nullCheck'),
             '488bcb',
             ('call', 'nullCheck'),
             'f30f107304488bce',
             ('call', 'nullCheck'),
             'f30f104e040f28c6',
             ('call', 'floatMul'),
             'f30f114304',
             ('rel', 'e9', 'widthRestore', 4),
             '488bcb',
             ('call', 'nullCheck'),
             '488bcb',
             ('call', 'nullCheck'),
             '488b7b04488bce',
             ('call', 'nullCheck'),
             '488b760449b9ffffffffffffff7f49b80000000000000080488bd6488bcf',
             ('call', 'signedMulGuard'),
             '413ac5',
             ('rel', '0f85', 'signedMul64Fail', 4),
             ('rel', 'e9', 'mulLongProduct', 4),
             '488bcb',
             ('call', 'nullCheck'),
             '48637b04488bce',
             ('call', 'nullCheck'),
             '486376044c8bc64c0fafc74981f800000080',
             ('rel', '0f8c', 'signedMul32Fail', 4),
             '4c8bc64c0fafc74981f8ffffff7f',
             ('rel', '0f8f', 'signedMul32Fail', 4),
             ('rel', 'e9', 'mulIntPrecommit', 4)),
 'Mul_Ovf_Un': ('8bd6498bcc',
                ('call', 'subtractSlot'),
                '488bf0bb0c0000008bd3498bcc',
                ('call', 'subtractSlot'),
                '8bd3488bc8',
                ('call', 'subtractSlot'),
                '488bd84889442460488bc8',
                ('call', 'nullCheck'),
                '833b017548488bcb',
                ('call', 'nullCheck'),
                '488bcb',
                ('call', 'nullCheck'),
                '488b7b04488bce',
                ('call', 'nullCheck'),
                '488b7604488bd6488bcf',
                ('call', 'unsignedMulGuard'),
                '413ac5',
                ('rel', '0f85', 'unsignedMul64Fail', 4),
                '488bd6488bcf',
                ('call', 'longMul'),
                '48894304',
                ('rel', 'e9', 'widthRestore', 4),
                '44392b',
                ('rel', '0f85', 'widthRestore', 4),
                '488bcb',
                ('call', 'nullCheck'),
                '8b7b04488bce',
                ('call', 'nullCheck'),
                '8b76048bce480fafcfb8ffffffff483bc8',
                ('rel', '0f87', 'unsignedMul32Fail', 4),
                '488bcb',
                ('call', 'nullCheck'),
                '8bd68bcf',
                ('call', 'intMul'),
                ('rel', 'e9', 'intStore', 4)),
 'unsupportedAddSub': (('rip', '488b0d', 'notImplementedType'),
                       ('call', 'allocateObject'),
                       '488bf8488bc8',
                       ('call', 'nullCheck'),
                       '33d2488bcf',
                       ('call', 'notImplementedCtor'),
                       '4533c941b001488bd7488b8c24f0030000',
                       ('call', 'runtimeException'),
                       ('rel', 'e9', 'normalCommit', 4)),
 'doubleStore': ('f20f114304', ('rel', 'e9', 'normalCommit', 4)),
 'floatStore': ('f30f114304', ('rel', 'eb', 'normalCommit', 1)),
 'longStore': ('48894304', ('rel', 'eb', 'normalCommit', 1)),
 'intStore': ('894304be0c000000',),
 'widthRestore': ('be0c000000',),
 'normalCommit': ('488bcb', ('rel', 'e9', 'pushAdvance', 4)),
 'mulLongProduct': ('488bd6488bcf', ('call', 'longMul'), '48894304', ('rel', 'e9', 'widthRestore', 4)),
 'mul64Store': ('48894304', ('rel', 'e9', 'widthRestore', 4)),
 'mulFloatStore': ('f30f114304', ('rel', 'e9', 'widthRestore', 4)),
 'mulDoubleStore': ('f20f114304', ('rel', 'e9', 'widthRestore', 4)),
 'mulIntPrecommit': ('488bcb', ('call', 'nullCheck'), '8bd68bcf', ('call', 'intMul'), ('rel', 'e9', 'intStore', 4)),
 'mulIntTail': (('call', 'intMul'), ('rel', 'e9', 'intStore', 4)),
 'addIntTail': (('call', 'intAdd'), ('rel', 'e9', 'intStore', 4)),
 'rem32Store': ('895304be0c000000', ('rel', 'eb', 'remTopCommit', 1)),
 'rem64Store': ('488953044c89642460', ('rel', 'e9', 'pcAdvance', 4)),
 'remTopCommit': ('4c89642460', ('rel', 'e9', 'pcAdvance', 4)),
 'unsignedMul64Fail': (('rip', '488b1d', 'executeContext'),
                       ('call', 'overflowRequest'),
                       '488bd3488bc8',
                       ('call', 'throwStop')),
 'unsignedMul32Fail': (('rip', '488b1d', 'executeContext'),
                       ('call', 'overflowRequest'),
                       '488bd3488bc8',
                       ('call', 'throwStop')),
 'signedMul64Fail': (('rip', '488b1d', 'executeContext'),
                     ('call', 'overflowRequest'),
                     '488bd3488bc8',
                     ('call', 'throwStop')),
 'signedMul32Fail': (('rip', '488b1d', 'executeContext'),
                     ('call', 'overflowRequest'),
                     '488bd3488bc8',
                     ('call', 'throwStop')),
 'unsignedAdd64Fail': (('rip', '488b1d', 'executeContext'),
                       ('call', 'overflowRequest'),
                       '488bd3488bc8',
                       ('call', 'throwStop')),
 'signedAdd64Fail': (('rip', '488b1d', 'executeContext'),
                     ('call', 'overflowRequest'),
                     '488bd3488bc8',
                     ('call', 'throwStop')),
 'unsignedAdd32Fail': (('rip', '488b1d', 'executeContext'),
                       ('call', 'overflowRequest'),
                       '488bd3488bc8',
                       ('call', 'throwStop')),
 'signedAdd32Fail': (('rip', '488b1d', 'executeContext'),
                     ('call', 'overflowRequest'),
                     '488bd3488bc8',
                     ('call', 'throwStop'))}
