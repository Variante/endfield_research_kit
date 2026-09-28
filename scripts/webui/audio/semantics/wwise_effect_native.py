"""Authenticate reviewed Wwise effect parameter layouts on selected inputs."""

from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "wwise_effect_parameters_native.json"


@lru_cache(maxsize=1)
def load_effect_parameter_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema") != "endfield.wwise-effect-parameters-native.v2":
        raise ValueError("unsupported Wwise effect parameter contract")
    return contract


def effect_parameter_schema(plugin_class_id: int) -> dict[str, Any] | None:
    contract = load_effect_parameter_contract()
    if contract.get("status") != "reviewedCurrentBuild":
        return None
    row = contract["parameterSchemas"].get(f"0x{plugin_class_id:08x}")
    return row if row and row.get("status") == "reviewed" else None


def _pe_body(image: bytes, rva: int, length: int) -> bytes:
    """Read a bounded RVA window from one PE image without another dependency."""
    if len(image) < 0x40 or image[:2] != b"MZ":
        raise ValueError("invalid PE DOS header")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    if pe_offset + 24 > len(image) or image[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    section_offset = pe_offset + 24 + optional_size
    if not 0 < section_count <= 96 or section_offset + section_count * 40 > len(image):
        raise ValueError("invalid PE section table")
    for index in range(section_count):
        at = section_offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", image, at + 8
        )
        if virtual_address <= rva and rva + length <= virtual_address + min(virtual_size, raw_size):
            start = raw_offset + rva - virtual_address
            if start + length <= len(image):
                return image[start:start + length]
    raise ValueError(f"RVA window 0x{rva:x}+{length} outside mapped PE bytes")


