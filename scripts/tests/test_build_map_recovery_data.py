import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_map_recovery_data as builder


class BuildMapRecoveryDataTests(unittest.TestCase):
    def test_e0m0_publishes_exact_reading_trigger_and_quest_coordinates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry.json"
            mission = root / "webui/data/lang/CN/mission/e0m0.json"
            mission.parent.mkdir(parents=True)
            registry.write_text(json.dumps({
                "worldEntityBriefInfos": {},
                "m_scriptEntityIdList": [{"scriptIdGlobal": 8700020018, "slotId": 40001}],
                "m_scriptEntityBriefInfo": [{"entityType": 32, "detailId": "int_mission_beacon", "position": {"x": 1, "y": 2, "z": 3}}],
            }), encoding="utf-8")
            mission.write_text(json.dumps({"timelineRecovery": {"questSpatialTrack": [{"questId": "e0m0_q#10", "centroid": {"x": 1.1, "y": 2, "z": 3}}]}}), encoding="utf-8")
            receiver = {"text_e0m0_1": [{
                "sourceFile": "source.json",
                "interactiveEventProducers": [{"scriptIdGlobal": "8700020018", "entitySlotId": 40001, "eventName": "readepitaph"}],
            }]}
            with mock.patch.object(builder, "ROOT", root), mock.patch.object(builder, "REGISTRY", registry), mock.patch.object(
                builder, "build_levelscript_unhosted_reading_popup_receiver_index", return_value=receiver
            ):
                payload = builder.build_e0m0("CN")
            reading = next(row for row in payload["markers"] if row.get("storyKey") == "text_e0m0_1")
            self.assertEqual(reading["eventName"], "readepitaph")
            self.assertEqual(reading["position"], {"x": 1, "y": 2, "z": 3})
            self.assertEqual(payload["questPoints"][0]["questId"], "e0m0_q#10")
            self.assertEqual(payload["renderBackground"]["status"], "asset_transform_recovery_required")

    def test_e0m0_tomb_marker_uses_tomb_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry.json"
            mission = root / "webui/data/lang/CN/mission/e0m0.json"
            mission.parent.mkdir(parents=True)
            registry.write_text(json.dumps({
                "worldEntityBriefInfos": {
                    "8700020001": {
                        "detailId": "int_narrative_common_BTomb01",
                        "position": {"x": 0, "y": 0, "z": 0},
                    },
                },
                "m_scriptEntityIdList": [],
                "m_scriptEntityBriefInfo": [],
            }), encoding="utf-8")
            mission.write_text(json.dumps({
                "timelineRecovery": {
                    "questSpatialTrack": [],
                    "scenePlacement": {},
                    "levelscriptSpatialProximity": [],
                },
            }), encoding="utf-8")
            receiver = {"text_e0m0_1": [{
                "sourceFile": "source.json",
                "interactiveEventProducers": [{"scriptIdGlobal": "8700020018", "entitySlotId": 40001, "eventName": "readepitaph"}],
            }]}
            with mock.patch.object(builder, "ROOT", root), mock.patch.object(builder, "REGISTRY", registry), mock.patch.object(
                builder, "build_levelscript_unhosted_reading_popup_receiver_index", return_value=receiver
            ):
                payload = builder.build_e0m0("CN")
            tombs = [row for row in payload["markers"] if row.get("detailId") == "int_narrative_common_BTomb01"]
            self.assertEqual(len(tombs), 1)
            self.assertEqual(tombs[0]["label"], "\u5893\u7891")

    def test_e0m0_collects_timeline_recovery_trigger_markers_and_links_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry.json"
            mission = root / "webui/data/lang/CN/mission/e0m0.json"
            mission.parent.mkdir(parents=True)
            registry.write_text(json.dumps({
                "worldEntityBriefInfos": {},
                "m_scriptEntityIdList": [],
                "m_scriptEntityBriefInfo": [],
            }), encoding="utf-8")
            mission.write_text(json.dumps({
                "timelineRecovery": {
                    "questSpatialTrack": [],
                    "scenePlacement": {
                        "scene_e0m0_1": {
                            "inheritedSpatialQuestCandidates": [{
                                "pin": {
                                    "sourceType": "missionArea",
                                    "missionAreaId": "e0m1_001",
                                    "label": "e0m1_001",
                                    "trackingType": "MissionAreaTrackingInfo",
                                    "mapId": "indie_dg002",
                                    "position": {"x": 10, "y": 20, "z": 30},
                                    "radius": 5.0,
                                },
                                "questId": "e0m0_q#1",
                                "file": "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700010007.json",
                                "scriptId": "8700010007",
                            }],
                        },
                    },
                    "levelscriptSpatialProximity": [{
                        "pin": {
                            "sourceType": "missionArea",
                            "missionAreaId": "e0m1_002",
                            "label": "e0m1_002",
                            "trackingType": "MissionAreaTrackingInfo",
                            "mapId": "indie_dg002",
                            "position": {"x": 100, "y": 40, "z": 60},
                        },
                        "questId": "e0m0_q#2",
                        "file": "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700020022.json",
                        "scriptId": "8700020022",
                    }],
                },
            }), encoding="utf-8")
            receiver = {"text_e0m0_1": [{
                "sourceFile": "source.json",
                "interactiveEventProducers": [{"scriptIdGlobal": "8700020018", "entitySlotId": 40001, "eventName": "readepitaph"}],
            }]}
            with mock.patch.object(builder, "ROOT", root), mock.patch.object(builder, "REGISTRY", registry), mock.patch.object(
                builder, "build_levelscript_unhosted_reading_popup_receiver_index", return_value=receiver
            ):
                payload = builder.build_e0m0("CN")
            triggers = [row for row in payload["markers"] if row["kind"] == "trigger" and row.get("pinLabel") in {"e0m1_001", "e0m1_002"}]
            self.assertEqual(len(triggers), 2)
            self.assertTrue(all("sourceFiles" in row and row["sourceFiles"] for row in triggers))
            self.assertIn("export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700010007.json", payload["linkedMissionFiles"])
            self.assertIn("export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700020022.json", payload["linkedMissionFiles"])


