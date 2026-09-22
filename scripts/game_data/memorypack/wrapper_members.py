"""Derive every generated ``*ForMemoryPack`` wrapper's serialized member order.

MemoryPack's generated wrapper for a type ``T`` carries one ``set___<name>__``
property setter per serialized member, and the selected build's readers consume
those members in that setter order, inherited wrapper first.  Reviewed contracts
already record that fact one wrapper at a time -- ``serializedMemberCount``,
``setterMethods``, ``selectedReadOrder`` -- because each was recovered by hand
from a disassembled ``Deserialize`` body.

This module derives the same fact in bulk from the installed build's metadata,
so a reader that reaches an unreviewed wrapper can name its members instead of
emitting positional kinds.  What it establishes is the *generated* member order
and each member's declared type; it does not prove a cursor, a width, or a
physical boundary, so a derived row is evidence tier ``direct`` and never
promotes a wrapper to ``exact``.  Use it to name what a reviewed reader already
walks, or to propose the shape of one that does not exist yet.

Two orders exist for the same wrapper and only one describes the wire:

* the runtime type's field declaration order (``generatedOwnFields`` in the
  reviewed contracts, from ``fields_for``), and
* the generated wrapper's setter order, which is what this module returns.

``verify_against_contracts`` re-derives every reviewed wrapper and reports the
agreement, so build drift or a wrong model shows up as a named disagreement
rather than as silently renamed fields.

Fails closed: a missing or unreadable installed build returns no rows and an
audit naming the gate that stopped it.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.repo_paths import REPO_ROOT as REPO


WRAPPER_SUFFIX = "ForMemoryPack"
# The generated property setter for serialized member ``name``.  The wrapper's
# own ``set____instance`` backing setter has no member and does not match.
SETTER_PATTERN = re.compile(r"^set___(?P<member>.+)__$")
LIST_PREFIX = "System.Collections.Generic.List`1<"
# Declared primitive names grouped by the width a reader consumes.  Everything
# absent here is an ``object`` whose extent only its own wrapper establishes.
PRIMITIVE_KINDS = {
    "bool": "bool",
    "byte": "scalar8", "sbyte": "scalar8",
    "short": "scalar16", "ushort": "scalar16", "char": "scalar16",
    "int": "scalar32", "uint": "scalar32",
    "long": "scalar64", "ulong": "scalar64",
    "float": "float32", "double": "float64",
    "string": "string",
}
# Byte width of each fixed-width kind.  A kind absent here is variable-length or
# an object, and only its own reader establishes an extent.
KIND_WIDTHS = {
    "bool": 1, "scalar8": 1, "scalar16": 2, "scalar32": 4, "scalar64": 8,
    "float32": 4, "float64": 8,
}
# An enum is written as its underlying type, which is the type of its generated
# ``value__`` field.  Most are int32, but this build has several that are not,
# so the width is resolved rather than assumed.
ENUM_UNDERLYING_FIELD = "value__"
# Every generated wrapper stores the value it wraps in exactly one field, whose
# name varies by generator vintage. Reading its declared type joins a wrapper to
# the type it wraps without matching on mangled names.
INSTANCE_FIELD_NAMES = ("__realInstance", "__instance", "___instance")
DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_wrapper_members.json"
# Chains deeper than this are a metadata cycle we refuse to walk, not a type.
MAX_PARENT_DEPTH = 32
# .NET ``TypeAttributes.Abstract``, as the metadata type flags carry it.
TYPE_ATTRIBUTE_ABSTRACT = 0x80
# The generated method a wrapper that deserializes itself declares.
DESERIALIZE_METHOD = "Deserialize"
# ``FieldAttributes.Static``, in the ``attrs`` halfword of an ``Il2CppType``.
FIELD_ATTRIBUTE_STATIC = 0x10
# The two pointers every IL2CPP object carries before its fields. A value
# type's recorded instance size is its boxed size, so the header comes off.
IL2CPP_OBJECT_HEADER = 0x10
VALUE_TYPE_BASE = "System.ValueType"


@dataclass(frozen=True)
class WrapperMember:
    """One serialized member of one generated wrapper."""

    name: str
    method_index: int
    declared_type: str | None
    kind: str
    declaring_wrapper: str
    underlying_kind: str | None = None
    width: int | None = None

    @property
    def fixed_width(self) -> bool:
        """Whether this member's size is fixed by its type alone."""
        return self.width is not None

    def row(self) -> dict[str, Any]:
        row = {
            "name": self.name,
            "methodIndex": self.method_index,
            "declaredType": self.declared_type,
            "kind": self.kind,
            "declaringWrapper": self.declaring_wrapper,
        }
        if self.underlying_kind is not None:
            row["underlyingKind"] = self.underlying_kind
        if self.width is not None:
            row["width"] = self.width
        return row


