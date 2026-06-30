#!/usr/bin/env python3
"""Build the WebUI game-data browser index.

The input is an installed/exported StreamingAssets/Data tree. The browser loads
the generated index lazily by logical group, with Json split by category and
folded by directory structure before filename prefix, while raw file previews
are served from the local export by serve.py.
"""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict
import math
import json
import re
import struct
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import OUT_DIR, ROOT, normalize_posix, write_json
from story_builder.levelscript_binary import (
    decode_levelscript_action_map_details,
    decode_levelscript_action_map_header,
    decode_levelscript_binary_summary,
)

DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_DATA_REL = Path("structured") / "StreamingAssets" / "Data"
GAME_DATA_DIR = OUT_DIR / "game_data"
HEADER_BYTES = 1024
STRING_SAMPLE_LIMIT = 8
STRING_SAMPLE_MAX_CHARS = 360
EXCLUDED_EXTENSIONS: set[str] = set()
EXCLUDED_GROUPS: set[str] = set()
VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "usm"}
PREFIX_GROUP_ROOTS = {"Json"}
AUTO_LOAD_ALL_FILE_LIMIT = 120_000
BUNDLE_MAIN_SHARD_CHARS = 1
HEX_STEM_RE = re.compile(r"^[0-9a-fA-F]{8,}$")
UNITY_VERSION_RE = re.compile(rb"20\d{2}\.\d+\.\d+[A-Za-z0-9_.-]*")
INTERESTING_STRING_KEYS = {
    "id",
    "key",
    "name",
    "title",
    "path",
    "missionId",
    "missionName",
    "levelId",
    "levelName",
    "mapId",
    "mapIdStr",
    "charId",
    "avatarTempletName",
    "avatarMeshName",
}
PRINTABLE_ASCII_RE = re.compile(rb"[\x20-\x7e]{5,}")
MEMORYPACK_NULL_COUNT = 0xFFFFFFFF
MEMORYPACK_EXTENDED_OBJECT_HEADER = 250
MEMORYPACK_UNION_WIDE_TAG = 0xFA
MEMORYPACK_MAX_MEMBER_COUNT = 128
LIPSYNC_MEMBER_COUNT = 15
BUFF_MEMBER_COUNT = 29
CHAR_INTERACT_PERFORM_MEMBER_COUNT = 26
SKILL_MEMBER_COUNT = 45
LEVELDATA_MEMBER_COUNT = 42
LEVELSCRIPT_TEMPLATE_MEMBER_COUNT = 6
INTERACTIVE_TABLE_MEMBER_COUNT = 2
MODEL_RADIUS_VALUE_MEMBER_COUNT = 4
TELEPORT_VALIDATION_VALUE_MEMBER_COUNT = 10
LUNA_AREA_ROW_MEMBER_COUNT = 6
MATRIX_SHOCK_WAVE_BEAT_REL = "Json/NonGeneratedConfigs/MatrixShockWaveBeatConfigTable.json"
MATRIX_SHOCK_WAVE_ROOT_MEMBER_COUNT = 2
MATRIX_SHOCK_WAVE_ROW_MEMBER_COUNT = 2
MATRIX_SHOCK_WAVE_POINT_MEMBER_COUNT = 3
BAMBOO_RAFT_TASK_TABLE_REL = "Json/NonGeneratedConfigs/BambooRaftTaskTable.json"
BAMBOO_RAFT_TASK_ROOT_MEMBER_COUNT = 1
BAMBOO_RAFT_TASK_VALUE_MEMBER_COUNT = 2
BAMBOO_RAFT_TASK_REF_MEMBER_COUNT = 2
SUBGAME_INSTANCE_DATA_TABLE_REL = "Json/GameplayConfigSubGameInstanceDataTable.json"
SUBGAME_INSTANCE_ROOT_MEMBER_COUNT = 1
SUBGAME_INSTANCE_VALUE_MEMBER_COUNT = 6
MISSION_AREA_TABLE_REL = "Json/GameplayConfigMissionAreaTable.json"
MISSION_AREA_VALUE_MEMBER_COUNT = 8
DAMAGE_TEXT_REL = "Json/GPUISystemConfig/damage_text.json"
DAMAGE_TEXT_ROOT_MEMBER_COUNT = 5
DAMAGE_TEXT_ROW_MEMBER_COUNT = 6
DAMAGE_TEXT_ANIMATION_MEMBER_COUNT = 5
DAMAGE_TEXT_NODE_MEMBER_COUNT = 6
DIALOG_ID_TABLE_REL = "Json/GameplayConfig/DialogIdTable.json"
DIALOG_ID_TABLE_ROOT_MEMBER_COUNT = 5
DIALOG_ID_TABLE_BRIEF_MEMBER_COUNT = 7
DIALOG_ID_TABLE_KEY_RE = re.compile(r"^(?:dlg|radio)_[A-Za-z0-9_]{2,140}$")
DIALOG_ID_TABLE_RAW_ID_RE = re.compile(rb"(dlg_[A-Za-z0-9_]{2,80}|radio_[A-Za-z0-9_]{2,80})")
DIALOG_ID_TABLE_LINE_RE = re.compile(r"^(?P<scene>dlg_[A-Za-z0-9_]+?)_(?P<trunk>[1-9]\d*)_(?P<line>\d{3,5})$")
DIALOG_ID_TABLE_OPTION_RAW_RE = re.compile(rb"(option_dlg_[A-Za-z0-9_]+?_[1-9]\d*_\d{3})")
DIALOG_ID_TABLE_OPTION_RE = re.compile(r"^option_(?P<scene>dlg_[A-Za-z0-9_]+?)_(?P<group>[1-9]\d*)_(?P<option>\d{3})$")
MODEL_TABLE_RELS = {
    "Json/GameplayConfig/ModelTable.json",
    "Json/NonGeneratedConfigs/ModelTable.json",
}
MODEL_TABLE_ROOT_MEMBER_COUNT = 2
MODEL_TABLE_MODEL_ROW_MEMBER_COUNT = 6
MODEL_TABLE_LAYOUT_ROW_MEMBER_COUNT = 12
MODEL_TABLE_LOCK_VIEW_CONFIG_MEMBER_COUNT = 3
MODEL_TABLE_LAYOUT_KEY_RE = re.compile(r"^[A-Za-z0-9_+ .-]{1,220}$")
WORLD_ENTITY_REGISTRY_REL = "Json/GameplayConfigWorldEntityRegistry.json"
WORLD_ENTITY_REGISTRY_ROOT_MEMBER_COUNT = 4
WORLD_ENTITY_BRIEF_ROW_MEMBER_COUNT = 4
WORLD_ENTITY_CONFIG_ROW_MEMBER_COUNT = 1
WORLD_ENTITY_PROPERTY_MEMBER_COUNT = 2
WORLD_ENTITY_PROPERTY_VALUE_MEMBER_COUNT = 2
WORLD_ENTITY_PROPERTY_VALUE_ITEM_MEMBER_COUNT = 2
NAVMESH_STATE_CONTAINER_MEMBER_COUNT = 6
LEVEL_CONFIG_MEMBER_COUNT = 15
SPAWNER_CONFIG_MEMBER_COUNT = 5
ATMOSPHERIC_NPC_TABLE_MEMBER_COUNT = 1
ATMOSPHERIC_NPC_ROW_MEMBER_COUNT = 109
ATMOSPHERIC_NPC_KEY_MAX_LENGTH = 120
NPC_MONTAGE_ROOT_MEMBER_COUNT = 3
NPC_MONTAGE_DATA_MEMBER_COUNT = 22
LIPSYNC_RECORD_DIMENSION_LIMIT = 64
INTERACTIVE_TEMPLATE_MEMBER_COUNT = 25
INTERACTIVE_TRIGGER_OBSERVER_COMPONENT_TAG = 0x00D9
INTERACTIVE_TRIGGER_OBSERVER_MEMBER_COUNT = 3
INTERACTIVE_COMMON_PERFORM_COMPONENT_TAG = 0x005A
INTERACTIVE_COMMON_PERFORM_MEMBER_COUNT = 3
INTERACTIVE_PERFORM_PROPERTY_ROW_MEMBER_COUNT = 3
INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG = 0x0069
INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT = 2
INTERACTIVE_HITTABLE_COMPONENT_TAG = 0x004A
INTERACTIVE_HITTABLE_MEMBER_COUNT = 3
INTERACTIVE_HITTABLE_COLLIDER_SHAPE_BLOB_LENGTH = 80
INTERACTIVE_AUDIO_COMPONENT_TAG = 0x0051
INTERACTIVE_AUDIO_MEMBER_COUNT = 2
INTERACTIVE_AUDIO_DATA_MEMBER_COUNT = 13
INTERACTIVE_SHOW_GUIDE_COMPONENT_TAGS = {
    0x00BA: "Core_ShowGuideComponentData",
    0x00BB: "Core_ShowGuideWithConditionComponentData",
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
INTERACTIVE_PROPERTY_VALUE_STRING_TAIL_TYPES = {7, 8}
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
    0x0006,
    0x0019,
    0x001B,
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
    0x00F5,
    0x00F6,
    0x00F8,
    0x00F9,
    0x00FC,
}
MODEL_VIEW_STATE_CONTROLLER_MEMBER_COUNT = 7
FLATBUFFER_PREVIEW_MAX_BYTES = 1_048_576
FLATBUFFER_MAX_FIELDS = 256
FLATBUFFER_MAX_VECTOR_LENGTH = 1_000_000
FLATBUFFER_MAX_STRING_LENGTH = 1024
FLATBUFFER_SCHEMALESS_SOURCE_NOTE = "schema-less FlatBuffers table/vtable traversal; field names require .fbs schema"
MEMORYPACK_SCHEMA_SOURCE_NOTE = "field order recovered from installed IL2CPP ForMemoryPack setter metadata"
INTERACTIVE_TEMPLATE_SCHEMA_SOURCE_NOTE = (
    "inherited field order recovered from IL2CPP template wrappers and byte-prefix validation"
)
BASE_COMPONENT_UNION_SOURCE_NOTE = (
    "BaseComponentData union formatter tags extracted from installed GameAssembly.dll"
)
BASE_COMPONENT_UNION_TAGS = {
    0x000C: "Core_AbilitySystemForIntData",
    0x0013: "Core_AttackTriggerComponentForIntData",
    0x0016: "Core_BaseControllerData",
    0x001B: "Core_CanSetVisibleComponentData",
    0x001F: "Core_CharacterMovementComponentData",
    0x0023: "Core_ClickTriggerComponentForIntData",
    0x002C: "Core_CustomCurveMoveComponentData",
    0x0034: "Core_ElectricNodeComponentData",
    0x003D: "Core_ErosionSludgeCoreComponentData",
    0x0042: "Core_FactoryBuildingWrapperComponentData",
    0x0045: "Core_GameplayElectricityNodeComponentData",
    0x0049: "Core_HeightZeroMarkerComponentData",
    0x004A: "Core_HittableComponentForIntData",
    0x004F: "Core_InteractCommonTwoStateComponentData",
    0x0051: "Core_InteractiveAudioData",
    0x0059: "Core_InteractiveCommonMultiStateComponentData",
    0x005A: "Core_InteractiveCommonPerformComponentData",
    0x005B: "Core_InteractiveCoolerUnitComponentData",
    0x0061: "Core_InteractiveDoorCommonComponentData",
    0x0062: "Core_InteractiveDynamicAINavComponentData",
    0x0069: "Core_InteractiveLogicControllerComponentData",
    0x006B: "Core_InteractiveManualMovePlatformComponentData",
    0x006C: "Core_InteractiveModelLevelUpComponentData",
    0x006F: "Core_InteractiveOutFallComponentData",
    0x0073: "Core_InteractiveRootComponentData",
    0x0075: "Core_InteractiveRunePointComponentData",
    0x0077: "Core_InteractiveSteamBlockerComponentData",
    0x0086: "Core_InteractiveWaterPipeComponentData",
    0x0087: "Core_InteractiveWaterSwitchComponentData",
    0x0092: "Core_KeepRelativeOffsetComponentData",
    0x009F: "Core_NavmeshDynamicBakeAreaComponentData",
    0x00AA: "Core_PlayerInteractPerformComponentData",
    0x00BA: "Core_ShowGuideComponentData",
    0x00BB: "Core_ShowGuideWithConditionComponentData",
    0x00BD: "Core_SimpleAnimatorComponentData",
    0x00CE: "Core_StepOnTriggerComponentForIntData",
    0x00D9: "Core_TriggerObserverComponentData",
    0x00DB: "Core_TriggerZoneComponentForIntData",
    0x00DF: "Core_WaterProgressDriveCurveMovementComponentData",
    0x00E0: "Core_WaterVolHeightMarkerComponentData",
    0x00E6: "CraneContainerComponentData",
    0x00E7: "CraneTowerComponentData",
    0x00E9: "DungeonExitComponentData",
    0x00ED: "HiddenMarkComponentComponentData",
    0x00EE: "InfraredGroupComponentData",
    0x00F5: "InteractiveMovingPlatClientOnlyComponentData",
    0x00F8: "InteractiveStainComponentData",
    0x00FC: "ScannableTraceComponentData",
    0x0108: "View_InteractiveModelComponentData",
    0x010A: "View_ModelComponentData",
}
MEMORYPACK_FIELD_SCHEMAS = {
    "BuffData": [
        "abilityEventAction",
        "addingCooldown",
        "applyTags",
        "attributeModifier",
        "blackboard",
        "buffEventAction",
        "damageModifier",
        "dispelConfig",
        "duration",
        "finishOnRepatriate",
        "globalModifier",
        "hasAddingCooldown",
        "hasIcon",
        "healModifier",
        "iconConfig",
        "id",
        "igniteEventAction",
        "ignoreCooldownWhenAdding",
        "ignoreTagImmune",
        "lifeType",
        "maxTriggerCnt",
        "poiseModifier",
        "shieldConfigs",
        "stackingSettings",
        "tagsAfterTriggerExtendBuffAction",
        "timelineActions",
        "triggerInterval",
        "useTimeDilationDt",
        "waitFirstTriggerInterval",
    ],
    "AnimationConfig": [
        "fallbackMontages",
        "bakedBindingPath",
        "controllerPath",
        "extraData",
        "montages",
        "npcMontages",
        "optControllerPath",
        "syncGroupAnimationCurves",
        "syncGroupCurves",
        "timeRefCurves",
        "useRotateDirection",
        "useStateVariables",
    ],
    "CharInteractPerformCfgs": [
        "activeTags",
        "allowInheritPerform",
        "bodyTypeActDataDict",
        "charPerformType",
        "chars",
        "decos",
        "defaultSubPerformEntry",
        "disableIKAndFollow",
        "effects",
        "endActions",
        "fixedTime",
        "forceExitCommandsContinuous",
        "guardActiveTags",
        "guardInterruptReasons",
        "hideWeapon",
        "inheritPerformIds",
        "interactives",
        "interruptReasons",
        "loopActions",
        "npcs",
        "performType",
        "preStartActions",
        "startActions",
        "subPerformEntries",
        "tmpObjects",
        "usePreStartActions",
    ],
    "LevelData": [
        "airWalls",
        "aiTransData",
        "autoSpawnedInteractives",
        "blackbox",
        "buildableCondition",
        "cameraPoses",
        "charPatrol",
        "doodadGroup",
        "dynamicOccludeAreas",
        "enemies",
        "enemyGroup",
        "enemyPatrol",
        "environmentVolumes",
        "factoryMines",
        "factoryPredefineData",
        "factoryRegions",
        "functionArea",
        "guideHints",
        "interactiveLockData",
        "interactives",
        "levelIdNum",
        "levelScriptBriefDataDict",
        "levelScriptDataPathDict",
        "levelUIs",
        "levelWideConfigs",
        "mapVolumeDatas",
        "missionAreas",
        "npcAttractPointData",
        "npcClusters",
        "npcGroup",
        "npcPatrol",
        "npcs",
        "patrols",
        "predefinedParams",
        "safeZone",
        "sceneId",
        "sludgeDatas",
        "spawners",
        "specificData",
        "splines",
        "waterVolumes",
        "worldWayPointData",
    ],
    "NpcAtmosphericDataTable": [
        "dataTable",
    ],
    "LevelConfig": [
        "m_defaultState",
        "m_dimensionSourceLevelId",
        "m_id",
        "m_idNum",
        "m_isDimensionLevel",
        "m_isSeamless",
        "m_levelDataPaths",
        "m_levelGrids",
        "m_mapIdStr",
        "m_playerInitPos",
        "m_playerInitRot",
        "m_rectLeftBottom",
        "m_rectRightTop",
        "m_scope",
        "m_startPos",
    ],
    "LevelScriptData": [
        "actionMap",
        "activeShapeList",
        "allowStartOnTravelPole",
        "allowTick",
        "endType",
        "enemies",
        "exitBuffer",
        "exitBufferOverride",
        "interactiveLocks",
        "interactives",
        "levelScriptType",
        "lstTemplatePath",
        "maxStage",
        "modules",
        "npcs",
        "parentLevelScriptId",
        "properties",
        "propertyIdToKeyMap",
        "refWorldEntityIdList",
        "resetModeWhenActive",
        "resetModeWhenEnd",
        "scriptId",
        "startShapeList",
        "startType",
        "taskMap",
        "triggerVolumes",
    ],
    "LevelScriptTemplateData": [
        "actionMap",
        "maxStage",
        "properties",
        "propertyIdToKeyMap",
        "taskMap",
        "templateId",
    ],
    "LipSync": [
        "A",
        "E",
        "EyebrowRaise",
        "EyePitch",
        "EyeYaw",
        "HeadPitch",
        "HeadRoll",
        "HeadYaw",
        "Height",
        "I",
        "O",
        "Squint",
        "U",
        "WidthClose",
        "WidthOpen",
    ],
    "NPCMontageJson": [
        "animType",
        "data",
        "tag",
    ],
    "SpawnerConfig": [
        "configId",
        "enemyLibrary",
        "routeMap",
        "settings",
        "waveMap",
    ],
    "InteractiveTable": [
        "coreTemplatePathDict",
        "interactiveDataDict",
    ],
    "InteractiveTemplateData": [
        "name",
        "factionIndex",
        "objectType",
        "bornTag",
        "componentList",
        "delayRecyclePerformTime",
        "delayToRecycleTime",
        "enableBornFadeIn",
        "fadeInTime",
        "sendDieEvent",
        "allGlobalSaveProperties",
        "allMapSaveProperties",
        "aoiRadiusType",
        "configProperties",
        "dataMap",
        "facOccDis",
        "hideInDialog",
        "mountPoints",
        "propertyIdToKeyMap",
        "propertyKeyToIdMap",
        "saveProperties",
        "templateVariant",
        "tempProperties",
        "useGlobalVar",
        "useMapVar",
    ],
    "ModelViewStateControllerData": [
        "cameraSignalSourceAssetHashes",
        "clipAssetInfos",
        "effectIds",
        "emissiveConfigHashes",
        "modelAnimatorDatas",
        "modelId",
        "preTickAnimator",
    ],
    "SkillData": [
        "actionGroupData",
        "attackRangeType",
        "blackboard",
        "buffInputBase",
        "buffs",
        "canCastInAir",
        "canDummyCast",
        "canMove",
        "cardAttributeModifier",
        "castData",
        "castType",
        "characterReturnToIdle",
        "comboSkillUIBigSpriteName",
        "comboSkillUISpriteName",
        "dontInterruptCombo",
        "dummyPositionOffset",
        "durationFrame",
        "exclusiveFrame",
        "hittableAttackRange",
        "iconBgType",
        "iconId",
        "level",
        "needEnemyOutOfScreenWarning",
        "needEnemyOutOfScreenWarningOverrideValue",
        "offsetRecordFrame",
        "overrideHittableObjAttackRange",
        "overrideNeedEnemyOutOfScreenWarning",
        "passiveSkillType",
        "rootMotionCliffCheck",
        "selectStrategy",
        "showNotRecommendState",
        "skillHighlightCondition",
        "skillId",
        "skillName",
        "skillSpecification",
        "skillTags",
        "smartTargetBuffFindSettings",
        "smartTargetBuffIds",
        "smartTargetSelectStrategy",
        "smartTargetTagQuery",
        "switchToBuffConfig",
        "switchToCenterBeforeCast",
        "tagDuringAttach",
        "toggleBuffs",
        "uiRangeHints",
    ],
}

BUFF_MEMORYPACK_FIELD_TYPES = {
    "abilityEventAction": "List",
    "addingCooldown": "Beyond.Blackboard.BlackboardDouble",
    "applyTags": "Beyond.Gameplay.Core.GameplayTagList",
    "attributeModifier": "Beyond.Gameplay.AttributeModifierData.AttributeModifier",
    "blackboard": "Dictionary",
    "buffEventAction": "List",
    "damageModifier": "List",
    "dispelConfig": "Beyond.Gameplay.Core.DispelConfig",
    "duration": "Beyond.Blackboard.BlackboardDouble",
    "finishOnRepatriate": "System.Boolean",
    "globalModifier": "List",
    "hasAddingCooldown": "System.Boolean",
    "hasIcon": "System.Boolean",
    "healModifier": "List",
    "iconConfig": "Beyond.Gameplay.Core.BuffIconConfig.BuffIconStyle",
    "id": "System.String",
    "igniteEventAction": "List",
    "ignoreCooldownWhenAdding": "System.Boolean",
    "ignoreTagImmune": "System.Boolean",
    "lifeType": "Beyond.Gameplay.Core.Buff.LifeType",
    "maxTriggerCnt": "Beyond.Blackboard.BlackboardInt",
    "poiseModifier": "List",
    "shieldConfigs": "List",
    "stackingSettings": "Beyond.Gameplay.Core.BuffStackingSettings.IdentifierType",
    "tagsAfterTriggerExtendBuffAction": "Beyond.Gameplay.Core.GameplayTagList",
    "timelineActions": "List",
    "triggerInterval": "Beyond.Blackboard.BlackboardDouble",
    "useTimeDilationDt": "System.Boolean",
    "waitFirstTriggerInterval": "System.Boolean",
}
BUFF_VALUE_FIELD_NAMES = {
    "addingCooldown",
    "duration",
    "finishOnRepatriate",
    "hasAddingCooldown",
    "hasIcon",
    "id",
    "ignoreCooldownWhenAdding",
    "ignoreTagImmune",
    "lifeType",
    "maxTriggerCnt",
    "triggerInterval",
    "useTimeDilationDt",
    "waitFirstTriggerInterval",
}
BUFF_SCHEMA_SAMPLE_FIELDS = [
    "id",
    "duration",
    "lifeType",
    "triggerInterval",
    "maxTriggerCnt",
    "applyTags",
    "attributeModifier",
    "buffEventAction",
    "blackboard",
    "timelineActions",
]
SKILL_MEMORYPACK_FIELD_TYPES = {
    "actionGroupData": "Beyond.Gameplay.Core.ActionGroupData",
    "attackRangeType": "Beyond.Gameplay.AttackRangeType",
    "blackboard": "Dictionary",
    "buffInputBase": "Beyond.Gameplay.Core.BuffInputBase",
    "buffs": "List",
    "canCastInAir": "System.Boolean",
    "canDummyCast": "System.Boolean",
    "canMove": "System.Boolean",
    "cardAttributeModifier": "Beyond.Gameplay.AttributeModifierData.AttributeModifier",
    "castData": "Beyond.Gameplay.Core.CastData.CostData",
    "castType": "Beyond.Gameplay.CastType",
    "characterReturnToIdle": "System.Boolean",
    "comboSkillUIBigSpriteName": "System.String",
    "comboSkillUISpriteName": "System.String",
    "dontInterruptCombo": "System.Boolean",
    "dummyPositionOffset": "UnityEngine.Vector3",
    "durationFrame": "System.Int32",
    "exclusiveFrame": "System.Int32",
    "hittableAttackRange": "System.Single",
    "iconBgType": "Beyond.GEnums.DamageType",
    "iconId": "System.String",
    "level": "System.Int32",
    "needEnemyOutOfScreenWarning": "System.Boolean",
    "needEnemyOutOfScreenWarningOverrideValue": "System.Boolean",
    "offsetRecordFrame": "System.Int32",
    "overrideHittableObjAttackRange": "System.Boolean",
    "overrideNeedEnemyOutOfScreenWarning": "System.Boolean",
    "passiveSkillType": "Beyond.Gameplay.PassiveSkillType",
    "rootMotionCliffCheck": "System.Boolean",
    "selectStrategy": "Beyond.Gameplay.SelectStrategy",
    "showNotRecommendState": "System.Boolean",
    "skillHighlightCondition": "Beyond.Gameplay.Core.SequenceActionData",
    "skillId": "System.String",
    "skillName": "System.String",
    "skillSpecification": "Beyond.Gameplay.SkillSpecification",
    "skillTags": "Beyond.Gameplay.Core.GameplayTagList",
    "smartTargetBuffFindSettings": "Beyond.Gameplay.Core.BuffFindSettings.CheckType",
    "smartTargetBuffIds": "List",
    "smartTargetSelectStrategy": "Beyond.Gameplay.SmartTargetSelectStrategy",
    "smartTargetTagQuery": "Beyond.Gameplay.Core.GameplayTagQuery.QueryType",
    "switchToBuffConfig": "Beyond.Gameplay.Core.SwitchToBuffConfig",
    "switchToCenterBeforeCast": "System.Boolean",
    "tagDuringAttach": "Beyond.Gameplay.Core.GameplayTagList",
    "toggleBuffs": "List",
    "uiRangeHints": "List",
}
SKILL_VALUE_FIELD_NAMES = {
    "attackRangeType",
    "canCastInAir",
    "canDummyCast",
    "canMove",
    "castType",
    "characterReturnToIdle",
    "comboSkillUIBigSpriteName",
    "comboSkillUISpriteName",
    "dontInterruptCombo",
    "dummyPositionOffset",
    "durationFrame",
    "exclusiveFrame",
    "hittableAttackRange",
    "iconBgType",
    "iconId",
    "level",
    "needEnemyOutOfScreenWarning",
    "needEnemyOutOfScreenWarningOverrideValue",
    "offsetRecordFrame",
    "overrideHittableObjAttackRange",
    "overrideNeedEnemyOutOfScreenWarning",
    "passiveSkillType",
    "rootMotionCliffCheck",
    "selectStrategy",
    "showNotRecommendState",
    "skillId",
    "skillName",
    "skillSpecification",
    "smartTargetSelectStrategy",
    "switchToCenterBeforeCast",
}
SKILL_SCHEMA_SAMPLE_FIELDS = [
    "skillId",
    "skillName",
    "level",
    "iconId",
    "durationFrame",
    "exclusiveFrame",
    "hittableAttackRange",
    "skillTags",
    "actionGroupData",
    "buffs",
    "blackboard",
    "switchToBuffConfig",
]
SKILL_DEFAULT_SWITCH_TO_BUFF_CONFIG_BYTE_LENGTH = 148
SKILL_UI_RANGE_HINT_MEMBER_COUNT = 3
SKILL_HINT_SHAPE_MEMBER_COUNT = 21
SKILL_HINT_SHAPE_NAMES = {
    0: "Point",
    1: "Rectangle",
    2: "Circle",
    3: "Sector",
    4: "Arrow",
    5: "VirtualArrow",
}
NUMERIC_STEM_RE = re.compile(r"^\d+$")
TRAILING_VARIANT_TOKEN_RE = re.compile(r"^\d+[A-Za-z]?$")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build WebUI indexes for StreamingAssets/Data.")
    parser.add_argument(
        "--export-root",
        type=Path,
        default=DEFAULT_EXPORT_ROOT,
        help=f"Export root that contains structured/StreamingAssets/Data. Default: {DEFAULT_EXPORT_ROOT}",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root to scan. Overrides --export-root/structured/StreamingAssets/Data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=GAME_DATA_DIR,
        help=f"Output directory under webui/data. Default: {GAME_DATA_DIR}",
    )
    parser.add_argument(
        "--groups",
        nargs="*",
        default=None,
        help="Optional top-level Data groups to scan, e.g. Json Bundles.",
    )
    return parser.parse_args(argv)


def rel_to_data_root(path: Path, data_root: Path) -> str:
    return path.relative_to(data_root).as_posix()


def first_group(rel: str) -> str:
    return rel.split("/", 1)[0] if rel else "[root]"


def category_for_rel(rel: str) -> str:
    parts = rel.split("/")
    if len(parts) > 1:
        return parts[1]
    return "[root]"


def stem_prefix(stem: str, group: str) -> str:
    text = str(stem or "").strip()
    if not text:
        return "[root]"
    text = re.sub(r"_meta$", "", text, flags=re.IGNORECASE)
    if NUMERIC_STEM_RE.fullmatch(text):
        return text[:4] if len(text) > 4 else text

    tokens = [token for token in re.split(r"[_\-.]+", text) if token]
    if not tokens:
        return text

    if group == "Json":
        while len(tokens) > 1 and TRAILING_VARIANT_TOKEN_RE.fullmatch(tokens[-1]):
            tokens.pop()
        return "_".join(tokens[:2])

    return tokens[0]


def structured_prefix_for_rel(rel: str) -> str:
    parts = rel.split("/")
    if len(parts) >= 4 and parts[0] == "Json":
        return "/".join(parts[1:-1])
    return ""


def entry_prefix_for_rel(rel: str) -> str:
    parts = rel.split("/")
    group = parts[0] if parts else ""
    filename = parts[-1] if parts else rel
    stem = Path(filename).stem
    if group in PREFIX_GROUP_ROOTS:
        structured = structured_prefix_for_rel(rel)
        if structured:
            return structured
        return stem_prefix(stem, group)
    return category_for_rel(rel)


def index_group_for_rel(rel: str) -> str:
    parts = rel.split("/")
    group = parts[0] if parts else "[root]"
    if group == "Json":
        dir_parts = parts[1:-1]
        if dir_parts:
            return "Json/" + "/".join(dir_parts[:1])
        return "Json/" + entry_prefix_for_rel(rel)

    if group == "Bundles":
        if len(parts) >= 4 and parts[2].lower() == "main":
            stem = Path(parts[-1]).stem
            if HEX_STEM_RE.fullmatch(stem):
                shard = stem[:BUNDLE_MAIN_SHARD_CHARS].lower()
            else:
                shard = (stem_prefix(stem, group)[:BUNDLE_MAIN_SHARD_CHARS] or "misc").lower()
            return "/".join(parts[:3] + [shard])
        if len(parts) >= 4:
            return "/".join(parts[:3])
        if len(parts) >= 2:
            return "/".join(parts[:2])
        return group

    if group in {"Streaming", "DynamicStreaming", "IrradianceVolume"}:
        if len(parts) >= 3:
            return "/".join(parts[:3])
        if len(parts) >= 2:
            return "/".join(parts[:2])
        return group

    if group == "Video":
        if len(parts) >= 3:
            return "/".join(parts[:3])
        if len(parts) >= 2:
            return "/".join(parts[:2])
        return group

    if group in {"Audio", "ExtendData"}:
        if len(parts) >= 2:
            return "/".join(parts[:2])
        return group

    return group


