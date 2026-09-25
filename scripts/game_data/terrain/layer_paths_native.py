"""Validate selected UnityPlayer Terrain layer and tile path construction."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.terrain-layer-paths-native-contract.v7"
DEFAULT_CONTRACT = CONTRACTS_DIR / "terrain_layer_paths_native.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/terrain/layer_paths_native.json"


def _rva(value: Any) -> int:
    return int(str(value), 0)


def verify_literal_load(pe: Any, row: dict[str, Any], *, start: int, end: int) -> dict[str, Any]:
    """Check one 7-byte RIP-relative LEA and its exact NUL-terminated target."""
    load_rva = _rva(row["loadRva"])
    literal_rva = _rva(row["literalRva"])
    if not start <= load_rva <= end - 7:
        raise ValueError(f"{row.get('family')}.load-outside-function")
    instruction = pe.bytes_at_va(pe.image_base + load_rva, 7)
    if (len(instruction) != 7 or instruction[0] not in (0x48, 0x4C)
            or instruction[1] != 0x8D or instruction[2] & 0xC7 != 0x05):
        raise ValueError(f"{row.get('family')}.not-rip-relative-lea")
    target_rva = load_rva + 7 + struct.unpack_from("<i", instruction, 3)[0]
    if target_rva != literal_rva:
        raise ValueError(
            f"{row.get('family')}.literal-target:expected=0x{literal_rva:x},actual=0x{target_rva:x}"
        )
    actual = pe.c_string_at_va(pe.image_base + literal_rva)
    if actual != row["template"]:
        raise ValueError(
            f"{row.get('family')}.literal:expected={row['template']!r},actual={actual!r}"
        )
    return {
        "family": row["family"],
        "template": actual,
        "literalRva": row["literalRva"],
        "loadRva": row["loadRva"],
        "loadBytes": instruction.hex().upper(),
    }


def _direct_call_target(pe: Any, call_rva: int) -> int:
    instruction = pe.bytes_at_va(pe.image_base + call_rva, 5)
    if len(instruction) != 5 or instruction[0] != 0xE8:
        raise ValueError(f"call:expected-direct-rel32-at=0x{call_rva:x}")
    return call_rva + 5 + struct.unpack_from("<i", instruction, 1)[0]


def _expect_instruction(
    pe: Any, rva: int, expected: bytes, label: str, *, start: int, end: int,
) -> None:
    if not start <= rva <= end - len(expected):
        raise ValueError(f"{label}:outside-function")
    actual = pe.bytes_at_va(pe.image_base + rva, len(expected))
    if actual != expected:
        raise ValueError(
            f"{label}:expected={expected.hex().upper()},actual={actual.hex().upper()}"
        )


def _verify_pdata_window(pe: Any, extents: dict[int, int], window: dict[str, Any], label: str) -> tuple[int, int]:
    start, end = _rva(window["startRva"]), _rva(window["endRva"])
    if end <= start or extents.get(pe.image_base + start) != pe.image_base + end:
        raise ValueError(f"{label}:pdata-extent-differs")
    actual = pe.bytes_at_va(pe.image_base + start, end - start)
    if hashlib.sha256(actual).hexdigest().upper() != str(window["sha256"]).upper():
        raise ValueError(f"{label}:sha256-differs")
    return start, end


def _conditional_branch_target(pe: Any, rva: int) -> int:
    prefix = pe.bytes_at_va(pe.image_base + rva, 2)
    if prefix == b"\x0f\x84":
        return rva + 6 + struct.unpack("<i", pe.bytes_at_va(pe.image_base + rva + 2, 4))[0]
    if prefix[:1] == b"\x74":
        return rva + 2 + struct.unpack("<b", prefix[1:])[0]
    raise ValueError(f"routine-context:expected-je-at=0x{rva:x}")


def verify_routine_context(
    pe: Any, spec: dict[str, Any], extents: dict[int, int], *, path_start: int, path_end: int,
) -> dict[str, Any]:
    """Prove that the path window is a continuation between entry and epilogue."""
    entry_start, entry_end = _verify_pdata_window(pe, extents, spec["entryWindow"], "routine-entry")
    prelude_start, prelude_end = _verify_pdata_window(
        pe, extents, spec["preludeWindow"], "routine-prelude"
    )
    epilogue_start, epilogue_end = _verify_pdata_window(
        pe, extents, spec["epilogueWindow"], "routine-epilogue"
    )
    if not (entry_end == prelude_start and prelude_end == path_start
            and path_end == epilogue_start):
        raise ValueError("routine-context:noncontiguous-windows")
    prologue = bytes.fromhex(spec["entryPrologueBytesHex"])
    _expect_instruction(
        pe, entry_start, prologue, "routine-context:entry-prologue",
        start=entry_start, end=entry_end,
    )
    epilogue = bytes.fromhex(spec["epilogueBytesHex"])
    _expect_instruction(
        pe, epilogue_start, epilogue, "routine-context:epilogue",
        start=epilogue_start, end=epilogue_end,
    )
    entry_exit = _rva(spec["entryExitBranchRva"])
    prelude_to_paths = _rva(spec["preludeToPathsBranchRva"])
    if (not entry_start <= entry_exit < entry_end
            or _conditional_branch_target(pe, entry_exit) != epilogue_start):
        raise ValueError("routine-context:entry-exit-target")
    if (not prelude_start <= prelude_to_paths < prelude_end
            or _conditional_branch_target(pe, prelude_to_paths) != path_start):
        raise ValueError("routine-context:prelude-to-paths-target")
    return {
        "entryRva": spec["entryWindow"]["startRva"],
        "pathContinuationRva": hex(path_start),
        "epilogueRva": spec["epilogueWindow"]["startRva"],
    }


def verify_terrain_tile_formatter(
    pe: Any, spec: dict[str, Any], extents: dict[int, int],
) -> dict[str, Any]:
    """Check the helper's root/high/low/middle argument vector and bridge."""
    start, end = _verify_pdata_window(pe, extents, spec["helperWindow"], "tile-formatter")
    bridge_start, bridge_end = _verify_pdata_window(
        pe, extents, spec["bridgeWindow"], "tile-formatter-bridge"
    )
    operations = (
        ("frameRva", b"\x4c\x8b\xdc\x53\x48\x83\xec\x60", "frame"),
        ("highLoadRva", b"\x41\x8b\x01", "high-load"),
        ("rootStoreRva", b"\x4d\x89\x43\xd0", "root-store"),
        ("highStoreRva", b"\x89\x44\x24\x40", "high-store"),
        ("lowPointerLoadRva", b"\x48\x8b\x84\x24\x90\x00\x00\x00", "low-pointer"),
        ("lowLoadRva", b"\x44\x8b\x00", "low-load"),
        ("middlePointerLoadRva", b"\x48\x8b\x84\x24\x98\x00\x00\x00", "middle-pointer"),
        ("lowStoreRva", b"\x45\x89\x43\xe0", "low-store"),
        ("middleLoadRva", b"\x44\x8b\x00", "middle-load"),
        ("middleStoreRva", b"\x45\x89\x43\xe8", "middle-store"),
        ("vectorPointerRva", b"\x4d\x8d\x43\xc8", "vector-pointer"),
    )
    positions = [_rva(spec[key]) for key, _, _ in operations]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError("tile-formatter:operation-order")
    for key, expected, label in operations:
        _expect_instruction(
            pe, _rva(spec[key]), expected, f"tile-formatter:{label}",
            start=start, end=end,
        )
    bridge_call = _rva(spec["bridgeCallRva"])
    if not start <= bridge_call <= end - 5 or _direct_call_target(pe, bridge_call) != bridge_start:
        raise ValueError("tile-formatter:bridge-target")
    parser_call = _rva(spec["parserCallRva"])
    if (not bridge_start <= parser_call <= bridge_end - 5
            or _direct_call_target(pe, parser_call) != _rva(spec["parserCallTargetRva"])):
        raise ValueError("tile-formatter-bridge:parser-target")
    return {
        "formatArgumentOrder": ["root", "high4", "low14", "middle14"],
        "argumentVectorOffsets": {"root": 8, "high4": 16, "low14": 24, "middle14": 32},
        "bridgeCallRva": spec["bridgeCallRva"],
        "parserCallRva": spec["parserCallRva"],
    }


