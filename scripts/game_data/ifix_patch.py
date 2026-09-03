"""Bounded structural reader for the installed IFix ``.patch.bytes`` files.

The two current files expose a 128-byte opaque prefix followed by the IFix
file-vm stream.  The stream framing is the format written by IFix's
``FileVirtualMachineBuilder``: strings, count-delimited metadata tables,
method bodies, and fix records.  This reader names only those boundaries and
metadata fields which are explicit in that writer.  Instruction words,
exception records, and the prefix remain opaque bytes; a parsed fix record is
not evidence that the patch was loaded or activated at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# This is the little-endian UInt64 witness present at offset 128 in both
# current Endfield files.  It is deliberately not substituted with the
# upstream Tencent InjectFix magic: the installed fork's bytes are the direct
# evidence for this value.
PATCH_MAGIC = 0x2DF86FA52CF233A2
OPAQUE_PREFIX_SIZE = 128
MAX_COUNT = 1_000_000
MAX_STRING_BYTES = 1 << 20


class BinaryFormatError(ValueError):
    """Raised when an IFix stream cannot be consumed exactly and safely."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


@dataclass(frozen=True)
class OpaqueRegion:
    name: str
    offset: int
    length: int
    sha256: str
    prefix_hex: str
    suffix_hex: str

    @classmethod
    def make(cls, name: str, data: bytes, offset: int, end: int) -> "OpaqueRegion":
        raw = data[offset:end]
        return cls(name, offset, len(raw), _sha256(raw), raw[:16].hex(), raw[-16:].hex())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "offset": self.offset,
            "length": self.length,
            "sha256": self.sha256,
            "prefixHex": self.prefix_hex,
            "suffixHex": self.suffix_hex,
            "fieldStatus": "opaque",
        }


@dataclass(frozen=True)
class StringRecord:
    offset: int
    end_offset: int
    value: str
    byte_length: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "endOffset": self.end_offset,
            "byteLength": self.byte_length,
            "value": self.value,
        }


@dataclass(frozen=True)
class MethodBody:
    index: int
    record_offset: int
    code_size: int
    code_offset: int
    code_end_offset: int
    exception_count: int
    exception_offset: int
    end_offset: int
    code_opaque: OpaqueRegion
    exception_opaque: OpaqueRegion

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "recordOffset": self.record_offset,
            "codeSize": self.code_size,
            "codeOffset": self.code_offset,
            "codeEndOffset": self.code_end_offset,
            "exceptionCount": self.exception_count,
            "exceptionOffset": self.exception_offset,
            "endOffset": self.end_offset,
            "code": self.code_opaque.to_dict(),
            "exceptions": self.exception_opaque.to_dict(),
        }


@dataclass(frozen=True)
class MethodSignature:
    offset: int
    end_offset: int
    is_generic: bool
    declaring_type_index: int
    name: StringRecord
    generic_type_indices: tuple[int, ...]
    parameter_type_indices: tuple[int, ...]
    parameter_generic_flags: tuple[bool, ...]
    parameter_generic_names: tuple[StringRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "endOffset": self.end_offset,
            "isGeneric": self.is_generic,
            "declaringTypeIndex": self.declaring_type_index,
            "name": self.name.to_dict(),
            "genericTypeIndices": list(self.generic_type_indices),
            "parameterTypeIndices": list(self.parameter_type_indices),
            "parameterGenericFlags": list(self.parameter_generic_flags),
            "parameterGenericNames": [item.to_dict() for item in self.parameter_generic_names],
        }


@dataclass(frozen=True)
class FixRecord:
    signature: MethodSignature
    fix_method_id: int
    end_offset: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "signature": self.signature.to_dict(),
            "fixMethodId": self.fix_method_id,
            "endOffset": self.end_offset,
            "activationStatus": "not-established-by-file-framing",
        }


class _Reader:
    def __init__(self, data: bytes, source: str):
        self.data = data
        self.source = source
        self.offset = 0

    def need(self, size: int, label: str) -> None:
        if size < 0 or self.offset < 0 or size > len(self.data) - self.offset:
            raise BinaryFormatError(
                f"{self.source}: {label} range [{self.offset}, {self.offset + size}) "
                f"is outside source length {len(self.data)}"
            )

    def raw(self, size: int, label: str) -> tuple[int, int, bytes]:
        self.need(size, label)
        start = self.offset
        self.offset += size
        return start, self.offset, self.data[start:self.offset]

    def u8(self, label: str) -> int:
        _, _, raw = self.raw(1, label)
        return raw[0]

    def i32(self, label: str) -> int:
        _, _, raw = self.raw(4, label)
        return struct.unpack("<i", raw)[0]

    def u64(self, label: str) -> int:
        _, _, raw = self.raw(8, label)
        return struct.unpack("<Q", raw)[0]

    def count(self, label: str) -> int:
        value = self.i32(label)
        if value < 0 or value > MAX_COUNT:
            raise BinaryFormatError(f"{self.source}: {label} count {value} outside 0..{MAX_COUNT}")
        return value

    def boolean(self, label: str) -> bool:
        value = self.u8(label)
        if value not in (0, 1):
            raise BinaryFormatError(f"{self.source}: {label} boolean byte {value} is not 0 or 1")
        return bool(value)

    def string(self, label: str) -> StringRecord:
        start = self.offset
        value_len = 0
        shift = 0
        for index in range(5):
            byte = self.u8(f"{label} 7-bit length")
            value_len |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
            shift += 7
        else:
            raise BinaryFormatError(f"{self.source}: {label} 7-bit length exceeds five bytes")
        if value_len > MAX_STRING_BYTES:
            raise BinaryFormatError(
                f"{self.source}: {label} UTF-8 length {value_len} exceeds {MAX_STRING_BYTES}"
            )
        _, end, raw = self.raw(value_len, f"{label} UTF-8 payload")
        try:
            value = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise BinaryFormatError(f"{self.source}: {label} is not strict UTF-8: {exc}") from exc
        return StringRecord(start, end, value, value_len)


