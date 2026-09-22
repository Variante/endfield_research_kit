"""Exact selected-build LevelCameraLookAt fields and unmanaged initial state."""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from . import params


CONTRACT_PATH = Path(__file__).with_name("camera_look_at_layout.json")
CONTRACT_SHA256 = "17240e7ab5c783214964dc9096e18a4a8b1945a2f698bcf58ba5cb42dce7dece"


class CameraLookAtDecodeError(ValueError):
    """The selected camera field has no authenticated exact boundary."""


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    raw = CONTRACT_PATH.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != CONTRACT_SHA256:
        raise CameraLookAtDecodeError(
            f"LevelCameraLookAt.contract_sha256: expected={CONTRACT_SHA256}, actual={actual}"
        )
    result = json.loads(raw)
    if result.get("schema") != "endfield.levelscript-camera-look-at.v1":
        raise CameraLookAtDecodeError("LevelCameraLookAt.contract_schema: unsupported")
    return result


def _initial_param(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    # The Param formatter copies an unmanaged 24-byte value. The separately
    # generated seven-member wrapper is not the constant's wire encoding.
    if offset < 0 or offset + 25 > len(data) or data[offset] != 4:
        return None
    raw = data[offset + 1:offset + 25]
    value: dict[str, Any] = {}
    for name, kind, at in _contract()["initialParam"]["fields"]:
        if kind == "bool":
            if raw[at] not in (0, 1):
                return None
            value[name] = bool(raw[at])
        else:
            number = struct.unpack_from("<f", raw, at)[0]
            if not math.isfinite(number):
                return None
            value[name] = number
    tail = params.decode_param_tail(data, offset + 25)
    if tail is None:
        return None
    binding, end = tail
    return {"value": value, "rawConstantHex": raw.hex(), **binding}, end


def _vector_param(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    if offset < 0 or offset + 13 > len(data) or data[offset] != 4:
        return None
    values = struct.unpack_from("<fff", data, offset + 1)
    if not all(math.isfinite(value) for value in values):
        return None
    tail = params.decode_param_tail(data, offset + 13)
    if tail is None:
        return None
    binding, end = tail
    return {"value": dict(zip(("x", "y", "z"), values)), **binding}, end


def _float_param(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    if offset < 0 or offset + 5 > len(data) or data[offset] != 4:
        return None
    value = struct.unpack_from("<f", data, offset + 1)[0]
    tail = params.decode_param_tail(data, offset + 5)
    if not math.isfinite(value) or tail is None:
        return None
    binding, end = tail
    return {"value": value, **binding}, end


def _curve_key_param(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    if offset < 0 or offset + 6 > len(data) or data[offset:offset + 2] != b"\x04\x01":
        return None
    size = struct.unpack_from("<i", data, offset + 2)[0]
    cursor = offset + 6
    if size == -1:
        key = None
    elif 0 <= size <= 1 << 20 and cursor + size <= len(data):
        try:
            key = data[cursor:cursor + size].decode("utf-8")
        except UnicodeDecodeError:
            return None
        cursor += size
    else:
        return None
    tail = params.decode_param_tail(data, cursor)
    if tail is None:
        return None
    binding, end = tail
    return {"value": {"key": key}, **binding}, end


def decode_fields(
    data: bytes, offset: int, *, game_root: Path | None = None,
) -> tuple[dict[str, Any], int]:
    """Read all 31 fields; reject native drift and unknown nested values."""
    contract = _contract()
    inputs = contract["nativeInputs"]
    native = check_installed_native_inputs(
        inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
        gameassembly=game_root.parent / "GameAssembly.dll" if game_root is not None else None,
        metadata=(game_root / "il2cpp_data/Metadata/global-metadata.dat")
        if game_root is not None else None,
    )
    if native.status != "validated":
        raise CameraLookAtDecodeError(
            f"LevelCameraLookAt.installed_native_inputs: expected=validated, "
            f"actual={native.status}, detail={native.detail}"
        )
    start = offset
    result: dict[str, Any] = {}
    decoders = {
        "Param<float>": _float_param,
        "Param<bool>": params.decode_bool_param,
        "Param<Vector3>": _vector_param,
        "Param<string>": params.decode_string_param,
        "Param<EntityPtr>": params.decode_constant_entity_ptr_param,
        "Param<CameraControlStateInitialParam>": _initial_param,
        "Param<CameraBlendCurveKey>": _curve_key_param,
        "Param<CinemachineBlendDefinition.Style>": params.decode_i32_param,
        "Param<NodeLookAtType>": params.decode_i32_param,
        "Param<MountPoint>": params.decode_i32_param,
        "ParamOutput<CameraControlState>": params.decode_param_output,
        "ParamOutput<int>": params.decode_param_output,
    }
    for name, kind in contract["fields"]:
        if 0 <= offset < len(data) and data[offset] == 0xFF:
            result[name] = None
            offset += 1
            continue
        decoder = decoders.get(kind)
        decoded = decoder(data, offset) if decoder is not None else None
        if decoded is None:
            raise CameraLookAtDecodeError(
                f"LevelCameraLookAt.{name}: unsupported {kind}, offset={offset}"
            )
        value, offset = decoded
        if kind.startswith("ParamOutput<"):
            value = {"paramTarget": value["paramSource"], "path": value["path"]}
        result[name] = value
    result["consumedBytes"] = offset - start
    return result, offset
