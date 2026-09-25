"""Fail-closed validation for the selected-build Streaming field-2 layout."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.common import sha256_file_upper as _sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR


SCHEMA = "endfield.streaming-field2-native-contract.v10"
DEFAULT_CONTRACT = CONTRACTS_DIR / "streaming_field2_native.json"
# Updated only after the reviewed JSON contract is finalized.


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()



def _pe_file_offset(image: bytes, rva: int, *, size: int = 1) -> int:
    if rva < 0 or size <= 0:
        raise ValueError(f"PE range RVA {rva}: expected nonnegative RVA and positive size, actual size {size}")
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
            if delta + size > raw_size:
                raise ValueError(
                    f"RVA 0x{rva:X} size {size}: expected section {index} raw end <= {raw_size}, actual {delta + size} (virtual-only or crossing section)"
                )
            return raw_pointer + delta
    raise ValueError(f"RVA 0x{rva:X} is outside all PE sections")


def _bounded_pe_range(image: bytes, rva: int, size: int) -> tuple[int, bytes]:
    """Reject invalid or non-contiguous mapped spans before slicing evidence."""
    offset = _pe_file_offset(image, rva, size=size)
    end = offset + size
    if end > len(image):
        raise ValueError(f"PE range RVA 0x{rva:X} file offset {offset}: expected end <= {len(image)}, actual {end}")
    return offset, image[offset:end]


def _pe_image_base(image: bytes) -> int:
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    optional = pe_offset + 24
    if struct.unpack_from("<H", image, optional)[0] != 0x20B:
        raise ValueError("expected PE32+ image")
    return struct.unpack_from("<Q", image, optional + 24)[0]


def _literal_rel32_calls_to(image: bytes, target_rva: int) -> list[int]:
    """Over-approximate literal calls in raw executable sections."""
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    section_table = pe_offset + 24 + struct.unpack_from("<H", image, pe_offset + 20)[0]
    result: list[int] = []
    for index in range(section_count):
        header = section_table + index * 40
        virtual_address, raw_size, raw_pointer = (
            struct.unpack_from("<I", image, header + 12)[0],
            struct.unpack_from("<I", image, header + 16)[0],
            struct.unpack_from("<I", image, header + 20)[0],
        )
        characteristics = struct.unpack_from("<I", image, header + 36)[0]
        if not characteristics & 0x20000000:
            continue
        body = image[raw_pointer : raw_pointer + raw_size]
        cursor = 0
        while True:
            cursor = body.find(b"\xE8", cursor)
            if cursor < 0 or cursor + 5 > len(body):
                break
            site = virtual_address + cursor
            if site + 5 + struct.unpack_from("<i", body, cursor + 1)[0] == target_rva:
                result.append(site)
            cursor += 1
    return sorted(result)


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
                actual_offset, body = _bounded_pe_range(unity_image, rva, size)
                if actual_offset != recorded_offset:
                    reject(f"{role}.file_offset", recorded_offset, actual_offset)
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

        candidate = contract.get("groupComponentNameCandidate") or {}
        try:
            base = _pe_image_base(unity_image)
            expected_base = int(candidate["unityPlayerImageBase"], 0)
            if base != expected_base:
                reject("component_name_candidate.image_base", hex(expected_base), hex(base))
            for row in candidate["icallBindings"]:
                role = str(row["name"])
                for kind in ("name", "function"):
                    pointer_rva = int(row[f"{kind}PointerRva"], 0)
                    target_rva = int(row[f"{kind}Rva"], 0)
                    pointer_offset = _pe_file_offset(unity_image, pointer_rva, size=8)
                    actual = struct.unpack_from("<Q", unity_image, pointer_offset)[0]
                    expected = base + target_rva
                    if actual != expected:
                        reject(f"{role}.{kind}_pointer", hex(expected), hex(actual))
            expected_calls = sorted(int(row, 0) for row in candidate["literalRel32CallSites"])
            actual_calls = _literal_rel32_calls_to(
                unity_image, int(candidate["prefixMaskHelperRva"], 0)
            )
            if actual_calls != expected_calls:
                reject(
                    "component_name_candidate.literal_rel32_calls",
                    [hex(row) for row in expected_calls],
                    [hex(row) for row in actual_calls[:20]],
                )
        except (KeyError, TypeError, ValueError, struct.error) as exc:
            reject("component_name_candidate.native", "valid selected binding and call census", str(exc))

        if native.status == NATIVE_EVIDENCE_VALIDATED:
            try:
                from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH
                from scripts.game_data.il2cpp.protocol import load_metadata_helper

                metadata = load_metadata_helper(METADATA_HELPER_PATH).Metadata(native.metadata)
                matching_types = [
                    row for row in metadata.types
                    if metadata.type_full_name(row) == candidate["metadataType"]
                ]
                if len(matching_types) != 1:
                    reject("component_name_candidate.metadata_type", 1, len(matching_types))
                else:
                    names = {
                        metadata.string(row.name_index)
                        for row in metadata.methods_for(matching_types[0])
                    }
                    present = sorted(set(candidate["absentMetadataMethods"]) & names)
                    if present:
                        reject("component_name_candidate.absent_metadata_methods", [], present)
            except (OSError, KeyError, TypeError, ValueError) as exc:
                reject("component_name_candidate.metadata", "parsed selected metadata", str(exc))

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
        "nestedContextObservations": (
            contract.get("nestedContextObservations") if not failures else None
        ),
        "nestedReaderPhaseObservations": (
            contract.get("nestedReaderPhaseObservations") if not failures else None
        ),
        "nestedKeyIndexObservations": (
            contract.get("nestedKeyIndexObservations") if not failures else None
        ),
        "nestedPairedRootObservations": (
            contract.get("nestedPairedRootObservations") if not failures else None
        ),
        "infoKeyProducerObservations": (
            contract.get("infoKeyProducerObservations") if not failures else None
        ),
        "groupComponentNameCandidate": (
            contract.get("groupComponentNameCandidate") if not failures else None
        ),
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "validationFailures": failures,
    }


__all__ = ["validate_streaming_field2_native_contract", "DEFAULT_CONTRACT"]
