"""Regenerate the BuffData root read-order contract against the selected build.

Writes ``buff_root_no_positive_native.json`` (validated by
``memorypack/buff_root_no_positive_native.py``). Every native fact is derived
from the installed image; nothing is carried over from the previous contract
except the reviewed per-member source *kind* (``list``, ``object``,
``packed-gameplay-tag-array``, ``bool``, ``pooled-string``, ``raw8``,
``byte``), which the derivation must then re-prove.

What it derives: the root ``Deserialize`` method row by name, the complete
AMD64 unwind-chain family of that method as code windows (the contiguous
primary chain is the body the member reads must lie in), the
``cmp bpl,<memberCount>`` header, the generated setter order, and for each
member in setter order the first destination store after the previous one
whose bytes encode the member's runtime field offset, the helper call
immediately before it, and the rip-relative ``mov rdx`` method-spec load
between the previous store and that call.

It refuses (writes nothing) when a member count, setter list, field type,
helper uniformity per kind, store ordering, or context type differs from what
the reviewed kind requires. An inserted or removed member needs review.

Run: ``python -m scripts.game_data.buff_root_regenerate [--write]``.
"""
from __future__ import annotations

import copy
import json
import struct
import sys
from typing import Any

from scripts.game_data.buff_frontiers_regenerate import _nested_contexts, _type_definition
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.levelscript_two_routes_native import (
    RouteRefused,
    _deserialize_method,
    _window,
    open_selected_build,
)

CONTRACT = CONTRACTS_DIR / "buff_root_no_positive_native.json"
SCHEMA = "endfield.buff-root-no-positive-native-contract.v2"
INT_WRAPPER = "Beyond.MemoryPack.Beyond_Blackboard_BlackboardIntForMemoryPack"
INT_BASE = "Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_int_int_ForMemoryPack"
STORE_KINDS = (
    "qword-rcx-disp8", "qword-rcx-disp32", "qword-rax-disp32",
    "byte-rcx-disp8", "byte-rcx-disp32", "byte-rax-disp8",
)
CONTEXT_KINDS = {"list", "object", "packed-gameplay-tag-array"}
INLINE_SOURCE = {"raw8": "837F3008", "byte": "837F3001"}


def expected_store(kind: str, offset: int) -> bytes | None:
    """Return the store encoding for one reviewed kind, or ``None`` if out of range."""
    if kind == "qword-rcx-disp8":
        return b"\x48\x89\x41" + bytes((offset,)) if 0 <= offset < 128 else None
    if kind == "qword-rcx-disp32":
        return b"\x48\x89\x81" + struct.pack("<I", offset)
    if kind == "qword-rax-disp32":
        return b"\x48\x89\x98" + struct.pack("<I", offset)
    if kind == "byte-rcx-disp8":
        return b"\x88\x41" + bytes((offset,)) if 0 <= offset < 128 else None
    if kind == "byte-rcx-disp32":
        return b"\x88\x81" + struct.pack("<I", offset)
    if kind == "byte-rax-disp8":
        return b"\x44\x88\x70" + bytes((offset,)) if 0 <= offset < 128 else None
    raise ValueError(f"store-kind={kind}")


def _rows(image: Any, start: int, end: int) -> list[dict[str, Any]]:
    base = image.pe.image_base
    out = []
    for row in image.mapper.decode_x64_subset(image.pe.bytes_at_va(base + start, end - start),
                                              base + start, stop_offset=end - start):
        va = int(row["va"], 16) if isinstance(row["va"], str) else row["va"]
        raw = bytes.fromhex(row["bytes"].replace(" ", "")) if isinstance(row["bytes"], str) else bytes(row["bytes"])
        out.append({"rva": va - base, "raw": raw, "text": row["text"]})
    return out


def _context_row(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "instructionRva": context["instructionRva"], "instructionHex": context["instructionHex"],
        "usageRawHex": context["usageRawHex"], "methodSpecIndex": context["methodSpecIndex"],
        "methodSpec": context["methodSpec"], "argumentRawHex": context["argumentRawHex"],
    }