@dataclass(frozen=True)
class WrapperType:
    """One generated wrapper and the members its readers consume, in order."""

    type_definition: int
    name: str
    parent_type_definition: int | None
    parent_name: str | None
    own_members: tuple[WrapperMember, ...]
    inherited_members: tuple[WrapperMember, ...]
    wrapped_type: str | None = None
    #: Whether the type this wrapper holds is a struct rather than a class.
    wrapped_is_value_type: bool = False
    #: Whether the wrapper's type is abstract, from its metadata type flags.
    abstract: bool = False
    #: Whether the wrapper declares a ``Deserialize`` of its own.
    own_deserialize: bool = False

    @property
    def members(self) -> tuple[WrapperMember, ...]:
        return self.inherited_members + self.own_members

    @property
    def frames_as_raw_struct(self) -> bool:
        """Whether this wrapper's body is its members laid down with no header.

        MemoryPack writes an unmanaged struct as raw memory: no null marker and
        no member-count header, because neither has anywhere to live in a value
        that is copied byte for byte.  ``Beyond.Gameplay.Core.GameplayTag`` is
        the case the reviewed reader proves -- a struct holding one ``int``,
        which the frozen reader takes as four raw bytes -- and the settled
        ``AudioId`` formatter body is the same rule with no wrapper at all.
        A struct with a managed member is not raw, so every member must be
        fixed-width for this to hold.
        """
        return bool(
            self.wrapped_is_value_type
            and self.members
            and all(member.fixed_width for member in self.members)
        )

    @property
    def frames_as_union(self) -> bool:
        """Whether MemoryPack writes a tag before this wrapper's body.

        A generated wrapper that deserializes itself carries its own
        ``Deserialize`` and reads a member header; a union base has none,
        because its generated union formatter reads the tag and dispatches to
        the concrete subtype's formatter instead.  The two facts this combines
        are independent -- being abstract comes from the type flags, having a
        ``Deserialize`` from the method list -- and on the selected build they
        agree on all 910 wrappers that have a subclass, with no exception.

        Having a subclass is *not* the test, which is the error this replaces.
        ``BlackboardString`` has one and is concrete, and the reviewed
        ``paired_payload`` reads it as the plain three-member object its member
        list describes, with no tag.  The natively walked root union
        ``AbilityActionData`` is abstract and has no ``Deserialize``, so the
        one union whose tags are read out of the binary satisfies this test.
        """
        return self.abstract and not self.own_deserialize

    @property
    def serialized_member_count(self) -> int:
        return len(self.members)

    @property
    def fixed_width(self) -> int | None:
        """The record's byte width when every member's size is type-fixed.

        This is the width of the members alone. It does not include whatever
        header the wrapper's own formatter writes, so it is a lower bound on a
        record's extent, not a proven boundary.
        """
        if not self.members or not all(member.fixed_width for member in self.members):
            return None
        return sum(member.width or 0 for member in self.members)

    def row(self) -> dict[str, Any]:
        return {
            "typeDefinition": self.type_definition,
            "wrapperName": self.name,
            "parentTypeDefinition": self.parent_type_definition,
            "parentWrapperName": self.parent_name,
            "wrappedType": self.wrapped_type,
            "serializedMemberCount": self.serialized_member_count,
            "inheritedMemberCount": len(self.inherited_members),
            "memberOrder": [member.name for member in self.members],
            "memberWidthSum": self.fixed_width,
            "framesAsUnion": self.frames_as_union,
            "framesAsRawStruct": self.frames_as_raw_struct,
            "members": [member.row() for member in self.members],
        }


