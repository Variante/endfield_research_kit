#!/usr/bin/env python3
"""Build the pinned secondary-dynamics substep accumulator/count contract."""

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
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_substep_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

CALLBACK_CONTRACT = SOURCE_ROOT / "secondary_dynamics_callback_contract.json"
SCHEDULE_CONTRACT = SOURCE_ROOT / "secondary_dynamics_schedule_contract.json"
TIME_CONTRACT = SOURCE_ROOT / "secondary_dynamics_time_manager_contract.json"

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

METHODS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (384441, "BeyondDynamicBone.ClothManager", "ClothUpdate", 0x182F918A0, 6256,
     "a1065dd5aaa62d715dc756e8ce87a4630d629d303494df34fb9d949b2231d077"),
    (384596, "BeyondDynamicBone.TeamManager", "AlwaysTeamUpdate", 0x1835BEA60, 14288,
     "ed476f614553028a2543f094526aaf370f9c2975bbb49b872eb17d43e6c0ca88"),
    (384599, "BeyondDynamicBone.TeamManager", "SimulationStepTeamUpdate", 0x182F8E3A0, 880,
     "a0031b5d80a0f3ef008aeea3a5f4cbd3a9b7d16cbd6370d6b28e8da7112138ed"),
    (385474, "BeyondDynamicBone.SimulationManager", "SimulationStepUpdate", 0x182F8F430, 5968,
     "5106aa8354dfe1d73e8a4ecb6a693cf8586938da5d456f7fc748267e08743335"),
    (385741, "BeyondDynamicBone.TimeManager", "FrameUpdate", 0x1834460C0, 448,
     "7a539536c6ac6431798cbb2cd35fc0601e4af158b620f2cafe26baeb7de2b863"),
    (385743, "BeyondDynamicBone.TimeManager", ".ctor", 0x184D87460, 32,
     "a892c8d0275f9a1665d104b60f0cda87628a3b0dd2a49158a2a377297d787d63"),
    (384711, "BeyondDynamicBone.TeamManager+AlwaysTeamUpdatePostJob", "Execute", 0x186733450, 2440,
     "54845866e2a08ec3f0d14a88960cb4ac64b7e54fdcfbf9b337f635ed885207f5"),
    (384614, "BeyondDynamicBone.TeamManager+SimulationStepTeamUpdateKernels",
     "SimulationStepTeamUpdateKernel$BurstManaged", 0x186727F20, 3424,
     "b5a49b1d2726d050c11d0eb4d9ae7cd99ab7baa96298887bbee8497e198619c7"),
    (384683, "BeyondDynamicBone.TeamManager+TeamData", "get_IsFixedUpdate", 0x18673DC38, 80,
     "977845151c99991f48d8068bc836881455d36bf895bd836631278572c7d7bad5"),
    (384684, "BeyondDynamicBone.TeamManager+TeamData", "get_IsUnscaled", 0x18673DFE4, 80,
     "0c4704f036eeff8b5978fdaaceb51e9896fca0046883ded43a923676f0206d13"),
    (384686, "BeyondDynamicBone.TeamManager+TeamData", "get_IsEnable", 0x1837EBD60, 96,
     "6319cec0b90302415f3cbf7a8d85fec1735de8c31836ee7cfd660763bad790ef"),
    (384697, "BeyondDynamicBone.TeamManager+TeamData", "get_IsCullingInvisible", 0x18673DB7C, 104,
     "dead8c860e4a34609cb117c83d7ad01c0f43f3cece57415297554311c264d81d"),
)

EQUATION_SPANS: tuple[tuple[str, int, int, str], ...] = (
    ("alwaysPostAccumulatorAndClamp", 0x186733AB8, 239,
     "9f63ac61d0207d69b19158d71e8e4d61f0816bd4be882a7cf7a5c2abaa4abdd5"),
    ("alwaysPostMaximumReduction", 0x186733C93, 55,
     "e17313c642cce94e7b94052f45b03e1f89dfdd99d4bbc98c92c235efcc93d3f6"),
    ("alwaysPostMaximumStore", 0x186733D81, 7,
     "ed4f2162511e6e34f1773287475c7c9b6362a7e8b45551a67e483d1aaa4ffcb6"),
    ("stepKernelGateAndClockAdvance", 0x186728096, 254,
     "fcb7a71d443f93a2db13acb47a928b4ba98b8c09ee196d3ce440ccf4bcd3e801"),
    ("clothUpdateSolverLoop", 0x182F920D7, 76,
     "39b295ef20f6a8ef8207962d3e79b27b33b439e8a628f53a2b090d46a6cf5e1b"),
    ("alwaysPostJobScalarConstruction", 0x1835C1401, 90,
     "3ac139e757e43380eedba389b735b54a835c597bbf7f75ff72cd4f66666ee156"),
)

