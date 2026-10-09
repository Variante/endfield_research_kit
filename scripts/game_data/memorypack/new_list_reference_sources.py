"""Selected new reference-list callers and capacity-constructor return paths."""
from __future__ import annotations
import struct
from typing import Any,Callable
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.reference_conversion_sources import validate_program,_target
from scripts.game_data.memorypack.read_value_reference_sources import _profile


def validate_capacity_constructor_context(image: Any,formatter: dict,context: dict,entries: Any,*,fail: Callable) -> dict:
    meta=image.metadata;selected=NativeReferenceContext(image);owner=meta.types[context['definition']]
    section=meta.sections['genericContainers'];at=section.offset+owner.generic_container_index*16
    if (context['isMethod'] or context['typeName']!='System.Collections.Generic.List`1'
            or image.type_name(owner.index)!=context['typeName'] or owner.generic_container_index<0
            or not section.offset<=at<=section.offset+section.size-16):
        fail('capacity-class-owner','owned generic List class context',context)
    definition,count,is_method,start=struct.unpack_from('<iiii',meta.buf,at)
    identity=type_parameter_owner(meta.buf,start,[t.generic_container_index for t in meta.types],source='newListReference')
    if (definition,count,is_method)!=(owner.index,1,0)or identity['typeIndex']!=owner.index or identity['ordinal']!=0:
        fail('capacity-reciprocal-var','one exact List class parameter',identity)
    slots={r['relativeSlot']:r for r in context['entries']}
    if len(slots)!=len(context['entries'])or not {0,1}<=slots.keys():
        fail('capacity-type-slots','unique List and element-array class slots',slots)
    def parameter(pointer):
        raw=image.pe.bytes_at_va(pointer,16)
        if raw[10:12]!=b'\x13\x00'or int.from_bytes(raw[:8],'little')!=start:
            fail('capacity-element-identity','same exact owned class VAR',raw.hex())
    for n in(0,1):
        row=slots[n];raw=bytes.fromhex(row['rawHex'])
        if (row['kind']!=2 or len(raw)!=16 or int.from_bytes(raw[:4],'little')!=2
                or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=row['index']):
            fail('capacity-context-payload','authenticated type slots',row)
    raw=image.pe.bytes_at_va(selected.type_pointer(slots[0]['index']),16)
    if raw[10:12]!=b'\x15\x00':fail('capacity-list-type','reference List class instantiation',raw.hex())
    definition_pointer,inst_pointer=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
    root=image.pe.bytes_at_va(definition_pointer,16)
    if root[10:12]!=b'\x12\x00'or int.from_bytes(root[:8],'little')!=owner.index:
        fail('capacity-list-definition','same complete List class root',root.hex())
    args=image.instantiations.resolve_pointer(inst_pointer).arguments
    if len(args)!=1:fail('capacity-list-arity',1,len(args))
    parameter(args[0].type_pointer_va)
    raw=image.pe.bytes_at_va(selected.type_pointer(slots[1]['index']),16)
    if raw[10:12]!=b'\x1d\x00':fail('capacity-array-type','SZARRAY of the same owned parameter',raw.hex())
    parameter(int.from_bytes(raw[:8],'little'))
    constructor=next((r for r in formatter['entries']if r['relativeSlot']==1),None)
    clear=next((r for r in formatter['entries']if r['relativeSlot']==2),None)
    if constructor is None or clear is None or constructor['kind']!=3:
        fail('capacity-formatter-constructor','owned constructor slot one',constructor)
    raw=bytes.fromhex(constructor['rawHex'])
    if (len(raw)!=16 or int.from_bytes(raw[:4],'little')!=3
            or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=constructor['index']):
        fail('capacity-constructor-payload','same authenticated MethodSpec',constructor)
    spec=entries.specs[constructor['index']];m=meta.methods[spec[0]];params=meta.parameters_for(m)
    if (list(spec)!=constructor['methodSpec']or spec[2]!=-1 or spec[1]!=clear['methodSpec'][1]
            or m.declaring_type!=owner.index or meta.string(m.name_index)!='.ctor' or m.flags&0x10
            or selected.type_name(m.return_type)!='void' or len(params)!=1):
        fail('capacity-constructor-abi','same List class instance constructor with one capacity parameter',spec)
    parameter_raw=image.pe.bytes_at_va(selected.type_pointer(params[0].type_index),16)
    if parameter_raw[10:12]!=b'\x08\x80' or selected.type_name(params[0].type_index)!='int':
        fail('capacity-int32-parameter','selected by-value signed Int32 parameter record',parameter_raw.hex())
    return {'constructorDefinition':m.index,'listClassDefinition':owner.index,
        'classSlots':[0,1],'formatterConstructorSlot':1,'capacityBits':32,
        'ownedClassParameterOrdinal':0,'openGenericFieldOffsetsUsed':False,'runtimeInflationObserved':False}


