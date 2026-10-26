"""Proof primitives for reviewed flat scalar Param child compositions.

The caller owns its type declaration and actual scalar/cursor program. This
module authenticates ordinary leaf ABI, four-field owned Param joins and the
selected StringPool dependency. It does not select a live formatter or infer sharing
from a generic registration pointer.
"""
from __future__ import annotations

import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.memorypack.wrapper_members import derive_from_image


def need(label: str, check: str, expected: Any, actual: Any) -> None:
    if expected != actual:
        raise ValueError(f"{label}.{check}: expected={str(expected)[:350]} actual={str(actual)[:350]}")


def ordinary(image: Any, pointer: int, kind: int, label: str, *, reference: bool = False) -> None:
    raw = image.pe.bytes_at_va(pointer, 16)
    need(label, "kind", kind, raw[10])
    need(label, "modifiersByrefPinned", 0, raw[11] & 0x7F)
    if reference:
        need(label, "referenceValueMarker", 0, raw[11] & 0x80)


def owned_method_abi(image: Any, context: Any, index: int, owner: int,
                     result: tuple[str, int, bool], arguments: list[tuple[str, int, bool]],
                     label: str) -> None:
    """Authenticate declared instance method types before interpreting its stores."""
    method = image.metadata.methods[index]
    need(label, "declaringType", owner, method.declaring_type)
    need(label, "instance", 0, method.flags & 0x10)
    need(label, "receiverReference", False, context.is_value_type(image.type_name(owner)))
    need(label, "arity", len(arguments), method.parameter_count)
    parameters = list(image.metadata.parameters_for(method))
    need(label, "parameterRows", len(arguments), len(parameters))
    declared = [method.return_type, *[row.type_index for row in parameters]]
    for position, (type_index, (name, kind, reference)) in enumerate(zip(declared, [result, *arguments])):
        pointer = context.type_pointer(type_index)
        need(label, f"declaredType[{position}]", name, runtime_type_name(image.pe, image.metadata, pointer))
        ordinary(image, pointer, kind, label + f".abi[{position}]", reference=reference)


def program(image: Any, rows: list[list[Any]], expected: list[bytes | None], label: str) -> None:
    need(label, "count", len(expected), len(rows))
    image.check_instruction_windows(rows, label=label)
    for index, ((rva, encoded), opcode) in enumerate(zip(rows, expected)):
        if opcode is not None:
            need(label, f"opcode[{index}]", opcode, bytes.fromhex(encoded))
        if index:
            need(label, "contiguous", rows[index - 1][0] + len(bytes.fromhex(rows[index - 1][1])), rva)


def program_extent(rows: list[list[Any]], window: dict[str, Any], label: str) -> None:
    if not rows:
        raise ValueError(f"{label}.emptyProgram")
    need(label, "programStart", window["startRva"], rows[0][0])
    need(label, "programEnd", window["endRva"], rows[-1][0] + len(bytes.fromhex(rows[-1][1])))


