#!/usr/bin/env python3
"""Transcribe and audit Simulation Start's pinned scalar double trig helpers."""

from __future__ import annotations

import argparse
import ast
import base64
import ctypes
import hashlib
import inspect
import json
import random
import struct
import zlib
from pathlib import Path
from typing import Any, Callable

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_simulation_start_trig_helpers_golden_vectors.json"
)
SIN_RVA, SIN_BYTES = 0x23C490, 720
SIN_SHA256 = "4b74ab7e0a799b053d616b14cf3380c3124a112d3756786a6df6c17f3d0521e4"
COS_RVA, COS_BYTES = 0x23C1C0, 718
COS_SHA256 = "6dd6e6504c6daed91f592c93fb0c0a6716787a20d2214fd83d4ed6e845ca0b8f"
REDUCER_RVA, REDUCER_BYTES = 0x23C760, 1147
REDUCER_SHA256 = "f03b3aa47f3d19ed6aa8cf1f7f997d7e4deabf1da6b9184f641a9fc31d4943a6"
TABLE_RVA, TABLE_BYTES = 0x3BC040, 3876 * 8
TABLE_SHA256 = "f76922848d66989df9746d647c9a012a90ff827eb83ca3c30c7c6c647271c1dc"

# zlib-compressed exact 3,876-double reducer table. The decompressed bytes are
# source-owned and hash-checked; source_sin/source_cos never read the DLL.
_TABLE_ZLIB_B64 = """
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
"""
_TABLE_BYTES = zlib.decompress(base64.b64decode(_TABLE_ZLIB_B64))
_TABLE = struct.unpack("<3876d", _TABLE_BYTES)


