#!/usr/bin/env python3
"""Build a fail-closed BeyondDynamicBone transform writeback contract.

This contract records the part of secondary-dynamics writeback that can be
proved from the pinned IL2CPP metadata and GameAssembly image: the
``DynamicBoneTransformManager`` array lifecycle, the managed job field
shapes, and the native ``TransformAccess`` property calls made by the read,
restore, and write jobs.  It does *not* implement a solver or infer the
pointer behind a NativeArray from a register value.

The native evidence files are ignored, build-local artifacts.  A clean
checkout without them is deliberately unavailable and fails closed.  The
installed ``GameAssembly.dll`` and ``global-metadata.dat`` are checked through
the repository's explicit two-file gate before any claim is published.
"""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_transform_writeback_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = "0x18b9217d0"
EXPECTED_BONE_ASSEMBLY_SHA256 = "025c209c7f0b9ee927891421c74b42bdd16ff224f16f9c189f9f7d6ad1a3182c"

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


def _body_identity(native: dict[str, Any], type_name: str, method_index: int, game_assembly: Path) -> dict[str, Any]:
    row = _body(native, type_name, method_index)
    scan_bytes = int(row.get("scanBytes", 0))
    file_offset = int(str(row.get("fileOffset")), 0)
    with game_assembly.open("rb") as stream:
        stream.seek(file_offset)
        body = stream.read(scan_bytes)
    if len(body) != scan_bytes:
        raise ContractError(f"native body truncated: {type_name} index {method_index}")
    return {
        "type": type_name,
        "method": row.get("method"),
        "methodIndex": method_index,
        "methodPointerVa": row.get("methodPointerVa"),
        "fileOffset": row.get("fileOffset"),
        "bytes": scan_bytes,
        "sha256": hashlib.sha256(body).hexdigest(),
        "hashSource": "pinned GameAssembly.dll fileOffset + scanBytes",
    }


def _resolved(call: dict[str, Any]) -> set[tuple[str, str]]:
    return {(str(row.get("type")), str(row.get("method"))) for row in call.get("resolved", [])}


def _register_writes(call: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for register, entry in (call.get("argumentContext", {}).get("argRegisterWrites") or {}).items():
        value = (entry.get("write") or {}).get("value")
        if value is not None:
            values[str(register)] = str(value)
    return values


def _call_record(body: dict[str, Any], spec: tuple[int, str, str, str, str, dict[str, str] | None]) -> dict[str, Any]:
    offset, target, type_name, method, role, expected_registers = spec
    matches = [call for call in body.get("directCalls", []) if int(call.get("offset", -1)) == offset]
    if len(matches) != 1:
        raise ContractError(f"expected one call at {body.get('method')}+{offset}, found {len(matches)}")
    call = matches[0]
    if str(call.get("targetVa")) != target:
        raise ContractError(f"{body.get('method')}+{offset} target drift")
    if (type_name, method) not in _resolved(call):
        raise ContractError(f"{body.get('method')}+{offset} resolver drift")
    observed = _register_writes(call)
    if expected_registers is not None and observed != expected_registers:
        raise ContractError(f"{body.get('method')}+{offset} register-write drift: {observed!r}")
    return {
        "offset": offset,
        "targetVa": target,
        "type": type_name,
        "method": method,
        "role": role,
        "observedRegisterWrites": observed,
    }


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
        dummy = _dummy_record(dummy_generation, game_path, metadata_path)

        method_identities = [_body_identity(native, type_name, index, game_path) for type_name, index in METHODS]
        call_rows: list[dict[str, Any]] = []
        for type_name, method_index in METHODS:
            specs = CALL_SPECS.get(method_index, ())
            if specs:
                body = _body(native, type_name, method_index)
                call_rows.extend([
                    {"methodIndex": method_index, "ownerType": type_name, "ownerMethod": body.get("method"), **_call_record(body, spec)}
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
            "status": "transform_writeback_access_closed",
            "secondary_dynamics_verified": False,
            "solver_implemented": False,
            "retail_equivalent": False,
            "native_gate": gate,
            "sources": {
                "native_evidence": file_record(native_evidence),
                "metadata_catalog": file_record(metadata_catalog),
                "dummy_generation": dummy,
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
                "transformAccessArrayLifecycle": manager_calls,
                "transformAccessProperties": transform_access_calls,
                "burstRangeDispatch": burst_dispatch_calls,
            },
            "writeback": {
                "resultFields": [
                    "lastpositionArray", "lastrotationArray", "lastlocalPositionArray", "lastlocalRotationArray",
                ],
                "readFields": ["positionArray", "rotationArray", "localPositionArray", "localRotationArray", "localToWorldMatrixArray"],
                "transformAccessPropertyReads": [row for row in transform_access_calls if row["role"] == "transform_read"],
                "transformAccessPropertyWrites": [row for row in transform_access_calls if row["role"] == "transform_write"],
                "pointerProvenance": "unresolved: native register values such as [rax] are recorded, but the evidence does not establish which NativeArray element produced each value",
                "jobIndexBoundary": "managed Execute(int index, TransformAccess transform) signatures are closed; schedule-range call and runtime array length are not independently closed here",
            },
            "execution_boundary": {
                "transform_access_array_create_destroy_closed": True,
                "transform_access_array_add_set_length_closed": True,
                "transform_access_property_reads_closed": True,
                "transform_access_property_writes_closed": True,
                "job_managed_field_shapes_closed": True,
                "burst_range_dispatch_edges_closed": bool(burst_dispatch_calls),
                "result_array_pointer_provenance_closed": False,
                "solver_numerics_recovered": False,
                "unity_runtime_executed": False,
                "reason": "Native TransformAccess lifecycle/property edges and managed job signatures are pinned for one client build; the array-element pointer mapping, full Burst numerics, scheduling range, and runtime/visual equivalence remain open.",
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
                "transform_access_array_create_destroy_closed": False,
                "transform_access_array_add_set_length_closed": False,
                "transform_access_property_reads_closed": False,
                "transform_access_property_writes_closed": False,
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
    elif result.get("status") == "transform_writeback_access_closed":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "output": str(args.output), "matches": matches, "validationFailures": result.get("validationFailures", [])}, ensure_ascii=False))
    if args.check and not matches:
        return 1
    return 0 if result.get("status") == "transform_writeback_access_closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