def allocation_bridge(image: Any, context: Any, parameter: dict[str, Any], label: str) -> None:
    """Bind both fresh-holder paths to one authenticated typed allocation cell."""
    ordinary(image, context.type_pointer(parameter['allocationContext']['typeIndex']), 21,
             label + '.allocationTypeAbi', reference=True)
    slot = parameter["ownedFieldSlots"]["idRef"]
    ctor = parameter["methods"][".ctor"]["instructions"]
    create = parameter["methods"]["CreateInstance"]["instructions"]
    tail = [b"\x48\x8d\x4b\x10", b"\x48\x89\x43\x10", b"\x48\x83\xc4\x20", b"\x5b", None]
    split_ctor = len(ctor) == 23
    if split_ctor:
        program(image, ctor, [b"\x40\x53", b"\x48\x83\xec\x20", None, b"\x48\x8b\xd9", b"\x74\x2a", None, None,
                         b"\x48\x85\xc0", b"\x74\x3a", b"\xc7\x40" + bytes((slot,)) + b"\xff\xff\xff\xff", *tail,
                         None, None, None, None, None, b"\xeb\xb5", None, b"\xcc"], label + ".ctor")
    factory = [b"\x40\x53", b"\x48\x83\xec\x20", None, b"\x48\x8b\xd9", b"\x75\x1f", None, None, None, None, None,
                           None, None, b"\x48\x85\xc0", b"\x75\x06", None, b"\xcc", b"\xc7\x40" + bytes((slot,)) + b"\xff\xff\xff\xff", *tail]
    program(image, create, factory, label + ".create")
    if not split_ctor: program(image, ctor, factory, label + ".ctor")
    allocation_targets = []
    for rows, load_index, call_index, tail_index in ((ctor, 5, 6, 14) if split_ctor else (ctor, 10, 11, 21), (create, 10, 11, 21)):
        rva, encoded = rows[load_index]
        raw = bytes.fromhex(encoded)
        need(label, "typedClassLoadOpcode", b"\x48\x8b\x0d", raw[:3])
        need(label, "typedClassLoadSize", 7, len(raw))
        need(label, "typedClassCell", parameter["allocationContext"]["usageCellRva"], rva + 7 + struct.unpack_from('<i', raw, 3)[0])
        rva, encoded = rows[call_index]
        raw = bytes.fromhex(encoded)
        need(label, "allocationOpcode", 0xE8, raw[0])
        need(label, "allocationSize", 5, len(raw))
        allocation_targets.append(rva + 5 + struct.unpack_from('<i', raw, 1)[0])
        need(label, "ownedBarrierTail", 0xE9, bytes.fromhex(rows[tail_index][1])[0])
    need(label, "sharedTypedAllocator", allocation_targets[0], allocation_targets[1])
    need(label, "ctorTypedLoad", parameter["allocationContext"]["instructionRva"], ctor[5 if split_ctor else 10][0])
    factory_prefixes={2:(b'\x80\x3d',7),5:(b'\x48\x8d\x0d',7),6:(b'\xe8',5),7:(b'\x48\x8d\x0d',7),8:(b'\xe8',5),9:(b'\xc6\x05',7),14:(b'\xe8',5)}
    for rows, prefixes in ((ctor, {2:(b'\x80\x3d',7),15:(b'\x48\x8d\x0d',7),16:(b'\xe8',5),17:(b'\x48\x8d\x0d',7),18:(b'\xe8',5),19:(b'\xc6\x05',7),21:(b'\xe8',5)} if split_ctor else factory_prefixes), (create, factory_prefixes)):
        for index, (prefix, size) in prefixes.items():
            raw = bytes.fromhex(rows[index][1])
            need(label, 'startupOrThrowOpcode', prefix, raw[:len(prefix)])
            need(label, 'startupOrThrowSize', size, len(raw))
    branches=[(create,4,10),(create,13,16)]+([(ctor,4,15),(ctor,8,21),(ctor,20,5)] if split_ctor else [(ctor,4,10),(ctor,13,16)])
    for rows, index, destination in branches:
        rva, encoded = rows[index]
        raw = bytes.fromhex(encoded)
        need(label, 'ownedBranchTarget', rows[destination][0], rva + len(raw) + int.from_bytes(raw[-1:], 'little', signed=True))


def call(image: Any, declared: list[Any], label: str) -> None:
    rva, encoded, target = declared
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    need(label, "bytes", encoded.upper(), raw.hex().upper())
    need(label, "opcode", 0xE8, raw[0])
    need(label, "target", target, rva + 5 + struct.unpack_from("<i", raw, 1)[0])


def reader_offsets(image: Any, label: str) -> dict[str, int]:
    context = NativeReferenceContext(image)
    need(label, "readerValueType", True, context.is_value_type("MemoryPack.MemoryPackReader"))
    definitions = image.named_type_definitions.get("MemoryPack.MemoryPackReader",())
    need(label, "readerDefinitionCount", 1, len(definitions))
    boxed = runtime_type_field_offsets(image.metadata, image.pe, image.registration, definitions[0].index)
    offsets = {name: boxed[name] - 16 for name in ("currentPtr", "bufferLength", "advancedCount", "consumed")}
    if not all(0 <= value < 128 for value in offsets.values()):
        raise ValueError(f"{label}.readerFieldRange: {offsets}")
    return offsets


