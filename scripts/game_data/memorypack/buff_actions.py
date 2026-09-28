"""Anonymous BuffData event-prefix framing; no legacy union-tag aliases.

``Reader`` is the structural cursor shared by the BuffData readers. It
records contiguous atomic spans and completed records but assigns no field
meanings; named receipts elsewhere attach generated names to its spans.

- ``event_prefix`` reads the 30-member ``BuffDataForMemoryPack`` header and
  field 0, ``abilityEventAction``, from byte zero.
- ``root_continuation`` reads fields 1-5 in generated setter order
  (``addingCooldown``, ``applyTags``, ``attributeModifier``, ``blackboard``,
  ``buffEventAction``) only after a supported first-collection endpoint;
  the caller owns that prerequisite.
- ``damage_modifier_element_profile`` and ``heal_modifier_element_profile``
  follow the generated three-field ``DamageModifier``/``HealModifier``
  wrappers and are driven by ``buff.frame_buff_named_middle``.

Damage processor union routes closed here: 0, 2, 3, 4, 5, 6, 9 and 10. The
current native dispatcher binds 0/2/3/4 to the critical-rate,
``AttackerCriticalDamageProcessorForMemoryPack``,
``AttackerPenProcessorForMemoryPack`` and
``DamageIndependentHealthProcessorForMemoryPack`` wrappers, each one
bounded ``BlackboardDouble`` (``scale`` or ``multiplier``); 5 to
``DamageScaleProcessorForMemoryPack`` (``addition``, ``side``,
``zoneName``); 6 to ``DamageTextProcessorForMemoryPack`` (a bounded
``DamageTextStyle`` scalar, then ``useHpChangeAsDisplayValue``); and 10 to
``ModifyCalcResultForMemoryPack`` (``baseMultiplier``, ``modifyType``,
``multiplierCnt``, the two multipliers as bounded ``BlackboardDouble``
around a raw enum-like scalar). Both current heal processor routes (0, 1)
are closed. Any other damage route stops at its union tag. The per-route
child receipts are the ``buff_damage_*_processor_child_receipt`` modules.

Root framing. ``event_prefix`` works under each retained filename-anchor
candidate's hard limit and stops at the first unsupported union; atomic spans
plus an explicit physical-file remainder tile the bytes, and that remainder is
opaque, not a decoded record. The root members after field 0 follow the
reviewed ``buff_root_prefix``/``fifth``/``sixth`` native contracts:

- fields 1-3 (``buff_root_prefix_native.json``): a scalar payload, a directly
  counted raw DWORD array (four bytes per entry, no element header; the
  ``GameplayTag`` type name does not select the separate tag-list wrapper),
  and a member-two collection profile whose terminal byte exists only when
  it is non-null;
- field 4 (``buff_root_fifth_native.json``), a ``List<DataPair>``: member-four
  elements read a byte, a signed nullable byte payload, eight raw bytes, then
  another nullable payload. The eight-byte load is pinned on its own -- not
  the scalar profile's four-byte value -- and the leading byte is not a union
  tag;
- field 5 (``buff_root_sixth_native.json``), a ``List<BuffActionMap>``: FF or
  member two, a nullable Sequence array, then a required inline DWORD. This
  reverses the first collection's scalar/array order, so equal member counts
  do not make the two maps interchangeable.

``Reader._action`` dispatches AbilityActionData records by type name: the tag
it reads is resolved per build (``levelscript_union_tags.tag_name``), and the
supported set, each reviewed member count (``_ACTION_MEMBER_COUNTS``) and
every per-type body are keyed by name, so a client update that renumbers the
union moves the routes with it. An unvalidated build admits no action.
``IF_ELSE_ACTION_TAG`` stays exported for the receipt that validates it
against the tag contract; the nested selector and processor unions below
still key on their tags.

Extended unions consume ``FA`` followed by a little-endian unsigned 16-bit
tag; records keep the decoded tag, not the escape byte. Supporting a decoded
tag does not admit its reserved single-byte encoding. The recurring action
prefix (one byte plus three scalar32 values) is a shared shape, not an
identifier, and cannot select a reader.

Evidence tier: ``structuralOnly`` cursor framing. The stored names and order
do not establish processor arithmetic, presentation behavior, live provider
choice or whole-BuffData EOF.
"""
import struct

from scripts.game_data import levelscript_union_tags as union_tags


IF_ELSE_ACTION_TAG = 0x00C9
IF_ELSE_ACTION_MEMBER_COUNT = 8
IF_ELSE_ACTION_READ_KINDS = (
    'anonymous-nonzero-byte',
    'anonymous-scalar32',
    'anonymous-scalar32',
    'anonymous-scalar32',
    'anonymous-nonzero-byte',
    'SequenceActionData',
    'SequenceActionData',
    'SequenceActionData',
)
SEQUENCE_RECURSION_LIMIT = 64

IF_ELSE_ACTION_NAME = 'Core_IfElseAction_IfElseActionData'

