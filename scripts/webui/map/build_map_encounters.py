"""Publish compact authored encounter views from the Data page's last publication.

This Map-owned sidecar never builds Data or decodes installed formats. Its joins
use stored level/config ids and entity pointers. Missing or stale publications
produce visible diagnostics, and rows without a proved map anchor stay unplaced.

    python -m scripts.webui.map.build_map_encounters
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
from typing import Any

from scripts.common import (
    EXPORT_LAYOUT, GLOBAL_METADATA_REL, check_installed_native_inputs,
    resolve_installed_game_data_root,
)
from scripts.game_data.levelscript_union_tags import contract_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.webui.data_inspector.contract import json_safe
from scripts.webui.data_inspector.publication import load_dataset

SCHEMA = "endfield.webui.map-encounters.v1"
DATASETS = {
    "level-data": "game/Json/LevelData",
    "spawner-config": "game/Json/SpawnerConfig",
    "atmospheric-npc": "game/Json/AtmosphericNpcData",
    "map-config": "game/Json/MapConfig",
}
BOUNDARY = (
    "Stored encounter configuration and authored coordinates. Config ids, explicit "
    "level ids and entity pointers are the only placement joins. Wave timestamps, "
    "scene conditions and patrol points do not establish live activation, visibility "
    "or traversability; local spawner action positions are not world anchors."
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object expected: {path.name}")
    return value


def selected_native_signature(export_root: Path, game_root: Path | None = None,
                              ) -> tuple[dict[str, Any], str]:
    """Authenticate the selected install, never fall back from an alternate export."""
    expected = contract_native_inputs()
    signature: dict[str, Any] = {"unionTagNativeInputs": expected}
    if any(re.fullmatch(r"[0-9A-Fa-f]{64}", str(expected.get(key) or "")) is None
           for key in ("gameAssemblySha256", "metadataSha256")):
        return {**signature, "nativeStatus": "unavailable"}, "Union-tag contract native inputs are invalid."
    if game_root is None:
        if export_root.resolve() != EXPORT_LAYOUT.root.resolve():
            return {**signature, "nativeStatus": "unavailable"}, "Alternate export requires --game-root to authenticate its native-backed records."
        game_root = resolve_installed_game_data_root()
    gate = check_installed_native_inputs(
        expected["gameAssemblySha256"], expected["metadataSha256"],
        gameassembly=game_root.parent / "GameAssembly.dll",
        metadata=game_root / GLOBAL_METADATA_REL,
    )
    signature.update(gameAssemblySha256=gate.gameassembly_sha256,
                     metadataSha256=gate.metadata_sha256, nativeStatus=gate.status)
    return signature, "" if gate.validated else f"Selected native inputs {gate.status}: {gate.detail}"


def load_publication(data_root: Path, export_root: Path, dataset: str,
                     native: tuple[dict[str, Any], str] | None = None,
                     ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Supply the selected native proof for Map's named Data consumers."""
    def check(recorded: dict[str, Any]) -> str:
        selected, diagnostic = native if native is not None else selected_native_signature(export_root)
        if selected.get("nativeStatus") != "validated":
            return diagnostic or "selected native inputs are not validated"
        if recorded.get("selectedNative") != json_safe(selected):
            return "Data publication native provenance differs from the selected build"
        return ""

    return load_dataset(data_root, export_root, dataset, DATASETS[dataset],
                        signature_check=check if dataset in {"spawner-config", "atmospheric-npc"} else None)


def _rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("rows", value.get("values", value.get("value", [])))
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _value(value: Any) -> Any:
    return value.get("value") if isinstance(value, dict) and "value" in value else value


def _position(value: Any) -> dict[str, float] | None:
    values = [value.get(k) for k in ("x", "y", "z")] if isinstance(value, dict) else value
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return None
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in values):
        return None
    return dict(zip(("x", "y", "z"), values))


