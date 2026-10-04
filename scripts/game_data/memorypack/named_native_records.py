"""Mechanical proof of named MemoryPack source reads and destinations.

Callers select and authenticate native inputs before supplying their image.
Reviewed full reader windows, wrapper members and closed MethodSpec types
join each ordered read to its actual runtime store or generated setter.
This direct tier proves stored names; collection/provider selection and live
execution remain the caller's conditional or unresolved evidence boundary.
"""
from __future__ import annotations
import struct
from typing import Any, Callable
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.wrapper_members import derive_from_image

def check_call(image: Any, call: dict[str, Any], *, label: str, fail: Callable[..., None]) -> None:
    raw = image.pe.bytes_at_va(image.pe.image_base + call["rva"], 5)
    actual = call["rva"] + 5 + struct.unpack_from("<i", raw, 1)[0]
    if raw[:1] != b"\xe8" or actual != call["targetRva"]:
        fail("source-call", call, {"rawHex": raw.hex().upper(), "targetRva": actual})


def decode_store(raw: bytes, *, allowed_bases: tuple[int, ...] = (0, 1)) -> tuple[int, int]:
    """Decode reviewed direct stores under the caller's explicit base scope."""
    label = "namedNativeRecords"
    cursor = 0
    if raw[:1] in (b"\xf2", b"\xf3"):
        cursor += 1
    rex = 0
    if cursor < len(raw) and 0x40 <= raw[cursor] <= 0x4F:
        rex = raw[cursor]; cursor += 1
    if raw[cursor:cursor + 2] == b"\x0f\x11":
        cursor += 2
    elif raw[cursor:cursor + 1] in (b"\x88", b"\x89"):
        cursor += 1
    else:
        raise ValueError(f"{label}.native:store-opcode")
    if cursor >= len(raw):
        raise ValueError(f"{label}.native:short-store")
    modrm = raw[cursor]; cursor += 1
    mode, base = modrm >> 6, (modrm & 7) + 8 * (rex & 1)
    width = 1 if mode == 1 else 4
    if mode not in (1, 2) or base not in allowed_bases or cursor + width != len(raw):
        raise ValueError(f"{label}.native:store-destination")
    return int.from_bytes(raw[cursor:], "little", signed=True), base


def check_typed_context(image: Any, context: dict[str, Any], declared_type: str, *, label: str, fail: Callable[..., None]) -> None:
    cell, usage = image.nested_usage_cell(context, label=label)
    index = method_spec_usage_index(usage, image.registration["methodSpecsCount"],
                                    source=str(image.gameassembly), offset=cell)
    spec = struct.unpack("<iii", image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + index * 12, 12))
    instance = image.instantiations.resolve(spec[2])
    actual = {"index": index, "spec": list(spec),
              "arguments": [a.raw_type_record_hex for a in instance.arguments]}
    wanted = {"index": context["methodSpecIndex"], "spec": context["methodSpec"],
              "arguments": [context["argumentRawHex"]]}
    if actual != wanted:
        fail("typed-context", wanted, actual)
    actual_type = runtime_type_name(image.pe, image.metadata, instance.arguments[0].type_pointer_va)
    if actual_type != declared_type:
        fail("closed-field-type", declared_type, actual_type)


