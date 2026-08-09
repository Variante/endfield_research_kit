from __future__ import annotations

import re
import struct
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from common import read_bytes_cached


LEVELSCRIPT_START_TYPE_NAMES = {
    0: "ByEnterStartShape",
    1: "Manual",
    2: "SameWithActive",
    3: "Never",
}

LEVELSCRIPT_END_TYPE_NAMES = {
    0: "Auto",
    1: "ByExitStartShape",
    2: "Manual",
    3: "SameWithDeactive",
    4: "Never",
}

# ``LevelScriptTriggerVolumeData`` is a MemoryPack union.  The current
# installed formatter assigns tag 1 to the no-extra-field Leader subtype; its
# payload then serializes the eight base members in generated setter order.
# Other subtype bodies are intentionally not decoded until their derived
# formatter layouts are proven from current blobs.
LEVELSCRIPT_TRIGGER_VOLUME_UNION_TAG_NAMES = {
    1: "Leader",
}

LEVELSCRIPT_TRIGGER_VOLUME_SCHEMA_MAPPING_ID = (
    "current-global-metadata-levelscript-trigger-volume-data-fields"
)
LEVELSCRIPT_TRIGGER_VOLUME_BASE_FIELDS = [
    "isImportant",
    "waitSrvRes",
    "enterCheckOnGround",
    "triggerOnPole",
    "slotId",
    "triggerCountLimit",
    "exitShapeStartIndex",
    "shapeList",
]
LEVELSCRIPT_TRIGGER_VOLUME_SERIALIZED_FIELDS = [
    "enterCheckOnGround",
    "exitShapeStartIndex",
    "isImportant",
    "shapeList",
    "slotId",
    "triggerCountLimit",
    "triggerOnPole",
    "waitSrvRes",
]

SCRIPT_POINTER_REF_RECORDS = {
    (0x045D, 0x0A),
}

# Exact current-build ActionHeader identities recovered from the installed
# ActionHeaderForMemoryPack formatter and global-metadata.dat. Keep this table
# version-scoped: historical exports use different serialized codes for some
# of the same event classes (notably OnDialogExit).
LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionheader"
)
LEVELSCRIPT_NATIVE_HEADER_NAMES: dict[tuple[int, int], str] = {
    (0x1052, 0x00): "LevelEvent_OnCustomEvent",
    (0x1054, 0x00): "LevelEvent_OnDialogEnter",
    (0x12BA, 0x00): "ScriptEvent_OnCustomEvent",
    (0x12BE, 0x00): "ScriptEvent_OnLeaderEnterTriggerVolume",
    (0x12C0, 0x00): "ScriptEvent_OnLeaderLeaveTriggerVolume",
    (0x126A, 0x00): "LevelEvent_OnEntityHpChanged",
    (0x1355, 0x00): "LevelEvent_OnDialogExit",
    (0x1385, 0x00): "LevelEvent_OnQuestStateChanged",
    (0x141E, 0x00): "EntityEvent_OnInteractiveStateChanged",
}

# Canonical current-build identities. The older table above remains for
# report/tests that still carry the compact parser's combined observed pair.
LEVELSCRIPT_NATIVE_HEADER_TAG_NAMES: dict[tuple[int, int], str] = {
    (0x0052, 0x10): "LevelEvent_OnCustomEvent",
    (0x0054, 0x10): "LevelEvent_OnDialogEnter",
    (0x00BA, 0x12): "ScriptEvent_OnCustomEvent",
    (0x00BE, 0x12): "ScriptEvent_OnLeaderEnterTriggerVolume",
    (0x00C0, 0x12): "ScriptEvent_OnLeaderLeaveTriggerVolume",
    (0x006A, 0x12): "LevelEvent_OnEntityHpChanged",
    (0x0055, 0x13): "LevelEvent_OnDialogExit",
    (0x0085, 0x13): "LevelEvent_OnQuestStateChanged",
    (0x001E, 0x14): "EntityEvent_OnInteractiveStateChanged",
}

# Complete current-build ActionHeaderForMemoryPack union registration table.
# GameAssembly cctor VA 0x1843bb480 registers contiguous tags 0x0000..0x00e5
# through helper 0x183ead480. Union identity is selected by the tag; the
# concrete subtype member count remains separately retained on decoded records
# as a payload-shape guard.
LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES: dict[int, str] = {
    0x0000: "EntityEvent_OnAbandonPackInteract",
    0x0001: "EntityEvent_OnAirborneApplied",
    0x0002: "EntityEvent_OnBBVariableChanged",
    0x0003: "EntityEvent_OnBeingBombed",
    0x0004: "EntityEvent_OnBeingScanned",
    0x0005: "EntityEvent_OnComboSkillActivated",
    0x0006: "EntityEvent_OnComboSkillTimeout",
    0x0007: "EntityEvent_OnCustomEvent",
    0x0008: "EntityEvent_OnCustomEventNew",
    0x0009: "EntityEvent_OnDefaultEvent",
    0x000A: "EntityEvent_OnDefaultEvent2",
    0x000B: "EntityEvent_OnDestructiblePhysicsDestroy",
    0x000C: "EntityEvent_OnElectricPowerChanged",
    0x000D: "EntityEvent_OnElectricSignal",
    0x000E: "EntityEvent_OnEntityDestroy",
    0x000F: "EntityEvent_OnEntityDie",
    0x0010: "EntityEvent_OnEntityDieEnd",
    0x0011: "EntityEvent_OnEntityDieStart",
    0x0012: "EntityEvent_OnEntityEnterTrigger",
    0x0013: "EntityEvent_OnEntityLeaveTrigger",
    0x0014: "EntityEvent_OnEntityReceiveWaterDroneAttack",
    0x0015: "EntityEvent_OnEntityStart",
    0x0016: "EntityEvent_OnFactoryInstOptionAdded",
    0x0017: "EntityEvent_OnFactoryInstOptionRemoved",
    0x0018: "EntityEvent_OnFactoryInstRepaired",
    0x0019: "EntityEvent_OnFactoryInstSetup",
    0x001A: "EntityEvent_OnFactoryInstStateChanged",
    0x001B: "EntityEvent_OnFactoryInstTypeUpdate",
    0x001C: "EntityEvent_OnHpChanged",
    0x001D: "EntityEvent_OnInteractiveScMove",
    0x001E: "EntityEvent_OnInteractiveStateChanged",
    0x001F: "EntityEvent_OnIntHpZero",
    0x0020: "EntityEvent_OnIntLocked",
    0x0021: "EntityEvent_OnIntReceiveAttack",
    0x0022: "EntityEvent_OnIntSubmitSuccess",
    0x0023: "EntityEvent_OnIntTryUnlock",
    0x0024: "EntityEvent_OnIntUnlocked",
    0x0025: "EntityEvent_OnIntUnlockFailed",
    0x0026: "EntityEvent_OnKnockBackApplied",
    0x0027: "EntityEvent_OnKnockDownApplied",
    0x0028: "EntityEvent_OnLeaderEnterLogicStartArea",
    0x0029: "EntityEvent_OnLeaderEnterTrigger",
    0x002A: "EntityEvent_OnLeaderEnterTriggerArea",
    0x002B: "EntityEvent_OnLeaderExitLogicStartArea",
    0x002C: "EntityEvent_OnLeaderLeaveTrigger",
    0x002D: "EntityEvent_OnLeaderLeaveTriggerArea",
    0x002E: "EntityEvent_OnMonsterEnterTrigger",
    0x002F: "EntityEvent_OnMonsterLeaveTrigger",
    0x0030: "EntityEvent_OnPhysicalInfliction",
    0x0031: "EntityEvent_OnPhysicalNoGuard",
    0x0032: "EntityEvent_OnPhysicalStatusApplied",
    0x0033: "EntityEvent_OnPoiseKnotBreak",
    0x0034: "EntityEvent_OnPoiseZero",
    0x0035: "EntityEvent_OnPropertyChanged",
    0x0036: "EntityEvent_OnSavepointReach",
    0x0037: "EntityEvent_OnSavePropertyChanged",
    0x0038: "EntityEvent_OnTargetNodeReached",
    0x0039: "EntityEvent_OnTriggerDisabled",
    0x003A: "EntityEvent_OnTriggerEnabled",
    0x003B: "EntityEvent_OnUIFacInteract",
    0x003C: "EntityEvent_OnUIFunction",
    0x003D: "EntityEvent_OnUIInteract",
    0x003E: "EntityEvent_OnVisibleChanged",
    0x003F: "EntityEventHeader",
    0x0040: "LevelEvent_OnAetherEnergyLockEndPointScanned",
    0x0041: "LevelEvent_OnAetherEnergyLockMidPointScanned",
    0x0042: "LevelEvent_OnAnyEnemyPoiseKnotBreak",
    0x0043: "LevelEvent_OnAnyEnemyPoiseZero",
    0x0044: "LevelEvent_OnAnyEntityChangeMode",
    0x0045: "LevelEvent_OnAnyEntityDie",
    0x0046: "LevelEvent_OnAnyEntityStart",
    0x0047: "LevelEvent_OnAtbZero",
    0x0048: "LevelEvent_OnAudioStateChanged",
    0x0049: "LevelEvent_OnBattlerActivated",
    0x004A: "LevelEvent_OnBattlerCompleted",
    0x004B: "LevelEvent_OnBattlerStageChanged",
    0x004C: "LevelEvent_OnBattleSignal",
    0x004D: "LevelEvent_OnBlightMiasmaAreaEnter",
    0x004E: "LevelEvent_OnBlightMiasmaWeakGuide",
    0x004F: "LevelEvent_OnCharacterPerfectDodge",
    0x0050: "LevelEvent_OnCountdownFinish",
    0x0051: "LevelEvent_OnCurveMoveReachNode",
    0x0052: "LevelEvent_OnCustomEvent",
    0x0053: "LevelEvent_OnCutsceneExit",
    0x0054: "LevelEvent_OnDialogEnter",
    0x0055: "LevelEvent_OnDialogExit",
    0x0056: "LevelEvent_OnDynamicTriggerEnter",
    0x0057: "LevelEvent_OnDynamicTriggerLeave",
    0x0058: "LevelEvent_OnEncounterActivated",
    0x0059: "LevelEvent_OnEncounterBattlePartBegin",
    0x005A: "LevelEvent_OnEncounterBattlePartEnd",
    0x005B: "LevelEvent_OnEncounterIntroPartBegin",
    0x005C: "LevelEvent_OnEncounterIntroPartEnd",
    0x005D: "LevelEvent_OnEncounterSurvivalBattlePartBegin",
    0x005E: "LevelEvent_OnEncounterSurvivalBattlePartEnd",
    0x005F: "LevelEvent_OnEncounterSurvivalIntroPartBegin",
    0x0060: "LevelEvent_OnEncounterSurvivalIntroPartEnd",
    0x0061: "LevelEvent_OnEncounterSurvivalTailPartBegin",
    0x0062: "LevelEvent_OnEncounterSurvivalTailPartEnd",
    0x0063: "LevelEvent_OnEncounterTailPartBegin",
    0x0064: "LevelEvent_OnEncounterTailPartEnd",
    0x0065: "LevelEvent_OnEnemyInFight",
    0x0066: "LevelEvent_OnEnemyPatrolEvent",
    0x0067: "LevelEvent_OnEnemyPoiseRecover",
    0x0068: "LevelEvent_OnEnemyTakeLastAttackDamage",
    0x0069: "LevelEvent_OnEntityCastSkill",
    0x006A: "LevelEvent_OnEntityHpChanged",
    0x006B: "LevelEvent_OnEntityTakeDamage",
    0x006C: "LevelEvent_OnEntityWeaknessTriggered",
    0x006D: "LevelEvent_OnFogNestCompleted",
    0x006E: "LevelEvent_OnGameplayNpcInteract",
    0x006F: "LevelEvent_OnGuideButterflyLsmReset",
    0x0070: "LevelEvent_OnGuideGroupComplete",
    0x0071: "LevelEvent_OnKickableBallDestroyed",
    0x0072: "LevelEvent_OnKickableBallInsideSpawner",
    0x0073: "LevelEvent_OnKickableBallOutsideSpawner",
    0x0074: "LevelEvent_OnKickableReceiverPopUp",
    0x0075: "LevelEvent_OnKickableTriggerInvoke",
    0x0076: "LevelEvent_OnLevelReset",
    0x0077: "LevelEvent_OnLinkWireModeEnd",
    0x0078: "LevelEvent_OnMainCharacterChanged",
    0x0079: "LevelEvent_OnMissionStateChanged",
    0x007A: "LevelEvent_OnMusicBeatEvent",
    0x007B: "LevelEvent_OnNpcDirtyBlockCleaned",
    0x007C: "LevelEvent_OnNpcPatrolCheckpointReach",
    0x007D: "LevelEvent_OnNpcPatrolStart",
    0x007E: "LevelEvent_OnNpcPatrolStop",
    0x007F: "LevelEvent_OnNpcReceiveAttack",
    0x0080: "LevelEvent_OnNpcSwitchToAIBehaviorEnd",
    0x0081: "LevelEvent_OnNpcSwitchToAIBehaviorStart",
    0x0082: "LevelEvent_OnPatrolEvent",
    0x0083: "LevelEvent_OnPlayerHitByAnchorWave",
    0x0084: "LevelEvent_OnProxyPatrolCheckpointReach",
    0x0085: "LevelEvent_OnQuestStateChanged",
    0x0086: "LevelEvent_OnRpgLevelUpAbilityStart",
    0x0087: "LevelEvent_OnSafeZoneScanHit",
    0x0088: "LevelEvent_OnScriptedCharPatrolEvent",
    0x0089: "LevelEvent_OnScriptedEnemyEvent",
    0x008A: "LevelEvent_OnServerDialogExit",
    0x008B: "LevelEvent_OnSetInSafeZone",
    0x008C: "LevelEvent_OnSkipBattlePopupConfirm",
    0x008D: "LevelEvent_OnSnailWaterFillingFinish",
    0x008E: "LevelEvent_OnSnapShotEnter",
    0x008F: "LevelEvent_OnSnapShotLeave",
    0x0090: "LevelEvent_OnSpawnerComplete",
    0x0091: "LevelEvent_OnSpawnerEntityDie",
    0x0092: "LevelEvent_OnSpawnerEntityDieEnd",
    0x0093: "LevelEvent_OnSpawnerEntityDieStart",
    0x0094: "LevelEvent_OnSpawnerEntitySpawn",
    0x0095: "LevelEvent_OnSpawnerEvent",
    0x0096: "LevelEvent_OnSpawnerGroupBegin",
    0x0097: "LevelEvent_OnSpawnerGroupComplete",
    0x0098: "LevelEvent_OnSpawnerMonsterWaveAllDieEnd",
    0x0099: "LevelEvent_OnSpawnerMonsterWaveAllDieStart",
    0x009A: "LevelEvent_OnSpawnerPause",
    0x009B: "LevelEvent_OnSpawnerStart",
    0x009C: "LevelEvent_OnSpawnerStop",
    0x009D: "LevelEvent_OnSpawnerWaveBegin",
    0x009E: "LevelEvent_OnSpawnerWaveComplete",
    0x009F: "LevelEvent_OnSpawnerWavePreComplete",
    0x00A0: "LevelEvent_OnSpecificEntityDie",
    0x00A1: "LevelEvent_OnSpecificEntityListDie",
    0x00A2: "LevelEvent_OnSpellAbnormalFinish",
    0x00A3: "LevelEvent_OnSpellAbnormalStart",
    0x00A4: "LevelEvent_OnSpellInfliction",
    0x00A5: "LevelEvent_OnSpotDiffMainStakeStateChanged",
    0x00A6: "LevelEvent_OnSquadAllMemberDie",
    0x00A7: "LevelEvent_OnSquadInFightChanged",
    0x00A8: "LevelEvent_OnSquadMemberUspReachMax",
    0x00A9: "LevelEvent_OnStartCharScriptedMode",
    0x00AA: "LevelEvent_OnSuperPressureBoardGroupSequenceFailed",
    0x00AB: "LevelEvent_OnTeleportFinish",
    0x00AC: "LevelEvent_OnTrainLevelEvent",
    0x00AD: "LevelEvent_OnTravelPoleBegin",
    0x00AE: "LevelEvent_OnTravelPoleEnter",
    0x00AF: "LevelEvent_OnTravelPoleExit",
    0x00B0: "LevelEvent_OnTravelPoleReach",
    0x00B1: "LevelEvent_OnWaterVolumeChanged",
    0x00B2: "LevelEvent_OnWeekRaidDangerChange",
    0x00B3: "LevelEvent_OnWeekRaidSettlement",
    0x00B4: "LevelEventHeader",
    0x00B5: "MissionEvent_OnClientGlobalVarChanged",
    0x00B6: "MissionEvent_OnCustomEventForMission",
    0x00B7: "MissionEvent_OnServerGlobalVarChanged",
    0x00B8: "MissionEventHeader",
    0x00B9: "ScriptEvent_OnBBVariableChanged",
    0x00BA: "ScriptEvent_OnCustomEvent",
    0x00BB: "ScriptEvent_OnKickableInteractiveEnterTriggerVolume",
    0x00BC: "ScriptEvent_OnKickableInteractiveEnterTriggerVolumeList",
    0x00BD: "ScriptEvent_OnKickableInteractiveLeaveTriggerVolume",
    0x00BE: "ScriptEvent_OnLeaderEnterTriggerVolume",
    0x00BF: "ScriptEvent_OnLeaderEnterTriggerVolumeList",
    0x00C0: "ScriptEvent_OnLeaderLeaveTriggerVolume",
    0x00C1: "ScriptEvent_OnLeaderLeaveTriggerVolumeList",
    0x00C2: "ScriptEvent_OnPropertyChanged",
    0x00C3: "ScriptEvent_OnScriptActive",
    0x00C4: "ScriptEvent_OnScriptComplete",
    0x00C5: "ScriptEvent_OnScriptEnd",
    0x00C6: "ScriptEvent_OnScriptMarkDone",
    0x00C7: "ScriptEvent_OnScriptPreActive",
    0x00C8: "ScriptEvent_OnScriptPreStart",
    0x00C9: "ScriptEvent_OnScriptStageChanged",
    0x00CA: "ScriptEvent_OnScriptStart",
    0x00CB: "ScriptEvent_OnScriptTick",
    0x00CC: "ScriptEvent_OnStartScriptControlledCharMode",
    0x00CD: "ScriptEvent_OnTeammateEnterTriggerVolume",
    0x00CE: "ScriptEvent_OnTeammateEnterTriggerVolumeList",
    0x00CF: "ScriptEvent_OnTeammateLeaveTriggerVolume",
    0x00D0: "ScriptEvent_OnTeammateLeaveTriggerVolumeList",
    0x00D1: "ScriptEventHeader",
    0x00D2: "Conditions_OnGlobalBuffAdded",
    0x00D3: "OnAnchorWaveProbeHit",
    0x00D4: "OnBeaconPoleLsmGuidingDecoChanged",
    0x00D5: "OnDecorationLoadDone",
    0x00D6: "OnEnterFocusMode",
    0x00D7: "OnForgeIronCameraShake",
    0x00D8: "OnHitByLaser",
    0x00D9: "OnHitByLaserEntity",
    0x00DA: "OnLeaveFocusMode",
    0x00DB: "OnMapVarChanged",
    0x00DC: "OnRopePortPlayAnim",
    0x00DD: "OnSettlementLevelUpFinish",
    0x00DE: "OnSettlementReadyPerformance",
    0x00DF: "OnSignalTowerScan",
    0x00E0: "OnSquadChangeFinish",
    0x00E1: "OnSubGameComplete",
    0x00E2: "OnSubGameEnterExitingPhase",
    0x00E3: "OnSubGameStart",
    0x00E4: "OnTianshizhuangActivate",
    0x00E5: "OnTianshizhuangFinish",
}


def levelscript_record_semantic_key(record: dict[str, Any]) -> tuple[int, int]:
    """Return normalized ``(MemoryPack union tag, subtype member count)``."""
    union_tag = record.get("unionTag")
    member_count = record.get("serializedMemberCount")
    if isinstance(union_tag, int) and isinstance(member_count, int):
        return union_tag, member_count
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        compact_tag = code & 0xFF
        compact_member_count = code >> 8
        if (
            code > 0xFF
            and compact_tag < 0xFA
            and compact_member_count <= 0x40
            and kind in (0, 1)
            and record.get("layout") != "fa"
        ):
            return compact_tag, compact_member_count
        return code, kind
    return -1, -1


def levelscript_native_header_name(
    record: dict[str, Any],
    *,
    allow_union_tag_fallback: bool = False,
) -> str:
    semantic_key = levelscript_record_semantic_key(record)
    name = LEVELSCRIPT_NATIVE_HEADER_TAG_NAMES.get(semantic_key)
    if name:
        return name
    if allow_union_tag_fallback:
        name = LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES.get(semantic_key[0])
        if name:
            return name
    code = record.get("code")
    kind = record.get("kind")
    return LEVELSCRIPT_NATIVE_HEADER_NAMES.get((code, kind), "")

LEVELSCRIPT_RECORD_HINTS = {
    (0x002D, 0x09): {
        "label": "actionbase-branch-sequence",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to Branch; "
            "GameAssembly Branch.Execute consumes _idList in index order"
        ),
        "actionBaseAction": "Branch",
    },
    (0x00FF, 0x0B): {
        "label": "actionbase-if-else",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to IfElseAction",
        "actionBaseAction": "IfElseAction",
    },
    (0x04BD, 0x0C): {
        "label": "actionbase-switch-int",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SwitchInt",
        "actionBaseAction": "SwitchInt",
    },
    (0x04BE, 0x0C): {
        "label": "actionbase-switch-int-larger",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "SwitchIntLarger; its Execute body selects serialized case/default ids"
        ),
        "actionBaseAction": "SwitchIntLarger",
    },
    (0x04BF, 0x0C): {
        "label": "actionbase-switch-string",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "SwitchString; generated setters serialize _caseIDList, "
            "_caseValueList, _defaultID, then _value"
        ),
        "actionBaseAction": "SwitchString",
    },
    (0x0495, 0x09): {
        "label": "actionbase-split",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to Split",
        "actionBaseAction": "Split",
    },
    (0x04F6, 0x08): {
        "label": "actionbase-wait-one-frame",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to WaitForOneFrame",
        "actionBaseAction": "WaitForOneFrame",
    },
    (0x04F5, 0x09): {
        "label": "actionbase-wait-for-npc-proxy-ready",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to WaitForNpcProxyReady",
        "actionBaseAction": "WaitForNpcProxyReady",
    },
    (0x04F9, 0x0E): {
        "label": "actionbase-wait-seconds-trigger-volume",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "WaitForSecondsInTriggerVolume; inherited generated setters expose "
            "_failID, _seconds, and _successID before _scriptPtr and _triggerSlotId"
        ),
        "actionBaseAction": "WaitForSecondsInTriggerVolume",
    },
    (0x02FE, 0x0A): {
        "label": "actionbase-main-char-move-to",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "MainCharMoveTo; generated setters name _endPos and _groundedMoveGait"
        ),
        "actionBaseAction": "MainCharMoveTo",
    },
    (0x04CA, 0x09): {
        "label": "actionbase-toggle-clear-screen-but-radio",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "ToggleClearScreenButRadio; its generated setter names _isShow"
        ),
        "actionBaseAction": "ToggleClearScreenButRadio",
        "presentationRole": "toggle-clear-screen-but-radio",
    },
    (0x0376, 0x0C): {
        "label": "actionbase-preload-cutscene",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to PreloadCutsceneAction",
        "actionBaseAction": "PreloadCutsceneAction",
    },
    (0x037E, 0x0A): {
        "label": "actionbase-raise-custom-level-event",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to RaiseCustomLevelEvent",
        "actionBaseAction": "RaiseCustomLevelEvent",
    },
    (0x0380, 0x0B): {
        "label": "actionbase-raise-custom-script-event",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "RaiseCustomScriptEvent"
        ),
        "actionBaseAction": "RaiseCustomScriptEvent",
    },
    (0x0304, 0x09): {
        "label": "actionbase-manually-start-guide-group",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "ManuallyStartGuideGroup"
        ),
        "actionBaseAction": "ManuallyStartGuideGroup",
    },
    (0x0455, 0x0A): {
        "label": "actionbase-set-override-interact-dialog",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "SetOverrideInteractDialog"
        ),
        "actionBaseAction": "SetOverrideInteractDialog",
    },
    (0x045D, 0x0A): {
        "label": "actionbase-set-script-task-ptr",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to SetScriptTaskPtr; "
            "payloads may carry a LevelScriptPtr-like value but not a literal levelId+scriptId"
        ),
        "actionBaseAction": "SetScriptTaskPtr",
    },
    (0x0463, 0x09): {
        "label": "actionbase-set-squad-member-pos-rot",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetSquadMemberPosRot",
        "actionBaseAction": "SetSquadMemberPosRot",
    },
    (0x02EE, 0x09): {
        "label": "guide-prompt",
        "confidence": "medium",
        "note": "payload carries guide_* ids and usually precedes tutorial radio/dialog flow",
    },
    (0x0E34, 0x00): {
        "label": "actionbase-call-server",
        "confidence": "high",
        "note": (
            "compact MemoryPack tag 0x34 with member count 0x0e maps to "
            "CallServer; generated setters name the event-args, event-name, "
            "callback, and custom-event fields"
        ),
        "actionBaseAction": "CallServer",
        "networkRole": "server-handoff",
    },
    (0x104A, 0x00): {
        "label": "float-property-signal",
        "confidence": "medium",
        "note": "payload carries a named signal plus an auto-named _floatValue property",
    },
    (0x03B8, 0x0A): {
        "label": "actionbase-set-buff-ptr",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "Set<Beyond.Gameplay.Core.BuffPtr>"
        ),
        "propertyRole": "property-setter",
        "propertyValueType": "BuffPtr",
        "actionBaseAction": "Set<BuffPtr>",
    },
    (0x03E7, 0x0A): {
        "label": "actionbase-set-child-game-object-active",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "SetChildGameObjectActive"
        ),
        "actionBaseAction": "SetChildGameObjectActive",
    },
    (0x03EA, 0x0A): {
        "label": "actionbase-set-current-terminal-reading-index",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "SetCurrentTerminalReadingIndex"
        ),
        "actionBaseAction": "SetCurrentTerminalReadingIndex",
    },
    (0x0176, 0x08): {
        "label": "actionbase-list-add-value-uint64",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to ListAddValueUInt64"
        ),
        "propertyRole": "property-list-add",
        "propertyValueType": "uint64-list",
        "actionBaseAction": "ListAddValueUInt64",
    },
    (0x0166, 0x0A): {
        "label": "actionbase-list-add-value-entity-ptr",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "ListAddValueEntityPtr"
        ),
        "propertyRole": "property-list-add",
        "propertyValueType": "entity-ptr-list",
        "actionBaseAction": "ListAddValueEntityPtr",
    },
    (0x02EC, 0x0A): {
        "label": "actionbase-list-shuffle-int64",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to ListShuffleInt64"
        ),
        "actionBaseAction": "ListShuffleInt64",
    },
    (0x02F1, 0x0A): {
        "label": "actionbase-list-shuffle-script-entity-ptr",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "ListShuffleScriptEntityPtr"
        ),
        "actionBaseAction": "ListShuffleScriptEntityPtr",
    },
    (0x0302, 0x0A): {
        "label": "actionbase-manual-end-levelscript",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to ManualEndLevelScript",
        "levelScriptControlRole": "manual-end",
        "actionBaseAction": "ManualEndLevelScript",
    },
    (0x0308, 0x0A): {
        "label": "actionbase-manual-start-levelscript",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to ManualStartLevelScript",
        "levelScriptControlRole": "manual-start",
        "actionBaseAction": "ManualStartLevelScript",
    },
    (0x03DA, 0x0A): {
        "label": "actionbase-set-bool",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetBool",
        "propertyRole": "property-setter",
        "propertyValueType": "bool",
        "actionBaseAction": "SetBool",
    },
    (0x0410, 0x0A): {
        "label": "actionbase-set-int",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetInt",
        "propertyRole": "property-setter",
        "propertyValueType": "int",
        "actionBaseAction": "SetInt",
    },
    (0x0413, 0x0A): {
        "label": "actionbase-set-int-increase",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetIntIncrease",
        "propertyRole": "property-setter",
        "propertyValueType": "int",
        "actionBaseAction": "SetIntIncrease",
    },
    (0x0501, 0x0A): {
        "label": "actionbase-while",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "WhileAction; generated setters serialize _condition before _doID"
        ),
        "actionBaseAction": "WhileAction",
    },
    (0x0A03, 0x00): {
        "label": "property-key-gate",
        "confidence": "medium",
        "note": (
            "compact condition/gate payload carries a property key, type code, post flag, "
            "and sometimes a tail local action ref; this code is outside all extracted "
            "MemoryPack union formatter tag ranges, so treat it as a gate/read shape until "
            "its non-union runtime family is decoded"
        ),
        "propertyRole": "property-key-gate",
    },
    (0x0BED, 0x00): {
        "label": "property-key-terminal-branch",
        "confidence": "medium",
        "note": (
            "payload carries a bool/scalar-looking prefix and a property key on a terminal-looking "
            "record, with tail integers that resolve to local record ids in observed scripts; it is "
            "outside all extracted MemoryPack union formatter tag ranges, so it remains a compact "
            "terminal/completion branch bridge rather than generic Set<bool> proof"
        ),
        "propertyRole": "property-key-terminal",
    },
    (0x094C, 0x00): {
        "label": "property-key-control",
        "confidence": "low",
        "note": "payload carries a property key near control records; exact role is not named",
        "propertyRole": "property-key-control",
    },
    (0x094D, 0x00): {
        "label": "property-key-control",
        "confidence": "low",
        "note": "payload carries a property key near control records; exact role is not named",
        "propertyRole": "property-key-control",
    },
    (0x0A14, 0x00): {
        "label": "trigger-volume-slot-gate",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids in a scalar gate/control record",
    },
    (0x012F, 0x07): {
        "label": "trigger-volume-slot-control",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids near trigger-volume event/check records",
    },
    (0x09C5, 0x00): {
        "label": "trigger-volume-slot-control",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids near trigger-volume event/check records",
    },
    (0x1093, 0x00): {
        "label": "trigger-volume-entity-output",
        "confidence": "low",
        "note": "payload carries trigger-volume slot ids and entity/instance output refs in some scripts",
    },
    (0x107B, 0x00): {
        "label": "trigger-volume-related-control",
        "confidence": "low",
        "note": "payload may carry trigger-volume slot ids inside a larger control/event record",
    },
    (0x10A6, 0x00): {
        "label": "trigger-volume-related-control",
        "confidence": "low",
        "note": "payload appears near trigger-volume event records; exact role is not named",
    },
    (0x0362, 0x0A): {
        "label": "named-signal",
        "confidence": "low",
        "note": "payload carries authored signal/key text used around levelseq/cutscene control",
    },
    (0x092A, 0x00): {
        "label": "boolean-or-flag-check",
        "confidence": "low",
        "note": "single scalar/flag-shaped payload; exact condition class is not named",
    },
    (0x093E, 0x00): {
        "label": "boolean-or-flag-check",
        "confidence": "low",
        "note": "single scalar/flag-shaped payload; exact condition class is not named",
    },
    (0x0B20, 0x00): {
        "label": "actionbase-black-screen-fade-out",
        "confidence": "high",
        "note": (
            "compact MemoryPack tag 0x20 with member count 0x0b maps to "
            "BlackScreenFadeOut; 0x0b20/0x00 is the legacy parser's combined observed pair"
        ),
        "actionBaseAction": "BlackScreenFadeOut",
    },
    (0x0952, 0x00): {
        "label": "actionbase-check-bool-if-true",
        "confidence": "high",
        "note": (
            "compact MemoryPack tag 0x52 with member count 0x09 maps to "
            "CheckBoolIfTrue; 0x0952/0x00 is the legacy parser's combined observed pair"
        ),
        "actionBaseAction": "CheckBoolIfTrue",
    },
    (0x09B9, 0x00): {
        "label": "actionbase-exit-level-custom-performance",
        "confidence": "high",
        "note": (
            "compact MemoryPack tag 0xb9 with member count 0x09 maps to "
            "ExitLevelCustomPerformance; 0x09b9/0x00 is the legacy parser's "
            "combined observed pair"
        ),
        "actionBaseAction": "ExitLevelCustomPerformance",
        "presentationRole": "exit-level-custom-performance",
    },
    (0x04B8, 0x09): {
        "label": "uid-keyed-control",
        "confidence": "low",
        "note": "payload carries a short uid/key string; exact class is not named",
    },
    (0x1280, 0x00): {
        "label": "branch-or-state-control",
        "confidence": "low",
        "note": "payload carries numeric state text and optional authored key; exact class is not named",
    },
}

LEVELSCRIPT_RECORD_TAG_HINTS = {
    (0x0020, 0x0B): LEVELSCRIPT_RECORD_HINTS[(0x0B20, 0x00)],
    (0x0052, 0x09): LEVELSCRIPT_RECORD_HINTS[(0x0952, 0x00)],
    (0x00B9, 0x09): LEVELSCRIPT_RECORD_HINTS[(0x09B9, 0x00)],
    (0x0034, 0x0E): LEVELSCRIPT_RECORD_HINTS[(0x0E34, 0x00)],
    (0x0003, 0x0A): LEVELSCRIPT_RECORD_HINTS[(0x0A03, 0x00)],
    (0x00ED, 0x0B): LEVELSCRIPT_RECORD_HINTS[(0x0BED, 0x00)],
}

PROPERTY_OUTPUT_RE = re.compile(
    r"^\$(?P<local>\d+)@_(?P<name>"
    r"oldValue|value|result|floatValue|entityOutput|instKeyOutput|"
    r"eventArgsPtr|triggerSlotIdOutput|guideId|groupKeyOutput|"
    r"spawnerOutput|waveKeyOutput|dialogId|finishId|isSkipped|newStageOutput|"
    r"optionIndex|npcPosition|entity|entityTemplateId|firstTargetId|skillId|"
    r"lsvPtrOutput|keyOutput|patrolIdOutput|inFight"
    r")$"
)

LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID = (
    "gameassembly-2026-07-17-memorypack-native-event-fields"
)
LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID = (
    "gameassembly-2026-07-11-memorypack-play-fmv-action-fields"
)
NOISY_PROPERTY_PREFIXES = (
    "$",
    "#",
    "dlg_",
    "sns_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "radio_",
    "misc_dlg_",
    "levelseq_",
    "guide_",
    "au_",
    "chr_",
    "skill_",
    "LD/",
)
NOISY_PROPERTY_TEXT = {
    "event_args",
    "blackboard",
    "PLAY_SEQ",
}
TRIGGER_VOLUME_RECORD_KEYS = {
    key
    for key, hint in LEVELSCRIPT_RECORD_HINTS.items()
    if str(hint.get("label") or "").startswith("trigger-volume")
    or str(hint.get("triggerRole") or "").startswith("trigger-volume")
}
TRIGGER_VOLUME_RECORD_KEYS.update({(0x12BE, 0x00), (0x12C0, 0x00)})

COMPACT_NULL_SENTINEL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"

LEVELSCRIPT_SHAPE_TYPE_NAMES = {
    0: "None",
    1: "BOX",
    2: "SPHERE",
}

LEVELSCRIPT_TRIGGER_VOLUME_SHAPE_TYPE_NAMES = {
    0: "None",
    1: "Box",
    2: "Sphere",
    3: "PolyLine",
    4: "Infinite",
}

ACTION_SERIALIZED_MAP_LIST_ORDER = ("actionList", "getterList", "headerList")
ACTION_SERIALIZED_MAP_ORDER_EVIDENCE = (
    "GameAssembly ActionSerializedMapForMemoryPack.Deserialize dispatches "
    "set___actionList__, set___getterList__, then set___headerList__; the "
    "setter bodies write ActionSerializedMap fields at +0x18, +0x20, and "
    "+0x10, and MetadataRegistration resolves those fields as "
    "List<ActionBase>, List<PureGetter>, and List<ActionHeader>. The "
    "physical second/third UID-list blocks match getter/header content "
    "signatures; two-block maps can omit an empty getterList and go straight "
    "to a header-shaped final block, leaving ScriptEventHeader-band rows in "
    "headerList instead of getterList."
)


def _u32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, offset)[0]


def _f32(data: bytes, offset: int) -> float | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack_from("<f", data, offset)[0]


