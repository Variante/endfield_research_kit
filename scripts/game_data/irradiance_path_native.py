"""Validate the selected IrradianceVolume V3 path and native cursor chain.

This proves selected scene/Gacha index-file suffix construction, one
serialized proxy source route, a path-keyed stream-buffer pointer handoff,
the selected queued request's exact-read outer I/O gate, and the absence of a
final EOF comparison in the selected parser body. It also checks the room
header, copied-record command binding and count-sized virtual dispatch. The
default provider's OS-file method set is a conditional registry fallback. Its
selected runtime provider and concrete VFS source remain unresolved.
The reviewed contract pins the selected native inputs and instruction windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, NativeImage, read_reviewed_contract
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import load_native_mapper, runtime_type_field_offsets
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.irradiance-v3-path-native-contract.v13"
DEFAULT_CONTRACT = CONTRACTS_DIR / "irradiance_v3_path_native.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/irradiance/v3_path_native.json"


def _int(value: str | int) -> int:
    return int(str(value), 0)


def _rel_target(pe: Any, rva: int, opcode: int) -> int:
    raw = pe.bytes_at_va(pe.image_base + rva, 5)
    if raw[0] != opcode:
        raise ValueError(f"irradiance.path:expected-opcode={opcode:02X},rva=0x{rva:X}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _check_region_room_path(pe: Any, extents: dict[int, int],
                            contract: dict[str, Any]) -> dict[str, Any]:
    """Check a selected room-name format and its bounded stream-request branch."""
    block = contract["nativeRegionRoomPath"]
    window = block["codeWindow"]
    start, end = _int(window["startRva"]), _int(window["endRva"])
    if extents.get(start) != end:
        raise ValueError("irradiance.path:region-room-pdata")
    raw = pe.bytes_at_va(pe.image_base + start, end - start)
    if hashlib.sha256(raw).hexdigest().upper() != window["sha256"].upper():
        raise ValueError("irradiance.path:region-room-window")
    literal_rva = _int(block["literalRva"])
    literal = block["literalAscii"].encode("ascii") + b"\0"
    if pe.bytes_at_va(pe.image_base + literal_rva, len(literal)) != literal:
        raise ValueError("irradiance.path:region-room-literal")
    load_rva = _int(block["literalLoadRva"])
    load = bytes.fromhex(block["literalLoadHex"])
    if (len(load) != 7 or load[:3] != b"\x48\x8d\x15"
            or pe.bytes_at_va(pe.image_base + load_rva, len(load)) != load
            or load_rva + 7 + struct.unpack_from("<i", load, 3)[0] != literal_rva):
        raise ValueError("irradiance.path:region-room-literal-load")
    calls = (("format", "formatCallRva", "formatTargetRva"),
             ("lookup", "lookupCallRva", "lookupTargetRva"),
             ("stream", "streamConstructionCallRva", "streamConstructionTargetRva"))
    sites = [load_rva]
    for label, site_key, target_key in calls:
        site, target = _int(block[site_key]), _int(block[target_key])
        if _rel_target(pe, site, 0xE8) != target:
            raise ValueError(f"irradiance.path:region-room-{label}-call")
        sites.append(site)
    if sites != sorted(sites) or not all(start <= site < end - 5 for site in sites):
        raise ValueError("irradiance.path:region-room-call-order")
    joined_calls = {row["role"]: _int(row["targetRva"])
                    for row in contract["nativeBufferJoin"]["calls"]}
    if (_int(block["lookupTargetRva"]) != joined_calls["path-keyed lookup"]
            or _int(block["streamConstructionTargetRva"]) != joined_calls["stream construction"]):
        raise ValueError("irradiance.path:region-room-shared-stream-targets")
    gate_rva = _int(block["lookupSuccessGateRva"])
    gate = bytes.fromhex(block["lookupSuccessGateHex"])
    if (gate_rva != _int(block["lookupCallRva"]) + 5 or gate != b"\x84\xc0\x74\x1c"
            or pe.bytes_at_va(pe.image_base + gate_rva, len(gate)) != gate
            or gate_rva + len(gate) + struct.unpack_from("<b", gate, 3)[0]
            <= _int(block["streamConstructionCallRva"])):
        raise ValueError("irradiance.path:region-room-lookup-gate")
    return {"literal": block["literalAscii"], "formatCallRva": block["formatCallRva"],
            "lookupCallRva": block["lookupCallRva"],
            "streamConstructionCallRva": block["streamConstructionCallRva"],
            "boundary": block["boundary"]}


def _check_region_room_parse(pe: Any, extents: dict[int, int],
                             contract: dict[str, Any]) -> dict[str, Any]:
    """Authenticate the selected ready-buffer room header and record copy."""
    block = contract["nativeRegionRoomParse"]
    room_window = contract["nativeRegionRoomPath"]["codeWindow"]
    room_start, room_end = _int(room_window["startRva"]), _int(room_window["endRva"])
    if _int(block["roomFunctionStartRva"]) != room_start or extents.get(room_start) != room_end:
        raise ValueError("irradiance.path:region-room-parse-function")
    if {row["role"] for row in block["codeWindows"]} != {
            "twelve-byte triple cursor leaf", "record byte-copy helper"}:
        raise ValueError("irradiance.path:region-room-parse-window-roles")
    for row in block["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if row["role"] == "record byte-copy helper" and extents.get(start) != end:
            raise ValueError(f"irradiance.path:region-room-parse-pdata={row['role']}")
        raw = pe.bytes_at_va(pe.image_base + start, end - start)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise ValueError(f"irradiance.path:region-room-parse-window={row['role']}")
    window_starts = {row["role"]: _int(row["startRva"]) for row in block["codeWindows"]}
    if {row["role"] for row in block["instructions"]} != {
            "cursor starts at byte four after magic",
            "ready buffer and magic 0x1000 gate",
            "header size then two twelve-byte triples",
            "three dimensions and header-sized record start",
            "selected eight-or-sixteen bytes per grid cell",
            "record source, byte count, destination and copy call"}:
        raise ValueError("irradiance.path:region-room-parse-instruction-roles")
    for row in block["instructions"]:
        rva, raw = _int(row["rva"]), bytes.fromhex(row["hex"])
        if not room_start <= rva < rva + len(raw) <= room_end:
            raise ValueError(f"irradiance.path:region-room-parse-instruction-range={row['role']}")
        if pe.bytes_at_va(pe.image_base + rva, len(raw)) != raw:
            raise ValueError(f"irradiance.path:region-room-parse-instruction={row['role']}")
    calls = {row["role"]: (_int(row["callRva"]), _int(row["targetRva"]))
             for row in block["calls"]}
    if set(calls) != {"ready status", "ready buffer pointer", "header size",
                      "first triple", "second triple", "first grid dimension",
                      "second grid dimension", "third grid dimension", "record byte copy"}:
        raise ValueError("irradiance.path:region-room-parse-call-roles")
    shared_calls = {row["role"]: _int(row["targetRva"])
                    for row in contract["nativeStreamFill"]["calls"]}
    if (calls["ready status"][1] != shared_calls["parser ready status"]
            or calls["ready buffer pointer"][1] != shared_calls["parser buffer pointer"]
            or any(calls[role][1] != _int(contract["nativeIndexCursor"]["cursorReadRva"])
                   for role in ("header size", "first grid dimension",
                                "second grid dimension", "third grid dimension"))
            or calls["first triple"][1] != window_starts["twelve-byte triple cursor leaf"]
            or calls["second triple"][1] != calls["first triple"][1]
            or calls["record byte copy"][1] != window_starts["record byte-copy helper"]):
        raise ValueError("irradiance.path:region-room-parse-shared-targets")
    for role, (site, target) in calls.items():
        if not room_start <= site < room_end - 5 or _rel_target(pe, site, 0xE8) != target:
            raise ValueError(f"irradiance.path:region-room-parse-call={role}")
    return {"magicWord": "0x00001000", "cursorStart": 4,
            "gridRecordBytes": [8, 16], "boundary": block["boundary"]}


def _check_region_room_assembly(pe: Any, contract: dict[str, Any]) -> dict[str, Any]:
    """Check the selected supplied-root directory and room-basename join."""
    block = contract["nativeRegionRoomAssembly"]
    windows = {row["role"]: row for row in block["codeWindows"]}
    if set(windows) != {"caller passes supplied root and room handler",
                        "conditional room root copy", "stored path equality check",
                        "stored path assignment", "last slash wrapper",
                        "last slash search leaf", "root prefix substring",
                        "root prefix copy", "append formatted basename",
                        "room path construction", "assembled path to lookup"}:
        raise ValueError("irradiance.path:region-room-assembly-window-roles")
    for role, row in windows.items():
        start, end = _int(row["startRva"]), _int(row["endRva"])
        raw = pe.bytes_at_va(pe.image_base + start, end - start)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise ValueError(f"irradiance.path:region-room-assembly-window={role}")
    room_start = _int(contract["nativeRegionRoomPath"]["codeWindow"]["startRva"])
    if not (_int(windows["room path construction"]["startRva"]) >= room_start
            and _int(windows["assembled path to lookup"]["endRva"])
            <= _int(contract["nativeRegionRoomPath"]["codeWindow"]["endRva"])):
        raise ValueError("irradiance.path:region-room-assembly-room-range")
    literal_rva, load_rva = _int(block["slashLiteralRva"]), _int(block["slashLiteralLoadRva"])
    literal, load = bytes.fromhex(block["slashLiteralHex"]), bytes.fromhex(block["slashLiteralLoadHex"])
    if (literal != b"/\0" or pe.bytes_at_va(pe.image_base + literal_rva, len(literal)) != literal
            or len(load) != 7 or load[:3] != b"\x4c\x8d\x0d"
            or pe.bytes_at_va(pe.image_base + load_rva, len(load)) != load
            or load_rva + 7 + struct.unpack_from("<i", load, 3)[0] != literal_rva):
        raise ValueError("irradiance.path:region-room-assembly-slash-literal")
    instructions = {row["role"]: row for row in block["instructions"]}
    if set(instructions) != {"caller root and handler object", "caller reloads handler object",
                             "conditional copy to handler plus eight",
                             "handler root plus eight to slash helper",
                             "root substring through slash plus one",
                             "copy prefix then append formatted name",
                             "assembled local passed to keyed lookup"}:
        raise ValueError("irradiance.path:region-room-assembly-instruction-roles")
    for role, row in instructions.items():
        rva, raw = _int(row["rva"]), bytes.fromhex(row["hex"])
        if pe.bytes_at_va(pe.image_base + rva, len(raw)) != raw:
            raise ValueError(f"irradiance.path:region-room-assembly-instruction={role}")
    calls = {row["role"]: (_int(row["callRva"]), _int(row["targetRva"]))
             for row in block["calls"]}
    if set(calls) != {"caller root copy", "caller room handler",
                      "stored path equality", "stored path changed assignment",
                      "stored path byte copy", "last slash search",
                      "handler last slash", "formatted basename", "formatted basename view",
                      "root prefix substring", "root prefix copy", "append formatted basename",
                      "append helper copies directory prefix", "append helper adds basename",
                      "assembled path lookup"}:
        raise ValueError("irradiance.path:region-room-assembly-call-roles")
    targets = {
        "caller root copy": "conditional room root copy",
        "caller room handler": None,
        "stored path equality": "stored path equality check",
        "stored path changed assignment": "stored path assignment",
        "stored path byte copy": None,
        "last slash search": "last slash search leaf",
        "handler last slash": "last slash wrapper",
        "root prefix substring": "root prefix substring",
        "root prefix copy": "root prefix copy",
        "append formatted basename": "append formatted basename",
        "append helper copies directory prefix": "stored path assignment",
    }
    room_parse_windows = {row["role"]: _int(row["startRva"])
                          for row in contract["nativeRegionRoomParse"]["codeWindows"]}
    for role, window_role in targets.items():
        if role == "caller room handler":
            expected = room_start
        elif role == "stored path byte copy":
            expected = room_parse_windows["record byte-copy helper"]
        else:
            expected = _int(windows[window_role]["startRva"])
        if calls[role][1] != expected:
            raise ValueError(f"irradiance.path:region-room-assembly-target={role}")
    path = contract["nativeRegionRoomPath"]
    if (calls["formatted basename"] != (_int(path["formatCallRva"]), _int(path["formatTargetRva"]))
            or calls["assembled path lookup"] != (_int(path["lookupCallRva"]), _int(path["lookupTargetRva"]))):
        raise ValueError("irradiance.path:region-room-assembly-shared-targets")
    for role, (site, target) in calls.items():
        if _rel_target(pe, site, 0xE8) != target:
            raise ValueError(f"irradiance.path:region-room-assembly-call={role}")
    return {"pathConstruction": "supplied root directory plus formatted room basename",
            "sourceRootValue": "unresolved", "selectedVfsRoomFile": "unresolved",
            "boundary": block["boundary"]}


def _check_region_room_consumer(pe: Any, extents: dict[int, int],
                                contract: dict[str, Any]) -> dict[str, Any]:
    """Authenticate the selected copied-record descriptor's command handoff."""
    block = contract["nativeRegionRoomConsumer"]
    windows = {row["role"]: row for row in block["codeWindows"]}
    if set(windows) != {"record allocation descriptor", "callback entry",
                        "callback payload clone", "callback thunk", "callback body",
                        "record binding", "binding slot setter", "dispatch wrapper"}:
        raise ValueError("irradiance.path:region-room-consumer-window-roles")
    pdata_roles = {"record allocation descriptor", "callback entry",
                   "callback payload clone", "callback body", "binding slot setter"}
    for role, row in windows.items():
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start or (role in pdata_roles and extents.get(start) != end):
            raise ValueError(f"irradiance.path:region-room-consumer-pdata={role}")
        raw = pe.bytes_at_va(pe.image_base + start, end - start)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise ValueError(f"irradiance.path:region-room-consumer-window={role}")
    room_window = contract["nativeRegionRoomPath"]["codeWindow"]
    room_start, room_end = _int(room_window["startRva"]), _int(room_window["endRva"])
    instructions = {row["role"]: row for row in block["instructions"]}
    if set(instructions) != {"allocate and copy record bytes",
                             "write grid and configuration descriptor", "pack callback payload",
                             "callback entry and payload clone", "bind record descriptor first word",
                             "dispatch groups from cell count", "positive-count virtual dispatch"}:
        raise ValueError("irradiance.path:region-room-consumer-instruction-roles")
    for role, row in instructions.items():
        rva, raw = _int(row["rva"]), bytes.fromhex(row["hex"])
        if not raw or pe.bytes_at_va(pe.image_base + rva, len(raw)) != raw:
            raise ValueError(f"irradiance.path:region-room-consumer-instruction={role}")
        if role in {"allocate and copy record bytes",
                    "write grid and configuration descriptor", "pack callback payload"}:
            if not room_start <= rva < rva + len(raw) <= room_end:
                raise ValueError(f"irradiance.path:region-room-consumer-room-range={role}")
    calls = {row["role"]: (_int(row["callRva"]), _int(row["targetRva"]))
             for row in block["calls"]}
    if set(calls) != {"record allocation", "record byte copy", "register callback",
                      "clone callback payload", "bind record descriptor",
                      "binding slot setter", "dispatch wrapper"}:
        raise ValueError("irradiance.path:region-room-consumer-call-roles")
    expected = {
        "record allocation": _int(windows["record allocation descriptor"]["startRva"]),
        "record byte copy": _int(next(row["startRva"] for row in
                                  contract["nativeRegionRoomParse"]["codeWindows"]
                                  if row["role"] == "record byte-copy helper")),
        "register callback": _int(windows["callback entry"]["startRva"]),
        "clone callback payload": _int(windows["callback payload clone"]["startRva"]),
        "bind record descriptor": _int(windows["record binding"]["startRva"]),
        "binding slot setter": _int(windows["binding slot setter"]["startRva"]),
        "dispatch wrapper": _int(windows["dispatch wrapper"]["startRva"]),
    }
    for role, (site, target) in calls.items():
        if target != expected[role] or _rel_target(pe, site, 0xE8) != target:
            raise ValueError(f"irradiance.path:region-room-consumer-call={role}")
    ranges = {
        "record allocation": (room_start, room_end),
        "record byte copy": (room_start, room_end),
        "register callback": (room_start, room_end),
        "clone callback payload": (_int(windows["callback entry"]["startRva"]),
                                   _int(windows["callback entry"]["endRva"])),
        "bind record descriptor": (_int(windows["callback body"]["startRva"]),
                                   _int(windows["callback body"]["endRva"])),
        "dispatch wrapper": (_int(windows["callback body"]["startRva"]),
                             _int(windows["callback body"]["endRva"])),
        "binding slot setter": (_int(windows["record binding"]["startRva"]),
                                _int(windows["record binding"]["endRva"])),
    }
    if any(not start <= calls[role][0] < end - 5 for role, (start, end) in ranges.items()):
        raise ValueError("irradiance.path:region-room-consumer-call-range")
    parse_copy = next(row for row in contract["nativeRegionRoomParse"]["calls"]
                      if row["role"] == "record byte copy")
    if calls["record byte copy"] != (_int(parse_copy["callRva"]),
                                    _int(parse_copy["targetRva"])):
        raise ValueError("irradiance.path:region-room-consumer-shared-copy")
    callback_site = _int(block["callbackPointerLoadRva"])
    callback_load = bytes.fromhex(block["callbackPointerLoadHex"])
    thunk = _int(windows["callback thunk"]["startRva"])
    body = _int(windows["callback body"]["startRva"])
    if (not (_int(windows["callback entry"]["startRva"]) <= callback_site
             < _int(windows["callback entry"]["endRva"]) - 7)
            or len(callback_load) != 7 or callback_load[:3] != b"\x48\x8d\x0d"
            or pe.bytes_at_va(pe.image_base + callback_site, 7) != callback_load
            or callback_site + 7 + struct.unpack_from("<i", callback_load, 3)[0] != thunk
            or _rel_target(pe, thunk, 0xE9) != body):
        raise ValueError("irradiance.path:region-room-consumer-callback-target")
    return {"recordHandoff": "copied record allocation descriptor to callback command",
            "binding": "allocation descriptor first word to native command slot",
            "dispatchGroups": "ceil(gridCellCount/64) x 1 x 1",
            "recordFields": "unresolved", "gpuExecution": "unresolved",
            "boundary": block["boundary"]}


