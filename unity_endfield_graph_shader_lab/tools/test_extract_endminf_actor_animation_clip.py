import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import extract_endminf_actor_animation_clip as extraction


class EndminfActorAnimationClipExtractionTests(unittest.TestCase):
    def test_clip_metrics_records_timing_and_bindings(self):
        value = {
            "m_Name": extraction.TARGET_NAME,
            "m_SampleRate": 60.0,
            "m_MuscleClip": {"m_StopTime": 5.8833337, "m_LoopTime": False},
            "m_ClipBindingConstant": {
                "genericBindings": [{"path": 1}, {"path": 2}],
                "pptrCurveMapping": [],
            },
            **{key: [] for key in (
                "m_RotationCurves",
                "m_CompressedRotationCurves",
                "m_EulerCurves",
                "m_PositionCurves",
                "m_ScaleCurves",
                "m_FloatCurves",
                "m_PPtrCurves",
            )},
            "m_AclCompressedBuffer": {"FloatCurveCount": 0},
        }
        metrics = extraction._clip_metrics(value)
        self.assertEqual(metrics["lengthSeconds"], 5.8833337)
        self.assertEqual(metrics["sampleRate"], 60.0)
        self.assertEqual(metrics["bindingCounts"]["totalBindingEntries"], 2)

    def test_clip_metrics_rejects_nonpositive_length(self):
        value = {
            "m_Name": extraction.TARGET_NAME,
            "m_SampleRate": 60.0,
            "m_MuscleClip": {"m_StopTime": 0.0},
            "m_ClipBindingConstant": {"genericBindings": [], "pptrCurveMapping": []},
            **{key: [] for key in (
                "m_RotationCurves",
                "m_CompressedRotationCurves",
                "m_EulerCurves",
                "m_PositionCurves",
                "m_ScaleCurves",
                "m_FloatCurves",
                "m_PPtrCurves",
            )},
        }
        with self.assertRaisesRegex(extraction.ExtractionError, "positive finite"):
            extraction._clip_metrics(value)

    def test_converted_clip_metrics_matches_serialized_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clip.anim"
            path.write_text(
                "%YAML 1.1\n"
                "AnimationClip:\n"
                "  m_Name: A_actor_endminf_ui_overview_02\n"
                "  m_SampleRate: 60\n"
                "  m_ClipBindingConstant:\n"
                "    genericBindings:\n"
                "    - path: 1\n"
                "      attribute: 1\n"
                "    - path: 2\n"
                "      attribute: 2\n"
                "    pptrCurveMapping: []\n"
                "  m_AnimationClipSettings:\n"
                "    m_StopTime: 5.8833337\n"
                "    m_LoopTime: 0\n",
                encoding="utf-8",
            )
            converted = extraction._converted_clip_metrics(path)
            serialized = {
                "name": extraction.TARGET_NAME,
                "sampleRate": 60.0,
                "lengthSeconds": 5.8833337,
                "loopTime": False,
                "bindingCounts": {
                    "genericBindings": 2,
                    "pptrCurveMapping": 0,
                    "totalBindingEntries": 2,
                },
            }
            extraction._assert_converted_matches_json(converted, serialized)

    def test_closure_selection_rejects_conflicting_exact_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "closure.json"
            base = {
                "Name": extraction.TARGET_NAME,
                "Container": "assets/effects/sk_fx_endminf_01_ui.fbx",
                "Source": r"D:\game\FC.chk",
                "PathID": -1,
                "Type": extraction.TARGET_TYPE,
                "Offset": 10,
            }
            path.write_text(json.dumps({
                "missingArtifacts": [{
                    "kind": extraction.TARGET_TYPE,
                    "name": extraction.TARGET_NAME,
                    "cab": "CAB-exact",
                    "pathId": -1,
                    "mismatchedCandidates": [],
                }],
                "target": [base, {**base, "Offset": 11}],
            }), encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, "conflicting AssetMap identities"):
                extraction._target_from_closure(path)

    def test_filter_validator_requires_one_exact_row(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "filter.json"
            target = {
                "name": extraction.TARGET_NAME,
                "type": extraction.TARGET_TYPE,
                "pathId": -1,
                "offset": 10,
                "source": "d:/game/fc.chk",
            }
            row = {
                "Name": extraction.TARGET_NAME,
                "Type": extraction.TARGET_TYPE,
                "PathID": -1,
                "Offset": 10,
                "Source": r"D:\game\FC.chk",
            }
            path.write_text(json.dumps([row]), encoding="utf-8")
            extraction._validate_filter_file(path, target, row)
            path.write_text(json.dumps([row, row]), encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, "one exact AssetMap row"):
                extraction._validate_filter_file(path, target, row)


if __name__ == "__main__":
    unittest.main()
