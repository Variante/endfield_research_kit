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
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack.wrapper_members import derive_from_image, unmanaged_value_sizes_from_image

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


def check_typed_context(image: Any, context: dict[str, Any], declared_type: str, *, label: str,
                        fail: Callable[..., None], load_prefixes: tuple[bytes, ...] | None = None) -> None:
    options = {} if load_prefixes is None else {'load_prefixes': load_prefixes}
    cell, usage = image.nested_usage_cell(context, label=label, **options)
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


def check_runtime_shape(image: Any, section: dict[str, Any], *, label: str,
                        fail: Callable[..., None]) -> None:
    """Authenticate a reviewed generated-setter parameter and direct-store plan."""
    runtime = section["runtimeType"]
    actual = {"typeName": image.type_name(runtime["typeDefinition"]),
              "fieldOffsets": runtime_type_field_offsets(image.metadata, image.pe, image.registration,
                                                         runtime["typeDefinition"])}
    expected = {key: runtime[key] for key in actual}
    if actual != expected:
        fail("runtime-field-offsets", expected, actual)
    for row in section["parameterTypes"]:
        method = image.metadata.methods[row["setterMethodIndex"]]
        if method.parameter_count != 1:
            fail("setter-arity", 1, method.parameter_count)
        parameter = image.metadata.parameters[method.parameter_start]
        pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + parameter.type_index * 8)
        actual = {"parameterTypeIndex": parameter.type_index,
                  "rawHex": image.pe.bytes_at_va(pointer, 16).hex().upper(),
                  "typeName": runtime_type_name(image.pe, image.metadata, pointer)}
        expected = {key: row[key] for key in actual}
        if actual != expected:
            fail("setter-parameter-type", expected, actual)
    image.check_instruction_windows(section["sourceAndDestinationInstructions"], label=label)
    for _rva, raw_hex, role in section["sourceAndDestinationInstructions"]:
        if role.endswith(" destination"):
            name = role.removesuffix(" destination")
            if bytes.fromhex(raw_hex)[-1] != runtime["fieldOffsets"].get(name):
                fail("field-destination", {name: runtime["fieldOffsets"].get(name)}, bytes.fromhex(raw_hex)[-1])


def _check_read_program(image: Any, window: dict[str, Any], instructions: Any,
                        expected: list[bytes], *, record: str, field: str,
                        label: str, fail: Callable[..., None]) -> None:
    if (not isinstance(instructions, list) or len(instructions) != len(expected)
            or any(not isinstance(row, list) or len(row) != 2 for row in instructions)):
        fail("unmanaged-source-instructions", len(expected), instructions, record=record, field=field)
    previous = window["startRva"]
    for row, raw in zip(instructions, expected, strict=True):
        at, hex_value = row
        if (type(at) is not int or not previous <= at <= window["endRva"] - len(raw)
                or hex_value != raw.hex().upper()):
            fail("unmanaged-source-instruction", raw.hex().upper(), row, record=record, field=field)
        previous = at + len(raw)
    image.check_instruction_windows(instructions, label=label)