@dataclass
class _Deriver:
    """The selected build's tables, parsed once and shared by every lookup."""

    image: NativeImage
    enum_definitions: set[int] = field(default_factory=set)
    _wrappers: dict[int, Any] = field(default_factory=dict)
    _own: dict[int, tuple[WrapperMember, ...]] = field(default_factory=dict)
    _resolved: dict[int, WrapperType] = field(default_factory=dict)
    _enum_underlying_cache: dict[int, str | None] = field(default_factory=dict)

    # ---- runtime type table ------------------------------------------

    def _type_va(self, type_index: int) -> int | None:
        count = self.image.registration["typesCount"]
        if not 0 <= type_index < count:
            return None
        table = int(self.image.registration["types"], 16)
        return self.image.pe.u64_at_va(table + type_index * 8)

    def _type_definition_for(self, type_index: int) -> int | None:
        """The TypeDef a runtime class/valuetype type index names, if it is one."""
        type_va = self._type_va(type_index)
        if type_va is None:
            return None
        offset, _section, _rva = self.image.pe.file_offset_for_va(type_va)
        if offset is None:
            return None
        data = struct.unpack_from("<Q", self.image.pe.buf, offset)[0]
        # IL2CPP_TYPE_VALUETYPE / IL2CPP_TYPE_CLASS carry a TypeDef index.
        if self.image.pe.buf[offset + 10] not in (0x11, 0x12):
            return None
        return data if 0 <= data < len(self.image.metadata.types) else None

    def _declared_type_name(self, type_index: int) -> str | None:
        type_va = self._type_va(type_index)
        if type_va is None:
            return None
        try:
            return runtime_type_name(self.image.pe, self.image.metadata, type_va)
        except (OSError, ValueError, struct.error, RuntimeError):
            return None

    # ---- member kinds -------------------------------------------------

    def _wrapped_type(self, definition: int) -> str | None:
        """The declared type this wrapper's instance field holds."""
        metadata = self.image.metadata
        for field_def in metadata.fields_for(metadata.types[definition]):
            if metadata.string(field_def.name_index) in INSTANCE_FIELD_NAMES:
                return self._declared_type_name(field_def.type_index)
        return None

    def _wrapped_is_value_type(self, definition: int) -> bool:
        """Whether the type this wrapper holds is a struct.

        A struct is framed as raw memory, so this is what separates a wrapper
        whose member header is written from one whose members are simply laid
        down end to end.
        """
        metadata = self.image.metadata
        for field_def in metadata.fields_for(metadata.types[definition]):
            if metadata.string(field_def.name_index) not in INSTANCE_FIELD_NAMES:
                continue
            wrapped = self._type_definition_for(field_def.type_index)
            if wrapped is None:
                return False
            parent = self._type_definition_for(metadata.types[wrapped].parent_index)
            return parent is not None and metadata.type_full_name(
                metadata.types[parent]) == "System.ValueType"
        return False

    def _field_attributes(self, type_index: int) -> int | None:
        """The ``attrs`` halfword of the ``Il2CppType`` a field declares."""
        type_va = self._type_va(type_index)
        if type_va is None:
            return None
        offset, _section, _rva = self.image.pe.file_offset_for_va(type_va)
        if offset is None:
            return None
        return struct.unpack_from("<H", self.image.pe.buf, offset + 8)[0]

    def _enum_underlying(self, definition: int) -> str | None:
        """The primitive an enum is written as, from its ``value__`` field."""
        if definition in self._enum_underlying_cache:
            return self._enum_underlying_cache[definition]
        metadata = self.image.metadata
        resolved: str | None = None
        for field_def in metadata.fields_for(metadata.types[definition]):
            if metadata.string(field_def.name_index) == ENUM_UNDERLYING_FIELD:
                declared = self._declared_type_name(field_def.type_index)
                resolved = PRIMITIVE_KINDS.get(declared) if declared else None
                break
        self._enum_underlying_cache[definition] = resolved
        return resolved

    def _kind(self, type_index: int, declared: str | None) -> tuple[str, str | None, int | None]:
        """The wire shape a reader sees, its underlying kind, and its width.

        The shape names what the generated member is, not a proven boundary: an
        ``object`` member still needs its own wrapper walked to know its extent.
        A width is returned only for a kind whose size is fixed by its type.
        """
        if declared is None:
            return "unresolved", None, None
        definition = self._type_definition_for(type_index)
        if definition is not None and definition in self.enum_definitions:
            underlying = self._enum_underlying(definition)
            return "enum", underlying, KIND_WIDTHS.get(underlying or "")
        if declared.startswith(LIST_PREFIX):
            return "list", None, None
        if declared.endswith("[]"):
            return "array", None, None
        kind = PRIMITIVE_KINDS.get(declared, "object")
        return kind, None, KIND_WIDTHS.get(kind)

    # ---- wrapper walk --------------------------------------------------

    def index_wrappers(self) -> None:
        metadata = self.image.metadata
        for type_def in metadata.types:
            if metadata.type_name(type_def).endswith(WRAPPER_SUFFIX):
                self._wrappers[type_def.index] = type_def
        for type_def in metadata.types:
            parent = self._type_definition_for(type_def.parent_index)
            if parent is not None and metadata.type_full_name(metadata.types[parent]) == "System.Enum":
                self.enum_definitions.add(type_def.index)

    def _own_members(self, definition: int) -> tuple[WrapperMember, ...]:
        if definition in self._own:
            return self._own[definition]
        metadata = self.image.metadata
        wrapper_name = metadata.type_full_name(metadata.types[definition])
        rows: list[WrapperMember] = []
        for method in metadata.methods_for(metadata.types[definition]):
            match = SETTER_PATTERN.match(metadata.string(method.name_index))
            if match is None:
                continue
            parameters = metadata.parameters_for(method)
            type_index = parameters[0].type_index if len(parameters) == 1 else -1
            declared = self._declared_type_name(type_index) if type_index >= 0 else None
            kind, underlying, width = self._kind(type_index, declared)
            rows.append(
                WrapperMember(
                    name=match.group("member"),
                    method_index=method.index,
                    declared_type=declared,
                    kind=kind,
                    declaring_wrapper=wrapper_name,
                    underlying_kind=underlying,
                    width=width,
                )
            )
        # The generated reader consumes members in setter declaration order,
        # which the metadata preserves as ascending method index.
        ordered = tuple(sorted(rows, key=lambda member: member.method_index))
        self._own[definition] = ordered
        return ordered

    def resolve(self, definition: int) -> WrapperType | None:
        if definition in self._resolved:
            return self._resolved[definition]
        if definition not in self._wrappers:
            return None
        metadata = self.image.metadata
        type_def = metadata.types[definition]
        parent = self._type_definition_for(type_def.parent_index)
        inherited: tuple[WrapperMember, ...] = ()
        parent_name: str | None = None
        if parent is not None and parent in self._wrappers:
            parent_name = metadata.type_full_name(metadata.types[parent])
            chain = self._parent_chain(parent)
            if chain is None:
                return None
            inherited = chain
        resolved = WrapperType(
            type_definition=definition,
            name=metadata.type_full_name(type_def),
            parent_type_definition=parent if parent in self._wrappers else None,
            parent_name=parent_name,
            own_members=self._own_members(definition),
            inherited_members=inherited,
            wrapped_type=self._wrapped_type(definition),
            wrapped_is_value_type=self._wrapped_is_value_type(definition),
            abstract=bool(getattr(type_def, "flags", 0) & TYPE_ATTRIBUTE_ABSTRACT),
            own_deserialize=any(
                metadata.string(method.name_index) == DESERIALIZE_METHOD
                for method in metadata.methods_for(type_def)
            ),
        )
        self._resolved[definition] = resolved
        return resolved

    def _parent_chain(self, definition: int) -> tuple[WrapperMember, ...] | None:
        """Every ancestor wrapper's members, outermost ancestor first."""
        chain: list[int] = []
        seen: set[int] = set()
        current: int | None = definition
        while current is not None and current in self._wrappers:
            if current in seen or len(chain) >= MAX_PARENT_DEPTH:
                return None
            seen.add(current)
            chain.append(current)
            current = self._type_definition_for(self.image.metadata.types[current].parent_index)
        members: list[WrapperMember] = []
        for ancestor in reversed(chain):
            members.extend(self._own_members(ancestor))
        return tuple(members)

    def all_wrappers(self) -> Iterable[WrapperType]:
        for definition in sorted(self._wrappers):
            resolved = self.resolve(definition)
            if resolved is not None:
                yield resolved


