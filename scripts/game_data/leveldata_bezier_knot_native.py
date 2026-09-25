"""Authenticate the selected BezierKnot formatter and native struct layout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets


SCHEMA = "endfield.leveldata-bezier-knot-native-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "leveldata_bezier_knot_native.json"


def validate_bezier_knot_native(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on build drift, changed formatter bytes or changed field offsets."""

    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"gate": gate, "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "validation_failed", "validationFailures": [{
            "gate": "read_contract", "expected": "reviewed JSON", "actual": str(exc)[:400],
        }]}
    if contract.get("schema") != SCHEMA:
        reject("schema", SCHEMA, contract.get("schema"))
    if contract.get("status") != "validated":
        reject("contract_status", "validated", contract.get("status"))

    expected_inputs = contract.get("nativeInputs") or {}
    root = Path(game_root) if game_root is not None else None
    native = check_installed_native_inputs(
        str(expected_inputs.get("GameAssembly.dll", "")),
        str(expected_inputs.get("global-metadata.dat", "")),
        gameassembly=root.parent / "GameAssembly.dll" if root is not None else None,
        metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root is not None else None,
    )
    result: dict[str, Any] = {
        "status": native.status,
        "contractSha256": hashlib.sha256(raw).hexdigest().upper(),
        "nativeInputs": {
            "GameAssembly.dll": native.gameassembly_sha256.upper(),
            "global-metadata.dat": native.metadata_sha256.upper(),
        },
        "nativeGateDetail": native.detail,
        "wireStride": None,
        "wireFields": None,
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "validationFailures": failures,
    }
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        return result

    unity_path = native.gameassembly.parent / "UnityPlayer.dll"
    unity_sha = sha256_file(unity_path).upper() if unity_path.is_file() else ""
    result["nativeInputs"]["UnityPlayer.dll"] = unity_sha
    if unity_sha != str(expected_inputs.get("UnityPlayer.dll", "")).upper():
        reject("unityplayer_sha256", expected_inputs.get("UnityPlayer.dll"), unity_sha)
    if failures:
        result["status"] = "validation_failed"
        return result

    try:
        image = NativeImage(native.gameassembly, native.metadata, label="bezier-knot")
        method = contract["formatterMethod"]
        image.validate_method_row(method)
        image.check_windows([contract["fastPathWindow"]])
        type_name = contract["structType"]
        type_rows = [row for row in image.metadata.types if image.metadata.type_full_name(row) == type_name]
        if len(type_rows) != 1:
            raise ValueError(f"struct-type-count={len(type_rows)}")
        offsets = runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, type_rows[0].index,
        )
        if offsets != contract["boxedFields"]:
            reject("boxed_field_offsets", contract["boxedFields"], offsets)
        wire_fields = contract["wireFields"]
        stride = contract["wireStride"]
        if (
            not isinstance(stride, int) or stride <= 0
            or stride != contract["fastPathWindow"]["wireStride"]
            or not isinstance(wire_fields, list)
            or len(wire_fields) != len(contract["boxedFields"])
            or [row[0] for row in wire_fields] != list(contract["boxedFields"])
            or any(
                not isinstance(row, list) or len(row) != 3
                or row[1] != contract["boxedFields"].get(row[0], -1) - 16
                or row[2] <= 0
                or row[1] + row[2] != (
                    wire_fields[index + 1][1] if index + 1 < len(wire_fields) else stride
                )
                for index, row in enumerate(wire_fields)
            )
            or sum(row[2] for row in wire_fields) != stride
        ):
            reject("wire_layout", "contiguous native fields through formatter stride", wire_fields)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        reject("selected_native_layout", "method, window and fields validated", str(exc)[:400])

    result["status"] = NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed"
    if not failures:
        result["wireStride"] = stride
        result["wireFields"] = wire_fields
    return result


__all__ = ["DEFAULT_CONTRACT", "validate_bezier_knot_native"]
