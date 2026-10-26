"""Complete current DamageUnit composition; enclosing actions remain separate."""
import json

from scripts.game_data.memorypack.skill_damage_component_bindings import compose
from scripts.game_data.memorypack.skill_root_child_bindings import need


def _merge(target,rows):
    for name,cap in rows.items():
        if name in target:need('same-current-Damage-child:'+name,target[name],cap)
        else:target[name]=cap


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import skill_damage_unit_sources as unit,skill_damage_union_components as unions
    from scripts.game_data.memorypack import skill_effect_components as effect,skill_root_cast_components as cast
    from scripts.game_data.memorypack import skill_damage_list_components as lists,reference_list_induction_sources as induction
    from scripts.game_data.memorypack import skill_damage_tag_components as tags,buff_ec_profiles_native as ec
    _publication_gate(image,pins);parent=unit.derive_reference(image,pins)
    union=unions.derive(image,pins);need('complete-current-Damage-unions',[],union['pendingJoins'])
    effects=effect.derive(image,pins);sound=unit.derive_hit_sound(image,pins);cost=cast.derive(image,pins)
    caps={};proofs={}
    _merge(caps,effects['capabilities']);_merge(caps,sound['capabilities'])
    _merge(caps,{'damage-calculation-union':union['families']['CalculationBase'],
        'damage-processor-union':union['families']['DamageProcessorBase'],
        'skill-root-cost-data':cost['capabilities']['skill-root-cost-data']})
    double=effects['proof']['referenceChildren']['Beyond.Blackboard+BlackboardDouble']
    vector=effects['proof']['referenceChildren']['Beyond.Blackboard+BlackboardVector3']
    _merge(caps,{'scalar-payload':dict(double['capabilities']['skill-blackboard-double'],ordinaryOriginalReadValueAdmitted=True),
        'blackboard-vector3':vector['capabilities']['skill-blackboard-vector3'],
        'skill-root-attribute-modifier':union['proof']['referenceChildren'][
            'Beyond.Gameplay.AttributeModifierData+AttributeModifier']['capabilities']['skill-root-attribute-modifier'],
        'byte-payload':dict(wholeGrammarAdmitted=True,encoding='int32-pool-index',emptyIndex=-1,nullIndex=-2)})
    reader=ec.clone_facts(image,pins)['ReadValue']
    for field,(typename,element,list_cap)in lists.ELEMENTS.items():
        join,=[row for row in parent['proof']['caller']['requiredChildJoins']if row['fieldName']==field]
        listing=induction.derive(image,pins,typed_request=join['typedRequest'],
            call_target=image.pe.image_base+join['sourceTargetRva'],element_type=typename,count_limit=10000)
        listing=dict(listing,referenceReaderTargetRva=reader['targetRva'])
        caps[list_cap]=lists.bind_list(pins,join,listing,caps[element],capability=element)
        proofs[field]=listing
    tag=tags.derive(image,pins)
    _merge(caps,{'skill-root-gameplay-tag':tag['capabilities']['skill-root-gameplay-tag'],
        'damage-gameplay-tag-list':tag['capabilities']['skill-root-gameplay-tag-value-list']})
    joined=compose(parent,pins,caps);_merge(caps,joined['capabilities'])
    shared={'scalar-payload','blackboard-vector3','skill-root-cost-data','skill-root-attribute-modifier',
        'skill-root-gameplay-tag','byte-payload'}
    owned={name:cap for name,cap in caps.items()if name not in shared}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-damage-components.v1',
        status='validated-conditional-complete-DamageUnit-grammar',nativeInputs=pins,capabilities=owned,
        requiredExternalCapabilities=sorted(shared),requiredExternalCapabilityShapes={name:caps[name]for name in sorted(shared)},
        proof=dict(parent=parent,unions=union,effect=effects,hitSound=sound,costData=cost,
            referenceLists=proofs,tagList=tag,referenceReader=reader,actualChildBindings=joined['actualChildBindings']),
        wholeDamageUnitAdmitted=True,actualEnclosingParentAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Complete selected current DamageUnit34/new/existing/FF source and ordinary adapter, all actual child MethodSpecs/E8 targets, complete Calculation6/Processor11 unions and ordinary children, own Cost/Processor/Tag collection inductions and complete Effect86/Terrain array/element grammar.',
            conditional='Initialized coherent nominal contexts and matching actual canonical callbacks, compatible normal allocator/provider/cache/collector and Win64 helpers, disjoint buffered storage, fresh arrays and fresh or reused-empty sufficiently-capacitated lists. Each shared capability must match the enclosing selected operation.',
            structuralOnly='Stored authored damage configuration and sound-event text; no runtime calculation, playback or Audio/asset binding.',
            unresolved=['actual enclosing DamageAction/list source joins','runtime provider/MethodInfo selection','whole Skill/physical EOF']))))
