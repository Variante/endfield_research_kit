"""Check reviewed claims about named method bodies against the selected build.

A reviewed native contract used to pin each method by token, address and body
hash, with its meaning written in prose. Only the names survive a client
update, so every build failed the pin even when the method still did the same
thing. This module states the meaning as checkable claims about a method named
by type and method, and evaluates them against whichever build is installed:

``calls``             the body calls (or tail-jumps to) each named method, directly,
                      through a split-off ``.pdata`` fragment it jumps to, or through
                      one unnamed helper; ``ordered`` requires first-call order
``comparesResult``    a named call's return value (through register moves) is compared
                      with a value, as an immediate or a register loaded with it
``matches``           some instruction (fragments included) fully matches a regex
``notCallsPrefix``    no direct or one-helper-deep callee name starts with the prefix
``returnsConstant``   some path returns the immediate value in ``eax``
``returnsEnumMember`` the immediate return matches a named member in the
                      selected build's native enum
``returnsArgument``   some path returns the named argument register unchanged
``storesConstant``    writes an immediate into a named field of ``this``
``readsField``        reads a named field (any base register)
``writesField``       writes a named field (any base register, including SSE stores)
``readsNestedField``  reads a named field through a previously loaded parent field
``passesFieldToCall`` loads a named field into a named register at a named call
``passesArgumentToCall`` a named incoming argument reaches a named callee
                      parameter through register copies
``passesEnumMemberToCall`` a selected enum member reaches a named callee
                      register parameter through constant and register moves
``callsAnonymousHelper`` a named caller reaches one unnamed native body whose
                      owned fragments contain selected calls and instructions;
                      caller parameters or constants can be checked at the call
``passesOutParameterToCall`` a named out-parameter slot is read back and passed
                      to a named later call
``passesNestedFieldToCall`` a named child field read through a named parent
                      reaches a named callee stack parameter
``forwardsStackParameter`` a named incoming stack parameter reaches a named
                      callee stack parameter
``loadsLiterals``     loads each named string literal through an IL2CPP usage cell
``loadsFloat32``      loads the named Single constant through a RIP-relative MOVSS
``zeroArgumentAt``    a named call receives zero in the given argument register
``branchesOnSign``    compares a named field with zero and branches on less-than
``storesArgument``    writes an argument register (through register moves) into a
                      named field of any object
``bindsLiteralToCallback`` a selected IL2CPP Action<T> callback and string-key
                      usage feed the same typed _TryAssign call
``dispatchesVirtualMethod`` an instance-data field and property blackboard
                      reach the selected native virtual slot, whose base and
                      named overrides all declare the same method
``comparesWithArguments`` compares one value with each named argument register
                      (through register moves), and with zero when ``zero`` is set

A method with several overloads is selected by its ``parameters`` type names.
``classArguments`` selects a concrete generic class instantiation when several
instantiations share the same method name.

Field offsets come from the selected build's MetadataRegistration, so no claim
carries an offset, token, address or hash. A claim that fails is a reviewed
meaning that no longer holds on this build; its consumer must not publish it.
"""
from __future__ import annotations

import hashlib
import re
import struct
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Iterable

from scripts.game_data.il2cpp import protocol as il2cpp
from scripts.game_data.il2cpp.call_graph import CallGraph, loaded_literals
from scripts.game_data.il2cpp.native_image import NativeImage

#: A helper or fragment larger than this is a method in its own right.
MAX_FOLLOWED_BYTES = 0x800
_JUMP = re.compile(r"(?:jmp|jcc|j[a-z]{1,3}) 0x([0-9a-f]+)$")
_CALL = re.compile(r"(call|jmp) 0x([0-9a-f]+)$")
_NEAR_CONDITION = {0x8C: "jl", 0x88: "js", 0x84: "je", 0x85: "jne"}


class ClaimError(RuntimeError):
    """A named method is missing or ambiguous in the selected build."""


@dataclass
class Body:
    symbol: str
    pointer: int
    size: int
    token: str
    rows: list[dict[str, Any]]
    fragment_rows: list[dict[str, Any]] = field(default_factory=list)

    @property
    def all_rows(self) -> list[dict[str, Any]]:
        return [*self.rows, *self.fragment_rows]


_GENERIC = re.compile(r"<(?!\w*>g__|\w*>b__)([A-Z]\w*(?:\s*,\s*[A-Z]\w*)*)>")


