#!/usr/bin/env python3
"""Build the pinned PostProxyMeshUpdate native scheduling contract.

The contract closes the managed/native ABI, ordered job construction, job
payload layouts, and exact generic scheduling identities.  It deliberately
leaves the CreatePostProxyMeshUpdateList and CalcLineNormalTangent worker
equations open; no capture samples, fitted curves, or replay data are inputs.
"""

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
DATA_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/secondary_dynamics_owner"
DEFAULT_OUTPUT = DATA_ROOT / "secondary_dynamics_post_proxy_contract.json"
DEFAULT_METADATA_EVIDENCE = EVIDENCE_ROOT / "post_proxy_metadata.json"
DEFAULT_NATIVE_EVIDENCE = EVIDENCE_ROOT / "post_proxy_native.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_METADATA_EVIDENCE_SHA256 = "d1533b659e33a2e561c444cb4aec9a929dfac355a8d3409748c009e9c277a295"
EXPECTED_NATIVE_EVIDENCE_SHA256 = "3bad91ae59e34b7abc50b5f88aafb77ea9e2c1395fba1346cc503deafb982b5d"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


POST_PROXY = {
    "methodIndex": 384785,
    "token": "0x060004da",
    "type": "BeyondDynamicBone.VirtualMeshManager",
    "method": "PostProxyMeshUpdate",
    "startVa": 0x182F8C4A0,
    "fileOffset": 0x2F8AAA0,
    "spanBytes": 0x10B0,
    "bodySha256": "5a74ebb4a44356d4114332da8ca9c4ed183ed2e7d88216637072e0ebf151bead",
    "firstRetOffset": 0xE34,
    "throughFirstRetSha256": "842cc941559ab9c9b6c7c62092ca6a30f05ca5ad7a7ea6c29e93a92e9fbc685c",
}

STAGES = (
    {
        "order": 1,
        "job": "CreatePostProxyMeshUpdateListJob",
        "jobTypeIndex": 208231,
        "setIndexCountOffset": 0x3B8,
        "setIndexCountVa": 0x183D84160,
        "getReflectionDataOffset": 0x496,
        "getReflectionDataMethodSpec": 516826,
        "reflectionPointerSlot": 483841,
        "reflectionGenericInst": 22216,
        "schedule": {"kind": "IJobParallelFor", "batchSize": 1, "methodIndex": 401866,
                     "pointerVa": 0x1876C6DC4, "methodSpec": 517373,
                     "pointerSlot": 484362},
        "crossFrame": {"methodIndex": 384474, "pointerVa": 0x187AF4C60,
                       "methodSpec": 508694, "pointerSlot": 477087},
    },
    {
        "order": 2,
        "job": "CalcLineNormalTangentJob",
        "jobTypeIndex": 208217,
        "setIndexCountOffset": 0x765,
        "setIndexCountVa": 0x183D51420,
        "getReflectionDataOffset": 0x838,
        "getReflectionDataMethodSpec": 516819,
        "reflectionPointerSlot": 483834,
        "reflectionGenericInst": 22056,
        "schedule": {"kind": "IJobParallelForDefer", "batchSize": 8, "methodIndex": 476935,
                     "pointerVa": 0x1876C6BA8, "methodSpec": 517163,
                     "pointerSlot": 484159},
        "crossFrame": {"methodIndex": 384475, "pointerVa": 0x187AF43D0,
                       "methodSpec": 508714, "pointerSlot": 477107},
    },
    {
        "order": 3,
        "job": "WriteTransformDataJob",
        "jobTypeIndex": 208234,
        "setIndexCountOffset": 0xA1B,
        "setIndexCountVa": 0x183D77850,
        "getReflectionDataOffset": 0xAE9,
        "getReflectionDataMethodSpec": 516828,
        "reflectionPointerSlot": 483843,
        "reflectionGenericInst": 22060,
        "schedule": {"kind": "IJobParallelForDefer", "batchSize": 16, "methodIndex": 476935,
                     "pointerVa": 0x1876C6BA8, "methodSpec": 517167,
                     "pointerSlot": 484163},
        "crossFrame": {"methodIndex": 384475, "pointerVa": 0x187AF773C,
                       "methodSpec": 508718, "pointerSlot": 477111},
    },
    {
        "order": 4,
        "job": "WriteTransformLocalDataJob",
        "jobTypeIndex": 208236,
        "setIndexCountOffset": 0xCD0,
        "setIndexCountVa": 0x183D52360,
        "getReflectionDataOffset": 0xDAE,
        "getReflectionDataMethodSpec": 516829,
        "reflectionPointerSlot": 483844,
        "reflectionGenericInst": 22061,
        "schedule": {"kind": "IJobParallelForDefer", "batchSize": 32, "methodIndex": 476935,
                     "pointerVa": 0x1876C6BA8, "methodSpec": 517168,
                     "pointerSlot": 484164},
        "crossFrame": {"methodIndex": 384475, "pointerVa": 0x187AF7974,
                       "methodSpec": 508719, "pointerSlot": 477112},
    },
)

