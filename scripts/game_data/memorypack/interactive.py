"""Focused MemoryPack decoder implementation extracted from the retired Data-page builder."""

from __future__ import annotations

import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.codecs.levelscript.action_map import decode_action_serialized_map
from scripts.game_data.memorypack.core import (
    MEMORYPACK_NULL_COUNT,
    MEMORYPACK_UNION_WIDE_TAG,
    STRING_SAMPLE_MAX_CHARS,
    format_offset,
    read_memorypack_bool,
    read_memorypack_f32,
    read_memorypack_i32,
    read_memorypack_u32_count,
    read_memorypack_utf8_string,
    require_memorypack_non_null_string,
)
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS


INTERACTIVE_TEMPLATE_MEMBER_COUNT = 26


INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG = 0x00F7


INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT = 3


INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG = 0x006B


INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT = 3


INTERACTIVE_PERFORM_PROPERTY_ROW_MEMBER_COUNT = 3


INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG = 0x007C


INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT = 2


INTERACTIVE_HITTABLE_COMPONENT_TAG = 0x0057


INTERACTIVE_HITTABLE_MEMBER_COUNT = 3


INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH = 80


INTERACTIVE_AUDIO_COMPONENT_TAG = 0x0061


INTERACTIVE_AUDIO_MEMBER_COUNT = 2


INTERACTIVE_DYNAMIC_AI_NAV_COMPONENT_TAG = 0x0073


INTERACTIVE_DYNAMIC_AI_NAV_MEMBER_COUNT = 2


INTERACTIVE_MODEL_LEVEL_UP_COMPONENT_TAG = 0x007F


INTERACTIVE_MODEL_LEVEL_UP_MEMBER_COUNT = 2


INTERACTIVE_NARRATIVE_COMPONENT_TAG = 0x00B7


INTERACTIVE_NARRATIVE_MEMBER_COUNT = 2


INTERACTIVE_CHARACTER_MOVEMENT_COMPONENT_TAG = 0x0027


INTERACTIVE_CHARACTER_MOVEMENT_MEMBER_COUNT = 5


INTERACTIVE_BASE_TRIGGER_COMPONENT_TAGS = {
    0x0018: "Core_AttackTriggerComponentForIntData",
    0x002C: "Core_ClickTriggerComponentForIntData",
    0x00D5: "Core_ScanTriggerComponentForIntData",
    0x00EB: "Core_StepOnTriggerComponentForIntData",
    0x00F9: "Core_TriggerZoneComponentForIntData",
}


INTERACTIVE_BASE_TRIGGER_MEMBER_COUNT = 3


INTERACTIVE_ABILITY_SYSTEM_COMPONENT_TAG = 0x000E


INTERACTIVE_ABILITY_SYSTEM_MEMBER_COUNT = 38


INTERACTIVE_ABILITY_SYSTEM_COLLIDER_SHAPE_LENGTH = 83


INTERACTIVE_AUDIO_DATA_MEMBER_COUNT = 13


INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS = {
    0x00D6: "Core_ShowGuideComponentData",
    0x00D7: "Core_ShowGuideWithConditionComponentData",
}


INTERACTIVE_SHOW_GUIDE_MEMBER_COUNT = 5


INTERACTIVE_AUDIO_BOOL_FIELDS = [
    "openAudio",
    "useActiveStencil",
    "useAttackStencil",
    "useCollectStencil",
    "useCustomStencil",
    "useDestroyStencil",
    "useDynamicLevel",
    "useInteractStencil",
    "useRepairStencil",
    "useTiggerStencil",
    "useWorkStencil",
]


INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES = {7, 8, 16, 28, 29}


INTERACTIVE_PERFORM_PROPERTY_TYPE_NAMES = {
    0: "Int",
    1: "Float",
    2: "String",
    3: "Ulong",
    4: "Bool",
    5: "Trigger",
}


INTERACTIVE_AUDIO_TRIGGER_STATE_NAMES = {
    0: "Invalid",
    1: "EnterArea",
    2: "InArea",
    3: "LeaveArea",
    4: "StartUp",
    5: "Working",
    6: "Stop",
    7: "Idle",
    8: "Attack",
    9: "BeHit",
    10: "Broken",
    11: "Repairing",
    12: "RepairDone",
    13: "Destroy",
    14: "Collect",
    15: "CollectHit",
    16: "CollectDestroy",
    17: "Interact",
    18: "Active",
    19: "NotActive",
}


INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS = {
    # Current installed dispatcher identities whose one-member bodies close as
    # exactly one typed property map and hand off to the next union/config
    # cursor throughout the selected corpus.
    0x0002,
    0x0008,
    0x0033,
    0x0056,
    0x0060,
    0x006C,
    0x00FF,
    0x010B,
    0x0015,
    0x001F,
    0x0023,
    0x0030,
    0x0037,
    0x0038,
    0x003E,
    0x0048,
    0x0046,
    0x004B,
    0x0050,
    0x005C,
    0x005E,
    0x006A,
    0x0072,
    0x0079,
    0x007E,
    0x0080,
    0x0082,
    0x0084,
    0x0089,
    0x008B,
    0x0093,
    0x0097,
    0x0099,
    0x009A,
    0x009B,
    0x00A1,
    0x00A6,
    0x00A7,
    0x00AF,
    0x00B9,
    0x00C5,
    0x00E3,
    0x00F0,
    0x00F2,
    0x00FD,
    0x00FE,
    0x0105,
    0x0106,
    0x0109,
    0x010D,
    0x010E,
    0x0115,
    0x0116,
    0x0119,
    0x011A,
    0x011F,
    0x0006,
    0x0019,
    0x001B,
    0x0022,
    0x0026,
    0x0027,
    0x002A,
    0x002C,
    0x002E,
    0x002F,
    0x0034,
    0x0035,
    0x003D,
    0x003F,
    0x0042,
    0x0044,
    0x0045,
    0x0049,
    0x004F,
    0x0055,
    0x0059,
    0x005A,
    0x0061,
    0x0064,
    0x0066,
    0x006B,
    0x006F,
    0x0070,
    0x0075,
    0x0077,
    0x007F,
    0x0083,
    0x0085,
    0x0086,
    0x0087,
    0x008D,
    0x008E,
    0x0092,
    0x009F,
    0x00A2,
    0x00AA,
    0x00BC,
    0x00C6,
    0x00D0,
    0x00D3,
    0x00D5,
    0x00D8,
    0x00DD,
    0x00DE,
    0x00DF,
    0x00E0,
    0x00E6,
    0x00EB,
    0x00ED,
    0x00EE,
    0x00F6,
    0x00F8,
    0x00F9,
    0x00FC,
}


INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS.update({
    0x0001,
    0x0011,
    0x0013,
    0x001A,
    0x0020,
    0x0021,
    0x0031,
    0x0032,
    0x0036,
    0x0039,
    0x003A,
    0x0047,
    0x004C,
    0x004D,
    0x0051,
    0x0054,
    0x005F,
    0x0062,
    0x0063,
    0x0065,
    0x0067,
    0x0068,
    0x0069,
    0x006E,
    0x0074,
    0x0076,
    0x0078,
    0x007A,
    0x0081,
    0x008A,
    0x0088,
    0x008C,
    0x008F,
    0x0090,
    0x0091,
    0x0095,
    0x0096,
    0x0098,
    0x009C,
    0x009D,
    0x009E,
    0x00A3,
    0x00A4,
    0x00A5,
    0x00A8,
    0x00AB,
    0x00AC,
    0x00AE,
    0x00B0,
    0x00B2,
    0x00B3,
    0x00B5,
    0x00B6,
    0x00C2,
    0x00C4,
    0x00C9,
    0x00CD,
    0x00CE,
    0x00D2,
    0x00DA,
    0x00DB,
    0x00DC,
    0x00E1,
    0x00E2,
    0x00E4,
    0x00E5,
    0x00E7,
    0x00E8,
    0x00E9,
    0x00F1,
    0x00F3,
    0x00F4,
    0x00F5,
    0x00FA,
    0x00FB,
    0x0100,
    0x0101,
    0x0102,
    0x0104,
    0x0108,
    0x010C,
    0x0111,
    0x0112,
    0x0113,
    0x0114,
    0x0117,
    0x0118,
    0x011B,
    0x011C,
    0x011D,
    0x011E,
    0x0120,
})

INTERACTIVE_TEMPLATE_SCHEMA_SOURCE_NOTE = (
    "26-member current root order recovered from IL2CPP template-wrapper setters "
    "and byte-cursor validation"
)


BASE_COMPONENT_UNION_SOURCE_NOTE = (
    "BaseComponentData union formatter tags extracted from installed GameAssembly.dll"
)


BASE_COMPONENT_UNION_TAGS = {
    0x0000: "AdditionalBattleShapeComponentData",
    0x0002: "AetherEnergyLockedIntComponentData",
    0x0008: "Core_AbandonPackBehaviourComponentData",
    0x000E: "Core_AbilitySystemForIntData",
    0x0011: "Core_ActivitySnapshotComponentData",
    0x0013: "Core_AetherEnergyLockedCollectionComponentData",
    0x0015: "Core_AetherEnergyLockedSpawnerComponentData",
    0x0018: "Core_AttackTriggerComponentForIntData",
    0x001C: "Core_BaseControllerData",
    0x001F: "Core_BelongToWaterVolumeComponentData",
    0x0023: "Core_CanSetVisibleComponentData",
    0x0027: "Core_CharacterMovementComponentData",
    0x002C: "Core_ClickTriggerComponentForIntData",
    0x002E: "Core_CommonCollectionComponentData",
    0x002F: "Core_CommonFixablePropsComponentData",
    0x0030: "Core_CommonLuaUICallComponentData",
    0x0031: "Core_CommonSwitchComponentData",
    0x0032: "Core_ContinuousInteractComponentData",
    0x0033: "Core_CurveMoveComponentData",
    0x0035: "Core_CustomCurveMoveComponentData",
    0x0037: "Core_DomainShopSystemComponentData",
    0x0038: "Core_DropItemBehaviourComponentData",
    0x0039: "Core_DungeonEntryPresetTeamSystemComponentData",
    0x003D: "Core_ElectricNodeComponentData",
    0x003E: "Core_EmptyLogicInteractiveComponentData",
    0x0045: "Core_ErosionCoreComponentData",
    0x0046: "Core_ErosionSludgeCoreComponentData",
    0x0048: "Core_FacBattleBuildingComponentData",
    0x0049: "Core_FacRegionUpgradeSystemComponentData",
    0x004B: "Core_FactoryBuildingWrapperComponentData",
    0x004D: "Core_FactoryGasCoreComponentData",
    0x004F: "Core_FixableRobotComponentData",
    0x0050: "Core_GameplayElectricityNodeComponentData",
    0x0051: "Core_GenderChangeSystemComponentData",
    0x0055: "Core_GoldCoinPlungingAttackBoardData",
    0x0056: "Core_HeightZeroMarkerComponentData",
    0x0057: "Core_HittableComponentForIntData",
    0x005C: "Core_InteractCommonTwoStateComponentData",
    0x005E: "Core_Interactive3DUIComponentData",
    0x005F: "Core_InteractiveAltarFireSeedComponentData",
    0x0060: "Core_InteractiveAssistedAimingComponentData",
    0x0061: "Core_InteractiveAudioData",
    0x0062: "Core_InteractiveAutoMovePlatformComponentData",
    0x0065: "Core_InteractiveBeaconPoleFireSeedComponentData",
    0x0066: "Core_InteractiveBehitPerformComponentData",
    0x0069: "Core_InteractiveCollectionPieceComponentData",
    0x006A: "Core_InteractiveCommonMultiStateComponentData",
    0x006B: "Core_InteractiveCommonPerformComponentData",
    0x006C: "Core_InteractiveCoolerUnitComponentData",
    0x006E: "Core_InteractiveDestructibleComponentData",
    0x0072: "Core_InteractiveDoorCommonComponentData",
    0x0073: "Core_InteractiveDynamicAINavComponentData",
    0x0075: "Core_InteractiveFacHintPerformComponentData",
    0x0077: "Core_InteractiveHintPerformComponentData",
    0x0079: "Core_InteractiveKickableReceiverComponentData",
    0x007A: "Core_InteractiveLifterButtonComponentData",
    0x007C: "Core_InteractiveLogicControllerComponentData",
    0x007E: "Core_InteractiveManualMovePlatformComponentData",
    0x007F: "Core_InteractiveModelLevelUpComponentData",
    0x0080: "Core_InteractiveMovingPlatformComponentData",
    0x0081: "Core_InteractiveNarrativeDoodadComponentData",
    0x0082: "Core_InteractiveOutFallComponentData",
    0x0084: "Core_InteractivePhysicsDestructibleComponentData",
    0x0087: "Core_InteractiveRootComponentData",
    0x0088: "Core_InteractiveRuneColumnComponentData",
    0x0089: "Core_InteractiveRunePointComponentData",
    0x008B: "Core_InteractiveSteamBlockerComponentData",
    0x008C: "Core_InteractiveSuperPressureBoardComponentData",
    0x008D: "Core_InteractiveSwitchAttackComponentData",
    0x008E: "Core_InteractiveSwitchAttackElectricComponentData",
    0x008F: "Core_InteractiveSwitchCommonNoElectricComponentData",
    0x0090: "Core_InteractiveSwitchLockComponentData",
    0x0091: "Core_InteractiveSwitchMultiStateComponentData",
    0x0092: "Core_InteractiveTerminalReadingComponentData",
    0x0093: "Core_InteractiveTwoPointMovementComponentData",
    0x0095: "Core_InteractiveUnstablePlatformComponentData",
    0x0096: "Core_InteractiveVerticalRopeComponentData",
    0x0097: "Core_InteractiveWaterFallComponentData",
    0x0098: "Core_InteractiveWaterFloaterComponentData",
    0x0099: "Core_InteractiveWaterGunDriveBallComponentData",
    0x009A: "Core_InteractiveWaterPipeComponentData",
    0x009B: "Core_InteractiveWaterSwitchComponentData",
    0x009C: "Core_InteractiveWaterVolumeSwitchComponentData",
    0x009D: "Core_InteractiveWaterVolumeTransfererComponentData",
    0x009E: "Core_InteractiveWeekRaidMineComponentData",
    0x009F: "Core_InteractiveWeekRaidMineCoreComponentData",
    0x00A1: "Core_InteractSimpleTwoStateComponentData",
    0x00A2: "Core_IntFacSoilComponentData",
    0x00A6: "Core_KeepRelativeOffsetComponentData",
    0x00A7: "Core_KickablePipelineComponentData",
    0x00A8: "Core_KickableSpawnerComponentData",
    0x00AB: "Core_LifterCoreComponentData",
    0x00AC: "Core_LifterForBoxGameCoreComponentData",
    0x00AF: "Core_MainCharacterInterestComponentData",
    0x00B0: "Core_MatrixElementComponentData",
    0x00B3: "Core_MissionBeaconComponentData",
    0x00B7: "Core_NarrativeComponentData",
    0x00B9: "Core_NavmeshDynamicBakeAreaComponentData",
    0x00C4: "Core_PlayerCinematicInteractPerformComponentData",
    0x00C5: "Core_PlayerInteractPerformComponentData",
    0x00D5: "Core_ScanTriggerComponentForIntData",
    0x00D6: "Core_ShowGuideComponentData",
    0x00D7: "Core_ShowGuideWithConditionComponentData",
    0x00D8: "Core_SignalTowerComponentData",
    0x00D9: "Core_SimpleAnimatorComponentData",
    0x00DB: "Core_SnapshotSystemComponentData",
    0x00E3: "Core_SpaceshipRegionWallData",
    0x00EB: "Core_StepOnTriggerComponentForIntData",
    0x00ED: "Core_SummonTeamComponentData",
    0x00F0: "Core_TeammateChangeAIModeComponentData",
    0x00F1: "Core_TianShiZhuangComponentData",
    0x00F2: "Core_TravelLinkEffectModelComponentData",
    0x00F3: "Core_TrchestBubbleComponentData",
    0x00F4: "Core_TreasureComponentData",
    0x00F5: "Core_TreasureStarData",
    0x00F6: "Core_TriggerObserverAllEntityComponentData",
    0x00F7: "Core_TriggerObserverComponentData",
    0x00F9: "Core_TriggerZoneComponentForIntData",
    0x00FB: "Core_VendingMachineComponentData",
    0x00FC: "Core_WaterAbsorbedImpactComponentData",
    0x00FD: "Core_WaterProgressComponentData",
    0x00FE: "Core_WaterProgressDriveCurveMovementComponentData",
    0x00FF: "Core_WaterVolHeightMarkerComponentData",
    0x0100: "Core_WeekRaidEntrySystemComponentData",
    0x0101: "Core_WeekRaidRuneComponentData",
    0x0102: "Core_WeekRaidTreasureComponentData",
    0x0105: "CraneContainerComponentData",
    0x0106: "CraneTowerComponentData",
    0x0108: "DestructibleGoldCoinComponentData",
    0x0109: "DungeonExitComponentData",
    0x010B: "ElectricFenceComponentData",
    0x010C: "GameplayLockedRewardComponentData",
    0x010D: "HiddenMarkComponentComponentData",
    0x010E: "InfraredGroupComponentData",
    0x0111: "InteractiveHydrantComponentData",
    0x0113: "InteractiveLsmControlledSwitchComponentData",
    0x0114: "InteractiveMatrixCenterComponentData",
    0x0115: "InteractiveMovingPlatClientOnlyComponentData",
    0x0116: "InteractivePressureSwitchComponentData",
    0x0117: "InteractiveRiftComponentData",
    0x0119: "InteractiveStainComponentData",
    0x011A: "InteractiveStartAreaComponentData",
    0x011B: "LoadingPortalComponentData",
    0x011C: "LockableTreasureComponentData",
    0x011D: "MicroSpotDiffMainStakeComponentData",
    0x011E: "MicroSpotDiffSubStakeComponentData",
    0x011F: "ScannableTraceComponentData",
    0x0120: "SeamlessPortalComponentData",
    0x012C: "View_InteractiveModelComponentData",
}