def wrapped_type_index(rows: dict[int, WrapperType]) -> dict[str, int]:
    """Map each wrapped type name to the one wrapper that wraps it.

    A nested member declares the type it holds, not the generated wrapper that
    frames it, so this is the join a recursive reader needs. A name claimed by
    more than one wrapper is dropped rather than resolved arbitrarily: an
    ambiguous join is not an identity.
    """
    claims: dict[str, list[int]] = {}
    for definition, wrapper in rows.items():
        if wrapper.wrapped_type:
            claims.setdefault(wrapper.wrapped_type, []).append(definition)
    return {name: found[0] for name, found in claims.items() if len(found) == 1}


def derive_from_image(image: NativeImage) -> dict[int, WrapperType]:
    """Derive every wrapper from an already-parsed image.

    A caller that has built a ``NativeImage`` for its own gate reuses it here
    instead of parsing the metadata a second time.
    """
    deriver = _Deriver(image)
    deriver.index_wrappers()
    return {wrapper.type_definition: wrapper for wrapper in deriver.all_wrappers()}


def enum_widths_from_image(image: NativeImage) -> dict[str, int]:
    """Every enum's serialized width, keyed by full type name.

    An enum is written as its underlying type, which is the declared type of
    its ``value__`` field.  Deriving it for every enum definition -- not only
    for the enums some wrapper happens to declare as a direct member -- is what
    lets a member holding ``List<SomeEnum>`` or ``SomeEnum[]`` resolve: the
    element type appears nowhere in a member list, so an incidental scan of
    members cannot see it.
    """
    deriver = _Deriver(image)
    deriver.index_wrappers()
    metadata = image.metadata
    widths: dict[str, int] = {}
    for definition in sorted(deriver.enum_definitions):
        width = KIND_WIDTHS.get(deriver._enum_underlying(definition) or "")
        if width is not None:
            widths[metadata.type_full_name(metadata.types[definition])] = width
    return widths


