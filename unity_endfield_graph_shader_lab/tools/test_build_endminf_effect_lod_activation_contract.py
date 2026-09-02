#!/usr/bin/env python3
"""Focused source/lifecycle tests for Endminf EffectLod activation recovery."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
LAB = HERE.parent
SPEC = importlib.util.spec_from_file_location(
    "build_endminf_effect_lod_activation_contract",
    HERE / "build_endminf_effect_lod_activation_contract.py",
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
RUNTIME = (
    LAB / "Assets/EndfieldGraphShaderLab/Runtime/Animation/"
    "EndfieldRecoveredEffectLodActivation.cs"
)
IMPORTER = (
    LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectImporter.cs"
)


class EndminfEffectLodActivationContractTests(unittest.TestCase):
    def test_published_contract_matches_exact_typetree_sources(self) -> None:
        payload = MOD.build(MOD.DEFAULT_STAGE, MOD.DEFAULT_DUMP)
        published = json.loads(MOD.OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload, published)
        self.assertEqual(len(payload["rows"]), 101)
        self.assertTrue(all(row["authoredInitialActive"] for row in payload["rows"]))
        self.assertEqual(
            payload["runtimeDefaults"],
            {
                "qualitySettingLodLevel": 8,
                "qualityNormalizationDomain": [1, 2, 4, 8],
                "targetLayers": 1,
            },
        )
        native = payload["nativeEvidence"]
        self.assertEqual(len(native["methodIdentities"]), len(MOD.NATIVE_METHODS))
        self.assertTrue(native["recordedInstalledIfixNonreplacement"])
        self.assertEqual(
            [row["name"] for row in native["byteGates"]],
            [row[0] for row in MOD.NATIVE_GATES],
        )
        self.assertEqual(
            [int(row["callVirtualAddress"], 16)
             for row in native["setAllTargetLayersDirectCallers"]],
            [0x183237E09, 0x183238163, 0x18323819A, 0x184D46F41],
        )

    def test_runtime_uses_normal_creation_masks_and_authored_initial_state(self) -> None:
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("NormalCreationQualitySettingLodLevel = 8", source)
        self.assertIn("NormalCreationTargetLayers = 1", source)
        self.assertIn("row.authoredInitialActive &&", source)
        self.assertIn("requestedLevel == 1 || requestedLevel == 2", source)
        self.assertNotIn("showSettingLodLevel", source)
        self.assertNotIn("showTargetLayers", source)

    def test_importer_configures_inactive_before_addcomponent_and_onenable(self) -> None:
        source = IMPORTER.read_text(encoding="utf-8")
        construct = source.index("var obj = new GameObject")
        inactive = source.index("obj.SetActive(false);", construct)
        attach = source.index("AttachExactLodActivation(", inactive)
        self.assertLess(inactive, attach)
        self.assertNotIn("obj.SetActive(true);", source)
        lod = source.index(
            "var activation = root.AddComponent<EndfieldRecoveredEffectLodActivation>();"
        )
        disabled = source.index("activation.enabled = false;", lod)
        rows = source.index("activation.rows = rows.ToArray();", disabled)
        apply = source.index("activation.ApplyBeforePlay();", rows)
        enabled = source.index("activation.enabled = true;", apply)
        self.assertLess(disabled, rows)
        self.assertLess(rows, apply)
        self.assertLess(apply, enabled)
        self.assertNotIn("activation.showSettingLodLevel", source)
        self.assertNotIn("activation.showTargetLayers", source)

    def test_missing_active_field_fails_closed(self) -> None:
        source_path = next(MOD.DEFAULT_DUMP.glob("*.txt"))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / source_path.name
            target.write_text(
                source_path.read_text(encoding="utf-8").replace(
                    "bool m_IsActive = True", "bool source_active_removed = True"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "missing serialized m_IsActive"):
                MOD.build(MOD.DEFAULT_STAGE, Path(folder))

    def test_other_native_build_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            wrong = Path(folder) / "GameAssembly.dll"
            wrong.write_bytes(b"not the pinned build")
            with self.assertRaisesRegex(ValueError, "native input gate failed closed"):
                MOD.validate_native(wrong, MOD.DEFAULT_METADATA, MOD.IFIX_STATE)

    def test_native_default_gate_drift_fails_closed(self) -> None:
        original = MOD.read_native_window

        def changed(path: Path, offset: int, size: int) -> bytes:
            value = original(path, offset, size)
            if offset == 0x3AE329B:
                value = bytes([value[0] ^ 1]) + value[1:]
            return value

        with mock.patch.object(MOD, "read_native_window", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "effect_lod_ctor_defaults"):
                MOD.validate_native(
                    MOD.DEFAULT_GAMEASSEMBLY, MOD.DEFAULT_METADATA, MOD.IFIX_STATE
                )

    def test_native_refresh_predicate_drift_fails_closed(self) -> None:
        original = MOD.read_native_window

        def changed(path: Path, offset: int, size: int) -> bytes:
            value = original(path, offset, size)
            if offset == 0x31F52D1:
                value = value[:-1] + bytes([value[-1] ^ 1])
            return value

        with mock.patch.object(MOD, "read_native_window", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "refresh_predicate_and_set_active"):
                MOD.validate_native(
                    MOD.DEFAULT_GAMEASSEMBLY, MOD.DEFAULT_METADATA, MOD.IFIX_STATE
                )

    def test_target_layer_cold_caller_ownership_drift_fails_closed(self) -> None:
        original = MOD.read_native_window

        def changed(path: Path, offset: int, size: int) -> bytes:
            value = original(path, offset, size)
            if offset == 0x4D458CE:
                value = bytes([value[0] ^ 1]) + value[1:]
            return value

        with mock.patch.object(MOD, "read_native_window", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "caller ownership window"):
                MOD.validate_native(
                    MOD.DEFAULT_GAMEASSEMBLY, MOD.DEFAULT_METADATA, MOD.IFIX_STATE
                )


if __name__ == "__main__":
    unittest.main()
