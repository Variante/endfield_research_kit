"""Recognize the installed build's inline patch-table entry guard.

Installed IL2CPP wrappers no longer call ``IFix.WrappersManagerImpl.IsPatched``
in their prologue. Each wrapped body instead loads one RIP-addressed root cell,
reads a per-family patch table from ``[root+tableDisp]`` and, when that table is
nonnull, enters a cold block that loads a function pointer from
``[table+slotDisp]``. A null function pointer branches back to the ordinary
fall-through; a nonnull one is called with ``[table+slotDisp+8]`` as its first
argument and the original arguments shifted, and its result is returned.

This module proves only that guard shape from instruction bytes:

* the root cell lies in zero-initialized (unbacked) storage of a writable
  section, so it is runtime-written and anonymous -- no stored table exists in
  the image;
* the guard instructions and their exact encodings, permitting only plain
  register-to-register parameter aliases (``MOV r64,r64`` or a zero-extending
  ``MOVZX r32,r8`` of a Bool argument) interleaved between the root load and
  the table load (they may not write RAX or RCX);
* the cold block's slot load, null test, and null edge back to the guard's
  fall-through, so both unpatched selections (null table or null slot) reach the
  same ordinary entry.

It does not prove which tables or slots are populated at runtime, who writes
the root, or what a patched replacement does. Callers that follow the ordinary
fall-through must state that selection as ``conditional``.
"""
from __future__ import annotations

import re
import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.context import rip_qword_load_target

# x86-64 register-number order, used to build the expected ModRM byte.
GENERAL = ('rax', 'rcx', 'rdx', 'rbx', 'rsp', 'rbp', 'rsi', 'rdi',
           'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15')


class PatchTableGuardError(ValueError):
    pass


def _require(value: bool, check: str, expected: Any, actual: Any) -> None:
    if not value:
        raise PatchTableGuardError(f'patch-table-{check}: expected={expected!r} actual={actual!r}')


def _register_move_bytes(destination: str, source: str) -> bytes:
    """MOV r64, r64 in the 8B /r form the compiler emits."""
    d = GENERAL.index(destination); s = GENERAL.index(source)
    rex = 0x48 | (0x04 if d >= 8 else 0) | (0x01 if s >= 8 else 0)
    return bytes([rex, 0x8b, 0xc0 | ((d & 7) << 3) | (s & 7)])


DWORD = ('eax', 'ecx', 'edx', 'ebx', 'esp', 'ebp', 'esi', 'edi',
         *(f'r{n}d' for n in range(8, 16)))
BYTE = ('al', 'cl', 'dl', 'bl', 'spl', 'bpl', 'sil', 'dil',
        *(f'r{n}b' for n in range(8, 16)))


def _zero_extend_byte_bytes(destination: int, source: int) -> bytes:
    """MOVZX r32, r8 (0F B6 /r); REX when an extended or SPL..DIL byte register."""
    rex = 0x40 | (0x04 if destination >= 8 else 0) | (0x01 if source >= 8 else 0)
    body = bytes([0x0f, 0xb6, 0xc0 | ((destination & 7) << 3) | (source & 7)])
    return (bytes([rex]) if rex != 0x40 or 4 <= source < 8 else b'') + body


def _alias(row: dict) -> tuple[str, str, bytes] | None:
    """Parameter alias row as (destination r64, source name, expected bytes)."""
    if match := re.fullmatch(r'mov (\w+), (\w+)', row['text']):
        destination, source = match.groups()
        if destination in GENERAL and source in GENERAL:
            return destination, source, _register_move_bytes(destination, source)
    if match := re.fullmatch(r'movzx (\w+), (\w+)', row['text']):
        destination, source = match.groups()
        if destination in DWORD and source in BYTE:
            d = DWORD.index(destination); s = BYTE.index(source)
            return GENERAL[d], source, _zero_extend_byte_bytes(d, s)
    return None


def _base_disp_load(raw: bytes, *, rex: int, reg: int, base: int) -> int | None:
    """Displacement of ``MOV r64,[base+disp8/32]`` with fixed REX/reg/base."""
    if len(raw) == 4 and raw[:2] == bytes([rex, 0x8b]) and raw[2] == 0x40 | (reg << 3) | base:
        return raw[3] if raw[3] < 0x80 else None
    if len(raw) == 7 and raw[:2] == bytes([rex, 0x8b]) and raw[2] == 0x80 | (reg << 3) | base:
        value = struct.unpack_from('<i', raw, 3)[0]
        return value if value >= 0 else None
    return None


def zero_initialized_cell(pe, cell: int) -> dict:
    """The writable section holding ``cell`` beyond its raw file bytes."""
    for section in pe.sections:
        start = pe.image_base + section['virtualAddress']
        if start <= cell and cell + 8 <= start + section['virtualSize']:
            _require(bool(section['characteristics'] & 0x80000000), 'root-writable',
                     'writable section', section['name'])
            _require(cell >= start + section['rawSize'], 'root-unbacked',
                     'zero-initialized storage beyond raw bytes', hex(cell))
            return {'section': section['name'], 'rootCell': hex(cell)}
    raise PatchTableGuardError(f'patch-table-root-section: expected=mapped section actual={cell:#x}')


