import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_endminf_animator_closure as closure


class EndminfAnimatorClosureTests(unittest.TestCase):
    def test_file_id_dependency_is_exact_and_fail_closed(self):
        owner = "CAB-owner"
        dependency = "CAB-controller"
        rows = {
            owner: [
                {
                    "cab": owner,
                    "source": r"D:\exact\owner.chk",
                    "sourceOffset": 100,
                    "dependencies": [dependency],
                }
            ],
            dependency: [
                {
                    "cab": dependency,
                    "source": r"D:\exact\owner.chk",
                    "sourceOffset": 200,
                    "dependencies": [],
                }
            ],
        }
        resolved = closure._resolve_dependency(rows, owner, 1, 123)
        self.assertEqual(resolved["cab"], dependency)
        self.assertEqual(resolved["dependencyIndex"], 1)
        local = closure._resolve_dependency(rows, owner, 0, 456)
        self.assertEqual(local["cab"], owner)
        with self.assertRaises(closure.ClosureError):
            closure._resolve_dependency(rows, owner, 2, 123)

    def test_asset_map_reads_exact_pathid_without_name_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "endfield_streamingassets_assets.json"
            path.write_text(
                '{\n  "AssetEntries": [\n'
                '    {\n      "Name": "wrong-name",\n'
                '      "Container": "wrong",\n      "Source": "D:\\\\wrong.chk",\n'
                '      "PathID": 22,\n      "Type": "AnimationClip",\n'
                '      "Hash": "bad",\n      "Offset": 1\n    },\n'
                '    {\n      "Name": "A_actor_endminf_ui_overview_02",\n'
                '      "Container": "exact",\n'
                '      "Source": "D:\\\\exact.chk",\n'
                '      "PathID": -7994037904239017215,\n'
                '      "Type": "AnimationClip",\n      "Hash": "good",\n'
                '      "Offset": 937624865\n    }\n  ]\n}\n',
                encoding="utf-8",
            )
            rows = closure._target_asset_map_rows([path], {-7994037904239017215})
            self.assertEqual(len(rows[-7994037904239017215]), 1)
            self.assertEqual(rows[-7994037904239017215][0]["Name"], "A_actor_endminf_ui_overview_02")
            self.assertEqual(rows[-7994037904239017215][0]["Offset"], 937624865)

    def test_report_validator_rejects_start_to_loop_claim(self):
        animators = []
        for index in range(7):
            animators.append(
                {
                    "animator": {"pathId": index + 1},
                    "controller": {
                        "status": "null_serialized_pointer",
                        "fileId": 0,
                        "pathId": 0,
                    },
                }
            )
        report = {
            "schema": closure.SCHEMA,
            "status": "incomplete_missing_artifacts",
            "stage": {"stageFingerprint": "f", "stampFingerprint": "f"},
            "animators": animators,
            "missingArtifacts": [{"kind": "AnimationClip", "cab": "CAB-x", "pathId": 1}],
            "playbackProof": {"startToLoopProven": True, "endProven": False},
            "summary": {"animatorCount": 7},
        }
        with self.assertRaises(closure.ClosureError):
            closure._validate_report(report)

    def test_stage_path_id_filename_is_signed_int64(self):
        self.assertEqual(
            closure._path_id_from_filename(Path("A_clip_pDB8EF20719226683.json")),
            -2625895420410042749,
        )
        self.assertIsNone(closure._path_id_from_filename(Path("clip.json")))


if __name__ == "__main__":
    unittest.main()