# Newly reached current dispatcher branches. Each identity is joined through
# the selected switch target's unresolved tag-1 usage cell, MetadataRegistration
# type table, and exact wrapper TypeDefinition.
BASE_COMPONENT_UNION_TAGS.update({
    0x0001: "AetherEnergyLockComponentData",
    0x001A: "Core_BalloonComponentData",
    0x0020: "Core_BlightMiasmaSafeZoneData",
    0x0021: "Core_BreakableFloorData",
    0x0036: "Core_DomainDepotSystemComponentData",
    0x003A: "Core_DungeonEntrySystemComponentData",
    0x0047: "Core_FacBattleBaseCoreComponentData",
    0x004C: "Core_FactoryGasComponentData",
    0x0054: "Core_GoldCoinComponentData",
    0x0063: "Core_InteractiveBambooRaftComponentData",
    0x0067: "Core_InteractiveCampfireComponentData",
    0x0068: "Core_InteractiveCollectionCoinComponentData",
    0x0074: "Core_InteractiveExitPerformanceComponentData",
    0x0076: "Core_InteractiveFlammableBombComponentData",
    0x0078: "Core_InteractiveKickableComponentData",
    0x008A: "Core_InteractiveSpecialSightComponentData",
    0x00A3: "Core_JumpMachineComponentData",
    0x00A4: "Core_JumpMachineElectricComponentData",
    0x00A5: "Core_JumpMachineVerticalComponentData",
    0x00AE: "Core_MagnetComponentData",
    0x00B2: "Core_MinigameBalloonSystemComponentData",
    0x00B5: "Core_MoveControlLogicComponentData",
    0x00B6: "Core_MultiTriggerObserverComponentData",
    0x00C2: "Core_PhysicsAudioComponentData",
    0x00C9: "Core_PurificationDeviceComponentData",
    0x00CD: "Core_RacingDungeonBattleEntrySystemComponentData",
    0x00CE: "Core_RecycleBinSystemComponentData",
    0x00D2: "Core_RotatorComponentData",
    0x00DA: "Core_SimulationTrainingSystemComponentData",
    0x00DC: "Core_SpaceshipCabinTerminalComponentData",
    0x00E1: "Core_SpaceshipMedalWallSystemData",
    0x00E2: "Core_SpaceshipMusicPlayerSystemComponentData",
    0x00E4: "Core_SpaceshipRoomDoorSystemData",
    0x00E5: "Core_SpaceshipScreenData",
    0x00E7: "Core_SpaceshipSummonData",
    0x00E8: "Core_SpaceshipVisitPortalSystemData",
    0x00E9: "Core_SpaceshipWeaponWallData",
    0x00FA: "Core_TyphoeaArcherySystemComponentData",
    0x0104: "Core_WorldEnergyPointSystemComponentData",
    0x0112: "InteractiveLeaderButterflyComponentData",
    0x0118: "InteractiveSmallButterflyComponentData",
})


def read_memorypack_union_tag(data: bytes, offset: int) -> tuple[int, int, int]:
    if offset >= len(data):
        raise ValueError("truncated-union-tag")
    first = data[offset]
    offset += 1
    if first == MEMORYPACK_UNION_WIDE_TAG:
        if offset + 2 > len(data):
            raise ValueError("truncated-wide-union-tag")
        tag = struct.unpack_from("<H", data, offset)[0]
        return tag, offset + 2, 3
    if first > MEMORYPACK_UNION_WIDE_TAG:
        raise ValueError(f"unsupported-union-tag-marker=0x{first:02x}")
    return first, offset, 1


def read_memorypack_i64(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 8 > len(data):
        raise ValueError("truncated-int64")
    return struct.unpack_from("<q", data, offset)[0], offset + 8


def float_from_low_bits(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]


def interactive_property_value_preview(
    value_type: int,
    value_bits: int,
    string_tail: str | None = None,
) -> int | float | bool | str | None:
    if value_type in INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES:
        return string_tail
    if value_type == 1:
        return bool(value_bits)
    if value_type in (5, 11, 12):
        return round(float_from_low_bits(value_bits), 6)
    return value_bits


def parse_interactive_component_property_value(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}.memberCount:truncated")
    member_count = data[offset]
    offset += 1
    if member_count != 2:
        raise ValueError(f"{field_name}.memberCount={member_count}")
    value_type, offset = read_memorypack_i32(data, offset)
    value_count, offset = read_memorypack_u32_count(
        data,
        offset,
        f"{field_name}.values",
        max_count=2048,
    )
    values: list[dict[str, Any]] = []
    tail_counts: Counter[int] = Counter()
    string_tail_counts: Counter[str] = Counter()
    for index in range(value_count):
        if offset >= len(data):
            raise ValueError(f"{field_name}.values[{index}].memberCount:truncated")
        item_member_count = data[offset]
        offset += 1
        if item_member_count != 2:
            raise ValueError(f"{field_name}.values[{index}].memberCount={item_member_count}")
        bits, offset = read_memorypack_i64(data, offset)
        string_tail: str | None = None
        tail: int | None = None
        if value_type in INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES:
            string_tail, offset, string_error = read_memorypack_utf8_string(
                data,
                offset,
                max_length=1024,
            )
            if string_error:
                raise ValueError(f"{field_name}.values[{index}].stringTail:{string_error}")
            if string_tail is not None:
                string_tail_counts[string_tail] += 1
        else:
            tail, offset = read_memorypack_i32(data, offset)
            tail_counts[tail] += 1
        values.append({
            "valueBit64": bits,
            "floatFromLowBits": round(float_from_low_bits(bits), 6),
            "preview": interactive_property_value_preview(value_type, bits, string_tail),
            "tailInt": tail,
            "stringTail": string_tail,
        })
    return {
        "memberCount": member_count,
        "valueType": value_type,
        "valueCount": value_count,
        "values": values,
        "tailCounts": {str(key): count for key, count in tail_counts.most_common(8)},
        "stringTailCounts": dict(string_tail_counts.most_common(12)),
    }, offset


def parse_interactive_component_property_map(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_entries: int = 4096,
    sample_limit: int = 16,
) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=max_entries)
    rows: list[dict[str, Any]] = []
    key_counts: Counter[str] = Counter()
    value_type_counts: Counter[int] = Counter()
    value_count_counts: Counter[int] = Counter()
    tail_counts: Counter[int] = Counter()
    string_tail_counts: Counter[str] = Counter()
    for index in range(count):
        if offset >= len(data):
            raise ValueError(f"{field_name}[{index}].memberCount:truncated")
        member_count = data[offset]
        offset += 1
        if member_count != 2:
            raise ValueError(f"{field_name}[{index}].memberCount={member_count}")
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{index}].key",
            max_length=256,
        )
        value, offset = parse_interactive_component_property_value(
            data,
            offset,
            f"{field_name}[{index}].value",
        )
        key_counts[key] += 1
        value_type_counts[int(value["valueType"])] += 1
        value_count_counts[int(value["valueCount"])] += 1
        for tail, tail_count in value["tailCounts"].items():
            tail_counts[int(tail)] += tail_count
        for string_tail, string_tail_count in (value.get("stringTailCounts") or {}).items():
            string_tail_counts[str(string_tail)] += int(string_tail_count)
        if len(rows) < sample_limit:
            rows.append({
                "key": key,
                "valueType": value["valueType"],
                "valueCount": value["valueCount"],
                "preview": [item["preview"] for item in value["values"][:12]],
                "values": value["values"][:12],
            })
    return {
        "count": count,
        "keys": list(key_counts),
        "keyCounts": dict(key_counts.most_common(24)),
        "valueTypeCounts": {str(key): count for key, count in value_type_counts.most_common(16)},
        "valueCountCounts": {str(key): count for key, count in value_count_counts.most_common(16)},
        "tailCounts": {str(key): count for key, count in tail_counts.most_common(16)},
        "stringTailCounts": dict(string_tail_counts.most_common(24)),
        "sampleRows": rows,
    }, offset


def interactive_property_preview_by_key(property_map: dict[str, Any]) -> dict[str, Any]:
    previews: dict[str, Any] = {}
    for row in property_map.get("sampleRows") or []:
        key = str(row.get("key") or "")
        values = row.get("preview") or []
        if not key:
            continue
        if len(values) == 1:
            previews[key] = values[0]
        else:
            previews[key] = values
    return previews


def parse_interactive_trigger_observer_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT:
        raise ValueError(f"triggerObserver.memberCount={member_count}")
    start = offset
    maps: list[dict[str, Any]] = []
    for field_index in range(member_count):
        property_map, offset = parse_interactive_component_property_map(
            data,
            offset,
            f"triggerObserver.field{field_index}",
        )
        maps.append(property_map)
    primary = maps[0] if maps else {"sampleRows": []}
    previews = interactive_property_preview_by_key(primary)
    return {
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "propertyMapCounts": [int(row.get("count") or 0) for row in maps],
        "primaryKeys": list((primary.get("keyCounts") or {}).keys()),
        "primaryValueTypeCounts": primary.get("valueTypeCounts") or {},
        "primaryValueCountCounts": primary.get("valueCountCounts") or {},
        "primaryTailCounts": primary.get("tailCounts") or {},
        "primaryPreviewByKey": previews,
        "sampleProperties": (primary.get("sampleRows") or [])[:12],
    }, offset


def parse_interactive_single_property_map_component(
    data: bytes,
    offset: int,
    tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != 1:
        raise ValueError(f"singlePropertyMap.memberCount={member_count}")
    start = offset
    type_name = BASE_COMPONENT_UNION_TAGS.get(tag, f"tag_0x{tag:04x}")
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        f"{type_name}.field0",
    )
    previews = interactive_property_preview_by_key(property_map)
    return {
        "tag": f"0x{tag:04x}",
        "type": type_name,
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "singlePropertyMap",
        "schemaSource": (
            "one-member property-map body validated by exact map parse and next-union handoff "
            "across export_full InteractiveData first payloads"
        ),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "stringTailCounts": property_map.get("stringTailCounts") or {},
        "previewByKey": previews,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
    }, offset


def parse_interactive_dynamic_ai_nav_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_DYNAMIC_AI_NAV_MEMBER_COUNT:
        raise ValueError(f"interactiveDynamicAINav.memberCount={member_count}")
    start = offset
    properties, offset = parse_interactive_component_property_map(
        data,
        offset,
        "interactiveDynamicAINav.instance",
    )
    obstacle_type, offset = read_memorypack_i32(data, offset)
    if obstacle_type not in (0, 1):
        raise ValueError(
            f"interactiveDynamicAINav.obstacleType={obstacle_type}"
        )
    return {
        "type": "Core_InteractiveDynamicAINavComponentData",
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapAndObstacleType",
        "schemaSource": (
            "current generated two-field wrapper order; exact property-map "
            "cursor and bounded ObstacleType enum"
        ),
        "propertyMapCount": int(properties.get("count") or 0),
        "propertyKeys": list((properties.get("keyCounts") or {}).keys()),
        "obstacleType": obstacle_type,
    }, offset


def parse_interactive_model_level_up_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_MODEL_LEVEL_UP_MEMBER_COUNT:
        raise ValueError(f"interactiveModelLevelUp.memberCount={member_count}")
    start = offset
    properties, offset = parse_interactive_component_property_map(
        data,
        offset,
        "interactiveModelLevelUp.instance",
    )
    model_levels, offset = _parse_interactive_string_list(
        data,
        offset,
        "interactiveModelLevelUp.modelLevelList",
    )
    return {
        "type": "Core_InteractiveModelLevelUpComponentData",
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapAndModelLevelList",
        "schemaSource": (
            "current generated two-field wrapper order; inherited DynamicPropertyComponentData "
            "property map followed by the derived model-level string list"
        ),
        "propertyMapCount": int(properties.get("count") or 0),
        "propertyKeys": list((properties.get("keyCounts") or {}).keys()),
        "modelLevelCount": None if model_levels is None else len(model_levels),
        "modelLevelList": model_levels,
    }, offset


def parse_interactive_narrative_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_NARRATIVE_MEMBER_COUNT:
        raise ValueError(f"interactiveNarrative.memberCount={member_count}")
    start = offset
    properties, offset = parse_interactive_component_property_map(
        data,
        offset,
        "interactiveNarrative.instance",
    )
    narrative_type, offset = read_memorypack_i32(data, offset)
    if narrative_type not in (1, 2, 3):
        raise ValueError(f"interactiveNarrative.narrativeType={narrative_type}")
    return {
        "type": "Core_NarrativeComponentData",
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapAndNarrativeType",
        "schemaSource": (
            "current generated two-field wrapper order; inherited InteractiveCoreComponentData "
            "property map followed by the derived NarrativeObjType enum"
        ),
        "propertyMapCount": int(properties.get("count") or 0),
        "propertyKeys": list((properties.get("keyCounts") or {}).keys()),
        "narrativeType": narrative_type,
    }, offset


