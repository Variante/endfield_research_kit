"""Selected bitwise, shift and unary caller programs; no VM execution.

Integer and Long retain their tag and use exact native payload widths. Shifts
mask the upper slot's low word to 31/63. Xor consumes an unsupported lower tag
without writing its payload; Not and Neg leave unsupported tags unchanged.
And/Or/shifts request a boxed-tag message and InvalidProgramException, then
the checked stop wrapper has INT3 after an opaque call. Callee outcomes remain
unobserved. Floating Neg XORs incoming XMM6/7 low lanes; pinned initial sign
mask loads are checked without claiming their preservation to a runtime entry.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import literal_record,unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_comparison_rules import _value_layout
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_slice,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class BitwiseRuleError(ValueError):
    """A bitwise/unary declaration lacks its selected finite witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise BitwiseRuleError('ifix-bitwise.'+label)


_HELPER_REFS={'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper','nullCheck':'negativeFieldRules.helpers.nullCheck',
 'usageResolve':'objectConversionRules.helpers.usageResolveThunk','boxOperand':'objectConversionRules.helpers.enumBoxThunk',
 'allocateObject':'objectConversionRules.helpers.allocationThunk','throwStop':'objectConversionRules.helpers.throwStop'}
_METHOD_REFS={'concatPair':'objectConversionRules.methods.concatPair','invalidCtor':'stackReferenceRules.nullConstructor'}
_METHODS={'concatPair':('System.String','Concat',['object','object'],'string',True),
          'invalidCtor':('System.InvalidProgramException','.ctor',['string'],'void',False)}
_TAIL_REFS={name:'basicOpcodeRules.sharedWindows.'+name for name in ('zeroRegister','slotWidth','loopState','pcAdvance')}
_TAIL_REFS['topCommit']='basicOpcodeRules.sharedWindows.pushTopCommit'
_CELLS={'valueType':(1,'IFix.Core.ValueType'),'invalidType':(1,'System.InvalidProgramException'),
 'executeContext':(3,'IFix.Core.VirtualMachine.Execute'),'shlLiteral':(5,'<< for '),'shrLiteral':(5,'>> for '),
 'andLiteral':(5,'& for '),'orLiteral':(5,'| for ')}
_TAGS={'Integer':0,'Long':1,'Float':2,'Double':3}
_BOUNDS={'schema':'endfield.ifix-vm-bitwise-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'slotBytes':12,'instructionBytes':8,'operandUse':'ignored','resultTag':'preserved','managedClear':'none-explicit-in-selected-caller-routes',
 'dispatchProofRef':'dispatchRules','valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout',
 'storageBoundary':'valid-stable-12-byte-slots','helperBoundary':'normal-selected-helper-return-and-no-helper-slot-mutation-assumed',
 'aliasBoundary':'runtime-helper-mutation-and-slot-overlap-unobserved',
 'floatingMaskBoundary':'incoming-XMM6-low32-and-XMM7-low64; stored-initial-sign-masks-proved-entry-preservation-unobserved',
 'stopBoundary':'checked-wrapper-opaque-call-followed-by-INT3; abnormal-transfer-outcome-unobserved'}