def _u64_offsets(data: bytes, value: int) -> list[int]:
    needle = struct.pack("<Q", value)
    offsets: list[int] = []
    start = 0
    while True:
        offset = data.find(needle, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets


def _is_plausible_levelscript_id(value: int) -> bool:
    return 1_000_000 <= value <= 999_999_999_999


def _list_status(raw_count: int | None) -> tuple[str, int | None]:
    if raw_count is None:
        return "missing", None
    if raw_count == 0xFFFFFFFF:
        return "null", None
    if raw_count <= 64:
        return "present", raw_count
    return "unknown", raw_count


def _drop_empty(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def _offset_hex(offset: int | None) -> str:
    return f"0x{offset:x}" if isinstance(offset, int) and offset >= 0 else ""


def _round_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


def decode_levelscript_action_map_header(data: bytes) -> dict[str, Any]:
    """Decode the stable header of the top-level LevelScriptData actionMap.

    The first serialized member after the LevelScriptData member count is the
    actionMap. For the exported blobs seen so far, non-empty action maps start
    with `02 03 <u32 count>` followed immediately by that many `actionList`
    records. The remaining `ActionSerializedMap` list boundaries need the UID
    record index, so they are decoded by `decode_levelscript_action_map_lists`.
    """
    if not data:
        return {}
    out: dict[str, Any] = {
        "offset": "0x1",
        "serializedMemberCount": data[0],
    }
    if len(data) >= 7 and data[1] == 0x02 and data[2] == 0x03:
        count = _u32(data, 3)
        out.update({
            "status": "present",
            "recordCount": count,
            "recordStartOffset": 7,
            "recordStartOffsetHex": "0x7",
            "headerHex": data[:7].hex(" "),
        })
        return _drop_empty(out)
    if len(data) >= 3 and data[1] == 0xFF:
        out.update({
            "status": "absent-marker",
            "marker": f"0xff 0x{data[2]:02x}",
            "headerHex": data[:3].hex(" "),
        })
        return _drop_empty(out)
    out.update({
        "status": "unknown",
        "headerHex": data[: min(len(data), 8)].hex(" "),
    })
    return _drop_empty(out)


def _record_start(record: dict[str, Any]) -> int:
    try:
        return int(record.get("start") or 0)
    except (TypeError, ValueError):
        return 0


def _record_local_id(record: dict[str, Any]) -> int | None:
    value = record.get("localId")
    return value if isinstance(value, int) else None


def _small_uid_list_count(value: int | None, remaining_records: int) -> bool:
    return (
        isinstance(value, int)
        and value != 0xFFFFFFFF
        and 0 <= value <= 10_000
        and (remaining_records <= 0 or value <= remaining_records)
    )


def _levelscript_header_list_like_record(record: dict[str, Any]) -> bool:
    code = record.get("code")
    kind = record.get("kind")
    return (
        isinstance(code, int)
        and isinstance(kind, int)
        and kind == 0x00
        and 0x0E00 <= code <= 0x18FF
    )


def _levelscript_getter_list_like_record(record: dict[str, Any]) -> bool:
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return False
    if (code, kind) == (0x0A03, 0x00):
        return True
    return kind in {0x07, 0x08, 0x09, 0x0A} and code <= 0x0446


def _block_looks_like_header_list(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    getter_like = sum(1 for record in records if _levelscript_getter_list_like_record(record))
    if getter_like:
        return False
    header_like = sum(1 for record in records if _levelscript_header_list_like_record(record))
    return header_like / len(records) >= 0.75


def _block_looks_like_levelscript_tail(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    outside_like = 0
    for record in records:
        code = record.get("code")
        kind = record.get("kind")
        if isinstance(code, int) and isinstance(kind, int) and (
            (code, kind) == (0x0000, 0x00) or code < 0x0100
        ):
            outside_like += 1
    return outside_like / len(records) >= 0.5


def _next_uid_block_relation(
    data: bytes,
    records: list[dict[str, Any]],
    index: int,
) -> str:
    record_count = len(records)
    if index >= record_count:
        return "none"
    marker_offset = _record_start(records[index]) - 4
    marker_value = _u32(data, marker_offset)
    remaining = record_count - index
    if not _small_uid_list_count(marker_value, remaining):
        return "invalid-marker"
    block = records[index : index + int(marker_value)]
    if _block_looks_like_header_list(block) or any(
        _levelscript_getter_list_like_record(record) for record in block
    ):
        return "action-map-like"
    if _block_looks_like_levelscript_tail(block):
        return "levelscript-tail-like"
    return "unknown-block"


def decode_levelscript_action_map_lists(
    data: bytes,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Decode the three `ActionSerializedMap` list boundaries.

    IL2CPP metadata names the runtime fields as `headerList`, `actionList`,
    and `getterList`. GameAssembly body recovery dispatches the generated
    wrapper setters as `actionList`, `getterList`, then `headerList`, and
    MetadataRegistration resolves those fields to `List<ActionBase>`,
    `List<PureGetter>`, and `List<ActionHeader>`. The compact LevelScript
    blobs follow the same physical order: the first count is in the actionMap
    header, and later counts sit immediately before the next UID record. Some
    two-block blobs omit an empty getter block and put a final header-shaped
    block after actionList; those are labeled as `headerList` by a conservative
    content check.
    """
    header = decode_levelscript_action_map_header(data)
    if not header:
        return {}
    out = dict(header)
    out["serializedListOrder"] = list(ACTION_SERIALIZED_MAP_LIST_ORDER)
    out["serializedListOrderEvidence"] = ACTION_SERIALIZED_MAP_ORDER_EVIDENCE
    if header.get("status") != "present":
        return _drop_empty(out)

    first_count = header.get("recordCount")
    if not isinstance(first_count, int) or first_count < 0:
        return _drop_empty(out)

    sorted_records = sorted(records or [], key=_record_start)
    record_count = len(sorted_records)
    lists: list[dict[str, Any]] = []

    def append_list(
        name: str,
        *,
        count: int | None,
        marker_offset: int | None,
        marker_value: int | None,
        start_index: int,
        source: str,
        status: str = "present",
    ) -> int:
        end_index = start_index
        if isinstance(count, int) and count >= 0:
            end_index = min(record_count, start_index + count)
        row: dict[str, Any] = {
            "name": name,
            "status": status,
            "count": count,
            "countOffset": _offset_hex(marker_offset),
            "countMarker": marker_value,
            "recordIndexStart": start_index,
            "recordIndexEnd": end_index,
            "decodedRecordCount": max(0, end_index - start_index),
            "source": source,
        }
        if isinstance(count, int) and record_count and start_index + count > record_count:
            row["status"] = "count-exceeds-decoded-records"
        lists.append(_drop_empty(row))
        return end_index

    index = append_list(
        "actionList",
        count=first_count,
        marker_offset=3,
        marker_value=first_count,
        start_index=0,
        source="actionMapHeader",
    )

    # An empty ActionSerializedMap is encoded as three consecutive zero list
    # counts immediately after the top-level ``02 03`` object marker.  This is
    # an exact corpus-wide shape in the current original export: every blob
    # whose actionList count is zero has zero getterList/headerList words at
    # offsets 7 and 11 as well.  Decode those words directly.  Looking for the
    # next UID boundary in this case can cross the action-map boundary and
    # misclassify unrelated LevelScript tail objects as executable records.
    if (
        first_count == 0
        and len(data) >= 15
        and _u32(data, 7) == 0
        and _u32(data, 11) == 0
    ):
        index = append_list(
            "getterList",
            count=0,
            marker_offset=7,
            marker_value=0,
            start_index=index,
            source="consecutiveEmptyListCount",
        )
        index = append_list(
            "headerList",
            count=0,
            marker_offset=11,
            marker_value=0,
            start_index=index,
            source="consecutiveEmptyListCount",
        )
        out["exactEmptyActionMap"] = True
        out["emptyMapBoundaryEndOffset"] = _offset_hex(15)
        if record_count:
            lists.append({
                "name": "outsideSerializedActionMap",
                "status": "residual-uid-records-after-exact-empty-map",
                "count": record_count,
                "recordIndexStart": 0,
                "recordIndexEnd": record_count,
            })
        out["serializedLists"] = lists
        out["listCounts"] = {
            str(row.get("name")): row.get("count")
            for row in lists
            if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
        }
        return _drop_empty(out)

    for name in ACTION_SERIALIZED_MAP_LIST_ORDER[1:]:
        if not sorted_records:
            lists.append({
                "name": name,
                "status": "records-not-provided",
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            continue
        if index >= record_count:
            lists.append({
                "name": name,
                "status": "no-decoded-records-after-previous-list",
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            continue
        marker_offset = _record_start(sorted_records[index]) - 4
        marker_value = _u32(data, marker_offset)
        remaining = record_count - index
        if marker_value == 0xFFFFFFFF:
            lists.append({
                "name": name,
                "status": "null-marker-or-unanchored",
                "countOffset": _offset_hex(marker_offset),
                "countMarker": marker_value,
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            break
        if not _small_uid_list_count(marker_value, remaining):
            lists.append({
                "name": name,
                "status": "unknown-marker",
                "countOffset": _offset_hex(marker_offset),
                "countMarker": marker_value,
                "recordIndexStart": index,
                "recordIndexEnd": index,
            })
            break
        if (
            name == "getterList"
            and _block_looks_like_header_list(sorted_records[index : index + int(marker_value)])
            and _next_uid_block_relation(
                data,
                sorted_records,
                index + int(marker_value),
            )
            in {"none", "invalid-marker", "levelscript-tail-like"}
        ):
            lists.append({
                "name": "getterList",
                "status": "omitted-or-empty-before-headerList",
                "count": 0,
                "recordIndexStart": index,
                "recordIndexEnd": index,
                "decodedRecordCount": 0,
                "source": "inferredEmptyFromFinalHeaderLikeBlock",
            })
            index = append_list(
                "headerList",
                count=int(marker_value),
                marker_offset=marker_offset,
                marker_value=marker_value,
                start_index=index,
                source="uidBoundaryMarkerInferredHeaderList",
            )
            break
        index = append_list(
            name,
            count=int(marker_value),
            marker_offset=marker_offset,
            marker_value=marker_value,
            start_index=index,
            source="uidBoundaryMarker",
        )

    if record_count and index < record_count:
        lists.append({
            "name": "outsideSerializedActionMap",
            "status": "residual-uid-records",
            "count": record_count - index,
            "recordIndexStart": index,
            "recordIndexEnd": record_count,
        })

    out["serializedLists"] = lists
    out["listCounts"] = {
        str(row.get("name")): row.get("count")
        for row in lists
        if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
    }
    return _drop_empty(out)


def levelscript_action_map_membership(
    data: bytes,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[int, str]]:
    """Return serialized action-map membership labels keyed by record start."""
    action_map = decode_levelscript_action_map_lists(data, records)
    sorted_records = sorted(records or [], key=_record_start)
    memberships: dict[int, str] = {}
    for list_info in action_map.get("serializedLists") or []:
        name = str(list_info.get("name") or "")
        if name not in ACTION_SERIALIZED_MAP_LIST_ORDER:
            continue
        start_index = int(list_info.get("recordIndexStart") or 0)
        end_index = int(list_info.get("recordIndexEnd") or start_index)
        list_records = sorted_records[start_index:end_index]
        linked_starts: set[int] = set()
        if name == "actionList":
            by_local_id: dict[int, list[dict[str, Any]]] = {}
            for record in list_records:
                local_id = _record_local_id(record)
                if local_id is not None:
                    by_local_id.setdefault(local_id, []).append(record)
            unique_targets = {
                local_id: bucket[0]
                for local_id, bucket in by_local_id.items()
                if len(bucket) == 1
            }
            linked_starts = {
                _record_start(target)
                for record in list_records
                if (target := unique_targets.get(record.get("nextId"))) is not None
            }
        for rel_index, record in enumerate(list_records, start=1):
            start = _record_start(record)
            label = f"{name}#{rel_index}"
            if name == "actionList":
                role = "linked" if start in linked_starts else "root"
                label = f"{label} {role}"
            memberships[start] = label
    return action_map, memberships


def _read_vector2(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 8 > len(data):
        return None, None
    return (
        {
            "x": _round_float(_f32(data, offset)),
            "y": _round_float(_f32(data, offset + 4)),
        },
        offset + 8,
    )


def _read_vector3(data: bytes, offset: int) -> tuple[dict[str, float] | None, int | None]:
    if offset < 0 or offset + 12 > len(data):
        return None, None
    return (
        {
            "x": _round_float(_f32(data, offset)),
            "y": _round_float(_f32(data, offset + 4)),
            "z": _round_float(_f32(data, offset + 8)),
        },
        offset + 12,
    )


def _decode_levelscript_shape(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode `Beyond.Gameplay.Core.LevelScriptShape`.

    The field order is verified from the MemoryPack setter order:
    eulerAngles, offset, radius, size, type. The object starts with a compact
    one-byte member count in these exported blobs.
    """
    if offset < 0 or offset + 45 > len(data):
        return None, None
    member_count = data[offset]
    cursor = offset + 1
    euler_angles, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    shape_offset, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    radius = _f32(data, cursor)
    cursor += 4
    size, cursor = _read_vector3(data, cursor)
    if cursor is None:
        return None, None
    shape_type_raw = _u32(data, cursor)
    cursor += 4
    return (
        _drop_empty(
            {
                "offset": _offset_hex(offset),
                "memberCount": member_count,
                "typeRaw": shape_type_raw,
                "type": LEVELSCRIPT_SHAPE_TYPE_NAMES.get(
                    shape_type_raw if shape_type_raw is not None else -1,
                    "",
                ),
                "position": shape_offset,
                "eulerAngles": euler_angles,
                "size": size,
                "radius": _round_float(radius),
            }
        ),
        cursor,
    )


def _decode_levelscript_shape_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 64,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    shapes: list[dict[str, Any]] = []
    for _ in range(count):
        shape, cursor = _decode_levelscript_shape(data, cursor)
        if shape is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["shapes"] = shapes
            return _drop_empty(out), None
        shapes.append(shape)
    out["parseStatus"] = "decoded"
    out["shapes"] = shapes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _valid_levelscript_active_shape(shape: dict[str, Any]) -> bool:
    """Validate one current MemoryPack ``LevelScriptShape`` structurally."""
    if (
        shape.get("memberCount") != 5
        or shape.get("typeRaw") not in LEVELSCRIPT_SHAPE_TYPE_NAMES
        or shape.get("typeRaw") == 0
    ):
        return False
    values: list[Any] = [shape.get("radius")]
    for field_name in ("position", "eulerAngles", "size"):
        field = shape.get(field_name)
        if not isinstance(field, dict) or set(field) != {"x", "y", "z"}:
            return False
        values.extend(field.values())
    return all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and abs(value) < 10_000_000
        for value in values
    )


def find_levelscript_active_shape_candidates(
    data: bytes,
    search_start: int,
    search_end: int,
) -> list[dict[str, Any]]:
    """Find exact active-shape members by their generated neighbor fields.

    Current metadata fixes the top-level MemoryPack order as ``actionMap``,
    ``activeShapeList``, three booleans, then ``endType``.  The scan remains
    fail-closed: a candidate must decode every shape with the exact five-member
    schema and must be followed by all four typed scalar neighbors.
    """
    lower = max(0, int(search_start))
    upper = min(len(data), max(lower, int(search_end)))
    candidates: list[dict[str, Any]] = []
    for offset in range(lower, upper):
        shape_list, cursor = _decode_levelscript_shape_list(data, offset)
        if (
            cursor is None
            or shape_list.get("status") != "present"
            or not isinstance(shape_list.get("count"), int)
            or int(shape_list["count"]) <= 0
            or shape_list.get("parseStatus") != "decoded"
            or not all(
                isinstance(shape, dict) and _valid_levelscript_active_shape(shape)
                for shape in shape_list.get("shapes") or []
            )
            or len(shape_list.get("shapes") or []) != int(shape_list["count"])
            or cursor + 7 > upper
        ):
            continue
        scalar_flags = list(data[cursor : cursor + 3])
        end_type_raw = _u32(data, cursor + 3)
        if (
            any(value not in (0, 1) for value in scalar_flags)
            or end_type_raw not in LEVELSCRIPT_END_TYPE_NAMES
        ):
            continue
        candidates.append({
            "offset": offset,
            "offsetHex": _offset_hex(offset),
            "endOffset": cursor,
            "endOffsetHex": _offset_hex(cursor),
            "shapeList": shape_list,
            "followingFields": {
                "allowStartOnTravelPole": bool(scalar_flags[0]),
                "allowTick": bool(scalar_flags[1]),
                "enablePreload": bool(scalar_flags[2]),
                "endTypeRaw": end_type_raw,
                "endTypeName": LEVELSCRIPT_END_TYPE_NAMES[end_type_raw],
            },
        })
    return candidates


def decode_levelscript_active_shape_list(
    data: bytes,
    script_id: int,
) -> dict[str, Any]:
    """Recover the authored active volume without an object-specific offset."""
    out: dict[str, Any] = {
        "schema": "levelScriptActiveShapeList.v1",
        "status": "unresolved",
        "candidateCount": 0,
    }
    if not data or data[0] != 27 or script_id <= 0:
        out["diagnostic"] = "topLevelMemberCountOrScriptId"
        return out

    records = extract_levelscript_uid_records(data)
    action_map = decode_levelscript_action_map_lists(data, records)
    sorted_records = sorted(records, key=_record_start)
    serialized_lists = [
        row
        for row in action_map.get("serializedLists") or []
        if row.get("name") in ACTION_SERIALIZED_MAP_LIST_ORDER
        and row.get("status") == "present"
        and isinstance(row.get("recordIndexEnd"), int)
    ]
    final_record_index = max(
        (int(row["recordIndexEnd"]) for row in serialized_lists),
        default=0,
    )
    if final_record_index <= 0 or final_record_index > len(sorted_records):
        out["diagnostic"] = "completeActionMapBoundaryMissing"
        return out

    tail_rows = [_tail_candidate(data, offset) for offset in _u64_offsets(data, script_id)]
    if not tail_rows:
        out["diagnostic"] = "verifiedTopLevelScriptIdMissing"
        return out
    best_score = max(int(row.get("score") or 0) for row in tail_rows)
    best_tails = [row for row in tail_rows if int(row.get("score") or 0) == best_score]
    if len(best_tails) != 1:
        out.update({
            "diagnostic": "topLevelScriptIdBoundaryAmbiguous",
            "tailCandidateCount": len(best_tails),
        })
        return out

    final_record = sorted_records[final_record_index - 1]
    search_start = int(final_record.get("payloadStart") or final_record.get("start") or 0)
    search_end = int(best_tails[0].get("scriptIdOffset") or 0)
    candidates = find_levelscript_active_shape_candidates(
        data,
        search_start,
        search_end,
    )
    out.update({
        "candidateCount": len(candidates),
        "candidateOffsets": [row["offsetHex"] for row in candidates[:8]],
        "searchStartOffsetHex": _offset_hex(search_start),
        "searchEndOffsetHex": _offset_hex(search_end),
        "actionMapFinalList": str(serialized_lists[-1].get("name") or ""),
        "serializedMemberOrder": [
            "actionMap",
            "activeShapeList",
            "allowStartOnTravelPole",
            "allowTick",
            "enablePreload",
            "endType",
        ],
    })
    if len(candidates) != 1:
        out["diagnostic"] = (
            "activeShapeCandidateMissing"
            if not candidates
            else "activeShapeCandidateAmbiguous"
        )
        return out

    candidate = candidates[0]
    shape_list = candidate["shapeList"]
    out.update({
        "status": "decoded_unique",
        "offsetHex": candidate["offsetHex"],
        "endOffsetHex": candidate["endOffsetHex"],
        "count": shape_list.get("count"),
        "shapes": shape_list.get("shapes") or [],
        "followingFields": candidate["followingFields"],
        "evidenceBoundary": (
            "This recovers the authored activation geometry and exact adjacent "
            "MemoryPack fields. It does not prove the player position, runtime "
            "inside/outside classification, activation outcome, mission owner, "
            "event firing, or Story order."
        ),
    })
    return out


def _decode_vector2_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    points: list[dict[str, float]] = []
    for _ in range(count):
        point, cursor = _read_vector2(data, cursor)
        if point is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["points"] = points
            return _drop_empty(out), None
        points.append(point)
    out["parseStatus"] = "decoded"
    out["points"] = points
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_vector3_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    points: list[dict[str, float]] = []
    for _ in range(count):
        point, cursor = _read_vector3(data, cursor)
        if point is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["points"] = points
            return _drop_empty(out), None
        points.append(point)
    out["parseStatus"] = "decoded"
    out["points"] = points
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_trigger_volume_shape(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode `Beyond.Gameplay.LevelScriptTriggerVolumeShapeData`."""
    if offset < 0 or offset + 1 > len(data):
        return None, None
    member_count = data[offset]
    cursor = offset + 1
    poly_line_points, cursor = _decode_vector2_list(data, cursor)
    if cursor is None:
        return None, None
    position, cursor = _read_vector3(data, cursor)
    if position is None or cursor is None:
        return None, None
    radius = _f32(data, cursor)
    cursor += 4
    rotation, cursor = _read_vector3(data, cursor)
    if rotation is None or cursor is None:
        return None, None
    shape_type_raw = _u32(data, cursor)
    cursor += 4
    size, cursor = _read_vector3(data, cursor)
    if size is None or cursor is None:
        return None, None
    return (
        _drop_empty(
            {
                "offset": _offset_hex(offset),
                "memberCount": member_count,
                "shapeTypeRaw": shape_type_raw,
                "shapeType": LEVELSCRIPT_TRIGGER_VOLUME_SHAPE_TYPE_NAMES.get(
                    shape_type_raw if shape_type_raw is not None else -1,
                    "",
                ),
                "position": position,
                "radius": _round_float(radius),
                "rotation": rotation,
                "size": size,
                "polyLinePoints": poly_line_points,
            }
        ),
        cursor,
    )


def _decode_trigger_volume_shape_list(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None

    shapes: list[dict[str, Any]] = []
    for _ in range(count):
        shape, cursor = _decode_trigger_volume_shape(data, cursor)
        if shape is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["shapes"] = shapes
            return _drop_empty(out), None
        shapes.append(shape)
    out["parseStatus"] = "decoded"
    out["shapes"] = shapes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _decode_trigger_volume_entry(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int | None]:
    """Decode one keyed `LevelScriptTriggerVolumeData` map entry."""
    if offset < 0 or offset + 6 > len(data):
        return None, None
    key_slot_id = _u32(data, offset)
    union_tag = data[offset + 4]
    member_count = data[offset + 5]
    if (
        union_tag not in LEVELSCRIPT_TRIGGER_VOLUME_UNION_TAG_NAMES
        or member_count != 8
    ):
        return None, None
    cursor = offset + 6
    if cursor + 6 > len(data):
        return None, None
    enter_check_on_ground = bool(data[cursor])
    cursor += 1
    exit_shape_start_index = _i32(data, cursor)
    cursor += 4
    is_important = bool(data[cursor])
    cursor += 1
    shape_list, cursor = _decode_trigger_volume_shape_list(data, cursor)
    if cursor is None or cursor + 10 > len(data):
        return None, None
    slot_id = _u32(data, cursor)
    cursor += 4
    trigger_count_limit = _i32(data, cursor)
    cursor += 4
    trigger_on_pole = bool(data[cursor])
    cursor += 1
    wait_srv_res = bool(data[cursor])
    cursor += 1
    if (
        key_slot_id != slot_id
        or key_slot_id is None
        or not 80_000 <= key_slot_id <= 89_999
        or trigger_count_limit is None
        or trigger_count_limit < -1
    ):
        return None, None
    return (
        _drop_empty(
            {
                "offset": _offset_hex(offset),
                "keySlotId": key_slot_id,
                "unionTag": union_tag,
                "triggerVolumeType": LEVELSCRIPT_TRIGGER_VOLUME_UNION_TAG_NAMES.get(
                    union_tag,
                    "",
                ),
                "memberCount": member_count,
                "enterCheckOnGround": enter_check_on_ground,
                "exitShapeStartIndex": exit_shape_start_index,
                "isImportant": is_important,
                "shapeList": shape_list,
                "slotId": slot_id,
                "triggerCountLimit": trigger_count_limit,
                "triggerOnPole": trigger_on_pole,
                "waitSrvRes": wait_srv_res,
            }
        ),
        cursor,
    )



TRIGGER_VOLUME_WRAPPER_PROLOGUE = bytes.fromhex(
    "00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "ff ff ff ff ea 03 00 00 ff ff ff ff "
    "01 00 00 00 00 00 00 00 00 00"
)


def _decode_trigger_volume_map(
    data: bytes,
    offset: int,
    *,
    max_count: int = 128,
) -> tuple[dict[str, Any], int | None]:
    raw_count = _u32(data, offset)
    status, count = _list_status(raw_count)
    cursor = offset + 4
    out: dict[str, Any] = {
        "offset": _offset_hex(offset),
        "status": status,
        "count": count,
    }
    wrapper_end = offset + 4 + len(TRIGGER_VOLUME_WRAPPER_PROLOGUE)
    if (
        raw_count == 4
        and wrapper_end + 4 <= len(data)
        and data[offset + 4:wrapper_end] == TRIGGER_VOLUME_WRAPPER_PROLOGUE
    ):
        inner, inner_cursor = _decode_trigger_volume_map(data, wrapper_end, max_count=max_count)
        if inner_cursor == len(data) and inner.get("status") == "present":
            wrapped = dict(inner)
            wrapped.update({
                "offset": _offset_hex(offset),
                "encoding": "wrapped-trigger-volume-map",
                "wrapperOffset": _offset_hex(offset),
                "wrapperBytes": 4 + len(TRIGGER_VOLUME_WRAPPER_PROLOGUE),
                "wrapperOuterCount": raw_count,
                "wrapperPrologueBytes": len(TRIGGER_VOLUME_WRAPPER_PROLOGUE),
                "innerMapOffset": _offset_hex(wrapper_end),
                "endOffset": _offset_hex(inner_cursor),
            })
            wrapped.setdefault("parseStatus", "decoded")
            return _drop_empty(wrapped), inner_cursor

    if status != "present" or count is None or count == 0:
        out["endOffset"] = _offset_hex(cursor)
        return _drop_empty(out), cursor
    if count > max_count:
        out["parseStatus"] = "count-too-large"
        return _drop_empty(out), None
    min_entry_bytes = 25
    minimum_bytes_required = count * min_entry_bytes
    remaining_bytes = max(0, len(data) - cursor)
    if minimum_bytes_required > remaining_bytes:
        out["parseStatus"] = "count-exceeds-remaining"
        out["remainingBytes"] = remaining_bytes
        out["minimumBytesRequired"] = minimum_bytes_required
        return _drop_empty(out), None

    volumes: list[dict[str, Any]] = []
    for _ in range(count):
        volume, cursor = _decode_trigger_volume_entry(data, cursor)
        if volume is None or cursor is None:
            out["parseStatus"] = "truncated"
            out["volumes"] = volumes
            return _drop_empty(out), None
        volumes.append(volume)
    out["parseStatus"] = "decoded"
    out["slotIds"] = [row.get("slotId") for row in volumes if row.get("slotId") is not None]
    out["volumes"] = volumes
    out["endOffset"] = _offset_hex(cursor)
    return _drop_empty(out), cursor


def _find_final_trigger_volume_map(
    data: bytes,
    *,
    search_start: int,
    max_scan_bytes: int = 1_048_576,
) -> tuple[int | None, dict[str, Any], int | None]:
    """Find the final exact trigger-volume dictionary after a non-empty task map.

    ``triggerVolumes`` is the final generated MemoryPack member of
    ``LevelScriptData``.  Fully decoding every polymorphic condition nested in
    the preceding ``taskMap`` is unnecessary for locating it: scan the bounded
    file tail and accept either the exact null/empty dictionary at EOF or a
    strict current-build Leader map whose decoded cursor lands exactly at EOF.
    Key/slot equality, subtype tag, member count, shape bodies, and field
    ranges are all validated by the entry decoder.
    """
    if not data:
        return None, {}, None
    lower = max(0, int(search_start), len(data) - max_scan_bytes)
    for offset in range(len(data) - 4, lower - 1, -1):
        raw_count = _u32(data, offset)
        if raw_count is None or not 1 <= raw_count <= 128:
            continue
        decoded, cursor = _decode_trigger_volume_map(data, offset)
        if (
            cursor == len(data)
            and decoded.get("status") == "present"
            and decoded.get("parseStatus") == "decoded"
            and len(decoded.get("volumes") or []) == raw_count
        ):
            return offset, decoded, cursor
    empty_offset = len(data) - 4
    if empty_offset >= lower:
        decoded, cursor = _decode_trigger_volume_map(data, empty_offset)
        if (
            cursor == len(data)
            and decoded.get("status") in {"null", "present"}
            and not decoded.get("volumes")
            and decoded.get("count") in {None, 0}
        ):
            decoded["parseStatus"] = "decoded"
            return empty_offset, decoded, cursor
    return None, {}, None


def decode_levelscript_encounter_module_target(
    data: bytes,
    encounter_pointer: int | str,
    expected_script_id: int | str,
) -> dict[str, Any]:
    """Resolve one exact ``LsmPtr`` to a top-level ``EncounterData`` value.

    The current MemoryPack union has no per-value byte length, so an unknown
    module cannot be skipped safely.  This decoder intentionally accepts only
    a one-entry ``modules`` dictionary whose sole union value is EncounterData,
    consumes that value completely, and validates the remaining top-level
    LevelScriptData tail through EOF.  It returns no partial result.
    """
    try:
        pointer = int(encounter_pointer)
        script_id = int(expected_script_id)
    except (TypeError, ValueError):
        return {}
    if not data or data[0] != 0x1B or pointer <= 0 or script_id <= 0:
        return {}

    class Cursor:
        def __init__(self, offset: int):
            self.offset = offset

        def take(self, size: int) -> bytes:
            if size < 0 or self.offset < 0 or self.offset + size > len(data):
                raise ValueError("truncated")
            value = data[self.offset:self.offset + size]
            self.offset += size
            return value

        def u8(self) -> int:
            return self.take(1)[0]

        def boolean(self) -> bool:
            value = self.u8()
            if value not in (0, 1):
                raise ValueError("invalid bool")
            return bool(value)

        def i32(self) -> int:
            return struct.unpack("<i", self.take(4))[0]

        def u32(self) -> int:
            return struct.unpack("<I", self.take(4))[0]

        def u64(self) -> int:
            return struct.unpack("<Q", self.take(8))[0]

        def f32(self) -> float:
            value = struct.unpack("<f", self.take(4))[0]
            if not math.isfinite(value):
                raise ValueError("non-finite float")
            return value

        def string(self) -> str | None:
            size = self.i32()
            if size == -1:
                return None
            if size < 0 or size > 1_048_576:
                raise ValueError("invalid string size")
            return self.take(size).decode("utf-8", errors="strict")

        def count(self, *, maximum: int = 1024) -> int | None:
            value = self.i32()
            if value == -1:
                return None
            if value < 0 or value > maximum:
                raise ValueError("invalid collection count")
            return value

    def pos_rot(cursor: Cursor) -> None:
        for _ in range(6):
            cursor.f32()

    def slot_ptr(cursor: Cursor) -> dict[str, Any]:
        if cursor.u8() != 3:
            raise ValueError("invalid slot pointer member count")
        return {
            "logicId": str(cursor.u64()),
            "slotId": cursor.u32(),
            "useSlotId": cursor.boolean(),
        }

    def intro_part(cursor: Cursor) -> None:
        if cursor.u8() != 13:
            raise ValueError("invalid intro-part member count")
        cursor.i32()  # airWallShowTiming
        cursor.i32()  # enemySpawnTiming
        cursor.f32()
        cursor.f32()
        cursor.boolean()
        cursor.boolean()
        if cursor.count() is not None:
            # OperaSegment is deliberately unsupported until a current blob
            # requires it; without a byte length it cannot be skipped.
            raise ValueError("unsupported intro opera segments")
        cursor.i32()  # teleportMode
        for _ in range(4):
            pos_rot(cursor)
        cursor.i32()  # teleportTiming

    needle = struct.pack("<Q", pointer)
    candidates: list[dict[str, Any]] = []
    start = 0
    while True:
        key_offset = data.find(needle, start)
        if key_offset < 0:
            break
        start = key_offset + 1
        if key_offset < 4 or _i32(data, key_offset - 4) != 1:
            continue
        try:
            cursor = Cursor(key_offset)
            if cursor.u64() != pointer or cursor.u8() != 2 or cursor.u8() != 16:
                continue
            disabled_when_completed = cursor.boolean()
            if cursor.u64() != pointer:
                continue
            activate_mode = cursor.i32()
            activate_mode_alter = cursor.i32()
            activate_trigger_slot_id = cursor.u32()
            activate_trigger_slot_id_alter = cursor.u32()
            if cursor.count() is not None:
                raise ValueError("unsupported direct air-wall list")
            air_wall_count = cursor.count(maximum=64)
            air_wall_ptrs = [slot_ptr(cursor) for _ in range(air_wall_count or 0)]
            if cursor.u8() != 8:
                raise ValueError("invalid battle-part member count")
            complete_delay = cursor.f32()
            complete_delay_mode = cursor.i32()
            complete_delay_str_param = cursor.string()
            complete_mode = cursor.i32()
            dont_hide_dead_enemy = cursor.boolean()
            exit_trigger_slot_id = cursor.u32()
            keep_hatred = cursor.boolean()
            protect_enemy = cursor.boolean()
            enemy_count = cursor.count(maximum=256)
            enemies = [slot_ptr(cursor) for _ in range(enemy_count or 0)]
            intro_part(cursor)
            if cursor.u8() != 0xFF:
                raise ValueError("unsupported intro-part alter")
            intro_part_mode = cursor.i32()
            spawner_id = cursor.u64()
            if cursor.u8() != 0xFF:
                raise ValueError("unsupported tail part")
            tail_part_mode = cursor.i32()
            encounter_end = cursor.offset

            # Exact current top-level tail after modules.  Non-null NPC or
            # property collections fail closed rather than being scanned.
            npc_count = cursor.count()
            if npc_count not in (None, 0) or cursor.u64() != 0:
                raise ValueError("unsupported npcs or parent script")
            if any(cursor.count() is not None for _ in range(3)):
                raise ValueError("unsupported property/reference collection")
            reset_mode_when_active = cursor.i32()
            reset_mode_when_end = cursor.i32()
            if cursor.u64() != script_id:
                raise ValueError("script id mismatch")
            if cursor.count() is not None:
                raise ValueError("unsupported start shape list")
            start_type = cursor.i32()
            if start_type not in LEVELSCRIPT_START_TYPE_NAMES:
                raise ValueError("invalid start type")
            if cursor.count() is not None:
                raise ValueError("unsupported task map")
            trigger_offset = cursor.offset
            trigger_map, trigger_end = _decode_trigger_volume_map(data, trigger_offset)
            if trigger_end != len(data):
                raise ValueError("top-level tail does not end at EOF")

            candidates.append(_drop_empty({
                "status": "exact_top_level_encounter_module_target",
                "moduleType": "EncounterData",
                "moduleUnionTag": "0x02",
                "serializedMemberCount": 16,
                "levelScriptVariablePtr": str(pointer),
                "levelNum": pointer // 100_000_000,
                "moduleLocalId": pointer % 100_000_000,
                "listenerScriptId": str(script_id),
                "dictionaryCount": 1,
                "dictionaryOffset": key_offset - 4,
                "dictionaryOffsetHex": _offset_hex(key_offset - 4),
                "dictionaryKeyOffset": key_offset,
                "dictionaryKeyOffsetHex": _offset_hex(key_offset),
                "encounterEndOffset": encounter_end,
                "encounterEndOffsetHex": _offset_hex(encounter_end),
                "disableWhenCompleted": disabled_when_completed,
                "activateMode": activate_mode,
                "activateModeAlter": activate_mode_alter,
                "activateTriggerSlotId": activate_trigger_slot_id,
                "activateTriggerSlotIdAlter": activate_trigger_slot_id_alter,
                "airWallPointers": air_wall_ptrs,
                "battlePart": {
                    "completeDelay": _round_float(complete_delay),
                    "completeDelayMode": complete_delay_mode,
                    "completeDelayStrParam": complete_delay_str_param,
                    "completeMode": complete_mode,
                    "dontHideDeadEnemyWhenComplete": dont_hide_dead_enemy,
                    "exitTriggerSlotId": exit_trigger_slot_id,
                    "keepHatred": keep_hatred,
                    "protectEnemyBeforeBattlePart": protect_enemy,
                },
                "enemyPointers": enemies,
                "introPartMode": intro_part_mode,
                "spawnerId": str(spawner_id),
                "tailPartMode": tail_part_mode,
                "resetModeWhenActive": reset_mode_when_active,
                "resetModeWhenEnd": reset_mode_when_end,
                "startType": LEVELSCRIPT_START_TYPE_NAMES[start_type],
                "triggerVolumeCount": trigger_map.get("count"),
                "serializedMissionOrQuestId": False,
                "clientRequest": False,
                "expectedServerReturn": False,
                "ownershipBoundary": (
                    "The exact runtime target is a level-script EncounterData module. "
                    "Its current-build serializer, BattlePart, and event payload contain "
                    "no missionId, questId, or MissionArea foreign key."
                ),
            }))
        except (UnicodeDecodeError, ValueError, struct.error):
            continue
    return candidates[0] if len(candidates) == 1 else {}


def decode_script_pointer_payload(
    data: bytes,
    record: dict[str, Any] | None,
    *,
    target_offset: int | None = None,
) -> dict[str, Any]:
    """Decode the compact script-pointer payload found in LevelScript records.

    This decodes bytes only. The flag byte is not yet mapped to start/end
    semantics, so callers must keep it diagnostic.
    """
    if not data or not record:
        return {}
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return {}
    if (code, kind) not in SCRIPT_POINTER_REF_RECORDS:
        return {}
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start + 9 > len(data):
        return {}
    if data[payload_start] != 0x04:
        return {}

    pointer_script = struct.unpack_from("<Q", data, payload_start + 1)[0]
    if not _is_plausible_levelscript_id(pointer_script):
        return {}
    pointer_offset = payload_start + 1
    flag_offset: int | None = None
    pointer_flag: int | None = None
    if payload_start + 23 <= len(data) and data[payload_start + 21] == 0x04:
        raw_flag = data[payload_start + 22]
        if raw_flag in (0, 1):
            pointer_flag = raw_flag
            flag_offset = payload_start + 22

    sentinel_shape = False
    if payload_start + 35 <= len(data):
        sentinel_shape = (
            data[payload_start + 9 : payload_start + 21]
            == b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
            and data[payload_start + 23 : payload_start + 35]
            == b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        )

    return _drop_empty(
        {
            "pointerScript": str(pointer_script),
            "pointerScriptOffset": pointer_offset,
            "pointerPayloadStart": payload_start,
            "pointerTargetMatches": (
                target_offset is None or int(target_offset) == pointer_offset
            ),
            "pointerFlag": pointer_flag,
            "pointerFlagOffset": flag_offset,
            "pointerPayloadShape": (
                "tagged-u64+tagged-flag+sentinels"
                if sentinel_shape and pointer_flag is not None
                else "tagged-u64"
            ),
        }
    )


def _is_printable_ascii(blob: bytes) -> bool:
    return all(0x20 <= byte <= 0x7E for byte in blob)


LEVELSCRIPT_HEX_UID_RE = re.compile(rb"[0-9a-f]{8}")


def _extract_levelscript_tagged_ascii_strings(
    data: bytes,
    tag: int = 0x04,
    *,
    max_len: int = 120,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    end = len(data) - 5
    i = 0
    while i < end:
        if data[i] != tag:
            i += 1
            continue
        size = struct.unpack_from("<I", data, i + 1)[0]
        if size <= 0 or size > max_len or i + 5 + size > len(data):
            i += 1
            continue
        raw = data[i + 5 : i + 5 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "text": text})
        i += 5 + size
    return hits


def _extract_levelscript_plain_ascii_strings(
    data: bytes,
    *,
    min_len: int = 3,
    max_len: int = 120,
    tagged_offsets: set[int] | None = None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    tagged_offsets = tagged_offsets or set()
    end = len(data) - 4
    i = 0
    while i < end:
        size = struct.unpack_from("<I", data, i)[0]
        if size < min_len or size > max_len or i + 4 + size > len(data):
            i += 1
            continue
        if i > 0 and data[i - 1] == 0x04 and (i - 1) in tagged_offsets:
            i += 4 + size
            continue
        raw = data[i + 4 : i + 4 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "payloadOffset": i + 4, "text": text})
        i += 4 + size
    return hits


def _decode_levelscript_uid_record(data: bytes, uid_off: int, uid: str) -> dict[str, Any] | None:
    if uid_off >= 14:
        start = uid_off - 14
        if start + 32 <= len(data):
            if (
                data[start] == 0xFA
                and data[start + 4] in (0, 1)
                and data[start + 9] == 0
                and _u32(data, start + 10) == 8
            ):
                local_id = _u32(data, start + 5)
                if isinstance(local_id, int) and local_id <= 0x1000:
                    return {
                        "start": start,
                        "layout": "fa",
                        "code": struct.unpack_from("<H", data, start + 1)[0],
                        "kind": data[start + 3],
                        "unionTag": struct.unpack_from("<H", data, start + 1)[0],
                        "serializedMemberCount": data[start + 3],
                        "dontLog": bool(data[start + 4]),
                        "unionTagEncoding": "memorypack-fa-u16",
                        "localId": local_id,
                        "uid": uid,
                        "nextId": _i32(data, start + 28),
                        "payloadStart": start + 32,
                        "strings": [],
                        "plainStrings": [],
                    }

    if uid_off >= 12:
        start = uid_off - 12
        if start + 30 <= len(data):
            code = struct.unpack_from("<H", data, start)[0]
            kind = data[start + 2]
            local_id = _u32(data, start + 3)
            if (
                isinstance(local_id, int)
                and data[start] < 0xFA
                and data[start + 1] <= 0x40
                and kind in (0, 1)
                and local_id <= 0x1000
                and data[start + 7] == 0
                and _u32(data, start + 8) == 8
            ):
                return {
                    "start": start,
                    "layout": "plain",
                    "code": code,
                    "kind": kind,
                    "unionTag": data[start],
                    "serializedMemberCount": data[start + 1],
                    "dontLog": bool(data[start + 2]),
                    "unionTagEncoding": "memorypack-u8",
                    "localId": local_id,
                    "uid": uid,
                    "nextId": _i32(data, start + 26),
                    "payloadStart": start + 30,
                    "strings": [],
                    "plainStrings": [],
                }

    return None


def extract_levelscript_uid_records(
    data: bytes,
    tagged_strings: list[dict[str, Any]] | None = None,
    plain_strings: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_starts: set[int] = set()
    tagged_strings = sorted(tagged_strings or [], key=lambda hit: int(hit.get("offset") or 0))
    plain_strings = sorted(plain_strings or [], key=lambda hit: int(hit.get("offset") or 0))

    for match in LEVELSCRIPT_HEX_UID_RE.finditer(data):
        uid_off = match.start()
        uid = match.group().decode("ascii")
        record = _decode_levelscript_uid_record(data, uid_off, uid)
        if record is None or int(record["start"]) in seen_starts:
            continue
        seen_starts.add(int(record["start"]))
        records.append(record)

    records.sort(key=_record_start)
    if not records:
        return records

    tagged_index = 0
    plain_index = 0
    for index, record in enumerate(records):
        next_start = _record_start(records[index + 1]) if index + 1 < len(records) else len(data)
        payload_start = int(record.get("payloadStart") or 0)
        while tagged_index < len(tagged_strings) and int(tagged_strings[tagged_index].get("offset") or 0) < payload_start:
            tagged_index += 1
        scan_index = tagged_index
        while scan_index < len(tagged_strings) and int(tagged_strings[scan_index].get("offset") or 0) < next_start:
            record["strings"].append(tagged_strings[scan_index])
            scan_index += 1
        while plain_index < len(plain_strings) and int(plain_strings[plain_index].get("offset") or 0) < payload_start:
            plain_index += 1
        scan_index = plain_index
        while scan_index < len(plain_strings) and int(plain_strings[scan_index].get("offset") or 0) < next_start:
            record["plainStrings"].append(plain_strings[scan_index])
            scan_index += 1

    return records


def decode_levelscript_action_map_details(
    data: bytes,
    *,
    sample_record_limit: int = 8,
    max_hint_records: int = 128,
) -> dict[str, Any]:
    tagged_strings = _extract_levelscript_tagged_ascii_strings(data)
    plain_strings = _extract_levelscript_plain_ascii_strings(
        data,
        tagged_offsets={int(hit.get("offset") or 0) for hit in tagged_strings},
    )
    records = extract_levelscript_uid_records(data, tagged_strings, plain_strings)
    action_map, memberships = levelscript_action_map_membership(data, records)
    list_status_counts: Counter[str] = Counter()
    for row in action_map.get("serializedLists") or []:
        name = str(row.get("name") or "")
        status = str(row.get("status") or "")
        if name or status:
            list_status_counts[f"{name}:{status}"] += 1

    membership_counts: Counter[str] = Counter()
    for label in memberships.values():
        label_text = str(label or "")
        if not label_text:
            continue
        list_name = label_text.split("#", 1)[0]
        if label_text.endswith(" root"):
            membership_counts[f"{list_name}:root"] += 1
        elif label_text.endswith(" linked"):
            membership_counts[f"{list_name}:linked"] += 1
        else:
            membership_counts[list_name] += 1

    record_code_counts: Counter[str] = Counter()
    hint_counts: Counter[str] = Counter()
    sample_rows: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        code = record.get("code")
        kind = record.get("kind")
        if isinstance(code, int) and isinstance(kind, int):
            record_code_counts[f"0x{code:04x}:0x{kind:02x}"] += 1
        next_start = _record_start(records[index + 1]) if index + 1 < len(records) else len(data)
        detail: dict[str, Any] = {}
        if index < max_hint_records:
            detail = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_start,
                action_map_role=memberships.get(_record_start(record)),
            )
            label = (
                detail.get("label")
                or (detail.get("actionHeader") or {}).get("payloadShape")
                or detail.get("payloadShape")
                or ""
            )
            if label:
                hint_counts[str(label)] += 1
        if len(sample_rows) < sample_record_limit:
            sample: dict[str, Any] = {
                "offset": _offset_hex(_record_start(record)),
                "layout": record.get("layout"),
                "role": memberships.get(_record_start(record)) or "",
                "code": f"0x{code:04x}" if isinstance(code, int) else "",
                "kind": f"0x{kind:02x}" if isinstance(kind, int) else "",
                "localId": record.get("localId"),
                "nextId": record.get("nextId"),
                "uid": record.get("uid"),
                "strings": [str(hit.get("text") or "") for hit in (record.get("strings") or [])[:4]],
                "plainStrings": [str(hit.get("text") or "") for hit in (record.get("plainStrings") or [])[:4]],
            }
            label = (
                detail.get("label")
                or (detail.get("actionHeader") or {}).get("payloadShape")
                or detail.get("payloadShape")
                or ""
            )
            if label:
                sample["payloadHint"] = label
            sample_rows.append(_drop_empty(sample))

    return _drop_empty(
        {
            "actionMap": action_map,
            "uidRecordCount": len(records),
            "membershipCount": len(memberships),
            "taggedStringCount": len(tagged_strings),
            "plainStringCount": len(plain_strings),
            "listStatusCounts": dict(list_status_counts.most_common(12)),
            "membershipCounts": dict(membership_counts.most_common(12)),
            "recordCodeCounts": dict(record_code_counts.most_common(24)),
            "recordHintCounts": dict(hint_counts.most_common(24)),
            "recordHintSampledCount": min(len(records), max_hint_records),
            "sampleRecords": sample_rows,
        }
    )


def _payload_sentinel_size(data: bytes, offset: int) -> int:
    if offset + 12 <= len(data) and data[offset : offset + 12] == COMPACT_NULL_SENTINEL:
        return 12
    return 0


def _decode_tagged_payload_fields(payload: bytes, *, max_fields: int = 8) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(payload) and len(fields) < max_fields:
        if payload[cursor] != 0x04:
            cursor += 1
            continue
        if cursor + 5 > len(payload):
            break

        size = struct.unpack_from("<I", payload, cursor + 1)[0]
        if 0 < size <= 120 and cursor + 5 + size <= len(payload):
            raw = payload[cursor + 5 : cursor + 5 + size]
            if _is_printable_ascii(raw):
                text = raw.decode("ascii", errors="replace")
                end = cursor + 5 + size
                fields.append(
                    _drop_empty(
                        {
                            "offset": _offset_hex(cursor),
                            "type": "string",
                            "value": text,
                        }
                    )
                )
                cursor = end + _payload_sentinel_size(payload, end)
                continue

        raw4 = payload[cursor + 1 : cursor + 5]
        scalar_u32 = struct.unpack("<I", raw4)[0]
        scalar_i32 = struct.unpack("<i", raw4)[0]
        scalar_float = struct.unpack("<f", raw4)[0]
        field: dict[str, Any] = {
            "offset": _offset_hex(cursor),
            "type": "scalar",
        }
        if scalar_u32 <= 1_000_000:
            field["u32"] = scalar_u32
        if -1_000_000 <= scalar_i32 <= 1_000_000:
            field["i32"] = scalar_i32
        if -1_000_000.0 <= scalar_float <= 1_000_000.0:
            field["float"] = _round_float(scalar_float)
        if not any(key in field for key in ("u32", "i32", "float")):
            field["rawHex"] = raw4.hex(" ")
        fields.append(_drop_empty(field))
        end = cursor + 5
        cursor = end + _payload_sentinel_size(payload, end)
    return fields


def _record_text_values(record: dict[str, Any] | None, fields: list[dict[str, Any]]) -> list[str]:
    values: list[str] = []
    for field in fields:
        if field.get("type") == "string" and field.get("value") not in values:
            values.append(str(field.get("value")))
    for key in ("strings", "plainStrings"):
        for hit in (record or {}).get(key) or []:
            text = hit.get("text") if isinstance(hit, dict) else hit
            if isinstance(text, str) and text and text not in values:
                values.append(text)
    return values


def _looks_like_property_key(text: str) -> bool:
    if not text or len(text) > 80:
        return False
    if text in NOISY_PROPERTY_TEXT:
        return False
    if text.isdigit():
        return False
    if any(text.startswith(prefix) for prefix in NOISY_PROPERTY_PREFIXES):
        return False
    return any(ch.isalpha() for ch in text)


def _extract_property_output_refs(texts: list[str]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for text in texts:
        match = PROPERTY_OUTPUT_RE.match(text)
        if not match:
            continue
        refs.append({
            "localId": int(match.group("local")),
            "field": match.group("name"),
            "ref": text,
        })
    return refs


def _extract_trigger_slot_ids(payload: bytes) -> list[int]:
    slots: list[int] = []
    for offset in range(0, max(0, len(payload) - 3)):
        value = struct.unpack_from("<I", payload, offset)[0]
        if 80000 <= value <= 89999 and value not in slots:
            slots.append(value)
    return slots


def _decode_script_event_header_scope(payload: bytes) -> dict[str, Any]:
    """Replay the inherited validate/targetScript/triggerTarget fields.

    Bytes 17 onward begin with ``ActionHeader._validate: Param<bool>``; values
    in that object are validation-node references, not script ids.  Only after
    the variable-length Param comes ``ScriptEventHeader._targetScript`` and
    ``_triggerTarget``.  The latter is SELF=0 or SPECIFY_SCRIPT=1.  A specified
    target can serialize a LevelScriptPtr ``scriptId`` but never a mission or
    quest id.
    """
    cursor = 17

    def read_string() -> tuple[str | None, int] | None:
        nonlocal cursor
        if cursor + 4 > len(payload):
            return None
        size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if size == -1:
            return None, cursor
        if size < 0 or size > 512 or cursor + size > len(payload):
            return None
        raw = payload[cursor : cursor + size]
        cursor += size
        try:
            return raw.decode("utf-8"), cursor
        except UnicodeDecodeError:
            return None

    if cursor >= len(payload) or payload[cursor] != 0x04:
        return {}
    cursor += 1
    if cursor + 9 > len(payload) or payload[cursor] not in (0, 1):
        return {}
    validate_value = bool(payload[cursor])
    cursor += 1
    validate_id_ref = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    validate_source = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    validate_path_result = read_string()
    if validate_path_result is None:
        return {}
    validate_path = validate_path_result[0]

    target_script: dict[str, Any] | None = None
    if cursor >= len(payload):
        return {}
    if payload[cursor] == 0xFF:
        cursor += 1
    else:
        if payload[cursor] != 0x04:
            return {}
        cursor += 1
        if cursor >= len(payload) or payload[cursor] != 0x01:
            return {}
        cursor += 1
        if cursor + 16 > len(payload):
            return {}
        script_id = struct.unpack_from("<Q", payload, cursor)[0]
        cursor += 8
        target_id_ref = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        target_source = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        target_path_result = read_string()
        if target_path_result is None:
            return {}
        target_script = {
            "scriptId": script_id,
            "idRef": target_id_ref,
            "paramSource": target_source,
            "path": target_path_result[0],
        }

    if cursor + 4 > len(payload):
        return {}
    trigger_target = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if trigger_target not in (0, 1):
        return {}

    out: dict[str, Any] = {
        "scriptEventScope": (
            "owning-level-script" if trigger_target == 0 else "specified-level-script"
        ),
        "triggerTarget": "SELF" if trigger_target == 0 else "SPECIFY_SCRIPT",
        "targetScriptPresent": target_script is not None,
        "validateParam": {
            "constValue": validate_value,
            "idRef": validate_id_ref,
            "paramSource": validate_source,
            "path": validate_path,
        },
        "_subtypeOffset": cursor,
    }
    if target_script is not None:
        out["targetScriptParam"] = target_script
        if (
            trigger_target == 1
            and target_script["scriptId"]
            and target_script["idRef"] == -1
            and target_script["paramSource"] == 0
            and not target_script["path"]
        ):
            out["specifiedTargetScriptId"] = target_script["scriptId"]
    return out


_DEFAULT_PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def _decode_param_output_ref(
    payload: bytes,
    cursor: int,
) -> tuple[str, int] | None:
    """Decode the current MemoryPack ``ParamOutput`` property-reference form."""
    decoded = _decode_param_output(payload, cursor)
    if decoded is None:
        return None
    detail, cursor = decoded
    value = detail.get("path")
    if detail.get("paramSource") != 0 or not isinstance(value, str):
        return None
    if not PROPERTY_OUTPUT_RE.match(value):
        return None
    return value, cursor


def _decode_param_output(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a present ``ParamOutput`` including a null property path.

    Most authored outputs point at ``$<localId>@_<field>`` with source zero.
    Current trigger-volume records also use source 100 with a null path.  That
    is still an exact serialized output parameter, but it is not a local
    property reference and must not be promoted to one.
    """
    if cursor + 9 > len(payload) or payload[cursor] != 0x02:
        return None
    source = struct.unpack_from("<i", payload, cursor + 1)[0]
    size = struct.unpack_from("<i", payload, cursor + 5)[0]
    cursor += 9
    if source < 0 or source > 0x10000:
        return None
    if size == -1:
        return {"paramSource": source, "path": None}, cursor
    if size <= 0 or size > 256 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return {"paramSource": source, "path": value}, cursor + size


def _decode_constant_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[str, int] | None:
    """Decode one constant ``Param<string>`` with the installed default tail."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size <= 0 or size > 256 or cursor + size + 12 > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    cursor += size
    if payload[cursor : cursor + 12] != _DEFAULT_PARAM_TAIL:
        return None
    return value, cursor + 12


def _decode_constant_i32_param(
    payload: bytes,
    cursor: int,
) -> tuple[int, int] | None:
    """Decode one constant ``Param<int>`` with the installed default tail."""
    if (
        cursor + 17 > len(payload)
        or payload[cursor] != 0x04
        or payload[cursor + 5 : cursor + 17] != _DEFAULT_PARAM_TAIL
    ):
        return None
    return struct.unpack_from("<i", payload, cursor + 1)[0], cursor + 17


def _decode_constant_bool_param(
    payload: bytes,
    cursor: int,
) -> tuple[bool, int] | None:
    """Decode one constant ``Param<bool>`` with the installed default tail."""
    if (
        cursor + 14 > len(payload)
        or payload[cursor] != 0x04
        or payload[cursor + 1] not in (0, 1)
        or payload[cursor + 2 : cursor + 14] != _DEFAULT_PARAM_TAIL
    ):
        return None
    return bool(payload[cursor + 1]), cursor + 14


def _decode_param_tail(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    """Decode the shared idRef/source/path tail of an authored Param value."""
    if cursor + 12 > len(payload):
        return None
    id_ref, param_source, path_size = struct.unpack_from("<iii", payload, cursor)
    cursor += 12
    if id_ref < -1 or param_source < 0 or param_source > 0x10000:
        return None
    if path_size == -1:
        path = None
    elif 0 <= path_size <= 1024 and cursor + path_size <= len(payload):
        try:
            path = payload[cursor : cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += path_size
    else:
        return None
    return {"idRef": id_ref, "paramSource": param_source, "path": path}, cursor


def _decode_i32_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<i", payload, cursor + 1)[0]
    tail = _decode_param_tail(payload, cursor + 5)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def _decode_bool_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    if (
        cursor + 2 > len(payload)
        or payload[cursor] != 0x04
        or payload[cursor + 1] not in (0, 1)
    ):
        return None
    tail = _decode_param_tail(payload, cursor + 2)
    if tail is None:
        return None
    detail, end = tail
    return {"value": bool(payload[cursor + 1]), **detail}, end


def _decode_float_param(payload: bytes, cursor: int) -> tuple[dict[str, Any], int] | None:
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    value = _round_float(struct.unpack_from("<f", payload, cursor + 1)[0])
    tail = _decode_param_tail(payload, cursor + 5)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def _decode_local_getter_ref(payload: bytes, cursor: int) -> tuple[int, int] | None:
    if (
        cursor + 17 > len(payload)
        or payload[cursor : cursor + 5] != b"\x04\x00\x00\x00\x00"
        or payload[cursor + 9 : cursor + 17] != b"\xff" * 8
    ):
        return None
    local_id = struct.unpack_from("<i", payload, cursor + 5)[0]
    if local_id < 0 or local_id > 0x10000:
        return None
    return local_id, cursor + 17


def _decode_pure_bool_getter_ref(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one exact ``PureGetter<bool>`` local-reference envelope.

    Boolean getter combinators serialize their child nodes directly rather
    than through the 17-byte ``Param<T>`` reference used by integer operands.
    The installed formatter writes tag 04/00, the local getter id, and two
    null i32 sentinels.  Constants remain distinguishable because their
    ``idRef`` is -1.
    """
    if (
        cursor + 14 > len(payload)
        or payload[cursor : cursor + 2] != b"\x04\x00"
        or payload[cursor + 6 : cursor + 14] != b"\xff" * 8
    ):
        return None
    local_id = struct.unpack_from("<i", payload, cursor + 2)[0]
    if local_id < 0 or local_id > 0x10000:
        return None
    return {
        "operandKind": "localGetterRef",
        "getterLocalId": local_id,
    }, cursor + 14


def _decode_bool_operand(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a polymorphic boolean constant/path or local getter operand."""
    getter_ref = _decode_pure_bool_getter_ref(payload, cursor)
    if getter_ref is not None:
        return getter_ref
    return _decode_bool_param(payload, cursor)


def _finish_getter_fields(
    payload: bytes,
    end: int,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """Accept exact subtype EOF or one proven outer-list u32 trailer.

    Some final getter rows are followed by the next serialized ActionMap list
    count before the next UID record begins.  The four bytes are not a getter
    field; retaining the value explicitly keeps the field decoder exact while
    allowing those terminal rows to be used.
    """
    if end == len(payload):
        return detail
    if end + 4 != len(payload):
        return {}
    return {
        **detail,
        "trailingActionMapFramingU32": struct.unpack_from("<I", payload, end)[0],
    }


def _decode_levelscript_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the 16-byte LevelScriptPtr value plus shared Param tail."""
    if cursor + 29 > len(payload) or payload[cursor] != 0x04:
        return None
    script_id = struct.unpack_from("<Q", payload, cursor + 1)[0]
    reserved = struct.unpack_from("<Q", payload, cursor + 9)[0]
    if reserved != 0:
        return None
    tail = _decode_param_tail(payload, cursor + 17)
    if tail is None:
        return None
    tail_detail, end = tail
    if script_id and not _is_plausible_levelscript_id(script_id):
        return None
    mode = "explicit_script" if script_id else "dynamic_or_unresolved"
    if not script_id and tail_detail == {
        "idRef": -1,
        "paramSource": 1002,
        "path": None,
    }:
        mode = "current_script"
    return {
        "mode": mode,
        "scriptId": str(script_id) if script_id else "",
        **tail_detail,
    }, end


def _decode_levelscript_task_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the current ``Param<LevelScriptTaskPtr>`` key shape."""
    if cursor + 2 > len(payload) or payload[cursor] != 0x04:
        return None
    pointer_mode = payload[cursor + 1]
    if pointer_mode not in (0, 1):
        return None
    decoded_key = _decode_nullable_string_value(payload, cursor + 2)
    if decoded_key is None:
        return None
    task_key = decoded_key[0]["value"]
    if task_key is not None and not re.fullmatch(r"[0-9a-f]{8}", task_key):
        return None
    tail = _decode_param_tail(payload, decoded_key[1])
    if tail is None:
        return None
    detail, end = tail
    return {
        "pointerMode": pointer_mode,
        "taskKey": task_key,
        **detail,
    }, end


def _decode_boolean_compare_getter(payload: bytes) -> dict[str, Any]:
    comparer = _decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    value_a = _decode_bool_operand(payload, comparer[1])
    if value_a is None:
        return {}
    value_b = _decode_bool_operand(payload, value_a[1])
    if value_b is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return _finish_getter_fields(payload, value_b[1], {
        "comparerRaw": comparer_raw,
        "comparerName": {0: "Equal", 1: "NotEqual"}.get(comparer_raw, ""),
        "valueA": value_a[0],
        "valueB": value_b[0],
        "payloadShape": "bool-comparer-two-polymorphic-bool-operands-exact-fields",
    })


def _decode_bool_binary_getter(
    payload: bytes,
    *,
    operation: str,
) -> dict[str, Any]:
    value_a = _decode_pure_bool_getter_ref(payload, 0)
    if value_a is None:
        return {}
    value_b = _decode_pure_bool_getter_ref(payload, value_a[1])
    if value_b is None:
        return {}
    return _finish_getter_fields(payload, value_b[1], {
        "operation": operation,
        "valueA": value_a[0],
        "valueB": value_b[0],
        "payloadShape": "two-pure-bool-getter-refs-exact-fields",
    })


def _decode_bool_invert_getter(payload: bytes) -> dict[str, Any]:
    value = _decode_pure_bool_getter_ref(payload, 0)
    if value is None:
        return {}
    return _finish_getter_fields(payload, value[1], {
        "operation": "Not",
        "value": value[0],
        "payloadShape": "one-pure-bool-getter-ref-exact-fields",
    })


def _decode_bool_multi_and_getter(payload: bytes) -> dict[str, Any]:
    if len(payload) < 4:
        return {}
    count = struct.unpack_from("<I", payload, 0)[0]
    if count == 0 or count > 256:
        return {}
    cursor = 4
    values: list[dict[str, Any]] = []
    for _index in range(count):
        value = _decode_pure_bool_getter_ref(payload, cursor)
        if value is None:
            return {}
        values.append(value[0])
        cursor = value[1]
    return _finish_getter_fields(payload, cursor, {
        "operation": "All",
        "values": values,
        "payloadShape": "counted-pure-bool-getter-refs-exact-fields",
    })


def _decode_getter_bool(payload: bytes) -> dict[str, Any]:
    value = _decode_bool_param(payload, 0)
    if value is None:
        return {}
    return _finish_getter_fields(payload, value[1], {
        "value": value[0],
        "payloadShape": "one-bool-param-exact-fields",
    })


def _decode_interactive_check_state_getter(payload: bytes) -> dict[str, Any]:
    """Decode comparer, ScriptEntityPtr target, and expected state exactly."""
    comparer = _decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    target = _decode_constant_entity_ptr_param(payload, comparer[1])
    if target is None:
        return {}
    value = _decode_i32_param(payload, target[1])
    if value is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return _finish_getter_fields(payload, value[1], {
        "type": "InteractiveCheckState",
        "comparer": comparer[0],
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
            2: "GreaterThan",
            3: "GreaterEqual",
            4: "LessThan",
            5: "LessEqual",
        }.get(comparer_raw, ""),
        "target": target[0],
        "value": value[0],
        "payloadShape": "comparer-entity-ptr-state-exact-fields",
        "nativeMappingId": "gameassembly-2026-08-02-interactive-check-state",
    })


def _decode_get_lsm_is_completed_getter(payload: bytes) -> dict[str, Any]:
    """Decode the two formatter fields used by ``GetLsmIsCompleted``.

    The first field is the current fixed-width ``Param<LsmPtr>`` value.  Its
    inner eight-byte value is retained losslessly because the pointer's bit
    allocation is not needed to establish the predicate.  The second field is
    the already-proven ``Param<LevelScriptPtr>`` representation.
    """
    if len(payload) < 21 or payload[:2] != b"\x04\x03":
        return {}
    lsm_tail = _decode_param_tail(payload, 9)
    if lsm_tail is None or lsm_tail[1] != 21:
        return {}
    script_ptr = _decode_levelscript_ptr_param(payload, 21)
    if script_ptr is None:
        return {}
    return _finish_getter_fields(payload, script_ptr[1], {
        "type": "GetLsmIsCompleted",
        "lsmPtr": {
            "rawValueHex": payload[1:9].hex(),
            **lsm_tail[0],
        },
        "scriptPtr": script_ptr[0],
        "resultField": "LevelScriptModule.isCompleted",
        "payloadShape": "lsm-ptr-and-level-script-ptr-exact-fields",
        "nativeMappingId": "gameassembly-2026-08-02-get-lsm-is-completed",
    })


def _decode_int_equal_getter(payload: bytes) -> dict[str, Any]:
    value_a = _decode_i32_operand(payload, 0)
    if value_a is None:
        return {}
    value_b = _decode_i32_operand(payload, value_a[1])
    if value_b is None:
        return {}
    has_getter_ref = any(
        operand.get("operandKind") == "localGetterRef"
        for operand in (value_a[0], value_b[0])
    )
    detail = {
        "operation": "Equal",
        "valueA": value_a[0],
        "valueB": value_b[0],
        "payloadShape": (
            "two-int-operands-exact-eof"
            if has_getter_ref
            else "two-int-params-exact-eof"
        ),
    }
    for label, operand in (("valueA", value_a[0]), ("valueB", value_b[0])):
        getter_local_id = operand.get("getterLocalId")
        if isinstance(getter_local_id, int):
            detail[f"{label}GetterLocalId"] = getter_local_id
    return _finish_getter_fields(payload, value_b[1], detail)


def _decode_i32_operand(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one polymorphic ``Param<int>`` operand exactly.

    The installed serializer uses the same field for authored constants and
    local getter references.  A getter reference has a distinct 17-byte
    envelope, so keep its identity instead of interpreting its local id as a
    constant value.
    """
    getter_ref = _decode_local_getter_ref(payload, cursor)
    if getter_ref is not None:
        return {
            "operandKind": "localGetterRef",
            "getterLocalId": getter_ref[0],
        }, getter_ref[1]
    value = _decode_i32_param(payload, cursor)
    if value is None:
        return None
    return value


def _decode_get_condition_result_getter(payload: bytes) -> dict[str, Any]:
    """Decode the embedded root ``GameCondition`` union used by this getter."""
    decoded = _decode_levelscript_task_condition(payload, 0, len(payload))
    if decoded is None:
        return {}
    condition, end = decoded
    return _finish_getter_fields(payload, end, {
        "condition": condition,
        "payloadShape": "root-game-condition-union-exact-fields",
    })


def _decode_int_random_getter(payload: bytes) -> dict[str, Any]:
    # Generated setter order is _max, then _min (confirmed by the current
    # IntGetterRandomForMemoryPack metadata and the installed payloads).
    maximum = _decode_i32_param(payload, 0)
    if maximum is None:
        return {}
    minimum = _decode_i32_param(payload, maximum[1])
    if minimum is None:
        return {}
    return _finish_getter_fields(payload, minimum[1], {
        "minimum": minimum[0],
        "maximum": maximum[0],
        "payloadShape": "max-then-min-int-params-exact-fields",
    })


def _decode_number_compare_getter(payload: bytes, *, floating: bool) -> dict[str, Any]:
    comparer = _decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    value_a = _decode_local_getter_ref(payload, comparer[1])
    if value_a is None:
        return {}
    value_decoder = _decode_float_param if floating else _decode_i32_param
    value_b = value_decoder(payload, value_a[1])
    if value_b is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return _finish_getter_fields(payload, value_b[1], {
        "comparerRaw": comparer_raw,
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
            2: "GreaterThan",
            3: "GreaterEqual",
            4: "LessThan",
            5: "LessEqual",
        }.get(comparer_raw, ""),
        "valueAGetterLocalId": value_a[0],
        "valueB": value_b[0],
        "valueType": "float" if floating else "int",
        "payloadShape": "number-comparer-getter-ref-constant-exact-eof",
    })


def _decode_getter_int(payload: bytes) -> dict[str, Any]:
    value = _decode_i32_param(payload, 0)
    if value is None:
        return {}
    return _finish_getter_fields(payload, value[1], {
        "value": value[0],
        "payloadShape": "one-int-param-exact-eof",
    })


def _decode_getter_string(payload: bytes) -> dict[str, Any]:
    """Decode the installed ``GetterString`` property-path payload.

    The leading byte is the nullable/default string marker, followed by the
    shared id/source/path fields.  Requiring exact EOF keeps arbitrary strings
    in neighboring records from being promoted to authored property getters.
    """
    if len(payload) < 17 or payload[0] != 0x04:
        return {}
    value_size, id_ref, param_source, path_size = struct.unpack_from(
        "<iiii", payload, 1
    )
    if (
        value_size != -1
        or id_ref != -1
        or param_source < 0
        or param_source > 0x10000
        or path_size <= 0
        or path_size > 1024
        or 17 + path_size != len(payload)
    ):
        return {}
    try:
        path = payload[17:].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    return {
        "value": None,
        "idRef": id_ref,
        "paramSource": param_source,
        "path": path,
        "payloadShape": "nullable-string-property-path-exact-eof",
    }


def _decode_start_dialog_action(payload: bytes) -> dict[str, Any]:
    """Decode the exact dynamic dialog getter reference in StartDialogAction."""
    if len(payload) < 17 or payload[0] != 0x04:
        return {}
    constant_size, getter_local_id, param_source, path_size = struct.unpack_from(
        "<iiii", payload, 1
    )
    if not (
        constant_size == -1
        and 0 <= getter_local_id <= 0x10000
        and param_source == -1
        and path_size == -1
    ):
        return {}
    return {
        "dialogGetterLocalId": getter_local_id,
        "constantDialogId": None,
        "paramSource": param_source,
        "path": None,
        "payloadShape": "null-dialog-value-local-getter-ref-exact-prefix",
    }


def _decode_get_levelscript_stage_getter(payload: bytes) -> dict[str, Any]:
    script_ptr = _decode_levelscript_ptr_param(payload, 0)
    if script_ptr is None:
        return {}
    return _finish_getter_fields(payload, script_ptr[1], {
        "scriptPtr": script_ptr[0],
        "payloadShape": "level-script-ptr-param-exact-fields",
    })


def _decode_is_endmin_gender_getter(payload: bytes) -> dict[str, Any]:
    gender = _decode_i32_param(payload, 0)
    if gender is None:
        return {}
    raw = gender[0]["value"]
    return _finish_getter_fields(payload, gender[1], {
        "gender": gender[0],
        "genderName": {0: "Male", 1: "Female"}.get(raw, ""),
        "payloadShape": "gender-param-exact-fields",
    })


def _decode_levelscript_property_bool_getter(payload: bytes) -> dict[str, Any]:
    property_key = _decode_constant_string_param(payload, 0)
    if property_key is None:
        return {}
    target = _decode_levelscript_ptr_param(payload, property_key[1])
    if target is None:
        return {}
    return _finish_getter_fields(payload, target[1], {
        "propertyKey": property_key[0],
        "targetScript": target[0],
        "payloadShape": "property-key-and-level-script-target-exact-fields",
    })


def _decode_constant_entity_ptr_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the installed constant ``Param<ScriptEntityPtr>`` representation."""
    if cursor + 27 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x03":
        return None
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    if use_slot_id not in (0, 1):
        return None
    id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    param_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    cursor += 27
    if path_size == -1:
        path = None
    elif 0 <= path_size <= 256 and cursor + path_size <= len(payload):
        try:
            path = payload[cursor : cursor + path_size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += path_size
    else:
        return None
    return {
        "logicId": logic_id,
        "slotId": slot_id,
        "useSlotId": bool(use_slot_id),
        "idRef": id_ref,
        "paramSource": param_source,
        "path": path,
    }, cursor


def _decode_get_mission_state_getter(payload: bytes) -> dict[str, Any]:
    """Decode the exact current-build ``GetMissionState._missionId`` field."""
    mission_param = _decode_constant_string_param(payload, 0)
    if mission_param is None or mission_param[1] != len(payload):
        return {}
    mission_id = mission_param[0]
    if not mission_id or not re.fullmatch(r"[A-Za-z0-9_#-]+", mission_id):
        return {}
    return {
        "type": "GetMissionState",
        "missionId": mission_id,
        "payloadShape": "constant-mission-id-exact-eof",
        "serializedMemberCount": 8,
        "pureGetterUnionTag": "0x013a",
        "nativeMappingId": (
            "gameassembly-2026-07-11-puregetter-mission-state"
        ),
        "executionSide": "client",
        "networkRole": "reads_synchronized_local_mission_state",
        "serverExchange": False,
    }


def _decode_compare_mission_state_getter(payload: bytes) -> dict[str, Any]:
    """Decode exact comparer/getter/state operands for ``CompareMissionState``."""
    if len(payload) != 51:
        return {}
    comparer = _decode_constant_i32_param(payload, 0)
    expected_state = _decode_constant_i32_param(payload, 34)
    if comparer is None or comparer[1] != 17 or expected_state is None:
        return {}
    if expected_state[1] != len(payload):
        return {}
    value_a = payload[17:34]
    if (
        value_a[:5] != b"\x04\x00\x00\x00\x00"
        or value_a[9:] != b"\xff" * 8
    ):
        return {}
    source_getter_local_id = struct.unpack_from("<i", value_a, 5)[0]
    if source_getter_local_id < 0 or source_getter_local_id > 0x10000:
        return {}
    return {
        "type": "CompareMissionState",
        "comparerRaw": comparer[0],
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
        }.get(comparer[0], ""),
        "valueAGetterLocalId": source_getter_local_id,
        "valueBStateRaw": expected_state[0],
        "valueBStateName": {
            0: "None",
            1: "Available",
            2: "Processing",
            3: "Completed",
            4: "Failed",
            5: "Disabled",
        }.get(expected_state[0], ""),
        "payloadShape": "comparer-getter-ref-state-constant-exact-eof",
        "serializedMemberCount": 10,
        "pureGetterUnionTag": "0x001f",
        "nativeMappingId": (
            "gameassembly-2026-07-11-puregetter-mission-state"
        ),
    }


def _decode_check_levelscript_stage_getter(payload: bytes) -> dict[str, Any]:
    """Decode the current generic LevelScript-stage comparison getter.

    Current metadata names the runtime fields ``_scriptPtr``, ``_comparer``,
    and ``_value``.  The generated MemoryPack setter order is comparer,
    scriptPtr, value; the native ``GetResult`` body resolves the script, reads
    its stage, and passes the operands to ``ComparerExtensions.DoCompare``.
    """
    comparer = _decode_i32_param(payload, 0)
    if comparer is None:
        return {}
    script_ptr = _decode_levelscript_ptr_param(payload, comparer[1])
    if script_ptr is None:
        return {}
    expected_stage = _decode_i32_param(payload, script_ptr[1])
    if expected_stage is None:
        return {}
    comparer_raw = comparer[0]["value"]
    return _finish_getter_fields(payload, expected_stage[1], {
        "type": "CheckLevelScriptStage",
        "scriptPtr": script_ptr[0],
        "comparer": comparer[0],
        "comparerName": {
            0: "Equal",
            1: "NotEqual",
            2: "GreaterThan",
            3: "GreaterEqual",
            4: "LessThan",
            5: "LessEqual",
        }.get(comparer_raw, ""),
        "expectedStage": expected_stage[0],
        "payloadShape": "comparer-level-script-ptr-stage-exact-fields",
        "serializedMemberCount": 10,
        "pureGetterUnionTag": "0x0013",
        "nativeMappingId": "gameassembly-2026-08-02-check-levelscript-stage",
        "executionSide": "client",
        "serverExchange": False,
    })


def _decode_check_mission_or_quest_complete_getter(
    payload: bytes,
) -> dict[str, Any]:
    """Decode the current mission/quest completion predicate.

    The generated formatter writes ``_isQuest`` followed by ``_missionId``.
    The native ``GetResult`` body selects MissionSystem.GetQuestState when the
    flag is true and GetMissionData otherwise, and accepts state value 3 in
    both paths.
    """
    is_quest = _decode_bool_param(payload, 0)
    if is_quest is None:
        return {}
    identity = _decode_constant_string_param(payload, is_quest[1])
    if identity is None:
        return {}
    mission_or_quest_id = identity[0]
    if not re.fullmatch(r"[A-Za-z0-9_#-]+", mission_or_quest_id):
        return {}
    target_kind = "quest" if is_quest[0]["value"] else "mission"
    return _finish_getter_fields(payload, identity[1], {
        "type": "CheckMissionOrQuestIsComplete",
        "isQuest": is_quest[0],
        "targetKind": target_kind,
        "missionOrQuestId": mission_or_quest_id,
        "completedStateRaw": 3,
        "completedStateName": "Completed",
        "payloadShape": "is-quest-and-identity-exact-fields",
        "serializedMemberCount": 9,
        "pureGetterUnionTag": "0x0016",
        "nativeMappingId": "gameassembly-2026-08-02-check-mission-or-quest-complete",
        "executionSide": "client",
        "networkRole": "reads_synchronized_local_mission_or_quest_state",
        "serverExchange": False,
    })


def _getter_subtype_payload(
    data: bytes,
    record: dict[str, Any],
    next_start: int | None,
) -> bytes:
    """Return subtype fields after the current PureGetter base shell."""
    start = int(record.get("start") or 0)
    prefix_size = 28 if record.get("layout") == "fa" else 26
    end = next_start if isinstance(next_start, int) else len(data)
    if start < 0 or end <= start + prefix_size or end > len(data):
        return b""
    return data[start + prefix_size : end]


def _decode_script_variable_changed_fields(
    payload: bytes,
    *,
    blackboard: bool,
) -> dict[str, Any]:
    """Decode exact SELF/specified-script variable-listener operands.

    The generated current-build formatters order the subtype members as
    ``key, oldValue, value`` for BB variables and ``oldValue, propertyKey,
    value`` for LevelScript properties.  Requiring exact EOF prevents strings
    in later action records from being mistaken for listener keys.
    """
    scope = _decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int):
        return {}

    if blackboard:
        key_param = _decode_constant_string_param(payload, cursor)
        if key_param is None:
            return {}
        key, cursor = key_param
        old_output = _decode_param_output_ref(payload, cursor)
        if old_output is None:
            return {}
        old_ref, cursor = old_output
    else:
        old_output = _decode_param_output_ref(payload, cursor)
        if old_output is None:
            return {}
        old_ref, cursor = old_output
        key_param = _decode_constant_string_param(payload, cursor)
        if key_param is None:
            return {}
        key, cursor = key_param

    value_output = _decode_param_output_ref(payload, cursor)
    if value_output is None:
        return {}
    value_ref, cursor = value_output
    if cursor != len(payload):
        return {}
    return {
        **scope,
        ("blackboardKeyFilter" if blackboard else "propertyKeyFilter"): key,
        "oldValueOutputRef": old_ref,
        "valueOutputRef": value_ref,
        "payloadShape": (
            "constant-blackboard-key-and-output-refs-exact-eof"
            if blackboard
            else "constant-property-key-and-output-refs-exact-eof"
        ),
    }


def _decode_leader_trigger_volume_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact ScriptEvent trigger-slot selector prefix.

    Some records are followed by serialized trigger-volume configuration before
    the next UID record.  Only the inherited scope and first subtype parameters
    belong to the receiver, so this intentionally validates that prefix rather
    than scanning every integer in the wider record window.
    """
    scope = _decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int):
        return {}
    subtype_offset = cursor
    slot_param = _decode_constant_i32_param(payload, cursor)
    if slot_param is None:
        return {}
    slot_id, cursor = slot_param
    output_ref: str | None = None
    output_param: dict[str, Any] | None = None
    if cursor < len(payload) and payload[cursor] == 0xFF:
        cursor += 1
    else:
        output = _decode_param_output(payload, cursor)
        if output is None:
            return {}
        output_param, cursor = output
        candidate_ref = output_param.get("path")
        if (
            output_param.get("paramSource") == 0
            and isinstance(candidate_ref, str)
            and PROPERTY_OUTPUT_RE.match(candidate_ref)
        ):
            output_ref = candidate_ref
    return {
        **scope,
        "triggerSlotIdFilter": slot_id,
        "triggerSlotIdOutputRef": output_ref,
        "triggerSlotIdOutputParam": output_param,
        "subtypeConsumedBytes": cursor - subtype_offset,
        "payloadShape": "constant-trigger-slot-selector-prefix",
    }


def _decode_entity_cast_skill_fields(payload: bytes) -> dict[str, Any]:
    """Decode the installed OnEntityCastSkill outputs and optional filters."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL:
        return {}
    cursor = 31
    outputs: dict[str, str] = {}
    for field in ("entity", "entityTemplateId", "firstTargetId"):
        output = _decode_param_output_ref(payload, cursor)
        if output is None:
            return {}
        outputs[field], cursor = output
    character_filter = _decode_constant_bool_param(payload, cursor)
    if character_filter is None:
        return {}
    is_character, cursor = character_filter
    skill_output = _decode_param_output_ref(payload, cursor)
    if skill_output is None:
        return {}
    outputs["skillId"], cursor = skill_output
    skill_filter = _decode_constant_i32_param(payload, cursor)
    if skill_filter is None:
        return {}
    skill_type, cursor = skill_filter
    trailing_container_bytes = len(payload) - cursor
    return {
        "entityOutputRef": outputs["entity"],
        "entityTemplateIdOutputRef": outputs["entityTemplateId"],
        "firstTargetIdOutputRef": outputs["firstTargetId"],
        "skillIdOutputRef": outputs["skillId"],
        "isCharacterFilter": is_character,
        "skillTypeFilter": skill_type,
        "filterModeEnabled": bool(payload[4]),
        "subtypeConsumedBytes": cursor,
        "trailingContainerBytes": trailing_container_bytes,
        "payloadShape": (
            "cast-skill-outputs-and-filter-operands-exact-eof"
            if not trailing_container_bytes
            else "cast-skill-outputs-and-filter-operands-exact-prefix"
        ),
    }


def _decode_specific_entity_die_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact entity output plus constant entity selector."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL:
        return {}
    output = _decode_param_output_ref(payload, 31)
    if output is None:
        return {}
    output_ref, cursor = output
    entity_param = _decode_constant_entity_ptr_param(payload, cursor)
    if entity_param is None:
        return {}
    entity_filter, cursor = entity_param
    if cursor != len(payload):
        return {}
    return {
        "entityOutputRef": output_ref,
        "entityFilter": entity_filter,
        "payloadShape": "entity-output-and-constant-entity-filter-exact-eof",
    }


def _decode_any_entity_die_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact entity-list, monster, and list-filter operands."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL:
        return {}
    output = _decode_param_output_ref(payload, 31)
    if output is None:
        return {}
    output_ref, cursor = output
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return {}
    count = struct.unpack_from("<I", payload, cursor + 1)[0]
    cursor += 5
    if count > 64:
        return {}
    entity_filters: list[dict[str, Any]] = []
    for _ in range(count):
        # ScriptEntityPtr values inside this current list are union tag 0x03,
        # uint64 logic id, uint32 slot id, then the use-slot boolean.
        if cursor + 14 > len(payload) or payload[cursor] != 0x03:
            return {}
        use_slot_id = payload[cursor + 13]
        if use_slot_id not in (0, 1):
            return {}
        entity_filters.append({
            "logicId": struct.unpack_from("<Q", payload, cursor + 1)[0],
            "slotId": struct.unpack_from("<I", payload, cursor + 9)[0],
            "useSlotId": bool(use_slot_id),
        })
        cursor += 14
    if payload[cursor : cursor + 12] != _DEFAULT_PARAM_TAIL:
        return {}
    cursor += 12
    is_monster_param = _decode_constant_bool_param(payload, cursor)
    if is_monster_param is None:
        return {}
    is_monster, cursor = is_monster_param
    filter_by_list_param = _decode_constant_bool_param(payload, cursor)
    if filter_by_list_param is None:
        return {}
    filter_by_list, cursor = filter_by_list_param
    if cursor != len(payload):
        return {}
    return {
        "entityOutputRef": output_ref,
        "entityListFilter": entity_filters,
        "isMonsterFilter": is_monster,
        "filterByList": filter_by_list,
        "payloadShape": "constant-entity-list-and-bool-filters-exact-eof",
    }


def _decode_encounter_battle_part_begin_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact LevelScript-variable pointer filter and null output."""
    if (
        len(payload) != 53
        or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL
        or payload[31] != 0x04
        or payload[40:52] != _DEFAULT_PARAM_TAIL
        or payload[52] != 0xFF
    ):
        return {}
    # Param<LevelScriptVariablePtr> is tag 0x04, a uint64 script pointer,
    # the ordinary Param tail, then a null output.  The pointer's low byte can
    # itself be 0x03; it is data, not a nested union tag.
    return {
        "levelScriptVariableFilter": struct.unpack_from("<Q", payload, 32)[0],
        "levelScriptVariableOutputPresent": False,
        "payloadShape": "constant-level-script-variable-pointer-null-output-exact-eof",
    }


def _decode_scripted_char_patrol_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact patrol-event key selector and output references."""
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL:
        return {}
    entity_output = _decode_param_output_ref(payload, 31)
    if entity_output is None:
        return {}
    entity_ref, cursor = entity_output
    key_param = _decode_constant_string_param(payload, cursor)
    if key_param is None:
        return {}
    key_filter, cursor = key_param
    if cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    cursor += 1
    patrol_output = _decode_param_output_ref(payload, cursor)
    if patrol_output is None:
        return {}
    patrol_ref, cursor = patrol_output
    if cursor != len(payload):
        return {}
    return {
        "scriptedCharEventKeyFilter": key_filter,
        "keyOutputPresent": False,
        "entityOutputRef": entity_ref,
        "patrolIdOutputRef": patrol_ref,
        "payloadShape": "constant-patrol-key-and-output-refs-exact-eof",
    }


def _decode_entity_event_header_scope(payload: bytes) -> dict[str, Any]:
    """Decode the exact current single-entity EntityEventHeader scope.

    The installed ``Param<ScriptEntityPtr>`` formatter serializes the pointer
    value followed by the ordinary ``Param`` id/source/path fields.  Accept
    both the constant pointer form and an authored dynamic property path, then
    require a null target-list input/output and ``SPECIFY_ENTITY``.  This
    exposes the serialized receiver selector; it never infers mission
    ownership from an entity, slot, or property name.
    """
    cursor = 17
    if cursor + 14 > len(payload) or payload[cursor] != 0x04:
        return {}
    validate_value = payload[cursor + 1]
    if validate_value not in (0, 1):
        return {}
    validate_id_ref = struct.unpack_from("<i", payload, cursor + 2)[0]
    validate_source = struct.unpack_from("<i", payload, cursor + 6)[0]
    validate_path_size = struct.unpack_from("<i", payload, cursor + 10)[0]
    cursor += 14
    if validate_path_size == -1:
        validate_path = None
    elif 0 <= validate_path_size <= 512 and cursor + validate_path_size <= len(payload):
        try:
            validate_path = payload[cursor : cursor + validate_path_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += validate_path_size
    else:
        return {}
    if cursor + 27 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x03":
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    if use_slot_id not in (0, 1):
        return {}
    cursor += 15
    if cursor + 12 > len(payload):
        return {}
    target_id_ref = struct.unpack_from("<i", payload, cursor)[0]
    target_source = struct.unpack_from("<i", payload, cursor + 4)[0]
    target_path_size = struct.unpack_from("<i", payload, cursor + 8)[0]
    cursor += 12
    if target_path_size == -1:
        target_path = None
    elif 0 <= target_path_size <= 512 and cursor + target_path_size <= len(payload):
        try:
            target_path = payload[cursor : cursor + target_path_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += target_path_size
    else:
        return {}
    if payload[cursor : cursor + 17] != b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4:
        return {}
    cursor += 17
    target_list_output_present = False
    target_list_output_encoding = "omitted-null"
    if cursor < len(payload) and payload[cursor] == 0xFF:
        # Older/current records may write an explicit null ParamOutput for the
        # target list.  Other current member-count layouts omit that trailing
        # null and place triggerTarget immediately after targetEntityList.
        cursor += 1
        target_list_output_encoding = "explicit-null"
    if cursor + 4 > len(payload):
        return {}
    trigger_target = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if trigger_target != 1:
        return {}
    return {
        "validateParam": {
            "constValue": bool(validate_value),
            "idRef": validate_id_ref,
            "paramSource": validate_source,
            "path": validate_path,
        },
        "entityEventScope": "specified-entity",
        "triggerTarget": "SPECIFY_ENTITY",
        "targetEntity": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
        },
        "targetEntityParam": {
            "idRef": target_id_ref,
            "paramSource": target_source,
            "path": target_path,
        },
        "targetEntityListPresent": False,
        "targetEntityListOutputPresent": target_list_output_present,
        "targetEntityListOutputEncoding": target_list_output_encoding,
        "_subtypeOffset": cursor,
    }


def _decode_script_stage_changed_fields(payload: bytes) -> dict[str, Any]:
    """Decode the current OnScriptStageChanged subtype prefix.

    Native setter order proves ``_newStageFilter`` precedes
    ``_newStageOutput``.  A present Param<int> is encoded at offset 36 as an
    object tag, i32 constant, and the exact three-part default source/path
    tail.  A null filter is one byte.  The record window may include later
    outer action-map bytes, so only this guarded subtype prefix is consumed.
    """
    scope = _decode_script_event_header_scope(payload)
    cursor = scope.pop("_subtypeOffset", None)
    if not scope or not isinstance(cursor, int) or cursor >= len(payload):
        return {}
    out = dict(scope)
    filter_offset = cursor
    if payload[cursor] == 0xFF:
        cursor += 1
        out["newStageFilterPresent"] = False
        out["newStageFilterOffset"] = _offset_hex(filter_offset)
    elif payload[cursor] == 0x04 and cursor + 13 <= len(payload):
        cursor += 1
        stage_value = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        stage_id_ref = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        stage_source = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if cursor + 4 > len(payload):
            return {}
        path_size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if path_size == -1:
            stage_path = None
        elif 0 <= path_size <= 512 and cursor + path_size <= len(payload):
            try:
                stage_path = payload[cursor : cursor + path_size].decode("utf-8")
            except UnicodeDecodeError:
                return {}
            cursor += path_size
        else:
            return {}
        out.update({
            "newStageFilterPresent": True,
            "newStageFilter": stage_value,
            "newStageFilterParam": {
                "constValue": stage_value,
                "idRef": stage_id_ref,
                "paramSource": stage_source,
                "path": stage_path,
            },
            "newStageFilterOffset": _offset_hex(filter_offset),
        })
    else:
        return {}

    output_offset = cursor
    if cursor >= len(payload):
        return {}
    if payload[cursor] == 0xFF:
        cursor += 1
        out["newStageOutputPresent"] = False
    elif payload[cursor] == 0x02 and cursor + 9 <= len(payload):
        cursor += 1
        output_source = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        output_size = struct.unpack_from("<i", payload, cursor)[0]
        cursor += 4
        if output_size < 0 or output_size > 512 or cursor + output_size > len(payload):
            return {}
        try:
            output_path = payload[cursor : cursor + output_size].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        cursor += output_size
        out.update({
            "newStageOutputPresent": True,
            "newStageOutputParam": {
                "paramSource": output_source,
                "path": output_path,
            },
        })
    else:
        return {}
    out["newStageOutputOffset"] = _offset_hex(output_offset)
    out["subtypeConsumedBytes"] = cursor - filter_offset
    return out


def _decode_spawner_begin_fields(payload: bytes, *, wave: bool) -> dict[str, Any]:
    """Decode the current exact SpawnerGroup/WaveBegin consumer shapes.

    Both event types serialize one inherited Param<bool> before their subtype
    fields.  The current residual Story consumers use constant strings,
    constant SpawnerPtr ids, null outputs, and end exactly after the final
    output marker.  Other parameter/output variants intentionally fail closed.
    """
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    inherited_filter = b"\x04\x01" + param_tail
    if len(payload) < 31 or payload[17:31] != inherited_filter:
        return {}

    cursor = 31

    def read_string_param() -> str | None:
        nonlocal cursor
        if cursor + 5 > len(payload) or payload[cursor] != 0x04:
            return None
        size = struct.unpack_from("<I", payload, cursor + 1)[0]
        cursor += 5
        if size > 256 or cursor + size + 12 > len(payload):
            return None
        raw = payload[cursor : cursor + size]
        cursor += size
        if payload[cursor : cursor + 12] != param_tail:
            return None
        cursor += 12
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def read_spawner_param() -> int | None:
        nonlocal cursor
        if cursor + 21 > len(payload) or payload[cursor] != 0x04:
            return None
        value = struct.unpack_from("<Q", payload, cursor + 1)[0]
        cursor += 9
        if payload[cursor : cursor + 12] != param_tail:
            return None
        cursor += 12
        return value

    if wave:
        spawner_id = read_spawner_param()
        if spawner_id is None or cursor >= len(payload) or payload[cursor] != 0xFF:
            return {}
        cursor += 1
        key = read_string_param()
        if key is None or cursor >= len(payload) or payload[cursor] != 0xFF:
            return {}
        cursor += 1
        if cursor != len(payload):
            return {}
        return {
            "spawnerFilterId": spawner_id,
            "spawnerOutputPresent": False,
            "waveKeyFilter": key,
            "waveKeyOutputPresent": False,
            "payloadShape": "constant-spawner-and-wave-key-null-outputs-exact-eof",
        }

    key = read_string_param()
    if key is None or cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    cursor += 1
    spawner_id = read_spawner_param()
    if spawner_id is None or cursor >= len(payload) or payload[cursor] != 0xFF:
        return {}
    cursor += 1
    if cursor != len(payload):
        return {}
    return {
        "groupKeyFilter": key,
        "groupKeyOutputPresent": False,
        "spawnerFilterId": spawner_id,
        "spawnerOutputPresent": False,
        "payloadShape": "constant-group-key-and-spawner-null-outputs-exact-eof",
    }


def _decode_spawner_complete_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact current ``OnSpawnerComplete`` consumer shape.

    The installed formatter appends ``_spawnerFilter: Param<SpawnerPtr>`` and
    ``_spawnerOutput: ParamOutput<SpawnerPtr>`` after the inherited
    ``ActionHeader._validate`` parameter.  The current residual Story consumer
    uses one constant uint64 spawner id, a null output, and exact EOF.
    """
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    inherited_filter = b"\x04\x01" + param_tail
    if (
        len(payload) != 53
        or payload[17:31] != inherited_filter
        or payload[31] != 0x04
        or payload[40:52] != param_tail
        or payload[52] != 0xFF
    ):
        return {}
    return {
        "spawnerFilterId": struct.unpack_from("<Q", payload, 32)[0],
        "spawnerOutputPresent": False,
        "payloadShape": "constant-spawner-null-output-exact-eof",
    }


def _decode_spawner_entity_spawn_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact current OnSpawnerEntitySpawn selector/output shape."""
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    if len(payload) < 90 or payload[17:31] != b"\x04\x01" + param_tail:
        return {}
    cursor = 31

    def read_output() -> str | None:
        nonlocal cursor
        if cursor + 9 > len(payload) or payload[cursor] != 0x02:
            return None
        source = struct.unpack_from("<i", payload, cursor + 1)[0]
        size = struct.unpack_from("<i", payload, cursor + 5)[0]
        cursor += 9
        if source != 0 or size <= 0 or size > 256 or cursor + size > len(payload):
            return None
        try:
            value = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
        return value

    def read_i32_param() -> int | None:
        nonlocal cursor
        if cursor + 17 > len(payload) or payload[cursor] != 0x04:
            return None
        value = struct.unpack_from("<i", payload, cursor + 1)[0]
        if payload[cursor + 5 : cursor + 17] != param_tail:
            return None
        cursor += 17
        return value

    def read_string_param() -> str | None:
        nonlocal cursor
        if cursor + 5 > len(payload) or payload[cursor] != 0x04:
            return None
        size = struct.unpack_from("<i", payload, cursor + 1)[0]
        cursor += 5
        if size <= 0 or size > 256 or cursor + size + 12 > len(payload):
            return None
        try:
            value = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
        if payload[cursor : cursor + 12] != param_tail:
            return None
        cursor += 12
        return value

    def read_u64_param() -> int | None:
        nonlocal cursor
        if cursor + 21 > len(payload) or payload[cursor] != 0x04:
            return None
        value = struct.unpack_from("<Q", payload, cursor + 1)[0]
        if payload[cursor + 9 : cursor + 21] != param_tail:
            return None
        cursor += 21
        return value

    entity_output = read_output()
    entity_template_filter = read_i32_param()
    group_key = read_string_param()
    group_output = read_output()
    spawner_id = read_u64_param()
    if (
        not entity_output
        or entity_template_filter is None
        or not group_key
        or not group_output
        or spawner_id is None
        or cursor >= len(payload)
        or payload[cursor] != 0xFF
    ):
        return {}
    cursor += 1
    wave_output = read_output()
    if not wave_output or cursor != len(payload):
        return {}
    return {
        "entityOutputRef": entity_output,
        "entityTemplateIdFilter": entity_template_filter,
        "groupKeyFilter": group_key,
        "groupKeyOutputRef": group_output,
        "spawnerFilterId": spawner_id,
        "spawnerOutputPresent": False,
        "waveKeyOutputRef": wave_output,
        "payloadShape": "constant-spawner-group-and-template-exact-eof",
    }


def _decode_spawner_entity_lifecycle_fields(payload: bytes) -> dict[str, Any]:
    """Decode current spawn-entity die/start/end filters and outputs.

    Installed MemoryPack setter order is entity output, filter type, group
    filter/output, spawner filter, then wave filter/output.  Nullable group and
    wave filters are retained as nulls; they are not inferred from filterType.
    """
    if len(payload) < 31 or payload[17:31] != b"\x04\x01" + _DEFAULT_PARAM_TAIL:
        return {}
    cursor = 31

    entity_output = _decode_param_output(payload, cursor)
    if entity_output is None:
        return {}
    entity_output_detail, cursor = entity_output

    filter_type = _decode_i32_param(payload, cursor)
    if filter_type is None:
        return {}
    filter_type_detail, cursor = filter_type

    def read_optional_string() -> tuple[str | None, int] | None:
        nonlocal cursor
        if cursor >= len(payload):
            return None
        if payload[cursor] == 0xFF:
            cursor += 1
            return None, cursor
        decoded = _decode_constant_string_param(payload, cursor)
        if decoded is None:
            return None
        value, cursor = decoded
        return value, cursor

    group_filter = read_optional_string()
    if group_filter is None:
        return {}
    group_key, _ = group_filter

    group_output = _decode_param_output(payload, cursor)
    if group_output is None:
        return {}
    group_output_detail, cursor = group_output

    if cursor + 21 > len(payload) or payload[cursor] != 0x04:
        return {}
    spawner_id = struct.unpack_from("<Q", payload, cursor + 1)[0]
    if payload[cursor + 9 : cursor + 21] != _DEFAULT_PARAM_TAIL:
        return {}
    cursor += 21

    wave_filter = read_optional_string()
    if wave_filter is None:
        return {}
    wave_key, _ = wave_filter

    wave_output = _decode_param_output(payload, cursor)
    if wave_output is None:
        return {}
    wave_output_detail, cursor = wave_output
    if cursor != len(payload):
        return {}

    return {
        "entityOutputParam": entity_output_detail,
        "filterType": filter_type_detail,
        "groupKeyFilter": group_key,
        "groupKeyOutputParam": group_output_detail,
        "spawnerFilterId": spawner_id,
        "waveKeyFilter": wave_key,
        "waveKeyOutputParam": wave_output_detail,
        "payloadShape": "spawner-entity-lifecycle-filters-and-outputs-exact-eof",
    }


def _decode_npc_patrol_checkpoint_fields(payload: bytes) -> dict[str, Any]:
    """Decode the exact dynamic-NPC patrol/checkpoint listener fields."""
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    if len(payload) < 100 or payload[17:31] != b"\x04\x01" + param_tail:
        return {}
    cursor = 31
    if cursor + 27 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x03":
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    target_id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    target_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    cursor += 27
    if use_slot_id not in (0, 1) or path_size <= 0 or path_size > 256:
        return {}
    if cursor + path_size > len(payload):
        return {}
    try:
        target_path = payload[cursor : cursor + path_size].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    cursor += path_size

    def read_i32_param() -> int | None:
        nonlocal cursor
        if cursor + 17 > len(payload) or payload[cursor] != 0x04:
            return None
        value = struct.unpack_from("<i", payload, cursor + 1)[0]
        if payload[cursor + 5 : cursor + 17] != param_tail:
            return None
        cursor += 17
        return value

    patrol_id = read_i32_param()
    checkpoint_index = read_i32_param()
    if patrol_id is None or checkpoint_index is None:
        return {}
    return {
        "npcEntityFilter": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
            "idRef": target_id_ref,
            "paramSource": target_source,
            "path": target_path,
        },
        "patrolIdFilter": patrol_id,
        "checkpointIndexFilter": checkpoint_index,
        "payloadShape": "dynamic-npc-patrol-checkpoint-fields",
    }


def _decode_named_native_event_detail(
    native_header_name: str,
    payload: bytes,
    texts: list[str],
    property_outputs: list[dict[str, Any]],
    trigger_slot_ids: list[int],
) -> dict[str, Any]:
    """Label exact current-build event fields without inventing ownership.

    The field names come from the installed build's generated MemoryPack
    types. Values still come only from the serialized LevelScript record.
    Complex pointer parameters remain undecoded; when their payload contains
    extra strings those strings are exposed as arguments, never interpreted as
    mission ids or producer ownership.
    """
    literal_texts = [text for text in texts if text and not text.startswith("$")]

    def refs(field: str) -> list[dict[str, Any]]:
        return [row for row in property_outputs if row.get("field") == field]

    detail: dict[str, Any] = {}
    if native_header_name == "ScriptEvent_OnScriptActive":
        scope = _decode_script_event_header_scope(payload)
        scope.pop("_subtypeOffset", None)
        if scope:
            detail = {
                "type": native_header_name,
                **scope,
                "subtypeFieldCount": 0,
                "transport": "local-level-script-runtime-event",
                "serializedMissionOrQuestId": False,
                "serverExchange": False,
                "summary": "local LevelScript runtime becomes active",
            }
    elif native_header_name == "ScriptEvent_OnScriptComplete":
        scope = _decode_script_event_header_scope(payload)
        subtype_offset = scope.pop("_subtypeOffset", None)
        if scope and isinstance(subtype_offset, int):
            trailing_container_bytes = len(payload) - subtype_offset
            detail = {
                "type": native_header_name,
                **scope,
                "subtypeFieldCount": 0,
                "subtypeConsumedBytes": 0,
                "trailingContainerBytes": trailing_container_bytes,
                "payloadShape": (
                    "zero-subtype-exact-eof"
                    if not trailing_container_bytes
                    else "zero-subtype-exact-prefix"
                ),
                "transport": "local-level-script-runtime-event",
                "serializedMissionOrQuestId": False,
                "serverExchange": False,
                "summary": "selected LevelScript runtime completes",
            }
    elif native_header_name in {
        "ScriptEvent_OnBBVariableChanged",
        "ScriptEvent_OnPropertyChanged",
    }:
        blackboard = native_header_name == "ScriptEvent_OnBBVariableChanged"
        variable_fields = _decode_script_variable_changed_fields(
            payload,
            blackboard=blackboard,
        )
        if variable_fields:
            key_field = "blackboardKeyFilter" if blackboard else "propertyKeyFilter"
            key = variable_fields[key_field]
            detail = {
                "type": native_header_name,
                **variable_fields,
                "oldValueOutputRefs": refs("oldValue"),
                "valueOutputRefs": refs("value"),
                "transport": "local-level-script-variable-event",
                "serializedMissionOrQuestId": False,
                "serverExchange": False,
                "summary": (
                    f"local LevelScript blackboard key {key} changes"
                    if blackboard
                    else f"local LevelScript property {key} changes"
                ),
            }
    elif native_header_name == "ScriptEvent_OnScriptStageChanged":
        stage_fields = _decode_script_stage_changed_fields(payload)
        stage_filter = stage_fields.get("newStageFilter")
        if stage_fields:
            detail = {
                "type": native_header_name,
                **stage_fields,
                "newStageOutputRefs": refs("newStageOutput"),
                "transport": "local-level-script-runtime-event",
                "serializedMissionOrQuestId": False,
                "serverExchange": False,
                "summary": (
                    f"local LevelScript stage changes to {stage_filter}"
                    if isinstance(stage_filter, int)
                    else "local LevelScript stage changes"
                ),
            }
    elif native_header_name == "LevelEvent_OnBattleSignal" and literal_texts:
        detail = {
            "type": native_header_name,
            "signalId": literal_texts[0],
            "floatValueOutputRefs": refs("floatValue"),
            "transport": "local-level-runtime-event",
            "serverExchange": False,
            "clientRequest": False,
            "expectedServerReturn": False,
            "serializedMissionOrQuestId": False,
            "summary": f"battle signal {literal_texts[0]}",
        }
    elif native_header_name in {
        "LevelEvent_OnCustomEvent",
        "ScriptEvent_OnCustomEvent",
        "EntityEvent_OnCustomEvent",
        "EntityEvent_OnCustomEventNew",
    } and literal_texts:
        entity_scope: dict[str, Any] = {}
        if native_header_name.startswith("EntityEvent_"):
            entity_scope = _decode_entity_event_header_scope(payload)
            entity_scope.pop("_subtypeOffset", None)
        detail = {
            "type": native_header_name,
            **entity_scope,
            "eventKey": literal_texts[0],
            "eventArgsOutputRefs": refs("eventArgsPtr"),
            "additionalEventArgumentTexts": literal_texts[1:],
            "transport": (
                "local-entity-runtime-event"
                if entity_scope
                else "local-level-script-runtime-event"
            ),
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
            "summary": f"custom event {literal_texts[0]}",
        }
    elif native_header_name == "LevelEvent_OnGuideGroupComplete" and literal_texts:
        detail = {
            "type": native_header_name,
            "guideIdFilter": literal_texts[0],
            "guideIdOutputRefs": refs("guideId"),
            "summary": f"guide group complete {literal_texts[0]}",
        }
    elif native_header_name == "LevelEvent_OnDialogExit" and literal_texts:
        # The current native type is the local LevelEvent.OnDialogExit
        # consumer (tag 0x55/member-count 19). Its Process method applies the
        # serialized dialog/optional-finish filters and writes these three
        # outputs before continuing the local ActionHeader chain. A separate
        # tag, 0x8a, names LevelEvent.OnServerDialogExit; do not collapse the
        # two or imply a request/response edge from this record.
        detail = {
            "type": native_header_name,
            "dialogIdFilter": literal_texts[0],
            "additionalDialogFilterTexts": literal_texts[1:],
            "dialogIdOutputRefs": refs("dialogId"),
            "finishIdOutputRefs": refs("finishId"),
            "isSkippedOutputRefs": refs("isSkipped"),
            "executionSide": "client",
            "serverExchange": False,
            "distinctServerEventType": "LevelEvent_OnServerDialogExit",
            "summary": f"local dialog exit {literal_texts[0]}",
        }
    elif native_header_name == "LevelEvent_OnSpawnerGroupBegin":
        spawner_fields = _decode_spawner_begin_fields(payload, wave=False)
        detail = {
            "type": native_header_name,
            **spawner_fields,
            "groupKeyFilter": (
                spawner_fields.get("groupKeyFilter")
                or (literal_texts[0] if literal_texts else "")
            ),
            "groupKeyOutputRefs": refs("groupKeyOutput"),
            "spawnerOutputRefs": refs("spawnerOutput"),
            "summary": (
                "spawner group begin "
                f"{spawner_fields.get('groupKeyFilter') or (literal_texts[0] if literal_texts else '')}"
            ),
        }
    elif native_header_name == "LevelEvent_OnSpawnerWaveBegin":
        spawner_fields = _decode_spawner_begin_fields(payload, wave=True)
        detail = {
            "type": native_header_name,
            **spawner_fields,
            "spawnerOutputRefs": refs("spawnerOutput"),
            "waveKeyOutputRefs": refs("waveKeyOutput"),
            "summary": (
                "spawner wave begin "
                f"{spawner_fields.get('waveKeyFilter') or (literal_texts[0] if literal_texts else '')}"
            ),
        }
    elif native_header_name == "LevelEvent_OnSpawnerComplete":
        spawner_fields = _decode_spawner_complete_fields(payload)
        if spawner_fields:
            detail = {
                "type": native_header_name,
                **spawner_fields,
                "spawnerOutputRefs": refs("spawnerOutput"),
                "transport": "server-to-client-push-then-local-runtime-event",
                "serverExchange": True,
                "serverMessage": "SC_SCENE_MONSTER_SPAWNER_COMPLETE",
                "serverFields": ["sceneNumId", "spawnerId"],
                "clientRequest": False,
                "expectedClientReply": False,
                "summary": (
                    "server confirms spawner completion "
                    f"{spawner_fields.get('spawnerFilterId')}"
                ),
            }
    elif native_header_name == "LevelEvent_OnSpawnerEntitySpawn":
        spawner_fields = _decode_spawner_entity_spawn_fields(payload)
        if spawner_fields:
            detail = {
                "type": native_header_name,
                **spawner_fields,
                "transport": "local-spawner-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"spawner {spawner_fields['spawnerFilterId']} group "
                    f"{spawner_fields['groupKeyFilter']} emits an entity"
                ),
            }
    elif native_header_name in {
        "LevelEvent_OnSpawnerEntityDie",
        "LevelEvent_OnSpawnerEntityDieStart",
        "LevelEvent_OnSpawnerEntityDieEnd",
    }:
        spawner_fields = _decode_spawner_entity_lifecycle_fields(payload)
        if spawner_fields:
            phase = {
                "LevelEvent_OnSpawnerEntityDie": "dies",
                "LevelEvent_OnSpawnerEntityDieStart": "starts dying",
                "LevelEvent_OnSpawnerEntityDieEnd": "finishes dying",
            }[native_header_name]
            detail = {
                "type": native_header_name,
                **spawner_fields,
                "entityOutputRefs": refs("entityOutput"),
                "groupKeyOutputRefs": refs("groupKeyOutput"),
                "waveKeyOutputRefs": refs("waveKeyOutput"),
                "transport": "local-spawner-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": f"an entity from spawner {spawner_fields['spawnerFilterId']} {phase}",
            }
    elif native_header_name == "LevelEvent_OnNpcPatrolCheckpointReach":
        patrol_fields = _decode_npc_patrol_checkpoint_fields(payload)
        if patrol_fields:
            detail = {
                "type": native_header_name,
                **patrol_fields,
                "npcPositionOutputRefs": refs("npcPosition"),
                "transport": "local-npc-patrol-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"NPC {patrol_fields['npcEntityFilter']['path']} reaches "
                    f"patrol {patrol_fields['patrolIdFilter']} checkpoint "
                    f"{patrol_fields['checkpointIndexFilter']}"
                ),
            }
    elif native_header_name == "LevelEvent_OnTeleportFinish" and literal_texts:
        detail = {
            "type": native_header_name,
            "actionIdFilter": literal_texts[0],
            "serializedMissionOrQuestId": False,
            "summary": f"teleport action finishes {literal_texts[0]}",
        }
    elif native_header_name == "LevelEvent_OnSquadInFightChanged":
        detail = {
            "type": native_header_name,
            "inFightOutputRefs": refs("inFight"),
            "transport": "local-squad-runtime-event",
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
            "summary": "squad combat state changes",
        }
    elif native_header_name == "LevelEvent_OnSkipBattlePopupConfirm":
        detail = {
            "type": native_header_name,
            "subtypeFieldCount": 0,
            "serializedMissionOrQuestId": False,
            "summary": "skip-battle popup is confirmed",
        }
    elif native_header_name == "LevelEvent_OnEntityCastSkill":
        skill_fields = _decode_entity_cast_skill_fields(payload)
        if skill_fields:
            detail = {
                "type": native_header_name,
                **skill_fields,
                "entityOutputRefs": refs("entity"),
                "entityTemplateIdOutputRefs": refs("entityTemplateId"),
                "firstTargetIdOutputRefs": refs("firstTargetId"),
                "skillIdOutputRefs": refs("skillId"),
                "transport": "local-entity-skill-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    "entity casts a skill (filter mode enabled)"
                    if skill_fields["filterModeEnabled"]
                    else "any entity casts a skill (filter mode disabled)"
                ),
            }
    elif native_header_name == "LevelEvent_OnAnyEntityDie":
        any_die_fields = _decode_any_entity_die_fields(payload)
        if any_die_fields:
            detail = {
                "type": native_header_name,
                **any_die_fields,
                "entityOutputRefs": refs("entity"),
                "transport": "local-entity-lifecycle-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    "matching entity in a "
                    f"{len(any_die_fields['entityListFilter'])}-member monster filter "
                    "list dies"
                ),
            }
    elif native_header_name == "LevelEvent_OnSpecificEntityDie":
        entity_fields = _decode_specific_entity_die_fields(payload)
        if entity_fields:
            target = entity_fields["entityFilter"]
            if target.get("useSlotId"):
                receiver = f"entity slot {target.get('slotId')}"
            elif target.get("logicId"):
                receiver = f"entity {target.get('logicId')}"
            elif isinstance(target.get("idRef"), int) and target["idRef"] >= 0:
                receiver = f"entity pointer from local getter {target['idRef']}"
            elif target.get("path"):
                receiver = f"entity pointer {target['path']}"
            else:
                receiver = "selected entity"
            detail = {
                "type": native_header_name,
                **entity_fields,
                "entityOutputRefs": refs("entity"),
                "transport": "local-entity-lifecycle-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": f"{receiver} dies",
            }
    elif native_header_name == "LevelEvent_OnEncounterBattlePartBegin":
        encounter_fields = _decode_encounter_battle_part_begin_fields(payload)
        if encounter_fields:
            detail = {
                "type": native_header_name,
                **encounter_fields,
                "levelScriptVariableOutputRefs": refs("lsvPtrOutput"),
                "transport": "local-encounter-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    "encounter battle part begins for LevelScript variable "
                    f"{encounter_fields['levelScriptVariableFilter']}"
                ),
            }
    elif native_header_name == "LevelEvent_OnScriptedCharPatrolEvent":
        patrol_fields = _decode_scripted_char_patrol_fields(payload)
        if patrol_fields:
            detail = {
                "type": native_header_name,
                **patrol_fields,
                "entityOutputRefs": refs("entityOutput"),
                "patrolIdOutputRefs": refs("patrolIdOutput"),
                "transport": "local-scripted-character-patrol-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    "scripted character patrol event "
                    f"{patrol_fields['scriptedCharEventKeyFilter']}"
                ),
            }
    elif native_header_name == "EntityEvent_OnSavePropertyChanged":
        entity_scope = _decode_entity_event_header_scope(payload)
        entity_scope.pop("_subtypeOffset", None)
        if entity_scope and literal_texts:
            target = entity_scope["targetEntity"]
            target_param = entity_scope["targetEntityParam"]
            if target.get("useSlotId"):
                receiver = f"entity slot {target.get('slotId')}"
            elif target.get("logicId"):
                receiver = f"entity {target.get('logicId')}"
            elif target_param.get("path"):
                receiver = f"entity pointer {target_param.get('path')}"
            else:
                receiver = "selected entity"
            detail = {
                "type": native_header_name,
                **entity_scope,
                "propertyKeyFilter": literal_texts[0],
                "oldValueOutputRefs": refs("oldValue"),
                "valueOutputRefs": refs("value"),
                "transport": "local-entity-property-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"{receiver} saved property {literal_texts[0]} changes"
                ),
            }
    elif native_header_name == "EntityEvent_OnInteractiveStateChanged":
        entity_scope = _decode_entity_event_header_scope(payload)
        entity_scope.pop("_subtypeOffset", None)
        if entity_scope:
            target = entity_scope["targetEntity"]
            target_param = entity_scope["targetEntityParam"]
            if target.get("useSlotId"):
                receiver = f"entity slot {target.get('slotId')}"
            elif target.get("logicId"):
                receiver = f"entity {target.get('logicId')}"
            elif target_param.get("path"):
                receiver = f"entity pointer {target_param.get('path')}"
            else:
                receiver = "selected entity"
            detail = {
                "type": native_header_name,
                **entity_scope,
                "oldValueOutputRefs": refs("oldValue"),
                "valueOutputRefs": refs("value"),
                "transport": "local-entity-property-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": f"{receiver} interactive state changes",
            }
    elif native_header_name == "EntityEvent_OnUIInteract":
        entity_scope = _decode_entity_event_header_scope(payload)
        subtype_offset = entity_scope.pop("_subtypeOffset", None)
        if entity_scope and isinstance(subtype_offset, int):
            # Current fields are ``_optionIndex`` output followed by the
            # optional ``_optionIndexFilter`` Param<int>.  Property output
            # extraction supplies the exact output ref.  Decode the constant
            # filter only when its complete Param tail is present.
            option_filter: int | None = None
            marker = b"\x04"
            param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
            search_start = max(subtype_offset, len(payload) - 17)
            for offset in range(search_start, max(search_start, len(payload) - 16)):
                if (
                    payload[offset : offset + 1] == marker
                    and payload[offset + 5 : offset + 17] == param_tail
                ):
                    option_filter = struct.unpack_from("<i", payload, offset + 1)[0]
                    break
            target_param = entity_scope["targetEntityParam"]
            receiver = (
                f"entity pointer {target_param.get('path')}"
                if target_param.get("path")
                else "selected entity"
            )
            detail = {
                "type": native_header_name,
                **entity_scope,
                "optionIndexOutputRefs": refs("optionIndex"),
                "optionIndexFilter": option_filter,
                "transport": "local-entity-interaction-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"{receiver} UI option {option_filter} selected"
                    if isinstance(option_filter, int)
                    else f"{receiver} UI interaction"
                ),
            }
    elif native_header_name == "EntityEvent_OnLeaderEnterTrigger":
        entity_scope = _decode_entity_event_header_scope(payload)
        entity_scope.pop("_subtypeOffset", None)
        if entity_scope:
            target = entity_scope["targetEntity"]
            detail = {
                "type": native_header_name,
                **entity_scope,
                "transport": "local-authored-trigger-volume-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"leader enters authored entity slot {target.get('slotId')}"
                    if target.get("useSlotId")
                    else "leader enters selected entity trigger"
                ),
            }
    elif native_header_name in {
        "ScriptEvent_OnLeaderEnterTriggerVolume",
        "ScriptEvent_OnLeaderLeaveTriggerVolume",
    }:
        trigger_fields = _decode_leader_trigger_volume_fields(payload)
        if trigger_fields:
            event_phrase = (
                "leader enters trigger slot"
                if native_header_name == "ScriptEvent_OnLeaderEnterTriggerVolume"
                else "leader leaves trigger slot"
            )
            detail = {
                "type": native_header_name,
                **trigger_fields,
                "triggerSlotIdOutputRefs": refs("triggerSlotIdOutput"),
                "transport": "local-authored-trigger-volume-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"{event_phrase} {trigger_fields['triggerSlotIdFilter']}"
                ),
            }
    if not detail:
        return {}
    detail["payloadSchemaStatus"] = "exact_current_build_memorypack_fields"
    detail["payloadSchemaMappingId"] = LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID
    return _drop_empty(detail)


def _extract_tail_local_refs(payload: bytes) -> list[int]:
    if len(payload) < 8:
        return []
    refs: list[int] = []
    for offset in (len(payload) - 8, len(payload) - 4):
        value = struct.unpack_from("<i", payload, offset)[0]
        if 0 <= value <= 0x1000 and value not in refs:
            refs.append(value)
    return refs


def _decode_split_action_refs(payload: bytes) -> list[int]:
    """Decode the exact current-build ``Split.actions`` local-id list.

    The installed ``SplitForMemoryPack`` formatter serializes one list.  Its
    payload is therefore a u32 count followed by that many signed local action
    ids.  Requiring the payload length to match exactly prevents arbitrary
    scalar tails from being promoted into control-flow edges.
    """
    if len(payload) < 4:
        return []
    count = struct.unpack_from("<I", payload, 0)[0]
    if count > 64 or len(payload) != 4 + count * 4:
        return []
    refs = [
        struct.unpack_from("<i", payload, 4 + index * 4)[0]
        for index in range(count)
    ]
    if any(ref < 0 or ref > 0x10000 for ref in refs):
        return []
    return refs


def _decode_branch_sequence_action_refs(payload: bytes) -> list[int]:
    """Decode the exact current-build ``Branch._idList`` action sequence.

    The installed formatter serializes ``_idList`` as a u32 count followed by
    signed local action ids. Original ``GameAssembly.dll`` method
    ``Beyond.Gameplay.Actions.Branch.Execute`` schedules the entry at
    ``m_index``, reserves the Branch action between non-final entries,
    increments the index, and resets it after the final entry. The list is
    therefore ordered continuation, not mutually exclusive branch arms.
    """
    refs = _decode_split_action_refs(payload)
    if any(ref <= 0 for ref in refs):
        return []
    return refs


def _decode_if_else_action_refs(payload: bytes) -> dict[str, Any]:
    """Decode exact ``IfElseAction`` true/false action ids from its tail.

    Current native setter order places the condition first, followed by the
    false and true action ids.  Those final two signed ints are accepted only
    when both are plausible same-file local ids; resolution still requires a
    unique actionList row at the consumer.
    """
    if len(payload) < 8:
        return {}
    false_id, true_id = struct.unpack_from("<ii", payload, len(payload) - 8)
    if any(ref < 0 or ref > 0x10000 for ref in (true_id, false_id)):
        return {}
    out = {
        "trueActionLocalId": true_id,
        "falseActionLocalId": false_id,
    }
    condition = payload[:-8]
    if (
        len(condition) == 14
        and condition[:2] == b"\x04\x01"
        and condition[6:] == b"\xff" * 8
    ):
        getter_id = struct.unpack_from("<i", condition, 2)[0]
        if 0 <= getter_id <= 0x10000:
            out["conditionGetterLocalId"] = getter_id
    else:
        inline_condition = _decode_bool_param(condition, 0)
        if inline_condition is not None and inline_condition[1] == len(condition):
            out["conditionParam"] = inline_condition[0]
    return out


def _decode_while_action(payload: bytes) -> dict[str, Any]:
    """Decode exact ``WhileAction`` condition and loop-body action id.

    The installed ``WhileActionForMemoryPack`` exposes generated setters for
    ``_condition`` followed by ``_doID``. The first field is one authored
    ``Param<bool>`` and the final field is the signed local action id.
    """
    condition = _decode_bool_param(payload, 0)
    condition_action_local_id: int | None = None
    if condition is not None:
        condition_detail, cursor = condition
    elif (
        len(payload) >= 14
        and payload[0] == 0x04
        and payload[1] in (0, 1)
        and payload[6:14] == b"\xff" * 8
    ):
        # Action-output parameters use the producing action id followed by
        # source/path sentinels, as in `$27@result` conditions.
        condition_action_local_id = struct.unpack_from("<i", payload, 2)[0]
        if condition_action_local_id <= 0 or condition_action_local_id > 0x10000:
            return {}
        condition_detail = {
            "value": bool(payload[1]),
            "idRef": condition_action_local_id,
            "paramSource": -1,
            "path": None,
        }
        cursor = 14
    else:
        return {}
    if cursor + 4 != len(payload):
        return {}
    do_action_local_id = struct.unpack_from("<i", payload, cursor)[0]
    if do_action_local_id <= 0 or do_action_local_id > 0x10000:
        return {}
    out = {
        "whileConditionParam": condition_detail,
        "whileDoActionLocalId": do_action_local_id,
    }
    if condition_action_local_id is not None:
        out["whileConditionActionLocalId"] = condition_action_local_id
    return out


def _decode_switch_int_action(
    payload: bytes,
    *,
    field_prefix: str = "switch",
    action_name: str = "SwitchInt",
    branch_role: str | None = None,
) -> dict[str, Any]:
    """Decode a serialized integer switch family using its shared shape.

    The current ``SwitchInt`` and ``SwitchIntLarger`` formatters both read, in
    setter order, ``_caseIDList``, ``_caseValueList``, ``_defaultID``, then a
    typed ``PureGetter<int> _value`` object.  Both lists use a u32 count
    followed by signed i32 values.  Keeping the parser parameterized by the
    family prefix prevents per-object recovery rules while retaining explicit
    family names in the emitted evidence.
    """
    if branch_role is None:
        family_token = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", action_name)
        family_token = family_token.replace("-Action", "").lower()
        branch_role = f"typed-{family_token}-actions"
    cursor = 0

    def read_i32_list() -> list[int] | None:
        nonlocal cursor
        if cursor + 4 > len(payload):
            return None
        count = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        if count > 64 or cursor + count * 4 > len(payload):
            return None
        values = [
            struct.unpack_from("<i", payload, cursor + index * 4)[0]
            for index in range(count)
        ]
        cursor += count * 4
        return values

    case_ids = read_i32_list()
    case_values = read_i32_list()
    if case_ids is None or case_values is None or len(case_ids) != len(case_values):
        return {}
    if cursor + 4 > len(payload):
        return {}
    default_id = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    value_getter = payload[cursor:]

    # The installed formatter writes a polymorphic PureGetter<int> object
    # here.  Every current integer-switch record has the object-present tag 0x04
    # and at least the 14-byte compact object shell.  Requiring it consumes the
    # complete record tail and prevents a matching scalar prefix from being
    # promoted into control flow.
    if len(value_getter) < 14 or value_getter[0] != 0x04:
        return {}
    if any(ref < -1 or ref > 0x10000 for ref in [*case_ids, default_id]):
        return {}

    branch_refs = list(dict.fromkeys(
        ref for ref in [*case_ids, default_id] if ref > 0
    ))
    case_ids_field = f"{field_prefix}CaseActionLocalIds"
    case_values_field = f"{field_prefix}CaseValues"
    cases_field = f"{field_prefix}Cases"
    default_field = f"{field_prefix}DefaultActionLocalId"
    value_length_field = f"{field_prefix}ValueGetterPayloadLength"
    value_prefix_field = f"{field_prefix}ValueGetterHexPrefix"
    out: dict[str, Any] = {
        case_ids_field: case_ids,
        case_values_field: case_values,
        cases_field: [
            {"value": value, "actionLocalId": action_id}
            for value, action_id in zip(case_values, case_ids)
        ],
        default_field: default_id,
        value_length_field: len(value_getter),
        value_prefix_field: value_getter[:32].hex(" "),
        "branchLocalRefs": branch_refs,
        "branchRole": branch_role,
    }
    # Common property-output/local-getter form used by the e3m4 radio chain:
    # object-present + zero subtype header + local getter id + null sentinel.
    if (
        len(value_getter) == 17
        and value_getter[:5] == b"\x04\x00\x00\x00\x00"
        and value_getter[9:] == b"\xff" * 8
    ):
        getter_id = struct.unpack_from("<i", value_getter, 5)[0]
        if 0 <= getter_id <= 0x10000:
            out[f"{field_prefix}ValueGetterLocalId"] = getter_id
    if f"{field_prefix}ValueGetterLocalId" not in out:
        inline_value = _decode_i32_param(value_getter, 0)
        if inline_value is not None and inline_value[1] == len(value_getter):
            out[f"{field_prefix}ValueParam"] = inline_value[0]
    return out


def _decode_switch_string_action(payload: bytes) -> dict[str, Any]:
    """Decode the current-build ``SwitchString`` branch table exactly."""
    cursor = 0

    def read_i32_list() -> list[int] | None:
        nonlocal cursor
        if cursor + 4 > len(payload):
            return None
        count = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        if count > 64 or cursor + count * 4 > len(payload):
            return None
        values = [
            struct.unpack_from("<i", payload, cursor + index * 4)[0]
            for index in range(count)
        ]
        cursor += count * 4
        return values

    def read_string_list() -> list[str | None] | None:
        nonlocal cursor
        if cursor + 4 > len(payload):
            return None
        count = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        if count > 64:
            return None
        values: list[str | None] = []
        for _ in range(count):
            if cursor + 4 > len(payload):
                return None
            size = struct.unpack_from("<i", payload, cursor)[0]
            cursor += 4
            if size == -1:
                values.append(None)
                continue
            if size < 0 or size > 1024 or cursor + size > len(payload):
                return None
            try:
                value = payload[cursor : cursor + size].decode("utf-8")
            except UnicodeDecodeError:
                return None
            if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
                return None
            values.append(value)
            cursor += size
        return values

    case_ids = read_i32_list()
    case_values = read_string_list()
    if case_ids is None or case_values is None or len(case_ids) != len(case_values):
        return {}
    if cursor + 4 > len(payload):
        return {}
    default_id = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if any(ref < -1 or ref > 0x10000 for ref in [*case_ids, default_id]):
        return {}

    value_param = _decode_string_param(payload, cursor)
    value_getter_local_id: int | None = None
    if value_param is not None and value_param[1] == len(payload):
        value_detail = value_param[0]
    elif (
        cursor + 17 == len(payload)
        and payload[cursor] == 0x04
        and payload[cursor + 1 : cursor + 5] == b"\xff" * 4
        and payload[cursor + 9 : cursor + 17] == b"\xff" * 8
    ):
        value_getter_local_id = struct.unpack_from("<i", payload, cursor + 5)[0]
        if value_getter_local_id <= 0 or value_getter_local_id > 0x10000:
            return {}
        value_detail = {
            "value": None,
            "idRef": value_getter_local_id,
            "paramSource": -1,
            "path": None,
        }
    else:
        return {}

    branch_refs = list(dict.fromkeys(
        ref for ref in [*case_ids, default_id] if ref > 0
    ))
    out: dict[str, Any] = {
        "switchStringCaseActionLocalIds": case_ids,
        "switchStringCaseValues": case_values,
        "switchStringCases": [
            {"value": value, "actionLocalId": action_id}
            for value, action_id in zip(case_values, case_ids)
        ],
        "switchStringDefaultActionLocalId": default_id,
        "switchStringValueParam": value_detail,
        "branchLocalRefs": branch_refs,
        "branchRole": "typed-switch-string-actions",
        "payloadShape": "switch-string-four-fields-exact-eof",
        "consumedBytes": len(payload),
    }
    if value_getter_local_id is not None:
        out["switchStringValueGetterLocalId"] = value_getter_local_id
    return out


def _decode_wait_for_seconds_in_trigger_volume_action(
    payload: bytes,
) -> dict[str, Any]:
    """Decode the inherited success/fail targets and trigger receiver exactly."""
    if len(payload) < 10 or payload[0] != 0xFF:
        return {}
    fail_id = struct.unpack_from("<i", payload, 1)[0]
    seconds = _decode_float_param(payload, 5)
    if seconds is None or seconds[1] + 4 > len(payload):
        return {}
    success_id = struct.unpack_from("<i", payload, seconds[1])[0]
    cursor = seconds[1] + 4
    script_ptr = _decode_levelscript_ptr_param(payload, cursor)
    if script_ptr is None:
        return {}
    trigger_slot = _decode_i32_param(payload, script_ptr[1])
    if trigger_slot is None or trigger_slot[1] != len(payload):
        return {}
    if any(ref < -1 or ref > 0x10000 for ref in (fail_id, success_id)):
        return {}
    return {
        "waitAreaEntity": None,
        "waitFailActionLocalId": fail_id,
        "waitSeconds": seconds[0],
        "waitSuccessActionLocalId": success_id,
        "waitScriptPtr": script_ptr[0],
        "waitTriggerSlotId": trigger_slot[0],
        "branchLocalRefs": list(dict.fromkeys(
            ref for ref in (fail_id, success_id) if ref > 0
        )),
        "branchRole": "typed-wait-trigger-volume-outcomes",
        "payloadShape": "wait-trigger-volume-five-inherited-fields-exact-eof",
        "consumedBytes": len(payload),
    }


def _decode_play3d_radio_action(payload: bytes) -> dict[str, Any]:
    """Decode the exact current-build ``Play3DRadio`` field sequence.

    The generated native deserializer sets the 12 subtype fields in the order
    replayed below.  This decoder intentionally requires the action payload to
    end at the twelfth field; a minority of records have additional serialized
    list framing after the action and remain unsupported until that outer
    framing is independently decoded.
    """
    sentinel = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    cursor = 0
    values: dict[str, Any] = {}
    offsets: dict[str, str] = {}
    encodings: dict[str, str] = {}

    class DecodeError(ValueError):
        pass

    def expect_tag(name: str) -> None:
        nonlocal cursor
        if cursor >= len(payload) or payload[cursor] != 0x04:
            raise DecodeError(f"{name}: missing object-present tag")
        offsets[name] = _offset_hex(cursor)
        cursor += 1

    def expect_sentinel(name: str) -> None:
        nonlocal cursor
        if payload[cursor : cursor + 12] != sentinel:
            raise DecodeError(f"{name}: invalid Param tail")
        cursor += 12

    def scalar(name: str, fmt: str, size: int) -> None:
        nonlocal cursor
        expect_tag(name)
        if cursor + size > len(payload):
            raise DecodeError(f"{name}: truncated scalar")
        values[name] = struct.unpack_from(fmt, payload, cursor)[0]
        cursor += size
        expect_sentinel(name)

    def boolean(name: str) -> None:
        nonlocal cursor
        expect_tag(name)
        if cursor >= len(payload) or payload[cursor] not in (0, 1):
            raise DecodeError(f"{name}: invalid bool")
        values[name] = bool(payload[cursor])
        cursor += 1
        expect_sentinel(name)

    def string(name: str, *, nullable: bool = False) -> None:
        nonlocal cursor
        offsets[name] = _offset_hex(cursor)
        if nullable and payload[cursor : cursor + 1] == b"\xff":
            values[name] = ""
            encodings[name] = "bare-null"
            cursor += 1
            return
        expect_tag(name)
        if cursor + 4 > len(payload):
            raise DecodeError(f"{name}: truncated length")
        size = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        if nullable and size == 0xFFFFFFFF:
            values[name] = ""
            encodings[name] = "tagged-null"
            expect_sentinel(name)
            return
        if size > 512 or cursor + size > len(payload):
            raise DecodeError(f"{name}: invalid length")
        try:
            values[name] = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DecodeError(f"{name}: invalid UTF-8") from exc
        cursor += size
        encodings[name] = "tagged-string"
        expect_sentinel(name)

    try:
        scalar("attenuationType", "<I", 4)
        boolean("enableAdvancedOptions")
        expect_tag("entityPtr")
        entity_raw = payload[cursor : cursor + 26]
        if len(entity_raw) != 26:
            raise DecodeError("entityPtr: truncated")
        if entity_raw[14:26] == sentinel:
            encodings["entityPtr"] = "default14+sentinel12"
        elif entity_raw[18:26] == b"\xff" * 8:
            encodings["entityPtr"] = "bound18+null8"
        else:
            raise DecodeError("entityPtr: unsupported shape")
        cursor += 26
        boolean("fromBegin")
        scalar("index", "<i", 4)
        boolean("noFlushAfterLoading")
        string("npcProxyId", nullable=True)
        boolean("onlyOnce")
        string("radioId")
        scalar("reverbOffset", "<f", 4)
        boolean("useNpcProxy")
        scalar("voOffset", "<f", 4)
    except (DecodeError, struct.error):
        return {}
    if cursor != len(payload):
        return {}
    return {
        "payloadShape": "play3d-radio-native-12-field-exact-eof",
        "radioId": str(values.get("radioId") or ""),
        "npcProxyId": str(values.get("npcProxyId") or ""),
        "useNpcProxy": bool(values.get("useNpcProxy")),
        "fields": values,
        "fieldOffsets": offsets,
        "fieldEncodings": encodings,
        "consumedBytes": cursor,
    }


def _decode_npc_patrol_start_action(payload: bytes) -> dict[str, Any]:
    """Decode the current four-field ``NpcPatrolStart`` action exactly."""
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    cursor = 0

    def read_bool_param() -> bool | None:
        nonlocal cursor
        if (
            cursor + 14 > len(payload)
            or payload[cursor] != 0x04
            or payload[cursor + 1] not in (0, 1)
            or payload[cursor + 2 : cursor + 14] != param_tail
        ):
            return None
        value = bool(payload[cursor + 1])
        cursor += 14
        return value

    def read_i32_param() -> int | None:
        nonlocal cursor
        if (
            cursor + 17 > len(payload)
            or payload[cursor] != 0x04
            or payload[cursor + 5 : cursor + 17] != param_tail
        ):
            return None
        value = struct.unpack_from("<i", payload, cursor + 1)[0]
        cursor += 17
        return value

    start_from_beginning = read_bool_param()
    patrol_id = read_i32_param()
    force_idle = read_bool_param()
    if (
        start_from_beginning is None
        or patrol_id is None
        or force_idle is None
        or patrol_id <= 0
        or cursor + 27 > len(payload)
        or payload[cursor : cursor + 2] != b"\x04\x03"
    ):
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    param_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    cursor += 27
    if (
        use_slot_id not in (0, 1)
        or path_size <= 0
        or path_size > 256
        or cursor + path_size != len(payload)
    ):
        return {}
    try:
        target_path = payload[cursor : cursor + path_size].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if not target_path or any(ord(char) < 0x20 for char in target_path):
        return {}
    return {
        "action": "NpcPatrolStart",
        "startFromBeginning": start_from_beginning,
        "patrolId": patrol_id,
        "forceIdle": force_idle,
        "targetNpc": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
            "idRef": id_ref,
            "paramSource": param_source,
            "path": target_path,
        },
        "payloadShape": "npc-patrol-start-four-field-exact-eof",
        "consumedBytes": len(payload),
    }


def _decode_exit_level_custom_performance_action(
    payload: bytes,
) -> dict[str, Any]:
    """Decode the current action's sole authored ``Param<uint>`` handle."""
    if (
        len(payload) != 17
        or payload[0] != 0x04
        or payload[5:17] != b"\xff" * 12
    ):
        return {}
    return {
        "payloadShape": "uint-handle-with-unset-param-tail-exact-eof",
        "handle": {
            "serializedConstValue": struct.unpack_from("<I", payload, 1)[0],
            "idRef": -1,
            "paramSource": -1,
            "path": None,
        },
        "consumedBytes": len(payload),
    }


def _decode_toggle_clear_screen_but_radio_action(
    payload: bytes,
) -> dict[str, Any]:
    """Decode the current action's sole authored ``Param<bool> _isShow``."""
    is_show = _decode_bool_param(payload, 0)
    if is_show is None or is_show[1] != len(payload):
        return {}
    return {
        "payloadShape": "is-show-bool-param-exact-eof",
        "isShow": is_show[0],
        "consumedBytes": is_show[1],
    }


def _decode_main_char_move_to_action(payload: bytes) -> dict[str, Any]:
    """Decode ``_endPos`` and ``_groundedMoveGait`` for the current action."""
    if len(payload) < 13 or payload[0] != 0x04:
        return {}
    end_pos = {
        "x": _round_float(struct.unpack_from("<f", payload, 1)[0]),
        "y": _round_float(struct.unpack_from("<f", payload, 5)[0]),
        "z": _round_float(struct.unpack_from("<f", payload, 9)[0]),
    }
    end_pos_tail = _decode_param_tail(payload, 13)
    if end_pos_tail is None:
        return {}
    end_pos_detail, cursor = end_pos_tail
    gait = _decode_i32_param(payload, cursor)
    if gait is None or gait[1] != len(payload):
        return {}
    return {
        "payloadShape": "end-pos-vector3-and-grounded-gait-exact-eof",
        "endPos": {**end_pos, **end_pos_detail},
        "groundedMoveGait": gait[0],
        "consumedBytes": gait[1],
    }


def _decode_call_server_action(payload: bytes) -> dict[str, Any]:
    """Decode the six generated fields in the current ``CallServer`` prefix."""
    if len(payload) < 4:
        return {}

    # MemoryPack writes ``_callClientOutputUIDs`` first.  Most current rows
    # serialize a null list (-1), which made the former fixed-prefix decoder
    # look complete.  Non-null lists are the server-callback header UIDs and
    # must be consumed before the remaining five fields.
    output_count = struct.unpack_from("<i", payload, 0)[0]
    if output_count < -1 or output_count > 4096:
        return {}
    cursor = 4
    call_client_output_uids: list[str] | None = None
    if output_count >= 0:
        call_client_output_uids = []
        for _index in range(output_count):
            if cursor + 4 > len(payload):
                return {}
            value_size = struct.unpack_from("<i", payload, cursor)[0]
            cursor += 4
            if value_size < 0 or cursor + value_size > len(payload):
                return {}
            try:
                value = payload[cursor : cursor + value_size].decode("utf-8")
            except UnicodeDecodeError:
                return {}
            cursor += value_size
            call_client_output_uids.append(value)

    if cursor + 6 > len(payload) or payload[cursor : cursor + 2] != b"\x04\x01":
        return {}
    event_args_size = struct.unpack_from("<i", payload, cursor + 2)[0]
    cursor += 6
    if event_args_size <= 0 or cursor + event_args_size > len(payload):
        return {}
    try:
        event_args_path = payload[cursor : cursor + event_args_size].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    event_args_tail = _decode_param_tail(payload, cursor + event_args_size)
    if event_args_tail is None:
        return {}
    event_args_detail, cursor = event_args_tail
    event_name = _decode_constant_string_param(payload, cursor)
    if event_name is None:
        return {}
    event_name_value, cursor = event_name
    if cursor + 3 > len(payload) or any(
        value not in (0, 1)
        for value in payload[cursor : cursor + 3]
    ):
        return {}
    use_custom_event, wait_for_callback, with_event_args = (
        bool(value) for value in payload[cursor:cursor + 3]
    )
    cursor += 3
    return {
        "payloadShape": "six-call-server-fields-exact-prefix",
        "callClientOutputUIDs": call_client_output_uids,
        "eventArgsPtr": {
            "pathValue": event_args_path,
            **event_args_detail,
        },
        "eventName": event_name_value,
        "useCustomEvent": use_custom_event,
        "waitForCallback": wait_for_callback,
        "withEventArgs": with_event_args,
        "consumedBytes": cursor,
        "trailingBytes": len(payload) - cursor,
    }


CALLSERVER_SERIALIZED_CONTRACT_FIELDS = (
    "payloadShape",
    "callClientOutputUIDs",
    "eventArgsPtr",
    "eventName",
    "eventNameIdentity",
    "callbackCorrelationLabel",
    "useCustomEvent",
    "waitForCallback",
    "withEventArgs",
    "consumedBytes",
    "trailingBytes",
)


def compact_callserver_serialized_contract(
    call_server: dict[str, Any],
) -> dict[str, Any]:
    """Project decoded bytes without derived graph/evidence annotations."""
    if not isinstance(call_server, dict):
        return {}
    return {
        key: call_server[key]
        for key in CALLSERVER_SERIALIZED_CONTRACT_FIELDS
        if key in call_server
    }


def _decode_entity_compare_getter(payload: bytes, property_outputs: list[dict]) -> dict[str, Any]:
    """Decode the exact current-build EntityCompare ScriptEntityPtr operand.

    PureGetter tag 0x28/member-count 10 compares one property-output operand
    with a typed ScriptEntityPtr constant. The latter is encoded as tag 04/03,
    logic id u64, slot id u32, and a one-byte use-slot flag at the guarded tail
    offsets below. Other operand variants deliberately remain unsupported.
    """
    if (
        len(payload) != 84
        or payload[0x39:0x3B] != b"\x04\x03"
        or payload[0x47] not in (0, 1)
        or not property_outputs
    ):
        return {}
    return {
        "type": "EntityCompare",
        "propertyOutputRefs": property_outputs,
        "scriptEntity": {
            "logicId": struct.unpack_from("<Q", payload, 0x3B)[0],
            "slotId": struct.unpack_from("<I", payload, 0x43)[0],
            "useSlotId": bool(payload[0x47]),
        },
        "payloadShape": "property-output-vs-script-entity-ptr",
    }


def _read_compact_string(payload: bytes, offset: int) -> tuple[str | None, int | None]:
    if offset < 0 or offset + 4 > len(payload):
        return None, None
    size = struct.unpack_from("<I", payload, offset)[0]
    if size > 120 or offset + 4 + size > len(payload):
        return None, None
    raw = payload[offset + 4 : offset + 4 + size]
    if not _is_printable_ascii(raw):
        return None, None
    return raw.decode("ascii", errors="replace"), offset + 4 + size


def _append_small_i32_tail(payload: bytes, cursor: int, out: dict[str, Any]) -> None:
    if cursor < 0 or cursor >= len(payload):
        return
    remaining = len(payload) - cursor
    if remaining != 4:
        if 0 < remaining <= 16:
            out["tailBytes"] = payload[cursor:].hex(" ")
        return
    value = struct.unpack_from("<i", payload, cursor)[0]
    out["tailLocalRef"] = value
    if 0 <= value <= 0x1000:
        out["gateLocalRefs"] = [value]


def _decode_post_flag_and_tail(payload: bytes, cursor: int, out: dict[str, Any]) -> None:
    if cursor + 14 > len(payload) or payload[cursor] != 0x04:
        _append_small_i32_tail(payload, cursor, out)
        return
    out["postFlag"] = payload[cursor + 1]
    out["postFlagOffset"] = _offset_hex(cursor + 1)
    out["postSentinel"] = payload[cursor + 2 : cursor + 14] == COMPACT_NULL_SENTINEL
    cursor += 14
    _append_small_i32_tail(payload, cursor, out)


def _decode_compact_property_gate(payload: bytes) -> dict[str, Any]:
    """Decode the compact 0x0a03 condition/gate payload shape.

    The runtime class is still unnamed. The stable exported shape is a
    sentinel-headed compact condition with one or two operand slots, an
    authored property/key string in many rows, a post-key 0/1 flag, and
    sometimes a trailing small int that resolves to a local action id.
    """
    if len(payload) < 15:
        return {}
    out: dict[str, Any] = {
        "payloadShape": "compact-condition-gate",
        "headByte": payload[0],
        "headSentinel": payload[1:13] == COMPACT_NULL_SENTINEL,
        "firstTag": payload[13],
        "firstFlag": payload[14],
    }
    if not out["headSentinel"] or payload[13] != 0x04:
        return _drop_empty(out)

    # Common key form:
    #   00 <sentinel> 04 00 ff ff ff ff <typeCode> <len> <key>
    if len(payload) >= 27 and payload[15:19] == b"\xff\xff\xff\xff":
        type_code = struct.unpack_from("<I", payload, 19)[0]
        key_text, cursor = _read_compact_string(payload, 23)
        if key_text is not None and cursor is not None:
            out.update(
                {
                    "schema": "single-key",
                    "typeCode": type_code,
                    "propertyKey": key_text,
                    "propertyKeyOffset": _offset_hex(27),
                }
            )
            _decode_post_flag_and_tail(payload, cursor, out)
            return _drop_empty(out)

    # Two-slot key form:
    #   00 <sentinel> 04 01 <sentinel> 04 00 ff ff ff ff <typeCode> <len> <key>
    if len(payload) >= 41 and payload[15:27] == COMPACT_NULL_SENTINEL and payload[27] == 0x04:
        type_code = struct.unpack_from("<I", payload, 33)[0]
        key_text, cursor = _read_compact_string(payload, 37)
        if key_text is not None and cursor is not None:
            out.update(
                {
                    "schema": "two-slot-key",
                    "secondTag": payload[27],
                    "secondFlag": payload[28],
                    "typeCode": type_code,
                    "propertyKey": key_text,
                    "propertyKeyOffset": _offset_hex(41),
                }
            )
            _decode_post_flag_and_tail(payload, cursor, out)
            return _drop_empty(out)

    # No-key local-ref form. These rows compare a local/scalar slot and do not
    # carry a property name in the action payload.
    if len(payload) >= 41 and payload[19:27] == b"\xff\xff\xff\xff\xff\xff\xff\xff" and payload[27] == 0x04:
        out.update(
            {
                "schema": "local-ref",
                "firstLocalRef": struct.unpack_from("<i", payload, 15)[0],
                "secondTag": payload[27],
                "secondFlag": payload[28],
                "secondSentinel": payload[29:41] == COMPACT_NULL_SENTINEL,
            }
        )
        _append_small_i32_tail(payload, 41, out)
        return _drop_empty(out)

    return _drop_empty(out)


def _decode_manual_levelscript_control(payload: bytes, role: str) -> dict[str, Any]:
    """Decode stable diagnostics for ManualStart/ManualEnd action payloads."""
    if len(payload) < 46:
        return {}
    script_id_candidate: int | None = None
    if payload[17] == 0x04 and len(payload) >= 26:
        raw_script_id = struct.unpack_from("<Q", payload, 18)[0]
        if _is_plausible_levelscript_id(raw_script_id):
            script_id_candidate = raw_script_id
    marker_values: list[int] = []
    for offset in range(0, len(payload) - 3):
        value = struct.unpack_from("<I", payload, offset)[0]
        if 900 <= value <= 1100 and value not in marker_values:
            marker_values.append(value)
    canonical_prefix = (
        payload[0] == 0x04
        and payload[1:9] == b"\xff" * 8
        and payload[13:17] == b"\xff" * 4
        and payload[17] == 0x04
        and payload[18:34] == b"\x00" * 16
        and payload[34:38] == b"\xff" * 4
        and payload[42:46] == b"\xff" * 4
    )
    out = {
        "action": "ManualStartLevelScript" if role == "manual-start" else "ManualEndLevelScript",
        "role": role,
        "payloadShape": "manual-levelscript-default-operands" if canonical_prefix else "manual-levelscript-unknown",
        "memberCountByte": payload[0],
        "markerU32s": marker_values,
        "hasLiteralLevelId": False,
        "hasLiteralScriptId": script_id_candidate is not None,
        "scriptIdCandidate": str(script_id_candidate) if script_id_candidate is not None else "",
        "constantTargetStatus": "script-id-only" if script_id_candidate is not None else "absent",
    }
    if canonical_prefix:
        # Both operands are serialized Param<T> values.  Current MemoryPack
        # metadata and generated Deserialize bodies establish the member order
        # as constValue, idRef, paramSource, path.  Keep the numeric sources
        # here; their build-specific enum names are supplied by the validated
        # original-binary contract rather than hardcoded into this parser.
        out["parameterSources"] = {
            "levelId": struct.unpack_from("<i", payload, 9)[0],
            "scriptId": struct.unpack_from("<i", payload, 38)[0],
        }
    if script_id_candidate is not None:
        out["payloadShape"] = "manual-levelscript-script-id-operand"
    if len(payload) > 46 and canonical_prefix:
        out["trailingBytesAfterCanonicalPrefix"] = payload[46:].hex(" ")
    return _drop_empty(out)


def _decode_action_header_prefix(payload: bytes) -> dict[str, Any]:
    """Decode the compact common ActionHeader prefix.

    GameAssembly body recovery shows the MemoryPack wrapper setters store
    ActionHeader fields at runtime offsets include nextID, priority,
    triggerActiveDuring, filterMode, filterLevel, filterMask, and validate.

    In the exported LevelScript blobs observed so far, high ActionHeader rows
    carry a compact 17-byte prefix. The useful playback edge is `_nextID`,
    serialized as a u32 at payload offset +5. The fixed record trailer also
    has a `nextId`-looking integer, but for headerList rows that value often
    points nowhere useful and is not the event-to-action edge.
    """
    if len(payload) < 17:
        return {}
    filter_mask = struct.unpack_from("<i", payload, 0)[0]
    filter_mode = payload[4]
    next_id = struct.unpack_from("<i", payload, 5)[0]
    priority = struct.unpack_from("<i", payload, 9)[0]
    trigger_active_during = struct.unpack_from("<i", payload, 13)[0]
    if filter_mode > 8:
        return {}
    if not (-1 <= next_id <= 0x10000):
        return {}
    if not (-1000 <= filter_mask <= 100000):
        return {}
    if not (-1000 <= priority <= 100000):
        return {}
    if not (-1000 <= trigger_active_during <= 100000):
        return {}
    validate_param: dict[str, Any] = {}
    if len(payload) >= 31 and payload[17] == 0x04 and payload[18] in (0, 1):
        id_ref = struct.unpack_from("<i", payload, 19)[0]
        param_source = struct.unpack_from("<i", payload, 23)[0]
        path_size = struct.unpack_from("<i", payload, 27)[0]
        if path_size == -1 and (
            (id_ref == -1 and param_source == 0)
            or (0 < id_ref <= 0x10000 and param_source == -1)
        ):
            validate_param = {
                "value": bool(payload[18]),
                "idRef": id_ref,
                "paramSource": param_source,
                "path": None,
                "payloadOffset": "0x11",
                "payloadShape": (
                    "action-header-validate-constant"
                    if id_ref == -1
                    else "action-header-validate-local-getter"
                ),
            }
    detail = {
            "payloadShape": "action-header-prefix",
            "filterMask": filter_mask,
            "filterMode": filter_mode,
            "nextId": next_id,
            "priority": priority,
            "triggerActiveDuring": trigger_active_during,
            "nextIdOffset": "0x5",
    }
    if validate_param:
        detail["validateParam"] = validate_param
        if validate_param["payloadShape"] == "action-header-validate-local-getter":
            detail["validateGetterLocalId"] = validate_param["idRef"]
    return _drop_empty(detail)


LEVELSCRIPT_EXACT_GETTER_FIELDS = (
    "booleanCompare",
    "boolGetterAnd",
    "boolGetterInvert",
    "boolGetterMultiAnd",
    "boolGetterOr",
    "checkLevelScriptStage",
    "checkMissionOrQuestIsComplete",
    "compareMissionState",
    "getConditionResult",
    "floatNewCompare",
    "getLevelScriptPropertyGenericBool",
    "getLevelScriptStage",
    "getMissionState",
    "getLsmIsCompleted",
    "getterBool",
    "getterInt",
    "getterString",
    "intCompare",
    "intEqual",
    "intRandom",
    "interactiveCheckState",
    "isEndminGender",
)


def _predicate_local_getter_refs(
    value: Any,
    path: str = "",
) -> list[dict[str, Any]]:
    """Collect explicitly typed local-getter references from exact fields."""
    refs: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if (
                isinstance(child, int)
                and (
                    key == "getterLocalId"
                    or key.endswith("GetterLocalId")
                )
            ):
                shorthand_base = key[: -len("GetterLocalId")]
                canonical_operand = value.get(shorthand_base)
                if (
                    shorthand_base
                    and isinstance(canonical_operand, dict)
                    and canonical_operand.get("getterLocalId") == child
                ):
                    continue
                refs.append({"path": child_path, "getterLocalId": child})
            else:
                refs.extend(_predicate_local_getter_refs(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            refs.extend(_predicate_local_getter_refs(child, child_path))
    return refs


def decode_levelscript_action_header_validation(
    data: bytes,
    header_local_id: int,
) -> dict[str, Any]:
    """Resolve one ActionHeader's exact serialized playback predicate.

    The resolver is deliberately identity-agnostic: it follows the header's
    ``_validate`` local getter reference through the decoded ActionMap and
    returns only an already exact getter family. Repeated local ids follow the
    installed ActionMapRuntime rule (the final serialized row owns the indexed
    runtime slot); unknown getter unions still fail closed.
    """
    if not data or not isinstance(header_local_id, int):
        return {}
    tagged_strings = _extract_levelscript_tagged_ascii_strings(data)
    plain_strings = _extract_levelscript_plain_ascii_strings(
        data,
        tagged_offsets={int(hit.get("offset") or 0) for hit in tagged_strings},
    )
    records = extract_levelscript_uid_records(data, tagged_strings, plain_strings)
    _action_map, memberships = levelscript_action_map_membership(data, records)
    matching_headers = [
        (index, record)
        for index, record in enumerate(records)
        if record.get("localId") == header_local_id
        and str(memberships.get(_record_start(record)) or "").startswith("headerList")
    ]
    if not matching_headers:
        return {}
    header_index, header_record = matching_headers[-1]
    header_next_start = (
        _record_start(records[header_index + 1])
        if header_index + 1 < len(records)
        else len(data)
    )
    header_detail = decode_levelscript_record_payload(
        data,
        header_record,
        next_start=header_next_start,
        action_map_role=memberships.get(_record_start(header_record)),
    )
    action_header = header_detail.get("actionHeader")
    if not isinstance(action_header, dict):
        return {}
    validate_param = action_header.get("validateParam")
    if not isinstance(validate_param, dict):
        return {}
    getter_local_id = action_header.get("validateGetterLocalId")
    if not isinstance(getter_local_id, int):
        if validate_param.get("payloadShape") != "action-header-validate-constant":
            return {}
        return {
            "status": "exact_current_build_memorypack_fields",
            "headerLocalId": header_local_id,
            "headerNextLocalId": action_header.get("nextId"),
            "validateParam": validate_param,
            "predicateType": "constant",
            "predicate": {"value": bool(validate_param.get("value"))},
        }
    getter_rows_by_id: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, record in enumerate(records):
        local_id = record.get("localId")
        if not isinstance(local_id, int):
            continue
        if not str(memberships.get(_record_start(record)) or "").startswith(
            "getterList"
        ):
            continue
        getter_rows_by_id.setdefault(local_id, []).append((index, record))

    def resolve_getter(
        local_id: int,
        stack: tuple[int, ...] = (),
    ) -> dict[str, Any]:
        if local_id in stack or len(stack) >= 64:
            return {}
        matching_getters = getter_rows_by_id.get(local_id) or []
        if not matching_getters:
            return {}
        getter_index, getter_record = matching_getters[-1]
        getter_next_start = (
            _record_start(records[getter_index + 1])
            if getter_index + 1 < len(records)
            else len(data)
        )
        getter_detail = decode_levelscript_record_payload(
            data,
            getter_record,
            next_start=getter_next_start,
            action_map_role=memberships.get(_record_start(getter_record)),
        )
        decoded_fields = [
            field
            for field in LEVELSCRIPT_EXACT_GETTER_FIELDS
            if isinstance(getter_detail.get(field), dict)
        ]
        if len(decoded_fields) != 1:
            return {}
        predicate_type = decoded_fields[0]
        predicate = getter_detail[predicate_type]
        children: list[dict[str, Any]] = []
        seen_refs: set[tuple[str, int]] = set()
        for ref in _predicate_local_getter_refs(predicate):
            ref_path = str(ref.get("path") or "")
            child_id = ref.get("getterLocalId")
            identity = (ref_path, child_id)
            if not isinstance(child_id, int) or identity in seen_refs:
                continue
            seen_refs.add(identity)
            child = resolve_getter(child_id, (*stack, local_id))
            if not child:
                return {}
            children.append({
                "path": ref_path,
                "getterLocalId": child_id,
                "predicate": child,
            })
        return {
            "predicateType": predicate_type,
            "predicate": predicate,
            "getterLocalId": local_id,
            "getterUnionTag": getter_detail.get("memoryPackUnionTag"),
            "getterSerializedMemberCount": getter_detail.get(
                "serializedMemberCount"
            ),
            "runtimeSlotStatus": "active-final-serialized-slot",
            "shadowedGetterRecordCount": len(matching_getters) - 1,
            "children": children,
        }

    predicate_tree = resolve_getter(getter_local_id)
    if not predicate_tree:
        return {}
    return {
        "status": "exact_current_build_memorypack_fields",
        "headerLocalId": header_local_id,
        "headerNextLocalId": action_header.get("nextId"),
        "validateParam": validate_param,
        "getterLocalId": getter_local_id,
        "getterUnionTag": predicate_tree.get("getterUnionTag"),
        "getterSerializedMemberCount": predicate_tree.get(
            "getterSerializedMemberCount"
        ),
        "runtimeSlotStatus": "active-final-serialized-slot",
        "shadowedHeaderRecordCount": len(matching_headers) - 1,
        "shadowedGetterRecordCount": predicate_tree.get(
            "shadowedGetterRecordCount", 0
        ),
        "predicateType": predicate_tree["predicateType"],
        "predicate": predicate_tree["predicate"],
        "predicateTree": predicate_tree,
    }


def _decode_entity_hp_changed_event(payload: bytes) -> dict[str, Any]:
    """Decode the current exact single-entity OnEntityHpChanged shape.

    This intentionally accepts only the fully replayed 84-byte form used by
    the current e11 Story trigger. Other list/path/output variants remain raw.
    """
    if len(payload) != 84:
        # The current dynamic-list form stores a LevelScript property path in
        # ``_entityFilter`` and a null ``_entityOutput`` before ``_hpRatio``.
        if len(payload) < 70 or payload[35] != 0x04 or payload[36:44] != b"\xff" * 8:
            return {}
        direction = struct.unpack_from("<i", payload, 31)[0]
        source = struct.unpack_from("<i", payload, 44)[0]
        path_size = struct.unpack_from("<i", payload, 48)[0]
        path_start = 52
        path_end = path_start + path_size
        if (
            direction not in (0, 1, 2)
            or path_size <= 0
            or path_size > 256
            or path_end + 18 != len(payload)
            or payload[path_end] != 0xFF
            or payload[path_end + 1] != 0x04
            or payload[path_end + 6 : path_end + 18]
            != b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        ):
            return {}
        try:
            path = payload[path_start:path_end].decode("utf-8")
        except UnicodeDecodeError:
            return {}
        hp_ratio = struct.unpack_from("<f", payload, path_end + 2)[0]
        if not math.isfinite(hp_ratio) or not 0 <= hp_ratio <= 1:
            return {}
        direction_name = ("Down", "Up", "UpAndDown")[direction]
        direction_phrase = ("falls", "rises", "crosses")[direction]
        return {
            "type": "LevelEvent_OnEntityHpChanged",
            "changedDirection": direction,
            "changedDirectionName": direction_name,
            "entityListFilter": {
                "paramSource": source,
                "path": path,
            },
            "entityOutputPresent": False,
            "hpRatio": round(hp_ratio, 6),
            "transport": "local-entity-hp-runtime-event",
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
            "summary": (
                f"entity list {path} HP {direction_phrase} through "
                f"{round(hp_ratio * 100, 3):g}%"
            ),
            "payloadShape": "dynamic-entity-list-hp-ratio-event",
        }
    if not (
        payload[17] == 4
        and payload[18] in (0, 1)
        and struct.unpack_from("<i", payload, 19)[0] == -1
        and struct.unpack_from("<i", payload, 23)[0] == 0
        and struct.unpack_from("<i", payload, 27)[0] == -1
        and payload[35] == 4
        and struct.unpack_from("<i", payload, 36)[0] == 1
        and payload[40] == 3
        and payload[53] in (0, 1)
        and struct.unpack_from("<i", payload, 54)[0] == -1
        and struct.unpack_from("<i", payload, 58)[0] == 0
        and struct.unpack_from("<i", payload, 62)[0] == -1
        and payload[66] == 0xFF
        and payload[67] == 4
        and struct.unpack_from("<i", payload, 72)[0] == -1
        and struct.unpack_from("<i", payload, 76)[0] == 0
        and struct.unpack_from("<i", payload, 80)[0] == -1
    ):
        return {}
    direction = struct.unpack_from("<i", payload, 31)[0]
    logic_id = struct.unpack_from("<Q", payload, 41)[0]
    slot_id = struct.unpack_from("<I", payload, 49)[0]
    hp_ratio = struct.unpack_from("<f", payload, 68)[0]
    if direction not in (0, 1, 2) or not math.isfinite(hp_ratio) or not 0 <= hp_ratio <= 1:
        return {}
    direction_name = ("Down", "Up", "UpAndDown")[direction]
    direction_phrase = ("falls", "rises", "crosses")[direction]
    return {
        "type": "LevelEvent_OnEntityHpChanged",
        "changedDirection": direction,
        "changedDirectionName": direction_name,
        "entityFilter": [{
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(payload[53]),
        }],
        "hpRatio": round(hp_ratio, 6),
        "transport": "local-entity-hp-runtime-event",
        "serverExchange": False,
        "serializedMissionOrQuestId": False,
        "summary": (
            f"entity slot {slot_id} HP {direction_phrase} through "
            f"{round(hp_ratio * 100, 3):g}%"
        ),
        "payloadShape": "single-entity-hp-ratio-event",
    }


def _decode_list_add_value_entity_ptr(payload: bytes) -> dict[str, Any]:
    """Decode one exact ListAddValueEntityPtr property/output chain."""
    if len(payload) < 50 or payload[0] != 0x04 or payload[1:9] != b"\xff" * 8:
        return {}
    list_source = struct.unpack_from("<i", payload, 9)[0]
    list_path_size = struct.unpack_from("<i", payload, 13)[0]
    list_path_start = 17
    list_path_end = list_path_start + list_path_size
    if list_path_size <= 0 or list_path_size > 256 or list_path_end + 29 > len(payload):
        return {}
    try:
        list_path = payload[list_path_start:list_path_end].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    cursor = list_path_end
    if payload[cursor : cursor + 2] != b"\x04\x03":
        return {}
    logic_id = struct.unpack_from("<Q", payload, cursor + 2)[0]
    slot_id = struct.unpack_from("<I", payload, cursor + 10)[0]
    use_slot_id = payload[cursor + 14]
    value_id_ref = struct.unpack_from("<i", payload, cursor + 15)[0]
    value_source = struct.unpack_from("<i", payload, cursor + 19)[0]
    value_path_size = struct.unpack_from("<i", payload, cursor + 23)[0]
    value_path_start = cursor + 27
    value_path_end = value_path_start + value_path_size
    if (
        use_slot_id not in (0, 1)
        or value_path_size <= 0
        or value_path_size > 256
        or value_path_end != len(payload)
    ):
        return {}
    try:
        value_path = payload[value_path_start:value_path_end].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    output_match = PROPERTY_OUTPUT_RE.match(value_path)
    if not output_match or output_match.group("name") != "entityOutput":
        return {}
    return {
        "action": "ListAddValueEntityPtr",
        "destinationList": {
            "paramSource": list_source,
            "path": list_path,
        },
        "valueEntity": {
            "logicId": logic_id,
            "slotId": slot_id,
            "useSlotId": bool(use_slot_id),
            "idRef": value_id_ref,
            "paramSource": value_source,
            "path": value_path,
            "sourceHeaderLocalId": int(output_match.group("local")),
        },
        "payloadShape": "dynamic-list-and-event-entity-output-exact-eof",
    }


def _decode_raise_custom_script_event(
    payload: bytes,
    texts: list[str],
) -> dict[str, Any]:
    """Decode the exact current-build ``RaiseCustomScriptEvent`` payload.

    GameAssembly and MemoryPack metadata establish the field order as
    ``eventArgsPtr``, ``eventKey``, and ``receiver``.  The current serialized
    receiver is a four-member ``Param<LevelScriptPtr>`` whose constant storage
    carries an explicit script id, or whose ``ParamSource`` value 1002 denotes
    the currently executing LevelScript.  Fail closed for every other shape so
    this diagnostic can never turn an arbitrary string into a script route.
    """
    event_key_offset = 18
    param_tail_size = 12
    receiver_size = 29
    minimum_size = event_key_offset + 5 + param_tail_size + receiver_size
    if len(payload) < minimum_size or payload[event_key_offset] != 0x04:
        return {}
    event_key_size = struct.unpack_from("<I", payload, event_key_offset + 1)[0]
    if not 0 < event_key_size <= 512:
        return {}
    event_key_start = event_key_offset + 5
    event_key_end = event_key_start + event_key_size
    receiver_start = event_key_end + param_tail_size
    if receiver_start + receiver_size > len(payload):
        return {}
    try:
        event_key = payload[event_key_start:event_key_end].decode("utf-8")
    except UnicodeDecodeError:
        return {}
    if (
        not event_key
        or event_key.startswith("$")
        or event_key not in texts
        or any(ord(char) < 0x20 or ord(char) == 0x7F for char in event_key)
    ):
        return {}
    receiver = payload[receiver_start : receiver_start + receiver_size]
    if receiver[0] != 0x04 or receiver[1] not in (0, 1):
        return {}
    has_const_value = bool(receiver[1])
    const_script_id = struct.unpack_from("<Q", receiver, 2)[0]
    id_ref = struct.unpack_from("<i", receiver, 17)[0]
    param_source = struct.unpack_from("<i", receiver, 21)[0]
    path_length = struct.unpack_from("<i", receiver, 25)[0]
    receiver_mode = "dynamic_or_unresolved"
    target_script_id: int | None = None
    if (
        not has_const_value
        and const_script_id == 0
        and id_ref == -1
        and param_source == 1002
        and path_length == -1
    ):
        receiver_mode = "current_script"
    elif (
        has_const_value
        and _is_plausible_levelscript_id(const_script_id)
        and id_ref == -1
        and param_source == 0
        and path_length == -1
    ):
        receiver_mode = "constant_script"
        target_script_id = const_script_id
    return _drop_empty(
        {
            "action": "RaiseCustomScriptEvent",
            "eventKey": event_key,
            "receiverMode": receiver_mode,
            "targetScriptId": target_script_id,
            "receiver": {
                "hasConstValue": has_const_value,
                "constScriptId": const_script_id,
                "idRef": id_ref,
                "paramSource": param_source,
                "pathLength": path_length,
                "payloadOffset": _offset_hex(receiver_start),
            },
            "payloadShape": "raise-custom-script-event-exact-current-build",
        }
    )


def _record_payload_window(
    data: bytes,
    record: dict[str, Any] | None,
    next_start: int | None,
) -> tuple[int, bytes]:
    if not data or not record:
        return 0, b""
    payload_start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if payload_start < 0 or payload_start >= len(data):
        return payload_start, b""
    if next_start is None or next_start <= payload_start or next_start > len(data):
        next_start = min(len(data), payload_start + 160)
    return payload_start, data[payload_start:next_start]


def _decode_tagged_string_parameter_at(
    payload: bytes,
    offset: int,
) -> tuple[str, int] | None:
    """Decode one exact constant-string ActionParam at ``offset``.

    Current LevelScript ActionParam constants use a one-byte constant tag,
    UTF-8 byte length, payload, then the shared 12-byte reference/source tail.
    Returning the consumed end lets callers prove whether a field is the final
    serialized member instead of selecting an arbitrary printable token.
    """
    param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
    if offset < 0 or offset + 5 > len(payload) or payload[offset] != 0x04:
        return None
    size = struct.unpack_from("<I", payload, offset + 1)[0]
    text_start = offset + 5
    text_end = text_start + size
    field_end = text_end + len(param_tail)
    if size <= 0 or field_end > len(payload):
        return None
    if payload[text_end:field_end] != param_tail:
        return None
    try:
        text = payload[text_start:text_end].decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not text or any(ord(char) < 0x20 or ord(char) == 0x7F for char in text):
        return None
    return text, field_end


def _decode_fmv_action(
    payload: bytes,
    payload_start: int,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Decode exact authored FMV ids from the two current native actions.

    IL2CPP metadata and the generated MemoryPack setters prove that
    ``PlayFmvAction._moviePath`` is the first derived field, while
    ``StartFmvAndTeleportAction._fmvId`` is the final derived field.  The
    member counts are part of the union identity, so a tag collision or a
    future payload shape fails closed.
    """
    semantic_key = levelscript_record_semantic_key(record)
    tagged_strings = sorted(
        (
            hit
            for hit in record.get("strings") or []
            if isinstance(hit, dict)
            and isinstance(hit.get("offset"), int)
            and isinstance(hit.get("text"), str)
        ),
        key=lambda hit: int(hit["offset"]),
    )
    if semantic_key == (0x035E, 0x0E):
        if len(tagged_strings) != 1:
            return {}
        hit = tagged_strings[0]
        relative_offset = int(hit["offset"]) - payload_start
        if relative_offset != 0:
            return {}
        decoded = _decode_tagged_string_parameter_at(payload, relative_offset)
        if not decoded or decoded[0] != hit["text"]:
            return {}
        return {
            "action": "PlayFmvAction",
            "fmvId": decoded[0],
            "sourceField": "_moviePath",
            "fieldOffset": _offset_hex(int(hit["offset"])),
            "payloadShape": "play-fmv-movie-path-first-derived-field",
            "nativeMappingId": LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID,
        }
    if semantic_key == (0x04A1, 0x10):
        if not tagged_strings:
            return {}
        hit = tagged_strings[-1]
        relative_offset = int(hit["offset"]) - payload_start
        decoded = _decode_tagged_string_parameter_at(payload, relative_offset)
        if (
            not decoded
            or decoded[0] != hit["text"]
            or decoded[1] != len(payload)
        ):
            return {}
        return {
            "action": "StartFmvAndTeleportAction",
            "fmvId": decoded[0],
            "sourceField": "_fmvId",
            "fieldOffset": _offset_hex(int(hit["offset"])),
            "payloadShape": "start-fmv-teleport-fmv-id-final-derived-field",
            "nativeMappingId": LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID,
        }
    return {}


def decode_levelscript_record_payload(
    data: bytes,
    record: dict[str, Any] | None,
    *,
    next_start: int | None = None,
    action_map_role: str | None = None,
) -> dict[str, Any]:
    """Decode small, diagnostic LevelScript action-record payload hints.

    This deliberately stays conservative: labels are shape hints, not a full
    opcode table. ManualStart/ManualEnd are named only where ActionBase
    formatter tags prove the class; observed rows still do not serialize
    literal levelId + scriptId targets in the action payload.
    """
    if not data or not record:
        return {}
    code = record.get("code")
    kind = record.get("kind")
    if not isinstance(code, int) or not isinstance(kind, int):
        return {}
    key = (code, kind)
    semantic_key = levelscript_record_semantic_key(record)
    payload_start, payload = _record_payload_window(data, record, next_start)
    if not payload:
        return {}

    hint = dict(
        LEVELSCRIPT_RECORD_TAG_HINTS.get(semantic_key)
        or LEVELSCRIPT_RECORD_HINTS.get(key)
        or {}
    )
    action_map_role_text = str(action_map_role or "")
    header_role = action_map_role_text.startswith("headerList")
    getter_role = action_map_role_text.startswith("getterList")
    native_header_name = levelscript_native_header_name(
        record,
        allow_union_tag_fallback=header_role,
    )
    if native_header_name:
        hint.setdefault("label", native_header_name)
        hint.setdefault("confidence", "high")
        hint.setdefault(
            "note",
            "exact current-build ActionHeader formatter mapping; regenerate for other game builds",
        )
        hint.setdefault("nativeHeaderMappingId", LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID)
    fields = _decode_tagged_payload_fields(payload)
    texts = _record_text_values(record, fields)
    property_outputs = _extract_property_output_refs(texts)
    property_keys = [
        text
        for text in texts
        if _looks_like_property_key(text) and not PROPERTY_OUTPUT_RE.match(text)
    ]
    trigger_slot_ids = (
        _extract_trigger_slot_ids(payload)
        if key in TRIGGER_VOLUME_RECORD_KEYS
        or native_header_name in {
            "ScriptEvent_OnLeaderEnterTriggerVolume",
            "ScriptEvent_OnLeaderLeaveTriggerVolume",
        }
        else []
    )
    out: dict[str, Any] = {
        "payloadStart": _offset_hex(payload_start),
        "payloadLength": len(payload),
        "payloadHexPrefix": payload[:48].hex(" "),
        "taggedFields": fields,
    }
    union_tag = record.get("unionTag")
    if isinstance(union_tag, int):
        out["memoryPackUnionTag"] = f"0x{union_tag:04x}"
    serialized_member_count = record.get("serializedMemberCount")
    if isinstance(serialized_member_count, int):
        out["serializedMemberCount"] = serialized_member_count
    if record.get("unionTagEncoding"):
        out["unionTagEncoding"] = record.get("unionTagEncoding")
    out.update(hint)
    action_header_code = header_role or bool(native_header_name)
    if action_header_code:
        action_header = _decode_action_header_prefix(payload)
        if action_header:
            filter_level = record.get("nextId")
            if isinstance(filter_level, int):
                action_header["filterLevel"] = filter_level
                action_header["filterLevelSource"] = "record-fixed-field"
            out["actionHeader"] = action_header
    if header_role and semantic_key == (0x006A, 0x12):
        event_detail = _decode_entity_hp_changed_event(payload)
        if event_detail:
            event_detail["payloadSchemaStatus"] = (
                "exact_current_build_memorypack_fields"
            )
            event_detail["payloadSchemaMappingId"] = (
                LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID
            )
            out["nativeEventDetail"] = event_detail
    if property_outputs:
        out["propertyOutputRefs"] = property_outputs
    if header_role and "nativeEventDetail" not in out:
        event_detail = _decode_named_native_event_detail(
            native_header_name,
            payload,
            texts,
            property_outputs,
            trigger_slot_ids,
        )
        if event_detail:
            out["nativeEventDetail"] = event_detail
    if property_keys and (
        "propertyRole" in hint
        or key in {
            (0x04B8, 0x09),
            (0x104A, 0x00),
        }
    ):
        out["propertyKeys"] = property_keys[:8]
    if trigger_slot_ids:
        out["triggerSlotIds"] = trigger_slot_ids
    if semantic_key == (0x0003, 0x0A):
        gate = _decode_compact_property_gate(payload)
        if gate:
            out["compactGate"] = gate
            gate_key = gate.get("propertyKey")
            if isinstance(gate_key, str) and gate_key and not gate_key.startswith("$"):
                property_keys = list(out.get("propertyKeys") or [])
                if gate_key not in property_keys:
                    property_keys.append(gate_key)
                out["propertyKeys"] = property_keys[:8]
            gate_refs = gate.get("gateLocalRefs") or []
            if gate_refs:
                out["gateLocalRefs"] = gate_refs
                out["gateRole"] = "conditional-local-ref"
    if semantic_key == (0x00ED, 0x0B):
        branch_refs = _extract_tail_local_refs(payload)
        if branch_refs:
            out["branchLocalRefs"] = branch_refs
            out["branchRole"] = "conditional-terminal-local-refs"
    if semantic_key == (0x0495, 0x09):
        split_refs = _decode_split_action_refs(payload)
        if split_refs:
            out["splitActionLocalIds"] = split_refs
            out["branchLocalRefs"] = split_refs
            out["branchRole"] = "typed-split-action-list"
    if semantic_key == (0x002D, 0x09):
        sequence_refs = _decode_branch_sequence_action_refs(payload)
        if sequence_refs:
            out["branchSequenceActionLocalIds"] = sequence_refs
            out["sequenceLocalRefs"] = sequence_refs
            out["sequenceRole"] = "typed-branch-ordered-action-list"
    if semantic_key == (0x00FF, 0x0B):
        if_else_refs = _decode_if_else_action_refs(payload)
        if if_else_refs:
            out.update(if_else_refs)
            out["branchLocalRefs"] = list(dict.fromkeys(
                ref
                for field in ("trueActionLocalId", "falseActionLocalId")
                for ref in [if_else_refs.get(field)]
                if isinstance(ref, int)
            ))
            out["branchRole"] = "typed-if-else-actions"
    if semantic_key == (0x0501, 0x0A):
        while_action = _decode_while_action(payload)
        if while_action:
            out.update(while_action)
            out["branchLocalRefs"] = [while_action["whileDoActionLocalId"]]
            out["branchRole"] = "typed-while-action-body"
    if semantic_key == (0x04BD, 0x0C):
        switch_int = _decode_switch_int_action(payload)
        if switch_int:
            out.update(switch_int)
    if semantic_key == (0x04BE, 0x0C):
        switch_int_larger = _decode_switch_int_action(
            payload,
            field_prefix="switchIntLarger",
            action_name="SwitchIntLarger",
            branch_role="typed-switch-int-larger-actions",
        )
        if switch_int_larger:
            out.update(switch_int_larger)
    if semantic_key == (0x049E, 0x0F):
        start_dialog = _decode_start_dialog_action(payload)
        if start_dialog:
            out["startDialogAction"] = start_dialog
    if semantic_key == (0x04BF, 0x0C):
        switch_string = _decode_switch_string_action(payload)
        if switch_string:
            out.update(switch_string)
    if semantic_key == (0x04F9, 0x0E):
        wait_trigger_volume = _decode_wait_for_seconds_in_trigger_volume_action(
            payload
        )
        if wait_trigger_volume:
            out.update(wait_trigger_volume)
    if semantic_key == (0x034A, 0x14):
        play3d_radio = _decode_play3d_radio_action(payload)
        if play3d_radio:
            out["play3DRadio"] = play3d_radio
    if semantic_key in {(0x035E, 0x0E), (0x04A1, 0x10)}:
        fmv_action = _decode_fmv_action(payload, payload_start, record)
        if fmv_action:
            out["fmvAction"] = fmv_action
    if semantic_key == (0x031E, 0x0C):
        npc_patrol_start = _decode_npc_patrol_start_action(payload)
        if npc_patrol_start:
            out["npcPatrolStart"] = npc_patrol_start
    if semantic_key == (0x00B9, 0x09):
        exit_custom_performance = _decode_exit_level_custom_performance_action(
            payload
        )
        if exit_custom_performance:
            out["exitLevelCustomPerformance"] = exit_custom_performance
    if semantic_key == (0x04CA, 0x09):
        toggle_clear_screen = _decode_toggle_clear_screen_but_radio_action(
            payload
        )
        if toggle_clear_screen:
            out["toggleClearScreenButRadio"] = toggle_clear_screen
    if semantic_key == (0x02FE, 0x0A):
        main_char_move_to = _decode_main_char_move_to_action(payload)
        if main_char_move_to:
            out["mainCharMoveTo"] = main_char_move_to
    if semantic_key == (0x0034, 0x0E):
        call_server = _decode_call_server_action(payload)
        if call_server:
            record_uid = str(record.get("uid") or "").strip()
            event_name = str(call_server.get("eventName") or "").strip()
            if (
                re.fullmatch(r"[0-9a-fA-F]{8}", record_uid)
                and event_name.casefold() == f"#{record_uid}".casefold()
            ):
                call_server.update({
                    "eventNameIdentity": "record-uid-prefixed",
                    "callbackCorrelationLabel": True,
                    "storyGraphRole": "diagnostic-only",
                    "missionOwnershipEvidence": False,
                    "orderEvidence": False,
                })
            out["callServer"] = call_server
    if semantic_key == (0x0166, 0x0A):
        list_add = _decode_list_add_value_entity_ptr(payload)
        if list_add:
            out["listAddValueEntityPtr"] = list_add
    if semantic_key == (0x0380, 0x0B):
        raise_custom_script_event = _decode_raise_custom_script_event(payload, texts)
        if raise_custom_script_event:
            out["raiseCustomScriptEvent"] = raise_custom_script_event
    if semantic_key == (0x0028, 0x0A):
        entity_compare = _decode_entity_compare_getter(payload, property_outputs)
        if entity_compare:
            out["entityCompare"] = entity_compare
    if getter_role and semantic_key in {
        (0x0004, 0x0A),
        (0x0006, 0x09),
        (0x000A, 0x08),
        (0x000B, 0x08),
        (0x000D, 0x09),
        (0x0013, 0x0A),
        (0x0016, 0x09),
        (0x001F, 0x0A),
        (0x004E, 0x08),
        (0x0049, 0x0A),
        (0x0100, 0x09),
        (0x012F, 0x08),
        (0x0133, 0x09),
        (0x013A, 0x08),
        (0x017C, 0x08),
        (0x0184, 0x08),
        (0x01A5, 0x08),
        (0x01AA, 0x0A),
        (0x01AC, 0x09),
        (0x01AD, 0x0A),
        (0x01BA, 0x09),
        (0x01C2, 0x08),
    }:
        getter_payload = _getter_subtype_payload(data, record, next_start)
        if semantic_key == (0x013A, 0x08):
            mission_state_getter = _decode_get_mission_state_getter(getter_payload)
            if mission_state_getter:
                out["getMissionState"] = mission_state_getter
        elif semantic_key == (0x0013, 0x0A):
            stage_check = _decode_check_levelscript_stage_getter(getter_payload)
            if stage_check:
                out["checkLevelScriptStage"] = stage_check
        elif semantic_key == (0x0016, 0x09):
            completion_check = _decode_check_mission_or_quest_complete_getter(
                getter_payload
            )
            if completion_check:
                out["checkMissionOrQuestIsComplete"] = completion_check
        elif semantic_key == (0x001F, 0x0A):
            mission_state_compare = _decode_compare_mission_state_getter(
                getter_payload
            )
            if mission_state_compare:
                out["compareMissionState"] = mission_state_compare
        elif semantic_key == (0x0004, 0x0A):
            boolean_compare = _decode_boolean_compare_getter(getter_payload)
            if boolean_compare:
                out["booleanCompare"] = boolean_compare
        elif semantic_key == (0x0006, 0x09):
            boolean_and = _decode_bool_binary_getter(
                getter_payload,
                operation="And",
            )
            if boolean_and:
                out["boolGetterAnd"] = boolean_and
        elif semantic_key == (0x000A, 0x08):
            boolean_invert = _decode_bool_invert_getter(getter_payload)
            if boolean_invert:
                out["boolGetterInvert"] = boolean_invert
        elif semantic_key == (0x000B, 0x08):
            boolean_all = _decode_bool_multi_and_getter(getter_payload)
            if boolean_all:
                out["boolGetterMultiAnd"] = boolean_all
        elif semantic_key == (0x000D, 0x09):
            boolean_or = _decode_bool_binary_getter(
                getter_payload,
                operation="Or",
            )
            if boolean_or:
                out["boolGetterOr"] = boolean_or
        elif semantic_key == (0x004E, 0x08):
            condition_result = _decode_get_condition_result_getter(
                getter_payload
            )
            if condition_result:
                out["getConditionResult"] = condition_result
        elif semantic_key == (0x0049, 0x0A):
            float_compare = _decode_number_compare_getter(
                getter_payload,
                floating=True,
            )
            if float_compare:
                out["floatNewCompare"] = float_compare
        elif semantic_key == (0x0100, 0x09):
            property_bool = _decode_levelscript_property_bool_getter(
                getter_payload
            )
            if property_bool:
                out["getLevelScriptPropertyGenericBool"] = property_bool
        elif semantic_key == (0x012F, 0x08):
            levelscript_stage = _decode_get_levelscript_stage_getter(
                getter_payload
            )
            if levelscript_stage:
                out["getLevelScriptStage"] = levelscript_stage
        elif semantic_key == (0x0133, 0x09):
            lsm_completed = _decode_get_lsm_is_completed_getter(getter_payload)
            if lsm_completed:
                out["getLsmIsCompleted"] = lsm_completed
        elif semantic_key == (0x017C, 0x08):
            getter_bool = _decode_getter_bool(getter_payload)
            if getter_bool:
                out["getterBool"] = getter_bool
        elif semantic_key == (0x0184, 0x08):
            getter_int = _decode_getter_int(getter_payload)
            if getter_int:
                out["getterInt"] = getter_int
        elif semantic_key == (0x01A5, 0x08):
            getter_string = _decode_getter_string(getter_payload)
            if getter_string:
                out["getterString"] = getter_string
        elif semantic_key == (0x01AA, 0x0A):
            int_compare = _decode_number_compare_getter(
                getter_payload,
                floating=False,
            )
            if int_compare:
                out["intCompare"] = int_compare
        elif semantic_key == (0x01AC, 0x09):
            int_equal = _decode_int_equal_getter(getter_payload)
            if int_equal:
                out["intEqual"] = int_equal
        elif semantic_key == (0x01AD, 0x0A):
            interactive_state = _decode_interactive_check_state_getter(
                getter_payload
            )
            if interactive_state:
                out["interactiveCheckState"] = interactive_state
        elif semantic_key == (0x01BA, 0x09):
            int_random = _decode_int_random_getter(getter_payload)
            if int_random:
                out["intRandom"] = int_random
        elif semantic_key == (0x01C2, 0x08):
            gender = _decode_is_endmin_gender_getter(getter_payload)
            if gender:
                out["isEndminGender"] = gender
    if key in {(0x0308, 0x0A), (0x0302, 0x0A)}:
        role = str(hint.get("levelScriptControlRole") or "")
        manual_control = _decode_manual_levelscript_control(payload, role)
        if manual_control:
            out["manualControl"] = manual_control

    if semantic_key == (0x04F7, 0x09) and payload[:1] == b"\x04" and len(payload) >= 5:
        out["seconds"] = _round_float(struct.unpack_from("<f", payload, 1)[0])
    elif key in SCRIPT_POINTER_REF_RECORDS:
        pointer = decode_script_pointer_payload(data, record)
        if pointer:
            out.setdefault("label", "script-ptr-scalar-ref")
            out.setdefault("confidence", "medium")
            out.setdefault("note", (
                "LevelScriptPtr plus scalar parameter; matches trigger-volume predicate/action field shape, "
                "not ManualStart/ManualEnd because no levelId string is serialized"
            ))
            out["scriptPointer"] = pointer
        else:
            out.setdefault("label", "scalar-control")
            out.setdefault("confidence", "low")
            out.setdefault("note", (
                "same opcode family as script-pointer refs, but this payload does not contain "
                "a plausible LevelScript id"
            ))
    elif key == (0x0463, 0x09) and len(payload) >= 4:
        count = struct.unpack_from("<I", payload, 0)[0]
        if count <= 64 and 4 + count * 4 <= len(payload):
            out["localRecordRefs"] = [
                struct.unpack_from("<I", payload, 4 + index * 4)[0]
                for index in range(count)
            ]
    elif semantic_key in {(0x02EE, 0x09), (0x0304, 0x09)}:
        for text in texts:
            if text.startswith("guide_") and not text.startswith("$"):
                out["guideId"] = text
                break
    elif key == (0x104A, 0x00):
        texts = [
            str(hit.get("text") or "")
            for hit in (record.get("strings") or []) + (record.get("plainStrings") or [])
            if isinstance(hit, dict) and hit.get("text")
        ]
        if texts:
            out["signalKeys"] = texts[:4]
    return _drop_empty(out)


def _tail_candidate(data: bytes, offset: int) -> dict[str, Any]:
    start_shape_offset = offset + 8
    start_shape, start_shape_end = _decode_levelscript_shape_list(data, start_shape_offset)
    start_shape_status = str(start_shape.get("status") or "missing")
    start_shape_count = start_shape.get("count")
    start_type_offset: int | None = None
    if start_shape_status in {"null", "present"} and start_shape_end is not None:
        start_type_offset = start_shape_end

    start_type_raw = _u32(data, start_type_offset) if start_type_offset is not None else None
    start_type_valid = start_type_raw in LEVELSCRIPT_START_TYPE_NAMES
    task_map_offset = start_type_offset + 4 if start_type_valid and start_type_offset is not None else None
    task_map_raw = _u32(data, task_map_offset) if task_map_offset is not None else None
    task_map_status, task_map_count = _list_status(task_map_raw)
    task_map_end: int | None = None
    if task_map_offset is not None and task_map_status == "null":
        task_map_end = task_map_offset + 4
    elif (
        task_map_offset is not None
        and task_map_status == "present"
        and task_map_count == 0
    ):
        # An empty dictionary has no records.  Its end is exact, so the next
        # top-level member must begin immediately after the count.  Searching
        # forward to the final trigger-volume-shaped bytes can otherwise make
        # an embedded logic ID look like the repeated top-level script ID.
        task_map_end = task_map_offset + 4
    trigger_volume_offset = task_map_end
    trigger_volume: dict[str, Any] = {}
    trigger_volume_end: int | None = None
    if trigger_volume_offset is not None:
        trigger_volume, trigger_volume_end = _decode_trigger_volume_map(data, trigger_volume_offset)
    elif task_map_offset is not None and task_map_status == "present":
        (
            trigger_volume_offset,
            trigger_volume,
            trigger_volume_end,
        ) = _find_final_trigger_volume_map(
            data,
            search_start=task_map_offset + 4,
        )
    trigger_volume_status = str(trigger_volume.get("status") or "missing")
    trigger_volume_count = trigger_volume.get("count")

    score = offset
    if start_type_valid:
        score += 1_000_000
    if start_shape_status == "null":
        score += 100_000
    elif start_shape_count == 0:
        score += 50_000
    if task_map_status in {"null", "present"}:
        score += 10_000
    if (
        trigger_volume_status in {"null", "present"}
        and trigger_volume.get("parseStatus") != "truncated"
        and trigger_volume_end == len(data)
    ):
        # A completely decoded final top-level member is stronger evidence
        # than a locally plausible embedded ID and shape/list header.
        score += 250_000

    return {
        "scriptIdOffset": offset,
        "scriptIdOffsetHex": f"0x{offset:x}",
        "startShapeListOffset": start_shape_offset,
        "startShapeListStatus": start_shape_status,
        "startShapeListCount": start_shape_count,
        "startShapeList": start_shape,
        "startTypeOffset": start_type_offset,
        "startTypeOffsetHex": _offset_hex(start_type_offset),
        "startTypeRaw": start_type_raw if start_type_valid else None,
        "startTypeName": LEVELSCRIPT_START_TYPE_NAMES.get(
            start_type_raw if start_type_raw is not None else -1,
            "",
        ),
        "taskMapOffset": task_map_offset,
        "taskMapOffsetHex": _offset_hex(task_map_offset),
        "taskMapStatus": task_map_status,
        "taskMapCount": task_map_count,
        "triggerVolumesOffset": trigger_volume_offset,
        "triggerVolumesOffsetHex": _offset_hex(trigger_volume_offset),
        "triggerVolumesStatus": trigger_volume_status,
        "triggerVolumesCount": trigger_volume_count,
        "triggerVolumes": trigger_volume,
        "score": score,
    }


LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID = (
    "gameassembly-2026-07-22-levelscript-task-check-mission-state-0x67"
)
LEVELSCRIPT_TASK_CONDITION_MAPPING_ID = (
    "gameassembly-2026-08-02-levelscript-task-root-gamecondition-tags"
)
LEVELSCRIPT_TASK_CONDITION_TAGS = {
    0x0017: ("CheckBuildingConnected", 8),
    0x0018: ("CheckBuildingConnectedAsMA2SB", 8),
    0x0019: ("CheckBuildingConnectedExist", 8),
    0x001A: ("CheckBuildingConnectedSpecify", 9),
    0x001B: ("CheckBuildingStateInArea", 9),
    0x0023: ("CheckClientGlobalVar", 7),
    0x0035: ("CheckFacBuildingState", 8),
    0x0038: ("CheckFluidVolume", 9),
    0x0039: ("CheckFMVFinish", 5),
    0x0045: ("CheckInteractiveDestroyed", 6),
    0x0050: ("CheckLevelScriptPropertyBool", 9),
    0x0051: ("CheckLevelScriptPropertyInt", 9),
    0x0053: ("CheckLevelScriptStage", 8),
    0x0067: ("CheckMissionState", 7),
    0x006A: ("CheckMonsterKilled", 9),
    0x006B: ("CheckMonsterSpawnerComplete", 6),
    0x0084: ("CheckRepairBuilding", 6),
    0x008D: ("CheckScriptTaskStateEqual", 9),
    0x008F: ("CheckServerGlobalVar", 7),
    0x009F: ("CheckTalkOptionFinish", 6),
    0x00B2: ("CombineCondition", 6),
    0x00D0: ("OnBuildingPanelOpen", 6),
    0x0108: ("DepotHasItem", 7),
    0x010B: ("FacBattleBuildingCurEnergy", 8),
    0x010D: ("FacBuildingCountInScene", 8),
    0x010E: ("FacBuildingFluidContainerHasItem", 9),
    0x010F: ("FacBuildingProducingCountInScene", 8),
    0x0112: ("FacProducePowerReach", 6),
    0x0113: ("FacProducingFormulaCountInScene", 8),
    0x0114: ("FacStatisticItemGen", 8),
    0x0115: ("FacStatisticItemGenRate", 8),
    0x0127: ("HasItemCount", 7),
    0x0129: ("InteractiveCheckBool", 8),
    0x012A: ("InteractiveCheckInt", 9),
    0x012D: ("PlayerHasItem", 8),
    0x012E: ("PlayerHasItemInItemBag", 8),
    0x0132: ("TaskReachDestination", 6),
}
_MISSION_STATE_NAMES = {
    0: "None",
    1: "Available",
    2: "Processing",
    3: "Completed",
    4: "Failed",
    5: "Disabled",
}
_MISSION_STATE_COMPARER_NAMES = {
    0: "Equal",
    1: "NotEqual",
}
_NUMBER_COMPARER_NAMES = {
    0: "Equal",
    1: "NotEqual",
    2: "GreaterThan",
    3: "GreaterEqual",
    4: "LessThan",
    5: "LessEqual",
}


def _decode_string_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode an authored ``Param<string>`` including a null constant value."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    size = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if size == -1:
        value = None
    elif 0 <= size <= 1024 and cursor + size <= len(payload):
        try:
            value = payload[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
    else:
        return None
    tail = _decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"value": value, **detail}, end


def _decode_nullable_string_value(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode a raw MemoryPack nullable string without a ``Param`` tail."""
    if cursor + 4 > len(payload):
        return None
    size = struct.unpack_from("<i", payload, cursor)[0]
    cursor += 4
    if size == -1:
        return {"value": None}, cursor
    if size < 0 or size > 1024 or cursor + size > len(payload):
        return None
    try:
        value = payload[cursor : cursor + size].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return {"value": value}, cursor + size


def _decode_u64_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode an authored eight-byte integer Param value."""
    if cursor + 9 > len(payload) or payload[cursor] != 0x04:
        return None
    value = struct.unpack_from("<Q", payload, cursor + 1)[0]
    tail = _decode_param_tail(payload, cursor + 9)
    if tail is None:
        return None
    detail, end = tail
    return {"value": str(value), **detail}, end


def _decode_entity_ptr_list_param(
    payload: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the current constant ``Param<List<ScriptEntityPtr>>`` shape."""
    if cursor + 5 > len(payload) or payload[cursor] != 0x04:
        return None
    count = struct.unpack_from("<i", payload, cursor + 1)[0]
    cursor += 5
    if count == -1:
        values = None
    elif 0 <= count <= 1024:
        values = []
        for _ in range(count):
            if cursor + 14 > len(payload) or payload[cursor] != 0x03:
                return None
            logic_id = struct.unpack_from("<Q", payload, cursor + 1)[0]
            slot_id = struct.unpack_from("<I", payload, cursor + 9)[0]
            use_slot_id = payload[cursor + 13]
            if use_slot_id not in (0, 1):
                return None
            values.append({
                "logicId": str(logic_id),
                "slotId": slot_id,
                "useSlotId": bool(use_slot_id),
            })
            cursor += 14
    else:
        return None
    tail = _decode_param_tail(payload, cursor)
    if tail is None:
        return None
    detail, end = tail
    return {"values": values, **detail}, end


def _decode_task_condition_union_header(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[int, int, str, int] | None:
    if offset + 2 > limit:
        return None
    if data[offset] < 0xFA:
        return data[offset], data[offset + 1], "memorypack-u8", offset + 2
    if data[offset] == 0xFA and offset + 4 <= limit:
        return (
            struct.unpack_from("<H", data, offset + 1)[0],
            data[offset + 3],
            "memorypack-fa-u16",
            offset + 4,
        )
    return None


def _decode_task_condition_common(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    if offset + 4 > limit:
        return None
    scope_mask = struct.unpack_from("<i", data, offset)[0]
    unique_id, cursor = _read_compact_string(data, offset + 4)
    if (
        unique_id is None
        or cursor is None
        or cursor + 2 > limit
        or not re.fullmatch(r"[0-9a-f]{8}", unique_id)
        or data[cursor] not in (0, 1)
        or data[cursor + 1] not in (0, 1)
        or scope_mask < 0
        or scope_mask > 0xFFFF
    ):
        return None
    return {
        "scopeMask": scope_mask,
        "uniqueId": unique_id,
        "useCurrentScope": bool(data[cursor]),
        "useGraphScope": bool(data[cursor + 1]),
    }, cursor + 2


def _condition_param(
    decoder: Any,
    data: bytes,
    cursor: int,
    limit: int,
) -> tuple[Any, int] | None:
    decoded = decoder(data, cursor)
    if decoded is None or decoded[1] > limit:
        return None
    return decoded


def _decode_levelscript_task_condition(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one supported root ``GameCondition`` task payload exactly."""
    start = offset
    header = _decode_task_condition_union_header(data, offset, limit)
    if header is None:
        return None
    union_tag, member_count, tag_encoding, cursor = header
    identity = LEVELSCRIPT_TASK_CONDITION_TAGS.get(union_tag)
    if identity is None or identity[1] != member_count:
        return None
    condition_type = identity[0]
    common_decoded = _decode_task_condition_common(data, cursor, limit)
    if common_decoded is None:
        return None
    common, cursor = common_decoded
    fields: dict[str, Any] = {}

    def read_param(name: str, decoder: Any) -> bool:
        nonlocal cursor
        decoded = _condition_param(decoder, data, cursor, limit)
        if decoded is None:
            return False
        fields[name], cursor = decoded
        return True

    if condition_type == "CheckMissionState":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("missionId", _decode_string_param)
            and read_param("targetMissionState", _decode_i32_param)
        ):
            return None
        comparer_raw = fields["comparer"]["value"]
        target_raw = fields["targetMissionState"]["value"]
        if (
            comparer_raw not in _MISSION_STATE_COMPARER_NAMES
            or target_raw not in _MISSION_STATE_NAMES
        ):
            return None
        fields["comparerName"] = _MISSION_STATE_COMPARER_NAMES[comparer_raw]
        fields["targetMissionStateName"] = _MISSION_STATE_NAMES[target_raw]
    elif condition_type == "CheckFMVFinish":
        if not read_param("fmvId", _decode_string_param):
            return None
    elif condition_type in ("CheckClientGlobalVar", "CheckServerGlobalVar"):
        key_decoder = (
            _decode_string_param
            if condition_type == "CheckClientGlobalVar"
            else _decode_i32_param
        )
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("key", key_decoder)
            and read_param("targetValue", _decode_u64_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type in (
        "CheckBuildingConnected",
        "CheckBuildingConnectedAsMA2SB",
    ):
        if not (
            read_param("facBuildingIdA", _decode_string_param)
            and read_param("facBuildingIdB", _decode_string_param)
            and read_param("targetCount", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckBuildingConnectedExist":
        if not (
            read_param("buildingIdEnd", _decode_string_param)
            and read_param("buildingIdStart", _decode_string_param)
            and read_param("exist", _decode_bool_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckBuildingConnectedSpecify":
        if not (
            read_param("connected", _decode_bool_param)
            and read_param("conveyorType", _decode_i32_param)
            and read_param("instKeyA", _decode_string_param)
            and read_param("instKeyB", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckBuildingStateInArea":
        if not (
            read_param("facBuildingId", _decode_string_param)
            and read_param("facStateType", _decode_i32_param)
            and read_param("targetAreaId", _decode_string_param)
            and read_param("targetCount", _decode_i32_param)
            and read_param("targetMapId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckFluidVolume":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("targetVolume", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
            and read_param("volumeId", _decode_u64_param)
            and read_param("waterType", _decode_string_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "CheckFacBuildingState":
        if not (
            read_param("facStateId", _decode_i32_param)
            and read_param("instKey", _decode_string_param)
            and read_param("isInState", _decode_bool_param)
            and read_param("sceneName", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckRepairBuilding":
        if not (
            read_param("repairId", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "CheckScriptTaskStateEqual":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
            and read_param("targetValue", _decode_i32_param)
            and read_param("taskKey", _decode_levelscript_task_ptr_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "OnBuildingPanelOpen":
        if not (
            read_param("buildingId", _decode_string_param)
            and read_param("needWaitAnimation", _decode_bool_param)
        ):
            return None
    elif condition_type == "FacProducePowerReach":
        if not (
            read_param("power", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "FacProducingFormulaCountInScene":
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
            and read_param("facFormulaId", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type == "DepotHasItem":
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("itemId", _decode_string_param)
            and read_param("targetItemCount", _decode_i32_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type in (
        "FacBattleBuildingCurEnergy",
        "FacBuildingCountInScene",
        "FacBuildingFluidContainerHasItem",
        "FacBuildingProducingCountInScene",
        "FacStatisticItemGen",
        "FacStatisticItemGenRate",
        "HasItemCount",
    ):
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
        ):
            return None
        if condition_type == "FacBattleBuildingCurEnergy":
            if not (
                read_param("instKey", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif condition_type in (
            "FacBuildingCountInScene",
            "FacBuildingProducingCountInScene",
        ):
            if not (
                read_param("facBuildingId", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif condition_type in (
            "FacStatisticItemGen",
            "FacStatisticItemGenRate",
        ):
            if not (
                read_param("itemId", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif condition_type == "FacBuildingFluidContainerHasItem":
            if not (
                read_param("instKey", _decode_string_param)
                and read_param("itemId", _decode_string_param)
                and read_param("levelId", _decode_string_param)
            ):
                return None
        elif not read_param("itemId", _decode_string_param):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type in ("PlayerHasItem", "PlayerHasItemInItemBag"):
        if not (
            read_param("displayInfoBox", _decode_nullable_string_value)
            and read_param("compareOperator", _decode_i32_param)
            and read_param("itemId", _decode_string_param)
            and read_param("targetItemCount", _decode_i32_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type == "CheckInteractiveDestroyed":
        if not (
            read_param("entity", _decode_constant_entity_ptr_param)
            and read_param("mapId", _decode_string_param)
        ):
            return None
    elif condition_type in (
        "CheckLevelScriptPropertyBool",
        "CheckLevelScriptPropertyInt",
    ):
        value_decoder = (
            _decode_bool_param
            if condition_type.endswith("Bool")
            else _decode_i32_param
        )
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("key", _decode_string_param)
            and read_param("mapId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
            and read_param("value", value_decoder)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "CheckLevelScriptStage":
        if not (
            read_param("compareOperator", _decode_i32_param)
            and read_param("progressToCompare", _decode_i32_param)
            and read_param("levelId", _decode_string_param)
            and read_param("scriptId", _decode_levelscript_ptr_param)
        ):
            return None
        fields["compareOperatorName"] = _NUMBER_COMPARER_NAMES.get(
            fields["compareOperator"]["value"],
            "",
        )
    elif condition_type == "CheckMonsterKilled":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("enemyIds", _decode_entity_ptr_list_param)
            and read_param("sceneId", _decode_string_param)
            and read_param("targetValue", _decode_u64_param)
            and cursor < limit
            and data[cursor] in (0, 1)
        ):
            return None
        fields["needKillAll"] = bool(data[cursor])
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
        cursor += 1
    elif condition_type == "CheckMonsterSpawnerComplete":
        if not (
            read_param("levelId", _decode_string_param)
            and read_param("spawnerId", _decode_u64_param)
        ):
            return None
    elif condition_type == "CheckTalkOptionFinish":
        if not (
            read_param("dialogId", _decode_string_param)
            and read_param("finishId", _decode_i32_param)
        ):
            return None
    elif condition_type == "InteractiveCheckBool":
        if not (
            read_param("compareValue", _decode_bool_param)
            and read_param("entityId", _decode_constant_entity_ptr_param)
            and read_param("key", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
    elif condition_type == "InteractiveCheckInt":
        if not (
            read_param("comparer", _decode_i32_param)
            and read_param("compareValue", _decode_i32_param)
            and read_param("entityId", _decode_constant_entity_ptr_param)
            and read_param("key", _decode_string_param)
            and read_param("levelId", _decode_string_param)
        ):
            return None
        fields["comparerName"] = _NUMBER_COMPARER_NAMES.get(
            fields["comparer"]["value"],
            "",
        )
    elif condition_type == "TaskReachDestination":
        if not (
            read_param("areaId", _decode_string_param)
            and read_param("mapId", _decode_string_param)
        ):
            return None
    elif condition_type == "CombineCondition":
        if cursor + 4 > limit:
            return None
        size = struct.unpack_from("<i", data, cursor)[0]
        cursor += 4
        if size < 0 or size > 1024 or cursor + size + 4 > limit:
            return None
        try:
            expression = data[cursor : cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
        subcondition_count = struct.unpack_from("<I", data, cursor)[0]
        cursor += 4
        # Current receiver task maps use only the exact empty serialized list.
        # A non-empty list has no element lengths and needs its own recursive
        # boundary proof before it can be accepted.
        if subcondition_count != 0:
            return None
        fields["conditionEvalString"] = expression
        fields["subConditionCount"] = 0
    else:
        return None

    return {
        "type": condition_type,
        "conditionUnionTag": f"0x{union_tag:04x}",
        "conditionUnionTagEncoding": tag_encoding,
        "serializedMemberCount": member_count,
        "conditionOffset": start,
        "conditionOffsetHex": _offset_hex(start),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        **common,
        **fields,
        "nativeMappingId": LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
    }, cursor


def _decode_levelscript_check_mission_state_condition(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one exact GameCondition tag 0x67 / seven-member payload."""
    start = offset
    if offset + 2 > limit or data[offset : offset + 2] != b"\x67\x07":
        return None
    cursor = offset + 2
    if cursor + 4 > limit:
        return None
    scope_mask = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    unique_id, next_cursor = _read_compact_string(data, cursor)
    if (
        unique_id is None
        or next_cursor is None
        or next_cursor > limit
        or not re.fullmatch(r"[0-9a-f]{8}", unique_id)
    ):
        return None
    cursor = next_cursor
    if (
        cursor + 2 > limit
        or data[cursor] not in (0, 1)
        or data[cursor + 1] not in (0, 1)
    ):
        return None
    use_current_scope = bool(data[cursor])
    use_graph_scope = bool(data[cursor + 1])
    cursor += 2
    comparer = _decode_constant_i32_param(data, cursor)
    if comparer is None or comparer[1] > limit:
        return None
    comparer_raw, cursor = comparer
    mission = _decode_constant_string_param(data, cursor)
    if mission is None or mission[1] > limit:
        return None
    mission_id, cursor = mission
    target_state = _decode_constant_i32_param(data, cursor)
    if target_state is None or target_state[1] > limit:
        return None
    target_state_raw, cursor = target_state
    if (
        scope_mask < 0
        or scope_mask > 0xFFFF
        or comparer_raw not in _MISSION_STATE_COMPARER_NAMES
        or target_state_raw not in _MISSION_STATE_NAMES
        or not mission_id
        or not re.fullmatch(r"[A-Za-z0-9_#-]+", mission_id)
    ):
        return None
    return {
        "type": "CheckMissionState",
        "conditionUnionTag": "0x0067",
        "serializedMemberCount": 7,
        "conditionOffset": start,
        "conditionOffsetHex": _offset_hex(start),
        "conditionEndOffset": cursor,
        "conditionEndOffsetHex": _offset_hex(cursor),
        "scopeMask": scope_mask,
        "uniqueId": unique_id,
        "useCurrentScope": use_current_scope,
        "useGraphScope": use_graph_scope,
        "comparerRaw": comparer_raw,
        "comparerName": _MISSION_STATE_COMPARER_NAMES[comparer_raw],
        "missionId": mission_id,
        "targetMissionStateRaw": target_state_raw,
        "targetMissionStateName": _MISSION_STATE_NAMES[target_state_raw],
        "nativeMappingId": LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
    }, cursor


def _decode_levelscript_single_condition_task_mission_state(
    data: bytes,
    offset: int,
    limit: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode one complete LevelScriptTaskData with one mission condition."""
    start = offset
    task_key, cursor = _read_compact_string(data, offset)
    if (
        task_key is None
        or cursor is None
        or cursor > limit
        or not re.fullmatch(r"[0-9a-f]{8}", task_key)
        or cursor + 6 > limit
        or data[cursor] != 4
        or data[cursor + 1] not in (0, 1)
    ):
        return None
    task_data_member_count = data[cursor]
    can_be_tracked = bool(data[cursor + 1])
    cursor += 2
    condition_count = struct.unpack_from("<I", data, cursor)[0]
    cursor += 4
    if condition_count != 1:
        return None
    condition_key, next_cursor = _read_compact_string(data, cursor)
    if (
        condition_key is None
        or next_cursor is None
        or next_cursor > limit
        or not re.fullmatch(r"[0-9a-f]{8}", condition_key)
    ):
        return None
    cursor = next_cursor
    if cursor >= limit or data[cursor] != 3:
        return None
    task_condition_member_count = data[cursor]
    cursor += 1
    condition_decoded = _decode_levelscript_check_mission_state_condition(
        data,
        cursor,
        limit,
    )
    if condition_decoded is None:
        return None
    condition, cursor = condition_decoded
    if condition["uniqueId"] != condition_key or cursor + 10 > limit:
        return None
    if data[cursor] not in (0, 1):
        return None
    is_main_objective = bool(data[cursor])
    objective_enum = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if data[cursor] not in (0, 1):
        return None
    need_manual_check = bool(data[cursor])
    task_type = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if not (0 <= objective_enum <= 0x100 and 0 <= task_type <= 0x100):
        return None
    return {
        "taskKey": task_key,
        "taskEntryOffset": start,
        "taskEntryOffsetHex": _offset_hex(start),
        "taskEntryEndOffset": cursor,
        "taskEntryEndOffsetHex": _offset_hex(cursor),
        "taskDataMemberCount": task_data_member_count,
        "canBeTracked": can_be_tracked,
        "conditionDictCount": condition_count,
        "conditionKey": condition_key,
        "taskConditionMemberCount": task_condition_member_count,
        "condition": condition,
        "isMainObjective": is_main_objective,
        "objectiveEnum": objective_enum,
        "needManualCheck": need_manual_check,
        "taskType": task_type,
    }, cursor


def _looks_like_levelscript_task_entry_prefix(
    data: bytes,
    offset: int,
    limit: int,
) -> bool:
    task_key, cursor = _read_compact_string(data, offset)
    return bool(
        task_key
        and cursor is not None
        and cursor + 6 <= limit
        and re.fullmatch(r"[0-9a-f]{8}", task_key)
        and data[cursor] == 4
        and data[cursor + 1] in (0, 1)
        and struct.unpack_from("<I", data, cursor + 2)[0] <= 128
    )


def _decode_levelscript_task_entry(
    data: bytes,
    offset: int,
    limit: int,
    diagnostics: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], int] | None:
    """Decode one complete current-build ``LevelScriptTaskData`` envelope."""
    start = offset
    task_key, cursor = _read_compact_string(data, offset)
    if (
        task_key is None
        or cursor is None
        or cursor + 6 > limit
        or not re.fullmatch(r"[0-9a-f]{8}", task_key)
        or data[cursor] != 4
        or data[cursor + 1] not in (0, 1)
    ):
        if diagnostics is not None and not diagnostics:
            diagnostics.append({
                "gate": "taskEntryEnvelope",
                "taskEntryOffset": offset,
                "taskEntryOffsetHex": _offset_hex(offset),
                "limitOffset": limit,
                "limitOffsetHex": _offset_hex(limit),
            })
        return None
    task_data_member_count = data[cursor]
    can_be_tracked = bool(data[cursor + 1])
    condition_count = struct.unpack_from("<I", data, cursor + 2)[0]
    cursor += 6
    if condition_count > 128:
        return None

    conditions: list[dict[str, Any]] = []
    for _ in range(condition_count):
        condition_entry_start = cursor
        condition_key, next_cursor = _read_compact_string(data, cursor)
        if (
            condition_key is None
            or next_cursor is None
            or next_cursor >= limit
            or not re.fullmatch(r"[0-9a-f]{8}", condition_key)
            or data[next_cursor] != 3
        ):
            if diagnostics is not None and not diagnostics:
                diagnostics.append({
                    "gate": "taskConditionEnvelope",
                    "taskKey": task_key,
                    "conditionIndex": len(conditions),
                    "conditionEntryOffset": condition_entry_start,
                    "conditionEntryOffsetHex": _offset_hex(
                        condition_entry_start
                    ),
                })
            return None
        cursor = next_cursor + 1
        if cursor < limit and data[cursor] == 0xFF:
            condition_decoded = ({
                "type": "NullGameCondition",
                "conditionUnionTag": None,
                "conditionUnionTagEncoding": "memorypack-null",
                "serializedMemberCount": None,
                "conditionOffset": cursor,
                "conditionOffsetHex": _offset_hex(cursor),
                "conditionEndOffset": cursor + 1,
                "conditionEndOffsetHex": _offset_hex(cursor + 1),
                "nativeMappingId": LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
            }, cursor + 1)
        else:
            condition_decoded = _decode_levelscript_task_condition(
                data,
                cursor,
                limit,
            )
        if condition_decoded is None:
            if diagnostics is not None and not diagnostics:
                header = _decode_task_condition_union_header(
                    data,
                    cursor,
                    limit,
                )
                union_tag = header[0] if header is not None else None
                member_count = header[1] if header is not None else None
                expected = (
                    LEVELSCRIPT_TASK_CONDITION_TAGS.get(union_tag)
                    if isinstance(union_tag, int)
                    else None
                )
                diagnostics.append({
                    "gate": (
                        "supportedConditionPayloadLayout"
                        if expected is not None
                        else "supportedConditionUnionTag"
                    ),
                    "taskKey": task_key,
                    "conditionKey": condition_key,
                    "conditionIndex": len(conditions),
                    "conditionOffset": cursor,
                    "conditionOffsetHex": _offset_hex(cursor),
                    "conditionUnionTag": (
                        f"0x{union_tag:04x}"
                        if isinstance(union_tag, int) else None
                    ),
                    "serializedMemberCount": member_count,
                    "expectedConditionType": (
                        expected[0] if expected is not None else None
                    ),
                    "expectedSerializedMemberCount": (
                        expected[1] if expected is not None else None
                    ),
                    "payloadHexPrefix": data[cursor : cursor + 48].hex(" "),
                    "nativeMappingId": LEVELSCRIPT_TASK_CONDITION_MAPPING_ID,
                })
            return None
        condition, cursor = condition_decoded
        if (
            (
                condition.get("type") != "NullGameCondition"
                and condition.get("uniqueId") != condition_key
            )
            or cursor + 5 > limit
            or data[cursor] not in (0, 1)
        ):
            return None
        is_main_objective = bool(data[cursor])
        objective_enum = struct.unpack_from("<i", data, cursor + 1)[0]
        cursor += 5
        if objective_enum < 0 or objective_enum > 0x100:
            return None
        conditions.append({
            "conditionKey": condition_key,
            "conditionEntryOffset": condition_entry_start,
            "conditionEntryOffsetHex": _offset_hex(condition_entry_start),
            "taskConditionMemberCount": 3,
            "isMainObjective": is_main_objective,
            "objectiveEnum": objective_enum,
            "condition": condition,
        })

    if cursor + 5 > limit or data[cursor] not in (0, 1):
        return None
    need_manual_check = bool(data[cursor])
    task_type = struct.unpack_from("<i", data, cursor + 1)[0]
    cursor += 5
    if task_type < 0 or task_type > 0x100:
        return None
    return {
        "taskKey": task_key,
        "taskEntryOffset": start,
        "taskEntryOffsetHex": _offset_hex(start),
        "taskEntryEndOffset": cursor,
        "taskEntryEndOffsetHex": _offset_hex(cursor),
        "taskDataMemberCount": task_data_member_count,
        "canBeTracked": can_be_tracked,
        "conditionDictCount": condition_count,
        "conditions": conditions,
        "needManualCheck": need_manual_check,
        "taskType": task_type,
    }, cursor


def decode_levelscript_task_conditions(
    data: bytes,
    script_id: int | str,
    *,
    diagnostics: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Recover only completely bounded LevelScript task-condition maps.

    The task dictionary begins at an exact validated top-level tail candidate.
    Every declared task and condition must decode in sequence, including its
    IDs and trailing fields.  When a trigger-volume dictionary follows, its
    exact offset is also required to equal the parsed task-map end.  Missing
    later top-level members are allowed only after the declared task count has
    parsed completely.  Results are dependency/evaluation evidence, never
    mission ownership or Story order.
    """
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return []
    if not data or data[0] not in (26, 27) or len(data) < 8:
        return []

    parsed_hosts: list[dict[str, Any]] = []
    for script_id_offset in _u64_offsets(data, numeric_script_id):
        host = _tail_candidate(data, script_id_offset)
        task_count = host.get("taskMapCount")
        task_map_offset = host.get("taskMapOffset")
        if (
            not host.get("startTypeName")
            or host.get("taskMapStatus") != "present"
            or not isinstance(task_count, int)
            or not isinstance(task_map_offset, int)
            or task_count <= 0
            or task_count > 128
        ):
            continue
        cursor = task_map_offset + 4
        trigger_offset = host.get("triggerVolumesOffset")
        limit = (
            int(trigger_offset)
            if isinstance(trigger_offset, int) and trigger_offset > cursor
            else len(data)
        )
        tasks: list[dict[str, Any]] = []
        valid = True
        for _ in range(task_count):
            decoded = _decode_levelscript_task_entry(
                data,
                cursor,
                limit,
                diagnostics,
            )
            if decoded is None:
                valid = False
                break
            task, cursor = decoded
            tasks.append(task)
        if not valid:
            continue
        if isinstance(trigger_offset, int) and cursor != trigger_offset:
            continue
        parsed_hosts.append({
            "scriptId": str(numeric_script_id),
            "levelScriptSerializedMemberCount": data[0],
            "scriptIdOffset": script_id_offset,
            "scriptIdOffsetHex": _offset_hex(script_id_offset),
            "startType": str(host.get("startTypeName") or ""),
            "taskMapOffset": task_map_offset,
            "taskMapOffsetHex": _offset_hex(task_map_offset),
            "taskMapCount": task_count,
            "taskMapEndOffset": cursor,
            "taskMapEndOffsetHex": _offset_hex(cursor),
            "taskMapBoundaryStatus": (
                "exact_trigger_volumes_offset"
                if isinstance(trigger_offset, int)
                else "exact_declared_task_count"
            ),
            "triggerVolumesStatus": str(
                host.get("triggerVolumesStatus") or "missing"
            ),
            "triggerVolumesOffset": trigger_offset,
            "triggerVolumesOffsetHex": _offset_hex(trigger_offset),
            "tasks": tasks,
            "payloadShape": (
                "validated-top-level-task-map-complete-supported-"
                "gameconditions"
            ),
        })

    signatures: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in parsed_hosts:
        signature = (
            row["scriptIdOffset"],
            row["taskMapOffset"],
            row["taskMapEndOffset"],
            tuple(
                (
                    task["taskKey"],
                    tuple(
                        (
                            condition["conditionKey"],
                            condition["condition"]["conditionUnionTag"],
                            condition["condition"]["conditionEndOffset"],
                        )
                        for condition in task["conditions"]
                    ),
                )
                for task in row["tasks"]
            ),
        )
        signatures.setdefault(signature, row)
    return list(signatures.values()) if len(signatures) == 1 else []


def decode_levelscript_task_mission_state_dependencies(
    data: bytes,
    script_id: int | str,
) -> list[dict[str, Any]]:
    """Recover structurally complete task-map mission-state conditions.

    This first narrow implementation supports the current-build top-level
    layout whose task map is followed by a null trigger-volume dictionary at
    EOF.  It scans only the uniquely validated task-map interval and accepts
    only complete one-condition task envelopes.  The result is dependency
    evidence, never a Story control path or mission owner.
    """
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return []
    if (
        not data
        or data[0] not in (26, 27)
        or len(data) < 8
        or data[-4:] != b"\x00\x00\x00\x00"
    ):
        return []
    tail_candidates = [
        _tail_candidate(data, offset)
        for offset in _u64_offsets(data, numeric_script_id)
    ]
    task_hosts = [
        candidate
        for candidate in tail_candidates
        if candidate.get("startTypeName")
        and candidate.get("taskMapStatus") == "present"
        and isinstance(candidate.get("taskMapOffset"), int)
        and isinstance(candidate.get("taskMapCount"), int)
        and 0 < int(candidate["taskMapCount"]) <= 128
    ]
    if len(task_hosts) != 1:
        return []
    host = task_hosts[0]
    task_map_offset = int(host["taskMapOffset"])
    task_map_count = int(host["taskMapCount"])
    task_map_start = task_map_offset + 4
    task_map_end = len(data) - 4
    if task_map_start >= task_map_end:
        return []

    candidates: list[dict[str, Any]] = []
    for offset in range(task_map_start, task_map_end):
        decoded = _decode_levelscript_single_condition_task_mission_state(
            data,
            offset,
            task_map_end,
        )
        if decoded is None:
            continue
        row, cursor = decoded
        if cursor != task_map_end and not _looks_like_levelscript_task_entry_prefix(
            data,
            cursor,
            task_map_end,
        ):
            continue
        candidates.append({
            **row,
            "scriptId": str(numeric_script_id),
            "levelScriptSerializedMemberCount": data[0],
            "startType": str(host.get("startTypeName") or ""),
            "taskMapOffset": task_map_offset,
            "taskMapOffsetHex": _offset_hex(task_map_offset),
            "taskMapCount": task_map_count,
            "taskMapEndOffset": task_map_end,
            "taskMapEndOffsetHex": _offset_hex(task_map_end),
            "triggerVolumesStatus": "empty",
            "triggerVolumesOffset": task_map_end,
            "triggerVolumesOffsetHex": _offset_hex(task_map_end),
            "payloadShape": (
                "validated-top-level-task-map-single-check-mission-state-"
                "task-and-null-trigger-volumes-eof"
            ),
        })
    signatures = [
        (
            row["taskKey"],
            row["conditionKey"],
            row["taskEntryOffset"],
        )
        for row in candidates
    ]
    if len(signatures) != len(set(signatures)):
        return []
    return sorted(candidates, key=lambda row: row["taskEntryOffset"])


def decode_levelscript_binary_summary(data: bytes, script_id: int) -> dict[str, Any]:
    """Decode stable top-level LevelScriptData facts from a raw blob.

    This intentionally handles only fields whose byte positions can be verified
    cheaply from the IL2CPP MemoryPack setter order. It does not parse action
    records or promote start/end semantics into order edges.
    """
    if not data or script_id <= 0:
        return {}
    action_map = decode_levelscript_action_map_header(data)
    offsets = _u64_offsets(data, script_id)
    candidates = [_tail_candidate(data, offset) for offset in offsets]
    best = max(candidates, key=lambda item: int(item.get("score") or 0), default={})
    active_shapes = decode_levelscript_active_shape_list(data, script_id)
    return {
        "serializedMemberCount": data[0],
        "expectedMemberCount": 27,
        "actionMapStatus": action_map.get("status") or "",
        "actionMapRecordCount": action_map.get("recordCount"),
        "actionMapRecordStartOffsetHex": action_map.get("recordStartOffsetHex") or "",
        "actionMapHeader": action_map,
        "scriptId": str(script_id),
        "scriptIdOffsets": [f"0x{offset:x}" for offset in offsets],
        "scriptIdOccurrenceCount": len(offsets),
        "scriptIdVerified": bool(offsets),
        "probableScriptIdOffset": best.get("scriptIdOffset"),
        "probableScriptIdOffsetHex": best.get("scriptIdOffsetHex") or "",
        "activeShapeList": active_shapes,
        "activeShapeListStatus": active_shapes.get("status") or "",
        "activeShapeListCount": active_shapes.get("count"),
        "activeShapeListShapes": active_shapes.get("shapes") or [],
        "startShapeListStatus": best.get("startShapeListStatus") or "",
        "startShapeListCount": best.get("startShapeListCount"),
        "startShapeListDetails": best.get("startShapeList") or {},
        "startShapeListShapes": (best.get("startShapeList") or {}).get("shapes") or [],
        "startTypeOffset": best.get("startTypeOffset"),
        "startTypeOffsetHex": best.get("startTypeOffsetHex") or "",
        "startTypeRaw": best.get("startTypeRaw"),
        "startTypeName": best.get("startTypeName") or "",
        "taskMapOffsetHex": best.get("taskMapOffsetHex") or "",
        "taskMapStatus": best.get("taskMapStatus") or "",
        "taskMapCount": best.get("taskMapCount"),
        "triggerVolumesOffsetHex": best.get("triggerVolumesOffsetHex") or "",
        "triggerVolumesStatus": best.get("triggerVolumesStatus") or "",
        "triggerVolumesCount": best.get("triggerVolumesCount"),
        "triggerVolumesDetails": best.get("triggerVolumes") or {},
        "triggerVolumeSlotIds": (best.get("triggerVolumes") or {}).get("slotIds") or [],
        "note": (
            "current 27-member top-level MemoryPack plus actionMap header and "
            "unique active shape, scriptId/startType/shape-list trigger fields decoded; "
            "final current-build Leader trigger-volume maps include exact slot and geometry; "
            "action start/end opcodes are still not decoded"
        ),
    }


def decode_levelscript_binary_file(path: Path, script_id: int | str) -> dict[str, Any]:
    try:
        numeric_script_id = int(script_id)
    except (TypeError, ValueError):
        return {}
    try:
        data = read_bytes_cached(path)
    except OSError:
        return {}
    return decode_levelscript_binary_summary(data, numeric_script_id)


def classify_local_trigger_volume_context(
    decoded: dict[str, Any],
    selector_slot_ids: list[int],
    *,
    trigger_volume_type: str = "Leader",
) -> dict[str, Any]:
    """Resolve typed event selectors to exact same-LevelScript volumes.

    The join is deliberately identifier-agnostic: callers supply selector
    slots decoded from a typed event payload, and this function validates the
    current MemoryPack trigger-volume schema before matching those slots.  The
    serialized volume has no dynamic-scene, mission, or quest foreign key, so
    a successful result proves local playback geometry only.
    """
    unique_slots = sorted({
        slot_id
        for slot_id in selector_slot_ids
        if isinstance(slot_id, int)
        and not isinstance(slot_id, bool)
        and slot_id > 0
    })
    details = decoded.get("triggerVolumesDetails") or {}
    volumes = details.get("volumes") or []
    expected_union_tags = {
        union_tag
        for union_tag, name in LEVELSCRIPT_TRIGGER_VOLUME_UNION_TAG_NAMES.items()
        if name == trigger_volume_type
    }
    matches: list[dict[str, Any]] = []
    ambiguous_slots: list[int] = []
    for slot_id in unique_slots:
        candidates = [
            volume
            for volume in volumes
            if isinstance(volume, dict)
            and volume.get("slotId") == slot_id
            and volume.get("keySlotId") == slot_id
            and volume.get("triggerVolumeType") == trigger_volume_type
            and volume.get("unionTag") in expected_union_tags
            and volume.get("memberCount")
            == len(LEVELSCRIPT_TRIGGER_VOLUME_SERIALIZED_FIELDS)
            and isinstance(volume.get("shapeList"), dict)
            and volume["shapeList"].get("status") == "present"
            and volume["shapeList"].get("parseStatus") == "decoded"
            and bool(volume["shapeList"].get("shapes"))
        ]
        if len(candidates) == 1:
            matches.append(candidates[0])
        elif len(candidates) > 1:
            ambiguous_slots.append(slot_id)
    matched_slots = sorted(int(volume["slotId"]) for volume in matches)
    missing_slots = sorted(set(unique_slots) - set(matched_slots))
    exact = (
        bool(unique_slots)
        and decoded.get("scriptIdVerified") is True
        and decoded.get("triggerVolumesStatus") == "present"
        and details.get("parseStatus") == "decoded"
        and not missing_slots
        and not ambiguous_slots
        and len(matches) == len(unique_slots)
    )
    return {
        "status": (
            "exact_local_levelscript_trigger_volume_without_foreign_identity"
            if exact
            else "unresolved_local_levelscript_trigger_volume"
        ),
        "selectorSlotIds": unique_slots,
        "matchedSlotIds": matched_slots,
        "missingSlotIds": missing_slots,
        "ambiguousSlotIds": ambiguous_slots,
        "triggerVolumesStatus": decoded.get("triggerVolumesStatus") or "",
        "triggerVolumesParseStatus": details.get("parseStatus") or "",
        "triggerVolumesOffsetHex": decoded.get("triggerVolumesOffsetHex") or "",
        "topLevelSerializedMemberCount": decoded.get("serializedMemberCount"),
        "scriptIdVerified": bool(decoded.get("scriptIdVerified")),
        "triggerVolumes": matches,
        "schema": {
            "baseType": "Beyond.Gameplay.LevelScriptTriggerVolumeData",
            "baseDeclaredFieldCount": len(LEVELSCRIPT_TRIGGER_VOLUME_BASE_FIELDS),
            "baseDeclaredFields": LEVELSCRIPT_TRIGGER_VOLUME_BASE_FIELDS,
            "leaderType": (
                "Beyond.Gameplay.LevelScriptTriggerVolumeDataForLeader"
                if trigger_volume_type == "Leader"
                else ""
            ),
            "leaderDeclaredFieldCount": 0 if trigger_volume_type == "Leader" else None,
            "serializedMemberCount": len(
                LEVELSCRIPT_TRIGGER_VOLUME_SERIALIZED_FIELDS
            ),
            "serializedFields": LEVELSCRIPT_TRIGGER_VOLUME_SERIALIZED_FIELDS,
            "mappingId": LEVELSCRIPT_TRIGGER_VOLUME_SCHEMA_MAPPING_ID,
        },
        "dynamicSceneIdentityFieldPresent": False,
        "missionOrQuestIdentityFieldPresent": False,
        "foreignKeyBridgeFound": False,
        "missionGraphAction": "none",
    }