def unmanaged_value_sizes_from_image(image: NativeImage) -> dict[str, int]:
    """Every blittable struct's size, keyed by full type name.

    MemoryPack writes an unmanaged struct as raw memory, so its serialized
    extent is its size in memory -- including the padding its field alignment
    introduces, which is why a summed member width is the wrong answer.
    ``CameraControlStateInitialParam`` is the case that proves it: four bools
    and three floats sum to 16, the struct is 24, and the reviewed reader takes
    24 raw bytes.

    The size is not computed here. It is read from the build's own
    ``Il2CppTypeDefinitionSizes`` table, whose ``instance_size`` is the boxed
    size, so the object header comes off. Five independent checks agree with
    it: ``GameplayTag`` 4 and ``CameraControlStateInitialParam`` 24 from the
    frozen reader's own raw takes, ``AudioId`` 4 from its formatter body's
    32-bit store, and ``Vector3`` 12 and ``Quaternion`` 16 from the widths that
    reader already consumes.

    Blittable is decided recursively and structurally: a value type qualifies
    when every non-static field it declares is a primitive other than
    ``string``, an enum, or another qualifying value type. A struct holding a
    managed field is not raw memory and is left out rather than sized.
    """
    deriver = _Deriver(image)
    deriver.index_wrappers()
    metadata, pe = image.metadata, image.pe
    table = int(image.registration["typeDefinitionsSizes"], 16)
    value_types = {
        type_def.index
        for type_def in metadata.types
        if (parent := deriver._type_definition_for(type_def.parent_index)) is not None
        and metadata.type_full_name(metadata.types[parent]) == VALUE_TYPE_BASE
    }

    def instance_fields(definition: int) -> list[Any]:
        rows = []
        for field_def in metadata.fields_for(metadata.types[definition]):
            attributes = deriver._field_attributes(field_def.type_index)
            if attributes is None or attributes & FIELD_ATTRIBUTE_STATIC:
                continue
            rows.append(field_def)
        return rows

    blittable: dict[int, bool] = {}

    def is_blittable(definition: int, stack: frozenset[int] = frozenset()) -> bool:
        if definition in blittable:
            return blittable[definition]
        if definition in stack or definition not in value_types:
            return False
        if definition in deriver.enum_definitions:
            blittable[definition] = True
            return True
        nested = stack | {definition}
        result = True
        for field_def in instance_fields(definition):
            declared = deriver._declared_type_name(field_def.type_index)
            kind = PRIMITIVE_KINDS.get(declared or "")
            if kind is not None and kind != "string":
                continue
            field_type = deriver._type_definition_for(field_def.type_index)
            if field_type is None or not is_blittable(field_type, nested):
                result = False
                break
        blittable[definition] = result
        return result

    sizes: dict[str, int] = {}
    for definition in sorted(value_types):
        if not is_blittable(definition):
            continue
        pointer = pe.u64_at_va(table + definition * 8)
        if not pointer:
            continue
        try:
            instance_size = struct.unpack_from("<I", pe.bytes_at_va(pointer, 4))[0]
        except (OSError, ValueError, struct.error):
            continue
        if instance_size > IL2CPP_OBJECT_HEADER:
            sizes[metadata.type_full_name(metadata.types[definition])] = (
                instance_size - IL2CPP_OBJECT_HEADER)
    return sizes