def verify_path_forwarding(
    pe: Any, row: dict[str, Any], targets: dict[str, Any], *,
    numeric_argument_stack_offset: int, start: int, end: int,
) -> dict[str, Any]:
    """Check one template store, formatter call and common-helper argument flow."""
    family = row["family"]
    load = _rva(row["loadRva"])
    store = _rva(row["templateStoreRva"])
    index_argument = _rva(row["formatIndexArgumentRva"])
    argument = _rva(row["formatArgumentRva"])
    formatter = _rva(row["formatCallRva"])
    destination = _rva(row["destinationPointerRva"])
    consumer = _rva(row["consumeCallRva"])
    stack_offset = _rva(row["formatStackOffset"])
    slot_offset = _rva(row["destinationPointerOffset"])
    if not (start <= load < store < index_argument < argument < formatter
            < destination < consumer <= end - 5):
        raise ValueError(f"{family}.forwarding-order-or-function-bounds")
    store_bytes = bytes.fromhex(row["templateStoreBytesHex"])
    if len(store_bytes) != 5 or pe.bytes_at_va(pe.image_base + store, 5) != store_bytes:
        raise ValueError(f"{family}.template-store-bytes")
    if (not 0 <= numeric_argument_stack_offset <= 0x7F
            or pe.bytes_at_va(pe.image_base + index_argument, 4)
            != b"\x4c\x8d\x4d" + bytes((numeric_argument_stack_offset,))):
        raise ValueError(f"{family}.format-index-argument")
    if not 0 <= stack_offset <= 0x7F or not 0 <= slot_offset <= 0x7F:
        raise ValueError(f"{family}.forwarding-offset-range")
    argument_bytes = b"\x48\x8d\x54\x24" + bytes((stack_offset,))
    if formatter == argument + 9:
        argument_bytes += b"\x48\x8d\x4d\x98"
    if (formatter != argument + len(argument_bytes)
            or pe.bytes_at_va(pe.image_base + argument, len(argument_bytes)) != argument_bytes):
        raise ValueError(f"{family}.format-argument")
    if _direct_call_target(pe, formatter) != _rva(targets["formatCallTargetRva"]):
        raise ValueError(f"{family}.format-call-target")
    forwarded = b"\x4c\x8d\x43" + bytes((slot_offset,)) + b"\x48\x8b\xd0\x48\x8d\x4d\x48"
    if (destination != formatter + 5 or consumer != destination + len(forwarded)
            or pe.bytes_at_va(pe.image_base + destination, len(forwarded)) != forwarded):
        raise ValueError(f"{family}.destination-forwarding")
    if _direct_call_target(pe, consumer) != _rva(targets["consumeCallTargetRva"]):
        raise ValueError(f"{family}.consume-call-target")
    return {
        "destinationPointerOffset": row["destinationPointerOffset"],
        "formatCallRva": row["formatCallRva"],
        "consumeCallRva": row["consumeCallRva"],
    }


