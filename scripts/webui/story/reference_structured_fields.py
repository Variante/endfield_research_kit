"""Maintained structured-field renderers for Text Tables rows.

The Text page renders every exported table generically: a row title plus its
localized text nodes. That drops the structural half of a configuration table
(which reward a level grants, which chips a stage locks, which dungeon a
gameplay row drives), and it drops whole tables that carry no localized text.

This module is the maintained renderer layer for the table families where that
structure is worth showing. It is deliberately declarative: one rule table per
exported table stem, and one resolver that only ever performs an *exact* row
lookup in another exported table. A rule never matches by name similarity, and
an unresolved reference is published as unresolved rather than guessed.

Emitted shape, appended to a Text row as ``fields``::

    {
      "field": "upgradeQuestId",       # raw exported field name
      "label": "Upgrade quest",        # maintained display label
      "value": "c34m3_q#10",           # raw exported value, verbatim
      "ref": {"table": "MissionRuntimeAsset", "row": "c34m3"},
      "resolved": true,                # ref points at a row that exists
      "name": "..."                    # localized name of the referenced row
    }

``ref.table`` is an exported table stem, so the frontend can select that table
and that row inside the Text page itself. ``ref.table`` may also be the
pseudo-source ``MissionRuntimeAsset`` (a mission id) or ``Level`` (a level id);
those name the owning evidence source and stay non-navigable, because the Text
page has no row for them.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field as dataclass_field

#: Pseudo table stems used when the referenced row is not an exported table.
MISSION_SOURCE = "MissionRuntimeAsset"
LEVEL_SOURCE = "Level"


@dataclass(frozen=True)
class FieldRule:
    """One maintained field of one maintained table."""

    label: str
    #: Exported table stem (or a pseudo source) the value points at.
    table: str = ""
    #: Treat the exported value as a list of references.
    is_list: bool = False
    #: Reference row key derivation from the raw value.
    #: "" keeps the value, "questMission" turns ``c34m3_q#10`` into ``c34m3``.
    row_from: str = ""


_ROWS = FieldRule


#: table stem -> field name -> rule. Field order here is the render order.
TABLE_FIELD_RULES: dict[str, dict[str, FieldRule]] = {
    # --- Typhoea archery / shooting range activity -------------------------
    "TyphoeaArcheryConst": {
        "shootingRangeDomainId": _ROWS("Domain", table="DomainDataTable"),
        "shootingRangeLevelId": _ROWS("Level", table=LEVEL_SOURCE),
        "shootingRangeLimitedActivityId": _ROWS("Limited activity", table="ActivityTable"),
    },
    "TyphoeaArcheryLevelTable": {
        "level": _ROWS("Level"),
        "costItemCount": _ROWS("Cost item count"),
        "domainDevExp": _ROWS("Domain development exp"),
        "levelReward": _ROWS("Level reward", table="RewardTable"),
        "levelRewardPreview": _ROWS("Level reward preview", table="RewardTable"),
        "upgradeQuestId": _ROWS("Upgrade quest", table=MISSION_SOURCE, row_from="questMission"),
    },
    "TyphoeaArcheryChipTable": {
        "chipId": _ROWS("Chip"),
        "portableDeviceId": _ROWS("Portable device item", table="ItemTable"),
        "sortId": _ROWS("Sort id"),
    },
    "TyphoeaArcheryDailyTrainTable": {
        "dailyLevelId": _ROWS("Daily level dungeon", table="DungeonTable"),
        "gameId": _ROWS("Game dungeon", table="DungeonTable"),
        "unlockLevel": _ROWS("Unlocks at archery level", table="TyphoeaArcheryLevelTable"),
        "rankListId": _ROWS("Rank list"),
    },
    "TyphoeaArcheryDailyLevelId2RankId": {
        "$key": _ROWS("Daily level dungeon", table="DungeonTable"),
        "$value": _ROWS("Rank list"),
    },
    "TyphoeaArcherySimulateTrainGroupTable": {
        "simLevelGroupId": _ROWS("Simulate train group"),
        "style": _ROWS("Style"),
    },
    "TyphoeaArcherySimulateTrainTable": {
        "simLevelId": _ROWS("Simulate level dungeon", table="DungeonTable"),
        "gameId": _ROWS("Game dungeon", table="DungeonTable"),
        "simLevelGroupId": _ROWS("Group", table="TyphoeaArcherySimulateTrainGroupTable"),
        "preLevel": _ROWS("Previous level", table="TyphoeaArcherySimulateTrainTable"),
        "levelReward": _ROWS("Level reward", table="RewardTable"),
        "Lockedchips": _ROWS("Locked chips", table="TyphoeaArcheryChipTable", is_list=True),
        "unlockLevel": _ROWS("Unlocks at archery level", table="TyphoeaArcheryLevelTable"),
        "sortId": _ROWS("Sort id"),
    },
    "TyphoeaShootingRangeAffixTable": {
        "affixId": _ROWS("Affix"),
    },
    "TyphoeaShootingRangeAffixCombinationTable": {
        "affixCombinationId": _ROWS("Affix combination"),
        "affixIds": _ROWS("Affixes", table="TyphoeaShootingRangeAffixTable", is_list=True),
    },
    # --- Parkour / racing activity ----------------------------------------
    "ParkourConst": {
        "mainPanelInstructionId": _ROWS("Main panel instruction", table="InstructionBook"),
        "parkourActivityId": _ROWS("Activity", table="ActivityTable"),
    },
    "ParkourGameplayTable": {
        "gameMechanicsId": _ROWS("Game mechanics dungeon", table="DungeonTable"),
        "firstPassRewardId": _ROWS("First pass reward", table="RewardTable"),
        "extraRewardId1": _ROWS("Star 1 reward", table="RewardTable"),
        "extraRewardId2": _ROWS("Star 2 reward", table="RewardTable"),
        "extraRewardId3": _ROWS("Star 3 reward", table="RewardTable"),
    },
    "ParkourUiTable": {
        "gameMechanicsId": _ROWS("Gameplay row", table="ParkourGameplayTable"),
        "showRewardId": _ROWS("Shown reward", table="RewardTable"),
        "bubbleMaxNumber": _ROWS("Bubble max number"),
    },
    # --- Foresight build planner (light) ----------------------------------
    "ForesightCharGrowthTable": {
        "charId": _ROWS("Character", table="CharacterTable"),
        "activityId": _ROWS("Activity", table="ActivityTable"),
        "weaponIds": _ROWS("Weapons", table="WeaponBasicTable", is_list=True),
        "charTypeId": _ROWS("Damage type"),
        "rarity": _ROWS("Rarity"),
        "isReplica": _ROWS("Replica"),
    },
    "ForesightCharWpnRecommendTable": {
        "charId": _ROWS("Character", table="CharacterTable"),
        "weaponIds": _ROWS("Recommended weapons", table="WeaponBasicTable", is_list=True),
    },
    "ForesightWeaponTable": {
        "weaponId": _ROWS("Weapon", table="WeaponBasicTable"),
        "rarity": _ROWS("Rarity"),
        "tgtLv": _ROWS("Target level"),
    },
    "ForesightWeaponGemwishlistTable": {
        "weaponId": _ROWS("Weapon", table="WeaponBasicTable"),
        "rarity": _ROWS("Rarity"),
        "tgtLv": _ROWS("Target level"),
    },
    "ForesightGrowthConfigTable": {
        "key": _ROWS("Key"),
        "value": _ROWS("Value"),
        "stringList": _ROWS("Items", table="ItemTable", is_list=True),
    },
    "ForesightGrowthStageTable": {
        "stageId": _ROWS("Stage"),
        "level": _ROWS("Character level"),
        "weaponLevel": _ROWS("Weapon level"),
        "breakStage": _ROWS("Break stage"),
        "containTalent": _ROWS("Includes talent"),
    },
}

#: Tables whose rows are plain scalars keyed by a configuration name.
SCALAR_ROW_TABLES = frozenset({
    "TyphoeaArcheryConst",
    "ParkourConst",
    "TyphoeaArcheryDailyLevelId2RankId",
})

_QUEST_MISSION = re.compile(r"^([A-Za-z0-9]+?)_q#\d+$")


def maintained_tables() -> frozenset[str]:
    """Return the exported table stems this module renders."""
    return frozenset(TABLE_FIELD_RULES)


def is_maintained_table(table_name: str) -> bool:
    return table_stem(table_name) in TABLE_FIELD_RULES


def table_stem(table_name: str) -> str:
    return str(table_name or "").removesuffix(".json")


def quest_mission_id(value: str) -> str:
    """Return the mission id of a ``<mission>_q#<n>`` quest id, else ""."""
    match = _QUEST_MISSION.match(str(value or "").strip())
    return match.group(1) if match else ""


