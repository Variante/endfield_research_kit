"""Selected conditional branches and signed physical-record target recipes.

Taken targets are relative to the current physical eight-byte instruction.
Brtrue/Brfalse pop one slot and clear its physical managed position. Binary
predicates pop two slots without explicit managed clearing. Equality compares
raw Float bits; ordered/unordered relational behavior follows native COMIS
flags. Runtime predicates, target validity, helper mutation and exceptional
transfers are unobserved. No branch is executed by this module.
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


class BranchRuleError(ValueError):
    """A branch declaration lacks its selected finite witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise BranchRuleError('ifix-branch.'+label)


_HELPER_REFS={'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper','nullCheck':'negativeFieldRules.helpers.nullCheck',
 'slotMultiply':'arithmeticWindows.signedSlotMultiply','pointerAdd':'arithmeticWindows.pointerAdd','pointerDifference':'arithmeticWindows.stackPointerSubtract',
 'arrayFetch':'initobjTypeOperand.consumerRowFetchHelper','assignmentCheck':'functionPointerRules.helpers.assignmentCheck',
 'managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper','usageResolve':'objectConversionRules.helpers.usageResolveThunk',
 'boxTag':'objectConversionRules.helpers.enumBoxThunk','allocateObject':'objectConversionRules.helpers.allocationThunk','throwStop':'objectConversionRules.helpers.throwStop'}
_METHOD_REFS={'concatPair':'objectConversionRules.methods.concatPair','notImplementedCtor':'objectConversionRules.methods.unsupportedCtor',
 'invalidCtor':'stackReferenceRules.nullConstructor','runtimeException':'delegateConstruction.methodCalls.nullFallbackException'}
_METHODS={'concatPair':('System.String','Concat',['object','object'],'string',True),
 'notImplementedCtor':('System.NotImplementedException','.ctor',['string'],'void',False),
 'invalidCtor':('System.InvalidProgramException','.ctor',['string'],'void',False),
 'runtimeException':('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False)}
_TAIL_REFS={name:'basicOpcodeRules.sharedWindows.'+name for name in ('zeroRegister','slotWidth','loopState','pcAdvance')}
_TAIL_REFS['defaultPcJoin']='dispatchRules.blocks.defaultPcJoin'
_CELL_REFS={'valueType':'bitwiseRules.usageCells.valueType','invalidType':'bitwiseRules.usageCells.invalidType',
 'executeContext':'bitwiseRules.usageCells.executeContext','notImplementedType':'dispatchRules.usageCells.notImplementedType'}
_FLOAT_REF='literalControlRules.floatConstant'
_CELLS={'valueType':(1,'IFix.Core.ValueType'),'invalidType':(1,'System.InvalidProgramException'),
 'executeContext':(3,'IFix.Core.VirtualMachine.Execute'),'notImplementedType':(1,'System.NotImplementedException'),
 'bleLiteral':(5,'Blt for '),'bgtLiteral':(5,'Bgt for ')}
_TAGS={'Integer':0,'Long':1,'Float':2,'Double':3,'Object':8,'ValueType':9}
_BOUNDS={'schema':'endfield.ifix-vm-branch-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'slotBytes':12,'instructionBytes':8,'operandUse':'signed-Int32-physical-record-displacement-from-current-PC',
 'takenTarget':'current-PC + signed-Operand * 8; native Int64/pointer wrap','fallthroughTarget':'current-PC + 8',
 'dispatchProofRef':'dispatchRules','valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout',
 'storageBoundary':'valid-stable-12-byte-slots-and-in-bounds-managed-storage',
 'registerBoundary':'selected-loop-frame-bindings;R12=top,R14=current-PC,R15=managed,R13=0,ESI=12;runtime-entry-unobserved',
 'helperBoundary':'normal-selected-helper-return-and-no-helper-slot-mutation-assumed','aliasBoundary':'runtime-helper-mutation-and-slot-overlap-unobserved',
 'targetBoundary':'authored-physical-storage-candidate-only;runtime-PC-entry-and-target-validity-unobserved',
 'floatingBoundary':'COMIS-flags-on-normal-completion;MXCSR-and-exception-state-unobserved',
 'unaryManagedIndex':'trunc(signedInt64(consumed-slot - evaluationBase)/12); native Int64 index retained',
 'stopBoundary':'checked-wrapper-opaque-call-followed-by-INT3; abnormal-transfer-outcome-unobserved'}
_RULES={
 'Br':{'stackDeltaSlots':0,'typeSelection':'none','predicate':'always','managedClear':'none-explicit'},
 'Brtrue':{'stackDeltaSlots':-1,'typeSelection':'consumed-tag-Integer-Long-Object-ValueType',
   'Integer':'Value1 != 0','Long':'raw64 != 0','Object-ValueType':'managed[signExtend(Value1)] != null','otherTags':'false',
   'managedClear':'null-request-at-consumed-physical-managed-position-for-all-tags'},
 'Brfalse':{'stackDeltaSlots':-1,'typeSelection':'consumed-tag-Integer-Long-Object-ValueType',
   'Integer':'Value1 == 0','Long':'raw64 == 0','Object-ValueType':'managed[signExtend(Value1)] == null','otherTags':'false',
   'managedClear':'null-request-at-consumed-physical-managed-position-for-all-tags'},
 'Beq':{'stackDeltaSlots':-2,'typeSelection':'both-tags-must-match','differentTags':'false','Integer-Float':'equal low32 raw bits',
   'Object-ValueType':'equal managed pointers selected by signExtended Value1 indexes','otherMatchingTags':'equal both payload words','managedClear':'none-explicit'},
 'Bne_Un':{'stackDeltaSlots':-2,'typeSelection':'both-tags-compared','differentTags':'true','Integer-Float':'unequal low32 raw bits',
   'Object-ValueType':'unequal managed pointers selected by signExtended Value1 indexes','otherMatchingTags':'unequal either payload word','managedClear':'none-explicit'},
 'Blt':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'signed lower < upper',
   'Float-Double':'ordered lower < upper','otherTags':'false','managedClear':'none-explicit'},
 'Bgt':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'signed lower > upper',
   'Float-Double':'ordered lower > upper','otherTags':'InvalidProgramException-message-request/stop-wrapper','managedClear':'none-explicit'},
 'Bge':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'signed lower >= upper',
   'Float-Double':'ordered lower >= upper','otherTags':'false','managedClear':'none-explicit'},
 'Ble':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'signed lower <= upper',
   'Float-Double':'ordered lower <= upper','otherTags':'NotImplementedException-message-request/runtimeException-wrap-true; false-on-normal-return','managedClear':'none-explicit'},
 'Blt_Un':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'unsigned lower < upper',
   'Float-Double':'lower < upper OR unordered','otherTags':'false','managedClear':'none-explicit'},
 'Bgt_Un':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'unsigned lower > upper',
   'Float-Double':'lower > upper OR unordered','otherTags':'false','managedClear':'none-explicit'},
 'Bge_Un':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'unsigned lower >= upper',
   'Float-Double':'lower >= upper OR unordered','otherTags':'false','managedClear':'none-explicit'},
 'Ble_Un':{'stackDeltaSlots':-2,'typeSelection':'lower-tag-only-upper-tag-unchecked','Integer-Long':'unsigned lower <= upper',
   'Float-Double':'lower <= upper OR unordered','otherTags':'false','managedClear':'none-explicit'},
}


