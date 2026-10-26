"""Reprove named EC profile roles from current source, without old cold owners.

The strict plain formatter regenerator cannot attribute historical disjoint
windows without their old unwind directory. This lane instead proves the
current conditional read programs by named consumer role. It retains the
anonymous parser vocabulary and grants no live formatter or whole-file claim.
"""
from __future__ import annotations

import copy
import json
import re
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import (
    generic_method_candidates, generic_type_carrier, method_spec_record, method_spec_usage_index,
)
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.native_image import native_validation_failure, open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.levelscript_two_routes_native import _window
from scripts.game_data.memorypack import buff_blackboard_double_native, pooled_source_helper
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive

SCHEMA = "endfield.buff-ec-profile-roles-native.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_ec_profiles_native.json"
PROJECTION_PATH = CONTRACTS_DIR / "buff_ec_native.json"
LABEL = "buffEcProfileRoles"


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(f"{LABEL}.{check}:{str(detail)[:700]}")


def first_difference(expected, actual, path="$"):
    """Bound a failed reviewed declaration to its first deterministic location."""
    if type(expected) is not type(actual):
        return {"path": path, "expectedType": type(expected).__name__, "actualType": type(actual).__name__}
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            return {"path": path, "expectedKeys": sorted(expected), "actualKeys": sorted(actual)}
        for key in sorted(expected):
            if expected[key] != actual[key]:
                return first_difference(expected[key], actual[key], path + "." + key)
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return {"path": path, "expectedLength": len(expected), "actualLength": len(actual)}
        for index, (left, right) in enumerate(zip(expected, actual)):
            if left != right:
                return first_difference(left, right, f"{path}[{index}]")
    elif expected != actual:
        return {"path": path, "expected": str(expected)[:200], "actual": str(actual)[:200]}
    return None


def raw(row):
    return bytes.fromhex(row["bytes"].replace(" ", ""))


def va(row):
    return int(row["va"], 16) if isinstance(row["va"], str) else row["va"]


def one(rows, predicate, label):
    found = [r for r in rows if predicate(r)]
    need(label, len(found) == 1, {"matches": len(found)})
    return found[0]


def site(row, base):
    return [va(row) - base, raw(row).hex().upper()]


def family_windows(image, entry):
    """Authenticate full unwind ranges without interpreting embedded data."""
    base = image.pe.image_base
    # Persist the exact JSON value that validators will later reload. The
    # unwind inventory includes version-number dictionary keys as integers.
    selected = json.loads(json.dumps(image.unwind_index.family(entry)))
    windows = []
    for part in selected["ranges"]:
        start, end = part["runtimeTriple"][:2]
        windows.append(_window(image, base + start, base + end, "complete current role unwind range"))
    return selected, windows


def family(image, entry):
    base = image.pe.image_base
    selected, windows = family_windows(image, entry)
    rows = []
    for part in selected["ranges"]:
        start, end = part["runtimeTriple"][:2]
        rows.extend(decode_string_source_instructions(image.mapper,
            image.pe.bytes_at_va(base + start, end - start), base + start))
    return selected, windows, rows


def fast_path(rows, header, reader, offsets, *, terminal_target=None):
    """Walk every instruction of the explicitly conditional normal read path."""
    need('path.literal-terminal-target', terminal_target is None or type(terminal_target) is int and terminal_target > 0)
    by_at = {va(r): r for r in rows}
    need("path.duplicate", len(by_at) == len(rows))
    at, seen, flags, decisions = va(header), [], None, []
    count = raw(header)[-1]
    while True:
        need("path.boundary-or-loop", at in by_at and at not in seen, hex(at))
        row = by_at[at]
        need("path.unknown", not row["text"].startswith("db "), row)
        seen.append(at)
        text = row["text"]
        flow = control_transfer(row)
        end = at + len(raw(row))
        if flow["kind"] == "conditional":
            code = flow["conditionCode"]
            prior = flags or ""
            if at == va(header) + len(raw(header)) and code in (4, 5):
                taken, reason = code == 4, "member count equals reviewed count"
            elif re.fullmatch(rf"cmp dword \[{reader}\+{offsets['bufferLength']:#x}\], 0x[14]", prior) and code in (12, 13):
                taken, reason = code == 13, "enough contiguous buffered input"
            elif re.fullmatch(r"(?:sub \w+, 0x[14]|add \w+, -0x[14])", prior) and code in (8, 9):
                taken, reason = code == 9, "remaining input after read is nonnegative"
            elif prior.startswith("test ") and code in (4, 5):
                left, _, right = prior[5:].partition(", ")
                need("path.self-test", left == right, prior)
                taken, reason = code == 5, "selected reference/formatter is nonnull"
            elif prior.startswith("cmp qword ") and prior.endswith(", 0x0") and code in (4, 5):
                taken, reason = code == 5, "selected context/storage is initialized and nonnull"
            elif prior.startswith("cmp dword ") and "[rip " in prior and prior.endswith(", 0x0") and code in (4, 5):
                taken, reason = code == 4, "selected reference barrier guard is zero"
            elif re.fullmatch(r"cmp dword \[\w+\+0xe0\], 0x0", prior) and code in (4, 5):
                taken, reason = code == 5, "selected class is initialized"
            else:
                need("path.unreviewed-branch", False, [hex(at), prior, code])
            need("path.edge", flow["target"] in by_at, hex(flow["target"]))
            decisions.append({"instruction": row, "condition": reason, "taken": taken})
            at = flow["target"] if taken else end
        elif flow["kind"] == "jump":
            if terminal_target is not None and flow['target'] == terminal_target:
                need('path.terminal-external', flow['target'] not in by_at)
                break
            need("path.jump", flow["target"] in by_at, flow)
            at = flow["target"]
        elif flow["kind"] == "return":
            break
        else:
            need("path.transfer", flow["kind"] in ("next", "call", "indirectCall", "registerCall"), flow)
            at = end
        if text.split()[0] in ("cmp", "test", "sub", "add", "xor", "and", "or", "inc", "dec", "shl", "shr", "sar"):
            flags = text
        if flow["kind"] in ("call", "indirectCall", "registerCall"):
            flags = None
    return [by_at[a] for a in seen], decisions