def _check_registered_reader(image: Any, proof: dict[str, Any], entry: dict[str, Any],
                              offsets: list[int], *, record: str, field: str,
                              label: str, fail: Callable[..., None]) -> None:
    """Authenticate a distinct registered body without claiming address identity.

    The registered normal path independently reads a DWORD, passes four to
    its direct cursor helper and returns those bits. The helper updates the
    same stored reader slots as the parent's optimized source body.
    """
    registered = proof.get("registeredReader") or {}
    if not isinstance(registered, dict):
        fail("unmanaged-registered-reader", "reviewed registered reader object", registered,
             record=record, field=field)
    window = registered.get("window") or {}
    advance = registered.get("advanceWindow") or {}
    call = registered.get("advanceCall") or {}
    if (any(not isinstance(w, dict) or any(type(w.get(k)) is not int for k in ("startRva", "endRva"))
            or w["startRva"] >= w["endRva"] for w in (window, advance))
            or not isinstance(call, dict) or any(type(call.get(k)) is not int for k in ("rva", "targetRva"))):
        fail("unmanaged-registered-reader", "bounded reader/helper windows and direct call", registered,
             record=record, field=field)
    if (entry["pointer"] != image.pe.image_base + window.get("startRva", -1)
            or call.get("targetRva") != advance.get("startRva")
            or not window.get("startRva", -1) <= call.get("rva", -2) <= window.get("endRva", -3) - 5):
        fail("unmanaged-registered-reader", "registered body and its own bounded cursor helper", registered,
             record=record, field=field)
    image.check_windows([window, advance], label=label)
    buffer, remaining, consumed, segment = offsets
    _check_read_program(image, window, registered.get("instructions"),
        [b"\x48\x8b\x5f" + bytes([buffer]), b"\xba\x04\x00\x00\x00", b"\x48\x8b\xcf",
         b"\x8b\x1b", b"\x8b\xc3"], record=record, field=field, label=label, fail=fail)
    instructions = registered["instructions"]
    if (instructions[3][0] + 2 != call["rva"] or call["rva"] + 5 != instructions[4][0]):
        fail("unmanaged-registered-read-return", "DWORD -> cursor helper(4) -> returned DWORD", call,
             record=record, field=field)
    def field_fail(check: str, expected: Any, actual: Any) -> None:
        fail(check, expected, actual, record=record, field=field)
    check_call(image, call, label=label, fail=field_fail)
    _check_read_program(image, advance, registered.get("advanceInstructions"),
        [b"\x48\x63\xfa", b"\x48\x8b\xd9", b"\x8b\x71" + bytes([remaining]), b"\x2b\xf7",
         b"\x48\x01\x7b" + bytes([buffer]), b"\x01\x7b" + bytes([consumed]),
         b"\x01\x7b" + bytes([segment]), b"\x89\x73" + bytes([remaining])],
        record=record, field=field, label=label, fail=fail)


def check_unmanaged_source(image: Any, source: dict[str, Any], member: dict[str, Any],
                           sizes: dict[str, int], entries: Any, *, record: str, width: int,
                           label: str, fail: Callable[..., None]) -> None:
    """Join a closed blittable type to the reviewed normal DWORD reader.

    A value-type size alone is not its wire grammar. Admission also requires
    the parent's typed source context, a reviewed helper window reached by
    this call, and its pointer load, DWORD read, four-byte cursor accounting
    and return. Short-segment/provider behavior remains outside this proof.
    """
    proof = member.get("unmanagedSource") or {}
    if not isinstance(proof, dict):
        fail("unmanaged-source-proof", "reviewed object", proof,
             record=record, field=member["fieldName"])
    actual = sizes.get(member["declaredType"])
    if (width != 4 or actual != width or proof.get("width") != width
            or member.get("sourceContextInstructionRva") is None):
        fail("unmanaged-source-width", {"width": width, "typedContext": True},
             {"typeSize": actual, "proof": proof}, record=record, field=member["fieldName"])
    start = proof.get("windowStartRva")
    window = next((w for w in source["codeWindows"] if w["startRva"] == start), None)
    if window is None or start != member["sourceCall"]["targetRva"]:
        fail("unmanaged-source-window", "source call enters a reviewed helper window", start,
             record=record, field=member["fieldName"])
    context = next((c for c in source["nestedContexts"]
                    if c["instructionRva"] == member["sourceContextInstructionRva"]), None)
    if context is None:
        fail("unmanaged-source-context", "closed source MethodSpec", None,
             record=record, field=member["fieldName"])
    try:
        entry = entries.resolve(context["methodSpec"][0], [], [member["declaredType"]])
    except ValueError as exc:
        fail("unmanaged-source-registration", "unique closed registered reader", str(exc),
             record=record, field=member["fieldName"])
    if entry["methodSpecIndex"] != context["methodSpecIndex"]:
        fail("unmanaged-source-registration", context["methodSpecIndex"], entry["methodSpecIndex"],
             record=record, field=member["fieldName"])
    offsets = [proof.get("bufferPointerOffset"), proof.get("remainingBytesOffset"),
               *(proof.get("consumedOffsets") or [])]
    if (len(offsets) != 4 or any(type(n) is not int or not 0 <= n < 128 for n in offsets)
            or len(set(offsets)) != 4):
        fail("unmanaged-source-offsets", "four distinct positive-disp8 slots", offsets,
             record=record, field=member["fieldName"])
    buffer, remaining, consumed, segment = offsets
    if entry["pointer"] != image.pe.image_base + start:
        _check_registered_reader(image, proof, entry, offsets, record=record, field=member["fieldName"],
                                 label=label, fail=fail)
    expected = [b"\x48\x8b\x5f" + bytes([buffer]), b"\x8b\x1b",
                b"\x8b\x77" + bytes([remaining]), b"\x83\xee\x04",
                b"\x48\x83\x47" + bytes([buffer, width]),
                b"\x83\x47" + bytes([consumed, width]),
                b"\x83\x47" + bytes([segment, width]),
                b"\x89\x77" + bytes([remaining]), b"\x8b\xc3"]
    _check_read_program(image, window, proof.get("instructions"), expected,
                        record=record, field=member["fieldName"], label=label, fail=fail)


