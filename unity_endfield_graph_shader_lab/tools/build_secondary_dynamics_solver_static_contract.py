#!/usr/bin/env python3
"""Pin the static Execute/UnsafeDo boundary for secondary-dynamics jobs.

This is deliberately a *boundary* contract.  ``Execute()`` is the managed
enumerator wrapper and ``UnsafeDo()`` is a Burst range-dispatch wrapper.  The
contract never labels either as the solver.  Only the indexed managed
``Execute(int)`` bodies below are classified as managed fallbacks, and their
raw buffer arithmetic is recorded as evidence.  The Burst implementation is
left unresolved until its generated function is independently identified.
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
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.md"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the pinned native evidence no longer matches."""


def _pe_image_module() -> Any:
    path = REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py"
    spec = importlib.util.spec_from_file_location("endfield_solver_pe_image", path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load PE helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _target(
    method_index: int,
    type_name: str,
    method: str,
    role: str,
    va: int,
    end_va: int,
    sha256: str,
    next_calls: list[dict[str, Any]],
    *,
    accesses: list[dict[str, Any]] | None = None,
    solver_status: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "methodIndex": method_index,
        "type": type_name,
        "method": method,
        "role": role,
        "solverStatus": solver_status,
        "va": _hex(va),
        "endVaExclusive": _hex(end_va),
        "spanBytes": end_va - va,
        "bodySha256": sha256,
        "nextCalls": next_calls,
    }
    if accesses is not None:
        row["bufferAccesses"] = accesses
    return row


def _managed_call(method_index: int, va: int, name: str, role: str) -> dict[str, Any]:
    return {"kind": role, "methodIndex": method_index, "va": _hex(va), "method": name}


SIM = "BeyondDynamicBone.SimulationManager"
COL = "BeyondDynamicBone.ColliderManager"
SIM_START = f"{SIM}+StartSimulationStepJob"
SIM_END = f"{SIM}+EndSimulationStepJob"
COL_START = f"{COL}+StartSimulationStepJob"
COL_END = f"{COL}+EndSimulationStepJob"


# VAs/spans are method-pointer boundaries from the pinned code-registration
# map.  Hashing exactly this interval also prevents a neighboring method from
# being accidentally treated as part of a body.
TARGETS = [
    _target(385696, SIM_START, "Execute", "managed_dispatch_wrapper", 0x186775A4C, 0x186775AE4,
            "26b144cda78f3f0f48cbdb9ce8f3883f8494bde58e2aa05e3363bb203e20a697",
            [_managed_call(385697, 0x186774BE8, "Execute(int)", "managed_fallback")],
            solver_status="wrapper_only"),
    _target(385697, SIM_START, "Execute(int)", "managed_fallback", 0x186774BE8, 0x186775A4C,
            "08fca10086f3b997dd895476d17f930b2ab66d8c63bf9462c8849b56d6edcf0a",
            [_managed_call(385698, 0x186775AE4, "Spring", "managed_helper"),
             _managed_call(385699, 0x186776704, "Wind", "managed_helper")],
            accesses=[
                {"jobField": "stepParticleIndexArray", "jobOffset": "0x18", "index": "Execute(index)", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0xe9"]},
                {"jobField": "teamIdArray", "jobOffset": "0xc8", "index": "particleIndex", "strideBytes": 2, "elementFieldDisplacements": [0], "instructionOffsets": ["0xf8"]},
                {"jobField": "teamDataArray", "jobOffset": "0x78", "index": "teamId", "strideBytes": 464, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112], "instructionOffsets": ["0xfd", "0x10e"]},
                {"jobField": "parameterArray", "jobOffset": "0x88", "index": "teamId", "strideBytes": 808, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112], "instructionOffsets": ["0x28e", "0x29f"]},
                {"jobField": "attributes", "jobOffset": "0x28", "index": "derivedVertexIndex", "strideBytes": 1, "elementFieldDisplacements": [0], "instructionOffsets": ["0x318"]},
                {"jobField": "depthArray", "jobOffset": "0x38", "index": "derivedVertexIndex", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0x328"]},
                {"jobField": "oldPosArray", "jobOffset": "0xd8", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x339", "0x33e"]},
                {"jobField": "oldPositionArray", "jobOffset": "0x128", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x39b", "0x39f"]},
                {"jobField": "positions", "jobOffset": "0x48", "index": "derivedVertexIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x37c", "0x380"]},
                {"jobField": "rotations", "jobOffset": "0x58", "index": "derivedVertexIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x36c"]},
                {"jobField": "basePosArray", "jobOffset": "0xf8", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x42a", "0x42e"]},
                {"jobField": "baseRotArray", "jobOffset": "0x118", "index": "particleIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x445"]},
                {"jobField": "stepBasicPositionArray", "jobOffset": "0x168", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x45e", "0x462"]},
                {"jobField": "stepBasicRotationArray", "jobOffset": "0x178", "index": "particleIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x479"]},
                {"jobField": "velocityPosArray", "jobOffset": "0x148", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0xdc2", "0xdc6"]},
                {"jobField": "nextPosArray", "jobOffset": "0xe8", "index": "particleIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0xde1", "0xde5"]},
            ],
            solver_status="managed_fallback_observed"),
    _target(385698, SIM_START, "Spring", "managed_helper", 0x186775AE4, 0x186776080,
            "149382eea39d5d1a3ca0e27ed701a665f51406664766283b070305adc52050b5", [],
            solver_status="helper_only"),
    _target(385699, SIM_START, "Wind", "managed_helper", 0x186776704, 0x186776B64,
            "2aca620c9c194d06742ffcc855efd57cca85bee46a8fc972da83ff02a855b0a0", [],
            solver_status="helper_only"),
    _target(385700, SIM_START, "WindForceBlend", "managed_helper", 0x186776394, 0x186776704,
            "0418400aa5d180fb7e81233ae707325e580d9881ffd519b0953e72ca9bce8796", [],
            solver_status="helper_only"),
    _target(385701, SIM_START, "UnsafeDo", "burst_range_dispatch_wrapper", 0x186776080, 0x186776394,
            "872a5aefd318ed907b800bb0c5a982cce47de2298019a3615416a8539da0944f",
            [_managed_call(385542, 0x1867744B0, "StartSimulationStepRangeKernel", "burst_wrapper"),
             _managed_call(385570, 0x1867775FC, "StartSimulationStepRangeKernel_00000408$BurstDirectCall.Invoke", "burst_invoke")],
            solver_status="wrapper_only_burst_solver_unresolved"),
    _target(385450, COL_START, "Execute", "managed_dispatch_wrapper", 0x186761580, 0x186761618,
            "11f3c6969dddd71698113711000f247f6adb4ade024af45c4f8d5adec260503d",
            [_managed_call(385451, 0x186761618, "Execute(int)", "managed_fallback")], solver_status="wrapper_only"),
    _target(385451, COL_START, "Execute(int)", "managed_fallback", 0x186761618, 0x1867624AC,
            "61d0b5400bed687be8baa7bf5281119b2ce09276423b84461fc27053710c7426",
            [], accesses=[
                {"jobField": "jobColliderIndexList", "jobOffset": "0x0", "index": "Execute(index)", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0x84"]},
                {"jobField": "flagArray", "jobOffset": "0x40", "index": "colliderIndex", "strideBytes": 1, "elementFieldDisplacements": [0], "instructionOffsets": ["0x8c"]},
                {"jobField": "teamIdArray", "jobOffset": "0x30", "index": "colliderIndex", "strideBytes": 2, "elementFieldDisplacements": [0], "instructionOffsets": ["0xb4"]},
                {"jobField": "teamDataArray", "jobOffset": "0x10", "index": "teamId", "strideBytes": 464, "elementFieldDisplacements": [0, 16, 32, 48, 64, 80, 96, 112], "instructionOffsets": ["0xb9", "0xc4"]},
                {"jobField": "centerDataArray", "jobOffset": "0x20", "index": "teamId", "strideBytes": 696, "elementFieldDisplacements": [0], "instructionOffsets": ["0x280", "0x299"]},
                {"jobField": "framePositions", "jobOffset": "0x60", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x155", "0x159"]},
                {"jobField": "oldFramePositions", "jobOffset": "0x90", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x178", "0x17c"]},
                {"jobField": "nowPositions", "jobOffset": "0xb0", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x2a0", "0x2a5"]},
                {"jobField": "nowRotations", "jobOffset": "0xc0", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x2ba"]},
                {"jobField": "oldPositions", "jobOffset": "0xd0", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x34b", "0x34f"]},
                {"jobField": "oldRotations", "jobOffset": "0xe0", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x420"]},
                {"jobField": "workDataArray", "jobOffset": "0xf0", "index": "teamId", "strideBytes": 184, "elementFieldDisplacements": [0, 16, 32, 48], "instructionOffsets": ["0xdaa", "0xdb1"]},
            ], solver_status="managed_fallback_observed"),
    _target(385452, COL_START, "UnsafeDo", "burst_range_dispatch_wrapper", 0x1867624AC, 0x1867626D4,
            "a1c75cee6d57da2caeb51378eef44c5e7e070a63088a09920a2373dfe20f682b",
            [_managed_call(385394, 0x186761454, "StartSimulationStepRangeKernel", "burst_wrapper")], solver_status="wrapper_only_burst_solver_unresolved"),
    _target(385454, COL_END, "Execute", "managed_dispatch_wrapper", 0x18675AA6C, 0x18675AB00,
            "82212005e41ac5518f49cdcdc8e3f3403c549899bd7042d70891b4ec3988cda5",
            [_managed_call(385455, 0x18675A9CC, "Execute(int)", "managed_fallback")], solver_status="wrapper_only"),
    _target(385455, COL_END, "Execute(int)", "managed_fallback", 0x18675A9CC, 0x18675AA6C,
            "f1c0ba8d18fa324f21aafd9c791f7658c7238d4bc4bfcacc5f1cd96268c8b297", [], accesses=[
                {"jobField": "jobColliderIndexList", "jobOffset": "0x0", "index": "Execute(index)", "strideBytes": 4, "elementFieldDisplacements": [0], "instructionOffsets": ["0x23"]},
                {"jobField": "nowPositions", "jobOffset": "0x10", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x35", "0x2f"]},
                {"jobField": "oldPositions", "jobOffset": "0x30", "index": "colliderIndex", "strideBytes": 24, "elementFieldDisplacements": [0, 16], "instructionOffsets": ["0x41", "0x45"]},
                {"jobField": "nowRotations", "jobOffset": "0x20", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x55"]},
                {"jobField": "oldRotations", "jobOffset": "0x40", "index": "colliderIndex", "strideBytes": 16, "elementFieldDisplacements": [0], "instructionOffsets": ["0x64"]},
            ], solver_status="managed_fallback_observed"),
    _target(385456, COL_END, "UnsafeDo", "burst_range_dispatch_wrapper", 0x18675AB00, 0x18675ABBC,
            "b8700fd30831d687414b987c03978d19b382aa2723816bc63e4fa2ce1e00c9b1",
            [_managed_call(385295, 0x18675A944, "EndSimulationStepRangeKernel", "burst_wrapper")], solver_status="wrapper_only_burst_solver_unresolved"),
]


def _verify_targets(gameassembly: Path) -> None:
    pe = _pe_image_module().PeImage(gameassembly)
    for row in TARGETS:
        va = int(row["va"], 16)
        size = int(row["spanBytes"])
        body = pe.bytes_at_va(va, size)
        if len(body) != size:
            raise ContractError(f"method {row['methodIndex']} span is truncated at {row['va']}")
        actual = hashlib.sha256(body).hexdigest()
        if actual != row["bodySha256"]:
            raise ContractError(
                f"method {row['methodIndex']} hash drift: {actual[:16]} != {row['bodySha256'][:16]}"
            )


def build_contract(
    gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
) -> dict[str, Any]:
    evidence = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if evidence.status != "validated":
        raise ContractError(f"native evidence gate {evidence.status}: {evidence.detail}")
    _verify_targets(evidence.gameassembly)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-solver-static.v1",
        "status": "native_spans_hash_pinned",
        "solverStatus": "managed_fallback_accesses_closed_burst_solver_unresolved",
        "nativeGate": {
            "gameAssembly": {"path": str(evidence.gameassembly), "size": evidence.gameassembly.stat().st_size, "sha256": evidence.gameassembly_sha256},
            "globalMetadata": {"path": str(evidence.metadata), "size": evidence.metadata.stat().st_size, "sha256": evidence.metadata_sha256},
        },
        "boundary": "NativeArray slots are outer job payload pointers; no NativeArray length field is read by indexed managed Execute bodies. _indexCount is read only by Execute() wrappers.",
        "targets": TARGETS,
    }


def _markdown(contract: dict[str, Any]) -> str:
    lines = ["# Secondary dynamics solver static boundary", "", f"Status: `{contract['status']}`.", "", contract["solverStatus"], "", "| Method | Role | Span | Solver classification | Next callee |", "|---|---|---:|---|---|"]
    for row in contract["targets"]:
        calls = ", ".join(f"{x['methodIndex']} `{x['va']}`" for x in row["nextCalls"]) or "—"
        lines.append(f"| {row['methodIndex']} {row['method']} | {row['role']} | `{row['va']}..{row['endVaExclusive']}` ({row['spanBytes']} B) | {row['solverStatus']} | {calls} |")
    lines += ["", "The indexed managed Execute bodies are the only rows with observed element arithmetic. Strides and element field displacements are evidence from the pinned x64 body; Burst range wrappers are not solver implementations.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    try:
        contract = build_contract(args.gameassembly, args.metadata)
    except ContractError as exc:
        print(f"[secondary-dynamics-static] {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(contract), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