def contexts(image, rows, *, allow_value_generic_arguments=False):
    """Every raw-backed RIP qword MethodSpec load, for all destination registers."""
    need('context.explicit-value-generic-option',type(allow_value_generic_arguments)is bool)
    out = []
    for row in rows:
        b = raw(row)
        if len(b) != 7 or b[0] not in (0x48, 0x4c) or b[1] != 0x8b or b[2] & 0xc7 != 5:
            continue
        cell = va(row) + 7 + struct.unpack_from("<i", b, 3)[0]
        usage = image.pe.bytes_at_va(cell, 8)
        try:
            index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
        except ValueError:
            continue
        spec = list(struct.unpack("<iii", image.pe.bytes_at_va(int(image.registration["methodSpecs"], 16) + index * 12, 12)))
        arguments = image.instantiations.resolve(spec[2]).arguments
        need("context.arity", len(arguments) == 1, spec)
        argument = bytes.fromhex(arguments[0].raw_type_record_hex)
        need("context.ordinary-argument", len(argument) == 16 and not argument[11] & 0x7f)
        definition = struct.unpack_from("<Q", argument)[0]
        generic = None
        if argument[10] == 0x15:
            cr = image.pe.bytes_at_va(definition, 32)
            br = image.pe.bytes_at_va(struct.unpack_from("<Q", cr)[0], 16)
            base_tag=0x12
            if allow_value_generic_arguments and (argument[11]&0x80 or br[10]==0x11):
                need('context.exact-value-generic-carriers',argument[10:12]==bytes((0x15,0x80))and br[10:12]==bytes((0x11,0x80)))
                base_tag=0x11
            carrier = generic_type_carrier(argument, cr, br, type_pointer=arguments[0].type_pointer_va,
                                           type_count=len(image.metadata.types), source=LABEL,base_type_tag=base_tag)
            definition = carrier["baseDefinitionIndex"]
            nested = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
            generic = {"carrierRawHex": cr.hex().upper(), "baseRawHex": br.hex().upper(),
                       "elementInstantiationIndex": nested.index,
                       "elementArguments": [a.raw_type_record_hex for a in nested.arguments]}
        method = image.metadata.methods[spec[0]]
        out.append({"instructionRva": va(row) - image.pe.image_base, "instructionHex": b.hex().upper(),
                    "cellVa": cell, "usageRawHex": usage.hex().upper(), "methodSpecIndex": index,
                    "methodSpec": spec, "argumentRawHex": argument.hex().upper(),
                    "typeDefinition": definition, "typeName": image.type_name(definition), "generic": generic,
                    "typeKind": argument[10], "fullTypeName": runtime_type_name(image.pe, image.metadata,
                        arguments[0].type_pointer_va), "methodOwner": image.type_name(method.declaring_type),
                    "methodName": image.metadata.string(method.name_index),
                    "register": row["text"].split(",")[0].split()[1]})
    return out


