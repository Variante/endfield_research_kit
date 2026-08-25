#!/usr/bin/env python3
"""Build the exact Endminf GetClothParameters scalar-packing contract."""

from __future__ import annotations

import argparse
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
SOLVER_INPUTS = SOURCE_ROOT / "secondary_dynamics_solver_inputs.json"
CURVE_CONTRACT = SOURCE_ROOT / "secondary_dynamics_curve_samples_contract.json"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_solver_scalar_packing_contract.json"

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_SOLVER_INPUTS_SIZE = 1_447_800
EXPECTED_SOLVER_INPUTS_SHA256 = "1f8e4a881a7f82aefe159e0596220e730653ea101e765163757cac756dfffd2b"

GET_CLOTH_PARAMETERS = {
    "methodIndex": 383686,
    "type": "BeyondDynamicBone.ClothSerializeData",
    "method": "GetClothParameters",
    "va": 0x18308A880,
    "bytes": 784,
    "sha256": "3310b78bf6c6eb495e70f7ae1ca93885f9689da0a3f4bdb9c7805826e1998380",
}
HELPERS = {
    "tether": {
        "va": 0x18308BED0,
        "bytes": 0x60,
        "sha256": "de1bb3e10bd618d7d1c46a099328a6cc23268bf52586b5ddfdcef8be2a78ba75",
    },
    "distance": {
        "va": 0x18308BD30,
        "bytes": 0x90,
        "sha256": "5020ac4ebe1770a881b20ec3677b552e6ad979600768c30601638e72e7c97bcd",
    },
    "collision": {
        "va": 0x18308BF90,
        "bytes": 0x70,
        "sha256": "bde9cd3c0ada86a62e538e50352a759935a1b1ddf2ed8762f7d9c359937c2708",
    },
}

# Exact argument setup through each rel32 call in GetClothParameters. The
# destination is relative to rbp; the completed ClothParameters local starts
# at rbp-0x60 and is copied to the caller's output at method offset 0x277.
CALLS = {
    "tether": {
        "sequenceOffset": 0x18E,
        "sequenceHex": "448b4310488d8d8c000000488b93c80000004533c9e8a8140000",
        "callOffset": 0x1A3,
        "serializedPointerOffset": 0xC8,
        "destinationStackDisplacement": 0x8C,
    },
    "distance": {
        "sequenceOffset": 0x1A8,
        "sequenceHex": "448b4310488d8d94000000488b93d00000004533c9e8ee120000",
        "callOffset": 0x1BD,
        "serializedPointerOffset": 0xD0,
        "destinationStackDisplacement": 0x94,
    },
    "collision": {
        "sequenceOffset": 0x20F,
        "sequenceHex": "448b4310488d8d04020000488b93f80000004533c9e8e7140000",
        "callOffset": 0x224,
        "serializedPointerOffset": 0xF8,
        "destinationStackDisplacement": 0x204,
    },
}
OUTPUT_BASE_STACK_DISPLACEMENT = -0x60
OUTPUT_COPY_SIGNATURE = (0x277, bytes.fromhex("488bcf488d45a0ba06000000"))

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


def _float_row(value: float) -> dict[str, Any]:
    packed = struct.pack("<f", float(value))
    return {
        "value": struct.unpack("<f", packed)[0],
        "bitsHex": f"{struct.unpack('<I', packed)[0]:08x}",
        "littleEndianBytesHex": packed.hex(),
    }


def _decode_rel32_target(body: bytes, method_va: int, offset: int) -> int:
    if body[offset:offset + 1] != b"\xe8":
        raise ContractError(f"expected rel32 call at GetClothParameters+0x{offset:x}")
    displacement = struct.unpack_from("<i", body, offset + 1)[0]
    return method_va + offset + 5 + displacement


def _verify_signature(body: bytes, offset: int, expected: bytes, label: str) -> None:
    if body[offset:offset + len(expected)] != expected:
        raise ContractError(f"native signature drift: {label}")


