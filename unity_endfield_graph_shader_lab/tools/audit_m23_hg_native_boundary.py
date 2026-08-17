#!/usr/bin/env python3
"""Pin the stripped UnityPlayer HG-particle native boundary for M23 recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "endfield.m23-hg-native-boundary.v1"
DEFAULT_UNITY_PLAYER = Path(r"D:/Program Files/Endfield Game/UnityPlayer.dll")
EXPECTED_SIZE = 38_194_232
EXPECTED_SHA256 = "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2"
EXPECTED_IMAGE_BASE = 0x180000000
TYPE_NAME = b"HGParticleMeshInstanceRenderer"
EXPECTED_NAME_OFFSETS = [0x1DA57A8, 0x1DA586A]
REGISTRATION_OFFSET = 0x21197C0
EXPECTED_REGISTRATION_QWORDS = [
    0x181DA6BA8,
    0x181CE1DF5,
    0x181CE1CC8,
    0x000002F8191FECD6,
    0x0000000080000000,
    0x0000000000000100,
]
FUNCTIONS = [
    ("hgMeshRendererDataInitializer", 0x181088D80, 0x35E,
     "e97ae32dba96720c667983b53657782f599cb1fab260922aae04b57d0c9d153f"),
    ("tableEntryLookup", 0x18042DA70, 0xEA,
     "e052dada114c67c22a85a2acac401b1208d9a222e8cf73889deaaafdbda63e37"),
    ("resourcePointerLookup", 0x180424C30, 0x12E,
     "4fa6cc9f5e55aa933412c4c3f8bd6d70ab1d2ca3ee4cb7f2b376f665b0a4348b"),
    ("tableFlagUpdate", 0x18033B740, 0x15C,
     "8bd61842065dea372ccc8b7291908c792bfaf5c8fb8cb670c3fdb97697010dee"),
    ("runtimeHandleLookup", 0x1801F7410, 0x7F,
     "4cfe945355004f04f9d261f6d7f3b3304e58fae6d382123e8e1c0f838be0905c"),
    ("registryFallbackLookup", 0x180133900, 0x119,
     "e5d0f9aff86db26163be508cb614c4e7c1482d4da55c2661881a354c05fd932b"),
]


def _pe_layout(data: bytes) -> tuple[int, list[dict[str, int]]]:
    if data[:2] != b"MZ":
        raise ValueError("UnityPlayer is not a PE image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("invalid PE signature")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic != 0x20B:
        raise ValueError("expected PE32+ UnityPlayer")
    image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    section_table = optional + optional_size
    sections = []
    for index in range(section_count):
        row = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, row + 8)
        sections.append({"virtualSize": virtual_size, "virtualAddress": virtual_address,
                         "rawSize": raw_size, "rawOffset": raw_offset})
    return image_base, sections


def _va_to_offset(va: int, image_base: int, sections: list[dict[str, int]]) -> int:
    rva = va - image_base
    for section in sections:
        start = section["virtualAddress"]
        limit = start + max(section["virtualSize"], section["rawSize"])
        if start <= rva < limit:
            return section["rawOffset"] + rva - start
    raise ValueError(f"VA is outside mapped PE sections: 0x{va:X}")


def audit(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    failures: list[dict[str, Any]] = []

    def check(check_id: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            failures.append({"id": check_id, "expected": expected, "actual": actual})

    digest = hashlib.sha256(data).hexdigest()
    check("file.size", len(data), EXPECTED_SIZE)
    check("file.sha256", digest, EXPECTED_SHA256)
    image_base, sections = _pe_layout(data)
    check("pe.imageBase", image_base, EXPECTED_IMAGE_BASE)

    offsets = []
    cursor = 0
    while True:
        found = data.find(TYPE_NAME, cursor)
        if found < 0:
            break
        offsets.append(found)
        cursor = found + 1
    check("typeName.offsets", offsets, EXPECTED_NAME_OFFSETS)

    qwords = list(struct.unpack_from("<6Q", data, REGISTRATION_OFFSET))
    check("registration.qwords", qwords, EXPECTED_REGISTRATION_QWORDS)
    check("registration.namePointer",
          _va_to_offset(qwords[0], image_base, sections), EXPECTED_NAME_OFFSETS[0])

    functions = []
    for name, va, size, expected_hash in FUNCTIONS:
        offset = _va_to_offset(va, image_base, sections)
        actual_hash = hashlib.sha256(data[offset:offset + size]).hexdigest()
        check(f"function.{name}.sha256", actual_hash, expected_hash)
        functions.append({"name": name, "virtualAddress": f"0x{va:X}",
                          "fileOffset": f"0x{offset:X}", "bytes": size,
                          "sha256": actual_hash})

    return {
        "schema": SCHEMA,
        "status": "pass" if not failures else "fail",
        "source": {"path": str(path), "bytes": len(data), "sha256": digest},
        "nativeTypeRegistration": {
            "name": TYPE_NAME.decode("ascii"),
            "nameOffsets": [f"0x{value:X}" for value in offsets],
            "registrationFileOffset": f"0x{REGISTRATION_OFFSET:X}",
            "methodBearingRegistration": False,
            "constructorOrVtableRecovered": False,
        },
        "initializer": {
            "recordBytes": 0x18,
            "recordFields": ["materialHandle:u32", "mainMeshHandle:u32",
                             "shadowProxyMeshHandle:u32"],
            "vertexOrConstantBufferProducer": False,
        },
        "functions": functions,
        "admission": {
            "hgParticleNativeTypeIdentified": True,
            "hgParticlePackerResolved": False,
            "stride136ProducerResolved": False,
            "drawTimeCb3ProducerResolved": False,
            "claim": "native registration and HGMesh handle initializer are pinned; neither exposes the particle packer",
        },
        "summary": {"failed": len(failures),
                    "firstFailure": failures[0]["id"] if failures else None},
        "failures": failures,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unity-player", type=Path, default=DEFAULT_UNITY_PLAYER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = audit(args.unity_player)
    except (OSError, ValueError, struct.error) as exc:
        report = {"schema": SCHEMA, "status": "fail", "error": str(exc)}
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
