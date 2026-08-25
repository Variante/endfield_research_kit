#!/usr/bin/env python3
"""Transcribe and execute the pinned Burst scalar float sincos helper."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_float_sincos_golden_vectors.json"
)
SINCOS_RVA = 0x1E5D30
SINCOS_BYTES = 521
SINCOS_SHA256 = "3021151e64547f2cc7e4266b846da35bbb8eef05f00d864a357f9757e730f0a6"
REDUCER_RVA = 0x1DE840
REDUCER_BYTES = 1134
REDUCER_SHA256 = "4e59a40ed0e7702288ddad778c7048e66844dd9f29e024b920961257c082537a"
TABLE_RVA = 0x3C3980
TABLE_BYTES = 416 * 4
TABLE_SHA256 = "32c2b51dce4fabf449ef59072cfc786c4112f20722d69c7136bb005dd3d8a4ef"

# Exact 416-word reducer table at RVA 0x3c3980. Keeping the source-owned bytes
# here makes source_sincos independent of native helper execution and DLL data.
_TABLE_HEX = (
    "83f9223e889cdc31e14fa9243ffaea170ee60b3ddf8d8db03e602da43ffaea170"
    "ee60b3ddf8d8db03e602da43ffaea17dc603e3bf5ddd8aed90356a2eaa3af15d"
    "c603e3bf5ddd8aed90356a2eaa3af15dc603e3bf5ddd8aed90356a2eaa3af15d"
    "c603e3bf5ddd8aed90356a2eaa3af156e83793a2a889c2d9df02721aa8fbe14"
    "6e83793a2a889c2d9df02721aa8fbe14dd06f339abef46adc51eb0a0ade00294"
    "b90d66395341642c157bc09f2d2b3891721bcc385341642c157bc09f2d2b3891"
    "e53618386bf5ddaa0c2a769b6f9afa0e27b7c136542a88290c2a769b6f9afa0e"
    "27b7c136542a88290c2a769b6f9afa0e27b7c136542a88290c2a769b6f9afa0e"
    "4e6e0336542a88290c2a769b6f9afa0e91935b33e14fa9243ffaea1790c8328b"
    "91935b33e14fa9243ffaea1790c8328b91935b33e14fa9243ffaea1790c8328b"
    "91935b33e14fa9243ffaea1790c8328b91935b33e14fa9243ffaea1790c8328b"
    "91935b33e14fa9243ffaea1790c8328b2227b732e14fa9243ffaea1790c8328b"
    "889cdc31e14fa9243ffaea1790c8328b889cdc31e14fa9243ffaea1790c8328b"
    "10393931e14fa9243ffaea1790c8328b41e46430853fa5230b2e289603775309"
    "41e46430853fa5230b2e28960377530983c8c92ff68035a30b2e289603775309"
    "0591132f14fe94220b2e2896037753092a889c2d9df02721aa8fbe14f2233288"
    "2a889c2d9df02721aa8fbe14f22332882a889c2d9df02721aa8fbe14f2233288"
    "5341642c157bc09f2d2b3891db06ee045341642c157bc09f2d2b3891db06ee04"
    "5341642c157bc09f2d2b3891db06ee04a582c82bac13fe1e2d2b3891db06ee04"
    "4a05112bac13fe1e2d2b3891db06ee04542a88290c2a769b6f9afa0e76927c81"
    "542a88290c2a769b6f9afa0e76927c81542a88290c2a769b6f9afa0e76927c81"
    "40a582270c2a769b6f9afa0e76927c8140a582270c2a769b6f9afa0e76927c81"
    "40a582270c2a769b6f9afa0e76927c8140a582270c2a769b6f9afa0e76927c81"
    "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600"
    "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600"
    "e14fa9243ffaea1790c8328b15db0600e14fa9243ffaea1790c8328b15db0600"
    "853fa5230b2e28960377530915db0000853fa5230b2e28960377530915db0000"
    "14fe94220b2e28960377530915db000014fe94220b2e28960377530915db0000"
    "9df02721aa8fbe14f2233288eb2400809df02721aa8fbe14f2233288eb240080"
    "9df02721aa8fbe14f2233288eb24008075c21f20a73efa13c98f4887eb040080"
    "75c21f20a73efa13c98f4887eb040080ac13fe1e2d2b3891db06ee0415000000"
    "ac13fe1e2d2b3891db06ee0415000000ac13fe1e2d2b3891db06ee0415000000"
    "58277c1e2d2b3891db06ee0415000000b04ef81d2d2b3891db06ee0415000000"
    "5f9d703da7a98f3027c90fa36233b596bf3ae13cb2ac60b027c90fa36233b596"
    "7d75423c6f9afa2e76927ca1e2c9ac14faea843b6f9afa2e76927ca1e2c9ac14"
    "485f1d3924b22cac96625b1e7987cd91485f1d3924b22cac96625b1e7987cd91"
    "485f1d3924b22cac96625b1e7987cd91485f1d3924b22cac96625b1e7987cd91"
    "485f1d3924b22cac96625b1e7987cd913ffaea3790c832ab96625b1e7987cd91"
    "3ffaea3790c832ab96625b1e7987cd913ffaea3790c832ab96625b1e7987cd91"
    "7df45537e06e9a2a96625b1e7987cd91fbe8ab363f224baaaa75129d1de2c910"
    "eaa3af3503775329ad14db1c8e77d88feaa3af3503775329ad14db1c8e77d88f"
    "aa8fbe34f22332a84dad939bc8219e0eaa8fbe34f22332a84dad939bc8219e0e"
    "a73efa33c98f48a7676a1d9a410e710da73efa33c98f48a7676a1d9a410e710d"
    "4d7d7433dbc05d26322bc519410e710d9afae832dbc05d26322bc519410e710d"
    "35f5513292fc08a53653eb98f01b6f8b6aeaa33192fc08a53653eb98f01b6f8b"
    "a7a98f3027c90fa36233b59684208709a7a98f3027c90fa36233b59684208709"
    "6f9afa2e76927ca1e2c9ac14801064076f9afa2e76927ca1e2c9ac1480106407"
    "6f9afa2e76927ca1e2c9ac14801064076f9afa2e76927ca1e2c9ac1480106407"
    "de34752e76927ca1e2c9ac1480106407bc69ea2d76927ca1e2c9ac1480106407"
    "77d3542d96625b1e7987cd91f30f8204eea6a92c96625b1e7987cd91f30f8204"
    "b89ba62b96625b1e7987cd91f30f8204b89ba62b96625b1e7987cd91f30f8204"
    "e06e9a2a96625b1e7987cd91f30f82040700000008000000090000000a000000"
)
_TABLE_BYTES = bytes.fromhex(_TABLE_HEX)
_TABLE = struct.unpack("<416f", _TABLE_BYTES)


def _from_bits(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def _bits(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _f(value: float) -> float:
    return _from_bits(_bits(value))


def _add(a: float, b: float) -> float:
    return _f(_f(a) + _f(b))


def _sub(a: float, b: float) -> float:
    return _f(_f(a) - _f(b))


def _mul(a: float, b: float) -> float:
    return _f(_f(a) * _f(b))


def _trunc_float(value: float) -> float:
    return _f(float(int(_f(value))))


def _abs(value: float) -> float:
    return _from_bits(_bits(value) & 0x7FFFFFFF)


def _xor_sign(value: float) -> float:
    return _from_bits(_bits(value) ^ 0x80000000)


def _large_reduce(input_bits: int) -> tuple[int, float, float]:
    """Instruction-order transcription of RVA 0x1de840 for finite float input."""
    exponent = (input_bits >> 23) & 0xFF
    shift = (1 if exponent < 0xDA else 0) << 29
    normalized_bits = (shift + input_bits - 0x20000000) & 0xFFFFFFFF
    x0 = _from_bits(normalized_bits)
    table_index = 4 * exponent - 0x260 if exponent >= 0x98 else 0

    tab0 = _TABLE[table_index]
    xhi = _from_bits(normalized_bits & 0xFFFFF000)
    xlo = _sub(x0, xhi)
    t0hi = _from_bits(_bits(tab0) & 0xFFFFF000)
    t0lo = _sub(tab0, t0hi)
    product0 = _mul(tab0, x0)
    error0 = _sub(_mul(xhi, t0hi), product0)
    error0 = _add(_mul(xlo, t0hi), error0)
    error0 = _add(_mul(t0lo, xhi), error0)
    error0 = _add(_mul(xlo, t0lo), error0)

    coarse = _mul(_trunc_float(_mul(0.0009765625, product0)), 1024.0)
    remainder0 = _sub(product0, coarse)
    positive0 = 1 if product0 > 0.0 else 0
    q0 = (((positive0 + int(_mul(remainder0, 8.0)) + 3) & 7) - 3) >> 1
    half0 = _from_bits((_bits(product0) & 0x80000000) | 0x3F000000)
    rounded0 = _trunc_float(_add(_mul(4.0, remainder0), half0))
    rounded0 = _mul(rounded0, 0.25)
    reduced0 = _sub(remainder0, rounded0)
    if _abs(reduced0) > 0.125:
        reduced0 = _sub(reduced0, half0)
    if _abs(reduced0) > 10000000000.0:
        reduced0 = _from_bits(_bits(reduced0) & 0x80000000)
    exact0 = _abs(product0) == _from_bits(0x3DFFFFFF)
    if exact0:
        reduced0 = product0

    saved_error0 = error0
    sum0 = _add(error0, reduced0)
    tab1 = _TABLE[table_index + 1]
    product1 = _mul(tab1, x0)
    sum1 = _add(product1, sum0)
    coarse1 = _mul(_trunc_float(_mul(0.0009765625, sum1)), 1024.0)
    remainder1 = _sub(sum1, coarse1)
    carried_q0 = 0 if exact0 else q0
    tab1hi = _from_bits(_bits(tab1) & 0xFFFFF000)
    positive1 = 1 if sum1 > 0.0 else 0
    half1 = _from_bits((_bits(sum1) & 0x80000000) | 0x3F000000)
    rounded1 = _mul(_trunc_float(_add(_mul(4.0, remainder1), half1)), 0.25)
    reduced1 = _sub(remainder1, rounded1)
    if _abs(reduced1) > 0.125:
        reduced1 = _sub(reduced1, half1)
    q1 = (((positive1 + int(_mul(remainder1, 8.0)) + 3) & 7) - 3) >> 1
    exact1 = _abs(sum1) == _from_bits(0x3DFFFFFF)
    if _abs(reduced1) > 10000000000.0:
        reduced1 = _from_bits(_bits(reduced1) & 0x80000000)
    if exact1:
        reduced1 = sum1
    quadrant = carried_q0 + (0 if exact1 else q1)

    if _abs(_from_bits(normalized_bits & 0x7FFFFFFF)) < _from_bits(0x3F333333):
        return quadrant, x0, 0.0

    tab1hi_value = tab1hi
    product_hi = _mul(xhi, tab1hi_value)
    tab1lo = _sub(tab1, tab1hi_value)
    product_error = _sub(product_hi, product1)
    product_error = _add(_mul(xlo, tab1hi_value), product_error)
    product_error = _add(_mul(tab1lo, xhi), product_error)
    sum1_tail = _sub(sum1, sum0)
    reduced0_tail = _sub(reduced0, sum0)
    product_error = _add(_mul(tab1lo, xlo), product_error)
    recovered_product1 = _sub(sum1, sum1_tail)
    reduced0_tail = _add(reduced0_tail, saved_error0)
    reduced0_tail = _add(product_error, reduced0_tail)
    sum0_tail = _sub(sum0, recovered_product1)
    product1_tail = _sub(product1, sum1_tail)
    sum0_tail = _add(product1_tail, sum0_tail)
    reduced0_tail = _add(reduced0_tail, sum0_tail)
    combined = _add(reduced0_tail, reduced1)
    combine_error = _sub(reduced1, combined)
    combine_error = _add(reduced0_tail, combine_error)

    tab2 = _TABLE[table_index + 2]
    tab2hi = _from_bits(_bits(tab2) & 0xFFFFF000)
    tab2lo = _sub(tab2, tab2hi)
    product2 = _mul(tab2, x0)
    product2_error = _sub(_mul(xhi, tab2hi), product2)
    product2_error = _add(_mul(tab2lo, xhi), product2_error)
    product2_error = _add(_mul(xlo, tab2hi), product2_error)
    product2_error = _add(_mul(xlo, tab2lo), product2_error)
    product3 = _mul(x0, _TABLE[table_index | 3])
    tail = _add(_add(product3, product2_error), combine_error)
    leading = _add(product2, combined)
    recovered_combined = _sub(leading, combined)
    leading_error = _sub(product2, recovered_combined)
    leading_error = _add(leading_error, _sub(combined, _sub(leading, recovered_combined)))
    tail = _add(tail, leading_error)
    reduced_hi = _add(leading, tail)
    reduced_lo = _add(tail, _sub(leading, reduced_hi))

    split_hi = _from_bits(_bits(reduced_hi) & 0xFFFFF000)
    split_lo = _sub(reduced_hi, split_hi)
    radians_hi = _mul(reduced_hi, _from_bits(0x40C90FDB))
    radians_error = _sub(_mul(split_hi, _from_bits(0x40C90000)), radians_hi)
    radians_error = _add(_mul(split_lo, _from_bits(0x40C90000)), radians_error)
    radians_error = _add(_mul(split_hi, _from_bits(0x3AFDB000)), radians_error)
    radians_error = _add(_mul(split_lo, _from_bits(0x3AFDB000)), radians_error)
    radians_error = _add(_mul(reduced_hi, _from_bits(0xB43BBD2E)), radians_error)
    radians_lo = _add(_mul(reduced_lo, _from_bits(0x40C90FDB)), radians_error)
    return quadrant, radians_hi, radians_lo


def source_sincos(input_bits: int) -> tuple[int, int, str]:
    """Return exact sine/cosine float bits without invoking native code."""
    x = _from_bits(input_bits)
    absolute = _abs(x)
    if absolute < 125.0:
        scaled = _mul(x, _from_bits(0x3F22F983))
        n = int(_add(scaled, -0.5 if scaled < 0.0 else 0.5))
        nf = _f(float(n))
        reduced = _add(_add(_add(x, _mul(nf, _from_bits(0xBFC90E00))),
                            _mul(nf, _from_bits(0xB86D5000))),
                       _mul(nf, _from_bits(0xB0885A31)))
        path = "small_split_pi_over_2"
    elif absolute < 39000.0:
        scaled = _mul(x, _from_bits(0x3F22F983))
        n = int(_add(scaled, -0.5 if scaled < 0.0 else 0.5))
        nf = _f(float(n))
        reduced = _add(_add(_add(_add(x, _mul(nf, _from_bits(0xBFC90000))),
                                 _mul(nf, _from_bits(0xB9FD8000))),
                            _mul(nf, _from_bits(0xB4A88000))),
                       _mul(nf, _from_bits(0xAE85A309)))
        path = "medium_split_pi_over_2"
    elif (input_bits & 0x7F800000) != 0x7F800000:
        n, hi, lo = _large_reduce(input_bits)
        reduced = _add(hi, lo)
        path = "large_table_reducer"
    else:
        n = 0
        reduced = _from_bits(0x7FC00000)
        path = "nonfinite_canonical_nan"

    z = _mul(reduced, reduced)
    sine = _from_bits(0x80000000)
    if input_bits != 0x80000000:
        sine_poly = _add(_mul(z, _from_bits(0xB94CA65B)), _from_bits(0x3C08839A))
        sine_poly = _add(_mul(z, sine_poly), _from_bits(0xBE2AAAA2))
        sine = _add(reduced, _mul(reduced, _mul(z, sine_poly)))
    cosine_poly = _add(_mul(z, _from_bits(0xB491ED89)), _from_bits(0x37D0078B))
    cosine_poly = _add(_mul(z, cosine_poly), _from_bits(0xBAB60B58))
    cosine_poly = _add(_mul(z, cosine_poly), _from_bits(0x3D2AAAAA))
    cosine_poly = _add(_mul(z, cosine_poly), -0.5)
    cosine = _add(_mul(z, cosine_poly), 1.0)

    if n & 1:
        out_cos = sine
        out_sin = _xor_sign(cosine) if n & 2 else cosine
    else:
        out_cos = cosine
        out_sin = _xor_sign(sine) if n & 2 else sine
    if (n + 1) & 2:
        out_cos = _xor_sign(out_cos)
    return _bits(out_sin), _bits(out_cos), path


CASES = (
    ("positive_zero", 0x00000000), ("negative_zero", 0x80000000),
    ("smallest_subnormal", 0x00000001), ("negative_smallest_subnormal", 0x80000001),
    ("one", 0x3F800000), ("minus_one", 0xBF800000),
    ("pi_over_four", 0x3F490FDB), ("small_below_125", 0x42F9FFFF),
    ("small_at_125", 0x42FA0000), ("small_above_125", 0x42FA0001),
    ("negative_125", 0xC2FA0000), ("medium_below_39000", 0x471857FF),
    ("large_at_39000", 0x47185800), ("large_above_39000", 0x47185801),
    ("negative_39000", 0xC7185800), ("large_power", 0x4F000000),
    ("very_large", 0x7149F2CA), ("maximum_finite", 0x7F7FFFFF),
    ("negative_maximum_finite", 0xFF7FFFFF), ("positive_infinity", 0x7F800000),
    ("negative_infinity", 0xFF800000), ("quiet_nan_payload", 0x7FC12345),
    ("negative_quiet_nan", 0xFFC54321), ("signaling_nan_payload", 0x7FA12345),
)


def _make_native(module: Any) -> tuple[Any, int]:
    # void thunk(void* target, uint32* in, uint32* out): exact bit load/store.
    code = bytes.fromhex(
        "4883ec38" "4c89442420" "f30f1002" "ffd1" "4c8b442420"
        "410f1300" "4883c438" "c3"
    )
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    address = kernel32.VirtualAlloc(None, len(code), 0x3000, 0x40)
    if not address:
        raise burst.ContractError(f"VirtualAlloc for sincos ABI thunk failed: {ctypes.get_last_error()}")
    ctypes.memmove(address, code, len(code))
    thunk = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(address)

    def invoke(value_bits: int) -> tuple[int, int]:
        source = ctypes.c_uint32(value_bits)
        result = (ctypes.c_uint32 * 2)()
        thunk(module._handle + SINCOS_RVA, ctypes.byref(source), result)
        return int(result[0]), int(result[1])

    return invoke, int(address)


def build_contract() -> dict[str, Any]:
    if len(_TABLE_BYTES) != TABLE_BYTES or hashlib.sha256(_TABLE_BYTES).hexdigest() != TABLE_SHA256:
        raise burst.ContractError("embedded reducer table identity differs")
    gate = burst._native_gate(None, None)
    dll = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll)
    burst._exact_rva_span(pe, SINCOS_RVA, SINCOS_BYTES, SINCOS_SHA256)
    burst._exact_rva_span(pe, REDUCER_RVA, REDUCER_BYTES, REDUCER_SHA256)
    module = ctypes.WinDLL(str(dll))
    native, _thunk_address = _make_native(module)
    vectors = []
    for name, input_bits in CASES:
        native_bits = native(input_bits)
        source_bits = source_sincos(input_bits)
        if native_bits != source_bits[:2]:
            raise burst.ContractError(
                f"source sincos differs for {name}: native={native_bits!r}, source={source_bits[:2]!r}"
            )
        vectors.append({
            "name": name,
            "input": {"float32": _from_bits(input_bits), "bitsLe": struct.pack("<I", input_bits).hex()},
            "path": source_bits[2],
            "output": {
                "sinFloat32": _from_bits(native_bits[0]),
                "sinBitsLe": struct.pack("<I", native_bits[0]).hex(),
                "cosFloat32": _from_bits(native_bits[1]),
                "cosBitsLe": struct.pack("<I", native_bits[1]).hex(),
            },
        })
    return {
        "schema": "endfield.charinfo.secondary-dynamics-float-sincos-golden-vectors.v1",
        "status": "native_helper_and_source_only_transcription_exact_for_controlled_and_boundary_cases",
        "nativeGate": gate,
        "helper": {"rva": f"0x{SINCOS_RVA:x}", "bytes": SINCOS_BYTES, "sha256": SINCOS_SHA256},
        "largeReducer": {"rva": f"0x{REDUCER_RVA:x}", "bytes": REDUCER_BYTES, "sha256": REDUCER_SHA256},
        "reducerTable": {"rva": f"0x{TABLE_RVA:x}", "bytes": TABLE_BYTES, "sha256": TABLE_SHA256,
                         "words": len(_TABLE)},
        "operationContract": {
            "reductionBranches": ["abs(x) < 125", "125 <= abs(x) < 39000", "finite abs(x) >= 39000",
                                  "infinity or NaN -> canonical quiet NaN"],
            "smallSplitBits": ["bfc90e00", "b86d5000", "b0885a31"],
            "mediumSplitBits": ["bfc90000", "b9fd8000", "b4a88000", "ae85a309"],
            "sinePolynomialBits": ["b94ca65b", "3c08839a", "be2aaaa2"],
            "cosinePolynomialBits": ["b491ed89", "37d0078b", "bab60b58", "3d2aaaaa", "bf000000", "3f800000"],
            "quadrant": "n low bits swap sine/cosine and XOR sign bits; cosine sign uses n+1",
            "specialCases": "negative zero preserves sine sign; infinities and all NaNs return canonical qNaN lanes",
            "sourceCallsNativeHelper": False,
            "sourceReadsNativeReducerTable": False,
        },
        "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "vectors": vectors,
        "boundary": {"nativeHelperExecuted": True, "sourceOnlyTranscriptionMatchedBitForBit": True,
                     "caseCount": len(vectors)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build_contract(), indent=2, allow_nan=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != payload:
            raise SystemExit("Float sincos golden vectors differ")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