def check_inline_source(image: Any, member: dict[str, Any], sizes: dict[str, int],
                        normal: dict[str, Any], previous: int, *, record: str,
                        label: str, fail: Callable[..., None]) -> None:
    """Prove an explicit inline 16-byte copy, its cursor call and destination.

    This path has no nested formatter context: the parent loads from its
    source pointer into a stack temporary, advances sixteen, then copies the
    same temporary into the independently checked runtime field. The bounded
    normal window and exact intervening bytes authenticate that transfer.
    """
    proof = member.get("inlineSource") or {}
    field = member["fieldName"]
    if (member["kind"] != "raw16" or sizes.get(member["declaredType"]) != 16
            or proof.get("width") != 16 or member.get("sourceContextInstructionRva") is not None
            or member["assignment"]["kind"] != "direct-store"):
        fail("inline-source-type", "inline 16-byte value and direct field store", proof,
             record=record, field=field)
    offsets = [proof.get("bufferPointerOffset"), proof.get("remainingBytesOffset"),
               *(proof.get("consumedOffsets") or [])]
    if (len(offsets) != 4 or any(type(n) is not int or not 0 <= n < 128 for n in offsets)
            or len(set(offsets)) != 4):
        fail("inline-source-offsets", "four distinct positive-disp8 slots", offsets,
             record=record, field=field)
    buffer, remaining, consumed, segment = offsets
    _check_read_program(image, normal, proof.get("instructions"),
        [b"\x48\x8b\x47" + bytes([buffer]), b"\xba\x10\x00\x00\x00",
         b"\x48\x8b\xcf", b"\x0f\x10\x00", b"\x0f\x11\x44\x24\x20"],
        record=record, field=field, label=label, fail=fail)
    assignment = member["assignment"]
    _check_read_program(image, normal, proof.get("destinationInstructions"),
        [b"\x0f\x10\x44\x24\x20", b"\x48\x8b\xcf", bytes.fromhex(assignment["rawHex"])],
        record=record, field=field, label=label, fail=fail)
    instructions = proof["instructions"]; destination = proof["destinationInstructions"]
    call = proof.get("advanceCall") or {}; advance = proof.get("advanceWindow") or {}
    if (not isinstance(call, dict) or any(type(call.get(k)) is not int for k in ("rva", "targetRva"))
            or not isinstance(advance, dict)
            or any(type(advance.get(k)) is not int for k in ("startRva", "endRva"))
            or advance["startRva"] >= advance["endRva"]):
        fail("inline-source-helper", "bounded direct cursor helper", proof, record=record, field=field)
    # Both small instruction programs must be contiguous; a width or stack
    # location change cannot be hidden in a gap between selected witnesses.
    for rows in (instructions, destination):
        if any(a[0] + len(bytes.fromhex(a[1])) != b[0] for a, b in zip(rows, rows[1:])):
            fail("inline-source-program", "contiguous instruction program", rows, record=record, field=field)
    if (not previous <= instructions[0][0]
            or instructions[-1][0] + 5 != call.get("rva")
            or call.get("targetRva") != advance.get("startRva")
            or not call.get("rva", -1) + 5 <= destination[0][0]
            or destination[-1][0] != assignment["rva"]
            or not normal["startRva"] <= call.get("rva", -1) <= normal["endRva"] - 5):
        fail("inline-source-order", "source -> advance(16) -> same temporary -> field", proof,
             record=record, field=field)
    bridge = proof.get("sourceToDestinationHex", "")
    if call["rva"] + 5 + len(bytes.fromhex(bridge)) != assignment["rva"]:
        fail("inline-source-bridge", assignment["rva"], bridge, record=record, field=field)
    def field_fail(check: str, expected: Any, actual: Any) -> None:
        fail(check, expected, actual, record=record, field=field)
    check_call(image, call, label=label, fail=field_fail)
    image.check_instruction_windows([[call["rva"] + 5, bridge]], label=label)
    image.check_windows([advance], label=label)
    _check_read_program(image, advance, proof.get("advanceInstructions"),
        [b"\x48\x63\xfa", b"\x48\x8b\xd9", b"\x8b\x71" + bytes([remaining]), b"\x2b\xf7",
         b"\x48\x01\x7b" + bytes([buffer]), b"\x01\x7b" + bytes([consumed]),
         b"\x01\x7b" + bytes([segment]), b"\x89\x73" + bytes([remaining])],
        record=record, field=field, label=label, fail=fail)
    # The sole accepted destination opcode writes all sixteen XMM bits.
    expected_store = b"\x0f\x11\x40" + bytes([assignment["fieldOffset"]])
    if bytes.fromhex(assignment["rawHex"]) != expected_store or assignment.get("baseRegister") != 0:
        fail("inline-destination-width", expected_store.hex().upper(), assignment,
             record=record, field=field)


