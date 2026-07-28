from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.story_builder import anime_assets
from scripts.story_builder import video_bindings


class VideoBindingsLevelScriptTests(unittest.TestCase):
    def test_gender_video_stem_uses_exact_base_binding(self) -> None:
        binding = {"fmvId": "cs_video_e2m8_2"}
        with patch.object(
            anime_assets,
            "_VIDEO_BINDINGS_CACHE",
            {"cs_video_e2m8_2": binding},
        ):
            self.assertIs(
                anime_assets._video_binding_for_stem(
                    "f_cs_video_e2m8_2"
                ),
                binding,
            )

    def test_nested_cutscene_dialog_scene_maps_to_mission(self) -> None:
        self.assertEqual(
            video_bindings.scene_to_mission(
                "cutscene_dlg_e9m2_3"
            ),
            "e9m2",
        )

    def test_collects_exact_native_fmv_target(self) -> None:
        occurrences = {
            "cutscene_dlg_e9m2_3": [{
                "levelId": "dung02_dg002",
                "scriptId": "24900160015",
                "sourceFile": "source.json",
                "actionMapRole": "actionList#0",
                "recordOffset": 4096,
                "localId": 25,
                "actionName": "PlayFmvAction",
                "recordClass": "play_fmv",
                "nativeMappingId": "levelscript-action-map-v1",
                "fmvAction": {
                    "action": "PlayFmvAction",
                    "fmvId": "cs_video_dlg_e9m2_3",
                    "sourceField": "_moviePath",
                    "fieldOffset": "0x1020",
                    "payloadShape":
                        "play-fmv-movie-path-first-derived-field",
                    "nativeMappingId": "levelscript-fmv-action-v1",
                },
            }],
        }

        rows = video_bindings.collect_levelscript_fmv_actions(
            occurrences
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fmvId"], "cs_video_dlg_e9m2_3")
        self.assertEqual(
            rows[0]["storyKey"],
            "cutscene_dlg_e9m2_3",
        )
        self.assertEqual(
            rows[0]["fmvAction"]["sourceField"],
            "_moviePath",
        )

    def test_rejects_mismatched_or_untyped_rows(self) -> None:
        exact_action = {
            "sourceFile": "source.json",
            "recordOffset": 4096,
            "recordClass": "play_fmv",
            "fmvAction": {
                "fmvId": "cs_video_dlg_e9m2_3",
                "sourceField": "_moviePath",
                "nativeMappingId": "levelscript-fmv-action-v1",
            },
        }
        occurrences = {
            "cutscene_wrong": [exact_action],
            "cutscene_dlg_e9m2_3": [{
                **exact_action,
                "recordClass": "preload_cutscene",
            }],
        }

        self.assertEqual(
            video_bindings.collect_levelscript_fmv_actions(
                occurrences
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
