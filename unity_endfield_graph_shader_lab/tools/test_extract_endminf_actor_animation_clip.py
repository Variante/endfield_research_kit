import json
import sys
import tempfile
import unittest
import zlib
from unittest import mock
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import extract_endminf_actor_animation_clip as extraction


class EndminfActorAnimationClipExtractionTests(unittest.TestCase):
    def _identity(self, source: str = "D:/game/source.chk"):
        return {
            "name": extraction.TARGET_NAME,
            "type": extraction.TARGET_TYPE,
            "pathId": -7994037904239017215,
            "pathIdHex": "910F78E15CD34301",
            "source": source,
            "sourceOffset": 937624865,
            "cab": "CAB-exact",
            "container": "assets/exact.fbx",
        }

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

    def test_object_index_requires_complete_zero_error_terminal_summary(self):
        identity = self._identity()
        summary = {
            "recordType": "summary",
            "schemaVersion": 1,
            "complete": True,
            "counts": {key: 0 for key in extraction.OBJECT_INDEX_REQUIRED_COUNTS},
            "errors": [],
            "source": identity["source"],
            "cab": identity["cab"],
            "pathId": identity["pathId"],
            "type": identity["type"],
            "name": identity["name"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "index.jsonl"
            path.write_text(json.dumps({"recordType": "object", "pathId": 1}) + "\n" + json.dumps(summary) + "\n", encoding="utf-8")
            self.assertEqual(extraction._object_index_summary(path, identity), summary)
            malformed = dict(summary)
            malformed["complete"] = False
            path.write_text(json.dumps(malformed) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, "not complete"):
                extraction._object_index_summary(path, identity)

    def test_object_index_rejects_case_or_error_drift(self):
        identity = self._identity()
        summary = {
            "recordType": "summary",
            "schemaVersion": 1,
            "complete": True,
            "counts": {key: 0 for key in extraction.OBJECT_INDEX_REQUIRED_COUNTS},
            "errors": [],
            "source": identity["source"],
            "cab": identity["cab"],
            "pathId": identity["pathId"],
            "type": identity["type"],
            "name": identity["name"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "index.jsonl"
            case_drift = dict(summary, source=identity["source"].upper())
            path.write_text(json.dumps(case_drift) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, "source differs"):
                extraction._object_index_summary(path, identity)
            error_drift = dict(summary, errors=[{"message": "bad"}])
            error_drift["counts"] = dict(summary["counts"], errors=1)
            path.write_text(json.dumps(error_drift) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, "count is nonzero"):
                extraction._object_index_summary(path, identity)

    def test_normalized_anim_requires_121_replacements_and_preserves_raw(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw.anim"
            normalized = root / "raw_unity_normalized.anim"
            raw.write_text("%YAML 1.1\n" + ("∞\n" * 121), encoding="utf-8")
            metrics = extraction._normalize_anim(raw, normalized)
            self.assertEqual(metrics["replacementCount"], 121)
            self.assertEqual(normalized.read_text(encoding="utf-8").count("∞"), 0)
            extraction._validate_normalized_anim(raw, normalized, metrics)
            raw.write_text(raw.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, r"raw \.anim hash changed"):
                extraction._validate_normalized_anim(raw, normalized, metrics)

    def test_binding_gap_report_keeps_all_three_hashes_unresolved(self):
        identity = self._identity()
        generic = []
        for path_hash in (4054261481, 1875086154, 2258644607):
            for attribute in (1, 2, 3):
                generic.append({"path": path_hash, "attribute": attribute, "typeID": "Transform"})
        clip = {"m_ClipBindingConstant": {"genericBindings": generic}}
        report = extraction._binding_gap_report(clip, identity)
        self.assertEqual(report["bindingCount"], 9)
        self.assertEqual(report["uniquePathHashCount"], 3)
        self.assertTrue(all(row["status"].startswith("unresolved_") for row in report["rows"]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "binding_gaps.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            extraction._validate_binding_gap_report(path, clip, identity)
            guessed = dict(report)
            guessed["rows"] = [dict(report["rows"][0], status="resolved", path="Root/Bone")]
            path.write_text(json.dumps(guessed), encoding="utf-8")
            with self.assertRaisesRegex(extraction.ExtractionError, "drifted"):
                extraction._validate_binding_gap_report(path, clip, identity)

    def test_avatar_tos_mapping_requires_exact_crc32_and_reports_absence(self):
        known_path = "Root/Bip001"
        known_hash = zlib.crc32(known_path.encode("utf-8")) & 0xFFFFFFFF
        missing_hash = 1875086154
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "EndminfAvatar.json"
            path.write_text(
                json.dumps(
                    {
                        "m_Name": "SK_actor_endminf_01Avatar",
                        "m_Avatar": {"m_AvatarSkeleton": {"m_Node": [{"name": "Root"}]}},
                        "m_TOS": {str(known_hash): known_path},
                    }
                ),
                encoding="utf-8",
            )
            report = extraction._avatar_tos_mapping_attempt(path, [known_hash, missing_hash])
        self.assertEqual(report["result"], "some_target_hashes_resolve_in_exact_avatar_tos")
        self.assertEqual(report["validKeyCount"], 1)
        self.assertEqual(report["invalidKeyCount"], 0)
        rows = {row["pathHash"]: row for row in report["targetRows"]}
        self.assertEqual(rows[known_hash]["path"], known_path)
        self.assertTrue(rows[known_hash]["algorithmMatches"])
        self.assertFalse(rows[missing_hash]["keyPresent"])

    def test_avatar_tos_negative_proof_keeps_all_target_rows_absent(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "EndminfAvatar.json"
            path.write_text(
                json.dumps(
                    {
                        "m_Name": "SK_actor_endminf_01Avatar",
                        "m_Avatar": {"m_AvatarSkeleton": {"m_Node": []}},
                        "m_TOS": {"123": "Root/Bip001"},
                    }
                ),
                encoding="utf-8",
            )
            report = extraction._avatar_tos_mapping_attempt(
                path, [1875086154, 2258644607, 4054261481]
            )
        self.assertEqual(report["result"], "all_target_hashes_absent_from_exact_avatar_tos")
        self.assertEqual(report["validKeyCount"], 0)
        self.assertEqual(report["invalidKeyCount"], 1)
        self.assertTrue(all(not row["keyPresent"] for row in report["targetRows"]))

    def test_actor_manifest_mapping_validates_stored_crc32_before_matching(self):
        known_path = "Root/Bip001"
        known_hash = zlib.crc32(known_path.encode("utf-8")) & 0xFFFFFFFF
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "endminf_ui_recovery_manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "transforms": [
                            {"path": known_path, "path_crc": known_hash},
                            {"path": "Root/Guessed", "path_crc": known_hash + 1},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = extraction._manifest_path_mapping_attempt(path, [known_hash, 1875086154])
        self.assertEqual(report["transformCount"], 2)
        self.assertEqual(report["validPathCrcCount"], 1)
        self.assertEqual(report["invalidPathCrcCount"], 1)
        rows = {row["pathHash"]: row for row in report["targetRows"]}
        self.assertEqual(rows[known_hash]["candidatePaths"], [known_path])
        self.assertEqual(rows[1875086154]["candidateCount"], 0)

    def test_reuse_path_calls_full_validator(self):
        source = Path(tempfile.gettempdir()) / "endminf-reuse-source.chk"
        target = self._identity(source.as_posix())
        row = {
            "Name": extraction.TARGET_NAME,
            "Type": extraction.TARGET_TYPE,
            "PathID": target["pathId"],
            "Offset": target["sourceOffset"],
            "Source": source.as_posix(),
            "Container": target["container"],
        }
        cab = {"cab": target["cab"]}
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "stage"
            output.mkdir()
            with mock.patch.object(extraction, "_target_from_closure", return_value={
                    "name": extraction.TARGET_NAME,
                    "type": extraction.TARGET_TYPE,
                    "pathId": target["pathId"],
                    "offset": target["sourceOffset"],
                    "source": source.as_posix().casefold(),
                    "sourceRaw": source.as_posix(),
                    "container": target["container"],
                    "cab": target["cab"],
                    "expectedSourceSnapshot": None,
                    "closure": "closure.json",
                }), mock.patch.object(extraction, "_asset_map_row", return_value=row), \
                    mock.patch.object(extraction, "_cab_row", return_value=cab), \
                    mock.patch.object(extraction, "_snapshot", return_value={
                        "path": source.as_posix(), "bytes": 1, "mtime_ns": 1,
                    }), mock.patch.object(extraction, "_validate_existing_stage", return_value={"status": "ok"}) as validator:
                result = extraction.extract(
                    closure_path=Path(temporary) / "closure.json",
                    asset_map_path=Path(temporary) / "asset-map.json",
                    cab_map_path=Path(temporary) / "cab-map.bin",
                    output=output,
                    force=False,
                    dry_run=False,
                    check=False,
                )
            self.assertEqual(result, {"status": "ok"})
            validator.assert_called_once()


if __name__ == "__main__":
    unittest.main()
