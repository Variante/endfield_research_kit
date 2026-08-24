#!/usr/bin/env python3
"""Build the pinned unpatched secondary-dynamics scheduling contract.

This closes managed job order, master-handle completion, and TransformAccess
writeback construction/scheduling.  It deliberately does not claim IFix
selection, Burst kernel identity, solver numerics, or executed Unity parity.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from capstone import Cs, CS_ARCH_X86, CS_MODE_64


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_schedule_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


METHODS = (
    {
        "methodIndex": 385474, "token": "0x0600078b",
        "type": "BeyondDynamicBone.SimulationManager", "method": "SimulationStepUpdate",
        "startVa": 0x182F8F430, "endVa": 0x182F90B80, "fileOffset": 0x2F8DA30,
        "sha256": "5106aa8354dfe1d73e8a4ecb6a693cf8586938da5d456f7fc748267e08743335",
        "firstRetOffset": 0x14EB,
    },
    {
        "methodIndex": 384432, "token": "0x06000379",
        "type": "BeyondDynamicBone.ClothManager", "method": "CompleteMasterJob",
        "startVa": 0x182F95120, "endVa": 0x182F95240, "fileOffset": 0x2F93720,
        "sha256": "25b200c3a3658e744fcfb7f3d08f21530ad26e9ac3d88e120c12b2a58d34a66d",
        "firstRetOffset": 0x74,
    },
    {
        "methodIndex": 384497, "token": "0x060003ba",
        "type": "BeyondDynamicBone.DynamicBoneTransformManager", "method": "WriteTransform",
        "startVa": 0x18672641C, "endVa": 0x186726644, "fileOffset": 0x6724A1C,
        "sha256": "0d2bd0087b25250cd8d88bf8325bbc9bac4da0b58622537e4891dc8fb5acd0f7",
        "firstRetOffset": 0x227,
    },
)

JOBS = (
    ("ClearStepCounter", 204173, 0x1837358F0, 483781, 516766, 22160, None, None, 0x372, 0x37F, 0x38D, 0x391, 0x396, 0x3B0),
    ("CreateUpdateParticleList", 204175, 0x1837359A0, 483782, 516767, 22161, 0x18E30D858, 0x183BB6810, 0x763, 0x770, 0x77E, 0x782, 0x787, 0x7A1),
    ("StartSimulationStepJob", 204183, 0x1837359A0, 483785, 516770, 22051, 0x18E30D868, 0x183BB8790, 0xC16, 0xC23, 0xC31, 0xC35, 0xC3A, 0xC54),
    ("UpdateStepBasicPotureJob", 204185, 0x1837359A0, 483786, 516771, 22052, 0x18E30D838, 0x183BB5120, 0xF50, 0xF5D, 0xF6B, 0xF6F, 0xF74, 0xF8E),
    ("EndSimulationStepJob", 204177, 0x1837359A0, 483783, 516768, 22048, 0x18E30D848, 0x183BBB010, 0x143D, 0x144A, 0x1458, 0x145C, 0x1461, 0x147B),
)

MANAGER_FIELDS = (
    ("flagArray", 229451, 0x10), ("positionArray", 229454, 0x28),
    ("lastpositionArray", 229455, 0x30), ("rotationArray", 229456, 0x38),
    ("lastrotationArray", 229457, 0x40), ("localPositionArray", 229459, 0x50),
    ("lastlocalPositionArray", 229460, 0x58), ("localRotationArray", 229461, 0x60),
    ("lastlocalRotationArray", 229462, 0x68), ("teamIdArray", 229464, 0x78),
    ("transformAccessArray", 229465, 0x80),
)
TEAM_FIELDS = (("teamDataArray", 229581, 0x10),)
JOB_FIELDS = (
    ("flagList", 229531, 0x00), ("lastpositionArray", 229532, 0x10),
    ("lastrotationArray", 229533, 0x20), ("lastlocalPositionArray", 229534, 0x30),
    ("lastlocalRotationArray", 229535, 0x40), ("teamIdArray", 229536, 0x50),
    ("teamDataArray", 229537, 0x60),
)
WRITE_SOURCES = (
    ("flagArray", 0x10, "flagList", 0x00, 0xD4, 0xE1, 0x186),
    ("positionArray", 0x28, "lastpositionArray", 0x10, 0xE6, 0xF3, 0x18C),
    ("rotationArray", 0x38, "lastrotationArray", 0x20, 0xF8, 0x105, 0x192),
    ("localPositionArray", 0x50, "lastlocalPositionArray", 0x30, 0x10A, 0x117, 0x198),
    ("localRotationArray", 0x60, "lastlocalRotationArray", 0x40, 0x11B, 0x128, 0x19C),
    ("teamIdArray", 0x78, "teamIdArray", 0x50, 0x12C, 0x140, 0x1A0),
    ("TeamManager.teamDataArray", 0x10, "teamDataArray", 0x60, 0x156, 0x15F, 0x17C),
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
    return (_load("schedule_metadata", root / "catalog_option_flow_metadata.py"),
            _load("schedule_native", root / "map_body_targets_to_gameassembly.py"))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _first_ret_offset(body: bytes, start_va: int) -> int:
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    for instruction in decoder.disasm(body, start_va):
        if instruction.mnemonic.startswith("ret"):
            return instruction.address - start_va
    raise ContractError(f"no decoded RET at 0x{start_va:x}")


def _gate(game_assembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    result = check_installed_native_inputs(EXPECTED_GAME_ASSEMBLY_SHA256, EXPECTED_METADATA_SHA256,
                                           gameassembly=game_assembly, metadata=metadata)
    if not result.validated:
        raise ContractError(f"native gate [{result.status}]: {result.detail}")
    ga, md = Path(result.gameassembly), Path(result.metadata)
    return {"gameAssembly": {"path": _repo_path(ga), "size": ga.stat().st_size, "sha256": result.gameassembly_sha256},
            "globalMetadata": {"path": _repo_path(md), "size": md.stat().st_size, "sha256": result.metadata_sha256}}


def _method_rows(md: Any, native: Any, pe: Any, code_registration: int) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    pointers, _ = native.build_pointer_indexes(pe, md, modules, ranges)
    bone = pointers["BeyondDynamicBone.dll"]
    method_start = ranges["BeyondDynamicBone.dll"]["methodStart"]
    unique = sorted({pointer for pointer in bone if pointer})
    rows = []
    for expected in METHODS:
        method = md.methods[expected["methodIndex"]]
        signature = native.method_signature(md, expected["methodIndex"])
        pointer = bone[expected["methodIndex"] - method_start]
        end = next(value for value in unique if value > pointer)
        body = pe.bytes_at_va(pointer, end - pointer)
        file_offset, section, _ = pe.file_offset_for_va(pointer)
        actual = {
            "methodIndex": expected["methodIndex"], "token": f"0x{method.token:08x}",
            "type": signature["type"], "method": signature["method"],
            "startVa": f"0x{pointer:x}", "endVa": f"0x{end:x}", "spanBytes": end - pointer,
            "fileOffset": f"0x{file_offset:x}", "section": section,
            "bodySha256": hashlib.sha256(body).hexdigest(),
            "firstRetOffset": f"0x{_first_ret_offset(body, pointer):x}",
        }
        wanted = (expected["token"], expected["type"], expected["method"], expected["startVa"], expected["endVa"],
                  expected["fileOffset"], expected["sha256"], expected["firstRetOffset"])
        got = (actual["token"], actual["type"], actual["method"], pointer, end, file_offset,
               actual["bodySha256"], _first_ret_offset(body, pointer))
        if got != wanted:
            raise ContractError(f"authoritative method drift for {expected['method']}: {got}")
        rows.append(actual)
    return rows, pointers


def _field_offsets(md: Any, pe: Any, registration: dict[str, Any], type_index: int,
                   expected: tuple[tuple[str, int, int], ...], *, value_type: bool = False) -> list[dict[str, Any]]:
    table = int(registration["fieldOffsets"], 16)
    type_table = pe.u64_at_va(table + type_index * 8)
    typedef = md.types[type_index]
    rows = []
    for name, field_index, offset in expected:
        ordinal = field_index - typedef.field_start
        if ordinal < 0 or ordinal >= typedef.field_count or md.string(md.fields[field_index].name_index) != name:
            raise ContractError(f"field identity drift: {type_index} {name}")
        actual = pe.u32_at_va(type_table + ordinal * 4)
        wanted = offset + 0x10 if value_type else offset
        if actual != wanted:
            raise ContractError(f"field offset drift: {name} 0x{actual:x} != 0x{wanted:x}")
        rows.append({"name": name, "fieldIndex": field_index,
                     "boxedFieldOffset": f"0x{actual:x}",
                     "nativePayloadOffset": f"0x{offset:x}" if value_type else None})
    return rows


def _generic_rows(md: Any, native: Any, pe: Any, code_registration: int, metadata_registration: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    index = native.build_generic_method_index(pe, md, code_registration, metadata_registration)
    jobs = []
    for order, row in enumerate(JOBS, 1):
        name, type_index, pointer, slot, spec_index, inst_index, type_slot, setter, reflection, icall_load, mode, dep, zero, call = row
        matches = [item for item in index.get(pointer, []) if item["methodIndex"] == 401847 and item["methodSpecIndex"] == spec_index]
        if len(matches) != 1:
            raise ContractError(f"GetReflectionData MethodSpec drift for {name}: {matches}")
        item = matches[0]
        arg = item["methodInstantiation"]
        if (item["token"], item["genericMethodPointerSlot"], arg["genericInstIndex"],
                arg["arguments"][0].get("typeIndex"), arg["arguments"][0].get("typeName")) != (
                "0x0600003e", slot, inst_index, type_index, f"BeyondDynamicBone.SimulationManager+{name}"):
            raise ContractError(f"GetReflectionData generic identity drift for {name}")
        jobs.append({"order": order, "jobType": f"BeyondDynamicBone.SimulationManager+{name}",
                     "jobTypeIndex": type_index, "getReflectionDataMethodSpecIndex": spec_index,
                     "genericMethodPointerSlot": slot, "methodInstantiationGenericInstIndex": inst_index,
                     "genericEntryVa": f"0x{pointer:x}",
                     "typeInfoSlotVa": f"0x{type_slot:x}" if type_slot else None,
                     "setIndexCountVa": f"0x{setter:x}" if setter else None,
                     "offsets": {"getReflectionData": f"0x{reflection:x}", "icallSlotLoad": f"0x{icall_load:x}",
                                 "scheduleModeStore": f"0x{mode:x}", "dependencyStore": f"0x{dep:x}",
                                 "outputZero": f"0x{zero:x}", "indirectScheduleCall": f"0x{call:x}"}})

    schedule_matches = [item for item in index.get(0x183B12D60, [])
                        if item["methodIndex"] == 406978 and item["methodSpecIndex"] == 517387]
    if len(schedule_matches) != 1:
        raise ContractError("WriteTransform Schedule<T> MethodSpec drift")
    schedule = schedule_matches[0]
    arg = schedule["methodInstantiation"]
    if (schedule["token"], schedule["genericMethodPointerSlot"], arg["genericInstIndex"],
            arg["arguments"][0].get("typeIndex"), arg["arguments"][0].get("typeName")) != (
            "0x06001449", 484375, 28355, 188650,
            "BeyondDynamicBone.DynamicBoneTransformManager+WriteTransformJob"):
        raise ContractError("WriteTransform Schedule<T> generic identity drift")
    return jobs, {"methodSpecIndex": 517387, "genericMethodPointerSlot": 484375,
                  "methodInstantiationGenericInstIndex": 28355, "jobTypeIndex": 188650,
                  "jobType": arg["arguments"][0]["typeName"]}


def _body_record(pe: Any, start: int, size: int, expected_hash: str, first_ret: int) -> dict[str, Any]:
    body = pe.bytes_at_va(start, size)
    digest = hashlib.sha256(body).hexdigest()
    if digest != expected_hash or _first_ret_offset(body, start) != first_ret:
        raise ContractError(f"body drift at 0x{start:x}: {digest}")
    return {"startVa": f"0x{start:x}", "endVa": f"0x{start + size:x}", "spanBytes": size,
            "bodySha256": digest, "firstRetOffset": f"0x{first_ret:x}"}


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
                   metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate = _gate(game_assembly, metadata)
    catalog, native = _helpers()
    md = catalog.Metadata(Path(gate["globalMetadata"]["path"]))
    pe = native.PeImage(Path(gate["gameAssembly"]["path"]))
    names = {md.string(image.name_index) for image in md.images}
    code = native.find_code_registration(pe, names)
    meta = native.find_metadata_registration(pe, code)
    if (code, meta) != (EXPECTED_CODE_REGISTRATION, EXPECTED_METADATA_REGISTRATION):
        raise ContractError(f"registration drift: {code!r}, {meta!r}")
    registration = native.metadata_registration_summary(pe, meta)
    methods, _ = _method_rows(md, native, pe, code)
    jobs, transform_spec = _generic_rows(md, native, pe, code, meta)
    manager_fields = _field_offsets(md, pe, registration, 48218, MANAGER_FIELDS)
    team_fields = _field_offsets(md, pe, registration, 48248, TEAM_FIELDS)
    job_fields = _field_offsets(md, pe, registration, 48216, JOB_FIELDS, value_type=True)
    for va, literal in ((0x18B8C7EA0, "Unity.Jobs.LowLevel.Unsafe.JobsUtility::ScheduleCrossFrameJob_Injected(Unity.Jobs.LowLevel.Unsafe.JobsUtility/JobScheduleParameters&,Unity.Jobs.LowLevel.Unsafe.JobQueuePriority,Unity.Jobs.JobHandle&)"),
                        (0x18B8FB930, "Unity.Jobs.JobHandle::ScheduleBatchedCrossFrameJobsAndComplete(Unity.Jobs.JobHandle&)"),
                        (0x18B8C84E0, "Unity.Jobs.LowLevel.Unsafe.JobsUtility::ScheduleParallelForTransform_Injected(Unity.Jobs.LowLevel.Unsafe.JobsUtility/JobScheduleParameters&,System.IntPtr,Unity.Jobs.JobHandle&)")):
        if pe.c_string_at_va(va) != literal:
            raise ContractError(f"icall literal drift at 0x{va:x}")
    wrapper = _body_record(pe, 0x1803698C8, 0x76,
                           "84d0c36acbe0b117db909abe436a6a90e5786e7077bad4753207c2c3e628d255", 0x75)
    generic = _body_record(pe, 0x183B12D60, 0xF0,
                           "891f42acb49be0849ff45440f1b272489211db8b86220305a658fa2f4a1d3095", 0xBE)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-schedule.v1",
        "status": "unpatched_schedule_and_transform_access_writeback_closed",
        "cross_frame_schedule_closed": True, "schedule_completion_closed": True,
        "transform_write_job_construction_closed": True, "transform_access_schedule_closed": True,
        "ifix_patched_route_closed": False, "solver_numerics_recovered": False,
        "unity_runtime_executed": False, "secondary_dynamics_verified": False,
        "nativeGate": gate,
        "registrations": {"codeRegistrationVa": f"0x{code:x}", "metadataRegistrationVa": f"0x{meta:x}"},
        "authoritativeMethods": methods,
        "ifixBoundary": {
            "SimulationStepUpdate": {"patchId": "0x31a", "comparisonOffset": "0x7a", "patchedTargetVa": "0x184f738c0"},
            "WriteTransform": {"patchId": "0x32a", "immediateOffset": "0xb2", "isPatchedCallOffset": "0xb7", "patchedBranchOffset": "0xbe", "patchedTargetVa": "0x1867265c8"},
            "classification": "all schedule claims are exact only for the unpatched native route",
        },
        "simulationStepUpdate": {
            "scheduleModeLane": 2, "scheduleModeSetOffset": "0x2be", "priority": 0,
            "icallSlotVa": "0x18f36ee88", "icallLiteralVa": "0x18b8c7ea0", "resolverVa": "0x180059fc0",
            "jobs": jobs,
            "boundary": "The ordered managed schedule and dependency chain are closed; scheduled Burst kernel bodies remain unresolved.",
        },
        "completeMasterJob": {
            "masterHandleObjectOffset": "0x38", "nonzeroCompareOffset": "0x5c",
            "clear16ByteOffset": "0x6b", "icallSlotLoadOffset": "0x75", "icallSlotVa": "0x18f36ee28",
            "handleAddressOffset": "0x81", "indirectCallOffset": "0x85", "coldLiteralOffset": "0xa8",
            "icallLiteralVa": "0x18b8fb930", "resolverCallOffset": "0xaf", "resolverVa": "0x180059ea0",
            "slotStoreOffset": "0xb4", "boundary": "Completes the exact ClothManager master handle and clears all 16 bytes.",
        },
        "writeTransform": {
            "managerFields": manager_fields, "teamManagerFields": team_fields, "jobFields": job_fields,
            "jobSizeBytes": 0x70, "zeroAddressOffset": "0xc6", "zeroSizeOffset": "0xcb", "memsetCallOffset": "0xcf",
            "sources": [{"source": source, "sourceObjectOffset": f"0x{source_offset:x}", "jobField": dest,
                         "jobPayloadOffset": f"0x{dest_offset:x}", "sourceLoadOffset": f"0x{load:x}",
                         "payloadLoadOffset": f"0x{payload:x}", "jobStoreOffset": f"0x{store:x}"}
                        for source, source_offset, dest, dest_offset, load, payload, store in WRITE_SOURCES],
            "currentVersusLastBoundary": "Job lastposition/rotation/local fields receive the manager's current arrays; manager last* arrays are unused.",
            "transformAccessArrayObjectOffset": "0x80", "transformAccessLoadOffset": "0x163",
            "dependencyLoadOffset": "0x16f", "dependencyStoreOffset": "0x16f", "wrapperCallOffset": "0x1a5",
            "concreteWrapper": {**wrapper, "hiddenMethodInfoSlotVa": "0x18e2fa2f0", "hiddenSlotLoadOffset": "0x59",
                                "hiddenArgumentStoreOffset": "0x60", "genericScheduleCallOffset": "0x65"},
            "genericSchedule": {**generic, **transform_spec, "getReflectionDataCallOffset": "0x56",
                                "scheduleModeLane": 1, "scheduleModeStoreOffset": "0x6e",
                                "icallSlotLoadOffset": "0x76", "icallSlotVa": "0x18f36eea0",
                                "indirectCallOffset": "0x97", "icallLiteralOffset": "0xcc",
                                "icallLiteralVa": "0x18b8c84e0", "resolverCallOffset": "0xd3",
                                "resolverVa": "0x180059fc0", "slotStoreOffset": "0xe1"},
        },
        "nonClaims": [
            "IFix patch activity and targets are not audited.",
            "The Burst solver kernels and their numeric equations are not recovered by this contract.",
            "Static native scheduling evidence is not a Unity runtime execution or retail-equivalence result.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
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
    except (ContractError, OSError, ValueError, KeyError, IndexError) as exc:
        print(f"secondary dynamics schedule unavailable: {exc}", file=sys.stderr)
        raise SystemExit(2)
