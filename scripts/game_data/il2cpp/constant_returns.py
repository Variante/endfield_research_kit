"""Prove a named enum literal survives one checked normal return path.

The selected caller returns the declared Int32-backed enum directly. A named
Boolean guard's false result falls through JNE to a complete EAX constant and
a plain epilogue. This does not classify the guard's other path or live calls.
"""
from __future__ import annotations

import re
import struct
from typing import Any

from .reference_layouts import NativeReferenceContext


def check_enum_return_after_false_call(index: Any, body: Any,
                                      spec: dict[str, Any]) -> str | None:
    from .body_claims import ClaimError

    label = "enum-return-after-false-call"
    try:
        enum_type, member, guard = spec["type"], spec["member"], spec["call"]
        context = NativeReferenceContext(index.image, index=index)
        if not context.is_enum(enum_type) or context.field(enum_type + "::value__")[1] != "int":
            return f"{label}: selected return enum must have an Int32 underlying field"
        value = index.enum_member_id(enum_type, member)
        if type(value) is not int or not -(1 << 31) <= value < (1 << 31):
            return f"{label}: selected enum member is outside Int32"

        def selected_method(pointer: int, symbol: str) -> Any:
            declarations = [row for row in index.names_by_pointer.get(pointer, [])
                            if f"{row.get('type')}.{row.get('method')}" == symbol]
            if len(declarations) != 1 or type(declarations[0].get("methodIndex")) is not int:
                raise ValueError("unique selected method declaration is missing")
            method = index.metadata.methods[declarations[0]["methodIndex"]]
            owner = index.metadata.types[method.declaring_type]
            if (index.metadata.type_full_name(owner) + "." + index.metadata.string(method.name_index) != symbol
                    or method.generic_container_index >= 0 or owner.generic_container_index >= 0):
                raise ValueError("selected owner/method identity or nongeneric ABI is missing")
            return method

        caller = selected_method(body.pointer, body.symbol)
        result = index.pe.bytes_at_va(context.type_pointer(caller.return_type), 16)
        if (len(result) != 16 or result[10] != 0x11 or result[11] & 0x7f
                or context.type_name(caller.return_type) != enum_type):
            return f"{label}: caller does not return the selected undecorated enum"
    except (ValueError, KeyError, IndexError, ClaimError) as exc:
        return f"{label}: selected declaration proof failed: {exc}"

    def adjacent(left: dict[str, Any], right: dict[str, Any]) -> bool:
        try:
            return int(left["va"], 16) + len(bytes.fromhex(left["bytes"])) == int(right["va"], 16)
        except (ValueError, TypeError, KeyError):
            return False

    for at, row in enumerate(body.rows):
        match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
        raw = bytes.fromhex(str(row.get("bytes") or ""))
        if not match or len(raw) != 5 or raw[0] != 0xe8:
            continue
        pointer = int(match[1], 16)
        if (int(row["va"], 16) + 5 + int.from_bytes(raw[1:], "little", signed=True) != pointer
                or guard not in index.names_of(pointer)):
            continue
        try:
            callee = selected_method(pointer, guard)
            result = index.pe.bytes_at_va(context.type_pointer(callee.return_type), 16)
            if len(result) != 16 or result[10] != 2 or result[11] & 0x7f:
                continue
        except (ValueError, KeyError, IndexError, ClaimError):
            continue
        tail = body.rows[at + 1:at + 13]
        if len(tail) < 4 or tail[0].get("text") != "test al, al" or bytes.fromhex(tail[0].get("bytes", "")) != b"\x84\xc0":
            continue
        branch = bytes.fromhex(tail[1].get("bytes", ""))
        if not (len(branch) == 6 and branch[:2] == b"\x0f\x85"
                or len(branch) == 2 and branch[:1] == b"\x75"):
            continue
        constant = bytes.fromhex(tail[2].get("bytes", ""))
        literal = (constant == b"\xb8" + struct.pack("<i", value)
                   and tail[2].get("text") in {f"mov eax, 0x{value & 0xffffffff:x}", f"mov eax, {value}"})
        zero = value == 0 and constant == b"\x33\xc0" and tail[2].get("text") == "xor eax, eax"
        if not (literal or zero):
            continue
        branch_va = int(tail[1]["va"], 16)
        target = branch_va + len(branch) + int.from_bytes(branch[2:] if len(branch) == 6 else branch[1:], "little", signed=True)
        for end in range(3, len(tail)):
            following = tail[end]
            text = str(following.get("text") or "")
            if text == "ret" and bytes.fromhex(following.get("bytes", "")) == b"\xc3":
                selected = [row, *tail[:end + 1]]
                if (all(adjacent(a, b) for a, b in zip(selected, selected[1:]))
                        and not int(tail[2]["va"], 16) <= target <= int(following["va"], 16)):
                    return None
                break
            if not re.fullmatch(r"(?:mov (?:rbx|rsi|rdi|rbp|r1[2-5]), \[rsp\+0x[0-9a-f]+\]|add rsp, 0x[0-9a-f]+|pop (?:rbx|rsi|rdi|rbp|r1[2-5])|nop)", text):
                break
    return f"{label}: no bounded EAX return of {enum_type}.{member} after false {guard}"
