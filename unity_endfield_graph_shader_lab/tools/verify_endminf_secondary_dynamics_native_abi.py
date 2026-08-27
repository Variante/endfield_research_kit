#!/usr/bin/env python3
"""Verify the pinned WriteTransform hidden-return ABI from GameAssembly.dll."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_secondary_dynamics_native_abi.json"
)
EXPECTED_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
WRITE_TRANSFORM_RVA = 0x672641C
WITNESSES = {
    "prologue": (0x0, "488bc448895808488970104889781855"),
    "jobHandleByRefFromR8": (0x22, "498bf0"),
    "instanceFromRdx": (0x29, "488bda"),
    "returnBufferFromRcx": (0x30, "488bf9"),
    "loadSixteenByteReturn": (0x1E7, "0f1000"),
    "returnRaxIsBuffer": (0x1F2, "488bc7"),
    "storeSixteenBytesToBuffer": (0x21B, "f30f7f07"),
    "return": (0x227, "c3"),
}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rva_to_offset(image: bytes, rva: int) -> int:
    require(len(image) >= 0x40 and image[:2] == b"MZ", "missing DOS header")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    require(pe_offset + 24 <= len(image), "truncated PE header")
    require(image[pe_offset:pe_offset + 4] == b"PE\0\0", "missing PE signature")
    number_of_sections = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    section_offset = pe_offset + 24 + optional_size
    require(section_offset + number_of_sections * 40 <= len(image),
            "truncated section table")
    for index in range(number_of_sections):
        offset = section_offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", image, offset + 8)
        span = max(virtual_size, raw_size)
        if virtual_address <= rva < virtual_address + span:
            delta = rva - virtual_address
            require(delta < raw_size, f"RVA 0x{rva:x} has no raw bytes")
            result = raw_offset + delta
            require(result < len(image), f"RVA 0x{rva:x} maps beyond the file")
            return result
    raise VerificationError(f"RVA 0x{rva:x} is outside every PE section")


def build_report(path: Path, expected_sha256: str | None = EXPECTED_SHA256) -> dict[str, Any]:
    require(path.is_file(), f"GameAssembly.dll is absent: {path}")
    actual_sha256 = sha256(path)
    if expected_sha256 is not None:
        require(actual_sha256 == expected_sha256,
                "GameAssembly.dll hash differs from the pinned client build")
    image = path.read_bytes()
    function_offset = rva_to_offset(image, WRITE_TRANSFORM_RVA)
    rows = []
    for name, (relative, expected_hex) in WITNESSES.items():
        expected = bytes.fromhex(expected_hex)
        start = function_offset + relative
        actual = image[start:start + len(expected)]
        require(actual == expected,
                f"{name} differs at RVA 0x{WRITE_TRANSFORM_RVA + relative:x}: "
                f"expected {expected.hex()}, actual {actual.hex()}")
        rows.append({
            "name": name,
            "rva": f"0x{WRITE_TRANSFORM_RVA + relative:x}",
            "bytes": expected.hex(),
        })
    return {
        "schema": "endfield.endminf-secondary-dynamics-native-abi.v1",
        "status": "validated_write_transform_hidden_return_abi",
        "gameAssembly": str(path.resolve()),
        "gameAssemblySize": path.stat().st_size,
        "gameAssemblySha256": actual_sha256,
        "writeTransformRva": f"0x{WRITE_TRANSFORM_RVA:x}",
        "abi": {
            "return": "16-byte JobHandle through rcx buffer, mirrored in rax",
            "instance": "rdx",
            "jobHandleByReference": "r8",
            "methodInfo": "r9",
        },
        "witnesses": rows,
    }


def default_game_assembly() -> Path | None:
    root = os.environ.get("ENDFIELD_GAME_ROOT")
    if not root:
        return None
    root_path = Path(root)
    candidates = (root_path / "GameAssembly.dll", root_path.parent / "GameAssembly.dll")
    return next((item for item in candidates if item.is_file()), candidates[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=default_game_assembly())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.game_assembly is None:
        parser.error("pass --game-assembly or set ENDFIELD_GAME_ROOT")
    try:
        report = build_report(args.game_assembly.resolve())
    except (OSError, ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
