from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "build_endminf_m27_global_mip_bias_source.py"
)
SPEC = importlib.util.spec_from_file_location("m27_c26_promoter_tested", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def admitted_result() -> dict:
    return {
        "schema": MODULE.SESSION_SCHEMA,
        "status": "inventoried_source_receipt_admitted",
        "session": "20260902T120000Z",
        "receiptSha256": "1" * 64,
        "runtimePackageSha256": "2" * 64,
        "sourceVerification": {
            "schema": MODULE.SOURCE_SCHEMA,
            "status": "source_receipt_admitted",
            "staticContractSha256": MODULE.EXPECTED_STATIC_CONTRACT_SHA256,
            "rendererPathId": MODULE.EXPECTED_RENDERER_PATH_ID,
            "sourceValues": {
                "materialMipBiasBits": 0x00000000,
                "dynamicTermBits": 0xBF800000,
                "globalMipBiasBits": 0xBF800000,
            },
            "publishedC26Bits": [0xBF800000, 0x3F000000],
            "canPopulatePhysicalCameraMipBiasSource": True,
            "presentationAuthority": False,
        },
        "presentationAuthority": False,
    }


class M27GlobalMipBiasPromotionTests(unittest.TestCase):
    def test_exact_admitted_result_builds_minimal_source(self) -> None:
        result = admitted_result()
        payload = MODULE.build_payload(result)
        self.assertEqual(payload["schema"], MODULE.PAYLOAD_SCHEMA)
        self.assertEqual(payload["status"], MODULE.PAYLOAD_STATUS)
        self.assertEqual(payload["globalMipBiasBits"], "bf800000")
        self.assertEqual(payload["publishedC26YBits"], "3f000000")
        self.assertFalse(payload["presentationAuthority"])
        self.assertEqual(
            payload["sourceReportSha256"],
            hashlib.sha256(MODULE._canonical_bytes(result)).hexdigest(),
        )

    def test_authority_and_identity_drift_fail_closed(self) -> None:
        mutations = (
            (("status",), "rejected", "not admitted"),
            (("presentationAuthority",), True, "non-authoritative"),
            (("receiptSha256",), "x" * 64, "SHA-256"),
            (("sourceVerification", "status"), "rejected", "source rejected"),
            (
                ("sourceVerification", "rendererPathId"),
                1,
                "PathID",
            ),
            (
                ("sourceVerification", "staticContractSha256"),
                "0" * 64,
                "static contract",
            ),
            (
                (
                    "sourceVerification",
                    "canPopulatePhysicalCameraMipBiasSource",
                ),
                False,
                "does not authorize",
            ),
        )
        for path, value, expected in mutations:
            with self.subTest(path=path):
                result = deepcopy(admitted_result())
                target = result
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaisesRegex(MODULE.PromotionError, expected):
                    MODULE.build_payload(result)

    def test_wrong_or_malformed_c26_bits_fail_closed(self) -> None:
        mutations = (
            (("sourceValues", "globalMipBiasBits"), 0, "differs"),
            (
                ("sourceValues", "materialMipBiasBits"),
                0x3F800000,
                "material plus dynamic",
            ),
            (("publishedC26Bits",), [0xBF800000], "two words"),
            (
                ("publishedC26Bits",),
                [0xBF800000, 0x3F800000],
                "differs from pow2",
            ),
            (("sourceValues", "dynamicTermBits"), "bf800000", "integer"),
        )
        for path, value, expected in mutations:
            with self.subTest(path=path):
                result = admitted_result()
                source = result["sourceVerification"]
                target = source
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaisesRegex(MODULE.PromotionError, expected):
                    MODULE.build_payload(result)

    def test_publish_and_check_are_canonical_and_fail_on_drift(self) -> None:
        payload = MODULE.build_payload(admitted_result())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "source.json"
            MODULE.publish_payload(payload, output, check=False)
            MODULE.publish_payload(payload, output, check=True)
            parsed = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(parsed, payload)
            output.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.PromotionError, "drift"):
                MODULE.publish_payload(payload, output, check=True)

    def test_cli_missing_raw_session_fails_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "source.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing M27 mip-bias receipt", completed.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
