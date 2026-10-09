"""Selected buffered reference-list control, below stored element admission.

The caller owns type/provider selection and child grammar. Exact header cursor
accounting and a reference append do not determine a child wire width. The
selected program covers an existing list with spare capacity and normal child
returns, and excludes allocation, growth, refill, error and GC-barrier paths.
"""
from __future__ import annotations

import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.reference_conversion_sources import validate_program, _target


def validate_list_element_context(image: Any, context: dict, entries: Any, *, fail: Callable) -> dict:
    """Static provider/formatter/Deserialize/Add all retain the same owned VAR."""
    selected = NativeReferenceContext(image);owner = image.metadata.types[context['definition']]
    section = image.metadata.sections['genericContainers'];at = section.offset + owner.generic_container_index*16
    if (context['isMethod'] or context['typeName'] != 'MemoryPack.Formatters.ListFormatter`1'
            or image.type_name(owner.index) != context['typeName'] or owner.generic_container_index < 0
            or not section.offset <= at <= section.offset+section.size-16):
        fail('list-context-owner','owned ListFormatter class context',context['definition'])
    definition,count,is_method,start = struct.unpack_from('<iiii',image.metadata.buf,at)
    if (definition,count,is_method) != (owner.index,1,0) or start < 0:
        fail('list-context-container','one owned class parameter',[definition,count,is_method,start])
    identity = type_parameter_owner(image.metadata.buf,start,
        [t.generic_container_index for t in image.metadata.types],source='listReferenceSource')
    if identity['typeIndex'] != owner.index or identity['ordinal'] != 0:
        fail('list-context-var-owner','reciprocal ListFormatter parameter',identity)
    slots = {r['relativeSlot']:r for r in context['entries']}
    if len(slots) != len(context['entries']) or any(n not in slots for n in (0,2,3,4,5,6)):
        fail('list-context-slots','unique element provider/formatter/Deserialize/Add slots',sorted(slots))
    def payload(slot,kind):
        row=slots[slot];raw=bytes.fromhex(row['rawHex'])
        if (len(raw)!=16 or row['kind']!=kind or int.from_bytes(raw[:4],'little')!=kind
                or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=row['index']):
            fail('list-context-payload',{'slot':slot,'kind':kind},row)
        return row
    instances=[]
    for slot,type_name,name,class_arg in ((2,'System.Collections.Generic.List`1','Clear',True),
            (3,'MemoryPack.MemoryPackFormatterProvider','GetFormatter',False),
            (5,'MemoryPack.MemoryPackFormatter`1','Deserialize',True),
            (6,'System.Collections.Generic.List`1','Add',True)):
        row=payload(slot,3);index=row['index']
        if type(index)is not int or not 0<=index<len(entries.specs):
            fail('list-method-spec-range','selected MethodSpec',index)
        spec=entries.specs[index];method=image.metadata.methods[spec[0]];ci,mi=spec[1:]
        instance=ci if class_arg else mi
        if (list(spec)!=row['methodSpec'] or (mi if class_arg else ci)!=-1
                or image.type_name(method.declaring_type)!=type_name
                or image.metadata.string(method.name_index)!=name):
            fail('list-context-method',[type_name,name],[spec,row])
        arguments=image.instantiations.resolve(instance).arguments
        if len(arguments)!=1:
            fail('list-context-arity','one element parameter',len(arguments))
        raw=image.pe.bytes_at_va(arguments[0].type_pointer_va,16)
        if raw[10:12]!=b'\x13\x00' or int.from_bytes(raw[:8],'little')!=start:
            fail('list-context-element-var','same owned class parameter',raw.hex())
        instances.append((instance,arguments[0].type_pointer_va))
    for slot,type_name in ((0,'System.Collections.Generic.List`1'),(4,'MemoryPack.MemoryPackFormatter`1')):
        row=payload(slot,2);raw=image.pe.bytes_at_va(selected.type_pointer(row['index']),16)
        if raw[10:12]!=b'\x15\x00':fail('list-formatter-reference','undecorated reference instantiation',raw.hex())
        definition_pointer,instance_pointer=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
        definition=image.pe.bytes_at_va(definition_pointer,16)
        if (definition[10:12]!=b'\x12\x00'
                or image.type_name(int.from_bytes(definition[:8],'little'))!=type_name):
            fail('list-formatter-definition',type_name,definition.hex())
        instance=image.instantiations.resolve_pointer(instance_pointer)
        if len(instance.arguments)!=1 or (instance.index,instance.arguments[0].type_pointer_va) not in instances or len(set(instances))!=1:
            fail('list-element-context-join','same exact instantiation and element pointer',instances)
    return {'elementParameterOrdinal':0,'authenticatedRelativeSlots':[0,2,3,4,5,6],
            'runtimeProviderObserved':False,'runtimeInflationObserved':False}


