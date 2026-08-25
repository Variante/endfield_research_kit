#!/usr/bin/env python3
"""Build Endminf's pinned 16-lane ClothParameters curve-sample contract."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
SOLVER_INPUTS = SOURCE_ROOT / "secondary_dynamics_solver_inputs.json"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_curve_samples_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None
DEFAULT_UNITY = Path(r"D:\Program Files\2021.3.34f1\Editor\Unity.exe")
DEFAULT_CROSSCHECK_UNITY = Path(r"D:\Program Files\2022.3.62f3\Editor\Unity.exe")

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_GAME_UNITY_VERSION = "2021.3.34f5"
EXPECTED_PROBE_UNITY_VERSION = "2021.3.34f1"
EXPECTED_CROSSCHECK_UNITY_VERSION = "2022.3.62f3"
EXPECTED_UNITY_PLAYER_SHA256 = "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2"
EXPECTED_GLOBAL_GAME_MANAGERS_SHA256 = "191619377ff312b785aae10faec8a75e39caf1ba60016ad08eff040b8c54f20d"

METHODS = {
    383686: ("BeyondDynamicBone.ClothSerializeData", "GetClothParameters", 0x18308A880, 784,
             "3310b78bf6c6eb495e70f7ae1ca93885f9689da0a3f4bdb9c7805826e1998380"),
    384360: ("BeyondDynamicBone.CurveSerializeData", "ConvertFloatArray", 0x18308ADC0, 256,
             "8fe7fc0bfabb68a5d6ef44c05d6f7f6b7f6d5181c76de72b74985053fcaac24b"),
    385965: ("BeyondDynamicBone.DataUtility", "ConvertAnimationCurve", 0x18308B620, 352,
             "9e2729a75917c7dd1221b7369b6b159288e7ffb8caf10a26c85a3d622e8a0ba9"),
}
HELPERS = {
    "float4x4_scalar_multiply": (0x18308B020, 185,
        "3f0c3ccdbcdf23a78cebcc4d503c41a33fcd594d0ccd661060ff4a45ede59f36"),
    "float4_scalar_multiply": (0x18308B480, 17,
        "71bac37f28c7d489d0ecd0fcf9d9e0b06c6c4bcf357819faab1baa23f54a5b00"),
}

# These are the only float4x4 curve buffers read by the requested solver stages.
CURVES: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("dampingCurveData", ("damping",), "Start", "0x1c"),
    ("radiusCurveData", ("radius",), "Point", "0x5c"),
    ("distanceRestorationStiffness", ("distanceConstraint", "stiffness"), "Distance", "0xf4"),
    ("angleRestorationStiffness", ("angleRestorationConstraint", "stiffness"), "Angle", "0x144"),
    ("angleLimit", ("angleLimitConstraint", "limitAngle"), "Angle", "0x190"),
)
STAGE_BUFFER_COUNTS = {"Start": 1, "Tether": 0, "Distance": 1, "Angle": 2,
                       "Point": 1, "Basic": 0, "End": 0}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _native_evidence(gameassembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != "validated":
        raise ContractError(f"common.check_installed_native_inputs [{gate.status}]: {gate.detail}")
    game_path, metadata_path = Path(gate.gameassembly), Path(gate.metadata)
    unity_player = game_path.parent / "UnityPlayer.dll"
    global_game_managers = game_path.parent / "Endfield_Data/globalgamemanagers"
    if not unity_player.is_file() or _sha256(unity_player) != EXPECTED_UNITY_PLAYER_SHA256:
        raise ContractError("installed UnityPlayer.dll missing or mismatched")
    if (not global_game_managers.is_file()
            or _sha256(global_game_managers) != EXPECTED_GLOBAL_GAME_MANAGERS_SHA256
            or EXPECTED_GAME_UNITY_VERSION.encode("ascii") not in global_game_managers.read_bytes()):
        raise ContractError("installed globalgamemanagers Unity version/hash drift")
    root = REPO_ROOT / "tools/endfield-il2cpp"
    catalog = _load("curve_samples_metadata", root / "catalog_option_flow_metadata.py")
    native = _load("curve_samples_native", root / "map_body_targets_to_gameassembly.py")
    md, pe = catalog.Metadata(metadata_path), native.PeImage(game_path)
    code_registration = native.find_code_registration(pe, {md.string(x.name_index) for x in md.images})
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(f"code registration drift: 0x{code_registration:x}")
    modules = native.parse_codegen_modules(pe, code_registration)
    _, by_pointer = native.build_pointer_indexes(pe, md, modules, native.image_method_ranges(md))
    all_pointers = sorted(pointer for pointer in by_pointer if pointer)
    rows = []
    bodies: dict[int, bytes] = {}
    for method_index, (type_name, method_name, expected_va, expected_size, expected_hash) in METHODS.items():
        matches = [(pointer, row) for pointer, identities in by_pointer.items() for row in identities
                   if int(row.get("methodIndex", -1)) == method_index]
        if len(matches) != 1:
            raise ContractError(f"method {method_index} resolves to {len(matches)} pointers")
        pointer, identity = matches[0]
        end = all_pointers[bisect.bisect_right(all_pointers, pointer)]
        body = pe.bytes_at_va(pointer, end - pointer)
        digest = hashlib.sha256(body).hexdigest()
        if (identity.get("type"), identity.get("method")) != (type_name, method_name):
            raise ContractError(f"method {method_index} identity drift")
        if (pointer, len(body), digest) != (expected_va, expected_size, expected_hash):
            raise ContractError(f"method {method_index} native body drift")
        bodies[method_index] = body
        rows.append({"methodIndex": method_index, "type": type_name, "method": method_name,
                     "token": identity["token"], "va": f"0x{pointer:x}",
                     "bytes": len(body), "sha256": digest})

    helper_rows = []
    for name, (va, size, expected_hash) in HELPERS.items():
        body = pe.bytes_at_va(va, size)
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected_hash:
            raise ContractError(f"native helper {name} drift")
        helper_rows.append({"name": name, "va": f"0x{va:x}", "bytes": size, "sha256": digest})

    # ConvertAnimationCurve: ebx starts at zero, evaluates before increment, loops to 16,
    # and computes the next time using cvtdq2ps followed by divss against 15.0f.
    curve_body = bodies[385965]
    signatures = {
        "initialLaneAndZeroTime": (0x89, bytes.fromhex("33db0f57f6")),
        "sixteenLaneStop": (0xED, bytes.fromhex("83fb107d11")),
        "floatIndexConversion": (0xF2, bytes.fromhex("660f6ef30f5bf6")),
        "divideByFifteen": (0xF9, bytes.fromhex("f30f5e35")),
    }
    for name, spec in signatures.items():
        offset, expected = spec
        if curve_body[offset:offset + len(expected)] != expected:
            raise ContractError(f"ConvertAnimationCurve signature {name} drift")
    fifteen_va = 0x18B9593B0
    fifteen = pe.bytes_at_va(fifteen_va, 4)
    if fifteen != struct.pack("<f", 15.0):
        raise ContractError("ConvertAnimationCurve divisor drift")
    convert = bodies[384360]
    if (convert[0x27:0x2A] != bytes.fromhex("384314")
            or convert[0x95:0x9A] != bytes.fromhex("e8c6070000")
            or convert[0xCC:0xD1] != bytes.fromhex("e88f010000")):
        raise ContractError("ConvertFloatArray useCurve/scalar-multiply branch drift")
    return {
        "gameAssembly": {"path": _repo_path(game_path), "size": game_path.stat().st_size,
                         "sha256": gate.gameassembly_sha256},
        "globalMetadata": {"path": _repo_path(metadata_path), "size": metadata_path.stat().st_size,
                           "sha256": gate.metadata_sha256},
        "unityPlayer": {"path": _repo_path(unity_player), "size": unity_player.stat().st_size,
                        "sha256": EXPECTED_UNITY_PLAYER_SHA256,
                        "unityVersion": EXPECTED_GAME_UNITY_VERSION},
        "globalGameManagers": {"path": _repo_path(global_game_managers),
                               "size": global_game_managers.stat().st_size,
                               "sha256": EXPECTED_GLOBAL_GAME_MANAGERS_SHA256},
        "codeRegistrationVa": f"0x{code_registration:x}",
        "methods": rows,
        "helpers": helper_rows,
        "sampleDivisor": {"va": f"0x{fifteen_va:x}", "value": 15.0, "bits": fifteen.hex()},
    }


def _at(value: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    current: Any = value
    for key in path:
        current = current[key]
    if not isinstance(current, dict) or not {"value", "useCurve", "curve"} <= set(current):
        raise ContractError(f"serialized curve payload missing at {'.'.join(path)}")
    return current


def _csharp_float(value: float) -> str:
    bits = struct.unpack("<I", struct.pack("<f", float(value)))[0]
    return f"BitConverter.Int32BitsToSingle(unchecked((int)0x{bits:08x}))"


def _unity_probe(curves: list[dict[str, Any]], unity: Path,
                 expected_version: str) -> tuple[dict[str, list[str]], str]:
    if not unity.is_file():
        raise ContractError(f"Unity executable not found: {unity}")
    cases = []
    for index, row in enumerate(curves):
        keys = []
        for key in row["curve"]["m_Curve"]:
            keys.append(
                "new Keyframe { time = %s, value = %s, inTangent = %s, outTangent = %s, "
                "weightedMode = (WeightedMode)%d, inWeight = %s, outWeight = %s }" % (
                    _csharp_float(key["time"]), _csharp_float(key["value"]),
                    _csharp_float(key["inSlope"]), _csharp_float(key["outSlope"]),
                    int(key["weightedMode"]), _csharp_float(key["inWeight"]),
                    _csharp_float(key["outWeight"]),
                )
            )
        if (int(row["curve"]["m_PreInfinity"]), int(row["curve"]["m_PostInfinity"])) != (2, 2):
            raise ContractError("Endminf curve infinity mode left the verified constant/clamped domain")
        cases.append(
            "Probe(%d, %s, %s, new Keyframe[] { %s });" % (
                index, "true" if row["useCurve"] else "false", _csharp_float(row["value"]),
                ",".join(keys),
            )
        )
    script = """using System; using System.IO; using UnityEditor; using UnityEngine;
