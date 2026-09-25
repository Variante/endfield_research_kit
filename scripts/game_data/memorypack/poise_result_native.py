"""Audit selected Poise calculation, virtual submission and field edges.

The selected metadata closes the virtual submission's candidate set, while
runtime receiver identity and live iFix state remain unobserved. A validated
report is conditional native evidence, not an applied or displayed amount.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol as il2cpp
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "poise_result_native.json"
SCHEMA = "endfield.poise-result-native-contract.v2"
REPORT_SCHEMA = "endfield.poise-result-native-audit.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/poise_result_native.json"

METHOD_ROLES = {
    "processDamage", "getFinalHealValue", "applyPoiseModifier", "newPoiseWithPack",
    "newPoise", "getTarget", "modifierConstructor", "getFinalDelta", "applyModifier",
    "applyModifierForGod", "patchCheck",
    "doApplyModifier", "getIsPoiseDamage", "getIsPoiseImmune",
    "isIgnorePoiseImmune", "hasPoise", "useMainBodyPoise", "getMaxPoise",
    "getPoise", "setPoise", "modifyPoise",
}
WINDOW_ROLES = (
    "processDamage", "getFinalHealValue", "newPoiseWithPack", "newPoise",
    "getTarget", "modifierConstructor", "getFinalDelta", "applyModifier",
    "applyModifierForGod", "doApplyModifier",
    "modifyPoise", "setPoise", "getPoise",
)
CALL_OWNERS = (
    "getFinalHealValue", "processDamage", "processDamage", "newPoiseWithPack",
    "newPoise", "applyModifier", "processDamage", "processDamage",
    "applyModifierForGod", "doApplyModifier", "doApplyModifier",
    "doApplyModifier", "doApplyModifier", "modifyPoise", "modifyPoise",
    "modifyPoise", "setPoise",
)
WITNESS_ROLES = {
    "afterTiming", "readPostModifierValue", "signMaskLoad", "attackerScalarArray",
    "outputScalarValue", "defenderScalarArray", "takenScalarValue",
    "outputScalarMultiply", "takenScalarMultiply",
    "enableBreakDilation", "hidePoiseEffect", "ignorePoiseImmune",
    "negativeValue", "targetReceiverMove", "targetClassLoad", "virtualApplySlot",
    "virtualApplyCompanion", "virtualApplyReceiver", "virtualApplyCall",
    "targetFieldReturn", "godPatchId", "godPatchTest", "godPatchBranch",
    "godUnpatchedResult", "signDirection", "absoluteMagnitude",
    "constructorValue", "constructorDirection", "constructorTarget", "finalDeltaSign",
    "poiseTargetDispatch", "poiseControllerField", "virtualPoiseGetSlot",
    "toSingle", "addCurrent", "virtualPoiseSetSlot", "virtualPoiseReadbackSlot",
    "actualDelta", "storeRealDelta", "poiseFieldWrite", "poiseFieldRead",
}


def _rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"contract-rva={value!r}")
    return int(value, 16)


def _runtime_type(image: NativeImage, index: int) -> str:
    if not 0 <= index < int(image.registration["typesCount"]):
        raise ValueError(f"native-type-index={index}")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    if not pointer:
        raise ValueError(f"native-type-pointer={index}")
    return il2cpp.runtime_type_name(image.pe, image.metadata, pointer)


def _signature(image: NativeImage, method: Any) -> dict[str, Any]:
    return {
        "parameters": [[image.metadata.string(row.name_index), _runtime_type(image, row.type_index)]
                       for row in image.metadata.parameters_for(method)],
        "returnType": _runtime_type(image, method.return_type),
    }


def _call_target(image: NativeImage, site: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xe8:
        raise ValueError(f"native-call-opcode={site:#x}:{raw.hex()}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_virtual_apply_candidates(
    image: NativeImage, dispatch: dict[str, Any], methods: dict[str, Any],
    slot: int,
) -> list[list[Any]]:
    """Close the metadata descendants and their selected vtable slot.

    A virtual receiver typed AbilitySystem can be any metadata descendant.
    Each selected vtable word encodes a method definition index in its low
    bits; compare the full word as well as the decoded method to fail closed.
    """
    if (dispatch["vtableBaseOffset"] < 0
            or dispatch["entryBytes"] < 8
            or dispatch["entryBytes"] % 8):
        raise ValueError("contract-virtual-apply-layout")
    metadata = image.metadata
    base = metadata.types[metadata.methods[methods["applyModifier"][0]].declaring_type]
    byval = {row.byval_type_index: row for row in metadata.types}
    descendants = []
    for candidate in metadata.types:
        current = candidate
        visited = set()
        while current is not None and current.index not in visited:
            if current.index == base.index:
                descendants.append(candidate)
                break
            visited.add(current.index)
            current = byval.get(current.parent_index)
    expected = dispatch["candidates"]
    if [row.index for row in descendants] != [row[0] for row in expected]:
        raise ValueError("native-virtual-apply-descendants")
    section = metadata.sections["vtableMethods"]
    checked = []
    for candidate, row in zip(descendants, expected):
        type_index, name, word_text, method_role = row
        if (metadata.type_full_name(candidate) != name
                or candidate.vtable_count <= slot
                or method_role not in ("applyModifier", "applyModifierForGod")):
            raise ValueError(f"native-virtual-apply-candidate={type_index}")
        word = struct.unpack_from(
            "<I", metadata.buf, section.offset + 4 * (candidate.vtable_start + slot),
        )[0]
        method_index = methods[method_role][0]
        if (word != _rva(word_text)
                or word != (0x60000000 | (method_index << 1) | 1)):
            raise ValueError(f"native-virtual-apply-slot={type_index}:word={word:#x}")
        checked.append([name, method_role])
    return checked


def _validate(image: NativeImage, contract: dict[str, Any]) -> dict[str, Any]:
    methods = contract["methods"]
    if set(methods) != METHOD_ROLES:
        raise ValueError("contract-method-set")
    resolved: dict[str, int] = {}
    for role, row in methods.items():
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError(f"contract-method-row={role}")
        resolved[role] = _rva(row[3])
        image.validate_method_row([*row[:3], resolved[role]], label="poise-result")
    signatures = contract["signatures"]
    if set(signatures) != {
        "getFinalHealValue", "newPoiseWithPack", "newPoise", "getTarget",
        "modifierConstructor", "getFinalDelta", "applyModifier", "applyModifierForGod",
        "doApplyModifier", "getPoise",
        "setPoise", "modifyPoise",
    }:
        raise ValueError("contract-signature-set")
    for role, expected in signatures.items():
        actual = _signature(image, image.metadata.methods[methods[role][0]])
        if actual != expected:
            raise ValueError(f"native-signature={role}:actual={actual!r}")
    if set(contract["virtualSlots"]) != {
        "applyModifier", "applyModifierForGod", "getPoise", "setPoise",
    }:
        raise ValueError("contract-virtual-slot-set")
    for role, slot in contract["virtualSlots"].items():
        actual = image.metadata.methods[methods[role][0]].slot
        if actual != slot:
            raise ValueError(f"native-virtual-slot={role}:actual={actual}")
    apply_candidates = _validate_virtual_apply_candidates(
        image, contract["virtualApplyDispatch"], methods,
        contract["virtualSlots"]["applyModifier"],
    )

    fields = contract["fields"]
    if [(row[0], row[1]) for row in fields] != [
        ("Beyond.Gameplay.Core.AbilitySystem+Modifier", name) for name in (
            "<deltaType>k__BackingField", "<value>k__BackingField",
            "<targetType>k__BackingField", "<realDelta>k__BackingField",
            "m_target",
        )
    ] + [("Beyond.Gameplay.Core.AbilitySystem", name)
         for name in ("m_poise", "m_poiseController")]:
        raise ValueError("contract-field-set")
    offsets: dict[str, int] = {}
    for owner_name, field_name, expected_type, expected_offset, expected_token in fields:
        owners = [row for row in image.metadata.types
                  if image.metadata.type_full_name(row) == owner_name]
        if len(owners) != 1:
            raise ValueError(f"native-field-owner={owner_name}:{len(owners)}")
        owner = owners[0]
        matches = [row for row in image.metadata.fields_for(owner)
                   if image.metadata.string(row.name_index) == field_name]
        if len(matches) != 1:
            raise ValueError(f"native-field-count={owner_name}.{field_name}:{len(matches)}")
        field = matches[0]
        actual_offset = il2cpp.runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, owner.index,
        ).get(field_name)
        actual_type = _runtime_type(image, field.type_index)
        if (actual_offset != expected_offset or actual_type != expected_type
                or f"0x{field.token:08x}" != expected_token):
            raise ValueError(
                f"native-field={owner_name}.{field_name}:type={actual_type}:offset={actual_offset}"
            )
        offsets[field_name] = actual_offset
    enum_rows = contract["enums"]
    if len(enum_rows) != 7 or len({(row[0], row[1]) for row in enum_rows}) != 7:
        raise ValueError("contract-enum-set")
    defaults = il2cpp.field_defaults(image.metadata)
    enum_ids: dict[str, int] = {}
    for enum_type, member_name, expected_id, expected_token in enum_rows:
        members = il2cpp.native_enum_members(
            image.metadata, defaults, image.pe, image.registration, enum_type,
        )
        matches = [row for row in members if row["name"] == member_name]
        if len(matches) != 1 or matches[0]["id"] != expected_id or matches[0]["token"] != expected_token:
            raise ValueError(f"native-enum={enum_type}.{member_name}")
        enum_ids[member_name] = expected_id

    windows = contract["codeWindows"]
    if len(windows) != len(WINDOW_ROLES):
        raise ValueError("contract-code-window-count")
    parsed = []
    for role, window in zip(WINDOW_ROLES, windows):
        start, end = _rva(window["startRva"]), _rva(window["endRva"])
        if start != resolved[role] or end <= start:
            raise ValueError(f"contract-code-window={role}")
        parsed.append({**window, "startRva": start, "endRva": end})
    image.check_windows(parsed, label="poise-result")

    calls = contract["callTargets"]
    if len(calls) != len(CALL_OWNERS):
        raise ValueError("contract-call-count")
    for owner, (site_text, target_role) in zip(CALL_OWNERS, calls):
        site = _rva(site_text)
        window = parsed[WINDOW_ROLES.index(owner)]
        if not window["startRva"] <= site < window["endRva"]:
            raise ValueError(f"contract-call-owner={owner}:{site:#x}")
        actual = _call_target(image, site)
        if actual != resolved[target_role]:
            raise ValueError(f"native-call-target={site:#x}:actual={actual:#x}")

    witnesses = contract["instructionWindows"]
    if set(witnesses) != WITNESS_ROLES:
        raise ValueError("contract-instruction-window-set")
    image.check_instruction_windows(
        [[_rva(row[0]), row[1], row[2]] for row in witnesses.values()],
        label="poise-result",
    )
    raw = {key: bytes.fromhex(row[1]) for key, row in witnesses.items()}
    mask = contract["signBitMask"]
    mask_load, mask_literal = _rva(mask["loadRva"]), _rva(mask["literalRva"])
    if (mask_load != _rva(witnesses["signMaskLoad"][0])
            or raw["signMaskLoad"][:5] != b"\xf2\x44\x0f\x10\x3d"
            or mask_load + len(raw["signMaskLoad"])
            + struct.unpack_from("<i", raw["signMaskLoad"], 5)[0] != mask_literal
            or bytes.fromhex(mask["littleEndianHex"]) != b"\x00" * 7 + b"\x80"
            or image.pe.bytes_at_va(image.pe.image_base + mask_literal, 8)
            != bytes.fromhex(mask["littleEndianHex"])):
        raise ValueError("native-poise-sign-bit-mask")
    # Exact displacement joins to the reviewed fields, after the value-type
    # object header is removed for Modifier's unboxed storage.
    if (struct.unpack_from("<I", raw["poiseControllerField"], 3)[0]
            != offsets["m_poiseController"]
            or raw["targetFieldReturn"][-1] != offsets["m_target"] - 16
            or struct.unpack_from("<I", raw["poiseFieldWrite"], 4)[0]
            != offsets["m_poise"]
            or struct.unpack_from("<I", raw["poiseFieldRead"], 4)[0]
            != offsets["m_poise"]
            or struct.unpack_from("<I", raw["storeRealDelta"], 5)[0]
            != offsets["<realDelta>k__BackingField"] - 16
            or raw["constructorDirection"][-1] != offsets["<deltaType>k__BackingField"] - 16
            or raw["constructorValue"][-1] != offsets["<value>k__BackingField"] - 16
            or raw["constructorTarget"][-1] != offsets["<targetType>k__BackingField"] - 16
            or raw["poiseTargetDispatch"][-1] != offsets["<targetType>k__BackingField"] - 16
            or struct.unpack_from("<I", raw["outputScalarValue"], 4)[0]
            != 0x20 + enum_ids["PoiseDamageOutputScalar"] * 8
            or struct.unpack_from("<I", raw["takenScalarValue"], 4)[0]
            != 0x20 + enum_ids["PoiseDamageTakenScalar"] * 8
            or struct.unpack_from("<I", raw["virtualPoiseGetSlot"], 1)[0]
            != contract["virtualSlots"]["getPoise"]
            or struct.unpack_from("<I", raw["virtualPoiseSetSlot"], 1)[0]
            != contract["virtualSlots"]["setPoise"]
            or struct.unpack_from("<I", raw["virtualPoiseReadbackSlot"], 1)[0]
            != contract["virtualSlots"]["getPoise"]):
        raise ValueError("native-poise-field-displacement")
    dispatch = contract["virtualApplyDispatch"]
    slot_offset = dispatch["vtableBaseOffset"] + (
        dispatch["entryBytes"] * contract["virtualSlots"]["applyModifier"]
    )
    if (raw["targetReceiverMove"] != b"\x48\x8b\xd8"
            or raw["targetClassLoad"] != b"\x4c\x8b\x03"
            or struct.unpack_from("<I", raw["virtualApplySlot"], 3)[0] != slot_offset
            or struct.unpack_from("<I", raw["virtualApplyCompanion"], 3)[0]
            != slot_offset + 8
            or raw["virtualApplyReceiver"] != b"\x48\x8b\xcb"
            or raw["virtualApplyCall"] != b"\xff\xd0"
            or raw["godPatchId"][0] != 0xB9
            or _rva(witnesses["godPatchId"][0]) + len(raw["godPatchId"])
            != _rva(calls[8][0])
            or _rva(calls[8][0]) + 5 != _rva(witnesses["godPatchTest"][0])
            or _rva(witnesses["godPatchTest"][0]) + len(raw["godPatchTest"])
            != _rva(witnesses["godPatchBranch"][0])
            or _rva(witnesses["godPatchBranch"][0]) + len(raw["godPatchBranch"])
            != _rva(witnesses["godUnpatchedResult"][0])
            or raw["godPatchTest"] != b"\x84\xc0"
            or raw["godPatchBranch"][0] != 0x75
            or _rva(witnesses["godPatchBranch"][0]) + 2
            + struct.unpack_from("<b", raw["godPatchBranch"], 1)[0]
            <= _rva(witnesses["godUnpatchedResult"][0]) + len(raw["godUnpatchedResult"])
            or raw["godUnpatchedResult"][0] != 0xB8
            or struct.unpack_from("<I", raw["godUnpatchedResult"], 1)[0]
            != enum_ids["Failed"]):
        raise ValueError("native-poise-virtual-apply-dispatch")
    return {
        "methodsValidated": len(methods), "codeWindowsValidated": len(windows),
        "directCallsValidated": len(calls), "instructionWitnessesValidated": len(witnesses),
        "virtualSlotsValidated": contract["virtualSlots"],
        "virtualApplyCandidatesValidated": apply_candidates,
        "conditionalPath": (
            "stored Poise calculation -> after-calculation modifiers -> two attribute scalars "
            "-> signed Modifier.NewPoise -> target virtual slot 87. Selected metadata maps five "
            "AbilitySystem types to base ApplyModifier and AbilitySystemForGod to its override. "
            "The God override returns Failed unpatched. If runtime target and guards select "
            "base ApplyModifier, _DoApplyModifier and ModifyPoise convert Double to Single, "
            "call virtual Poise accessors, and record readback realDelta"
        ),
    }


def audit(*, gameassembly: Path, metadata: Path,
          contract_path: Path = CONTRACT) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, status="validated", label="poise-result",
    )
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["gameAssemblySha256"], expected["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA, "status": gate.status, "detail": gate.detail,
        "contractSha256": digest,
        "nativeInputs": {"gameAssemblySha256": gate.gameassembly_sha256,
                         "metadataSha256": gate.metadata_sha256},
        "evidenceBoundary": contract["evidenceBoundary"],
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return report
    try:
        report.update(_validate(NativeImage(gameassembly, metadata, label="poise-result"), contract))
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as error:
        report["status"] = "mismatched"
        report["detail"] = str(error)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata)
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, TypeError) as error:
        report = {"schema": REPORT_SCHEMA, "status": "failed", "detail": str(error)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "detail": report.get("detail", ""),
                      "output": str(output)}, sort_keys=True))
    return 0 if report["status"] == NATIVE_EVIDENCE_VALIDATED else 2


if __name__ == "__main__":
    raise SystemExit(main())
