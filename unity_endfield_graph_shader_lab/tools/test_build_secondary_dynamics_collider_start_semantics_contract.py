import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
REPORT = SOURCE / "secondary_dynamics_collider_start_semantics_contract.json"


class ColliderStartSemanticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(REPORT.read_text(encoding="utf-8"))
        cls.by_hash = {row["hash"]: row for row in cls.payload["targets"]}

    def test_native_gate_is_three_file_pinned(self):
        gate = self.payload["nativeGate"]
        self.assertEqual(gate["gameAssembly"]["sha256"], "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce")
        self.assertEqual(gate["globalMetadata"]["sha256"], "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e")
        self.assertEqual(gate["libBurstGenerated"]["sha256"], "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99")

    def test_three_candidates_are_bounded(self):
        self.assertEqual(set(self.by_hash), {
            "4aa6773b1eaf6055e0feb9593e092585",
            "7342567c29c434b5b924be51bd8e34b7",
            "8b3d2761aaaac71a35d4a2557d570456",
        })
        self.assertEqual(len(self.by_hash), 3)

    def test_argument_reorder_excludes_first_candidate(self):
        row = self.by_hash["4aa6773b1eaf6055e0feb9593e092585"]
        self.assertFalse(row["callMapping"]["canonicalOrderExact"])
        self.assertEqual(row["callMapping"]["callArgumentSources"][:4], ["param16", "param2", "param3", "param4"])
        self.assertFalse(row["semanticMatch"]["allRequiredChecksPass"])

    def test_semantic_candidate_matches_both_cpu_variants(self):
        row = self.by_hash["8b3d2761aaaac71a35d4a2557d570456"]
        self.assertTrue(row["callMapping"]["canonicalOrderExact"])
        self.assertTrue(row["semanticMatch"]["allRequiredChecksPass"])
        for variant in ("avx2", "x64_sse2"):
            checks = row["semanticMatch"]["guardMatches"][variant]
            self.assertTrue(checks["flagArrayParam5"])
            self.assertTrue(checks["teamIdWordParam4"])
            self.assertTrue(checks["teamDataStride464"])
            self.assertTrue(checks["indexParameter17"])

    def test_near_candidate_is_rejected_by_body_accesses(self):
        row = self.by_hash["7342567c29c434b5b924be51bd8e34b7"]
        self.assertTrue(row["callMapping"]["canonicalOrderExact"])
        self.assertFalse(row["semanticMatch"]["allRequiredChecksPass"])
        for variant in ("avx2", "x64_sse2"):
            checks = row["semanticMatch"]["guardMatches"][variant]
            self.assertFalse(checks["flagArrayParam5"])

    def test_initializer_chains_are_recorded_without_runtime_identity(self):
        expected_core = {
            "4aa6773b1eaf6055e0feb9593e092585": {"avx2": "0x24fa60", "x64_sse2": "0xb5450"},
            "7342567c29c434b5b924be51bd8e34b7": {"avx2": "0x284c50", "x64_sse2": "0xf4100"},
            "8b3d2761aaaac71a35d4a2557d570456": {"avx2": "0x243810", "x64_sse2": "0xa7e50"},
        }
        for hash_name, row in self.by_hash.items():
            by_variant = {item["cpuVariant"]: item for item in row["initializerAssignments"]}
            for variant, core in expected_core[hash_name].items():
                self.assertEqual(by_variant[variant]["core"]["beginRva"], core)
                self.assertGreaterEqual(len(by_variant[variant]["callChain"]), 2)
        decision = self.payload["semanticDecision"]
        self.assertEqual(decision["semanticCandidateHash"], "8b3d2761aaaac71a35d4a2557d570456")
        self.assertFalse(decision["wrapperHashIdentityPublished"])
        self.assertEqual(decision["wrapperToHashMappingStatus"], "unresolved_runtime_GetProcAddress_required")


if __name__ == "__main__":
    unittest.main()
