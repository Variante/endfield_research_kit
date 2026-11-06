"""Exact named PlungingAttackData representation; no wire width inference."""
TYPE='Beyond.Gameplay.Core.AbilitySystemData+PlungingAttackData'
FIELDS=[('startDuration','float',16,12),('endDuration','float',20,12),
        ('enableOverridePlungingAttackDownSpeed','bool',24,2),('overridePlungingAttackDownSpeed','float',28,12)]


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    if not ctx.is_value_type(TYPE)or td.generic_container_index>=0:raise ValueError('plungingLayout.own-nongeneric-value')
    rows=[]
    for f in md.fields_for(td):
        if ctx.field_attributes(f.type_index)&16:continue
        name=md.string(f.name_index);fact=ctx.field(TYPE+'::'+name);raw=image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16)
        rows.append((name,fact[1],fact[2],raw[10]));scalar.ordinary(image,ctx.type_pointer(f.type_index),raw[10],'plungingLayout.field')
    if rows!=FIELDS:raise ValueError('plungingLayout.own-exact-fields:'+str(rows))
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    if(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))!=(32,16):raise ValueError('plungingLayout.own-size-table')
    return dict(typeName=TYPE,typeDefinition=td.index,managedBytes=16,fields=rows,
        referenceLaneOffsets=[],paddingByteRanges=[[9,3]],wireGrammarAdmitted=False)


def require_event(event,setter):
    layout=setter.get('nominalValueLayout',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    if not(event.get('kind')=='value16:'+TYPE and event.get('declaredType')==layout.get('typeName')==TYPE
        and event.get('mode')=='buffered-called-advance-raw16'and event.get('actualSourceProved')is True
        and event.get('wireBytes')==layout.get('managedBytes')==setter.get('storedBytes')==16
        and layout.get('fields')in(FIELDS,[list(f)for f in FIELDS])
        and layout.get('referenceLaneOffsets')==[]and layout.get('paddingByteRanges')==[[9,3]]
        and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition')):
        raise ValueError('plungingLayout.separate-own-source-setter-layout')
    return layout
