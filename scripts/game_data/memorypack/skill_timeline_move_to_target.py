"""Current selected SkillData MoveToTargetAction framing.

The selected seventeen-member reader's source calls and setter order fix
LayerMask, TargetSettings and AnimationCurve children among primitive flags
and raw float bits.  Stored movement parameters do not prove actual motion.
"""
from __future__ import annotations

import hashlib
import json
import struct
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.formatter_native import check_formatter_windows, is_role_projection
from scripts.game_data.memorypack.skill_timeline_dependencies import validate_dependencies
from scripts.game_data.memorypack.buff import _ability_action_tag, _ability_action_tag_bytes
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs


LABEL = "skillTimelineMoveToTarget"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_move_to_target_native.json"
TAG_NAME = "Core_MoveToTargetAction_Data"
SCHEMA = "endfield.skill-timeline-move-to-target-native-contract.v2"
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32",
    "bool-byte", "layer-mask-raw4", "bool-byte", "float32-bits",
    "target-profile", "bool-byte", "bool-byte", "bool-byte",
    "float32-bits", "curve-profile", "float32-bits",
    "bool-byte", "bool-byte",
)
_READERS = {
    "bool-byte": lambda reader: reader.take(1, "MoveToTargetAction.bool-byte"),
    "enum32": lambda reader: reader.take(4, "MoveToTargetAction.enum32"),
    "scalar32": lambda reader: reader.take(4, "MoveToTargetAction.scalar32"),
    "layer-mask-raw4": lambda reader: reader.take(4, "MoveToTargetAction.LayerMask-raw4"),
    "float32-bits": lambda reader: reader.take(4, "MoveToTargetAction.float32-bits"),
    "target-profile": lambda reader: reader.target_profile(),
    "curve-profile": lambda reader: reader.curve_profile(),
}


def _contract(*, gameassembly=None, metadata=None) -> dict[str, Any]:
    if (gameassembly is None) != (metadata is None):
        raise ValueError(f"{LABEL}.native:both-selected-paths-required")
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema=SCHEMA,
        label=LABEL,
        status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    setters = contract.get("setterMethods")
    contexts = contract.get("nestedContexts")
    if (
        contract.get("dispatcher", {}).get("unionTag") != _ability_action_tag(TAG_NAME, gameassembly=gameassembly, metadata=metadata)
        or contract.get("serializedMemberCount") != len(READ_KINDS)
        or not isinstance(reads, list)
        or [row.get("memberIndex") for row in reads] != list(range(len(READ_KINDS)))
        or not isinstance(setters, list)
        or len(setters) != 13
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 5, 8, 13]
        or [row.get("typeName") for row in contexts]
        != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "UnityEngine.LayerMask",
            "Beyond.Gameplay.Core.TargetSettings",
            "UnityEngine.AnimationCurve",
        ]
        or [row.get("path") for row in contract.get("dependencies", ())]
        != ["memorypack_layer_mask_source_native.json", "buff_ec_native.json", "buff_98_native.json"]
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x40\x80\xFE" + bytes([len(READ_KINDS)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    fields = ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex"]
    for setter in setters:
        if not setter[1].startswith("set___") or not setter[1].endswith("__"):
            raise ValueError(f"{LABEL}.contract:setter-name")
        fields.append(setter[1].removeprefix("set___").removesuffix("__"))
    if (
        [row.get("fieldName") for row in reads] != fields
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or [row[2] for row in setters]
        != [
            "System.Boolean", "UnityEngine.LayerMask", "System.Boolean",
            "System.Single", "Beyond.Gameplay.Core.TargetSettings",
            "System.Boolean", "System.Boolean", "System.Boolean",
            "System.Single", "UnityEngine.AnimationCurve", "System.Single",
            "System.Boolean", "System.Boolean",
        ]
    ):
        raise ValueError(f"{LABEL}.contract:read-shape")
    return contract