def check_clone_registration(image, method, equivalent, code, table):
    """Join just the reviewed MethodSpec/table slot/pointer, without a name inventory."""
    registration = image.registration
    index = equivalent["methodSpecIndex"]
    need("clones.spec-index", type(index) is int and 0 <= index < registration["methodSpecsCount"])
    address = int(registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
                             registration["genericInstsCount"], source=LABEL, offset=address)
    need("clones.method-definition", spec[0] == method[0], spec)
    rows = generic_method_candidates(table, registration["genericMethodTableCount"],
        registration["methodSpecsCount"], {index}, code["genericMethodPointersCount"],
        code["invokerPointersCount"], source=LABEL, offset=int(registration["genericMethodTable"], 16))
    need("clones.unique-registration", len(rows) == 1, len(rows))
    slot = rows[0]["indices"][0]
    need("clones.pointer-slot", slot == equivalent["genericMethodPointerSlot"], slot)
    pointer = struct.unpack("<Q", image.pe.bytes_at_va(int(code["genericMethodPointers"], 16) + slot * 8, 8))[0]
    need("clones.physical-entry", pointer == image.pe.image_base + equivalent["rva"], hex(pointer))


def clone_facts(image, inputs):
    fact = json.loads((CONTRACTS_DIR / "memorypack_reader_clones_native.json").read_bytes())
    need("clones.schema", fact.get("schema") == "endfield.memorypack-reader-clones-native.v3"
         and fact.get("status") == "exact-current-build")
    need("clones.native-inputs", fact["nativeInputs"] == inputs)
    code = image.mapper.code_registration_summary(image.pe, image.code_registration)
    count = image.registration["genericMethodTableCount"]
    need("clones.table-count", type(count) is int and 0 <= count <= 1_000_000)
    table = image.pe.bytes_at_va(int(image.registration["genericMethodTable"], 16), count * 16)
    selected = {}
    for name in ("ReadValue", "ReadPackable"):
        claim = "MemoryPack.MemoryPackReader." + name
        c = one(fact["clones"], lambda c: c["claim"] == claim and c["resultAbi"] == "reference", "clones." + name)
        method = c["equivalentMethod"]
        image.validate_method_row(method)
        need("clones.claim", method[1:3] == ["MemoryPack.MemoryPackReader", name])
        equivalent = c["equivalentBody"]
        check_clone_registration(image, method, equivalent, code, table)
        windows = [w for root in c["bodyRoots"] for w in family(image, root)[1]]
        need("clones.full-families", {(w["startRva"], w["endRva"]) for w in windows}
             == {(w["startRva"], w["endRva"]) for w in c["codeWindows"]})
        image.check_windows(c["codeWindows"])
        image.check_instruction_windows(c["instructions"])
        selected[name] = c
    rows = family(image, selected["ReadValue"]["equivalentBody"]["rva"])[2]
    provider = one(list(enumerate(rows)), lambda pair: pair[0] > 1 and pair[1]["text"].startswith("call 0x")
        and rows[pair[0] - 1]["text"] == "mov rcx, [rcx]"
        and re.fullmatch(r"mov rcx, \[\w+\+0x38\]", rows[pair[0] - 2]["text"]), "provider.call")
    dispatch = one(list(enumerate(rows)), lambda pair: pair[0] > 3 and pair[1]["text"].startswith("call 0x")
        and rows[pair[0] - 4]["text"] == "mov ecx, 0x5", "provider.dispatch")
    selected["providerTarget"] = control_transfer(provider[1])["target"]
    selected["dispatchTarget"] = control_transfer(dispatch[1])["target"]
    return selected


def source_offsets(image):
    selected = NativeReferenceContext(image)
    result = {name: selected.field("MemoryPack.MemoryPackReader::" + name)[2] - 16
              for name in ("currentPtr", "bufferLength", "advancedCount", "consumed")}
    need("reader.offsets", len(set(result.values())) == 4 and all(0 <= n < 128 for n in result.values()))
    return result


def last_write(path, index, register):
    from scripts.game_data.il2cpp.initializer_control import _ALIASES
    for row in reversed(path[:index]):
        head, _, rest = row["text"].partition(" ")
        declared = (row.get("write") or {}).get("register")
        if declared is not None and _ALIASES.get(declared, declared) == register:
            return row
        if head not in ("cmp", "test", "bt", "push", "nop", "ret", "int3", "prefetch", "call") and not head.startswith("j"):
            destination = rest.split(",")[0]
            if _ALIASES.get(destination, destination) == register:
                return row
        if head in ("mul", "div", "idiv", "cdq", "cqo", "cdqe") and register in ("rax", "rdx"):
            return row
        if head == "xchg" and _ALIASES.get(rest.split(", ")[-1], rest.split(", ")[-1]) == register:
            return row
        if head == "call" and register in ("rax", "rcx", "rdx", "r8", "r9", "r10", "r11"):
            return None
    return None


