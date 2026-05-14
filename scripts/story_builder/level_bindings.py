from __future__ import annotations

from .context import *
from .anime_assets import *
from .scene_graph import *

def _topo_sort_quests(quests_out: list[dict]) -> list[dict]:
    by_id = {q["id"]: q for q in quests_out if q.get("id")}
    indegree = {qid: 0 for qid in by_id}
    succs: dict[str, set[str]] = defaultdict(set)

    def has_path(src: str, dst: str) -> bool:
        if src == dst:
            return True
        seen: set[str] = set()
        stack = list(succs.get(src) or [])
        while stack:
            cur = stack.pop()
            if cur == dst:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(succs.get(cur) or [])
        return False

    def add_edge(src: str, dst: str) -> None:
        if not src or not dst or src == dst:
            return
        if src not in by_id or dst not in by_id or dst in succs[src]:
            return
        succs[src].add(dst)
        indegree[dst] += 1

    for q in by_id.values():
        for prev in q.get("prev") or []:
            add_edge(prev, q["id"])

    story_ref_owners: dict[str, list[str]] = defaultdict(list)
    for q in by_id.values():
        qid = q["id"]
        for field_name in ("dialogs", "cutscenes", "remotecomms", "radios"):
            for ref in q.get(field_name) or []:
                if ref and qid not in story_ref_owners[ref]:
                    story_ref_owners[ref].append(qid)

    # A failedCondition story ref is an authored "this branch closes when that
    # scene happens" guard. Use it as a weak chronology edge when it does not
    # contradict the explicit prevQuestIdList graph.
    for q in by_id.values():
        qid = q["id"]
        for ref in q.get("failStoryRefs") or []:
            for owner_id in story_ref_owners.get(ref) or []:
                if owner_id == qid or has_path(owner_id, qid):
                    continue
                add_edge(qid, owner_id)

    ready = [by_id[qid] for qid, deg in indegree.items() if deg == 0]
    ready.sort(key=_quest_sort_key)

    out: list[dict] = []
    emitted: set[str] = set()
    while ready:
        cur = ready.pop(0)
        qid = cur["id"]
        if qid in emitted:
            continue
        emitted.add(qid)
        out.append(cur)
        for nxt in sorted(succs.get(qid, []), key=lambda next_id: _quest_sort_key(by_id[next_id])):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(by_id[nxt])
        ready.sort(key=_quest_sort_key)

    if len(out) < len(by_id):
        for q in sorted(by_id.values(), key=_quest_sort_key):
            if q["id"] not in emitted:
                out.append(q)
    return out


def _load_npc_proxy_ex() -> dict:
    global _NPC_PROXY_EX_CACHE
    if _NPC_PROXY_EX_CACHE is not None:
        return _NPC_PROXY_EX_CACHE
    if not NPC_PROXY_EX_PATH.exists():
        _NPC_PROXY_EX_CACHE = {}
        return _NPC_PROXY_EX_CACHE
    try:
        with NPC_PROXY_EX_PATH.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _NPC_PROXY_EX_CACHE = {}
        return _NPC_PROXY_EX_CACHE
    _NPC_PROXY_EX_CACHE = raw if isinstance(raw, dict) else {}
    return _NPC_PROXY_EX_CACHE


def _levelscript_file_sort_key(path: Path) -> tuple:
    stem = path.stem
    if stem.isdigit():
        return (0, int(stem), stem)
    return (1, stem)


def _load_mission_levelscript_dialogs(mission_id: str, level_ids: list[str]) -> list[dict]:
    cache_key = (mission_id, tuple(dict.fromkeys(level_ids)))
    if cache_key in _MISSION_LEVELSCRIPT_CACHE:
        return _MISSION_LEVELSCRIPT_CACHE[cache_key]

    prefix = f"dlg_{mission_id}_".encode("ascii")
    hints: list[dict] = []
    for level_id in cache_key[1]:
        if not level_id:
            continue
        level_dir = LEVELSCRIPT_DIR / level_id
        if not level_dir.is_dir():
            continue
        for path in sorted(level_dir.glob("*.json"), key=_levelscript_file_sort_key):
            try:
                blob = path.read_bytes()
            except OSError:
                continue
            if prefix not in blob:
                continue
            dialogs: list[str] = []
            for token in re.findall(rb"[ -~]{4,}", blob):
                text = token.decode("ascii", "ignore")
                for dialog_id in re.findall(rf"dlg_{re.escape(mission_id)}_\d+", text):
                    if dialog_id not in dialogs:
                        dialogs.append(dialog_id)
            if dialogs:
                hints.append({
                    "levelId": level_id,
                    "file": repo_rel(path),
                    "fileOrder": _levelscript_file_sort_key(path),
                    "dialogs": dialogs,
                })
    _MISSION_LEVELSCRIPT_CACHE[cache_key] = hints
    return hints