JOB_FIELDS = {
    "CreatePostProxyMeshUpdateListJob": (
        48300,
        (("teamDataArray", 229882, 0x00), ("processingCounter0", 229883, 0x10),
         ("processingList0", 229884, 0x20), ("processingCounter1", 229885, 0x30),
         ("processingList1", 229886, 0x40), ("processingCounter2", 229887, 0x50),
         ("processingList2", 229888, 0x60), ("processingCounter3", 229889, 0x70),
         ("processingList3", 229890, 0x80), ("_indexCount", 229891, 0x90)),
        0xA0,
    ),
    "CalcLineNormalTangentJob": (
        48301,
        (("jobBaseLineList", 229892, 0x00), ("teamDataArray", 229893, 0x10),
         ("parameterArray", 229894, 0x20), ("attributes", 229895, 0x30),
         ("positions", 229896, 0x40), ("rotations", 229897, 0x50),
         ("vertexLocalPositions", 229898, 0x60), ("vertexLocalRotations", 229899, 0x70),
         ("parentIndices", 229900, 0x80), ("childIndexArray", 229901, 0x90),
         ("childDataArray", 229902, 0xA0), ("baseLineFlags", 229903, 0xB0),
         ("baseLineTeamIds", 229904, 0xC0), ("baseLineStartIndices", 229905, 0xD0),
         ("baseLineDataCounts", 229906, 0xE0), ("baseLineData", 229907, 0xF0),
         ("_indexCount", 229908, 0x100)),
        0x110,
    ),
    "WriteTransformDataJob": (
        48304,
        (("jobVertexIndexList", 229927, 0x00), ("teamDataArray", 229928, 0x10),
         ("transformPositionArray", 229929, 0x20), ("transformRotationArray", 229930, 0x30),
         ("teamIds", 229931, 0x40), ("positions", 229932, 0x50),
         ("rotations", 229933, 0x60), ("vertexToTransformRotations", 229934, 0x70),
         ("_indexCount", 229935, 0x80)),
        0x90,
    ),
    "WriteTransformLocalDataJob": (
        48305,
        (("jobVertexIndexList", 229936, 0x00), ("teamDataArray", 229937, 0x10),
         ("teamIds", 229938, 0x20), ("attributes", 229939, 0x30),
         ("vertexParentIndices", 229940, 0x40), ("transformPositionArray", 229941, 0x50),
         ("transformRotationArray", 229942, 0x60), ("transformScaleArray", 229943, 0x70),
         ("transformLocalPositionArray", 229944, 0x80),
         ("transformLocalRotationArray", 229945, 0x90), ("_indexCount", 229946, 0xA0)),
        0xB0,
    ),
}