def parse_interactive_character_movement_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Decode the current character-movement component wrapper."""

    if member_count != INTERACTIVE_CHARACTER_MOVEMENT_MEMBER_COUNT:
        raise ValueError(f"characterMovement.memberCount={member_count}")
    start = offset
    properties, offset = parse_interactive_component_property_map(
        data, offset, "characterMovement.instance"
    )
    ability_count, offset = _read_interactive_count_or_null(
        data,
        offset,
        "characterMovement.abilityEntityMovementDataList",
        max_count=1_000,
    )
    if ability_count not in (None, 0):
        raise ValueError(
            "characterMovement.abilityEntityMovementDataList:"
            f"unsupported-count={ability_count}"
        )

    if offset >= len(data):
        raise ValueError("characterMovement.movementData:truncated-marker")
    movement_marker = data[offset]
    offset += 1
    movement_data: dict[str, float] | None = None
    if movement_marker != 0xFF:
        if movement_marker != 5:
            raise ValueError(
                "characterMovement.movementData:"
                f"member-count={movement_marker},expected=5"
            )
        movement_data = {}
        for field in (
            "aiRotationSpeed",
            "moveSpeed",
            "navAcceleration",
            "overrideStepDownOffset",
            "overrideStepOffset",
        ):
            value, offset = read_memorypack_f32(data, offset)
            if not math.isfinite(value):
                raise ValueError(f"characterMovement.movementData.{field}:non-finite")
            movement_data[field] = round(value, 6)

    override_move_mode, offset = read_memorypack_i32(data, offset)
    if not 0 <= override_move_mode <= 35:
        raise ValueError(
            f"characterMovement.overrideMoveMode={override_move_mode}"
        )

    if offset >= len(data):
        raise ValueError("characterMovement.proxyShape:truncated-marker")
    shape_marker = data[offset]
    offset += 1
    proxy_shape: dict[str, float] | None = None
    if shape_marker != 0xFF:
        if shape_marker != 2:
            raise ValueError(
                f"characterMovement.proxyShape:member-count={shape_marker},expected=2"
            )
        height, offset = read_memorypack_f32(data, offset)
        radius, offset = read_memorypack_f32(data, offset)
        if not math.isfinite(height) or not math.isfinite(radius):
            raise ValueError("characterMovement.proxyShape:non-finite")
        proxy_shape = {"height": round(height, 6), "radius": round(radius, 6)}

    return {
        "type": "Core_CharacterMovementComponentData",
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapAbilityMovementsMovementDataMoveModeAndShape",
        "schemaSource": (
            "current generated five-field wrapper order; inherited DynamicPropertyComponentData "
            "map followed by AbilityEntityMovementData list, MovementData, MoveMode and Shape; "
            "exact next-union handoff"
        ),
        "propertyMapCount": int(properties.get("count") or 0),
        "propertyKeys": list((properties.get("keyCounts") or {}).keys()),
        "abilityEntityMovementDataCount": ability_count,
        "movementData": movement_data,
        "overrideMoveMode": override_move_mode,
        "proxyShape": proxy_shape,
    }, offset


def _read_interactive_strict_bool(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated")
    value = data[offset]
    if value not in (0, 1):
        raise ValueError(f"{field_name}:invalid-bool={value}")
    return bool(value), offset + 1


def _read_interactive_string(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[str | None, int]:
    value, offset, error = read_memorypack_utf8_string(
        data,
        offset,
        max_length=65_536,
    )
    if error:
        raise ValueError(f"{field_name}:{error}")
    return value, offset


def _read_interactive_count_or_null(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_count: int = 10_000,
) -> tuple[int | None, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-count")
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if count == MEMORYPACK_NULL_COUNT:
        return None, offset
    if count > max_count:
        raise ValueError(f"{field_name}:invalid-count={count}")
    return count, offset


def _parse_interactive_condition_object(
    data: bytes,
    offset: int,
    field_name: str,
    member_count: int,
    parser: Any,
) -> tuple[dict[str, Any] | None, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-marker")
    marker = data[offset]
    offset += 1
    if marker == 0xFF:
        return None, offset
    if marker != member_count:
        raise ValueError(
            f"{field_name}:member-count={marker},expected={member_count}"
        )
    return parser(data, offset, field_name)


def _parse_interactive_base_condition(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    condition_type, offset = read_memorypack_i32(data, offset)

    def parse_game_events(
        payload: bytes,
        cursor: int,
        label: str,
    ) -> tuple[dict[str, Any], int]:
        event_count, cursor = _read_interactive_count_or_null(
            payload, cursor, f"{label}.events"
        )
        events: list[int] = []
        for index in range(event_count or 0):
            event, cursor = read_memorypack_i32(payload, cursor)
            events.append(event)
        need_hide, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.needHide"
        )
        return {"events": events, "needHide": need_hide}, cursor

    game_events, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.gameEventsUpdateConfig", 2, parse_game_events
    )
    group_name, offset = _read_interactive_string(
        data, offset, f"{field_name}.groupName"
    )

    def parse_one_bool(
        payload: bytes,
        cursor: int,
        label: str,
    ) -> tuple[dict[str, Any], int]:
        value, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.value"
        )
        return {"value": value}, cursor

    level_entity, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.levelEntityConfig", 1, parse_one_bool
    )
    no_use, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.noUseConfig", 1, parse_one_bool
    )

    def parse_property_data(
        payload: bytes,
        cursor: int,
        label: str,
    ) -> tuple[dict[str, Any], int]:
        bool_value, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.bValue"
        )
        if cursor >= len(payload):
            raise ValueError(f"{label}.compareType:truncated")
        compare_type = payload[cursor]
        cursor += 1
        property_name, cursor = _read_interactive_string(
            payload, cursor, f"{label}.propertyName"
        )
        use_bool, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.useBool"
        )
        value, cursor = read_memorypack_i32(payload, cursor)
        return {
            "bValue": bool_value,
            "compareType": compare_type,
            "propertyName": property_name,
            "useBool": use_bool,
            "value": value,
        }, cursor

    property_data, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.propertyData", 5, parse_property_data
    )

    def parse_system_state(
        payload: bytes,
        cursor: int,
        label: str,
    ) -> tuple[dict[str, Any], int]:
        succeed, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.succeed"
        )
        system_state, cursor = read_memorypack_i32(payload, cursor)
        system_type, cursor = read_memorypack_i32(payload, cursor)
        return {
            "succeed": succeed,
            "systemState": system_state,
            "systemType": system_type,
        }, cursor

    system_state, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.systemStateConfig", 3, parse_system_state
    )

    def parse_system_unlock(
        payload: bytes,
        cursor: int,
        label: str,
    ) -> tuple[dict[str, Any], int]:
        invert, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.isInvert"
        )
        system_type, cursor = read_memorypack_i32(payload, cursor)
        return {"isInvert": invert, "systemType": system_type}, cursor

    system_unlock, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.systemUnlockConfig", 2, parse_system_unlock
    )

    def parse_target_entity(
        payload: bytes,
        cursor: int,
        label: str,
    ) -> tuple[dict[str, Any], int]:
        ignore, cursor = _read_interactive_strict_bool(
            payload, cursor, f"{label}.ignore"
        )
        ignore_name, cursor = _read_interactive_string(
            payload, cursor, f"{label}.ignorePropertyName"
        )
        property_name, cursor = _read_interactive_string(
            payload, cursor, f"{label}.propertyName"
        )
        if cursor >= len(payload) or payload[cursor] != 0xFF:
            marker = payload[cursor] if cursor < len(payload) else None
            raise ValueError(f"{label}.target:unsupported-marker={marker}")
        cursor += 1
        value, cursor = read_memorypack_i32(payload, cursor)
        return {
            "ignore": ignore,
            "ignorePropertyName": ignore_name,
            "propertyName": property_name,
            "target": None,
            "value": value,
        }, cursor

    target_entity, offset = _parse_interactive_condition_object(
        data, offset, f"{field_name}.targetEntityConfig", 5, parse_target_entity
    )
    return {
        "conditionType": condition_type,
        "gameEventsUpdateConfig": game_events,
        "groupName": group_name,
        "levelEntityConfig": level_entity,
        "noUseConfig": no_use,
        "propertyData": property_data,
        "systemStateConfig": system_state,
        "systemUnlockConfig": system_unlock,
        "targetEntityConfig": target_entity,
    }, offset


def _parse_interactive_property_state(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    if offset >= len(data) or data[offset] != 20:
        marker = data[offset] if offset < len(data) else None
        raise ValueError(f"{field_name}:member-count={marker},expected=20")
    offset += 1
    attack_tags, offset = read_memorypack_i32(data, offset)
    check_perform_tag, offset = _read_interactive_strict_bool(
        data, offset, f"{field_name}.checkPerformTag"
    )
    condition_expression, offset = _read_interactive_string(
        data, offset, f"{field_name}.conditionExpression"
    )
    condition_count, offset = _read_interactive_count_or_null(
        data, offset, f"{field_name}.conditions"
    )
    conditions: list[dict[str, Any]] = []
    for index in range(condition_count or 0):
        if offset >= len(data) or data[offset] != 9:
            marker = data[offset] if offset < len(data) else None
            raise ValueError(
                f"{field_name}.conditions[{index}]:member-count={marker},expected=9"
            )
        condition, offset = _parse_interactive_base_condition(
            data, offset + 1, f"{field_name}.conditions[{index}]"
        )
        conditions.append(condition)
    event_id, offset = _read_interactive_string(
        data, offset, f"{field_name}.eventId"
    )
    expected_new_value, offset = read_memorypack_i32(data, offset)
    flags: dict[str, bool] = {}
    for flag_name in (
        "hasCustomLevelEvent",
        "ignoreClientExpectedValue",
        "ignoreInSpace",
        "invokeOnceBeforeEndScan",
        "isContinuous",
    ):
        flags[flag_name], offset = _read_interactive_strict_bool(
            data, offset, f"{field_name}.{flag_name}"
        )
    logic_cd, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(logic_cd):
        raise ValueError(f"{field_name}.logicCD:non-finite")
    option_icon, offset = _read_interactive_string(
        data, offset, f"{field_name}.optionIcon"
    )
    if offset >= len(data):
        raise ValueError(f"{field_name}.optionName:truncated-marker")
    lang_marker = data[offset]
    offset += 1
    option_name: str | None = None
    if lang_marker != 0xFF:
        if lang_marker != 1:
            raise ValueError(
                f"{field_name}.optionName:member-count={lang_marker},expected=1"
            )
        option_name, offset = _read_interactive_string(
            data, offset, f"{field_name}.optionName.key"
        )
    perform_tag, offset = read_memorypack_i32(data, offset)
    step_on_force, offset = _read_interactive_strict_bool(
        data, offset, f"{field_name}.stepOnForceTrigger"
    )
    step_on_stay_time, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(step_on_stay_time):
        raise ValueError(f"{field_name}.stepOnStayTime:non-finite")
    trigger_changed, offset = _read_interactive_strict_bool(
        data, offset, f"{field_name}.triggerBasePropertyChanged"
    )
    trigger_id, offset = read_memorypack_i32(data, offset)
    trigger_type, offset = read_memorypack_i32(data, offset)
    return {
        "attackTags": attack_tags,
        "checkPerformTag": check_perform_tag,
        "conditionExpression": condition_expression,
        "conditions": conditions,
        "eventId": event_id,
        "expectedNewValue": expected_new_value,
        **flags,
        "logicCD": round(logic_cd, 6),
        "optionIcon": option_icon,
        "optionName": option_name,
        "performTag": perform_tag,
        "stepOnForceTrigger": step_on_force,
        "stepOnStayTime": round(step_on_stay_time, 6),
        "triggerBasePropertyChanged": trigger_changed,
        "triggerId": trigger_id,
        "triggerType": trigger_type,
    }, offset


def _parse_interactive_trigger_condition_fields(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    """Decode the inherited three-member ``TriggerCondition`` body."""

    condition_expression, offset = _read_interactive_string(
        data, offset, f"{field_name}.conditionExpression"
    )
    condition_count, offset = _read_interactive_count_or_null(
        data, offset, f"{field_name}.conditions", max_count=1_000
    )
    conditions: list[dict[str, Any] | None] = []
    for index in range(condition_count or 0):
        label = f"{field_name}.conditions[{index}]"
        if offset >= len(data):
            raise ValueError(f"{label}:truncated-marker")
        marker = data[offset]
        offset += 1
        if marker == 0xFF:
            conditions.append(None)
            continue
        if marker != 9:
            raise ValueError(f"{label}:member-count={marker},expected=9")
        condition, offset = _parse_interactive_base_condition(
            data, offset, label
        )
        conditions.append(condition)
    trigger_type, offset = read_memorypack_i32(data, offset)
    return {
        "conditionExpression": condition_expression,
        "conditions": conditions,
        "triggerType": trigger_type,
    }, offset


def _parse_interactive_trigger_behaviour(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any] | None, int]:
    """Decode the current four-member ``TriggerBehaviourBase`` wrapper."""

    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-marker")
    marker = data[offset]
    offset += 1
    if marker == 0xFF:
        return None, offset
    if marker != 4:
        raise ValueError(f"{field_name}:member-count={marker},expected=4")

    table_count, offset = _read_interactive_count_or_null(
        data, offset, f"{field_name}.conditions", max_count=1_000
    )
    table_conditions: list[dict[str, Any] | None] = []
    for index in range(table_count or 0):
        label = f"{field_name}.conditions[{index}]"
        if offset >= len(data):
            raise ValueError(f"{label}:truncated-marker")
        item_marker = data[offset]
        offset += 1
        if item_marker == 0xFF:
            table_conditions.append(None)
            continue
        if item_marker != 4:
            raise ValueError(f"{label}:member-count={item_marker},expected=4")
        row, offset = _parse_interactive_trigger_condition_fields(
            data, offset, label
        )
        field_name_value, offset = _read_interactive_string(
            data, offset, f"{label}.fieldName"
        )
        table_conditions.append({**row, "fieldName": field_name_value})

    property_key, offset = _read_interactive_string(
        data, offset, f"{field_name}.propertyKey"
    )
    server_count, offset = _read_interactive_count_or_null(
        data, offset, f"{field_name}.serverConditions", max_count=1_000
    )
    server_conditions: list[dict[str, Any] | None] = []
    for index in range(server_count or 0):
        label = f"{field_name}.serverConditions[{index}]"
        if offset >= len(data):
            raise ValueError(f"{label}:truncated-marker")
        item_marker = data[offset]
        offset += 1
        if item_marker == 0xFF:
            server_conditions.append(None)
            continue
        if item_marker != 3:
            raise ValueError(f"{label}:member-count={item_marker},expected=3")
        row, offset = _parse_interactive_trigger_condition_fields(
            data, offset, label
        )
        server_conditions.append(row)

    behaviour_type, offset = read_memorypack_i32(data, offset)
    if behaviour_type not in (0, 1, 2):
        raise ValueError(f"{field_name}.type={behaviour_type}")
    return {
        "memberCount": marker,
        "conditions": table_conditions,
        "propertyKey": property_key,
        "serverConditions": server_conditions,
        "type": behaviour_type,
    }, offset


def parse_interactive_base_trigger_component(
    data: bytes,
    offset: int,
    tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Decode current BaseTrigger, property states and trigger behaviour."""

    if tag not in INTERACTIVE_BASE_TRIGGER_COMPONENT_TAGS:
        raise ValueError(f"baseTrigger.tag=0x{tag:04x}")
    if member_count != INTERACTIVE_BASE_TRIGGER_MEMBER_COUNT:
        raise ValueError(f"baseTrigger.memberCount={member_count}")
    start = offset
    if offset + 4 > len(data):
        raise ValueError("baseTrigger.propertyList:truncated")
    instance_marker = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if instance_marker != MEMORYPACK_NULL_COUNT:
        raise ValueError(f"baseTrigger.propertyList={instance_marker}")
    state_count, offset = read_memorypack_u32_count(
        data, offset, "baseTrigger.propertyStateData", max_count=1_000
    )
    states: list[dict[str, Any]] = []
    for index in range(state_count):
        state, offset = _parse_interactive_property_state(
            data, offset, f"baseTrigger.propertyStateData[{index}]"
        )
        states.append(state)
    trigger_behaviour, offset = _parse_interactive_trigger_behaviour(
        data, offset, "baseTrigger.triggerBehaviourBase"
    )
    return {
        "tag": f"0x{tag:04x}",
        "type": INTERACTIVE_BASE_TRIGGER_COMPONENT_TAGS[tag],
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "nullPropertyListPropertyStatesAndTriggerBehaviour",
        "fieldOrder": ["propertyList", "propertyStateData", "triggerBehaviourBase"],
        "propertyList": None,
        "schemaSource": (
            "current BaseTrigger, PropertyStateData and BaseConditionData generated "
            "wrapper order, including inherited DynamicProperty.propertyList; selected-build generic joins for TableFieldCondition and ServerPropertyCondition lists; sequential cursor"
        ),
        "propertyStateCount": state_count,
        "conditionCount": sum(len(row["conditions"]) for row in states),
        "conditionExpressions": [
            str(row.get("conditionExpression") or "")
            for row in states
            if row.get("conditionExpression")
        ],
        "optionNames": [
            str(row.get("optionName") or "")
            for row in states
            if row.get("optionName")
        ],
        "propertyStates": states,
        "triggerBehaviourBase": trigger_behaviour,
    }, offset


