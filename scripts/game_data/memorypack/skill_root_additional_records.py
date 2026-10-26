"""Finite additional Skill child callers; delegated grammars stay explicit.

AttributeModifier and SwitchToBuffConfig use independently selected complete
MC/FF/new source families and exact original field stores. This owner invokes
the reusable direct-record algorithm with its own finite named declarations;
it does not admit an array/list element, BlackboardDouble, TargetSettings or
SequenceActionData from a field name. Initialized selected callbacks/contexts,
typed zeroed allocations, stable buffered storage and ordinary noninterfering
helpers/barriers remain conditional. Runtime selection, delegated child
grammars and enclosing SkillData/physical EOF remain unresolved.
"""
from scripts.game_data.memorypack import scalar_param_native as scalar

DECLARATIONS={
 'Beyond.Gameplay.AttributeModifierData+AttributeModifier':(
    ('attributeType','Beyond.GEnums.AttributeType','enum'),
    ('formulaItem','Beyond.GEnums.ModifierType','enum'),
    ('modifyAttributeType','Beyond.GEnums.ModifyAttributeType','enum'),
    ('param','Beyond.Blackboard+BlackboardDouble','reference')),
 'Beyond.Gameplay.Core.SwitchToBuffConfig':(
    ('asSkillCast','bool','bool'),
    ('buffs','System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffInput>','list'),
    ('buffSource','Beyond.Gameplay.Core.TargetSettings','reference'),
    ('condition','Beyond.Gameplay.Core.SequenceActionData','reference'),
    ('targets','Beyond.Gameplay.Core.TargetSettings','reference')),
}


def derive(image,pins,*,types=None):
    from scripts.game_data.memorypack.skill_root_record_sources import derive_direct_record
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    selected_inputs(pins);types=list(DECLARATIONS)if types is None else list(types)
    scalar.need('skillRootAdditionalRecords','finite-source-owners',True,
        bool(types)and len(types)==len(set(types))and set(types)<=set(DECLARATIONS))
    records={name:derive_direct_record(image,pins,name,DECLARATIONS[name],
        constructor_holder='rdi'if name=='Beyond.Gameplay.Core.SwitchToBuffConfig'else'rbx')for name in types}
    return dict(schema='endfield.skill-root-additional-record-sources.v1',nativeInputs=pins,
        status='proved-record-callers-requires-child-joins',records=records,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Finite named AttributeModifier/SwitchToBuffConfig source order, metadata/ABI, registered wrapper, constructor/getter, unchanged fields and complete selected returns.',
            conditional=__doc__,structuralOnly='Stored Skill configuration.',
            unresolved=['each explicit requiredChildJoins grammar','runtime selection','whole root/physical EOF']))
