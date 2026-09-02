from __future__ import annotations

import importlib.util
import json
import struct
import sys
import unittest
from copy import deepcopy
from pathlib import Path


TOOLS = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    path = TOOLS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUILDER = _load(
    "test_m27_mip_bias_builder",
    "build_endminf_m27_global_mip_bias_contract.py",
)
VERIFIER = _load(
    "test_m27_mip_bias_verifier",
    "verify_endminf_m27_global_mip_bias_receipt.py",
)


def _bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _receipt(contract_sha256: str) -> dict:
    return {
        "schema": "endfield.endminf-m27-global-mip-bias-receipt.v1",
        "complete": True,
        "truncated": False,
        "eventLossCount": 0,
        "capturedConstantsUsedAsSource": False,
        "staticContractSha256": contract_sha256,
        "build": {
            "gameAssemblySha256": VERIFIER.EXPECTED_GAME_ASSEMBLY_SHA256,
            "globalMetadataSha256": VERIFIER.EXPECTED_METADATA_SHA256,
        },
        "draw": {
            "rendererPathId": VERIFIER.EXPECTED_RENDERER_PATH_ID,
            "rendererIdentityAuthority": (
                "pinned-source-to-exact-shader-ia-draw-join"
            ),
            "vertexShaderSha256": VERIFIER.EXPECTED_VERTEX_SHA256,
            "pixelShaderSha256": VERIFIER.EXPECTED_PIXEL_SHA256,
            "observedVertexShaderIdentity": (
                VERIFIER.EXPECTED_VERTEX_IDENTITY
            ),
            "observedPixelShaderIdentity": VERIFIER.EXPECTED_PIXEL_IDENTITY,
            "observedIndexCount": VERIFIER.EXPECTED_INDEX_COUNT,
            "observedInstanceCount": 1,
            "observedIndexedInstanced": True,
        },
        "diagnostics": {
            "hooksInstalled": True,
            "callbacksQuiescent": True,
            "sourceObservations": 1,
            "sourceAttemptFailures": 0,
            "publicationObservations": 1,
            "publicationAttemptFailures": 0,
            "identityValidationRejections": 0,
            "drawObservations": 1,
            "admittedJoinCount": 1,
            "cameraSlotCapacityRejections": 0,
            "candidateLockRejections": 0,
            "ambiguousDrawJoins": 0,
            "duplicateReceipts": 0,
        },
        "identity": {
            "hgCameraId": 0x1000,
            "additionalCameraDataId": 0x2000,
            "dynamicResolutionHandlerId": 0x3000,
            "changedWithinEpoch": False,
        },
        "ordering": {
            "sourceEpoch": 27,
            "publicationEpoch": 27,
            "drawEpoch": 27,
            "sourceSequence": 10,
            "publicationSequence": 11,
            "drawSequence": 12,
        },
        "values": {
            "materialMipBiasBits": _bits(0.0),
            "useMipBias": True,
            "forceApply": False,
            "inputWidth": 1920,
            "outputWidth": 3840,
            "dynamicTermBits": _bits(-1.0),
            "globalMipBiasBits": _bits(-1.0),
            "publishedC26XBits": _bits(-1.0),
            "publishedC26YBits": _bits(0.5),
        },
    }