def _parse_interactive_string_list(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_count: int = 4096,
) -> tuple[list[str] | None, int]:
    count, offset = _read_interactive_count_or_null(
        data, offset, field_name, max_count=max_count
    )
    if count is None:
        return None, offset
    values: list[str] = []
    for index in range(count):
        value, offset = require_memorypack_non_null_string(
            data, offset, f"{field_name}[{index}]", max_length=1024
        )
        values.append(value)
    return values, offset


def _parse_interactive_empty_wrapper_dictionary(
    data: bytes,
    offset: int,
    field_name: str,
) -> int:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-marker")
    marker = data[offset]
    offset += 1
    if marker == 0xFF:
        return offset
    if marker != 1:
        raise ValueError(f"{field_name}:member-count={marker},expected=1")
    count, offset = read_memorypack_u32_count(
        data, offset, field_name, max_count=0
    )
    assert count == 0
    return offset


def _parse_interactive_empty_or_null_list(
    data: bytes,
    offset: int,
    field_name: str,
) -> int:
    count, offset = _read_interactive_count_or_null(
        data, offset, field_name, max_count=0
    )
    if count not in (None, 0):
        raise ValueError(f"{field_name}:unsupported-count={count}")
    return offset


def _parse_interactive_skill_data_bundle(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any] | None, int]:
    if offset >= len(data):
        raise ValueError("abilitySystem.skillDataBundle:truncated-marker")
    marker = data[offset]
    offset += 1
    if marker == 0xFF:
        return None, offset
    if marker != 20:
        raise ValueError(
            f"abilitySystem.skillDataBundle:member-count={marker},expected=20"
        )
    offset = _parse_interactive_empty_wrapper_dictionary(
        data, offset, "abilitySystem.skillDataBundle.activeSkillTypeOverrides"
    )
    active, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.skillDataBundle.allActiveSkillId"
    )
    normal, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.skillDataBundle.allNormalAttackId"
    )
    passive, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.skillDataBundle.allPassiveSkillId"
    )
    offset = _parse_interactive_empty_or_null_list(
        data, offset, "abilitySystem.skillDataBundle.comboSkillBlackboard"
    )
    offset = _parse_interactive_empty_or_null_list(
        data, offset, "abilitySystem.skillDataBundle.comboSkillConditions"
    )
    combo_skill_id, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.comboSkillId"
    )
    combo_priority, offset = read_memorypack_i32(data, offset)
    combo_node, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.comboSkillSpecialNodeName"
    )
    offset = _parse_interactive_empty_wrapper_dictionary(
        data, offset, "abilitySystem.skillDataBundle.defaultCmdMapping"
    )
    dodge, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.dodgeSkillId"
    )
    enable_combo, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.skillDataBundle.enableComboSkillBlackboard"
    )
    breaking, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.skillDataBundle.enabledBreakingNormalAttacks"
    )
    enabled_passive, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.skillDataBundle.enabledPassiveSkills"
    )
    hud, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.hudPanelName"
    )
    attack_list, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.skillDataBundle.normalAttackList"
    )
    normal_skill, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.normalSkillId"
    )
    plunge_end, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.plungingAttackEndId"
    )
    plunge_start, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.plungingAttackStartId"
    )
    ultimate, offset = _read_interactive_string(
        data, offset, "abilitySystem.skillDataBundle.ultimateSkillId"
    )
    return {
        "allActiveSkillId": active,
        "allNormalAttackId": normal,
        "allPassiveSkillId": passive,
        "comboSkillId": combo_skill_id,
        "comboSkillPriorityType": combo_priority,
        "comboSkillSpecialNodeName": combo_node,
        "dodgeSkillId": dodge,
        "enableComboSkillBlackboard": enable_combo,
        "enabledBreakingNormalAttacks": breaking,
        "enabledPassiveSkills": enabled_passive,
        "hudPanelName": hud,
        "normalAttackList": attack_list,
        "normalSkillId": normal_skill,
        "plungingAttackEndId": plunge_end,
        "plungingAttackStartId": plunge_start,
        "ultimateSkillId": ultimate,
    }, offset


def parse_interactive_ability_system_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    """Decode the current 38-member interactive AbilitySystem wrapper.

    The generated reader consumes the 34 inherited AbilitySystemData members
    first, in setter order, followed by the four AbilitySystemForInt members.
    Positive nested domains without a proved reader remain fail-closed.
    """

    if member_count != INTERACTIVE_ABILITY_SYSTEM_MEMBER_COUNT:
        raise ValueError(f"abilitySystem.memberCount={member_count}")
    start = offset
    accurate, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.accurateMarkTargetDistance"
    )
    bone_paths, offset = _parse_interactive_string_list(
        data, offset, "abilitySystem.bakedMeshPointBonePathList"
    )
    offset = _parse_interactive_empty_wrapper_dictionary(
        data, offset, "abilitySystem.bakedMeshPoints"
    )
    if offset >= len(data) or data[offset] != 2:
        marker = data[offset] if offset < len(data) else None
        raise ValueError(f"abilitySystem.battleRootData.member-count={marker}")
    offset += 1
    override_battle_root, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.battleRootData.overrideBattleRoot"
    )
    root_mount_point, offset = read_memorypack_i32(data, offset)
    for name in ("buffDuringPoiseExist", "buffDuringZeroPoise"):
        offset = _parse_interactive_empty_or_null_list(
            data, offset, f"abilitySystem.{name}"
        )
    check_ally, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.checkAllyBlockableMoveCollider"
    )
    custom_distance, offset = read_memorypack_f32(data, offset)
    custom_height, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(custom_distance) or not math.isfinite(custom_height):
        raise ValueError("abilitySystem.markTargetDistance:non-finite")
    offset = _parse_interactive_empty_or_null_list(
        data, offset, "abilitySystem.dashBuff"
    )
    if offset >= len(data) or data[offset] != 0xFF:
        marker = data[offset] if offset < len(data) else None
        raise ValueError(f"abilitySystem.deadEffect:unsupported-marker={marker}")
    offset += 1
    offset = _parse_interactive_empty_or_null_list(
        data, offset, "abilitySystem.deadEffects"
    )
    default_hit, offset = _read_interactive_string(
        data, offset, "abilitySystem.defaultHitEffect"
    )
    effect_scale, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(effect_scale):
        raise ValueError("abilitySystem.effectScale:non-finite")
    offset = _parse_interactive_empty_or_null_list(
        data, offset, "abilitySystem.entityBlackboard"
    )
    offset = _parse_interactive_empty_wrapper_dictionary(
        data, offset, "abilitySystem.extraShapesData"
    )
    health_type, offset = read_memorypack_i32(data, offset)
    hit_flash, offset = _read_interactive_string(
        data, offset, "abilitySystem.hitFlashAsset"
    )
    play_hit_flash, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.isPlayHitFlash"
    )
    max_potential_buff, offset = _read_interactive_string(
        data, offset, "abilitySystem.maxPotentialEffectBuffId"
    )
    if offset >= len(data) or data[offset] != 0xFF:
        marker = data[offset] if offset < len(data) else None
        raise ValueError(f"abilitySystem.modeConfig:unsupported-marker={marker}")
    offset += 1
    flags: dict[str, bool] = {}
    for name in (
        "overrideDeadEffect",
        "overrideMarkTargetDistance",
        "overrideMarkTargetHeight",
        "playPoiseBrokenEffect",
    ):
        flags[name], offset = _read_interactive_strict_bool(
            data, offset, f"abilitySystem.{name}"
        )
    if offset + 16 > len(data):
        raise ValueError("abilitySystem.plungingAttackData:truncated")
    plunging_blob = data[offset:offset + 16]
    offset += 16
    if plunging_blob[0] not in (0, 1):
        raise ValueError(
            f"abilitySystem.plungingAttackData.enable={plunging_blob[0]}"
        )
    plunging_floats = struct.unpack_from("<3f", plunging_blob, 4)
    if not all(math.isfinite(value) for value in plunging_floats):
        raise ValueError("abilitySystem.plungingAttackData:non-finite")
    poise_end, offset = read_memorypack_f32(data, offset)
    poise_immobilize, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(poise_end) or not math.isfinite(poise_immobilize):
        raise ValueError("abilitySystem.poiseTiming:non-finite")
    offset = _parse_interactive_empty_wrapper_dictionary(
        data, offset, "abilitySystem.preloadAbilityEntities"
    )
    if offset >= len(data) or data[offset] != 2:
        marker = data[offset] if offset < len(data) else None
        raise ValueError(f"abilitySystem.shapeData.member-count={marker}")
    offset += 1
    detected_height, offset = read_memorypack_f32(data, offset)
    detected_radius, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(detected_height) or not math.isfinite(detected_radius):
        raise ValueError("abilitySystem.shapeData:non-finite")
    offset = _parse_interactive_empty_wrapper_dictionary(
        data, offset, "abilitySystem.skillCameraConfig"
    )
    skill_bundle, offset = _parse_interactive_skill_data_bundle(data, offset)
    if offset >= len(data):
        raise ValueError("abilitySystem.uiData:truncated-marker")
    ui_marker = data[offset]
    offset += 1
    if ui_marker == 0xFF:
        ui_data = None
    elif ui_marker == 10:
        if offset >= len(data) or data[offset] != 0xFF:
            marker = data[offset] if offset < len(data) else None
            raise ValueError(
                f"abilitySystem.uiData.damageTextRelated:unsupported-marker={marker}"
            )
        offset += 1
        if offset + 29 > len(data):
            raise ValueError("abilitySystem.uiData:truncated")
        raw = data[offset:offset + 29]
        offset += 29
        if raw[16] not in (0, 1) or any(value not in (0, 1) for value in raw[25:29]):
            raise ValueError("abilitySystem.uiData:invalid-bool")
        floats = struct.unpack_from("<2f", raw, 0) + (struct.unpack_from("<f", raw, 8)[0],) + struct.unpack_from("<2f", raw, 17)
        if not all(math.isfinite(value) for value in floats):
            raise ValueError("abilitySystem.uiData:non-finite")
        ui_data = {"rawHex": raw.hex()}
    else:
        raise ValueError(f"abilitySystem.uiData.member-count={ui_marker}")
    unlock, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.unlockAfterOutScreen"
    )
    collider_start = offset
    collider_end = collider_start + INTERACTIVE_ABILITY_SYSTEM_COLLIDER_SHAPE_LENGTH
    if collider_end > len(data):
        raise ValueError("abilitySystem.battleShapeData:truncated")
    collider_blob = data[collider_start:collider_end]
    if not collider_blob or collider_blob[0] != 16:
        marker = collider_blob[0] if collider_blob else None
        raise ValueError(f"abilitySystem.battleShapeData.member-count={marker}")
    offset = collider_end
    property_list, offset = parse_interactive_component_property_map(
        data, offset, "abilitySystem.propertyList"
    )
    offset = _parse_interactive_empty_or_null_list(
        data, offset, "abilitySystem.skillBlackboardDataPairs"
    )
    use_self, offset = _read_interactive_strict_bool(
        data, offset, "abilitySystem.useSelfBlackboard"
    )
    return {
        "tag": f"0x{INTERACTIVE_ABILITY_SYSTEM_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS[INTERACTIVE_ABILITY_SYSTEM_COMPONENT_TAG],
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "abilitySystemDataThenAbilitySystemForIntData",
        "schemaSource": (
            "current generated reader/setter order; nested wrapper member counts; "
            "exact next-union handoff across supported current InteractiveData payloads"
        ),
        "accurateMarkTargetDistance": accurate,
        "bakedMeshPointBonePathList": bone_paths,
        "battleRootData": {
            "overrideBattleRoot": override_battle_root,
            "rootMountPoint": root_mount_point,
        },
        "checkAllyBlockableMoveCollider": check_ally,
        "customMarkTargetDistance": round(custom_distance, 6),
        "customMarkTargetHeight": round(custom_height, 6),
        "defaultHitEffect": default_hit,
        "effectScale": round(effect_scale, 6),
        "healthType": health_type,
        "hitFlashAsset": hit_flash,
        "isPlayHitFlash": play_hit_flash,
        "maxPotentialEffectBuffId": max_potential_buff,
        **flags,
        "poiseBrokenEndTime": round(poise_end, 6),
        "poiseKnotBreakImmobilizeTime": round(poise_immobilize, 6),
        "shapeData": {
            "detectedHeight": round(detected_height, 6),
            "detectedRadius": round(detected_radius, 6),
        },
        "skillDataBundle": skill_bundle,
        "uiData": ui_data,
        "unlockAfterOutScreen": unlock,
        "battleShapeDataByteLength": len(collider_blob),
        "propertyListCount": int(property_list.get("count") or 0),
        "propertyKeys": list((property_list.get("keyCounts") or {}).keys()),
        "useSelfBlackboard": use_self,
    }, offset


