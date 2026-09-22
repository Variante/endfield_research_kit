"""Reviewed per-record naming tables for LevelScript action-map records.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

from collections import Counter
from scripts.game_data import levelscript_union_tags as union_tags
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
    union_tags.header_code("LevelEvent_OnCustomEvent"): "LevelEvent_OnCustomEvent",
    union_tags.header_code("LevelEvent_OnDialogEnter"): "LevelEvent_OnDialogEnter",
    union_tags.header_code("ScriptEvent_OnCustomEvent"): "ScriptEvent_OnCustomEvent",
    union_tags.header_code("ScriptEvent_OnLeaderEnterTriggerVolume"): "ScriptEvent_OnLeaderEnterTriggerVolume",
    union_tags.header_code("ScriptEvent_OnLeaderLeaveTriggerVolume"): "ScriptEvent_OnLeaderLeaveTriggerVolume",
    union_tags.header_code("LevelEvent_OnEntityHpChanged"): "LevelEvent_OnEntityHpChanged",
    union_tags.header_code("LevelEvent_OnDialogExit"): "LevelEvent_OnDialogExit",
    union_tags.header_code("LevelEvent_OnQuestStateChanged"): "LevelEvent_OnQuestStateChanged",
    union_tags.header_code("EntityEvent_OnInteractiveStateChanged"): "EntityEvent_OnInteractiveStateChanged",
}


# Canonical current-build identities. The older table above remains for
# report/tests that still carry the compact parser's combined observed pair.
LEVELSCRIPT_NATIVE_HEADER_TAG_NAMES: dict[tuple[int, int], str] = {
    union_tags.header("LevelEvent_OnCustomEvent"): "LevelEvent_OnCustomEvent",
    union_tags.header("LevelEvent_OnDialogEnter"): "LevelEvent_OnDialogEnter",
    union_tags.header("ScriptEvent_OnCustomEvent"): "ScriptEvent_OnCustomEvent",
    union_tags.header("ScriptEvent_OnLeaderEnterTriggerVolume"): "ScriptEvent_OnLeaderEnterTriggerVolume",
    union_tags.header("ScriptEvent_OnLeaderLeaveTriggerVolume"): "ScriptEvent_OnLeaderLeaveTriggerVolume",
    union_tags.header("LevelEvent_OnEntityHpChanged"): "LevelEvent_OnEntityHpChanged",
    union_tags.header("LevelEvent_OnDialogExit"): "LevelEvent_OnDialogExit",
    union_tags.header("LevelEvent_OnQuestStateChanged"): "LevelEvent_OnQuestStateChanged",
    union_tags.header("LevelEvent_OnProxyPatrolCheckpointReach"): "LevelEvent_OnProxyPatrolCheckpointReach",
    union_tags.header("EntityEvent_OnInteractiveStateChanged"): "EntityEvent_OnInteractiveStateChanged",
}


# Complete current-build ActionHeaderForMemoryPack union registration table.
# GameAssembly cctor VA 0x1843bb480 registers contiguous tags 0x0000..0x00e5
# through helper 0x183ead480. Union identity is selected by the tag; the
# concrete subtype member count remains separately retained on decoded records
# as a payload-shape guard.
LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES: dict[int, str] = {
    tag: name for (tag, _members), name in union_tags.names("ActionHeader").items()
}


def levelscript_native_header_contract(
    gameassembly_sha256: str,
    metadata_sha256: str,
) -> dict[str, Any]:
    """Gate the ActionHeader union registry to the build its tag contract names."""
    recorded = union_tags.contract_native_inputs()
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
                recorded["gameAssemblySha256"],
            ),
            (
                "global-metadata.dat",
                metadata_sha256,
                recorded["metadataSha256"],
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
    union_tags.action("Branch"): {
        "label": "actionbase-branch-sequence",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to Branch; "
            "GameAssembly Branch.Execute consumes _idList in index order"
        ),
        "actionBaseAction": "Branch",
    },
    union_tags.action("IfElseAction"): {
        "label": "actionbase-if-else",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to IfElseAction",
        "actionBaseAction": "IfElseAction",
    },
    union_tags.action("SwitchInt"): {
        "label": "actionbase-switch-int",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SwitchInt",
        "actionBaseAction": "SwitchInt",
    },
    union_tags.action("SwitchIntLarger"): {
        "label": "actionbase-switch-int-larger",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "SwitchIntLarger; its Execute body selects serialized case/default ids"
        ),
        "actionBaseAction": "SwitchIntLarger",
    },
    union_tags.action("SwitchString"): {
        "label": "actionbase-switch-string",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "SwitchString; generated setters serialize _caseIDList, "
            "_caseValueList, _defaultID, then _value"
        ),
        "actionBaseAction": "SwitchString",
    },
    union_tags.action("Split"): {
        "label": "actionbase-split",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to Split",
        "actionBaseAction": "Split",
    },
    union_tags.action("WaitForOneFrame"): {
        "label": "actionbase-wait-one-frame",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to WaitForOneFrame",
        "actionBaseAction": "WaitForOneFrame",
    },
    union_tags.action("TreasureHuntConfigAction"): {
        "label": "actionbase-treasure-hunt-config",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to TreasureHuntConfigAction",
        "actionBaseAction": "TreasureHuntConfigAction",
    },
    union_tags.action("WaitForSecondsInTriggerVolume"): {
        "label": "actionbase-wait-seconds-trigger-volume",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "WaitForSecondsInTriggerVolume; inherited generated setters expose "
            "_failID, _seconds, and _successID before _scriptPtr and _triggerSlotId"
        ),
        "actionBaseAction": "WaitForSecondsInTriggerVolume",
    },
    union_tags.action("MainCharMoveTo"): {
        "label": "actionbase-main-char-move-to",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "MainCharMoveTo; generated setters name _endPos and _groundedMoveGait"
        ),
        "actionBaseAction": "MainCharMoveTo",
    },
    union_tags.action("ToggleClearScreenButRadio"): {
        "label": "actionbase-toggle-clear-screen-but-radio",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "ToggleClearScreenButRadio; its generated setter names _isShow"
        ),
        "actionBaseAction": "ToggleClearScreenButRadio",
        "presentationRole": "toggle-clear-screen-but-radio",
    },
    union_tags.action("PreloadCutsceneAction"): {
        "label": "actionbase-preload-cutscene",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to PreloadCutsceneAction",
        "actionBaseAction": "PreloadCutsceneAction",
    },
    union_tags.action("RaiseCustomLevelEvent"): {
        "label": "actionbase-raise-custom-level-event",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to RaiseCustomLevelEvent",
        "actionBaseAction": "RaiseCustomLevelEvent",
    },
    union_tags.action("RaiseCustomScriptEvent"): {
        "label": "actionbase-raise-custom-script-event",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "RaiseCustomScriptEvent"
        ),
        "actionBaseAction": "RaiseCustomScriptEvent",
    },
    union_tags.action("LoadLevelSequenceAction"): {
        "label": "actionbase-load-level-sequence",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps this code to "
            "LoadLevelSequenceAction"
        ),
        "actionBaseAction": "LoadLevelSequenceAction",
    },
    union_tags.action("ManuallyStartGuideGroup"): {
        "label": "actionbase-manually-start-guide-group",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to ManuallyStartGuideGroup",
        "actionBaseAction": "ManuallyStartGuideGroup",
    },
    union_tags.action("RestorePlayerGait"): {
        "label": "actionbase-restore-player-gait",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to RestorePlayerGait",
        "actionBaseAction": "RestorePlayerGait",
    },
    union_tags.action("SetEnablePlayerMoveCamera"): {
        "label": "actionbase-set-enable-player-move-camera",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetEnablePlayerMoveCamera",
        "actionBaseAction": "SetEnablePlayerMoveCamera",
    },
    union_tags.action("WaitForEntityStart"): {
        "label": "actionbase-wait-for-entity-start",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to WaitForEntityStart",
        "actionBaseAction": "WaitForEntityStart",
    },
    union_tags.action("SetOverrideInteractDialog"): {
        "label": "actionbase-set-override-interact-dialog",
        "confidence": "high",
        "note": (
            "current installed ActionBase formatter tag maps the code to "
            "SetOverrideInteractDialog"
        ),
        "actionBaseAction": "SetOverrideInteractDialog",
    },
    union_tags.action("SetScriptTaskPtr"): {
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
    union_tags.action("SetCurrentTerminalReadingIndex"): {
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
    union_tags.action("ListAddValueEntityPtr"): {
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
    union_tags.action("ManualEndLevelScript"): {
        "label": "actionbase-manual-end-levelscript",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to ManualEndLevelScript",
        "levelScriptControlRole": "manual-end",
        "actionBaseAction": "ManualEndLevelScript",
    },
    union_tags.action("ManualStartLevelScript"): {
        "label": "actionbase-manual-start-levelscript",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to ManualStartLevelScript",
        "levelScriptControlRole": "manual-start",
        "actionBaseAction": "ManualStartLevelScript",
    },
    union_tags.action("SetBool"): {
        "label": "actionbase-set-bool",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetBool",
        "propertyRole": "property-setter",
        "propertyValueType": "bool",
        "actionBaseAction": "SetBool",
    },
    union_tags.action("SetInt"): {
        "label": "actionbase-set-int",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetInt",
        "propertyRole": "property-setter",
        "propertyValueType": "int",
        "actionBaseAction": "SetInt",
    },
    union_tags.action("SetIntIncrease"): {
        "label": "actionbase-set-int-increase",
        "confidence": "high",
        "note": "current installed ActionBase formatter tag maps this code to SetIntIncrease",
        "propertyRole": "property-setter",
        "propertyValueType": "int",
        "actionBaseAction": "SetIntIncrease",
    },
    union_tags.action("WhileAction"): {
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
