"""Project stored battle references from Data's last publication.

Scene ids, LevelData script/host pointers and named dungeon-id switches own
joins. Wave ids and dictionary order never establish execution order.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from pathlib import Path

from scripts.common import EXPORT_ROOT, GLOBAL_METADATA_REL, check_installed_native_inputs, resolve_installed_game_data_root
from scripts.webui.data_inspector.publication import load_dataset, load_published_snapshot

FAMILIES = {"level-data": "LevelData", "levelscript-data": "LevelScriptData", "spawner-config": "SpawnerConfig"}


def load_evidence(data_root: Path, *, export_root: Path | None = None, game_root: Path | None = None) -> tuple[dict, list]:
    native_results = {}

    def native_check(recorded):
        selected = recorded.get("selectedNative") or {}
        assembly, metadata = selected.get("gameAssemblySha256"), selected.get("metadataSha256")
        if selected.get("nativeStatus") != "validated" or not assembly or not metadata:
            return "Data publication lacks validated selected-native inputs"
        if game_root is None and export_root is not None and export_root.resolve() != EXPORT_ROOT.resolve():
            return "Alternate export requires --game-root for native-backed battle evidence"
        pair = (assembly, metadata)
        if pair not in native_results:
            selected_root = game_root or resolve_installed_game_data_root()
            gate = check_installed_native_inputs(assembly, metadata,
                gameassembly=selected_root.parent / "GameAssembly.dll", metadata=selected_root / GLOBAL_METADATA_REL)
            native_results[pair] = "" if gate.validated else f"Selected native inputs {gate.status}: {gate.detail}"
        return native_results[pair]

    datasets, audits = {}, []
    for family, folder in FAMILIES.items():
        kwargs = {"signature_check": native_check} if family != "level-data" else {}
        if export_root is None:
            records, audit = load_published_snapshot(data_root, family, f"game/Json/{folder}", **kwargs)
        else:
            records, audit = load_dataset(data_root, export_root, family, f"game/Json/{folder}", **kwargs)
        if family == 'spawner-config' and records:
            statuses = Counter(str(row.get('status') or 'missing') for row in records)
            usable = sum(row.get('status') == 'named_exact'
                         and (row.get('payload') or {}).get('schemaStatus') == 'named_exact' for row in records)
            audit = {**audit, 'publicationStatus': audit.get('status'),
                     'usableRecordCount': usable, 'recordStatusCounts': dict(sorted(statuses.items()))}
            if not usable:
                first = next((str(row.get('diagnostic') or row.get('summary') or '')[:300]
                              for row in records if row.get('diagnostic') or row.get('summary')), '')
                audit.update(status='unavailable', diagnostic=(
                    'SpawnerConfig publication has no complete named records: '
                    + ', '.join(f'{name}={count}' for name, count in sorted(statuses.items()))
                    + (f'; first diagnostic: {first}' if first else '')))
        datasets[family] = records
        audits.append({key: audit[key] for key in ("datasetId", "status", "diagnostic", "recordCount", "manifestSha256",
            'publicationStatus', 'usableRecordCount', 'recordStatusCounts') if key in audit})
    return datasets, audits


def node_name(node):
    return node.get("action") or node.get("header") or node.get("wrapperName", "").split("Actions_")[-1].removesuffix("ForMemoryPack")


def node_id(node):
    return node.get("fields", {}).get("ID", node.get("envelope", {}).get("localId", node.get("envelope", {}).get("id")))


def literal(value):
    if isinstance(value, dict) and value.get("paramSource") == 0 and value.get("idRef", -1) == -1 and not value.get("path"):
        return value.get("value")
    return None


def next_id(node):
    return node.get("fields", {}).get("nextID", node.get("envelope", {}).get("nextId", -1))


def script_map(record):
    return record.get("payload", {}).get("ranges", {}).get("actionMap", {}).get("dataMap", {})


def dungeon_receivers(record, dungeon_id):
    """Only a named GetCurDungeonId -> SwitchString -> literal receiver chain."""
    data = script_map(record)
    getters = {node_id(n): n for n in data.get("getterList", [])}
    actions = {node_id(n): n for n in data.get("actionList", [])}
    receivers = set()
    for switch in actions.values():
        fields = switch.get("fields", {})
        value = fields.get("value") or {}
        if (node_name(switch) != "SwitchString" or value.get("paramSource") != -1
                or node_name(getters.get(value.get("idRef"), {})) != "GetCurDungeonId"):
            continue
        values, ids = fields.get("caseValueList", []), fields.get("caseIDList", [])
        if len(values) != len(ids):
            continue
        for case, start in zip(values, ids):
            if case != dungeon_id:
                continue
            visited = set()
            while start in actions and start not in visited:
                visited.add(start)
                node = actions[start]
                if node_name(node) == "RaiseCustomScriptEvent":
                    receiver = node.get("fields", {}).get("receiver") or {}
                    if receiver.get("mode") == "explicit_script" and receiver.get("paramSource") == 0:
                        receivers.add(str(receiver.get("scriptId")))
                # Do not traverse unknown, conditional, loop or parallel nodes.
                if node_name(node) in {"IfElseAction", "Split", "SwitchString"} or "Repeat" in node_name(node):
                    break
                start = next_id(node)
    return receivers


def project_spawner(record):
    payload = record.get("payload") or {}
    if record.get("status") != "named_exact" or payload.get("schemaStatus") != "named_exact":
        return None
    libraries = defaultdict(list)
    for row in payload.get("enemyLibrary", []):
        libraries[row.get("key")].append(row)
    waves = []
    for wave in payload.get("waves", []):
        groups = []
        for group in wave.get("groupMap", []):
            spawns, other = [], []
            for action in group.get("actionMap", []):
                if action.get("concreteType") != "SpawnerActions.SpawnMonsterFromTemplateV2":
                    other.append(action.get("concreteType") or "unresolved")
                    continue
                matches = libraries.get(action.get("libraryKey"), [])
                enemy = matches[0] if len(matches) == 1 else {}
                count = action.get("spawnCount")
                spawns.append({"enemyId": enemy.get("enemyId", ""), "level": enemy.get("enemyLevel"),
                    "count": count if isinstance(count, int) and count >= 0 else None,
                    "timestamp": action.get("timestamp"), "interval": action.get("spawnInterval"),
                    "actionId": action.get("actionId"), "libraryKey": action.get("libraryKey"),
                    "buffs": [{"id": b["buffId"], "blackboards": b.get("blackboards", [])} for b in enemy.get("bornBuffList", [])],
                    "aiOverride": enemy.get("overrideAIConfig") or "", "preWarnTime": enemy.get("preWarnTime"),
                    "resolved": bool(enemy), "levelUsesGrade": bool(payload.get("settings", {}).get("enemyLevelUseLevelGrade"))})
            spawns.sort(key=lambda s: _time(s["timestamp"]))
            non_spawning = {"SpawnerActions.PreviewRoute", "SpawnerActions.Pause", "SpawnerActions.RaiseEvent", "SpawnerActions.PlayAudio"}
            complete = (not payload.get("hasUnresolvedActionUnion") and all(t in non_spawning for t in other)
                        and all(s["count"] is not None and s["resolved"] for s in spawns))
            groups.append({"id": group.get("groupId"), "timestamp": group.get("timestamp"),
                "mode": group.get("groupMode"), "killCount": group.get("groupModeKillCount"),
                "targetKey": group.get("groupModeTargetKey"), "backupCount": group.get("groupBackUpCount"),
                "limitMaxCount": group.get("limitGroupMaxCount"), "maxCount": group.get("groupMaxCount"),
                "hasDeadline": group.get("hasDeadlineBegin"), "deadlineDelta": group.get("deadlineBeginDeltaTime"),
                "spawns": spawns, "otherActions": other,
                "configuredCount": sum(s["count"] for s in spawns) if complete else None})
        groups.sort(key=lambda g: _time(g["timestamp"]))
        complete = all(g["configuredCount"] is not None for g in groups)
        waves.append({"id": wave.get("waveId"), "key": wave.get("waveKey"), "timestamp": wave.get("timestamp"),
            "repeatable": wave.get("repeatable"), "hidden": wave.get("isHidden"), "mode": wave.get("waveMode"),
            "killCount": wave.get("waveModeKillCount"), "targetKey": wave.get("waveModeTargetKey"),
            "hasDeadline": wave.get("hasDeadlineBegin"), "deadlineDelta": wave.get("deadlineBeginDeltaTime"),
            "groups": groups, "configuredCount": sum(g["configuredCount"] for g in groups) if complete else None})
    waves.sort(key=lambda w: _time(w["timestamp"]))
    return {"id": payload.get("configId"), "waves": waves, "source": record["source"]["path"],
        "settings": payload.get("settings", {}), "unresolvedActions": bool(payload.get("hasUnresolvedActionUnion"))}


def _time(value):
    return value if isinstance(value, (int, float)) and math.isfinite(value) else math.inf


def script_buffs(record, spawner_ids):
    data = script_map(record)
    actions = {node_id(n): n for n in data.get("actionList", [])}
    getters = {node_id(n): n for n in data.get("getterList", [])}
    triggers = defaultdict(list)
    for header in data.get("headerList", []):
        pending, seen = [next_id(header)], set()
        while pending:
            nid = pending.pop()
            if nid not in actions or nid in seen:
                continue
            seen.add(nid)
            n = actions[nid]; f = n.get("fields", {})
            triggers[nid].append({"type": node_name(header), "eventKey": literal(header.get("fields", {}).get("eventKey"))})
            pending.append(next_id(n))
            if node_name(n) == "Split": pending.extend(f.get("idList", []))
            if node_name(n) == "IfElseAction": pending.extend([f.get("onFalseID"), f.get("onTrueID")])
            if node_name(n) == "SwitchString": pending.extend(f.get("caseIDList", []))
            if node_name(n).startswith("Repeat"): pending.append(f.get("doID"))
    rows = []
    for nid, node in actions.items():
        if node_name(node) not in {"AddBuffToTargetV2", "AddBuffToTargetFromGodEntity"}:
            continue
        f = node.get("fields", {}); buff_id = literal(f.get("buffId"))
        if not isinstance(buff_id, str) or not buff_id:
            continue
        target = f.get("target") or {}; scope = "unresolved"
        getter = getters.get(target.get("idRef"), {}) if target.get("paramSource") == -1 else {}
        if node_name(getter) == "GetMainCharacter": scope = "mainCharacter"
        for repeat in actions.values():
            rf = repeat.get("fields", {})
            if (node_name(repeat) != "RepeatEntityPtrListAction" or target.get("paramSource") != 100
                    or target.get("path") != (rf.get("entity") or {}).get("path")):
                continue
            pointer = rf.get("entityList") or {}
            g = getters.get(pointer.get("idRef"), {}) if pointer.get("paramSource") == -1 else {}
            spawner = literal(g.get("fields", {}).get("spawnerPtr"))
            if node_name(g) == "SpawnerGetSpawnedEntityList" and isinstance(spawner, dict) and str(spawner.get("id")) in spawner_ids:
                scope = "spawnedEnemies"
        rows.append({"id": buff_id, "actionId": nid, "target": scope,
            "triggers": triggers[nid], "blackboards": literal(f.get("blackboardKVPairList")) or [],
            "useBlackboard": literal(f.get("useBlackboard")), "source": record["source"]["path"]})
    return rows


def project_encounters(entries, datasets, bound_scripts=None):
    """Select each stage's spawners: a named dungeon branch first, then the
    stage's own ``SubGameInstanceDataTable.bindScriptId`` when a scene host
    belongs to that exact script; otherwise every host of the shared scene."""
    bound_scripts = bound_scripts or {}
    scenes = defaultdict(lambda: {"hosts": [], "scripts": set(), "sources": []})
    for record in datasets.get("level-data", []):
        if record.get("status") != "named_exact": continue
        fields = record.get("payload", {}).get("fields", {})
        scene = (fields.get("sceneId") or {}).get("value")
        if not scene: continue
        scenes[scene]["hosts"].extend(fields.get("spawners", {}).get("rows", []))
        scenes[scene]["scripts"].update(str(b["scriptId"]) for b in fields.get("levelScriptBriefDataDict", {}).get("entries", []))
        scenes[scene]["sources"].append(record["source"]["path"])
    scripts, configs = defaultdict(list), defaultdict(list)
    for r in datasets.get("levelscript-data", []):
        if r.get("status") == "named_exact": scripts[str(r.get("payload", {}).get("fields", {}).get("scriptId"))].append(r)
    for r in datasets.get("spawner-config", []):
        configs[r.get("payload", {}).get("configId")].append(r)
    for entry in entries:
        scene = scenes.get(entry["sceneId"])
        if not scene:
            entry["battle"] = {"selection": "unresolved", "spawners": [], "fieldBuffs": []}
            continue
        scene_scripts = [scripts[sid][0] for sid in sorted(scene["scripts"]) if len(scripts[sid]) == 1]
        receivers = set().union(*(dungeon_receivers(r, entry["id"]) for r in scene_scripts))
        owned = [h for h in scene["hosts"] if str(h.get("belongLevelScriptId")) in receivers]
        selection = "dungeonBranch" if owned else "sharedScene"
        bound = str(bound_scripts.get(entry["id"]) or "")
        if not owned and bound:
            owned = [h for h in scene["hosts"] if str(h.get("belongLevelScriptId")) == bound]
            if owned:
                selection, receivers = "boundScript", {bound}
        selected = bool(owned)
        hosts = owned if selected else scene["hosts"]
        spawners = []
        for host in hosts:
            candidates = configs[host.get("configId")]
            cfg = project_spawner(candidates[0]) if len(candidates) == 1 else None
            if cfg:
                spawners.append({**cfg, "hostId": str(host.get("spawnerId")), "scriptId": str(host.get("belongLevelScriptId"))})
        selected_scripts = [r for r in scene_scripts if not selected or str(r["payload"]["fields"]["scriptId"]) in receivers]
        ids = {str(h.get("spawnerId")) for h in hosts}
        entry["battle"] = {"selection": selection,
            "spawners": spawners, "fieldBuffs": [b for r in selected_scripts for b in script_buffs(r, ids)],
            "sources": scene["sources"], "receiverScriptIds": sorted(receivers)}
