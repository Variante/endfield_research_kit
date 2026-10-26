"""Authenticate conditional IFix call requests and return cleanup.

Call uses the operand's unsigned low word for unmanagedCodes and signed high
word for argument count. Callvirt first requests an Object-tag receiver at
top minus that count and checks its managed reference for null. Callvirtvirt
casts that receiver to AnonymousStorey, selects its info by typeId and reads
the low-word VTable entry as a signed method ID. The shared internal route
requests recursive Execute with argumentBase=top-count slots, the original
managed/base arrays, refCount zero and topWriteBack null. Its returned pointer
becomes top on normal return. Recursive execution and runtime table contents
are unobserved.

Calli consumes the preceding Object descriptor, casts managed[Value1] to
MethodBase, then clears the managed slot at the descriptor's own physical
base-relative index before the MethodBase-null check. Its operand is unused.
The VM's MethodBase-to-CalliInvokerInfo cache selects an existing info on a
successful TryGetValue. A miss requests ReflectionMethodInvoker, wraps its
named Invoke MethodDef in ExternInvoker and stores it in the new info. Its
ArgumentCount is GetParameters().Length plus one for an instance method,
computed with native Int32 addition, then cached. The GetParameters virtual
slot and stored generic contexts are authenticated; their runtime results
and exact generic sharing are unobserved.

Calli rewinds before constructing Call and writes ThreadStackInfo's unmanaged
Top to that rewound pointer before requesting ExternInvoker.Invoke(false).
The common external caller instead publishes its incoming top, rewinds by
the signed high-word count and passes isInstantiate=(opcode==Newobj). Its
selection from the parent's CallExtern/Newobj dispatcher remains inherited.
Both explicitly store four Call fields, request an opaque zero-fill helper
before those stores and copy all five words to the final Call. The fifth
word's value after that helper is unobserved. The shared delegate entry is
authenticated as an anonymous indirect trampoline, without assigning names
to its runtime delegate words or claiming which function it invokes.

Ret optionally writes argumentBase-refCount slots through topWriteBack. A
nonzero operand copies the preceding raw twelve-byte descriptor into
argumentBase, saving Value2 before the eight-byte copy. For Object/ValueType
only, it copies the managed reference to the argument-base index if needed
and always rewrites Value1 to that low Int32 index. The result route clears
managed[int32(i+argumentIndex+1)] while signext(i)<(top-base)/slotBytes-1;
the void route clears managed[int32(i+argumentIndex)] with the bound without
minus one. Each counter increment is native wrapping Int32 addition. They
return argumentBase plus one slot or argumentBase respectively. These are
loop recipes, not a guarantee of termination or a safe mathematical range.

Finite programs cover every instruction and branch join in these routes,
ABI homes, initial scratch values and Call copies. They require consistent
loop entry state (including zero scratch and slot width), valid stable
storage and normal nonmutating helper returns. Target bounds/values, aliases,
casts, allocation, cache state, reflection results, exception/unwind choice
and actual execution remain unobserved. Error requests do not prove that the
runtime exception helper throws; their normal-return continuation is retained.
Native addresses and hashes belong to the reviewed contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_name, runtime_type_field_offsets
from scripts.game_data.il2cpp.context import literal_record, unresolved_usage_index, usage_method_spec
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_update_rules import _ref, _rva, _hash, _expect, _type_pointer
from scripts.game_data.ifix_vm_new_field_rules import _guard_type, _dictionary_signature, _canonical_target
from scripts.game_data.ifix_vm_negative_field_rules import _EXECUTE_TYPES
from scripts.game_data.ifix_vm_dispatch_rules import resolve_selected_dispatch_entry


class CallOpcodeRuleError(ValueError):
    """A call/return rule lacks its selected native witness."""


_HELPER_REFS = {
 'subtractSlot':'constrainedTypeOperand.stackEffect.priorPointerHelper','nullCheck':'negativeFieldRules.helpers.nullCheck',
 'slotMultiply':'arithmeticWindows.signedSlotMultiply','pointerAdd':'arithmeticWindows.pointerAdd',
 'pointerDifference':'arithmeticWindows.stackPointerSubtract','int32Add':'negativeFieldRules.helpers.int32Add',
 'advancePointer':'basicOpcodeRules.helpers.advancePointer','arrayFetch':'initobjTypeOperand.consumerRowFetchHelper',
 'assignmentCheck':'functionPointerRules.helpers.assignmentCheck','managedStore':'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
 'cast':'referenceUpdateRules.helpers.cast','allocateObject':'dispatchRules.helpers.allocateObject',
 'boxOperand':'dispatchRules.helpers.boxOperand','classInitialize':'objectConversionRules.helpers.classInitialize',
 'writeBarrier':'referenceAddressRules.helpers.referenceBarrier','arrayStore':'anonymousStoreyRules.helpers.infoArrayStore',
 'anonymousInfoFetch':'functionPointerRules.helpers.anonymousInfoFetch','int32ArrayFetch':'functionPointerRules.helpers.int32ArrayFetch',
 'parameterQuery':'genericDelegateFactoryRules.helpers.parameterQueryHelper','cacheLookup':'genericDelegateFactoryRules.helpers.cacheLookupHelper',
 'cacheStore':'genericDelegateFactoryRules.helpers.cacheStoreHelper','typeCarrier':'instanceFieldRules.helpers.typeCarrier',
}
_METHOD_REFS = {'enumToString':'dispatchRules.methods.enumToString',
 'runtimeException':'delegateConstruction.methodCalls.nullFallbackException','reflectionCtor':'reflectionDispatch.methods.reflectionConstructor',
 'externDelegateCtor':'reflectionDispatch.methods.delegateConstructor','isStatic':'reflectionDispatch.methods.isStatic','execute':'consumer',
 'invalidProgramCtor':'stackReferenceRules.nullConstructor','externInvoke':'reflectionDispatch.methods.delegateInvoke'}
_METHODS = {
 'methodBaseEqual':('System.Reflection.MethodBase','op_Equality',['System.Reflection.MethodBase','System.Reflection.MethodBase'],'bool',True),
 'concatObjects':('System.String','Concat',['object','object'],'string',True),
 'concatStrings':('System.String','Concat',['string','string'],'string',True),
 'stackGet':('IFix.Core.ThreadStackInfo','get_Stack',[],'IFix.Core.ThreadStackInfo',True),
 'invalidProgramCtor':('System.InvalidProgramException','.ctor',['string'],'void',False),
 'infoCtor':('IFix.Core.VirtualMachine+CalliInvokerInfo','.ctor',[],'void',False),
 'externInvoke':('IFix.Core.ExternInvoker','Invoke',['IFix.Core.VirtualMachine','IFix.Core.Call','bool'],'void',False),
 'enumToString':('System.Enum','ToString',[],'string',False),
 'runtimeException':('IFix.Core.VirtualMachine','throwRuntimeException',['System.Exception','bool'],'void',False),
 'reflectionCtor':('IFix.Core.ReflectionMethodInvoker','.ctor',['System.Reflection.MethodBase'],'void',False),
 'externDelegateCtor':('IFix.Core.ExternInvoker','.ctor',['object','nint'],'void',False),
 'isStatic':('System.Reflection.MethodBase','get_IsStatic',[],'bool',False),
 'execute':('IFix.Core.VirtualMachine','Execute',_EXECUTE_TYPES,'IFix.Core.Value*',False),
 'reflectionInvoke':('IFix.Core.ReflectionMethodInvoker','Invoke',['IFix.Core.VirtualMachine','IFix.Core.Call','bool'],'void',False),
 'getParameters':('System.Reflection.MethodBase','GetParameters',[],'System.Reflection.ParameterInfo[]',False),
}
_FIELD_TYPES = {
 'IFix.Core.VirtualMachine':(False,{'unmanagedCodes':('IFix.Core.Instruction**',24),
     'externInvokers':('IFix.Core.ExternInvoker[]',48),'calliInvokerCache':('System.Collections.Generic.Dictionary`2<System.Reflection.MethodBase,IFix.Core.VirtualMachine+CalliInvokerInfo>',56),
     'anonymousStoreyInfos':('IFix.Core.AnonymousStoreyInfo[]',104)}),
 'IFix.Core.VirtualMachine+CalliInvokerInfo':(False,{'Invoker':('IFix.Core.ExternInvoker',16),'ArgumentCount':('int',24)}),
 'IFix.Core.AnonymousStorey':(False,{'typeId':('int',32)}),
 'IFix.Core.AnonymousStoreyInfo':(False,{'VTable':('int[]',48)}),
 'IFix.Core.ThreadStackInfo':(False,{'UnmanagedStack':('IFix.Core.UnmanagedStack*',16)}),
 'IFix.Core.UnmanagedStack':(True,{'Top':('IFix.Core.Value*',24)}),
 'IFix.Core.Call':(True,{'argumentBase':('IFix.Core.Value*',16),'evaluationStackBase':('IFix.Core.Value*',24),
     'managedStack':('object[]',32),'currentTop':('IFix.Core.Value*',40),'topWriteBack':('IFix.Core.Value**',48)}),
 'IFix.Core.Value':(True,{'Type':('IFix.Core.ValueType',16),'Value1':('int',20),'Value2':('int',24)}),
}
_TYPE_CELLS = {'methodBaseType':'System.Reflection.MethodBase','anonymousType':'IFix.Core.AnonymousStorey',
 'valueTypeType':'IFix.Core.ValueType','threadType':'IFix.Core.ThreadStackInfo','reflectionType':'IFix.Core.ReflectionMethodInvoker',
 'invalidProgramType':'System.InvalidProgramException','externInvokerType':'IFix.Core.ExternInvoker',
 'calliInfoType':'IFix.Core.VirtualMachine+CalliInvokerInfo'}
_LITERALS = {'underflowPrefix':'Calli stack underflow for ','callvirtvirtSuffix':' for Callvirtvirt',
 'nullMethodLiteral':'Calli target is null or not MethodBase','badTagLiteral':'Calli expect MethodBase pointer but got ',
 'callvirtSuffix':' for Callvirt'}
_OPCODES = ('Call','Callvirt','Callvirtvirt','Calli','Ret')
_CLAIMS = {'schema':'endfield.ifix-vm-call-opcode-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'slotBytes':12,'callValueBytes':40,'callObjectHeaderBytes':16,
 'helperRefs':_HELPER_REFS,'methodRefs':_METHOD_REFS,
 'getParametersRef':'genericDelegateFactoryRules.virtualMethods.getParameters',
 'reflectionInvokeRef':'reflectionDispatch.methods.reflectionInvoke',
 'loopStateRef':'basicOpcodeRules.sharedWindows.loopState','pcAdvanceRef':'basicOpcodeRules.sharedWindows.pcAdvance',
 'externalSelectorRef':'reflectionDispatch','valueLayoutRef':'constrainedTypeOperand.stackEffect.valueLayout',
 'internalRecipe':'low-word-method-index;signed-high-word-count;recursive-Execute(refCount=0,topWriteBack=null);commit-returned-top',
 'virtualRecipe':'Object-receiver-at-top-minus-count;nonnull-managed-owner;Callvirt:low-word-ID;Callvirtvirt:AnonymousStorey-typeId-info-VTable[low-word]-signed-ID',
 'calliRecipe':'preceding-Object-to-MethodBase;physical-managed-clear;cache-TryGetValue;miss-build-and-cache-Invoker-and-ArgumentCount;rewind;Call;publish-ThreadStack.Top;Invoke(false);commit-currentTop',
 'calliOperandBoundary':'authored-operand-unused',
 'calliCountRecipe':'native-Int32(GetParameters.Length+(IsStatic?0:1));cached-ArgumentCount-used-as-signed-count',
 'externalRecipe':'inherited-selected-invoker;publish-incoming-top;rewind-by-signed-high-word-count;Call;Invoke(opcode==Newobj);commit-currentTop',
 'returnRecipe':'optional-topWriteBack=argumentBase-refCount-slots;nonzero-operand:raw-copy-and-Object-or-ValueType-managed-rebase;cleanup;return-argumentBase-plus-result-slot',
 'cleanupRecipe':'i32=0;while-signext(i32)<signed-slot-distance(top,base)-resultCount:clear-managed[int32(i32+argumentIndex+resultCount)];i32=int32(i32+1)',
 'storageBoundary':'consistent-loop-entry-zero-scratch-and-slot-width;valid-stable-storage-and-normal-nonmutating-helper-return',
 'aliasBoundary':'actual-overlap-target-values-helper-mutation-and-return-cleanup-aliases-unobserved',
 'calleeBoundary':'inherited-callee-outcomes-reflection-casts-cache-allocation-sharing-and-indirect-delegate-target-unobserved',
 'callZeroBoundary':'zero-fill-request-only;four-explicit-field-stores;fifth-word-after-helper-unobserved',
 'exceptionBoundary':'error-request-and-normal-return-continuations-authenticated;throw-unwind-and-external-null-exits-unresolved',
 'loopTerminationBoundary':'wrapping-Int32-counter-and-signed-bound-recipe;termination-and-range-validity-unobserved',
 'tagMembers':{'Object':8,'ValueType':9},'newobjOpcodeId':24,
}


def _need(ok: bool, detail: str) -> None:
    if not ok: raise CallOpcodeRuleError('callOpcode.'+detail)


def _carrier(image: Any, pointer: int, expected: str, *, byref: bool=False, seen: frozenset[int]=frozenset()) -> None:
    _need(len(seen)<8 and pointer not in seen,'carrier: recursive/deep type')
    raw=image.pe.bytes_at_va(pointer,16)
    _need(len(raw)==16 and bool(raw[11]&0x20)==byref,'carrier: malformed/by-reference flag differs')
    nested=expected.endswith('[]') or expected.endswith('*')
    kind=(0x1d if expected.endswith('[]')else 0x0f) if nested else {
        'bool':2,'int':8,'string':0x0e,'object':0x1c,'void':1,'nint':0x18,
        'IFix.Core.Value':0x11,'IFix.Core.Instruction':0x11,'IFix.Core.Call':0x11,
        'IFix.Core.ValueType':0x11,'IFix.Core.UnmanagedStack':0x11,
    }.get(expected,0x15 if '`' in expected and '<' in expected else 0x12)
    _need(raw[10]==kind,'carrier: primitive/class/pointer/array/generic kind differs')
    if nested:_carrier(image,int.from_bytes(raw[:8],'little'),expected[:-2] if expected.endswith('[]')else expected[:-1],seen=seen|{pointer})
    elif kind==0x15:_guard_type(image,pointer)
    _need(runtime_type_name(image.pe,image.metadata,pointer)==expected,'carrier: named type differs')


def _method(image: Any, row: dict, name: str, extents: dict[int,int], *, virtual_slot: int|None=None) -> int:
    owner,method_name,params,returned,static=_METHODS[name];md=image.metadata
    _need(row.get('type')==owner and row.get('method')==method_name,'method: declared identity differs: '+name)
    _need('parameterCount'not in row or row['parameterCount']==len(params),'method: declared parameter count differs: '+name)
    _need('parameterTypes' not in row or row['parameterTypes']==params,'method: declared parameters differ: '+name)
    _need('returnType' not in row or row['returnType']==returned,'method: declared return differs: '+name)
    selected=[]
    for t in md.types:
        if md.type_full_name(t)!=owner:continue
        for m in md.methods_for(t):
            if md.string(m.name_index)!=method_name or m.parameter_count!=len(params):continue
            if [runtime_type_name(image.pe,md,_type_pointer(image,p.type_index))for p in md.parameters_for(m)]==params:selected.append(m)
    _need(len(selected)==1,'method: one named overload required: '+name);m=selected[0]
    for k,(p,typ) in enumerate(zip(md.parameters_for(m),params)):
        _carrier(image,_type_pointer(image,p.type_index),typ,byref=name in ('externInvoke','reflectionInvoke') and k==1)
    _carrier(image,_type_pointer(image,m.return_type),returned)
    _need(bool(m.flags&0x10)==static and m.generic_container_index==-1,'method: static/generic differs: '+name)
    if virtual_slot is not None:
        _need(m.slot==virtual_slot and m.flags&0x40 and row.get('slot')==virtual_slot,'method: virtual slot differs: '+name)
        _need('token'not in row or m.token==_rva(row['token']),'method: virtual token differs: '+name)
        return virtual_slot
    _need(m.token==_rva(row['token']),'method: token differs: '+name)
    at=image.method_pointer_va(m)-image.pe.image_base;_need(at==_rva(row['rva']),'method: pointer differs: '+name)
    if 'bodyBytes'in row:
        size=row['bodyBytes'];_need(type(size)is int and 0<size<=65536 and extents.get(image.pe.image_base+at)==image.pe.image_base+at+size,'method: body extent differs: '+name)
        _hash(image.pe.bytes_at_va(image.pe.image_base+at,size),{'byteCount':size,'sha256':row['bodySha256']},name)
    elif 'byteCount'in row:
        _need(row.get('bodyBoundary')=='entry-window-callee-outcome-unresolved','method: entry boundary differs: '+name)
        _hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name)
    else:_need(name=='externInvoke' and row.get('bodyExtent')=='sharedDelegateTrampoline','method: body witness missing: '+name)
    return at


def _layouts(image: Any, spec: dict, contract: dict) -> None:
    _need(set(spec['fieldLayouts'])==set(_FIELD_TYPES),'layout owner set differs')
    md=image.metadata
    for owner,(value,fields)in _FIELD_TYPES.items():
        types=[t for t in md.types if md.type_full_name(t)==owner];row=spec['fieldLayouts'][owner]
        _need(len(types)==1 and bool(types[0].bitfield&1)==value and row=={'type':owner,'isValueType':value,
            'fields':{n:{'type':typ,'offset':off}for n,(typ,off)in fields.items()}},'layout owner/declaration differs: '+owner)
        definitions={md.string(f.name_index):f for f in md.fields_for(types[0])};offsets=runtime_type_field_offsets(md,image.pe,image.registration,types[0].index)
        for n,(typ,off)in fields.items():
            _need(n in definitions and offsets.get(n)==off,'layout field/offset differs: '+owner+'.'+n)
            pointer=_type_pointer(image,definitions[n].type_index);_carrier(image,pointer,typ)
            _need(not int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&0x10,'layout: expected instance field')
    value=_ref(contract,spec['valueLayoutRef'])
    _need(value.get('fieldOffsets')=={'Type':16,'Value1':20,'Value2':24},'Value descriptor offsets differ')


def _context(image: Any, row: dict, target: int) -> None:
    identity='TryGetValue' if row['name']=='cacheTryGet'else 'set_Item';args=['System.Reflection.MethodBase','IFix.Core.VirtualMachine+CalliInvokerInfo']
    _need(row.get('usageTag')==6 and row.get('identity')==identity and row.get('classArguments')==args,'context declaration differs')
    md,reg=image.metadata,image.registration;at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8);start=_rva(reg['methodSpecs'])
    rec=usage_method_spec(raw,image.pe.bytes_at_va(start,reg['methodSpecsCount']*12),len(md.methods),reg['genericInstsCount'],source='callOpcode.context',usage_offset=image.pe.image_base+at,records_offset=start)
    _need(rec['classInstantiationIndex']>=0 and rec['methodInstantiationIndex']==-1,'context: expected class-only instantiation')
    method=md.methods[rec['definition']]
    _need(md.type_full_name(md.types[method.declaring_type])=='System.Collections.Generic.Dictionary`2' and md.string(method.name_index)==identity,'context named definition differs')
    _dictionary_signature(image,method,identity)
    _carrier(image,_type_pointer(image,method.return_type),'bool' if identity=='TryGetValue'else 'void')
    arguments=image.instantiations.resolve(rec['classInstantiationIndex']).arguments
    for arg in arguments:
        _need(bytes.fromhex(arg.raw_type_record_hex)==image.pe.bytes_at_va(arg.type_pointer_va,16),'context: argument snapshot differs')
        _guard_type(image,arg.type_pointer_va)
    _need([runtime_type_name(image.pe,md,a.type_pointer_va)for a in arguments]==args,'context: constructed arguments differ')
    _canonical_target(image,method.index,target)


def _cells(image: Any, spec: dict, targets: dict[str,int], contract: dict, extents: dict[int,int]) -> dict[str,int]:
    rows={r['name']:r for r in spec['usageCells']};expected=set(_TYPE_CELLS)|set(_LITERALS)|{'cacheTryGet','cacheSet','reflectionMethod'}
    _need(len(rows)==len(spec['usageCells']) and set(rows)==expected,'usage declaration set differs');cells={}
    for name,row in rows.items():
        at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8)
        _need(raw==bytes.fromhex(row['rawHex']),'usage bytes differ: '+name);cells[name]=at
        if name in _TYPE_CELLS:
            _need(row.get('usageTag')==1 and row.get('identity')==_TYPE_CELLS[name],'type usage declaration differs')
            index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='callOpcode.type',offset=at)
            _carrier(image,_type_pointer(image,index),_TYPE_CELLS[name])
        elif name in _LITERALS:
            _need(row.get('usageTag')==5 and row.get('identity')==_LITERALS[name],'literal declaration differs')
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData']
            idx=unresolved_usage_index(raw,table.size//8,tag=5,source='callOpcode.literal',offset=at);off=table.offset+idx*8
            begin,size=literal_record(md.buf[off:off+8],pool.size,source='callOpcode.literal',offset=off)
            _need(md.buf[pool.offset+begin:pool.offset+begin+size]==_LITERALS[name].encode(),'literal bytes differ')
        elif name in ('cacheTryGet','cacheSet'):_context(image,row,targets['cacheLookup' if name=='cacheTryGet'else 'cacheStore'])
        else:
            _need(row.get('usageTag')==3 and row.get('identity')=='ReflectionMethodInvoker.Invoke','reflection MethodDef declaration differs')
            index=unresolved_usage_index(raw,len(image.metadata.methods),tag=3,source='callOpcode.reflection',offset=at)
            method=image.metadata.methods[index];inherited=_ref(contract,spec['reflectionInvokeRef'])
            _need(method.token==_rva(inherited['token']) and image.metadata.type_full_name(image.metadata.types[method.declaring_type])==_METHODS['reflectionInvoke'][0]
                and image.metadata.string(method.name_index)=='Invoke','reflection MethodDef identity differs')
            _method(image,inherited,'reflectionInvoke',extents)
    return cells


def _program(base: int, tokens: Any, targets: dict[str,int], cells: dict[str,int]) -> bytes:
    p=_Program(base)
    for token in tokens:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]],bytes.fromhex(args[2]))
        elif kind=='edge':
            prefix=bytes.fromhex(args[0]);width=1 if len(prefix)==1 and prefix!=b'\xe9'else 4
            delta=targets[args[1]]-(base+len(p.raw)+len(prefix)+width)
            _need(-(1<<(8*width-1))<=delta<(1<<(8*width-1)),'edge displacement outside width')
            p.add(prefix+delta.to_bytes(width,'little',signed=True))
        else:_need(False,'unknown finite token')
    return p.finish()


def validate_call_opcode_rules(image: Any, spec: dict, body: bytes, body_rva: int, opcode_ids: dict[str,int], contract: dict, extents: dict[int,int]) -> dict:
    """Parent supplies authenticated Execute/dispatcher and prerequisite groups."""
    _need(all(spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/boundary')
    _need(set(spec['methods'])==set(_METHODS)-set(_METHOD_REFS)-{'reflectionInvoke','getParameters'},'method declaration set differs')
    _need(set(spec['helpers'])=={'cacheLookupWrapper','cacheStoreWrapper','zeroMemory','externInvokeEntry'},'helper declaration set differs')
    blocks={r['name']:r for r in spec['blocks']};_need(len(blocks)==len(spec['blocks']) and set(blocks)==set(_PROGRAMS),'block declaration set differs')
    _need(set(spec['entries'])==set(_OPCODES),'opcode entry set differs')
    _need(set(spec['opcodeIds'])==set(_OPCODES) and all(spec['opcodeIds'][n]==opcode_ids[n]for n in _OPCODES)
        and opcode_ids['Newobj']==spec['newobjOpcodeId'],'selected opcode IDs differ')
    _need(set(spec['targets'])=={'restoreZero','pcAdvance','commonInternal','nullCallvirtExit','nullCallvirtvirtExit','calliTail','externalCommit'},'target declaration set differs')
    tags={r['name']:r['id']for r in enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.ValueType')}
    _need(all(tags.get(k)==v for k,v in _CLAIMS['tagMembers'].items()),'selected ValueType tags differ')
    _layouts(image,spec,contract);targets={}
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name);targets[name]=at
    for name,path in _METHOD_REFS.items():targets[name]=_method(image,_ref(contract,path),name,extents)
    for name,row in spec['methods'].items():
        _need(row.get('parameterCount')==len(_METHODS[name][2]),'method: declared parameter count differs: '+name)
        targets[name]=_method(image,row,name,extents)
    _method(image,_ref(contract,spec['getParametersRef']),'getParameters',extents,virtual_slot=18)
    for name,row in spec['helpers'].items():
        _need(row.get('effectBoundary')=='opaque-callee-request-only','helper result promoted')
        at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name);targets[name]=at
    cells=_cells(image,spec,targets,contract,extents)
    _need(targets['externInvokeEntry']==targets['externInvoke'],'shared delegate entry method join differs')
    # Context wrappers select the same named canonical-family helpers. Runtime
    # selection of the stored exact sharing remains unobserved.
    for name,cell,callee in [('cacheLookupWrapper','cacheTryGet','cacheLookup'),('cacheStoreWrapper','cacheSet','cacheStore')]:
        p=_Program(targets[name]);p.rip('4c8b0d',cells[cell]);p.rip('e9',targets[callee])
        _expect(image.pe.bytes_at_va(image.pe.image_base+targets[name],spec['helpers'][name]['byteCount']),p.finish(),name+'.context-forward')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['infoCtor'],3),bytes.fromhex('c20000'),'CalliInvokerInfo.empty-constructor-entry')
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['externInvoke'],20),bytes.fromhex('488b41284c8bd1488b4940488944242849ff6218'),'ExternInvoker.anonymous-indirect-entry')
    p=_Program(targets['zeroMemory']);p.add('4c8bc233d2');p.rip('e9',_rva(spec['zeroMemoryTarget']))
    _expect(image.pe.bytes_at_va(image.pe.image_base+targets['zeroMemory'],spec['helpers']['zeroMemory']['byteCount']),p.finish(),'Call.opaque-zero-fill-forward')
    targets.update({n:_rva(at)for n,at in spec['targets'].items()})
    _need(targets['commonInternal']==_rva(blocks['commonInternal']['rva']) and targets['calliTail']==_rva(blocks['calliTail']['rva'])
        and targets['externalCommit']==_rva(blocks['Calli']['rva'])+blocks['Calli']['byteCount']-10
        and targets['restoreZero']==_rva(blocks['slotWidthRestore']['rva']) and targets['restoreZero']+5==targets['pcAdvance'],'tail joins differ')
    for name,path in [('loopState',spec['loopStateRef']),('pcAdvance',spec['pcAdvanceRef'])]:
        row=_ref(contract,path);at=_rva(row['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);_hash(raw,row,name)
        if name=='pcAdvance':_need(at==targets['pcAdvance'],'PC tail differs')
        else:
            p=_Program(at);p.add('488b9c2410040000498bce');p.call(targets['nullCheck']);p.add('418b0e894c2470')
            _expect(raw,p.finish(),'loop.entry-base-and-opcode')
    for name,row in blocks.items():
        at=_rva(row['rva']);size=row['byteCount'];off=at-body_rva
        _need(type(size)is int and 0<size<=8192 and 0<=off<=len(body)-size,'Execute block range differs: '+name)
        raw=body[off:off+size];_hash(raw,row,name);_expect(raw,_program(at,_PROGRAMS[name],targets,cells),name+'.full-finite-program')
    dispatcher=contract['dispatchRules'];basic=contract['basicOpcodeRules']
    for name in _OPCODES:
        at=_rva(spec['entries'][name]);_need(at==_rva(blocks[name]['rva']),'opcode block entry differs')
        actual=resolve_selected_dispatch_entry(body,body_rva,_rva(basic['dispatchStartRva']),opcode_ids[name],
            zero_compare_rva=_rva(dispatcher['extensions']['zeroCompare']['rva']),sub_esi_rva=_rva(dispatcher['extensions']['subEsi']['rva']),
            entry_rvas={_rva(r['entryRva'])for r in dispatcher['entryPoints']})
        _need(actual==at,'selected opcode route differs: '+name)
    return {'status':'validated_conditional_call_and_return_recipes','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        **{k:spec[k]for k in ('internalRecipe','virtualRecipe','calliRecipe','calliOperandBoundary','calliCountRecipe','externalRecipe',
            'returnRecipe','cleanupRecipe','storageBoundary','aliasBoundary','calleeBoundary','callZeroBoundary','exceptionBoundary','loopTerminationBoundary')},
        'unresolved':['runtime-method-table-indices-and-contents','runtime-receiver-cast-and-cache-results','GetParameters-array-length-and-IsStatic-result',
            'runtime-generic-sharing-and-indirect-delegate-target','opaque-zero-fill-fifth-Call-word','recursive-Execute-and-ExternInvoker-outcomes',
            'actual-storage-overlap-and-helper-mutation','cleanup-counter-termination-and-target-bounds','throw-unwind-and-external-null-exits','actual-execution']}


def validate_selected_call_opcode_rules(contract: dict, *, gameassembly: Path, metadata: Path, spec: dict|None=None) -> dict:
    """Require the explicit selected native pair; never use a global game root."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths are required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'nativeInputs: selected hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.calls');extents=image.mapper.pdata_function_extents(image.pe)
    consumer=contract['consumer'];at=_method(image,consumer,'execute',extents);body=image.pe.bytes_at_va(image.pe.image_base+at,consumer['bodyBytes'])
    enums=enum_members(image.metadata,field_defaults(image.metadata),'IFix.Core.Code');ids={r['name']:r['id']for r in enums}
    return validate_call_opcode_rules(image,contract['callOpcodeRules']if spec is None else spec,body,at,ids,contract,extents)


