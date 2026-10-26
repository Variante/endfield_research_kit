"""Publish authored combat dungeon catalogs, without inferring runtime waves."""
from __future__ import annotations
from scripts.webui.localization import HOTFIX_TABLE, read_text_table

import json
import re
from pathlib import Path

from scripts.common import EXPORT_ROOT, LANG_DIR, write_json
from scripts.webui.gameplay.battle_activities import TABLES as ACTIVITY_TABLES, activity_links

# Explicit supported gameplay categories; puzzle/factory/racing rows are not
# combat stages merely because they share DungeonTable's framing.
COMBAT_CATEGORIES = frozenset({
    "dungeon_highdifficulty", "dungeon_bossrush", "dungeon_resource",
    "dungeon_seasontower", "dungeon_actmonster", "dungeon_chartrial",
    "dungeon_chartutorial", "dungeon_train", "dungeon_worldlevel",
    "dungeon_weeklyraid", "dungeon_takestwo",
})
TABLES = (
    "DungeonTable", "DungeonSeriesTable", "DungeonTypeTable", "DungeonRaidTable",
    "RewardTable", "ItemTable", "EnemyTable", "EnemyDisplayInfoTable",
    "EnemyTemplateDisplayInfoTable", "ActivityDungeonTable", "ActivityTable", "SeasonTowerDungeonTable",
    *ACTIVITY_TABLES,
)
TEXT_FIELDS = ("dungeonDesc", "dungeonLevelDesc", "featureDesc", "mainGoalDesc", "extraGoalDesc")
REWARD_FIELDS = ("firstPassRewardId", "rewardId", "extraRewardId", "customRewardId", "hunterModeRewardId")


def description_parameters(value: str, params: list | None) -> str:
    """Substitute only authored numeric placeholders with the same row's keys."""
    values = {}
    for param in params or []:
        values.setdefault(param.get("key"), []).append(param.get("value"))

    def replace(match):
        key, decimals, percent = match.group(1), match.group(2) or "", match.group(3)
        candidates = values.get(key, [])
        if len(candidates) != 1 or not isinstance(candidates[0], (int, float)):
            return match.group(0)
        value = candidates[0] * (100 if percent else 1)
        return f"{value:.{len(decimals)}f}" + ("%" if percent else "")

    return re.sub(r"\{([^{}:]+):0(?:\.(0+))?(%)?\}", replace, value)


