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
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from capstone import CS_ARCH_X86, CS_MODE_64, CS_OP_MEM, CS_OP_REG, Cs
except ImportError as exc:  # pragma: no cover - native evidence cannot be checked without it
    raise RuntimeError("capstone is required for the transform-read native writer audit") from exc


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
    ("MagicaManager..cctor through static defaults", 385109, "0x184cf53d0", 0x4CF39D0, 171, "20a1f98600d1dd19a0d48fb654d54887f535a629f661b5df0a374c34ada7155b"),
    ("BeyondBoneCloth.get_bUseRelativeTransform", 383548, "0x184d86f90", 0x4D85590, 5, "dd59d7db8b7cc28acba8b73658d8a5d3ff5c6184e1209c8a81e6e6c41512b249"),
    ("TeamData.get_bUseRelativeTransform active body", 384682, "0x18673e0d4", 0x673C6D4, 41, "18acb47564555c60fcb1b34f31d94567a25dc24314cb839e9c5a7937ada6b4c4"),
    ("TeamManager.AlwaysTeamUpdate primary relative propagation", 384596, "0x1835bf8f0", 0x35BDEF0, 51, "9d02ec2876a1f13b0c401cdfa78c94a437770f02c1d897cd9eb5142d3f7e87b8"),
    ("TeamManager.AlwaysTeamUpdate synchronized relative propagation", 384596, "0x1835bfc85", 0x35BE285, 53, "859c08440b5cd1a269056b6adf60a7528812f2a66e891eee393a2d004d74f8c0"),
    ("DynamicBoneTransformManager.CopyDoubleBuffer active body", 384479, "0x183d42300", 0x3D40900, 335, "cda347050a942ff4ccc2aaa35d7d064b36a4087f06b4c9b17e9eeef9f1f98e18"),
    ("ClothManager.ClothUpdate transform-input branch region", 384441, "0x182f91cc9", 0x2F902C9, 772, "c13f2c0c6e0f90e21026902783f404ec7c4bc9a4247ee125a5c7c58cd1e4d017"),
    ("ClothManager.ClothUpdate complete selector body", 384441, "0x182f918a0", 0x2F8FEA0, 6256, "a1065dd5aaa62d715dc756e8ce87a4630d629d303494df34fb9d949b2231d077"),
    ("BeyondBoneCloth.set_bUseRelativeTransform", 383549, "0x184d86fa0", 0x4D855A0, 16, "4fe4a69cef9b16817af29745e9cee3e8d6b5b734848871512eb9f11740f143d8"),
    ("BeyondBoneCloth.SetRelativeTransform", 383550, "0x18668ce7c", 0x668B47C, 620, "b40f228e52934995785d67a87a44bbc507b46f09e8c1f45cdf8ab6e3a6252eee"),
    ("CharacterAnimationComponent.SetClothTransformPreTeleport", 51183, "0x186c644b4", 0x6C62AB4, 1288, "64ba58dcced9abfcdc734bb7d34b8a77781ff155f598747ed250874edd51a237"),
    ("ClothCalculator.TeleportClothUseRelativeTransform", 2026, "0x18742cdc4", 0x742B3C4, 580, "6e2b937c43470da003d5144dddf76e4bca4b94fc664bf4e320b5462a2bfccec4"),
    ("ClothCalculator.ResetCloth", 2027, "0x18742c5f0", 0x742ABF0, 712, "e80c6cd6ad47541624371ebf15dfd5b8dfa5d723b5a6a42e1ff54fae4ac79fd8"),
    ("MagicaManager.SetUseCrossFrameJob", 385092, "0x186750314", 0x674E914, 152, "7f8177e11c6bae26c38cb5905ccf9333f34c28268979c0d284695370058e27ce"),
    ("CinematicTimelineManagerBase.SquadMemberVisible", 60810, "0x186da2d7c", 0x6DA137C, 300, "4f8ad2b37d7f611a39f6a61bb026855a73cfe5c3684ebc6fb068d6a5845f40a7"),
    ("MainStreamTimelineManagerBase.PrepareToPlayMainTimeline", 61287, "0x186dbfd48", 0x6DBE348, 368, "9628cacf3df5cf75434e4fcde9a8deba92471372d1640c649a6a055be2076945"),
    ("MainStreamTimelineManagerBase.RecoverMainTimeline", 61284, "0x186dbff54", 0x6DBE554, 304, "809f5829b731d3645a5cb56a2cb3715bc34fdfe2f5b6351f28d1c18b376ead08"),
    ("PhysicsClothQuality.Apply", 478837, "0x18ac426f4", 0xAC40CF4, 176, "3421131db5f08226318cc5849e9efdad3154e6042cc4efc4f1a833b85783e051"),
)