def ext_label(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "[none]"


def should_index_path(path: Path, data_root: Path) -> bool:
    rel = rel_to_data_root(path, data_root)
    return first_group(rel) not in EXCLUDED_GROUPS and ext_label(path) not in EXCLUDED_EXTENSIONS


def hex_signature(data: bytes, length: int = 8) -> str:
    return " ".join(f"{byte:02X}" for byte in data[:length])



def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
def read_header(path: Path) -> bytes:
    try:
        with path.open("rb") as fh:
            return fh.read(HEADER_BYTES)
    except OSError:
        return b""


def text_json_encoding_from_header(data: bytes) -> str | None:
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith(b"\xff\xfe"):
        return "utf-16le"
    if data.startswith(b"\xfe\xff"):
        return "utf-16be"
    stripped = data.lstrip()
    if stripped.startswith((b"{", b"[")):
        return "utf-8-sig"
    return None


def load_text_json(path: Path, encoding: str) -> tuple[Any, str]:
    raw = path.read_bytes()
    if encoding == "utf-16le" and raw.startswith(b"\xff\xfe"):
        text = raw[2:].decode("utf-16le")
    elif encoding == "utf-16be" and raw.startswith(b"\xfe\xff"):
        text = raw[2:].decode("utf-16be")
    else:
        text = raw.decode(encoding)
    return json.loads(text), encoding


def scalar_string(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return ""


def add_sample(out: list[str], label: str, value: Any) -> None:
    text = scalar_string(value).strip()
    if not text:
        return
    if len(text) > 60:
        text = text[:57] + "..."
    item = f"{label}={text}" if label else text
    if item not in out:
        out.append(item)


def collect_json_samples(node: Any, out: list[str], *, depth: int = 0) -> None:
    if len(out) >= STRING_SAMPLE_LIMIT or depth > 4:
        return
    if isinstance(node, dict):
        for key, value in node.items():
            if len(out) >= STRING_SAMPLE_LIMIT:
                return
            key_text = str(key)
            if key_text in INTERESTING_STRING_KEYS:
                add_sample(out, key_text, value)
        for key, value in list(node.items())[:24]:
            if len(out) >= STRING_SAMPLE_LIMIT:
                return
            if isinstance(value, (dict, list)):
                collect_json_samples(value, out, depth=depth + 1)
            elif depth <= 1:
                add_sample(out, str(key), value)
    elif isinstance(node, list):
        for value in node[:16]:
            if len(out) >= STRING_SAMPLE_LIMIT:
                return
            collect_json_samples(value, out, depth=depth + 1)


def summarize_json(node: Any) -> tuple[str, list[str], int | None, str]:
    keys: list[str] = []
    row_count: int | None = None
    if isinstance(node, dict):
        keys = [str(key) for key in list(node.keys())[:12]]
        if len(node) == 1:
            key = next(iter(node.keys()))
            value = node[key]
            if isinstance(value, dict):
                row_count = len(value)
                summary = f"object key {key} with {row_count} object entries"
            elif isinstance(value, list):
                row_count = len(value)
                summary = f"object key {key} with {row_count} array entries"
            else:
                summary = f"object key {key}"
        elif isinstance(node.get("dataTable"), dict):
            row_count = len(node["dataTable"])
            summary = f"dataTable with {row_count} entries"
        elif isinstance(node.get("array"), list):
            row_count = len(node["array"])
            summary = f"array wrapper with {row_count} entries"
        else:
            summary = f"object with {len(node)} keys"
    elif isinstance(node, list):
        row_count = len(node)
        if node and isinstance(node[0], dict):
            keys = [str(key) for key in list(node[0].keys())[:12]]
            summary = f"array with {row_count} object entries"
        else:
            summary = f"array with {row_count} entries"
    else:
        summary = type(node).__name__

    samples: list[str] = []
    collect_json_samples(node, samples)
    return summary, keys, row_count, " | ".join(samples)[:STRING_SAMPLE_MAX_CHARS]


def u32_values(data: bytes, count: int = 4) -> list[int]:
    values: list[int] = []
    padded = data + b"\x00" * max(0, count * 4 - len(data))
    for index in range(count):
        values.append(struct.unpack_from("<I", padded, index * 4)[0])
    return values



def read_binary_for_parser(path: Path, size: int, header: bytes, *, max_size: int = 262_144) -> bytes:
    if size <= max_size:
        try:
            return path.read_bytes()
        except OSError:
            return header
    return header


def read_u32_at(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def read_i32_at(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, offset)[0]


def flatbuffer_table_layout(data: bytes, table_pos: int) -> tuple[int, int, list[int]] | None:
    vtable_rel = read_i32_at(data, table_pos)
    if vtable_rel is None or vtable_rel <= 0:
        return None
    vtable_pos = table_pos - vtable_rel
    if vtable_pos < 0 or vtable_pos + 4 > len(data):
        return None
    vtable_len, object_len = struct.unpack_from("<HH", data, vtable_pos)
    if not (4 <= vtable_len <= 512 and (vtable_len - 4) % 2 == 0):
        return None
    if not (4 <= object_len <= 65535):
        return None
    if vtable_pos + vtable_len > len(data):
        return None
    field_count = (vtable_len - 4) // 2
    if field_count > FLATBUFFER_MAX_FIELDS:
        return None
    if table_pos + 4 > len(data):
        return None
    offsets = list(struct.unpack_from("<" + "H" * field_count, data, vtable_pos + 4)) if field_count else []
    return vtable_pos, object_len, offsets


def flatbuffer_root_layout(data: bytes, size: int) -> tuple[int, int, int, list[int]] | None:
    if len(data) < 16:
        return None
    root_offset = read_u32_at(data, 0)
    if root_offset is None:
        return None
    if root_offset < 4 or root_offset > 1_000_000:
        return None
    if root_offset + 8 > min(size, len(data)):
        return None
    layout = flatbuffer_table_layout(data, root_offset)
    if not layout:
        return None
    vtable_pos, object_len, offsets = layout
    return root_offset, vtable_pos, object_len, offsets


def flatbuffer_uoffset_target(data: bytes, offset: int) -> int | None:
    rel = read_u32_at(data, offset)
    if rel is None or rel == 0:
        return None
    target = offset + rel
    if target < 0 or target >= len(data):
        return None
    return target


def flatbuffer_string_at(data: bytes, offset: int) -> str | None:
    length = read_u32_at(data, offset)
    if length is None or length <= 0 or length > FLATBUFFER_MAX_STRING_LENGTH:
        return None
    end = offset + 4 + length
    if end >= len(data) or data[end] != 0:
        return None
    raw = data[offset + 4:end]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if any(ord(ch) < 32 for ch in text):
        return None
    if not any(ch.isalnum() for ch in text):
        return None
    return text


def flatbuffer_vector_length_at(data: bytes, offset: int) -> int | None:
    length = read_u32_at(data, offset)
    if length is None or length > FLATBUFFER_MAX_VECTOR_LENGTH:
        return None
    if length == 0:
        return length
    if offset + 4 + length <= len(data) or offset + 4 + length * 4 <= len(data):
        return length
    return None


def add_flatbuffer_sample(samples: list[str], text: str | None) -> None:
    if not text:
        return
    text = text.strip()
    if not text:
        return
    if len(text) > 96:
        text = text[:93] + "..."
    if text not in samples:
        samples.append(text)


def collect_flatbuffer_strings_from_vector(
    data: bytes,
    vector_pos: int,
    vector_len: int,
    samples: list[str],
    seen_tables: set[int],
    depth: int,
) -> None:
    if len(samples) >= STRING_SAMPLE_LIMIT or depth > 2:
        return
    for index in range(min(vector_len, 10)):
        elem_pos = vector_pos + 4 + index * 4
        target = flatbuffer_uoffset_target(data, elem_pos)
        if target is None:
            continue
        text = flatbuffer_string_at(data, target)
        if text:
            add_flatbuffer_sample(samples, text)
        elif flatbuffer_table_layout(data, target):
            collect_flatbuffer_strings_from_table(data, target, samples, seen_tables, depth + 1)
        if len(samples) >= STRING_SAMPLE_LIMIT:
            return


def collect_flatbuffer_strings_from_table(
    data: bytes,
    table_pos: int,
    samples: list[str],
    seen_tables: set[int],
    depth: int = 0,
) -> None:
    if len(samples) >= STRING_SAMPLE_LIMIT or depth > 2 or table_pos in seen_tables:
        return
    layout = flatbuffer_table_layout(data, table_pos)
    if not layout:
        return
    seen_tables.add(table_pos)
    _, _, offsets = layout
    for field_offset in offsets[:64]:
        if not field_offset:
            continue
        field_pos = table_pos + field_offset
        target = flatbuffer_uoffset_target(data, field_pos)
        if target is None:
            continue
        text = flatbuffer_string_at(data, target)
        if text:
            add_flatbuffer_sample(samples, text)
        else:
            vector_len = flatbuffer_vector_length_at(data, target)
            if vector_len is not None:
                collect_flatbuffer_strings_from_vector(data, target, vector_len, samples, seen_tables, depth)
            if flatbuffer_table_layout(data, target):
                collect_flatbuffer_strings_from_table(data, target, samples, seen_tables, depth + 1)
        if len(samples) >= STRING_SAMPLE_LIMIT:
            return


def root_flatbuffer_vector_lengths(data: bytes, root_offset: int, offsets: list[int]) -> dict[str, int]:
    vectors: dict[str, int] = {}
    for index, field_offset in enumerate(offsets):
        if not field_offset:
            continue
        target = flatbuffer_uoffset_target(data, root_offset + field_offset)
        if target is None or flatbuffer_string_at(data, target):
            continue
        vector_len = flatbuffer_vector_length_at(data, target)
        if vector_len is not None:
            vectors[f"field{index}"] = vector_len
    return vectors


def decode_flatbuffer_bytes(rel: str, path: Path, size: int, header: bytes) -> dict[str, Any] | None:
    data = read_binary_for_parser(path, size, header, max_size=FLATBUFFER_PREVIEW_MAX_BYTES)
    layout = flatbuffer_root_layout(data, size)
    if not layout:
        return None
    root_offset, _vtable_pos, object_len, offsets = layout
    field_count = len(offsets)
    present_fields = [index for index, field_offset in enumerate(offsets) if field_offset]
    vector_lengths = root_flatbuffer_vector_lengths(data, root_offset, offsets)
    positive_vectors = {name: count for name, count in vector_lengths.items() if count > 0}
    empty_vectors = [name for name, count in sorted(vector_lengths.items()) if count == 0]
    vector_parts = [f"{name}:{count}" for name, count in sorted(positive_vectors.items())[:8]]
    summary = (
        f"FlatBuffer-like binary; root {root_offset}, object {object_len} bytes, "
        f"{field_count} fields, {len(present_fields)} present"
    )
    if vector_parts:
        summary += "; vectors " + ", ".join(vector_parts)
    elif empty_vectors:
        suffix = ",..." if len(empty_vectors) > 6 else ""
        summary += "; empty vectors " + ", ".join(empty_vectors[:6]) + suffix
    if size > len(data):
        summary += f"; previewed first {len(data) // 1024} KiB"

    samples: list[str] = []
    collect_flatbuffer_strings_from_table(data, root_offset, samples, set())
    sample_parts: list[str] = []
    if present_fields:
        names = [f"field{index}" for index in present_fields[:16]]
        suffix = ",..." if len(present_fields) > 16 else ""
        sample_parts.append("present=" + ",".join(names) + suffix)
    if samples:
        sample_parts.append("strings=" + " | ".join(samples[:STRING_SAMPLE_LIMIT]))
    sample_parts.append(FLATBUFFER_SCHEMALESS_SOURCE_NOTE)
    rows = max(positive_vectors.values()) if positive_vectors else None
    return {
        "kind": "flatbuffer-bytes",
        "subtype": category_for_rel(rel),
        "summary": summary,
        "keys": [f"field{index}" for index in present_fields[:24]],
        "rows": rows,
        "sample": "; ".join(sample_parts),
    }


def memorypack_member_count(data: bytes) -> int | None:
    if not data:
        return None
    first = data[0]
    if first < MEMORYPACK_EXTENDED_OBJECT_HEADER and first <= MEMORYPACK_MAX_MEMBER_COUNT:
        return first
    return None


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
        if len(rows) < 16:
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
        if len(audio_rows) < 16:
            audio_rows.append({
                "state": state,
                "stateName": state_name,
                "audioCount": event_count,
                "events": events[:12],
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
        if len(custom_rows) < 16:
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
        "sampleAudioRows": audio_rows,
        "sampleCustomRows": custom_rows,
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


def format_offset(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def summarize_member_counts(counts: list[int | None], limit: int = 15) -> str:
    values: list[str] = []
    for index, count in enumerate(counts[:limit], start=1):
        values.append(f"{index}={'null' if count is None else count}")
    if len(counts) > limit:
        values.append("...")
    return ", ".join(values)


def read_memorypack_utf8_string(
    data: bytes,
    offset: int,
    *,
    max_length: int = 16_384,
) -> tuple[str | None, int, str | None]:
    if offset + 4 > len(data):
        return None, offset, "truncated-length"
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length == MEMORYPACK_NULL_COUNT:
        return None, offset, None
    if length > max_length or offset + length > len(data):
        return None, offset, f"invalid-length={length}"
    raw = data[offset:offset + length]
    offset += length
    return raw.decode("utf-8", "replace"), offset, None


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


def scan_length_prefixed_utf8_string_hits(
    data: bytes,
    *,
    start: int = 0,
    max_scan_bytes: int | None = None,
    max_samples: int = 128,
    min_length: int = 2,
    max_length: int = 160,
) -> list[dict[str, Any]]:
    end = len(data) if max_scan_bytes is None else min(len(data), start + max_scan_bytes)
    hits: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for pos in range(max(start, 0), max(start, end - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        if length < min_length or length > max_length or pos + 4 + length > end:
            continue
        raw = data[pos + 4:pos + 4 + length]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text):
            continue
        if not any(ch.isalnum() for ch in text):
            continue
        key = (pos, text)
        if key in seen:
            continue
        seen.add(key)
        hits.append({"offset": format_offset(pos), "length": length, "value": text})
        if len(hits) >= max_samples:
            break
    return hits


def contains_length_prefixed_utf8_string(data: bytes, value: str) -> bool:
    if not value:
        return False
    raw = value.encode("utf-8")
    if not raw:
        return False
    marker = struct.pack("<I", len(raw)) + raw
    return marker in data




def length_prefixed_utf8_string_marker_info(
    data: bytes,
    value: str,
    *,
    max_offsets: int = 8,
) -> tuple[int, list[int]]:
    if not value:
        return 0, []
    raw = value.encode("utf-8")
    if not raw:
        return 0, []
    marker = struct.pack("<I", len(raw)) + raw
    count = 0
    offsets: list[int] = []
    start = 0
    while True:
        pos = data.find(marker, start)
        if pos < 0:
            break
        count += 1
        if len(offsets) < max_offsets:
            offsets.append(pos)
        start = pos + 1
    return count, offsets


def format_offset_list(offsets: list[int], total_count: int | None = None) -> str:
    if not offsets:
        return ""
    values = [format_offset(offset) for offset in offsets]
    if total_count is not None and total_count > len(offsets):
        values.append("...")
    return ",".join(values)


def compact_memorypack_type_name(type_name: str) -> str:
    text = str(type_name or "").replace("+", ".").replace("&", "").strip()
    if text.startswith("System."):
        return text.rsplit(".", 1)[-1]
    if text.startswith("UnityEngine."):
        return text.rsplit(".", 1)[-1]
    if text in {"List", "Dictionary"}:
        return text
    if "." in text:
        return text.rsplit(".", 1)[-1]
    return text or "unknown"


def memorypack_schema_type_sample_parts(
    field_types: dict[str, str],
    sample_fields: list[str],
) -> list[str]:
    parts: list[str] = []
    for field_name in sample_fields:
        type_name = field_types.get(field_name, "unknown")
        parts.append(f"{field_name}:{compact_memorypack_type_name(type_name)}")
    return parts


def memorypack_schema_field_groups(
    schema: list[str],
    value_field_names: set[str],
) -> tuple[list[str], list[str]]:
    value_fields = [field for field in schema if field in value_field_names]
    complex_fields = [field for field in schema if field not in value_field_names]
    return value_fields, complex_fields


def skill_schema_type_sample_parts() -> list[str]:
    return memorypack_schema_type_sample_parts(
        SKILL_MEMORYPACK_FIELD_TYPES,
        SKILL_SCHEMA_SAMPLE_FIELDS,
    )


def skill_schema_field_groups(schema: list[str]) -> tuple[list[str], list[str]]:
    return memorypack_schema_field_groups(schema, SKILL_VALUE_FIELD_NAMES)


def buff_schema_type_sample_parts() -> list[str]:
    return memorypack_schema_type_sample_parts(
        BUFF_MEMORYPACK_FIELD_TYPES,
        BUFF_SCHEMA_SAMPLE_FIELDS,
    )


def buff_schema_field_groups(schema: list[str]) -> tuple[list[str], list[str]]:
    return memorypack_schema_field_groups(schema, BUFF_VALUE_FIELD_NAMES)

def unique_strings(values: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
            if len(out) >= limit:
                break
    return out


def is_buff_param_string(value: str) -> bool:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{1,48}$", value):
        return False
    if value.startswith(("buff_", "icon_", "au_", "P_")):
        return False
    return "/" not in value


def read_buff_u32_field(data: bytes, offset: int, field_name: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-u32")
    return struct.unpack_from("<I", data, offset)[0], offset + 4


def read_buff_bool_field(data: bytes, offset: int, field_name: str) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-bool")
    raw = data[offset]
    if raw not in (0, 1):
        raise ValueError(f"{field_name}:invalid-bool={raw}")
    return bool(raw), offset + 1


def read_buff_blackboard_int_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}.blackboardKey:{error}")
    use_blackboard_key, offset = read_buff_bool_field(data, offset, f"{field_name}.useBlackboardKey")
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}.value:truncated-i32")
    value = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "value": value,
    }, offset


def read_buff_blackboard_float_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{field_name}:member-count={member_count}")
    key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}.blackboardKey:{error}")
    use_blackboard_key, offset = read_buff_bool_field(data, offset, f"{field_name}.useBlackboardKey")
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}.value:truncated-f32")
    value = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "blackboardKey": key or "",
        "useBlackboardKey": use_blackboard_key,
        "serializedValueType": "System.Single",
        "value": round(value, 6),
    }, offset


def read_buff_gameplay_tag_field(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count not in (0, 2):
        raise ValueError(f"{field_name}:member-count={member_count}")
    tag_id, offset = read_buff_u32_field(data, offset, f"{field_name}.tagId")
    tag_name, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}.tagName:{error}")
    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "tagId": tag_id,
        "tagName": tag_name or "",
    }, offset


def read_buff_stacking_settings_compact_id_branch(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError("stackingSettings:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 12:
        raise ValueError(f"stackingSettings:member-count={member_count}")

    identifier_type = data[offset]
    offset += 1
    if identifier_type not in (0, 1):
        raise ValueError(f"stackingSettings.identifierType:raw={identifier_type}")
    is_need_stack_effect, offset = read_buff_bool_field(
        data,
        offset,
        "stackingSettings.isNeedStackEffect",
    )
    if offset + 4 > len(data):
        raise ValueError("stackingSettings.maxStackCnt:truncated-i32")
    max_stack_count = struct.unpack_from("<i", data, offset)[0]
    offset += 4
    max_stack_count_key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"stackingSettings.maxStackCntKey:{error}")
    negate_priority, offset = read_buff_bool_field(data, offset, "stackingSettings.negatePriority")
    if offset + 4 > len(data):
        raise ValueError("stackingSettings.priority:truncated-f32")
    priority = struct.unpack_from("<f", data, offset)[0]
    offset += 4
    priority_key, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"stackingSettings.priorityKey:{error}")
    stack_effect_count, offset = read_buff_u32_field(data, offset, "stackingSettings.stackEffectsCount")
    if stack_effect_count > 256:
        raise ValueError(f"stackingSettings.stackEffectsCount:large-count={stack_effect_count}")
    stacking_type = data[offset]
    offset += 1
    if stacking_type > 16:
        raise ValueError(f"stackingSettings.stackingType:raw={stacking_type}")
    use_max_stack_count_key, offset = read_buff_bool_field(
        data,
        offset,
        "stackingSettings.useMaxStackCntKey",
    )
    use_priority_key, offset = read_buff_bool_field(data, offset, "stackingSettings.usePriorityKey")

    return {
        "memberCount": member_count,
        "offset": format_offset(start),
        "branch": "compact-id",
        "branchNote": "validated rows use identifierType=Id; stackingKey branch remains opaque",
        "identifierTypeRaw": identifier_type,
        "stackingTypeRaw": stacking_type,
        "maxStackCnt": max_stack_count,
        "maxStackCntKey": max_stack_count_key or "",
        "useMaxStackCntKey": use_max_stack_count_key,
        "usePriorityKey": use_priority_key,
        "priority": round(priority, 6),
        "priorityKey": priority_key or "",
        "negatePriority": negate_priority,
        "isNeedStackEffect": is_need_stack_effect,
        "stackEffectsCount": stack_effect_count,
    }, offset


def summarize_buff_post_id_prefix_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "idMarkerOffset": candidate.get("idMarkerOffset"),
        "status": candidate.get("status"),
        "offset": candidate.get("offset"),
        "endOffset": candidate.get("endOffset"),
    }
    for key in (
        "tailParseStatus",
        "tailParseOffset",
        "error",
        "tailParseError",
        "igniteEventActionCount",
        "poiseModifierCount",
        "shieldConfigsCount",
    ):
        if key in candidate:
            summary[key] = candidate.get(key)
    return {key: value for key, value in summary.items() if value not in (None, "")}


def decode_buff_post_id_prefix_at(
    data: bytes,
    id_value: str,
    id_marker_offset: int,
) -> dict[str, Any]:
    start = id_marker_offset + 4 + len(id_value.encode("utf-8"))
    offset = start
    try:
        ignite_count, offset = read_buff_u32_field(data, offset, "igniteEventActionCount")
        if ignite_count > 256:
            raise ValueError(f"igniteEventActionCount:large-count={ignite_count}")
        ignore_cooldown, offset = read_buff_bool_field(
            data,
            offset,
            "ignoreCooldownWhenAdding",
        )
        ignore_tag_immune, offset = read_buff_bool_field(data, offset, "ignoreTagImmune")
        if offset >= len(data):
            raise ValueError("lifeType:truncated-u8")
        life_type = data[offset]
        offset += 1
        max_trigger_count, offset = read_buff_blackboard_int_field(
            data,
            offset,
            "maxTriggerCnt",
        )
        poise_modifier_count, offset = read_buff_u32_field(data, offset, "poiseModifierCount")
        if poise_modifier_count > 256:
            raise ValueError(f"poiseModifierCount:large-count={poise_modifier_count}")

        result: dict[str, Any] = {
            "status": "parsed-through-poiseModifierCount",
            "source": "anchored after exact top-level id marker; stops before nonzero list bodies",
            "idMarkerOffset": format_offset(id_marker_offset),
            "offset": format_offset(start),
            "igniteEventActionCount": ignite_count,
            "ignoreCooldownWhenAdding": ignore_cooldown,
            "ignoreTagImmune": ignore_tag_immune,
            "lifeTypeRaw": life_type,
            "maxTriggerCnt": max_trigger_count,
            "poiseModifierCount": poise_modifier_count,
        }
        if poise_modifier_count == 0:
            shield_config_count, offset = read_buff_u32_field(data, offset, "shieldConfigsCount")
            if shield_config_count > 256:
                raise ValueError(f"shieldConfigsCount:large-count={shield_config_count}")
            result["shieldConfigsCount"] = shield_config_count
            result["status"] = "parsed-through-shieldConfigsCount"
            if shield_config_count == 0:
                tail_offset = offset
                try:
                    stacking_settings, tail_offset = read_buff_stacking_settings_compact_id_branch(
                        data,
                        tail_offset,
                    )
                    tags_after_trigger, tail_offset = read_buff_gameplay_tag_field(
                        data,
                        tail_offset,
                        "tagsAfterTriggerExtendBuffAction",
                    )
                    timeline_action_count, tail_offset = read_buff_u32_field(
                        data,
                        tail_offset,
                        "timelineActionsCount",
                    )
                    if timeline_action_count > 256:
                        raise ValueError(f"timelineActionsCount:large-count={timeline_action_count}")
                    trigger_interval, tail_offset = read_buff_blackboard_float_field(
                        data,
                        tail_offset,
                        "triggerInterval",
                    )
                    use_time_dilation_dt, tail_offset = read_buff_bool_field(
                        data,
                        tail_offset,
                        "useTimeDilationDt",
                    )
                    wait_first_trigger_interval, tail_offset = read_buff_bool_field(
                        data,
                        tail_offset,
                        "waitFirstTriggerInterval",
                    )
                    if tail_offset != len(data):
                        raise ValueError(f"tail-not-exact={format_offset(tail_offset)}")
                    result["status"] = "parsed-through-exact-tail"
                    result["stackingSettings"] = stacking_settings
                    result["tagsAfterTriggerExtendBuffAction"] = tags_after_trigger
                    result["timelineActionsCount"] = timeline_action_count
                    result["triggerInterval"] = trigger_interval
                    result["useTimeDilationDt"] = use_time_dilation_dt
                    result["waitFirstTriggerInterval"] = wait_first_trigger_interval
                    result["endOffset"] = format_offset(tail_offset)
                except (struct.error, UnicodeDecodeError, ValueError) as tail_exc:
                    result["tailParseStatus"] = "parse-error"
                    result["tailParseOffset"] = format_offset(tail_offset)
                    result["tailParseError"] = str(tail_exc)
        else:
            result["stopReason"] = "poiseModifier list body not skipped"
        result.setdefault("endOffset", format_offset(offset))
        return result
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        return {
            "status": "parse-error",
            "idMarkerOffset": format_offset(id_marker_offset),
            "offset": format_offset(offset),
            "error": str(exc),
        }


def decode_buff_post_id_prefix(
    data: bytes,
    id_value: str,
    id_marker_count: int,
    id_marker_offsets: list[int],
) -> dict[str, Any]:
    if not id_value or not id_marker_offsets:
        return {"status": "missing-id-marker"}

    candidates = [
        decode_buff_post_id_prefix_at(data, id_value, marker_offset)
        for marker_offset in id_marker_offsets
    ]
    if id_marker_count == 1:
        return candidates[0]

    exact_candidates = [
        candidate for candidate in candidates
        if candidate.get("status") == "parsed-through-exact-tail"
    ]
    if len(exact_candidates) == 1:
        result = dict(exact_candidates[0])
        result["anchorSelection"] = {
            "status": "selected-from-ambiguous-id-markers",
            "idMarkerCount": id_marker_count,
            "selectedIdMarkerOffset": result.get("idMarkerOffset"),
            "selectionCriteria": "unique BuffData id marker candidate parsed through exact tail",
            "candidateSummaries": [
                summarize_buff_post_id_prefix_candidate(candidate)
                for candidate in candidates[:12]
            ],
        }
        return result

    return {
        "status": "ambiguous-id-marker",
        "idMarkerCount": id_marker_count,
        "candidateCount": len(candidates),
        "idMarkerOffsets": [format_offset(offset) for offset in id_marker_offsets],
        "selectionCriteria": "requires a unique BuffData candidate that parses through exact tail",
        "candidateSummaries": [
            summarize_buff_post_id_prefix_candidate(candidate)
            for candidate in candidates[:12]
        ],
    }

def buff_post_id_prefix_sample(prefix: dict[str, Any]) -> str:
    status = str(prefix.get("status") or "")
    if not status.startswith("parsed-through"):
        return ""
    max_trigger = prefix.get("maxTriggerCnt") or {}
    if prefix.get("status") == "parsed-through-exact-tail":
        stacking = prefix.get("stackingSettings") or {}
        trigger = prefix.get("triggerInterval") or {}
        parts = [
            f"life:{prefix.get('lifeTypeRaw')}",
            f"maxTrig:{max_trigger.get('value')}",
            f"stack:{stacking.get('stackingTypeRaw')}",
            f"maxStack:{stacking.get('maxStackCnt')}",
            f"trig:{trigger.get('value')}",
            f"wait:{int(bool(prefix.get('waitFirstTriggerInterval')))}",
        ]
        return ",".join(parts)

    parts = [
        f"life:{prefix.get('lifeTypeRaw')}",
        f"maxTrig:{max_trigger.get('value')}",
        f"immune:{int(bool(prefix.get('ignoreTagImmune')))}",
        f"poise:{prefix.get('poiseModifierCount')}",
    ]
    if "shieldConfigsCount" in prefix:
        parts.append(f"shield:{prefix.get('shieldConfigsCount')}")
    return ",".join(parts)


def read_skill_u8_field(data: bytes, offset: int, field_name: str, *, max_value: int = 255) -> tuple[int, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-u8")
    value = data[offset]
    if value > max_value:
        raise ValueError(f"{field_name}:raw={value}")
    return value, offset + 1


def read_skill_i32_field(data: bytes, offset: int, field_name: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-i32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_skill_bool_field(data: bytes, offset: int, field_name: str) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-bool")
    value = data[offset]
    if value not in (0, 1):
        raise ValueError(f"{field_name}:byte={value}")
    return bool(value), offset + 1


def read_skill_f32_field(data: bytes, offset: int, field_name: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-f32")
    return struct.unpack_from("<f", data, offset)[0], offset + 4


def read_skill_vector2_field(data: bytes, offset: int, field_name: str) -> tuple[dict[str, float], int]:
    if offset + 8 > len(data):
        raise ValueError(f"{field_name}:truncated-vector2")
    x, y = struct.unpack_from("<ff", data, offset)
    return {"x": round(x, 6), "y": round(y, 6)}, offset + 8


def read_skill_clean_string_field(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 128,
) -> tuple[str, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset, max_length=max_length)
    if error:
        raise ValueError(f"{field_name}:{error}")
    value = value or ""
    if not is_clean_skill_identifier_string(value):
        raise ValueError(f"{field_name}:not-clean len={len(value)}")
    return value, offset


def read_skill_string_list_field(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_items: int = 64,
) -> tuple[dict[str, Any], int]:
    start = offset
    count, offset = read_buff_u32_field(data, offset, f"{field_name}Count")
    if count == MEMORYPACK_NULL_COUNT:
        return {"offset": format_offset(start), "count": None, "items": []}, offset
    if count > max_items:
        raise ValueError(f"{field_name}:large-count={count}")
    items: list[str] = []
    for index in range(count):
        value, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
        if error:
            raise ValueError(f"{field_name}[{index}]:{error}")
        value = value or ""
        if not is_clean_skill_identifier_string(value):
            raise ValueError(f"{field_name}[{index}]:not-clean len={len(value)}")
        items.append(value)
    return {"offset": format_offset(start), "count": count, "items": items[:8]}, offset


def read_skill_gameplay_tag_record(data: bytes, offset: int, field_name: str, index: int) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}[{index}]:truncated-member-count")
    member_count = data[offset]
    offset += 1
    tag_id, offset = read_buff_u32_field(data, offset, f"{field_name}[{index}].tagId")
    tag_name, offset, error = read_memorypack_utf8_string(data, offset, max_length=256)
    if error:
        raise ValueError(f"{field_name}[{index}].tagName:{error}")
    tag_name = tag_name or ""
    if tag_name and not is_clean_skill_tag_name(tag_name):
        raise ValueError(f"{field_name}[{index}].tagName:not-clean len={len(tag_name)}")
    return {
        "index": index,
        "memberCount": member_count,
        "tagId": tag_id,
        "tagHash": f"0x{tag_id:08x}",
        "tagName": tag_name,
    }, offset


def read_skill_gameplay_tag_list_field(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_items: int = 128,
) -> tuple[dict[str, Any], int]:
    start = offset
    raw_count, offset_after_u32 = read_buff_u32_field(data, offset, f"{field_name}Count")
    branch = "counted"
    prefix_member_count: int | None = None
    count = raw_count
    body_offset = offset_after_u32
    if raw_count == MEMORYPACK_NULL_COUNT:
        return {
            "offset": format_offset(start),
            "branch": branch,
            "prefixMemberCount": None,
            "count": None,
            "tags": [],
        }, body_offset
    if raw_count > max_items:
        prefix_member_count = data[start]
        if prefix_member_count != 1:
            raise ValueError(f"{field_name}:large-count={raw_count}")
        count, body_offset = read_buff_u32_field(data, start + 1, f"{field_name}.wrappedCount")
        branch = "one-member-wrapper"
    if count > max_items:
        raise ValueError(f"{field_name}:large-count={count}")
    tags: list[dict[str, Any]] = []
    for index in range(count):
        tag, body_offset = read_skill_gameplay_tag_record(data, body_offset, field_name, index)
        tags.append(tag)
    return {
        "offset": format_offset(start),
        "branch": branch,
        "prefixMemberCount": prefix_member_count,
        "count": count,
        "tags": tags[:8],
    }, body_offset


def is_clean_skill_tag_name(value: str) -> bool:
    if not value or len(value) > 180:
        return False
    if any(ord(ch) < 32 or ch == "�" for ch in value):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_./#:+-]+", value))


def is_clean_skill_identifier_string(value: str) -> bool:
    if value == "":
        return True
    if len(value) > 180:
        return False
    if any(ord(ch) < 32 or ch == "�" for ch in value):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_./#:+-]+", value))


def read_skill_hint_shape_data(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError("uiRangeHint.shapeData:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != SKILL_HINT_SHAPE_MEMBER_COUNT:
        raise ValueError(f"uiRangeHint.shapeData.memberCount={member_count}")

    angle, offset = read_skill_f32_field(data, offset, "uiRangeHint.shapeData.angle")
    angle_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.angleKey")
    center_base_is_end_point, offset = read_skill_bool_field(
        data,
        offset,
        "uiRangeHint.shapeData.centerBaseIsEndPoint",
    )
    center_offset, offset = read_skill_vector2_field(data, offset, "uiRangeHint.shapeData.centerOffset")
    center_offset_x_key, offset = read_skill_clean_string_field(
        data,
        offset,
        "uiRangeHint.shapeData.centerOffsetXKey",
    )
    center_offset_z_key, offset = read_skill_clean_string_field(
        data,
        offset,
        "uiRangeHint.shapeData.centerOffsetZKey",
    )
    extent, offset = read_skill_vector2_field(data, offset, "uiRangeHint.shapeData.extent")
    extent_x_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.extentXKey")
    extent_z_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.extentZKey")
    fixed_extent, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.fixedExtent")
    radius, offset = read_skill_f32_field(data, offset, "uiRangeHint.shapeData.radius")
    radius_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.radiusKey")
    restrict_end_point_in_range, offset = read_skill_bool_field(
        data,
        offset,
        "uiRangeHint.shapeData.restrictEndPointInRange",
    )
    shape, offset = read_skill_i32_field(data, offset, "uiRangeHint.shapeData.shape")
    if shape < 0 or shape > 16:
        raise ValueError(f"uiRangeHint.shapeData.shape={shape}")
    use_angle_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useAngleKey")
    use_center_offset_key, offset = read_skill_bool_field(
        data,
        offset,
        "uiRangeHint.shapeData.useCenterOffsetKey",
    )
    use_extent_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useExtentKey")
    use_radius_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useRadiusKey")
    use_width_key, offset = read_skill_bool_field(data, offset, "uiRangeHint.shapeData.useWidthKey")
    width, offset = read_skill_f32_field(data, offset, "uiRangeHint.shapeData.width")
    width_key, offset = read_skill_clean_string_field(data, offset, "uiRangeHint.shapeData.widthKey")

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "byteLength": offset - start,
        "angle": round(angle, 6),
        "angleKey": angle_key,
        "centerBaseIsEndPoint": center_base_is_end_point,
        "centerOffset": center_offset,
        "centerOffsetXKey": center_offset_x_key,
        "centerOffsetZKey": center_offset_z_key,
        "extent": extent,
        "extentXKey": extent_x_key,
        "extentZKey": extent_z_key,
        "fixedExtent": fixed_extent,
        "radius": round(radius, 6),
        "radiusKey": radius_key,
        "restrictEndPointInRange": restrict_end_point_in_range,
        "shapeRaw": shape,
        "shapeName": SKILL_HINT_SHAPE_NAMES.get(shape, f"shape_{shape}"),
        "useAngleKey": use_angle_key,
        "useCenterOffsetKey": use_center_offset_key,
        "useExtentKey": use_extent_key,
        "useRadiusKey": use_radius_key,
        "useWidthKey": use_width_key,
        "width": round(width, 6),
        "widthKey": width_key,
    }, offset


def read_skill_ui_range_hint_data(
    data: bytes,
    offset: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"uiRangeHints[{index}]:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != SKILL_UI_RANGE_HINT_MEMBER_COUNT:
        raise ValueError(f"uiRangeHints[{index}].memberCount={member_count}")
    select_all, offset = read_skill_bool_field(data, offset, f"uiRangeHints[{index}].selectAll")
    shape_data, offset = read_skill_hint_shape_data(data, offset)
    target_faction, offset = read_skill_i32_field(data, offset, f"uiRangeHints[{index}].targetFaction")
    if target_faction < 0 or target_faction > 16:
        raise ValueError(f"uiRangeHints[{index}].targetFaction={target_faction}")
    return {
        "index": index,
        "offset": format_offset(start),
        "memberCount": member_count,
        "byteLength": offset - start,
        "selectAll": select_all,
        "shapeData": shape_data,
        "targetFactionRaw": target_faction,
    }, offset


SKILL_POST_ID_PARSED_STATUSES = {"parsed-through-smartTargetTagQuery", "parsed-through-smartTargetPayload"}


SKILL_COMPARE_TYPE_NAMES = {
    0: "LT",
    1: "LE",
    2: "GT",
    3: "GE",
    4: "Equals",
}


def read_skill_assign_pair_data(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 6:
        raise ValueError(f"{field_name}:member-count={member_count}")

    direct_value_type, offset = read_buff_u32_field(data, offset, f"{field_name}.directValueType")
    input_value_key, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{field_name}.inputValueKey",
        max_length=256,
    )
    numeric_value, offset = read_skill_f32_field(data, offset, f"{field_name}.numericValue")
    string_value, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{field_name}.stringValue",
        max_length=256,
    )
    target_key, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{field_name}.targetKey",
        max_length=256,
    )
    use_direct_value, offset = read_skill_bool_field(data, offset, f"{field_name}.useDirectValue")

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "directValueTypeRaw": direct_value_type,
        "inputValueKey": input_value_key,
        "numericValue": round(numeric_value, 6),
        "stringValue": string_value,
        "targetKey": target_key,
        "useDirectValue": use_direct_value,
        "byteLength": offset - start,
    }, offset


def read_skill_buff_input_data(
    data: bytes,
    offset: int,
    index: int,
    field_name: str = "toggleBuffs.buffs",
) -> tuple[dict[str, Any], int]:
    item_name = f"{field_name}[{index}]"
    start = offset
    if offset >= len(data):
        raise ValueError(f"{item_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 3:
        raise ValueError(f"{item_name}:member-count={member_count}")

    assign_blackboard, offset = read_skill_bool_field(
        data,
        offset,
        f"{item_name}.assignBlackboard",
    )
    assign_items_count, offset = read_buff_u32_field(
        data,
        offset,
        f"{item_name}.assignItemsCount",
    )
    if assign_items_count > 32:
        raise ValueError(f"{item_name}.assignItemsCount:large-count={assign_items_count}")

    assign_items: list[dict[str, Any]] = []
    for item_index in range(assign_items_count):
        assign_item, offset = read_skill_assign_pair_data(
            data,
            offset,
            f"{item_name}.assignItems[{item_index}]",
        )
        assign_items.append(assign_item)

    buff_id, offset = read_skill_clean_string_field(
        data,
        offset,
        f"{item_name}.buffId",
        max_length=256,
    )
    if not buff_id.startswith("buff_"):
        raise ValueError(f"{item_name}.buffId:unexpected={buff_id!r}")

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "assignBlackboard": assign_blackboard,
        "assignItemsCount": assign_items_count,
        "assignItems": assign_items[:8],
        "buffId": buff_id,
        "byteLength": offset - start,
    }, offset


def read_skill_toggle_condition_data(
    data: bytes,
    offset: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    condition_kind, offset = read_skill_u8_field(
        data,
        offset,
        f"toggleBuffs.conditions[{index}].kind",
        max_value=16,
    )
    if condition_kind != 1:
        raise ValueError(f"toggleBuffs.conditions[{index}].kind={condition_kind}")
    member_count, offset = read_skill_u8_field(
        data,
        offset,
        f"toggleBuffs.conditions[{index}].memberCount",
        max_value=16,
    )
    if member_count != 2:
        raise ValueError(f"toggleBuffs.conditions[{index}].member-count={member_count}")

    compare_raw, offset = read_buff_u32_field(data, offset, f"toggleBuffs.conditions[{index}].compare")
    if compare_raw > 16:
        raise ValueError(f"toggleBuffs.conditions[{index}].compare:raw={compare_raw}")
    value, offset = read_buff_blackboard_float_field(
        data,
        offset,
        f"toggleBuffs.conditions[{index}].value",
    )

    return {
        "offset": format_offset(start),
        "kindRaw": condition_kind,
        "kindName": "compareBlackboardValue",
        "memberCount": member_count,
        "compareRaw": compare_raw,
        "compareName": SKILL_COMPARE_TYPE_NAMES.get(compare_raw, f"compare_{compare_raw}"),
        "value": value,
        "byteLength": offset - start,
    }, offset


def read_skill_toggle_buff_data(
    data: bytes,
    offset: int,
    index: int,
) -> tuple[dict[str, Any], int]:
    start = offset
    if offset >= len(data):
        raise ValueError(f"toggleBuffs[{index}]:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 2:
        raise ValueError(f"toggleBuffs[{index}]:member-count={member_count}")

    buffs_count, offset = read_buff_u32_field(data, offset, f"toggleBuffs[{index}].buffsCount")
    if buffs_count > 32:
        raise ValueError(f"toggleBuffs[{index}].buffsCount:large-count={buffs_count}")
    buffs: list[dict[str, Any]] = []
    for buff_index in range(buffs_count):
        buff, offset = read_skill_buff_input_data(data, offset, buff_index)
        buffs.append(buff)

    conditions_count, offset = read_buff_u32_field(data, offset, f"toggleBuffs[{index}].conditionsCount")
    if conditions_count > 32:
        raise ValueError(f"toggleBuffs[{index}].conditionsCount:large-count={conditions_count}")
    conditions: list[dict[str, Any]] = []
    for condition_index in range(conditions_count):
        condition, offset = read_skill_toggle_condition_data(data, offset, condition_index)
        conditions.append(condition)

    return {
        "offset": format_offset(start),
        "memberCount": member_count,
        "metadataFieldOrder": ["buffs", "conditions"],
        "buffsCount": buffs_count,
        "buffs": buffs[:8],
        "conditionsCount": conditions_count,
        "conditions": conditions[:8],
        "byteLength": offset - start,
    }, offset


def scan_skill_tag_record_hits(
    data: bytes,
    start: int,
    end: int,
    *,
    max_records: int = 12,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    limit = max(start, min(end, len(data)) - 8)
    for offset in range(max(start, 0), limit):
        member_count = data[offset]
        if member_count not in (1, 2, 3, 4):
            continue
        if offset + 9 > end:
            continue
        tag_id = struct.unpack_from("<I", data, offset + 1)[0]
        tag_name, tag_end, error = read_memorypack_utf8_string(data, offset + 5, max_length=256)
        if error:
            continue
        tag_name = tag_name or ""
        if not tag_name.startswith("Skill/") or not is_clean_skill_tag_name(tag_name):
            continue
        records.append({
            "offset": format_offset(offset),
            "memberCount": member_count,
            "tagId": tag_id,
            "tagHash": f"0x{tag_id:08x}",
            "tagName": tag_name,
            "byteLength": tag_end - offset,
        })
        if len(records) >= max_records:
            break
    return records


def read_skill_switch_to_buff_config_data(
    data: bytes,
    switch_offset: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    offset = switch_offset
    if offset >= len(data):
        raise ValueError("switchToBuffConfig:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 5:
        raise ValueError(f"switchToBuffConfig:member-count={member_count}")
    as_skill_cast, offset = read_skill_bool_field(data, offset, "switchToBuffConfig.asSkillCast")
    buffs_count, offset = read_buff_u32_field(data, offset, "switchToBuffConfig.buffsCount")
    if buffs_count > 256:
        raise ValueError(f"switchToBuffConfig.buffsCount:large-count={buffs_count}")

    buffs: list[dict[str, Any]] = []
    for buff_index in range(buffs_count):
        buff, offset = read_skill_buff_input_data(
            data,
            offset,
            buff_index,
            "switchToBuffConfig.buffs",
        )
        buffs.append(buff)

    suffix_offset = offset
    default_length = SKILL_DEFAULT_SWITCH_TO_BUFF_CONFIG_BYTE_LENGTH
    default_end = switch_offset + default_length
    post_switch_tail = decode_skill_post_switch_tail_at(data, default_end, default_length, "default-fixed")
    body_end = default_end
    boundary_status = "default-fixed"

    if default_end < suffix_offset or post_switch_tail.get("status") != "parsed-through-exact-tail":
        scan_start = max(suffix_offset, switch_offset + 6)
        scan_end = min(len(data), suffix_offset + 4096)
        found_tail: dict[str, Any] | None = None
        found_end = -1
        for candidate_end in range(scan_start, scan_end):
            if data[candidate_end] not in (0, 1):
                continue
            candidate_length = candidate_end - switch_offset
            candidate_tail = decode_skill_post_switch_tail_at(
                data,
                candidate_end,
                candidate_length,
                "validated-post-tail-scan",
            )
            if candidate_tail.get("status") == "parsed-through-exact-tail":
                found_tail = candidate_tail
                found_end = candidate_end
                break
        if found_tail is not None:
            body_end = found_end
            post_switch_tail = found_tail
            boundary_status = "validated-post-tail-scan"
        else:
            body_end = max(default_end, suffix_offset)
            boundary_status = "default-fixed-parse-error"

    suffix_length = max(0, body_end - suffix_offset)
    suffix_bytes = data[suffix_offset:body_end]
    switch_config = {
        "memberCount": member_count,
        "asSkillCast": as_skill_cast,
        "asSkillCastRaw": int(as_skill_cast),
        "buffsCount": buffs_count,
        "buffs": buffs[:8],
        "fieldOrder": ["asSkillCast", "buffs", "buffSource", "condition", "targets"],
        "defaultByteLength": default_length,
        "bodyByteLength": max(0, body_end - switch_offset),
        "boundaryStatus": boundary_status,
        "remainingSwitchSuffixByteLength": suffix_length,
        "remainingSwitchSuffixFieldOrder": ["buffSource", "condition", "targets"],
        "remainingSwitchSuffixPrefixHex": suffix_bytes[:96].hex(" "),
        "remainingSwitchSuffixStringHits": scan_length_prefixed_utf8_string_hits(
            suffix_bytes,
            max_samples=12,
            max_length=120,
        ),
    }
    if post_switch_tail.get("status") != "parsed-through-exact-tail":
        switch_config["boundaryError"] = post_switch_tail.get("error")
    return switch_config, post_switch_tail


def decode_skill_post_switch_tail_at(
    data: bytes,
    switch_end: int,
    switch_config_byte_length: int,
    boundary_status: str,
) -> dict[str, Any]:
    offset = switch_end
    try:
        if switch_end > len(data):
            raise ValueError("switch-config-boundary:truncated")
        switch_to_center, offset = read_skill_bool_field(
            data,
            offset,
            "switchToCenterBeforeCast",
        )
        tag_during_attach, offset = read_skill_gameplay_tag_list_field(
            data,
            offset,
            "tagDuringAttach",
        )
        toggle_buffs_count, offset = read_buff_u32_field(data, offset, "toggleBuffsCount")
        if toggle_buffs_count > 256:
            raise ValueError(f"toggleBuffsCount:large-count={toggle_buffs_count}")

        result: dict[str, Any] = {
            "status": "parsed-through-toggleBuffsCount",
            "source": (
                "validated SwitchToBuffConfig boundary plus final SkillData tail fields; "
                "UIRangeHintData and toggleBuffs branches require exact file-end handoff"
            ),
            "offset": format_offset(switch_end),
            "switchToBuffConfigByteLength": switch_config_byte_length,
            "switchToBuffConfigBoundaryStatus": boundary_status,
            "switchToCenterBeforeCast": switch_to_center,
            "tagDuringAttach": tag_during_attach,
            "toggleBuffsCount": toggle_buffs_count,
            "endOffset": format_offset(offset),
        }
        toggle_buffs: list[dict[str, Any]] = []
        for index in range(toggle_buffs_count):
            toggle_buff, offset = read_skill_toggle_buff_data(data, offset, index)
            toggle_buffs.append(toggle_buff)
        if toggle_buffs:
            result["toggleBuffs"] = toggle_buffs[:8]

        ui_range_hints_count, offset = read_buff_u32_field(data, offset, "uiRangeHintsCount")
        if ui_range_hints_count > 32:
            raise ValueError(f"uiRangeHintsCount:large-count={ui_range_hints_count}")
        ui_range_hints: list[dict[str, Any]] = []
        for index in range(ui_range_hints_count):
            hint, offset = read_skill_ui_range_hint_data(data, offset, index)
            ui_range_hints.append(hint)
        result["status"] = "parsed-through-exact-tail"
        result["uiRangeHintsCount"] = ui_range_hints_count
        result["uiRangeHints"] = ui_range_hints[:8]
        result["endOffset"] = format_offset(offset)
        result["exactLength"] = offset == len(data)
        if offset != len(data):
            raise ValueError(f"tail-not-exact={format_offset(offset)}")
        return result
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        return {
            "status": "parse-error",
            "offset": format_offset(offset),
            "switchToBuffConfigByteLength": switch_config_byte_length,
            "switchToBuffConfigBoundaryStatus": boundary_status,
            "error": str(exc),
        }


def decode_skill_post_switch_tail_fields(data: bytes, switch_offset: int) -> dict[str, Any]:
    switch_end = switch_offset + SKILL_DEFAULT_SWITCH_TO_BUFF_CONFIG_BYTE_LENGTH
    return decode_skill_post_switch_tail_at(
        data,
        switch_end,
        SKILL_DEFAULT_SWITCH_TO_BUFF_CONFIG_BYTE_LENGTH,
        "default-fixed",
    )


def decode_skill_switch_tail_probe(data: bytes, offset: int) -> dict[str, Any]:
    tail = data[offset:]
    if not tail:
        return {
            "status": "empty-tail",
            "offset": format_offset(offset),
            "tailByteLength": 0,
        }

    scan_limit = min(len(tail), 512)
    marker_rel: int | None = None
    as_skill_cast = 0
    buffs_count = 0
    for rel in range(scan_limit):
        if tail[rel] != 5 or rel + 6 > len(tail):
            continue
        maybe_as_skill_cast = tail[rel + 1]
        if maybe_as_skill_cast not in (0, 1):
            continue
        maybe_buffs_count = struct.unpack_from("<I", tail, rel + 2)[0]
        if maybe_buffs_count > 256:
            continue
        marker_rel = rel
        as_skill_cast = maybe_as_skill_cast
        buffs_count = maybe_buffs_count
        break

    if marker_rel is None:
        return {
            "status": "switch-marker-not-found",
            "offset": format_offset(offset),
            "tailByteLength": len(tail),
            "tailPrefixHex": tail[:48].hex(" "),
            "stringHits": scan_length_prefixed_utf8_string_hits(tail, max_samples=8, max_length=120),
        }

    pre_switch = tail[:marker_rel]
    switch_offset = offset + marker_rel
    switch_tail = tail[marker_rel:]
    try:
        switch_to_buff_config, post_switch_tail = read_skill_switch_to_buff_config_data(data, switch_offset)
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        switch_to_buff_config = {
            "memberCount": 5,
            "asSkillCast": bool(as_skill_cast),
            "asSkillCastRaw": as_skill_cast,
            "buffsCount": buffs_count,
            "fieldOrder": ["asSkillCast", "buffs", "buffSource", "condition", "targets"],
            "defaultByteLength": SKILL_DEFAULT_SWITCH_TO_BUFF_CONFIG_BYTE_LENGTH,
            "boundaryStatus": "parse-error",
            "boundaryError": str(exc),
        }
        post_switch_tail = decode_skill_post_switch_tail_fields(data, switch_offset)
    return {
        "status": "switch-marker-found",
        "source": (
            "SwitchToBuffConfig marker uses local IL2CPP MemoryPack schema "
            "(member count 5; generated fields asSkillCast, buffs, buffSource, condition, targets)"
        ),
        "offset": format_offset(switch_offset),
        "tailByteLength": len(tail),
        "preSwitchByteLength": marker_rel,
        "preSwitchPrefixHex": pre_switch[:48].hex(" "),
        "preSwitchStringHits": scan_length_prefixed_utf8_string_hits(
            pre_switch,
            max_samples=8,
            max_length=120,
        ),
        "preSwitchTagRecords": scan_skill_tag_record_hits(
            data,
            offset,
            switch_offset,
            max_records=8,
        ),
        "switchToBuffConfig": switch_to_buff_config,
        "postSwitchTail": post_switch_tail,
        "unparsedFromSwitchByteLength": len(switch_tail),
        "switchPrefixHex": switch_tail[:64].hex(" "),
        "switchStringHits": scan_length_prefixed_utf8_string_hits(
            switch_tail,
            max_samples=12,
            max_length=120,
        ),
    }


def decode_skill_post_id_tail_prefix_at(
    data: bytes,
    id_value: str,
    id_marker_offset: int,
) -> dict[str, Any]:
    start = id_marker_offset + 4 + len(id_value.encode("utf-8"))
    offset = start
    skill_name = ""
    skill_specification: int | None = None
    skill_tags: dict[str, Any] | None = None
    smart_target_buff_find_settings: int | None = None
    smart_target_buff_ids: dict[str, Any] | None = None
    smart_target_select_strategy: int | None = None
    smart_target_tag_query: int | None = None
    try:
        skill_name_value, offset, error = read_memorypack_utf8_string(data, offset, max_length=512)
        if error:
            raise ValueError(f"skillName:{error}")
        skill_name = skill_name_value or ""
        skill_specification, offset = read_skill_i32_field(data, offset, "skillSpecification")
        skill_tags, offset = read_skill_gameplay_tag_list_field(data, offset, "skillTags")
        smart_target_buff_find_settings, offset = read_skill_u8_field(
            data,
            offset,
            "smartTargetBuffFindSettings",
            max_value=32,
        )
        smart_target_buff_ids, offset = read_skill_string_list_field(data, offset, "smartTargetBuffIds")
        smart_target_select_strategy, offset = read_skill_u8_field(
            data,
            offset,
            "smartTargetSelectStrategy",
            max_value=32,
        )
        smart_target_tag_query, offset = read_skill_u8_field(
            data,
            offset,
            "smartTargetTagQuery",
            max_value=32,
        )
        switch_tail_probe = decode_skill_switch_tail_probe(data, offset)
        return {
            "status": "parsed-through-smartTargetTagQuery",
            "source": (
                "anchored after candidate exact skillId marker; parses clean post-id scalar/list prefix "
                "and probes the following SwitchToBuffConfig tail marker"
            ),
            "idMarkerOffset": format_offset(id_marker_offset),
            "offset": format_offset(start),
            "skillName": skill_name,
            "skillSpecificationRaw": skill_specification,
            "skillTags": skill_tags,
            "smartTargetBuffFindSettingsRaw": smart_target_buff_find_settings,
            "smartTargetBuffIds": smart_target_buff_ids,
            "smartTargetSelectStrategyRaw": smart_target_select_strategy,
            "smartTargetTagQueryRaw": smart_target_tag_query,
            "switchTailProbe": switch_tail_probe,
            "endOffset": format_offset(offset),
        }
    except (struct.error, UnicodeDecodeError, ValueError) as exc:
        fallback_probe = decode_skill_switch_tail_probe(data, offset)
        fallback_tail = fallback_probe.get("postSwitchTail") or {}
        if (
            fallback_probe.get("status") == "switch-marker-found"
            and fallback_tail.get("status") == "parsed-through-exact-tail"
            and fallback_tail.get("exactLength") is True
        ):
            payload_start = offset
            payload_length = fallback_probe.get("preSwitchByteLength")
            result: dict[str, Any] = {
                "status": "parsed-through-smartTargetPayload",
                "source": (
                    "post-id scalar prefix hit a non-simple smart-target/tag-query payload; "
                    "the payload is preserved with string/tag diagnostics and validated by exact SwitchToBuffConfig handoff"
                ),
                "idMarkerOffset": format_offset(id_marker_offset),
                "offset": format_offset(start),
                "skillName": skill_name,
                "skillSpecificationRaw": skill_specification,
                "skillTags": skill_tags,
                "smartTargetBuffFindSettingsRaw": smart_target_buff_find_settings,
                "smartTargetBuffIds": smart_target_buff_ids,
                "smartTargetSelectStrategyRaw": smart_target_select_strategy,
                "smartTargetTagQueryRaw": smart_target_tag_query,
                "smartTargetParseError": str(exc),
                "smartTargetPayload": {
                    "status": "validated-by-switch-tail",
                    "offset": format_offset(payload_start),
                    "byteLength": payload_length,
                    "stringHits": fallback_probe.get("preSwitchStringHits") or [],
                    "tagRecords": fallback_probe.get("preSwitchTagRecords") or [],
                    "prefixHex": fallback_probe.get("preSwitchPrefixHex"),
                    "layoutNote": (
                        "Payload bytes occur between the simple smart-target fields and SwitchToBuffConfig. "
                        "Observed records use GameplayTag-like memberCount/tagId/string triples and/or buff-id strings."
                    ),
                },
                "switchTailProbe": fallback_probe,
                "endOffset": format_offset(payload_start),
            }
            return result
        return {
            "status": "parse-error",
            "idMarkerOffset": format_offset(id_marker_offset),
            "offset": format_offset(offset),
            "error": str(exc),
        }


def is_skill_top_level_post_id_tail_candidate(candidate: dict[str, Any]) -> bool:
    if candidate.get("status") not in SKILL_POST_ID_PARSED_STATUSES:
        return False
    skill_tags = candidate.get("skillTags") or {}
    if skill_tags.get("count") != 1:
        return False
    switch_tail = candidate.get("switchTailProbe") or {}
    post_switch_tail = switch_tail.get("postSwitchTail") or {}
    return (
        switch_tail.get("status") == "switch-marker-found"
        and post_switch_tail.get("status") == "parsed-through-exact-tail"
        and post_switch_tail.get("exactLength") is True
    )


def summarize_skill_post_id_tail_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    skill_tags = candidate.get("skillTags") or {}
    smart_target_buff_ids = candidate.get("smartTargetBuffIds") or {}
    switch_tail = candidate.get("switchTailProbe") or {}
    post_switch_tail = switch_tail.get("postSwitchTail") or {}
    return {
        "idMarkerOffset": candidate.get("idMarkerOffset"),
        "status": candidate.get("status"),
        "offset": candidate.get("offset"),
        "error": candidate.get("error"),
        "skillTagsCount": skill_tags.get("count"),
        "smartTargetBuffIdsCount": smart_target_buff_ids.get("count"),
        "smartTargetTagQueryRaw": candidate.get("smartTargetTagQueryRaw"),
        "switchTailStatus": switch_tail.get("status"),
        "postSwitchStatus": post_switch_tail.get("status"),
        "postSwitchExactLength": post_switch_tail.get("exactLength"),
    }


def decode_skill_post_id_tail_prefix(
    data: bytes,
    id_value: str,
    id_marker_count: int,
    id_marker_offsets: list[int],
) -> dict[str, Any]:
    if not id_value or not id_marker_offsets:
        return {"status": "missing-id-marker"}

    candidates = [
        decode_skill_post_id_tail_prefix_at(data, id_value, marker_offset)
        for marker_offset in id_marker_offsets
    ]
    if id_marker_count == 1:
        return candidates[0]

    structural_candidates = [candidate for candidate in candidates if is_skill_top_level_post_id_tail_candidate(candidate)]
    simple_candidates = [
        candidate
        for candidate in structural_candidates
        if candidate.get("status") == "parsed-through-smartTargetTagQuery"
    ]
    selected = simple_candidates if len(simple_candidates) == 1 else structural_candidates
    if len(selected) == 1:
        result = selected[0]
        result["source"] = (
            "selected exact top-level skillId marker among multiple length-prefixed id references; "
            "embedded id-string references were rejected by post-id and exact-tail structure"
        )
        result["anchorSelection"] = {
            "status": "selected-from-ambiguous-id-markers",
            "idMarkerCount": id_marker_count,
            "candidateCount": len(candidates),
            "selectedIdMarkerOffset": result.get("idMarkerOffset"),
            "selectionCriteria": (
                "post-id prefix parsed, skillTags.count == 1, SwitchToBuffConfig marker found, "
                "and post-switch tail reached exact EOF"
            ),
            "candidateSummaries": [summarize_skill_post_id_tail_candidate(candidate) for candidate in candidates[:12]],
        }
        return result

    return {
        "status": "ambiguous-id-marker",
        "idMarkerCount": id_marker_count,
        "candidateCount": len(candidates),
        "idMarkerOffsets": [format_offset(offset) for offset in id_marker_offsets],
        "selectionCriteria": (
            "post-id prefix parsed, skillTags.count == 1, SwitchToBuffConfig marker found, "
            "and post-switch tail reached exact EOF"
        ),
        "selectedCandidateCount": len(selected),
        "structuralCandidateCount": len(structural_candidates),
        "simpleCandidateCount": len(simple_candidates),
        "candidateSummaries": [summarize_skill_post_id_tail_candidate(candidate) for candidate in candidates[:12]],
    }


def skill_post_id_tail_sample(prefix: dict[str, Any]) -> str:
    if prefix.get("status") not in SKILL_POST_ID_PARSED_STATUSES:
        return ""
    tags = prefix.get("skillTags") or {}
    smart_target_buff_ids = prefix.get("smartTargetBuffIds") or {}
    parts = [
        f"spec:{prefix.get('skillSpecificationRaw')}",
        f"tags:{tags.get('count')}",
    ]
    anchor_selection = prefix.get("anchorSelection") or {}
    if anchor_selection.get("status") == "selected-from-ambiguous-id-markers":
        parts.append("anchor:selected-from-ambiguous-id-markers")
        parts.append(f"anchorOffset:{anchor_selection.get('selectedIdMarkerOffset')}")
    if tags.get("branch") == "one-member-wrapper":
        parts.append("tagMode:wrap")
    clean_tags = [
        str(tag.get("tagName") or "")
        for tag in tags.get("tags") or []
        if is_clean_skill_tag_name(str(tag.get("tagName") or ""))
    ]
    if clean_tags:
        parts.append("tag:" + clean_tags[0][:80])
    smart_payload = prefix.get("smartTargetPayload") or {}
    if smart_payload:
        parts.append(f"smartPayload:{smart_payload.get('byteLength')}")
        tag_records = smart_payload.get("tagRecords") or []
        if tag_records:
            parts.append(f"smartTags:{len(tag_records)}")
    parts.extend([
        f"find:{prefix.get('smartTargetBuffFindSettingsRaw')}",
        f"buffIds:{smart_target_buff_ids.get('count')}",
        f"select:{prefix.get('smartTargetSelectStrategyRaw')}",
        f"query:{prefix.get('smartTargetTagQueryRaw')}",
    ])
    switch_tail = prefix.get("switchTailProbe") or {}
    if switch_tail.get("status") == "switch-marker-found":
        switch_config = switch_tail.get("switchToBuffConfig") or {}
        parts.append(f"switchRel:{switch_tail.get('preSwitchByteLength')}")
        parts.append(f"switchBuffs:{switch_config.get('buffsCount')}")
        post_switch_tail = switch_tail.get("postSwitchTail") or {}
        if post_switch_tail:
            parts.append(f"center:{int(bool(post_switch_tail.get('switchToCenterBeforeCast')))}")
            tag_attach = post_switch_tail.get("tagDuringAttach") or {}
            parts.append(f"attach:{tag_attach.get('count')}")
            if "toggleBuffsCount" in post_switch_tail:
                parts.append(f"toggle:{post_switch_tail.get('toggleBuffsCount')}")
            if "uiRangeHintsCount" in post_switch_tail:
                parts.append(f"ui:{post_switch_tail.get('uiRangeHintsCount')}")
            if post_switch_tail.get("status") == "parsed-through-exact-tail":
                parts.append("tailExact")
            elif post_switch_tail.get("status") == "parse-error":
                parts.append("tailErr")
        parts.append(f"tail:{switch_tail.get('tailByteLength')}")
    elif switch_tail:
        parts.append(f"switch:{switch_tail.get('status')}")
    return ",".join(parts)


def read_memorypack_tag_list_prefix(
    data: bytes,
    offset: int,
    *,
    max_items: int = 32,
) -> tuple[list[dict[str, Any]], int | None, int, str | None]:
    if offset + 4 > len(data):
        return [], None, offset, "truncated-count"
    raw_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if raw_count == MEMORYPACK_NULL_COUNT:
        return [], None, offset, None
    if raw_count > max_items:
        return [], raw_count, offset, f"large-count={raw_count}"

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


def decode_lipsync_memorypack(data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != LIPSYNC_MEMBER_COUNT:
        return None

    offset = 1
    fields: list[dict[str, Any]] = []
    total_records = 0
    exact = True
    for index in range(1, LIPSYNC_MEMBER_COUNT + 1):
        if offset + 4 > len(data):
            exact = False
            fields.append({"index": index, "status": "truncated", "offset": format_offset(offset)})
            break

        raw_count = struct.unpack_from("<I", data, offset)[0]
        field_name = MEMORYPACK_FIELD_SCHEMAS["LipSync"][index - 1]
        field: dict[str, Any] = {"index": index, "name": field_name, "offset": format_offset(offset)}
        offset += 4
        if raw_count == MEMORYPACK_NULL_COUNT:
            field.update({"status": "null", "count": None})
            fields.append(field)
            continue

        if raw_count > 250_000:
            exact = False
            field.update({"status": "invalid-count", "count": raw_count})
            fields.append(field)
            break

        dims: Counter[int] = Counter()
        first_record: list[float] = []
        valid = True
        for record_index in range(raw_count):
            if offset + 4 > len(data):
                valid = False
                break
            dimension = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            if dimension > LIPSYNC_RECORD_DIMENSION_LIMIT or offset + dimension * 4 > len(data):
                valid = False
                break
            dims[dimension] += 1
            if record_index == 0:
                first_record = [
                    round(struct.unpack_from("<f", data, offset + item * 4)[0], 4)
                    for item in range(min(dimension, 6))
                ]
            offset += dimension * 4

        total_records += raw_count
        field.update({
            "status": "present" if valid else "truncated",
            "count": raw_count,
            "dimensions": {str(key): value for key, value in sorted(dims.items())},
        })
        if first_record:
            field["first"] = first_record
        fields.append(field)
        if not valid:
            exact = False
            break

    if offset != size:
        exact = False

    counts = [field.get("count") for field in fields if field.get("status") in {"present", "null"}]
    present = sum(1 for field in fields if field.get("status") == "present")
    nulls = sum(1 for field in fields if field.get("status") == "null")
    dimensions: Counter[int] = Counter()
    for field in fields:
        for key, value in (field.get("dimensions") or {}).items():
            try:
                dimensions[int(key)] += int(value)
            except (TypeError, ValueError):
                pass

    return {
        "kind": "memorypack-json",
        "subtype": "LipSync",
        "summary": (
            f"MemoryPack LipSync curves; {present} present lists, {nulls} null lists, "
            f"{total_records} records"
            + ("; decoded exact length" if exact else "; partial decode")
        ),
        "rows": total_records,
        "keys": MEMORYPACK_FIELD_SCHEMAS["LipSync"],
        "sample": (
            f"memberCount=15; counts {summarize_member_counts(counts)}; "
            f"dimensions {', '.join(f'{key}={value}' for key, value in dimensions.most_common(3))}"
        ),
        "decoded": {
            "memberCount": LIPSYNC_MEMBER_COUNT,
            "exact": exact,
            "presentLists": present,
            "nullLists": nulls,
            "totalRecords": total_records,
            "fields": fields,
        },
    }


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

    born_tags, born_tag_count, offset, tag_error = read_memorypack_tag_list_prefix(data, offset)
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
                        if second_component_tag in (0x108, 0x10A) and second_component_member_count == 4:
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
            "MemoryPack InteractiveTemplateData; 25 inherited template members; "
            "component prefix, next payload tag, and selected component bodies decoded from bytes"
        ),
        "rows": component_count,
        "keys": MEMORYPACK_FIELD_SCHEMAS["InteractiveTemplateData"],
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": INTERACTIVE_TEMPLATE_MEMBER_COUNT,
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
            "componentCommonPerformData": common_perform_component,
            "componentCommonPerformComponents": common_perform_components,
            "componentLogicControllerData": logic_controller_component,
            "componentLogicControllerComponents": logic_controller_components,
            "componentHittableData": hittable_component,
            "componentHittableComponents": hittable_components,
            "componentAudioData": audio_component,
            "componentAudioComponents": audio_components,
            "componentShowGuideData": show_guide_component,
            "componentShowGuideComponents": show_guide_components,
            "componentStringSamples": component_string_samples,
            "componentUnionSource": BASE_COMPONENT_UNION_SOURCE_NOTE if first_component_type else "",
            "componentParseError": component_error or "",
            "exactLength": False,
        },
    }


def read_memorypack_gameplay_tag_tail(data: bytes, *, max_scan_bytes: int = 512) -> dict[str, Any] | None:
    scan_start = max(0, len(data) - max_scan_bytes)
    for pos in range(scan_start, max(scan_start, len(data) - 8)):
        if data[pos] != 2:
            continue
        if pos + 9 > len(data):
            continue
        hash_value = struct.unpack_from("<I", data, pos + 1)[0]
        length = struct.unpack_from("<I", data, pos + 5)[0]
        text_start = pos + 9
        text_end = text_start + length
        if length <= 0 or length > 512 or text_end != len(data):
            continue
        raw = data[text_start:text_end]
        try:
            tag = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in tag) or "/" not in tag:
            continue
        parts = [part for part in tag.split("/") if part]
        return {
            "offset": pos,
            "hash": hash_value,
            "hashHex": f"0x{hash_value:08x}",
            "tag": tag,
            "parts": parts,
            "depth": len(parts),
        }
    return None


def classify_npc_montage_tag(parts: list[str]) -> dict[str, str]:
    if len(parts) < 3:
        return {"domain": "", "category": "", "form": "", "body": "", "role": "", "action": ""}
    domain = "/".join(parts[:3])
    category = parts[2] if len(parts) > 2 else ""
    action = parts[-1] if parts else ""
    if category == "Generic":
        return {
            "domain": domain,
            "category": category,
            "form": "",
            "body": parts[3] if len(parts) > 3 else "",
            "role": "",
            "action": action,
        }
    return {
        "domain": domain,
        "category": category,
        "form": parts[3] if len(parts) > 3 else "",
        "body": parts[4] if len(parts) > 4 else "",
        "role": parts[5] if len(parts) > 5 else "",
        "action": action,
    }


def decode_npc_montage_json_memorypack(rel: str, path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    parts = rel.split("/")
    if not (len(parts) >= 4 and parts[0] == "Json" and parts[1] == "NPC" and parts[2] == "MontageJson"):
        return None
    if not data or data[0] != NPC_MONTAGE_ROOT_MEMBER_COUNT or len(data) < 10:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("NPCMontageJson")
    if not schema:
        return None

    try:
        anim_type = struct.unpack_from("<i", data, 1)[0]
        data_member_count = data[5]
    except struct.error:
        return None
    if data_member_count != NPC_MONTAGE_DATA_MEMBER_COUNT:
        return None
    tag_tail = read_memorypack_gameplay_tag_tail(data)
    if not tag_tail:
        return None

    tag = str(tag_tail["tag"])
    tag_parts = list(tag_tail.get("parts") or [])
    tag_info = classify_npc_montage_tag(tag_parts)
    tag_offset = int(tag_tail["offset"])
    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=64, max_length=260)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 32)
    extra_strings = unique_strings([value for value in strings if value != tag], 12)
    source_folder = "/".join(parts[3:-1])

    details = [
        f"animType={anim_type}",
        f"dataMembers={data_member_count}",
        f"tag={tag}",
    ]
    if tag_info.get("category"):
        details.append("category=" + tag_info["category"])
    if tag_info.get("form"):
        details.append("form=" + tag_info["form"])
    if tag_info.get("body"):
        details.append("body=" + tag_info["body"])
    if tag_info.get("role"):
        details.append("role=" + tag_info["role"])
    if tag_info.get("action"):
        details.append("action=" + tag_info["action"])
    if extra_strings:
        details.append("strings=" + ",".join(extra_strings[:3]))

    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "NPCMontageJson",
        "summary": (
            "MemoryPack NPCMontageJson; object member count 3; "
            f"animType {anim_type}; data member count {data_member_count}; "
            "tail GameplayTag parsed exactly"
        ),
        "rows": None,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": NPC_MONTAGE_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": ["animType", "dataMemberCount", "tag", "tagHash", "tagParts", "lengthPrefixedStrings"],
            "animType": anim_type,
            "animTypeName": "",
            "dataMemberCount": data_member_count,
            "dataPayloadBytes": tag_offset - 6,
            "tag": tag,
            "tagHash": tag_tail["hashHex"],
            "tagDepth": tag_tail["depth"],
            "tagParts": tag_parts,
            "tagCategory": tag_info,
            "sourceFolder": source_folder,
            "sampledStringCount": len(strings),
            "extraStrings": extra_strings,
            "stringHits": hits[:16],
            "tailTagOffset": format_offset(tag_offset),
            "exactTailTag": True,
            "exactLength": False,
        },
    }


def find_length_prefixed_utf8_tail_value(data: bytes, value: str, *, trailing_bytes: int = 1) -> tuple[int, int] | None:
    raw = value.encode("utf-8")
    marker = struct.pack("<I", len(raw)) + raw
    pos = data.rfind(marker)
    if pos < 0:
        return None
    end = pos + len(marker)
    if end + trailing_bytes != len(data):
        return None
    return pos, end


def decode_model_view_state_controller_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    schema = MEMORYPACK_FIELD_SCHEMAS.get("ModelViewStateControllerData")
    if not schema or not data or data[0] != MODEL_VIEW_STATE_CONTROLLER_MEMBER_COUNT:
        return None

    def read_u32_count(offset: int, field: str, *, max_count: int = 4096) -> tuple[int | None, int, str | None]:
        if offset + 4 > len(data):
            return None, offset, f"{field}:truncated-count"
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if count == MEMORYPACK_NULL_COUNT:
            return None, offset, None
        if count > max_count:
            return count, offset, f"{field}:large-count={count}"
        return count, offset, None

    stem = path.stem
    tail = find_length_prefixed_utf8_tail_value(data, stem, trailing_bytes=1)
    if not tail:
        return None
    model_id_offset, model_id_end = tail
    pre_tick_raw = data[model_id_end]
    if pre_tick_raw not in (0, 1):
        return None
    pre_tick_animator = bool(pre_tick_raw)

    offset = 1
    camera_count, offset, err = read_u32_count(offset, "cameraSignalSourceAssetHashes")
    if err or camera_count is None:
        return None
    if offset + camera_count * 8 > len(data):
        return None
    camera_hashes = [f"0x{struct.unpack_from('<Q', data, offset + index * 8)[0]:016x}" for index in range(camera_count)]
    offset += camera_count * 8

    clip_count, offset, err = read_u32_count(offset, "clipAssetInfos")
    if err or clip_count is None:
        return None
    clip_infos: list[dict[str, Any]] = []
    for index in range(clip_count):
        if offset + 13 > len(data) or data[offset] != 2:
            return None
        member_count = data[offset]
        hash_value = struct.unpack_from("<Q", data, offset + 1)[0]
        clip_name, next_offset, err = read_memorypack_utf8_string(data, offset + 9, max_length=512)
        if err or clip_name is None:
            return None
        clip_infos.append({
            "index": index,
            "memberCount": member_count,
            "hash": f"0x{hash_value:016x}",
            "name": clip_name,
        })
        offset = next_offset

    effect_count, offset, err = read_u32_count(offset, "effectIds")
    if err or effect_count is None:
        return None
    effect_ids: list[str] = []
    for _ in range(effect_count):
        effect_id, offset, err = read_memorypack_utf8_string(data, offset, max_length=512)
        if err or effect_id is None:
            return None
        effect_ids.append(effect_id)

    emissive_count, offset, err = read_u32_count(offset, "emissiveConfigHashes")
    if err or emissive_count is None:
        return None
    if offset + emissive_count * 8 > len(data):
        return None
    emissive_hashes = [
        f"0x{struct.unpack_from('<Q', data, offset + index * 8)[0]:016x}"
        for index in range(emissive_count)
    ]
    offset += emissive_count * 8

    model_animator_count, model_animator_body_offset, err = read_u32_count(offset, "modelAnimatorDatas")
    if err or model_animator_count is None:
        return None
    if model_animator_body_offset > model_id_offset:
        return None
    body_size = model_id_offset - model_animator_body_offset
    body_hits = scan_length_prefixed_utf8_string_hits(
        data,
        start=model_animator_body_offset,
        max_scan_bytes=body_size,
        max_samples=128,
        min_length=2,
        max_length=260,
    )
    body_strings = unique_strings([str(hit.get("value") or "") for hit in body_hits], 64)
    body_clip_refs = unique_strings([value for value in body_strings if value.startswith("A_")], 12)
    body_effect_refs = unique_strings([value for value in body_strings if value.startswith("P_")], 12)
    animator_names = unique_strings(
        [
            value
            for value in body_strings
            if value not in body_clip_refs
            and value not in body_effect_refs
            and value != stem
            and not value.startswith("A_")
            and not value.startswith("P_")
        ],
        16,
    )

    details = [
        f"modelId={stem}",
        f"clipInfos={clip_count}",
        f"effects={effect_count}",
        f"emissiveHashes={emissive_count}",
        f"modelAnimatorDatas={model_animator_count}",
        f"preTickAnimator={str(pre_tick_animator).lower()}",
    ]
    if clip_infos:
        details.append("clips=" + ",".join(str(item["name"]) for item in clip_infos[:3]))
    if effect_ids:
        details.append("effects=" + ",".join(effect_ids[:3]))
    if animator_names:
        details.append("animatorStrings=" + ",".join(animator_names[:4]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 6:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "ModelViewStateControllerData",
        "summary": (
            "MemoryPack ModelViewStateControllerData; object member count 7; "
            f"clips {clip_count}; effects {effect_count}; modelAnimatorDatas {model_animator_count}; "
            "modelId/preTick tail verified"
        ),
        "rows": None,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": MODEL_VIEW_STATE_CONTROLLER_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "cameraSignalSourceAssetHashes",
                "clipAssetInfos",
                "effectIds",
                "emissiveConfigHashes",
                "modelAnimatorDatasCount",
                "modelId",
                "preTickAnimator",
                "modelAnimatorDataStringSamples",
            ],
            "cameraSignalSourceAssetHashCount": camera_count,
            "cameraSignalSourceAssetHashes": camera_hashes[:16],
            "clipAssetInfoCount": clip_count,
            "clipAssetInfos": clip_infos[:16],
            "effectIdCount": effect_count,
            "effectIds": effect_ids[:16],
            "emissiveConfigHashCount": emissive_count,
            "emissiveConfigHashes": emissive_hashes[:16],
            "modelAnimatorDatasCount": model_animator_count,
            "modelAnimatorDatasOffset": format_offset(offset),
            "modelAnimatorDatasBodyBytes": body_size,
            "modelAnimatorDataStringSamples": body_strings[:24],
            "modelAnimatorDataClipRefs": body_clip_refs,
            "modelAnimatorDataEffectRefs": body_effect_refs,
            "animatorNames": animator_names,
            "modelId": stem,
            "modelIdOffset": format_offset(model_id_offset),
            "preTickAnimator": pre_tick_animator,
            "exactPrefixFields": [
                "cameraSignalSourceAssetHashes",
                "clipAssetInfos",
                "effectIds",
                "emissiveConfigHashes",
                "modelAnimatorDatasCount",
            ],
            "exactTailFields": ["modelId", "preTickAnimator"],
            "exactLength": False,
        },
    }


