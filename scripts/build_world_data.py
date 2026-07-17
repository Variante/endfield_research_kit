"""Build compact authored world data for the static WebUI.

The output intentionally describes authored configuration only.  It does not
represent live spawn state, simulation, mission progress, map visibility, or
player/account state.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXPORT_ROOT, LANG_DIR, rel_path, write_json


TABLE_REL = Path("structured") / "StreamingAssets" / "Table"
DATA_JSON_REL = Path("structured") / "StreamingAssets" / "Data" / "Json"
FALLBACK_TABLE_REL = Path("structured") / "Persistent" / "Table"
FALLBACK_DATA_JSON_REL = Path("structured") / "Persistent" / "Data" / "Json"
NULL_COUNT = 0xFFFFFFFF


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact static WebUI world data from authored Endfield exports.",
        epilog=("Outputs data/lang/<LANG>/world/index.json. Live spawn state, mission progress, "
                "simulation, visibility, inventory, and account state are excluded."),
    )
    parser.add_argument("--languages", nargs="+", default=["CN"], help="Language codes to build; default: CN.")
    parser.add_argument("--default-language", default="CN", help="Fallback language; default: CN.")
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT, help="Export root containing structured data.")
    parser.add_argument("--out-dir", type=Path, default=LANG_DIR, help="WebUI language output root.")
    return parser.parse_args(argv)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def clean_id(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def source_path(path: Path, export_root: Path) -> str:
    try:
        return path.relative_to(export_root).as_posix()
    except ValueError:
        return path.as_posix()


def source_root_label(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    return parts[1] if len(parts) > 1 and parts[0] == "structured" else path


def first_existing(export_root: Path, rel: Path) -> Path:
    for base in (Path("structured") / "StreamingAssets", Path("structured") / "Persistent"):
        path = export_root / base / rel
        if path.is_file():
            return path
    return export_root / "structured" / "StreamingAssets" / rel


def load_table(export_root: Path, name: str) -> dict[str, Any]:
    for rel in (TABLE_REL / name, FALLBACK_TABLE_REL / name):
        payload = read_json(export_root / rel, None)
        if isinstance(payload, dict):
            return payload
    return {}


def localized(i18n: dict[str, Any], fallback: dict[str, Any], node: Any) -> str:
    if isinstance(node, str):
        return node.strip()
    if not isinstance(node, dict):
        return ""
    text = clean_id(node.get("text"))
    if text:
        return text
    key = clean_id(node.get("id") or node.get("key"))
    return clean_id(i18n.get(key) or fallback.get(key)) if key and key != "0" else ""


def inferred_map_id(level_id: str) -> str:
    if "_lv" in level_id:
        return level_id.split("_lv", 1)[0]
    if level_id.lower().startswith("map"):
        prefix = level_id.split("_", 1)[0]
        if prefix[3:].isdigit():
            return prefix
    return ""


def relation(source: str, target: str, kind: str, evidence: str, confidence: str = "direct") -> tuple[str, str, str, str, str]:
    return source, target, kind, confidence, evidence


def mp_u32(data: bytes, offset: int, field: str, max_count: int = 50_000) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field}:truncated")
    value = struct.unpack_from("<I", data, offset)[0]
    if value != NULL_COUNT and value > max_count:
        raise ValueError(f"{field}:count={value}")
    return value, offset + 4


def mp_i32(data: bytes, offset: int, field: str) -> tuple[int, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field}:truncated")
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def mp_f32(data: bytes, offset: int, field: str) -> tuple[float, int]:
    if offset + 4 > len(data):
        raise ValueError(f"{field}:truncated")
    return round(struct.unpack_from("<f", data, offset)[0], 4), offset + 4


def mp_bool(data: bytes, offset: int, field: str) -> tuple[bool, int]:
    if offset >= len(data) or data[offset] not in (0, 1):
        raise ValueError(f"{field}:invalid")
    return bool(data[offset]), offset + 1


def mp_string(data: bytes, offset: int, field: str, max_length: int = 2048) -> tuple[str, int]:
    length, offset = mp_u32(data, offset, field, max_length)
    if length == NULL_COUNT:
        return "", offset
    end = offset + length
    if end > len(data):
        raise ValueError(f"{field}:truncated-string")
    try:
        return data[offset:end].decode("utf-8"), end
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field}:invalid-utf8") from exc


def decode_spawner_buff(data: bytes, offset: int) -> tuple[str, int]:
    if offset >= len(data) or data[offset] != 2:
        raise ValueError("buff:member-count")
    offset += 1
    count, offset = mp_u32(data, offset, "buff.blackboards", 256)
    if count == NULL_COUNT:
        count = 0
    for _ in range(count):
        if offset >= len(data) or data[offset] != 4:
            raise ValueError("blackboard:member-count")
        offset += 1
        _key, offset = mp_string(data, offset, "blackboard.key", 256)
        _use_string, offset = mp_bool(data, offset, "blackboard.useString")
        _value_float, offset = mp_f32(data, offset, "blackboard.valueFloat")
        _value_string, offset = mp_string(data, offset, "blackboard.valueString", 512)
    return mp_string(data, offset, "buff.id", 256)


def decode_spawner(path: Path) -> dict[str, Any] | None:
    """Decode the exact, guarded SpawnerConfig enemy-library prefix."""
    try:
        data = path.read_bytes()
        if not data or data[0] != 5:
            return None
        offset = 1
        config_id, offset = mp_string(data, offset, "configId", 512)
        count, offset = mp_u32(data, offset, "enemyLibrary", 10_000)
        if count == NULL_COUNT:
            count = 0
        enemies: list[dict[str, Any]] = []
        for index in range(count):
            if offset >= len(data) or data[offset] != 11:
                raise ValueError("enemy:member-count")
            offset += 1
            buff_count, offset = mp_u32(data, offset, "enemy.buffs", 256)
            if buff_count == NULL_COUNT:
                buff_count = 0
            buffs: list[str] = []
            for _ in range(buff_count):
                buff_id, offset = decode_spawner_buff(data, offset)
                if buff_id:
                    buffs.append(buff_id)
            enemy_id, offset = mp_string(data, offset, "enemy.id", 256)
            enemy_level, offset = mp_i32(data, offset, "enemy.level")
            forced, offset = mp_bool(data, offset, "enemy.forceToBattle")
            key, offset = mp_string(data, offset, "enemy.key", 256)
            ai, offset = mp_string(data, offset, "enemy.overrideAI", 512)
            gait, offset = mp_i32(data, offset, "enemy.patrolGait")
            audio, offset = mp_string(data, offset, "enemy.preWarnAudio", 512)
            rotation = []
            for axis in range(4):
                value, offset = mp_f32(data, offset, f"enemy.preWarnRotation[{axis}]")
                rotation.append(value)
            effect, offset = mp_string(data, offset, "enemy.preWarnEffect", 512)
            prewarn_time, offset = mp_f32(data, offset, "enemy.preWarnTime")
            enemies.append({
                "index": index, "enemyId": enemy_id, "enemyLevel": enemy_level,
                "forceToBattle": forced, "key": key, "overrideAIConfig": ai,
                "patrolGait": gait, "bornBuffIds": sorted(set(buffs)),
                "preWarnAudioId": audio, "preWarnEffectId": effect,
                "preWarnEffectFixedRotation": rotation, "preWarnTime": prewarn_time,
            })
        return {"configId": config_id or path.stem, "enemyLibrary": enemies}
    except (OSError, ValueError, struct.error):
        return None


def iter_files(root: Path) -> Iterable[Path]:
    return sorted((path for path in root.rglob("*.json") if path.is_file()), key=lambda path: path.as_posix().lower()) if root.is_dir() else []


def add_entry(entries: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    entry_id = clean_id(payload.get("id"))
    if entry_id:
        entries[entry_id] = {key: value for key, value in payload.items() if value not in (None, "", [], {})}


def build_language(language: str, fallback_language: str, export_root: Path) -> dict[str, Any]:
    i18n = load_table(export_root, f"I18nTextTable_{language}.json")
    fallback = i18n if language == fallback_language else load_table(export_root, f"I18nTextTable_{fallback_language}.json")
    if not i18n:
        i18n = fallback

    entries: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str, str, str]] = set()

    map_rows = load_table(export_root, "MapIdTable.json")
    level_desc = load_table(export_root, "LevelDescTable.json")
    level_basic_path = first_existing(export_root, Path("Data") / "Json" / "GameplayConfig" / "LevelBasicInfoTable.json")
    level_basic = read_json(level_basic_path, {}) or {}
    audio_level = load_table(export_root, "AudioLevel.json")
    audio_collections = load_table(export_root, "AudioCollection.json")
    enemy_table = load_table(export_root, "EnemyTable.json")
    enemy_display = load_table(export_root, "EnemyDisplayInfoTable.json")
    enemy_template_display = load_table(export_root, "EnemyTemplateDisplayInfoTable.json")
    interactive_attrs = load_table(export_root, "InteractiveAttributeDataTable.json")

    map_ids = set(map_rows)
    for map_id, row in sorted(map_rows.items()):
        if not isinstance(row, dict):
            continue
        add_entry(entries, {
            "id": f"map:{map_id}", "kind": "map",
            "name": localized(i18n, fallback, row.get("showName")) or map_id,
            "description": localized(i18n, fallback, row.get("description")),
            "mapId": map_id, "source": f"{TABLE_REL.as_posix()}/MapIdTable.json#{map_id}",
        })

    level_ids = set(level_desc) | set(level_basic) | set(audio_level)
    scripts_by_level: dict[str, list[str]] = defaultdict(list)
    level_script_root = export_root / DATA_JSON_REL / "LevelScriptData"
    if not level_script_root.is_dir():
        level_script_root = export_root / FALLBACK_DATA_JSON_REL / "LevelScriptData"
    for path in iter_files(level_script_root):
        level_id = path.parent.name
        script_id = path.stem
        entry_id = f"levelScript:{level_id}:{script_id}"
        scripts_by_level[level_id].append(script_id)
        add_entry(entries, {
            "id": entry_id, "kind": "levelScript", "name": script_id,
            "levelIds": [level_id], "scriptIds": [script_id],
            "source": source_path(path, export_root),
        })
        edges.add(relation(f"level:{level_id}", entry_id, "levelHasScript", "LevelScriptData directory and filename"))
        level_ids.add(level_id)

    level_audio_ids: dict[str, list[str]] = {}
    for level_id, row in sorted(audio_level.items()):
        if not isinstance(row, dict):
            continue
        values = [clean_id(value) for value in row.get("levelInitEvent") or [] if clean_id(value) not in ("", "0")]
        for field in ("battleMusicTriggerEvent", "customMusicModeBaseState"):
            value = clean_id(row.get(field))
            if value and value != "0":
                values.append(value)
        level_audio_ids[level_id] = sorted(set(values))

    for level_id in sorted(level_ids):
        desc = level_desc.get(level_id) if isinstance(level_desc.get(level_id), dict) else {}
        basic = level_basic.get(level_id) if isinstance(level_basic.get(level_id), dict) else {}
        map_id = inferred_map_id(level_id)
        if map_id and map_id not in map_ids:
            add_entry(entries, {"id": f"map:{map_id}", "kind": "map", "name": map_id, "mapId": map_id, "source": "inferred from authored level id prefix"})
            map_ids.add(map_id)
        add_entry(entries, {
            "id": f"level:{level_id}", "kind": "level",
            "name": localized(i18n, fallback, desc.get("showName")) or level_id,
            "description": localized(i18n, fallback, desc.get("description")),
            "mapId": map_id, "levelIds": [level_id],
            "levelType": basic.get("levelType"), "scope": basic.get("scope"),
            "configPath": clean_id(basic.get("configPath")),
            "audioIds": level_audio_ids.get(level_id, []),
            "scriptIds": sorted(scripts_by_level.get(level_id, [])),
            "source": source_path(level_basic_path, export_root) + f"#{level_id}" if basic else f"{TABLE_REL.as_posix()}/LevelDescTable.json#{level_id}",
        })
        if map_id:
            edges.add(relation(f"level:{level_id}", f"map:{map_id}", "levelBelongsToMap", "level id `_lv` prefix", "inferred"))
        for audio_id in level_audio_ids.get(level_id, []):
            slot_id = f"audioSlot:{audio_id}"
            add_entry(entries, {"id": slot_id, "kind": "audioSlot", "name": audio_id, "audioIds": [audio_id], "source": f"{TABLE_REL.as_posix()}/AudioLevel.json#{level_id}"})
            edges.add(relation(f"level:{level_id}", slot_id, "levelUsesAudioSlot", f"AudioLevel.{level_id}"))

    for collection_id, row in sorted(audio_collections.items()):
        if not isinstance(row, dict):
            continue
        audio_ids = sorted({clean_id(value) for value in row.values() if clean_id(value)})
        collection_entry = f"audioCollection:{collection_id}"
        add_entry(entries, {
            "id": collection_entry, "kind": "audioCollection", "name": collection_id,
            "audioIds": audio_ids, "slots": {key: value for key, value in sorted(row.items()) if clean_id(value)},
            "source": f"{TABLE_REL.as_posix()}/AudioCollection.json#{collection_id}",
        })
        for field, audio_id_raw in sorted(row.items()):
            audio_id = clean_id(audio_id_raw)
            if not audio_id:
                continue
            slot_id = f"audioSlot:{audio_id}"
            add_entry(entries, {"id": slot_id, "kind": "audioSlot", "name": audio_id, "audioIds": [audio_id], "source": f"{TABLE_REL.as_posix()}/AudioCollection.json#{collection_id}.{field}"})
            edges.add(relation(collection_entry, slot_id, "audioCollectionUsesSlot", f"AudioCollection.{collection_id}.{field}"))

    registry_rel = Path("Data") / "Json" / "GameplayConfig" / "WorldEntityRegistry.json"
    registry_paths = [
        export_root / base / registry_rel
        for base in (Path("structured") / "StreamingAssets", Path("structured") / "Persistent")
        if (export_root / base / registry_rel).is_file()
    ]
    registry_path = registry_paths[0] if registry_paths else export_root / "structured" / "StreamingAssets" / registry_rel
    registry_sources = [source_path(path, export_root) for path in registry_paths]
    world_rows: dict[str, Any] = {}
    world_row_sources: dict[str, list[str]] = defaultdict(list)
    for path in registry_paths:
        registry = read_json(path, {}) or {}
        rows = registry.get("worldEntityBriefInfos") if isinstance(registry, dict) else {}
        if isinstance(rows, dict):
            # Persistent and Streaming mirrors are collapsed by stable entity id.
            for entity_id, row in rows.items():
                entity_key = clean_id(entity_id)
                world_rows[entity_key] = row
                world_row_sources[entity_key].append(source_path(path, export_root))
    interactive_instances: Counter[str] = Counter()
    interactive_sources: dict[str, set[str]] = defaultdict(set)
    for entity_id, row in sorted((world_rows or {}).items(), key=lambda item: clean_id(item[0])):
        if not isinstance(row, dict):
            continue
        entity_key = clean_id(entity_id)
        detail_id = clean_id(row.get("detailId"))
        interactive_ids = [detail_id] if detail_id.startswith("int_") else []
        row_sources = sorted(set(world_row_sources.get(entity_key) or registry_sources))
        add_entry(entries, {
            "id": f"worldEntity:{entity_key}", "kind": "worldEntity", "name": detail_id or entity_key,
            "detailId": detail_id, "entityType": row.get("entityType"),
            "position": row.get("position"), "rotation": row.get("rotation"),
            "interactiveIds": interactive_ids, "source": row_sources[0] if row_sources else source_path(registry_path, export_root),
            "sources": [source_root_label(value) for value in row_sources],
        })
        if interactive_ids:
            interactive_instances[detail_id] += 1
            interactive_sources[detail_id].update(world_row_sources.get(entity_key) or registry_sources)
            edges.add(relation(f"worldEntity:{entity_key}", f"interactive:{detail_id}", "worldEntityUsesInteractive", f"worldEntityBriefInfos.{entity_key}.detailId"))

    for interactive_id, count in sorted(interactive_instances.items()):
        attr = interactive_attrs.get(interactive_id) if isinstance(interactive_attrs.get(interactive_id), dict) else {}
        audio_ids = sorted({clean_id(value) for value in (audio_collections.get(interactive_id) or {}).values() if clean_id(value)}) if isinstance(audio_collections.get(interactive_id), dict) else []
        interactive_source_paths = sorted(interactive_sources.get(interactive_id) or registry_sources)
        add_entry(entries, {
            "id": f"interactive:{interactive_id}", "kind": "interactive", "name": interactive_id,
            "interactiveIds": [interactive_id], "audioIds": audio_ids, "instanceCount": count,
            "attributes": {key: attr.get(key) for key in ("hp", "atk", "def", "pen") if key in attr},
            "source": f"{interactive_source_paths[0] if interactive_source_paths else source_path(registry_path, export_root)}#detailId:{interactive_id}",
            "sources": [source_root_label(value) for value in interactive_source_paths],
        })
        if interactive_id in audio_collections:
            edges.add(relation(f"interactive:{interactive_id}", f"audioCollection:{interactive_id}", "interactiveUsesAudioCollection", "matching authored detailId / AudioCollection key"))

    npc_path = first_existing(export_root, Path("Data") / "Json" / "GameplayConfig" / "NpcProxyTable.json")
    npc_ex_path = first_existing(export_root, Path("Data") / "Json" / "GameplayConfig" / "NpcProxyExDataTable.json")
    npc_rows_payload = read_json(npc_path, {}) or {}
    npc_rows = npc_rows_payload.get("dataTable") if isinstance(npc_rows_payload, dict) else {}
    npc_ex = read_json(npc_ex_path, {}) or {}
    proxy_info = npc_ex.get("proxyInfoData") if isinstance(npc_ex, dict) else {}
    for proxy_id, row in sorted((npc_rows or {}).items()):
        if not isinstance(row, dict):
            continue
        info = proxy_info.get(proxy_id) if isinstance(proxy_info, dict) and isinstance(proxy_info.get(proxy_id), dict) else {}
        level_id = clean_id(row.get("levelId"))
        map_id = clean_id(info.get("mapId")) or inferred_map_id(level_id)
        numeric_audio = clean_id((row.get("overrideInitAudioId") or {}).get("_id")) if isinstance(row.get("overrideInitAudioId"), dict) else ""
        audio_ids = [numeric_audio] if numeric_audio and numeric_audio != "0" else []
        add_entry(entries, {
            "id": f"npcProxy:{proxy_id}", "kind": "npcProxy", "name": clean_id(info.get("npcNameId")) or proxy_id,
            "description": clean_id(info.get("npcId")), "mapId": map_id,
            "levelIds": [level_id] if level_id else [], "position": row.get("position"), "rotation": row.get("rotation"),
            "entityType": row.get("entityType"), "audioIds": audio_ids,
            "aiConfigId": clean_id(row.get("aiCfg")), "npcGroupId": clean_id(row.get("npcGroupId")),
            "environmentTalkIds": sorted(clean_id(value) for value in row.get("envTalkIds") or [] if clean_id(value)),
            "controlByLevelScript": row.get("controlByLevelScript"), "source": source_path(npc_path, export_root) + f"#{proxy_id}",
        })
        if level_id:
            edges.add(relation(f"npcProxy:{proxy_id}", f"level:{level_id}", "npcProxyInLevel", f"NpcProxyTable.{proxy_id}.levelId"))
        if map_id:
            edges.add(relation(f"npcProxy:{proxy_id}", f"map:{map_id}", "npcProxyOnMap", f"NpcProxyExDataTable.proxyInfoData.{proxy_id}.mapId" if info.get("mapId") else "level id prefix", "direct" if info.get("mapId") else "inferred"))
        for audio_id in audio_ids:
            slot_id = f"audioSlot:{audio_id}"
            add_entry(entries, {"id": slot_id, "kind": "audioSlot", "name": audio_id, "audioIds": [audio_id], "source": source_path(npc_path, export_root) + f"#{proxy_id}.overrideInitAudioId"})
            edges.add(relation(f"npcProxy:{proxy_id}", slot_id, "npcProxyUsesAudio", f"NpcProxyTable.{proxy_id}.overrideInitAudioId"))

    spawner_root = export_root / DATA_JSON_REL / "SpawnerConfig"
    if not spawner_root.is_dir():
        spawner_root = export_root / FALLBACK_DATA_JSON_REL / "SpawnerConfig"
    referenced_enemy_ids: set[str] = set()
    for path in iter_files(spawner_root):
        decoded = decode_spawner(path)
        if not decoded:
            continue
        level_id = path.parent.name
        config_id = clean_id(decoded.get("configId")) or path.stem
        spawner_id = f"spawner:{level_id}:{config_id}"
        enemy_rows = decoded.get("enemyLibrary") or []
        enemy_ids = sorted({clean_id(row.get("enemyId")) for row in enemy_rows if clean_id(row.get("enemyId"))})
        audio_ids = sorted({clean_id(row.get("preWarnAudioId")) for row in enemy_rows if clean_id(row.get("preWarnAudioId"))})
        referenced_enemy_ids.update(enemy_ids)
        level_entry_id = f"level:{level_id}"
        if level_entry_id not in entries:
            map_id = inferred_map_id(level_id)
            add_entry(entries, {
                "id": level_entry_id, "kind": "level", "name": level_id,
                "mapId": map_id, "levelIds": [level_id], "source": "SpawnerConfig directory name",
            })
            if map_id:
                if f"map:{map_id}" not in entries:
                    add_entry(entries, {"id": f"map:{map_id}", "kind": "map", "name": map_id, "mapId": map_id, "source": "inferred from authored level id prefix"})
                edges.add(relation(level_entry_id, f"map:{map_id}", "levelBelongsToMap", "level id `_lv` prefix", "inferred"))
        add_entry(entries, {
            "id": spawner_id, "kind": "spawner", "name": config_id,
            "levelIds": [level_id], "enemyIds": enemy_ids, "audioIds": audio_ids,
            "enemyLibrary": enemy_rows, "source": source_path(path, export_root),
        })
        edges.add(relation(spawner_id, f"level:{level_id}", "spawnerInLevel", "SpawnerConfig directory name"))
        for enemy_id in enemy_ids:
            edges.add(relation(spawner_id, f"enemy:{enemy_id}", "spawnerSpawnsEnemy", "SpawnerConfig.enemyLibrary.enemyId"))
        for audio_id in audio_ids:
            slot_id = f"audioSlot:{audio_id}"
            add_entry(entries, {"id": slot_id, "kind": "audioSlot", "name": audio_id, "audioIds": [audio_id], "source": source_path(path, export_root) + "#enemyLibrary.preWarnAudioId"})
            edges.add(relation(spawner_id, slot_id, "spawnerUsesAudio", "SpawnerConfig.enemyLibrary.preWarnAudioEventKey"))

    # MapBriefInfo supplies authored enemy sets for the top-level maps.  Keep
    # this join conservative: only maps already established by MapIdTable or a
    # level prefix are promoted, rather than treating every dungeon id as a
    # separate top-level world map.
    map_lookup_path = first_existing(export_root, Path("Data") / "Json" / "GameplayConfig" / "MapIdTable.json")
    map_brief_path = first_existing(export_root, Path("Data") / "Json" / "GameplayConfig" / "MapBriefInfoTable.json")
    map_lookup = read_json(map_lookup_path, {}) or {}
    map_brief = read_json(map_brief_path, {}) or {}
    num_to_str = map_lookup.get("mapIdNumToStr") if isinstance(map_lookup, dict) else {}
    brief_maps = map_brief.get("mapTable") if isinstance(map_brief, dict) else {}
    for map_num, map_payload in sorted((brief_maps or {}).items(), key=lambda item: clean_id(item[0])):
        map_id = clean_id((num_to_str or {}).get(clean_id(map_num)))
        if not map_id or map_id not in map_ids or not isinstance(map_payload, dict):
            continue
        sublevels = map_payload.get("subLevelTable") if isinstance(map_payload.get("subLevelTable"), dict) else {}
        for sublevel_id, sublevel in sorted(sublevels.items()):
            if not isinstance(sublevel, dict):
                continue
            for enemy_id_raw in sublevel.get("enemyIdSet") or []:
                enemy_id = clean_id(enemy_id_raw)
                if not enemy_id:
                    continue
                referenced_enemy_ids.add(enemy_id)
                edges.add(relation(f"map:{map_id}", f"enemy:{enemy_id}", "mapHasEnemy", f"MapBriefInfoTable.mapTable.{map_num}.subLevelTable.{sublevel_id}.enemyIdSet"))

    for enemy_id in sorted(referenced_enemy_ids):
        row = enemy_table.get(enemy_id) if isinstance(enemy_table.get(enemy_id), dict) else {}
        template_id = clean_id(row.get("templateId")) or enemy_id
        display = enemy_display.get(enemy_id) if isinstance(enemy_display.get(enemy_id), dict) else {}
        template_display = enemy_template_display.get(template_id) if isinstance(enemy_template_display.get(template_id), dict) else {}
        model_id = clean_id(row.get("modelId"))
        add_entry(entries, {
            "id": f"enemy:{enemy_id}", "kind": "enemy",
            "name": localized(i18n, fallback, display.get("name")) or localized(i18n, fallback, template_display.get("name")) or enemy_id,
            "description": localized(i18n, fallback, display.get("description")) or localized(i18n, fallback, template_display.get("description")),
            "enemyIds": [enemy_id], "modelIds": [model_id] if model_id else [],
            "templateId": template_id, "aiConfigId": clean_id(row.get("aiTemplateId")),
            "source": f"{TABLE_REL.as_posix()}/EnemyTable.json#{enemy_id}",
        })
        if model_id:
            model_entry = f"model:{model_id}"
            add_entry(entries, {"id": model_entry, "kind": "model", "name": model_id, "modelIds": [model_id], "source": f"{TABLE_REL.as_posix()}/EnemyTable.json#{enemy_id}.modelId"})
            edges.add(relation(f"enemy:{enemy_id}", model_entry, "enemyUsesModel", f"EnemyTable.{enemy_id}.modelId"))

    ordered_entries = [entries[key] for key in sorted(entries)]
    ordered_relations = [
        {"source": source, "target": target, "type": kind, "confidence": confidence, "evidence": evidence}
        for source, target, kind, confidence, evidence in sorted(edges)
        if source in entries and target in entries
    ]
    kinds = dict(sorted(Counter(entry["kind"] for entry in ordered_entries).items()))
    return {
        "language": language,
        "scopeNote": ("Static authored world configuration with direct source evidence. Positions are authored coordinates; "
                      "map links inferred from level-id prefixes are labelled. Live spawn state, simulation, mission progress, "
                      "map visibility, inventory, and account state are excluded."),
        "counts": {"entries": len(ordered_entries), "relations": len(ordered_relations), "kinds": kinds},
        "entries": ordered_entries,
        "relations": ordered_relations,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    default_language = clean_id(args.default_language).upper() or "CN"
    built = 0
    for raw_language in args.languages:
        language = clean_id(raw_language).upper()
        if not language:
            continue
        payload = build_language(language, default_language, args.export_root)
        output = args.out_dir / language / "world" / "index.json"
        changed = write_json(output, payload)
        counts = payload["counts"]
        print(f"{language}: wrote {rel_path(output)} ({counts['entries']} entries, {counts['relations']} relations; changed={str(changed).lower()})")
        print("  kinds: " + ", ".join(f"{kind}={count}" for kind, count in counts["kinds"].items()))
        built += 1
    if not built:
        print("No non-empty language codes were supplied.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