def _u16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off : off + 2], "little", signed=False)


def _u32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off : off + 4], "little", signed=False)


def _i32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off : off + 4], "little", signed=True)


def _is_printable_ascii(blob: bytes) -> bool:
    return all(PRINTABLE_ASCII_MIN <= b <= PRINTABLE_ASCII_MAX for b in blob)


def _extract_tagged_ascii_strings(
    data: bytes,
    tag: int,
    *,
    max_len: int = 120,
) -> list[dict]:
    hits: list[dict] = []
    end = len(data) - 5
    i = 0
    while i < end:
        if data[i] != tag:
            i += 1
            continue
        size = int.from_bytes(data[i + 1 : i + 5], "little", signed=False)
        if size <= 0 or size > max_len or i + 5 + size > len(data):
            i += 1
            continue
        raw = data[i + 5 : i + 5 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({
            "offset": i,
            "text": text,
        })
        i += 5 + size
    return hits


def _decode_uid_record(data: bytes, uid_off: int, uid: str) -> dict | None:
    if uid_off >= 14:
        start = uid_off - 14
        if start + 32 <= len(data):
            if (
                data[start] == 0xFA
                and data[start + 4] == 0
                and data[start + 9] == 0
                and _u32(data, start + 10) == 8
            ):
                local_id = _u32(data, start + 5)
                if local_id <= 0x1000:
                    return {
                        "start": start,
                        "layout": "fa",
                        "code": _u16(data, start + 1),
                        "kind": data[start + 3],
                        "localId": local_id,
                        "uid": uid,
                        "nextId": _i32(data, start + 28),
                        "payloadStart": start + 32,
                        "strings": [],
                    }

    if uid_off >= 12:
        start = uid_off - 12
        if start + 30 <= len(data):
            code = _u16(data, start)
            kind = data[start + 2]
            local_id = _u32(data, start + 3)
            if (
                code <= 0x1FFF
                and kind <= 0x10
                and local_id <= 0x1000
                and data[start + 7] == 0
                and _u32(data, start + 8) == 8
            ):
                return {
                    "start": start,
                    "layout": "plain",
                    "code": code,
                    "kind": kind,
                    "localId": local_id,
                    "uid": uid,
                    "nextId": _i32(data, start + 26),
                    "payloadStart": start + 30,
                    "strings": [],
                }

    return None


def _extract_uid_records(data: bytes, string_hits: list[dict]) -> list[dict]:
    records: list[dict] = []
    seen_starts: set[int] = set()
    sorted_hits = sorted(string_hits, key=lambda hit: hit["offset"])

    for match in HEX_UID_RE.finditer(data):
        uid_off = match.start()
        uid = match.group().decode("ascii")
        record = _decode_uid_record(data, uid_off, uid)
        if record is None or record["start"] in seen_starts:
            continue
        seen_starts.add(record["start"])
        records.append(record)

    records.sort(key=lambda record: record["start"])
    if not records:
        return records

    hit_idx = 0
    for idx, record in enumerate(records):
        next_start = records[idx + 1]["start"] if idx + 1 < len(records) else len(data)
        while hit_idx < len(sorted_hits) and sorted_hits[hit_idx]["offset"] < record["payloadStart"]:
            hit_idx += 1
        scan_idx = hit_idx
        while scan_idx < len(sorted_hits) and sorted_hits[scan_idx]["offset"] < next_start:
            record["strings"].append(sorted_hits[scan_idx])
            scan_idx += 1

    return records


def _build_unique_record_target_map(records: list[dict]) -> dict[int, dict]:
    by_local_id: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        by_local_id[record["localId"]].append(record)
    return {
        local_id: bucket[0]
        for local_id, bucket in by_local_id.items()
        if len(bucket) == 1
    }


def _build_uid_record_chains(records: list[dict]) -> list[list[dict]]:
    if not records:
        return []

    unique_targets = _build_unique_record_target_map(records)
    by_start = {record["start"]: record for record in records}
    target_starts = {
        target["start"]
        for record in records
        if (target := unique_targets.get(record["nextId"])) is not None
    }
    entry_starts = [record["start"] for record in records if record["start"] not in target_starts]
    chains: list[list[dict]] = []
    seen: set[int] = set()

    for entry_start in entry_starts:
        chain: list[dict] = []
        current = entry_start
        while current in by_start and current not in seen:
            record = by_start[current]
            chain.append(record)
            seen.add(record["start"])
            target = unique_targets.get(record["nextId"])
            if target is None:
                break
            current = target["start"]
        if chain:
            chains.append(chain)

    for record in records:
        if record["start"] not in seen:
            chains.append([record])
    return chains


def _extract_named_entry_tables(
    data: bytes,
    *,
    min_entries: int = 3,
    max_string_len: int = 120,
) -> list[list[dict]]:
    tables: list[list[dict]] = []
    limit = len(data) - 4
    for start in range(limit):
        count = int.from_bytes(data[start : start + 4], "little", signed=False)
        if count < min_entries or count > 64:
            continue
        pos = start + 4
        entries: list[dict] = []
        ok = True
        for _ in range(count):
            if pos + 8 > len(data):
                ok = False
                break
            key = int.from_bytes(data[pos : pos + 4], "little", signed=False)
            size = int.from_bytes(data[pos + 4 : pos + 8], "little", signed=False)
            pos += 8
            if size <= 0 or size > max_string_len or pos + size > len(data):
                ok = False
                break
            raw = data[pos : pos + size]
            pos += size
            if not _is_printable_ascii(raw):
                ok = False
                break
            entries.append({
                "key": key,
                "text": raw.decode("ascii"),
            })
        if ok:
            tables.append(entries)
    return tables


def _choose_best_named_entry_table(data: bytes) -> list[dict]:
    tables = _extract_named_entry_tables(data)
    if not tables:
        return []

    def score(entries: list[dict]) -> tuple[int, int]:
        lt_count = sum(1 for entry in entries if LT_BINDING_RE.match(entry["text"]))
        return (lt_count, len(entries))

    return max(tables, key=score)


def _load_leveldata_named_entries(path: Path) -> list[dict]:
    cache_key = str(path)
    if cache_key in _LEVELDATA_NAMED_TABLE_CACHE:
        return _LEVELDATA_NAMED_TABLE_CACHE[cache_key]

    try:
        data = path.read_bytes()
    except OSError:
        entries: list[dict] = []
    else:
        entries = _choose_best_named_entry_table(data)

    _LEVELDATA_NAMED_TABLE_CACHE[cache_key] = entries
    return entries


def _load_levelscript_binding_data(level_id: str) -> dict:
    if level_id in _LEVELSCRIPT_BINDING_CACHE:
        return _LEVELSCRIPT_BINDING_CACHE[level_id]

    out = {
        "uidPayloads": {},
        "files": [],
    }
    level_dir = LEVELSCRIPT_DIR / level_id
    if not level_dir.is_dir():
        _LEVELSCRIPT_BINDING_CACHE[level_id] = out
        return out

    def add_payload(uid: str, payload: str) -> None:
        bucket = out["uidPayloads"].setdefault(uid, [])
        if payload not in bucket:
            bucket.append(payload)

    for path in sorted(level_dir.glob("*.json"), key=_levelscript_file_sort_key):
        try:
            data = path.read_bytes()
        except OSError:
            continue

        string_hits = _extract_tagged_ascii_strings(data, 0x04)
        records = _extract_uid_records(data, string_hits)
        if not records and not string_hits:
            continue

        sorted_hits = sorted(string_hits, key=lambda hit: hit["offset"])
        for record in records:
            for hit in record["strings"]:
                add_payload(record["uid"], hit["text"])

        for match in HEX_UID_RE.finditer(data):
            uid_off = match.start()
            uid = match.group().decode("ascii")
            for hit in sorted_hits:
                if hit["offset"] <= uid_off:
                    continue
                if hit["offset"] - uid_off > 80:
                    break
                add_payload(uid, hit["text"])
                break

        out["files"].append({
            "file": repo_rel(path),
            "records": records,
            "stringHits": sorted_hits,
        })

    _LEVELSCRIPT_BINDING_CACHE[level_id] = out
    return out


def _build_levelscript_file_order_scene_sequences(
    level_id: str,
    dialog_key_resolver,
    mission_id: str = "",
) -> list[dict]:
    """Return per-file scene-ref sequences ordered by byte offset in each
    levelscript file. Complements `_build_levelscript_scene_chain_map`,
    which only follows UID `nextId` linked-list chains. Boss-fight scripts
    sprinkle scene refs across parallel event records that aren't UID-linked;
    file offset still tracks the SerializeReference authoring order and gives
    a usable weak ordering hint. Caller is responsible for treating these as
    weak edges, not tight constraints."""
    info = _load_levelscript_binding_data(level_id)
    out: list[dict] = []
    for file_info in info["files"]:
        scene_keys: list[str] = []
        seen: set[str] = set()
        for hit in file_info.get("stringHits") or []:
            text = hit.get("text") or ""
            scene_key = _resolve_payload_scene_key(text, mission_id, dialog_key_resolver)
            if not scene_key or scene_key in seen:
                continue
            seen.add(scene_key)
            scene_keys.append(scene_key)
        if len(scene_keys) < 2:
            continue
        out.append({
            "levelId": level_id,
            "file": file_info["file"],
            "sequence": scene_keys,
        })
    return out


def _annotate_binding_payloads(
    payloads: list[str],
    dialog_key_resolver,
    mission_id: str = "",
) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for payload in payloads:
        if not payload or payload in seen:
            continue
        seen.add(payload)
        ref = {"text": payload}
        node_key = ""
        node_kind = ""
        scene_key = _resolve_payload_scene_key(payload, mission_id, dialog_key_resolver)
        if scene_key:
            node_key = scene_key
            node_kind = _scene_graph_node_kind(scene_key)
            ref["sceneKey"] = scene_key
        elif (node_key := _scene_graph_runtime_payload_key(payload, mission_id, dialog_key_resolver)):
            node_kind = _scene_graph_node_kind(node_key)
        if node_key:
            ref["nodeKey"] = node_key
        if node_kind:
            ref["kind"] = node_kind
        out.append(ref)
    return out


def _build_level_binding_groups(
    named_entries: list[dict],
    uid_payloads: dict[str, list[str]],
    dialog_key_resolver,
    mission_id: str = "",
) -> list[dict]:
    groups: list[dict] = []
    current: dict | None = None
    for entry in named_entries:
        match = LT_BINDING_RE.match(entry["text"])
        if match:
            if current is None:
                current = {"label": "Ungrouped", "rows": []}
                groups.append(current)
            payloads: list[str] = []
            for uid in (match.group("uid1"), match.group("uid2")):
                for payload in uid_payloads.get(uid, []):
                    if payload not in payloads:
                        payloads.append(payload)
            current["rows"].append({
                "key": entry["key"],
                "text": entry["text"],
                "kind": match.group("kind"),
                "payloads": _annotate_binding_payloads(payloads, dialog_key_resolver, mission_id),
                "_debug": {
                    "source": {
                        "key": entry["key"],
                        "text": entry["text"],
                        "uids": [match.group("uid1"), match.group("uid2")],
                    },
                },
            })
            continue
        if entry["text"].endswith("ID"):
            continue
        current = {"label": entry["text"], "rows": []}
        groups.append(current)
    return [group for group in groups if group["rows"]]


def _make_levelscript_chain_step(record: dict, dialog_key_resolver, mission_id: str = "") -> dict:
    payloads = _annotate_binding_payloads(
        [hit["text"] for hit in record["strings"]],
        dialog_key_resolver,
        mission_id,
    )
    return {
        "localId": record["localId"],
        "nextId": record["nextId"],
        "payloads": payloads,
        "_debug": {
            "source": {
                "layout": record["layout"],
                "code": f"0x{record['code']:04x}",
                "kind": f"0x{record['kind']:02x}",
                "uid": record["uid"],
                "start": record["start"],
            },
        },
    }


def _build_levelscript_scene_chain_map(
    level_id: str,
    dialog_key_resolver,
    mission_id: str = "",
) -> dict[str, list[dict]]:
    info = _load_levelscript_binding_data(level_id)
    scene_chains: dict[str, list[dict]] = defaultdict(list)
    seen_signatures: set[tuple] = set()

    for file_info in info["files"]:
        for chain in _build_uid_record_chains(file_info["records"]):
            if len(chain) < 2:
                continue
            steps = [_make_levelscript_chain_step(record, dialog_key_resolver, mission_id) for record in chain]
            scene_keys: list[str] = []
            seen_scene_keys: set[str] = set()
            for step in steps:
                for payload in step["payloads"]:
                    scene_key = payload.get("sceneKey")
                    if scene_key and scene_key not in seen_scene_keys:
                        seen_scene_keys.add(scene_key)
                        scene_keys.append(scene_key)
            if not scene_keys:
                continue

            signature = (
                file_info["file"],
                tuple(
                    (
                        step["localId"],
                        tuple(payload["text"] for payload in step["payloads"]),
                    )
                    for step in steps
                ),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            chain_entry = {
                "levelId": level_id,
                "file": file_info["file"],
                "steps": steps,
                "_debug": {
                    "source": {
                        "file": file_info["file"],
                        "levelId": level_id,
                    },
                },
            }
            for scene_key in scene_keys:
                scene_chains[scene_key].append(chain_entry)

    return scene_chains


def _scene_binding_search_text(binding_entry: dict) -> str:
    parts: list[str] = []
    for group in binding_entry.get("groups") or []:
        if group.get("label"):
            parts.append(group["label"])
        for row in group.get("rows") or []:
            if row.get("text"):
                parts.append(row["text"])
            for payload in row.get("payloads") or []:
                if payload.get("text"):
                    parts.append(payload["text"])
    for chain in binding_entry.get("chains") or []:
        if chain.get("levelId"):
            parts.append(chain["levelId"])
        for step in chain.get("steps") or []:
            for payload in step.get("payloads") or []:
                if payload.get("text"):
                    parts.append(payload["text"])
    return " ".join(part for part in parts if part)


def infer_mission_dialog_order(
    mission_id: str,
    mission_entries: list[dict],
    mission_flow: dict | None,
    mission_level_refs: list[dict] | None = None,
) -> dict[str, int]:
    entries_by_key = {
        entry["k"]: entry
        for entry in mission_entries
        if entry.get("d") in MISSION_SCENE_ENTRY_KINDS and entry.get("k")
    }
    if not entries_by_key:
        return {}
    dialog_entries_by_key = {
        key: entry
        for key, entry in entries_by_key.items()
        if entry.get("d") in ("dlg", "sns")
    }

    npc_proxy_ex = _load_npc_proxy_ex()
    proxy_rows = npc_proxy_ex.get("data") or {}
    proxy_info = npc_proxy_ex.get("proxyInfoData") or {}

    level_ids: list[str] = []
    if mission_flow:
        if mission_flow.get("level"):
            level_ids.append(mission_flow["level"])
        for quest in mission_flow.get("quests") or []:
            for scene_id in quest.get("scenes") or []:
                if scene_id and scene_id not in level_ids:
                    level_ids.append(scene_id)
    for ref in mission_level_refs or []:
        level_id = ref.get("levelId") or ""
        if level_id and level_id not in level_ids:
            level_ids.append(level_id)

    levelscript_hints = _load_mission_levelscript_dialogs(mission_id, level_ids)
    dialogs_by_level: dict[str, list[str]] = defaultdict(list)
    for hint in levelscript_hints:
        for dialog_id in hint.get("dialogs") or []:
            if dialog_id in dialog_entries_by_key and dialog_id not in dialogs_by_level[hint["levelId"]]:
                dialogs_by_level[hint["levelId"]].append(dialog_id)

    actor_sets = {
        key: set(entry.get("c") or [])
        for key, entry in dialog_entries_by_key.items()
    }
    kind_order = {"sns": 0, "cutscene": 1, "dlg": 2, "black": 3, "remotecomm": 4, "radio": 5, "env": 6, "misc": 7}

    ordered_keys: list[str] = []
    seen: set[str] = set()

    def push(dialog_id: str) -> None:
        if dialog_id in entries_by_key and dialog_id not in seen:
            seen.add(dialog_id)
            ordered_keys.append(dialog_id)

    def resolve_entry_scene_ref(raw_ref: str) -> str:
        candidates = _unique_preserve([
            str(raw_ref or "").strip(),
            *_scene_ref_alias_candidates(raw_ref),
        ])
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in entries_by_key:
                return candidate
            canonical_cutscene = _canonical_cutscene_key(candidate) or ""
            if canonical_cutscene in entries_by_key:
                return canonical_cutscene
        return ""

    script_scene_ref_cache: dict[tuple[str, str], list[str]] = {}

    def levelscript_scene_refs_for_script(level_id: str, script_id) -> list[str]:
        if not level_id or script_id is None:
            return []
        script_stem = str(script_id)
        cache_key = (level_id, script_stem)
        if cache_key in script_scene_ref_cache:
            return script_scene_ref_cache[cache_key]
        hits: list[tuple[int, int, str]] = []
        for file_info in _load_levelscript_binding_data(level_id).get("files") or []:
            if Path(file_info.get("file") or "").stem != script_stem:
                continue
            for record in file_info.get("records") or []:
                record_start = int(record.get("start") or 0)
                for hit in record.get("strings") or []:
                    scene_ref = resolve_entry_scene_ref(hit.get("text") or "")
                    if not scene_ref:
                        continue
                    hits.append((record_start, int(hit.get("offset") or record_start), scene_ref))
        refs = _unique_preserve([scene_ref for _, __, scene_ref in sorted(hits)])
        script_scene_ref_cache[cache_key] = refs
        return refs

    def normalized_script_ids(values) -> list[str]:
        out: list[str] = []
        for value in values or []:
            script_id = value
            if isinstance(value, dict):
                script_id = value.get("scriptId") or value.get("value")
                if isinstance(script_id, dict):
                    script_id = script_id.get("scriptId")
            if script_id is None:
                continue
            script_id_text = str(script_id)
            if script_id_text and script_id_text not in out:
                out.append(script_id_text)
        return out

    def quest_condition_script_scene_refs(quest: dict) -> list[str]:
        refs: list[str] = []
        default_scene_ids = list(quest.get("scenes") or [])
        for anchor in quest.get("objectiveAnchors") or []:
            anchor_scene_ids = list(anchor.get("sceneIds") or default_scene_ids)
            script_ids = normalized_script_ids(anchor.get("scriptIds"))
            for script_id in script_ids:
                for scene_id in anchor_scene_ids:
                    for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                        if scene_ref not in refs:
                            refs.append(scene_ref)
            for leaf in anchor.get("conditionLeaves") or []:
                leaf_scene_ids = list(leaf.get("sceneIds") or anchor_scene_ids)
                for script_id in normalized_script_ids(leaf.get("scriptIds")):
                    for scene_id in leaf_scene_ids:
                        for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                            if scene_ref not in refs:
                                refs.append(scene_ref)
        return refs

    def has_unplaced_prior_levelscript_dialog(level_id: str, dialog_id: str) -> bool:
        dialogs = dialogs_by_level.get(level_id) or []
        if dialog_id not in dialogs:
            return False
        for prior_dialog_id in dialogs[:dialogs.index(dialog_id)]:
            if prior_dialog_id in entries_by_key and prior_dialog_id not in seen:
                return True
        return False

    def push_unplaced_levelscript_dialogs_before(scene_ids, stop_dialog_ids) -> None:
        stop_dialog_ids = set(stop_dialog_ids or [])
        for scene_id in scene_ids or []:
            for dialog_id in dialogs_by_level.get(scene_id) or []:
                if dialog_id in seen:
                    continue
                if dialog_id in stop_dialog_ids:
                    break
                push(dialog_id)
                break

    if mission_flow:
        visited_quest_levels: set[str] = set()
        for quest in mission_flow.get("quests") or []:
            explicit = [dialog_id for dialog_id in (quest.get("dialogs") or []) if dialog_id in entries_by_key]
            explicit_cutscenes = [cutscene_id for cutscene_id in (quest.get("cutscenes") or []) if cutscene_id in entries_by_key]
            explicit_remotecomms = [remote_id for remote_id in (quest.get("remotecomms") or []) if remote_id in entries_by_key]
            explicit_radios = [radio_id for radio_id in (quest.get("radios") or []) if radio_id in entries_by_key]
            for scene_ref in quest_condition_script_scene_refs(quest):
                push(scene_ref)
            if explicit or explicit_cutscenes or explicit_remotecomms:
                push_unplaced_levelscript_dialogs_before(quest.get("scenes") or [], explicit)
            for dialog_id in explicit:
                push(dialog_id)
            for cutscene_id in explicit_cutscenes:
                push(cutscene_id)
            for remote_id in explicit_remotecomms:
                push(remote_id)
            for radio_id in explicit_radios:
                push(radio_id)

            for proxy_id in quest.get("proxies") or []:
                for row in proxy_rows.get(proxy_id, []):
                    if not isinstance(row, dict):
                        continue
                    dialog_id = row.get("dialogId") or ""
                    row_mission = row.get("missionId") or ""
                    if dialog_id and (not row_mission or row_mission == mission_id):
                        push(dialog_id)

            if explicit or explicit_cutscenes or explicit_remotecomms:
                continue

            best_dialog = ""
            best_level = ""
            best_score = -1
            for proxy_id in quest.get("proxies") or []:
                actor_id = str((proxy_info.get(proxy_id) or {}).get("npcNameId") or "")
                for scene_id in quest.get("scenes") or []:
                    for dialog_id in dialogs_by_level.get(scene_id, []):
                        if dialog_id in seen:
                            continue
                        score = 2
                        if actor_id and actor_id in actor_sets.get(dialog_id, set()):
                            score += 4
                        if score > best_score:
                            best_score = score
                            best_dialog = dialog_id
                            best_level = scene_id
            if (
                best_dialog
                and best_score >= 5
                and not has_unplaced_prior_levelscript_dialog(best_level, best_dialog)
            ):
                push(best_dialog)

            for scene_id in quest.get("scenes") or []:
                if not scene_id or scene_id in visited_quest_levels:
                    continue
                visited_quest_levels.add(scene_id)
                dialogs = dialogs_by_level.get(scene_id) or []
                if dialogs and dialogs[0] not in seen:
                    push(dialogs[0])

    for level_id in level_ids:
        for dialog_id in dialogs_by_level.get(level_id, []):
            push(dialog_id)

    for entry in sorted(
        entries_by_key.values(),
        key=lambda e: (
            e.get("s", 10**9),
            kind_order.get(e.get("d"), 99),
            e.get("k") or "",
        ),
    ):
        push(entry["k"])

    return {dialog_id: order for order, dialog_id in enumerate(ordered_keys)}


def build_mission_scene_file_order(
    mission_entries: list[dict],
    mission_flow: dict | None,
) -> dict:
    """Build source-strict scene/file order from MissionRuntimeAsset quest edges.

    This intentionally treats `prevQuestIdList` as a partial order. Sibling
    quests in the same DAG layer share the same broad order bucket; the payload
    keeps them as separate groups instead of pretending the fallback sort is
    authored chronology.
    """
    entries_by_key = {
        entry["k"]: entry
        for entry in mission_entries
        if entry.get("d") in MISSION_SCENE_ENTRY_KINDS and entry.get("k")
    }
    if not entries_by_key or not mission_flow:
        return {}

    quests = [
        quest
        for quest in (mission_flow.get("quests") or [])
        if quest.get("id")
    ]
    if not quests:
        return {}

    quest_by_id = {quest["id"]: quest for quest in quests}

    def resolve_entry_scene_ref(raw_ref: str) -> str:
        candidates = _unique_preserve([
            str(raw_ref or "").strip(),
            *_scene_ref_alias_candidates(raw_ref),
        ])
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in entries_by_key:
                return candidate
            canonical_cutscene = _canonical_cutscene_key(candidate) or ""
            if canonical_cutscene in entries_by_key:
                return canonical_cutscene
        return ""

    def quest_scene_refs(quest: dict) -> list[str]:
        refs: list[str] = []
        for field_name in ("dialogs", "cutscenes", "remotecomms", "radios"):
            for raw_ref in quest.get(field_name) or []:
                resolved = resolve_entry_scene_ref(raw_ref)
                if resolved and resolved not in refs:
                    refs.append(resolved)
        return refs

    depth_by_id: dict[str, int] = {}
    visiting: set[str] = set()
    loops: set[tuple[str, ...]] = set()

    def quest_depth(quest_id: str, stack: tuple[str, ...] = ()) -> int:
        if quest_id in depth_by_id:
            return depth_by_id[quest_id]
        if quest_id in visiting:
            try:
                loop = (*stack[stack.index(quest_id):], quest_id)
            except ValueError:
                loop = (*stack, quest_id)
            loops.add(loop)
            return 0
        quest = quest_by_id.get(quest_id)
        if not quest:
            return 0
        visiting.add(quest_id)
        prev_depths = [
            quest_depth(prev_id, (*stack, quest_id))
            for prev_id in (quest.get("prev") or [])
            if prev_id in quest_by_id
        ]
        visiting.remove(quest_id)
        depth_by_id[quest_id] = (max(prev_depths) + 1) if prev_depths else 0
        return depth_by_id[quest_id]

    for quest in quests:
        quest_depth(quest["id"])

    groups: list[dict] = []
    order_map: dict[str, int] = {}
    scene_to_quests: dict[str, list[str]] = defaultdict(list)
    edges_by_pair: dict[tuple[str, str], dict] = {}
    unresolved_prev: list[dict] = []

    quest_refs_by_id = {
        quest["id"]: quest_scene_refs(quest)
        for quest in quests
    }
    layer_counts = Counter(
        depth_by_id.get(quest["id"], 0)
        for quest in quests
        if quest_refs_by_id.get(quest["id"])
    )

    for quest in sorted(
        quests,
        key=lambda quest: (
            depth_by_id.get(quest["id"], 10**9),
            _quest_sort_key(quest),
        ),
    ):
        quest_id = quest["id"]
        refs = quest_refs_by_id.get(quest_id) or []
        layer = depth_by_id.get(quest_id, 0)
        for local_index, scene_key in enumerate(refs):
            order_map.setdefault(scene_key, layer * 1000 + local_index)
            if quest_id not in scene_to_quests[scene_key]:
                scene_to_quests[scene_key].append(quest_id)
        for prev_id in quest.get("prev") or []:
            if prev_id not in quest_by_id:
                unresolved_prev.append({
                    "questId": quest_id,
                    "prevQuestId": prev_id,
                    "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
                })
                continue
            prev_refs = quest_refs_by_id.get(prev_id) or []
            if not prev_refs or not refs:
                continue
            pair = (prev_refs[-1], refs[0])
            if pair[0] == pair[1]:
                continue
            edge = edges_by_pair.setdefault(pair, {
                "from": pair[0],
                "to": pair[1],
                "kind": "questPrev",
                "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
                "questIds": [],
            })
            for edge_quest_id in (prev_id, quest_id):
                if edge_quest_id and edge_quest_id not in edge["questIds"]:
                    edge["questIds"].append(edge_quest_id)
        if refs:
            groups.append({
                "questId": quest_id,
                "layer": layer,
                "prevQuestIds": list(quest.get("prev") or []),
                "sceneKeys": refs,
                "parallelLayer": layer_counts[layer] > 1,
                "source": "MissionRuntimeAsset.questDic[*]",
            })

    if not groups and not edges_by_pair:
        return {}

    return {
        "source": "MissionRuntimeAsset.questDic[*].prevQuestIdList",
        "mode": "questDagPartialOrder",
        "note": (
            "Layer order comes from explicit quest predecessor edges. Groups in "
            "the same layer are parallel unless another source edge connects them."
        ),
        "groups": groups,
        "edges": sorted(
            edges_by_pair.values(),
            key=lambda edge: (
                order_map.get(edge["from"], 10**9),
                order_map.get(edge["to"], 10**9),
                edge["from"],
                edge["to"],
            ),
        ),
        "sceneQuestRefs": {
            scene_key: quest_ids
            for scene_key, quest_ids in sorted(
                scene_to_quests.items(),
                key=lambda item: (order_map.get(item[0], 10**9), item[0]),
            )
        },
        "orderMap": order_map,
        "unresolvedPrevQuestRefs": unresolved_prev,
        "loops": [
            {"questIds": list(loop)}
            for loop in sorted(loops)
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