def decode_char_interact_perform_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    schema = MEMORYPACK_FIELD_SCHEMAS.get("CharInteractPerformCfgs")
    if not schema or not data or data[0] != CHAR_INTERACT_PERFORM_MEMBER_COUNT:
        return None

    offset = 1
    active_tags, active_tag_count, offset, err = read_memorypack_tag_list_prefix(data, offset, max_items=64)
    if err or active_tag_count is None:
        return None
    if offset >= len(data) or data[offset] not in (0, 1):
        return None
    allow_inherit_perform = bool(data[offset])
    offset += 1
    if offset + 4 > len(data):
        return None
    body_type_act_data_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if body_type_act_data_count > 1024:
        return None

    hits = scan_length_prefixed_utf8_string_hits(
        data,
        start=offset,
        max_samples=256,
        min_length=2,
        max_length=320,
    )
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 96)
    active_tag_values = {str(tag.get("tag") or "") for tag in active_tags}
    non_prefix_strings = [value for value in strings if value not in active_tag_values]
    status_tags = unique_strings([value for value in strings if value.startswith("Status/")], 16)
    montage_refs = unique_strings([value for value in strings if value.startswith("Montage/")], 16)
    actor_refs = unique_strings([value for value in strings if value.startswith(("chr_", "npc_"))], 16)
    effect_ids = unique_strings([value for value in strings if value.startswith("P_")], 16)
    perform_refs = unique_strings([value for value in strings if value.startswith("CharIntPerform")], 16)
    asset_refs = unique_strings(
        [
            value
            for value in strings
            if value.startswith(("DynamicAssets/", "Designer/", "Attachment/", "Weapons/"))
        ],
        16,
    )
    ccs_refs = unique_strings([value for value in strings if value.startswith(("Interact/", "LD/"))], 16)
    state_or_param = unique_strings(
        [
            value
            for value in non_prefix_strings
            if re.match(r"^[A-Za-z][A-Za-z0-9_]{2,48}$", value)
            and not value.startswith(("CharIntPerform", "Status", "Montage", "DynamicAssets"))
        ],
        16,
    )

    details = [
        f"activeTags={active_tag_count}",
        f"allowInheritPerform={str(allow_inherit_perform).lower()}",
        f"bodyTypeActDataDict={body_type_act_data_count}",
    ]
    if status_tags:
        details.append("status=" + ",".join(status_tags[:2]))
    if effect_ids:
        details.append("effects=" + ",".join(effect_ids[:3]))
    if montage_refs:
        details.append("montages=" + ",".join(montage_refs[:2]))
    if actor_refs:
        details.append("actors=" + ",".join(actor_refs[:3]))
    if perform_refs:
        details.append("performRefs=" + ",".join(perform_refs[:3]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "CharInteractPerformCfgs",
        "summary": (
            "MemoryPack CharInteractPerformCfgs; object member count 26; "
            f"activeTags {active_tag_count}; bodyTypeActDataDict {body_type_act_data_count}; "
            "body string preview classified"
        ),
        "rows": None,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": CHAR_INTERACT_PERFORM_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "activeTags",
                "allowInheritPerform",
                "bodyTypeActDataDictCount",
                "bodyStringSamples",
            ],
            "activeTagCount": active_tag_count,
            "activeTags": active_tags,
            "allowInheritPerform": allow_inherit_perform,
            "bodyTypeActDataDictCount": body_type_act_data_count,
            "bodyTypeActDataDictOffset": format_offset(offset),
            "statusTags": status_tags,
            "montageRefs": montage_refs,
            "actorRefs": actor_refs,
            "effectIds": effect_ids,
            "performRefs": perform_refs,
            "assetRefs": asset_refs,
            "ccsRefs": ccs_refs,
            "stateOrParamStrings": state_or_param,
            "bodyStringSamples": non_prefix_strings[:32],
            "stringHitCount": len(hits),
            "stringHits": hits[:24],
            "exactPrefixFields": [
                "activeTags",
                "allowInheritPerform",
                "bodyTypeActDataDictCount",
            ],
            "exactLength": False,
        },
    }