class BodyIndex:
    """Name-addressed method bodies of one opened build."""

    def __init__(self, image: NativeImage) -> None:
        self.image = image
        self.mapper = image.mapper
        self.pe = image.pe
        self.metadata = image.metadata

    @cached_property
    def names_by_pointer(self) -> dict[int, list[dict[str, Any]]]:
        modules = self.mapper.parse_codegen_modules(self.pe, self.image.code_registration)
        ranges = self.mapper.image_method_ranges(self.metadata)
        _by_image, by_pointer = self.mapper.build_pointer_indexes(self.pe, self.metadata, modules, ranges)
        generic = self.mapper.build_generic_method_index(
            self.pe, self.metadata, self.image.code_registration, self.image.metadata_registration
        )
        return {**generic, **by_pointer}

    @cached_property
    def pointers_by_name(self) -> dict[str, set[int]]:
        index: dict[str, set[int]] = {}
        for pointer, rows in self.names_by_pointer.items():
            for row in rows:
                index.setdefault(f"{row.get('type')}.{row.get('method')}", set()).add(pointer)
        return index

    @cached_property
    def extents(self) -> dict[int, int]:
        return self.mapper.pdata_function_extents(self.pe)

    @cached_property
    def sorted_pointers(self) -> list[int]:
        return sorted(self.names_by_pointer)

    @cached_property
    def types(self) -> dict[str, Any]:
        return {self.metadata.type_full_name(row): row for row in self.metadata.types}

    @cached_property
    def enum_defaults(self) -> dict[int, tuple[int, int]]:
        return il2cpp.field_defaults(self.metadata)

    def enum_member_id(self, type_name: str, member_name: str) -> int:
        try:
            members = il2cpp.native_enum_members(
                self.metadata, self.enum_defaults, self.pe, self.image.registration,
                type_name,
            )
        except (RuntimeError, ValueError, KeyError, IndexError) as exc:
            raise ClaimError(f"enum-unavailable:{type_name}:{exc}") from exc
        matches = [row["id"] for row in members if row["name"] == member_name]
        if len(matches) != 1:
            raise ClaimError(f"enum-member-missing-or-duplicate:{type_name}.{member_name}")
        return matches[0]

    @cached_property
    def by_suffix(self) -> dict[str, set[str]]:
        """Full names keyed by every ``Type.Method`` suffix spelling."""
        table: dict[str, set[str]] = {}
        for full in self.pointers_by_name:
            if full.endswith("..ctor"):
                type_name, method = full[:-6], ".ctor"
            else:
                type_name, _, method = full.rpartition(".")
            parts = re.split(r"[.+]", type_name)
            for count in range(1, len(parts) + 1):
                table.setdefault(f"{'.'.join(parts[-count:])}.{method}", set()).add(full)
            # A local function is cited by its outer type, not its closure class.
            if len(parts) > 1 and parts[-1].startswith("<>c") and method.startswith("<"):
                for count in range(1, len(parts)):
                    table.setdefault(f"{'.'.join(parts[-count - 1:-1])}.{method}", set()).add(full)
        return table

    def resolve(self, short: str, previous_type: str | None = None) -> str | None:
        """The unique full name a short ``Type.Method`` spelling cites, if any.

        Generic arguments become an arity (``List<T>`` -> ``List`1``), a
        trailing parameter list is ignored, and a bare method name inherits
        ``previous_type``. Ambiguous or unknown spellings resolve to None.
        """
        name = _GENERIC.sub(lambda m: f"`{len(m.group(1).split(','))}", short.strip())
        name = re.sub(r"\([^)]*\)$", "", name)
        if "." not in name and previous_type:
            name = f"{previous_type}.{name}"
        hits = self.by_suffix.get(name) or set()
        return next(iter(hits)) if len(hits) == 1 else None

    def name_of(self, pointer: int) -> str | None:
        rows = self.names_by_pointer.get(pointer)
        return f"{rows[0].get('type')}.{rows[0].get('method')}" if rows else None

    def names_of(self, pointer: int) -> list[str]:
        """Every method sharing one body: IL2CPP folds identical code."""
        return sorted({f"{row.get('type')}.{row.get('method')}" for row in self.names_by_pointer.get(pointer) or []})

    def field_offset(self, qualified: str) -> int:
        type_name, _, field_name = qualified.partition("::")
        type_def = self.types.get(type_name)
        if type_def is None:
            raise ClaimError(f"field-owner-missing:{type_name}")
        offsets = il2cpp.runtime_type_field_offsets(
            self.metadata, self.pe, self.image.registration, type_def.index
        )
        if field_name not in offsets:
            raise ClaimError(f"field-missing:{qualified}")
        return offsets[field_name]

    def _extent(self, pointer: int) -> int:
        if pointer in self.extents:
            # One function can span several chained .pdata chunks that fall
            # through into each other; stop at the next named method.
            end = self.extents[pointer]
            while end in self.extents and end not in self.names_by_pointer and end - pointer < 0x4000:
                end = self.extents[end]
            return end - pointer
        size, _next = self.mapper.estimate_scan_size(pointer, self.sorted_pointers, 0x4000)
        return size

    def _decode(self, pointer: int, size: int) -> list[dict[str, Any]]:
        return self.mapper.decode_x64_subset(self.pe.bytes_at_va(pointer, size), pointer, stop_offset=size)

    def ifix_patch_id(self, pointer: int) -> str | None:
        """An early iFix patch id tested by the body at ``pointer``.

        An iFix-wrapped method loads its patch id into ``ecx`` and calls
        ``IFix.WrappersManagerImpl.IsPatched`` in its prologue. This bounded
        search inspects at most the first 40 decoded instructions in 0x200
        bytes; ``None`` means not found there, not proof that the method is
        unwrapped or absent from an installed patch file.
        """
        size = min(self._extent(pointer), 0x200)
        last_ecx = None
        for row in self._decode(pointer, size)[:40]:
            text = str(row.get("text") or "")
            load = re.fullmatch(r"mov ecx, (0x[0-9a-f]+)", text)
            if load:
                last_ecx = load.group(1)
            call = re.fullmatch(r"call 0x([0-9a-f]+)", text)
            if call and "IFix.WrappersManagerImpl.IsPatched" in self.names_of(int(call.group(1), 16)):
                return last_ecx
        return None

    def parameter_types(self, pointer: int) -> list[list[str]]:
        """The parameter type names of every method sharing the body."""
        found = []
        for row in self.names_by_pointer.get(pointer) or []:
            index = row.get("methodIndex")
            if not isinstance(index, int) or not 0 <= index < len(self.metadata.methods):
                continue
            method = self.metadata.methods[index]
            found.append([
                self.metadata.metadata_type_name(parameter.type_index)
                for parameter in self.metadata.parameters_for(method)
            ])
        return found

    def parameter_location(self, pointer: int, symbol: str, parameter: str) -> tuple[str, int | str]:
        """Resolve one named parameter to its Windows x64 argument location.

        A stack offset is relative to entry RSP. At a call site the same
        parameter occupies an outgoing slot eight bytes lower, because the
        return address has not yet been pushed.
        """
        locations: set[tuple[str, int | str]] = set()
        for row in self.names_by_pointer.get(pointer) or []:
            if f"{row.get('type')}.{row.get('method')}" != symbol:
                continue
            method_index = row.get("methodIndex")
            if not isinstance(method_index, int) or not 0 <= method_index < len(self.metadata.methods):
                continue
            method = self.metadata.methods[method_index]
            parameters = self.metadata.parameters_for(method)
            matches = [position for position, item in enumerate(parameters)
                       if self.metadata.string(item.name_index) == parameter]
            if len(matches) != 1:
                continue
            position = matches[0]
            registers = ("rcx", "rdx", "r8", "r9") if method.flags & 0x10 else ("rdx", "r8", "r9")
            if position < len(registers):
                locations.add(("register", registers[position]))
            else:
                locations.add(("stack", 0x28 + (position - len(registers)) * 8))
        if len(locations) != 1:
            raise ClaimError(f"parameter missing or ambiguous: {symbol}.{parameter} at 0x{pointer:x}")
        return next(iter(locations))

    def body(
        self,
        type_name: str,
        method: str,
        method_arguments: list[str] | None = None,
        parameters: list[str] | None = None,
        parameters_prefix: list[str] | None = None,
        class_arguments: list[str] | None = None,
    ) -> Body:
        pointers = sorted(self.pointers_by_name.get(f"{type_name}.{method}") or [])
        if parameters is not None:
            pointers = [pointer for pointer in pointers if list(parameters) in self.parameter_types(pointer)]
        if parameters_prefix is not None:
            pointers = [
                pointer for pointer in pointers
                if any(
                    signature[:len(parameters_prefix)] == list(parameters_prefix)
                    for signature in self.parameter_types(pointer)
                )
            ]
        if method_arguments is not None:
            pointers = [
                pointer for pointer in pointers
                if any(
                    [arg.get("typeName") for arg in (row.get("methodInstantiation") or {}).get("arguments") or []]
                    == list(method_arguments)
                    for row in self.names_by_pointer[pointer]
                )
            ]
        if class_arguments is not None:
            pointers = [
                pointer for pointer in pointers
                if any(
                    [arg.get("typeName") for arg in (row.get("classInstantiation") or {}).get("arguments") or []]
                    == list(class_arguments)
                    for row in self.names_by_pointer[pointer]
                )
            ]
        if len(pointers) != 1:
            raise ClaimError(f"{type_name}.{method}:{len(pointers)} bodies")
        pointer = pointers[0]
        size = self._extent(pointer)
        token = str((self.names_by_pointer[pointer][0]).get("token") or "")
        body = Body(f"{type_name}.{method}", pointer, size, token, self._decode(pointer, size))
        body.fragment_rows = self.body_with_fragments(body)[len(body.rows):]
        return body

    @cached_property
    def chained_fragments(self) -> dict[int, list[tuple[int, int]]]:
        """Each function's split-off ``.pdata`` fragments, by chained unwind info.

        A cold path the compiler moved into its own ``.pdata`` entry carries
        ``UNW_FLAG_CHAININFO``, and its unwind data ends in the RUNTIME_FUNCTION of
        the function it belongs to. Following that chain names a fragment's
        owner exactly, however the owner reaches it.
        """
        pe = self.pe
        section = next((row for row in pe.sections if row["name"] == ".pdata"), None)
        if section is None:
            return {}
        raw = bytes(pe.buf[section["rawPointer"]:section["rawPointer"] + section["virtualSize"]])
        entries: dict[int, tuple[int, int]] = {}
        for offset in range(0, len(raw) - 11, 12):
            begin, end, unwind = struct.unpack_from("<III", raw, offset)
            if begin == 0:
                break
            entries[pe.image_base + begin] = (pe.image_base + end, unwind)

        def root(start: int) -> int:
            for _hop in range(8):
                info = pe.file_offset_for_rva(entries[start][1])[0]
                if not (pe.buf[info] >> 3) & 0x4:
                    return start
                chained = info + 4 + ((pe.buf[info + 2] + 1) & ~1) * 2
                parent = pe.image_base + struct.unpack_from("<I", pe.buf, chained)[0]
                if parent not in entries:
                    return start
                start = parent
            return start

        fragments: dict[int, list[tuple[int, int]]] = {}
        for start, (end, _unwind) in entries.items():
            owner = root(start)
            if owner != start:
                fragments.setdefault(owner, []).append((start, end - start))
        return fragments

    def body_with_fragments(self, body: Body) -> list[dict[str, Any]]:
        """A body's rows plus every fragment it owns and the fragments it jumps to."""
        rows = list(body.rows)
        followed = set()
        for start, size in self.chained_fragments.get(body.pointer, ()):
            followed.add(start)
            rows.extend(self._decode(start, size))
        for row in body.rows:
            match = _JUMP.fullmatch(str(row.get("text") or ""))
            if not match:
                continue
            target = int(match.group(1), 16)
            if body.pointer <= target < body.pointer + body.size or target in self.names_by_pointer:
                continue
            if target in followed:
                continue
            if target in self.extents and self.extents[target] - target <= MAX_FOLLOWED_BYTES:
                rows.extend(self._decode(target, self.extents[target] - target))
        return rows

    def overload_bodies(self, type_name: str, method: str) -> list[Body]:
        """Every body sharing a name (overloads and instantiations)."""
        bodies = []
        for pointer in sorted(self.pointers_by_name.get(f"{type_name}.{method}") or []):
            size = self._extent(pointer)
            bodies.append(Body(f"{type_name}.{method}", pointer, size, "", self._decode(pointer, size)))
        return bodies

    def callees(self, rows: Iterable[dict[str, Any]]) -> list[tuple[int, str]]:
        """``(offset, name)`` for each call/jump reaching a named method."""
        found: list[tuple[int, str]] = []
        for row in rows:
            match = _CALL.fullmatch(str(row.get("text") or ""))
            if not match:
                continue
            target = int(match.group(2), 16)
            names = self.names_of(target)
            if names:
                found.extend((int(row.get("offset") or 0), name) for name in names)
                continue
            if target in self.extents and self.extents[target] - target <= MAX_FOLLOWED_BYTES:
                helper = self.pe.bytes_at_va(target, self.extents[target] - target)
                for position in range(len(helper) - 5):
                    if helper[position] != 0xE8:
                        continue
                    inner = self.names_of(target + position + 5 + struct.unpack_from("<i", helper, position + 1)[0])
                    found.extend((int(row.get("offset") or 0), name) for name in inner)
        return found


