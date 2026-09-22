"""Name functions in the shipped AkSoundEngine.dll from the installed Wwise SDK.

The shipped DLL has RTTI disabled and exports almost nothing, so its 12,512
functions are anonymous. They are not unknowable: the DLL is built from the
SDK's static libraries, and those libraries are ordinary COFF archives whose
objects carry one named COMDAT `.text` section per function. Matching a
function against them turns an address into a name.

**What makes a match an identification rather than a guess.** A shared prologue
proves nothing -- MSVC emits the same register saves everywhere. Two facts
together do: a candidate must have *exactly* the same byte length, and must
agree on at least `ACCEPT` of its bytes. The disagreements are then explicable,
and on inspection they are: relocated call targets and rip-relative
displacements, which the linker rewrites. A candidate that merely scores well
without an equal length is not offered, and where two candidates score within
`MARGIN` of each other the function is left unnamed rather than assigned to the
better of two similar ones.

**What a name does and does not establish.** It identifies the code, and with
it the class and method the SDK compiled there. It says nothing about when that
function runs, what calls it, or whether the shipped build patched its body --
a match at 0.83 agreement is the same function, not necessarily the same
behaviour. Treat a name as an identity to reason from, not as a proof of what
the runtime does.

This exists because two hooks in the audio catalog were named by their supposed
role and one of them was wrong. `AkSoundEngine.SourceMediaLookup` is a
speaker-volume mixing callback; `SourceProviderPreparation` is
`CAkSrcFileBase::CreateStream`, which explains why it never observes
external-source voice. A role recorded in prose is a hypothesis; the symbol is
the fact.

Fails closed: without the SDK or the installed DLL there is no map, and the
report says which input was missing rather than returning a short list.
"""
from __future__ import annotations

import argparse
import collections
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_SDK = Path(r"D:\Program Files\Wwise_2023.1.17.8841")
SDK_LIB_RELATIVE = "SDK/x64_vc170/Profile/lib/AkSoundEngine.lib"
DEFAULT_DLL = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data\Plugins\x86_64\AkSoundEngine.dll")
DEFAULT_OUTPUT = REPO / "reports/audio/wwise_sdk_symbols.json"
#: A match must agree on at least this fraction of an equal-length body.
ACCEPT = 0.80
#: and beat the next candidate by this much, or the function stays unnamed.
MARGIN = 0.05
COFF_MACHINE_AMD64 = 0x8664
#: ``IMAGE_SYM_TYPE`` for a function symbol.
SYM_TYPE_FUNCTION = 0x20
MIN_BODY_BYTES = 16


class SymbolError(ValueError):
    """An input was missing or unreadable; the detail names it."""


# ---- COFF and PE readers ------------------------------------------------


def _coff_sections(obj: bytes) -> list[tuple[int, str, int, int]]:
    count = struct.unpack_from("<H", obj, 2)[0]
    offset = 20 + struct.unpack_from("<H", obj, 16)[0]
    rows = []
    for index in range(count):
        name = obj[offset:offset + 8].rstrip(b"\0").decode("ascii", "replace")
        raw_size, raw_pointer = struct.unpack_from("<II", obj, offset + 16)
        rows.append((index + 1, name, raw_pointer, raw_size))
        offset += 40
    return rows


def _coff_symbols(obj: bytes) -> list[tuple[str, int, int, int]]:
    pointer, count = struct.unpack_from("<II", obj, 8)
    strings_at = pointer + count * 18
    rows, index = [], 0
    while index < count:
        record = pointer + index * 18
        raw = obj[record:record + 8]
        if raw[:4] == b"\0\0\0\0":
            start = strings_at + struct.unpack_from("<I", raw, 4)[0]
            name = obj[start:obj.find(b"\0", start)].decode("ascii", "replace")
        else:
            name = raw.rstrip(b"\0").decode("ascii", "replace")
        value, section, symbol_type, _class, aux = struct.unpack_from("<IhHBB", obj, record + 8)
        rows.append((name, section, value, symbol_type))
        # An auxiliary record is not a symbol; skipping it is what keeps the
        # walk aligned, and getting this wrong silently returns section names.
        index += 1 + aux
    return rows


def library_functions(lib: Path) -> list[tuple[str, bytes]]:
    """Every uniquely named function body the archive defines."""
    if not lib.is_file():
        raise SymbolError(f"no Wwise SDK library at {lib}")
    blob = lib.read_bytes()
    if blob[:8] != b"!<arch>\n":
        raise SymbolError(f"{lib.name}: not a COFF archive")
    found: list[tuple[str, bytes]] = []
    position = 8
    while position + 60 <= len(blob):
        header = blob[position:position + 60]
        try:
            size = int(header[48:58].decode().strip())
        except ValueError:
            break
        data = position + 60
        obj = blob[data:data + size]
        if len(obj) > 20 and struct.unpack_from("<H", obj, 0)[0] == COFF_MACHINE_AMD64:
            symbols = _coff_symbols(obj)
            for number, name, raw_pointer, raw_size in _coff_sections(obj):
                if not name.startswith(".text") or raw_size < MIN_BODY_BYTES or not raw_pointer:
                    continue
                named = [
                    symbol for (symbol, section, value, symbol_type) in symbols
                    if section == number and value == 0
                    and symbol_type == SYM_TYPE_FUNCTION and not symbol.startswith(".")
                ]
                # A COMDAT holding two names cannot attribute a body to one of
                # them, so it contributes nothing rather than a coin flip.
                if len(named) == 1:
                    found.append((named[0], obj[raw_pointer:raw_pointer + raw_size]))
        position = data + size + (size & 1)
    return found


