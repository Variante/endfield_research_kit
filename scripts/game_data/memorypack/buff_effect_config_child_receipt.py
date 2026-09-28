"""Selected native and exact-byte child receipt for Buff EffectActionCfg.

The 85 direct fields are named at a certified EffectAction.effectActionCfg
span. Nested values retain their prior structural framing; the enclosing
BuffData record is not promoted to a whole named schema.

The generated wrapper's setter order agrees with the selected reader's 85
source operations, and every operation has a checked destination store at
the corresponding runtime field offset; vector members also have their
companion stores checked. The runtime type has two additional fields,
``forceGuardEffect`` and ``centerOffset``, that this serialized wrapper
does not read. The gate reparses each selected ``EffectAction`` and requires
the child to end at the independently certified parent field boundary.
Strings stay signed-length byte spans. The ``TerrainEffectData`` array is
proved only on its null or empty branch; positive arrays are refused, and
effect execution stays unresolved. The three ``BlackboardVector3`` members
and scalar blackboard children are named by
``buff_effect_vector_child_receipt``.
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


LABEL = "buffEffectConfigChild"
SCHEMA = "endfield.buff-effect-config-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_effect_config_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-effect-config-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    members = contract.get("readOrder")
    if (
        contract.get("sourceReaderContract") != "buff_9a_native.json"
        or contract.get("parentActionContract") != "buff_a2_native.json"
        or len(contract.get("sourceReaderMethodIndices", [])) != 2
        or len(contract.get("sourceReaderWindowStarts", [])) != 3
        or type(contract.get("wrapperTypeDefinition")) is not int
        or type(contract.get("runtimeTypeDefinition")) is not int
        or not isinstance(members, list) or not members
        or [row.get("index") for row in members] != list(range(len(members)))
        or len({row.get("fieldName") for row in members}) != len(members)
        or any(not isinstance(row.get("storeWindows"), list)
               or len(row["storeWindows"]) != (2 if row.get("kind") in (8, 12) else 1)
               for row in members)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _store_displacement(raw: bytes) -> tuple[int, int]:
    """Read the destination displacement of a reviewed scalar/vector store."""
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
        raise ValueError(f"{LABEL}.native:short-direct-store")
    modrm = raw[cursor]
    cursor += 1
    mode, base = modrm >> 6, modrm & 7
    if mode not in (1, 2) or base not in (0, 1):
        raise ValueError(f"{LABEL}.native:destination-register")
    width = 1 if mode == 1 else 4
    if cursor + width != len(raw):
        raise ValueError(f"{LABEL}.native:store-width")
    return int.from_bytes(raw[cursor:], "little", signed=True), base


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck the reader, 85 setter types, and each direct destination store."""
    contract = _contract()
    expected = contract["nativeInputs"]
    source = json.loads((CONTRACTS_DIR / contract["sourceReaderContract"]).read_bytes())
    parent = json.loads((CONTRACTS_DIR / contract["parentActionContract"]).read_bytes())
    if (source.get("schemaVersion") != 1 or parent.get("schemaVersion") != 1
            or source.get("anonymousReadOrder", {}).get("member85")
            != [row["kind"] for row in contract["readOrder"]]
            or len(source.get("anonymousReadOrder", {}).get("member85SourceOperations", []))
            != len(contract["readOrder"])):
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
        raise ValueError(f"{LABEL}.native:source-reader-methods")
    for row in methods:
        image.validate_method_row(row, label=LABEL)
    windows = [row for row in source["codeWindows"]
               if row["startRva"] in contract["sourceReaderWindowStarts"]]
    if [row["startRva"] for row in windows] != contract["sourceReaderWindowStarts"]:
        raise ValueError(f"{LABEL}.native:source-reader-windows")
    image.check_windows(windows, label=LABEL)
    wrapper = image.metadata.types[contract["wrapperTypeDefinition"]]
    if image.type_name(contract["wrapperTypeDefinition"]) != contract["wrapperTypeName"]:
        raise ValueError(f"{LABEL}.native:wrapper-type")
    setters = image.setter_methods(wrapper, parameter="typeName", label=LABEL)
    expected_setters = [[row["setterMethodIndex"],
                         f"set___{row['fieldName']}__", row["setterParameterType"]]
                        for row in contract["readOrder"]]
    if setters != expected_setters:
        raise ValueError(f"{LABEL}.native:setter-order-or-parameter")
    derived = derive_from_image(image).get(contract["wrapperTypeDefinition"])
    if (derived is None or len(derived.members) != len(contract["readOrder"])
            or [(row.name, row.method_index, row.declared_type)
                for row in derived.members]
            != [(row["fieldName"], row["setterMethodIndex"], row["declaredType"])
                for row in contract["readOrder"]]):
        raise ValueError(f"{LABEL}.native:declared-member-types")
    if image.type_name(contract["runtimeTypeDefinition"]) != contract["runtimeTypeName"]:
        raise ValueError(f"{LABEL}.native:runtime-type")
    runtime_offsets = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration,
        contract["runtimeTypeDefinition"],
    )
    serialized_offsets = {row["fieldName"]: row["runtimeFieldOffset"]
                          for row in contract["readOrder"]}
    if (set(serialized_offsets) & set(contract["unserializedRuntimeFields"])
            or runtime_offsets != (serialized_offsets
                                   | contract["unserializedRuntimeFields"])):
        raise ValueError(f"{LABEL}.native:runtime-fields")
    operations = source["anonymousReadOrder"]["member85SourceOperations"]
    reader_start = methods[1][3]
    reader_windows = [row for row in windows if row["startRva"] == reader_start]
    if len(reader_windows) != 1:
        raise ValueError(f"{LABEL}.native:source-reader-normal-window")
    reader_end = reader_windows[0]["endRva"]
    for index, row in enumerate(contract["readOrder"]):
        operation = operations[index]
        start = operation["at"]
        end = (operations[index + 1]["at"]
               if index + 1 < len(operations) else reader_end)
        if row["sourceOperationRva"] != start or not reader_start <= start < end <= reader_end:
            raise ValueError(f"{LABEL}.native:source-operation={index}")
        if "call" in operation:
            raw = image.pe.bytes_at_va(image.pe.image_base + start, 5)
            if (raw[:1] != b"\xe8" or start + 5 + struct.unpack_from("<i", raw, 1)[0]
                    != operation["call"]):
                raise ValueError(f"{LABEL}.native:source-call={index}")
        store_windows = row["storeWindows"]
        expected_offsets = [row["runtimeFieldOffset"]]
        if row["kind"] == 8:
            expected_offsets.append(row["runtimeFieldOffset"] + 4)
        elif row["kind"] == 12:
            expected_offsets.append(row["runtimeFieldOffset"] + 8)
        if len(store_windows) != len(expected_offsets):
            raise ValueError(f"{LABEL}.native:store-count={index}")
        for (rva, raw_hex), field_offset in zip(store_windows, expected_offsets, strict=True):
            if not start <= rva < end or rva + len(raw_hex) // 2 > end:
                raise ValueError(f"{LABEL}.native:store-span={index}")
            raw = bytes.fromhex(raw_hex)
            if image.pe.bytes_at_va(image.pe.image_base + rva, len(raw)) != raw:
                raise ValueError(f"{LABEL}.native:store-bytes={index}")
            actual_offset, _base = _store_displacement(raw)
            if actual_offset != field_offset:
                raise ValueError(f"{LABEL}.native:destination-offset={index}")
    return {
        "status": "validated", "nativeInputs": expected,
        "readOrder": [{"fieldName": row["fieldName"], "kind": row["kind"]}
                      for row in contract["readOrder"]],
        "directDestinationStores": sum(len(row["storeWindows"])
                                        for row in contract["readOrder"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_effect_config_child_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name one independently bounded child while retaining nested limits."""
    contract = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("readOrder")
            != [{"fieldName": row["fieldName"], "kind": row["kind"]}
                for row in contract["readOrder"]]):
        raise ValueError(f"{LABEL}.decode:native-not-validated")
    if (not isinstance(source, str) or not source
            or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
            or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:source-or-span")
    reader = Reader(data, source, end)
    reader.pos = start
    if reader.peek() == 0xFF:
        reader.take(1, "null-effect-configuration")
        status = "exact-null"
        fields: list[dict[str, Any]] = []
    else:
        reader.header(len(contract["readOrder"]))
        fields = []
        for member in contract["readOrder"]:
            field_start = reader.pos
            kind = member["kind"]
            if type(kind) is int:
                reader.take(kind, member["fieldName"])
            elif kind == "payload":
                reader.byte_payload()
            elif kind == "scalar":
                reader.scalar_payload()
            elif kind == "vector":
                reader.vector_payload()
            elif kind == "empty-array":
                reader.empty_damage_collection("effect array")
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if reader.pos <= field_start:
                raise ValueError(f"{LABEL}.decode:field-no-progress={member['fieldName']}")
            fields.append({"fieldName": member["fieldName"], "kind": kind,
                           "start": field_start, "end": reader.pos})
        status = "named-direct-members-exact-span"
    if reader.pos != end or (fields and (
            fields[0]["start"] != start + 1
            or any(left["end"] != right["start"]
                   for left, right in zip(fields, fields[1:])))):
        raise ValueError(f"{LABEL}.decode:child-end={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA, "source": source, "logicalSha256": logical_sha256.upper(),
        "status": status, "start": start, "end": end,
        "namedFields": fields, "wholeChildSpanExact": True,
        "recursiveValueMeaningExact": False, "wholeBuffDataExact": False,
    }