def validate_capacity_constructor_programs(image: Any,programs: dict,array_call: int,*,fail: Callable) -> dict:
    if set(programs)!={'zero','positive'}:fail('capacity-program-scope','zero and positive capacity returns',programs)
    common=['48895C2408','4889742410','57','4883EC20','8BDA','498BF0','488BF9','85D2',None,
        '498B4020','488B80C0000000',None]
    suffix=['488B5C2430','488B742438','4883C420','5F','C3']
    positive=common+['488B4008','F6803801000001',None,'488BD3','488BC8',None,None,'48894710',None]+suffix
    zero=common+['488B00','F6803801000001',None,'83B8E000000000',None,'488B4620','488B88C0000000',
        '488B01','F6803801000001',None,None,'488B80B8000000','488B08','48894F10',None]+suffix
    _profile(image,programs['positive'],positive,{8:('0F88',False),11:('0F84',False),14:('75',True),20:('74',True)},
        {17:'arrayAllocation'},{18:'833D'},(),(),{'arrayAllocation':array_call},fail=fail)
    _profile(image,programs['zero'],zero,{8:('0F88',False),11:('0F84',True),14:('75',True),16:('75',True),21:('75',True),26:('74',True)},
        {},{22:'833D'},(),(),{},fail=fail)
    flags=[]
    for key,n in(('positive',18),('zero',22)):
        at,h=programs[key]['program'][n];raw=bytes.fromhex(h);flags.append(at+7+int.from_bytes(raw[2:6],'little',signed=True))
    if flags[0]!=flags[1]:fail('capacity-barrier-state','same independently selected constructor barrier flag',flags)
    return {'completeSelectedReturns':True,'savedReceiver':'rdi','savedCapacity':'ebx','savedMethodInfo':'rsi',
        'arrayContextSlot':1,'observedReceiverReferenceSlot':16,'storedArrayResultBits':64,
        'positiveCapacityPassedUnchanged':True,'zeroCapacityReadsStaticReference':True,
        'directCountOrVersionWrites':0,'receiverCountZeroProved':False,'arrayAllocationEffectsProved':False,
        'disabledBarrierFlagRva':flags[0],'openGenericFieldOffsetsUsed':False}


def validate_new_reference_list(image: Any,programs: dict,existing: dict,calls: dict,*,fail: Callable) -> dict:
    """Join new allocation/constructor prefix to the independently proved loop."""
    if set(programs)!={'nullList','emptyNewList','singleElement','twoElements'}:
        fail('new-list-program-scope','null, empty-new, single and repeated reference list',programs)
    old=existing['program'];single=programs['singleElement']['program']
    for p in programs.values():validate_program(image,p,fail=fail,extra_opcodes={'482BC8':'sub rcx, rax'})
    if (len(single)!=124 or single[:39]!=old[:39]or single[62:73]!=old[50:61]
            or single[73:114]!=old[61:102]or single[114:]!=old[102:]):
        fail('new-list-shared-loop-and-cursor','same independently proved count/provider/41-instruction loop/full epilogue',single)
    middle=['488B88C0000000','488B01','F6803801000001',None,'488BC8',None,'488BD8','4885C0',None,
        '488B4D20','488B91C0000000','488B4A08','4C396120',None,'488B4520','8BD7','488BCB',
        '4C8B80C0000000','4D8B4008',None,None,'48891E',None]
    for n,(row,h)in enumerate(zip(single[39:62],middle,strict=True),39):
        if h is not None and row[1]!=h:fail('new-list-allocation-constructor-output',{'position':n,'bytes':h},row)
    for n,op,taken in((38,'74',True),(42,'75',True),(47,'0F84',False),(52,'75',True),(61,'74',True),(72,'0F8E',False)):
        at,h=single[n];raw=bytes.fromhex(h)
        if raw[:len(bytes.fromhex(op))]!=bytes.fromhex(op)or single[n+1][0]!=(_target(at,raw)if taken else at+len(raw)):
            fail('new-list-selected-guard',{'position':n,'opcode':op,'taken':taken},single[n:n+2])
    for n,name in((44,'objectAllocation'),(58,'capacityConstructor')):
        at,h=single[n];raw=bytes.fromhex(h)
        if len(raw)!=5 or raw[0]!=0xe8 or _target(at,raw)!=calls[name]:fail('new-list-actual-call',name,single[n])
    at,h=single[59];raw=bytes.fromhex(h)
    if len(raw)!=7 or raw[:3]!=b'\x44\x39\x25':fail('new-list-output-disabled-barrier','RIP comparison with preserved R12D zero',single[59])
    flag=at+7+int.from_bytes(raw[3:7],'little',signed=True)
    if programs['emptyNewList']['program']!=single[:73]+single[114:]:
        fail('empty-new-list-return','same constructor/provider prefix and direct no-child return',programs['emptyNewList']['program'])
    if programs['twoElements']['program']!=single[:73]+single[73:114]*2+single[114:]:
        fail('new-list-exact-loop-repetition','same independently proved full loop and back edge',programs['twoElements']['program'])
    null=programs['nullList']['program']
    null_tail=[None,'4C8926',None]+[r[1]for r in old[-8:]]
    if len(null)!=44 or null[:33]!=old[:33]:fail('null-list-header','same complete four-byte count/cursor prefix',null)
    for n,(row,wanted)in enumerate(zip(null[33:],null_tail,strict=True),33):
        if wanted is not None and row[1]!=wanted:fail('null-list-output-and-return',{'position':n,'bytes':wanted},row)
    at,h=null[33];raw=bytes.fromhex(h)
    if len(raw)!=7 or raw[:3]!=b'\x44\x39\x25'or at+7+int.from_bytes(raw[3:7],'little',signed=True)!=flag:
        fail('null-list-output-barrier-state','same disabled output barrier flag',null[33])
    at,h=null[35];raw=bytes.fromhex(h)
    if raw[:1]!=b'\x74'or _target(at,raw)!=null[36][0]:fail('null-list-selected-return','selected disabled barrier return',null[35:37])
    return {'completeSelectedReturns':True,'listNullWireBytes':4,'listHeaderWireBytes':4,'elementWireBytes':None,
        'allocatedListRegister':'rbx','sameConstructedListStoredThroughOutput':True,
        'capacityCountPassedUnchanged':True,'reusedLoopInstructionCount':41,'sameReaderRegister':'r14',
        'newObjectInitialCount':'conditional zero','spareArrayCapacity':'conditional typed allocation result',
        'outputDisabledBarrierFlagRva':flag,'positiveListAdmitted':False,'wholeRootAdmitted':False}