def project_call_opcode_rules(decoded: dict, spec: dict) -> list[dict]:
    """Project authored call/Ret operands after selected native validation."""
    _need(all(spec.get(k)==v for k,v in _CLAIMS.items()) and set(spec['opcodeIds'])==set(_OPCODES),'unsupported projection schema/reference/boundary')
    result=[]
    for method in decoded['methods']:
        for instruction in method['instructions']:
            name=instruction['name']
            if name not in _OPCODES:continue
            operand=instruction['operandUnsigned']
            _need(type(operand)is int and 0<=operand<=0xffffffff and instruction['opcode']==spec['opcodeIds'][name],name+': malformed operand/opcode')
            signed=operand if operand<0x80000000 else operand-0x100000000
            _need('operandSigned'not in instruction or type(instruction['operandSigned'])is int and instruction['operandSigned']==signed,name+': inconsistent signed operand')
            out={'vmMethodIndex':method['index'],'instructionIndex':instruction['index'],'offset':instruction['offset'],'opcode':name,
                'operandUnsigned':operand,'operandSigned':signed,'evidenceBoundary':'conditional','executionBoundary':'unobserved',
                **{k:spec[k]for k in ('storageBoundary','aliasBoundary','calleeBoundary','exceptionBoundary','loopTerminationBoundary')}}
            if name=='Ret':out.update(hasResult=operand!=0,effect=spec['returnRecipe'],cleanup=spec['cleanupRecipe'],normalReturnSlotDelta=1 if operand else 0)
            elif name=='Calli':out.update(operandConsumedByThisOpcode=False,effect=spec['calliRecipe'],argumentCount=spec['calliCountRecipe'],callZeroBoundary=spec['callZeroBoundary'])
            else:
                count=operand>>16;count=count if count<0x8000 else count-0x10000
                out.update(argumentCount=count,selector=operand&0xffff,selectorMeaning='VTable-slot'if name=='Callvirtvirt'else 'unmanagedCodes-index',
                    effect=spec['internalRecipe'],receiverCheck=spec['virtualRecipe']if name!='Call'else 'none-in-selected-route',
                    normalReturnTop='recursive-Execute-returned-pointer')
            result.append(out)
    return result


