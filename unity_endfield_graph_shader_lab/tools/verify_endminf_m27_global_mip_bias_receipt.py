#!/usr/bin/env python3
"""Verify a same-epoch M27 global-mip-bias producer receipt.

This verifier admits only source observations.  Captured constant-buffer values
may be checked as downstream validation, but can never stand in for the
physical-camera and dynamic-resolution inputs.
"""

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
REPO_ROOT = LAB_ROOT.parent
DEFAULT_CONTRACT = (
    REPO_ROOT
    / "reports/assets/character_recovery/"
    "endminf_m27_global_mip_bias_contract.json"
)
EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "c24495e51b406f03b03890c4788ee618ae022c991405be5d5b8b787cb775ae89"
)
EXPECTED_METADATA_SHA256 = (
    "0076743397acadf03d3b0064343a963c7c88863b8160526d397e4b3efb96f02e"
)
EXPECTED_RENDERER_PATH_ID = 59284134265994738
EXPECTED_VERTEX_SHA256 = (
    "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c"
)
EXPECTED_PIXEL_SHA256 = (
    "a6e069e2635fdc09c21c2ca5c1a34e3da142b5a6627dd3d49f131563715c724c"
)
EXPECTED_VERTEX_IDENTITY = 0xC0266E7FAC0046C1
EXPECTED_PIXEL_IDENTITY = 0xA6E069E2635FDC09
EXPECTED_INDEX_COUNT = 1080


class ReceiptError(RuntimeError):
    pass


def _load_builder() -> Any:
    path = Path(__file__).with_name(
        "build_endminf_m27_global_mip_bias_contract.py"
    )
    spec = importlib.util.spec_from_file_location("m27_mip_bias_contract", path)
    if spec is None or spec.loader is None:
        raise ReceiptError(f"unable to load contract builder: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptError(message)


def _require_int(value: Any, label: str, *, positive: bool = False) -> int:
    _require(type(value) is int, f"{label} must be an integer")
    if positive:
        _require(value > 0, f"{label} must be positive")
    return value


def _require_bits(value: Any, label: str) -> int:
    bits = _require_int(value, label)
    _require(0 <= bits <= 0xFFFFFFFF, f"{label} is not uint32")
    decoded = struct.unpack("<f", struct.pack("<I", bits))[0]
    _require(math.isfinite(decoded), f"{label} is non-finite")
    return bits


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", _f32(value)))[0]


def _float_from_bits(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value))[0]


def load_validated_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> tuple[dict[str, Any], str]:
    _require(contract_path.is_file(), f"missing static contract: {contract_path}")
    try:
        on_disk = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptError(f"invalid static contract: {exc}") from exc
    builder = _load_builder()
    try:
        rebuilt = builder.build_contract(gameassembly, metadata)
    except Exception as exc:
        raise ReceiptError(f"static contract native gate failed: {exc}") from exc
    _require(on_disk == rebuilt, "generated static contract drift")
    _require(
        rebuilt.get("sourceEquationClosed") is True
        and rebuilt.get("selectedValueSourceClosed") is False
        and rebuilt.get("safeToPopulateFromCapturedC26") is False,
        "static contract authority boundary drift",
    )
    return rebuilt, _sha256_bytes(_canonical_bytes(rebuilt))