def check_provider_output_source(image: Any, source: dict[str, Any], member: dict[str, Any],
                                 record: dict[str, Any], normal: dict[str, Any], previous: int, *,
                                 record_key: str, label: str, fail: Callable[..., None]) -> None:
    """Prove a typed provider's sixteen-byte result reaches its runtime field.

    Sixteen is the runtime value extent, not a wire read. The independent
    child still owns its serialized grammar. A later wrapper getter cannot
    masquerade as the source call: the closed context, hidden output pointer,
    reader argument and complete stack-to-field transfer are separate.
    This does not equate an optimized call target with a registered entry or
    prove live formatter/provider selection.
    """
    proof = member.get("providerOutputSource") or {}
    field = member["fieldName"]; assignment = member["assignment"]
    report_failure = fail
    def fail(check: str, expected: Any, actual: Any, **_details: Any) -> None:
        report_failure(check, expected, actual, record=record_key, field=field)
    context = next((c for c in source["nestedContexts"]
                    if c["instructionRva"] == member.get("sourceContextInstructionRva")), None)
    if (proof.get("mode") != "provider-struct16" or proof.get("runtimeValueBytes") != 16
            or member["kind"] != "query-profile" or assignment["kind"] != "direct-store"
            or context is None or context.get("typeKind") != 17
            or context.get("typeDefinition") != proof.get("runtimeValueTypeDefinition")):
        fail("provider-output-type", "typed query provider output and direct store", proof, record=record["runtimeTypeName"], field=field)
    owner = image.metadata.types[context["typeDefinition"]]
    sizes = int(image.registration["typeDefinitionsSizes"], 16)
    extent = image.pe.u32_at_va(image.pe.u64_at_va(sizes + owner.index * 8)) - 16
    if (image.metadata.metadata_type_name(owner.parent_index) != "System.ValueType"
            or image.type_name(owner.index) != member["declaredType"] or extent != 16):
        fail("provider-output-runtime-size", 16, extent, field=field)
    definition = image.metadata.methods[context["methodSpec"][0]]
    actual = [definition.index, image.type_name(definition.declaring_type), image.metadata.string(definition.name_index)]
    if actual != proof.get("sourceDefinition") or actual[2] != "ReadValue":
        fail("provider-output-definition", proof.get("sourceDefinition"), actual, field=field)
    section = image.metadata.sections["genericContainers"]
    offset = section.offset + definition.generic_container_index * 16
    if definition.generic_container_index < 0 or not section.offset <= offset <= section.offset + section.size - 16:
        fail("provider-output-return-container", "bounded method generic container", definition.generic_container_index)
    container = struct.unpack_from("<iiii", image.metadata.buf, offset)
    return_pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + definition.return_type * 8)
    return_raw = image.pe.bytes_at_va(return_pointer, 16)
    if (definition.parameter_count != 0 or definition.flags & 0x10
            or container[:3] != (definition.index, 1, 1)
            or len(return_raw) != 16 or return_raw[10:12] != b"\x1e\x00"
            or int.from_bytes(return_raw[:8], "little") != container[3]):
        fail("provider-output-return-abi", "instance ReadValue<T>() returns its sole undecorated MVAR", {
            "parameters": definition.parameter_count, "static": bool(definition.flags & 0x10),
            "container": list(container), "returnTypeHex": return_raw.hex().upper()})
    _check_read_program(image, normal, proof.get("argumentInstructions"),
        [bytes.fromhex(context["instructionHex"]), b"\x48\x8d\x4c\x24\x20", b"\x48\x8b\x1b", b"\x48\x8b\xd7"],
        record=record["runtimeTypeName"], field=field, label=label, fail=fail)
    arguments = proof["argumentInstructions"]; bridge = proof.get("bridgeInstructions")
    getter = proof.get("getterCall") or {}; method = proof.get("getterMethod")
    if (not isinstance(method, list) or len(method) != 4 or method[1] != record["wrapperTypeName"]
            or method[2] != "get___instance" or getter.get("targetRva") != method[3]):
        fail("provider-output-getter", "actual wrapper instance getter", proof, field=field)
    image.validate_method_row(method, label=label)
    getter_definition = image.metadata.methods[method[0]]
    return_pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + getter_definition.return_type * 8)
    if runtime_type_name(image.pe, image.metadata, return_pointer) != record["runtimeTypeName"]:
        fail("provider-output-getter-type", record["runtimeTypeName"], runtime_type_name(image.pe, image.metadata, return_pointer), field=field)
    if (not isinstance(bridge, list) or len(bridge) != 10
            or len(bytes.fromhex(bridge[1][1])) != 6 or not bridge[1][1].startswith("0F84")
            or len(bytes.fromhex(bridge[6][1])) != 2 or not bridge[6][1].startswith("74")):
        fail("provider-output-bridge", "complete null-check/getter/stack-copy program", bridge, field=field)
    store = b"\x0f\x11\x40" + bytes([assignment["fieldOffset"]])
    _check_read_program(image, normal, bridge,
        [b"\x48\x85\xdb", bytes.fromhex(bridge[1][1]), b"\x33\xd2", b"\x48\x8b\xcb",
         image.pe.bytes_at_va(image.pe.image_base + getter["rva"], 5), b"\x48\x85\xc0", bytes.fromhex(bridge[6][1]),
         b"\x0f\x10\x44\x24\x20", b"\x48\x8d\x48" + bytes([assignment["fieldOffset"] + 8]), store],
        record=record["runtimeTypeName"], field=field, label=label, fail=fail)
    call = member["sourceCall"]
    if (arguments[0][0] != context["instructionRva"] or arguments[-1][0] + 3 != call["rva"]
            or not previous <= arguments[0][0] or call["rva"] + 5 != bridge[0][0]
            or bridge[4][0] != getter.get("rva") or bridge[-1][0] != assignment["rva"]
            or assignment["rawHex"] != store.hex().upper() or assignment["baseRegister"] != 0):
        fail("provider-output-order", "typed read into stack -> wrapper getter -> full destination copy", proof, field=field)
    for program in (arguments, bridge):
        if any(a[0] + len(bytes.fromhex(a[1])) != b[0] for a, b in zip(program, program[1:])):
            fail("provider-output-contiguity", "contiguous programs", program, field=field)
    check_call(image, getter, label=label, fail=fail)