def inline_read(path, index, reader, offsets):
    """Prove the load and all four fast cursor/counter changes, instruction by instruction."""
    load = path[index + 1]
    zero = load.get("byteMemoryZeroExtensionOperation")
    move = load.get("memoryOperation")
    if zero:
        address, width = zero["sourceAddress"], zero["memoryReadBytes"]
    else:
        need("inline.value-load", move and move["direction"] == "load", load)
        address, width = move["address"], move["memoryBytes"]
    need("inline.width", address["base"] == "rax" and address["index"] is None
         and address["displacement"] == 0 and width in (1, 4), load)
    remaining = path[index + 2]
    match = re.fullmatch(rf"mov (\w+), \[{reader}\+{offsets['bufferLength']:#x}\]", remaining["text"])
    need("inline.remaining", bool(match), remaining)
    register = match.group(1)
    need("inline.subtract", path[index + 3]["text"] in (
        f"sub {register}, {width:#x}", f"add {register}, -{width:#x}"), path[index + 3])
    branch = control_transfer(path[index + 4])
    need("inline.nonnegative", branch["kind"] == "conditional" and branch["conditionCode"] in (8, 9))
    expected = []
    for name, bits in (("currentPtr", "qword"), ("advancedCount", "dword"), ("consumed", "dword")):
        operand = f"{bits} [{reader}+{offsets[name]:#x}]"
        expected.append(f"inc {operand}" if width == 1 else f"add {operand}, {width:#x}")
    expected.append(f"mov [{reader}+{offsets['bufferLength']:#x}], {register}")
    actual = [r["text"] for r in path[index + 5:index + 9]]
    need("inline.cursor-program", actual == expected, {"expected": expected, "actual": actual})
    return width, path[index:index + 9]


def wrapper_header(image, rows, header, reader, offsets):
    """Own the one-byte header and the FF clear path separately from member reads."""
    from scripts.game_data.il2cpp.initializer_control import _ALIASES
    base = image.pe.image_base
    register = header["text"][4:].split(",")[0]
    null = one(rows, lambda r: r["text"] == f"cmp {register}, -0x1", "header.null-compare")
    by_at = {va(r): r for r in rows}
    candidates = []
    for i, row in enumerate(rows[:-1]):
        if va(row) >= va(null) or row["text"] != f"mov rax, [{reader}+{offsets['currentPtr']:#x}]":
            continue
        load = rows[i + 1].get("byteMemoryZeroExtensionOperation", {})
        dest = load.get("destinationRegister")
        if dest and _ALIASES.get(dest, dest) == _ALIASES.get(register, register):
            candidates.append(row)
    start = one(candidates, lambda r: True, "header.source-byte")
    at, path = va(start), []
    while at != va(null):
        need("header.source-boundary", at in by_at and at not in {va(r) for r in path} and len(path) < 20)
        row = by_at[at]
        path.append(row)
        flow = control_transfer(row)
        if flow["kind"] == "conditional":
            need("header.source-nonnegative", flow["conditionCode"] in (8, 9))
            at = flow["target"] if flow["conditionCode"] == 9 else at + len(raw(row))
        else:
            need("header.source-transfer", flow["kind"] == "next", row)
            at += len(raw(row))
    width, program = inline_read(path, 0, reader, offsets)
    need("header.width-and-complete", width == 1 and program == path)
    edge = by_at[va(null) + len(raw(null))]
    branch = control_transfer(edge)
    need("header.ff-edge", branch["kind"] == "conditional" and branch["conditionCode"] == 4
         and branch["target"] in by_at)
    output = one(rows, lambda r: r["text"] == "mov rdi, rdx", "header.output-save")
    at, tail, stores, calls, barrier_targets = branch["target"], [], [], [], []
    while True:
        need("header.null-boundary", at in by_at and at not in {va(r) for r in tail} and len(tail) < 25,
             {"at": hex(at), "tail": [r['text'] for r in tail]})
        row = by_at[at]
        tail.append(row)
        if row["text"] == "mov qword [rdi], 0x0":
            stores.append(row)
        else:
            need("header.null-instruction", row["text"].startswith(("mov rcx, rdi", "mov rbx,", "mov rbp,",
                "mov rsi,", "mov r14,", "mov r15,", "add rsp,", "pop ", "ret", "call 0x", "jmp 0x")), row)
        flow = control_transfer(row)
        if flow["kind"] == "return":
            break
        if flow["kind"] == "call":
            argument = last_write(tail, len(tail) - 1, "rcx")
            need("header.null-call-argument", argument is not None and argument["text"] == "mov rcx, rdi")
            calls.append(row)
            barrier_targets.append(flow["target"] - base)
        if flow["kind"] == "jump" and flow["target"] not in by_at:
            argument = last_write(tail, len(tail) - 1, "rcx")
            need("header.null-tail-argument", argument is not None and argument["text"] == "mov rcx, rdi")
            need("header.null-restored-tail", len(tail) >= 3 and tail[-2]["text"].startswith("pop "))
            calls.append(row)
            barrier_targets.append(flow["target"] - base)
            break
        need("header.null-transfer", flow["kind"] in ("next", "call", "jump"), row)
        at = flow["target"] if flow["kind"] == "jump" else at + len(raw(row))
    need("header.null-clear-and-call", len(stores) == 1 and len(calls) == 1)
    # Authenticate the selected null return/tail frame. No normal-path field
    # saves occur before the FF guard, so its initial prologue owns these homes.
    prologue = []
    for row in rows:
        if row["text"].startswith("cmp byte [rip"):
            break
        prologue.append(row)
    delta, saved, restored = 0, {}, set()
    for row in prologue:
        text, move = row["text"], row.get("memoryOperation", {})
        if text.startswith("push "):
            delta -= 8
            saved[text[5:]] = delta
        elif text.startswith("sub rsp, "):
            delta -= int(text.split(", ")[1], 16)
        else:
            address = move.get("address", {})
            need("header.prologue-home", move.get("direction") == "store" and move["memoryBytes"] == 8
                 and address.get("base") == "rsp" and address.get("index") is None
                 and not address.get("ripRelative"), row)
            saved[move["register"]] = delta + address["displacement"]
    need("header.prologue-frame", saved and delta <= -32 and (8 + delta) % 16 == 0)
    initial_delta = delta
    for row in tail:
        text, move = row["text"], row.get("memoryOperation", {})
        if text.startswith("pop "):
            register = text[4:]
            need("header.pop-home", saved.get(register) == delta and register not in restored, row)
            restored.add(register)
            delta += 8
        elif text.startswith("add rsp, "):
            delta += int(text.split(", ")[1], 16)
        elif move.get("direction") == "load" and move.get("register") in saved:
            address = move["address"]
            need("header.restore-home", move["memoryBytes"] == 8 and address["base"] == "rsp"
                 and address["index"] is None and delta + address["displacement"] == saved[move["register"]]
                 and move["register"] not in restored, row)
            restored.add(move["register"])
        if control_transfer(row)["kind"] == "call":
            need("header.call-frame", delta <= -32 and (8 + delta) % 16 == 0)
    need("header.complete-return-frame", delta == 0 and restored == set(saved), [delta, saved, restored])
    return {"sourceProgram": [site(r, base) for r in path], "nullCompare": site(null, base),
            "nullEdge": site(edge, base), "outputSave": site(output, base),
            "nullReturnProgram": [site(r, base) for r in tail], "wireBytes": 1,
            "referenceBarrierTargetRva": barrier_targets[0],
            "nullFrameBytes": -initial_delta, "nullSavedHomes": saved,
            "condition": "selected buffered header path, compatible output storage and ordinary ABI/callee behavior"}