def verify_record_assembly(
    pe: Any, spec: dict[str, Any], paths: list[dict[str, Any]], *,
    start: int, end: int,
) -> dict[str, Any]:
    """Check allocation, the common numeric argument, result slots and append."""
    staged = _rva(spec["numericArgumentLoadAndStageRva"])
    setup = _rva(spec["allocationSetupRva"])
    allocation = _rva(spec["allocationCallRva"])
    capture = _rva(spec["allocatedPointerCaptureRva"])
    initialize = _rva(spec["destinationSlotInitRva"])
    local_store = _rva(spec["localPointerStoreRva"])
    numeric_store = _rva(spec["numericArgumentStoreRva"])
    append_argument = _rva(spec["appendArgumentRva"])
    append_call = _rva(spec["appendCallRva"])
    numeric_stack = _rva(spec["numericArgumentStackOffset"])
    local_stack = _rva(spec["localPointerStackOffset"])
    collection_offset = _rva(spec["appendCollectionOffset"])
    slot_offsets = sorted(_rva(row["destinationPointerOffset"]) for row in paths)
    if not (start <= staged < setup < allocation < capture < initialize
            < local_store < numeric_store < min(_rva(row["formatCallRva"]) for row in paths)
            < max(_rva(row["consumeCallRva"]) for row in paths)
            < append_argument < append_call <= end - 5):
        raise ValueError("record-assembly:order-or-function-bounds")
    if any(not 0 <= value <= 0x7F for value in
           (numeric_stack, local_stack, collection_offset, *slot_offsets)):
        raise ValueError("record-assembly:offset-range")
    stage_bytes = b"\x8b\x30\x89\x75" + bytes((numeric_stack,))
    if pe.bytes_at_va(pe.image_base + staged, len(stage_bytes)) != stage_bytes:
        raise ValueError("record-assembly:numeric-argument-stage")
    setup_bytes = pe.bytes_at_va(pe.image_base + setup, 11)
    if (len(setup_bytes) != 11 or setup_bytes[:2] != b"\x41\xb8"
            or setup_bytes[6:7] != b"\xb9"
            or struct.unpack_from("<I", setup_bytes, 2)[0] != spec["alignmentBytes"]
            or struct.unpack_from("<I", setup_bytes, 7)[0] != spec["recordBytes"]):
        raise ValueError("record-assembly:allocation-size-or-alignment")
    if _direct_call_target(pe, allocation) != _rva(spec["allocatorRva"]):
        raise ValueError("record-assembly:allocator-target")
    if pe.bytes_at_va(pe.image_base + capture, 3) != b"\x48\x8b\xd8":
        raise ValueError("record-assembly:allocated-pointer-capture")
    init_bytes = b"".join(
        b"\x48\xc7\x40" + bytes((offset,)) + b"\x01\x00\x00\x00"
        for offset in slot_offsets
    )
    if pe.bytes_at_va(pe.image_base + initialize, len(init_bytes)) != init_bytes:
        raise ValueError("record-assembly:destination-slot-initialization")
    if pe.bytes_at_va(pe.image_base + local_store, 4) != b"\x48\x89\x5d" + bytes((local_stack,)):
        raise ValueError("record-assembly:local-pointer-store")
    if pe.bytes_at_va(pe.image_base + numeric_store, 2) != b"\x89\x33":
        raise ValueError("record-assembly:numeric-argument-record-store")
    append_bytes = (
        b"\x48\x8d\x4f" + bytes((collection_offset,))
        + b"\x48\x8d\x55" + bytes((local_stack,))
    )
    if (append_call != append_argument + len(append_bytes)
            or pe.bytes_at_va(pe.image_base + append_argument, len(append_bytes))
            != append_bytes):
        raise ValueError("record-assembly:append-argument")
    if _direct_call_target(pe, append_call) != _rva(spec["appendCallTargetRva"]):
        raise ValueError("record-assembly:append-call-target")
    return {
        "recordBytes": spec["recordBytes"],
        "alignmentBytes": spec["alignmentBytes"],
        "numericPathArgumentRecordOffset": 0,
        "destinationPointerOffsets": {
            row["family"]: row["destinationPointerOffset"] for row in paths
        },
        "appendCollectionOffset": spec["appendCollectionOffset"],
    }


