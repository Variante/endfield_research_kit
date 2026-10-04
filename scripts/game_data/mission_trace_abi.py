"""Prove string-wrapper passing from selected native instructions, not size.

Layout and native argument representation are separate facts. A single
reference value type can arrive indirectly even when its unboxed size is eight
bytes. This bounded analysis requires its entry argument (or its first pointer
load) to reach the first parameter of a selected System.String.op_Equality.
Only register copies and a zero-offset pointer load carry identity; joins keep
facts common to every incoming path and calls discard volatile registers.
"""
from __future__ import annotations

import re
from typing import Any


def prove_string_argument_mode(instructions: list[dict[str, Any]], *,
                               argument_register: str, equality_pointer: int,
                               mode: str) -> dict[str, Any]:
    if mode not in {"inlineValue", "indirectValue"} or not 0 < len(instructions) <= 4096:
        raise ValueError("unsupported or unbounded string argument proof")
    positions = {int(row["va"], 16): index for index, row in enumerate(instructions)}
    if len(positions) != len(instructions):
        raise ValueError("duplicate native instruction address")
    states: dict[int, dict[str, str]] = {0: {argument_register: "argument"}}
    pending = [0]
    steps = 0
    while pending:
        index = pending.pop(0)
        steps += 1
        if steps > len(instructions) * 32:
            raise ValueError("native argument proof iteration budget exceeded")
        row, state = instructions[index], dict(states[index])
        text = row["text"]
        mnemonic = text.split(" ", 1)[0]
        supported = {"mov", "movzx", "movsx", "movsxd", "lea", "xor", "sub", "add", "and", "or",
                     "shl", "shr", "sar", "inc", "dec", "cmp", "test", "push", "pop", "ret", "int3", "nop", "call"}
        if mnemonic not in supported and not re.fullmatch(r"j[a-z]+", mnemonic):
            raise ValueError(f"unsupported instruction in argument proof: {text}")
        if mnemonic == "call":
            for register in ("rax", "rcx", "rdx", "r8", "r9", "r10", "r11"):
                state.pop(register, None)
        else:
            write = row.get("write")
            if write:
                register, value = write["register"], write["value"]
                tag = state.get(value) if mnemonic == "mov" else None
                load = re.fullmatch(r"\[(r(?:[abcd]x|[sd]i|[bs]p|[89]|1[0-5]))(?:\+0x0)?\]", value)
                if mnemonic == "mov" and load and state.get(load.group(1)) == "argument":
                    tag = "pointee"
                # Partial-register writes destroy a pointer, including its aliases.
                aliases = {alias: root for root, variants in {
                    "rax": ("eax", "ax", "al", "ah"), "rcx": ("ecx", "cx", "cl", "ch"),
                    "rdx": ("edx", "dx", "dl", "dh"), "rbx": ("ebx", "bx", "bl", "bh"),
                    "rsi": ("esi", "si", "sil"), "rdi": ("edi", "di", "dil"),
                    "rsp": ("esp", "sp", "spl"), "rbp": ("ebp", "bp", "bpl"),
                }.items() for alias in variants}
                canonical = aliases.get(register, register)
                canonical = re.sub(r"(r(?:[89]|1[0-5]))[dwb]$", r"\1", canonical)
                if register != canonical or not tag:
                    state.pop(canonical, None)
                else:
                    state[canonical] = tag
        branch = re.fullmatch(r"(j[a-z]+) 0x([0-9a-f]+)", text)
        if mnemonic.startswith("j") and branch is None:
            raise ValueError(f"argument proof has an unmodeled branch: {text}")
        if mnemonic in {"ret", "int3"} and text != mnemonic:
            raise ValueError(f"argument proof has an unmodeled terminator: {text}")
        successors = []
        if branch:
            target = positions.get(int(branch.group(2), 16))
            if target is None:
                raise ValueError("argument proof branch leaves bounded body")
            successors.append(target)
        if text not in {"ret", "int3"} and not (branch and branch.group(1) == "jmp") and index + 1 < len(instructions):
            successors.append(index + 1)
        for successor in successors:
            previous = states.get(successor)
            merged = dict(state) if previous is None else {key: value for key, value in previous.items() if state.get(key) == value}
            if previous is None or merged != previous:
                states[successor] = merged
                pending.append(successor)
    expected = "pointee" if mode == "indirectValue" else "argument"
    calls = [row["offset"] for index, row in enumerate(instructions)
             if row["text"] == f"call 0x{equality_pointer:x}" and states.get(index, {}).get("rcx") == expected]
    if not calls:
        raise ValueError(f"{mode}: entry argument does not reach selected string equality as {expected}")
    return {"mode": mode, "inputRegister": argument_register, "consumer": "System.String.op_Equality(string,string)",
            "consumerArgumentIndex": 0, "consumerCallOffsets": calls,
            "pointerLoads": 1 if mode == "indirectValue" else 0,
            "evidence": "selected bounded body; register copies and zero-offset load; control-flow joins; volatile-call clobbers"}
