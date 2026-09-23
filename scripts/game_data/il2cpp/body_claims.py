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
``returnsArgument``   some path returns the named argument register unchanged
``storesConstant``    writes an immediate into a named field of ``this``
``readsField``        reads a named field (any base register)
``zeroArgumentAt``    a named call receives zero in the given argument register
``branchesOnSign``    compares a named field with zero and branches on less-than

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
        """The iFix patch id the body at ``pointer`` tests before its AOT path.

        An iFix-wrapped method loads its patch id into ``ecx`` and calls
        ``IFix.WrappersManagerImpl.IsPatched`` in its prologue.
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

    def body(self, type_name: str, method: str, method_arguments: list[str] | None = None) -> Body:
        pointers = sorted(self.pointers_by_name.get(f"{type_name}.{method}") or [])
        if method_arguments is not None:
            pointers = [
                pointer for pointer in pointers
                if any(
                    [arg.get("typeName") for arg in (row.get("methodInstantiation") or {}).get("arguments") or []]
                    == list(method_arguments)
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

    def body_with_fragments(self, body: Body) -> list[dict[str, Any]]:
        """A body's rows plus the split-off fragments it jumps to, one level."""
        rows = list(body.rows)
        for row in body.rows:
            match = _JUMP.fullmatch(str(row.get("text") or ""))
            if not match:
                continue
            target = int(match.group(1), 16)
            if body.pointer <= target < body.pointer + body.size or target in self.names_by_pointer:
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


def check_claim(index: BodyIndex, body: Body, claim: dict[str, Any]) -> str | None:
    """Return a bounded failure reason, or ``None`` when the claim holds."""
    rows = body.all_rows
    texts = _texts(rows)
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
            aliases = {"eax"}
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
    return f"unknown claim {sorted(claim)}"


def evaluate(index: BodyIndex, methods: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate every method's claims; return (rows, failures)."""
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for symbol, spec in methods.items():
        try:
            body = index.body(spec["type"], spec["method"], spec.get("methodArguments"))
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