# Every AbilityActionData type ``Reader._action`` reads, with the member count
# its layout reads. Keyed by type name: the tag is resolved per build
# (``levelscript_union_tags.tag_name``) and never written down here.
_ACTION_MEMBER_COUNTS = {
    IF_ELSE_ACTION_NAME: IF_ELSE_ACTION_MEMBER_COUNT,
    'Core_Conditions_CheckSkillId_Data': 5,
    'Core_ModifyDynamicBlackboard_Data': 10,
    'Core_CompareFloat_Data': 7,
    'Core_RaiseTrainLevelEvent_Data': 8,
    'Core_FinishBuffAdvanced_Data': 13,
    'Core_Conditions_CheckBuffIdInContext_Data': 8,
    'Core_CreateBuffAction_Data': 19,
    'Core_Conditions_CheckBuffIdInContextAdvanced_Data': 8,
    'Core_Conditions_CheckDamageDecorateMask_Data': 6,
    'Core_CheckBuffStackNumAdvanced_Data': 10,
    'Core_Conditions_CheckSkillType_Data': 9,
    'Core_FindTargetAction_FindTargetActionData': 18,
    'Core_Conditions_CheckMainCharacterCondition_Data': 5,
    'Core_Conditions_CheckTimedMarkerCondition_Data': 9,
    'Core_Conditions_CheckBuffStackNum_Data': 8,
    'Core_AbilityActions_FinishBuffAction_Data': 12,
    'Core_DamageAction_DamageActionData': 11,
    'Core_EffectAction_EffectActionData': 18,
    'Core_Conditions_CheckHp_Data': 8,
    'Core_SpawnAbilityEntity_Data': 38,
    'Core_SetSkillCdAtOnce_Data': 11,
    'Core_Conditions_CheckPoiseValue_Data': 8,
    'Core_ObtainCostAction_Data': 20,
    'Core_CreateTimedMarker_Data': 9,
    'Core_NotNextCheckAction_Data': 4,
    'Core_Conditions_CheckTagMatch_Data': 6,
    'Core_FinishOwnerAction_Data': 6,
    'Core_Conditions_CheckTargetsEqual_Data': 6,
    'Core_SpellInflictionOnChar_Data': 13,
    'Core_Conditions_CheckSuperArmor_Data': 7,
    'Core_Conditions_CheckPhysicalInflictionType_Data': 6,
    'Core_SaveBuffStackNumAdvanced_Data': 9,
    'Core_SimpleCalcBBAction_Data': 8,
    'Core_Conditions_CheckObjectTypeMatch_Data': 6,
    'Core_CheckGlobalCDTimerAction_Data': 6,
    'Core_PauseBuffTime_Data': 5,
    'Core_DebugPrintAction_Data': 9,
    'Core_HealAction_Data': 16,
    'Core_PlaySoundAction_PlaySoundActionData': 22,
    'Core_AddGlobalCDTimer_Data': 7,
    'Core_Conditions_CheckSpellInflictionType_Data': 6,
    'Core_Conditions_Probablity_Data': 5,
    'Core_CheckOriginSkillType_Data': 6,
    'Core_Conditions_CheckCustomAbilityEvent_Data': 6,
    'Core_GetTargetBuffBBAdvanced_Data': 8,
    'Core_SendBattleSignalToLevel_Data': 6,
    'Core_LaunchProjectile_Data': 37,
    'Core_ForEachAction_Data': 6,
    'Core_Conditions_CheckObtainAtbType_Data': 8,
    'Core_CameraImpulseAction_CameraImpulseActionData': 12,
    'Core_SpawnInteractiveGoldCoin_Data': 6,
    'Core_Conditions_CheckTargetContains_Data': 6,
    'Core_CharHurtAnimAction_Data': 15,
    'Core_MergeTargetAction_Data': 7,
    'Core_Conditions_CheckEntityNum_Data': 10,
    'Core_CheckConsumeBuffLayer_Data': 7,
    'Core_SetBuffDurationAction_Data': 9,
    'Core_Conditions_CheckSkillCastId_Data': 4,
    'Core_Conditions_CheckDamageType_Data': 5,
    'Core_CheckDistanceCondition_Data': 10,
    'Core_CastSkill_Data': 10,
    'Core_CreateGlobalBuffAction_Data': 8,
    'Core_Conditions_CheckSkillDamageType_Data': 5,
    'Core_SpellInfliction_Data': 8,
    'Core_ShowHideActorAction_ShowHideActorData': 10,
    'Core_Conditions_SaveHealValue_Data': 6,
    'Core_StoreAttributeValue_Data': 13,
    'Core_SaveAtbObtainValue_Data': 6,
    'Core_InterruptAction_Data': 8,
    'Core_Conditions_CheckEnemyRank_Data': 6,
    'Core_RecoverFromPoiseBreak_Data': 5,
    'Core_BlowOffCharacterAction_Data': 15,
    'Core_AchieveSpecialGameEventAction_Data': 5,
    'Core_SaveValueFromAIBlackboard_Data': 11,
    'Core_AbilityActions_FinishGlobalBuffAction_Data': 9,
    'Core_CompareString_Data': 6,
    'Core_Conditions_CheckDamageTypeMask_Data': 5,
    'Core_SaveDamageContext_Data': 6,
    'Core_Conditions_CheckWeaponTypeCondition_Data': 6,
    'Core_StoreEntityProperty_Data': 11,
    'Core_CheckDamageTransferredSource_Data': 6,
    'Core_EnemyHurtAnimAction_Data': 28,
    'Core_Conditions_CheckHasDamageSkillCastId_Data': 4,
    'Core_SaveDamageSkillCastId_Data': 4,
    'Core_CountShieldUIAction_Data': 8,
    'Core_ForceTargetInFightAction_Data': 6,
    'Core_AddTagAction_Data': 8,
    'Core_AddTagToEntities_Data': 8,
    'Core_ChangeSeasonTowerEnergyAction_Data': 5,
    'Core_PlayAnimationAction_PlayAnimationActionData': 16,
    'Core_SetHpFloor_Data': 8,
    'Core_SaveShieldValueToBB_Data': 7,
    'Core_SaveTargetDistanceAction_Data': 7,
    'Core_CurveEvaluateFloat_Data': 9,
    'Core_SwitchAction_Data': 7,
    'Core_CreateBuffAttachingSkill_Data': 19,
    'Core_StoreSkillDamageType_Data': 5,
    'Core_NotifyCharPassiveUIAction_Data': 6,
    'Core_Conditions_CheckUsp_Data': 8,
    'Core_SaveCollectedBuffBbValue_Data': 6,
    'Core_Conditions_ModifyCollectedBuffBbValue_Data': 9,
    'Core_Conditions_CheckHealTag_Data': 5,
    'Core_Conditions_CheckOverHeal_Data': 7,
    'Core_Conditions_CheckSkillInterruptReason_Data': 5,
    'Core_TriggerCustomAbilityEvent_Data': 8,
    'Core_CheckDamageTag_Data': 6,
    'Core_TriggerComboSkillAction_Data': 9,
    'Core_SaveCharTypeId_Data': 6,
    'Core_TriggerLiinoUIEvent_Data': 7,
    'Core_SaveBuffStackNum_Data': 7,
    'Core_ReadSkillSettingData_Data': 5,
    'Core_Conditions_CheckDamageIgnoreImmuneLevel_Data': 6,
    'Core_TimeDilationAction_Data': 16,
    'Core_ChannelingAction_Data': 10,
    'Core_ShakeCountShieldUIAction_Data': 5,
    'Core_SpendAtbAction_Data': 7,
    'Core_AbilityActions_InterruptCurSkillAction_Data': 5,
    'Core_CheckBuffEnhanceChangedLayer_Data': 7,
    'Core_ClearProjectileAction_Data': 12,
    'Core_SetGeneralAbilityCd_Data': 6,
    'Core_EnablePartsAction_Data': 11,
    'View_AddCameraControlStateAction_AddCameraControlStateActionData': 23,
    'Core_AddDynamicCcsAction_AddDynamicCcsActionData': 50,
    'Core_RandomAction_Data': 8,
    'Core_DispelAction_Data': 9,
    'Core_BlowOffAction_Data': 17,
    'Core_Conditions_OrConditionAction_Data': 5,
    'Core_Condition_CheckSquadInFight_Data': 5,
    'Core_CostAtbRefreshLongestSkillCd_Data': 5,
    'Core_RecoverDashEnergy_Data': 6,
    'Core_RecordBattleDetails_Data': 5,
    'Core_SetFirstDashParam_Data': 5,
    'Core_Conditions_CheckProjectileInPerfectDodgeCd_Data': 5,
    'Core_Conditions_CheckProjectileIgnoreImmuneLevel_Data': 6,
    'Core_SetSuperArmorAction_Data': 7,
    'Core_AuraAction_Data': 30,
    'Core_SwitchModeAction_Data': 8,
    'Core_GetAITransDataAction_Data': 6,
    'Core_OnSpellAbnormalStartFinish_Data': 6,
    'Core_HitStopAction_Data': 12,
    'Core_VulnerableAction_Data': 14,
    'Core_RecoverPoiseAction_Data': 11,
    'Core_SkillAffixAction_Data': 4,
    'Core_IgniteBuffTextAction_Data': 11,
    'Core_RefreshBuffAttrModifierValue_Data': 4,
    'Core_ChangeSkillAction_Data': 14,
    'Core_RecoverLockOnEndIfNoLockAction_Data': 5,
    'Core_EnhancedAction_Data': 14,
    'Core_MoveToAction_Data': 46,
    'Core_TeleportAction_Data': 14,
    'Core_TriggerCharSpellInflictionEvent_Data': 7,
    'Core_ForceHideHeadBarAction_Data': 6,
    'Core_MoveGaitAction_Data': 6,
    'Core_SaveBuffLifeTime_Data': 7,
    'Core_SetAnimatorParamAction_Data': 8,
    'Core_ShelterAction_Data': 13,
    'Core_CharWeaponVisibleAction_CharWeaponVisibleActionData': 10,
    'Core_RefrainObtainUsp_Data': 7,
    'Core_SelfRotateAction_Data': 18,
    'Core_SetWeaknessAction_Data': 11,
    'Core_AddAIMarkerAction_Data': 8,
    'Core_TriggerSpellBurstEventAction_Data': 5,
    'Core_WeakAction_Data': 13,
    'Core_ContinuousFindTargetAction_Data': 19,
    'Core_SetAnimTimeScaleAction_Data': 6,
    'Core_SlowAction_Data': 13,
    'Core_StoreBuffCount_Data': 8,
    'Core_ChangeGeneralAbilityButton_Data': 7,
    'Core_OnSpellInflictionStart_Data': 5,
    'Core_TyphoeaArcheryChipDataAction_Data': 18,
    'Core_TyphoeaIsInShootingRangeAction_Data': 6,
    'Core_ForceTriggerWeakness_Data': 6,
    'Core_SetDamageTagImmuneRule_Data': 6,
    'Core_LockCameraAimAction_LockCameraAimActionData': 54,
    'Core_IgniteAction_Data': 8,
    'Core_BindBountyEnemyAction_Data': 5,
    'Core_EventListenerAction_Data': 5,
    'Core_VoiceTriggerAction_VoiceTriggerActionData': 11,
    'Core_VoiceInterruptAction_VoiceInterruptActionData': 6,
    'Core_CreateAdditionalBattleShape_Data': 10,
    'Core_CreateDynamicBattleShape_Data': 7,
    'Core_TogglableAction_Data': 6,
    'Core_LaunchUpwardAction_Data': 15,
    'Core_BombTouchLayerAction_Data': 15,
    'Core_FlowTextAction_Data': 9,
    'Core_ModifyResilienceDecreaseFactor_Data': 5,
    'Core_Conditions_CheckBuffFromSource_Data': 9,
    'Core_CharWeaponAnimationAction_CharWeaponAnimationActionData': 12,
    'Core_BreakoutAction_Data': 6,
    'Core_EnableSpecialAim_Data': 7,
    'Core_BroadcastAlertToCharactersAction_BroadcastAlertToCharactersActionData': 11,
    'Core_SpawnEnemyAction_Data': 18,
    'Core_Conditions_CheckProfession_Data': 6,
    'Core_ShowSquadTipsAction_Data': 5,
    'Core_GainCostAction_Data': 7,
    'Core_PullAction_Data': 19,
    'Core_ConvertToTargetContext_Data': 12,
    'Core_ComboCacheAction_Data': 5,
    'Core_SpeedupAction_Data': 13,
    'Core_Conditions_CompareDeckAttr_Data': 10,
    'Core_SetStrafeModeAction_Data': 10,
    'Core_SetWaterDroneItemModePersistLiquidIdAction_Data': 6,
    'Core_TagQueryListenerAction_Data': 9,
    'Core_AirborneAction_AirborneActionData': 16,
    'Core_CastPlungingAttack_Data': 5,
}



class FrameError(ValueError):
    def __init__(self, source, offset, expected, actual, category='malformed'):
        self.diagnostic=dict(source=source,offset=offset,expected=expected,actual=actual,category=category)
        super().__init__(f'{source}: offset={offset} expected={expected!r} actual={actual!r}')


class Unsupported(FrameError):
    pass


