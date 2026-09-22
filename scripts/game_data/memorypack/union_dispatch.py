"""Read a MemoryPack union's tag assignment from its native formatter switch.

A union base's generated formatter, ``<Base>+<Base>Formatter.Deserialize``,
reads the compact tag and dispatches through one MSVC jump table::

    cmp   tag, N-1 ; ja default
    lea   base, [ImageBase]
    mov   r32, [base + tag*4 + tableRva]
    add   r64, base
    jmp   r64

Each entry reaches, through at most one ``e9 rel32`` thunk, a branch whose
first ``mov rdx, [rip+disp32]`` loads the concrete wrapper's type-usage cell.
Resolving every cell names every tag from the build itself -- the evidence the
reviewed per-row contracts recorded one tag at a time.

Nothing here is pinned. The formatter is found by name, the table by
instruction shape, and a candidate is accepted only when its entries resolve
one-for-one onto the family's derived wrapper set with no shared targets;
anything else raises. The branch rule was checked on every entry of six
families (ActionBase, PureGetter, ActionHeader, AbilityActionData,
GameCondition, BaseComponentData). Smaller unions compile to compare chains
rather than a jump table and are refused, not guessed.

Run as: python -m scripts.game_data.memorypack.union_dispatch --base NAME
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.memorypack.wrapper_members import WrapperType, derive_from_image

WRAPPER_NAMESPACE = "Beyond.MemoryPack."
#: How far past the formatter's entry point a jump table is looked for. The
#: accepted table must still resolve onto the family exactly, so a table that
#: belongs to a neighbouring function cannot be taken by mistake.
SCAN_BYTES = 0x20000
BRANCH_SCAN_BYTES = 96


class UnionDispatchError(RuntimeError):
    """The switch could not be read unambiguously, so nothing is returned."""


@dataclass(frozen=True)
class SwitchEntry:
    tag: int
    wrapper_name: str
    type_definition: int
    target_va: int
    body_va: int
    usage_cell_va: int
    registered_type_index: int

    def row(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "wrapperName": self.wrapper_name,
            "typeDefinition": self.type_definition,
            "targetVa": hex(self.target_va),
            "bodyVa": hex(self.body_va),
            "usageCellVa": hex(self.usage_cell_va),
            "registeredTypeIndex": self.registered_type_index,
        }


def _family(wrappers: dict[int, WrapperType], base: str) -> set[int]:
    by_name = {wrapper.name: definition for definition, wrapper in wrappers.items()}
    root = by_name.get(base)
    if root is None:
        raise UnionDispatchError(f"union base wrapper not found: {base}")
    members = set()
    for definition, wrapper in wrappers.items():
        parent, seen = wrapper.parent_type_definition, set()
        while parent is not None and parent not in seen:
            seen.add(parent)
            if parent == root:
                members.add(definition)
                break
            parent = wrappers[parent].parent_type_definition if parent in wrappers else None
    return members


def _formatter_deserialize_va(image: NativeImage, base: str) -> int:
    short = base.rsplit(".", 1)[-1]
    owner = f"{base}+{short}Formatter"
    metadata = image.metadata
    matches = [
        method for method in metadata.methods
        if metadata.string(method.name_index) == "Deserialize"
        and image.type_name(method.declaring_type) == owner
    ]
    if len(matches) != 1:
        raise UnionDispatchError(f"{owner}.Deserialize: expected one method, found {len(matches)}")
    return image.method_pointer_va(matches[0])


def _jump_tables(image: NativeImage, start: int) -> list[tuple[int, int]]:
    """Every ``(table_va, entry_count)`` jump table in the scan window."""
    pe = image.pe
    blob = pe.bytes_at_va(start, SCAN_BYTES)
    found: list[tuple[int, int]] = []
    position = 0
    while (index := blob.find(b"\xff", position)) >= 0:
        position = index + 1
        if index < 12 or index + 1 >= len(blob) or not 0xE0 <= blob[index + 1] <= 0xE7:
            continue
        if blob[index - 3] not in (0x48, 0x49, 0x4C, 0x4D) or blob[index - 2] != 0x03:
            continue
        mov = index - 3 - 7
        if blob[mov] != 0x8B:
            mov -= 1
            if blob[mov + 1] != 0x8B:
                continue
            mov += 1
        modrm, sib = blob[mov + 1], blob[mov + 2]
        if modrm >> 6 != 2 or modrm & 7 != 4 or sib >> 6 != 2:
            continue
        table_rva = struct.unpack_from("<I", blob, mov + 3)[0]
        if not any(
            blob[lea] in (0x48, 0x4C) and blob[lea + 1] == 0x8D and (blob[lea + 2] & 0xC7) == 0x05
            and start + lea + 7 + struct.unpack_from("<i", blob, lea + 3)[0] == pe.image_base
            for lea in range(mov - 7, max(mov - 24, 0), -1)
        ):
            continue
        count = _guard_count(blob, mov)
        if count:
            found.append((pe.image_base + table_rva, count))
    return found


def _guard_count(blob: bytes, before: int) -> int | None:
    """The entry count from the ``cmp reg/mem, imm; ja`` guarding the table."""
    for ja in range(before - 1, max(before - 64, 0), -1):
        if blob[ja] != 0x0F or blob[ja + 1] != 0x87:
            continue
        for back in range(3, 12):
            cmp = ja - back
            if cmp < 0:
                return None
            opcode = blob[cmp]
            if opcode == 0x3D and back == 5:
                return struct.unpack_from("<I", blob, cmp + 1)[0] + 1
            if opcode in (0x81, 0x83) and (blob[cmp + 1] >> 3) & 7 == 7:
                mod, rm = blob[cmp + 1] >> 6, blob[cmp + 1] & 7
                length = {3: 2, 1: 4 if rm == 4 else 3, 0: 3 if rm == 4 else 2}.get(mod)
                if length is None:
                    continue
                width = 4 if opcode == 0x81 else 1
                if cmp + length + width == ja:
                    raw = blob[cmp + length:cmp + length + width]
                    return int.from_bytes(raw, "little") + 1
        return None
    return None


def _entry(image: NativeImage, table_va: int, tag: int) -> SwitchEntry | None:
    pe = image.pe
    target = pe.image_base + struct.unpack("<I", pe.bytes_at_va(table_va + tag * 4, 4))[0]
    body = target
    head = pe.bytes_at_va(target, 5)
    if head[0] == 0xE9:
        body = target + 5 + struct.unpack("<i", head[1:])[0]
    code = pe.bytes_at_va(body, BRANCH_SCAN_BYTES)
    load = code.find(b"\x48\x8b\x15")
    if load < 0:
        return None
    usage = body + load + 7 + struct.unpack("<i", code[load + 3:load + 7])[0]
    registration = image.registration
    try:
        index = unresolved_usage_index(
            pe.bytes_at_va(usage, 8), registration["typesCount"], tag=1,
            source=str(image.gameassembly), offset=usage,
        )
    except ValueError:
        return None
    type_pointer = pe.u64_at_va(int(registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", pe.bytes_at_va(type_pointer, 16))[0]
    return SwitchEntry(
        tag=tag, wrapper_name=image.type_name(definition), type_definition=definition,
        target_va=target, body_va=body, usage_cell_va=usage, registered_type_index=index,
    )


def read_union_switch(
    image: NativeImage,
    base: str,
    *,
    wrappers: dict[int, WrapperType] | None = None,
) -> dict[str, Any]:
    """Every tag of ``base``'s union, read from its formatter switch."""
    base = base if base.startswith(WRAPPER_NAMESPACE) else WRAPPER_NAMESPACE + base
    wrappers = wrappers if wrappers is not None else derive_from_image(image)
    family = _family(wrappers, base)
    dispatcher = _formatter_deserialize_va(image, base)
    accepted = []
    for table_va, count in _jump_tables(image, dispatcher):
        if count != len(family):
            continue
        entries = [_entry(image, table_va, tag) for tag in range(count)]
        if any(entry is None for entry in entries):
            continue
        definitions = [entry.type_definition for entry in entries]
        targets = [entry.target_va for entry in entries]
        if set(definitions) == family and len(set(definitions)) == count and len(set(targets)) == count:
            accepted.append((table_va, entries))
    if len(accepted) != 1:
        raise UnionDispatchError(
            f"{base}: expected one jump table resolving onto its {len(family)} wrappers, "
            f"found {len(accepted)}"
        )
    table_va, entries = accepted[0]
    return {
        "base": base,
        "dispatcherVa": hex(dispatcher),
        "tableVa": hex(table_va),
        "entryCount": len(entries),
        "entries": [entry.row() for entry in entries],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="union base wrapper type, e.g. Beyond_Gameplay_Actions_PureGetterForMemoryPack")
    args = parser.parse_args(argv)
    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        print(json.dumps({"status": native.status, "detail": native.detail}))
        return 1
    try:
        result = read_union_switch(NativeImage(native.gameassembly, native.metadata, label="unionDispatch"), args.base)
    except UnionDispatchError as error:
        print(json.dumps({"status": "failed", "detail": str(error)}))
        return 1
    print(json.dumps({"status": "validated", **result}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
