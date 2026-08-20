import importlib.util
import json
import sys
import unittest
from pathlib import Path

from scripts.common import resolve_installed_native_inputs


MODULE_PATH = Path(__file__).with_name("build_secondary_dynamics_spring_semantics_contract.py")
SPEC = importlib.util.spec_from_file_location("secondary_spring_contract_test_module", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


GAME_ASSEMBLY, METADATA = resolve_installed_native_inputs()
OUTPUT = MODULE.DEFAULT_OUTPUT
MARKDOWN = MODULE.DEFAULT_MARKDOWN


class SpringContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = MODULE.build_contract(GAME_ASSEMBLY, METADATA)

    def test_checked_in_contract_is_current(self) -> None:
        self.assertEqual(json.loads(OUTPUT.read_text(encoding="utf-8")), self.contract)
        self.assertEqual(MARKDOWN.read_text(encoding="utf-8"), MODULE._markdown(self.contract))

    def test_method_identity_and_solver_boundary(self) -> None:
        self.assertEqual(self.contract["status"], "managed_spring_static_semantics_closed")
        self.assertFalse(self.contract["solverImplemented"])
        self.assertFalse(self.contract["retailEquivalent"])
        method = self.contract["method"]
        self.assertEqual(method["methodIndex"], 385698)
        self.assertEqual(method["spanBytes"], 0x59C)
        self.assertEqual(method["bodySha256"], MODULE.METHOD_SHA256)
        self.assertEqual(method["arrayStrideStatus"], "not_applicable_helper_has_no_nativearray_operand")
        self.assertEqual(method["nativeArrayAccesses"], [])

    def test_parameter_and_direct_layout_evidence(self) -> None:
        method = self.contract["method"]
        self.assertEqual(
            [row["name"] for row in method["parameters"]],
            ["springParams", "normalAxis", "nextPos", "basePos", "baseRot", "noiseTime", "scaleRatio"],
        )
        layout = method["valueTypeLayouts"][0]
        self.assertEqual(layout["name"], "BeyondDynamicBone.SpringConstraint+SpringConstraintParams")
        self.assertEqual(
            [(row["name"], row["nativePayloadOffset"]) for row in layout["fields"]],
            [("springPower", "0x0"), ("limitDistance", "0x4"),
             ("normalLimitRatio", "0x8"), ("springNoise", "0xc")],
        )
        abi = {(row["argument"], row["location"]): row for row in method["argumentAbi"]}
        self.assertEqual(abi[("nextPos", "r14")]["instructionOffset"], "0x26")
        self.assertEqual(abi[("springParams", "rdi")]["instructionOffset"], "0x34")
        self.assertEqual(abi[("basePos", "r15")]["instructionOffset"], "0x76")
        self.assertEqual(abi[("noiseTime", "[rbp+0x60]")]["instructionOffset"], "0x438")

    def test_branch_and_call_counts_and_patch_gate(self) -> None:
        method = self.contract["method"]
        self.assertEqual(len(method["directCalls"]), 29)
        self.assertEqual(len(method["branches"]), 22)
        branches = {(row["instructionOffset"], row["mnemonic"]): row["targetOffset"] for row in method["branches"]}
        self.assertEqual(branches[("0x70", "jne")], "0x50b")
        self.assertEqual(branches[("0x51b", "jne")], "0x523")
        self.assertEqual(branches[("0xf9", "je")], "0x17f")
        self.assertEqual(branches[("0x218", "jmp")], "0x41d")
        calls = {(row["instructionOffset"], row["targetVa"]) for row in method["directCalls"]}
        self.assertIn(("0x69", "0x182f95a30"), calls)
        self.assertIn(("0x510", "0x185396738"), calls)
        self.assertIn(("0x55f", "0x1866e13d0"), calls)

    def test_constants_and_memory_operands(self) -> None:
        method = self.contract["method"]
        constants = {(row["instructionOffset"], row["value"]): row["targetVa"] for row in method["constants"]}
        self.assertEqual(constants[("0xb6", 1.0)], "0x18b959200")
        self.assertEqual(constants[("0x1e1", 9.99999993922529e-09)], "0x18b9593b4")
        self.assertEqual(constants[("0x447", 0.6000000238418579)], "0x18b959530")
        self.assertEqual(constants[("0x45e", 0.0)], "0x18b959248")
        accesses = {(row["owner"], row["displacementBytes"], row["access"]): row for row in method["memoryAccesses"]}
        self.assertIn(("SpringConstraintParams.limitDistance", 4, "read"), accesses)
        self.assertIn(("SpringConstraintParams.normalLimitRatio", 8, "read"), accesses)
        self.assertIn(("SpringConstraintParams.springNoise", 12, "read"), accesses)
        self.assertEqual(accesses[("nextPos", 0, "write")]["baseRegister"], "r14")

    def test_memory_direction_and_constant_opcode_fail_closed(self) -> None:
        body = bytearray(MODULE._ACTIVE_PE.bytes_at_va(MODULE.METHOD_VA, MODULE.METHOD_END - MODULE.METHOD_VA))
        body[0x4FF + 2] = 0x10  # turn movups store (0x11) into a load
        with self.assertRaises(MODULE.ContractError):
            MODULE._verify_memory_sites(bytes(body))
        body = bytearray(MODULE._ACTIVE_PE.bytes_at_va(MODULE.METHOD_VA, MODULE.METHOD_END - MODULE.METHOD_VA))
        body[0xB6] = 0xF2  # prefix drift; RIP target alone must not pass
        with self.assertRaises(MODULE.ContractError):
            MODULE._constant_site(bytes(body), MODULE.METHOD_VA, 0xB6, 0x18B959200, "float32", 4)

    def test_check_diff_reports_bounded_path(self) -> None:
        self.assertEqual(
            MODULE._first_diff({"method": {"span": 1}}, {"method": {"span": 2}}),
            ("$.method.span", "1", "2"),
        )

    def test_branch_verifier_fails_closed_on_tampered_bytes(self) -> None:
        method = self.contract["method"]
        branch = next(row for row in method["branches"] if row["instructionOffset"] == "0x70")
        offset = int(branch["instructionOffset"], 16)
        body = bytearray(b"\x90" * (MODULE.METHOD_END - MODULE.METHOD_VA))
        body[offset:offset + len(bytes.fromhex(branch["instructionBytes"]))] = bytes.fromhex(branch["instructionBytes"])
        body[offset + 1] = 0x84  # same rel32 target, opposite condition
        mnemonic, target, _bytes = MODULE._branch_bytes(bytes(body), offset)
        self.assertEqual(target, int(branch["targetOffset"], 16))
        self.assertNotEqual(mnemonic, branch["mnemonic"])


if __name__ == "__main__":
    unittest.main()
