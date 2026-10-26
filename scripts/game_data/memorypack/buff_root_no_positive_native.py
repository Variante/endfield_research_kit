"""Selected BuffData root read order for records without recursive list children.

``buff_root_no_positive_native.json`` (schema v2) is self-contained: it pins
the root ``Deserialize`` method row, every range of its AMD64 unwind-chain
family as a hashed code window, the ``cmp bpl,<memberCount>`` header, and for
each of the 30 generated setters the source read, generic method-spec context
and destination store inside the contiguous primary body. ``id`` is a
``pooled-string`` read: a signed StringPool index whose helper target is
re-proved through ``pooled_source_helper`` (the installed build no longer
writes inline UTF-8 strings). Helper call targets must be uniform per kind.

The byte reader in ``buff_root_no_positive`` uses these facts for the
null/empty recursive collection branch; its positive branches reuse this root
order and add their own child contracts. The contract is regenerated, never
hand-carried, by ``python -m scripts.game_data.buff_root_regenerate --write``.
A different installed build yields no rows (``mismatched``/``missing``).
"""
from __future__ import annotations

import hashlib
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffRootNoPositive"
CONTRACT_PATH = CONTRACTS_DIR / "buff_root_no_positive_native.json"
SCHEMA = "endfield.buff-root-no-positive-native-contract.v2"
CALL_KINDS = {"list", "object", "packed-gameplay-tag-array", "bool", "pooled-string"}
INLINE_KINDS = {"raw8", "byte"}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema=SCHEMA,
        status="exact-current-build",
        label=LABEL,
    )
    fields = contract.get("fields")
    if (
        not isinstance(fields, list)
        or not contract.get("codeWindows")
        or contract.get("bodyRange", [None])[0] != contract.get("rootMethod", [None] * 4)[3]
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
    image.validate_method_row(contract["rootMethod"], label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)
    body_start, root_end = contract["bodyRange"]
    covered = body_start
    for window in sorted(contract["codeWindows"], key=lambda w: w["startRva"]):
        if window["startRva"] == covered:
            covered = window["endRva"]
    if covered != root_end:
        raise ValueError(f"{LABEL}.native:body-range")
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
            if kind == "pooled-string":
                pooled_source_helper.validate_on_image(image, image.pe.image_base + target, inputs)
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