def check_value_wrapper_destination(image: Any, record: dict[str, Any], wrapper: Any,
                                    normal: dict[str, Any], *, record_key: str,
                                    label: str, fail: Callable[..., None]) -> dict[str, int]:
    """Project boxed metadata member offsets into an actual inline wrapper.

    A wrapper reference passed by reference is not a boxed value receiver.
    The normal fallthrough program must derive RBX from the second argument,
    dereference it once and preserve it through every selected field store.
    Calls preserve nonvolatile RBX under the selected Win64 ABI. Alternate
    null, construction and error paths remain in the owning source contract.
    """
    proof = record.get("valueWrapperDestination") or {}
    def bad(check: str, expected: Any, actual: Any) -> None:
        fail("value-wrapper-" + check, expected, actual, record=record_key)
    if (proof.get("mode") != "inline-wrapper-value-rbx" or not wrapper.wrapped_is_value_type
            or proof.get("boxedHeaderBytes") != 16 or record["inheritedMemberCount"] != 0):
        bad("shape", "non-inherited inline value wrapper with selected object header", proof)
    metadata, pe = image.metadata, image.pe
    table = int(image.registration["types"], 16)
    def type_raw(index: int) -> bytes:
        return pe.bytes_at_va(pe.u64_at_va(table + index * 8), 16)
    definition = metadata.methods[record["readerMethod"][0]]
    parameters = list(metadata.parameters_for(definition))
    result = type_raw(definition.return_type)
    raw_parameters = [type_raw(p.type_index) for p in parameters]
    if (not definition.flags & 0x10 or len(parameters) != 2 or len(result) != 16 or result[10] != 1
            or any(len(raw) != 16 or raw[11] & 0x7f != 0x20 for raw in raw_parameters)
            or raw_parameters[0][10] != 0x11 or raw_parameters[1][10] != 0x12
            or runtime_type_name(pe, metadata, pe.u64_at_va(table + parameters[0].type_index * 8)) != "MemoryPack.MemoryPackReader"
            or int.from_bytes(raw_parameters[1][:8], "little") != record["wrapperTypeDefinition"]):
        bad("reader-abi", "static void Deserialize(ref MemoryPackReader, ref exact wrapper)",
            {"static": bool(definition.flags & 0x10), "return": result.hex(),
             "parameters": [raw.hex() for raw in raw_parameters]})
    runtime = metadata.types[record["runtimeTypeDefinition"]]
    if metadata.metadata_type_name(runtime.parent_index) != "System.ValueType":
        bad("runtime", "System.ValueType", metadata.metadata_type_name(runtime.parent_index))
    fields = [f for f in metadata.fields_for(metadata.types[record["wrapperTypeDefinition"]])
              if metadata.string(f.name_index) == proof.get("instanceFieldName")]
    if len(fields) != 1:
        bad("instance-field", "one selected wrapper instance field", len(fields))
    raw = type_raw(fields[0].type_index)
    if (len(raw) != 16 or int.from_bytes(raw[8:10], "little") & 0x10 or raw[10] != 0x11
            or int.from_bytes(raw[:8], "little") != runtime.index):
        bad("instance-type", record["runtimeTypeName"], raw.hex())
    wrapper_offset = runtime_type_field_offsets(metadata, pe, image.registration,
        record["wrapperTypeDefinition"])[proof["instanceFieldName"]]
    runtime_offsets = runtime_type_field_offsets(metadata, pe, image.registration, runtime.index)
    projected = {m["fieldName"]: wrapper_offset + runtime_offsets[m["fieldName"]] - 16
                 for m in record["members"]}
    if wrapper_offset < 16 or any(runtime_offsets[m["fieldName"]] < 16
            or m["assignment"]["kind"] != "direct-store"
            or m["assignment"]["baseRegister"] != 3
            or m["assignment"]["fieldOwnerTypeDefinition"] != runtime.index
            or m["assignment"]["fieldOffset"] != projected[m["fieldName"]]
            for m in record["members"]):
        bad("projected-offset", projected, [m["assignment"] for m in record["members"]])
    program = proof.get("receiverProgram")
    alias = proof.get("receiverAliasInstruction"); dereference = proof.get("receiverDereferenceInstruction")
    if (not isinstance(program, list) or not program or any(not isinstance(row, list) or len(row) != 2
            or type(row[0]) is not int or not isinstance(row[1], str) or not row[1] for row in program)
            or alias != program[0] or alias[1] != "488BDA" or dereference not in program
            or dereference[1] != "488B1B"
            or not normal["startRva"] <= alias[0] < dereference[0]
            or any(a[0] + len(bytes.fromhex(a[1])) != b[0] for a, b in zip(program, program[1:]))
            or program[-1][0] + len(bytes.fromhex(program[-1][1])) != record["members"][-1]["assignment"]["rva"]
            or record["members"][-1]["assignment"]["rva"] >= normal["endRva"]
            or any(not dereference[0] < m["sourceCall"]["rva"] < m["assignment"]["rva"] for m in record["members"])):
        bad("receiver-program", "complete normal program: second ref argument -> wrapper -> all stores", proof)
    image.check_instruction_windows(program, label=label)
    for at, hex_value in program:
        raw = bytes.fromhex(hex_value)
        rows = image.mapper.decode_x64_subset(raw, pe.image_base + at, stop_offset=len(raw))
        if len(rows) != 1 or str(rows[0]["text"]).startswith("db"):
            bad("receiver-instruction", "one understood instruction", [at, hex_value, rows])
        write = rows[0].get("write") or {}
        if (write.get("register") in {"rbx", "ebx", "bx", "bl", "bh"}
                and [at, hex_value] not in (alias, dereference)):
            bad("receiver-clobber", "preserved wrapper receiver", [at, hex_value, write])
    return projected


