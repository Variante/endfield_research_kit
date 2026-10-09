"""Owned ReadArray contexts and complete buffered reference-array source paths."""
from __future__ import annotations
import struct
from typing import Any,Callable
from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.reference_conversion_sources import validate_program,_target

EXTRA_OPS={'482BC8':'sub rcx, rax','6666660F1F840000000000':'nop'}


def validate_read_array_context(image: Any,contexts: list,usage: dict,entries: Any,
                                element_pointer: int,deserialize_definition: int,*,fail: Callable) -> dict:
    selected=NativeReferenceContext(image);meta=image.metadata;section=meta.sections['genericContainers']
    containers=[m.generic_container_index for m in meta.methods]
    if len(contexts)!=2 or not all(r['isMethod']and r['typeName']=='MemoryPack.MemoryPackReader'for r in contexts):
        fail('array-context-owners','both owned Reader overloads',contexts)
    def owner(row):
        m=meta.methods[row['definition']];at=section.offset+m.generic_container_index*16
        if (m.flags&0x10 or image.type_name(m.declaring_type)!='MemoryPack.MemoryPackReader'
                or meta.string(m.name_index)!='ReadArray' or m.generic_container_index<0
                or not section.offset<=at<=section.offset+section.size-16):
            fail('array-method-owner','instance ReadArray with a bounded generic container',row)
        definition,count,is_method,start=struct.unpack_from('<iiii',meta.buf,at)
        identity=method_parameter_owner(meta.buf,start,containers,source='arrayReferenceSource')
        if (definition,count,is_method)!=(m.index,1,1) or identity['methodIndex']!=m.index or identity['ordinal']!=0:
            fail('array-reciprocal-mvar','one reciprocal method parameter',identity)
        return m,start
    def array_type(pointer,start,byref=False):
        raw=image.pe.bytes_at_va(pointer,16)
        if raw[10:12]!=bytes((0x1d,0x20 if byref else 0)):
            fail('array-signature','exact SZARRAY, with required byref decoration',raw.hex())
        parameter=image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16)
        if parameter[10:12]!=b'\x1e\x00' or int.from_bytes(parameter[:8],'little')!=start:
            fail('array-signature-element','same owned MVAR element',parameter.hex())
    def slots(row,kinds):
        if [r['relativeSlot']for r in row['entries']]!=list(range(len(kinds))):
            fail('array-context-slots','complete ordered unique slots',row)
        for r,kind in zip(row['entries'],kinds,strict=True):
            raw=bytes.fromhex(r['rawHex'])
            if (len(raw)!=16 or r['kind']!=kind or int.from_bytes(raw[:4],'little')!=kind
                    or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=r['index']):
                fail('array-context-payload','same authenticated kind/index',r)
        return row['entries']
    def method_slot(row,type_name,name,start,class_argument=False):
        spec=entries.specs[row['index']];m=meta.methods[spec[0]]
        if (list(spec)!=row['methodSpec'] or image.type_name(m.declaring_type)!=type_name
                or meta.string(m.name_index)!=name or spec[2 if class_argument else 1]!=-1):
            fail('array-context-method',[type_name,name],row)
        instance=spec[1 if class_argument else 2];args=image.instantiations.resolve(instance).arguments
        if len(args)!=1:fail('array-element-arity','one method element parameter',len(args))
        raw=image.pe.bytes_at_va(args[0].type_pointer_va,16)
        if raw[10:12]!=b'\x1e\x00' or int.from_bytes(raw[:8],'little')!=start:
            fail('array-method-element','same complete owned MVAR record',raw.hex())
        return spec,instance
    first,second=contexts;fm,fvar=owner(first);sm,svar=owner(second)
    if usage['methodSpec'][:2]!=[fm.index,-1] or usage['classArguments']!=[]:
        fail('array-source-overload','closed first Reader overload',usage)
    args=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    if len(args)!=1 or args[0].type_pointer_va!=element_pointer:
        fail('array-concrete-element','same exact original field array-element pointer',usage)
    if meta.parameters_for(fm):fail('array-return-overload-abi','no explicit parameters',fm.index)
    array_type(selected.type_pointer(fm.return_type),fvar)
    fs=slots(first,[3]);nested,_=method_slot(fs[0],'MemoryPack.MemoryPackReader','ReadArray',fvar)
    if nested[0]!=sm.index:fail('array-overload-context-join','same second overload definition',nested)
    params=meta.parameters_for(sm)
    if len(params)!=1 or selected.type_name(sm.return_type)!='void':
        fail('array-byref-overload-abi','void with one array byref',sm.index)
    array_type(selected.type_pointer(params[0].type_index),svar,True)
    ss=slots(second,[3,3,2,3,2,3])
    for slot,type_name,name,class_arg in ((0,'MemoryPack.MemoryPackReader','DangerousReadUnmanagedArray',False),
            (1,'System.Array','Empty',False),(3,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',False),
            (5,'MemoryPack.MemoryPackFormatter`1','Deserialize',True)):
        spec,_=method_slot(ss[slot],type_name,name,svar,class_arg)
        if slot==5 and spec[0]!=deserialize_definition:
            fail('array-deserialize-signature','same independently proved slot-five void/two-byref formatter declaration',spec)
    array_type(selected.type_pointer(ss[2]['index']),svar)
    raw=image.pe.bytes_at_va(selected.type_pointer(ss[4]['index']),16)
    if raw[10:12]!=b'\x15\x00':fail('array-formatter-type','reference generic formatter',raw.hex())
    definition,inst=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
    leaf=image.pe.bytes_at_va(definition,16)
    if leaf[10:12]!=b'\x12\x00' or image.type_name(int.from_bytes(leaf[:8],'little'))!='MemoryPack.MemoryPackFormatter`1':
        fail('array-formatter-owner','same reference formatter definition',leaf.hex())
    instance=image.instantiations.resolve_pointer(inst)
    if instance.index!=ss[5]['methodSpec'][1] or len(instance.arguments)!=1:
        fail('array-formatter-deserialize-instance','same complete element instantiation',instance.index)
    parameter=image.pe.bytes_at_va(instance.arguments[0].type_pointer_va,16)
    if parameter[10:12]!=b'\x1e\x00' or int.from_bytes(parameter[:8],'little')!=svar:
        fail('array-formatter-element','same second overload MVAR',parameter.hex())
    return {'returnOverloadDefinition':fm.index,'byrefOverloadDefinition':sm.index,
        'readArrayOverloadsReciprocallyJoined':True,'emptyArrayTypeProviderAndDeserializeOwned':True,
        'formatterSlot':5,'unmanagedSlotExecuted':False,'runtimeInflationObserved':False}


HEADER=['4053','56','57','4157','4883EC38',None,'4C8BFA','488BD9',None,
 '837B{bufferLength:02X}01',None,'488B43{currentPtr:02X}','0FB630','8B7B{bufferLength:02X}',
 '83EF01',None,'48FF43{currentPtr:02X}','FF43{advancedCount:02X}','FF43{consumed:02X}',
 '897B{bufferLength:02X}','4080FEFF',None]
COUNT=['49833F00',None,'4080FE03',None,'48896C2468','4C896C2428','4C89742420',None,
 '4D8B2F','48837F3800',None,'488B4738','33F6','4889742460','488B38','48397738',None,
 '837B{bufferLength:02X}04',None,'488B43{currentPtr:02X}','8B28','448B73{bufferLength:02X}',
 '4183EE04',None,'488343{currentPtr:02X}04','8343{advancedCount:02X}04','8343{consumed:02X}04',
 '448973{bufferLength:02X}','486343{consumed:02X}','488B4B{totalLength:02X}','482BC8','4863C5',
 '483BC8',None,'4C89642430',None,'83FDFF',None]
POSITIVE=['85ED',None,'488B442460','4885C0',None,'488B4738','488B4010','F6803801000001',None,
 '488BD5','488BC8',None,None,'4889442460',None,None,'39B1E0000000',None,'488B4738','488B4818',None,
 '4C8BF0','85ED',None,'6666660F1F840000000000']
LOOP=['488B7C2460','4885FF',None,'4D85F6',None,'3B77{arrayLength:02X}',None,'498B0E',None,
 '4D8B16','488BD3','4863C6','498BCE','4883C004','4D8B8A98010000','4C8D04C7',
 '41FF9290010000','FFC6','3BF5',None]
TAIL=['4D85ED',None,'4D8B4510','4D85C0',None,None,'488B442460','498940{actionData:02X}',None,
 '837B{bufferLength:02X}01','498B37',None,'488B43{currentPtr:02X}','0FB628','8B7B{bufferLength:02X}',
 '83EF01',None,'48FF43{currentPtr:02X}','FF43{advancedCount:02X}','FF43{consumed:02X}',
 '897B{bufferLength:02X}','4885F6',None,'488B4E10','4885C9',None,'4084ED','0F95C0','8841{guard:02X}',
 '837B{bufferLength:02X}01','498B37',None,'488B43{currentPtr:02X}','0FB628','8B7B{bufferLength:02X}',
 '83EF01',None,'48FF43{currentPtr:02X}','FF43{advancedCount:02X}','FF43{consumed:02X}',
 '897B{bufferLength:02X}','4885F6',None,'488B4E10','4885C9',None,'4C8B642430','4084ED',
 '4C8B6C2428','488B6C2468','0F95C0','4C8B742420','8841{main:02X}','4883C438','415F','5F','5E','5B','C3']


def validate_sequence_array_programs(image: Any,programs: dict,offsets: dict,fields: dict,
                                     calls: dict,usage: dict,barrier: dict,*,fail: Callable) -> dict:
    """Exact count/cursor, identical repeated child block and normalized flags."""
    if set(programs)!={'ff','nullArray','emptyArray','singleElement','twoElements'}:
        fail('array-program-scope','all selected wrapper/array branches through return',sorted(programs))
    values=dict(offsets,**fields,arrayLength=24)
    def fmt(profile):return [h.format(**values)if h is not None else None for h in profile]
    common=HEADER+COUNT
    def profile(mode):
        if mode=='ff':return HEADER+['33F6','498BCF','498937','4883C438','415F','5F','5E','5B',None,None,'4C8BC1',None,'C3']
        if mode=='nullArray':return common+[None,'4889742460',None]+TAIL
        if mode=='emptyArray':return common+['85ED',None,'488B4738','488B4808',None,None,'4889442460',None]+TAIL
        return common+POSITIVE+LOOP+[None]+TAIL
    branch_common={8:('75',True),10:('7D',True),15:('79',True),21:('75',True),23:('75',True),25:('0F85',False),
        32:('75',True),38:('75',True),40:('7D',True),45:('79',True),55:('0F8C',False),59:('75',True)}
    branch_tail={1:('0F84',False),4:('0F84',False),8:('74',True),11:('7D',True),16:('79',True),
        22:('0F84',False),25:('0F84',False),31:('7D',True),36:('79',True),42:('74',False),45:('74',False)}
    for mode in ('ff','nullArray','emptyArray','singleElement'):
        proof=programs[mode];rows=proof['program'];expected=fmt(profile(mode))
        validate_program(image,proof,fail=fail,extra_opcodes=EXTRA_OPS)
        if len(rows)!=len(expected):fail('array-profile-size',len(expected),len(rows))
        for n,(row,wanted)in enumerate(zip(rows,expected,strict=True)):
            if wanted is not None and row[1]!=wanted:fail('array-owned-transfer-or-cursor',{'position':n,'bytes':wanted},row)
        branches=dict(branch_common);call_positions={};rips={5:'803D'};jumps={}
        if mode=='ff':
            branches={8:('75',True),10:('7D',True),15:('79',True),21:('75',False),33:('74',True)}
            rips[31]='833D';jumps[30]=barrier['program'][0][0]
            if rows[31:]!=barrier['program']:fail('array-source-ff-barrier','same independently proved disabled barrier through RET',rows[31:])
            tail_start=None
        else:
            rips.update({29:'488B3D',57:'4C8D25'})
            if rows[29]!=[usage['instructionRva'],usage['instructionHex']]:fail('array-owned-source-usage','same actual ReadArray usage load',rows[29])
            if mode=='nullArray':
                branches.update({59:('75',False),62:('0F84',True)});rips[60]='3935';tail_start=63
            elif mode=='emptyArray':
                branches.update({61:('0F84',True),67:('74',True)});call_positions[64]='emptyArray';rips[65]='3935';tail_start=68
            else:
                branches.update({61:('0F84',False),64:('74',True),68:('75',True),74:('74',True),77:('75',True),
                    83:('0F8E',False),87:('0F84',False),89:('0F84',False),91:('0F83',False),104:('7C',False)})
                call_positions.update({71:'arrayAllocation',80:'getFormatter',93:'classPrepare'})
                rips.update({72:'3935',75:'488B0D'});jumps[105]=rows[106][0];tail_start=106
            branches.update({tail_start+n:v for n,v in branch_tail.items()});rips[tail_start+5]='833D'
        covered=set(branches)|set(call_positions)|set(rips)|set(jumps)
        if covered!={n for n,h in enumerate(expected)if h is None}:
            fail('array-variable-instruction-coverage','every variable instruction owns its meaning',covered)
        for n,(opcode,taken)in branches.items():
            at,h=rows[n];raw=bytes.fromhex(h)
            if raw[:len(bytes.fromhex(opcode))]!=bytes.fromhex(opcode) or rows[n+1][0]!=(_target(at,raw)if taken else at+len(raw)):
                fail('array-selected-guard',{'position':n,'opcode':opcode,'taken':taken},rows[n:n+2])
        for n,name in call_positions.items():
            at,h=rows[n];raw=bytes.fromhex(h)
            if len(raw)!=5 or raw[0]!=0xe8 or _target(at,raw)!=calls[name]:fail('array-physical-call',name,rows[n])
        for n,prefix in rips.items():
            raw=bytes.fromhex(rows[n][1]);opcode=bytes.fromhex(prefix)
            size=6 if prefix=='3935' else 7
            if len(raw)!=size or raw[:len(opcode)]!=opcode or prefix in('803D','833D')and raw[-1]!=0:
                fail('array-rip-owned-load-or-zero-guard',prefix,rows[n])
        for n,target in jumps.items():
            at,h=rows[n];raw=bytes.fromhex(h)
            if raw[0]not in(0xe9,0xeb)or _target(at,raw)!=target:fail('array-physical-jump',target,rows[n])
    single=programs['singleElement']['program'];repeated=programs['twoElements']
    validate_program(image,repeated,fail=fail,extra_opcodes=EXTRA_OPS)
    if repeated['program']!=single[:85]+single[85:105]*2+single[105:]:
        fail('array-identical-loop-repetition','same complete twenty-instruction child block and real back edge',repeated['program'])
    at,h=single[104]
    if _target(at,bytes.fromhex(h))!=single[85][0]:fail('array-signed-count-back-edge','ESI increment compared with unchanged saved EBP count',single[102:105])
    return {'completeSelectedReturns':True,'wrapperNullWireBytes':1,'nonNullDirectWireBytes':7,
        'directCursorEquation':'1 object header + 4 array count + 1 guard flag + 1 main-character flag + sum(child cursor advances)',
        'arrayCountBits':32,'selectedArrayCounts':['-1','0','positive signed Int32'],
        'sameReaderRegister':'rbx','arrayResultEntryStackOffset':8,'countRegister':'ebp','indexRegister':'esi',
        'loopInstructionCount':20,'formatterRegister':'r14','formatterSlot':5,'childOutputRegister':'r8',
        'childOutputAddress':'array base + 32 + sign-extended index * 8','runtimeReferenceStride':8,'childWireBytes':None,
        'flagReadOrder':['onlyExecuteWhenSourceIsGuard','onlyExecuteWhenSourceIsMainChar'],
        'flagsNormalizedByNonzero':True,'sourceFrameBytesBelowEntry':88,
        'arrayAllocationAndEmptyResult':'conditional typed normal returns','calleeEffectsProved':False,
        'originalChildCursorComposition':'unresolved','positiveListAdmitted':False,'wholeRootAdmitted':False}
