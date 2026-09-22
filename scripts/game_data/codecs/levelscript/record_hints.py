"""Reviewed per-record naming tables for LevelScript action-map records.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

from collections import Counter
from scripts.common import RECORDED_NATIVE_GAMEASSEMBLY_SHA256
from scripts.common import RECORDED_NATIVE_METADATA_SHA256
from scripts.game_data.codecs.levelscript.framing_common import _record_start
from typing import Any

# Exact current-build ActionHeader identities recovered from the installed
# ActionHeaderForMemoryPack formatter and global-metadata.dat. Keep this table
# version-scoped: historical exports use different serialized codes for some
# of the same event classes (notably OnDialogExit).
LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionheader"
)


LEVELSCRIPT_NATIVE_HEADER_CONTRACT_SCHEMA = "levelScriptNativeHeaderContract.v1"


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
    (0x0085, 0x15): "LevelEvent_OnProxyPatrolCheckpointReach",
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


def levelscript_native_header_contract(
    gameassembly_sha256: str,
    metadata_sha256: str,
) -> dict[str, Any]:
    """Gate the recorded ActionHeader union registry to its exact build."""
    gameassembly_sha256 = str(gameassembly_sha256 or "").upper()
    metadata_sha256 = str(metadata_sha256 or "").upper()
    missing = [
        label
        for label, value in (
            ("GameAssembly.dll", gameassembly_sha256),
            ("global-metadata.dat", metadata_sha256),
        )
        if not value
    ]
    mismatches = [
        {
            "source": label,
            "expected": expected,
            "actual": actual,
        }
        for label, actual, expected in (
            (
                "GameAssembly.dll",
                gameassembly_sha256,
                RECORDED_NATIVE_GAMEASSEMBLY_SHA256,
            ),
            (
                "global-metadata.dat",
                metadata_sha256,
                RECORDED_NATIVE_METADATA_SHA256,
            ),
        )
        if actual and actual != expected
    ]
    status = "missing" if missing else "mismatched" if mismatches else "validated"
    return {
        "schema": LEVELSCRIPT_NATIVE_HEADER_CONTRACT_SCHEMA,
        "mappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
        "status": status,
        "sources": {
            "gameAssemblySha256": gameassembly_sha256,
            "globalMetadataSha256": metadata_sha256,
        },
        "missing": missing,
        "mismatches": mismatches,
    }


def summarize_levelscript_native_header_records(
    records: list[dict[str, Any]],
    memberships: dict[int, str],
    *,
    names: set[str],
) -> list[dict[str, Any]]:
    """Summarize exact header-list records selected by the native registry."""
    counts: Counter[tuple[int, int, str]] = Counter()
    for record in records:
        role = str(memberships.get(_record_start(record)) or "")
        if not role.startswith("headerList"):
            continue
        union_tag, member_count = levelscript_record_semantic_key(record)
        header_name = LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES.get(union_tag, "")
        if header_name in names:
            counts[(union_tag, member_count, header_name)] += 1
    return [
        {
            "headerTagHex": f"0x{union_tag:04x}",
            "serializedMemberCount": member_count,
            "headerName": header_name,
            "count": count,
            "headerListCount": count,
            "headerTable": "Beyond_Gameplay_Actions_ActionHeader",
            "nativeHeaderMappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
        }
        for (union_tag, member_count, header_name), count in sorted(counts.items())
    ]


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
    (0x04F5, 0x0A): {
        "label": "actionbase-treasure-hunt-config",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to TreasureHuntConfigAction",
        "actionBaseAction": "TreasureHuntConfigAction",
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
        "label": "actionbase-load-level-sequence",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "LoadLevelSequenceAction"
        ),
        "actionBaseAction": "LoadLevelSequenceAction",
    },
    (0x030E, 0x09): {
        "label": "actionbase-manually-start-guide-group",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to ManuallyStartGuideGroup",
        "actionBaseAction": "ManuallyStartGuideGroup",
    },
    (0x03A9, 0x09): {
        "label": "actionbase-restore-player-gait",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to RestorePlayerGait",
        "actionBaseAction": "RestorePlayerGait",
    },
    (0x0402, 0x09): {
        "label": "actionbase-set-enable-player-move-camera",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetEnablePlayerMoveCamera",
        "actionBaseAction": "SetEnablePlayerMoveCamera",
    },
    (0x050C, 0x09): {
        "label": "actionbase-wait-for-entity-start",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to WaitForEntityStart",
        "actionBaseAction": "WaitForEntityStart",
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


LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID = (
    "gameassembly-2026-07-17-memorypack-native-event-fields"
)


LEVELSCRIPT_NATIVE_AUDIO_ACTION_MAPPING_ID = (
    "gameassembly-2026-08-09-memorypack-audio-action-fields"
)


LEVELSCRIPT_NATIVE_LIST_GET_VALUE_STRING_MAPPING_ID = (
    "gameassembly-2026-08-11-memorypack-list-get-value-string-fields"
)


TRIGGER_VOLUME_RECORD_KEYS = {
    key
    for key, hint in LEVELSCRIPT_RECORD_HINTS.items()
    if str(hint.get("label") or "").startswith("trigger-volume")
    or str(hint.get("triggerRole") or "").startswith("trigger-volume")
}
