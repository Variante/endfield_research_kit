#!/usr/bin/env python3
"""Build a fail-closed BeyondDynamicBone transform writeback contract.

This contract records the exact post-solver world/local publication equations,
their manager-array provenance and schedule, and the final
``DynamicBoneTransformManager.WriteTransformJob`` branches proved from the
pinned IL2CPP metadata and GameAssembly image.  Endminf duplicate transform
bindings remain deliberately unresolved because the original job contains no
static owner-priority rule.

The native evidence files are ignored, build-local artifacts.  A clean
checkout without them is deliberately unavailable and fails closed.  The
installed ``GameAssembly.dll`` and ``global-metadata.dat`` are checked through
the repository's explicit two-file gate before any claim is published.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/secondary_dynamics_owner"

DEFAULT_NATIVE = EVIDENCE_ROOT / "transform_writeback_native.json"
DEFAULT_METADATA_CATALOG = EVIDENCE_ROOT / "transform_writeback_metadata.json"
DEFAULT_DUMMY_GENERATION = REPO_ROOT / "tools/DummyDll/generation.json"
DEFAULT_PAYLOAD_DECODE = SOURCE_ROOT / "secondary_dynamics_payload_decode.json"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_transform_writeback_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = "0x18b9217d0"
EXPECTED_BONE_ASSEMBLY_SHA256 = "025c209c7f0b9ee927891421c74b42bdd16ff224f16f9c189f9f7d6ad1a3182c"
EXPECTED_PAYLOAD_DECODE_SHA256 = "3e1841d21c8e249b505ca74379632b8ab308a1ffedc166130206a9f706737e35"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the pinned native or metadata evidence drifts."""


MANAGER = "BeyondDynamicBone.DynamicBoneTransformManager"
READ_ANIMATOR_JOB = f"{MANAGER}+ReadAnimatorBufferDataJob"
WRITE_ANIMATOR_JOB = f"{MANAGER}+WriteAnimatorBufferDataJob"
READ_JOB = f"{MANAGER}+ReadTransformJob"
RESTORE_JOB = f"{MANAGER}+RestoreTransformJob"
WRITE_JOB = f"{MANAGER}+WriteTransformJob"
READ_COMPONENT_JOB = f"{MANAGER}+ReadComponentTransformJob"
VIRTUAL_WRITE_JOB = "BeyondDynamicBone.VirtualMeshManager+WriteTransformDataJob"
VIRTUAL_LOCAL_WRITE_JOB = "BeyondDynamicBone.VirtualMeshManager+WriteTransformLocalDataJob"
VIRTUAL_WRITE_KERNELS = "BeyondDynamicBone.VirtualMeshManager+WriteTransformDataJobKernels"
VIRTUAL_LOCAL_WRITE_KERNELS = "BeyondDynamicBone.VirtualMeshManager+WriteTransformLocalDataJobKernels"
ANIMATOR_WRITE_KERNELS = f"{MANAGER}+WriteAnimatorBufferDataJobKernels"

CONTRACT_STATUS = "transform_writeback_contract_closed_with_duplicate_boundary"

# Exact spans transcribed during the completed publication/writeback
# investigation. These are independently re-hashed from the gated image on
# every build, rather than accepted as narrative evidence.
PINNED_NATIVE_SPANS: tuple[dict[str, Any], ...] = (
    {"name": "WriteTransformDataKernel", "va": "0x186754520", "fileOffset": "0x6752b20", "bytes": 180, "sha256": "4331bae2a6a6f86a6f36f1c928d1c801e51a03a81a5a62a615e5521be92f6ce8"},
    {"name": "WriteTransformDataRangeKernel", "va": "0x186754680", "fileOffset": "0x6752c80", "bytes": 184, "sha256": "e2cdc75fd27b63f2ac803c80ba94b48a7114c8bec4982f96664b24b86d10c923"},
    {"name": "WriteTransformLocalDataKernel", "va": "0x1867555e8", "fileOffset": "0x6753be8", "bytes": 208, "sha256": "f7c329ea399f191c7c4f5be5bc11ff3b52c3c9592c2d7aeef0e51ad9137ca115"},
    {"name": "WriteTransformLocalDataRangeKernel", "va": "0x186755784", "fileOffset": "0x6753d84", "bytes": 208, "sha256": "b3798e37d293ce37ebc5460db6ce424e40f217ce617057ae96421f3c69a05d9e"},
    {"name": "WriteTransformJob.Execute.hot", "va": "0x18672e7e0", "fileOffset": "0x672cde0", "bytes": 2003, "sha256": "be8906f5f1bbca55200b7941031e56cb8e0a260054cc7a892ba056c2644dd91e"},
)


# Route-independent GameAssembly worker boundaries for observation-only stage
# telemetry.  Each entry is reached before the BurstDirectCall wrapper chooses
# its runtime function pointer or managed fallback, so a capture observer does
# not need to guess a lib_burst_generated.dll export or CPU variant.  The
# selected Burst route remains explicitly unresolved below.
STAGE_OBSERVER_METHOD_SPECS: dict[int, dict[str, Any]] = {
    385713: {
        "type": "BeyondDynamicBone.SimulationManager+CalcDisplayPositionJob",
        "method": "UnsafeDo",
        "role": "calc_display_worker",
        "va": "0x18676b3c4",
        "fileOffset": "0x67699c4",
        "bytes": 368,
        "sha256": "f87adbb7832b3946c707e34684602cbc77dcaef3d46bb93b2eba792a26446817",
    },
    385650: {
        "type": "BeyondDynamicBone.SimulationManager+CalcDisplayPositionJobKernels",
        "method": "CalcDisplayPositionRangeKernel",
        "role": "calc_display_route_independent_dispatcher",
        "va": "0x18676accc",
        "fileOffset": "0x67692cc",
        "bytes": 240,
        "sha256": "0c269791256da59e5e178d55df90241dd95d9e7af2776f6276aef02b00b6ef6a",
    },
    385672: {
        "type": "BeyondDynamicBone.SimulationManager+CalcDisplayPositionJobKernels+CalcDisplayPositionRangeKernel_00000411$BurstDirectCall",
        "method": "Invoke",
        "role": "calc_display_burst_directcall",
        "va": "0x18676bbf8",
        "fileOffset": "0x676a1f8",
        "bytes": 428,
        "sha256": "81486ab95a6b2f028640fb77dddd7ce15f391ddec07607a7377d214370c56094",
    },
    385063: {
        "type": VIRTUAL_WRITE_JOB,
        "method": "UnsafeDo",
        "role": "post_proxy_world_worker",
        "va": "0x186754b30",
        "fileOffset": "0x6753130",
        "bytes": 280,
        "sha256": "7b1212e8ed5eda8f98c63d49a09dca1c4f2254a67eac7136e5f0e59fd927bad3",
    },
    384879: {
        "type": VIRTUAL_WRITE_KERNELS,
        "method": "WriteTransformDataRangeKernel",
        "role": "post_proxy_world_route_independent_dispatcher",
        "va": "0x186754680",
        "fileOffset": "0x6752c80",
        "bytes": 184,
        "sha256": "e2cdc75fd27b63f2ac803c80ba94b48a7114c8bec4982f96664b24b86d10c923",
    },
    384901: {
        "type": "BeyondDynamicBone.VirtualMeshManager+WriteTransformDataJobKernels+WriteTransformDataRangeKernel_000002ED$BurstDirectCall",
        "method": "Invoke",
        "role": "post_proxy_world_burst_directcall",
        "va": "0x1867550e4",
        "fileOffset": "0x67536e4",
        "bytes": 340,
        "sha256": "7e15e27032cea2ab2ac74f248af07a56f502027d0e05370d206aa41b0c4abfe7",
    },
    385067: {
        "type": VIRTUAL_LOCAL_WRITE_JOB,
        "method": "UnsafeDo",
        "role": "post_proxy_local_worker",
        "va": "0x186755ca8",
        "fileOffset": "0x67542a8",
        "bytes": 356,
        "sha256": "a060e53d3a5bb005cdeae8e597bb7e9bfc2176ddad93070d225578b904e298fd",
    },
    384903: {
        "type": VIRTUAL_LOCAL_WRITE_KERNELS,
        "method": "WriteTransformLocalDataRangeKernel",
        "role": "post_proxy_local_route_independent_dispatcher",
        "va": "0x186755784",
        "fileOffset": "0x6753d84",
        "bytes": 208,
        "sha256": "b3798e37d293ce37ebc5460db6ce424e40f217ce617057ae96421f3c69a05d9e",
    },
    384925: {
        "type": "BeyondDynamicBone.VirtualMeshManager+WriteTransformLocalDataJobKernels+WriteTransformLocalDataRangeKernel_000002EF$BurstDirectCall",
        "method": "Invoke",
        "role": "post_proxy_local_burst_directcall",
        "va": "0x1867563d0",
        "fileOffset": "0x67549d0",
        "bytes": 400,
        "sha256": "6ab6d3fe1ebeb9e74eefd7233fdeda8dda0a339f3843425f605154f56757fb4d",
    },
}