def parse_interactive_template_config_properties(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    """Decode the exact template fields through ``configProperties``.

    ``offset`` must be the proven end of the complete component list.  The
    serialized order comes from the current ForMemoryPack setters: five
    scalar lifecycle fields, two property maps, ``aoiRadiusType``, then the
    authored template config map.  Parsing every preceding field prevents a
    coincidental property-map-shaped byte range from being accepted.
    """

    start = offset
    delay_recycle_perform_time, offset = read_memorypack_f32(data, offset)
    delay_to_recycle_time, offset = read_memorypack_f32(data, offset)
    if offset >= len(data):
        raise ValueError("interactiveTemplate.enableBornFadeIn:truncated")
    enable_born_fade_in = data[offset]
    offset += 1
    if enable_born_fade_in not in (0, 1):
        raise ValueError(
            f"interactiveTemplate.enableBornFadeIn={enable_born_fade_in}"
        )
    fade_in_time, offset = read_memorypack_f32(data, offset)
    if offset >= len(data):
        raise ValueError("interactiveTemplate.sendDieEvent:truncated")
    send_die_event = data[offset]
    offset += 1
    if send_die_event not in (0, 1):
        raise ValueError(f"interactiveTemplate.sendDieEvent={send_die_event}")
    all_global, offset = parse_interactive_component_property_map(
        data, offset, "interactiveTemplate.allGlobalSaveProperties"
    )
    all_map, offset = parse_interactive_component_property_map(
        data, offset, "interactiveTemplate.allMapSaveProperties"
    )
    aoi_radius_type, offset = read_memorypack_i32(data, offset)
    config_offset = offset
    config, offset = parse_interactive_component_property_map(
        data,
        offset,
        "interactiveTemplate.configProperties",
        sample_limit=4096,
    )
    audio_rows: list[dict[str, Any]] = []
    for row in config.get("sampleRows") or []:
        values = [
            str(value.get("stringTail") or "").strip()
            for value in row.get("values") or []
            if str(value.get("stringTail") or "").strip().startswith("au_")
        ]
        if not values:
            continue
        audio_rows.append({
            "key": str(row.get("key") or ""),
            "events": values,
            "valueType": row.get("valueType"),
            "identityKind": (
                "rtpcParameter"
                if all(value.startswith("au_rtpc_") for value in values)
                else "wwiseEvent"
            ),
        })
    return {
        "byteLength": offset - start,
        "schemaSource": (
            "current InteractiveTemplateData ForMemoryPack setter order; "
            "all preceding scalar and property-map fields decoded exactly"
        ),
        "delayRecyclePerformTime": round(delay_recycle_perform_time, 6),
        "delayToRecycleTime": round(delay_to_recycle_time, 6),
        "enableBornFadeIn": bool(enable_born_fade_in),
        "fadeInTime": round(fade_in_time, 6),
        "sendDieEvent": bool(send_die_event),
        "allGlobalSavePropertyCount": int(all_global.get("count") or 0),
        "allMapSavePropertyCount": int(all_map.get("count") or 0),
        "aoiRadiusType": aoi_radius_type,
        "configPropertiesOffset": format_offset(config_offset),
        "configPropertiesEndOffset": format_offset(offset),
        "configPropertyCount": int(config.get("count") or 0),
        "configPropertyKeys": list(config.get("keys") or []),
        "audioPropertyRows": audio_rows,
    }, offset


def _parse_interactive_template_variant(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    """Decode one current 14-member ``InteractiveTemplateVariant`` value."""

    start = offset

    def strict_bool(label: str) -> bool:
        nonlocal offset
        if offset >= len(data) or data[offset] not in (0, 1):
            actual = data[offset] if offset < len(data) else None
            raise ValueError(f"{label}:invalid-bool={actual}")
        value = bool(data[offset])
        offset += 1
        return value

    def nullable_count(label: str, max_count: int = 10_000) -> int | None:
        nonlocal offset
        if offset + 4 > len(data):
            raise ValueError(f"{label}:truncated-count")
        value = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if value == MEMORYPACK_NULL_COUNT:
            return None
        if value > max_count:
            raise ValueError(f"{label}:invalid-count={value}")
        return value

    def optional_scalar(label: str, kind: str) -> dict[str, Any]:
        nonlocal offset
        enabled = strict_bool(f"{label}.enabled")
        if offset + 7 > len(data) or data[offset:offset + 3] != b"\x00\x00\x00":
            padding = data[offset:offset + 3].hex()
            raise ValueError(f"{label}:invalid-padding={padding}")
        offset += 3
        if kind == "float":
            value, offset = read_memorypack_f32(data, offset)
            if not math.isfinite(value):
                raise ValueError(f"{label}:non-finite")
            value = round(value, 6)
        else:
            value, offset = read_memorypack_i32(data, offset)
        return {"enabled": enabled, "value": value}

    def optional_reference_header(label: str) -> bool:
        nonlocal offset
        if offset >= len(data) or data[offset] != 2:
            actual = data[offset] if offset < len(data) else None
            raise ValueError(f"{label}:member-count={actual}")
        offset += 1
        return strict_bool(f"{label}.enabled")

    def optional_string(label: str) -> dict[str, Any]:
        nonlocal offset
        enabled = optional_reference_header(label)
        value, offset, error = read_memorypack_utf8_string(
            data, offset, max_length=1024
        )
        if error:
            raise ValueError(f"{label}:{error}")
        return {"enabled": enabled, "value": value}

    def optional_tag_array(label: str) -> dict[str, Any]:
        nonlocal offset
        enabled = optional_reference_header(label)
        count = nullable_count(label)
        values: list[int] = []
        for _ in range(count or 0):
            value, offset = read_memorypack_i32(data, offset)
            values.append(value)
        return {"enabled": enabled, "value": None if count is None else values}

    def optional_mount_points(label: str) -> dict[str, Any]:
        nonlocal offset
        enabled = optional_reference_header(label)
        count = nullable_count(label)
        values: list[dict[str, Any]] = []
        for index in range(count or 0):
            if offset >= len(data) or data[offset] != 2:
                actual = data[offset] if offset < len(data) else None
                raise ValueError(f"{label}[{index}]:member-count={actual}")
            offset += 1
            mount_point, offset = read_memorypack_i32(data, offset)
            name, offset = require_memorypack_non_null_string(
                data, offset, f"{label}[{index}].name", max_length=256
            )
            values.append({"mountPoint": mount_point, "name": name})
        return {"enabled": enabled, "value": None if count is None else values}

    def optional_string_array(label: str) -> dict[str, Any]:
        nonlocal offset
        enabled = optional_reference_header(label)
        count = nullable_count(label)
        values: list[str] = []
        for index in range(count or 0):
            value, offset = require_memorypack_non_null_string(
                data, offset, f"{label}[{index}]", max_length=256
            )
            values.append(value)
        return {"enabled": enabled, "value": None if count is None else values}

    if offset >= len(data) or data[offset] != 14:
        actual = data[offset] if offset < len(data) else None
        raise ValueError(f"{field_name}:member-count={actual}")
    offset += 1
    aoi_radius_type = optional_scalar(f"{field_name}.aoiRadiusType", "int")
    born_tag = optional_tag_array(f"{field_name}.bornTag")
    if offset >= len(data) or data[offset] != 1:
        actual = data[offset] if offset < len(data) else None
        raise ValueError(f"{field_name}.componentDiffProperties:object-marker={actual}")
    offset += 1
    component_count = nullable_count(f"{field_name}.componentDiffProperties")
    if component_count is None:
        raise ValueError(f"{field_name}.componentDiffProperties:null-count")
    component_diff_properties: list[dict[str, Any]] = []
    for index in range(component_count):
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}.componentDiffProperties[{index}].key",
            max_length=256,
        )
        if offset >= len(data) or data[offset] != 1:
            actual = data[offset] if offset < len(data) else None
            raise ValueError(
                f"{field_name}.componentDiffProperties[{index}].value.member-count={actual}"
            )
        value, offset = parse_interactive_component_property_map(
            data,
            offset + 1,
            f"{field_name}.componentDiffProperties[{index}].value",
            sample_limit=4096,
        )
        component_diff_properties.append({"key": key, "value": value})
    delay_recycle = optional_scalar(
        f"{field_name}.delayRecyclePerformTime", "float"
    )
    delay_to_recycle = optional_scalar(f"{field_name}.delayToRecycleTime", "float")
    diff_properties, offset = parse_interactive_component_property_map(
        data, offset, f"{field_name}.diffProperties", sample_limit=4096
    )
    fac_occ_dis = optional_scalar(f"{field_name}.facOccDis", "float")
    faction_index = optional_scalar(f"{field_name}.factionIndex", "int")
    global_var_diff, offset = parse_interactive_component_property_map(
        data, offset, f"{field_name}.globalVarDiff", sample_limit=4096
    )
    hide_in_dialog = {
        "enabled": strict_bool(f"{field_name}.hideInDialog.enabled"),
        "value": strict_bool(f"{field_name}.hideInDialog.value"),
    }
    map_var_diff, offset = parse_interactive_component_property_map(
        data, offset, f"{field_name}.mapVarDiff", sample_limit=4096
    )
    model_id = optional_string(f"{field_name}.modelId")
    mount_points = optional_mount_points(f"{field_name}.mountPoints")
    guide_variables = optional_string_array(
        f"{field_name}.relatedGuideTimestampGameVar"
    )
    return {
        "sourceOffset": start,
        "endOffset": offset,
        "memberCount": 14,
        "aoiRadiusType": aoi_radius_type,
        "bornTag": born_tag,
        "componentDiffProperties": component_diff_properties,
        "delayRecyclePerformTime": delay_recycle,
        "delayToRecycleTime": delay_to_recycle,
        "diffProperties": diff_properties,
        "facOccDis": fac_occ_dis,
        "factionIndex": faction_index,
        "globalVarDiff": global_var_diff,
        "hideInDialog": hide_in_dialog,
        "mapVarDiff": map_var_diff,
        "modelId": model_id,
        "mountPoints": mount_points,
        "relatedGuideTimestampGameVar": guide_variables,
    }, offset


def parse_interactive_template_empty_tail(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    """Consume the exact supported-action-map template tail.

    The field order is the current generated wrapper order. This variant is
    deliberately narrow around ``dataMap``: positive bodies use the reviewed
    sequential action-map codec, and unsupported unions fail closed. The generated
    variant dictionary, mount-point, dictionary, string-array, and
    ParamKeyValue-list fields use complete typed codecs and may be populated.
    """

    start = offset

    def require_byte(value: int, label: str) -> None:
        nonlocal offset
        if offset >= len(data):
            raise ValueError(f"interactiveTemplate.{label}:truncated")
        actual = data[offset]
        offset += 1
        if actual != value:
            raise ValueError(
                f"interactiveTemplate.{label}=0x{actual:02x},expected=0x{value:02x}"
            )

    def read_nullable_count(label: str, *, max_count: int = 10_000) -> int | None:
        nonlocal offset
        if offset + 4 > len(data):
            raise ValueError(f"interactiveTemplate.{label}:truncated")
        actual = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if actual == MEMORYPACK_NULL_COUNT:
            return None
        if actual > max_count:
            raise ValueError(f"interactiveTemplate.{label}={actual},max={max_count}")
        return actual

    def read_bool(label: str) -> bool:
        nonlocal offset
        if offset >= len(data):
            raise ValueError(f"interactiveTemplate.{label}:truncated")
        actual = data[offset]
        offset += 1
        if actual not in (0, 1):
            raise ValueError(f"interactiveTemplate.{label}={actual}")
        return bool(actual)

    def read_property_list(label: str) -> dict[str, Any] | None:
        nonlocal offset
        if offset + 4 > len(data):
            raise ValueError(f"interactiveTemplate.{label}:truncated")
        if struct.unpack_from("<I", data, offset)[0] == MEMORYPACK_NULL_COUNT:
            offset += 4
            return None
        value, offset = parse_interactive_component_property_map(
            data,
            offset,
            f"interactiveTemplate.{label}",
            sample_limit=4096,
        )
        return value

    data_map, offset = decode_action_serialized_map(data, offset)
    fac_occ_dis, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(fac_occ_dis):
        raise ValueError("interactiveTemplate.facOccDis:non-finite")
    hide_in_dialog = read_bool("hideInDialog")

    mount_point_count = read_nullable_count("mountPoints.count")
    mount_points: list[dict[str, Any]] = []
    for index in range(mount_point_count or 0):
        if offset >= len(data):
            raise ValueError(f"interactiveTemplate.mountPoints[{index}].memberCount:truncated")
        member_count = data[offset]
        offset += 1
        if member_count != 2:
            raise ValueError(
                f"interactiveTemplate.mountPoints[{index}].memberCount={member_count}"
            )
        mount_point, offset = read_memorypack_i32(data, offset)
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveTemplate.mountPoints[{index}].name",
            max_length=256,
        )
        mount_points.append({"mountPoint": mount_point, "name": name})

    require_byte(1, "propertyIdToKeyMap.objectMarker")
    property_id_to_key_count = read_nullable_count("propertyIdToKeyMap.count")
    if property_id_to_key_count is None:
        raise ValueError("interactiveTemplate.propertyIdToKeyMap.count=null")
    property_id_to_key: list[dict[str, Any]] = []
    for index in range(property_id_to_key_count):
        key, offset = read_memorypack_i32(data, offset)
        value, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveTemplate.propertyIdToKeyMap[{index}].value",
            max_length=256,
        )
        property_id_to_key.append({"key": key, "value": value})

    require_byte(1, "propertyKeyToIdMap.objectMarker")
    property_key_to_id_count = read_nullable_count("propertyKeyToIdMap.count")
    if property_key_to_id_count is None:
        raise ValueError("interactiveTemplate.propertyKeyToIdMap.count=null")
    property_key_to_id: list[dict[str, Any]] = []
    for index in range(property_key_to_id_count):
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveTemplate.propertyKeyToIdMap[{index}].key",
            max_length=256,
        )
        value, offset = read_memorypack_i32(data, offset)
        property_key_to_id.append({"key": key, "value": value})

    guide_count = read_nullable_count("relatedGuideTimestampGameVar.count")
    related_guide_timestamp_game_var: list[str] | None = None
    if guide_count is not None:
        related_guide_timestamp_game_var = []
        for index in range(guide_count):
            value, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"interactiveTemplate.relatedGuideTimestampGameVar[{index}]",
                max_length=256,
            )
            related_guide_timestamp_game_var.append(value)

    save_properties = read_property_list("saveProperties")
    require_byte(1, "templateVariant.objectMarker")
    template_variant_count = read_nullable_count("templateVariant.count")
    if template_variant_count is None:
        raise ValueError("interactiveTemplate.templateVariant.count=null")
    template_variants: list[dict[str, Any]] = []
    seen_variant_keys: set[str] = set()
    for index in range(template_variant_count):
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveTemplate.templateVariant[{index}].key",
            max_length=512,
        )
        if key in seen_variant_keys:
            raise ValueError(
                f"interactiveTemplate.templateVariant[{index}].duplicate-key={key!r}"
            )
        seen_variant_keys.add(key)
        value, offset = _parse_interactive_template_variant(
            data,
            offset,
            f"interactiveTemplate.templateVariant[{index}].value",
        )
        template_variants.append({"key": key, "value": value})
    temp_properties = read_property_list("tempProperties")
    use_global_var = read_bool("useGlobalVar")
    use_map_var = read_bool("useMapVar")
    if offset != len(data):
        raise ValueError(
            f"interactiveTemplate.emptyTail:trailing-bytes={len(data) - offset}"
        )
    return {
        "byteLength": offset - start,
        "schemaStatus": "named_exact",
        "schemaSource": (
            "current 26-field InteractiveTemplateData wrapper setter order; "
            "null or three-empty-list ActionSerializedMap plus typed mount-point, dictionary, string-array, "
            "and ParamKeyValue-list fields; typed 14-member template variants closed at EOF"
        ),
        "dataMap": data_map,
        "facOccDis": round(fac_occ_dis, 6),
        "hideInDialog": hide_in_dialog,
        "mountPointCount": mount_point_count,
        "mountPoints": mount_points,
        "propertyIdToKeyCount": property_id_to_key_count,
        "propertyIdToKeyMap": property_id_to_key,
        "propertyKeyToIdCount": property_key_to_id_count,
        "propertyKeyToIdMap": property_key_to_id,
        "relatedGuideTimestampGameVar": related_guide_timestamp_game_var,
        "savePropertyCount": None if save_properties is None else save_properties["count"],
        "saveProperties": save_properties,
        "templateVariantCount": template_variant_count,
        "templateVariants": template_variants,
        "tempPropertyCount": None if temp_properties is None else temp_properties["count"],
        "tempProperties": temp_properties,
        "useGlobalVar": use_global_var,
        "useMapVar": use_map_var,
    }, offset