@dataclass(frozen=True)
class DerivedTables:
    """The type tables a plan resolver needs beside the wrappers.

    Neither is visible from a member list: an enum reached only as a list
    element is declared by no member, and a struct's serialized extent is its
    aligned size rather than its members' summed widths.
    """

    enum_widths: dict[str, int]
    value_sizes: dict[str, int]


def load_derived_tables(
    *, gameassembly: Path | None = None, metadata: Path | None = None
) -> tuple[dict[int, WrapperType], DerivedTables, dict[str, Any]]:
    """Every wrapper and both type tables from one parse of the installed build.

    A caller needing them takes them here rather than gating three times; the
    metadata walk that finds the wrappers already classifies the enums and the
    value types.
    """
    tables = DerivedTables({}, {})
    rows, audit = load_wrapper_members(
        gameassembly=gameassembly, metadata=metadata, _tables=tables
    )
    return rows, tables, audit


def load_wrapper_members(
    *, gameassembly: Path | None = None, metadata: Path | None = None,
    _tables: "DerivedTables | None" = None,
) -> tuple[dict[int, WrapperType], dict[str, Any]]:
    """Return ``{typeDefinition: WrapperType}`` for the installed build.

    The gate carries no expected hashes because the derivation describes
    whichever build is installed; the measured hashes are recorded so a
    consumer can pin what it read.  ``_tables`` is filled in place for
    ``load_derived_tables``, which needs the type tables off the same parse.
    """
    audit: dict[str, Any] = {"status": "derivation_failed", "failures": []}
    try:
        gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
        audit["nativeGate"] = {"status": gate.status, "detail": gate.detail}
        if gate.status != "validated":
            audit["failures"].append({
                "gate": "installed_native_inputs",
                "expected": "validated",
                "actual": gate.status,
                "detail": gate.detail,
            })
            audit["status"] = gate.status
            return {}, audit
        audit["nativeInputs"] = {
            "GameAssembly.dll": gate.gameassembly_sha256,
            "global-metadata.dat": gate.metadata_sha256,
        }
        image = NativeImage(gate.gameassembly, gate.metadata, label="wrapperMembers")
        rows = derive_from_image(image)
        if _tables is not None:
            _tables.enum_widths.update(enum_widths_from_image(image))
            _tables.value_sizes.update(unmanaged_value_sizes_from_image(image))
        audit.update(
            status="validated",
            wrapperCount=len(rows),
            wrappersWithMembers=sum(1 for row in rows.values() if row.members),
            evidenceBoundary={
                "direct": (
                    "The selected build's generated wrapper setters name each serialized "
                    "member and their metadata order is the generated read order, inherited "
                    "wrapper members first."
                ),
                "structuralOnly": (
                    "Member kinds group declared types; no cursor, serialized width, nested "
                    "extent, enum value or runtime meaning is established."
                ),
            },
        )
        return rows, audit
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        audit["failures"].append({"gate": "wrapper_derivation", "detail": str(error)})
        return {}, audit