TYPE_FIELDS: tuple[tuple[str, int, tuple[tuple[str, int, int], ...]], ...] = (
    ("BeyondDynamicBone.TimeManager", 48430, (
        ("simulationFrequency", 230469, 0x10),
        ("maxSimulationCountPerFrame", 230470, 0x14),
        ("FixedUpdateCount", 230473, 0x20),
        ("GlobalTimeScale", 230474, 0x24),
        ("SimulationDeltaTime", 230475, 0x28),
        ("MaxDeltaTime", 230476, 0x2C),
    )),
    ("BeyondDynamicBone.TeamManager", 48248, (
        ("teamDataArray", 229581, 0x10),
        ("maxUpdateCount", 229585, 0x30),
    )),
    ("BeyondDynamicBone.TeamManager+AlwaysTeamUpdatePostJob", 48236, (
        ("teamCount", 229722, 0x0),
        ("unityFrameDeltaTime", 229723, 0x4),
        ("unityFrameFixedDeltaTime", 229724, 0x8),
        ("unityFrameUnscaledDeltaTime", 229725, 0xC),
        ("globalTimeScale", 229726, 0x10),
        ("simulationDeltaTime", 229727, 0x14),
        ("maxSimmulationCountPerFrame", 229728, 0x18),
        ("maxUpdateCount", 229729, 0x20),
        ("teamDataArray", 229730, 0x30),
    )),
    ("BeyondDynamicBone.TeamManager+SimulationStepTeamUpdateJob", 48245, (
        ("updateIndex", 229764, 0x0),
        ("simulationDeltaTime", 229765, 0x4),
        ("teamDataArray", 229766, 0x8),
    )),
    ("BeyondDynamicBone.TeamManager+TeamData", 48233, (
        ("flag", 229636, 0x0),
        ("originalUpdateMode", 229637, 0x8),
        ("updateMode", 229638, 0xC),
        ("frameDeltaTime", 229639, 0x10),
        ("time", 229640, 0x14),
        ("oldTime", 229641, 0x18),
        ("nowUpdateTime", 229642, 0x1C),
        ("oldUpdateTime", 229643, 0x20),
        ("frameUpdateTime", 229644, 0x24),
        ("frameOldTime", 229645, 0x28),
        ("timeScale", 229646, 0x2C),
        ("nowTimeScale", 229647, 0x30),
        ("updateCount", 229648, 0x34),
        ("skipCount", 229649, 0x38),
        ("frameInterpolation", 229650, 0x3C),
        ("resetSimulationToAnimationPose", 229672, 0xEC),
    )),
)

CONSTANTS = (
    ("one", 0x18B959200, 1.0),
    ("zero", 0x18B959220, 0.0),
    ("pausedClockEpsilon", 0x18B9592C0, 9.999999747378752e-05),
)

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
        _load("secondary_substep_metadata", root / "catalog_option_flow_metadata.py"),
        _load("secondary_substep_native", root / "map_body_targets_to_gameassembly.py"),
    )


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file(path: Path, digest: str) -> dict[str, Any]:
    return {"path": _repo_path(path), "size": path.stat().st_size, "sha256": digest}


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def advance_normal_team(
    *, time: float, now_update_time: float, frame_delta_time: float,
    simulation_delta_time: float, max_count: int,
) -> tuple[int, int, float, float]:
    """Execute the recovered normal/scaled accumulator and solver clock update."""

    candidate = _f32(_f32(time) + _f32(frame_delta_time))
    ratio = _f32(_f32(candidate - _f32(now_update_time)) / _f32(simulation_delta_time))
    raw = int(ratio)
    update_count = min(raw, max_count)
    skip_count = raw - update_count
    if skip_count > 0:
        candidate = _f32(candidate - _f32(_f32(float(skip_count)) * _f32(simulation_delta_time)))
    for _ in range(max(update_count, 0)):
        now_update_time = _f32(_f32(now_update_time) + _f32(simulation_delta_time))
    return update_count, skip_count, candidate, _f32(now_update_time)


