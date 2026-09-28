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

A profile-guided formatter may split the same switch: it tests its most
frequent tag first and moves the table to a cold section::

    cmp   tag, N-1 ; jne cold      (tag N-1 falls through)
  cold:
    ja    default                  (reuses the hot compare's flags)
    lea / mov / add / jmp          (the same N-entry table)

The table's last entry points back at the hot fall-through, so the cold table
still names every tag (``SpawnerActionData``).

Nothing here is pinned. The formatter is found by name, the table by
instruction shape, and a candidate is accepted only when its entries resolve
one-for-one onto the family's derived wrapper set with no shared targets;
anything else raises. The branch rule was checked on every entry of six
families (ActionBase, PureGetter, ActionHeader, AbilityActionData,
GameCondition, BaseComponentData).

A small union may compile to a linear compare chain instead of a table::

    test tag, tag ; je  branch0
    cmp  tag, 1   ; jne default    (tag 1 falls through)

Each ``test``/``cmp`` on the one tag register pairs an immediate with its
``je`` target or, for ``jne``, its fall-through, and the chain continues on
the not-equal path (``PatrolSubActionData``).  A chain is read only when no
table resolves, is accepted under the same one-for-one rule, and must name
tags ``0..N-1``; any other compare shape (a binary-search tree, a range test)
is refused, not guessed.  A chain has no table, so its ``tableVa`` is
``None``.

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
#: How far into a hot-case split's cold target the table dispatch may start.
COLD_HEAD_BYTES = 40
#: How far past the formatter's entry point a compare chain may start.
CHAIN_SCAN_BYTES = 0x100
#: Bytes decoded at each chain link: one compare plus one conditional jump.
CHAIN_LINK_BYTES = 16


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


def _table_dispatch(blob: bytes, index: int, blob_va: int, image_base: int) -> tuple[int, int] | None:
    """``(mov offset, table rva)`` when ``blob[index]`` ends a table dispatch.

    The shape is ``lea base, [ImageBase]; mov r32, [base + tag*4 + rva];
    add r64, base; jmp r64``, with ``blob`` loaded from ``blob_va``.
    """
    if index < 12 or index + 1 >= len(blob) or blob[index] != 0xFF:
        return None
    if not 0xE0 <= blob[index + 1] <= 0xE7:
        return None
    if blob[index - 3] not in (0x48, 0x49, 0x4C, 0x4D) or blob[index - 2] != 0x03:
        return None
    mov = index - 3 - 7
    if blob[mov] != 0x8B:
        mov -= 1
        if blob[mov + 1] != 0x8B:
            return None
        mov += 1
    modrm, sib = blob[mov + 1], blob[mov + 2]
    if modrm >> 6 != 2 or modrm & 7 != 4 or sib >> 6 != 2:
        return None
    table_rva = struct.unpack_from("<I", blob, mov + 3)[0]
    if not any(
        blob[lea] in (0x48, 0x4C) and blob[lea + 1] == 0x8D and (blob[lea + 2] & 0xC7) == 0x05
        and blob_va + lea + 7 + struct.unpack_from("<i", blob, lea + 3)[0] == image_base
        for lea in range(mov - 7, max(mov - 24, 0), -1)
    ):
        return None
    return mov, table_rva


def _jump_tables(image: NativeImage, start: int) -> list[tuple[int, int]]:
    """Every ``(table_va, entry_count)`` jump table in the scan window."""
    pe = image.pe
    blob = pe.bytes_at_va(start, SCAN_BYTES)
    found: list[tuple[int, int]] = []
    position = 0
    while (index := blob.find(b"\xff", position)) >= 0:
        position = index + 1
        dispatch = _table_dispatch(blob, index, start, pe.image_base)
        if dispatch is None:
            continue
        mov, table_rva = dispatch
        count = _guard_count(blob, mov)
        if count:
            found.append((pe.image_base + table_rva, count))
    return found


def _hot_case_tables(image: NativeImage, start: int) -> list[tuple[int, int]]:
    """Every ``(table_va, entry_count)`` behind a hot-case split in the window.

    A ``cmp tag, N-1; jne rel32`` qualifies only when its target opens with
    the ``ja`` that reuses those flags, directly followed by the table
    dispatch; the table then has ``N`` entries.
    """
    pe = image.pe
    blob = pe.bytes_at_va(start, SCAN_BYTES)
    found: list[tuple[int, int]] = []
    position = 0
    while (jne := blob.find(b"\x0f\x85", position)) >= 0:
        position = jne + 1
        if jne + 6 > len(blob):
            break
        count = _compare_bound(blob, jne)
        if not count:
            continue
        cold = start + jne + 6 + struct.unpack_from("<i", blob, jne + 2)[0]
        try:
            head = pe.bytes_at_va(cold, COLD_HEAD_BYTES)
        except ValueError:
            continue
        if head[:2] != b"\x0f\x87":
            continue
        for jump in range(6 + 7 + 7 + 3, len(head) - 1):
            dispatch = _table_dispatch(head, jump, cold, pe.image_base)
            if dispatch is not None:
                found.append((pe.image_base + dispatch[1], count))
                break
    return found


def _guard_count(blob: bytes, before: int) -> int | None:
    """The entry count from the ``cmp reg/mem, imm; ja`` guarding the table."""
    for ja in range(before - 1, max(before - 64, 0), -1):
        if blob[ja] != 0x0F or blob[ja + 1] != 0x87:
            continue
        return _compare_bound(blob, ja)
    return None


def _compare_bound(blob: bytes, branch: int) -> int | None:
    """``imm + 1`` of the ``cmp reg/mem, imm`` ending exactly at ``branch``."""
    for back in range(3, 12):
        cmp = branch - back
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
            if cmp + length + width == branch:
                raw = blob[cmp + length:cmp + length + width]
                return int.from_bytes(raw, "little") + 1
    return None


def _entry(image: NativeImage, table_va: int, tag: int) -> SwitchEntry | None:
    pe = image.pe
    target = pe.image_base + struct.unpack("<I", pe.bytes_at_va(table_va + tag * 4, 4))[0]
    return _entry_at(image, target, tag)


def _entry_at(image: NativeImage, target: int, tag: int) -> SwitchEntry | None:
    """The wrapper whose type-usage cell the branch at ``target`` loads first."""
    pe = image.pe
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


def _compare_at(blob: bytes, at: int) -> tuple[tuple[int, int], int, int] | None:
    """``(register, immediate, end)`` of a ``test r,r`` or ``cmp r,imm`` at ``at``.

    Register-direct forms only: ``[66][REX] 85 /r`` with equal operands (an
    immediate of zero), ``[66][REX] 83 /7 ib`` with a non-negative byte,
    ``[66][REX] 81 /7 iw|id`` and ``[66] 3D iw|id``.  The register is its
    operand width and number.
    """
    cursor, width, rex = at, 32, 0
    if cursor < len(blob) and blob[cursor] == 0x66:
        cursor, width = cursor + 1, 16
    if cursor < len(blob) and 0x40 <= blob[cursor] <= 0x4F:
        rex, cursor = blob[cursor], cursor + 1
        width = 64 if rex & 8 else width
    if cursor + 1 >= len(blob):
        return None
    opcode, modrm = blob[cursor], blob[cursor + 1]
    immediate_width = 2 if width == 16 else 4
    if opcode == 0x3D and not rex:
        end = cursor + 1 + immediate_width
        if end > len(blob):
            return None
        return (width, 0), int.from_bytes(blob[cursor + 1:end], "little"), end
    if modrm >> 6 != 3:
        return None
    register = (width, ((rex & 1) << 3) | (modrm & 7))
    if opcode == 0x85:
        if (modrm >> 3) & 7 != modrm & 7 or (rex >> 2) & 1 != rex & 1:
            return None
        return register, 0, cursor + 2
    if (modrm >> 3) & 7 != 7:
        return None
    if opcode == 0x83 and cursor + 2 < len(blob) and blob[cursor + 2] < 0x80:
        return register, blob[cursor + 2], cursor + 3
    if opcode == 0x81:
        end = cursor + 2 + immediate_width
        if end > len(blob):
            return None
        return register, int.from_bytes(blob[cursor + 2:end], "little"), end
    return None


def _equality_jump_at(blob: bytes, at: int, blob_va: int) -> tuple[bool, int, int] | None:
    """``(is_je, target, next)`` of a ``je``/``jne`` (rel8 or rel32) at ``at``."""
    if at + 1 < len(blob) and blob[at] in (0x74, 0x75):
        end = at + 2
        return blob[at] == 0x74, blob_va + end + struct.unpack_from("<b", blob, at + 1)[0], blob_va + end
    if at + 5 < len(blob) and blob[at] == 0x0F and blob[at + 1] in (0x84, 0x85):
        end = at + 6
        return blob[at + 1] == 0x84, blob_va + end + struct.unpack_from("<i", blob, at + 2)[0], blob_va + end
    return None


def _compare_chain(image: NativeImage, start: int, limit: int) -> dict[int, int] | None:
    """``tag -> branch VA`` along the compare chain beginning at ``start``.

    Stops at the first link that is not a compare on the same register
    followed by ``je``/``jne``; ``None`` when a tag repeats.
    """
    pe = image.pe
    branches: dict[int, int] = {}
    register = None
    link = start
    for _ in range(limit):
        try:
            blob = pe.bytes_at_va(link, CHAIN_LINK_BYTES)
        except ValueError:
            break
        compare = _compare_at(blob, 0)
        if compare is None or (register is not None and compare[0] != register):
            break
        jump = _equality_jump_at(blob, compare[2], link)
        if jump is None:
            break
        register, tag = compare[0], compare[1]
        if tag in branches:
            return None
        is_je, target, following = jump
        branches[tag] = target if is_je else following
        link = following if is_je else target
    return branches or None


def _compare_chains(image: NativeImage, start: int, count: int) -> list[tuple[int, dict[int, int]]]:
    """Every ``(chain start, tag -> branch)`` naming exactly tags ``0..count-1``."""
    blob = image.pe.bytes_at_va(start, CHAIN_SCAN_BYTES)
    found = []
    for at in range(len(blob)):
        compare = _compare_at(blob, at)
        if compare is None or _equality_jump_at(blob, compare[2], start) is None:
            continue
        branches = _compare_chain(image, start + at, count + 1)
        if branches is not None and sorted(branches) == list(range(count)):
            found.append((start + at, branches))
    return found


def _resolves_onto(entries: list[SwitchEntry | None], family: set[int]) -> bool:
    """Every entry resolved, one-for-one onto the family, with no shared branch."""
    if any(entry is None for entry in entries):
        return False
    definitions = [entry.type_definition for entry in entries]
    targets = [entry.target_va for entry in entries]
    return set(definitions) == family and len(set(definitions)) == len(entries) == len(set(targets))


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
    tables = _jump_tables(image, dispatcher)
    tables += [table for table in _hot_case_tables(image, dispatcher) if table not in tables]
    accepted = []
    for table_va, count in tables:
        if count != len(family):
            continue
        entries = [_entry(image, table_va, tag) for tag in range(count)]
        if _resolves_onto(entries, family):
            accepted.append((table_va, entries))
    if not accepted:
        seen: set[tuple[tuple[int, int], ...]] = set()
        for _start, branches in _compare_chains(image, dispatcher, len(family)):
            entries = [_entry_at(image, branches[tag], tag) for tag in range(len(family))]
            signature = tuple(sorted(branches.items()))
            if signature not in seen and _resolves_onto(entries, family):
                seen.add(signature)
                accepted.append((None, entries))
    if len(accepted) != 1:
        raise UnionDispatchError(
            f"{base}: expected one jump table or compare chain resolving onto its "
            f"{len(family)} wrappers, found {len(accepted)}"
        )
    table_va, entries = accepted[0]
    return {
        "base": base,
        "dispatcherVa": hex(dispatcher),
        "tableVa": None if table_va is None else hex(table_va),
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