IMAGE_BASE = 0x180000000
MAGICA_MANAGER_TYPEINFO_SLOT_VA = 0x18E396218
EXPECTED_USE_ANIMATOR_WRITERS = (0x184CF5449,)
EXPECTED_USE_CROSS_FRAME_WRITERS = (0x184CF5437, 0x186750378, 0x18AC42772)
DIRECT_CALL_TARGETS = {
    "CopyDoubleBuffer": (0x183D42300, ()),
    "ReadTransform": (0x183B127D0, (0x182F91D47, 0x182F91FFB)),
    "ReadAnimatorBufferData": (0x186725E4C, (0x182F91E60,)),
    "WriteTransform": (0x18672641C, (0x182F9245C,)),
    "WriteAnimatorBufferData": (0x186726158, (0x182F92955, 0x186718171)),
    "BeyondBoneCloth.set_bUseRelativeTransform": (0x184D86FA0, ()),
    "CharacterAnimationComponent.SetClothTransformPreTeleport": (0x186C644B4, ()),
    "BeyondBoneCloth.SetRelativeTransform": (
        0x18668CE7C,
        (0x186C647AB, 0x186C6487F, 0x18742C7F5, 0x18742CF34),
    ),
    "ClothCalculator.TeleportClothUseRelativeTransform": (
        0x18742CDC4, (0x186DE3D4B, 0x1874A3431)),
    "ClothCalculator.ResetCloth": (0x18742C5F0, (0x186DDFBFE, 0x1874A0906)),
    "NPCCPUAnimator.TeleportClothUseRelativeTransform": (0x1874A31F0, (0x186A9F4B6,)),
    "NPCCPUAnimator.ResetCloth": (0x1874A08C4, (0x186A9F4D3,)),
    "ScriptAnimationJobSyncMono.ResetCloth": (0x186DDF9A8, (0x18B34F2F9,)),
    "MagicaManager.SetUseCrossFrameJob": (
        0x186750314,
        (0x186DA2E5B, 0x186DBFE79, 0x186DC0040),
    ),
}