def find_interactive_audio_property_maps(data: bytes) -> list[dict[str, Any]]:
    """Find complete typed property maps whose key explicitly denotes audio.

    This is intentionally narrower than a string scan.  A row is returned only
    when the enclosing MemoryPack property map parses completely and the
    selected key/value row contains a non-RTPC ``au_*`` identity.  The
    containing component remains unresolved unless another component decoder
    supplies it.
    """

    key_names = ("audio_key", "audio_key_start", "audio_key_loop", "audio_key_end", "hit_sound_event")
    candidate_ranges: set[tuple[int, int]] = set()
    rows: list[dict[str, Any]] = []
    for key_name in key_names:
        marker = struct.pack("<I", len(key_name)) + key_name.encode("utf-8")
        marker_offset = 0
        while True:
            marker_offset = data.find(marker, marker_offset)
            if marker_offset < 0:
                break
            search_start = max(0, marker_offset - 4096)
            matches: list[tuple[int, int, dict[str, Any]]] = []
            for property_offset in range(search_start, marker_offset + 1):
                try:
                    property_map, end = parse_interactive_component_property_map(
                        data,
                        property_offset,
                        "interactive.audioPropertyMap",
                        max_entries=256,
                    )
                except (UnicodeDecodeError, struct.error, ValueError):
                    continue
                if property_offset <= marker_offset < end and key_name in (property_map.get("keys") or []):
                    matches.append((property_offset, end, property_map))
            # A unique enclosing typed map is the fail-closed acceptance gate.
            unique = {(start, end): value for start, end, value in matches}
            if len(unique) == 1:
                (property_offset, end), property_map = next(iter(unique.items()))
                if (property_offset, end) not in candidate_ranges:
                    audio_rows: list[dict[str, Any]] = []
                    for row in property_map.get("sampleRows") or []:
                        key = str(row.get("key") or "")
                        if key not in key_names:
                            continue
                        values = [str(value) for value in (row.get("preview") or []) if value]
                        events = [
                            value for value in values
                            if value.startswith("au_") and not value.startswith("au_rtpc_")
                        ]
                        if events:
                            audio_rows.append({
                                "key": key,
                                "events": events,
                                "valueType": row.get("valueType"),
                                "identityKind": "wwiseEvent",
                            })
                    if audio_rows:
                        candidate_ranges.add((property_offset, end))
                        rows.append({
                            "propertyMapOffset": format_offset(property_offset),
                            "propertyMapEndOffset": format_offset(end),
                            "propertyMapCount": int(property_map.get("count") or 0),
                            "propertyKeys": list(property_map.get("keys") or []),
                            "audioPropertyRows": audio_rows,
                            "componentResolutionStatus": "containingComponentUnresolved",
                            "runtimePropertyConsumerStatus": "unresolved",
                            "runtimeEventPostingStatus": "notObserved",
                        })
            marker_offset += 1
    rows.sort(key=lambda row: int(str(row["propertyMapOffset"]), 16))
    return rows


def parse_interactive_common_perform_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT:
        raise ValueError(f"commonPerform.memberCount={member_count}")
    start = offset
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        "commonPerform.dynamicPropertyMap",
    )
    previews = interactive_property_preview_by_key(property_map)

    perform_property_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "commonPerform.propertyDataList",
        max_count=4096,
    )
    rows: list[dict[str, Any]] = []
    property_name_counts: Counter[str] = Counter()
    property_type_counts: Counter[int] = Counter()
    property_type_name_counts: Counter[str] = Counter()
    is_property_counts: Counter[bool] = Counter()
    for row_index in range(perform_property_count):
        if offset >= len(data):
            raise ValueError(f"commonPerform.propertyDataList[{row_index}].memberCount:truncated")
        row_member_count = data[offset]
        offset += 1
        if row_member_count != INTERACTIVE_PERFORM_PROPERTY_ROW_MEMBER_COUNT:
            raise ValueError(
                f"commonPerform.propertyDataList[{row_index}].memberCount={row_member_count}"
            )
        if offset >= len(data):
            raise ValueError(f"commonPerform.propertyDataList[{row_index}].isProperty:truncated")
        is_property_byte = data[offset]
        if is_property_byte not in (0, 1):
            raise ValueError(
                f"commonPerform.propertyDataList[{row_index}].isProperty.byte={is_property_byte}"
            )
        is_property, offset = read_memorypack_bool(data, offset)
        property_name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"commonPerform.propertyDataList[{row_index}].propertyName",
            max_length=256,
        )
        property_type, offset = read_memorypack_i32(data, offset)
        property_type_name = INTERACTIVE_PERFORM_PROPERTY_TYPE_NAMES.get(
            property_type,
            f"type_{property_type}",
        )
        property_name_counts[property_name] += 1
        property_type_counts[property_type] += 1
        property_type_name_counts[property_type_name] += 1
        is_property_counts[is_property] += 1
        if len(rows) < 24:
            rows.append({
                "memberCount": row_member_count,
                "propertyName": property_name,
                "propertyType": property_type,
                "propertyTypeName": property_type_name,
                "isProperty": is_property,
            })

    if offset >= len(data):
        raise ValueError("commonPerform.syncGameplayLock:truncated")
    sync_gameplay_lock_byte = data[offset]
    if sync_gameplay_lock_byte not in (0, 1):
        raise ValueError(f"commonPerform.syncGameplayLock.byte={sync_gameplay_lock_byte}")
    sync_gameplay_lock, offset = read_memorypack_bool(data, offset)

    return {
        "tag": f"0x{INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "dynamicPropertyMapPerformPropertyListAndLockFlag",
        "schemaSource": (
            "component fields identified from local IL2CPP metadata; custom MemoryPack row byte order "
            "validated as bool, string, int32 by exact next-component handoff across export_full InteractiveData"
        ),
        "dynamicPropertyMapCount": int(property_map.get("count") or 0),
        "dynamicPropertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "dynamicPropertyValueTypeCounts": property_map.get("valueTypeCounts") or {},
        "dynamicPropertyValueCountCounts": property_map.get("valueCountCounts") or {},
        "dynamicPropertyTailCounts": property_map.get("tailCounts") or {},
        "dynamicPropertyStringTailCounts": property_map.get("stringTailCounts") or {},
        "dynamicPreviewByKey": previews,
        "sampleDynamicProperties": (property_map.get("sampleRows") or [])[:16],
        "performPropertyCount": perform_property_count,
        "performPropertyNameCounts": dict(property_name_counts.most_common(32)),
        "performPropertyTypeCounts": {str(key): count for key, count in property_type_counts.most_common(16)},
        "performPropertyTypeNameCounts": dict(property_type_name_counts.most_common(16)),
        "performPropertyIsPropertyCounts": {str(key): count for key, count in is_property_counts.most_common(4)},
        "samplePerformProperties": rows,
        "syncGameplayLock": sync_gameplay_lock,
        "syncGameplayLockByte": sync_gameplay_lock_byte,
    }, offset


def parse_interactive_hittable_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_HITTABLE_MEMBER_COUNT:
        raise ValueError(f"hittable.memberCount={member_count}")
    start = offset
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        "hittable.propertyData",
    )
    previews = interactive_property_preview_by_key(property_map)

    collider_start = offset
    collider_end = collider_start + INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH
    if collider_end + 4 > len(data):
        raise ValueError("hittable.colliderShapeData:truncated")
    collider_blob = data[collider_start:collider_end]
    collider_member_count = collider_blob[0] if collider_blob else None
    if collider_member_count != 16:
        raise ValueError(f"hittable.colliderShapeData.memberCount={collider_member_count}")
    if collider_blob.count(b"\xff\xff\xff\xff") < 4:
        raise ValueError("hittable.colliderShapeData.nullMarkersLow")
    offset = collider_end

    enable_extra_check_bytes = data[offset:offset + 4]
    offset += 4
    if enable_extra_check_bytes[:3] != b"\x00\x00\x00" or enable_extra_check_bytes[3] not in (0, 1):
        raise ValueError(f"hittable.enableExtraCheck.bytes={enable_extra_check_bytes.hex()}")
    enable_extra_check = bool(enable_extra_check_bytes[3])

    return {
        "tag": f"0x{INTERACTIVE_HITTABLE_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_HITTABLE_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapColliderShapeAndFlag",
        "schemaSource": (
            "fields recovered from local IL2CPP metadata; shared property map, fixed-size "
            "ColliderShapeData blob, and trailing enableExtraCheck flag validated by next-component handoff"
        ),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "previewByKey": previews,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
        "colliderShapeDataMemberCount": collider_member_count,
        "colliderShapeDataByteLength": INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH,
        "colliderShapeDataNullMarkerCount": collider_blob.count(b"\xff\xff\xff\xff"),
        "colliderShapeDataPrefixHex": collider_blob[:24].hex(),
        "enableExtraCheck": enable_extra_check,
        "enableExtraCheckBytes": enable_extra_check_bytes.hex(),
    }, offset


def parse_interactive_logic_controller_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT:
        raise ValueError(f"logicController.memberCount={member_count}")
    start = offset
    logic_type, offset = read_memorypack_i32(data, offset)
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        "logicController.propertyList",
    )
    previews = interactive_property_preview_by_key(property_map)
    return {
        "tag": f"0x{INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "logicTypeAndPropertyMap",
        "schemaSource": (
            "field order recovered from local IL2CPP ForMemoryPack setters; "
            "propertyList body validated as the shared Interactive property-map grammar"
        ),
        "logicType": logic_type,
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "previewByKey": previews,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
    }, offset


def parse_interactive_audio_component(
    data: bytes,
    offset: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if member_count != INTERACTIVE_AUDIO_MEMBER_COUNT:
        raise ValueError(f"interactiveAudio.memberCount={member_count}")
    start = offset
    prefix_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "interactiveAudio.prefix",
        max_count=0,
    )
    if offset >= len(data):
        raise ValueError("interactiveAudio.audioData.memberCount:truncated")
    audio_data_member_count = data[offset]
    offset += 1
    if audio_data_member_count != INTERACTIVE_AUDIO_DATA_MEMBER_COUNT:
        raise ValueError(f"interactiveAudio.audioData.memberCount={audio_data_member_count}")

    audio_name_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "interactiveAudio.audioNameDict",
        max_count=4096,
    )
    audio_rows: list[dict[str, Any]] = []
    state_counts: Counter[int] = Counter()
    state_name_counts: Counter[str] = Counter()
    audio_event_counts: Counter[str] = Counter()
    for row_index in range(audio_name_count):
        state, offset = read_memorypack_i32(data, offset)
        state_name = INTERACTIVE_AUDIO_TRIGGER_STATE_NAMES.get(state, f"state_{state}")
        state_counts[state] += 1
        state_name_counts[state_name] += 1
        event_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"interactiveAudio.audioNameDict[{row_index}].audio",
            max_count=4096,
        )
        events: list[str] = []
        for event_index in range(event_count):
            event, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"interactiveAudio.audioNameDict[{row_index}].audio[{event_index}]",
                max_length=256,
            )
            events.append(event)
            audio_event_counts[event] += 1
        audio_rows.append({
            "state": state,
            "stateName": state_name,
            "audioCount": event_count,
            "events": events,
        })

    custom_audio_count, offset = read_memorypack_u32_count(
        data,
        offset,
        "interactiveAudio.customAudioData",
        max_count=4096,
    )
    custom_rows: list[dict[str, Any]] = []
    custom_name_counts: Counter[str] = Counter()
    custom_event_counts: Counter[str] = Counter()
    for row_index in range(custom_audio_count):
        if offset >= len(data):
            raise ValueError(f"interactiveAudio.customAudioData[{row_index}].memberCount:truncated")
        custom_member_count = data[offset]
        offset += 1
        if custom_member_count != 3:
            raise ValueError(f"interactiveAudio.customAudioData[{row_index}].memberCount={custom_member_count}")
        event, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveAudio.customAudioData[{row_index}].event",
            max_length=256,
        )
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveAudio.customAudioData[{row_index}].name",
            max_length=256,
        )
        note, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"interactiveAudio.customAudioData[{row_index}].note",
            max_length=512,
        )
        custom_name_counts[name] += 1
        custom_event_counts[event] += 1
        custom_rows.append({
            "event": event,
            "name": name,
            "note": note,
        })

    bools: dict[str, bool] = {}
    true_fields: list[str] = []
    for field_name in INTERACTIVE_AUDIO_BOOL_FIELDS:
        value, offset = read_memorypack_bool(data, offset)
        bools[field_name] = value
        if value:
            true_fields.append(field_name)

    return {
        "tag": f"0x{INTERACTIVE_AUDIO_COMPONENT_TAG:04x}",
        "type": BASE_COMPONENT_UNION_TAGS.get(INTERACTIVE_AUDIO_COMPONENT_TAG, ""),
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "audioComponentData",
        "schemaSource": (
            "field order recovered from full local IL2CPP metadata; audio dictionaries, "
            "custom audio rows, and boolean tail validated by component-list handoff"
        ),
        "prefixCount": prefix_count,
        "audioDataMemberCount": audio_data_member_count,
        "audioNameCount": audio_name_count,
        "customAudioCount": custom_audio_count,
        "stateCounts": {str(key): count for key, count in state_counts.most_common(24)},
        "stateNameCounts": dict(state_name_counts.most_common(24)),
        "audioEventCounts": dict(audio_event_counts.most_common(24)),
        "customNameCounts": dict(custom_name_counts.most_common(24)),
        "customEventCounts": dict(custom_event_counts.most_common(24)),
        "booleans": bools,
        "trueBooleanFields": true_fields,
        "audioRows": audio_rows,
        "customRows": custom_rows,
        "sampleAudioRows": audio_rows[:16],
        "sampleCustomRows": custom_rows[:16],
    }, offset


def read_memorypack_vector3_f32(data: bytes, offset: int, field_name: str) -> tuple[dict[str, float], int]:
    x, offset = read_memorypack_f32(data, offset)
    y, offset = read_memorypack_f32(data, offset)
    z, offset = read_memorypack_f32(data, offset)
    if not all(math.isfinite(value) for value in (x, y, z)):
        raise ValueError(f"{field_name}:non-finite")
    return {
        "x": round(x, 6),
        "y": round(y, 6),
        "z": round(z, 6),
    }, offset


