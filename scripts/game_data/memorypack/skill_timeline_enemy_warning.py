"""Current-build SkillData EnemyWarningAction 0x00AA source reader.

The selected native action reader has the same finite member-kind sequence as
the already reviewed 0x00A2 action. The contract keeps its independent native
dispatch, reader callsites, and nested generic type joins. Nested EffectActionCfg
and TargetSettings keep the shared reader's exact stop behavior.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineEnemyWarning"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_enemy_warning_native.json"
_READERS = {
    "bool-byte": lambda reader: reader.take(1, "EnemyWarningAction.bool-byte"),
    "scalar32": lambda reader: reader.take(4, "EnemyWarningAction.scalar32"),
    "byte-payload": lambda reader: reader.byte_payload(),
    "target-profile": lambda reader: reader.target_profile(),
    "effect-configuration-profile": lambda reader: reader.effect_configuration_profile(),
}


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-enemy-warning-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    if (
        not isinstance(reads, list)
        or len(reads) != 18
        or [row.get("memberIndex") for row in reads] != list(range(18))
        or any(row.get("readKind") not in _READERS for row in reads)
        or contract.get("dispatcher", {}).get("unionTag") != 0x00AA
        or [row.get("typeName") for row in contract.get("nestedContexts", [])]
        != [
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Gameplay.EffectActionCfg",
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Gameplay.Core.TargetSettings",
        ]
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    buff = json.loads((CONTRACTS_DIR / "buff_a2_native.json").read_bytes())
    normalized = ["bool-byte" if kind == "byte" else kind for kind in buff.get("anonymousReadOrder", {}).get("member18", [])]
    if buff.get("schemaVersion") != 1 or normalized != [row["readKind"] for row in reads]:
        raise ValueError(f"{LABEL}.contract:shared-profile-drift")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected action route and each ordered source read."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(
        [[contract["memberCountInstruction"]["rva"], contract["memberCountInstruction"]["hex"]]],
        label=LABEL,
    )
    previous = -1
    for read in contract["orderedSourceReads"]:
        rva = read["sourceCallsiteRva"]
        if rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"].upper():
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    for dependency in contract["dependencies"]:
        reviewed = json.loads((CONTRACTS_DIR / dependency["path"]).read_bytes())
        if reviewed.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:dependency-schema={dependency['path']}")
        image.check_windows(reviewed["codeWindows"], label=f"{LABEL}.{dependency['path']}")
    for context in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec={context['instructionRva']:#x}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12),
            len(image.metadata.methods),
            image.registration["genericInstsCount"],
            source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={index}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            argument.hex().upper() != context["argumentRawHex"].upper()
            or argument[10] not in (0x11, 0x12)
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "methodIndices": methods,
        "sourceReadCount": len(contract["orderedSourceReads"]),
        "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_enemy_warning_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Advance one reached 0x00AA action under its explicit source order."""
    del depth
    contract = _contract()
    if tag != contract["dispatcher"]["unionTag"] or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(contract["orderedSourceReads"]))
    for read in contract["orderedSourceReads"]:
        _READERS[read["readKind"]](reader)
