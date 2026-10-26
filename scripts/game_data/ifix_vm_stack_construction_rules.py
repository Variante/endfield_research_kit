"""Authenticate thread-stack construction and Call.Begin's frame recipe.

Call.Begin requests ThreadStackInfo.get_Stack and zeroes its five-word output,
then stores ManagedStack, Top as currentTop, another Top read as argumentBase,
Base as evaluationStackBase and the address of Top as topWriteBack. These
are repeated field reads, not an atomic snapshot. The inherited complete
write-barrier grammar preserves the saved thread receiver register across
the managed-array store. Under stable valid storage the frame's writeback
pointer therefore aliases that thread holder's Top word.

get_Stack initializes its named class, reads static localSlot and requests
Thread.GetData. A nonnull ThreadStackInfo cast result is returned immediately.
A null cast result requests the named VM._Info message, allocation and the
thread constructor, then Thread.SetData with localSlot and that saved new
receiver before returning it. Thread selection, cast/API results, class and
thread-local state, allocation and logger outcomes remain unobserved.

The constructor requests two Marshal.AllocHGlobal(int) allocations. It stores
the first result as evaluationStackHandler, the second as unmanagedStackHandler
and UnmanagedStack, then writes the first result to both unboxed Base and Top.
It requests an object[] using the declared slot count and stores ManagedStack.
The native requested Value byte count is checked against slot count times
descriptor width; this describes allocation requests, not valid capacity or
successful storage. The static constructor requests Thread.AllocateDataSlot
and stores its return as static localSlot with a reference barrier.

Full finite programs authenticate all branches, null-failure exits, typed
cells, helper calls and stores. Named metadata includes nested byref/kind and
instance/static checks. Runtime pointers, bounds, allocator defaults, aliases,
thread races, helper mutation, GC, unwinding and actual execution stay open.
Native declarations live in reviewed JSON. No VM method named AllocateStack
is presumed from a source guide or from an anonymous allocation helper.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name,runtime_type_field_offsets
from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program,_barrier_program
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect,_identity
from scripts.game_data.ifix_vm_reference_update_rules import _type_pointer
from scripts.game_data.ifix_vm_call_opcode_rules import _carrier


class StackConstructionRuleError(ValueError):
    """A thread/frame construction request lacks its selected witness."""


_METHOD_REFS={'begin':'delegateBridgeRules.methods.begin','stackGet':'callOpcodeRules.methods.stackGet','threadCtor':'newFieldRules.methods.threadCtor'}
_METHODS={'begin':('IFix.Core.Call','Begin',[],'IFix.Core.Call',True),
 'stackGet':('IFix.Core.ThreadStackInfo','get_Stack',[],'IFix.Core.ThreadStackInfo',True),
 'threadCtor':('IFix.Core.ThreadStackInfo','.ctor',[],'void',False),
 'staticConstructor':('IFix.Core.ThreadStackInfo','.cctor',[],'void',True),
 'getData':('System.Threading.Thread','GetData',['System.LocalDataStoreSlot'],'object',True),
 'setData':('System.Threading.Thread','SetData',['System.LocalDataStoreSlot','object'],'void',True),
 'allocateSlot':('System.Threading.Thread','AllocateDataSlot',[],'System.LocalDataStoreSlot',True),
 'allocHGlobal':('System.Runtime.InteropServices.Marshal','AllocHGlobal',['int'],'nint',True),
 'logInfo':('IFix.Core.VirtualMachine','_Info',['string'],'void',True)}
_HELPER_REFS={'typeInitialize':'referenceUpdateRules.helpers.typeInitialize','classInitialize':'objectConversionRules.helpers.classInitialize',
 'allocateThread':'stackReferenceRules.nullObjectHelper','arrayAllocate':'objectConversionRules.helpers.arrayAllocate',
 'cast':'referenceUpdateRules.helpers.cast','nullFailure':'referenceUpdateRules.helpers.nullFailure','writeBarrier':'delegateBridgeRules.referenceWriteBarrier'}
_USAGE_REFS={'threadType':'callOpcodeRules.usageCells.threadType','objectArray':'arrayRules.usageCells.objectArray',
 'marshalType':'objectOpcodeRules.usageCells.cell01'}
_CELLS={'threadType':'IFix.Core.ThreadStackInfo','objectArray':'object[]','marshalType':'System.Runtime.InteropServices.Marshal',
 'vmType':'IFix.Core.VirtualMachine','createLiteral':'create thread stack'}
_EXTRA_FIELDS={'IFix.Core.ThreadStackInfo':{'ManagedStack':('object[]',24,False),'evaluationStackHandler':('nint',32,False),
 'unmanagedStackHandler':('nint',40,False),'localSlot':('System.LocalDataStoreSlot',0,True)},
 'IFix.Core.UnmanagedStack':{'Base':('IFix.Core.Value*',16,False)}}
_CLAIMS={'schema':'endfield.ifix-vm-stack-construction-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'methodRefs':_METHOD_REFS,'helperRefs':_HELPER_REFS,'usageRefs':_USAGE_REFS,'layoutRef':'callOpcodeRules.fieldLayouts',
 'frameRecipe':'zero-five-words;thread.ManagedStack;thread.Top:currentTop;thread.Top:argumentBase;thread.Base:evaluationStackBase;address-of-thread.Top:topWriteBack',
 'threadSelectionRecipe':'GetData(static-localSlot);cast-ThreadStackInfo;nonnull:return-cast;null:_Info;allocate-construct;SetData(localSlot,saved-receiver);return-saved-receiver',
 'constructorRecipe':'two-AllocHGlobal-int-requests;store-both-handlers-and-second-UnmanagedStack;write-first-result-as-Base-and-Top;allocate-and-store-object-array;barrier',
 'staticRecipe':'AllocateDataSlot;store-static-localSlot;reference-barrier',
 'allocationBoundary':'declared-native-byte-and-slot-requests-only;allocator-defaults-actual-capacity-and-validity-unobserved',
 'storageBoundary':'valid-stable-thread-holder-frame-and-arrays;normal-helpers-without-unmodelled-mutation',
 'aliasBoundary':'conditional-Top-word-writeback-address;repeated-reads-not-atomic;runtime-overlap-races-and-helper-mutation-unobserved',
 'runtimeBoundary':'thread-API-cast-logger-class-init-allocation-GC-and-execution-unobserved',
 'exceptionBoundary':'authenticated-null-failure-request-and-stop-byte;runtime-throw-unwind-unobserved',
 'valueBytes':12,'callBytes':40,'objectHeaderBytes':16}


def _need(ok: bool,detail: str) -> None:
    if not ok:raise StackConstructionRuleError('stackConstruction.'+detail)


def _signature(image: Any,identity: tuple) -> None:
    owner,name,params,returned,static=identity;md=image.metadata
    methods=[m for t in md.types if md.type_full_name(t)==owner for m in md.methods_for(t)if md.string(m.name_index)==name and m.parameter_count==len(params)
        and [runtime_type_name(image.pe,md,_type_pointer(image,p.type_index))for p in md.parameters_for(m)]==params]
    _need(len(methods)==1,'one named overload required');m=methods[0]
    _need(bool(m.flags&0x10)==static and m.generic_container_index==-1,'static/generic signature differs')
    for index,typ in [(p.type_index,typ)for p,typ in zip(md.parameters_for(m),params)]+[(m.return_type,returned)]:_carrier(image,_type_pointer(image,index),typ)


def _fields(image: Any,spec: dict,contract: dict) -> None:
    inherited=_ref(contract,spec['layoutRef']);owners={'IFix.Core.ThreadStackInfo':False,'IFix.Core.UnmanagedStack':True,'IFix.Core.Call':True}
    _need(spec['additionalFields']=={owner:{n:{'type':typ,'offset':off,'static':static}for n,(typ,off,static)in fields.items()}for owner,fields in _EXTRA_FIELDS.items()},'additional field declarations differ')
    required={'IFix.Core.ThreadStackInfo':{'UnmanagedStack':('IFix.Core.UnmanagedStack*',16)},
        'IFix.Core.UnmanagedStack':{'Top':('IFix.Core.Value*',24)},'IFix.Core.Call':{'argumentBase':('IFix.Core.Value*',16),
            'evaluationStackBase':('IFix.Core.Value*',24),'managedStack':('object[]',32),'currentTop':('IFix.Core.Value*',40),'topWriteBack':('IFix.Core.Value**',48)}}
    md=image.metadata
    for owner,value in owners.items():
        types=[t for t in md.types if md.type_full_name(t)==owner]
        _need(len(types)==1 and bool(types[0].bitfield&1)==value and inherited[owner]['type']==owner and inherited[owner]['isValueType']==value,'layout owner/value kind differs')
        fields={n:(typ,off,False)for n,(typ,off)in required[owner].items()}
        for n,(typ,off)in required[owner].items():_need(inherited[owner]['fields'].get(n)=={'type':typ,'offset':off},'inherited field differs')
        fields.update(_EXTRA_FIELDS.get(owner,{}));definitions={md.string(f.name_index):f for f in md.fields_for(types[0])};offsets=runtime_type_field_offsets(md,image.pe,image.registration,types[0].index)
        for n,(typ,off,static)in fields.items():
            _need(n in definitions and offsets.get(n)==off,'selected field offset differs');pointer=_type_pointer(image,definitions[n].type_index);_carrier(image,pointer,typ)
            _need(bool(int.from_bytes(image.pe.bytes_at_va(pointer,16)[8:10],'little')&0x10)==static,'selected field static kind differs')


def _cells(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    _need(set(spec['usageCells'])==set(_CELLS)-set(_USAGE_REFS),'usage declaration set differs')
    rows=dict(spec['usageCells']);rows.update({n:_ref(contract,path)for n,path in _USAGE_REFS.items()});result={}
    for name,row in rows.items():
        at=_rva(row['cellRva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,8);result[name]=at
        stored=row.get('rawHex',_rva(row.get('encodedWord',0)).to_bytes(8,'little').hex())
        _need(raw==bytes.fromhex(stored) and row.get('usageTag')==(5 if name=='createLiteral'else 1),'usage bytes/tag differ')
        _need(row.get('identity',row.get('typeName'))==_CELLS[name],'usage declared identity differs')
        if name=='createLiteral':
            md=image.metadata;table,pool=md.sections['stringLiteral'],md.sections['stringLiteralData'];idx=unresolved_usage_index(raw,table.size//8,tag=5,source='stackConstruction.literal',offset=at);off=table.offset+idx*8
            start,size=literal_record(md.buf[off:off+8],pool.size,source='stackConstruction.literal',offset=off)
            _need(md.buf[pool.offset+start:pool.offset+start+size]==_CELLS[name].encode(),'create-thread literal differs')
        else:
            index=unresolved_usage_index(raw,image.registration['typesCount'],tag=1,source='stackConstruction.type',offset=at);_carrier(image,_type_pointer(image,index),_CELLS[name])
    _need(set(spec['flags'])==set(_PROGRAMS),'initialization flag set differs')
    result.update({n+'Flag':_rva(at)for n,at in spec['flags'].items()});return result


def _program(name: str,at: int,targets: dict[str,int],cells: dict[str,int],spec: dict) -> bytes:
    p=_Program(at)
    for token in _PROGRAMS[name]:
        if isinstance(token,str):p.add(token);continue
        kind,*args=token
        if kind=='call':p.call(targets[args[0]])
        elif kind=='rip':p.rip(args[0],cells[args[1]],bytes.fromhex(args[2]))
        elif kind=='tail':p.rip('e9',targets[args[0]])
        elif kind=='imm':p.add(args[0]);p.add(spec['allocationRequests'][args[1]].to_bytes(4,'little',signed=True))
        else:_need(False,'unknown finite token')
    return p.finish()


def validate_stack_construction_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    """Parent supplies authenticated selected inputs and dependency groups."""
    _need(all(type(spec.get(k))is type(v)and spec.get(k)==v for k,v in _CLAIMS.items()),'unsupported schema/reference/boundary')
    _need(set(spec['methods'])==set(_METHODS)-set(_METHOD_REFS),'method declaration set differs');_fields(image,spec,contract);targets={};bodies={}
    allocation=spec['allocationRequests'];_need(set(allocation)=={'valueStorageBytes','managedSlotCount','holderBytes'}and all(type(n)is int and 0<n<=0x7fffffff for n in allocation.values())
        and allocation['valueStorageBytes']==allocation['managedSlotCount']*spec['valueBytes'] and allocation['holderBytes']==16,'allocation byte/slot requests differ')
    for name,identity in _METHODS.items():
        row=dict(_ref(contract,_METHOD_REFS[name])if name in _METHOD_REFS else spec['methods'][name]);row.setdefault('parameterCount',len(identity[2]));_signature(image,identity)
        targets[name]=_identity(image,row,identity,name,extents,body_required=name in _PROGRAMS)
        if name in _PROGRAMS:bodies[name]=image.pe.bytes_at_va(image.pe.image_base+targets[name],row['bodyBytes'])
        else:_need(row.get('effectBoundary')=='named-request-runtime-outcome-unobserved','API outcome promoted')
    for name,path in _HELPER_REFS.items():
        row=_ref(contract,path);at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']),row,name);targets[name]=at
    barrier=_ref(contract,_HELPER_REFS['writeBarrier']);_expect(image.pe.bytes_at_va(image.pe.image_base+targets['writeBarrier'],barrier['byteCount']),_barrier_program(barrier),'frame.receiver-preserving-barrier')
    cells=_cells(image,spec,contract)
    for name in _PROGRAMS:_expect(bodies[name],_program(name,targets[name],targets,cells,spec),name+'.full-finite-program')
    return {'status':'validated_conditional_thread_stack_and_frame_recipes','evidenceBoundary':'conditional','executionBoundary':'unobserved',
        **{k:spec[k]for k in ('frameRecipe','threadSelectionRecipe','constructorRecipe','staticRecipe','allocationBoundary','storageBoundary','aliasBoundary','runtimeBoundary','exceptionBoundary')},
        'allocationRequests':allocation,'unresolved':['runtime-thread-slot-and-GetData-SetData-cast-results','runtime-allocator-results-and-capacity-validity',
            'class-state-and-thread-races','repeated-field-read-stability-and-storage-aliases','logger-helper-and-GC-outcomes','throw-unwind-and-actual-execution']}


def validate_selected_stack_construction_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit GameAssembly and metadata paths are required'}
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'selected native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.stackConstruction')
    return validate_stack_construction_rules(image,contract['stackConstructionRules']if spec is None else spec,contract,image.mapper.pdata_function_extents(image.pe))


_PROGRAMS = {'begin': ['40534883ec20',
           ('rip', '803d', 'beginFlag', '00'),
           '488bd97513',
           ('rip', '488d0d', 'threadType', ''),
           ('call', 'typeInitialize'),
           ('rip', 'c605', 'beginFlag', '01'),
           '0f57c033c00f11030f11431048894320',
           ('rip', '488b0d', 'threadType', ''),
           ('call', 'classInitialize'),
           '33c9',
           ('call', 'stackGet'),
           '4c8bc80f57c033c00f11030f114310488943204d85c9745c498b491848894b10488d4b10',
           ('call', 'writeBarrier'),
           '498b41104885c07442488b400848894318498b41104885c07431488b4008488903498b41104885c07421488b0048894308498b41104885c074114883c00848894320488bc34883c4205bc3',
           ('call', 'nullFailure'),
           'cc'],
 'stackGet': ['40534883ec20',
              ('rip', '803d', 'stackGetFlag', '00'),
              '752b',
              ('rip', '488d0d', 'threadType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'vmType', ''),
              ('call', 'typeInitialize'),
              ('rip', '488d0d', 'createLiteral', ''),
              ('call', 'typeInitialize'),
              ('rip', 'c605', 'stackGetFlag', '01'),
              ('rip', '488b0d', 'threadType', ''),
              ('call', 'classInitialize'),
              ('rip', '488b05', 'threadType', ''),
              '33d2488b88b8000000488b09',
              ('call', 'getData'),
              ('rip', '488b15', 'threadType', ''),
              '488bc8',
              ('call', 'cast'),
              '488bd84885c07566',
              ('rip', '488b0d', 'vmType', ''),
              ('call', 'classInitialize'),
              ('rip', '488b0d', 'createLiteral', ''),
              '33d2',
              ('call', 'logInfo'),
              ('rip', '488b0d', 'threadType', ''),
              ('call', 'allocateThread'),
              '488bd84885c07506',
              ('call', 'nullFailure'),
              'cc33d2488bcb',
              ('call', 'threadCtor'),
              ('rip', '488b0d', 'threadType', ''),
              ('call', 'classInitialize'),
              ('rip', '488b05', 'threadType', ''),
              '4533c0488bd3488b88b8000000488b09',
              ('call', 'setData'),
              '488bc34883c4205bc3'],
 'threadCtor': ['40534883ec20',
                ('rip', '803d', 'threadCtorFlag', '00'),
                '488bd9751f',
                ('rip', '488d0d', 'marshalType', ''),
                ('call', 'typeInitialize'),
                ('rip', '488d0d', 'objectArray', ''),
                ('call', 'typeInitialize'),
                ('rip', 'c605', 'threadCtorFlag', '01'),
                ('rip', '488b0d', 'marshalType', ''),
                ('call', 'classInitialize'),
                '33d2',
                ('imm', 'b9', 'valueStorageBytes'),
                ('call', 'allocHGlobal'),
                '33d2488943208d4a10',
                ('call', 'allocHGlobal'),
                '4889432848894310488b4b204885c0742a48894808',
                ('imm', 'ba', 'managedSlotCount'),
                '488908',
                ('rip', '488b0d', 'objectArray', ''),
                ('call', 'arrayAllocate'),
                '488d4b18488943184883c4205b',
                ('tail', 'writeBarrier'),
                ('call', 'nullFailure'),
                'cc'],
 'staticConstructor': ['4883ec28',
                       ('rip', '803d', 'staticConstructorFlag', '00'),
                       '7513',
                       ('rip', '488d0d', 'threadType', ''),
                       ('call', 'typeInitialize'),
                       ('rip', 'c605', 'staticConstructorFlag', '01'),
                       '33c9',
                       ('call', 'allocateSlot'),
                       ('rip', '488b0d', 'threadType', ''),
                       '488b91b8000000488902',
                       ('rip', '488b0d', 'threadType', ''),
                       '488b89b80000004883c428',
                       ('tail', 'writeBarrier')]}