def decode_animation_config_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != len(MEMORYPACK_FIELD_SCHEMAS.get("AnimationConfig", [])):
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("AnimationConfig")
    if not schema:
        return None

    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=640, max_length=260)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 192)
    facial_morphs = unique_strings([value for value in strings if value.startswith("FacialMorph/")], 12)
    montage_paths = unique_strings([value for value in strings if value.startswith("Montage/")], 12)
    actor_anims = unique_strings([value for value in strings if value.startswith("A_actor_")], 12)
    cutscene_refs = unique_strings(
        [value for value in strings if value.startswith("cutscene_") or re.match(r"^e\d+m\d+_", value)],
        12,
    )
    other_paths = unique_strings(
        [
            value
            for value in strings
            if "/" in value
            and value not in facial_morphs
            and value not in montage_paths
        ],
        12,
    )
    state_names = unique_strings(
        [
            value
            for value in strings
            if "/" not in value
            and not value.startswith("A_actor_")
            and not value.startswith("cutscene_")
            and not re.match(r"^e\d+m\d+_", value)
        ],
        24,
    )
    bool_tail_valid = len(data) >= 2 and data[-2] in (0, 1) and data[-1] in (0, 1)
    use_rotate_direction = bool(data[-2]) if bool_tail_valid else None
    use_state_variables = bool(data[-1]) if bool_tail_valid else None

    details = [
        f"strings={len(strings)}",
        f"useRotateDirection={str(use_rotate_direction).lower() if use_rotate_direction is not None else 'unknown'}",
        f"useStateVariables={str(use_state_variables).lower() if use_state_variables is not None else 'unknown'}",
    ]
    if state_names:
        details.append("states=" + ",".join(state_names[:5]))
    if facial_morphs:
        details.append("facial=" + ",".join(facial_morphs[:2]))
    if montage_paths:
        details.append("montages=" + ",".join(montage_paths[:2]))
    if actor_anims:
        details.append("actorAnims=" + ",".join(actor_anims[:2]))
    if cutscene_refs:
        details.append("cutscenes=" + ",".join(cutscene_refs[:2]))

    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "AnimationConfig",
        "summary": (
            "MemoryPack AnimationConfig; object member count 12; "
            f"{len(strings)} sampled length-prefixed strings; "
            f"boolean tail {'verified' if bool_tail_valid else 'not verified'}"
        ),
        "rows": None,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": 12,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "stateNames",
                "facialMorphs",
                "montagePaths",
                "actorAnimationRefs",
                "cutsceneRefs",
                "booleanTail",
            ],
            "sampledStringCount": len(strings),
            "stateNames": state_names,
            "facialMorphs": facial_morphs,
            "montagePaths": montage_paths,
            "actorAnimationRefs": actor_anims,
            "cutsceneRefs": cutscene_refs,
            "otherPaths": other_paths,
            "useRotateDirection": use_rotate_direction,
            "useStateVariables": use_state_variables,
            "booleanTailVerified": bool_tail_valid,
            "stringHits": hits[:48],
            "exactLength": False,
        },
    }


def decode_buff_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != BUFF_MEMBER_COUNT:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("BuffData")
    if not schema:
        return None

    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=192)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 64)
    stem = path.stem
    id_marker_count, id_marker_offsets = length_prefixed_utf8_string_marker_info(data, stem)
    id_verified = id_marker_count > 0
    id_value = stem if id_verified else next((value for value in strings if value.startswith("buff_")), "")
    value_fields, complex_fields = buff_schema_field_groups(schema)
    post_id_prefix = decode_buff_post_id_prefix(data, id_value, id_marker_count, id_marker_offsets)

    tags = unique_strings(
        [value for value in strings if "/" in value and not value.startswith(("Assets/", "assets/"))],
        6,
    )
    params = unique_strings([value for value in strings if is_buff_param_string(value)], 8)
    refs = unique_strings(
        [
            value
            for value in strings
            if value != id_value and value.startswith(("buff_", "P_", "au_", "icon_"))
        ],
        6,
    )

    details = [
        f"id={id_value or 'unknown'}",
        "idString=verified" if id_verified else "idString=missing",
        f"strings={len(strings)}",
        f"idMarkers={id_marker_count}",
        f"typedFields={len(value_fields)}/{len(schema)}",
    ]
    if id_marker_offsets:
        details.append("idOffsets=" + format_offset_list(id_marker_offsets, id_marker_count))
    details.append("schemaTypes=" + ",".join(buff_schema_type_sample_parts()[:6]))
    post_id_sample = buff_post_id_prefix_sample(post_id_prefix)
    if post_id_sample:
        details.append("postId=" + post_id_sample)
    if tags:
        details.append("tags=" + ",".join(tags[:3]))
    if params:
        details.append("params=" + ",".join(params[:5]))
    if refs:
        details.append("refs=" + ",".join(refs[:3]))

    return {
        "kind": "memorypack-json",
        "subtype": "BuffData",
        "summary": (
            f"MemoryPack BuffData; object member count {BUFF_MEMBER_COUNT}; "
            f"id string {'verified' if id_verified else 'not found'}; "
            f"{len(strings)} sampled length-prefixed strings; "
            f"exact id markers {id_marker_count}; "
            f"field types recovered ({len(value_fields)} scalar/flag/id, "
            f"{len(complex_fields)} complex/list)"
            + (
                "; post-id tail parsed"
                if post_id_prefix.get("status") == "parsed-through-exact-tail"
                else (
                    "; post-id prefix parsed"
                    if str(post_id_prefix.get("status") or "").startswith("parsed-through")
                    else ""
                )
            )
        ),
        "rows": None,
        "keys": schema,
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": BUFF_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "id",
                "fieldTypes",
                "idMarkerOffsets",
                "postIdPrefix",
                "lengthPrefixedStrings",
            ],
            "id": id_value,
            "idStringVerified": id_verified,
            "idMarkerCount": id_marker_count,
            "idMarkerOffsets": [format_offset(offset) for offset in id_marker_offsets],
            "fieldTypes": BUFF_MEMORYPACK_FIELD_TYPES,
            "scalarFlagOrIdFields": value_fields,
            "complexOrListFields": complex_fields,
            "postIdPrefix": post_id_prefix,
            "stringCount": len(strings),
            "tags": tags,
            "params": params,
            "refs": refs,
            "stringHits": hits[:24],
            "exactLength": False,
        },
    }


def decode_skill_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != SKILL_MEMBER_COUNT:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("SkillData")
    if not schema:
        return None

    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=320)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 96)
    stem = path.stem
    id_marker_count, id_marker_offsets = length_prefixed_utf8_string_marker_info(data, stem, max_offsets=64)
    id_verified = id_marker_count > 0
    id_value = stem if id_verified else next((value for value in strings if value.startswith(("chr_", "eny_", "abilityentity_"))), "")
    value_fields, complex_fields = skill_schema_field_groups(schema)
    post_id_tail = decode_skill_post_id_tail_prefix(data, id_value, id_marker_count, id_marker_offsets)

    tags = unique_strings(
        [value for value in strings if "/" in value and not value.startswith(("Assets/", "assets/"))],
        8,
    )
    assets = unique_strings(
        [value for value in strings if value.startswith(("Assets/", "assets/"))],
        4,
    )
    refs = unique_strings(
        [
            value
            for value in strings
            if value != id_value
            and value.startswith((
                "buff_", "skill_", "P_", "au_", "icon_", "projectile_",
                "abilityentity_", "chr_", "eny_", "cc_", "common_",
            ))
        ],
        8,
    )
    params = unique_strings(
        [
            value
            for value in strings
            if is_buff_param_string(value)
            and value != id_value
            and value not in refs
            and not value.startswith(("skill_", "projectile_", "abilityentity_", "chr_", "eny_", "cc_", "common_"))
        ],
        10,
    )

    details = [
        f"id={id_value or 'unknown'}",
        "idString=verified" if id_verified else "idString=missing",
        f"strings={len(strings)}",
        f"idMarkers={id_marker_count}",
        f"typedFields={len(value_fields)}/{len(schema)}",
    ]
    if id_marker_offsets:
        details.append("idOffsets=" + format_offset_list(id_marker_offsets, id_marker_count))
    details.append("schemaTypes=" + ",".join(skill_schema_type_sample_parts()[:6]))
    post_id_sample = skill_post_id_tail_sample(post_id_tail)
    if post_id_sample:
        details.append("postId=" + post_id_sample)
    if tags:
        details.append("tags=" + ",".join(tags[:3]))
    if params:
        details.append("params=" + ",".join(params[:6]))
    if refs:
        details.append("refs=" + ",".join(refs[:4]))
    if assets:
        details.append("assets=" + ",".join(assets[:2]))

    return {
        "kind": "memorypack-json",
        "subtype": "SkillData",
        "summary": (
            f"MemoryPack SkillData; object member count {SKILL_MEMBER_COUNT}; "
            f"id string {'verified' if id_verified else 'not found'}; "
            f"{len(strings)} sampled length-prefixed strings; "
            f"field types recovered ({len(value_fields)} primitive/enum/string/vector, "
            f"{len(complex_fields)} complex/list)"
            + (
                "; post-id tail prefix parsed"
                if post_id_tail.get("status") in SKILL_POST_ID_PARSED_STATUSES
                else ""
            )
        ),
        "rows": None,
        "keys": schema,
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": SKILL_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "skillId",
                "fieldTypes",
                "idMarkerOffsets",
                "postIdTailPrefix",
                "lengthPrefixedStrings",
            ],
            "id": id_value,
            "idStringVerified": id_verified,
            "idMarkerCount": id_marker_count,
            "idMarkerOffsets": [format_offset(offset) for offset in id_marker_offsets],
            "fieldTypes": SKILL_MEMORYPACK_FIELD_TYPES,
            "valueLikeFields": value_fields,
            "complexOrListFields": complex_fields,
            "postIdTailPrefix": post_id_tail,
            "stringCount": len(strings),
            "tags": tags,
            "params": params,
            "refs": refs,
            "assets": assets,
            "stringHits": hits[:32],
            "exactLength": False,
        },
    }


def decode_leveldata_memorypack(rel: str, path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != LEVELDATA_MEMBER_COUNT:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("LevelData")
    if not schema:
        return None

    parts = rel.split("/")
    scene_id = parts[2] if len(parts) >= 4 and parts[0] == "Json" and parts[1] == "LevelData" else path.parent.name
    scene_verified = contains_length_prefixed_utf8_string(data, scene_id)
    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=512, max_length=220)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 128)

    level_scripts = unique_strings([value for value in strings if value.startswith("sc_")], 10)
    task_markers = unique_strings(
        [
            value
            for value in strings
            if value.startswith("lt:") or value.startswith(("Task", "FinishObj_", "guide_"))
        ],
        10,
    )
    params = unique_strings(
        [
            value
            for value in strings
            if is_buff_param_string(value)
            and value != scene_id
            and value not in task_markers
            and not value.startswith(("sc_", "guide_", "scene_", "base", "map", "dung", "indie", "Task", "FinishObj_", "lt:"))
        ],
        10,
    )
    assets = unique_strings([value for value in strings if value.startswith(("Assets/", "assets/"))], 4)
    refs = unique_strings(
        [
            value
            for value in strings
            if value != scene_id
            and re.match(r"^(scene_|base\d+_|map\d+_|dung\d+_|indie_|main\d+_|rgl\d+_)", value)
        ],
        8,
    )

    details = [
        f"sceneId={scene_id or 'unknown'}",
        "sceneId=verified" if scene_verified else "sceneId=missing",
        f"strings={len(strings)}",
    ]
    if level_scripts:
        details.append("levelScripts=" + ",".join(level_scripts[:4]))
    if task_markers:
        details.append("markers=" + ",".join(task_markers[:4]))
    if params:
        details.append("params=" + ",".join(params[:5]))
    if refs:
        details.append("refs=" + ",".join(refs[:3]))
    if assets:
        details.append("assets=" + ",".join(assets[:2]))

    return {
        "kind": "memorypack-json",
        "subtype": "LevelData",
        "summary": (
            f"MemoryPack LevelData; object member count {LEVELDATA_MEMBER_COUNT}; "
            f"scene id {'verified' if scene_verified else 'not found'}; "
            f"{len(strings)} sampled length-prefixed strings"
        ),
        "rows": None,
        "keys": schema,
        "sample": "; ".join(details)[:STRING_SAMPLE_MAX_CHARS],
        "decoded": {
            "memberCount": LEVELDATA_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": ["sceneId", "levelScriptRefs", "lengthPrefixedStrings"],
            "sceneId": scene_id,
            "sceneIdStringVerified": scene_verified,
            "sampledStringCount": len(strings),
            "levelScripts": level_scripts,
            "taskMarkers": task_markers,
            "params": params,
            "refs": refs,
            "assets": assets,
            "stringHits": hits[:40],
            "exactLength": False,
        },
    }


def read_memorypack_i32(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated-int32")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_memorypack_f32(data: bytes, offset: int) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated-float32")
    return struct.unpack_from("<f", data, offset)[0], offset + 4


def read_memorypack_bool(data: bytes, offset: int) -> tuple[bool, int]:
    if offset >= len(data):
        raise ValueError("truncated-bool")
    return bool(data[offset]), offset + 1


def require_memorypack_string(
    data: bytes,
    offset: int,
    field_name: str,
) -> tuple[str | None, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset)
    if error:
        raise ValueError(f"{field_name}:{error}")
    return value, offset


def read_memorypack_vec2(data: bytes, offset: int) -> tuple[list[float], int]:
    out: list[float] = []
    for _index in range(2):
        value, offset = read_memorypack_f32(data, offset)
        out.append(round(value, 4))
    return out, offset


def read_memorypack_vec3(data: bytes, offset: int) -> tuple[list[float], int]:
    out: list[float] = []
    for _index in range(3):
        value, offset = read_memorypack_f32(data, offset)
        out.append(round(value, 4))
    return out, offset


def find_levelconfig_map_id_tail(data: bytes, start: int) -> tuple[int, str, int] | None:
    tail_size = 56
    for pos in range(max(start, 0), max(start, len(data) - tail_size - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        text_start = pos + 4
        text_end = text_start + length
        if length <= 0 or length > 220 or text_end > len(data):
            continue
        if len(data) - text_end != tail_size:
            continue
        raw = data[text_start:text_end]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text) or not any(ch.isalnum() for ch in text):
            continue
        return pos, text, text_end
    return None


def decode_level_config_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != LEVEL_CONFIG_MEMBER_COUNT:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("LevelConfig")
    if not schema:
        return None

    try:
        offset = 1
        if offset >= len(data) or data[offset] != 3:
            return None
        offset += 1
        exported_scene_config_path, offset = require_memorypack_string(
            data,
            offset,
            "defaultState.exportedSceneConfigPath",
        )
        default_state_name, offset = require_memorypack_string(data, offset, "defaultState.name")
        source_scene_name, offset = require_memorypack_string(data, offset, "defaultState.sourceSceneName")
        dimension_source_level_id, offset = require_memorypack_string(data, offset, "dimensionSourceLevelId")
        level_id, offset = require_memorypack_string(data, offset, "id")
        id_num, offset = read_memorypack_i32(data, offset)
        is_dimension_level, offset = read_memorypack_bool(data, offset)
        is_seamless, offset = read_memorypack_bool(data, offset)
        if offset + 4 > len(data):
            return None
        level_data_path_count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        if level_data_path_count == MEMORYPACK_NULL_COUNT:
            level_data_path_count_value: int | None = None
        elif level_data_path_count <= 100_000:
            level_data_path_count_value = int(level_data_path_count)
        else:
            return None
        pre_map_payload_offset = offset
        map_tail = find_levelconfig_map_id_tail(data, pre_map_payload_offset)
        if not map_tail:
            return None
        map_id_offset, map_id, tail_offset = map_tail
        player_init_pos, tail_offset = read_memorypack_vec3(data, tail_offset)
        player_init_rot, tail_offset = read_memorypack_vec3(data, tail_offset)
        rect_left_bottom, tail_offset = read_memorypack_vec2(data, tail_offset)
        rect_right_top, tail_offset = read_memorypack_vec2(data, tail_offset)
        scope, tail_offset = read_memorypack_i32(data, tail_offset)
        start_pos, tail_offset = read_memorypack_vec3(data, tail_offset)
        if tail_offset != len(data):
            return None
    except (UnicodeDecodeError, ValueError, struct.error):
        return None

    id_verified = level_id == path.stem
    pre_map_payload_bytes = map_id_offset - pre_map_payload_offset
    details = [
        f"id={level_id or 'unknown'}",
        "idString=verified" if id_verified else "idString=missing",
        f"idNum={id_num}",
        f"mapId={map_id}",
        f"levelDataPaths={level_data_path_count_value if level_data_path_count_value is not None else 'null'}",
        f"scope={scope}",
        f"init=({','.join(str(value) for value in player_init_pos)})",
        f"rect=({rect_left_bottom[0]},{rect_left_bottom[1]})-({rect_right_top[0]},{rect_right_top[1]})",
    ]
    if exported_scene_config_path:
        details.append(f"defaultScene={exported_scene_config_path}")

    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 5:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "LevelConfig",
        "summary": (
            f"MemoryPack LevelConfig; object member count {LEVEL_CONFIG_MEMBER_COUNT}; "
            f"id {'verified' if id_verified else 'not found'}; "
            f"level data path count {level_data_path_count_value if level_data_path_count_value is not None else 'null'}; "
            "default state and numeric tail parsed"
        ),
        "rows": level_data_path_count_value,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": LEVEL_CONFIG_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": ["defaultState", "id", "levelDataPaths", "mapId", "numericTail"],
            "defaultState": {
                "exportedSceneConfigPath": exported_scene_config_path,
                "name": default_state_name,
                "sourceSceneName": source_scene_name,
            },
            "dimensionSourceLevelId": dimension_source_level_id,
            "id": level_id,
            "idStringVerified": id_verified,
            "idNum": id_num,
            "isDimensionLevel": is_dimension_level,
            "isSeamless": is_seamless,
            "levelDataPathCount": level_data_path_count_value,
            "preMapPayloadOffset": format_offset(pre_map_payload_offset),
            "preMapPayloadBytes": pre_map_payload_bytes,
            "preMapPayloadDecoded": False,
            "mapId": map_id,
            "mapIdOffset": format_offset(map_id_offset),
            "playerInitPos": player_init_pos,
            "playerInitRot": player_init_rot,
            "rectLeftBottom": rect_left_bottom,
            "rectRightTop": rect_right_top,
            "scope": scope,
            "startPos": start_pos,
            "exactLength": True,
        },
    }


