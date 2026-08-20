#!/usr/bin/env python3
"""Pin the managed end-of-step secondary-dynamics helper chain.

``EndSimulationStepJob.Execute(int)`` is the managed indexed fallback that
finishes one particle step.  Its body reads the fixed-client job arrays,
projects collision/velocity vectors through ``MathUtility`` helpers, and
writes velocity/friction/position results back to arrays.  This contract
records those byte-backed facts only.  It is not the Burst range kernel and
does not claim a complete secondary-dynamics solver or transform equivalence.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from capstone import CS_ARCH_X86, CS_MODE_64, CS_OP_IMM, CS_OP_MEM, Cs


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
JOB_LAYOUT_PATH = SOURCE_ROOT / "secondary_dynamics_job_layout_contract.json"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_integrator_contract.json"
DEFAULT_MARKDOWN = SOURCE_ROOT / "secondary_dynamics_integrator_contract.md"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0

METHOD_INDEX = 385708
EXPECTED_METHOD = {
    "type": "BeyondDynamicBone.SimulationManager+EndSimulationStepJob",
    "method": "Execute",
    "va": 0x18676E964,
    "bodySha256": "0b5d95b2c3da269554beb03aefabc2b5e6bdd6f2aa897943e1c4328e45e4d77c",
    "token": "0x06000875",
}

# These are the direct edges that form the managed integrator/helper chain.
# Other direct calls in the body (runtime patch plumbing and Unity math
# intrinsics) remain counted but are not assigned a fabricated semantic name.
EXPECTED_CHAIN_CALLS: tuple[tuple[int, int, int, str], ...] = (
    (0x3BB, 0x18673DEE8, 384698, "BeyondDynamicBone.TeamManager+TeamData.get_IsSpring"),
    (0x4C3, 0x184D87200, 386216, "BeyondDynamicBone.MathUtility.AutoToFloat3"),
    (0x55E, 0x186696AC8, 386213, "BeyondDynamicBone.MathUtility.Project"),
    (0xA1B, 0x184D87200, 386216, "BeyondDynamicBone.MathUtility.AutoToFloat3"),
    (0xA95, 0x1866B0CB4, 386214, "BeyondDynamicBone.MathUtility.ProjectOnPlane"),
    (0xCD3, 0x184D87200, 386216, "BeyondDynamicBone.MathUtility.AutoToFloat3"),
    (0xD43, 0x184D87200, 386216, "BeyondDynamicBone.MathUtility.AutoToFloat3"),
)

EXPECTED_HELPER_SPANS = {
    384698: {
        "type": "BeyondDynamicBone.TeamManager+TeamData",
        "method": "get_IsSpring",
        "va": 0x18673DEE8,
        "bodySha256": "bf6bb2d728e7f490306baa4a2a8295e3273d8a91a378f493af81e5aae33e1e77",
        "token": "0x06000483",
    },
    386213: {
        "type": "BeyondDynamicBone.MathUtility",
        "method": "Project",
        "va": 0x186696AC8,
        "bodySha256": "7eaabebfeb20205d0ea319d066cae13cfc4f4df938c066ce4361dafdbd6b3dd7",
        "token": "0x06000a6e",
    },
    386214: {
        "type": "BeyondDynamicBone.MathUtility",
        "method": "ProjectOnPlane",
        "va": 0x1866B0CB4,
        "bodySha256": "ca219c115689076aca94f79adefc4e14aa9672036a97217cbf70283e09959381",
        "token": "0x06000a6f",
    },
    386216: {
        "type": "BeyondDynamicBone.MathUtility",
        "method": "AutoToFloat3",
        "va": 0x184D87200,
        "bodySha256": "618a3b7dcb353a27723827ed14e05f3ba1453888fe7ca7ffdd0fa72441e702d8",
        "token": "0x06000a71",
    },
}

EXPECTED_HELPER_DIRECT_CALLS: dict[int, tuple[tuple[int, int], ...]] = {
    384698: ((0x10, 0x182F95A30), (0x31, 0x185396738), (0x3B, 0x1800D8260)),
    386213: ((0x4E, 0x185F0AE78), (0x63, 0x185F00E9C)),
    386214: ((0x53, 0x185F0AE78), (0x63, 0x185F00E9C), (0x98, 0x185F00F40)),
    386216: (),
}

# Every control-flow branch in the pinned indexed body.  The condition and
# relative destination are decoded from x64 instructions on each build.
EXPECTED_BRANCHES: tuple[tuple[int, str, int], ...] = (
    (0x74, "jne", 0x89), (0x9B, "jne", 0xDA1), (0x11C, "jne", 0xD4),
    (0x1A4, "jne", 0x15C), (0x225, "jne", 0x1DD), (0x292, "jne", 0x24A),
    (0x309, "jne", 0x2C1), (0x3B0, "jne", 0x3C8), (0x3C2, "je", 0xD00),
    (0x468, "je", 0x6EE), (0x472, "jbe", 0x6EE), (0x47C, "jbe", 0x6EE),
    (0x5E7, "ja", 0x610), (0x605, "ja", 0x60A), (0x60E, "jmp", 0x618),
    (0x6EC, "jmp", 0x715), (0x7E4, "jbe", 0x813), (0x811, "jmp", 0x823),
    (0x839, "je", 0x93B), (0x84B, "jbe", 0x93B), (0x859, "jb", 0x93B),
    (0x95B, "jb", 0x98D), (0x999, "jbe", 0xC90), (0x9AB, "jbe", 0xC90),
    (0x9C5, "jb", 0xC90), (0xAD4, "jbe", 0xC90), (0xD9F, "jmp", 0xDC7),
    (0xDAE, "jne", 0xDB6),
)

# The materialized EndSimulationStepJob offsets come from the job-layout
# contract.  The builder re-reads and verifies them before accepting accesses.
EXPECTED_JOB_FIELDS = {
    "simulationDeltaTime": 0x0,
    "stepParticleIndexArray": 0x8,
    "teamDataArray": 0x18,
    "parameterArray": 0x28,
    "centerDataArray": 0x38,
    "attributes": 0x48,
    "vertexDepths": 0x58,
    "teamIdArray": 0x68,
    "nextPosArray": 0x78,
    "oldPosArray": 0x88,
    "velocityPosArray": 0x98,
    "velocityArray": 0xA8,
    "realVelocityArray": 0xB8,
    "frictionArray": 0xC8,
    "staticFrictionArray": 0xD8,
    "collisionNormalArray": 0xE8,
    "_indexCount": 0xF8,
}

# (instruction offset, field name).  These are direct job-payload pointer
# loads; the array element accesses below then show the particle/team index
# and byte width used by the managed fallback.
EXPECTED_JOB_POINTER_LOADS = (
    (0xA1, "stepParticleIndexArray"), (0xB9, "teamIdArray"),
    (0xCD, "teamDataArray"), (0x142, "centerDataArray"),
    (0x1C4, "parameterArray"), (0x331, "attributes"),
    (0x349, "vertexDepths"), (0x35F, "nextPosArray"),
    (0x378, "oldPosArray"), (0x3C8, "collisionNormalArray"),
    (0x3D3, "velocityPosArray"), (0x3DE, "frictionArray"),
    (0x43C, "staticFrictionArray"), (0x715, "staticFrictionArray"),
    (0x943, "frictionArray"), (0xCEF, "velocityArray"),
    (0xD48, "realVelocityArray"), (0xD72, "oldPosArray"),
)

EXPECTED_SCALAR_LOADS = (
    (0x5D4, "simulationDeltaTime"), (0x754, "simulationDeltaTime"),
    (0xD6E, "simulationDeltaTime"), (0xD79, "simulationDeltaTime"),
    (0xD7D, "simulationDeltaTime"),
)

# (instruction offset, semantic field, base register, index register, scale,
# displacement, width, access).  The register roots are intentionally part of
# the evidence: a copied element stride without its real pointer/index chain
# is not sufficient to claim an integrator writeback.
EXPECTED_MEMORY_SITES = (
    (0xB5, "stepParticleIndexArray", "rax", "rdi", 4, 0, 4, "read"),
    (0xC1, "teamIdArray", "rax", "rdi", 2, 0, 2, "read"),
    (0x368, "nextPosArray", "rax", "rcx", 8, 0, 16, "read"),
    (0x36D, "nextPosArray", "rax", "rcx", 8, 16, 8, "read"),
    (0x37F, "oldPosArray", "rax", "rcx", 8, 0, 16, "read"),
    (0x384, "oldPosArray", "rax", "rcx", 8, 16, 8, "read"),
    (0x3EE, "collisionNormalArray", "r11", "r9", 4, 0, 8, "read"),
    (0x3F4, "collisionNormalArray", "r11", "r9", 4, 8, 4, "read"),
    (0x3F9, "velocityPosArray", "r15", "r14", 8, 0, 16, "read"),
    (0x405, "velocityPosArray", "r15", "r14", 8, 16, 8, "read"),
    (0x40C, "frictionArray", "rax", "rdi", 4, 0, 4, "read"),
    (0x455, "staticFrictionArray", "rax", "rdi", 4, 0, 4, "read"),
    (0x73D, "staticFrictionArray", "rax", "rdi", 4, 0, 4, "write"),
    (0x956, "frictionArray", "rax", "rdi", 4, 0, 4, "write"),
    (0xCF6, "velocityArray", "rax", "rdx", 4, 0, 8, "write"),
    (0xCFB, "velocityArray", "rax", "rdx", 4, 8, 4, "write"),
    (0xD84, "realVelocityArray", "rcx", "rdx", 4, 0, 8, "write"),
    (0xD89, "realVelocityArray", "rcx", "rdx", 4, 8, 4, "write"),
    (0xD93, "oldPosArray", "rax", "rcx", 8, 0, 16, "write"),
    (0xD98, "oldPosArray", "rax", "rcx", 8, 16, 8, "write"),
)
# The load which establishes the base pointer for each array access.  This is
# deliberately per-site (rather than merely "some load before it").
EXPECTED_MEMORY_POINTER_BINDINGS = {
    0xB5: 0xA1, 0xC1: 0xB9, 0x368: 0x35F, 0x36D: 0x35F,
    0x37F: 0x378, 0x384: 0x378, 0x3EE: 0x3C8, 0x3F4: 0x3C8,
    0x3F9: 0x3D3, 0x405: 0x3D3, 0x40C: 0x3DE, 0x455: 0x43C,
    0x73D: 0x715, 0x956: 0x943, 0xCF6: 0xCEF, 0xCFB: 0xCEF,
    0xD84: 0xD48, 0xD89: 0xD48, 0xD93: 0xD72, 0xD98: 0xD72,
}
EXPECTED_JOB_TYPE_INDEX = 48424
EXPECTED_FIELD_METADATA = {
    "simulationDeltaTime": (230433, 163868, "Single", 4, 0x0),
    "stepParticleIndexArray": (230434, 83201, "NativeArray", 16, 0x8),
    "teamDataArray": (230435, 83381, "NativeArray", 16, 0x18),
    "parameterArray": (230436, 83108, "NativeArray", 16, 0x28),
    "centerDataArray": (230437, 83349, "NativeArray", 16, 0x38),
    "attributes": (230438, 83290, "NativeArray", 16, 0x48),
    "vertexDepths": (230439, 83240, "NativeArray", 16, 0x58),
    "teamIdArray": (230440, 83197, "NativeArray", 16, 0x68),
    "nextPosArray": (230441, 83298, "NativeArray", 16, 0x78),
    "oldPosArray": (230442, 83298, "NativeArray", 16, 0x88),
    "velocityPosArray": (230443, 83298, "NativeArray", 16, 0x98),
    "velocityArray": (230444, 83304, "NativeArray", 16, 0xA8),
    "realVelocityArray": (230445, 83304, "NativeArray", 16, 0xB8),
    "frictionArray": (230446, 83240, "NativeArray", 16, 0xC8),
    "staticFrictionArray": (230447, 83240, "NativeArray", 16, 0xD8),
    "collisionNormalArray": (230448, 83304, "NativeArray", 16, 0xE8),
    "_indexCount": (230449, 83620, "NativeReference", 16, 0xF8),
}

EXPECTED_TEAM_STRIDE = (0xC6, 0x1D0)
EXPECTED_DIRECT_CALL_COUNT = {METHOD_INDEX: 52, 384698: 3, 386213: 2, 386214: 3, 386216: 0}
EXPECTED_UNRESOLVED_CALL_COUNT = {METHOD_INDEX: 31, 384698: 1, 386213: 2, 386214: 3, 386216: 0}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the fixed-client evidence no longer closes."""


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
    return (
        _load("secondary_integrator_metadata", root / "catalog_option_flow_metadata.py"),
        _load("secondary_integrator_native", root / "map_body_targets_to_gameassembly.py"),
    )