def _check_index_suffix(
    image: NativeImage, contract: dict[str, Any], methods: dict[str, int]
) -> dict[str, Any]:
    """Bind the selected scene/Gacha path builders to one literal suffix."""
    block = contract["managedIndexPath"]
    pe, metadata = image.pe, image.metadata
    literal = block["literal"]
    index = int(block["literalIndex"])
    rows = metadata.sections["stringLiteral"]
    pool = metadata.sections["stringLiteralData"]
    if not 0 <= index < rows.size // 8:
        raise ValueError("irradiance.path:index-suffix-literal-index")
    length, start = struct.unpack_from("<ii", metadata.buf, rows.offset + 8 * index)
    if length < 0 or start < 0 or start + length > pool.size:
        raise ValueError("irradiance.path:index-suffix-literal-range")
    value = metadata.buf[pool.offset + start:pool.offset + start + length]
    if value != literal.encode("utf-8"):
        raise ValueError("irradiance.path:index-suffix-literal-value")
    cell_rva = _int(block["usageCellRva"])
    expected_usage = (5 << 29) | (index << 1) | 1
    if pe.u64_at_va(pe.image_base + cell_rva) != expected_usage:
        raise ValueError("irradiance.path:index-suffix-usage-cell")
    for row in block["literalLoads"]:
        rva = _int(row["rva"])
        raw = pe.bytes_at_va(pe.image_base + rva, 7)
        if raw != bytes.fromhex(row["hex"]) or raw[:3] != b"\x48\x8B\x15":
            raise ValueError(f"irradiance.path:index-suffix-load={row['role']}")
        target = rva + 7 + struct.unpack_from("<i", raw, 3)[0]
        if target != cell_rva:
            raise ValueError(f"irradiance.path:index-suffix-cell={row['role']}")
    concat_rva = methods["Concat"]
    for row in block["concatCalls"]:
        target = _rel_target(pe, _int(row["rva"]), 0xE8)
        if target != concat_rva:
            raise ValueError(f"irradiance.path:index-suffix-concat={row['role']}")
    for row in block["codeWindows"]:
        start_rva, end_rva = _int(row["startRva"]), _int(row["endRva"])
        if end_rva <= start_rva:
            raise ValueError(f"irradiance.path:index-suffix-window-range={row['role']}")
        raw = pe.bytes_at_va(pe.image_base + start_rva, end_rva - start_rva)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise ValueError(f"irradiance.path:index-suffix-window={row['role']}")
    return {
        "suffix": literal,
        "scene": "StreamingInNewMap appends suffix to supplied root, stages +0x28; PipelineUpdate moves +0x28 to +0x20 and passes +0x20 to SetMapV3 on path change",
        "proxy": "selected ConvertFrom branch appends suffix to its converted property string and stages +0x28",
        "gacha": "CreateGachaIV and UpdateGachaIV append suffix to supplied root at +0x40; PipelineUpdate passes +0x40 to SetMapV3 on its separate branch",
        "exactVfsIdentity": "unresolved: supplied root and resource lookup normalization remain unjoined to one authenticated logical path",
    }


