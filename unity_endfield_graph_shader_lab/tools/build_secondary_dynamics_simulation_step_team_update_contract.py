#!/usr/bin/env python3
"""Build the pinned Endminf SimulationStepTeamUpdate center-feed contract."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import build_secondary_dynamics_burst_export_contract as burst


LAB_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_simulation_step_team_update_contract.json"
ELEMENT_LAYOUT = SOURCE_ROOT / "secondary_dynamics_element_layout_contract.json"
CENTER_CONTRACT = SOURCE_ROOT / "secondary_dynamics_center_update_contract.json"
SUBSTEP_CONTRACT = SOURCE_ROOT / "secondary_dynamics_substep_contract.json"
TIME_CONTRACT = SOURCE_ROOT / "secondary_dynamics_time_manager_contract.json"
SOLVER_INPUTS = SOURCE_ROOT / "secondary_dynamics_solver_inputs.json"
SIMULATION_START = SOURCE_ROOT / "secondary_dynamics_simulation_start_semantics_contract.json"

TEAM_STRIDE = 0x1D0
PARAMETER_STRIDE = 0x328
CENTER_STRIDE = 0x2B8
TEAM_WIND_STRIDE = 0x98
ACTIVE_GATE_MASK = 0x2000000000080812
ACTIVE_GATE_VALUE = 0x2

EXPORT_NAME = "c0a24ff8b401b4fe70437eb0869ac9b8"
EXPORT_RVA = 0x3612F0
EXPORT_BYTES = 64
EXPORT_SHA256 = "d695346de78e30061c597c17d82848db558d91e921b53d87925d1995caf7298b"
SLOT_RVA = 0x3C6230
AVX_ASSIGN_RVA = 0x36076A
AVX_ASSIGN_SHA256 = "630db5dc93ce48838e04abf8fb8e48ad8aee7df3544a9c7c162c4a30afdf6d81"
AVX_ENTRY_RVA = 0x11F8F0
AVX_ENTRY_BYTES = 49
AVX_ENTRY_SHA256 = "6c84744430b8b7f37a34e321f40b69501a4330921b6ffa31d490ccf5b5fc391b"
AVX_RANGE_RVA = 0x11F930
AVX_RANGE_BYTES = 45
AVX_RANGE_SHA256 = "33442ab7a9f298dba728acbb01d6aeed2267be6c620f3ad14c6dbeef2fbeacf4"
AVX_CORE_RVA = 0x11FB00
AVX_CORE_BYTES = 5340
AVX_CORE_SHA256 = "918e4d5815781a3396587f468bd469cbd1e2a4119c18d2c1fa3630b0b5c5f71c"
GET_WORK_RANGE_SLOT_RVA = 0x3C4180

MANAGED_METHOD = {
    "methodIndex": 384614,
    "type": "BeyondDynamicBone.TeamManager+SimulationStepTeamUpdateKernels",
    "method": "SimulationStepTeamUpdateKernel$BurstManaged",
    "startVa": "0x186727f20",
    "spanBytes": 3424,
    "sha256": "b5a49b1d2726d050c11d0eb4d9ae7cd99ab7baa96298887bbee8497e198619c7",
}

FIELDS = {
    "stepMoveInertiaRatio": (0x1C0, "f"),
    "stepRotationInertiaRatio": (0x1C4, "f"),
    "stepVector": (0x1C8, "3f"),
    "stepRotation": (0x1D4, "4f"),
    "inertiaVector": (0x1E4, "3f"),
    "inertiaRotation": (0x1F0, "4f"),
    "stepMovingSpeed": (0x200, "f"),
    "stepMovingDirection": (0x204, "3f"),
    "angularVelocity": (0x210, "f"),
    "rotationAxis": (0x214, "3f"),
    "initLocalGravityDirection": (0x220, "3f"),
}


class ContractError(RuntimeError):
    pass


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    try:
        display = path.resolve().relative_to(LAB_ROOT.parent.resolve()).as_posix()
    except ValueError:
        display = path.resolve().as_posix()
    return {"path": display, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _source(path: Path, schema: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != schema:
        raise ContractError(f"source schema drift: {path.name}")
    return payload, {**_file(path), "schema": schema, "status": payload.get("status")}


def _identity(pe: dict[str, Any]) -> dict[str, Any]:
    export = next((row for row in pe["exports"] if row["name"] == EXPORT_NAME), None)
    if export is None or export["rva"] != EXPORT_RVA:
        raise ContractError("SimulationStepTeamUpdate export identity drift")
    body, instructions = burst._exact_rva_span(pe, EXPORT_RVA, EXPORT_BYTES, EXPORT_SHA256)
    calls = burst._rip_call_rows(pe, pe["imageBase"] + EXPORT_RVA, instructions)
    if len(calls) != 1 or int(calls[0]["targetVa"], 16) - pe["imageBase"] != SLOT_RVA:
        raise ContractError("SimulationStepTeamUpdate function-pointer slot drift")
    assignment, assignment_instructions = burst._exact_rva_span(
        pe, AVX_ASSIGN_RVA, 14, AVX_ASSIGN_SHA256
    )
    if [row.mnemonic for row in assignment_instructions] != ["lea", "mov"]:
        raise ContractError("AVX2 assignment shape drift")
    if [burst._rip_memory_target(pe, row) for row in assignment_instructions] != [
        pe["imageBase"] + AVX_ENTRY_RVA, pe["imageBase"] + SLOT_RVA
    ]:
        raise ContractError("AVX2 assignment edge drift")
    for rva, size, digest in (
        (AVX_ENTRY_RVA, AVX_ENTRY_BYTES, AVX_ENTRY_SHA256),
        (AVX_RANGE_RVA, AVX_RANGE_BYTES, AVX_RANGE_SHA256),
        (AVX_CORE_RVA, AVX_CORE_BYTES, AVX_CORE_SHA256),
    ):
        burst._exact_rva_span(pe, rva, size, digest)
    _, entry = burst._exact_rva_span(pe, AVX_ENTRY_RVA, AVX_ENTRY_BYTES, AVX_ENTRY_SHA256)
    _, range_loop = burst._exact_rva_span(pe, AVX_RANGE_RVA, AVX_RANGE_BYTES, AVX_RANGE_SHA256)
    if [burst._direct_target(row, pe["imageBase"]) for row in entry if row.mnemonic == "call"] != [AVX_RANGE_RVA]:
        raise ContractError("entry-to-range edge drift")
    if [burst._direct_target(row, pe["imageBase"]) for row in range_loop if row.mnemonic == "call"] != [AVX_CORE_RVA]:
        raise ContractError("range-to-core edge drift")
    _, core = burst._exact_rva_span(pe, AVX_CORE_RVA, AVX_CORE_BYTES, AVX_CORE_SHA256)
    text = [f"{row.mnemonic} {row.op_str}" for row in core]
    for marker in ("0x1d0", "0x2b8", "0x328", "0x98", "+ 0x1c8]", "+ 0x1f0]", "+ 0x210]", "+ 0x214]"):
        if not any(marker in row for row in text):
            raise ContractError(f"AVX2 core marker missing: {marker}")
    forbidden_stores = {"[r15 + 0x200]", "[r15 + 0x204]", "[r15 + 0x208]", "[r15 + 0x20c]",
                        "[r15 + 0x220]", "[r15 + 0x224]", "[r15 + 0x228]"}
    stores = [row for row in text if row.startswith(("mov ", "movss ", "movlps ", "movups "))]
    if any(any(marker in row.split(",", 1)[0] for marker in forbidden_stores) for row in stores):
        raise ContractError("preserved-field store audit drift")
    return {
        "selectionBasis": "unique seven-argument scheduled-team export whose AVX2 core indexes TeamData/ClothParameters/CenterData/TeamWindData at 0x1d0/0x328/0x2b8/0x98 and publishes the center feed",
        "export": {"name": EXPORT_NAME, "rva": f"0x{EXPORT_RVA:x}", "bytes": len(body), "sha256": EXPORT_SHA256, "functionPointerSlotRva": f"0x{SLOT_RVA:x}"},
        "avx2": {
            "burstInitializeAssignment": {"rva": f"0x{AVX_ASSIGN_RVA:x}", "bytes": len(assignment), "sha256": AVX_ASSIGN_SHA256},
            "entry": {"rva": f"0x{AVX_ENTRY_RVA:x}", "bytes": AVX_ENTRY_BYTES, "sha256": AVX_ENTRY_SHA256},
            "rangeLoop": {"rva": f"0x{AVX_RANGE_RVA:x}", "bytes": AVX_RANGE_BYTES, "sha256": AVX_RANGE_SHA256},
            "core": {"rva": f"0x{AVX_CORE_RVA:x}", "bytes": AVX_CORE_BYTES, "sha256": AVX_CORE_SHA256},
        },
    }


def _selected(buffer: Any, base: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    raw = bytes(buffer)
    for name, (offset, fmt) in FIELDS.items():
        size = struct.calcsize("<" + fmt)
        values = struct.unpack_from("<" + fmt, raw, base + offset)
        result[name] = {
            "values": list(values),
            "bits": raw[base + offset:base + offset + size].hex(),
        }
    for name, (offset, fmt) in {
        "nowWorldPosition": (0x170, "3d"), "nowWorldRotation": (0x188, "4f"),
        "oldWorldPosition": (0x198, "3d"), "oldWorldRotation": (0x1B0, "4f"),
    }.items():
        size = struct.calcsize("<" + fmt)
        result[name] = {"values": list(struct.unpack_from("<" + fmt, raw, base + offset)),
                        "bits": raw[base + offset:base + offset + size].hex()}
    return result


def _native_vector(dll_path: Path, *, owner: str, local_inertia: float, depth_inertia: float,
                   translation: tuple[float, float, float], angle_degrees: float,
                   movement_speed_limit: float, rotation_speed_limit: float) -> dict[str, Any]:
    array = lambda size: (ctypes.c_ubyte * size)()
    team, parameter, center, team_wind = (array(TEAM_STRIDE * 2), array(PARAMETER_STRIDE * 2),
                                          array(CENTER_STRIDE * 2), array(TEAM_WIND_STRIDE * 2))
    t, p, c = TEAM_STRIDE, PARAMETER_STRIDE, CENTER_STRIDE
    dt = _f32(1.0 / 90.0)
    struct.pack_into("<Q", team, t, 0x82)
    struct.pack_into("<f", team, t + 0x14, 1.0)
    struct.pack_into("<f", team, t + 0x1C, _f32(1.0 - dt))
    struct.pack_into("<f", team, t + 0x28, 0.0)
    struct.pack_into("<i", team, t + 0x34, 1)
    struct.pack_into("<3f", team, t + 0x54, 1.0, 1.0, 1.0)
    struct.pack_into("<3f", center, c + 0x120, 1.0, 1.0, 1.0)
    struct.pack_into("<3f", center, c + 0x160, 1.0, 1.0, 1.0)
    struct.pack_into("<3d", center, c + 0xF8, *translation)
    struct.pack_into("<4f", center, c + 0x150, 0.0, 0.0, 0.0, 1.0)
    struct.pack_into("<4f", center, c + 0x188, 0.0, 0.0, 0.0, 1.0)
    struct.pack_into("<4f", center, c + 0x1B0, 0.0, 0.0, 0.0, 1.0)
    half = math.radians(angle_degrees) * 0.5
    struct.pack_into("<4f", center, c + 0x110, 0.0, 0.0, _f32(math.sin(half)), _f32(math.cos(half)))
    struct.pack_into("<f", parameter, p + 0xC8, _f32(local_inertia))
    struct.pack_into("<2f", parameter, p + 0xCC, _f32(movement_speed_limit), _f32(rotation_speed_limit))
    struct.pack_into("<f", parameter, p + 0xD4, _f32(depth_inertia))
    struct.pack_into("<3f", parameter, p + 4, 0.0, -1.0, 0.0)
    sentinels = {
        "stepMovingSpeed": (7.25,), "stepMovingDirection": (0.25, -0.5, 0.75),
        "initLocalGravityDirection": (-0.125, 0.375, -0.625),
    }
    for name, values in sentinels.items():
        offset, fmt = FIELDS[name]
        struct.pack_into("<" + fmt, center, c + offset, *values)

    job = array(0x48)
    struct.pack_into("<if", job, 0, 0, dt)
    for offset, value in ((0x08, team), (0x18, parameter), (0x28, center), (0x38, team_wind)):
        struct.pack_into("<Q", job, offset, ctypes.addressof(value))
    ranges = array(0x10)
    state = {"calls": 0}
    callback_type = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_int,
                                     ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))

    @callback_type
    def one_range(_ranges: int, _worker: int, start: Any, end: Any) -> bool:
        if state["calls"] == 0:
            start[0], end[0] = 0, 2
            state["calls"] = 1
            return True
        return False

    module = ctypes.WinDLL(str(dll_path))
    slot = ctypes.c_void_p.from_address(module._handle + GET_WORK_RANGE_SLOT_RVA)
    original = slot.value
    slot.value = ctypes.cast(one_range, ctypes.c_void_p).value
    try:
        fn = ctypes.CFUNCTYPE(None, *([ctypes.c_void_p] * 6), ctypes.c_int)(module._handle + AVX_CORE_RVA)
        fn(ctypes.addressof(job), 0, 0, ctypes.addressof(ranges), 0, 0, 0)
    finally:
        slot.value = original
    if state["calls"] != 1:
        raise ContractError("bounded native range callback did not execute exactly one range")
    selected = _selected(center, c)
    preserved = {name: selected[name]["values"] == list(values) for name, values in sentinels.items()}
    if not all(preserved.values()):
        raise ContractError(f"native preserved-field drift: {owner}")
    return {
        "name": f"endminf_{owner.lower()}_stationary_root_controlled_center_step",
        "inputs": {"flagBefore": "0x82", "updateIndex": 0, "updateCount": 1,
                   "simulationDeltaTimeF32": dt, "frameInterpolationExpected": 1.0,
                   "frameWorldTranslation": list(translation), "frameWorldRotationDegreesZ": angle_degrees,
                   "localInertiaF32": _f32(local_inertia), "depthInertiaF32": _f32(depth_inertia),
                   "localMovementSpeedLimitF32": _f32(movement_speed_limit),
                   "localRotationSpeedLimitF32": _f32(rotation_speed_limit),
                   "windZoneCount": 0},
        "selectedNativeOutputs": selected,
        "preservedSentinels": preserved,
        "nativeHarness": "AVX2 scheduled range core with a bounded in-process GetWorkStealingRange callback; no game process or installed file is modified",
    }


def _owner_facts(solver: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {"MC_Ribbon2": (1.0, 0.0), "MC_Hair": (1.0, 1.0),
                "MC_Ribbon": (0.7, 0.0), "MC_Coat": (0.8, 0.7)}
    rows = []
    cloths = {row["game_object_path"]: row for row in solver["actors"]["endminf"]["cloths"]}
    if set(cloths) != set(expected):
        raise ContractError("Endminf owner set drift")
    for owner, (local, depth) in expected.items():
        inertia = cloths[owner]["serialized_data"]["inertiaConstraint"]
        actual = (_f32(float(inertia["localInertia"])), _f32(float(inertia["depthInertia"])))
        if actual != (_f32(local), _f32(depth)):
            raise ContractError(f"Endminf inertia source drift: {owner}")
        move_limit = inertia["localMovementSpeedLimit"]
        rotation_limit = inertia["localRotationSpeedLimit"]
        packed_move = _f32(float(move_limit["value"])) if int(move_limit["use"]) else -1.0
        packed_rotation = _f32(float(rotation_limit["value"])) if int(rotation_limit["use"]) else -1.0
        rows.append({"owner": owner,
                     "worldInertiaF32": _f32(float(inertia["worldInertia"])),
                     "localInertiaF32": actual[0], "depthInertiaF32": actual[1],
                     "localMovementSpeedLimitF32": packed_move,
                     "localRotationSpeedLimitF32": packed_rotation,
                     "teamUpdateUnclampedRatios": {"stepMoveInertiaRatio": _f32(1.0 - actual[0]),
                                                    "stepRotationInertiaRatio": _f32(1.0 - actual[0])},
                     "depthConsumer": "Simulation Start k=(1-depth^2)*depthInertia; SimulationStepTeamUpdate does not read depthInertia"})
    return rows


def build_contract() -> dict[str, Any]:
    gate = burst._native_gate(None, None)
    dll_path = Path(gate["libBurstGenerated"]["path"])
    pe = burst._pe_exports(dll_path)
    layout, layout_record = _source(ELEMENT_LAYOUT, "endfield.charinfo.secondary-dynamics-element-layout.v1")
    center, center_record = _source(CENTER_CONTRACT, "endfield.charinfo.secondary-dynamics-center-update.v1")
    substep, substep_record = _source(SUBSTEP_CONTRACT, "endfield.charinfo.secondary-dynamics-substep.v1")
    time, time_record = _source(TIME_CONTRACT, "endfield.charinfo.secondary-dynamics-time-manager.v1")
    start, start_record = _source(SIMULATION_START, "endfield.charinfo.secondary-dynamics-simulation-start-semantics.v1")
    solver = json.loads(SOLVER_INPUTS.read_text(encoding="utf-8"))
    solver_record = _file(SOLVER_INPUTS)
    elements = {row["name"]: row["nativeSizeBytes"] for row in layout["elements"]}
    if (elements.get("BeyondDynamicBone.TeamManager+TeamData"),
            elements.get("BeyondDynamicBone.InertiaConstraint+CenterData"),
            elements.get("BeyondDynamicBone.ClothParameters"),
            elements.get("BeyondDynamicBone.TeamWindData")) != (
            TEAM_STRIDE, CENTER_STRIDE, PARAMETER_STRIDE, TEAM_WIND_STRIDE):
        raise ContractError("canonical structure stride drift")
    if "SimulationStepTeamUpdate" not in json.dumps(substep, separators=(",", ":")):
        raise ContractError("substep ownership edge drift")
    managed = next((row for row in substep.get("nativeMethods", [])
                    if row.get("methodIndex") == MANAGED_METHOD["methodIndex"]), None)
    if managed is None or any(managed.get(key) != value for key, value in MANAGED_METHOD.items()):
        raise ContractError("managed SimulationStepTeamUpdate identity drift")
    if "preserves CenterData byte range 0x1c0..0x22b" not in json.dumps(center, separators=(",", ":")):
        raise ContractError("CalcCenter preservation boundary drift")
    if "inertiaDepth" not in json.dumps(start, separators=(",", ":")):
        raise ContractError("Simulation Start depth consumer drift")
    owners = _owner_facts(solver)
    vectors = [
        _native_vector(dll_path, owner="MC_Hair", local_inertia=1.0, depth_inertia=1.0,
                       translation=(0.015625, -0.0078125, 0.00390625), angle_degrees=22.5,
                       movement_speed_limit=-1.0, rotation_speed_limit=-1.0),
        _native_vector(dll_path, owner="MC_Coat", local_inertia=0.8, depth_inertia=0.7,
                       translation=(0.03125, 0.015625, -0.0078125), angle_degrees=45.0,
                       movement_speed_limit=5.0, rotation_speed_limit=720.0),
    ]
    return {
        "schema": "endfield.charinfo.secondary-dynamics-simulation-step-team-update.v1",
        "status": "target_stationary_root_no_wind_unpatched_avx2_center_feed_closed",
        "targetReady": True,
        "nativeGate": gate,
        "sourceContracts": [layout_record, center_record, substep_record, time_record, start_record,
                            {**solver_record, "schema": solver.get("schema"), "status": solver.get("status")}],
        "managedMethod": MANAGED_METHOD,
        "burstIdentity": _identity(pe),
        "scheduleAndGate": {
            "order": "CalcCenterAndInertiaAndWind -> per-solver-step SimulationStepTeamUpdate -> Simulation Start",
            "activeGate": "execute only when (TeamData.flag & 0x2000000000080812) == 0x2",
            "stepGate": "TeamManager sets Flag_StepRunning bit 7 iff updateIndex < TeamData.updateCount; otherwise this team returns before center-feed work",
            "targetUnpatchedFlags": "the required active-mask value is 0x2 and the scheduler sets bit 0x80 while executing; all unrelated bits pass through. 0x22 -> 0xa2 is the validated ordinary basis, not a claim that every unrelated live flag bit is fixed.",
            "clock": "simulationDeltaTime is binary32 1/90; ordinary 60 fps frames execute the pinned one/two-step cadence",
        },
        "exactEquations": {
            "interpolation": [
                "nowUpdateTime = f32(nowUpdateTime + simulationDeltaTime)",
                "denominator = f32(time - frameOldTime)",
                "frameInterpolation = denominator > 0 ? clamp01(f32((nowUpdateTime-frameOldTime)/denominator)) : 1",
                "nowWorldPosition = lerp(oldFrameWorldPosition, frameWorldPosition, frameInterpolation)",
                "nowWorldRotation = shortest-arc slerp(oldFrameWorldRotation, frameWorldRotation, frameInterpolation)",
            ],
            "step": [
                "stepVector = f32(nowWorldPosition - oldWorldPosition)",
                "stepRotation = shortest rotation from oldWorldRotation to nowWorldRotation",
                "stepAngle = quaternion angle(stepRotation) in radians",
                "angularVelocity = f32(stepAngle / simulationDeltaTime)",
                "rotationAxis = stepAngle > 1e-8f ? ToAngleAxis(stepRotation).axis : float3(0)",
            ],
            "localInertia": [
                "moveRatio = f32(1 - parameters.localInertia)",
                "if movementSpeedLimit >= 0 and length(stepVector)/dt > movementSpeedLimit: moveRatio = lerp(1, moveRatio, movementSpeedLimit/(length(stepVector)/dt))",
                "rotationSpeedDegrees = f32(stepAngle / dt * 57.295780181884766f)",
                "rotationRatio = f32(1 - parameters.localInertia)",
                "weightedRotationSpeedDegrees = f32(parameters.localInertia * rotationSpeedDegrees)",
                "if rotationSpeedLimit >= 0 and weightedRotationSpeedDegrees > rotationSpeedLimit: rotationRatio = lerp(1, rotationRatio, rotationSpeedLimit/weightedRotationSpeedDegrees)",
                "stepMoveInertiaRatio = moveRatio; inertiaVector = f32(stepVector * moveRatio)",
                "stepRotationInertiaRatio = rotationRatio; inertiaRotation = shortest-arc slerp(identity, stepRotation, rotationRatio)",
            ],
            "stateAdvance": [
                "oldWorldPosition = prior nowWorldPosition; oldWorldRotation = prior nowWorldRotation",
                "nowWorldPosition/nowWorldRotation receive this substep's interpolated center",
            ],
        },
        "writeOwnership": {
            "written": ["stepMoveInertiaRatio", "stepRotationInertiaRatio", "stepVector", "stepRotation",
                        "inertiaVector", "inertiaRotation", "angularVelocity", "rotationAxis"],
            "preservedByThisKernel": ["stepMovingSpeed", "stepMovingDirection", "initLocalGravityDirection"],
            "correctionToBroadBoundary": "The AVX2 store audit disproves the broad assumption that every field in CenterData+0x1c0..0x22b is written here. Offsets 0x200..0x20f and 0x220..0x22b are preserved.",
        },
        "endminfTarget": {
            "rootMotion": "ui_overview_start/loop actor root is stationary; CalcCenter still supplies animated fixed-center frameWorldPosition/frameWorldRotation",
            "owners": owners,
            "depthBoundary": "depthInertia is target-active but not a SimulationStepTeamUpdate input. It is consumed by Simulation Start after this kernel: k=(1-depth^2)*depthInertia, then translation/rotation interpolate from this kernel's inertia feed toward the full step feed.",
            "ratios": {"gravityRatio": 1.0, "scaleRatio": 1.0, "windZoneCount": 0,
                       "negativeScale": "unsupported/fail-closed", "IFix": "unsupported/fail-closed"},
        },
        "verification": {"nativeVectorCount": len(vectors), "vectors": vectors,
                         "checks": ["pinned installed GameAssembly/global-metadata/lib_burst hashes",
                                    "exact export/slot/AVX2 assignment/entry/range/core hashes and edges",
                                    "canonical 0x1d0/0x328/0x2b8/0x98 strides",
                                    "bounded direct native Hair and Coat vectors",
                                    "preserved-field finite sentinels"]},
        "failClosedBoundary": {
            "targetReady": True,
            "supported": "Endminf ui_overview_start/loop, stationary actor root, positive scale, no wind zones, unpatched path, default 90 Hz",
            "rejected": ["general wind", "negative scale", "IFix/patched route", "nondefault timestep/power helpers"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_contract()
        encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == encoded
            print(json.dumps({"status": payload["status"], "targetReady": payload["targetReady"],
                              "matches": matches, "validationFailures": [] if matches else ["generated contract drift"]}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
        print(json.dumps({"status": payload["status"], "targetReady": payload["targetReady"],
                          "output": str(args.output), "vectors": payload["verification"]["nativeVectorCount"]}))
        return 0
    except (OSError, ValueError, KeyError, IndexError, struct.error, ContractError, burst.ContractError) as exc:
        print(json.dumps({"status": "unavailable", "targetReady": False, "validationFailures": [str(exc)]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