def decode_spawner_blackboard_pair(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError("blackboard:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 4:
        raise ValueError(f"blackboard:member-count={member_count}")
    key, offset = require_memorypack_string(data, offset, "blackboard.key")
    use_string, offset = read_memorypack_bool(data, offset)
    value_float, offset = read_memorypack_f32(data, offset)
    value_string, offset = require_memorypack_string(data, offset, "blackboard.valueString")
    return {
        "key": key,
        "useString": use_string,
        "valueFloat": round(value_float, 4),
        "valueString": value_string,
    }, offset


def decode_spawner_buff_inst(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError("buff:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 2:
        raise ValueError(f"buff:member-count={member_count}")
    if offset + 4 > len(data):
        raise ValueError("buff:blackboard-count-truncated")
    blackboard_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if blackboard_count == MEMORYPACK_NULL_COUNT:
        blackboard_count = 0
    if blackboard_count > 256:
        raise ValueError(f"buff:blackboard-count={blackboard_count}")
    blackboard: list[dict[str, Any]] = []
    for _index in range(blackboard_count):
        pair, offset = decode_spawner_blackboard_pair(data, offset)
        blackboard.append(pair)
    buff_id, offset = require_memorypack_string(data, offset, "buff.buffId")
    return {"buffId": buff_id, "blackboard": blackboard}, offset


def decode_spawner_enemy_library_item(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError("enemy:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count != 11:
        raise ValueError(f"enemy:member-count={member_count}")

    if offset + 4 > len(data):
        raise ValueError("enemy:born-buff-count-truncated")
    born_buff_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if born_buff_count == MEMORYPACK_NULL_COUNT:
        born_buff_count = 0
    if born_buff_count > 256:
        raise ValueError(f"enemy:born-buff-count={born_buff_count}")
    born_buffs: list[dict[str, Any]] = []
    for _index in range(born_buff_count):
        buff, offset = decode_spawner_buff_inst(data, offset)
        born_buffs.append(buff)

    enemy_id, offset = require_memorypack_string(data, offset, "enemy.enemyId")
    enemy_level, offset = read_memorypack_i32(data, offset)
    force_to_battle, offset = read_memorypack_bool(data, offset)
    key, offset = require_memorypack_string(data, offset, "enemy.key")
    override_ai_config, offset = require_memorypack_string(data, offset, "enemy.overrideAIConfig")
    patrol_gait, offset = read_memorypack_i32(data, offset)
    prewarn_audio, offset = require_memorypack_string(data, offset, "enemy.preWarnAudioEventKey")
    fixed_rotation: list[float] = []
    for _index in range(4):
        value, offset = read_memorypack_f32(data, offset)
        fixed_rotation.append(round(value, 4))
    prewarn_effect, offset = require_memorypack_string(data, offset, "enemy.preWarnEffectKey")
    prewarn_time, offset = read_memorypack_f32(data, offset)
    return {
        "enemyId": enemy_id,
        "enemyLevel": enemy_level,
        "forceToBattle": force_to_battle,
        "key": key,
        "overrideAIConfig": override_ai_config,
        "patrolGait": patrol_gait,
        "preWarnAudioEventKey": prewarn_audio,
        "preWarnEffectFixedRotation": fixed_rotation,
        "preWarnEffectKey": prewarn_effect,
        "preWarnTime": round(prewarn_time, 4),
        "bornBuffs": born_buffs,
    }, offset


def decode_spawner_enemy_library(
    data: bytes,
    offset: int,
    count: int | None,
) -> tuple[list[dict[str, Any]], int, str | None]:
    if count is None:
        return [], offset, None
    if count > 256:
        return [], offset, f"enemyLibrary-count={count}"
    items: list[dict[str, Any]] = []
    try:
        for _index in range(count):
            item, offset = decode_spawner_enemy_library_item(data, offset)
            items.append(item)
    except ValueError as exc:
        return items, offset, str(exc)
    return items, offset, None


def decode_spawner_config_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != SPAWNER_CONFIG_MEMBER_COUNT:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("SpawnerConfig")
    if not schema:
        return None

    offset = 1
    config_id, offset, config_error = read_memorypack_utf8_string(data, offset)
    if config_error or not config_id:
        return None
    if offset + 4 > len(data):
        return None
    enemy_library_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if enemy_library_count == MEMORYPACK_NULL_COUNT:
        enemy_library_count_value: int | None = None
    elif enemy_library_count <= 10_000:
        enemy_library_count_value = int(enemy_library_count)
    else:
        return None

    enemy_items, enemy_library_end_offset, enemy_error = decode_spawner_enemy_library(
        data,
        offset,
        enemy_library_count_value,
    )
    id_verified = config_id == path.stem
    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=320, max_length=220)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 96)

    enemies = unique_strings(
        [str(item.get("enemyId") or "") for item in enemy_items]
        or [value for value in strings if value.startswith("eny_")],
        10,
    )
    born_buff_ids = unique_strings(
        [
            str(buff.get("buffId") or "")
            for item in enemy_items
            for buff in item.get("bornBuffs", [])
        ]
        or [value for value in strings if value.startswith("buff_")],
        10,
    )
    audio = unique_strings(
        [str(item.get("preWarnAudioEventKey") or "") for item in enemy_items]
        or [value for value in strings if value.startswith(("au_", "sfx_", "vo_"))],
        6,
    )
    effects = unique_strings(
        [str(item.get("preWarnEffectKey") or "") for item in enemy_items]
        or [
            value
            for value in strings
            if value.startswith(("P_", "E_")) and value.count("_") >= 2
        ],
        6,
    )
    waves = unique_strings(
        [value for value in strings if re.match(r"^w(?:ave)?[0-9A-Za-z_]*$", value)],
        8,
    )
    params = unique_strings(
        [
            value
            for value in strings
            if is_buff_param_string(value)
            and value != config_id
            and value not in enemies
            and value not in born_buff_ids
            and value not in audio
            and value not in effects
            and value not in waves
            and not re.match(r"^[0-9A-F]{8}$", value)
            and not re.match(r"^[A-Z][A-Za-z]{1,7}$", value)
        ],
        10,
    )
    force_count = sum(1 for item in enemy_items if item.get("forceToBattle"))
    first_enemy = enemy_items[0] if enemy_items else {}
    first_buffs = [
        str(buff.get("buffId") or "")
        for buff in first_enemy.get("bornBuffs", [])[:3]
        if buff.get("buffId")
    ]

    details = [
        f"configId={config_id}",
        "idString=verified" if id_verified else "idString=missing",
        f"enemyLibrary={enemy_library_count_value if enemy_library_count_value is not None else 'null'}",
        "enemyRows=parsed" if enemy_error is None else f"enemyRows=partial:{enemy_error}",
    ]
    if first_enemy:
        details.append(
            "firstEnemy="
            + ",".join(
                part
                for part in [
                    str(first_enemy.get("enemyId") or ""),
                    f"lv{first_enemy.get('enemyLevel')}",
                    "force" if first_enemy.get("forceToBattle") else "",
                ]
                if part
            )
        )
    if force_count:
        details.append(f"forced={force_count}")
    if first_buffs:
        details.append("firstBuffs=" + ",".join(first_buffs))
    if enemies:
        details.append("enemies=" + ",".join(enemies[:3]))
    if born_buff_ids:
        details.append("buffs=" + ",".join(born_buff_ids[:3]))
    if waves:
        details.append("waves=" + ",".join(waves[:4]))
    if params:
        details.append("params=" + ",".join(params[:3]))
    if audio:
        details.append("audio=" + ",".join(audio[:1]))
    if effects:
        details.append("effects=" + ",".join(effects[:1]))

    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    parsed_note = "enemy library parsed" if enemy_error is None else f"enemy library partial ({enemy_error})"
    return {
        "kind": "memorypack-json",
        "subtype": "SpawnerConfig",
        "summary": (
            f"MemoryPack SpawnerConfig; object member count {SPAWNER_CONFIG_MEMBER_COUNT}; "
            f"configId {'verified' if id_verified else 'not found'}; "
            f"enemy library count {enemy_library_count_value if enemy_library_count_value is not None else 'null'}; "
            f"{parsed_note}"
        ),
        "rows": enemy_library_count_value,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": SPAWNER_CONFIG_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": ["configId", "enemyLibrary", "lengthPrefixedStrings"],
            "configId": config_id,
            "idStringVerified": id_verified,
            "enemyLibraryCount": enemy_library_count_value,
            "enemyLibraryParsed": enemy_error is None,
            "enemyLibraryParseError": enemy_error or "",
            "enemyLibraryEndOffset": format_offset(enemy_library_end_offset),
            "enemyLibrarySample": enemy_items[:3],
            "sampledStringCount": len(strings),
            "enemies": enemies,
            "buffs": born_buff_ids,
            "waves": waves,
            "params": params,
            "audio": audio,
            "effects": effects,
            "stringHits": hits[:32],
            "exactLength": False,
        },
    }


def atmospheric_npc_key_is_plausible(value: str) -> bool:
    text = str(value or "")
    if not text.startswith("npc_"):
        return False
    lowered = text.lower()
    return (
        "_atmospheric_" in lowered
        or "_enviromental_" in lowered
        or "_environmental_" in lowered
    )


def atmospheric_npc_row_key_positions(data: bytes) -> list[tuple[int, str]]:
    positions: list[tuple[int, str]] = []
    for pos in range(5, max(5, len(data) - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        text_start = pos + 4
        text_end = text_start + length
        if not (1 <= length <= ATMOSPHERIC_NPC_KEY_MAX_LENGTH and text_end < len(data)):
            continue
        if data[text_end] != ATMOSPHERIC_NPC_ROW_MEMBER_COUNT:
            continue
        raw = data[text_start:text_end]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text) or not atmospheric_npc_key_is_plausible(text):
            continue
        positions.append((pos, text))
    return positions


def scan_atmospheric_npc_row_strings(
    data: bytes,
    start: int,
    end: int,
    *,
    limit: int = 64,
) -> list[str]:
    strings: list[str] = []
    for pos in range(max(0, start), max(max(0, start), min(len(data), end) - 4)):
        length = struct.unpack_from("<I", data, pos)[0]
        if length <= 0 or length > 220 or pos + 4 + length > end:
            continue
        raw = data[pos + 4:pos + 4 + length]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if any(ord(ch) < 32 for ch in text) or not any(ch.isalnum() for ch in text):
            continue
        if text not in strings:
            strings.append(text)
            if len(strings) >= limit:
                break
    return strings


def atmospheric_level_id_like(value: str) -> bool:
    text = str(value or "")
    if not text or text.startswith("npc_") or "_cluster_" in text:
        return False
    if "_atmospheric_" in text or "_enviromental_" in text or "_environmental_" in text:
        return False
    return bool(re.match(r"^(?:base|map|dung|indie|main|rgl)\d{0,2}(?:_|$)", text, re.IGNORECASE))


def classify_atmospheric_npc_strings(strings: list[str], row_keys: set[str]) -> dict[str, list[str]]:
    return {
        "aiConfigs": unique_strings([value for value in strings if value.startswith("aiconf_")], 12),
        "montages": unique_strings([value for value in strings if value.startswith("Montage/")], 12),
        "facialAnims": unique_strings([value for value in strings if value.startswith("FacialMorph/")], 12),
        "envTalks": unique_strings([value for value in strings if value.startswith("envTalk_")], 12),
        "templateIds": unique_strings(
            [
                value
                for value in strings
                if value.startswith("npc_")
                and value not in row_keys
                and not atmospheric_npc_key_is_plausible(value)
            ],
            12,
        ),
        "clusters": unique_strings([value for value in strings if "_cluster_" in value], 12),
        "levels": unique_strings([value for value in strings if atmospheric_level_id_like(value)], 12),
    }


def decode_atmospheric_npc_table_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != ATMOSPHERIC_NPC_TABLE_MEMBER_COUNT or len(data) < 5:
        return None
    schema = MEMORYPACK_FIELD_SCHEMAS.get("NpcAtmosphericDataTable")
    if not schema:
        return None

    table_count = struct.unpack_from("<I", data, 1)[0]
    if table_count > 100_000:
        return None
    positions = atmospheric_npc_row_key_positions(data)
    row_keys = [text for _pos, text in positions]
    row_key_set = set(row_keys)
    row_boundaries_verified = len(positions) == table_count
    if table_count == 0 and len(data) != 5:
        row_boundaries_verified = False

    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=512, max_length=220)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 160)
    classified = classify_atmospheric_npc_strings(strings, row_key_set)

    row_samples: list[dict[str, Any]] = []
    for index, (pos, key) in enumerate(positions[:10]):
        key_length = struct.unpack_from("<I", data, pos)[0]
        member_offset = pos + 4 + key_length
        next_offset = positions[index + 1][0] if index + 1 < len(positions) else len(data)
        value_start = member_offset + 1
        row_strings = scan_atmospheric_npc_row_strings(data, value_start, next_offset, limit=80)
        row_classified = classify_atmospheric_npc_strings(row_strings, {key})
        row_sample = {
            "index": index,
            "key": key,
            "memberCount": data[member_offset] if member_offset < len(data) else None,
            "aiCfg": next(iter(row_classified["aiConfigs"]), ""),
            "templateDataId": next(iter(row_classified["templateIds"]), ""),
            "levelId": next(iter(row_classified["levels"]), ""),
            "clusterId": next(iter(row_classified["clusters"]), ""),
            "montages": row_classified["montages"][:3],
            "facialAnims": row_classified["facialAnims"][:2],
            "envTalks": row_classified["envTalks"][:3],
            "rowStartOffset": format_offset(pos),
            "rowEndOffset": format_offset(next_offset),
        }
        row_samples.append(row_sample)

    details = [
        f"rows={table_count}",
        "rowKeys=verified" if row_boundaries_verified else f"rowKeys={len(positions)}/{table_count}",
    ]
    if row_keys:
        details.append(f"first={row_keys[0]}")
    if classified["aiConfigs"]:
        details.append("ai=" + ",".join(classified["aiConfigs"][:3]))
    if classified["montages"]:
        details.append("montages=" + ",".join(classified["montages"][:2]))
    if classified["envTalks"]:
        details.append("envTalks=" + ",".join(classified["envTalks"][:3]))
    if classified["templateIds"]:
        details.append("templates=" + ",".join(classified["templateIds"][:3]))
    if classified["clusters"]:
        details.append("clusters=" + ",".join(classified["clusters"][:2]))
    if classified["levels"]:
        details.append("levels=" + ",".join(classified["levels"][:3]))

    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "NpcAtmosphericDataTable",
        "summary": (
            "MemoryPack NpcAtmosphericDataTable; object member count "
            f"{ATMOSPHERIC_NPC_TABLE_MEMBER_COUNT}; dataTable rows {table_count}; "
            f"LevelNpcData-like row member count {ATMOSPHERIC_NPC_ROW_MEMBER_COUNT}; "
            f"row boundaries {'verified' if row_boundaries_verified else 'partial'}"
        ),
        "rows": table_count,
        "keys": ["dataTable", "rowKey", "aiCfg", "montages", "envTalkIds", "templateDataId", "clusterId", "levelId"],
        "sample": sample,
        "decoded": {
            "memberCount": ATMOSPHERIC_NPC_TABLE_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "rowSchemaSource": "LevelEntityData/LevelNpcData field names from installed IL2CPP metadata; full 109-member inherited row payload not yet named",
            "decodedPreviewFields": [
                "dataTable",
                "rowKeys",
                "aiCfg",
                "montages",
                "facialAnims",
                "envTalkIds",
                "templateDataId",
                "clusterId",
                "levelId",
            ],
            "tableRowCount": table_count,
            "rowKeyCount": len(positions),
            "rowBoundariesVerified": row_boundaries_verified,
            "rowMemberCount": ATMOSPHERIC_NPC_ROW_MEMBER_COUNT,
            "rowKeysSample": row_keys[:20],
            "rowSamples": row_samples,
            "aiConfigs": classified["aiConfigs"],
            "montages": classified["montages"],
            "facialAnims": classified["facialAnims"],
            "envTalks": classified["envTalks"],
            "templateIds": classified["templateIds"],
            "clusters": classified["clusters"],
            "levels": classified["levels"],
            "sampledStringCount": len(strings),
            "stringHits": hits[:48],
            "rowPayloadDecoded": False,
            "exactLength": row_boundaries_verified,
        },
    }


def classify_levelscript_template_strings(strings: list[str], template_id: str) -> dict[str, list[str]]:
    hash8_re = re.compile(r"^[0-9a-f]{8}$", re.IGNORECASE)
    structural_prefixes = ("lt:p:", "lt:mp:", "#", "$", "@lsm_key@")
    hash_values = unique_strings([value for value in strings if hash8_re.match(value)], 16)
    property_refs = unique_strings([value for value in strings if value.startswith("lt:p:")], 16)
    map_property_refs = unique_strings([value for value in strings if value.startswith("lt:mp:")], 16)
    local_refs = unique_strings([value for value in strings if value.startswith("$")], 16)
    hash_refs = unique_strings([value for value in strings if value.startswith("#")], 16)
    montage_refs = unique_strings([value for value in strings if value.startswith("Montage/")], 16)
    audio_refs = unique_strings([value for value in strings if value.startswith(("au_", "radio_", "bark_"))], 16)
    effect_refs = unique_strings([value for value in strings if value.startswith("P_")], 16)
    lsm_keys = unique_strings([value for value in strings if value.startswith("@lsm_key@")], 16)
    slash_refs = unique_strings(
        [
            value
            for value in strings
            if "/" in value
            and value not in montage_refs
            and not value.startswith(structural_prefixes)
        ],
        16,
    )
    key_like = unique_strings(
        [
            value
            for value in strings
            if value != template_id
            and not hash8_re.match(value)
            and not value.startswith(structural_prefixes)
            and value not in montage_refs
            and value not in audio_refs
            and value not in effect_refs
            and value not in slash_refs
            and re.match(r"^[A-Za-z_][A-Za-z0-9_:@-]{2,96}$", value)
        ],
        32,
    )
    comments = unique_strings(
        [
            value
            for value in strings
            if value != template_id
            and " " in value
            and not value.startswith(structural_prefixes)
        ],
        12,
    )
    return {
        "keyLikeStrings": key_like,
        "hash8Strings": hash_values,
        "hashRefs": hash_refs,
        "propertyRefs": property_refs,
        "mapPropertyRefs": map_property_refs,
        "localRefs": local_refs,
        "lsmKeys": lsm_keys,
        "montageRefs": montage_refs,
        "audioRefs": audio_refs,
        "effectRefs": effect_refs,
        "slashRefs": slash_refs,
        "commentStrings": comments,
    }


def read_memorypack_u32_count(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_count: int = 50_000,
) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-count")
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if count == MEMORYPACK_NULL_COUNT:
        raise ValueError(f"{field_name}:null-count")
    if count > max_count:
        raise ValueError(f"{field_name}:invalid-count={count}")
    return count, offset


def require_memorypack_non_null_string(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 512,
) -> tuple[str, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset, max_length=max_length)
    if error:
        raise ValueError(f"{field_name}:{error}")
    if value is None:
        raise ValueError(f"{field_name}:null-string")
    return value, offset


def decode_interactive_table_memorypack(data: bytes, size: int) -> dict[str, Any] | None:
    schema = MEMORYPACK_FIELD_SCHEMAS.get("InteractiveTable")
    if not schema or not data or data[0] != INTERACTIVE_TABLE_MEMBER_COUNT:
        return None

    try:
        offset = 1
        core_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "coreTemplatePathDict",
            max_count=10_000,
        )
        core_entries: list[tuple[str, str]] = []
        for index in range(core_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"coreTemplatePathDict[{index}].key",
            )
            value, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"coreTemplatePathDict[{index}].value",
                max_length=1024,
            )
            core_entries.append((key, value))

        interactive_offset = offset
        interactive_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "interactiveDataDict",
            max_count=50_000,
        )
        interactive_entries: list[tuple[str, int, str]] = []
        marker_counts: Counter[int] = Counter()
        for index in range(interactive_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"interactiveDataDict[{index}].key",
            )
            if offset >= len(data):
                raise ValueError(f"interactiveDataDict[{index}].value:truncated-member-count")
            value_member_count = data[offset]
            offset += 1
            marker_counts[value_member_count] += 1
            value, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"interactiveDataDict[{index}].value.templateId",
            )
            interactive_entries.append((key, value_member_count, value))

        if offset != len(data):
            return None
    except ValueError:
        return None

    core_keys = {key for key, _value in core_entries}
    target_ids = {value for _key, _marker, value in interactive_entries}
    missing_targets = sorted(target_ids - core_keys)
    unused_core_templates = sorted(core_keys - target_ids)
    self_rows = sum(1 for key, _marker, value in interactive_entries if key == value)
    alias_rows = interactive_count - self_rows
    core_samples = [
        {"id": key, "path": value}
        for key, value in core_entries[:8]
    ]
    interactive_samples = [
        {"id": key, "valueMemberCount": marker, "templateId": value}
        for key, marker, value in interactive_entries[:12]
    ]

    details = [
        f"coreTemplates={core_count}",
        f"interactiveData={interactive_count}",
        f"uniqueTargets={len(target_ids)}",
        f"selfRows={self_rows}",
        f"aliases={alias_rows}",
    ]
    if interactive_entries:
        sample_pairs = [f"{key}->{value}" for key, _marker, value in interactive_entries[:4]]
        details.append("samples=" + ",".join(sample_pairs))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "InteractiveTable",
        "summary": (
            "MemoryPack InteractiveTable; object member count 2; "
            f"coreTemplatePathDict {core_count} string paths; "
            f"interactiveDataDict {interactive_count} one-member template refs; "
            "exact length"
        ),
        "rows": interactive_count,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": INTERACTIVE_TABLE_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": ["coreTemplatePathDict", "interactiveDataDict"],
            "coreTemplatePathCount": core_count,
            "interactiveDataCount": interactive_count,
            "interactiveDataOffset": format_offset(interactive_offset),
            "valueMemberCountMarkers": dict(sorted(marker_counts.items())),
            "uniqueTemplateTargets": len(target_ids),
            "selfRows": self_rows,
            "aliasRows": alias_rows,
            "allTargetsHaveCoreTemplate": not missing_targets,
            "missingTargetSamples": missing_targets[:16],
            "unusedCoreTemplateSamples": unused_core_templates[:16],
            "coreTemplatePathSamples": core_samples,
            "interactiveDataSamples": interactive_samples,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_model_radius_table_memorypack(data: bytes, size: int) -> dict[str, Any] | None:
    if not data or data[0] != 1:
        return None

    try:
        offset = 1
        entry_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "ModelRadiusTable",
            max_count=50_000,
        )
        marker_counts: Counter[int] = Counter()
        field0_counts: Counter[int] = Counter()
        flag_counts: Counter[int] = Counter()
        field2_counts: Counter[int] = Counter()
        rows: list[tuple[str, int, int, int, float]] = []
        radii: list[float] = []
        for index in range(entry_count):
            model_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"ModelRadiusTable[{index}].key",
                max_length=512,
            )
            if offset >= len(data):
                raise ValueError(f"ModelRadiusTable[{index}].value:truncated-member-count")
            value_member_count = data[offset]
            offset += 1
            marker_counts[value_member_count] += 1
            field0, offset = read_memorypack_i32(data, offset)
            if offset >= len(data):
                raise ValueError(f"ModelRadiusTable[{index}].flag:truncated")
            flag = data[offset]
            offset += 1
            field2, offset = read_memorypack_i32(data, offset)
            if offset + 4 > len(data):
                raise ValueError(f"ModelRadiusTable[{index}].radius:truncated")
            radius = struct.unpack_from("<f", data, offset)[0]
            offset += 4
            if not math.isfinite(radius):
                raise ValueError(f"ModelRadiusTable[{index}].radius:non-finite")
            field0_counts[field0] += 1
            flag_counts[flag] += 1
            field2_counts[field2] += 1
            rows.append((model_id, value_member_count, field0, field2, radius))
            radii.append(radius)

        if offset != len(data):
            return None
        if set(marker_counts) != {MODEL_RADIUS_VALUE_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    radius_min = min(radii) if radii else 0.0
    radius_max = max(radii) if radii else 0.0
    radius_avg = sum(radii) / len(radii) if radii else 0.0
    zero_radius_count = sum(1 for value in radii if value == 0.0)
    sample_rows = [
        {
            "modelId": model_id,
            "valueMemberCount": marker,
            "field0": field0,
            "field2": field2,
            "radius": round(radius, 6),
        }
        for model_id, marker, field0, field2, radius in rows[:12]
    ]

    details = [
        f"rows={entry_count}",
        f"radiusMin={radius_min:.4g}",
        f"radiusMax={radius_max:.4g}",
        "flagBytes=" + ",".join(f"{key}:{value}" for key, value in sorted(flag_counts.items())),
    ]
    if rows:
        samples = [f"{model_id}:{radius:.4g}" for model_id, _marker, _field0, _field2, radius in rows[:4]]
        details.append("samples=" + ",".join(samples))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "ModelRadiusTable",
        "summary": (
            "MemoryPack ModelRadiusTable; object member count 1; "
            f"{entry_count} keyed radius rows; value object member count 4; "
            "exact length"
        ),
        "rows": entry_count,
        "keys": ["modelId", "field0", "flagByte", "field2", "radius"],
        "sample": sample,
        "decoded": {
            "memberCount": 1,
            "format": "memorypack",
            "decodedPreviewFields": ["modelId", "field0", "flagByte", "field2", "radius"],
            "entryCount": entry_count,
            "valueMemberCountMarkers": dict(sorted(marker_counts.items())),
            "field0Counts": dict(sorted(field0_counts.items())),
            "flagByteCounts": dict(sorted(flag_counts.items())),
            "field2Counts": dict(sorted(field2_counts.items())),
            "radiusMin": round(radius_min, 6),
            "radiusMax": round(radius_max, 6),
            "radiusAvg": round(radius_avg, 6),
            "zeroRadiusCount": zero_radius_count,
            "sampleRows": sample_rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


TELEPORT_VALIDATION_TABLE_RELS = {
    "Json/GameplayConfig/CinematicTeleportValidationDataTable.json",
    "Json/GameplayConfig/CommonSysTeleportValidationDataTable.json",
    "Json/GameplayConfig/GuideTeleportValidationDataTable.json",
    "Json/GameplayConfig/MapTeleportValidationDataTable.json",
}


def read_memorypack_nullable_string(
    data: bytes,
    offset: int,
    field_name: str,
    *,
    max_length: int = 512,
) -> tuple[str | None, int]:
    value, offset, error = read_memorypack_utf8_string(data, offset, max_length=max_length)
    if error:
        raise ValueError(f"{field_name}:{error}")
    return value, offset


def decode_teleport_validation_table_memorypack(
    rel: str,
    data: bytes,
    size: int,
) -> dict[str, Any] | None:
    if rel not in TELEPORT_VALIDATION_TABLE_RELS or not data or data[0] != 1:
        return None

    try:
        offset = 1
        entry_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "TeleportValidationDataTable",
            max_count=50_000,
        )
        marker_counts: Counter[int] = Counter()
        flag_word_counts: Counter[int] = Counter()
        map_id_counts: Counter[str] = Counter()
        tail_counts: list[Counter[int]] = [Counter(), Counter(), Counter(), Counter()]
        first_floats: list[float] = []
        rows: list[dict[str, Any]] = []
        duplicate_id_matches = 0
        for index in range(entry_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"TeleportValidationDataTable[{index}].key",
                max_length=512,
            )
            if offset >= len(data):
                raise ValueError(f"TeleportValidationDataTable[{index}].value:truncated-member-count")
            value_member_count = data[offset]
            offset += 1
            marker_counts[value_member_count] += 1
            first_float, offset = read_memorypack_f32(data, offset)
            if not math.isfinite(first_float):
                raise ValueError(f"TeleportValidationDataTable[{index}].field0Float:non-finite")
            inner_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"TeleportValidationDataTable[{index}].id",
                max_length=512,
            )
            if inner_id == key:
                duplicate_id_matches += 1
            if offset + 2 > len(data):
                raise ValueError(f"TeleportValidationDataTable[{index}].flagWord:truncated")
            flag_word = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            position, offset = read_memorypack_vec3(data, offset)
            rotation, offset = read_memorypack_vec3(data, offset)
            if not all(math.isfinite(float(value)) for value in position + rotation):
                raise ValueError(f"TeleportValidationDataTable[{index}].vectors:non-finite")
            map_id, offset = read_memorypack_nullable_string(
                data,
                offset,
                f"TeleportValidationDataTable[{index}].mapId",
                max_length=256,
            )
            tails: list[int] = []
            for tail_index in range(4):
                value, offset = read_memorypack_i32(data, offset)
                tails.append(value)
                tail_counts[tail_index][value] += 1
            first_floats.append(first_float)
            flag_word_counts[flag_word] += 1
            map_id_counts["<null>" if map_id is None else map_id] += 1
            if len(rows) < 16:
                rows.append(
                    {
                        "id": key,
                        "valueMemberCount": value_member_count,
                        "field0Float": round(first_float, 6),
                        "flagWord": flag_word,
                        "position": position,
                        "rotation": rotation,
                        "mapId": map_id,
                        "tailInts": tails,
                    }
                )

        if offset != len(data):
            return None
        if set(marker_counts) != {TELEPORT_VALIDATION_VALUE_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    table_name = Path(rel).stem
    map_summary = ",".join(
        f"{key}:{count}" for key, count in map_id_counts.most_common(4)
    )
    tail2_summary = ",".join(
        f"{key}:{count}" for key, count in tail_counts[2].most_common(4)
    )
    details = [
        f"rows={entry_count}",
        f"idsVerified={duplicate_id_matches}/{entry_count}",
        f"field0Range={min(first_floats):.4g}..{max(first_floats):.4g}",
    ]
    if map_summary:
        details.append("mapIds=" + map_summary)
    if tail2_summary:
        details.append("tail2=" + tail2_summary)
    if rows:
        sample_bits = []
        for row in rows[:3]:
            map_label = row["mapId"] if row["mapId"] is not None else "<null>"
            sample_bits.append(f"{row['id']}@{map_label}")
        details.append("samples=" + ",".join(sample_bits))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "TeleportValidationDataTable",
        "summary": (
            f"MemoryPack {table_name}; object member count 1; "
            f"{entry_count} keyed teleport rows; value object member count 10; "
            "exact length"
        ),
        "rows": entry_count,
        "keys": [
            "id",
            "field0Float",
            "flagWord",
            "position",
            "rotation",
            "mapId",
            "tail0",
            "tail1",
            "tail2",
            "tail3",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": 1,
            "format": "memorypack",
            "decodedPreviewFields": [
                "id",
                "field0Float",
                "flagWord",
                "position",
                "rotation",
                "mapId",
                "tailInts",
            ],
            "entryCount": entry_count,
            "valueMemberCountMarkers": dict(sorted(marker_counts.items())),
            "duplicateIdMatches": duplicate_id_matches,
            "field0Min": round(min(first_floats), 6) if first_floats else 0.0,
            "field0Max": round(max(first_floats), 6) if first_floats else 0.0,
            "flagWordCounts": dict(sorted(flag_word_counts.items())),
            "mapIdCounts": dict(map_id_counts.most_common(16)),
            "tailIntCounts": [dict(counter.most_common(16)) for counter in tail_counts],
            "sampleRows": rows,
            "exactLength": True,
            "fileSize": size,
        },
    }



