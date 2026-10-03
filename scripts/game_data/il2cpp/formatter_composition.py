"""Authenticate reviewed static MemoryPack formatter compositions.

The domain caller owns the selected-build gate, contract schema and stored
field grammar. This algorithm joins registered original/adapter/wrapper type
pointers, constructor contexts, concrete conversion/formatter vtables and
generic context entries. Native windows authenticate reviewed ABI facts;
their presence never derives a wire width or claims a live provider result.
"""
from __future__ import annotations

import struct
from typing import Any
from scripts.game_data.il2cpp.context import method_spec_record, select_rgctx_range
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name


def _type_pointer(image: NativeImage, index: int, label: str) -> int:
    if not 0 <= index < image.registration["typesCount"]:
        raise ValueError(f"{label}.native:type-index={index}")
    return image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)


def _vtable(image: NativeImage, definition: int, slot: int, expected: int, label: str) -> None:
    metadata = image.metadata
    owner = metadata.types[definition]
    section = metadata.sections["vtableMethods"]
    offset = section.offset + 4 * (owner.vtable_start + slot)
    if not (0 <= slot < owner.vtable_count and section.offset <= offset <= section.offset + section.size - 4):
        raise ValueError(f"{label}.native:vtable-range={definition}/{slot}")
    word = struct.unpack_from("<I", metadata.buf, offset)[0]
    if word != (0x60000000 | (expected << 1) | 1):
        raise ValueError(f"{label}.native:vtable-method={definition}/{slot}:expected={expected}:word={word:#x}")