def _pe_image_base(image: bytes) -> int:
    if len(image) < 0x40 or image[:2] != b"MZ":
        raise ValueError("invalid PE DOS header")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    optional = pe_offset + 24
    if optional + 32 > len(image) or image[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    if struct.unpack_from("<H", image, optional)[0] != 0x20B:
        raise ValueError("AkSoundEngine.dll is not PE32+")
    return struct.unpack_from("<Q", image, optional + 24)[0]


def _validate_registration_witness(
    image: bytes, image_base: int, class_id: str, witness: dict[str, Any], method_rva: int
) -> None:
    """Join a plug-in registration to its parameter factory and vtable slot."""
    registration = struct.unpack(
        "<QQQQ", _pe_body(image, int(witness["registrationRva"], 16), 32)
    )
    expected = (
        witness["pluginType"],
        witness["pluginId"],
        image_base + int(witness["factoryRva"], 16),
        image_base + int(witness["parameterFactoryRva"], 16),
    )
    if registration != expected or int(class_id, 16) != (expected[1] << 16) | expected[0]:
        raise ValueError(f"effect registration mismatch for {class_id}")
    factory = _pe_body(
        image, int(witness["parameterFactoryRva"], 16), witness["parameterFactoryBodyLength"]
    )
    if hashlib.sha256(factory).hexdigest() != witness["parameterFactoryBodySha256"]:
        raise ValueError(f"parameter factory body mismatch for {class_id}")
    if "parameterConstructorRva" in witness:
        constructor_rva = int(witness["parameterConstructorRva"], 16)
        jump_rva = int(witness["constructorJumpRva"], 16)
        jump = _pe_body(image, jump_rva, 5)
        if jump[0] != 0xE9 or jump_rva + 5 + struct.unpack_from("<i", jump, 1)[0] != constructor_rva:
            raise ValueError(f"parameter constructor jump mismatch for {class_id}")
        constructor = _pe_body(image, constructor_rva, witness["parameterConstructorBodyLength"])
        if hashlib.sha256(constructor).hexdigest() != witness["parameterConstructorBodySha256"]:
            raise ValueError(f"parameter constructor body mismatch for {class_id}")
    lea_rva = int(witness["vtableLeaRva"], 16)
    lea = _pe_body(image, lea_rva, 7)
    if lea[:3].hex() != witness["vtableLeaPrefixHex"]:
        raise ValueError(f"parameter vtable LEA mismatch for {class_id}")
    if lea_rva + 7 + struct.unpack_from("<i", lea, 3)[0] != int(witness["vtableRva"], 16):
        raise ValueError(f"parameter vtable target mismatch for {class_id}")
    slot = struct.unpack(
        "<Q", _pe_body(image, int(witness["vtableRva"], 16) + witness["setParamsBlockSlot"], 8)
    )[0]
    if witness["setParamsBlockSlot"] != 40 or slot != image_base + method_rva:
        raise ValueError(f"SetParamsBlock vtable slot mismatch for {class_id}")


def check_effect_parameter_native_inputs(game_root: Path) -> dict[str, Any]:
    """Validate the selected native triplet, method bodies, and registration joins."""
    contract = load_effect_parameter_contract()
    expected = contract["nativeInputs"]
    selected = Path(game_root)
    native = check_installed_native_inputs(
        expected_gameassembly_sha256=expected["gameAssemblySha256"],
        expected_metadata_sha256=expected["globalMetadataSha256"],
        gameassembly=selected.parent / "GameAssembly.dll",
        metadata=selected / "il2cpp_data" / "Metadata" / "global-metadata.dat",
    )
    ak_path = selected / "Plugins" / "x86_64" / "AkSoundEngine.dll"
    result: dict[str, Any] = {
        "status": native.status,
        "detail": native.detail,
        "contractSchema": contract["schema"],
        "selectedGameRoot": str(selected),
        "gameAssemblySha256": native.gameassembly_sha256,
        "globalMetadataSha256": native.metadata_sha256,
        "akSoundEnginePath": str(ak_path),
        "akSoundEngineSha256": "",
        "expectedAkSoundEngineSha256": expected["akSoundEngineSha256"],
        "expectedAkSoundEngineSize": expected["akSoundEngineFileSize"],
        "validatedClassIds": [],
        "validatedStructuralClassIds": [],
    }
    if contract.get("status") != "reviewedCurrentBuild":
        result.update(status="mismatched", detail="Wwise effect parameter contract is not reviewed")
        return result
    if native.status != "validated":
        return result
    if not ak_path.is_file():
        result.update(status="missing", detail=f"selected AkSoundEngine.dll not found at {ak_path}")
        return result
    actual_size = ak_path.stat().st_size
    actual_sha256 = sha256_file(ak_path)
    result["akSoundEngineSize"] = actual_size
    result["akSoundEngineSha256"] = actual_sha256
    if actual_size != expected["akSoundEngineFileSize"] or actual_sha256.casefold() != expected["akSoundEngineSha256"].casefold():
        result.update(
            status="mismatched",
            detail=(
                "selected AkSoundEngine.dll differs from the reviewed effect layout: "
                f"size={actual_size} sha256={actual_sha256[:12]}, "
                f"expected size={expected['akSoundEngineFileSize']} "
                f"sha256={expected['akSoundEngineSha256'][:12]}"
            ),
        )
        return result
    image = ak_path.read_bytes()
    try:
        image_base = _pe_image_base(image) if contract.get("registrationWitnesses") else 0
        validated_class_ids = []
        for class_id, row in contract["parameterSchemas"].items():
            if row.get("status") != "reviewed":
                continue
            method = row["setParamsBlock"]
            body = _pe_body(image, int(method["rva"], 16), method["bodyLength"])
            if hashlib.sha256(body).hexdigest().casefold() != method["bodySha256"].casefold():
                raise ValueError(f"SetParamsBlock body mismatch for {class_id}")
            validated_class_ids.append(class_id)
        validated_structural_class_ids = []
        structural_rows = contract.get("structuralSchemas", {})
        witnesses = contract.get("registrationWitnesses", {})
        if {k for k, v in witnesses.items() if v["role"] == "structuralOnly"} != set(structural_rows):
            raise ValueError("structural effect registration witness set differs from schemas")
        for class_id, row in structural_rows.items():
            if row["status"] != "structuralOnly":
                raise ValueError(f"structural effect status mismatch for {class_id}")
            method = row["setParamsBlock"]
            body = _pe_body(image, int(method["rva"], 16), method["bodyLength"])
            if hashlib.sha256(body).hexdigest().casefold() != method["bodySha256"].casefold():
                raise ValueError(f"structural SetParamsBlock body mismatch for {class_id}")
            validated_structural_class_ids.append(class_id)
        for class_id, witness in witnesses.items():
            if witness["role"] == "slotControl":
                if class_id not in validated_class_ids:
                    raise ValueError(f"unreviewed effect slot control {class_id}")
                method = contract["parameterSchemas"][class_id]["setParamsBlock"]
            elif witness["role"] == "structuralOnly":
                method = structural_rows[class_id]["setParamsBlock"]
            else:
                raise ValueError(f"unknown effect registration role for {class_id}")
            _validate_registration_witness(image, image_base, class_id, witness, int(method["rva"], 16))
    except (KeyError, TypeError, ValueError, struct.error) as exc:
        result.update(status="mismatched", detail=str(exc))
        return result
    result["validatedClassIds"] = sorted(validated_class_ids)
    result["validatedStructuralClassIds"] = sorted(validated_structural_class_ids)
    return result
