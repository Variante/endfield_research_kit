#!/usr/bin/env python3
"""Pins symmetric LayerMask import and verification for recovered Endminf VFX."""

from pathlib import Path
import unittest


LAB = Path(__file__).resolve().parents[1]
IMPORTER = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldZhuangfyParticleEffectImporter.cs"
)


class EndminfZhuangfyLayerMaskVerificationContractTests(unittest.TestCase):
    def test_apply_and_verify_share_unsigned_m_bits_conversion(self) -> None:
        source = IMPORTER.read_text(encoding="utf-8")
        self.assertEqual(source.count("LayerMaskInt(value, path)"), 2)
        helper = source[source.index("private static int LayerMaskInt"):]
        self.assertIn('dictionary.TryGetValue("m_Bits", out source)', helper)
        self.assertIn("Convert.ToUInt32(", helper)
        self.assertIn("unchecked((int)", helper)

    def test_conversion_failures_identify_path_type_and_value(self) -> None:
        source = IMPORTER.read_text(encoding="utf-8")
        helper = source[source.index("private static int LayerMaskInt"):]
        for diagnostic in (
            "object without required m_Bits",
            "Layer mask source conversion failed at {path}",
            "expected UInt32",
            "actual type={sourceType}",
            "value={sourceValue}",
        ):
            self.assertIn(diagnostic, helper)
        for exception in (
            "InvalidCastException",
            "FormatException",
            "OverflowException",
        ):
            self.assertIn(exception, helper)


if __name__ == "__main__":
    unittest.main()
