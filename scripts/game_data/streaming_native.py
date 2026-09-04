"""Fail-closed validation for the selected-build Streaming field-2 layout."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs


SCHEMA = "endfield.streaming-field2-native-contract.v3"
DEFAULT_CONTRACT = Path(__file__).with_name("streaming_field2_native.json")
# Updated only after the reviewed JSON contract is finalized.
CONTRACT_SHA256 = "C26E27E77F1102F177AA1C2DF6F27FD46A191665FBE61DF4058333ECF5D633BC"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _pe_file_offset(image: bytes, rva: int) -> int:
    if len(image) < 0x40:
        raise ValueError(f"PE image too short: expected at least 64, actual {len(image)}")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    if pe_offset + 24 > len(image) or image[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError(f"invalid PE signature at expected file offset {pe_offset}")
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_size
    for index in range(section_count):
        position = section_table + index * 40
        if position + 40 > len(image):
            raise ValueError(
                f"truncated PE section {index}: expected end {position + 40}, actual EOF {len(image)}"
            )
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", image, position + 8
        )
        if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
            delta = rva - virtual_address
            if delta >= raw_size:
                raise ValueError(
                    f"RVA 0x{rva:X} lies in virtual-only bytes of PE section {index}"
                )
            return raw_pointer + delta
    raise ValueError(f"RVA 0x{rva:X} is outside all PE sections")


def validate_streaming_field2_native_contract(
    *,
    contract_path: Path = DEFAULT_CONTRACT,
    game_root: Path | None = None,
) -> dict[str, Any]:
    """Revalidate every native byte range supporting the row representation."""

    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"gate": gate, "expected": expected, "actual": actual})

    try:
        raw_contract = Path(contract_path).read_bytes()
        contract = json.loads(raw_contract.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "status": "validation_failed",
            "validationFailures": [
                {"gate": "read_valid_contract", "expected": True, "actual": str(exc)[:400]}
            ],
        }
    actual_contract_sha256 = _sha256_bytes(raw_contract)
    if actual_contract_sha256 != CONTRACT_SHA256:
        reject("contract_sha256", CONTRACT_SHA256, actual_contract_sha256)
    if contract.get("schema") != SCHEMA:
        reject("schema", SCHEMA, contract.get("schema"))
    if contract.get("status") != "validated":
        reject("contract_status", "validated", contract.get("status"))

    expected_inputs = contract.get("nativeInputs") or {}
    root = Path(game_root) if game_root is not None else None
    gameassembly = root.parent / "GameAssembly.dll" if root is not None else None
    metadata = (
        root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
        if root is not None
        else None
    )
    native = check_installed_native_inputs(
        str(expected_inputs.get("gameAssemblySha256", "")),
        str(expected_inputs.get("metadataSha256", "")),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_gameassembly_and_metadata",
            NATIVE_EVIDENCE_VALIDATED,
            {"status": native.status, "detail": native.detail},
        )

    unity_player = native.gameassembly.parent / "UnityPlayer.dll"
    unity_image = b""
    try:
        actual_unity_sha256 = _sha256_file(unity_player)
        unity_image = unity_player.read_bytes()
    except OSError as exc:
        actual_unity_sha256 = f"unreadable: {exc}"
    expected_unity_sha256 = str(expected_inputs.get("unityPlayerSha256", "")).upper()
    if actual_unity_sha256 != expected_unity_sha256:
        reject("unityplayer_sha256", expected_unity_sha256, actual_unity_sha256)

    if unity_image:
        for row in contract.get("unityPlayerRanges") or []:
            role = str(row.get("role", "unknown"))
            try:
                rva = int(row["rva"])
                recorded_offset = int(row["fileOffset"])
                size = int(row["size"])
                actual_offset = _pe_file_offset(unity_image, rva)
                if actual_offset != recorded_offset:
                    reject(f"{role}.file_offset", recorded_offset, actual_offset)
                body = unity_image[actual_offset : actual_offset + size]
                if len(body) != size:
                    reject(f"{role}.body_size", size, len(body))
                    continue
                expected_hash = str(row.get("bodySha256", "")).upper()
                actual_hash = _sha256_bytes(body)
                if actual_hash != expected_hash:
                    reject(f"{role}.body_sha256", expected_hash, actual_hash)
                expected_entry = bytes.fromhex(str(row.get("entryBytesHex", "")))
                if body[: len(expected_entry)] != expected_entry:
                    reject(
                        f"{role}.entry_bytes",
                        expected_entry.hex().upper(),
                        body[: len(expected_entry)].hex().upper(),
                    )
            except (KeyError, TypeError, ValueError) as exc:
                reject(f"{role}.byte_range", "valid bounded PE range", str(exc))

        observation = contract.get("consumerObservations") or {}
        try:
            diagnostic = str(observation["diagnosticUtf8"]).encode("utf-8") + b"\0"
            offset = _pe_file_offset(unity_image, int(observation["diagnosticRva"]))
            actual = unity_image[offset : offset + len(diagnostic)]
            if actual != diagnostic:
                reject(
                    "consumer_diagnostic_utf8",
                    diagnostic.hex().upper(),
                    actual.hex().upper(),
                )
        except (KeyError, TypeError, ValueError) as exc:
            reject("consumer_diagnostic", "valid bounded UTF-8 diagnostic", str(exc))

        for row in contract.get("utf8Strings") or []:
            role = str(row.get("role", "unknown"))
            try:
                expected_text = str(row["text"]).encode("utf-8") + b"\0"
                offset = _pe_file_offset(unity_image, int(row["rva"]))
                actual_text = unity_image[offset : offset + len(expected_text)]
                if actual_text != expected_text:
                    reject(
                        f"{role}.utf8",
                        expected_text.hex().upper(),
                        actual_text.hex().upper(),
                    )
            except (KeyError, TypeError, ValueError) as exc:
                reject(f"{role}.utf8", "valid bounded UTF-8 string", str(exc))

    status = NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed"
    return {
        "status": status,
        "nativeMappingId": contract.get("nativeMappingId"),
        "contractSha256": actual_contract_sha256,
        "gameAssemblySha256": native.gameassembly_sha256.upper(),
        "metadataSha256": native.metadata_sha256.upper(),
        "unityPlayerSha256": actual_unity_sha256,
        "rowLayout": contract.get("rowLayout"),
        "consumerObservations": contract.get("consumerObservations"),
        "carrierObservations": contract.get("carrierObservations"),
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "validationFailures": failures,
    }


__all__ = ["validate_streaming_field2_native_contract", "DEFAULT_CONTRACT"]
