"""Prove five conditional IFix comparison producers from selected native bytes.

Ceq compares stored bits for scalar words and pointer identity for managed tags;
ordered comparisons select by the left tag alone. Unsigned floating comparisons
include unordered flags, and Cgt_Un's managed route tests left nonnull/right null.
Every normal commit writes Integer and a normalized low Boolean word, preserves
the high word, and consumes one slot. Runtime values, floating exceptions, helper
mutation, aliasing, storage validity and execution are never inferred.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import literal_record,unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults,runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_slice,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class ComparisonRuleError(ValueError):
    """The selected comparison claim lacks its finite native witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise ComparisonRuleError('ifix-comparison.'+label)


_HELPER_REFS={'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper',
 'pointerDifference':'arithmeticWindows.stackPointerSubtract','nullCheck':'negativeFieldRules.helpers.nullCheck',
 'arrayFetch':'initobjTypeOperand.consumerRowFetchHelper','assignmentCheck':'functionPointerRules.helpers.assignmentCheck',
 'managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper','allocateObject':'dispatchRules.helpers.allocateObject'}
_METHOD_REFS={'invalidCtor':'stackReferenceRules.nullConstructor','runtimeException':'delegateConstruction.methodCalls.nullFallbackException'}
_METHODS={'invalidCtor':('System.InvalidProgramException','.ctor',['string'],'void',False),
 'runtimeException':('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False)}
_TAIL_REFS={name:'basicOpcodeRules.sharedWindows.'+name for name in ('zeroRegister','slotWidth','loopState','pcAdvance')}
_TAIL_REFS['slotPcTail']='functionPointerRules.slotPcTail'
_TAGS={'Integer':0,'Long':1,'Float':2,'Double':3,'Object':8,'ValueType':9}
_CELL_NAMES={'invalidType':(1,'System.InvalidProgramException'),'mismatchLiteral':(5,'Ceq for diff type')}
_RULES={
 'Ceq':{'typeSelection':'both-tags-must-match-exception-request-otherwise',
        'predicate':'Integer-or-Float-low32-bits-equal; other-nonmanaged-tags-both32-words-equal; Object-or-ValueType-managed-pointer-equal',
        'unsupportedTagResult':'matching-nonmanaged-tags-use-both-payload-words',
        'mismatchedTagRequest':'InvalidProgramException/throwRuntimeException-wrap-true; false-only-if-normal-return',
        'managedClear':'Object-or-ValueType-route-requests-null-at-both-signedInt32-physical-slot-indexes'},
 'Cgt':{'typeSelection':'left-tag-only-Integer-Long-Float-Double','predicate':'signed32-or-signed64-greater; Float-or-Double-ordered-greater',
        'unsupportedTagResult':'false','mismatchedTagRequest':'none','managedClear':'none-explicit-in-selected-route'},
 'Clt':{'typeSelection':'left-tag-only-Integer-Long-Float-Double','predicate':'signed32-or-signed64-less; Float-or-Double-ordered-less',
        'unsupportedTagResult':'false','mismatchedTagRequest':'none','managedClear':'none-explicit-in-selected-route'},
 'Cgt_Un':{'typeSelection':'left-tag-only-Integer-Long-Float-Double-Object-ValueType',
        'predicate':'unsigned32-or-unsigned64-greater; Float-or-Double-greater-or-unordered; Object-or-ValueType-left-nonnull-and-right-null',
        'unsupportedTagResult':'false','mismatchedTagRequest':'none','managedClear':'none-explicit-in-selected-route'},
 'Clt_Un':{'typeSelection':'left-tag-only-Integer-Long-Float-Double','predicate':'unsigned32-or-unsigned64-less; Float-or-Double-less-or-unordered',
        'unsupportedTagResult':'false','mismatchedTagRequest':'none','managedClear':'none-explicit-in-selected-route'},
}


def _claims(spec: dict) -> dict[str,dict]:
    _need(spec.get('schema')=='endfield.ifix-vm-comparison-rules.v1' and spec.get('evidenceBoundary')=='conditional'
      and spec.get('executionBoundary')=='unobserved' and spec.get('slotBytes')==12 and spec.get('instructionBytes')==8
      and spec.get('operandUse')=='ignored' and spec.get('resultTag')=='Integer' and spec.get('resultTagId')==0
      and spec.get('resultValue1')=='normalized-Boolean-0-or-1' and spec.get('resultValue2')=='preserved'
      and spec.get('stackDeltaSlots')==-1 and spec.get('normalNextInstructionDelta')==1
      and spec.get('storageBoundary')=='valid-stable-12-byte-slots-and-in-bounds-managed-array-selections'
      and spec.get('helperBoundary')=='normal-selected-helper-return-and-no-helper-slot-mutation-assumed'
      and spec.get('aliasBoundary')=='runtime-helper-mutation-and-slot-overlap-unobserved'
      and spec.get('managedClearBoundary')=='checked-helper-in-bounds-store-route-only'
      and spec.get('floatingBoundary')=='native-COMIS-flags-if-control-returns-normally; floating-exception-state-unobserved'
      and spec.get('dispatchProofRef')=='dispatchRules' and spec.get('valueLayoutRef')=='constrainedTypeOperand.stackEffect.valueLayout'
      and spec.get('helperRefs')==_HELPER_REFS and spec.get('methodRefs')==_METHOD_REFS and spec.get('tailRefs')==_TAIL_REFS
      and spec.get('tagMembers')==_TAGS,'unsupported schema/layout/reference/boundary')
    rows={row.get('opcode'):row for row in spec['rules']}
    _need(len(rows)==len(spec['rules']) and set(rows)==set(_RULES),'comparison family differs')
    for name,row in rows.items():
        _need(all(row.get(key)==value for key,value in _RULES[name].items()),'predicate claims differ: '+name)
    return rows


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int]) -> bytes:
    p=_Program(at)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='rel':
            prefix,target,size=args;raw=bytes.fromhex(prefix)
            displacement=targets[target]-(at+len(p.raw)+len(raw)+size)
            p.add(raw+displacement.to_bytes(size,'little',signed=True))
        else:_need(False,'unknown finite comparison token')
    return p.finish()