def profile_events(image, claim, path, context_rows, reader, offsets, targets, aliases):
    """Account for every reader source call or inline dereference on this path."""
    base = image.pe.image_base
    by_context = {base + c["instructionRva"]: c for c in context_rows}
    events, used, provider = [], set(), None
    for index, row in enumerate(path):
        text = row["text"]
        if text == f"mov rax, [{reader}+{offsets['currentPtr']:#x}]":
            width, program = inline_read(path, index, reader, offsets)
            events.append({"kind": "byte" if width == 1 else "scalar32", "wireBytes": width,
                           "instruction": site(row, base), "program": [site(r, base) for r in program]})
        flow = control_transfer(row)
        if flow["kind"] != "call":
            continue
        target = flow["target"]
        previous = last_write(path, index, "rcx")
        reader_call = previous is not None and previous["text"] == f"mov rcx, {reader}"
        event = None
        if target == targets["providerTarget"]:
            need("provider.context-program", index >= 2 and path[index - 1]["text"] == "mov rcx, [rcx]")
            match = re.fullmatch(r"mov rcx, \[(\w+)\+0x38\]", path[index - 2]["text"])
            need("provider.companion-load", bool(match))
            load = last_write(path, index - 2, match.group(1))
            need("provider.static-companion", load is not None and va(load) in by_context, load)
            provider = by_context[va(load)]
            need("provider.ReadValue", provider["methodOwner"] == "MemoryPack.MemoryPackReader"
                 and provider["methodName"] == "ReadValue" and provider["typeKind"] == 0x12)
        elif target == targets["dispatchTarget"]:
            need("provider.dispatch-prefix", provider is not None and index >= 4)
            prefix = [r["text"] for r in path[index - 4:index]]
            need("provider.slot-reader-output", prefix[0] == "mov ecx, 0x5"
                 and re.fullmatch(r"lea r9, \[rsp\+0x[0-9a-f]+\]", prefix[1])
                 and prefix[2:] == [f"mov r8, {reader}", "mov rdx, rax"], prefix)
            output = prefix[1].removeprefix("lea r9, ")
            zeros = [r for r in path[:index] if r["text"] == f"mov qword {output}, 0x0"]
            need("provider.zero-output", len(zeros) == 1)
            event = {"kind": aliases.get(provider["fullTypeName"]), "context": provider,
                     "instruction": site(row, base), "mode": "typed-provider-slot-five",
                     "providerCallTargetRva": targets["providerTarget"] - base}
            used.add(provider["instructionRva"])
            provider = None
        elif reader_call:
            if target in (targets["bool"], targets["int32"]):
                event = {"kind": "byte" if target == targets["bool"] else "scalar32",
                         "wireBytes": 1 if target == targets["bool"] else 4,
                         "instruction": site(row, base), "mode": "proved-primitive"}
                load = last_write(path, index, "rdx")
                context = by_context.get(va(load)) if load else None
                if context:
                    selected = NativeReferenceContext(image)
                    need("primitive.enum-context", context["methodName"] == "ReadUnmanaged"
                         and context["methodOwner"] == "MemoryPack.MemoryPackReader"
                         and selected.is_enum(context["fullTypeName"]) and target == targets["int32"])
                    event["context"] = context
                    used.add(context["instructionRva"])
            elif target == targets["string"]:
                event = {"kind": "byte-payload", "wireBytes": 4,
                         "instruction": site(row, base), "mode": "proved-pooled-string"}
            elif target in (targets["ReadValue"]["targetRva"] + base, targets["ReadPackable"]["targetRva"] + base):
                load = last_write(path, index, "rdx")
                context = by_context.get(va(load)) if load else None
                method = "ReadValue" if target == targets["ReadValue"]["targetRva"] + base else "ReadPackable"
                need("direct.context", context is not None and context["methodName"] == method
                     and context["methodOwner"] == "MemoryPack.MemoryPackReader", load)
                event = {"kind": aliases.get(context["fullTypeName"]), "context": context,
                         "instruction": site(row, base), "mode": "proved-reference-clone"}
                used.add(context["instructionRva"])
            else:
                need("source.unproved-reader-call", False, hex(target - base))
        if event:
            need("source.named-type-role", event.get("kind") is not None, event.get("context"))
            events.append(event)
    expected = claim["anonymousReadOrder"]
    need("source.read-count-order", [e["kind"] for e in events] == expected,
         {"owner": claim["ownerType"], "expected": expected, "actual": [e["kind"] for e in events]})
    need("source.all-contexts-bound", used == {c["instructionRva"] for c in context_rows},
         {"unbound": sorted({c['instructionRva'] for c in context_rows} - used)})
    for member, event in zip(claim["members"], events):
        if "context" in event:
            need("source.full-declared-type", event["context"]["fullTypeName"] == member["declaredType"],
                 [member, event["context"]["fullTypeName"]])
    return events