_PROGRAMS = {'Call': ['498bce',
          ('call', 'nullCheck'),
          '418b5e04c1fb10498bce',
          ('call', 'nullCheck'),
          '410fb77604488b7f188bceba08000000',
          ('call', 'slotMultiply'),
          '488bd0488bcf',
          ('call', 'pointerAdd'),
          '488b384863cbba0c000000',
          ('call', 'slotMultiply'),
          '488bd0498bcc',
          ('call', 'pointerDifference'),
          '4c896c24484c896c244044896c243889742430895c2428488b8c241004000048894c24204d8bcf4c8bc0488bd7488b8c24f0030000',
          ('call', 'execute'),
          '4c8be048894424584889442460',
          ('edge', 'e9', 'restoreZero')],
 'Callvirt': ['498bce',
              ('call', 'nullCheck'),
              '458b760441c1fe104963ce8bd6',
              ('call', 'slotMultiply'),
              '488bd0498bcc',
              ('call', 'pointerDifference'),
              '488bd8488bc8',
              ('call', 'nullCheck'),
              '833b080f8483000000488bcb',
              ('call', 'nullCheck'),
              '4c8bc3',
              ('rip', '488b15', 'valueTypeType', ''),
              '488d8c24a8020000',
              ('call', 'typeCarrier'),
              '33d2488d8c24a8020000',
              ('call', 'enumToString'),
              '4533c0',
              ('rip', '488b15', 'callvirtSuffix', ''),
              '488bc8',
              ('call', 'concatStrings'),
              '488bf0',
              ('rip', '488b0d', 'invalidProgramType', ''),
              ('call', 'allocateObject'),
              '488bf8488bc8',
              ('call', 'nullCheck'),
              '4533c0488bd6488bcf',
              ('call', 'invalidProgramCtor'),
              '4533c941b001488bd7488b8c24f0030000',
              ('call', 'runtimeException'),
              'be0c000000488bcb',
              ('call', 'nullCheck'),
              '48635b04498bcf',
              ('call', 'nullCheck'),
              '488bd3498bcf',
              ('call', 'arrayFetch'),
              '493bc5',
              ('edge', '0f84', 'nullCallvirtExit'),
              '488b5c2450488bcb',
              ('call', 'nullCheck'),
              '0fb77b04488b8424f0030000488b5818488bcfba08000000',
              ('call', 'slotMultiply'),
              '488bd0488bcb',
              ('call', 'pointerAdd'),
              '488b184963ce8bd6',
              ('call', 'slotMultiply'),
              '488bd0498bcc',
              ('call', 'pointerDifference'),
              '4c896c24484c896c244044896c2438897c24304489742428488b8c241004000048894c24204d8bcf4c8bc0488bd3488b8c24f0030000',
              ('call', 'execute'),
              '4c8be048894424584889442460',
              ('edge', 'e9', 'pcAdvance')],
 'Callvirtvirt': ['498bce',
                  ('call', 'nullCheck'),
                  '458b760441c1fe104963ce8bd6',
                  ('call', 'slotMultiply'),
                  '488bd0498bcc',
                  ('call', 'pointerDifference'),
                  '488bd8488bc8',
                  ('call', 'nullCheck'),
                  '833b080f8483000000488bcb',
                  ('call', 'nullCheck'),
                  '4c8bc3',
                  ('rip', '488b15', 'valueTypeType', ''),
                  '488d8c24c0020000',
                  ('call', 'typeCarrier'),
                  '33d2488d8c24c0020000',
                  ('call', 'enumToString'),
                  '4533c0',
                  ('rip', '488b15', 'callvirtvirtSuffix', ''),
                  '488bc8',
                  ('call', 'concatStrings'),
                  '488bf0',
                  ('rip', '488b0d', 'invalidProgramType', ''),
                  ('call', 'allocateObject'),
                  '488bf8488bc8',
                  ('call', 'nullCheck'),
                  '4533c0488bd6488bcf',
                  ('call', 'invalidProgramCtor'),
                  '4533c941b001488bd7488b8c24f0030000',
                  ('call', 'runtimeException'),
                  'be0c000000488bcb',
                  ('call', 'nullCheck'),
                  '48637b04498bcf',
                  ('call', 'nullCheck'),
                  '488bd7498bcf',
                  ('call', 'arrayFetch'),
                  '493bc5',
                  ('edge', '0f84', 'nullCallvirtvirtExit'),
                  '488bcb',
                  ('call', 'nullCheck'),
                  '48635b04498bcf',
                  ('call', 'nullCheck'),
                  '488bd3498bcf',
                  ('call', 'arrayFetch'),
                  ('rip', '488b15', 'anonymousType', ''),
                  '488bc8',
                  ('call', 'cast'),
                  '488bd8488b8424f0030000488b7868488bcb',
                  ('call', 'nullCheck'),
                  '48635b20488bcf',
                  ('call', 'nullCheck'),
                  '488bd3488bcf',
                  ('call', 'anonymousInfoFetch'),
                  '488bd8488bc8',
                  ('call', 'nullCheck'),
                  '488b5b30488b7c2450488bcf',
                  ('call', 'nullCheck'),
                  '8b7f04488bcb',
                  ('call', 'nullCheck'),
                  '0fb7d7488bcb',
                  ('call', 'int32ArrayFetch'),
                  '4863f8',
                  ('edge', 'e9', 'commonInternal')],
 'Calli': ['8bd6498bcc',
           ('call', 'subtractSlot'),
           '4c8bf8488bc8',
           ('call', 'nullCheck'),
           '41833f087479498bcf',
           ('call', 'nullCheck'),
           '418b0789842458010000488d942458010000',
           ('rip', '488b0d', 'valueTypeType', ''),
           ('call', 'boxOperand'),
           '4533c0488bd0',
           ('rip', '488b0d', 'badTagLiteral', ''),
           ('call', 'concatObjects'),
           '488bf8',
           ('rip', '488b0d', 'invalidProgramType', ''),
           ('call', 'allocateObject'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '4533c0488bd7488bcb',
           ('call', 'invalidProgramCtor'),
           '4533c941b001488bd3488bbc24f0030000488bcf',
           ('call', 'runtimeException'),
           '498bcf',
           ('call', 'nullCheck'),
           '49635f044c8ba42408040000498bcc',
           ('call', 'nullCheck'),
           '488bd3498bcc',
           ('call', 'arrayFetch'),
           ('rip', '488b15', 'methodBaseType', ''),
           '488bc8',
           ('call', 'cast'),
           '4c8bf0488b9c2410040000488bd3498bcf',
           ('call', 'pointerDifference'),
           '498bcc',
           ('call', 'nullCheck'),
           '33d2498bcc',
           ('call', 'assignmentCheck'),
           '488bd3498bcf',
           ('call', 'pointerDifference'),
           '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04533c0498bcc',
           ('call', 'managedStore'),
           '4533c033d2498bce',
           ('call', 'methodBaseEqual'),
           '413ac5743a',
           ('rip', '488b0d', 'invalidProgramType', ''),
           ('call', 'allocateObject'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '4533c0',
           ('rip', '488b15', 'nullMethodLiteral', ''),
           '488bcb',
           ('call', 'invalidProgramCtor'),
           '4533c941b001488bd3488bcf',
           ('call', 'runtimeException'),
           '488b5f38488bcb',
           ('call', 'nullCheck'),
           ('rip', '4c8b0d', 'cacheTryGet', ''),
           '4c8d8424a8000000498bd6488bcb',
           ('call', 'cacheLookupWrapper'),
           '413ac50f8516010000',
           ('rip', '488b0d', 'calliInfoType', ''),
           ('call', 'allocateObject'),
           '488bf0488bc8',
           ('call', 'nullCheck'),
           '33d2488bce',
           ('call', 'infoCtor'),
           ('rip', '488b0d', 'reflectionType', ''),
           ('call', 'allocateObject'),
           '488bf8488bc8',
           ('call', 'nullCheck'),
           '4533c0498bd6488bcf',
           ('call', 'reflectionCtor'),
           ('rip', '488b0d', 'externInvokerType', ''),
           ('call', 'allocateObject'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '4533c9',
           ('rip', '4c8b05', 'reflectionMethod', ''),
           '488bd7488bcb',
           ('call', 'externDelegateCtor'),
           '488bce',
           ('call', 'nullCheck'),
           '48895e10488d4e10488bd3',
           ('call', 'writeBarrier'),
           '498bce',
           ('call', 'nullCheck'),
           'b912000000498bd6',
           ('call', 'parameterQuery'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '498bce',
           ('call', 'nullCheck'),
           '33d2498bce',
           ('call', 'isStatic'),
           '8b5b18413ac5bf010000007403418bfd488bce',
           ('call', 'nullCheck'),
           '8bd78bcb',
           ('call', 'int32Add'),
           '8946184889b424a8000000488b8424f0030000488b5838488bcb',
           ('call', 'nullCheck'),
           ('rip', '4c8b0d', 'cacheSet', ''),
           '4c8bc6498bd6488bcb',
           ('call', 'cacheStoreWrapper'),
           'be0c000000488b9c24a8000000488bcb',
           ('call', 'nullCheck'),
           '48634b188bd6',
           ('call', 'slotMultiply'),
           '488bd0498bcf',
           ('call', 'pointerDifference'),
           '488bf8488b9c2410040000483bc373624533c0498bd6',
           ('rip', '488b0d', 'underflowPrefix', ''),
           ('call', 'concatObjects'),
           '488bf0',
           ('rip', '488b0d', 'invalidProgramType', ''),
           ('call', 'allocateObject'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '4533c0488bd6488bcb',
           ('call', 'invalidProgramCtor'),
           '4533c941b001488bd34c8bb424f0030000498bce',
           ('call', 'runtimeException'),
           'be0c000000488b9c2410040000eb084c8bb424f003000048897c2460ba28000000488d8c24c0000000',
           ('call', 'zeroMemory'),
           '4889bc24c00000004889bc24d80000004c89a424d0000000498bd4488d8c24d0000000',
           ('call', 'writeBarrier'),
           '48899c24c80000000f108424c00000000f118424480200000f108c24d00000000f118c2458020000f20f108424e0000000f20f11842468020000',
           ('rip', '488b0d', 'threadType', ''),
           ('call', 'classInitialize'),
           '33c9',
           ('call', 'stackGet'),
           '488bd8488bc8',
           ('call', 'nullCheck'),
           '488b5b10488bcb',
           ('call', 'nullCheck'),
           '48897b08488b9c24a8000000488bcb',
           ('call', 'nullCheck'),
           '488b5b10488bcb',
           ('call', 'nullCheck'),
           '4c896c24204533c94c8d842448020000498bd6488bcb',
           ('call', 'externInvoke'),
           '4c8ba424600200004c89642458',
           ('edge', 'e9', 'calliTail')],
 'externalCaller': ['4c8b742450498bce',
                    ('call', 'nullCheck'),
                    '458b760441c1fe10488b8424f0030000488b5830488bcb',
                    ('call', 'nullCheck'),
                    '4963d7488bcb',
                    ('call', 'anonymousInfoFetch'),
                    '488bf8493bc50f8592000000488b8424f0030000488b7030488b5840488bcb',
                    ('call', 'nullCheck'),
                    '4963d7488bcb',
                    ('call', 'arrayFetch'),
                    '488bf8',
                    ('rip', '488b0d', 'reflectionType', ''),
                    ('call', 'allocateObject'),
                    '488bd8488bc8',
                    ('call', 'nullCheck'),
                    '4533c0488bd7488bcb',
                    ('call', 'reflectionCtor'),
                    ('rip', '488b0d', 'externInvokerType', ''),
                    ('call', 'allocateObject'),
                    '488bf8488bc8',
                    ('call', 'nullCheck'),
                    '4533c9',
                    ('rip', '4c8b05', 'reflectionMethod', ''),
                    '488bd3488bcf',
                    ('call', 'externDelegateCtor'),
                    '488bce',
                    ('call', 'nullCheck'),
                    '498bd74c8bc7488bce',
                    ('call', 'arrayStore'),
                    'be0c0000004963ce8bd6',
                    ('call', 'slotMultiply'),
                    '488bd0498bcc',
                    ('call', 'pointerDifference'),
                    '488bd8ba28000000488d8c24c0000000',
                    ('call', 'zeroMemory'),
                    '48899c24c000000048899c24d8000000488b84240804000048898424d0000000488bd0488d8c24d0000000',
                    ('call', 'writeBarrier'),
                    '488b84241004000048898424c80000000f108424c00000000f118424700200000f108c24d00000000f118c2480020000f20f108424e0000000f20f11842490020000',
                    ('rip', '488b0d', 'threadType', ''),
                    ('call', 'classInitialize'),
                    '33c9',
                    ('call', 'stackGet'),
                    '488bd8488bc8',
                    ('call', 'nullCheck'),
                    '488b5b10488bcb',
                    ('call', 'nullCheck'),
                    '4c8963088b5c2470488bcf',
                    ('call', 'nullCheck'),
                    '83fb18410f94c14c896c24204c8d842470020000488b9424f0030000488bcf',
                    ('call', 'externInvoke'),
                    '4c8ba42488020000',
                    ('edge', 'e9', 'externalCommit')],
 'Ret': ['4c39ac2430040000742f48638c24280400008bd6',
         ('call', 'slotMultiply'),
         '488bd0488bbc2400040000488bcf',
         ('call', 'pointerDifference'),
         '488b8c2430040000488901eb08488bbc2400040000498bce',
         ('call', 'nullCheck'),
         '45396e047579488bb42498000000488bd3498bcc',
         ('call', 'pointerDifference'),
         '488bc848b8abaaaaaaaaaaaa2a48f7e948d1fa488bc248c1e83f4803d04963c5483bc27d3c498bcf',
         ('call', 'nullCheck'),
         '33d2498bcf',
         ('call', 'assignmentCheck'),
         '8bd6418bcd',
         ('call', 'int32Add'),
         '4863d04533c0498bcf',
         ('call', 'managedStore'),
         'ba01000000418bcd',
         ('call', 'int32Add'),
         '448be8eb94e9330100008bd6498bcc',
         ('call', 'subtractSlot'),
         '488bc88b4008f20f1001f20f1107894708488bcf',
         ('call', 'nullCheck'),
         '833f08740d488bcf',
         ('call', 'nullCheck'),
         '833f09755e488bcf',
         ('call', 'nullCheck'),
         '48635f044c8bb42498000000413bde7437498bcf',
         ('call', 'nullCheck'),
         '488bd3498bcf',
         ('call', 'arrayFetch'),
         '488bd8498bcf',
         ('call', 'nullCheck'),
         '488bd3498bcf',
         ('call', 'assignmentCheck'),
         '4963d64c8bc3498bcf',
         ('call', 'managedStore'),
         '488bcf',
         ('call', 'nullCheck'),
         '44897704eb084c8bb42498000000bb01000000488b942410040000498bcc',
         ('call', 'pointerDifference'),
         '488bc848b8abaaaaaaaaaaaa2a48f7e9488bca48d1f9488bc148c1e83f4803c8488bd3',
         ('call', 'pointerDifference'),
         '4963cd483bc87d46498bcf',
         ('call', 'nullCheck'),
         '33d2498bcf',
         ('call', 'assignmentCheck'),
         '418bd6418bcd',
         ('call', 'int32Add'),
         '8bd38bc8',
         ('call', 'int32Add'),
         '4863d04533c0498bcf',
         ('call', 'managedStore'),
         '8bd3418bcd',
         ('call', 'int32Add'),
         '448be8e97affffff8bd6488bcf',
         ('call', 'advancePointer'),
         '488bf8488bc74c8d9c24b0030000410f2873f0410f287be0450f2843d0450f284bc0450f2853b0450f285ba0450f286390450f286b80450f28b370ffffff450f28bb60ffffff498be3415f415e415d415c5f5e5bc3'],
 'calliTail': ['4c89642460', ('edge', 'e9', 'pcAdvance')],
 'commonInternal': ['488b8424f0030000488b5818488bcfba08000000',
                    ('call', 'slotMultiply'),
                    '488bd0488bcb',
                    ('call', 'pointerAdd'),
                    '488b184963ce8bd6',
                    ('call', 'slotMultiply'),
                    '488bd0498bcc',
                    ('call', 'pointerDifference'),
                    '4c896c24484c896c244044896c2438897c24304489742428488b8c241004000048894c24204d8bcf4c8bc0488bd3488b8c24f0030000',
                    ('call', 'execute'),
                    '4c8be048894424584889442460',
                    ('edge', 'e9', 'pcAdvance')],
 'argumentPosition': ['488b942410040000498bce',
                      ('call', 'pointerDifference'),
                      '488bc848b8abaaaaaaaaaaaa2a48f7e9488bca48d1f9488bc148c1e83f4803c848898c2498000000'],
 'zeroScratch': ['4533ed4c896c2468'],
 'callStructInitial': ['44896c24704c89ac24a80000000f57c033c00f118424480200000f1184245802000048898424680200000f57c90f118c24c00000000f118c24d000000048898424e00000000f118424700200000f1184248002000048898424900200004c89ac24a0010000'],
 'abiPrelude': ['488bc44c8948204c8940184889480853565741544155415641574881ecb00300000f2970b80f2978a8440f294098440f294888440f299078ffffff440f299868ffffff440f29a058ffffff440f29a848ffffff440f29b038ffffff440f29b828ffffff4d8bf94d8bf04c8be24889542478488bf1'],
 'slotWidthRestore': ['be0c000000']}
