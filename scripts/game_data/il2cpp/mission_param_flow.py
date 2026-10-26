"""Bounded symbolic checks for leaf Param source-selector programs.

The caller authenticates selected method registration, bytes and a concrete
paramSource cell witness. No open generic offsets or runtime context are
inferred here. Equality-only leaves partition all Int32 inputs by their
compared constants; one other input represents the remaining equivalence class.
"""
from __future__ import annotations

from typing import Any


def prove_source_selector(raw: bytes, source_offset: int) -> dict[str, Any]:
    if not raw or len(raw) > 32 or not 0 <= source_offset <= 127:
        raise ValueError("param_selector.bounds: require a 1..32 byte leaf and witnessed byte displacement")
    pending, instructions, constants, occupied = [0], {}, set(), set()
    while pending:
        at = pending.pop()
        if at in instructions:
            continue
        if not 0 <= at < len(raw) or at in occupied:
            raise ValueError(f"param_selector.target: offset={at} outside window or inside instruction")
        tail = raw[at:]
        if tail.startswith(bytes([0x83, 0x79, source_offset])) and len(tail) >= 4:
            value = int.from_bytes(tail[3:4], "little", signed=True)
            size, op, arg = 4, "cmp", value
            constants.add(value)
        elif tail.startswith(bytes([0x81, 0x79, source_offset])) and len(tail) >= 7:
            value = int.from_bytes(tail[3:7], "little", signed=True)
            size, op, arg = 7, "cmp", value
            constants.add(value)
        elif tail[:1] in (b"\x74", b"\x75") and len(tail) >= 2:
            size, op, arg = 2, "je" if tail[0] == 0x74 else "jne", at+2+int.from_bytes(tail[1:2], "little", signed=True)
        elif tail.startswith(b"\x0f\x94\xc0"):
            size, op, arg = 3, "sete", None
        elif tail.startswith(b"\x32\xc0"):
            size, op, arg = 2, "false", None
        elif tail.startswith(b"\xb0\x01"):
            size, op, arg = 2, "true", None
        elif tail.startswith(b"\xc3"):
            size, op, arg = 1, "ret", None
        else:
            raise ValueError(f"param_selector.opcode: offset={at} bytes={tail[:8].hex()}")
        cells = set(range(at, at+size))
        if cells & occupied or at+size > len(raw):
            raise ValueError(f"param_selector.overlap: offset={at}")
        occupied |= cells
        instructions[at] = size, op, arg
        if op != "ret":
            pending.append(at+size)
        if op in ("je", "jne"):
            pending.append(arg)
    if occupied != set(range(len(raw))):
        raise ValueError("param_selector.coverage: window contains unvisited bytes")
    other = next(v for v in range(-33, 34) if v not in constants)
    outcomes = {}
    for source in sorted(constants | {other}):
        at, zero, result, seen = 0, None, None, set()
        while at not in seen:
            seen.add(at)
            size, op, arg = instructions[at]
            if op == "cmp":
                zero = source == arg
            elif op in ("je", "jne", "sete"):
                if zero is None:
                    raise ValueError("param_selector.flags: use before comparison")
                if op == "sete":
                    result = zero
                elif zero == (op == "je"):
                    at = arg
                    continue
            elif op in ("false", "true"):
                result = op == "true"
                zero = True if op == "false" else zero
            elif op == "ret":
                if result is None:
                    raise ValueError("param_selector.return: AL is undefined")
                outcomes[source] = result
                break
            at += size
        else:
            raise ValueError("param_selector.loop: no returning leaf path")
    if outcomes[other]:
        raise ValueError("param_selector.complement: expected finite source membership")
    return {"selectedSources": [v for v in sorted(constants) if outcomes[v]],
            "checkedBytes": len(raw), "checkedInputClasses": len(outcomes),
            "boundary": "Complete equality-only Int32 selector leaf; coherent witnessed Param cell required. No value resolution or live type/context selection."}