def validate_registered_formatter_composition(image: NativeImage, contract: dict[str, Any], *, label: str) -> None:
    """Authenticate explicit reviewed joins; never infer a wire grammar or live selection."""
    if not contract["registrations"] or not contract["interfaces"] or not contract["genericContexts"]:
        raise ValueError(f"{label}.contract:empty-composition")
    originals_declared = [row["originalType"] for row in contract["registrations"]]
    interfaces_declared = [row["originalType"] for row in contract["interfaces"]]
    if len(set(originals_declared)) != len(originals_declared) or sorted(originals_declared) != sorted(interfaces_declared):
        raise ValueError(f"{label}.contract:registration-interface-bijection")
    wrappers = {row["originalType"]: row["wrapperType"] for row in contract["registrations"]}
    if any(wrappers[row["originalType"]] != row["wrapperType"] for row in contract["interfaces"]):
        raise ValueError(f"{label}.contract:registered-wrapper-interface-identity")
    image.check_windows(contract["codeWindows"], label=label)
    for window in contract.get("instructionWindows", []):
        image.check_instruction_windows([[window["rva"], window["hex"]]], label=label)
    for method in contract["methods"]:
        image.validate_method_row(method, label=label)
    for row in contract.get("usageContexts", []):
        validate_typed_usage_context(image, row, label=label)
    originals: dict[str, int] = {}
    for row in contract["registrations"]:
        instance = image.instantiations.resolve(row["classInstantiation"])
        if len(instance.arguments) != 2:
            raise ValueError(f"{label}.native:adapter-arity")
        arguments = [a.type_pointer_va for a in instance.arguments]
        names = [runtime_type_name(image.pe, image.metadata, p) for p in arguments]
        if names != [row["originalType"], row["wrapperType"]]:
            raise ValueError(f"{label}.native:adapter-arguments={row['originalType']}")
        adapter_pointer = _type_pointer(image, row["adapterTypeIndex"], label)
        raw = image.pe.bytes_at_va(adapter_pointer, 16)
        carrier = struct.unpack_from("<Q", raw)[0]
        if raw[10] != 0x15:
            raise ValueError(f"{label}.native:adapter-type-kind")
        definition_pointer, instance_pointer = struct.unpack("<QQ", image.pe.bytes_at_va(carrier, 16))
        if (runtime_type_name(image.pe, image.metadata, definition_pointer) != "Beyond.MemoryPack.GenericMemoryPackFormatter`2"
                or image.instantiations.resolve_pointer(instance_pointer).index != instance.index
                or _type_pointer(image, row["keyTypeIndex"], label) != arguments[0]):
            raise ValueError(f"{label}.native:adapter-key-identity={row['originalType']}")
        spec_index = row["constructorMethodSpecIndex"]
        if not 0 <= spec_index < image.registration["methodSpecsCount"]:
            raise ValueError(f"{label}.native:constructor-method-spec-index={spec_index}")
        address = int(image.registration["methodSpecs"], 16) + spec_index * 12
        actual = method_spec_record(image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
                                    image.registration["genericInstsCount"], source=label, offset=address)
        if list(actual) != row["constructorMethodSpec"] or actual[1:] != (instance.index, -1):
            raise ValueError(f"{label}.native:constructor-context")
        method = image.metadata.methods[actual[0]]
        if (image.type_name(method.declaring_type) != "Beyond.MemoryPack.GenericMemoryPackFormatter`2"
                or image.metadata.string(method.name_index) != ".ctor"):
            raise ValueError(f"{label}.native:constructor-method")
        originals[row["originalType"]] = arguments[0]
    for row in contract["interfaces"]:
        owner = image.metadata.types[row["wrapperDefinition"]]
        if image.type_name(owner.index) != row["wrapperType"]:
            raise ValueError(f"{label}.native:interface-wrapper")
        section = image.metadata.sections["interfaceOffsets"]
        offset = section.offset + owner.interface_offsets_start * 8
        length = owner.interface_offsets_count * 8
        if not section.offset <= offset <= section.offset + section.size - length:
            raise ValueError(f"{label}.native:interface-range")
        pairs = list(struct.iter_unpack("<ii", image.metadata.buf[offset:offset + length]))
        expected = (row["interfaceTypeIndex"], row["interfaceOffset"])
        if pairs.count(expected) != 1:
            raise ValueError(f"{label}.native:interface-slot")
        pointer = _type_pointer(image, row["interfaceTypeIndex"], label)
        raw = image.pe.bytes_at_va(pointer, 16)
        if raw[10] != 0x15:
            raise ValueError(f"{label}.native:interface-type-kind")
        carrier = struct.unpack_from("<Q", raw)[0]
        definition_pointer, instance_pointer = struct.unpack("<QQ", image.pe.bytes_at_va(carrier, 16))
        arguments = image.instantiations.resolve_pointer(instance_pointer).arguments
        if (runtime_type_name(image.pe, image.metadata, definition_pointer) != "Beyond.MemoryPack.IMemoryPackDeSerializeWrapper`1"
                or len(arguments) != 1 or arguments[0].type_pointer_va != originals[row["originalType"]]):
            raise ValueError(f"{label}.native:conversion-argument")
        _vtable(image, owner.index, row["interfaceOffset"], row["getValueMethodIndex"], label)
        method = image.metadata.methods[row["getValueMethodIndex"]]
        if method.declaring_type != owner.index or image.metadata.string(method.name_index) != "GetValue":
            raise ValueError(f"{label}.native:conversion-method-identity")
        formatter = image.metadata.methods[row["formatterDeserializeMethodIndex"]]
        if formatter.declaring_type != row["formatterDefinition"] or image.metadata.string(formatter.name_index) != "Deserialize":
            raise ValueError(f"{label}.native:formatter-method-identity")
        if _type_pointer(image, method.return_type, label) != originals[row["originalType"]]:
            raise ValueError(f"{label}.native:conversion-return-type")
        _vtable(image, row["formatterDefinition"], 5, row["formatterDeserializeMethodIndex"], label)
    validate_generic_contexts(image, contract["genericContexts"], label=label)


