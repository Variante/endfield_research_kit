"""Finite current action children joined to their complete actual union caller.

Only freshly source-proved concrete wrappers whose entire member program is
compiled from independently owned primitives/pool reads are admitted here.
The native table selects the tag; metadata counts or historical tags never
supply grammar. Other children remain explicit pending joins. Original eager
registration is unnecessary for the union's ReadPackable<ConcreteWrapper>;
own wrapper construction/cache/getter and inherited base conversion are proved.
This component does not publish an aggregate, runtime behavior or whole Skill.
"""
import json

from scripts.game_data.memorypack.generated_record_components import compile_member_program
from scripts.game_data.memorypack.skill_action_union_sources import TYPE,WRAPPER
from scripts.game_data.memorypack.skill_action_nested_record_sources import RECORDS as NESTED_RECORDS
from scripts.game_data.memorypack import skill_ordinary_ability_map_sources as ORDINARY_MAP
from scripts.game_data.memorypack import skill_raycast_record_sources as RAYCAST
from scripts.game_data.memorypack import skill_pull_attenuation_sources as PULL

LABEL='skillActionComponents'
SCHEMA='endfield.skill-action-components.v5'
INITIAL_WRAPPERS=('Beyond.MemoryPack.Beyond_Gameplay_Core_IntResourceHpCheckAction_DataForMemoryPack',)
REFERENCES={
    'Beyond.Blackboard+BlackboardDouble':('skill-blackboard-double','blackboard-double','scalar-payload'),
    'Beyond.Blackboard+BlackboardInt':('skill-blackboard-int','scalar-payload','blackboard-int'),
    'Beyond.Blackboard+BlackboardVector2':('skill-blackboard-vector2','blackboard-vector2','blackboard-vector2'),
    'Beyond.Blackboard+BlackboardVector3':('skill-blackboard-vector3','blackboard-vector3','blackboard-vector3'),
    'Beyond.Gameplay.Core.TargetSettings':('target-profile','target-profile','target-profile'),
    'Beyond.Gameplay.Core.DirectionSettings':('direction-profile','direction-profile','direction-profile'),
    'Beyond.Gameplay.Core.Selector+SelectorData':('selector-profile','selector-profile','selector-profile'),
    'Beyond.Blackboard+BlackboardString':('skill-blackboard-string','root-record','skill-blackboard-string'),
    'Beyond.Gameplay.Core.Conditions.BlackboardBuffId':('skill-blackboard-buff-id','root-record','skill-blackboard-buff-id'),
    'Beyond.Gameplay.Core.BlackboardImpactValue':('skill-blackboard-impact-value','root-record','skill-blackboard-impact-value'),
    'Beyond.Gameplay.Core.BlackboardSuperArmorValue':('skill-blackboard-super-armor-value','root-record','skill-blackboard-super-armor-value'),
    'Beyond.Gameplay.Core.BlowOffCharacterAction+BlackboardCharBlowOffPriorityValue':('skill-blackboard-blowoff-priority','root-record','skill-blackboard-blowoff-priority'),
    'Beyond.Gameplay.Core.AnimatorParamAction':('skill-action-animator-param','root-record','skill-action-animator-param'),
    'Beyond.Gameplay.Core.SkillAlertData':('skill-action-alert-data','root-record','skill-action-alert-data'),
    'UnityEngine.AnimationCurve':('curve-profile','curve-profile','curve-profile'),
    'Beyond.Gameplay.Core.BuffFindSettings':('skill-root-buff-find-settings','buff-find-settings','skill-root-buff-find-settings'),
    'Beyond.Gameplay.Core.BuffFilterSettings':('skill-selector-buff-filter-settings','buff-filter-settings','skill-selector-buff-filter-settings'),
    'Beyond.Gameplay.Core.SequenceActionData':('SequenceActionData','sequence-profile','SequenceActionData'),
    'Beyond.Gameplay.Core.GameplayTagList':('skill-root-gameplay-tag-list','root-record','skill-root-gameplay-tag-list'),
    'Beyond.Gameplay.Core.BuffInput':('skill-root-buff-input','root-record','skill-root-buff-input'),
    'Beyond.Gameplay.EffectActionCfg':('skill-effect-action-config','effect-profile','skill-effect-action-config'),
    'Beyond.Gameplay.Core.DamageAction+DamageUnit':('skill-damage-unit','damage-unit-profile','skill-damage-unit'),
    'Beyond.Gameplay.Core.CalculationBase':('damage-calculation-union','damage-union','damage-calculation-union'),
    'Beyond.Gameplay.Core.DamageProcessorBase':('damage-processor-union','damage-union','damage-processor-union'),
    'Beyond.Gameplay.Core.CastData+CostData':('skill-root-cost-data','root-record','skill-root-cost-data'),
    'Beyond.Gameplay.Core.DamageAction+HitEnvData':('skill-hit-env-data','hit-env-profile','skill-hit-env-data'),
    'Beyond.Gameplay.Core.KeywordEnhanceEdit':('skill-keyword-enhance-edit','action-setting-profile','skill-keyword-enhance-edit'),
    'Beyond.Gameplay.Core.BuffIconDurationSourceSetting':('skill-buff-icon-duration-setting','action-setting-profile','skill-buff-icon-duration-setting'),
    'Beyond.Gameplay.Core.CreateBuffActionInput':('skill-action-create-buff-input','root-record','skill-action-create-buff-input'),
    'Beyond.Gameplay.Core.GlobalBuffInput':('skill-global-buff-input','root-record','skill-global-buff-input'),
    'Beyond.Gameplay.WeaponVFXOverrideConfig':('skill-action-weapon-vfx-override','root-record','skill-action-weapon-vfx-override'),
    'Beyond.Gameplay.ColliderShapeData':('skill-action-collider-shape','action-geometry-profile','skill-action-collider-shape'),
    'Beyond.Gameplay.Core.PhysicsCastAction+SourceForwardData':('skill-action-physics-source-forward','action-geometry-profile','skill-action-physics-source-forward'),
    'Beyond.Gameplay.Core.PhysicsCastAction+SourceToTargetData':('skill-action-physics-source-to-target','action-geometry-profile','skill-action-physics-source-to-target'),
}
REFERENCES.update({name:(spec['capability'],'action-nested-record-profile',spec['capability'])for name,spec in NESTED_RECORDS.items()})
REFERENCES[ORDINARY_MAP.TYPE]=(ORDINARY_MAP.CAPABILITY,'ordinary-ability-map-profile',ORDINARY_MAP.CAPABILITY)
from scripts.game_data.memorypack import skill_target_filter_sources as TARGET_FILTER,skill_special_aim_components as SPECIAL_AIM
REFERENCES[TARGET_FILTER.TYPE]=(TARGET_FILTER.CAPABILITY,'target-filter-profile',TARGET_FILTER.CAPABILITY)
REFERENCES[SPECIAL_AIM.TYPE]=(SPECIAL_AIM.CAPABILITY,'special-aim-profile',SPECIAL_AIM.CAPABILITY)
from scripts.game_data.memorypack import skill_camera_transition_sources as CAMERA_TRANSITION
REFERENCES[CAMERA_TRANSITION.TYPE]=(CAMERA_TRANSITION.CAPABILITY,'camera-transition-profile',CAMERA_TRANSITION.CAPABILITY)
from scripts.game_data.memorypack import skill_camera_custom_components as CAMERA_CUSTOM
REFERENCES[CAMERA_CUSTOM.TYPE]=(CAMERA_CUSTOM.CAPABILITY,'camera-custom-profile',CAMERA_CUSTOM.CAPABILITY)
from scripts.game_data.memorypack import skill_look_at_target_sources as LOOK_AT
REFERENCES[LOOK_AT.TYPE]=(LOOK_AT.CAPABILITY,'look-at-target-profile',LOOK_AT.CAPABILITY)
REFERENCES.update({name:(spec['capability'],'raycast-record-profile',spec['capability'])for name,spec in RAYCAST.RECORDS.items()})


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def child_request(image,source,read):
    """Select the actual caller context or the separately owned Query helper."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    context=read.get('context')
    if read.get('sourceContextMode')=='owned-closed-forwarder':
        from scripts.game_data.memorypack.generated_managed_forwarder_components import TYPE,require_source
        actual=source['sourceScope'].get('managedValueSources',{}).get(str(read['memberIndex']),{})
        usage=actual.get('proof',{}).get('typedRequest',{})
        need('finite-owned-internal-Query-request',read.get('declaredType')==TYPE)
        require_source(actual,read,source['nativeInputs'],usage)
        context=actual['proof']['internalContext']
    if not isinstance(context,dict)or type(context.get('instructionRva'))is not int:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        error=CensusGateError(LABEL+'.child-context',source=source.get('wrapperName','unknown')+'::Deserialize',
            expected='actual typed caller MethodInfo or separately proved own Query internal context',
            actual=dict(memberIndex=read.get('memberIndex'),fieldName=read.get('fieldName'),typeName=read.get('declaredType'),sourceContextMode=read.get('sourceContextMode')))
        error.diagnostic.update(validator=LABEL,failedGate='missing-owned-typed-context',nativeInputs=source.get('nativeInputs'),
            sourceInstruction=read.get('instruction'),sourceWindows=source.get('codeWindows',[])[:4])
        import json
        error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error
    fresh=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
    if read.get('sourceContextMode')=='owned-closed-forwarder':
        need('same-fresh-internal-Query-request',fresh==actual['proof']['typedRequest'])
    return fresh


def compile_child(route,conversion,source,pins,*,value4=None,reference_children=None,typed_requests=None,collection_children=None,
        managed_value_children=None,static_reference_children=None):
    """Pure join of independently fresh source results; no native admission."""
    from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program
    from scripts.game_data.memorypack.skill_action_collection_sources import COLLECTIONS
    name=route['wrapperName'];original=route['wrappedType'];life=source['lifecycle']
    need('same-finite-caller-child',route.get('family')=='AbilityActionData'
        and type(route.get('tag'))is int and 0<=route['tag']<=65535
        and(name,original)==(source.get('wrapperName'),source.get('wrappedType')))
    need('complete-null-output-caller',route['source'].get('outputInitiallyNull')is True
        and route['source'].get('normalReturn')is True and route['source'].get('sameReader')is True
        and route['source'].get('sameOutput')is True and route['source'].get('unchangedCompleteReference')is True
        and route['source'].get('concreteChildGrammarAdmitted')is False)
    need('exact-typed-child',route['typedArgument'].get('argumentType')==name
        and route['typedArgument'].get('concreteTypeKind')==18
        and route['typedRequest'].get('methodSpec')==route['parentTypedRequest'].get('methodSpec'))
    need('actual-inherited-base-conversion',conversion.get('wrapperName')==name
        and conversion.get('holder',{}).get('declaredType')==TYPE
        and type(conversion.get('holder',{}).get('offset'))is int and conversion['holder']['offset']==16
        and life.get('baseHolder')==[WRAPPER,TYPE,16])
    value8={str(read['memberIndex']):source['sourceScope']['primitiveSources'][str(read['memberIndex'])]
        for read in source['orderedSourceReads']if read['kind']=='value8:UnityEngine.Vector2'}
    from scripts.game_data.memorypack.corpus_gate import CensusGateError
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import TYPES as MANAGED_TYPES,bind as bind_managed
    from scripts.game_data.memorypack import skill_gait_dictionary_components as gait
    from scripts.game_data.memorypack.skill_gait_dictionary_sources import TYPE as GAIT
    managed_value_children={}if managed_value_children is None else managed_value_children
    selected_values={r['memberIndex']:managed_value_children[r['declaredType']]
        for r in source['orderedSourceReads']if r['kind'].startswith('managed:')and r['declaredType']in managed_value_children}
    try:
        compiled,pending=compile_member_program(source,pins,wrapper_name=name,type_name=original,
            value4={}if value4 is None else value4,value8={'UnityEngine.Vector2':value8}if value8 else{},
            references=REFERENCES,reference_children=reference_children,typed_requests=typed_requests,
            collections=COLLECTIONS,collection_children=collection_children,
            typed_values=MANAGED_TYPES,value_children=selected_values,value_binder=bind_managed,
            static_references={GAIT:(gait.CAPABILITY,gait.WIRE,gait.CAPABILITY)},static_reference_children=static_reference_children)
    except CensusGateError as error:
        detail=error.diagnostic
        if (detail.get('code')!='generatedInlineRecordComponents.inline-field'
                or detail.get('validator')!='generatedInlineRecordComponents'):raise
        index=detail.get('memberIndex')
        read=source['orderedSourceReads'][index]if type(index)is int and 0<=index<len(source['orderedSourceReads'])else{}
        return None,[dict(memberIndex=index,fieldName=detail.get('fieldName'),kind=read.get('kind'),
            typeName=read.get('declaredType'),reason='Independent inline source/field composition remains unproved.',diagnostic=detail)]
    if pending:return None,pending
    row=dict(family='AbilityActionData',tag=route['tag'],wrapperName=name,wrappedType=original,
        memberCount=compiled['memberCount'],sourceOwner='skill_timeline_current_sequence_native.json',
        reads=compiled['reads'],wrapperNullAdmitted=True)
    validate_program(row)
    return dict(program=row,requiredCapabilities=compiled['requiredCapabilities'],childBindings=compiled['childBindings']),[]


def _reference_components(image,pins,needed):
    """Fresh independently owned strong children; no bare nominal admission."""
    from scripts.game_data.memorypack import skill_blackboard_double_sources,skill_blackboard_int_sources
    from scripts.game_data.memorypack import skill_blackboard_vector2_sources,skill_blackboard_vector3_sources
    modules={'Beyond.Blackboard+BlackboardDouble':skill_blackboard_double_sources,
        'Beyond.Blackboard+BlackboardInt':skill_blackboard_int_sources,
        'Beyond.Blackboard+BlackboardVector2':skill_blackboard_vector2_sources,
        'Beyond.Blackboard+BlackboardVector3':skill_blackboard_vector3_sources}
    result={name:module.derive(image,pins)for name,module in modules.items()if name in needed}
    ec_names={'Beyond.Gameplay.Core.TargetSettings':'target-profile','Beyond.Gameplay.Core.DirectionSettings':'direction-profile',
        'Beyond.Gameplay.Core.Selector+SelectorData':'selector-profile'}
    if set(ec_names)&needed:
        from scripts.game_data.memorypack.skill_ec_components import derive
        ec=derive(image,pins)
        for name,cap in ec_names.items():
            if name in needed:result[name]=dict(nativeInputs=pins,capabilities={cap:ec['capabilities'][cap]})
    find='Beyond.Gameplay.Core.BuffFindSettings';filter_type='Beyond.Gameplay.Core.BuffFilterSettings'
    if needed&{find,filter_type}:
        from scripts.game_data.memorypack.skill_root_buff_find_components import derive
        component=derive(image,pins)
        if find in needed:result[find]=component
        if filter_type in needed:
            from scripts.game_data.memorypack.skill_selector_buff_filter_components import derive as derive_filter
            result[filter_type]=derive_filter(image,pins,buff_find_component=component)
    if 'Beyond.Gameplay.Core.SequenceActionData'in needed:
        from scripts.game_data.memorypack.skill_sequence_components import derive
        result['Beyond.Gameplay.Core.SequenceActionData']=derive(image,pins)
    if 'Beyond.Gameplay.Core.GameplayTagList'in needed:
        from scripts.game_data.memorypack.skill_root_gameplay_tag_list_components import derive
        result['Beyond.Gameplay.Core.GameplayTagList']=derive(image,pins)
    if 'Beyond.Gameplay.Core.BuffInput'in needed:
        from scripts.game_data.memorypack.skill_root_buff_input_components import derive
        result['Beyond.Gameplay.Core.BuffInput']=derive(image,pins)
    if 'Beyond.Blackboard+BlackboardString'in needed:
        from scripts.game_data.memorypack.skill_blackboard_string_sources import derive
        result['Beyond.Blackboard+BlackboardString']=derive(image,pins)
    if 'Beyond.Gameplay.Core.Conditions.BlackboardBuffId'in needed:
        from scripts.game_data.memorypack.skill_blackboard_buff_id_sources import derive
        result['Beyond.Gameplay.Core.Conditions.BlackboardBuffId']=derive(image,pins)
    dropdowns=needed&{'Beyond.Gameplay.Core.BlackboardImpactValue','Beyond.Gameplay.Core.BlackboardSuperArmorValue'}
    if dropdowns:
        from scripts.game_data.memorypack.skill_dropdown_blackboard_sources import derive
        component=derive(image,pins,type_names=sorted(dropdowns))
        for name in dropdowns:result[name]=component
    if 'Beyond.Gameplay.Core.BlowOffCharacterAction+BlackboardCharBlowOffPriorityValue'in needed:
        from scripts.game_data.memorypack.skill_blowoff_priority_sources import derive
        result['Beyond.Gameplay.Core.BlowOffCharacterAction+BlackboardCharBlowOffPriorityValue']=derive(image,pins)
    records=needed&{'Beyond.Gameplay.Core.AnimatorParamAction','Beyond.Gameplay.Core.SkillAlertData','Beyond.Gameplay.WeaponVFXOverrideConfig'}
    if records:
        from scripts.game_data.memorypack.skill_action_reference_components import derive
        component=derive(image,pins,type_names=sorted(records))
        for name in records:result[name]=component
    if 'UnityEngine.AnimationCurve'in needed:
        from scripts.game_data.memorypack.skill_animation_curve_sources import derive
        component=derive(image,pins)
        result['UnityEngine.AnimationCurve']=dict(nativeInputs=pins,
            capabilities={'curve-profile':component['capabilities']['skill-animation-curve']},proof=component)
    damage_names=set(REFERENCES)-{'Beyond.Gameplay.Core.CastData+CostData'}
    damage_names={name for name in damage_names if REFERENCES[name][0]in(
        'skill-effect-action-config','skill-damage-unit','damage-calculation-union','damage-processor-union')}
    damage_component=None
    if needed&damage_names:
        from scripts.game_data.memorypack.skill_damage_components import derive
        damage_component=derive(image,pins)
        for name in needed&damage_names:result[name]=damage_component
    if 'Beyond.Gameplay.Core.CastData+CostData'in needed:
        from scripts.game_data.memorypack.skill_root_cast_components import derive
        result['Beyond.Gameplay.Core.CastData+CostData']=derive(image,pins)
    if 'Beyond.Gameplay.Core.DamageAction+HitEnvData'in needed:
        from scripts.game_data.memorypack import skill_hit_env_sources
        result['Beyond.Gameplay.Core.DamageAction+HitEnvData']=(skill_hit_env_sources.derive(image,pins)if damage_component is None
            else skill_hit_env_sources._derive_on_calculation(image,pins,damage_component))
    settings=needed&{'Beyond.Gameplay.Core.KeywordEnhanceEdit','Beyond.Gameplay.Core.BuffIconDurationSourceSetting'}
    if settings:
        from scripts.game_data.memorypack.skill_action_setting_sources import derive
        component=derive(image,pins,type_names=sorted(settings))
        for name in settings:result[name]=component
    if 'Beyond.Gameplay.Core.CreateBuffActionInput'in needed:
        from scripts.game_data.memorypack.skill_action_create_buff_input_sources import derive
        result['Beyond.Gameplay.Core.CreateBuffActionInput']=derive(image,pins)
    if 'Beyond.Gameplay.Core.GlobalBuffInput'in needed:
        from scripts.game_data.memorypack.skill_global_buff_input_sources import derive
        result['Beyond.Gameplay.Core.GlobalBuffInput']=derive(image,pins)
    from scripts.game_data.memorypack import skill_action_geometry_sources
    geometry=needed&set(skill_action_geometry_sources.RECORDS)
    if geometry:
        component=skill_action_geometry_sources.derive(image,pins,type_names=sorted(geometry))
        for name in geometry:result[name]=component
    nested=needed&set(NESTED_RECORDS)
    if nested:
        from scripts.game_data.memorypack.skill_action_nested_record_sources import derive
        component=derive(image,pins,type_names=sorted(nested))
        for name in nested:result[name]=component
    if ORDINARY_MAP.TYPE in needed:result[ORDINARY_MAP.TYPE]=ORDINARY_MAP.derive(image,pins)
    raycast=needed&set(RAYCAST.RECORDS)
    if raycast:
        component=RAYCAST.derive(image,pins,type_names=sorted(raycast))
        for name in raycast:result[name]=component
    if TARGET_FILTER.TYPE in needed:result[TARGET_FILTER.TYPE]=TARGET_FILTER.derive(image,pins)
    if SPECIAL_AIM.TYPE in needed:result[SPECIAL_AIM.TYPE]=SPECIAL_AIM.derive(image,pins)
    if CAMERA_TRANSITION.TYPE in needed:result[CAMERA_TRANSITION.TYPE]=CAMERA_TRANSITION.derive(image,pins)
    if CAMERA_CUSTOM.TYPE in needed:result[CAMERA_CUSTOM.TYPE]=CAMERA_CUSTOM.derive(image,pins)
    if LOOK_AT.TYPE in needed:result[LOOK_AT.TYPE]=LOOK_AT.derive(image,pins)
    return result


def _managed_components(image,pins,complete):
    """Fresh finite wire children, separate from each caller's managed source."""
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import derive_children
    return derive_children(image,pins,complete)