def _native_evidence(gameassembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if gate.status != "validated":
        raise ContractError(f"common.check_installed_native_inputs [{gate.status}]: {gate.detail}")
    game_path, metadata_path = Path(gate.gameassembly), Path(gate.metadata)
    native = _load(
        "solver_scalar_packing_native",
        REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py",
    )
    pe = native.PeImage(game_path)

    curve = json.loads(CURVE_CONTRACT.read_text(encoding="utf-8"))
    methods = {row["methodIndex"]: row for row in curve.get("nativeGate", {}).get("methods", [])}
    curve_method = methods.get(GET_CLOTH_PARAMETERS["methodIndex"])
    expected_curve_row = {
        key: GET_CLOTH_PARAMETERS[key]
        for key in ("methodIndex", "type", "method", "va", "bytes", "sha256")
    }
    if curve_method is None or {
        "methodIndex": curve_method.get("methodIndex"),
        "type": curve_method.get("type"),
        "method": curve_method.get("method"),
        "va": int(curve_method.get("va", "0"), 16),
        "bytes": curve_method.get("bytes"),
        "sha256": curve_method.get("sha256"),
    } != expected_curve_row:
        raise ContractError("curve contract GetClothParameters identity/body gate drift")

    method_body = pe.bytes_at_va(GET_CLOTH_PARAMETERS["va"], GET_CLOTH_PARAMETERS["bytes"])
    if hashlib.sha256(method_body).hexdigest() != GET_CLOTH_PARAMETERS["sha256"]:
        raise ContractError("GetClothParameters native body drift")
    output_offset, output_signature = OUTPUT_COPY_SIGNATURE
    _verify_signature(method_body, output_offset, output_signature, "completed output copy base")

    helper_rows: dict[str, Any] = {}
    call_rows: dict[str, Any] = {}
    helper_bodies: dict[str, bytes] = {}
    for name, expected in HELPERS.items():
        helper_body = pe.bytes_at_va(expected["va"], expected["bytes"])
        digest = hashlib.sha256(helper_body).hexdigest()
        if digest != expected["sha256"]:
            raise ContractError(f"{name} helper native body drift")
        helper_bodies[name] = helper_body
        helper_rows[name] = {
            "va": f"0x{expected['va']:x}",
            "bytes": expected["bytes"],
            "endVaExclusive": f"0x{expected['va'] + expected['bytes']:x}",
            "sha256": digest,
        }
        call = CALLS[name]
        sequence = bytes.fromhex(call["sequenceHex"])
        _verify_signature(method_body, call["sequenceOffset"], sequence, f"{name} argument setup")
        target = _decode_rel32_target(method_body, GET_CLOTH_PARAMETERS["va"], call["callOffset"])
        if target != expected["va"]:
            raise ContractError(f"GetClothParameters {name} helper target drift")
        output_base_offset = call["destinationStackDisplacement"] - OUTPUT_BASE_STACK_DISPLACEMENT
        call_rows[name] = {
            "argumentSetupOffset": f"0x{call['sequenceOffset']:x}",
            "argumentSetupBytesHex": call["sequenceHex"],
            "callOffset": f"0x{call['callOffset']:x}",
            "callVa": f"0x{GET_CLOTH_PARAMETERS['va'] + call['callOffset']:x}",
            "targetVa": f"0x{target:x}",
            "serializedPointerSource": f"ClothSerializeData+0x{call['serializedPointerOffset']:x}",
            "helperDestination": f"stack rbp+0x{call['destinationStackDisplacement']:x}",
            "clothParametersBase": "stack rbp-0x60",
            "clothParametersDestinationOffset": f"0x{output_base_offset:x}",
        }

    # Prove the helper bodies at instruction-byte granularity. These signatures
    # contain the source loads, destination stores, and literal words at issue.
    helper_signatures = {
        "tether": [(0x3A, "8b47108903c743048fc2f53c")],
        "distance": [(0x5F, "0f11070f114f100f1157200f115f30c747409a99993e")],
        "collision": [(0x3A, "8b431089078b43148947048b4314894708")],
    }
    for name, rows in helper_signatures.items():
        for offset, signature_hex in rows:
            _verify_signature(helper_bodies[name], offset, bytes.fromhex(signature_hex), f"{name} body stores")

    return {
        "gameAssembly": {
            "path": _repo_path(game_path),
            "size": game_path.stat().st_size,
            "sha256": gate.gameassembly_sha256,
        },
        "globalMetadata": {
            "path": _repo_path(metadata_path),
            "size": metadata_path.stat().st_size,
            "sha256": gate.metadata_sha256,
        },
        "curveContract": {
            "path": _repo_path(CURVE_CONTRACT),
            "size": CURVE_CONTRACT.stat().st_size,
            "sha256": _sha256(CURVE_CONTRACT),
            "methodIdentityCrossChecked": True,
        },
        "method": {
            "methodIndex": GET_CLOTH_PARAMETERS["methodIndex"],
            "type": GET_CLOTH_PARAMETERS["type"],
            "method": GET_CLOTH_PARAMETERS["method"],
            "va": f"0x{GET_CLOTH_PARAMETERS['va']:x}",
            "bytes": GET_CLOTH_PARAMETERS["bytes"],
            "endVaExclusive": f"0x{GET_CLOTH_PARAMETERS['va'] + GET_CLOTH_PARAMETERS['bytes']:x}",
            "sha256": GET_CLOTH_PARAMETERS["sha256"],
            "completedOutputLocalBase": "rbp-0x60",
            "completedOutputCopySignatureOffset": f"0x{output_offset:x}",
            "completedOutputCopySignatureHex": output_signature.hex(),
        },
        "helpers": helper_rows,
        "calls": call_rows,
        "helperBodyProof": {
            "tether": {
                "signatureOffset": "0x3a",
                "signatureHex": helper_signatures["tether"][0][1],
                "equations": [
                    "*(uint32*)(destination+0x0) = *(uint32*)(serializedTether+0x10)",
                    "*(uint32*)(destination+0x4) = 0x3cf5c28f",
                ],
            },
            "distance": {
                "signatureOffset": "0x5f",
                "signatureHex": helper_signatures["distance"][0][1],
                "equations": [
                    "destination+0x0..0x3f = converted authored stiffness float4x4",
                    "*(uint32*)(destination+0x40) = 0x3e99999a",
                ],
            },
            "collision": {
                "signatureOffset": "0x3a",
                "signatureHex": helper_signatures["collision"][0][1],
                "equations": [
                    "*(uint32*)(destination+0x0) = *(uint32*)(serializedCollision+0x10)",
                    "*(uint32*)(destination+0x4) = *(uint32*)(serializedCollision+0x14)",
                    "*(uint32*)(destination+0x8) = *(uint32*)(serializedCollision+0x14)",
                ],
            },
        },
    }


def build_contract(gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    if SOLVER_INPUTS.stat().st_size != EXPECTED_SOLVER_INPUTS_SIZE or _sha256(SOLVER_INPUTS) != EXPECTED_SOLVER_INPUTS_SHA256:
        raise ContractError("secondary_dynamics_solver_inputs.json size/hash drift")
    source = json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))
    if source.get("schema") != "endfield.charinfo.secondary-dynamics-solver-inputs.v1":
        raise ContractError("solver-input schema drift")
    cloths = source.get("actors", {}).get("endminf", {}).get("cloths", [])
    owner_order = ["MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat"]
    if [row.get("game_object_path") for row in cloths] != owner_order:
        raise ContractError("Endminf owner order drift")

    constant_stretch = _float_row(struct.unpack("<f", struct.pack("<I", 0x3CF5C28F))[0])
    constant_velocity = _float_row(struct.unpack("<f", struct.pack("<I", 0x3E99999A))[0])
    owners: dict[str, Any] = {}
    for owner in cloths:
        serialized = owner.get("serialized_data", {})
        try:
            compression = serialized["tetherConstraint"]["distanceCompression"]
            friction = serialized["colliderCollisionConstraint"]["friction"]
        except (KeyError, TypeError) as exc:
            raise ContractError(f"missing Endminf scalar source for {owner.get('game_object_path')}") from exc
        owners[owner["game_object_path"]] = {
            "tetherCompressionLimit": {
                "clothParametersOffset": "0xec",
                "sourcePath": "serialized_data.tetherConstraint.distanceCompression",
                **_float_row(compression),
            },
            "tetherStretchLimit": {
                "clothParametersOffset": "0xf0",
                "sourcePath": "native constant 0x3cf5c28f",
                **constant_stretch,
            },
            "distanceVelocityAttenuation": {
                "clothParametersOffset": "0x134",
                "sourcePath": "native constant 0x3e99999a",
                **constant_velocity,
            },
            "collisionDynamicFriction": {
                "clothParametersOffset": "0x268",
                "sourcePath": "serialized_data.colliderCollisionConstraint.friction",
                **_float_row(friction),
            },
            "collisionStaticFriction": {
                "clothParametersOffset": "0x26c",
                "sourcePath": "serialized_data.colliderCollisionConstraint.friction",
                **_float_row(friction),
            },
        }

    return {
        "schema": "endfield.charinfo.secondary-dynamics-solver-scalar-packing.v1",
        "status": "endminf_get_cloth_parameters_requested_scalars_exact",
        "nativeGate": _native_evidence(gameassembly, metadata),
        "source": {
            "solverInputs": {
                "path": _repo_path(SOLVER_INPUTS),
                "size": SOLVER_INPUTS.stat().st_size,
                "sha256": _sha256(SOLVER_INPUTS),
                "hashPinned": True,
            },
        },
        "packing": {
            "outputBase": "GetClothParameters completed ClothParameters local at rbp-0x60",
            "tether": {
                "helperDestinationOffset": "0xec",
                "writes": {"+0x0": "compression -> ClothParameters+0xec", "+0x4": "0x3cf5c28f -> ClothParameters+0xf0"},
            },
            "distance": {
                "helperDestinationOffset": "0xf4",
                "writes": {"+0x40": "0x3e99999a -> ClothParameters+0x134"},
            },
            "collision": {
                "helperDestinationOffset": "0x264",
                "writes": {"+0x4": "friction -> ClothParameters+0x268", "+0x8": "friction -> ClothParameters+0x26c"},
            },
        },
        "owners": owners,
        "validation": {
            "installedNativeInputsValidated": True,
            "methodAndHelperBodiesHashAndSizePinned": True,
            "helperCallTargetsAndArgumentSetupPinned": True,
            "helperSourceLoadsAndDestinationStoresPinned": True,
            "authoredOwnerSourceHashPinned": True,
            "ownerCount": len(owners),
            "unresolvedRequestedScalars": [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_contract(args.gameassembly, args.metadata)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            raise ContractError(f"generated contract differs: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": payload["status"], "owners": len(payload["owners"]), "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
