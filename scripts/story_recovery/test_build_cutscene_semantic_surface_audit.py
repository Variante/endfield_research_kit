from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_cutscene_semantic_surface_audit as audit  # noqa: E402


def payload(*, variants=None, bindings=None, text_only=False):
    return {
        "key": "cutscene_test",
        "kind": "cutscene",
        "mission": "test",
        "lines": [],
        "cutscene": {
            "variants": variants or [],
            "levelscriptFmvBindings": bindings or [],
            "textOnlyUnconfirmed": text_only,
        },
    }


def exact_fmv_binding():
    return {
        "fmvId": "cs_video_test",
        "sources": [{
            "kind": "levelscriptFmvAction",
            "sourceFile": "LevelScriptData/test.json",
            "actionName": "PlayFmvAction",
            "nativeMappingId": "mapping",
        }],
    }


class CutsceneSemanticSurfaceAuditTests(unittest.TestCase):
    def test_classifies_all_evidence_shapes(self) -> None:
        cases = [
            (
                payload(variants=[{"part": "root"}, {"part": "Actor"}]),
                "unity_timeline_root",
            ),
            (
                payload(
                    variants=[{"part": "root"}],
                    bindings=[exact_fmv_binding()],
                ),
                "unity_timeline_plus_levelscript_fmv",
            ),
            (
                payload(variants=[{"part": "Actor"}, {"part": "Audio"}]),
                "unity_timeline_components_without_root",
            ),
            (
                payload(bindings=[exact_fmv_binding()]),
                "levelscript_fmv_only",
            ),
            (
                payload(text_only=True),
                "text_table_only_unconfirmed",
            ),
        ]
        for source, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    audit.classify_cutscene("cutscene_test", source)[
                        "classification"
                    ],
                    expected,
                )

    def test_rejects_untyped_or_conflicting_rows(self) -> None:
        with self.assertRaisesRegex(
            audit.AuditError, "no Unity Timeline"
        ):
            audit.classify_cutscene("cutscene_test", payload())
        with self.assertRaisesRegex(
            audit.AuditError, "conflicts with authored asset evidence"
        ):
            audit.classify_cutscene(
                "cutscene_test",
                payload(variants=[{"part": "root"}], text_only=True),
            )
        with self.assertRaisesRegex(
            audit.AuditError, "lacks an exact levelscriptFmvAction source"
        ):
            audit.classify_cutscene(
                "cutscene_test",
                payload(bindings=[{"fmvId": "cs_video_test", "sources": []}]),
            )


if __name__ == "__main__":
    unittest.main()