def verify_receipt(
    receipt: dict[str, Any], contract_sha256: str
) -> dict[str, Any]:
    _require(
        receipt.get("schema")
        == "endfield.endminf-m27-global-mip-bias-receipt.v1",
        "receipt schema mismatch",
    )
    _require(receipt.get("complete") is True, "receipt is incomplete")
    _require(receipt.get("truncated") is False, "receipt is truncated")
    _require(
        _require_int(receipt.get("eventLossCount"), "eventLossCount") == 0,
        "receipt reports lost events",
    )
    _require(
        receipt.get("capturedConstantsUsedAsSource") is False,
        "captured constants cannot be used as source evidence",
    )
    _require(
        receipt.get("staticContractSha256") == contract_sha256,
        "static contract hash mismatch",
    )

    build = receipt.get("build")
    _require(isinstance(build, dict), "missing build identity")
    _require(
        build.get("gameAssemblySha256") == EXPECTED_GAME_ASSEMBLY_SHA256,
        "GameAssembly hash mismatch",
    )
    _require(
        build.get("globalMetadataSha256") == EXPECTED_METADATA_SHA256,
        "global-metadata hash mismatch",
    )

    draw = receipt.get("draw")
    _require(isinstance(draw, dict), "missing draw identity")
    _require(
        draw.get("rendererPathId") == EXPECTED_RENDERER_PATH_ID,
        "renderer PathID mismatch",
    )
    _require(
        draw.get("vertexShaderSha256") == EXPECTED_VERTEX_SHA256,
        "vertex shader identity mismatch",
    )
    _require(
        draw.get("pixelShaderSha256") == EXPECTED_PIXEL_SHA256,
        "pixel shader identity mismatch",
    )
    _require(
        draw.get("rendererIdentityAuthority")
        == "pinned-source-to-exact-shader-ia-draw-join",
        "renderer identity authority mismatch",
    )
    _require(
        _require_int(
            draw.get("observedVertexShaderIdentity"),
            "observedVertexShaderIdentity",
            positive=True,
        )
        == EXPECTED_VERTEX_IDENTITY,
        "observed vertex shader identity mismatch",
    )
    _require(
        _require_int(
            draw.get("observedPixelShaderIdentity"),
            "observedPixelShaderIdentity",
            positive=True,
        )
        == EXPECTED_PIXEL_IDENTITY,
        "observed pixel shader identity mismatch",
    )
    _require(
        _require_int(
            draw.get("observedIndexCount"),
            "observedIndexCount",
            positive=True,
        )
        == EXPECTED_INDEX_COUNT,
        "observed index count mismatch",
    )
    _require(
        _require_int(
            draw.get("observedInstanceCount"),
            "observedInstanceCount",
            positive=True,
        )
        == 1,
        "observed instance count mismatch",
    )
    _require(
        draw.get("observedIndexedInstanced") is True,
        "observed draw mode mismatch",
    )

    diagnostics = receipt.get("diagnostics")
    _require(isinstance(diagnostics, dict), "missing receipt diagnostics")
    _require(diagnostics.get("hooksInstalled") is True, "hooks were not installed")
    _require(
        diagnostics.get("callbacksQuiescent") is True,
        "observer callbacks were not quiescent",
    )
    for key in (
        "sourceObservations",
        "publicationObservations",
        "drawObservations",
    ):
        _require_int(diagnostics.get(key), f"diagnostics.{key}", positive=True)
    _require(
        _require_int(
            diagnostics.get("admittedJoinCount"),
            "diagnostics.admittedJoinCount",
        )
        == 1,
        "receipt does not contain exactly one admitted join",
    )
    for key in ("sourceAttemptFailures", "publicationAttemptFailures"):
        _require_int(diagnostics.get(key), f"diagnostics.{key}")
    for key in (
        "identityValidationRejections",
        "cameraSlotCapacityRejections",
        "candidateLockRejections",
        "ambiguousDrawJoins",
        "duplicateReceipts",
    ):
        _require(
            _require_int(diagnostics.get(key), f"diagnostics.{key}") == 0,
            f"receipt reports {key}",
        )

    identity = receipt.get("identity")
    _require(isinstance(identity, dict), "missing producer identities")
    producer_ids = []
    for key in (
        "hgCameraId",
        "additionalCameraDataId",
        "dynamicResolutionHandlerId",
    ):
        producer_ids.append(
            _require_int(identity.get(key), f"identity.{key}", positive=True)
        )
    _require(
        len(set(producer_ids)) == len(producer_ids),
        "producer identities are not distinct runtime objects",
    )
    _require(
        identity.get("changedWithinEpoch") is False,
        "producer identity changed within epoch",
    )

    ordering = receipt.get("ordering")
    _require(isinstance(ordering, dict), "missing ordering evidence")
    source_epoch = _require_int(
        ordering.get("sourceEpoch"), "sourceEpoch", positive=True
    )
    publish_epoch = _require_int(
        ordering.get("publicationEpoch"), "publicationEpoch", positive=True
    )
    draw_epoch = _require_int(
        ordering.get("drawEpoch"), "drawEpoch", positive=True
    )
    _require(
        source_epoch == publish_epoch == draw_epoch,
        "source, publication, and draw are not in one epoch",
    )
    source_sequence = _require_int(
        ordering.get("sourceSequence"), "sourceSequence", positive=True
    )
    publication_sequence = _require_int(
        ordering.get("publicationSequence"),
        "publicationSequence",
        positive=True,
    )
    draw_sequence = _require_int(
        ordering.get("drawSequence"), "drawSequence", positive=True
    )
    _require(
        source_sequence < publication_sequence < draw_sequence,
        "receipt ordering is not source < publication < draw",
    )

    values = receipt.get("values")
    _require(isinstance(values, dict), "missing producer values")
    material_bits = _require_bits(
        values.get("materialMipBiasBits"), "materialMipBiasBits"
    )
    _require(
        type(values.get("useMipBias")) is bool,
        "useMipBias must be a boolean",
    )
    _require(
        type(values.get("forceApply")) is bool,
        "forceApply must be a boolean",
    )
    input_width = _require_int(
        values.get("inputWidth"), "inputWidth", positive=True
    )
    output_width = _require_int(
        values.get("outputWidth"), "outputWidth", positive=True
    )
    dynamic_bits = _require_bits(
        values.get("dynamicTermBits"), "dynamicTermBits"
    )
    global_bits = _require_bits(
        values.get("globalMipBiasBits"), "globalMipBiasBits"
    )
    c26_x_bits = _require_bits(
        values.get("publishedC26XBits"), "publishedC26XBits"
    )
    c26_y_bits = _require_bits(
        values.get("publishedC26YBits"), "publishedC26YBits"
    )

    applies = values["useMipBias"] or values["forceApply"]
    expected_dynamic = (
        _f32(math.log(float(input_width) / float(output_width), 2.0))
        if applies
        else 0.0
    )
    _require(
        dynamic_bits == _bits(expected_dynamic),
        "dynamic term does not match the pinned CalculateMipBias equation",
    )
    expected_global = _f32(
        _float_from_bits(material_bits) + _float_from_bits(dynamic_bits)
    )
    _require(
        global_bits == _bits(expected_global),
        "global mip bias does not match the pinned HGCamera.Update addition",
    )
    _require(c26_x_bits == global_bits, "published c26.x does not match HGCamera")
    expected_pow2 = _f32(math.pow(2.0, _float_from_bits(global_bits)))
    _require(
        c26_y_bits == _bits(expected_pow2),
        "published c26.y does not match pow(2,c26.x)",
    )
    return {
        "schema": "endfield.endminf-m27-global-mip-bias-verification.v1",
        "status": "source_receipt_admitted",
        "staticContractSha256": contract_sha256,
        "sameEpoch": source_epoch,
        "rendererPathId": EXPECTED_RENDERER_PATH_ID,
        "sourceValues": {
            "materialMipBiasBits": material_bits,
            "useMipBias": values["useMipBias"],
            "forceApply": values["forceApply"],
            "inputWidth": input_width,
            "outputWidth": output_width,
            "dynamicTermBits": dynamic_bits,
            "globalMipBiasBits": global_bits,
        },
        "publishedC26Bits": [c26_x_bits, c26_y_bits],
        "canPopulatePhysicalCameraMipBiasSource": True,
        "presentationAuthority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        _contract, contract_sha256 = load_validated_contract(
            args.contract, args.gameassembly, args.metadata
        )
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        result = verify_receipt(receipt, contract_sha256)
    except (OSError, json.JSONDecodeError, ReceiptError) as exc:
        print(f"Endminf M27 global-mip-bias receipt failed: {exc}", file=sys.stderr)
        return 1
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
