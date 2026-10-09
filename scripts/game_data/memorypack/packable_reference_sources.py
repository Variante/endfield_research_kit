"""Owned ReadPackable-to-ReadValue parameter and actual inline return transfer."""
from __future__ import annotations
import struct
from typing import Any,Callable
from scripts.game_data.il2cpp.context import method_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.read_value_reference_sources import _profile
from scripts.game_data.memorypack.reference_conversion_sources import _target


def validate_packable_context(image: Any,context: dict,read_value_definition: int,entries: Any,*,fail: Callable) -> dict:
    meta=image.metadata;selected=NativeReferenceContext(image);m=meta.methods[context['definition']]
    section=meta.sections['genericContainers'];at=section.offset+m.generic_container_index*16
    if (not context['isMethod'] or context['typeName']!='MemoryPack.MemoryPackReader'
            or image.type_name(m.declaring_type)!=context['typeName'] or meta.string(m.name_index)!='ReadPackable'
            or m.flags&0x10 or meta.parameters_for(m) or m.generic_container_index<0
            or not section.offset<=at<=section.offset+section.size-16):
        fail('packable-context-owner','instance Reader.ReadPackable with no explicit parameters',context)
    owner,count,is_method,start=struct.unpack_from('<iiii',meta.buf,at)
    identity=method_parameter_owner(meta.buf,start,[m.generic_container_index for m in meta.methods],source='packableReference')
    if (owner,count,is_method)!=(m.index,1,1)or identity['methodIndex']!=m.index or identity['ordinal']!=0:
        fail('packable-reciprocal-mvar','one exact owned method parameter',identity)
    def parameter(pointer):
        raw=image.pe.bytes_at_va(pointer,16)
        if raw[10:12]!=b'\x1e\x00'or int.from_bytes(raw[:8],'little')!=start:
            fail('packable-parameter-identity','same undecorated owned MVAR',raw.hex())
    parameter(selected.type_pointer(m.return_type))
    if len(context['entries'])!=1:fail('packable-context-slots','one complete ReadValue slot',context['entries'])
    slot=context['entries'][0];raw=bytes.fromhex(slot['rawHex'])
    if (slot['relativeSlot']!=0 or slot['kind']!=3 or len(raw)!=16 or int.from_bytes(raw[:4],'little')!=3
            or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=slot['index']
            or not 0<=slot['index']<len(entries.specs)):
        fail('packable-context-payload','same complete owned slot-zero MethodSpec payload',slot)
    spec=entries.specs[slot['index']]
    if list(spec)!=slot['methodSpec']or spec[:2]!=(read_value_definition,-1):
        fail('packable-read-value-join','same independently proved ReadValue definition',spec)
    arguments=image.instantiations.resolve(spec[2]).arguments
    if len(arguments)!=1:fail('packable-nested-arity',1,len(arguments))
    parameter(arguments[0].type_pointer_va)
    return {'packableDefinition':m.index,'nestedReadValueDefinition':read_value_definition,
        'ownedMethodParameterOrdinal':0,'runtimeInflationObserved':False}


PACKABLE=[
 '48895C2408','55','56','57','4154','4155','4156','4157','4883EC70','488BDA','4C8BF9','48837A3800',None,
 '488B4338','488B18','48837B3800',None,'48C744242000000000',None,'83B9E000000000',None,
 '488B4338','488B30','48837E3800',None,'488B5E38','488B1B',None,'83B9E000000000',None,
 '4885DB',None,'83B9E000000000',None,'B201','488BCB',None,'4C8D6820',None,'488B8B80000000',None,'90',
 '488B4340','49C7C0FFFFFFFF','4C898424C8000000','483B4338',None,'4533C9','4C898C24B8000000',
 '488B6B48','48FFCD','498BCD',None,'488BF8','4C898424C0000000','4C8B7368','448B6350','4823FD','488D0C7F','453B24CE',None,
 '48837B3800',None,'488D047F','41833CC600',None,'498B54C608','498BCD',None,'85C0',None,'4883FFFF',None,
 '488D0C7F','498D14CE','488B4348','488D0C40','488B4368','488D0CC8','483BD1',None,
 '488B4A10','488B4370','488B2CC8','488B8B80000000',None,'90',None,'83B9E000000000',None,None,None,None,'83B9E000000000',None,
 '488BCD',None,'488BD8','488B4638','488B4008','F6803801000001',None,'4885DB',None,'488BD0','488B0B',None,'84C0',None,
 'B905000000','4C8D4C2420','4D8BC7','488BD3',None,'488B442420','488B9C24B0000000','4883C470','415F','415E','415D','415C','5F','5E','5D','C3']