def verify_terrain_tile_path(
    pe: Any, row: dict[str, Any], spec: dict[str, Any], *, start: int, end: int,
) -> dict[str, Any]:
    """Check a tile template's root, formatter and result-slot forwarding."""
    family = str(row["family"])
    load = _rva(row["loadRva"])
    root = _rva(row["rootPointerRva"])
    store = _rva(row["templateStoreRva"])
    high_argument = _rva(row["highArgumentRva"])
    formatter = _rva(row["formatCallRva"])
    destination = _rva(row["destinationPointerRva"])
    consumer = _rva(row["consumeCallRva"])
    slot = _rva(row["destinationPointerOffset"])
    owner_stack = _rva(spec["ownerPointerStackOffset"])
    high_stack = _rva(spec["highStackOffset"])
    if not (start <= load < root < store < high_argument < formatter
            < destination < consumer < _rva(spec["appendArgumentRva"]) < end):
        raise ValueError(f"{family}.tile-forwarding-order")
    if not (0 <= slot <= 0x7F and 0 <= high_stack <= 0x7F
            and 0 <= owner_stack <= 0x7F):
        raise ValueError(f"{family}.tile-forwarding-offset")
    _expect_instruction(
        pe, root, b"\x4c\x8d\x87" + struct.pack("<i", _rva(spec["rootPointerOffset"])),
        f"{family}.root-pointer", start=start, end=end,
    )
    _expect_instruction(
        pe, root + 7, b"\x48\x8d\x44\x24" + bytes((_rva(spec["middleStackOffset"]),)),
        f"{family}.middle-argument", start=start, end=end,
    )
    store_bytes = bytes.fromhex(row["templateStoreBytesHex"])
    if len(store_bytes) not in (4, 5):
        raise ValueError(f"{family}.template-store-width")
    _expect_instruction(
        pe, store, store_bytes, f"{family}.template-store", start=start, end=end,
    )
    _expect_instruction(
        pe, high_argument, b"\x4c\x8d\x4c\x24" + bytes((high_stack,)),
        f"{family}.high-argument", start=start, end=end,
    )
    _expect_instruction(
        pe, high_argument - 5, b"\x48\x89\x44\x24\x28",
        f"{family}.middle-pointer-stage", start=start, end=end,
    )
    _expect_instruction(
        pe, high_argument + 5, b"\x48\x8d\x44\x24" + bytes((_rva(spec["lowStackOffset"]),)),
        f"{family}.low-argument", start=start, end=end,
    )
    _expect_instruction(
        pe, formatter - 10, b"\x48\x89\x44\x24\x20",
        f"{family}.low-pointer-stage", start=start, end=end,
    )
    if _direct_call_target(pe, formatter) != _rva(spec["formatCallTargetRva"]):
        raise ValueError(f"{family}.tile-format-call-target")
    forwarded = (
        b"\x4c\x8d\x43" + bytes((slot,))
        + b"\x48\x8b\xd0\x48\x8d\x4d" + bytes((owner_stack,))
    )
    if destination != formatter + 5 or consumer != destination + len(forwarded):
        raise ValueError(f"{family}.tile-destination-order")
    _expect_instruction(
        pe, destination, forwarded, f"{family}.tile-destination-forwarding",
        start=start, end=end,
    )
    if _direct_call_target(pe, consumer) != _rva(spec["consumeCallTargetRva"]):
        raise ValueError(f"{family}.tile-consume-call-target")
    return {
        "destinationPointerOffset": row["destinationPointerOffset"],
        "rootPointerOffset": spec["rootPointerOffset"],
        "formatCallRva": row["formatCallRva"],
        "consumeCallRva": row["consumeCallRva"],
    }


