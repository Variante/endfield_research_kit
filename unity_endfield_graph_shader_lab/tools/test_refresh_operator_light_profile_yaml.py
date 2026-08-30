#!/usr/bin/env python3
from __future__ import annotations

import unittest

from refresh_operator_light_profile_yaml import refresh_text


class RefreshOperatorLightProfileYamlTests(unittest.TestCase):
    def test_refreshes_source_fields_and_is_idempotent(self) -> None:
        profile = """  characterLighting:
    useRecoveredSourceMainLightDescriptor: 1
    sourceDirectIntensityDividePi: 2.7
  operatorLights:
  - sourceName: Test
    falloffDistance: 100
    followerSourceRawDataSha256: raw
  characterLightingProvenance: source
"""
        operators = {
            "actors": {
                "endminf": {
                    "count": 1,
                    "lights": [{
                        "name": "Test",
                        "culling_box_falloff_threshold": 0.8,
                        "use_far_distance_show": False,
                        "enable_override_shadow_light": False,
                        "runtime_semantic_sha256": "a" * 64,
                    }],
                }
            }
        }
        render = {
            "environment": {
                "serialized": {
                    "direct_color_mode": 1,
                    "direct_custom_color": {"r": 1, "g": 0.5, "b": 0.25, "a": 1},
                }
            }
        }
        refreshed = refresh_text(profile, "endminf", operators, render)
        self.assertIn("sourceDirectColor: {r: 1, g: 0.5, b: 0.25, a: 1}", refreshed)
        self.assertIn("cullingBoxFalloffThreshold: 0.8", refreshed)
        self.assertIn("useFarDistanceShow: 0", refreshed)
        self.assertIn("enableOverrideShadowLight: 0", refreshed)
        self.assertIn("sourceSemanticSha256: " + "a" * 64, refreshed)
        self.assertEqual(
            refreshed,
            refresh_text(refreshed, "endminf", operators, render),
        )


if __name__ == "__main__":
    unittest.main()
