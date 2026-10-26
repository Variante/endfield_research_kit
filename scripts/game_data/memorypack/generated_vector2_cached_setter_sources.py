"""Own by-value Vector2 spill/getter/two-Single store source.

This finite setter preserves the incoming RDX eight bytes across its own
coherent getter. The two raw MOVSS lanes and full frame are proved separately
from the Reader's wire source. It supplies no Int64 alias or child grammar.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='UnityEngine.Vector2'
LABEL='generatedVector2CachedSetter'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,*,getter,field):
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    need('literal-owned-getter-field',type(getter)is int and getter>0 and type(field)is int and field>=16)
    g=BytesPath(regions,entry);g.take('4883ec28','4889542448','33d2');g.call(getter);g.take('4885c0')
    exit=_nonnull(g);null=exit['nullTargetVa'];normal=exit['normalTargetVa']
    g.take('f30f10442448','f30f104c244c',_displacement('f30f1140',field),_displacement('f30f1148',field+4),'4883c428','c3')
    return dict(selectedBytes=g.seen,typeName=TYPE,storedBytes=8,fieldOffset=field,
        incomingValueRegister='rdx',sourceLocal=dict(displacement=72,bytes=8,entryRelativeOffset=32),
        sourceSlices=[[0,4],[4,4]],wholeRawBitsStoredUnchanged=True,fullValueStoredUnchanged=True,
        normalFrameAndReturn=True,entryRspRestored=True,noIntegerNonvolatilesWritten=True,
        getterTarget=getter,ownedNullExit=dict(instructionVa=null,normalEntryVa=normal,
            bytes=bytes(g.bytes[null+i]for i in range(6)).hex().upper()),childGrammarAdmitted=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar,pointer_param as pointer
    _publication_gate(image,pins);ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-Vector2-parameter',member.declared_type==TYPE and ctx.is_value_type(TYPE)
        and not ctx.is_value_type(wrapper.wrapped_type)and method.generic_container_index<0)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],LABEL+'.setter')
    md=image.metadata;td=ctx.index.types[TYPE];fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
    need('own-named-two-Single-layout',td.generic_container_index<0 and actual==[('x','float',16),('y','float',20)])
    for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,LABEL+'.lane')
    need('own-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-managed-parameter-size',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(24,8))
    parameter,=md.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    getter=pointer.methods(image,wrapper)['get___instance'];get=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=image.pe.image_base+barrier,pins=pins)
    body=members._body(image,image.method_pointer_va(method),pins=pins);parsed=program(body['regions'],body['pointer'],getter=image.method_pointer_va(getter),field=offset)
    _publication_gate(image,pins)
    return dict(method=[method.index,wrapper.name,md.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=8,
        nominalValueLayout=dict(typeName=TYPE,typeDefinition=td.index,fields=actual,managedBytes=8,referenceLaneOffsets=[],wireReadAdmitted=False),
        sourceFamily=body['family'],codeWindows=body['windows'],profile='cached-getter-setter',program=parsed,getter=get,
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)
