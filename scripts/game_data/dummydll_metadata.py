"""Read ECMA-335 metadata out of the IL2CPP DummyDll set, stdlib only.

`tools/DummyDll` holds the Cpp2IL-regenerated managed image of one installed
build.  Its MemoryPack wrapper classes carry two facts that no exported byte
stream states: the *declaration order* of a serialized type's members, and the
declared type of each one.  MemoryPack writes members in that order, so a
wrapper's ordered setter list is the wire layout of the payload it wraps.

This module is the reader for that.  It is deliberately narrow: it parses only
the tables needed to walk TypeDef -> base chain -> MethodDef setters and to
decode a setter's parameter signature.  It does not execute IL, read method
bodies, or attempt a general-purpose disassembler.

It reads whatever DummyDll set it is pointed at, so it carries no build-locked
constant.  A caller that turns its output into a schema claim must gate on the
installed native inputs itself; see
`scripts.game_data.levelscript_union_layouts` for the reviewed example.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any, Iterator

from scripts.repo_paths import REPO_ROOT

DEFAULT_DUMMYDLL_ROOT = REPO_ROOT / "tools" / "DummyDll"

# Table ids this reader understands.  Offsets are accumulated only across
# tables it can size, so an unmodelled later table cannot silently shift one.
T_MODULE, T_TYPEREF, T_TYPEDEF = 0x00, 0x01, 0x02
T_FIELD, T_METHODDEF, T_PARAM = 0x04, 0x06, 0x08
T_INTERFACEIMPL, T_STANDALONESIG = 0x09, 0x11
T_PROPERTYMAP, T_PROPERTY, T_METHODSEMANTICS = 0x15, 0x17, 0x18
T_TYPESPEC, T_NESTEDCLASS = 0x1B, 0x29

#: ECMA-335 II.23.1.5 FieldAttributes bits this reader filters on. Neither a
#: static nor a literal field occupies space in an instance.
TYPE_ABSTRACT = 0x00000080
FIELD_STATIC = 0x0010
FIELD_LITERAL = 0x0040

RESOLUTION_SCOPE = (0x00, 0x1A, 0x23, 0x01)
TYPE_DEF_OR_REF = (0x02, 0x01, 0x1B)
HAS_SEMANTICS = (0x14, 0x17)

# ECMA-335 II.23.1.16 element types that need no further resolution.
PRIMITIVE_ELEMENT_TYPES = {
    0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "int8", 0x05: "uint8",
    0x06: "int16", 0x07: "uint16", 0x08: "int32", 0x09: "uint32",
    0x0A: "int64", 0x0B: "uint64", 0x0C: "float", 0x0D: "double",
    0x0E: "string", 0x18: "IntPtr", 0x19: "UIntPtr", 0x1C: "object",
}


class DummyDllMetadataError(ValueError):
    """The image is not a managed assembly this reader can walk."""


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _uncompress(blob: bytes, pos: int) -> tuple[int, int]:
    """Read one ECMA-335 compressed unsigned integer."""

    head = blob[pos]
    if not head & 0x80:
        return head, pos + 1
    if head & 0xC0 == 0x80:
        return ((head & 0x3F) << 8) | blob[pos + 1], pos + 2
    return (
        ((head & 0x1F) << 24)
        | (blob[pos + 1] << 16)
        | (blob[pos + 2] << 8)
        | blob[pos + 3]
    ), pos + 4


class CliMetadata:
    """One managed image: heaps, table offsets, and the walks built on them."""

    def __init__(self, data: bytes, *, name: str = "<memory>") -> None:
        self.data = data
        self.name = name
        self._read_metadata_root(self._metadata_offset())
        self._read_table_header()
        self._size_tables()

    # -- PE / metadata plumbing -------------------------------------------

    def _metadata_offset(self) -> int:
        data = self.data
        if data[:2] != b"MZ":
            raise DummyDllMetadataError(f"{self.name}: not a PE image")
        pe = _u32(data, 0x3C)
        if data[pe : pe + 4] != b"PE\0\0":
            raise DummyDllMetadataError(f"{self.name}: bad PE signature")
        coff = pe + 4
        section_count = _u16(data, coff + 2)
        optional_size = _u16(data, coff + 16)
        optional = coff + 20
        magic = _u16(data, optional)
        directories = optional + (96 if magic == 0x10B else 112)
        sections = []
        table = optional + optional_size
        for index in range(section_count):
            row = table + index * 40
            sections.append((
                _u32(data, row + 12), _u32(data, row + 8),
                _u32(data, row + 20), _u32(data, row + 16),
            ))

        def to_offset(rva: int) -> int:
            for virtual, virtual_size, raw, raw_size in sections:
                if virtual <= rva < virtual + max(virtual_size, raw_size):
                    return raw + (rva - virtual)
            raise DummyDllMetadataError(f"{self.name}: RVA {rva:#x} is unmapped")

        cli_header = to_offset(_u32(data, directories + 14 * 8))
        return to_offset(_u32(data, cli_header + 8))

    def _read_metadata_root(self, offset: int) -> None:
        data = self.data
        if data[offset : offset + 4] != b"BSJB":
            raise DummyDllMetadataError(f"{self.name}: bad metadata signature")
        pos = offset + 16 + _u32(data, offset + 12) + 2
        stream_count = _u16(data, pos)
        pos += 2
        self.streams: dict[str, tuple[int, int]] = {}
        for _ in range(stream_count):
            start, size = _u32(data, pos), _u32(data, pos + 4)
            pos += 8
            end = data.index(b"\0", pos)
            self.streams[data[pos:end].decode("ascii")] = (offset + start, size)
            pos = ((end + 1 + 3) // 4) * 4
        for required in ("#Strings", "#Blob"):
            if required not in self.streams:
                raise DummyDllMetadataError(f"{self.name}: missing {required} heap")

    def _read_table_header(self) -> None:
        stream = self.streams.get("#~") or self.streams.get("#-")
        if stream is None:
            raise DummyDllMetadataError(f"{self.name}: missing table stream")
        offset = stream[0]
        heap_sizes = self.data[offset + 6]
        self.string_width = 4 if heap_sizes & 1 else 2
        self.guid_width = 4 if heap_sizes & 2 else 2
        self.blob_width = 4 if heap_sizes & 4 else 2
        valid = struct.unpack_from("<Q", self.data, offset + 8)[0]
        pos = offset + 24
        self.rows: dict[int, int] = {}
        for table in range(64):
            if valid >> table & 1:
                self.rows[table] = _u32(self.data, pos)
                pos += 4
        self._rows_start = pos

    def _index_width(self, table: int) -> int:
        return 4 if self.rows.get(table, 0) >= (1 << 16) else 2

    def _coded_width(self, tables: tuple[int, ...], bits: int) -> int:
        limit = 1 << (16 - bits)
        return 4 if any(self.rows.get(t, 0) >= limit for t in tables) else 2

    def _size_tables(self) -> None:
        """Size every ECMA-335 table, because offsets accumulate in order.

        A table this reader never queries still sits between two it does, so
        an unmodelled one would silently shift every later offset. Sizing all
        of them is what makes an offset trustworthy rather than lucky.
        """

        s, g, b = self.string_width, self.guid_width, self.blob_width
        index, coded = self._index_width, self._coded_width
        type_ref = coded(TYPE_DEF_OR_REF, 2)
        has_constant = coded((0x04, 0x08, 0x17), 2)
        has_custom = coded((
            0x06, 0x04, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x00, 0x0E, 0x17, 0x14,
            0x11, 0x1A, 0x1B, 0x20, 0x23, 0x26, 0x27, 0x28, 0x2A, 0x2C,
        ), 5)
        has_marshal = coded((0x04, 0x08), 1)
        has_security = coded((0x02, 0x06, 0x20), 2)
        member_ref_parent = coded((0x02, 0x01, 0x1A, 0x06, 0x1B), 3)
        has_semantics = coded(HAS_SEMANTICS, 1)
        method_def_or_ref = coded((0x06, 0x0A), 1)
        member_forwarded = coded((0x04, 0x06), 1)
        implementation = coded((0x26, 0x23, 0x27), 2)
        custom_attr_type = coded((0x06, 0x0A), 3)
        scope = coded(RESOLUTION_SCOPE, 2)
        type_or_method = coded((0x02, 0x06), 1)
        self.row_size = {
            0x00: 2 + s + 3 * g,
            0x01: scope + s + s,
            0x02: 4 + s + s + type_ref + index(0x04) + index(0x06),
            0x03: index(0x04),
            0x04: 2 + s + b,
            0x05: index(0x06),
            0x06: 4 + 2 + 2 + s + b + index(0x08),
            0x07: index(0x08),
            0x08: 2 + 2 + s,
            0x09: index(0x02) + type_ref,
            0x0A: member_ref_parent + s + b,
            0x0B: 1 + 1 + has_constant + b,
            0x0C: has_custom + custom_attr_type + b,
            0x0D: has_marshal + b,
            0x0E: 2 + has_security + b,
            0x0F: 2 + 4 + index(0x02),
            0x10: 4 + index(0x04),
            0x11: b,
            0x12: index(0x02) + index(0x14),
            0x13: index(0x14),
            0x14: 2 + s + type_ref,
            0x15: index(0x02) + index(0x17),
            0x16: index(0x17),
            0x17: 2 + s + b,
            0x18: 2 + index(0x06) + has_semantics,
            0x19: index(0x02) + method_def_or_ref + method_def_or_ref,
            0x1A: s,
            0x1B: b,
            0x1C: 2 + member_forwarded + s + index(0x1A),
            0x1D: 4 + index(0x04),
            0x1E: 4 + 4,
            0x1F: 4,
            0x20: 4 + 2 * 4 + 4 + b + s + s,
            0x21: 4,
            0x22: 4 + 4 + 4,
            0x23: 2 * 4 + 4 + b + s + s + b,
            0x24: 4 + index(0x23),
            0x25: 4 + 4 + 4 + index(0x23),
            0x26: 4 + s + b,
            0x27: 4 + 4 + s + s + implementation,
            0x28: 4 + 4 + s + implementation,
            0x29: index(0x02) + index(0x02),
            0x2A: 2 + 2 + type_or_method + s,
            0x2B: method_def_or_ref + b,
            0x2C: index(0x2A) + type_ref,
        }
        pos = self._rows_start
        self.table_offset: dict[int, int] = {}
        for table in sorted(self.rows):
            if table not in self.row_size:
                raise DummyDllMetadataError(
                    f"{self.name}: unmodelled metadata table {table:#04x}"
                )
            self.table_offset[table] = pos
            pos += self.row_size[table] * self.rows[table]

    def _require(self, table: int) -> None:
        if self.rows.get(table) and table not in self.table_offset:
            raise DummyDllMetadataError(
                f"{self.name}: table {table:#04x} has rows but no offset"
            )

    def _cell(self, table: int, row: int, field_offset: int, width: int) -> int:
        base = self.table_offset[table] + row * self.row_size[table] + field_offset
        return _u32(self.data, base) if width == 4 else _u16(self.data, base)

    # -- heaps -------------------------------------------------------------

    def string(self, index: int) -> str:
        start = self.streams["#Strings"][0] + index
        end = self.data.index(b"\0", start)
        return self.data[start:end].decode("utf-8", "replace")

    def blob(self, index: int) -> bytes:
        pos = self.streams["#Blob"][0] + index
        length, pos = _uncompress(self.data, pos)
        return self.data[pos : pos + length]

    # -- tables ------------------------------------------------------------

    def _field_rows(self) -> list[tuple[str, int, int]]:
        """``(name, signatureBlobIndex, flags)`` for every Field, in order."""

        cached = getattr(self, "_field_row_cache", None)
        if cached is None:
            self._require(T_FIELD)
            width = self.string_width
            cached = [(
                self.string(self._cell(T_FIELD, row, 2, width)),
                self._cell(T_FIELD, row, 2 + width, self.blob_width),
                self._cell(T_FIELD, row, 0, 2),
            ) for row in range(self.rows.get(T_FIELD, 0))]
            self._field_row_cache = cached
        return cached

    def fields(self, type_row: int) -> list[tuple[str, str]]:
        """Instance ``(name, declaredType)`` in declaration order.

        Static and literal fields are excluded. They occupy no space in an
        instance, so counting them inflates a struct's size and can make a
        type holding a static reference look reference-bearing --
        `GameplayTag` declares a `string[]` constant and is otherwise a bare
        int32.
        """

        rows = self._field_rows()
        out = []
        for row in self.type_defs()[type_row]["fieldRows"]:
            name, signature, flags = rows[row]
            if flags & (FIELD_STATIC | FIELD_LITERAL):
                continue
            blob = self.blob(signature)
            # FieldSig is the 0x06 calling convention followed by one Type.
            out.append((name, self.decode_type(blob, 1)[0] if blob[:1] == b"\x06" else "?"))
        return out

    def enum_underlying_type(self, type_row: int) -> str | None:
        """An enum's storage type, read from its ``value__`` instance field.

        An enum is written as its underlying type, and that is not always
        int32: the reviewed LevelScript wrappers include byte-backed enums.
        Assuming int32 would silently mis-size those members, so the width is
        read rather than defaulted.
        """

        for name, declared in self.fields(type_row):
            if name == "value__":
                return declared
        return None

    def _method_names(self) -> list[str]:
        cached = getattr(self, "_method_name_cache", None)
        if cached is None:
            self._require(T_METHODDEF)
            width = self.string_width
            cached = [
                self.string(self._cell(T_METHODDEF, row, 8, width))
                for row in range(self.rows.get(T_METHODDEF, 0))
            ]
            self._method_name_cache = cached
        return cached

    def method_signature_blob(self, row: int) -> bytes:
        offset = 4 + 2 + 2 + self.string_width
        return self.blob(self._cell(T_METHODDEF, row, offset, self.blob_width))

    def type_refs(self) -> list[tuple[str, str, int]]:
        """``(name, namespace, resolutionScopeCode)`` for every TypeRef."""

        cached = getattr(self, "_type_ref_cache", None)
        if cached is None:
            self._require(T_TYPEREF)
            scope = self._coded_width(RESOLUTION_SCOPE, 2)
            width = self.string_width
            cached = [(
                self.string(self._cell(T_TYPEREF, row, scope, width)),
                self.string(self._cell(T_TYPEREF, row, scope + width, width)),
                self._cell(T_TYPEREF, row, 0, scope),
            ) for row in range(self.rows.get(T_TYPEREF, 0))]
            self._type_ref_cache = cached
        return cached

    def type_ref_full_name(self, row: int) -> str:
        """A TypeRef's name, prefixed by its declaring types when nested.

        A nested type's ResolutionScope is the TypeRef of the type that
        declares it, so the enclosing name is read off the table rather than
        guessed from a short name that other assemblies also use.
        """

        refs = self.type_refs()
        parts: list[str] = []
        seen: set[int] = set()
        current = row
        while 0 <= current < len(refs) and current not in seen:
            seen.add(current)
            name, _namespace, scope = refs[current]
            parts.append(name.split("`")[0])
            if scope & 3 != 3:  # not ResolutionScope=TypeRef, so not nested
                break
            current = (scope >> 2) - 1
        return ".".join(reversed(parts))

    def type_def_full_name(self, row: int) -> str:
        """A TypeDef's name, prefixed by its declaring types when nested."""

        type_defs = self.type_defs()
        nested = self.nested_parents()
        parts: list[str] = []
        seen: set[int] = set()
        current = row
        while 0 <= current < len(type_defs) and current not in seen:
            seen.add(current)
            parts.append(type_defs[current]["name"].split("`")[0])
            parent = nested.get(current)
            if parent is None:
                break
            current = parent
        return ".".join(reversed(parts))

    def type_defs(self) -> list[dict[str, Any]]:
        """Every TypeDef with its base-class code and its method row range."""

        cached = getattr(self, "_type_def_cache", None)
        if cached is not None:
            return cached
        self._require(T_TYPEDEF)
        width = self.string_width
        type_ref = self._coded_width(TYPE_DEF_OR_REF, 2)
        method_width = self._index_width(T_METHODDEF)
        field_width = self._index_width(T_FIELD)
        field_list = 4 + width + width + type_ref
        method_list = field_list + field_width
        names = self._method_names()
        field_count = self.rows.get(T_FIELD, 0)
        total = self.rows.get(T_TYPEDEF, 0)
        rows: list[dict[str, Any]] = []
        for row in range(total):
            start = self._cell(T_TYPEDEF, row, method_list, method_width)
            field_start = self._cell(T_TYPEDEF, row, field_list, field_width)
            if row + 1 < total:
                end = self._cell(T_TYPEDEF, row + 1, method_list, method_width)
                field_end = self._cell(T_TYPEDEF, row + 1, field_list, field_width)
            else:
                end, field_end = len(names) + 1, field_count + 1
            rows.append({
                "row": row,
                "name": self.string(self._cell(T_TYPEDEF, row, 4, width)),
                "namespace": self.string(self._cell(T_TYPEDEF, row, 4 + width, width)),
                "extendsCode": self._cell(T_TYPEDEF, row, 4 + width + width, type_ref),
                "fieldRows": range(max(field_start - 1, 0), min(field_end - 1, field_count)),
                "methodRows": range(max(start - 1, 0), min(end - 1, len(names))),
            })
        self._type_def_cache = rows
        return rows

    def is_abstract(self, type_row: int) -> bool:
        """Whether the TypeDef carries the abstract flag."""

        return bool(self._cell(T_TYPEDEF, type_row, 0, 4) & TYPE_ABSTRACT)

    def type_layout(self, type_row: int) -> str:
        """`auto`, `sequential` or `explicit`, from the TypeDef layout bits."""

        flags = self._cell(T_TYPEDEF, type_row, 0, 4)
        return {0x00: "auto", 0x08: "sequential", 0x10: "explicit"}.get(
            flags & 0x18, "unknown"
        )

    def nested_parents(self) -> dict[int, int]:
        """Nested TypeDef row -> enclosing TypeDef row, both zero-based."""

        cached = getattr(self, "_nested_cache", None)
        if cached is None:
            cached = {}
            if self.rows.get(T_NESTEDCLASS) and T_NESTEDCLASS in self.table_offset:
                width = self._index_width(T_TYPEDEF)
                for row in range(self.rows[T_NESTEDCLASS]):
                    nested = self._cell(T_NESTEDCLASS, row, 0, width)
                    enclosing = self._cell(T_NESTEDCLASS, row, width, width)
                    if nested and enclosing:
                        cached[nested - 1] = enclosing - 1
            self._nested_cache = cached
        return cached

    def setters(self, type_row: int) -> list[tuple[int, str]]:
        """``(methodRow, setterName)`` in declaration order for one TypeDef."""

        names = self._method_names()
        return [
            (row, names[row])
            for row in self.type_defs()[type_row]["methodRows"]
            if names[row].startswith("set_")
        ]

    # -- signatures ---------------------------------------------------------

    def type_spec_name(self, row: int) -> str:
        return self.decode_type(
            self.blob(self._cell(T_TYPESPEC, row, 0, self.blob_width)), 0
        )[0]

    def type_def_or_ref_name(self, code: int) -> str:
        tag, row = code & 3, code >> 2
        if row == 0:
            return "?"
        if tag == 0:
            return self.type_def_full_name(row - 1)
        if tag == 1:
            return self.type_ref_full_name(row - 1)
        return self.type_spec_name(row - 1)

    def decode_type(self, blob: bytes, pos: int) -> tuple[str, int]:
        """Decode one ECMA-335 Type from a signature blob."""

        element = blob[pos]
        pos += 1
        if element in PRIMITIVE_ELEMENT_TYPES:
            return PRIMITIVE_ELEMENT_TYPES[element], pos
        if element in (0x11, 0x12):  # VALUETYPE, CLASS
            code, pos = _uncompress(blob, pos)
            return self.type_def_or_ref_name(code), pos
        if element == 0x1D:  # SZARRAY
            inner, pos = self.decode_type(blob, pos)
            return inner + "[]", pos
        if element == 0x14:  # ARRAY
            inner, pos = self.decode_type(blob, pos)
            rank, pos = _uncompress(blob, pos)
            for _ in range(2):
                count, pos = _uncompress(blob, pos)
                for _ in range(count):
                    _, pos = _uncompress(blob, pos)
            return f"{inner}[{',' * max(rank - 1, 0)}]", pos
        if element == 0x15:  # GENERICINST
            base, pos = self.decode_type(blob, pos)
            count, pos = _uncompress(blob, pos)
            args = []
            for _ in range(count):
                argument, pos = self.decode_type(blob, pos)
                args.append(argument)
            return f"{base}<{','.join(args)}>", pos
        if element in (0x0F, 0x10, 0x45):  # PTR, BYREF, PINNED
            return self.decode_type(blob, pos)
        if element in (0x13, 0x1E):  # VAR, MVAR
            index, pos = _uncompress(blob, pos)
            return f"!{index}", pos
        if element in (0x1F, 0x20):  # CMOD_REQD, CMOD_OPT
            _, pos = _uncompress(blob, pos)
            return self.decode_type(blob, pos)
        raise DummyDllMetadataError(
            f"{self.name}: unsupported signature element {element:#04x}"
        )

    def setter_parameter_type(self, method_row: int) -> str | None:
        """The declared type of a one-argument setter, or ``None``."""

        blob = self.method_signature_blob(method_row)
        pos = 1
        if blob[0] & 0x10:  # GENERIC: skip the generic parameter count
            _, pos = _uncompress(blob, pos)
        count, pos = _uncompress(blob, pos)
        if count < 1:
            return None
        _, pos = self.decode_type(blob, pos)  # return type
        return self.decode_type(blob, pos)[0]


def iter_assemblies(root: Path = DEFAULT_DUMMYDLL_ROOT) -> Iterator[Path]:
    """Every ``*.dll`` in a DummyDll set, in a stable order."""

    directory = Path(root)
    if not directory.is_dir():
        raise DummyDllMetadataError(f"DummyDll root not found: {directory}")
    return iter(sorted(directory.glob("*.dll")))


def load(path: Path) -> CliMetadata:
    """Parse one assembly off disk."""

    return CliMetadata(Path(path).read_bytes(), name=Path(path).name)
