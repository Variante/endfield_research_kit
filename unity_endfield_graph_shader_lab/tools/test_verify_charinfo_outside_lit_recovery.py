#!/usr/bin/env python3
"""Focused tests for SphereOutside recovery validator diagnostics."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name(
    "verify_charinfo_outside_lit_recovery.py"
)
MODULE_SPEC = importlib.util.spec_from_file_location(
    "verify_charinfo_outside_lit_recovery",
    MODULE_PATH,
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"cannot load verifier module: {MODULE_PATH}")
verifier = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(verifier)


class UnityLogEvidenceTests(unittest.TestCase):
    def test_exact_pinned_log_passes_without_semantic_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unity.log"
            path.write_text("exact pinned log", encoding="utf-8")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                verifier.require_unity_log(path, expected, ["not required"])
            self.assertEqual(output.getvalue(), "")

    def test_rerun_log_requires_all_semantic_success_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unity.log"
            path.write_text(
                "Verifier.BuildAndValidate\nreport written\nreturn code 0\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                verifier.require_unity_log(
                    path,
                    "0" * 64,
                    ["Verifier.BuildAndValidate", "report written", "return code 0"],
                )
            message = output.getvalue()
            self.assertIn("semantic gate passed", message)
            self.assertIn("pinned=" + "0" * 64, message)

    def test_rerun_log_reports_the_missing_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unity.log"
            path.write_text("Verifier.BuildAndValidate\n", encoding="utf-8")
            with self.assertRaisesRegex(
                AssertionError,
                "missing token 'return code 0'",
            ):
                verifier.require_unity_log(
                    path,
                    "0" * 64,
                    ["Verifier.BuildAndValidate", "return code 0"],
                )


class SourceTextEvidenceTests(unittest.TestCase):
    def test_source_hash_accepts_crlf_checkout_of_pinned_lf_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.cs"
            path.write_bytes(b"first\r\nsecond\r\n")
            expected = hashlib.sha256(b"first\nsecond\n").hexdigest()
            verifier.require_text_hash(path, expected)

    def test_source_hash_reports_expected_and_actual_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.cs"
            path.write_text("actual\n", encoding="utf-8")
            with self.assertRaisesRegex(
                AssertionError,
                "canonical-LF SHA-256.*does not match pinned",
            ):
                verifier.require_text_hash(path, "0" * 64)


class DeferredGBufferFrameContractTests(unittest.TestCase):
    @staticmethod
    def load_current_report(
        api: str = "d3d12",
    ) -> tuple[dict[str, object], dict[str, object]]:
        contract = json.loads(
            verifier.BINDING_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        transport = contract["deferred_gbuffer_frame_transport"]
        evidence = transport["validation"]["gpu_reports"][api]
        report = json.loads(
            (verifier.LAB_ROOT / evidence["path"]).read_text(encoding="utf-8")
        )
        return transport, report

    def test_current_same_camera_frame_report_passes(self) -> None:
        transport, report = self.load_current_report()
        verifier.verify_deferred_gbuffer_frame_report(
            transport,
            report,
            "d3d12",
            source=Path("fixture_contract.json"),
        )

    def test_changed_gbuffer_payload_failure_is_actionable(self) -> None:
        transport, report = self.load_current_report()
        changed = copy.deepcopy(report)
        changed["gpuReadbacks"]["GBufferB"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            AssertionError,
            "Deferred HGBuffer frame validator failed: "
            "check=frame_report.d3d12.readbacks; "
            "source=fixture_contract.json; expected=.*18e66c.*actual=.*000000",
        ):
            verifier.verify_deferred_gbuffer_frame_report(
                transport,
                changed,
                "d3d12",
                source=Path("fixture_contract.json"),
            )


class HGBufferMotionContractTests(unittest.TestCase):
    def test_source_hgbuffer_motion_varyings_and_encoding_are_pinned(self) -> None:
        recovery = json.loads(
            verifier.RECOVERY_PATH.read_text(encoding="utf-8")
        )
        verifier.verify_hgbuffer(recovery)


class DeferredTransformVariablesContractTests(unittest.TestCase):
    @staticmethod
    def load_current_report(
        api: str = "d3d12",
    ) -> dict[str, object]:
        contract = json.loads(
            verifier.BINDING_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        evidence = contract[
            "selected_deferred_transform_variables_transport"
        ]["validation"]["gpu_reports"][api]
        return json.loads(
            (verifier.LAB_ROOT / evidence["path"]).read_text(
                encoding="utf-8"
            )
        )

    def test_current_transform_variables_report_passes(self) -> None:
        report = self.load_current_report()
        verifier.verify_deferred_transform_variables_gpu_report(
            report,
            "d3d12",
            Path("fixture_contract.json"),
        )

    def test_changed_transform_word_failure_is_actionable(self) -> None:
        report = self.load_current_report()
        changed = copy.deepcopy(report)
        changed["actualWords"][0] = "0x00000000"
        with self.assertRaisesRegex(
            AssertionError,
            "Deferred TransformVariables validator failed: "
            "check=transform_variables.d3d12.words; "
            "source=fixture_contract.json",
        ):
            verifier.verify_deferred_transform_variables_gpu_report(
                changed,
                "d3d12",
                Path("fixture_contract.json"),
            )


class CharInfoV2DataPathContractTests(unittest.TestCase):
    @staticmethod
    def load_current_contract() -> tuple[dict[str, object], dict[str, object]]:
        contract = json.loads(
            verifier.BINDING_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        ownership = contract["charinfo_irradiance_volume_ownership"]
        report = json.loads(
            (
                verifier.LAB_ROOT / ownership["v2_audit_path"]
            ).read_text(encoding="utf-8")
        )
        return ownership, report

    def test_current_v2_data_path_contract_passes(self) -> None:
        ownership, report = self.load_current_contract()
        verifier.verify_charinfo_v2_data_path_contract(
            ownership,
            report,
            Path("fixture_contract.json"),
        )

    def test_shipped_suffix_match_failure_is_actionable(self) -> None:
        ownership, report = self.load_current_contract()
        changed = copy.deepcopy(ownership)
        changed["installed_map_path_selection"][
            "matching_shipped_iv_files"
        ] = 1
        with self.assertRaisesRegex(
            AssertionError,
            "CharInfo V2 irradiance data-path validator failed: "
            "check=installed_map_path_selection.matching_shipped_iv_files; "
            "source=fixture_contract.json; expected=0; actual=1",
        ):
            verifier.verify_charinfo_v2_data_path_contract(
                changed,
                report,
                Path("fixture_contract.json"),
            )

    def test_missing_map_parameter_failure_is_actionable(self) -> None:
        ownership, report = self.load_current_contract()
        changed = copy.deepcopy(report)
        changed["activeClipmaps"]["installedMissingMapState"]["parameters"][
            "param3"
        ][1] = 1.0
        with self.assertRaisesRegex(
            AssertionError,
            "CharInfo V2 irradiance data-path validator failed: "
            "check=audit.active_clipmap.installed_missing_map; "
            "source=fixture_contract.json; expected=.*actual=.*1.0",
        ):
            verifier.verify_charinfo_v2_data_path_contract(
                ownership,
                changed,
                Path("fixture_contract.json"),
            )


class LightBinningContractTests(unittest.TestCase):
    @staticmethod
    def load_current_contract() -> tuple[dict[str, object], dict[str, object]]:
        contract = json.loads(
            verifier.BINDING_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        runtime = contract["light_binning_runtime"]
        audit = json.loads(
            (verifier.LAB_ROOT / runtime["audit_path"]).read_text(
                encoding="utf-8"
            )
        )
        return runtime, audit

    def test_current_light_binning_contract_passes(self) -> None:
        runtime, audit = self.load_current_contract()
        verifier.verify_light_binning_contract(
            runtime,
            audit,
            Path("fixture_contract.json"),
        )

    def test_combined_buffer_size_failure_is_actionable(self) -> None:
        runtime, audit = self.load_current_contract()
        changed = copy.deepcopy(audit)
        changed["combinedBuffer"]["example3840x2160"]["totalBytes"] = 0
        with self.assertRaisesRegex(
            AssertionError,
            "CharInfo light-binning validator failed: "
            "check=contract.combined_buffer; source=fixture_contract.json; "
            "expected=.*totalBytes.*0",
        ):
            verifier.verify_light_binning_contract(
                runtime,
                changed,
                Path("fixture_contract.json"),
            )

    def test_canonical_reflection_tail_failure_is_actionable(self) -> None:
        runtime, _ = self.load_current_contract()
        transport = runtime["canonical_combined_transport"]
        evidence = transport["gpu_reports"]["d3d12"]
        report = json.loads(
            (verifier.LAB_ROOT / evidence["path"]).read_text(encoding="utf-8")
        )
        changed = copy.deepcopy(report)
        changed["reflectionSegmentIsZero"] = False
        with self.assertRaisesRegex(
            AssertionError,
            "CharInfo light-binning validator failed: "
            "check=gpu_report.d3d12.readback; "
            "source=fixture_contract.json; expected=.*True.*actual=.*False",
        ):
            verifier.verify_canonical_binning_gpu_report(
                transport,
                changed,
                "d3d12",
                runtime["audit_sha256"],
                Path("fixture_contract.json"),
            )

    def test_same_frame_canonical_buffer_failure_is_actionable(self) -> None:
        runtime, _ = self.load_current_contract()
        resources = runtime["canonical_combined_transport"][
            "same_frame_reflection_resources"
        ]
        evidence = resources["gpu_reports"]["d3d12"]
        report = json.loads(
            (verifier.LAB_ROOT / evidence["path"]).read_text(encoding="utf-8")
        )
        changed = copy.deepcopy(report)
        changed["canonicalBufferPreserved"] = False
        with self.assertRaisesRegex(
            AssertionError,
            "CharInfo light-binning validator failed: "
            "check=gpu_report.d3d12.canonical_buffer_preserved; "
            "source=fixture_contract.json; expected=True; actual=False",
        ):
            verifier.verify_canonical_reflection_frame_gpu_report(
                resources,
                changed,
                "d3d12",
                Path("fixture_contract.json"),
            )


class VisibilitySHConstantsContractTests(unittest.TestCase):
    @staticmethod
    def load_current_contract() -> tuple[dict[str, object], dict[str, object]]:
        contract = json.loads(
            verifier.BINDING_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        transport = contract["visibility_sh_resource_binding"][
            "constants_transport"
        ]
        audit = json.loads(
            (verifier.LAB_ROOT / transport["audit_path"]).read_text(
                encoding="utf-8"
            )
        )
        return transport, audit

    def test_current_visibility_sh_constants_audit_passes(self) -> None:
        transport, audit = self.load_current_contract()
        verifier.verify_visibility_sh_constants_audit(
            transport,
            audit,
            Path("fixture_contract.json"),
        )

    def test_selected_consumer_failure_is_actionable(self) -> None:
        transport, _ = self.load_current_contract()
        evidence = transport["gpu_reports"]["d3d12"]
        report = json.loads(
            (verifier.LAB_ROOT / evidence["path"]).read_text(encoding="utf-8")
        )
        changed = copy.deepcopy(report)
        changed["selectedDeferredWordsMatch"] = False
        with self.assertRaisesRegex(
            AssertionError,
            "VisibilitySHConstData validator failed: "
            "check=gpu_report.d3d12.publication; "
            "source=fixture_contract.json; expected=.*True.*actual=.*False",
        ):
            verifier.verify_visibility_sh_constants_gpu_report(
                transport,
                changed,
                "d3d12",
                Path("fixture_contract.json"),
            )

    def test_native_ab_params_failure_is_actionable(self) -> None:
        transport, audit = self.load_current_contract()
        changed = copy.deepcopy(audit)
        changed["fixedRows"]["abParams"]["wordBits"][1] = "0x00000000"
        with self.assertRaisesRegex(
            AssertionError,
            "VisibilitySHConstData validator failed: "
            "check=audit.ab_params_bits; source=fixture_contract.json; "
            "expected=.*0x3ea16095.*actual=.*0x00000000",
        ):
            verifier.verify_visibility_sh_constants_audit(
                transport,
                changed,
                Path("fixture_contract.json"),
            )

    def test_native_zero_fill_failure_is_actionable(self) -> None:
        transport, audit = self.load_current_contract()
        changed = copy.deepcopy(audit)
        changed["fullProducerInitialization"]["zeroRows"] = [5, 6]
        with self.assertRaisesRegex(
            AssertionError,
            "VisibilitySHConstData validator failed: "
            "check=audit.full_producer_initialization; "
            "source=fixture_contract.json; expected=.*5, 6, 7.*actual=.*5, 6",
        ):
            verifier.verify_visibility_sh_constants_audit(
                transport,
                changed,
                Path("fixture_contract.json"),
            )


class HdplsMatrixFormulaContractTests(unittest.TestCase):
    @staticmethod
    def load_current_contract() -> tuple[dict[str, object], dict[str, object]]:
        contract = json.loads(
            verifier.BINDING_CONTRACT_PATH.read_text(encoding="utf-8")
        )
        binding = next(
            row
            for row in contract["identified_unnamed_constant_buffer_roles"]
            if row["role"] == "HDPunctualLightCharacterShadowData"
        )
        native = binding["native_producer"]
        audit = json.loads(
            verifier.repo_path(native["audit_path"]).read_text(encoding="utf-8")
        )
        return native, audit

    def test_current_matrix_formula_contract_passes(self) -> None:
        native, audit = self.load_current_contract()
        verifier.verify_hdpls_matrix_formula_contract(
            native,
            audit,
            Path("fixture_contract.json"),
        )

    def test_direction_epsilon_failure_is_actionable(self) -> None:
        native, audit = self.load_current_contract()
        changed = copy.deepcopy(audit)
        changed["matrix_production"]["light_direction"][
            "direction_epsilon"
        ] = 0.001
        with self.assertRaisesRegex(
            AssertionError,
            "HDPLS matrix-production validator failed: "
            "check=matrix_production.light_direction; "
            "source=fixture_contract.json; expected=.*actual=.*0.001",
        ):
            verifier.verify_hdpls_matrix_formula_contract(
                native,
                changed,
                Path("fixture_contract.json"),
            )


class HdplsResourceLifecycleContractTests(unittest.TestCase):
    @staticmethod
    def load_current_contract() -> tuple[dict[str, object], dict[str, object]]:
        return HdplsMatrixFormulaContractTests.load_current_contract()

    def test_current_resource_lifecycle_contract_passes(self) -> None:
        native, audit = self.load_current_contract()
        verifier.verify_hdpls_resource_lifecycle_contract(
            native,
            audit,
            Path("fixture_contract.json"),
        )

    def test_screen_output_binding_failure_is_actionable(self) -> None:
        native, audit = self.load_current_contract()
        changed = copy.deepcopy(audit)
        changed["resource_lifecycle"]["screen_resolve"]["shader"][
            "global_output"
        ] = "HGShaderIDs._HDPLSTex"
        with self.assertRaisesRegex(
            AssertionError,
            "HDPLS resource-lifecycle validator failed: "
            "check=screen_resolve.shader; source=fixture_contract.json; "
            "expected=.*_HDPLSScreenSpaceShadowMask.*actual=.*_HDPLSTex",
        ):
            verifier.verify_hdpls_resource_lifecycle_contract(
                native,
                changed,
                Path("fixture_contract.json"),
            )

    def test_installed_ifix_target_count_failure_is_actionable(self) -> None:
        native, audit = self.load_current_contract()
        changed = copy.deepcopy(audit)
        changed["installed_ifix_state"]["persistent_target_count"] = 31
        with self.assertRaisesRegex(
            AssertionError,
            "HDPLS resource-lifecycle validator failed: "
            "check=installed_ifix_state; source=fixture_contract.json; "
            "expected=.*30.*actual=.*31",
        ):
            verifier.verify_hdpls_resource_lifecycle_contract(
                native,
                changed,
                Path("fixture_contract.json"),
            )


if __name__ == "__main__":
    unittest.main()
