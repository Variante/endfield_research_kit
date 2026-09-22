"""Name the direct calls a method body makes, on the selected build.

A native contract that says "A calls B, then C" is only portable if B and C
are recorded by name. This module turns a body into that form: it scans the
body for ``E8 rel32`` calls and names each target by reverse lookup over every
registered method pointer -- ordinary methods through each image's pointer
array, generic instantiations through the metadata registration's generic
method table. A byte that merely looks like ``E8`` inside another instruction
almost never lands exactly on a registered method start, and a target that
names nothing is reported unnamed rather than guessed.

Nothing is pinned; everything is read from the ``NativeImage`` given.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from scripts.game_data.il2cpp.context import method_spec_record
from scripts.game_data.il2cpp.native_image import NativeImage


@dataclass(frozen=True)
class DirectCall:
    offset: int
    target_va: int
    names: tuple[str, ...]

    def row(self) -> dict[str, Any]:
        return {"offset": self.offset, "targetVa": hex(self.target_va), "targets": list(self.names)}


class CallGraph:
    def __init__(self, image: NativeImage) -> None:
        self.image = image

    def _method_name(self, index: int) -> str:
        metadata = self.image.metadata
        method = metadata.methods[index]
        return f"{self.image.type_name(method.declaring_type)}.{metadata.string(method.name_index)}"

    @cached_property
    def names_by_pointer(self) -> dict[int, tuple[str, ...]]:
        image, pe, metadata = self.image, self.image.pe, self.image.metadata
        found: dict[int, list[str]] = {}
        arrays: dict[str, bytes] = {}
        for index, method in enumerate(metadata.methods):
            owner = metadata.string(metadata.images[image.owners[method.declaring_type]].name_index)
            if owner not in arrays:
                module = image.modules[owner]
                count = pe.u32_at_va(module + 8)
                arrays[owner] = pe.bytes_at_va(pe.u64_at_va(module + 16), count * 8)
            slot = (method.token & 0x00FFFFFF) - 1
            pointers = arrays[owner]
            if 0 <= slot < len(pointers) // 8:
                pointer = struct.unpack_from("<Q", pointers, slot * 8)[0]
                if pointer:
                    found.setdefault(pointer, []).append(self._method_name(index))
        registration = image.registration
        code = image.mapper.code_registration_summary(pe, image.code_registration)
        specs_base = int(registration["methodSpecs"], 16)
        table_base = int(registration["genericMethodTable"], 16)
        table = pe.bytes_at_va(table_base, registration["genericMethodTableCount"] * 16)
        for row in range(registration["genericMethodTableCount"]):
            spec_index = struct.unpack_from("<i", table, row * 16)[0]
            if not 0 <= spec_index < registration["methodSpecsCount"]:
                continue
            definition, _class_inst, _method_inst = method_spec_record(
                pe.bytes_at_va(specs_base + spec_index * 12, 12), len(metadata.methods),
                registration["genericInstsCount"], source=str(image.gameassembly),
                offset=specs_base + spec_index * 12)
            # Rows may carry an adjustor thunk index; only the method pointer
            # index matters for naming a call target.
            pointer_index = struct.unpack_from("<i", table, row * 16 + 4)[0]
            if not 0 <= pointer_index < code["genericMethodPointersCount"]:
                continue
            pointer = pe.u64_at_va(int(code["genericMethodPointers"], 16) + pointer_index * 8)
            if pointer and 0 <= definition < len(metadata.methods):
                found.setdefault(pointer, []).append(self._method_name(definition) + "<generic>")
        return {pointer: tuple(sorted(set(names))) for pointer, names in found.items()}

    def field_loads_before(self, start_va: int, calls: list[DirectCall], callee: str,
                           field_offset: int, window: int = 0x40) -> int:
        """How many calls to ``callee`` are preceded by ``mov rcx, [reg+field_offset]``."""
        displacement = struct.pack("<i", field_offset)
        # REX.W 8B /r with mod=10, reg=rcx: ``mov rcx, [base+disp32]``.
        patterns = [bytes([0x48, 0x8B, 0x88 | base]) + displacement for base in range(8)]
        count = 0
        for call in calls:
            if not calls_named(call, callee):
                continue
            start = max(call.offset - window, 0)
            region = self.image.pe.bytes_at_va(start_va + start, call.offset - start)
            if any(pattern in region for pattern in patterns):
                count += 1
        return count

    def direct_calls(self, start_va: int, size: int) -> list[DirectCall]:
        """Every ``E8 rel32`` in ``[start, start+size)`` whose target is a method start."""
        body = self.image.pe.bytes_at_va(start_va, size)
        calls = []
        for offset in range(len(body) - 4):
            if body[offset] != 0xE8:
                continue
            target = start_va + offset + 5 + struct.unpack_from("<i", body, offset + 1)[0]
            names = self.names_by_pointer.get(target)
            if names:
                calls.append(DirectCall(offset, target, names))
        return calls


def calls_named(call: DirectCall, suffix: str) -> bool:
    """Whether a call's target names a method ending in ``suffix``."""
    return any(name.removesuffix("<generic>").endswith(suffix) for name in call.names)


def first_missing_in_order(calls: list[DirectCall], callees: list[str]) -> str | None:
    """The first of ``callees`` not found after its predecessor, or ``None``."""
    cursor = 0
    for callee in callees:
        while cursor < len(calls) and not calls_named(calls[cursor], callee):
            cursor += 1
        if cursor == len(calls):
            return callee
        cursor += 1
    return None


def loaded_literals(graph: CallGraph, start_va: int, size: int) -> set[str]:
    """String literals whose usage cells the body loads with ``mov r64, [rip+disp32]``."""
    image = graph.image
    pe, metadata = image.pe, image.metadata
    literal_section = metadata.sections["stringLiteral"]
    data_section = metadata.sections["stringLiteralData"]
    body = pe.bytes_at_va(start_va, size)
    found: set[str] = set()
    for offset in range(size - 6):
        if body[offset] not in (0x48, 0x4C) or body[offset + 1] != 0x8B or (body[offset + 2] & 0xC7) != 0x05:
            continue
        cell = start_va + offset + 7 + struct.unpack_from("<i", body, offset + 3)[0]
        try:
            word = pe.u64_at_va(cell)
        except ValueError:
            continue
        if word > 0xFFFFFFFF or not word & 1 or word >> 29 != 5:
            continue
        index = (word >> 1) & 0x0FFFFFFF
        if index >= literal_section.size // 8:
            continue
        length, start = struct.unpack_from("<ii", metadata.buf, literal_section.offset + index * 8)
        found.add(metadata.buf[data_section.offset + start:data_section.offset + start + length]
                  .decode("utf-8", "replace"))
    return found