_RULES={
 'And':{'normalStackDeltaSlots':-1,'typeSelection':'left-tag-only-Integer-Long','Integer':'left-low32 AND right-low32; Value2-preserved',
        'Long':'left-raw64 AND right-raw64','otherTags':'InvalidProgramException-message-request/stop-wrapper'},
 'Or':{'normalStackDeltaSlots':-1,'typeSelection':'left-tag-only-Integer-Long','Integer':'left-low32 OR right-low32; Value2-preserved',
        'Long':'left-raw64 OR right-raw64','otherTags':'InvalidProgramException-message-request/stop-wrapper'},
 'Xor':{'normalStackDeltaSlots':-1,'typeSelection':'left-tag-only-Integer-Long','Integer':'left-low32 XOR right-low32; Value2-preserved',
        'Long':'left-raw64 XOR right-raw64','otherTags':'payload-unchanged-normal-pop-one'},
 'Shl':{'normalStackDeltaSlots':-1,'typeSelection':'left-tag-only-Integer-Long','Integer':'left-low32 SHL (right.Value1 AND 31); Value2-preserved',
        'Long':'left-raw64 SHL (right.Value1 AND 63)','otherTags':'InvalidProgramException-message-request/stop-wrapper'},
 'Shr':{'normalStackDeltaSlots':-1,'typeSelection':'left-tag-only-Integer-Long','Integer':'left-low32 SAR (right.Value1 AND 31); Value2-preserved',
        'Long':'left-raw64 SAR (right.Value1 AND 63)','otherTags':'InvalidProgramException-message-request/stop-wrapper'},
 'Shr_Un':{'normalStackDeltaSlots':-1,'typeSelection':'left-tag-only-Integer-Long','Integer':'left-low32 SHR (right.Value1 AND 31); Value2-preserved',
        'Long':'left-raw64 SHR (right.Value1 AND 63)','otherTags':'InvalidProgramException-message-request/stop-wrapper'},
 'Not':{'normalStackDeltaSlots':0,'typeSelection':'top-minus-one-tag-Integer-Long','Integer':'NOT low32; Value2-preserved',
        'Long':'NOT raw64','otherTags':'payload-unchanged-normal-top-unchanged'},
 'Neg':{'normalStackDeltaSlots':0,'typeSelection':'top-minus-one-tag-Integer-Long-Float-Double','Integer':'NEG low32 modulo 2^32; Value2-preserved',
        'Long':'NEG raw64 modulo 2^64','Float':'raw32 XOR low32(XMM6); Value2-preserved','Double':'raw64 XOR low64(XMM7)',
        'otherTags':'payload-unchanged-normal-top-unchanged'},
}