def _ordinary_trace(frame_count: int) -> dict[str, Any]:
    frame_dt = _f32(1.0 / 60.0)
    simulation_dt = _f32(1.0 / 90.0)
    time = _f32(0.0)
    now = _f32(0.0)
    counts: list[int] = []
    for _ in range(frame_count):
        count, _, time, now = advance_normal_team(
            time=time,
            now_update_time=now,
            frame_delta_time=frame_dt,
            simulation_delta_time=simulation_dt,
            max_count=3,
        )
        counts.append(count)
    return {
        "initialState": {"time": 0.0, "nowUpdateTime": 0.0},
        "frameDeltaTimeFloat32": frame_dt,
        "simulationDeltaTimeFloat32": simulation_dt,
        "counts": counts,
        "totalSolverSteps": sum(counts),
        "finalTime": time,
        "finalNowUpdateTime": now,
    }


def _load_source_contract(path: Path, schema: str, status: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"source contract unavailable: {path}: {exc}") from exc
    if payload.get("schema") != schema or payload.get("status") != status:
        raise ContractError(f"source contract schema/status drift: {path}")
    native = payload.get("native_gate") or payload.get("nativeGate") or {}
    game = native.get("gameAssembly") or {}
    metadata = native.get("globalMetadata") or {}
    if game.get("sha256") != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError(f"source contract GameAssembly drift: {path}")
    if metadata.get("sha256") != EXPECTED_METADATA_SHA256:
        raise ContractError(f"source contract metadata drift: {path}")
    return payload, {"path": _repo_path(path), "schema": schema, "status": status}


def _field_rows(md: Any, pe: Any, registration: dict[str, Any]) -> list[dict[str, Any]]:
    table = int(registration["fieldOffsets"], 16)
    result: list[dict[str, Any]] = []
    for type_name, type_index, expected_fields in TYPE_FIELDS:
        type_def = md.types[type_index]
        if md.type_full_name(type_def) != type_name:
            raise ContractError(f"type identity drift: {type_index} {type_name}")
        pointer = pe.u64_at_va(table + type_index * 8)
        if not pointer:
            raise ContractError(f"field-offset table missing: {type_name}")
        rows = []
        for name, field_index, native_offset in expected_fields:
            ordinal = field_index - type_def.field_start
            if ordinal < 0 or ordinal >= type_def.field_count:
                raise ContractError(f"field ordinal drift: {type_name}.{name}")
            field = md.fields[field_index]
            if md.string(field.name_index) not in (name, f"<{name}>k__BackingField"):
                raise ContractError(f"field identity drift: {type_name}.{name}")
            boxed = pe.u32_at_va(pointer + ordinal * 4)
            expected_boxed = native_offset if type_name in (
                "BeyondDynamicBone.TimeManager", "BeyondDynamicBone.TeamManager"
            ) else native_offset + 0x10
            if boxed != expected_boxed:
                raise ContractError(
                    f"field offset drift: {type_name}.{name}: 0x{boxed:x} != 0x{expected_boxed:x}"
                )
            rows.append({
                "name": name,
                "fieldIndex": field_index,
                "boxedFieldOffset": f"0x{boxed:x}",
                "nativePayloadOffset": None if expected_boxed == native_offset else f"0x{native_offset:x}",
            })
        result.append({"type": type_name, "typeIndex": type_index, "fields": rows})
    return result


