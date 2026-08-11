"""Decode a detached, build-pinned LightCullResult capture artifact.

This tool deliberately consumes a user-supplied JSON artifact only.  It does
not attach to, inject into, or inspect a live game process.  The artifact
contains the pointer/count observed by an authorized external capture and the
raw ``VisibleLight`` bytes copied from that capture.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any, Mapping


SCHEMA = "endfield.light-cull-capture.v1"
GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
UNITY_PLAYER_SHA256 = "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2"
GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
ROW_STRIDE_BYTES = 148
MAX_VISIBLE_LIGHT_COUNT = 256


class CaptureDecodeError(ValueError):
    """Raised when a detached capture cannot be decoded without guessing."""


def _required(mapping: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        raise CaptureDecodeError(f"{path}.{key}: missing required field")
    return mapping[key]


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise CaptureDecodeError(f"{path}: expected non-empty string")
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool):
        raise CaptureDecodeError(f"{path}: boolean is not an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError as exc:
            raise CaptureDecodeError(f"{path}: invalid integer {value!r}") from exc
    raise CaptureDecodeError(f"{path}: expected integer or 0x-prefixed string")


def _raw_rows(value: Any, path: str) -> bytes:
    if not isinstance(value, str):
        raise CaptureDecodeError(f"{path}: expected hexadecimal byte string")
    text = value
    try:
        return bytes.fromhex(text)
    except ValueError as exc:
        raise CaptureDecodeError(f"{path}: invalid hexadecimal byte string") from exc


def _finite_float(value: float, path: str) -> float:
    if not math.isfinite(value):
        raise CaptureDecodeError(f"{path}: non-finite decoded float")
    return value


def _finite_floats(
    row: bytes, offset: int, count: int, path: str
) -> tuple[float, ...]:
    return tuple(
        _finite_float(value, path)
        for value in struct.unpack_from(f"<{count}f", row, offset)
    )


def decode_capture(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and decode one detached LightCullResult JSON document."""

    if _required(document, "schema", "capture") != SCHEMA:
        raise CaptureDecodeError(
            f"capture.schema: expected {SCHEMA!r}"
        )
    if _required(document, "gameBuild", "capture") != GAME_BUILD:
        raise CaptureDecodeError(
            f"capture.gameBuild: expected {GAME_BUILD!r}"
        )

    pins = _required(document, "binaryPins", "capture")
    if not isinstance(pins, Mapping):
        raise CaptureDecodeError("capture.binaryPins: expected object")
    if _text(_required(pins, "unityPlayerSha256", "capture.binaryPins"), "capture.binaryPins.unityPlayerSha256").lower() != UNITY_PLAYER_SHA256:
        raise CaptureDecodeError("capture.binaryPins.unityPlayerSha256: binary pin mismatch")
    if _text(_required(pins, "gameAssemblySha256", "capture.binaryPins"), "capture.binaryPins.gameAssemblySha256").lower() != GAME_ASSEMBLY_SHA256:
        raise CaptureDecodeError("capture.binaryPins.gameAssemblySha256: binary pin mismatch")

    call_site = _text(_required(document, "callSite", "capture"), "capture.callSite")
    if call_site not in {"normal", "ui"}:
        raise CaptureDecodeError("capture.callSite: expected 'normal' or 'ui'")

    result = _required(document, "result", "capture")
    if not isinstance(result, Mapping):
        raise CaptureDecodeError("capture.result: expected object")
    pointer = _integer(
        _required(result, "visibleLightsPtr", "capture.result"),
        "capture.result.visibleLightsPtr",
    )
    count = _integer(
        _required(result, "visibleLightCount", "capture.result"),
        "capture.result.visibleLightCount",
    )
    if pointer < 0:
        raise CaptureDecodeError("capture.result.visibleLightsPtr: must be non-negative")
    if not 0 <= count <= MAX_VISIBLE_LIGHT_COUNT:
        raise CaptureDecodeError(
            "capture.result.visibleLightCount: expected 0..256"
        )
    raw = _raw_rows(
        _required(result, "rawRowsHex", "capture.result"),
        "capture.result.rawRowsHex",
    )
    expected_bytes = count * ROW_STRIDE_BYTES
    if len(raw) != expected_bytes:
        raise CaptureDecodeError(
            "capture.result.rawRowsHex: expected "
            f"{expected_bytes} bytes for count={count}, got {len(raw)}"
        )
    if count == 0 and pointer != 0:
        raise CaptureDecodeError(
            "capture.result.visibleLightsPtr: zero count must carry a null pointer"
        )
    if count > 0 and pointer == 0:
        raise CaptureDecodeError(
            "capture.result.visibleLightsPtr: non-zero count requires a pointer"
        )

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row = raw[index * ROW_STRIDE_BYTES : (index + 1) * ROW_STRIDE_BYTES]
        light_type = struct.unpack_from("<I", row, 0x00)[0]
        final_color = _finite_floats(
            row, 0x04, 4, f"capture.result.rows[{index}].finalColor"
        )
        local_to_world_matrix = _finite_floats(
            row,
            0x24,
            16,
            f"capture.result.rows[{index}].localToWorldMatrix",
        )
        specular_intensity = _finite_float(
            struct.unpack_from("<f", row, 0x64)[0],
            f"capture.result.rows[{index}].specularIntensity",
        )
        light_range = _finite_float(
            struct.unpack_from("<f", row, 0x68)[0],
            f"capture.result.rows[{index}].range",
        )
        spot_angle = _finite_float(
            struct.unpack_from("<f", row, 0x6C)[0],
            f"capture.result.rows[{index}].spotAngle",
        )
        priority = struct.unpack_from("<i", row, 0x70)[0]
        position = tuple(
            _finite_float(value, f"capture.result.rows[{index}].worldPosition")
            for value in struct.unpack_from("<3f", row, 0x74)
        )
        identity_word_0x84 = struct.unpack_from("<I", row, 0x84)[0]
        if identity_word_0x84 != 0:
            raise CaptureDecodeError(
                f"capture.result.rows[{index}].rawIdentityWord0x84: "
                "expected converter-written zero"
            )
        rows.append(
            {
                "index": index,
                "lightType": light_type,
                "finalColor": list(final_color),
                "localToWorldMatrix": list(local_to_world_matrix),
                "specularIntensity": specular_intensity,
                "priority": priority,
                "range": light_range,
                "spotAngle": spot_angle,
                "worldPosition": list(position),
                "rawIdentityWord0x80": struct.unpack_from("<I", row, 0x80)[0],
                "rawIdentityWord0x84": identity_word_0x84,
                "rawIdentityPointer0x88": f"0x{struct.unpack_from('<Q', row, 0x88)[0]:X}",
            }
        )

    return {
        "schema": SCHEMA,
        "gameBuild": GAME_BUILD,
        "callSite": call_site,
        "result": {
            "visibleLightsPtr": f"0x{pointer:X}",
            "visibleLightCount": count,
            "rawBytes": len(raw),
            "rowStrideBytes": ROW_STRIDE_BYTES,
        },
        "rows": rows,
    }


def load_capture(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureDecodeError(f"{path}: cannot read JSON capture") from exc
    if not isinstance(document, Mapping):
        raise CaptureDecodeError(f"{path}: top-level JSON value must be an object")
    return decode_capture(document)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decode a detached, build-pinned LightCullResult capture"
    )
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        decoded = load_capture(args.capture)
    except CaptureDecodeError as exc:
        parser.error(str(exc))
    rendered = json.dumps(decoded, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
