"""Fail-closed validator for the selected-build animation-curve contract."""

from __future__ import annotations

from scripts.game_data.contracts import CONTRACTS_DIR
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
    sha256_file,
)


SCHEMA = "endfield.animation-curve-native-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "animation_curve_native.json"
CONTRACT_SHA256 = "6CD01647D099CA52A8398F9DDB6EAB1753634D4CA7333C693D8EECF3B7BE1428"


def _pe_file_offset(image: bytes, rva: int, size: int) -> int:
    if rva < 0 or size <= 0 or len(image) < 0x40:
        raise ValueError(f"invalid PE range rva=0x{rva:x} size={size}")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    if pe_offset + 24 > len(image) or image[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_size
    for index in range(section_count):
        row = section_table + index * 40
        if row + 40 > len(image):
            raise ValueError(f"truncated PE section table at index {index}")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", image, row + 8
        )
        if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
            delta = rva - virtual_address
            if delta + size > raw_size or raw_pointer + delta + size > len(image):
                raise ValueError(f"PE range crosses raw section at index {index}")
            return raw_pointer + delta
    raise ValueError(f"RVA 0x{rva:x} is outside PE sections")


def validate_animation_curve_native_contract(
    *,
    contract_path: Path = DEFAULT_CONTRACT,
    game_root: Path | None = None,
) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"gate": gate, "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "status": "validation_failed",
            "validationFailures": [{
                "gate": "read_valid_contract", "expected": True, "actual": str(exc)[:400]
            }],
        }
    actual_contract_sha = hashlib.sha256(raw).hexdigest().upper()
    if actual_contract_sha != CONTRACT_SHA256:
        reject("contract_sha256", CONTRACT_SHA256, actual_contract_sha)
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
        metadata=(
            root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
            if root is not None else None
        ),
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_gameassembly_and_metadata",
            NATIVE_EVIDENCE_VALIDATED,
            {"status": native.status, "detail": native.detail},
        )

    unity_path = native.gameassembly.parent / "UnityPlayer.dll"
    actual_unity_sha = sha256_file(unity_path) if unity_path.is_file() else ""
    expected_unity_sha = str(expected_inputs.get("UnityPlayer.dll", "")).casefold()
    if actual_unity_sha.casefold() != expected_unity_sha:
        reject("unityplayer_sha256", expected_unity_sha, actual_unity_sha)

    if native.gameassembly.is_file() and native.status == NATIVE_EVIDENCE_VALIDATED:
        image = native.gameassembly.read_bytes()
        windows = [
            ("fKeyframe", (contract.get("fKeyframe") or {}).get("codeWindow") or {}),
            ("fAnimationCurve", (contract.get("fAnimationCurve") or {}).get("codeWindow") or {}),
            (
                "fAnimationCurve.keysRepresentation",
                ((contract.get("fAnimationCurve") or {}).get("keysRepresentation") or {}).get("codeWindow") or {},
            ),
        ]
        for owner, window in windows:
            try:
                rva = int(str(window["rva"]), 0)
                length = int(window["length"])
                offset = _pe_file_offset(image, rva, length)
                actual = hashlib.sha256(image[offset:offset + length]).hexdigest()
                expected = str(window["sha256"]).casefold()
                if actual.casefold() != expected:
                    reject(f"{owner}.code_window_sha256", expected, actual)
            except (KeyError, TypeError, ValueError) as exc:
                reject(f"{owner}.code_window", "valid bounded PE window", str(exc))

    return {
        "status": NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed",
        "contractSha256": actual_contract_sha,
        "gameAssemblySha256": native.gameassembly_sha256.upper(),
        "metadataSha256": native.metadata_sha256.upper(),
        "unityPlayerSha256": actual_unity_sha.upper(),
        "fKeyframe": contract.get("fKeyframe") if not failures else None,
        "fAnimationCurve": contract.get("fAnimationCurve") if not failures else None,
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "validationFailures": failures,
    }


__all__ = ["DEFAULT_CONTRACT", "validate_animation_curve_native_contract"]