class Reader:
    def __init__(self,data,source,limit=None):
        self.data=data;self.source=source;self.pos=0;self.ranges=[];self.records=[]
        self.postprocessor_depth=0;self.target_depth=0
        self.limit=len(data) if limit is None else limit
        if type(self.limit) is not int or not 0<=self.limit<=len(data):
            raise FrameError(source,0,'limit within file',self.limit)

    def take(self,n,kind):
        if type(n) is not int or n<0 or n>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':n},{'remaining':self.limit-self.pos},'truncated')
        start=self.pos;self.pos+=n
        if n:self.ranges.append(dict(start=start,end=self.pos,kind=kind))
        return self.data[start:self.pos]

    def peek(self):
        if self.pos==self.limit:raise FrameError(self.source,self.pos,'one byte','EOF','truncated')
        return self.data[self.pos]

    def header(self,expected):
        actual=self.peek()
        if actual!=expected:raise FrameError(self.source,self.pos,expected,actual,'member-count')
        self.take(1,'member-header')

    def count(self,minimum,reserve=0,nullable=False):
        start=self.pos;n=struct.unpack('<i',self.take(4,'count-i32'))[0]
        if n==-1 and nullable:return n
        maximum=max(0,(self.limit-self.pos-reserve)//minimum)
        if n<0 or n>maximum:
            raise FrameError(self.source,start,{'minimum':-1 if nullable else 0,'maximum':maximum},n,'count-bounds')
        return n

    def sequence(self,depth=0):
        start=self.pos
        self._sequence(depth)
        self.records.append(dict(start=start,end=self.pos,kind='sequence'))

    def _sequence(self,depth):
        if depth>SEQUENCE_RECURSION_LIMIT:
            raise Unsupported(self.source,self.pos,
                              f'nesting <= {SEQUENCE_RECURSION_LIMIT}',depth,'depth-limit')
        if self.peek()==255:self.take(1,'null-sequence');return
        self.header(3)
        count=self.count(1,reserve=2,nullable=True)
        for _ in range(max(0,count)):self.action(depth+1)
        # The structural reader only records the terminal byte ranges; zero
        # values are valid and are not rejected or assigned field semantics.
        self.take(1,'anonymous-byte')
        self.take(1,'anonymous-byte')

    def action(self,depth):
        start=self.pos
        lead=self.peek();width=3 if lead==250 else 1
        if width>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':width},{'remaining':self.limit-self.pos},'truncated')
        tag=struct.unpack_from('<H',self.data,self.pos+1)[0] if lead==250 else lead
        self._action(depth,tag,width)
        self.records.append(dict(start=start,end=self.pos,kind='union',tag=tag))

    def _action(self,depth,tag,width):
        # FA carries an unsigned little-endian tag, not a child-object header.
        # Keep unknown tags at their first byte; never search for a later tag.
        if tag==255 and width==1:self.take(1,'null-union');return
        name=union_tags.tag_name('AbilityActionData',tag)
        if name=='Core_PatrolTeleport_Data':
            # This selected header-six action reads a byte, three raw scalars,
            # a bounded signed-length byte payload, then four float32 bytes.
            self.take(width,'union-tag')
            if self.peek()==255:self.take(1,'null-wrapper');return
            self.header(6)
            self.take(1,'anonymous-byte')
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.byte_payload(reserve=4)
            self.take(4,'anonymous-float32-bits')
            return
        if name in ('Core_IntResourceHpCheckAction_Data','Core_IntResourceOnHpZeroAction_Data'):
            # Current native routes D5/D6 share a four-member source reader:
            # one boolean byte followed by three fixed-width raw DWORDs.
            # Keep the child values anonymous; the VFS bytes do not establish
            # their managed field ownership or gameplay meaning.
            self.take(width,'union-tag')
            if self.peek()==255:self.take(1,'null-wrapper');return
            self.header(4)
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(3):self.take(4,'anonymous-scalar32')
            return
        # FC/FD/FE are authenticated only in their extended encodings.
        if (width==1 and tag>=251) or name not in _ACTION_MEMBER_COUNTS:raise Unsupported(self.source,self.pos,'supported current union tag'+union_tags.unavailable_note(),tag,'union-tag')
        self.take(width,'union-tag')
        if self.peek()==255:self.take(1,'null-wrapper');return
        self.header(_ACTION_MEMBER_COUNTS[name])
        self.take(1,'anonymous-nonzero-byte')
        for _ in range(3):self.take(4,'anonymous-scalar32')
        if name=='Core_CastPlungingAttack_Data':
            # The selected header-five reader consumes the existing bounded
            # TargetSettings profile after its anonymous byte/DWORD prefix.
            self.target_profile();return
        if name=='Core_AirborneAction_AirborneActionData':
            # The selected header-16 reader follows the static source order:
            # EffectActionCfg, DWORD, DirectionSettings, two BlackboardDouble
            # profiles, direct bytes/words, then two TargetSettings profiles.
            self.effect_configuration_profile()
            self.take(4,'anonymous-scalar32')
            self.direction_profile()
            self.scalar_payload();self.scalar_payload()
            self.take(1,'anonymous-byte')
            self.take(4,'anonymous-raw4')
            self.take(1,'anonymous-byte')
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.take(4,'anonymous-raw4')
            self.target_profile()
            return
        if name=='Core_ComboCacheAction_Data':
            start=self.pos
            for _ in range(max(0,self.count(1,nullable=True))):self.combo_cache_mapping_profile()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-combo-cache-mapping-list'));return
        if name=='Core_SpeedupAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte')
            self.paired_payload();self.scalar_payload()
            list_start=self.pos
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.keyword_edit_profile()
            self.records.append(dict(start=list_start,end=self.pos,kind='anonymous-keyword-edit-list'))
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.target_profile();self.target_profile();return
        if name=='Core_Conditions_CompareDeckAttr_Data':
            # The common byte/three-DWORD prefix above covers members 1-4.
            # Members 5-6 and 8 are direct scalar32 reads; the nested scalar
            # and target profiles retain their own null and unsupported states.
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.scalar_payload()
            self.take(4,'anonymous-scalar32')
            self.scalar_payload()
            self.target_profile();return
        if name=='Core_TagQueryListenerAction_Data':
            # The selected header-nine reader consumes two existing bounded
            # profiles between its shared prefix and anonymous byte/DWORD tail.
            self.query_profile();self.sequence(depth)
            self.take(1,'anonymous-byte')
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32')
            return
        if name=='Core_SetStrafeModeAction_Data':
            # The selected header-ten reader ends with a bounded TargetSettings
            # and a required opaque four-byte slot.
            self.take(1,'anonymous-byte');self.take(1,'anonymous-byte')
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.take(4,'anonymous-raw4')
            return
        if name=='Core_SetWaterDroneItemModePersistLiquidIdAction_Data':
            # The selected header-six reader reuses the bounded paired-byte
            # payload and TargetSettings profiles after its shared prefix.
            self.paired_payload()
            self.target_profile()
            return
        if name=='Core_TyphoeaIsInShootingRangeAction_Data':
            # The selected header-six reader consumes two independent bounded
            # byte payloads after its shared byte/three-DWORD prefix.
            self.byte_payload()
            self.byte_payload()
            return
        if name=='Core_SetDamageTagImmuneRule_Data':
            # The selected header-six reader consumes GameplayTagQuery and
            # TargetSettings profiles after its shared byte/three-DWORD prefix.
            self.query_profile()
            self.target_profile()
            return
        if name=='Core_LockCameraAimAction_LockCameraAimActionData':
            # The header-54 reader has already consumed members 1-4 above.
            # Preserve the remaining direct source order; static type contexts
            # select bounded profiles, not field names or camera semantics.
            self.take(1,'anonymous-byte')
            self.take(4,'anonymous-raw4')
            self.curve_profile()
            self.take(4,'anonymous-scalar32')
            self.take(4,'anonymous-raw4')
            self.curve_profile()
            self.take(4,'anonymous-scalar32')
            self.take(4,'anonymous-raw4')
            for _ in range(3):self.take(1,'anonymous-byte')
            for _ in range(2):self.take(4,'anonymous-raw4')
            for _ in range(3):self.take(1,'anonymous-byte')
            self.take(24,'anonymous-raw24')
            for _ in range(2):self.take(1,'anonymous-byte')
            self.take(4,'anonymous-raw4')
            self.scalar_payload()
            self.take(4,'anonymous-raw4')
            self.scalar_payload()
            for _ in range(2):self.take(4,'anonymous-raw4')
            for _ in range(2):self.take(1,'anonymous-byte')
            self.take(4,'anonymous-raw4')
            self.scalar_payload()
            self.take(4,'anonymous-raw4')
            self.scalar_payload()
            self.take(4,'anonymous-raw4')
            self.scalar_payload()
            self.take(1,'anonymous-byte')
            for _ in range(2):self.take(4,'anonymous-raw4')
            for _ in range(3):self.take(12,'anonymous-raw12')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            for _ in range(4):self.take(1,'anonymous-byte')
            self.take(4,'anonymous-raw4')
            self.target_profile()
            self.target_profile()
            for _ in range(2):self.take(1,'anonymous-byte')
            return
        if name=='Core_ForceTriggerWeakness_Data':
            # The selected header-six reader consumes two independent bounded
            # TargetSettings profiles after its shared byte/three-DWORD prefix.
            self.target_profile()
            self.target_profile()
            return
        if name=='Core_ConvertToTargetContext_Data':
            self.vector_payload();self.target_profile()
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-raw4');self.take(4,'anonymous-scalar32');return
        if name=='Core_PullAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte')
            start=self.pos
            for _ in range(max(0,self.count(1,reserve=24,nullable=True))):self.pull_attenuation_profile()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-pull-attenuation-list'))
            self.target_profile()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-raw4');self.take(4,'anonymous-raw4');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32');self.take(4,'anonymous-raw4')
            self.target_profile();self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_GainCostAction_Data':
            self.cost_profile()
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');return
        if name=='Core_Conditions_CheckProfession_Data':self.target_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_SpawnEnemyAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32');self.take(16,'anonymous-raw16')
            for _ in range(max(0,self.count(1,reserve=17,nullable=True))):self.input_profile()
            self.target_profile();self.byte_payload();self.byte_payload()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.take(4,'anonymous-raw4')
            self.take(1,'anonymous-nonzero-byte');self.target_profile();return
        if name=='Core_BroadcastAlertToCharactersAction_BroadcastAlertToCharactersActionData':
            self.skill_alert_profile()
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-raw4');self.target_profile();return
        if name=='Core_EnableSpecialAim_Data':
            self.special_aim_shape_list();self.target_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_BreakoutAction_Data':self.byte_payload();self.take(4,'anonymous-scalar32');return
        if name=='Core_CharWeaponAnimationAction_CharWeaponAnimationActionData':
            for _ in range(2):self.take(1,'anonymous-byte')
            self.animator_param_profile();self.animator_param_profile()
            self.take(4,'anonymous-raw4');self.take(1,'anonymous-byte')
            self.animator_param_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_Conditions_CheckBuffFromSource_Data':
            self.single_payload();self.target_profile();self.target_profile()
            self.take(1,'anonymous-byte');self.scalar_payload();return
        if name=='Core_FlowTextAction_Data':
            self.take(16,'anonymous-raw16');self.take(1,'anonymous-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.byte_payload();return
        if name=='Core_BombTouchLayerAction_Data':
            self.sequence(depth);self.sequence(depth);self.effect_configuration_profile()
            self.take(1,'anonymous-byte');self.take(4,'anonymous-scalar32');self.take(4,'anonymous-float32-bits')
            self.target_profile();self.take(4,'anonymous-scalar32');self.sequence(depth)
            self.effect_configuration_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_LaunchUpwardAction_Data':
            self.effect_configuration_profile();self.take(4,'anonymous-scalar32');self.direction_profile()
            self.scalar_payload();self.scalar_payload();self.take(4,'anonymous-float32-bits')
            self.take(4,'anonymous-scalar32');self.target_profile();self.take(4,'anonymous-float32-bits')
            self.target_profile();self.take(1,'anonymous-byte');return
        if name=='Core_TogglableAction_Data':self.sequence(depth);self.sequence(depth);return
        if name=='Core_CreateAdditionalBattleShape_Data':
            self.take(4,'anonymous-float32-bits')
            for _ in range(3):self.take(1,'anonymous-byte')
            self.collider_shape_profile();self.target_profile();return
        if name=='Core_CreateDynamicBattleShape_Data':
            self.take(4,'anonymous-float32-bits');self.take(4,'anonymous-float32-bits')
            self.take(4,'anonymous-scalar32');return
        if name=='Core_VoiceInterruptAction_VoiceInterruptActionData':self.take(4,'anonymous-scalar32');self.take(1,'anonymous-byte');return
        if name=='Core_VoiceTriggerAction_VoiceTriggerActionData':
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');self.byte_payload()
            self.target_profile();return
        if name=='Core_EventListenerAction_Data':self.ability_action_map_collection_profile(depth);return
        if name=='Core_BindBountyEnemyAction_Data':self.paired_payload();return
        if name=='Core_IgniteAction_Data':
            self.target_profile();self.take(4,'anonymous-scalar32');self.byte_payload();self.target_profile();return
        if name=='Core_TyphoeaArcheryChipDataAction_Data':
            for _ in range(4):self.byte_payload()
            for _ in range(5):self.take(1,'anonymous-byte')
            self.byte_payload();self.byte_payload();self.take(1,'anonymous-byte')
            self.byte_payload();self.byte_payload();return
        if name=='Core_ChangeGeneralAbilityButton_Data':
            self.single_payload();self.byte_payload();self.take(4,'anonymous-scalar32');return
        if name=='Core_StoreBuffCount_Data':
            self.byte_payload();self.byte_payload();self.target_profile();self.take(1,'anonymous-byte');return
        if name=='Core_SetAnimTimeScaleAction_Data':
            self.target_profile();self.scalar_payload();return
        if name=='Core_ContinuousFindTargetAction_Data':
            self.direction_profile();self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-byte');self.byte_payload()
            self.selector_profile();self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(1,'anonymous-byte');self.take(1,'anonymous-byte')
            self.take(4,'anonymous-float32-bits');return
        if name in ('Core_TriggerSpellBurstEventAction_Data','Core_OnSpellInflictionStart_Data'):self.take(4,'anonymous-scalar32');return
        if name=='Core_AddAIMarkerAction_Data':
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.target_profile();self.take(1,'anonymous-byte')
            return
        if name=='Core_SetWeaknessAction_Data':
            self.scalar_payload();self.scalar_payload();self.take(1,'anonymous-byte')
            self.sequence(depth);self.scalar_payload();self.take(1,'anonymous-byte');self.scalar_payload()
            return
        if name=='Core_SelfRotateAction_Data':
            self.direction_profile()
            for _ in range(5):self.take(1,'anonymous-byte')
            self.byte_payload()
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.take(4,'anonymous-raw-float32');self.take(4,'anonymous-scalar32')
            self.target_profile();self.take(1,'anonymous-byte')
            return
        if name=='Core_RefrainObtainUsp_Data':
            self.take(1,'anonymous-byte');self.tag_list_profile(reserve=1);self.target_profile()
            return
        if name=='Core_CharWeaponVisibleAction_CharWeaponVisibleActionData':
            for _ in range(3):self.take(1,'anonymous-byte')
            self.weapon_vfx_profile();self.take(1,'anonymous-byte');self.take(4,'anonymous-scalar32')
            return
        if name=='Core_SetAnimatorParamAction_Data':
            self.take(1,'anonymous-byte')
            self.animator_param_profile();self.animator_param_profile();self.byte_payload()
            return
        if name=='Core_SaveBuffLifeTime_Data':
            self.target_profile();self.finder_profile();self.byte_payload()
            return
        if name=='Core_MoveGaitAction_Data':
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_ForceHideHeadBarAction_Data':
            self.take(1,'anonymous-byte')
            self.target_profile()
            return
        if name=='Core_TriggerCharSpellInflictionEvent_Data':
            self.target_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_TeleportAction_Data':
            self.sequence(depth)
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-raw4');self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_MoveToAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(6):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            # Unity Vector3 is raw12 here; the following blackboard vector is variable.
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32')
            self.vector_payload();self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.take(4,'anonymous-raw4');self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            for _ in range(3):self.scalar_payload()
            self.curve_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(4,'anonymous-raw4');self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.scalar_payload()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload_curve_profile();self.scalar_payload_curve_profile();return
        if name=='Core_RecoverLockOnEndIfNoLockAction_Data':
            self.target_profile();return
        if name=='Core_ChangeSkillAction_Data':
            self.scalar_payload();self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.target_profile();self.take(1,'anonymous-nonzero-byte');self.byte_payload();return
        if name=='Core_IgniteBuffTextAction_Data':
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.take(8,'anonymous-inline8');self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.byte_payload();return
        if name in ('Core_SkillAffixAction_Data','Core_RefreshBuffAttrModifierValue_Data'):return
        if name=='Core_RecoverPoiseAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.effect_configuration_profile()
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.calculation_profile();self.target_profile();return
        if name in ('Core_VulnerableAction_Data','Core_EnhancedAction_Data','Core_ShelterAction_Data','Core_WeakAction_Data','Core_SlowAction_Data'):
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.paired_payload();self.scalar_payload()
            # Header13 actions end at the second target; header14 adds a DWORD.
            for _ in range(max(0,self.count(1,reserve=4 if name in ('Core_ShelterAction_Data','Core_WeakAction_Data','Core_SlowAction_Data') else 8,nullable=True))):self.keyword_edit_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.target_profile();self.target_profile()
            if name not in ('Core_ShelterAction_Data','Core_WeakAction_Data','Core_SlowAction_Data'):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_HitStopAction_Data':
            self.take(4,'anonymous-scalar32');self.target_profile();self.byte_payload();self.curve_profile()
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_OnSpellAbnormalStartFinish_Data':
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_GetAITransDataAction_Data':
            self.byte_payload();self.byte_payload();return
        if name=='Core_SwitchModeAction_Data':
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload();self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_AuraAction_Data':
            self.sequence(depth);self.sequence(depth);self.byte_payload();self.target_profile()
            self.take(4,'anonymous-scalar32');self.scalar_bytes_profile()
            for _ in range(max(0,self.count(1,reserve=31,nullable=True))):self.buff_input_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.direction_profile();self.scalar_payload()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.collider_shape_profile();self.target_filter_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_SetSuperArmorAction_Data':
            self.scalar_flag_payload();self.scalar_flag_payload();self.target_profile();return
        if name=='Core_Conditions_CheckProjectileIgnoreImmuneLevel_Data':
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if name in ('Core_SetFirstDashParam_Data','Core_Conditions_CheckProjectileInPerfectDodgeCd_Data'):
            self.take(1,'anonymous-byte');return
        if name=='Core_RecordBattleDetails_Data':
            self.take(4,'anonymous-scalar32');return
        if name=='Core_RecoverDashEnergy_Data':
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();return
        if name in ('Core_CostAtbRefreshLongestSkillCd_Data','Core_ModifyResilienceDecreaseFactor_Data'):
            self.scalar_payload();return
        if name=='Core_Condition_CheckSquadInFight_Data':
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_Conditions_OrConditionAction_Data':
            for _ in range(max(0,self.count(1,nullable=True))):self.sequence(depth+1)
            return
        if name=='Core_BlowOffAction_Data':
            self.target_profile();self.scalar_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.direction_profile();self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();return
        if name=='Core_DispelAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.target_profile();self.query_profile();return
        if name=='Core_RandomAction_Data':
            self.scalar_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32');self.byte_payload();return
        if name=='Core_AddDynamicCcsAction_AddDynamicCcsActionData':
            for _ in range(2):self.vector_payload()
            for _ in range(4):self.scalar_payload()
            for _ in range(2):
                self.curve_profile();self.take(4,'anonymous-scalar32');self.scalar_payload()
            self.take(4,'anonymous-raw4');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.byte_payload();self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=31,nullable=True))):self.counted_payload_scalars_profile()
            self.curve_profile();self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=25,nullable=True))):self.counted_payload_scalars_profile()
            self.vector_payload()
            for _ in range(6):self.scalar_payload()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.curve_profile();self.vector_payload()
            for _ in range(13):self.take(1,'anonymous-nonzero-byte')
            return
        if name=='View_AddCameraControlStateAction_AddCameraControlStateActionData':
            self.curve_profile();self.take(4,'anonymous-scalar32');self.take(4,'anonymous-raw4')
            self.curve_profile();self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(4,'anonymous-raw4')
            self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            for _ in range(max(0,self.count(4,reserve=6,nullable=True))):self.byte_payload()
            for _ in range(6):self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_EnablePartsAction_Data':
            self.take(1,'anonymous-nonzero-byte')
            self.byte_profile();self.scalar_pair_flags_profile();self.query_profile()
            self.byte_profile();self.scalar_pair_flags_profile()
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_SetGeneralAbilityCd_Data':
            self.scalar_payload();self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_ClearProjectileAction_Data':
            self.scalar_payload();self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(4,reserve=1,nullable=True))):self.byte_payload()
            self.target_profile();return
        if name=='Core_SpendAtbAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.target_profile();self.scalar_payload()
            return
        if name=='Core_ChannelingAction_Data':
            self.sequence(depth);self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32');return
        if name=='Core_TimeDilationAction_Data':
            self.byte_payload();self.scalar_payload()
            for _ in range(max(0,self.count(1,reserve=21,nullable=True))):self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=16,nullable=True))):self.target_profile()
            self.scalar_payload()
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.curve_profile();self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_ReadSkillSettingData_Data':
            for _ in range(max(0,self.count(1,nullable=True))):self.scalar_target_payload_profile()
            return
        if name=='Core_SaveBuffStackNum_Data':
            self.single_payload();self.target_profile();self.byte_payload();return
        if name=='Core_TriggerLiinoUIEvent_Data':
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.scalar_payload();return
        if name=='Core_SaveCharTypeId_Data':
            self.byte_payload();self.target_profile();return
        if name=='Core_TriggerComboSkillAction_Data':
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.assignment_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(3):self.target_profile()
            return
        if name=='Core_CheckDamageTag_Data':
            self.take(4,'anonymous-scalar32');self.tag_elements();return
        if name=='Core_TriggerCustomAbilityEvent_Data':
            self.paired_payload();self.scalar_payload();self.target_profile();self.target_profile();return
        if name=='Core_Conditions_CheckSkillInterruptReason_Data':
            for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_Conditions_CheckOverHeal_Data':
            for _ in range(3):self.byte_payload()
            return
        if name=='Core_Conditions_CheckHealTag_Data':self.query_profile();return
        if name=='Core_Conditions_ModifyCollectedBuffBbValue_Data':
            self.scalar_payload();self.byte_payload();self.scalar_payload();self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_Conditions_CheckUsp_Data':
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.scalar_payload();return
        if name=='Core_NotifyCharPassiveUIAction_Data':self.target_profile();self.scalar_payload();return
        if name in ('Core_StoreSkillDamageType_Data','Core_ShowSquadTipsAction_Data'):self.byte_payload();return
        if name=='Core_SwitchAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();start=self.pos
            for _ in range(max(0,self.count(1,nullable=True))):self.sequence_scalar_profile(depth)
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-sequence-scalar-list'));return
        if name=='Core_CurveEvaluateFloat_Data':
            self.byte_payload();self.curve_profile();self.scalar_payload()
            self.byte_payload();self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_SaveTargetDistanceAction_Data':
            self.byte_payload();self.target_profile();self.target_profile();return
        if name=='Core_SaveShieldValueToBB_Data':
            self.byte_payload();self.target_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_SetHpFloor_Data':
            self.sequence(depth);self.scalar_payload();self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_PlayAnimationAction_PlayAnimationActionData':
            self.byte_payload()
            for _ in range(4):self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.sequence(depth)
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_ChangeSeasonTowerEnergyAction_Data':
            self.scalar_payload();return
        if name=='Core_AddTagAction_Data':
            self.paired_payload();self.target_profile();self.tag_elements(reserve=1)
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_AddTagToEntities_Data':
            # Tag 0x0C independently selects the header-eight AddTagToEntities
            # reader. Its selected direct list is List<GameplayTag>; reserve
            # the required terminal byte while keeping the list profile finite.
            self.paired_payload();self.target_profile();self.tag_elements(reserve=1)
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_CountShieldUIAction_Data':
            self.scalar_payload();self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.target_profile();return
        if name=='Core_EnemyHurtAnimAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile();self.curve_profile()
            self.take(1,'anonymous-nonzero-byte');self.take(1,'anonymous-nonzero-byte')
            self.direction_profile();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.scalar_flag_payload();self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload();self.scalar_payload();return
        if name=='Core_CheckDamageTransferredSource_Data':
            self.byte_payload();self.query_profile();return
        if name=='Core_StoreEntityProperty_Data':
            self.scalar_payload();self.scalar_payload();self.byte_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_Conditions_CheckWeaponTypeCondition_Data':
            self.target_profile();self.take(4,'anonymous-scalar32');return
        if name=='Core_SaveDamageContext_Data':
            self.byte_payload();self.take(4,'anonymous-scalar32');return
        if name=='Core_CompareString_Data':
            self.paired_payload();self.paired_payload();return
        if name=='Core_AbilityActions_FinishGlobalBuffAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');start=self.pos
            for _ in range(max(0,self.count(1,reserve=1,nullable=True))):self.single_payload()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-single-payload-list'))
            self.take(1,'anonymous-nonzero-byte');return
        if name=='Core_SaveValueFromAIBlackboard_Data':
            self.byte_payload();self.target_profile()
            for _ in range(4):self.byte_payload()
            self.take(4,'anonymous-scalar32');return
        if name=='Core_BlowOffCharacterAction_Data':
            self.target_profile();self.scalar_flag_payload();self.scalar_payload()
            self.direction_profile();self.scalar_payload();self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();return
        if name=='Core_RecoverFromPoiseBreak_Data':
            self.target_profile();return
        if name=='Core_Conditions_CheckEnemyRank_Data':
            self.take(4,'anonymous-scalar32');self.target_profile();return
        if name=='Core_InterruptAction_Data':
            self.target_profile();self.target_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_StoreAttributeValue_Data':
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.scalar_payload()
            self.byte_payload();self.scalar_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.target_profile();self.take(1,'anonymous-nonzero-byte');return
        if name in ('Core_Conditions_SaveHealValue_Data','Core_SaveAtbObtainValue_Data','Core_SaveCollectedBuffBbValue_Data'):
            self.byte_payload();self.byte_payload();return
        if name=='Core_ShowHideActorAction_ShowHideActorData':
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile();return
        if name=='Core_SpellInfliction_Data':
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.target_profile();return
        if name=='Core_Conditions_CheckSkillDamageType_Data':
            start=self.pos
            for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar32-list'));return
        if name=='Core_CreateGlobalBuffAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            start=self.pos
            for _ in range(max(0,self.count(1,reserve=1,nullable=True))):self.global_input_profile()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-global-input-list'))
            self.target_profile();return
        if name=='Core_CastSkill_Data':
            self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.paired_payload();self.take(1,'anonymous-nonzero-byte');self.target_profile();return
        if name=='Core_CheckDistanceCondition_Data':
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.target_profile();return
        if name in ('Core_Conditions_CheckDamageType_Data','Core_AchieveSpecialGameEventAction_Data','Core_Conditions_CheckDamageTypeMask_Data'):self.take(4,'anonymous-scalar32');return
        if name in ('Core_Conditions_CheckSkillCastId_Data','Core_Conditions_CheckHasDamageSkillCastId_Data','Core_SaveDamageSkillCastId_Data'):return
        if name=='Core_SetBuffDurationAction_Data':
            self.finder_profile();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile();self.scalar_payload()
            return
        if name in ('Core_CheckConsumeBuffLayer_Data','Core_CheckBuffEnhanceChangedLayer_Data'):
            self.take(4,'anonymous-scalar32');self.scalar_payload();self.byte_payload()
            return
        if name=='Core_Conditions_CheckEntityNum_Data':
            self.target_profile();self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.byte_payload()
            return
        if name=='Core_MergeTargetAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            start=self.pos
            for _ in range(max(0,self.count(1,nullable=True))):self.target_profile()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-list'))
            return
        if name=='Core_CharHurtAnimAction_Data':
            self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.curve_profile()
            self.take(1,'anonymous-nonzero-byte');self.direction_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            # The concrete final reader consumes four source bytes, even
            # though its managed wrapper name contains BlackboardDouble.
            self.scalar_payload()
            return
        if name=='Core_Conditions_CheckTargetContains_Data':
            self.target_profile();self.target_profile()
            return
        if name=='Core_SpawnInteractiveGoldCoin_Data':
            self.scalar_payload();self.target_profile()
            return
        if name=='Core_CameraImpulseAction_CameraImpulseActionData':
            self.byte_payload();self.take(1,'anonymous-nonzero-byte')
            self.impulse_profile();self.take(4,'anonymous-scalar32')
            self.take(12,'anonymous-raw12')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.target_profile()
            return
        if name=='Core_Conditions_CheckObtainAtbType_Data':
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):
                start=self.pos
                for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
                self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar32-list'))
            return
        if name=='Core_ForEachAction_Data':
            self.sequence(depth);self.target_profile()
            return
        if name=='Core_LaunchProjectile_Data':
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,nullable=True))):self.assignment_profile()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32')
            self.take(12,'anonymous-raw12');self.take(12,'anonymous-raw12')
            self.take(4,'anonymous-scalar32');self.take(12,'anonymous-raw12')
            self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,nullable=True))):self.target_bytes_profile()
            self.byte_payload();self.byte_payload();self.target_profile()
            for _ in range(3):self.byte_payload()
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.target_profile();self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_SendBattleSignalToLevel_Data':
            self.scalar_payload();self.paired_payload()
            return
        if name=='Core_GetTargetBuffBBAdvanced_Data':
            self.byte_payload();self.finder_profile();self.byte_payload();self.target_profile()
            return
        if name=='Core_Conditions_CheckCustomAbilityEvent_Data':
            self.paired_payload();self.byte_payload()
            return
        if name=='Core_Conditions_Probablity_Data':
            self.scalar_payload()
            return
        if name=='Core_Conditions_CheckSpellInflictionType_Data':
            self.take(4,'anonymous-scalar32');self.byte_payload()
            return
        if name=='Core_AddGlobalCDTimer_Data':
            self.byte_payload();self.scalar_payload();self.target_profile()
            return
        if name=='Core_NotNextCheckAction_Data':return
        if name=='Core_Conditions_CheckSuperArmor_Data':
            self.target_profile();self.take(4,'anonymous-scalar32');self.scalar_payload()
            return
        if name=='Core_SpellInflictionOnChar_Data':
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32')
            self.target_profile();self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if name in ('Core_Conditions_CheckTargetsEqual_Data','Core_ForceTargetInFightAction_Data'):
            self.target_profile();self.target_profile()
            return
        if name=='Core_FinishOwnerAction_Data':
            self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_Conditions_CheckTagMatch_Data':
            self.target_profile();self.query_profile()
            return
        if name=='Core_CreateTimedMarker_Data':
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.paired_payload()
            self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_ObtainCostAction_Data':
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.scalar_payload()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            return
        if name=='Core_SetSkillCdAtOnce_Data':
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            return
        if name=='Core_SpawnAbilityEntity_Data':
            self.byte_payload();self.byte_payload();self.take(4,'anonymous-scalar32');self.byte_payload()
            self.target_profile();self.direction_profile()
            for _ in range(4):self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=64,nullable=True))):self.assignment_profile()
            self.take(1,'anonymous-nonzero-byte');self.target_profile();self.take(4,'anonymous-scalar32')
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(16,'anonymous-raw16')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            for _ in range(max(0,self.count(4,reserve=9,nullable=True))):self.byte_payload()
            for _ in range(9):self.take(1,'anonymous-nonzero-byte')
            return
        if name in ('Core_Conditions_CheckHp_Data','Core_Conditions_CheckPoiseValue_Data'):
            self.take(4,'anonymous-scalar32');self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            return
        if name=='Core_EffectAction_EffectActionData':
            self.byte_payload();self.target_profile();self.effect_configuration_profile();self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            for _ in range(5):self.take(1,'anonymous-nonzero-byte')
            self.byte_payload();self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_DamageAction_DamageActionData':
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.damage_unit_profile()
            self.target_profile();self.hit_environment_profile()
            self.take(1,'anonymous-nonzero-byte');self.target_profile()
            return
        if name=='Core_AbilityActions_FinishBuffAction_Data':
            for _ in range(max(0,self.count(1,reserve=7,nullable=True))):self.single_payload()
            self.target_profile();self.target_profile()
            self.take(1,'anonymous-nonzero-byte');self.scalar_payload();self.target_profile()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_Conditions_CheckBuffStackNum_Data':
            self.single_payload();self.target_profile()
            self.take(4,'anonymous-scalar32');self.scalar_payload()
            return
        if name=='Core_Conditions_CheckTimedMarkerCondition_Data':
            self.byte_payload();self.target_profile();self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            return
        if name in ('Core_Conditions_CheckMainCharacterCondition_Data','Core_ShakeCountShieldUIAction_Data','Core_AbilityActions_InterruptCurSkillAction_Data'):
            self.target_profile()
            return
        if name=='Core_FindTargetAction_FindTargetActionData':
            self.direction_profile()
            self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.selector_profile()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32');self.byte_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            return
        if name in ('Core_Conditions_CheckSkillType_Data','Core_CheckOriginSkillType_Data'):
            self.take(4,'anonymous-scalar32')
            if name=='Core_Conditions_CheckSkillType_Data':
                for _ in range(2):self.take(1,'anonymous-nonzero-byte')
                self.target_profile()
            start=self.pos
            # Conditional list framing plus an independently joined element
            # source reader; not a live generic formatter-selection claim.
            for _ in range(max(0,self.count(4,nullable=True))):self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar32-list'))
            return
        if name=='Core_CheckBuffStackNumAdvanced_Data':
            self.finder_profile()
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            return
        if name=='Core_PlaySoundAction_PlaySoundActionData':
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.byte_payload();self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.target_profile()
            for _ in range(4):self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            return
        if name=='Core_HealAction_Data':
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.effect_configuration_profile();self.calculation_profile()
            self.take(4,'anonymous-scalar32');self.tag_list_profile();self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            self.target_profile();self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_DebugPrintAction_Data':
            self.byte_payload();self.take(16,'anonymous-raw16');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.target_profile()
            return
        if name=='Core_PauseBuffTime_Data':
            self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_CheckGlobalCDTimerAction_Data':
            self.byte_payload()
            self.target_profile()
            return
        if name=='Core_Conditions_CheckObjectTypeMatch_Data':
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            return
        if name=='Core_SimpleCalcBBAction_Data':
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.scalar_payload()
            self.scalar_payload()
            return
        if name=='Core_SaveBuffStackNumAdvanced_Data':
            self.finder_profile()
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_Conditions_CheckPhysicalInflictionType_Data':
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            return
        if name in ('Core_Conditions_CheckDamageDecorateMask_Data','Core_Conditions_CheckDamageIgnoreImmuneLevel_Data'):
            self.take(4,'anonymous-scalar32')
            self.take(8,'anonymous-scalar64')
            return
        if name in ('Core_CreateBuffAction_Data','Core_CreateBuffAttachingSkill_Data'):
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_bytes_profile()
            for _ in range(max(0,self.count(1,reserve=20,nullable=True))):self.input_profile()
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(4,reserve=6,nullable=True))):self.byte_payload()
            for _ in range(5):self.take(1,'anonymous-nonzero-byte')
            self.target_profile()
            return
        if name in ('Core_Conditions_CheckBuffIdInContext_Data','Core_Conditions_CheckBuffIdInContextAdvanced_Data'):
            self.byte_payload()
            for _ in range(max(0,self.count(1,reserve=5,nullable=True))):
                if name=='Core_Conditions_CheckBuffIdInContext_Data':self.single_payload()
                else:self.paired_payload()
            self.take(4,'anonymous-scalar32')
            self.query_profile()
            return
        if name=='Core_FinishBuffAdvanced_Data':
            self.target_profile()
            self.finder_profile()
            self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            self.target_profile()
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            return
        if name=='Core_RaiseTrainLevelEvent_Data':
            self.paired_payload()
            self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte')
            self.paired_payload()
            return
        if name=='Core_CompareFloat_Data':
            self.take(4,'anonymous-scalar32')
            for _ in range(2):self.scalar_payload()
            return
        if name=='Core_ModifyDynamicBlackboard_Data':
            self.take(4,'anonymous-scalar32')
            self.target_profile()
            self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.scalar_payload()
            return
        if name=='Core_Conditions_CheckSkillId_Data':
            start=self.pos
            # Null element is one byte. Bound count before iterating, even
            # though a non-null member-three element needs at least ten bytes.
            for _ in range(max(0,self.count(1,nullable=True))):self.paired_payload()
            self.records.append(dict(start=start,end=self.pos,kind='anonymous-paired-payload-list'))
            return
        if name != IF_ELSE_ACTION_NAME:
            raise Unsupported(self.source,self.pos,
                              'explicit selected action body',tag,'union-tag')
        self.take(1,IF_ELSE_ACTION_READ_KINDS[4])
        for kind in IF_ELSE_ACTION_READ_KINDS[5:]:
            if kind != 'SequenceActionData':
                raise FrameError(self.source,self.pos,'SequenceActionData',kind,'internal-range')
            self.sequence(depth)

    def ability_action_map_collection_profile(self,depth):
        # AbilityActionMap puts its DWORD before the Sequence array. The
        # separately framed BuffActionMap has the opposite source order.
        start=self.pos
        for _ in range(max(0,self.count(1,nullable=True))):
            item_start=self.pos
            if self.peek()==255:self.take(1,'null-ability-action-map')
            else:
                self.header(2)
                self.take(4,'anonymous-map-scalar32')
                for _ in range(max(0,self.count(1,nullable=True))):
                    self.sequence(depth)
            self.records.append(dict(start=item_start,end=self.pos,kind='anonymous-ability-action-map'))
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-ability-action-map-list'))

    def combo_cache_mapping_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-combo-cache-mapping')
        else:
            self.header(6);self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
            self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-combo-cache-mapping'))

    def pull_attenuation_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-pull-attenuation-profile')
        else:
            self.header(2);self.take(4,'anonymous-raw4');self.scalar_flag_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-pull-attenuation-profile'))

    def cost_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-cost-profile')
        else:
            self.header(3);self.take(4,'anonymous-raw4')
            self.take(4,'anonymous-scalar32');self.take(4,'anonymous-raw4')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-cost-profile'))

    def skill_alert_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-skill-alert')
        else:
            self.header(9)
            for _ in range(3):self.take(4,'anonymous-raw4')
            self.take(4,'anonymous-scalar32')
            for _ in range(4):self.take(4,'anonymous-raw4')
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-skill-alert-profile'))

    def special_aim_shape_list(self):
        start=self.pos
        count=self.count(1,reserve=5,nullable=True)
        for _ in range(max(0,count)):self.special_aim_shape()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-special-aim-shape-list'))

    def special_aim_shape(self):
        start=self.pos;lead=self.peek()
        if lead==255:self.take(1,'null-special-aim-shape');return
        width=3 if lead==250 else 1
        if width>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':width},{'remaining':self.limit-self.pos},'truncated')
        tag=struct.unpack_from('<H',self.data,self.pos+1)[0] if width==3 else lead
        if tag!=0:raise Unsupported(self.source,self.pos,0,tag,'special-aim-shape-tag')
        self.take(width,'special-aim-shape-tag')
        if self.peek()==255:self.take(1,'null-special-aim-sector')
        else:
            self.header(3);self.take(4,'anonymous-scalar32')
            self.scalar_payload();self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-special-aim-shape',tag=tag))

    def byte_payload(self,*,reserve=0):
        start=self.pos
        n=self.count(1,reserve=reserve,nullable=True)
        # The selected native helper advances by the supplied byte length.
        # Do not substitute standard MemoryPack UTF-16/negative-length layouts
        # or claim decoder parity; even non-UTF8 bytes are structurally valid.
        if n>0:self.take(n,'anonymous-length-prefixed-bytes')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-byte-payload',isNull=n==-1))

    def paired_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-paired-payload')
        else:
            self.header(3)
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-paired-payload'))

    def scalar_flag_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-flag-payload')
        else:
            self.header(4);self.byte_payload();self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-flag-payload'))

    def scalar_target_payload_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-target-payload')
        else:
            self.header(4);self.scalar_payload();self.byte_payload()
            self.target_profile();self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-target-payload'))

    def single_payload(self):
        # A member-one wrapper is a separate serialized byte from its payload
        # length. Neither a value-type name nor an output slot gives its width.
        start=self.pos
        if self.peek()==255:self.take(1,'null-single-payload')
        else:
            self.header(1)
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-single-payload'))

    def null_profile(self,kind):
        actual=self.peek()
        if actual!=255:
            raise Unsupported(self.source,self.pos,'null-only '+kind+' profile',actual,'nested-profile')
        self.take(1,'null-'+kind)

    def scalar_bytes_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-bytes-profile')
        else:
            self.header(2)
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-bytes-profile'))

    def target_bytes_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-target-bytes-profile')
        else:
            self.header(2)
            self.target_profile()
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-bytes-profile'))

    def assignment_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-assignment-profile')
        else:
            self.header(6)
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-assignment-profile'))

    def global_input_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-global-input-profile')
        else:
            self.header(3);self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=1,nullable=True))):self.assignment_profile()
            self.single_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-global-input-profile'))

    def keyword_edit_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-keyword-edit-profile')
        else:
            self.header(3)
            for _ in range(max(0,self.count(4,reserve=5,nullable=True))):self.byte_payload()
            self.take(4,'anonymous-scalar32');self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-keyword-edit-profile'))

    def buff_input_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-buff-input-profile')
        else:
            self.header(3);self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.assignment_profile()
            self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-buff-input-profile'))

    def target_filter_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-target-filter-profile')
        else:
            self.header(10)
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.query_profile();self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-filter-profile'))

    def input_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-input-profile')
        else:
            self.header(5)
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(max(0,self.count(1,reserve=9,nullable=True))):self.assignment_profile()
            self.byte_payload()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-input-profile'))

    def collider_shape_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-collider-shape-profile')
        else:
            self.header(16)
            for _ in range(2):
                self.take(12,'anonymous-raw12')
                for _ in range(3):self.byte_payload()
            for _ in range(2):
                self.take(4,'anonymous-scalar32');self.byte_payload()
            self.take(12,'anonymous-raw12');self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-collider-shape-profile'))

    def counted_payload_scalars_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-counted-payload-scalars-profile')
        else:
            self.header(1)
            for _ in range(max(0,self.count(1,nullable=True))):self.byte_payload_scalars_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-counted-payload-scalars-profile'))

    def byte_payload_scalars_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-byte-payload-scalars-profile')
        else:
            self.header(5);self.take(1,'anonymous-byte');self.byte_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(4,'anonymous-raw4')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-byte-payload-scalars-profile'))

    def byte_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-byte-profile')
        else:
            self.header(1);self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-byte-profile'))

    def scalar_pair_flags_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-pair-flags-profile')
        else:
            self.header(6)
            for _ in range(2):
                self.take(4,'anonymous-scalar32');self.scalar_payload()
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-pair-flags-profile'))

    def query_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-query-profile')
        else:
            self.header(2)
            self.take(4,'anonymous-scalar32')
            # Selected consumer copies and advances count*4 bytes. Bound the
            # multiplication by remaining input; do not emulate native overflow.
            for _ in range(max(0,self.count(4,nullable=True))):
                self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-query-profile'))

    def finder_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-finder-profile')
        else:
            self.header(3)
            for _ in range(max(0,self.count(4,reserve=5,nullable=True))):self.byte_payload()
            self.take(4,'anonymous-scalar32')
            self.query_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-finder-profile'))

    def sequence_scalar_profile(self,depth):
        start=self.pos
        if self.peek()==255:self.take(1,'null-sequence-scalar-profile')
        else:
            self.header(2)
            self.sequence(depth);self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-sequence-scalar-profile'))

    def weapon_vfx_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-weapon-vfx-profile')
        else:
            self.header(18)
            for _ in range(9):self.take(1,'anonymous-byte')
            for _ in range(9):self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-weapon-vfx-profile'))

    def animator_param_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-animator-param-profile')
        else:
            self.header(5);self.take(4,'anonymous-scalar32');self.take(1,'anonymous-byte')
            # The selected float helper advances four bytes; preserve all bits.
            self.take(4,'anonymous-raw4')
            for _ in range(2):self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-animator-param-profile'))

    def scalar_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-payload')
        else:
            self.header(3)
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            # The selected reader advances four bytes, regardless of the
            # managed type name. Preserve bits, including non-finite values.
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-payload'))

    def scalar_payload_curve_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-scalar-payload-curve-profile')
        else:
            # Selected SubSpeed header5 requires its final DWORD after the curve.
            self.header(5);self.scalar_payload();self.byte_payload();self.scalar_payload()
            self.curve_profile();self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-scalar-payload-curve-profile'))

    def curve_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-curve-profile')
        else:
            self.header(3)
            for _ in range(2):self.take(4,'anonymous-scalar32')
            for _ in range(max(0,self.count(28,nullable=True))):
                # Native source cursor advances 28; no per-element header.
                self.take(28,'anonymous-raw28')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-curve-profile'))

    def envelope_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-envelope-profile')
        else:
            self.header(7)
            for _ in range(2):
                self.curve_profile();self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-envelope-profile'))

    def impulse_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-impulse-profile')
        else:
            self.header(18);self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.curve_profile()
            # Mixed DWORD and MOVSS source helpers each consume four bytes.
            for _ in range(11):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.byte_payload()
            self.take(4,'anonymous-scalar32');self.envelope_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-impulse-profile'))

    def direction_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-direction-profile')
        else:
            self.header(8)
            self.take(1,'anonymous-nonzero-byte')
            self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte')
            for _ in range(2):
                if self.peek()==255:self.null_profile('nested-target')
                else:self.target_profile()
                self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-direction-profile'))

    def selector_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-selector-profile')
        else:
            self.header(3)
            self.selector_finder_profile()
            for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.selector_postprocessor_profile()
            for _ in range(max(0,self.count(1,nullable=True))):self.selector_validator_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-profile'))

    def selector_finder_profile(self):
        start=self.pos
        tag=self.nested_union_tag((0,1,2,3,5,7,8,10,12,13,14,16,18,19,21),'finder')
        if tag is None:pass
        elif self.peek()==255:self.take(1,'null-nested-finder-wrapper')
        else:
            self.header({0:0,1:0,2:0,3:4,5:0,7:8,8:0,10:0,12:1,13:1,14:2,16:9,18:11,19:4,21:0}[tag])
            if tag==3:
                self.take(12,'anonymous-raw12');self.take(16,'anonymous-raw16')
                self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            elif tag==7:
                for _ in range(3):self.take(1,'anonymous-nonzero-byte')
                for _ in range(2):self.take(4,'anonymous-scalar32')
                self.take(1,'anonymous-nonzero-byte')
                for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.shape_profile()
                self.take(4,'anonymous-scalar32')
            elif tag==12:self.query_profile()
            elif tag==13:self.take(4,'anonymous-scalar32')
            elif tag==14:
                self.vector_payload();self.vector_payload()
            elif tag==16:
                self.scalar_payload();self.vector2_payload();self.vector_payload()
                for _ in range(3):self.scalar_payload()
                self.take(4,'anonymous-scalar32')
                for _ in range(2):self.take(1,'anonymous-byte')
            elif tag==18:
                for _ in range(3):self.take(1,'anonymous-nonzero-byte')
                for _ in range(3):self.take(4,'anonymous-scalar32')
                self.byte_payload()
                for _ in range(2):self.take(1,'anonymous-nonzero-byte')
                self.take(4,'anonymous-scalar32');self.collider_shape_profile()
            elif tag==19:
                self.take(1,'anonymous-nonzero-byte');self.scalar_payload()
                self.selection_profile();self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-finder-profile'))

    def nested_union_tag(self,supported,kind):
        lead=self.peek()
        if lead==255:self.take(1,'null-nested-'+kind);return None
        width=3 if lead==250 else 1
        if width>self.limit-self.pos:
            raise FrameError(self.source,self.pos,{'bytes':width},{'remaining':self.limit-self.pos},'truncated')
        tag=struct.unpack_from('<H',self.data,self.pos+1)[0] if lead==250 else lead
        if tag not in supported:
            raise Unsupported(self.source,self.pos,'supported nested-'+kind+' union tag',tag,'nested-profile')
        self.take(width,'nested-'+kind+'-union-tag');return tag

    def selector_validator_profile(self):
        start=self.pos;tag=self.nested_union_tag((1,2,4,5,9,10,11),'validator')
        if tag is None:pass
        elif self.peek()==255:self.take(1,'null-nested-validator-wrapper')
        else:
            self.header(2 if tag in (1,2) else 3 if tag==4 else 1 if tag==11 else 0)
            if tag==1:
                self.finder_profile();self.take(4,'anonymous-scalar32')
            elif tag==2:
                self.take(4,'anonymous-scalar32');self.take(4,'anonymous-scalar32')
            elif tag==4:
                self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32');self.scalar_payload()
            elif tag==11:self.query_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-validator-profile'))

    def selector_postprocessor_profile(self):
        start=self.pos;tag=self.nested_union_tag((1,4,7,8),'postprocessor')
        if tag is None:pass
        elif self.peek()==255:self.take(1,'null-nested-postprocessor-wrapper')
        elif tag==1:
            self.header(1)
            for _ in range(max(0,self.count(1,nullable=True))):self.shape_profile()
        elif tag==8:
            self.header(2);self.take(4,'anonymous-scalar32');self.scalar_payload()
        elif tag==7:
            self.header(6);self.filter_profile()
            for _ in range(2):
                self.take(4,'anonymous-scalar32');self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
        else:
            # Admit one finite target expansion; a further recursive instance
            # remains a reported gap before its member header is consumed.
            if self.postprocessor_depth:
                raise Unsupported(self.source,self.pos,'postprocessor target depth <= 1',2,'depth-limit')
            self.header(2);self.postprocessor_depth+=1
            try:self.target_profile()
            finally:self.postprocessor_depth-=1
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selector-postprocessor-profile'))

    def filter_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-filter-profile')
        else:
            self.header(2);self.finder_profile();self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-filter-profile'))

    def vector2_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-vector2-payload')
        else:
            self.header(2)
            for _ in range(2):self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-vector2-payload'))

    def vector_payload(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-vector-payload')
        else:
            self.header(3)
            # Three nested scalar payloads, not twelve raw coordinate bytes.
            for _ in range(3):self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-vector-payload'))

    def shape_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-shape-profile')
        else:
            self.header(18)
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.vector_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte');self.vector_payload();self.scalar_payload()
            self.take(4,'anonymous-scalar32')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.scalar_payload()
            for _ in range(2):self.take(4,'anonymous-scalar32')
            self.scalar_payload();self.take(4,'anonymous-scalar32');self.vector_payload()
            self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-shape-profile'))

    def selection_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-selection-profile')
        else:
            self.header(4);self.finder_profile()
            for _ in range(max(0,self.count(1,reserve=5,nullable=True))):self.single_payload()
            self.take(4,'anonymous-scalar32');self.query_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-selection-profile'))

    def tag_elements(self,*,reserve=0):
        for _ in range(max(0,self.count(1,reserve=reserve,nullable=True))):
            element=self.pos
            if self.peek()==255:self.take(1,'null-tag-element')
            else:self.header(1);self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=element,end=self.pos,kind='anonymous-tag-element'))

    def raw_dword_array(self):
        # The selected root helper copies count*4 bytes, without element headers.
        start=self.pos
        count=self.count(4,nullable=True)
        self.take(max(0,count)*4,'anonymous-dword-array-body')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-dword-array',count=count))

    def data_pair_collection_profile(self):
        start=self.pos
        count=self.count(1,nullable=True)
        for _ in range(max(0,count)):
            element=self.pos
            if self.peek()==255:self.take(1,'null-data-pair-profile')
            else:
                self.header(4)
                self.take(1,'anonymous-byte')
                self.byte_payload()
                # This selected helper advances eight source bytes; it is not
                # the four-byte raw value inside scalar_payload().
                self.take(8,'anonymous-raw8')
                self.byte_payload()
            self.records.append(dict(start=element,end=self.pos,kind='anonymous-data-pair-profile'))
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-data-pair-collection-profile',count=count))

    def buff_action_map_collection_profile(self):
        start=self.pos
        count=self.count(1,nullable=True)
        for _ in range(max(0,count)):
            element=self.pos
            if self.peek()==255:self.take(1,'null-buff-action-map-profile')
            else:
                self.header(2)
                for _ in range(max(0,self.count(1,reserve=4,nullable=True))):self.sequence()
                # This map reads its Sequence array before the scalar, unlike
                # the separately pinned map in the first root collection.
                self.take(4,'anonymous-scalar32')
            self.records.append(dict(start=element,end=self.pos,kind='anonymous-buff-action-map-profile'))
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-buff-action-map-collection-profile',count=count))

    def modifier_element_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-modifier-element-profile')
        else:
            self.header(4)
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-modifier-element-profile'))

    def damage_processor_profile(self):
        # Separately pinned union routes and leaf readers; raw values do not
        # establish critical-rate arithmetic or attribute mutation semantics.
        start=self.pos;tag=self.nested_union_tag((0,2,3,4,5,6,9,10),'damage-processor')
        if tag is not None:
            if self.peek()==255:self.take(1,'null-damage-processor-wrapper')
            else:
                self.header({0:1,2:1,3:1,4:1,5:3,6:2,9:2,10:3}[tag])
                if tag in (0,2,3,4):
                    # Tags 0/2/3/4 select the critical-rate,
                    # attacker-critical-damage, attacker-penetration and
                    # independent-health wrappers. Each generated wrapper has
                    # one BlackboardDouble setter and one matching source read.
                    self.scalar_payload()
                elif tag==5:
                    # Current native dispatcher tag 5 selects
                    # DamageScaleProcessorForMemoryPack. Its generated wrapper
                    # and selected reader consume addition, side, zoneName.
                    self.scalar_payload()
                    self.take(4,'anonymous-damage-scale-side32')
                    self.byte_payload()
                elif tag==6:
                    # Current native dispatcher tag 6 selects
                    # DamageTextProcessorForMemoryPack: style then bool.
                    self.take(4,'anonymous-damage-text-style32')
                    self.take(1,'anonymous-damage-text-use-hp-change-byte')
                elif tag==9:
                    self.modifier_element_profile()
                    self.take(4,'anonymous-scalar32')
                else:
                    # Current native dispatcher tag 10 selects
                    # ModifyCalcResultForMemoryPack. Generated setter and
                    # selected reader order is baseMultiplier, modifyType,
                    # multiplierCnt.
                    self.scalar_payload()
                    self.take(4,'anonymous-modify-calc-result-type32')
                    self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-damage-processor-profile',variant=tag))

    def damage_modifier_element_profile(self):
        """Current DamageModifier.DataForMemoryPack wrapper in setter order."""
        start=self.pos
        if self.peek()==255:self.take(1,'null-damage-modifier-wrapper')
        else:
            self.header(3)
            self.sequence()
            count=self.count(1,reserve=4,nullable=True)
            for _ in range(max(0,count)):self.damage_processor_profile()
            self.take(4,'anonymous-enable-side32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-damage-modifier-profile'))

    def damage_modifier_collection_profile(self):
        start=self.pos;count=self.count(1,nullable=True)
        for _ in range(max(0,count)):self.damage_modifier_element_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-damage-modifier-collection-profile',count=count))
        return count

    def heal_processor_profile(self):
        """Two current HealProcessor union routes observed in BuffData."""
        start=self.pos;tag=self.nested_union_tag((0,1),'heal-processor')
        if tag is not None:
            if self.peek()==255:self.take(1,'null-heal-processor-wrapper')
            else:
                self.header({0:2,1:3}[tag])
                if tag==0:
                    self.modifier_element_profile()
                    self.take(4,'anonymous-scalar32')
                else:
                    self.scalar_payload()
                    self.take(4,'anonymous-scalar32')
                    self.scalar_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-heal-processor-profile',variant=tag))

    def heal_modifier_element_profile(self):
        """Current HealModifier.DataForMemoryPack wrapper in setter order."""
        start=self.pos
        if self.peek()==255:self.take(1,'null-heal-modifier-wrapper')
        else:
            self.header(3)
            self.sequence()
            self.take(4,'anonymous-enable-side32')
            count=self.count(1,nullable=True)
            for _ in range(max(0,count)):self.heal_processor_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-heal-modifier-profile'))

    def heal_modifier_collection_profile(self):
        start=self.pos;count=self.count(1,nullable=True)
        for _ in range(max(0,count)):self.heal_modifier_element_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-heal-modifier-collection-profile',count=count))
        return count

    def modifier_collection_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-modifier-collection-profile')
        else:
            self.header(2)
            count=self.count(1,reserve=1,nullable=True)
            for _ in range(max(0,count)):
                self.modifier_element_profile()
            # A null/empty array still has this independent root-member byte.
            self.take(1,'anonymous-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-modifier-collection-profile'))

    def tag_list_profile(self,*,reserve=0):
        # Conditional list count/loop plus separately pinned member-one element;
        # no candidate search or live provider/adapter-selection claim.
        start=self.pos
        if self.peek()==255:self.take(1,'null-tag-list-profile')
        else:
            self.header(1)
            self.tag_elements(reserve=reserve)
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-tag-list-profile'))

    def calculation_profile(self):
        start=self.pos;tag=self.nested_union_tag((0,1,2,3,5),'calculation')
        if tag is not None:
            if self.peek()==255:self.take(1,'null-calculation-wrapper')
            else:
                self.header({0:1,1:2,2:3,3:4,5:4}[tag])
                if tag in (2,5):self.take(1,'anonymous-nonzero-byte')
                # PrimaryAttrCalculation has a different member-four layout
                # from tag3: byte/DWORD precede its one scalar profile.
                if tag==5:self.take(4,'anonymous-scalar32')
                self.scalar_payload()
                if tag==3:self.take(4,'anonymous-scalar32')
                # Tag1 reads two independent scalars, even when the first is null.
                if tag in (1,2,3):self.scalar_payload()
                if tag in (3,5):self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-calculation-profile'))

    def empty_damage_collection(self,kind):
        # Only the selected count/null/empty path is closed; positive element
        # counts remain unsupported rather than guessing their wire widths.
        start=self.pos;n=self.count(1,nullable=True)
        if n>0:raise Unsupported(self.source,start,'null or empty '+kind,n,'nested-profile')

    def hit_sound_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-hit-sound-profile')
        else:self.header(1);self.byte_payload()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-hit-sound-profile'))

    def hit_environment_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-hit-environment-profile')
        else:
            self.header(4);self.take(8,'anonymous-scalar64')
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.calculation_profile()
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-hit-environment-profile'))

    def damage_unit_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-damage-unit-profile')
        else:
            self.header(33)
            for _ in range(2):self.take(1,'anonymous-nonzero-byte')
            self.calculation_profile();self.scalar_payload();self.take(1,'anonymous-nonzero-byte')
            self.empty_damage_collection('damage unit list')
            self.take(4,'anonymous-scalar32');self.take(8,'anonymous-scalar64')
            # Only the second list has selected DamageProcessorBase elements.
            # Reserve the third count and shortest remaining unit tail.
            for _ in range(max(0,self.count(1,reserve=42,nullable=True))):self.damage_processor_profile()
            self.empty_damage_collection('damage unit list')
            self.take(4,'anonymous-scalar32');self.byte_payload();self.take(4,'anonymous-scalar32')
            self.effect_configuration_profile()
            for _ in range(5):self.take(1,'anonymous-nonzero-byte')
            self.hit_sound_profile();self.take(4,'anonymous-scalar32')
            for _ in range(6):self.take(1,'anonymous-nonzero-byte')
            self.calculation_profile();self.take(1,'anonymous-nonzero-byte');self.take(4,'anonymous-scalar32')
            for _ in range(3):self.take(1,'anonymous-nonzero-byte')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-damage-unit-profile'))

    def effect_configuration_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-effect-configuration-profile')
        else:
            self.header(85)
            # One entry per native source member; inline 8/12-byte reads are
            # raw spans, while vector payloads contain three nested records.
            layout=(
            4,4,4,1,1,4,4,4,4,8,4,'scalar',
            'payload','empty-array',1,4,1,4,4,1,1,4,1,1,
            4,1,1,1,1,1,1,'scalar',4,1,4,'payload',
            4,1,4,4,4,4,1,12,'vector',4,4,1,
            1,4,4,4,1,4,4,12,'vector',1,12,'vector',
            1,4,1,1,1,4,4,1,1,1,1,1,
            1,1,1,1,4,1,1,4,4,4,4,'payload',
            1,
            )
            for op in layout:
                if isinstance(op,int):self.take(op,'anonymous-byte' if op==1 else 'anonymous-raw'+str(op))
                elif op=='payload':self.byte_payload()
                elif op=='scalar':self.scalar_payload()
                elif op=='vector':self.vector_payload()
                else:self.empty_damage_collection('effect array')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-effect-configuration-profile'))

    def target_profile(self):
        # Count every active non-null target, including direction and selector paths.
        if self.peek()==255:return self._target_profile()
        if self.target_depth>=64:
            raise Unsupported(self.source,self.pos,'target nesting <= 64',self.target_depth+1,'depth-limit')
        self.target_depth+=1
        try:self._target_profile()
        finally:self.target_depth-=1

    def _target_profile(self):
        start=self.pos
        if self.peek()==255:self.take(1,'null-target-profile')
        else:
            self.header(13)
            self.direction_profile()
            self.byte_payload()
            self.take(1,'anonymous-nonzero-byte')
            self.take(4,'anonymous-scalar32')
            self.take(1,'anonymous-nonzero-byte')
            self.byte_payload()
            self.selector_profile()
            for _ in range(3):self.take(4,'anonymous-scalar32')
            self.byte_payload()
            self.byte_payload()
            self.take(4,'anonymous-scalar32')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-target-profile'))