def validate_buffered_reference_list(image: Any, single: dict, repeated: dict,
                                    offsets: dict, *, fail: Callable) -> dict:
    """Own header, one complete loop body, its actual repetition and return.

    The repeated packet witnesses the same block and back edge. The block's
    increment/reset/saved-count comparison prove the control invariant under
    the stated normal-child/spare-capacity conditions; source children remain
    delegated and their bytes are never inferred from runtime array stride.
    """
    for proof in (single,repeated):
        validate_program(image,proof,fail=fail,extra_opcodes={'482BC8':'sub rcx, rax'})
    pointer,remaining,advanced,consumed,total = (offsets[k] for k in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    if any(type(n)is not int or not 0<=n<128 for n in offsets.values()):
        fail('list-reader-offsets','bounded unboxed Reader fields',offsets)
    prefix=['48895C2420','55','56','57','4154','4156','4883EC30','4533E4','498BE9',
        f'837A{remaining:02X}04','498BF0','4C8BF2','4C89642420',None,
        f'498B46{pointer:02X}','486338','897C2468',f'418B5E{remaining:02X}','83EB04',None,
        f'498346{pointer:02X}04',f'418346{advanced:02X}04',f'418346{consumed:02X}04',
        f'41895E{remaining:02X}',f'496346{consumed:02X}',f'498B4E{total:02X}','482BC8','483BCF',None,
        '83FFFF','0F95C0','84C0',None,'4C897C2470','4C896C2460',None,
        '488B4520','4C3926',None,'488B90C0000000','488B1E','488B4210','4C396020',None,
        '488B4520','488BCB','488B90C0000000','488B5210',None,None,
        None,'4439A1E0000000',None,'488B4520','488B88C0000000','488B4918',None,
        '4C8BE8','458BFC','85FF',None]
    loop=['4C89642420','4D85ED',None,'498B4D00',None,'498B4500','4C8D442420','498BD6',
        '498BCD','4C8B8898010000','FF9090010000','488B1E','4C8B642420','4885DB',None,
        '488B4520','488B88C0000000','488B4130','4883782000',None,'488B4520','48635318',
        '488B88C0000000','488B7930','FF431C','488B4B10','4885C9',None,'3B5118',None,
        '8D4201','894318','3B5118',None,None,'4C8964D120',None,
        '41FFC7','41BC00000000','443B7C2468',None]
    suffix=['4C8B6C2460','4C8B7C2470','488B5C2478','4883C430','415E','415C','5F','5E','5D','C3']
    if len(prefix)!=61 or len(loop)!=41 or len(suffix)!=10:
        raise AssertionError('list profile ownership')
    program=single['program']
    if len(program)!=len(prefix+loop+suffix):fail('list-complete-profile',112,len(program))
    for n,(row,wanted) in enumerate(zip(program,prefix+loop+suffix,strict=True)):
        if wanted is not None and row[1]!=wanted:
            fail('list-owned-transfer-or-cursor',{'position':n,'bytes':wanted},row)
    if repeated['program']!=program[:61]+program[61:102]*2+program[102:]:
        fail('list-exact-loop-repetition','identical complete block repeated with actual back edge',repeated['program'])
    for n,opcode,take in ((13,b'\x7d',True),(19,b'\x79',True),(28,b'\x0f\x8c',False),
            (32,b'\x0f\x84',False),(38,b'\x74',False),(43,b'\x75',True),(52,b'\x75',True),
            (60,b'\x0f\x8e',False),(63,b'\x0f\x84',False),(75,b'\x0f\x84',False),
            (80,b'\x75',True),(88,b'\x0f\x84',False),(90,b'\x72',True),
            (94,b'\x0f\x83',False),(97,b'\x74',True)):
        at,raw_hex=program[n];raw=bytes.fromhex(raw_hex)
        if raw[:len(opcode)]!=opcode or program[n+1][0]!=(_target(at,raw) if take else at+len(raw)):
            fail('list-selected-guard',{'position':n,'taken':take},[at,raw_hex])
    branch_at,branch_hex=program[101];branch=bytes.fromhex(branch_hex)
    if (branch[:2]!=b'\x0f\x8c' or _target(branch_at,branch)!=program[61][0]
            or program[102][0]!=branch_at+len(branch)):
        fail('list-loop-count-edge','signed saved-count comparison repeats same child block',program[100:103])
    call_targets=[]
    for n in (48,56,65):
        at,raw_hex=program[n];raw=bytes.fromhex(raw_hex)
        if len(raw)!=5 or raw[0]!=0xe8:fail('list-relative-helper-call','actual direct helper',program[n])
        call_targets.append(_target(at,raw))
    return {'headerWireBytes':4,'signedCountBits':32,'headerReaderCounterStores':4,
        'savedCountEntryOffset':16,'elementOutputFrameOffset':32,'elementOutputInitiallyNull':True,
        'elementFormatterSlot':5,'runtimeReferenceBytes':8,'elementWireBytes':None,
        'readerRegister':'r14','formatterRegister':'r13','childOutputRegister':'r8',
        'existingListContextCallRva':call_targets[0],'elementContextCallRva':call_targets[1],
        'listStorageOffsets':{'count':24,'version':28,'items':16,'arrayLength':24,'arrayData':32},
        'classPrepareHelperRva':call_targets[2],'loopInstructionCount':41,
        'loopBackEdgeRva':branch_at,'positiveListAdmitted':False}