def finder_null_role(image, method, offsets):
    """Reprove the current high-byte role, without claiming an old cold owner."""
    base = image.pe.image_base
    selected, windows, rows = family(image, method[3])
    prologue = [one(rows, lambda r: r["text"] == text, "finder." + text)
                for text in ("xor r12d, r12d", "mov rbx, r8", "mov rdi, rdx")]
    candidates = []
    for i, row in enumerate(rows):
        if i < 3 or i + 2 >= len(rows):
            continue
        if (row["text"].startswith("call 0x") and rows[i - 3]["text"].startswith("lea rdx, [rbp+")
                and raw(rows[i - 2])[:4] == bytes.fromhex("66448965")
                and rows[i - 1]["text"] == "mov rcx, rdi"
                and rows[i + 1]["text"] == "test al, al"
                and raw(rows[i + 2])[:2] == bytes.fromhex("0F84")):
            candidates.append(i)
    need("finder.header-call", len(candidates) == 1, candidates)
    i = candidates[0]
    primary_end = selected["ranges"][0]["runtimeTriple"][1] + base
    primary = [r for r in rows if base + method[3] <= va(r) < primary_end]
    entry_flow = control_transfer(primary[-1])
    need("finder.initialized-entry", entry_flow["kind"] == "conditional"
         and entry_flow["conditionCode"] == 5 and entry_flow["target"] == va(rows[i - 3]))
    need("finder.prologue-control", all(control_transfer(r)["kind"] == "next" for r in primary[:-1]))
    target = control_transfer(rows[i])["target"]
    by_at = {va(r): r for r in rows}
    edge = control_transfer(rows[i + 2])
    need("finder.false-target", edge["target"] in by_at)
    clear = by_at[edge["target"]]
    need("finder.output-clear", raw(clear) == bytes.fromhex("4C8923"))
    helper, hw, hr = family(image, target - base)
    need("finder.helper-decode", not any(r["text"].startswith("db ") for r in hr))
    need("finder.zero-preserved", not any(re.search(r"\br12\w*\b", r["text"]) for r in hr))
    for text in ("mov r14, rdx", "mov rbx, rcx"):
        one(hr, lambda r: r["text"] == text, "finder.helper-abi")
    compare = one(hr, lambda r: raw(r) == bytes.fromhex("4080FFFA"), "finder.fa-compare")
    pos = hr.index(compare)
    hb = {va(r): r for r in hr}
    above_equal = control_transfer(hr[pos + 1])
    need("finder.unsigned-compare", above_equal["kind"] == "conditional" and above_equal["conditionCode"] == 3)
    not_equal_row = hb.get(above_equal["target"])
    need("finder.not-equal-row", not_equal_row is not None)
    not_equal = control_transfer(not_equal_row)
    need("finder.high-not-equal", not_equal["kind"] == "conditional" and not_equal["conditionCode"] == 5)
    zero = hb.get(not_equal["target"])
    need("finder.false-zero", zero is not None and raw(zero) == bytes.fromhex("33C0"))
    zp = hr.index(zero)
    need("finder.zero-tag-output", raw(hr[zp + 1]) == bytes.fromhex("66418906"))
    end = control_transfer(hr[zp + 2])
    need("finder.false-return-jump", end["kind"] == "jump" and end["target"] in hb)
    at, tail = end["target"], []
    while True:
        row = hb[at]
        need("finder.false-epilogue", row["text"].startswith(("mov rbx,", "mov rsi,", "mov rdi,", "add rsp,", "pop r14", "ret")), row)
        tail.append(row)
        if control_transfer(row)["kind"] == "return":
            break
        at += len(raw(row))
        need("finder.false-tail-boundary", at in hb and len(tail) < 10)
    load = one(hr, lambda r: raw(r) == bytes.fromhex("0FB638"), "finder.source-byte")
    li = hr.index(load)
    # The whole fast first-byte cursor program uses the metadata-derived slots.
    width, program = inline_read(hr, li - 1, "rbx", offsets)
    need("finder.header-width", width == 1)
    return {"callerMethod": method, "callerFamily": selected,
            "callerPrologue": [site(r, base) for r in prologue],
            "callerInitializedEntryProgram": [site(r, base) for r in primary],
            "callerHeaderAndFalseEdge": [site(r, base) for r in rows[i - 3:i + 3]],
            "callerOutputClear": site(clear, base), "helperEntryRva": target - base,
            "helperFamily": helper, "helperSourceProgram": [site(r, base) for r in program],
            "helperHighByteDecision": [site(r, base) for r in (compare, hr[pos + 1], not_equal_row, zero, hr[zp + 1], hr[zp + 2])],
            "helperFalseReturn": [site(r, base) for r in tail], "falseFirstByteRange": [251, 255]}, windows + hw