def _texts(rows: Iterable[dict[str, Any]]) -> list[str]:
    return [str(row.get("text") or "") for row in rows]


def _condition(row: dict[str, Any]) -> str:
    text = str(row.get("text") or "")
    raw = str(row.get("bytes") or "").split()
    if text.startswith("jcc ") and len(raw) >= 2 and raw[0].lower() == "0f":
        return _NEAR_CONDITION.get(int(raw[1], 16), "jcc")
    return text.split(" ", 1)[0]


_REGISTER_ROOT = {
    alias: root
    for root, aliases in {
        "rax": ("rax", "eax", "ax", "al", "ah"),
        "rbx": ("rbx", "ebx", "bx", "bl", "bh"),
        "rcx": ("rcx", "ecx", "cx", "cl", "ch"),
        "rdx": ("rdx", "edx", "dx", "dl", "dh"),
        "rsi": ("rsi", "esi", "si", "sil"),
        "rdi": ("rdi", "edi", "di", "dil"),
        "rbp": ("rbp", "ebp", "bp", "bpl"),
        "rsp": ("rsp", "esp", "sp", "spl"),
        **{f"r{number}": tuple(f"r{number}{suffix}" for suffix in ("", "d", "w", "b"))
           for number in range(8, 16)},
    }.items()
    for alias in aliases
}


