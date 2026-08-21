"""Hostile tests for the pinned Endminm comparable capture evidence."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

import build_endminm_comparable_capture as capture


class EndminmComparableCaptureTests(unittest.TestCase):
    def test_capture_evidence_rebuilds_with_exact_score_and_contract(self) -> None:
        report = capture.check_report()
        self.assertEqual(report["identity"]["characterId"], "chr_0002_endminm")
        self.assertEqual(report["capture"]["environment"]["timesSeconds"], [0.133])
        self.assertEqual(report["comparison"]["resolution"], [3840, 2160])
        self.assertTrue(report["comparison"]["sameCameraContract"])
        self.assertTrue(report["comparison"]["sameRenderSettingsContract"])
        self.assertAlmostEqual(report["comparison"]["eccTranslation"], 0.433439, places=6)

    def test_capture_evidence_hostile_mutations_fail_closed(self) -> None:
        base = json.loads(capture.REPORT_PATH.read_text(encoding="utf-8"))
        mutations = {
            "render_sha": lambda value: value["capture"]["output"].__setitem__("sha256", "0" * 64),
            "prefab_sha": lambda value: value["sourceAssets"]["prefab"].__setitem__("sha256", "0" * 64),
            "controller_sha": lambda value: value["sourceAssets"]["controllerAudit"].__setitem__("sha256", "0" * 64),
            "camera_contract": lambda value: value["comparison"].__setitem__("sameCameraContract", False),
            "render_settings": lambda value: value["comparison"].__setitem__("sameRenderSettingsContract", False),
            "sample_time": lambda value: value["comparison"].__setitem__("sampleTimeSeconds", 0.333),
            "score": lambda value: value["comparison"].__setitem__("eccTranslation", 0.99),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                candidate = copy.deepcopy(base)
                mutate(candidate)
                with NamedTemporaryFile("w", suffix=".json", dir=capture.PROJECT_ROOT / "tools", delete=False) as handle:
                    handle.write(json.dumps(candidate))
                    path = Path(handle.name)
                try:
                    with self.assertRaises(capture.CaptureEvidenceError):
                        capture.check_report(path)
                finally:
                    path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