def _check_proxy_root(image: NativeImage, contract: dict[str, Any], methods: dict[str, int]) -> dict[str, Any]:
    """Prove the selected proxy route's root source without naming its value."""
    block = contract["managedProxyRoot"]
    pe, metadata = image.pe, image.metadata
    owner_index = int(block["ownerTypeIndex"])
    if not 0 <= owner_index < len(metadata.types):
        raise ValueError("irradiance.path:proxy-owner-index")
    owner = metadata.types[owner_index]
    if metadata.type_full_name(owner) != block["ownerType"]:
        raise ValueError("irradiance.path:proxy-owner-type")
    field = block["propertyField"]
    names = {metadata.string(row.name_index) for row in metadata.fields_for(owner)}
    offsets = runtime_type_field_offsets(metadata, pe, image.registration, owner.index)
    if field["name"] not in names or offsets.get(field["name"]) != _int(field["staticOffset"]):
        raise ValueError("irradiance.path:proxy-property-field")
    cell = _int(block["classUsageCellRva"])
    raw = pe.bytes_at_va(pe.image_base + cell, 8)
    registered = unresolved_usage_index(
        raw, image.registration["typesCount"], tag=1,
        source=str(image.gameassembly), offset=cell,
    )
    if registered != int(block["registeredTypeIndex"]):
        raise ValueError("irradiance.path:proxy-class-registration")
    type_pointer = pe.u64_at_va(int(image.registration["types"], 16) + registered * 8)
    definition = struct.unpack_from("<Q", pe.bytes_at_va(type_pointer, 16))[0]
    if definition != owner.index:
        raise ValueError("irradiance.path:proxy-class-definition")
    load_rva = _int(block["classLoadRva"])
    load = pe.bytes_at_va(pe.image_base + load_rva, 7)
    if load != bytes.fromhex(block["classLoadHex"]) or load[:3] != b"\x48\x8B\x05":
        raise ValueError("irradiance.path:proxy-class-load")
    if load_rva + 7 + struct.unpack_from("<i", load, 3)[0] != cell:
        raise ValueError("irradiance.path:proxy-class-cell")
    name_load_rva = _int(block["converterNameLoadRva"])
    name_load = pe.bytes_at_va(pe.image_base + name_load_rva, 7)
    if name_load != bytes.fromhex(block["converterNameLoadHex"]) or name_load[:3] != b"\x48\x8D\x0D":
        raise ValueError("irradiance.path:proxy-converter-name-load")
    name_rva = name_load_rva + 7 + struct.unpack_from("<i", name_load, 3)[0]
    if pe.c_string_at_va(pe.image_base + name_rva) != block["converterFullName"]:
        raise ValueError("irradiance.path:proxy-converter-name")
    if methods["ConvertFrom"] != _int(block["convertFromRva"]):
        raise ValueError("irradiance.path:proxy-convert-from")
    for row in block["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start:
            raise ValueError(f"irradiance.path:proxy-window-range={row['role']}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:proxy-window={row['role']}")
    initializer = pe.bytes_at_va(pe.image_base + _int(block["initializerRva"]), 12)
    if initializer[:5] != b"\x48\xC7\x44\x24\x20" or initializer[9:] != b"\x45\x33\xD2":
        raise ValueError("irradiance.path:proxy-property-initializer")
    stored = struct.pack("<q", struct.unpack_from("<i", initializer, 5)[0]) + bytes(4)
    if stored.hex().upper() != block["propertyIdInitializerBytes"].upper():
        raise ValueError("irradiance.path:proxy-property-initializer-bytes")
    return {
        "propertyField": field["name"],
        "selectedRoute": "ConvertFrom passes the static property's 12-byte ID to ConvertStringFrom_Injected and concatenates its returned string with /v3/index.bytes before storing manager +0x28",
        "propertyIdInitializerBytes": block["propertyIdInitializerBytes"],
        "rootValue": "unresolved: serialized property value is not authenticated to a VFS path",
    }


def _check_managed(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    pe = image.pe
    methods: dict[str, int] = {}
    for row in contract["methods"]:
        index = image.validate_method_row(
            [row["index"], row["type"], row["method"]], label="irradiance.path"
        )
        actual = image.method_pointer_va(image.metadata.methods[index]) - pe.image_base
        expected = _int(row["pointerRva"])
        if actual != expected:
            raise ValueError(
                f"irradiance.path:method-pointer={row['method']}:"
                f"expected=0x{expected:X},actual=0x{actual:X}"
            )
        methods[row["method"]] = actual

    instructions = []
    for row in contract["managedInstructions"]:
        rva = _int(row["rva"])
        expected = bytes.fromhex(row["hex"])
        actual = pe.bytes_at_va(pe.image_base + rva, len(expected))
        if actual != expected:
            raise ValueError(f"irradiance.path:managed-instruction={row['role']}:rva=0x{rva:X}")
        if "callTargetRva" in row:
            target = _rel_target(pe, rva + len(expected) - 5, 0xE8)
            if target != _int(row["callTargetRva"]) or target != methods["SetMapV3"]:
                raise ValueError(f"irradiance.path:managed-call={row['role']}:target=0x{target:X}")
        instructions.append({"role": row["role"], "rva": row["rva"]})

    stub = contract["managedIcallStub"]
    rva = _int(stub["nameLoadRva"])
    raw = pe.bytes_at_va(pe.image_base + rva, 7)
    if raw != bytes.fromhex(stub["nameLoadHex"]) or raw[:3] != b"\x48\x8D\x0D":
        raise ValueError("irradiance.path:managed-icall-name-load")
    name_rva = rva + 7 + struct.unpack_from("<i", raw, 3)[0]
    if pe.c_string_at_va(pe.image_base + name_rva) != stub["fullName"]:
        raise ValueError("irradiance.path:managed-icall-name")
    return {
        "methods": methods,
        "instructions": instructions,
        "icallName": stub["fullName"],
        "indexPath": _check_index_suffix(image, contract, methods),
        "proxyRoot": _check_proxy_root(image, contract, methods),
    }


def _pdata_extents(pe: Any) -> dict[int, int]:
    section = next((row for row in pe.sections if row["name"] == ".pdata"), None)
    if section is None:
        raise ValueError("irradiance.path:unity-pdata-missing")
    raw = pe.buf[section["rawPointer"]:section["rawPointer"] + section["rawSize"]]
    return {
        start: end
        for start, end, _unwind in struct.iter_unpack("<III", raw[:len(raw) // 12 * 12])
        if end > start
    }


def _check_buffer_join(pe: Any, contract: dict[str, Any]) -> dict[str, Any]:
    join = contract["nativeBufferJoin"]
    for row in join["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start:
            raise ValueError(f"irradiance.path:buffer-window-range=0x{start:X}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:buffer-window=0x{start:X}")
    for row in join["calls"]:
        target = _rel_target(pe, _int(row["callRva"]), 0xE8)
        if target != _int(row["targetRva"]):
            raise ValueError(f"irradiance.path:buffer-call={row['role']}:target=0x{target:X}")
    for row in join["instructions"]:
        rva = _int(row["rva"])
        expected = bytes.fromhex(row["hex"])
        if pe.bytes_at_va(pe.image_base + rva, len(expected)) != expected:
            raise ValueError(f"irradiance.path:buffer-instruction={row['role']}:rva=0x{rva:X}")
    return {
        "pathKey": "same parser input retained at native +0xB0",
        "lookup": "retained path key drives a native lookup; successful result supplies a two-u64 stream source pair",
        "stream": "result word1 sizes an allocation and is retained as the requested data-buffer size",
        "cursor": "ready stream returns its stored data-buffer pointer; parser initializes cursor middle word to -1",
        "u32Read": "pointer-plus-offset read advances four bytes without a local bound comparison",
        "sourceVfsIdentity": "unresolved",
        "outerIoBoundGate": "selected type-zero queue dispatch checks its exact read byte count before status zero",
    }


def _check_stream_completion(pe: Any, extents: dict[int, int], contract: dict[str, Any]) -> dict[str, str]:
    block = contract["nativeStreamCompletion"]
    load_rva = _int(block["handlerLoadRva"])
    raw = pe.bytes_at_va(pe.image_base + load_rva, 7)
    if raw != bytes.fromhex(block["handlerLoadHex"]) or raw[:3] != b"\x48\x8D\x0D":
        raise ValueError("irradiance.path:stream-completion-handler-load")
    target = load_rva + 7 + struct.unpack_from("<i", raw, 3)[0]
    if target != _int(block["handlerRva"]):
        raise ValueError("irradiance.path:stream-completion-handler-target")
    if _rel_target(pe, _int(block["queueJumpRva"]), 0xE9) != _int(block["queueTargetRva"]):
        raise ValueError("irradiance.path:stream-completion-queue")
    window = block["handlerWindow"]
    start, end = _int(window["startRva"]), _int(window["endRva"])
    if start != target or extents.get(start) != end:
        raise ValueError("irradiance.path:stream-completion-handler-pdata")
    digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
    if digest != window["sha256"].upper():
        raise ValueError("irradiance.path:stream-completion-handler-window")
    return {
        "queue": "selected stream constructor queues the allocated object",
        "callback": "completion writes stream status and decrements reference count; no fill is shown in this handler",
        "bufferFill": "selected callback does not fill; selected type-zero queue dispatch reads into the request buffer before callback",
    }


def _check_stream_fill(pe: Any, extents: dict[int, int], contract: dict[str, Any]) -> dict[str, str]:
    block = contract["nativeStreamFill"]
    queue_rva = _int(block["queueSingletonLoadRva"])
    wrapper_rva = _int(block["workerWrapperSingletonLoadRva"])
    for role, rva, expected in (
        ("queue", queue_rva, bytes.fromhex(block["queueSingletonLoadHex"])),
        ("worker", wrapper_rva, bytes.fromhex(block["workerWrapperHex"])[3:10]),
    ):
        raw = pe.bytes_at_va(pe.image_base + rva, len(expected))
        if raw != expected or len(raw) != 7 or raw[:2] != b"\x48\x8b":
            raise ValueError(f"irradiance.path:stream-fill-{role}-singleton-load")
        target = rva + 7 + struct.unpack_from("<i", raw, 3)[0]
        if target != _int(block["sharedSingletonRva"]):
            raise ValueError(f"irradiance.path:stream-fill-{role}-singleton-target")
    wrapper_start = _int(block["workerWrapperRva"])
    wrapper_raw = bytes.fromhex(block["workerWrapperHex"])
    if pe.bytes_at_va(pe.image_base + wrapper_start, len(wrapper_raw)) != wrapper_raw:
        raise ValueError("irradiance.path:stream-fill-worker-wrapper")
    if _rel_target(pe, _int(block["workerWrapperJumpRva"]), 0xE9) != _int(block["workerRva"]):
        raise ValueError("irradiance.path:stream-fill-worker-wrapper-target")

    for row in block["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start or extents.get(start) != end:
            raise ValueError(f"irradiance.path:stream-fill-pdata=0x{start:X}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:stream-fill-window=0x{start:X}")
    for row in block["calls"]:
        rva, expected = _int(row["callRva"]), _int(row["targetRva"])
        target = _rel_target(pe, rva, 0xE8)
        if target != expected:
            raise ValueError(f"irradiance.path:stream-fill-call={row['role']}:target=0x{target:X}")
    for row in block["instructions"]:
        rva, expected = _int(row["rva"]), bytes.fromhex(row["hex"])
        raw = pe.bytes_at_va(pe.image_base + rva, len(expected))
        if raw != expected:
            raise ValueError(f"irradiance.path:stream-fill-instruction={row['role']}:rva=0x{rva:X}")
        if row["role"].startswith("alternate ") and row["role"].endswith(" singleton load"):
            if len(raw) != 7 or raw[:2] != b"\x48\x8b" or (
                rva + 7 + struct.unpack_from("<i", raw, 3)[0] != _int(block["sharedSingletonRva"])
            ):
                raise ValueError(f"irradiance.path:stream-fill-alternate-singleton={row['role']}")
    return {
        "queue": "selected stream object enters this singleton's pending queue; another producer branches between direct invocation of its worker and enqueueing the same request shape",
        "read": "worker sends the stream's +0x78 lookup word as backend offset, +0x68 data buffer, and +0x70 requested size through an accumulating read helper",
        "outerIoBoundGate": "this sibling worker reports success status 0 only when returned byte count equals requested size; selected type-zero queue dispatch has its own authenticated gate",
        "backend": "read helper calls a resource backend virtual method; concrete VFS identity and normalization remain unresolved",
        "queueToWorkerDispatch": "selected queued request is handled by the separately authenticated type-zero dispatcher, not proven through this sibling worker",
        "parserFinalEof": "separate: selected parser has no final cursor EOF equality check",
    }


def _check_selected_queue_dispatch(pe: Any, extents: dict[int, int], contract: dict[str, Any]) -> dict[str, str]:
    block = contract["nativeSelectedQueueDispatch"]
    singleton_rva = _int(block["singletonRva"])
    for role, rva_key, prefix in (
        ("publication", "globalStoreRva", b"\x48\x89\x05"),
        ("thread-load", "globalLoadRva", b"\x48\x8b\x3d"),
    ):
        rva = _int(block[rva_key])
        raw = pe.bytes_at_va(pe.image_base + rva, 7)
        if raw[:3] != prefix or rva + 7 + struct.unpack_from("<i", raw, 3)[0] != singleton_rva:
            raise ValueError(f"irradiance.path:selected-queue-{role}")
    function_load = _int(block["threadFunctionLoadRva"])
    raw = pe.bytes_at_va(pe.image_base + function_load, 7)
    if raw[:3] != b"\x48\x8d\x05" or (
        function_load + 7 + struct.unpack_from("<i", raw, 3)[0] != _int(block["threadFunctionRva"])
    ) or pe.bytes_at_va(pe.image_base + _int(block["threadFunctionStoreRva"]), 4) != b"\x48\x89\x47\x60":
        raise ValueError("irradiance.path:selected-queue-thread-function")
    entry_load = _int(block["threadEntryLoadRva"])
    raw = pe.bytes_at_va(pe.image_base + entry_load, 7)
    if raw[:3] != b"\x4c\x8d\x05" or (
        entry_load + 7 + struct.unpack_from("<i", raw, 3)[0] != _int(block["threadEntryRva"])
    ):
        raise ValueError("irradiance.path:selected-queue-thread-entry")
    for row in block["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start or extents.get(start) != end:
            raise ValueError(f"irradiance.path:selected-queue-pdata=0x{start:X}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:selected-queue-window=0x{start:X}")
    for row in block["calls"]:
        rva, target = _int(row["callRva"]), _int(row["targetRva"])
        if _rel_target(pe, rva, 0xE8) != target:
            raise ValueError(f"irradiance.path:selected-queue-call={row['role']}")
    for row in block["instructions"]:
        rva, expected = _int(row["rva"]), bytes.fromhex(row["hex"])
        if pe.bytes_at_va(pe.image_base + rva, len(expected)) != expected:
            raise ValueError(f"irradiance.path:selected-queue-instruction={row['role']}")
    table_rva = _int(block["selectorTableRva"])
    index = int(block["selectorIndex"])
    target = struct.unpack("<I", pe.bytes_at_va(pe.image_base + table_rva + index * 4, 4))[0]
    if index != 0 or target != _int(block["selectorTargetRva"]):
        raise ValueError("irradiance.path:selected-queue-type-zero-target")
    return {
        "request": "selected constructor sets type and queue-partition words to zero, with no multi-read descriptor",
        "dispatch": "singleton thread drains the same pending vector, selects the type-zero request, and enters its read branch",
        "read": "selected type-zero branch passes request +0x68 buffer, +0x78 offset and +0x70 size to the accumulating read helper",
        "outerIoBoundGate": "selected branch returns success status zero only after its read byte count equals the requested size",
        "backend": "resource backend virtual call remains unresolved; this dispatch does not establish a unique VFS file identity",
    }


def _check_backend_boundary(pe: Any, extents: dict[int, int], contract: dict[str, Any]) -> dict[str, str]:
    block = contract["nativeBackendBoundary"]
    for row in block["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start or extents.get(start) != end:
            raise ValueError(f"irradiance.path:backend-pdata=0x{start:X}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:backend-window=0x{start:X}")
    for row in block["calls"]:
        if _rel_target(pe, _int(row["callRva"]), 0xE8) != _int(row["targetRva"]):
            raise ValueError(f"irradiance.path:backend-call={row['role']}")
    for row in block["instructions"]:
        rva, expected = _int(row["rva"]), bytes.fromhex(row["hex"])
        if pe.bytes_at_va(pe.image_base + rva, len(expected)) != expected:
            raise ValueError(f"irradiance.path:backend-instruction={row['role']}")
    return {
        "handleSelector": "selected request name enters a byte-comparing resource cache; a hit returns a slot and a miss creates one",
        "miss": "the selected miss path forwards its resource name and zero flags through handle creation to a provider open",
        "providerOpen": "provider pointer is loaded from the created handle and opened through its virtual method",
        "providerRead": "the selected read helper loads a provider pointer from the returned slot and invokes its virtual read method",
        "fileIdentity": "unresolved: concrete provider instance and supplied root are not authenticated to a unique VFS index.bytes",
    }


def _check_fallback_provider(pe: Any, extents: dict[int, int], contract: dict[str, Any]) -> dict[str, Any]:
    """Authenticate the registry's default provider without asserting its live selection."""
    block = contract["nativeFallbackProvider"]
    for row in block["codeWindows"]:
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if end <= start or extents.get(start) != end:
            raise ValueError(f"irradiance.path:fallback-pdata=0x{start:X}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:fallback-window=0x{start:X}")
    for row in block["calls"]:
        if _rel_target(pe, _int(row["callRva"]), 0xE8) != _int(row["targetRva"]):
            raise ValueError(f"irradiance.path:fallback-call={row['role']}")
    for row in block["instructions"]:
        rva, expected = _int(row["rva"]), bytes.fromhex(row["hex"])
        if pe.bytes_at_va(pe.image_base + rva, len(expected)) != expected:
            raise ValueError(f"irradiance.path:fallback-instruction={row['role']}")
    global_rva = _int(block["managerGlobalRva"])
    for role in ("manager receives new registry", "resource lookup loads registry"):
        row = next(row for row in block["instructions"] if row["role"] == role)
        rva = _int(row["rva"])
        raw = pe.bytes_at_va(pe.image_base + rva, 7)
        if rva + 7 + struct.unpack_from("<i", raw, 3)[0] != global_rva:
            raise ValueError(f"irradiance.path:fallback-registry-target={role}")
    vtable_rva = _int(block["defaultVtableRva"])
    row = next(row for row in block["instructions"] if row["role"] == "default provider final vtable load")
    rva = _int(row["rva"])
    raw = pe.bytes_at_va(pe.image_base + rva, 7)
    if rva + 7 + struct.unpack_from("<i", raw, 3)[0] != vtable_rva:
        raise ValueError("irradiance.path:fallback-vtable-target")
    slots = {}
    for row in block["methodSlots"]:
        target = pe.u64_at_va(pe.image_base + vtable_rva + _int(row["offset"])) - pe.image_base
        if target != _int(row["targetRva"]):
            raise ValueError(f"irradiance.path:fallback-vtable-slot={row['role']}")
        slots[row["role"]] = row["targetRva"]
    if slots["provide fallback"] != block["fallbackMethodRva"]:
        raise ValueError("irradiance.path:fallback-method-target")

    directory = block["importDirectory"]
    optional = pe.u32_at_file(0x3C) + 24
    if pe.u32_at_file(optional + 120) != _int(directory["descriptorRva"]):
        raise ValueError("irradiance.path:fallback-import-directory")
    if pe.bytes_at_va(pe.image_base + _int(directory["descriptorRva"]), 20) != bytes.fromhex(directory["descriptorHex"]):
        raise ValueError("irradiance.path:fallback-import-descriptor")
    if pe.c_string_at_va(pe.image_base + _int(directory["dllNameRva"])) != directory["dll"]:
        raise ValueError("irradiance.path:fallback-import-dll")
    imports = []
    for row in block["imports"]:
        rva = _int(row["callRva"])
        raw = pe.bytes_at_va(pe.image_base + rva, 6)
        slot = rva + 6 + struct.unpack_from("<i", raw, 2)[0]
        if raw[:2] != b"\xFF\x15" or slot != _int(directory["firstThunkRva"]) + int(row["iatIndex"]) * 8:
            raise ValueError(f"irradiance.path:fallback-import-call={row['role']}")
        lookup = _int(directory["firstLookupRva"]) + int(row["iatIndex"]) * 8
        if pe.u64_at_va(pe.image_base + lookup) != _int(row["nameRva"]):
            raise ValueError(f"irradiance.path:fallback-import-lookup={row['role']}")
        name = struct.pack("<H", int(row["hint"])) + row["name"].encode("ascii") + b"\0"
        if pe.bytes_at_va(pe.image_base + _int(row["nameRva"]), len(name)) != name:
            raise ValueError(f"irradiance.path:fallback-import-name={row['role']}")
        imports.append(row["name"])
    return {
        "selection": "default only when no registered provider matches the resource name",
        "methodSlots": slots,
        "imports": imports,
        "boundary": "fallback open and read reach Windows file APIs; the provider selected by the IV request and the exact file path remain unresolved",
    }


def _check_cursor_bounds(pe: Any, cursor: dict[str, Any]) -> dict[str, str]:
    # The caller authenticates each window and its .pdata extent. Require
    # uninterrupted coverage of the selected parser before recording a
    # negative claim about its final cursor check.
    first, final = _int(cursor["parserRva"]), _int(cursor["parserEndRva"])
    windows = sorted(
        (_int(row["startRva"]), _int(row["endRva"]))
        for row in cursor["windows"]
        if first <= _int(row["startRva"]) and _int(row["endRva"]) <= final
    )
    if not windows or windows[0][0] != first or windows[-1][1] != final or any(
        left[1] != right[0] for left, right in zip(windows, windows[1:])
    ):
        raise ValueError("irradiance.path:parser-body-coverage")
    byte_rva = _int(cursor["byteReadRva"])
    expected = bytes.fromhex(cursor["byteReadHex"])
    if pe.bytes_at_va(pe.image_base + byte_rva, len(expected)) != expected:
        raise ValueError("irradiance.path:cursor-u8-reader")
    if _rel_target(pe, _int(cursor["byteReadCallRva"]), 0xE8) != byte_rva:
        raise ValueError("irradiance.path:cursor-u8-call")
    return {
        "parserBody": "complete selected parser body authenticated through contiguous code windows",
        "u8AndU32Readers": "both leaf readers load pointer-plus-offset and advance without a local length comparison",
        "finalParserEof": "no final cursor-offset-versus-stream-size or EOF equality check in this selected parser body",
        "outerIoBounds": "selected type-zero queue dispatch checks exact-sized read; parser final EOF check is separate and absent",
    }


def _check_unity(unity_path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    pe = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(unity_path)
    table = contract["unityIcallTable"]
    count, slot = int(table["count"]), int(table["slot"])
    if count <= slot or slot < 0:
        raise ValueError("irradiance.path:icall-slot-out-of-range")
    names = pe.bytes_at_va(pe.image_base + _int(table["nameTableRva"]), (count + 1) * 8)
    if struct.unpack_from("<Q", names, count * 8)[0] != 0:
        raise ValueError("irradiance.path:icall-name-sentinel")
    functions = pe.bytes_at_va(pe.image_base + _int(table["functionTableRva"]), count * 8)
    name_va = struct.unpack_from("<Q", names, slot * 8)[0]
    function_va = struct.unpack_from("<Q", functions, slot * 8)[0]
    if pe.c_string_at_va(name_va) != table["name"]:
        raise ValueError("irradiance.path:unity-icall-name")
    if function_va != pe.image_base + _int(table["functionRva"]):
        raise ValueError("irradiance.path:unity-icall-function")
    # These are parallel, NUL-terminated name and code-pointer arrays. Check
    # the whole selected table, rather than accepting a coincidental slot.
    for index in range(count):
        name = pe.c_string_at_va(struct.unpack_from("<Q", names, index * 8)[0])
        target = struct.unpack_from("<Q", functions, index * 8)[0]
        offset, section, _rva = pe.file_offset_for_va(target)
        if not name.startswith("UnityEngine.") or offset is None or section != ".text":
            raise ValueError(f"irradiance.path:icall-table-row={index}")

    proxy = contract["managedProxyRoot"]["unityConverter"]
    proxy_slot = int(proxy["slot"])
    if not 0 <= proxy_slot < count:
        raise ValueError("irradiance.path:proxy-icall-slot")
    proxy_name = pe.c_string_at_va(struct.unpack_from("<Q", names, proxy_slot * 8)[0])
    proxy_function = struct.unpack_from("<Q", functions, proxy_slot * 8)[0]
    if proxy_name != proxy["name"] or proxy_function != pe.image_base + _int(proxy["functionRva"]):
        raise ValueError("irradiance.path:proxy-icall-table")

    extents = _pdata_extents(pe)
    proxy_window = proxy["codeWindow"]
    proxy_start, proxy_end = _int(proxy_window["startRva"]), _int(proxy_window["endRva"])
    if extents.get(proxy_start) != proxy_end:
        raise ValueError("irradiance.path:proxy-unity-pdata")
    proxy_digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + proxy_start, proxy_end - proxy_start)).hexdigest().upper()
    if proxy_digest != proxy_window["sha256"].upper():
        raise ValueError("irradiance.path:proxy-unity-window")
    cursor = contract["nativeIndexCursor"]
    for row in (*contract["unityWindows"], *cursor["windows"]):
        start, end = _int(row["startRva"]), _int(row["endRva"])
        if extents.get(start) != end:
            raise ValueError(f"irradiance.path:unity-pdata=0x{start:X}")
        digest = hashlib.sha256(pe.bytes_at_va(pe.image_base + start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"irradiance.path:unity-window=0x{start:X}")

    helper = contract["nativePathHelper"]
    for call, target in (
        ("wrapperCallRva", "helperRva"),
        ("objectAccessCallRva", "objectAccessTargetRva"),
    ):
        if _rel_target(pe, _int(helper[call]), 0xE8) != _int(helper[target]):
            raise ValueError(f"irradiance.path:native-call={call}")
    rva = _int(helper["fieldAddressRva"])
    if pe.bytes_at_va(pe.image_base + rva, 7) != bytes.fromhex(helper["fieldAddressHex"]):
        raise ValueError("irradiance.path:native-field-address")
    if _rel_target(pe, _int(helper["assignmentJumpRva"]), 0xE9) != _int(helper["assignmentTargetRva"]):
        raise ValueError("irradiance.path:native-assignment")

    # The later consumer retrieves the same native +0x220 path, hands it to a
    # parser routine, and reads V3 magics through an advancing u32 cursor.
    # This does not yet bind the cursor's source buffer to a specific VFS file.
    if _rel_target(pe, _int(cursor["pathGetterCallRva"]), 0xE8) != _int(cursor["pathGetterRva"]):
        raise ValueError("irradiance.path:native-path-getter")
    getter_field = bytes.fromhex(cursor["pathGetterFieldHex"])
    if pe.bytes_at_va(pe.image_base + _int(cursor["pathGetterFieldRva"]), len(getter_field)) != getter_field:
        raise ValueError("irradiance.path:native-path-getter-field")
    if _rel_target(pe, _int(cursor["parserCallRva"]), 0xE8) != _int(cursor["parserRva"]):
        raise ValueError("irradiance.path:native-parser-call")
    if _rel_target(pe, _int(cursor["magicReadCallRva"]), 0xE8) != _int(cursor["cursorReadRva"]):
        raise ValueError("irradiance.path:native-magic-read-call")
    for label, rva_key, hex_key in (
        ("path-to-parser", "pathGetterCallRva", "pathToParserHex"),
        ("cursor-u32", "cursorReadRva", "cursorReadHex"),
        ("magic-gate", "magicGateRva", "magicGateHex"),
        ("scene-record", "sceneRecordRva", "sceneRecordHex"),
        ("gacha-record", "gachaRecordRva", "gachaRecordHex"),
    ):
        expected = bytes.fromhex(cursor[hex_key])
        if pe.bytes_at_va(pe.image_base + _int(cursor[rva_key]), len(expected)) != expected:
            raise ValueError(f"irradiance.path:native-{label}")
    buffer_join = _check_buffer_join(pe, contract)
    cursor_bounds = _check_cursor_bounds(pe, cursor)
    stream_completion = _check_stream_completion(pe, extents, contract)
    stream_fill = _check_stream_fill(pe, extents, contract)
    selected_queue_dispatch = _check_selected_queue_dispatch(pe, extents, contract)
    backend_boundary = _check_backend_boundary(pe, extents, contract)
    fallback_provider = _check_fallback_provider(pe, extents, contract)
    region_room_path = _check_region_room_path(pe, extents, contract)
    region_room_parse = _check_region_room_parse(pe, extents, contract)
    region_room_assembly = _check_region_room_assembly(pe, contract)
    region_room_consumer = _check_region_room_consumer(pe, extents, contract)
    return {
        "icallName": table["name"],
        "proxyConverter": {"icallSlot": proxy_slot, "functionRva": proxy["functionRva"]},
        "icallSlot": slot,
        "registeredFunctionRva": table["functionRva"],
        "nativePathFieldOffset": "0x220",
        "indexCursor": {
            "magicWords": ["0x03000002", "0x03000003"],
            "sceneRecordBytes": 36,
            "gachaRecordBytes": 32,
            "sourceBufferBoundary": "path-keyed native stream pointer; exact VFS source unresolved",
            "bounds": cursor_bounds,
        },
        "bufferJoin": buffer_join,
        "streamCompletion": stream_completion,
        "streamFill": stream_fill,
        "selectedQueueDispatch": selected_queue_dispatch,
        "backendBoundary": backend_boundary,
        "fallbackProvider": fallback_provider,
        "regionRoomPath": region_room_path,
        "regionRoomParse": region_room_parse,
        "regionRoomAssembly": region_room_assembly,
        "regionRoomConsumer": region_room_consumer,
    }


def audit(
    *, contract_path: Path = DEFAULT_CONTRACT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="irradiance.path", status="validated"
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": "endfield.irradiance-v3-path-native-audit.v13",
        "contract": {"path": str(contract_path), "sha256": contract_sha},
        "source": {
            "gameAssembly": str(gate.gameassembly),
            "metadata": str(gate.metadata),
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "metadataSha256": gate.metadata_sha256.upper(),
        },
        "status": gate.status,
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        report["detail"] = gate.detail
        return report
    unity_path = gate.gameassembly.parent / "UnityPlayer.dll"
    report["source"]["unityPlayer"] = str(unity_path)
    if not unity_path.is_file():
        report.update(status="missing", detail=f"UnityPlayer.dll missing at {unity_path}")
        return report
    unity_sha = sha256_file_upper(unity_path)
    report["source"]["unityPlayerSha256"] = unity_sha
    if unity_sha != inputs["unityPlayerSha256"].upper():
        report.update(status="mismatched", detail="UnityPlayer.dll hash differs from reviewed contract")
        return report
    try:
        image = NativeImage(gate.gameassembly, gate.metadata, label="irradiance.path")
        report["managed"] = _check_managed(image, contract)
        report["unity"] = _check_unity(unity_path, contract)
        report["evidenceBoundary"] = contract["evidenceBoundary"]
    except (KeyError, ValueError, TypeError) as exc:
        report.pop("managed", None)
        report.pop("unity", None)
        report.update(status="validation_failed", detail=str(exc))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = audit(
        contract_path=args.contract, gameassembly=args.gameassembly, metadata=args.metadata
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Irradiance V3 path: {report['status']} ({args.out})")
    if report.get("detail"):
        print(report["detail"])
    return 0 if report["status"] in {"validated", "missing", "mismatched"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