def _value_layout(image: Any,contract: dict) -> None:
    row=_ref(contract,'constrainedTypeOperand.stackEffect.valueLayout');md=image.metadata
    _need(row.get('type')=='IFix.Core.Value' and row.get('fieldOffsets')=={'Type':16,'Value1':20,'Value2':24},'Value declaration differs')
    owners=[t for t in md.types if md.type_full_name(t)=='IFix.Core.Value'];_need(len(owners)==1 and owners[0].bitfield&1,'Value owner/carrier differs')
    fields={md.string(f.name_index):f for f in md.fields_for(owners[0])}
    _need(all(name in fields and _type(image,fields[name].type_index)==kind for name,kind in [('Type','IFix.Core.ValueType'),('Value1','int'),('Value2','int')]),'Value raw fields differ')
    for name in ('Type','Value1','Value2'):
        pointer=image.pe.u64_at_va(_rva(image.registration['types'])+fields[name].type_index*8)
        _need(not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&0x10,'Value static field differs: '+name)
    offsets=runtime_type_field_offsets(md,image.pe,image.registration,owners[0].index)
    _need(all(offsets.get(name)==off for name,off in row['fieldOffsets'].items()),'Value native offsets differ')


def _cells(image: Any,spec: dict) -> dict[str,int]:
    rows={row['name']:row for row in spec['usageCells']};_need(len(rows)==len(spec['usageCells']) and set(rows)==set(_CELL_NAMES),'comparison cell set differs');result={}
    for name,(tag,identity) in _CELL_NAMES.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(row.get('usageTag')==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'stored comparison usage differs: '+name);result[name]=at
        if tag==1:
            idx=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='ifix-comparison.type',offset=at)
            _need(_type(image,idx)==identity,'comparison raw nonbyref type differs')
        else:
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData']
            idx=unresolved_usage_index(raw,table.size//8,tag=5,source='ifix-comparison.literal',offset=at);off=table.offset+idx*8
            start,size=literal_record(md.buf[off:off+8],pool.size,source='ifix-comparison.literal',offset=off)
            _need(md.buf[pool.offset+start:pool.offset+start+size]==identity.encode(),'Ceq mismatch literal differs')
    return result


def validate_comparison_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Prove fixed tag/predicate/store programs; caller owns prior whole-input gates."""
    rules=_claims(spec);_value_layout(image,contract)
    tags={x['name']:x['id'] for x in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(tags.get(name)==value for name,value in _TAGS.items()),'actual ValueType enum differs')
    targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'helper.'+name);targets[name]=at
        if name=='subtractSlot':_expect(raw,bytes.fromhex('4863c2482bc8488bc1c3'),'subtractSlot')
        elif name=='pointerDifference':_expect(raw,bytes.fromhex('482bca488bc1c3'),'pointerDifference')
        elif name=='arrayFetch':_expect(raw,bytes.fromhex('4883ec283b5118730a488b44d1204883c428c3'),'arrayFetch.in-bounds-leaf')
        elif name=='managedStore':
            _expect(raw[:9],bytes.fromhex('4883ec283b5118735d'),'managedStore.in-bounds-check')
            _expect(raw[16:23],bytes.fromhex('4c8944d120744a'),'managedStore.selected-store')
    for name,identity in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[name]));row.setdefault('parameterCount',len(identity[2]))
        targets[name]=_identity(image,row,identity,name,extents)
    helpers={row['name']:row for row in spec['helpers']};_need(len(helpers)==len(spec['helpers']) and set(helpers)=={'pointerEquals'},'comparison helper set differs')
    row=helpers['pointerEquals'];at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount'])
    _need(row.get('bodyBoundary')=='complete-pointer-equality-leaf','pointer equality boundary differs');_hash(raw,row,'pointerEquals');_expect(raw,bytes.fromhex('483bca0f94c0c3'),'pointerEquals');targets['pointerEquals']=at
    for name,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=_slice(body,body_rva,at,row['byteCount'],name);_hash(raw,row,'tail.'+name);targets[name]=at
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    _expect(_slice(body,body_rva,targets['slotPcTail'],5,'slotPcTail'),bytes.fromhex('be0c000000'),'slotPcTail')
    _need(targets['slotPcTail']+5==targets['pcAdvance'],'slot/PC tail adjacency differs')
    cells=_cells(image,spec);blocks={row['name']:row for row in spec['blocks']}
    _need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_BLOCKS),'comparison block set differs')
    targets.update({name:_rva(row['rva']) for name,row in blocks.items()})
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'block.'+name);_expect(raw,_program(name,targets[name],targets,cells),'block.'+name)
    _need(targets['commitSIL']+blocks['commitSIL']['byteCount']==targets['topCommit'],'SIL/top commit adjacency differs')
    dispatch=contract['dispatchRules'];_need(dispatch.get('schema')=='endfield.ifix-vm-dispatch-rules.v1','missing reviewed dispatch prerequisite')
    for name,shape in [('zeroCompare','413bcd'),('subEsi','2bce')]:
        row=dispatch['extensions'][name];raw=_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name);_hash(raw,row,'dispatch.'+name);_expect(raw,bytes.fromhex(shape),'dispatch.'+name)
    entries={_rva(row['entryRva']) for row in dispatch['entryPoints']};checked=[]
    for name,row in rules.items():
        _need(type(row['opcodeId']) is int and row['opcodeId']==opcode_ids.get(name),'actual Code enum differs: '+name)
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],
            zero_compare_rva=_rva(dispatch['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(dispatch['extensions']['subEsi']['rva']),entry_rvas=entries)
        _need(entry==_rva(row['entryRva'])==targets[name],'selected comparison entry differs: '+name)
        checked.append({'opcode':name,'opcodeId':row['opcodeId'],'entryRva':hex(entry),'stackDeltaSlots':-1})
    return {'status':'validated_conditional_comparison_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved','entries':checked,
       'resultTag':'Integer','resultValue1':spec['resultValue1'],'resultValue2':'preserved','managedClearBoundary':spec['managedClearBoundary'],
       'unresolved':['runtime-slot-tags-and-payload-values','managed-index-and-array-storage-validity','floating-exception-state',
                     'exception-allocation-construction-and-throw-outcomes','helper-alias-mutation-and-slot-overlap','actual-execution']}


def project_comparison_rules(decoded: dict,spec: dict) -> list[dict]:
    """Project conditional recipes only; never calculate a runtime comparison result."""
    rules=_claims(spec);result=[]
    for method in decoded['methods']:
        for ins in method['instructions']:
            name=ins['name']
            if name not in rules:continue
            row=rules[name];operand=ins['operandUnsigned']
            _need(type(operand) is int and 0<=operand<=0xffffffff and type(ins['opcode']) is int and ins['opcode']==row['opcodeId'],'malformed operand/opcode: '+name)
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned' not in ins or type(ins['operandSigned']) is int and ins['operandSigned']==signed,'inconsistent signed operand: '+name)
            result.append({'vmMethodIndex':method['index'],'instructionIndex':ins['index'],'offset':ins['offset'],'opcode':name,
               'operandUnsigned':operand,'operandSigned':signed,'operandUse':'ignored','leftSlot':'incoming-top-2','rightSlot':'incoming-top-1',
               'resultSlot':'incoming-top-2','resultTag':'Integer','resultTagId':0,'resultValue1':'normalized-Boolean-0-or-1',
               'resultValue2':'preserved','stackDeltaSlots':-1,'normalNextInstructionDelta':1,**_RULES[name],
               'managedClearBoundary':spec['managedClearBoundary'],'runtimePredicateResult':'unobserved',
               'evidenceBoundary':'conditional','executionBoundary':'unobserved','storageBoundary':spec['storageBoundary'],
               'helperBoundary':spec['helperBoundary'],'floatingBoundary':spec['floatingBoundary']})
            result[-1]['aliasBoundary']=spec['aliasBoundary']
            if name=='Ceq':result[-1]['managedPositionIndex']='signedInt32(trunc(signedInt64(slot-evaluationBase)/12)); sign-extended for helper index'
    return result


def validate_selected_comparison_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Authenticate explicit selected inputs/Execute, then this comparison family."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.comparison');extents=image.mapper.pdata_function_extents(image.pe)
    base=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,contract['consumer']['bodyBytes'])
    ids={row['name']:row['id'] for row in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_comparison_rules(image,contract['comparisonRules'] if spec is None else spec,body,base,ids,contract,extents)


_BLOCKS = {'Ceq': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8be048894424588bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd8418af5488bc8',
         ('call', 'nullCheck'),
         '8b3b498bcc',
         ('call', 'nullCheck'),
         '413b3c247444',
         ('rip', '488b0d', 'invalidType'),
         ('call', 'allocateObject'),
         '488bf8488bc8',
         ('call', 'nullCheck'),
         '4533c0',
         ('rip', '488b15', 'mismatchLiteral'),
         '488bcf',
         ('call', 'invalidCtor'),
         '4533c941b001488bd7488b8c24f0030000',
         ('call', 'runtimeException'),
         ('rel', 'e9', 'commitSIL', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '833b08747a488bcb',
         ('call', 'nullCheck'),
         '833b09746d488bcb',
         ('call', 'nullCheck'),
         '8b7b04498bcc',
         ('call', 'nullCheck'),
         '413b7c2404400f94c6488bcb',
         ('call', 'nullCheck'),
         '44392b',
         ('rel', '0f84', 'commitSIL', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '833b02',
         ('rel', '0f84', 'commitSIL', 4),
         '413af57422488bcb',
         ('call', 'nullCheck'),
         '8b7b08498bcc',
         ('call', 'nullCheck'),
         '413b7c2408750840b601',
         ('rel', 'e9', 'commitSIL', 4),
         '418af5',
         ('rel', 'e9', 'commitSIL', 4),
         '488bbc2410040000488bd7488bcb',
         ('call', 'pointerDifference'),
         '488bc848beabaaaaaaaaaaaa2a488bc648f7e94c8bf249d1fe498bc648c1e83f4c03f0488bd7498bcc',
         ('call', 'pointerDifference'),
         '488bc8488bc648f7e94c8bfa49d1ff498bc748c1e83f4c03f8488bcb',
         ('call', 'nullCheck'),
         '48637b04488bb42408040000488bce',
         ('call', 'nullCheck'),
         '488bd7488bce',
         ('call', 'arrayFetch'),
         '488bf0498bcc',
         ('call', 'nullCheck'),
         '49637c2404488b8c2408040000',
         ('call', 'nullCheck'),
         '488bd7488bbc2408040000488bcf',
         ('call', 'arrayFetch'),
         '488bd0488bce',
         ('call', 'pointerEquals'),
         '408af0488bcf',
         ('call', 'nullCheck'),
         '33d2488bcf',
         ('call', 'assignmentCheck'),
         '4963d64533c0488bcf',
         ('call', 'managedStore'),
         '488bcf',
         ('call', 'nullCheck'),
         '33d2488bcf',
         ('call', 'assignmentCheck'),
         '4963d74533c0488bcf',
         ('call', 'managedStore'),
         'e970feffff'),
 'Cgt': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8be048894424588bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd8410fb6fd488bc8',
         ('call', 'nullCheck'),
         '8b03413bc5746d83e801744983e801742383f801757e488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bcc',
         ('call', 'nullCheck'),
         '66410f2f742404eb1b488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bcc',
         ('call', 'nullCheck'),
         '410f2f742404400f97c7eb3f488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bcc',
         ('call', 'nullCheck'),
         '493b7c2404400f9fc7eb20488bcb',
         ('call', 'nullCheck'),
         '8b7304498bcc',
         ('call', 'nullCheck'),
         '413b742404b8010000000f4ff8488bcb',
         ('call', 'nullCheck'),
         '44892b418bf5413afd400f95c6488bcb',
         ('call', 'nullCheck'),
         '897304',
         ('rel', 'e9', 'topCommit', 4)),
 'Clt': ('8bd6498bcc',
         ('call', 'subtractSlot'),
         '4c8be048894424588bd6488bc8',
         ('call', 'subtractSlot'),
         '488bd8410fb6fd488bc8',
         ('call', 'nullCheck'),
         '8b03413bc5747e83e801745783e801742e83f801',
         ('rel', '0f85', 'commitDIL', 4),
         '488bcb',
         ('call', 'nullCheck'),
         'f20f107304498bcc',
         ('call', 'nullCheck'),
         'f2410f10442404660f2fc6',
         ('rel', 'e9', 'floatSetA', 4),
         '488bcb',
         ('call', 'nullCheck'),
         'f30f107304498bcc',
         ('call', 'nullCheck'),
         'f3410f104424040f2fc6',
         ('rel', 'e9', 'floatSetA', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '488b7b04498bcc',
         ('call', 'nullCheck'),
         '493b7c2404400f9cc7',
         ('rel', 'e9', 'commitDIL', 4),
         '488bcb',
         ('call', 'nullCheck'),
         '8b7304498bcc',
         ('call', 'nullCheck'),
         '413b742404b8010000000f4cf8',
         ('rel', 'e9', 'commitDIL', 4)),
 'Cgt_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '4c8be048894424588bd6488bc8',
            ('call', 'subtractSlot'),
            '488bd8410fb6f5488bc8',
            ('call', 'nullCheck'),
            '8b0b83f9050f8fb70000000f8414010000413bcd0f848a00000083e901746a83e901742b83f9010f85f8000000488bcb',
            ('call', 'nullCheck'),
            'f20f107304498bcc',
            ('call', 'nullCheck'),
            'f2410f10442404660f2fc6eb1f488bcb',
            ('call', 'nullCheck'),
            'f30f107304498bcc',
            ('call', 'nullCheck'),
            'f3410f104424040f2fc6418bcd0f92c1418bc5413bcd0f94c0413bc5400f94c6e99c000000488bcb',
            ('call', 'nullCheck'),
            '488b7b04498bcc',
            ('call', 'nullCheck'),
            '493b7c2404eb18488bcb',
            ('call', 'nullCheck'),
            '8b7b04498bcc',
            ('call', 'nullCheck'),
            '413b7c2404400f97c6eb6383e906745e83e901745983e901740583f901754f488bcb',
            ('call', 'nullCheck'),
            '48637b04498bcf',
            ('call', 'nullCheck'),
            '488bd7498bcf',
            ('call', 'arrayFetch'),
            '493bc5742b498bcc',
            ('call', 'nullCheck'),
            '49637c2404498bcf',
            ('call', 'nullCheck'),
            '488bd7498bcf',
            ('call', 'arrayFetch'),
            '493bc5b8010000000f44f0488bcb',
            ('call', 'nullCheck'),
            '44892b418bfd413af5400f95c7488bcb',
            ('call', 'nullCheck'),
            '897b044c89642460',
            ('rel', 'e9', 'slotPcTail', 4)),
 'Clt_Un': ('8bd6498bcc',
            ('call', 'subtractSlot'),
            '4c8be048894424588bd6488bc8',
            ('call', 'subtractSlot'),
            '488bd8410fb6fd488bc8',
            ('call', 'nullCheck'),
            '8b03413bc50f848900000083e801746283e801742783f801',
            ('rel', '0f85', 'commitDIL', 4),
            '488bcb',
            ('call', 'nullCheck'),
            'f20f107304498bcc',
            ('call', 'nullCheck'),
            '66410f2f742404eb1b488bcb',
            ('call', 'nullCheck'),
            'f30f107304498bcc',
            ('call', 'nullCheck'),
            '410f2f742404418bcd0f92c1418bc5413bcd0f94c0413bc5400f94c7',
            ('rel', 'e9', 'commitDIL', 4),
            '488bcb',
            ('call', 'nullCheck'),
            '488b7b04498bcc',
            ('call', 'nullCheck'),
            '493b7c2404400f92c7',
            ('rel', 'e9', 'commitDIL', 4),
            '488bcb',
            ('call', 'nullCheck'),
            '8b7304498bcc',
            ('call', 'nullCheck'),
            '413b742404b8010000000f42f8',
            ('rel', 'e9', 'commitDIL', 4)),
 'floatSetA': ('400f97c7', ('rel', 'eb', 'commitDIL', 1)),
 'commitDIL': ('488bcb',
               ('call', 'nullCheck'),
               '44892b418bf5413afd400f95c6488bcb',
               ('call', 'nullCheck'),
               '897304',
               ('rel', 'e9', 'topCommit', 4)),
 'commitSIL': ('488bcb', ('call', 'nullCheck'), '44892b418bfd413af5400f95c7488bcb', ('call', 'nullCheck'), '897b04'),
 'topCommit': ('4c89642460', ('rel', 'e9', 'slotPcTail', 4))}