class EndminfM27GlobalMipBiasContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = BUILDER.build_contract()
        cls.contract_sha256 = VERIFIER._sha256_bytes(
            VERIFIER._canonical_bytes(cls.contract)
        )

    def test_static_contract_closes_equation_not_selected_lifecycle(self) -> None:
        self.assertTrue(self.contract["sourceEquationClosed"])
        self.assertFalse(self.contract["selectedValueSourceClosed"])
        self.assertFalse(self.contract["safeToPopulateFromCapturedC26"])
        self.assertFalse(
            self.contract["decision"][
                "canSourceCloseSelectedC26WithoutRuntimeReceipt"
            ]
        )
        self.assertFalse(self.contract["decision"]["presentationAuthority"])
        self.assertEqual(
            self.contract["sourceEquation"]["c26x"],
            "materialTerm + dynamicTerm",
        )

    def test_exact_same_epoch_source_receipt_is_admitted(self) -> None:
        result = VERIFIER.verify_receipt(
            _receipt(self.contract_sha256), self.contract_sha256
        )
        self.assertEqual(result["status"], "source_receipt_admitted")
        self.assertTrue(result["canPopulatePhysicalCameraMipBiasSource"])
        self.assertFalse(result["presentationAuthority"])

    def test_nonhistorical_source_value_is_admitted(self) -> None:
        receipt = _receipt(self.contract_sha256)
        receipt["diagnostics"]["publicationAttemptFailures"] = 3
        receipt["values"].update(
            {
                "inputWidth": 1920,
                "outputWidth": 1920,
                "dynamicTermBits": _bits(0.0),
                "globalMipBiasBits": _bits(0.0),
                "publishedC26XBits": _bits(0.0),
                "publishedC26YBits": _bits(1.0),
            }
        )
        result = VERIFIER.verify_receipt(receipt, self.contract_sha256)
        self.assertEqual(result["publishedC26Bits"], [_bits(0.0), _bits(1.0)])

    def test_captured_constant_source_is_rejected(self) -> None:
        receipt = _receipt(self.contract_sha256)
        receipt["capturedConstantsUsedAsSource"] = True
        with self.assertRaisesRegex(
            VERIFIER.ReceiptError, "captured constants cannot"
        ):
            VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_wrong_dynamic_term_is_rejected(self) -> None:
        receipt = _receipt(self.contract_sha256)
        receipt["values"]["dynamicTermBits"] = _bits(0.0)
        with self.assertRaisesRegex(VERIFIER.ReceiptError, "dynamic term"):
            VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_cross_epoch_join_is_rejected(self) -> None:
        receipt = _receipt(self.contract_sha256)
        receipt["ordering"]["drawEpoch"] += 1
        with self.assertRaisesRegex(VERIFIER.ReceiptError, "not in one epoch"):
            VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_non_distinct_producer_identities_are_rejected(self) -> None:
        receipt = _receipt(self.contract_sha256)
        receipt["identity"]["dynamicResolutionHandlerId"] = receipt[
            "identity"
        ]["hgCameraId"]
        with self.assertRaisesRegex(
            VERIFIER.ReceiptError, "not distinct runtime objects"
        ):
            VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_nonpositive_epoch_or_sequence_is_rejected(self) -> None:
        for key in ("sourceEpoch", "sourceSequence"):
            with self.subTest(key=key):
                receipt = _receipt(self.contract_sha256)
                receipt["ordering"][key] = 0
                with self.assertRaisesRegex(VERIFIER.ReceiptError, "positive"):
                    VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_observed_draw_identity_and_mode_are_required(self) -> None:
        mutations = (
            ("observedVertexShaderIdentity", 1, "observed vertex shader"),
            ("observedPixelShaderIdentity", 1, "observed pixel shader"),
            ("observedIndexCount", 72, "observed index count"),
            ("observedInstanceCount", 2, "observed instance count"),
            ("observedIndexedInstanced", False, "observed draw mode"),
        )
        for key, value, expected in mutations:
            with self.subTest(key=key):
                receipt = _receipt(self.contract_sha256)
                receipt["draw"][key] = value
                with self.assertRaisesRegex(VERIFIER.ReceiptError, expected):
                    VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_renderer_authority_and_diagnostics_are_required(self) -> None:
        receipt = _receipt(self.contract_sha256)
        receipt["draw"]["rendererIdentityAuthority"] = "asserted"
        with self.assertRaisesRegex(VERIFIER.ReceiptError, "authority"):
            VERIFIER.verify_receipt(receipt, self.contract_sha256)

        for key, value, expected in (
            ("callbacksQuiescent", False, "not quiescent"),
            ("ambiguousDrawJoins", 1, "ambiguousDrawJoins"),
            ("admittedJoinCount", 2, "exactly one"),
        ):
            with self.subTest(key=key):
                receipt = _receipt(self.contract_sha256)
                receipt["diagnostics"][key] = value
                with self.assertRaisesRegex(VERIFIER.ReceiptError, expected):
                    VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_lost_or_changed_identity_receipts_are_rejected(self) -> None:
        for mutation, expected in (
            (("eventLossCount",), "lost events"),
            (("identity", "changedWithinEpoch"), "identity changed"),
        ):
            with self.subTest(mutation=mutation):
                receipt = deepcopy(_receipt(self.contract_sha256))
                target = receipt
                for key in mutation[:-1]:
                    target = target[key]
                target[mutation[-1]] = 1 if len(mutation) == 1 else True
                with self.assertRaisesRegex(VERIFIER.ReceiptError, expected):
                    VERIFIER.verify_receipt(receipt, self.contract_sha256)

    def test_static_contract_file_matches_exact_native_rebuild(self) -> None:
        on_disk = json.loads(BUILDER.DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(on_disk, self.contract)


if __name__ == "__main__":
    unittest.main()
