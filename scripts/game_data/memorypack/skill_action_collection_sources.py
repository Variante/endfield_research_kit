"""Finite action collection children, independently of root field ownership.

Each actual current ReadPackable<List<T>> MethodSpec/E8 selects the existing
nominal count/constructor/callback/Add/induction owner and exact element grammar.
DataPair32, AssignPair40, BuffId8 and GameplayTag4 are distinct managed ABIs;
their child records have their own MC/FF wire programs, never raw stride reads.
String callbacks use signed pool-index4, distinct from reference stride8.
Fresh or reused-empty/spare-capacity lists, initialized coherent contexts and
matching normal callbacks/helpers remain conditions. No action framing, root
field join, live provider selection or enclosing EOF is admitted here.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_packable_list,need
from scripts.game_data.memorypack.skill_action_nested_record_lists import TYPES as NESTED_LISTS
from scripts.game_data.memorypack import skill_ordinary_ability_map_sources as ORDINARY_MAP
from scripts.game_data.memorypack import skill_special_aim_components as SPECIAL_AIM
from scripts.game_data.memorypack import skill_camera_transition_sources as CAMERA_TRANSITION
from scripts.game_data.memorypack import skill_raycast_record_sources as RAYCAST
from scripts.game_data.memorypack import skill_pull_attenuation_sources as PULL
from scripts.game_data.memorypack.skill_action_selector_list_sources import TYPES as SELECTOR_LISTS
from scripts.game_data.memorypack.enum_list_native_sources import ENUM_TYPES
from scripts.game_data.memorypack import skill_look_at_target_sources as LOOK_AT

NESTED_LIST_ELEMENTS={'System.Collections.Generic.List`1<'+name+'>':name for name in NESTED_LISTS}

COLLECTIONS={
    'System.Collections.Generic.List`1<string>':('skill-root-pooled-string-list','root-pooled-string-list','skill-root-pooled-string-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>':('skill-root-gameplay-tag-value-list','root-collection','skill-root-gameplay-tag-value-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffId>':('skill-root-buff-id-list','root-collection','skill-root-buff-id-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffId>':('skill-action-global-buff-id-list','root-collection','skill-action-global-buff-id-list'),
    'System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>':('skill-root-data-pair-list-positive','root-collection','skill-root-data-pair-list-positive'),
    'System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>':('skill-root-assign-pair-list','root-collection','skill-root-assign-pair-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffInput>':('skill-root-buff-input-list','root-collection','skill-root-buff-input-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.CreateBuffActionInput>':('skill-action-create-buff-input-list','root-collection','skill-action-create-buff-input-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffInput>':('skill-action-global-buff-input-list','root-collection','skill-action-global-buff-input-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.TargetSettings>':('skill-action-target-settings-list','root-collection','skill-action-target-settings-list'),
    'System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardString>':('skill-action-blackboard-string-list','root-collection','skill-action-blackboard-string-list'),
    'System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardDouble>':('skill-action-blackboard-double-list','root-collection','skill-action-blackboard-double-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Conditions.BlackboardBuffId>':('skill-action-blackboard-buff-id-list','root-collection','skill-action-blackboard-buff-id-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.SequenceActionData>':('skill-action-sequence-list','root-collection','skill-action-sequence-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.KeywordEnhanceEdit>':('skill-action-keyword-edit-list','root-collection','skill-action-keyword-edit-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageAction+DamageUnit>':('skill-action-damage-unit-list','root-collection','skill-action-damage-unit-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.CastData+CostData>':('damage-cost-data-list','damage-list','damage-cost-data-list'),
    'System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageProcessorBase>':('damage-processor-list','damage-list','damage-processor-list'),
}
COLLECTIONS.update({nominal:(NESTED_LISTS[name][0],'root-collection',NESTED_LISTS[name][0])for nominal,name in NESTED_LIST_ELEMENTS.items()})
COLLECTIONS.update({'System.Collections.Generic.List`1<'+name+'>':(spec[0],spec[2],spec[0])for name,spec in SELECTOR_LISTS.items()})
COLLECTIONS['System.Collections.Generic.List`1<'+ORDINARY_MAP.TYPE+'>']=(ORDINARY_MAP.LIST,'root-collection',ORDINARY_MAP.LIST)
COLLECTIONS['System.Collections.Generic.List`1<'+SPECIAL_AIM.TYPE+'>']=(SPECIAL_AIM.LIST,'root-collection',SPECIAL_AIM.LIST)
COLLECTIONS['System.Collections.Generic.List`1<'+CAMERA_TRANSITION.TYPE+'>']=(CAMERA_TRANSITION.LIST,'root-collection',CAMERA_TRANSITION.LIST)
COLLECTIONS['System.Collections.Generic.List`1<'+RAYCAST.ELEMENT+'>']=(RAYCAST.LIST,'root-collection',RAYCAST.LIST)
COLLECTIONS['System.Collections.Generic.List`1<'+PULL.TYPE+'>']=(PULL.LIST,'root-collection',PULL.LIST)
ENUM_LISTS={'System.Collections.Generic.List`1<'+name+'>':name for name in ENUM_TYPES}
COLLECTIONS['System.Collections.Generic.List`1<'+LOOK_AT.TYPE+'>']=(LOOK_AT.LIST,'root-collection',LOOK_AT.LIST)
COLLECTIONS.update({nominal:('skill-enum-list:'+name,'root-collection','skill-enum-list:'+name)for nominal,name in ENUM_LISTS.items()})


def _derive_with_references(image,pins,*,typed_request,call_target,reference_children=None,selector_component=None,enum_component=None):
    """Internal same-image composition; public entry derives every child itself."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    _publication_gate(image,pins);validate_typed_usage_context(image,typed_request,label='skillActionCollectionSources')
    args=typed_request.get('methodArguments',[])
    need('finite-known-action-list',True,len(args)==1 and args[0]in COLLECTIONS)
    nominal=args[0];capability,wire,_=COLLECTIONS[nominal]
    if nominal in ENUM_LISTS:
        from scripts.game_data.memorypack.enum_list_native_sources import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<string>':
        from scripts.game_data.memorypack.skill_pooled_string_list_sources import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>':
        from scripts.game_data.memorypack.skill_gameplay_tag_lists import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffId>':
        from scripts.game_data.memorypack.skill_root_buff_id_lists import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffId>':
        from scripts.game_data.memorypack.skill_global_buff_id_lists import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>':
        from scripts.game_data.memorypack.skill_root_value_lists import derive_data_pair_list_component as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>':
        from scripts.game_data.memorypack.skill_root_assign_pair_lists import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.CreateBuffActionInput>':
        from scripts.game_data.memorypack.skill_action_create_buff_input_sources import derive_list as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffInput>':
        from scripts.game_data.memorypack.skill_global_buff_input_sources import derive_list as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.TargetSettings>':
        from scripts.game_data.memorypack.skill_action_target_list_sources import derive as leaf
    elif nominal in{'System.Collections.Generic.List`1<'+name+'>'for name in SELECTOR_LISTS}:
        from scripts.game_data.memorypack.skill_action_selector_list_sources import derive as leaf
    elif nominal in('System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardString>',
            'System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardDouble>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Conditions.BlackboardBuffId>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.SequenceActionData>'):
        from scripts.game_data.memorypack.skill_action_reference_list_sources import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.KeywordEnhanceEdit>':
        from scripts.game_data.memorypack.skill_keyword_edit_list_sources import derive as leaf
    elif nominal in('System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageAction+DamageUnit>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.CastData+CostData>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageProcessorBase>'):
        from scripts.game_data.memorypack.skill_action_damage_list_sources import derive as leaf
    elif nominal in NESTED_LIST_ELEMENTS:
        from scripts.game_data.memorypack.skill_action_nested_record_lists import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<'+ORDINARY_MAP.TYPE+'>':
        leaf=ORDINARY_MAP.derive_list
    elif nominal=='System.Collections.Generic.List`1<'+CAMERA_TRANSITION.TYPE+'>':
        leaf=CAMERA_TRANSITION.derive_list
    elif nominal=='System.Collections.Generic.List`1<'+LOOK_AT.TYPE+'>':
        leaf=LOOK_AT.derive_list
    elif nominal=='System.Collections.Generic.List`1<'+SPECIAL_AIM.TYPE+'>':
        from scripts.game_data.memorypack.skill_special_aim_list_sources import derive as leaf
    elif nominal=='System.Collections.Generic.List`1<'+RAYCAST.ELEMENT+'>':
        leaf=RAYCAST.derive_list
    elif nominal=='System.Collections.Generic.List`1<'+PULL.TYPE+'>':
        from scripts.game_data.memorypack.skill_pull_attenuation_lists import derive as leaf
    else:
        from scripts.game_data.memorypack.skill_root_buff_input_components import derive_list as leaf
    target='Beyond.Gameplay.Core.TargetSettings'
    if nominal in ENUM_LISTS:
        from scripts.game_data.memorypack.enum_list_native_sources import bind_request
        from scripts.game_data.memorypack.skill_enum_list_codec import require_capability,element_capability
        enum_type=ENUM_LISTS[nominal];source=leaf(image,pins)if enum_component is None else enum_component
        parent=bind_request(image,pins,source,typed_request=typed_request,call_target=call_target,enum_type=enum_type)
        element=element_capability(enum_type);cap=source['capabilities'][capability];callback=source['capabilities'][element]
        require_capability(cap,callback,name=enum_type)
        component=dict(schema='endfield.skill-enum-list-child.v1',status='validated-conditional-enum-list-child',nativeInputs=pins,
            capabilities={capability:cap,element:callback},proof=dict(source=source,actualParentRequestBinding=parent),
            parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    elif nominal in{'System.Collections.Generic.List`1<'+name+'>'for name in SELECTOR_LISTS}and selector_component is not None:
        from scripts.game_data.memorypack.skill_action_selector_list_sources import _derive_on_selectors
        component=_derive_on_selectors(image,pins,selector_component,typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.CreateBuffActionInput>'and reference_children is not None:
        from scripts.game_data.memorypack.skill_action_create_buff_input_sources import _derive_list_on_child,TYPE
        component=_derive_list_on_child(image,pins,reference_children[TYPE],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GlobalBuffInput>'and reference_children is not None:
        from scripts.game_data.memorypack.skill_global_buff_input_sources import _derive_list_on_child,TYPE
        component=_derive_list_on_child(image,pins,reference_children[TYPE],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+target+'>'and reference_children is not None:
        from scripts.game_data.memorypack.skill_action_target_list_sources import _derive_on_target
        component=_derive_on_target(image,pins,reference_children[target],typed_request=typed_request,call_target=call_target)
    elif nominal in('System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardString>',
            'System.Collections.Generic.List`1<Beyond.Blackboard+BlackboardDouble>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Conditions.BlackboardBuffId>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.SequenceActionData>')and reference_children is not None:
        from scripts.game_data.memorypack.skill_action_reference_list_sources import _derive_on_child,TYPES
        element,=[t for t in TYPES if nominal=='System.Collections.Generic.List`1<'+t+'>']
        component=_derive_on_child(image,pins,reference_children[element],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.KeywordEnhanceEdit>'and reference_children is not None:
        from scripts.game_data.memorypack.skill_keyword_edit_list_sources import _derive_on_child,TYPE
        component=_derive_on_child(image,pins,reference_children[TYPE],typed_request=typed_request,call_target=call_target)
    elif nominal in('System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageAction+DamageUnit>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.CastData+CostData>',
            'System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageProcessorBase>')and reference_children is not None:
        from scripts.game_data.memorypack.skill_action_damage_list_sources import _derive_on_child,TYPES
        element,=[t for t in TYPES if nominal=='System.Collections.Generic.List`1<'+t+'>']
        component=_derive_on_child(image,pins,reference_children[element],typed_request=typed_request,call_target=call_target)
    elif nominal in NESTED_LIST_ELEMENTS and reference_children is not None:
        from scripts.game_data.memorypack.skill_action_nested_record_lists import _derive_on_child
        component=_derive_on_child(image,pins,reference_children[NESTED_LIST_ELEMENTS[nominal]],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+ORDINARY_MAP.TYPE+'>'and reference_children is not None:
        component=ORDINARY_MAP._derive_list_on_child(image,pins,reference_children[ORDINARY_MAP.TYPE],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+SPECIAL_AIM.TYPE+'>'and reference_children is not None:
        from scripts.game_data.memorypack.skill_special_aim_list_sources import _derive_on_union
        component=_derive_on_union(image,pins,reference_children[SPECIAL_AIM.TYPE],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+RAYCAST.ELEMENT+'>'and reference_children is not None:
        component=RAYCAST._derive_list_on_child(image,pins,reference_children[RAYCAST.ELEMENT],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+PULL.TYPE+'>'and reference_children is not None:
        from scripts.game_data.memorypack.skill_pull_attenuation_lists import _derive_on_child
        component=_derive_on_child(image,pins,reference_children[PULL.REFERENCE],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+CAMERA_TRANSITION.TYPE+'>'and reference_children is not None:
        component=CAMERA_TRANSITION._derive_list_on_child(image,pins,reference_children[CAMERA_TRANSITION.TYPE],typed_request=typed_request,call_target=call_target)
    elif nominal=='System.Collections.Generic.List`1<'+LOOK_AT.TYPE+'>'and reference_children is not None:
        component=LOOK_AT._derive_list_on_child(image,pins,reference_children[LOOK_AT.TYPE],typed_request=typed_request,call_target=call_target)
    else:component=leaf(image,pins,typed_request=typed_request,call_target=call_target)
    binding=bind_read_packable_list(pins,dict(fieldName='actual-action-list-source',typeName=nominal,
        typedRequest=typed_request,sourceTargetRva=call_target-image.pe.image_base),component,capability)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-collection-sources.v1',status='validated-conditional-action-list-child',
        nativeInputs=pins,closedListType=nominal,listCapability=capability,wireKind=wire,
        capabilities=component['capabilities'],binding=binding,proof=component,
        parentFieldAdmitted=False,wholeSkillDataAdmitted=False,evidenceBoundary=dict(
            exact='Actual closed ReadPackable list source, complete selected count/loop/return/induction and independent exact element callback/grammar joins.',
            conditional=__doc__,structuralOnly='Stored authored collection.',
            unresolved=['actual enclosing action caller/field/union','runtime provider/MethodInfo choice','nonempty reused/growth/refill paths','whole owner/EOF']))))


def derive(image,pins,*,typed_request,call_target):
    return _derive_with_references(image,pins,typed_request=typed_request,call_target=call_target)