def decode_damage_text_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != DAMAGE_TEXT_REL:
        return None
    if not data or data[0] != DAMAGE_TEXT_ROOT_MEMBER_COUNT:
        return None

    def parse_animation_ref(offset: int, row_index: int, anim_index: int) -> tuple[dict[str, Any], int]:
        if offset >= len(data) or data[offset] != DAMAGE_TEXT_ANIMATION_MEMBER_COUNT:
            raise ValueError(f"damageText[{row_index}].animation[{anim_index}].memberCount")
        offset += 1
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"damageText[{row_index}].animation[{anim_index}].name",
            max_length=128,
        )
        duration = round(read_memorypack_f32(data, offset)[0], 6)
        offset += 4
        int0 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        int1 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        int2 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        if not math.isfinite(duration) or abs(duration) > 10_000:
            raise ValueError(f"damageText[{row_index}].animation[{anim_index}].duration")
        if any(abs(value) > 1_000_000 for value in (int0, int1, int2)):
            raise ValueError(f"damageText[{row_index}].animation[{anim_index}].ints")
        return {
            "name": name,
            "durationOrScale": duration,
            "int0": int0,
            "int1": int1,
            "int2": int2,
        }, offset

    def parse_node_meta(offset: int, row_index: int, node_index: int) -> tuple[dict[str, Any], int]:
        if offset >= len(data) or data[offset] != DAMAGE_TEXT_NODE_MEMBER_COUNT:
            raise ValueError(f"damageText[{row_index}].node[{node_index}].memberCount")
        offset += 1
        name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"damageText[{row_index}].node[{node_index}].name",
            max_length=128,
        )
        text_or_value, offset = read_memorypack_nullable_string(
            data,
            offset,
            f"damageText[{row_index}].node[{node_index}].textOrValue",
            max_length=256,
        )
        resource_or_path, offset = read_memorypack_nullable_string(
            data,
            offset,
            f"damageText[{row_index}].node[{node_index}].resourceOrPath",
            max_length=256,
        )
        scalar = round(read_memorypack_f32(data, offset)[0], 6)
        offset += 4
        int0 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        int1 = struct.unpack_from("<i", data, offset)[0]
        offset += 4
        if not math.isfinite(scalar) or abs(scalar) > 10_000:
            raise ValueError(f"damageText[{row_index}].node[{node_index}].scalar")
        if any(abs(value) > 1_000_000 for value in (int0, int1)):
            raise ValueError(f"damageText[{row_index}].node[{node_index}].ints")
        return {
            "name": name,
            "textOrValue": text_or_value,
            "resourceOrPath": resource_or_path,
            "scalar": scalar,
            "int0": int0,
            "int1": int1,
        }, offset

    def parse_row_prefix(offset: int, row_index: int) -> tuple[dict[str, Any], int]:
        start = offset
        if offset >= len(data) or data[offset] != DAMAGE_TEXT_ROW_MEMBER_COUNT:
            raise ValueError(f"damageText[{row_index}].memberCount")
        offset += 1
        row_flag = data[offset]
        offset += 1
        if row_flag not in {0, 1}:
            raise ValueError(f"damageText[{row_index}].rowFlag={row_flag}")
        animation_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"damageText[{row_index}].animationCount",
            max_count=16,
        )
        if animation_count <= 0:
            raise ValueError(f"damageText[{row_index}].animationCount=0")
        animations: list[dict[str, Any]] = []
        for anim_index in range(animation_count):
            animation, offset = parse_animation_ref(offset, row_index, anim_index)
            animations.append(animation)

        node_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"damageText[{row_index}].nodeMetaCount",
            max_count=256,
        )
        layout_count, offset = read_memorypack_u32_count(
            data,
            offset,
            f"damageText[{row_index}].layoutCount",
            max_count=256,
        )
        if node_count != layout_count:
            raise ValueError(f"damageText[{row_index}].layoutCountMismatch={node_count}/{layout_count}")
        nodes: list[dict[str, Any]] = []
        for node_index in range(node_count):
            node, offset = parse_node_meta(offset, row_index, node_index)
            nodes.append(node)
        return {
            "startOffset": start,
            "rowFlag": row_flag,
            "animationCount": animation_count,
            "animations": animations,
            "nodeMetaCount": node_count,
            "layoutCount": layout_count,
            "nodes": nodes,
        }, offset

    def is_row_start(offset: int) -> bool:
        try:
            parse_row_prefix(offset, -1)
        except (ValueError, struct.error, UnicodeDecodeError):
            return False
        return True

    try:
        offset = 1
        charset, offset = require_memorypack_non_null_string(
            data,
            offset,
            "damageText.charset",
            max_length=128,
        )
        declared_rows, offset = read_memorypack_u32_count(
            data,
            offset,
            "damageText.rows",
            max_count=1_000,
        )
        if declared_rows <= 0:
            return None

        row_member_counts: Counter[int] = Counter()
        animation_member_counts: Counter[int] = Counter()
        node_member_counts: Counter[int] = Counter()
        animation_count_by_row: Counter[int] = Counter()
        node_count_pairs: Counter[str] = Counter()
        tail_length_counts: Counter[int] = Counter()
        row_flags: Counter[int] = Counter()
        animation_names: list[str] = []
        node_names: list[str] = []
        node_resource_refs: list[str] = []
        sample_rows: list[dict[str, Any]] = []

        for row_index in range(declared_rows):
            row, after_nodes = parse_row_prefix(offset, row_index)
            row_member_counts[DAMAGE_TEXT_ROW_MEMBER_COUNT] += 1
            row_flags[row["rowFlag"]] += 1
            animation_count_by_row[row["animationCount"]] += 1
            node_count_pairs[f"{row['nodeMetaCount']}/{row['layoutCount']}"] += 1
            animation_member_counts[DAMAGE_TEXT_ANIMATION_MEMBER_COUNT] += len(row["animations"])
            node_member_counts[DAMAGE_TEXT_NODE_MEMBER_COUNT] += len(row["nodes"])

            if row_index + 1 < declared_rows:
                next_offset = None
                for candidate in range(after_nodes, len(data)):
                    if is_row_start(candidate):
                        next_offset = candidate
                        break
                if next_offset is None:
                    return None
            else:
                next_offset = len(data)
            tail = data[after_nodes:next_offset]
            tail_length_counts[len(tail)] += 1
            tail_hits = scan_length_prefixed_utf8_string_hits(
                tail,
                max_samples=6,
                min_length=2,
                max_length=96,
            )

            for animation in row["animations"]:
                name = animation["name"]
                if name not in animation_names and len(animation_names) < 64:
                    animation_names.append(name)
            for node in row["nodes"]:
                name = node["name"]
                if name not in node_names and len(node_names) < 96:
                    node_names.append(name)
                for key in ("textOrValue", "resourceOrPath"):
                    value = node.get(key)
                    if value and value not in node_resource_refs and len(node_resource_refs) < 96:
                        node_resource_refs.append(value)

            if len(sample_rows) < 20:
                sample_rows.append({
                    "index": row_index,
                    "startOffset": format_offset(row["startOffset"]),
                    "rowFlag": row["rowFlag"],
                    "animationRefs": row["animations"],
                    "nodeMetaCount": row["nodeMetaCount"],
                    "layoutCount": row["layoutCount"],
                    "nodeNames": [node["name"] for node in row["nodes"]],
                    "nodeResourceRefs": [
                        value
                        for node in row["nodes"]
                        for value in (node.get("textOrValue"), node.get("resourceOrPath"))
                        if value
                    ][:12],
                    "layoutTailLength": len(tail),
                    "layoutTailStringSamples": tail_hits,
                })
            offset = next_offset

        if offset != len(data):
            return None
        if row_member_counts != Counter({DAMAGE_TEXT_ROW_MEMBER_COUNT: declared_rows}):
            return None
    except (ValueError, struct.error, UnicodeDecodeError):
        return None

    anim_summary = ",".join(f"{key}:{count}" for key, count in animation_count_by_row.most_common(6))
    node_summary = ",".join(f"{key}:{count}" for key, count in node_count_pairs.most_common(6))
    tail_summary = ",".join(f"{key}:{count}" for key, count in tail_length_counts.most_common(6))
    details = [
        f"rows={declared_rows}",
        f"charset={charset}",
        f"animationCounts={anim_summary}",
        f"nodeCounts={node_summary}",
    ]
    if tail_summary:
        details.append("tailLengths=" + tail_summary)
    if animation_names:
        details.append("sampleAnimations=" + ",".join(animation_names[:5]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "GPUISystemConfigDamageText",
        "summary": (
            "MemoryPack GPUISystemConfig damage_text; object member count 5; "
            f"{declared_rows} damage-text rows with exact animation/node metadata; exact length"
        ),
        "rows": declared_rows,
        "keys": [
            "charset",
            "animationRefs",
            "nodeNames",
            "nodeResourceRefs",
            "layoutTailLength",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": DAMAGE_TEXT_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": [
                "charset",
                "animationRefs",
                "nodeNames",
                "nodeResourceRefs",
                "layoutTailLength",
            ],
            "charset": charset,
            "declaredRowCount": declared_rows,
            "rowMemberCountMarkers": dict(sorted(row_member_counts.items())),
            "animationMemberCountMarkers": dict(sorted(animation_member_counts.items())),
            "nodeMemberCountMarkers": dict(sorted(node_member_counts.items())),
            "rowFlagCounts": dict(sorted(row_flags.items())),
            "animationCountByRow": dict(sorted(animation_count_by_row.items())),
            "nodeCountPairs": dict(node_count_pairs.most_common(32)),
            "tailLengthCounts": dict(tail_length_counts.most_common(32)),
            "animationRefs": animation_names,
            "nodeNames": node_names,
            "nodeResourceRefs": node_resource_refs,
            "sampleRows": sample_rows,
            "exactLength": True,
            "fileSize": size,
        },
    }

def decode_mission_area_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != MISSION_AREA_TABLE_REL:
        return None
    if not data or data[0] != 1:
        return None

    def read_ascii_id_at(offset: int, *, max_length: int = 96) -> tuple[str, int] | None:
        if offset + 4 > len(data):
            return None
        length = struct.unpack_from("<I", data, offset)[0]
        if length <= 0 or length > max_length or offset + 4 + length > len(data):
            return None
        raw = data[offset + 4:offset + 4 + length]
        try:
            value = raw.decode("ascii")
        except UnicodeDecodeError:
            return None
        if not all(ch.isalnum() or ch == "_" for ch in value):
            return None
        return value, offset + 4 + length

    def is_row_start(offset: int) -> bool:
        parsed = read_ascii_id_at(offset)
        if not parsed:
            return False
        key, cursor = parsed
        if cursor >= len(data) or data[cursor] != MISSION_AREA_VALUE_MEMBER_COUNT:
            return False
        cursor += 1
        if cursor >= len(data) or data[cursor] != 0:
            return False
        cursor += 1
        duplicate = read_ascii_id_at(cursor)
        return bool(duplicate and duplicate[0] == key)

    def find_next_row_start(min_offset: int) -> int | None:
        for candidate in range(max(min_offset, 0), len(data)):
            if is_row_start(candidate):
                return candidate
        return None

    try:
        offset = 1
        header_count0, offset = read_memorypack_u32_count(
            data,
            offset,
            "MissionAreaTable.headerCount0",
            max_count=128,
        )
        header_count1, offset = read_memorypack_u32_count(
            data,
            offset,
            "MissionAreaTable.headerCount1",
            max_count=10_000,
        )
        row_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "MissionAreaTable.rows",
            max_count=10_000,
        )
        if header_count0 != 1 or row_count <= 0:
            return None

        member_counts: Counter[int] = Counter()
        marker_counts: Counter[int] = Counter()
        flag_counts: Counter[int] = Counter()
        type_counts: Counter[int] = Counter()
        tail_length_counts: Counter[int] = Counter()
        duplicate_matches = 0
        rows: list[dict[str, Any]] = []
        first_keys: list[str] = []

        for row_index in range(row_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"MissionAreaTable[{row_index}].key",
                max_length=96,
            )
            if offset >= len(data):
                raise ValueError(f"MissionAreaTable[{row_index}].memberCount:truncated")
            member_count = data[offset]
            offset += 1
            member_counts[member_count] += 1
            if offset >= len(data):
                raise ValueError(f"MissionAreaTable[{row_index}].marker:truncated")
            string_marker = data[offset]
            offset += 1
            marker_counts[string_marker] += 1
            duplicate_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"MissionAreaTable[{row_index}].duplicateId",
                max_length=96,
            )
            if duplicate_id == key:
                duplicate_matches += 1

            if row_index + 1 < row_count:
                next_offset = find_next_row_start(offset + 60)
                if next_offset is None:
                    return None
            else:
                next_offset = len(data)
            tail = data[offset:next_offset]
            if len(tail) < 67:
                return None
            flag = tail[0]
            type_id = struct.unpack_from("<i", tail, 1)[0]
            values = [round(struct.unpack_from("<f", tail, 5 + index * 4)[0], 4) for index in range(10)]
            if not all(math.isfinite(value) and abs(value) < 10_000_000 for value in values):
                return None
            if flag not in {0, 1} or type_id not in {1, 2}:
                return None
            flag_counts[flag] += 1
            type_counts[type_id] += 1
            tail_length_counts[len(tail)] += 1
            if len(first_keys) < 16:
                first_keys.append(key)
            if len(rows) < 16:
                rows.append(
                    {
                        "key": key,
                        "duplicateId": duplicate_id,
                        "valueMemberCount": member_count,
                        "stringMarker": string_marker,
                        "flag": flag,
                        "typeId": type_id,
                        "primaryVec3": values[:3],
                        "secondaryVec3": values[3:6],
                        "sizeValues": values[6:10],
                        "tailLength": len(tail),
                        "extraTailLength": max(0, len(tail) - 67),
                        "tailMarkerPreview": tail[45:min(len(tail), 67)].hex(" "),
                    }
                )
            offset = next_offset

        if offset != len(data):
            return None
        if set(member_counts) != {MISSION_AREA_VALUE_MEMBER_COUNT}:
            return None
        if set(marker_counts) != {0}:
            return None
    except (ValueError, struct.error):
        return None

    tail_summary = ",".join(f"{key}:{count}" for key, count in tail_length_counts.most_common(6))
    type_summary = ",".join(f"{key}:{count}" for key, count in type_counts.most_common(6))
    details = [
        f"rows={row_count}",
        f"headerCount1={header_count1}",
        f"duplicateMatches={duplicate_matches}/{row_count}",
    ]
    if type_summary:
        details.append("types=" + type_summary)
    if tail_summary:
        details.append("tailLengths=" + tail_summary)
    if first_keys:
        details.append("sampleKeys=" + ",".join(first_keys[:4]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "GameplayConfigMissionAreaTable",
        "summary": (
            "MemoryPack GameplayConfigMissionAreaTable; object member count 1; "
            f"{row_count} mission-area rows with 8-member value records; exact length"
        ),
        "rows": row_count,
        "keys": [
            "key",
            "duplicateId",
            "flag",
            "typeId",
            "primaryVec3",
            "secondaryVec3",
            "sizeValues",
            "tailLength",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": 1,
            "format": "memorypack",
            "decodedPreviewFields": [
                "key",
                "duplicateId",
                "flag",
                "typeId",
                "primaryVec3",
                "secondaryVec3",
                "sizeValues",
                "tailLength",
            ],
            "headerCount0": header_count0,
            "headerCount1": header_count1,
            "entryCount": row_count,
            "valueMemberCountMarkers": dict(sorted(member_counts.items())),
            "stringMarkerCounts": dict(sorted(marker_counts.items())),
            "duplicateIdMatches": duplicate_matches,
            "flagCounts": dict(flag_counts.most_common(16)),
            "typeIdCounts": dict(type_counts.most_common(16)),
            "tailLengthCounts": dict(tail_length_counts.most_common(16)),
            "sampleRows": rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_subgame_instance_data_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != SUBGAME_INSTANCE_DATA_TABLE_REL:
        return None
    if not data or data[0] != SUBGAME_INSTANCE_ROOT_MEMBER_COUNT:
        return None

    def read_fixed(offset: int, length: int, field_name: str) -> tuple[bytes, int]:
        if offset + length > len(data):
            raise ValueError(f"{field_name}:truncated")
        return data[offset:offset + length], offset + length

    try:
        offset = 1
        entry_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "SubGameInstanceDataTable.entries",
            max_count=1_000,
        )
        member_counts: Counter[int] = Counter()
        failure_counts: Counter[str] = Counter()
        success_counts: Counter[str] = Counter()
        default_counts: Counter[str] = Counter()
        quit_button_counts: Counter[str] = Counter()
        short_hash_counts: Counter[str] = Counter()
        source_matches = 0
        rows: list[dict[str, Any]] = []

        for row_index in range(entry_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].key",
                max_length=160,
            )
            if offset >= len(data):
                raise ValueError(f"SubGameInstanceDataTable[{row_index}].memberCount:truncated")
            value_member_count = data[offset]
            offset += 1
            member_counts[value_member_count] += 1

            prefix_bytes, offset = read_fixed(offset, 28, f"SubGameInstanceDataTable[{row_index}].prefix")
            failure_text_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].failureTextId",
                max_length=160,
            )
            after_failure, offset = read_fixed(offset, 11, f"SubGameInstanceDataTable[{row_index}].afterFailure")
            source_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].sourceId",
                max_length=160,
            )
            after_source, offset = read_fixed(offset, 10, f"SubGameInstanceDataTable[{row_index}].afterSource")
            short_hash, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].shortHash",
                max_length=32,
            )
            if not re.fullmatch(r"[0-9A-Fa-f]{8}", short_hash):
                raise ValueError(f"SubGameInstanceDataTable[{row_index}].shortHash:unexpected")
            after_short_hash, offset = read_fixed(offset, 2, f"SubGameInstanceDataTable[{row_index}].afterShortHash")
            default_group, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].defaultGroup",
                max_length=160,
            )
            after_default, offset = read_fixed(offset, 9, f"SubGameInstanceDataTable[{row_index}].afterDefault")
            quit_button_text_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].quitButtonTextId",
                max_length=160,
            )
            after_quit, offset = read_fixed(offset, 10, f"SubGameInstanceDataTable[{row_index}].afterQuit")
            success_text_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"SubGameInstanceDataTable[{row_index}].successTextId",
                max_length=160,
            )
            tail_bytes, offset = read_fixed(offset, 10, f"SubGameInstanceDataTable[{row_index}].tail")

            if source_id == key:
                source_matches += 1
            failure_counts[failure_text_id] += 1
            success_counts[success_text_id] += 1
            default_counts[default_group] += 1
            quit_button_counts[quit_button_text_id] += 1
            short_hash_counts[short_hash] += 1
            if len(rows) < 12:
                rows.append(
                    {
                        "key": key,
                        "valueMemberCount": value_member_count,
                        "prefixU64": struct.unpack_from("<Q", prefix_bytes, 0)[0],
                        "prefixBytes": prefix_bytes.hex(" "),
                        "failureTextId": failure_text_id,
                        "sourceId": source_id,
                        "shortHash": short_hash,
                        "defaultGroup": default_group,
                        "quitButtonTextId": quit_button_text_id,
                        "successTextId": success_text_id,
                        "markerBytes": {
                            "afterFailure": after_failure.hex(" "),
                            "afterSource": after_source.hex(" "),
                            "afterShortHash": after_short_hash.hex(" "),
                            "afterDefault": after_default.hex(" "),
                            "afterQuit": after_quit.hex(" "),
                            "tail": tail_bytes.hex(" "),
                        },
                    }
                )

        if offset != len(data):
            return None
        if set(member_counts) != {SUBGAME_INSTANCE_VALUE_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    details = [f"rows={entry_count}", f"sourceMatches={source_matches}/{entry_count}"]
    if failure_counts:
        details.append("failure=" + ",".join(f"{key}:{count}" for key, count in failure_counts.most_common(3)))
    if success_counts:
        details.append("success=" + ",".join(f"{key}:{count}" for key, count in success_counts.most_common(3)))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 2:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "SubGameInstanceDataTable",
        "summary": (
            "MemoryPack SubGameInstanceDataTable; object member count 1; "
            f"{entry_count} keyed rows with 6-member value records; exact length"
        ),
        "rows": entry_count,
        "keys": [
            "key",
            "failureTextId",
            "sourceId",
            "shortHash",
            "defaultGroup",
            "quitButtonTextId",
            "successTextId",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": SUBGAME_INSTANCE_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": [
                "key",
                "failureTextId",
                "sourceId",
                "shortHash",
                "defaultGroup",
                "quitButtonTextId",
                "successTextId",
                "markerBytes",
            ],
            "entryCount": entry_count,
            "valueMemberCountMarkers": dict(sorted(member_counts.items())),
            "sourceIdMatchesKey": source_matches,
            "failureTextIdCounts": dict(failure_counts.most_common(16)),
            "successTextIdCounts": dict(success_counts.most_common(16)),
            "defaultGroupCounts": dict(default_counts.most_common(16)),
            "quitButtonTextIdCounts": dict(quit_button_counts.most_common(16)),
            "shortHashCounts": dict(short_hash_counts.most_common(16)),
            "sampleRows": rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_matrix_shock_wave_beat_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != MATRIX_SHOCK_WAVE_BEAT_REL:
        return None
    if not data or data[0] != MATRIX_SHOCK_WAVE_ROOT_MEMBER_COUNT:
        return None

    try:
        offset = 1
        root_float_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "MatrixShockWaveBeatConfigTable.rootFloats",
            max_count=128,
        )
        root_floats: list[float] = []
        for _index in range(root_float_count):
            value, offset = read_memorypack_f32(data, offset)
            if not math.isfinite(value):
                raise ValueError("MatrixShockWaveBeatConfigTable.rootFloats:non-finite")
            root_floats.append(round(value, 4))

        section_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "MatrixShockWaveBeatConfigTable.sections",
            max_count=128,
        )
        sections: list[dict[str, Any]] = []
        row_member_counts: Counter[int] = Counter()
        point_member_counts: Counter[int] = Counter()
        point_count_counts: Counter[int] = Counter()
        final_float_counts: Counter[str] = Counter()
        total_rows = 0
        total_points = 0

        for section_index in range(section_count):
            start_float, offset = read_memorypack_f32(data, offset)
            end_float, offset = read_memorypack_f32(data, offset)
            if not math.isfinite(start_float) or not math.isfinite(end_float):
                raise ValueError(f"MatrixShockWaveBeatConfigTable.sections[{section_index}]:non-finite-range")
            row_count, offset = read_memorypack_u32_count(
                data,
                offset,
                f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows",
                max_count=2_000,
            )
            rows: list[dict[str, Any]] = []
            for row_index in range(row_count):
                key, offset = require_memorypack_non_null_string(
                    data,
                    offset,
                    f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].key",
                    max_length=64,
                )
                if not re.fullmatch(r"[0-9A-F]{8}", key):
                    raise ValueError(f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].key:unexpected")
                if offset >= len(data):
                    raise ValueError(f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].memberCount:truncated")
                row_member_count = data[offset]
                offset += 1
                row_member_counts[row_member_count] += 1
                point_count, offset = read_memorypack_u32_count(
                    data,
                    offset,
                    f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].points",
                    max_count=64,
                )
                points: list[dict[str, Any]] = []
                for point_index in range(point_count):
                    if offset >= len(data):
                        raise ValueError(
                            f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].points[{point_index}].memberCount:truncated"
                        )
                    point_member_count = data[offset]
                    offset += 1
                    point_member_counts[point_member_count] += 1
                    x_value, offset = read_memorypack_f32(data, offset)
                    y_value, offset = read_memorypack_f32(data, offset)
                    if offset + 4 > len(data):
                        raise ValueError(
                            f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].points[{point_index}].field2:truncated"
                        )
                    field2_u32 = struct.unpack_from("<I", data, offset)[0]
                    field2_f32 = struct.unpack_from("<f", data, offset)[0]
                    offset += 4
                    if not math.isfinite(x_value) or not math.isfinite(y_value) or abs(x_value) > 10_000 or abs(y_value) > 10_000:
                        raise ValueError(
                            f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].points[{point_index}]:non-finite"
                        )
                    if len(points) < 6:
                        point = {
                            "memberCount": point_member_count,
                            "x": round(x_value, 4),
                            "y": round(y_value, 4),
                            "field2U32": field2_u32,
                        }
                        if field2_u32 != 0 and math.isfinite(field2_f32) and abs(field2_f32) > 0.001:
                            point["field2Float"] = round(field2_f32, 4)
                        points.append(point)
                final_float, offset = read_memorypack_f32(data, offset)
                if not math.isfinite(final_float) or abs(final_float) > 100_000:
                    raise ValueError(f"MatrixShockWaveBeatConfigTable.sections[{section_index}].rows[{row_index}].finalFloat:non-finite")
                final_float_key = f"{round(final_float, 4):g}"
                final_float_counts[final_float_key] += 1
                point_count_counts[point_count] += 1
                total_rows += 1
                total_points += point_count
                if len(rows) < 16:
                    rows.append(
                        {
                            "key": key,
                            "rowMemberCount": row_member_count,
                            "pointCount": point_count,
                            "pointsPreview": points,
                            "finalFloat": round(final_float, 4),
                        }
                    )
            sections.append(
                {
                    "sectionIndex": section_index,
                    "startFloat": round(start_float, 4),
                    "endFloat": round(end_float, 4),
                    "rowCount": row_count,
                    "sampleRows": rows,
                }
            )

        if offset != len(data):
            return None
        if set(row_member_counts) != {MATRIX_SHOCK_WAVE_ROW_MEMBER_COUNT}:
            return None
        if set(point_member_counts) != {MATRIX_SHOCK_WAVE_POINT_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    details = [
        "rootFloats=" + ",".join(f"{value:g}" for value in root_floats),
        f"sections={section_count}",
        f"rows={total_rows}",
        f"points={total_points}",
    ]
    final_summary = ",".join(f"{key}:{count}" for key, count in final_float_counts.most_common(6))
    if final_summary:
        details.append("finalFloats=" + final_summary)
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "MatrixShockWaveBeatConfigTable",
        "summary": (
            "MemoryPack MatrixShockWaveBeatConfigTable; object member count 2; "
            f"{section_count} section(s), {total_rows} hash-key rows, {total_points} points; "
            "exact length"
        ),
        "rows": total_rows,
        "keys": ["key", "pointCount", "points", "finalFloat"],
        "sample": sample,
        "decoded": {
            "memberCount": MATRIX_SHOCK_WAVE_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": ["rootFloats", "sections", "key", "pointsPreview", "finalFloat"],
            "rootFloats": root_floats,
            "sectionCount": section_count,
            "totalRows": total_rows,
            "totalPoints": total_points,
            "rowMemberCountMarkers": dict(sorted(row_member_counts.items())),
            "pointMemberCountMarkers": dict(sorted(point_member_counts.items())),
            "pointCountCounts": dict(point_count_counts.most_common(16)),
            "finalFloatCounts": dict(final_float_counts.most_common(16)),
            "sections": sections,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_bamboo_raft_task_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != BAMBOO_RAFT_TASK_TABLE_REL:
        return None
    if not data or data[0] != BAMBOO_RAFT_TASK_ROOT_MEMBER_COUNT:
        return None

    try:
        offset = 1
        entry_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "BambooRaftTaskTable.entries",
            max_count=512,
        )
        value_member_counts: Counter[int] = Counter()
        task_member_counts: Counter[int] = Counter()
        field0_counts: Counter[int] = Counter()
        task_count_counts: Counter[int] = Counter()
        task_tail_counts: Counter[int] = Counter()
        tail_u64_counts: Counter[int] = Counter()
        duplicate_matches = 0
        total_task_refs = 0
        rows: list[dict[str, Any]] = []

        for row_index in range(entry_count):
            if offset + 8 > len(data):
                raise ValueError(f"BambooRaftTaskTable[{row_index}].header:truncated")
            hash_u32 = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            field0_u32 = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            if offset >= len(data):
                raise ValueError(f"BambooRaftTaskTable[{row_index}].memberCount:truncated")
            value_member_count = data[offset]
            offset += 1
            value_member_counts[value_member_count] += 1
            task_count, offset = read_memorypack_u32_count(
                data,
                offset,
                f"BambooRaftTaskTable[{row_index}].tasks",
                max_count=128,
            )
            tasks: list[dict[str, Any]] = []
            for task_index in range(task_count):
                task_id, offset = require_memorypack_non_null_string(
                    data,
                    offset,
                    f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].taskId",
                    max_length=96,
                )
                if offset >= len(data):
                    raise ValueError(f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].memberCount:truncated")
                task_member_count = data[offset]
                offset += 1
                task_member_counts[task_member_count] += 1
                duplicate_id, offset = require_memorypack_non_null_string(
                    data,
                    offset,
                    f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].duplicateId",
                    max_length=96,
                )
                if offset + 4 > len(data):
                    raise ValueError(f"BambooRaftTaskTable[{row_index}].tasks[{task_index}].tail:truncated")
                task_tail = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                if duplicate_id == task_id:
                    duplicate_matches += 1
                task_tail_counts[task_tail] += 1
                if len(tasks) < 8:
                    tasks.append(
                        {
                            "taskId": task_id,
                            "memberCount": task_member_count,
                            "duplicateId": duplicate_id,
                            "tailU32": task_tail,
                        }
                    )
            if offset + 8 > len(data):
                raise ValueError(f"BambooRaftTaskTable[{row_index}].tail:truncated")
            tail_u64 = struct.unpack_from("<Q", data, offset)[0]
            offset += 8
            field0_counts[field0_u32] += 1
            task_count_counts[task_count] += 1
            tail_u64_counts[tail_u64] += 1
            total_task_refs += task_count
            if len(rows) < 16:
                rows.append(
                    {
                        "hashU32": hash_u32,
                        "field0U32": field0_u32,
                        "valueMemberCount": value_member_count,
                        "taskCount": task_count,
                        "taskRefs": tasks,
                        "tailU64": tail_u64,
                    }
                )

        if offset != len(data):
            return None
        if set(value_member_counts) != {BAMBOO_RAFT_TASK_VALUE_MEMBER_COUNT}:
            return None
        if set(task_member_counts) != {BAMBOO_RAFT_TASK_REF_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    field0_summary = ",".join(f"{key}:{count}" for key, count in field0_counts.most_common(6))
    task_summary = ",".join(f"{key}:{count}" for key, count in task_count_counts.most_common(6))
    details = [f"rows={entry_count}", f"taskRefs={total_task_refs}"]
    if field0_summary:
        details.append("field0=" + field0_summary)
    if task_summary:
        details.append("taskCounts=" + task_summary)
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "BambooRaftTaskTable",
        "summary": (
            "MemoryPack BambooRaftTaskTable; object member count 1; "
            f"{entry_count} rows, {total_task_refs} duplicated task refs; exact length"
        ),
        "rows": entry_count,
        "keys": ["hashU32", "field0U32", "taskRefs", "tailU64"],
        "sample": sample,
        "decoded": {
            "memberCount": BAMBOO_RAFT_TASK_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": ["hashU32", "field0U32", "taskRefs", "tailU64"],
            "entryCount": entry_count,
            "totalTaskRefs": total_task_refs,
            "duplicateIdMatches": duplicate_matches,
            "valueMemberCountMarkers": dict(sorted(value_member_counts.items())),
            "taskMemberCountMarkers": dict(sorted(task_member_counts.items())),
            "field0Counts": dict(field0_counts.most_common(16)),
            "taskCountCounts": dict(task_count_counts.most_common(16)),
            "taskTailCounts": dict(task_tail_counts.most_common(16)),
            "tailU64Counts": dict(tail_u64_counts.most_common(16)),
            "sampleRows": rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_luna_area_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    parts = rel.split("/")
    if len(parts) < 4 or parts[0] != "Json" or parts[1] != "NavMesh" or parts[-1] != "LunaArea.json":
        return None
    if not data or data[0] != 1:
        return None

    try:
        offset = 1
        area_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "LunaArea",
            max_count=10_000,
        )
        marker_counts: Counter[int] = Counter()
        area_id_counts: Counter[int] = Counter()
        vertex_count_counts: Counter[int] = Counter()
        tail_u32_counts: Counter[int] = Counter()
        tail_u64_samples: list[int] = []
        rows: list[dict[str, Any]] = []
        total_vertices = 0
        max_vertices = 0
        for index in range(area_count):
            if offset >= len(data):
                raise ValueError(f"LunaArea[{index}].memberCount:truncated")
            row_member_count = data[offset]
            offset += 1
            marker_counts[row_member_count] += 1
            area_id, offset = read_memorypack_i32(data, offset)
            center, offset = read_memorypack_vec2(data, offset)
            vertex_count, offset = read_memorypack_u32_count(
                data,
                offset,
                f"LunaArea[{index}].vertices",
                max_count=2_000,
            )
            vertices: list[list[float]] = []
            for _vertex_index in range(vertex_count):
                vertex, offset = read_memorypack_vec3(data, offset)
                if len(vertices) < 4:
                    vertices.append(vertex)
            if offset + 12 > len(data):
                raise ValueError(f"LunaArea[{index}].tail:truncated")
            tail_u64 = struct.unpack_from("<Q", data, offset)[0]
            offset += 8
            tail_u32 = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            if not all(math.isfinite(float(value)) for value in center):
                raise ValueError(f"LunaArea[{index}].center:non-finite")
            if not all(math.isfinite(float(value)) for vertex in vertices for value in vertex):
                raise ValueError(f"LunaArea[{index}].vertices:non-finite")
            area_id_counts[area_id] += 1
            vertex_count_counts[vertex_count] += 1
            tail_u32_counts[tail_u32] += 1
            if len(tail_u64_samples) < 16:
                tail_u64_samples.append(tail_u64)
            total_vertices += vertex_count
            max_vertices = max(max_vertices, vertex_count)
            if len(rows) < 12:
                rows.append(
                    {
                        "areaId": area_id,
                        "rowMemberCount": row_member_count,
                        "center": center,
                        "vertexCount": vertex_count,
                        "verticesPreview": vertices,
                        "tailU64": tail_u64,
                        "tailU32": tail_u32,
                    }
                )

        if offset != len(data):
            return None
        if set(marker_counts) != {LUNA_AREA_ROW_MEMBER_COUNT}:
            return None
    except (ValueError, struct.error):
        return None

    area_summary = ",".join(f"{key}:{count}" for key, count in area_id_counts.most_common(4))
    vertex_summary = ",".join(f"{key}:{count}" for key, count in vertex_count_counts.most_common(4))
    tail_summary = ",".join(f"{key}:{count}" for key, count in tail_u32_counts.most_common(4))
    details = [
        f"areas={area_count}",
        f"vertices={total_vertices}",
        f"maxVertices={max_vertices}",
    ]
    if area_summary:
        details.append("areaIds=" + area_summary)
    if vertex_summary:
        details.append("vertexCounts=" + vertex_summary)
    if tail_summary:
        details.append("tailU32=" + tail_summary)
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "LunaArea",
        "summary": (
            "MemoryPack LunaArea; object member count 1; "
            f"{area_count} polygon area rows; {total_vertices} vertices; "
            "exact length"
        ),
        "rows": area_count,
        "keys": [
            "areaId",
            "center",
            "vertexCount",
            "vertices",
            "tailU64",
            "tailU32",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": 1,
            "format": "memorypack",
            "decodedPreviewFields": [
                "areaId",
                "center",
                "vertexCount",
                "verticesPreview",
                "tailU64",
                "tailU32",
            ],
            "areaCount": area_count,
            "totalVertices": total_vertices,
            "maxVertices": max_vertices,
            "rowMemberCountMarkers": dict(sorted(marker_counts.items())),
            "areaIdCounts": dict(area_id_counts.most_common(16)),
            "vertexCountCounts": dict(vertex_count_counts.most_common(16)),
            "tailU32Counts": dict(tail_u32_counts.most_common(16)),
            "tailU64Samples": tail_u64_samples,
            "sampleRows": rows,
            "exactLength": True,
            "fileSize": size,
        },
    }


def parse_navmesh_state_record_field(
    data: bytes,
    offset: int,
    count: int,
    record_kind: str,
) -> tuple[int, list[dict[str, Any]]] | None:
    rows: list[dict[str, Any]] = []
    if record_kind == "bounds36":
        row_size = 36
        if offset + count * row_size > len(data):
            return None
        for _index in range(count):
            key = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            area_id = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            kind = struct.unpack_from("<i", data, offset)[0]
            offset += 4
            values = [round(struct.unpack_from("<f", data, offset + index * 4)[0], 4) for index in range(6)]
            offset += 24
            if not all(math.isfinite(value) and abs(value) < 100_000_000 for value in values):
                return None
            rows.append({"key": key, "areaId": area_id, "kind": kind, "boundsValues": values})
        return offset, rows

    if record_kind in {"ints16", "ints20"}:
        int_count = 4 if record_kind == "ints16" else 5
        row_size = int_count * 4
        if offset + count * row_size > len(data):
            return None
        for _index in range(count):
            values = [struct.unpack_from("<i", data, offset + index * 4)[0] for index in range(int_count)]
            offset += row_size
            rows.append({"values": values})
        return offset, rows

    if record_kind == "groupedU64Lists":
        for _group_index in range(count):
            if offset + 12 > len(data):
                return None
            key, field0, sublist_count = struct.unpack_from("<III", data, offset)
            offset += 12
            if key < 100_000_000 or field0 > 10 or sublist_count > 64:
                return None
            lists: list[dict[str, Any]] = []
            total_ids = 0
            for _list_index in range(sublist_count):
                if offset + 8 > len(data):
                    return None
                list_index, item_count = struct.unpack_from("<II", data, offset)
                offset += 8
                if list_index > 128 or item_count > 512 or offset + item_count * 8 > len(data):
                    return None
                ids: list[int] = []
                for item_index in range(item_count):
                    value = struct.unpack_from("<Q", data, offset + item_index * 8)[0]
                    if value == 0 or value > 0xFFFFFFFF:
                        return None
                    if len(ids) < 8:
                        ids.append(value)
                offset += item_count * 8
                total_ids += item_count
                if len(lists) < 8:
                    lists.append({"index": list_index, "count": item_count, "idsPreview": ids})
            rows.append({
                "key": key,
                "field0": field0,
                "sublistCount": sublist_count,
                "totalIds": total_ids,
                "lists": lists,
            })
        return offset, rows

    if record_kind == "idValueLists":
        for _index in range(count):
            if offset + 12 > len(data):
                return None
            key = struct.unpack_from("<Q", data, offset)[0]
            offset += 8
            value_count = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            if key == 0 or key > 0xFFFFFFFF or value_count > 32 or offset + value_count * 4 > len(data):
                return None
            values = [struct.unpack_from("<I", data, offset + index * 4)[0] for index in range(value_count)]
            if any(value > 100_000 for value in values):
                return None
            offset += value_count * 4
            rows.append({"key": key, "valueCount": value_count, "values": values[:12]})
        return offset, rows

    return None


def find_navmesh_state_container_parse(
    data: bytes,
    offset: int,
    field_index: int,
    fields: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    if field_index == NAVMESH_STATE_CONTAINER_MEMBER_COUNT:
        return fields if offset == len(data) else None
    if offset + 4 > len(data):
        return None
    count = struct.unpack_from("<I", data, offset)[0]
    if count > 1_000:
        return None
    value_offset = offset + 4
    if count == 0:
        decoded = {
            "fieldIndex": field_index + 1,
            "recordKind": "empty",
            "count": 0,
            "sampleRows": [],
        }
        return find_navmesh_state_container_parse(data, value_offset, field_index + 1, fields + [decoded])

    for record_kind in ("bounds36", "ints20", "ints16", "groupedU64Lists", "idValueLists"):
        parsed = parse_navmesh_state_record_field(data, value_offset, count, record_kind)
        if not parsed:
            continue
        next_offset, rows = parsed
        decoded = {
            "fieldIndex": field_index + 1,
            "recordKind": record_kind,
            "count": count,
            "sampleRows": rows[:8],
        }
        result = find_navmesh_state_container_parse(data, next_offset, field_index + 1, fields + [decoded])
        if result is not None:
            return result
    return None





def dialog_id_table_row_start(data: bytes, offset: int) -> str | None:
    if offset + 5 > len(data):
        return None
    length = struct.unpack_from("<I", data, offset)[0]
    if length < 5 or length > 140 or offset + 4 + length >= len(data):
        return None
    try:
        key = data[offset + 4:offset + 4 + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not DIALOG_ID_TABLE_KEY_RE.match(key):
        return None
    if data[offset + 4 + length] != DIALOG_ID_TABLE_BRIEF_MEMBER_COUNT:
        return None
    return key


def parse_dialog_id_table_int_string_map(data: bytes, offset: int, field_name: str, *, max_count: int = 20_000) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=max_count)
    rows: list[dict[str, Any]] = []
    key_min: int | None = None
    key_max: int | None = None
    for row_index in range(count):
        row_offset = offset
        value, offset = read_memorypack_i32(data, offset)
        text, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{row_index}].value",
            max_length=220,
        )
        if key_min is None or value < key_min:
            key_min = value
        if key_max is None or value > key_max:
            key_max = value
        if len(rows) < 8 or row_index >= count - 3:
            rows.append({"index": row_index, "offset": format_offset(row_offset), "key": value, "value": text})
    return {
        "count": count,
        "keyMin": key_min,
        "keyMax": key_max,
        "sampleRows": rows[:16],
    }, offset


def parse_dialog_id_table_string_int_map(data: bytes, offset: int, field_name: str, *, max_count: int = 20_000) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=max_count)
    rows: list[dict[str, Any]] = []
    value_counts: Counter[int] = Counter()
    key_prefix_counts: Counter[str] = Counter()
    for row_index in range(count):
        row_offset = offset
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{row_index}].key",
            max_length=220,
        )
        value, offset = read_memorypack_i32(data, offset)
        value_counts[value] += 1
        prefix = "option" if key.startswith("option_dlg_") else key.split("_", 1)[0]
        key_prefix_counts[prefix] += 1
        if len(rows) < 8 or row_index >= count - 3:
            rows.append({"index": row_index, "offset": format_offset(row_offset), "key": key, "value": value})
    return {
        "count": count,
        "valueMin": min(value_counts) if value_counts else None,
        "valueMax": max(value_counts) if value_counts else None,
        "keyPrefixCounts": dict(key_prefix_counts.most_common(12)),
        "sampleRows": rows[:16],
    }, offset


def dialog_id_table_counter_to_json(counter: Counter[Any], limit: int = 24) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, count in counter.most_common(limit):
        if key is None or key == MEMORYPACK_NULL_COUNT:
            out_key = "null"
        elif isinstance(key, bool):
            out_key = "true" if key else "false"
        else:
            out_key = str(key)
        out[out_key] = count
    return out


def parse_dialog_id_table_lang_key(data: bytes, offset: int, field_name: str) -> tuple[dict[str, Any], int]:
    if offset >= len(data):
        raise ValueError(f"{field_name}:truncated-member-count")
    member_count = data[offset]
    offset += 1
    if member_count == (MEMORYPACK_NULL_COUNT & 0xFF):
        return {"memberCount": None, "value": None}, offset
    if member_count != 1:
        raise ValueError(f"{field_name}:unexpected-member-count={member_count}")
    value, offset = require_memorypack_string(data, offset, f"{field_name}.value")
    return {"memberCount": member_count, "value": value}, offset


def parse_dialog_id_table_string_list(data: bytes, offset: int, field_name: str, *, max_count: int = 256) -> tuple[dict[str, Any], int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field_name}:truncated-count")
    count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if count == MEMORYPACK_NULL_COUNT:
        return {"count": None, "values": []}, offset
    if count > max_count:
        raise ValueError(f"{field_name}:invalid-count={count}")
    values: list[str] = []
    for index in range(count):
        value, offset = require_memorypack_non_null_string(data, offset, f"{field_name}[{index}]", max_length=220)
        values.append(value)
    return {"count": count, "values": values}, offset


def parse_dialog_id_table_mask_segment(segment: bytes, field_name: str) -> dict[str, Any]:
    if segment == bytes([MEMORYPACK_NULL_COUNT & 0xFF]):
        return {"isNull": True, "byteLength": 1}
    if len(segment) < 15 or segment[0] != 6:
        raise ValueError(f"{field_name}:not-common-mask")
    curve = segment[2:-13]
    if not curve:
        raise ValueError(f"{field_name}.curve:empty")
    fade_in = struct.unpack_from("<f", segment, len(segment) - 13)[0]
    fade_out = struct.unpack_from("<f", segment, len(segment) - 9)[0]
    mask_type = struct.unpack_from("<i", segment, len(segment) - 5)[0]
    use_curve_byte = segment[-1]
    if not math.isfinite(fade_in) or not math.isfinite(fade_out):
        raise ValueError(f"{field_name}.fade:non-finite")
    if abs(fade_in) > 120 or abs(fade_out) > 120:
        raise ValueError(f"{field_name}.fade:out-of-range")
    if mask_type < 0 or mask_type > 16:
        raise ValueError(f"{field_name}.maskType:out-of-range={mask_type}")
    if use_curve_byte not in (0, 1):
        raise ValueError(f"{field_name}.useCurve:invalid={use_curve_byte}")
    return {
        "isNull": False,
        "byteLength": len(segment),
        "memberCount": segment[0],
        "audioBlackScreenBehaviour": segment[1],
        "curveByteLength": len(curve),
        "curvePrefixHex": curve[:12].hex(),
        "fadeInDuration": round(fade_in, 4),
        "fadeOutDuration": round(fade_out, 4),
        "maskType": mask_type,
        "useCurve": bool(use_curve_byte),
    }


