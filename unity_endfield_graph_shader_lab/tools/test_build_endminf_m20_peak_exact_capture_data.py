#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import build_endminf_m20_peak_exact_capture_data as subject


class M20PeakCaptureDataTests(unittest.TestCase):
    def test_exact_live_packet_is_source_closed(self) -> None:
        packet = subject.collect(subject.CAPTURE)
        self.assertEqual(subject.VS_SHA256, subject.m21.sha256(packet["vs"]))
        self.assertEqual(subject.PS_SHA256, subject.m21.sha256(packet["ps"]))
        self.assertEqual(subject.VERTEX_SHA256,
                         subject.m21.sha256(packet["vertices"]))
        self.assertEqual(subject.INDEX_SHA256,
                         subject.m21.sha256(packet["indices"]))
        self.assertEqual(subject.ATLAS_SHA256,
                         subject.m21.sha256(packet["atlas"]))

    def test_generated_contract_retains_retail_atlas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cs = root / "payload.cs"
            cpp = root / "payload.h"
            subject.build(subject.CAPTURE, cs, cpp)
            self.assertIn("20260828T224210Z", cs.read_text(encoding="utf-8"))
            generated = cpp.read_text(encoding="utf-8")
            self.assertIn("g_EndfieldM20PeakAtlasBc7", generated)
            self.assertIn("g_EndfieldM20PeakPixelDxbc", generated)
            self.assertIn("g_EndfieldM20PeakIndexCount = 36u", generated)


if __name__ == "__main__":
    unittest.main()
