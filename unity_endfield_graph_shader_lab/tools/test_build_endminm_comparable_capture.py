"""Hostile tests for the pinned Endminm comparable capture evidence."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

import build_endminm_comparable_capture as capture


class EndminmComparableCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The canonical rebuild recomputes ECC for all 151 3840x2160 rows.  The
        # validator caches that result within this process so every hostile
        # mutation below exercises the checker, not a second image scan.
        cls.report = capture.check_report()
        cls.base = json.loads(capture.REPORT_PATH.read_text(encoding="utf-8"))

    def _assert_mutation_rejected(self, label: str, mutate) -> None:
        candidate = copy.deepcopy(self.base)
        mutate(candidate)
        with self.subTest(label=label):
            with NamedTemporaryFile(
                "w", suffix=".json", dir=capture.PROJECT_ROOT / "tools", delete=False
            ) as handle:
                handle.write(json.dumps(candidate))
                path = Path(handle.name)
            try:
                with self.assertRaises(capture.CaptureEvidenceError):
                    capture.check_report(path)
            finally:
                path.unlink(missing_ok=True)

    def test_capture_evidence_rebuilds_with_exact_sweep_and_contract(self) -> None:
        report = self.report
        self.assertEqual(report["schema"], "endfield.character-recovery.common-camera-identity-sweep.v2")
        self.assertEqual(report["identity"]["competitor"]["characterId"], "chr_0002_endminm")
        self.assertEqual(report["controllerSourceResolution"]["auditReportedSourceContainerId"], "5767187")
        self.assertEqual(report["controllerSourceResolution"]["manifestClaimedSourceContainerId"], "1476960")
        self.assertEqual(report["controllerSourceResolution"]["currentExportContentContainerId"], "6197695")
        self.assertEqual(report["commonRenderContract"]["camera"]["sameTransformFor"], ["chr_0003_endminf", "chr_0002_endminm"])
        self.assertTrue(report["admission"]["sameCamera"])
        self.assertTrue(report["admission"]["sameRenderSettings"])
        self.assertTrue(report["admission"]["sweepComplete"])
        sweep = report["comparison"]["sweep"]
        self.assertEqual(sweep["sampleCount"], 151)
        self.assertEqual(sweep["rows"][0]["timeSeconds"], 0.0)
        self.assertEqual(sweep["rows"][-1]["timeSeconds"], 2.5)
        self.assertEqual([row["index"] for row in sweep["rows"]], list(range(151)))
        self.assertEqual(
            report["comparison"]["competitorScore"],
            max(row["eccTranslation"] for row in sweep["rows"]),
        )
        self.assertAlmostEqual(report["comparison"]["targetScore"], 0.820471, places=6)
        self.assertAlmostEqual(report["comparison"]["competitorScore"], 0.406829, places=6)
        self.assertAlmostEqual(report["comparison"]["targetMargin"], 0.413642, places=6)
        self.assertEqual(report["admission"]["status"], "proven")

    def test_capture_evidence_hostile_mutations_fail_closed(self) -> None:
        def row(report):
            return report["comparison"]["sweep"]["rows"][17]

        mutations = {
            "source_manifest_sha": lambda value: value["sourceAssets"]["manifest"].__setitem__("sha256", "0" * 64),
            "source_controller_sha": lambda value: value["sourceAssets"]["controllerAudit"]["currentOriginalDataController"].__setitem__("sha256", "0" * 64),
            "prefab_sha": lambda value: value["sourceAssets"]["prefab"].__setitem__("sha256", "0" * 64),
            "controller_resolution": lambda value: value["controllerSourceResolution"].__setitem__("currentExportContentContainerId", "1476960"),
            "camera_override": lambda value: value["commonRenderContract"]["camera"]["override"]["position"].__setitem__(0, 0.1),
            "scene_sha": lambda value: value["commonRenderContract"]["scene"].__setitem__("sha256", "0" * 64),
            "pipeline_sha": lambda value: value["commonRenderContract"]["pipeline"].__setitem__("sha256", "0" * 64),
            "target_sha": lambda value: value["comparison"]["targetRender"].__setitem__("sha256", "0" * 64),
            "row_sha": lambda value: row(value).__setitem__("sha256", "0" * 64),
            "row_time": lambda value: row(value).__setitem__("timeSeconds", 0.3),
            "row_ecc": lambda value: row(value).__setitem__("eccTranslation", 0.99),
            "row_removed": lambda value: value["comparison"]["sweep"]["rows"].pop(17),
            "competitor_max": lambda value: value["comparison"].__setitem__("competitorScore", 0.99),
            "admission_status": lambda value: value["admission"].__setitem__("status", "candidate"),
            "admission_gate": lambda value: value["admission"].__setitem__("matteCandidateAllowed", False),
        }
        for label, mutate in mutations.items():
            self._assert_mutation_rejected(label, mutate)


if __name__ == "__main__":
    unittest.main()
