import importlib.util
import json
import struct
import sys
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("build_secondary_dynamics_simulation_step_team_update_contract.py")
if str(PATH.parent) not in sys.path:
    sys.path.insert(0, str(PATH.parent))
SPEC = importlib.util.spec_from_file_location("simulation_step_team_update_contract", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SimulationStepTeamUpdateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = MODULE.build_contract()

    def test_target_is_ready_only_for_the_named_boundary(self):
        self.assertTrue(self.payload["targetReady"])
        self.assertTrue(self.payload["failClosedBoundary"]["targetReady"])
        self.assertIn("stationary actor root", self.payload["failClosedBoundary"]["supported"])
        self.assertIn("IFix/patched route", self.payload["failClosedBoundary"]["rejected"])

    def test_native_identity_is_hash_pinned(self):
        identity = self.payload["burstIdentity"]
        self.assertEqual(identity["export"]["name"], MODULE.EXPORT_NAME)
        self.assertEqual(identity["avx2"]["core"]["sha256"], MODULE.AVX_CORE_SHA256)

    def test_owner_values_are_exact_binary32(self):
        owners = {row["owner"]: row for row in self.payload["endminfTarget"]["owners"]}
        self.assertEqual(owners["MC_Hair"]["localInertiaF32"], 1.0)
        self.assertEqual(owners["MC_Hair"]["depthInertiaF32"], 1.0)
        self.assertEqual(struct.pack("<f", owners["MC_Coat"]["localInertiaF32"]).hex(), "cdcc4c3f")
        self.assertEqual(struct.pack("<f", owners["MC_Coat"]["depthInertiaF32"]).hex(), "3333333f")

    def test_unclamped_ratios_use_local_not_world_or_depth_inertia(self):
        owners = {row["owner"]: row for row in self.payload["endminfTarget"]["owners"]}
        self.assertEqual(owners["MC_Hair"]["teamUpdateUnclampedRatios"]["stepMoveInertiaRatio"], 0.0)
        self.assertEqual(struct.pack("<f", owners["MC_Coat"]["teamUpdateUnclampedRatios"]["stepMoveInertiaRatio"]).hex(), "cccc4c3e")

    def test_depth_is_deferred_to_simulation_start(self):
        boundary = self.payload["endminfTarget"]["depthBoundary"]
        self.assertIn("not a SimulationStepTeamUpdate input", boundary)
        self.assertIn("k=(1-depth^2)*depthInertia", boundary)

    def test_write_ownership_preserves_three_fields(self):
        ownership = self.payload["writeOwnership"]
        self.assertEqual(ownership["preservedByThisKernel"],
                         ["stepMovingSpeed", "stepMovingDirection", "initLocalGravityDirection"])
        self.assertNotIn("stepMovingSpeed", ownership["written"])

    def test_hair_and_coat_native_vectors_exist_and_preserve_sentinels(self):
        vectors = self.payload["verification"]["vectors"]
        self.assertIn("mc_hair", vectors[0]["name"])
        self.assertIn("mc_coat", vectors[1]["name"])
        self.assertTrue(all(all(row["preservedSentinels"].values()) for row in vectors))
        hair, coat = vectors
        self.assertEqual(hair["selectedNativeOutputs"]["stepMoveInertiaRatio"]["bits"], "00000000")
        self.assertEqual(coat["selectedNativeOutputs"]["stepMoveInertiaRatio"]["bits"], "cccc4c3e")

    def test_generated_contract_matches_builder(self):
        generated = json.loads(MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(generated, self.payload)


if __name__ == "__main__":
    unittest.main()
