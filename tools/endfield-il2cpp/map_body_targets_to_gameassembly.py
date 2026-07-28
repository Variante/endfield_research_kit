#!/usr/bin/env python3
"""
Map IL2CPP metadata body targets to GameAssembly.dll method pointers.

This is a deliberately small static helper. It does not need
MetadataRegistration, Il2CppDumper, Cpp2IL, or a running game process. It uses
the CodeRegistration address found by Cpp2IL, reads the per-module
Il2CppCodeGenModule method-pointer tables, and joins those slots back to the
metadata method indexes emitted by `catalog_option_flow_metadata.py`.

Usage:
  python tools/endfield-il2cpp/map_body_targets_to_gameassembly.py
  python tools/endfield-il2cpp/map_body_targets_to_gameassembly.py --catalog reports/story/recovery/options/option_flow_runtime_metadata.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import struct
import sys
from collections import Counter
from bisect import bisect_right
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_METADATA = Path("export_full/recovered/il2cpp/global-metadata.dat")
DEFAULT_CATALOG = Path("reports/story/recovery/options/option_flow_runtime_metadata_focus.json")
DEFAULT_JSON = Path("reports/story/recovery/options/option_flow_body_targets_gameassembly.json")
DEFAULT_MD = Path("reports/story/recovery/options/option_flow_body_targets_gameassembly.md")
# CodeRegistration VA is build-specific (HGP relocates it each GameAssembly build).
# Current value is for the July-11 install. When a game update breaks the mapping
# (symptom: "VA outside image" in parse_codegen_modules), re-derive it with
# scratch/reverse_engineering/il2cpp_gameplay_sim/stage0/find_code_registration.py and update here.
# Prior build was 0x18C439740.
DEFAULT_CODE_REGISTRATION = 0x18B9217D0
# MetadataRegistration is likewise build-specific. It is only needed to name
# generic method instantiations, which live in CodeRegistration.genericMethodPointers
# rather than in the per-image Il2CppCodeGenModule tables. Without it, every call
# into a generic instantiation reports as an unresolved address, which silently
# understates the coverage of any direct-call census. Re-derive with
# find_metadata_registration() after a game update.
DEFAULT_METADATA_REGISTRATION = 0x18B921C30
DEFAULT_BODY_SUMMARY_METHOD_RE = (
    r"GenPlayable|InitDialogOptions|"
    r"DialogChooseOption|DialogTimelineDoNext|DialogTimelineGetAllTimelinePlayable|"
    r"DialogTimelineGetAllActiveClips|DialogTimelineDisableLoopInRange|"
    r"TryTriggerTrunkBindingOption|_TryDoNext|_SelectIndexInTimeline|"
    r"SelectIndex|OnJumpForward|SetDialogOption|ResetDialogOption|"
    r"TryGetJumpClip|DoJump|DoReverseJump|_CheckIfTimeJumping|_TrySelectBranch"
)
ARG_GP_REGISTERS = ("rcx", "rdx", "r8", "r9")
ARG_XMM_REGISTERS = ("xmm0", "xmm1", "xmm2", "xmm3")
ARG_REGISTERS = ARG_GP_REGISTERS + ARG_XMM_REGISTERS


def load_catalog_module() -> Any:
    path = Path(__file__).with_name("catalog_option_flow_metadata.py")
    spec = importlib.util.spec_from_file_location("endfield_il2cpp_catalog", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load catalog helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PeImage:
    def __init__(self, path: Path):
        self.path = path
        self.buf = path.read_bytes()
        pe_offset = self.u32_at_file(0x3C)
        if self.u32_at_file(pe_offset) != 0x00004550:
            raise ValueError(f"not a PE image: {path}")
        coff = pe_offset + 4
        self.section_count = self.u16_at_file(coff + 2)
        optional_size = self.u16_at_file(coff + 16)
        optional = coff + 20
        magic = self.u16_at_file(optional)
        if magic != 0x20B:
            raise ValueError("only PE32+ x64 images are supported")
        self.image_base = self.u64_at_file(optional + 24)
        section_offset = optional + optional_size
        self.sections: list[dict[str, Any]] = []
        for index in range(self.section_count):
            off = section_offset + index * 40
            name = self.buf[off:off + 8].split(b"\0", 1)[0].decode("ascii", errors="replace")
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", self.buf, off + 8
            )
            self.sections.append(
                {
                    "name": name,
                    "virtualAddress": virtual_address,
                    "virtualSize": virtual_size,
                    "rawPointer": raw_pointer,
                    "rawSize": raw_size,
                }
            )

    def u16_at_file(self, offset: int) -> int:
        return struct.unpack_from("<H", self.buf, offset)[0]

    def u32_at_file(self, offset: int) -> int:
        return struct.unpack_from("<I", self.buf, offset)[0]

    def u64_at_file(self, offset: int) -> int:
        return struct.unpack_from("<Q", self.buf, offset)[0]

    def file_offset_for_rva(self, rva: int) -> tuple[int | None, str]:
        for section in self.sections:
            start = section["virtualAddress"]
            size = max(section["virtualSize"], section["rawSize"])
            if start <= rva < start + size:
                return section["rawPointer"] + (rva - start), section["name"]
        return None, ""

    def file_offset_for_va(self, va: int) -> tuple[int | None, str, int]:
        rva = va - self.image_base
        file_offset, section = self.file_offset_for_rva(rva)
        return file_offset, section, rva

    def u32_at_va(self, va: int) -> int:
        offset, _, _ = self.file_offset_for_va(va)
        if offset is None:
            raise ValueError(f"VA outside image: 0x{va:x}")
        return self.u32_at_file(offset)

    def u64_at_va(self, va: int) -> int:
        offset, _, _ = self.file_offset_for_va(va)
        if offset is None:
            raise ValueError(f"VA outside image: 0x{va:x}")
        return self.u64_at_file(offset)

    def bytes_at_va(self, va: int, size: int) -> bytes:
        offset, _, _ = self.file_offset_for_va(va)
        if offset is None:
            return b""
        return self.buf[offset:offset + size]

    def c_string_at_va(self, va: int, *, limit: int = 512) -> str:
        offset, _, _ = self.file_offset_for_va(va)
        if offset is None:
            return f"<bad-va:0x{va:x}>"
        end = self.buf.find(b"\0", offset, offset + limit)
        if end < 0:
            end = offset + limit
        return self.buf[offset:end].decode("utf-8", errors="replace")


def parse_int(value: str) -> int:
    return int(value, 0)


def code_registration_summary(pe: PeImage, code_registration_va: int) -> dict[str, Any]:
    # Unity 2021 IL2CPP CodeRegistration layout:
    # count/pointer pairs for reverse P/Invoke and generic methods, then a
    # pointer-only generic adjustor thunk table, then more count/pointer pairs.
    return {
        "va": f"0x{code_registration_va:x}",
        "reversePInvokeWrapperCount": pe.u32_at_va(code_registration_va),
        "reversePInvokeWrappers": f"0x{pe.u64_at_va(code_registration_va + 0x08):x}",
        "genericMethodPointersCount": pe.u32_at_va(code_registration_va + 0x10),
        "genericMethodPointers": f"0x{pe.u64_at_va(code_registration_va + 0x18):x}",
        "genericAdjustorThunks": f"0x{pe.u64_at_va(code_registration_va + 0x20):x}",
        "invokerPointersCount": pe.u32_at_va(code_registration_va + 0x28),
        "invokerPointers": f"0x{pe.u64_at_va(code_registration_va + 0x30):x}",
        "unresolvedVirtualCallCount": pe.u32_at_va(code_registration_va + 0x38),
        "unresolvedVirtualCallPointers": f"0x{pe.u64_at_va(code_registration_va + 0x40):x}",
        "interopDataCount": pe.u32_at_va(code_registration_va + 0x48),
        "interopData": f"0x{pe.u64_at_va(code_registration_va + 0x50):x}",
        "windowsRuntimeFactoryCount": pe.u32_at_va(code_registration_va + 0x58),
        "windowsRuntimeFactoryTable": f"0x{pe.u64_at_va(code_registration_va + 0x60):x}",
        "codeGenModulesCount": pe.u32_at_va(code_registration_va + 0x68),
        "codeGenModules": f"0x{pe.u64_at_va(code_registration_va + 0x70):x}",
    }


def parse_codegen_modules(pe: PeImage, code_registration_va: int) -> dict[str, dict[str, Any]]:
    module_count = pe.u32_at_va(code_registration_va + 0x68)
    module_table_va = pe.u64_at_va(code_registration_va + 0x70)
    modules: dict[str, dict[str, Any]] = {}
    for index in range(module_count):
        module_va = pe.u64_at_va(module_table_va + index * 8)
        name = pe.c_string_at_va(pe.u64_at_va(module_va))
        modules[name] = {
            "index": index,
            "moduleVa": module_va,
            "methodPointerCount": pe.u32_at_va(module_va + 0x08),
            "methodPointersVa": pe.u64_at_va(module_va + 0x10),
            "adjustorThunkCount": pe.u32_at_va(module_va + 0x18),
            "adjustorThunksVa": pe.u64_at_va(module_va + 0x20),
            "invokerIndicesVa": pe.u64_at_va(module_va + 0x28),
        }
    return modules


def image_method_ranges(md: Any) -> dict[str, dict[str, int]]:
    ranges: dict[str, dict[str, int]] = {}
    for image in md.images:
        starts: list[int] = []
        ends: list[int] = []
        for type_index in range(image.type_start, image.type_start + image.type_count):
            type_def = md.types[type_index]
            if type_def.method_count <= 0 or type_def.method_start < 0:
                continue
            starts.append(type_def.method_start)
            ends.append(type_def.method_start + type_def.method_count)
        ranges[md.string(image.name_index)] = {
            "typeStart": image.type_start,
            "typeCount": image.type_count,
            "methodStart": min(starts) if starts else -1,
            "methodEnd": max(ends) if ends else -1,
            "methodCount": sum(end - start for start, end in zip(starts, ends)),
        }
    return ranges


def method_signature(md: Any, method_index: int) -> dict[str, Any]:
    method = md.methods[method_index]
    type_def = md.types[method.declaring_type]
    return {
        "methodIndex": method_index,
        "type": md.type_full_name(type_def),
        "method": md.string(method.name_index),
        "token": f"0x{method.token:08x}",
    }


def build_pointer_indexes(
    pe: PeImage,
    md: Any,
    modules: dict[str, dict[str, Any]],
    ranges: dict[str, dict[str, int]],
) -> tuple[dict[str, list[int]], dict[int, list[dict[str, Any]]]]:
    pointers_by_image: dict[str, list[int]] = {}
    method_by_pointer: dict[int, list[dict[str, Any]]] = {}
    for image_name, module in modules.items():
        image_range = ranges.get(image_name)
        if image_range is None or image_range["methodStart"] < 0:
            continue
        method_count = min(module["methodPointerCount"], image_range["methodCount"])
        pointers: list[int] = []
        for slot in range(method_count):
            ptr = pe.u64_at_va(module["methodPointersVa"] + slot * 8)
            pointers.append(ptr)
            method_index = image_range["methodStart"] + slot
            if ptr and method_index < len(md.methods):
                method_by_pointer.setdefault(ptr, []).append(method_signature(md, method_index))
        pointers_by_image[image_name] = pointers
    return pointers_by_image, method_by_pointer


METADATA_REGISTRATION_FIELDS = (
    "genericClasses",
    "genericInsts",
    "genericMethodTable",
    "types",
    "methodSpecs",
    "fieldOffsets",
    "typeDefinitionsSizes",
    "metadataUsages",
)
# Il2CppGenericMethodFunctionsDefinitions on this build is
# (genericMethodIndex, methodIndex, invokerIndex, adjustorThunkIndex).
GENERIC_METHOD_TABLE_STRIDE = 16
# Il2CppMethodSpec is (methodDefinitionIndex, classIndexIndex, methodIndexIndex).
METHOD_SPEC_STRIDE = 12


def metadata_registration_summary(pe: PeImage, metadata_registration_va: int) -> dict[str, Any]:
    """Read the count/pointer pairs of Il2CppMetadataRegistration."""
    summary: dict[str, Any] = {"va": f"0x{metadata_registration_va:x}"}
    for index, name in enumerate(METADATA_REGISTRATION_FIELDS):
        base = metadata_registration_va + index * 0x10
        summary[f"{name}Count"] = pe.u32_at_va(base)
        summary[name] = f"0x{pe.u64_at_va(base + 8):x}"
    return summary


def metadata_registration_is_plausible(pe: PeImage, candidate_va: int) -> bool:
    """Reject candidates whose table pointers fall outside the image."""
    try:
        summary = metadata_registration_summary(pe, candidate_va)
    except (ValueError, struct.error):
        return False
    for name in METADATA_REGISTRATION_FIELDS:
        pointer = int(summary[name], 16)
        if not pointer:
            continue
        file_offset, _, _ = pe.file_offset_for_va(pointer)
        if file_offset is None:
            return False
    return True


def find_metadata_registration(pe: PeImage, code_registration_va: int) -> int | None:
    """Locate MetadataRegistration from the codegen registration call site.

    s_Il2CppCodegenRegistration() loads CodeRegistration and MetadataRegistration
    with adjacent rip-relative LEAs. CodeRegistration is already known, so scan
    executable sections for the LEA that resolves to it and validate the nearby
    LEA targets as MetadataRegistration candidates.
    """
    candidates: list[int] = []
    for section in pe.sections:
        if not section["rawSize"]:
            continue
        data = pe.buf[section["rawPointer"]: section["rawPointer"] + section["rawSize"]]
        va_base = pe.image_base + section["virtualAddress"]
        targets: list[tuple[int, int]] = []
        for offset in range(len(data) - 7):
            if data[offset] & 0xF8 != 0x48 or data[offset + 1] != 0x8D:
                continue
            if (data[offset + 2] & 0xC7) != 0x05:
                continue
            disp = struct.unpack_from("<i", data, offset + 3)[0]
            va = va_base + offset
            targets.append((va, va + 7 + disp))
        anchors = [va for va, target in targets if target == code_registration_va]
        if not anchors:
            continue
        for anchor in anchors:
            for va, target in targets:
                if va == anchor or abs(va - anchor) > 0x40:
                    continue
                if target != code_registration_va:
                    candidates.append(target)
    for candidate in candidates:
        if metadata_registration_is_plausible(pe, candidate):
            return candidate
    return None


def build_generic_method_index(
    pe: PeImage,
    md: Any,
    code_registration_va: int,
    metadata_registration_va: int,
) -> dict[int, list[dict[str, Any]]]:
    """Map generic instantiation entry points to their open generic definitions.

    genericMethodPointers[slot] is reached through the genericMethodTable row
    whose indices.methodIndex is that slot; the row's genericMethodIndex selects
    a methodSpec, whose methodDefinitionIndex names the open generic method.
    """
    code_summary = code_registration_summary(pe, code_registration_va)
    pointer_base = int(code_summary["genericMethodPointers"], 16)
    pointer_count = code_summary["genericMethodPointersCount"]
    meta_summary = metadata_registration_summary(pe, metadata_registration_va)
    table_count = meta_summary["genericMethodTableCount"]
    table_offset, _, _ = pe.file_offset_for_va(int(meta_summary["genericMethodTable"], 16))
    spec_offset, _, _ = pe.file_offset_for_va(int(meta_summary["methodSpecs"], 16))
    spec_count = meta_summary["methodSpecsCount"]
    if table_offset is None or spec_offset is None or not pointer_base:
        return {}

    table = pe.buf[table_offset: table_offset + table_count * GENERIC_METHOD_TABLE_STRIDE]
    slot_to_spec: dict[int, int] = {}
    for index in range(table_count):
        generic_method_index, slot = struct.unpack_from(
            "<ii", table, index * GENERIC_METHOD_TABLE_STRIDE
        )
        if 0 <= generic_method_index < spec_count and 0 <= slot < pointer_count:
            slot_to_spec.setdefault(slot, generic_method_index)

    index: dict[int, list[dict[str, Any]]] = {}
    for slot, generic_method_index in slot_to_spec.items():
        pointer = pe.u64_at_va(pointer_base + slot * 8)
        if not pointer:
            continue
        method_definition_index = struct.unpack_from(
            "<i", pe.buf, spec_offset + generic_method_index * METHOD_SPEC_STRIDE
        )[0]
        if not 0 <= method_definition_index < len(md.methods):
            continue
        row = method_signature(md, method_definition_index)
        row["genericInstantiation"] = True
        row["genericMethodPointerSlot"] = slot
        row["methodSpecIndex"] = generic_method_index
        index.setdefault(pointer, []).append(row)
    return index


def generic_body_candidates(
    generic_index: dict[int, list[dict[str, Any]]],
    method_index: int,
) -> list[dict[str, Any]]:
    """Return distinct generic entry points for one open method definition.

    IL2CPP leaves some open generic method slots null in the normal codegen
    module table even though a concrete shipped MethodSpec has an executable
    body in ``genericMethodPointers``.  Group MethodSpecs by entry point so a
    uniquely shared body can be decoded safely while genuinely distinct
    instantiations remain fail-closed.
    """
    by_pointer: dict[int, list[dict[str, Any]]] = {}
    for pointer, rows in generic_index.items():
        matches = [
            dict(row)
            for row in rows
            if int(row.get("methodIndex", -1)) == method_index
        ]
        if matches:
            by_pointer.setdefault(pointer, []).extend(matches)
    return [
        {
            "methodPointerVa": f"0x{pointer:x}",
            "instantiations": rows,
        }
        for pointer, rows in sorted(by_pointer.items())
    ]


def decode_modrm(byte: int) -> tuple[int, int, int]:
    return (byte >> 6) & 0x3, (byte >> 3) & 0x7, byte & 0x7


def signed_hex(value: int) -> str:
    return f"-0x{-value:x}" if value < 0 else f"+0x{value:x}"


def reg_name(code: int, *, width: int = 64) -> str:
    names64 = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
               "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
    names32 = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi",
               "r8d", "r9d", "r10d", "r11d", "r12d", "r13d", "r14d", "r15d"]
    names8 = ["al", "cl", "dl", "bl", "spl", "bpl", "sil", "dil",
              "r8b", "r9b", "r10b", "r11b", "r12b", "r13b", "r14b", "r15b"]
    if width == 8:
        return names8[code]
    return (names64 if width == 64 else names32)[code]


def xmm_name(code: int) -> str:
    return f"xmm{code}"


def canonical_arg_register(name: str) -> str | None:
    aliases = {
        "rcx": "rcx", "ecx": "rcx", "cl": "rcx",
        "rdx": "rdx", "edx": "rdx", "dl": "rdx",
        "r8": "r8", "r8d": "r8", "r8b": "r8",
        "r9": "r9", "r9d": "r9", "r9b": "r9",
        "xmm0": "xmm0", "xmm1": "xmm1", "xmm2": "xmm2", "xmm3": "xmm3",
    }
    return aliases.get(name)


def canonical_register(name: str) -> str:
    aliases = {
        "eax": "rax", "ax": "rax", "al": "rax",
        "ecx": "rcx", "cx": "rcx", "cl": "rcx",
        "edx": "rdx", "dx": "rdx", "dl": "rdx",
        "ebx": "rbx", "bx": "rbx", "bl": "rbx",
        "esp": "rsp", "sp": "rsp", "spl": "rsp",
        "ebp": "rbp", "bp": "rbp", "bpl": "rbp",
        "esi": "rsi", "si": "rsi", "sil": "rsi",
        "edi": "rdi", "di": "rdi", "dil": "rdi",
    }
    if re.fullmatch(r"r\d+d", name):
        return name[:-1]
    if re.fullmatch(r"r\d+b", name):
        return name[:-1]
    return aliases.get(name, name)


def is_register_name(value: str) -> bool:
    return canonical_register(value) in {
        "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
        "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
        "xmm0", "xmm1", "xmm2", "xmm3", "xmm4", "xmm5", "xmm6",
        "xmm7", "xmm8", "xmm9", "xmm10", "xmm11", "xmm12", "xmm13",
        "xmm14", "xmm15",
    }


def read_disp(data: bytes, pos: int, size: int) -> tuple[int, int]:
    if pos + size > len(data):
        return 0, len(data)
    if size == 1:
        return struct.unpack_from("<b", data, pos)[0], pos + 1
    if size == 4:
        return struct.unpack_from("<i", data, pos)[0], pos + 4
    return 0, pos


def rm_operand(
    data: bytes,
    pos: int,
    mod: int,
    rm: int,
    rex_b: int,
    *,
    width: int,
    start_va: int,
    offset: int,
) -> tuple[str, int]:
    rm_code = rm | (rex_b << 3)
    if mod == 3:
        return reg_name(rm_code, width=width), pos
    return format_memory_operand(
        data,
        pos,
        mod,
        rm,
        rex_b,
        start_va=start_va + offset,
        instruction_end_hint=(pos - offset) + (4 if mod in (0, 2) else 1),
    )


def format_memory_operand(
    data: bytes,
    pos: int,
    mod: int,
    rm: int,
    rex_b: int,
    *,
    start_va: int,
    instruction_end_hint: int,
) -> tuple[str, int]:
    base_reg = rm | (rex_b << 3)
    if rm == 4:
        # SIB addressing. Only stringify the common forms; still advance over
        # displacement correctly so later instructions stay aligned.
        sib = data[pos]
        pos += 1
        scale = (sib >> 6) & 0x3
        index = (sib >> 3) & 0x7
        sib_base = sib & 0x7
        base_name = reg_name(sib_base | (rex_b << 3))
        index_name = "" if index == 4 else reg_name(index)
        if mod == 0 and sib_base == 5:
            disp, pos = read_disp(data, pos, 4)
            base = f"0x{disp & 0xffffffff:x}"
        elif mod == 1:
            disp, pos = read_disp(data, pos, 1)
            base = f"{base_name}{signed_hex(disp)}"
        elif mod == 2:
            disp, pos = read_disp(data, pos, 4)
            base = f"{base_name}{signed_hex(disp)}"
        else:
            base = base_name
        if index_name:
            return f"[{base}+{index_name}*{1 << scale}]", pos
        return f"[{base}]", pos
    if mod == 0 and rm == 5:
        disp, pos = read_disp(data, pos, 4)
        rip_target = start_va + instruction_end_hint + disp
        return f"[rip{signed_hex(disp)} => 0x{rip_target:x}]", pos
    base_name = reg_name(base_reg)
    if mod == 1:
        disp, pos = read_disp(data, pos, 1)
        return f"[{base_name}{signed_hex(disp)}]", pos
    if mod == 2:
        disp, pos = read_disp(data, pos, 4)
        return f"[{base_name}{signed_hex(disp)}]", pos
    return f"[{base_name}]", pos


def decode_one_x64(data: bytes, offset: int, start_va: int) -> tuple[dict[str, Any], int]:
    pos = offset
    prefixes = []
    while pos < len(data) and data[pos] in (0x66, 0x67, 0xF0, 0xF2, 0xF3):
        prefixes.append(data[pos])
        pos += 1
    rex = 0
    if pos < len(data) and 0x40 <= data[pos] <= 0x4F:
        rex = data[pos]
        pos += 1
    if pos >= len(data):
        return {"offset": offset, "text": "db", "write": None}, offset + 1
    opcode = data[pos]
    pos += 1
    rex_w = (rex >> 3) & 1
    rex_r = (rex >> 2) & 1
    rex_b = rex & 1
    width = 64 if rex_w else 32

    def result(text: str, write: tuple[str, str] | None, new_pos: int) -> tuple[dict[str, Any], int]:
        return {
            "offset": offset,
            "va": f"0x{start_va + offset:x}",
            "bytes": data[offset:new_pos].hex(" "),
            "text": text,
            "write": {"register": write[0], "value": write[1]} if write else None,
        }, new_pos

    if opcode == 0x90:
        return result("nop", None, pos)
    if opcode == 0xCC:
        return result("int3", None, pos)
    if opcode == 0xC3:
        return result("ret", None, pos)
    if opcode == 0xC2 and pos + 2 <= len(data):
        imm = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        return result(f"ret 0x{imm:x}", None, pos)
    if 0x50 <= opcode <= 0x57:
        reg = (opcode - 0x50) | (rex_b << 3)
        return result(f"push {reg_name(reg)}", None, pos)
    if 0x58 <= opcode <= 0x5F:
        reg = (opcode - 0x58) | (rex_b << 3)
        dst = reg_name(reg)
        return result(f"pop {dst}", (dst, f"pop({dst})"), pos)

    if opcode in (0x8A, 0x88, 0x8B, 0x89, 0x8D, 0x63) and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, reg, rm = decode_modrm(modrm)
        reg_code = reg | (rex_r << 3)
        rm_code = rm | (rex_b << 3)
        if opcode == 0x8A:
            dst = reg_name(reg_code, width=8)
            src, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=8, start_va=start_va, offset=offset,
            )
            return result(f"mov {dst}, {src}", (dst, src), pos)
        if opcode == 0x88:
            src = reg_name(reg_code, width=8)
            dst, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=8, start_va=start_va, offset=offset,
            )
            return result(f"mov {dst}, {src}", (dst, src) if mod == 3 else None, pos)
        if opcode == 0x8B:
            dst = reg_name(reg_code, width=width)
            src, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=width, start_va=start_va, offset=offset,
            )
            return result(f"mov {dst}, {src}", (dst, src), pos)
        if opcode == 0x89:
            src = reg_name(reg_code, width=width)
            dst, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=width, start_va=start_va, offset=offset,
            )
            return result(f"mov {dst}, {src}", (dst, src) if mod == 3 else None, pos)
        if opcode == 0x63:
            dst = reg_name(reg_code, width=64)
            src, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=32, start_va=start_va, offset=offset,
            )
            return result(f"movsxd {dst}, {src}", (dst, src), pos)
        dst = reg_name(reg_code, width=64)
        src, pos = rm_operand(
            data, pos, mod, rm, rex_b,
            width=64, start_va=start_va, offset=offset,
        )
        return result(f"lea {dst}, {src}", (dst, f"&{src}"), pos)

    if opcode in (0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF):
        reg = (opcode - 0xB8) | (rex_b << 3)
        dst = reg_name(reg, width=width)
        if pos + 4 > len(data):
            return result(f"db 0x{opcode:02x}", None, offset + 1)
        imm = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return result(f"mov {dst}, 0x{imm:x}", (dst, f"0x{imm:x}"), pos)

    if 0xB0 <= opcode <= 0xB7 and pos < len(data):
        reg = (opcode - 0xB0) | (rex_b << 3)
        dst = reg_name(reg, width=8)
        imm = data[pos]
        pos += 1
        return result(f"mov {dst}, 0x{imm:x}", (dst, f"0x{imm:x}"), pos)

    if opcode == 0x33 and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, reg, rm = decode_modrm(modrm)
        reg_code = reg | (rex_r << 3)
        rm_code = rm | (rex_b << 3)
        dst = reg_name(reg_code, width=width)
        if mod == 3 and reg_code == rm_code:
            return result(f"xor {dst}, {dst}", (dst, "0"), pos)
        return result(f"xor {dst}, {reg_name(rm_code, width=width) if mod == 3 else 'mem'}", None, pos)

    if opcode in (0x80, 0x81, 0x83) and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, group_op, rm = decode_modrm(modrm)
        op_width = 8 if opcode == 0x80 else width
        dst, pos = rm_operand(
            data, pos, mod, rm, rex_b,
            width=op_width, start_va=start_va, offset=offset,
        )
        if opcode in (0x80, 0x83):
            if pos >= len(data):
                return result(f"db 0x{opcode:02x}", None, offset + 1)
            imm = struct.unpack_from("<b", data, pos)[0]
            pos += 1
        else:
            if pos + 4 > len(data):
                return result(f"db 0x{opcode:02x}", None, offset + 1)
            imm = struct.unpack_from("<i", data, pos)[0]
            pos += 4
        op_name = {
            0: "add",
            1: "or",
            4: "and",
            5: "sub",
            7: "cmp",
        }.get(group_op, f"group{group_op}")
        imm_text = f"-0x{-imm:x}" if imm < 0 else f"0x{imm:x}"
        write = None
        if op_name in {"add", "sub", "and", "or"} and is_register_name(dst):
            if op_name == "or" and imm == -1:
                write = (dst, "-1")
            else:
                write = (dst, f"{dst} {op_name} {imm_text}")
        return result(f"{op_name} {dst}, {imm_text}", write, pos)

    if opcode in (0x84, 0x85, 0x39, 0x3B) and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, reg, rm = decode_modrm(modrm)
        reg_code = reg | (rex_r << 3)
        operand_width = 8 if opcode == 0x84 else width
        reg_operand = reg_name(reg_code, width=operand_width)
        rm_op, pos = rm_operand(
            data, pos, mod, rm, rex_b,
            width=operand_width, start_va=start_va, offset=offset,
        )
        if opcode in (0x84, 0x85):
            return result(f"test {rm_op}, {reg_operand}", None, pos)
        if opcode == 0x39:
            return result(f"cmp {rm_op}, {reg_operand}", None, pos)
        return result(f"cmp {reg_operand}, {rm_op}", None, pos)

    if opcode == 0x3D and pos + 4 <= len(data):
        imm = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        imm_text = f"-0x{-imm:x}" if imm < 0 else f"0x{imm:x}"
        return result(f"cmp eax, {imm_text}", None, pos)

    if opcode in (0xC6, 0xC7) and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, group_op, rm = decode_modrm(modrm)
        if group_op != 0:
            return result(f"db 0x{opcode:02x}", None, offset + 1)
        dst, pos = rm_operand(
            data, pos, mod, rm, rex_b,
            width=8 if opcode == 0xC6 else 32,
            start_va=start_va,
            offset=offset,
        )
        if opcode == 0xC6:
            imm = data[pos]
            pos += 1
        else:
            imm = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        return result(
            f"mov {dst}, 0x{imm:x}",
            (dst, f"0x{imm:x}") if is_register_name(dst) else None,
            pos,
        )

    if opcode in (0x44, 0x45) and pos < len(data):
        # Common two-byte REX-prefixed 32-bit forms such as:
        #   45 33 c0       xor r8d, r8d
        #   44 8b c3       mov r8d, ebx
        nested = bytes([opcode]) + data[pos:pos + 8]
        decoded, used = decode_one_x64(nested, 0, start_va + offset)
        if used > 1:
            decoded["offset"] = offset
            decoded["va"] = f"0x{start_va + offset:x}"
            decoded["bytes"] = data[offset:offset + used].hex(" ")
            return decoded, offset + used

    if opcode == 0xE8 and pos + 4 <= len(data):
        rel = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        target = start_va + pos + rel
        return result(f"call 0x{target:x}", None, pos)

    if opcode == 0xE9 and pos + 4 <= len(data):
        rel = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        return result(f"jmp 0x{start_va + pos + rel:x}", None, pos)

    if ((0x70 <= opcode <= 0x7F) or opcode == 0xEB) and pos < len(data):
        disp = struct.unpack_from("<b", data, pos)[0]
        pos += 1
        mnemonic = {
            0x70: "jo",
            0x71: "jno",
            0x72: "jb",
            0x73: "jae",
            0x74: "je",
            0x75: "jne",
            0x76: "jbe",
            0x77: "ja",
            0x78: "js",
            0x79: "jns",
            0x7A: "jp",
            0x7B: "jnp",
            0x7C: "jl",
            0x7D: "jge",
            0x7E: "jle",
            0x7F: "jg",
            0xEB: "jmp",
        }[opcode]
        return result(f"{mnemonic} 0x{start_va + pos + disp:x}", None, pos)

    if opcode == 0xFF and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, group_op, rm = decode_modrm(modrm)
        operand, pos = rm_operand(
            data, pos, mod, rm, rex_b,
            width=64, start_va=start_va, offset=offset,
        )
        op_name = {0: "inc", 1: "dec", 2: "call", 4: "jmp", 6: "push"}.get(group_op, f"ff/{group_op}")
        return result(f"{op_name} {operand}", None, pos)

    if opcode == 0x0F and pos < len(data):
        op2 = data[pos]
        pos += 1
        if 0x90 <= op2 <= 0x9F and pos < len(data):
            modrm = data[pos]
            pos += 1
            mod, _reg, rm = decode_modrm(modrm)
            dst, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=8, start_va=start_va, offset=offset,
            )
            mnemonic = {
                0x92: "setb",
                0x93: "setae",
                0x94: "sete",
                0x95: "setne",
                0x96: "setbe",
                0x97: "seta",
                0x9C: "setl",
                0x9D: "setge",
                0x9E: "setle",
                0x9F: "setg",
            }.get(op2, f"setcc/{op2:02x}")
            return result(f"{mnemonic} {dst}", (dst, "cc") if is_register_name(dst) else None, pos)
        if op2 == 0xAB and pos < len(data):
            modrm = data[pos]
            pos += 1
            mod, reg, rm = decode_modrm(modrm)
            reg_code = reg | (rex_r << 3)
            src = reg_name(reg_code, width=width)
            dst, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=width, start_va=start_va, offset=offset,
            )
            prefix = "lock " if 0xF0 in prefixes else ""
            return result(f"{prefix}bts {dst}, {src}", None, pos)
        if op2 in (0xB6, 0xB7) and pos < len(data):
            modrm = data[pos]
            pos += 1
            mod, reg, rm = decode_modrm(modrm)
            reg_code = reg | (rex_r << 3)
            dst = reg_name(reg_code, width=width)
            src, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=8 if op2 == 0xB6 else 32,
                start_va=start_va,
                offset=offset,
            )
            return result(f"movzx {dst}, {src}", (dst, src), pos)
        if op2 in (0x2E, 0x2F) and pos < len(data):
            modrm = data[pos]
            pos += 1
            mod, reg, rm = decode_modrm(modrm)
            reg_code = reg | (rex_r << 3)
            left = xmm_name(reg_code)
            right, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=64, start_va=start_va, offset=offset,
            )
            mnemonic = "ucomisd" if op2 == 0x2E else "comisd"
            return result(f"{mnemonic} {left}, {right}", None, pos)
        if op2 in (0x10, 0x11, 0x28, 0x29, 0x57, 0x58, 0x59, 0x5C, 0x5D) and pos < len(data):
            modrm = data[pos]
            pos += 1
            mod, reg, rm = decode_modrm(modrm)
            reg_code = reg | (rex_r << 3)
            rm_code = rm | (rex_b << 3)
            if op2 in (0x10, 0x28):
                mnemonic = "movsd" if 0xF2 in prefixes else "movaps"
                dst = xmm_name(reg_code)
                if mod == 3:
                    src = xmm_name(rm_code)
                else:
                    src, pos = format_memory_operand(
                        data,
                        pos,
                        mod,
                        rm,
                        rex_b,
                        start_va=start_va + offset,
                        instruction_end_hint=(pos - offset) + (4 if mod in (0, 2) else 1),
                    )
                return result(f"{mnemonic} {dst}, {src}", (dst, src), pos)
            if op2 in (0x11, 0x29):
                mnemonic = "movsd" if 0xF2 in prefixes else "movaps"
                src = xmm_name(reg_code)
                if mod == 3:
                    dst = xmm_name(rm_code)
                    return result(f"{mnemonic} {dst}, {src}", (dst, src), pos)
                dst, pos = format_memory_operand(
                    data,
                    pos,
                    mod,
                    rm,
                    rex_b,
                    start_va=start_va + offset,
                    instruction_end_hint=(pos - offset) + (4 if mod in (0, 2) else 1),
                )
                return result(f"{mnemonic} {dst}, {src}", None, pos)
            dst = xmm_name(reg_code)
            if op2 in (0x58, 0x59, 0x5C, 0x5D):
                mnemonic = {
                    0x58: "addsd" if 0xF2 in prefixes else "addps",
                    0x59: "mulsd" if 0xF2 in prefixes else "mulps",
                    0x5C: "subsd" if 0xF2 in prefixes else "subps",
                    0x5D: "minsd" if 0xF2 in prefixes else "minps",
                }[op2]
                if mod == 3:
                    src = xmm_name(rm_code)
                else:
                    src, pos = format_memory_operand(
                        data,
                        pos,
                        mod,
                        rm,
                        rex_b,
                        start_va=start_va + offset,
                        instruction_end_hint=(pos - offset) + (4 if mod in (0, 2) else 1),
                    )
                return result(f"{mnemonic} {dst}, {src}", (dst, f"{dst} {mnemonic} {src}"), pos)
            src = xmm_name(rm_code) if mod == 3 else "mem"
            if mod == 3 and reg_code == rm_code:
                return result(f"xorps {dst}, {dst}", (dst, "0"), pos)
            return result(f"xorps {dst}, {src}", None, pos)
        if op2 == 0x0D and pos < len(data):
            modrm = data[pos]
            pos += 1
            mod, _reg, rm = decode_modrm(modrm)
            operand, pos = rm_operand(
                data, pos, mod, rm, rex_b,
                width=64, start_va=start_va, offset=offset,
            )
            return result(f"prefetch {operand}", None, pos)
        if 0x80 <= op2 <= 0x8F and pos + 4 <= len(data):
            disp = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            return result(f"jcc 0x{start_va + pos + disp:x}", None, pos)

    if opcode == 0xC1 and pos < len(data):
        modrm = data[pos]
        pos += 1
        mod, group_op, rm = decode_modrm(modrm)
        dst, pos = rm_operand(
            data, pos, mod, rm, rex_b,
            width=width, start_va=start_va, offset=offset,
        )
        imm = data[pos]
        pos += 1
        op_name = {
            4: "shl",
            5: "shr",
            7: "sar",
        }.get(group_op, f"shift{group_op}")
        write = (dst, f"{dst} {op_name} 0x{imm:x}") if is_register_name(dst) else None
        return result(f"{op_name} {dst}, 0x{imm:x}", write, pos)

    return result(f"db 0x{opcode:02x}", None, offset + 1)


def decode_x64_subset(data: bytes, start_va: int, *, stop_offset: int) -> list[dict[str, Any]]:
    instructions: list[dict[str, Any]] = []
    offset = 0
    limit = min(stop_offset, len(data))
    while offset < limit:
        try:
            instr, next_offset = decode_one_x64(data[:limit], offset, start_va)
        except (IndexError, struct.error):
            # Method-span estimates can end on padding or in the prefix/modrm
            # of an instruction owned by the following method. Preserve those
            # terminal bytes as unknown data instead of discarding every union
            # registration already decoded from the bounded method body.
            for tail_offset in range(offset, limit):
                instructions.append({
                    "offset": tail_offset,
                    "va": f"0x{start_va + tail_offset:x}",
                    "bytes": f"{data[tail_offset]:02x}",
                    "text": f"db 0x{data[tail_offset]:02x}",
                    "write": None,
                    "truncatedTerminal": True,
                })
            break
        instructions.append(instr)
        if next_offset <= offset:
            offset += 1
        else:
            offset = next_offset
    return instructions


def call_argument_context(
    data: bytes,
    start_va: int,
    call_offset: int,
    *,
    window: int,
) -> dict[str, Any]:
    instructions = decode_x64_subset(data, start_va, stop_offset=call_offset)
    nearby = [
        instr for instr in instructions
        if max(0, call_offset - window) <= instr["offset"] < call_offset
    ]
    last_writes: dict[str, dict[str, Any]] = {}
    for instr in nearby:
        if str(instr.get("text", "")).startswith("call "):
            last_writes.clear()
            continue
        write = instr.get("write")
        if not write:
            continue
        arg_reg = canonical_arg_register(write["register"])
        if arg_reg:
            last_writes[arg_reg] = instr
    return {
        "windowBytes": window,
        "nearbyInstructions": nearby,
        "argRegisterWrites": {
            reg: last_writes[reg]
            for reg in ARG_REGISTERS
            if reg in last_writes
        },
    }


MEMORY_RE = re.compile(r"\[([^\]]+)\]")
REGISTER_TOKEN_RE = re.compile(
    r"\b(?:r(?:1[0-5]|[8-9])d?|r(?:ax|bx|cx|dx|si|di|sp|bp)|"
    r"e(?:ax|bx|cx|dx|si|di|sp|bp)|[abcd]l|[sd]il|[sb]pl|xmm(?:1[0-5]|[0-9]))\b"
)
REGISTER_DEST_RE = re.compile(
    r"^(?:mov(?:sd|aps|sxd|zx)?|lea|xor|xorps|pop|"
    r"addsd|addps|mulsd|mulps|subsd|subps|minsd|minps|"
    r"shl|shr|sar)\s+"
    r"(?P<dst>(?:r(?:1[0-5]|[8-9])d?|r(?:ax|bx|cx|dx|si|di|sp|bp)|"
    r"e(?:ax|bx|cx|dx|si|di|sp|bp)|[abcd]l|[sd]il|[sb]pl|xmm(?:1[0-5]|[0-9])))\b"
)


def is_static_method(row: dict[str, Any]) -> bool:
    try:
        flags = int(str(row.get("flags") or "0"), 16)
    except ValueError:
        return False
    return bool(flags & 0x0010)


def param_origin_registers(row: dict[str, Any]) -> dict[str, str]:
    origins: dict[str, str] = {}
    param_details = list(row.get("parameterDetails") or [])
    register_index = 0
    if not is_static_method(row):
        origins["rcx"] = "this"
        register_index = 1
    gp_order = ("rcx", "rdx", "r8", "r9")
    xmm_order = ("xmm0", "xmm1", "xmm2", "xmm3")
    for param in param_details:
        if register_index >= len(gp_order):
            break
        name = str(param.get("name") or f"param{register_index}")
        type_name = str(param.get("typeName") or "")
        origin = f"param:{name}"
        if type_name in {"System.Single", "System.Double"}:
            origins[xmm_order[register_index]] = origin
        else:
            origins[gp_order[register_index]] = origin
        register_index += 1
    return origins


def memory_base_and_disp(expr: str) -> tuple[str, str]:
    clean = expr.split("=>", 1)[0].replace(" ", "")
    match = re.match(r"([a-z][a-z0-9]*)([+-]0x[0-9a-f]+)?", clean)
    if not match:
        return "", ""
    base = canonical_register(match.group(1))
    return base, match.group(2) or ""


def origin_for_memory_expr(expr: str, origins: dict[str, str]) -> str:
    base, disp = memory_base_and_disp(expr)
    if not base or base in {"rsp", "rbp"}:
        return ""
    base_origin = origins.get(base)
    if not base_origin:
        return ""
    if not is_interesting_origin(base_origin):
        return ""
    return f"{base_origin}{disp}"


def is_interesting_origin(origin: str) -> bool:
    return origin.startswith(("this", "param:", "&this", "&param:"))


def origin_for_value(value: str, origins: dict[str, str]) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if value in {"0", "-1"} or value.startswith("0x") or value.startswith("-0x"):
        return value
    expression = re.match(
        r"(?P<reg>(?:r(?:1[0-5]|[8-9])d?|r(?:ax|bx|cx|dx|si|di|sp|bp)|"
        r"e(?:ax|bx|cx|dx|si|di|sp|bp)|[abcd]l|[sd]il|[sb]pl|xmm(?:1[0-5]|[0-9])))\s+"
        r"(?P<op>[a-z]+)\s+(?P<rhs>.+)$",
        value,
    )
    if expression:
        base_origin = origins.get(canonical_register(expression.group("reg")))
        if base_origin:
            return f"{base_origin} {expression.group('op')} {expression.group('rhs')}"
    if value.startswith("&[") and value.endswith("]"):
        inner = value[2:-1]
        origin = origin_for_memory_expr(inner, origins)
        return f"&{origin}" if origin else value
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        origin = origin_for_memory_expr(inner, origins)
        return origin or value
    if is_register_name(value):
        return origins.get(canonical_register(value), value)
    return value


def destination_register_to_ignore(instr: dict[str, Any]) -> str:
    write = instr.get("write") or {}
    register = str(write.get("register") or "")
    if register and is_register_name(register):
        return canonical_register(register)
    text = str(instr.get("text") or "")
    match = REGISTER_DEST_RE.match(text)
    if match:
        return canonical_register(match.group("dst"))
    return ""


def instruction_uses_origin(instr: dict[str, Any], origins: dict[str, str]) -> list[str]:
    used: list[str] = []
    text = str(instr.get("text") or "")
    ignored_destination = destination_register_to_ignore(instr)
    for reg in REGISTER_TOKEN_RE.findall(text):
        canonical = canonical_register(reg)
        if ignored_destination and canonical == ignored_destination:
            continue
        origin = origins.get(canonical)
        if origin and is_interesting_origin(origin) and origin not in used:
            used.append(origin)
    for expr in MEMORY_RE.findall(text):
        origin = origin_for_memory_expr(expr, origins)
        if origin and is_interesting_origin(origin) and origin not in used:
            used.append(origin)
    return used


def call_resolves_method(call: dict[str, Any], method_name: str) -> bool:
    return any(row.get("method") == method_name for row in (call.get("resolved") or []))


def call_resolves_type_method(call: dict[str, Any], type_suffix: str, method_name: str) -> bool:
    return any(
        str(row.get("type") or "").endswith(type_suffix) and row.get("method") == method_name
        for row in (call.get("resolved") or [])
    )


def previous_call_before(call_rows: list[dict[str, Any]], offset: int) -> dict[str, Any] | None:
    prior = [call for call in call_rows if int(call.get("offset") or 0) < offset]
    return prior[-1] if prior else None


def next_call_after(
    call_rows: list[dict[str, Any]],
    offset: int,
    *,
    method_name: str | None = None,
    type_suffix: str | None = None,
) -> dict[str, Any] | None:
    for call in call_rows:
        call_offset = int(call.get("offset") or 0)
        if call_offset <= offset:
            continue
        if method_name and type_suffix:
            if not call_resolves_type_method(call, type_suffix, method_name):
                continue
        elif method_name and not call_resolves_method(call, method_name):
            continue
        return call
    return None


def calls_resolving_method(
    call_rows: list[dict[str, Any]],
    method_name: str,
    *,
    type_suffix: str | None = None,
) -> list[dict[str, Any]]:
    return [
        call
        for call in call_rows
        if (
            call_resolves_type_method(call, type_suffix, method_name)
            if type_suffix
            else call_resolves_method(call, method_name)
        )
    ]


def call_at_offset(call_rows: list[dict[str, Any]], offset: int) -> dict[str, Any] | None:
    return next((call for call in call_rows if int(call.get("offset") or 0) == offset), None)


def previous_instruction_matching(
    instructions: list[dict[str, Any]],
    offset: int,
    pattern: str,
) -> dict[str, Any] | None:
    regex = re.compile(pattern)
    matches = [
        instr
        for instr in instructions
        if int(instr.get("offset") or 0) < offset
        and regex.search(str(instr.get("text") or ""))
    ]
    return matches[-1] if matches else None


def next_instruction_matching(
    instructions: list[dict[str, Any]],
    offset: int,
    pattern: str,
) -> dict[str, Any] | None:
    regex = re.compile(pattern)
    for instr in instructions:
        if int(instr.get("offset") or 0) <= offset:
            continue
        if regex.search(str(instr.get("text") or "")):
            return instr
    return None


def compact_call_reference(call: dict[str, Any] | None) -> dict[str, Any]:
    if not call:
        return {}
    arg_writes = {}
    for register, instr in ((call.get("argumentContext") or {}).get("argRegisterWrites") or {}).items():
        arg_writes[register] = {
            "offset": instr.get("offset"),
            "text": instr.get("text"),
            "value": (instr.get("write") or {}).get("value"),
        }
    return {
        "offset": call.get("offset"),
        "targetVa": call.get("targetVa"),
        "resolved": [
            {
                "methodIndex": row.get("methodIndex"),
                "type": row.get("type"),
                "method": row.get("method"),
            }
            for row in (call.get("resolved") or [])[:3]
        ],
        "argRegisterWrites": arg_writes,
    }


def classify_target_preview(instructions: list[dict[str, Any]]) -> str:
    texts = [str(instr.get("text") or "") for instr in instructions]
    joined = " | ".join(texts)
    if (
        "mov [rcx], rdx" in joined
        and "mov [rcx+0x8]" in joined
        and "mov [rcx+0x10]" in joined
    ):
        return "listEnumeratorCtorLike"
    if (
        "mov rdi, [rcx]" in joined
        and "mov esi, [rcx+0xc]" in joined
        and "mov [rcx+0x10], rax" in joined
    ):
        return "listEnumeratorMoveNextLike"
    if "call 0x182b37b40" in joined and "mov rax, rbx" in joined:
        return "listEnumeratorCtorWrapperLike"
    if (
        "cmp edx, [rcx+0x18]" in joined
        and "mov rax, [rcx+0x10]" in joined
        and "mov rax, [rax+0x20+rcx*8]" in joined
    ):
        return "listGetItemLike"
    if "inc [rcx+0x1c]" in joined and "mov [rbx+0x20+rdi*8]" in joined:
        return "listAddLike"
    if "test rcx, rcx" in joined and "call 0x180002c90" in joined and "mov rax, rbx" in joined:
        return "unityObjectAliveFilterLike"
    if "jmp rax" in joined and "[r9+0x220]" in joined:
        return "virtualOrGenericInvokerLike"
    if "call 0x18008fe30" in joined and "[r9+0x38]" in joined:
        return "genericLookupHelperLike"
    if "[rbx+0x20]" in joined and "[rax+0x11c]" in joined:
        return "unityObjectFieldGetterLike"
    return ""


def call_target_preview(pe: PeImage | None, call: dict[str, Any], *, max_bytes: int = 0x100) -> dict[str, Any]:
    if pe is None:
        return {}
    target = str(call.get("targetVa") or "")
    if not target.startswith("0x"):
        return {}
    try:
        target_va = int(target, 16)
        data = pe.bytes_at_va(target_va, max_bytes)
        instructions = []
        offset = 0
        while offset < len(data) and len(instructions) < 48:
            try:
                instr, next_offset = decode_one_x64(data, offset, target_va)
            except Exception:
                break
            instructions.append(instr)
            if next_offset <= offset:
                offset += 1
            else:
                offset = next_offset
    except Exception as exc:  # pragma: no cover - diagnostic path
        return {"error": str(exc)}
    preview = {
        "classification": classify_target_preview(instructions),
        "instructions": [compact_instruction(instr) for instr in instructions],
    }
    return {key: value for key, value in preview.items() if value not in (None, "", [], {})}


def compact_call_sequence(
    calls: list[dict[str, Any]],
    *,
    limit: int = 12,
    pe: PeImage | None = None,
    include_target_preview: bool = False,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in calls[:limit]:
        row = compact_call_reference(call)
        if include_target_preview and not row.get("resolved"):
            preview = call_target_preview(pe, call)
            if preview:
                row["targetPreview"] = preview
        rows.append(row)
    return rows


def registers_in_text(text: str) -> list[str]:
    out: list[str] = []
    for register in REGISTER_TOKEN_RE.findall(str(text or "")):
        canonical = canonical_register(register)
        if canonical and canonical not in out:
            out.append(canonical)
    return out


def compact_write(instr: dict[str, Any] | None) -> dict[str, Any]:
    if not instr:
        return {}
    write = instr.get("write") or {}
    row = {
        "offset": instr.get("offset"),
        "text": instr.get("text"),
        "register": write.get("register"),
        "value": write.get("value"),
    }
    return {key: value for key, value in row.items() if value not in (None, "", [], {})}


def backward_register_slice(
    instructions: list[dict[str, Any]],
    offset: int,
    registers: list[str],
    *,
    max_steps: int = 96,
    max_rows: int = 24,
) -> list[dict[str, Any]]:
    needed = {
        canonical_register(register)
        for register in registers
        if canonical_register(register)
    }
    if not needed:
        return []
    rows: list[dict[str, Any]] = []
    prior = [
        instr
        for instr in instructions
        if int(instr.get("offset") or 0) < offset
    ][-max_steps:]
    for instr in reversed(prior):
        text = str(instr.get("text") or "")
        write = instr.get("write") or {}
        dst = canonical_register(str(write.get("register") or "")) if write else destination_register_to_ignore(instr)
        text_registers = registers_in_text(text)
        uses_needed = any(register in needed for register in text_registers if register != dst)
        defines_needed = bool(dst and dst in needed)
        if not uses_needed and not defines_needed:
            continue
        rows.append(compact_instruction(instr))
        if defines_needed:
            needed.discard(dst)
            for source_register in registers_in_text(str(write.get("value") or "")):
                needed.add(source_register)
        if len(rows) >= max_rows:
            break
    rows.reverse()
    return rows


def argument_write_source_register(call: dict[str, Any], arg_register: str) -> str:
    writes = (call.get("argumentContext") or {}).get("argRegisterWrites") or {}
    instr = writes.get(arg_register) or {}
    write = instr.get("write") or {}
    value = str(write.get("value") or "")
    return canonical_register(value) if is_register_name(value) else ""


def previous_movsd_field_load(
    instructions: list[dict[str, Any]],
    offset: int,
    xmm_register: str,
) -> dict[str, Any] | None:
    if not xmm_register:
        return None
    pattern = rf"movsd {re.escape(xmm_register)}, \[[a-z0-9]+\+0x18\]$"
    return previous_instruction_matching(instructions, offset, pattern)


def movsd_field_source(instr: dict[str, Any] | None) -> dict[str, Any]:
    if not instr:
        return {}
    text = str(instr.get("text") or "")
    match = re.match(r"movsd (?P<xmm>xmm\d+), \[(?P<base>[a-z0-9]+)\+0x18\]$", text)
    if not match:
        return {}
    return {
        "xmm": match.group("xmm"),
        "baseRegister": canonical_register(match.group("base")),
        "field": "+0x18",
        "load": compact_instruction(instr),
    }


def compact_matching_instructions(
    instructions: list[dict[str, Any]],
    start_offset: int,
    end_offset: int,
    patterns: tuple[str, ...],
    *,
    limit: int = 16,
) -> list[dict[str, Any]]:
    regexes = [re.compile(pattern) for pattern in patterns]
    rows: list[dict[str, Any]] = []
    for instr in instructions:
        offset = int(instr.get("offset") or 0)
        if offset < start_offset or offset > end_offset:
            continue
        text = str(instr.get("text") or "")
        if not any(regex.search(text) for regex in regexes):
            continue
        rows.append(compact_instruction(instr))
        if len(rows) >= limit:
            break
    return rows


def add_fact_window(
    fact: dict[str, Any],
    instructions: list[dict[str, Any]],
    offset: int,
    *,
    before: int = 5,
    after: int = 5,
) -> None:
    fact["window"] = instruction_window(instructions, offset, before=before, after=after)


def extract_option_flow_facts(
    row: dict[str, Any],
    instructions: list[dict[str, Any]],
    call_rows: list[dict[str, Any]],
    pe: PeImage | None = None,
) -> list[dict[str, Any]]:
    type_name = str(row.get("type") or "")
    method = str(row.get("method") or "")
    facts: list[dict[str, Any]] = []

    if type_name.endswith(".DialogOptionPlayableAsset") and method == "GenPlayable":
        init_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogOptionBehaviour",
            method_name="InitDialogOptions",
        )
        if init_call:
            fact = {
                "kind": "optionPlayableSerializedRowsToBehaviour",
                "summary": (
                    "DialogOptionPlayableAsset.GenPlayable passes the serialized option row list "
                    "from the asset into DialogOptionBehaviour.InitDialogOptions."
                ),
                "serializedOptionRowsField": "asset+0x28",
                "initDialogOptionsCall": compact_call_reference(init_call),
                "initDialogOptionsArguments": {
                    key: compact_write(value)
                    for key, value in ((init_call.get("argumentContext") or {}).get("argRegisterWrites") or {}).items()
                    if key in {"rcx", "rdx", "r8"}
                },
                "interpretation": (
                    "The serialized Timeline option rows are the source for runtime option data; "
                    "this call does not expose a separate branch-target field."
                ),
            }
            add_fact_window(fact, instructions, int(init_call.get("offset") or 0))
            facts.append(fact)

    if type_name.endswith(".DialogTimelineManager") and method == "SelectIndex":
        select_timeline_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogTimelineManager",
            method_name="_SelectIndexInTimeline",
        )
        reset_call = next_call_after(
            call_rows,
            int(select_timeline_call.get("offset") or 0) if select_timeline_call else 0,
            type_suffix=".DialogTimelineManager",
            method_name="ResetDialogOption",
        )
        if select_timeline_call:
            fact = {
                "kind": "timelineSelectCallsChooseThenReset",
                "summary": (
                    "DialogTimelineManager.SelectIndex records the UI selection, calls "
                    "_SelectIndexInTimeline with that index, then calls ResetDialogOption."
                ),
                "selectTimelineCall": compact_call_reference(select_timeline_call),
                "resetDialogOptionCall": compact_call_reference(reset_call),
                "selectionIndexArgument": compact_write(
                    ((select_timeline_call.get("argumentContext") or {}).get("argRegisterWrites") or {}).get("rdx")
                ),
                "interpretation": (
                    "ResetDialogOption is post-selection cleanup around the runtime option gate, "
                    "not an authored branch-target lookup."
                ),
            }
            add_fact_window(fact, instructions, int(select_timeline_call.get("offset") or 0), before=10, after=14)
            facts.append(fact)

    if type_name.endswith(".DialogTimelineManager") and method == "OnJumpForward":
        stop_calls = [
            call
            for call in call_rows
            if any(
                target.get("method") in {"_StopLipSync", "_StopVoice"}
                for target in call.get("resolved") or []
            )
        ]
        branch_calls = [
            call
            for call in call_rows
            if any(
                target.get("method") in {"DialogChooseOption", "SetDialogOption", "ResetDialogOption"}
                for target in call.get("resolved") or []
            )
        ]
        if stop_calls or not branch_calls:
            fact = {
                "kind": "jumpForwardNoOptionRouteTarget",
                "summary": (
                    "DialogTimelineManager.OnJumpForward stops current playback state but has no "
                    "direct option choose/set/reset call in the recovered body."
                ),
                "stopCalls": compact_call_sequence(stop_calls),
                "optionRouteCalls": compact_call_sequence(branch_calls),
                "interpretation": (
                    "Runtime Jump clips may move playback time, but this method does not expose "
                    "a serialized option-branch target."
                ),
            }
            add_fact_window(
                fact,
                instructions,
                int(stop_calls[0].get("offset") or 0) if stop_calls else 0,
                before=6,
                after=10,
            )
            facts.append(fact)

    if type_name.endswith(".DialogTimelineManager") and method == "ResetDialogOption":
        clear_selected_clip = next(
            (
                instr
                for instr in instructions
                if str(instr.get("text") or "") == "and [rdi+0x1a8], 0x0"
            ),
            None,
        )
        refresh_call = next_call_after(
            call_rows,
            int(clear_selected_clip.get("offset") or 0) if clear_selected_clip else 0,
            type_suffix=".DialogTimelineManager",
            method_name="DoRefreshTimelineLoopEnable",
        )
        if clear_selected_clip:
            fact = {
                "kind": "resetClearsSelectedActiveClip",
                "summary": (
                    "ResetDialogOption clears the selected active clip pointer and refreshes "
                    "Timeline loop state."
                ),
                "selectedActiveClipField": "this+0x1a8",
                "currentOptionListField": "this+0x1e0",
                "clearOffset": clear_selected_clip.get("offset"),
                "clearInstruction": clear_selected_clip.get("text"),
                "refreshTimelineLoopCall": compact_call_reference(refresh_call),
                "interpretation": (
                    "This supports treating post-jump option resets as cleanup/default state, "
                    "not as evidence that all candidate response lines share one branch."
                ),
            }
            add_fact_window(fact, instructions, int(clear_selected_clip.get("offset") or 0), before=6, after=10)
            facts.append(fact)

    if method == "_SelectIndexInTimeline":
        for instr in instructions:
            text = str(instr.get("text") or "")
            match = re.match(r"mov (?P<dst>[a-z0-9]+), \[rax\+0x98\]$", text)
            if not match:
                continue
            offset = int(instr.get("offset") or 0)
            choose_call = next_call_after(
                call_rows,
                offset,
                type_suffix=".DialogUtils",
                method_name="DialogChooseOption",
            )
            fact = {
                "kind": "selectedOptionFieldToRuntimeChoice",
                "summary": (
                    "The selected Timeline option object is looked up with the UI index, "
                    "then its +0x98 field is passed to DialogChooseOption as the runtime option index."
                ),
                "selectedOptionField": "+0x98",
                "readOffset": offset,
                "readInstruction": text,
                "lookupCall": compact_call_reference(previous_call_before(call_rows, offset)),
                "chooseCall": compact_call_reference(choose_call),
            }
            add_fact_window(fact, instructions, offset)
            facts.append(fact)
            break

    if method == "DialogChooseOption":
        for instr in instructions:
            text = str(instr.get("text") or "")
            if not re.match(r"mov \[rax\+0x18\], [a-z0-9]+$", text):
                continue
            offset = int(instr.get("offset") or 0)
            wrapper_call = next_call_after(call_rows, offset)
            fact = {
                "kind": "runtimeOptionIndexWrite",
                "summary": (
                    "DialogChooseOption writes the selected optionIndex into a runtime "
                    "option/playable object +0x18 field before invoking the wrapper path."
                ),
                "runtimeOptionField": "+0x18",
                "writeOffset": offset,
                "writeInstruction": text,
                "wrapperCall": compact_call_reference(wrapper_call),
            }
            add_fact_window(fact, instructions, offset)
            facts.append(fact)
            break

    if method == "SetDialogOption":
        compare_current = next(
            (
                instr
                for instr in instructions
                if str(instr.get("text") or "") == "cmp ecx, [rsi+0x18]"
            ),
            None,
        )
        compare_zero = next(
            (
                instr
                for instr in instructions
                if str(instr.get("text") or "") == "cmp ebp, [rsi+0x18]"
            ),
            None,
        )
        if compare_current:
            offset = int(compare_current.get("offset") or 0)
            fact = {
                "kind": "setDialogOptionIndexGate",
                "summary": (
                    "SetDialogOption compares the current manager option +0x18 "
                    "against the candidate option +0x18, then treats zero as a "
                    "non-branch/default option."
                ),
                "currentOptionField": "this+0x1e0+0x18",
                "candidateOptionField": "param:options+0x18",
                "compareOffset": offset,
                "zeroCompareOffset": compare_zero.get("offset") if compare_zero else None,
            }
            add_fact_window(fact, instructions, offset)
            facts.append(fact)

    if method == "DialogTimelineDoNext":
        def calls_named(method_name: str) -> list[dict[str, Any]]:
            return calls_resolving_method(call_rows, method_name)

        active_at_time_calls = calls_named("GetActiveClipsAtGivenTime")
        active_range_calls = calls_named("GetActiveClipsAtGivenTimeRange")
        if active_at_time_calls or active_range_calls:
            first_query_offset = int(
                min(
                    [
                        int(call.get("offset") or 0)
                        for call in [*active_at_time_calls, *active_range_calls]
                    ]
                )
            )
            fact = {
                "kind": "timelineDoNextActiveClipQueries",
                "summary": (
                    "DialogTimelineDoNext resolves Timeline playables through the playable graph, "
                    "then asks Unity Timeline for clips active at the current time or time range."
                ),
                "interpretation": (
                    "Runtime dialog/cutscene advancement is driven by Timeline active-clip "
                    "time windows; this is strong evidence for intra-Timeline order but not "
                    "an option branch target by itself."
                ),
                "playableGraphCalls": compact_call_sequence(
                    [
                        *calls_named("get_playableGraph")[:4],
                        *calls_named("GetRootPlayable")[:4],
                        *calls_named("GetWrapScriptObject")[:4],
                        *calls_named("GetTimelinePlayable")[:4],
                    ],
                    pe=pe,
                    include_target_preview=True,
                ),
                "timelineActiveClipCalls": compact_call_sequence(
                    [*active_at_time_calls, *active_range_calls],
                    pe=pe,
                    include_target_preview=True,
                ),
                "timelineIntervalTreeCalls": compact_call_sequence(
                    calls_named("UpdateIntervalTree"),
                    pe=pe,
                    include_target_preview=True,
                ),
                "cutsceneRootRetimingCalls": compact_call_sequence(
                    calls_named("SetNewTimeForCutsceneRoot"),
                    pe=pe,
                    include_target_preview=True,
                ),
                "timelineTimeArgumentState": compact_matching_instructions(
                    instructions,
                    0,
                    first_query_offset,
                    (
                        r"movaps xmm7, xmm2$",
                        r"movaps xmm8, xmm1$",
                        r"movsd \[[a-z0-9]+\+0x18\], xmm2$",
                        r"mov \[[a-z0-9]+\+0x8\], rcx$",
                        r"comisd xmm\d+, xmm\d+$",
                    ),
                ),
                "timelinePointQueryState": compact_matching_instructions(
                    instructions,
                    max(0, int(active_at_time_calls[0].get("offset") or 0) - 80)
                    if active_at_time_calls
                    else 0,
                    int(active_at_time_calls[0].get("offset") or 0) + 24
                    if active_at_time_calls
                    else 0,
                    (
                        r"movsd xmm1, \[rsp\+0x88\]$",
                        r"addsd xmm1, \[rsp\+0x80\]$",
                        r"xor r9d, r9d$",
                        r"xor r8d, r8d$",
                        r"mov rcx, rax$",
                    ),
                ),
                "timelineRangeQueryState": compact_matching_instructions(
                    instructions,
                    max(0, int(active_range_calls[0].get("offset") or 0) - 96)
                    if active_range_calls
                    else 0,
                    int(active_range_calls[0].get("offset") or 0) + 24
                    if active_range_calls
                    else 0,
                    (
                        r"mov rdx, \[rcx\+0xb8\]$",
                        r"subsd xmm1, xmm6$",
                        r"mov r9, \[rdx\+0x80\]$",
                        r"movaps xmm2, xmm7$",
                        r"mov rcx, r14$",
                    ),
                ),
            }
            add_fact_window(fact, instructions, first_query_offset, before=16, after=20)
            facts.append(fact)

    if method == "DialogTimelineGetAllTimelinePlayable":
        append_call = call_at_offset(call_rows, 0x193)
        fact = {
            "kind": "timelinePlayableListFromTimelineRoot",
            "summary": (
                "DialogTimelineGetAllTimelinePlayable creates or reuses a playable result list, "
                "derives a playable collection from timelineRoot, resolves each item through "
                "PlayableDirectorUtility.GetTimelinePlayable, and appends non-null playables."
            ),
            "resultListSetupCalls": compact_call_sequence(
                [call for call in (call_at_offset(call_rows, 0xF6), call_at_offset(call_rows, 0x111)) if call],
                pe=pe,
                include_target_preview=True,
            ),
            "timelineRootCollectionCalls": compact_call_sequence(
                [call for call in (call_at_offset(call_rows, 0x119), call_at_offset(call_rows, 0x134)) if call],
                pe=pe,
                include_target_preview=True,
            ),
            "playableResolutionCalls": compact_call_sequence(
                [call for call in (call_at_offset(call_rows, 0x14C), call_at_offset(call_rows, 0x156)) if call],
                pe=pe,
                include_target_preview=True,
            ),
            "resultAppendCalls": compact_call_sequence(
                [call for call in (append_call,) if call],
                pe=pe,
                include_target_preview=True,
            ),
            "resultListAccesses": compact_matching_instructions(
                instructions,
                0xB0,
                0x1DA,
                (
                    r"mov rcx, \[rax\+0xb8\]$",
                    r"mov rcx, \[rcx\+0x98\]$",
                    r"mov rdx, \[rcx\+0xb8\]$",
                    r"mov rcx, \[rdx\+0x98\]$",
                    r"mov rax, \[rax\+0xb8\]$",
                    r"mov rax, \[rax\+0x98\]$",
                ),
            ),
            "timelineRootAndLoopState": compact_matching_instructions(
                instructions,
                0xE6,
                0x198,
                (
                    r"test rdi, rdi$",
                    r"mov rcx, rdi$",
                    r"mov rbx, rax$",
                    r"cmp edi, \[rbx\+0x18\]$",
                    r"mov edx, edi$",
                    r"mov rsi, rax$",
                    r"test rax, rax$",
                    r"mov rdx, rsi$",
                    r"inc rdi$",
                ),
            ),
        }
        add_fact_window(fact, instructions, 0x116, before=12, after=36)
        facts.append(fact)

    if method == "DialogTimelineGetAllActiveClips":
        get_all_playables_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogUtils",
            method_name="DialogTimelineGetAllTimelinePlayable",
        )
        if get_all_playables_call:
            call_offset = int(get_all_playables_call.get("offset") or 0)
            fact = {
                "kind": "activeClipsFromTimelinePlayableClipLists",
                "summary": (
                    "DialogTimelineGetAllActiveClips enumerates all Timeline playables, "
                    "then each playable's +0x40 clip list, filters active clip objects, "
                    "and appends them to outClips."
                ),
                "allTimelinePlayableCall": compact_call_reference(get_all_playables_call),
                "outerTimelinePlayableEnumerationCalls": compact_call_sequence(
                    [
                        call
                        for call in (call_at_offset(call_rows, 0x19F), call_at_offset(call_rows, 0x1D3))
                        if call
                    ],
                    pe=pe,
                    include_target_preview=True,
                ),
                "innerClipEnumerationCalls": compact_call_sequence(
                    [
                        call
                        for call in (call_at_offset(call_rows, 0x207), call_at_offset(call_rows, 0x241))
                        if call
                    ],
                    pe=pe,
                    include_target_preview=True,
                ),
                "activeClipFilterCalls": compact_call_sequence(
                    [call for call in (call_at_offset(call_rows, 0x256),) if call],
                    pe=pe,
                    include_target_preview=True,
                ),
                "outClipAppendCalls": compact_call_sequence(
                    [call for call in (call_at_offset(call_rows, 0x276),) if call],
                    pe=pe,
                    include_target_preview=True,
                ),
                "playableClipListLoads": compact_matching_instructions(
                    instructions,
                    call_offset,
                    0x276,
                    (
                        r"mov rdx, \[rax\+0x40\]$",
                        r"mov rdx, rax$",
                        r"mov rcx, rbx$",
                    ),
                ),
                "activeClipCollectionState": compact_matching_instructions(
                    instructions,
                    call_offset,
                    0x276,
                    (
                        r"mov \[rsp\+0xb8\], rbx$",
                        r"mov rax, \[rsp\+0x30\]$",
                        r"mov rcx, \[rsp\+0x48\]$",
                        r"mov rdx, rax$",
                        r"mov rcx, rbx$",
                    ),
                ),
            }
            add_fact_window(fact, instructions, call_offset, before=5, after=38)
            facts.append(fact)

    if method == "TryTriggerTrunkBindingOption":
        active_clip_list_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogUtils",
            method_name="DialogTimelineGetAllActiveClips",
        )
        set_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogTimelineManager",
            method_name="SetDialogOption",
        )
        active_clip_list_offset = int(active_clip_list_call.get("offset") or 0) if active_clip_list_call else 0
        set_call_offset = int(set_call.get("offset") or 0) if set_call else 0
        if active_clip_list_call and set_call_offset > active_clip_list_offset:
            traversal_calls = [
                call
                for call in call_rows
                if active_clip_list_offset < int(call.get("offset") or 0) < set_call_offset
            ]
            iterator_setup_calls = [
                call
                for call in traversal_calls
                if int(call.get("offset") or 0) <= 0x2e5
            ]
            playable_lookup_calls = [
                call
                for call in traversal_calls
                if int(call.get("offset") or 0) > 0x2e5
            ]
            fact = {
                "kind": "activeClipTraversalWindow",
                "summary": (
                    "After DialogTimelineGetAllActiveClips, TryTriggerTrunkBindingOption "
                    "walks stack/list state to recover active clip nodes before the "
                    "SetDialogOption gate."
                ),
                "interpretation": (
                    "The selected candidate node is held in rbx, its option payload is "
                    "loaded from [rbx+0x28], and rsi is the paired start-boundary node "
                    "used later for the loop-disable start time."
                ),
                "activeClipListCall": compact_call_reference(active_clip_list_call),
                "iteratorSetupCalls": compact_call_sequence(
                    iterator_setup_calls,
                    pe=pe,
                    include_target_preview=True,
                ),
                "playableLookupCalls": compact_call_sequence(
                    playable_lookup_calls,
                    pe=pe,
                    include_target_preview=True,
                ),
                "stateLoads": compact_matching_instructions(
                    instructions,
                    active_clip_list_offset,
                    set_call_offset,
                    (
                        r"mov r14, \[rsp\+0xc0\]$",
                        r"mov r15, \[rsp\+0x28\]$",
                        r"mov rsi, \[rsp\+0x30\]$",
                        r"mov r13, rax$",
                        r"mov rbx, rax$",
                    ),
                ),
                "candidateChecks": compact_matching_instructions(
                    instructions,
                    active_clip_list_offset,
                    set_call_offset,
                    (
                        r"mov rax, \[rbx\+0x28\]$",
                        r"test rbx, rbx$",
                        r"test rax, rax$",
                        r"cmp \[rax\+0x18\], 0x0$",
                    ),
                ),
            }
            add_fact_window(fact, instructions, active_clip_list_offset, before=8, after=22)
            facts.append(fact)
        if set_call:
            call_offset = int(set_call.get("offset") or 0)
            gate = previous_instruction_matching(
                instructions,
                call_offset,
                r"cmp \[rax\+0x18\], 0x0$",
            )
            fact = {
                "kind": "activeClipOptionGate",
                "summary": (
                    "TryTriggerTrunkBindingOption only calls SetDialogOption for an "
                    "active clip whose runtime +0x18 option field is positive."
                ),
                "activeClipField": "+0x18",
                "gateOffset": gate.get("offset") if gate else None,
                "activeClipListCall": compact_call_reference(active_clip_list_call),
                "setDialogOptionCall": compact_call_reference(set_call),
                "selectedOptionClipArgument": compact_write(
                    ((set_call.get("argumentContext") or {}).get("argRegisterWrites") or {}).get("rdx")
                ),
                "selectedOptionClipSlice": backward_register_slice(
                    instructions,
                    call_offset,
                    ["rax"],
                ),
            }
            add_fact_window(fact, instructions, call_offset, before=12, after=8)
            facts.append(fact)
        disable_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogUtils",
            method_name="DialogTimelineDisableLoopInRange",
        )
        if disable_call:
            call_offset = int(disable_call.get("offset") or 0)
            start_xmm = argument_write_source_register(disable_call, "xmm1")
            end_xmm = argument_write_source_register(disable_call, "xmm2")
            start_load = previous_movsd_field_load(
                instructions,
                call_offset,
                start_xmm,
            )
            end_load = previous_movsd_field_load(
                instructions,
                call_offset,
                end_xmm,
            )
            start_source = movsd_field_source(start_load)
            end_source = movsd_field_source(end_load)
            start_base = start_source.get("baseRegister") or ""
            end_base = end_source.get("baseRegister") or ""
            adjustment = previous_instruction_matching(
                instructions,
                call_offset,
                rf"subsd {re.escape(end_xmm)}, " if end_xmm else r"subsd xmm\d+, ",
            )
            selected_clip_store = next_instruction_matching(
                instructions,
                call_offset,
                r"mov \[[a-z0-9]+\+0x1a8\], [a-z0-9]+$",
            )
            fact = {
                "kind": "selectedClipLoopDisableRange",
                "summary": (
                    "After selecting an active option clip, TryTriggerTrunkBindingOption "
                    "passes clip time fields into DialogTimelineDisableLoopInRange."
                ),
                "activeClipListCall": compact_call_reference(active_clip_list_call),
                "startTimeSource": start_source,
                "endTimeSource": end_source,
                "startTimeLoad": compact_instruction(start_load) if start_load else {},
                "endTimeLoad": compact_instruction(end_load) if end_load else {},
                "endTimeAdjustment": compact_instruction(adjustment) if adjustment else {},
                "disableLoopCall": compact_call_reference(disable_call),
                "selectedClipStore": compact_instruction(selected_clip_store) if selected_clip_store else {},
                "setToDisableState": compact_matching_instructions(
                    instructions,
                    int(set_call.get("offset") or 0) if set_call else call_offset,
                    call_offset + 16,
                    (
                        r"mov rdx, rax$",
                        r"mov rcx, r14$",
                        r"movsd xmm7, \[rsi\+0x18\]$",
                        r"movsd xmm6, \[rbx\+0x18\]$",
                        r"subsd xmm6, ",
                        r"movaps xmm2, xmm6$",
                        r"movaps xmm1, xmm7$",
                        r"mov rcx, r15$",
                        r"mov \[r14\+0x1a8\], rbx$",
                    ),
                ),
                "startSourceSlice": backward_register_slice(
                    instructions,
                    call_offset,
                    [value for value in [start_base, start_xmm] if value],
                ),
                "endSourceSlice": backward_register_slice(
                    instructions,
                    call_offset,
                    [value for value in [end_base, end_xmm] if value],
                ),
            }
            add_fact_window(fact, instructions, call_offset, before=24, after=10)
            facts.append(fact)

    if method == "DialogTimelineDisableLoopInRange":
        get_all_playables_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogUtils",
            method_name="DialogTimelineGetAllTimelinePlayable",
        )
        active_range_calls = calls_resolving_method(call_rows, "GetActiveClipsAtGivenTimeRange")
        if get_all_playables_call and active_range_calls:
            playable_offset = int(get_all_playables_call.get("offset") or 0)
            range_call = active_range_calls[0]
            range_offset = int(range_call.get("offset") or 0)
            fact = {
                "kind": "disableLoopRangeActiveClipScan",
                "summary": (
                    "DialogTimelineDisableLoopInRange enumerates Timeline playables, "
                    "queries clips active in the selected start/end range, and disables "
                    "looping for matching runtime elements."
                ),
                "interpretation": (
                    "The disable pass uses the selected clip time interval as cleanup "
                    "after the option gate; it supports clip-order evidence but does "
                    "not by itself identify a new option branch target."
                ),
                "allTimelinePlayableCall": compact_call_reference(get_all_playables_call),
                "timelineActiveClipCalls": compact_call_sequence(
                    active_range_calls,
                    pe=pe,
                    include_target_preview=True,
                ),
                "outerTimelinePlayableEnumerationCalls": compact_call_sequence(
                    [
                        call
                        for call in (call_at_offset(call_rows, 0x13F), call_at_offset(call_rows, 0x173))
                        if call
                    ],
                    pe=pe,
                    include_target_preview=True,
                ),
                "innerClipEnumerationCalls": compact_call_sequence(
                    [
                        call
                        for call in (call_at_offset(call_rows, 0x21A), call_at_offset(call_rows, 0x257))
                        if call
                    ],
                    pe=pe,
                    include_target_preview=True,
                ),
                "activeClipFilterCalls": compact_call_sequence(
                    [call for call in (call_at_offset(call_rows, 0x26C),) if call],
                    pe=pe,
                    include_target_preview=True,
                ),
                "rangeArgumentState": compact_matching_instructions(
                    instructions,
                    0,
                    range_offset,
                    (
                        r"movsd \[[a-z0-9]+\+0x18\], xmm2$",
                        r"movsd \[[a-z0-9]+\+0x10\], xmm1$",
                        r"movaps xmm6, xmm2$",
                        r"movaps xmm7, xmm1$",
                        r"mov rbx, rcx$",
                        r"movaps xmm2, xmm6$",
                        r"movaps xmm1, xmm7$",
                    ),
                ),
                "playableTraversalState": compact_matching_instructions(
                    instructions,
                    playable_offset,
                    range_offset,
                    (
                        r"test rax, rax$",
                        r"mov rdx, rax$",
                        r"lea rcx, \[rsp\+0x80\]$",
                        r"mov rcx, \[rsp\+0x68\]$",
                        r"mov rbx, rax$",
                        r"test rbx, rbx$",
                    ),
                ),
                "activeRangeClipState": compact_matching_instructions(
                    instructions,
                    range_offset,
                    range_offset + 160,
                    (
                        r"mov rdx, rax$",
                        r"mov rcx, [a-z0-9]+$",
                        r"test rdx, rdx$",
                        r"test rax, rax$",
                        r"mov rbx, rax$",
                        r"call 0x18003f5a0$",
                    ),
                ),
            }
            add_fact_window(fact, instructions, range_offset, before=20, after=20)
            facts.append(fact)

    if method == "_TryDoNext":
        trigger_call = next_call_after(
            call_rows,
            0,
            type_suffix=".DialogTimelineManager",
            method_name="TryTriggerTrunkBindingOption",
        )
        if trigger_call:
            call_offset = int(trigger_call.get("offset") or 0)
            gate = previous_instruction_matching(
                instructions,
                call_offset,
                r"cmp \[rax\+0x18\], 0x0$",
            )
            fact = {
                "kind": "tryDoNextSelectedOptionGate",
                "summary": (
                    "_TryDoNext checks the current manager option +0x18 before "
                    "falling into TryTriggerTrunkBindingOption."
                ),
                "currentOptionField": "this+0x1e0+0x18",
                "gateOffset": gate.get("offset") if gate else None,
                "triggerCall": compact_call_reference(trigger_call),
            }
            add_fact_window(fact, instructions, call_offset)
            facts.append(fact)

    return facts


def build_method_body_summary(
    row: dict[str, Any],
    data: bytes,
    start_va: int,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    pe: PeImage | None = None,
    *,
    max_instructions: int,
) -> dict[str, Any]:
    instructions = decode_x64_subset(data, start_va, stop_offset=len(data))
    unknown_count = sum(1 for instr in instructions if str(instr.get("text") or "").startswith("db "))
    ret_offset = next(
        (instr.get("offset") for instr in instructions if str(instr.get("text") or "").startswith("ret")),
        None,
    )
    origins = param_origin_registers(row)
    initial_origins = dict(origins)
    memory_counter: Counter[str] = Counter()
    field_counter: Counter[str] = Counter()
    param_flow: dict[str, list[dict[str, Any]]] = {}
    interesting: list[dict[str, Any]] = []
    field_accesses: list[dict[str, Any]] = []
    control_flow: list[dict[str, Any]] = []
    call_rows: list[dict[str, Any]] = []

    def remember_flow(origin: str, instr: dict[str, Any]) -> None:
        bucket = param_flow.setdefault(origin, [])
        if len(bucket) < max_instructions:
            bucket.append({
                "offset": instr.get("offset"),
                "va": instr.get("va"),
                "text": instr.get("text"),
                "bytes": instr.get("bytes"),
            })

    for instr in instructions:
        text = str(instr.get("text") or "")
        offset = int(instr.get("offset") or 0)
        used_origins = instruction_uses_origin(instr, origins)
        for origin in used_origins:
            remember_flow(origin, instr)

        memory_origins: list[str] = []
        for expr in MEMORY_RE.findall(text):
            memory_counter[expr] += 1
            origin = origin_for_memory_expr(expr, origins)
            if origin:
                field_counter[origin] += 1
                memory_origins.append(origin)
                if len(field_accesses) < max_instructions * 2:
                    field_accesses.append({
                        "offset": offset,
                        "va": instr.get("va"),
                        "text": text,
                        "bytes": instr.get("bytes"),
                        "operand": f"[{expr}]",
                        "origin": origin,
                        "kind": memory_access_kind(text, expr),
                    })

        call_match = re.match(r"call 0x([0-9a-f]+)$", text)
        if call_match:
            target_va = int(call_match.group(1), 16)
            call_rows.append({
                "offset": offset,
                "targetVa": f"0x{target_va:x}",
                "resolved": method_by_pointer.get(target_va, []),
                "argumentContext": call_argument_context(
                    data,
                    start_va,
                    offset,
                    window=96,
                ),
            })

        is_control_flow = text.startswith(("cmp ", "test ", "j", "call ", "ret"))
        if is_control_flow and len(control_flow) < max_instructions * 2:
            row_out = {
                "offset": offset,
                "va": instr.get("va"),
                "text": text,
                "bytes": instr.get("bytes"),
            }
            target = branch_target_from_text(text)
            if target:
                row_out["targetVa"] = target
                if call_match:
                    row_out["resolved"] = method_by_pointer.get(int(target, 16), [])
            if used_origins:
                row_out["originUses"] = used_origins
            if memory_origins:
                row_out["memoryOrigins"] = memory_origins
            control_flow.append(row_out)

        is_interesting = (
            bool(used_origins)
            or bool(memory_origins)
            or is_control_flow
        )
        if is_interesting and len(interesting) < max_instructions:
            row_out = {
                "offset": offset,
                "va": instr.get("va"),
                "text": text,
                "bytes": instr.get("bytes"),
            }
            if used_origins:
                row_out["originUses"] = used_origins
            if memory_origins:
                row_out["memoryOrigins"] = memory_origins
            interesting.append(row_out)

        write = instr.get("write")
        if write:
            dst = canonical_register(str(write.get("register") or ""))
            if dst in {"rsp", "rbp"}:
                origins.pop(dst, None)
                continue
            if dst:
                value_origin = origin_for_value(str(write.get("value") or ""), origins)
                if value_origin:
                    origins[dst] = value_origin
                elif dst in origins:
                    origins.pop(dst, None)

    window_specs: list[tuple[int, str]] = []
    seen_window_offsets: set[int] = set()

    def add_window(offset: int, label: str) -> None:
        if offset in seen_window_offsets:
            return
        seen_window_offsets.add(offset)
        window_specs.append((offset, label))

    for access in field_accesses:
        origin = str(access.get("origin") or "")
        text = str(access.get("text") or "")
        if origin.startswith(("this", "param:")) or any(token in text for token in ("0x18", "0x98", "0x110")):
            add_window(int(access.get("offset") or 0), f"field {origin} @ +0x{int(access.get('offset') or 0):x}")
    for origin, rows in param_flow.items():
        if "index" not in origin.lower() and "option" not in origin.lower():
            continue
        for flow_row in rows:
            text = str(flow_row.get("text") or "")
            offset = int(flow_row.get("offset") or 0)
            if any(token in text for token in ("0x18", "0x98")) or text.startswith(("mov edx", "mov r8d")):
                add_window(offset, f"value {origin} @ +0x{offset:x} {text}")
    for control_row in control_flow:
        resolved = control_row.get("resolved") or []
        text = str(control_row.get("text") or "")
        if control_row.get("originUses") or control_row.get("memoryOrigins") or any(
            "Dialog" in target.get("type", "") or "Dialog" in target.get("method", "")
            for target in resolved
        ):
            add_window(
                int(control_row.get("offset") or 0),
                f"control @ +0x{int(control_row.get('offset') or 0):x} {text}",
            )
    for call in call_rows:
        resolved = call.get("resolved") or []
        if any("Dialog" in target.get("type", "") or "Dialog" in target.get("method", "") for target in resolved):
            add_window(
                int(call.get("offset") or 0),
                f"call {', '.join(target.get('method', '') for target in resolved[:2])} @ +0x{int(call.get('offset') or 0):x}",
            )

    return {
        "initialRegisterOrigins": initial_origins,
        "finalRegisterOrigins": {
            key: value for key, value in origins.items()
            if value.startswith(("this", "param:"))
        },
        "instructionCount": len(instructions),
        "unknownInstructionCount": unknown_count,
        "firstRetOffset": ret_offset,
        "topMemoryOperands": [
            {"operand": operand, "count": count}
            for operand, count in memory_counter.most_common(20)
        ],
        "fieldLikeOrigins": [
            {"origin": origin, "count": count}
            for origin, count in field_counter.most_common(30)
        ],
        "fieldAccesses": field_accesses,
        "controlFlow": control_flow,
        "controlFlowWindows": [
            {
                "offset": offset,
                "label": label,
                "instructions": instruction_window(instructions, offset),
            }
            for offset, label in window_specs[:20]
        ],
        "paramFlow": param_flow,
        "interestingInstructions": interesting,
        "optionFlowFacts": extract_option_flow_facts(row, instructions, call_rows, pe=pe),
        "calls": call_rows,
    }


def scan_direct_calls(
    pe: PeImage,
    start_va: int,
    size: int,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    catalog_target_keys: set[tuple[int, str, str]],
    *,
    include_unresolved: bool,
    arg_context_window: int,
) -> tuple[list[dict[str, Any]], int]:
    data = pe.bytes_at_va(start_va, size)
    calls: list[dict[str, Any]] = []
    unresolved_count = 0
    for offset in range(0, max(0, len(data) - 5)):
        if data[offset] != 0xE8:
            continue
        rel = struct.unpack_from("<i", data, offset + 1)[0]
        target_va = start_va + offset + 5 + rel
        arg_context = call_argument_context(
            data,
            start_va,
            offset,
            window=arg_context_window,
        )
        resolved = method_by_pointer.get(target_va, [])
        if not resolved:
            unresolved_count += 1
            if include_unresolved:
                calls.append(
                    {
                        "offset": offset,
                        "targetVa": f"0x{target_va:x}",
                        "resolved": [],
                        "isCatalogTarget": False,
                        "isDialogRelated": False,
                        "argumentContext": arg_context,
                    }
                )
            continue
        is_catalog_target = any(
            (row["methodIndex"], row["type"], row["method"]) in catalog_target_keys
            for row in resolved
        )
        is_dialog_related = any("Dialog" in row["type"] or "Dialog" in row["method"] for row in resolved)
        calls.append(
            {
                "offset": offset,
                "targetVa": f"0x{target_va:x}",
                "resolved": resolved,
                "isCatalogTarget": is_catalog_target,
                "isDialogRelated": is_dialog_related,
                "argumentContext": arg_context,
            }
        )
    return calls, unresolved_count


def estimate_scan_size(pointer: int, sorted_module_pointers: list[int], max_scan_bytes: int) -> tuple[int, int | None]:
    pos = bisect_right(sorted_module_pointers, pointer)
    next_pointer = sorted_module_pointers[pos] if pos < len(sorted_module_pointers) else None
    if next_pointer is None or next_pointer <= pointer:
        return max_scan_bytes, next_pointer
    delta = next_pointer - pointer
    if delta <= 0 or delta > max_scan_bytes:
        return max_scan_bytes, next_pointer
    return delta, next_pointer


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog_module = load_catalog_module()
    metadata_path = catalog_module.resolve_metadata_path(args.metadata, prefer_cache=True)
    md = catalog_module.Metadata(metadata_path)
    pe = PeImage(args.gameassembly)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    code_reg = parse_int(args.code_registration)
    code_reg_summary = code_registration_summary(pe, code_reg)
    modules = parse_codegen_modules(pe, code_reg)
    ranges = image_method_ranges(md)
    pointers_by_image, method_by_pointer = build_pointer_indexes(pe, md, modules, ranges)
    generic_index: dict[int, list[dict[str, Any]]] = {}
    generic_index_summary: dict[str, Any] = {"enabled": False}
    if getattr(args, "include_generic_instantiations", False):
        metadata_reg = (
            parse_int(args.metadata_registration)
            if args.metadata_registration
            else find_metadata_registration(pe, code_reg)
        )
        if metadata_reg is None:
            generic_index_summary["error"] = "MetadataRegistration not found"
        else:
            generic_index = build_generic_method_index(pe, md, code_reg, metadata_reg)
            added = 0
            for pointer, rows in generic_index.items():
                if pointer not in method_by_pointer:
                    method_by_pointer[pointer] = rows
                    added += 1
            generic_index_summary = {
                "enabled": True,
                "metadataRegistration": f"0x{metadata_reg:x}",
                "genericInstantiations": len(generic_index),
                "namedEntryPointsAdded": added,
            }
    sorted_all_pointers = sorted({
        pointer
        for pointers in pointers_by_image.values()
        for pointer in pointers
        if pointer
    } | set(generic_index))
    catalog_target_keys = {
        (row["methodIndex"], row["type"], row["method"])
        for row in catalog.get("bodyTargets", [])
    }
    body_summary_re = re.compile(args.body_summary_method_regex) if args.body_summary_method_regex else None

    mapped_targets: list[dict[str, Any]] = []
    for row in catalog.get("bodyTargets", []):
        image_name = row.get("image", "")
        image_range = ranges.get(image_name)
        module = modules.get(image_name)
        pointers = pointers_by_image.get(image_name, [])
        mapped = dict(row)
        mapped["imageMethodRange"] = image_range
        mapped["codeGenModule"] = module
        mapped["mappingStatus"] = "unmapped"
        if not image_range or not module:
            mapped["mappingError"] = "missing image range or codegen module"
            mapped_targets.append(mapped)
            continue
        slot = row["methodIndex"] - image_range["methodStart"]
        mapped["moduleMethodSlot"] = slot
        if slot < 0 or slot >= len(pointers):
            mapped["mappingError"] = "method index outside module method pointer table"
            mapped_targets.append(mapped)
            continue
        pointer = pointers[slot]
        generic_candidates = (
            generic_body_candidates(generic_index, int(row["methodIndex"]))
            if not pointer and generic_index
            else []
        )
        if len(generic_candidates) == 1:
            pointer = int(generic_candidates[0]["methodPointerVa"], 16)
            mapped["genericBodyCandidate"] = generic_candidates[0]
            mapping_status = "mappedGenericInstantiation"
        elif len(generic_candidates) > 1:
            mapped["mappingStatus"] = "ambiguousGenericInstantiations"
            mapped["genericBodyCandidates"] = generic_candidates
            mapped_targets.append(mapped)
            continue
        else:
            mapping_status = "mapped" if pointer else "nullPointer"
        file_offset, section, rva = pe.file_offset_for_va(pointer)
        scan_size, next_pointer = estimate_scan_size(pointer, sorted_all_pointers, args.max_scan_bytes)
        direct_calls, unresolved_call_count = scan_direct_calls(
            pe,
            pointer,
            scan_size,
            method_by_pointer,
            catalog_target_keys,
            include_unresolved=args.include_unresolved_calls,
            arg_context_window=args.arg_context_window,
        )
        mapped.update(
            {
                "mappingStatus": mapping_status,
                "methodPointerVa": f"0x{pointer:x}",
                "methodPointerRva": f"0x{rva:x}",
                "fileOffset": f"0x{file_offset:x}" if file_offset is not None else "",
                "section": section,
                "scanBytes": scan_size,
                "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else "",
                "headBytes": pe.bytes_at_va(pointer, args.head_bytes).hex(" "),
                "directCalls": direct_calls,
                "unresolvedDirectCallCount": unresolved_call_count,
            }
        )
        if body_summary_re and (
            body_summary_re.search(str(row.get("method") or ""))
            or body_summary_re.search(str(row.get("type") or ""))
        ):
            mapped["methodBodySummary"] = build_method_body_summary(
                row,
                pe.bytes_at_va(pointer, scan_size),
                pointer,
                method_by_pointer,
                pe=pe,
                max_instructions=args.body_summary_max_instructions,
            )
        mapped_targets.append(mapped)

    direct_call_edges = collect_direct_call_edges(mapped_targets)
    return {
        "metadata": {
            "metadataPath": str(metadata_path),
            "gameAssembly": str(args.gameassembly),
            "imageBase": f"0x{pe.image_base:x}",
            "catalog": str(args.catalog),
        },
        "settings": {
            "codeRegistration": f"0x{code_reg:x}",
            "headBytes": args.head_bytes,
            "maxScanBytes": args.max_scan_bytes,
            "includeUnresolvedCalls": args.include_unresolved_calls,
            "argContextWindow": args.arg_context_window,
            "bodySummaryMethodRegex": args.body_summary_method_regex,
            "bodySummaryMaxInstructions": args.body_summary_max_instructions,
        },
        "codeRegistration": code_reg_summary,
        "summary": {
            "catalogBodyTargetCount": len(catalog.get("bodyTargets", [])),
            "mappedTargetCount": sum(
                1
                for row in mapped_targets
                if row["mappingStatus"] in {"mapped", "mappedGenericInstantiation"}
            ),
            "codeGenModuleCount": len(modules),
            "genericInstantiationIndex": generic_index_summary,
            "resolvedDirectCallCount": sum(len(row.get("directCalls", [])) for row in mapped_targets),
            "dialogRelatedDirectCallCount": sum(
                1
                for row in mapped_targets
                for call in row.get("directCalls", [])
                if call.get("isDialogRelated")
            ),
            "catalogTargetDirectCallCount": sum(
                1
                for row in mapped_targets
                for call in row.get("directCalls", [])
                if call.get("isCatalogTarget")
            ),
            "importantDirectCallEdgeCount": len(direct_call_edges),
            "optionFlowFactCount": sum(
                len((row.get("methodBodySummary") or {}).get("optionFlowFacts") or [])
                for row in mapped_targets
            ),
        },
        "directCallEdges": direct_call_edges,
        "bodyTargets": mapped_targets,
    }


def collect_direct_call_edges(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for row in rows:
        caller = {
            "methodIndex": row["methodIndex"],
            "type": row["type"],
            "method": row["method"],
            "methodPointerVa": row.get("methodPointerVa", ""),
        }
        for call in row.get("directCalls", []):
            resolved = call.get("resolved") or []
            if not resolved:
                continue
            important = call.get("isCatalogTarget") or any(
                target["type"].endswith(".DialogUtils") for target in resolved
            )
            if not important:
                continue
            edges.append(
                {
                    "caller": caller,
                    "offset": call["offset"],
                    "targetVa": call["targetVa"],
                    "callees": resolved,
                    "isCatalogTarget": call.get("isCatalogTarget", False),
                    "isDialogRelated": call.get("isDialogRelated", False),
                    "argumentContext": call.get("argumentContext", {}),
                }
            )
    edges.sort(
        key=lambda edge: (
            edge["caller"]["type"],
            edge["caller"]["method"],
            edge["offset"],
        )
    )
    return edges


def call_label(call: dict[str, Any]) -> str:
    resolved = call.get("resolved") or []
    if not resolved:
        return f"+0x{call['offset']:x} -> {call['targetVa']}"
    labels = [
        f"{row['methodIndex']}:{row['type'].split('.')[-1]}.{row['method']}"
        for row in resolved[:3]
    ]
    suffix = " target" if call.get("isCatalogTarget") else ""
    return f"+0x{call['offset']:x} -> {call['targetVa']} ({'; '.join(labels)}){suffix}"


def argument_context_summary(context: dict[str, Any] | None) -> str:
    if not context:
        return ""
    writes = context.get("argRegisterWrites") or {}
    parts: list[str] = []
    for register in ARG_REGISTERS:
        instr = writes.get(register)
        if not instr:
            continue
        write = instr.get("write") or {}
        value = write.get("value") or instr.get("text") or "?"
        parts.append(f"{register}={value} @ +0x{instr.get('offset', 0):x}")
    return "; ".join(parts)


def nearby_context_summary(context: dict[str, Any] | None, *, limit: int = 6) -> str:
    if not context:
        return ""
    nearby = context.get("nearbyInstructions") or []
    texts = [
        f"+0x{instr.get('offset', 0):x} {instr.get('text', '')}"
        for instr in nearby[-limit:]
        if instr.get("text")
    ]
    return " | ".join(texts)


def compact_instruction(instr: dict[str, Any]) -> dict[str, Any]:
    row = {
        "offset": instr.get("offset"),
        "va": instr.get("va"),
        "text": instr.get("text"),
        "bytes": instr.get("bytes"),
    }
    for key in ("originUses", "memoryOrigins"):
        if instr.get(key):
            row[key] = instr[key]
    return row


def instruction_window(
    instructions: list[dict[str, Any]],
    offset: int,
    *,
    before: int = 6,
    after: int = 6,
) -> list[dict[str, Any]]:
    if not instructions:
        return []
    nearest_index = min(
        range(len(instructions)),
        key=lambda index: abs(int(instructions[index].get("offset") or 0) - offset),
    )
    start = max(0, nearest_index - before)
    end = min(len(instructions), nearest_index + after + 1)
    return [compact_instruction(instr) for instr in instructions[start:end]]


def summarize_instruction_window(window: list[dict[str, Any]], *, limit: int = 10) -> str:
    return " | ".join(
        f"+0x{int(instr.get('offset') or 0):x} {instr.get('text', '')}"
        for instr in window[:limit]
        if instr.get("text")
    )


def branch_target_from_text(text: str) -> str:
    match = re.match(r"(?:jcc|je|jne|jmp|call) (0x[0-9a-f]+)$", text)
    return match.group(1) if match else ""


def memory_access_kind(text: str, expr: str) -> str:
    if re.match(r"mov(?:sd|aps|sxd|zx)? \[" + re.escape(expr) + r"\],", text):
        return "write"
    return "read"


def option_flow_fact_lines(facts: list[dict[str, Any]]) -> list[str]:
    if not facts:
        return []
    lines = ["- option-flow facts:"]
    for fact in facts:
        kind = fact.get("kind") or "fact"
        summary = fact.get("summary") or ""
        lines.append(f"  - {kind}: {summary}")
        interesting_keys = [
            "selectedOptionField",
            "runtimeOptionField",
            "currentOptionField",
            "candidateOptionField",
            "activeClipField",
            "readInstruction",
            "writeInstruction",
            "compareOffset",
            "zeroCompareOffset",
            "gateOffset",
        ]
        parts: list[str] = []
        for key in interesting_keys:
            value = fact.get(key)
            if value not in (None, "", {}):
                if isinstance(value, int):
                    value = f"+0x{value:x}"
                parts.append(f"{key}={value}")
        if parts:
            lines.append(f"    - detail: `{' ; '.join(parts)}`")
        for call_key in (
            "lookupCall",
            "chooseCall",
            "wrapperCall",
            "allTimelinePlayableCall",
            "activeClipListCall",
            "setDialogOptionCall",
            "disableLoopCall",
            "triggerCall",
        ):
            call = fact.get(call_key) or {}
            if not call:
                continue
            resolved = call.get("resolved") or []
            label = "; ".join(
                f"{row.get('methodIndex')}:{str(row.get('type') or '').split('.')[-1]}.{row.get('method')}"
                for row in resolved[:3]
            ) or call.get("targetVa", "")
            offset = call.get("offset")
            offset_text = f"+0x{int(offset):x}" if isinstance(offset, int) else str(offset)
            lines.append(f"    - {call_key}: `{offset_text} -> {call.get('targetVa', '')} {label}`")
        for call_list_key in (
            "outerTimelinePlayableEnumerationCalls",
            "innerClipEnumerationCalls",
            "activeClipFilterCalls",
            "outClipAppendCalls",
            "playableGraphCalls",
            "timelineActiveClipCalls",
            "timelineIntervalTreeCalls",
            "cutsceneRootRetimingCalls",
            "resultListSetupCalls",
            "timelineRootCollectionCalls",
            "playableResolutionCalls",
            "resultAppendCalls",
            "iteratorSetupCalls",
            "playableLookupCalls",
        ):
            calls = fact.get(call_list_key) or []
            if not calls:
                continue
            pieces: list[str] = []
            for call in calls[:8]:
                resolved = call.get("resolved") or []
                label = ";".join(
                    f"{row.get('methodIndex')}:{str(row.get('type') or '').split('.')[-1]}.{row.get('method')}"
                    for row in resolved[:2]
                ) or call.get("targetVa", "")
                classification = (call.get("targetPreview") or {}).get("classification")
                if classification:
                    label = f"{label}[{classification}]"
                offset = call.get("offset")
                offset_text = f"+0x{int(offset):x}" if isinstance(offset, int) else str(offset)
                pieces.append(f"{offset_text}->{label}")
            lines.append(f"    - {call_list_key}: `{' | '.join(pieces)}`")
            for call in calls[:3]:
                preview = call.get("targetPreview") or {}
                preview_text = summarize_instruction_window(preview.get("instructions") or [], limit=6)
                if not preview_text:
                    continue
                offset = call.get("offset")
                offset_text = f"+0x{int(offset):x}" if isinstance(offset, int) else str(offset)
                classification = preview.get("classification") or "unclassified"
                lines.append(f"    - {call_list_key} preview {offset_text} ({classification}): `{preview_text}`")
        if fact.get("interpretation"):
            lines.append(f"    - interpretation: `{fact.get('interpretation')}`")
        selected_argument = fact.get("selectedOptionClipArgument") or {}
        if selected_argument:
            lines.append(
                "    - selectedOptionClipArgument: "
                f"`+0x{int(selected_argument.get('offset') or 0):x} "
                f"{selected_argument.get('text', '')}`"
            )
        for source_key in ("startTimeSource", "endTimeSource"):
            source = fact.get(source_key) or {}
            if source:
                lines.append(
                    f"    - {source_key}: "
                    f"`{source.get('xmm')} <- [{source.get('baseRegister')}{source.get('field')}]`"
                )
        for instr_key in ("startTimeLoad", "endTimeLoad", "endTimeAdjustment", "selectedClipStore"):
            instr = fact.get(instr_key) or {}
            if instr:
                lines.append(
                    f"    - {instr_key}: `+0x{int(instr.get('offset') or 0):x} {instr.get('text', '')}`"
                )
        for instr_list_key in (
            "playableClipListLoads",
            "activeClipCollectionState",
            "timelineTimeArgumentState",
            "timelinePointQueryState",
            "timelineRangeQueryState",
            "resultListAccesses",
            "timelineRootAndLoopState",
            "stateLoads",
            "candidateChecks",
            "setToDisableState",
            "rangeArgumentState",
            "playableTraversalState",
            "activeRangeClipState",
        ):
            instr_text = summarize_instruction_window(fact.get(instr_list_key) or [], limit=16)
            if instr_text:
                lines.append(f"    - {instr_list_key}: `{instr_text}`")
        for slice_key in ("selectedOptionClipSlice", "startSourceSlice", "endSourceSlice"):
            slice_text = summarize_instruction_window(fact.get(slice_key) or [], limit=24)
            if slice_text:
                lines.append(f"    - {slice_key}: `{slice_text}`")
        window_text = summarize_instruction_window(fact.get("window") or [], limit=8)
        if window_text:
            lines.append(f"    - window: `{window_text}`")
    return lines


def method_body_summary_lines(summary: dict[str, Any]) -> list[str]:
    if not summary:
        return []
    lines = [
        (
            f"- body decode: {summary.get('instructionCount', 0)} instr; "
            f"unknown: {summary.get('unknownInstructionCount', 0)}; "
            f"first ret: "
            f"{'+0x' + format(summary['firstRetOffset'], 'x') if summary.get('firstRetOffset') is not None else 'n/a'}"
        )
    ]
    origins = summary.get("initialRegisterOrigins") or {}
    if origins:
        origin_text = "; ".join(f"{reg}={origin}" for reg, origin in sorted(origins.items()))
        lines.append(f"- initial args: `{origin_text}`")
    field_origins = summary.get("fieldLikeOrigins") or []
    if field_origins:
        top = "; ".join(
            f"{row['origin']} x{row['count']}"
            for row in field_origins[:8]
        )
        lines.append(f"- field-like access origins: `{top}`")
    param_flow = summary.get("paramFlow") or {}
    for origin, flow_rows in list(param_flow.items())[:6]:
        flow_text = " | ".join(
            f"+0x{int(row.get('offset') or 0):x} {row.get('text')}"
            for row in flow_rows[:8]
        )
        if flow_text:
            lines.append(f"- `{origin}` flow: `{flow_text}`")
    field_accesses = summary.get("fieldAccesses") or []
    if field_accesses:
        lines.append("- field-like accesses:")
        for access in field_accesses[:12]:
            lines.append(
                "  - "
                f"+0x{int(access.get('offset') or 0):x} "
                f"{access.get('kind', 'read')} {access.get('origin', '')}: "
                f"`{access.get('text', '')}`"
            )
    lines.extend(option_flow_fact_lines(summary.get("optionFlowFacts") or []))
    windows = summary.get("controlFlowWindows") or []
    if windows:
        lines.append("- decision windows:")
        for window in windows[:10]:
            title = window.get("label") or f"+0x{int(window.get('offset') or 0):x}"
            window_text = summarize_instruction_window(window.get("instructions") or [])
            if window_text:
                lines.append(f"  - {title}: `{window_text}`")
    calls = summary.get("calls") or []
    if calls:
        lines.append("- decoded body calls:")
        for call in calls[:10]:
            lines.append(f"  - {call_label(call)}")
            arg_summary = argument_context_summary(call.get("argumentContext"))
            if arg_summary:
                lines.append(f"    - args: `{arg_summary}`")
    return lines


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    meta = report["metadata"]
    summary = report["summary"]
    code_reg = report["codeRegistration"]
    lines = [
        "# Dialog Option Flow GameAssembly Body Targets",
        "",
        f"Catalog: `{meta['catalog']}`",
        f"GameAssembly: `{meta['gameAssembly']}`",
        f"Metadata: `{meta['metadataPath']}`",
        "",
        f"- image base: `{meta['imageBase']}`",
        f"- CodeRegistration: `{code_reg['va']}`",
        f"- codegen modules: {summary['codeGenModuleCount']:,}",
        f"- catalog body targets: {summary['catalogBodyTargetCount']:,}",
        f"- mapped body targets: {summary['mappedTargetCount']:,}",
        f"- resolved direct calls: {summary['resolvedDirectCallCount']:,}",
        f"- dialog-related direct calls: {summary['dialogRelatedDirectCallCount']:,}",
        f"- direct calls to catalog targets: {summary['catalogTargetDirectCallCount']:,}",
        f"- important direct-call edges: {summary['importantDirectCallEdgeCount']:,}",
        f"- extracted option-flow facts: {summary.get('optionFlowFactCount', 0):,}",
        "",
        "## Important Direct-Call Edges",
        "",
        "",
    ]
    if not report["directCallEdges"]:
        lines.append("- none")
    else:
        for edge in report["directCallEdges"]:
            caller = edge["caller"]
            callee_labels = [
                f"{callee['methodIndex']}:{callee['type'].split('.')[-1]}.{callee['method']}"
                for callee in edge["callees"][:3]
            ]
            suffix = " target" if edge.get("isCatalogTarget") else ""
            lines.append(
                f"- `{caller['type'].split('.')[-1]}.{caller['method']}` "
                f"+0x{edge['offset']:x} -> {edge['targetVa']} "
                f"({'; '.join(callee_labels)}){suffix}"
            )
            arg_summary = argument_context_summary(edge.get("argumentContext"))
            if arg_summary:
                lines.append(f"  - args: `{arg_summary}`")
            nearby_summary = nearby_context_summary(edge.get("argumentContext"))
            if nearby_summary:
                lines.append(f"  - nearby: `{nearby_summary}`")
    lines.extend(["", "## Targets", ""])
    for row in report["bodyTargets"]:
        params = ", ".join(row.get("parameters") or [])
        lines.extend(
            [
                f"### `{row['type']}.{row['method']}({params})`",
                "",
                f"- methodIndex: {row['methodIndex']}; token: `{row['token']}`",
                f"- mapping: {row['mappingStatus']}; slot: {row.get('moduleMethodSlot', '')}",
            ]
        )
        if row["mappingStatus"] not in {"mapped", "mappedGenericInstantiation"}:
            lines.extend(["", ""])
            continue
        generic_body = row.get("genericBodyCandidate") or {}
        if generic_body:
            specs = generic_body.get("instantiations") or []
            lines.append(
                "- generic body: "
                f"{len(specs)} MethodSpec row(s) share this entry point"
            )
        lines.extend(
            [
                f"- VA: `{row['methodPointerVa']}`; RVA: `{row['methodPointerRva']}`; file: `{row['fileOffset']}`",
                f"- scan bytes: {row['scanBytes']}; next method pointer: `{row['nextMethodPointerVa']}`",
                f"- head bytes: `{row['headBytes']}`",
            ]
        )
        body_lines = method_body_summary_lines(row.get("methodBodySummary") or {})
        if body_lines:
            lines.extend(body_lines)
        interesting_calls = [
            call
            for call in row.get("directCalls", [])
            if call.get("isCatalogTarget") or call.get("isDialogRelated")
        ]
        if interesting_calls:
            lines.append("- direct calls:")
            for call in interesting_calls:
                lines.append(f"  - {call_label(call)}")
                arg_summary = argument_context_summary(call.get("argumentContext"))
                if arg_summary:
                    lines.append(f"    - args: `{arg_summary}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--code-registration", default=hex(DEFAULT_CODE_REGISTRATION))
    parser.add_argument(
        "--include-generic-instantiations",
        action="store_true",
        help="Also name generic method instantiations from MetadataRegistration. "
             "Off by default so existing reports stay byte-identical; enable it "
             "before concluding that a call target has no consumer.",
    )
    parser.add_argument(
        "--metadata-registration",
        default="",
        help="MetadataRegistration VA. Empty re-derives it from the codegen "
             "registration call site.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--head-bytes", type=int, default=32)
    parser.add_argument("--max-scan-bytes", type=int, default=0x4000)
    parser.add_argument("--arg-context-window", type=int, default=96)
    parser.add_argument("--body-summary-method-regex", default=DEFAULT_BODY_SUMMARY_METHOD_RE)
    parser.add_argument("--body-summary-max-instructions", type=int, default=80)
    parser.add_argument("--include-unresolved-calls", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.markdown, report)
    summary = report["summary"]
    print(f"mapped body targets: {summary['mappedTargetCount']}/{summary['catalogBodyTargetCount']}")
    print(f"resolved direct calls: {summary['resolvedDirectCallCount']}")
    print(f"dialog-related direct calls: {summary['dialogRelatedDirectCallCount']}")
    print(f"direct calls to catalog targets: {summary['catalogTargetDirectCallCount']}")
    print(f"wrote JSON: {args.out}")
    print(f"wrote Markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
