"""Bounded static Dictionary initializer and Int32 lookup-return programs.

Callers supply owned native instruction rows and an authenticated decoder for
the exact MethodSpec usage passed at a call. Shared generic entry addresses do
not supply closed arguments. Nothing here establishes runtime initialization,
an executed lookup, or the meaning of an enum/value pair.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from .integer_addressing import decode_lea_address


def dictionary_add_blocks(instructions: list[dict], *, add_targets: set[int],
                          expected_type: str, decode_context: Any,
                          validator: str) -> Iterable[tuple[dict, list[dict], dict]]:
    block_start = 0
    for call_index, instruction in enumerate(instructions):
        call = re.fullmatch(r"call 0x([0-9a-f]+)", str(instruction.get("text") or ""))
        if not call or int(call.group(1), 16) not in add_targets:
            continue
        block = instructions[block_start:call_index]
        slot = None
        for ordinal in reversed(range(len(block))):
            row = block[ordinal]
            text = str(row.get("text") or "")
            load = re.fullmatch(r"mov r9, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]", text)
            if load:
                slot = int(load.group(1), 16)
                break
            if (text.startswith("call ") or re.match(
                    r"(?:mov|lea|xor|pop|add|sub|and|or) r9(?:d|w|b)?(?:,|$)", text)):
                break
        if slot is None:
            raise ValueError(f"validator={validator} gate=add_method_context "
                             "expected='RIP MethodSpec load into r9 without clobber' "
                             f"actual='missing' source={instruction.get('va')}")
        try:
            context = decode_context(slot, int(call.group(1), 16))
        except ValueError as exc:
            raise ValueError(f"validator={validator} gate=add_method_context "
                             f"expected={expected_type!r} actual={str(exc)[:600]!r} "
                             f"source={instruction.get('va')}") from exc
        block_start = call_index + 1
        if context.get("declaringType") == expected_type:
            yield instruction, block, context


def _selector(block: list[dict]) -> int | None:
    for row in reversed(block):
        text = str(row.get("text") or "")
        literal = re.fullmatch(r"mov edx, 0x([0-9a-f]+)", text)
        if literal:
            return int(literal.group(1), 16)
        if text == "xor edx, edx":
            return 0
        if text.startswith("call ") or re.match(r"(?:mov|lea|xor|and|or|add|sub) (?:rdx|edx)(?:,|$)", text):
            return None
    return None


def parse_enum_int_initializer(instructions: list[dict], *, add_targets: set[int],
                               expected_type: str, decode_context: Any,
                               validator: str) -> list[dict]:
    rows = []
    for call, block, context in dictionary_add_blocks(
            instructions, add_targets=add_targets, expected_type=expected_type,
            decode_context=decode_context, validator=validator):
        selector = _selector(block)
        value = None
        program = None
        for ordinal in reversed(range(len(block))):
            row = block[ordinal]
            text = str(row.get("text") or "")
            literal = re.fullmatch(r"mov r8d, 0x([0-9a-f]+)", text)
            if literal:
                value = int(literal.group(1), 16)
                program = row
                break
            if text == "xor r8d, r8d":
                value = 0
                program = row
                break
            if text.startswith(("lea r8,", "lea r8d,")):
                raw = bytes.fromhex(str(row.get("bytes") or ""))
                decoded = decode_lea_address(raw, 0, int(row["va"], 16))
                base_value = _selector(block[:ordinal])
                if decoded and decoded[1] == len(raw) and base_value is not None:
                    operation = decoded[0]["addressOperation"]
                    if (operation["destination"] in {"r8", "r8d"} and operation["destinationBits"] in {32, 64}
                            and operation["base"] == "rdx" and operation["index"] is None
                            and not operation["ripRelative"]):
                        value = base_value + operation["displacement"]
                        program = {**row, "decodedAddress": operation}
                break
            if text.startswith("call ") or re.match(r"(?:mov|lea|xor|and|or|add|sub) r8(?:d|w|b)?(?:,|$)", text):
                break
        if selector is None or value is None:
            raise ValueError(f"validator={validator} gate=enum_int_arguments "
                             "expected='literal enum and Int32 value' "
                             f"actual={(selector, value)!r} source={call.get('va')}")
        value &= 0xFFFFFFFF
        value = value - (1 << 32) if value >= 1 << 31 else value
        rows.append({"selectorValue": selector, "value": value,
                     "dictionaryAddCallVa": call.get("va"), "dictionaryAddContext": context,
                     "valueProgram": program})
    if not rows or len({row["selectorValue"] for row in rows}) != len(rows):
        raise ValueError(f"validator={validator} gate=enum_int_rows expected='nonempty unique selectors' "
                         f"actual={[row['selectorValue'] for row in rows]!r}")
    return rows


def prove_masked_int32_lookup_return(raw: bytes, output_displacement: int) -> dict:
    """NEG AL; SBB EAX,EAX; AND EAX,[RSP+out]; balanced epilogue; RET.

Only a Bool-returning selected TryGetValue call can provide AL's 0/1
precondition. That call, its dictionary, key, output slot and initial value
are separate obligations of the caller.
"""
    if (not 0 <= output_displacement <= 0x7F or len(raw) != 14
            or raw[:8] != bytes.fromhex("F6 D8 1B C0 23 44 24") + bytes([output_displacement])
            or raw[8:11] != bytes.fromhex("48 83 C4")
            or raw[11] > 0x7F or raw[12:] != bytes.fromhex("5B C3")):
        raise ValueError("native-static-dictionary.lookup-return: expected complete Bool mask, selected Int32 out slot and plain epilogue")
    return {"status": "validated", "falseReturn": 0, "trueReturn": "selected Int32 output",
            "outputStackDisplacement": output_displacement, "stackReleaseBytes": raw[11],
            "programHex": raw.hex().upper(), "conditions": "AL is the selected Bool lookup result; balanced frame and output-slot ownership checked by caller"}
