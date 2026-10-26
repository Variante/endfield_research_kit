"""Conditional IFix exception requests, stored handler selection and resumes.

Throw ignores the descriptor tag and requests a safe cast of its indexed
managed value. Rethrow requests the stored exception home. Leave records a
pending absolute instruction index; Endfinally selects a stored handler or
resumes that index. getExceptionHandler scans stored order with half-open try
ranges, querying virtual slot 30 for Catch entries. A conditional catch entry
clears signed-index managed ranges and stores an Object descriptor before
requesting the handler PC. No native exception delivery or VM is executed.

Native virtual dispatch, helper outcomes/mutation, storage validity, loop
entry and exception delivery remain unobserved. The exception-store leafs
prove pointer reads and a depth decrement, not runtime container validity.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import enum_members,field_defaults,runtime_type_field_offsets
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry
from scripts.game_data.ifix_vm_comparison_rules import _value_layout
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_slice,_hash,_expect,_type,_identity
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES


class ExceptionDispatchRuleError(ValueError):
    """An exception-control declaration lacks its finite native witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise ExceptionDispatchRuleError('ifix-exception.'+label)


_HELPER_REFS={'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper',
 'nullCheck':'negativeFieldRules.helpers.nullCheck','slotMultiply':'arithmeticWindows.signedSlotMultiply',
 'pointerAdd':'arithmeticWindows.pointerAdd','pointerDifference':'arithmeticWindows.stackPointerSubtract',
 'arrayFetch':'initobjTypeOperand.consumerRowFetchHelper','handlerFetch':'functionPointerRules.helpers.anonymousInfoFetch',
 'assignmentCheck':'functionPointerRules.helpers.assignmentCheck','managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
 'usageResolve':'objectConversionRules.helpers.usageResolveThunk','cast':'referenceUpdateRules.helpers.cast',
 'throwStop':'objectConversionRules.helpers.throwStop','int32Add':'negativeFieldRules.helpers.int32Add',
 'int32Subtract':'indirectOpcodeRules.helpers.intSubtract','advancePointer':'basicOpcodeRules.helpers.advancePointer',
 'boundsFailure':'referenceUpdateRules.helpers.boundsFailure','nullFailure':'referenceUpdateRules.helpers.nullFailure',
 'assignableRequest':'objectOpcodeRules.helpers.assignableRequest','classPrepare':'chainFieldRules.helpers.classPrepare'}
_METHOD_REFS={'objectGetType':'functionPointerRules.helpers.objectGetType'}
_METHODS={'objectGetType':('System.Object','GetType',[],'System.Type',False),
 'getExceptionHandler':('IFix.Core.VirtualMachine','getExceptionHandler',['int','System.Type','int'],'IFix.Core.ExceptionHandler',False)}
_TAIL_REFS={n:'basicOpcodeRules.sharedWindows.'+n for n in ('zeroRegister','slotWidth','loopState','pcAdvance')}
_CELL_REFS={'executeContext':'bitwiseRules.usageCells.executeContext'}
_FIELDS={'vm':('IFix.Core.VirtualMachine',{'exceptionHandlers':'IFix.Core.ExceptionHandler[][]'}),
 'handler':('IFix.Core.ExceptionHandler',{'CatchType':'System.Type','HandlerType':'IFix.Core.ExceptionHandlerType',
   'TryStart':'int','TryEnd':'int','HandlerStart':'int'})}