def parse_interactive_show_guide_component(
    data: bytes,
    offset: int,
    tag: int,
    member_count: int,
) -> tuple[dict[str, Any], int]:
    if tag not in INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS:
        raise ValueError(f"showGuide.tag=0x{tag:04x}")
    if member_count != INTERACTIVE_SHOW_GUIDE_MEMBER_COUNT:
        raise ValueError(f"showGuide.memberCount={member_count}")
    start = offset
    type_name = BASE_COMPONENT_UNION_TAGS.get(tag, INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS[tag])
    property_map, offset = parse_interactive_component_property_map(
        data,
        offset,
        f"{type_name}.propertyMap",
    )
    previews = interactive_property_preview_by_key(property_map)
    center, offset = read_memorypack_vector3_f32(data, offset, f"{type_name}.center")
    radius, offset = read_memorypack_f32(data, offset)
    if not math.isfinite(radius):
        raise ValueError(f"{type_name}.radius:non-finite")
    if offset >= len(data):
        raise ValueError(f"{type_name}.shape:truncated")
    shape = data[offset]
    offset += 1
    if shape not in (0, 1, 2):
        raise ValueError(f"{type_name}.shape={shape}")
    size, offset = read_memorypack_vector3_f32(data, offset, f"{type_name}.size")
    return {
        "tag": f"0x{tag:04x}",
        "type": type_name,
        "memberCount": member_count,
        "byteLength": offset - start,
        "bodyShape": "propertyMapCenterRadiusShapeAndSize",
        "schemaSource": (
            "five-member ShowGuide body inferred from local IL2CPP generated formatter metadata "
            "and validated as property map, Vector3 center, float radius, byte shape, Vector3 size "
            "by exact component-count and next-union handoffs across export_full InteractiveData"
        ),
        "propertyMapCount": int(property_map.get("count") or 0),
        "propertyKeys": list((property_map.get("keyCounts") or {}).keys()),
        "valueTypeCounts": property_map.get("valueTypeCounts") or {},
        "valueCountCounts": property_map.get("valueCountCounts") or {},
        "tailCounts": property_map.get("tailCounts") or {},
        "stringTailCounts": property_map.get("stringTailCounts") or {},
        "previewByKey": previews,
        "center": center,
        "radius": round(radius, 6),
        "shape": shape,
        "size": size,
        "sampleProperties": (property_map.get("sampleRows") or [])[:16],
    }, offset


