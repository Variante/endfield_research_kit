from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
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

    def test_gender_definition_base_is_not_a_definition_only_gap(
        self,
    ) -> None:
        bindings = {"cs_video_e2m8_2": {}}
        fmv_id = "f_cs_video_e2m8_2"
        base = video_bindings.fmv_id_to_base(fmv_id)
        resolved = (
            fmv_id
            if fmv_id in bindings
            else base if base in bindings else ""
        )
        self.assertEqual(resolved, "cs_video_e2m8_2")

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

    def test_definition_is_not_an_authoritative_binding(self) -> None:
        definition = {
            "fmvId": "cs_video_e1m3_3",
            "numericIds": [18],
            "placementEvidence": False,
        }
        with (
            patch.object(
                anime_assets,
                "_VIDEO_BINDINGS_CACHE",
                {},
            ),
            patch.object(
                anime_assets,
                "_VIDEO_DEFINITIONS_CACHE",
                {"cs_video_e1m3_3": definition},
            ),
        ):
            self.assertIsNone(
                anime_assets._video_binding_for_stem(
                    "cs_video_e1m3_3"
                )
            )
            self.assertIs(
                anime_assets._video_definition_for_stem(
                    "cs_video_e1m3_3"
                ),
                definition,
            )

    def test_collects_definition_timeline_without_placement(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mono = root / "StreamingAssets" / "json_by_type" / "MonoBehaviour"
            persistent = root / "Persistent" / "json_by_type" / "MonoBehaviour"
            mono.mkdir(parents=True)
            persistent.mkdir(parents=True)

            def write_object(
                path_id: int,
                name: str,
                payload: dict,
            ) -> None:
                suffix = f"{path_id & ((1 << 64) - 1):016X}"
                (mono / f"{name}_p{suffix}.json").write_text(
                    json.dumps({
                        "$animestudio": {
                            "pathId": path_id,
                            "sourceFile": "CAB-fixture",
                        },
                        "m_Name": name,
                        **payload,
                    }),
                    encoding="utf-8",
                )

            write_object(
                100,
                "fixture_playable",
                {"m_Tracks": [{"m_PathID": 200}]},
            )
            write_object(
                200,
                "Subtitle Track",
                {
                    "m_Clips": [{
                        "m_Start": 1.5,
                        "m_Duration": 2.0,
                        "m_Asset": {"m_PathID": 300},
                    }]
                },
            )
            write_object(
                300,
                "SubtitlePlayableAsset",
                {"_textId": "fmv_fixture_01"},
            )
            definition = {
                "sources": [{
                    "asset": (
                        "export_full/recovered/AnimeStudio-cli/"
                        "StreamingAssets/json_by_type/MonoBehaviour/"
                        "fmv_fixture.json"
                    ),
                    "defaultPlayablePathId": 100,
                    "defaultPlayableSourceFile": "CAB-fixture",
                }]
            }
            with patch.object(
                video_bindings,
                "MONOBEHAVIOUR_DIRS",
                (mono, persistent),
            ):
                evidence = (
                    video_bindings.collect_definition_timeline_evidence(
                        definition
                    )
                )
            self.assertEqual(evidence["trackCount"], 1)
            self.assertEqual(evidence["clipCount"], 1)
            self.assertEqual(evidence["subtitleClipCount"], 1)
            self.assertEqual(
                evidence["subtitleTextIds"],
                ["fmv_fixture_01"],
            )
            self.assertFalse(evidence["placementEvidence"])


if __name__ == "__main__":
    unittest.main()
