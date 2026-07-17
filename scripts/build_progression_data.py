"""Build authored progression and reward relationships for the static WebUI.

The output is a descriptive view of exported table configuration.  It does
not model a live account, current availability, random-drop probabilities, or
an optimal upgrade plan.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXPORT_ROOT, LANG_DIR, ROOT, rel_path, write_json


SCHEMA_VERSION = 1
TABLE_SOURCE_RELS = (
    ("StreamingAssets", Path("structured") / "StreamingAssets" / "Table"),
    ("Persistent", Path("structured") / "Persistent" / "Table"),
)
TABLE_NAMES = (
    "CharacterTable.json",
    "CharGrowthTable.json",
    "CharLevelUpTable.json",
    "CharBreakTable.json",
    "CharBreakStageTable.json",
    "CharBreakNodeTable.json",
    "CharacterPotentialTable.json",
    "PotentialTalentEffectTable.json",
    "WeaponBasicTable.json",
    "WeaponUpgradeTemplateTable.json",
    "WeaponUpgradeTemplateSumTable.json",
    "WeaponBreakThroughTemplateTable.json",
    "WeaponTalentTemplateTable.json",
    "EquipTable.json",
    "EquipEnhanceCostTable.json",
    "ItemTable.json",
    "RewardTable.json",
    "RewardDropTable.json",
    "WikiEnemyDropTable.json",
    "UseItemTable.json",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build authored progression/reward data for the static WebUI.",
        epilog=("Outputs data/lang/<LANG>/progression/index.json. The payload does not "
                "claim live availability, account state, probabilities, or optimal plans."),
    )
    parser.add_argument("--languages", nargs="+", default=["CN"], help="Language codes; default: CN.")
    parser.add_argument("--default-language", default="CN", help="Localization fallback; default: CN.")
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=LANG_DIR)
    return parser.parse_args(argv)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def table_roots(export_root: Path) -> list[tuple[str, Path]]:
    return [(label, export_root / path) for label, path in TABLE_SOURCE_RELS if (export_root / path).is_dir()]


def merge_payload(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        return {**base, **overlay}
    if isinstance(base, list) and isinstance(overlay, list):
        return [*base, *overlay]
    return overlay


def load_table(roots: list[tuple[str, Path]], name: str, default: Any = None) -> Any:
    payload: Any = None
    found = False
    for _label, root in roots:
        value = read_json(root / name, None)
        if value is None:
            continue
        payload = value if not found else merge_payload(payload, value)
        found = True
    if found:
        return payload
    return {} if isinstance(default, dict) else ([] if isinstance(default, list) else default)


def clean_id(value: Any) -> str:
    return "" if value in (None, "") else str(value).strip()


def sorted_rows(table: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    if not isinstance(table, dict):
        return []
    return ((str(key), value) for key, value in sorted(table.items(), key=lambda pair: str(pair[0])) if isinstance(value, dict))


def copy_fields(row: dict[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {field: row[field] for field in fields if field in row and row[field] not in (None, "", [], {})}


def localized_text(i18n: dict[str, Any], fallback: dict[str, Any], value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        key = str(int(value))
        return str(i18n.get(key) or fallback.get(key) or "").strip()
    if not isinstance(value, dict):
        return ""
    if value.get("text"):
        return str(value["text"]).strip()
    key = clean_id(value.get("id"))
    return str(i18n.get(key) or fallback.get(key) or "").strip() if key and key != "0" else ""


def bundles(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return result
    for entry in value:
        if not isinstance(entry, dict):
            continue
        item_id = clean_id(entry.get("id") or entry.get("itemId"))
        if item_id:
            result.append({"itemId": item_id, "count": entry.get("count", entry.get("itemCount", 0))})
    return result


def source(table: str, row: str, path: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {"table": table, "row": row}
    if path:
        result["path"] = path
    return result


class Builder:
    def __init__(self, language: str, default_language: str, roots: list[tuple[str, Path]], tables: dict[str, Any]):
        self.language = language
        self.default_language = default_language
        self.roots = roots
        self.tables = tables
        self.i18n = load_table(roots, f"I18nTextTable_{language}.json", {}) or {}
        self.fallback = load_table(roots, f"I18nTextTable_{default_language}.json", {}) or {}
        self.nodes: dict[str, dict[str, Any]] = {}
        self.relations: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
        self.root_ids: set[str] = set()
        self.items = tables.get("ItemTable.json") or {}

    def text(self, value: Any) -> str:
        return localized_text(self.i18n, self.fallback, value)

    def add_node(self, node_id: str, kind: str, name: str, *, raw: dict[str, Any] | None = None,
                 evidence: dict[str, Any] | None = None, root: bool = False) -> None:
        if not node_id:
            return
        candidate: dict[str, Any] = {"id": node_id, "kind": kind, "name": name or node_id.split(":", 1)[-1]}
        if raw:
            candidate["raw"] = raw
        if evidence:
            candidate["source"] = evidence
        existing = self.nodes.get(node_id)
        if existing is None:
            self.nodes[node_id] = candidate
        else:
            if existing["kind"] == "reference" and kind != "reference":
                self.nodes[node_id] = candidate
            elif evidence and evidence != existing.get("source"):
                sources = existing.setdefault("sources", [existing.pop("source")]) if existing.get("source") else existing.setdefault("sources", [])
                if evidence not in sources:
                    sources.append(evidence)
        if root:
            self.root_ids.add(node_id)

    def add_relation(self, start: str, end: str, kind: str, *, table: str, row: str, path: str,
                     raw: dict[str, Any] | None = None, confidence: str = "direct", note: str = "") -> None:
        evidence = source(table, row, path)
        key = (start, end, kind, confidence, table, f"{row}/{path}")
        value: dict[str, Any] = {
            "source": start, "target": end, "kind": kind, "confidence": confidence, "evidence": evidence,
        }
        if raw:
            value["raw"] = raw
        if note:
            value["note"] = note
        self.relations[key] = value

    def ensure_reference(self, node_id: str, kind: str | None = None) -> None:
        if node_id not in self.nodes:
            self.add_node(node_id, kind or "reference", node_id.split(":", 1)[-1])

    def ensure_item(self, item_id: str) -> str:
        node_id = f"item:{item_id}"
        if node_id in self.nodes:
            return node_id
        row = self.items.get(item_id) if isinstance(self.items, dict) else None
        if isinstance(row, dict):
            raw = copy_fields(row, ("rarity", "type", "showingType", "iconId", "iconCompositeId", "modelKey", "sortId1", "sortId2"))
            description = self.text(row.get("desc"))
            if description:
                raw["description"] = description
            raw["obtainWayIds"] = [clean_id(value) for value in row.get("obtainWayIds") or [] if clean_id(value)]
            raw["outcomeItemIds"] = [clean_id(value) for value in row.get("outcomeItemIds") or [] if clean_id(value)]
            self.add_node(node_id, "item", self.text(row.get("name")) or item_id, raw=raw,
                          evidence=source("ItemTable.json", item_id), root=True)
        else:
            self.add_node(node_id, "item_reference", item_id)
        return node_id

    def add_costs(self, owner_id: str, costs: list[dict[str, Any]], table: str, row: str, path: str) -> None:
        for index, cost in enumerate(costs):
            item_id = clean_id(cost.get("itemId"))
            if not item_id:
                continue
            target = self.ensure_item(item_id)
            self.add_relation(owner_id, target, "costs_item", table=table, row=row,
                              path=f"{path}[{index}]", raw={"count": cost.get("count", 0)})

    def build_items(self) -> None:
        for item_id, _row in sorted_rows(self.items):
            self.ensure_item(item_id)
        for item_id, row in sorted_rows(self.items):
            owner = self.ensure_item(item_id)
            for index, obtain_id in enumerate(row.get("obtainWayIds") or []):
                obtain_key = clean_id(obtain_id)
                if not obtain_key:
                    continue
                target = f"obtain_way:{obtain_key}"
                self.add_node(target, "obtain_way_reference", obtain_key)
                self.add_relation(owner, target, "lists_obtain_way", table="ItemTable.json", row=item_id,
                                  path=f"obtainWayIds[{index}]",
                                  note="Authored UI obtain-way identifier; availability and route semantics are not inferred.")
            for index, outcome_id in enumerate(row.get("outcomeItemIds") or []):
                outcome_key = clean_id(outcome_id)
                if outcome_key:
                    self.add_relation(owner, self.ensure_item(outcome_key), "yields_item", table="ItemTable.json", row=item_id,
                                      path=f"outcomeItemIds[{index}]")

    def build_character_progression(self) -> None:
        characters = self.tables.get("CharacterTable.json") or {}
        growth = self.tables.get("CharGrowthTable.json") or {}
        for key, row in sorted_rows(characters):
            char_id = clean_id(row.get("charId") or key)
            raw = copy_fields(row, ("rarity", "profession", "weaponType", "charTypeId", "defaultWeaponId", "mainAttrType", "subAttrType"))
            self.add_node(f"character:{char_id}", "character", self.text(row.get("name")) or clean_id(row.get("engName")) or char_id,
                          raw=raw, evidence=source("CharacterTable.json", key), root=True)

        curve_id = "character_level_curve:default"
        self.add_node(curve_id, "character_level_curve", "Character level costs",
                      evidence=source("CharLevelUpTable.json", "*"), root=True)
        for key, row in sorted_rows(self.tables.get("CharLevelUpTable.json")):
            checkpoint = f"character_level:{key}"
            self.add_node(checkpoint, "character_level_checkpoint", f"Character level {key}", raw=copy_fields(row, ("exp", "gold")),
                          evidence=source("CharLevelUpTable.json", key))
            self.add_relation(curve_id, checkpoint, "has_level_checkpoint", table="CharLevelUpTable.json", row=key, path="")

        for char_key, row in sorted_rows(growth):
            char_id = clean_id(row.get("charId") or char_key)
            owner = f"character:{char_id}"
            self.ensure_reference(owner, "character")
            for node_key, entry in sorted((row.get("charBreakCostMap") or {}).items(), key=lambda pair: str(pair[0])):
                if not isinstance(entry, dict):
                    continue
                node_id = f"character_break:{char_id}:{node_key}"
                raw = copy_fields(entry, ("breakStage", "equipTierLimit", "nodeType"))
                self.add_node(node_id, "character_break", self.text(entry.get("name")) or str(node_key), raw=raw,
                              evidence=source("CharGrowthTable.json", char_key, f"charBreakCostMap.{node_key}"))
                self.add_relation(owner, node_id, "has_breakthrough", table="CharGrowthTable.json", row=char_key,
                                  path=f"charBreakCostMap.{node_key}")
                self.add_costs(node_id, bundles(entry.get("requiredItem")), "CharGrowthTable.json", char_key,
                               f"charBreakCostMap.{node_key}.requiredItem")
            for index, entry in enumerate(row.get("skillLevelUp") or []):
                if not isinstance(entry, dict):
                    continue
                group = clean_id(entry.get("skillGroupId")) or "unknown"
                level = clean_id(entry.get("level")) or str(index)
                node_id = f"character_skill_level:{char_id}:{group}:{level}"
                self.add_node(node_id, "character_skill_level", f"{group} level {level}",
                              raw=copy_fields(entry, ("level", "goldCost", "skillGroupId")),
                              evidence=source("CharGrowthTable.json", char_key, f"skillLevelUp[{index}]"))
                self.add_relation(owner, node_id, "has_skill_level_checkpoint", table="CharGrowthTable.json", row=char_key,
                                  path=f"skillLevelUp[{index}]")
                costs = bundles(entry.get("itemBundle"))
                if entry.get("goldCost") not in (None, 0):
                    costs.append({"itemId": "item_gold", "count": entry["goldCost"]})
                self.add_costs(node_id, costs, "CharGrowthTable.json", char_key, f"skillLevelUp[{index}].costs")
            for node_key, entry in sorted((row.get("talentNodeMap") or {}).items(), key=lambda pair: str(pair[0])):
                if not isinstance(entry, dict):
                    continue
                node_id = f"character_talent:{char_id}:{node_key}"
                raw = copy_fields(entry, ("nodeId", "nodeType"))
                for field in ("attributeNodeInfo", "factorySkillNodeInfo", "passiveSkillNodeInfo"):
                    if isinstance(entry.get(field), dict):
                        raw[field] = entry[field]
                self.add_node(node_id, "character_talent", str(node_key), raw=raw,
                              evidence=source("CharGrowthTable.json", char_key, f"talentNodeMap.{node_key}"))
                self.add_relation(owner, node_id, "has_talent_node", table="CharGrowthTable.json", row=char_key,
                                  path=f"talentNodeMap.{node_key}")
                self.add_costs(node_id, bundles(entry.get("requiredItem")), "CharGrowthTable.json", char_key,
                               f"talentNodeMap.{node_key}.requiredItem")

        effects = self.tables.get("PotentialTalentEffectTable.json") or {}
        for char_key, row in sorted_rows(self.tables.get("CharacterPotentialTable.json")):
            owner = f"character:{char_key}"
            self.ensure_reference(owner, "character")
            for index, entry in enumerate(row.get("potentialUnlockBundle") or []):
                if not isinstance(entry, dict):
                    continue
                level = clean_id(entry.get("level")) or str(index + 1)
                node_id = f"character_potential:{char_key}:{level}"
                raw = copy_fields(entry, ("level", "potentialEffectId", "unlockCardTopicItem", "unlockCharPictureItemList"))
                self.add_node(node_id, "character_potential", self.text(entry.get("name")) or f"Potential {level}", raw=raw,
                              evidence=source("CharacterPotentialTable.json", char_key, f"potentialUnlockBundle[{index}]"))
                self.add_relation(owner, node_id, "has_potential", table="CharacterPotentialTable.json", row=char_key,
                                  path=f"potentialUnlockBundle[{index}]")
                item_ids = entry.get("itemIds") or []
                counts = entry.get("itemCnts") or []
                costs = [{"itemId": clean_id(item), "count": counts[pos] if pos < len(counts) else None}
                         for pos, item in enumerate(item_ids) if clean_id(item)]
                self.add_costs(node_id, costs, "CharacterPotentialTable.json", char_key,
                               f"potentialUnlockBundle[{index}].itemIds")
                effect_id = clean_id(entry.get("potentialEffectId"))
                if effect_id:
                    effect_row = effects.get(effect_id) if isinstance(effects, dict) else None
                    target = f"potential_effect:{effect_id}"
                    self.add_node(target, "potential_effect", self.text(effect_row.get("desc")) if isinstance(effect_row, dict) else effect_id,
                                  raw=copy_fields(effect_row, ("dataList",)) if isinstance(effect_row, dict) else None,
                                  evidence=source("PotentialTalentEffectTable.json", effect_id) if isinstance(effect_row, dict) else None)
                    self.add_relation(node_id, target, "applies_potential_effect", table="CharacterPotentialTable.json", row=char_key,
                                      path=f"potentialUnlockBundle[{index}].potentialEffectId")

    def build_weapon_progression(self) -> None:
        for key, row in sorted_rows(self.tables.get("WeaponBasicTable.json")):
            weapon_id = clean_id(row.get("weaponId") or key)
            owner = f"weapon:{weapon_id}"
            raw = copy_fields(row, ("rarity", "weaponType", "maxLv", "levelTemplateId", "breakthroughTemplateId",
                                    "talentTemplateId", "potentialUpItemList", "weaponPotentialSkill", "weaponSkillList", "modelPath"))
            self.add_node(owner, "weapon", self.text(row.get("engName")) or weapon_id, raw=raw,
                          evidence=source("WeaponBasicTable.json", key), root=True)
            for field, prefix, relation_kind, table in (
                ("levelTemplateId", "weapon_upgrade_template", "uses_upgrade_template", "WeaponUpgradeTemplateTable.json"),
                ("breakthroughTemplateId", "weapon_breakthrough_template", "uses_breakthrough_template", "WeaponBreakThroughTemplateTable.json"),
                ("talentTemplateId", "weapon_talent_template", "uses_talent_template", "WeaponTalentTemplateTable.json"),
            ):
                template_id = clean_id(row.get(field))
                if template_id:
                    target = f"{prefix}:{template_id}"
                    self.add_node(target, prefix, template_id, evidence=source(table, template_id))
                    self.add_relation(owner, target, relation_kind, table="WeaponBasicTable.json", row=key, path=field)
            for index, item_id in enumerate(row.get("potentialUpItemList") or []):
                item_key = clean_id(item_id)
                if item_key:
                    self.add_relation(owner, self.ensure_item(item_key), "uses_potential_item", table="WeaponBasicTable.json", row=key,
                                      path=f"potentialUpItemList[{index}]")

        sums = self.tables.get("WeaponUpgradeTemplateSumTable.json") or {}
        for template_id, row in sorted_rows(self.tables.get("WeaponUpgradeTemplateTable.json")):
            owner = f"weapon_upgrade_template:{template_id}"
            self.add_node(owner, "weapon_upgrade_template", template_id, evidence=source("WeaponUpgradeTemplateTable.json", template_id))
            sum_rows = (sums.get(template_id) or {}).get("list") if isinstance(sums.get(template_id), dict) else []
            sums_by_level = {clean_id(value.get("weaponLv")): value for value in sum_rows or [] if isinstance(value, dict)}
            for index, entry in enumerate(row.get("list") or []):
                if not isinstance(entry, dict):
                    continue
                level = clean_id(entry.get("weaponLv")) or str(index + 1)
                node_id = f"weapon_level:{template_id}:{level}"
                raw = dict(entry)
                if isinstance(sums_by_level.get(level), dict):
                    raw.update({key: value for key, value in sums_by_level[level].items() if key != "weaponLv"})
                self.add_node(node_id, "weapon_level_checkpoint", f"Weapon level {level}", raw=raw,
                              evidence=source("WeaponUpgradeTemplateTable.json", template_id, f"list[{index}]"))
                self.add_relation(owner, node_id, "has_level_checkpoint", table="WeaponUpgradeTemplateTable.json", row=template_id,
                                  path=f"list[{index}]")

        for template_id, row in sorted_rows(self.tables.get("WeaponBreakThroughTemplateTable.json")):
            owner = f"weapon_breakthrough_template:{template_id}"
            self.add_node(owner, "weapon_breakthrough_template", template_id,
                          evidence=source("WeaponBreakThroughTemplateTable.json", template_id))
            for index, entry in enumerate(row.get("list") or []):
                if not isinstance(entry, dict):
                    continue
                level = clean_id(entry.get("breakthroughShowLv")) or str(index)
                node_id = f"weapon_breakthrough:{template_id}:{level}"
                self.add_node(node_id, "weapon_breakthrough", f"Breakthrough {level}",
                              raw=copy_fields(entry, ("breakthroughLv", "breakthroughShowLv", "breakthroughGold", "skillLevelBounds")),
                              evidence=source("WeaponBreakThroughTemplateTable.json", template_id, f"list[{index}]"))
                self.add_relation(owner, node_id, "has_breakthrough", table="WeaponBreakThroughTemplateTable.json", row=template_id,
                                  path=f"list[{index}]")
                costs = bundles(entry.get("breakItemList"))
                if entry.get("breakthroughGold") not in (None, 0):
                    costs.append({"itemId": "item_gold", "count": entry["breakthroughGold"]})
                self.add_costs(node_id, costs, "WeaponBreakThroughTemplateTable.json", template_id, f"list[{index}].costs")

        for template_id, row in sorted_rows(self.tables.get("WeaponTalentTemplateTable.json")):
            owner = f"weapon_talent_template:{template_id}"
            self.add_node(owner, "weapon_talent_template", template_id, evidence=source("WeaponTalentTemplateTable.json", template_id))
            for index, entry in enumerate(row.get("list") or []):
                if not isinstance(entry, dict):
                    continue
                level = clean_id(entry.get("talentLv")) or str(index + 1)
                node_id = f"weapon_talent:{template_id}:{level}"
                self.add_node(node_id, "weapon_talent", f"Weapon potential {level}", raw=dict(entry),
                              evidence=source("WeaponTalentTemplateTable.json", template_id, f"list[{index}]"))
                self.add_relation(owner, node_id, "has_talent_checkpoint", table="WeaponTalentTemplateTable.json", row=template_id,
                                  path=f"list[{index}]")

    def build_equipment_progression(self) -> None:
        enhance = self.tables.get("EquipEnhanceCostTable.json") or {}
        for domain_id, row in sorted_rows(enhance):
            config_id = f"equipment_enhance_cost:{domain_id}"
            self.add_node(config_id, "equipment_enhance_cost", f"{domain_id} enhancement cost", raw=copy_fields(row, (
                "domainId", "consumeItemId", "consumeItemCnt", "returnbackItemId", "returnbackItemCnt",
            )), evidence=source("EquipEnhanceCostTable.json", domain_id))
            consume = clean_id(row.get("consumeItemId"))
            if consume:
                self.add_relation(config_id, self.ensure_item(consume), "costs_item", table="EquipEnhanceCostTable.json", row=domain_id,
                                  path="consumeItemId", raw={"count": row.get("consumeItemCnt", 0)})
            returned = clean_id(row.get("returnbackItemId"))
            if returned:
                self.add_relation(config_id, self.ensure_item(returned), "returns_item", table="EquipEnhanceCostTable.json", row=domain_id,
                                  path="returnbackItemId", raw={"count": row.get("returnbackItemCnt", 0)})

        for key, row in sorted_rows(self.tables.get("EquipTable.json")):
            item_id = clean_id(row.get("itemId") or key)
            owner = f"equipment:{item_id}"
            item_row = self.items.get(item_id) if isinstance(self.items, dict) else None
            name = self.text(item_row.get("name")) if isinstance(item_row, dict) else item_id
            raw = copy_fields(row, ("domainId", "minWearLv", "partType", "suitID", "displayBaseAttrModifier", "displayAttrModifiers"))
            self.add_node(owner, "equipment", name or item_id, raw=raw, evidence=source("EquipTable.json", key), root=True)
            self.add_relation(owner, self.ensure_item(item_id), "represented_by_item", table="EquipTable.json", row=key, path="itemId")
            domain_id = clean_id(row.get("domainId"))
            config_id = f"equipment_enhance_cost:{domain_id}"
            if domain_id and config_id in self.nodes:
                self.add_relation(owner, config_id, "uses_domain_enhance_cost", table="EquipTable.json", row=key, path="domainId")
            modifiers = [value for value in row.get("equipAttrModifiers") or [] if isinstance(value, dict)]
            stage_count = max((len(value.get("attrValues") or []) for value in modifiers), default=0)
            for stage in range(stage_count):
                checkpoint = f"equipment_stage:{item_id}:{stage}"
                values = [{**copy_fields(value, ("attrIndex", "attrType", "modifierType", "modifyAttributeType")),
                           "attrValue": value.get("attrValues", [])[stage]}
                          for value in modifiers if stage < len(value.get("attrValues") or [])]
                self.add_node(checkpoint, "equipment_attribute_stage", f"Attribute stage {stage}",
                              raw={"stageIndex": stage, "modifiers": values},
                              evidence=source("EquipTable.json", key, f"equipAttrModifiers[*].attrValues[{stage}]"))
                self.add_relation(owner, checkpoint, "has_authored_attribute_stage", table="EquipTable.json", row=key,
                                  path=f"equipAttrModifiers[*].attrValues[{stage}]",
                                  note="The table exposes an authored array index; runtime enhancement-roll behavior is not inferred.")

    def build_rewards_and_drops(self) -> None:
        for key, row in sorted_rows(self.tables.get("RewardTable.json")):
            reward_id = clean_id(row.get("rewardId") or key)
            owner = f"reward:{reward_id}"
            fixed = bundles(row.get("itemBundles"))
            probable = bundles(row.get("probItemBundles"))
            self.add_node(owner, "reward_bundle", reward_id,
                          raw={"fixedEntryCount": len(fixed), "probableEntryCount": len(probable)},
                          evidence=source("RewardTable.json", key), root=True)
            for relation_kind, entries, path in (("contains_item", fixed, "itemBundles"),
                                                 ("may_contain_item", probable, "probItemBundles")):
                for index, entry in enumerate(entries):
                    self.add_relation(owner, self.ensure_item(entry["itemId"]), relation_kind, table="RewardTable.json", row=key,
                                      path=f"{path}[{index}]", raw={"count": entry.get("count", 0)},
                                      note="Probability is not provided by this table." if relation_kind == "may_contain_item" else "")

        for key, row in sorted_rows(self.tables.get("RewardDropTable.json")):
            drop_id = clean_id(row.get("rewardId") or key)
            owner = f"drop_pool:{drop_id}"
            self.add_node(owner, "drop_pool", drop_id, evidence=source("RewardDropTable.json", key), root=True)
            for index, item_id in enumerate(row.get("itemIds") or []):
                item_key = clean_id(item_id)
                if item_key:
                    self.add_relation(owner, self.ensure_item(item_key), "lists_drop_item", table="RewardDropTable.json", row=key,
                                      path=f"itemIds[{index}]", note="Membership only; probability and live eligibility are not present.")

        for enemy_id, row in sorted_rows(self.tables.get("WikiEnemyDropTable.json")):
            owner = f"enemy:{enemy_id}"
            self.add_node(owner, "enemy_reference", enemy_id, evidence=source("WikiEnemyDropTable.json", enemy_id), root=True)
            for index, item_id in enumerate(row.get("dropItemIds") or []):
                item_key = clean_id(item_id)
                if item_key:
                    self.add_relation(owner, self.ensure_item(item_key), "wiki_lists_drop_item", table="WikiEnemyDropTable.json", row=enemy_id,
                                      path=f"dropItemIds[{index}]", note="Wiki-authored drop membership; probability is not claimed.")

    def build_use_paths(self) -> None:
        for item_id, row in sorted_rows(self.tables.get("UseItemTable.json")):
            owner = self.ensure_item(clean_id(row.get("itemId") or item_id))
            profile = f"item_use:{item_id}"
            raw = copy_fields(row, ("duration", "effectType", "isPersistentBuff", "isValuableDepot", "stackingKey", "targetNumType", "uiType"))
            description = self.text(row.get("itemUseDesc"))
            if description:
                raw["description"] = description
            self.add_node(profile, "item_use", description or item_id, raw=raw, evidence=source("UseItemTable.json", item_id))
            self.add_relation(owner, profile, "has_use_configuration", table="UseItemTable.json", row=item_id, path="")
            for index, action in enumerate(row.get("useActions") or []):
                if not isinstance(action, dict):
                    continue
                action_id = f"item_use_action:{item_id}:{index}"
                self.add_node(action_id, "item_use_action", f"Use action {index + 1}", raw=dict(action),
                              evidence=source("UseItemTable.json", item_id, f"useActions[{index}]"))
                self.add_relation(profile, action_id, "has_use_action", table="UseItemTable.json", row=item_id,
                                  path=f"useActions[{index}]")
                buff = action.get("buffBBData") if isinstance(action.get("buffBBData"), dict) else {}
                buff_id = clean_id(buff.get("buffId"))
                if buff_id:
                    target = f"buff:{buff_id}"
                    self.add_node(target, "buff_reference", buff_id)
                    self.add_relation(action_id, target, "use_action_applies_buff", table="UseItemTable.json", row=item_id,
                                      path=f"useActions[{index}].buffBBData", raw={"useType": action.get("useType"), "blackboard": buff.get("blackboard") or []})
                skill = action.get("skillBBData") if isinstance(action.get("skillBBData"), dict) else {}
                skill_id = clean_id(skill.get("skillId"))
                if skill_id:
                    target = f"skill:{skill_id}"
                    self.add_node(target, "skill_reference", skill_id)
                    self.add_relation(action_id, target, "use_action_invokes_skill", table="UseItemTable.json", row=item_id,
                                      path=f"useActions[{index}].skillBBData", raw={"useType": action.get("useType"), "skillPath": skill.get("skillPath"), "blackboard": skill.get("blackboard") or []})

    def payload(self) -> dict[str, Any]:
        self.build_items()
        self.build_character_progression()
        self.build_weapon_progression()
        self.build_equipment_progression()
        self.build_rewards_and_drops()
        self.build_use_paths()
        nodes = sorted(self.nodes.values(), key=lambda row: (str(row["kind"]), str(row["name"]).casefold(), str(row["id"])))
        relations = sorted(self.relations.values(), key=lambda row: (
            str(row["source"]), str(row["kind"]), str(row["target"]),
            str(row["evidence"].get("table", "")), str(row["evidence"].get("row", "")), str(row["evidence"].get("path", "")),
        ))
        node_ids = {str(row["id"]) for row in nodes}
        dangling = [row for row in relations if row["source"] not in node_ids or row["target"] not in node_ids]
        if len(node_ids) != len(nodes):
            raise ValueError("progression node ids are not unique")
        if dangling:
            raise ValueError(f"progression relations have {len(dangling)} dangling endpoints")
        kinds = Counter(str(row["kind"]) for row in nodes)
        relation_kinds = Counter(str(row["kind"]) for row in relations)
        confidence = Counter(str(row["confidence"]) for row in relations)
        return {
            "schemaVersion": SCHEMA_VERSION,
            "language": self.language,
            "defaultLanguage": self.default_language,
            "scope": {
                "authoredStaticConfiguration": True,
                "liveAccountState": False,
                "optimalPlanner": False,
                "dropProbabilitiesClaimed": False,
                "graphEvidenceUsed": False,
                "note": "Direct exported-table relationships only. UI obtain-way IDs and drop memberships remain qualified; availability, probability, runtime rolls, inventory, and optimal routing are not inferred.",
            },
            "sources": [
                {"root": label, "path": rel_path(path), "tables": [name for name in TABLE_NAMES if (path / name).is_file()]}
                for label, path in self.roots
            ],
            "counts": {
                "roots": len(self.root_ids), "nodes": len(nodes), "relations": len(relations),
                "nodeKinds": dict(sorted(kinds.items())), "relationKinds": dict(sorted(relation_kinds.items())),
                "confidence": dict(sorted(confidence.items())),
            },
            "rootIds": sorted(self.root_ids),
            "nodes": nodes,
            "relations": relations,
        }


def build_language(args: argparse.Namespace, language: str) -> tuple[Path, dict[str, Any], bool]:
    language = language.upper()
    default_language = args.default_language.upper()
    roots = table_roots(args.export_root)
    if not roots:
        raise FileNotFoundError(f"No structured table roots under {args.export_root}")
    tables = {name: load_table(roots, name, {}) for name in TABLE_NAMES}
    payload = Builder(language, default_language, roots, tables).payload()
    output = args.out_dir / language / "progression" / "index.json"
    changed = write_json(output, payload)
    return output, payload, changed


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for language in args.languages:
        output, payload, changed = build_language(args, language)
        counts = payload["counts"]
        display = output.relative_to(ROOT) if output.is_relative_to(ROOT) else output
        print(f"{language.upper()}: {counts['roots']} roots, {counts['nodes']} nodes, "
              f"{counts['relations']} relations, changed={str(changed).lower()} -> {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