_EH_TAGS={'Catch':0,'Filter':1,'Finally':2,'Fault':4}
_BOUNDS={'schema':'endfield.ifix-vm-exception-dispatch-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'slotBytes':12,'instructionBytes':8,'dispatchProofRef':'dispatchRules','valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout',
 'registerBoundary':'selected-loop-frame-bindings;R12=top,R14=PC,R15=managed,RBX=evaluationBase,R13=0,ESI=12;runtime-entry-unobserved',
 'frameBoundary':'selected-stored-frame-homes;argument/local/count/PC-runtime-values-unobserved',
 'storageBoundary':'valid-stable-slot-array-handler-and-exception-container-storage-required',
 'helperBoundary':'normal-selected-helper-return-and-no-helper-slot-mutation-assumed',
 'aliasBoundary':'helper-alias-mutation-slot-overlap-and-container-storage-validity-unresolved',
 'stopBoundary':'checked-wrapper-opaque-call-followed-by-INT3;exception-delivery-and-abnormal-transfer-unobserved',
 'handlerSelection':'first-stored-order:Finally-or-Catch-with-nonzero-virtual-query-AL;TryStart<=signed-ipc<TryEnd;Filter-Fault-skipped',
 'handlerQueryOrder':'CatchType-null-check-and-virtual-query-before-try-range-check;Finally-skips-query',
 'virtualBoundary':'slot30-CatchType-receiver-runtime-Type-argument-request;optimized-sharing-and-runtime-vtable-binding-unresolved',
 'catchEntryBoundary':'conditional-selected-native-catch-continuation-entry;native-EH-delivery-container-push-and-current-exception-unobserved',
 'handlerResumeBoundary':'handler-PC-and-top-homes-written;exception-store-pop;subsequent-register-restore-loop-unresolved',
 'clearLoopBoundary':'signed-Int32-range-counter-wrap;termination-bounds-and-storage-not-inferred',
 'targetBoundary':'authored-physical-storage-candidate-only;runtime-PC-entry-and-target-validity-unobserved'}
_RULES={
 'Throw':{'operandUse':'unused','valueSelection':'managed[signExtend(top-minus-one.Value1)];tag-unchecked;safe-cast-System.Exception',
   'managedClear':'null-request-at-trunc(signedInt64(top-evaluationBase)/12)-1;Int64-index-retained',
   'topEffect':'stored-top-home-minus-one-only-before-stop;top-register-and-normal-top-home-not-rewritten',
   'control':'throwStop(cast-result,stored-Execute-context) request'},
 'Rethrow':{'operandUse':'unused','valueSelection':'stored-current-exception-home',
   'managedClear':'none-explicit','topEffect':'unchanged-before-stop','control':'throwStop(stored-exception,stored-Execute-context) request'},
 'Leave':{'operandUse':'whole-signed-Int32-absolute-physical-index','pendingWrite':'authored-Operand-bits',
   'topEffect':'unchanged','control':'common-PC-plus-eight-request;later-loop-EH-control-unresolved'},
 'Endfinally':{'operandUse':'whole-signed-Int32-stored-handler-index-or-minus-one-sentinel',
   'pendingZero':'top-minus-one-managed-Value1-safe-cast;clear-signExtend(Int32(trunc((top-base)/12)-1));stored-top-home-pop;stop-request',
   'pendingNonzeroSentinel':'codeBase+signExtend(pending)*8;clear-pending;write-PC-homes;loop-read-request',
   'pendingNonzeroHandler':'exceptionHandlers[signed-methodIndex][signed-Operand];HandlerType-unchecked',
   'pendingInsideTry':'codeBase+signExtend(pending)*8;clear-pending;write-PC-homes;loop-restore-request',
   'pendingOutsideTry':'codeBase+signExtend(HandlerStart)*8;preserve-pending;write-PC-homes;loop-restore-request'}}
_CATCH_RULES={
 'acquire':'read pointer at container+signExtend(Int32(depth))*8-8;store current-exception home;restore codeBase home;ipc=Int32(trunc(signedInt64(savedPC-codeBase)/8));Object.GetType request;getExceptionHandler request',
 'handler':'newSlot=stored-localBase+signExtend(stored-localCount)*12;old/new positions=Int32(trunc(signedInt64(slot-evaluationBase)/12));clear managed signed-Int32 [newPosition,oldPosition);store Object tag8 and Value1=newPosition preserving Value2;managed[signExtend(newPosition)]=stored-exception request;top=newSlot+12;PC=codeBase+signExtend(HandlerStart)*8;pop exception-container depth;later-loop-unresolved',
 'noHandler':'clear managed signed-Int32 [Int32(trunc((argumentBase-evaluationBase)/12))-refCount,Int32(trunc((storedTop-evaluationBase)/12)));if nonnull topWriteBack write argumentBase-signExtend(refCount)*12;pop exception-container depth;request stop with stored exception',
 'containerPop':'depth=Int32(depth-1);return old selected last pointer;no explicit element clear'}