def validate_named_records(image: Any, source: dict[str, Any], records: dict[str, Any], *,
                           label: str, fail: Callable[..., None]) -> dict[str, Any]:
    """Validate one authenticated source family and return only proved names."""
    for method in source["methods"]:
        image.validate_method_row(method, label=label)
    image.check_windows(source["codeWindows"], label=label)
    wrappers = derive_from_image(image)
    contexts = {c["instructionRva"]: c for c in source["nestedContexts"]}
    proved = {}
    for key, record in records.items():
        members = record["members"]; wrapper = wrappers.get(record["wrapperTypeDefinition"])
        if image.type_name(record["runtimeTypeDefinition"]) != record["runtimeTypeName"]:
            fail("runtime-type", record["runtimeTypeName"], image.type_name(record["runtimeTypeDefinition"]), record=key)
        wanted = [(m["fieldName"], m["setterMethodIndex"], m["declaredType"]) for m in members]
        actual = None if wrapper is None else [(m.name, m.method_index, m.declared_type) for m in wrapper.members]
        if (actual != wanted or wrapper.name != record["wrapperTypeName"]
                or wrapper.wrapped_type != record["runtimeTypeName"]
                or len(wrapper.inherited_members) != record["inheritedMemberCount"]):
            fail("generated-members", wanted, actual, record=key)
        kinds = source["anonymousReadOrder"][record["sourceReadOrder"]]
        indices = record.get("sourceReadMemberIndices")
        if indices is not None:
            if (not isinstance(indices, list) or len(indices) != len(members)
                    or any(type(i) is not int or not 0 <= i < len(kinds) for i in indices)
                    or indices != sorted(set(indices))):
                fail("source-member-indices", len(members), indices, record=key)
            kinds = [kinds[i] for i in indices]
        if kinds != [m["kind"] for m in members]:
            fail("source-read-order", kinds, [m["kind"] for m in members], record=key)
        reader = record["readerMethod"]
        if reader not in source["methods"] or reader[1] != wrapper.name or reader[2] != "Deserialize":
            fail("source-reader", record["wrapperTypeName"], reader, record=key)
        normal = next(w for w in source["codeWindows"] if w["startRva"] == reader[3])
        previous = normal["startRva"]
        runtime = image.metadata.types[record["runtimeTypeDefinition"]]
        allowed_owners = {runtime.index}
        if wrapper.inherited_members:
            parent_name = image.metadata.metadata_type_name(runtime.parent_index)
            allowed_owners.add(next(t.index for t in image.metadata.types if image.metadata.type_full_name(t) == parent_name))
        for member, derived in zip(members, wrapper.members, strict=True):
            operation_start = previous
            width = {"byte": 1, "scalar32": 4, "scalar64": 8}.get(member["kind"])
            if width is not None and derived.width != width:
                fail("source-field-width", width, derived.width, record=key, field=member["fieldName"])
            nested = derived.kind in ("object", "list")
            if nested and member.get("sourceContextInstructionRva") is None:
                fail("nested-context-required", nested, member.get("sourceContextInstructionRva"), record=key, field=member["fieldName"])
            call = member["sourceCall"]; assignment = member["assignment"]
            bridge = bytes.fromhex(member["sourceToDestinationHex"])
            if not previous <= call["rva"] < call["rva"] + 5 + len(bridge) == assignment["rva"] < normal["endRva"]:
                fail("read-destination-order", [previous, normal["endRva"]], member, record=key, field=member["fieldName"])
            check_call(image, call, label=label, fail=fail)
            image.check_instruction_windows([[call["rva"] + 5, member["sourceToDestinationHex"]]], label=label)
            if assignment["kind"] == "direct-store":
                raw = bytes.fromhex(assignment["rawHex"])
                owner = assignment["fieldOwnerTypeDefinition"]
                if owner not in allowed_owners:
                    fail("destination-owner", sorted(allowed_owners), owner, record=key, field=member["fieldName"])
                offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner)
                actual_store = decode_store(raw, allowed_bases=(0, 1, 3))
                wanted_store = (offsets[member["fieldName"]], assignment["baseRegister"])
                if actual_store != wanted_store or assignment["fieldOffset"] != wanted_store[0]:
                    fail("destination-offset", wanted_store, actual_store, record=key, field=member["fieldName"])
                image.check_instruction_windows([[assignment["rva"], assignment["rawHex"]]], label=label)
                previous = assignment["rva"] + len(raw)
                tails = assignment.get("tailStores", [])
                if member["kind"] == "raw12" and [t.get("offsetDelta") for t in tails] != [8]:
                    fail("raw12-tail", [8], tails, record=key, field=member["fieldName"])
                for tail in tails:
                    actual_tail = decode_store(bytes.fromhex(tail["rawHex"]), allowed_bases=(0, 1, 3))
                    expected_tail = (wanted_store[0] + tail["offsetDelta"], wanted_store[1])
                    if tail["rva"] != previous or actual_tail != expected_tail:
                        fail("destination-tail", expected_tail, actual_tail, record=key, field=member["fieldName"])
                    image.check_instruction_windows([[tail["rva"], tail["rawHex"]]], label=label)
                    previous = tail["rva"] + len(bytes.fromhex(tail["rawHex"]))
            elif assignment["kind"] == "setter":
                method = image.metadata.methods[member["setterMethodIndex"]]
                if assignment["methodIndex"] != member["setterMethodIndex"] or image.method_pointer_va(method) != image.pe.image_base + assignment["targetRva"]:
                    fail("setter-identity", member["setterMethodIndex"], assignment, record=key, field=member["fieldName"])
                check_call(image, assignment, label=label, fail=fail); previous = assignment["rva"] + 5
            else:
                fail("assignment-kind", "direct-store or setter", assignment["kind"], record=key)
            context_rva = member.get("sourceContextInstructionRva")
            if context_rva is not None:
                if not operation_start <= context_rva < call["rva"]:
                    fail("context-order", [operation_start, call["rva"]], context_rva, record=key)
                if context_rva not in contexts:
                    fail("missing-typed-context", context_rva, sorted(contexts), record=key, field=member["fieldName"])
                check_typed_context(image, contexts[context_rva], member["declaredType"], label=label, fail=fail)
        proved[key] = [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in members]
    return proved
