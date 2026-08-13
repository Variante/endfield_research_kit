import unittest
import json
import struct
import tempfile
from pathlib import Path
from unittest import mock


from scripts.story_builder import callserver_callbacks, mission_flow
from scripts.story_builder.codecs.levelscript.switch_actions import (
    decode_switch_action,
)
from scripts.story_builder.codecs.levelscript.exit_custom_performance import (
    decode_exit_level_custom_performance_action,
)
from scripts.story_builder.level_bindings import (
    LEVELSCRIPT_MISSIONISH_RE,
    _decode_uid_record,
    build_spawner_config_mission_index,
    classify_levelscript_record,
    _levelscript_native_control_paths_to_record,
    _prepare_levelscript_native_control_context,
    build_resolved_mission_tracking_context_rows,
    levelscript_native_action_name,
    match_pos_tracking_leader_trigger_context,
    match_tracking_point_inside_leader_trigger_context,
    match_levelscript_native_black_record,
    match_entity_tracking_native_entity_event_context,
    resolve_dynamic_hp_spawner_context,
)
from scripts.story_builder.levelscript_binary import (
    LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES,
    LEVELSCRIPT_NATIVE_HEADER_NAMES,
    compact_callserver_serialized_contract,
    decode_levelscript_record_payload,
    extract_levelscript_uid_records,
    levelscript_native_header_name,
)
from scripts.story_builder.mission_recovery import (
    enrich_source_backed_scene_edge_context,
    is_call_server_self_uid_callback,
    is_play_dialog_hide_non_identifier_payload,
    typed_cutscene_single_char_parameter_action,
    source_backed_call_server_callbacks_from_scene_graph,
    source_backed_hash_terminals_from_scene_graph,
)
from scripts.story_builder.callserver_callbacks import (
    validate_callserver_serialized_contract,
)


