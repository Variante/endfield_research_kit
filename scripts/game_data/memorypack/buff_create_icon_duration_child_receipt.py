"""Native-gated direct fields of CreateBuffAction.buffIconDurationSource.

The child is replayed only at a range certified by the selected CreateBuff
parent. String content is retained as source bytes; duration behavior is not
inferred from the stored enum and string.

The selected two-member ``BuffIconDurationSourceSetting`` reader stores
``durationSourceType`` and ``timedMarkerId``. The validator checks the
selected reader window, generated setters, source read call and destination
stores against runtime field offsets. ``buff_create_action_root_receipt``
composes this child into the narrow sole-CreateBuff root route.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.skill_timeline_create_buff import (
    _contract as _parent_contract,
    validate_current_native_contract as validate_parent_native,
)


LABEL = "buffCreateIconDurationChild"
SCHEMA = "endfield.buff-create-icon-duration-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_create_icon_duration_child_native.json"


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.buff-create-icon-duration-child-native-contract.v1",
        status="exact-current-build",
        label=LABEL,
    )
    if (
        value.get("parentActionContract") != "skill_timeline_create_buff_native.json"
        or value.get("readerContract") != "buff_92_native.json"
        or value.get("parentUnionTag") != 0x0092
        or len(value.get("wrapper", {}).get("setterMethods", ())) != 2
        or value["wrapper"].get("readOrder") != ["durationSourceType", "timedMarkerId"]
        or [row[1].removeprefix("set___").removesuffix("__")
            for row in value["wrapper"]["setterMethods"]] != value["wrapper"]["readOrder"]
        or set(value.get("sourceInstructions", {})) != {
            "memberCountCompare", "durationSourceTypeStore",
            "timedMarkerIdReadCall", "timedMarkerIdStore",
        }
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Check parent route, child reader, setter order and destination stores."""
    contract = _contract()
    expected = contract["nativeInputs"]
    parent = _parent_contract()
    if (
        parent.get("nativeInputs") != expected
        or parent.get("dispatcher", {}).get("unionTag") != contract["parentUnionTag"]
        or parent.get("dependencies", [{}])[0].get("path") != contract["readerContract"]
    ):
        raise ValueError(f"{LABEL}.native:parent-contract-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    parent_native = validate_parent_native()
    if (
        parent_native.get("status") != "validated"
        or parent_native.get("nativeInputs") != expected
        or parent_native.get("unionTag") != contract["parentUnionTag"]
    ):
        raise ValueError(f"{LABEL}.native:parent-not-validated")
    unityplayer = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    reader = json.loads(
        (CONTRACTS_DIR / contract["readerContract"]).read_text(encoding="utf-8")
    )
    if (
        reader.get("schemaVersion") != 1
        or reader.get("anonymousReadOrder", {}).get("member2")
        != ["scalar32", "byte-payload"]
    ):
        raise ValueError(f"{LABEL}.native:reader-layout-drift")
    method_rows = [row for row in reader["methods"]
                   if row[0] == contract["readerMethodIndex"]]
    windows = [row for row in reader["codeWindows"]
               if row["startRva"] == contract["readerNormalWindowStartRva"]]
    if len(method_rows) != 1 or len(windows) != 1:
        raise ValueError(f"{LABEL}.native:reader-window-or-method")
    image.validate_method_row(method_rows[0], label=LABEL)
    image.check_windows(windows, label=LABEL)
    window = windows[0]
    wrapper = contract["wrapper"]
    owner = image.metadata.types[wrapper["typeDefinition"]]
    if (
        image.metadata.type_full_name(owner) != wrapper["typeName"]
        or image.setter_methods(owner, parameter="typeName", label=LABEL)
        != wrapper["setterMethods"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-setters")
    runtime_type = contract["runtimeType"]
    actual_offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration,
        runtime_type["typeDefinition"],
    )
    if (
        image.type_name(runtime_type["typeDefinition"]) != runtime_type["typeName"]
        or actual_offsets != runtime_type["fieldOffsets"]
    ):
        raise ValueError(f"{LABEL}.native:runtime-field-offsets")
    instructions = contract["sourceInstructions"]
    image.check_instruction_windows(
        [[row[0], row[1]] for row in instructions.values()], label=LABEL,
    )
    if not all(window["startRva"] <= row[0]
               and row[0] + len(bytes.fromhex(row[1])) <= window["endRva"]
               for row in instructions.values()):
        raise ValueError(f"{LABEL}.native:source-instruction-bounds")
    compare = instructions["memberCountCompare"]
    enum_store = instructions["durationSourceTypeStore"]
    string_call = instructions["timedMarkerIdReadCall"]
    string_store = instructions["timedMarkerIdStore"]
    if (
        not compare[0] < enum_store[0] < string_call[0] < string_store[0]
        or bytes.fromhex(enum_store[1])[-1]
        != actual_offsets["durationSourceType"]
        or bytes.fromhex(string_store[1])[-1]
        != actual_offsets["timedMarkerId"]
    ):
        raise ValueError(f"{LABEL}.native:source-store-order")
    call_raw = bytes.fromhex(string_call[1])
    if (
        len(call_raw) != 5 or call_raw[:1] != b"\xe8"
        or string_call[0] + 5 + struct.unpack_from("<i", call_raw, 1)[0]
        != string_call[2]
    ):
        raise ValueError(f"{LABEL}.native:string-source-call")
    return {
        "status": "validated", "nativeInputs": expected,
        "parentUnionTag": contract["parentUnionTag"],
        "readOrder": wrapper["readOrder"],
        "runtimeFieldOffsets": {
            name: actual_offsets[name] for name in wrapper["readOrder"]
        },
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_icon_duration_child(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name the two stored child members at a certified parent field range."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("parentUnionTag") != contract["parentUnionTag"]
        or native_validation.get("readOrder") != contract["wrapper"]["readOrder"]
    ):
        raise ValueError(f"{LABEL}:native-not-validated")
    if (
        not isinstance(source, str) or not source
        or type(start) is not int or type(end) is not int
        or not 0 <= start < end <= len(data)
        or not isinstance(logical_sha256, str)
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}:source-or-range")
    reader = Reader(data, source, end)
    reader.pos = start
    reader.header(2)
    enum_start = reader.pos
    enum_raw = reader.take(4, "durationSourceType.raw-int32")
    string_start = reader.pos
    reader.byte_payload()
    if reader.pos != end:
        raise ValueError(f"{LABEL}:child-end={reader.pos}; expected={end}")
    string_count = struct.unpack_from("<i", data, string_start)[0]
    fields = [
        {"fieldName": "durationSourceType", "start": enum_start,
         "end": string_start, "storedInt32": struct.unpack("<i", enum_raw)[0],
         "rawHex": enum_raw.hex().upper()},
        {"fieldName": "timedMarkerId", "start": string_start,
         "end": end, "storedByteLength": string_count,
         "sourceBytesSha256": (
             hashlib.sha256(data[string_start + 4:end]).hexdigest().upper()
             if string_count >= 0 else None
         ), "stringDecodeClaimed": False},
    ]
    return {
        "schema": SCHEMA, "status": "named-direct-members-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "memberCount": 2,
        "namedFields": fields, "wholeStoredSpanExact": True,
        "runtimeDurationSelectionKnown": False,
        "wholeBuffDataExact": False,
    }