def sequence_frame(data,*,source='<sequence>'):
    reader=Reader(data,source);reader.sequence()
    if reader.pos!=len(data):raise FrameError(source,reader.pos,'EOF',len(data)-reader.pos,'trailing-byte')
    return reader.ranges


def event_prefix(data,*,source,limit=None):
    reader=Reader(data,source,limit);status='supported-prefix';diagnostic=None
    field_start=1
    try:
        reader.header(30)
        field_start=reader.pos
        count=reader.count(9)
        for _ in range(count):
            start=reader.pos
            reader.header(2);reader.take(4,'anonymous-map-scalar32')
            for _ in range(reader.count(1)):reader.sequence()
            reader.records.append(dict(start=start,end=reader.pos,kind='map'))
    except Unsupported as exc:status='unsupported';diagnostic=exc.diagnostic
    except FrameError as exc:status='failed';diagnostic=exc.diagnostic
    # Atomic scalar spans plus the explicit remainder must tile the whole file.
    # Completed parent records intentionally contain their nested child ranges.
    cursor=0
    for span in reader.ranges:
        if span['start']!=cursor or not cursor<span['end']<=reader.limit:
            raise FrameError(source,cursor,'contiguous bounded scalar ranges',span,'internal-range')
        cursor=span['end']
    if cursor!=reader.pos:raise FrameError(source,cursor,reader.pos,cursor,'internal-range')
    named_fields=[]
    if status=='supported-prefix':
        named_fields.append(dict(index=0,name='abilityEventAction',start=field_start,end=reader.pos,
                                 boundaryClass='exact-cursor'))
    return dict(status=status,diagnostic=diagnostic,consumedEnd=reader.pos,readLimit=reader.limit,ranges=reader.ranges,
                completedRecords=reader.records,
                namedFields=named_fields,
                fieldOrderSource='current generated BuffDataForMemoryPack setter order',
                opaqueRemainderRange=[reader.pos,len(data)],wholeSchemaExact=False,
                evidenceLevel='structural-only',boundary='Forward prefix profile only; no whole-object ownership, field meanings or EOF claim. Opaque remainder is bounded by the authenticated physical file, not a decoded record extent.')