COLD_SPANS = (
    ("createList.parallelSchedule", 0x184F719AD, 183, "4719cfbfbd935abeec928b9bb13817c689d15b9d0f4ec1105e084b720c643765"),
    ("createList.managedWorkerFallback", 0x184F71A64, 90, "072931d13b5e4b4ed4bf76acb4fc573a38437c91cd7198d926fd96525f8b7b7f"),
    ("calcLine.parallelSchedule", 0x184F71B5B, 172, "ef1a37914751af65e5300ee74593270555942a13a452c2a4bb606d24655ddc95"),
    ("calcLine.managedWorkerFallback", 0x184F71C07, 90, "345d0c714243e33ef822263e1ea3abdf2032de0c41e5421ee1879adbd3ed95c8"),
    ("writeWorldAndLocal.directSchedule", 0x184F71CF9, 709, "6282f4c057e37c867e134ab63218d4be2e390e0b274e93935641a7a7c8138460"),
    ("writeWorld.managedWorkerFallback", 0x184F71FBE, 166, "3b9a21353d270175e9cb543bcc950961d2d37d82b67cc9a6f0eb206c2ad92d71"),
    ("writeLocal.parallelSchedule", 0x184F720F2, 182, "5b7ef19b3b21bc5435d2bf143a029a754e584a7c437bd2fe67cd3a2359a8df13"),
    ("writeLocal.managedWorkerFallback", 0x184F721A8, 90, "93473a002a7338a223d7d2e8a8e453df5b9b04a0df3f764570442a0d636a29e4"),
)

FALLBACK_CALLS = (
    ("createList", 0x184F71AAE, 0x18674EEC0),
    ("calcLine", 0x184F71C54, 0x186746134),
    ("writeWorld", 0x184F720B1, 0x186754B30),
    ("writeLocal", 0x184F721F5, 0x186755CA8),
)

WORKER_TARGETS = (
    (384830, "CreatePostProxyMeshUpdateListKernel", 0x18674E9C4),
    (384831, "CreatePostProxyMeshUpdateListRangeKernel", 0x18674EB40),
    (384832, "CreatePostProxyMeshUpdateListKernel$BurstManaged", 0x186743868),
    (384833, "CreatePostProxyMeshUpdateListRangeKernel$BurstManaged", 0x18674EA88),
    (384854, "CalcLineNormalTangentKernel", 0x1867456E4),
    (384855, "CalcLineNormalTangentRangeKernel", 0x18674580C),
    (384856, "CalcLineNormalTangentKernel$BurstManaged", 0x186744FB0),
    (384857, "CalcLineNormalTangentRangeKernel$BurstManaged", 0x186741214),
)


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (_load("post_proxy_metadata", root / "catalog_option_flow_metadata.py"),
            _load("post_proxy_native", root / "map_body_targets_to_gameassembly.py"))


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


def _source(path: Path, expected_hash: str) -> dict[str, Any]:
    actual = _sha(path)
    if actual != expected_hash:
        raise ContractError(f"source drift: {_repo_path(path)} {actual} != {expected_hash}")
    return {"repoPath": _repo_path(path), "size": path.stat().st_size, "sha256": actual}


def _gate(game_assembly: Path | None, metadata: Path | None) -> tuple[dict[str, Any], Path, Path]:
    result = check_installed_native_inputs(EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256,
                                           gameassembly=game_assembly, metadata=metadata)
    if not result.validated:
        raise ContractError(f"native gate [{result.status}]: {result.detail}")
    ga, md = Path(result.gameassembly), Path(result.metadata)
    gate = {
        "gameAssembly": {"path": _repo_path(ga), "size": ga.stat().st_size,
                         "sha256": result.gameassembly_sha256},
        "globalMetadata": {"path": _repo_path(md), "size": md.stat().st_size,
                           "sha256": result.metadata_sha256},
    }
    return gate, ga, md


def _call_target(pe: Any, call_va: int) -> int:
    data = pe.bytes_at_va(call_va, 5)
    if len(data) != 5 or data[0] != 0xE8:
        raise ContractError(f"expected rel32 call at 0x{call_va:x}")
    return call_va + 5 + struct.unpack_from("<i", data, 1)[0]


def _validate_call(pe: Any, call_va: int, target_va: int) -> None:
    actual = _call_target(pe, call_va)
    if actual != target_va:
        raise ContractError(f"call drift at 0x{call_va:x}: 0x{actual:x} != 0x{target_va:x}")


