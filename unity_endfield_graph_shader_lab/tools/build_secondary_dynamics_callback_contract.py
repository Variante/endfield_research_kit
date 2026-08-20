#!/usr/bin/env python3
"""Build the native-evidence callback and transform-writeback contract.

The serialized ``secondary_dynamics_solver_inputs.json`` contract deliberately
stops before implementing a solver.  This companion contract closes the next
boundary that can be recovered without inventing Burst numerics: the pinned
PlayerLoop callback enters ``ClothManager.ClothUpdate``, the native body stages
transform/animator inputs, runs the simulation manager, and writes transform
and animator buffers back through the exact native bridge.

This is a static/native contract, not a solver and not visual verification.
All claims are withheld when the explicit installed native inputs, DummyDll
generation record, or evidence maps drift.

The lifecycle/native maps live under the repository's ignored local evidence
area.  A clean checkout without those maps is intentionally unavailable and
fails closed; this tool does not claim it can independently reconstruct them.
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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402

EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/secondary_dynamics_owner"
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"

SOLVER_INPUTS = SOURCE_ROOT / "secondary_dynamics_solver_inputs.json"
PLAYER_LOOP_CONTRACT = SOURCE_ROOT / "playerloop_recovery_contract.json"
DEFAULT_NATIVE = EVIDENCE_ROOT / "lifecycle_native.json"
DEFAULT_METADATA_CATALOG = EVIDENCE_ROOT / "lifecycle_metadata.json"
DEFAULT_DUMMY_GENERATION = REPO_ROOT / "tools/DummyDll/generation.json"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_callback_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_BONE_ASSEMBLY_SHA256 = "025c209c7f0b9ee927891421c74b42bdd16ff224f16f9c189f9f7d6ad1a3182c"
EXPECTED_CODE_REGISTRATION = "0x18b9217d0"

CALLBACK_TYPE = "BeyondDynamicBone.MagicaManager+<>c"
CALLBACK_METHOD = "<SetCustomGameLoop>b__40_1"
CALLBACK_METHOD_INDEX = 385118
CALLBACK_VA = "0x183234640"
CALLBACK_DELEGATE_SLOT = "0x18"
CALLBACK_PLAYER_LOOP_ORDINAL = 2
CALLBACK_PLAYER_LOOP_CALL_OFFSET = 988
CALLBACK_PLAYER_LOOP_CALL_VA = "0x183323a5c"

CLOTH_MANAGER_TYPE = "BeyondDynamicBone.ClothManager"
CLOTH_UPDATE_METHOD = "ClothUpdate"
CLOTH_UPDATE_METHOD_INDEX = 384441
CLOTH_UPDATE_VA = "0x182f918a0"

# These are deliberately narrow: they are the named calls that establish the
# scheduling/read/write boundary.  The full native body remains in the pinned
# evidence map and is not copied into the generated WebUI-facing contract.
CALLBACK_CALLS = (
    (394, "0x182f95240", "BeyondDynamicBone.MagicaManager", "get_Time"),
    (419, CLOTH_UPDATE_VA, CLOTH_MANAGER_TYPE, CLOTH_UPDATE_METHOD),
    (493, "0x1835bcab0", "BeyondDynamicBone.TeamManager", "MonitoringProcess"),
    (790, "0x182f95240", "BeyondDynamicBone.MagicaManager", "get_Time"),
)

CALLBACK_ABI = {
    419: {"rcx": "rbp", "rdx": "0"},
    493: {"rcx": "rbp", "rdx": "0", "r8": "0"},
}

CRITICAL_CALLS = (
    (447, "0x1834460c0", "BeyondDynamicBone.TimeManager", "FrameUpdate"),
    (672, "0x1835bd710", "Unity.Jobs.JobHandle", "Complete"),
    (752, "0x1835bea60", "BeyondDynamicBone.TeamManager", "AlwaysTeamUpdate"),
    (971, "0x183df49b0", "BeyondDynamicBone.WindManager", "AlwaysWindUpdate"),
    (990, "0x182f8bca0", "BeyondDynamicBone.SimulationManager", "WorkBufferUpdate"),
    (1191, "0x183b127d0", "BeyondDynamicBone.DynamicBoneTransformManager", "ReadTransform"),
    (1232, "0x183b125a0", "BeyondDynamicBone.DynamicBoneTransformManager", "WriteDoubleBufferTransform"),
    (1472, "0x186725e4c", "BeyondDynamicBone.DynamicBoneTransformManager", "ReadAnimatorBufferData"),
    (1883, "0x183b127d0", "BeyondDynamicBone.DynamicBoneTransformManager", "ReadTransform"),
    (1930, "0x182f8b170", "BeyondDynamicBone.VirtualMeshManager", "PreProxyMeshUpdate"),
    (1973, "0x1835bc3e0", "BeyondDynamicBone.TeamManager", "CalcCenterAndInertiaAndWind"),
    (2016, "0x182f8ad10", "BeyondDynamicBone.SimulationManager", "PreSimulationUpdate"),
    (2091, "0x182f914d0", "BeyondDynamicBone.ColliderManager", "PreSimulationUpdate"),
    (2160, "0x182f8f430", "BeyondDynamicBone.SimulationManager", "SimulationStepUpdate"),
    (2214, "0x182f8a9f0", "BeyondDynamicBone.SimulationManager", "CalcDisplayPosition"),
    (2257, "0x182f8c4a0", "BeyondDynamicBone.VirtualMeshManager", "PostProxyMeshUpdate"),
    (3004, "0x18672641c", "BeyondDynamicBone.DynamicBoneTransformManager", "WriteTransform"),
    (4277, "0x186726158", "BeyondDynamicBone.DynamicBoneTransformManager", "WriteAnimatorBufferData"),
    (4358, "0x182f8d550", "BeyondDynamicBone.ColliderManager", "PostSimulationUpdate"),
    (4401, "0x183dc03b0", "BeyondDynamicBone.TeamManager", "PostTeamUpdate"),
    (4448, "0x182f95120", CLOTH_MANAGER_TYPE, "CompleteMasterJob"),
)

# ABI writes at the call site are part of the contract.  The pointers are
# represented symbolically exactly as the evidence decoder reports them; no
# guessed managed struct layout is introduced here.
ABI_CALLS = {
    1191: {
        "rcx": "&[rsp+0x40]",
        "rdx": "rdi",
        "r8": "&[rsp+0x50]",
        "r9": "0",
    },
    1232: {
        "xmm0": "[rax]",
        "rcx": "&[rsp+0x50]",
        "rdx": "rdi",
        "r8": "&[rsp+0x40]",
        "r9": "0",
    },
    1472: {
        "rcx": "&[rsp+0x60]",
        "rdx": "[rsp+0x238]",
        "r8": "&[rsp+0x40]",
        "r9": "&[r15+0xb8]",
    },
    1883: {
        "rcx": "&[rsp+0x50]",
        "rdx": "rdi",
        "r8": "&[rsp+0x40]",
        "r9": "0",
    },
    3004: {
        "xmm0": "[rbx+0x38]",
        "rcx": "&[rsp+0x70]",
        "rdx": "rax",
        "r8": "&[rsp+0x40]",
        "r9": "0",
    },
    4277: {
        "xmm0": "[r8+0x38]",
        "rcx": "&[rsp+0x70]",
        "rdx": "[rsp+0x238]",
        "r8": "&[rsp+0x40]",
        "r9": "&[r15+0xb8]",
    },
}


class ContractError(RuntimeError):
    """Raised when a native/evidence gate does not close."""


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


def _method_record(lifecycle: dict[str, Any], type_name: str, method_name: str) -> dict[str, Any]:
    for row in lifecycle.get("method_bodies", []):
        if row.get("type") == type_name and row.get("method") == method_name:
            return row
    raise ContractError(f"missing method hash record: {type_name}::{method_name}")


def _body_target(native: dict[str, Any], type_name: str, method_name: str) -> dict[str, Any]:
    for row in native.get("bodyTargets", []):
        if row.get("type") == type_name and row.get("method") == method_name:
            return row
    raise ContractError(f"missing native body target: {type_name}::{method_name}")


def _resolved_name(call: dict[str, Any]) -> tuple[str, str] | None:
    resolved = call.get("resolved") or []
    exact = {(str(row.get("type")), str(row.get("method"))) for row in resolved}
    if len(exact) == 1:
        return next(iter(exact))
    return None


def _calls_by_offset(body: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for call in body.get("directCalls", []):
        offset = int(call.get("offset", -1))
        if offset in result:
            raise ContractError(f"duplicate direct-call offset {offset} in {body.get('method')}")
        result[offset] = call
    return result


def _method_identity(
    lifecycle: dict[str, Any],
    native: dict[str, Any],
    type_name: str,
    method_name: str,
    game_assembly: Path,
) -> dict[str, Any]:
    record = _method_record(lifecycle, type_name, method_name)
    body = _body_target(native, type_name, method_name)
    for field, expected in (
        ("methodIndex", record["method_index"]),
        ("methodPointerVa", record["va"]),
        ("scanBytes", record["bytes"]),
    ):
        if body.get(field) != expected:
            raise ContractError(
                f"{type_name}::{method_name} {field} drift: "
                f"expected {expected!r}, actual {body.get(field)!r}"
            )
    file_offset = int(str(body.get("fileOffset")), 0)
    body_bytes = int(body.get("scanBytes", 0))
    if body_bytes != int(record["bytes"]):
        raise ContractError(
            f"{type_name}::{method_name} native scan length drift: "
            f"expected {record['bytes']!r}, actual {body_bytes!r}"
        )
    with game_assembly.open("rb") as stream:
        stream.seek(file_offset)
        native_body = stream.read(body_bytes)
    if len(native_body) != body_bytes:
        raise ContractError(
            f"{type_name}::{method_name} native body truncated at file offset "
            f"0x{file_offset:x}"
        )
    native_sha256 = hashlib.sha256(native_body).hexdigest()
    if native_sha256 != record["sha256"]:
        raise ContractError(
            f"{type_name}::{method_name} native body sha256 drift: "
            f"expected {record['sha256']}, actual {native_sha256}"
        )
    return {
        "type": type_name,
        "method": method_name,
        "methodIndex": int(record["method_index"]),
        "methodPointerVa": record["va"],
        "fileOffset": record["file_offset"],
        "bytes": int(record["bytes"]),
        "sha256": record["sha256"],
        "nativeBodySha256": native_sha256,
        "hashSource": "pinned GameAssembly.dll fileOffset + scanBytes",
    }


def _call_record(
    body: dict[str, Any],
    offset: int,
    target_va: str,
    type_name: str,
    method_name: str,
    *,
    abi: dict[str, str] | None = None,
) -> dict[str, Any]:
    call = _calls_by_offset(body).get(offset)
    if call is None:
        raise ContractError(f"missing call offset {offset} in {body.get('method')}")
    if str(call.get("targetVa")) != target_va:
        raise ContractError(
            f"{body.get('method')} call {offset} target drift: "
            f"expected {target_va}, actual {call.get('targetVa')}"
        )
    if _resolved_name(call) != (type_name, method_name):
        raise ContractError(
            f"{body.get('method')} call {offset} resolver drift: "
            f"expected {type_name}::{method_name}, actual {_resolved_name(call)}"
        )
    row: dict[str, Any] = {
        "offset": offset,
        "targetVa": target_va,
        "type": type_name,
        "method": method_name,
    }
    if abi is not None:
        observed: dict[str, str] = {}
        for register, entry in (call.get("argumentContext", {}).get("argRegisterWrites") or {}).items():
            write = entry.get("write") or {}
            if "value" in write:
                observed[str(register)] = str(write["value"])
        if observed != abi:
            raise ContractError(
                f"{body.get('method')} call {offset} ABI drift: "
                f"expected {abi!r}, actual {observed!r}"
            )
        row["abiRegisterWrites"] = abi
    return row


def _dummy_generation_record(path: Path, game_assembly: Path, metadata: Path) -> dict[str, Any]:
    generation = load_json(path)
    game = generation.get("game") or {}
    if game.get("gameAssemblySha256") != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError("DummyDll generation GameAssembly hash drift")
    if game.get("metadataSha256") != EXPECTED_METADATA_SHA256:
        raise ContractError("DummyDll generation metadata hash drift")
    if game.get("gameAssemblyBytes") != game_assembly.stat().st_size:
        raise ContractError("DummyDll generation GameAssembly size drift")
    if game.get("metadataBytes") != metadata.stat().st_size:
        raise ContractError("DummyDll generation metadata size drift")
    if generation.get("registrations", {}).get("codeRegistration") != EXPECTED_CODE_REGISTRATION:
        raise ContractError("DummyDll generation code registration drift")
    assembly = next(
        (row for row in generation.get("assemblies", {}).get("files", []) if row.get("name") == "BeyondDynamicBone.dll"),
        None,
    )
    if not assembly or assembly.get("sha256") != EXPECTED_BONE_ASSEMBLY_SHA256:
        raise ContractError("DummyDll generation lacks the pinned BeyondDynamicBone.dll hash")
    return {
        "record": file_record(path),
        "schema": generation.get("schema"),
        "game": {
            "gameAssemblySha256": game.get("gameAssemblySha256"),
            "metadataSha256": game.get("metadataSha256"),
            "codeRegistration": generation["registrations"]["codeRegistration"],
        },
        "BeyondDynamicBone.dll": {
            "bytes": int(assembly["bytes"]),
            "sha256": assembly["sha256"],
        },
    }


def _native_gate(
    game_assembly: Path | None,
    metadata: Path | None,
) -> dict[str, Any]:
    """Use the repository's install resolver and native hash gate exactly once."""

    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not result.validated:
        raise ContractError(f"common.check_installed_native_inputs [{result.status}]: {result.detail}")
    resolved_game_assembly = Path(result.gameassembly)
    resolved_metadata = Path(result.metadata)
    return {
        "gameAssembly": {"path": resolved_game_assembly.as_posix(), "size": resolved_game_assembly.stat().st_size, "sha256": result.gameassembly_sha256},
        "globalMetadata": {"path": resolved_metadata.as_posix(), "size": resolved_metadata.stat().st_size, "sha256": result.metadata_sha256},
    }


