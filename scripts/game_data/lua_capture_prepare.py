"""Derive the EndfieldCapture Lua-VM observer declarations from the installed build.

The Lua VM, lua-protobuf, and luasocket are all compiled into GameAssembly.dll, so
every observable entry point is a managed wrapper resolved by name and followed
through its tail transfer.  Nothing is hardcoded: each address is re-derived from
the selected install, and an address is emitted only after its wrapper body, the
transfer it performs, and the target prologue bytes have all been validated.
Preparation never launches or opens a game process.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_MISMATCHED,
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
    sha256_file,
)
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.method_resolver import (
    MethodSpec,
    ResolverError,
    open_resolver,
)
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfieldCapture.luaVmPreparation.v1"
HEADER_SCHEMA = "endfieldCapture.luaVmBuild.v1"
MANAGED_TYPE = "XLua.LuaDLL.Lua"
PROCESS_NAME = "Endfield.exe"
MODULE_NAME = "GameAssembly.dll"

# Managed wrappers whose native bodies the observer needs.  lua_tolstring,
# lua_type, lua_pushlstring and lua_tonumber are called by the provider, never
# hooked; the remaining three are the transfer sites that reveal the loader, the
# pb opener, and the socket.core opener.  lua_type gates every string read so
# the observer never lets lua_tolstring convert a non-string argument in place,
# and it gates the number read so lua_tonumber is only asked about numbers.
WRAPPERS = (
    "lua_tolstring",
    "lua_pushlstring",
    "lua_type",
    "lua_tonumber",
    "xluaL_loadbuffer",
    "luaopen_pb",
    "luaopen_socket_core",
)

# pb module functions the observer hooks, in activation order.
PB_HOOKS = ("load", "loadfile", "encode", "decode")
# socket.core tcp metatable functions the observer hooks.
TCP_HOOKS = ("receive", "send", "setpeername", "setfd", "getfd")
# Identifier-shaped names only: the pb registration array stores bare Lua names.
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,31}")
PIN_BYTES = 16
LOADER_WINDOW = 256
OPENER_WINDOW = 4096
# The payloads that matter are the xluaL_loadbuffer chunks (observed up to 47 KB)
# and pb.load's serialized FileDescriptorSet: the boot-time descriptor.proto set
# alone is 7,606 bytes, and the game's own schema set is far larger.  A 4 KiB cap
# hides the schema entirely, so the cap is sized for a whole schema blob.
MAX_CHUNK_BYTES = 262144


def prologue_ok(body: bytes) -> bool:
    """True when the first bytes look like an x64 function entry."""
    if len(body) < PIN_BYTES:
        return False
    first = body[0]
    if 0x50 <= first <= 0x5F:  # push r64
        return True
    if first in (0x48, 0x4C) and body[1] == 0x89:  # mov r/m64, r64
        return True
    if first == 0x48 and body[1] == 0x8B:  # mov r64, r/m64
        return True
    # REX-prefixed push (40 57 = push rdi) or REX-prefixed mov.
    if 0x40 <= first <= 0x4F and (0x50 <= body[1] <= 0x5F or body[1] == 0x89):
        return True
    if first == 0x48 and body[1] == 0x83 and body[2] == 0xEC:  # sub rsp, imm8
        return True
    if first == 0x48 and body[1] == 0x81 and body[2] == 0xEC:  # sub rsp, imm32
        return True
    if first == 0x48 and body[1] == 0xB8:  # mov rax, imm64
        return True
    if first == 0xE9 or first == 0xFF:  # thunk
        return True
    return False


class Image:
    """Section-aware reads over the selected GameAssembly.dll."""

    def __init__(self, pe: Any) -> None:
        self.pe = pe
        self.base = pe.image_base
        self.sections: dict[str, dict[str, int]] = {}
        for section in pe.sections:
            if section["rawSize"]:
                self.sections[section["name"]] = section

    def section_of(self, va: int) -> str:
        rva = va - self.base
        for name, section in self.sections.items():
            end = section["virtualAddress"] + max(
                section["virtualSize"], section["rawSize"]
            )
            if section["virtualAddress"] <= rva < end:
                return name
        return ""

    def bytes_at(self, va: int, size: int) -> bytes:
        offset, section, _rva = self.pe.file_offset_for_va(va)
        if offset is None or section not in self.sections:
            return b""
        row = self.sections[section]
        available = row["rawPointer"] + row["rawSize"] - offset
        if available < size:
            return b""
        return self.pe.buf[offset : offset + size]

    def c_string(self, va: int, limit: int = 64) -> str:
        raw = self.bytes_at(va, limit)
        if not raw:
            return ""
        text = raw.split(b"\0", 1)[0]
        if len(text) == 0 or len(text) >= limit:
            return ""
        try:
            decoded = text.decode("ascii")
        except UnicodeDecodeError:
            return ""
        return decoded if decoded.isprintable() else ""

    def u64(self, va: int) -> int:
        raw = self.bytes_at(va, 8)
        return int.from_bytes(raw, "little") if len(raw) == 8 else 0

    def body(self, va: int, window: int) -> tuple[int, bytes]:
        offset, section, _rva = self.pe.file_offset_for_va(va)
        if offset is None or section not in self.sections:
            return 0, b""
        row = self.sections[section]
        available = row["rawPointer"] + row["rawSize"] - offset
        size = min(window, available)
        return offset, self.pe.buf[offset : offset + size]


def transfers(image: Image, va: int, body: bytes) -> list[dict[str, Any]]:
    """Every direct control transfer in a body window, in address order.

    Only ``jmp rel32``/``call rel32`` and ``jmp [rip+disp32]`` are decoded; a
    target is kept only when it lands on a plausible function entry inside the
    image's executable section, which rejects bytes that merely resemble an
    opcode inside an immediate.
    """
    found: list[dict[str, Any]] = []
    text = image.sections.get(".text")
    if text is None:
        return found
    text_start = image.base + text["virtualAddress"]
    text_end = text_start + max(text["virtualSize"], text["rawSize"])

    def keep(target: int) -> bool:
        return text_start <= target < text_end and prologue_ok(
            image.bytes_at(target, PIN_BYTES)
        )

    for offset in range(len(body) - 4):
        opcode = body[offset]
        if opcode in (0xE8, 0xE9):
            delta = int.from_bytes(body[offset + 1 : offset + 5], "little", signed=True)
            target = va + offset + 5 + delta
            if keep(target):
                found.append(
                    {
                        "offset": offset,
                        "kind": "call" if opcode == 0xE8 else "jmp",
                        "target": target,
                    }
                )
        elif opcode == 0xFF and (body[offset + 1] & 0xC7) == 0x25:
            delta = int.from_bytes(body[offset + 2 : offset + 6], "little", signed=True)
            slot = va + offset + 6 + delta
            target = image.u64(slot)
            if keep(target):
                found.append(
                    {"offset": offset, "kind": "jmp-indirect", "target": target,
                     "slot": slot}
                )
    return found


def rip_lea_targets(image: Image, va: int, body: bytes) -> list[int]:
    """RIP-relative ``lea r64, [rip+disp32]`` targets in address order.

    ``4? 8D <modrm mod=00 rm=101> disp32`` is unambiguous enough to scan without
    a full length decoder, and every candidate is then classified by section.
    """
    targets: list[int] = []
    offset = 0
    while offset + 8 <= len(body):
        first = body[offset]
        rex = 0x40 <= first <= 0x4F
        index = offset + 1 if rex else offset
        if index + 6 > len(body):
            break
        if body[index] != 0x8D:
            offset += 1
            continue
        modrm = body[index + 1]
        if (modrm >> 6) != 0x00 or (modrm & 0x07) != 0x05:
            offset += 1
            continue
        delta = int.from_bytes(body[index + 2 : index + 6], "little", signed=True)
        targets.append(va + index + 6 + delta)
        offset = index + 6
    return targets


def resolve_wrapper(image: Image, resolver: Any, name: str) -> dict[str, Any]:
    """Managed wrapper row: metadata index, body VA, and body bytes."""
    row = resolver.resolve(MethodSpec(MANAGED_TYPE, name))
    if row.get("status") != "exact":
        raise ValueError(
            f"wrapper {MANAGED_TYPE}.{name} status={row.get('status')} "
            f"is not an exact unique match"
        )
    matches = row.get("matches") or []
    if len(matches) != 1:
        raise ValueError(
            f"wrapper {MANAGED_TYPE}.{name} matched {len(matches)} methods"
        )
    described = matches[0]
    if described.get("bodyStatus") != "resolved":
        raise ValueError(
            f"wrapper {MANAGED_TYPE}.{name} bodyStatus="
            f"{described.get('bodyStatus')}"
        )
    va = int(described["methodPointerVa"], 16)
    extent = int(described["bodyExtent"])
    _offset, body = image.body(va, extent)
    if len(body) < 5:
        raise ValueError(f"wrapper {MANAGED_TYPE}.{name} body is unreadable")
    return {
        "method": name,
        "declaringType": described["declaringType"],
        "methodIndex": described["methodIndex"],
        "token": described["token"],
        "wrapperVa": f"0x{va:x}",
        "wrapperRva": f"0x{va - image.base:x}",
        "bodyExtent": extent,
        "bodyBytes": body[:PIN_BYTES].hex(),
        "va": va,
        "body": body,
    }


def thunk_jump(image: Image, va: int, body: bytes) -> int | None:
    """First ``jmp rel32`` in a thunk body.

    Argument-preparing thunks (``lua_tonumber`` zeroing ``pisnum`` before
    jumping to ``lua_tonumberx``) do not start with a prologue, so the byte
    scan is only accepted when the jump lands in ``.text`` and the instruction
    is followed by int3 padding.
    """
    for offset in range(len(body) - 5):
        if body[offset] != 0xE9:
            continue
        delta = int.from_bytes(body[offset + 1:offset + 5], "little", signed=True)
        target = va + offset + 5 + delta
        if image.section_of(target) != ".text":
            continue
        if body[offset + 5] != 0xCC:
            continue
        return target
    return None


def follow_native(image: Image, wrapper: dict[str, Any]) -> dict[str, Any]:
    """The single native function a wrapper tail-transfers to.

    A wrapper can land on an argument-preparing thunk first: ``lua_tonumber``
    jumps to ``lua_tonumberx`` with ``pisnum`` zeroed.  The walk follows chained
    jumps until it reaches a real prologue, and records the thunks it skipped.
    """
    direct = [item for item in transfers(image, wrapper["va"], wrapper["body"])
              if item["kind"] in ("jmp", "jmp-indirect")]
    if len(direct) == 1:
        target = direct[0]["target"]
        kind = direct[0]["kind"]
    else:
        target = thunk_jump(image, wrapper["va"], wrapper["body"])
        if target is None:
            raise ValueError(
                f"wrapper {wrapper['method']} has {len(direct)} tail transfers, "
                "expected exactly one"
            )
        kind = "jmp-thunk"
    chain: list[int] = []
    for _ in range(3):
        if prologue_ok(image.bytes_at(target, PIN_BYTES)):
            break
        chain.append(target)
        nxt = thunk_jump(image, target, image.bytes_at(target, 32))
        if nxt is None:
            raise ValueError(
                f"wrapper {wrapper['method']} native target is not a prologue"
            )
        target = nxt
    else:
        raise ValueError(
            f"wrapper {wrapper['method']} native target is not a prologue"
        )
    wrapper["nativeVa"] = f"0x{target:x}"
    wrapper["nativeRva"] = f"0x{target - image.base:x}"
    wrapper["nativeBytes"] = image.bytes_at(target, PIN_BYTES).hex()
    wrapper["transfer"] = kind
    wrapper["thunkChain"] = [f"0x{value:x}" for value in chain]
    wrapper["native"] = target
    return wrapper


def derive_loader(image: Image, wrapper: dict[str, Any]) -> dict[str, Any]:
    """The native chunk loader behind ``xluaL_loadbuffer``.

    The wrapper marshals the managed byte[] first, so the string helper is the
    first executable transfer and the loader is the last one.
    """
    window = wrapper["body"][:LOADER_WINDOW]
    ordered = transfers(image, wrapper["va"], window)
    if len(ordered) < 2:
        raise ValueError(
            f"xluaL_loadbuffer body exposes {len(ordered)} executable transfers, "
            "expected a helper call and a loader transfer"
        )
    helper, loader = ordered[0], ordered[-1]
    if helper["target"] == loader["target"]:
        raise ValueError("xluaL_loadbuffer helper and loader are the same target")
    wrapper["stringHelperVa"] = f"0x{helper['target']:x}"
    wrapper["stringHelperRva"] = f"0x{helper['target'] - image.base:x}"
    wrapper["nativeVa"] = f"0x{loader['target']:x}"
    wrapper["nativeRva"] = f"0x{loader['target'] - image.base:x}"
    wrapper["nativeBytes"] = image.bytes_at(loader["target"], PIN_BYTES).hex()
    wrapper["transfer"] = loader["kind"]
    wrapper["native"] = loader["target"]
    wrapper["transfers"] = [
        {"offset": item["offset"], "kind": item["kind"],
         "target": f"0x{item['target']:x}"}
        for item in ordered
    ]
    return wrapper


def stack_frame(body: bytes) -> int:
    """Offset from the adjusted ``rsp`` to ``rbp`` in the function prologue."""
    lea = body.find(b"\x48\x8d\x6c\x24")  # lea rbp, [rsp+disp8]
    wide = body.find(b"\x48\x8d\xac\x24")  # lea rbp, [rsp+disp32]
    if lea < 0 and wide < 0:
        return 0
    if 0 <= lea < wide or wide < 0:
        frame = int.from_bytes(body[lea + 4 : lea + 5], "little", signed=True)
    else:
        lea = wide
        frame = int.from_bytes(body[lea + 4 : lea + 8], "little", signed=True)
    sub8 = body.find(b"\x48\x83\xec")     # sub rsp, imm8
    sub32 = body.find(b"\x48\x81\xec")    # sub rsp, imm32
    subs = [position for position in (sub8, sub32) if position >= 0]
    if not subs:
        return frame
    after = [position for position in subs if position >= lea]
    sub = min(after) if after else min(subs)
    adjust = (body[sub + 3] if sub == sub8
              else int.from_bytes(body[sub + 3 : sub + 7], "little"))
    # ``lea rbp, [rsp+d]`` before ``sub rsp, n`` leaves rbp n bytes high.
    return adjust + frame if sub >= lea else frame


def stack_slots(image: Image, va: int, body: bytes) -> dict[int, int]:
    """Stack slots the function fills with RIP-relative addresses.

    Each ``lea reg,[rip+d]`` is paired with the following
    ``mov [rsp|rbp+d],reg`` of the same register, which recovers the array the
    registration is built in without a full length decoder.
    """
    frame = stack_frame(body)
    leas: list[tuple[int, int, int]] = []
    offset = 0
    while offset + 7 <= len(body):
        first = body[offset]
        rex = 0x40 <= first <= 0x4F
        index = offset + 1 if rex else offset
        if index + 6 <= len(body) and body[index] == 0x8D:
            modrm = body[index + 1]
            if (modrm >> 6) == 0x00 and (modrm & 0x07) == 0x05:
                delta = int.from_bytes(body[index + 2 : index + 6], "little",
                                       signed=True)
                register = ((modrm >> 3) & 0x07) | (0x08 if rex and (first & 0x04) else 0)
                leas.append((index, register, va + index + 6 + delta))
                offset = index + 6
                continue
        offset += 1
    slots: dict[int, int] = {}
    used: set[int] = set()
    offset = 0
    while offset + 5 <= len(body):
        first = body[offset]
        rex = 0x40 <= first <= 0x4F
        index = offset + 1 if rex else offset
        if index + 4 <= len(body) and body[index] == 0x89:
            modrm = body[index + 1]
            mode = modrm >> 6
            rm = modrm & 0x07
            base_is_rbp = False
            extra = 0
            if mode in (0x01, 0x02):
                if rm == 0x05:  # [rbp+disp]; REX.B would mean r13
                    if rex and (first & 0x01):
                        offset += 1
                        continue
                    base_is_rbp = True
                elif rm == 0x04 and index + 2 < len(body):
                    sib = body[index + 2]
                    if (sib & 0x07) != 0x04 or ((sib >> 3) & 0x07) != 0x04:
                        offset += 1
                        continue
                    extra = 1  # SIB byte precedes the displacement
                else:
                    offset += 1
                    continue
                width = (2 if mode == 0x01 else 6) + extra
                if index + width <= len(body):
                    disp_at = index + 2 + extra
                    disp = (int.from_bytes(body[disp_at : disp_at + 1], "little", signed=True)
                            if mode == 0x01 else
                            int.from_bytes(body[disp_at : disp_at + 4], "little", signed=True))
                    register = ((modrm >> 3) & 0x07) | (0x08 if rex and (first & 0x04) else 0)
                    slot = disp + frame if base_is_rbp else disp
                    for position, candidate, target in reversed(leas):
                        if position in used or candidate != register:
                            continue
                        if position >= index or index - position > 40:
                            continue
                        used.add(position)
                        slots[slot] = target
                        break
                    offset = index + width
                    continue
        offset += 1
    return slots


def pb_tables(image: Image, opener_va: int) -> list[dict[str, Any]]:
    """The registration arrays the pb opener builds on the stack.

    The opener fills consecutive 8-byte stack slots with the name/function
    pairs, so the arrays are recovered from the slots themselves: a run of
    adjacent slots whose entries alternate ``.rdata`` identifier and ``.text``
    function is a registration, and the NULL terminator ends it. The module
    table is the run carrying every ``PB_HOOKS`` name; the ``pb.State``
    metatable is the ``__gc``-keyed run registered alongside it.
    """
    _offset, body = image.body(opener_va, OPENER_WINDOW)
    if len(body) < 64:
        raise ValueError("pb opener body is unreadable")
    slots = stack_slots(image, opener_va, body)
    if len(slots) < 2 * len(PB_HOOKS):
        raise ValueError(f"pb opener fills only {len(slots)} stack slots")
    ordered = sorted(slots)
    runs: list[list[int]] = [[ordered[0]]]
    for slot in ordered[1:]:
        if slot - runs[-1][-1] == 8:
            runs[-1].append(slot)
        else:
            runs.append([slot])
    tables: list[dict[str, Any]] = []
    for run in runs:
        rows: list[dict[str, Any]] = []
        index = 0
        while index + 1 < len(run):
            name_va = slots[run[index]]
            function = slots[run[index + 1]]
            name = (image.c_string(name_va)
                    if image.section_of(name_va) == ".rdata" else "")
            if (IDENTIFIER.fullmatch(name) and image.section_of(function) == ".text"
                    and prologue_ok(image.bytes_at(function, PIN_BYTES))):
                rows.append({
                    "name": name,
                    "nameVa": f"0x{name_va:x}",
                    "va": f"0x{function:x}",
                    "rva": f"0x{function - image.base:x}",
                    "bytes": image.bytes_at(function, PIN_BYTES).hex(),
                    "slot": f"0x{run[index]:x}",
                })
                index += 2
                continue
            index += 1
        names = [row["name"] for row in rows]
        if all(hook in names for hook in PB_HOOKS):
            tables.append({"table": "pb", "rows": rows})
        elif "__gc" in names and "__tostring" not in names:
            tables.append({"table": "pb.State", "rows": rows})
    if not any(table["table"] == "pb" for table in tables):
        raise ValueError("no stack slot run carries the pb registration array")
    rows = [row for table in tables for row in table["rows"]]
    names = [row["name"] for row in rows]
    if len(set(names)) != len(names):
        raise ValueError("pb registration names are not unique")
    return tables


def tcp_table(image: Image, opener_va: int) -> list[dict[str, Any]]:
    """The socket.core tcp ``luaL_Reg`` array in ``.data``.

    ``setpeername`` appears in two luasocket registration arrays: the generic
    socket object (where it is an alias of ``connect``) and the tcp metatable.
    Its ``.rdata`` string is the anchor, every ``.data`` qword pointing at it is
    walked into a complete array, and the tcp metatable is the one exposing
    ``receivefrom``/``sendto`` with ``setpeername`` as its own entry.
    """
    rdata = image.sections.get(".rdata")
    data = image.sections.get(".data")
    if rdata is None or data is None:
        raise ValueError("GameAssembly.dll has no .rdata/.data section")
    needle = b"setpeername\0"
    rdata_start = rdata["rawPointer"]
    rdata_end = rdata_start + rdata["rawSize"]
    hits: list[int] = []
    position = rdata_start
    while True:
        found = image.pe.buf.find(needle, position, rdata_end)
        if found < 0:
            break
        hits.append(image.base + rdata["virtualAddress"] + (found - rdata_start))
        position = found + 1
    if len(hits) != 1:
        raise ValueError(f"setpeername string appears {len(hits)} times in .rdata")
    anchor = hits[0]
    packed = struct.pack("<Q", anchor)
    data_start = data["rawPointer"]
    data_end = data_start + data["rawSize"]
    slots: list[int] = []
    position = data_start
    while True:
        found = image.pe.buf.find(packed, position, data_end)
        if found < 0:
            break
        slots.append(image.base + data["virtualAddress"] + (found - data_start))
        position = found + 1
    if not slots:
        raise ValueError("no .data qword references the setpeername string")

    def valid(address: int) -> str:
        name_va = image.u64(address)
        function = image.u64(address + 8)
        if image.section_of(name_va) != ".rdata":
            return ""
        if image.section_of(function) != ".text":
            return ""
        name = image.c_string(name_va)
        if not IDENTIFIER.fullmatch(name) or not prologue_ok(
            image.bytes_at(function, PIN_BYTES)
        ):
            return ""
        return name

    _offset, opener_body = image.body(opener_va, OPENER_WINDOW)
    opener_targets = set(rip_lea_targets(image, opener_va, opener_body))
    tables: list[dict[str, Any]] = []
    seen: set[int] = set()
    for entry in slots:
        start = entry
        while valid(start - 16):
            start -= 16
        if start in seen:
            continue
        seen.add(start)
        rows: list[dict[str, Any]] = []
        cursor = start
        while True:
            name = valid(cursor)
            if not name:
                break
            function = image.u64(cursor + 8)
            rows.append({
                "name": name,
                "nameVa": f"0x{image.u64(cursor):x}",
                "va": f"0x{function:x}",
                "rva": f"0x{function - image.base:x}",
                "bytes": image.bytes_at(function, PIN_BYTES).hex(),
            })
            cursor += 16
        names = [row["name"] for row in rows]
        if not rows or "setpeername" not in names:
            continue
        by_name = {row["name"]: row["va"] for row in rows}
        aliased = by_name.get("connect") == by_name.get("setpeername")
        tables.append({
            "start": start,
            "rows": rows,
            "complete": all(hook in names for hook in TCP_HOOKS),
            "tcp": (not aliased and "receivefrom" in names and "sendto" in names
                    and "connect" not in names),
            "referenced": start in opener_targets,
        })
    tcp_arrays = [table for table in tables if table["tcp"] and table["complete"]]
    if len(tcp_arrays) == 1:
        chosen = tcp_arrays[0]
    else:
        raise ValueError(
            f"socket.core tcp luaL_Reg is ambiguous: {len(tables)} arrays carry "
            f"setpeername, {len(tcp_arrays)} are tcp metatables (starts: "
            + ", ".join(hex(table["start"]) for table in tables) + ")"
        )
    for row in chosen["rows"]:
        row["tableVa"] = f"0x{chosen['start']:x}"
        row["referencedByOpener"] = chosen["referenced"]
    return chosen["rows"]


def compare_candidate(profile: dict[str, Any], path: Path) -> dict[str, Any]:
    """Compare the derived table with the offline candidate report, if present."""
    if not path.is_file():
        return {"status": "absent", "path": str(path)}
    candidate = json.loads(path.read_text(encoding="utf-8"))
    derived = profile["nativeTargets"]
    reproduced: list[str] = []
    differing: dict[str, dict[str, str]] = {}
    for label, value in (candidate.get("nativeTargets") or {}).items():
        wanted = str(value).lower()
        if label in derived and derived[label].lower() == wanted:
            reproduced.append(label)
        else:
            differing[label] = {"candidate": wanted,
                                "derived": derived.get(label, "absent")}
    addresses = {value.lower() for value in derived.values()}
    missing = [label for label, value in (candidate.get("nativeTargets") or {}).items()
               if str(value).lower() not in addresses]
    return {
        "status": "compared",
        "path": str(path),
        "reproduced": len(reproduced),
        "differing": differing,
        "candidateAddresses": len(candidate.get("nativeTargets") or {}),
        "candidateAddressesReproduced": (len(candidate.get("nativeTargets") or {})
                                         - len(missing)),
        "candidateAddressesMissing": missing,
    }


def prepare(game_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    gameassembly = game_dir / "GameAssembly.dll"
    metadata = game_dir / "Endfield_Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    native = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise NativeInputsUnvalidated(native)
    resolver, receipt = open_resolver(gameassembly=gameassembly, metadata=metadata)
    image = Image(resolver.pe)

    wrappers: dict[str, dict[str, Any]] = {}
    for name in WRAPPERS:
        wrappers[name] = resolve_wrapper(image, resolver, name)
    for name in ("lua_tolstring", "lua_pushlstring", "lua_type", "lua_tonumber",
                 "luaopen_pb", "luaopen_socket_core"):
        follow_native(image, wrappers[name])
    derive_loader(image, wrappers["xluaL_loadbuffer"])

    pb = [dict(row, table=entry["table"])
          for entry in pb_tables(image, wrappers["luaopen_pb"]["native"])
          for row in entry["rows"]]
    tcp = tcp_table(image, wrappers["luaopen_socket_core"]["native"])
    pb_by_name = {row["name"]: row for row in pb}
    tcp_by_name = {row["name"]: row for row in tcp}

    targets: dict[str, str] = {
        "lua_tolstring": wrappers["lua_tolstring"]["nativeVa"],
        "lua_pushlstring": wrappers["lua_pushlstring"]["nativeVa"],
        "xluaL_loadbuffer": wrappers["xluaL_loadbuffer"]["nativeVa"],
        "il2cpp_e2u_string_helper": wrappers["xluaL_loadbuffer"]["stringHelperVa"],
        "luaopen_pb": wrappers["luaopen_pb"]["nativeVa"],
        "luaopen_socket_core": wrappers["luaopen_socket_core"]["nativeVa"],
    }
    for row in pb:
        targets[f"{row['table']}.{row['name']}"] = row["va"]
    for row in tcp:
        targets[f"tcp.{row['name']}"] = row["va"]

    hooks: list[dict[str, Any]] = []
    for role, abi in (
        ("xluaL_loadbuffer", "lua.loadbuffer.v1"),
        ("pb.load", "lua.pb.load.v1"),
        ("pb.loadfile", "lua.pb.loadfile.v1"),
        ("pb.encode", "lua.pb.encode.v1"),
        ("pb.decode", "lua.pb.decode.v1"),
        ("tcp.receive", "lua.tcp.receive.v1"),
        ("tcp.send", "lua.tcp.send.v1"),
        ("tcp.setpeername", "lua.tcp.setpeername.v1"),
        ("tcp.setfd", "lua.tcp.setfd.v1"),
        ("tcp.getfd", "lua.tcp.getfd.v1"),
    ):
        row = {
            "role": role,
            "module": MODULE_NAME,
            "abiId": abi,
            "va": targets[role],
            "rva": f"0x{int(targets[role], 16) - image.base:x}",
            "bytes": image.bytes_at(int(targets[role], 16), PIN_BYTES).hex(),
        }
        hooks.append(row)

    profile = {
        "schema": SCHEMA,
        "status": NATIVE_EVIDENCE_VALIDATED,
        "offlineOnly": True,
        "processName": PROCESS_NAME,
        "moduleName": MODULE_NAME,
        "imageBase": f"0x{image.base:x}",
        "gameBuild": f"endfield-gameassembly-{native.gameassembly_sha256[:8]}",
        "files": {
            "gameAssembly": {
                "relativePath": "GameAssembly.dll",
                "bytes": gameassembly.stat().st_size,
                "sha256": native.gameassembly_sha256,
            },
            "metadata": {
                "relativePath": "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
                "bytes": metadata.stat().st_size,
                "sha256": native.metadata_sha256,
            },
        },
        "nativeInputs": receipt,
        "managedWrappers": {
            name: {key: value for key, value in row.items()
                   if key not in ("va", "body")}
            for name, row in wrappers.items()
        },
        "pbRegistrations": pb,
        "tcpRegistrations": tcp,
        "nativeTargets": targets,
        "hooks": hooks,
        "declared": {
            "lua_tolstring": wrappers["lua_tolstring"]["nativeRva"],
            "lua_pushlstring": wrappers["lua_pushlstring"]["nativeRva"],
            "lua_type": wrappers["lua_type"]["nativeRva"],
            "lua_tonumberx": wrappers["lua_tonumber"]["nativeRva"],
        },
        "limits": {"maxChunkBytes": MAX_CHUNK_BYTES, "pinBytes": PIN_BYTES},
    }
    return profile, native


class NativeInputsUnvalidated(RuntimeError):
    def __init__(self, result: Any) -> None:
        super().__init__(f"{result.status}: {result.detail}")
        self.result = result


def header(profile: dict[str, Any], profile_path: Path) -> str:
    lines = [
        "#pragma once",
        "// Generated by scripts/game_data/lua_capture_prepare.py. Do not edit.",
        "#include <array>",
        "#include <cstdint>",
        "namespace lua_vm_capture::build {",
        f'inline constexpr const char* schema = "{HEADER_SCHEMA}";',
        f'inline constexpr const char* process_name = "{profile["processName"]}";',
        f'inline constexpr const char* module_name = "{profile["moduleName"]}";',
        f'inline constexpr const char* game_build = "{profile["gameBuild"]}";',
        f'inline constexpr std::uint64_t gameassembly_bytes = '
        f'{profile["files"]["gameAssembly"]["bytes"]}ULL;',
        f'inline constexpr const char* gameassembly_sha256 = '
        f'"{profile["files"]["gameAssembly"]["sha256"]}";',
        f'inline constexpr std::uint64_t metadata_bytes = '
        f'{profile["files"]["metadata"]["bytes"]}ULL;',
        f'inline constexpr const char* metadata_sha256 = '
        f'"{profile["files"]["metadata"]["sha256"]}";',
        "struct Pin { const char* role; std::uint32_t rva; const char* bytes; };",
        "inline constexpr Pin hooks[] = {",
    ]
    for row in profile["hooks"]:
        lines.append(
            '{"' + row["role"] + '", ' + str(int(row["rva"], 16)) + ', "'
            + row["bytes"] + '"},'
        )
    lines += [
        "};",
        f'inline constexpr unsigned hook_count = {len(profile["hooks"])};',
        "inline constexpr Pin declared[] = {",
    ]
    for name, rva in profile["declared"].items():
        lines.append('{"' + name + '", ' + str(int(rva, 16)) + ', nullptr},')
    lines += [
        "};",
        f'inline constexpr unsigned declared_count = {len(profile["declared"])};',
        f'inline constexpr unsigned max_chunk_bytes = {profile["limits"]["maxChunkBytes"]};',
        f'inline constexpr unsigned pin_bytes = {profile["limits"]["pinBytes"]};',
        f'inline constexpr const wchar_t* profile_path = '
        f'L{json.dumps(str(profile_path).replace(chr(92), "/"))};',
        f'inline constexpr const char* profile_sha256 = '
        f'"{sha256_file(profile_path)}";',
        "}",
    ]
    return "\n".join(lines) + "\n"


def failure_report(status: str, detail: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "offlineOnly": True,
        "diagnostic": detail[:1600],
        "addressesEmitted": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="generated lua_vm_build.h")
    parser.add_argument("--report", type=Path, required=True,
                        help="preparation report JSON")
    parser.add_argument("--compare", type=Path,
                        default=REPO_ROOT / "reports/game_data/network/lua_vm_targets.json")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    report_path = args.report.resolve()
    # Generated declarations are artifacts; never route them into a source tree.
    for path in (output, report_path):
        if not any(path.is_relative_to(REPO_ROOT / root)
                   for root in ("reports", "tmp", "scratch")):
            parser.error("--output and --report must stay under reports/, tmp/ or scratch/")
    try:
        profile, native = prepare(args.game_dir.resolve())
        profile["candidateComparison"] = compare_candidate(profile, args.compare)
        atomic_write_text(report_path, json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
        atomic_write_text(output, header(profile, report_path))
        report = {
            "schema": "endfieldCapture.luaVmPreparationReport.v1",
            "status": NATIVE_EVIDENCE_VALIDATED,
            "offlineOnly": True,
            "gameBuild": profile["gameBuild"],
            "gameAssemblySha256": native.gameassembly_sha256,
            "metadataSha256": native.metadata_sha256,
            "hooks": len(profile["hooks"]),
            "pbRegistrations": len(profile["pbRegistrations"]),
            "tcpRegistrations": len(profile["tcpRegistrations"]),
            "declared": len(profile["declared"]),
            "addressesEmitted": len(profile["nativeTargets"]),
            "candidateComparison": profile["candidateComparison"],
            "profile": str(report_path),
            "profileSha256": sha256_file(report_path),
            "header": str(output),
            "headerSha256": sha256_file(output),
        }
    except NativeInputsUnvalidated as exc:
        report = failure_report(exc.result.status, str(exc))
        atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report))
        return 1
    except (OSError, ValueError, KeyError, ResolverError) as exc:
        report = failure_report(NATIVE_EVIDENCE_MISMATCHED, str(exc))
        atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report))
        return 1
    atomic_write_text(report_path.parent / "preparation-report.json",
                      json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