STAGE_OBSERVER_CHAINS: tuple[dict[str, Any], ...] = (
    {
        "stage": "CalcDisplayPosition",
        "worker": 385713,
        "dispatcher": 385650,
        "directCall": 385672,
        "workerCallOffset": 286,
        "dispatcherCallOffset": 208,
        "indirectCall": {"offset": 260, "instructionBytes": "41 ff d2", "operand": "r10"},
        "managedFallback": {
            "type": "BeyondDynamicBone.SimulationManager+CalcDisplayPositionJobKernels",
            "method": "CalcDisplayPositionRangeKernel$BurstManaged",
            "methodIndex": 385652,
            "va": "0x1867640f8",
            "callOffset": 395,
        },
    },
    {
        "stage": "PostProxyMeshUpdate.WriteTransformData",
        "worker": 385063,
        "dispatcher": 384879,
        "directCall": 384901,
        "workerCallOffset": 211,
        "dispatcherCallOffset": 155,
        "indirectCall": {"offset": 204, "instructionBytes": "ff d0", "operand": "rax"},
        "managedFallback": {
            "type": VIRTUAL_WRITE_KERNELS,
            "method": "WriteTransformDataKernel",
            "methodIndex": 384878,
            "va": "0x186754520",
            "callOffset": 298,
        },
    },
    {
        "stage": "PostProxyMeshUpdate.WriteTransformLocalData",
        "worker": 385067,
        "dispatcher": 384903,
        "directCall": 384925,
        "workerCallOffset": 272,
        "dispatcherCallOffset": 181,
        "indirectCall": {"offset": 237, "instructionBytes": "41 ff d2", "operand": "r10"},
        "managedFallback": {
            "type": VIRTUAL_LOCAL_WRITE_KERNELS,
            "method": "WriteTransformLocalDataKernel",
            "methodIndex": 384902,
            "va": "0x1867555e8",
            "callOffset": 358,
        },
    },
)


# Metadata method identities required by this contract.  The index disambiguates
# overloaded Execute/AddTransform methods and is checked against the catalog.
METHODS: tuple[tuple[str, int], ...] = (
    (MANAGER, 384477),  # WriteAnimatorBufferData
    (MANAGER, 384478),  # ReadAnimatorBufferData
    (MANAGER, 384479),  # CopyDoubleBuffer
    (MANAGER, 384480),  # WriteDoubleBufferTransform
    (MANAGER, 384481),  # get_Count
    (MANAGER, 384482),  # Dispose
    (MANAGER, 384484),  # Initialize
    (MANAGER, 384486),  # AddTransform(VirtualMeshContainer,int)
    (MANAGER, 384487),  # AddTransform(int,int)
    (MANAGER, 384488),  # AddTransform(Transform,...)
    (MANAGER, 384494),  # Expand
    (MANAGER, 384495),  # RestoreTransform
    (MANAGER, 384496),  # ReadTransform
    (MANAGER, 384497),  # WriteTransform
    (MANAGER, 384498),  # ValidPosition
    (MANAGER, 384499),  # AddComponentTransform
    (MANAGER, 384501),  # ReadComponentTransform
    (READ_ANIMATOR_JOB, 384530),
    (READ_ANIMATOR_JOB, 384531),
    (WRITE_ANIMATOR_JOB, 384532),
    (WRITE_ANIMATOR_JOB, 384533),
    (READ_JOB, 384537),
    (RESTORE_JOB, 384536),
    (WRITE_JOB, 384566),
    (READ_COMPONENT_JOB, 384567),
    (VIRTUAL_WRITE_JOB, 385060),
    (VIRTUAL_WRITE_JOB, 385061),
    (VIRTUAL_WRITE_JOB, 385062),
    (VIRTUAL_WRITE_JOB, 385063),
    (VIRTUAL_LOCAL_WRITE_JOB, 385064),
    (VIRTUAL_LOCAL_WRITE_JOB, 385065),
    (VIRTUAL_LOCAL_WRITE_JOB, 385066),
    (VIRTUAL_LOCAL_WRITE_JOB, 385067),
)

FIELD_SHAPES: dict[str, tuple[str, ...]] = {
    MANAGER: (
        "flagArray", "initLocalPositionArray", "initLocalRotationArray",
        "positionArray", "lastpositionArray", "rotationArray",
        "lastrotationArray", "scaleArray", "localPositionArray",
        "lastlocalPositionArray", "localRotationArray",
        "lastlocalRotationArray", "localToWorldMatrixArray", "teamIdArray",
        "transformAccessArray", "animatorTransformMap", "componentPositionArray",
        "componentTransformAccessArray", "isValid",
    ),
    READ_ANIMATOR_JOB: (
        "flagList", "positionArray", "rotationArray", "scaleList",
        "localPositionArray", "localRotationArray", "localToWorldMatrixArray",
        "teamId2AnimatorInstanceId", "animatorID2RWHandler",
        "transformID2RWHandlerID", "teamIdArray", "teamDataArray",
    ),
    WRITE_ANIMATOR_JOB: (
        "flagList", "positionArray", "rotationArray", "localPositionArray",
        "localRotationArray", "teamId2AnimatorInstanceId", "animatorID2RWHandler",
        "transformID2RWHandlerID", "teamIdArray", "teamDataArray",
    ),
    READ_JOB: (
        "flagList", "positionArray", "rotationArray", "scaleList",
        "localPositionArray", "localRotationArray", "localToWorldMatrixArray",
        "teamIdArray", "teamDataArray",
    ),
    RESTORE_JOB: ("flagList", "localPositionArray", "localRotationArray", "teamIdArray", "teamDataArray"),
    WRITE_JOB: (
        "flagList", "lastpositionArray", "lastrotationArray",
        "lastlocalPositionArray", "lastlocalRotationArray", "teamIdArray", "teamDataArray",
    ),
    READ_COMPONENT_JOB: ("positionArray",),
}


def _call(
    offset: int,
    target: str,
    type_name: str,
    method: str,
    role: str,
    *,
    registers: dict[str, str] | None = None,
) -> tuple[int, str, str, str, str, dict[str, str] | None]:
    return offset, target, type_name, method, role, registers


