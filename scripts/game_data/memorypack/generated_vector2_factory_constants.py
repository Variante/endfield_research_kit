"""Exact native constructor DWORD stores into named Vector2 float lanes."""

TYPE='UnityEngine.Vector2'


def need(check,condition):
    if not condition:raise ValueError('generatedVector2FactoryConstant.'+check)


def constant(layout,parent_field,store):
    need('own-exact-Vector2-layout',layout.get('typeName')==TYPE and type(layout.get('typeDefinition'))is int
        and layout.get('fields')==[['x','float',16],['y','float',20]]and layout.get('managedBytes')==8
        and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[])
    need('own-named-parent-field',isinstance(parent_field,(list,tuple))and len(parent_field)==3
        and parent_field[1]==TYPE and type(parent_field[2])is int and parent_field[2]>=16)
    relative=store.get('offset',-1)-parent_field[2]
    need('one-complete-Vector2-Single-lane',type(store.get('bytes'))is int and store['bytes']==4
        and relative in(0,4)and isinstance(store.get('constantHex'),str)and len(bytes.fromhex(store['constantHex']))==4
        and store.get('requiresBooleanByteField')is not True)
    lane='x'if relative==0 else'y'
    return dict(field=list(parent_field),constantHex=store['constantHex'],bytes=4,
        nestedField=[TYPE,'float',16+relative],nestedFieldName=lane,parentValueByteOffset=relative,
        nominalValueLayout=layout,wireGrammarAdmitted=False)


def bind(image,ctx,parent_field,store):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('own-nongeneric-value',ctx.is_value_type(TYPE)and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[]
    for field in fields:
        name=md.string(field.name_index);fact=ctx.field(TYPE+'::'+name);actual.append([name,*fact[1:]])
        scalar.ordinary(image,ctx.type_pointer(field.type_index),12,'generatedVector2FactoryConstant.field')
    need('own-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-size-table-row',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(24,8))
    return constant(dict(typeName=TYPE,typeDefinition=td.index,fields=actual,managedBytes=8,
        referenceLaneOffsets=[],paddingByteRanges=[]),parent_field,store)