def _verify_solver_sources(solver: dict[str, Any], native_path: Path, catalog_path: Path) -> None:
    source_build = solver.get("source_build") or {}
    if source_build.get("game_assembly", {}).get("sha256") != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError("solver-input GameAssembly hash drift")
    if source_build.get("global_metadata", {}).get("sha256") != EXPECTED_METADATA_SHA256:
        raise ContractError("solver-input metadata hash drift")
    evidence = solver.get("native_lifecycle", {}).get("evidence") or {}
    for label, path in (("native_map", native_path), ("metadata_catalog", catalog_path)):
        record = evidence.get(label) or {}
        if record.get("repo_path") != _repo_path(path):
            raise ContractError(f"solver-input {label} source path drift")
        if record.get("size") != path.stat().st_size or record.get("sha256") != sha256(path):
            raise ContractError(f"solver-input {label} evidence hash/size drift")


def _verify_player_loop(solver: dict[str, Any], player_loop: dict[str, Any]) -> None:
    if player_loop.get("schema") != "endfieldPlayerLoopRecoveryContract.v1":
        raise ContractError("unexpected PlayerLoop contract schema")
    if player_loop.get("status") != "partial_unresolved_first_system_anchor":
        raise ContractError("unexpected PlayerLoop contract status")
    if (player_loop.get("sourceHashes") or {}).get("GameAssembly.dll") != EXPECTED_GAME_ASSEMBLY_SHA256:
        raise ContractError("PlayerLoop GameAssembly hash drift")
    if (player_loop.get("sourceHashes") or {}).get("global-metadata.dat") != EXPECTED_METADATA_SHA256:
        raise ContractError("PlayerLoop metadata hash drift")
    rows = player_loop.get("insertions") or []
    if len(rows) != 7 or rows[1].get("ordinal") != CALLBACK_PLAYER_LOOP_ORDINAL:
        raise ContractError("PlayerLoop callback ordinal drift")
    row = rows[1]
    if row.get("categoryName", {}).get("value") != "FixedUpdate":
        raise ContractError("PlayerLoop callback category drift")
    if row.get("systemName", {}).get("value") != "ScriptRunBehaviourFixedUpdate":
        raise ContractError("PlayerLoop callback system drift")
    if row.get("last") is not False or row.get("before") is not False:
        raise ContractError("PlayerLoop callback insertion flags drift")
    if row.get("nativeCallOffset") != CALLBACK_PLAYER_LOOP_CALL_OFFSET:
        raise ContractError("PlayerLoop callback native call offset drift")
    if row.get("nativeCallVa") != CALLBACK_PLAYER_LOOP_CALL_VA:
        raise ContractError("PlayerLoop callback native call VA drift")
    if solver.get("native_lifecycle", {}).get("player_loop", {}).get("status") != player_loop.get("status"):
        raise ContractError("solver-input PlayerLoop status drift")
    registration = next(
        (
            callback
            for callback in solver.get("native_lifecycle", {}).get("manager", {}).get("callbacks", [])
            if callback.get("method") == CALLBACK_METHOD
        ),
        None,
    )
    if not registration:
        raise ContractError("solver-input callback registration is missing")
    if registration.get("va") != CALLBACK_VA:
        raise ContractError("solver-input callback registration VA drift")
    if registration.get("delegate_slot") != CALLBACK_DELEGATE_SLOT:
        raise ContractError("solver-input callback delegate slot drift")


