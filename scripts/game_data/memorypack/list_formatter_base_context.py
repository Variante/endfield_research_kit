"""Declared ListFormatter<T> parent/constructor context and closed RET control."""
from __future__ import annotations
import struct
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from .list_reference_sources import validate_list_element_context


def validate_list_formatter_base_context(image, context, entries, *, fail):
    element=validate_list_element_context(image,context,entries,fail=fail)
    selected=NativeReferenceContext(image);owner=image.metadata.types[context['definition']]
    slots={r['relativeSlot']:r for r in context['entries']}
    if any(n not in slots for n in (0,7,8)):
        fail('base-context-slots','List<T>, inherited ctor and parent type slots',sorted(slots))
    for n,kind in ((7,3),(8,2)):
        row=slots[n];raw=bytes.fromhex(row['rawHex'])
        if (len(raw)!=16 or row['kind']!=kind or int.from_bytes(raw[:4],'little')!=kind
                or image.pe.u32_at_va(int.from_bytes(raw[8:],'little'))!=row['index']):
            fail('base-context-payload',{'slot':n,'kind':kind},row)
    row=slots[7]
    if type(row['index']) is not int or not 0<=row['index']<len(entries.specs):
        fail('base-ctor-method-spec-range','in-range MethodSpec',row['index'])
    spec=entries.specs[row['index']]
    if list(spec)!=row['methodSpec'] or spec[1]<0 or spec[2]!=-1:
        fail('base-ctor-class-instantiation','class-only inherited constructor',spec)
    method=image.metadata.methods[spec[0]]
    if (image.type_name(method.declaring_type)!='MemoryPack.MemoryPackFormatter`1'
            or image.metadata.string(method.name_index)!='.ctor' or method.flags&0x10
            or method.parameter_count!=0 or selected.type_name(method.return_type)!='void'):
        fail('base-ctor-declaration','instance void MemoryPackFormatter ctor with no explicit parameters',spec[0])
    parent=selected.type_pointer(owner.parent_index)
    if selected.type_pointer(slots[8]['index'])!=parent:
        fail('base-parent-pointer','slot8 equals actual declared parent',owner.parent_index)
    raw=image.pe.bytes_at_va(parent,16)
    if raw[10:12]!=b'\x15\x00':
        fail('base-parent-reference-kind','undecorated generic reference type',raw.hex())
    definition_pointer,instance_pointer=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
    definition=image.pe.bytes_at_va(definition_pointer,16)
    if definition[10:12]!=b'\x12\x00' or int.from_bytes(definition[:8],'little')!=method.declaring_type:
        fail('base-parent-constructor-owner','same generic definition as inherited constructor',definition.hex())
    parent_inst=image.instantiations.resolve_pointer(instance_pointer)
    ctor_inst=image.instantiations.resolve(spec[1]);list_pointer=selected.type_pointer(slots[0]['index'])
    if (parent_inst.index!=ctor_inst.index or len(parent_inst.arguments)!=1 or len(ctor_inst.arguments)!=1
            or parent_inst.arguments[0].type_pointer_va!=list_pointer or ctor_inst.arguments[0].type_pointer_va!=list_pointer):
        fail('base-parent-list-argument','same exact List<T> argument for parent and inherited ctor',spec)
    return {'listFormatterDefinition':owner.index,'baseConstructorDefinition':method.index,
        'parentTypeIndex':owner.parent_index,'baseConstructorClassInstantiationIndex':ctor_inst.index,
        'inheritedConstructorSlot':7,'declaredParentTypeSlot':8,'elementParameterOrdinal':element['elementParameterOrdinal'],
        'parentAndConstructorShareListArgument':True,'actualRuntimeSlotArrayObserved':False,
        'coldIndirectTargetIdentityProved':False}


def validate_closed_zero_pop_return(raw):
    if raw not in (b'\xc3',b'\xc2\x00\x00'):
        raise ValueError('closedReturnEntry.zero-pop-return-program')
    return {'instructionsChecked':1,'bytesChecked':len(raw),'explicitDataStores':0,
        'stackBytesPopped':8,'additionalStackCleanupBytes':0,'flagsAndGeneralRegistersPreserved':True,
        'uniqueNamedMethodBodyProved':False,'fullPhysicalFunctionExtentProved':False,
        'actualColdTargetMatchesEntryProved':False,
        'condition':'Execution begins at this entry with a readable ordinary return stack and valid return address. Registered folded aliases do not identify the actual runtime cold target.'}