# Exact native bridge edges.  These are intentionally named calls rather than
# a guessed disassembly of every load/store in a Burst body.
CALL_SPECS: dict[int, tuple[tuple[int, str, str, str, str, dict[str, str] | None], ...]] = {
    384484: (
        _call(1055, "0x1846d6af0", "UnityEngine.Jobs.TransformAccessArray", "Create", "array_create"),
        _call(1146, "0x1846d6af0", "UnityEngine.Jobs.TransformAccessArray", "Create", "array_create"),
    ),
    384482: (
        _call(512, "0x1847de1e0", "UnityEngine.Jobs.TransformAccessArray", "DestroyTransformAccessArray", "array_destroy"),
        _call(558, "0x1847de1e0", "UnityEngine.Jobs.TransformAccessArray", "DestroyTransformAccessArray", "array_destroy"),
    ),
    384486: (
        _call(609, "0x1845993e0", "UnityEngine.Jobs.TransformAccessArray", "GetLength", "array_length"),
        _call(677, "0x1843320f0", "UnityEngine.Jobs.TransformAccessArray", "Add", "array_add"),
        _call(785, "0x1844716f0", "UnityEngine.Jobs.TransformAccessArray", "SetTransform", "array_set_transform"),
        _call(820, "0x1843320f0", "UnityEngine.Jobs.TransformAccessArray", "Add", "array_add"),
    ),
    384487: (
        _call(476, "0x1845993e0", "UnityEngine.Jobs.TransformAccessArray", "GetLength", "array_length"),
        _call(525, "0x1843320f0", "UnityEngine.Jobs.TransformAccessArray", "Add", "array_add"),
        _call(745, "0x1843320f0", "UnityEngine.Jobs.TransformAccessArray", "Add", "array_add"),
        _call(767, "0x1844716f0", "UnityEngine.Jobs.TransformAccessArray", "SetTransform", "array_set_transform"),
    ),
    384488: (
        _call(1217, "0x185395b28", "UnityEngine.Jobs.TransformAccessArray", "get_length", "array_length"),
        _call(1239, "0x1843320f0", "UnityEngine.Jobs.TransformAccessArray", "Add", "array_add"),
        _call(1254, "0x1844716f0", "UnityEngine.Jobs.TransformAccessArray", "SetTransform", "array_set_transform"),
    ),
    384494: (
        _call(627, "0x185395b28", "UnityEngine.Jobs.TransformAccessArray", "get_length", "array_length"),
        _call(652, "0x1843320f0", "UnityEngine.Jobs.TransformAccessArray", "Add", "array_add"),
        _call(662, "0x185395b28", "UnityEngine.Jobs.TransformAccessArray", "get_length", "array_length"),
        _call(699, "0x185397c4c", "UnityEngine.Jobs.TransformAccessArray", "get_Item", "array_item"),
        _call(720, "0x1844716f0", "UnityEngine.Jobs.TransformAccessArray", "SetTransform", "array_set_transform"),
        _call(740, "0x1844716f0", "UnityEngine.Jobs.TransformAccessArray", "SetTransform", "array_set_transform"),
    ),
    384501: (
        _call(470, "0x1845993e0", "UnityEngine.Jobs.TransformAccessArray", "GetLength", "array_length"),
    ),
    384531: (
        _call(1293, "0x18b3def38", "UnityEngine.Jobs.TransformAccess", "get_position", "transform_read", registers={"rcx": "&[rsp+0x40]", "rdx": "rbx", "r8": "0"}),
        _call(1330, "0x18b3def80", "UnityEngine.Jobs.TransformAccess", "get_rotation", "transform_read", registers={"rcx": "&[rsp+0x60]", "rdx": "rbx", "r8": "0"}),
        _call(1350, "0x18b3deec8", "UnityEngine.Jobs.TransformAccess", "get_localToWorldMatrix", "transform_read", registers={"rcx": "&[rbp-0x20]", "rdx": "rbx", "r8": "0"}),
        _call(1432, "0x18b3dedfc", "UnityEngine.Jobs.TransformAccess", "get_localPosition", "transform_read", registers={"rcx": "&[rsp+0x40]", "rdx": "rbx", "r8": "0"}),
        _call(1509, "0x18b3dee44", "UnityEngine.Jobs.TransformAccess", "get_localRotation", "transform_read", registers={"rcx": "&[rsp+0x60]", "rdx": "rbx", "r8": "0", "xmm0": "[rax]"}),
    ),
    384537: (
        _call(386, "0x18b3def38", "UnityEngine.Jobs.TransformAccess", "get_position", "transform_read", registers={"rcx": "&[rsp+0x50]", "rdx": "rsi", "r8": "0"}),
        _call(423, "0x18b3def80", "UnityEngine.Jobs.TransformAccess", "get_rotation", "transform_read", registers={"rcx": "&[rsp+0x30]", "rdx": "rsi", "r8": "0"}),
        _call(444, "0x18b3deec8", "UnityEngine.Jobs.TransformAccess", "get_localToWorldMatrix", "transform_read", registers={"rcx": "&[rsp+0x60]", "rdx": "rsi", "r8": "0"}),
        _call(527, "0x18b3dedfc", "UnityEngine.Jobs.TransformAccess", "get_localPosition", "transform_read", registers={"rcx": "&[rsp+0x30]", "rdx": "rsi", "r8": "0"}),
        _call(604, "0x18b3dee44", "UnityEngine.Jobs.TransformAccess", "get_localRotation", "transform_read", registers={"rcx": "&[rsp+0x30]", "rdx": "rsi", "r8": "0", "xmm0": "[rax]"}),
    ),
    384536: (
        _call(378, "0x18b3defbc", "UnityEngine.Jobs.TransformAccess", "set_localPosition", "transform_write", registers={"rcx": "rsi", "rdx": "&[rsp+0x30]", "r8": "0", "xmm0": "[rax]"}),
        _call(441, "0x18b3defd0", "UnityEngine.Jobs.TransformAccess", "set_localRotation", "transform_write", registers={"rcx": "rsi", "rdx": "&[rsp+0x40]", "r8": "0", "xmm0": "[rax]"}),
    ),
    384566: (
        _call(420, "0x18b3dedfc", "UnityEngine.Jobs.TransformAccess", "get_localPosition", "transform_read", registers={"rcx": "&[rsp+0x30]", "rdx": "r14", "r8": "0"}),
        _call(664, "0x18b3defbc", "UnityEngine.Jobs.TransformAccess", "set_localPosition", "transform_write", registers={"rcx": "r14", "rdx": "&[rsp+0x60]", "r8": "0", "xmm0": "[rax]"}),
        _call(691, "0x18b3dee44", "UnityEngine.Jobs.TransformAccess", "get_localRotation", "transform_read", registers={"rcx": "&[rsp+0x40]", "rdx": "r14", "r8": "0"}),
        _call(852, "0x18b3defd0", "UnityEngine.Jobs.TransformAccess", "set_localRotation", "transform_write", registers={"rcx": "r14", "rdx": "&[rsp+0x40]", "r8": "0", "xmm0": "[rax]"}),
        _call(935, "0x18b3def80", "UnityEngine.Jobs.TransformAccess", "get_rotation", "transform_read", registers={"rcx": "&[rsp+0x40]", "rdx": "r14", "r8": "0"}),
        _call(1332, "0x18b3df00c", "UnityEngine.Jobs.TransformAccess", "set_rotation", "transform_write", registers={"rcx": "r14", "rdx": "&[rsp+0x40]", "r8": "0", "xmm0": "[rax]"}),
        _call(1384, "0x18b3def38", "UnityEngine.Jobs.TransformAccess", "get_position", "transform_read", registers={"rcx": "&[rsp+0x40]", "rdx": "r14", "r8": "0"}),
        _call(1902, "0x18b3deff8", "UnityEngine.Jobs.TransformAccess", "set_position", "transform_write", registers={"rcx": "r14", "rdx": "&[rsp+0x30]", "r8": "0", "xmm0": "[rax]"}),
    ),
    384567: (
        _call(61, "0x18b3def38", "UnityEngine.Jobs.TransformAccess", "get_position", "transform_read", registers={"rcx": "&[rsp+0x40]", "rdx": "rbx", "r8": "0"}),
    ),
    385063: (
        _call(211, "0x186754680", VIRTUAL_WRITE_KERNELS, "WriteTransformDataRangeKernel", "burst_range_dispatch"),
    ),
    385067: (
        _call(272, "0x186755784", VIRTUAL_LOCAL_WRITE_KERNELS, "WriteTransformLocalDataRangeKernel", "burst_range_dispatch"),
    ),
    384533: (
        _call(319, "0x18672d534", f"{MANAGER}+WriteAnimatorBufferDataJobKernels", "WriteAnimatorBufferDataRangeKernel", "burst_range_dispatch"),
    ),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def file_record(path: Path) -> dict[str, Any]:
    return {"repo_path": _repo_path(path), "size": path.stat().st_size, "sha256": sha256(path)}


def _endminf_duplicate_source_boundary(path: Path = DEFAULT_PAYLOAD_DECODE) -> dict[str, Any]:
    record = file_record(path)
    if record["sha256"] != EXPECTED_PAYLOAD_DECODE_SHA256:
        raise ContractError("secondary-dynamics payload decode hash drift")
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_path: dict[str, list[dict[str, Any]]] = {}
    for cloth in payload["actors"]["endminf"]["cloths"]:
        owner = cloth["game_object_path"]
        transforms = cloth["transform_array"]["entries"][:-1]
        attributes = cloth["proxy_mesh_arrays"]["attributes"]["values"]
        if len(transforms) != len(attributes):
            raise ContractError(f"{owner} transform/attribute cardinality drift")
        for index, (transform, attribute) in enumerate(zip(transforms, attributes)):
            by_path.setdefault(transform["hierarchy_path"], []).append({
                "owner": owner,
                "vertexIndex": index,
                "attribute": int(attribute),
            })
    duplicates = [rows for rows in by_path.values() if len(rows) > 1]
    if len(duplicates) != 26 or any(len(rows) != 2 for rows in duplicates):
        raise ContractError("Endminf duplicate transform source cardinality drift")
    pair_counts: dict[str, int] = {}
    attribute_pair_counts: dict[str, int] = {}
    for rows in duplicates:
        rows.sort(key=lambda row: row["owner"])
        pair = "/".join(row["owner"] for row in rows)
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
        non_coat = next(row for row in rows if row["owner"] != "MC_Coat")
        coat = next(row for row in rows if row["owner"] == "MC_Coat")
        key = f"{non_coat['attribute']}:{coat['attribute']}"
        attribute_pair_counts[key] = attribute_pair_counts.get(key, 0) + 1
    if pair_counts != {"MC_Coat/MC_Ribbon2": 6, "MC_Coat/MC_Ribbon": 20}:
        raise ContractError("Endminf duplicate owner-pair census drift")
    if attribute_pair_counts != {"1:0": 5, "2:0": 19, "0:0": 2}:
        raise ContractError("Endminf duplicate attribute-pair census drift")
    return {
        "source": record,
        "duplicatePathCount": len(duplicates),
        "ownerPairCounts": pair_counts,
        "attributePairCountsNonCoatToCoat": attribute_pair_counts,
        "coatAttributesAllFixedZero": True,
        "nonCoatDynamicVsCoatFixed": 24,
        "bothFixed": 2,
        "interpretation": "source topology distinguishes 24 dynamic Ribbon/Ribbon2 entries from fixed Coat copies, but this does not prove TransformAccess execution order or authorize a winner",
        "boundedCompatibilityCandidate": "prefer a nonzero VertexAttribute over a zero-attribute duplicate; leaves two fixed/fixed duplicates unresolved and is not selected by this contract",
    }


def _validate_pinned_spans(game_assembly: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with game_assembly.open("rb") as stream:
        for expected in PINNED_NATIVE_SPANS:
            stream.seek(int(expected["fileOffset"], 16))
            payload = stream.read(int(expected["bytes"]))
            if len(payload) != int(expected["bytes"]):
                raise ContractError(f"short native span for {expected['name']}")
            actual = hashlib.sha256(payload).hexdigest()
            if actual != expected["sha256"]:
                raise ContractError(f"native span hash drift for {expected['name']}: {actual}")
            records.append(dict(expected))
    return records


def _load_il2cpp_helpers() -> tuple[Any, Any]:
    """Load the maintained PE and metadata parsers as independent witnesses."""
    root = REPO_ROOT / "tools/endfield-il2cpp"
    def load(name: str, path: Path) -> Any:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ContractError(f"unable to load independent parser: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    return load("secondary_writeback_native_parser", root / "map_body_targets_to_gameassembly.py"), load(
        "secondary_writeback_metadata_parser", root / "catalog_option_flow_metadata.py"
    )


def _independent_context(game_assembly: Path, metadata: Path) -> tuple[Any, Any, dict[int, list[dict[str, Any]]], list[int]]:
    native_parser, metadata_parser = _load_il2cpp_helpers()
    pe = native_parser.PeImage(game_assembly)
    md = metadata_parser.Metadata(metadata)
    code_registration = int(EXPECTED_CODE_REGISTRATION, 16)
    modules = native_parser.parse_codegen_modules(pe, code_registration)
    ranges = native_parser.image_method_ranges(md)
    _, method_by_pointer = native_parser.build_pointer_indexes(pe, md, modules, ranges)
    pointers = sorted(method_by_pointer)
    if not pointers:
        raise ContractError("independent method-pointer index is empty")
    return pe, md, method_by_pointer, pointers


def _metadata_identity(md: Any, type_name: str, method_index: int) -> tuple[str, str]:
    if method_index < 0 or method_index >= len(md.methods):
        raise ContractError(f"metadata method index out of range: {method_index}")
    method = md.methods[method_index]
    actual_type = md.type_full_name(md.types[method.declaring_type])
    actual_method = md.string(method.name_index)
    if actual_type != type_name:
        raise ContractError(f"metadata declaring type drift for method {method_index}: {actual_type}")
    return actual_type, actual_method


def _method_pointer(
    method_index: int,
    method_by_pointer: dict[int, list[dict[str, Any]]],
) -> int:
    pointers = [
        pointer
        for pointer, rows in method_by_pointer.items()
        if any(int(row.get("methodIndex", -1)) == method_index for row in rows)
    ]
    if len(pointers) != 1:
        raise ContractError(f"independent method pointer is ambiguous for method index {method_index}")
    return pointers[0]


def _stage_observer_identity(
    method_index: int,
    spec: dict[str, Any],
    pe: Any,
    md: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    pointers: list[int],
) -> dict[str, Any]:
    actual_type, actual_method = _metadata_identity(md, str(spec["type"]), method_index)
    if actual_method != spec["method"]:
        raise ContractError(f"stage observer method name drift for method index {method_index}: {actual_method}")
    pointer = _method_pointer(method_index, method_by_pointer)
    if pointer != int(spec["va"], 16):
        raise ContractError(f"stage observer method pointer drift for method index {method_index}: 0x{pointer:x}")
    file_offset, section, _ = pe.file_offset_for_va(pointer)
    if file_offset is None or section not in {".text", "il2cpp"}:
        raise ContractError(f"stage observer method is not executable for method index {method_index}")
    if file_offset != int(spec["fileOffset"], 16):
        raise ContractError(f"stage observer file offset drift for method index {method_index}: 0x{file_offset:x}")
    next_pointer = next(
        (candidate for candidate in pointers if candidate > pointer and pe.file_offset_for_va(candidate)[1] == section),
        None,
    )
    if next_pointer is None or next_pointer - pointer != int(spec["bytes"]):
        raise ContractError(f"stage observer method span drift for method index {method_index}")
    body = pe.bytes_at_va(pointer, next_pointer - pointer)
    actual_hash = hashlib.sha256(body).hexdigest()
    if actual_hash != spec["sha256"]:
        raise ContractError(f"stage observer method hash drift for method index {method_index}: {actual_hash}")
    return {
        "type": actual_type,
        "method": actual_method,
        "methodIndex": method_index,
        "role": spec["role"],
        "methodPointerVa": f"0x{pointer:x}",
        "fileOffset": f"0x{file_offset:x}",
        "section": section,
        "bytes": len(body),
        "sha256": actual_hash,
        "hashSource": "current metadata method pointer + PE executable section span to next pointer",
    }


def _validate_catalog_against_metadata(catalog: dict[str, Any], md: Any) -> None:
    """Reject catalog self-reported indexes unless raw metadata agrees."""
    for type_name in set(type_name for type_name, _ in METHODS):
        row = _catalog_type(catalog, type_name)
        type_index = int(row.get("index", -1))
        if type_index < 0 or type_index >= len(md.types) or md.type_full_name(md.types[type_index]) != type_name:
            raise ContractError(f"metadata type index drift for {type_name}")
        raw_fields = {field.index: field for field in md.fields_for(md.types[type_index])}
        for field in row.get("fields", []):
            index = int(field.get("index", -1))
            raw = raw_fields.get(index)
            if raw is None or md.string(raw.name_index) != field.get("name") or raw.type_index != int(field.get("typeIndex", -1)):
                raise ContractError(f"metadata field index drift for {type_name}::{field.get('name')}")
        for method in row.get("methods", []):
            index = int(method.get("index", -1))
            if index < 0 or index >= len(md.methods):
                raise ContractError(f"metadata method index drift for {type_name}")
            raw = md.methods[index]
            if raw.declaring_type != type_index or md.string(raw.name_index) != method.get("name"):
                raise ContractError(f"metadata method identity drift for {type_name} index {index}")
            if raw.return_type != int(method.get("returnTypeIndex", -1)):
                raise ContractError(f"metadata return type drift for {type_name} index {index}")
            params = md.parameters_for(raw)
            details = method.get("parameterDetails", [])
            if len(params) != len(details) or any(
                param.type_index != int(detail.get("typeIndex", -1)) or md.string(param.name_index) != detail.get("name")
                for param, detail in zip(params, details)
            ):
                raise ContractError(f"metadata parameter shape drift for {type_name} index {index}")


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not result.validated:
        raise ContractError(f"common.check_installed_native_inputs [{result.status}]: {result.detail}")
    game_path = Path(result.gameassembly)
    metadata_path = Path(result.metadata)
    return {
        "gameAssembly": {"path": game_path.as_posix(), "size": game_path.stat().st_size, "sha256": result.gameassembly_sha256},
        "globalMetadata": {"path": metadata_path.as_posix(), "size": metadata_path.stat().st_size, "sha256": result.metadata_sha256},
    }


def _dummy_record(path: Path, game_assembly: Path, metadata: Path) -> dict[str, Any]:
    generation = load_json(path)
    game = generation.get("game") or {}
    if game.get("gameAssemblySha256") != EXPECTED_GAME_ASSEMBLY_SHA256 or game.get("metadataSha256") != EXPECTED_METADATA_SHA256:
        raise ContractError("DummyDll generation source hash drift")
    if game.get("gameAssemblyBytes") != game_assembly.stat().st_size or game.get("metadataBytes") != metadata.stat().st_size:
        raise ContractError("DummyDll generation source size drift")
    if generation.get("registrations", {}).get("codeRegistration") != EXPECTED_CODE_REGISTRATION:
        raise ContractError("DummyDll generation code registration drift")
    assembly = next((row for row in generation.get("assemblies", {}).get("files", []) if row.get("name") == "BeyondDynamicBone.dll"), None)
    if not assembly or assembly.get("sha256") != EXPECTED_BONE_ASSEMBLY_SHA256:
        raise ContractError("DummyDll generation lacks pinned BeyondDynamicBone.dll")
    return {
        "record": file_record(path),
        "schema": generation.get("schema"),
        "gameAssemblySha256": game.get("gameAssemblySha256"),
        "metadataSha256": game.get("metadataSha256"),
        "codeRegistration": generation["registrations"]["codeRegistration"],
        "BeyondDynamicBone.dll": {"bytes": int(assembly["bytes"]), "sha256": assembly["sha256"]},
        "role": "managed field-shape corroboration only; not implementation evidence",
    }


def _catalog_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("matchedTypes", "memberOnlyTypes"):
        rows = catalog.get(key, [])
        result.extend(rows.values() if isinstance(rows, dict) else rows)
    return result


def _catalog_type(catalog: dict[str, Any], full_name: str) -> dict[str, Any]:
    for row in _catalog_rows(catalog):
        if row.get("fullName") == full_name:
            return row
    raise ContractError(f"metadata catalog missing type: {full_name}")


def _catalog_method(catalog: dict[str, Any], type_name: str, method_index: int) -> dict[str, Any]:
    row = _catalog_type(catalog, type_name)
    for method in row.get("methods", []):
        if int(method.get("index", -1)) == method_index:
            return method
    raise ContractError(f"metadata catalog missing method {type_name} index {method_index}")


def _managed_type(catalog: dict[str, Any], type_name: str) -> dict[str, Any]:
    row = _catalog_type(catalog, type_name)
    fields_by_name = {field.get("name"): field for field in row.get("fields", [])}
    fields: list[dict[str, Any]] = []
    for field_name in FIELD_SHAPES.get(type_name, ()):
        field = fields_by_name.get(field_name)
        if field is None:
            raise ContractError(f"metadata catalog missing field {type_name}::{field_name}")
        fields.append({
            "name": field_name,
            "metadataFieldIndex": int(field["index"]),
            "metadataTypeIndex": int(field["typeIndex"]),
            "metadataTypeName": field.get("typeName"),
        })
    return {
        "metadataTypeIndex": int(row["index"]),
        "fullName": type_name,
        "image": row.get("image"),
        "fields": fields,
    }


def _body(native: dict[str, Any], type_name: str, method_index: int) -> dict[str, Any]:
    for row in native.get("bodyTargets", []):
        if row.get("type") == type_name and int(row.get("methodIndex", -1)) == method_index:
            return row
    raise ContractError(f"native evidence missing body target {type_name} index {method_index}")


def _body_identity(
    native: dict[str, Any],
    type_name: str,
    method_index: int,
    game_assembly: Path,
    pe: Any,
    md: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    pointers: list[int],
) -> dict[str, Any]:
    row = _body(native, type_name, method_index)
    actual_type, actual_method = _metadata_identity(md, type_name, method_index)
    pointer = [ptr for ptr, rows in method_by_pointer.items() if any(int(sig.get("methodIndex", -1)) == method_index for sig in rows)]
    if len(pointer) != 1:
        raise ContractError(f"independent method pointer is ambiguous for {type_name} index {method_index}")
    method_pointer = pointer[0]
    file_offset, section, _ = pe.file_offset_for_va(method_pointer)
    if file_offset is None or section not in {".text", "il2cpp"}:
        raise ContractError(f"method pointer is not executable for {type_name} index {method_index}")
    next_pointer = next((candidate for candidate in pointers if candidate > method_pointer and pe.file_offset_for_va(candidate)[1] == section), None)
    if next_pointer is None or next_pointer <= method_pointer:
        raise ContractError(f"no positive executable span for {type_name} index {method_index}")
    span = next_pointer - method_pointer
    body = pe.bytes_at_va(method_pointer, span)
    if len(body) != span:
        raise ContractError(f"independent native body truncated: {type_name} index {method_index}")
    if row.get("method") != actual_method or str(row.get("methodPointerVa", "")).lower() != f"0x{method_pointer:x}":
        raise ContractError(f"ignored native method identity disagrees with current metadata/registration: {type_name} index {method_index}")
    if int(row.get("scanBytes", 0)) != span or int(str(row.get("fileOffset")), 0) != file_offset:
        raise ContractError(f"ignored native span disagrees with current executable pointer span: {type_name} index {method_index}")
    return {
        "type": type_name,
        "method": actual_method,
        "methodIndex": method_index,
        "methodPointerVa": f"0x{method_pointer:x}",
        "fileOffset": f"0x{file_offset:x}",
        "section": section,
        "bytes": span,
        "sha256": hashlib.sha256(body).hexdigest(),
        "hashSource": "current metadata method pointer + PE executable section span to next pointer",
    }


def _resolved(call: dict[str, Any]) -> set[tuple[str, str]]:
    return {(str(row.get("type")), str(row.get("method"))) for row in call.get("resolved", [])}


def _decoded_calls(
    pe: Any,
    identity: dict[str, Any],
    native_parser: Any | None = None,
) -> dict[int, dict[str, Any]]:
    # Decode directly from the current image; the ignored directCalls list is
    # never consulted.
    if native_parser is None:
        native_parser, _ = _load_il2cpp_helpers()
    pointer = int(identity["methodPointerVa"], 16)
    body = pe.bytes_at_va(pointer, int(identity["bytes"]))
    instructions = native_parser.decode_x64_subset(body, pointer, stop_offset=len(body))
    calls: dict[int, dict[str, Any]] = {}
    for instruction in instructions:
        text = str(instruction.get("text", ""))
        if not text.startswith("call 0x"):
            continue
        raw = bytes.fromhex(str(instruction.get("bytes", "")))
        opcode_delta = raw.find(b"\xe8")
        if opcode_delta < 0:
            continue
        target = text.split(" ", 1)[1]
        call_offset = int(instruction["offset"]) + opcode_delta
        calls[call_offset] = {
            "offset": call_offset,
            "targetVa": target.lower(),
            "bytes": instruction.get("bytes"),
            "va": instruction.get("va"),
        }
    return calls


def _stage_observer_contract(
    pe: Any,
    md: Any,
    method_by_pointer: dict[int, list[dict[str, Any]]],
    pointers: list[int],
) -> dict[str, Any]:
    identities = {
        method_index: _stage_observer_identity(
            method_index,
            spec,
            pe,
            md,
            method_by_pointer,
            pointers,
        )
        for method_index, spec in STAGE_OBSERVER_METHOD_SPECS.items()
    }
    native_parser, _ = _load_il2cpp_helpers()

    def direct_edge(owner_index: int, offset: int, target_index: int, role: str) -> dict[str, Any]:
        owner = identities[owner_index]
        target = identities[target_index]
        call = _decoded_calls(pe, owner, native_parser).get(offset)
        if call is None or str(call.get("targetVa", "")).lower() != target["methodPointerVa"]:
            raise ContractError(
                f"stage observer direct-call edge drift for method {owner_index} at offset {offset}"
            )
        return {
            "ownerMethodIndex": owner_index,
            "offset": offset,
            "instructionVa": call["va"],
            "instructionBytes": call["bytes"],
            "targetMethodIndex": target_index,
            "targetVa": target["methodPointerVa"],
            "role": role,
        }

    stages: list[dict[str, Any]] = []
    for chain in STAGE_OBSERVER_CHAINS:
        worker_index = int(chain["worker"])
        dispatcher_index = int(chain["dispatcher"])
        direct_call_index = int(chain["directCall"])
        fallback = dict(chain["managedFallback"])
        fallback_index = int(fallback["methodIndex"])
        fallback_type, fallback_method = _metadata_identity(md, str(fallback["type"]), fallback_index)
        if fallback_method != fallback["method"]:
            raise ContractError(f"stage observer fallback method name drift for method index {fallback_index}")
        fallback_pointer = _method_pointer(fallback_index, method_by_pointer)
        if fallback_pointer != int(fallback["va"], 16):
            raise ContractError(f"stage observer fallback pointer drift for method index {fallback_index}")

        worker_edge = direct_edge(
            worker_index,
            int(chain["workerCallOffset"]),
            dispatcher_index,
            "worker_to_route_independent_dispatcher",
        )
        dispatcher_edge = direct_edge(
            dispatcher_index,
            int(chain["dispatcherCallOffset"]),
            direct_call_index,
            "dispatcher_to_burst_directcall",
        )
        direct_identity = identities[direct_call_index]
        fallback_call = _decoded_calls(pe, direct_identity, native_parser).get(int(fallback["callOffset"]))
        if fallback_call is None or str(fallback_call.get("targetVa", "")).lower() != f"0x{fallback_pointer:x}":
            raise ContractError(f"stage observer managed-fallback edge drift for method index {direct_call_index}")

        pointer = int(direct_identity["methodPointerVa"], 16)
        body = pe.bytes_at_va(pointer, int(direct_identity["bytes"]))
        instructions = native_parser.decode_x64_subset(body, pointer, stop_offset=len(body))
        indirect_spec = dict(chain["indirectCall"])
        indirect_rows = [row for row in instructions if int(row.get("offset", -1)) == int(indirect_spec["offset"])]
        expected_text = f"call {indirect_spec['operand']}"
        if (
            len(indirect_rows) != 1
            or str(indirect_rows[0].get("bytes", "")).lower() != str(indirect_spec["instructionBytes"]).lower()
            or str(indirect_rows[0].get("text", "")).lower() != expected_text.lower()
        ):
            raise ContractError(f"stage observer Burst function-pointer call drift for method index {direct_call_index}")

        stages.append({
            "stage": chain["stage"],
            "worker": identities[worker_index],
            "routeIndependentDispatcher": identities[dispatcher_index],
            "burstDirectCall": identities[direct_call_index],
            "callEdges": [
                worker_edge,
                dispatcher_edge,
                {
                    "ownerMethodIndex": direct_call_index,
                    "offset": int(indirect_spec["offset"]),
                    "instructionVa": indirect_rows[0]["va"],
                    "instructionBytes": indirect_rows[0]["bytes"],
                    "operand": indirect_spec["operand"],
                    "targetVa": None,
                    "role": "runtime_selected_burst_function_pointer",
                },
                {
                    "ownerMethodIndex": direct_call_index,
                    "offset": int(fallback["callOffset"]),
                    "instructionVa": fallback_call["va"],
                    "instructionBytes": fallback_call["bytes"],
                    "targetMethodIndex": fallback_index,
                    "targetVa": f"0x{fallback_pointer:x}",
                    "role": "managed_fallback",
                },
            ],
            "managedFallback": {
                "type": fallback_type,
                "method": fallback_method,
                "methodIndex": fallback_index,
                "methodPointerVa": f"0x{fallback_pointer:x}",
            },
            "captureBoundary": "observe the GameAssembly route-independent range dispatcher at entry/return; do not hook or replay a guessed Burst implementation",
        })

    return {
        "status": "route_independent_gameassembly_worker_entries_closed_selected_burst_route_unobserved",
        "stages": stages,
        "selectedBurstCpuRoute": {
            "status": "unresolved",
            "runtimeSelectedPointerObserved": False,
            "selectedExport": None,
            "selectedCpuVariant": None,
            "reason": "the current GameAssembly bodies perform an indirect call through a runtime function pointer; the installed static image does not identify the returned lib_burst_generated.dll address or selected CPU variant",
            "requiredEvidence": "observation-only BurstDirectCall returned-pointer/GetProcAddress telemetry from the exact gated process; no authored curve, parameter, sampled trajectory, or game-state modification",
        },
    }


def _call_record(
    decoded_calls: dict[int, dict[str, Any]],
    spec: tuple[int, str, str, str, str, dict[str, str] | None],
) -> dict[str, Any]:
    offset, target, type_name, method, role, expected_registers = spec
    call = decoded_calls.get(offset)
    if call is None or str(call.get("targetVa", "")).lower() != target.lower():
        raise ContractError(f"decoded current GameAssembly call edge drift at offset {offset}")
    return {
        "offset": offset,
        "targetVa": target,
        "type": type_name,
        "method": method,
        "role": role,
        "instructionBytes": call.get("bytes"),
        "instructionVa": call.get("va"),
    }


def _validate_evidence_call_consistency(body: dict[str, Any], spec: tuple[int, str, str, str, str, dict[str, str] | None]) -> None:
    """Treat ignored directCalls as a consistency check, never as authority."""
    offset, target, type_name, method, _, _ = spec
    rows = [row for row in body.get("directCalls", []) if int(row.get("offset", -1)) == offset]
    if len(rows) != 1 or str(rows[0].get("targetVa", "")).lower() != target.lower():
        raise ContractError(f"ignored direct-call evidence disagrees at offset {offset}")
    resolved = {(str(item.get("type")), str(item.get("method"))) for item in rows[0].get("resolved", [])}
    if (type_name, method) not in resolved:
        raise ContractError(f"ignored direct-call resolver evidence disagrees at offset {offset}")


def _validate_sources(native: dict[str, Any], catalog: dict[str, Any], native_path: Path, catalog_path: Path) -> None:
    metadata = native.get("metadata") or {}
    if str(metadata.get("metadataSha256", "")).lower() != EXPECTED_METADATA_SHA256:
        raise ContractError("native evidence metadata hash drift")
    if str(metadata.get("gameAssemblySha256", "")).lower() != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError("native evidence GameAssembly hash drift")
    code_registration = native.get("codeRegistration")
    code_registration = code_registration.get("va") if isinstance(code_registration, dict) else code_registration
    if str(code_registration or "").lower() != EXPECTED_CODE_REGISTRATION:
        raise ContractError("native evidence code registration drift")
    if str(catalog.get("metadata", {}).get("sha256", "")).lower() != EXPECTED_METADATA_SHA256:
        raise ContractError("metadata catalog hash drift")
    if native.get("metadata", {}).get("catalog") and _repo_path(catalog_path) not in str(native["metadata"]["catalog"]).replace("\\", "/"):
        raise ContractError("native evidence catalog source path drift")
    if int(native.get("summary", {}).get("mappedTargetCount", 0)) != int(native.get("summary", {}).get("catalogBodyTargetCount", -1)):
        raise ContractError("native evidence contains unresolved body targets")
    if not native_path.is_file() or not catalog_path.is_file():
        raise ContractError("ignored native evidence files are missing")


def build_contract(
    game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
    native_evidence: Path = DEFAULT_NATIVE,
    metadata_catalog: Path = DEFAULT_METADATA_CATALOG,
    dummy_generation: Path = DEFAULT_DUMMY_GENERATION,
) -> dict[str, Any]:
    try:
        gate = _native_gate(game_assembly, metadata)
        game_path = Path(gate["gameAssembly"]["path"])
        metadata_path = Path(gate["globalMetadata"]["path"])
        native = load_json(native_evidence)
        catalog = load_json(metadata_catalog)
        _validate_sources(native, catalog, native_evidence, metadata_catalog)
        pe, md, method_by_pointer, pointers = _independent_context(game_path, metadata_path)
        _validate_catalog_against_metadata(catalog, md)
        dummy = _dummy_record(dummy_generation, game_path, metadata_path)
        pinned_spans = _validate_pinned_spans(game_path)
        stage_observer = _stage_observer_contract(pe, md, method_by_pointer, pointers)

        method_identities = [
            _body_identity(native, type_name, index, game_path, pe, md, method_by_pointer, pointers)
            for type_name, index in METHODS
        ]
        identity_by_method = {(row["type"], row["methodIndex"]): row for row in method_identities}
        decoded_by_method = {
            key: _decoded_calls(pe, identity)
            for key, identity in identity_by_method.items()
            if key[1] in CALL_SPECS
        }
        call_rows: list[dict[str, Any]] = []
        for type_name, method_index in METHODS:
            specs = CALL_SPECS.get(method_index, ())
            if specs:
                body = _body(native, type_name, method_index)
                decoded_calls = decoded_by_method[(type_name, method_index)]
                for spec in specs:
                    _validate_evidence_call_consistency(body, spec)
                call_rows.extend([
                    {"methodIndex": method_index, "ownerType": type_name, "ownerMethod": identity_by_method[(type_name, method_index)]["method"], **_call_record(decoded_calls, spec)}
                    for spec in specs
                ])

        type_names = list(dict.fromkeys(type_name for type_name, _ in METHODS if type_name in FIELD_SHAPES))
        managed_types = [_managed_type(catalog, type_name) for type_name in type_names]
        method_signatures = []
        for type_name, method_index in METHODS:
            method = _catalog_method(catalog, type_name, method_index)
            method_signatures.append({
                "type": type_name,
                "methodIndex": method_index,
                "name": method.get("name"),
                "parameters": [
                    {"name": detail.get("name"), "metadataTypeIndex": int(detail["typeIndex"]), "metadataTypeName": detail.get("typeName")}
                    for detail in method.get("parameterDetails", [])
                ],
                "returnTypeIndex": int(method["returnTypeIndex"]),
                "returnTypeName": method.get("returnTypeName"),
            })

        manager_calls = [row for row in call_rows if row["role"].startswith("array_")]
        transform_access_calls = [row for row in call_rows if row["type"] == "UnityEngine.Jobs.TransformAccess"]
        burst_dispatch_calls = [row for row in call_rows if row["role"] == "burst_range_dispatch"]
        return {
            "schema": "endfield.charinfo.secondary-dynamics-transform-writeback.v1",
            "status": CONTRACT_STATUS,
            "secondary_dynamics_verified": False,
            "solver_implemented": False,
            "retail_equivalent": False,
            "native_gate": gate,
            "sources": {
                "native_evidence": file_record(native_evidence),
                "metadata_catalog": file_record(metadata_catalog),
                "dummy_generation": dummy,
                "payload_decode": file_record(DEFAULT_PAYLOAD_DECODE),
                "codeRegistration": EXPECTED_CODE_REGISTRATION,
            },
            "managed": {
                "typeCount": len(managed_types),
                "types": managed_types,
                "methodSignatures": method_signatures,
                "fieldTypeBoundary": "metadata type indexes and names are retained; unresolved constructed NativeArray type indexes are not guessed",
            },
            "native": {
                "methodBodies": method_identities,
                "pinnedEquationSpans": pinned_spans,
                "transformAccessArrayLifecycle": manager_calls,
                "transformAccessProperties": transform_access_calls,
                "burstRangeDispatch": burst_dispatch_calls,
                "stageObserverEntries": stage_observer,
            },
            "writeback": {
                "publicationSchedule": {
                    "postProxyOrder": ["CreatePostProxyMeshUpdateList", "CalcLineNormalTangent", "WriteTransformData", "WriteTransformLocalData"],
                    "managerOrder": ["ReadTransform", "PreProxyMeshUpdate", "SimulationStepUpdate", "CalcDisplayPosition", "PostProxyMeshUpdate", "DynamicBoneTransformManager.WriteTransform", "WriteAnimatorBufferData", "PostSimulationUpdate", "CompleteMasterJob"],
                    "rangeDirection": "ascending jobVertexIndexList order",
                },
                "arrayProvenance": {
                    "jobVertexIndexList": "SimulationManager post-proxy update list",
                    "teamDataArray": {"manager": "TeamManager", "managerOffset": "0x10", "strideBytes": 464},
                    "teamIdArray": {"manager": "VirtualMeshManager", "managerOffset": "0x10"},
                    "attributes": {"manager": "VirtualMeshManager", "managerOffset": "0x18"},
                    "vertexParentIndices": {"manager": "VirtualMeshManager", "managerOffset": "0x58"},
                    "vertexToTransformRotations": {"manager": "VirtualMeshManager", "managerOffset": "0x110"},
                    "positionsPostSolver": {"manager": "VirtualMeshManager", "managerOffset": "0x118"},
                    "rotationsPostSolver": {"manager": "VirtualMeshManager", "managerOffset": "0x120"},
                    "worldPositionOutput": {"manager": MANAGER, "managerOffset": "0x28", "field": "positionArray"},
                    "worldRotationOutput": {"manager": MANAGER, "managerOffset": "0x38", "field": "rotationArray"},
                    "scaleInput": {"manager": MANAGER, "managerOffset": "0x48", "field": "scaleArray"},
                    "localPositionOutput": {"manager": MANAGER, "managerOffset": "0x50", "field": "localPositionArray"},
                    "localRotationOutput": {"manager": MANAGER, "managerOffset": "0x60", "field": "localRotationArray"},
                    "finalJobBinding": "WriteTransformJob fields are named last*, but WriteTransform schedules the current position/rotation/local arrays above; the manager last* buffers are not publication sources",
                },
                "worldPublication": {
                    "abi": ["int* jobVertexIndexList", "TeamData* teamDataArray (stride 464)", "double3* transformPositionArray", "quaternion* transformRotationArray", "int16* teamIdArray", "double3* positionsPostSolver", "quaternion* rotationsPostSolver", "quaternion* vertexToTransformRotations", "int* lengthPtr"],
                    "guards": ["v = jobVertexIndexList[index]", "teamId = teamIdArray[v]", "return when teamId == 0"],
                    "indexEquations": ["local = v - team.proxyCommonChunk.start", "bone = team.proxyBoneChunk.start + local", "dst = team.proxyTransformChunk.start + local"],
                    "equations": ["transformPositionArray[dst] = positionsPostSolver[v]", "correction.value = team.negativeScaleQuaternionValue.value * vertexToTransformRotations[bone].value  # componentwise", "transformRotationArray[dst] = hamilton_f32(rotationsPostSolver[v], correction)"],
                    "excludedOperations": ["normalization", "interpolation", "attribute filtering", "blend weighting"],
                },
                "localPublication": {
                    "guards": ["v = jobVertexIndexList[index]", "return when teamIdArray[v] == 0", "return when vertexParentIndices[v] < 0", "return when (attributes[v] & 2) == 0"],
                    "indexEquations": ["local = v - team.proxyCommonChunk.start", "child = team.proxyTransformChunk.start + local", "parent = team.proxyTransformChunk.start + vertexParentIndices[v]"],
                    "equations": ["deltaWorld = worldPosition[child] - worldPosition[parent]  # float64", "parentInv = conjugate(worldRotation[parent]) / dot(worldRotation[parent], worldRotation[parent])  # float32, no zero guard", "localD = rotate_double(float64(parentInv), deltaWorld)", "localPosition[child] = float3(localD / double3(scale[parent]))", "relative = hamilton_f32(parentInv, worldRotation[child])", "localRotation[child].value = relative.value * team.negativeScaleQuaternionValue.value  # componentwise"],
                    "excludedOperations": ["blend weighting", "zero-length quaternion guard"],
                },
                "finalTransformJob": {
                    "flags": {"0x01": "read", "0x02": "world rotation write", "0x04": "local position/rotation write", "0x08": "restore", "0x10": "enable"},
                    "entryGates": ["0x10 enable flag is required", "culling-invisible entries are rejected", "native validity checks run before any TransformAccess write"],
                    "weightEquation": "w = float32(team.clothSimulateWeight(+0xf0) * team.clothLodFadeWeight(+0xf4))",
                    "unusedWeightField": "team.blendWeight(+0x104) is not used",
                    "branchPrecedence": "world branch when (flags & 0x02) != 0; otherwise local branch when (flags & 0x04) != 0",
                    "localBranch": ["targets are the current localPositionArray/localRotationArray", "when w < 1, saturated lerp current local position to target and shortest-path slerp current local rotation to target", "when w >= 1, assign targets directly"],
                    "worldBranch": ["shortest-path slerp current world rotation to target world rotation using w", "apply relative-transform state when enabled", "write world position only for spring entries", "when w < 1, saturated lerp current world position to target; when w >= 1, assign target directly"],
                    "dynamicInputs": ["culling state", "clothLodFadeWeight", "relative-transform state"],
                },
                "endminfBindingBoundary": {
                    "bindingEntries": 126,
                    "uniqueTransforms": 100,
                    "duplicateEntries": 26,
                    "overlaps": [
                        {"left": "Ribbon2", "right": "Coat", "duplicateEntries": 6},
                        {"left": "Ribbon", "right": "Coat", "duplicateEntries": 20},
                        {"left": "Hair", "right": "other", "duplicateEntries": 0},
                    ],
                    "addTransformDeduplicates": False,
                    "representation": "duplicates remain distinct NativeArray and TransformAccessArray entries",
                    "jobMode": 1,
                    "winner": None,
                    "failClosedReason": "TransformAccess execution exposes no static deterministic winner or owner priority; require live job-list/TransformAccess telemetry or an explicitly labeled compatibility policy",
                    "sourceAttributeClassification": _endminf_duplicate_source_boundary(),
                },
                "transformAccessPropertyReads": [row for row in transform_access_calls if row["role"] == "transform_read"],
                "transformAccessPropertyWrites": [row for row in transform_access_calls if row["role"] == "transform_write"],
            },
            "execution_boundary": {
                "transform_access_array_call_edges_closed": True,
                "array_ownership_closed": True,
                "schedule_closed": True,
                "transform_access_property_reads_closed": True,
                "transform_access_property_writes_closed": True,
                "job_managed_field_shapes_closed": True,
                "burst_range_dispatch_edges_closed": bool(burst_dispatch_calls),
                "stage_observer_gameassembly_entries_closed": True,
                "selected_burst_cpu_route_closed": False,
                "result_array_pointer_provenance_closed": True,
                "world_publication_equations_closed": True,
                "local_publication_equations_closed": True,
                "final_write_transform_branches_closed": True,
                "duplicate_transform_winner_closed": False,
                "solver_numerics_recovered": False,
                "unity_runtime_executed": False,
                "reason": "Publication provenance, equations, scheduling, and final TransformAccess branches are closed for the pinned client. Endminf's 26 duplicate entries have no proven deterministic winner; solver/runtime/visual equivalence also remain outside this contract.",
            },
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        return {
            "schema": "endfield.charinfo.secondary-dynamics-transform-writeback.v1",
            "status": "unavailable",
            "secondary_dynamics_verified": False,
            "solver_implemented": False,
            "retail_equivalent": False,
            "validationFailures": [str(exc)],
            "execution_boundary": {
                "transform_access_array_call_edges_closed": False,
                "array_ownership_closed": False,
                "schedule_closed": False,
                "transform_access_property_reads_closed": False,
                "transform_access_property_writes_closed": False,
                "stage_observer_gameassembly_entries_closed": False,
                "selected_burst_cpu_route_closed": False,
                "reason": "Native/evidence gate failed closed; no transform writeback claim is published.",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--native-evidence", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--metadata-catalog", type=Path, default=DEFAULT_METADATA_CATALOG)
    parser.add_argument("--dummy-generation", type=Path, default=DEFAULT_DUMMY_GENERATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build_contract(args.game_assembly, args.metadata, args.native_evidence, args.metadata_catalog, args.dummy_generation)
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    matches = None
    if args.check:
        matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
    elif result.get("status") == CONTRACT_STATUS:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "output": str(args.output), "matches": matches, "validationFailures": result.get("validationFailures", [])}, ensure_ascii=False))
    if args.check and not matches:
        return 1
    return 0 if result.get("status") == CONTRACT_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