def _check_index(value: int, count: int, label: str, source: str) -> None:
    # -1 is used by IFix for some optional type/method references.
    if value < -1 or value >= count:
        raise BinaryFormatError(f"{source}: {label} index {value} outside -1..{count - 1}")


def _signature(reader: _Reader, type_count: int, label: str) -> MethodSignature:
    start = reader.offset
    generic = reader.boolean(f"{label} generic flag")
    declaring = reader.i32(f"{label} declaring type")
    _check_index(declaring, type_count, f"{label} declaring type", reader.source)
    name = reader.string(f"{label} name")
    generic_indices: list[int] = []
    if generic:
        generic_count = reader.count(f"{label} generic argument")
        for index in range(generic_count):
            value = reader.i32(f"{label} generic argument {index}")
            _check_index(value, type_count, f"{label} generic argument {index}", reader.source)
            generic_indices.append(value)
    parameter_count = reader.count(f"{label} parameter")
    parameter_types: list[int] = []
    parameter_flags: list[bool] = []
    parameter_names: list[StringRecord] = []
    for index in range(parameter_count):
        parameter_generic = reader.boolean(f"{label} parameter {index} generic flag") if generic else False
        parameter_flags.append(parameter_generic)
        if parameter_generic:
            parameter_names.append(reader.string(f"{label} parameter {index} generic name"))
        else:
            value = reader.i32(f"{label} parameter {index} type")
            _check_index(value, type_count, f"{label} parameter {index} type", reader.source)
            parameter_types.append(value)
    return MethodSignature(
        offset=start,
        end_offset=reader.offset,
        is_generic=generic,
        declaring_type_index=declaring,
        name=name,
        generic_type_indices=tuple(generic_indices),
        parameter_type_indices=tuple(parameter_types),
        parameter_generic_flags=tuple(parameter_flags),
        parameter_generic_names=tuple(parameter_names),
    )