def validate_packable_transfer(image: Any,proof: dict,calls: dict,*,fail: Callable) -> dict:
    branches={n:('0F84',False)for n in(12,16,20,24,29,31,33,46,72,80,89,91,94,101,103,108)}
    branches.update({60:('75',True),62:('0F87',False),65:('0F85',False),70:('0F85',False)})
    _profile(image,proof,PACKABLE,branches,
        {36:'typeKey',52:'cacheHash',68:'cacheCompare',96:'formatterResult',106:'formatterClassPredicate',113:'formatterDispatch'},
        {18:'488B0D',27:'488B0D',38:'488B1D',87:'488B0D',90:'803D',92:'488B0D'},(),(40,85),calls,fail=fail)
    return {'entryRva':proof['program'][0][0],'readerRegister':'rcx','methodInfoRegister':'rdx',
        'savedReaderRegister':'r15','readValueContextSlot':0,'providerMethodInfoRegister':'rsi',
        'localOutputFromEntryRsp':-136,'zeroInitializedOutputBits':64,'formatterSlot':5,'returnRegister':'rax',
        'sameReaderAndLocalThroughCompleteReturn':True,'directReaderWrites':0,
        'globalIndirectEffectsProved':False,'runtimeProviderSelectionObserved':False}


def validate_root_list_field_transfer(image: Any,proof: dict,context: dict,call_rva: int,field_offset: int,*,fail: Callable) -> dict:
    """Local source argument/result join; caller Reader/wrapper state is explicit."""
    rows=proof['program'];image.check_windows([proof['window']],label='rootListFieldTransfer')
    image.check_instruction_windows(rows,label='rootListFieldTransfer')
    expected=[context['instructionHex'],'488BCF','488B1E',None,'4885DB',None,'488B4B10','4885C9',None,
        '488981'+field_offset.to_bytes(4,'little').hex().upper()]
    if len(rows)!=10 or rows[0][0]!=context['instructionRva']:
        fail('root-list-local-program','same ten-instruction context/call/result field join',rows)
    for n,(at,h)in enumerate(rows):
        raw=bytes.fromhex(h);decoded=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
        if len(decoded)!=1 or 'db 'in decoded[0]['text']or expected[n]is not None and h!=expected[n]:
            fail('root-list-owned-argument-result',{'position':n,'bytes':expected[n]},rows[n])
        if n==3:
            if len(raw)!=5 or raw[0]!=0xe8 or _target(at,raw)!=call_rva:
                fail('root-list-actual-helper',call_rva,rows[n])
        if n in(5,8)and(len(raw)!=6 or raw[:2]!=b'\x0f\x84'):
            fail('root-list-nonnull-guards','untaken exact wrapper/original JE guards',rows[n])
        if n<len(rows)-1 and rows[n+1][0]!=at+len(raw):
            fail('root-list-unaltered-return-successor','fallthrough to same full-width RAX store',rows[n:n+2])
    return {'callerReaderRegister':'rdi','savedWrapperRegister':'rbx','wrapperByrefRegister':'rsi',
        'wrapperOriginalObservedOffset':16,'originalListDestinationOffset':field_offset,'storedReturnBits':64,
        'sameReadPackableReturnStored':True,'completeRootEntryProvenance':False,
        'condition':'caller Reader and wrapper already have compatible live values; helper obeys Win64 nonvolatile ABI and returns normally; wrapper/original remain nonnull'}