def regenerate(reviewed: dict[str, Any], image: Any, inputs: dict[str, str]) -> dict[str, Any]:
    base = image.pe.image_base
    wrapper_name = reviewed["rootWrapper"]
    wrapper = image.metadata.types[_type_definition(image, wrapper_name)]
    owner_def = _type_definition(image, reviewed["ownerType"])
    owner = image.metadata.types[owner_def]
    root = _deserialize_method(image, wrapper_name)
    family = image.unwind_index.family(root[3])
    ranges = [r["runtimeTriple"][:2] for r in family["ranges"]]
    body_end = root[3]
    for start, end in ranges:
        if start == body_end or start == root[3]:
            body_end = max(body_end, end)
    windows = [_window(image, base + s, base + e,
                       f"complete unwind-chain range {i} of the selected root Deserialize family")
               for i, (s, e) in enumerate(ranges)]
    rows = _rows(image, root[3], body_end)

    count = len(reviewed["fields"])
    header = [r for r in rows if r["raw"] == b"\x40\x80\xFD" + bytes((count,))]
    if len(header) != 1:
        raise RouteRefused(f"root-header:found={len(header)}")
    setters = image.setter_methods(wrapper, label="buffRootRegenerate")
    if [s[1] for s in setters] != [f["setterMethod"][1] for f in reviewed["fields"]]:
        raise RouteRefused(f"root-setters:installed={[s[1] for s in setters]}")
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
    owner_fields = {image.metadata.string(r.name_index): r for r in image.metadata.fields_for(owner)}
    contexts = {c["instructionRva"]: c for c in _nested_contexts(
        image, {"startRva": root[3], "endRva": body_end})}

    fields = []
    position = rows.index(header[0])
    previous_store = header[0]["rva"]
    for reviewed_field, setter in zip(reviewed["fields"], setters):
        name = reviewed_field["name"]
        kind = reviewed_field["source"]["kind"]
        if kind == "string":
            kind = "pooled-string"
        offset = offsets[name]
        pointer = image.pe.u64_at_va(int(image.registration["types"], 16)
                                     + owner_fields[name].type_index * 8)
        declared = runtime_type_name(image.pe, image.metadata, pointer)
        encodings = {k: expected_store(k, offset) for k in STORE_KINDS}
        store_at = next((i for i in range(position + 1, len(rows))
                         if rows[i]["raw"] in encodings.values()), None)
        if store_at is None:
            raise RouteRefused(f"store={name}:offset={offset}")
        store = rows[store_at]
        store_kind = next(k for k, v in encodings.items() if v == store["raw"])
        segment = rows[position + 1:store_at]
        field: dict[str, Any] = {
            "index": reviewed_field["index"], "name": name, "declaredType": declared,
            "setterMethod": setter, "ownerFieldOffset": offset,
        }
        if kind in INLINE_SOURCE:
            sources = [r for r in segment if r["raw"].hex().upper() == INLINE_SOURCE[kind]]
            if len(sources) != 1:
                raise RouteRefused(f"inline-source={name}:found={len(sources)}")
            field["source"] = {"kind": kind, "rva": sources[0]["rva"], "hex": INLINE_SOURCE[kind]}
        else:
            calls = [r for r in segment if r["raw"][:1] == b"\xE8" and len(r["raw"]) == 5]
            if not calls:
                raise RouteRefused(f"source-call={name}")
            call = calls[-1]
            target = call["rva"] + 5 + struct.unpack_from("<i", call["raw"], 1)[0]
            source = {"kind": kind, "rva": call["rva"], "hex": call["raw"].hex().upper(),
                      "targetRva": target}
            loads = [contexts[r["rva"]] for r in segment
                     if r["rva"] in contexts and r["rva"] < call["rva"]]
            if kind in CONTEXT_KINDS:
                if len(loads) != 1:
                    raise RouteRefused(f"source-context={name}:found={len(loads)}")
                context = _context_row(loads[0])
                argument = image.instantiations.resolve(context["methodSpec"][2]).arguments[0]
                context["argumentType"] = runtime_type_name(image.pe, image.metadata,
                                                            argument.type_pointer_va)
                expected = declared[:-2] if kind == "packed-gameplay-tag-array" else declared
                if context["argumentType"] != expected:
                    raise RouteRefused(f"context-type={name}:{context['argumentType']}!={expected}")
                source["context"] = context
            elif loads:
                raise RouteRefused(f"primitive-context={name}")
            field["source"] = source
        field["store"] = {"rva": store["rva"], "hex": store["raw"].hex().upper(), "kind": store_kind}
        fields.append(field)
        position = store_at
        previous_store = store["rva"]
    targets: dict[str, set[int]] = {}
    for f in fields:
        if "targetRva" in f["source"]:
            targets.setdefault(f["source"]["kind"], set()).add(f["source"]["targetRva"])
    if any(len(v) != 1 for v in targets.values()):
        raise RouteRefused(f"helper-target-variation={ {k: sorted(v) for k, v in targets.items()} }")

    int_wrapper_def = _type_definition(image, INT_WRAPPER)
    int_base_def = _type_definition(image, INT_BASE)
    new = {
        "schema": SCHEMA,
        "status": "exact-current-build",
        "nativeInputs": dict(inputs),
        "reviewedDependencies": [
            "buff_adding_cooldown_ownership_native.json", "buff_dispel_config_native.json",
            "buff_icon_config_native.json", "buff_stacking_compact_native.json",
            "buff_timeline_empty_native.json", "memorypack_pooled_string_reader_native.json",
        ],
        "rootMethod": root,
        "rootWrapper": wrapper_name,
        "ownerType": reviewed["ownerType"],
        "rootMemberCount": count,
        "codeWindows": windows,
        "bodyRange": [root[3], body_end],
        "headerInstruction": [header[0]["rva"], header[0]["raw"].hex().upper()],
        "blackboardIntChild": {
            "wrapperType": INT_WRAPPER, "wrapperTypeDefinition": int_wrapper_def,
            "baseType": INT_BASE, "baseTypeDefinition": int_base_def,
            "setterMethods": image.setter_methods(image.metadata.types[int_base_def],
                                                  parameter="typeName", label="buffRootRegenerate"),
        },
        "fields": fields,
        "evidenceBoundary": copy.deepcopy(reviewed["evidenceBoundary"]),
    }
    return new


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    reviewed = json.loads(CONTRACT.read_bytes())
    image, inputs = open_selected_build()
    try:
        new = regenerate(reviewed, image, inputs)
    except RouteRefused as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
    if "--write" in argv:
        CONTRACT.write_bytes(text.encode("utf-8"))
        print(f"wrote {CONTRACT}")
    else:
        print(text[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
