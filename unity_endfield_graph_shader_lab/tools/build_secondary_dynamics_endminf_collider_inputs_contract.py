#!/usr/bin/env python3
"""Build the pinned Endminf managed ColliderManager input contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
OUTPUT = SOURCE_ROOT / "secondary_dynamics_endminf_collider_inputs_contract.json"
OWNER = SOURCE_ROOT / "secondary_dynamics_owner_recovery.json"
START = SOURCE_ROOT / "secondary_dynamics_collider_start_semantics_contract.json"
JOB_LAYOUT = SOURCE_ROOT / "secondary_dynamics_job_layout_contract.json"
IFIX = SOURCE_ROOT / "installed_ifix_patch_state.json"

GAME_ASSEMBLY = Path(r"D:/Program Files/Endfield Game/GameAssembly.dll")
GLOBAL_METADATA = Path(
    r"D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
)
LIB_BURST = Path(
    r"D:/Program Files/Endfield Game/Endfield_Data/Plugins/x86_64/lib_burst_generated.dll"
)

PINNED_FILES = {
    GAME_ASSEMBLY: (280436712, "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"),
    GLOBAL_METADATA: (62925560, "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"),
    LIB_BURST: (4042216, "ee8702dd63dec2db7dc29d5bc23b8acd032f0e19a0daad5f69e6c45f9d3ceb99"),
    OWNER: (None, "1051703d0695e26769be9e98a89e57d91ded27939b4888115d59f1e0fe0edaa6"),
    START: (None, "65059af0fd550584ab80b8ca979b53338340eb4a672bb0a1b75ee05b97fac9b1"),
    JOB_LAYOUT: (None, "f8720afa5a0c6715475df119d22e139fcdc0515ad5b461928d51e0596ad2487d"),
    IFIX: (None, "71eaa80479920463835ef5fabc7697dfeea5fef9f287c109e994fca7edcdb9af"),
}

METHOD_SPANS = {
    "BeyondBoneCapsuleCollider.GetColliderType": (
        383709, 0x184552AF0, 0x60,
        "5ea13d0153913cdfae99d7b1278e26592de70e5fead530e5982784f4c4e1de11",
    ),
    "BeyondBoneCapsuleCollider.GetSize": (
        383711, 0x18323E8E0, 0x90,
        "2642d21f5f1e90ffe07aa98b4a06b85d79f2c80612a095d1c6b533137ff4233f",
    ),
    "BeyondBoneCapsuleCollider.IsReverseDirection": (
        383714, 0x1845E7D40, 0x30,
        "a70be918436276d213c69269a046a3c3f0aed21e97f614fb479605ade0738a07",
    ),
    "ColliderManager.AddColliderInternal": (
        385330, 0x1833A86A0, 0x550,
        "22683e8bb0f0f8fb7fd4e6eca8debf2ea553a4598f96b3f010bc57301f04d3bd",
    ),
    "ColliderKernels.PreSimulationUpdateKernel$BurstManaged": (
        385347, 0x18675672C, 0x83C,
        "0c610647139c65e6b0999b882380a0f93c2600de3af77744c89301b187b95bf3",
    ),
}

START_CORE = {
    "exportName": "8b3d2761aaaac71a35d4a2557d570456",
    "rva": 0x243810,
    "bytes": 2732,
    "sha256": "a69539c847d5f68e7a1c155058f8299a6953c79004ef28e14282ccdec26d0615",
}


class ContractError(RuntimeError):
    pass


class PeImage:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        pe = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe:pe + 4] != b"PE\0\0":
            raise ContractError(f"not a PE image: {path}")
        coff = pe + 4
        section_count = struct.unpack_from("<H", self.data, coff + 2)[0]
        optional_size = struct.unpack_from("<H", self.data, coff + 16)[0]
        optional = coff + 20
        if struct.unpack_from("<H", self.data, optional)[0] != 0x20B:
            raise ContractError(f"not an x64 PE image: {path}")
        self.image_base = struct.unpack_from("<Q", self.data, optional + 24)[0]
        section_table = optional + optional_size
        self.sections: list[tuple[int, int, int]] = []
        for index in range(section_count):
            off = section_table + index * 40
            virtual_size, rva, raw_size, raw = struct.unpack_from("<IIII", self.data, off + 8)
            self.sections.append((rva, max(virtual_size, raw_size), raw))

    def at_rva(self, rva: int, size: int) -> bytes:
        for start, span, raw in self.sections:
            if start <= rva and rva + size <= start + span:
                return self.data[raw + rva - start:raw + rva - start + size]
        raise ContractError(f"RVA span outside {self.path}: 0x{rva:x}+0x{size:x}")

    def at_va(self, va: int, size: int) -> bytes:
        return self.at_rva(va - self.image_base, size)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _gate(path: Path, expected_size: int | None, expected_sha: str) -> dict[str, Any]:
    if not path.is_file():
        raise ContractError(f"required source missing: {path}")
    size = path.stat().st_size
    digest = _sha256(path.read_bytes())
    if expected_size is not None and size != expected_size:
        raise ContractError(f"source size drift for {path}: expected {expected_size}, got {size}")
    if digest != expected_sha:
        raise ContractError(f"source hash drift for {path}: expected {expected_sha}, got {digest}")
    try:
        relative = path.relative_to(LAB_ROOT).as_posix()
        return {"path": relative, "size": size, "sha256": digest}
    except ValueError:
        return {"pathAtRecovery": path.as_posix(), "size": size, "sha256": digest}


def _f32_bits(value: float) -> str:
    return struct.pack("<f", float(value)).hex()


def collider_type(direction: int, aligned_on_center: int) -> int:
    if direction not in (0, 1, 2):
        raise ContractError(f"unsupported serialized capsule direction: {direction}")
    if aligned_on_center not in (0, 1):
        raise ContractError(f"non-boolean alignedOnCenter: {aligned_on_center}")
    return direction + (2 if aligned_on_center else 5)


def size_input(size: dict[str, Any], radius_separation: int) -> list[float]:
    if radius_separation not in (0, 1):
        raise ContractError(f"non-boolean radiusSeparation: {radius_separation}")
    x, y, z = (float(size[key]) for key in ("x", "y", "z"))
    return [x, y if radius_separation else x, z]


def registration_flag(collider_type_value: int, enabled: int, reverse: int) -> int:
    if collider_type_value not in range(8):
        raise ContractError(f"collider type does not fit low flag nibble: {collider_type_value}")
    if enabled not in (0, 1) or reverse not in (0, 1):
        raise ContractError("enabled/reverse values must be serialized booleans")
    return collider_type_value | 0x10 | (0x20 if enabled else 0) | 0x40 | (0x80 if reverse else 0)


def _validate_native() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    game = PeImage(GAME_ASSEMBLY)
    method_rows = []
    for name, (method_index, va, size, expected) in METHOD_SPANS.items():
        body = game.at_va(va, size)
        actual = _sha256(body)
        if actual != expected:
            raise ContractError(f"method body drift for {name}: expected {expected}, got {actual}")
        method_rows.append({
            "method": name, "methodIndex": method_index, "va": f"0x{va:x}",
            "bodyBytes": size, "bodySha256": actual,
        })

    add = game.at_va(METHOD_SPANS["ColliderManager.AddColliderInternal"][1], 0x550)
    add_signatures = {
        "virtualGetColliderTypeSlot7": (0xA5, "b907000000488bd6e89ed0c9fc"),
        "validBitOr": (0xB5, "80cb10"),
        "enabledBitSelect": (0xC2, "0fb6cb80e3df80c92084c00f45d9"),
        "resetBitOr": (0xD0, "80cb40"),
        "virtualIsReverseDirectionSlot11": (0xD3, "b90b000000488bd6e800dbc5fc"),
        "reverseBitSelect": (0xE0, "0fb6cb80e37f80c9800fb6db84c00fb6c9488b47180f45d9"),
        "centerCopy": (0x109, "488b4f20f20f104620"),
        "virtualGetSizeSlot9": (0x148, "ba09000000"),
        "transformPosition": (0x193, "488bce"),
        "transformRotationThenLocalScale": (0x1FA, "33d2488bce0f1030e829d0bfff"),
    }
    for label, (offset, expected_hex) in add_signatures.items():
        expected = bytes.fromhex(expected_hex)
        actual = add[offset:offset + len(expected)]
        if actual != expected:
            raise ContractError(f"AddColliderInternal signature drift at {label}")

    pre = game.at_va(METHOD_SPANS["ColliderKernels.PreSimulationUpdateKernel$BurstManaged"][1], 0x83C)
    pre_signatures = {
        "activeFlagGates": (0x72, "f6c3100f866f070000f6c3200f8666070000"),
        "centerTimesScale": (0x1CC, "e8a31d63fe"),
        "float3ToDouble3": (0x1EB, "e88490a0fd"),
        "publishFramePosition": (0x243, "488b85f0050000450f1144cd00f2450f114ccd10"),
        "publishFrameRotation": (0x257, "498bce4803c9f30f7f3cc8"),
        "publishFrameScale": (0x262, "488b85f80500004b8d0c76f20f11348889748808"),
        "resetGateAndClear": (0x276, "488d8d40030000e89a74feff84c00f85ea040000f6c340"),
        "clearResetBit": (0x7E3, "80e3bf43881c26"),
    }
    for label, (offset, expected_hex) in pre_signatures.items():
        expected = bytes.fromhex(expected_hex)
        actual = pre[offset:offset + len(expected)]
        if actual != expected:
            raise ContractError(f"PreSimulationUpdate managed signature drift at {label}")

    burst = PeImage(LIB_BURST)
    core = burst.at_rva(START_CORE["rva"], START_CORE["bytes"])
    actual_core = _sha256(core)
    if actual_core != START_CORE["sha256"]:
        raise ContractError("Collider Start core body drift")
    dispatch_signatures = {
        "capsuleOuterRangeIncludes2Through7": (0x64A, "8d51f880faf90f83b7000000"),
        "capsuleJumpTableIncludesOnly2Through6": (0x70D, "89ca83c2fe83fa047751"),
        "type7FallsThroughZeroWorkPath": (0x731, "c5d057edc5f057c9c4413057c9c4413857c0c5e857d2c5d857e4c5c057ffc4412857d2c4412057dbe996020000"),
    }
    for label, (offset, expected_hex) in dispatch_signatures.items():
        expected = bytes.fromhex(expected_hex)
        if core[offset:offset + len(expected)] != expected:
            raise ContractError(f"Collider Start dispatch signature drift at {label}")
    return (
        {"methods": method_rows, "addColliderInternalSignatures": sorted(add_signatures),
         "preSimulationUpdateSignatures": sorted(pre_signatures)},
        method_rows,
        {
            "exportName": START_CORE["exportName"], "rva": f"0x{START_CORE['rva']:x}",
            "bodyBytes": START_CORE["bytes"], "bodySha256": actual_core,
            "dispatchSignatures": sorted(dispatch_signatures),
        },
    )


def _validate_dependencies() -> tuple[dict[str, Any], dict[str, Any]]:
    owner = json.loads(OWNER.read_text(encoding="utf-8"))
    start = json.loads(START.read_text(encoding="utf-8"))
    layout = json.loads(JOB_LAYOUT.read_text(encoding="utf-8"))
    ifix = json.loads(IFIX.read_text(encoding="utf-8"))
    if owner["source_build"]["game_assembly"]["sha256"] != PINNED_FILES[GAME_ASSEMBLY][1]:
        raise ContractError("owner contract GameAssembly identity drift")
    if start["semanticDecision"]["semanticCandidateHash"] != START_CORE["exportName"]:
        raise ContractError("Collider Start selected export drift")
    jobs = [row for row in layout["jobs"] if row["type"] == "BeyondDynamicBone.ColliderManager+StartSimulationStepJob"]
    if len(jobs) != 1:
        raise ContractError("Collider Start job layout is not unique")
    field_types = {row["name"]: row["elementType"]["name"] for row in jobs[0]["fields"] if "elementType" in row}
    expected_types = {
        "flagArray": "BeyondDynamicBone.ExBitFlag8", "sizeArray": "Unity.Mathematics.float3",
        "framePositions": "Unity.Mathematics.double3", "frameRotations": "Unity.Mathematics.quaternion",
        "frameScales": "Unity.Mathematics.float3", "oldFramePositions": "Unity.Mathematics.double3",
        "oldFrameRotations": "Unity.Mathematics.quaternion", "nowPositions": "Unity.Mathematics.double3",
        "nowRotations": "Unity.Mathematics.quaternion", "oldPositions": "Unity.Mathematics.double3",
        "oldRotations": "Unity.Mathematics.quaternion",
    }
    for name, expected in expected_types.items():
        if field_types.get(name) != expected:
            raise ContractError(f"Collider Start job field type drift for {name}")
    patched = [row for row in ifix["targets"] if row["type"].startswith("BeyondDynamicBone.")]
    if patched:
        raise ContractError(f"installed IFix unexpectedly targets BeyondDynamicBone: {patched}")
    return owner, {"jobFieldTypes": expected_types, "installedIfixBeyondDynamicBoneTargetCount": 0}


def _row(source: dict[str, Any], index: int) -> dict[str, Any]:
    direction = int(source["direction"])
    aligned = int(source["aligned_on_center"])
    reverse = int(source["reverse_direction"])
    radius_separation = int(source["radius_separation"])
    enabled = int(source["enabled"])
    kind = collider_type(direction, aligned)
    registered = registration_flag(kind, enabled, reverse)
    start_flag = registered & 0xBF
    size = size_input(source["size"], radius_separation)
    axis = "xyz"[direction]
    return {
        "index": index,
        "pathId": int(source["path_id"]),
        "gameObjectPath": source["game_object_path"],
        "serialized": {
            "enabled": enabled, "direction": direction, "reverseDirection": reverse,
            "radiusSeparation": radius_separation, "alignedOnCenter": aligned,
            "center": source["center"], "size": source["size"],
            "rawDataSha256": source["raw_data_sha256"],
        },
        "managedMapping": {
            "colliderType": kind,
            "typeName": f"capsule_{axis}_{'centered' if aligned else 'one_sided'}",
            "registrationFlag": f"0x{registered:02x}",
            "colliderStartFlagAfterPreSimulation": f"0x{start_flag:02x}",
            "flagBits": {"valid": True, "enable": bool(enabled), "resetAfterPreSimulation": False,
                         "reverse": bool(reverse)},
            "sizeArray": size,
            "sizeArrayFloatBits": [_f32_bits(value) for value in size],
            "axisScaleExpression": f"transformScale.{axis}",
            "effectiveRadiiAndLengthExpression": "abs(axisScale) * sizeArray.xyz",
            "framePositionExpression": (
                "transformPosition[transformIndex] + double3("
                "math.rotate(transformRotation[transformIndex], centerArray[colliderIndex] * "
                "transformScale[transformIndex]))"
            ),
            "frameRotationExpression": "transformRotation[transformIndex]",
            "frameScaleExpression": "transformScale[transformIndex]",
        },
    }


def build_contract() -> dict[str, Any]:
    source_files = {
        path.name: _gate(path, size, digest)
        for path, (size, digest) in PINNED_FILES.items()
    }
    native_evidence, _, core = _validate_native()
    owner, dependency_checks = _validate_dependencies()
    colliders = [
        row for row in owner["actors"]["endminf"]["colliders"]
        if row["type"] == "BeyondDynamicBone.BeyondBoneCapsuleCollider"
    ]
    if len(colliders) != 10:
        raise ContractError(f"expected 10 Endminf capsules, got {len(colliders)}")
    rows = [_row(row, index) for index, row in enumerate(colliders)]
    if any(row["serialized"]["alignedOnCenter"] != 1 for row in rows):
        raise ContractError("Endminf unexpectedly contains a one-sided capsule")
    if any(row["managedMapping"]["colliderType"] == 7 for row in rows):
        raise ContractError("Endminf unexpectedly constructs ColliderType 7")
    return {
        "schema": "endfield.charinfo.secondary-dynamics-endminf-collider-inputs-v1",
        "status": "endminf_managed_collider_input_mapping_closed",
        "sourceFiles": source_files,
        "nativeEvidence": native_evidence,
        "colliderStartCore": core,
        "dependencyChecks": dependency_checks,
        "managedConstruction": {
            "fieldOffsets": {
                "ColliderComponent.center": "0x20", "ColliderComponent.size": "0x2c",
                "BeyondBoneCapsuleCollider.direction": "0x40",
                "BeyondBoneCapsuleCollider.reverseDirection": "0x44",
                "BeyondBoneCapsuleCollider.radiusSeparation": "0x45",
                "BeyondBoneCapsuleCollider.alignedOnCenter": "0x46",
            },
            "colliderTypeTable": [
                {"direction": direction, "axis": "xyz"[direction], "alignedOnCenter": aligned,
                 "colliderType": collider_type(direction, aligned),
                 "coreCapsuleBranch": collider_type(direction, aligned) in range(2, 7)}
                for direction in range(3) for aligned in (1, 0)
            ],
            "flagFormula": (
                "GetColliderType() | 0x10(valid) | (isActiveAndEnabled ? 0x20 : 0) | "
                "0x40(reset) | (IsReverseDirection() ? 0x80 : 0)"
            ),
            "sizeFormula": "radiusSeparation ? float3(size.x,size.y,size.z) : float3(size.x,size.x,size.z)",
            "registrationFrameSources": {
                "framePositions": "double3(Component.transform.position)",
                "frameRotations": "quaternion(Component.transform.rotation)",
                "frameScales": "Component.transform.localScale",
                "oldFramePositions": "framePositions", "oldFrameRotations": "frameRotations",
                "nowPositions": "framePositions", "nowRotations": "frameRotations",
                "oldPositions": "framePositions", "oldRotations": "frameRotations",
            },
            "preSimulationPublication": {
                "framePositions": (
                    "transformPosition + double3(math.rotate(transformRotation, center * transformScale))"
                ),
                "frameRotations": "transformRotation",
                "frameScales": "transformScale",
                "resetBranch": (
                    "TeamData.IsReset or flag bit 0x40 copies the published frame position/rotation to "
                    "oldFrame, now, and old arrays, then clears flag bit 0x40 before Collider Start."
                ),
                "ordinaryBranchBoundary": (
                    "The exact non-reset publication is closed. Inertia-shift and negative-scale-teleport "
                    "special branches remain outside this focused Endminf row contract."
                ),
            },
        },
        "endminf": {
            "capsuleCount": len(rows),
            "directionCounts": {"0/x": sum(r["serialized"]["direction"] == 0 for r in rows),
                                "1/y": sum(r["serialized"]["direction"] == 1 for r in rows),
                                "2/z": sum(r["serialized"]["direction"] == 2 for r in rows)},
            "colliderStartFlagCounts": {
                "0x32": sum(r["managedMapping"]["colliderStartFlagAfterPreSimulation"] == "0x32" for r in rows),
                "0x34": sum(r["managedMapping"]["colliderStartFlagAfterPreSimulation"] == "0x34" for r in rows),
            },
            "rows": rows,
        },
        "type7Reconciliation": {
            "managedConstruction": "direction=2 and alignedOnCenter=false returns ColliderType 7",
            "nativeCore": (
                "The pinned core's outer capsule range admits low-nibble types 2..7, but its jump table "
                "contains entries only for 2..6; type 7 falls through the zero-work path."
            ),
            "endminfImpact": (
                "none: all 10 Endminf capsules serialize alignedOnCenter=1, producing nine type-2 X "
                "capsules and one type-4 Z capsule"
            ),
            "runtimeBoundary": (
                "Type 7 remains fail-closed for a general runtime port; this contract does not relabel it "
                "as supported merely because managed construction can emit it."
            ),
        },
        "boundary": [
            "This is a static, hash-pinned transcription of the installed unpatched BeyondDynamicBone path.",
            "Live bone transform values are animation-frame inputs; the exact managed source arrays and equations are closed, not numeric values for every video frame.",
            "No Unity runtime, data builder, solver, kernel, verifier, or transform writeback file is modified or enabled by this contract.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_contract()
        serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
            print(json.dumps({"status": payload["status"], "matches": matches,
                              "capsules": payload["endminf"]["capsuleCount"]}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(f"wrote {args.output}")
        return 0
    except (ContractError, KeyError, OSError, ValueError) as exc:
        print(json.dumps({"status": "failed_closed", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
