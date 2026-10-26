"""Fresh finite ExtraData dependency graph on the caller's selected image.

This orchestration reads no generated evidence reports. Each record, actual
typed array/list/dictionary call, canonical value child and union transport is
derived on the same supplied image before their independent binders compose.
"""


def need(check,condition):
    if not condition:raise ValueError('animationExtraGraph.'+check)


def derive(image,pins,*,pooled_capability):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack import animation_extra_record_components as records
    from scripts.game_data.memorypack import animation_extra_array_components as arrays
    from scripts.game_data.memorypack import animation_extra_reference_lists as lists
    from scripts.game_data.memorypack import animation_extra_int_array_components as integers
    from scripts.game_data.memorypack import animation_extra_dictionary_components as dictionaries
    from scripts.game_data.memorypack import animation_enemy_hurt_enum_lists as enums
    from scripts.game_data.memorypack import animation_idle_condition_sources as idle_source,animation_idle_condition_components as idle
    from scripts.game_data.memorypack import animation_extra_union_sources as union_source,animation_extra_union_components as union
    from scripts.game_data.memorypack import animation_extra_value32_components as values32
    from scripts.game_data.memorypack import shader_property_value_components as shader,animation_renderer_value_components as renderer
    from scripts.game_data.memorypack import animation_enemy_shake_value_components as shake
    from scripts.game_data.memorypack import beyond_curve_value_components as curves,sk_morph_value_components as morph
    _publication_gate(image,pins);base=image.pe.image_base
    need('current-pool-capability',pooled_capability.get('wholeGrammarAdmitted')is True
        and pooled_capability.get('encoding')=='int32-pool-index'and pooled_capability.get('wireBytes')==4
        and pooled_capability.get('emptyIndex')==-1 and pooled_capability.get('nullIndex')==-2)
    names=list(records.PLANS);wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in names}
    need('all-finite-current-record-wrappers',set(wrappers)==set(names))
    result=derive_many(image,pins,[wrappers[name].name for name in names]);sources={}
    for name,row in zip(names,result['owners'],strict=True):
        need('complete-record-source:'+name,row.get('status')=='complete-reader-source-proved')
        need('same-finite-source-owner',row['proof']['wrappedType']==name);sources[name]=row['proof']
    completed={};active=set();elements={};dictionary_cache={};idle_union=None;enemy_enums=None

    def usage(read):
        return derive_typed_usage_context(image,read['context']['instructionRva'],label='animationExtraGraph.actual')

    def element(name):
        if name not in elements:
            if name in values32.PLANS:elements[name]=values32.derive(image,pins,type_name=name)
            elif name==renderer.source.TYPE:elements[name]=renderer.derive(image,pins)
            elif name==shader.source.TYPE:elements[name]=shader.derive(image,pins)
            elif name==shake.TYPE:elements[name]=shake.derive(image,pins)
            else:raise ValueError('animationExtraGraph.unowned-value-element:'+name)
        return elements[name]

    def idle_conditions():
        nonlocal idle_union
        if idle_union is None:
            transport=idle_source.derive_transport(image,pins)
            idle_union=idle.compose(transport,[record(name)for name in idle_source.TYPES])
            idle.validate_component(idle_union,pins)
        return idle_union

    def enemy_lists():
        nonlocal enemy_enums
        if enemy_enums is None:
            full=sources[enums.PARENT];requests=[]
            for index in enums.FIELDS.values():
                read=full['orderedSourceReads'][index]
                requests.append(dict(fieldName=read['fieldName'],typeName=read['declaredType'],typedRequest=usage(read),
                    sourceTargetRva=read['sourceTargetRva'],instruction=read['instruction']))
            enemy_enums=enums.derive(image,pins,requests=requests)
        return enemy_enums

    def dictionary(typ,read):
        if typ not in dictionary_cache:
            value_type=dictionaries.source.TYPES[typ][1]
            children={}if value_type=='string'else{value_type:record(value_type)if value_type in records.PLANS else element(value_type)}
            result=dictionaries._derive_on_children(image,pins,
                requests={typ:dict(typedRequest=usage(read),sourceTarget=base+read['sourceTargetRva'])},
                children=children,pooled_capability=pooled_capability)
            selected,=result['owners'];dictionaries.validate_component(selected,pins);dictionary_cache[typ]=selected
        return dictionary_cache[typ]

    def record(name):
        if name in completed:return completed[name]
        need('acyclic-finite-record-graph',name in sources and name not in active);active.add(name)
        full=sources[name];children={}
        for read in full['orderedSourceReads']:
            index=read['memberIndex'];typ=read['declaredType']
            target=base+read['sourceTargetRva']if type(read.get('sourceTargetRva'))is int else None
            if typ in records.VALUES:
                builder=curves if typ=='Beyond.FAnimationCurve'else morph
                children[index]=builder.derive(image,pins,typed_request=usage(read),source_target=target)
            elif typ in records.PLANS:children[index]=record(typ)
            elif typ in dictionaries.CAPABILITIES:children[index]=dictionary(typ,read)
            elif typ=='int[]':children[index]=integers.derive(image,pins,typed_request=usage(read),call_target=target,source_instruction=read['instruction'])
            elif typ in {name+'[]'for name in arrays.TYPES}:
                item=typ[:-2];children[index]=arrays.compose(full['sourceScope']['arraySources'][str(index)],element(item),pins)
            elif typ==enums.LIST:children[index]=enemy_lists()
            elif typ in{lists.list_type(t)for t in lists.TYPES}:
                item=typ[len('System.Collections.Generic.List`1<'):-1]
                child=None if item=='string'else idle_conditions()if item==idle_source.TYPE else record(item)
                children[index]=lists.derive_member(image,pins,parent_source=full,member_index=index,element_component=child)
        component=records.derive_selected(image,pins,source=full,children=children)
        active.remove(name);completed[name]=component;return component

    transport=union_source.derive_transport(image,pins)
    component=union.compose(transport,[record(name)for name in union.TYPES]);union.validate_component(component,pins)
    _publication_gate(image,pins);return component
