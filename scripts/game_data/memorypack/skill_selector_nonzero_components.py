"""Finite selector children compiled only from complete current source programs.

The finite domain contains owned primitive, pooled-string, named four-byte
value and independently proved ordinary reference sources. A complete caller
with an unsupported nested child stays pending.
No metadata name, managed width or successful outer cursor supplies that child.
Union/base-adapter/interface conversion and enclosing owner remain separate.
"""
from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program

LABEL='skillSelectorNonzeroComponents'
from scripts.game_data.memorypack.generated_record_components import ATOMS,VALUE4,compile_member_program
HITBOX='Beyond.Gameplay.Core.Selector+HitBoxFinder+ShapeData'
HITBOX_LIST='skill-selector-hitbox-shape-list'
COLLECTIONS={'System.Collections.Generic.List`1<'+HITBOX+'>':(HITBOX_LIST,'root-collection',HITBOX_LIST)}
REFERENCES={
    'Beyond.Blackboard+BlackboardDouble':('skill-blackboard-double','blackboard-double','scalar-payload'),
    'Beyond.Blackboard+BlackboardInt':('skill-blackboard-int','scalar-payload','blackboard-int'),
    'Beyond.Blackboard+BlackboardVector2':('skill-blackboard-vector2','blackboard-vector2','blackboard-vector2'),
    'Beyond.Blackboard+BlackboardVector3':('skill-blackboard-vector3','blackboard-vector3','blackboard-vector3'),
    'Beyond.Gameplay.Core.TargetSettings':('target-profile','target-profile','target-profile'),
    'Beyond.Gameplay.Core.DirectionSettings':('direction-profile','direction-profile','direction-profile'),
    'Beyond.Gameplay.Core.Selector+SelectorData':('selector-profile','selector-profile','selector-profile'),
    'Beyond.Gameplay.Core.BuffFindSettings':('skill-root-buff-find-settings','buff-find-settings','skill-root-buff-find-settings'),
    'Beyond.Gameplay.Core.BuffFilterSettings':('skill-selector-buff-filter-settings','buff-filter-settings','skill-selector-buff-filter-settings'),
    'Beyond.Gameplay.ColliderShapeData':('skill-action-collider-shape','action-geometry-profile','skill-action-collider-shape'),
}


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def collider_child(component,pins):
    """Bind the independent ordinary collider owner, never its managed size."""
    from scripts.game_data.memorypack import skill_action_geometry_sources as geometry
    name='Beyond.Gameplay.ColliderShapeData';key=geometry.RECORDS[name]['capability']
    cap=component.get('capabilities',{}).get(key,{})
    need('same-own-collider-component',component.get('schema')=='endfield.skill-action-geometry-sources.v1'
        and component.get('status')=='validated-conditional-action-geometry'and component.get('nativeInputs')==pins
        and component.get('wholeSkillDataAdmitted')is False and cap.get('typeName')==name
        and cap.get('wrapperName')==geometry.RECORDS[name]['wrapperName']and cap.get('memberCount')==len(geometry.RECORDS[name]['members'])
        and cap.get('orderedReads')==geometry.ordered_reads(name)
        and all(cap.get(key)is True for key in('nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>=0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return dict(nativeInputs=pins,capabilities={key:cap})


def compile_primitive_child(route,source,pins,*,value4,reference_children=None,typed_requests=None,managed_value_children=None,collection_children=None):
    """Pure finite selector program; fresh native derivation remains separate."""
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import TYPES,bind
    selected={}if managed_value_children is None else {r['memberIndex']:managed_value_children[r['declaredType']]
        for r in source['orderedSourceReads']if r['kind'].startswith('managed:')and r['declaredType']in managed_value_children}
    result,pending=compile_member_program(source,pins,wrapper_name=route['wrapperName'],type_name=route['wrappedType'],
        value4=value4,references=REFERENCES,reference_children=reference_children,typed_requests=typed_requests,
        typed_values=TYPES,value_children=selected,value_binder=bind,
        collections=COLLECTIONS,collection_children=collection_children)
    if pending:return None,pending
    row=dict(family=route['family'],tag=route['tag'],wrapperName=route['wrapperName'],wrappedType=route['wrappedType'],
        memberCount=result['memberCount'],sourceOwner='skill_timeline_current_sequence_native.json',
        reads=result['reads'],wrapperNullAdmitted=True)
    validate_program(row)
    return dict(program=row,requiredCapabilities=result['requiredCapabilities'],childBindings=result['childBindings']),[]


def _derive_with_dispatches(image,pins,dispatches,*,ec_component=None,buff_find_component=None,buff_filter_component=None,nested_component=None,geometry_component=None,wrapper_names=None):
    """Internal same-image composition; the public entry derives dispatches fresh."""
    from scripts.game_data.memorypack import generated_reader_sources as readers
    from scripts.game_data.memorypack import buff_gameplay_tag_native,buff_layer_mask_native,pooled_source_helper
    from scripts.game_data.memorypack import skill_blackboard_double_sources,skill_blackboard_int_sources,skill_blackboard_vector2_sources,skill_blackboard_vector3_sources
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    need('same-current-dispatch-scope',dispatches.get('status')=='validated-all-selector-dispatches'
        and dispatches.get('nativeInputs')==pins and dispatches.get('wholeSkillDataAdmitted')is False)
    inventory={w.name:w for w in image.memorypack_wrappers.values()};routes=[];abstract=[]
    for family,body in dispatches['families'].items():
        for route in body['programs']:
            wrapper=inventory[route['wrapperName']]
            if wrapper.abstract:abstract.append(dict(family=family,tag=route['tag'],wrapperName=wrapper.name))
            elif wrapper.members:routes.append(route)
    by_name={r['wrapperName']:r for r in routes};need('distinct-nonzero-wrappers',len(by_name)==len(routes))
    if wrapper_names is not None:
        need('explicit-finite-nonzero-wrapper-selection',type(wrapper_names)is list and bool(wrapper_names)
            and len(wrapper_names)==len(set(wrapper_names))and set(wrapper_names)<=set(by_name))
        by_name={name:by_name[name]for name in wrapper_names}
    components=readers.derive_many(image,pins,list(by_name))
    need('same-fresh-concrete-source-inputs',components['nativeInputs']==pins and components['wholeOwnerAdmitted']is False)
    value4={}
    for owner in(buff_gameplay_tag_native,buff_layer_mask_native):
        proof=owner.validate_on_image(image,pins);value4[proof['typeName']]=proof
    blackboard=skill_blackboard_double_sources.derive(image,pins)
    reference_children={'Beyond.Blackboard+BlackboardDouble':blackboard,
        'Beyond.Blackboard+BlackboardInt':skill_blackboard_int_sources.derive(image,pins),
        'Beyond.Blackboard+BlackboardVector2':skill_blackboard_vector2_sources.derive(image,pins),
        'Beyond.Blackboard+BlackboardVector3':skill_blackboard_vector3_sources.derive(image,pins)}
    if ec_component is None:
        from scripts.game_data.memorypack.skill_ec_components import derive
        ec_component=derive(image,pins)
    need('same-fresh-ec-reference-component',ec_component.get('status')=='validated-conditional-finite-ec-components'
        and ec_component.get('nativeInputs')==pins and ec_component.get('wholeSkillDataAdmitted')is False)
    for typename,capability in(('Beyond.Gameplay.Core.TargetSettings','target-profile'),
            ('Beyond.Gameplay.Core.DirectionSettings','direction-profile'),('Beyond.Gameplay.Core.Selector+SelectorData','selector-profile')):
        reference_children[typename]=dict(nativeInputs=pins,capabilities={capability:ec_component['capabilities'][capability]})
    if buff_find_component is None:
        from scripts.game_data.memorypack.skill_root_buff_find_components import derive
        buff_find_component=derive(image,pins)
    need('same-fresh-BuffFind-reference-component',buff_find_component.get('schema')=='endfield.skill-root-buff-find-components.v1'
        and buff_find_component.get('status')=='validated-conditional-components'and buff_find_component.get('nativeInputs')==pins)
    reference_children['Beyond.Gameplay.Core.BuffFindSettings']=buff_find_component
    if buff_filter_component is None:
        from scripts.game_data.memorypack.skill_selector_buff_filter_components import derive
        buff_filter_component=derive(image,pins,buff_find_component=buff_find_component)
    need('same-fresh-BuffFilter-reference-component',buff_filter_component.get('schema')=='endfield.skill-selector-buff-filter-components.v1'
        and buff_filter_component.get('status')=='validated-conditional-BuffFilter-components'and buff_filter_component.get('nativeInputs')==pins)
    reference_children['Beyond.Gameplay.Core.BuffFilterSettings']=buff_filter_component
    if geometry_component is None:
        from scripts.game_data.memorypack.skill_action_geometry_sources import derive as derive_geometry
        geometry_component=derive_geometry(image,pins,type_names=['Beyond.Gameplay.ColliderShapeData'])
    reference_children['Beyond.Gameplay.ColliderShapeData']=collider_child(geometry_component,pins)
    from scripts.game_data.memorypack import skill_action_nested_record_sources as nested
    from scripts.game_data.memorypack.skill_action_nested_record_lists import _derive_on_child as derive_nested_list
    if nested_component is None:nested_component=nested.derive(image,pins,type_names=[nested.LINE_END,nested.HITBOX])
    need('same-fresh-HitBox-record-component',nested_component.get('nativeInputs')==pins
        and nested_component.get('schema')=='endfield.skill-action-nested-record-sources.v1'
        and nested_component.get('status')=='validated-conditional-action-nested-records'
        and nested_component.get('wholeOwnerAdmitted')is False)
    from scripts.game_data.memorypack.skill_action_nested_record_codec import require_capability
    require_capability(nested_component['capabilities']['skill-selector-hitbox-shape'],'skill-selector-hitbox-shape')
    reference_children[HITBOX]=nested_component
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import derive_children
    managed_children=derive_children(image,pins,[o['proof']for o in components['owners']if o['status']=='complete-reader-source-proved'])
    programs=[];requirements={};pending=[];proved=[];pooled={};bindings={};managed_identities={};collection_identities={};collection_proofs={}
    seen=set()
    for component in components['owners']:
        proof=component.get('proof');name=proof['wrapperName']if proof is not None else component['wrapperName']
        need('one-own-concrete-source-result',name in by_name and name not in seen);seen.add(name)
        if component['status']!='complete-reader-source-proved':
            pending.append(dict(wrapperName=name,stage='complete-caller-source',reason=component['reason']));continue
        typed_requests={read['memberIndex']:derive_typed_usage_context(image,read['context']['instructionRva'],label=LABEL)
            for read in proof['orderedSourceReads']if(read['kind'].startswith('reference:')
            and read['declaredType']in(set(reference_children)|set(COLLECTIONS)))or(read['kind'].startswith('managed:')and read['declaredType']in managed_children)}
        selected_lists={}
        for read in proof['orderedSourceReads']:
            if read['declaredType']not in COLLECTIONS:continue
            index=read['memberIndex'];usage=typed_requests[index];key=(tuple(usage['methodSpec']),read['sourceTargetRva'])
            if key not in collection_proofs:
                listing=derive_nested_list(image,pins,nested_component,typed_request=usage,
                    call_target=image.pe.image_base+read['sourceTargetRva'])
                collection_proofs[key]=dict(listCapability=HITBOX_LIST,source=listing)
            selected_lists[index]=collection_proofs[key]['source']
        result,children=compile_primitive_child(by_name[name],proof,pins,value4=value4,
            reference_children=reference_children,typed_requests=typed_requests,managed_value_children=managed_children,
            collection_children=selected_lists)
        if children:
            pending.append(dict(wrapperName=name,stage='child-grammar',required=children));continue
        for read in proof['orderedSourceReads']:
            if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
                target=read['sourceTargetRva'];pooled[target]=pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
        programs.append(result['program']);requirements[name]=result['requiredCapabilities'];proved.append(proof)
        if result['childBindings']:bindings[name]=result['childBindings']
        for binding in result['childBindings']:
            if 'collectionIdentity'in binding:
                cap=binding['capability'];identity=binding['collectionIdentity']
                need('same-closed-selector-collection',cap not in collection_identities or collection_identities[cap]==identity)
                collection_identities[cap]=identity
            if 'managedValueCapabilityShape'in binding:
                cap=binding['capability'];shape=binding['managedValueCapabilityShape']
                need('same-managed-wire-capability-shape',cap not in managed_identities or managed_identities[cap]==shape)
                managed_identities[cap]=shape
    need('complete-nonzero-result-bijection',seen==set(by_name))
    used={name for names in requirements.values()for name in names}
    identities={operation:{key:reference_children[typename]['capabilities'][capability][key]
        for key in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
        for typename,(capability,_,operation)in REFERENCES.items()if operation in used}
    return dict(status='validated-finite-nonzero-selector-components',nativeInputs=dict(pins),programs=programs,
        requiredCapabilitiesByWrapper=requirements,
        requiredExternalCapabilityIdentities=identities,
        requiredExternalManagedValueIdentities=managed_identities,
        requiredExternalCollectionIdentities=collection_identities,
        proof=dict(concreteReaders=proved,atomicValueSources=value4,pooledSources=pooled,
            referenceChildren=reference_children,managedValueChildren=managed_children,
            collectionChildren=list(collection_proofs.values()),childBindings=bindings),
        pendingJoins=pending,abstractNestedUnions=abstract,baseAdapterConversionAdmitted=False,
        wholeSelectorUnionAdmitted=False,wholeSkillDataAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_selector_union_sources import derive_dispatches
    _publication_gate(image,pins)
    result=_derive_with_dispatches(image,pins,derive_dispatches(image,pins,include_nonzero=True))
    _publication_gate(image,pins)
    return result
