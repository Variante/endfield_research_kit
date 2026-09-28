"""Validate the selected native 128-bit Init descriptor mask setup."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.streaming.native import _pe_file_offset, _pe_image_base


SCHEMA = "endfield.streaming-descriptor-mask-native-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "streaming_descriptor_mask_native.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _mapped(image: bytes, rva: int, size: int) -> bytes:
    offset = _pe_file_offset(image, rva, size=size)
    body = image[offset : offset + size]
    if len(body) != size:
        raise ValueError(f"RVA {rva:#x}: short mapped read {len(body)}/{size}")
    return body


def _number(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def validate_descriptor_mask_native(
    *, game_root: Path, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Fail closed on source, selected bytes, or direct-call drift."""
    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw)
        if contract.get("schema") != SCHEMA or contract.get("status") != "selected-structural":
            raise ValueError("contract:schema-or-status")
        pins = contract["nativeInputs"]
        root = Path(game_root)
        native = check_installed_native_inputs(
            pins["gameAssemblySha256"], pins["metadataSha256"],
            gameassembly=root.parent / "GameAssembly.dll",
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat",
        )
        if native.status != NATIVE_EVIDENCE_VALIDATED:
            raise ValueError(f"native:{native.status}:{native.detail}")
        unity = root.parent / "UnityPlayer.dll"
        image = unity.read_bytes()
        unity_hash = _sha256(image)
        if unity_hash != pins["unityPlayerSha256"]:
            raise ValueError(f"unityplayer:sha256={unity_hash}")
        if _pe_image_base(image) != _number(contract["unityPlayerImageBase"]):
            raise ValueError("unityplayer:image-base")
        for row in contract["codeWindows"]:
            start, end = _number(row["startRva"]), _number(row["endRva"])
            if end <= start or _sha256(_mapped(image, start, end - start)) != row["sha256"]:
                raise ValueError(f"code-window:{row['role']}")
        for row in contract["calls"]:
            source, target = _number(row["sourceRva"]), _number(row["targetRva"])
            opcode = _mapped(image, source, 5)
            if opcode[0] != 0xE8 or source + 5 + struct.unpack_from("<i", opcode, 1)[0] != target:
                raise ValueError(f"call:{row['role']}")
        for row in contract["instructions"]:
            rva, expected = _number(row["rva"]), bytes.fromhex(row["hex"])
            if not expected or _mapped(image, rva, len(expected)) != expected:
                raise ValueError(f"instruction:{row['role']}")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, struct.error) as error:
        return {"status": "validation_failed", "reason": str(error)}
    return {
        "status": "validated", "contractSha256": _sha256(raw),
        "nativeInputs": dict(pins),
        "evidenceBoundary": contract["evidenceBoundary"],
    }