def _from_bits(bits: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", bits & 0xFFFFFFFFFFFFFFFF))[0]


def _bits(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def _add(a: float, b: float) -> float:
    return float(float(a) + float(b))


def _sub(a: float, b: float) -> float:
    return float(float(a) - float(b))


def _mul(a: float, b: float) -> float:
    return float(float(a) * float(b))


def _abs(value: float) -> float:
    return _from_bits(_bits(value) & 0x7FFFFFFFFFFFFFFF)


def _xor_sign(value: float) -> float:
    return _from_bits(_bits(value) ^ 0x8000000000000000)


def _trunc_double(value: float) -> float:
    return float(int(value))


def _large_reduce(input_bits: int) -> tuple[int, float, float]:
    """Instruction-order transcription of shared reducer RVA 0x23c760."""
    exponent = (input_bits >> 52) & 0x7FF
    shift = (1 if exponent < 0x6BC else 0) << 58
    normalized_bits = (input_bits + 0xFC00000000000000 + shift) & 0xFFFFFFFFFFFFFFFF
    x0 = _from_bits(normalized_bits)
    index = 4 * exponent - 0x10D8 if exponent >= 0x436 else 0

    tab0 = _TABLE[index]
    xhi = _from_bits(normalized_bits & 0xFFFFFFFFF8000000)
    xlo = _sub(x0, xhi)
    tab0hi = _from_bits(_bits(tab0) & 0xFFFFFFFFF8000000)
    tab0lo = _sub(tab0, tab0hi)
    product0 = _mul(tab0, x0)
    error0 = _sub(_mul(xhi, tab0hi), product0)
    error0 = _add(_mul(xlo, tab0hi), error0)
    error0 = _add(_mul(tab0lo, xhi), error0)
    error0 = _add(_mul(xlo, tab0lo), error0)

    coarse0 = _mul(_trunc_double(_mul(product0, 2.0 ** -28)), 2.0 ** 28)
    rem0 = _sub(product0, coarse0)
    positive0 = 1 if product0 > 0.0 else 0
    q0 = (((positive0 + int(_mul(rem0, 8.0)) + 3) & 7) - 3) >> 1
    half0 = _from_bits((_bits(product0) & 0x8000000000000000) | 0x3FE0000000000000)
    rounded0 = _mul(_trunc_double(_add(_mul(4.0, rem0), half0)), 0.25)
    reduced0 = _sub(rem0, rounded0)
    if _abs(reduced0) > 0.25:
        reduced0 = _sub(reduced0, half0)
    if _abs(reduced0) > 10000000000.0:
        reduced0 = _from_bits(_bits(reduced0) & 0x8000000000000000)
    exact0 = _abs(product0) == 0.12499999999999999
    if exact0:
        reduced0 = product0

    saved_error0 = error0
    sum0 = _add(error0, reduced0)
    tab1 = _TABLE[index + 1]
    tab1hi = _from_bits(_bits(tab1) & 0xFFFFFFFFF8000000)
    tab1lo = _sub(tab1, tab1hi)
    product1 = _mul(tab1, x0)
    sum1 = _add(product1, sum0)
    positive1 = 1 if sum1 > 0.0 else 0
    half1 = _from_bits((_bits(sum1) & 0x8000000000000000) | 0x3FE0000000000000)
    coarse1 = _mul(_trunc_double(_mul(sum1, 2.0 ** -28)), 2.0 ** 28)
    rem1 = _sub(sum1, coarse1)
    rounded1 = _mul(_trunc_double(_add(_mul(4.0, rem1), half1)), 0.25)
    reduced1 = _sub(rem1, rounded1)
    if _abs(reduced1) > 0.25:
        reduced1 = _sub(reduced1, half1)
    q1 = (((positive1 + int(_mul(rem1, 8.0)) + 3) & 7) - 3) >> 1
    if _abs(reduced1) > 10000000000.0:
        reduced1 = _from_bits(_bits(reduced1) & 0x8000000000000000)
    exact1 = _abs(sum1) == 0.12499999999999999
    if exact1:
        reduced1 = sum1
    quadrant = (0 if exact0 else q0) + (0 if exact1 else q1)

    product1_error = _sub(_mul(tab1hi, xhi), product1)
    product1_error = _add(_mul(tab1hi, xlo), product1_error)
    product1_error = _add(_mul(tab1lo, xhi), product1_error)
    product1_error = _add(_mul(tab1lo, xlo), product1_error)
    sum1_minus_sum0 = _sub(sum1, sum0)
    reduced0_tail = _sub(reduced0, sum0)
    recovered_sum0 = _sub(sum1, sum1_minus_sum0)
    reduced0_tail = _add(reduced0_tail, saved_error0)
    reduced0_tail = _add(product1_error, reduced0_tail)
    sum0_tail = _sub(sum0, recovered_sum0)
    product1_tail = _sub(product1, sum1_minus_sum0)
    sum0_tail = _add(product1_tail, sum0_tail)
    reduced0_tail = _add(reduced0_tail, sum0_tail)
    combined = _add(reduced0_tail, reduced1)
    combined_error = _add(_sub(reduced1, combined), reduced0_tail)

    tab2 = _TABLE[index + 2]
    tab2hi = _from_bits(_bits(tab2) & 0xFFFFFFFFF8000000)
    tab2lo = _sub(tab2, tab2hi)
    product2 = _mul(tab2, x0)
    product2_error = _sub(_mul(xhi, tab2hi), product2)
    product2_error = _add(_mul(tab2lo, xhi), product2_error)
    product2_error = _add(_mul(xlo, tab2hi), product2_error)
    product2_error = _add(_mul(xlo, tab2lo), product2_error)
    tail = _add(_add(_mul(x0, _TABLE[index | 3]), product2_error), combined_error)
    leading = _add(product2, combined)
    recovered_combined = _sub(leading, combined)
    leading_error = _add(_sub(product2, recovered_combined),
                         _sub(combined, _sub(leading, recovered_combined)))
    tail = _add(tail, leading_error)
    reduced_hi = _add(tail, leading)
    reduced_lo = _add(tail, _sub(leading, reduced_hi))

    if _abs(x0) < 0.7:
        return quadrant, x0, 0.0
    split_hi = _from_bits(_bits(reduced_hi) & 0xFFFFFFFFF8000000)
    split_lo = _sub(reduced_hi, split_hi)
    tau = _from_bits(0x401921FB54442D18)
    tau_hi = _from_bits(0x401921FB50000000)
    tau_mid = _from_bits(0x3E7110B460000000)
    tau_lo = _from_bits(0x3CB1A62633145C07)
    radians_hi = _mul(reduced_hi, tau)
    radians_error = _sub(_mul(split_hi, tau_hi), radians_hi)
    radians_error = _add(_mul(split_lo, tau_hi), radians_error)
    radians_error = _add(_mul(split_hi, tau_mid), radians_error)
    radians_error = _add(_mul(split_lo, tau_mid), radians_error)
    radians_error = _add(_mul(reduced_hi, tau_lo), radians_error)
    radians_lo = _add(_mul(reduced_lo, tau), radians_error)
    return quadrant, radians_hi, radians_lo


_POLY = tuple(_from_bits(v) for v in (
    0xBC62622B22D526BE, 0x3CE94FA618796592, 0xBD6AE7EA531357BF,
    0x3DE6124601C23966, 0xBE5AE64567CB5786, 0x3EC71DE3A5568A50,
    0xBF2A01A01A019FC7, 0x3F8111111111110F, 0xBFC5555555555555,
))


def _sin_poly(reduced: float, input_bits: int) -> float:
    if input_bits == 0x8000000000000000:
        return _from_bits(0x8000000000000000)
    z = _mul(reduced, reduced)
    z2 = _mul(z, z)
    z4 = _mul(z2, z2)
    p0 = _add(_mul(z, _POLY[0]), _POLY[1])
    p1 = _add(_mul(z, _POLY[2]), _POLY[3])
    p = _add(p1, _mul(z2, p0))
    high = _mul(z4, p)
    p2 = _add(_mul(z, _POLY[4]), _POLY[5])
    p3 = _add(_mul(z, _POLY[6]), _POLY[7])
    low = _add(p3, _mul(z2, p2))
    poly = _add(_add(low, high), 0.0)
    poly = _add(_mul(z, poly), _POLY[8])
    return _add(reduced, _mul(z, _mul(reduced, poly)))


def _source_sin_detail(input_bits: int) -> tuple[int, str]:
    x = _from_bits(input_bits)
    absolute = _abs(x)
    if absolute < 15.0:
        scaled = _mul(x, _from_bits(0x3FD45F306DC9C883))
        n = int(_add(scaled, -0.5 if scaled < 0.0 else 0.5))
        nd = float(n)
        reduced = _add(_add(x, _mul(nd, _from_bits(0xC00921FB54442D18))),
                       _mul(nd, _from_bits(0xBCA1A62633145C07)))
        if n & 1:
            reduced = _xor_sign(reduced)
        path = "small_split_pi"
    elif absolute < 100000000000000.0:
        high_n = _trunc_double(_mul(x, _from_bits(0x3E545F306DC9C883)))
        high_scaled = _mul(high_n, 16777216.0)
        scaled = _sub(_mul(x, _from_bits(0x3FD45F306DC9C883)), high_scaled)
        low_n = int(_add(scaled, -0.5 if scaled < 0.0 else 0.5))
        low_d = float(low_n)
        reduced = _sub(x, _mul(high_scaled, _from_bits(0x400921FB50000000)))
        reduced = _sub(reduced, _mul(low_d, _from_bits(0x400921FB50000000)))
        reduced = _sub(reduced, _mul(high_scaled, _from_bits(0x3E6110B460000000)))
        reduced = _sub(reduced, _mul(low_d, _from_bits(0x3E6110B460000000)))
        reduced = _sub(reduced, _mul(high_scaled, _from_bits(0x3CA1A62630000000)))
        reduced = _sub(reduced, _mul(low_d, _from_bits(0x3CA1A62630000000)))
        reduced = _add(reduced, _mul(_add(high_scaled, low_d), _from_bits(0xBAF8A2E03707344A)))
        if low_n & 1:
            reduced = _xor_sign(reduced)
        path = "medium_split_pi"
    elif (input_bits & 0x7FF0000000000000) != 0x7FF0000000000000:
        n, hi, lo = _large_reduce(input_bits)
        reduced = hi
        positive = 1 if hi > 0.0 else 0
        if n & 1:
            sign = _bits(hi) & 0x8000000000000000
            pio2 = _from_bits(0xBFF921FB54442D18 ^ sign)
            pio2lo = _from_bits(0xBC91A62633145C07 ^ sign)
            summed = _add(hi, pio2)
            correction = _add(_add(_sub(hi, _sub(summed, pio2)), _sub(pio2, _sub(summed, hi))),
                              _add(pio2lo, lo))
            hi, lo = summed, correction
            reduced = hi
        selector = positive + 2 * (n & 3) + 1
        reduced = _add(reduced, lo)
        if (selector >> 2) & 1:
            reduced = _xor_sign(reduced)
        path = "large_shared_table_reducer"
    else:
        return 0x7FF8000000000000, "nonfinite_canonical_nan"
    return _bits(_sin_poly(reduced, input_bits)), path


def _source_cos_detail(input_bits: int) -> tuple[int, str]:
    x = _from_bits(input_bits)
    absolute = _abs(x)
    if absolute < 15.0:
        scaled = _add(_mul(x, _from_bits(0x3FD45F306DC9C883)), -0.5)
        n = int(_add(scaled, -0.5 if scaled < 0.0 else 0.5))
        selector = 2 * n + 1
        nd = float(selector)
        reduced = _add(_add(x, _mul(nd, _from_bits(0xBFF921FB54442D18))),
                       _mul(nd, _from_bits(0xBC91A62633145C07)))
        if not (selector & 2):
            reduced = _xor_sign(reduced)
        path = "small_split_pi_over_2"
    elif absolute < 100000000000000.0:
        high_n = _trunc_double(_add(_mul(x, _from_bits(0x3E645F306DC9C883)),
                                    _from_bits(0xBE545F306DC9C883)))
        scaled = _add(_mul(x, _from_bits(0x3FD45F306DC9C883)), -0.5)
        scaled = _add(scaled, _mul(high_n, -8388608.0))
        low_n = int(_add(scaled, -0.5 if scaled < 0.0 else 0.5))
        selector = 2 * low_n + 1
        high_scaled = _mul(high_n, 16777216.0)
        low_d = float(selector)
        reduced = _sub(x, _mul(high_scaled, _from_bits(0x3FF921FB50000000)))
        reduced = _sub(reduced, _mul(low_d, _from_bits(0x3FF921FB50000000)))
        reduced = _sub(reduced, _mul(high_scaled, _from_bits(0x3E5110B460000000)))
        reduced = _sub(reduced, _mul(low_d, _from_bits(0x3E5110B460000000)))
        reduced = _sub(reduced, _mul(high_scaled, _from_bits(0x3C91A62630000000)))
        reduced = _sub(reduced, _mul(low_d, _from_bits(0x3C91A62630000000)))
        reduced = _add(reduced, _mul(_add(high_scaled, low_d), _from_bits(0xBAE8A2E03707344A)))
        if not (selector & 2):
            reduced = _xor_sign(reduced)
        path = "medium_split_pi_over_2"
    elif (input_bits & 0x7FF0000000000000) != 0x7FF0000000000000:
        n, hi, lo = _large_reduce(input_bits)
        reduced = hi
        positive = 1 if hi > 0.0 else 0
        if not (n & 1):
            sign = 0x8000000000000000 if hi <= 0.0 else 0
            pio2 = _from_bits(0xBFF921FB54442D18 ^ sign)
            pio2lo = _from_bits(0xBC91A62633145C07 ^ sign)
            summed = _add(hi, pio2)
            correction = _add(_add(_sub(hi, _sub(summed, pio2)), _sub(pio2, _sub(summed, hi))),
                              _add(pio2lo, lo))
            hi, lo = summed, correction
            reduced = hi
        selector = positive + 2 * (n & 3) + 7
        reduced = _add(reduced, lo)
        if ((selector >> 1) & 2) == 0:
            reduced = _xor_sign(reduced)
        path = "large_shared_table_reducer"
    else:
        return 0x7FF8000000000000, "nonfinite_canonical_nan"
    return _bits(_sin_poly(reduced, 0)), path


def source_sin(input_bits: int) -> int:
    """Return exact sine bits without native execution or native data reads."""
    return _source_sin_detail(input_bits)[0]


def source_cos(input_bits: int) -> int:
    """Return exact cosine bits without native execution or native data reads."""
    return _source_cos_detail(input_bits)[0]


CASES = (
    ("positive_zero", 0x0000000000000000), ("negative_zero", 0x8000000000000000),
    ("smallest_subnormal", 0x0000000000000001), ("negative_smallest_subnormal", 0x8000000000000001),
    ("one", 0x3FF0000000000000), ("minus_one", 0xBFF0000000000000),
    ("small_below_15", 0x402DFFFFFFFFFFFF), ("small_at_15", 0x402E000000000000),
    ("small_above_15", 0x402E000000000001), ("negative_15", 0xC02E000000000000),
    ("medium_below_1e14", 0x42D6BCC41E8FFFFF), ("large_at_1e14", 0x42D6BCC41E900000),
    ("large_above_1e14", 0x42D6BCC41E900001), ("negative_1e14", 0xC2D6BCC41E900000),
    ("large_power", 0x5FF0000000000000), ("very_large", 0x7E37E43C8800759C),
    ("maximum_finite", 0x7FEFFFFFFFFFFFFF), ("negative_maximum_finite", 0xFFEFFFFFFFFFFFFF),
    ("positive_infinity", 0x7FF0000000000000), ("negative_infinity", 0xFFF0000000000000),
    ("quiet_nan_payload", 0x7FF8123456789ABC), ("negative_quiet_nan", 0xFFF8ABCDEF012345),
    ("signaling_nan_payload", 0x7FF0123456789ABC),
)


def _native_functions(module: Any) -> tuple[Callable[[int], int], Callable[[int], int]]:
    sin_fn = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)(module._handle + SIN_RVA)
    cos_fn = ctypes.CFUNCTYPE(ctypes.c_double, ctypes.c_double)(module._handle + COS_RVA)

    def invoke(function: Any, bits: int) -> int:
        return _bits(function(_from_bits(bits)))

    return lambda bits: invoke(sin_fn, bits), lambda bits: invoke(cos_fn, bits)


def _assert_source_call_graph() -> dict[str, Any]:
    names = {"source_sin", "source_cos", "_source_sin_detail", "_source_cos_detail", "_large_reduce",
             "_sin_poly", "_from_bits", "_bits", "_add", "_sub", "_mul", "_abs", "_xor_sign",
             "_trunc_double"}
    forbidden = {"ctypes", "WinDLL", "CDLL", "CFUNCTYPE", "_native_gate", "_pe_exports",
                 "_exact_rva_span", "_native_functions", "module", "dll"}
    hits: list[str] = []
    for name in names:
        tree = ast.parse(inspect.getsource(globals()[name]))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                hits.append(f"{name}:{node.id}")
            if isinstance(node, ast.Attribute) and node.attr in forbidden:
                hits.append(f"{name}:{node.attr}")
    if hits:
        raise burst.ContractError(f"source call graph reaches native machinery: {hits}")
    return {"functionsChecked": sorted(names), "forbiddenReferences": sorted(forbidden), "violations": hits}


def _audit(native_sin: Callable[[int], int], native_cos: Callable[[int], int]) -> dict[str, int]:
    exponent_count = 0
    for exponent in range(2047):
        for sign in (0, 0x8000000000000000):
            for mantissa in (0, 1, 0x123456789AB, 0x7FFFFFFFFFFFF, 0xFFFFFFFFFFFFF):
                bits = sign | (exponent << 52) | mantissa
                if (native_sin(bits), native_cos(bits)) != (source_sin(bits), source_cos(bits)):
                    raise burst.ContractError(f"stratified audit differs at 0x{bits:016x}")
                exponent_count += 1
    rng = random.Random(0x23C49023C1C0)
    deterministic_count = 0
    while deterministic_count < 25000:
        bits = rng.getrandbits(64)
        if ((bits >> 52) & 0x7FF) == 0x7FF:
            continue
        if (native_sin(bits), native_cos(bits)) != (source_sin(bits), source_cos(bits)):
            raise burst.ContractError(f"deterministic audit differs at 0x{bits:016x}")
        deterministic_count += 1
    return {"stratifiedFiniteInputs": exponent_count, "deterministicFiniteInputs": deterministic_count}


def build_contract(run_broad_audit: bool = True) -> dict[str, Any]:
    if len(_TABLE_BYTES) != TABLE_BYTES or hashlib.sha256(_TABLE_BYTES).hexdigest() != TABLE_SHA256:
        raise burst.ContractError("embedded reducer table identity differs")
    source_proof = _assert_source_call_graph()
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    burst._exact_rva_span(pe, SIN_RVA, SIN_BYTES, SIN_SHA256)
    burst._exact_rva_span(pe, COS_RVA, COS_BYTES, COS_SHA256)
    burst._exact_rva_span(pe, REDUCER_RVA, REDUCER_BYTES, REDUCER_SHA256)
    table_offset = burst._rva_file_offset(pe, TABLE_RVA, TABLE_BYTES)
    native_table = pe["data"][table_offset:table_offset + TABLE_BYTES]
    if native_table != _TABLE_BYTES:
        raise burst.ContractError("embedded reducer table differs from pinned native table")
    module = ctypes.WinDLL(str(dll))
    native_sin, native_cos = _native_functions(module)
    vectors = []
    for name, bits in CASES:
        source = (source_sin(bits), source_cos(bits))
        native = (native_sin(bits), native_cos(bits))
        if source != native:
            raise burst.ContractError(f"controlled vector differs for {name}: native={native}, source={source}")
        vectors.append({"name": name, "inputBitsLe": struct.pack("<Q", bits).hex(),
                        "path": _source_sin_detail(bits)[1],
                        "sinBitsLe": struct.pack("<Q", native[0]).hex(),
                        "cosBitsLe": struct.pack("<Q", native[1]).hex()})
    audit = _audit(native_sin, native_cos) if run_broad_audit else {
        "stratifiedFiniteInputs": 0, "deterministicFiniteInputs": 0}
    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-start-trig-helpers-golden-vectors.v1",
        "status": "native_helpers_and_standalone_source_transcriptions_bit_exact",
        "nativeGate": gate,
        "helpers": {
            "springSine": {"rva": f"0x{SIN_RVA:x}", "bytes": SIN_BYTES, "sha256": SIN_SHA256,
                           "abi": "double -> double"},
            "coneCosine": {"rva": f"0x{COS_RVA:x}", "bytes": COS_BYTES, "sha256": COS_SHA256,
                           "abi": "double -> double"}},
        "sharedReducer": {"rva": f"0x{REDUCER_RVA:x}", "bytes": REDUCER_BYTES,
                          "sha256": REDUCER_SHA256},
        "reducerTable": {"rva": f"0x{TABLE_RVA:x}", "bytes": TABLE_BYTES,
                         "doubleWords": len(_TABLE), "sha256": TABLE_SHA256,
                         "sourceOwnedCompressedEmbedding": True},
        "sourceIndependenceProof": source_proof | {
            "sourceCallsNativeCode": False, "sourceReadsNativeDllTable": False,
            "nativeExecutionConfinedToAuditHarness": True},
        "coverage": audit | {"controlledBoundaryVectors": len(vectors),
                             "finiteExponentFieldsCovered": 2047 if run_broad_audit else 0,
                             "mantissasPerSignAndExponent": 5},
        "vectors": vectors,
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_contract(), indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("Simulation Start trig helper golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