def derive(image, inputs, reviewed, projection):
    """Derive all current native facts from stable reviewed role declarations."""
    need("schema", reviewed.get("schema") == SCHEMA and reviewed.get("projection") == PROJECTION_PATH.name)
    need("profile-set", [c["profile"] for c in reviewed["claims"]] == ["member10", "member13", "member8", "member3"])
    base = image.pe.image_base
    methods = [_method_row(image, [0, owner, name, 1]) for owner, name in reviewed["methodRoles"]]
    offsets = source_offsets(image)
    targets = clone_facts(image, inputs)
    reference = json.loads((CONTRACTS_DIR / "skill_custom_root_motion_native.json").read_bytes())
    need("primitives.native-inputs", reference["nativeInputs"] == inputs)
    from scripts.game_data.skill_timeline_routes_regenerate import reference_primitives
    primitives = reference_primitives(reference)
    targets.update(bool=base + primitives["bool"], int32=base + primitives["int32"], string=base + primitives["bytes"])
    prove_primitive(image, targets["bool"], "bool-byte")
    prove_primitive(image, targets["int32"], "int32")
    pooled_source_helper.validate_on_image(image, targets["string"], inputs)
    scalar = buff_blackboard_double_native.derive(image, inputs)
    scalar_reviewed = json.loads(buff_blackboard_double_native.CONTRACT_PATH.read_bytes())
    need("scalar.dependency-current", scalar == scalar_reviewed)
    aliases = {"Beyond.Gameplay.Core.TargetSettings": "member13", "Beyond.Gameplay.Core.DirectionSettings": "member8",
               "Beyond.Gameplay.Core.Selector+SelectorData": "member3", "Beyond.Blackboard+BlackboardDouble": "scalar-payload",
               "Beyond.Gameplay.Core.Selector+Finder+Data": "delegated-finder"}
    profiles, all_contexts, all_windows = [], [], []
    for claim in reviewed["claims"]:
        method = one(methods, lambda m: m[1:3] == [claim["ownerType"], claim["methodName"]], "profile.method")
        wrappers = [w for w in image.memorypack_wrappers.values() if w.name == claim["ownerType"]]
        wrapper = one(wrappers, lambda w: True, "profile.wrapper")
        actual = [{"name": m.name, "declaredType": m.declared_type} for m in wrapper.members]
        need("profile.declarations", actual == claim["members"], {"owner": claim["ownerType"], "actual": actual})
        for member in claim["members"]:
            if member["declaredType"].startswith("System.Collections.Generic.List`1<"):
                aliases[member["declaredType"]] = "delegated-list"
        selected, windows, rows = family(image, method[3])
        need("profile.decode", not any(r["text"].startswith("db ") for r in rows), claim["ownerType"])
        header = one(rows, lambda r: r["text"].startswith("cmp ") and r["text"].endswith(", " + hex(len(actual)))
                     and raw(r)[-1] == len(actual), "profile.header")
        register = one(rows, lambda r: r["text"] in ("mov rbx, rcx", "mov rdi, rcx"), "profile.reader-save")["text"].split()[1].rstrip(",")
        path, decisions = fast_path(rows, header, register, offsets)
        header_proof = wrapper_header(image, rows, header, register, offsets)
        loaded = contexts(image, rows)
        events = profile_events(image, claim, path, loaded, register, offsets, targets, aliases)
        all_contexts.extend(c for c in loaded if c["methodName"] != "ReadUnmanaged")
        profiles.append({"profile": claim["profile"], "method": method, "family": selected,
                         "header": site(header, base), "readerRegister": register, "events": events,
                         "headerProof": header_proof,
                         "selectedProgram": [site(r, base) for r in path],
                         "selectedConditions": [{"instruction": site(d["instruction"], base),
                              "condition": d["condition"], "taken": d["taken"]} for d in decisions]})
    need("headers.shared-reference-barrier", len({p['headerProof']['referenceBarrierTargetRva'] for p in profiles}) == 1)
    for method in methods:
        all_windows.extend(family(image, method[3])[1])
    finder = one(methods, lambda m: m[1:3] == reviewed["finderRole"], "finder.method")
    null, windows = finder_null_role(image, finder, offsets)
    all_windows.extend(windows)
    unique = {}
    for window in all_windows:
        unique.setdefault((window["startRva"], window["endRva"]), window)
    out = copy.deepcopy(projection)
    need("projection.read-orders", out["anonymousReadOrder"] == {
        **{c["profile"]: c["anonymousReadOrder"] for c in reviewed["claims"]},
        "scalar-payload": ["byte-payload", "byte", "scalar32"]})
    shape = list(projection["nestedContexts"][0])
    annotated = [dict(w, requiredRoleContract=CONTRACT_PATH.name) for w in unique.values()]
    out.update(schemaVersion=2, methods=methods, codeWindows=annotated,
               nestedContexts=[{k: c[k] for k in shape} for c in all_contexts],
               roleContract=CONTRACT_PATH.name)
    current = copy.deepcopy(reviewed)
    current.update(status="exact-current-build", nativeInputs=dict(inputs),
                   proof={"readerOffsets": offsets, "profiles": profiles, "finderNull": null,
                          "scalarDependency": buff_blackboard_double_native.CONTRACT_PATH.name})
    return current, out


