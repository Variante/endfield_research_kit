from __future__ import annotations

import unittest
from pathlib import Path

from scripts.story_builder.cutscene_semantics import (
    cutscene_semantic_shape,
    cutscene_subtitle_evidence,
    exact_levelscript_fmv_bindings,
    select_subtitle_text_group_from_display_names,
)


def exact_fmv_binding() -> dict:
    return {
        "fmvId": "cs_video_test",
        "sources": [{
            "kind": "levelscriptFmvAction",
            "sourceFile": "LevelScriptData/test.json",
            "actionName": "PlayFmvAction",
            "nativeMappingId": "mapping",
        }],
    }


class CutsceneSemanticsTests(unittest.TestCase):
    def test_language_bundle_attaches_semantics_only_to_cutscene_payload(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "story_builder"
            / "language_bundle.py"
        ).read_text(encoding="utf-8")
        assignment = (
            'payload["cutscene"]["semanticShape"] = cutscene_semantic_shape('
        )
        self.assertEqual(source.count(assignment), 1)
        cutscene_payload = source.index('"kind": "cutscene"')
        assignment_offset = source.index(assignment)
        write_offset = source.index(
            "write_conv_payload(cutscene_key, payload)", cutscene_payload
        )
        self.assertLess(cutscene_payload, assignment_offset)
        self.assertLess(assignment_offset, write_offset)

    def test_classifies_generated_cutscene_shapes(self) -> None:
        cases = [
            ({"variants": [{"part": "root"}]}, "unityTimeline"),
            (
                {
                    "variants": [{"part": "root"}],
                    "levelscriptFmvBindings": [exact_fmv_binding()],
                },
                "unityTimelineWithIndependentFmv",
            ),
            (
                {"variants": [{"part": "Actor"}]},
                "timelineComponentsWithoutRoot",
            ),
            (
                {"levelscriptFmvBindings": [exact_fmv_binding()]},
                "levelscriptFmv",
            ),
            ({"textOnlyUnconfirmed": True}, "textOnlyUnconfirmed"),
        ]
        for source, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(cutscene_semantic_shape(source), expected)

    def test_rejects_unclassified_and_conflicting_shapes(self) -> None:
        with self.assertRaisesRegex(ValueError, "no classifiable"):
            cutscene_semantic_shape({})
        with self.assertRaisesRegex(ValueError, "conflicts"):
            cutscene_semantic_shape({
                "variants": [{"part": "root"}],
                "textOnlyUnconfirmed": True,
            })

    def test_levelscript_fmv_binding_requires_exact_source(self) -> None:
        self.assertEqual(
            exact_levelscript_fmv_bindings({
                "levelscriptFmvBindings": [exact_fmv_binding()],
            }),
            [exact_fmv_binding()],
        )
        with self.assertRaisesRegex(
            ValueError,
            "lacks an exact levelscriptFmvAction source",
        ):
            cutscene_semantic_shape({
                "levelscriptFmvBindings": [{
                    "fmvId": "cs_video_test",
                    "sources": [],
                }],
            })

    def test_classifies_subtitle_evidence_separately_from_text(self) -> None:
        self.assertEqual(
            cutscene_subtitle_evidence({"hasSubtitleTrack": True}, [{}]),
            "authoredTrack",
        )
        self.assertEqual(
            cutscene_subtitle_evidence({}, [{"text": "line"}]),
            "localizedTextWithoutTrack",
        )
        self.assertEqual(cutscene_subtitle_evidence({}, []), "none")

    def test_selects_unique_text_group_from_ordered_track_display_names(self) -> None:
        groups = {
            "cutscene_e0m0_2": [
                {"text": "你来了"},
                {"text": "文明的恩惠，也是灾祸的根源"},
            ],
            "cutscene_e0m0_02": [
                {"text": "你来了"},
                {"text": "出发吧 管理员"},
            ],
        }
        tracks = [{"lines": [
            {"displayName": "你来了。"},
            {"displayName": "出发吧，“管理员”。"},
        ]}]
        self.assertEqual(
            select_subtitle_text_group_from_display_names(groups, tracks),
            "cutscene_e0m0_02",
        )

    def test_display_name_group_selection_fails_closed(self) -> None:
        ambiguous = {
            "first": [{"text": "相同"}],
            "second": [{"text": "相同。"}],
        }
        self.assertEqual(
            select_subtitle_text_group_from_display_names(
                ambiguous,
                [{"lines": [{"displayName": "相同"}]}],
            ),
            "",
        )

    def test_e0m0_2_tracks_select_padded_script(self) -> None:
        padded = [
            "你来了",
            "怎么这么久？",
            "抱歉 耽搁了一会儿",
            "“源石”……",
            "这独属于你的恩惠",
            "却被窃取 被污染",
            "你的命运并非只有一种选择",
            "这一次",
            "不要留下遗憾",
            "出发吧 管理员",
        ]
        alternate = [
            "你来了",
            "怎么这么久？",
            "抱歉，耽搁了一会儿",
            "那个是……",
            "“源石”",
            "文明的恩惠，也是灾祸的根源",
            "真庆幸还能和你一起前进",
            "这一次",
            "不要留下遗憾",
            "出发吧，“管理员”",
        ]
        tracks = [
            {"lines": [{"displayName": text} for text in padded]},
            {"lines": [{"displayName": text} for text in padded]},
        ]
        self.assertEqual(
            select_subtitle_text_group_from_display_names(
                {
                    "cutscene_e0m0_2": [
                        {"text": text} for text in alternate
                    ],
                    "cutscene_e0m0_02": [
                        {"text": text} for text in padded
                    ],
                },
                tracks,
            ),
            "cutscene_e0m0_02",
        )
        self.assertEqual(
            select_subtitle_text_group_from_display_names(
                {"only": [{"text": "文本"}]},
                [{"lines": [{"displayName": ""}]}],
            ),
            "",
        )