def _field_layout(md: Any, pe: Any, registration: dict[str, Any], job: str) -> dict[str, Any]:
    type_index, expected, size = JOB_FIELDS[job]
    typedef = md.types[type_index]
    offset_table = pe.u64_at_va(int(registration["fieldOffsets"], 16) + type_index * 8)
    fields = []
    for name, field_index, payload_offset in expected:
        ordinal = field_index - typedef.field_start
        if ordinal < 0 or ordinal >= typedef.field_count:
            raise ContractError(f"field ordinal drift for {job}.{name}")
        actual_name = md.string(md.fields[field_index].name_index)
        boxed_offset = pe.u32_at_va(offset_table + ordinal * 4)
        if actual_name != name or boxed_offset != payload_offset + 0x10:
            raise ContractError(f"field drift for {job}.{name}: {actual_name} 0x{boxed_offset:x}")
        fields.append({"name": name, "fieldIndex": field_index,
                       "nativePayloadOffset": f"0x{payload_offset:x}",
                       "boxedFieldOffset": f"0x{boxed_offset:x}"})
    return {"metadataTypeIndex": type_index, "nativePayloadBytes": size, "fields": fields}


def _generic(index: dict[int, list[dict[str, Any]]], *, pointer: int, method_index: int,
             spec_index: int, slot: int, job_type_index: int, job_type: str,
             inst_index: int | None = None) -> dict[str, Any]:
    matches = [row for row in index.get(pointer, [])
               if row["methodIndex"] == method_index and row["methodSpecIndex"] == spec_index]
    if len(matches) != 1:
        raise ContractError(f"generic MethodSpec drift for {job_type}: {matches}")
    row = matches[0]
    inst = row["methodInstantiation"]
    arg = inst["arguments"][0] if len(inst.get("arguments", [])) == 1 else {}
    if (row["genericMethodPointerSlot"], arg.get("typeIndex"), arg.get("typeName")) != (
            slot, job_type_index, job_type):
        raise ContractError(f"generic identity drift for {job_type}")
    if inst_index is not None and inst.get("genericInstIndex") != inst_index:
        raise ContractError(f"generic instantiation drift for {job_type}")
    return {"methodIndex": method_index, "token": row["token"], "methodSpecIndex": spec_index,
            "genericMethodPointerSlot": slot, "methodInstantiationGenericInstIndex": inst["genericInstIndex"],
            "genericEntryVa": f"0x{pointer:x}", "jobTypeIndex": job_type_index, "jobType": job_type}


def _method_pointer_context(md: Any, native: Any, pe: Any, code: int) -> tuple[list[int], list[int], int]:
    modules = native.parse_codegen_modules(pe, code)
    ranges = native.image_method_ranges(md)
    pointers, _ = native.build_pointer_indexes(pe, md, modules, ranges)
    bone = pointers["BeyondDynamicBone.dll"]
    return bone, sorted({pointer for pointer in bone if pointer}), ranges["BeyondDynamicBone.dll"]["methodStart"]


def _method_record(md: Any, bone: list[int], unique: list[int], method_start: int, method_index: int,
                   expected_name: str, expected_pointer: int) -> dict[str, Any]:
    pointer = bone[method_index - method_start]
    # Check the defining metadata record and codegen pointer together.
    if pointer != expected_pointer or md.string(md.methods[method_index].name_index) != expected_name:
        raise ContractError(f"worker identity drift for method {method_index}")
    end = next(value for value in unique if value > pointer)
    return {"methodIndex": method_index, "token": f"0x{md.methods[method_index].token:08x}",
            "method": expected_name, "startVa": f"0x{pointer:x}", "endVa": f"0x{end:x}",
            "spanBytes": end - pointer}