def _writes_register(row: dict[str, Any], register: str) -> bool:
    root = _REGISTER_ROOT.get(register, register)
    write = row.get("write")
    if isinstance(write, dict):
        written = write.get("register")
        return isinstance(written, str) and _REGISTER_ROOT.get(written, written) == root
    match = re.match(r"(?:mov|movsxd|movzx|movsx|lea|xor|pop|add|sub|or|and|shl|shr|sar|imul|inc|dec) (\w+)(?:,|$)", str(row.get("text") or ""))
    return bool(match and _REGISTER_ROOT.get(match.group(1), match.group(1)) == root)


def _field_load(text: str, offset: int) -> str | None:
    match = re.fullmatch(rf"mov (\w+), \[\w+\+0x{offset:x}\]", text)
    return match.group(1) if match else None


def _rip_usage_word(index: BodyIndex, row: dict[str, Any], register: str, tag: int) -> int | None:
    """Read one unresolved IL2CPP usage cell loaded into a named register."""
    if not re.fullmatch(
        rf"mov {re.escape(register)}, \[rip[+-]0x[0-9a-f]+(?: => 0x[0-9a-f]+)?\]",
        str(row.get("text") or ""),
    ):
        return None
    raw = bytes.fromhex(str(row.get("bytes") or ""))
    if len(raw) != 7:
        return None
    va = int(str(row.get("va") or "0"), 16)
    cell = va + len(raw) + struct.unpack_from("<i", raw, 3)[0]
    try:
        word = index.pe.u64_at_va(cell)
    except ValueError:
        return None
    return word if word <= 0xFFFFFFFF and word & 1 and word >> 29 == tag else None


def _usage_method_name(index: BodyIndex, row: dict[str, Any]) -> str | None:
    word = _rip_usage_word(index, row, "r8", 3)
    if word is None:
        return None
    method_index = (word >> 1) & 0x0FFFFFFF
    if method_index >= len(index.metadata.methods):
        return None
    method = index.metadata.methods[method_index]
    if not 0 <= method.declaring_type < len(index.metadata.types):
        return None
    return (f"{index.metadata.type_full_name(index.metadata.types[method.declaring_type])}."
            f"{index.metadata.string(method.name_index)}")


def _usage_literal(index: BodyIndex, row: dict[str, Any]) -> str | None:
    word = _rip_usage_word(index, row, "r8", 5)
    if word is None:
        return None
    section = index.metadata.sections["stringLiteral"]
    data_section = index.metadata.sections["stringLiteralData"]
    literal_index = (word >> 1) & 0x0FFFFFFF
    if literal_index >= section.size // 8:
        return None
    length, start = struct.unpack_from("<ii", index.metadata.buf, section.offset + literal_index * 8)
    if length < 0 or start < 0 or start + length > data_section.size:
        return None
    return index.metadata.buf[data_section.offset + start:data_section.offset + start + length].decode("utf-8", "replace")


def _virtual_method_slot(index: BodyIndex, symbol: str) -> int:
    type_name, separator, method_name = symbol.rpartition(".")
    if not separator or type_name not in index.types:
        raise ClaimError(f"virtual method type missing: {symbol}")
    methods = [
        method for method in index.metadata.methods_for(index.types[type_name])
        if index.metadata.string(method.name_index) == method_name
    ]
    if len(methods) != 1 or not methods[0].flags & 0x40 or methods[0].slot == 0xFFFF:
        raise ClaimError(f"virtual method missing or ambiguous: {symbol}")
    return methods[0].slot


def _virtual_slot_helper(index: BodyIndex, pointer: int) -> bool:
    """Recognize the selected IL2CPP helper's receiver/slot/argument dispatch."""
    try:
        size = index._extent(pointer)
        if size > MAX_FOLLOWED_BYTES:
            return False
        data = index.pe.bytes_at_va(pointer, size)
    except (KeyError, ValueError):
        return False
    # ecx is the vtable slot; rdx is the receiver; r8 is the property
    # blackboard. Il2CppClass's 16-byte vtable entries start at +0x140.
    prefix = bytes.fromhex("0f b7 f9 49 8b f0 48 8b 0a 48 8b da")
    entry = bytes.fromhex("48 8d 47 14 48 c1 e0 04 48 03 03 4c 8b 08 4c 8b 40 08")
    invoke = bytes.fromhex("48 8b d6 48 8b cb 41 ff d1")
    first = data.find(prefix)
    second = data.find(entry, first + len(prefix)) if first >= 0 else -1
    third = data.find(invoke, second + len(entry)) if second >= 0 else -1
    return first >= 0 and second >= 0 and third >= 0


def _rsp_delta(rows: list[dict[str, Any]], position: int) -> int:
    """Bytes by which the current RSP is below entry RSP before one row."""
    delta = 0
    for row in rows[:position]:
        instruction = str(row.get("text") or "")
        if re.fullmatch(r"push \w+", instruction):
            delta += 8
        elif re.fullmatch(r"pop \w+", instruction):
            delta -= 8
        elif match := re.fullmatch(r"sub rsp, (0x[0-9a-f]+|\d+)", instruction):
            delta += int(match.group(1), 0)
        elif match := re.fullmatch(r"add rsp, (0x[0-9a-f]+|\d+)", instruction):
            delta -= int(match.group(1), 0)
        elif _writes_register(row, "rsp"):
            raise ClaimError(f"unhandled RSP write: {instruction}")
    return delta


def _named_direct_call(index: BodyIndex, row: dict[str, Any], symbol: str) -> int | None:
    match = _CALL.fullmatch(str(row.get("text") or ""))
    if match and symbol in index.names_of(int(match.group(2), 16)):
        return int(match.group(2), 16)
    return None