def split_dialog_id_table_masks(prefix: bytes, field_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for split in range(1, len(prefix)):
        try:
            after_mask = parse_dialog_id_table_mask_segment(prefix[:split], f"{field_name}.afterMaskBlendData")
            before_mask = parse_dialog_id_table_mask_segment(prefix[split:], f"{field_name}.beforeMaskBlendData")
        except (ValueError, struct.error):
            continue
        matches.append((after_mask, before_mask))
    if len(matches) != 1:
        raise ValueError(f"{field_name}.maskPrefix:ambiguous-splits={len(matches)}")
    return matches[0]


def parse_dialog_brief_info_payload(payload: bytes, key: str, field_name: str) -> dict[str, Any]:
    marker = struct.pack("<I", len(key.encode("utf-8"))) + key.encode("utf-8")
    search_from = 0
    last_error = "duplicate-dialogId:not-found"
    while True:
        dialog_id_offset = payload.find(marker, search_from)
        if dialog_id_offset < 0:
            break
        try:
            after_mask, before_mask = split_dialog_id_table_masks(payload[:dialog_id_offset], field_name)
            offset = dialog_id_offset
            dialog_id, offset = require_memorypack_non_null_string(payload, offset, f"{field_name}.dialogId", max_length=220)
            if dialog_id != key:
                raise ValueError(f"{field_name}.dialogId:mismatch")
            dialog_type, offset = read_memorypack_i32(payload, offset)
            if dialog_type < 0 or dialog_type > 32:
                raise ValueError(f"{field_name}.dialogType:out-of-range={dialog_type}")
            interact_text, offset = parse_dialog_id_table_lang_key(payload, offset, f"{field_name}.interactText")
            npc_proxy_ids, offset = parse_dialog_id_table_string_list(payload, offset, f"{field_name}.npcProxyIds")
            if offset >= len(payload):
                raise ValueError(f"{field_name}.useBlackScreen:truncated")
            use_black_screen_byte = payload[offset]
            offset += 1
            if use_black_screen_byte not in (0, 1):
                raise ValueError(f"{field_name}.useBlackScreen:invalid={use_black_screen_byte}")
            if offset != len(payload):
                raise ValueError(f"{field_name}:trailing-bytes={len(payload) - offset}")
            return {
                "maskPrefixLength": dialog_id_offset,
                "afterMaskBlendData": after_mask,
                "beforeMaskBlendData": before_mask,
                "dialogId": dialog_id,
                "dialogType": dialog_type,
                "interactText": interact_text["value"],
                "interactTextMemberCount": interact_text["memberCount"],
                "npcProxyIdCount": npc_proxy_ids["count"],
                "npcProxyIds": npc_proxy_ids["values"],
                "useBlackScreen": bool(use_black_screen_byte),
            }
        except (UnicodeDecodeError, struct.error, ValueError) as exc:
            last_error = str(exc)
            search_from = dialog_id_offset + 1
    raise ValueError(f"{field_name}:{last_error}")


def summarize_dialog_id_table_registry(data: bytes) -> dict[str, Any]:
    all_ids = sorted({match.group().decode("ascii") for match in DIALOG_ID_TABLE_RAW_ID_RE.finditer(data)})
    option_ids = sorted({match.group().decode("ascii") for match in DIALOG_ID_TABLE_OPTION_RAW_RE.finditer(data)})

    per_line_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    options_by_scene: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    root_keys: set[str] = set()
    for ident in all_ids:
        if ident.startswith("radio_"):
            root_keys.add(ident)
            continue
        match = DIALOG_ID_TABLE_LINE_RE.match(ident)
        if match:
            per_line_by_scene[match.group("scene")][int(match.group("trunk"))].append(ident)
        else:
            root_keys.add(ident)
    for ident in option_ids:
        match = DIALOG_ID_TABLE_OPTION_RE.match(ident)
        if match:
            options_by_scene[match.group("scene")][int(match.group("group"))].append(ident)

    all_scenes = root_keys | set(per_line_by_scene)
    with_decomp = 0
    multi_trunk = 0
    root_only = 0
    with_options = 0
    option_count = 0
    line_count = 0
    for scene in all_scenes:
        trunks = per_line_by_scene.get(scene, {})
        trunk_count = len(trunks)
        scene_line_count = sum(len(values) for values in trunks.values())
        option_groups = options_by_scene.get(scene, {})
        scene_option_count = sum(len(values) for values in option_groups.values())
        line_count += scene_line_count
        option_count += scene_option_count
        if trunk_count > 0:
            with_decomp += 1
        else:
            root_only += 1
        if trunk_count > 1:
            multi_trunk += 1
        if scene_option_count > 0:
            with_options += 1
    return {
        "registeredSceneCount": len(all_scenes),
        "rootKeyCount": len(root_keys),
        "lineIdCount": line_count,
        "optionIdCount": option_count,
        "withTrunkLineDecomposition": with_decomp,
        "multiTrunkSceneCount": multi_trunk,
        "rootOnlySceneCount": root_only,
        "withOptionsSceneCount": with_options,
        "radioSceneCount": sum(1 for key in all_scenes if key.startswith("radio_")),
    }


def decode_dialog_id_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != DIALOG_ID_TABLE_REL:
        return None
    if not data or data[0] != DIALOG_ID_TABLE_ROOT_MEMBER_COUNT:
        return None

    try:
        offset = 1
        brief_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "dialogBriefInfoDict",
            max_count=20_000,
        )
        starts: list[tuple[int, str]] = []
        for candidate in range(offset, len(data) - 5):
            key = dialog_id_table_row_start(data, candidate)
            if key is not None:
                starts.append((candidate, key))
                if len(starts) >= brief_count + 1:
                    break
        if len(starts) < brief_count or starts[0][0] != offset:
            raise ValueError("dialogBriefInfoDict.rowStarts:not-found")

        last_start = starts[brief_count - 1][0]
        search_end = starts[brief_count][0] if len(starts) > brief_count else len(data)
        field2_offset: int | None = None
        for candidate in range(last_start + 1, search_end):
            if candidate + 4 > len(data):
                break
            if struct.unpack_from("<I", data, candidate)[0] != brief_count:
                continue
            try:
                _field2_probe, probe_offset = parse_dialog_id_table_int_string_map(
                    data,
                    candidate,
                    "dialogIdByIntIdProbe",
                    max_count=20_000,
                )
            except (UnicodeDecodeError, struct.error, ValueError):
                continue
            if probe_offset <= len(data):
                field2_offset = candidate
                break
        if field2_offset is None:
            raise ValueError("dialogBriefInfoDict.end:not-found")

        brief_rows: list[dict[str, Any]] = []
        interesting_brief_rows: list[dict[str, Any]] = []
        payload_length_counts: Counter[int] = Counter()
        duplicate_key_matches = 0
        brief_key_prefix_counts: Counter[str] = Counter()
        brief_mask_prefix_length_counts: Counter[int] = Counter()
        brief_mask_length_counts: Counter[str] = Counter()
        brief_dialog_type_counts: Counter[int] = Counter()
        brief_interact_text_counts: Counter[str | None] = Counter()
        brief_npc_proxy_count_counts: Counter[int | None] = Counter()
        brief_use_black_screen_counts: Counter[bool] = Counter()
        brief_mask_field_counts: dict[str, Counter[Any]] = defaultdict(Counter)
        dialog_brief_info_parsed_count = 0
        for row_index, (row_start, key) in enumerate(starts[:brief_count]):
            row_end = starts[row_index + 1][0] if row_index + 1 < brief_count else field2_offset
            key_length = struct.unpack_from("<I", data, row_start)[0]
            payload_start = row_start + 4 + key_length + 1
            if row_end < payload_start:
                raise ValueError(f"dialogBriefInfoDict[{row_index}].payload:negative")
            payload = data[payload_start:row_end]
            payload_length_counts[len(payload)] += 1
            parsed_brief = parse_dialog_brief_info_payload(payload, key, f"dialogBriefInfoDict[{row_index}]")
            dialog_brief_info_parsed_count += 1
            if parsed_brief["dialogId"] == key:
                duplicate_key_matches += 1
            prefix = "radio" if key.startswith("radio_") else key.split("_", 2)[1] if key.startswith("dlg_") and len(key.split("_", 2)) > 1 else key.split("_", 1)[0]
            brief_key_prefix_counts[prefix] += 1
            brief_mask_prefix_length_counts[parsed_brief["maskPrefixLength"]] += 1
            after_mask = parsed_brief["afterMaskBlendData"]
            before_mask = parsed_brief["beforeMaskBlendData"]
            brief_mask_length_counts[f"after:{after_mask['byteLength']}|before:{before_mask['byteLength']}"] += 1
            brief_dialog_type_counts[parsed_brief["dialogType"]] += 1
            brief_interact_text_counts[parsed_brief["interactText"]] += 1
            brief_npc_proxy_count_counts[parsed_brief["npcProxyIdCount"]] += 1
            brief_use_black_screen_counts[parsed_brief["useBlackScreen"]] += 1
            for side, mask in (("afterMaskBlendData", after_mask), ("beforeMaskBlendData", before_mask)):
                brief_mask_field_counts[f"{side}.isNull"][mask["isNull"]] += 1
                brief_mask_field_counts[f"{side}.byteLength"][mask["byteLength"]] += 1
                if not mask["isNull"]:
                    for field in (
                        "audioBlackScreenBehaviour",
                        "curveByteLength",
                        "fadeInDuration",
                        "fadeOutDuration",
                        "maskType",
                        "useCurve",
                    ):
                        brief_mask_field_counts[f"{side}.{field}"][mask[field]] += 1
            row_preview = {
                "key": key,
                "offset": format_offset(row_start),
                "payloadLength": len(payload),
                "dialogType": parsed_brief["dialogType"],
                "interactText": parsed_brief["interactText"],
                "npcProxyIdCount": parsed_brief["npcProxyIdCount"],
                "npcProxyIds": parsed_brief["npcProxyIds"][:8],
                "useBlackScreen": parsed_brief["useBlackScreen"],
                "afterMaskBlendData": after_mask,
                "beforeMaskBlendData": before_mask,
            }
            if len(brief_rows) < 16:
                string_hits = scan_length_prefixed_utf8_string_hits(
                    payload,
                    max_samples=8,
                    min_length=3,
                    max_length=160,
                )
                row_preview["stringSamples"] = [hit["value"] for hit in string_hits[:6]]
                brief_rows.append(row_preview)
            has_variant_mask = after_mask["byteLength"] not in (1, 31) or before_mask["byteLength"] not in (1, 31)
            has_non_default_text = parsed_brief["interactText"] is not None
            has_null_mask = after_mask["isNull"] or before_mask["isNull"]
            if len(interesting_brief_rows) < 16 and (has_variant_mask or has_non_default_text or has_null_mask):
                interesting_brief_rows.append(row_preview)

        offset = field2_offset
        field2, offset = parse_dialog_id_table_int_string_map(data, offset, "dialogIdByIntId")
        field3, offset = parse_dialog_id_table_int_string_map(data, offset, "optionIdByIntId")
        field4, offset = parse_dialog_id_table_string_int_map(data, offset, "intIdByDialogOrOptionId")
        field5, offset = parse_dialog_id_table_string_int_map(data, offset, "intIdByDialogId")
        if offset != len(data):
            raise ValueError(f"trailing-bytes:{len(data) - offset}")
    except (UnicodeDecodeError, struct.error, ValueError):
        return None

    registry = summarize_dialog_id_table_registry(data)
    payload_summary = ",".join(
        f"{length}:{count}" for length, count in payload_length_counts.most_common(6)
    )
    dialog_type_summary = ",".join(
        f"{dialog_type}:{count}" for dialog_type, count in brief_dialog_type_counts.most_common(4)
    )
    details = [
        f"briefRows={brief_count}",
        f"briefParsed={dialog_brief_info_parsed_count}",
        f"dialogTypes={dialog_type_summary}",
        f"dialogIntMap={field2['count']}",
        f"optionIntMap={field3['count']}",
        f"reverseAll={field4['count']}",
        f"reverseDialog={field5['count']}",
        f"registryScenes={registry['registeredSceneCount']}",
        f"payloads={payload_summary}",
    ]
    if brief_rows:
        details.append("samples=" + ",".join(row["key"] for row in brief_rows[:3]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 5:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "DialogIdTable",
        "summary": (
            "MemoryPack DialogIdTable; object member count 5; "
            f"{brief_count} DialogBriefInfo rows, {field3['count']} option-id rows; exact length"
        ),
        "rows": brief_count + field2["count"] + field3["count"] + field4["count"] + field5["count"],
        "keys": [
            "dialogId",
            "dialogBriefInfoPayloadLength",
            "dialogType",
            "interactText",
            "npcProxyIds",
            "useBlackScreen",
            "dialogIntId",
            "optionId",
            "optionIntId",
            "registrySceneCount",
            "lineIdCount",
            "optionIdCount",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": DIALOG_ID_TABLE_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": "DialogIdTable runtime class and registry semantics from scripts/story_builder/dialog_registry.py plus IL2CPP MemoryPack formatter metadata; table and nested DialogBriefInfo fields recovered by exact byte boundaries",
            "decodedPreviewFields": [
                "dialogBriefInfoDict",
                "DialogBriefInfo.afterMaskBlendData",
                "DialogBriefInfo.beforeMaskBlendData",
                "DialogBriefInfo.dialogId",
                "DialogBriefInfo.dialogType",
                "DialogBriefInfo.interactText",
                "DialogBriefInfo.npcProxyIds",
                "DialogBriefInfo.useBlackScreen",
                "dialogIdByIntId",
                "optionIdByIntId",
                "intIdByDialogOrOptionId",
                "intIdByDialogId",
                "registrySummary",
            ],
            "dialogBriefInfoMemberCount": DIALOG_ID_TABLE_BRIEF_MEMBER_COUNT,
            "dialogBriefInfoFieldOrder": [
                "afterMaskBlendData",
                "beforeMaskBlendData",
                "dialogId",
                "dialogType",
                "interactText",
                "npcProxyIds",
                "useBlackScreen",
            ],
            "dialogBriefInfoCount": brief_count,
            "dialogBriefInfoParsedCount": dialog_brief_info_parsed_count,
            "dialogBriefInfoEndOffset": format_offset(field2_offset),
            "dialogBriefInfoDuplicateKeyMatches": duplicate_key_matches,
            "dialogBriefInfoPayloadLengthCounts": {str(key): count for key, count in payload_length_counts.most_common(24)},
            "dialogBriefInfoKeyPrefixCounts": dict(brief_key_prefix_counts.most_common(24)),
            "dialogBriefInfoMaskPrefixLengthCounts": {str(key): count for key, count in brief_mask_prefix_length_counts.most_common(24)},
            "dialogBriefInfoMaskLengthCounts": dict(brief_mask_length_counts.most_common(24)),
            "dialogBriefInfoDialogTypeCounts": dialog_id_table_counter_to_json(brief_dialog_type_counts),
            "dialogBriefInfoInteractTextCounts": dialog_id_table_counter_to_json(brief_interact_text_counts),
            "dialogBriefInfoNpcProxyIdCountCounts": dialog_id_table_counter_to_json(brief_npc_proxy_count_counts),
            "dialogBriefInfoUseBlackScreenCounts": dialog_id_table_counter_to_json(brief_use_black_screen_counts),
            "dialogBriefInfoMaskFieldCounts": {
                key: dialog_id_table_counter_to_json(value)
                for key, value in sorted(brief_mask_field_counts.items())
            },
            "dialogBriefInfoSampleRows": brief_rows,
            "dialogBriefInfoInterestingRows": interesting_brief_rows,
            "dialogIdByIntId": field2,
            "optionIdByIntId": field3,
            "intIdByDialogOrOptionId": field4,
            "intIdByDialogId": field5,
            "registrySummary": registry,
            "exactLength": True,
            "fileSize": size,
        },
    }

def decode_world_entity_registry_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel != WORLD_ENTITY_REGISTRY_REL:
        return None
    if not data or data[0] != WORLD_ENTITY_REGISTRY_ROOT_MEMBER_COUNT:
        return None

    def read_u64(offset: int, field_name: str) -> tuple[int, int]:
        if offset + 8 > len(data):
            raise ValueError(f"{field_name}:truncated-u64")
        return struct.unpack_from("<Q", data, offset)[0], offset + 8

    def read_i64(offset: int, field_name: str) -> tuple[int, int]:
        if offset + 8 > len(data):
            raise ValueError(f"{field_name}:truncated-i64")
        return struct.unpack_from("<q", data, offset)[0], offset + 8

    def read_vec3(offset: int, field_name: str) -> tuple[list[float], int]:
        values: list[float] = []
        for axis in range(3):
            value, offset = read_memorypack_f32(data, offset)
            if not math.isfinite(value) or abs(value) > 1_000_000:
                raise ValueError(f"{field_name}[{axis}]:invalid-float")
            values.append(round(value, 6))
        return values, offset

    def float_from_low_bits(value: int) -> float:
        raw = struct.pack("<I", value & 0xFFFFFFFF)
        return round(struct.unpack("<f", raw)[0], 6)

    try:
        offset = 1
        empty_field_1, offset = read_memorypack_u32_count(
            data,
            offset,
            "emptyField1",
            max_count=1,
        )
        empty_field_2, offset = read_memorypack_u32_count(
            data,
            offset,
            "emptyField2",
            max_count=1,
        )
        if empty_field_1 != 0 or empty_field_2 != 0:
            raise ValueError("expected-empty-prefix-fields")

        brief_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "worldEntityBriefInfos",
            max_count=20_000,
        )
        brief_rows: list[dict[str, Any]] = []
        brief_marker_counts: Counter[int] = Counter()
        entity_type_counts: Counter[int] = Counter()
        detail_id_counts: Counter[str] = Counter()
        key_deltas: Counter[int] = Counter()
        min_key: int | None = None
        max_key: int | None = None
        previous_key: int | None = None
        for row_index in range(brief_count):
            key, offset = read_u64(offset, f"worldEntityBriefInfos[{row_index}].key")
            if min_key is None or key < min_key:
                min_key = key
            if max_key is None or key > max_key:
                max_key = key
            if previous_key is not None:
                key_deltas[key - previous_key] += 1
            previous_key = key
            if offset >= len(data):
                raise ValueError(f"worldEntityBriefInfos[{row_index}].memberCount:truncated")
            member_count = data[offset]
            offset += 1
            brief_marker_counts[member_count] += 1
            if member_count != WORLD_ENTITY_BRIEF_ROW_MEMBER_COUNT:
                raise ValueError(f"worldEntityBriefInfos[{row_index}].memberCount={member_count}")
            detail_id, offset = read_memorypack_nullable_string(
                data,
                offset,
                f"worldEntityBriefInfos[{row_index}].detailId",
                max_length=512,
            )
            entity_type, offset = read_memorypack_i32(data, offset)
            position, offset = read_vec3(offset, f"worldEntityBriefInfos[{row_index}].position")
            rotation, offset = read_vec3(offset, f"worldEntityBriefInfos[{row_index}].rotation")
            entity_type_counts[entity_type] += 1
            detail_id_counts[detail_id if detail_id is not None else "<null>"] += 1
            if len(brief_rows) < 16:
                brief_rows.append({
                    "entityId": key,
                    "detailId": detail_id,
                    "entityType": entity_type,
                    "position": position,
                    "rotation": rotation,
                })

        config_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "worldEntityConfigInfos",
            max_count=20_000,
        )
        config_rows: list[dict[str, Any]] = []
        config_marker_counts: Counter[int] = Counter()
        property_count_counts: Counter[int] = Counter()
        property_marker_counts: Counter[int] = Counter()
        property_name_counts: Counter[str] = Counter()
        property_value_marker_counts: Counter[int] = Counter()
        property_value_type_counts: Counter[int] = Counter()
        value_item_marker_counts: Counter[int] = Counter()
        value_item_tail_counts: Counter[int] = Counter()
        total_properties = 0
        total_value_items = 0
        for row_index in range(config_count):
            key, offset = read_u64(offset, f"worldEntityConfigInfos[{row_index}].key")
            if offset >= len(data):
                raise ValueError(f"worldEntityConfigInfos[{row_index}].memberCount:truncated")
            member_count = data[offset]
            offset += 1
            config_marker_counts[member_count] += 1
            if member_count != WORLD_ENTITY_CONFIG_ROW_MEMBER_COUNT:
                raise ValueError(f"worldEntityConfigInfos[{row_index}].memberCount={member_count}")
            property_count, offset = read_memorypack_u32_count(
                data,
                offset,
                f"worldEntityConfigInfos[{row_index}].propertyList",
                max_count=128,
            )
            property_count_counts[property_count] += 1
            properties: list[dict[str, Any]] = []
            for property_index in range(property_count):
                total_properties += 1
                if offset >= len(data):
                    raise ValueError(f"worldEntityConfigInfos[{row_index}].property[{property_index}].memberCount:truncated")
                property_member_count = data[offset]
                offset += 1
                property_marker_counts[property_member_count] += 1
                if property_member_count != WORLD_ENTITY_PROPERTY_MEMBER_COUNT:
                    raise ValueError(
                        f"worldEntityConfigInfos[{row_index}].property[{property_index}].memberCount={property_member_count}"
                    )
                property_name, offset = require_memorypack_non_null_string(
                    data,
                    offset,
                    f"worldEntityConfigInfos[{row_index}].property[{property_index}].key",
                    max_length=128,
                )
                property_name_counts[property_name] += 1
                if offset >= len(data):
                    raise ValueError(f"worldEntityConfigInfos[{row_index}].property[{property_index}].valueMemberCount:truncated")
                value_member_count = data[offset]
                offset += 1
                property_value_marker_counts[value_member_count] += 1
                if value_member_count != WORLD_ENTITY_PROPERTY_VALUE_MEMBER_COUNT:
                    raise ValueError(
                        f"worldEntityConfigInfos[{row_index}].property[{property_index}].valueMemberCount={value_member_count}"
                    )
                value_type, offset = read_memorypack_i32(data, offset)
                property_value_type_counts[value_type] += 1
                value_count, offset = read_memorypack_u32_count(
                    data,
                    offset,
                    f"worldEntityConfigInfos[{row_index}].property[{property_index}].valueArray",
                    max_count=128,
                )
                values: list[dict[str, Any]] = []
                for value_index in range(value_count):
                    total_value_items += 1
                    if offset >= len(data):
                        raise ValueError(
                            f"worldEntityConfigInfos[{row_index}].property[{property_index}].value[{value_index}].memberCount:truncated"
                        )
                    item_member_count = data[offset]
                    offset += 1
                    value_item_marker_counts[item_member_count] += 1
                    if item_member_count != WORLD_ENTITY_PROPERTY_VALUE_ITEM_MEMBER_COUNT:
                        raise ValueError(
                            f"worldEntityConfigInfos[{row_index}].property[{property_index}].value[{value_index}].memberCount={item_member_count}"
                        )
                    value_bits, offset = read_i64(
                        offset,
                        f"worldEntityConfigInfos[{row_index}].property[{property_index}].value[{value_index}].valueBit64",
                    )
                    tail_int, offset = read_memorypack_i32(data, offset)
                    value_item_tail_counts[tail_int] += 1
                    values.append({
                        "valueBit64": value_bits,
                        "floatFromLowBits": float_from_low_bits(value_bits),
                        "tailInt": tail_int,
                    })
                properties.append({
                    "key": property_name,
                    "valueType": value_type,
                    "values": values,
                })
            if len(config_rows) < 16:
                config_rows.append({
                    "entityId": key,
                    "propertyCount": property_count,
                    "properties": properties,
                })

        if offset != len(data):
            raise ValueError(f"trailing-bytes:{len(data) - offset}")
        if set(brief_marker_counts) != {WORLD_ENTITY_BRIEF_ROW_MEMBER_COUNT}:
            raise ValueError("worldEntityBriefInfos.memberCounts:mismatch")
        if config_count and set(config_marker_counts) != {WORLD_ENTITY_CONFIG_ROW_MEMBER_COUNT}:
            raise ValueError("worldEntityConfigInfos.memberCounts:mismatch")
        if total_properties and set(property_marker_counts) != {WORLD_ENTITY_PROPERTY_MEMBER_COUNT}:
            raise ValueError("worldEntityConfigInfos.property.memberCounts:mismatch")
        if total_properties and set(property_value_marker_counts) != {WORLD_ENTITY_PROPERTY_VALUE_MEMBER_COUNT}:
            raise ValueError("worldEntityConfigInfos.property.value.memberCounts:mismatch")
        if total_value_items and set(value_item_marker_counts) != {WORLD_ENTITY_PROPERTY_VALUE_ITEM_MEMBER_COUNT}:
            raise ValueError("worldEntityConfigInfos.property.value.itemMemberCounts:mismatch")
    except (UnicodeDecodeError, struct.error, ValueError):
        return None

    def top_counter(counter: Counter[Any], limit: int = 16) -> dict[str, int]:
        return {str(key): count for key, count in counter.most_common(limit)}

    entity_summary = ",".join(f"{key}:{count}" for key, count in entity_type_counts.most_common(6))
    detail_summary = ",".join(f"{key}:{count}" for key, count in detail_id_counts.most_common(4))
    property_summary = ",".join(f"{key}:{count}" for key, count in property_name_counts.most_common(6))
    details = [
        f"emptyFields={empty_field_1},{empty_field_2}",
        f"briefRows={brief_count}",
        f"configRows={config_count}",
        f"entityTypes={entity_summary}",
    ]
    if detail_summary:
        details.append("details=" + detail_summary)
    if property_summary:
        details.append("properties=" + property_summary)
    if brief_rows:
        details.append("samples=" + ",".join(str(row["entityId"]) for row in brief_rows[:3]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "GameplayConfigWorldEntityRegistry",
        "summary": (
            "MemoryPack GameplayConfigWorldEntityRegistry; object member count 4; "
            f"{brief_count} brief rows and {config_count} config rows; exact length"
        ),
        "rows": brief_count + config_count,
        "keys": [
            "entityId",
            "detailId",
            "entityType",
            "position",
            "rotation",
            "propertyList",
            "valueType",
            "valueBit64",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": WORLD_ENTITY_REGISTRY_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": [
                "worldEntityBriefInfos",
                "worldEntityConfigInfos",
                "entityTypeCounts",
                "detailIdCounts",
            ],
            "emptyFieldCounts": [empty_field_1, empty_field_2],
            "briefRowMemberCount": WORLD_ENTITY_BRIEF_ROW_MEMBER_COUNT,
            "configRowMemberCount": WORLD_ENTITY_CONFIG_ROW_MEMBER_COUNT,
            "propertyMemberCount": WORLD_ENTITY_PROPERTY_MEMBER_COUNT,
            "propertyValueMemberCount": WORLD_ENTITY_PROPERTY_VALUE_MEMBER_COUNT,
            "propertyValueItemMemberCount": WORLD_ENTITY_PROPERTY_VALUE_ITEM_MEMBER_COUNT,
            "briefCount": brief_count,
            "configCount": config_count,
            "briefEntityIdMin": min_key,
            "briefEntityIdMax": max_key,
            "briefMarkerCounts": top_counter(brief_marker_counts),
            "entityTypeCounts": top_counter(entity_type_counts),
            "detailIdCounts": top_counter(detail_id_counts),
            "keyDeltaCounts": top_counter(key_deltas, 12),
            "configMarkerCounts": top_counter(config_marker_counts),
            "propertyCountCounts": top_counter(property_count_counts),
            "propertyMarkerCounts": top_counter(property_marker_counts),
            "propertyNameCounts": top_counter(property_name_counts),
            "propertyValueMarkerCounts": top_counter(property_value_marker_counts),
            "propertyValueTypeCounts": top_counter(property_value_type_counts),
            "valueItemMarkerCounts": top_counter(value_item_marker_counts),
            "valueItemTailCounts": top_counter(value_item_tail_counts),
            "sampleBriefRows": brief_rows,
            "sampleConfigRows": config_rows,
            "exactLength": True,
            "fileSize": size,
        },
    }

def parse_model_table_lock_view_config_map(data: bytes, offset: int, field_name: str) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(
        data,
        offset,
        field_name,
        max_count=256,
    )
    rows: list[dict[str, Any]] = []
    key_counts: Counter[str] = Counter()
    view_config_counts: Counter[str] = Counter()
    model_node_counts: Counter[str] = Counter()
    for index in range(count):
        key, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{index}].key",
            max_length=256,
        )
        if offset >= len(data):
            raise ValueError(f"{field_name}[{index}].memberCount:truncated")
        member_count = data[offset]
        offset += 1
        if member_count != MODEL_TABLE_LOCK_VIEW_CONFIG_MEMBER_COUNT:
            raise ValueError(f"{field_name}[{index}].memberCount={member_count}")
        model_node_name, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{index}].modelNodeName",
            max_length=512,
        )
        mount_offset, offset = read_memorypack_vec3(data, offset)
        view_config_id, offset = require_memorypack_non_null_string(
            data,
            offset,
            f"{field_name}[{index}].viewConfigId",
            max_length=512,
        )
        key_counts[key] += 1
        view_config_counts[view_config_id] += 1
        model_node_counts[model_node_name] += 1
        if len(rows) < 8:
            rows.append({
                "key": key,
                "modelNodeName": model_node_name,
                "mountOffset": mount_offset,
                "viewConfigId": view_config_id,
            })
    return {
        "count": count,
        "sampleRows": rows,
        "keyCounts": dict(key_counts.most_common(12)),
        "modelNodeNameCounts": dict(model_node_counts.most_common(12)),
        "viewConfigIdCounts": dict(view_config_counts.most_common(12)),
    }, offset


def parse_model_table_shape_data_list(data: bytes, offset: int, field_name: str) -> tuple[dict[str, Any], int]:
    count, offset = read_memorypack_u32_count(data, offset, field_name, max_count=256)
    rows: list[dict[str, Any]] = []
    shape_counts: Counter[int] = Counter()
    for index in range(count):
        center, offset = read_memorypack_vec3(data, offset)
        height, offset = read_memorypack_f32(data, offset)
        radius, offset = read_memorypack_f32(data, offset)
        shape, offset = read_memorypack_i32(data, offset)
        size, offset = read_memorypack_vec3(data, offset)
        if not math.isfinite(height) or not math.isfinite(radius):
            raise ValueError(f"{field_name}[{index}].heightRadius:non-finite")
        if shape < 0 or shape > 16:
            raise ValueError(f"{field_name}[{index}].shape={shape}")
        shape_counts[shape] += 1
        if len(rows) < 8:
            rows.append({
                "shape": shape,
                "center": center,
                "height": round(height, 6),
                "radius": round(radius, 6),
                "size": size,
            })
    return {
        "count": count,
        "shapeCounts": {str(key): count for key, count in shape_counts.most_common(12)},
        "sampleRows": rows,
    }, offset


def parse_model_table_extra_data_interactive(data: bytes, offset: int, field_name: str) -> tuple[dict[str, Any], int]:
    start = offset
    center, offset = read_memorypack_vec3(data, offset)
    collision_shape_datas, offset = parse_model_table_shape_data_list(
        data,
        offset,
        f"{field_name}.collisionShapeDatas",
    )
    if offset + 2 > len(data):
        raise ValueError(f"{field_name}.collisionType:truncated")
    collision_type = data[offset]
    offset += 1
    dynamic_update_rvo_byte = data[offset]
    offset += 1
    if collision_type not in (0, 1, 2):
        raise ValueError(f"{field_name}.collisionType={collision_type}")
    if dynamic_update_rvo_byte not in (0, 1):
        raise ValueError(f"{field_name}.dynamicUpdateRVO={dynamic_update_rvo_byte}")
    gameplay_lock_view_config, offset = parse_model_table_lock_view_config_map(
        data,
        offset,
        f"{field_name}.gameplayLockViewConfig",
    )
    if offset >= len(data):
        raise ValueError(f"{field_name}.hasMultiLevel:truncated")
    has_multi_level_byte = data[offset]
    offset += 1
    if has_multi_level_byte not in (0, 1):
        raise ValueError(f"{field_name}.hasMultiLevel={has_multi_level_byte}")
    height, offset = read_memorypack_f32(data, offset)
    obstacle_type, offset = read_memorypack_i32(data, offset)
    radius, offset = read_memorypack_f32(data, offset)
    rvo_concern_value, offset = read_memorypack_i32(data, offset)
    shape, offset = read_memorypack_i32(data, offset)
    size, offset = read_memorypack_vec3(data, offset)
    if not math.isfinite(height) or not math.isfinite(radius):
        raise ValueError(f"{field_name}.heightRadius:non-finite")
    if obstacle_type not in (0, 1, 2):
        raise ValueError(f"{field_name}.obstacleType={obstacle_type}")
    if shape not in (0, 1, 2):
        raise ValueError(f"{field_name}.shape={shape}")
    return {
        "byteLength": offset - start,
        "center": center,
        "collisionShapeDataCount": collision_shape_datas["count"],
        "collisionShapeDatas": collision_shape_datas["sampleRows"],
        "collisionShapeShapeCounts": collision_shape_datas["shapeCounts"],
        "collisionType": collision_type,
        "dynamicUpdateRVO": bool(dynamic_update_rvo_byte),
        "gameplayLockViewConfigCount": gameplay_lock_view_config["count"],
        "gameplayLockViewConfig": gameplay_lock_view_config["sampleRows"],
        "gameplayLockViewConfigKeyCounts": gameplay_lock_view_config["keyCounts"],
        "gameplayLockViewConfigModelNodeCounts": gameplay_lock_view_config["modelNodeNameCounts"],
        "gameplayLockViewConfigIdCounts": gameplay_lock_view_config["viewConfigIdCounts"],
        "hasMultiLevel": bool(has_multi_level_byte),
        "height": round(height, 6),
        "obstacleType": obstacle_type,
        "radius": round(radius, 6),
        "rvoConcernValue": rvo_concern_value,
        "shape": shape,
        "size": size,
    }, offset



def decode_model_table_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    if rel not in MODEL_TABLE_RELS:
        return None
    if not data or data[0] != MODEL_TABLE_ROOT_MEMBER_COUNT:
        return None

    try:
        offset = 1
        model_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "modelDict",
            max_count=10_000,
        )
        model_rows: list[dict[str, Any]] = []
        flag_counts: Counter[int] = Counter()
        tail_counts: Counter[int] = Counter()
        scale_counts: Counter[float] = Counter()
        prefab_extension_counts: Counter[str] = Counter()
        path_category_counts: Counter[str] = Counter()
        duplicate_model_id_matches = 0
        non_null_alt_model_ids = 0
        model_marker_counts: Counter[int] = Counter()
        for row_index in range(model_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"modelDict[{row_index}].key",
                max_length=256,
            )
            if offset >= len(data):
                raise ValueError(f"modelDict[{row_index}].memberCount:truncated")
            member_count = data[offset]
            offset += 1
            model_marker_counts[member_count] += 1
            if member_count != MODEL_TABLE_MODEL_ROW_MEMBER_COUNT:
                raise ValueError(f"modelDict[{row_index}].memberCount={member_count}")
            alt_model_id, offset = read_memorypack_nullable_string(
                data,
                offset,
                f"modelDict[{row_index}].altModelId",
                max_length=512,
            )
            if alt_model_id is not None:
                non_null_alt_model_ids += 1
            if offset >= len(data):
                raise ValueError(f"modelDict[{row_index}].flag:truncated")
            flag = data[offset]
            offset += 1
            model_id, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"modelDict[{row_index}].modelId",
                max_length=512,
            )
            prefab_path, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"modelDict[{row_index}].prefabPath",
                max_length=2048,
            )
            scale, offset = read_memorypack_f32(data, offset)
            tail_int, offset = read_memorypack_i32(data, offset)
            if not math.isfinite(scale) or abs(scale) > 10_000:
                raise ValueError(f"modelDict[{row_index}].scale")
            if key == model_id:
                duplicate_model_id_matches += 1
            flag_counts[flag] += 1
            tail_counts[tail_int] += 1
            scale_counts[round(scale, 6)] += 1
            suffix = Path(prefab_path).suffix.lower() or "[none]"
            prefab_extension_counts[suffix] += 1
            category = "other"
            for marker in ("/PostModels/", "/Models/", "/UIModels/", "/level_models/"):
                if marker in prefab_path:
                    category = marker.strip("/")
                    break
            path_category_counts[category] += 1
            if len(model_rows) < 16:
                model_rows.append({
                    "modelId": key,
                    "altModelId": alt_model_id,
                    "flag": flag,
                    "duplicateModelId": model_id,
                    "prefabPath": prefab_path,
                    "scale": round(scale, 6),
                    "tailInt": tail_int,
                })

        model_table_end = offset
        layout_count, offset = read_memorypack_u32_count(
            data,
            offset,
            "layoutDict",
            max_count=10_000,
        )
        layout_rows: list[dict[str, Any]] = []
        layout_lock_rows: list[dict[str, Any]] = []
        layout_collision_shape_rows: list[dict[str, Any]] = []
        layout_marker_counts: Counter[int] = Counter()
        layout_byte_length_counts: Counter[int] = Counter()
        layout_collision_type_counts: Counter[int] = Counter()
        layout_dynamic_update_rvo_counts: Counter[bool] = Counter()
        layout_has_multi_level_counts: Counter[bool] = Counter()
        layout_lock_config_count_counts: Counter[int] = Counter()
        layout_lock_config_key_counts: Counter[str] = Counter()
        layout_lock_config_model_node_counts: Counter[str] = Counter()
        layout_lock_config_id_counts: Counter[str] = Counter()
        layout_obstacle_type_counts: Counter[int] = Counter()
        layout_shape_counts: Counter[int] = Counter()
        layout_collision_shape_data_count_counts: Counter[int] = Counter()
        for row_index in range(layout_count):
            key, offset = require_memorypack_non_null_string(
                data,
                offset,
                f"layoutDict[{row_index}].key",
                max_length=256,
            )
            if not MODEL_TABLE_LAYOUT_KEY_RE.match(key):
                raise ValueError(f"layoutDict[{row_index}].key:invalid")
            if offset >= len(data):
                raise ValueError(f"layoutDict[{row_index}].memberCount:truncated")
            member_count = data[offset]
            offset += 1
            layout_marker_counts[member_count] += 1
            if member_count != MODEL_TABLE_LAYOUT_ROW_MEMBER_COUNT:
                raise ValueError(f"layoutDict[{row_index}].memberCount={member_count}")
            value_start = offset
            layout_extra, offset = parse_model_table_extra_data_interactive(
                data,
                offset,
                f"layoutDict[{row_index}]",
            )
            if offset <= value_start:
                raise ValueError(f"layoutDict[{row_index}].value:not-consumed")
            layout_byte_length_counts[layout_extra["byteLength"]] += 1
            layout_collision_type_counts[layout_extra["collisionType"]] += 1
            layout_dynamic_update_rvo_counts[layout_extra["dynamicUpdateRVO"]] += 1
            layout_has_multi_level_counts[layout_extra["hasMultiLevel"]] += 1
            layout_lock_config_count_counts[layout_extra["gameplayLockViewConfigCount"]] += 1
            layout_obstacle_type_counts[layout_extra["obstacleType"]] += 1
            layout_shape_counts[layout_extra["shape"]] += 1
            layout_collision_shape_data_count_counts[layout_extra["collisionShapeDataCount"]] += 1
            for lock_key, count in layout_extra["gameplayLockViewConfigKeyCounts"].items():
                layout_lock_config_key_counts[lock_key] += count
            for model_node, count in layout_extra["gameplayLockViewConfigModelNodeCounts"].items():
                layout_lock_config_model_node_counts[model_node] += count
            for view_config_id, count in layout_extra["gameplayLockViewConfigIdCounts"].items():
                layout_lock_config_id_counts[view_config_id] += count
            row_preview = {
                "key": key,
                "byteLength": layout_extra["byteLength"],
                "center": layout_extra["center"],
                "collisionType": layout_extra["collisionType"],
                "dynamicUpdateRVO": layout_extra["dynamicUpdateRVO"],
                "gameplayLockViewConfigCount": layout_extra["gameplayLockViewConfigCount"],
                "hasMultiLevel": layout_extra["hasMultiLevel"],
                "height": layout_extra["height"],
                "obstacleType": layout_extra["obstacleType"],
                "radius": layout_extra["radius"],
                "rvoConcernValue": layout_extra["rvoConcernValue"],
                "shape": layout_extra["shape"],
                "size": layout_extra["size"],
                "collisionShapeDataCount": layout_extra["collisionShapeDataCount"],
            }
            if len(layout_rows) < 16:
                layout_rows.append(row_preview)
            if layout_extra["gameplayLockViewConfigCount"] and len(layout_lock_rows) < 16:
                lock_preview = dict(row_preview)
                lock_preview["gameplayLockViewConfig"] = layout_extra["gameplayLockViewConfig"]
                layout_lock_rows.append(lock_preview)
            if layout_extra["collisionShapeDataCount"] and len(layout_collision_shape_rows) < 16:
                collision_preview = dict(row_preview)
                collision_preview["collisionShapeDatas"] = layout_extra["collisionShapeDatas"]
                layout_collision_shape_rows.append(collision_preview)

        if offset != len(data):
            raise ValueError(f"trailing-bytes:{len(data) - offset}")
        if duplicate_model_id_matches != model_count:
            raise ValueError("modelDict.duplicateModelId:mismatch")
        if set(model_marker_counts) != {MODEL_TABLE_MODEL_ROW_MEMBER_COUNT}:
            raise ValueError("modelDict.memberCounts:mismatch")
        if set(layout_marker_counts) != {MODEL_TABLE_LAYOUT_ROW_MEMBER_COUNT}:
            raise ValueError("layoutDict.memberCounts:mismatch")
    except (UnicodeDecodeError, struct.error, ValueError):
        return None

    def top_counter(counter: Counter[Any], limit: int = 16) -> dict[str, int]:
        return {str(key): count for key, count in counter.most_common(limit)}

    layout_payload_summary = ",".join(
        f"{length}:{count}" for length, count in layout_byte_length_counts.most_common(8)
    )
    details = [
        f"models={model_count}",
        f"layouts={layout_count}",
        f"flags=" + ",".join(f"{key}:{count}" for key, count in flag_counts.most_common(4)),
        f"tails=" + ",".join(f"{key}:{count}" for key, count in tail_counts.most_common(5)),
        f"extraBytes={layout_payload_summary}",
        f"lockCfgs=" + ",".join(f"{key}:{count}" for key, count in layout_lock_config_count_counts.most_common(3)),
    ]
    if model_rows:
        details.append("sampleModels=" + ",".join(row["modelId"] for row in model_rows[:3]))
    if layout_rows:
        details.append("sampleLayouts=" + ",".join(row["key"] for row in layout_rows[:3]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 4:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "ModelTable",
        "summary": (
            "MemoryPack ModelTable; object member count 2; "
            f"{model_count} model rows and {layout_count} layout rows; exact length"
        ),
        "rows": model_count + layout_count,
        "keys": [
            "modelId",
            "altModelId",
            "flag",
            "prefabPath",
            "scale",
            "tailInt",
            "layoutKey",
            "layoutExtraDataByteLength",
            "center",
            "collisionType",
            "dynamicUpdateRVO",
            "gameplayLockViewConfig",
            "hasMultiLevel",
            "height",
            "obstacleType",
            "radius",
            "rvoConcernValue",
            "shape",
            "size",
        ],
        "sample": sample,
        "decoded": {
            "memberCount": MODEL_TABLE_ROOT_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": [
                "modelRows",
                "layoutRows",
                "layoutExtraDataInteractive",
                "gameplayLockViewConfig",
            ],
            "modelRowMemberCount": MODEL_TABLE_MODEL_ROW_MEMBER_COUNT,
            "layoutRowMemberCount": MODEL_TABLE_LAYOUT_ROW_MEMBER_COUNT,
            "modelCount": model_count,
            "layoutCount": layout_count,
            "modelTableEndOffset": format_offset(model_table_end),
            "duplicateModelIdMatches": duplicate_model_id_matches,
            "nonNullAltModelIdCount": non_null_alt_model_ids,
            "flagCounts": top_counter(flag_counts),
            "tailIntCounts": top_counter(tail_counts),
            "scaleCounts": top_counter(scale_counts),
            "prefabExtensionCounts": top_counter(prefab_extension_counts),
            "pathCategoryCounts": top_counter(path_category_counts),
            "layoutExtraDataByteLengthCounts": top_counter(layout_byte_length_counts),
            "layoutCollisionTypeCounts": top_counter(layout_collision_type_counts),
            "layoutDynamicUpdateRVOCounts": top_counter(layout_dynamic_update_rvo_counts),
            "layoutHasMultiLevelCounts": top_counter(layout_has_multi_level_counts),
            "layoutGameplayLockViewConfigCountCounts": top_counter(layout_lock_config_count_counts),
            "layoutGameplayLockViewConfigKeyCounts": top_counter(layout_lock_config_key_counts),
            "layoutGameplayLockViewConfigModelNodeCounts": top_counter(layout_lock_config_model_node_counts),
            "layoutGameplayLockViewConfigIdCounts": top_counter(layout_lock_config_id_counts),
            "layoutObstacleTypeCounts": top_counter(layout_obstacle_type_counts),
            "layoutShapeCounts": top_counter(layout_shape_counts),
            "layoutCollisionShapeDataCountCounts": top_counter(layout_collision_shape_data_count_counts),
            "modelRows": model_rows,
            "layoutRows": layout_rows,
            "layoutGameplayLockViewConfigRows": layout_lock_rows,
            "layoutCollisionShapeDataRows": layout_collision_shape_rows,
            "exactLength": True,
            "fileSize": size,
        },
    }