def _contract_wrappers(value: Any) -> Iterable[dict[str, Any]]:
    """Every reviewed block that names a wrapper type definition."""
    if isinstance(value, dict):
        definition = value.get("wrapperTypeDefinition", value.get("typeDefinition"))
        if isinstance(definition, int):
            yield value
        for nested in value.values():
            yield from _contract_wrappers(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _contract_wrappers(nested)


def verify_against_contracts(
    rows: dict[int, WrapperType], contracts: Iterable[Path]
) -> dict[str, Any]:
    """Re-derive every reviewed wrapper and report where the two disagree.

    Only facts a contract actually records are checked: its serialized member
    count and, where present, the member names its ``setterMethods`` list.  A
    contract's ``generatedOwnFields`` is the runtime type's field declaration
    order, which is a different fact, so it is reported beside the derived order
    rather than compared against it.
    """
    checks = {"countChecked": 0, "countAgreed": 0, "namesChecked": 0, "namesAgreed": 0}
    disagreements: list[dict[str, Any]] = []
    declaration_order_differs = 0
    for path in sorted(contracts):
        try:
            value = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        source = path.relative_to(REPO).as_posix()
        for block in _contract_wrappers(value):
            definition = block.get("wrapperTypeDefinition", block.get("typeDefinition"))
            derived = rows.get(definition)
            if derived is None:
                continue
            recorded_count = block.get("serializedMemberCount")
            if isinstance(recorded_count, int):
                checks["countChecked"] += 1
                if recorded_count == derived.serialized_member_count:
                    checks["countAgreed"] += 1
                else:
                    disagreements.append({
                        "contract": source, "wrapperName": derived.name, "check": "serializedMemberCount",
                        "recorded": recorded_count, "derived": derived.serialized_member_count,
                    })
            recorded_names = [
                match.group("member")
                for row in block.get("setterMethods") or []
                if isinstance(row, (list, tuple)) and len(row) > 1
                for match in [SETTER_PATTERN.match(str(row[1]))]
                if match is not None
            ]
            if recorded_names:
                derived_own = [member.name for member in derived.own_members]
                checks["namesChecked"] += 1
                if recorded_names == derived_own:
                    checks["namesAgreed"] += 1
                else:
                    disagreements.append({
                        "contract": source, "wrapperName": derived.name, "check": "setterMemberOrder",
                        "recorded": recorded_names, "derived": derived_own,
                    })
            declared = block.get("generatedOwnFields")
            if declared and list(declared) != [member.name for member in derived.own_members]:
                declaration_order_differs += 1
    return {
        **checks,
        "declarationOrderDiffers": declaration_order_differs,
        "disagreements": disagreements,
        "note": (
            "declarationOrderDiffers counts reviewed wrappers whose runtime field "
            "declaration order is not the generated setter order; those are two "
            "different facts and only the setter order describes the wire."
        ),
    }


def build(output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    rows, audit = load_wrapper_members()
    contracts = sorted((REPO / "scripts/game_data/contracts").glob("*.json"))
    verification = verify_against_contracts(rows, contracts) if rows else {}
    report = {
        "schema": "endfield.memorypack-wrapper-members.v1",
        "audit": audit,
        "contractVerification": verification,
        "summary": {
            "status": audit["status"],
            "wrappers": len(rows),
            "wrappersWithMembers": sum(1 for row in rows.values() if row.members),
            "countAgreed": verification.get("countAgreed"),
            "countChecked": verification.get("countChecked"),
            "namesAgreed": verification.get("namesAgreed"),
            "namesChecked": verification.get("namesChecked"),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "wrappers": [rows[definition].row() for definition in sorted(rows)],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--wrapper", action="append", default=[],
                        help="print one wrapper's derived member order instead of writing a report")
    args = parser.parse_args()
    if args.wrapper:
        rows, audit = load_wrapper_members()
        if audit["status"] != "validated":
            print(json.dumps(audit, ensure_ascii=False), file=sys.stderr)
            return 1
        by_name = {row.name: row for row in rows.values()}
        for wanted in args.wrapper:
            matched = [name for name in by_name if name.endswith(wanted) or name == wanted]
            if not matched:
                print(json.dumps({"wrapper": wanted, "status": "not-found"}), file=sys.stderr)
                return 1
            for name in sorted(matched):
                print(json.dumps(by_name[name].row(), ensure_ascii=False, sort_keys=False))
        return 0
    try:
        report = build(args.output)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
