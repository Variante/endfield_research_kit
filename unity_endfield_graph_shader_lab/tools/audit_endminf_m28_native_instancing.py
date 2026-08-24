#!/usr/bin/env python3
"""Pin the current-build native M28 SRP-instancing selection boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import common  # noqa: E402
from scripts.story_builder.animestudio_story_objects import (  # noqa: E402
    REVERSE_GAMEASSEMBLY_SHA256,
    REVERSE_METADATA_SHA256,
)


OUTPUT = ROOT / "reports/assets/character_recovery/endminf_m28_native_instancing.json"
PROGRAM_REPORT = ROOT / "reports/assets/character_recovery/endminf_m28_refract_program.json"
SOURCE_REPORT = ROOT / "reports/assets/character_recovery/endminf_m28_source_contract.json"

UNITY_PLAYER_BYTES = 38_194_232
UNITY_PLAYER_SHA256 = "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2"
UNITY_PLAYER_TIMESTAMP = 0x6A4FE14E
IMAGE_BASE = 0x180000000
KEYWORD_TABLE_OFFSET = 0x21049B0
KEYWORD_TABLE_COUNT = 57
KEYWORD_ENTRY_BYTES = 16
SRP_KEYWORD_ORDINAL = 30
SRP_KEYWORD_ENTRY_OFFSET = 0x2104B90
KEYWORD_ACCESSOR_RANGE = (0x180618C50, 0x180618CAC)
KEYWORD_ACCESSOR_SHA256 = "eba3b7e55afd88fe83bef747331e36147f9e114e0a623ac10f534df62219da5f"
KEYWORD_ACCESSOR_CALL_SITES = (0x180614039, 0x180619587)
KEYWORD_REGISTRY_INIT_RANGE = (0x180619520, 0x180619664)
KEYWORD_REGISTRY_INIT_SHA256 = "4ecca66c0514341ce460dde5513efe3da215a87cc803ca6d1a2f3cf1d787b52a"
KEYWORD_REGISTRY_INIT_CALL_SITE = 0x18062850C
DEFAULT_BUILTIN_SET_RANGE = (0x180614000, 0x18061419D)
DEFAULT_BUILTIN_SET_SHA256 = "ef0bf83b663f8506250eb7ad692eab57c319abc8dd8fd589557887b4927c996f"
DEFAULT_BUILTIN_SET_CALLER_RANGE = (0x1805E5700, 0x1805E5A18)
DEFAULT_BUILTIN_SET_CALLER_SHA256 = "bc7bca2c140c79762d7ed618646cc6c3b420f126149e25431a3693647521ee06"
DEFAULT_BUILTIN_SET_CALL_SITE = 0x1805E57D8
DEFAULT_BUILTIN_ORDINALS_VA = 0x181D88A48
DEFAULT_BUILTIN_ORDINALS = (35, 33, 36, 37)
KEYWORD_REGISTER_RANGE = (0x180627040, 0x1806272D0)
KEYWORD_REGISTER_SHA256 = "68e731952f52c629e7ae95e12b67834cc7cb14fa76659aac700ee76ff5e94e0a"
KEYWORD_ID_BIT30_SEQUENCE_VA = 0x180627145
KEYWORD_ID_BIT30_SEQUENCE = bytes.fromhex(
    "8b8424800000000fbae81eeb42488d"
)
EXPECTED_KEYWORD_NEIGHBORS = {
    26: "INSTANCING_ON",
    27: "PROCEDURAL_INSTANCING_ON",
    28: "DOTS_INSTANCING_ON",
    29: "HG_ECS_INSTANCING_ON",
    30: "SRP_INSTANCING_ON",
    31: "HG_FACTORY_INSTANCING_ON",
    32: "VERTEX_SKINNING_ON",
}


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pe_layout(data: bytes) -> tuple[int, int, list[dict[str, int | str]]]:
    require(data[:2] == b"MZ", "UnityPlayer is not an MZ image")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    require(data[pe : pe + 4] == b"PE\0\0", "UnityPlayer has no PE signature")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    timestamp = struct.unpack_from("<I", data, pe + 8)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    require(struct.unpack_from("<H", data, optional)[0] == 0x20B,
            "UnityPlayer is not PE32+")
    image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    rows: list[dict[str, int | str]] = []
    table = optional + optional_size
    for index in range(count):
        offset = table + index * 40
        name = data[offset : offset + 8].split(b"\0", 1)[0].decode("ascii")
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        rows.append({
            "name": name,
            "virtualSize": virtual_size,
            "virtualAddress": virtual_address,
            "rawSize": raw_size,
            "rawOffset": raw_offset,
        })
    return image_base, timestamp, rows


def va_to_offset(
    va: int, image_base: int, sections: list[dict[str, int | str]]
) -> int:
    rva = va - image_base
    for row in sections:
        start = int(row["virtualAddress"])
        limit = start + max(int(row["virtualSize"]), int(row["rawSize"]))
        if start <= rva < limit:
            return int(row["rawOffset"]) + rva - start
    raise AuditError(f"VA is outside UnityPlayer sections: 0x{va:X}")


def read_c_string(data: bytes, offset: int) -> str:
    end = data.find(b"\0", offset)
    require(end >= offset and end - offset <= 128, "bad keyword string boundary")
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError("keyword string is not ASCII") from exc


def read_keyword_table(
    data: bytes,
    start: int,
    count: int,
    pointer_to_offset: Callable[[int], int],
) -> list[str]:
    require(start >= 0 and start + count * KEYWORD_ENTRY_BYTES <= len(data),
            "keyword table exceeds UnityPlayer")
    names = []
    for index in range(count):
        pointer, auxiliary = struct.unpack_from(
            "<QQ", data, start + index * KEYWORD_ENTRY_BYTES
        )
        require(auxiliary == 0, f"keyword entry {index} auxiliary lane is nonzero")
        names.append(read_c_string(data, pointer_to_offset(pointer)))
    return names


def read_va_bytes(
    data: bytes,
    va: int,
    size: int,
    image_base: int,
    sections: list[dict[str, int | str]],
) -> bytes:
    offset = va_to_offset(va, image_base, sections)
    require(offset + size <= len(data), f"VA range exceeds UnityPlayer: 0x{va:X}")
    return data[offset : offset + size]


def require_rel32_call(
    data: bytes,
    site: int,
    target: int,
    image_base: int,
    sections: list[dict[str, int | str]],
) -> None:
    encoded = read_va_bytes(data, site, 5, image_base, sections)
    require(encoded[0] == 0xE8, f"expected direct call at 0x{site:X}")
    displacement = struct.unpack_from("<i", encoded, 1)[0]
    require(site + 5 + displacement == target,
            f"direct call target drifted at 0x{site:X}")


def validate_native_selection_search(
    data: bytes,
    image_base: int,
    sections: list[dict[str, int | str]],
    names: list[str],
) -> dict[str, object]:
    ranges = (
        ("keywordAccessor", KEYWORD_ACCESSOR_RANGE, KEYWORD_ACCESSOR_SHA256),
        ("keywordRegistryInit", KEYWORD_REGISTRY_INIT_RANGE,
         KEYWORD_REGISTRY_INIT_SHA256),
        ("defaultBuiltInSet", DEFAULT_BUILTIN_SET_RANGE,
         DEFAULT_BUILTIN_SET_SHA256),
        ("defaultBuiltInSetCaller", DEFAULT_BUILTIN_SET_CALLER_RANGE,
         DEFAULT_BUILTIN_SET_CALLER_SHA256),
        ("keywordRegister", KEYWORD_REGISTER_RANGE, KEYWORD_REGISTER_SHA256),
    )
    bodies = []
    for name, (start, end), expected_sha in ranges:
        body = read_va_bytes(data, start, end - start, image_base, sections)
        require(sha256_bytes(body) == expected_sha,
                f"{name} native body drifted")
        bodies.append({
            "name": name,
            "virtualAddress": f"0x{start:X}",
            "bytes": len(body),
            "sha256": expected_sha,
        })

    ordinal_bytes = read_va_bytes(
        data, DEFAULT_BUILTIN_ORDINALS_VA,
        len(DEFAULT_BUILTIN_ORDINALS) * 4, image_base, sections
    )
    ordinals = struct.unpack(f"<{len(DEFAULT_BUILTIN_ORDINALS)}I", ordinal_bytes)
    require(ordinals == DEFAULT_BUILTIN_ORDINALS,
            "default built-in keyword ordinal seed drifted")
    require(SRP_KEYWORD_ORDINAL not in ordinals,
            "SRP_INSTANCING_ON unexpectedly entered the default seed")
    bit_sequence = read_va_bytes(
        data, KEYWORD_ID_BIT30_SEQUENCE_VA, len(KEYWORD_ID_BIT30_SEQUENCE),
        image_base, sections
    )
    require(bit_sequence == KEYWORD_ID_BIT30_SEQUENCE,
            "keyword-ID bit-30 classifier sequence drifted")
    for site in KEYWORD_ACCESSOR_CALL_SITES:
        require_rel32_call(
            data, site, KEYWORD_ACCESSOR_RANGE[0], image_base, sections
        )
    require_rel32_call(
        data, KEYWORD_REGISTRY_INIT_CALL_SITE, KEYWORD_REGISTRY_INIT_RANGE[0],
        image_base, sections
    )
    require_rel32_call(
        data, DEFAULT_BUILTIN_SET_CALL_SITE, DEFAULT_BUILTIN_SET_RANGE[0],
        image_base, sections
    )

    return {
        "bodyHashedFunctions": bodies,
        "defaultBuiltInSeed": {
            "ordinals": list(ordinals),
            "names": [names[index] for index in ordinals],
            "containsSrpInstancing": False,
            "conclusion": (
                "The exact four-keyword default seed contains only stereo modes. "
                "Each name is resolved to an internal 16-bit keyword ID before "
                "setting the corresponding dynamic-bitset lane; ordinal 30 is "
                "not itself the runtime bit position."
            ),
        },
        "keywordBitset": {
            "ownerArgument": "defaultBuiltInSet rcx, passed as r12 by its sole audited caller",
            "inlineWordsOffset": "0x100",
            "capacityOffset": "0x118",
            "inlineCapacityBytes": 128,
            "indexEquation": "word = internalKeywordId >> 6; bit = internalKeywordId & 63",
            "heapBoundary": (
                "capacity <= 0x80 uses inline qwords at owner+0x100; larger "
                "storage uses the pointer at owner+0x100"
            ),
            "selectionBoundary": (
                "A draw publisher must operate on the resolved internal ID. "
                "Searching for immediate ordinal 30 or mask 0x40000000 cannot "
                "identify SRP_INSTANCING_ON soundly."
            ),
        },
        "registrationOnlyBoundary": {
            "auditedAccessorCallSites": [
                f"0x{site:X}" for site in KEYWORD_ACCESSOR_CALL_SITES
            ],
            "registryInitCallSite": f"0x{KEYWORD_REGISTRY_INIT_CALL_SITE:X}",
            "defaultSeedCallSite": f"0x{DEFAULT_BUILTIN_SET_CALL_SITE:X}",
            "conclusion": (
                "The ordinal table feeds registration and the stereo default "
                "seed; it is not a draw-time ordinal-indexed selector."
            ),
        },
        "rejectedBit30FalsePositive": {
            "virtualAddress": f"0x{KEYWORD_ID_BIT30_SEQUENCE_VA:X}",
            "instruction": "bts eax, 0x1e",
            "classification": "dynamic keyword-ID namespace encoding",
            "reason": (
                "The bit is applied to a dynamically returned keyword ID inside "
                "the string-registration function, alongside mutually exclusive "
                "bit-31 and bit-30-plus-31 encodings. It is not a write to a "
                "built-in keyword-set lane and cannot prove ordinal 30 selection."
            ),
        },
        "selectionConsequence": (
            "Static registry ownership, the default seed, and the apparent bit-30 "
            "site do not close the retail M28 draw discriminator."
        ),
    }


def validate_instance_contract() -> dict[str, object]:
    program = json.loads(PROGRAM_REPORT.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    require(program.get("status") ==
            "exact_program_pairs_validated_unity_admission_fail_closed",
            "M28 program report is not exact/current")
    require(source.get("status") == "exact_material_and_two_source_tuples_closed",
            "M28 source report is not exact/current")
    programs = {Path(row["file"]).name: row for row in program["programs"]}
    vertex = programs["0624_endfield_dxbc_0.dxbc"]
    fragment = programs["0625_endfield_dxbc_1.dxbc"]
    vertex_cb = {row["register"]: row for row in vertex["constantBuffers"]}
    fragment_cb = {row["register"]: row for row in fragment["constantBuffers"]}
    require(vertex_cb[3]["float4Count"] == 4094 and vertex_cb[3]["dynamicIndexed"],
            "instanced vertex b3 declaration drifted")
    require(fragment_cb[2]["float4Count"] == 4085 and fragment_cb[2]["dynamicIndexed"],
            "instanced fragment b2 declaration drifted")
    require(any(row["semantic"] == "SV_InstanceID" for row in vertex["inputs"]),
            "instanced vertex signature lost SV_InstanceID")
    consumers = source.get("consumers", [])
    require(len(consumers) == 2, "M28 exact consumer count drifted")
    for row in consumers:
        renderer = row["renderer"]
        require(renderer["sourceEnabled"] is True and renderer["gpuInstancing"] is True,
                "M28 source renderer instancing state drifted")
        require(renderer["hgGpuInstancing"] is False and
                renderer["vertexStreams"]["serialized"] == [0, 1, 3, 4, 5, 34],
                "M28 source renderer stream state drifted")
        particle = row["particleSystem"]
        require(particle["burst"]["count"] == 1,
                "M28 source burst count drifted")
    stride = 16
    capacity = 256
    require((capacity - 1) * stride + 13 + 1 == 4094,
            "instanced vertex array capacity equation drifted")
    require((capacity - 1) * stride + 4 + 1 == 4085,
            "instanced fragment array capacity equation drifted")
    return {
        "recordFloat4Count": stride,
        "recordBytes": stride * 16,
        "instanceIdInclusive": [0, capacity - 1],
        "capacity": capacity,
        "vertexHighestLane": 13,
        "fragmentLodLane": "c4.y",
        "shaderSideBaseOffset": False,
        "batchingConsequence": (
            "D3D11 SV_InstanceID directly indexes one 256-byte record; more than "
            "256 instances require CPU-side split/rebind or buffer rebasing."
        ),
        "sourceConsumerBurstCount": 1,
        "oneInstanceSelectionBoundary": (
            "Instance 0 makes the instanced and non-instanced per-object lanes "
            "numerically compatible; it does not prove which pair was selected."
        ),
    }


def build(unity_player: Path, gate: common.InstalledNativeInputs) -> dict[str, object]:
    data = unity_player.read_bytes()
    require(len(data) == UNITY_PLAYER_BYTES, "UnityPlayer byte size drifted")
    require(sha256_bytes(data) == UNITY_PLAYER_SHA256, "UnityPlayer SHA-256 drifted")
    image_base, timestamp, sections = pe_layout(data)
    require(image_base == IMAGE_BASE, "UnityPlayer image base drifted")
    require(timestamp == UNITY_PLAYER_TIMESTAMP, "UnityPlayer timestamp drifted")
    names = read_keyword_table(
        data,
        KEYWORD_TABLE_OFFSET,
        KEYWORD_TABLE_COUNT,
        lambda pointer: va_to_offset(pointer, image_base, sections),
    )
    require(KEYWORD_TABLE_OFFSET + SRP_KEYWORD_ORDINAL * KEYWORD_ENTRY_BYTES ==
            SRP_KEYWORD_ENTRY_OFFSET, "SRP keyword entry arithmetic drifted")
    for ordinal, expected in EXPECTED_KEYWORD_NEIGHBORS.items():
        require(names[ordinal] == expected,
                f"built-in keyword {ordinal} drifted: {names[ordinal]}")
    require(names.count("SRP_INSTANCING_ON") == 1,
            "SRP_INSTANCING_ON is not unique in the built-in table")
    require(data.count(b"SRP_INSTANCING_ON\0") == 1,
            "SRP_INSTANCING_ON string occurrence count drifted")
    selection_search = validate_native_selection_search(
        data, image_base, sections, names
    )

    return {
        "schema": "endfield.endminf-m28-native-instancing.v1",
        "status": "keyword_and_instance_shape_closed_pair_selection_undetermined",
        "nativeEvidence": {
            "gate": gate.status,
            "gameAssemblySha256": gate.gameassembly_sha256,
            "metadataSha256": gate.metadata_sha256,
            "unityPlayer": {
                "name": unity_player.name,
                "bytes": len(data),
                "sha256": UNITY_PLAYER_SHA256,
                "timeDateStamp": f"0x{timestamp:08X}",
                "imageBase": f"0x{image_base:X}",
            },
        },
        "builtInKeywordTable": {
            "ownership": "HyperGryph-modified UnityPlayer native built-in keywords",
            "fileOffset": f"0x{KEYWORD_TABLE_OFFSET:X}",
            "entryBytes": KEYWORD_ENTRY_BYTES,
            "entryCount": KEYWORD_TABLE_COUNT,
            "srpInstancingOrdinalZeroBased": SRP_KEYWORD_ORDINAL,
            "srpInstancingEntryFileOffset": f"0x{SRP_KEYWORD_ENTRY_OFFSET:X}",
            "neighbors": [
                {"ordinal": ordinal, "name": names[ordinal]}
                for ordinal in sorted(EXPECTED_KEYWORD_NEIGHBORS)
            ],
            "conclusion": (
                "SRP_INSTANCING_ON is a native UnityPlayer built-in keyword, not "
                "a managed HGRP/material keyword; pair selection must be recovered "
                "from UnityPlayer draw submission."
            ),
        },
        "instanceContract": validate_instance_contract(),
        "nativeSelectionSearch": selection_search,
        "selection": {
            "selectedPair": "undetermined",
            "admitted": False,
            "closed": [
                "both complete D3D11 pair programs",
                "native built-in keyword identity and ordinal",
                "keyword registry/accessor ownership and the stereo-only default seed",
                "rejection of the keyword-ID bit-30 false positive",
                "256-byte instance record, capacity 256, and no shader-side base",
                "both source renderers use one-particle mesh GPU instancing",
            ],
            "open": [
                "UnityPlayer discriminator that enables built-in ordinal 30",
                "retail ParserBindChannels/default BLEND and TEXCOORD4 publication",
                "VertexSkinMatrices and unnamed per-object record producer",
            ],
            "rejectedInferences": [
                "m_EnableGPUInstancing=true alone",
                "material m_EnableInstancingVariants=false",
                "one-particle batch size",
                "existence of the SRP-instanced program",
            ],
        },
        "nextNativeGate": (
            "Recover and body-hash the UnityPlayer draw discriminator that toggles "
            "built-in keyword ordinal 30, then evaluate it against the exact M28 "
            "renderer tuple without changing admission."
        ),
        "protectedControls": {
            "overview_02/all/shitou (1)": "M21 exact crystal; untouched",
            "overview_02/all/suikuai (1)": "exact refract shards; untouched",
            "overview_02/all/suikuai (2)": "M27 LitEffect; untouched",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    gate = common.check_installed_native_inputs(
        REVERSE_GAMEASSEMBLY_SHA256,
        REVERSE_METADATA_SHA256,
    )
    if not gate.validated:
        required = common.native_evidence_required()
        print(common.native_evidence_skip_message(
            "audit_endminf_m28_native_instancing", gate, required=required
        ), file=sys.stderr)
        return 1 if required else 0
    unity_player = gate.gameassembly.parent / "UnityPlayer.dll"
    try:
        payload = json.dumps(build(unity_player, gate), indent=2) + "\n"
    except (OSError, ValueError, struct.error, AuditError) as exc:
        print(f"audit_endminf_m28_native_instancing: FAIL: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != payload:
            print(f"audit_endminf_m28_native_instancing: stale report: {OUTPUT}",
                  file=sys.stderr)
            return 1
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(payload, encoding="utf-8")
    print("audit_endminf_m28_native_instancing: OK "
          f"ordinal={SRP_KEYWORD_ORDINAL} selection=undetermined")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