def check_entry_guard(rows: list[dict], position: int, *, pe,
                      decode: Callable[[int, int], list[dict]]) -> dict:
    """Prove the guard starting at ``rows[position]``.

    ``rows`` are contiguous decoded rows (``va``, ``bytes``, ``text``) and
    ``decode(pointer, size)`` decodes the cold block. Returns the guard facts,
    the parameter aliases established between the loads, and the index of the
    first row after the guard's conditional branch (the ordinary entry).
    """
    def raw(row):
        return bytes.fromhex(row['bytes'])

    load = rows[position]
    load_raw = raw(load)
    _require(load_raw[:3] == b'\x48\x8b\x05', 'root-load', 'mov rax,[rip+disp32]', load_raw.hex())
    cell = rip_qword_load_target(load_raw, int(load['va'], 16), source='patchTableGuard')
    storage = zero_initialized_cell(pe, cell)
    aliases = {}
    interleaved = []
    at = position + 1
    while True:
        _require(at < len(rows), 'table-load', 'present', 'end of rows')
        row = rows[at]
        alias = _alias(row)
        if alias is None:
            # Vector save/copy rows may be scheduled between the root load and
            # the table load; they touch neither RAX nor RCX.
            if re.fullmatch(r'movaps (\[rsp\+0x[0-9a-f]+\]|xmm\d+), xmm\d+', row['text']) and raw(row)[:1] in (b'\x0f', b'\x44'):
                interleaved.append(row['text'])
                at += 1
                continue
            break
        destination, source, expected = alias
        source_full = GENERAL[BYTE.index(source)] if source in BYTE else source
        _require(destination not in ('rax', 'rcx', 'rsp') and source_full not in ('rax', 'rsp')
                 and destination not in aliases and source_full not in aliases,
                 'alias', 'fresh register copy of an incoming register', row['text'])
        _require(raw(row) == expected, 'alias-encoding', expected.hex(), raw(row).hex())
        aliases[destination] = source
        at += 1
    table_disp = _base_disp_load(raw(rows[at]), rex=0x48, reg=1, base=0)
    _require(table_disp is not None and table_disp % 8 == 0, 'table-load',
             'mov rcx,[rax+aligned disp]', rows[at]['text'])
    _require(at + 2 < len(rows) and raw(rows[at + 1]) == b'\x48\x85\xc9', 'table-test',
             'test rcx,rcx', rows[at + 1]['text'] if at + 1 < len(rows) else None)
    branch = rows[at + 2]; branch_raw = raw(branch)
    branch_va = int(branch['va'], 16)
    if len(branch_raw) == 6 and branch_raw[:2] == b'\x0f\x85':
        cold = branch_va + 6 + struct.unpack_from('<i', branch_raw, 2)[0]
    elif len(branch_raw) == 2 and branch_raw[0] == 0x75:
        cold = branch_va + 2 + struct.unpack_from('<b', branch_raw, 1)[0]
    else:
        raise PatchTableGuardError(f'patch-table-branch: expected=jne actual={branch_raw.hex()}')
    fallthrough = branch_va + len(branch_raw)
    cold_rows = decode(cold, 16)
    _require(len(cold_rows) >= 3, 'cold-block', 'slot load, test, branch', len(cold_rows))
    # The slot function pointer lands in R10 or RAX; the test names the same register.
    for slot_register, rex, number, slot_test in (('r10', 0x4c, 2, b'\x4d\x85\xd2'), ('rax', 0x48, 0, b'\x48\x85\xc0')):
        slot_disp = _base_disp_load(raw(cold_rows[0]), rex=rex, reg=number, base=1)
        if slot_disp is not None:
            break
    _require(slot_disp is not None and slot_disp % 8 == 0, 'slot-load',
             'mov r10|rax,[rcx+aligned disp]', cold_rows[0]['text'])
    _require(raw(cold_rows[1]) == slot_test, 'slot-test', f'test {slot_register},{slot_register}', cold_rows[1]['text'])
    null_raw = raw(cold_rows[2]); null_va = int(cold_rows[2]['va'], 16)
    if len(null_raw) == 6 and null_raw[:2] == b'\x0f\x84':
        null_target = null_va + 6 + struct.unpack_from('<i', null_raw, 2)[0]
    elif len(null_raw) == 2 and null_raw[0] == 0x74:
        null_target = null_va + 2 + struct.unpack_from('<b', null_raw, 1)[0]
    else:
        raise PatchTableGuardError(f'patch-table-slot-branch: expected=je actual={null_raw.hex()}')
    _require(null_target == fallthrough, 'slot-null-edge', hex(fallthrough), hex(null_target))
    return {**storage, 'tableDisplacement': table_disp, 'slotDisplacement': slot_disp,
            'slotRegister': slot_register, 'coldEntry': hex(cold), 'ordinaryEntry': hex(fallthrough),
            'aliases': aliases, 'interleavedVectorRows': interleaved, 'nextPosition': at + 3,
            'selection': 'unpatched: null table or null slot function (anonymous runtime state)'}
