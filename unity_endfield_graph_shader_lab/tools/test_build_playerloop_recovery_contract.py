import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

MODULE_PATH = Path(__file__).with_name("build_playerloop_recovery_contract.py")
SPEC = importlib.util.spec_from_file_location("playerloop_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PlayerLoopContractTests(unittest.TestCase):
    def test_current_contract_has_exact_anchors_and_flags(self):
        contract = json.loads(MODULE.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "partial_unresolved_first_system_anchor")
        self.assertEqual([row["categoryName"]["value"] for row in contract["insertions"]], ["EarlyUpdate", "FixedUpdate", "Update", "PreLateUpdate", "PreLateUpdate", "PostLateUpdate", "PostLateUpdate"])
        self.assertEqual(
            contract["insertions"][0]["systemName"]["status"],
            "unresolved_initialized_static_field",
        )
        self.assertNotIn("value", contract["insertions"][0]["systemName"])
        self.assertEqual(
            [row["systemName"]["value"] for row in contract["insertions"][1:]],
            ["ScriptRunBehaviourFixedUpdate", "ScriptRunDelayedTasks", "ScriptRunBehaviourLateUpdate", "ScriptRunBehaviourLateUpdate", "ScriptRunDelayedDynamicFrameRate", "FinishFrameRendering"],
        )
        self.assertEqual([(row["last"], row["before"]) for row in contract["insertions"]], [(True, False), (False, False), (False, False), (False, True), (False, False), (False, False), (False, False)])

    def test_native_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing.dll"
            result = MODULE.build_contract(missing, missing, missing, missing)
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("missing GameAssembly.dll", result["validationFailures"][0])

    def test_stack_argument_requires_one_exact_write(self):
        exact = {"nearbyInstructions": [{"text": "mov [rsp+0x20], 0x1"}]}
        self.assertIs(MODULE._stack_value(exact, "0x20"), True)
        ambiguous = {"nearbyInstructions": [
            {"text": "mov [rsp+0x20], r14b"},
            {"text": "mov [rsp+0x20], 0x1"},
        ]}
        self.assertIsNone(MODULE._stack_value(ambiguous, "0x20"))
        noisy = {"nearbyInstructions": [{"text": "mov eax, 0x1"}]}
        self.assertIsNone(MODULE._stack_value(noisy, "0x20"))


if __name__ == "__main__":
    unittest.main()
