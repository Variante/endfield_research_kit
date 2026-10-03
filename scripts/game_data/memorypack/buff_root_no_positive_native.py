"""Selected BuffData root read order for records without recursive list children.

The reviewed root body already has a complete native code window. This
contract adds the per-member source-call, generic argument, and destination
store joins. The byte reader in ``buff_root_no_positive`` uses these facts only
for the null/empty recursive collection branch.

``buff_root_no_positive_native.json`` joins all 30 root source reads,
generic contexts, generated setters and destination stores to the installed
native body; the positive branches in ``buff_root_no_positive`` reuse this
root order and add their own child contracts. A different installed build
yields no rows.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffRootNoPositive"
CONTRACT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"
INT_CONTRACT_PATH = CONTRACTS_DIR / "buff_16b_native.json"
PROVIDER_CONTRACT_PATH = CONTRACTS_DIR / "buff_b4_native.json"
CALL_KINDS = {"list", "object", "packed-gameplay-tag-array", "bool", "string"}
INLINE_KINDS = {"raw8", "byte"}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.buff-root-no-positive-native-contract.v1",
        status="exact-current-build",
        label=LABEL,
    )
    fields = contract.get("fields")
    if (
        contract.get("reviewedDependencies", [None])[0] != ROOT_CONTRACT_PATH.name
        or INT_CONTRACT_PATH.name not in contract.get("reviewedDependencies", ())
        or PROVIDER_CONTRACT_PATH.name not in contract.get("reviewedDependencies", ())
        or contract.get("conditionalProviderEvidence", {}).get("contract") != PROVIDER_CONTRACT_PATH.name
        or not isinstance(fields, list)
        or contract.get("rootMemberCount") != len(fields)
        or len(fields) != 30
        or [f.get("index") for f in fields] != list(range(len(fields)))
        or len({f.get("name") for f in fields}) != len(fields)
        or any(f.get("source", {}).get("kind") not in CALL_KINDS | INLINE_KINDS for f in fields)
    ):
        raise ValueError(f"{LABEL}.contract:root-shape")
    return contract


def _selected_type(image: Any, name: str) -> Any:
    rows = [row for row in image.metadata.types
            if image.metadata.type_full_name(row) == name]
    if len(rows) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(rows)}")
    return rows[0]


def _expected_store(kind: str, offset: int) -> bytes:
    if kind == "qword-rcx-disp8" and 0 <= offset < 128:
        return b"\x48\x89\x41" + bytes((offset,))
    if kind == "qword-rcx-disp32":
        return b"\x48\x89\x81" + struct.pack("<I", offset)
    if kind == "qword-rax-disp32":
        return b"\x48\x89\x98" + struct.pack("<I", offset)
    if kind == "byte-rcx-disp8" and 0 <= offset < 128:
        return b"\x88\x41" + bytes((offset,))
    if kind == "byte-rcx-disp32":
        return b"\x88\x81" + struct.pack("<I", offset)
    if kind == "byte-rax-disp8" and 0 <= offset < 128:
        return b"\x44\x88\x70" + bytes((offset,))
    raise ValueError(f"{LABEL}.native:unsupported-store={kind}:{offset}")


def _check_context(image: Any, context: dict[str, Any], declared: str, kind: str) -> None:
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    if list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:method-spec-record")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:method-argument-count")
    argument = instance.arguments[0]
    name = runtime_type_name(image.pe, image.metadata, argument.type_pointer_va)
    if (argument.raw_type_record_hex != context["argumentRawHex"]
            or name != context["argumentType"]):
        raise ValueError(f"{LABEL}.native:method-argument")
    expected = declared[:-2] if kind == "packed-gameplay-tag-array" else declared
    if name != expected:
        raise ValueError(f"{LABEL}.native:source-field-type={name}!={expected}")


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    """Authenticate all selected root reads and direct stores, or fail closed."""
    contract = _contract()
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail,
                "evidenceBoundary": "No selected root ownership on changed native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != inputs["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}

    image = open_native_image(gate.gameassembly, gate.metadata)
    root = json.loads(ROOT_CONTRACT_PATH.read_bytes())
    child_int = json.loads(INT_CONTRACT_PATH.read_bytes())
    provider = json.loads(PROVIDER_CONTRACT_PATH.read_bytes())
    if (
        root.get("schemaVersion") != 1 or child_int.get("schemaVersion") != 1
        or provider.get("schemaVersion") != 1
        or root["methods"][1] != contract["rootMethod"]
        or root["codeWindows"][0]["startRva"] != contract["rootMethod"][3]
        or contract["conditionalProviderEvidence"]["codeWindowIndices"] != [9, 10, 11]
    ):
        raise ValueError(f"{LABEL}.native:reviewed-dependency")
    for method in root["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(root["codeWindows"], label=LABEL)
    image.check_windows([provider["codeWindows"][index] for index in (9, 10, 11)], label=LABEL)
    for method in child_int["methods"][2:]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(child_int["codeWindows"][4:], label=LABEL)
    int_child = contract["blackboardIntChild"]
    int_wrapper = image.metadata.types[int_child["wrapperTypeDefinition"]]
    int_base = image.metadata.types[int_child["baseTypeDefinition"]]
    if (
        image.metadata.type_full_name(int_wrapper) != int_child["wrapperType"]
        or image.metadata.type_full_name(int_base) != int_child["baseType"]
        or int_wrapper.parent_index != int_base.byval_type_index
        or image.setter_methods(int_base, parameter="typeName", label=LABEL)
        != int_child["setterMethods"]
    ):
        raise ValueError(f"{LABEL}.native:blackboard-int-child")
    image.check_instruction_windows([contract["headerInstruction"]], label=LABEL)
    if (contract["headerInstruction"][1] !=
            (b"\x40\x80\xFD" + bytes((contract["rootMemberCount"],))).hex().upper()):
        raise ValueError(f"{LABEL}.native:root-member-count")

    wrapper = _selected_type(image, contract["rootWrapper"])
    owner = _selected_type(image, contract["ownerType"])
    setters = image.setter_methods(wrapper, label=LABEL)
    if setters != [f["setterMethod"] for f in contract["fields"]]:
        raise ValueError(f"{LABEL}.native:setter-order")
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
    owner_fields = {image.metadata.string(row.name_index): row
                    for row in image.metadata.fields_for(owner)}
    helper_targets: dict[str, set[int]] = {}
    previous = contract["headerInstruction"][0]
    root_end = root["codeWindows"][0]["endRva"]
    for field in contract["fields"]:
        name = field["name"]
        source = field["source"]
        store = field["store"]
        read_rva = source["rva"]
        store_rva = store["rva"]
        prior_store_rva = previous
        if (name not in offsets or name not in owner_fields
                or field["ownerFieldOffset"] != offsets[name]
                or not previous < read_rva < store_rva < root_end):
            raise ValueError(f"{LABEL}.native:member-order={name}")
        pointer = image.pe.u64_at_va(
            int(image.registration["types"], 16) + owner_fields[name].type_index * 8
        )
        declared = runtime_type_name(image.pe, image.metadata, pointer)
        if declared != field["declaredType"]:
            raise ValueError(f"{LABEL}.native:field-type={name}")
        image.check_instruction_windows(
            [[read_rva, source["hex"]], [store_rva, store["hex"]]], label=LABEL,
        )
        if bytes.fromhex(store["hex"]) != _expected_store(store["kind"], offsets[name]):
            raise ValueError(f"{LABEL}.native:destination-store={name}")
        kind = source["kind"]
        if kind in CALL_KINDS:
            raw = bytes.fromhex(source["hex"])
            if len(raw) != 5 or raw[0] != 0xE8:
                raise ValueError(f"{LABEL}.native:source-call={name}")
            target = read_rva + 5 + struct.unpack_from("<i", raw, 1)[0]
            if target != source["targetRva"]:
                raise ValueError(f"{LABEL}.native:source-target={name}")
            helper_targets.setdefault(kind, set()).add(target)
            context = source.get("context")
            if kind in {"list", "object", "packed-gameplay-tag-array"}:
                if (not isinstance(context, dict)
                        or not prior_store_rva < context["instructionRva"] < read_rva):
                    raise ValueError(f"{LABEL}.native:source-context-order={name}")
                _check_context(image, context, declared, kind)
            elif context is not None:
                raise ValueError(f"{LABEL}.native:primitive-context={name}")
        elif kind == "raw8":
            if source["hex"] != "837F3008":
                raise ValueError(f"{LABEL}.native:raw8-source={name}")
        elif kind == "byte":
            if source["hex"] != "837F3001":
                raise ValueError(f"{LABEL}.native:byte-source={name}")
        previous = store_rva
    if any(len(targets) != 1 for targets in helper_targets.values()):
        raise ValueError(f"{LABEL}.native:helper-target-variation")
    return {
        "status": "validated", "nativeInputs": inputs,
        "memberCount": len(contract["fields"]),
        "sourceCallCount": sum(f["source"]["kind"] in CALL_KINDS for f in contract["fields"]),
        "genericContextCount": sum(bool(f["source"].get("context")) for f in contract["fields"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }
