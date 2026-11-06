"""Independent current Vector4 declaration; no wire width from managed size."""


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    name='UnityEngine.Vector4';md=image.metadata;td=ctx.index.types[name]
    def need(check,condition):
        if not condition:raise ValueError('unityVector4.'+check)
    need('ordinary-nongeneric-value',ctx.is_value_type(name)and not ctx.is_enum(name)
         and ctx.parent(name)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in fields]
    need('independent-xyzw-Single-layout',actual==[(axis,'float',16+4*i)for i,axis in enumerate('xyzw')])
    for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,'unityVector4.Single')
    need('bounded-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('independent-boxed-and-native-width',(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))==(32,16))
    return dict(typeName=name,typeDefinition=td.index,fields=actual,managedBytes=16,boxedBytes=32,
        referenceLaneOffsets=[],paddingByteRanges=[],wireReadAdmitted=False,managedSizeUsedForWireWidth=False)
