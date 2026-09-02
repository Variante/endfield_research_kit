#!/usr/bin/env python3
"""Promote an authenticated M27 mip-bias session into a Unity source asset."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Resources/EndfieldRecoveredM27/"
    "endminf_m27_global_mip_bias_source.json"
)
PAYLOAD_SCHEMA = "endfield.endminf-m27-global-mip-bias-unity-source.v1"
PAYLOAD_STATUS = "source_authenticated_for_c26_only"
SESSION_SCHEMA = (
    "endfield.endminf-m27-global-mip-bias-session-verification.v1"
)
SOURCE_SCHEMA = "endfield.endminf-m27-global-mip-bias-verification.v1"
EXPECTED_RENDERER_PATH_ID = 59284134265994738
EXPECTED_STATIC_CONTRACT_SHA256 = (
    "01d703a635fa1b2f2cf463cc78c501bab2e1e97d93444605fb82be62f9f5d0d9"
)
EXPECTED_GLOBAL_MIP_BIAS_BITS = 0xBF800000
EXPECTED_GLOBAL_MIP_BIAS_POW2_BITS = 0x3F000000


class PromotionError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PromotionError(message)


def _require_sha256(value: Any, label: str) -> str:
    _require(isinstance(value, str), f"{label} must be a string")
    _require(
        len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value),
        f"{label} must be lowercase SHA-256 hex",
    )
    return value


def _require_bits(value: Any, label: str) -> int:
    _require(type(value) is int, f"{label} must be an integer")
    _require(0 <= value <= 0xFFFFFFFF, f"{label} must be uint32")
    return value


def _canonical_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _float_from_bits(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value))[0]


def _float_bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _load_session_verifier() -> Any:
    path = Path(__file__).with_name(
        "verify_endminf_m27_global_mip_bias_session.py"
    )
    spec = importlib.util.spec_from_file_location(
        "m27_mip_bias_session_promoter_verifier", path
    )
    if spec is None or spec.loader is None:
        raise PromotionError(f"unable to load session verifier: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_payload(result: dict[str, Any]) -> dict[str, Any]:
    _require(isinstance(result, dict), "session verification must be an object")
    _require(result.get("schema") == SESSION_SCHEMA, "session schema mismatch")
    _require(
        result.get("status") == "inventoried_source_receipt_admitted",
        "session receipt was not admitted",
    )
    session = result.get("session")
    _require(isinstance(session, str) and session, "source session is missing")
    receipt_sha256 = _require_sha256(
        result.get("receiptSha256"), "receiptSha256"
    )
    runtime_sha256 = _require_sha256(
        result.get("runtimePackageSha256"), "runtimePackageSha256"
    )
    _require(
        result.get("presentationAuthority") is False,
        "session result must remain non-authoritative for presentation",
    )

    source = result.get("sourceVerification")
    _require(isinstance(source, dict), "source verification is missing")
    _require(source.get("schema") == SOURCE_SCHEMA, "source schema mismatch")
    _require(source.get("status") == "source_receipt_admitted", "source rejected")
    static_sha256 = _require_sha256(
        source.get("staticContractSha256"), "staticContractSha256"
    )
    _require(
        static_sha256 == EXPECTED_STATIC_CONTRACT_SHA256,
        "static contract hash mismatch",
    )
    _require(
        source.get("rendererPathId") == EXPECTED_RENDERER_PATH_ID,
        "renderer PathID mismatch",
    )
    _require(
        source.get("canPopulatePhysicalCameraMipBiasSource") is True,
        "source does not authorize c26 population",
    )
    _require(
        source.get("presentationAuthority") is False,
        "source result must remain non-authoritative for presentation",
    )
    values = source.get("sourceValues")
    _require(isinstance(values, dict), "source values are missing")
    material_bits = _require_bits(
        values.get("materialMipBiasBits"), "materialMipBiasBits"
    )
    dynamic_bits = _require_bits(
        values.get("dynamicTermBits"), "dynamicTermBits"
    )
    global_bits = _require_bits(
        values.get("globalMipBiasBits"), "globalMipBiasBits"
    )
    published = source.get("publishedC26Bits")
    _require(
        isinstance(published, list) and len(published) == 2,
        "publishedC26Bits must contain two words",
    )
    published_x = _require_bits(published[0], "publishedC26Bits[0]")
    published_y = _require_bits(published[1], "publishedC26Bits[1]")
    _require(global_bits == published_x, "published c26.x differs from source")
    material = _float_from_bits(material_bits)
    dynamic_term = _float_from_bits(dynamic_bits)
    global_mip_bias = _float_from_bits(global_bits)
    published_pow2 = _float_from_bits(published_y)
    _require(
        all(
            math.isfinite(value)
            for value in (
                material,
                dynamic_term,
                global_mip_bias,
                published_pow2,
            )
        ),
        "source c26 equation contains a non-finite value",
    )
    _require(
        _float_bits(material + dynamic_term) == global_bits,
        "material plus dynamic term differs from global mip bias",
    )
    _require(
        _float_bits(2.0**global_mip_bias) == published_y,
        "published c26.y differs from pow2(global mip bias)",
    )
    _require(
        global_bits == EXPECTED_GLOBAL_MIP_BIAS_BITS
        and published_y == EXPECTED_GLOBAL_MIP_BIAS_POW2_BITS,
        "source does not establish selected c26=(-1,0.5)",
    )

    source_report_sha256 = hashlib.sha256(_canonical_bytes(result)).hexdigest()
    return {
        "schema": PAYLOAD_SCHEMA,
        "status": PAYLOAD_STATUS,
        "sourceSession": session,
        "sourceReportSha256": source_report_sha256,
        "receiptSha256": receipt_sha256,
        "runtimePackageSha256": runtime_sha256,
        "staticContractSha256": static_sha256,
        "rendererPathId": str(EXPECTED_RENDERER_PATH_ID),
        "materialMipBiasBits": f"{material_bits:08x}",
        "dynamicTermBits": f"{dynamic_bits:08x}",
        "globalMipBiasBits": f"{global_bits:08x}",
        "publishedC26YBits": f"{published_y:08x}",
        "canPopulatePhysicalCameraMipBiasSource": True,
        "presentationAuthority": False,
    }


def publish_payload(
    payload: dict[str, Any], output: Path, *, check: bool
) -> None:
    serialized = _canonical_bytes(payload)
    if check:
        _require(output.is_file(), f"missing generated Unity source: {output}")
        _require(
            output.read_bytes() == serialized,
            f"generated Unity source drift: {output}",
        )
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(serialized)
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_root", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        verifier = _load_session_verifier()
        result = verifier.verify_session(
            args.session_root,
            contract=args.contract,
            gameassembly=args.gameassembly,
            metadata=args.metadata,
        )
        payload = build_payload(result)
        publish_payload(payload, args.output, check=args.check)
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        PromotionError,
        RuntimeError,
    ) as exc:
        print(f"Endminf M27 c26 Unity promotion failed: {exc}", file=sys.stderr)
        return 1
    action = "check passed" if args.check else "source promoted"
    print(f"Endminf M27 c26 Unity {action}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
