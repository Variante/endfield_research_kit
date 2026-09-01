from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_overview_effect_stage.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_overview_effect_stage",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EndminfOverviewEffectStageTests(unittest.TestCase):
    def test_exact_per_owner_stage_content_is_pinned(self) -> None:
        self.assertEqual(
            MODULE.stage_content_sha256(MODULE.DEFAULT_STAGE),
            MODULE.STAGE_CONTENT_SHA256,
        )

    def test_aggregate_preserving_owner_swaps_change_stage_hash(self) -> None:
        mutations = ("scaling", "shape", "materials")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                stage = Path(temp) / "stage"
                shutil.copytree(MODULE.DEFAULT_STAGE, stage)
                if mutation == "scaling":
                    paths = sorted((stage / "ParticleSystem").glob("*.json"))
                    rows = [(path, json.loads(path.read_text(encoding="utf-8")))
                            for path in paths]
                    left = next(item for item in rows if item[1]["scalingMode"] == 0)
                    right = next(item for item in rows if item[1]["scalingMode"] == 1)
                    left[1]["scalingMode"], right[1]["scalingMode"] = (
                        right[1]["scalingMode"], left[1]["scalingMode"]
                    )
                elif mutation == "shape":
                    paths = sorted((stage / "ParticleSystem").glob("*.json"))
                    rows = [(path, json.loads(path.read_text(encoding="utf-8")))
                            for path in paths]
                    left = next(item for item in rows if int(
                        (item[1].get("ShapeModule") or {}).get("m_Texture", {})
                        .get("m_PathID", 0)) == MODULE.SHAPE_TEXTURE_PATH_ID)
                    right = next(item for item in rows if int(
                        (item[1].get("ShapeModule") or {}).get("m_Texture", {})
                        .get("m_PathID", 0)) == 0)
                    left_shape = left[1]["ShapeModule"]
                    right_shape = right[1]["ShapeModule"]
                    left_shape["m_Texture"], right_shape["m_Texture"] = (
                        copy.deepcopy(right_shape["m_Texture"]),
                        copy.deepcopy(left_shape["m_Texture"]),
                    )
                else:
                    paths = sorted((stage / "ParticleSystemRenderer").glob("*.json"))
                    rows = [(path, json.loads(path.read_text(encoding="utf-8")))
                            for path in paths]
                    left = rows[0]
                    right = next(
                        item for item in rows[1:]
                        if item[1].get("m_Materials") != left[1].get("m_Materials")
                    )
                    left[1]["m_Materials"], right[1]["m_Materials"] = (
                        copy.deepcopy(right[1]["m_Materials"]),
                        copy.deepcopy(left[1]["m_Materials"]),
                    )
                for path, row in (left, right):
                    path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
                self.assertNotEqual(
                    MODULE.stage_content_sha256(stage),
                    MODULE.STAGE_CONTENT_SHA256,
                )
                with self.assertRaisesRegex(
                    RuntimeError,
                    "exact per-owner stage content drifted",
                ):
                    MODULE.validate(stage, MODULE.DEFAULT_CLOSURE)

    def test_v2_consumers_use_direct_renderer_ownership(self) -> None:
        spawner = MODULE.SPAWNER.read_text(encoding="utf-8")
        self.assertIn(
            '"endfield.endminf-overview-particle-stage.v2"',
            spawner,
        )
        self.assertIn("TryValidateEndminfV2Marker(", spawner)
        for path in (
            MODULE.LITEFFECT_BINDING_BUILDER,
            MODULE.M27_ABI_PROBE,
            MODULE.BLOCKED_CENSUS,
        ):
            source = path.read_text(encoding="utf-8")
            self.assertIn(".generatedRenderer", source)
            self.assertNotIn("renderers[index]", source)


if __name__ == "__main__":
    unittest.main()