def project(tables: dict, i18n: dict, language: str, *, enemy_names: dict | None = None) -> dict:
    """Exact IDs own joins; missing targets remain explicitly unresolved."""
    def localized(value):
        if isinstance(value, dict):
            return str(i18n.get(str(value.get("id")), value.get("text") or ""))
        return str(value or "")

    dungeons = tables.get("DungeonTable", {})
    series = tables.get("DungeonSeriesTable", {})
    types = tables.get("DungeonTypeTable", {})
    raids = tables.get("DungeonRaidTable", {})
    rewards = tables.get("RewardTable", {})
    items = tables.get("ItemTable", {})
    enemies = tables.get("EnemyTable", {})
    display = tables.get("EnemyDisplayInfoTable", {})
    templates = tables.get("EnemyTemplateDisplayInfoTable", {})
    linked_activities = activity_links(tables, localized)

    entries = []
    for dungeon_id, row in dungeons.items():
        category = row.get("dungeonCategory")
        if category not in COMBAT_CATEGORIES:
            continue
        series_id = row.get("dungeonSeriesId") or ""
        group = series.get(series_id, {})
        members = group.get("includeDungeonIds") or []
        membership = dungeon_id in members
        raid = raids.get(dungeon_id, {})
        counterpart = raid.get("RelatedLevel") or ""
        enemy_rows = []
        for index, enemy_id in enumerate(row.get("enemyIds") or []):
            enemy = enemies.get(enemy_id, {})
            template_id = enemy.get("templateId") or ""
            info = display.get(enemy_id, {})
            template = templates.get(template_id, {})
            levels = row.get("enemyLevels") or []
            enemy_rows.append({
                "id": enemy_id, "name": (enemy_names or {}).get(enemy_id) or localized(info.get("name")) or localized(template.get("name")) or enemy_id,
                "level": levels[index] if index < len(levels) else None,
                "resolved": enemy_id in enemies or enemy_id in (enemy_names or {}),
            })
        reward_rows = []
        for field in REWARD_FIELDS:
            reward_id = row.get(field)
            if not reward_id:
                continue
            reward = rewards.get(reward_id, {})
            reward_rows.append({
                "field": field, "id": reward_id, "resolved": reward_id in rewards,
                "items": [{"id": bundle["id"], "name": localized(items.get(bundle["id"], {}).get("name")) or bundle["id"],
                           "count": bundle.get("count"), "resolved": bundle["id"] in items}
                          for bundle in reward.get("itemBundles", [])],
                "hasRandomRewards": bool(reward.get("probItemBundles")),
            })
        entries.append({
            "id": dungeon_id, "name": localized(row.get("dungeonName")) or dungeon_id,
            "category": category, "categoryName": localized(types.get(category, {}).get("enemyInfoTitle")) or category,
            "seriesId": series_id, "seriesName": localized(group.get("name")) or series_id,
            "seriesDescription": localized(group.get("desc")), "seriesResolved": series_id in series,
            "seriesOrder": group.get("sortId", 0), "order": members.index(dungeon_id) if membership else row.get("sortId", 0),
            "membershipConfirmed": membership,
            "mode": "raid" if raid.get("isRaid") is True else "normal" if raid.get("isRaid") is False else "unspecified",
            "counterpart": counterpart if counterpart in dungeons and dungeons[counterpart].get("dungeonCategory") in COMBAT_CATEGORIES else "",
            "recommendLevel": row.get("recommendLv"), "stamina": row.get("costStamina"),
            "hunterStamina": row.get("hunterModeCostStamina"),
            "texts": {field: localized(row.get(field)) for field in TEXT_FIELDS},
            "enemies": enemy_rows, "rewards": reward_rows, "activities": linked_activities.get(dungeon_id, []),
            "sceneId": row.get("sceneId") or "", "levelId": row.get("levelId") or "",
            "artTokens": [{"token": row[field], "table": "DungeonTable", "row": dungeon_id, "field": field}
                          for field in ("dungeonPicPath", "dungeonImg") if row.get(field)],
            "fieldDescription": description_parameters(localized(tables.get("SeasonTowerDungeonTable", {}).get(dungeon_id, {}).get("specialBuffDesc")), row.get("paramList")),
            "specialUnlockCondition": row.get("unlockSpCond") is True,
            "source": {"table": "DungeonTable", "row": dungeon_id},
        })
    entries.sort(key=lambda r: (r["category"] != "dungeon_highdifficulty", r["category"], r["seriesOrder"], r["seriesId"], r["order"], r["id"]))
    return {"schemaVersion": 3, "language": language, "evidenceBoundary": "storedConfiguration", "entries": entries}


def build(languages: list[str], *, export_root: Path = EXPORT_ROOT, output_root: Path = LANG_DIR, game_root: Path | None = None) -> int:
    from scripts.common import require_export_layout

    require_export_layout(export_root)
    table_root = export_root / "game" / "Table"
    # Required inputs fail visibly instead of replacing the catalog with emptiness.
    tables = {name: json.loads((table_root / f"{name}.json").read_text(encoding="utf-8-sig")) for name in TABLES}
    for language in languages:
        language = language.upper()
        i18n = read_text_table(table_root / f"I18nTextTable_{language}.json", language)
        payload = project(tables, i18n, language)
        enrich(payload, tables, output_root.parent, root=output_root / language, export_root=export_root, game_root=game_root)
        payload["sources"] = [f"game/Table/{name}.json" for name in (*TABLES, f"I18nTextTable_{language}")]
        if (table_root / HOTFIX_TABLE).is_file():
            payload["sources"].append(f"game/Table/{HOTFIX_TABLE}")
        output = output_root / language / "gameplay" / "battle_stages.json"
        write_json(output, payload)
        print(f"{language}: {len(payload['entries'])} combat stages -> {output}")
    return 0


