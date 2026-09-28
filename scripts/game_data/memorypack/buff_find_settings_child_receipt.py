"""Selected native and exact-byte BuffFindSettings/GameplayTagQuery receipt.

``FinishBuffAdvanced.buffSettings`` is a ``BuffFindSettings``. Its reader
consumes ``buffIdList``, ``checkType`` and ``tagQuery`` in generated setter
order; the nested ``GameplayTagQuery`` reader stores ``queryType`` and
``tags``. Selected normal/null reader windows, source contexts, runtime field
offsets and direct destination stores authenticate these five names. The
gate rechecks every source and parent action and closes each reached
``buffSettings`` span at its independently fixed boundary, including
positive string lists and positive packed tag arrays.

Evidence boundary: the string list's selected generic type and signed-length
byte grammar do not identify a live ``ListFormatter<string>`` provider, so
decoded text and provider parity are ``conditional``. Tag values are raw
stored IDs; the runtime buff finder and tag predicate stay unresolved.
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
from scripts.game_data.memorypack.wrapper_members import derive_from_image


LABEL = "buffFindSettingsChild"
SCHEMA = "endfield.buff-find-settings-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_find_settings_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-find-settings-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    children = contract.get("children")
    if (
        contract.get("sourceReaderContract") != "buff_b4_native.json"
        or contract.get("parentActionContract")
        != "buff_finish_buff_advanced_action_receipt_native.json"
        or len(contract.get("sourceReaderMethodIndices", ())) != 4
        or len(contract.get("sourceReaderWindowStarts", ())) != 6
        or not isinstance(children, list) or len(children) != 2
        or [(row.get("sourceKindsKey"), len(row.get("fields", ())))
            for row in children] != [("finder-profile", 3), ("query-profile", 2)]
        or set(contract.get("contextRvas", ())) != {"buffIdList", "tagQuery", "tags"}
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _store_offset(raw: bytes) -> int:
    cursor = 0
    if raw[cursor:cursor + 1] in (b"\xf2", b"\xf3"):
        cursor += 1
    if cursor < len(raw) and 0x40 <= raw[cursor] <= 0x4F:
        cursor += 1
    if raw[cursor:cursor + 2] == b"\x0f\x11":
        cursor += 2
    elif raw[cursor:cursor + 1] in (b"\x88", b"\x89"):
        cursor += 1
    else:
        raise ValueError(f"{LABEL}.native:not-a-direct-store")
    if cursor >= len(raw):
        raise ValueError(f"{LABEL}.native:short-store")
    modrm = raw[cursor]
    cursor += 1
    mode, base = modrm >> 6, modrm & 7
    if mode not in (1, 2) or base not in (0, 1, 5, 7):
        raise ValueError(f"{LABEL}.native:destination-register")
    width = 1 if mode == 1 else 4
    if cursor + width != len(raw):
        raise ValueError(f"{LABEL}.native:store-width")
    return int.from_bytes(raw[cursor:], "little", signed=True)


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck selected reader windows, generated members and direct stores."""
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceReaderContract"]).read_bytes())
    parent = json.loads((CONTRACTS_DIR / contract["parentActionContract"]).read_bytes())
    expected = contract["nativeInputs"]
    if (source.get("schemaVersion") != 1
            or parent.get("nativeInputs") != expected
            or any(source.get("anonymousReadOrder", {}).get(row["sourceKindsKey"])
                   != [field["kind"] for field in row["fields"]]
                   for row in contract["children"])):
        raise ValueError(f"{LABEL}.native:source-contract-shape")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if (not unityplayer.is_file()
            or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    methods = [row for row in source["methods"]
               if row[0] in contract["sourceReaderMethodIndices"]]
    if [row[0] for row in methods] != contract["sourceReaderMethodIndices"]:
        raise ValueError(f"{LABEL}.native:reader-methods")
    for row in methods:
        image.validate_method_row(row, label=LABEL)
    windows = [row for row in source["codeWindows"]
               if row["startRva"] in contract["sourceReaderWindowStarts"]]
    if [row["startRva"] for row in windows] != contract["sourceReaderWindowStarts"]:
        raise ValueError(f"{LABEL}.native:reader-windows")
    image.check_windows(windows, label=LABEL)
    derived = derive_from_image(image)
    child_ranges = {}
    for child in contract["children"]:
        definition = child["typeDefinition"]
        wrapper = image.metadata.types[definition]
        fields = child["fields"]
        if image.type_name(definition) != child["typeName"]:
            raise ValueError(f"{LABEL}.native:wrapper-type={definition}")
        setters = image.setter_methods(wrapper, parameter="typeName", label=LABEL)
        if setters != [[field["setterMethodIndex"], f"set___{field['name']}__",
                        field["setterParameterType"]] for field in fields]:
            raise ValueError(f"{LABEL}.native:setters={definition}")
        resolved = derived.get(definition)
        if (resolved is None or len(resolved.members) != len(fields)
                or [(item.name, item.method_index, item.declared_type)
                    for item in resolved.members]
                != [(field["name"], field["setterMethodIndex"], field["declaredType"])
                    for field in fields]):
            raise ValueError(f"{LABEL}.native:declared-types={definition}")
        runtime_definition = child["runtimeTypeDefinition"]
        if image.type_name(runtime_definition) != child["runtimeTypeName"]:
            raise ValueError(f"{LABEL}.native:runtime-type={definition}")
        offsets = runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, runtime_definition,
        )
        if offsets != {field["name"]: field["runtimeFieldOffset"] for field in fields}:
            raise ValueError(f"{LABEL}.native:runtime-fields={definition}")
        method = next(row for row in methods if row[1] == child["typeName"])
        normal = next((row for row in windows if row["startRva"] == method[3]), None)
        if normal is None:
            raise ValueError(f"{LABEL}.native:normal-window={definition}")
        child_ranges[child["sourceKindsKey"]] = (normal["startRva"], normal["endRva"])
        prior = normal["startRva"]
        for field in fields:
            rva, raw_hex = field["store"]
            raw = bytes.fromhex(raw_hex)
            if (not prior < rva < normal["endRva"]
                    or rva + len(raw) > normal["endRva"]
                    or image.pe.bytes_at_va(image.pe.image_base + rva, len(raw)) != raw
                    or _store_offset(raw) != field["runtimeFieldOffset"]):
                raise ValueError(f"{LABEL}.native:destination-store={field['name']}")
            prior = rva
    contexts = {row["instructionRva"]: row for row in source["nestedContexts"]}
    for name, rva in contract["contextRvas"].items():
        context = contexts.get(rva)
        if context is None:
            raise ValueError(f"{LABEL}.native:context={name}")
        instruction = image.pe.bytes_at_va(image.pe.image_base + rva, 7)
        if (instruction.hex().upper() != context["instructionHex"].upper()
                or instruction[:3] not in (b"\x48\x8b\x15", b"\x48\x8b\x35")):
            raise ValueError(f"{LABEL}.native:context-instruction={name}")
        cell = image.pe.image_base + rva + 7 + struct.unpack_from("<i", instruction, 3)[0]
        if (cell != context["cellVa"]
                or image.pe.bytes_at_va(cell, 8).hex().upper()
                != context["usageRawHex"].upper()):
            raise ValueError(f"{LABEL}.native:context-usage={name}")
    finder_start, finder_end = child_ranges["finder-profile"]
    query_start, query_end = child_ranges["query-profile"]
    if (not finder_start < contract["contextRvas"]["buffIdList"]
            < contract["children"][0]["fields"][0]["store"][0]
            < contract["children"][0]["fields"][1]["store"][0]
            < contract["contextRvas"]["tagQuery"]
            < contract["children"][0]["fields"][2]["store"][0] < finder_end
            or not query_start < contract["children"][1]["fields"][0]["store"][0]
            < contract["contextRvas"]["tags"]
            < contract["children"][1]["fields"][1]["store"][0] < query_end):
        raise ValueError(f"{LABEL}.native:source-read-and-store-order")
    return {
        "status": "validated", "nativeInputs": expected,
        "readOrders": {child["sourceKindsKey"]: [field["name"] for field in child["fields"]]
                       for child in contract["children"]},
        "directDestinationStores": sum(len(child["fields"])
                                        for child in contract["children"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_find_settings_child_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name one bounded BuffFindSettings child and its nested tag query."""
    contract = _contract()
    orders = {child["sourceKindsKey"]: [field["name"] for field in child["fields"]]
              for child in contract["children"]}
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("readOrders") != orders):
        raise ValueError(f"{LABEL}.decode:native-not-validated")
    if (not isinstance(source, str) or not source
            or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
            or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:source-or-span")
    reader = Reader(data, source, end)
    reader.pos = start
    members = []
    query_members = []
    list_count = None
    tag_count = None
    if reader.peek() == 0xFF:
        reader.take(1, "null-buff-find-settings")
        status = "exact-null"
        query_status = None
    else:
        reader.header(len(orders["finder-profile"]))
        field_start = reader.pos
        list_count = reader.count(4, reserve=5, nullable=True)
        for _ in range(max(0, list_count)):
            reader.byte_payload()
        members.append({"fieldName": orders["finder-profile"][0],
                        "start": field_start, "end": reader.pos,
                        "count": list_count, "kind": "counted-byte-payloads"})
        field_start = reader.pos
        reader.take(4, "checkType")
        members.append({"fieldName": orders["finder-profile"][1],
                        "start": field_start, "end": reader.pos,
                        "kind": "scalar32"})
        field_start = reader.pos
        if reader.peek() == 0xFF:
            reader.take(1, "null-tag-query")
            query_status = "exact-null"
        else:
            reader.header(len(orders["query-profile"]))
            inner_start = reader.pos
            reader.take(4, "queryType")
            query_members.append({"fieldName": orders["query-profile"][0],
                                  "start": inner_start, "end": reader.pos,
                                  "kind": "scalar32"})
            inner_start = reader.pos
            tag_count = reader.count(4, nullable=True)
            reader.take(max(0, tag_count) * 4, "tags")
            query_members.append({"fieldName": orders["query-profile"][1],
                                  "start": inner_start, "end": reader.pos,
                                  "count": tag_count, "kind": "counted-scalar32"})
            query_status = "named-direct-members-exact-span"
        members.append({"fieldName": orders["finder-profile"][2],
                        "start": field_start, "end": reader.pos,
                        "kind": "query-profile", "queryStatus": query_status,
                        "namedQueryFields": query_members})
        status = "named-direct-members-exact-span"
    if (reader.pos != end or (members and (
            members[0]["start"] != start + 1
            or any(left["end"] != right["start"]
                   for left, right in zip(members, members[1:]))))):
        raise ValueError(f"{LABEL}.decode:child-end={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA, "source": source, "logicalSha256": logical_sha256.upper(),
        "status": status, "start": start, "end": end,
        "namedFields": members, "buffIdListCount": list_count,
        "tagCount": tag_count, "wholeChildSpanExact": True,
        "runtimePredicateProved": False, "wholeBuffDataExact": False,
    }
