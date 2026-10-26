"""Selected-build ownership and raw-byte decoder for BuffData.dispelConfig.

Field seven is copied, not member-read: the root reader checks and copies
eight source bytes directly into the installed ``BuffData.dispelConfig``
value. Metadata places ``canBeDispelled`` at byte zero and the signed
``DispelLevel`` value at byte four; the three intervening bytes are preserved
as padding.

The contract records no address of its own beyond what ``derive`` recomputes
on the selected build: the root contract (``buff_root_no_positive_native``,
validated first) proves the raw8 source guard and the store into
``BuffData.dispelConfig``; this module decodes the root body between those two
instructions and requires exactly the eight-byte copy shape (load the source
pointer, dereference one qword, advance the pointer and both consumed counters
by eight), then re-derives the setter parameter, owner field type, value
field order/offsets/types, boxed size and enum underlying type. The validator
refuses a contract that differs from that derivation. Missing or changed
native inputs keep the raw eight bytes and the naming blocker. The decoder
does not constrain padding or enum values, and stored values do not prove
runtime dispel decisions or enum effects.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.il2cpp.native_image import (
    native_validation_failure,
    open_native_image,
    read_reviewed_contract,
)
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffDispelConfig"
CONTRACT_PATH = CONTRACTS_DIR / "buff_dispel_config_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
SCHEMA = "endfield.buff-dispel-config-native-contract.v2"
OBJECT_HEADER_SIZE = 16
FIELD_NAME = "dispelConfig"
COPY_SHAPE = (
    ("mov {ptr}, [rdi+0x50]", "load current source pointer"),
    ("mov {val}, [{ptr}]", "load raw eight-byte value"),
    ("add [rdi+0x50], 0x8", "advance source pointer by eight"),
    ("add [rdi+0x40], 0x8", "advance consumed byte count by eight"),
    ("add [rdi+0x44], 0x8", "advance secondary byte count by eight"),
)
EVIDENCE = {
    "exact": "On the selected build the root Deserialize method checks eight available source bytes, copies one raw qword and advances the source pointer and both consumed counters by eight before storing it into BuffData.dispelConfig; the selected field-layout table places a bool at byte zero and a signed int32 enum at byte four. The three intervening bytes are preserved as padding.",
    "direct": "The selected generated wrapper declares set___dispelConfig__, and metadata names the two instance fields and the DispelLevel enum's int32 underlying value.",
    "structuralOnly": "The child decoder reports stored bytes and values. It does not constrain padding contents or enum values to those observed in the corpus.",
    "unresolved": "Runtime dispel decisions, enum effects, alternate native builds, and other BuffData naming blockers are outside this contract.",
}


def _fail(detail: str) -> None:
    raise ValueError(f"{LABEL}.native:{detail}")


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )
    return value


def _selected_type(image: Any, name: str) -> Any:
    matches = [row for row in image.metadata.types
               if image.metadata.type_full_name(row) == name]
    if len(matches) != 1:
        _fail(f"type={name}; matches={len(matches)}")
    return matches[0]


def _field_type_name(image: Any, field: Any) -> str:
    table = int(image.registration["types"], 16)
    pointer = image.pe.u64_at_va(table + field.type_index * 8)
    return runtime_type_name(image.pe, image.metadata, pointer)


def _copy_instructions(image: Any, root_field: dict[str, Any]) -> list[list[Any]]:
    """Decode the root body between the raw8 guard and the store; require the copy shape."""
    base = image.pe.image_base
    source, store = root_field["source"], root_field["store"]
    if source["kind"] != "raw8" or store["kind"] != "qword-rax-disp32":
        _fail("root-field-kind")
    start, stop = source["rva"], store["rva"] + len(bytes.fromhex(store["hex"]))
    rows = image.mapper.decode_x64_subset(
        image.pe.bytes_at_va(base + start, stop - start), base + start, stop_offset=stop - start)
    decoded = [(int(r["va"], 16) - base if isinstance(r["va"], str) else r["va"] - base,
                r["bytes"].replace(" ", "").upper(), r["text"]) for r in rows]
    if not decoded or decoded[0][0] != start or decoded[-1][0] != store["rva"]:
        _fail("copy-decode-boundary")
    found: list[list[Any]] = [[start, source["hex"], "require eight available source bytes"]]
    ptr = val = None
    cursor = 1
    for pattern, note in COPY_SHAPE:
        while cursor < len(decoded) - 1:
            rva, raw, text = decoded[cursor]
            cursor += 1
            if ptr is None and text.startswith("mov ") and text.endswith(", [rdi+0x50]"):
                ptr = text[4:].split(",")[0]
            if ptr is not None and val is None and text.startswith("mov ") and text.endswith(f", [{ptr}]"):
                val = text[4:].split(",")[0]
            if ptr is not None and text == pattern.format(ptr=ptr, val=val):
                found.append([rva, raw, note])
                break
        else:
            _fail(f"copy-shape-missing={note}")
    if val is None or store["hex"][:6].upper() != {"rbx": "488998", "rbp": "4889A8"}.get(val, ""):
        _fail(f"copy-store-register={val}")
    found.append([store["rva"], store["hex"].upper(), "store value into BuffData.dispelConfig"])
    return found


def derive(image: Any, inputs: dict[str, str], root: dict[str, Any]) -> dict[str, Any]:
    """Re-derive every recorded dispel fact from the selected build and root contract."""
    field = next(row for row in root["fields"] if row["name"] == FIELD_NAME)
    setter_index, setter_name = field["setterMethod"]
    setter = image.metadata.methods[setter_index]
    wrapper = image.metadata.types[setter.declaring_type]
    if (image.metadata.type_full_name(wrapper) != root["rootWrapper"]
            or image.metadata.string(setter.name_index) != setter_name
            or setter.parameter_count != 1):
        _fail("wrapper-setter")
    value_type = _field_type_name(image, image.metadata.parameters[setter.parameter_start])
    owner = _selected_type(image, root["ownerType"])
    owner_declared = [f for f in image.metadata.fields_for(owner)
                      if image.metadata.string(f.name_index) == FIELD_NAME]
    if len(owner_declared) != 1 or _field_type_name(image, owner_declared[0]) != value_type:
        _fail("owner-field-type")
    owner_offset = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, owner.index)[FIELD_NAME]
    if owner_offset != field["ownerFieldOffset"] or bytes.fromhex(field["store"]["hex"]) != \
            b"\x48\x89\x98" + struct.pack("<I", owner_offset):
        _fail("owner-store-offset")
    value = _selected_type(image, value_type)
    fields = image.metadata.fields_for(value)
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, value.index)
    value_fields = [{"name": image.metadata.string(f.name_index), "type": _field_type_name(image, f),
                     "runtimeOffset": offsets[image.metadata.string(f.name_index)],
                     "wireOffset": offsets[image.metadata.string(f.name_index)] - OBJECT_HEADER_SIZE}
                    for f in fields]
    size_pointer = image.pe.u64_at_va(int(image.registration["typeDefinitionsSizes"], 16) + value.index * 8)
    boxed = image.pe.u32_at_va(size_pointer)
    if [row["name"] for row in value_fields] != ["canBeDispelled", "dispelledLevel"] or \
            [row["wireOffset"] for row in value_fields] != [0, 4] or boxed - OBJECT_HEADER_SIZE != 8:
        _fail("value-layout")
    enum_name = value_fields[1]["type"]
    enum = _selected_type(image, enum_name)
    underlying = next(f for f in image.metadata.fields_for(enum)
                      if image.metadata.string(f.name_index) == "value__")
    return {
        "schema": SCHEMA,
        "status": "exact-current-build",
        "nativeInputs": inputs,
        "reviewedDependencies": [ROOT_CONTRACT_PATH.name],
        "rootMethod": root["rootMethod"],
        "setterMethod": [setter_index, root["rootWrapper"], setter_name],
        "wrapperSetterParameterTypeIndex": image.metadata.parameters[setter.parameter_start].type_index,
        "ownerField": f"{root['ownerType']}::{FIELD_NAME}",
        "valueType": value_type,
        "valueTypeDefinition": value.index,
        "valueTypeBoxedSize": boxed,
        "valueTypeRawSize": boxed - OBJECT_HEADER_SIZE,
        "valueFields": value_fields,
        "enumType": enum_name,
        "enumUnderlyingType": _field_type_name(image, underlying),
        "sourceToFieldInstructions": _copy_instructions(image, field),
        "evidenceBoundary": EVIDENCE,
    }


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    """Validate the root contract, then require this contract to equal a fresh derivation."""
    from scripts.game_data.memorypack import buff_root_no_positive_native
    try:
        contract = _contract()
        expected = contract["nativeInputs"]
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=gameassembly, metadata=metadata,
        )
        if gate.status != "validated":
            return {"status": gate.status, "nativeStatus": gate.status, "detail": gate.detail,
                    "evidenceBoundary": "No named child fields on missing or mismatched native inputs."}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file():
            return {"status": "missing", "nativeStatus": "missing", "detail": f"{unity} is absent"}
        if sha256_file_upper(unity) != expected["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "nativeStatus": "mismatched",
                    "detail": "UnityPlayer.dll hash differs"}
        if contract["reviewedDependencies"] != [ROOT_CONTRACT_PATH.name]:
            _fail("dependency-list")
        root_status = buff_root_no_positive_native.validate_current_native_contract(
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        if root_status.get("status") != "validated":
            return {"status": root_status.get("status", "invalid"),
                    "nativeStatus": root_status.get("status"), "detail": f"root: {root_status.get('detail')}"}
        root = buff_root_no_positive_native._contract()
        image = open_native_image(gate.gameassembly, gate.metadata)
        derived = json.loads(json.dumps(derive(image, expected, root)))
        for key in sorted(set(contract) | set(derived)):
            if contract.get(key) != derived.get(key):
                _fail(f"derivation-differs={key}")
        return {"status": "validated", "nativeStatus": "validated",
                "field": contract["ownerField"], "rawSize": contract["valueTypeRawSize"],
                "valueFields": contract["valueFields"], "nativeInputs": expected,
                "evidenceBoundary": contract["evidenceBoundary"]}
    except (ValueError, KeyError, IndexError, TypeError, OSError, StopIteration) as error:
        return native_validation_failure(error, label=LABEL, source_path=CONTRACT_PATH)


def decode_dispel_config(
    data: bytes, start: int, end: int, *, native_validation: dict[str, Any]
) -> dict[str, Any]:
    """Decode one authenticated raw-eight value; keep padding and enum raw."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.boundary:invalid")
    if end - start != 8:
        raise ValueError(f"{LABEL}.boundary:expected-eight actual={end - start}")
    raw_bool = data[start]
    if raw_bool not in (0, 1):
        raise ValueError(f"{LABEL}.canBeDispelled:invalid-bool={raw_bool}")
    padding = data[start + 1:start + 4]
    raw_enum = data[start + 4:end]
    level = struct.unpack("<i", raw_enum)[0]
    return {
        "status": "exact", "startOffset": start, "consumedEnd": end,
        "wholeValueExact": True, "representation": "unmanaged-struct-raw8",
        "fields": [
            {"name": "canBeDispelled", "start": start, "end": start + 1,
             "declaredType": "bool", "rawByte": raw_bool, "value": bool(raw_bool),
             "boundaryClass": "exact-cursor"},
            {"name": "dispelledLevel", "start": start + 4, "end": end,
             "declaredType": "Beyond.Gameplay.Core.DispelLevel", "rawBitsHex": raw_enum.hex().upper(),
             "rawSignedValue": level, "boundaryClass": "exact-cursor"},
        ],
        "paddingRange": [start + 1, start + 4],
        "paddingHex": padding.hex().upper(),
        "evidenceBoundary": "Stored native value layout only; no runtime dispel behavior.",
    }


def main(argv: list[str] | None = None) -> int:
    """Print (or with ``--write`` record) the derivation for the selected build."""
    from scripts.game_data.levelscript_two_routes_native import open_selected_build
    from scripts.game_data.memorypack import buff_root_no_positive_native
    args = sys.argv[1:] if argv is None else argv
    image, inputs = open_selected_build()
    text = json.dumps(derive(image, inputs, buff_root_no_positive_native._contract()),
                      indent=2, ensure_ascii=False) + "\n"
    if args == ["--write"]:
        CONTRACT_PATH.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
