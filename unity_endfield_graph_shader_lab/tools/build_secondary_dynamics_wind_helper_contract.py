#!/usr/bin/env python3
"""Pin the managed Wind/WindForceBlend static boundary.

This is native byte evidence for the fixed client only.  It records the two
managed helper bodies, their direct-call edges, branch targets, constants, and
the outer Wind job-buffer arithmetic.  It does not identify or execute the
Burst implementation and must not be read as a complete secondary-dynamics
solver.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
JOB_LAYOUT_PATH = SOURCE_ROOT / "secondary_dynamics_job_layout_contract.json"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_wind_helper_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_wind_helper_contract.md"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the selected native inputs no longer match."""


def _load_solver_builder() -> Any:
    path = LAB_ROOT / "tools/build_secondary_dynamics_solver_static_contract.py"
    spec = importlib.util.spec_from_file_location("secondary_wind_solver_static", path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load solver static helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STATIC = _load_solver_builder()

WIND_INDEX = 385699
WIND_FORCE_BLEND_INDEX = 385700
WIND_VA = 0x186776704
WIND_END = 0x186776B64
WIND_FORCE_BLEND_VA = 0x186776394
WIND_FORCE_BLEND_END = 0x186776704

EXPECTED_SPANS = {
    WIND_INDEX: {
        "type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "method": "Wind",
        "va": WIND_VA,
        "endVaExclusive": WIND_END,
        "bodySha256": "2aca620c9c194d06742ffcc855efd57cca85bee46a8fc972da83ff02a855b0a0",
    },
    WIND_FORCE_BLEND_INDEX: {
        "type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "method": "WindForceBlend",
        "va": WIND_FORCE_BLEND_VA,
        "endVaExclusive": WIND_FORCE_BLEND_END,
        "bodySha256": "0418400aa5d180fb7e81233ae707325e580d9881ffd519b0953e72ca9bce8796",
    },
}

# Every direct call in the two pinned spans.  The two WindForceBlend calls are
# separately labelled below because their argument setup is part of the
# evidence; retaining the complete map catches neighboring-body/span drift.
EXPECTED_CALLS = {
    WIND_INDEX: [
        (0x54, 0x180035ED0),
        (0x6C, 0x18033B9D0),
        (0x7C, 0x182F95A30),
        (0x93, 0x14077679D),
        (0x169, 0x186786388),
        (0x1A8, 0x18838DDEC),
        (0x28A, WIND_FORCE_BLEND_VA),
        (0x2BA, 0x1830E9EA0),
        (0x318, WIND_FORCE_BLEND_VA),
        (0x348, 0x1830E9EA0),
        (0x3A2, 0x1830E7A60),
        (0x3C3, 0x185396738),
        (0x3D0, 0x1800D8260),
        (0x40B, 0x10F776B15),
        (0x424, 0x1866E0F2C),
    ],
    WIND_FORCE_BLEND_INDEX: [
        (0x22, 0x19651EF03),
        (0x49, 0x182F95A30),
        (0x92, 0x184118DE0),
        (0xB8, 0x185F356E4),
        (0xE6, 0x184118DE0),
        (0x113, 0x18B297E28),
        (0x129, 0x18B297E28),
        (0x13E, 0x1858CACF0),
        (0x15E, 0x1858CAD18),
        (0x16B, 0x185EDD110),
        (0x178, 0x1853DF234),
        (0x1A8, 0x1858CACF0),
        (0x1B8, 0x1858CACF0),
        (0x1EB, 0x1858CACF0),
        (0x20A, 0x1862E3328),
        (0x22F, 0x1866AD72C),
        (0x248, 0x1830E8510),
        (0x25D, 0x185F0E3A0),
        (0x28F, 0x182EE75E0),
        (0x2C2, 0x1830E7A60),
        (0x2FA, 0x185396738),
        (0x307, 0x1800D8260),
        (0x335, 0x1866E0B88),
    ],
}

# (method-relative instruction offset, branch opcode, target-relative offset,
# durable interpretation).  Branch targets are verified from the rel8/rel32
# bytes; the interpretation intentionally remains a static boundary label.
EXPECTED_BRANCHES = {
    WIND_INDEX: [
        (0x4B, "jne", 0x60, "lazy initialization path"),
        (0x83, "jne", 0x3BE, "IFix patch path"),
        (0x176, "jle", 0x2D4, "no wind zones"),
        (0x2CE, "jl", 0x196, "wind-zone loop"),
        (0x2E0, "jbe", 0x356, "turbulence threshold skips second blend"),
        (0x3CE, "jne", 0x3D6, "IFix fallback path"),
    ],
    WIND_FORCE_BLEND_INDEX: [
        (0x50, "jne", 0x2F3, "IFix fallback path"),
        (0x68, "ja", 0x2DB, "wind-info magnitude threshold writes zero"),
    ],
}

# Each entry is (instruction offset, instruction length, operation, expected
# float32 bits).  RIP-relative target addresses and source bytes are emitted
# in the report and checked on every build.
EXPECTED_CONSTANTS = {
    WIND_INDEX: [
        (0x9C, 8, "one", 0x3F800000),
        (0xCD, 8, "wind-index-scale", 0x3B1D0B3E),
        (0xE4, 8, "wind-index-amplitude", 0x42C80000),
        (0xF6, 8, "particle-index-scale", 0x40862760),
        (0x2D9, 7, "minimum-turbulence", 0x3C23D70A),
    ],
    WIND_FORCE_BLEND_INDEX: [
        (0x5C, 8, "minimum-wind-info", 0x3C23D70A),
        (0x82, 8, "noise-frequency", 0x41200000),
        (0xCE, 8, "noise-position-scale", 0x40140B78),
        (0x12E, 8, "noise-position-bias", 0x40133333),
        (0x182, 8, "wind-angle-degrees", 0x42340000),
        (0x1AD, 8, "degrees-to-radians", 0x3C8EFA35),
        (0x1C5, 8, "turbulence-mix", 0x3ECCCCCD),
        (0x1D1, 8, "turbulence-bias", 0x3DCCCCCD),
        (0x262, 8, "one", 0x3F800000),
        (0x26E, 8, "normalization-scale", 0x40F00000),
        (0x294, 8, "subtract-one", 0xBF800000),
        (0x2A8, 8, "half", 0x3F000000),
    ],
}

EXPECTED_CONSTANT_PREFIXES = {
    WIND_INDEX: {
        0x9C: bytes.fromhex("f3 0f 10 35"),
        0xCD: bytes.fromhex("f3 0f 59 0d"),
        0xE4: bytes.fromhex("f3 0f 59 0d"),
        0xF6: bytes.fromhex("f3 0f 59 05"),
        0x2D9: bytes.fromhex("0f 2f 05"),
    },
    WIND_FORCE_BLEND_INDEX: {
        0x5C: bytes.fromhex("f3 0f 10 05"),
        0x82: bytes.fromhex("f3 0f 59 15"),
        0xCE: bytes.fromhex("f3 0f 59 15"),
        0x12E: bytes.fromhex("f3 0f 10 0d"),
        0x182: bytes.fromhex("f3 0f 10 0d"),
        0x1AD: bytes.fromhex("f3 0f 10 0d"),
        0x1C5: bytes.fromhex("f3 0f 59 1d"),
        0x1D1: bytes.fromhex("f3 0f 58 1d"),
        0x262: bytes.fromhex("f3 0f 10 15"),
        0x26E: bytes.fromhex("f3 0f 5e 1d"),
        0x294: bytes.fromhex("f3 0f 5c 3d"),
        0x2A8: bytes.fromhex("f3 0f 59 3d"),
    },
}

WIND_BUFFER_ACCESS = [
    {
        "jobField": "vertexRootIndices",
        "role": "wind-index lookup by vindex",
        "jobOffset": "0x68",
        "index": "vindex",
        "strideBytes": 4,
        "elementFieldDisplacements": [0],
        "jobLoadInstructionOffsets": ["0x89"],
        "elementInstructionOffsets": ["0xb3"],
    },
    {
        "jobField": "teamWindArray",
        "role": "zone wind-info records consumed as windInfo",
        "jobOffset": "0xa8",
        "index": "teamId",
        "strideBytes": 152,
        "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112, 128, 144],
        "strideInstructionOffsets": ["0xc6"],
        "jobLoadInstructionOffsets": ["0xdd"],
        "elementInstructionOffsets": ["0x112", "0x118", "0x120", "0x128", "0x130", "0x138", "0x140", "0x148", "0x151", "0x159"],
    },
    {
        "jobField": "windDataArray",
        "role": "aggregate wind-info records",
        "jobOffset": "0xb8",
        "index": "zoneId",
        "strideBytes": 212,
        "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208],
        "strideInstructionOffsets": ["0x1da"],
        "jobLoadInstructionOffsets": ["0x1d3"],
        "elementInstructionOffsets": ["0x1fb", "0x1fe", "0x205", "0x20d", "0x215", "0x21d", "0x225", "0x22d", "0x23f", "0x246", "0x24d", "0x255", "0x25d", "0x261"],
        "secondChunkBaseAdd": "0x80",
    },
    {
        "jobField": "frictionArray",
        "role": "pindex-dependent friction sample",
        "jobOffset": "0x158",
        "index": "pindex",
        "strideBytes": 4,
        "elementFieldDisplacements": [0],
        "jobLoadInstructionOffsets": ["0x36d"],
        "elementInstructionOffsets": ["0x384"],
    },
]

WIND_FORCE_BLEND_POINTER_ACCESS = [
    ("windInfo", "rbx", 0x56, 0x8, 4),
    ("windInfo", "rbx", 0x6E, 0x4, 4),
    ("windInfo", "rbx", 0xBD, 0x4, 4),
    ("windInfo", "rbx", 0x20F, 0xC, 8),
    ("windInfo", "rbx", 0x218, 0x14, 4),
    ("windParams", "rsi", 0x163, 0xC, 4),
    ("windParams", "rsi", 0x18A, 0x8, 4),
    ("windParams", "rsi", 0x1BD, 0xC, 4),
    ("windPos", "rdi", 0x77, 0x0, 8),
    ("windPos", "rdi", 0x7F, 0x8, 4),
    ("windPos", "rdi", 0xC6, 0x0, 8),
    ("windPos", "rdi", 0xE0, 0x8, 4),
]

WIND_FORCE_BLEND_RAW_POINTER_INSTRUCTIONS = {
    0x18A: bytes.fromhex("f3 0f 59 76 08"),
}

BLEND_CALL_SEMANTICS = [
    {
        "offset": "0x28a",
        "role": "zone_wind_info_blend",
        "windInfo": "local teamWindDataArray[zoneId] copy at rbp-0x38",
        "windParams": "Wind.windParams (r8 <- rbx)",
        "windPos": "local wind position at rbp-0x70",
        "windTurbulence": "stack +0x20 from rbp+0x98",
        "result": "stack +0x28 -> rsp+0x60 (12-byte value)",
        "setupInstructionOffsets": ["0x1b1", "0x1c0", "0x23b", "0x26f", "0x27f", "0x284"],
    },
    {
        "offset": "0x318",
        "role": "aggregate_wind_info_blend",
        "windInfo": "local aggregate wind-info copy at rbp+0x60",
        "windParams": "Wind.windParams (r8 <- rbx)",
        "windPos": "local wind position at rbp-0x70",
        "windTurbulence": "stack +0x20 from constant one (xmm6)",
        "result": "stack +0x28 -> rsp+0x60 (12-byte value)",
        "setupInstructionOffsets": ["0x2e8", "0x2f0", "0x2f8", "0x2fc", "0x305", "0x312"],
    },
]

BLEND_CALL_RAW_BYTES = {
    0x1B1: bytes.fromhex("4c 8d 4d 90"),
    0x1C0: bytes.fromhex("4c 8b c3"),
    0x23B: bytes.fromhex("48 8d 55 c8"),
    0x26F: bytes.fromhex("48 8d 44 24 60"),
    0x27F: bytes.fromhex("48 89 44 24 28"),
    0x284: bytes.fromhex("f3 0f 11 44 24 20"),
    0x2E8: bytes.fromhex("48 8d 44 24 60"),
    0x2F0: bytes.fromhex("48 89 44 24 28"),
    0x2F8: bytes.fromhex("4c 8d 4d 90"),
    0x2FC: bytes.fromhex("4c 8b c3"),
    0x305: bytes.fromhex("48 8d 55 60"),
    0x312: bytes.fromhex("f3 0f 11 74 24 20"),
}

BLEND_RESULT_RAW_BYTES = {
    "normal": {
        0x2C7: bytes.fromhex("48 8b 4d 77"),
        0x2D2: bytes.fromhex("f2 0f 11 01"),
        0x2D6: bytes.fromhex("89 51 08"),
    },
    "threshold_zero": {
        0x2DB: bytes.fromhex("48 8b 4d 77"),
        0x2E8: bytes.fromhex("f2 0f 11 01"),
        0x2EC: bytes.fromhex("f3 0f 11 51 08"),
    },
}


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _method_row(method_by_pointer: dict[int, list[dict[str, Any]]], method_index: int) -> tuple[int, dict[str, Any]]:
    rows = STATIC._register_method_rows(method_by_pointer, method_index)
    if len(rows) != 1:
        raise ContractError(f"method {method_index} resolves to {len(rows)} native pointers")
    return rows[0]


def _verify_method(
    native: Any,
    md: Any,
    pe: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    all_pointers: list[int],
    method_index: int,
) -> tuple[dict[str, Any], bytes]:
    pointer, signature = _method_row(method_by_pointer, method_index)
    expected = EXPECTED_SPANS[method_index]
    if pointer != expected["va"]:
        raise ContractError(f"method {method_index} VA drift: {_hex(pointer)} != {_hex(expected['va'])}")
    if signature.get("type") != expected["type"] or not STATIC._method_label_matches(md, method_index, expected["method"]):
        raise ContractError(f"method {method_index} metadata identity drift")
    next_pointers = [value for value in all_pointers if value > pointer]
    if not next_pointers or next_pointers[0] != expected["endVaExclusive"]:
        actual = _hex(next_pointers[0]) if next_pointers else "<none>"
        raise ContractError(f"method {method_index} span end drift: {actual} != {_hex(expected['endVaExclusive'])}")
    span = expected["endVaExclusive"] - expected["va"]
    body = pe.bytes_at_va(pointer, span)
    if len(body) != span:
        raise ContractError(f"method {method_index} span is truncated")
    actual_hash = hashlib.sha256(body).hexdigest()
    if actual_hash != expected["bodySha256"]:
        raise ContractError(f"method {method_index} hash drift: {actual_hash[:16]} != {expected['bodySha256'][:16]}")
    calls, _ = native.scan_direct_calls(pe, pointer, span, method_by_pointer, set(), include_unresolved=True, arg_context_window=0)
    call_map = [(int(call["offset"]), int(call["targetVa"], 16)) for call in calls]
    if call_map != EXPECTED_CALLS[method_index]:
        raise ContractError(f"method {method_index} direct-call map drift: {call_map!r}")
    return {
        "methodIndex": method_index,
        "type": expected["type"],
        "method": expected["method"],
        "va": _hex(pointer),
        "endVaExclusive": _hex(expected["endVaExclusive"]),
        "spanBytes": span,
        "bodySha256": actual_hash,
        "directCalls": [{"offset": _hex(offset), "targetVa": _hex(target)} for offset, target in call_map],
    }, body


def _branch_target(body: bytes, offset: int) -> tuple[str, int] | None:
    if offset < 0 or offset >= len(body):
        return None
    opcode = body[offset]
    if opcode == 0xEB or 0x70 <= opcode <= 0x7F:
        if offset + 2 > len(body):
            return None
        short_names = {0x70: "jo", 0x71: "jno", 0x72: "jb", 0x73: "jae", 0x74: "je", 0x75: "jne", 0x76: "jbe", 0x77: "ja", 0x78: "js", 0x79: "jns", 0x7A: "jp", 0x7B: "jnp", 0x7C: "jl", 0x7D: "jge", 0x7E: "jle", 0x7F: "jg"}
        return ("jmp" if opcode == 0xEB else short_names[opcode], offset + 2 + struct.unpack_from("<b", body, offset + 1)[0])
    if opcode == 0xE9:
        if offset + 5 > len(body):
            return None
        return ("jmp", offset + 5 + struct.unpack_from("<i", body, offset + 1)[0])
    if opcode == 0x0F and offset + 6 <= len(body) and 0x80 <= body[offset + 1] <= 0x8F:
        near_names = {0x80: "jo", 0x81: "jno", 0x82: "jb", 0x83: "jae", 0x84: "je", 0x85: "jne", 0x86: "jbe", 0x87: "ja", 0x88: "js", 0x89: "jns", 0x8A: "jp", 0x8B: "jnp", 0x8C: "jl", 0x8D: "jge", 0x8E: "jle", 0x8F: "jg"}
        return (near_names[body[offset + 1]], offset + 6 + struct.unpack_from("<i", body, offset + 2)[0])
    return None


def _verify_branches(body: bytes, method_index: int) -> list[dict[str, Any]]:
    rows = []
    for offset, mnemonic, target, meaning in EXPECTED_BRANCHES[method_index]:
        actual = _branch_target(body, offset)
        if actual is None or actual[1] != target or actual[0] != mnemonic:
            raise ContractError(f"method {method_index} branch {_hex(offset)} condition/target drift: actual={actual!r}, expected=({mnemonic!r}, {_hex(target)})")
        rows.append({"offset": _hex(offset), "condition": mnemonic, "targetOffset": _hex(target), "opcode": body[offset:offset + 2].hex() if body[offset] == 0x0F else body[offset:offset + 1].hex(), "meaning": meaning})
    return rows


def _verify_constants(pe: Any, body: bytes, method_index: int, va: int) -> list[dict[str, Any]]:
    rows = []
    for offset, length, meaning, bits in EXPECTED_CONSTANTS[method_index]:
        if offset + length > len(body):
            raise ContractError(f"method {method_index} constant {_hex(offset)} is out of span")
        prefix = EXPECTED_CONSTANT_PREFIXES[method_index][offset]
        if body[offset:offset + len(prefix)] != prefix:
            raise ContractError(
                f"method {method_index} constant {_hex(offset)} opcode/prefix drift: "
                f"{body[offset:offset + len(prefix)].hex()} != {prefix.hex()}"
            )
        displacement = struct.unpack_from("<i", body, offset + length - 4)[0]
        target = va + offset + length + displacement
        raw = pe.bytes_at_va(target, 4)
        if len(raw) != 4:
            raise ContractError(f"method {method_index} constant {_hex(offset)} target is outside image")
        actual_bits = struct.unpack("<I", raw)[0]
        if actual_bits != bits:
            raise ContractError(f"method {method_index} constant {_hex(offset)} drift: {_hex(actual_bits)} != {_hex(bits)}")
        rows.append({"offset": _hex(offset), "meaning": meaning, "opcodePrefix": prefix.hex(), "targetVa": _hex(target), "float32Bits": _hex(actual_bits), "float32": struct.unpack("<f", raw)[0]})
    return rows


def _verify_memory(body: bytes, method_index: int, offset: int, *, base: str | None = None, displacement: int | None = None, width: int | None = None, scale: int | None = None) -> None:
    entry = STATIC._memory_instruction(body, offset)
    if entry is None or entry.get("kind") != "memory":
        raise ContractError(f"method {method_index} memory instruction {_hex(offset)} did not decode")
    if base is not None and entry.get("base") != base:
        raise ContractError(f"method {method_index} memory {_hex(offset)} base drift: {entry.get('base')} != {base}")
    if displacement is not None and int(entry.get("displacement", 0)) != displacement:
        raise ContractError(f"method {method_index} memory {_hex(offset)} displacement drift")
    if width is not None and int(entry.get("width", 0)) != width:
        raise ContractError(f"method {method_index} memory {_hex(offset)} width drift")
    if scale is not None and int(entry.get("scale", 0)) != scale:
        raise ContractError(f"method {method_index} memory {_hex(offset)} scale drift")


def _verify_raw(body: bytes, method_index: int, offset: int, expected: bytes) -> None:
    actual = body[offset:offset + len(expected)]
    if actual != expected:
        raise ContractError(
            f"method {method_index} instruction {_hex(offset)} drift: "
            f"{actual.hex()} != {expected.hex()}"
        )


def _verify_wind_buffers(body: bytes) -> list[dict[str, Any]]:
    for access in WIND_BUFFER_ACCESS:
        job_loads = [int(value, 16) for value in access["jobLoadInstructionOffsets"]]
        for offset in job_loads:
            _verify_memory(body, WIND_INDEX, offset, base="rdi", displacement=int(access["jobOffset"], 16), width=8)
        for offset_text in access.get("strideInstructionOffsets", []):
            entry = STATIC._memory_instruction(body, int(offset_text, 16))
            if entry is None or entry.get("kind") != "imul" or int(entry.get("immediate")) != access["strideBytes"]:
                raise ContractError(f"Wind {access['jobField']} stride arithmetic drift")
        if access["jobField"] == "vertexRootIndices":
            # movd xmm1,dword ptr [rax+rcx*4]; this SIMD opcode is outside
            # the older generic memory decoder used by the solver contract.
            _verify_raw(body, WIND_INDEX, 0xB3, bytes.fromhex("66 0f 6e 0c 88"))
        elif access["jobField"] == "frictionArray":
            # subss xmm2,dword ptr [rax+rcx*4].
            _verify_raw(body, WIND_INDEX, 0x384, bytes.fromhex("f3 0f 5c 14 88"))
        _verify_wind_element_instructions(body, access)
    return WIND_BUFFER_ACCESS


def _verify_wind_element_instructions(body: bytes, access: dict[str, Any]) -> None:
    field = access["jobField"]
    offsets = [int(value, 16) for value in access.get("elementInstructionOffsets", [])]
    if field == "vertexRootIndices":
        return
    if field == "frictionArray":
        return
    expected = access["elementFieldDisplacements"]
    if field == "teamWindArray":
        widths = [16] * 9 + [8]
    elif field == "windDataArray":
        widths = [16] * 13 + [4]
    else:
        raise ContractError(f"unhandled Wind element field {field}")
    if len(offsets) != len(expected) or len(widths) != len(offsets):
        raise ContractError(f"Wind {field} element access table is internally inconsistent")
    base_adjust = 0
    raw_displacements = list(expected)
    if field == "teamWindArray":
        # The final two loads use rdx=0x80, so their raw displacements are
        # 0 and 0x10 even though their element-relative offsets are 0x80/0x90.
        raw_displacements[-2:] = [expected[-2] - 0x80, expected[-1] - 0x80]
    elif field == "windDataArray":
        # The second chunk starts after the pinned add rax,0x80 at 0x231.
        _verify_raw(body, WIND_INDEX, 0x231, bytes.fromhex("48 03 c2"))
        raw_displacements = expected[:8] + [value - 0x80 for value in expected[8:]]
    for index, (offset, displacement, width) in enumerate(zip(offsets, raw_displacements, widths)):
        actual_displacement = displacement
        _verify_memory(body, WIND_INDEX, offset, base="rax", displacement=actual_displacement, width=width)


def _canonical_wind_job_fields() -> dict[str, dict[str, Any]]:
    if not JOB_LAYOUT_PATH.is_file():
        raise ContractError(f"canonical job layout is missing: {JOB_LAYOUT_PATH}")
    payload = json.loads(JOB_LAYOUT_PATH.read_text(encoding="utf-8"))
    jobs = [row for row in payload.get("jobs", []) if row.get("type") == "BeyondDynamicBone.SimulationManager+StartSimulationStepJob"]
    if len(jobs) != 1:
        raise ContractError(f"canonical job layout expected one SimulationManager StartSimulationStepJob, found {len(jobs)}")
    result: dict[str, dict[str, Any]] = {}
    for field in jobs[0].get("fields", []):
        offset = field.get("nativePayloadOffset")
        if offset in {"0x68", "0xa8", "0xb8", "0x158"}:
            result[offset] = field
    expected_names = {"0x68": "vertexRootIndices", "0xa8": "teamWindArray", "0xb8": "windDataArray", "0x158": "frictionArray"}
    for offset, name in expected_names.items():
        field = result.get(offset)
        if field is None or field.get("name") != name:
            actual = field.get("name") if field else "<missing>"
            raise ContractError(f"canonical job layout field {offset} drift: {actual} != {name}")
    return result


def _verify_canonical_wind_job_fields() -> dict[str, dict[str, Any]]:
    canonical = _canonical_wind_job_fields()
    expected = {"0x68": ("vertexRootIndices", 4), "0xa8": ("teamWindArray", 152), "0xb8": ("windDataArray", 212), "0x158": ("frictionArray", 4)}
    for offset, (name, size) in expected.items():
        field = canonical[offset]
        element = field.get("elementType") or {}
        if int(element.get("nativeSizeBytes", -1)) != size:
            raise ContractError(f"canonical job layout {name} element size drift: {element.get('nativeSizeBytes')} != {size}")
        for access in WIND_BUFFER_ACCESS:
            if access["jobOffset"] == offset:
                if access["jobField"] != name or access["strideBytes"] != size:
                    raise ContractError(f"Wind buffer attribution drift at {offset}: {access['jobField']}/{access['strideBytes']} != {name}/{size}")
    return canonical


def _verify_blend_pointer_access(body: bytes) -> list[dict[str, Any]]:
    rows = []
    for name, base, offset, displacement, width in WIND_FORCE_BLEND_POINTER_ACCESS:
        raw = WIND_FORCE_BLEND_RAW_POINTER_INSTRUCTIONS.get(offset)
        if raw is None:
            _verify_memory(body, WIND_FORCE_BLEND_INDEX, offset, base=base, displacement=displacement, width=width)
        else:
            _verify_raw(body, WIND_FORCE_BLEND_INDEX, offset, raw)
        rows.append({"source": name, "base": base, "offset": _hex(offset), "fieldDisplacement": _hex(displacement), "widthBytes": width})
    return rows


def _verify_blend_call_setup(body: bytes) -> list[dict[str, Any]]:
    for offset, raw in BLEND_CALL_RAW_BYTES.items():
        _verify_raw(body, WIND_INDEX, offset, raw)
    rows = []
    for item in BLEND_CALL_SEMANTICS:
        setup = []
        for offset_text in item["setupInstructionOffsets"]:
            offset = int(offset_text, 16)
            setup.append({"offset": offset_text, "rawBytes": BLEND_CALL_RAW_BYTES[offset].hex()})
        row = dict(item)
        row["setupInstructions"] = setup
        rows.append(row)
    return rows


def _verify_blend_result_stores(body: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path, instructions in BLEND_RESULT_RAW_BYTES.items():
        rows = []
        for offset, raw in instructions.items():
            _verify_raw(body, WIND_FORCE_BLEND_INDEX, offset, raw)
            rows.append({"offset": _hex(offset), "rawBytes": raw.hex()})
        result[path] = rows
    return result


def build_contract(gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY, metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    evidence = check_installed_native_inputs(EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256, gameassembly=gameassembly, metadata=metadata)
    if evidence.status != "validated":
        raise ContractError(f"native evidence gate {evidence.status}: {evidence.detail}")
    native, md, pe, method_by_pointer, all_pointers = STATIC._native_indexes(evidence.metadata, evidence.gameassembly)
    canonical_fields = _verify_canonical_wind_job_fields()
    methods: dict[int, dict[str, Any]] = {}
    bodies: dict[int, bytes] = {}
    for method_index in (WIND_INDEX, WIND_FORCE_BLEND_INDEX):
        row, body = _verify_method(native, md, pe, method_by_pointer, all_pointers, method_index)
        row["branches"] = _verify_branches(body, method_index)
        row["constants"] = _verify_constants(pe, body, method_index, EXPECTED_SPANS[method_index]["va"])
        methods[method_index] = row
        bodies[method_index] = body
    methods[WIND_INDEX]["bufferAccesses"] = _verify_wind_buffers(bodies[WIND_INDEX])
    methods[WIND_INDEX]["canonicalJobLayoutSource"] = {"path": str(JOB_LAYOUT_PATH), "sha256": hashlib.sha256(JOB_LAYOUT_PATH.read_bytes()).hexdigest()}
    methods[WIND_INDEX]["canonicalJobFields"] = {
        offset: {"name": field["name"], "nativePayloadOffset": field["nativePayloadOffset"], "elementType": field.get("elementType", {}).get("name"), "elementSizeBytes": field.get("elementType", {}).get("nativeSizeBytes")}
        for offset, field in canonical_fields.items()
    }
    methods[WIND_FORCE_BLEND_INDEX]["pointerFieldAccesses"] = _verify_blend_pointer_access(bodies[WIND_FORCE_BLEND_INDEX])
    methods[WIND_INDEX]["blendCallSemantics"] = _verify_blend_call_setup(bodies[WIND_INDEX])
    result_stores = _verify_blend_result_stores(bodies[WIND_FORCE_BLEND_INDEX])
    methods[WIND_FORCE_BLEND_INDEX]["resultContract"] = {
        "normalPath": {"resultPointerStackOffset": "0x30", "writes": [{"offset": "0x0", "widthBytes": 8}, {"offset": "0x8", "widthBytes": 4}]},
        "thresholdPath": {"resultPointerStackOffset": "0x30", "writes": [{"offset": "0x0", "widthBytes": 8}, {"offset": "0x8", "widthBytes": 4}], "value": "zero"},
        "rawInstructions": result_stores,
    }
    return {
        "schema": "endfield.charinfo.secondary-dynamics-wind-helper.v1",
        "status": "native_spans_hash_pinned_wind_helpers",
        "solverStatus": "managed_helper_static_semantics_only_burst_solver_unresolved",
        "nativeGate": {
            "gameAssembly": {"path": str(evidence.gameassembly), "size": evidence.gameassembly.stat().st_size, "sha256": evidence.gameassembly_sha256},
            "globalMetadata": {"path": str(evidence.metadata), "size": evidence.metadata.stat().st_size, "sha256": evidence.metadata_sha256},
        },
        "boundary": "Wind/WindForceBlend are managed helper bodies reached by the indexed Execute fallback. This contract does not instantiate jobs, execute Burst, or claim full solver equivalence.",
        "methods": [methods[WIND_INDEX], methods[WIND_FORCE_BLEND_INDEX]],
    }


def _markdown(contract: dict[str, Any]) -> str:
    lines = ["# Secondary dynamics Wind helper static boundary", "", f"Status: `{contract['status']}`.", "", contract["solverStatus"], "", "| Method | Span | Branches | Constants | Direct calls |", "|---|---:|---:|---:|---:|"]
    for row in contract["methods"]:
        lines.append(f"| {row['methodIndex']} `{row['method']}` | `{row['va']}..{row['endVaExclusive']}` ({row['spanBytes']} B) | {len(row['branches'])} | {len(row['constants'])} | {len(row['directCalls'])} |")
    lines += ["", "Wind copies job-owned wind-index (4-byte), wind-data (0x98-byte), team-wind-data (0xd4-byte), and depth (4-byte) records before the two statically verified WindForceBlend calls. WindForceBlend has explicit minimum-magnitude and IFix branches and writes a 12-byte result; Burst dispatch and runtime behavior remain unresolved.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true", help="verify checked-in outputs without writing")
    args = parser.parse_args()
    try:
        contract = build_contract(args.gameassembly, args.metadata)
    except ContractError as exc:
        print(f"[secondary-dynamics-wind] {exc}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or not args.markdown.is_file():
            print("[secondary-dynamics-wind] checked-in output is missing", file=sys.stderr)
            return 2
        if json.loads(args.output.read_text(encoding="utf-8")) != contract or args.markdown.read_text(encoding="utf-8") != _markdown(contract):
            print("[secondary-dynamics-wind] checked-in output is stale", file=sys.stderr)
            return 2
        print(f"checked {args.output} and {args.markdown}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(contract), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