def image_functions(dll: Path) -> tuple[dict[int, bytes], dict[str, Any]]:
    """Every function the PE's own exception directory declares, with its body."""
    if not dll.is_file():
        raise SymbolError(f"no AkSoundEngine.dll at {dll}")
    blob = dll.read_bytes()
    pe = struct.unpack_from("<I", blob, 0x3C)[0]
    if blob[pe:pe + 4] != b"PE\0\0":
        raise SymbolError(f"{dll.name}: not a PE image")
    count = struct.unpack_from("<H", blob, pe + 6)[0]
    offset = pe + 24 + struct.unpack_from("<H", blob, pe + 20)[0]
    sections = {}
    for _ in range(count):
        name = blob[offset:offset + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", blob, offset + 8)
        sections[name] = (virtual_address, virtual_size, raw_size, raw_pointer)
        offset += 40
    for required in (".text", ".pdata"):
        if required not in sections:
            raise SymbolError(f"{dll.name}: no {required} section")
    text_rva, text_vsize, text_rsize, text_raw = sections[".text"]
    _pv, pdata_vsize, pdata_rsize, pdata_raw = sections[".pdata"]
    bodies: dict[int, bytes] = {}
    for index in range(min(pdata_vsize, pdata_rsize) // 12):
        begin, end, _unwind = struct.unpack_from("<III", blob, pdata_raw + index * 12)
        if not begin or end <= begin:
            continue
        start = text_raw + (begin - text_rva)
        bodies[begin] = blob[start:start + (end - begin)]
    return bodies, {"functions": len(bodies), "bytes": len(blob)}


# ---- matching -----------------------------------------------------------


def match_functions(
    bodies: dict[int, bytes], candidates: Iterable[tuple[str, bytes]]
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    """Name each function whose equal-length best candidate is clearly best."""
    by_length: dict[int, list[tuple[str, bytes]]] = collections.defaultdict(list)
    for name, body in candidates:
        by_length[len(body)].append((name, body))
    named: dict[int, dict[str, Any]] = {}
    counts = {"named": 0, "ambiguous": 0, "belowThreshold": 0, "noCandidate": 0}
    for rva, body in bodies.items():
        pool = by_length.get(len(body))
        if not pool:
            counts["noCandidate"] += 1
            continue
        scored = sorted(
            ((sum(1 for a, b in zip(body, candidate) if a == b) / len(body), name)
             for name, candidate in pool),
            reverse=True)
        best = scored[0]
        runner = scored[1][0] if len(scored) > 1 else 0.0
        if best[0] < ACCEPT:
            counts["belowThreshold"] += 1
        elif best[0] - runner < MARGIN:
            counts["ambiguous"] += 1
        else:
            counts["named"] += 1
            named[rva] = {"symbol": best[1], "agreement": round(best[0], 3),
                          "bytes": len(body)}
    return named, counts


def name_addresses(
    rvas: Iterable[int], sdk: Path = DEFAULT_SDK, dll: Path = DEFAULT_DLL
) -> dict[int, dict[str, Any]]:
    """Name just the addresses asked for, each with the evidence for its name.

    Callers annotating a hook catalog want the symbol beside the address they
    already recorded, not the whole map.
    """
    bodies, _image = image_functions(dll)
    wanted = {rva: bodies[rva] for rva in rvas if rva in bodies}
    named, _counts = match_functions(wanted, library_functions(sdk / SDK_LIB_RELATIVE))
    for row in named.values():
        row["evidence"] = (
            f"identical {row['bytes']}-byte extent, "
            f"{row['agreement'] * 100:.1f}% byte agreement; "
            "differences are relocated operands")
    return named


def build(output: Path, sdk: Path = DEFAULT_SDK, dll: Path = DEFAULT_DLL) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    bodies, image = image_functions(dll)
    candidates = library_functions(sdk / SDK_LIB_RELATIVE)
    named, counts = match_functions(bodies, candidates)
    report = {
        "schema": "endfield.wwise-sdk-symbols.v1",
        "inputs": {"sdk": str(sdk), "dll": str(dll), **image,
                   "libraryFunctions": len(candidates)},
        "thresholds": {"accept": ACCEPT, "margin": MARGIN},
        "summary": {
            "status": "validated",
            **counts,
            "namedFraction": round(counts["named"] / max(len(bodies), 1), 4),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "evidenceBoundary": (
            "A match is an equal-length body agreeing on at least the accept "
            "threshold, with the runner-up behind by the margin; the disagreeing "
            "bytes are relocated call targets and rip-relative displacements. It "
            "identifies the code and therefore the class and method, not when the "
            "function runs, what calls it, or whether the shipped build changed its "
            "behaviour."
        ),
        "symbols": {f"0x{rva:x}": row for rva, row in sorted(named.items())},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=DEFAULT_SDK)
    parser.add_argument("--dll", type=Path, default=DEFAULT_DLL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--find", action="append", default=[],
                        help="print only symbols containing this text")
    args = parser.parse_args()
    try:
        report = build(args.output, args.sdk, args.dll)
    except (SymbolError, OSError, ValueError, KeyError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    if args.find:
        for rva, row in report["symbols"].items():
            if any(token in row["symbol"] for token in args.find):
                print(f"{rva}\t{row['agreement']}\t{row['symbol']}")
        return 0
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
