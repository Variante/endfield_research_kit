"""Prove a Win64 packed String/Int32 argument split at a selected generic call.

The vector's producer, enumeration semantics and runtime contents are separate
obligations. A shared native entry address never selects closed generic types.
"""
from __future__ import annotations

import re
from typing import Any

from .context import usage_method_spec
from .protocol import runtime_type_name


def prove_string_int_split(raw: bytes) -> dict[str, Any]:
    """MOVDQA; PSRLDQ 8; MOVD R8D; MOVQ RDX, with no intervening operation."""
    program = bytes.fromhex("66 0F 6F C1 66 0F 73 D8 08 66 41 0F 7E C0 66 48 0F 7E CA")
    if raw != program:
        raise ValueError("packed_pair.argument_program: expected complete XMM1 low64->RDX, bits64..95->R8D program")
    return {"vector": "xmm1", "keyRegister": "rdx", "keyBits": [0, 63],
            "valueRegister": "r8d", "valueBits": [64, 95], "valueUpperBits": "zeroed",
            "byteCount": len(raw)}


def passed_context(index: Any, slot: int, target: int) -> dict[str, Any]:
    """Resolve the exact R9 MethodSpec load beside a two-parameter instance call."""
    image, metadata, pe = index.image, index.metadata, index.pe
    start = int(image.registration["methodSpecs"], 16)
    records = pe.bytes_at_va(start, image.registration["methodSpecsCount"] * 12)
    context = usage_method_spec(pe.bytes_at_va(slot, 8), records, len(metadata.methods), image.instantiations.count,
                                source=str(image.gameassembly), usage_offset=slot, records_offset=start)
    method = metadata.methods[context["definition"]]
    if (method.parameter_count != 2 or method.flags & 0x10 or context["methodInstantiationIndex"] != -1 or
            not any(row.get("methodIndex") == context["definition"] for row in index.names_by_pointer.get(target, []))):
        raise ValueError("packed_pair.method_context: expected matching two-parameter instance definition and no method arguments")
    arguments = [runtime_type_name(pe, metadata, argument.type_pointer_va)
                 for argument in image.instantiations.resolve(context["classInstantiationIndex"]).arguments]
    return {"symbol": metadata.type_full_name(metadata.types[method.declaring_type]) + "." + metadata.string(method.name_index),
            "classArguments": arguments, "methodSpecIndex": context["index"], "usageSlotVa": hex(slot)}


def check_packed_pair_call(index: Any, body: Any, spec: Any) -> str | None:
    """Only a direct call fully inside its owning body admits this grammar."""
    if (not isinstance(spec, dict) or set(spec) != {"call", "classArguments"} or
            not isinstance(spec["call"], str) or spec["classArguments"] != ["string", "int"]):
        return "packed_pair.claim_shape: requires a named call and selected [string,int] class arguments"
    failures = []
    for row in body.rows:
        match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
        if not match:
            continue
        target = int(match[1], 16)
        if spec["call"] not in index.names_of(target):
            continue
        call = int(row["va"], 16)
        if not body.pointer + 26 <= call or call + 5 > body.pointer + body.size:
            failures.append("call window is outside its owner")
            continue
        raw = index.pe.bytes_at_va(call - 26, 31)
        if raw[:3] != bytes.fromhex("4C 8B 0D") or raw[26] != 0xE8:
            failures.append("missing adjacent R9 RIP MethodSpec load and direct call")
            continue
        actual_target = call + 5 + int.from_bytes(raw[27:31], "little", signed=True)
        if actual_target != target:
            failures.append("decoded direct target differs from raw bytes")
            continue
        slot = call - 19 + int.from_bytes(raw[3:7], "little", signed=True)
        try:
            prove_string_int_split(raw[7:26])
            context = passed_context(index, slot, target)
        except (ValueError, OSError, KeyError, IndexError, AttributeError) as exc:
            failures.append(str(exc)[:400])
            continue
        if context["symbol"] != spec["call"] or context["classArguments"] != spec["classArguments"]:
            failures.append(f"selected call context differs: {context['symbol']} {context['classArguments']}")
            continue
        return None
    return "packed_pair.call_argument_binding: " + ("; ".join(failures[:3]) if failures else "no owned named call matches")