def _claims(spec: dict) -> dict[str,dict]:
    _need(all(spec.get(k)==v for k,v in _BOUNDS.items()) and type(spec.get('slotBytes')) is int and type(spec.get('instructionBytes')) is int
      and spec.get('helperRefs')==_HELPER_REFS and spec.get('methodRefs')==_METHOD_REFS and spec.get('tailRefs')==_TAIL_REFS
      and spec.get('cellRefs')==_CELL_REFS and spec.get('handlerEnumMembers')==_EH_TAGS and spec.get('catchRules')==_CATCH_RULES,'unsupported schema/reference/conditional boundary')
    rows={r['opcode']:r for r in spec['rules']};_need(len(rows)==len(spec['rules']) and set(rows)==set(_RULES),'opcode rule set differs')
    for name,row in rows.items():_need(all(row.get(k)==v for k,v in _RULES[name].items()),'opcode claim differs: '+name)
    return rows


def _layouts(image: Any,spec: dict,contract: dict) -> dict[str,dict[str,int]]:
    rows=spec['fieldLayouts'];_need(set(rows)==set(_FIELDS),'layout owner set differs');md=image.metadata;result={}
    for role,(owner_name,fields) in _FIELDS.items():
        row=rows[role];owners=[t for t in md.types if md.type_full_name(t)==owner_name]
        _need(len(owners)==1 and not owners[0].bitfield&1 and row.get('type')==owner_name and set(row['fields'])==set(fields),'layout owner/field set differs: '+role)
        owner=owners[0];offsets=runtime_type_field_offsets(md,image.pe,image.registration,owner.index);definitions={md.string(f.name_index):f for f in md.fields_for(owner)};result[role]={}
        for name,typ in fields.items():
            f=definitions.get(name);r=row['fields'][name]
            _need(f is not None and r.get('type')==typ and _type(image,f.type_index)==typ and type(r.get('offset')) is int
                and offsets.get(name)==r['offset'] and 0<=r['offset']<128,'raw nonbyref layout differs: '+role+'.'+name)
            ptr=image.pe.u64_at_va(_rva(image.registration['types'])+f.type_index*8)
            carrier=image.pe.bytes_at_va(ptr,16)
            _need(not int.from_bytes(carrier[8:10],'little')&0x10,'instance layout has static carrier: '+name)
            kind=0x08 if typ=='int' else 0x11 if typ=='IFix.Core.ExceptionHandlerType' else 0x1d if typ.endswith('[][]') else 0x12
            _need(carrier[10]==kind,'raw field carrier kind differs: '+name)
            result[role][name]=r['offset']
    eh=contract['exceptionHandler'];_need(eh.get('type')=='IFix.Core.ExceptionHandler' and all(result['handler'][n]==eh['fieldOffsets'][n] for n in result['handler']),'inherited handler layout differs')
    _need({r['name']:r['id'] for r in enum_members(md,field_defaults(md),'IFix.Core.ExceptionHandlerType')}==_EH_TAGS,'HandlerType enum differs')
    _value_layout(image,contract)
    _need(next((r['id'] for r in enum_members(md,field_defaults(md),'IFix.Core.ValueType') if r['name']=='Object'),None)==8,'Object tag differs')
    return result


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    rows={r['name']:r for r in spec['usageCells']};_need(len(rows)==len(spec['usageCells']) and set(rows)=={'exceptionType'},'own usage cell set differs')
    rows.update({n:_ref(contract,path) for n,path in _CELL_REFS.items()});result={}
    for name,(tag,identity) in {'exceptionType':(1,'System.Exception'),'executeContext':(3,'IFix.Core.VirtualMachine.Execute')}.items():
        row=rows[name];at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(type(row.get('usageTag')) is int and row['usageTag']==tag and row.get('identity')==identity and raw==bytes.fromhex(row['rawHex']),'stored usage differs: '+name);result[name]=at
        if tag==1:
            idx=unresolved_usage_index(raw,image.registration['typesCount'],tag=tag,source='ifix-EH.type',offset=at);_need(_type(image,idx)==identity,'Exception raw nonbyref type differs')
        else:
            md=image.metadata;idx=unresolved_usage_index(raw,len(md.methods),tag=tag,source='ifix-EH.context',offset=at);m=md.methods[idx]
            owners=[t for t in md.types if t.method_start<=idx<t.method_start+t.method_count]
            _need(len(owners)==1 and md.type_full_name(owners[0])=='IFix.Core.VirtualMachine' and md.string(m.name_index)=='Execute'
              and m.token==_rva(contract['consumer']['token']) and m.parameter_count==len(_EXECUTE_TYPES)
              and [_type(image,p.type_index) for p in md.parameters_for(m)]==_EXECUTE_TYPES and _type(image,m.return_type)=='IFix.Core.Value*'
              and not m.flags&0x10 and m.generic_container_index==-1 and image.method_pointer_va(m)==image.pe.image_base+_rva(contract['consumer']['rva']),
              'stored Execute MethodDef context differs')
    return result


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int],fields: dict[str,dict[str,int]]) -> bytes:
    p=_Program(at)
    for token in _BLOCKS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]])
        elif kind=='field':p.add(bytes.fromhex(args[0])+bytes([fields[args[1]][args[2]]]))
        elif kind=='rel':
            prefix,target,size=args;raw=bytes.fromhex(prefix);disp=targets[target]-(at+len(p.raw)+len(raw)+size);p.add(raw+disp.to_bytes(size,'little',signed=True))
        else:_need(False,'unknown finite token')
    return p.finish()


