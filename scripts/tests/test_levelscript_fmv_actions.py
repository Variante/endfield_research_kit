import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.story_builder import level_bindings
from scripts.story_builder.language_bundle import (
    filter_non_fmv_story_playback_index,
    filter_native_story_playback_index,
    native_fmv_scope_is_complete,
)
from scripts.story_builder.level_bindings import (
    build_levelscript_action_story_occurrences,
    classify_levelscript_record,
    levelscript_native_action_name,
)
from scripts.story_builder.levelscript_binary import (
    LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID,
    decode_levelscript_record_payload,
)


PARAM_TAIL = b"\xff\xff\xff\xff\x00\x00\x00\x00\xff\xff\xff\xff"


def tagged_string_param(text: str) -> bytes:
    raw = text.encode("utf-8")
    return b"\x04" + len(raw).to_bytes(4, "little") + raw + PARAM_TAIL


class LevelScriptFmvActionTests(unittest.TestCase):
    def test_play_fmv_decodes_movie_path_as_first_derived_field(self) -> None:
        fmv_id = "cs_video_testm1_1"
        payload = tagged_string_param(fmv_id) + bytes(64)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x035E,
            "kind": 0x0E,
            "unionTag": 0x035E,
            "serializedMemberCount": 0x0E,
            "strings": [{"offset": 0, "text": fmv_id}],
        }

        detail = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )["fmvAction"]
        self.assertEqual("PlayFmvAction", levelscript_native_action_name(record))
        self.assertEqual("play_fmv", classify_levelscript_record(record))
        self.assertEqual(fmv_id, detail["fmvId"])
        self.assertEqual("_moviePath", detail["sourceField"])
        self.assertEqual(LEVELSCRIPT_NATIVE_FMV_ACTION_MAPPING_ID, detail["nativeMappingId"])

    def test_start_fmv_teleport_uses_exact_final_fmv_field(self) -> None:
        teleport_id = "TpForLs_10001_deadbeef"
        fmv_id = "cs_video_testm1_2"
        first = tagged_string_param(teleport_id)
        gap = bytes(11)
        final_offset = len(first) + len(gap)
        payload = first + gap + tagged_string_param(fmv_id)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x04A1,
            "kind": 0x10,
            "unionTag": 0x04A1,
            "serializedMemberCount": 0x10,
            "strings": [
                {"offset": 0, "text": teleport_id},
                {"offset": final_offset, "text": fmv_id},
            ],
        }

        detail = decode_levelscript_record_payload(
            payload,
            record,
            next_start=len(payload),
            action_map_role="actionList#1 root",
        )["fmvAction"]
        self.assertEqual("StartFmvAndTeleportAction", detail["action"])
        self.assertEqual(fmv_id, detail["fmvId"])
        self.assertEqual("_fmvId", detail["sourceField"])

    def test_fmv_decoder_rejects_member_count_and_field_boundary_mismatches(self) -> None:
        fmv_id = "cs_video_testm1_3"
        payload = tagged_string_param(fmv_id)
        wrong_count = {
            "payloadStart": 0,
            "code": 0x035E,
            "kind": 0x0D,
            "unionTag": 0x035E,
            "serializedMemberCount": 0x0D,
            "strings": [{"offset": 0, "text": fmv_id}],
        }
        self.assertNotIn(
            "fmvAction",
            decode_levelscript_record_payload(payload, wrong_count, next_start=len(payload)),
        )

        not_final = {
            "payloadStart": 0,
            "code": 0x04A1,
            "kind": 0x10,
            "unionTag": 0x04A1,
            "serializedMemberCount": 0x10,
            "strings": [{"offset": 0, "text": fmv_id}],
        }
        self.assertNotIn(
            "fmvAction",
            decode_levelscript_record_payload(
                payload + b"\x00",
                not_final,
                next_start=len(payload) + 1,
            ),
        )

    def test_occurrence_builder_normalizes_only_exact_cs_video_identity(self) -> None:
        fmv_id = "cs_video_testm1_4"
        payload = tagged_string_param(fmv_id) + bytes(32)
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x035E,
            "kind": 0x0E,
            "unionTag": 0x035E,
            "serializedMemberCount": 0x0E,
            "localId": 1,
            "nextId": -1,
            "strings": [{"offset": 0, "text": fmv_id}],
            "plainStrings": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            level_dir = root / "LevelScriptData" / "map_test"
            level_dir.mkdir(parents=True)
            (root / "source.bin").write_bytes(payload)
            binding_data = {
                "files": [{
                    "file": "source.bin",
                    "fileStem": "10001",
                    "records": [record],
                    "stringHits": [],
                    "plainStringHits": [],
                }],
            }
            with (
                mock.patch.object(level_bindings, "ROOT", root),
                mock.patch.object(level_bindings, "LEVELSCRIPT_DIR", root / "LevelScriptData"),
                mock.patch.object(level_bindings, "_LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE", None),
                mock.patch.object(level_bindings, "_load_levelscript_binding_data", return_value=binding_data),
                mock.patch.object(
                    level_bindings,
                    "levelscript_action_map_membership",
                    return_value=({}, {0: "actionList#1 root"}),
                ),
                mock.patch.object(
                    level_bindings,
                    "_prepare_levelscript_native_control_context",
                    return_value={},
                ),
                mock.patch.object(
                    level_bindings,
                    "_levelscript_native_control_paths_to_record",
                    return_value=[],
                ),
            ):
                index = build_levelscript_action_story_occurrences()

        row = index["cutscene_testm1_4"][0]
        self.assertEqual("play_fmv", row["recordClass"])
        self.assertEqual(fmv_id, row["fmvAction"]["fmvId"])
        self.assertNotIn(fmv_id, index)

    def test_malformed_fmv_never_falls_back_to_incidental_story_literal(self) -> None:
        payload = b"not-a-tagged-parameter"
        record = {
            "start": 0,
            "payloadStart": 0,
            "code": 0x035E,
            "kind": 0x0E,
            "unionTag": 0x035E,
            "serializedMemberCount": 0x0E,
            "localId": 1,
            "nextId": -1,
            "strings": [{"offset": 0, "text": "cutscene_incidental_1"}],
            "plainStrings": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LevelScriptData" / "map_test").mkdir(parents=True)
            (root / "source.bin").write_bytes(payload)
            binding_data = {
                "files": [{
                    "file": "source.bin",
                    "fileStem": "10001",
                    "records": [record],
                    "stringHits": [],
                    "plainStringHits": [],
                }],
            }
            with (
                mock.patch.object(level_bindings, "ROOT", root),
                mock.patch.object(level_bindings, "LEVELSCRIPT_DIR", root / "LevelScriptData"),
                mock.patch.object(level_bindings, "_LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE", None),
                mock.patch.object(level_bindings, "_load_levelscript_binding_data", return_value=binding_data),
                mock.patch.object(
                    level_bindings,
                    "levelscript_action_map_membership",
                    return_value=({}, {0: "actionList#1 root"}),
                ),
            ):
                self.assertEqual({}, build_levelscript_action_story_occurrences())

    def test_emitted_page_filter_rejects_manual_override_ghosts(self) -> None:
        index = {
            "cutscene_exists": [{"fmvAction": {"fmvId": "cs_video_exists"}}],
            "cutscene_native_only": [{"fmvAction": {"fmvId": "cs_video_native_only"}}],
            "cutscene_false_match": [{"fmvAction": {"fmvId": "cs_video_false_match"}}],
        }
        self.assertEqual(
            {"cutscene_exists": index["cutscene_exists"]},
            filter_native_story_playback_index(
                index,
                {"cutscene_exists", "cutscene_false_match"},
                {("cutscene_false_match", "cs_video_false_match")},
            ),
        )

    def test_emitted_page_filter_normalizes_authored_dialog_aliases(self) -> None:
        occurrence = {
            "levelId": "dung_test",
            "scriptId": "10001",
            "sourceFile": "LevelScriptData/dung_test/10001.json",
            "recordOffset": 32,
            "actionName": "StartDialogAndTeleportAction",
        }

        def resolve(story_key: str, emitted: set[str]) -> str:
            alias = f"misc_{story_key}"
            return alias if alias in emitted else ""

        self.assertEqual(
            {
                "misc_dlg_testm1_1d5": [{
                    **occurrence,
                    "authoredStoryKey": "dlg_testm1_1d5",
                }],
            },
            filter_native_story_playback_index(
                {"dlg_testm1_1d5": [occurrence]},
                {"misc_dlg_testm1_1d5"},
                story_key_resolver=resolve,
            ),
        )

    def test_fmv_mission_scope_requires_every_occurrence_to_agree(self) -> None:
        hosted = {"mission": [{"recordClass": "play_fmv"}]}
        self.assertTrue(native_fmv_scope_is_complete(
            [{"recordClass": "play_fmv"}],
            hosted,
            [],
        ))
        self.assertFalse(native_fmv_scope_is_complete(
            [{"recordClass": "play_fmv"}, {"recordClass": "play_fmv"}],
            hosted,
            [],
        ))
        self.assertFalse(native_fmv_scope_is_complete(
            [{"recordClass": "play_fmv"}],
            {
                "mission": [{"recordClass": "play_fmv"}],
                "other": [{"recordClass": "play_fmv"}],
            },
            [],
        ))
        self.assertFalse(native_fmv_scope_is_complete(
            [{"recordClass": "play_fmv"}],
            hosted,
            [{"status": "shared"}],
        ))

    def test_generic_native_context_index_excludes_every_fmv_row(self) -> None:
        dialog = {"recordClass": "play_dialog", "id": 1}
        fmv = {"recordClass": "play_fmv", "id": 2}
        self.assertEqual(
            {"mixed": [dialog]},
            filter_non_fmv_story_playback_index({
                "mixed": [dialog, fmv],
                "fmv_only": [fmv],
            }),
        )


if __name__ == "__main__":
    unittest.main()
