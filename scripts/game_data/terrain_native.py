"""Fail-closed validation for the selected-build Terrain TRET consumer."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.story_builder.native_protocol.il2cpp import (
    enum_members,
    field_defaults,
    load_metadata_helper,
)


SCHEMA = "endfield.terrain-tret-native-contract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("terrain_tret_native.json")
METADATA_HELPER = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "endfield-il2cpp"
    / "catalog_option_flow_metadata.py"
)
# Filled after the reviewed JSON contract is finalized. Keeping this pin in
# code makes edits to the evidence catalog explicit rather than silent.
CONTRACT_SHA256 = "4A7BC679B01AFD5D81B909FB16F1359FF680B31970F88BEBE9BB857440ED7152"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _pe_file_offset(image: bytes, rva: int) -> int:
    """Map one RVA through a PE section table, rejecting virtual-only bytes."""

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


def validate_terrain_native_contract(
    *,
    contract_path: Path = DEFAULT_CONTRACT,
    game_root: Path | None = None,
) -> dict[str, Any]:
    """Revalidate every native identity used by the Terrain range contract."""

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
                actual_body_sha256 = _sha256_bytes(body)
                expected_body_sha256 = str(row.get("bodySha256", "")).upper()
                if actual_body_sha256 != expected_body_sha256:
                    reject(f"{role}.body_sha256", expected_body_sha256, actual_body_sha256)
                entry_hex = str(row.get("entryBytesHex", ""))
                if entry_hex:
                    expected_entry = bytes.fromhex(entry_hex)
                    if body[: len(expected_entry)] != expected_entry:
                        reject(
                            f"{role}.entry_bytes",
                            entry_hex.upper(),
                            body[: len(expected_entry)].hex().upper(),
                        )
            except (KeyError, TypeError, ValueError) as exc:
                reject(f"{role}.byte_range", "valid bounded PE range", str(exc))

        table = contract.get("graphicsFormatDescriptorTable") or {}
        try:
            table_offset = _pe_file_offset(unity_image, int(table["rva"]))
            stride = int(table["entryStride"])
            for entry in table.get("entries") or []:
                value = int(entry["value"])
                expected_prefix = bytes.fromhex(str(entry["prefixHex"]))
                position = table_offset + value * stride
                actual_prefix = unity_image[position : position + len(expected_prefix)]
                if len(actual_prefix) != len(expected_prefix) or actual_prefix != expected_prefix:
                    reject(
                        f"graphics_format_{value}.descriptor_prefix",
                        expected_prefix.hex().upper(),
                        actual_prefix.hex().upper(),
                    )
        except (KeyError, TypeError, ValueError) as exc:
            reject("graphics_format_descriptor_table", "valid bounded PE table", str(exc))

    if native.metadata.is_file():
        try:
            helper = load_metadata_helper(METADATA_HELPER)
            metadata_image = helper.Metadata(native.metadata)
            current_rows = {
                int(row["id"]): row
                for row in enum_members(
                    metadata_image,
                    field_defaults(metadata_image),
                    "UnityEngine.Experimental.Rendering.GraphicsFormat",
                )
            }
            for expected in contract.get("graphicsFormats") or []:
                value = int(expected["value"])
                actual = current_rows.get(value)
                expected_shape = {
                    "id": value,
                    "name": expected.get("name"),
                    "token": expected.get("fieldToken"),
                }
                actual_shape = (
                    {
                        "id": actual.get("id"),
                        "name": actual.get("name"),
                        "token": actual.get("token"),
                    }
                    if actual
                    else None
                )
                if actual_shape != expected_shape:
                    reject(f"graphics_format_{value}.metadata_enum", expected_shape, actual_shape)
        except Exception as exc:
            reject("graphics_format_metadata_enum", "readable exact enum", str(exc)[:400])

    status = NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed"
    return {
        "status": status,
        "nativeMappingId": contract.get("nativeMappingId"),
        "contractSha256": actual_contract_sha256,
        "gameAssemblySha256": native.gameassembly_sha256.upper(),
        "metadataSha256": native.metadata_sha256.upper(),
        "unityPlayerSha256": actual_unity_sha256,
        "headerConsumer": contract.get("headerConsumer"),
        "graphicsFormats": contract.get("graphicsFormats"),
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "validationFailures": failures,
    }


__all__ = ["validate_terrain_native_contract", "DEFAULT_CONTRACT"]
