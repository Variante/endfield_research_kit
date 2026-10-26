"""Authenticate the closed stored Param<SplinePtr> child without resolving a spline.

The declaration owns addresses and byte windows. The algorithm independently
checks typed contexts, owned receivers and the four-byte buffered source/cursor
program; live formatter replacement and movement remain outside this proof.
"""
from __future__ import annotations

import argparse
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.memorypack import utf8_source_helper
from scripts.game_data.memorypack.wrapper_members import derive_from_image

SCHEMA = "endfield.levelscript-spline-ptr-native.v2"
LABEL = "levelscriptSplinePtrNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_spline_ptr_native.json"


def _need(check: str, expected: Any, actual: Any) -> None:
    if expected != actual:
        raise ValueError(f"{LABEL}.{check}: expected={str(expected)[:400]} actual={str(actual)[:400]}")


def _ordinary_abi(raw: bytes, kind: int, check: str) -> None:
    _need(check + ".recordSize", 16, len(raw))
    _need(check + ".kind", kind, raw[10])
    # The selected Il2CppType profile separates the value-type marker (0x80)
    # from modifiers/byref/pinned in the low seven bits. These are primitive
    # and independently authenticated value types, never reference aliases.
    _need(check + ".ordinaryFlags", 0, raw[11] & 0x7F)


def _contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    _need("contract.schema", SCHEMA, value.get("schema"))
    _need("contract.status", "exact-current-build", value.get("status"))
    _need("contract.dependencies", [{"role": "utf8Source", "path": utf8_source_helper.CONTRACT_PATH.name}],
          value.get("dependencies"))
    parameter, pointer, source = value["parameter"], value["pointer"], value["constantSource"]
    _need("contract.parameterType", "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.SplinePtr>", parameter["wrapper"]["wrappedType"])
    _need("contract.pointerType", "Beyond.Gameplay.Core.SplinePtr", pointer["wrapper"]["wrappedType"])
    _need("contract.rawSize", 4, pointer["rawSize"])
    _need("contract.parameterFields", [["constValue", "Beyond.Gameplay.Core.SplinePtr"], ["idRef", "int"], ["paramSource", "int"], ["path", "string"]],
          [[row["name"], row["declaredType"]] for row in parameter["orderedReads"]])
    _need("contract.typedConstantMethod", ["MemoryPack.MemoryPackReader", "ReadUnmanaged", [], ["Beyond.Gameplay.Core.SplinePtr"]],
          [source["typedContext"][key] for key in ("typeName", "methodName", "classArguments", "methodArguments")])
    _need("contract.memberCount", 4, parameter["wrapper"]["serializedMemberCount"])
    _need("contract.pointerFields", [["id", "int"]], [[row["name"], row["declaredType"]] for row in pointer["wrapper"]["members"]])
    return value


def _call(image: Any, row: list[Any]) -> None:
    rva, expected, target = row
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    _need("native.callBytes", expected.upper(), raw.hex().upper())
    _need("native.callOpcode", 0xE8, raw[0])
    _need("native.callTarget", target, rva + 5 + struct.unpack_from("<i", raw, 1)[0])


def _opcode_program(image: Any, rows: list[list[Any]], expected: list[bytes | None], label: str) -> None:
    _need(label + ".count", len(expected), len(rows))
    image.check_instruction_windows(rows, label=LABEL + "." + label)
    for index, ((rva, encoded), opcode) in enumerate(zip(rows, expected)):
        raw = bytes.fromhex(encoded)
        if opcode is not None:
            _need(label + f".opcode[{index}]", opcode, raw)
        if index:
            _need(label + f".contiguous[{index}]", rows[index - 1][0] + len(bytes.fromhex(rows[index - 1][1])), rva)