def _claims(spec: dict) -> dict[str,dict]:
    _need(all(spec.get(k)==v for k,v in _BOUNDS.items()) and type(spec.get('slotBytes')) is int and type(spec.get('instructionBytes')) is int
      and spec.get('helperRefs')==_HELPER_REFS and spec.get('methodRefs')==_METHOD_REFS and spec.get('tailRefs')==_TAIL_REFS
      and spec.get('tagMembers')==_TAGS,'unsupported schema/reference/layout/boundary')
    rows={row['opcode']:row for row in spec['rules']};_need(len(rows)==len(spec['rules']) and set(rows)==set(_RULES),'bitwise family differs')
    for name,row in rows.items():_need(type(row.get('normalStackDeltaSlots')) is int and all(row.get(k)==v for k,v in _RULES[name].items()),'operator claims differ: '+name)
    return rows


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='rel':
            prefix,target,size=args;raw=bytes.fromhex(prefix);disp=targets[target]-(at+len(p.raw)+len(raw)+size)
            p.add(raw+disp.to_bytes(size,'little',signed=True))
        else:_need(False,'unknown finite bitwise token')
    return p.finish()


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    rows={row['name']:row for row in spec['usageCells']};_need(len(rows)==len(spec['usageCells']) and set(rows)==set(_CELLS),'usage set differs');result={}
    for name,(tag,identity) in _CELLS.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(row.get('usageTag')==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'stored usage differs: '+name);result[name]=at
        if tag==1:
            idx=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='ifix-bitwise.type',offset=at);_need(_type(image,idx)==identity,'raw nonbyref carrier differs: '+name)
        elif tag==3:
            idx=unresolved_usage_index(raw,len(image.metadata.methods),tag=tag,source='ifix-bitwise.context',offset=at)
            md=image.metadata;method=md.methods[idx];owners=[t for t in md.types if t.method_start<=idx<t.method_start+t.method_count]
            _need(len(owners)==1 and md.type_full_name(owners[0])=='IFix.Core.VirtualMachine' and md.string(method.name_index)=='Execute'
              and method.token==_rva(contract['consumer']['token']) and method.parameter_count==len(_EXECUTE_TYPES)
              and [_type(image,p.type_index) for p in md.parameters_for(method)]==_EXECUTE_TYPES
              and _type(image,method.return_type)=='IFix.Core.Value*' and not method.flags&0x10 and method.generic_container_index==-1
              and image.method_pointer_va(method)==image.pe.image_base+_rva(contract['consumer']['rva']),'stored Execute MethodDef context differs')
        else:
            md=image.metadata;t,p=md.sections['stringLiteral'],md.sections['stringLiteralData'];idx=unresolved_usage_index(raw,t.size//8,tag=tag,source='ifix-bitwise.literal',offset=at)
            off=t.offset+idx*8;begin,size=literal_record(md.buf[off:off+8],p.size,source='ifix-bitwise.literal',offset=off)
            _need(md.buf[p.offset+begin:p.offset+begin+size]==identity.encode(),'stored operator message differs: '+name)
    masks={row['name']:row for row in spec['masks']};_need(len(masks)==len(spec['masks']) and set(masks)=={'floatMask','doubleMask'},'mask set differs')
    for name,count,value in [('floatMask',4,1<<31),('doubleMask',8,1<<63)]:
        row=masks[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,name)
        _need(row['byteCount']==count and int.from_bytes(raw,'little')==value,'stored sign mask differs: '+name);result[name]=at
    return result


def validate_bitwise_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Validate complete supported programs and bounded stop requests offline."""
    rules=_claims(spec);_value_layout(image,contract)
    tags={row['name']:row['id'] for row in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(tags.get(n)==v for n,v in _TAGS.items()),'actual ValueType enum differs');targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'helper.'+name);targets[name]=at
        if name=='subtractSlot':_expect(raw,bytes.fromhex('4863c2482bc8488bc1c3'),'subtractSlot')
        elif name=='throwStop':
            _need(len(raw)==20 and raw[:14]==bytes.fromhex('4883ec2833c04889413848894140') and raw[14]==0xe8 and raw[19]==0xcc,'stop wrapper shape differs')
    for name,identity in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[name]));row.setdefault('parameterCount',len(identity[2]));targets[name]=_identity(image,row,identity,name,extents)
    for name,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,'tail.'+name);targets[name]=at
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    p=_Program(targets['topCommit']);p.add('4c8be048894424584889442460');p.rip('e9',targets['pcAdvance'])
    _expect(_slice(body,body_rva,p.base,len(p.raw),'topCommit'),p.finish(),'topCommit')
    cells=_cells(image,spec,contract);blocks={row['name']:row for row in spec['blocks']}
    _need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_BLOCKS),'bitwise block set differs');targets.update({n:_rva(r['rva']) for n,r in blocks.items()})
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'block.'+name);_expect(raw,_program(name,targets[name],targets,cells),'block.'+name)
    dispatch=contract['dispatchRules'];_need(dispatch.get('schema')=='endfield.ifix-vm-dispatch-rules.v1','reviewed dispatch prerequisite missing')
    for name,shape in [('zeroCompare','413bcd'),('subEsi','2bce')]:
        row=dispatch['extensions'][name];raw=_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name);_hash(raw,row,'dispatch.'+name);_expect(raw,bytes.fromhex(shape),'dispatch.'+name)
    entries={_rva(row['entryRva']) for row in dispatch['entryPoints']};checked=[]
    for name,row in rules.items():
        _need(type(row['opcodeId']) is int and row['opcodeId']==opcode_ids.get(name),'Code enum differs: '+name)
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],
            zero_compare_rva=_rva(dispatch['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(dispatch['extensions']['subEsi']['rva']),entry_rvas=entries)
        _need(entry==_rva(row['entryRva'])==targets[name],'selected bitwise entry differs: '+name)
        checked.append({'opcode':name,'opcodeId':row['opcodeId'],'entryRva':hex(entry),'normalStackDeltaSlots':row['normalStackDeltaSlots']})
    return {'status':'validated_conditional_bitwise_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved','entries':checked,
       'floatingMaskBoundary':spec['floatingMaskBoundary'],'stopBoundary':spec['stopBoundary'],'managedClear':spec['managedClear'],
       'unresolved':['runtime-tags-payloads-and-shift-counts','FP-Neg-incoming-register-mask-preservation-and-entry',
                     'boxing-message-allocation-constructor-and-abnormal-transfer-outcomes','helper-alias-mutation-and-storage-validity','actual-execution']}


def project_bitwise_rules(decoded: dict,spec: dict) -> list[dict]:
    """Project stored opcode recipes; do not compute runtime values or entry."""
    rules=_claims(spec);result=[]
    for method in decoded['methods']:
        for ins in method['instructions']:
            name=ins['name']
            if name not in rules:continue
            row=rules[name];operand=ins['operandUnsigned'];_need(type(operand) is int and 0<=operand<=0xffffffff and type(ins['opcode']) is int and ins['opcode']==row['opcodeId'],'malformed operand/opcode: '+name)
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned' not in ins or type(ins['operandSigned']) is int and ins['operandSigned']==signed,'inconsistent signed operand: '+name)
            result.append({'vmMethodIndex':method['index'],'instructionIndex':ins['index'],'offset':ins['offset'],'opcode':name,
              'operandUnsigned':operand,'operandSigned':signed,'operandUse':'ignored','resultSlot':'incoming-top-1' if name in ('Neg','Not') else 'incoming-top-2',
              'resultTag':'preserved','normalNextInstructionDelta':1,**_RULES[name],
              'managedClear':spec['managedClear'],'floatingMaskBoundary':spec['floatingMaskBoundary'],'stopBoundary':spec['stopBoundary'],
              'storageBoundary':spec['storageBoundary'],'helperBoundary':spec['helperBoundary'],'aliasBoundary':spec['aliasBoundary'],
              'runtimeResult':'unobserved','evidenceBoundary':'conditional','executionBoundary':'unobserved'})
    return result


def validate_selected_bitwise_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Explicit selected native gate, with no root fallback or process execution."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.bitwise');extents=image.mapper.pdata_function_extents(image.pe)
    base=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,contract['consumer']['bodyBytes'])
    ids={row['name']:row['id'] for row in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_bitwise_rules(image,contract['bitwiseRules'] if spec is None else spec,body,base,ids,contract,extents)


_BLOCKS = {'Shl': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd88bd6498bcc',
         ('call', 'subtractSlot'),
         '488bc8',
         ('call', 'nullCheck'),
         '8bd6498bcc',
         ('call', 'subtractSlot'),
         '8b7004488bcb',
         ('call', 'nullCheck'),
         '488bcb44392b751d',
         ('call', 'nullCheck'),
         '8b7b04488bcb',
         ('call', 'nullCheck'),
         '83e61f408aced3e7897b04eb27833b01',
         ('rel', '0f85', 'invalidShl', 4),
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b430483e63f408ace48d3e048894304be0c0000008bd6498bcc',
         ('call', 'subtractSlot'),
         ('rel', 'e9', 'topCommit', 4)),
 'Shr_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '488bd88bd6498bcc',
            ('call', 'subtractSlot'),
            '488bc8',
            ('call', 'nullCheck'),
            '8bd6498bcc',
            ('call', 'subtractSlot'),
            '8b7004488bcb',
            ('call', 'nullCheck'),
            '488bcb44392b751d',
            ('call', 'nullCheck'),
            '8b7b04488bcb',
            ('call', 'nullCheck'),
            '83e61f408aced3ef',
            ('rel', 'e9', 'shift32Store', 4),
            '833b01',
            ('rel', '0f85', 'invalidShr_Un', 4),
            ('call', 'nullCheck'),
            '488bcb',
            ('call', 'nullCheck'),
            '488b430483e63f408ace48d3e8',
            ('rel', 'e9', 'shift64Store', 4)),
 'Shr': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd88bd6498bcc',
         ('call', 'subtractSlot'),
         '488bc8',
         ('call', 'nullCheck'),
         '8bd6498bcc',
         ('call', 'subtractSlot'),
         '8b7004488bcb',
         ('call', 'nullCheck'),
         '488bcb44392b751d',
         ('call', 'nullCheck'),
         '8b7b04488bcb',
         ('call', 'nullCheck'),
         '83e61f408aced3ff',
         ('rel', 'e9', 'shift32Store', 4),
         '833b01',
         ('rel', '0f85', 'invalidShr', 4),
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b430483e63f408ace48d3f8',
         ('rel', 'e9', 'shift64Store', 4)),
 'And': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8bf08bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd8488bc8',
         ('call', 'nullCheck'),
         '488bcb833b017526',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bce',
         ('call', 'nullCheck'),
         '498b46044823c748894304eb2f44392b',
         ('rel', '0f85', 'invalidAnd', 4),
         ('call', 'nullCheck'),
         '8b7304498bce',
         ('call', 'nullCheck'),
         '418b7e04488bcb',
         ('call', 'nullCheck'),
         '23fe897b04be0c0000004d8be64c897424584c89742460',
         ('rel', 'e9', 'pcAdvance', 4)),
 'Or': ('8bd6498bcc',
        ('call', 'subtractSlot'),
        '4c8bf08bd6498bcc',
        ('call', 'subtractSlot'),
        '8bd6488bc8',
        ('call', 'subtractSlot'),
        '488bd8488bc8',
        ('call', 'nullCheck'),
        '488bcb833b017525',
        ('call', 'nullCheck'),
        '488bcb',
        ('call', 'nullCheck'),
        '488b7b04498bce',
        ('call', 'nullCheck'),
        '498b4604480bc7',
        ('rel', 'e9', 'and64Store', 4),
        '44392b',
        ('rel', '0f85', 'invalidOr', 4),
        ('call', 'nullCheck'),
        '8b7304498bce',
        ('call', 'nullCheck'),
        '418b7e04488bcb',
        ('call', 'nullCheck'),
        '0bfe',
        ('rel', 'e9', 'and32Store', 4)),
 'Xor': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8be048894424588bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd8488bc8',
         ('call', 'nullCheck'),
         '833b01752d488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bcc',
         ('call', 'nullCheck'),
         '498b4424044833c748894304',
         ('rel', 'e9', 'xorTopCommit', 4),
         '44392b',
         ('rel', '0f85', 'xorTopCommit', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7304498bcc',
         ('call', 'nullCheck'),
         '418b7c2404488bcb',
         ('call', 'nullCheck'),
         '33fe897b04',
         ('rel', 'e9', 'xor32Tail', 4)),
 'Not': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bd8488bc8',
         ('call', 'nullCheck'),
         '833b017519488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '48f75304',
         ('rel', 'e9', 'pcAdvance', 4),
         '44392b',
         ('rel', '0f85', 'pcAdvance', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7b04488bcb',
         ('call', 'nullCheck'),
         'f7d7',
         ('rel', 'e9', 'wordStore', 4)),
 'Neg': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bd8488bc8',
         ('call', 'nullCheck'),
         '8b03413bc5747783e801745283e801742b83f801',
         ('rel', '0f85', 'pcAdvance', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f1043040f57c7f20f114304',
         ('rel', 'e9', 'pcAdvance', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f1043040f57c6f30f114304',
         ('rel', 'e9', 'pcAdvance', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488bcb',
         ('call', 'nullCheck'),
         '488b430448f7d848894304',
         ('rel', 'e9', 'pcAdvance', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7b04488bcb',
         ('call', 'nullCheck'),
         'f7df',
         ('rel', 'e9', 'wordStore', 4)),
 'shift32Store': ('897b04', ('rel', 'eb', 'shiftPop', 1)),
 'shift64Store': ('48894304be0c0000008bd6498bcc', ('call', 'subtractSlot'), ('rel', 'e9', 'topCommit', 4)),
 'shiftPop': ('be0c0000008bd6498bcc', ('call', 'subtractSlot'), ('rel', 'e9', 'topCommit', 4)),
 'and64Store': ('48894304', ('rel', 'eb', 'andCommit', 1)),
 'and32Store': ('897b04be0c0000004d8be64c897424584c89742460', ('rel', 'e9', 'pcAdvance', 4)),
 'andCommit': ('4d8be64c897424584c89742460', ('rel', 'e9', 'pcAdvance', 4)),
 'xor32Tail': ('be0c000000', ('rel', 'eb', 'xorTopCommit', 1)),
 'xorTopCommit': ('4c89642460', ('rel', 'e9', 'pcAdvance', 4)),
 'wordStore': ('897b04', ('rel', 'e9', 'pcAdvance', 4)),
 'invalidShl': (('call', 'nullCheck'),
                '8b0389842450010000',
                ('rip', '488d0d', 'valueType'),
                ('call', 'usageResolve'),
                '488d942450010000488bc8',
                ('call', 'boxOperand'),
                '488bd8',
                ('rip', '488d0d', 'shlLiteral'),
                ('call', 'usageResolve'),
                '4533c0488bd3488bc8',
                ('call', 'concatPair'),
                '488bf8',
                ('rip', '488d0d', 'invalidType'),
                ('call', 'usageResolve'),
                '488bc8',
                ('call', 'allocateObject'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '4533c0488bd7488bcb',
                ('call', 'invalidCtor'),
                ('rip', '488d0d', 'executeContext'),
                ('call', 'usageResolve'),
                '488bd0488bcb',
                ('call', 'throwStop')),
 'invalidShr_Un': (('call', 'nullCheck'),
                   '8b0389842454010000',
                   ('rip', '488d0d', 'valueType'),
                   ('call', 'usageResolve'),
                   '488d942454010000488bc8',
                   ('call', 'boxOperand'),
                   '488bd8',
                   ('rip', '488d0d', 'shrLiteral'),
                   ('call', 'usageResolve'),
                   '4533c0488bd3488bc8',
                   ('call', 'concatPair'),
                   '488bf8',
                   ('rip', '488d0d', 'invalidType'),
                   ('call', 'usageResolve'),
                   '488bc8',
                   ('call', 'allocateObject'),
                   '488bd8488bc8',
                   ('call', 'nullCheck'),
                   '4533c0488bd7488bcb',
                   ('call', 'invalidCtor'),
                   ('rip', '488d0d', 'executeContext'),
                   ('call', 'usageResolve'),
                   '488bd0488bcb',
                   ('call', 'throwStop')),
 'invalidShr': (('call', 'nullCheck'),
                '8b0389842480010000',
                ('rip', '488d0d', 'valueType'),
                ('call', 'usageResolve'),
                '488d942480010000488bc8',
                ('call', 'boxOperand'),
                '488bd8',
                ('rip', '488d0d', 'shrLiteral'),
                ('call', 'usageResolve'),
                '4533c0488bd3488bc8',
                ('call', 'concatPair'),
                '488bf8',
                ('rip', '488d0d', 'invalidType'),
                ('call', 'usageResolve'),
                '488bc8',
                ('call', 'allocateObject'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '4533c0488bd7488bcb',
                ('call', 'invalidCtor'),
                ('rip', '488d0d', 'executeContext'),
                ('call', 'usageResolve'),
                '488bd0488bcb',
                ('call', 'throwStop')),
 'invalidAnd': (('call', 'nullCheck'),
                '8b0389842400010000',
                ('rip', '488d0d', 'valueType'),
                ('call', 'usageResolve'),
                '488d942400010000488bc8',
                ('call', 'boxOperand'),
                '488bd8',
                ('rip', '488d0d', 'andLiteral'),
                ('call', 'usageResolve'),
                '4533c0488bd3488bc8',
                ('call', 'concatPair'),
                '488bf8',
                ('rip', '488d0d', 'invalidType'),
                ('call', 'usageResolve'),
                '488bc8',
                ('call', 'allocateObject'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '4533c0488bd7488bcb',
                ('call', 'invalidCtor'),
                ('rip', '488d0d', 'executeContext'),
                ('call', 'usageResolve'),
                '488bd0488bcb',
                ('call', 'throwStop')),
 'invalidOr': (('call', 'nullCheck'),
               '8b0389842408010000',
               ('rip', '488d0d', 'valueType'),
               ('call', 'usageResolve'),
               '488d942408010000488bc8',
               ('call', 'boxOperand'),
               '488bd8',
               ('rip', '488d0d', 'orLiteral'),
               ('call', 'usageResolve'),
               '4533c0488bd3488bc8',
               ('call', 'concatPair'),
               '488bf8',
               ('rip', '488d0d', 'invalidType'),
               ('call', 'usageResolve'),
               '488bc8',
               ('call', 'allocateObject'),
               '488bd8488bc8',
               ('call', 'nullCheck'),
               '4533c0488bd7488bcb',
               ('call', 'invalidCtor'),
               ('rip', '488d0d', 'executeContext'),
               ('call', 'usageResolve'),
               '488bd0488bcb',
               ('call', 'throwStop')),
 'maskInitial': (('rip', 'f30f1035', 'floatMask'), ('rip', 'f20f103d', 'doubleMask'))}
