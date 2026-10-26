"""Fresh CharInteract action and nested-union transports, without child wire."""
import json,struct

PREFIX='Beyond.Gameplay.Core.CharInteractPerform.'
TYPE=PREFIX+'CharInteractPerformActionData'
NESTED=tuple(PREFIX+n for n in('ActorActData','CharActData','DecoActData','EffectActData','NpcActData','TmpObjectActData',
    'SubSpecialPerformEntry','SpecialSubPerformCondition'))
SCHEMA='endfield.char-interact-union-sources.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('charUnionSources.'+check+':'+str(detail)[:1400])


def norm(value):return json.loads(json.dumps(value))


def _attribute_node(image,pins,node):
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack import pointer_param as pointer,reference_adapter_sources as adapters
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.current_reference_union_sources import _lineage
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    need('fresh-complete-own-nested-transport',node.get('status')=='complete-nested-union-transport-source'
        and node.get('wrappedType')in NESTED and node.get('concreteChildGrammarAdmitted')is False and node.get('wholeOwnerAdmitted')is False)
    wrappers={w.name:w for w in image.memorypack_wrappers.values()};wrapper=wrappers[node['wrapperName']]
    need('same-current-nominal-union-wrapper',wrapper.wrapped_type==node['wrappedType']and wrapper.frames_as_union)
    row=node['slot5Method'];method=md.methods[row[0]]
    need('same-actual-slot5-instance-formatter',method.slot==5 and not method.flags&16
        and image.method_pointer_va(method)==base+row[3]and image.type_name(method.declaring_type)==row[1]
        and md.string(method.name_index)=='Deserialize')
    _vtable(image,method.declaring_type,5,method.index,'charUnion.own-slot5')
    image.check_windows(node['sourceWindows'],label='charUnion.nested-source')
    cached=[f for f in md.fields_for(md.types[wrapper.type_definition])
        if md.string(f.name_index)=='__realInstance'and not ctx.field_attributes(f.type_index)&16]
    need('one-or-no-own-typed-cache',len(cached)<=1)
    pair=norm(derive_pair(image,wrapper.wrapped_type,wrapper.name,owned_getter_family=bool(cached)))
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('same-current-formatter-canonical-pair',selected_image is image and selected_wrapper.name==wrapper.name
            and norm(selected_pair)==pair and face['formatterDeserializeMethodIndex']==method.index)
        return dict(readerTargetMode='independently-proved-inline',ownedWindows=node['sourceWindows'],
            programs=node['cases'],canonicalFF=node['canonicalFF'],completeOwnNestedTransportRequired=True)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];holder=_wrapper_holder(ctx,image,wrapper)
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
    conversion_at=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_at)
    for route in node['cases']:
        child=wrappers[route['wrapperName']];td=md.types[child.type_definition]
        at=section.offset+td.interface_offsets_start*8
        interfaces=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]))
        selected=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
        need('one-own-inherited-nominal-interface',len(selected)==1,child.name);ordinal,offset=selected[0]
        _vtable(image,child.type_definition,offset,getter.index,'charUnion.inherited-getter')
        proof=adapters.conversion(conversion['regions'],conversion_at,
            base+adapter['canonicalRoutes']['conversionPrepareRva'],image.method_pointer_va(getter),ordinal=ordinal)
        joins.append(dict(wrapperName=child.name,wrappedType=child.wrapped_type,interfaceOrdinal=ordinal,
            interfaceOffset=offset,conversion=proof,wrapperLineage=_lineage(ctx,md,child.name,wrapper.name)))
    original=ctx.index.types[wrapper.wrapped_type]
    need('own-abstract-reference-original',not ctx.is_value_type(wrapper.wrapped_type)and original.flags&128==128)
    return norm(dict(typeName=wrapper.wrapped_type,wrapperName=wrapper.name,nominalOriginal=dict(typeName=wrapper.wrapped_type,
        typeDefinition=original.index,flags=original.flags,valueType=False),source=node,pair=pair,adapter=adapter,
        getterMethod=[getter.index,wrapper.name,'GetValue',image.method_pointer_va(getter)-base],holder=holder,
        conversionWindows=conversion['windows'],conversionRegions=[[a-base,h.hex()]for a,h in conversion['regions']],
        inheritedConversions=joins,concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False))


def derive_nested_adapters(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.levelscript_condition_nested_sources import derive_many
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);by_type={w.wrapped_type:w for w in image.memorypack_wrappers.values()}
    selected=derive_many(image,pins,[by_type[n].name for n in NESTED]);outcomes=[]
    for name,node in zip(NESTED,selected['owners'],strict=True):
        try:outcomes.append(dict(typeName=name,status='complete-union-source-and-adapter',proof=_attribute_node(image,pins,node)))
        except(ValueError,KeyError,IndexError,TypeError)as error:
            outcomes.append(dict(typeName=name,status='pendingReview',reason=str(error)[:5000]))
    references=reference_reader_abi(image,pins);_publication_gate(image,pins)
    return norm(dict(schema=SCHEMA,nativeInputs=pins,nestedTransports=selected,outcomes=outcomes,
        referenceReaders=references,concreteChildGrammarAdmitted=False,wholeOwnerAdmitted=False))


def derive(image,pins):
    from scripts.game_data.memorypack.animation_union_sources import derive as top
    result=derive_nested_adapters(image,pins)
    result['top']=top(image,pins,families=('char-animation',),all_char_routes=True)
    return result