PINNED_INSTRUCTIONS = (
    ("SetRelativeTransform true-to-false store", "0x18668cf04", 0x668B504, "40887778"),
    ("SetRelativeTransform enable store", "0x18668d025", 0x668B625, "c6477801"),
    ("property setter backing-field store", "0x184d86fa0", 0x4D855A0, "885178c3"),
    ("SetUseCrossFrameJob live store", "0x186750378", 0x674E978, "88590948"),
    ("cctor UseCrossFrameJob=true", "0x184cf5437", 0x4CF3A37, "c6410901"),
    ("cctor UseAnimatorTransform=false", "0x184cf5449", 0x4CF3A49, "4488510a"),
    ("SquadMemberVisible restore true", "0x186da2e57", 0x6DA1457, "33d2b101e8b4d49aff"),
    ("PrepareToPlayMainTimeline set false", "0x186dbfe75", 0x6DBE475, "33d233c9e8960499ff"),
    ("RecoverMainTimeline restore true", "0x186dc003c", 0x6DBE63C, "33d2b101e8cf0299ff"),
    ("PhysicsClothQuality.Apply configured store", "0x18ac42764", 0xAC40D64, "488b05ad3a7503488b88b8000000885909"),
    ("ClothUpdate UseCrossFrameJob selector", "0x182f92425", 0x2F90A25, "488b81b8000000807809007534"),
    ("ClothUpdate UseAnimatorTransform selector", "0x182f9247b", 0x2F90A7B, "488b81b800000080780a000f85"),
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


def _pin_native_instructions(game_assembly: Path) -> list[dict[str, Any]]:
    image = game_assembly.read_bytes()
    rows = []
    for name, va, offset, expected_hex in PINNED_INSTRUCTIONS:
        expected = bytes.fromhex(expected_hex)
        actual = image[offset:offset + len(expected)]
        if actual != expected:
            raise ContractError(f"native instruction drift for {name}: {actual.hex()}")
        rows.append({
            "name": name,
            "va": va,
            "fileOffset": f"0x{offset:x}",
            "instructionBytes": actual.hex(" "),
        })
    return rows


def _executable_sections(image: bytes) -> list[tuple[int, int, int]]:
    """Return (file offset, byte size, VA) for executable PE sections."""
    if image[:2] != b"MZ":
        raise ContractError("GameAssembly is not a PE image")
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    if image[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ContractError("GameAssembly PE signature drift")
    section_count = struct.unpack_from("<H", image, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", image, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_size
    rows = []
    for index in range(section_count):
        base = section_table + index * 40
        virtual_address = struct.unpack_from("<I", image, base + 12)[0]
        raw_size = struct.unpack_from("<I", image, base + 16)[0]
        raw_offset = struct.unpack_from("<I", image, base + 20)[0]
        characteristics = struct.unpack_from("<I", image, base + 36)[0]
        if characteristics & 0x20000000 and raw_size:
            rows.append((raw_offset, raw_size, IMAGE_BASE + virtual_address))
    if not rows:
        raise ContractError("GameAssembly has no executable PE sections")
    return rows


def _direct_call_xrefs(image: bytes, sections: list[tuple[int, int, int]], target_va: int) -> tuple[int, ...]:
    result = []
    for raw_offset, raw_size, section_va in sections:
        payload = image[raw_offset:raw_offset + raw_size]
        cursor = 0
        while True:
            cursor = payload.find(b"\xe8", cursor)
            if cursor < 0:
                break
            if cursor + 5 <= len(payload):
                source_va = section_va + cursor
                displacement = struct.unpack_from("<i", payload, cursor + 1)[0]
                if source_va + 5 + displacement == target_va:
                    result.append(source_va)
            cursor += 1
    return tuple(result)


def _direct_call_xrefs_many(
    image: bytes,
    sections: list[tuple[int, int, int]],
    target_vas: set[int],
) -> dict[int, tuple[int, ...]]:
    """Resolve all selected rel32 call targets in one executable-section pass."""
    result: dict[int, list[int]] = {target: [] for target in target_vas}
    for raw_offset, raw_size, section_va in sections:
        payload = image[raw_offset:raw_offset + raw_size]
        cursor = 0
        while True:
            cursor = payload.find(b"\xe8", cursor)
            if cursor < 0:
                break
            if cursor + 5 <= len(payload):
                source_va = section_va + cursor
                displacement = struct.unpack_from("<i", payload, cursor + 1)[0]
                target_va = source_va + 5 + displacement
                if target_va in result:
                    result[target_va].append(source_va)
            cursor += 1
    return {target: tuple(rows) for target, rows in result.items()}


def _audit_native_routes(game_assembly: Path) -> dict[str, Any]:
    image = game_assembly.read_bytes()
    sections = _executable_sections(image)
    xrefs_by_target = _direct_call_xrefs_many(
        image, sections, {target for target, _ in DIRECT_CALL_TARGETS.values()})
    call_rows = {}
    for name, (target, expected_xrefs) in DIRECT_CALL_TARGETS.items():
        actual = xrefs_by_target[target]
        if actual != expected_xrefs:
            raise ContractError(f"direct-call xrefs drift for {name}: {actual!r}")
        call_rows[name] = {
            "targetVa": f"0x{target:x}",
            "directCallCount": len(actual),
            "sourceVas": [f"0x{value:x}" for value in actual],
        }

    # MagicaManager's TypeInfo slot is independently joined by the pinned
    # cctor/ClothUpdate spans. Audit every compiled reference to that slot and
    # find writes to static_fields+0x0a (UseAnimatorTransform). This avoids
    # treating the cctor default as a live invariant if another method writes it.
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    writer_vas: dict[int, set[int]] = {0x09: set(), 0x0A: set()}
    rip_load_pattern = re.compile(rb"[\x48-\x4f][\x8b\x8d].{5}", re.DOTALL)
    for raw_offset, raw_size, section_va in sections:
        payload = image[raw_offset:raw_offset + raw_size]
        for match in rip_load_pattern.finditer(payload):
            cursor = match.start()
            prefix, opcode, modrm = match.group()[:3]
            if modrm & 0xC7 != 0x05:
                continue
            source_va = section_va + cursor
            if source_va + 7 + struct.unpack_from("<i", payload, cursor + 3)[0] != MAGICA_MANAGER_TYPEINFO_SLOT_VA:
                continue
            window = payload[cursor:cursor + 64]
            instructions = list(decoder.disasm(window, source_va))
            if not instructions or len(instructions[0].operands) < 2 or instructions[0].operands[0].type != CS_OP_REG:
                continue
            type_register = instructions[0].operands[0].reg
            static_register = None
            for instruction in instructions[1:]:
                if instruction.mnemonic.startswith("j") or instruction.mnemonic in ("call", "ret"):
                    break
                operands = instruction.operands
                if (len(operands) >= 2 and operands[0].type == CS_OP_REG and operands[1].type == CS_OP_MEM
                        and operands[1].mem.base == type_register and operands[1].mem.disp == 0xB8):
                    static_register = operands[0].reg
                    continue
                if static_register is None:
                    continue
                for operand_index, operand in enumerate(operands):
                    if (operand.type != CS_OP_MEM or operand.mem.base != static_register
                            or operand.mem.disp not in writer_vas):
                        continue
                    if operand_index == 0 and instruction.mnemonic.startswith("mov"):
                        writer_vas[operand.mem.disp].add(instruction.address)
    actual_cross_writers = tuple(sorted(writer_vas[0x09]))
    actual_animator_writers = tuple(sorted(writer_vas[0x0A]))
    if actual_cross_writers != EXPECTED_USE_CROSS_FRAME_WRITERS:
        raise ContractError(f"UseCrossFrameJob writer audit drift: {actual_cross_writers!r}")
    if actual_animator_writers != EXPECTED_USE_ANIMATOR_WRITERS:
        raise ContractError(f"UseAnimatorTransform writer audit drift: {actual_animator_writers!r}")
    return {
        "directCalls": call_rows,
        "magicaManagerStaticFields": {
            "typeInfoSlotVa": f"0x{MAGICA_MANAGER_TYPEINFO_SLOT_VA:x}",
            "cctorDefaults": {"EnableTick": True, "UseCrossFrameJob": True, "UseAnimatorTransform": False},
            "useCrossFrameJobCompiledWriterVas": [f"0x{value:x}" for value in actual_cross_writers],
            "useCrossFrameJobWriterBoundary": "the cctor, SetUseCrossFrameJob, and PhysicsClothQuality.Apply are the complete compiled static-field writer set",
            "useAnimatorTransformCompiledWriterVas": [f"0x{value:x}" for value in actual_animator_writers],
            "useAnimatorTransformWriterBoundary": "the sole compiled writer is MagicaManager..cctor; no managed setter exists in pinned metadata",
        },
    }


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
    native_routes = _audit_native_routes(ga)
    return {
        "schema": "endfield.charinfo.secondary-dynamics-transform-read.v1",
        "status": "endminf_transform_read_callback_closed_relative_and_cross_frame_telemetry_required",
        "nativeGate": native_gate,
        "sources": {"payload": payload_source, "transformWriteback": writeback_source,
                    "callback": callback_source, "schedule": schedule_source},
        "native": {"pinnedSpans": _pin_native_spans(ga),
                   "pinnedInstructions": _pin_native_instructions(ga),
                   "routeAudit": native_routes, "ifix": {
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
            "copyDoubleBufferCadence": {
                "publicMethodDirectCallCountInPinnedImage": 0,
                "callsPerClothUpdate": 0,
                "activeRoute": "not called by ClothManager.ClothUpdate; CopyDoubleBufferJob is therefore not scheduled by the statically closed target pipeline",
                "boundary": "the copy equations describe the dormant public method, not an invented per-frame current-to-last transition",
            },
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
            "sourceStaticBranch": {
                "UseAnimatorTransform": {
                    "value": False,
                    "proof": "MagicaManager..cctor writes static_fields+0x0a = 0; an exhaustive compiled TypeInfo writer audit finds no other writer and pinned metadata exposes no setter",
                    "selectedRoute": "ordinary TransformAccess ReadTransform route; ReadAnimatorBufferData is skipped",
                },
                "UseCrossFrameJob": {
                    "cctorDefault": True,
                    "targetValue": None,
                    "targetLiveValueClosed": False,
                    "routes": {"true": "skip the second ReadTransform at ClothUpdate+0x75b", "false": "execute the second ReadTransform"},
                    "writerAudit": "the cctor, SetUseCrossFrameJob, and PhysicsClothQuality.Apply are the complete compiled writers of MagicaManager static_fields+0x09",
                    "qualityProfileWriter": {
                        "type": "Beyond.Scripts.Quality.Components.PhysicsClothQuality",
                        "field": "UseCrossFrameJob at object+0x19",
                        "applyEquation": "MagicaManager.UseCrossFrameJob = PhysicsClothQuality.UseCrossFrameJob",
                        "targetAuthoredValueClosed": False,
                    },
                    "transitions": [
                        "PhysicsClothQuality.Apply stores its authored UseCrossFrameJob byte from object+0x19 directly, after the cctor and without calling SetUseCrossFrameJob",
                        "PrepareToPlayMainTimeline conditionally stores false and records its return in timeline+0x188",
                        "RecoverMainTimeline restores true only when timeline+0x188 is set",
                        "CinematicTimelineManagerBase.SquadMemberVisible restores true when its +0x188 flag is set, then clears that flag",
                    ],
                    "targetBoundary": "ordinary Character Info playback excludes the main-stream/cinematic temporary transitions, but no accepted serialized quality-profile evidence pins PhysicsClothQuality.UseCrossFrameJob for the captured session",
                },
            },
            "perFrameOrdering": ["ReadTransform call site 1191", "WriteDoubleBufferTransform call site 1232",
                                 "ReadAnimatorBufferData skipped because UseAnimatorTransform is false",
                                 "second ReadTransform call site 1883 only when live UseCrossFrameJob is false",
                                 "PreProxyMeshUpdate", "SimulationStepUpdate"],
            "orderingBoundary": "The animator-buffer branch is source-statically closed off. The quality-profile writer leaves the target-live cross-frame value open, so execution of the second ReadTransform needs one runtime byte. Public CopyDoubleBuffer has zero direct call sites and zero calls in ClothUpdate.",
        },
        "callbackWritebackSelector": {
            "selectorField": "MagicaManager.UseAnimatorTransform at static_fields+0x0a",
            "targetValue": False,
            "targetValueClosed": True,
            "writerAudit": "the cctor false store is the sole compiled writer; pinned metadata has no managed setter",
            "clothUpdateBranch": "after the UseCrossFrameJob branch, false selects the TransformAccess WriteTransform implementation; true selects WriteAnimatorBufferData",
            "targetRoute": "TransformAccess WriteTransform",
            "writeTransformDirectCallSite": "0x182f9245c",
            "writeAnimatorBufferDataDirectCallSite": "0x182f92955",
            "animatorBufferWritebackSelected": False,
            "runtimeTelemetryRequired": False,
        },
        "teamRelativeTransform": {
            "clothBackingField": "BeyondBoneCloth.<bUseRelativeTransform>k__BackingField at object+0x78",
            "initialValue": False,
            "initialValueBasis": "the backing field is absent from all four Endminf serialized type trees and is zero-initialized; serialized relativeTransformPos/Rot do not enable it",
            "teamPropagation": "AlwaysTeamUpdate writes TeamData.useRelativeTransform at native payload+0x9c from (cloth object+0x78 != 0) on both primary and synchronized routes",
            "teamBooleanEquation": "TeamData.bUseRelativeTransform = (useRelativeTransform > 0)",
            "writerAudit": {
                "propertySetter": "set_bUseRelativeTransform is a direct object+0x78 store and has zero direct callers in the pinned executable",
                "statefulWriter": "SetRelativeTransform contains the only source-visible stateful backing-field writes and has exactly four direct callers",
                "characterPreTeleportCallerBoundary": "CharacterAnimationComponent.SetClothTransformPreTeleport has zero direct callers; source-static evidence cannot exclude reflection, a delegate/function-pointer invocation, or a call before the accepted capture interval",
            },
            "stateMachine": {
                "enableFromFalse": "SetRelativeTransform(true,newPos,newRot): store newPos/newRot, then bUseRelativeTransform=true",
                "updateWhileTrue": "SetRelativeTransform(true,newPos,newRot): compose the existing relative frame with the new frame, then preserve true",
                "disableFromTrue": "SetRelativeTransform(false,...): store false and reset relativeTransformPos/Rot to the native zero/identity defaults",
                "falseWhileAlreadyFalse": "the body would initialize the supplied frame and set true; recovered reset callers rely on the active-relative precondition rather than treating false as an idempotent setter",
            },
            "compiledMutators": [
                {"method": "CharacterAnimationComponent.SetClothTransformPreTeleport", "callSites": ["0x186c647ab", "0x186c6487f"], "argument": True, "effect": "enable or update relative frame for both dynamic and static cloth lists"},
                {"method": "NPC.Animation.ClothCalculator.ResetCloth", "callSites": ["0x18742c7f5"], "argument": False, "effect": "disable after hard reset, or after soft reset when keepPose is false"},
                {"method": "NPC.Animation.ClothCalculator.TeleportClothUseRelativeTransform", "callSites": ["0x18742cf34"], "argument": True, "effect": "enable or update relative frame"},
            ],
            "resetTeleportCallGraph": [
                "ScriptAnimationJobSyncMono._UpdateClothRelativeTransform and NPCCPUAnimator.TeleportClothUseRelativeTransform feed ClothCalculator.TeleportClothUseRelativeTransform(true)",
                "ScriptAnimationJobSyncMono.ResetCloth and NPCCPUAnimator.ResetCloth feed ClothCalculator.ResetCloth",
                "NPCAbility.TeleportToImmediate invokes the NPCCPUAnimator teleport wrapper followed by its reset wrapper",
                "CharacterAnimationComponent.SetClothTransformPreTeleport is source-static dormant (zero direct call sites), but its public nonvirtual body remains a possible external/delegate entry before capture",
            ],
            "targetLiveValueClosed": False,
            "boundary": "stationary root motion proves no frame-to-frame root delta, but does not prove whether model placement enabled a persistent relative frame before the first captured ClothUpdate",
            "minimumRuntimeTelemetry": {
                "initialSample": "for MC_Ribbon2, MC_Hair, MC_Ribbon, and MC_Coat, read TeamData.useRelativeTransform at payload+0x9c after AlwaysTeamUpdate and before the first ReadTransform of the maintained 770-frame sequence",
                "transitionWatch": "record SetRelativeTransform entry rcx and useRelativeTransform (dl) during the same sequence; zero calls proves the four initial samples remain constant",
                "alternative": "sample the four BeyondBoneCloth backing bytes at object+0x78 before every ReadTransform; this replaces the entry watch but is not smaller",
                "notRequired": ["UseAnimatorTransform", "callback route"],
            },
        },
        "minimumSessionTelemetry": {
            "crossFrame": "sample MagicaManager static_fields+0x09 immediately before each ClothUpdate in the maintained 770-frame sequence; one byte selects whether the second ReadTransform executes and also covers quality reapplication",
            "relativeInitial": "sample TeamData.useRelativeTransform at payload+0x9c for MC_Ribbon2, MC_Hair, MC_Ribbon, and MC_Coat after AlwaysTeamUpdate and before their first ReadTransform",
            "relativeTransitions": "record SetRelativeTransform entry rcx/dl during the sequence, or resample the four TeamData lanes every frame",
            "callbackSelector": "no telemetry: UseAnimatorTransform=false and TransformAccess WriteTransform are source-statically closed",
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
            "copyDoubleBufferActiveCadenceClosed": True,
            "readTransformCurrentArrayEquationsClosed": True, "endminfOneBoneProxyMappingClosed": True,
            "duplicateEntryMappingClosed": True,
            "animatorBufferBranchClosed": True,
            "useRelativeTransformInitialValueClosed": True,
            "useRelativeTransformTargetLiveValueClosed": False,
            "useCrossFrameJobTargetLiveValueClosed": False,
            "callbackWritebackSelectorClosed": True,
            "targetReady": False,
            "targetReadySubset": "the unpatched ordinary TransformAccess callback route, dormant CopyDoubleBuffer cadence, and animator-buffer exclusion are closed; one cross-frame byte plus four relative-transform lanes require target-session evidence",
            "unresolved": [
                "four live Endminf TeamData.useRelativeTransform values after possible pre-capture model placement",
                "live MagicaManager.UseCrossFrameJob after PhysicsClothQuality.Apply",
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
