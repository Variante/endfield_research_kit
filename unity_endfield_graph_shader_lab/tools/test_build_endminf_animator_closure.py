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
    @staticmethod
    def _null_report():
        return {
            "schema": closure.SCHEMA,
            "status": "incomplete_missing_artifacts",
            "stage": {"stageFingerprint": "f", "stampFingerprint": "f"},
            "animators": [
                {
                    "animator": {"pathId": index + 1},
                    "controller": {
                        "status": "null_serialized_pointer",
                        "fileId": 0,
                        "pathId": 0,
                    },
                }
                for index in range(7)
            ],
            "missingArtifacts": [{"kind": "AnimationClip", "cab": "CAB-x", "pathId": 1}],
            "playbackProof": {"startToLoopProven": False, "endProven": False},
            "summary": {"animatorCount": 7},
        }

    @staticmethod
    def _stage_clip_fixture(root):
        path = root / "A_clip_p0000000000000001.json"
        path.write_text('{"m_Name":"clip"}\n', encoding="utf-8")
        return {
            1: {
                "path": path,
                "value": {"m_Name": "clip"},
                "filter": {
                    "Name": "clip",
                    "Source": r"D:\\exact\\owner.chk",
                    "PathID": 1,
                    "Type": "AnimationClip",
                    "Offset": 100,
                },
            }
        }

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

    def test_stage_artifact_rejects_wrong_source_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage_clips = self._stage_clip_fixture(Path(temporary))
            with self.assertRaisesRegex(closure.ClosureError, "source mismatch"):
                closure._stage_artifact(
                    stage_clips,
                    path_id=1,
                    name="clip",
                    source=r"D:\\wrong\\owner.chk",
                    offset=100,
                )

    def test_stage_artifact_rejects_wrong_offset_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            stage_clips = self._stage_clip_fixture(Path(temporary))
            with self.assertRaisesRegex(closure.ClosureError, "offset mismatch"):
                closure._stage_artifact(
                    stage_clips,
                    path_id=1,
                    name="clip",
                    source=r"D:\\exact\\owner.chk",
                    offset=101,
                )

    def test_playback_owner_cab_mismatch_fails_closed(self):
        row = {
            "artifact": "effect.json",
            "source": r"D:\\exact\\owner.chk",
            "sourceOffset": 100,
            "sourceCab": "CAB-other",
        }
        cab_rows = {
            "CAB-owner": [{
                "cab": "CAB-owner",
                "source": r"D:\\exact\\owner.chk",
                "sourceOffset": 100,
                "dependencies": [],
            }]
        }
        with self.assertRaisesRegex(closure.ClosureError, "owner CAB mismatch"):
            closure._bind_playback_owner(row, cab_rows)

    def test_report_validator_rejects_unverified_playback_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "owner.chk"
            source.write_bytes(b"cab")
            report = self._null_report()
            report["sourceSnapshots"] = {"cabSources": [closure._file_snapshot(source)]}
            report["playbackProof"]["effectAnimationRows"] = [{"ownerCabVerified": False}]
            with self.assertRaisesRegex(closure.ClosureError, "owner CAB"):
                closure._validate_report(report)

    def test_report_validator_rejects_stale_cab_source_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "owner.chk"
            source.write_bytes(b"old")
            report = self._null_report()
            report["sourceSnapshots"] = {"cabSources": [closure._file_snapshot(source)]}
            closure._validate_report(report)
            source.write_bytes(b"newer")
            with self.assertRaisesRegex(closure.ClosureError, "source provenance is stale"):
                closure._validate_report(report)

    def test_report_validator_rejects_start_to_loop_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "owner.chk"
            source.write_bytes(b"cab")
            report = self._null_report()
            report["sourceSnapshots"] = {"cabSources": [closure._file_snapshot(source)]}
            report["playbackProof"]["startToLoopProven"] = True
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