public static class CurveSamplesProbe {
  static StreamWriter output;
  static void Probe(int id, bool useCurve, float scalar, Keyframe[] keys) {
    var curve = new AnimationCurve(keys);
    output.Write(id.ToString());
    for (int i=0;i<16;i++) { float t=(float)i/15.0f; float v=useCurve ? curve.Evaluate(t)*scalar : scalar;
      output.Write(" " + BitConverter.SingleToInt32Bits(v).ToString("x8")); }
    output.WriteLine();
  }
  public static void Run() { output=new StreamWriter(Environment.GetEnvironmentVariable("ENDFIELD_CURVE_PROBE_OUTPUT"));
    %s output.Dispose(); EditorApplication.Exit(0); }
}
""" % " ".join(cases)
    # Unity can retain short-lived Windows file handles after its parent exits.
    # Ignore only cleanup errors in the OS temp tree; contract validation above
    # still fails closed on every probe/process/output error.
    with tempfile.TemporaryDirectory(prefix="endfield_curve_samples_", ignore_cleanup_errors=True) as temp_name:
        root = Path(temp_name)
        (root / "Assets/Editor").mkdir(parents=True)
        (root / "ProjectSettings").mkdir()
        (root / "ProjectSettings/ProjectVersion.txt").write_text(
            f"m_EditorVersion: {expected_version}\n",
            encoding="utf-8",
        )
        (root / "Assets/Editor/CurveSamplesProbe.cs").write_text(script, encoding="utf-8")
        output, log = root / "curve_samples.txt", root / "unity.log"
        env = dict(__import__("os").environ)
        env["ENDFIELD_CURVE_PROBE_OUTPUT"] = str(output)
        process = subprocess.run(
            [str(unity), "-batchmode", "-nographics", "-quit", "-projectPath", str(root),
             "-executeMethod", "CurveSamplesProbe.Run", "-logFile", str(log)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT, timeout=300,
        )
        log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        if process.returncode != 0 or not output.is_file():
            raise ContractError(f"Unity curve probe failed ({process.returncode}): {log_text[-2000:]}")
        rows: dict[str, list[str]] = {}
        for line in output.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) != 17:
                raise ContractError(f"Unity curve probe emitted malformed row: {line!r}")
            rows[parts[0]] = parts[1:]
        if len(rows) != len(curves):
            raise ContractError("Unity curve probe row count drift")
        version_line = next((line for line in log_text.splitlines() if "Version:" in line), "")
        if expected_version not in log_text and expected_version not in version_line:
            raise ContractError("Unity curve probe version drift")
        return rows, hashlib.sha256(script.encode("utf-8")).hexdigest()


def build_contract(gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA,
                   unity: Path = DEFAULT_UNITY,
                   crosscheck_unity: Path = DEFAULT_CROSSCHECK_UNITY) -> dict[str, Any]:
    native = _native_evidence(gameassembly, metadata)
    source = json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))
    if source.get("schema") != "endfield.charinfo.secondary-dynamics-solver-inputs.v1":
        raise ContractError("solver-input schema drift")
    cloths = source.get("actors", {}).get("endminf", {}).get("cloths", [])
    if [row.get("game_object_path") for row in cloths] != ["MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat"]:
        raise ContractError("Endminf owner order drift")
    probe_inputs: list[dict[str, Any]] = []
    descriptors: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for owner in cloths:
        serialized = owner["serialized_data"]
        for buffer_name, path, stage, offset in CURVES:
            value = _at(serialized, path)
            keys = value["curve"].get("m_Curve", [])
            key_times = [struct.pack("<f", float(key.get("time", float("nan")))) for key in keys]
            curve = value["curve"]
            if (len(keys) != 2 or key_times != [struct.pack("<f", 0.0), struct.pack("<f", 1.0)]
                    or any(int(key.get("weightedMode", -1)) != 0 for key in keys)
                    or (int(curve.get("m_PreInfinity", -1)), int(curve.get("m_PostInfinity", -1))) != (2, 2)
                    or int(curve.get("m_RotationOrder", -1)) != 4):
                raise ContractError(f"unsupported/unresolved curve domain: {owner['game_object_path']} {buffer_name}")
            descriptors.append((owner["game_object_path"], buffer_name, stage, offset, value))
            probe_inputs.append(value)
    samples, probe_sha = _unity_probe(probe_inputs, unity, EXPECTED_PROBE_UNITY_VERSION)
    crosscheck_samples, crosscheck_sha = _unity_probe(
        probe_inputs, crosscheck_unity, EXPECTED_CROSSCHECK_UNITY_VERSION)
    if crosscheck_samples != samples:
        raise ContractError("2021/2022 Unity AnimationCurve golden outputs differ")
    owners: dict[str, dict[str, Any]] = {}
    for index, (owner, name, stage, offset, value) in enumerate(descriptors):
        bits = samples[str(index)]
        packed = [struct.pack("<I", int(item, 16)) for item in bits]
        values = [struct.unpack("<f", item)[0] for item in packed]
        owners.setdefault(owner, {"buffers": {}})["buffers"][name] = {
            "consumerStage": stage, "clothParametersOffset": offset,
            "sourcePath": ".".join(next(path for n, path, _, _ in CURVES if n == name)),
            "value": value["value"], "useCurve": bool(value["useCurve"]),
            "keyframes": value["curve"]["m_Curve"],
            "samples": values, "sampleBitsHex": bits,
            "packedLittleEndianSha256": hashlib.sha256(b"".join(packed)).hexdigest(),
        }
    return {
        "schema": "endfield.charinfo.secondary-dynamics-curve-samples.v1",
        "status": "endminf_requested_stage_curve_samples_exact",
        "nativeGate": native,
        "source": {"solverInputs": {"path": _repo_path(SOLVER_INPUTS),
                                      "size": SOLVER_INPUTS.stat().st_size,
                                      "sha256": _sha256(SOLVER_INPUTS)}},
        "conversion": {
            "laneCount": 16,
            "sampleOrder": "ascending lane i=0..15",
            "samplePosition": "binary32(i) / binary32(15.0), one divss per lane after lane zero",
            "curveEvaluation": "UnityEngine.AnimationCurve.Evaluate(binary32 position)",
            "verifiedCurveDomain": (
                "exactly two unweighted keys at binary32 times 0 and 1; serialized pre/post "
                "infinity mode 2 (constant/clamped); unweighted cubic Hermite uses key0 "
                "outSlope and key1 inSlope"
            ),
            "floatRoundingAuthority": (
                "published lane words are the executed native Unity evaluator result followed "
                "by the GameAssembly-proven binary32 scalar mulps; no host-language polynomial "
                "re-evaluation is used"
            ),
            "useCurveFalse": "all lanes equal the authored binary32 scalar",
            "useCurveTrue": "Evaluate result multiplied by authored scalar with packed binary32 mulps",
            "matrixLaneOrder": "float4x4 c0.xyzw, c1.xyzw, c2.xyzw, c3.xyzw",
            "unityGolden": {
                "installedGameVersion": EXPECTED_GAME_UNITY_VERSION,
                "nearestPatchExecutable": _repo_path(unity),
                "nearestPatchVersion": EXPECTED_PROBE_UNITY_VERSION,
                "nearestPatchProbeSourceSha256": probe_sha,
                "crosscheckExecutable": _repo_path(crosscheck_unity),
                "crosscheckVersion": EXPECTED_CROSSCHECK_UNITY_VERSION,
                "crosscheckProbeSourceSha256": crosscheck_sha,
                "allRowsExecuted": True,
                "allLaneWordsBitIdenticalAcrossProbes": True,
            },
        },
        "requestedStageBufferCounts": STAGE_BUFFER_COUNTS,
        "owners": owners,
        "validation": {
            "nativeMethodsHashPinned": True,
            "nativeSamplingLoopAndScalarMultiplyPinned": True,
            "authoredInputsHashPinned": True,
            "unityAnimationCurveExecuted": True,
            "allOwnerBufferCount": len(descriptors),
            "unresolvedDomains": [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--unity", type=Path, default=DEFAULT_UNITY)
    parser.add_argument("--crosscheck-unity", type=Path, default=DEFAULT_CROSSCHECK_UNITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_contract(args.gameassembly, args.metadata, args.unity, args.crosscheck_unity)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            raise ContractError(f"generated contract differs: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": payload["status"], "owners": len(payload["owners"]),
                      "buffers": payload["validation"]["allOwnerBufferCount"],
                      "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
