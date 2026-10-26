"""Selected vector type/layout identity and authenticated unwind-owned records."""
from __future__ import annotations
import hashlib
import struct
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.il2cpp.sse_lanes import decode_sse_lanes
from scripts.game_data.memorypack import scalar_param_native as scalar


def vector_recorder(image, *, lanes=False):
    base = image.pe.image_base
    unwind = image.unwind_index
    class LaneMapper:
        def decode_one_x64(self,data,offset,start_va):
            return decode_sse_lanes(data,offset,start_va) or image.mapper.decode_one_x64(data,offset,start_va)
    mapper=LaneMapper() if lanes else image.mapper
    def record(rva, *, fragments=False):
        family = unwind.family(rva)
        windows = []
        for row in sorted(family['ranges'], key=lambda r:(r['runtimeTriple'][0]!=rva,r['runtimeTriple'][0])):
            start, end, _ = row['runtimeTriple']; data = image.pe.bytes_at_va(base+start,end-start)
            windows.append({'startRva':start,'endRva':end,'sha256':hashlib.sha256(data).hexdigest().upper()})
        window = windows[0]
        if fragments:
            end = window['endRva']
            for row in sorted(windows[1:],key=lambda r:r['startRva']):
                if row['startRva']==end:end=row['endRva']
            data = image.pe.bytes_at_va(base+rva,end-rva)
            window = {'startRva':rva,'endRva':end,'sha256':hashlib.sha256(data).hexdigest().upper()}
        data = image.pe.bytes_at_va(base+window['startRva'],window['endRva']-window['startRva'])
        rows = decode_string_source_instructions(mapper,data,base+rva)
        return {'pointerRva':rva,'window':window,'fragmentWindows':windows[1:] if fragments else [],
                'instructions':[[int(row['va'],16)-base,bytes.fromhex(row['bytes']).hex().upper()] for row in rows]}
    return record


def vector_context(image,context,dimension,*,label):
    scalar.need(label,'vectorDimension',True,type(dimension) is int and dimension in (2,3))
    name='UnityEngine.Vector'+str(dimension)
    scalar.need(label,'typedSource',['MemoryPack.MemoryPackReader','ReadUnmanaged',[],[name]],
                [context[k] for k in ('typeName','methodName','classArguments','methodArguments')])
    selected = NativeReferenceContext(image); md = image.metadata
    definition = selected.index.types[name]
    scalar.need(label,'nongenericValue',(True,-1),(selected.is_value_type(name),definition.generic_container_index))
    fields = [f for f in md.fields_for(definition) if not selected.field_attributes(f.type_index)&16]
    actual = [(md.string(f.name_index),*selected.field(name+'::'+md.string(f.name_index))[1:]) for f in fields]
    scalar.need(label,'valueFields',[(axis,'float',16+4*n) for n,axis in enumerate(('x','y','z')[:dimension])],actual)
    for field in fields:scalar.ordinary(image,selected.type_pointer(field.type_index),12,label+'.fieldAbi')
    scalar.need(label,'typeSizeIndex',True,0<=definition.index<image.registration['typeDefinitionsSizesCount'])
    sizes = image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
    scalar.need(label,'boxedSize',16+4*dimension,image.pe.u32_at_va(sizes))
    scalar.need(label,'nativeSize',4*dimension,image.pe.u32_at_va(sizes+4))
    argument = image.instantiations.resolve(context['methodSpec'][2]).arguments[0]
    scalar.ordinary(image,argument.type_pointer_va,17,label+'.closedValueAbi')
    scalar.need(label,'argumentDefinition',definition.index,int.from_bytes(image.pe.bytes_at_va(argument.type_pointer_va,8),'little'))
    method = md.methods[context['methodSpec'][0]]
    scalar.need(label,'declaredUnmanagedMethod',('MemoryPack.MemoryPackReader','ReadUnmanaged'),
                (image.type_name(method.declaring_type),md.string(method.name_index)))
    scalar.need(label,'sourceInstanceNoArguments',(0,0,[]),(method.flags&16,method.parameter_count,list(md.parameters_for(method))))
    section = md.sections['genericContainers']; at = section.offset+method.generic_container_index*16
    scalar.need(label,'genericContainerBounds',True,method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
    container = struct.unpack_from('<iiii',md.buf,at)
    scalar.need(label,'genericMethod',(method.index,1,1),container[:3])
    returned = image.pe.bytes_at_va(selected.type_pointer(method.return_type),16)
    scalar.need(label,'returnMvar',b'\x1e\x00',returned[10:12])
    scalar.need(label,'returnParameter',container[3],int.from_bytes(returned[:8],'little'))
    entry = GenericEntries(image).resolve(method.index,[],[name])
    scalar.need(label,'registeredMethodSpec',context['methodSpecIndex'],entry['methodSpecIndex'])
    return entry