def build_from_reference(languages: list[str], *, output_root: Path = LANG_DIR) -> int:
    """Preview only the last published WebUI data; never read an unfinished export."""
    for language in languages:
        language = language.upper()
        root = output_root / language
        index = json.loads((root / "reference" / "index.json").read_text(encoding="utf-8-sig"))
        if index.get("language") != language:
            raise ValueError(f"{language}: published reference index language mismatch: {index.get('language')!r}")
        files = {row["table"].removesuffix(".json"): row["file"] for row in index["tables"]}
        tables, sources = {}, []
        for name in TABLES:
            if name in files:
                path = root / "reference" / files[name]
                published = json.loads(path.read_text(encoding="utf-8-sig"))
                if published.get("language") != language or not isinstance(published.get("rawRows"), dict):
                    raise ValueError(f"{language}: published reference table has invalid language/rawRows: {path}")
                tables[name] = published["rawRows"]
                sources.append(f"reference/{files[name]}")
        for name in ("DungeonTable", "DungeonSeriesTable", "DungeonTypeTable"):
            if name not in tables:
                raise ValueError(f"{language}: required published reference table missing: {name}")
        enemy_names = {}
        gameplay_path = root / "gameplay" / "index.json"
        if gameplay_path.is_file():
            gameplay = json.loads(gameplay_path.read_text(encoding="utf-8-sig"))
            if gameplay.get("language") != language:
                raise ValueError(f"{language}: published Gameplay language mismatch: {gameplay_path}")
            for enemy in gameplay.get("entries", []):
                if enemy.get("kind") != "enemy":
                    continue
                enemy_names[enemy["id"]] = enemy["title"]
                for variant_id in enemy.get("variantIds", []):
                    enemy_names[variant_id] = enemy["title"]
            sources.append("gameplay/index.json")
        payload = project(tables, {}, language, enemy_names=enemy_names)
        enrich(payload, tables, output_root.parent, root=root)
        payload.update({"publicationMode": "referencePreview", "sources": sources,
                        "missingTables": [name for name in TABLES if name not in tables]})
        output = root / "gameplay" / "battle_stages.json"
        write_json(output, payload)
        print(f"{language}: {len(payload['entries'])} published-reference preview stages -> {output}")
    return 0


def enrich(payload: dict, tables: dict, data_root: Path, *, root: Path, export_root: Path | None = None, game_root: Path | None = None):
    from scripts.webui.gameplay.battle_evidence import load_evidence, project_encounters
    from scripts.webui.gameplay.battle_links import link_stages
    from scripts.webui.gameplay.battle_presentation import enrich_presentation

    enrich_presentation(payload, tables, data_root=data_root, language_root=root)
    datasets, audits = load_evidence(data_root / "data_inspector", export_root=export_root, game_root=game_root)
    subgames = conditions = None
    if export_root is not None:
        subgame_path = export_root / "game" / "Json" / "GameplayConfig" / "SubGameInstanceDataTable.json"
        if subgame_path.is_file():
            subgames = json.loads(subgame_path.read_text(encoding="utf-8-sig")).get("dataTable")
        condition_path = export_root / "game" / "Table" / "GameMechanicConditionTable.json"
        if condition_path.is_file():
            conditions = json.loads(condition_path.read_text(encoding="utf-8-sig"))
    bound = {key: row.get("bindScriptId") for key, row in (subgames or {}).items() if isinstance(row, dict)}
    project_encounters(payload["entries"], datasets, bound)
    link_stages(payload["entries"], data_root=data_root, root=root, conditions=conditions, subgames=subgames)
    # Stages in one shared scene reach the same spawners; publish each once.
    spawners: dict[str, dict] = {}
    for row in payload["entries"]:
        battle = row["battle"]
        configs = battle.pop("spawners")
        for cfg in configs:
            spawners.setdefault(cfg["id"], cfg)
        battle["spawnerIds"] = [cfg["id"] for cfg in configs]
    payload["spawners"] = spawners
    spawns = [spawn for cfg in spawners.values() for wave in cfg["waves"] for group in wave["groups"] for spawn in group["spawns"]]
    used_enemies = {e["id"] for row in payload["entries"] for e in row["enemies"]} | {s["enemyId"] for s in spawns}
    payload["enemyDetails"] = {key: value for key, value in payload["enemyDetails"].items() if key in used_enemies}
    used_buffs = {buff for enemy in payload["enemyDetails"].values() for buff in enemy["bornBuffs"]}
    used_buffs.update(buff["id"] for spawn in spawns for buff in spawn["buffs"])
    used_buffs.update(buff["id"] for row in payload["entries"] for buff in row["battle"]["fieldBuffs"])
    if export_root is not None:
        # Resolve every applied buff from BuffData, not only those the
        # character/enemy index happened to reference.
        from scripts.webui.gameplay.base_data import (build_gameplay_buff_catalog, load_gameplay_tag_registry,
                                                      load_native_gameplay_semantics)
        payload["buffDetails"] = build_gameplay_buff_catalog(
            export_root, sorted(used_buffs), load_native_gameplay_semantics(), load_gameplay_tag_registry(export_root))
    else:
        payload["buffDetails"] = {key: value for key, value in payload["buffDetails"].items() if key in used_buffs}
    payload["battleEvidence"] = audits
