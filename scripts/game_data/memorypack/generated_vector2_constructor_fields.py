"""Named Vector2 Single subfields in two selected Original constructors.

A raw DWORD default can lie inside an actual value field. Its ownership comes
from that field's exact ordinary Vector2 record and the independently named
x/y Single layout, never from its width or neighboring offsets. This proves
storage ownership only; constructor bytes, default bits, factory transfers,
serialized framing and caller frames are independently checked.
"""

LABEL='generatedVector2ConstructorFields'
TYPE='UnityEngine.Vector2'
TYPES=('Beyond.Gameplay.View.Animation.CameraPropertyCondition',
       'Beyond.Gameplay.View.Animation.LODScreenSizeCondition')


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def component_fields(original,layout,parents):
    """Pure ownership joins over fresh selected native metadata facts."""
    need('explicit-current-Original',original in TYPES)
    definition=layout.get('typeDefinition')
    need('own-ordinary-Vector2-value',layout.get('typeName')==TYPE and type(definition)is int
         and definition>=0 and layout.get('parentType')=='System.ValueType'
         and layout.get('genericContainerIndex')==-1
         and layout.get('boxedBytes')==24 and layout.get('nativeBytes')==8)
    axes=layout.get('fields',[])
    need('complete-current-x-y-Single-fields',isinstance(axes,list)and len(axes)==2
         and[(f.get('owner'),f.get('name'),f.get('typeName'),f.get('offset'))for f in axes]==
         [(TYPE,'x','float',16),(TYPE,'y','float',20)])
    for field in axes:
        raw=bytes.fromhex(field.get('rawHex',''))
        need('ordinary-owned-Single-field-record',len(raw)==16 and raw[10:12]==bytes((12,128)))
    need('bounded-owned-Vector2-parent-fields',isinstance(parents,list)and 1<=len(parents)<=16)
    occupied=set();result=[];names=set()
    for field in parents:
        raw=bytes.fromhex(field.get('rawHex',''));offset=field.get('offset');name=field.get('name')
        need('actual-owned-ordinary-Vector2-parent-field',field.get('owner')==original
             and field.get('typeName')==TYPE and type(name)is str and name and name not in names
             and type(offset)is int and 16<=offset<2**31-8
             and len(raw)==16 and raw[10:12]==bytes((17,128))
             and not int.from_bytes(raw[8:10],'little')&16
             and int.from_bytes(raw[:8],'little')==definition)
        span=set(range(offset,offset+8))
        need('disjoint-current-value-fields',not occupied&span)
        occupied.update(span);names.add(name)
        for axis in axes:
            relative=axis['offset']-16
            result.append(dict(owner=original,name=name,typeName=TYPE,
                offset=offset+relative,bytes=4,parentField=dict(field),
                valueSubfield=dict(axis,managedOffset=relative),
                storageOwnership='named-Vector2-Single-component',scalarFieldAliasUsed=False))
    return result


def derive(image,ctx,original):
    """Fresh nominal/layout facts; caller separately proves constructor bytes."""
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('finite-selected-parent',original in TYPES)
    md=image.metadata;td=ctx.index.types[TYPE];parent=ctx.index.types[original]
    need('named-nongeneric-reference-Original',parent.generic_container_index<0
         and not ctx.is_value_type(original))
    fields=[]
    for field in md.fields_for(td):
        if ctx.field_attributes(field.type_index)&16:continue
        name=md.string(field.name_index);fact=ctx.field(TYPE+'::'+name)
        fields.append(dict(owner=TYPE,name=name,typeName=fact[1],offset=fact[2],
            rawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
    need('bounded-current-Vector2-size-record',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    layout=dict(typeName=TYPE,typeDefinition=td.index,parentType=ctx.parent(TYPE),
        genericContainerIndex=td.generic_container_index,fields=fields,
        boxedBytes=image.pe.u32_at_va(size),nativeBytes=image.pe.u32_at_va(size+4))
    parents=[]
    for field in md.fields_for(parent):
        if ctx.field_attributes(field.type_index)&16 or ctx.type_name(field.type_index)!=TYPE:continue
        name=md.string(field.name_index);fact=ctx.field(original+'::'+name)
        scalar.ordinary(image,ctx.type_pointer(field.type_index),17,LABEL+'.parentField')
        parents.append(dict(owner=original,name=name,typeName=fact[1],offset=fact[2],
            rawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
    return dict(originalType=original,nominalLayout=layout,parentFields=parents,
        componentFields=component_fields(original,layout,parents),
        fieldDefaultsInferred=False,constructorProgramAdmitted=False,wireGrammarAdmitted=False)
