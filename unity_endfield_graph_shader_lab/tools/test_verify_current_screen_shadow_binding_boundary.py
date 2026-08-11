from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify_current_screen_shadow_binding_boundary as boundary


class CurrentScreenShadowBindingBoundaryTests(unittest.TestCase):
    def test_current_boundary_is_explicitly_fail_closed(self) -> None:
        result = boundary.verify_current_boundary()
        self.assertTrue(result["ok"])
        self.assertFalse(result["producer"]["content_valid"])
        self.assertFalse(result["producer"]["skin_keyword_gate"])
        self.assertFalse(result["skin_consumer"]["retail_global_keyword"])
        self.assertEqual(
            result["interpretation"]["retail_frame_parity"],
            "not asserted",
        )

    def test_missing_anchor_reports_label_and_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            producer = Path(temporary) / "producer.cs"
            producer.write_text("// incomplete producer\n", encoding="utf-8")
            with mock.patch.object(boundary, "PRODUCER", producer):
                with self.assertRaisesRegex(
                    AssertionError,
                    r"current screen-shadow producer.*_ScreenSpaceShadowMask",
                ):
                    boundary.verify_current_boundary()


if __name__ == "__main__":
    unittest.main()