def _reference_row_key(rule: FieldRule, value) -> str:
    raw = "" if value is None else str(value)
    if not raw:
        return ""
    if rule.row_from == "questMission":
        return quest_mission_id(raw)
    if isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return raw


def _display_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return "" if value is None else str(value)


def _iter_values(rule: FieldRule, value) -> Iterable:
    if rule.is_list:
        if not isinstance(value, list):
            return []
        return [item for item in value if item not in (None, "")]
    return [value]


def _is_present(value) -> bool:
    return value not in (None, "", [], {})


@dataclass
class ReferenceResolver:
    """Exact row lookup across exported tables.

    ``row_exists`` answers whether ``<table stem>`` has row ``<key>``.
    ``row_name`` returns that row's localized display name, or "".
    """

    row_exists: Callable[[str, str], bool]
    row_name: Callable[[str, str], str] = dataclass_field(
        default=lambda _table, _row: ""
    )

    def resolve(self, table: str, row_key: str) -> tuple[bool, str]:
        if not table or not row_key:
            return (False, "")
        if table in {MISSION_SOURCE, LEVEL_SOURCE}:
            return (bool(self.row_exists(table, row_key)), "")
        if not self.row_exists(table, row_key):
            return (False, "")
        return (True, str(self.row_name(table, row_key) or ""))