def root_continuation(data,*,source,start,limit=None):
    """Members 2-6, called only after a supported first-collection endpoint.

    The caller owns that prerequisite; this function does not authenticate an
    arbitrary start offset or claim that a suffix candidate is a root field.
    """
    reader=Reader(data,source,limit)
    if type(start) is not int or not 1<=start<=reader.limit:
        raise FrameError(source,0,'first-collection endpoint within read limit',start,'start-bounds')
    reader.pos=start;status='supported-prefix';diagnostic=None
    named_fields=[]
    try:
        for index,name,read_field in (
            (1,'addingCooldown',reader.scalar_payload),
            (2,'applyTags',reader.raw_dword_array),
            (3,'attributeModifier',reader.modifier_collection_profile),
            (4,'blackboard',reader.data_pair_collection_profile),
            (5,'buffEventAction',reader.buff_action_map_collection_profile),
        ):
            field_start=reader.pos
            read_field()
            named_fields.append(dict(index=index,name=name,start=field_start,end=reader.pos,
                                     boundaryClass='exact-cursor'))
    except Unsupported as exc:status='unsupported';diagnostic=exc.diagnostic
    except FrameError as exc:status='failed';diagnostic=exc.diagnostic
    cursor=start
    for span in reader.ranges:
        if span['start']!=cursor or not cursor<span['end']<=reader.limit:
            raise FrameError(source,cursor,'contiguous bounded scalar ranges',span,'internal-range')
        cursor=span['end']
    if cursor!=reader.pos:raise FrameError(source,cursor,reader.pos,cursor,'internal-range')
    return dict(status=status,diagnostic=diagnostic,startOffset=start,consumedEnd=reader.pos,
                readLimit=reader.limit,ranges=reader.ranges,completedRecords=reader.records,
                namedFields=named_fields,
                fieldOrderSource='current generated BuffDataForMemoryPack setter order',
                opaqueRemainderRange=[reader.pos,len(data)],wholeSchemaExact=False,
                evidenceLevel='structural-only',
                boundary='Selected root members 2-6 after the independently supported first collection. '
                'Together their atomic ranges and the physical-file opaque remainder tile EOF; '
                'no field meanings, live provider selection or whole-BuffData EOF claim.')
