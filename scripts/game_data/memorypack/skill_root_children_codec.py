"""Finite source-owned current Skill child codecs under an operation capability.

Only exact proved nominal record/list programs below are available. Each child
and pool lookup passes the enclosing operation gate before its bytes are read;
unsupported counts stop before the count. Managed widths are checked as native
ABI facts but never consumed as wire widths. These structural codecs do not
open native inputs, admit a root, or infer runtime buff/blackboard behavior.
"""
import struct
from scripts.game_data.memorypack.skill_action_nested_record_codec import CAPABILITIES as NESTED_RECORDS
from scripts.game_data.memorypack import skill_ordinary_ability_map_sources as ORDINARY_MAP
from scripts.game_data.memorypack import skill_special_aim_components as SPECIAL_AIM
from scripts.game_data.memorypack import skill_camera_transition_sources as CAMERA_TRANSITION
from scripts.game_data.memorypack import skill_raycast_record_sources as RAYCAST
from scripts.game_data.memorypack import skill_pull_attenuation_sources as PULL
from scripts.game_data.memorypack.enum_list_native_sources import ENUM_TYPES
from scripts.game_data.memorypack import skill_look_at_target_sources as LOOK_AT

LABEL='skillRootChildren'
MAX_DEPTH=64
VALUE_RECORDS={
 'skill-root-gameplay-tag':('Beyond.Gameplay.Core.GameplayTag',1,4,5,(('tagId','int32'),)),
 'skill-root-buff-id':('Beyond.Gameplay.Core.BuffId',1,8,5,(('buffId','pooled-string'),)),
 'skill-global-buff-id':('Beyond.Gameplay.Core.GlobalBuffId',1,8,5,(('id','pooled-string'),)),
 'skill-root-data-pair':('Beyond.Blackboard+DataPair',4,32,18,(
    ('isDynamic','bool'),('key','pooled-string'),('valueDouble','double-bits'),('valueStr','pooled-string'))),
 'skill-root-assign-pair':('Beyond.Blackboard+AssignPair',6,40,22,(
    ('directValueType','enum32'),('inputValueKey','pooled-string'),('numericValue','single-bits'),
    ('stringValue','pooled-string'),('targetKey','pooled-string'),('useDirectValue','bool'))),
}
LISTS={
 LOOK_AT.LIST:(LOOK_AT.TYPE,False,LOOK_AT.CAPABILITY,10000),
 'skill-action-projectile-preset-point-list':('Beyond.Gameplay.Core.LaunchProjectile+PresetPointDef',False,'skill-action-projectile-preset-point',10000),
 'skill-selector-hitbox-shape-list':('Beyond.Gameplay.Core.Selector+HitBoxFinder+ShapeData',False,'skill-selector-hitbox-shape',10000),
 'skill-root-gameplay-tag-value-list':('Beyond.Gameplay.Core.GameplayTag',True,'skill-root-gameplay-tag',4096),
 'skill-root-buff-id-list':('Beyond.Gameplay.Core.BuffId',True,'skill-root-buff-id',4096),
 'skill-action-global-buff-id-list':('Beyond.Gameplay.Core.GlobalBuffId',True,'skill-global-buff-id',4096),
 'skill-root-data-pair-list-positive':('Beyond.Blackboard+DataPair',True,'skill-root-data-pair',4096),
 'skill-root-assign-pair-list':('Beyond.Blackboard+AssignPair',True,'skill-root-assign-pair',4096),
 'skill-root-buff-input-list':('Beyond.Gameplay.Core.BuffInput',False,'skill-root-buff-input',10000),
 'skill-root-ability-condition-list':('Beyond.Gameplay.Core.Abilities.Condition.ConditionBase',False,'skill-root-ability-condition',10000),
 'skill-root-toggle-buff-list':('Beyond.Gameplay.Core.ToggleBuffData',False,'skill-root-toggle-buff',10000),
 'skill-root-ui-range-hint-list':('Beyond.Gameplay.Core.UIRangeHintData',False,'skill-root-ui-range-hint',10000),
 'skill-action-target-settings-list':('Beyond.Gameplay.Core.TargetSettings',False,'target-profile',10000),
 'skill-action-blackboard-string-list':('Beyond.Blackboard+BlackboardString',False,'skill-blackboard-string',10000),
 'skill-action-blackboard-double-list':('Beyond.Blackboard+BlackboardDouble',False,'skill-blackboard-double',10000),
 'skill-action-blackboard-buff-id-list':('Beyond.Gameplay.Core.Conditions.BlackboardBuffId',False,'skill-blackboard-buff-id',10000),
 'skill-action-selector-validator-list':('Beyond.Gameplay.Core.Selector+Validator+Data',False,'SelectorValidator',10000),
 'skill-action-selector-postprocessor-list':('Beyond.Gameplay.Core.Selector+PostProcessor+Data',False,'SelectorPostProcessor',10000),
 'skill-action-sequence-list':('Beyond.Gameplay.Core.SequenceActionData',False,'SequenceActionData',10000),
 'skill-action-keyword-edit-list':('Beyond.Gameplay.Core.KeywordEnhanceEdit',False,'skill-keyword-enhance-edit',10000),
 'skill-action-create-buff-input-list':('Beyond.Gameplay.Core.CreateBuffActionInput',False,'skill-action-create-buff-input',10000),
 'skill-action-global-buff-input-list':('Beyond.Gameplay.Core.GlobalBuffInput',False,'skill-global-buff-input',10000),
 'skill-action-damage-unit-list':('Beyond.Gameplay.Core.DamageAction+DamageUnit',False,'skill-damage-unit',10000),
 'damage-cost-data-list':('Beyond.Gameplay.Core.CastData+CostData',False,'skill-root-cost-data',10000),
 'damage-processor-list':('Beyond.Gameplay.Core.DamageProcessorBase',False,'damage-processor-union',10000),
 'skill-action-battle-command-mapping-list':('Beyond.Gameplay.Core.ComboCacheAction+Data+BattleCmdMappingModifierData',False,'skill-action-battle-command-mapping-modifier',10000),
 'skill-action-attribute-override-list':('Beyond.Gameplay.Core.OverrideRawAttributeAction+AttributeOverrideEntry',False,'skill-action-attribute-override-entry',10000),
 'skill-action-read-skill-setting-list':('Beyond.Gameplay.Core.ReadSkillSettingData+ReadData',False,'skill-action-read-skill-setting',10000),
 'skill-action-switch-option-list':('Beyond.Gameplay.Core.SwitchAction+Option',False,'skill-action-switch-option',10000),
 ORDINARY_MAP.LIST:(ORDINARY_MAP.TYPE,False,ORDINARY_MAP.CAPABILITY,10000),
 SPECIAL_AIM.LIST:(SPECIAL_AIM.TYPE,False,SPECIAL_AIM.CAPABILITY,10000),
 CAMERA_TRANSITION.LIST:(CAMERA_TRANSITION.TYPE,False,CAMERA_TRANSITION.CAPABILITY,10000),
 RAYCAST.LIST:(RAYCAST.ELEMENT,False,RAYCAST.RECORDS[RAYCAST.ELEMENT]['capability'],10000),
 PULL.LIST:(PULL.TYPE,True,PULL.CAPABILITY,10000),
}
LISTS.update({'skill-enum-list:'+name:(name,True,'skill-enum-callback:'+name,10000)for name in ENUM_TYPES})
ARRAYS={
 'skill-root-attribute-modifier-array':('Beyond.Gameplay.AttributeModifierData+AttributeModifier',False,'skill-root-attribute-modifier',10000),
 ORDINARY_MAP.ARRAY:(ORDINARY_MAP.SEQUENCE,False,'SequenceActionData',10000),
}
QUERY='skill-root-gameplay-tag-query'
TAG_ARRAY='skill-root-gameplay-tag-array'
TAG_RAW='skill-root-gameplay-tag-raw4'
POOLED_STRINGS='skill-root-pooled-string-list'
QUERY_ORDER=[dict(fieldName='queryType',kind='enum32',childCapability=None),
    dict(fieldName='tags',kind='unmanaged-array',childCapability=TAG_ARRAY)]