class RelatedFilePinningTests(unittest.TestCase):
    """The published pins carry their own evidence strength and stay fetchable."""

    def test_href_maps_both_published_path_spaces_onto_server_routes(self):
        self.assertEqual(
            builder._href("export_full/structured/a.json"),
            "/export_full/structured/a.json",
        )
        # serve.py mounts webui/ at the site root, so the `webui/` prefix has to
        # be dropped or the published dialog file would 404.
        self.assertEqual(builder._href("webui/data/lang/CN/conv/text_e0m0_1.json"), "/data/lang/CN/conv/text_e0m0_1.json")

    def test_related_rows_declare_strength_and_sort_by_usefulness(self):
        rows = [
            builder._related("a.json", "entity_registry", "registry"),
            builder._related("b.json", "story_proximity", "scene"),
            builder._related("c.json", "story_exact_producer", "text"),
        ]
        self.assertEqual([row["strength"] for row in rows], ["strong", "weak", "strong"])
        ordered = builder._sorted_related(rows)
        # The exact story wins over the level-wide registry file, and every weak
        # pin sorts after every strong one.
        self.assertEqual([row["path"] for row in ordered], ["c.json", "a.json", "b.json"])

    def test_resolved_slot_stops_the_story_reaching_the_scripts_other_slots(self):
        """A named slot is a gate, not a hint.

        `cutscene_e0m0_2ndZiplineA` names slot 40007 on producer 8700040013.
        Indexing it under the bare script id pinned it to slots 40004/40005/
        40006 as well - entities the same row proves are the wrong ones.
        """
        mission = {
            "flow": {
                "missionStoryConnections": [{
                    "key": "zipline_a",
                    "producerEntityPositionStatus": "exact_unique_world_entity_registry_script_slot",
                    "producerEntities": [{"scriptIdGlobal": "8700040013", "slotId": "40007"}],
                    "producerScriptIds": ["8700040013"],
                    "listenerScriptIds": ["8700010008"],
                    "anchorScriptIds": ["8700040001"],
                    "entitySlotIds": ["40007"],
                }],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["slot:8700040013:40007"]], ["zipline_a"])
        # Nothing may fall back to the whole script, the listener, or the
        # ordering anchor once the exact producer entity is known.
        self.assertNotIn("script:8700040013", index)
        self.assertNotIn("script:8700010008", index)
        self.assertNotIn("anchor:8700040001", index)

    def test_named_slots_without_a_registry_row_stay_slot_scoped(self):
        mission = {
            "flow": {
                "missionStoryConnections": [{
                    "key": "slotted",
                    "producerScriptIds": ["8700040013"],
                    "entitySlotIds": ["40006"],
                }],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["scriptslot:8700040013:40006"]], ["slotted"])
        self.assertNotIn("script:8700040013", index)

    def test_anchor_scripts_are_kept_apart_from_the_story_player(self):
        """Anchors order a scene; they are not the entity that plays it."""
        mission = {
            "flow": {
                "missionStoryConnections": [{
                    "key": "unplaced",
                    "producerScriptIds": ["8700020019"],
                    "anchorScriptIds": ["8700040001"],
                }],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["script:8700020019"]], ["unplaced"])
        self.assertEqual([row["key"] for row in index["anchor:8700040001"]], ["unplaced"])
        self.assertNotIn("script:8700040001", index)

    def test_scene_bindings_are_keyed_by_script_without_claiming_a_slot(self):
        """The chains name a level-script file but never an entity slot."""
        mission = {
            "extras": {
                "sceneBindings": {
                    "cutscene_e0m0_6": {"chains": [{
                        "levelId": "indie_dg004",
                        "file": "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg004/23900030000.json",
                        "steps": [
                            {"payloads": [{"sceneKey": "cutscene_e0m0_6", "kind": "cutscene"}]},
                            {"payloads": [{"sceneKey": "cutscene_e0m0_7", "kind": "cutscene"}]},
                        ],
                    }]},
                    "elsewhere": {"chains": [{
                        "levelId": "indie_dg002",
                        "file": "export_full/x.json",
                        "steps": [{"payloads": [{"sceneKey": "ignored", "kind": "cutscene"}]}],
                    }]},
                },
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._scene_binding_pins_by_level(mission, "e0m0", "CN")

        # Each chain is filed under the level it declares, so one mission's
        # chains can place dialog on several maps without ever crossing over.
        self.assertEqual(sorted(index), ["indie_dg002", "indie_dg004"])
        self.assertEqual(sorted(index["indie_dg004"]), ["condition:23900030000"])
        self.assertEqual(
            [row["key"] for row in index["indie_dg004"]["condition:23900030000"]],
            ["cutscene_e0m0_6", "cutscene_e0m0_7"],
        )
        self.assertEqual([row["key"] for row in index["indie_dg002"]["condition:x"]], ["ignored"])

    def test_trigger_slots_outside_the_registry_id_space_are_reported_not_placed(self):
        mission = {
            "flow": {
                "missionStoryConnections": [
                    {"key": "radio_in_volume", "triggerSlotIds": ["80009"]},
                    {"key": "on_a_real_entity", "triggerSlotIds": ["40007"]},
                ],
            },
        }
        registry = {"m_scriptEntityIdList": [{"scriptIdGlobal": 8700040013, "slotId": 40007}]}
        report = builder._unresolved_trigger_slots(mission, registry)

        self.assertEqual(report["count"], 1)
        self.assertEqual(report["stories"][0]["key"], "radio_in_volume")
        self.assertIn("not the recovered trigger position", report["boundary"])

    def test_proximity_rows_pinned_to_a_tracking_position_still_reach_their_quest(self):
        """Only mission-area pins become trigger markers, but every row names a quest.

        Rows pinned to a `trackingPos` used to be dropped entirely, which is
        why scenes like `radio_e0m0_8d4` and the level scripts behind them were
        absent from the payload.
        """
        timeline = {
            "levelscriptSpatialProximity": [{
                "sceneKey": "radio_e0m0_8d4",
                "questId": "e0m0_q#7",
                "scriptId": "8700040000",
                "file": "export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700040000.json",
                "pin": {"sourceType": "trackingPos", "position": {"x": 1, "y": 2, "z": 3}},
            }],
            "scenePlacement": {},
        }
        index = builder._quest_proximity_index(timeline)
        self.assertEqual([row["sceneKey"] for row in index["e0m0_q#7"]], ["radio_e0m0_8d4"])

        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"), \
                mock.patch.object(builder, "_script_file_for_id", return_value=None):
            point = builder._quest_point(
                {"questId": "e0m0_q#7", "centroid": {"x": 0, "y": 0, "z": 0}},
                "CN",
                {},
                {},
                index,
            )

        self.assertEqual(point["sceneKeys"], ["radio_e0m0_8d4"])
        paths = {pin["path"] for pin in point["relatedFiles"]}
        self.assertIn("webui/data/lang/CN/conv/radio_e0m0_8d4.json", paths)
        self.assertIn("export_full/structured/StreamingAssets/Data/Json/LevelScriptData/indie_dg002/8700040000.json", paths)

    def test_unplaced_stories_state_why_each_scene_is_absent(self):
        mission = {
            "flow": {
                "sceneGraph": {"nodes": [
                    {"key": "placed", "kind": "radio"},
                    {"key": "scoped", "kind": "radio"},
                    {"key": "elsewhere", "kind": "cutscene"},
                    {"key": "ordered", "kind": "cutscene"},
                    {"key": "nothing", "kind": "cutscene"},
                ]},
                "missionStoryConnections": [],
            },
            "timelineRecovery": {"scenePlacement": {"ordered": {"kind": "cutscene"}}},
            "extras": {"sceneBindings": {"elsewhere": {"chains": [{"levelId": "indie_dg004", "steps": []}]}}},
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            report = builder._unplaced_report(builder._unplaced_story_rows(
                builder._placement_marked_scene_universe(mission),
                builder._cross_level_scenes(mission, "indie_dg002"),
                "indie_dg002",
                "CN",
                {"webui/data/lang/CN/conv/placed.json"},
                {"webui/data/lang/CN/conv/scoped.json"},
            ))

        reasons = {row["key"]: row["reason"] for row in report["stories"]}
        self.assertNotIn("placed", reasons)
        self.assertEqual(reasons["scoped"], "mission_scope_only")
        self.assertEqual(reasons["elsewhere"], "cross_level_binding")
        self.assertEqual(reasons["ordered"], "graph_evidence_only")
        self.assertEqual(reasons["nothing"], "no_placement_evidence")
        self.assertEqual(report["count"], 4)
        self.assertIn("indie_dg004", next(row["detail"] for row in report["stories"] if row["key"] == "elsewhere"))

    def test_story_index_separates_exact_narrow_and_whole_mission_scopes(self):
        mission = {
            "flow": {
                "missionStoryConnections": [
                    {
                        "key": "exact_scene",
                        "producerEntityPositionStatus": "exact_unique_world_entity_registry_script_slot",
                        "producerEntities": [{"scriptIdGlobal": "8700040013", "slotId": "40007"}],
                        "producerScriptIds": ["8700040013"],
                        "anchorQuestIds": ["e0m0_q#2"],
                        "missionAreaIds": ["area_a"],
                        "sourceFiles": ["export_full/x.json"],
                    },
                    {"key": "broad_scene", "missionAreaIds": ["area_a", "area_b"]},
                ],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["slot:8700040013:40007"]], ["exact_scene"])
        # The slot gate is independent of the quest and mission-area scopes:
        # those describe when the scene plays, not which entity plays it.
        self.assertNotIn("script:8700040013", index)
        self.assertEqual([row["key"] for row in index["quest:e0m0_q#2"]], ["exact_scene"])
        # `area_a` is narrower than the mission's full area set, so it keeps its
        # per-area pin; the scene covering every area is filed mission-wide
        # instead of being repeated on each trigger.
        self.assertEqual([row["key"] for row in index["area:area_a"]], ["exact_scene"])
        self.assertNotIn("area:area_b", index)
        self.assertEqual([row["key"] for row in index["mission:areas"]], ["broad_scene"])


class LevelGeneralizationTests(unittest.TestCase):
    """Every level is recovered from the same sources, with no level named in code."""

    def test_registry_ids_bucket_onto_the_level_their_leading_digits_encode(self):
        registry = {
            "worldEntityBriefInfos": {"8700020001": {"detailId": "int_doodad_a", "position": {"x": 0, "y": 0, "z": 0}}},
            "m_scriptEntityIdList": [
                {"scriptIdGlobal": 8700040013, "slotId": 40007},
                {"scriptIdGlobal": 23900030000, "slotId": 30001},
                # idNum 4242 is declared by no level row, so it can be plotted
                # in no coordinate space and must be dropped rather than guessed.
                {"scriptIdGlobal": 424200000001, "slotId": 1},
            ],
            "m_scriptEntityBriefInfo": [
                {"entityType": 32, "detailId": "int_simple_travel_pole", "position": {"x": 1, "y": 2, "z": 3}},
                {"entityType": 32, "detailId": "int_narrative_empty", "position": {"x": 4, "y": 5, "z": 6}},
                {"entityType": 32, "detailId": "int_empty", "position": {"x": 7, "y": 8, "z": 9}},
            ],
            "npcProxyBriefInfos": {"8700010000": {"proxyId": "chen_indie_dg002", "position": {"x": 0, "y": 0, "z": 0}}},
        }
        buckets = builder._registry_by_level(registry, {"indie_dg002": 87, "indie_dg004": 239})

        self.assertEqual(len(buckets["indie_dg002"]["world"]), 1)
        self.assertEqual(len(buckets["indie_dg002"]["script"]), 1)
        self.assertEqual(len(buckets["indie_dg002"]["npc"]), 1)
        self.assertEqual(len(buckets["indie_dg004"]["script"]), 1)
        self.assertNotIn("", buckets)
        self.assertEqual(sorted(buckets), ["indie_dg002", "indie_dg004"])

    def test_entity_classification_prefers_detail_id_then_entity_type(self):
        kind, sub_kind, label, _ = builder._classify_entity("int_narrative_common_BTomb01", 32)
        self.assertEqual((kind, sub_kind, label), ("scenery", "tomb", "墓碑"))
        self.assertEqual(builder._classify_entity("int_narrative_empty", 32)[0], "narrative")
        # A second filter level separates chests from the other collectibles,
        # which is the distinction the layer tree exposes.
        self.assertEqual(builder._classify_entity("int_trchest_common_normal", 32)[:2], ("collectible", "chest"))
        self.assertEqual(builder._classify_entity("int_goldcoin_1", 32)[:2], ("collectible", "currency"))
        self.assertEqual(builder._classify_entity("eny_0029_lbmob", 16)[0], "enemy")
        # No detailId rule matches, so the registry's own entityType decides.
        self.assertEqual(builder._classify_entity("int_unknown_thing", 16)[0], "enemy")
        self.assertEqual(builder._classify_entity("", None)[:2], ("scenery", "unclassified"))

    def test_quest_centroid_spanning_two_levels_is_plotted_on_neither(self):
        self.assertTrue(builder._quest_belongs_to_level({"scenes": ["map01_lv001"]}, "map01_lv001"))
        self.assertFalse(builder._quest_belongs_to_level({"scenes": ["map01_lv001"]}, "map02_lv002"))
        # A centroid averaged over two coordinate spaces exists in neither.
        self.assertFalse(builder._quest_belongs_to_level({"scenes": ["map01_lv001", "map02_lv002"]}, "map01_lv001"))
        # A row that names no scene claims no other level.
        self.assertTrue(builder._quest_belongs_to_level({}, "map01_lv001"))

    def test_attachment_index_keeps_proxy_and_script_bindings_apart(self):
        mission = {
            "timelineRecovery": {
                "npcProxyDialogAttachments": [{"sceneKey": "dlg_a1m9_2", "questId": "a1m9_q#3", "npcProxyId": "weiermolin_map02_v1d2d0_a1m9Start"}],
                "scriptConditionAttachments": [{"sceneKey": "dlg_c13m2_5", "questId": "c13m2_q#5", "mapId": "map01_lv007", "scriptId": "2800080001"}],
            },
        }
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"), \
                mock.patch.object(builder, "_script_file_for_id", return_value=None):
            index = builder._attachment_story_index(mission, "CN")

        self.assertEqual([row["key"] for row in index["proxy:weiermolin_map02_v1d2d0_a1m9Start"]], ["dlg_a1m9_2"])
        self.assertEqual([row["key"] for row in index["condition:2800080001"]], ["dlg_c13m2_5"])

    def test_map_pins_only_plot_in_the_level_they_name(self):
        mission = {
            "flow": {
                "mapPins": [
                    {"scene": "base01_lv001", "sourceType": "npcProxy", "position": {"x": 1, "y": 2, "z": 3}, "questIds": ["a1m10_q#2"], "npcProxyId": "pelica_base01_lv001"},
                    {"scene": "map02_lv002", "sourceType": "trackingPos", "position": {"x": 9, "y": 9, "z": 9}, "questIds": []},
                    # Mission-area pins are plotted from the proximity rows,
                    # which also carry the level script behind the volume.
                    {"scene": "base01_lv001", "sourceType": "missionArea", "position": {"x": 4, "y": 4, "z": 4}},
                ],
            },
        }
        attachments = {"proxy:pelica_base01_lv001": [{"key": "dlg_a1m10_1", "convFile": "webui/data/lang/CN/conv/dlg_a1m10_1.json", "sourceFiles": []}]}
        with mock.patch.object(builder, "_mission_runtime_asset", return_value=None):
            rows = builder._map_pin_markers(mission, "CN", {}, attachments, "a1m10", "base01_lv001")

        self.assertEqual([row["kind"] for row in rows], ["npc"])
        self.assertEqual(rows[0]["sceneKeys"], ["dlg_a1m10_1"])
        self.assertTrue(rows[0]["registryBacked"])
        self.assertEqual(
            [pin["relation"] for pin in rows[0]["relatedFiles"]],
            ["story_npc_proxy"],
        )

    def test_reading_receivers_are_indexed_by_running_and_producing_script(self):
        index = builder._reading_receivers_by_level({
            "text_c13m2_1": [{"levelId": "map01_lv007", "scriptId": "2800080008", "sourceFile": "a.json"}],
            "text_e0m0_1": [{
                "scriptId": "8700020019",
                "sourceFile": "b.json",
                "interactiveEventProducers": [{"scriptIdGlobal": "8700020018", "entitySlotId": 40001}],
            }],
        })

        self.assertEqual([row["key"] for row in index["map01_lv007"]["2800080008"]], ["text_c13m2_1"])
        # The row declares no level, so it is offered to every level under "".
        # It reaches both the script that runs the action and the script that
        # serializes the producing entity, which are different identities.
        self.assertEqual(sorted(index[""]), ["8700020018", "8700020019"])

    def test_registry_backed_markers_drop_the_repeated_level_wide_registry_pin(self):
        entities = {
            "world": [("8700020001", {"entityType": 32, "detailId": "int_doodad_a", "position": {"x": 0, "y": 0, "z": 0}})],
            "script": [],
            "npc": [],
        }
        with mock.patch.object(builder, "_script_file_for_id", return_value=None):
            rows = builder._registry_markers(entities, "indie_dg002", "CN", {}, {}, {}, {})

        self.assertTrue(rows[0]["registryBacked"])
        # Repeating one identical 7 MB path on every node is what the flag
        # replaces; the map's own relatedFiles still publishes it once.
        self.assertEqual([pin["relation"] for pin in rows[0]["relatedFiles"]], [])


class FilterFacetTests(unittest.TestCase):
    """The page's mission and layer filters are driven by published facets."""

    def test_stories_remember_the_mission_that_authored_them(self):
        mission = {"flow": {"missionStoryConnections": [{"key": "scene", "producerScriptIds": ["1"]}]}}
        with mock.patch.object(builder, "_conv_file_for_key", side_effect=lambda language, key: f"webui/data/lang/{language}/conv/{key}.json"):
            index = builder._story_index(mission, "CN", "a1m9")
        self.assertEqual(index["script:1"][0]["mission"], "a1m9")
        # A level pools several missions, so the node has to be able to say
        # which of them put dialog on it.
        self.assertEqual(builder._story_missions(index["script:1"]), ["a1m9"])

    def test_story_missions_ignores_rows_with_no_owner(self):
        self.assertEqual(builder._story_missions([{"mission": ""}, {"key": "x"}]), [])
        self.assertEqual(
            builder._story_missions([{"mission": "b"}], [{"mission": "a"}, {"mission": "b"}]),
            ["a", "b"],
        )

    def test_facets_publish_a_two_level_layer_tree_and_mission_weights(self):
        markers = [
            {"kind": "collectible", "subKind": "chest", "label": "宝箱", "storyCount": 0, "sceneKeys": []},
            {"kind": "collectible", "subKind": "chest", "label": "宝箱", "storyCount": 0, "sceneKeys": []},
            {"kind": "collectible", "subKind": "currency", "label": "货币", "storyCount": 0, "sceneKeys": []},
            {"kind": "npc", "subKind": "npc_proxy", "label": "pelica", "storyCount": 1, "sceneKeys": ["dlg_1"], "missions": ["a1m10"]},
        ]
        quests = [{"questId": "a1m10_q#1", "missions": ["a1m10"]}]
        facets = builder._facets(markers, quests, ["a1m10"])

        self.assertEqual(facets["kinds"]["collectible"]["count"], 3)
        # Chests are separable from the other collectibles, which is the whole
        # point of the second level.
        self.assertEqual(facets["kinds"]["collectible"]["subKinds"]["chest"]["count"], 2)
        self.assertEqual(facets["kinds"]["collectible"]["subKinds"]["currency"]["label"], "货币")
        self.assertEqual(facets["kinds"]["npc"]["storyCount"], 1)
        self.assertEqual(facets["missions"]["a1m10"], {"markers": 1, "questPoints": 1, "stories": 1})

    def test_a_mission_with_no_plotted_node_still_appears_with_zero_weight(self):
        facets = builder._facets([], [], ["e0m0"])
        self.assertEqual(facets["missions"]["e0m0"], {"markers": 0, "questPoints": 0, "stories": 0})


class MapNamingAndMinimapTests(unittest.TestCase):
    """Level display names and the in-game map-screen background."""

    def _write_tile(self, root, name, rgba):
        tile_dir = root / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D"
        tile_dir.mkdir(parents=True, exist_ok=True)
        path = tile_dir / name
        row = bytes(rgba) * 4
        builder._png_write(path, 4, 4, [row] * 4)
        return path

    def _write_config(self, root, level_id, cells):
        config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
        config_dir.mkdir(parents=True, exist_ok=True)
        chunks = {
            f"m_{level_id}_{x}_{y}": {
                "chunkId": f"m_{level_id}_{x}_{y}",
                "lodType": 1,
                "x": x,
                "y": y,
                "worldCenter": {"x": x * 128 - 64, "y": y * 128 - 64},
                "worldLeftBottom": {"x": (x - 1) * 128.0, "y": (y - 1) * 128.0},
                "worldRightTop": {"x": x * 128.0, "y": y * 128.0},
            }
            for x, y in cells
        }
        (config_dir / f"{level_id}.json").write_text(json.dumps({"basic": {}, "mediumChunks": chunks}), encoding="utf-8")

    def test_level_families_use_the_recovered_region_names(self):
        self.assertEqual(builder._level_family("map01_lv001"), "四号谷地 / Valley-IV Map01")
        self.assertEqual(builder._level_family("map02_lv002"), "武陵 / Wuling Map02")
        self.assertEqual(builder._level_family("indie_dg002"), "独立场景 / Indie")

    def test_region_key_keeps_each_large_scene_coordinate_space_separate(self):
        self.assertEqual(builder._region_key("map01_lv001"), "map01")
        self.assertEqual(builder._region_key("map02_lv008"), "map02")
        self.assertEqual(builder._region_key("indie_dg002"), "indie_dg002")

    def test_region_bounds_union_only_uses_complete_preferred_backgrounds(self):
        payloads = [
            {"minimap": {"src": "render/a.png", "worldBounds": {"minX": -10, "maxX": 5, "minZ": 20, "maxZ": 30}}},
            {"minimap": {"src": None, "worldBounds": {"minX": -999, "maxX": 999, "minZ": -999, "maxZ": 999}},
             "renderBackground": {"src": "render/b.png", "worldBounds": {"minX": 5, "maxX": 20, "minZ": 10, "maxZ": 25}}},
            {"minimap": {"src": "render/incomplete.png", "worldBounds": {"minX": 0, "maxX": 1, "minZ": 0}}},
        ]
        self.assertEqual(builder._region_bounds(payloads), {"minX": -10.0, "maxX": 20.0, "minZ": 10.0, "maxZ": 30.0})
        self.assertIsNone(builder._region_bounds([payloads[-1]]))

    def test_level_names_resolve_the_level_table_rows_per_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tables = root / "export_full/structured/StreamingAssets/Table"
            tables.mkdir(parents=True)
            (tables / "LevelDescTable.json").write_text(json.dumps({
                "map01_lv001": {"id": "map01_lv001", "showName": {"id": 111, "text": ""}},
                "map02_lv002": {"id": "map02_lv002", "showName": {"id": 222, "text": ""}},
                "map02_lv000": {"id": "map02_lv000", "showName": {"id": 333, "text": ""}},
                "indie_dg002": {"id": "indie_dg002", "showName": {"id": 444, "text": ""}},
            }), encoding="utf-8")
            (tables / "I18nTextTable_CN.json").write_text(json.dumps({
                "111": "枢纽区",
                "222": "武陵城\t",
                "333": "?",
                "444": "？？？",
            }), encoding="utf-8")
            with mock.patch.object(builder, "ROOT", root):
                names = builder._level_names("CN")
        # Trailing tabs are stripped; empty and placeholder texts publish no
        # name so the reader falls back to the level id instead.
        self.assertEqual(names, {"map01_lv001": "枢纽区", "map02_lv002": "武陵城"})

    def test_minimap_background_composites_the_chunk_grid_top_z_up(self):
        red = (255, 0, 0, 255)
        green = (0, 255, 0, 255)
        blue = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_config(root, "test_lv001", [(1, 1), (1, 2)])
            # Cell (1,1) owns two near-duplicate exports; the lexicographically
            # first filename is the stable choice, so green wins over red.
            self._write_tile(root, "m_test_lv001_1_1_pAAAA.png", red)
            self._write_tile(root, "m_test_lv001_1_1_p0000.png", green)
            self._write_tile(root, "m_test_lv001_1_2_pBBBB.png", blue)
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv001")
                self.assertEqual(info["status"], "in_game_minimap")
                self.assertEqual(info["src"], "render/test_lv001_minimap.png")
                self.assertEqual(info["layer"], "m")
                self.assertEqual(info["tileCount"], 2)
                self.assertEqual(info["worldBounds"], {"minX": 0.0, "maxX": 128.0, "minZ": 0.0, "maxZ": 256.0})
                # y index 2 is the +Z side, so blue must sit on top and the
                # chosen (1,1) art, green, on the bottom.
                _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv001_minimap.png")
                self.assertEqual((_w, _h), (4, 8))
                self.assertEqual(bytes(rgba[0][:4]), bytes(blue))
                self.assertEqual(bytes(rgba[7][:4]), bytes(green))
                # The sidecar records the chosen files by hash so an unchanged
                # rebuild reuses the composite instead of repainting it.
                self.assertTrue((root / "webui/data/map_recovery/render/test_lv001_minimap.sources.json").exists())
                again = builder._minimap_background("test_lv001")
                self.assertEqual(again, info)

    def test_minimap_background_rotates_art_when_the_config_inverts_xz(self):
        green = (0, 255, 0, 255)
        blue = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            # The same two cells as the top-Z-up test, but this level's basic
            # block marks the art as authored inverted, so the game (and the
            # composite) must rotate the finished picture 180 degrees: the
            # lower cell's art ends up on top, mirrored in both axes.
            (config_dir / "test_lv004.json").write_text(json.dumps({
                "basic": {"needInverseXZ": True},
                "mediumChunks": {
                    "m_test_lv004_1_1": {
                        "x": 1, "y": 1,
                        "worldLeftBottom": {"x": 0.0, "y": 0.0},
                        "worldRightTop": {"x": 128.0, "y": 128.0},
                    },
                    "m_test_lv004_1_2": {
                        "x": 1, "y": 2,
                        "worldLeftBottom": {"x": 0.0, "y": 128.0},
                        "worldRightTop": {"x": 128.0, "y": 256.0},
                    },
                },
            }), encoding="utf-8")
            self._write_tile(root, "m_test_lv004_1_1_pDDDD.png", green)
            self._write_tile(root, "m_test_lv004_1_2_pEEEE.png", blue)
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv004")
            self.assertEqual(info["status"], "in_game_minimap")
            self.assertTrue(info["inverted"])
            # The world rectangle is unchanged; only the picture rotates.
            self.assertEqual(info["worldBounds"], {"minX": 0.0, "maxX": 128.0, "minZ": 0.0, "maxZ": 256.0})
            _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv004_minimap.png")
            self.assertEqual(bytes(rgba[0][:4]), bytes(green))
            self.assertEqual(bytes(rgba[7][:4]), bytes(blue))
            sidecar = json.loads((root / "webui/data/map_recovery/render/test_lv004_minimap.sources.json").read_text(encoding="utf-8"))
            self.assertTrue(sidecar["inverted"])

    def test_minimap_background_stretches_half_size_chunks_to_their_rect(self):
        green = (0, 255, 0, 255)
        blue = (0, 0, 255, 255)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "export_full/structured/StreamingAssets/Data/Json/UILevelMapLoadConfig"
            config_dir.mkdir(parents=True)
            # (1,1) covers 128x128 world units, (1,2) covers 256x128: the same
            # 4x4 texture must draw at a different pixel size for each.
            (config_dir / "test_lv003.json").write_text(json.dumps({"basic": {}, "mediumChunks": {
                "m_test_lv003_1_1": {
                    "x": 1, "y": 1,
                    "worldLeftBottom": {"x": 0.0, "y": 0.0},
                    "worldRightTop": {"x": 128.0, "y": 128.0},
                },
                "m_test_lv003_1_2": {
                    "x": 1, "y": 2,
                    "worldLeftBottom": {"x": 0.0, "y": 128.0},
                    "worldRightTop": {"x": 256.0, "y": 256.0},
                },
            }}), encoding="utf-8")
            self._write_tile(root, "m_test_lv003_1_1_pDDDD.png", green)
            self._write_tile(root, "m_test_lv003_1_2_pEEEE.png", blue)
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv003")
            self.assertEqual(info["status"], "in_game_minimap")
            self.assertEqual(info["worldBounds"], {"minX": 0.0, "maxX": 256.0, "minZ": 0.0, "maxZ": 256.0})
            _w, _h, rgba = builder._png_decode(root / "webui/data/map_recovery/render/test_lv003_minimap.png")
            # The canvas follows the world rectangle (256x256 units) at the
            # scale of the largest chunk, so the big chunk fills the +Z half
            # natively while the small chunk is drawn at reduced size in its
            # own 128x128 corner of the -Z half; the remaining corner stays
            # clear.
            self.assertEqual((_w, _h), (4, 8))
            self.assertEqual(bytes(rgba[0][:4]), bytes(blue))
            self.assertEqual(bytes(rgba[7][:4]), bytes(green))
            self.assertEqual(bytes(rgba[7][8:12]), bytes((0, 0, 0, 0)))

    def test_minimap_background_fails_closed_on_an_incomplete_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cells = [(1, 1), (1, 2), (2, 2)]  # a hole at (2,1)
            self._write_config(root, "test_lv002", cells)
            for x, y in cells:
                self._write_tile(root, f"m_test_lv002_{x}_{y}_pCCCC.png", (10, 20, 30, 255))
            with mock.patch.object(builder, "ROOT", root):
                info = builder._minimap_background("test_lv002")
            self.assertEqual(info["status"], "in_game_minimap_missing")
            self.assertIsNone(info["src"])
            self.assertFalse((root / "webui/data/map_recovery").exists())


if __name__ == "__main__":
    unittest.main()