def _sha256(path: Path) -> str:
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


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _repo_path(path), "size": path.stat().st_size, "sha256": digest or _sha256(path)}


def _native_gate(gameassembly: Path | None, metadata: Path | None) -> tuple[Path, Path, dict[str, Any]]:
    evidence = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if evidence.status != "validated":
        raise ContractError(f"common.check_installed_native_inputs [{evidence.status}]: {evidence.detail}")
    game_path = Path(evidence.gameassembly)
    metadata_path = Path(evidence.metadata)
    return game_path, metadata_path, {
        "gameAssembly": _file(game_path, evidence.gameassembly_sha256),
        "globalMetadata": _file(metadata_path, evidence.metadata_sha256),
    }


def _method_rows(native: Any, md: Any, pe: Any) -> tuple[dict[int, list[dict[str, Any]]], list[int]]:
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(f"code registration drift: {code_registration!r} != 0x{EXPECTED_CODE_REGISTRATION:x}")
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    _, by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    all_pointers = sorted(pointer for pointer in by_pointer if pointer)
    return by_pointer, all_pointers


def _resolve_method(md: Any, by_pointer: dict[int, list[dict[str, Any]]], method_index: int, expected: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    candidates = [
        (pointer, signature)
        for pointer, signatures in by_pointer.items()
        for signature in signatures
        if int(signature.get("methodIndex", -1)) == method_index
    ]
    if len(candidates) != 1:
        raise ContractError(f"method {method_index} resolves to {len(candidates)} native pointers")
    pointer, signature = candidates[0]
    if pointer != int(expected["va"]):
        raise ContractError(f"method {method_index} VA drift: 0x{pointer:x} != 0x{int(expected['va']):x}")
    if signature.get("type") != expected["type"] or signature.get("method") != expected["method"] or str(signature.get("token", "")).lower() != str(expected.get("token", "")).lower():
        raise ContractError(f"method {method_index} identity drift")
    return pointer, signature


def _span_record(native: Any, md: Any, pe: Any, by_pointer: dict[int, list[dict[str, Any]]], all_pointers: list[int], method_index: int, expected: dict[str, Any]) -> tuple[dict[str, Any], bytes, list[dict[str, Any]], int]:
    pointer, signature = _resolve_method(md, by_pointer, method_index, expected)
    position = bisect.bisect_right(all_pointers, pointer)
    if position >= len(all_pointers):
        raise ContractError(f"method {method_index} has no bounded next pointer")
    end = all_pointers[position]
    body = pe.bytes_at_va(pointer, end - pointer)
    if len(body) != end - pointer:
        raise ContractError(f"method {method_index} span truncated")
    digest = hashlib.sha256(body).hexdigest()
    if digest != expected["bodySha256"]:
        raise ContractError(f"method {method_index} body hash drift: {digest[:16]} != {expected['bodySha256'][:16]}")
    calls, unresolved = native.scan_direct_calls(
        pe, pointer, end - pointer, by_pointer, set(), include_unresolved=True, arg_context_window=0
    )
    if len(calls) != EXPECTED_DIRECT_CALL_COUNT[method_index] or unresolved != EXPECTED_UNRESOLVED_CALL_COUNT[method_index]:
        raise ContractError(f"method {method_index} direct-call census drift: {len(calls)}/{unresolved}")
    return {
        "methodIndex": method_index,
        "type": signature["type"],
        "method": signature["method"],
        "token": signature["token"],
        "va": f"0x{pointer:x}",
        "endVaExclusive": f"0x{end:x}",
        "spanBytes": end - pointer,
        "bodySha256": digest,
        "directCallCount": len(calls),
        "unresolvedDirectCallCount": unresolved,
    }, body, calls, pointer


def _call_target(calls: list[dict[str, Any]], offset: int, target: int, method_index: int | None, label: str, md: Any | None = None) -> dict[str, Any]:
    matches = [row for row in calls if int(row["offset"]) == offset]
    if len(matches) != 1 or int(matches[0]["targetVa"], 16) != target:
        raise ContractError(f"method {method_index} call {label} at 0x{offset:x} drift")
    resolved = matches[0].get("resolved", [])
    if method_index is not None and not any(int(row.get("methodIndex", -1)) == method_index for row in resolved):
        raise ContractError(f"method {method_index} call {label} has no metadata identity")
    if method_index is not None and md is not None:
        method = md.methods[method_index]
        actual_type = md.type_full_name(md.types[method.declaring_type])
        actual_name = md.string(method.name_index)
        actual_token = f"0x{int(method.token):08x}"
        if label != f"{actual_type}.{actual_name}":
            raise ContractError(f"call label drift at 0x{offset:x}: {label!r} != {actual_type}.{actual_name}")
        row = next(row for row in resolved if int(row.get("methodIndex", -1)) == method_index)
        if row.get("type") != actual_type or row.get("method") != actual_name or str(row.get("token", "")).lower() != actual_token:
            raise ContractError(f"call metadata identity drift at 0x{offset:x}")
    return {
        "offset": f"0x{offset:x}",
        "targetVa": f"0x{target:x}",
        "methodIndex": method_index,
        "method": label,
        "resolved": resolved,
    }


def _branches(body: bytes, start: int) -> list[dict[str, Any]]:
    cs = Cs(CS_ARCH_X86, CS_MODE_64)
    cs.detail = True
    rows: list[dict[str, Any]] = []
    for instruction in cs.disasm(body, start):
        if not instruction.mnemonic.startswith("j"):
            continue
        if not instruction.operands or instruction.operands[0].type != CS_OP_IMM:
            raise ContractError(f"branch at 0x{instruction.address - start:x} has no immediate target")
        rows.append({
            "offset": instruction.address - start,
            "condition": instruction.mnemonic,
            "targetOffset": instruction.operands[0].imm - start,
            "opcode": instruction.bytes.hex(),
        })
    expected = [(offset, condition, target) for offset, condition, target in EXPECTED_BRANCHES]
    actual = [(row["offset"], row["condition"], row["targetOffset"]) for row in rows]
    if actual != expected:
        raise ContractError(f"integrator branch decode drift: {actual!r} != {expected!r}")
    return [{**row, "offset": f"0x{row['offset']:x}", "targetOffset": f"0x{row['targetOffset']:x}"} for row in rows]


def _memory_instruction(body: bytes, method_offset: int, operand_index: int | None = None) -> Any:
    cs = Cs(CS_ARCH_X86, CS_MODE_64)
    cs.detail = True
    start = 0x18676E964
    for instruction in cs.disasm(body, start):
        if instruction.address - start != method_offset:
            continue
        candidates = [
            (index, operand)
            for index, operand in enumerate(instruction.operands)
            if operand.type == CS_OP_MEM and (operand_index is None or index == operand_index)
        ]
        if len(candidates) != 1:
            raise ContractError(f"memory site 0x{method_offset:x} is not memory")
        _, operand = candidates[0]
        mem = operand.mem
        return {
            "mnemonic": instruction.mnemonic,
            "rawBytes": instruction.bytes.hex(),
            "base": instruction.reg_name(mem.base) if mem.base else None,
            "index": instruction.reg_name(mem.index) if mem.index else None,
            "scale": mem.scale,
            "displacement": mem.disp,
            "widthBytes": operand.size,
        }
    raise ContractError(f"memory site 0x{method_offset:x} does not decode")


def _verify_memory(body: bytes, job_fields: dict[str, int], pointer_loads: tuple[tuple[int, str], ...]) -> list[dict[str, Any]]:
    if len(EXPECTED_MEMORY_SITES) != len(set(EXPECTED_MEMORY_SITES)):
        raise ContractError("memory-site census contains duplicates")
    rows: list[dict[str, Any]] = []
    for offset, field, base, index, scale, displacement, width, access in EXPECTED_MEMORY_SITES:
        if field not in job_fields:
            raise ContractError(f"memory site {field} is not a canonical job field")
        bound_load = EXPECTED_MEMORY_POINTER_BINDINGS.get(offset)
        matching_loads = [load_offset for load_offset, load_field in pointer_loads if load_field == field]
        if bound_load not in matching_loads:
            raise ContractError(f"memory site {field} at 0x{offset:x} has no canonical pointer load")
        decoded = _memory_instruction(body, offset, 0 if access == "write" else 1)
        if (decoded["base"], decoded["index"], decoded["scale"], decoded["displacement"], decoded["widthBytes"]) != (base, index, scale, displacement, width):
            raise ContractError(f"memory site {field} at 0x{offset:x} drift: {decoded}")
        mnemonic = str(decoded["mnemonic"])
        is_write = mnemonic.startswith("mov") and offset in {0x73D, 0x956, 0xCF6, 0xCFB, 0xD84, 0xD89, 0xD93, 0xD98}
        if (access == "write") != is_write:
            raise ContractError(f"memory site {field} at 0x{offset:x} write direction drift")
        rows.append({"offset": f"0x{offset:x}", "field": field, "access": access, **decoded, "displacement": f"0x{displacement:x}"})
    # The team-data native stride is an immediate in an imul rather than a
    # memory operand.  Decode its bytes through Capstone and retain the exact
    # instruction as separate evidence.
    cs = Cs(CS_ARCH_X86, CS_MODE_64)
    stride_instruction = next((ins for ins in cs.disasm(body, 0x18676E964) if ins.address - 0x18676E964 == EXPECTED_TEAM_STRIDE[0]), None)
    if stride_instruction is None or stride_instruction.mnemonic != "imul" or "0x1d0" not in stride_instruction.op_str.lower():
        raise ContractError("teamDataArray x teamId stride decode drift")
    return rows


def _job_layout(gate: dict[str, Any]) -> dict[str, Any]:
    if not JOB_LAYOUT_PATH.is_file():
        raise ContractError(f"missing canonical job layout: {JOB_LAYOUT_PATH}")
    payload = json.loads(JOB_LAYOUT_PATH.read_text(encoding="utf-8"))
    if payload.get("status") != "outer_job_layout_closed" or payload.get("outer_job_layout_recovered") is not True or payload.get("job_payload_layout_recovered") is not False:
        raise ContractError("canonical job layout status is not closed")
    native_gate = payload.get("native_gate", {})
    for key, expected_hash in (("gameAssembly", EXPECTED_GAME_ASSEMBLY_SHA256), ("globalMetadata", EXPECTED_METADATA_SHA256)):
        if native_gate.get(key, {}).get("sha256", "").lower() != expected_hash:
            raise ContractError(f"canonical job layout native gate drift: {key}")
        if native_gate.get(key, {}).get("sha256", "").lower() != gate[key]["sha256"].lower() or native_gate.get(key, {}).get("size") != gate[key]["size"]:
            raise ContractError(f"canonical job layout does not match selected native gate: {key}")
    rows = [row for row in payload.get("jobs", []) if row.get("type") == EXPECTED_METHOD["type"]]
    if len(rows) != 1:
        raise ContractError("canonical job layout lacks unique EndSimulationStepJob")
    raw_fields = rows[0].get("fields", [])
    if int(rows[0].get("typeIndex", -1)) != EXPECTED_JOB_TYPE_INDEX:
        raise ContractError("canonical job typeIndex drift")
    if len(raw_fields) != len(EXPECTED_JOB_FIELDS) or len({row.get("name") for row in raw_fields}) != len(raw_fields):
        raise ContractError("canonical EndSimulationStepJob field set is incomplete or duplicated")
    fields = {str(row["name"]): int(str(row["nativePayloadOffset"]), 16) for row in raw_fields}
    if fields != EXPECTED_JOB_FIELDS or set(fields) != set(EXPECTED_FIELD_METADATA):
        raise ContractError(f"EndSimulationStepJob field offsets drift: {fields!r}")
    for row in raw_fields:
        if not isinstance(row.get("fieldIndex"), int) or not isinstance(row.get("metadataTypeIndex"), int) or not row.get("kind") or int(row.get("slotWidthBytes", 0)) <= 0:
            raise ContractError(f"canonical field metadata incomplete: {row.get('name')}")
    if [int(row["fieldIndex"]) for row in raw_fields] != list(range(230433, 230450)):
        raise ContractError("canonical field index set drift")
    for row in raw_fields:
        expected = EXPECTED_FIELD_METADATA.get(str(row["name"]))
        actual = (int(row["fieldIndex"]), int(row["metadataTypeIndex"]), str(row["kind"]), int(row["slotWidthBytes"]), int(str(row["nativePayloadOffset"]), 16))
        if expected != actual:
            raise ContractError(f"canonical field provenance drift: {row.get('name')}")
    return {"path": _repo_path(JOB_LAYOUT_PATH), "sha256": _sha256(JOB_LAYOUT_PATH), "fields": {name: f"0x{value:x}" for name, value in fields.items()}}


def _job_pointer_rows(body: bytes) -> list[dict[str, Any]]:
    cs = Cs(CS_ARCH_X86, CS_MODE_64)
    cs.detail = True
    start = 0x18676E964
    rows: list[dict[str, Any]] = []
    if len(EXPECTED_JOB_POINTER_LOADS) != len(set(EXPECTED_JOB_POINTER_LOADS)) or len(EXPECTED_SCALAR_LOADS) != len(set(EXPECTED_SCALAR_LOADS)):
        raise ContractError("job-load census contains duplicates")
    for offset, field in EXPECTED_JOB_POINTER_LOADS:
        decoded = _memory_instruction(body, offset, 1)
        if decoded["base"] != "rbx" or decoded["displacement"] != EXPECTED_JOB_FIELDS[field] or decoded["widthBytes"] != 8:
            raise ContractError(f"job pointer load {field} at 0x{offset:x} drift: {decoded}")
        rows.append({"offset": f"0x{offset:x}", "field": field, **decoded, "displacement": f"0x{decoded['displacement']:x}"})
    for offset, field in EXPECTED_SCALAR_LOADS:
        decoded = _memory_instruction(body, offset, 1)
        if decoded["base"] != "rbx" or decoded["displacement"] != EXPECTED_JOB_FIELDS[field] or decoded["widthBytes"] != 4:
            raise ContractError(f"scalar load {field} at 0x{offset:x} drift: {decoded}")
        rows.append({"offset": f"0x{offset:x}", "field": field, **decoded, "displacement": f"0x{decoded['displacement']:x}"})
    return rows


def build_contract(gameassembly: Path | None = DEFAULT_GAME_ASSEMBLY, metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    if len(EXPECTED_CHAIN_CALLS) != 7 or len({(o, t, i) for o, t, i, _ in EXPECTED_CHAIN_CALLS}) != 7:
        raise ContractError("direct-call chain census is incomplete or duplicated")
    if set(EXPECTED_HELPER_SPANS) != {384698, 386213, 386214, 386216} or set(EXPECTED_HELPER_DIRECT_CALLS) != set(EXPECTED_HELPER_SPANS):
        raise ContractError("helper span census is incomplete")
    if len(EXPECTED_JOB_POINTER_LOADS) != 18 or len(EXPECTED_SCALAR_LOADS) != 5 or len(EXPECTED_MEMORY_SITES) != 20:
        raise ContractError("bounded job/access census is incomplete")
    game_path, metadata_path, gate = _native_gate(gameassembly, metadata)
    catalog, native = _helpers()
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    by_pointer, all_pointers = _method_rows(native, md, pe)
    main_expected = dict(EXPECTED_METHOD)
    main, body, calls, pointer = _span_record(native, md, pe, by_pointer, all_pointers, METHOD_INDEX, main_expected)
    chain_calls = []
    for offset, target, method_index, label in EXPECTED_CHAIN_CALLS:
        chain_calls.append(_call_target(calls, offset, target, method_index, label, md))

    helper_rows: list[dict[str, Any]] = []
    for method_index, expected in sorted(EXPECTED_HELPER_SPANS.items()):
        row, helper_body, helper_calls, _ = _span_record(native, md, pe, by_pointer, all_pointers, method_index, expected)
        actual_pairs = {(int(call["offset"]), int(call["targetVa"], 16)) for call in helper_calls}
        expected_pairs = set(EXPECTED_HELPER_DIRECT_CALLS[method_index])
        if actual_pairs != expected_pairs:
            raise ContractError(f"helper {method_index} direct-call chain drift: {actual_pairs!r} != {expected_pairs!r}")
        selected = []
        for offset, target in EXPECTED_HELPER_DIRECT_CALLS[method_index]:
            selected.append(_call_target(helper_calls, offset, target, None, f"{expected['type']}.{expected['method']}"))
        row["selectedDirectCalls"] = selected
        helper_rows.append(row)

    return {
        "schema": "endfield.charinfo.secondary-dynamics-integrator.v1",
        "status": "native_spans_hash_pinned_managed_integrator_boundary",
        "solverStatus": "managed_end_step_helper_chain_only_burst_solver_unresolved",
        "secondaryDynamicsVerified": False,
        "nativeGate": gate,
        "canonicalJobLayout": _job_layout(gate),
        "root": {**main, "jobPointerLoads": _job_pointer_rows(body), "branches": _branches(body, pointer), "memoryAccesses": _verify_memory(body, EXPECTED_JOB_FIELDS, EXPECTED_JOB_POINTER_LOADS), "selectedHelperCalls": chain_calls},
        "helperBodies": helper_rows,
        "boundary": "EndSimulationStepJob.Execute(int) is a managed fallback. Its array writebacks and MathUtility helper edges are pinned, but the Burst EndSimulationStepRangeKernel and complete solver remain unresolved.",
    }


def _markdown(contract: dict[str, Any]) -> str:
    root = contract["root"]
    lines = [
        "# Secondary dynamics managed integrator boundary",
        "",
        f"Status: `{contract['status']}`.",
        "",
        contract["solverStatus"],
        "",
        f"Indexed method `385708` span `{root['va']}..{root['endVaExclusive']}` ({root['spanBytes']} bytes), body hash `{root['bodySha256']}`.",
        "",
        "The fixed-client managed fallback reads the step/team and secondary-dynamics arrays, calls `TeamData.get_IsSpring`, `MathUtility.Project`, `ProjectOnPlane`, and `AutoToFloat3`, then writes velocity/friction/old-position array values. These are static byte facts, not Burst or transform equivalence.",
        "",
        "| Helper method | Span | Direct calls |",
        "|---|---|---:|",
    ]
    for row in contract["helperBodies"]:
        lines.append(f"| `{row['methodIndex']} {row['method']}` | `{row['va']}..{row['endVaExclusive']}` ({row['spanBytes']} B) | {len(row['selectedDirectCalls'])} selected |")
    lines += ["", f"Branches pinned: {len(root['branches'])}; memory sites pinned: {len(root['memoryAccesses'])}; selected helper edges: {len(root['selectedHelperCalls'])}.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true", help="verify checked-in output without writing")
    args = parser.parse_args()
    try:
        contract = build_contract(args.gameassembly, args.metadata)
    except (ContractError, OSError, ValueError) as exc:
        print(f"[secondary-dynamics-integrator] {exc}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or not args.markdown.is_file():
            print("[secondary-dynamics-integrator] checked-in output is missing", file=sys.stderr)
            return 2
        if json.loads(args.output.read_text(encoding="utf-8")) != contract or args.markdown.read_text(encoding="utf-8") != _markdown(contract):
            print("[secondary-dynamics-integrator] checked-in output is stale", file=sys.stderr)
            return 2
        print(f"checked {args.output} and {args.markdown}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(_markdown(contract), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