def verify_terrain_tile_record(
    pe: Any, spec: dict[str, Any], paths: list[dict[str, Any]], *,
    start: int, end: int,
) -> dict[str, Any]:
    """Check packed tile-id extraction, six result slots and collection append."""
    source = _rva(spec["numericArgumentLoadAndStageRva"])
    allocation = _rva(spec["allocationCallRva"])
    capture = _rva(spec["allocatedPointerCaptureRva"])
    initialize = _rva(spec["destinationSlotInitRva"])
    local_store = _rva(spec["localPointerStoreRva"])
    numeric_store = _rva(spec["numericArgumentStoreRva"])
    owner_store = _rva(spec["ownerPointerStoreRva"])
    append_argument = _rva(spec["appendArgumentRva"])
    append_call = _rva(spec["appendCallRva"])
    slots = sorted(_rva(row["destinationPointerOffset"]) for row in paths)
    if (slots != [8, 16, 24, 32, 40, 48]
            or int(spec["recordBytes"]) != 56
            or not start <= source < allocation < capture < initialize < local_store
            < numeric_store < owner_store < min(_rva(row["formatCallRva"]) for row in paths)
            < max(_rva(row["consumeCallRva"]) for row in paths)
            < append_argument < append_call <= end - 5):
        raise ValueError("terrain-tile-record:shape-or-order")
    numeric_stack = _rva(spec["numericArgumentStackOffset"])
    local_stack = _rva(spec["localPointerStackOffset"])
    owner_stack = _rva(spec["ownerPointerStackOffset"])
    high_stack = _rva(spec["highStackOffset"])
    low_stack = _rva(spec["lowStackOffset"])
    middle_stack = _rva(spec["middleStackOffset"])
    if any(not 0 <= value <= 0x7F for value in
           (numeric_stack, local_stack, owner_stack, high_stack, low_stack, middle_stack)):
        raise ValueError("terrain-tile-record:stack-offset-range")
    _expect_instruction(
        pe, source, b"\x8b\x30\x89\x75" + bytes((numeric_stack,)),
        "terrain-tile-record:numeric-argument-stage", start=start, end=end,
    )
    shift_high = int(spec["highShiftBits"])
    shift_middle = int(spec["middleShiftBits"])
    mask = int(spec["lowMiddleMask"])
    if (not 0 < shift_middle < 32 or shift_high != 2 * shift_middle
            or shift_high >= 32 or mask != (1 << shift_middle) - 1):
        raise ValueError("terrain-tile-record:bitfield-shape")
    operations = (
        ("highCopyRva", b"\x8b\xd6", "high-copy"),
        ("highShiftRva", b"\xc1\xea" + bytes((shift_high,)), "high-shift"),
        ("highStoreRva", b"\x89\x54\x24" + bytes((high_stack,)), "high-store"),
        ("lowCopyRva", b"\x8b\xce", "low-copy"),
        ("lowMaskRva", b"\x81\xe1" + struct.pack("<I", mask), "low-mask"),
        ("lowStoreRva", b"\x89\x4c\x24" + bytes((low_stack,)), "low-store"),
        ("middleCopyRva", b"\x8b\xc6", "middle-copy"),
        ("middleShiftRva", b"\xc1\xe8" + bytes((shift_middle,)), "middle-shift"),
        ("middleMaskRva", b"\x25" + struct.pack("<I", mask), "middle-mask"),
        ("middleStoreRva", b"\x89\x44\x24" + bytes((middle_stack,)), "middle-store"),
    )
    for key, expected, label in operations:
        _expect_instruction(
            pe, _rva(spec[key]), expected, f"terrain-tile-record:{label}",
            start=start, end=end,
        )
    _expect_instruction(
        pe, _rva(spec["alignmentLoadRva"]),
        b"\x41\xb8" + struct.pack("<I", int(spec["alignmentBytes"])),
        "terrain-tile-record:alignment", start=start, end=end,
    )
    _expect_instruction(
        pe, _rva(spec["recordSizeLoadRva"]),
        b"\xb9" + struct.pack("<I", int(spec["recordBytes"])),
        "terrain-tile-record:allocation-size", start=start, end=end,
    )
    if _direct_call_target(pe, allocation) != _rva(spec["allocatorRva"]):
        raise ValueError("terrain-tile-record:allocator-target")
    _expect_instruction(
        pe, capture, b"\x48\x8b\xd8", "terrain-tile-record:pointer-capture",
        start=start, end=end,
    )
    _expect_instruction(
        pe, initialize,
        b"".join(
            b"\x48\xc7\x40" + bytes((offset,)) + b"\x01\x00\x00\x00"
            for offset in slots
        ),
        "terrain-tile-record:slot-initialization", start=start, end=end,
    )
    _expect_instruction(
        pe, local_store, b"\x48\x89\x5d" + bytes((local_stack,)),
        "terrain-tile-record:local-pointer", start=start, end=end,
    )
    _expect_instruction(
        pe, numeric_store, b"\x89\x33", "terrain-tile-record:packed-id-store",
        start=start, end=end,
    )
    _expect_instruction(
        pe, owner_store, b"\x48\x89\x7d" + bytes((owner_stack,)),
        "terrain-tile-record:owner-pointer", start=start, end=end,
    )
    append_bytes = (
        b"\x48\x8d\x8f" + struct.pack("<i", _rva(spec["appendCollectionOffset"]))
        + b"\x48\x8d\x55" + bytes((local_stack,))
    )
    if append_call != append_argument + len(append_bytes):
        raise ValueError("terrain-tile-record:append-order")
    _expect_instruction(
        pe, append_argument, append_bytes, "terrain-tile-record:append-arguments",
        start=start, end=end,
    )
    if _direct_call_target(pe, append_call) != _rva(spec["appendCallTargetRva"]):
        raise ValueError("terrain-tile-record:append-target")
    return {
        "recordBytes": spec["recordBytes"],
        "alignmentBytes": spec["alignmentBytes"],
        "packedArgumentRecordOffset": 0,
        "packedArgumentBits": {
            "high": [shift_high, 31],
            "middle": [shift_middle, shift_middle + mask.bit_length() - 1],
            "low": [0, mask.bit_length() - 1],
        },
        "destinationPointerOffsets": {
            row["family"]: row["destinationPointerOffset"] for row in paths
        },
        "appendCollectionOffset": spec["appendCollectionOffset"],
    }