def validate_exception_dispatch_rules(image: Any,spec: dict,body: bytes,body_rva: int,opcode_ids: dict[str,int],contract: dict,extents: dict[int,int]) -> dict:
    """Caller supplies authenticated selected inputs, Execute and prerequisites."""
    rules=_claims(spec);fields=_layouts(image,spec,contract);targets={}
    leaves={'subtractSlot':'4863c2482bc8488bc1c3','pointerDifference':'482bca488bc1c3','pointerAdd':'488d0411c3',
      'slotMultiply':'4863c2480fafc1c3','arrayFetch':'4883ec283b5118730a488b44d1204883c428c3',
      'int32Add':'8d0411c3','int32Subtract':'2bca8bc1c3','advancePointer':'4863c24803c1c3'}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,'helper.'+name);targets[name]=at
        if name in leaves:_expect(raw,bytes.fromhex(leaves[name]),'helper.'+name)
        elif name=='managedStore':
            _need(len(raw)==23 and raw[:9]==bytes.fromhex('4883ec283b5118735d') and raw[16:23]==bytes.fromhex('4c8944d120744a'),'managed store selected prefix differs')
        elif name=='throwStop':_need(len(raw)==20 and raw[:14]==bytes.fromhex('4883ec2833c04889413848894140') and raw[14]==0xe8 and raw[19]==0xcc,'stop wrapper shape differs')
    row=_ref(contract,_HELPER_REFS['handlerFetch']);raw=image.pe.bytes_at_va(image.pe.image_base+targets['handlerFetch'],row['byteCount'])
    p=_Program(targets['handlerFetch']);p.add('4883ec283b51187206');p.call(targets['boundsFailure']);p.add('cc488b44d1204883c428c3')
    _expect(raw,p.finish(),'handlerFetch')
    for name,hex_value in {'exceptionStoreRead':'48634110488b44c1f8c3','exceptionStorePop':'486351108d42ff894110488b44d1f8c3'}.items():
        row=spec['helpers'][name];at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,name);_expect(raw,bytes.fromhex(hex_value),name);targets[name]=at
    _need(set(spec['helpers'])=={'exceptionStoreRead','exceptionStorePop'},'own helper set differs')
    for name,signature in _METHODS.items():
        row=_ref(contract,_METHOD_REFS[name]) if name in _METHOD_REFS else spec['methods'][name]
        row=dict(row);row.setdefault('parameterCount',len(signature[2]))
        if name=='objectGetType':row.setdefault('bodyBoundary','entry-window-callee-outcome-unresolved')
        targets[name]=_identity(image,row,signature,name,extents)
    _need(set(spec['methods'])=={'getExceptionHandler'},'own method set differs')
    _identity(image,spec['virtualMethod'],('System.Type','IsAssignableFrom',['System.Type'],'bool',False),'IsAssignableFrom',extents,virtual_slot=30)
    row=_ref(contract,_HELPER_REFS['assignableRequest']);raw=image.pe.bytes_at_va(image.pe.image_base+targets['assignableRequest'],row['byteCount'])
    _expect(raw,_program('assignablePrefix',targets['assignableRequest'],targets,{},fields),'assignablePrefix')
    row=spec['methods']['getExceptionHandler'];raw=image.pe.bytes_at_va(image.pe.image_base+targets['getExceptionHandler'],row['bodyBytes'])
    _expect(raw,_program('getExceptionHandler',targets['getExceptionHandler'],targets,{},fields),'getExceptionHandler')
    for name,path in _TAIL_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);_hash(_slice(body,body_rva,at,row['byteCount'],name),row,'tail.'+name);targets[name]=at
    _expect(_slice(body,body_rva,targets['zeroRegister'],3,'zeroRegister'),bytes.fromhex('4533ed'),'zeroRegister')
    _expect(_slice(body,body_rva,targets['slotWidth'],5,'slotWidth'),bytes.fromhex('be0c000000'),'slotWidth')
    cells=_cells(image,spec,contract);blocks={r['name']:r for r in spec['blocks']}
    _need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_BLOCKS)-{'getExceptionHandler','assignablePrefix'},'block set differs')
    targets.update({n:_rva(r['rva']) for n,r in blocks.items()});targets['unhandledPop']=targets['unhandled']+50
    for name,row in blocks.items():
        raw=_slice(body,body_rva,targets[name],row['byteCount'],name);_hash(raw,row,'block.'+name);_expect(raw,_program(name,targets[name],targets,cells,fields),'block.'+name)
    _need(targets['loopRead']==targets['loopState']+8 and targets['loopRestore']+8==targets['loopState'],'loop read/register joins differ')
    d=contract['dispatchRules'];_need(d.get('schema')=='endfield.ifix-vm-dispatch-rules.v1','dispatch prerequisite missing')
    for name,shape in [('zeroCompare','413bcd'),('subEsi','2bce')]:
        row=d['extensions'][name];raw=_slice(body,body_rva,_rva(row['rva']),row['byteCount'],name);_hash(raw,row,'dispatch.'+name);_expect(raw,bytes.fromhex(shape),'dispatch.'+name)
    entries={_rva(r['entryRva']) for r in d['entryPoints']};checked=[]
    for name,row in rules.items():
        _need(type(row['opcodeId']) is int and row['opcodeId']==opcode_ids.get(name),'Code enum differs: '+name)
        entry=resolve_selected_dispatch_entry(body,body_rva,_rva(contract['basicOpcodeRules']['dispatchStartRva']),row['opcodeId'],zero_compare_rva=_rva(d['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(d['extensions']['subEsi']['rva']),entry_rvas=entries)
        _need(entry==_rva(row['entryRva'])==targets[name],'selected entry differs: '+name);checked.append({'opcode':name,'opcodeId':row['opcodeId'],'entryRva':hex(entry),**_RULES[name]})
    return {'status':'validated_conditional_exception_dispatch_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved','entries':checked,
      'handlerSelection':spec['handlerSelection'],'handlerQueryOrder':spec['handlerQueryOrder'],'catchRules':spec['catchRules'],'catchEntryBoundary':spec['catchEntryBoundary'],
      'unresolved':['native-EH-delivery-and-container-push','runtime-vtable-binding-optimized-sharing-and-query-result','runtime-handler-and-exception-values',
          'slot-array-container-validity-and-helper-mutation','clear-loop-termination-overflow-and-bounds','subsequent-loop-register-restore-and-target-entry','actual-execution']}


def project_exception_dispatch_rules(decoded: dict,spec: dict) -> list[dict]:
    """Preserve authored handler/absolute-index candidates without execution."""
    rules=_claims(spec);out=[]
    for method in decoded['methods']:
        count=method['instructionCount'];start=method['codeOffset'];records={r['index']:r for r in method['instructions']}
        _need(type(count) is int and count>=0 and type(start) is int and start>=0 and len(records)==len(method['instructions'])==count
            and all(type(r['index']) is int and 0<=r['index']<count and type(r['offset']) is int and r['offset']==start+r['index']*8 for r in method['instructions']),'malformed physical inventory')
        for ins in method['instructions']:
            name=ins['name']
            if name not in rules:continue
            operand=ins['operandUnsigned'];_need(type(operand) is int and 0<=operand<=0xffffffff and type(ins['opcode']) is int and ins['opcode']==rules[name]['opcodeId'],'malformed authored operand/opcode')
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned' not in ins or type(ins['operandSigned']) is int and ins['operandSigned']==signed,'inconsistent signed operand')
            row=dict(vmMethodIndex=method['index'],instructionIndex=ins['index'],offset=ins['offset'],opcode=name,operandUnsigned=operand,operandSigned=signed,**_RULES[name],
                evidenceBoundary='conditional',executionBoundary='unobserved',runtimeException='unobserved',**{k:spec[k] for k in ('storageBoundary','registerBoundary','helperBoundary','stopBoundary','targetBoundary')})
            if name=='Leave':
                candidate=records.get(signed);row.update(candidateTargetPhysicalIndex=signed,candidateTargetByteOffset=start+signed*8,candidateTargetStorage='outside-authored-method-storage' if not 0<=signed<count else 'inline-data-record' if candidate and candidate.get('recordKind')=='inline-data' else 'stored-opcode-record')
            elif name=='Endfinally':row.update(authoredHandlerIndex=None if signed==-1 else signed,handlerCandidateBoundary='minus-one-sentinel' if signed==-1 else 'stored-handler-row-runtime-table-unobserved',pendingRuntimeIndex='unobserved')
            out.append(row)
    return out


def validate_selected_exception_dispatch_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Explicit input gate and complete Execute identity; never execute native."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.exception-dispatch');extents=image.mapper.pdata_function_extents(image.pe)
    base=_identity(image,contract['consumer'],('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),'Execute',extents)
    body=image.pe.bytes_at_va(image.pe.image_base+base,contract['consumer']['bodyBytes']);ids={r['name']:r['id'] for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code')}
    return validate_exception_dispatch_rules(image,contract['exceptionDispatchRules'] if spec is None else spec,body,base,ids,contract,extents)

_BLOCKS = {'Endfinally': ('44396c2474',
                ('rel', '0f84', 'pendingZeroThrow', 4),
                '498bce',
                ('call', 'nullCheck'),
                'b8ffffffff41394604',
                ('rel', '0f84', 'pendingSentinel', 4),
                ('field', '488b5f', 'vm', 'exceptionHandlers'),
                '488bcb',
                ('call', 'nullCheck'),
                '4863942420040000488bcb',
                ('call', 'handlerFetch'),
                '488bd8498bce',
                ('call', 'nullCheck'),
                '49637e04488bcb',
                ('call', 'nullCheck'),
                '488bd7488bcb',
                ('call', 'handlerFetch'),
                '488bd8488bc8',
                ('call', 'nullCheck'),
                '48637c2474',
                ('field', '3b7b', 'handler', 'TryStart'),
                ('rel', '7c', 'pendingOutside', 1),
                '488bcb',
                ('call', 'nullCheck'),
                ('field', '3b7b', 'handler', 'TryEnd'),
                ('rel', '7d', 'pendingOutside', 1)),
 'pendingInTry': ('488bcfba08000000',
                  ('call', 'slotMultiply'),
                  '488bd0488b4c2478',
                  ('call', 'pointerAdd'),
                  '4c8bf0488944245044896c2474',
                  ('rel', 'e9', 'targetHome', 4)),
 'pendingOutside': ('488bcb',
                    ('call', 'nullCheck'),
                    ('field', '48634b', 'handler', 'HandlerStart'),
                    'ba08000000',
                    ('call', 'slotMultiply'),
                    '488b4c2478',
                    ('rel', 'e9', 'targetAdd', 4)),
 'pendingSentinel': ('48634c2474ba08000000',
                     ('call', 'slotMultiply'),
                     '488bd0488b4c2478',
                     ('call', 'pointerAdd'),
                     '4c8bf0488944245048898424f803000044896c2474',
                     ('rel', 'e9', 'loopRead', 4)),
 'Leave': ('498bce', ('call', 'nullCheck'), '418b460489442474', ('rel', 'e9', 'pcAdvance', 4)),
 'pendingZeroThrow': ('488bd3498bcc',
                      ('call', 'pointerDifference'),
                      '488bc848b8abaaaaaaaaaaaa2a48f7e9488bca48d1f9488bc148c1e83f4803c8ba01000000',
                      ('call', 'pointerDifference'),
                      '488bf88bd6498bcc',
                      ('call', 'subtractSlot'),
                      '488bc8',
                      ('call', 'nullCheck'),
                      '8bd6498bcc',
                      ('call', 'subtractSlot'),
                      '48635804498bcf',
                      ('call', 'nullCheck'),
                      '488bd3498bcf',
                      ('call', 'arrayFetch'),
                      '488bd8',
                      ('rip', '488d0d', 'exceptionType'),
                      ('call', 'usageResolve'),
                      '488bd0488bcb',
                      ('call', 'cast'),
                      '488bd8498bcf',
                      ('call', 'nullCheck'),
                      '33d2498bcf',
                      ('call', 'assignmentCheck'),
                      '4863d74533c0498bcf',
                      ('call', 'managedStore'),
                      '8bd6498bcc',
                      ('call', 'subtractSlot'),
                      '4889442460',
                      ('rip', '488d0d', 'executeContext'),
                      ('call', 'usageResolve'),
                      '488bd0488bcb',
                      ('call', 'throwStop')),
 'Throw': ('488bd3498bcc',
           ('call', 'pointerDifference'),
           '488bc848b8abaaaaaaaaaaaa2a48f7e9488bca48d1f9488bc148c1e83f4803c8ba01000000',
           ('call', 'pointerDifference'),
           '488bf88bd6498bcc',
           ('call', 'subtractSlot'),
           '488bc8',
           ('call', 'nullCheck'),
           '8bd6498bcc',
           ('call', 'subtractSlot'),
           '48635804498bcf',
           ('call', 'nullCheck'),
           '488bd3498bcf',
           ('call', 'arrayFetch'),
           '488bd8',
           ('rip', '488d0d', 'exceptionType'),
           ('call', 'usageResolve'),
           '488bd0488bcb',
           ('call', 'cast'),
           '488bd8498bcf',
           ('call', 'nullCheck'),
           '33d2498bcf',
           ('call', 'assignmentCheck'),
           '4533c0488bd7498bcf',
           ('call', 'managedStore'),
           '8bd6498bcc',
           ('call', 'subtractSlot'),
           '4889442460',
           ('rip', '488d0d', 'executeContext'),
           ('call', 'usageResolve'),
           '488bd0488bcb',
           ('call', 'throwStop')),
 'Rethrow': (('rip', '488d0d', 'executeContext'),
             ('call', 'usageResolve'),
             '488bd0488b8c2490000000',
             ('call', 'throwStop')),
 'exceptionHomesInit': ('498bc5488984249000000048898424c00100004c89a424b8010000',),
 'localCountHome': ('498bcc', ('call', 'nullCheck'), '418b7c2404c1ff1089bc2448010000'),
 'localBaseHome': ('48638c2418040000be0c0000008bd6',
                   ('call', 'slotMultiply'),
                   '488bd0498bce',
                   ('call', 'pointerAdd'),
                   '488bd848898424b8000000'),
 'exceptionHomeRestore': ('488b8424c00100004889842490000000',),
 'catchAcquire': ('488d8c2468010000',
                  ('call', 'exceptionStoreRead'),
                  '488bf04889842490000000488b8424b80100004889442478488bd0488b8c24f8030000',
                  ('call', 'pointerDifference'),
                  '489983e207488d1c0248c1fb03488bce',
                  ('call', 'nullCheck'),
                  '33d2488bce',
                  ('call', 'objectGetType'),
                  '4533ed4c896c24684c896c2420448bcb4c8bc08b942420040000488b8c24f0030000',
                  ('call', 'getExceptionHandler'),
                  '4c8bf04885c0',
                  ('rel', '0f85', 'handlerBegin', 4)),
 'noHandler': ('488b942410040000488b4c2460',
               ('call', 'pointerDifference'),
               '488bc848bfabaaaaaaaaaaaa2a488bc748f7e9488bda48d1fb488bc348c1e83f4803d8488b942410040000488b8c2400040000',
               ('call', 'pointerDifference'),
               '488bc8488bc748f7e9488bca48d1f9488bc148c1e83f4803c88b942428040000',
               ('call', 'int32Subtract'),
               '8bf83bc3',
               ('rel', '0f8d', 'unhandled', 4),
               '488bb42408040000'),
 'noHandlerClear': ('488bce',
                    ('call', 'nullCheck'),
                    '33d2488bce',
                    ('call', 'assignmentCheck'),
                    '4863d74533c0488bce',
                    ('call', 'managedStore'),
                    'ba010000008bcf',
                    ('call', 'int32Add'),
                    '8bf83bc3',
                    ('rel', '0f8d', 'unhandledRestore', 4),
                    ('rel', 'eb', 'noHandlerClear', 1)),
 'handlerBegin': ('48638c2448010000ba0c000000',
                  ('call', 'slotMultiply'),
                  '488bd0488b8c24b8000000',
                  ('call', 'pointerAdd'),
                  '4c8bf8488b942410040000488b4c2460',
                  ('call', 'pointerDifference'),
                  '488bc848beabaaaaaaaaaaaa2a488bc648f7e9488bda48d1fb488bcb48c1e93f4803d9488b942410040000498bcf',
                  ('call', 'pointerDifference'),
                  '488bc8488bc648f7e9488bfa48d1ff488bc748c1e83f4803f88bf74c8ba424080400003bfb',
                  ('rel', '7d', 'handlerPayload', 1)),
 'handlerClear': ('498bcc',
                  ('call', 'nullCheck'),
                  '33d2498bcc',
                  ('call', 'assignmentCheck'),
                  '4863d64533c0498bcc',
                  ('call', 'managedStore'),
                  'ba010000008bce',
                  ('call', 'int32Add'),
                  '8bf03bc3',
                  ('rel', '7c', 'handlerClear', 1)),
 'handlerPayload': ('498bcf',
                    ('call', 'nullCheck'),
                    '41c70708000000498bcf',
                    ('call', 'nullCheck'),
                    '41897f04498bcc',
                    ('call', 'nullCheck'),
                    '488b9c2490000000488bd3498bcc',
                    ('call', 'assignmentCheck'),
                    '4863d74c8bc3498bcc',
                    ('call', 'managedStore'),
                    'be0c0000008bd6498bcf',
                    ('call', 'advancePointer'),
                    '4c8be04889442458488944246048899c24c0010000498bce',
                    ('call', 'nullCheck'),
                    ('field', '49634e', 'handler', 'HandlerStart'),
                    '8d56fc',
                    ('call', 'slotMultiply'),
                    '488bd0488b4c2478',
                    ('call', 'pointerAdd'),
                    '4c8bf0488944245048898424f8030000488d8c2468010000',
                    ('call', 'exceptionStorePop')),
 'unhandledRestore': ('488bb42490000000',),
 'unhandled': ('488b9c24300400004885db',
               ('rel', '74', 'unhandledPop', 1),
               '48638c2428040000ba0c000000',
               ('call', 'slotMultiply'),
               '488bd0488b8c2400040000',
               ('call', 'pointerDifference'),
               '488903488d8c2468010000',
               ('call', 'exceptionStorePop'),
               ('rip', '488d0d', 'executeContext'),
               ('call', 'usageResolve'),
               '488bd0488bce',
               ('call', 'throwStop'),
               'cc'),
 'targetAdd': ('488bd0', ('call', 'pointerAdd'), '4c8bf04889442450'),
 'targetHome': ('48898424f8030000', ('rel', 'e9', 'loopRestore', 4)),
 'loopRestore': ('488bbc24f0030000488b9c2410040000498bce', ('call', 'nullCheck'), '418b0e894c2470'),
 'loopRead': ('498bce', ('call', 'nullCheck'), '418b0e894c2470')}

_BLOCKS.update({
 'assignablePrefix': ('48895c2408488954241055565741544155415641574883ec50498bf84c8bfa0fb7d9488b0a',
    ('call','classPrepare'),'488d431448c1e0044903074c8b084c8b7008'),
 'getExceptionHandler': ('488bc44889580848896810488970184889782041564883ec20',
    ('field','488b71','vm','exceptionHandlers'),'418be94d8bf04885f60f84840000003b561873794863c2488b74c62033ff4885f674703b7e187d6173634863c7488b5cc6204885db745c',
    ('field','837b','handler','HandlerType'),'027420',('field','837b','handler','HandlerType'),'007524',
    ('field','488b53','handler','CatchType'),'4885d27447b91e0000004d8bc6',('call','assignableRequest'),'84c0740a',
    ('field','3b6b','handler','TryStart'),'7c05',('field','3b6b','handler','TryEnd'),
    '7c04ffc7ebb8488bc3488b5c2430488b6c2438488b742440488b7c24484883c420415ec333c0ebe1',
    ('call','boundsFailure'),'cc',('call','nullFailure'),'cc')})