def _dependency(path: Path, expected_hash: str, schema: str) -> dict[str, Any]:
    source = _source(path, expected_hash)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != schema or payload.get("native_gate", {}).get("gameAssembly", {}).get("sha256") != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError(f"dependency contract drift: {path.name}")
    return {**source, "schema": schema, "status": payload.get("status")}


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA,
                   metadata_evidence: Path = DEFAULT_METADATA_EVIDENCE,
                   native_evidence: Path = DEFAULT_NATIVE_EVIDENCE) -> dict[str, Any]:
    gate, game_path, metadata_path = _gate(game_assembly, metadata)
    sources = {
        "metadataCatalog": _source(metadata_evidence, EXPECTED_METADATA_EVIDENCE_SHA256),
        "nativeEvidence": _source(native_evidence, EXPECTED_NATIVE_EVIDENCE_SHA256),
    }
    metadata_payload = json.loads(metadata_evidence.read_text(encoding="utf-8"))
    native_payload = json.loads(native_evidence.read_text(encoding="utf-8"))
    if metadata_payload["metadata"]["sha256"] != EXPECTED_METADATA_SHA256:
        raise ContractError("metadata evidence describes another build")
    if (native_payload["metadata"]["metadataSha256"].lower() != EXPECTED_METADATA_SHA256 or
            native_payload["metadata"]["gameAssemblySha256"].lower() != EXPECTED_GAME_ASSEMBLY_SHA256 or
            int(native_payload["settings"]["codeRegistration"], 16) != EXPECTED_CODE_REGISTRATION):
        raise ContractError("native evidence describes another build")
    evidence_method = next((row for row in native_payload["bodyTargets"]
                            if row["methodIndex"] == POST_PROXY["methodIndex"]), None)
    if evidence_method is None or (evidence_method["method"], int(evidence_method["methodPointerVa"], 16),
                                   evidence_method["scanBytes"],
                                   evidence_method["methodBodySummary"]["firstRetOffset"]) != (
            POST_PROXY["method"], POST_PROXY["startVa"], POST_PROXY["spanBytes"], POST_PROXY["firstRetOffset"]):
        raise ContractError("PostProxyMeshUpdate evidence row drift")

    catalog, native = _helpers()
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    names = {md.string(image.name_index) for image in md.images}
    code = native.find_code_registration(pe, names)
    meta = native.find_metadata_registration(pe, code)
    if (code, meta) != (EXPECTED_CODE_REGISTRATION, EXPECTED_METADATA_REGISTRATION):
        raise ContractError(f"registration drift: {code!r}, {meta!r}")
    registration = native.metadata_registration_summary(pe, meta)
    bone, unique, method_start = _method_pointer_context(md, native, pe, code)
    method = md.methods[POST_PROXY["methodIndex"]]
    pointer = bone[POST_PROXY["methodIndex"] - method_start]
    body = pe.bytes_at_va(pointer, POST_PROXY["spanBytes"])
    if (md.string(method.name_index), f"0x{method.token:08x}", pointer,
            pe.file_offset_for_va(pointer)[0], hashlib.sha256(body).hexdigest(), body[POST_PROXY["firstRetOffset"]]) != (
            POST_PROXY["method"], POST_PROXY["token"], POST_PROXY["startVa"], POST_PROXY["fileOffset"],
            POST_PROXY["bodySha256"], 0xC3):
        raise ContractError("authoritative PostProxyMeshUpdate body drift")
    if hashlib.sha256(body[:POST_PROXY["firstRetOffset"] + 1]).hexdigest() != POST_PROXY["throughFirstRetSha256"]:
        raise ContractError("PostProxyMeshUpdate first-return prefix drift")
    expected_entry = bytes.fromhex(
        "48 8b c4 48 89 58 10 48 89 70 18 48 89 78 20 48 89 48 08 55 41 54 41 55 41 56 41 57"
    )
    if body[:len(expected_entry)] != expected_entry or body[0x2E:0x31] != b"\x48\x8b\xda" or body[0x49:0x4C] != b"\x4d\x8b\xe0":
        raise ContractError("PostProxyMeshUpdate Win64 ABI prologue drift")
    if body[0xDFD:0xE00] != b"\x0f\x11\x00":
        raise ContractError("PostProxyMeshUpdate hidden return write drift")

    for stage in STAGES:
        _validate_call(pe, pointer + stage["setIndexCountOffset"], stage["setIndexCountVa"])
        _validate_call(pe, pointer + stage["getReflectionDataOffset"], 0x183F51D90)
    for _, call_va, target_va in FALLBACK_CALLS:
        _validate_call(pe, call_va, target_va)
    for call_va, target_va in ((0x184F71E4E, 0x186732144), (0x184F71FAA, 0x18673237C)):
        _validate_call(pe, call_va, target_va)
    for va, expected in ((0x184F719BD, b"\x41\xb9\x01\x00\x00\x00"),
                         (0x184F71BCC, b"\x41\xb9\x08\x00\x00\x00"),
                         (0x184F71E41, b"\xc7\x44\x24\x20\x10\x00\x00\x00"),
                         (0x184F71F9D, b"\xc7\x44\x24\x20\x20\x00\x00\x00")):
        if pe.bytes_at_va(va, len(expected)) != expected:
            raise ContractError(f"batch-size immediate drift at 0x{va:x}")

    cold = []
    for name, start, size, expected_hash in COLD_SPANS:
        data = pe.bytes_at_va(start, size)
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != expected_hash:
            raise ContractError(f"cold span drift for {name}: {actual_hash}")
        cold.append({"name": name, "startVa": f"0x{start:x}", "spanBytes": size,
                     "sha256": actual_hash})

    generic_index = native.build_generic_method_index(pe, md, code, meta)
    stages = []
    for raw in STAGES:
        job_type = f"BeyondDynamicBone.VirtualMeshManager+{raw['job']}"
        reflection = _generic(generic_index, pointer=0x183F51D90, method_index=401847,
                              spec_index=raw["getReflectionDataMethodSpec"],
                              slot=raw["reflectionPointerSlot"], job_type_index=raw["jobTypeIndex"],
                              job_type=job_type, inst_index=raw["reflectionGenericInst"])
        schedule_raw = raw["schedule"]
        schedule = _generic(generic_index, pointer=schedule_raw["pointerVa"],
                            method_index=schedule_raw["methodIndex"], spec_index=schedule_raw["methodSpec"],
                            slot=schedule_raw["pointerSlot"], job_type_index=raw["jobTypeIndex"],
                            job_type=job_type)
        cross_raw = raw["crossFrame"]
        cross = _generic(generic_index, pointer=cross_raw["pointerVa"],
                         method_index=cross_raw["methodIndex"], spec_index=cross_raw["methodSpec"],
                         slot=cross_raw["pointerSlot"], job_type_index=raw["jobTypeIndex"],
                         job_type=job_type)
        stages.append({"order": raw["order"], "job": raw["job"],
                       "setIndexCount": {"callOffset": f"0x{raw['setIndexCountOffset']:x}",
                                         "targetVa": f"0x{raw['setIndexCountVa']:x}"},
                       "getReflectionData": {**reflection, "callOffset": f"0x{raw['getReflectionDataOffset']:x}"},
                       "parallelSchedule": {**schedule, "kind": schedule_raw["kind"],
                                            "innerLoopBatchCount": schedule_raw["batchSize"]},
                       "crossFrameScheduleHelper": cross,
                       "jobPayload": _field_layout(md, pe, registration, raw["job"])})

    workers = []
    for method_index, name, expected_pointer in WORKER_TARGETS:
        row = _method_record(md, bone, unique, method_start, method_index, name, expected_pointer)
        data = pe.bytes_at_va(expected_pointer, row["spanBytes"])
        row["bodySha256"] = hashlib.sha256(data).hexdigest()
        workers.append(row)
    expected_managed = {
        384832: (3300, "02a0d53fed888f05f966dbe2250f59e4f2722d0cfac3928e7a2b268d39bb4bde"),
        384856: (1844, "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829"),
    }
    for row in workers:
        if row["methodIndex"] in expected_managed and (row["spanBytes"], row["bodySha256"]) != expected_managed[row["methodIndex"]]:
            raise ContractError(f"managed worker body drift for {row['method']}")
    create_hot_hash = hashlib.sha256(pe.bytes_at_va(0x186743868, 0x223)).hexdigest()
    if create_hot_hash != "05248d617681f7cbce052c79fffc748936523f7230da3812c6c8bab0f3230213":
        raise ContractError(f"CreatePostProxyMeshUpdateList hot-path drift: {create_hot_hash}")

    dependencies = {
        "callback": _dependency(DATA_ROOT / "secondary_dynamics_callback_contract.json",
                                "a6143a667a6df88f088201fe314522589f9faf5149ed2f20a1dc581cf3f27f65",
                                "endfield.charinfo.secondary-dynamics-callback-writeback.v1"),
        "transformWriteback": _dependency(DATA_ROOT / "secondary_dynamics_transform_writeback_contract.json",
                                          "f3e44da89e706cf5a43e625f774196091790b5d548ab720d35b0d8ce77c520c8",
                                          "endfield.charinfo.secondary-dynamics-transform-writeback.v1"),
    }
    sources["dependencies"] = dependencies
    return {
        "schema": "endfield.charinfo.secondary-dynamics-post-proxy.v1",
        "status": "post_proxy_schedule_and_create_list_control_closed_calc_line_vectors_open",
        "manager_schedule_closed": True,
        "managed_job_payload_layout_closed": True,
        "generic_methodspec_identities_closed": True,
        "world_local_publication_equations_closed": True,
        "create_list_worker_control_flow_recovered": True,
        "calc_line_entry_control_flow_recovered": True,
        "create_list_kernel_numerics_recovered": False,
        "calc_line_normal_tangent_numerics_recovered": False,
        "selected_cross_frame_route_closed": False,
        "solver_implemented": False,
        "retail_equivalent": False,
        "capture_used_as_implementation_source": False,
        "native_gate": gate,
        "sources": sources,
        "registrations": {"codeRegistrationVa": f"0x{code:x}",
                          "metadataRegistrationVa": f"0x{meta:x}"},
        "managerAbi": {
            "methodIndex": POST_PROXY["methodIndex"], "token": POST_PROXY["token"],
            "type": POST_PROXY["type"], "method": POST_PROXY["method"],
            "startVa": f"0x{pointer:x}", "fileOffset": f"0x{POST_PROXY['fileOffset']:x}",
            "spanBytes": POST_PROXY["spanBytes"], "bodySha256": POST_PROXY["bodySha256"],
            "firstRetOffset": f"0x{POST_PROXY['firstRetOffset']:x}",
            "throughFirstRetSha256": POST_PROXY["throughFirstRetSha256"],
            "win64Arguments": {"rcx": "hidden 16-byte JobHandle return buffer", "rdx": "VirtualMeshManager this",
                               "r8": "input JobHandle address", "r9": "MethodInfo (unused by unpatched body)"},
            "return": "the dependency threaded through all four stages is written to the hidden return buffer",
        },
        "stageOrder": stages,
        "dependencyFlow": "input JobHandle -> CreatePostProxyMeshUpdateList -> CalcLineNormalTangent -> WriteTransformData -> WriteTransformLocalData -> returned JobHandle",
        "createListHotControlFlow": {
            "managedWorkerMethodIndex": 384832,
            "hotSpan": {"startVa": "0x186743868", "throughRetBytes": 0x223,
                        "throughRetSha256": "05248d617681f7cbce052c79fffc748936523f7230da3812c6c8bab0f3230213"},
            "argumentBoundary": {
                "registers": {"rcx": "teamDataArray", "rdx": "processingCounter0",
                              "r8": "processingList0", "r9": "processingCounter1"},
                "stackArguments": [
                    {"rbpOffset": "0x120", "value": "processingList1"},
                    {"rbpOffset": "0x128", "value": "processingCounter2"},
                    {"rbpOffset": "0x130", "value": "processingList2"},
                    {"rbpOffset": "0x138", "value": "processingCounter3"},
                    {"rbpOffset": "0x140", "value": "processingList3"},
                    {"rbpOffset": "0x148", "value": "teamId"},
                ],
            },
            "teamDataStrideBytes": 0x1D0,
            "gates": [
                {"offset": "0x2d", "condition": "teamId != 0"},
                {"offset": "0xcb", "call": "TeamData.get_IsEnable", "required": True},
                {"offset": "0xdf", "call": "TeamData.get_IsCullingInvisible", "required": False},
            ],
            "atomicQueueAppends": [
                {"queue": 0, "sourceDataChunkPayloadOffsets": ["0x44", "0x48"],
                 "conditions": ["TeamData.get_TriangleCount() > 0", "DataChunk at payload 0x44 is valid"],
                 "atomicReserveOffset": "0x110", "appendLoopOffsets": ["0x121", "0x134"]},
                {"queue": 1, "sourceDataChunkPayloadOffsets": ["0x44", "0x48"],
                 "conditions": ["TeamData payload int at 0x38 == 3"],
                 "atomicReserveOffset": "0x143", "appendLoopOffsets": ["0x158", "0x16f"]},
                {"queue": 2, "sourceDataChunkPayloadOffsets": ["0x7c", "0x80"],
                 "conditions": ["DataChunk at payload 0x7c is valid"],
                 "atomicReserveOffset": "0x191", "appendLoopOffsets": ["0x1a6", "0x1bc"]},
                {"queue": 3, "sourceDataChunkPayloadOffsets": ["0x54", "0x58"],
                 "conditions": ["TeamData.get_TriangleCount() > 0"],
                 "atomicReserveOffset": "0x1d5", "appendLoopOffsets": ["0x1ef", "0x204"]},
            ],
            "operation": "Each accepted chunk atomically reserves count slots, then appends the contiguous indices start + i. No captured indices are stored.",
        },
        "calcLineEntryControlFlow": {
            "managedWorkerMethodIndex": 384856,
            "bodySha256": "9868eee8cddc41aae648fead87025f7a53b4d158dca963865dfd2126a0f9a829",
            "entryGates": [
                {"offset": "0x98", "operation": "baseLineIndex = jobBaseLineList[index]"},
                {"offset": "0xa3", "condition": "attributes[baseLineIndex] bit 0 is set"},
                {"offset": "0xb4", "operation": "teamId = baseLineTeamIds[baseLineIndex]"},
                {"offset": "0xb9", "condition": "teamId != 0"},
                {"offset": "0x152", "call": "TeamData.get_IsEnable", "required": True},
                {"offset": "0x168", "call": "TeamData.get_IsCullingInvisible", "required": False},
                {"offset": "0x206", "operation": "childCount = baseLineDataCounts[baseLineIndex]"},
                {"offset": "0x20b", "condition": "childCount != 0"},
            ],
            "numericBoundary": "The child traversal and normal/tangent math after offset 0x245 remain code-only disassembly targets; no capture-derived vector or curve is substituted.",
        },
        "routeEvidence": {"coldSpans": cold,
                          "classification": "Both parallel/cross-frame scheduling helpers and managed-worker fallback paths are present; static code alone does not select the runtime branch."},
        "openWorkerTargets": workers,
        "nextDisassemblyTargets": [
            {"methodIndex": 384856, "method": "CalcLineNormalTangentKernel$BurstManaged",
             "reason": "continue after the closed entry gates to recover child traversal, line normal/tangent equations, and degeneracy branches from code"},
        ],
        "nonClaims": [
            "The older 80-bone capture is not an implementation input and supplies no positions, timing, curves, or fitted constants.",
            "CreatePostProxyMeshUpdateList queue control flow is closed, but CalcLineNormalTangent vector equations remain unresolved.",
            "The presence of multiple schedule/fallback helpers does not establish which runtime branch is selected.",
            "This static contract is not a Unity execution or retail-equivalence result.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--metadata-evidence", type=Path, default=DEFAULT_METADATA_EVIDENCE)
    parser.add_argument("--native-evidence", type=Path, default=DEFAULT_NATIVE_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_contract(game_assembly=args.game_assembly, metadata=args.metadata,
                             metadata_evidence=args.metadata_evidence, native_evidence=args.native_evidence)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == encoded
        print(json.dumps({"status": payload["status"], "matches": matches, "output": str(args.output)}))
        return 0 if matches else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": payload["status"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, ValueError, KeyError, IndexError, StopIteration) as exc:
        print(f"secondary dynamics PostProxy unavailable: {exc}", file=sys.stderr)
        raise SystemExit(2)
