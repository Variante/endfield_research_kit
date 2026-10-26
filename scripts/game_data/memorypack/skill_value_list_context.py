"""Exact typed parent and closed value-element ListFormatter context joins.

This component owns only the actual reference ReadPackable<List<T>> caller,
current selected closed ListFormatter<T> registration, generic VAR ownership,
capacity/empty-array contexts and formatter ABI. It grants no count path,
element size/codec, callback, store loop or enclosing record. Each value owner
must prove those programs independently against its actual source family.
Ready coherent closed contexts and normal compatible reference-provider choice
are conditional; runtime inflation/provider selection remains unobserved.
"""
import copy
import json
import struct

from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillValueListContext'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def require_value_element(raw,definition):
    """Exact undecorated non-byref value record; never a width inference."""
    need('complete-element-type-record',16,len(raw))
    need('undecorated-value-element',(b'\x11\x80',definition),
        (raw[10:12],int.from_bytes(raw[:8],'little')))


def clear_zero_program(regions,entry):
    """Selected value-list Clear prefix/return; nominal target is caller-owned."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    g=BytesPath(regions,entry)
    g.take('448b4118','ff411c','c7411800000000','4585c0');g.branch('7e',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,initialSize=0,returnedSize=0,sizeOffset=24,
        versionOffset=28,elementArrayTouched=False,normalReturn=True,fullPhysicalExtentProved=False)


def bind_list_add_abi(image,method_index):
    """Own the by-value formal VAR separately from any optimized helper entry."""
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    ctx=NativeReferenceContext(image);md=image.metadata;td=ctx.index.types['System.Collections.Generic.List`1']
    method=md.methods[method_index]
    need('named-List-Add-owner',(td.index,'Add',False,'void',1),
        (method.declaring_type,md.string(method.name_index),bool(method.flags&16),ctx.type_name(method.return_type),method.parameter_count))
    section=md.sections['genericContainers'];at=section.offset+td.generic_container_index*16
    need('owned-list-generic-container',True,td.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
    owner,count,is_method,parameter=struct.unpack_from('<iiii',md.buf,at)
    need('one-List-class-parameter',(td.index,1,0),(owner,count,is_method))
    formal,=md.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(formal.type_index),16)
    need('Add-by-value-owned-VAR',(b'\x13\x00',parameter),(raw[10:12],int.from_bytes(raw[:8],'little')))
    return dict(methodDefinition=method.index,declaringType=td.index,returnType='void',instance=True,
        formalKind=19,formalByRef=False,ownedClassParameter=parameter,managedArgumentBytes=None,
        actualHelperArgumentProgramRequired=True)


def derive(image,pins,*,typed_request,call_target,element_type):
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack import modelview_packable_sources
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
    from scripts.game_data.memorypack.pointer_param import owned
    selected_inputs(pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;entries=GenericEntries(image)
    need('explicit-element-name',True,isinstance(element_type,str)and bool(element_type))
    declared='System.Collections.Generic.List`1<'+element_type+'>'
    validate_typed_usage_context(image,typed_request,label=LABEL+'.caller')
    bind_typed_read(image,typed_request,method_name='ReadPackable',argument=declared,kind=21,reference=True)
    argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    carrier=ContextSymbols(image).type(argument.type_pointer_va)
    need('closed-list-name',declared,carrier['name']);element,=carrier['classArguments'];raw=bytes.fromhex(element['rawHex'])
    require_value_element(raw,ctx.index.types[element_type].index)
    need('actual-value-type',True,ctx.is_value_type(element_type));need('non-enum-element',False,ctx.is_enum(element_type))
    need('value-parent','System.ValueType',ctx.parent(element_type))
    core=_load('npc_runtime_native.json',pins)['readPackable']
    generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    need('actual-ReadPackable-target',base+core['entryRva'],call_target)
    reference=modelview_packable_sources.validate_components(image,pins,core,routes)
    td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    registration=entries.resolve(method.index,[element_type],[])
    need('exact-closed-element-registration',[raw.hex().upper()],
        [a['raw_type_record_hex'].upper()for a in registration['classInstantiation']['arguments']])
    source=owned(image,registration['pointer']);context=ContextSymbols(image).context(td.index)
    typed=validate_list_formatter_base_context(image,context,entries,fail=need)
    list_td=ctx.index.types['System.Collections.Generic.List`1'];list_context=ContextSymbols(image).context(list_td.index)
    capacity=validate_capacity_constructor_context(image,context,list_context,entries,fail=need)
    _vtable(image,td.index,5,method.index,LABEL)
    need('formatter-signature',(False,5,2,'void'),
        (bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
    reader_parameter,output_parameter=md.parameters_for(method)
    reader=image.pe.bytes_at_va(ctx.type_pointer(reader_parameter.type_index),16)
    need('formatter-reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (reader[10:12],int.from_bytes(reader[:8],'little')))
    slots={r['relativeSlot']:r for r in context['entries']}
    output=image.pe.bytes_at_va(ctx.type_pointer(output_parameter.type_index),16)
    owned_list=image.pe.bytes_at_va(ctx.type_pointer(slots[0]['index']),16)
    need('formatter-output-byref',(b'\x15\x20',owned_list[:8]),(output[10:12],output[:8]))
    static=[f for f in md.fields_for(list_td)if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
    need('sole-list-static-array',1,len(static));empty,=static
    empty_raw=image.pe.bytes_at_va(ctx.type_pointer(empty.type_index),16)
    need('static-empty-SZARRAY',b'\x1d\x00',empty_raw[10:12])
    formal,=next(r for r in list_context['entries']if r['relativeSlot']==0)['type']['classArguments']
    need('empty-array-same-owned-VAR',formal['typePointerVa'],int.from_bytes(empty_raw[:8],'little'))
    result=json.loads(json.dumps(dict(nativeInputs=pins,elementType=element_type,elementValueType=True,
        closedListType=declared,typedRequest=typed_request,callTargetRva=call_target-base,
        registration=registration,referenceSource=reference,closedCarrier=carrier,context=context,
        typedContext=typed,capacityContext=capacity,listContext=list_context,sourceWindows=source['windows'],
        emptyArrayTypeHex=empty_raw.hex().upper(),elementGrammarAdmitted=False,countsAdmitted=[],
        positiveCountsAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual typed reference parent helper, closed value-element list registration, owned generic method/type contexts and formatter ABI; static empty-array element ownership.',
            conditional=__doc__,unresolved=['signed count source','positive element callback/Add/store source','element grammar','runtime selection','whole owner/EOF']))))
    return result,source