def decode_navmesh_state_container_memorypack(rel: str, data: bytes, size: int) -> dict[str, Any] | None:
    parts = rel.split("/")
    if len(parts) < 4 or parts[0] != "Json" or parts[1] != "NavMesh" or parts[-1] != "NavMeshStateContainer.json":
        return None
    if not data or data[0] != NAVMESH_STATE_CONTAINER_MEMBER_COUNT:
        return None

    fields = find_navmesh_state_container_parse(data, 1, 0, [])
    if fields is None:
        return None

    record_kind_counts = Counter(str(field.get("recordKind") or "") for field in fields)
    total_rows = sum(int(field.get("count") or 0) for field in fields)
    non_empty = [field for field in fields if int(field.get("count") or 0) > 0]
    field_bits = [
        f"f{field['fieldIndex']}={field['recordKind']}:{field['count']}"
        for field in fields
    ]
    sample = "; ".join([f"rows={total_rows}", *field_bits])
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(field_bits) > 3:
        field_bits.pop()
        sample = "; ".join([f"rows={total_rows}", *field_bits])

    return {
        "kind": "memorypack-json",
        "subtype": "NavMeshStateContainer",
        "summary": (
            "MemoryPack NavMeshStateContainer; object member count 6; "
            f"{total_rows} numeric state rows across {len(non_empty)} non-empty fields; "
            "exact length"
        ),
        "rows": total_rows,
        "keys": ["fieldIndex", "recordKind", "count", "sampleRows"],
        "sample": sample,
        "decoded": {
            "memberCount": NAVMESH_STATE_CONTAINER_MEMBER_COUNT,
            "format": "memorypack",
            "decodedPreviewFields": ["fieldIndex", "recordKind", "count", "sampleRows"],
            "fieldCount": len(fields),
            "totalRows": total_rows,
            "recordKindCounts": dict(sorted(record_kind_counts.items())),
            "fields": fields,
            "exactLength": True,
            "fileSize": size,
        },
    }


def decode_levelscript_template_memorypack(path: Path, data: bytes, size: int) -> dict[str, Any] | None:
    schema = MEMORYPACK_FIELD_SCHEMAS.get("LevelScriptTemplateData")
    if not schema or not data or data[0] != LEVELSCRIPT_TEMPLATE_MEMBER_COUNT:
        return None
    tail = find_length_prefixed_utf8_tail_value(data, path.stem, trailing_bytes=0)
    if not tail:
        return None
    template_id_offset, _template_id_end = tail
    action_map = decode_levelscript_action_map_header(data)
    if action_map.get("status") != "present":
        return None
    action_count = action_map.get("recordCount")
    if not isinstance(action_count, int) or action_count < 0:
        return None

    hits = scan_length_prefixed_utf8_string_hits(data, max_samples=512, min_length=2, max_length=320)
    strings = unique_strings([str(hit.get("value") or "") for hit in hits], 192)
    non_template_strings = [value for value in strings if value != path.stem]
    classified = classify_levelscript_template_strings(non_template_strings, path.stem)

    details = [
        f"templateId={path.stem}",
        f"actionMap={action_map.get('status')}",
        f"records={action_count}",
    ]
    if classified["keyLikeStrings"]:
        details.append("keys=" + ",".join(classified["keyLikeStrings"][:4]))
    if classified["montageRefs"]:
        details.append("montages=" + ",".join(classified["montageRefs"][:2]))
    if classified["audioRefs"]:
        details.append("audio=" + ",".join(classified["audioRefs"][:2]))
    if classified["effectRefs"]:
        details.append("effects=" + ",".join(classified["effectRefs"][:2]))
    sample = "; ".join(details)
    while len(sample) > STRING_SAMPLE_MAX_CHARS and len(details) > 3:
        details.pop()
        sample = "; ".join(details)

    return {
        "kind": "memorypack-json",
        "subtype": "LevelScriptTemplateData",
        "summary": (
            "MemoryPack LevelScriptTemplateData; object member count 6; "
            f"actionMap {action_map.get('status')} with {action_count} records; "
            "templateId tail verified"
        ),
        "rows": action_count,
        "keys": schema,
        "sample": sample,
        "decoded": {
            "memberCount": LEVELSCRIPT_TEMPLATE_MEMBER_COUNT,
            "format": "memorypack",
            "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            "decodedPreviewFields": [
                "actionMapHeader",
                "templateId",
                "lengthPrefixedStringCategories",
            ],
            "actionMapStatus": action_map.get("status") or "",
            "actionMapRecordCount": action_count,
            "actionMapRecordStartOffsetHex": action_map.get("recordStartOffsetHex") or "",
            "actionMapHeader": action_map,
            "templateId": path.stem,
            "templateIdOffset": format_offset(template_id_offset),
            "templateIdTailVerified": True,
            "sampledStringCount": len(strings),
            "stringHits": hits[:48],
            **classified,
            "exactPrefixFields": ["actionMapHeader"],
            "exactTailFields": ["templateId"],
            "exactLength": False,
        },
    }


def decode_levelscript_memorypack(path: Path, data: bytes) -> dict[str, Any] | None:
    if not data or data[0] != 26:
        return None
    try:
        script_id = int(path.stem)
    except ValueError:
        return None

    decoded = decode_levelscript_binary_summary(data, script_id)
    if not decoded:
        return None

    action_details = decode_levelscript_action_map_details(data)
    if action_details:
        decoded["actionMapDetails"] = action_details

    action_status = decoded.get("actionMapStatus") or "unknown"
    action_count = decoded.get("actionMapRecordCount")
    start_type = decoded.get("startTypeName") or "unknown"
    verified = "verified" if decoded.get("scriptIdVerified") else "not verified"
    list_counts = (action_details.get("actionMap") or {}).get("listCounts") or {}
    membership_counts = action_details.get("membershipCounts") or {}
    details = [
        f"scriptId={decoded.get('scriptId')}",
        f"scriptId {verified}",
        f"actionMap={action_status}",
    ]
    if action_count is not None:
        details.append(f"records={action_count}")
    if action_details.get("uidRecordCount") is not None:
        details.append(f"uidRecords={action_details.get('uidRecordCount')}")
    if list_counts:
        list_parts = [
            f"{name}={value}"
            for name in ("actionList", "getterList", "headerList")
            if (value := list_counts.get(name)) is not None
        ]
        if list_parts:
            details.append("lists=" + ",".join(list_parts))
    if membership_counts:
        root_count = membership_counts.get("actionList:root")
        linked_count = membership_counts.get("actionList:linked")
        action_membership = []
        if root_count is not None:
            action_membership.append(f"root={root_count}")
        if linked_count is not None:
            action_membership.append(f"linked={linked_count}")
        if action_membership:
            details.append("actionMembership=" + ",".join(action_membership))
    if decoded.get("startTypeName"):
        details.append(f"startType={start_type}")
    if decoded.get("triggerVolumesStatus"):
        details.append(f"triggerVolumes={decoded.get('triggerVolumesStatus')}")

    return {
        "kind": "memorypack-json",
        "subtype": "LevelScriptData",
        "summary": f"MemoryPack LevelScriptData; 26 members; {', '.join(details[1:])}",
        "rows": action_count,
        "keys": MEMORYPACK_FIELD_SCHEMAS["LevelScriptData"],
        "sample": "; ".join(details),
        "decoded": decoded,
    }


def memorypack_schema_for_rel(rel: str, category: str, member_count: int) -> tuple[str, list[str]] | tuple[None, None]:
    parts = rel.split("/")
    schema_id = category
    if len(parts) >= 4 and parts[0] == "Json" and parts[1] == "NPC" and parts[2] == "MontageJson":
        schema_id = "NPCMontageJson"
    elif rel == "Json/Interactive/InteractiveTable.json":
        schema_id = "InteractiveTable"
    elif len(parts) >= 4 and parts[0] == "Json" and parts[1] == "Interactive" and parts[2] == "InteractiveData":
        schema_id = "InteractiveTemplateData"
    elif len(parts) >= 4 and parts[0] == "Json" and parts[1] == "Interactive" and parts[2] == "ModelViewStateControllerData":
        schema_id = "ModelViewStateControllerData"

    schema = MEMORYPACK_FIELD_SCHEMAS.get(schema_id)
    if schema and len(schema) == member_count:
        return schema_id, schema
    return None, None


def decode_memorypack_json(rel: str, path: Path, size: int, header: bytes) -> dict[str, Any] | None:
    category = category_for_rel(rel)
    member_count = memorypack_member_count(header)
    if member_count is None:
        return None

    if category == "LevelScriptData":
        data = read_binary_for_parser(path, size, header, max_size=8_000_000)
        decoded = decode_levelscript_memorypack(path, data)
        if decoded:
            return decoded

    if category == "LevelScriptTemplateData":
        data = read_binary_for_parser(path, size, header, max_size=256_000)
        decoded = decode_levelscript_template_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "LipSync":
        data = read_binary_for_parser(path, size, header)
        decoded = decode_lipsync_memorypack(data, size)
        if decoded:
            return decoded

    parts = rel.split("/")
    if len(parts) >= 4 and parts[0] == "Json" and parts[1] == "NPC" and parts[2] == "MontageJson":
        data = read_binary_for_parser(path, size, header, max_size=32_000)
        decoded = decode_npc_montage_json_memorypack(rel, path, data, size)
        if decoded:
            return decoded

    if category == "AnimationConfig":
        data = read_binary_for_parser(path, size, header, max_size=512_000)
        decoded = decode_animation_config_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "CharInteractPerformCfgs":
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_char_interact_perform_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "BuffData":
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_buff_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "SkillData":
        data = read_binary_for_parser(path, size, header, max_size=512_000)
        decoded = decode_skill_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "LevelData":
        data = read_binary_for_parser(path, size, header, max_size=1_000_000)
        decoded = decode_leveldata_memorypack(rel, path, data, size)
        if decoded:
            return decoded

    if category == "AtmosphericNpcData":
        data = read_binary_for_parser(path, size, header, max_size=3_000_000)
        decoded = decode_atmospheric_npc_table_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "LevelConfig":
        data = read_binary_for_parser(path, size, header, max_size=16_000)
        decoded = decode_level_config_memorypack(path, data, size)
        if decoded:
            return decoded

    if category == "SpawnerConfig":
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_spawner_config_memorypack(path, data, size)
        if decoded:
            return decoded

    if rel == "Json/Interactive/InteractiveTable.json":
        data = read_binary_for_parser(path, size, header, max_size=256_000)
        decoded = decode_interactive_table_memorypack(data, size)
        if decoded:
            return decoded

    if rel == "Json/GameplayConfig/ModelRadiusTable.json":
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_model_radius_table_memorypack(data, size)
        if decoded:
            return decoded

    if rel in TELEPORT_VALIDATION_TABLE_RELS:
        data = read_binary_for_parser(path, size, header, max_size=256_000)
        decoded = decode_teleport_validation_table_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == DAMAGE_TEXT_REL:
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_damage_text_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == DIALOG_ID_TABLE_REL:
        data = read_binary_for_parser(path, size, header, max_size=1_000_000)
        decoded = decode_dialog_id_table_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == WORLD_ENTITY_REGISTRY_REL:
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_world_entity_registry_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel in MODEL_TABLE_RELS:
        data = read_binary_for_parser(path, size, header, max_size=512_000)
        decoded = decode_model_table_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == MISSION_AREA_TABLE_REL:
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_mission_area_table_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == SUBGAME_INSTANCE_DATA_TABLE_REL:
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_subgame_instance_data_table_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == BAMBOO_RAFT_TASK_TABLE_REL:
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_bamboo_raft_task_table_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel == MATRIX_SHOCK_WAVE_BEAT_REL:
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_matrix_shock_wave_beat_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel.startswith("Json/NavMesh/") and rel.endswith("/LunaArea.json"):
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_luna_area_memorypack(rel, data, size)
        if decoded:
            return decoded

    if rel.startswith("Json/NavMesh/") and rel.endswith("/NavMeshStateContainer.json"):
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_navmesh_state_container_memorypack(rel, data, size)
        if decoded:
            return decoded

    parts = rel.split("/")
    if len(parts) >= 4 and parts[0] == "Json" and parts[1] == "Interactive" and parts[2] == "InteractiveData":
        data = read_binary_for_parser(path, size, header, max_size=1_000_000)
        decoded = decode_interactive_template_memorypack(path, data, size)
        if decoded:
            return decoded

    if len(parts) >= 4 and parts[0] == "Json" and parts[1] == "Interactive" and parts[2] == "ModelViewStateControllerData":
        data = read_binary_for_parser(path, size, header, max_size=128_000)
        decoded = decode_model_view_state_controller_memorypack(path, data, size)
        if decoded:
            return decoded

    words = u32_values(header, 4)
    schema_id, schema = memorypack_schema_for_rel(rel, category, member_count)
    if schema:
        return {
            "kind": "memorypack-json",
            "subtype": schema_id,
            "summary": (
                f"MemoryPack {schema_id}; object member count {member_count}; "
                f"field names recovered from IL2CPP metadata"
            ),
            "rows": None,
            "keys": schema,
            "sample": (
                f"memberCount={member_count}; fields {', '.join(schema[:8])}"
                f"; first bytes {hex_signature(header, 16)}"
            ),
            "decoded": {
                "memberCount": member_count,
                "format": "memorypack",
                "schemaSource": MEMORYPACK_SCHEMA_SOURCE_NOTE,
            },
        }

    return {
        "kind": "memorypack-json",
        "subtype": category,
        "summary": (
            f"MemoryPack-like binary config; object member count {member_count}; "
            f"header u32 {', '.join(str(value) for value in words[:4])}"
        ),
        "rows": None,
        "keys": [],
        "sample": f"memberCount={member_count}; first bytes {hex_signature(header, 16)}",
        "decoded": {"memberCount": member_count, "format": "memorypack-like"},
    }


def ascii_samples(data: bytes) -> str:
    samples = []
    for match in PRINTABLE_ASCII_RE.finditer(data):
        text = match.group(0).decode("ascii", "ignore").strip()
        if text and text not in samples:
            samples.append(text[:80])
        if len(samples) >= 5:
            break
    return " | ".join(samples)


def utf16le_samples(data: bytes) -> str:
    try:
        text = data.decode("utf-16le", "ignore")
    except UnicodeDecodeError:
        return ""
    samples = []
    for match in re.finditer(r"[\x20-\x7e\u4e00-\u9fff]{4,}", text):
        item = match.group(0).strip()
        if item and item not in samples:
            samples.append(item[:80])
        if len(samples) >= 5:
            break
    return " | ".join(samples)


def mp4_summary(data: bytes) -> tuple[str, str]:
    if len(data) < 16 or data[4:8] != b"ftyp":
        return "mp4", "MP4 video"
    size = struct.unpack_from(">I", data, 0)[0]
    major = data[8:12].decode("ascii", "replace").strip("\x00")
    brands = []
    end = min(len(data), max(16, size))
    for offset in range(16, end, 4):
        brand = data[offset:offset + 4].decode("ascii", "replace").strip("\x00")
        if brand:
            brands.append(brand)
    suffix = f"; brands {', '.join(brands[:5])}" if brands else ""
    return major or "mp4", f"MP4 video ({major or 'unknown brand'}{suffix})"


def unity_version_marker(data: bytes) -> str:
    match = UNITY_VERSION_RE.search(data)
    return match.group(0).decode("ascii", "replace") if match else ""


def flatbuffer_summary(data: bytes, size: int) -> str | None:
    layout = flatbuffer_root_layout(data, size)
    if not layout:
        return None
    root_offset, _vtable_pos, object_len, offsets = layout
    present = sum(1 for field_offset in offsets if field_offset)
    return (
        f"FlatBuffer-like binary; root {root_offset}, object {object_len} bytes, "
        f"{len(offsets)} fields, {present} present"
    )


def classify_binary(rel: str, path: Path, size: int, header: bytes) -> tuple[str, str, str]:
    ext = ext_label(path)
    parts = rel.split("/")
    group = parts[0] if parts else ""
    category = category_for_rel(rel)
    words = u32_values(header, 4)
    word_summary = ", ".join(str(value) for value in words[:4])

    if header[4:8] == b"ftyp" or ext == "mp4":
        subtype, summary = mp4_summary(header)
        return "video", subtype, summary

    if ext in VIDEO_EXTENSIONS:
        return "video", ext, f"{ext.upper()} video/media payload; header u32 {word_summary}"

    if ext == "pck":
        stem_lower = path.stem.lower()
        subtype = "banks" if stem_lower.endswith("_banks") else "stream" if "_stream" in stem_lower else "pck"
        payload_shape = "plain AKPK header" if header.startswith(b"AKPK") else "encoded Endfield payload"
        return "wwise-pck", subtype, f"Wwise PCK {subtype} ({payload_shape}); header u32 {word_summary}"

    if ext == "ab":
        version = unity_version_marker(header)
        version_suffix = f"; Unity version marker {version}" if version else ""
        if header.startswith(b"UnityFS"):
            return "asset-bundle", "UnityFS", "Unity asset bundle (plain UnityFS header)" + version_suffix
        return "asset-bundle", "encoded", f"Endfield encoded AssetBundle payload; non-UnityFS header u32 {word_summary}{version_suffix}"

    if ext == "bytes":
        fb_summary = flatbuffer_summary(header, size)
        if fb_summary:
            return "flatbuffer-bytes", category, fb_summary
        if group == "IrradianceVolume":
            subtype = "index" if path.name == "index.bytes" else "region" if path.name.startswith("regionIv") else "volume"
            return "irradiance-volume", subtype, f"Irradiance volume {subtype}; header u32 {word_summary}"
        if group in {"Streaming", "DynamicStreaming"}:
            return "world-streaming-bytes", group.lower(), f"{group} world-streaming chunk; header u32 {word_summary}"
        return "binary-bytes", category, f"Binary .bytes payload; header u32 {word_summary}"

    if ext == "bin":
        subtype = "string-path-hash" if "StringPathHash" in path.name else path.stem
        if "StringPathHash" in path.name and size % 8 == 0:
            rows = size // 8
            return "binary-index", subtype, f"Binary {subtype} table; {rows:,} fixed 8-byte rows; header u32 {word_summary}"
        if "StringPathHash" in path.name:
            return "binary-index", subtype, f"Binary {subtype} table; non-8-byte-aligned encoded payload; header u32 {word_summary}"
        return "binary-index", subtype, f"Binary index {subtype}; header u32 {word_summary}"

    if ext == "hgmmap":
        return "hgmmap", path.stem, f"HGM bundle map/manifest payload; header u32 {word_summary}"

    if ext == "json":
        subtype = category
        return "binary-json", subtype, f"Binary config blob with .json name; header u32 {word_summary}"

    return "binary", ext, f"Binary payload; header u32 {word_summary}"


DECODER_STATUS_FIELD_LIMIT = 24
DECODER_ISSUE_FIELD_LIMIT = 12
DECODER_ISSUE_STATUS_VALUES = {
    "ambiguous-id-marker",
    "count-exceeds-remaining",
    "empty-tail",
    "invalid-count",
    "missing-id-marker",
    "parse-error",
    "switch-marker-not-found",
    "truncated",
}


def collect_decoder_status_fields(
    node: Any,
    *,
    path: str = "decoded",
    limit: int = DECODER_STATUS_FIELD_LIMIT,
) -> list[str]:
    fields: list[str] = []

    def visit(value: Any, current_path: str) -> None:
        if len(fields) >= limit:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if len(fields) >= limit:
                    break
                key_text = str(key)
                item_path = f"{current_path}.{key_text}"
                key_lower = key_text.lower()
                if (
                    key_lower == "status"
                    or key_lower.endswith("status")
                    or key_lower == "error"
                    or key_lower.endswith("error")
                ) and isinstance(item, (str, int, float, bool)):
                    item_text = str(item)
                    if item_text:
                        fields.append(f"{item_path}={item_text}")
                if isinstance(item, (dict, list)):
                    visit(item, item_path)
        elif isinstance(value, list):
            for index, item in enumerate(value[:8]):
                if len(fields) >= limit:
                    break
                if isinstance(item, (dict, list)):
                    visit(item, f"{current_path}[{index}]")

    visit(node, path)
    return fields


def decoder_issue_fields(status_fields: list[str]) -> list[str]:
    issues: list[str] = []
    for field in status_fields:
        name, _sep, value = field.partition("=")
        if ".candidateSummaries[" in name:
            continue
        value_lower = value.lower()
        if value_lower in DECODER_ISSUE_STATUS_VALUES or "parse-error" in value_lower:
            issues.append(field)
        if len(issues) >= DECODER_ISSUE_FIELD_LIMIT:
            break
    return issues


def add_decoder_status_fields(entry: dict[str, Any], decoded: dict[str, Any]) -> None:
    decoded_payload = decoded.get("decoded")
    if not isinstance(decoded_payload, dict):
        return
    status_fields = collect_decoder_status_fields(decoded_payload)
    if status_fields:
        entry["ds"] = status_fields
    issue_fields = decoder_issue_fields(status_fields)
    if issue_fields:
        entry["di"] = issue_fields


def compact_entry(
    rel: str,
    path: Path,
    data_root: Path,
    include_hash: bool = False,
    stat_result: Any | None = None,
    header: bytes | None = None,
) -> dict[str, Any]:
    stat = stat_result or path.stat()
    size = int(stat.st_size)
    header = read_header(path) if header is None else header
    entry: dict[str, Any] = {
        "p": rel,
        "s": size,
        "e": ext_label(path),
        "d": category_for_rel(rel),
        "g": entry_prefix_for_rel(rel),
        "x": hex_signature(header),
    }
    if include_hash:
        entry["hash"] = file_sha256(path)

    encoding = text_json_encoding_from_header(header) if path.suffix.lower() == ".json" else None
    if encoding:
        try:
            payload, used_encoding = load_text_json(path, encoding)
            summary, keys, rows, samples = summarize_json(payload)
            entry.update({
                "k": "text-json",
                "q": used_encoding,
                "h": summary,
            })
            if keys:
                entry["a"] = keys
            if rows is not None:
                entry["r"] = rows
            if samples:
                entry["t"] = samples
            return entry
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            entry.update({
                "k": "json-error",
                "q": type(exc).__name__,
                "h": f"Text-like JSON failed to parse: {exc}",
            })
            return entry

    if path.suffix.lower() == ".json":
        decoded_binary = decode_memorypack_json(rel, path, size, header)
        if decoded_binary:
            entry.update({
                "k": decoded_binary["kind"],
                "q": decoded_binary["subtype"],
                "h": decoded_binary["summary"],
            })
            if decoded_binary.get("rows") is not None:
                entry["r"] = decoded_binary["rows"]
            if decoded_binary.get("keys"):
                entry["a"] = decoded_binary["keys"]
            if decoded_binary.get("sample"):
                entry["t"] = str(decoded_binary["sample"])[:STRING_SAMPLE_MAX_CHARS]
            add_decoder_status_fields(entry, decoded_binary)
            return entry

    if path.suffix.lower() == ".bytes":
        decoded_flatbuffer = decode_flatbuffer_bytes(rel, path, size, header)
        if decoded_flatbuffer:
            entry.update({
                "k": decoded_flatbuffer["kind"],
                "q": decoded_flatbuffer["subtype"],
                "h": decoded_flatbuffer["summary"],
            })
            if decoded_flatbuffer.get("rows") is not None:
                entry["r"] = decoded_flatbuffer["rows"]
            if decoded_flatbuffer.get("keys"):
                entry["a"] = decoded_flatbuffer["keys"]
            if decoded_flatbuffer.get("sample"):
                entry["t"] = str(decoded_flatbuffer["sample"])[:STRING_SAMPLE_MAX_CHARS]
            add_decoder_status_fields(entry, decoded_flatbuffer)
            return entry

    kind, subtype, summary = classify_binary(rel, path, size, header)
    sample_text = ascii_samples(header) or utf16le_samples(header)
    entry.update({
        "k": kind,
        "q": subtype,
        "h": summary,
    })
    if sample_text:
        entry["t"] = sample_text[:STRING_SAMPLE_MAX_CHARS]
    return entry


def wanted_group(path: Path, data_root: Path, selected: set[str] | None) -> bool:
    if not selected:
        return True
    rel = rel_to_data_root(path, data_root)
    return first_group(rel) in selected


def safe_group_filename(group: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", group).strip("_") or "root"


def group_matches_selected(group: str, selected: set[str] | None) -> bool:
    if not selected:
        return True
    return first_group(group) in selected


def aggregate_group_counts(groups: list[dict[str, Any]]) -> dict[str, Any]:
    extensions: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    total_files = 0
    total_bytes = 0
    for group in groups:
        total_files += int(group.get("files") or 0)
        total_bytes += int(group.get("bytes") or 0)
        extensions.update({str(key): int(value) for key, value in (group.get("extensions") or {}).items()})
        kinds.update({str(key): int(value) for key, value in (group.get("kinds") or {}).items()})
    return {
        "files": total_files,
        "bytes": total_bytes,
        "extensions": dict(sorted(extensions.items())),
        "kinds": dict(sorted(kinds.items())),
    }


def build_index(data_root: Path, output: Path, export_root: Path, selected_groups: set[str] | None) -> dict[str, Any]:
    entries_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    group_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "files": 0,
        "bytes": 0,
        "extensions": Counter(),
        "kinds": Counter(),
        "categories": Counter(),
    })
    total_extensions: Counter[str] = Counter()
    total_kinds: Counter[str] = Counter()
    total_files = 0
    total_bytes = 0

    file_infos: list[tuple[Path, str, Any, bytes, tuple[int, str]]] = []
    hash_candidate_keys: Counter[tuple[int, str]] = Counter()
    for path in sorted(data_root.rglob("*")):
        if not (path.is_file() and wanted_group(path, data_root, selected_groups) and should_index_path(path, data_root)):
            continue
        rel = rel_to_data_root(path, data_root)
        stat = path.stat()
        header = read_header(path)
        key = (int(stat.st_size), hex_signature(header))
        file_infos.append((path, rel, stat, header, key))
        hash_candidate_keys[key] += 1

    for path, rel, stat, header, hash_key in file_infos:
        group = index_group_for_rel(rel)
        entry = compact_entry(
            rel,
            path,
            data_root,
            include_hash=hash_candidate_keys[hash_key] > 1,
            stat_result=stat,
            header=header,
        )
        entries_by_group[group].append(entry)

        stats = group_stats[group]
        size = int(entry.get("s") or 0)
        kind = str(entry.get("k") or "unknown")
        ext = str(entry.get("e") or "[none]")
        category = str(entry.get("d") or "[root]")
        stats["files"] += 1
        stats["bytes"] += size
        stats["extensions"][ext] += 1
        stats["kinds"][kind] += 1
        stats["categories"][category] += 1
        total_files += 1
        total_bytes += size
        total_extensions[ext] += 1
        total_kinds[kind] += 1

    try:
        source_root = data_root.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        source_root = data_root.resolve().as_posix()
    try:
        export_root_rel = export_root.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        export_root_rel = export_root.resolve().as_posix()

    groups_dir = output / "groups"
    groups_dir.mkdir(parents=True, exist_ok=True)
    existing_index: dict[str, Any] | None = None
    existing_index_path = output / "index.json"
    if selected_groups and existing_index_path.exists():
        try:
            loaded_index = json.loads(existing_index_path.read_text(encoding="utf-8"))
            if loaded_index.get("sourceRoot") == source_root and loaded_index.get("exportRoot") == export_root_rel:
                existing_index = loaded_index
        except (OSError, json.JSONDecodeError):
            existing_index = None

    if selected_groups and existing_index:
        stale_files = []
        for group in existing_index.get("groups", []):
            group_id = str(group.get("id") or "")
            file_rel = str(group.get("file") or "")
            if file_rel and group_matches_selected(group_id, selected_groups):
                stale_files.append(output / file_rel)
    else:
        stale_files = list(groups_dir.glob("*.json"))

    for stale_group in stale_files:
        try:
            stale_group.unlink()
        except FileNotFoundError:
            pass
    group_payloads: list[dict[str, Any]] = []
    for group in sorted(entries_by_group):
        entries = entries_by_group[group]
        entries.sort(key=lambda item: str(item.get("p") or "").lower())
        filename = safe_group_filename(group) + ".json"
        write_json(groups_dir / filename, {
            "group": group,
            "entries": entries,
        })
        stats = group_stats[group]
        group_payloads.append({
            "id": group,
            "file": f"groups/{filename}",
            "files": int(stats["files"]),
            "bytes": int(stats["bytes"]),
            "extensions": dict(sorted(stats["extensions"].items())),
            "kinds": dict(sorted(stats["kinds"].items())),
            "categories": dict(stats["categories"].most_common(80)),
        })

    if selected_groups and existing_index:
        preserved_groups = [
            group
            for group in existing_index.get("groups", [])
            if not group_matches_selected(str(group.get("id") or ""), selected_groups)
        ]
        group_payloads = sorted(
            preserved_groups + group_payloads,
            key=lambda group: str(group.get("id") or ""),
        )
    else:
        group_payloads.sort(key=lambda group: str(group.get("id") or ""))

    aggregate_counts = aggregate_group_counts(group_payloads)
    payload = {
        "generated": int(time.time()),
        "sourceRoot": source_root,
        "exportRoot": export_root_rel,
        "rawRoute": "/export_data/",
        "counts": aggregate_counts,
        "requiresGroupSelection": int(aggregate_counts.get("files") or 0) > AUTO_LOAD_ALL_FILE_LIMIT,
        "autoLoadAllLimit": AUTO_LOAD_ALL_FILE_LIMIT,
        "groups": group_payloads,
    }
    write_json(output / "index.json", payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_root = args.export_root
    data_root = args.data_root or (export_root / DEFAULT_DATA_REL)
    if not data_root.exists():
        raise SystemExit(f"Data root not found: {data_root}")

    selected_groups = set(args.groups) if args.groups else None
    args.output.mkdir(parents=True, exist_ok=True)
    payload = build_index(data_root, args.output, export_root, selected_groups)
    counts = payload["counts"]
    print(
        "Game data index written:",
        normalize_posix(args.output),
        (
            f"({counts['files']:,} files; {counts['bytes'] / (1024 * 1024):.1f} MiB; "
            f"{len(payload['groups'])} group(s))"
        ),
    )
    for group in payload["groups"]:
        print(
            f"  {group['id']}: {group['files']:,} files, "
            f"{group['bytes'] / (1024 * 1024):.1f} MiB"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
