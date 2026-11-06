"""Own current Interactive collection requests and bounded source programs.

Reference slots never supply element wire widths. Each populated record still
needs its concrete grammar and Original/wrapper conversion. Value collections
are selected by exact nominal owner, separately from reference lists and enum
callbacks. No retained investigation or corpus-count observation is an input.
"""
import json

from scripts.game_data.memorypack import interactive_parent_bindings as parent

SCHEMA='endfield.interactive-collection-source.v1'
HEAD='System.Collections.Generic.List`1<'
REFERENCE_ELEMENTS=frozenset({
    'Beyond.Gameplay.ParamKeyValue',
    'Beyond.Gameplay.Core.PropertyStateData','Beyond.Gameplay.Core.BaseConditionData',
    'Beyond.Gameplay.Core.InteractivePerformPropertyData','Beyond.Gameplay.Core.CustomAudioData',
    'Beyond.Gameplay.Core.BuffInput','Beyond.Gameplay.Core.ModeData','Beyond.Gameplay.EffectActionCfg',
    'Beyond.Gameplay.Core.TableFieldCondition','Beyond.Gameplay.Core.ServerPropertyCondition',
    'Beyond.Gameplay.Core.ComboSkillCondition',
    'Beyond.Gameplay.AbilityEntityTemplateData+AbilityEntityMovementData','string',
})
DATA_PAIR='Beyond.Blackboard+DataPair'


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveCollections.'+check+':'+str(detail)[:1000])


def derive_member(image,pins,source,member_index,*,enum_source=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import reference_list_value_sources as references
    from scripts.game_data.memorypack import interactive_enum_sources as enums
    from scripts.game_data.memorypack import skill_root_value_lists as pairs
    _publication_gate(image,pins)
    need('literal-owned-member',type(member_index)is int
        and 0<=member_index<len(source.get('orderedSourceReads',[])))
    read=source['orderedSourceReads'][member_index];name=read['declaredType']
    need('closed-List-only',name.startswith(HEAD)and name.endswith('>'))
    element=name[len(HEAD):-1];transfer=parent.bind_reference_result(source,read,pins)
    request=parent.fresh_request(image,read);target=image.pe.image_base+read['sourceTargetRva']
    need('actual-ReadPackable-closed-list',tuple(request.get(k)for k in
        ('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[name]))
    if element in REFERENCE_ELEMENTS:
        ctx=NativeReferenceContext(image)
        need('own-nominal-reference-element',not ctx.is_value_type(element))
        child=references.derive_source(image,pins,typed_request=request,call_target=target,
            element_type=element,count_limit=4096)
        references.verify_source(child,pins)
        operation='reference-list';element_admitted=False
    elif element==enums.EVENT:
        if enum_source is None:enum_source=enums.derive(image,pins)
        child=dict(source=enum_source,binding=enums.bind_event_list(image,pins,read,enum_source))
        operation='nominal-enum32-list';element_admitted=True
    elif element==DATA_PAIR:
        child=pairs.derive_data_pair_list_component(image,pins,typed_request=request,
            call_target=target,count_limit=4096)
        operation='data-pair-value-list';element_admitted=True
    elif element=='int':
        from scripts.game_data.memorypack.leveldata_int_list_sources import derive
        child=derive(image,pins,typed_request=request,call_target=target,count_limit=4096)
        operation='int32-value-list';element_admitted=True
    else:raise ValueError('interactiveCollections.unproved-exact-element:'+element)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,typeName=name,elementType=element,
        operation=operation,headerBytes=4,countRange=[-1,4096],parentBinding=transfer,typedRequest=request,
        readerMethodDefinition=request['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],proof=child,
        elementGrammarAdmitted=element_admitted,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True,runtimeSelectionObserved=False)))