def validate_current_native_contract(*, gameassembly=None, metadata=None) -> dict[str, Any]:
    """Reprove the selected route, seventeen source calls and nested profiles."""
    if (gameassembly is None) != (metadata is None):
        raise ValueError(f"{LABEL}.native:both-selected-paths-required")
    sources = snapshot_complete_reader_inputs()
    contract = _contract(gameassembly=gameassembly, metadata=metadata)
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
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
    _publication_gate(image, expected)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    check_formatter_windows(image, contract, label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    reads = contract["orderedSourceReads"]
    previous = -1
    for read in reads:
        rva = read["sourceCallsiteRva"]
        if rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != read["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
        if target != read["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    # Uniform regeneration independently re-proves each exact return-to-setter
    # transfer, including inherited members, on this same selected image.
    actual = derive_on_image(image, expected, contract)
    if actual != contract:
        raise ValueError(f"{LABEL}.native:current-source-declaration-differs")
    for context in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index={context['memberIndex']}")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record={index}")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity={index}")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            argument.hex().upper() != context["argumentRawHex"]
            or argument[10] != context["typeKind"]
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:generic-type={index}")
    validate_dependencies(image, contract, label=LABEL)
    _publication_gate(image, expected)
    if sources != snapshot_complete_reader_inputs():
        raise ValueError(f"{LABEL}.native:reader-source-drift")

    return {
        "status": "validated", "nativeInputs": expected,
        "methodIndices": methods, "sourceReadCount": len(reads),
        "nestedContextCount": len(contract["nestedContexts"]),
    }


def decode_move_to_target_action(reader: Reader, depth: int, tag: int, width: int, *,
                                 gameassembly=None, metadata=None) -> None:
    """Consume one reached MoveToTargetAction with finite nested profiles."""
    del depth
    selected = {} if gameassembly is None and metadata is None else dict(gameassembly=gameassembly, metadata=metadata)
    contract = _contract(**selected)
    encoded = _ability_action_tag_bytes(TAG_NAME, **selected)
    if encoded is None or tag != contract["dispatcher"]["unionTag"] or width != len(encoded):
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_KINDS))
    for kind in READ_KINDS:
        _READERS[kind](reader)


def derive_on_image(image, inputs, reviewed):
    """Migrate the reviewed semantic shape, re-proving every selected address."""
    import copy
    from scripts.game_data import skill_timeline_routes_regenerate as routes
    from scripts.game_data.buff_frontiers_regenerate import _method_row, _read_switch
    candidate = copy.deepcopy(reviewed)
    if candidate.get("schema") == "endfield.skill-timeline-move-to-target-native-contract.v1":
        candidate["nestedContexts"] = candidate.pop("genericContexts")
        candidate.pop("setterCallsites")
    elif candidate.get("schema") != SCHEMA:
        raise ValueError(f"{LABEL}.regenerate:unsupported-reviewed-shape")
    if (candidate.get("serializedMemberCount") != len(READ_KINDS)
            or tuple(r["readKind"] for r in candidate["orderedSourceReads"]) != READ_KINDS):
        raise ValueError(f"{LABEL}.regenerate:reviewed-read-shape")
    candidate["schema"] = SCHEMA
    wrapper = candidate["dispatcher"]["wrapperName"]
    candidate["methods"].sort(key=lambda m: m[1] != wrapper)
    candidate["evidenceBoundary"]["exact"] = "Fresh selected AbilityActionData route, current wrapper/method/full families, all seventeen actual source reads/setter transfers and four generic arguments are re-proved on the selected native image."
    base = image.pe.image_base
    extents = dict(image.mapper.pdata_function_extents(image.pe))
    fragments = {}
    for method in candidate["methods"]:
        row = _method_row(image, method)
        fragments[base + row[3]] = [(base + a, b - a)
            for a, b, _ in (p["runtimeTriple"] for p in image.unwind_index.family(row[3])["ranges"])
            if a != row[3]]
    result = routes.regenerate(candidate, image, inputs, switch=_read_switch(image),
        extents=extents, fragments=fragments, wrappers=image.memorypack_wrappers)
    routes.check_family_primitives(image, {CONTRACT_PATH.name: result}, routes.reference_primitives())
    failed = {k: v for k, v in routes.dependency_status(image, result).items() if v != "validated"}
    if failed:
        raise ValueError(f"{LABEL}.regenerate:dependencies:{failed}")
    return result


def validate_on_image(image, inputs, contract):
    """Reprove the complete reviewed current route without opening an image."""
    _publication_gate(image, inputs)
    if contract.get("nativeInputs") != inputs or contract.get("schema") != SCHEMA:
        raise ValueError(f"{LABEL}.native:current-contract-inputs-or-schema")
    if derive_on_image(image, inputs, contract) != contract:
        raise ValueError(f"{LABEL}.native:current-source-declaration-differs")
    _publication_gate(image, inputs)
    return dict(status="validated", nativeInputs=inputs,
        sourceReadCount=len(READ_KINDS), nestedContextCount=4,
        unionTag=contract["dispatcher"]["unionTag"])
