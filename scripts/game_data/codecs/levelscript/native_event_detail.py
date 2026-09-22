"""Exact codec for the named native event payload detail.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

import struct

from scripts.game_data.codecs.levelscript import entity_cast_and_death_events as levelscript_entity_events
from scripts.game_data.codecs.levelscript import entity_event_scope as levelscript_entity_event_scope
from scripts.game_data.codecs.levelscript import params as levelscript_params
from scripts.game_data.codecs.levelscript import proxy_patrol_checkpoint as levelscript_proxy_patrol
from scripts.game_data.codecs.levelscript import script_event_scope as levelscript_script_event_scope
from scripts.game_data.codecs.levelscript import script_stage_changed as levelscript_script_stage_changed
from scripts.game_data.codecs.levelscript import spawner_events as levelscript_spawner_events
from scripts.game_data.codecs.levelscript.condition_getters import _decode_encounter_lsm_fields
from scripts.game_data.codecs.levelscript.condition_getters import _decode_leader_trigger_volume_fields
from scripts.game_data.codecs.levelscript.condition_getters import _decode_leader_trigger_volume_list_fields
from scripts.game_data.codecs.levelscript.condition_getters import _decode_npc_patrol_checkpoint_fields
from scripts.game_data.codecs.levelscript.condition_getters import _decode_script_variable_changed_fields
from scripts.game_data.codecs.levelscript.condition_getters import _decode_scripted_char_patrol_fields
from scripts.game_data.codecs.levelscript.condition_params import _decode_levelscript_ptr_param
from scripts.game_data.codecs.levelscript.framing_common import _drop_empty
from scripts.game_data.codecs.levelscript.framing_common import _round_float
from scripts.game_data.codecs.levelscript.params import decode_bool_param as _decode_bool_param
from scripts.game_data.codecs.levelscript.params import decode_i32_param as _decode_i32_param
from scripts.game_data.codecs.levelscript.params import decode_param_tail as _decode_param_tail
from scripts.game_data.codecs.levelscript.record_hints import LEVELSCRIPT_NATIVE_EVENT_PAYLOAD_MAPPING_ID
from typing import Any

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
        scope = levelscript_script_event_scope.decode_script_event_header_scope(payload)
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
        scope = levelscript_script_event_scope.decode_script_event_header_scope(payload)
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
        stage_fields = levelscript_script_stage_changed.decode_script_stage_changed_fields(
            payload,
            native_header_name,
        )
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
            entity_scope = levelscript_entity_event_scope.decode_entity_event_header_scope(payload)
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
        spawner_fields = levelscript_spawner_events.decode_spawner_event_fields(
            payload,
            native_header_name,
        )
        if spawner_fields:
            detail = {
                "type": native_header_name,
                **spawner_fields,
                "groupKeyOutputRefs": refs("groupKeyOutput"),
                "spawnerOutputRefs": refs("spawnerOutput"),
                "transport": "local-spawner-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "payloadDecodeStatus": "exact_complete_subtype",
                "summary": f"spawner group begin {spawner_fields.get('groupKeyFilter') or ''}",
            }
        elif refs("groupKeyOutput") or refs("spawnerOutput") or literal_texts:
            detail = {
                "type": native_header_name,
                "observedLiteralTexts": literal_texts,
                "groupKeyOutputRefs": refs("groupKeyOutput"),
                "spawnerOutputRefs": refs("spawnerOutput"),
                "payloadDecodeStatus": "partial_known_fields",
                "_payloadSchemaStatus": "partial_known_fields",
                "summary": "spawner group begin with unresolved filter fields",
            }
    elif native_header_name == "LevelEvent_OnSpawnerWaveBegin":
        spawner_fields = levelscript_spawner_events.decode_spawner_event_fields(
            payload,
            native_header_name,
        )
        if spawner_fields:
            detail = {
                "type": native_header_name,
                **spawner_fields,
                "spawnerOutputRefs": refs("spawnerOutput"),
                "waveKeyOutputRefs": refs("waveKeyOutput"),
                "transport": "local-spawner-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "payloadDecodeStatus": "exact_complete_subtype",
                "summary": f"spawner wave begin {spawner_fields.get('waveKeyFilter') or ''}",
            }
        elif refs("spawnerOutput") or refs("waveKeyOutput") or literal_texts:
            detail = {
                "type": native_header_name,
                "observedLiteralTexts": literal_texts,
                "spawnerOutputRefs": refs("spawnerOutput"),
                "waveKeyOutputRefs": refs("waveKeyOutput"),
                "payloadDecodeStatus": "partial_known_fields",
                "_payloadSchemaStatus": "partial_known_fields",
                "summary": "spawner wave begin with unresolved filter fields",
            }
    elif native_header_name == "LevelEvent_OnSpawnerComplete":
        spawner_fields = levelscript_spawner_events.decode_spawner_event_fields(
            payload,
            native_header_name,
        )
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
        spawner_fields = levelscript_spawner_events.decode_spawner_event_fields(
            payload,
            native_header_name,
        )
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
        spawner_fields = levelscript_spawner_events.decode_spawner_event_fields(
            payload,
            native_header_name,
        )
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
    elif native_header_name in {
        "LevelEvent_OnSpawnerStart",
        "LevelEvent_OnSpawnerPause",
        "LevelEvent_OnSpawnerGroupComplete",
        "LevelEvent_OnSpawnerWaveComplete",
    }:
        spawner_fields = levelscript_spawner_events.decode_spawner_event_fields(
            payload,
            native_header_name,
        )
        if spawner_fields:
            detail = {
                "type": native_header_name,
                **spawner_fields,
                "transport": "local-spawner-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"{native_header_name.removeprefix('LevelEvent_On')} "
                    f"for spawner {spawner_fields['spawnerFilterId']}"
                ),
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
                    f"patrol {patrol_fields.get('patrolIdFilter', 'runtime')} "
                    f"checkpoint {patrol_fields.get('checkpointIndexFilter', 'runtime')}"
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
    elif native_header_name == levelscript_entity_events.ENTITY_CAST_SKILL:
        skill_fields = levelscript_entity_events.decode_entity_event_fields(
            payload,
            native_header_name,
        )
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
    elif native_header_name == levelscript_entity_events.ANY_ENTITY_DIE:
        any_die_fields = levelscript_entity_events.decode_entity_event_fields(
            payload,
            native_header_name,
        )
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
    elif native_header_name == levelscript_entity_events.SPECIFIC_ENTITY_DIE:
        entity_fields = levelscript_entity_events.decode_entity_event_fields(
            payload,
            native_header_name,
        )
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
    elif native_header_name in {
        "LevelEvent_OnEncounterActivated",
        "LevelEvent_OnEncounterBattlePartBegin",
    }:
        encounter_fields = _decode_encounter_lsm_fields(payload)
        if encounter_fields:
            detail = {
                "type": native_header_name,
                **encounter_fields,
                "lsmPtrOutputRefs": refs("lsmPtrOutput"),
                "transport": "local-encounter-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"{native_header_name.removeprefix('LevelEvent_On')} for "
                    f"Encounter module {encounter_fields['lsmPtrFilter']}"
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
        entity_scope = levelscript_entity_event_scope.decode_entity_event_header_scope(payload)
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
    elif native_header_name == levelscript_proxy_patrol.EVENT_NAME:
        patrol_fields = levelscript_proxy_patrol.decode_proxy_patrol_checkpoint_event(
            payload,
            levelscript_proxy_patrol.EVENT_SEMANTIC_KEY,
            header_role=True,
        )
        if patrol_fields:
            detail = {
                "type": native_header_name,
                **patrol_fields,
                "transport": "local-proxy-patrol-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"NPC proxy {patrol_fields['proxyIdFilter']} reaches patrol "
                    f"{patrol_fields['patrolIdFilter']} point "
                    f"{patrol_fields['pointIndexFilter']}"
                ),
            }
    elif native_header_name == levelscript_entity_events.SPECIFIC_ENTITY_LIST_DIE:
        list_die_fields = levelscript_entity_events.decode_entity_event_fields(
            payload,
            native_header_name,
        )
        if list_die_fields:
            detail = {
                "type": native_header_name,
                **list_die_fields,
                "entityOutputRefs": refs("entity"),
                "transport": "local-entity-lifecycle-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    "matching entity in a "
                    f"{len(list_die_fields['entityListFilter'])}-member specific list dies"
                ),
            }
    elif native_header_name == levelscript_entity_events.ENEMY_IN_FIGHT:
        fight_fields = levelscript_entity_events.decode_entity_event_fields(
            payload,
            native_header_name,
        )
        if fight_fields:
            detail = {
                "type": native_header_name,
                **fight_fields,
                "entityOutputRefs": refs("entity"),
                "transport": "local-entity-combat-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    f"matching entity in a {len(fight_fields['entityListFilter'])}-member "
                    "constant list enters combat"
                ),
            }
    elif native_header_name in {
        "EntityEvent_OnBeingScanned",
        "EntityEvent_OnEntityDestroy",
        "EntityEvent_OnEntityStart",
        "EntityEvent_OnHpChanged",
        "EntityEvent_OnIntUnlocked",
        "EntityEvent_OnIntUnlockFailed",
    }:
        # The inherited EntityEventHeader selector is independently exact even
        # when this subtype's trailing members are not yet named.  Preserve a
        # narrower schema status so consumers may use only the specified
        # constant EntityPtr and cannot mistake the subtype for fully decoded.
        entity_scope = levelscript_entity_event_scope.decode_entity_event_header_scope(payload)
        entity_scope.pop("_subtypeOffset", None)
        if entity_scope:
            target = entity_scope["targetEntity"]
            target_param = entity_scope["targetEntityParam"]
            receiver = (
                f"entity slot {target.get('slotId')}"
                if target.get("useSlotId")
                else f"entity {target.get('logicId')}"
                if target.get("logicId")
                else f"entity pointer {target_param.get('path')}"
                if target_param.get("path")
                else "selected entity"
            )
            detail = {
                "type": native_header_name,
                **entity_scope,
                "transport": "local-entity-runtime-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": f"{receiver} receives {native_header_name}",
                "_payloadSchemaStatus": "exact_current_build_entity_event_scope_fields",
            }
    elif native_header_name == "EntityEvent_OnInteractiveStateChanged":
        entity_scope = levelscript_entity_event_scope.decode_entity_event_header_scope(payload)
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
        entity_scope = levelscript_entity_event_scope.decode_entity_event_header_scope(payload)
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
        entity_scope = levelscript_entity_event_scope.decode_entity_event_header_scope(payload)
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
    elif native_header_name == "ScriptEvent_OnLeaderEnterTriggerVolumeList":
        trigger_fields = _decode_leader_trigger_volume_list_fields(payload)
        if trigger_fields:
            detail = {
                "type": native_header_name,
                **trigger_fields,
                "transport": "local-authored-trigger-volume-event",
                "serverExchange": False,
                "serializedMissionOrQuestId": False,
                "summary": (
                    "leader enters one of trigger slots "
                    + ", ".join(
                        str(slot_id)
                        for slot_id in trigger_fields["triggerSlotIdFilters"]
                    )
                ),
            }
    if not detail:
        return {}
    detail.setdefault("payloadDecodeStatus", "exact_complete_subtype")
    detail["payloadSchemaStatus"] = detail.pop(
        "_payloadSchemaStatus",
        "exact_current_build_memorypack_fields",
    )
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


def _decode_wait_for_seconds_in_trigger_volume_action(
    payload: bytes,
) -> dict[str, Any]:
    """Decode the inherited success/fail targets and trigger receiver exactly."""
    if len(payload) < 10 or payload[0] != 0xFF:
        return {}
    fail_id = struct.unpack_from("<i", payload, 1)[0]
    seconds = levelscript_params.decode_float_param(payload, 5)
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