def _source_program(image: Any, contract: dict[str, Any]) -> dict[str, int]:
    source = contract["constantSource"]
    selected = NativeReferenceContext(image)
    _need("native.readerValueType", True, selected.is_value_type("MemoryPack.MemoryPackReader"))
    definitions = [row.index for row in image.metadata.types if image.type_name(row.index) == "MemoryPack.MemoryPackReader"]
    _need("native.readerDefinitionCount", 1, len(definitions))
    boxed = runtime_type_field_offsets(image.metadata, image.pe, image.registration, definitions[0])
    offsets = {name: boxed[name] - 16 for name in ("currentPtr", "bufferLength", "advancedCount", "consumed")}
    for name, offset in offsets.items():
        if not 0 <= offset < 128:
            raise ValueError(f"{LABEL}.native.readerField: {name}={offset}")
    cur, remaining, advanced, consumed = (offsets[name] for name in ("currentPtr", "bufferLength", "advancedCount", "consumed"))
    rows = source["sourceInstructions"]
    expected = [b"\x48\x89\x5c\x24\x08", b"\x57", b"\x48\x83\xec\x20", b"\x83\x79" + bytes((remaining, 4)), b"\x48\x8b\xf9", None,
                b"\x45\x33\xc0", b"\xba\x04\x00\x00\x00", None, b"\x48\x8b\x5f" + bytes((cur,)), b"\xba\x04\x00\x00\x00", b"\x48\x8b\xcf", b"\x8b\x1b", None,
                b"\x8b\xc3", b"\x48\x8b\x5c\x24\x30", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    _opcode_program(image, rows, expected, "source")
    raw = bytes.fromhex(rows[5][1])
    _need("native.sourceGuardOpcode", 0x7D, raw[0])
    _need("native.sourceGuardSize", 2, len(raw))
    _need("native.sourceGuardTarget", rows[9][0], rows[5][0] + 2 + int.from_bytes(raw[1:], "little", signed=True))
    advance_call = [rows[13][0], rows[13][1], source["advancePointerRva"]]
    _call(image, advance_call)
    window = source["advanceWindow"]
    raw = image.pe.bytes_at_va(image.pe.image_base + window["startRva"], window["endRva"] - window["startRva"])
    # The normal program spans chained unwind entries. Decode exact opcodes
    # here rather than treating the mapper's unsupported ADD/SUB as aliases.
    pieces = [b"\x85\xd2", None, b"\x48\x89\x5c\x24\x10", b"\x57", b"\x48\x83\xec\x20", b"\x48\x63\xfa", b"\x48\x8b\xd9", b"\x48\x89\x74\x24\x30",
              b"\x8b\x71" + bytes((remaining,)), b"\x2b\xf7", None, b"\x48\x01\x7b" + bytes((cur,)), b"\x01\x7b" + bytes((advanced,)), b"\x01\x7b" + bytes((consumed,)), b"\x89\x73" + bytes((remaining,)),
              b"\x48\x8b\x74\x24\x30", b"\x48\x8b\x5c\x24\x38", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    at = 0
    for index, piece in enumerate(pieces):
        if piece is None:
            size, prefix = (2, b"\x74") if index == 1 else (6, b"\x0f\x88")
            _need("native.advanceGuardOpcode", prefix, raw[at:at + len(prefix)])
            if index == 1:
                _need("native.advanceZeroTarget", len(raw) - 1, at + 2 + int.from_bytes(raw[at + 1:at + 2], "little", signed=True))
            at += size
        else:
            _need("native.advanceOpcode", piece, raw[at:at + len(piece)])
            at += len(piece)
    _need("native.advanceClosedNormalExtent", len(raw), at)
    return offsets


def _int32_program(image: Any, contract: dict[str, Any], offsets: dict[str, int]) -> None:
    source = contract["int32Source"]
    cur, remaining, advanced, consumed = (offsets[name] for name in ("currentPtr", "bufferLength", "advancedCount", "consumed"))
    image.check_windows([source["window"]], label=LABEL)
    expected = [b"\x48\x89\x5c\x24\x08", b"\x48\x89\x74\x24\x10", b"\x57", b"\x48\x83\xec\x20", b"\x83\x79" + bytes((remaining, 4)), b"\x48\x8b\xd9", None,
                b"\x48\x8b\x43" + bytes((cur,)), b"\x8b\x30", b"\x8b\x7b" + bytes((remaining,)), b"\x83\xef\x04", None,
                b"\x48\x83\x43" + bytes((cur, 4)), b"\x83\x43" + bytes((advanced, 4)), b"\x83\x43" + bytes((consumed, 4)), b"\x89\x7b" + bytes((remaining,)),
                b"\x48\x8b\x5c\x24\x30", b"\x8b\xc6", b"\x48\x8b\x74\x24\x38", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    _opcode_program(image, source["instructions"], expected, "int32Source")
    for index, prefix in ((6, b"\x0f\x8c"), (11, b"\x0f\x88")):
        raw = bytes.fromhex(source["instructions"][index][1])
        _need("native.int32GuardOpcode", prefix, raw[:2])
        _need("native.int32GuardSize", 6, len(raw))


def _read_joins(image: Any, parameter: dict[str, Any], body: Any, source: dict[str, Any], int32: dict[str, Any], utf8: dict[str, Any]) -> None:
    """Re-derive actual ordered calls and complete argument/return intervals."""
    base = image.pe.image_base
    rows = body.rows
    current = {int(row["va"], 16) - base: index for index, row in enumerate(rows)}
    def raw(row: dict[str, Any]) -> bytes:
        return bytes.fromhex(row["bytes"])
    def instruction_rows(values: list[dict[str, Any]]) -> list[list[Any]]:
        return [[int(row["va"], 16) - base, raw(row).hex().upper()] for row in values]
    def write_register(row: dict[str, Any]) -> str | None:
        return (row.get("write") or {}).get("register")
    reader_aliases = {"rsi", "esi", "si", "sil"}
    output_aliases = {"rbx", "ebx", "bx", "bl", "bh"}
    rcx_aliases = {"rcx", "ecx", "cx", "cl", "ch"}
    rax_aliases = {"rax", "eax", "ax", "al", "ah"}
    rdx_aliases = {"rdx", "edx", "dx", "dl", "dh"}
    saves = {kind: [i for i, row in enumerate(rows) if raw(row) == encoded] for kind, encoded in (("reader", b"\x48\x8b\xf1"), ("output", b"\x48\x8b\xda"))}
    _need("native.savedReaderCount", 1, len(saves["reader"]))
    _need("native.savedOutputCount", 1, len(saves["output"]))
    first_read = parameter["orderedReads"][0]["readCall"][0]
    count_rows = [row for row in rows if raw(row) == b"\x80\x7c\x24\x30\x04" and int(row["va"], 16) - base < first_read]
    _need("native.memberCountCompare", 1, len(count_rows))
    previous = int(count_rows[0]["va"], 16) - base
    positive_start = current[previous]
    actual_calls = []
    expected_calls = []
    for index, read in enumerate(parameter["orderedReads"]):
        field = read["name"]
        method = parameter["methods"]["set___" + field + "__"]
        _need("native.setterMethodIdentity", method["methodIndex"], read["setterMethodIndex"])
        _need("native.setterActualDestination", method["pointerRva"], read["setterCall"][2])
        _need("native.readSetterOrder", True, previous < read["readCall"][0] < read["setterCall"][0])
        if read["readCall"][0] not in current or read["setterCall"][0] not in current:
            raise ValueError(f"{LABEL}.native.readOutsideDeserialize: {field}")
        read_at, setter_at = current[read["readCall"][0]], current[read["setterCall"][0]]
        before = rows[current[previous] + 1:read_at]
        between = rows[read_at + 1:setter_at]
        receiver = "rbx" if field == "path" else "rdi"
        receiver_bytes = b"\x48\x8b\x1b" if field == "path" else b"\x48\x8b\x3b"
        setup = [row for row in before if raw(row) in {receiver_bytes, b"\x48\x8b\xce"}]
        _need("native.actualReaderSetup", instruction_rows(setup), read["readerSetup"])
        _need("native.readerSetupCount", 2, len(setup))
        _need("native.readerArgumentAlias", b"\x48\x8b\xce", raw(next(row for row in reversed(before) if write_register(row) in rcx_aliases)))
        receiver_names = output_aliases if field == "path" else {"rdi", "edi", "di", "dil"}
        _need("native.wrapperArgumentOrigin", receiver_bytes, raw(next(row for row in reversed(before) if write_register(row) in receiver_names)))
        _need("native.actualReturnInterval", instruction_rows(between), read["returnToSetter"])
        forward = b"\x48\x8b\xd0" if field == "path" else b"\x8b\xd0"
        forwards = [i for i, row in enumerate(between) if raw(row) == forward]
        _need("native.returnForwardCount", 1, len(forwards))
        _need("native.returnValueUnchanged", [], [row["text"] for row in between[:forwards[0]] if write_register(row) in rax_aliases or raw(row)[:1] == b"\xe8"])
        _need("native.forwardedValueUnchanged", [], [row["text"] for row in between[forwards[0] + 1:] if write_register(row) in rdx_aliases])
        receiver_forward = b"\x48\x8b\xcb" if field == "path" else b"\x48\x8b\xcf"
        _need("native.setterReceiverAlias", receiver_forward, raw(next(row for row in reversed(between) if write_register(row) in rcx_aliases)))
        if field == "constValue":
            _need("native.actualConstantSource", source["sourceWindow"]["startRva"], read["readCall"][2])
        elif field in ("idRef", "paramSource"):
            _need("native.actualInt32Source", int32["window"]["startRva"], read["readCall"][2])
        elif read["readCall"][2] not in utf8["sourceHelpers"]:
            raise ValueError(f"{LABEL}.native.actualUtf8Source: {read['readCall'][2]}")
        _need("native.savedReaderSurvives", [], [row["text"] for row in rows[saves["reader"][0] + 1:read_at] if write_register(row) in reader_aliases])
        allowed_output = read["readerSetup"][0][0] if field == "path" and raw(setup[0]) == receiver_bytes else None
        _need("native.savedOutputSurvives", [], [row["text"] for row in rows[saves["output"][0] + 1:read_at] if write_register(row) in output_aliases and int(row["va"], 16) - base != allowed_output])
        expected_calls.extend((read["readCall"][0], read["setterCall"][0]))
        previous = read["setterCall"][0]
    for offset, row in enumerate(rows[positive_start + 1:current[previous] + 1], positive_start + 1):
        if raw(row)[:1] == b"\xe8":
            actual_calls.append(int(row["va"], 16) - base)
        elif row["text"].startswith(("db ", "call ", "jmp ")):
            raise ValueError(f"{LABEL}.native.positiveUnknownOrTransfer: {row['va']} {row['text']}")
        elif row["text"].startswith("j"):
            encoded = raw(row)
            if offset == positive_start + 1:
                if not (encoded[:1] == b"\x75" and len(encoded) == 2 or encoded[:2] == b"\x0f\x85" and len(encoded) == 6):
                    raise ValueError(f"{LABEL}.native.memberCountGuardOpcode: {encoded.hex()}")
                # The admitted stored header is exactly four; this mismatch
                # branch is untaken and its exception construction is outside
                # the positive buffered field program.
                continue
            if encoded[:1] == b"\x74" and len(encoded) == 2:
                target = int(row["va"], 16) - base + 2 + int.from_bytes(encoded[1:], "little", signed=True)
            elif encoded[:2] == b"\x0f\x84" and len(encoded) == 6:
                target = int(row["va"], 16) - base + 6 + struct.unpack_from("<i", encoded, 2)[0]
            else:
                raise ValueError(f"{LABEL}.native.positiveGuardOpcode: {row['va']} {encoded.hex()}")
            if target not in current:
                raise ValueError(f"{LABEL}.native.positiveGuardOutsideBody: {target}")
            destination = current[target]
            _need("native.nullGuardThrow", b"\xe8", raw(rows[destination])[:1])
            _need("native.nullGuardThrowEnd", b"\xcc", raw(rows[destination + 1]))
            preceding = rows[current[int(row["va"], 16) - base] - 1]
            if raw(preceding) not in (b"\x48\x85\xff", b"\x48\x85\xdb"):
                raise ValueError(f"{LABEL}.native.positiveGuardReceiverTest: {preceding['text']}")
    # No other branch in the complete method may enter a field-read interior.
    last = current[previous]
    for row in rows:
        encoded = raw(row)
        if len(encoded) == 2 and 0x70 <= encoded[0] <= 0x7F:
            target = int(row["va"], 16) - base + 2 + int.from_bytes(encoded[1:], "little", signed=True)
        elif len(encoded) == 6 and encoded[:1] == b"\x0f" and 0x80 <= encoded[1] <= 0x8F:
            target = int(row["va"], 16) - base + 6 + struct.unpack_from("<i", encoded, 2)[0]
        elif len(encoded) == 5 and encoded[0] == 0xE9:
            target = int(row["va"], 16) - base + 5 + struct.unpack_from("<i", encoded, 1)[0]
        else:
            continue
        if target in current and positive_start < current[target] <= last:
            raise ValueError(f"{LABEL}.native.branchIntoFieldInterior: {row['va']}->{target}")
    _need("native.completePositiveCallOrder", expected_calls, actual_calls)


def _validate(image: Any, contract: dict[str, Any], utf8: dict[str, Any]) -> dict[str, Any]:
    parameter, pointer, source = contract["parameter"], contract["pointer"], contract["constantSource"]
    wrappers = derive_from_image(image)
    bodies = BodyIndex(image)
    table_rva, image_size, exception_raw = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(exception_raw, lambda rva, size: image.pe.bytes_at_va(image.pe.image_base + rva, size), table_rva=table_rva, image_size=image_size)
    for record in (parameter, pointer):
        expected = record["wrapper"]
        wrapper = wrappers.get(expected["typeDefinition"])
        if wrapper is None:
            raise ValueError(f"{LABEL}.native.wrapperMissing: {expected['wrapperName']}")
        _need("native.wrapperIdentity", [expected["wrapperName"], expected["wrappedType"], expected["serializedMemberCount"]], [wrapper.name, wrapper.wrapped_type, len(wrapper.members)])
        _need("native.wrapperValueType", record["wrappedIsValueType"], wrapper.wrapped_is_value_type)
        _need("native.wrapperFields", [[row["name"], row["declaredType"], row["methodIndex"]] for row in expected["members"]], [[row.name, row.declared_type, row.method_index] for row in wrapper.members])
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, wrapper.type_definition)
        _need("native.ownedHolderSlot", 16, offsets.get("__instance"))
        for name, method in record["methods"].items():
            image.validate_method_row([method["methodIndex"], wrapper.name, name, method["pointerRva"]], label=LABEL)
            image.check_windows([method["window"]], label=LABEL)
            image.check_instruction_windows(method["instructions"], label=LABEL)
            if name == "Deserialize":
                body = bodies.body(wrapper.name, name)
                _need("native.completeDeserializeWindow", [body.pointer - image.pe.image_base, body.pointer + body.size - image.pe.image_base],
                      [method["window"]["startRva"], method["window"]["endRva"]])
    original = pointer["original"]
    _need("native.pointerOriginalType", "Beyond.Gameplay.Core.SplinePtr", image.type_name(original["typeDefinition"]))
    fields = list(image.metadata.fields_for(image.metadata.types[original["typeDefinition"]]))
    _need("native.pointerOriginalFieldCount", 1, len(fields))
    _need("native.pointerOriginalFieldName", "id", image.metadata.string(fields[0].name_index))
    field_type = image.pe.u64_at_va(int(image.registration["types"], 16) + fields[0].type_index * 8)
    _need("native.pointerIdType", "int", runtime_type_name(image.pe, image.metadata, field_type))
    _ordinary_abi(image.pe.bytes_at_va(field_type, 16), 0x08, "native.pointerIdOrdinaryAbi")
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, original["typeDefinition"])
    _need("native.pointerIdUnboxedSlot", 0, offsets["id"] - 16)
    table = int(image.registration["typeDefinitionsSizes"], 16)
    sizes = image.pe.u64_at_va(table + original["typeDefinition"] * 8)
    _need("native.pointerBoxedSize", 20, image.pe.u32_at_va(sizes))
    _need("native.pointerSourceArgument", ["Beyond.Gameplay.Core.SplinePtr"], source["typedContext"]["methodArguments"])
    validate_typed_usage_context(image, parameter["allocationContext"], label=LABEL)
    _need("native.allocationType", parameter["wrapper"]["wrappedType"], parameter["allocationContext"]["typeName"])
    validate_typed_usage_context(image, source["typedContext"], label=LABEL)
    arguments = image.instantiations.resolve(source["typedContext"]["methodSpec"][2]).arguments
    _need("native.closedPointerArgumentCount", 1, len(arguments))
    _ordinary_abi(bytes.fromhex(arguments[0].raw_type_record_hex), 0x11, "native.closedPointerOrdinaryAbi")
    method = image.metadata.methods[source["registeredMethod"]]
    _need("native.sourceInstance", 0, method.flags & 0x10)
    _need("native.sourceParameterCount", 0, method.parameter_count)
    container_section = image.metadata.sections["genericContainers"]
    if method.generic_container_index < 0:
        raise ValueError(f"{LABEL}.native.sourceGenericContainerMissing")
    at = container_section.offset + method.generic_container_index * 16
    if not container_section.offset <= at <= container_section.offset + container_section.size - 16:
        raise ValueError(f"{LABEL}.native.sourceGenericContainerBounds")
    container = struct.unpack_from("<iiii", image.metadata.buf, at)
    _need("native.sourceGenericContainer", (method.index, 1, 1), container[:3])
    return_type = image.pe.u64_at_va(int(image.registration["types"], 16) + method.return_type * 8)
    returned = image.pe.bytes_at_va(return_type, 16)
    _need("native.sourceReturnMvar", b"\x1e\x00", returned[10:12])
    _need("native.sourceReturnArgument", container[3], int.from_bytes(returned[:8], "little"))
    entry = GenericEntries(image).resolve(source["registeredMethod"], source["typedContext"]["classArguments"], source["typedContext"]["methodArguments"])
    _need("native.registeredSourcePointer", image.pe.image_base + source["sourceWindow"]["startRva"], entry["pointer"])
    image.check_windows([source["sourceWindow"], source["advanceWindow"], *source["advanceChainedWindows"]], label=LABEL)
    family = unwind.family(source["advancePointerRva"])
    actual_ranges = sorted((row["runtimeTriple"][0], row["runtimeTriple"][1]) for row in family["ranges"])
    primary = unwind.entries[source["advancePointerRva"]]
    expected_ranges = sorted([(primary[0], primary[1]), *[(row["startRva"], row["endRva"]) for row in source["advanceChainedWindows"]]])
    _need("native.advanceUnwindMembership", expected_ranges, actual_ranges)
    offsets = _source_program(image, contract)
    _int32_program(image, contract, offsets)
    _read_joins(image, parameter, bodies.body(parameter["wrapper"]["wrapperName"], "Deserialize"), source, contract["int32Source"], utf8)
    # Independently verify actual read destinations and member setters. The
    # receiver is always the current byref wrapper, including the last path.
    for read in parameter["orderedReads"]:
        _call(image, read["readCall"])
        _call(image, read["setterCall"])
        image.check_instruction_windows(read["readerSetup"] + read["returnToSetter"], label=LABEL)
        field = read["name"]
        rows = parameter["methods"]["set___" + field + "__"]["instructions"]
        slot = parameter["ownedFieldSlots"][field]
        if field == "path":
            expected = [b"\x48\x83\xec\x28", b"\x48\x8b\x49\x10", b"\x48\x85\xc9", None, None, b"\xcc", b"\x48\x89\x51" + bytes((slot,)), b"\x48\x83\xc1" + bytes((slot,)), b"\x48\x83\xc4\x28", None]
        else:
            expected = [b"\x48\x83\xec\x28", b"\x48\x8b\x41\x10", b"\x48\x85\xc0", None, None, b"\xcc", b"\x89\x50" + bytes((slot,)), b"\x48\x83\xc4\x28", b"\xc3"]
        _opcode_program(image, rows, expected, "owned." + field)
        branch = bytes.fromhex(rows[3][1])
        _need("native.ownedNonNullBranch", 0x75, branch[0])
        _need("native.ownedNonNullBranchSize", 2, len(branch))
        _need("native.ownedNonNullStoreTarget", rows[6][0], rows[3][0] + 2 + int.from_bytes(branch[1:], "little", signed=True))
        _need("native.ownedNullThrowCall", 0xE8, bytes.fromhex(rows[4][1])[0])
        if field == "path":
            _need("native.ownedPathBarrierTail", 0xE9, bytes.fromhex(rows[-1][1])[0])
    _opcode_program(image, parameter["methods"]["GetValue"]["instructions"], [b"\x48\x8b\x41\x10", b"\xc3"], "ownedParamGetter")
    _opcode_program(image, pointer["methods"]["GetValue"]["instructions"], [b"\x8b\x41\x10", b"\xc3"], "embeddedIdGetter")
    _need("native.constSourceCall", source["sourceWindow"]["startRva"], parameter["orderedReads"][0]["readCall"][2])
    return {"codecKind": "Param<SplinePtr>", "rawSize": 4, "idType": "int32", "evidenceBoundary": contract["evidenceBoundary"]}


@lru_cache(maxsize=4)
def validate_spline_ptr_native_contract(*, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None) -> dict[str, Any]:
    try:
        contract = _contract(Path(contract_path))
        pins = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None)
        if gate.status != "validated":
            return {"status": gate.status, "detail": gate.detail, "nativeInputs": pins}
        utf8 = utf8_source_helper.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
        if utf8.get("status") != "validated":
            return {"status": utf8.get("status"), "detail": utf8.get("detail"), "nativeInputs": pins, "dependency": "memorypack_utf8_source_helper"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        result = _validate(image, contract, utf8)
        after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"], gameassembly=gate.gameassembly, metadata=gate.metadata)
        if after.status != "validated":
            return {"status": after.status, "detail": after.detail, "nativeInputs": pins}
        return {"status": "validated", "nativeInputs": pins, **result}
    except (ValueError, KeyError, OSError, IndexError, struct.error) as exc:
        return {"status": "unresolved", "detail": str(exc)[:1500]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    audit = validate_spline_ptr_native_contract(contract_path=args.contract, game_root=args.game_root)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
