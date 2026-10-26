"""Actual action-owned damage lists and independently complete elements.

The action's closed ReadPackable request and target select a fresh bounded
list source. DamageUnit, CostData and DamageProcessor keep their distinct
ordinary reference owners; list stride supplies no element wire grammar.
The enclosing action caller and runtime callback selection remain separate.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPES={
    'Beyond.Gameplay.Core.DamageAction+DamageUnit':('skill-action-damage-unit-list','skill-damage-unit',None),
    'Beyond.Gameplay.Core.CastData+CostData':('damage-cost-data-list','skill-root-cost-data','costDataList'),
    'Beyond.Gameplay.Core.DamageProcessorBase':('damage-processor-list','damage-processor-union','damageProcessors'),
}


def _derive_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    """Caller freshly derives the selected element on this same image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list
    _publication_gate(image,pins)
    args=typed_request.get('methodArguments',[])
    choices=[name for name in TYPES if args==['System.Collections.Generic.List`1<'+name+'>']]
    need('finite-action-damage-list',1,len(choices));typename,=choices
    name,element,field=TYPES[typename];need('same-action-damage-child-inputs',pins,child['nativeInputs'])
    listing=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=typename,count_limit=count_limit)
    need('same-actual-action-damage-list-request',typed_request,listing['witnessComponent']['typedRequest'])
    need('same-actual-action-damage-list-target',call_target-image.pe.image_base,listing['witnessComponent']['callTargetRva'])
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    reader=ec.clone_facts(image,pins)['ReadValue'];element_cap=child['capabilities'][element]
    need('same-action-list-element-reader-definition',reader['equivalentMethod'][0],element_cap['referenceReaderMethodDefinition'])
    need('same-action-list-element-reader-target',reader['targetRva'],element_cap['referenceReaderTargetRva'])
    need('same-action-list-callback-reader-definition',element_cap['referenceReaderMethodDefinition'],
        listing['witnessComponent']['referenceSource']['valueContext']['readerMethodDefinition'])
    if field is None:
        cap=compose_reference_list(listing,child,pins,element_type=typename,element_capability=element,label='action-DamageUnit-list')
    else:
        from scripts.game_data.memorypack import skill_damage_list_components as lists
        listing=dict(listing,referenceReaderTargetRva=reader['targetRva'])
        cap=lists.bind_list(pins,dict(fieldName=field,typeName=args[0],typedRequest=typed_request,
            sourceTargetRva=call_target-image.pe.image_base),listing,child['capabilities'][element],capability=element)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-damage-list-sources.v1',
        status='validated-conditional-action-damage-list',nativeInputs=pins,
        capabilities={name:cap,element:child['capabilities'][element]},requiredExternalCapabilities=[element],
        proof=dict(collection=listing,child=child),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Actual closed damage list source and bounded fresh/reused-empty count induction, complete nominal ordinary element source.',
            conditional=__doc__+' Initialized compatible contexts/callbacks, normal helpers, fresh lists or reused-empty lists with spare capacity and disjoint buffered storage.',
            structuralOnly='Stored authored damage collection.',unresolved=['enclosing action caller/union','runtime selection/evaluation','whole owner/EOF']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    args=typed_request.get('methodArguments',[])
    if args==['System.Collections.Generic.List`1<Beyond.Gameplay.Core.CastData+CostData>']:
        from scripts.game_data.memorypack.skill_root_cast_components import derive as child_source
        child=child_source(image,pins)
    elif args==['System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageProcessorBase>']:
        from scripts.game_data.memorypack.skill_damage_union_components import derive as child_source
        proof=child_source(image,pins)
        need('complete-action-processor-union',[],proof['pendingJoins'])
        child=dict(nativeInputs=pins,capabilities={'damage-processor-union':proof['families']['DamageProcessorBase']},proof=proof)
    else:
        need('finite-public-action-damage-list',['System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageAction+DamageUnit>'],args)
        from scripts.game_data.memorypack.skill_damage_components import derive as child_source
        child=child_source(image,pins)
    return _derive_on_child(image,pins,child,typed_request=typed_request,
        call_target=call_target,count_limit=count_limit)
