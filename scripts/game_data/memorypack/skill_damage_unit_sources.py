"""Current DamageUnit caller ownership, independent of its delegated children.

The finite declaration names stored fields. Each field must match current
metadata, actual buffered source, typed context and unchanged result store.
Calculation/processor unions, effects and positive lists need separate source
composition before any whole DamageUnit or enclosing Skill claim.
"""
from scripts.game_data.memorypack.skill_root_record_sources import derive_direct_record

TYPE='Beyond.Gameplay.Core.DamageAction+DamageUnit'
DECLARATIONS=(
 ('alwaysEndCoalition','bool','bool'),
 ('alwaysStartNewCoalition','bool','bool'),
 ('atkCalculation','Beyond.Gameplay.Core.CalculationBase','reference'),
 ('atkScale','Beyond.Blackboard+BlackboardDouble','reference'),
 ('controlEffectRoll','bool','bool'),
 ('costDataList','System.Collections.Generic.List`1<Beyond.Gameplay.Core.CastData+CostData>','list'),
 ('damageAttributeType','Beyond.Gameplay.DamageAttributeType','enum'),
 ('damageDecorateMask','long','int64'),
 ('damageProcessors','System.Collections.Generic.List`1<Beyond.Gameplay.Core.DamageProcessorBase>','list'),
 ('damageTags','System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>','list'),
 ('damageTextFollowDuration','float','single'),
 ('damageType','Beyond.GEnums.DamageType','enum'),
 ('damageVisualCoalitionGroupKey','string','pool'),
 ('damageVisualImportance','Beyond.Gameplay.Core.AbilitySystem+Modifier+DamageVisualImportance','enum'),
 ('effectData','Beyond.Gameplay.EffectActionCfg','reference'),
 ('enableDamageVisualCoalition','bool','bool'),
 ('enablePoiseBreakTimeDilation','bool','bool'),
 ('gainCost','bool','bool'),
 ('hideMainCharHpScreenEffect','bool','bool'),
 ('hidePoiseUIEffect','bool','bool'),
 ('hitSoundData','Beyond.Gameplay.Core.DamageAction+DamageUnit+HitSoundData','reference'),
 ('ignoreDamageImmuneLevel','Beyond.Gameplay.DamageDecorateType','enum'),
 ('ignorePoiseImmune','bool','bool'),
 ('onlyEnableForMainChar','bool','bool'),
 ('playDefaultHitEffect','bool','bool'),
 ('playHitEffect','bool','bool'),
 ('playHitFlashEffect','bool','bool'),
 ('playHitSound','bool','bool'),
 ('poiseCalculation','Beyond.Gameplay.Core.CalculationBase','reference'),
 ('reduceDamageForGuard','bool','bool'),
 ('reduceDamageForGuardRatio','float','single'),
 ('simpleCalculation','bool','bool'),
 ('takeAtkSnapshot','bool','bool'),
 ('updatePositionOnCoalition','bool','bool'),
)


def derive(image,pins):
    """Return only a fresh same-image source candidate; no child admission."""
    return derive_direct_record(image,pins,TYPE,DECLARATIONS,constructor_holder='rdi')


def derive_reference(image,pins):
    """Own the ordinary DamageUnit adapter, without delegated child admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_child_bindings import need,reference_record_abi
    _publication_gate(image,pins);caller=derive(image,pins)
    need('own-DamageUnit-reference-nominal',TYPE,caller['typeName'])
    need('own-DamageUnit-source-count',len(DECLARATIONS),caller['memberCount'])
    abi=reference_record_abi(image,pins,caller)
    _publication_gate(image,pins)
    return dict(schema='endfield.damage-unit-reference-source.v1',status='validated-DamageUnit-source-and-reference-adapter',
        nativeInputs=dict(pins),typeName=TYPE,wrapperName=caller['wrapperName'],memberCount=caller['memberCount'],
        referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'],
        proof=dict(caller=caller,referenceABI=abi),childGrammarsAdmitted=False,actualParentJoinAdmitted=False,
        wholeDamageUnitAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary='Exact complete current DamageUnit34 caller/new/FF/return, own holder/getter/factory, eager canonical ordinary adapter and Reader ABI. Delegated reference/union/list/effect grammars, actual enclosing action/list and runtime selection remain separate obligations.')


def derive_hit_sound(image,pins):
    """Own the nominal pooled sound-event record, independent of playback."""
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_record_abi
    caller=derive_direct_record(image,pins,TYPE+'+HitSoundData',
        (('soundEvent','string','pool'),),holder='rsi')
    abi=reference_record_abi(image,pins,caller)
    reads=[dict(memberIndex=0,fieldName='soundEvent',kind='pooled-string',childCapability='byte-payload')]
    capability=dict(typeName=caller['typeName'],wrapperName=caller['wrapperName'],memberCount=1,
        orderedReads=reads,wholeGrammarAdmitted=True,nullAdmitted=True,nullMarker=255,
        ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        **{key:abi[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    return dict(schema='endfield.damage-hit-sound-source.v2',nativeInputs=dict(pins),
        status='validated-hit-sound-record-and-reference-adapter',typeName=caller['typeName'],
        wrapperName=caller['wrapperName'],memberCount=1,orderedReads=reads,
        capabilities={'damage-hit-sound-data':capability},requiredExternalCapabilities=['byte-payload'],
        proof=dict(caller=caller,referenceAbi=abi),
        ownGetterReturnedReferenceSemanticsProved=True,actualParentJoinAdmitted=False,
        wholeDamageUnitAdmitted=False,playbackBindingAdmitted=False,
        evidenceBoundary='Exact current one-field pooled sound-event wrapper source/new/FF/full return, own holder/getter, eager canonical reference adapter and conversion, and independently owned generic Reader sources. Matching ready nominal callbacks, coherent contexts and source-disjoint helper effects are conditional. Parent typed source and selected exported pool remain separate; stored sound-event text does not establish a Wwise event, Audio binding or runtime playback.')