def structured_reference_fields(
    table_name: str,
    row_key: str,
    row,
    resolver: ReferenceResolver,
) -> list[dict]:
    """Return the maintained structured fields for one exported table row.

    Returns ``[]`` for any table without a maintained rule set, so the caller
    keeps its generic behaviour untouched.
    """
    stem = table_stem(table_name)
    rules = TABLE_FIELD_RULES.get(stem)
    if not rules:
        return []

    if stem in SCALAR_ROW_TABLES and not isinstance(row, dict):
        return _scalar_row_fields(stem, rules, row_key, row, resolver)
    if not isinstance(row, dict):
        return []

    out: list[dict] = []
    for field_name, rule in rules.items():
        if field_name.startswith("$"):
            continue
        value = row.get(field_name)
        if not _is_present(value):
            continue
        out.extend(_field_entries(field_name, rule, value, resolver))
    return out


def _scalar_row_fields(
    stem: str,
    rules: dict[str, FieldRule],
    row_key: str,
    row,
    resolver: ReferenceResolver,
) -> list[dict]:
    """Render a ``Const``-shaped table whose row is a bare scalar."""
    key_rule = rules.get("$key")
    value_rule = rules.get("$value")
    if key_rule or value_rule:
        out: list[dict] = []
        if key_rule:
            out.extend(_field_entries("$key", key_rule, row_key, resolver))
        if value_rule and _is_present(row):
            out.extend(_field_entries("$value", value_rule, row, resolver))
        return out
    rule = rules.get(row_key)
    if rule is None or not _is_present(row):
        return []
    return _field_entries(row_key, rule, row, resolver)


def _field_entries(
    field_name: str,
    rule: FieldRule,
    value,
    resolver: ReferenceResolver,
) -> list[dict]:
    out: list[dict] = []
    for item in _iter_values(rule, value):
        if not _is_present(item):
            continue
        entry: dict = {
            "field": field_name,
            "label": rule.label,
            "value": _display_value(item),
        }
        if rule.table:
            ref_row = _reference_row_key(rule, item)
            if ref_row:
                resolved, name = resolver.resolve(rule.table, ref_row)
                entry["ref"] = {"table": rule.table, "row": ref_row}
                entry["resolved"] = resolved
                if name:
                    entry["name"] = name
        out.append(entry)
    return out


__all__ = [
    "FieldRule",
    "LEVEL_SOURCE",
    "MISSION_SOURCE",
    "ReferenceResolver",
    "SCALAR_ROW_TABLES",
    "TABLE_FIELD_RULES",
    "is_maintained_table",
    "maintained_tables",
    "quest_mission_id",
    "structured_reference_fields",
    "table_stem",
]
