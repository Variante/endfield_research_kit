#!/usr/bin/env python3
"""Focused tests for the current Eye/brow ForwardLit contract."""

from __future__ import annotations

import collections
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_eye_brow_forward_recovery as recovery


class EyeBrowForwardRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = recovery.load_json(recovery.CONTRACT_PATH)

    def test_current_roster_scope(self) -> None:
        scope = self.contract["scope"]
        self.assertEqual(scope["playable_actor_count"], 31)
        self.assertEqual(scope["eye_family_actor_count"], 29)
        self.assertEqual(scope["source_proven_zero_actors"], ["antal", "dapan"])
        self.assertEqual(len(self.contract["materials"]), 59)

    def test_exact_variant_and_raster_census(self) -> None:
        materials = self.contract["materials"].values()
        self.assertEqual(
            collections.Counter(row["variant_class"] for row in materials),
            collections.Counter({1: 30, 2: 21, 3: 8}),
        )
        self.assertEqual(
            collections.Counter(row["custom_render_queue"] for row in materials),
            collections.Counter({2000: 47, 2015: 11, 2050: 1}),
        )
        self.assertEqual(
            collections.Counter(row["depth_only_enabled"] for row in materials),
            collections.Counter({False: 49, True: 10}),
        )

    def test_pinned_current_d3d11_fragments(self) -> None:
        recovery.verify_variants(self.contract)

    def test_material_and_source_gated_implementation(self) -> None:
        recovery.verify_materials(self.contract)
        recovery.verify_implementation()


if __name__ == "__main__":
    unittest.main()