def validate_generic_contexts(image: NativeImage, rows: list[dict[str, Any]], *, label: str) -> None:
    """Authenticate complete symbolic RGCTX ownership, ranges and slots."""
    for row in rows:
        owner = image.metadata.methods[row["definition"]] if row["isMethod"] else image.metadata.types[row["definition"]]
        type_index = owner.declaring_type if row["isMethod"] else owner.index
        image_name = image.metadata.string(image.metadata.images[image.owners[type_index]].name_index)
        module = image.modules[image_name]
        if image_name != row["image"] or owner.token != row["token"]:
            raise ValueError(f"{label}.native:context-owner")
        ranges_va = image.pe.u64_at_va(module + 0x48)
        entries_va = image.pe.u64_at_va(module + 0x58)
        actual = select_rgctx_range(image.pe.bytes_at_va(ranges_va, image.pe.u32_at_va(module + 0x40) * 12),
                                    image.pe.u32_at_va(module + 0x50), owner.token, source=label, offset=ranges_va)
        if actual != (row["start"], row["count"]):
            raise ValueError(f"{label}.native:context-range")
        if sorted(entry["relativeSlot"] for entry in row["entries"]) != list(range(row["count"])):
            raise ValueError(f"{label}.contract:complete-context-slots")
        for entry in row["entries"]:
            raw = image.pe.bytes_at_va(entries_va + (row["start"] + entry["relativeSlot"]) * 16, 16)
            if raw.hex().upper() != entry["rawHex"]:
                raise ValueError(f"{label}.native:context-entry")


def validate_typed_usage_context(image: NativeImage, row: dict[str, Any], *, label: str) -> None:
    """Check one reviewed RIP-relative type/MethodSpec usage and exact arguments."""
    raw = bytes.fromhex(row["instructionHex"])
    image.check_instruction_windows([[row["instructionRva"], row["instructionHex"]]], label=label)
    if len(raw) != 7 or raw[:2] not in (b"\x48\x8b", b"\x4c\x8b") or raw[2] & 0xc7 != 5:
        raise ValueError(f"{label}.native:usage-rip-load")
    cell = row["instructionRva"] + len(raw) + struct.unpack_from("<i", raw, 3)[0]
    if cell != row["usageCellRva"]:
        raise ValueError(f"{label}.native:usage-cell-target")
    actual = image.pe.bytes_at_va(image.pe.image_base + cell, 8)
    if actual.hex().upper() != row["usageRawHex"]:
        raise ValueError(f"{label}.native:usage-cell-bytes")
    usage = int.from_bytes(actual, "little")
    if usage >> 32 or not usage & 1 or usage >> 29 != row["tag"]:
        raise ValueError(f"{label}.native:usage-kind")
    index = (usage & 0x1fffffff) >> 1
    if row["tag"] == 1:
        if index != row["typeIndex"]:
            raise ValueError(f"{label}.native:usage-type-index")
        pointer = _type_pointer(image, index, label)
        if runtime_type_name(image.pe, image.metadata, pointer) != row["typeName"] or image.pe.bytes_at_va(pointer, 16).hex().upper() != row["typeRawHex"]:
            raise ValueError(f"{label}.native:usage-type-identity")
    elif row["tag"] == 6:
        if index != row["methodSpecIndex"] or not 0 <= index < image.registration["methodSpecsCount"]:
            raise ValueError(f"{label}.native:usage-method-spec-index")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(image.pe.bytes_at_va(address, 12), len(image.metadata.methods), image.registration["genericInstsCount"], source=label, offset=address)
        method = image.metadata.methods[spec[0]]
        if list(spec) != row["methodSpec"] or image.type_name(method.declaring_type) != row["typeName"] or image.metadata.string(method.name_index) != row["methodName"]:
            raise ValueError(f"{label}.native:usage-method-identity")
        for instance, field in zip(spec[1:], ("classArguments", "methodArguments")):
            names = [] if instance == -1 else [runtime_type_name(image.pe, image.metadata, arg.type_pointer_va) for arg in image.instantiations.resolve(instance).arguments]
            if names != row[field]:
                raise ValueError(f"{label}.native:usage-method-arguments={field}")
    else:
        raise ValueError(f"{label}.contract:unsupported-usage-kind={row['tag']}")