def scan_memorypack_utf8_strings(
    data: bytes,
    offset: int,
    *,
    max_scan_bytes: int = 2048,
    max_samples: int = 8,
    max_length: int = 96,
) -> list[str]:
    end = min(len(data), offset + max_scan_bytes)
    samples: list[str] = []
    for pos in range(max(offset, 0), max(offset, end - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        if length <= 0 or length > max_length or pos + 4 + length > end:
            continue
        raw = data[pos + 4:pos + 4 + length]
        if not raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text):
            continue
        if not any(ch.isalnum() for ch in text):
            continue
        if text not in samples:
            samples.append(text)
            if len(samples) >= max_samples:
                break
    return samples


def read_memorypack_tag_list_prefix(
    data: bytes,
    offset: int,
    *,
    max_items: int = 32,
    allow_hash_only: bool = False,
) -> tuple[list[dict[str, Any]], int | None, int, str | None]:
    if offset + 4 > len(data):
        return [], None, offset, "truncated-count"
    raw_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if raw_count == MEMORYPACK_NULL_COUNT:
        return [], None, offset, None
    if raw_count > max_items:
        return [], raw_count, offset, f"large-count={raw_count}"

    if allow_hash_only:
        hash_only_end = offset + raw_count * 4
        if hash_only_end + 4 <= len(data):
            following_count = struct.unpack_from("<I", data, hash_only_end)[0]
            if following_count == MEMORYPACK_NULL_COUNT or following_count <= 10_000:
                return [
                    {
                        "index": index,
                        "memberCount": None,
                        "hash": f"0x{struct.unpack_from('<I', data, offset + index * 4)[0]:08x}",
                        "tag": None,
                        "serialization": "hashOnly",
                    }
                    for index in range(raw_count)
                ], raw_count, hash_only_end, None

    tags: list[dict[str, Any]] = []
    for index in range(raw_count):
        if offset + 5 > len(data):
            return tags, raw_count, offset, "truncated-item"
        member_count = data[offset]
        offset += 1
        hash_value = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        tag, offset, err = read_memorypack_utf8_string(data, offset)
        tags.append({
            "index": index,
            "memberCount": member_count,
            "hash": f"0x{hash_value:08x}",
            "tag": tag,
        })
        if err:
            return tags, raw_count, offset, err
    return tags, raw_count, offset, None


def decode_interactive_template_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != INTERACTIVE_TEMPLATE_MEMBER_COUNT:
        return None

    offset = 1
    name, offset, name_error = read_memorypack_utf8_string(data, offset)
    if name_error or not name:
        return None
    if offset + 4 > len(data):
        return None
    faction_index = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    object_type, offset, object_type_error = read_memorypack_utf8_string(data, offset)
    if object_type_error:
        return None

    born_tags, born_tag_count, offset, tag_error = read_memorypack_tag_list_prefix(
        data,
        offset,
        allow_hash_only=True,
    )
    component_count: int | None = None
    component_offset = offset
    first_component_tag: int | None = None
    first_component_type = ""
    first_component_member_count: int | None = None
    first_component_tag_width = 0
    first_component_end_offset: int | None = None
    second_component_tag: int | None = None
    second_component_type = ""
    second_component_member_count: int | None = None
    second_component_tag_width = 0
    second_component_end_offset: int | None = None
    model_component: dict[str, Any] | None = None
    component_prefix_rows: list[dict[str, Any]] = []
    component_prefix_parsed_count = 0
    component_prefix_end_offset: int | None = None
    first_payload_component: dict[str, Any] | None = None
    first_payload_body_end_offset: int | None = None
    trigger_observer_component: dict[str, Any] | None = None
    property_map_component: dict[str, Any] | None = None
    component_payload_parsed_count = 0
    component_payload_parsed_rows: list[dict[str, Any]] = []
    trigger_observer_components: list[dict[str, Any]] = []
    property_map_components: list[dict[str, Any]] = []
    dynamic_ai_nav_components: list[dict[str, Any]] = []
    model_level_up_components: list[dict[str, Any]] = []
    narrative_components: list[dict[str, Any]] = []
    character_movement_components: list[dict[str, Any]] = []
    base_trigger_components: list[dict[str, Any]] = []
    common_perform_component: dict[str, Any] | None = None
    common_perform_components: list[dict[str, Any]] = []
    logic_controller_component: dict[str, Any] | None = None
    logic_controller_components: list[dict[str, Any]] = []
    hittable_component: dict[str, Any] | None = None
    hittable_components: list[dict[str, Any]] = []
    audio_component: dict[str, Any] | None = None
    audio_components: list[dict[str, Any]] = []
    show_guide_component: dict[str, Any] | None = None
    show_guide_components: list[dict[str, Any]] = []
    component_stop_component: dict[str, Any] | None = None
    component_scan_offset: int | None = None
    template_config_properties: dict[str, Any] | None = None
    template_empty_tail: dict[str, Any] | None = None
    template_action_map_audio: dict[str, Any] | None = None
    component_string_samples: list[str] = []
    component_error: str | None = None

    def component_type_name(tag: int) -> str:
        return BASE_COMPONENT_UNION_TAGS.get(tag, f"tag_0x{tag:04x}")

    def component_row(
        index: int,
        tag: int,
        tag_width: int,
        member_count: int,
        payload_offset: int,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "tag": f"0x{tag:04x}",
            "type": component_type_name(tag),
            "tagWidth": tag_width,
            "memberCount": member_count,
            "payloadOffset": format_offset(payload_offset),
        }

    if offset + 4 <= len(data):
        raw_component_count = struct.unpack_from("<I", data, offset)[0]
        if raw_component_count == MEMORYPACK_NULL_COUNT:
            component_count = None
            offset += 4
        elif raw_component_count <= 10_000:
            component_count = raw_component_count
            offset += 4
            component_cursor = offset
            if component_count:
                try:
                    first_component_tag, component_cursor, first_component_tag_width = read_memorypack_union_tag(
                        data,
                        component_cursor,
                    )
                    first_component_type = component_type_name(first_component_tag)
                    if component_cursor >= len(data):
                        raise ValueError("truncated-first-component-member-count")
                    first_component_member_count = data[component_cursor]
                    component_cursor += 1
                    first_component_end_offset = component_cursor
                    component_prefix_rows.append(
                        component_row(
                            0,
                            first_component_tag,
                            first_component_tag_width,
                            first_component_member_count,
                            component_cursor,
                        )
                    )
                    component_prefix_parsed_count = 1
                    component_prefix_end_offset = component_cursor
                    if component_count > 1:
                        second_component_tag, component_cursor, second_component_tag_width = read_memorypack_union_tag(
                            data,
                            component_cursor,
                        )
                        second_component_type = component_type_name(second_component_tag)
                        if component_cursor >= len(data):
                            raise ValueError("truncated-second-component-member-count")
                        second_component_member_count = data[component_cursor]
                        component_cursor += 1
                        if second_component_tag == 0x12C and second_component_member_count == 4:
                            born_fade_in_time, component_cursor = read_memorypack_f32(data, component_cursor)
                            if component_cursor >= len(data):
                                raise ValueError("truncated-model-component-enable-born-fade-in")
                            enable_born_fade_in_byte = data[component_cursor]
                            component_cursor += 1
                            if enable_born_fade_in_byte not in (0, 1):
                                raise ValueError(
                                    f"invalid-model-component-enable-born-fade-in={enable_born_fade_in_byte}"
                                )
                            model_id, component_cursor, model_error = read_memorypack_utf8_string(
                                data,
                                component_cursor,
                                max_length=512,
                            )
                            if model_error:
                                raise ValueError(f"invalid-model-component-id={model_error}")
                            model_scale, component_cursor = read_memorypack_f32(data, component_cursor)
                            if not math.isfinite(born_fade_in_time) or not math.isfinite(model_scale):
                                raise ValueError("model-component-float-non-finite")
                            model_component = {
                                "tag": f"0x{second_component_tag:04x}",
                                "type": second_component_type,
                                "memberCount": second_component_member_count,
                                "bornFadeInTime": round(born_fade_in_time, 6),
                                "enableBornFadeIn": bool(enable_born_fade_in_byte),
                                "modelId": model_id,
                                "modelScale": round(model_scale, 6),
                            }
                            second_component_end_offset = component_cursor
                            component_prefix_rows.append({
                                **component_row(
                                    1,
                                    second_component_tag,
                                    second_component_tag_width,
                                    second_component_member_count,
                                    second_component_end_offset,
                                ),
                                "modelId": model_id,
                            })
                            component_prefix_parsed_count = 2
                            component_prefix_end_offset = component_cursor
                    if second_component_end_offset is not None:
                        component_cursor = second_component_end_offset
                        component_scan_offset = component_cursor
                        for component_index in range(2, component_count or 0):
                            tag, component_cursor, tag_width = read_memorypack_union_tag(data, component_cursor)
                            if component_cursor >= len(data):
                                raise ValueError(f"truncated-component-{component_index}-member-count")
                            member_count = data[component_cursor]
                            component_cursor += 1
                            row = component_row(component_index, tag, tag_width, member_count, component_cursor)
                            if member_count == 0:
                                row["parsedBody"] = "zero"
                                if first_payload_component is None:
                                    component_prefix_rows.append(row)
                                    component_prefix_parsed_count = component_index + 1
                                    component_prefix_end_offset = component_cursor
                                else:
                                    component_payload_parsed_count += 1
                                    component_payload_parsed_rows.append(row)
                                component_scan_offset = component_cursor
                                continue
                            if first_payload_component is None:
                                first_payload_component = row

                            parsed_body_end_offset: int | None = None
                            if (
                                tag == INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG
                                and member_count == INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT
                            ):
                                parsed_trigger_observer, parsed_body_end_offset = (
                                    parse_interactive_trigger_observer_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_trigger_observer["byteLength"]
                                row["parsedBody"] = "propertyMaps"
                                if trigger_observer_component is None:
                                    trigger_observer_component = parsed_trigger_observer
                                trigger_observer_components.append({
                                    "index": component_index,
                                    **parsed_trigger_observer,
                                })
                            elif tag in INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS and member_count == 1:
                                parsed_property_map, parsed_body_end_offset = (
                                    parse_interactive_single_property_map_component(
                                        data,
                                        component_cursor,
                                        tag,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_property_map["byteLength"]
                                row["parsedBody"] = "propertyMap"
                                if property_map_component is None:
                                    property_map_component = parsed_property_map
                                property_map_components.append({
                                    "index": component_index,
                                    **parsed_property_map,
                                })
                            elif (
                                tag == INTERACTIVE_DYNAMIC_AI_NAV_COMPONENT_TAG
                                and member_count == INTERACTIVE_DYNAMIC_AI_NAV_MEMBER_COUNT
                            ):
                                parsed_dynamic_ai_nav, parsed_body_end_offset = (
                                    parse_interactive_dynamic_ai_nav_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_dynamic_ai_nav["byteLength"]
                                row["parsedBody"] = "propertyMapAndObstacleType"
                                row["obstacleType"] = parsed_dynamic_ai_nav["obstacleType"]
                                dynamic_ai_nav_components.append({
                                    "index": component_index,
                                    **parsed_dynamic_ai_nav,
                                })
                            elif (
                                tag == INTERACTIVE_MODEL_LEVEL_UP_COMPONENT_TAG
                                and member_count == INTERACTIVE_MODEL_LEVEL_UP_MEMBER_COUNT
                            ):
                                parsed_model_level_up, parsed_body_end_offset = (
                                    parse_interactive_model_level_up_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_model_level_up["byteLength"]
                                row["parsedBody"] = "propertyMapAndModelLevelList"
                                row["modelLevelCount"] = parsed_model_level_up["modelLevelCount"]
                                model_level_up_components.append({
                                    "index": component_index,
                                    **parsed_model_level_up,
                                })
                            elif (
                                tag == INTERACTIVE_NARRATIVE_COMPONENT_TAG
                                and member_count == INTERACTIVE_NARRATIVE_MEMBER_COUNT
                            ):
                                parsed_narrative, parsed_body_end_offset = (
                                    parse_interactive_narrative_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_narrative["byteLength"]
                                row["parsedBody"] = "propertyMapAndNarrativeType"
                                row["narrativeType"] = parsed_narrative["narrativeType"]
                                narrative_components.append({
                                    "index": component_index,
                                    **parsed_narrative,
                                })
                            elif (
                                tag == INTERACTIVE_CHARACTER_MOVEMENT_COMPONENT_TAG
                                and member_count == INTERACTIVE_CHARACTER_MOVEMENT_MEMBER_COUNT
                            ):
                                parsed_character_movement, parsed_body_end_offset = (
                                    parse_interactive_character_movement_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_character_movement["byteLength"]
                                row["parsedBody"] = (
                                    "propertyMapAbilityMovementsMovementDataMoveModeAndShape"
                                )
                                row["overrideMoveMode"] = parsed_character_movement[
                                    "overrideMoveMode"
                                ]
                                character_movement_components.append({
                                    "index": component_index,
                                    **parsed_character_movement,
                                })
                            elif (
                                tag in INTERACTIVE_BASE_TRIGGER_COMPONENT_TAGS
                                and member_count == INTERACTIVE_BASE_TRIGGER_MEMBER_COUNT
                            ):
                                parsed_base_trigger, parsed_body_end_offset = (
                                    parse_interactive_base_trigger_component(
                                        data,
                                        component_cursor,
                                        tag,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_base_trigger["byteLength"]
                                row["parsedBody"] = "propertyStatesAndNullTriggerBehaviour"
                                row["propertyStateCount"] = parsed_base_trigger["propertyStateCount"]
                                row["conditionCount"] = parsed_base_trigger["conditionCount"]
                                base_trigger_components.append({
                                    "index": component_index,
                                    **parsed_base_trigger,
                                })
                            elif (
                                tag == INTERACTIVE_ABILITY_SYSTEM_COMPONENT_TAG
                                and member_count == INTERACTIVE_ABILITY_SYSTEM_MEMBER_COUNT
                            ):
                                parsed_ability_system, parsed_body_end_offset = (
                                    parse_interactive_ability_system_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_ability_system["byteLength"]
                                row["parsedBody"] = "abilitySystemDataThenAbilitySystemForIntData"
                                row["skillIds"] = sorted({
                                    value
                                    for values in (
                                        (parsed_ability_system.get("skillDataBundle") or {}).get("allActiveSkillId") or [],
                                        (parsed_ability_system.get("skillDataBundle") or {}).get("allPassiveSkillId") or [],
                                        (parsed_ability_system.get("skillDataBundle") or {}).get("normalAttackList") or [],
                                    )
                                    for value in values
                                })
                            elif (
                                tag == INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG
                                and member_count == INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT
                            ):
                                parsed_common_perform, parsed_body_end_offset = (
                                    parse_interactive_common_perform_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_common_perform["byteLength"]
                                row["parsedBody"] = "commonPerformData"
                                row["performPropertyCount"] = parsed_common_perform["performPropertyCount"]
                                row["syncGameplayLock"] = parsed_common_perform["syncGameplayLock"]
                                if common_perform_component is None:
                                    common_perform_component = parsed_common_perform
                                common_perform_components.append({
                                    "index": component_index,
                                    **parsed_common_perform,
                                })
                            elif (
                                tag == INTERACTIVE_HITTABLE_COMPONENT_TAG
                                and member_count == INTERACTIVE_HITTABLE_MEMBER_COUNT
                            ):
                                parsed_hittable, parsed_body_end_offset = parse_interactive_hittable_component(
                                    data,
                                    component_cursor,
                                    member_count,
                                )
                                row["byteLength"] = parsed_hittable["byteLength"]
                                row["parsedBody"] = "propertyMapColliderShapeAndFlag"
                                row["propertyMapCount"] = parsed_hittable["propertyMapCount"]
                                row["enableExtraCheck"] = parsed_hittable["enableExtraCheck"]
                                if hittable_component is None:
                                    hittable_component = parsed_hittable
                                hittable_components.append({
                                    "index": component_index,
                                    **parsed_hittable,
                                })
                            elif (
                                tag == INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG
                                and member_count == INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT
                            ):
                                parsed_logic_controller, parsed_body_end_offset = (
                                    parse_interactive_logic_controller_component(
                                        data,
                                        component_cursor,
                                        member_count,
                                    )
                                )
                                row["byteLength"] = parsed_logic_controller["byteLength"]
                                row["parsedBody"] = "logicTypeAndPropertyMap"
                                row["logicType"] = parsed_logic_controller["logicType"]
                                if logic_controller_component is None:
                                    logic_controller_component = parsed_logic_controller
                                logic_controller_components.append({
                                    "index": component_index,
                                    **parsed_logic_controller,
                                })
                            elif tag == INTERACTIVE_AUDIO_COMPONENT_TAG and member_count == INTERACTIVE_AUDIO_MEMBER_COUNT:
                                parsed_audio, parsed_body_end_offset = parse_interactive_audio_component(
                                    data,
                                    component_cursor,
                                    member_count,
                                )
                                row["byteLength"] = parsed_audio["byteLength"]
                                row["parsedBody"] = "audioComponentData"
                                row["audioNameCount"] = parsed_audio["audioNameCount"]
                                row["customAudioCount"] = parsed_audio["customAudioCount"]
                                if audio_component is None:
                                    audio_component = parsed_audio
                                audio_components.append({
                                    "index": component_index,
                                    **parsed_audio,
                                })
                            elif tag in INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS and member_count == INTERACTIVE_SHOW_GUIDE_MEMBER_COUNT:
                                parsed_show_guide, parsed_body_end_offset = parse_interactive_show_guide_component(
                                    data,
                                    component_cursor,
                                    tag,
                                    member_count,
                                )
                                row["byteLength"] = parsed_show_guide["byteLength"]
                                row["parsedBody"] = "showGuideBoundsData"
                                row["shape"] = parsed_show_guide["shape"]
                                if show_guide_component is None:
                                    show_guide_component = parsed_show_guide
                                show_guide_components.append({
                                    "index": component_index,
                                    **parsed_show_guide,
                                })
                            else:
                                component_stop_component = row
                                component_scan_offset = component_cursor
                                break

                            if parsed_body_end_offset is None:
                                raise ValueError(f"component-{component_index}-body-not-consumed")
                            if first_payload_component is row:
                                first_payload_body_end_offset = parsed_body_end_offset
                            component_payload_parsed_count += 1
                            component_payload_parsed_rows.append(row)
                            component_cursor = parsed_body_end_offset
                            component_scan_offset = component_cursor
                    if (
                        component_count is not None
                        and component_stop_component is None
                        and component_scan_offset is not None
                        and component_prefix_parsed_count + component_payload_parsed_count
                        == component_count
                    ):
                        template_config_properties, _template_config_end = (
                            parse_interactive_template_config_properties(
                                data,
                                component_scan_offset,
                            )
                        )
                        try:
                            from story_builder.levelscript_binary import (
                                decode_embedded_action_serialized_map_audio,
                            )
                        except ImportError:
                            from scripts.game_data.levelscript_binary import (
                                decode_embedded_action_serialized_map_audio,
                            )
                        template_action_map_audio = (
                            decode_embedded_action_serialized_map_audio(
                                data,
                                _template_config_end,
                            )
                            or None
                        )
                        try:
                            template_empty_tail, _template_tail_end = (
                                parse_interactive_template_empty_tail(
                                    data,
                                    _template_config_end,
                                )
                            )
                        except (struct.error, ValueError):
                            template_empty_tail = None
                    scan_offset = (
                        component_scan_offset
                        or first_payload_body_end_offset
                        or (
                            int(first_payload_component.get("payloadOffset", "0x0"), 16)
                            if first_payload_component
                            else component_prefix_end_offset or second_component_end_offset or first_component_end_offset or offset
                        )
                    )
                    component_string_samples = scan_memorypack_utf8_strings(data, scan_offset)
                except (UnicodeDecodeError, struct.error, ValueError) as exc:
                    component_error = str(exc)
                    component_string_samples = scan_memorypack_utf8_strings(data, offset)
        else:
            component_error = f"invalid-component-count={raw_component_count}"
    else:
        component_error = "truncated-component-count"

    category_tags = [
        str(row.get("tag") or "")
        for row in born_tags
        if str(row.get("tag") or "").startswith("Category/")
    ]
    tag_sample = [str(row.get("tag") or "") for row in born_tags[:4] if row.get("tag")]
    details = [
        f"name={name}",
        f"factionIndex={faction_index}",
        f"objectType={object_type}" if object_type else "objectType=null",
        f"bornTags={born_tag_count if born_tag_count is not None else 'null'}",
    ]
    if component_count is not None:
        details.append(f"components={component_count}")
    if first_component_type:
        details.append(f"firstComponent={first_component_type}")
    if model_component and model_component.get("modelId"):
        details.append(f"modelComponent={model_component['modelId']}")
    if component_prefix_parsed_count:
        details.append(f"componentPrefix={component_prefix_parsed_count}")
    if first_payload_component:
        details.append(
            f"nextComponent={first_payload_component['type']}:{first_payload_component['memberCount']}"
        )
    if trigger_observer_component:
        details.append(
            "triggerMaps=" + ",".join(str(value) for value in trigger_observer_component["propertyMapCounts"])
        )
        trigger_preview = trigger_observer_component.get("primaryPreviewByKey") or {}
        if "shape" in trigger_preview:
            details.append(f"triggerShape={trigger_preview['shape']}")
        if "radius" in trigger_preview:
            details.append(f"triggerRadius={trigger_preview['radius']}")
    if property_map_component:
        details.append(f"propertyMap={property_map_component['propertyMapCount']}")
        property_keys = property_map_component.get("propertyKeys") or []
        if property_keys:
            details.append("propertyKeys=" + ",".join(str(key) for key in property_keys[:3]))
    if common_perform_component:
        details.append(f"commonPerform={common_perform_component['performPropertyCount']}")
        perform_names = list((common_perform_component.get("performPropertyNameCounts") or {}).keys())
        if perform_names:
            details.append("performKeys=" + ",".join(str(key) for key in perform_names[:3]))
        if common_perform_component.get("syncGameplayLock"):
            details.append("syncGameplayLock=true")
    if logic_controller_component:
        details.append(f"logicType={logic_controller_component['logicType']}")
        logic_keys = logic_controller_component.get("propertyKeys") or []
        if logic_keys:
            details.append("logicKeys=" + ",".join(str(key) for key in logic_keys[:3]))
    if hittable_component:
        details.append(f"hittableMap={hittable_component['propertyMapCount']}")
        hittable_keys = hittable_component.get("propertyKeys") or []
        if hittable_keys:
            details.append("hittableKeys=" + ",".join(str(key) for key in hittable_keys[:3]))
        if hittable_component.get("enableExtraCheck"):
            details.append("hittableExtraCheck=true")
    if audio_component:
        details.append(f"audioStates={audio_component['audioNameCount']}")
        if audio_component.get("customAudioCount"):
            details.append(f"customAudio={audio_component['customAudioCount']}")
        audio_rows = audio_component.get("sampleAudioRows") or []
        first_events = [
            str(event)
            for row in audio_rows[:2]
            for event in (row.get("events") or [])[:1]
            if event
        ]
        if first_events:
            details.append("audio=" + ",".join(first_events[:2]))
    if show_guide_component:
        details.append(f"showGuideMap={show_guide_component['propertyMapCount']}")
        details.append(f"guideShape={show_guide_component['shape']}")
    if component_payload_parsed_count:
        details.append(f"parsedPayloads={component_payload_parsed_count}")
    if template_config_properties:
        details.append(
            f"templateConfig={template_config_properties['configPropertyCount']}"
        )
        template_audio_rows = template_config_properties.get("audioPropertyRows") or []
        if template_audio_rows:
            details.append(
                "templateAudio="
                + ",".join(
                    str(event)
                    for row in template_audio_rows[:2]
                    for event in (row.get("events") or [])[:1]
                )
            )
    if template_action_map_audio and template_action_map_audio.get("audioActions"):
        details.append(
            f"templateAudioActions={len(template_action_map_audio['audioActions'])}"
        )
    if component_stop_component and component_stop_component is not first_payload_component:
        details.append(
            f"stopComponent={component_stop_component['type']}:{component_stop_component['memberCount']}"
        )
    if category_tags:
        details.append(f"category={category_tags[0]}")
    if component_string_samples:
        details.append("componentStrings=" + ",".join(component_string_samples[:3]))
    if tag_error:
        details.append(f"tagParse={tag_error}")
    if component_error:
        details.append(f"componentParse={component_error}")

    return {
        "kind": "memorypack-json",
        "subtype": "InteractiveTemplateData",
        "summary": (
            "MemoryPack InteractiveTemplateData; 26-member current root; "
            "component prefix, next payload tag, and selected component bodies decoded from bytes"
        ),
        "rows": component_count,
        "keys": MEMORYPACK_FIELD_SCHEMAS["InteractiveTemplateData"],
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": INTERACTIVE_TEMPLATE_MEMBER_COUNT,
            "knownOrderedMemberCount": len(
                MEMORYPACK_FIELD_SCHEMAS["InteractiveTemplateData"]
            ),
            "unpositionedDeclaredMembers": [],
            "format": "memorypack",
            "schemaSource": INTERACTIVE_TEMPLATE_SCHEMA_SOURCE_NOTE,
            "decodedPrefixFields": [
                "name",
                "factionIndex",
                "objectType",
                "bornTag",
                "componentList",
                "componentListFirst",
                "componentListSecondModel",
                "componentListZeroMemberPrefix",
                "componentListFirstPayloadTag",
                "componentListTriggerObserverBody",
                "componentListFirstPayloadPropertyMap",
                "componentListCommonPerformBody",
                "componentListLogicControllerBody",
                "componentListHittableBody",
                "componentListAudioBody",
                "componentListShowGuideBody",
                "componentListParsedPayloads",
                "templateConfigProperties",
                "templateEmptyTail",
                "templateActionMapAudio",
            ],
            "name": name,
            "factionIndex": faction_index,
            "objectType": object_type,
            "bornTagCount": born_tag_count,
            "bornTags": born_tags,
            "componentListCount": component_count,
            "componentListOffset": format_offset(component_offset),
            "componentListFirstTag": f"0x{first_component_tag:04x}" if first_component_tag is not None else "",
            "componentListFirstType": first_component_type,
            "componentListFirstTagWidth": first_component_tag_width,
            "componentListFirstMemberCount": first_component_member_count,
            "componentListFirstEndOffset": format_offset(first_component_end_offset),
            "componentListSecondTag": f"0x{second_component_tag:04x}" if second_component_tag is not None else "",
            "componentListSecondType": second_component_type,
            "componentListSecondTagWidth": second_component_tag_width,
            "componentListSecondMemberCount": second_component_member_count,
            "componentListSecondEndOffset": format_offset(second_component_end_offset),
            "componentModelData": model_component,
            "componentListPrefixParsedCount": component_prefix_parsed_count,
            "componentListPrefixEndOffset": format_offset(component_prefix_end_offset),
            "componentListPrefixRows": component_prefix_rows,
            "componentListFirstPayload": first_payload_component,
            "componentListFirstPayloadBodyEndOffset": format_offset(first_payload_body_end_offset),
            "componentListParsedPayloadCount": component_payload_parsed_count,
            "componentListParsedPayloadRows": component_payload_parsed_rows,
            "componentListStopPayload": component_stop_component,
            "componentListScanOffset": format_offset(component_scan_offset),
            "componentTriggerObserverData": trigger_observer_component,
            "componentTriggerObserverComponents": trigger_observer_components,
            "componentPropertyMapData": property_map_component,
            "componentPropertyMapComponents": property_map_components,
            "componentDynamicAINavComponents": dynamic_ai_nav_components,
            "componentModelLevelUpComponents": model_level_up_components,
            "componentNarrativeComponents": narrative_components,
            "componentCharacterMovementComponents": character_movement_components,
            "componentBaseTriggerComponents": base_trigger_components,
            "componentCommonPerformData": common_perform_component,
            "componentCommonPerformComponents": common_perform_components,
            "componentAudioPropertyComponents": [],
            "componentLogicControllerData": logic_controller_component,
            "componentLogicControllerComponents": logic_controller_components,
            "componentHittableData": hittable_component,
            "componentHittableComponents": hittable_components,
            "componentAudioData": audio_component,
            "componentAudioComponents": audio_components,
            "componentShowGuideData": show_guide_component,
            "componentShowGuideComponents": show_guide_components,
            "templateConfigProperties": template_config_properties,
            "templateEmptyTail": template_empty_tail,
            "templateActionMapAudio": template_action_map_audio,
            "componentStringSamples": component_string_samples,
            "componentUnionSource": BASE_COMPONENT_UNION_SOURCE_NOTE if first_component_type else "",
            "componentParseError": component_error or "",
            "exactLength": template_empty_tail is not None,
            "schemaStatus": (
                "named_exact" if template_empty_tail is not None else "bounded_partial"
            ),
        },
    }