def _constant_before_call(rows: list[dict[str, Any]], call_at: int, register: str) -> int | None:
    """Trace a callee register backward through bounded constant and register moves."""
    current = _REGISTER_ROOT.get(register, register)
    volatile = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
    for row in reversed(rows[max(0, call_at - 80):call_at]):
        instruction = str(row.get("text") or "")
        if instruction.startswith("call ") and current in volatile:
            return None
        if not _writes_register(row, current):
            continue
        direct = re.fullmatch(r"mov (\w+), (-?(?:0x[0-9a-f]+|\d+))", instruction)
        if direct and _REGISTER_ROOT.get(direct.group(1)) == current:
            return int(direct.group(2), 0)
        moved = re.fullmatch(r"mov (\w+), (\w+)", instruction)
        if moved and _REGISTER_ROOT.get(moved.group(1)) == current:
            source = _REGISTER_ROOT.get(moved.group(2))
            if source is None:
                return None
            current = source
            continue
        zeroed = re.fullmatch(r"xor (\w+), (\w+)", instruction)
        if zeroed and _REGISTER_ROOT.get(zeroed.group(1)) == current and zeroed.group(1) == zeroed.group(2):
            return 0
        return None
    return None


def _parameter_aliases_before_call(
    index: BodyIndex, body: Body, call_at: int, parameter: str,
) -> set[str]:
    kind, source = index.parameter_location(body.pointer, body.symbol, parameter)
    if kind != "register":
        raise ClaimError(f"{body.symbol}.{parameter} is not a register parameter")
    aliases = {_REGISTER_ROOT[str(source)]}
    volatile = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
    for row in body.rows[:call_at]:
        instruction = str(row.get("text") or "")
        moved = re.fullmatch(r"mov (\w+), (\w+)", instruction)
        if moved:
            destination = _REGISTER_ROOT.get(moved.group(1))
            source_register = _REGISTER_ROOT.get(moved.group(2))
            if destination:
                if source_register in aliases:
                    aliases.add(destination)
                else:
                    aliases.discard(destination)
        else:
            for register in tuple(aliases):
                if _writes_register(row, register):
                    aliases.discard(register)
        if instruction.startswith("call "):
            aliases -= volatile
    return aliases


