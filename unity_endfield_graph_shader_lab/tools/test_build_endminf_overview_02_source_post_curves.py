#!/usr/bin/env python3
"""Focused tests for the exact Endminf overview-02 source post curves."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_overview_02_source_post_curves",
    HERE / "build_endminf_overview_02_source_post_curves.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

EXPECTED_PAYLOAD_SHA256 = (
    "0919ae4aab01e7772fb0c3987ad16f2885ad6374ff6c88a4adc065e4ba19353c"
)


class EndminfOverview02SourcePostCurveTests(unittest.TestCase):
    def test_published_payload_matches_hash_gated_source_build(self) -> None:
        payload = MODULE.build()
        self.assertEqual(payload, json.loads(MODULE.OUTPUT.read_text(encoding="utf-8")))
        self.assertEqual(
            hashlib.sha256(MODULE.encode(payload)).hexdigest(),
            EXPECTED_PAYLOAD_SHA256,
        )
        self.assertEqual(
            [row["role"] for row in payload["curves"]],
            ["chromaticIntensity", "radialIntensity", "radialPower"],
        )
        self.assertEqual([len(row["keys"]) for row in payload["curves"]], [5, 5, 1])
        self.assertEqual(
            payload["curves"][0]["keys"][0],
            {
                "time": 0.0,
                "a": 54.86399841308594,
                "b": -13.7160005569458,
                "c": 0.0,
                "d": 0.12700000405311584,
            },
        )
        self.assertEqual(
            payload["curves"][1]["keys"][2],
            {
                "time": 4.400000095367432,
                "a": -5886.0166015625,
                "b": 294.300537109375,
                "c": 0.0,
                "d": 0.0,
            },
        )
        self.assertEqual(payload["curves"][2]["keys"][0]["d"], 1.0)

    def test_source_file_mutation_fails_closed_at_hash_gate(self) -> None:
        source = json.loads(MODULE.SOURCE_CLIP.read_text(encoding="utf-8"))
        source["m_Name"] = "mutated"
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "clip.json"
            changed.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(MODULE, "SOURCE_CLIP", changed):
                with self.assertRaisesRegex(ValueError, "clip hash drifted"):
                    MODULE.build()

    def test_published_check_canonicalizes_windows_line_endings(self) -> None:
        payload = MODULE.encode(MODULE.build())
        crlf_payload = payload.replace(b"\n", b"\r\n")
        self.assertEqual(MODULE.canonicalize_newlines(crlf_payload), payload)

    def test_binding_mutation_fails_closed_after_identity_gate(self) -> None:
        source = json.loads(MODULE.SOURCE_CLIP.read_text(encoding="utf-8"))
        bindings = source["m_ClipBindingConstant"]["genericBindings"]
        bindings[0] = copy.deepcopy(bindings[0])
        bindings[0]["attribute"] = MODULE.EXPECTED_POWER_ATTRIBUTE
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "clip.json"
            changed.write_text(json.dumps(source), encoding="utf-8")
            with mock.patch.object(MODULE, "SOURCE_CLIP", changed), mock.patch.object(
                MODULE,
                "sha256",
                return_value=MODULE.EXPECTED_CLIP_SHA256,
            ):
                with self.assertRaisesRegex(ValueError, "binding 0 script/member"):
                    MODULE.build()

    def test_native_audit_mutation_fails_closed(self) -> None:
        audit = json.loads(MODULE.NATIVE_AUDIT.read_text(encoding="utf-8"))
        apply_method = next(
            row
            for row in audit["scriptTypes"][0]["methods"]
            if row["method"] == "Apply"
        )
        apply_method["bodySha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "audit.json"
            changed.write_text(json.dumps(audit), encoding="utf-8")
            with mock.patch.object(MODULE, "NATIVE_AUDIT", changed):
                with self.assertRaisesRegex(ValueError, "audit content hash drifted"):
                    MODULE.build()

    def test_runtime_uses_exact_cubic_payload_without_fitted_curve(self) -> None:
        runtime = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldRecoveredEndminfSourcePostCurves.cs"
        ).read_text(encoding="utf-8")
        clock = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "EndfieldEndminfVisualCompatibilityClock.cs"
        ).read_text(encoding="utf-8")
        pipeline = (
            HERE.parent
            / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
            / "HGCompatRenderPipeline.cs"
        ).read_text(encoding="utf-8")
        for token in (
            EXPECTED_PAYLOAD_SHA256,
            "Resources.Load<TextAsset>(ResourceName)",
            'Replace("\\r\\n", "\\n")',
            "sha.ComputeHash(Encoding.UTF8.GetBytes(normalizedPayload))",
            "return ((key.a * delta + key.b) * delta + key.c) * delta + key.d;",
        ):
            self.assertIn(token, runtime)
        self.assertIn("EndfieldRecoveredEndminfSourcePostCurves.TryEvaluate(", clock)
        self.assertIn("public static bool SourcePostClockAuthenticated => false;", clock)
        evaluator = clock[
            clock.index("public static bool TryEvaluateRecoveredPost("):
            clock.index("private static bool TryGetAuthenticatedSourcePostElapsed(")
        ]
        self.assertIn("!TryGetAuthenticatedSourcePostElapsed(out float elapsed)", evaluator)
        self.assertNotIn("TryGetElapsed(", evaluator)
        for token in (
            "EvaluateSourceCurve(",
            "initialPeak * 0.45f",
            "4.3166667f",
            "4.35f",
            "4.5166667f",
        ):
            self.assertNotIn(token, clock)
        self.assertIn("endminfPost.radialIntensity,", pipeline)
        self.assertIn("endminfPost.chromaticIntensity,", pipeline)
        self.assertNotIn("EndminfCompatibilityUberIntensityScale", pipeline)


if __name__ == "__main__":
    unittest.main()