class MissionFlowLevelScriptEventTests(unittest.TestCase):
    def test_callserver_audit_carries_native_contract_failure(self):
        failed_contract = {
            "status": "mismatched",
            "sourceFile": "scripts/story_builder/native_contracts/callserver_callback.json",
            "sourceSha256": "test",
            "nativeContract": {},
            "validationFailures": [{
                "validator": "callServerCallbackNativeContract",
                "gate": "installed_native_inputs",
            }],
        }
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(
            callserver_callbacks.CALLSERVER_CALLBACK_CONTRACT_AUDIT,
            failed_contract,
            clear=True,
        ):
            report = callserver_callbacks.build_report(
                level_script_root=Path(temporary)
            )

        self.assertEqual("validation_failed", report["status"])
        self.assertEqual(1, report["summary"]["validationFailures"])
        self.assertEqual(
            "installed_native_inputs",
            report["validationFailures"][0]["gate"],
        )

    def test_sns_objective_tracking_is_typed_attachment_not_playback(self):
        hints = mission_flow._extract_tracking_hints({
            "objectiveList": [{
                "trackingInfoList": [{
                    "$type": (
                        "Beyond.Gameplay.SnsTrackingInfo, Gameplay.Beyond"
                    ),
                    "snsDialogId": "sns_testm1_1",
                }],
            }],
        })
        self.assertEqual([{
            "type": "SnsTrackingInfo",
            "snsDialogId": "sns_testm1_1",
            "objectiveIndex": 1,
            "trackingIndex": 0,
        }], hints)

        rows = mission_flow._objective_tracking_story_connections(hints)
        self.assertEqual(1, len(rows))
        self.assertEqual("sns_testm1_1", rows[0]["key"])
        self.assertEqual(
            "objective_tracking_story_reference",
            rows[0]["relation"],
        )
        self.assertEqual("context", rows[0]["direction"])
        self.assertEqual("tracking", rows[0]["phase"])
        self.assertEqual("native_typed_context", rows[0]["confidence"])
        self.assertIs(rows[0]["playback"], False)
        self.assertEqual(
            (
                "MissionRuntimeAsset.questDic[*].objectiveList[0]"
                ".trackingInfoList[0].snsDialogId"
            ),
            rows[0]["source"],
        )

    def test_timeline_scene_edges_receive_only_exact_graph_context(self):
        timeline = {
            "sourceBackedSceneEdges": [
                {
                    "from": "state",
                    "to": "dlg_testm1_1",
                    "kind": "levelscriptChain",
                },
                {
                    "from": "state",
                    "to": "dlg_testm1_2",
                    "kind": "levelscriptChain",
                },
            ],
        }
        graph = {
            "edges": [
                {
                    "from": "state",
                    "to": "dlg_testm1_1",
                    "kind": "levelscriptChain",
                    "sourceActions": ["StartDialogAction"],
                    "sourceActionClasses": ["play_dialog"],
                },
                {
                    "from": "state",
                    "to": "dlg_testm1_2",
                    "kind": "authoredDirect",
                    "sourceEvents": ["LevelEvent_OnCustomEvent"],
                },
            ],
        }
        self.assertEqual(
            1,
            enrich_source_backed_scene_edge_context(timeline, graph),
        )
        self.assertEqual(
            ["StartDialogAction"],
            timeline["sourceBackedSceneEdges"][0]["sourceActions"],
        )
        self.assertEqual(
            ["play_dialog"],
            timeline["sourceBackedSceneEdges"][0]["sourceActionClasses"],
        )
        self.assertNotIn(
            "sourceEvents",
            timeline["sourceBackedSceneEdges"][1],
        )

    def test_prepared_control_context_reuses_typed_record_decodes(self):
        header = {
            "code": 0x1052,
            "kind": 0,
            "start": 10,
            "localId": 1,
            "nextId": 0,
            "strings": [],
            "plainStrings": [],
        }
        first = {
            "code": 0x0357,
            "kind": 0x14,
            "start": 100,
            "localId": 2,
            "nextId": 3,
            "strings": [{"text": "cutscene_testm1_1"}],
            "plainStrings": [],
        }
        second = {
            "code": 0x0357,
            "kind": 0x14,
            "start": 200,
            "localId": 3,
            "nextId": -1,
            "strings": [{"text": "cutscene_testm1_2"}],
            "plainStrings": [],
        }
        data = bytes(300)
        records = [header, first, second]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 linked",
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 2}}
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ) as decoder:
            prepared = _prepare_levelscript_native_control_context(
                data,
                records,
                membership,
            )
            first_paths = _levelscript_native_control_paths_to_record(
                data,
                records,
                membership,
                first,
                prepared=prepared,
            )
            second_paths = _levelscript_native_control_paths_to_record(
                data,
                records,
                membership,
                second,
                prepared=prepared,
            )

        self.assertEqual([2], first_paths[0]["pathLocalIds"])
        self.assertEqual([2, 3], second_paths[0]["pathLocalIds"])
        self.assertEqual(
            [[3]],
            [
                [step["localId"] for step in path]
                for path in first_paths[0]["downstreamControlPaths"]
            ],
        )
        self.assertEqual(
            "exact_serialized_typed_reachability",
            first_paths[0]["downstreamControlStatus"],
        )
        self.assertEqual([], second_paths[0]["downstreamControlPaths"])
        self.assertEqual(3, decoder.call_count)

    def test_dynamic_hp_spawner_context_rejects_constant_entity_lists(self):
        self.assertEqual(
            {},
            resolve_dynamic_hp_spawner_context(
                {"sourceFile": "unused.bin"},
                {
                    "status": "exact_serialized_control_path",
                    "headerName": "LevelEvent_OnAnyEntityDie",
                    "eventDetail": {
                        "entityListFilter": [{"logicId": 2_100_021_214}],
                    },
                },
            ),
        )

    def test_current_play_remotecomm_action_is_native_playback(self):
        record = {
            "unionTag": 0x0365,
            "serializedMemberCount": 17,
        }
        self.assertEqual("PlayRemoteComm", levelscript_native_action_name(record))
        self.assertEqual("play_remotecomm", classify_levelscript_record(record))

    def test_raise_custom_script_event_decodes_current_script_receiver(self):
        event_key = "fx_show_formal"
        param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        event_args = b"\x04\x01" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4
        receiver = (
            b"\x04\x00"
            + b"\x00" * 15
            + (-1).to_bytes(4, "little", signed=True)
            + (1002).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        payload = (
            event_args
            + b"\x04"
            + len(event_key).to_bytes(4, "little")
            + event_key.encode("ascii")
            + param_tail
            + receiver
        )
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x0380,
            "kind": 0x0B,
            "unionTag": 0x0380,
            "serializedMemberCount": 11,
            "strings": [{"offset": 18, "text": event_key}],
        }

        decoded = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )["raiseCustomScriptEvent"]
        self.assertEqual("RaiseCustomScriptEvent", levelscript_native_action_name(record))
        self.assertEqual("raise_custom_event", classify_levelscript_record(record))
        self.assertEqual(event_key, decoded["eventKey"])
        self.assertEqual("current_script", decoded["receiverMode"])
        self.assertNotIn("targetScriptId", decoded)
        self.assertEqual(1002, decoded["receiver"]["paramSource"])

    def test_raise_custom_script_event_decodes_constant_script_receiver(self):
        event_key = "StageFailAction"
        target_script_id = 85_937_500
        param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        event_args = b"\x04\x01" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4
        receiver = (
            b"\x04\x01"
            + target_script_id.to_bytes(8, "little")
            + b"\x00" * 7
            + (-1).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        payload = (
            event_args
            + b"\x04"
            + len(event_key).to_bytes(4, "little")
            + event_key.encode("ascii")
            + param_tail
            + receiver
        )
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x0380,
            "kind": 0x0B,
            "unionTag": 0x0380,
            "serializedMemberCount": 11,
            "strings": [{"offset": 18, "text": event_key}],
        }

        decoded = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )["raiseCustomScriptEvent"]
        self.assertEqual("constant_script", decoded["receiverMode"])
        self.assertEqual(target_script_id, decoded["targetScriptId"])
        self.assertTrue(decoded["receiver"]["hasConstValue"])

    def test_current_action_header_union_table_is_complete_and_contiguous(self):
        self.assertEqual(230, len(LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES))
        self.assertEqual(list(range(0xE6)), sorted(LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES))
        self.assertEqual(
            "LevelEvent_OnTravelPoleBegin",
            LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES[0xAD],
        )
        self.assertEqual(
            "MissionEvent_OnClientGlobalVarChanged",
            LEVELSCRIPT_NATIVE_HEADER_UNION_TAG_NAMES[0xB5],
        )

    def test_actionbase_tag_collision_is_not_named_as_mission_event_without_header_role(self):
        # Tag 0xb7 is ExitCustomMusicMode in the ActionBase union and
        # OnServerGlobalVarChanged in the ActionHeader union.  Current files
        # contain 0xb7/8 ActionBase rows, so list membership must select the
        # union table before a native event name is allowed.
        record = {
            "unionTag": 0x00B7,
            "serializedMemberCount": 8,
            "code": 0x00B7,
            "kind": 8,
        }
        self.assertEqual("", levelscript_native_header_name(record))
        self.assertEqual(
            "MissionEvent_OnServerGlobalVarChanged",
            levelscript_native_header_name(record, allow_union_tag_fallback=True),
        )

    def test_current_native_header_mappings_do_not_reuse_historical_trigger_codes(self):
        self.assertEqual(
            LEVELSCRIPT_NATIVE_HEADER_NAMES[(0x12BE, 0x00)],
            "ScriptEvent_OnLeaderEnterTriggerVolume",
        )
        self.assertEqual(
            LEVELSCRIPT_NATIVE_HEADER_NAMES[(0x12C0, 0x00)],
            "ScriptEvent_OnLeaderLeaveTriggerVolume",
        )
        self.assertEqual(
            LEVELSCRIPT_NATIVE_HEADER_NAMES[(0x1355, 0x00)],
            "LevelEvent_OnDialogExit",
        )
        self.assertEqual(
            LEVELSCRIPT_NATIVE_HEADER_NAMES[(0x1052, 0x00)],
            "LevelEvent_OnCustomEvent",
        )
        self.assertEqual(
            LEVELSCRIPT_NATIVE_HEADER_NAMES[(0x126A, 0x00)],
            "LevelEvent_OnEntityHpChanged",
        )

    def test_dialog_exit_event_is_decoded_as_local_and_distinct_from_server_event(self):
        data = bytearray(17)
        data[4] = 1
        data[5:9] = (3).to_bytes(4, "little", signed=True)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x1355,
            "kind": 0,
            "unionTag": 0x55,
            "serializedMemberCount": 19,
            "unionTagEncoding": "memorypack-u8",
            "localId": 2,
            "nextId": 0,
            "plainStrings": [
                "$2@_dialogId",
                "$2@_finishId",
                "$2@_isSkipped",
                "dlg_example",
            ],
        }

        decoded = decode_levelscript_record_payload(
            bytes(data),
            record,
            next_start=len(data),
            action_map_role="headerList#1",
        )
        detail = decoded["nativeEventDetail"]
        self.assertEqual("dlg_example", detail["dialogIdFilter"])
        self.assertEqual("dialogId", detail["dialogIdOutputRefs"][0]["field"])
        self.assertEqual("finishId", detail["finishIdOutputRefs"][0]["field"])
        self.assertEqual("isSkipped", detail["isSkippedOutputRefs"][0]["field"])
        self.assertEqual("client", detail["executionSide"])
        self.assertFalse(detail["serverExchange"])
        self.assertEqual(
            "LevelEvent_OnServerDialogExit",
            detail["distinctServerEventType"],
        )

    def test_residual_runtime_receivers_decode_exact_current_operands(self):
        param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        common = bytes(17) + b"\x04\x01" + param_tail
        script_scope = common + b"\xff" + (0).to_bytes(4, "little", signed=True)

        def output_ref(local_id, field):
            value = f"${local_id}@_{field}".encode("ascii")
            return b"\x02" + bytes(4) + len(value).to_bytes(4, "little") + value

        def string_param(value):
            raw = value.encode("ascii")
            return b"\x04" + len(raw).to_bytes(4, "little") + raw + param_tail

        def i32_param(value):
            return b"\x04" + value.to_bytes(4, "little", signed=True) + param_tail

        def bool_param(value):
            return b"\x04" + bytes([int(value)]) + param_tail

        def decode(union_tag, member_count, payload, plain_strings=()):
            return decode_levelscript_record_payload(
                payload,
                {
                    "code": union_tag,
                    "kind": 0,
                    "unionTag": union_tag,
                    "serializedMemberCount": member_count,
                    "payloadStart": 0,
                    "nextId": 0,
                    "plainStrings": [{"text": value} for value in plain_strings],
                },
                next_start=len(payload),
                action_map_role="headerList#1",
            )["nativeEventDetail"]

        bb = decode(
            0xB9,
            19,
            script_scope
            + string_param("n_interacts")
            + output_ref(41, "oldValue")
            + output_ref(41, "value"),
            ("n_interacts", "$41@_oldValue", "$41@_value"),
        )
        self.assertEqual("n_interacts", bb["blackboardKeyFilter"])
        self.assertEqual("SELF", bb["triggerTarget"])
        self.assertFalse(bb["serverExchange"])

        prop = decode(
            0xC2,
            19,
            script_scope
            + output_ref(30, "oldValue")
            + string_param("AllLock")
            + output_ref(30, "value"),
            ("$30@_oldValue", "AllLock", "$30@_value"),
        )
        self.assertEqual("AllLock", prop["propertyKeyFilter"])

        complete = decode(0xC4, 16, script_scope)
        self.assertEqual(0, complete["subtypeFieldCount"])
        self.assertEqual("owning-level-script", complete["scriptEventScope"])

        cast = decode(
            0x69,
            20,
            common
            + output_ref(0, "entity")
            + output_ref(0, "entityTemplateId")
            + output_ref(0, "firstTargetId")
            + bool_param(False)
            + output_ref(0, "skillId")
            + i32_param(0),
            ("$0@_entity", "$0@_entityTemplateId", "$0@_firstTargetId", "$0@_skillId"),
        )
        self.assertFalse(cast["filterModeEnabled"])
        self.assertFalse(cast["isCharacterFilter"])
        self.assertEqual(0, cast["skillTypeFilter"])
        self.assertEqual(0, cast["trailingContainerBytes"])

        cast_with_script_container = decode(
            0x69,
            20,
            common
            + output_ref(57, "entity")
            + output_ref(57, "entityTemplateId")
            + output_ref(57, "firstTargetId")
            + bool_param(False)
            + output_ref(57, "skillId")
            + i32_param(0)
            + b"\x01\x04\x00\x00\x00",
            (
                "$57@_entity",
                "$57@_entityTemplateId",
                "$57@_firstTargetId",
                "$57@_skillId",
            ),
        )
        self.assertEqual(
            "cast-skill-outputs-and-filter-operands-exact-prefix",
            cast_with_script_container["payloadShape"],
        )
        self.assertEqual(5, cast_with_script_container["trailingContainerBytes"])

        logic_id = 17_500_000_006
        entity_param = (
            b"\x04\x03"
            + logic_id.to_bytes(8, "little")
            + bytes(5)
            + (-1).to_bytes(4, "little", signed=True)
            + bytes(4)
            + (-1).to_bytes(4, "little", signed=True)
        )
        specific = decode(
            0xA0,
            16,
            common + output_ref(41, "entity") + entity_param,
            ("$41@_entity",),
        )
        self.assertEqual(logic_id, specific["entityFilter"]["logicId"])

        encounter = decode(
            0x59,
            16,
            common + b"\x04" + (34_700_000_003).to_bytes(8, "little") + param_tail + b"\xff",
        )
        self.assertEqual(34_700_000_003, encounter["levelScriptVariableFilter"])

        patrol = decode(
            0x88,
            18,
            common
            + output_ref(140, "entityOutput")
            + string_param("patrol2end")
            + b"\xff"
            + output_ref(140, "patrolIdOutput"),
            ("$140@_entityOutput", "patrol2end", "$140@_patrolIdOutput"),
        )
        self.assertEqual("patrol2end", patrol["scriptedCharEventKeyFilter"])

        list_entity = (
            b"\x03"
            + (2_100_021_214).to_bytes(8, "little")
            + bytes(5)
        )
        any_die = decode(
            0x45,
            18,
            common
            + output_ref(13, "entity")
            + b"\x04"
            + (1).to_bytes(4, "little")
            + list_entity
            + param_tail
            + bool_param(True)
            + bool_param(True),
            ("$13@_entity",),
        )
        self.assertTrue(any_die["filterByList"])
        self.assertTrue(any_die["isMonsterFilter"])
        self.assertEqual(2_100_021_214, any_die["entityListFilter"][0]["logicId"])

    def test_script_stage_changed_decodes_exact_local_filter_without_ownership(self):
        data = bytearray(54)
        data[4] = 1
        data[5:9] = (23).to_bytes(4, "little", signed=True)
        data[17:19] = b"\x04\x01"
        data[19:23] = (10).to_bytes(4, "little", signed=True)
        data[23:27] = (-1).to_bytes(4, "little", signed=True)
        data[27:31] = (-1).to_bytes(4, "little", signed=True)
        data[31:36] = b"\xff\x00\x00\x00\x00"
        data[36] = 4
        data[37:41] = (3).to_bytes(4, "little", signed=True)
        data[41:45] = (-1).to_bytes(4, "little", signed=True)
        data[45:49] = (0).to_bytes(4, "little", signed=True)
        data[49:53] = (-1).to_bytes(4, "little", signed=True)
        data[53] = 0xFF
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x12C9,
            "kind": 0,
            "unionTag": 0xC9,
            "serializedMemberCount": 18,
            "localId": 22,
            "nextId": 0,
            "plainStrings": [],
        }

        decoded = decode_levelscript_record_payload(
            bytes(data),
            record,
            next_start=len(data),
            action_map_role="headerList#1",
        )
        detail = decoded["nativeEventDetail"]
        self.assertEqual(3, detail["newStageFilter"])
        self.assertEqual("owning-level-script", detail["scriptEventScope"])
        self.assertEqual("SELF", detail["triggerTarget"])
        self.assertFalse(detail["targetScriptPresent"])
        self.assertEqual(10, detail["validateParam"]["idRef"])
        self.assertFalse(detail["serializedMissionOrQuestId"])
        self.assertFalse(detail["serverExchange"])

    def test_script_active_has_no_subtype_or_mission_ownership_fields(self):
        data = bytearray(36)
        data[5:9] = (9).to_bytes(4, "little", signed=True)
        data[17:19] = b"\x04\x01"
        data[19:23] = (-1).to_bytes(4, "little", signed=True)
        data[23:27] = (0).to_bytes(4, "little", signed=True)
        data[27:31] = (-1).to_bytes(4, "little", signed=True)
        data[31:36] = b"\xff\x00\x00\x00\x00"
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x10C3,
            "kind": 0,
            "unionTag": 0xC3,
            "serializedMemberCount": 16,
            "localId": 8,
            "nextId": 0,
            "plainStrings": [],
        }

        decoded = decode_levelscript_record_payload(
            bytes(data),
            record,
            next_start=len(data),
            action_map_role="headerList#1",
        )
        detail = decoded["nativeEventDetail"]
        self.assertEqual(0, detail["subtypeFieldCount"])
        self.assertEqual("owning-level-script", detail["scriptEventScope"])
        self.assertEqual("SELF", detail["triggerTarget"])
        self.assertFalse(detail["targetScriptPresent"])
        self.assertFalse(detail["serializedMissionOrQuestId"])
        self.assertFalse(detail["serverExchange"])

    def test_script_complete_accepts_exact_zero_subtype_before_outer_container(self):
        data = bytearray(36)
        data[5:9] = (13).to_bytes(4, "little", signed=True)
        data[17:19] = b"\x04\x01"
        data[19:23] = (-1).to_bytes(4, "little", signed=True)
        data[23:27] = (0).to_bytes(4, "little", signed=True)
        data[27:31] = (-1).to_bytes(4, "little", signed=True)
        data[31:36] = b"\xff\x00\x00\x00\x00"
        data.extend(b"outer-action-map-bytes")
        detail = decode_levelscript_record_payload(
            bytes(data),
            {
                "start": 0,
                "payloadStart": 0,
                "code": 0x10C4,
                "kind": 0,
                "unionTag": 0xC4,
                "serializedMemberCount": 16,
                "localId": 21,
                "nextId": 13,
                "plainStrings": [],
            },
            next_start=len(data),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual(0, detail["subtypeFieldCount"])
        self.assertEqual("zero-subtype-exact-prefix", detail["payloadShape"])
        self.assertEqual(len(b"outer-action-map-bytes"), detail["trailingContainerBytes"])

    def test_spawner_group_begin_decodes_exact_constant_filters(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(17)
        data[4] = 1
        data[5:9] = (49).to_bytes(4, "little", signed=True)
        data.extend(b"\x04\x01" + tail)
        data.extend(b"\x04" + (3).to_bytes(4, "little") + b"701" + tail)
        data.extend(b"\xff\x04" + (10200260004).to_bytes(8, "little") + tail)
        data.extend(b"\xff")
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x1296,
            "kind": 0,
            "unionTag": 0x96,
            "serializedMemberCount": 18,
            "localId": 48,
            "nextId": 0,
            "plainStrings": [],
        }

        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertEqual("701", detail["groupKeyFilter"])
        self.assertEqual(10200260004, detail["spawnerFilterId"])
        self.assertFalse(detail["groupKeyOutputPresent"])
        self.assertFalse(detail["spawnerOutputPresent"])

    def test_spawner_wave_begin_decodes_exact_constant_filters(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(17)
        data[4] = 1
        data[5:9] = (38).to_bytes(4, "little", signed=True)
        data.extend(b"\x04\x01" + tail)
        data.extend(b"\x04" + (10200260004).to_bytes(8, "little") + tail)
        data.extend(b"\xff\x04" + (1).to_bytes(4, "little") + b"4" + tail)
        data.extend(b"\xff")
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x129D,
            "kind": 0,
            "unionTag": 0x9D,
            "serializedMemberCount": 18,
            "localId": 37,
            "nextId": 0,
            "plainStrings": [],
        }

        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertEqual("4", detail["waveKeyFilter"])
        self.assertEqual(10200260004, detail["spawnerFilterId"])
        self.assertFalse(detail["waveKeyOutputPresent"])
        self.assertFalse(detail["spawnerOutputPresent"])

    def test_spawner_complete_decodes_server_push_and_exact_spawner_id(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(17)
        data[5:9] = (143).to_bytes(4, "little", signed=True)
        data.extend(b"\x04\x01" + tail)
        data.extend(b"\x04" + (23100270003).to_bytes(8, "little") + tail)
        data.extend(b"\xff")
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x1090,
            "kind": 0,
            "unionTag": 0x90,
            "serializedMemberCount": 16,
            "localId": 142,
            "nextId": 0,
            "plainStrings": [],
        }

        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertEqual(23100270003, detail["spawnerFilterId"])
        self.assertFalse(detail["spawnerOutputPresent"])
        self.assertEqual(
            "SC_SCENE_MONSTER_SPAWNER_COMPLETE",
            detail["serverMessage"],
        )
        self.assertTrue(detail["serverExchange"])
        self.assertFalse(detail["clientRequest"])
        self.assertFalse(detail["expectedClientReply"])

    def test_spawner_config_mission_index_requires_unique_config_and_mission(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            level = root / "map02_lv008"
            level.mkdir()
            (level / "sc_map02_lv008_23100270003.json").write_bytes(
                b"eny_0117_klhound_gm02m20\x00eny_0118_klhog_gm02m20"
            )
            unique = build_spawner_config_mission_index(
                {"gm02m20", "e11m1"},
                root=root,
            )[23100270003]
            self.assertEqual("unique", unique["status"])
            self.assertEqual(["gm02m20"], unique["missionIds"])
            self.assertEqual("map02_lv008", unique["configs"][0]["levelId"])

            (level / "sc_map02_lv008_23100270004.json").write_bytes(
                b"eny_test_gm02m20\x00eny_test_e11m1"
            )
            ambiguous = build_spawner_config_mission_index(
                {"gm02m20", "e11m1"},
                root=root,
            )[23100270004]
            self.assertEqual("ambiguous", ambiguous["status"])

    def test_save_property_event_decodes_exact_non_slot_entity_target(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(80)
        data[5:9] = (10).to_bytes(4, "little", signed=True)
        data[17:31] = b"\x04\x01" + tail
        data[31:58] = (
            b"\x04\x03"
            + (23400083108).to_bytes(8, "little")
            + (0).to_bytes(4, "little")
            + b"\x00"
            + tail
        )
        data[58:75] = b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4
        data[75] = 0xFF
        data[76:80] = (1).to_bytes(4, "little", signed=True)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x1537,
            "kind": 0,
            "unionTag": 0x37,
            "serializedMemberCount": 21,
            "localId": 5,
            "nextId": 0,
            "strings": [
                {"text": "state"},
                {"text": "$5@_oldValue"},
                {"text": "$5@_value"},
            ],
        }
        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertEqual(23400083108, detail["targetEntity"]["logicId"])
        self.assertFalse(detail["targetEntity"]["useSlotId"])
        self.assertEqual("state", detail["propertyKeyFilter"])
        self.assertFalse(detail["serverExchange"])

    def test_save_property_event_accepts_current_omitted_null_list_output(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"

        def output(value: str) -> bytes:
            raw = value.encode("utf-8")
            return b"\x02" + (0).to_bytes(4, "little", signed=True) + len(raw).to_bytes(4, "little") + raw

        data = bytearray(17)
        data[5:9] = (7).to_bytes(4, "little", signed=True)
        data.extend(
            b"\x04\x01"
            + (5).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        data.extend(
            b"\x04\x03"
            + (0).to_bytes(8, "little")
            + (40002).to_bytes(4, "little")
            + b"\x01"
            + tail
        )
        data.extend(b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4)
        data.extend((1).to_bytes(4, "little", signed=True))
        data.extend(output("$6@_oldValue"))
        data.extend(b"\x04" + (5).to_bytes(4, "little") + b"state" + tail)
        data.extend(output("$6@_value"))
        detail = decode_levelscript_record_payload(
            bytes(data),
            {
                "start": 0,
                "payloadStart": 0,
                "code": 0x1537,
                "kind": 0,
                "unionTag": 0x37,
                "serializedMemberCount": 21,
                "localId": 6,
                "nextId": 7,
                "strings": [
                    {"text": "state"},
                    {"text": "$6@_oldValue"},
                    {"text": "$6@_value"},
                ],
            },
            next_start=len(data),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual("omitted-null", detail["targetEntityListOutputEncoding"])
        self.assertEqual(40002, detail["targetEntity"]["slotId"])
        self.assertEqual("state", detail["propertyKeyFilter"])
        self.assertEqual(5, detail["validateParam"]["idRef"])
        self.assertEqual(-1, detail["validateParam"]["paramSource"])

    def test_interactive_state_event_exposes_exact_entity_slot_receiver(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(80)
        data[5:9] = (8).to_bytes(4, "little", signed=True)
        data[17:31] = b"\x04\x01" + tail
        data[31:58] = (
            b"\x04\x03"
            + (0).to_bytes(8, "little")
            + (40002).to_bytes(4, "little")
            + b"\x01"
            + tail
        )
        data[58:75] = b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4
        data[75] = 0xFF
        data[76:80] = (1).to_bytes(4, "little", signed=True)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x141E,
            "kind": 0,
            "unionTag": 0x1E,
            "serializedMemberCount": 20,
            "localId": 7,
            "nextId": 0,
            "plainStrings": [
                {"text": "$7@_oldValue"},
                {"text": "$7@_value"},
            ],
        }
        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertTrue(detail["targetEntity"]["useSlotId"])
        self.assertEqual(40002, detail["targetEntity"]["slotId"])
        self.assertEqual("oldValue", detail["oldValueOutputRefs"][0]["field"])
        self.assertFalse(detail["serializedMissionOrQuestId"])

    def test_ui_interact_event_preserves_dynamic_entity_property_selector(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(17)
        data[5:9] = (2).to_bytes(4, "little", signed=True)
        data.extend(b"\x04\x01" + tail)
        data.extend(
            b"\x04\x03"
            + (0).to_bytes(8, "little")
            + (0).to_bytes(4, "little")
            + b"\x00"
            + (-1).to_bytes(4, "little", signed=True)
            + (200).to_bytes(4, "little", signed=True)
            + (10).to_bytes(4, "little", signed=True)
            + b"liftButton"
        )
        data.extend(b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4)
        data.extend(b"\xff" + (1).to_bytes(4, "little", signed=True))
        output = b"$1@_optionIndex"
        data.extend(b"\x02" + (0).to_bytes(4, "little") + len(output).to_bytes(4, "little") + output)
        data.extend(b"\x04" + (1).to_bytes(4, "little", signed=True) + tail)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x153D,
            "kind": 0,
            "unionTag": 0x3D,
            "serializedMemberCount": 20,
            "localId": 1,
            "nextId": 0,
            "plainStrings": [
                {"text": "liftButton"},
                {"text": "$1@_optionIndex"},
            ],
        }
        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertEqual(200, detail["targetEntityParam"]["paramSource"])
        self.assertEqual("liftButton", detail["targetEntityParam"]["path"])
        self.assertEqual(1, detail["optionIndexFilter"])
        self.assertEqual("optionIndex", detail["optionIndexOutputRefs"][0]["field"])
        self.assertFalse(detail["serverExchange"])

    def test_entity_custom_event_keeps_receiver_and_event_key_together(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        data = bytearray(80)
        data[5:9] = (12).to_bytes(4, "little", signed=True)
        data[17:31] = b"\x04\x01" + tail
        data[31:58] = (
            b"\x04\x03"
            + (25000040034).to_bytes(8, "little")
            + (0).to_bytes(4, "little")
            + b"\x00"
            + tail
        )
        data[58:75] = b"\x04" + b"\xff" * 8 + b"\x00" * 4 + b"\xff" * 4
        data[75] = 0xFF
        data[76:80] = (1).to_bytes(4, "little", signed=True)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x1408,
            "kind": 0,
            "unionTag": 0x08,
            "serializedMemberCount": 20,
            "localId": 11,
            "nextId": 0,
            "strings": [
                {"text": "OnRuneColumnMatch"},
                {"text": "$11@_eventArgsPtr"},
            ],
        }
        detail = decode_levelscript_record_payload(
            bytes(data), record, next_start=len(data), action_map_role="headerList#1"
        )["nativeEventDetail"]
        self.assertEqual(25000040034, detail["targetEntity"]["logicId"])
        self.assertEqual("OnRuneColumnMatch", detail["eventKey"])
        self.assertFalse(detail["serializedMissionOrQuestId"])

    def test_non_script_tracking_matches_unique_world_entity_property_listener(self):
        from scripts.story_builder import level_bindings

        detail = {
            "type": "EntityEvent_OnSavePropertyChanged",
            "payloadSchemaStatus": "exact_current_build_memorypack_fields",
            "targetEntity": {
                "logicId": 23400083108,
                "slotId": 0,
                "useSlotId": False,
            },
            "targetEntityListPresent": False,
            "targetEntityListOutputPresent": False,
            "propertyKeyFilter": "state",
            "serverExchange": False,
            "serializedMissionOrQuestId": False,
        }
        occurrence = {
            "levelId": "map02_lv004",
            "scriptId": "23400083014",
            "sourceFile": "LevelScriptData/map02_lv004/23400083014.json",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "EntityEvent_OnSavePropertyChanged",
                "eventDetail": detail,
            }],
        }
        tracking = {
            "type": "EntityTrackingInfo",
            "scene": "map02_lv004",
            "trackScriptEntity": False,
            "entityLogicId": 83108,
            "scriptId": 0,
            "entitySlotId": 0,
        }
        with mock.patch.object(
            level_bindings,
            "_WORLD_ENTITY_BRIEF_LOGIC_CACHE",
            {83108: [{
                "globalLogicId": 23400083108,
                "entityType": 32,
                "entityDetailId": "int_switch_wltech01",
                "registrySourceFile": "WorldEntityRegistry.json",
            }]},
        ):
            matches = match_entity_tracking_native_entity_event_context(
                occurrence,
                tracking,
            )
        self.assertEqual(1, len(matches))
        self.assertEqual(23400083108, matches[0]["targetGlobalLogicId"])
        self.assertEqual("state", matches[0]["propertyKey"])

    def test_full_action_header_tags_require_header_list_context(self):
        record = {
            "code": 0x0A28,
            "kind": 0,
            "unionTag": 0x28,
            "serializedMemberCount": 10,
        }
        self.assertEqual("", levelscript_native_header_name(record))
        self.assertEqual(
            "EntityEvent_OnLeaderEnterLogicStartArea",
            levelscript_native_header_name(record, allow_union_tag_fallback=True),
        )
        self.assertNotIn((0x12A1, 0x00), LEVELSCRIPT_NATIVE_HEADER_NAMES)
        self.assertNotIn((0x1250, 0x00), LEVELSCRIPT_NATIVE_HEADER_NAMES)

    def test_compact_memorypack_tag_is_exposed_without_breaking_legacy_pair(self):
        data = bytearray(30)
        data[0] = 0x20
        data[1] = 0x0B
        data[2] = 0
        data[3:7] = (5).to_bytes(4, "little")
        data[7] = 0
        data[8:12] = (8).to_bytes(4, "little")
        data[12:20] = b"d074f3a4"
        data[26:30] = (6).to_bytes(4, "little", signed=True)

        record = _decode_uid_record(bytes(data), 12, "d074f3a4")
        self.assertEqual(0x0B20, record["code"])
        self.assertEqual(0x00, record["kind"])
        self.assertEqual(0x20, record["unionTag"])
        self.assertEqual(0x0B, record["serializedMemberCount"])
        self.assertEqual("memorypack-u8", record["unionTagEncoding"])
        shared_record = extract_levelscript_uid_records(bytes(data))[0]
        self.assertEqual(0x20, shared_record["unionTag"])
        self.assertEqual(0x0B, shared_record["serializedMemberCount"])

    def test_compact_exit_level_custom_performance_is_exact_cleanup_action(self):
        data = bytearray(47)
        data[0] = 0xB9
        data[1] = 0x09
        data[2] = 0
        data[3:7] = (5).to_bytes(4, "little")
        data[7] = 0
        data[8:12] = (8).to_bytes(4, "little")
        data[12:20] = b"604fd823"
        data[20:24] = (1).to_bytes(4, "little")
        data[24] = 1
        data[25] = 1
        data[26:30] = (-1).to_bytes(4, "little", signed=True)
        data[30] = 0x04
        data[31:35] = (0).to_bytes(4, "little")
        data[35:47] = b"\xff" * 12

        record = _decode_uid_record(bytes(data), 12, "604fd823")
        detail = decode_levelscript_record_payload(
            bytes(data),
            record,
            next_start=len(data),
            action_map_role="actionList#1 root",
        )

        self.assertEqual(0x09B9, record["code"])
        self.assertEqual(0xB9, record["unionTag"])
        self.assertEqual(0x09, record["serializedMemberCount"])
        self.assertEqual(
            "ExitLevelCustomPerformance",
            levelscript_native_action_name(record),
        )
        self.assertEqual(
            "presentation_cleanup",
            classify_levelscript_record(record),
        )
        self.assertEqual(
            "actionbase-exit-level-custom-performance",
            detail["label"],
        )
        self.assertEqual(
            {
                "payloadShape": "uint-handle-with-unset-param-tail-exact-eof",
                "handle": {
                    "serializedConstValue": 0,
                    "idRef": -1,
                    "paramSource": -1,
                    "path": None,
                },
                "consumedBytes": 17,
            },
            detail["exitLevelCustomPerformance"],
        )
        self.assertEqual(
            {},
            decode_exit_level_custom_performance_action(
                bytes(data[30:47]),
                (0x00B9, 0x08),
            ),
        )

    def test_dialog_teleport_followups_are_exact_presentation_actions(self):
        toggle_payload = bytes.fromhex(
            "04 00 ff ff ff ff 00 00 00 00 ff ff ff ff"
        )
        toggle_record = {
            "code": 0x04CA,
            "kind": 0x09,
            "unionTag": 0x04CA,
            "serializedMemberCount": 9,
            "payloadStart": 0,
        }
        toggle_detail = decode_levelscript_record_payload(
            toggle_payload,
            toggle_record,
            next_start=len(toggle_payload),
            action_map_role="actionList#3 linked",
        )
        self.assertEqual(
            "ToggleClearScreenButRadio",
            levelscript_native_action_name(toggle_record),
        )
        self.assertEqual(
            "presentation_toggle",
            classify_levelscript_record(toggle_record),
        )
        self.assertEqual(
            {
                "payloadShape": "is-show-bool-param-exact-eof",
                "isShow": {
                    "value": False,
                    "idRef": -1,
                    "paramSource": 0,
                    "path": None,
                },
                "consumedBytes": 14,
            },
            toggle_detail["toggleClearScreenButRadio"],
        )

        move_payload = bytes.fromhex(
            "04 00 00 00 00 00 00 00 00 00 00 00 00 "
            "ff ff ff ff c8 00 00 00 0c 00 00 00 "
            "77 61 6c 6b 5f 65 6e 64 5f 70 6f 73 "
            "04 00 00 00 00 ff ff ff ff 00 00 00 00 ff ff ff ff"
        )
        move_record = {
            "code": 0x02FE,
            "kind": 0x0A,
            "unionTag": 0x02FE,
            "serializedMemberCount": 10,
            "payloadStart": 0,
        }
        move_detail = decode_levelscript_record_payload(
            move_payload,
            move_record,
            next_start=len(move_payload),
            action_map_role="actionList#4 linked",
        )
        self.assertEqual(
            "MainCharMoveTo",
            levelscript_native_action_name(move_record),
        )
        self.assertEqual(
            "movement_control",
            classify_levelscript_record(move_record),
        )
        self.assertEqual(
            {
                "payloadShape": "end-pos-vector3-and-grounded-gait-exact-eof",
                "endPos": {
                    "x": 0.0,
                    "y": 0.0,
                    "z": 0.0,
                    "idRef": -1,
                    "paramSource": 200,
                    "path": "walk_end_pos",
                },
                "groundedMoveGait": {
                    "value": 0,
                    "idRef": -1,
                    "paramSource": 0,
                    "path": None,
                },
                "consumedBytes": 54,
            },
            move_detail["mainCharMoveTo"],
        )

    def test_compact_call_server_terminal_decodes_exact_generated_fields(self):
        payload = bytes.fromhex(
            "ff ff ff ff 04 01 0a 00 00 00 "
            "65 76 65 6e 74 5f 61 72 67 73 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff "
            "04 09 00 00 00 23 35 62 64 33 31 38 62 61 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff 00 01 00"
        )
        record = {
            "code": 0x0E34,
            "kind": 0,
            "unionTag": 0x0034,
            "serializedMemberCount": 14,
            "payloadStart": 0,
            "uid": "5bd318ba",
        }
        detail = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#7 linked",
        )

        self.assertEqual("CallServer", levelscript_native_action_name(record))
        self.assertEqual("server_handoff", classify_levelscript_record(record))
        self.assertEqual("actionbase-call-server", detail["label"])
        self.assertEqual(
            {
                "payloadShape": "six-call-server-fields-exact-prefix",
                "callClientOutputUIDs": None,
                "eventArgsPtr": {
                    "pathValue": "event_args",
                    "idRef": -1,
                    "paramSource": 0,
                    "path": None,
                },
                "eventName": "#5bd318ba",
                "eventNameIdentity": "record-uid-prefixed",
                "callbackCorrelationLabel": True,
                "storyGraphRole": "diagnostic-only",
                "missionOwnershipEvidence": False,
                "orderEvidence": False,
                "useCustomEvent": False,
                "waitForCallback": True,
                "withEventArgs": False,
                "consumedBytes": 61,
                "trailingBytes": 0,
            },
            detail["callServer"],
        )
        step = {
            "source": {
                "code": "0x0e34",
                "kind": "0x00",
                "uid": "5bd318ba",
            },
        }
        self.assertTrue(is_call_server_self_uid_callback("#5bd318ba", step))
        self.assertFalse(is_call_server_self_uid_callback("#2f436d36", step))
        self.assertEqual(
            [],
            source_backed_hash_terminals_from_scene_graph({
                "levelscriptHashTerminals": [{
                    "sceneKey": "dlg_sm2l7m1_9",
                    "hash": "#5bd318ba",
                    "direction": "story->hash",
                    "hashStep": step,
                }],
            }),
        )
        callbacks = source_backed_call_server_callbacks_from_scene_graph({
            "levelscriptCallServerCallbacks": [{
                "kind": "levelscriptCallServerSelfUidCallback",
                "file": "LevelScriptData/map02_lv006/22999990003.json",
                "levelId": "map02_lv006",
                "precedingSceneKey": "dlg_sm2l7m1_9",
                "callbackLabel": "#5bd318ba",
                "recordUid": "5bd318ba",
                "sourceStep": step,
            }],
        })
        self.assertEqual(1, len(callbacks))
        self.assertFalse(callbacks[0]["storyNode"])
        self.assertFalse(callbacks[0]["missionOwnershipEvidence"])
        self.assertFalse(callbacks[0]["orderEvidence"])

    def test_call_server_decodes_non_null_callback_uid_list_generically(self):
        payload = bytes.fromhex(
            "02 00 00 00 "
            "08 00 00 00 33 30 33 65 34 35 32 62 "
            "08 00 00 00 62 38 37 34 37 63 30 30 "
            "04 01 0a 00 00 00 65 76 65 6e 74 5f 61 72 67 73 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff "
            "04 09 00 00 00 23 65 65 63 39 35 63 35 37 "
            "ff ff ff ff 00 00 00 00 ff ff ff ff 00 01 00"
        )
        record = {
            "code": 0x0E34,
            "kind": 0,
            "unionTag": 0x0034,
            "serializedMemberCount": 14,
            "payloadStart": 0,
            "uid": "eec95c57",
        }

        detail = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#49 linked",
        )["callServer"]

        self.assertEqual(["303e452b", "b8747c00"], detail["callClientOutputUIDs"])
        self.assertEqual("#eec95c57", detail["eventName"])
        self.assertTrue(detail["waitForCallback"])
        self.assertEqual(len(payload), detail["consumedBytes"])
        self.assertEqual(0, detail["trailingBytes"])

    def test_call_server_complete_contract_validator_is_value_agnostic(self):
        contract = {
            "callClientOutputUIDs": None,
            "eventArgsPtr": {
                "pathValue": "arbitrary_param_name",
                "paramSource": 100,
                "path": "$9@_value",
            },
            "eventName": "arbitrary_runtime_event",
            "useCustomEvent": True,
            "waitForCallback": False,
            "withEventArgs": True,
            "consumedBytes": 72,
            "trailingBytes": 4,
        }
        self.assertEqual(
            [],
            validate_callserver_serialized_contract(
                contract,
                source_file="fixture.json",
                local_id=9,
                uid="01020304",
            ),
        )

    def test_call_server_complete_contract_validator_reports_missing_fields(self):
        failures = validate_callserver_serialized_contract(
            {"eventName": "event"},
            source_file="fixture.json",
            local_id=9,
            uid="01020304",
        )
        self.assertEqual(
            "callserver_serialized_fields_present",
            failures[0]["gate"],
        )
        self.assertIn("eventArgsPtr", failures[0]["actualMissing"])

    def test_call_server_contract_projection_excludes_graph_annotations(self):
        projected = compact_callserver_serialized_contract({
            "eventName": "#01020304",
            "eventArgsPtr": {"pathValue": "event_args"},
            "missionOwnershipEvidence": False,
            "orderEvidence": False,
            "storyGraphRole": "diagnostic-only",
        })
        self.assertEqual(
            {
                "eventName": "#01020304",
                "eventArgsPtr": {"pathValue": "event_args"},
            },
            projected,
        )

    def test_play_dialog_hide_punctuation_payload_is_not_a_graph_node(self):
        step = {
            "payloads": [
                {
                    "text": "#",
                    "nodeKey": "#",
                    "kind": "levelscriptSymbol",
                },
                {
                    "text": "dlg_sm2l5m1_7",
                    "sceneKey": "dlg_sm2l5m1_7",
                    "nodeKey": "dlg_sm2l5m1_7",
                    "kind": "runtimeDialog",
                },
            ],
            "_debug": {
                "source": {
                    "code": "0x035a",
                    "kind": "0x0f",
                    "uid": "15196cb4",
                    "actionMapRole": "actionList#1 root",
                },
            },
        }
        self.assertTrue(is_play_dialog_hide_non_identifier_payload("#", step))
        self.assertTrue(is_play_dialog_hide_non_identifier_payload("%", step))
        self.assertFalse(
            is_play_dialog_hide_non_identifier_payload("#a354645e", step)
        )
        step_without_dialog = {
            **step,
            "payloads": [step["payloads"][0]],
        }
        self.assertFalse(
            is_play_dialog_hide_non_identifier_payload("#", step_without_dialog)
        )
        step_with_header_membership = {
            **step,
            "_debug": {
                "source": {
                    **step["_debug"]["source"],
                    "actionMapRole": "headerList#1",
                },
            },
        }
        self.assertFalse(
            is_play_dialog_hide_non_identifier_payload(
                "#",
                step_with_header_membership,
            )
        )
        other_action = {
            "payloads": step["payloads"],
            "_debug": {
                "source": {
                    "code": "0x0357",
                    "kind": "0x14",
                    "uid": "15196cb4",
                    "actionMapRole": "actionList#1 root",
                },
            },
        }
        self.assertFalse(
            is_play_dialog_hide_non_identifier_payload("#", other_action)
        )

    def test_typed_cutscene_single_char_parameter_is_not_a_graph_node(self):
        step = {
            "payloads": [
                {
                    "text": "P",
                    "nodeKey": "P",
                    "kind": "levelscriptSymbol",
                },
                {
                    "text": "cutscene_e6m1_2_1",
                    "sceneKey": "cutscene_e6m1_2_1",
                    "nodeKey": "cutscene_e6m1_2_1",
                    "kind": "cutscene",
                },
            ],
            "_debug": {
                "source": {
                    "code": "0x049c",
                    "kind": "0x12",
                    "uid": "63889ee7",
                    "actionMapRole": "actionList#1 root",
                },
            },
        }
        self.assertEqual(
            "StartCutsceneAndHideSceneObjectAction",
            typed_cutscene_single_char_parameter_action("P", step),
        )
        self.assertEqual(
            "",
            typed_cutscene_single_char_parameter_action(
                "cutscene_e6m1_2_1",
                step,
            ),
        )
        self.assertEqual(
            "",
            typed_cutscene_single_char_parameter_action("parameterName", step),
        )
        step["_debug"]["source"]["code"] = "0x0357"
        step["_debug"]["source"]["kind"] = "0x14"
        self.assertEqual(
            "",
            typed_cutscene_single_char_parameter_action("P", step),
        )
        step["_debug"]["source"]["code"] = "0x049c"
        step["_debug"]["source"]["kind"] = "0x12"
        step["_debug"]["source"]["actionMapRole"] = "headerList#1"
        self.assertEqual(
            "",
            typed_cutscene_single_char_parameter_action("P", step),
        )

    def test_story_boundary_context_actions_use_formatter_names(self):
        self.assertEqual(
            "AddCameraControlState",
            levelscript_native_action_name({
                "layout": "plain",
                "code": 0x0F0B,
                "kind": 0,
            }),
        )
        self.assertEqual(
            "RequireSettlementShow",
            levelscript_native_action_name({
                "layout": "fa",
                "code": 0x0392,
                "kind": 0x0B,
            }),
        )

    def test_uid_parser_accepts_dont_log_and_wide_compact_member_count(self):
        compact = bytearray(30)
        compact[0] = 0x8A
        compact[1] = 0x25
        compact[2] = 1
        compact[3:7] = (7).to_bytes(4, "little")
        compact[7] = 0
        compact[8:12] = (8).to_bytes(4, "little")
        compact[12:20] = b"1234abcd"
        compact[26:30] = (-1).to_bytes(4, "little", signed=True)
        compact_record = _decode_uid_record(bytes(compact), 12, "1234abcd")
        self.assertEqual("plain", compact_record["layout"])
        self.assertEqual(0x8A, compact_record["unionTag"])
        self.assertEqual(0x25, compact_record["serializedMemberCount"])
        self.assertTrue(compact_record["dontLog"])

        extended = bytearray(32)
        extended[0] = 0xFA
        extended[1:3] = (0x04F2).to_bytes(2, "little")
        extended[3] = 0x09
        extended[4] = 1
        extended[5:9] = (25).to_bytes(4, "little")
        extended[9] = 0
        extended[10:14] = (8).to_bytes(4, "little")
        extended[14:22] = b"4e7ff916"
        extended[28:32] = (-1).to_bytes(4, "little", signed=True)
        extended_record = _decode_uid_record(bytes(extended), 14, "4e7ff916")
        self.assertEqual("fa", extended_record["layout"])
        self.assertEqual(0x04F2, extended_record["unionTag"])
        self.assertEqual(0x09, extended_record["serializedMemberCount"])
        self.assertTrue(extended_record["dontLog"])
        shared_extended = extract_levelscript_uid_records(bytes(extended))[0]
        self.assertEqual("fa", shared_extended["layout"])

    def test_typed_branch_split_and_if_else_payloads_preserve_native_order(self):
        branch_payload = struct.pack("<III", 2, 143, 121)
        branch = decode_levelscript_record_payload(
            branch_payload,
            {"code": 0x002D, "kind": 0x09, "payloadStart": 0},
            next_start=len(branch_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual([143, 121], branch["branchSequenceActionLocalIds"])
        self.assertEqual(
            "typed-branch-ordered-action-list",
            branch["sequenceRole"],
        )

        split_payload = struct.pack("<III", 2, 97, 88)
        split = decode_levelscript_record_payload(
            split_payload,
            {"code": 0x0495, "kind": 0x09, "payloadStart": 0},
            next_start=len(split_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual([97, 88], split["splitActionLocalIds"])

        if_else_payload = b"condition" + struct.pack("<ii", 61, 58)
        if_else = decode_levelscript_record_payload(
            if_else_payload,
            {"code": 0x00FF, "kind": 0x0B, "payloadStart": 0},
            next_start=len(if_else_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual(61, if_else["falseActionLocalId"])
        self.assertEqual(58, if_else["trueActionLocalId"])

        inline_condition_payload = (
            b"\x04\x01"
            + struct.pack("<iii", -1, 100, 5)
            + b"radio"
            + struct.pack("<ii", 61, 58)
        )
        inline_condition = decode_levelscript_record_payload(
            inline_condition_payload,
            {"code": 0x00FF, "kind": 0x0B, "payloadStart": 0},
            next_start=len(inline_condition_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual(
            {"value": True, "idRef": -1, "paramSource": 100, "path": "radio"},
            inline_condition["conditionParam"],
        )

        while_payload = (
            b"\x04\x00"
            + struct.pack("<iii", 58, -1, -1)
            + struct.pack("<i", 26)
        )
        while_action = decode_levelscript_record_payload(
            while_payload,
            {
                "code": 0x0501,
                "kind": 0x0A,
                "unionTag": 0x0501,
                "serializedMemberCount": 0x0A,
                "payloadStart": 0,
            },
            next_start=len(while_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual(26, while_action["whileDoActionLocalId"])
        self.assertEqual(
            {
                "value": False,
                "idRef": 58,
                "paramSource": -1,
                "path": None,
            },
            while_action["whileConditionParam"],
        )
        self.assertEqual([26], while_action["branchLocalRefs"])
        self.assertEqual("typed-while-action-body", while_action["branchRole"])
        self.assertEqual(58, while_action["whileConditionActionLocalId"])

        malformed_while = decode_levelscript_record_payload(
            while_payload + b"\x00",
            {
                "code": 0x0501,
                "kind": 0x0A,
                "unionTag": 0x0501,
                "serializedMemberCount": 0x0A,
                "payloadStart": 0,
            },
            next_start=len(while_payload) + 1,
            action_map_role="actionList#1 root",
        )
        self.assertNotIn("whileDoActionLocalId", malformed_while)

    def test_control_path_traverses_typed_while_action_body(self):
        header = {
            "code": 0x1052,
            "kind": 0x00,
            "start": 10,
            "localId": 1,
            "nextId": 0,
            "strings": [],
            "plainStrings": [],
        }
        while_action = {
            "code": 0x0501,
            "kind": 0x0A,
            "start": 100,
            "localId": 3,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        target = {
            "code": 0x0363,
            "kind": 0x0D,
            "start": 200,
            "localId": 4,
            "nextId": -1,
            "strings": [{"text": "radio_testm1_1"}],
            "plainStrings": [],
        }
        records = [header, while_action, target]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 root",
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 3}}
            if record is while_action:
                return {"whileDoActionLocalId": 4}
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            paths = _levelscript_native_control_paths_to_record(
                bytes(300), records, membership, target
            )
        self.assertEqual(1, len(paths))
        self.assertEqual([3, 4], paths[0]["pathLocalIds"])
        self.assertEqual("WhileAction.doAction", paths[0]["path"][-1]["edge"])

    def test_control_path_traverses_typed_branch_sequence_entries(self):
        header = {
            "code": 0x1052,
            "kind": 0x00,
            "start": 10,
            "localId": 1,
            "nextId": 0,
            "strings": [],
            "plainStrings": [],
        }
        branch = {
            "code": 0x002D,
            "kind": 0x09,
            "start": 100,
            "localId": 120,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        first = {
            "code": 0x04F7,
            "kind": 0x09,
            "start": 200,
            "localId": 143,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        target = {
            "code": 0x0357,
            "kind": 0x14,
            "start": 300,
            "localId": 121,
            "nextId": -1,
            "strings": [{"text": "cutscene_testm1_1"}],
            "plainStrings": [],
        }
        records = [header, branch, first, target]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 root",
            300: "actionList#3 root",
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 120}}
            if record is branch:
                return {"branchSequenceActionLocalIds": [143, 121]}
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            paths = _levelscript_native_control_paths_to_record(
                bytes(400), records, membership, target
            )
        self.assertEqual(1, len(paths))
        self.assertEqual([120, 121], paths[0]["pathLocalIds"])
        self.assertEqual("Branch.sequence[1]", paths[0]["path"][-1]["edge"])

    def test_switch_int_decodes_native_lists_and_rejects_partial_shapes(self):
        payload = (
            struct.pack("<Iii", 2, 8, -1)
            + struct.pack("<Iii", 2, 0, 1)
            + struct.pack("<i", 0)
            + b"\x04\x00\x00\x00\x00"
            + struct.pack("<i", 6)
            + b"\xff" * 8
        )
        decoded = decode_levelscript_record_payload(
            payload,
            {
                "code": 0x04BD,
                "kind": 0x0C,
                "unionTag": 0x04BD,
                "serializedMemberCount": 0x0C,
                "payloadStart": 0,
            },
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual([8, -1], decoded["switchCaseActionLocalIds"])
        self.assertEqual([0, 1], decoded["switchCaseValues"])
        self.assertEqual(0, decoded["switchDefaultActionLocalId"])
        self.assertEqual(6, decoded["switchValueGetterLocalId"])
        self.assertEqual([8], decoded["branchLocalRefs"])
        self.assertEqual(
            decoded["switchCases"],
            decode_switch_action(payload, (0x04BD, 0x0C))["switchCases"],
        )
        self.assertEqual({}, decode_switch_action(payload, (0x04BD, 0x0B)))

        inline_value = (
            struct.pack("<Ii", 1, 8)
            + struct.pack("<Ii", 1, 3)
            + struct.pack("<i", 0)
            + b"\x04"
            + struct.pack("<iiii", 0, -1, 100, 3)
            + b"sum"
        )
        decoded_inline = decode_levelscript_record_payload(
            inline_value,
            {
                "code": 0x04BD,
                "kind": 0x0C,
                "unionTag": 0x04BD,
                "serializedMemberCount": 0x0C,
                "payloadStart": 0,
            },
            next_start=len(inline_value),
            action_map_role="actionList#1 root",
        )
        self.assertEqual(
            {"value": 0, "idRef": -1, "paramSource": 100, "path": "sum"},
            decoded_inline["switchValueParam"],
        )

        mismatched = struct.pack("<IiIi", 1, 8, 2, 0)
        rejected = decode_levelscript_record_payload(
            mismatched,
            {
                "code": 0x04BD,
                "kind": 0x0C,
                "unionTag": 0x04BD,
                "serializedMemberCount": 0x0C,
                "payloadStart": 0,
            },
            next_start=len(mismatched),
            action_map_role="actionList#1 root",
        )
        self.assertNotIn("switchCaseActionLocalIds", rejected)

    def test_switch_int_larger_reuses_exact_integer_switch_shape(self):
        payload = (
            struct.pack("<Iii", 2, 90, 157)
            + struct.pack("<Iii", 2, 2, 9)
            + struct.pack("<i", 0)
            + b"\x04\x00\x00\x00\x00"
            + struct.pack("<i", 156)
            + b"\xff" * 8
        )
        decoded = decode_levelscript_record_payload(
            payload,
            {
                "code": 0x04BE,
                "kind": 0x0C,
                "unionTag": 0x04BE,
                "serializedMemberCount": 0x0C,
                "payloadStart": 0,
            },
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual("SwitchIntLarger", decoded["actionBaseAction"])
        self.assertEqual([90, 157], decoded["switchIntLargerCaseActionLocalIds"])
        self.assertEqual([2, 9], decoded["switchIntLargerCaseValues"])
        self.assertEqual(0, decoded["switchIntLargerDefaultActionLocalId"])
        self.assertEqual(156, decoded["switchIntLargerValueGetterLocalId"])
        self.assertEqual([90, 157], decoded["branchLocalRefs"])

    def test_switch_int_path_reaches_serialized_radio_chain(self):
        header = {
            "code": 0x12BE,
            "kind": 0,
            "start": 10,
            "localId": 27,
            "nextId": 0,
            "strings": [],
            "plainStrings": [],
        }
        switch = {
            "code": 0x04BD,
            "kind": 0x0C,
            "unionTag": 0x04BD,
            "serializedMemberCount": 0x0C,
            "start": 100,
            "localId": 7,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        radios = [
            {
                "code": 0x0364 if local_id < 11 else 0x0363,
                "kind": 0x0D,
                "start": 200 + index * 100,
                "localId": local_id,
                "nextId": local_id + 1 if local_id < 11 else -1,
                "strings": [{"text": key}],
                "plainStrings": [],
            }
            for index, (local_id, key) in enumerate((
                (8, "radio_e3m4_14"),
                (9, "radio_e3m4_7"),
                (10, "radio_e3m4_15"),
                (11, "radio_e3m4_8"),
            ))
        ]
        records = [header, switch, *radios]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            **{
                record["start"]: f"actionList#{index + 2} linked"
                for index, record in enumerate(radios)
            },
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 7}}
            if record is switch:
                return {
                    "switchCaseActionLocalIds": [8, -1],
                    "switchCaseValues": [0, 1],
                    "switchDefaultActionLocalId": 0,
                }
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            for index, radio in enumerate(radios):
                paths = _levelscript_native_control_paths_to_record(
                    bytes(700), records, membership, radio
                )
                self.assertEqual(1, len(paths))
                self.assertEqual(
                    [7, *range(8, 9 + index)],
                    paths[0]["pathLocalIds"],
                )
                self.assertEqual(
                    "SwitchInt.case[0]=0",
                    paths[0]["path"][1]["edge"],
                )

    def test_switch_string_decodes_exact_case_targets_and_rejects_trailing_bytes(self):
        value_param = (
            b"\x04"
            + (-1).to_bytes(4, "little", signed=True)
            + (142).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        payload = (
            struct.pack("<Iii", 2, 131, -1)
            + struct.pack("<I", 2)
            + struct.pack("<I", len(b"chr_9000_endmin"))
            + b"chr_9000_endmin"
            + struct.pack("<I", len(b"chr_0031_mifu"))
            + b"chr_0031_mifu"
            + struct.pack("<i", 0)
            + value_param
        )
        record = {
            "code": 0x04BF,
            "kind": 0x0C,
            "unionTag": 0x04BF,
            "serializedMemberCount": 0x0C,
            "payloadStart": 0,
        }
        decoded = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual("SwitchString", decoded["actionBaseAction"])
        self.assertEqual([131, -1], decoded["switchStringCaseActionLocalIds"])
        self.assertEqual(
            ["chr_9000_endmin", "chr_0031_mifu"],
            decoded["switchStringCaseValues"],
        )
        self.assertEqual(0, decoded["switchStringDefaultActionLocalId"])
        self.assertEqual(142, decoded["switchStringValueGetterLocalId"])
        self.assertEqual([131], decoded["branchLocalRefs"])
        self.assertEqual(
            "switch-string-four-fields-exact-eof",
            decoded["payloadShape"],
        )

        malformed = decode_levelscript_record_payload(
            payload + b"\x00",
            record,
            next_start=len(payload) + 1,
            action_map_role="actionList#1 root",
        )
        self.assertNotIn("switchStringCaseActionLocalIds", malformed)

    def test_wait_trigger_volume_decodes_exact_success_target_and_receiver(self):
        default_tail = struct.pack("<iii", -1, 0, -1)
        seconds = b"\x04" + struct.pack("<f", 40.0) + default_tail
        current_script = (
            b"\x04"
            + (0).to_bytes(8, "little")
            + (0).to_bytes(8, "little")
            + struct.pack("<iii", -1, 1002, -1)
        )
        trigger_slot = b"\x04" + struct.pack("<i", 80001) + default_tail
        payload = (
            b"\xff"
            + struct.pack("<i", 0)
            + seconds
            + struct.pack("<i", 32)
            + current_script
            + trigger_slot
        )
        record = {
            "code": 0x04F9,
            "kind": 0x0E,
            "unionTag": 0x04F9,
            "serializedMemberCount": 0x0E,
            "payloadStart": 0,
        }
        decoded = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual(
            "WaitForSecondsInTriggerVolume",
            decoded["actionBaseAction"],
        )
        self.assertEqual(0, decoded["waitFailActionLocalId"])
        self.assertEqual(32, decoded["waitSuccessActionLocalId"])
        self.assertEqual(40.0, decoded["waitSeconds"]["value"])
        self.assertEqual("current_script", decoded["waitScriptPtr"]["mode"])
        self.assertEqual(80001, decoded["waitTriggerSlotId"]["value"])
        self.assertEqual([32], decoded["branchLocalRefs"])

        malformed = decode_levelscript_record_payload(
            payload + b"\x00",
            record,
            next_start=len(payload) + 1,
            action_map_role="actionList#1 root",
        )
        self.assertNotIn("waitSuccessActionLocalId", malformed)

    def test_control_path_traverses_switch_string_and_wait_success_targets(self):
        header = {
            "code": 0x12BA,
            "kind": 0,
            "start": 10,
            "localId": 1,
            "nextId": 0,
            "strings": [{"text": "WaitArea"}],
            "plainStrings": [],
        }
        switch_string = {
            "code": 0x04BF,
            "kind": 0x0C,
            "unionTag": 0x04BF,
            "serializedMemberCount": 0x0C,
            "start": 100,
            "localId": 2,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        wait = {
            "code": 0x04F9,
            "kind": 0x0E,
            "unionTag": 0x04F9,
            "serializedMemberCount": 0x0E,
            "start": 200,
            "localId": 3,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        target = {
            "code": 0x0363,
            "kind": 0x0D,
            "start": 300,
            "localId": 4,
            "nextId": -1,
            "strings": [{"text": "radio_testm1_1"}],
            "plainStrings": [],
        }
        records = [header, switch_string, wait, target]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 root",
            300: "actionList#3 root",
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 2}}
            if record is switch_string:
                return {
                    "switchStringCaseActionLocalIds": [3],
                    "switchStringCaseValues": ["chr_9000_endmin"],
                    "switchStringDefaultActionLocalId": 0,
                }
            if record is wait:
                return {
                    "waitSuccessActionLocalId": 4,
                    "waitFailActionLocalId": 0,
                    "waitScriptPtr": {"mode": "current_script"},
                }
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            paths = _levelscript_native_control_paths_to_record(
                bytes(400), records, membership, target
            )
        self.assertEqual(1, len(paths))
        self.assertEqual([2, 3, 4], paths[0]["pathLocalIds"])
        self.assertEqual(
            "SwitchString.case[0]=chr_9000_endmin",
            paths[0]["path"][1]["edge"],
        )
        self.assertEqual(
            "WaitForSecondsInTriggerVolume.successAction",
            paths[0]["path"][2]["edge"],
        )

        def decode_cross_script(_data, record, **_kwargs):
            detail = decode(_data, record, **_kwargs)
            if record is wait:
                detail["waitScriptPtr"] = {
                    "mode": "explicit_script",
                    "scriptId": "300010008",
                }
            return detail

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode_cross_script,
        ):
            self.assertEqual(
                [],
                _levelscript_native_control_paths_to_record(
                    bytes(400), records, membership, target
                ),
            )

    def test_entity_hp_header_separates_filter_level_mask_and_exact_condition(self):
        payload = bytearray(84)
        payload[0:4] = (3).to_bytes(4, "little", signed=True)
        payload[4] = 1
        payload[5:9] = (209).to_bytes(4, "little", signed=True)
        payload[17] = 4
        payload[18] = 1
        payload[19:23] = (-1).to_bytes(4, "little", signed=True)
        payload[23:27] = (0).to_bytes(4, "little", signed=True)
        payload[27:31] = (-1).to_bytes(4, "little", signed=True)
        payload[31:35] = (0).to_bytes(4, "little", signed=True)
        payload[35] = 4
        payload[36:40] = (1).to_bytes(4, "little", signed=True)
        payload[40] = 3
        payload[41:49] = (0).to_bytes(8, "little")
        payload[49:53] = (40021).to_bytes(4, "little")
        payload[53] = 1
        payload[54:58] = (-1).to_bytes(4, "little", signed=True)
        payload[58:62] = (0).to_bytes(4, "little", signed=True)
        payload[62:66] = (-1).to_bytes(4, "little", signed=True)
        payload[66] = 0xFF
        payload[67] = 4
        payload[68:72] = struct.pack("<f", 0.1)
        payload[72:76] = (-1).to_bytes(4, "little", signed=True)
        payload[76:80] = (0).to_bytes(4, "little", signed=True)
        payload[80:84] = (-1).to_bytes(4, "little", signed=True)
        record = {
            "code": 0x126A,
            "kind": 0,
            "unionTag": 0x6A,
            "serializedMemberCount": 0x12,
            "payloadStart": 0,
            "nextId": 1,
        }
        decoded = decode_levelscript_record_payload(
            bytes(payload),
            record,
            next_start=len(payload),
            action_map_role="headerList#1",
        )
        self.assertEqual(3, decoded["actionHeader"]["filterMask"])
        self.assertEqual(1, decoded["actionHeader"]["filterLevel"])
        event = decoded["nativeEventDetail"]
        self.assertEqual("Down", event["changedDirectionName"])
        self.assertEqual(40021, event["entityFilter"][0]["slotId"])
        self.assertEqual(0.1, event["hpRatio"])

    def test_dynamic_hp_list_and_exact_spawner_writer_fields_decode(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        hp_payload = bytearray(35)
        hp_payload[4] = 1
        hp_payload[5:9] = (70).to_bytes(4, "little", signed=True)
        hp_payload[17] = 4
        hp_payload[18] = 1
        hp_payload[19:23] = (68).to_bytes(4, "little", signed=True)
        hp_payload[23:27] = (-1).to_bytes(4, "little", signed=True)
        hp_payload[27:31] = (-1).to_bytes(4, "little", signed=True)
        hp_payload[31:35] = (0).to_bytes(4, "little", signed=True)
        list_path = b"entity03_01"
        hp_payload.extend(
            b"\x04" + b"\xff" * 8
            + (100).to_bytes(4, "little", signed=True)
            + len(list_path).to_bytes(4, "little", signed=True)
            + list_path
            + b"\xff\x04"
            + struct.pack("<f", 0.01)
            + tail
        )

        hp = decode_levelscript_record_payload(
            bytes(hp_payload),
            {
                "payloadStart": 0,
                "code": 0x126A,
                "kind": 0,
                "unionTag": 0x6A,
                "serializedMemberCount": 18,
                "nextId": 0,
            },
            next_start=len(hp_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual("entity03_01", hp["entityListFilter"]["path"])
        self.assertEqual(0.01, hp["hpRatio"])
        self.assertFalse(hp["serverExchange"])

        value_path = b"$42@_entityOutput"
        writer_payload = (
            b"\x04" + b"\xff" * 8
            + (100).to_bytes(4, "little", signed=True)
            + len(list_path).to_bytes(4, "little", signed=True)
            + list_path
            + b"\x04\x03" + b"\x00" * 13
            + (-1).to_bytes(4, "little", signed=True)
            + (100).to_bytes(4, "little", signed=True)
            + len(value_path).to_bytes(4, "little", signed=True)
            + value_path
        )
        writer = decode_levelscript_record_payload(
            writer_payload,
            {
                "payloadStart": 0,
                "code": 0x0166,
                "kind": 0x0A,
                "unionTag": 0x0166,
                "serializedMemberCount": 10,
                "nextId": 44,
            },
            next_start=len(writer_payload),
            action_map_role="actionList#1 root",
        )
        self.assertEqual("ListAddValueEntityPtr", writer["actionBaseAction"])
        self.assertEqual(
            42,
            writer["listAddValueEntityPtr"]["valueEntity"]["sourceHeaderLocalId"],
        )
        self.assertEqual(
            "entity03_01",
            writer["listAddValueEntityPtr"]["destinationList"]["path"],
        )

        def output_ref(value: bytes) -> bytes:
            return b"\x02" + (0).to_bytes(4, "little") + len(value).to_bytes(4, "little") + value

        group_key = b"101"
        spawn_payload = bytearray(17)
        spawn_payload[5:9] = (43).to_bytes(4, "little", signed=True)
        spawn_payload.extend(b"\x04\x01" + tail)
        spawn_payload.extend(output_ref(b"$42@_entityOutput"))
        spawn_payload.extend(b"\x04" + (8).to_bytes(4, "little", signed=True) + tail)
        spawn_payload.extend(
            b"\x04" + len(group_key).to_bytes(4, "little") + group_key + tail
        )
        spawn_payload.extend(output_ref(b"$42@_groupKeyOutput"))
        spawn_payload.extend(
            b"\x04" + (23100270003).to_bytes(8, "little") + tail + b"\xff"
        )
        spawn_payload.extend(output_ref(b"$42@_waveKeyOutput"))
        spawn = decode_levelscript_record_payload(
            bytes(spawn_payload),
            {
                "payloadStart": 0,
                "code": 0x1594,
                "kind": 0,
                "unionTag": 0x94,
                "serializedMemberCount": 21,
                "localId": 42,
                "nextId": 0,
            },
            next_start=len(spawn_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual(23100270003, spawn["spawnerFilterId"])
        self.assertEqual("101", spawn["groupKeyFilter"])
        self.assertEqual("$42@_entityOutput", spawn["entityOutputRef"])
        self.assertFalse(spawn["serverExchange"])

        lifecycle_payload = bytearray(17)
        lifecycle_payload[5:9] = (36).to_bytes(4, "little", signed=True)
        lifecycle_payload.extend(b"\x04\x01" + tail)
        lifecycle_payload.extend(output_ref(b"$35@_entityOutput"))
        lifecycle_payload.extend(b"\x04" + (0).to_bytes(4, "little", signed=True) + tail)
        lifecycle_payload.extend(b"\xff")
        lifecycle_payload.extend(output_ref(b"$35@_groupKeyOutput"))
        lifecycle_payload.extend(
            b"\x04" + (23100080001).to_bytes(8, "little") + tail + b"\xff"
        )
        lifecycle_payload.extend(output_ref(b"$35@_waveKeyOutput"))
        lifecycle = decode_levelscript_record_payload(
            bytes(lifecycle_payload),
            {
                "payloadStart": 0,
                "code": 0x1591,
                "kind": 0,
                "unionTag": 0x91,
                "serializedMemberCount": 21,
                "localId": 35,
                "nextId": 36,
            },
            next_start=len(lifecycle_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual(23100080001, lifecycle["spawnerFilterId"])
        self.assertNotIn("groupKeyFilter", lifecycle)
        self.assertNotIn("waveKeyFilter", lifecycle)
        self.assertEqual("$35@_entityOutput", lifecycle["entityOutputParam"]["path"])
        self.assertFalse(lifecycle["serverExchange"])

    def test_action_header_decodes_exact_local_validation_getter(self):
        payload = bytearray(31)
        payload[5:9] = (102).to_bytes(4, "little", signed=True)
        payload[17] = 4
        payload[18] = 1
        payload[19:23] = (100).to_bytes(4, "little", signed=True)
        payload[23:27] = (-1).to_bytes(4, "little", signed=True)
        payload[27:31] = (-1).to_bytes(4, "little", signed=True)
        record = {
            "code": 0x104C,
            "kind": 0,
            "unionTag": 0x4C,
            "serializedMemberCount": 16,
            "payloadStart": 0,
            "nextId": -1,
        }
        decoded = decode_levelscript_record_payload(
            bytes(payload),
            record,
            next_start=len(payload),
            action_map_role="headerList#1",
        )
        header = decoded["actionHeader"]
        self.assertEqual(102, header["nextId"])
        self.assertEqual(100, header["validateGetterLocalId"])
        self.assertEqual(
            "action-header-validate-local-getter",
            header["validateParam"]["payloadShape"],
        )

        payload[23:27] = (7).to_bytes(4, "little", signed=True)
        rejected = decode_levelscript_record_payload(
            bytes(payload),
            record,
            next_start=len(payload),
            action_map_role="headerList#1",
        )
        self.assertNotIn("validateParam", rejected["actionHeader"])

    def test_npc_patrol_checkpoint_decodes_exact_dynamic_selector(self):
        tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        payload = bytearray(17)
        payload[5:9] = (50).to_bytes(4, "little", signed=True)
        payload.extend(b"\x04\x01" + tail)
        alias = b"Robot2"
        payload.extend(
            b"\x04\x03" + b"\x00" * 13
            + (-1).to_bytes(4, "little", signed=True)
            + (200).to_bytes(4, "little", signed=True)
            + len(alias).to_bytes(4, "little", signed=True)
            + alias
        )
        payload.extend(b"\x04" + (10001).to_bytes(4, "little", signed=True) + tail)
        payload.extend(b"\x04" + (8).to_bytes(4, "little", signed=True) + tail)
        output = b"$49@_npcPosition"
        payload.extend(
            b"\xff\x02" + (0).to_bytes(4, "little")
            + len(output).to_bytes(4, "little") + output + b"\xff\xff"
        )
        detail = decode_levelscript_record_payload(
            bytes(payload),
            {
                "payloadStart": 0,
                "code": 0x157C,
                "kind": 0,
                "unionTag": 0x7C,
                "serializedMemberCount": 21,
                "localId": 49,
                "nextId": 0,
                "plainStrings": [
                    {"text": "Robot2"},
                    {"text": "$49@_npcPosition"},
                ],
            },
            next_start=len(payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual("Robot2", detail["npcEntityFilter"]["path"])
        self.assertEqual(10001, detail["patrolIdFilter"])
        self.assertEqual(8, detail["checkpointIndexFilter"])
        self.assertEqual("npcPosition", detail["npcPositionOutputRefs"][0]["field"])
        self.assertFalse(detail["serverExchange"])

    def test_native_event_fields_label_battle_custom_guide_and_trigger_payloads(self):
        battle_payload = bytes.fromhex(
            "00 00 00 00 00 66 00 00 00 00 00 00 00 00 00 00 00 "
            "04 01 64 00 00 00 ff ff ff ff ff ff ff ff 02 00 00 00 "
            "00 10 00 00 00 24 31 30 31 40 5f 66 6c 6f 61 74 56 "
            "61 6c 75 65 04 0d 00 00 00 72 61 64 69 6f 5f 65 30 "
            "6d 30 5f 31 33 ff ff ff ff 00 00 00 00 ff ff ff ff"
        )
        battle = decode_levelscript_record_payload(
            battle_payload,
            {
                "code": 0x104C,
                "kind": 0,
                "unionTag": 0x4C,
                "serializedMemberCount": 0x10,
                "payloadStart": 0,
                "nextId": 0,
                "strings": [
                    {"text": "radio_e0m0_13"},
                    {"text": "$101@_floatValue"},
                ],
            },
            next_start=len(battle_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual("radio_e0m0_13", battle["signalId"])
        self.assertEqual(
            "$101@_floatValue",
            battle["floatValueOutputRefs"][0]["ref"],
        )
        self.assertEqual("local-level-runtime-event", battle["transport"])
        self.assertFalse(battle["serverExchange"])
        self.assertFalse(battle["clientRequest"])
        self.assertFalse(battle["expectedServerReturn"])
        self.assertFalse(battle["serializedMissionOrQuestId"])

        custom_payload = bytearray(80)
        custom_payload[5:9] = (12).to_bytes(4, "little", signed=True)
        custom = decode_levelscript_record_payload(
            bytes(custom_payload),
            {
                "code": 0x12BA,
                "kind": 0,
                "unionTag": 0xBA,
                "serializedMemberCount": 0x12,
                "payloadStart": 0,
                "nextId": 0,
                "strings": [
                    {"text": "TigerStart"},
                    {"text": "$11@_eventArgsPtr"},
                ],
            },
            next_start=len(custom_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual("TigerStart", custom["eventKey"])
        self.assertEqual("eventArgsPtr", custom["eventArgsOutputRefs"][0]["field"])

        guide_payload = bytearray(80)
        guide_payload[5:9] = (13).to_bytes(4, "little", signed=True)
        guide = decode_levelscript_record_payload(
            bytes(guide_payload),
            {
                "code": 0x1270,
                "kind": 0,
                "unionTag": 0x70,
                "serializedMemberCount": 0x12,
                "payloadStart": 0,
                "nextId": 0,
                "strings": [
                    {"text": "guide_battle_enemy_intro"},
                    {"text": "$0@_guideId"},
                ],
            },
            next_start=len(guide_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual("guide_battle_enemy_intro", guide["guideIdFilter"])
        self.assertEqual("guideId", guide["guideIdOutputRefs"][0]["field"])

        manual_guide = decode_levelscript_record_payload(
            bytes(48),
            {
                "code": 0x0304,
                "kind": 0x09,
                "payloadStart": 0,
                "nextId": -1,
                "strings": [{"text": "guide_group_camille_skill_intro"}],
            },
            next_start=48,
            action_map_role="actionList#1",
        )
        self.assertEqual(
            "ManuallyStartGuideGroup",
            manual_guide["actionBaseAction"],
        )
        self.assertEqual(
            "guide_group_camille_skill_intro",
            manual_guide["guideId"],
        )

        param_tail = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"
        trigger_payload = (
            bytes(17)
            + b"\x04\x01"
            + param_tail
            + b"\xff"
            + (0).to_bytes(4, "little", signed=True)
            + b"\x04"
            + (80001).to_bytes(4, "little", signed=True)
            + param_tail
            + b"\xff"
        )
        trigger = decode_levelscript_record_payload(
            trigger_payload,
            {
                "code": 0x12BE,
                "kind": 0,
                "unionTag": 0xBE,
                "serializedMemberCount": 0x12,
                "payloadStart": 0,
                "nextId": 0,
                "strings": [{"text": "$36@_triggerSlotIdOutput"}],
            },
            next_start=len(trigger_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual(80001, trigger["triggerSlotIdFilter"])
        self.assertEqual(
            "triggerSlotIdOutput",
            trigger["triggerSlotIdOutputRefs"][0]["field"],
        )

        dynamic_output_payload = trigger_payload[:-1] + (
            b"\x02"
            + (100).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        dynamic_output = decode_levelscript_record_payload(
            dynamic_output_payload,
            {
                "code": 0x12BE,
                "kind": 0,
                "unionTag": 0xBE,
                "serializedMemberCount": 0x12,
                "payloadStart": 0,
                "nextId": 0,
                "strings": [],
            },
            next_start=len(dynamic_output_payload),
            action_map_role="headerList#1",
        )["nativeEventDetail"]
        self.assertEqual(80001, dynamic_output["triggerSlotIdFilter"])
        self.assertEqual(
            {"paramSource": 100, "path": None},
            dynamic_output["triggerSlotIdOutputParam"],
        )

    def test_pos_tracking_matches_exact_event_selected_trigger_center(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "90000000001.json"
            source_path.write_bytes(b"fixture")
            occurrence = {
                "levelId": "map_fixture_lv001",
                "scriptId": "90000000001",
                "sourceFile": str(source_path),
                "nativeEventOwners": [{
                    "status": "exact_serialized_control_path",
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "triggerSlotIds": [80001, 80002],
                    "eventDetail": {
                        "payloadSchemaStatus": (
                            "exact_current_build_memorypack_fields"
                        ),
                        "triggerSlotIdFilter": 80001,
                    },
                }],
            }
            tracking = {
                "type": "PosTrackingInfo",
                "sourceType": "trackingPos",
                "scene": "map_fixture_lv001",
                "position": {"x": 1.0, "y": 2.0, "z": 3.0},
            }
            summary = {
                "triggerVolumesDetails": {
                    "status": "present",
                    "parseStatus": "decoded",
                    "volumes": [{
                        "slotId": 80001,
                        "triggerVolumeType": "Leader",
                        "offset": 100,
                        "shapeList": {"shapes": [{
                            "shapeType": "Box",
                            "offset": 120,
                            "position": {"x": 1.0004, "y": 2.0, "z": 3.0},
                            "size": {"x": 4.0, "y": 5.0, "z": 6.0},
                        }]},
                    }],
                },
            }
            with mock.patch(
                "scripts.story_builder.level_bindings."
                "decode_levelscript_binary_file",
                return_value=summary,
            ):
                from scripts.story_builder import level_bindings

                level_bindings._LEVELSCRIPT_BINARY_SUMMARY_CACHE.clear()
                level_bindings._LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE.clear()
                matches = match_pos_tracking_leader_trigger_context(
                    occurrence,
                    tracking,
                )
                wrong_scene = match_pos_tracking_leader_trigger_context(
                    occurrence,
                    {**tracking, "scene": "map_fixture_lv002"},
                )

            self.assertEqual(1, len(matches))
            self.assertEqual(80001, matches[0]["triggerSlotId"])
            self.assertEqual([], wrong_scene)

    def test_pos_tracking_rejects_legacy_trigger_slot_aggregate(self):
        occurrence = {
            "levelId": "map_fixture_lv001",
            "scriptId": "90000000001",
            "sourceFile": "unused.bin",
            "nativeEventOwners": [{
                "status": "exact_serialized_control_path",
                "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                "triggerSlotIds": [80001, 80002],
            }],
        }
        tracking = {
            "type": "PosTrackingInfo",
            "sourceType": "trackingPos",
            "scene": "map_fixture_lv001",
            "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        }
        self.assertEqual(
            [],
            match_pos_tracking_leader_trigger_context(occurrence, tracking),
        )

    def test_tracking_point_containment_is_typed_rotated_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "90000000002.json"
            source_path.write_bytes(b"fixture")
            occurrence = {
                "levelId": "map_fixture_lv001",
                "scriptId": "90000000002",
                "sourceFile": str(source_path),
                "nativeEventOwners": [{
                    "status": (
                        "exact_serialized_control_path_equivalent_duplicates"
                    ),
                    "headerName": "ScriptEvent_OnLeaderEnterTriggerVolume",
                    "eventDetail": {
                        "payloadSchemaStatus": (
                            "exact_current_build_memorypack_fields"
                        ),
                        "triggerSlotIdFilter": 80001,
                    },
                }],
            }
            tracking = {
                "type": "MissionAreaTrackingInfo",
                "sourceType": "missionArea",
                "scene": "map_fixture_lv001",
                "position": {"x": 4.0, "y": 0.0, "z": 0.0},
            }
            box = {
                "shapeType": "Box",
                "offset": 120,
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
                "size": {"x": 2.0, "y": 2.0, "z": 10.0},
            }

            def summary(shapes):
                return {
                    "triggerVolumesDetails": {
                        "status": "present",
                        "parseStatus": "decoded",
                        "volumes": [{
                            "slotId": 80001,
                            "triggerVolumeType": "Leader",
                            "offset": 100,
                            "shapeList": {"shapes": shapes},
                        }],
                    },
                }

            with mock.patch(
                "scripts.story_builder.level_bindings."
                "decode_levelscript_binary_file",
                return_value=summary([box]),
            ):
                from scripts.story_builder import level_bindings

                level_bindings._LEVELSCRIPT_BINARY_SUMMARY_CACHE.clear()
                level_bindings._LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE.clear()
                matches = match_tracking_point_inside_leader_trigger_context(
                    occurrence,
                    tracking,
                )
            self.assertEqual(1, len(matches))
            self.assertEqual(
                "oriented_box_euler_zxy",
                matches[0]["containmentMethod"],
            )
            self.assertFalse(matches[0]["questActivation"])
            self.assertFalse(matches[0]["storyOrderEvidence"])

            with mock.patch(
                "scripts.story_builder.level_bindings."
                "decode_levelscript_binary_file",
                return_value=summary([box, dict(box, offset=140)]),
            ):
                level_bindings._LEVELSCRIPT_BINARY_SUMMARY_CACHE.clear()
                level_bindings._LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE.clear()
                ambiguous = match_tracking_point_inside_leader_trigger_context(
                    occurrence,
                    tracking,
                )
            self.assertEqual([], ambiguous)
            self.assertEqual(
                [],
                match_tracking_point_inside_leader_trigger_context(
                    occurrence,
                    {**tracking, "scene": "map_fixture_lv002"},
                ),
            )

    def test_resolved_mission_tracking_rows_preserve_exact_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mission_path = root / "mission_general.json"
            mission_path.write_text(json.dumps({
                "missionId": "mission_general",
                "questDic": {
                    "mission_general_q#1": {
                        "questId": "mission_general_q#1",
                        "objectiveList": [{
                            "trackingInfoList": [{
                                "$type": "Beyond.Gameplay.PosTrackingInfo",
                                "sceneId": "map_fixture_lv001",
                                "trackingPos": {
                                    "x": 1.0, "y": 2.0, "z": 3.0,
                                },
                            }],
                        }],
                    },
                },
            }), encoding="utf-8")
            rows = build_resolved_mission_tracking_context_rows(
                {"mission_general"},
                mission_runtime_root=root,
            )
            no_rows = build_resolved_mission_tracking_context_rows(
                set(),
                mission_runtime_root=root,
            )
        self.assertEqual(1, len(rows))
        self.assertEqual([], no_rows)
        self.assertEqual("mission_general_q#1", rows[0]["questId"])
        self.assertEqual("trackingPos", rows[0]["sourceType"])
        self.assertEqual(
            "$.questDic.mission_general_q#1.objectiveList[0].trackingInfoList[0]",
            rows[0]["missionRuntimeSourcePath"],
        )

    def test_exact_header_and_if_else_path_reaches_black_without_adjacency(self):
        header = {
            "code": 0x1052,
            "kind": 0x00,
            "start": 10,
            "localId": 1,
            "nextId": 0,
            "strings": [{"text": "rookie"}],
            "plainStrings": [],
            "unionTag": 0x52,
            "serializedMemberCount": 0x10,
        }
        gate = {
            "code": 0x00FF,
            "kind": 0x0B,
            "start": 100,
            "localId": 2,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        black = {
            "code": 0x04A5,
            "kind": 0x1B,
            "start": 200,
            "localId": 3,
            "nextId": -1,
            "strings": [{"text": "black_testm1_1_001"}],
            "plainStrings": [],
        }
        predicate_getter = {
            "code": 0x01C2,
            "kind": 0x08,
            "unionTag": 0x01C2,
            "serializedMemberCount": 0x08,
            "start": 250,
            "localId": 5,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        decoy = {
            "code": 0x0495,
            "kind": 0x09,
            "start": 300,
            "localId": 4,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        records = [header, gate, black, predicate_getter, decoy]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 root",
            250: "getterList#1 root",
            300: "actionList#3 root",
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 2}}
            if record is gate:
                return {
                    "conditionGetterLocalId": 5,
                    "falseActionLocalId": 4,
                    "trueActionLocalId": 3,
                }
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            paths = _levelscript_native_control_paths_to_record(
                bytes(400), records, membership, black
            )
        self.assertEqual(1, len(paths))
        self.assertEqual("LevelEvent_OnCustomEvent", paths[0]["headerName"])
        self.assertEqual([2, 3], paths[0]["pathLocalIds"])
        self.assertEqual("IfElseAction.trueAction", paths[0]["path"][-1]["edge"])
        self.assertEqual(
            "IsEndminGender",
            paths[0]["path"][0]["branchPredicate"]["getterName"],
        )

    def test_control_path_uses_final_runtime_slot_for_duplicate_ids(self):
        header = {
            "code": 0x1052,
            "kind": 0x00,
            "start": 10,
            "localId": 1,
            "nextId": 0,
            "strings": [],
            "plainStrings": [],
        }
        duplicate_a = {
            "code": 0x0495,
            "kind": 0x09,
            "start": 100,
            "localId": 7,
            "nextId": -1,
            "strings": [],
            "plainStrings": [],
        }
        duplicate_b = {**duplicate_a, "start": 200}
        target = {
            "code": 0x0357,
            "kind": 0x14,
            "start": 300,
            "localId": 8,
            "nextId": -1,
            "strings": [{"text": "cutscene_testm1_1"}],
            "plainStrings": [],
        }
        records = [header, duplicate_a, duplicate_b, target]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 root",
            300: "actionList#3 root",
        }

        def decode(_data, record, **_kwargs):
            if record is header:
                return {"actionHeader": {"nextId": 7}}
            if record in (duplicate_a, duplicate_b):
                return {"splitActionLocalIds": [8]}
            return {}

        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            paths = _levelscript_native_control_paths_to_record(
                bytes(400), records, membership, target
            )
        self.assertEqual(1, len(paths))
        self.assertEqual(
            "exact_serialized_control_path_runtime_shadowing",
            paths[0]["status"],
        )
        self.assertEqual(
            [100, 200],
            paths[0]["path"][0]["equivalentRecordOffsets"],
        )

        duplicate_b["nextId"] = 9
        with mock.patch(
            "scripts.story_builder.level_bindings.decode_levelscript_record_payload",
            side_effect=decode,
        ):
            paths = _levelscript_native_control_paths_to_record(
                bytes(400), records, membership, target
            )
        self.assertEqual(1, len(paths))
        self.assertEqual(
            [100],
            paths[0]["path"][0]["runtimeShadowedRecordOffsets"],
        )
        self.assertEqual(
            "different_payload",
            paths[0]["path"][0]["runtimeDuplicateSignatureStatus"],
        )

    def test_if_else_and_entity_compare_decode_exact_tracked_slot_bridge(self):
        if_else_payload = (
            b"\x04\x01"
            + (65).to_bytes(4, "little", signed=True)
            + b"\xff" * 8
            + (0).to_bytes(4, "little", signed=True)
            + (63).to_bytes(4, "little", signed=True)
        )
        if_else = decode_levelscript_record_payload(
            if_else_payload,
            {
                "code": 0x00FF,
                "kind": 0x0B,
                "unionTag": 0x00FF,
                "serializedMemberCount": 0x0B,
                "payloadStart": 0,
            },
            next_start=len(if_else_payload),
            action_map_role="actionList#1",
        )
        self.assertEqual(65, if_else["conditionGetterLocalId"])
        self.assertEqual(63, if_else["trueActionLocalId"])

        getter_payload = bytearray(84)
        getter_payload[0x20:0x24] = (100).to_bytes(4, "little")
        ref = b"$61@_entityOutput"
        getter_payload[0x24:0x28] = len(ref).to_bytes(4, "little")
        getter_payload[0x28:0x28 + len(ref)] = ref
        getter_payload[0x39:0x3B] = b"\x04\x03"
        getter_payload[0x3B:0x43] = (0).to_bytes(8, "little")
        getter_payload[0x43:0x47] = (40010).to_bytes(4, "little")
        getter_payload[0x47] = 1
        getter = decode_levelscript_record_payload(
            bytes(getter_payload),
            {
                "code": 0x0A28,
                "kind": 0,
                "unionTag": 0x28,
                "serializedMemberCount": 10,
                "payloadStart": 0,
                "strings": [{"text": "$61@_entityOutput"}],
            },
            next_start=len(getter_payload),
            action_map_role="getterList#1",
        )
        self.assertEqual(40010, getter["entityCompare"]["scriptEntity"]["slotId"])
        self.assertEqual(
            [{"localId": 61, "field": "entityOutput", "ref": "$61@_entityOutput"}],
            getter["entityCompare"]["propertyOutputRefs"],
        )

    def test_exact_mission_state_getter_and_compare_operands_decode(self):
        default_tail = (
            (-1).to_bytes(4, "little", signed=True)
            + (0).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )

        def getter_record(
            union_tag: int,
            member_count: int,
            local_id: int,
            uid: bytes,
            subtype: bytes,
        ) -> bytes:
            tag = (
                b"\xfa" + union_tag.to_bytes(2, "little")
                if union_tag > 0xFF
                else bytes([union_tag])
            )
            return (
                tag
                + bytes([member_count, 0])
                + local_id.to_bytes(4, "little", signed=True)
                + b"\x00"
                + len(uid).to_bytes(4, "little")
                + uid
                + (1).to_bytes(4, "little")
                + b"\x00\x01"
                + subtype
            )

        mission_id = b"a1m6d6"
        get_blob = getter_record(
            0x013A,
            8,
            221,
            b"d91b3067",
            b"\x04" + len(mission_id).to_bytes(4, "little") + mission_id + default_tail,
        )
        get_record = extract_levelscript_uid_records(get_blob)[0]
        get_detail = decode_levelscript_record_payload(
            get_blob,
            get_record,
            next_start=len(get_blob),
            action_map_role="getterList#1",
        )["getMissionState"]
        self.assertEqual("a1m6d6", get_detail["missionId"])
        self.assertEqual("constant-mission-id-exact-eof", get_detail["payloadShape"])

        constant_i32 = lambda value: (
            b"\x04" + value.to_bytes(4, "little", signed=True) + default_tail
        )
        getter_ref = (
            b"\x04"
            + (0).to_bytes(4, "little", signed=True)
            + (221).to_bytes(4, "little", signed=True)
            + b"\xff" * 8
        )
        compare_blob = getter_record(
            0x001F,
            10,
            222,
            b"c895a2f3",
            constant_i32(1) + getter_ref + constant_i32(3),
        )
        compare_record = extract_levelscript_uid_records(compare_blob)[0]
        compare_detail = decode_levelscript_record_payload(
            compare_blob,
            compare_record,
            next_start=len(compare_blob),
            action_map_role="getterList#2",
        )["compareMissionState"]
        self.assertEqual(1, compare_detail["comparerRaw"])
        self.assertEqual("NotEqual", compare_detail["comparerName"])
        self.assertEqual(221, compare_detail["valueAGetterLocalId"])
        self.assertEqual(3, compare_detail["valueBStateRaw"])
        self.assertEqual("Completed", compare_detail["valueBStateName"])
        self.assertFalse(get_detail["serverExchange"])

        constant_bool = lambda value: (
            b"\x04" + bytes([int(value)]) + default_tail
        )
        boolean_blob = getter_record(
            0x0004,
            10,
            223,
            b"8e43c761",
            constant_i32(1)
            + constant_bool(True)
            + constant_bool(False)
            + (3).to_bytes(4, "little"),
        )
        boolean_record = extract_levelscript_uid_records(boolean_blob)[0]
        boolean_detail = decode_levelscript_record_payload(
            boolean_blob,
            boolean_record,
            next_start=len(boolean_blob),
            action_map_role="getterList#3",
        )["booleanCompare"]
        self.assertEqual("NotEqual", boolean_detail["comparerName"])
        self.assertTrue(boolean_detail["valueA"]["value"])
        self.assertFalse(boolean_detail["valueB"]["value"])
        self.assertEqual(3, boolean_detail["trailingActionMapFramingU32"])

        int_equal_blob = getter_record(
            0x01AC,
            9,
            224,
            b"e722f08a",
            constant_i32(7) + constant_i32(3),
        )
        int_equal_record = extract_levelscript_uid_records(int_equal_blob)[0]
        int_equal_detail = decode_levelscript_record_payload(
            int_equal_blob,
            int_equal_record,
            next_start=len(int_equal_blob),
            action_map_role="getterList#4",
        )["intEqual"]
        self.assertEqual("Equal", int_equal_detail["operation"])
        self.assertEqual(7, int_equal_detail["valueA"]["value"])
        self.assertEqual(3, int_equal_detail["valueB"]["value"])

        int_equal_ref_blob = getter_record(
            0x01AC,
            9,
            225,
            b"f722f08a",
            getter_ref + constant_i32(0),
        )
        int_equal_ref_record = extract_levelscript_uid_records(
            int_equal_ref_blob
        )[0]
        int_equal_ref_detail = decode_levelscript_record_payload(
            int_equal_ref_blob,
            int_equal_ref_record,
            next_start=len(int_equal_ref_blob),
            action_map_role="getterList#5",
        )["intEqual"]
        self.assertEqual(221, int_equal_ref_detail["valueAGetterLocalId"])
        self.assertEqual(
            "localGetterRef",
            int_equal_ref_detail["valueA"]["operandKind"],
        )
        self.assertEqual(0, int_equal_ref_detail["valueB"]["value"])

        compact_string = lambda value: (
            len(value).to_bytes(4, "little") + value
        )
        fmv_condition = (
            b"\x39\x05"
            + (1).to_bytes(4, "little", signed=True)
            + compact_string(b"12345678")
            + b"\x00\x01"
            + b"\x04"
            + compact_string(b"cs_video_fixture")
            + default_tail
        )
        condition_blob = getter_record(
            0x004E,
            8,
            226,
            b"a722f08a",
            fmv_condition,
        )
        condition_record = extract_levelscript_uid_records(condition_blob)[0]
        condition_detail = decode_levelscript_record_payload(
            condition_blob,
            condition_record,
            next_start=len(condition_blob),
            action_map_role="getterList#6",
        )["getConditionResult"]
        self.assertEqual("CheckFMVFinish", condition_detail["condition"]["type"])
        self.assertEqual(
            "cs_video_fixture",
            condition_detail["condition"]["fmvId"]["value"],
        )

        malformed_condition_blob = bytearray(condition_blob)
        condition_offset = malformed_condition_blob.index(b"\x39\x05")
        malformed_condition_blob[condition_offset + 1] = 6
        malformed_condition_record = extract_levelscript_uid_records(
            bytes(malformed_condition_blob)
        )[0]
        self.assertNotIn(
            "getConditionResult",
            decode_levelscript_record_payload(
                bytes(malformed_condition_blob),
                malformed_condition_record,
                next_start=len(malformed_condition_blob),
                action_map_role="getterList#6",
            ),
        )

        malformed_ref_blob = int_equal_ref_blob[:-1]
        malformed_ref_record = extract_levelscript_uid_records(
            malformed_ref_blob
        )[0]
        self.assertNotIn(
            "intEqual",
            decode_levelscript_record_payload(
                malformed_ref_blob,
                malformed_ref_record,
                next_start=len(malformed_ref_blob),
                action_map_role="getterList#5",
            ),
        )

        random_blob = getter_record(
            0x01BA,
            9,
            225,
            b"9c265984",
            constant_i32(5) + constant_i32(2),
        )
        random_record = extract_levelscript_uid_records(random_blob)[0]
        random_detail = decode_levelscript_record_payload(
            random_blob,
            random_record,
            next_start=len(random_blob),
            action_map_role="getterList#5",
        )["intRandom"]
        self.assertEqual(2, random_detail["minimum"]["value"])
        self.assertEqual(5, random_detail["maximum"]["value"])

        int_compare_blob = getter_record(
            0x01AA,
            10,
            226,
            b"0929ce54",
            constant_i32(3) + getter_ref + constant_i32(12),
        )
        int_compare_record = extract_levelscript_uid_records(int_compare_blob)[0]
        int_compare_detail = decode_levelscript_record_payload(
            int_compare_blob,
            int_compare_record,
            next_start=len(int_compare_blob),
            action_map_role="getterList#6",
        )["intCompare"]
        self.assertEqual("GreaterEqual", int_compare_detail["comparerName"])
        self.assertEqual(221, int_compare_detail["valueAGetterLocalId"])
        self.assertEqual(12, int_compare_detail["valueB"]["value"])

        getter_int_blob = getter_record(
            0x0184,
            8,
            227,
            b"a7c4870d",
            constant_i32(9),
        )
        getter_int_record = extract_levelscript_uid_records(getter_int_blob)[0]
        getter_int_detail = decode_levelscript_record_payload(
            getter_int_blob,
            getter_int_record,
            next_start=len(getter_int_blob),
            action_map_role="getterList#7",
        )["getterInt"]
        self.assertEqual(9, getter_int_detail["value"]["value"])

        current_script_ptr = (
            b"\x04"
            + (0).to_bytes(8, "little")
            + (0).to_bytes(8, "little")
            + (-1).to_bytes(4, "little", signed=True)
            + (1002).to_bytes(4, "little", signed=True)
            + (-1).to_bytes(4, "little", signed=True)
        )
        stage_blob = getter_record(
            0x012F,
            8,
            228,
            b"af227158",
            current_script_ptr + (2).to_bytes(4, "little"),
        )
        stage_record = extract_levelscript_uid_records(stage_blob)[0]
        stage_detail = decode_levelscript_record_payload(
            stage_blob,
            stage_record,
            next_start=len(stage_blob),
            action_map_role="getterList#8",
        )["getLevelScriptStage"]
        self.assertEqual("current_script", stage_detail["scriptPtr"]["mode"])
        self.assertEqual(2, stage_detail["trailingActionMapFramingU32"])

        gender_blob = getter_record(
            0x01C2,
            8,
            229,
            b"cb7fd156",
            constant_i32(1) + (15).to_bytes(4, "little"),
        )
        gender_record = extract_levelscript_uid_records(gender_blob)[0]
        gender_detail = decode_levelscript_record_payload(
            gender_blob,
            gender_record,
            next_start=len(gender_blob),
            action_map_role="getterList#9",
        )["isEndminGender"]
        self.assertEqual("Female", gender_detail["genderName"])

        property_key = b"isTalkFinished"
        explicit_target = (
            b"\x04"
            + (22800700001).to_bytes(8, "little")
            + (0).to_bytes(8, "little")
            + default_tail
        )
        property_blob = getter_record(
            0x0100,
            9,
            230,
            b"f96ad36e",
            b"\x04"
            + len(property_key).to_bytes(4, "little")
            + property_key
            + default_tail
            + explicit_target
            + (3).to_bytes(4, "little"),
        )
        property_record = extract_levelscript_uid_records(property_blob)[0]
        property_detail = decode_levelscript_record_payload(
            property_blob,
            property_record,
            next_start=len(property_blob),
            action_map_role="getterList#10",
        )["getLevelScriptPropertyGenericBool"]
        self.assertEqual("isTalkFinished", property_detail["propertyKey"])
        self.assertEqual("22800700001", property_detail["targetScript"]["scriptId"])

        stage_check_blob = getter_record(
            0x0013,
            10,
            231,
            b"0ce4d2aa",
            constant_i32(0) + current_script_ptr + constant_i32(4),
        )
        stage_check_record = extract_levelscript_uid_records(stage_check_blob)[0]
        stage_check = decode_levelscript_record_payload(
            stage_check_blob,
            stage_check_record,
            next_start=len(stage_check_blob),
            action_map_role="getterList#11",
        )["checkLevelScriptStage"]
        self.assertEqual("Equal", stage_check["comparerName"])
        self.assertEqual("current_script", stage_check["scriptPtr"]["mode"])
        self.assertEqual(4, stage_check["expectedStage"]["value"])

        quest_id = b"sm1l1m2_q#7"
        completion_blob = getter_record(
            0x0016,
            9,
            232,
            b"4ec92d36",
            constant_bool(True)
            + b"\x04"
            + len(quest_id).to_bytes(4, "little")
            + quest_id
            + default_tail,
        )
        completion_record = extract_levelscript_uid_records(completion_blob)[0]
        completion = decode_levelscript_record_payload(
            completion_blob,
            completion_record,
            next_start=len(completion_blob),
            action_map_role="getterList#12",
        )["checkMissionOrQuestIsComplete"]
        self.assertTrue(completion["isQuest"]["value"])
        self.assertEqual("quest", completion["targetKind"])
        self.assertEqual("sm1l1m2_q#7", completion["missionOrQuestId"])
        self.assertEqual("Completed", completion["completedStateName"])

        malformed_completion = decode_levelscript_record_payload(
            completion_blob[:-1],
            completion_record,
            next_start=len(completion_blob) - 1,
            action_map_role="getterList#12",
        )
        self.assertNotIn(
            "checkMissionOrQuestIsComplete",
            malformed_completion,
        )

    def records(self):
        return [
            {
                "code": 0x1385,
                "kind": 0x00,
                "start": 10,
                "localId": 40,
                "nextId": 0,
                "strings": [{"text": "testm1_q#2"}],
                "plainStrings": [],
            },
            {
                "code": 0x0363,
                "kind": 0x0D,
                "start": 100,
                "localId": 15,
                "nextId": 16,
                "strings": [{"text": "radio_testm1_2"}],
                "plainStrings": [],
            },
            {
                "code": 0x0E34,
                "kind": 0x00,
                "start": 200,
                "localId": 16,
                "nextId": -1,
                "strings": [],
                "plainStrings": [{"text": "radio_not_a_tagged_action_payload"}],
            },
        ]

    def membership(self):
        return {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 linked",
        }

    def decoded_header(self, state=3):
        return {
            "taggedFields": [{"offset": "0x1f", "i32": state}],
            "actionHeader": {"nextId": 15},
        }

    def recover(self, records, *, state=3, membership=None):
        with (
            mock.patch.object(
                mission_flow,
                "levelscript_action_map_membership",
                return_value=({}, membership or self.membership()),
            ),
            mock.patch.object(
                mission_flow,
                "decode_levelscript_record_payload",
                return_value=self.decoded_header(state),
            ),
        ):
            return mission_flow._levelscript_quest_state_changed_connections_from_file(
                bytes(320),
                records,
                level_id="map_test",
                script_id="1001",
                source_file="LevelScriptData/map_test/1001.json",
            )

    def test_completed_quest_event_attaches_tagged_action_story_payload(self):
        rows = self.recover(self.records())["testm1_q#2"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "radio_testm1_2")
        self.assertEqual(rows[0]["relation"], "levelscript_quest_completed_action")
        self.assertEqual(rows[0]["direction"], "quest_to_story")
        self.assertEqual(rows[0]["phase"], "succeed")
        self.assertEqual(rows[0]["questState"], 3)
        self.assertEqual(rows[0]["actionLocalId"], 15)
        self.assertEqual(rows[0]["actionPathIndex"], 0)
        self.assertEqual(rows[0]["actionPathLocalIds"], [15, 16])
        self.assertEqual(rows[0]["sourceFile"], "LevelScriptData/map_test/1001.json")

    def test_processing_quest_event_attaches_tagged_action_story_payload(self):
        rows = self.recover(self.records(), state=2)["testm1_q#2"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "radio_testm1_2")
        self.assertEqual(rows[0]["relation"], "levelscript_quest_processing_action")
        self.assertEqual(rows[0]["phase"], "start")
        self.assertEqual(rows[0]["questState"], 2)
        self.assertEqual(rows[0]["questStateName"], "Processing")

    def test_unknown_quest_state_is_not_attached(self):
        self.assertEqual(self.recover(self.records(), state=10), {})

    def test_mission_reference_filter_covers_all_exported_id_families(self):
        for value in (
            "a1m6d2_q#2",
            "c16m4d5",
            "db01m2d1_q#4",
            "dm01m1",
            "e11m1_q#25",
            "f1m32_q#Side1CompleteSNS",
            "gm02m15_q#7",
            "m1m74_q#2",
            "sm2l6m1_q#Encounter",
            "hidden42_a1m9ending",
        ):
            self.assertIsNotNone(LEVELSCRIPT_MISSIONISH_RE.fullmatch(value), value)
        for value in ("heal_ratio", "radio_e1m1_1", "map02_lv001"):
            self.assertIsNone(LEVELSCRIPT_MISSIONISH_RE.fullmatch(value), value)

    def test_native_black_action_requires_exact_unique_line_ownership(self):
        record = {
            "code": 0x0310,
            "kind": 0x14,
            "plainStrings": [
                {"text": "black_testm1_1_001", "offset": 120},
                {"text": "black_testm1_1_002", "offset": 144},
            ],
        }
        line_owner = {
            "black_testm1_1_001": "black_testm1_1",
            "black_testm1_1_002": "black_testm1_1",
        }
        matched = match_levelscript_native_black_record(record, line_owner)
        self.assertEqual(matched["key"], "black_testm1_1")
        self.assertEqual(
            matched["lineIds"],
            ["black_testm1_1_001", "black_testm1_1_002"],
        )

        mixed_owner = {**line_owner, "black_testm1_1_002": "black_otherm1_1"}
        self.assertIsNone(match_levelscript_native_black_record(record, mixed_owner))
        self.assertIsNone(match_levelscript_native_black_record(record, {}))

    def test_ambiguous_action_target_is_not_attached(self):
        records = self.records()
        records.append({
            "code": 0x0364,
            "kind": 0x0D,
            "start": 150,
            "localId": 15,
            "nextId": -1,
            "strings": [{"text": "radio_testm1_ambiguous"}],
            "plainStrings": [],
        })
        membership = {**self.membership(), 150: "actionList#2 root"}
        self.assertEqual(self.recover(records, membership=membership), {})

    def test_tagged_story_text_in_non_playback_action_is_not_attached(self):
        records = self.records()
        records[1]["code"] = 0x035B
        records[1]["kind"] = 0x0C
        self.assertEqual(self.recover(records), {})

    def test_processing_quest_state_gate_attaches_as_context(self):
        records = [
            {
                "code": 0x12BE,
                "kind": 0x00,
                "start": 10,
                "localId": 7,
                "nextId": 0,
                "strings": [],
                "plainStrings": [],
            },
            {
                "code": 0x04F0,
                "kind": 0x09,
                "start": 100,
                "payloadStart": 120,
                "localId": 8,
                "nextId": 10,
                "strings": [{"text": "f1m5_q#18"}],
                "plainStrings": [],
            },
            {
                "code": 0x0363,
                "kind": 0x0D,
                "start": 200,
                "localId": 10,
                "nextId": -1,
                "strings": [{"text": "radio_f1m5_2"}],
                "plainStrings": [],
            },
        ]
        membership = {
            10: "headerList#1",
            100: "actionList#1 root",
            200: "actionList#2 linked",
        }
        data = bytearray(320)
        data[120] = 0x7E

        def decode(_data, record, **_kwargs):
            if record["localId"] == 7:
                return {"actionHeader": {"nextId": 8}}
            if record["localId"] == 8:
                return {
                    "taggedFields": [
                        {"type": "scalar", "i32": 0},
                        {"type": "string", "value": "f1m5_q#18"},
                        {"type": "scalar", "i32": 2},
                    ],
                }
            return {}

        with (
            mock.patch.object(
                mission_flow,
                "levelscript_action_map_membership",
                return_value=({}, membership),
            ),
            mock.patch.object(
                mission_flow,
                "decode_levelscript_record_payload",
                side_effect=decode,
            ),
        ):
            rows = mission_flow._levelscript_quest_state_gate_connections_from_file(
                bytes(data),
                records,
                level_id="map01_lv002",
                script_id="200190001",
                source_file="LevelScriptData/map01_lv002/200190001.json",
            )["f1m5_q#18"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "radio_f1m5_2")
        self.assertEqual(rows[0]["relation"], "levelscript_quest_state_gate")
        self.assertEqual(rows[0]["direction"], "context")
        self.assertEqual(rows[0]["conditionQuestState"], 2)
        self.assertEqual(
            rows[0]["sourceFile"],
            "LevelScriptData/map01_lv002/200190001.json",
        )


if __name__ == "__main__":
    unittest.main()