def check_claim(index: BodyIndex, body: Body, claim: dict[str, Any]) -> str | None:
    """Return a bounded failure reason, or ``None`` when the claim holds."""
    rows = body.all_rows
    texts = _texts(rows)
    if "callsAnonymousHelper" in claim:
        spec = claim["callsAnonymousHelper"]
        expected_calls = set(spec.get("helperCalls") or [])
        expected_instructions = list(spec.get("helperMatches") or [])
        for call_at, row in enumerate(body.rows):
            match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
            if not match:
                continue
            pointer = int(match.group(1), 16)
            if index.names_of(pointer) or pointer not in index.extents:
                continue
            size = index.extents[pointer] - pointer
            fragments = index.chained_fragments.get(pointer, ())
            if size <= 0 or size + sum(length for _start, length in fragments) > MAX_FOLLOWED_BYTES:
                continue
            helper = Body("<anonymous>", pointer, size, "", index._decode(pointer, size))
            helper.fragment_rows = index.body_with_fragments(helper)[len(helper.rows):]
            names = {name for _offset, name in index.callees(helper.all_rows)}
            instructions = _texts(helper.all_rows)
            if (not expected_calls <= names or any(
                not any(re.fullmatch(pattern, instruction) for instruction in instructions)
                for pattern in expected_instructions
            )):
                continue
            if any(
                _REGISTER_ROOT.get(register, register)
                not in _parameter_aliases_before_call(index, body, call_at, parameter)
                for parameter, register in (spec.get("argumentMap") or {}).items()
            ):
                continue
            if any(
                _constant_before_call(body.rows, call_at, register) != int(value)
                for register, value in (spec.get("constantArguments") or {}).items()
            ):
                continue
            return None
        return (f"{body.symbol}: no anonymous call satisfies calls={sorted(expected_calls)} "
                f"instructions={expected_instructions} arguments={spec.get('argumentMap') or {}} "
                f"constants={spec.get('constantArguments') or {}}")
    if "passesEnumMemberToCall" in claim:
        spec = claim["passesEnumMemberToCall"]
        member = index.enum_member_id(spec["enumType"], spec["member"])
        for position, row in enumerate(body.rows):
            pointer = _named_direct_call(index, row, spec["call"])
            if pointer is None:
                continue
            kind, register = index.parameter_location(pointer, spec["call"], spec["parameter"])
            if kind == "register" and _constant_before_call(body.rows, position, str(register)) == member:
                return None
        return f"{spec['call']}.{spec['parameter']} never receives {spec['enumType']}.{spec['member']}"
    if "passesArgumentToCall" in claim:
        spec = claim["passesArgumentToCall"]
        source_kind, source = index.parameter_location(body.pointer, body.symbol, spec["fromParameter"])
        if source_kind != "register":
            return f"{body.symbol}.{spec['fromParameter']} is not a register argument"
        aliases = {_REGISTER_ROOT[str(source)]}
        volatile = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
        for row in body.rows:
            target = _named_direct_call(index, row, spec["call"])
            if target is not None:
                kind, destination = index.parameter_location(target, spec["call"], spec["toParameter"])
                if kind == "register" and _REGISTER_ROOT[str(destination)] in aliases:
                    return None
            instruction = str(row.get("text") or "")
            moved = re.fullmatch(r"mov (\w+), (\w+)", instruction)
            if moved:
                destination = _REGISTER_ROOT.get(moved.group(1))
                source_register = _REGISTER_ROOT.get(moved.group(2))
                if destination:
                    if source_register in aliases:
                        aliases.add(destination)
                    else:
                        aliases.discard(destination)
            elif _writes_register(row, "rsp"):
                pass
            else:
                for register in tuple(aliases):
                    if _writes_register(row, register):
                        aliases.discard(register)
            if instruction.startswith("call "):
                aliases -= volatile
        return f"{body.symbol}.{spec['fromParameter']} never reaches {spec['call']}.{spec['toParameter']}"
    if "passesOutParameterToCall" in claim:
        spec = claim["passesOutParameterToCall"]
        for source_at, source_row in enumerate(body.rows):
            source_pointer = _named_direct_call(index, source_row, spec["fromCall"])
            if source_pointer is None:
                continue
            source_kind, source_register = index.parameter_location(
                source_pointer, spec["fromCall"], spec["outParameter"])
            if source_kind != "register":
                continue
            for preceding_at in range(max(0, source_at - 10), source_at):
                preceding = body.rows[preceding_at]
                slot = re.fullmatch(
                    rf"lea {re.escape(str(source_register))}, \[rsp\+0x([0-9a-f]+)\]",
                    str(preceding.get("text") or ""),
                )
                if slot is None:
                    continue
                offset = slot.group(1)
                for target_at in range(source_at + 1, min(len(body.rows), source_at + 40)):
                    target_pointer = _named_direct_call(index, body.rows[target_at], spec["toCall"])
                    if target_pointer is None:
                        continue
                    target_kind, target_register = index.parameter_location(
                        target_pointer, spec["toCall"], spec["inParameter"])
                    if target_kind != "register":
                        continue
                    load = f"mov {target_register}, [rsp+0x{offset}]"
                    if (_rsp_delta(body.rows, preceding_at) != _rsp_delta(body.rows, target_at)
                            or any(
                        re.fullmatch(rf"mov \[rsp\+0x{offset}\], .+", instruction)
                        for instruction in _texts(body.rows[source_at + 1:target_at]))):
                        continue
                    for load_at in range(source_at + 1, target_at):
                        if str(body.rows[load_at].get("text") or "") != load:
                            continue
                        if not any(_writes_register(other, str(target_register))
                                   for other in body.rows[load_at + 1:target_at]):
                            return None
        return (f"{spec['fromCall']}.{spec['outParameter']} slot never reaches "
                f"{spec['toCall']}.{spec['inParameter']}")
    if "passesNestedFieldToCall" in claim:
        spec = claim["passesNestedFieldToCall"]
        parent = index.field_offset(spec["parentField"])
        child = index.field_offset(spec["field"])
        for call_at, row in enumerate(body.rows):
            pointer = _named_direct_call(index, row, spec["call"])
            if pointer is None:
                continue
            kind, entry_offset = index.parameter_location(pointer, spec["call"], spec["parameter"])
            if kind != "stack":
                continue
            outgoing = int(entry_offset) - 8
            for store_at in range(max(0, call_at - 40), call_at):
                stored = re.fullmatch(
                    rf"mov \[rsp\+0x{outgoing:x}\], (\w+)",
                    str(body.rows[store_at].get("text") or ""),
                )
                if (stored is None or _rsp_delta(body.rows, store_at) != _rsp_delta(body.rows, call_at)
                        or any(re.fullmatch(rf"mov \[rsp\+0x{outgoing:x}\], .+", instruction)
                               for instruction in _texts(body.rows[store_at + 1:call_at]))):
                    continue
                value_register = stored.group(1)
                for child_at in range(max(0, store_at - 50), store_at):
                    loaded = re.fullmatch(
                        rf"mov {re.escape(value_register)}, \[(\w+)\+0x{child:x}\]",
                        str(body.rows[child_at].get("text") or ""),
                    )
                    if loaded is None or any(_writes_register(other, value_register)
                                             for other in body.rows[child_at + 1:store_at]):
                        continue
                    parent_register = loaded.group(1)
                    for parent_at in range(max(0, child_at - 80), child_at):
                        if (_field_load(str(body.rows[parent_at].get("text") or ""), parent)
                                == parent_register
                                and not any(_writes_register(other, parent_register)
                                            for other in body.rows[parent_at + 1:child_at])):
                            return None
        return f"{spec['field']} never reaches {spec['call']}.{spec['parameter']}"
    if "forwardsStackParameter" in claim:
        spec = claim["forwardsStackParameter"]
        source_kind, entry_offset = index.parameter_location(body.pointer, body.symbol, spec["fromParameter"])
        if source_kind != "stack":
            return f"{body.symbol}.{spec['fromParameter']} is not a stack argument"
        for call_at, row in enumerate(body.rows):
            pointer = _named_direct_call(index, row, spec["call"])
            if pointer is None:
                continue
            target_kind, target_offset = index.parameter_location(pointer, spec["call"], spec["toParameter"])
            if target_kind != "stack":
                continue
            outgoing = int(target_offset) - 8
            for load_at in range(max(0, call_at - 50), call_at):
                incoming = int(entry_offset) + _rsp_delta(body.rows, load_at)
                loaded = re.fullmatch(
                    rf"mov (\w+), \[rsp\+0x{incoming:x}\]",
                    str(body.rows[load_at].get("text") or ""),
                )
                if loaded is None:
                    continue
                register = loaded.group(1)
                for store_at in range(load_at + 1, min(call_at, load_at + 5)):
                    if (_rsp_delta(body.rows, store_at) != _rsp_delta(body.rows, call_at)
                            or any(_writes_register(other, register)
                                   for other in body.rows[load_at + 1:store_at])):
                        continue
                    if str(body.rows[store_at].get("text") or "") != f"mov [rsp+0x{outgoing:x}], {register}":
                        continue
                    if not any(re.fullmatch(rf"mov \[rsp\+0x{outgoing:x}\], .+", instruction)
                               for instruction in _texts(body.rows[store_at + 1:call_at])):
                        return None
        return (f"{body.symbol}.{spec['fromParameter']} never reaches "
                f"{spec['call']}.{spec['toParameter']}")
    if "dispatchesVirtualMethod" in claim:
        spec = claim["dispatchesVirtualMethod"]
        base = spec["base"]
        slot = _virtual_method_slot(index, base)
        for override in spec["overrides"]:
            actual = _virtual_method_slot(index, override)
            if actual != slot:
                return f"{override} slot {actual} differs from {base} slot {slot}"
        immediate = {f"mov ecx, 0x{slot:x}", f"mov ecx, {slot}"}
        for position, row in enumerate(body.rows):
            call = _CALL.fullmatch(str(row.get("text") or ""))
            if not call or call.group(1) != "call":
                continue
            window = _texts(body.rows[max(0, position - 18):position])
            for receiver_at, receiver in enumerate(window):
                receiver_load = re.fullmatch(r"mov rsi, \[rbx\+0x([0-9a-f]+)\]", receiver)
                if not receiver_load:
                    continue
                receiver_offset = receiver_load.group(1)
                if f"mov [rbx+0x{receiver_offset}], rax" not in _texts(body.rows[:position]):
                    continue
                for blackboard_at, blackboard in enumerate(window[receiver_at + 1:], receiver_at + 1):
                    blackboard_load = re.fullmatch(r"mov r8, \[rbx\+0x([0-9a-f]+)\]", blackboard)
                    if not blackboard_load or blackboard_load.group(1) == receiver_offset:
                        continue
                    tail = window[blackboard_at + 1:]
                    if len(tail) != 2 or tail[0] not in immediate or tail[1] != "mov rdx, rsi":
                        continue
                    if _virtual_slot_helper(index, int(call.group(2), 16)):
                        return None
        return f"no instance-data/blackboard dispatch through {base} slot {slot}"
    if "bindsLiteralToCallback" in claim:
        spec = claim["bindsLiteralToCallback"]
        literal, callback, assign_call = spec["literal"], spec["callback"], spec["assignCall"]
        for assign_at, row in enumerate(rows):
            match = _CALL.fullmatch(str(row.get("text") or ""))
            if not match or assign_call not in index.names_of(int(match.group(2), 16)):
                continue
            for literal_at in range(max(0, assign_at - 8), assign_at):
                if _usage_literal(index, rows[literal_at]) != literal:
                    continue
                for ctor_at in range(max(0, literal_at - 8), literal_at):
                    ctor = _CALL.fullmatch(texts[ctor_at])
                    if not ctor or not any(
                        name.startswith("System.Action`1..ctor")
                        for name in index.names_of(int(ctor.group(2), 16))
                    ):
                        continue
                    if "mov r9, rsi" not in texts[ctor_at + 1:assign_at]:
                        continue
                    if any(_usage_method_name(index, rows[callback_at]) == callback
                           for callback_at in range(max(0, ctor_at - 8), ctor_at)):
                        return None
        return f"{assign_call} does not bind literal {literal!r} to callback {callback}"
    if "calls" in claim:
        seen = index.callees(rows)
        names = [name for _offset, name in seen]
        missing = [name for name in claim["calls"] if name not in names]
        if missing:
            return f"missing calls {missing}"
        if claim.get("ordered"):
            firsts = [names.index(name) for name in claim["calls"]]
            if firsts != sorted(firsts):
                return f"calls out of order {claim['calls']}"
        return None
    if "comparesResult" in claim:
        target, value = claim["comparesResult"]["call"], int(claim["comparesResult"]["value"])
        immediates = {f"0x{value:x}", str(value)}
        holding = {
            match.group(1)
            for text in texts
            if (match := re.fullmatch(r"mov (\w+), (0x[0-9a-f]+|\d+)", text)) and match.group(2) in immediates
        }
        for position, row in enumerate(rows):
            match = _CALL.fullmatch(str(row.get("text") or ""))
            if not match or target not in index.names_of(int(match.group(2), 16)):
                continue
            aliases = {"rax", "eax"}
            for text in texts[position + 1:position + 12]:
                moved = re.fullmatch(r"mov (\w+), (\w+)", text)
                if moved and moved.group(2) in aliases:
                    aliases.add(moved.group(1))
                compared = re.fullmatch(r"cmp (\w+), (\w+)", text)
                if compared and compared.group(1) in aliases and (
                    compared.group(2) in immediates or compared.group(2) in holding
                ):
                    return None
        return f"{target} result never compared with {value}"
    if "matches" in claim:
        pattern = re.compile(claim["matches"])
        return None if any(pattern.fullmatch(text) for text in texts) else f"no instruction matches {claim['matches']!r}"
    if "notCallsPrefix" in claim:
        prefix = claim["notCallsPrefix"]
        hits = sorted({name for _offset, name in index.callees(rows) if name.startswith(prefix)})
        return f"calls {hits}" if hits else None
    if "returnsEnumMember" in claim:
        spec = claim["returnsEnumMember"]
        value = index.enum_member_id(spec["type"], spec["member"])
        reason = check_claim(index, body, {"returnsConstant": value})
        return (f"{spec['type']}.{spec['member']} ({value}): {reason}"
                if reason else None)
    if "returnsConstant" in claim:
        value = int(claim["returnsConstant"])
        wanted = {f"mov eax, 0x{value:x}", f"mov eax, {value}"}
        return None if wanted & set(_texts(body.rows)) else f"no mov eax, 0x{value:x}"
    if "returnsArgument" in claim:
        aliases = {claim["returnsArgument"]}
        for text in _texts(body.rows):
            match = re.fullmatch(r"mov (\w+), (\w+)", text)
            if match and match.group(2) in aliases:
                aliases.add(match.group(1))
        return None if any(f"mov eax, {alias}" in texts for alias in aliases - {"eax"}) else "argument not returned"
    if "storesConstant" in claim:
        offset = index.field_offset(claim["storesConstant"]["field"])
        value = int(claim["storesConstant"]["value"])
        pattern = re.compile(rf"mov \[\w+\+0x{offset:x}\], 0x{value:x}$")
        return None if any(pattern.fullmatch(text) for text in texts) else f"no store of {value} at +0x{offset:x}"
    if "readsField" in claim:
        offset = index.field_offset(claim["readsField"])
        pattern = re.compile(rf"\[\w+\+0x{offset:x}\]")
        return None if any(pattern.search(text) and not text.startswith("lea ") for text in texts) else f"no read of +0x{offset:x}"
    if "writesField" in claim:
        offset = index.field_offset(claim["writesField"])
        pattern = re.compile(rf"mov(?:sd|ss|ups|aps)? \[\w+\+0x{offset:x}\], (?:\w+|0x[0-9a-f]+)$")
        return None if any(pattern.fullmatch(text) for text in texts) else f"no write of +0x{offset:x}"
    if "loadsLiterals" in claim:
        found = loaded_literals(CallGraph(index.image), body.pointer, body.size)
        missing = sorted(set(claim["loadsLiterals"]) - found)
        return f"missing string literals {missing}" if missing else None
    if "loadsFloat32" in claim:
        expected = struct.pack("<f", float(claim["loadsFloat32"]))
        data = index.pe.bytes_at_va(body.pointer, body.size)
        for offset in range(max(0, len(data) - 7)):
            if data[offset:offset + 3] != b"\xf3\x0f\x10":
                continue
            if data[offset + 3] & 0xC7 != 0x05:
                continue
            displacement = struct.unpack_from("<i", data, offset + 4)[0]
            constant_va = body.pointer + offset + 8 + displacement
            try:
                actual = index.pe.bytes_at_va(constant_va, 4)
            except ValueError:
                continue
            if actual == expected:
                return None
        return f"no RIP-relative MOVSS loads Single {claim['loadsFloat32']!r}"
    if "readsNestedField" in claim:
        spec = claim["readsNestedField"]
        parent = index.field_offset(spec["parentField"])
        child = index.field_offset(spec["field"])
        for position, row in enumerate(rows):
            register = _field_load(str(row.get("text") or ""), parent)
            if register is None:
                continue
            pattern = re.compile(rf"\[{re.escape(register)}\+0x{child:x}\]")
            for following in rows[position + 1:position + 33]:
                following_text = str(following.get("text") or "")
                if following_text.startswith("call "):
                    break
                if pattern.search(following_text) and not following_text.startswith("lea "):
                    return None
                if _writes_register(following, register):
                    break
        return f"no read of {spec['field']} through {spec['parentField']}"
    if "passesFieldToCall" in claim:
        spec = claim["passesFieldToCall"]
        offset = index.field_offset(spec["field"])
        register = spec["register"]
        target = spec["call"]
        for position, row in enumerate(rows):
            match = _CALL.fullmatch(str(row.get("text") or ""))
            if not match or target not in index.names_of(int(match.group(2), 16)):
                continue
            for preceding in reversed(rows[max(0, position - 8):position]):
                preceding_text = str(preceding.get("text") or "")
                if preceding_text.startswith("call "):
                    break
                if _writes_register(preceding, register):
                    if _field_load(preceding_text, offset) == register:
                        return None
                    break
        return f"{target} never receives {spec['field']} in {register}"
    if "zeroArgumentAt" in claim:
        target, register = claim["zeroArgumentAt"]["call"], claim["zeroArgumentAt"]["register"]
        for position, row in enumerate(rows):
            match = _CALL.fullmatch(str(row.get("text") or ""))
            if not match or index.name_of(int(match.group(2), 16)) != target:
                continue
            window = texts[max(0, position - 6):position]
            if f"xor {register}, {register}" in window or f"mov {register}, 0x0" in window:
                return None
        return f"{target} never receives zero in {register}"
    if "branchesOnSign" in claim:
        offset = index.field_offset(claim["branchesOnSign"])
        for position, text in enumerate(texts):
            if re.fullmatch(rf"cmp \[\w+\+0x{offset:x}\], 0x0", text):
                if any(_condition(row) in {"jl", "js"} for row in rows[position + 1:position + 3]):
                    return None
        return f"no signed branch on +0x{offset:x}"
    if "storesArgument" in claim:
        offset = index.field_offset(claim["storesArgument"]["field"])
        aliases = _argument_aliases(texts, claim["storesArgument"]["argument"])
        for text in texts:
            stored = re.fullmatch(rf"mov \[\w+\+0x{offset:x}\], (\w+)", text)
            if stored and stored.group(1) in aliases:
                return None
        return f"argument {claim['storesArgument']['argument']} never stored at +0x{offset:x}"
    if "comparesWithArguments" in claim:
        spec = claim["comparesWithArguments"]
        compared: set[str] = set()
        for argument in spec["arguments"]:
            aliases = _argument_aliases(texts, argument)
            if any(
                (match := re.fullmatch(r"cmp (\w+), (\w+)", text))
                and (match.group(1) in aliases) != (match.group(2) in aliases)
                for text in texts
            ):
                compared.add(argument)
        missing = [argument for argument in spec["arguments"] if argument not in compared]
        if missing:
            return f"no comparison with {missing}"
        if spec.get("zero") and not any(
            re.fullmatch(r"test (\w+), \1", text) and _condition(rows[position + 1]) in {"je", "jne"}
            for position, text in enumerate(texts[:-1])
        ):
            return "no zero test"
        return None
    return f"unknown claim {sorted(claim)}"