REFERENCE_RECORDS={
 'skill-global-buff-input':('Beyond.Gameplay.Core.GlobalBuffInput',(
    ('assignBlackboard','bool',None),('assignItems','value-list','skill-root-assign-pair-list'),
    ('globalBuffId','record','skill-global-buff-id'))),
 'skill-action-create-buff-input':('Beyond.Gameplay.Core.CreateBuffActionInput',(
    ('assignBlackboard','bool',None),('assignItems','value-list','skill-root-assign-pair-list'),
    ('buffId','pooled-string','byte-payload'),('buffIdKey','pooled-string','byte-payload'),
    ('readIdFromBlackboard','bool',None))),
 'skill-root-toggle-buff':('Beyond.Gameplay.Core.ToggleBuffData',(
    ('buffs','reference-list','skill-root-buff-input-list'),('conditions','reference-list','skill-root-ability-condition-list'))),
 'skill-root-ui-range-hint':('Beyond.Gameplay.Core.UIRangeHintData',(
    ('selectAll','bool',None),('shapeData','record','skill-root-skill-hint-shape'),('targetFaction','enum32',None))),
 'skill-root-skill-hint-shape':('Beyond.Gameplay.SkillHintShapeData',(
    ('angle','single-bits',None),('angleKey','pooled-string','byte-payload'),('centerBaseIsEndPoint','bool',None),
    ('centerOffset','vector2-raw8',None),('centerOffsetXKey','pooled-string','byte-payload'),('centerOffsetZKey','pooled-string','byte-payload'),
    ('extent','vector2-raw8',None),('extentXKey','pooled-string','byte-payload'),('extentZKey','pooled-string','byte-payload'),
    ('fixedExtent','bool',None),('radius','single-bits',None),('radiusKey','pooled-string','byte-payload'),
    ('restrictEndPointInRange','bool',None),('shape','enum32',None),('useAngleKey','bool',None),
    ('useCenterOffsetKey','bool',None),('useExtentKey','bool',None),('useRadiusKey','bool',None),('useWidthKey','bool',None),
    ('width','single-bits',None),('widthKey','pooled-string','byte-payload'))),
 'skill-root-check-attribute':('Beyond.Gameplay.Core.Abilities.Condition.CheckAttribute',(
    ('attributeType','enum32',None),('compareType','enum32',None),('value','record','skill-blackboard-double'))),
 'skill-root-check-cur-hp-ratio':('Beyond.Gameplay.Core.Abilities.Condition.CheckCurHpRatio',(
    ('compareType','enum32',None),('value','record','skill-blackboard-double'))),
 'skill-root-switch-to-buff-config':('Beyond.Gameplay.Core.SwitchToBuffConfig',(
    ('asSkillCast','bool',None),('buffs','reference-list','skill-root-buff-input-list'),
    ('buffSource','target-profile','target-profile'),('condition','sequence-profile','SequenceActionData'),
    ('targets','target-profile','target-profile'))),
 'skill-root-buff-find-settings':('Beyond.Gameplay.Core.BuffFindSettings',(
    ('buffIdList','pooled-string-list',POOLED_STRINGS),('checkType','enum32',None),
    ('tagQuery','record',QUERY))),
 'skill-root-gameplay-tag-list':('Beyond.Gameplay.Core.GameplayTagList',(
    ('predefinedTag','value-list','skill-root-gameplay-tag-value-list'),)),
 'skill-blackboard-double':('Beyond.Blackboard+BlackboardDouble',(
    ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','single-bits',None))),
 'skill-blackboard-string':('Beyond.Blackboard+BlackboardString',(
    ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','pooled-string','byte-payload'))),
 'skill-blackboard-buff-id':('Beyond.Gameplay.Core.Conditions.BlackboardBuffId',(
    ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','pooled-string','byte-payload'))),
 'skill-blackboard-impact-value':('Beyond.Gameplay.Core.BlackboardImpactValue',(
    ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),
    ('value','int32',None),('useCustomValue','bool',None))),
 'skill-blackboard-super-armor-value':('Beyond.Gameplay.Core.BlackboardSuperArmorValue',(
    ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),
    ('value','int32',None),('useCustomValue','bool',None))),
 'skill-blackboard-blowoff-priority':('Beyond.Gameplay.Core.BlowOffCharacterAction+BlackboardCharBlowOffPriorityValue',(
    ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),
    ('value','int32',None),('useCustomValue','bool',None))),
 'skill-action-animator-param':('Beyond.Gameplay.Core.AnimatorParamAction',(
    ('animatorParam','int32',None),('boolValue','bool',None),('floatValue','single-bits',None),
    ('intValue','int32',None),('paramType','enum32',None))),
 'skill-action-alert-data':('Beyond.Gameplay.Core.SkillAlertData',(
    ('activeTime','single-bits',None),('angle','single-bits',None),('circleOriginOffset','single-bits',None),
    ('moveType','enum32',None),('radius','single-bits',None),('rayMaxDistance','single-bits',None),
    ('rayOriginOffset','single-bits',None),('rayWidth','single-bits',None),('shape','enum32',None))),
 'skill-action-weapon-vfx-override':('Beyond.Gameplay.WeaponVFXOverrideConfig',
    tuple((name,'bool',None)for name in(
        'enableToFightAppearParticleFx','enableToFightAppearRendererFx','enableToIdleAppearParticleFx',
        'enableToIdleAppearRendererFx','enableToIdleAppearRendererFx2','enableToIdleAppearRendererFx3',
        'enableToIdleAppearRendererFx4','enableToIdleDisappearParticleFx','enableToIdleDisappearRendererFx'))+
    tuple((name,'pooled-string','byte-payload')for name in(
        'toFightAppearParticleFx','toFightAppearRendererFx','toIdleAppearParticleFx','toIdleAppearRendererFx',
        'toIdleAppearRendererFx2','toIdleAppearRendererFx3','toIdleAppearRendererFx4','toIdleDisappearParticleFx',
        'toIdleDisappearRendererFx'))),
 'skill-root-attribute-modifier':('Beyond.Gameplay.AttributeModifierData+AttributeModifier',(
    ('attributeType','enum32',None),('formulaItem','enum32',None),('modifyAttributeType','enum32',None),
    ('param','record','skill-blackboard-double'))),
 'skill-root-attribute-modifier-data':('Beyond.Gameplay.AttributeModifierData',(
    ('attributeModifiers','reference-array','skill-root-attribute-modifier-array'),('isConvertedAttribute','bool',None))),
 'skill-root-cost-data':('Beyond.Gameplay.Core.CastData+CostData',(
    ('atbValueThreshold','single-bits',None),('costType','enum32',None),('costValue','single-bits',None))),
 'skill-root-cast-data':('Beyond.Gameplay.Core.CastData',(
    ('castAngle','single-bits',None),('castDistance','record','skill-blackboard-double'),
    ('checkCastDistanceType','enum32',None),('checkHeightDiff','bool',None),('cooldownTime','single-bits',None),
    ('costData','record','skill-root-cost-data'),('heightDiffLimit','record','skill-blackboard-double'),
    ('maxChargeTime','int32',None),('rotateType','enum32',None),('startCdFrame','int32',None),('useCustomCastDistance','bool',None))),
}
BUFF_INPUT_ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('assignBlackboard','bool',None),('assignItems','value-list','skill-root-assign-pair-list'),
    ('buffId','pooled-string','byte-payload'))]
CREATE_BUFF_INPUT_ORDER=BUFF_INPUT_ORDER+[
    dict(fieldName='buffIdKey',kind='pooled-string',childCapability='byte-payload'),
    dict(fieldName='readIdFromBlackboard',kind='bool',childCapability=None)]
BUFF_UNION='skill-root-buff-input-base-positive'
CREATE_BUFF='skill-root-create-buff-action-input'
BUFF_UNION_ROUTES=[
    dict(tag=0,wrappedType='Beyond.Gameplay.Core.BuffInput',wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffInputForMemoryPack',childCapability='skill-root-buff-input'),
    dict(tag=1,wrappedType='Beyond.Gameplay.Core.CreateBuffActionInput',wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffActionInputForMemoryPack',childCapability=CREATE_BUFF)]
CONDITION_UNION='skill-root-ability-condition'
CONDITION_ROUTES=[dict(tag=i,wrappedType='Beyond.Gameplay.Core.Abilities.Condition.'+name,
    wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_Abilities_Condition_'+name+'ForMemoryPack',childCapability=cap)
    for i,name,cap in((0,'CheckAttribute','skill-root-check-attribute'),(1,'CheckCurHpRatio','skill-root-check-cur-hp-ratio'))]
UNIONS={BUFF_UNION:('Beyond.Gameplay.Core.BuffInputBase',BUFF_UNION_ROUTES),
    CONDITION_UNION:('Beyond.Gameplay.Core.Abilities.Condition.ConditionBase',CONDITION_ROUTES)}


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


class RootChildrenReader:
    """Share the authenticated caller's cursor, byte ranges, pool and child gates."""
    def __init__(self,reader):self.reader=reader

    def _capability(self,name):return self.reader.operation.child(name)

    def _record_cap(self,name):
        cap=self._capability(name)
        if name==PULL.CAPABILITY:
            from scripts.game_data.memorypack.skill_pull_attenuation_codec import require_capability
            return require_capability(cap)
        if name in {spec['capability']for spec in RAYCAST.RECORDS.values()}:
            from scripts.game_data.memorypack.skill_raycast_record_codec import require_capability
            return require_capability(cap,name)
        if name==ORDINARY_MAP.CAPABILITY:
            from scripts.game_data.memorypack.skill_ordinary_ability_map_codec import require_capability
            return require_capability(cap)
        if name in NESTED_RECORDS:
            from scripts.game_data.memorypack.skill_action_nested_record_codec import require_capability
            return require_capability(cap,name)
        if name in VALUE_RECORDS:
            typename,count,managed,wire,order=VALUE_RECORDS[name]
            need('value-record-type:'+name,cap.get('typeName')==typename)
            for field,expected in(('memberCount',count),('managedBytes',managed),('positiveWireBytes',wire),('nullWireBytes',1),('nullMarker',255)):
                need('value-record-layout:'+name+':'+field,type(cap.get(field))is int and cap[field]==expected)
            need('value-record-default:'+name,cap.get('nullReturnsDefaultValue')is True and cap.get('nullable')is True and cap.get('wireBytes')is None)
            need('value-record-order:'+name,cap.get('orderedReads')==[dict(fieldName=n,kind=k)for n,k in order])
            if name=='skill-global-buff-id':
                need('GlobalBuffId-own-source',all(cap.get(k)is True for k in
                    ('wholeGrammarAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
        elif name==QUERY:
            need('Query-exact-type',cap.get('typeName')=='Beyond.Gameplay.Core.GameplayTagQuery')
            need('Query-literal-layout',all(type(cap.get(k))is int and cap[k]==v
                for k,v in(('memberCount',2),('managedBytes',16),('nullMarker',255),('nullWireBytes',1))))
            need('Query-admitted-default',cap.get('wholeGrammarAdmitted')is True and cap.get('nullReturnsDefaultValue')is True
                and cap.get('nullable')is True and cap.get('positiveWireBytes')is None and cap.get('wireBytes')is None)
            need('Query-own-getter-factory',cap.get('ownConcreteGetterSemanticsProved')is True and cap.get('ownConcreteFactorySemanticsProved')is True)
            need('Query-exact-order',cap.get('orderedReads')==QUERY_ORDER)
        elif name in REFERENCE_RECORDS:
            typename,order=REFERENCE_RECORDS[name]
            need('reference-record-type:'+name,cap.get('typeName')==typename)
            need('reference-record-count:'+name,type(cap.get('memberCount'))is int and cap['memberCount']==len(order))
            need('reference-record-order:'+name,cap.get('orderedReads')==[
                dict(fieldName=n,kind=k,childCapability=c)for n,k,c in order])
            need('reference-record-positive:'+name,cap.get('wholeGrammarAdmitted')is True
                and cap.get('ownConcreteGetterSemanticsProved')is True and cap.get('ownConcreteFactorySemanticsProved')is True)
            need('reference-record-null:'+name,type(cap.get('nullMarker'))is int and cap['nullMarker']==255
                and cap.get('nullAdmitted')is True and cap.get('nullable')is True)
            if name in('skill-root-check-attribute','skill-root-check-cur-hp-ratio'):
                need('Condition-wrapper-only-admission',cap.get('generatedWrapperOnly')is True
                    and cap.get('ordinaryOriginalReadValueAdmitted')is False)
            if name in('skill-blackboard-double','skill-blackboard-buff-id','skill-blackboard-string','skill-action-animator-param','skill-action-alert-data',
                    'skill-blackboard-impact-value','skill-blackboard-super-armor-value','skill-action-create-buff-input',
                    'skill-action-weapon-vfx-override','skill-global-buff-input','skill-blackboard-blowoff-priority'):
                need('action-record-ordinary-source:'+name,cap.get('ordinaryOriginalReadValueAdmitted')is True
                    and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
                    and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
            if name=='skill-action-create-buff-input':
                need('Create-ordinary-distinct-from-wrapper-only',cap.get('generatedWrapperOnly')is False)
        elif name in('skill-root-buff-input',CREATE_BUFF):
            created=name==CREATE_BUFF;typename='Beyond.Gameplay.Core.CreateBuffActionInput'if created else'Beyond.Gameplay.Core.BuffInput'
            need('buff-input-type',cap.get('typeName')==typename)
            need('buff-input-count',type(cap.get('memberCount'))is int and cap['memberCount']==(5 if created else 3))
            need('buff-input-order',cap.get('orderedReads')==(CREATE_BUFF_INPUT_ORDER if created else BUFF_INPUT_ORDER))
            need('buff-input-admission',cap.get('wholeGrammarAdmitted')is True and cap.get('ownConcreteGetterSemanticsProved')is True)
            need('buff-input-null-marker',type(cap.get('nullMarker'))is int and cap['nullMarker']==255 and cap.get('nullAdmitted')is True)
            if created:
                need('Create-wrapper-only-admission',cap.get('generatedWrapperOnly')is True and cap.get('ordinaryOriginalReadValueAdmitted')is False
                    and cap.get('ownConcreteFactorySemanticsProved')is True)
        else:raise ValueError(LABEL+'.unknown-record='+str(name))
        return cap

    def record(self,name,depth=0):
        if name=='skill-impulse-envelope':
            from scripts.game_data.memorypack.skill_impulse_envelope_codec import ImpulseEnvelopeReader
            return ImpulseEnvelopeReader(self.reader).record(depth)
        if name=='skill-smart-target-select-setting':
            from scripts.game_data.memorypack.skill_smart_target_value_codec import SmartTargetValueReader
            return SmartTargetValueReader(self.reader).record(depth)
        need('depth',type(depth)is int and 0<=depth<=MAX_DEPTH)
        if name==PULL.CAPABILITY:
            from scripts.game_data.memorypack.skill_pull_attenuation_codec import PullAttenuationReader
            return PullAttenuationReader(self.reader).record(depth)
        if name in {spec['capability']for spec in RAYCAST.RECORDS.values()}:
            from scripts.game_data.memorypack.skill_raycast_record_codec import RaycastRecordReader
            return RaycastRecordReader(self.reader).record(name,depth)
        if name==ORDINARY_MAP.CAPABILITY:
            from scripts.game_data.memorypack.skill_ordinary_ability_map_codec import OrdinaryMapReader
            return OrdinaryMapReader(self.reader).record(depth)
        if name in NESTED_RECORDS:
            from scripts.game_data.memorypack.skill_action_nested_record_codec import NestedRecordReader
            return NestedRecordReader(self.reader).record(name,depth)
        cap=self._record_cap(name);r=self.reader;start=r.pos
        if r.peek()==255:
            r.take(1,name+'.null')
            out=dict(start=start,end=r.pos,kind=name,isNull=True,fields=[])
            if name in VALUE_RECORDS or name==QUERY:out['returnsDefaultValue']=True
            r.records.append(out);return out
        r.header(cap['memberCount']);fields=[]
        if name in VALUE_RECORDS:
            order=VALUE_RECORDS[name][4]
            for field,kind in order:
                at=r.pos
                if kind=='pooled-string':r.byte_payload()
                else:r.take({'bool':1,'enum32':4,'int32':4,'single-bits':4,'double-bits':8}[kind],name+'.'+field+'.'+kind)
                fields.append(dict(fieldName=field,start=at,end=r.pos))
        elif name==QUERY:
            at=r.pos;r.take(4,name+'.queryType.enum32');fields.append(dict(fieldName='queryType',start=at,end=r.pos))
            at=r.pos;self.primitive_array(TAG_ARRAY,depth+1);fields.append(dict(fieldName='tags',start=at,end=r.pos))
        elif name in REFERENCE_RECORDS:
            for field,kind,child in REFERENCE_RECORDS[name][1]:
                at=r.pos
                if kind=='pooled-string':r.byte_payload()
                elif kind=='record':self.record(child,depth+1)
                elif kind in('reference-array','reference-list','value-list'):self.collection(child,depth+1)
                elif kind=='pooled-string-list':self.pooled_strings(child,depth+1)
                elif kind in('target-profile','sequence-profile'):
                    need('depth',depth+1<=MAX_DEPTH)
                    if kind=='target-profile':r.target_profile()
                    else:r._sequence(depth+1)
                else:r.take({'bool':1,'enum32':4,'int32':4,'single-bits':4,'vector2-raw8':8}[kind],name+'.'+field+'.'+kind)
                fields.append(dict(fieldName=field,start=at,end=r.pos))
        else:
            at=r.pos;r.take(1,'BuffInput.assignBlackboard.bool')
            fields.append(dict(fieldName='assignBlackboard',start=at,end=r.pos));at=r.pos
            self.collection('skill-root-assign-pair-list',depth+1)
            fields.append(dict(fieldName='assignItems',start=at,end=r.pos));at=r.pos
            r.byte_payload();fields.append(dict(fieldName='buffId',start=at,end=r.pos))
            if name==CREATE_BUFF:
                at=r.pos;r.byte_payload();fields.append(dict(fieldName='buffIdKey',start=at,end=r.pos))
                at=r.pos;r.take(1,'CreateBuffActionInput.readIdFromBlackboard.bool')
                fields.append(dict(fieldName='readIdFromBlackboard',start=at,end=r.pos))
        out=dict(start=start,end=r.pos,kind=name,isNull=False,memberCount=cap['memberCount'],fields=fields)
        r.records.append(out);return out

    def pooled_strings(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=MAX_DEPTH)
        need('known-pooled-string-list',name==POOLED_STRINGS)
        cap=self._capability(name);r=self.reader;start=r.pos
        need('pooled-string-list-exact-kind',cap.get('elementType')=='string'and cap.get('elementValueType')is False
            and cap.get('closedListType')=='System.Collections.Generic.List`1<string>'and cap.get('elementCapability')=='byte-payload')
        need('pooled-string-list-callback',cap.get('stringEncoding')=='int32-pool-index'
            and all(type(cap.get(k))is int and cap[k]==v for k,v in(('elementWireBytes',4),('elementManagedReferenceBytes',8))))
        need('pooled-string-list-null-empty',cap.get('nullable')is True and cap.get('collectionCounts')==[-1,0]
            and all(type(n)is int for n in cap['collectionCounts']))
        limit=cap.get('countLimit');need('pooled-string-list-bound',type(limit)is int and 0<=limit<=10000)
        need('pooled-string-list-positive-flag',type(cap.get('positiveCountsAdmitted'))is bool)
        if r.pos+4>r.limit:raise ValueError(LABEL+'.truncated-count='+name)
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('pooled-string-list-unproved-count:'+str(count),-1<=count<=limit and(count<=0 or cap['positiveCountsAdmitted']is True))
        if count>0:
            need('pooled-string-list-positive-elements',cap.get('elementGrammarAdmitted')is True)
            need('pooled-string-list-selected-pool-child',self._capability('byte-payload').get('wholeGrammarAdmitted')is True)
        actual=r.count(4,nullable=True)
        for _ in range(max(0,actual)):r.byte_payload()
        out=dict(start=start,end=r.pos,kind=name,count=actual,elementType='string');r.records.append(out);return out

    def primitive_array(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=MAX_DEPTH);need('known-primitive-array',name==TAG_ARRAY)
        cap=self._capability(name);r=self.reader;start=r.pos;typename='Beyond.Gameplay.Core.GameplayTag'
        need('Tag-array-nominal',cap.get('elementType')==typename and cap.get('closedArrayType')==typename+'[]'
            and cap.get('elementValueType')is True and cap.get('elementCapability')==TAG_RAW)
        need('Tag-array-raw-width',type(cap.get('elementWireBytes'))is int and cap['elementWireBytes']==4)
        need('Tag-array-null-empty',cap.get('nullable')is True and cap.get('collectionCounts')==[-1,0]
            and all(type(n)is int for n in cap['collectionCounts']))
        limit=cap.get('countLimit');need('Tag-array-resource-bound',type(limit)is int and 0<=limit<=64)
        need('Tag-array-positive-flag',type(cap.get('positiveCountsAdmitted'))is bool)
        if r.pos+4>r.limit:raise ValueError(LABEL+'.truncated-count='+name)
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('Tag-array-unproved-count:'+str(count),-1<=count<=limit and(count<=0 or cap['positiveCountsAdmitted']is True))
        if count>0:
            need('Tag-array-positive-source',cap.get('elementGrammarAdmitted')is True and cap.get('bulkCopyProved')is True)
            element=self._capability(TAG_RAW)
            need('Tag-array-independent-raw-child',element.get('typeName')==typename and element.get('elementValueType')is True
                and element.get('wholeGrammarAdmitted')is True and element.get('nullable')is False
                and all(type(element.get(k))is int and element[k]==v for k,v in(('managedBytes',4),('wireBytes',4),('contextTypeKind',17))))
        actual=r.count(4,nullable=True)
        r.take(max(actual,0)*4,name+'.raw4-payload')
        out=dict(start=start,end=r.pos,kind=name,count=actual,elementType=typename);r.records.append(out);return out

    def _union_cap(self,name):
        need('known-union',name in UNIONS);cap=self._capability(name);typename,routes=UNIONS[name]
        need('BuffInputBase-union-type',cap.get('typeName')==typename)
        need('BuffInputBase-positive-children',cap.get('wholeGrammarAdmitted')is True
            and cap.get('baseGetterSemanticsProved')is True and cap.get('concreteChildGrammarsProved')is True)
        need('BuffInputBase-null-marker',type(cap.get('nullMarker'))is int and cap['nullMarker']==255 and cap.get('nullAdmitted')is True)
        need('BuffInputBase-tag-domain',cap.get('supportedShortTags')==[0,1]
            and all(type(tag)is int for tag in cap['supportedShortTags'])
            and cap.get('extendedTagsAdmitted')is False and cap.get('reservedMarkersAdmitted')is False)
        need('BuffInputBase-concrete-routes',cap.get('routes')==routes
            and all(type(route.get('tag'))is int for route in cap['routes']))
        return cap,routes

    def union(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=MAX_DEPTH)
        cap,routes=self._union_cap(name);r=self.reader;start=r.pos
        tag=r.peek()
        if tag==255:
            r.take(1,name+'.null');out=dict(start=start,end=r.pos,kind=name,isNull=True)
        else:
            need('BuffInputBase-unsupported-tag:'+str(tag),tag in(0,1))
            route=routes[tag];self._record_cap(route['childCapability'])
            r.take(1,name+'.union-tag');child=self.record(route['childCapability'],depth+1)
            out=dict(start=start,end=r.pos,kind=name,isNull=False,tag=tag,child=child)
        r.records.append(out);return out

    def collection(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=MAX_DEPTH)
        if name==LOOK_AT.LIST:
            from scripts.game_data.memorypack.skill_look_at_target_codec import LookAtTargetReader
            return LookAtTargetReader(self.reader).collection(depth)
        if name in{'skill-enum-list:'+nominal for nominal in ENUM_TYPES}:
            from scripts.game_data.memorypack.skill_enum_list_codec import read
            return read(self.reader,name,depth)
        if name==CAMERA_TRANSITION.LIST:
            from scripts.game_data.memorypack.skill_camera_transition_codec import CameraTransitionReader
            return CameraTransitionReader(self.reader).collection(depth)
        if name==SPECIAL_AIM.LIST:
            from scripts.game_data.memorypack.skill_special_aim_codec import SpecialAimReader
            return SpecialAimReader(self.reader).collection(depth)
        if name==ORDINARY_MAP.ARRAY:
            from scripts.game_data.memorypack.skill_ordinary_ability_map_codec import OrdinaryMapReader
            return OrdinaryMapReader(self.reader).array(depth)
        if name not in LISTS and name not in ARRAYS:raise ValueError(LABEL+'.unknown-collection='+str(name))
        array=name in ARRAYS
        typename,value,element,maximum=(ARRAYS if array else LISTS)[name];cap=self._capability(name);r=self.reader;start=r.pos
        need('list-type:'+name,cap.get('elementType')==typename and cap.get('elementValueType')is value
            and cap.get('closedArrayType'if array else'closedListType')==(typename+'[]'if array else'System.Collections.Generic.List`1<'+typename+'>'))
        need('list-element:'+name,cap.get('elementCapability')==element)
        need('list-nullable:'+name,cap.get('nullable')is True)
        counts=cap.get('collectionCounts')
        need('list-counts:'+name,isinstance(counts,list)and all(type(n)is int for n in counts)and -1 in counts and 0 in counts)
        limit=cap.get('countLimit');need('list-resource-bound:'+name,type(limit)is int and 0<=limit<=maximum)
        need('literal-positive-admission:'+name,type(cap.get('positiveCountsAdmitted'))is bool)
        if r.pos+4>r.limit:raise ValueError(LABEL+'.truncated-count='+name)
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        admitted=count in counts or count>0 and cap['positiveCountsAdmitted']is True
        need('unproved-count:'+name+':'+str(count),admitted and -1<=count<=limit)
        if count>0:
            need('positive-count-gate:'+name,cap['positiveCountsAdmitted']is True)
            need('positive-elements:'+name,cap.get('elementGrammarAdmitted')is True)
            need('depth',depth+1<=MAX_DEPTH)
            if element in UNIONS:self._union_cap(element)
            elif element in('SelectorValidator','SelectorPostProcessor'):
                child=self._capability(element);tags=child.get('admittedRouteTags')
                need('Selector-list-finite-current-union',child.get('typeName')==typename
                    and child.get('nullAdmitted')is True and child.get('wholeGrammarAdmitted')is False
                    and child.get('positiveRoutesRequireExplicitProgram')is True
                    and isinstance(tags,list)and bool(tags)and all(type(tag)is int and 0<=tag<=65535 for tag in tags)
                    and tags==sorted(set(tags))and cap.get('admittedRouteTags')==tags)
            elif name=='skill-action-damage-unit-list':
                from scripts.game_data.memorypack.skill_damage_codec import DamageUnitReader
                DamageUnitReader(r).require_damage_capability()
            elif name=='damage-processor-list':
                child=self._capability(element)
                need('Damage-list-own-complete-union',child.get('typeName')==typename
                    and child.get('wholeGrammarAdmitted')is True and child.get('ordinaryOriginalReadValueAdmitted')is True
                    and child.get('baseGetterSemanticsProved')is True and child.get('concreteChildGrammarsProved')is True)
            elif name=='skill-action-keyword-edit-list':
                from scripts.game_data.memorypack.skill_action_setting_codec import require_capability
                require_capability(self._capability(element),element)
            elif name in('skill-action-target-settings-list','skill-action-sequence-list'):
                child=self._capability(element)
                need('Target-list-own-positive-child',child.get('typeName')==typename
                    and child.get('wholeGrammarAdmitted')is True and child.get('ordinaryOriginalReadValueAdmitted')is True
                    and child.get('ownConcreteGetterSemanticsProved')is True and child.get('ownConcreteFactorySemanticsProved')is True
                    and type(child.get('referenceReaderMethodDefinition'))is int and child['referenceReaderMethodDefinition']>0
                    and type(child.get('referenceReaderTargetRva'))is int and child['referenceReaderTargetRva']>0)
                if name=='skill-action-sequence-list':
                    need('Sequence-list-own-count-induction',child.get('positiveCountsAdmitted')is True
                        and child.get('freshArrayCountInductionProved')is True
                        and type(child.get('countLimit'))is int and 17<=child['countLimit']<=10000)
            else:self._record_cap(element)
        actual=r.count(1,nullable=True)
        for _ in range(max(0,actual)):
            if element in('SelectorValidator','SelectorPostProcessor'):r._selector(element)
            elif name=='skill-action-target-settings-list':r.target_profile()
            elif name=='skill-action-sequence-list':r._sequence(depth+1)
            elif name=='skill-action-damage-unit-list':
                from scripts.game_data.memorypack.skill_damage_codec import DamageUnitReader
                DamageUnitReader(r).damage(depth+1)
            elif name=='damage-processor-list':
                from scripts.game_data.memorypack.skill_damage_children_codec import DamageChildrenReader
                DamageChildrenReader(r).union(element,depth+1)
            elif name=='skill-action-keyword-edit-list':
                from scripts.game_data.memorypack.skill_action_setting_codec import ActionSettingReader
                ActionSettingReader(r).record(element,depth+1)
            else:(self.union if element in UNIONS else self.record)(element,depth+1)
        out=dict(start=start,end=r.pos,kind=name,count=actual,elementType=typename)
        r.records.append(out);return out