def _derive_with_transport(image,pins,transport,wrapper_names,*,reference_children=None,managed_value_children=None,selector_component=None):
    """Internal same-image composition; public derive re-proves transport first."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import generated_reader_sources as readers,pooled_source_helper
    _publication_gate(image,pins)
    need('fresh-current-transport-scope',transport.get('schema')=='endfield.skill-action-union-source.v1'
        and transport.get('status')=='validated-current-action-union-transport'and transport.get('nativeInputs')==pins
        and transport.get('typeName')==TYPE and transport.get('wrapperName')==WRAPPER
        and transport.get('baseGetterSemanticsAdmitted')is True
        and transport.get('concreteChildGrammarAdmitted')is False and transport.get('wholeUnionAdmitted')is False)
    names=list(wrapper_names)
    need('bounded-distinct-explicit-wrapper-scope',0<len(names)<=512 and len(names)==len(set(names))
        and all(isinstance(name,str)and name for name in names))
    routes={r['wrapperName']:r for r in transport['programs']};conversions={r['wrapperName']:r for r in transport['derivedOriginalConversions']}
    need('exact-current-transport-bijection',len(routes)==len(transport['programs'])==len(conversions)
        and set(routes)==set(conversions)and set(names)<=set(routes))
    by_name={w.name:w for w in image.memorypack_wrappers.values()}
    need('concrete-owned-child-wrappers',all(not by_name[name].abstract for name in names))
    fresh=readers.derive_many(image,pins,names)
    need('same-selected-concrete-source',fresh['nativeInputs']==pins and fresh['wholeOwnerAdmitted']is False)
    complete=[o['proof']for o in fresh['owners']if o['status']=='complete-reader-source-proved']
    needed={r['declaredType']for proof in complete for r in proof['orderedSourceReads']
        if r['kind'].startswith('reference:')and r['declaredType']in REFERENCES}
    if any(r['declaredType']=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.TargetSettings>'
            for proof in complete for r in proof['orderedSourceReads']):needed.add('Beyond.Gameplay.Core.TargetSettings')
    if any(r['declaredType']=='System.Collections.Generic.List`1<'+PULL.TYPE+'>'
            for proof in complete for r in proof['orderedSourceReads']):needed.add(PULL.REFERENCE)
    for element in('Beyond.Blackboard+BlackboardDouble','Beyond.Blackboard+BlackboardString',
            'Beyond.Gameplay.Core.Conditions.BlackboardBuffId','Beyond.Gameplay.Core.SequenceActionData',
            'Beyond.Gameplay.Core.KeywordEnhanceEdit',
            'Beyond.Gameplay.Core.DamageAction+DamageUnit','Beyond.Gameplay.Core.DamageProcessorBase',
            'Beyond.Gameplay.Core.CastData+CostData','Beyond.Gameplay.Core.CreateBuffActionInput','Beyond.Gameplay.Core.GlobalBuffInput',
            *NESTED_RECORDS,*RAYCAST.RECORDS,ORDINARY_MAP.TYPE,SPECIAL_AIM.TYPE,CAMERA_TRANSITION.TYPE,LOOK_AT.TYPE):
        if any(r['declaredType']=='System.Collections.Generic.List`1<'+element+'>'
                for proof in complete for r in proof['orderedSourceReads']):needed.add(element)
    reference_children=_reference_components(image,pins,needed)if reference_children is None else reference_children
    need('explicit-fresh-reference-scope',set(reference_children)<=set(REFERENCES))
    from scripts.game_data.memorypack.skill_action_selector_list_sources import TYPES as SELECTOR_LISTS
    selector_lists={'System.Collections.Generic.List`1<'+name+'>'for name in SELECTOR_LISTS}
    if selector_component is None and any(read['declaredType']in selector_lists for owner in complete for read in owner['orderedSourceReads']):
        from scripts.game_data.memorypack.skill_selector_union_sources import derive as derive_selectors
        selector_component=derive_selectors(image,pins)
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import TYPES as MANAGED_TYPES
    managed_value_children=_managed_components(image,pins,complete)if managed_value_children is None else managed_value_children
    need('explicit-fresh-managed-value-scope',set(managed_value_children)<=set(MANAGED_TYPES))
    value4={};value_types={r['declaredType']for proof in complete for r in proof['orderedSourceReads']if r['kind'].startswith('value4:')}
    if value_types:
        from scripts.game_data.memorypack import buff_gameplay_tag_native,buff_layer_mask_native
        for nominal,owner in(('Beyond.Gameplay.Core.GameplayTag',buff_gameplay_tag_native),('UnityEngine.LayerMask',buff_layer_mask_native)):
            if nominal in value_types:
                atom=owner.validate_on_image(image,pins);value4[atom['typeName']]=atom
    programs=[];pending=[];sources=[];requirements={};seen=set();pooled={};bindings={};collection_proofs={};collection_identities={};managed_identities={}
    static_children=[];static_identities={};gait_callbacks=None
    from scripts.game_data.memorypack import skill_gait_dictionary_components as gait
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import skill_action_collection_sources as lists
    enum_lists=None
    if any(read['declaredType']in lists.ENUM_LISTS for proof in complete for read in proof['orderedSourceReads']):
        from scripts.game_data.memorypack.enum_list_native_sources import derive as derive_enum_lists
        enum_lists=derive_enum_lists(image,pins)
    for owner in fresh['owners']:
        proof=owner.get('proof');name=proof['wrapperName']if proof is not None else owner['wrapperName']
        need('one-result-per-selected-child',name in names and name not in seen);seen.add(name)
        if owner['status']!='complete-reader-source-proved':
            pending.append(dict(wrapperName=name,stage='concrete-source',reason=owner['reason']));continue
        typed_requests={r['memberIndex']:child_request(image,proof,r)
            for r in proof['orderedSourceReads']if(r['kind'].startswith('reference:')
            and r['declaredType']in(set(reference_children)|set(lists.COLLECTIONS)))or(r['kind'].startswith('managed:')
            and r['declaredType']in managed_value_children)or r.get('mode')=='typed-static-out-reference'}
        selected_static={}
        for read in proof['orderedSourceReads']:
            if read.get('mode')!='typed-static-out-reference':continue
            child=gait.derive(image,pins,context=read['context'],source_target=image.pe.image_base+read['sourceTargetRva'],callback_children=gait_callbacks)
            gait_callbacks=(child['proof']['single'],child['proof']['enum'])
            selected_static[read['memberIndex']]=child;static_children.append(child)
        selected_lists={}
        for read in proof['orderedSourceReads']:
            if read['declaredType']not in lists.COLLECTIONS:continue
            index=read['memberIndex'];usage=typed_requests[index]
            key=(read['declaredType'],tuple(usage['methodSpec']),read['sourceTargetRva'])
            if key not in collection_proofs:
                options=dict(reference_children=reference_children)
                if read['declaredType']in lists.ENUM_LISTS:options['enum_component']=enum_lists
                if read['declaredType']in selector_lists:options['selector_component']=selector_component
                collection_proofs[key]=lists._derive_with_references(image,pins,typed_request=usage,
                    call_target=image.pe.image_base+read['sourceTargetRva'],**options)
            selected_lists[index]=collection_proofs[key]
        compiled,children=compile_child(routes[name],conversions[name],proof,pins,value4=value4,
            reference_children=reference_children,typed_requests=typed_requests,collection_children=selected_lists,
            managed_value_children=managed_value_children,static_reference_children=selected_static)
        if children:
            pending.append(dict(wrapperName=name,stage='child-grammar',required=children));continue
        for read in proof['orderedSourceReads']:
            if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
                target=read['sourceTargetRva'];pooled[target]=pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
        programs.append(compiled['program']);requirements[name]=compiled['requiredCapabilities'];sources.append(proof)
        if compiled['childBindings']:bindings[name]=compiled['childBindings']
        for binding in compiled['childBindings']:
            if 'collectionIdentity'in binding:
                cap=binding['capability'];identity=binding['collectionIdentity']
                need('same-closed-collection-scope',cap not in collection_identities or collection_identities[cap]==identity)
                collection_identities[cap]=identity
            if 'managedValueCapabilityShape'in binding:
                cap=binding['capability'];shape=binding['managedValueCapabilityShape']
                need('same-managed-wire-capability-shape',cap not in managed_identities or managed_identities[cap]==shape)
                managed_identities[cap]=shape
            if 'staticReferenceCapabilityShape'in binding:
                cap=binding['capability'];shape=binding['staticReferenceCapabilityShape']
                need('same-static-reference-wire-capability',cap not in static_identities or static_identities[cap]==shape)
                static_identities[cap]=shape
    need('complete-selected-result-bijection',seen==set(names))
    used={cap for caps in requirements.values()for cap in caps}
    identities={operation:{key:reference_children[typename]['capabilities'][capability][key]
        for key in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
        for typename,(capability,_,operation)in REFERENCES.items()if operation in used}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-finite-current-action-components',nativeInputs=pins,
        selectedWrappers=names,programs=programs,routeRequirements=requirements,pendingRoutes=pending,
        requiredExternalCapabilities=sorted({cap for caps in requirements.values()for cap in caps}),
        requiredExternalCapabilityIdentities=identities,
        requiredExternalCollectionIdentities=collection_identities,
        requiredExternalManagedValueIdentities=managed_identities,
        requiredExternalStaticReferenceIdentities=static_identities,
        proof=dict(transport=transport,concreteReaders=sources,pooledSources=pooled,
            atomicValueSources=value4,referenceChildren=reference_children,childBindings=bindings,
            collectionChildren=list(collection_proofs.values()),managedValueChildren=managed_value_children,
            staticReferenceChildren=static_children),
        wholeUnionAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Finite selected current action table/caller/base conversion plus complete concrete new/existing/FF source/lifecycle/cache/factory/setter and compiled owned primitive or pooled-string members.',
            conditional=__doc__+' Coherent initialized current contexts and selected matching callbacks, normal compatible allocation/cache/provider/collector/Win64 effects and stable disjoint buffered storage are required.',
            structuralOnly='Stored configuration; no action execution, ordering or gameplay effect follows.',
            unresolved=['unselected routes and pending children','runtime callback/provider/inflation selection',
                'cold/refill/malformed/noncoherent paths','enclosing action lists/root/physical EOF']))))


def derive(image,pins,*,wrapper_names=INITIAL_WRAPPERS):
    from scripts.game_data.memorypack.skill_action_union_sources import derive as derive_transport
    return _derive_with_transport(image,pins,derive_transport(image,pins),wrapper_names)


def derive_all(image,pins):
    """The current finite table supplies candidates, never their wire grammar."""
    from scripts.game_data.memorypack.skill_action_union_sources import derive as derive_transport
    transport=derive_transport(image,pins);inventory={w.name:w for w in image.memorypack_wrappers.values()}
    names=[r['wrapperName']for r in transport['programs']if not inventory[r['wrapperName']].abstract]
    return _derive_with_transport(image,pins,transport,names)