_ARGUMENT_WIDTHS = {
    "rcx": "ecx", "rdx": "edx", "r8": "r8d", "r9": "r9d",
    "ecx": "rcx", "edx": "rdx", "r8d": "r8", "r9d": "r9",
}


def _argument_aliases(texts: list[str], argument: str) -> set[str]:
    """Registers holding ``argument`` after the prologue's register moves."""
    aliases = {argument, _ARGUMENT_WIDTHS.get(argument, argument)}
    for text in texts:
        moved = re.fullmatch(r"mov (\w+), (\w+)", text)
        if moved and moved.group(2) in aliases:
            aliases.add(moved.group(1))
    return aliases


def evaluate(index: BodyIndex, methods: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate every method's claims; return (rows, failures)."""
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for symbol, spec in methods.items():
        try:
            body = index.body(
                spec["type"], spec["method"], spec.get("methodArguments"),
                spec.get("parameters"), spec.get("parametersPrefix"), spec.get("classArguments"),
            )
        except ClaimError as error:
            failures.append({"symbol": symbol, "claim": "resolve", "reason": str(error)})
            continue
        for claim in spec.get("claims") or []:
            try:
                reason = check_claim(index, body, claim)
            except ClaimError as error:
                reason = str(error)
            if reason:
                failures.append({"symbol": symbol, "claim": claim, "reason": reason})
        data = index.pe.bytes_at_va(body.pointer, body.size)
        rows.append({
            "symbol": symbol,
            "token": body.token,
            "address": f"0x{body.pointer:x}",
            "byteCount": body.size,
            "bodySha256": hashlib.sha256(data).hexdigest(),
            "claims": spec.get("claims") or [],
            "contract": spec.get("contract", ""),
        })
    return rows, failures


__all__ = ["Body", "BodyIndex", "ClaimError", "check_claim", "evaluate"]
