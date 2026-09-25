"""Exact whole-record PlaySound action contexts and selected event enum labels."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members, runtime_type_name


PLAY_SOUND_TYPE = "Beyond.Gameplay.Core.PlaySoundAction+PlaySoundActionData"
FAMILIES = ("SkillData", "BuffData")
EVENT_ENUM_FIELDS = (
    ("buffEvent", "Beyond.Gameplay.Core.BuffActionMap", "Beyond.Gameplay.Core.Buff+Event"),
    ("abilityEvent", "Beyond.Gameplay.Core.AbilityActionMap", "Beyond.Gameplay.Core.AbilitySystem+Event"),
)


def selected_event_enum_names(
    gameassembly: Path, metadata: Path,
) -> tuple[dict[str, dict[int, str]], dict[str, Any]]:
    """Type-check action-map fields before assigning selected native enum labels."""
    image = NativeImage(gameassembly, metadata, label="play-sound-action-enums")
    type_table = int(image.registration["types"], 16)
    type_count = int(image.registration["typesCount"])
    defaults = field_defaults(image.metadata)
    names: dict[str, dict[int, str]] = {}
    audit: dict[str, Any] = {}
    for field_name, owner_name, expected_type in EVENT_ENUM_FIELDS:
        owners = [
            row for row in image.metadata.types
            if image.metadata.type_full_name(row) == owner_name
        ]
        if len(owners) != 1:
            raise ValueError(f"selected-enum-owner={owner_name}: count={len(owners)}")
        fields = [
            row for row in image.metadata.fields_for(owners[0])
            if image.metadata.string(row.name_index) == field_name
        ]
        if len(fields) != 1:
            raise ValueError(f"selected-enum-field={owner_name}.{field_name}: count={len(fields)}")
        field = fields[0]
        if not 0 <= field.type_index < type_count:
            raise ValueError(f"selected-enum-type-index={owner_name}.{field_name}: {field.type_index}")
        type_va = image.pe.u64_at_va(type_table + field.type_index * 8)
        if not type_va:
            raise ValueError(f"selected-enum-type-pointer={owner_name}.{field_name}: missing")
        actual_type = runtime_type_name(image.pe, image.metadata, type_va)
        if actual_type != expected_type:
            raise ValueError(
                f"selected-enum-field-type={owner_name}.{field_name}: "
                f"expected={expected_type}, actual={actual_type}"
            )
        members = native_enum_members(
            image.metadata, defaults, image.pe, image.registration, expected_type
        )
        name_by_id: dict[int, str] = {}
        for member in members:
            value = int(member["id"])
            if value in name_by_id:
                raise ValueError(f"duplicate-selected-enum-id={expected_type}:{value}")
            name_by_id[value] = str(member["name"])
        if not name_by_id:
            raise ValueError(f"empty-selected-enum={expected_type}")
        names[field_name] = name_by_id
        audit[field_name] = {
            "fieldOwner": owner_name,
            "fieldName": field_name,
            "fieldToken": f"0x{field.token:08x}",
            "fieldType": expected_type,
            "members": members,
        }
    return names, audit


def apply_event_enum_names(
    rows: list[dict[str, Any]],
    event_enum_names: dict[str, dict[int, str]],
) -> None:
    """Label only selected enum values whose field type was checked above."""
    for row in rows:
        for field_name, names in event_enum_names.items():
            value = row[field_name]
            if value is None:
                row[field_name + "Name"] = None
                continue
            if not isinstance(value, int) or value not in names:
                raise ValueError(
                    f"unmapped-selected-enum={row['sourcePath']}:{row['actionPath']}:"
                    f"{field_name}={value}"
                )
            row[field_name + "Name"] = names[value]


def walk_actions(
    value: Any,
    path: str = "$",
    ancestors: tuple[tuple[str, dict[str, Any]], ...] = (),
) -> Iterator[tuple[str, dict[str, Any], tuple[tuple[str, dict[str, Any]], ...]]]:
    """Yield typed PlaySound unions with their exact decoded ancestry."""
    if isinstance(value, dict):
        if value.get("$type") == PLAY_SOUND_TYPE:
            fields = value.get("$value")
            if not isinstance(fields, dict):
                raise ValueError(f"PlaySoundActionData is not an object at {path}")
            yield path, fields, ancestors
        parents = (*ancestors, (path, value))
        for key, child in value.items():
            if key == "$value" and value.get("$type") == PLAY_SOUND_TYPE:
                continue
            yield from walk_actions(child, f"{path}.{key}", parents)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_actions(child, f"{path}[{index}]", ancestors)


def action_row(
    family: str,
    source: str,
    source_sha256: str,
    path: str,
    fields: dict[str, Any],
    ancestors: tuple[tuple[str, dict[str, Any]], ...],
) -> dict[str, Any]:
    timeline = next(
        (node for _, node in reversed(ancestors)
         if "_startFrame" in node and "_endFrame" in node),
        None,
    )
    buff_event = next(
        (node.get("buffEvent") for _, node in reversed(ancestors)
         if "buffEvent" in node),
        None,
    )
    ability_event = next(
        (node.get("abilityEvent") for _, node in reversed(ancestors)
         if "abilityEvent" in node),
        None,
    )
    guards = next(
        (node for _, node in reversed(ancestors)
         if "onlyExecuteWhenSourceIsGuard" in node
         and "onlyExecuteWhenSourceIsMainChar" in node),
        None,
    )
    event = fields.get("_soundEvent")
    literal = event if isinstance(event, str) else ""
    return {
        "configKind": family,
        "configId": Path(source).stem,
        "sourcePath": source,
        "sourceSha256": source_sha256,
        "actionPath": path,
        "eventLiteral": literal,
        "eventLiteralStatus": (
            "empty" if not literal.strip()
            else "outerWhitespaceUnresolved" if literal != literal.strip()
            else "asSerialized"
        ),
        "startFrame": timeline.get("_startFrame") if timeline else None,
        "endFrame": timeline.get("_endFrame") if timeline else None,
        "buffEvent": buff_event,
        "abilityEvent": ability_event,
        "onlyExecuteWhenSourceIsGuard": (
            guards.get("onlyExecuteWhenSourceIsGuard") if guards else None
        ),
        "onlyExecuteWhenSourceIsMainChar": (
            guards.get("onlyExecuteWhenSourceIsMainChar") if guards else None
        ),
        "enclosingActionTypes": [
            node["$type"] for _, node in ancestors
            if isinstance(node.get("$type"), str)
        ],
        "serializedAction": fields,
        "evidenceBoundary": (
            "Exact decoded PlaySoundActionData at the recorded source path. "
            "Frame, Buff event and Ability event fields are enclosing authored context; "
            "enum labels identify serialized values, not runtime dispatch. Branch selection, "
            "target resolution, Wwise Event identity and playback are unresolved."
        ),
    }


