#!/usr/bin/env python3
"""Tests for actor-scoped operator-light source hashing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operator_lights_source import scoped_payload, scoped_sha256


class OperatorLightsSourceTests(unittest.TestCase):
    def test_installed_endminf_overview_fixture_has_exact_b31_membership(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "Assets"
            / "EndfieldGraphShaderLab"
            / "Generated"
            / "OriginalData"
            / "RenderParameters"
            / "operator_lights.json"
        )
        actor = json.loads(source.read_text(encoding="utf-8"))["actors"]["endminf"]
        lights = actor["lights"]
        self.assertEqual(len(lights), 12)
        self.assertTrue(all(row["enabled"] for row in lights))
        self.assertTrue(all(row["character_only"] for row in lights))
        self.assertTrue(all(not row["enable_obb_culling_box"] for row in lights))
        self.assertTrue(all(row["cookie_path_id"] == 0 for row in lights))
        self.assertTrue(all(not row["flicker_enabled"] for row in lights))
        self.assertTrue(
            all(row["culling_box_falloff_threshold"] == 0.8 for row in lights)
        )
        self.assertTrue(all(not row["use_far_distance_show"] for row in lights))
        self.assertTrue(
            all(not row["enable_override_shadow_light"] for row in lights)
        )
        self.assertEqual(
            [(row["index"], row["name"], row["shadow_type"], row["light_type"])
             for row in lights if row["shadow_type"] != 0],
            [(3, "RimLight_2", 2, 0), (11, "RimLight_2 (1)", 2, 0)],
        )

    def test_scope_is_deterministic_and_excludes_other_actors(self) -> None:
        payload = {
            "actors": {
                "wulfa": {"lights": [1, 2]},
                "liino": {"lights": [3]},
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operator_lights.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            first = scoped_sha256(path, ("wulfa",))
            payload["actors"]["liino"]["lights"].append(4)
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(first, scoped_sha256(path, ("wulfa",)))

    def test_missing_scoped_actor_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing scoped actors: wulfa"):
            scoped_payload({"actors": {}}, ("wulfa",))


if __name__ == "__main__":
    unittest.main()
