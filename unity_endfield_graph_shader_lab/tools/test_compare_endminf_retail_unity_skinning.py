#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("compare_endminf_retail_unity_skinning.py")
SPEC = importlib.util.spec_from_file_location("endminf_skin_compare", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def identity():
    return [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


class ComparatorTests(unittest.TestCase):
    def test_rigid_interpolation_and_metrics(self):
        bindpose = identity()
        low = identity()
        high = identity()
        high[0][3] = 2.0
        unity_skin = identity()
        unity_skin[0][3] = 1.0
        row = {"bindpose": bindpose, "skin": unity_skin, "root": unity_skin, "path": "bone"}
        result = MODULE.compare_mesh("hair", [row], [low], [high], 0.5)
        self.assertAlmostEqual(result["elementAbsoluteError"]["max"], 0.0)
        self.assertAlmostEqual(result["rootTranslationError"]["max"], 0.0)
        self.assertAlmostEqual(result["rootRotationErrorDegrees"]["max"], 0.0)

    def test_bindpose_is_inverted_before_root_interpolation(self):
        bindpose = identity()
        bindpose[0][3] = -3.0
        low_root = identity()
        low_root[1][3] = 2.0
        high_root = identity()
        high_root[1][3] = 4.0
        unity_root = identity()
        unity_root[1][3] = 3.0
        low_skin = MODULE.mat_mul(low_root, bindpose)
        high_skin = MODULE.mat_mul(high_root, bindpose)
        unity_skin = MODULE.mat_mul(unity_root, bindpose)
        row = {"bindpose": bindpose, "skin": unity_skin, "root": unity_root, "path": "bone"}
        result = MODULE.compare_mesh("cloth_04", [row], [low_skin], [high_skin], 0.5)
        self.assertAlmostEqual(result["elementAbsoluteError"]["max"], 0.0)
        self.assertAlmostEqual(result["rootTranslationError"]["max"], 0.0)

    def test_non_rigid_root_fails_closed(self):
        matrix = identity()
        matrix[0][0] = 1.2
        with self.assertRaisesRegex(MODULE.ComparisonError, "non-unit scale"):
            MODULE.rigid_parts(matrix, "bad root")

    def test_non_finite_report_matrix_fails_closed(self):
        value = {
            f"row{row}": {component: (float("nan") if row == 2 and component == "z" else 0.0) for component in "xyzw"}
            for row in range(4)
        }
        with self.assertRaisesRegex(MODULE.ComparisonError, "not finite"):
            MODULE.report_matrix(value, "bad matrix")

    def test_timing_boundary_requires_both_uncertainty_edges(self):
        rows = [(100, 1_000_000, Path("100")), (104, 1_600_000, Path("104"))]
        low, high = MODULE.bracket(rows, 102.0, 1.0)
        self.assertEqual((low[0], high[0]), (100, 104))
        with self.assertRaisesRegex(MODULE.ComparisonError, "do not bracket"):
            MODULE.bracket(rows, 100.5, 1.0)

    def test_resource_binding_rejects_unmatched_cb2_id(self):
        metadata = {
            "frame": 1,
            "selectedResourceRecords": [
                {"completed": True, "captureKind": 5, "byteSize": MODULE.PALETTE_BYTES, "blobBytes": MODULE.PALETTE_BYTES, "objectId": 20},
                {"completed": False, "captureKind": 3, "byteSize": MODULE.PALETTE_BYTES, "blobBytes": 0, "objectId": 20},
                {"completed": True, "captureKind": 2, "byteSize": MODULE.CB2_BYTES, "blobBytes": MODULE.CB2_BYTES, "objectId": 30},
            ],
        }
        with self.assertRaisesRegex(MODULE.ComparisonError, "does not match"):
            MODULE.select_resources(metadata, {31})

    def test_shader_identity_fails_closed(self):
        metadata = {
            "frame": 1,
            "drawRecords": [{
                "indexedInstanced": True, "count": 27_615,
                "vsCb2RangeValid": True, "vsCb2MetadataValid": True,
                "vsCb2NumConstants": MODULE.CB2_CONSTANTS,
                "vsCb2CurrentPaletteRaw": 1, "vsCb2PreviousPaletteRaw": 2,
                "vsCb2BufferId": 30,
                "shaders": [{"stage": 0, "identityHash": 9, "bytecodeSize": 9}, {"stage": 4, "identityHash": 8, "bytecodeSize": 8}],
            }],
        }
        with self.assertRaisesRegex(MODULE.ComparisonError, "no gated hair draw"):
            MODULE.select_draw(metadata, "hair")

    def test_cloth_02_contract_matches_retained_peak_draw(self):
        contract = MODULE.MESHES["cloth_02"]
        self.assertEqual(contract["indexCount"], 2_286)
        self.assertEqual(contract["matrixCount"], 29)
        self.assertIn((13_479_119_685_698_484_394, 8296), contract["vertexShaders"])

    def test_select_draw_ignores_non_palette_shader_variants(self):
        good_vs = next(iter(MODULE.MESHES["cloth_02"]["vertexShaders"]))
        common = {
            "indexedInstanced": True, "count": 2_286,
            "vsCb2RangeValid": True, "vsCb2MetadataValid": True,
            "vsCb2BufferId": 30,
        }
        metadata = {"frame": 1, "drawRecords": [
            {**common, "vsCb2NumConstants": 16, "vsCb2CurrentPaletteRaw": 0, "vsCb2PreviousPaletteRaw": 0,
             "shaders": [{"stage": 0, "identityHash": 1, "bytecodeSize": 6136}, {"stage": 4, "identityHash": 8, "bytecodeSize": 8}]},
            {**common, "vsCb2NumConstants": MODULE.CB2_CONSTANTS, "vsCb2CurrentPaletteRaw": 10, "vsCb2PreviousPaletteRaw": 9,
             "shaders": [{"stage": 0, "identityHash": good_vs[0], "bytecodeSize": good_vs[1]}, {"stage": 4, "identityHash": 8, "bytecodeSize": 8}]},
        ]}
        selected = MODULE.select_draw(metadata, "cloth_02")
        self.assertEqual(selected["currentRaw"], 10)


if __name__ == "__main__":
    unittest.main()
