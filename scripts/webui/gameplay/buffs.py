"""Gameplay projection of fully consumed, identifier-matched BuffData values."""
from __future__ import annotations

from typing import Any


def resolved(record: dict[str, Any]) -> bool:
    return (record.get("idStringVerified") is True
            and record.get("status") in {"exact", "parsed-through-exact-tail"}
            and bool(record.get("evidenceStatus"))
            and record.get("evidenceStatus") != "unresolved")


def _action(item: Any) -> dict[str, Any]:
    item = item or {}
    members = item.get("$value") or {}
    framing = item.get('$framing') or {}
    return {**framing, "tag": hex(item['$tag']), "typeName": item.get("$type"),
            'name': item.get('$type'), 'decodeStatus': 'derived',
            'semanticStatus': 'stored-action-fields', 'boundaryProof': 'derived-plan-consumption',
            "decoded": {"semanticStatus": "stored-action-fields", 'decodeStatus': 'derived',
                        'type': item.get('$type'), 'memberCount': framing.get('memberCount'),
                        'byteLength': framing.get('bytes'),
                        "prefix": {"isEnable": members.get("isEnable")}, "members": members}}


def project(value: dict[str, Any], enums: dict[str, dict[int, str]]) -> dict[str, Any]:
    def named(fields, names):
        result = dict(fields)
        for name in names:
            selected = result.get(name)
            if selected not in enums[name]:
                raise ValueError(f'BuffData unmapped {name}={selected!r}')
            result[name + 'Name'] = enums[name][selected]
        return result

    life = value.get("lifeType")
    stack = dict(value.get("stackingSettings") or {})
    for field in ("identifierType", "stackingType"):
        selected = stack.get(field)
        if selected not in enums[field]:
            raise ValueError(f"BuffData unmapped {field}={selected!r}")
        stack[field + "Name"] = enums[field][selected]
    if life not in enums["lifeType"]:
        raise ValueError(f"BuffData unmapped lifeType={life!r}")
    events = []
    for event in value.get("abilityEventAction") or []:
        event = event or {}
        sequences = []
        for sequence in event.get("actions") or []:
            sequence = sequence or {}
            sequences.append({**{key: sequence.get(key) for key in
                                ("onlyExecuteWhenSourceIsGuard", "onlyExecuteWhenSourceIsMainChar")},
                              'actionDataCount': len(sequence.get('actionData') or []),
                              "actionDataItems": [_action(item) for item in sequence.get("actionData") or []]})
        events.append({**event, 'abilityEventName': enums['abilityEvent'].get(event.get('abilityEvent')),
                       "actions": sequences})
    modifier = dict(value.get('attributeModifier') or {})
    modifier['attributeModifiers'] = [named(item, ('attributeType', 'formulaItem', 'modifyAttributeType'))
                                      for item in modifier.get('attributeModifiers') or []]
    tags = []
    for item in value.get("applyTags") or []:
        if isinstance(item, dict) and set(item) == {"raw"} and len(item["raw"]) == 8:
            tags.append(f"0x{int.from_bytes(bytes.fromhex(item['raw']), 'little'):08x}")
        elif isinstance(item, dict) and type(item.get("value")) is int:
            tags.append(f"0x{item['value'] & 0xffffffff:08x}")
        else:
            raise ValueError(f"BuffData unprojected applyTags item: {str(item)[:150]}")
    # These children are preserved as authored data, without inventing effect
    # semantics from a union type name or treating an action as executed.
    other = {key: value.get(key) for key in ("buffEventAction", "damageModifier", "globalModifier",
             "healModifier", "igniteEventAction", "poiseModifier", "shieldConfigs", "timelineActions")}
    return {
        "id": value["id"], "status": "exact", "idStringVerified": True,
        "evidenceStatus": "derived-plan-whole-record", "preIdModifierStatus": "whole-record-derived-plan",
        "lifeType": {"raw": life, "value": life, "name": enums["lifeType"][life]},
        "duration": value.get("duration"), "maxTriggerCnt": value.get("maxTriggerCnt"),
        "triggerInterval": value.get("triggerInterval"), "stacking": stack,
        "flags": {key: value.get(key) for key in ("ignoreCooldownWhenAdding", "ignoreTagImmune",
                  "onlyUseSelfTimeDilation", "useTimeDilationDt", "waitFirstTriggerInterval")},
        "addingCooldown": value.get("addingCooldown"), "applyTags": {"tagIds": tags},
        "attributeModifier": modifier, "abilityEventActions": events,
        "abilityEventActionCount": len(events), "blackboardCandidates": [],
        "blackboard": value.get("blackboard"), "otherStoredEffects": other,
        "unresolvedEffects": (any(bool(child) for child in other.values())
                              or any(event['abilityEventName'] is None for event in events)),
        "tags": [], "refs": [],
    }
