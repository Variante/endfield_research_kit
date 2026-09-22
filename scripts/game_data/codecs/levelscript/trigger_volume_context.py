"""Resolution of typed trigger-volume selectors against same-LevelScript volumes.

Moved verbatim out of ``scripts/game_data/levelscript_binary.py``.
"""

from __future__ import annotations

from typing import Any

from scripts.game_data.codecs.levelscript import trigger_volumes as levelscript_trigger_volumes


def classify_local_trigger_volume_context(
    decoded: dict[str, Any],
    selector_slot_ids: list[int],
    *,
    trigger_volume_type: str = "Leader",
) -> dict[str, Any]:
    """Resolve typed event selectors to exact same-LevelScript volumes.

    The join is deliberately identifier-agnostic: callers supply selector
    slots decoded from a typed event payload, and this function validates the
    current MemoryPack trigger-volume schema before matching those slots.  The
    serialized volume has no dynamic-scene, mission, or quest foreign key, so
    a successful result proves local playback geometry only.
    """
    unique_slots = sorted({
        slot_id
        for slot_id in selector_slot_ids
        if isinstance(slot_id, int)
        and not isinstance(slot_id, bool)
        and slot_id > 0
    })
    details = decoded.get("triggerVolumesDetails") or {}
    volumes = details.get("volumes") or []
    expected_union_tags = {
        union_tag
        for union_tag, name in levelscript_trigger_volumes.UNION_TAG_NAMES.items()
        if name == trigger_volume_type
    }
    matches: list[dict[str, Any]] = []
    ambiguous_slots: list[int] = []
    for slot_id in unique_slots:
        candidates = [
            volume
            for volume in volumes
            if isinstance(volume, dict)
            and volume.get("slotId") == slot_id
            and volume.get("keySlotId") == slot_id
            and volume.get("triggerVolumeType") == trigger_volume_type
            and volume.get("unionTag") in expected_union_tags
            and volume.get("memberCount")
            == len(levelscript_trigger_volumes.SERIALIZED_FIELDS)
            and isinstance(volume.get("shapeList"), dict)
            and volume["shapeList"].get("status") == "present"
            and volume["shapeList"].get("parseStatus") == "decoded"
            and bool(volume["shapeList"].get("shapes"))
        ]
        if len(candidates) == 1:
            matches.append(candidates[0])
        elif len(candidates) > 1:
            ambiguous_slots.append(slot_id)
    matched_slots = sorted(int(volume["slotId"]) for volume in matches)
    missing_slots = sorted(set(unique_slots) - set(matched_slots))
    exact = (
        bool(unique_slots)
        and decoded.get("scriptIdVerified") is True
        and decoded.get("triggerVolumesStatus") == "present"
        and details.get("parseStatus") == "decoded"
        and not missing_slots
        and not ambiguous_slots
        and len(matches) == len(unique_slots)
    )
    return {
        "status": (
            "exact_local_levelscript_trigger_volume_without_foreign_identity"
            if exact
            else "unresolved_local_levelscript_trigger_volume"
        ),
        "selectorSlotIds": unique_slots,
        "matchedSlotIds": matched_slots,
        "missingSlotIds": missing_slots,
        "ambiguousSlotIds": ambiguous_slots,
        "triggerVolumesStatus": decoded.get("triggerVolumesStatus") or "",
        "triggerVolumesParseStatus": details.get("parseStatus") or "",
        "triggerVolumesOffsetHex": decoded.get("triggerVolumesOffsetHex") or "",
        "topLevelSerializedMemberCount": decoded.get("serializedMemberCount"),
        "scriptIdVerified": bool(decoded.get("scriptIdVerified")),
        "triggerVolumes": matches,
        "schema": {
            "baseType": "Beyond.Gameplay.LevelScriptTriggerVolumeData",
            "baseDeclaredFieldCount": len(levelscript_trigger_volumes.BASE_FIELDS),
            "baseDeclaredFields": levelscript_trigger_volumes.BASE_FIELDS,
            "leaderType": (
                "Beyond.Gameplay.LevelScriptTriggerVolumeDataForLeader"
                if trigger_volume_type == "Leader"
                else ""
            ),
            "leaderDeclaredFieldCount": 0 if trigger_volume_type == "Leader" else None,
            "serializedMemberCount": len(
                levelscript_trigger_volumes.SERIALIZED_FIELDS
            ),
            "serializedFields": levelscript_trigger_volumes.SERIALIZED_FIELDS,
            "mappingId": levelscript_trigger_volumes.SCHEMA_MAPPING_ID,
        },
        "dynamicSceneIdentityFieldPresent": False,
        "missionOrQuestIdentityFieldPresent": False,
        "foreignKeyBridgeFound": False,
        "missionGraphAction": "none",
    }