def _pick(row: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {key: row[key] for key in keys if key in row and row[key] is not None}


def _compact(value: Any) -> Any:
    """Remove byte cursor decoration, preserving all stored semantic fields."""
    if isinstance(value, list):
        return [_compact(v) for v in value]
    if isinstance(value, dict):
        if "value" in value and set(value) <= {"value", "startOffset", "endOffset", "count"}:
            return _compact(value["value"])
        return {key: _compact(v) for key, v in value.items()
                if key not in {"startOffset", "endOffset", "indexInCollection", "memberCount", "fieldOrder", "fieldOrderSource"}}
    return value


def _source(dataset: str, row: dict[str, Any]) -> dict[str, Any]:
    return {"datasetId": dataset, "recordId": row["id"], "status": row.get("status"),
            **_pick(row.get("source") or {}, "path", "href")}


def _base(dataset: str, record: dict[str, Any], kind: str, key: str,
          level: str = "", position: Any = None) -> dict[str, Any]:
    pos = _position(position)
    return {"id": f"{dataset}:{record['id']}#{kind}:{key}", "kind": kind,
            "levelId": level, "placement": "placed" if level and pos else "level" if level else "unplaced",
            "position": pos if level else None, "status": record.get("status", "unknown"),
            "sources": [_source(dataset, record)]}


def project_records(datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Project exact stored joins; leave missing/ambiguous joins explicit."""
    result: list[dict[str, Any]] = []
    hosts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entities: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in datasets.get("level-data", []):
        fields = (record.get("payload") or {}).get("fields") or {}
        level = str(_value(fields.get("sceneId")) or "")
        if not level or record.get("status") not in {"named_exact", "bounded_partial", "exact"}:
            continue
        for enemy in _rows(fields.get("enemies")):
            logic = str(enemy.get("levelLogicId") or "")
            position = _position((enemy.get("transform") or {}).get("position"))
            if logic and logic != "0" and position:
                entities[(level, f"world:{logic}")].append({"position": position, "source": _source("level-data", record)})
    for record in datasets.get("level-data", []):
        fields = (record.get("payload") or {}).get("fields") or {}
        level = str(_value(fields.get("sceneId")) or "")
        # A bounded frame may prove earlier fields, but no sceneId means no map join.
        if record.get("status") not in {"named_exact", "bounded_partial", "exact"}:
            continue
        for index, host in enumerate(_rows(fields.get("spawners"))):
            item = _base("level-data", record, "spawner", str(index), level, host.get("position"))
            item.update(title=str(host.get("configId") or host.get("spawnerId") or "Spawner"),
                        host=_pick(host, "configId", "spawnerId", "belongLevelScriptId", "enableWaveDieEvent", "rotation"))
            hosts[str(host.get("configId") or "")].append(item)
        for field, category in (("enemyPatrol", "enemy"), ("npcPatrol", "npc"), ("patrols", "general")):
            for index, patrol in enumerate(_rows(fields.get(field))):
                points = [{"position": _position(p.get("position")),
                           **_pick(p, "enterGaitRaw", "patrolGaitRaw"),
                           "actions": _compact(_rows(p.get("actions")))}
                          for p in _rows(patrol.get("points"))]
                points = [p for p in points if p["position"]]
                # General PatrolData may be local; retain its stored values without plotting them.
                world_points = points if field != "patrols" else []
                item = _base("level-data", record, "patrol", f"{field}:{index}", level,
                             world_points[0]["position"] if world_points else None)
                item.update(title=f"{category} patrol {patrol.get('patrolId', patrol.get('id', index))}",
                            category=category, fields=_compact({k: v for k, v in patrol.items() if k != "points"}),
                            points=points, plotPoints=world_points,
                            boundary="Stored point sequence; route ownership and runtime traversability are unresolved.")
                result.append(item)
        for index, group in enumerate(_rows(fields.get("enemyGroup"))):
            members = []
            member_sources = []
            for slot in _rows(group.get("slot")):
                pointer = slot.get("entityPtr") or {}
                logic_id = str(pointer.get("logicId") or "")
                identity = (f"script:{logic_id}:{pointer.get('slotId')}" if pointer.get("useSlotId")
                            else f"world:{logic_id}")
                candidates = entities.get((level, identity), []) if logic_id and logic_id != "0" else []
                members.append({"identity": identity, **_pick(slot, "leader", "offset"),
                                "position": _position(candidates[0].get("position")) if len(candidates) == 1 else None,
                                "join": "exact_entity_pointer" if len(candidates) == 1 else "ambiguous" if candidates else "unplaced"})
                if len(candidates) == 1:
                    member_sources.append(candidates[0]["source"])
            item = _base("level-data", record, "group", str(index), level)
            item.update(title=f"Enemy group {group.get('groupId', index)}",
                        fields=_pick(group, "groupId", "count", "patrolId", "radius", "speed", "templateId", "lockLeaderSlot"),
                        members=members)
            for source in member_sources:
                if source not in item["sources"]:
                    item["sources"].append(source)
            if level and any(m["position"] for m in members):
                item["placement"] = "placed"
            result.append(item)
    configs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in datasets.get("spawner-config", []):
        payload = record.get("payload") or {}
        if record.get("status") == "named_exact" and payload.get("configId"):
            configs[str(payload["configId"])].append(record)
        else:
            item = _base("spawner-config", record, "spawner", "unresolved")
            item.update(title=record.get("title") or record["id"], diagnostic=record.get("diagnostic") or
                        "Configuration decode is incomplete; no placement join attempted.")
            result.append(item)
    for config_id in sorted(set(configs) | set(hosts)):
        candidates = configs.get(config_id, [])
        linked_hosts = hosts.get(config_id, [])
        if len(candidates) == 1:
            record = candidates[0]
            payload = record["payload"]
            targets = linked_hosts or [_base("spawner-config", record, "spawner", "config")]
            for item in targets:
                item.update(title=config_id, configId=config_id,
                            enemyLibrary=_compact(payload.get("enemyLibrary") or []),
                            waves=_compact(payload.get("waves") or []), routes=_compact(payload.get("routeMap") or []),
                            settings=_compact(payload.get("settings") or {}),
                            configJoin="exact_config_id" if linked_hosts else "no_host",
                            boundary="Host coordinates only. Action positions and routes remain in their stored coordinate space.")
                source = _source("spawner-config", record)
                if source not in item["sources"]:
                    item["sources"].append(source)
                result.append(item)
        else:
            for item in linked_hosts:
                item.update(configJoin="ambiguous" if candidates else "missing",
                            diagnostic="Config id is ambiguous." if candidates else "Config is absent or unavailable in the Data publication.")
                result.append(item)
            for record in candidates:
                item = _base("spawner-config", record, "spawner", "ambiguous")
                item.update(title=config_id, diagnostic="Duplicate config id; no host join attempted.")
                result.append(item)
    for record in datasets.get("atmospheric-npc", []):
        entries = (record.get("payload") or {}).get("entries") or []
        for index, entry in enumerate(entries):
            named = entry.get("proxyBodyStatus") == "named_exact_npc_runtime_proxy"
            wrapper = entry.get("npcRuntimeProxyData") or {} if named else {}
            proxy = wrapper.get("npcRuntimeProxyData") or {}
            npc = wrapper.get("levelNpcData") or {}
            entity = (wrapper.get("levelEntityData") or {}).get("fields") or {}
            level = str(proxy.get("levelId") or "")
            item = _base("atmospheric-npc", record, "npc", str(index), level, entity.get("position"))
            item.update(title=npc.get("npcName") or npc.get("npcId") or entry.get("key") or record.get("title"),
                        fields={**_pick(npc, "npcId", "templateDataId", "npcName", "doPatrol", "defaultActivePatrol", "patrolIdNew", "defaultMontage"),
                                **_pick(proxy, "proxyId", "clusterId", "subDataParentId"),
                                **_pick(entity, "levelLogicId", "rotation", "createState")},
                        envTalkIds=_compact(npc.get("envTalkIds") or {}),
                        boundary="Authored NPC proxy placement; configured patrol ids do not prove the active patrol.")
            if not named:
                item["diagnostic"] = "NPC proxy body is opaque; level and position are not promoted."
            result.append(item)
        if not entries:
            item = _base("atmospheric-npc", record, "npc", "unresolved")
            item.update(title=record.get("title") or record["id"], diagnostic=record.get("diagnostic") or "No decoded NPC entries.")
            result.append(item)
    for record in datasets.get("map-config", []):
        fields = (record.get("payload") or {}).get("fields") or {}
        levels = fields.get("levelStrIds") or [] if record.get("status") == "named_exact" else []
        for level in dict.fromkeys(str(v) for v in levels) or {"": None}:
            item = _base("map-config", record, "scene-state", str(level), str(level))
            item.update(title=str(fields.get("mapIdStr") or record.get("title") or "Map conditions"),
                        sceneStates=fields.get("sceneStates") or {}, conditions=fields.get("sceneStateConditions") or [],
                        variables={"names": fields.get("mapVarNumId2Name") or {}, "defaults": fields.get("mapVarClientDefaultValues") or {}},
                        boundary="Map-wide stored scene conditions. Comparison codes are raw; no live result or entity visibility is inferred.")
            if not levels:
                item["diagnostic"] = record.get("diagnostic") or "No validated levelStrIds join."
            result.append(item)
    return result


def build(*, data_root: Path, export_root: Path, map_root: Path,
          game_root: Path | None = None) -> dict[str, Any]:
    datasets = {}
    audits = []
    try:
        native = selected_native_signature(export_root, game_root)
    except (OSError, ValueError, RuntimeError) as exc:
        native = ({"nativeStatus": "unavailable"}, str(exc)[:500])
    for dataset in DATASETS:
        records, audit = load_publication(data_root, export_root, dataset, native)
        datasets[dataset] = records
        audits.append(audit)
    map_index = _read(map_root / "index.json")
    levels = {str(variant["id"]) for row in map_index.get("maps", [])
              for variant in [row, *(row.get("variants") or [])]}
    rows = project_records(datasets)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        level = row["levelId"]
        if level not in levels:
            row["placement"] = "unplaced"
            row["diagnostic"] = row.get("diagnostic") or ("Referenced level has no published Map." if level else "No explicit level join.")
            buckets["unplaced"].append(row)
        else:
            buckets[level].append(row)
    out = map_root / "encounters"
    out.mkdir(parents=True, exist_ok=True)
    descriptors = []
    for level, entries in sorted(buckets.items()):
        # Map ids come from existing filenames, never from untrusted decoded ids.
        name = f"{level}.json"
        document = {"schema": SCHEMA, "levelId": level, "boundary": BOUNDARY,
                    "rows": sorted(entries, key=lambda r: (r["kind"], str(r.get("title") or ""), r["id"]))}
        target = (out / name).resolve()
        if not target.is_relative_to(out.resolve()):
            raise ValueError(f"Encounter output escapes its directory: {name}")
        target.write_text(json.dumps(json_safe(document), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        descriptors.append({"levelId": level, "path": name, "count": len(entries),
                            "bytes": target.stat().st_size, "kindCounts": dict(Counter(r["kind"] for r in entries))})
    index = {"schema": SCHEMA, "boundary": BOUNDARY, "datasets": audits, "levels": descriptors,
             "recordCount": len(rows), "kindCounts": dict(Counter(r["kind"] for r in rows))}
    # Replacing the index last makes missing families disappear even if old shards remain.
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "webui/data/data_inspector")
    parser.add_argument("--export-root", type=Path, default=EXPORT_LAYOUT.root)
    parser.add_argument("--game-root", type=Path, help="Selected Endfield_Data directory for native provenance (required for alternate exports).")
    parser.add_argument("--map-root", type=Path, default=REPO_ROOT / "webui/data/map_recovery")
    args = parser.parse_args(argv)
    index = build(data_root=args.data_root, export_root=args.export_root, map_root=args.map_root, game_root=args.game_root)
    print(f"map encounters: {index['recordCount']} authored rows; {index['kindCounts']}")
    for audit in index["datasets"]:
        print(f"  {audit['datasetId']}: {audit['status']} {audit.get('diagnostic', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