def validate_on_image(image, inputs, *, projection=None):
    """Mandatory semantic gate for any consumer of the EC projection."""
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL)
    need("native-inputs", contract["nativeInputs"] == inputs)
    projection = projection if projection is not None else json.loads(PROJECTION_PATH.read_bytes())
    need("required-role-contract", projection.get("schemaVersion") == 2
         and projection.get("roleContract") == CONTRACT_PATH.name
         and projection.get("codeWindows")
         and all(w.get("requiredRoleContract") == CONTRACT_PATH.name for w in projection["codeWindows"]))
    actual, projected = derive(image, inputs, contract, projection)
    need("reviewed-proof", actual == contract, first_difference(contract, actual))
    need("projection-current", projected == projection, first_difference(projection, projected))
    return {"status": "validated", "nativeInputs": inputs, "roleContract": CONTRACT_PATH.name,
            "profiles": {p["profile"]: len(p["events"]) for p in actual["proof"]["profiles"]},
            "evidenceBoundary": contract["evidenceBoundary"]}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    if (gameassembly is None) != (metadata is None):
        raise ValueError(f"{LABEL}.native:both-selected-paths-required")
    try:
        contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL)
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
                                            gameassembly=gameassembly, metadata=metadata)
        if gate.status != "validated":
            return {"status": gate.status, "detail": gate.detail}
        image = open_native_image(gate.gameassembly, gate.metadata)
        _publication_gate(image, inputs)
        result = validate_on_image(image, inputs)
        _publication_gate(image, inputs)
        return result
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        return native_validation_failure(error, label=LABEL, source_path=CONTRACT_PATH)
