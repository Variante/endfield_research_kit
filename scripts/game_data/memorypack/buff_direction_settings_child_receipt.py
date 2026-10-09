"""Selected native direct DirectionSettings members inside Buff targets.

The parent TargetSettings adapter owns `advancedDirection` and its exact span.
This reader names the DirectionSettings direct members through the selected
derived plan and source MethodSpec, retaining nested source/target objects at
their existing evidence tier.

The selected source MethodSpec, reader window, generated setters and derived
plan name ``clampToXZ``, ``customSourceAndTarget``, ``directionType``,
``invertDirection``, ``source``, ``sourceMountPoint``, ``target`` and
``targetMountPoint`` in direct stored order. Each parent target is reparsed
and the direction reader must end at the independently fixed field extent.
This direct receipt retains nonnull nested ``TargetSettings`` at the structural
tier. ``buff_direction_target_children`` separately proves each reference
transfer and composes its original child span; a null marker alone does not
establish a nonnull body. No runtime direction selection is claimed.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack import buff_target_settings_child_receipt as target
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify
from scripts.game_data.memorypack.derived_values import ValueReader
from scripts.common import check_installed_native_inputs


SCHEMA = "endfield.buff-direction-settings-action-child-receipt.v1"
LABEL = "buffDirectionSettingsActionChild"
DIRECTION_TYPE = "Beyond.Gameplay.Core.DirectionSettings"
DIRECTION_WRAPPER = "Beyond.MemoryPack.Beyond_Gameplay_Core_DirectionSettingsForMemoryPack"
FIELD_NAME = "advancedDirection"


def _setter_name(row: list[Any] | tuple[Any, ...]) -> str:
    name = row[1]
    if not isinstance(name, str) or not name.startswith("set___") or not name.endswith("__"):
        raise ValueError(f"{LABEL}.native:setter-name")
    return name.removeprefix("set___").removesuffix("__")


def validate_current_native_contract(
    *, target_native: dict[str, Any] | None = None,
    gameassembly: Path | None = None, metadata: Path | None = None,
    parent_tags: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    """Check target ownership, Direction reader, MethodSpec and setter order."""
    if target_native is None:
        target_native = target.validate_current_native_contract(
            gameassembly=gameassembly, metadata=metadata, parent_tags=parent_tags,
        )
    if target_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:target-not-validated")
    registry = target_native["_registry"]
    target_definition = target_native["targetDefinition"]
    parent_members = [row for row in registry.plans[target_definition]
                      if row.name == FIELD_NAME]
    if (len(parent_members) != 1 or parent_members[0].kind != "object"
            or parent_members[0].ref not in registry.plans
            or registry.wrapped_names.get(parent_members[0].ref) != DIRECTION_TYPE):
        raise ValueError(f"{LABEL}.native:target-direction-field")
    definition = parent_members[0].ref
    plan = registry.plans[definition]
    nested_targets = [member for member in plan
                      if member.kind == "object" and member.ref == target_definition]
    if len(nested_targets) != 2:
        raise ValueError(f"{LABEL}.native:direction-target-refs")
    expected = target_native["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != "validated":
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    image = open_native_image(gate.gameassembly, gate.metadata)
    source, _catalog = modify._contracts()
    methods = [row for row in source["methods"] if row[1] == DIRECTION_WRAPPER]
    if len(methods) != 1:
        raise ValueError(f"{LABEL}.native:direction-reader-count={len(methods)}")
    image.validate_method_row(methods[0], label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == DIRECTION_WRAPPER]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:direction-wrapper-count={len(owners)}")
    names = [_setter_name(row) for row in image.setter_methods(
        owners[0], parameter="typeName", label=LABEL
    )]
    if names != [member.name for member in plan]:
        raise ValueError(f"{LABEL}.native:direction-setter-order")
    contexts = [row for row in source["nestedContexts"]
                if row.get("typeName") == DIRECTION_TYPE]
    if len(contexts) != 1:
        raise ValueError(f"{LABEL}.native:direction-context-count={len(contexts)}")
    context = contexts[0]
    instruction = image.pe.bytes_at_va(
        image.pe.image_base + context["instructionRva"], 7
    )
    if (instruction.hex().upper() != context["instructionHex"].upper()
            or instruction[:3] != b"\x48\x8b\x35"):
        raise ValueError(f"{LABEL}.native:direction-rip-load")
    cell = (image.pe.image_base + context["instructionRva"] + 7
            + struct.unpack_from("<i", instruction, 3)[0])
    if cell != context["cellVa"]:
        raise ValueError(f"{LABEL}.native:direction-usage-cell")
    usage = image.pe.bytes_at_va(cell, 8)
    if usage.hex().upper() != context["usageRawHex"].upper():
        raise ValueError(f"{LABEL}.native:direction-usage-value")
    spec_index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(gate.gameassembly), offset=cell,
    )
    if spec_index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:direction-method-spec-index")
    raw = image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + spec_index * 12, 12
    )
    if list(struct.unpack("<iii", raw)) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:direction-method-spec")
    arguments = image.instantiations.resolve(context["methodSpec"][2]).arguments
    if (len(arguments) != 1
            or arguments[0].raw_type_record_hex.upper() != context["argumentRawHex"].upper()
            or image.type_name(context["typeDefinition"]) != context["typeName"]):
        raise ValueError(f"{LABEL}.native:direction-type")
    return {
        "status": "validated", "nativeInputs": expected,
        "targetNative": target_native,
        "directionDefinition": definition,
        "directMemberNames": names,
        "nestedTargetMemberNames": [member.name for member in nested_targets],
        "_registry": registry,
    }


def decode_direction_settings_value(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Read one source-bound typed value; its caller proves field ownership."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    if (not isinstance(data, bytes) or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()):
        raise ValueError(f"{LABEL}:logical-sha256-mismatch source={source}")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}:invalid-value-range source={source} range=[{start},{end})")
    registry = native_validation["_registry"]
    definition = native_validation["directionDefinition"]
    plan = registry.plans[definition]
    if [member.name for member in plan] != native_validation["directMemberNames"]:
        raise ValueError(f"{LABEL}:direction-plan-drift")
    reader = ValueReader(data, source, end, registry=registry)
    reader.pos = start
    if reader.peek() == 0xFF:
        reader.take(1, "null-direction-settings")
        members = []
        status = "exact-null"
    else:
        reader.header(len(plan))
        members = []
        for member in plan:
            member_start = reader.pos
            value = reader._value_member(member, 1)
            if reader.pos <= member_start:
                raise ValueError(f"{LABEL}:direction-member-no-progress:{member.name}")
            members.append({
                "fieldName": member.name, "kind": member.kind,
                "start": member_start, "end": reader.pos,
                "nestedTargetStatus": (
                    "exact-null" if member.kind == "object" and value is None
                    else "structural-only" if member.kind == "object" else None
                ),
            })
        status = "named-direct-members-exact-span"
    if reader.pos != end:
        raise ValueError(f"{LABEL}:direction-end={reader.pos}; expected={end}")
    return {
    "start": start, "end": end,
    "status": status, "namedMembers": members,
    "wholeStoredSpanExact": True,
    "recursiveNamedSchemaExact": False,
}


def decode_direction_settings_action_child_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    tag: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse parent targets, then name each bounded direction child."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    parent = target.decode_target_settings_action_child_receipt(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, tag=tag,
        native_validation=native_validation["targetNative"],
    )
    if (parent.get("status") != "named-direct-target-members"
            or parent.get("wholeActionRecursiveSchemaExact") is not False
            or parent.get("wholeBuffDataExact") is not False):
        raise ValueError(f"{LABEL}:target-parent-drift")
    directions = []
    for target_child in parent["targetChildren"]:
        if target_child["status"] != "named-direct-members-exact-span":
            raise ValueError(f"{LABEL}:null-or-unsupported-parent-target")
        fields = [field for field in target_child["namedMembers"]
                  if field["fieldName"] == FIELD_NAME and field["kind"] == "object"]
        if len(fields) != 1:
            raise ValueError(f"{LABEL}:direction-field-missing-or-ambiguous")
        field = fields[0]
        directions.append({
            "targetParentField": target_child["parentField"],
            **decode_direction_settings_value(
                data, source=source, logical_sha256=logical_sha256,
                start=field["start"], end=field["end"],
                native_validation=native_validation,
            ),
        })
    return {
        "schema": SCHEMA, "status": "named-direct-direction-members",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "parentTag": tag, "parentActionRange": [start, end],
        "directionChildren": directions,
        "wholeActionRecursiveSchemaExact": False,
        "wholeBuffDataExact": False,
        "evidenceBoundary": (
            "The selected TargetSettings reader owns each advancedDirection "
            "extent, and the selected DirectionSettings reader and generated "
            "setters name its direct stored members. Nested source/target "
            "objects, runtime direction choice and the enclosing action/BuffData "
            "recursive schemas remain unresolved."
        ),
    }
