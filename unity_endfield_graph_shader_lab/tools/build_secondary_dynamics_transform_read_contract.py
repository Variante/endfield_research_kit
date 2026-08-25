#!/usr/bin/env python3
"""Build the pinned Endminf transform-read/input-publication contract.

The contract is deliberately data/evidence only.  It records the 126 ordered
BoneCloth transform bindings, the DynamicBoneTransformManager read lifecycle,
and the exact structural route into proxy ``positions``/``rotations`` consumed
as Simulation Start base inputs.  It does not install a runtime hook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DATA_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_PAYLOAD = DATA_ROOT / "secondary_dynamics_payload_decode.json"
DEFAULT_WRITEBACK = DATA_ROOT / "secondary_dynamics_transform_writeback_contract.json"
DEFAULT_CALLBACK = DATA_ROOT / "secondary_dynamics_callback_contract.json"
DEFAULT_SCHEDULE = DATA_ROOT / "secondary_dynamics_schedule_contract.json"
DEFAULT_OUTPUT = DATA_ROOT / "secondary_dynamics_transform_read_contract.json"

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_INPUTS = {
    "payload": (1161329, "3e1841d21c8e249b505ca74379632b8ab308a1ffedc166130206a9f706737e35"),
    "writeback": (89645, "276db9e3faf37f8f36624358558d4d89db709825d1772409fb9a3aaabda0573c"),
    "callback": (17561, "a6143a667a6df88f088201fe314522589f9faf5149ed2f20a1dc581cf3f27f65"),
    "schedule": (14618, "d442c5ee85e85e863923a13af5b1caf6bb696c8f4e3ecb554a47d9991357288e"),
}

# File-offset spans are independently checked against the gated image.  The
# selected spans end at the first RET except where the complete mapped method
# span is intentionally retained.
NATIVE_SPANS = (
    ("DynamicBoneTransformManager.AddTransform(Transform,flag,teamId)", 384488, "0x186724e0c", 0x672340C, 1387, "01d4bcf101841d3489809e29f1d999d8beb3d933e279902d45e90318bc3ee6b1"),
    ("DynamicBoneTransformManager.EnableTransform(index,sw)", 384493, "0x1833a8d60", 0x33A7360, 125, "c2b342a3240bc5fcc41e4f611a79348cccd4c082f332dae18eeaed59222d7ae9"),
    ("DynamicBoneTransformManager.CopyDoubleBufferJob.Execute", 384534, "0x186724ce8", 0x67232E8, 289, "8496b8577097b6a3f91c592da353c521af4c0b8f50075571e13b794352bbbbd9"),
    ("DynamicBoneTransformManager.ReadTransformJob.Execute", 384537, "0x186727248", 0x6725848, 1734, "96309abe74a2726bd30e849cb6571f0b2867f655fcb847a61ae634b610e323bf"),
    ("VirtualMeshManager.PreProxyMeshUpdate", 384784, "0x182f8b170", 0x2F89770, 2864, "6bd765d1933f0ffe83f08e6fa6c24da1ec89900f5ae688cec8c24d628b14aae0"),
    ("VirtualMeshManager.CalcProxyMeshSkinningJob.Execute(index)", 385042, "0x186747cec", 0x67462EC, 1760, "23a1856ddf09c6ff6e71af8d07b983e76af5a7ddf9ff32a7ba042f46341cee33"),
)

OWNER_ORDER = ("MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat")
FLAG_BY_ATTRIBUTE = {0: 0x01, 1: 0x0B, 2: 0x0D}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _load_pinned(label: str, path: Path) -> tuple[Any, dict[str, Any]]:
    expected_size, expected_hash = EXPECTED_INPUTS[label]
    if not path.is_file():
        raise ContractError(f"missing {label}: {path}")
    actual = (path.stat().st_size, _sha(path))
    if actual != (expected_size, expected_hash):
        raise ContractError(f"{label} drift: {actual} != {(expected_size, expected_hash)}")
    return json.loads(path.read_text(encoding="utf-8")), {
        "repoPath": _repo_path(path), "size": actual[0], "sha256": actual[1]
    }


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> tuple[Path, dict[str, Any]]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not gate.validated:
        raise ContractError(f"native gate [{gate.status}]: {gate.detail}")
    ga = Path(gate.gameassembly)
    return ga, {
        "status": gate.status,
        "gameAssembly": {"path": _repo_path(ga), "size": ga.stat().st_size, "sha256": gate.gameassembly_sha256},
        "globalMetadata": {"path": _repo_path(Path(gate.metadata)), "size": Path(gate.metadata).stat().st_size, "sha256": gate.metadata_sha256},
    }


def _pin_native_spans(game_assembly: Path) -> list[dict[str, Any]]:
    image = game_assembly.read_bytes()
    rows = []
    for name, method_index, va, offset, size, expected in NATIVE_SPANS:
        digest = hashlib.sha256(image[offset:offset + size]).hexdigest()
        if digest != expected:
            raise ContractError(f"native span drift for {name}: {digest}")
        rows.append({"name": name, "methodIndex": method_index, "va": va,
                     "fileOffset": f"0x{offset:x}", "bytes": size, "sha256": digest})
    return rows


def _decode_weight(raw_hex: str, local_index: int) -> None:
    raw = bytes.fromhex(raw_hex)
    if len(raw) != 32:
        raise ContractError(f"bone weight byte size drift at {local_index}")
    weights = struct.unpack_from("<4f", raw, 0)
    indices = struct.unpack_from("<4i", raw, 16)
    if weights != (1.0, 0.0, 0.0, 0.0) or indices[0] != local_index:
        raise ContractError(f"non-identity one-bone binding at {local_index}: {weights} {indices}")


def _build_entries(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actor = payload["actors"]["endminf"]
    owners = {row["game_object_path"]: row for row in actor["cloths"]}
    if tuple(owners) != OWNER_ORDER:
        raise ContractError(f"owner order drift: {tuple(owners)}")
    entries: list[dict[str, Any]] = []
    summaries = []
    for owner_name in OWNER_ORDER:
        owner = owners[owner_name]
        arrays = owner["proxy_mesh_arrays"]
        refs = arrays["referenceIndices"]["values"]
        attrs = arrays["attributes"]["values"]
        transform_entries = owner["transform_array"]["entries"]
        source_flags = arrays["transformData"]["flagArray"]["values"]
        skin_indices = arrays["skinBoneTransformIndices"]["values"]
        weights = arrays["boneWeights"]["values"]
        count = len(refs)
        if not (count == len(attrs) == len(skin_indices) == len(weights)):
            raise ContractError(f"proxy cardinality drift for {owner_name}")
        if len(transform_entries) != count + 1 or len(source_flags) != count + 1:
            raise ContractError(f"owner-root exclusion drift for {owner_name}")
        if refs != list(range(count)) or skin_indices != list(range(count)):
            raise ContractError(f"identity transform mapping drift for {owner_name}")
        owner_start = len(entries)
        for local_index, (attribute, flag) in enumerate(zip(attrs, source_flags[:count])):
            if FLAG_BY_ATTRIBUTE.get(attribute) != flag:
                raise ContractError(f"attribute/flag drift for {owner_name}[{local_index}]: {attribute}/{flag}")
            _decode_weight(weights[local_index], local_index)
            transform = transform_entries[local_index]
            entries.append({
                "orderedIndex": len(entries),
                "managerIndex": len(entries),
                "owner": owner_name,
                "ownerLocalIndex": local_index,
                "proxyVertexIndexWithinOwner": local_index,
                "referenceIndex": refs[local_index],
                "transformPathId": transform["m_PathID"],
                "hierarchyPath": transform["hierarchy_path"],
                "attribute": attribute,
                "sourceFlag": flag,
                "sourceFlagHex": f"0x{flag:02x}",
                "activeManagerFlag": flag | 0x10,
                "activeManagerFlagHex": f"0x{flag | 0x10:02x}",
                "readChannels": ["worldPosition", "worldRotation", "localPosition", "localRotation", "lossyScale", "localToWorldMatrix"],
                "baseInput": {"position": "proxy.positions[proxyVertex]", "rotation": "proxy.rotations[proxyVertex]"},
            })
        counts = Counter(attrs)
        summaries.append({
            "owner": owner_name, "orderedStart": owner_start, "bindingCount": count,
            "serializedTransformCountIncludingOwnerRoot": len(transform_entries),
            "excludedOwnerRoot": transform_entries[-1]["hierarchy_path"],
            "attributeCounts": {str(key): counts[key] for key in sorted(counts)},
            "sourceFlagCounts": {f"0x{FLAG_BY_ATTRIBUTE[key]:02x}": counts[key] for key in sorted(counts)},
        })
    if len(entries) != 126:
        raise ContractError(f"Endminf ordered binding count drift: {len(entries)}")
    return entries, summaries


def _duplicates(entries: list[dict[str, Any]]) -> dict[str, Any]:
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in entries:
        by_path[row["hierarchyPath"]].append(row)
    groups = []
    for path, rows in by_path.items():
        if len(rows) > 1:
            groups.append({"hierarchyPath": path, "orderedIndices": [x["orderedIndex"] for x in rows],
                           "owners": [x["owner"] for x in rows], "attributes": [x["attribute"] for x in rows],
                           "sourceFlags": [x["sourceFlagHex"] for x in rows]})
    groups.sort(key=lambda row: row["orderedIndices"])
    return {"bindingEntries": len(entries), "uniqueTransforms": len(by_path),
            "duplicateEntries": len(entries) - len(by_path), "duplicatePathCount": len(groups),
            "preservedAsDistinctManagerEntries": True, "groups": groups}


def build_contract(*, game_assembly: Path | None = None, metadata: Path | None = None,
                   payload_path: Path = DEFAULT_PAYLOAD, writeback_path: Path = DEFAULT_WRITEBACK,
                   callback_path: Path = DEFAULT_CALLBACK, schedule_path: Path = DEFAULT_SCHEDULE) -> dict[str, Any]:
    ga, native_gate = _native_gate(game_assembly, metadata)
    payload, payload_source = _load_pinned("payload", payload_path)
    writeback, writeback_source = _load_pinned("writeback", writeback_path)
    callback, callback_source = _load_pinned("callback", callback_path)
    schedule, schedule_source = _load_pinned("schedule", schedule_path)
    if writeback["writeback"]["endminfBindingBoundary"]["bindingEntries"] != 126:
        raise ContractError("writeback binding boundary drift")
    critical = [(row["offset"], row["method"]) for row in callback["writeback"]["criticalCalls"]]
    required = [(1191, "ReadTransform"), (1232, "WriteDoubleBufferTransform"),
                (1883, "ReadTransform"), (1930, "PreProxyMeshUpdate"),
                (2160, "SimulationStepUpdate")]
    if any(row not in critical for row in required):
        raise ContractError("callback read/pre-proxy order drift")
    if schedule["status"] != "unpatched_schedule_and_transform_access_writeback_closed":
        raise ContractError("schedule contract status drift")
    entries, owner_summaries = _build_entries(payload)
    duplicates = _duplicates(entries)
    if (duplicates["uniqueTransforms"], duplicates["duplicateEntries"]) != (100, 26):
        raise ContractError("Endminf duplicate census drift")
    return {
        "schema": "endfield.charinfo.secondary-dynamics-transform-read.v1",
        "status": "endminf_transform_read_and_base_input_publication_closed_with_relative_route_boundary",
        "nativeGate": native_gate,
        "sources": {"payload": payload_source, "transformWriteback": writeback_source,
                    "callback": callback_source, "schedule": schedule_source},
        "native": {"pinnedSpans": _pin_native_spans(ga), "ifix": {
            "readTransformJobPatchId": "0x34e", "route": "unpatched native body only",
            "patchedRouteRecovered": False}},
        "flags": {
            "bits": {"0x01": "read", "0x02": "world rotation write", "0x04": "local position/rotation write",
                     "0x08": "restore", "0x10": "enable"},
            "attributeToSourceFlag": {"0": "0x01", "1": "0x0b", "2": "0x0d"},
            "activeEquation": "activeManagerFlag = sourceFlag | 0x10; disabling clears only 0x10",
            "readSelection": "all attributes carry 0x01; attribute does not select world versus local input reads",
        },
        "endminf": {"ownerOrder": list(OWNER_ORDER), "owners": owner_summaries,
                    "orderedEntries": entries, "duplicates": duplicates},
        "managerLifecycle": {
            "addTransformInitialization": {
                "flagArray[i]": "sourceFlag",
                "initLocalPositionArray[i]": "float3(transform.localPosition)",
                "initLocalRotationArray[i]": "quaternion(transform.localRotation)",
                "positionArray[i]": "lastpositionArray[i] = double3(transform.position)",
                "rotationArray[i]": "lastrotationArray[i] = quaternion(transform.rotation)",
                "scaleArray[i]": "float3(transform.lossyScale)",
                "localPositionArray[i]": "lastlocalPositionArray[i] = float3(transform.localPosition)",
                "localRotationArray[i]": "lastlocalRotationArray[i] = quaternion(transform.localRotation)",
                "localToWorldMatrixArray[i]": "float4x4(transform.localToWorldMatrix)",
                "teamIdArray[i]": "(short)teamId",
                "transformAccessArray[i]": "the same Transform; duplicate paths remain separate entries",
            },
            "copyDoubleBufferJob": [
                "lastpositionArray = copy(positionArray)", "lastrotationArray = copy(rotationArray)",
                "lastlocalPositionArray = copy(localPositionArray)", "lastlocalRotationArray = copy(localRotationArray)"],
            "readTransformJobGates": ["TransformAccess is valid", "(flag & 0x10) != 0", "(flag & 0x01) != 0",
                                      "team is not culling-invisible", "team is not LOD-culled"],
            "readTransformJobActiveWrites": {
                "sampledForEveryAttribute": ["transform.position", "transform.rotation", "transform.localToWorldMatrix",
                                              "transform.localPosition", "transform.localRotation"],
                "localPositionArray[i]": "float3(transform.localPosition)",
                "localRotationArray[i]": "quaternion(transform.localRotation)",
                "scaleArray[i]": "scale extracted from transform.localToWorldMatrix",
                "localToWorldMatrixArray[i]": "float4x4(transform.localToWorldMatrix), or its relative-space form when TeamData.useRelativeTransform > 0",
                "positionArray[i]": "double3(transform.position) when useRelativeTransform == 0; relative-space transformed position otherwise",
                "rotationArray[i]": "quaternion(transform.rotation) when useRelativeTransform == 0; relative-space transformed rotation otherwise",
                "lastArrays": "not written by ReadTransformJob",
            },
            "perFrameOrdering": ["ReadTransform call site 1191", "WriteDoubleBufferTransform call site 1232",
                                 "optional animator-buffer read", "ReadTransform call site 1883",
                                 "PreProxyMeshUpdate", "SimulationStepUpdate"],
            "orderingBoundary": "The two ReadTransform call sites and intervening WriteDoubleBufferTransform are exact. Static evidence does not select the Endminf animator branch or prove a per-frame caller of public CopyDoubleBuffer; its exact copy equation is retained without inventing a call site.",
        },
        "baseInputPublication": {
            "managerInput": "ReadTransformJob localToWorldMatrixArray for every active 0/1/2 attribute",
            "preProxyJob": "VirtualMeshManager.CalcProxyMeshSkinningJob",
            "endminfOneBoneReduction": [
                "referenceIndices[v] == v and skinBoneTransformIndices[v] == v for all 126 owner-local vertices",
                "boneWeights[v] has weight0=1, weights1..3=0, and boneIndex0=v",
                "skinningMatrix[v] = transformLocalToWorldMatrixArray[managerIndex(v)] * skinBoneBindPoses[v]",
                "proxy.positions[v] = double3(mul(skinningMatrix[v], float4(localPositions[v], 1)).xyz)",
                "proxy.rotations[v] is reconstructed from localNormals/localTangents transformed by the same one-bone skinningMatrix",
            ],
            "simulationStartMapping": {
                "authoredPosition": "proxy.positions[ownerProxyChunk.start + ownerLocalIndex]",
                "authoredRotation": "proxy.rotations[ownerProxyChunk.start + ownerLocalIndex]",
                "basePosition": "lerp(oldPosition, authoredPosition, frameInterpolation)",
                "baseRotation": "shortest-arc slerp(oldRotation, authoredRotation, frameInterpolation)",
            },
            "localChannelRole": "localPosition/localRotation are captured for restore/local writeback; they do not directly feed Endminf proxy basePosition/baseRotation",
        },
        "executionBoundary": {
            "orderedSourceFlagsClosed": True, "allSixTransformReadChannelsClosed": True,
            "managerInitializationClosed": True, "copyDoubleBufferEquationsClosed": True,
            "readTransformCurrentArrayEquationsClosed": True, "endminfOneBoneProxyMappingClosed": True,
            "duplicateEntryMappingClosed": True,
            "targetReady": False,
            "targetReadySubset": "the active, unpatched, non-relative owner-solver input route is complete when actual Unity Transform samples and exact team state are supplied",
            "unresolved": [
                "live Endminf TeamData.useRelativeTransform value and the general relative-space numeric branch",
                "which conditional ClothUpdate ReadTransform/animator-buffer branch executes for the target session",
                "a concrete per-frame call site for public CopyDoubleBuffer",
                "IFix-patched ReadTransformJob execution",
                "duplicate transform write winner (read entries themselves remain exact and distinct)",
            ],
            "unityRuntimeModified": False, "runtimeHookInstalled": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        contract = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
    except ContractError as exc:
        print(f"transform-read contract unavailable: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != text:
            print(f"generated contract differs: {args.output}", file=sys.stderr)
            return 1
        print(f"generated contract matches: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