def build_contract(
    *, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
) -> dict[str, Any]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not gate.validated:
        raise ContractError(f"common.check_installed_native_inputs [{gate.status}]: {gate.detail}")

    callback, callback_record = _load_source_contract(
        CALLBACK_CONTRACT,
        "endfield.charinfo.secondary-dynamics-callback-writeback.v1",
        "native_callback_writeback_closed",
    )
    schedule, schedule_record = _load_source_contract(
        SCHEDULE_CONTRACT,
        "endfield.charinfo.secondary-dynamics-schedule.v1",
        "unpatched_schedule_and_transform_access_writeback_closed",
    )
    time_contract, time_record = _load_source_contract(
        TIME_CONTRACT,
        "endfield.charinfo.secondary-dynamics-time-manager.v1",
        "retail_default_step_scalars_closed_nondefault_power_helper_unported",
    )
    selectors = callback.get("simulationSelectors") or {}
    if selectors.get("mutuallyExclusiveWholePipeline") is not True:
        raise ContractError("callback pipeline selector drift")
    scheduled = next(
        (row for row in schedule.get("authoritativeMethods", [])
         if row.get("methodIndex") == 385474),
        None,
    )
    if not scheduled or scheduled.get("bodySha256") != METHODS[3][5]:
        raise ContractError("schedule SimulationStepUpdate identity drift")
    if time_contract.get("constructorDefaults") != {
        "simulationFrequency": 90,
        "maxSimulationCountPerFrame": 3,
        "GlobalTimeScale": 1.0,
    }:
        raise ContractError("TimeManager retail defaults drift")

    game_path = Path(gate.gameassembly)
    metadata_path = Path(gate.metadata)
    catalog, native = _helpers()
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    code_registration = native.find_code_registration(
        pe, {md.string(image.name_index) for image in md.images}
    )
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(f"code registration drift: 0x{code_registration:x}")
    if metadata_registration != EXPECTED_METADATA_REGISTRATION:
        raise ContractError(f"metadata registration drift: 0x{metadata_registration:x}")
    modules = native.parse_codegen_modules(pe, code_registration)
    _, by_pointer = native.build_pointer_indexes(
        pe, md, modules, native.image_method_ranges(md)
    )
    pointers = sorted(pointer for pointer in by_pointer if pointer)

    method_rows = []
    for method_index, type_name, method_name, expected_va, expected_size, expected_hash in METHODS:
        matches = [
            (pointer, row)
            for pointer, rows in by_pointer.items()
            for row in rows
            if int(row.get("methodIndex", -1)) == method_index
        ]
        if len(matches) != 1:
            raise ContractError(f"method {method_index} resolves to {len(matches)} pointers")
        pointer, identity = matches[0]
        next_index = bisect.bisect_right(pointers, pointer)
        if next_index >= len(pointers):
            raise ContractError(f"method {method_index} has no next method boundary")
        end = pointers[next_index]
        body = pe.bytes_at_va(pointer, end - pointer)
        digest = hashlib.sha256(body).hexdigest()
        if (identity.get("type"), identity.get("method")) != (type_name, method_name):
            raise ContractError(f"method identity drift: {method_index}")
        if (pointer, len(body), digest) != (expected_va, expected_size, expected_hash):
            raise ContractError(f"native body drift: {type_name}::{method_name}")
        method_rows.append({
            "methodIndex": method_index,
            "token": identity["token"],
            "type": type_name,
            "method": method_name,
            "startVa": f"0x{pointer:x}",
            "endVa": f"0x{end:x}",
            "spanBytes": len(body),
            "sha256": digest,
        })

    span_rows = []
    for name, start, size, expected_hash in EQUATION_SPANS:
        data = pe.bytes_at_va(start, size)
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_hash:
            raise ContractError(f"equation span drift: {name}")
        span_rows.append({
            "name": name,
            "startVa": f"0x{start:x}",
            "endVa": f"0x{start + size:x}",
            "spanBytes": size,
            "sha256": digest,
        })

    constant_rows = []
    for name, address, expected in CONSTANTS:
        raw = pe.bytes_at_va(address, 4)
        value = struct.unpack("<f", raw)[0]
        if raw != struct.pack("<f", expected):
            raise ContractError(f"constant drift: {name}")
        constant_rows.append({"name": name, "va": f"0x{address:x}", "bits": raw.hex(), "value": value})

    registration = native.metadata_registration_summary(pe, metadata_registration)
    layouts = _field_rows(md, pe, registration)
    trace12 = _ordinary_trace(12)
    trace60 = _ordinary_trace(60)
    trace1200 = _ordinary_trace(1200)
    if set(trace1200["counts"]) != {1, 2} or trace1200["totalSolverSteps"] != 1800:
        raise ContractError("ordinary 60 fps float32 trace drift")

    return {
        "schema": "endfield.charinfo.secondary-dynamics-substep.v1",
        "status": "pinned_unpatched_substep_accumulator_count_and_solver_loop_closed",
        "nativeGate": {
            "gameAssembly": _file(game_path, gate.gameassembly_sha256),
            "globalMetadata": _file(metadata_path, gate.metadata_sha256),
            "codeRegistrationVa": f"0x{code_registration:x}",
            "metadataRegistrationVa": f"0x{metadata_registration:x}",
        },
        "sourceContracts": [callback_record, schedule_record, time_record],
        "nativeMethods": method_rows,
        "equationSpans": span_rows,
        "constants": constant_rows,
        "fieldAndArrayProvenance": {
            "layouts": layouts,
            "flow": [
                "TimeManager.FrameUpdate writes SimulationDeltaTime/MaxDeltaTime and clamps configuration.",
                "TeamManager.AlwaysTeamUpdate constructs AlwaysTeamUpdatePostJob from TimeManager and Unity time sources.",
                "AlwaysTeamUpdatePostJob reads/writes TeamManager.teamDataArray and reduces active per-team updateCount into TeamManager.maxUpdateCount.",
                "ClothManager.ClothUpdate reads *TeamManager.maxUpdateCount and calls SimulationManager.SimulationStepUpdate(updateCount=maxUpdateCount, updateIndex=i) for i in [0,maxUpdateCount).",
                "SimulationStepUpdate schedules TeamManager.SimulationStepTeamUpdate; its kernel executes a team only when updateIndex < TeamData.updateCount.",
            ],
            "alwaysPostJobScalarSources": {
                "teamCount": "TeamManager.get_TeamCount()",
                "unityFrameDeltaTime": "TimeManager.GetDeltaTime()",
                "unityFrameFixedDeltaTime": "float32(TimeManager.FixedUpdateCount * TimeManager.GetFixedDeltaTime())",
                "unityFrameUnscaledDeltaTime": "TimeManager.GetUnscaledDeltaTime()",
                "globalTimeScale": "TimeManager.GlobalTimeScale",
                "simulationDeltaTime": "TimeManager.SimulationDeltaTime",
                "maxSimmulationCountPerFrame": "TimeManager.maxSimulationCountPerFrame",
                "maxUpdateCount": "TeamManager.maxUpdateCount NativeReference<int>",
                "teamDataArray": "TeamManager.teamDataArray NativeArray<TeamData>",
            },
        },
        "frameUpdate": {
            "configurationClampsInclusive": {
                "simulationFrequency": [30, 150],
                "maxSimulationCountPerFrame": [1, 5],
                "GlobalTimeScale": [0.0, 1.0],
            },
            "equations": [
                "SimulationDeltaTime = float32(1.0f / float32(simulationFrequency))",
                "MaxDeltaTime = float32(float32(maxSimulationCountPerFrame) * SimulationDeltaTime)",
            ],
            "retailDefaults": {
                "simulationFrequency": 90,
                "maxSimulationCountPerFrame": 3,
                "GlobalTimeScale": 1.0,
                "SimulationDeltaTimeFloat32": _f32(1.0 / 90.0),
                "MaxDeltaTimeFloat32": _f32(_f32(3.0) * _f32(1.0 / 90.0)),
            },
        },
        "perTeamAccumulator": {
            "eligibleTeams": "teamId 1..teamCount-1; get_IsEnable must pass; culling-invisible teams take the non-accumulating branch",
            "deltaSelection": [
                "get_IsFixedUpdate: selectedDelta = unityFrameFixedDeltaTime",
                "else get_IsUnscaled: selectedDelta = unityFrameUnscaledDeltaTime",
                "else selectedDelta = unityFrameDeltaTime",
            ],
            "equations": [
                "effectiveScale = get_IsUnscaled ? TeamData.timeScale : float32(TeamData.timeScale * globalTimeScale)",
                "Flag_SyncSuspend (0x10) forces effectiveScale = 0",
                "candidateTime = float32(TeamData.time + float32(effectiveScale * selectedDelta))",
                "rawCount = truncTowardZero(float32(float32(candidateTime - TeamData.nowUpdateTime) / simulationDeltaTime))",
                "TeamData.updateCount = rawCount >= maxSimmulationCountPerFrame ? maxSimmulationCountPerFrame : rawCount",
                "TeamData.skipCount = rawCount - TeamData.updateCount",
                "if skipCount > 0: candidateTime = float32(candidateTime - float32(float32(skipCount) * simulationDeltaTime))",
                "TeamData.oldTime = previous TeamData.time; TeamData.time = candidateTime",
                "maxUpdateCount = max(maxUpdateCount, TeamData.updateCount), seeded at 0",
            ],
            "branches": {
                "resetSimulationToAnimationPoseNonzero": [
                    "TeamData.nowUpdateTime = candidateTime",
                    "TeamData.updateCount = 0",
                    "TeamData.skipCount = 0",
                    "Flag_Reset (0x4) is set",
                ],
                "pendingCountWhileEffectiveScaleExactlyZero": [
                    "TeamData.nowUpdateTime = float32(float32(candidateTime - simulationDeltaTime) + 0.0001f)",
                    "TeamData.updateCount = 0",
                    "TeamData.skipCount = 0",
                ],
                "positiveUpdateCount": [
                    "TeamData.oldUpdateTime = previous TeamData.nowUpdateTime",
                    "TeamData.frameOldTime = previous TeamData.frameUpdateTime",
                    "TeamData.frameUpdateTime = candidateTime",
                ],
                "signedBoundary": "No lower clamp is present after cvttss2si; nonpositive updateCount does not raise maxUpdateCount and does not execute a team step.",
            },
        },
        "solverLoop": {
            "globalLoop": "for updateIndex = 0; updateIndex < maxUpdateCount; ++updateIndex: SimulationStepUpdate(maxUpdateCount, updateIndex)",
            "perTeamGate": "Flag_StepRunning (bit 7) is set exactly when updateIndex < TeamData.updateCount; otherwise that team returns before solver work.",
            "perExecutedTeamStep": [
                "TeamData.nowUpdateTime = float32(TeamData.nowUpdateTime + simulationDeltaTime)",
                "denominator = float32(TeamData.time - TeamData.frameOldTime)",
                "if denominator > 0: TeamData.frameInterpolation = clamp(float32((TeamData.nowUpdateTime - TeamData.frameOldTime) / denominator), 0, 1); else frameInterpolation = 1",
            ],
            "meaning": "The number of SimulationStepUpdate calls is the maximum active team count; each team executes only its own updateCount prefix of those calls.",
        },
        "ordinary60FpsDefault90Hz": {
            "perRenderFrameSolverSteps": [1, 2],
            "nominalAverageStepsPerFrame": 1.5,
            "nominalStepsPerSecond": 90,
            "maxThreeClampReached": False,
            "phaseRule": "The exact 1/2 ordering depends on TeamData.time and nowUpdateTime; float32 accumulation does not guarantee a strict alternating sequence or exactly 90 steps in every wall-clock one-second window.",
            "zeroInitializedFirst12Frames": trace12,
            "zeroInitializedFirst60Frames": {
                "counts": trace60["counts"],
                "totalSolverSteps": trace60["totalSolverSteps"],
            },
            "zeroInitializedFirst1200Frames": {
                "uniqueCounts": sorted(set(trace1200["counts"])),
                "totalSolverSteps": trace1200["totalSolverSteps"],
                "nominalExpectedSteps": 1800,
            },
        },
        "implementationBoundary": {
            "unpatchedPinnedRouteClosed": True,
            "frameUpdateScalarsClosed": True,
            "perTeamAccumulatorClosed": True,
            "globalCountReductionClosed": True,
            "solverLoopCountClosed": True,
            "perTeamStepClockClosed": True,
            "ifixPatchedRouteClosed": False,
            "runtimeImplemented": False,
            "visualVerificationPerformed": False,
        },
        "nonClaims": [
            "The IFix-patched SimulationStepUpdate route is not audited; all equations are for the pinned unpatched native route.",
            "Sync-parent, animator-update-mode, and distance-culling ownership selection around the accumulator is not reinterpreted beyond the pinned branch/helper identities.",
            "This static contract does not implement the solver, enable writeback, or establish rendered equivalence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
        encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == encoded
            print(json.dumps({"status": result["status"], "matches": matches, "output": str(args.output)}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"], "output": str(args.output)}))
        return 0
    except (ContractError, OSError, ValueError, KeyError, IndexError, struct.error) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