def validate_named_records(image: Any, source: dict[str, Any], records: dict[str, Any], *,
                           label: str, fail: Callable[..., None]) -> dict[str, Any]:
    """Validate one authenticated source family and return only proved names."""
    for method in source["methods"]:
        image.validate_method_row(method, label=label)
    image.check_windows(source["codeWindows"], label=label)
    wrappers = derive_from_image(image)
    contexts = {c["instructionRva"]: c for c in source["nestedContexts"]}
    unmanaged_sizes = None
    generic_entries = None
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
        if record.get("setterOutputSource") is not None:
            from scripts.game_data.memorypack import setter_output_sources
            setter_output_sources.validate_setter_outputs(image, source, record,
                fail=lambda check, expected, actual: fail(check, expected, actual, record=key))
        if record.get("sourceArgumentRoles") is not None:
            from scripts.game_data.memorypack import struct_output_sources
            struct_output_sources.check_parent_argument_roles(image, record, normal, label=label,
                fail=lambda check, expected, actual: fail(check, expected, actual, record=key))
        projected = (check_value_wrapper_destination(image, record, wrapper, normal,
            record_key=key, label=label, fail=fail) if record.get("valueWrapperDestination") is not None else None)
        previous = normal["startRva"]
        runtime = image.metadata.types[record["runtimeTypeDefinition"]]
        allowed_owners = {runtime.index}
        if wrapper.inherited_members:
            parent_name = image.metadata.metadata_type_name(runtime.parent_index)
            allowed_owners.add(next(t.index for t in image.metadata.types if image.metadata.type_full_name(t) == parent_name))
        for member, derived in zip(members, wrapper.members, strict=True):
            operation_start = previous
            if member["kind"] == "raw8" and (member.get("unmanagedOutputSource") or {}).get("mode") != "unmanaged-return64-float-pair":
                fail("raw8-output-proof-required", "explicit full-width source and destination programs", member, record=key, field=member["fieldName"])
            width = {"byte": 1, "byte-enum": 1, "scalar32": 4, "raw4": 4, "scalar64": 8}.get(member["kind"])
            if width is not None and derived.width != width:
                if derived.width is None and member.get("unmanagedSource") is not None:
                    if unmanaged_sizes is None:
                        unmanaged_sizes = unmanaged_value_sizes_from_image(image)
                        generic_entries = GenericEntries(image)
                    check_unmanaged_source(image, source, member, unmanaged_sizes, generic_entries,
                                           record=key, width=width, label=label, fail=fail)
                else:
                    fail("source-field-width", width, derived.width, record=key, field=member["fieldName"])
            inline = member.get("inlineSource") is not None
            if inline:
                if unmanaged_sizes is None:
                    unmanaged_sizes = unmanaged_value_sizes_from_image(image)
                if member["inlineSource"].get("mode") in {"inline-cursor-struct16", "inline-cursor-struct12", "inline-cursor-scalar32"}:
                    from scripts.game_data.memorypack import struct_output_sources
                    check_fail = lambda check, expected, actual: fail(check, expected, actual, record=key, field=member["fieldName"])
                    if member["inlineSource"].get("mode") == "inline-cursor-scalar32":
                        struct_output_sources.check_inline_scalar32(image, member, record, normal, previous,
                            label=label, fail=check_fail)
                    else:
                        checker = (struct_output_sources.check_inline12
                                   if member["inlineSource"].get("mode") == "inline-cursor-struct12"
                                   else struct_output_sources.check_inline16)
                        checker(image, member, record, unmanaged_sizes, normal, previous,
                            label=label, fail=check_fail)
                else:
                    check_inline_source(image, member, unmanaged_sizes, normal, previous,
                                        record=key, label=label, fail=fail)
            if member.get("unmanagedOutputSource") is not None:
                if unmanaged_sizes is None:
                    unmanaged_sizes = unmanaged_value_sizes_from_image(image)
                from scripts.game_data.memorypack import struct_output_sources
                checker = (struct_output_sources.check_unmanaged8
                           if member["unmanagedOutputSource"].get("mode") == "unmanaged-return64-float-pair"
                           else struct_output_sources.check_unmanaged12)
                checker(image, source, member, record, unmanaged_sizes, normal, previous,
                    label=label, fail=lambda check, expected, actual: fail(check, expected, actual, record=key, field=member["fieldName"]))
            nested = derived.kind in ("object", "list") and not inline
            if nested and member.get("sourceContextInstructionRva") is None:
                fail("nested-context-required", nested, member.get("sourceContextInstructionRva"), record=key, field=member["fieldName"])
            assignment = member["assignment"]
            if member.get("providerOutputSource") is not None:
                if member["providerOutputSource"].get("mode") == "provider-output32":
                    from scripts.game_data.memorypack import struct_output_sources
                    struct_output_sources.check_provider32(image, source, member, record, normal, previous,
                        label=label, fail=lambda check, expected, actual: fail(check, expected, actual, record=key, field=member["fieldName"]))
                else:
                    check_provider_output_source(image, source, member, record, normal, previous, record_key=key, label=label, fail=fail)
            if not inline:
                call = member["sourceCall"]
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
                wanted_store = ((projected if projected is not None else offsets)[member["fieldName"]], assignment["baseRegister"])
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