def parse_ifix_patch(data: bytes, *, source: str = "<bytes>") -> dict[str, Any]:
    """Parse one current IFix patch with strict bounds and exact consumption."""

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    data = bytes(data)
    if len(data) < OPAQUE_PREFIX_SIZE + 8:
        raise BinaryFormatError(f"{source}: shorter than opaque prefix and magic")
    reader = _Reader(data, source)
    prefix_start, prefix_end, _ = reader.raw(OPAQUE_PREFIX_SIZE, f"{source} opaque prefix")
    prefix = OpaqueRegion.make("opaque-prefix", data, prefix_start, prefix_end)
    magic_offset = reader.offset
    magic = reader.u64(f"{source} instruction magic")
    if magic != PATCH_MAGIC:
        raise BinaryFormatError(f"{source}: instruction magic 0x{magic:016x} != 0x{PATCH_MAGIC:016x}")

    bridge = reader.string(f"{source} interface bridge type")
    extern_type_count = reader.count(f"{source} extern type")
    extern_types = tuple(reader.string(f"{source} extern type {index}") for index in range(extern_type_count))

    method_count = reader.count(f"{source} method")
    methods: list[MethodBody] = []
    for index in range(method_count):
        record_offset = reader.offset
        code_size = reader.count(f"{source} method {index} code")
        code_offset = reader.offset
        _, code_end, _ = reader.raw(code_size * 8, f"{source} method {index} instruction words")
        exception_count = reader.count(f"{source} method {index} exception")
        exception_offset = reader.offset
        _, end_offset, _ = reader.raw(exception_count * 24, f"{source} method {index} exception records")
        methods.append(
            MethodBody(
                index=index,
                record_offset=record_offset,
                code_size=code_size,
                code_offset=code_offset,
                code_end_offset=code_end,
                exception_count=exception_count,
                exception_offset=exception_offset,
                end_offset=end_offset,
                code_opaque=OpaqueRegion.make(f"method-{index}-instruction-words", data, code_offset, code_end),
                exception_opaque=OpaqueRegion.make(f"method-{index}-exception-records", data, exception_offset, end_offset),
            )
        )

    extern_method_count = reader.count(f"{source} extern method")
    extern_methods = tuple(
        _signature(reader, extern_type_count, f"{source} extern method {index}")
        for index in range(extern_method_count)
    )

    intern_string_count = reader.count(f"{source} intern string")
    intern_strings = tuple(reader.string(f"{source} intern string {index}") for index in range(intern_string_count))

    field_info_count = reader.count(f"{source} field info")
    field_infos: list[dict[str, Any]] = []
    for index in range(field_info_count):
        start = reader.offset
        is_new = reader.boolean(f"{source} field {index} is-new flag")
        declaring = reader.i32(f"{source} field {index} declaring type")
        _check_index(declaring, extern_type_count, f"{source} field {index} declaring type", source)
        name = reader.string(f"{source} field {index} name")
        field_type = method_id = None
        if is_new:
            field_type = reader.i32(f"{source} field {index} type")
            _check_index(field_type, extern_type_count, f"{source} field {index} type", source)
            method_id = reader.i32(f"{source} field {index} initializer method")
        field_infos.append({
            "index": index,
            "offset": start,
            "endOffset": reader.offset,
            "isNewField": is_new,
            "declaringTypeIndex": declaring,
            "name": name.to_dict(),
            "fieldTypeIndex": field_type,
            "initializerMethodId": method_id,
        })

    static_count = reader.count(f"{source} static field type")
    static_fields = []
    for index in range(static_count):
        start = reader.offset
        type_index = reader.i32(f"{source} static field {index} type")
        _check_index(type_index, extern_type_count, f"{source} static field {index} type", source)
        cctor_id = reader.i32(f"{source} static field {index} cctor")
        static_fields.append({"index": index, "offset": start, "endOffset": reader.offset, "typeIndex": type_index, "cctorMethodId": cctor_id})

    anonymous_count = reader.count(f"{source} anonymous storey")
    if anonymous_count:
        raise BinaryFormatError(
            f"{source}: anonymous storey table has {anonymous_count} rows; current framing reader "
            "does not guess its nested interface-slot layout"
        )

    wrappers_manager = reader.string(f"{source} wrappers manager implementation")
    assembly = reader.string(f"{source} assembly")

    fix_count = reader.count(f"{source} fix record")
    fixes: list[FixRecord] = []
    for index in range(fix_count):
        signature = _signature(reader, extern_type_count, f"{source} fix record {index} signature")
        fix_method_id = reader.i32(f"{source} fix record {index} method id")
        fixes.append(FixRecord(signature, fix_method_id, reader.offset))

    new_class_count = reader.count(f"{source} new class")
    new_classes = tuple(reader.string(f"{source} new class {index}") for index in range(new_class_count))
    if reader.offset != len(data):
        raise BinaryFormatError(
            f"{source}: trailing bytes [{reader.offset}, {len(data)}) ({len(data) - reader.offset} bytes)"
        )

    return {
        "format": "endfield-ifix-patch-bytes-v1",
        "source": source,
        "input": {"length": len(data), "sha256": _sha256(data), "md5": _md5(data)},
        "opaquePrefix": prefix.to_dict(),
        "magic": {"offset": magic_offset, "value": f"0x{magic:016x}"},
        "interfaceBridgeType": bridge.to_dict(),
        "externTypes": {"count": extern_type_count, "records": [item.to_dict() for item in extern_types]},
        "methods": {"count": method_count, "records": [item.to_dict() for item in methods]},
        "externMethods": {"count": extern_method_count, "records": [item.to_dict() for item in extern_methods]},
        "internStrings": {"count": intern_string_count, "records": [item.to_dict() for item in intern_strings]},
        "fieldInfos": {"count": field_info_count, "records": field_infos},
        "staticFieldTypes": {"count": static_count, "records": static_fields},
        "anonymousStoreyInfos": {"count": anonymous_count, "records": []},
        "wrappersManagerImplementation": wrappers_manager.to_dict(),
        "assembly": assembly.to_dict(),
        "fixRecords": {
            "count": fix_count,
            "records": [item.to_dict() for item in fixes],
            "activationStatus": "not-established-by-file-framing",
        },
        "newClasses": {"count": new_class_count, "records": [item.to_dict() for item in new_classes]},
        "consumedBytes": reader.offset,
        "status": "format_framed_bounded_opaque",
    }


def _sweep(paths: list[Path]) -> dict[str, Any]:
    rows = []
    for path in paths:
        data = path.read_bytes()
        row: dict[str, Any] = {
            "source": str(path),
            "input": {"length": len(data), "sha256": _sha256(data), "md5": _md5(data)},
        }
        try:
            row["status"] = "ok"
            row["parsed"] = parse_ifix_patch(data, source=str(path))
            row["consumedBytes"] = row["parsed"]["consumedBytes"]
        except (BinaryFormatError, OSError, ValueError) as exc:
            row["status"] = "failed"
            row["error"] = str(exc)[:500]
            row["consumedBytes"] = None
        rows.append(row)
    return {"format": "endfield-ifix-patch-sweep-v1", "files": rows, "fileCount": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = _sweep(args.input)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if all(item["status"] == "ok" for item in result["files"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