def validate_terrain_layer_paths(
    *, game_root: Path, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Fail closed on every selected native input, function and path load."""
    try:
        contract, _ = read_reviewed_contract(
            contract_path, schema=SCHEMA, status="validated", label="terrain-layer-paths"
        )
        expected = contract["nativeInputs"]
        if not isinstance(expected, dict):
            raise ValueError("nativeInputs:not-object")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "validation_failed", "paths": [], "terrainPaths": [],
                "reason": f"contract={error}"}
    root = Path(game_root)
    gameassembly = root.parent / "GameAssembly.dll"
    metadata = root / "il2cpp_data/Metadata/global-metadata.dat"
    gate = check_installed_native_inputs(
        str(expected.get("gameAssemblySha256") or ""),
        str(expected.get("metadataSha256") or ""),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {
            "status": gate.status, "paths": [], "terrainPaths": [], "reason": gate.detail,
        }
    unity_player = root.parent / "UnityPlayer.dll"
    try:
        actual_unity_hash = sha256_file_upper(unity_player)
    except OSError as error:
        return {"status": "missing", "paths": [], "terrainPaths": [],
                "reason": f"UnityPlayer.dll={error}"}
    if actual_unity_hash != str(expected.get("unityPlayerSha256") or "").upper():
        return {"status": "mismatched", "paths": [], "terrainPaths": [],
                "reason": "UnityPlayer.dll hash differs"}
    try:
        mapper = load_native_mapper(NATIVE_MAPPER_PATH)
        pe = mapper.PeImage(unity_player)
        function_extents = mapper.pdata_function_extents(pe)
        window = contract["functionWindow"]
        start, end = _verify_pdata_window(pe, function_extents, window, "functionWindow")
        routine_context = verify_routine_context(
            pe, contract["routineContext"], function_extents,
            path_start=start, path_end=end,
        )
        tile_formatter = verify_terrain_tile_formatter(
            pe, contract["terrainTileFormatter"], function_extents,
        )
        declared_paths = contract["paths"]
        if (not isinstance(declared_paths, list) or len(declared_paths) != 3
                or {row.get("family") for row in declared_paths if isinstance(row, dict)}
                != {"C", "D", "N"}):
            raise ValueError("paths:expected-C-D-N")
        targets = contract["pathForwarding"]
        record_spec = contract["recordAssembly"]
        paths = [
            {
                **verify_literal_load(pe, row, start=start, end=end),
                **verify_path_forwarding(
                    pe, row, targets,
                    numeric_argument_stack_offset=_rva(record_spec["numericArgumentStackOffset"]),
                    start=start, end=end,
                ),
            }
            for row in declared_paths
        ]
        record_assembly = verify_record_assembly(
            pe, record_spec, declared_paths, start=start, end=end
        )
        declared_terrain_paths = contract["terrainPaths"]
        if (not isinstance(declared_terrain_paths, list)
                or len(declared_terrain_paths) != 6
                or {row.get("family") for row in declared_terrain_paths
                    if isinstance(row, dict)} != {
                        "Terrain_H", "Terrain_N", "Terrain_T", "Terrain_A",
                        "Terrain_S", "Terrain_C",
                    }):
            raise ValueError("terrainPaths:expected-H-N-T-A-S-C")
        tile_spec = contract["terrainTileRecord"]
        terrain_paths = [
            {
                **verify_literal_load(pe, row, start=start, end=end),
                **verify_terrain_tile_path(pe, row, tile_spec, start=start, end=end),
            }
            for row in declared_terrain_paths
        ]
        terrain_tile_record = verify_terrain_tile_record(
            pe, tile_spec, declared_terrain_paths, start=start, end=end,
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as error:
        return {"status": "validation_failed", "paths": [], "terrainPaths": [],
                "reason": str(error)}
    return {
        "status": "validated",
        "paths": paths,
        "terrainPaths": terrain_paths,
        "recordAssembly": record_assembly,
        "terrainTileRecord": terrain_tile_record,
        "terrainTileFormatter": tile_formatter,
        "routineContext": routine_context,
        "functionWindow": {"startRva": window["startRva"], "endRva": window["endRva"]},
        "nativeInputs": expected,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Explicit selected Endfield_Data root")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    result = validate_terrain_layer_paths(
        game_root=args.game_root, contract_path=args.contract
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    count = len(result["paths"]) + len(result["terrainPaths"])
    print(f"Terrain path loads: {result['status']}; {count} selected templates")
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