def integer_source(image: Any, record: dict[str, Any], offsets: dict[str, int], label: str, *, width: int = 4) -> None:
    """Prove the complete DWORD or QWORD buffered read and cursor program."""
    cur, rem, adv, used = (offsets[name] for name in ("currentPtr", "bufferLength", "advancedCount", "consumed"))
    need(label,'integerWidth',True,type(width) is int and width in (4,8));rex=b'\x48' if width==8 else b''
    image.check_windows([record["window"]], label=label)
    program_extent(record["instructions"], record["window"], label)
    expected = [b"\x48\x89\x5c\x24\x08", b"\x48\x89\x74\x24\x10", b"\x57", b"\x48\x83\xec\x20", b"\x83\x79" + bytes((rem, width)), b"\x48\x8b\xd9", None,
                b"\x48\x8b\x43" + bytes((cur,)), rex+b"\x8b\x30", b"\x8b\x7b" + bytes((rem,)), b"\x83\xc7"+bytes((256-width,)), None,
                b"\x48\x83\x43" + bytes((cur, width)), b"\x83\x43" + bytes((adv, width)), b"\x83\x43" + bytes((used, width)), b"\x89\x7b" + bytes((rem,)),
                b"\x48\x8b\x5c\x24\x30", rex+b"\x8b\xc6", b"\x48\x8b\x74\x24\x38", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    program(image, record["instructions"], expected, label)
    for index, prefix in ((6, b"\x0f\x8c"), (11, b"\x0f\x88")):
        raw = bytes.fromhex(record["instructions"][index][1])
        need(label, "guardOpcode", prefix, raw[:2])
        need(label, "guardSize", 6, len(raw))
        target=record['instructions'][index][0]+6+int.from_bytes(raw[2:],'little',signed=True)
        need(label,'coldGuardOutsideBufferedProgram',False,record['window']['startRva']<=target<record['window']['endRva'])


def boolean_source(image: Any, record: dict[str, Any], offsets: dict[str, int], label: str) -> None:
    """Prove the complete buffered byte read, cursor update and normalized AL."""
    cur,rem,adv,used=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed'))
    image.check_windows([record['window']],label=label);program_extent(record['instructions'],record['window'],label)
    expected=[b'\x48\x89\x5c\x24\x08',b'\x48\x89\x74\x24\x10',b'\x57',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((rem,1)),b'\x48\x8b\xd9',None,
        b'\x48\x8b\x43'+bytes((cur,)),b'\x0f\xb6\x30',b'\x8b\x7b'+bytes((rem,)),b'\x83\xef\x01',None,b'\x48\xff\x43'+bytes((cur,)),
        b'\xff\x43'+bytes((adv,)),b'\xff\x43'+bytes((used,)),b'\x89\x7b'+bytes((rem,)),b'\x48\x8b\x5c\x24\x30',b'\x40\x84\xf6',b'\x48\x8b\x74\x24\x38',b'\x0f\x95\xc0',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
    program(image,record['instructions'],expected,label)
    for at,opcode in ((6,b'\x0f\x8c'),(11,b'\x0f\x88')):
        rva,encoded=record['instructions'][at];raw=bytes.fromhex(encoded)
        need(label,'guardOpcode',opcode,raw[:2]);need(label,'guardSize',6,len(raw))
        target=rva+6+int.from_bytes(raw[2:],'little',signed=True)
        need(label,'coldGuardOutsideBufferedProgram',False,record['window']['startRva']<=target<record['window']['endRva'])


def uint64_source(image: Any, source: dict[str, Any], offsets: dict[str, int]) -> None:
    """Prove the buffered QWORD read and its separately owned cursor advance."""
    label='scalarParam.uint64Source';cur,rem=offsets['currentPtr'],offsets['bufferLength']
    expected=[b'\x48\x89\x5c\x24\x08',b'\x57',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((rem,8)),b'\x48\x8b\xf9',None,
              b'\x48\x8b\x5f'+bytes((cur,)),b'\xba\x08\x00\x00\x00',b'\x48\x8b\xcf',b'\x48\x8b\x1b',None,
              b'\x48\x8b\xc3',b'\x48\x8b\x5c\x24\x30',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
    program(image,source['instructions'],expected,label)
    raw=bytes.fromhex(source['instructions'][5][1]);need(label,'guardOpcode',b'\x0f\x8c',raw[:2]);need(label,'guardSize',6,len(raw))
    call(image,[*source['instructions'][10],source['advance']['pointerRva']],label+'.advanceCall')
    advance_source(image,source['advance'],offsets,label+'.advance')


def int32_advanced_source(image: Any, source: dict[str, Any], offsets: dict[str, int]) -> None:
    """Prove a DWORD result and the separately owned four-byte cursor advance."""
    label='scalarParam.int32AdvancedSource';cur,rem=offsets['currentPtr'],offsets['bufferLength']
    expected=[b'\x48\x89\x5c\x24\x08',b'\x57',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((rem,4)),b'\x48\x8b\xf9',None,
        b'\x45\x33\xc0',b'\xba\x04\x00\x00\x00',None,b'\x48\x8b\x5f'+bytes((cur,)),b'\xba\x04\x00\x00\x00',b'\x48\x8b\xcf',b'\x8b\x1b',None,
        b'\x8b\xc3',b'\x48\x8b\x5c\x24\x30',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
    program(image,source['instructions'],expected,label)
    rva,encoded=source['instructions'][5];raw=bytes.fromhex(encoded)
    need(label,'guardOpcode',b'\x7d',raw[:1]);need(label,'guardSize',2,len(raw))
    need(label,'bufferedGuardTarget',source['instructions'][9][0],rva+2+int.from_bytes(raw[1:],'little',signed=True))
    call(image,[*source['instructions'][13],source['advance']['pointerRva']],label+'.advanceCall')
    advance_source(image,source['advance'],offsets,label+'.advance')


def advance_source(image: Any, record: dict[str, Any], offsets: dict[str, int], label: str) -> None:
    image.check_windows([record["window"], *record["fragmentWindows"]], label=label)
    unwind = image.unwind_index
    family = unwind.family(record["pointerRva"])
    primary = unwind.entries[record["pointerRva"]]
    need(label, "unwindFamily", sorted([(primary[0], primary[1]), *[(row["startRva"], row["endRva"]) for row in record["fragmentWindows"]]]),
         sorted((row["runtimeTriple"][0], row["runtimeTriple"][1]) for row in family["ranges"]))
    cur, rem, adv, used = (offsets[name] for name in ("currentPtr", "bufferLength", "advancedCount", "consumed"))
    raw = image.pe.bytes_at_va(image.pe.image_base + record["window"]["startRva"], record["window"]["endRva"] - record["window"]["startRva"])
    pieces = [b"\x85\xd2", None, b"\x48\x89\x5c\x24\x10", b"\x57", b"\x48\x83\xec\x20", b"\x48\x63\xfa", b"\x48\x8b\xd9", b"\x48\x89\x74\x24\x30",
              b"\x8b\x71" + bytes((rem,)), b"\x2b\xf7", None, b"\x48\x01\x7b" + bytes((cur,)), b"\x01\x7b" + bytes((adv,)), b"\x01\x7b" + bytes((used,)), b"\x89\x73" + bytes((rem,)),
              b"\x48\x8b\x74\x24\x30", b"\x48\x8b\x5c\x24\x38", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    at = 0
    for index, piece in enumerate(pieces):
        if piece is None:
            size, prefix = (2, b"\x74") if index == 1 else (6, b"\x0f\x88")
            need(label, "guard", prefix, raw[at:at + len(prefix)])
            if index == 1:
                need(label, "zeroTarget", len(raw) - 1, at + 2 + int.from_bytes(raw[at + 1:at + 2], "little", signed=True))
            at += size
        else:
            need(label, "opcode", piece, raw[at:at + len(piece)])
            at += len(piece)
    need(label, "closedNormalExtent", len(raw), at)


def parameter_joins(image: Any, parameter: dict[str, Any], body: Any, source: dict[str, Any], integer: dict[str, Any], strings: dict[str, Any], width: int, label: str) -> None:
    """Prove the selected saved-reader/owned-holder four-field program."""
    rows, base = body.rows, image.pe.image_base
    raw = lambda row: bytes.fromhex(row["bytes"])
    declared_rows = lambda values: [[int(row["va"], 16) - base, raw(row).hex().upper()] for row in values]
    written = lambda row: (row.get("write") or {}).get("register")
    indices = {int(row["va"], 16) - base: index for index, row in enumerate(rows)}
    count = parameter["memberCountInstruction"]
    stack_count=count[1].upper()=='807C243004'
    reader_save,reader_arg,holder_load,holder_arg,holder_test=(b'\x48\x8b\xf1',b'\x48\x8b\xce',b'\x48\x8b\x3b',b'\x48\x8b\xcf',b'\x48\x85\xff') if stack_count else (b'\x48\x8b\xf9',b'\x48\x8b\xcf',b'\x48\x8b\x33',b'\x48\x8b\xce',b'\x48\x85\xf6')
    reader_aliases,holder_aliases=({'rsi','esi','si','sil'},{'rdi','edi','di','dil'}) if stack_count else ({'rdi','edi','di','dil'},{'rsi','esi','si','sil'})
    aliases = {"reader": reader_aliases, "output": {"rbx", "ebx", "bx", "bl", "bh"},
               "rcx": {"rcx", "ecx", "cx", "cl", "ch"}, "rax": {"rax", "eax", "ax", "al", "ah"}, "rdx": {"rdx", "edx", "dx", "dl", "dh"}}
    saves = {name: [i for i, row in enumerate(rows) if raw(row) == encoded] for name, encoded in (("reader", reader_save), ("output", b"\x48\x8b\xda"))}
    for name in saves:
        need(label, name + "SaveCount", 1, len(saves[name]))
    need(label, "countCompareBytes", '807C243004' if stack_count else "4080FE04", count[1].upper())
    need(label, "countActual", count, declared_rows([rows[indices[count[0]]]])[0])
    count_index = indices[count[0]]
    if not stack_count:need(label, "countStackRead", b"\x0f\xb6\x74\x24\x30", raw(rows[count_index - 1]))
    previous, start = count[0], count_index
    expected_calls = []
    for read in parameter["orderedReads"]:
        field = read["name"]
        method = parameter["methods"]["set___" + field + "__"]
        need(label, "setterIdentity", method["methodIndex"], read["setterMethodIndex"])
        need(label, "setterTarget", method["pointerRva"], read["setterCall"][2])
        need(label, "fieldOrder", True, previous < read["readCall"][0] < read["setterCall"][0])
        read_index, setter_index = indices[read["readCall"][0]], indices[read["setterCall"][0]]
        before, between = rows[indices[previous] + 1:read_index], rows[read_index + 1:setter_index]
        receiver = b"\x48\x8b\x1b" if field == "path" else holder_load
        receiver_names = aliases["output"] if field == "path" else holder_aliases
        setup = [row for row in before if raw(row) in (receiver, reader_arg)]
        need(label, "actualSetup", declared_rows(setup), read["readerSetup"])
        need(label, "setupCount", 2, len(setup))
        need(label, "readerArgument", reader_arg, raw(next(row for row in reversed(before) if written(row) in aliases["rcx"])))
        need(label, "ownedWrapper", receiver, raw(next(row for row in reversed(before) if written(row) in receiver_names)))
        need(label, "actualReturnInterval", declared_rows(between), read["returnToSetter"])
        forward = b"\x48\x8b\xd0" if field == "path" or field == "constValue" and width == 8 else b"\x8b\xd0"
        positions = [i for i, row in enumerate(between) if raw(row) == forward]
        need(label, "forwardCount", 1, len(positions))
        need(label, "returnedValueUnchanged", [], [row["text"] for row in between[:positions[0]] if written(row) in aliases["rax"] or raw(row)[:1] == b"\xe8"])
        need(label, "forwardedValueUnchanged", [], [row["text"] for row in between[positions[0] + 1:] if written(row) in aliases["rdx"]])
        need(label, "setterReceiver", b"\x48\x8b\xcb" if field == "path" else holder_arg, raw(next(row for row in reversed(between) if written(row) in aliases["rcx"])))
        target = read["readCall"][2]
        if field == "constValue":
            need(label, "actualScalarSource", source["window"]["startRva"], target)
            if 'typedContext' in source:
                context_index=indices[source['typedContext']['instructionRva']]
                need(label,'constantContextInFieldInterval',True,start<context_index<read_index)
                need(label,'constantContextArgument',b'\x48\x8b\x15',raw(rows[context_index])[:3])
                need(label,'constantContextPreserved',[],[row['text'] for row in rows[context_index+1:read_index]
                    if written(row) in aliases['rdx'] or raw(row)[:1]==b'\xe8'])
        elif field in ("idRef", "paramSource"):
            need(label, "actualIntegerSource", integer["window"]["startRva"], target)
        elif target not in strings["sourceHelpers"]:
            raise ValueError(f"{label}.actualStringSource: {target}")
        need(label, "readerPreserved", [], [row["text"] for row in rows[saves["reader"][0] + 1:read_index] if written(row) in aliases["reader"]])
        permitted = next((int(row["va"], 16) - base for row in setup if raw(row) == receiver), None) if field == "path" else None
        need(label, "outputPreserved", [], [row["text"] for row in rows[saves["output"][0] + 1:read_index] if written(row) in aliases["output"] and int(row["va"], 16) - base != permitted])
        expected_calls.extend((read["readCall"][0], read["setterCall"][0]))
        previous = read["setterCall"][0]
    last = indices[previous]
    actual_calls = []
    for index in range(start + 1, last + 1):
        row, encoded = rows[index], raw(rows[index])
        if encoded[:1] == b"\xe8":
            actual_calls.append(int(row["va"], 16) - base)
        elif row["text"].startswith(("db ", "call ", "jmp ")):
            raise ValueError(f"{label}.unknownOrTransfer: {row['va']} {row['text']}")
        elif row["text"].startswith("j"):
            if index == start + 1:
                need(label, "countMismatchGuard", b"\x0f\x85", encoded[:2])
                need(label, "countMismatchGuardSize", 6, len(encoded))
                continue
            if encoded[:1] == b"\x74" and len(encoded) == 2:
                target = int(row["va"], 16) - base + 2 + int.from_bytes(encoded[1:], "little", signed=True)
            elif encoded[:2] == b"\x0f\x84" and len(encoded) == 6:
                target = int(row["va"], 16) - base + 6 + struct.unpack_from("<i", encoded, 2)[0]
            else:
                raise ValueError(f"{label}.unexpectedGuard: {encoded.hex()}")
            destination = indices[target]
            need(label, "guardThrow", b"\xe8", raw(rows[destination])[:1])
            need(label, "guardThrowEnd", b"\xcc", raw(rows[destination + 1]))
            need(label, "guardReceiverTest", True, raw(rows[index - 1]) in (holder_test, b"\x48\x85\xdb"))
    for row in rows:
        encoded, origin = raw(row), int(row["va"], 16) - base
        if len(encoded) == 2 and 0x70 <= encoded[0] <= 0x7F:
            target = origin + 2 + int.from_bytes(encoded[1:], "little", signed=True)
        elif len(encoded) == 6 and encoded[0] == 15 and 0x80 <= encoded[1] <= 0x8F:
            target = origin + 6 + struct.unpack_from("<i", encoded, 2)[0]
        elif len(encoded) == 5 and encoded[0] == 233:
            target = origin + 5 + struct.unpack_from("<i", encoded, 1)[0]
        else:
            continue
        if target in indices and start < indices[target] <= last:
            raise ValueError(f"{label}.branchIntoFieldInterior: {origin}->{target}")
    need(label, "positiveCallOrder", expected_calls, actual_calls)


def parameter_setter(image: Any, instructions: list[list[Any]], *, name: str, slot: int, width: int, label: str, floating: bool = False) -> None:
    """Prove the owned store, null guard and reference-barrier tail."""
    if name == "path":
        store=b"\x48\x89\x51" + bytes((slot,));advance=b"\x48\x83\xc1" + bytes((slot,))
        nonnull=bytes.fromhex(instructions[3][1])==b'\x75\x06'
        expected = [b"\x48\x83\xec\x28", b"\x48\x8b\x49\x10", b"\x48\x85\xc9", None, *([None,b'\xcc',store,advance,b'\x48\x83\xc4\x28',None] if nonnull else [store,advance,b'\x48\x83\xc4\x28',None,None,b'\xcc'])]
    else:
        if floating:need(label,'floatingStoreWidth',4,width)
        store = ((b'\xf3\x0f\x11\x48' if floating else b'\x88\x50' if width == 1 else b'\x48\x89\x50' if width == 8 else b'\x89\x50')
                 if name == 'constValue' else b'\x89\x50') + bytes((slot,))
        expected = [b"\x48\x83\xec\x28", b"\x48\x8b\x41\x10", b"\x48\x85\xc0", None, None, b"\xcc", store, b"\x48\x83\xc4\x28", b"\xc3"]
    program(image, instructions, expected, label + ".setter." + name)
    branch = bytes.fromhex(instructions[3][1])
    if name == "path":
        need(label, "nullPathBranch", 0x75 if nonnull else 0x74, branch[0])
        need(label, "nullPathBranchSize", 2, len(branch))
        need(label, "nullPathTarget", instructions[6 if nonnull else 8][0], instructions[3][0] + 2 + int.from_bytes(branch[1:], "little", signed=True))
        need(label, "pathBarrierTail", 0xE9, bytes.fromhex(instructions[9 if nonnull else 7][1])[0])
        need(label, "pathNullThrow", 0xE8, bytes.fromhex(instructions[4 if nonnull else 8][1])[0])
    else:
        need(label, "nonNullStoreBranch", 0x75, branch[0])
        need(label, "nonNullStoreTarget", instructions[6][0], instructions[3][0] + 2 + int.from_bytes(branch[1:], "little", signed=True))
        need(label, "nullThrow", 0xE8, bytes.fromhex(instructions[4][1])[0])


def read_scalar_contract(path: Path, *, schema: str, type_name: str, codec_kind: str) -> dict[str, Any]:
    label=schema.removeprefix('endfield.').rsplit('.',1)[0];contract=json.loads(path.read_bytes())
    for key,expected in (('schema',schema),('status','exact-current-build'),('codecKind',codec_kind),
                         ('dependencies',[{'role':'pooledStringSource','path':pooled_source_helper.CONTRACT_PATH.name}])):
        need(label,key,expected,contract.get(key))
    leaf,parameter=contract['leaf'],contract['parameter']
    need(label,'leafType',type_name,leaf['typeName'])
    need(label,'parameterType','Beyond.Gameplay.Actions.Param`1<'+type_name+'>',parameter['wrappedType'])
    need(label,'fields',[['constValue',type_name],['idRef','int'],['paramSource','int'],['path','string']],[[r['name'],r['declaredType']] for r in parameter['orderedReads']])
    need(label,'pinScope',{'GameAssembly.dll','global-metadata.dat'},set(contract['nativeInputs']))
    return contract


def validate(path: Path, *, schema: str, type_name: str, codec_kind: str, game_root: Path | None,
             prove_source: Callable[[Any, dict[str, Any], dict[str, int]], None],
             gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    """Authenticate one caller-owned leaf and return no rows on any refusal."""
    label = schema.removeprefix("endfield.").rsplit('.',1)[0]
    try:
        contract = read_scalar_contract(path,schema=schema,type_name=type_name,codec_kind=codec_kind)
        pins = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        if (gameassembly is None)!=(metadata is None):raise ValueError(f'{label}.explicitNativePair: both paths required')
        gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"], gameassembly=Path(gameassembly) if gameassembly is not None else root.parent / "GameAssembly.dll" if root else None,
            metadata=Path(metadata) if metadata is not None else root / "il2cpp_data/Metadata/global-metadata.dat" if root else None)
        if gate.status != "validated":
            return {"status": gate.status, "detail": gate.detail, "nativeInputs": pins}
        strings = pooled_source_helper.validate_current_native_contract(gameassembly=gate.gameassembly, metadata=gate.metadata)
        if strings.get("status") != "validated":
            return {"status": strings.get("status"), "detail": strings.get("detail"), "dependency": "pooledStringSource"}
        # Cache only the expensive composition, after the selected-input gate.
        # Declarations are a value key, not a pinned tracked-file digest.
        result = _cached_composition(gate.gameassembly, gate.metadata,
            json.dumps(contract, sort_keys=True), json.dumps(strings, sort_keys=True), prove_source, label)
        after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"], gameassembly=gate.gameassembly, metadata=gate.metadata)
        if after.status != "validated":
            return {"status": after.status, "detail": after.detail, "nativeInputs": pins}
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,strings['nativeInputs'])
        if failed:return {**failed,'dependency':'pooledStringSource'}
        return {"status": "validated", "nativeInputs": pins, **result}
    except (ValueError, KeyError, OSError, IndexError, StopIteration, struct.error, TypeError) as exc:
        return native_validation_failure(exc,label=label,source_path=path)


@lru_cache(maxsize=8)
def _cached_composition(gameassembly: Path, metadata: Path, declaration: str,
                        string_declaration: str, prove_source: Callable, label: str) -> dict[str, Any]:
    image = open_native_image(gameassembly, metadata)
    return _composition(image, json.loads(declaration), json.loads(string_declaration), prove_source, label)


def _composition(image: Any, contract: dict[str, Any], strings: dict[str, Any], prove_source: Callable, label: str) -> dict[str, Any]:
    need(label, 'pathEncoding', 'int32-pool-index', strings.get('wireEncoding'))
    leaf, parameter, source = contract["leaf"], contract["parameter"], contract["constantSource"]
    context, wrappers, bodies = NativeReferenceContext(image), derive_from_image(image), image.body_index
    width = leaf["rawSize"]
    primitive = {"int": (8, 4), "ulong": (11, 8)}.get(leaf["fieldType"])
    need(label, "primitiveDeclaration", primitive, (leaf["fieldKind"], width))
    need(label, "valueLeaf", True, context.is_value_type(leaf["typeName"]))
    need(label, "originalType", leaf["typeName"], image.type_name(leaf["typeDefinition"]))
    fields = [field for field in image.metadata.fields_for(image.metadata.types[leaf["typeDefinition"]])
              if not context.field_attributes(field.type_index) & 0x10]
    need(label, "leafFieldCount", 1, len(fields))
    field = fields[0]
    need(label, "leafFieldName", leaf["fieldName"], image.metadata.string(field.name_index))
    pointer = context.type_pointer(field.type_index)
    need(label, "leafFieldType", leaf["fieldType"], runtime_type_name(image.pe, image.metadata, pointer))
    ordinary(image, pointer, leaf["fieldKind"], label + ".leafAbi")
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, leaf["typeDefinition"])
    need(label, "leafUnboxedSlot", 0, offsets[leaf["fieldName"]] - 16)
    sizes = image.pe.u64_at_va(int(image.registration["typeDefinitionsSizes"], 16) + leaf["typeDefinition"] * 8)
    need(label, "leafBoxedSize", width + 16, image.pe.u32_at_va(sizes))
    for definition, name, methods in ((parameter["typeDefinition"], parameter["wrapperName"], parameter["methods"]), (leaf["wrapperTypeDefinition"], leaf["wrapperName"], leaf["methods"])):
        wrapper = wrappers[definition]
        need(label, "wrapperName", name, wrapper.name)
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, definition)
        need(label, "ownedHolder", 16, offsets["__instance"])
        holder = next(field for field in image.metadata.fields_for(image.metadata.types[definition]) if image.metadata.string(field.name_index) == "__instance")
        need(label, "holderType", parameter["wrappedType"] if definition == parameter["typeDefinition"] else leaf["typeName"], context.type_name(holder.type_index))
        ordinary(image, context.type_pointer(holder.type_index), 21 if definition == parameter["typeDefinition"] else 17,
                 label + ".holderAbi", reference=definition == parameter["typeDefinition"])
        for method_name, record in methods.items():
            image.validate_method_row([record["methodIndex"], name, method_name, record["pointerRva"]], label=label)
            if method_name in (".ctor", "CreateInstance"):
                owned_method_abi(image, context, record["methodIndex"], definition, ("void", 1, False), [], label + "." + name + "." + method_name)
            elif method_name == "GetValue":
                returned = ((parameter["wrappedType"], 21, True) if definition == parameter["typeDefinition"]
                            else (leaf["typeName"], 17, False))
                owned_method_abi(image, context, record["methodIndex"], definition, returned, [], label + "." + name + ".GetValue")
            elif method_name.startswith("set___"):
                field_name = method_name[len("set___"):-2]
                argument = ({"constValue": (leaf["typeName"], 17, False), "idRef": ("int", 8, False),
                             "paramSource": ("int", 8, False), "path": ("string", 14, True)}[field_name]
                            if definition == parameter["typeDefinition"] else (leaf["fieldType"], leaf["fieldKind"], False))
                owned_method_abi(image, context, record["methodIndex"], definition, ("void", 1, False), [argument], label + "." + name + "." + method_name)
            image.check_windows([record["window"]], label=label)
            image.check_instruction_windows(record["instructions"], label=label)
            program_extent(record["instructions"], record["window"], label + "." + method_name)
            if method_name == "Deserialize":
                body = bodies.body(name, method_name)
                need(label, "completeReader", [body.pointer - image.pe.image_base, body.pointer + body.size - image.pe.image_base], [record["window"]["startRva"], record["window"]["endRva"]])
    need(label, "parameterMembers", parameter["members"], [{"name": row.name, "declaredType": row.declared_type, "methodIndex": row.method_index} for row in wrappers[parameter["typeDefinition"]].members])
    validate_typed_usage_context(image, parameter["allocationContext"], label=label)
    need(label, "allocationType", parameter["wrappedType"], parameter["allocationContext"]["typeName"])
    allocation_bridge(image, context, parameter, label + ".allocationBridge")
    validate_typed_usage_context(image, source["typedContext"], label=label)
    need(label, "typedSource", ["MemoryPack.MemoryPackReader", "ReadUnmanaged", [], [leaf["typeName"]]], [source["typedContext"][key] for key in ("typeName", "methodName", "classArguments", "methodArguments")])
    arguments = image.instantiations.resolve(source["typedContext"]["methodSpec"][2]).arguments
    need(label, "argumentCount", 1, len(arguments))
    ordinary(image, arguments[0].type_pointer_va, 17, label + ".closedValueAbi")
    method = image.metadata.methods[source["registeredMethod"]]
    need(label, "sourceInstance", 0, method.flags & 16)
    need(label, "sourceParameterCount", 0, method.parameter_count)
    section = image.metadata.sections["genericContainers"]
    at = section.offset + method.generic_container_index * 16
    if method.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
        raise ValueError(f"{label}.genericContainerBounds")
    container = struct.unpack_from("<iiii", image.metadata.buf, at)
    need(label, "genericContainer", (method.index, 1, 1), container[:3])
    returned = image.pe.bytes_at_va(context.type_pointer(method.return_type), 16)
    need(label, "returnMvar", b"\x1e\x00", returned[10:12])
    need(label, "returnParameter", container[3], int.from_bytes(returned[:8], "little"))
    entry = GenericEntries(image).resolve(method.index, [], [leaf["typeName"]])
    need(label, "registeredProvenance", source["registeredEntry"], json.loads(json.dumps(entry)))
    need(label, "registeredEqualityDeclaration", source["actualEqualsRegistered"], entry["pointer"] == image.pe.image_base + source["window"]["startRva"])
    image.check_windows([source["window"]], label=label)
    program_extent(source["instructions"], source["window"], label + ".constantSource")
    offsets = reader_offsets(image, label)
    prove_source(image, source, offsets)
    integer_source(image, contract["int32Source"], offsets, label + ".int32Source")
    parameter_joins(image, parameter, bodies.body(parameter["wrapperName"], "Deserialize"), source, contract["int32Source"], strings, width, label)
    for read in parameter["orderedReads"]:
        call(image, read["readCall"], label)
        call(image, read["setterCall"], label)
        name = read["name"]
        slot = parameter["ownedFieldSlots"][name]
        instructions = parameter["methods"]["set___" + name + "__"]["instructions"]
        parameter_setter(image,instructions,name=name,slot=slot,width=width,label=label)
    program(image, parameter["methods"]["GetValue"]["instructions"], [b"\x48\x8b\x41\x10", b"\xc3"], label + ".ownedGetter")
    prefix = b"\x48" if width == 8 else b""
    program(image, leaf["methods"]["GetValue"]["instructions"], [prefix + b"\x8b\x41\x10", b"\xc3"], label + ".leafGetter")
    program(image, leaf["methods"]["set___" + leaf["fieldName"] + "__"]["instructions"], [prefix + b"\x89\x51\x10", b"\xc3"], label + ".leafSetter")
    return {"codecKind": contract["codecKind"], "rawSize": width, "fieldName": leaf["fieldName"], "fieldType": leaf["fieldType"], "pathEncoding":"int32-pool-index", "registeredPointerEqualsActualCall": source["actualEqualsRegistered"], "evidenceBoundary": contract["evidenceBoundary"]}