def _claims(spec: dict) -> dict[str,dict]:
    _need(all(spec.get(k)==v for k,v in _BOUNDS.items()) and type(spec.get('slotBytes')) is int and type(spec.get('instructionBytes')) is int
        and spec.get('helperRefs')==_HELPER_REFS and spec.get('methodRefs')==_METHOD_REFS and spec.get('tailRefs')==_TAIL_REFS
        and spec.get('cellRefs')==_CELL_REFS and spec.get('floatConstantRef')==_FLOAT_REF and spec.get('tagMembers')==_TAGS,'unsupported schema/reference/layout/boundary')
    rows={row['opcode']:row for row in spec['rules']};_need(len(rows)==len(spec['rules']) and set(rows)==set(_RULES),'branch family differs')
    for name,row in rows.items():_need(type(row.get('stackDeltaSlots')) is int and all(row.get(k)==v for k,v in _RULES[name].items()),'branch claims differ: '+name)
    return rows


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='rel':
            prefix,target,size=args;raw=bytes.fromhex(prefix);disp=targets[target]-(at+len(p.raw)+len(raw)+size);p.add(raw+disp.to_bytes(size,'little',signed=True))
        else:_need(False,'unknown finite branch token')
    return p.finish()


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    own={r['name']:r for r in spec['usageCells']};_need(len(own)==len(spec['usageCells']) and set(own)=={'bleLiteral','bgtLiteral'},'own literal set differs')
    rows={n:_ref(contract,path) for n,path in _CELL_REFS.items()};rows.update(own);result={}
    for name,(tag,identity) in _CELLS.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(type(row.get('usageTag')) is int and row['usageTag']==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'stored usage differs: '+name);result[name]=at
        if tag==1:
            idx=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='ifix-branch.type',offset=at);_need(_type(image,idx)==identity,'raw nonbyref carrier differs: '+name)
        elif tag==3:
            idx=unresolved_usage_index(raw,len(image.metadata.methods),tag=tag,source='ifix-branch.context',offset=at);md=image.metadata;m=md.methods[idx]
            owners=[t for t in md.types if t.method_start<=idx<t.method_start+t.method_count]
            _need(len(owners)==1 and md.type_full_name(owners[0])=='IFix.Core.VirtualMachine' and md.string(m.name_index)=='Execute'
              and m.token==_rva(contract['consumer']['token']) and m.parameter_count==len(_EXECUTE_TYPES)
              and [_type(image,p.type_index) for p in md.parameters_for(m)]==_EXECUTE_TYPES and _type(image,m.return_type)=='IFix.Core.Value*'
              and not m.flags&0x10 and m.generic_container_index==-1 and image.method_pointer_va(m)==image.pe.image_base+_rva(contract['consumer']['rva']),
              'stored Execute MethodDef context differs')
        else:
            md=image.metadata;t,p=md.sections['stringLiteral'],md.sections['stringLiteralData'];idx=unresolved_usage_index(raw,t.size//8,tag=tag,source='ifix-branch.literal',offset=at)
            off=t.offset+idx*8;begin,size=literal_record(md.buf[off:off+8],p.size,source='ifix-branch.literal',offset=off)
            _need(md.buf[p.offset+begin:p.offset+begin+size]==identity.encode(),'stored branch message differs: '+name)
    row=_ref(contract,_FLOAT_REF);at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount'])
    _need(type(row['byteCount']) is int and row['byteCount']==4 and raw==bytes.fromhex(row['hex'])==bytes.fromhex('00000080'),'float restore constant differs');result['floatMask']=at
    return result


def validate_branch_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Validate finite branch/store/tail programs, with conditional runtime state."""
    rules=_claims(spec);_value_layout(image,contract);tags={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(tags.get(n)==v for n,v in _TAGS.items()),'actual ValueType enum differs');targets={}
    expected={'subtractSlot':'4863c2482bc8488bc1c3','pointerDifference':'482bca488bc1c3','pointerAdd':'488d0411c3',
              'slotMultiply':'4863c2480fafc1c3','arrayFetch':'4883ec283b5118730a488b44d1204883c428c3'}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'helper.'+name);targets[name]=at
        if name in expected:_expect(raw,bytes.fromhex(expected[name]),'helper.'+name)
        elif name=='managedStore':
            _need(len(raw)==23,'managedStore prefix length differs');_expect(raw[:9],bytes.fromhex('4883ec283b5118735d'),'managedStore.in-bounds-check');_expect(raw[16:23],bytes.fromhex('4c8944d120744a'),'managedStore.selected-store')
        elif name=='throwStop':_need(len(raw)==20 and raw[:14]==bytes.fromhex('4883ec2833c04889413848894140') and raw[14]==0xe8 and raw[19]==0xcc,'stop wrapper shape differs')
    for name,signature in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[name]));row.setdefault('parameterCount',len(signature[2]));targets[name]=_identity(image,row,signature,name,extents)
    for name,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,'tail.'+name);targets[name]=at
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister');_expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    p=_Program(targets['defaultPcJoin']);p.rip('e9',targets['pcAdvance']);_expect(_slice(body,body_rva,p.base,len(p.raw),'defaultPcJoin'),p.finish(),'defaultPcJoin')
    cells=_cells(image,spec,contract);blocks={row['name']:row for row in spec['blocks']};_need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_BLOCKS),'branch block set differs')
    targets.update({n:_rva(r['rva']) for n,r in blocks.items()})
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'block.'+name);_expect(raw,_program(name,targets[name],targets,cells),'block.'+name)
    _need(targets['loopRestore']+8==targets['loopState'] and targets['loopRead']==targets['loopState']+8,'current PC/register restore joins differ')
    dispatch=contract['dispatchRules'];_need(dispatch.get('schema')=='endfield.ifix-vm-dispatch-rules.v1','reviewed dispatch prerequisite missing')
    for name,shape in [('zeroCompare','413bcd'),('subEsi','2bce')]:
        row=dispatch['extensions'][name];raw=_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name);_hash(raw,row,'dispatch.'+name);_expect(raw,bytes.fromhex(shape),'dispatch.'+name)
    entries={_rva(row['entryRva']) for row in dispatch['entryPoints']};checked=[]
    for name,row in rules.items():
        _need(type(row['opcodeId']) is int and row['opcodeId']==opcode_ids.get(name),'Code enum differs: '+name)
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],
            zero_compare_rva=_rva(dispatch['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(dispatch['extensions']['subEsi']['rva']),entry_rvas=entries)
        _need(entry==_rva(row['entryRva'])==targets[name],'selected branch entry differs: '+name);checked.append({'opcode':name,'opcodeId':row['opcodeId'],'entryRva':hex(entry),'stackDeltaSlots':row['stackDeltaSlots']})
    return {'status':'validated_conditional_branch_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved','entries':checked,
        'takenTarget':spec['takenTarget'],'targetBoundary':spec['targetBoundary'],'unaryManagedIndex':spec['unaryManagedIndex'],
        'unresolved':['runtime-predicates-and-helper-results','target-entry-and-native-storage-validity','helper-alias-mutation-and-slot-overlap',
                      'FP-state-and-exception-transfer','actual-execution']}


def project_branch_rules(decoded: dict,spec: dict) -> list[dict]:
    """Join candidate targets to physical stored records without asserting entry."""
    rules=_claims(spec);result=[]
    for method in decoded['methods']:
        records={r['index']:r for r in method['instructions']};count=method['instructionCount'];start=method['codeOffset']
        _need(type(count) is int and count>=0 and type(start) is int and start>=0 and len(records)==len(method['instructions'])==count
          and all(type(r['index']) is int and 0<=r['index']<count and type(r['offset']) is int and r['offset']==start+r['index']*8 for r in method['instructions']),
          'malformed physical instruction inventory')
        for ins in method['instructions']:
            name=ins['name']
            if name not in rules:continue
            row=rules[name];operand=ins['operandUnsigned'];idx=ins['index'];offset=ins['offset']
            _need(type(operand) is int and 0<=operand<=0xffffffff and type(ins['opcode']) is int and ins['opcode']==row['opcodeId']
                  and type(idx) is int and 0<=idx<count and type(offset) is int and offset>=0,'malformed operand/opcode/index: '+name)
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned' not in ins or type(ins['operandSigned']) is int and ins['operandSigned']==signed,'inconsistent signed operand: '+name)
            target=idx+signed;stored=records.get(target);candidate='outside-authored-method-storage' if not 0<=target<count else 'inline-data-record' if stored and stored.get('recordKind')=='inline-data' else 'stored-opcode-record' if stored else 'unresolved-stored-record'
            result.append({'vmMethodIndex':method['index'],'instructionIndex':idx,'offset':offset,'opcode':name,
                'operandUnsigned':operand,'operandSigned':signed,'operandUse':spec['operandUse'],'candidateTargetPhysicalIndex':target,
                'candidateTargetByteOffset':offset+signed*8,'candidateTargetStorage':candidate,'candidateFallthroughPhysicalIndex':idx+1,
                **_RULES[name],**{k:spec[k] for k in ('takenTarget','fallthroughTarget','storageBoundary','registerBoundary','helperBoundary','aliasBoundary','targetBoundary','floatingBoundary','stopBoundary')},
                'runtimePredicateResult':'unobserved','evidenceBoundary':'conditional','executionBoundary':'unobserved'})
            if row['stackDeltaSlots']==-1:result[-1]['managedPositionIndex']=spec['unaryManagedIndex']
    return result


def validate_selected_branch_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Explicit native gate and complete interpreter authentication, offline."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.branches');extents=image.mapper.pdata_function_extents(image.pe)
    base=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,contract['consumer']['bodyBytes']);ids={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_branch_rules(image,contract['branchRules'] if spec is None else spec,body,base,ids,contract,extents)


_BLOCKS = {'Br': ('498bce',
        ('call', 'nullCheck'),
        '49634e04ba08000000',
        ('call', 'slotMultiply'),
        '488bd0498bce',
        ('call', 'pointerAdd'),
        '4c8bf0488944245048898424f8030000',
        ('rel', 'e9', 'loopRead', 4)),
 'Brtrue': ('410fb6fd8bd6498bcc',
            ('call', 'subtractSlot'),
            '4c8be048894424584889442460488bc8',
            ('call', 'nullCheck'),
            '418b0424413bc5751c498bcc',
            ('call', 'nullCheck'),
            '45396c2404418bc50f94c0413bc5400f94c7eb5bb9010000003bc1750f498bcc',
            ('call', 'nullCheck'),
            '4d396c2404ebd983c0f83bc1773c498bcc',
            ('call', 'nullCheck'),
            '49635c2404498bcf',
            ('call', 'nullCheck'),
            '488bd3498bcf',
            ('call', 'arrayFetch'),
            '418bcd493bc50f94c1413bcdb8010000000f44f8488b9c2410040000488bd3498bcc',
            ('call', 'pointerDifference'),
            '498bcf',
            ('call', 'nullCheck'),
            '33d2498bcf',
            ('call', 'assignmentCheck'),
            '488bd3498bcc',
            ('call', 'pointerDifference'),
            '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
            ('call', 'managedStore'),
            ('rel', 'e9', 'unaryDecision', 4)),
 'Brfalse': ('410fb6fd8bd6498bcc',
             ('call', 'subtractSlot'),
             '4c8be048894424584889442460488bc8',
             ('call', 'nullCheck'),
             '418b0424413bc57513498bcc',
             ('call', 'nullCheck'),
             '45396c2404400f94c7eb52b9010000003bc1750f498bcc',
             ('call', 'nullCheck'),
             '4d396c2404ebe283c0f83bc17733498bcc',
             ('call', 'nullCheck'),
             '49635c2404498bcf',
             ('call', 'nullCheck'),
             '488bd3498bcf',
             ('call', 'arrayFetch'),
             '493bc5b8010000000f44f8488b9c2410040000488bd3498bcc',
             ('call', 'pointerDifference'),
             '498bcf',
             ('call', 'nullCheck'),
             '33d2498bcf',
             ('call', 'assignmentCheck'),
             '488bd3498bcc',
             ('call', 'pointerDifference'),
             '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcf',
             ('call', 'managedStore'),
             '413afd',
             ('rel', '0f84', 'pcAdvance', 4),
             '498bce',
             ('call', 'nullCheck'),
             '49634e04ba08000000',
             ('call', 'slotMultiply'),
             '488bd0498bce',
             ('call', 'pointerAdd'),
             '4c8bf0488944245048898424f8030000488bbc24f0030000',
             ('rel', 'e9', 'loopRead', 4)),
 'Blt': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bd88bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '4c8be048894424584889442460488bc8',
         ('call', 'nullCheck'),
         '418b0c24413bcd747f83e901745c83e901742b83f901',
         ('rel', '0f85', 'pcAdvance', 4),
         '498bcc',
         ('call', 'nullCheck'),
         'f2410f10742404488bcb',
         ('call', 'nullCheck'),
         'f20f104304660f2fc6eb1f498bcc',
         ('call', 'nullCheck'),
         'f3410f10742404488bcb',
         ('call', 'nullCheck'),
         'f30f1043040f2fc60f97c0',
         ('rip', 'f30f1035', 'floatMask'),
         'eb3b498bcc',
         ('call', 'nullCheck'),
         '498b7c2404488bcb',
         ('call', 'nullCheck'),
         '483b7b040f9cc0eb1d498bcc',
         ('call', 'nullCheck'),
         '418b7c2404488bcb',
         ('call', 'nullCheck'),
         '3b7b047c0c418ac5413ac5',
         ('rel', '0f84', 'pcAdvance', 4),
         '498bce',
         ('call', 'nullCheck'),
         '49634e04ba08000000',
         ('call', 'slotMultiply'),
         '498bce488bd0',
         ('call', 'pointerAdd'),
         '4c8bf0488944245048898424f8030000',
         ('rel', 'e9', 'loopRestore', 4)),
 'Blt_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '488bd88bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '4c8be048894424584889442460488bc8',
            ('call', 'nullCheck'),
            '418b0c24413bcd0f848700000083e901746183e901742783f901',
            ('rel', '0f85', 'pcAdvance', 4),
            '498bcc',
            ('call', 'nullCheck'),
            'f2410f10742404488bcb',
            ('call', 'nullCheck'),
            '660f2f7304eb1b498bcc',
            ('call', 'nullCheck'),
            'f3410f10742404488bcb',
            ('call', 'nullCheck'),
            '0f2f7304418bcd0f92c1418bc5413bcd0f94c0413bc50f94c0',
            ('rel', 'e9', 'floatRestore', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '498b7c2404488bcb',
            ('call', 'nullCheck'),
            '483b7b040f92c0',
            ('rel', 'e9', 'lessDecision', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '418b7c2404488bcb',
            ('call', 'nullCheck'),
            '3b7b04',
            ('rel', '0f82', 'relationalTaken', 4),
            ('rel', 'e9', 'lessFalse', 4)),
 'Bge': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bd88bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '4c8be048894424584889442460488bc8',
         ('call', 'nullCheck'),
         '418b0c24413bcd0f848100000083e901745283e901742783f901',
         ('rel', '0f85', 'pcAdvance', 4),
         '498bcc',
         ('call', 'nullCheck'),
         'f2410f10742404488bcb',
         ('call', 'nullCheck'),
         '660f2f7304eb1b498bcc',
         ('call', 'nullCheck'),
         'f3410f10742404488bcb',
         ('call', 'nullCheck'),
         '0f2f7304418bc50f92c0',
         ('rel', 'e9', 'booleanInvert', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '498b7c2404488bcb',
         ('call', 'nullCheck'),
         '418bc5483b7b040f9cc0413bc50f94c0',
         ('rel', 'e9', 'lessDecision', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '418b7c2404488bcb',
         ('call', 'nullCheck'),
         '418bc53b7b040f9cc0413bc5',
         ('rel', '0f84', 'relationalTaken', 4),
         ('rel', 'e9', 'lessFalse', 4)),
 'Ble': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bd88bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '4c8be048894424584889442460488bc8',
         ('call', 'nullCheck'),
         '418b0c24413bcd0f84fd00000083e9010f84d000000083e9010f84a300000083f901498bcc7479',
         ('call', 'nullCheck'),
         '418b0424898424e8000000488d9424e8000000',
         ('rip', '488b0d', 'valueType'),
         ('call', 'boxTag'),
         '4533c0488bd0',
         ('rip', '488b0d', 'bleLiteral'),
         ('call', 'concatPair'),
         '488bf8',
         ('rip', '488b0d', 'notImplementedType'),
         ('call', 'allocateObject'),
         '488bd8488bc8',
         ('call', 'nullCheck'),
         '4533c0488bd7488bcb',
         ('call', 'notImplementedCtor'),
         '488b8c24f0030000488bd341b0014533c9',
         ('call', 'runtimeException'),
         ('rel', 'e9', 'defaultPcJoin', 4),
         ('call', 'nullCheck'),
         'f2410f10742404488bcb',
         ('call', 'nullCheck'),
         'f20f104304660f2fc6',
         ('rel', 'e9', 'orderedNotLess', 4),
         '498bcc',
         ('call', 'nullCheck'),
         'f3410f10742404488bcb',
         ('call', 'nullCheck'),
         'f30f1043040f2fc6',
         ('rel', 'e9', 'orderedNotLess', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '498b7c2404488bcb',
         ('call', 'nullCheck'),
         '418bc5483b7b040f9fc0',
         ('rel', 'e9', 'inverseDecision', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '418b7c2404488bcb',
         ('call', 'nullCheck'),
         '418bc53b7b040f9fc0',
         ('rel', 'e9', 'inverseIntegerDecision', 4)),
 'Bgt': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bd88bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '4c8be048894424584889442460488bc8',
         ('call', 'nullCheck'),
         '418b0c24413bcd747583e901744f83e901742a83f901498bcc',
         ('rel', '0f85', 'invalidBgt', 4),
         ('call', 'nullCheck'),
         'f2410f10742404488bcb',
         ('call', 'nullCheck'),
         '660f2f7304',
         ('rel', 'e9', 'floatSetA', 4),
         '498bcc',
         ('call', 'nullCheck'),
         'f3410f10742404488bcb',
         ('call', 'nullCheck'),
         '0f2f7304',
         ('rel', 'e9', 'floatSetA', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '498b7c2404488bcb',
         ('call', 'nullCheck'),
         '483b7b040f9fc0',
         ('rel', 'e9', 'lessDecision', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '418b7c2404488bcb',
         ('call', 'nullCheck'),
         '3b7b04',
         ('rel', '0f8f', 'relationalTaken', 4),
         ('rel', 'e9', 'lessFalse', 4)),
 'Bgt_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '488bd88bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '4c8be048894424584889442460488bc8',
            ('call', 'nullCheck'),
            '418b0c24413bcd747d83e901745783e901742e83f901',
            ('rel', '0f85', 'pcAdvance', 4),
            '498bcc',
            ('call', 'nullCheck'),
            'f2410f10742404488bcb',
            ('call', 'nullCheck'),
            'f20f104304660f2fc6',
            ('rel', 'e9', 'unorderedCF', 4),
            '498bcc',
            ('call', 'nullCheck'),
            'f3410f10742404488bcb',
            ('call', 'nullCheck'),
            'f30f1043040f2fc6',
            ('rel', 'e9', 'unorderedCF', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '498b7c2404488bcb',
            ('call', 'nullCheck'),
            '483b7b040f97c0',
            ('rel', 'e9', 'lessDecision', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '418b7c2404488bcb',
            ('call', 'nullCheck'),
            '3b7b04',
            ('rel', '0f87', 'relationalTaken', 4),
            ('rel', 'e9', 'lessFalse', 4)),
 'Bge_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '488bd88bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '4c8be048894424584889442460488bc8',
            ('call', 'nullCheck'),
            '418b0c24413bcd0f848000000083e901745783e901742e83f901',
            ('rel', '0f85', 'pcAdvance', 4),
            '498bcc',
            ('call', 'nullCheck'),
            'f2410f10742404488bcb',
            ('call', 'nullCheck'),
            'f20f104304660f2fc6',
            ('rel', 'e9', 'unorderedNotGreater', 4),
            '498bcc',
            ('call', 'nullCheck'),
            'f3410f10742404488bcb',
            ('call', 'nullCheck'),
            'f30f1043040f2fc6',
            ('rel', 'e9', 'unorderedNotGreater', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '498b7c2404488bcb',
            ('call', 'nullCheck'),
            '418bc5483b7b040f92c0',
            ('rel', 'e9', 'inverseDecision', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '418b7c2404488bcb',
            ('call', 'nullCheck'),
            '418bc53b7b040f92c0',
            ('rel', 'e9', 'inverseIntegerDecision', 4)),
 'Ble_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '488bd88bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '4c8be048894424584889442460488bc8',
            ('call', 'nullCheck'),
            '418b0c24413bcd747b83e901745283e901742783f901',
            ('rel', '0f85', 'pcAdvance', 4),
            '498bcc',
            ('call', 'nullCheck'),
            'f2410f10742404488bcb',
            ('call', 'nullCheck'),
            '660f2f7304eb1b498bcc',
            ('call', 'nullCheck'),
            'f3410f10742404488bcb',
            ('call', 'nullCheck'),
            '0f2f7304418bc50f97c0',
            ('rel', 'e9', 'booleanInvert', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '498b7c2404488bcb',
            ('call', 'nullCheck'),
            '418bc5483b7b040f97c0',
            ('rel', 'e9', 'inverseDecision', 4),
            '498bcc',
            ('call', 'nullCheck'),
            '418b7c2404488bcb',
            ('call', 'nullCheck'),
            '418bc53b7b040f97c0',
            ('rel', 'e9', 'inverseIntegerDecision', 4)),
 'Bne_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '488bf88bd6498bcc',
            ('call', 'subtractSlot'),
            '8bd6488bc8',
            ('call', 'subtractSlot'),
            '4c8be048894424584889442460488bc8',
            ('call', 'nullCheck'),
            '418b1c24488bcf',
            ('call', 'nullCheck'),
            '3b1f0f85e8000000498bcc',
            ('call', 'nullCheck'),
            '41833c24087478498bcc',
            ('call', 'nullCheck'),
            '41833c24097469498bcc',
            ('call', 'nullCheck'),
            '418b5c2404488bcf',
            ('call', 'nullCheck'),
            '3b5f040f85ac000000498bcc',
            ('call', 'nullCheck'),
            '45392c240f848e000000498bcc',
            ('call', 'nullCheck'),
            '41833c2402747f498bcc',
            ('call', 'nullCheck'),
            '418b5c2408488bcf',
            ('call', 'nullCheck'),
            '418bc53b5f080f94c0413bc5755cb801000000eb58498bcc',
            ('call', 'nullCheck'),
            '49635c2404498bcf',
            ('call', 'nullCheck'),
            '488bd3498bcf',
            ('call', 'arrayFetch'),
            '488bf0488bcf',
            ('call', 'nullCheck'),
            '48635f04498bcf',
            ('call', 'nullCheck'),
            '488bd3498bcf',
            ('call', 'arrayFetch'),
            '418bcd483bf00f94c1413bcd7411be0c000000418bc5413bc5',
            ('rel', '0f84', 'pcAdvance', 4),
            '498bce',
            ('call', 'nullCheck'),
            '49634e04ba08000000',
            ('call', 'slotMultiply'),
            '488bd0498bce',
            ('call', 'pointerAdd'),
            '4c8bf0488944245048898424f8030000be0c000000',
            ('rel', 'e9', 'loopRestore', 4)),
 'Beq': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '488bf88bd6498bcc',
         ('call', 'subtractSlot'),
         '8bd6488bc8',
         ('call', 'subtractSlot'),
         '4c8be048894424584889442460488bc8',
         ('call', 'nullCheck'),
         '418b1c24488bcf',
         ('call', 'nullCheck'),
         '3b1f',
         ('rel', '0f85', 'pcAdvance', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '41833c2408746f498bcc',
         ('call', 'nullCheck'),
         '41833c24097460498bcc',
         ('call', 'nullCheck'),
         '418b5c2404488bcf',
         ('call', 'nullCheck'),
         '3b5f04',
         ('rel', '0f85', 'pcAdvance', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '45392c24',
         ('rel', '0f84', 'equalityTrue', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '41833c2402',
         ('rel', '0f84', 'equalityTrue', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '418b5c2408488bcf',
         ('call', 'nullCheck'),
         '3b5f08',
         ('rel', 'e9', 'equalityFlagDecision', 4),
         '498bcc',
         ('call', 'nullCheck'),
         '49635c2404498bcf',
         ('call', 'nullCheck'),
         '488bd3498bcf',
         ('call', 'arrayFetch'),
         '488bf0488bcf',
         ('call', 'nullCheck'),
         '48635f04498bcf',
         ('call', 'nullCheck'),
         '488bd3498bcf',
         ('call', 'arrayFetch'),
         '483bf0',
         ('rel', 'e9', 'managedEqualityDecision', 4)),
 'floatSetA': ('0f97c0',),
 'floatRestore': (('rip', 'f30f1035', 'floatMask'), ('rel', 'eb', 'lessDecision', 1)),
 'unorderedCF': ('418bcd0f92c1418bc5413bcd0f94c0413bc50f94c0', ('rel', 'e9', 'floatRestore', 4)),
 'booleanInvert': ('413bc50f94c0', ('rel', 'e9', 'floatRestore', 4)),
 'lessFalse': ('418ac5413ac5', ('rel', '0f84', 'pcAdvance', 4)),
 'lessDecision': ('413ac5', ('rel', '0f84', 'pcAdvance', 4)),
 'relationalTaken': ('498bce',
                     ('call', 'nullCheck'),
                     '49634e04ba08000000',
                     ('call', 'slotMultiply'),
                     '498bce488bd0',
                     ('call', 'pointerAdd'),
                     '4c8bf0488944245048898424f8030000',
                     ('rel', 'e9', 'loopRestore', 4)),
 'unaryDecision': ('413afd',
                   ('rel', '0f84', 'pcAdvance', 4),
                   '498bce',
                   ('call', 'nullCheck'),
                   '49634e04ba08000000',
                   ('call', 'slotMultiply'),
                   '488bd0498bce',
                   ('call', 'pointerAdd'),
                   '4c8bf0488944245048898424f8030000488bbc24f0030000',
                   ('rel', 'e9', 'loopRead', 4)),
 'equalityFlagDecision': (('rel', '75', 'equalityFalse', 1), 'b801000000', ('rel', 'eb', 'equalityBoolDecision', 1)),
 'equalityTrue': ('b801000000', ('rel', 'eb', 'equalityBoolDecision', 1)),
 'managedEqualityDecision': (('rel', '74', 'equalityTaken', 1), 'be0c000000418bc5413bc5', ('rel', '0f84', 'pcAdvance', 4)),
 'equalityFalse': ('418bc5413bc5', ('rel', '0f84', 'pcAdvance', 4)),
 'equalityBoolDecision': ('413bc5', ('rel', '0f84', 'pcAdvance', 4)),
 'equalityTaken': ('498bce',
                   ('call', 'nullCheck'),
                   '49634e04ba08000000',
                   ('call', 'slotMultiply'),
                   '488bd0498bce',
                   ('call', 'pointerAdd'),
                   '4c8bf0488944245048898424f8030000be0c000000',
                   ('rel', 'e9', 'loopRestore', 4)),
 'inverseDecision': ('413bc50f94c0', ('rel', 'e9', 'lessDecision', 4)),
 'inverseIntegerDecision': ('413bc5', ('rel', '0f84', 'relationalTaken', 4), ('rel', 'e9', 'lessFalse', 4)),
 'orderedNotLess': ('418bc50f92c0', ('rel', 'e9', 'booleanInvert', 4)),
 'unorderedNotGreater': ('418bc50f97c0', ('rel', 'e9', 'booleanInvert', 4)),
 'invalidBgt': (('call', 'nullCheck'),
                '418b042489842404010000',
                ('rip', '488d0d', 'valueType'),
                ('call', 'usageResolve'),
                '488d942404010000488bc8',
                ('call', 'boxTag'),
                '488bd8',
                ('rip', '488d0d', 'bgtLiteral'),
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
 'loopRestore': ('488bbc24f0030000488b9c2410040000498bce', ('call', 'nullCheck'), '418b0e894c2470'),
 'loopRead': ('498bce', ('call', 'nullCheck'), '418b0e894c2470')}
