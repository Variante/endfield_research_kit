#!/usr/bin/env python3
"""Build the pinned BeyondDynamicBone TimeManager stepping contract.

This closes the fixed-client scheduling scalars used by the secondary-dynamics
solver.  It does not implement constraints or enable transform writeback.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_time_manager_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0

METHODS = {
    385734: ("Initialize", 0x1835BA850, 560, "6e39b0ea824c6375f1c14e1500fb17bde06d8afc1779736bee8b5a4c33c9632b"),
    385736: ("AfterFixedUpdate", 0x183E4A330, 112, "a1f54667445c72f0502805ed5d6b00a8d7c4680b26bc7c29207d8e0063cd5b61"),
    385737: ("AfterRenderring", 0x183234180, 112, "cc9c3c4b5eebd8cf471c08ef6738339740f4989e40eb3544ae34a6759ae74c4b"),
    385738: ("GetDeltaTime", 0x183231FA0, 128, "f7ef6cd96a92a7a2a07592f51c9fb3f6936304943d073225021516f33f95d951"),
    385739: ("GetFixedDeltaTime", 0x183232020, 64, "ab9c53a98bab0a463553003587b553db5134a5c90a00aacbb879d73ee18ec369"),
    385740: ("GetUnscaledDeltaTime", 0x183231F60, 64, "1fe77eb36686402d4552846ee1a17bdc40d5f53fd38e7e22c8f60fef8dea452b"),
    385741: ("FrameUpdate", 0x1834460C0, 448, "7a539536c6ac6431798cbb2cd35fc0601e4af158b620f2cafe26baeb7de2b863"),
    385743: (".ctor", 0x184D87460, 32, "a892c8d0275f9a1665d104b60f0cda87628a3b0dd2a49158a2a377297d787d63"),
}

FIELD_OFFSETS = {
    "simulationFrequency": "0x10",
    "maxSimulationCountPerFrame": "0x14",
    "updateLocation": "0x18",
    "isValid": "0x1c",
    "FixedUpdateCount": "0x20",
    "GlobalTimeScale": "0x24",
    "SimulationDeltaTime": "0x28",
    "MaxDeltaTime": "0x2c",
    "SimulationPower": "0x30",
    "DeltaTime": "0x40",
    "FixedDeltaTime": "0x44",
    "UnscaledDeltaTime": "0x48",
    "EnableAOVMode": "0x4c",
}

CONSTANTS = {
    "one": (0x18B959200, 1.0),
    "referenceFrequency": (0x18B959478, 90.0),
    "powerExponent": (0x18B95958C, 1.7999999523162842),
}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (
        _load("secondary_time_metadata", root / "catalog_option_flow_metadata.py"),
        _load("secondary_time_native", root / "map_body_targets_to_gameassembly.py"),
    )


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file(path: Path, digest: str) -> dict[str, Any]:
    return {"path": _repo_path(path), "size": path.stat().st_size, "sha256": digest}


def _method_indexes(native: Any, md: Any, pe: Any) -> tuple[dict[int, list[dict[str, Any]]], list[int]]:
    code_registration = native.find_code_registration(
        pe, {md.string(image.name_index) for image in md.images}
    )
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(f"code registration drift: 0x{code_registration:x}")
    modules = native.parse_codegen_modules(pe, code_registration)
    _, by_pointer = native.build_pointer_indexes(
        pe, md, modules, native.image_method_ranges(md)
    )
    return by_pointer, sorted(pointer for pointer in by_pointer if pointer)


def build_contract(
    gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
) -> dict[str, Any]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if gate.status != "validated":
        raise ContractError(f"common.check_installed_native_inputs [{gate.status}]: {gate.detail}")
    game_path = Path(gate.gameassembly)
    metadata_path = Path(gate.metadata)
    catalog, native = _helpers()
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    by_pointer, all_pointers = _method_indexes(native, md, pe)

    methods = []
    bodies: dict[int, bytes] = {}
    for method_index, (name, expected_va, expected_size, expected_hash) in METHODS.items():
        candidates = [
            (pointer, row)
            for pointer, rows in by_pointer.items()
            for row in rows
            if int(row.get("methodIndex", -1)) == method_index
        ]
        if len(candidates) != 1:
            raise ContractError(f"method {method_index} resolves to {len(candidates)} pointers")
        pointer, identity = candidates[0]
        end = all_pointers[bisect.bisect_right(all_pointers, pointer)]
        body = pe.bytes_at_va(pointer, end - pointer)
        digest = hashlib.sha256(body).hexdigest()
        if identity.get("type") != "BeyondDynamicBone.TimeManager" or identity.get("method") != name:
            raise ContractError(f"method {method_index} identity drift")
        if pointer != expected_va or len(body) != expected_size or digest != expected_hash:
            raise ContractError(f"method {method_index} native body drift")
        bodies[method_index] = body
        methods.append({
            "methodIndex": method_index,
            "method": name,
            "token": identity["token"],
            "va": f"0x{pointer:x}",
            "bytes": len(body),
            "sha256": digest,
        })

    ctor = bodies[385743]
    if not (ctor.startswith(bytes.fromhex("c741105a000000c7411403000000c741240000803f"))):
        raise ContractError("TimeManager constructor constants drift")
    frame = bodies[385741]
    if frame[0x100:0x105] != bytes.fromhex("e8db07effc"):
        raise ContractError("FrameUpdate scalar power-helper call drift")
    if int.from_bytes(frame[0x101:0x105], "little", signed=True) + 0x1834461C5 != 0x1803369A0:
        raise ContractError("FrameUpdate scalar power-helper target drift")

    constants = {}
    for name, (address, expected) in CONSTANTS.items():
        raw = pe.bytes_at_va(address, 4)
        value = struct.unpack("<f", raw)[0]
        if struct.pack("<f", value) != struct.pack("<f", expected):
            raise ContractError(f"TimeManager constant {name} drift")
        constants[name] = {"va": f"0x{address:x}", "value": value, "bits": raw.hex()}

    return {
        "schema": "endfield.charinfo.secondary-dynamics-time-manager.v1",
        "status": "retail_default_step_scalars_closed_nondefault_power_helper_unported",
        "nativeGate": {
            "gameAssembly": _file(game_path, gate.gameassembly_sha256),
            "globalMetadata": _file(metadata_path, gate.metadata_sha256),
            "codeRegistrationVa": f"0x{EXPECTED_CODE_REGISTRATION:x}",
        },
        "type": "BeyondDynamicBone.TimeManager",
        "fieldOffsets": FIELD_OFFSETS,
        "methods": methods,
        "constants": constants,
        "constructorDefaults": {
            "simulationFrequency": 90,
            "maxSimulationCountPerFrame": 3,
            "GlobalTimeScale": 1.0,
        },
        "frameUpdate": {
            "frequencyClampInclusive": [30, 150],
            "simulationCountClampInclusive": [1, 5],
            "globalTimeScaleClampInclusive": [0.0, 1.0],
            "equations": [
                "SimulationDeltaTime = float32(1.0f / float32(simulationFrequency))",
                "MaxDeltaTime = float32(float32(maxSimulationCountPerFrame) * SimulationDeltaTime)",
                "basePower = min(float32(90.0f / float32(simulationFrequency)), 1.0f)",
                "SimulationPower.xyz = basePower",
                "SimulationPower.w = pinnedScalarPowerHelper(basePower, 1.8f)",
            ],
            "scalarPowerHelper": {
                "va": "0x1803369a0",
                "ported": False,
                "defaultInput": [1.0, 1.7999999523162842],
                "defaultOutput": 1.0,
            },
            "retailDefault": {
                "SimulationDeltaTime": 1.0 / 90.0,
                "MaxDeltaTime": 3.0 / 90.0,
                "SimulationPower": [1.0, 1.0, 1.0, 1.0],
            },
        },
        "callbacks": {
            "AfterFixedUpdate": "FixedUpdateCount += 1",
            "AfterRenderring": "FixedUpdateCount = 0",
        },
        "timeSources": {
            "normalMode": {
                "DeltaTime": "UnityEngine.Time.deltaTime",
                "FixedDeltaTime": "UnityEngine.Time.fixedDeltaTime",
                "UnscaledDeltaTime": "UnityEngine.Time.unscaledDeltaTime",
            },
            "aovMode": "uses the separately stored DeltaTime/FixedDeltaTime/UnscaledDeltaTime backing values",
        },
        "implementationBoundary": {
            "retailDefaultStepScalarsClosed": True,
            "nondefaultScalarPowerHelperPorted": False,
            "simulationSubstepAccumulatorClosed": False,
            "solverWritebackEnabled": False,
            "visualVerificationPerformed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        contract = build_contract(args.gameassembly, args.metadata)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    except (ContractError, OSError, ValueError) as exc:
        print(f"secondary dynamics TimeManager contract failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