def build_contract(
    *,
    game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
    solver_inputs: Path = SOLVER_INPUTS,
    native_evidence: Path = DEFAULT_NATIVE,
    metadata_catalog: Path = DEFAULT_METADATA_CATALOG,
    player_loop: Path = PLAYER_LOOP_CONTRACT,
    dummy_generation: Path = DEFAULT_DUMMY_GENERATION,
) -> dict[str, Any]:
    try:
        native_gate = _native_gate(game_assembly, metadata)
        solver = load_json(solver_inputs)
        native = load_json(native_evidence)
        catalog = load_json(metadata_catalog)
        loop = load_json(player_loop)
        _verify_solver_sources(solver, native_evidence, metadata_catalog)
        _verify_player_loop(solver, loop)
        dummy = _dummy_generation_record(
            dummy_generation,
            Path(native_gate["gameAssembly"]["path"]),
            Path(native_gate["globalMetadata"]["path"]),
        )

        callback_body = _body_target(native, CALLBACK_TYPE, CALLBACK_METHOD)
        cloth_body = _body_target(native, CLOTH_MANAGER_TYPE, CLOTH_UPDATE_METHOD)
        callback_identity = _method_identity(
            solver["native_lifecycle"], native, CALLBACK_TYPE, CALLBACK_METHOD,
            Path(native_gate["gameAssembly"]["path"]),
        )
        cloth_identity = _method_identity(
            solver["native_lifecycle"], native, CLOTH_MANAGER_TYPE, CLOTH_UPDATE_METHOD,
            Path(native_gate["gameAssembly"]["path"]),
        )

        callback_calls = [
            _call_record(
                callback_body,
                offset,
                target,
                typ,
                method,
                abi=CALLBACK_ABI.get(offset),
            )
            for offset, target, typ, method in CALLBACK_CALLS
        ]
        critical_calls = [
            _call_record(
                cloth_body,
                offset,
                target,
                typ,
                method,
                abi=ABI_CALLS.get(offset),
            )
            for offset, target, typ, method in CRITICAL_CALLS
        ]
        callback_direct = [
            row
            for row in callback_body.get("directCalls", [])
            if int(row.get("offset", -1)) in {item[0] for item in CALLBACK_CALLS}
        ]
        if len(callback_direct) != len(CALLBACK_CALLS):
            raise ContractError("callback direct-call set is incomplete")
        if callback_body.get("methodBodySummary", {}).get("unknownInstructionCount") != 0:
            raise ContractError("callback body contains unknown decoded instructions")
        # The long ClothUpdate body contains decoder ``db`` fragments around
        # control-flow recovery (the pinned map reports 367 unknown bytes), so
        # the contract closes only the independently resolved critical call
        # edges below.  It must not turn that partial instruction decode into
        # a claim about Burst arithmetic.

        return {
            "schema": "endfield.charinfo.secondary-dynamics-callback-writeback.v1",
            "recovered_at": solver.get("recovered_at"),
            "status": "native_callback_writeback_closed",
            "secondary_dynamics_verified": False,
            "solver_implemented": False,
            "retail_equivalent": False,
            "native_gate": native_gate,
            "sources": {
                "solver_inputs": file_record(solver_inputs),
                "native_evidence": file_record(native_evidence),
                "metadata_catalog": file_record(metadata_catalog),
                "player_loop_contract": file_record(player_loop),
                "dummy_generation": dummy,
                "codeRegistration": EXPECTED_CODE_REGISTRATION,
                "catalogMetadata": {
                    "sha256": catalog.get("metadata", {}).get("sha256"),
                    "version": catalog.get("metadata", {}).get("version"),
                },
            },
            "callback": {
                "delegateSlot": CALLBACK_DELEGATE_SLOT,
                "playerLoopOrdinal": CALLBACK_PLAYER_LOOP_ORDINAL,
                "playerLoopCategory": "FixedUpdate",
                "playerLoopSystem": "ScriptRunBehaviourFixedUpdate",
                "nativeCallOffset": CALLBACK_PLAYER_LOOP_CALL_OFFSET,
                "nativeCallVa": CALLBACK_PLAYER_LOOP_CALL_VA,
                "insertion": {"last": False, "before": False},
                "method": callback_identity,
                "calls": callback_calls,
                "argumentContract": {
                    "ClothUpdate": {"rcx": "rbp", "rdx": "0"},
                    "MonitoringProcess": {"rcx": "rbp", "rdx": "0", "r8": "0"},
                },
            },
            "writeback": {
                "method": cloth_identity,
                "decoder": {
                    "unknownInstructionCount": cloth_body.get("methodBodySummary", {}).get("unknownInstructionCount"),
                    "boundary": "Critical named call edges and their order are exact; unknown decoder fragments remain outside the numeric claim.",
                },
                "criticalCalls": critical_calls,
                "stages": {
                    "preparation": [447, 672, 752, 971, 990],
                    "inputRead": [1191, 1232, 1472, 1883],
                    "simulation": [1930, 1973, 2016, 2091, 2160, 2214, 2257],
                    "transformWriteback": [3004, 4277],
                    "postSimulation": [4358, 4401, 4448],
                },
                "orderingGates": [
                    {"before": 1191, "after": 3004, "relation": "ReadTransform precedes WriteTransform"},
                    {"before": 1472, "after": 4277, "relation": "ReadAnimatorBufferData precedes WriteAnimatorBufferData"},
                    {"before": 2160, "after": 3004, "relation": "SimulationStepUpdate precedes WriteTransform"},
                    {"before": 672, "after": 4448, "relation": "JobHandle.Complete precedes CompleteMasterJob"},
                ],
                "abiBoundary": "The six transform/animator bridge call sites retain exact native register writes; stack locations and pointers are symbolic native evidence, not a recovered managed layout.",
            },
            "execution_boundary": {
                "native_callback_closed": True,
                "transform_writeback_route_closed": True,
                "burst_constraint_numerics_recovered": False,
                "job_payload_layout_recovered": False,
                "unity_runtime_executed": False,
                "visual_verification_required": True,
                "ignoredEvidenceBoundary": "lifecycle_native.json, lifecycle_metadata.json, and related filters are ignored local evidence; a clean checkout without them is unavailable and fails closed rather than independently reconstructing the map.",
                "reason": "Exact callback, scheduling, transform read, simulation dispatch, and writeback call sites are closed for the pinned client; Burst constraint numerics and runtime execution remain unimplemented.",
            },
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ContractError) as exc:
        return {
            "schema": "endfield.charinfo.secondary-dynamics-callback-writeback.v1",
            "status": "unavailable",
            "secondary_dynamics_verified": False,
            "solver_implemented": False,
            "retail_equivalent": False,
            "validationFailures": [str(exc)],
            "execution_boundary": {
                "native_callback_closed": False,
                "transform_writeback_route_closed": False,
                "reason": "Native/evidence gate failed closed; no callback or writeback claim is published.",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--solver-inputs", type=Path, default=SOLVER_INPUTS)
    parser.add_argument("--native-evidence", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--metadata-catalog", type=Path, default=DEFAULT_METADATA_CATALOG)
    parser.add_argument("--player-loop", type=Path, default=PLAYER_LOOP_CONTRACT)
    parser.add_argument("--dummy-generation", type=Path, default=DEFAULT_DUMMY_GENERATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build_contract(
        game_assembly=args.game_assembly,
        metadata=args.metadata,
        solver_inputs=args.solver_inputs,
        native_evidence=args.native_evidence,
        metadata_catalog=args.metadata_catalog,
        player_loop=args.player_loop,
        dummy_generation=args.dummy_generation,
    )
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    matches = None
    if args.check:
        matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
    elif result.get("status") == "native_callback_writeback_closed":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "output": str(args.output), "matches": matches, "validationFailures": result.get("validationFailures", [])}, ensure_ascii=False))
    if args.check and not matches:
        return 1
    return 0 if result.get("status") == "native_callback_writeback_closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
