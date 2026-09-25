"""Inputs for the Gameplay character loadout calculator.

The page computes a character's final attributes from a selected level,
weapon, equipment set and potential. This stage publishes only the inputs
that computation reads, each from its game source:

* the reviewed attribute formula (``scripts.game_data.attribute_formula_native``),
  gated on the installed build, plus the ``BattleConst`` coefficients it names;
* per-attribute display names/formats (``AttributeShowConfigTable``), defaults
  and clamp bounds (``AttributeMetaTable``) and native ``AttributeType`` names;
* every raw ``CharacterTable`` attribute per level and break stage;
* every ``EquipTable.equipAttrModifiers`` line, including the main/sub lines
  whose ``attrType`` is 0;
* ``SkillData.cardAttributeModifier`` for weapon and equipment-set skills,
  decoded with the same whole-record plan as the skill damage catalog.

Nothing here evaluates a formula; a missing gate publishes its status and the
page shows the calculation as unavailable.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.source_paths import ExportLayout

BATTLE_CONST_KEYS = (
    "atkRateOfMain",
    "atkRateOfSub",
    "efficiencyOfSTR",
    "efficiencyOfAGI",
    "efficiencyOfWISD",
    "healerEfficiencyOfWILL",
    "recoverEfficiencyOfWILL",
)
# AttributeShowConfigTable lists one display row per modifier; the final-value
# row uses ModifierType None (9).
FINAL_VALUE_MODIFIER = 9


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def attribute_calculation_payload(
    tables: dict[str, Any],
    i18n_text: Any,
    native_semantics: dict[str, Any] | None,
    formula: dict[str, Any] | None,
) -> dict[str, Any]:
    formula = formula or {}
    status = formula.get("status") or "unavailable"
    battle = tables.get("BattleConst.json") or {}
    meta = tables.get("AttributeMetaTable.json") or {}
    show = tables.get("AttributeShowConfigTable.json") or {}
    native_names = (native_semantics or {}).get("attributeTypes") or {}
    attributes: dict[str, Any] = {}
    for key, row in meta.items():
        attr_type = _int((row or {}).get("attributeType", key))
        if attr_type is None:
            continue
        options = [item for item in ((show.get(str(attr_type)) or {}).get("list") or []) if isinstance(item, dict)]
        final = next((item for item in options if item.get("attributeModifier") == FINAL_VALUE_MODIFIER), options[0] if options else {})
        attributes[str(attr_type)] = {
            "name": i18n_text(final.get("name")) if final else "",
            "valueFormat": final.get("valueFormat") or "" if final else "",
            "showPercent": bool(final.get("showPercent")) if final else False,
            "sortIndex": final.get("index") if final else None,
            "default": row.get("defaultValue"),
            "min": row.get("minValue") if row.get("hasMinValue") else None,
            "max": row.get("maxValue") if row.get("hasMaxValue") else None,
            "nativeName": native_names.get(str(attr_type)),
        }
    return {
        "evidence": {
            "status": status,
            "detail": formula.get("detail") or "",
            "boundary": formula.get("evidenceBoundary") or {},
            "failures": formula.get("failures") or [],
        },
        "formula": formula.get("formula") if status == "validated" else None,
        "coefficients": {key: battle.get(key) for key in BATTLE_CONST_KEYS} if status == "validated" else {},
        "attributes": attributes,
    }


def character_raw_attribute_rows(
    char_row: dict[str, Any], attribute_values: Any, playable_max_level: Any, meta: dict[str, Any],
) -> list[dict[str, Any]]:
    """Raw CharacterTable attributes per (level, breakStage), playable levels only.

    A value equal to its AttributeMetaTable default is omitted; the page
    reads the default for any attribute a row does not list.
    """

    cap = _int(playable_max_level)
    rows = []
    for index, row in enumerate(char_row.get("attributes") or []):
        if not isinstance(row, dict):
            continue
        values = attribute_values(row)
        level = _int(values.get(0)) or index + 1
        if cap is not None and level > cap:
            continue
        rows.append({
            "level": level,
            "breakStage": row.get("breakStage"),
            "attrs": {
                str(key): value for key, value in values.items()
                if key != 0 and value != (meta.get(str(key)) or {}).get("defaultValue")
            },
        })
    return rows


def equipment_attribute_modifiers(equip_row: dict[str, Any]) -> list[dict[str, Any]]:
    """EquipTable equipAttrModifiers lines as the runtime reads them."""

    out = []
    for item in equip_row.get("equipAttrModifiers") or []:
        if not isinstance(item, dict):
            continue
        out.append({
            "attrIndex": item.get("attrIndex"),
            "attrType": item.get("attrType"),
            "modifierType": item.get("modifierType"),
            "modifyAttributeType": item.get("modifyAttributeType"),
            "values": list(item.get("attrValues") or []),
        })
    return sorted(out, key=lambda item: (_int(item.get("attrIndex")) or 0, _int(item.get("attrType")) or 0))


def skill_attribute_modifiers(export_root: Path, skill_ids: set[str], context: dict[str, Any] | None) -> dict[str, Any]:
    """Decode SkillData cardAttributeModifier for the named skills.

    Only whole-record decodes whose identifier matches are published; any
    other outcome records a status so the page can say the bonus is unknown.
    """

    context = context or {}
    if (context.get("evidence") or {}).get("status") != "validated":
        return {}
    from scripts.game_data.memorypack.buff_actions import Unsupported
    from scripts.game_data.memorypack.derived_values import decode_file, find_identifier

    source_root = ExportLayout(export_root).json_dir / "SkillData"
    out: dict[str, Any] = {}
    for skill_id in sorted(skill_ids):
        if not re.fullmatch(r"[A-Za-z0-9_]+", skill_id):
            continue
        path = source_root / f"{skill_id}.json"
        if not path.is_file():
            out[skill_id] = {"status": "missing", "modifiers": []}
            continue
        try:
            raw = path.read_bytes()
            value, reached = decode_file(raw, context["root"], context["registry"], source=path.name)
            if reached != len(raw) or find_identifier(value) != skill_id:
                raise ValueError(f"whole-record-or-identifier mismatch: {reached}/{len(raw)}")
            card = value.get("cardAttributeModifier") or {}
            modifiers = []
            for item in card.get("attributeModifiers") or []:
                param = item.get("param") or {}
                modifiers.append({
                    "attributeType": item.get("attributeType"),
                    "modifierType": item.get("formulaItem"),
                    "modifyAttributeType": item.get("modifyAttributeType"),
                    "blackboardKey": param.get("blackboardKey") if param.get("useBlackboardKey") else None,
                    "value": None if param.get("useBlackboardKey") else param.get("value"),
                })
            out[skill_id] = {"status": "exact", "modifiers": modifiers,
                             "isConvertedAttribute": bool(card.get("isConvertedAttribute"))}
        except (OSError, Unsupported, ValueError, KeyError, IndexError, TypeError) as exc:
            out[skill_id] = {"status": "unavailable", "detail": f"{type(exc).__name__}: {exc}", "modifiers": []}
    return out


def apply_loadout_data(
    weapons: list[dict[str, Any]],
    equipment: list[dict[str, Any]],
    characters: list[dict[str, Any]],
    tables: dict[str, Any],
    attribute_values: Any,
    export_root: Path,
    skill_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Attach loadout inputs to entries; return the skill modifier catalog."""

    char_table = tables.get("CharacterTable.json") or {}
    for character in characters:
        row = char_table.get(character.get("id")) or {}
        playable = (character.get("stats") or {}).get("playableMaxLevel")
        character["attributeRows"] = character_raw_attribute_rows(
            row, attribute_values, playable, tables.get("AttributeMetaTable.json") or {},
        )
    equip_table = tables.get("EquipTable.json") or {}
    skill_ids: set[str] = set()
    for item in equipment:
        item["attributeModifiers"] = equipment_attribute_modifiers(equip_table.get(item.get("id")) or {})
        for effect in (item.get("suit") or {}).get("effects") or []:
            if effect.get("skillId"):
                skill_ids.add(str(effect["skillId"]))
    for weapon in weapons:
        for skill in weapon.get("skills") or []:
            if skill.get("id"):
                skill_ids.add(str(skill["id"]))
    return skill_attribute_modifiers(export_root, skill_ids, skill_context)
