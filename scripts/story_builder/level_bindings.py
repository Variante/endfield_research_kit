from __future__ import annotations

import math
import struct
from functools import lru_cache

from .context import *
from .anime_assets import *
from .scene_graph import *
from .levelscript_binary import (
    LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
    LEVELSCRIPT_NATIVE_HEADER_NAMES,
    LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
    decode_levelscript_binary_file,
    decode_levelscript_encounter_module_target,
    decode_levelscript_record_payload,
    decode_levelscript_task_mission_state_dependencies,
    extract_levelscript_uid_records,
    levelscript_action_map_membership,
    levelscript_native_header_name,
    levelscript_record_semantic_key,
    _extract_levelscript_plain_ascii_strings,
    _extract_levelscript_tagged_ascii_strings,
)

_LEVELDATA_NAMED_TABLES_CACHE: dict[str, list[list[dict]]] = {}
_LEVELSCRIPT_UID_OCCURRENCE_CACHE: dict[tuple[str, ...], dict[str, list[dict]]] = {}
_LEVELTIMELINE_MARKER_CACHE: dict[tuple[tuple[str, ...], tuple[str, ...]], list[dict]] = {}
_LEVELSCRIPT_DIALOG_EXIT_TEXT_PAIR_CACHE: dict[str, list[dict]] = {}
_LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE: dict[str, list[dict]] | None = None
_LEVELSCRIPT_NATIVE_STORY_PLAYBACK_CACHE: dict[str, list[dict]] | None = None
_WORLD_ENTITY_REGISTRY_CACHE: dict[str, dict[tuple[int, int], list[dict]]] = {}
_WORLD_ENTITY_REGISTRY_GLOBAL_SCRIPT_CACHE: dict[str, dict[int, list[dict]]] = {}
_LEVELSCRIPT_BINARY_SUMMARY_CACHE: dict[tuple[str, str], dict] = {}
_LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE: dict[tuple[str, str], dict] = {}
_INTERACTIVE_OBJECT_TEMPLATE_CACHE: dict | None = None
_ENTITY_TRACKING_NATIVE_EVENT_CACHE: dict[tuple[str, str, int], list[dict]] = {}
_WORLD_ENTITY_BRIEF_LOGIC_CACHE: dict[int, list[dict]] | None = None
_HP_SPAWNER_RECORD_CACHE: dict[str, tuple[list[dict], dict[int, str]]] = {}
_LEVELSCRIPT_DIALOG_FILES_BY_LEVEL: dict[
    str,
    tuple[tuple[Path, tuple, bytes, tuple[str, ...]], ...],
] = {}
_LEVELSCRIPT_DIALOGS_BY_LEVEL_MISSION: dict[tuple[str, str], list[dict]] = {}

GLOBAL_SCRIPT_ID_SCALE = 100_000_000

# GameAssembly's recovered MemoryPack union table maps compact ActionHeader tag
# 0x55 with 0x13 subtype members to Beyond.Gameplay.LevelEvent_OnDialogExit.
# The legacy combined pair remains exported for compatibility. Unlike file-
# order proximity, the event itself states that its action chain runs after the
# named dialog exits.
LEVELSCRIPT_DIALOG_EXIT_OPCODE = (0x1355, 0x00)
LEVELSCRIPT_DIALOG_EXIT_TAG = (0x0055, 0x13)


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


def _load_levelscript_dialog_files(level_id: str) -> tuple[
    tuple[Path, tuple, bytes, tuple[str, ...]], ...
]:
    """Read each original LevelScript once and retain exact printable runs."""
    if level_id in _LEVELSCRIPT_DIALOG_FILES_BY_LEVEL:
        return _LEVELSCRIPT_DIALOG_FILES_BY_LEVEL[level_id]
    level_dir = LEVELSCRIPT_DIR / level_id
    files: list[tuple[Path, tuple, bytes, tuple[str, ...]]] = []
    if level_dir.is_dir():
        for path in sorted(level_dir.glob("*.json"), key=_levelscript_file_sort_key):
            try:
                blob = read_bytes_cached(path)
            except OSError:
                continue
            printable = tuple(
                token.decode("ascii", "ignore")
                for token in re.findall(rb"[ -~]{4,}", blob)
            )
            files.append((path, _levelscript_file_sort_key(path), blob, printable))
    result = tuple(files)
    _LEVELSCRIPT_DIALOG_FILES_BY_LEVEL[level_id] = result
    return result


def _load_levelscript_dialogs_for_level(mission_id: str, level_id: str) -> list[dict]:
    cache_key = (level_id, mission_id)
    if cache_key in _LEVELSCRIPT_DIALOGS_BY_LEVEL_MISSION:
        return _LEVELSCRIPT_DIALOGS_BY_LEVEL_MISSION[cache_key]
    prefix = f"dlg_{mission_id}_".encode("ascii")
    dialog_re = re.compile(rf"dlg_{re.escape(mission_id)}_\d+")
    hints: list[dict] = []
    for path, file_order, blob, printable in _load_levelscript_dialog_files(level_id):
        # Keep the former raw membership gate and substring regex semantics.
        if prefix not in blob:
            continue
        dialogs: list[str] = []
        for text in printable:
            for dialog_id in dialog_re.findall(text):
                if dialog_id not in dialogs:
                    dialogs.append(dialog_id)
        if dialogs:
            hints.append({
                "levelId": level_id,
                "file": repo_rel(path),
                "fileOrder": file_order,
                "dialogs": dialogs,
            })
    _LEVELSCRIPT_DIALOGS_BY_LEVEL_MISSION[cache_key] = hints
    return hints


def _load_mission_levelscript_dialogs(mission_id: str, level_ids: list[str]) -> list[dict]:
    cache_key = (mission_id, tuple(dict.fromkeys(level_ids)))
    if cache_key in _MISSION_LEVELSCRIPT_CACHE:
        return _MISSION_LEVELSCRIPT_CACHE[cache_key]

    hints: list[dict] = []
    for level_id in cache_key[1]:
        if not level_id:
            continue
        hints.extend(_load_levelscript_dialogs_for_level(mission_id, level_id))
    _MISSION_LEVELSCRIPT_CACHE[cache_key] = hints
    return hints


# Normalized LevelScript (MemoryPack union tag, concrete member count) -> class.
#
# This table is tied to the installed 2026-07-11 GameAssembly build. Its
# ActionBaseForMemoryPack formatter table was recovered at CodeRegistration
# 0x18b9217d0 and contains contiguous tags 0x0000..0x0520. The member count is
# retained as a payload-shape guard. Compact records must not be keyed by the
# legacy parser's combined `(memberCount << 8) | tag` value.
LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18b9217d0-actionbase-0x0000-0x0520"
)
LEVELSCRIPT_NATIVE_ACTION_NAMES: dict[tuple[int, int], str] = {
    (0x002D, 0x09): "Branch",
    (0x00FF, 0x0B): "IfElseAction",
    (0x0410, 0x0A): "SetInt",
    (0x0310, 0x14): "NarrativeBlackScreenAction",
    (0x031E, 0x0C): "NpcPatrolStart",
    (0x034A, 0x14): "Play3DRadio",
    (0x034B, 0x14): "Play3DRadioAndWait",
    (0x0357, 0x14): "PlayCutsceneAction",
    (0x0358, 0x14): "PlayCutsceneIgnoreCinematicQueue",
    (0x035E, 0x0E): "PlayFmvAction",
    (0x0376, 0x0C): "PreloadCutsceneAction",
    (0x037E, 0x0A): "RaiseCustomLevelEvent",
    (0x0380, 0x0B): "RaiseCustomScriptEvent",
    (0x035A, 0x0F): "PlayDialogAndHideSceneObjectAction",
    (0x0360, 0x0F): "PlayLevelSequenceAction",
    (0x0361, 0x12): "PlayLevelSequenceAndControlSceneObjectsAction",
    (0x0363, 0x0D): "PlayRadio",
    (0x0364, 0x0D): "PlayRadioAndWait",
    (0x0365, 0x11): "PlayRemoteComm",
    (0x049B, 0x13): "StartCutsceneAndControlSceneObjectAction",
    (0x049C, 0x12): "StartCutsceneAndHideSceneObjectAction",
    (0x049D, 0x16): "StartCutsceneAndTeleportAction",
    (0x049E, 0x0F): "StartDialogAction",
    (0x049F, 0x10): "StartDialogAndTeleportAction",
    (0x04A1, 0x10): "StartFmvAndTeleportAction",
    (0x04A5, 0x1B): "StartNarrativeBlackScreenAndTeleport",
    (0x04BD, 0x0C): "SwitchInt",
    (0x0495, 0x09): "Split",
    (0x04F6, 0x08): "WaitForOneFrame",
    (0x04F5, 0x09): "WaitForNpcProxyReady",
    (0x0020, 0x0B): "BlackScreenFadeOut",
    (0x0052, 0x09): "CheckBoolIfTrue",
    (0x04DA, 0x09): "TravelPoleHandoverToCutscene",
}
LEVELSCRIPT_NATIVE_GETTER_MAPPING_ID = (
    "gameassembly-2026-07-11-cr-0x18413bed0-puregetter-0x0000-0x044e"
)
# Only predicate getter shapes currently reached by Story-bearing native
# Split/IfElse/Switch paths are retained here. The member count guards against
# confusing overlapping union-tag spaces or a future changed payload shape.
LEVELSCRIPT_NATIVE_GETTER_NAMES: dict[tuple[int, int], str] = {
    (0x0004, 0x0A): "BooleanCompare",
    (0x001F, 0x0A): "CompareMissionState",
    (0x0049, 0x0A): "FloatNewCompare",
    (0x004E, 0x08): "GetConditionResult",
    (0x0100, 0x09): "GetLevelScriptPropertyGenericBool",
    (0x012F, 0x08): "GetLevelScriptStage",
    (0x013A, 0x08): "GetMissionState",
    (0x0184, 0x08): "GetterInt",
    (0x01AA, 0x0A): "IntCompare",
    (0x01AC, 0x09): "IntEqual",
    (0x01BA, 0x09): "IntGetterRandom",
    (0x01C2, 0x08): "IsEndminGender",
}
LEVELSCRIPT_STORY_KEY_PREFIXES = (
    "dlg_",
    "misc_dlg_",
    "sns_",
    "cutscene_",
    "black_",
    "remotecomm_",
    "radio_",
)
LEVELSCRIPT_MISSIONISH_RE = re.compile(
    r"^(?:(?:[A-Za-z]+\d+(?:l\d+)?m\d+(?:d\d+)?)|"
    r"(?:hidden\d+(?:_[A-Za-z0-9]+)*))"
    r"(?:_q#[A-Za-z0-9_#-]+)?$",
    re.IGNORECASE,
)

_SPAWNER_CONFIG_ID_RE = re.compile(r"_(?P<id>\d+)$")
_SPAWNER_CONFIG_ASCII_TOKEN_RE = re.compile(rb"[A-Za-z][A-Za-z0-9_#-]{3,}")


def build_spawner_config_mission_index(
    mission_ids: set[str] | list[str] | tuple[str, ...],
    *,
    root: Path | None = None,
) -> dict[int, dict]:
    """Resolve authored mission tokens in current SpawnerConfig bytes.

    This is intentionally narrower than a filename heuristic.  The uint64 id
    comes from the config filename, while a mission is accepted only when its
    exact MissionRuntime id occurs as a non-alphanumeric-delimited segment in
    an authored ASCII identifier inside that same original config.  Duplicate
    config ids or multiple mission ids remain ambiguous.
    """
    config_root = root or SPAWNER_CONFIG_DIR
    canonical_ids = {
        str(mission_id).lower(): str(mission_id)
        for mission_id in mission_ids
        if str(mission_id).strip()
    }
    if not config_root.is_dir() or not canonical_ids:
        return {}
    mission_pattern = re.compile(
        rb"(?<![A-Za-z0-9])(?:"
        + b"|".join(
            re.escape(value.encode("ascii"))
            for value in sorted(canonical_ids, key=lambda value: (-len(value), value))
        )
        + rb")(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    rows_by_id: dict[int, list[dict]] = defaultdict(list)
    for path in sorted(config_root.rglob("*.json")):
        match = _SPAWNER_CONFIG_ID_RE.search(path.stem)
        if not match:
            continue
        try:
            data = read_bytes_cached(path)
        except OSError:
            continue
        authored_tokens: list[str] = []
        authored_missions: set[str] = set()
        for token_match in _SPAWNER_CONFIG_ASCII_TOKEN_RE.finditer(data):
            token_bytes = token_match.group()
            matches = list(mission_pattern.finditer(token_bytes))
            if not matches:
                continue
            token = token_bytes.decode("ascii")
            if token not in authored_tokens:
                authored_tokens.append(token)
            for mission_match in matches:
                canonical = canonical_ids.get(
                    mission_match.group().decode("ascii").lower()
                )
                if canonical:
                    authored_missions.add(canonical)
        rows_by_id[int(match.group("id"))].append({
            "levelId": path.parent.name,
            "sourceFile": repo_rel(path),
            "missionIds": sorted(authored_missions),
            "authoredTokens": authored_tokens,
        })

    out: dict[int, dict] = {}
    for spawner_id, rows in rows_by_id.items():
        mission_matches = sorted({
            mission_id
            for row in rows
            for mission_id in row.get("missionIds") or []
        })
        out[spawner_id] = {
            "status": (
                "unique"
                if len(rows) == 1 and len(mission_matches) == 1
                else "ambiguous"
                if mission_matches
                else "no_authored_mission"
            ),
            "spawnerId": spawner_id,
            "missionIds": mission_matches,
            "configs": rows,
        }
    return out


def resolve_dynamic_hp_spawner_context(
    occurrence: dict,
    event_owner: dict,
) -> dict:
    """Resolve one dynamic HP list to its exact spawning producer.

    The accepted chain is deliberately narrow and entirely serialized in one
    current-build LevelScript:

    ``OnSpawnerEntitySpawn`` -> ``ListAddValueEntityPtr`` -> named entity list
    -> ``OnEntityHpChanged`` -> Story playback.

    Duplicate writers, nonconstant spawners/groups, cross-script references,
    and output refs that do not name the producer header all fail closed.
    """
    event_detail = event_owner.get("eventDetail") or {}
    entity_list = event_detail.get("entityListFilter") or {}
    if not isinstance(entity_list, dict):
        return {}
    list_path = str(entity_list.get("path") or "").strip()
    source_file = str(occurrence.get("sourceFile") or "").strip()
    if (
        event_owner.get("status") != "exact_serialized_control_path"
        or event_owner.get("headerName") != "LevelEvent_OnEntityHpChanged"
        or event_detail.get("payloadSchemaStatus")
        != "exact_current_build_memorypack_fields"
        or event_detail.get("payloadShape")
        != "dynamic-entity-list-hp-ratio-event"
        or entity_list.get("paramSource") != 100
        or not list_path
        or not source_file
    ):
        return {}
    source_path = Path(source_file)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if not source_path.is_file():
        return {}
    cache_key = str(source_path.resolve())
    cached = _HP_SPAWNER_RECORD_CACHE.get(cache_key)
    if cached is None:
        data = read_bytes_cached(source_path)
        tagged = _extract_levelscript_tagged_ascii_strings(data)
        plain = _extract_levelscript_plain_ascii_strings(
            data,
            tagged_offsets={int(row.get("offset") or 0) for row in tagged},
        )
        records = extract_levelscript_uid_records(data, tagged, plain)
        _action_map, membership = levelscript_action_map_membership(data, records)
        decoded_records: list[dict] = []
        for index, record in enumerate(records):
            next_start = (
                int(records[index + 1].get("start") or 0)
                if index + 1 < len(records)
                else len(data)
            )
            decoded_records.append({
                "record": record,
                "role": str(membership.get(int(record.get("start") or 0)) or ""),
                "detail": decode_levelscript_record_payload(
                    data,
                    record,
                    next_start=next_start,
                    action_map_role=membership.get(int(record.get("start") or 0)),
                ),
            })
        cached = (decoded_records, membership)
        _HP_SPAWNER_RECORD_CACHE[cache_key] = cached
    decoded_records, _membership = cached

    writers: list[dict] = []
    for decoded in decoded_records:
        record = decoded["record"]
        detail = decoded["detail"]
        list_add = detail.get("listAddValueEntityPtr") or {}
        destination = list_add.get("destinationList") or {}
        value_entity = list_add.get("valueEntity") or {}
        if (
            not decoded["role"].startswith("actionList")
            or detail.get("actionBaseAction") != "ListAddValueEntityPtr"
            or list_add.get("payloadShape")
            != "dynamic-list-and-event-entity-output-exact-eof"
            or destination.get("paramSource") != 100
            or str(destination.get("path") or "") != list_path
            or value_entity.get("paramSource") != 100
            or not str(value_entity.get("path") or "").startswith("$")
            or not isinstance(value_entity.get("sourceHeaderLocalId"), int)
        ):
            continue
        source_header_local = int(value_entity["sourceHeaderLocalId"])
        source_headers = []
        for header in decoded_records:
            header_record = header["record"]
            header_detail = header["detail"]
            native_detail = header_detail.get("nativeEventDetail") or {}
            action_header = header_detail.get("actionHeader") or {}
            if (
                not header["role"].startswith("headerList")
                or header_record.get("localId") != source_header_local
                or native_detail.get("type") != "LevelEvent_OnSpawnerEntitySpawn"
                or native_detail.get("payloadSchemaStatus")
                != "exact_current_build_memorypack_fields"
                or action_header.get("nextId") != record.get("localId")
                or native_detail.get("entityOutputRef")
                != value_entity.get("path")
            ):
                continue
            source_headers.append({
                "record": header_record,
                "role": header["role"],
                "eventDetail": native_detail,
            })
        if len(source_headers) != 1:
            continue
        writers.append({
            "record": record,
            "role": decoded["role"],
            "listAddValueEntityPtr": list_add,
            "sourceHeader": source_headers[0],
        })
    if len(writers) != 1:
        return {}
    writer = writers[0]
    source_event = writer["sourceHeader"]["eventDetail"]
    spawner_id = source_event.get("spawnerFilterId")
    group_key = str(source_event.get("groupKeyFilter") or "")
    if not isinstance(spawner_id, int) or not group_key:
        return {}
    return {
        "status": "exact",
        "levelId": str(occurrence.get("levelId") or ""),
        "scriptId": str(occurrence.get("scriptId") or ""),
        "sourceFile": repo_rel(source_path),
        "entityListPath": list_path,
        "hpHeaderLocalId": event_owner.get("headerLocalId"),
        "hpRatio": event_detail.get("hpRatio"),
        "changedDirectionName": event_detail.get("changedDirectionName"),
        "listAddLocalId": writer["record"].get("localId"),
        "spawnHeaderLocalId": writer["sourceHeader"]["record"].get("localId"),
        "spawnerId": spawner_id,
        "groupKey": group_key,
        "entityTemplateIdFilter": source_event.get("entityTemplateIdFilter"),
        "spawnEventDetail": source_event,
    }


def match_entity_tracking_native_entity_event_context(
    occurrence: dict,
    tracking: dict,
) -> list[dict]:
    """Match a non-script quest target to an exact EntityEvent target.

    ``trackScriptEntity=false`` stores a level-local entity logic id.  Resolve
    that suffix through the current WorldEntityRegistry and require exactly
    one authored global id; only an exact current EntityEventHeader
    ``ScriptEntityPtr`` target in the same level is accepted.  This proves
    navigation context, never objective completion or playback causality.
    """
    if not isinstance(occurrence, dict) or not isinstance(tracking, dict):
        return []
    if (
        str(tracking.get("type") or "") != "EntityTrackingInfo"
        or tracking.get("trackScriptEntity") is not False
        or str(occurrence.get("levelId") or "")
        != str(tracking.get("scene") or "")
    ):
        return []
    local_logic_id = tracking.get("entityLogicId")
    if (
        not isinstance(local_logic_id, int)
        or isinstance(local_logic_id, bool)
        or local_logic_id <= 0
        or tracking.get("scriptId") not in (0, "0", None)
        or tracking.get("entitySlotId") not in (0, "0", None)
    ):
        return []
    level_id = str(tracking.get("scene") or "")
    global _WORLD_ENTITY_BRIEF_LOGIC_CACHE
    registry_path = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    if _WORLD_ENTITY_BRIEF_LOGIC_CACHE is None:
        try:
            with registry_path.open(encoding="utf-8") as stream:
                raw_registry = json.load(stream)
        except (OSError, json.JSONDecodeError):
            raw_registry = {}
        rows_by_local: dict[int, list[dict]] = defaultdict(list)
        brief_infos = (
            raw_registry.get("worldEntityBriefInfos")
            if isinstance(raw_registry, dict)
            else {}
        )
        for raw_logic_id, brief in (
            brief_infos.items() if isinstance(brief_infos, dict) else []
        ):
            try:
                global_logic_id = int(raw_logic_id)
            except (TypeError, ValueError):
                continue
            if global_logic_id <= 0 or not isinstance(brief, dict):
                continue
            rows_by_local[global_logic_id % GLOBAL_SCRIPT_ID_SCALE].append({
                "globalLogicId": global_logic_id,
                "entityType": brief.get("entityType"),
                "entityDetailId": str(brief.get("detailId") or ""),
                "position": brief.get("position"),
                "rotation": brief.get("rotation"),
                "registrySourceFile": repo_rel(registry_path),
            })
        _WORLD_ENTITY_BRIEF_LOGIC_CACHE = dict(rows_by_local)
    registry_candidates = list(
        _WORLD_ENTITY_BRIEF_LOGIC_CACHE.get(local_logic_id) or []
    )
    if len(registry_candidates) != 1:
        return []
    registry_resolution = registry_candidates[0]
    expected_global_logic_id = int(registry_resolution["globalLogicId"])
    matches: list[dict] = []
    for owner in occurrence.get("nativeEventOwners") or []:
        if (
            not isinstance(owner, dict)
            or owner.get("status") != "exact_serialized_control_path"
            or owner.get("headerName") != "EntityEvent_OnSavePropertyChanged"
        ):
            continue
        detail = owner.get("eventDetail") or {}
        target = detail.get("targetEntity") or {}
        global_logic_id = target.get("logicId")
        if (
            detail.get("type") != "EntityEvent_OnSavePropertyChanged"
            or detail.get("payloadSchemaStatus")
            != "exact_current_build_memorypack_fields"
            or detail.get("targetEntityListPresent") is not False
            or detail.get("targetEntityListOutputPresent") is not False
            or detail.get("serverExchange") is not False
            or detail.get("serializedMissionOrQuestId") is not False
            or not isinstance(global_logic_id, int)
            or target.get("useSlotId")
            or global_logic_id != expected_global_logic_id
        ):
            continue
        matches.append({
            "status": "exact_tracked_global_entity_context",
            "levelId": level_id,
            "trackedLocalLogicId": local_logic_id,
            "targetGlobalLogicId": global_logic_id,
            "worldEntityBrief": registry_resolution,
            "propertyKey": detail.get("propertyKeyFilter"),
            "eventOwner": owner,
            "sourceFile": str(occurrence.get("sourceFile") or ""),
            "scriptId": str(occurrence.get("scriptId") or ""),
            "registrySourceFile": repo_rel(registry_path),
        })
    return matches if len(matches) == 1 else []

# Shared semantic classes for reports and the Story/Mission join. These are
# native formatter names above, not filename-shape guesses.
LEVELSCRIPT_OPCODE_TABLE: dict[tuple[int, int], str] = {
    (0x002D, 0x09): "sequence",
    (0x00FF, 0x0B): "branch",
    (0x0310, 0x14): "play_black",
    (0x031E, 0x0C): "npc_patrol_control",
    (0x034A, 0x14): "play_radio",
    (0x034B, 0x14): "play_radio",
    (0x0357, 0x14): "play_cutscene",
    (0x0358, 0x14): "play_cutscene",
    (0x035E, 0x0E): "play_fmv",
    (0x0376, 0x0C): "preload_cutscene",
    (0x037E, 0x0A): "raise_custom_event",
    (0x0380, 0x0B): "raise_custom_event",
    (0x035A, 0x0F): "play_dialog",
    (0x0360, 0x0F): "play_levelseq",
    (0x0361, 0x12): "play_levelseq",
    (0x0363, 0x0D): "play_radio",
    (0x0364, 0x0D): "play_radio",
    (0x0365, 0x11): "play_remotecomm",
    (0x049B, 0x13): "play_cutscene",
    (0x049C, 0x12): "play_cutscene",
    (0x049D, 0x16): "play_cutscene",
    (0x049E, 0x0F): "play_dialog",
    (0x049F, 0x10): "play_dialog",
    (0x04A1, 0x10): "play_fmv",
    (0x04A5, 0x1B): "play_black",
    (0x04BD, 0x0C): "branch",
    (0x0495, 0x09): "branch",
    (0x04F6, 0x08): "control_wait",
    (0x04F5, 0x09): "control_wait_npc_proxy",
    (0x0020, 0x0B): "presentation_fade",
    (0x0052, 0x09): "gate",
    (0x04DA, 0x09): "play_cutscene",
    (0x0016, 0x09): "set_state",
    (0x0015, 0x09): "set_state",
    (0x0070, 0x13): "set_state",
    (0x0450, 0x0f): "show_guide",
}

_LEVELSCRIPT_BLACK_LINE_ID_RE = re.compile(r"^black_.+_\d{3,}$", re.IGNORECASE)


def levelscript_native_action_name(record: dict) -> str:
    return LEVELSCRIPT_NATIVE_ACTION_NAMES.get(
        levelscript_record_semantic_key(record),
        "",
    )


def match_levelscript_native_black_record(
    record: dict,
    black_line_owner: dict[str, str],
) -> dict | None:
    """Resolve one typed native black action through exact TextTable line ids.

    The action payload stores black-screen line ids rather than a conversation
    key. Every black-looking line id in the record must resolve, and all of
    them must resolve to the same emitted Story conversation.
    """
    pair = levelscript_record_semantic_key(record)
    if LEVELSCRIPT_OPCODE_TABLE.get(pair) != "play_black":
        return None
    line_offsets: dict[str, list[int]] = defaultdict(list)
    unresolved_black_ids: list[str] = []
    story_keys: set[str] = set()
    for field_name in ("strings", "plainStrings"):
        for hit in record.get(field_name) or []:
            text = str(hit.get("text") if isinstance(hit, dict) else hit or "").strip()
            if not _LEVELSCRIPT_BLACK_LINE_ID_RE.fullmatch(text):
                continue
            story_key = str(black_line_owner.get(text) or "")
            if not story_key:
                unresolved_black_ids.append(text)
                continue
            story_keys.add(story_key)
            offset = hit.get("offset") if isinstance(hit, dict) else None
            if isinstance(offset, int) and offset not in line_offsets[text]:
                line_offsets[text].append(offset)
            else:
                line_offsets.setdefault(text, [])
    if unresolved_black_ids or len(story_keys) != 1 or not line_offsets:
        return None
    return {
        "key": next(iter(story_keys)),
        "lineIds": sorted(line_offsets),
        "lineOffsets": {
            line_id: sorted(offsets)
            for line_id, offsets in sorted(line_offsets.items())
        },
    }


def _prepare_levelscript_native_control_context(
    data: bytes,
    records: list[dict],
    membership: dict[int, str],
) -> dict:
    """Prepare immutable per-file facts reused by every Story action lookup."""
    ordered = sorted(records or [], key=lambda row: int(row.get("start") or 0))
    next_starts = {
        int(record.get("start") or 0): (
            int(ordered[index + 1].get("start") or len(data))
            if index + 1 < len(ordered)
            else len(data)
        )
        for index, record in enumerate(ordered)
    }
    action_buckets: dict[int, list[dict]] = defaultdict(list)
    getter_buckets: dict[int, list[dict]] = defaultdict(list)
    for record in ordered:
        local_id = record.get("localId")
        role = str(membership.get(int(record.get("start") or 0)) or "")
        if isinstance(local_id, int) and role.startswith("actionList#"):
            action_buckets[local_id].append(record)
        elif isinstance(local_id, int) and role.startswith("getterList#"):
            getter_buckets[local_id].append(record)
    decoded_cache: dict[int, dict] = {}

    def decoded(record: dict) -> dict:
        start = int(record.get("start") or 0)
        if start not in decoded_cache:
            decoded_cache[start] = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_starts.get(start),
                action_map_role=str(membership.get(start) or ""),
            )
        return decoded_cache[start]

    def control_signature(record: dict) -> tuple:
        """Return only binary-decoded fields that affect static traversal."""
        detail = decoded(record)
        return (
            levelscript_record_semantic_key(record),
            record.get("nextId"),
            tuple(_levelscript_record_texts(record)),
            tuple(detail.get("branchSequenceActionLocalIds") or []),
            tuple(detail.get("splitActionLocalIds") or []),
            detail.get("trueActionLocalId"),
            detail.get("falseActionLocalId"),
            tuple(detail.get("switchCaseActionLocalIds") or []),
            tuple(detail.get("switchCaseValues") or []),
            detail.get("switchDefaultActionLocalId"),
        )

    # Authored files can repeat one local-id record byte-for-byte in separate
    # serialized list fragments. Accept the id only when every record has the
    # same typed tag/member count, texts, nextId, and decoded branch targets.
    # Retain every offset so the graph can distinguish this from a physically
    # unique record. Conflicting duplicates still fail closed.
    action_by_local: dict[int, dict] = {}
    equivalent_record_offsets: dict[int, list[int]] = {}
    for local_id, bucket in action_buckets.items():
        signatures = {control_signature(record) for record in bucket}
        if len(signatures) != 1:
            continue
        action_by_local[local_id] = bucket[0]
        if len(bucket) > 1:
            equivalent_record_offsets[local_id] = sorted(
                int(record.get("start") or 0) for record in bucket
            )
    getter_by_local = {
        local_id: bucket[0]
        for local_id, bucket in getter_buckets.items()
        if len(bucket) == 1
    }
    return {
        "ordered": ordered,
        "actionBuckets": dict(action_buckets),
        "actionByLocal": action_by_local,
        "getterByLocal": getter_by_local,
        "equivalentRecordOffsets": equivalent_record_offsets,
        "decodedByStart": decoded_cache,
        "nextStarts": next_starts,
    }


def _levelscript_native_control_paths_to_record(
    data: bytes,
    records: list[dict],
    membership: dict[int, str],
    target_record: dict,
    *,
    prepared: dict | None = None,
) -> list[dict]:
    """Return exact ActionHeader/typed-branch paths to one action record.

    Every traversed local id must resolve to exactly one actionList row.  The
    graph uses only authored ``ActionHeader.nextId``, ``ActionBase.nextId``,
    the current-build ordered ``Branch._idList``, ``Split.actions`` list,
    current-build ``IfElseAction`` true/false fields, and current-build
    ``SwitchInt`` case/default lists. It deliberately does not use record
    adjacency or infer a mission owner from an event name/trigger slot. Callers
    scanning one file should reuse the prepared context so typed payloads and
    duplicate-id validation are decoded once rather than once per
    Story-bearing action.
    """
    context = prepared or _prepare_levelscript_native_control_context(
        data,
        records,
        membership,
    )
    ordered = list(context.get("ordered") or [])
    action_buckets = context.get("actionBuckets") or {}
    action_by_local = context.get("actionByLocal") or {}
    getter_by_local = context.get("getterByLocal") or {}
    equivalent_record_offsets = context.get("equivalentRecordOffsets") or {}
    decoded_cache = context.get("decodedByStart") or {}
    next_starts = context.get("nextStarts") or {}
    target_local_id = target_record.get("localId")
    if not isinstance(target_local_id, int):
        return []
    if target_local_id not in action_by_local or target_record not in action_buckets.get(
        target_local_id,
        [],
    ):
        return []

    def decoded(record: dict) -> dict:
        start = int(record.get("start") or 0)
        if start not in decoded_cache:
            decoded_cache[start] = decode_levelscript_record_payload(
                data,
                record,
                next_start=next_starts.get(start),
                action_map_role=str(membership.get(start) or ""),
            )
        return decoded_cache[start]

    def successors(record: dict) -> list[tuple[str, int]]:
        edges: list[tuple[str, int]] = []
        next_id = record.get("nextId")
        if isinstance(next_id, int) and next_id >= 0:
            edges.append(("ActionBase.nextId", next_id))
        pair = levelscript_record_semantic_key(record)
        detail = decoded(record)
        if pair == (0x002D, 0x09):
            for index, local_id in enumerate(
                detail.get("branchSequenceActionLocalIds") or []
            ):
                if isinstance(local_id, int):
                    edges.append((f"Branch.sequence[{index}]", local_id))
        elif pair == (0x0495, 0x09):
            for index, local_id in enumerate(detail.get("splitActionLocalIds") or []):
                if isinstance(local_id, int):
                    edges.append((f"Split.actions[{index}]", local_id))
        elif pair == (0x00FF, 0x0B):
            for field_name, label in (
                ("trueActionLocalId", "IfElseAction.trueAction"),
                ("falseActionLocalId", "IfElseAction.falseAction"),
            ):
                local_id = detail.get(field_name)
                if isinstance(local_id, int):
                    edges.append((label, local_id))
        elif pair == (0x04BD, 0x0C):
            case_ids = detail.get("switchCaseActionLocalIds") or []
            case_values = detail.get("switchCaseValues") or []
            for index, (case_value, local_id) in enumerate(zip(case_values, case_ids)):
                if isinstance(local_id, int) and local_id > 0:
                    edges.append((f"SwitchInt.case[{index}]={case_value}", local_id))
            default_id = detail.get("switchDefaultActionLocalId")
            if isinstance(default_id, int) and default_id > 0:
                edges.append(("SwitchInt.default", default_id))
        return list(dict.fromkeys(edges))

    def compact_step(record: dict, edge: str) -> dict:
        code = int(record.get("code") or 0)
        kind = int(record.get("kind") or 0)
        pair = levelscript_record_semantic_key(record)
        texts = _levelscript_record_texts(record)
        detail = decoded(record)
        predicate: dict = {}
        getter_local_id = None
        if pair == (0x00FF, 0x0B):
            getter_local_id = detail.get("conditionGetterLocalId")
        elif pair == (0x04BD, 0x0C):
            getter_local_id = detail.get("switchValueGetterLocalId")
        if isinstance(getter_local_id, int):
            getter = getter_by_local.get(getter_local_id)
            predicate = {
                "status": "exact_unique_getter" if getter else "unresolved_getter_ref",
                "getterLocalId": getter_local_id,
            }
            if getter:
                getter_pair = levelscript_record_semantic_key(getter)
                getter_detail = decoded(getter)
                predicate.update({
                    "getterName": LEVELSCRIPT_NATIVE_GETTER_NAMES.get(getter_pair, ""),
                    "getterUnionTag": f"0x{getter_pair[0]:04x}",
                    "getterSerializedMemberCount": getter_pair[1],
                    "getterTexts": _levelscript_record_texts(getter)[:8],
                    "nativeMappingId": LEVELSCRIPT_NATIVE_GETTER_MAPPING_ID,
                })
                for detail_kind in (
                    "booleanCompare",
                    "floatNewCompare",
                    "intCompare",
                    "intEqual",
                    "intRandom",
                    "getterInt",
                    "getLevelScriptStage",
                    "getLevelScriptPropertyGenericBool",
                    "isEndminGender",
                ):
                    predicate_detail = getter_detail.get(detail_kind)
                    if predicate_detail:
                        predicate["detailKind"] = detail_kind
                        predicate["detail"] = predicate_detail
                        source_getter_id = predicate_detail.get(
                            "valueAGetterLocalId"
                        )
                        source_getter = getter_by_local.get(source_getter_id)
                        if source_getter:
                            source_pair = levelscript_record_semantic_key(source_getter)
                            predicate["sourceGetter"] = {
                                key: value
                                for key, value in {
                                    "getterLocalId": source_getter_id,
                                    "getterName": LEVELSCRIPT_NATIVE_GETTER_NAMES.get(
                                        source_pair, ""
                                    ),
                                    "getterUnionTag": f"0x{source_pair[0]:04x}",
                                    "getterSerializedMemberCount": source_pair[1],
                                    "getterTexts": _levelscript_record_texts(
                                        source_getter
                                    )[:8],
                                    "getterInt": decoded(source_getter).get(
                                        "getterInt"
                                    ) or {},
                                }.items()
                                if value not in ("", None, [], {})
                            }
                        break
                compare = getter_detail.get("compareMissionState") or {}
                if compare:
                    predicate["compareMissionState"] = compare
                    source_getter_id = compare.get("valueAGetterLocalId")
                    source_getter = getter_by_local.get(source_getter_id)
                    if source_getter:
                        source_pair = levelscript_record_semantic_key(source_getter)
                        source_detail = decoded(source_getter)
                        predicate["sourceGetter"] = {
                            key: value
                            for key, value in {
                                "getterLocalId": source_getter_id,
                                "getterName": LEVELSCRIPT_NATIVE_GETTER_NAMES.get(
                                    source_pair, ""
                                ),
                                "getterUnionTag": f"0x{source_pair[0]:04x}",
                                "getterSerializedMemberCount": source_pair[1],
                                "getMissionState": source_detail.get("getMissionState") or {},
                            }.items()
                            if value not in ("", None, [], {})
                        }
        elif pair in {(0x00FF, 0x0B), (0x04BD, 0x0C)}:
            inline_param = (
                detail.get("conditionParam")
                or detail.get("switchValueParam")
                or {}
            )
            predicate = {
                "status": (
                    "exact_inline_param"
                    if inline_param
                    else "inline_getter_unresolved"
                ),
                "param": inline_param,
                "texts": texts[:8],
                "payloadHexPrefix": detail.get("payloadHexPrefix") or "",
            }

        return {
            key: value
            for key, value in {
                "edge": edge,
                "localId": record.get("localId"),
                "opcode": f"0x{code:04x}/0x{kind:02x}",
                "unionTag": (
                    f"0x{int(record.get('unionTag')):04x}"
                    if isinstance(record.get("unionTag"), int)
                    else ""
                ),
                "serializedMemberCount": record.get("serializedMemberCount"),
                "actionName": LEVELSCRIPT_NATIVE_ACTION_NAMES.get(pair, ""),
                "recordClass": LEVELSCRIPT_OPCODE_TABLE.get(pair, ""),
                "texts": texts[:8],
                "branchPredicate": predicate,
                "equivalentRecordOffsets": equivalent_record_offsets.get(
                    int(record.get("localId"))
                ) if isinstance(record.get("localId"), int) else None,
            }.items()
            if value not in ("", None, [], {})
        }

    paths: list[dict] = []
    seen_paths: set[tuple] = set()
    for header in ordered:
        header_start = int(header.get("start") or 0)
        if not str(membership.get(header_start) or "").startswith("headerList#"):
            continue
        header_detail = decoded(header)
        action_header = header_detail.get("actionHeader")
        if not isinstance(action_header, dict):
            continue
        first_local_id = action_header.get("nextId")
        first = action_by_local.get(first_local_id) if isinstance(first_local_id, int) else None
        if first is None:
            continue
        queue: list[tuple[dict, list[dict], frozenset[int]]] = [(
            first,
            [compact_step(first, "ActionHeader.nextId")],
            frozenset({int(first_local_id)}),
        )]
        while queue and len(paths) < 64:
            current, path, visited = queue.pop(0)
            if current.get("localId") == target_local_id:
                path_signature = tuple(
                    (step.get("edge"), step.get("localId")) for step in path
                )
                signature = (header_start, path_signature)
                if signature in seen_paths:
                    continue
                seen_paths.add(signature)
                code = int(header.get("code") or 0)
                kind = int(header.get("kind") or 0)
                has_equivalent_duplicates = any(
                    len(step.get("equivalentRecordOffsets") or []) > 1
                    for step in path
                )
                paths.append({
                    "status": (
                        "exact_serialized_control_path_equivalent_duplicates"
                        if has_equivalent_duplicates
                        else "exact_serialized_control_path"
                    ),
                    "headerName": levelscript_native_header_name(
                        header,
                        allow_union_tag_fallback=True,
                    ),
                    "headerOpcode": f"0x{code:04x}/0x{kind:02x}",
                    "headerUnionTag": (
                        f"0x{int(header.get('unionTag')):04x}"
                        if isinstance(header.get("unionTag"), int)
                        else ""
                    ),
                    "headerSerializedMemberCount": header.get(
                        "serializedMemberCount"
                    ),
                    "headerLocalId": header.get("localId"),
                    "headerTexts": _levelscript_record_texts(header)[:8],
                    "eventDetail": header_detail.get("nativeEventDetail") or {},
                    "targetLocalId": first_local_id,
                    "triggerSlotIds": list(header_detail.get("triggerSlotIds") or []),
                    "pathLocalIds": [step.get("localId") for step in path],
                    "path": path,
                    "nativeHeaderMappingId": LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID,
                })
                continue
            if len(path) >= 64:
                continue
            for edge, next_local_id in successors(current):
                if next_local_id in visited:
                    continue
                next_record = action_by_local.get(next_local_id)
                if next_record is None:
                    continue
                queue.append((
                    next_record,
                    [*path, compact_step(next_record, edge)],
                    visited | {next_local_id},
                ))
    return paths


def build_levelscript_native_black_action_index(
    black_line_owner: dict[str, str],
) -> dict[str, list[dict]]:
    """Return exact native black-action occurrences grouped by Story key."""
    out: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    if not LEVELSCRIPT_DIR.is_dir() or not black_line_owner:
        return {}
    for level_dir in sorted(path for path in LEVELSCRIPT_DIR.iterdir() if path.is_dir()):
        info = _load_levelscript_binding_data(level_dir.name)
        for file_info in info.get("files") or []:
            source_file = str(file_info.get("file") or "")
            if not source_file:
                continue
            try:
                data = read_bytes_cached(ROOT / source_file)
            except OSError:
                continue
            records = list(file_info.get("records") or [])
            _action_map, membership = levelscript_action_map_membership(data, records)
            control_context: dict | None = None
            for record in records:
                record_start = int(record.get("start") or 0)
                action_map_role = str(membership.get(record_start) or "")
                if not action_map_role.startswith("actionList#"):
                    continue
                matched = match_levelscript_native_black_record(record, black_line_owner)
                if not matched:
                    continue
                signature = (source_file, record_start)
                if signature in seen:
                    continue
                seen.add(signature)
                pair = levelscript_record_semantic_key(record)
                occurrence = {
                    **matched,
                    "levelId": level_dir.name,
                    "scriptId": str(file_info.get("fileStem") or ""),
                    "sourceFile": source_file,
                    "actionMapRole": action_map_role,
                    "recordOffset": record_start,
                    "actionCode": f"0x{int(record.get('code') or 0):04x}",
                    "actionKind": f"0x{int(record.get('kind') or 0):02x}",
                    "unionTag": (
                        f"0x{int(record.get('unionTag')):04x}"
                        if isinstance(record.get("unionTag"), int)
                        else ""
                    ),
                    "serializedMemberCount": record.get("serializedMemberCount"),
                    "localId": record.get("localId"),
                    "nextId": record.get("nextId"),
                    "uid": str(record.get("uid") or ""),
                    "actionName": LEVELSCRIPT_NATIVE_ACTION_NAMES.get(pair, ""),
                    "recordClass": LEVELSCRIPT_OPCODE_TABLE.get(pair, ""),
                    "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
                }
                if control_context is None:
                    control_context = _prepare_levelscript_native_control_context(
                        data,
                        records,
                        membership,
                    )
                control_paths = _levelscript_native_control_paths_to_record(
                    data,
                    records,
                    membership,
                    record,
                    prepared=control_context,
                )
                if control_paths:
                    occurrence["nativeEventOwnerStatus"] = (
                        "exact_serialized_control_path"
                    )
                    occurrence["nativeEventOwners"] = control_paths
                out[matched["key"]].append(occurrence)
    return dict(out)


def classify_levelscript_record(record: dict) -> str:
    """Return the semantic class for a record from
    `_load_levelscript_binding_data`, or `""` if its `(code, kind)` is
    not yet in the opcode table."""
    if not isinstance(record, dict):
        return ""
    return LEVELSCRIPT_OPCODE_TABLE.get(levelscript_record_semantic_key(record), "")


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


def _extract_length_prefixed_ascii_strings(
    data: bytes,
    *,
    min_len: int = 3,
    max_len: int = 120,
    tagged_offsets: set[int] | None = None,
) -> list[dict]:
    """Return plain ``<le32 length><ascii>`` strings in a LevelScript blob.

    LevelScript payload text is often serialized as ``0x04`` tagged strings,
    but property keys used by mission conditions can appear as ordinary
    Unity length-prefixed strings. Keep these hits separate from tagged story
    payloads so existing story-edge recovery does not accidentally promote
    generic/debug strings.
    """
    hits: list[dict] = []
    tagged_offsets = tagged_offsets or set()
    end = len(data) - 4
    i = 0
    while i < end:
        size = int.from_bytes(data[i : i + 4], "little", signed=False)
        if size < min_len or size > max_len or i + 4 + size > len(data):
            i += 1
            continue
        if i > 0 and data[i - 1] == 0x04 and (i - 1) in tagged_offsets:
            i += 4 + size
            continue
        raw = data[i + 4 : i + 4 + size]
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
            "payloadOffset": i + 4,
            "text": text,
        })
        i += 4 + size
    return hits


def _decode_uid_record(data: bytes, uid_off: int, uid: str) -> dict | None:
    if uid_off >= 14:
        start = uid_off - 14
        if start + 32 <= len(data):
            if (
                data[start] == 0xFA
                and data[start + 4] in (0, 1)
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
                        "unionTag": _u16(data, start + 1),
                        "serializedMemberCount": data[start + 3],
                        "dontLog": bool(data[start + 4]),
                        "unionTagEncoding": "memorypack-fa-u16",
                        "localId": local_id,
                        "uid": uid,
                        "nextId": _i32(data, start + 28),
                        "payloadStart": start + 32,
                        "strings": [],
                        "plainStrings": [],
                    }

    if uid_off >= 12:
        start = uid_off - 12
        if start + 30 <= len(data):
            code = _u16(data, start)
            kind = data[start + 2]
            local_id = _u32(data, start + 3)
            if (
                data[start] < 0xFA
                and data[start + 1] <= 0x40
                and kind in (0, 1)
                and local_id <= 0x1000
                and data[start + 7] == 0
                and _u32(data, start + 8) == 8
            ):
                return {
                    "start": start,
                    "layout": "plain",
                    "code": code,
                    "kind": kind,
                    "unionTag": data[start],
                    "serializedMemberCount": data[start + 1],
                    "dontLog": bool(data[start + 2]),
                    "unionTagEncoding": "memorypack-u8",
                    "localId": local_id,
                    "uid": uid,
                    "nextId": _i32(data, start + 26),
                    "payloadStart": start + 30,
                    "strings": [],
                    "plainStrings": [],
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


def _attach_hits_to_records(records: list[dict], hits: list[dict], field: str) -> None:
    if not records or not hits:
        return
    sorted_hits = sorted(hits, key=lambda hit: hit["offset"])
    hit_idx = 0
    for idx, record in enumerate(records):
        next_start = records[idx + 1]["start"] if idx + 1 < len(records) else 10**18
        record.setdefault(field, [])
        while hit_idx < len(sorted_hits) and sorted_hits[hit_idx]["offset"] < record["payloadStart"]:
            hit_idx += 1
        scan_idx = hit_idx
        while scan_idx < len(sorted_hits) and sorted_hits[scan_idx]["offset"] < next_start:
            record[field].append(sorted_hits[scan_idx])
            scan_idx += 1


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
            entry_index = len(entries)
            entry_offset = pos
            key = int.from_bytes(data[pos : pos + 4], "little", signed=False)
            size = int.from_bytes(data[pos + 4 : pos + 8], "little", signed=False)
            pos += 8
            if size <= 0 or size > max_string_len or pos + size > len(data):
                ok = False
                break
            text_offset = pos
            raw = data[pos : pos + size]
            pos += size
            if not _is_printable_ascii(raw):
                ok = False
                break
            entries.append({
                "key": key,
                "text": raw.decode("ascii"),
                "index": entry_index,
                "tableOffset": start,
                "entryOffset": entry_offset,
                "textOffset": text_offset,
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
        data = read_bytes_cached(path)
    except OSError:
        entries: list[dict] = []
    else:
        entries = _choose_best_named_entry_table(data)

    _LEVELDATA_NAMED_TABLE_CACHE[cache_key] = entries
    return entries


def _load_leveldata_named_tables(path: Path) -> list[list[dict]]:
    cache_key = str(path)
    if cache_key in _LEVELDATA_NAMED_TABLES_CACHE:
        return _LEVELDATA_NAMED_TABLES_CACHE[cache_key]

    try:
        data = read_bytes_cached(path)
    except OSError:
        tables: list[list[dict]] = []
    else:
        tables = _extract_named_entry_tables(data)

    _LEVELDATA_NAMED_TABLES_CACHE[cache_key] = tables
    return tables


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
            data = read_bytes_cached(path)
        except OSError:
            continue

        string_hits = _extract_tagged_ascii_strings(data, 0x04)
        plain_string_hits = _extract_length_prefixed_ascii_strings(
            data,
            tagged_offsets={hit["offset"] for hit in string_hits},
        )
        records = _extract_uid_records(data, string_hits)
        _attach_hits_to_records(records, plain_string_hits, "plainStrings")
        if not records and not string_hits and not plain_string_hits:
            continue

        sorted_hits = sorted(string_hits, key=lambda hit: hit["offset"])
        sorted_plain_hits = sorted(plain_string_hits, key=lambda hit: hit["offset"])
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
            "fileStem": path.stem,
            "records": records,
            "stringHits": sorted_hits,
            "plainStringHits": sorted_plain_hits,
        })

    _LEVELSCRIPT_BINDING_CACHE[level_id] = out
    return out


def build_levelscript_action_story_occurrences() -> dict[str, list[dict]]:
    """Return exact tagged Story ids in decoded LevelScript actionList rows."""
    global _LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE
    if _LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE is not None:
        return _LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE
    out: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple] = set()
    if not LEVELSCRIPT_DIR.is_dir():
        _LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE = {}
        return {}

    for level_dir in sorted(path for path in LEVELSCRIPT_DIR.iterdir() if path.is_dir()):
        info = _load_levelscript_binding_data(level_dir.name)
        for file_info in info.get("files") or []:
            source_file = str(file_info.get("file") or "")
            if not source_file:
                continue
            source_missionish_refs: list[dict] = []
            seen_source_refs: set[tuple[str, int | None]] = set()
            for hit_kind, hits in (
                ("tagged", file_info.get("stringHits") or []),
                ("plain", file_info.get("plainStringHits") or []),
            ):
                for hit in hits:
                    if not isinstance(hit, dict):
                        continue
                    text = str(hit.get("text") or "").strip()
                    offset = hit.get("offset")
                    signature = (text, offset if isinstance(offset, int) else None)
                    if not LEVELSCRIPT_MISSIONISH_RE.fullmatch(text) or signature in seen_source_refs:
                        continue
                    seen_source_refs.add(signature)
                    source_missionish_refs.append({
                        "text": text,
                        "offset": offset,
                        "encoding": hit_kind,
                    })
            try:
                data = read_bytes_cached(ROOT / source_file)
            except OSError:
                continue
            records = list(file_info.get("records") or [])
            _action_map, membership = levelscript_action_map_membership(data, records)
            control_context: dict | None = None
            ordered_records = sorted(
                records,
                key=lambda row: int(row.get("start") or 0),
            )
            next_starts = {
                int(record.get("start") or 0): (
                    int(ordered_records[index + 1].get("start") or len(data))
                    if index + 1 < len(ordered_records)
                    else len(data)
                )
                for index, record in enumerate(ordered_records)
            }
            for record in records:
                action_name = levelscript_native_action_name(record)
                record_class = classify_levelscript_record(record)
                record_start = int(record.get("start") or 0)
                action_map_role = str(membership.get(record_start) or "")
                if not action_map_role.startswith("actionList#"):
                    continue
                story_hits: dict[str, list[int]] = defaultdict(list)
                for hit in record.get("strings") or []:
                    story_key = str(
                        hit.get("text") if isinstance(hit, dict) else hit or ""
                    ).strip()
                    if story_key.startswith(LEVELSCRIPT_STORY_KEY_PREFIXES):
                        offset = hit.get("offset") if isinstance(hit, dict) else None
                        if isinstance(offset, int) and offset not in story_hits[story_key]:
                            story_hits[story_key].append(offset)
                fmv_action: dict = {}
                fmv_story_key = ""
                fmv_field_offset = None
                if record_class == "play_fmv":
                    fmv_action = decode_levelscript_record_payload(
                        data,
                        record,
                        next_start=next_starts.get(record_start),
                        action_map_role=action_map_role,
                    ).get("fmvAction") or {}
                    fmv_id = str(fmv_action.get("fmvId") or "")
                    if re.fullmatch(r"cs_video_[A-Za-z0-9][A-Za-z0-9_]*", fmv_id):
                        fmv_story_key = f"cutscene_{fmv_id[len('cs_video_') :]}"
                        raw_offset = fmv_action.get("fieldOffset")
                        try:
                            fmv_field_offset = int(str(raw_offset), 16)
                        except (TypeError, ValueError):
                            fmv_field_offset = None
                        if (
                            isinstance(fmv_field_offset, int)
                            and fmv_field_offset not in story_hits[fmv_story_key]
                        ):
                            story_hits[fmv_story_key].append(fmv_field_offset)
                    # FMV rows are playback evidence only when the exact native
                    # target field decodes. Do not let another incidental
                    # dlg_/cutscene_ literal in a malformed FMV payload become
                    # a Story occurrence through the generic string scanner.
                    if not (
                        fmv_action
                        and fmv_story_key
                        and isinstance(fmv_field_offset, int)
                    ):
                        continue
                    story_hits = {fmv_story_key: [fmv_field_offset]}
                all_story_keys = sorted(story_hits)
                for story_key, string_offsets in story_hits.items():
                    signature = (
                        story_key,
                        source_file,
                        record_start,
                    )
                    if signature in seen:
                        continue
                    seen.add(signature)
                    out[story_key].append({
                        "levelId": level_dir.name,
                        "scriptId": str(file_info.get("fileStem") or ""),
                        "sourceFile": source_file,
                        "actionMapRole": action_map_role,
                        "recordOffset": record_start,
                        "stringOffsets": sorted(string_offsets),
                        "allStoryKeysInRecord": all_story_keys,
                        "sourceMissionishRefs": source_missionish_refs,
                        "actionCode": f"0x{int(record.get('code') or 0):04x}",
                        "actionKind": f"0x{int(record.get('kind') or 0):02x}",
                        "localId": record.get("localId"),
                        "nextId": record.get("nextId"),
                    })
                    if action_name and record_class:
                        out[story_key][-1].update({
                            "actionName": action_name,
                            "recordClass": record_class,
                            "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
                        })
                        if action_name == "Play3DRadio":
                            native_detail = decode_levelscript_record_payload(
                                data,
                                record,
                                next_start=next_starts.get(record_start),
                                action_map_role=action_map_role,
                            ).get("play3DRadio") or {}
                            # Only attach the typed target fields to the Story
                            # occurrence whose id is the exact native radioId.
                            if native_detail.get("radioId") == story_key:
                                out[story_key][-1]["play3DRadio"] = native_detail
                        if (
                            record_class == "play_fmv"
                            and fmv_action
                            and story_key == fmv_story_key
                        ):
                            out[story_key][-1]["fmvAction"] = fmv_action
                        if control_context is None:
                            control_context = _prepare_levelscript_native_control_context(
                                data,
                                records,
                                membership,
                            )
                        control_paths = _levelscript_native_control_paths_to_record(
                            data,
                            records,
                            membership,
                            record,
                            prepared=control_context,
                        )
                        if control_paths:
                            for control_path in control_paths:
                                event_detail = control_path.get("eventDetail") or {}
                                if (
                                    control_path.get("headerName")
                                    == "LevelEvent_OnEncounterBattlePartBegin"
                                    and isinstance(
                                        event_detail.get("levelScriptVariableFilter"),
                                        int,
                                    )
                                ):
                                    runtime_target = (
                                        decode_levelscript_encounter_module_target(
                                            data,
                                            event_detail["levelScriptVariableFilter"],
                                            file_info.get("fileStem") or "",
                                        )
                                    )
                                    if runtime_target:
                                        runtime_target["sourceFile"] = source_file
                                        control_path["runtimeTarget"] = runtime_target
                            out[story_key][-1]["nativeEventOwnerStatus"] = (
                                "exact_serialized_control_path"
                            )
                            out[story_key][-1]["nativeEventOwners"] = control_paths

    _LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE = dict(out)
    return _LEVELSCRIPT_ACTION_STORY_OCCURRENCES_CACHE


def build_levelscript_native_story_playback_index() -> dict[str, list[dict]]:
    """Return the action occurrences with current-build playback type proof.

    This proves an action-record-to-Story edge only. It deliberately does not
    infer which mission or quest causes the containing LevelScript to run.
    """
    global _LEVELSCRIPT_NATIVE_STORY_PLAYBACK_CACHE
    if _LEVELSCRIPT_NATIVE_STORY_PLAYBACK_CACHE is not None:
        return _LEVELSCRIPT_NATIVE_STORY_PLAYBACK_CACHE
    out = {
        story_key: [
            row
            for row in rows
            if row.get("actionName") and row.get("recordClass")
        ]
        for story_key, rows in build_levelscript_action_story_occurrences().items()
    }
    _LEVELSCRIPT_NATIVE_STORY_PLAYBACK_CACHE = {
        story_key: rows
        for story_key, rows in out.items()
        if rows
    }
    return _LEVELSCRIPT_NATIVE_STORY_PLAYBACK_CACHE


def _native_vector_close(
    left: object,
    right: object,
    *,
    tolerance: float = 0.001,
    angular: bool = False,
) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    for axis in ("x", "y", "z"):
        try:
            left_value = float(left.get(axis))
            right_value = float(right.get(axis))
        except (TypeError, ValueError):
            return False
        delta = abs(left_value - right_value)
        if angular:
            delta = min(delta % 360.0, (-delta) % 360.0)
        if delta > tolerance:
            return False
    return True


def _exact_leader_trigger_slot_ids(event_owners: list[dict]) -> list[int]:
    """Return only typed Leader-trigger selectors from current-build payloads.

    ``triggerSlotIds`` is a legacy aggregate collected from the surrounding
    serialized record.  It can include adjacent dictionary values.  The
    decoded native event payload's ``triggerSlotIdFilter`` is the actual
    receiver selector, so geometry context must fail closed without it.
    """
    return sorted({
        int(slot_id)
        for owner in event_owners
        for detail in [owner.get("eventDetail")]
        if isinstance(detail, dict)
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        for slot_id in [detail.get("triggerSlotIdFilter")]
        if isinstance(slot_id, int) and not isinstance(slot_id, bool)
    })


def _levelscript_binary_summary(source_file: str, script_id: str) -> dict:
    """Load one immutable build input once, including path validation.

    Geometry matching calls this for many quest/Story pairs that share the
    same LevelScript. Caching only by resolved path still repeated Windows
    ``is_file`` and ``resolve`` syscalls hundreds of thousands of times.
    """
    lookup_key = (source_file, script_id)
    cached = _LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE.get(lookup_key)
    if cached is not None:
        return cached
    source_path = ROOT / source_file
    if not source_file or not script_id or not source_path.is_file():
        _LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE[lookup_key] = {}
        return {}
    cache_key = (str(source_path.resolve()), script_id)
    if cache_key not in _LEVELSCRIPT_BINARY_SUMMARY_CACHE:
        _LEVELSCRIPT_BINARY_SUMMARY_CACHE[cache_key] = (
            decode_levelscript_binary_file(source_path, script_id)
        )
    summary = _LEVELSCRIPT_BINARY_SUMMARY_CACHE[cache_key]
    _LEVELSCRIPT_BINARY_SUMMARY_SOURCE_CACHE[lookup_key] = summary
    return summary


def match_mission_area_leader_trigger_context(
    occurrence: dict,
    tracking: dict,
) -> list[dict]:
    """Match one quest MissionArea to the exact playback trigger geometry.

    The join is intentionally contextual rather than causal:

    ``MissionRuntime.MissionAreaTrackingInfo`` -> the level-specific
    ``MissionAreaTable`` shape -> a current-build Leader trigger-volume entry
    selected by the exact ``ScriptEvent_OnLeaderEnterTriggerVolume`` control
    path that reaches this Story action.

    Matching positions/shape dimensions are original-data evidence that the
    quest target and playback use the same authored trigger geometry.  It does
    not prove that quest state starts the action or that a server response is
    involved.
    """
    if not isinstance(occurrence, dict) or not isinstance(tracking, dict):
        return []
    if (
        str(tracking.get("type") or "") != "MissionAreaTrackingInfo"
        or str(tracking.get("sourceType") or "") != "missionArea"
        or not tracking.get("missionAreaId")
        or not tracking.get("levelNum")
    ):
        return []
    level_id = str(occurrence.get("levelId") or "")
    if not level_id or level_id != str(tracking.get("scene") or ""):
        return []
    event_owners = [
        owner
        for owner in occurrence.get("nativeEventOwners") or []
        if isinstance(owner, dict)
        and owner.get("status") == "exact_serialized_control_path"
        and owner.get("headerName") == "ScriptEvent_OnLeaderEnterTriggerVolume"
    ]
    trigger_slots = _exact_leader_trigger_slot_ids(event_owners)
    if not event_owners or not trigger_slots:
        return []

    source_file = str(occurrence.get("sourceFile") or "")
    script_id = str(occurrence.get("scriptId") or "")
    summary = _levelscript_binary_summary(source_file, script_id)
    trigger_map = summary.get("triggerVolumesDetails") or {}
    if (
        trigger_map.get("status") != "present"
        or trigger_map.get("parseStatus") != "decoded"
    ):
        return []

    try:
        mission_shape_type = int(tracking.get("shapeType"))
        mission_radius = float(tracking.get("radius") or 0.0)
    except (TypeError, ValueError):
        return []
    matches: list[dict] = []
    for volume in trigger_map.get("volumes") or []:
        if (
            not isinstance(volume, dict)
            or volume.get("triggerVolumeType") != "Leader"
            or volume.get("slotId") not in trigger_slots
        ):
            continue
        for shape in (volume.get("shapeList") or {}).get("shapes") or []:
            if not isinstance(shape, dict):
                continue
            trigger_shape_type = {"Box": 1, "Sphere": 2}.get(
                str(shape.get("shapeType") or "")
            )
            if trigger_shape_type != mission_shape_type:
                continue
            if not _native_vector_close(
                shape.get("position"),
                tracking.get("position"),
            ):
                continue
            if mission_shape_type == 1:
                if not _native_vector_close(shape.get("size"), tracking.get("size")):
                    continue
                if not _native_vector_close(
                    shape.get("rotation"),
                    tracking.get("rotation"),
                    angular=True,
                ):
                    continue
            elif abs(float(shape.get("radius") or 0.0) - mission_radius) > 0.001:
                continue
            matches.append({
                "status": "exact_same_trigger_geometry_context",
                "levelId": level_id,
                "levelNum": str(tracking.get("levelNum") or ""),
                "scriptId": script_id,
                "triggerSlotId": volume.get("slotId"),
                "triggerVolumeType": volume.get("triggerVolumeType"),
                "triggerVolumeOffset": volume.get("offset"),
                "triggerShapeOffset": shape.get("offset"),
                "triggerShape": shape,
                "missionAreaId": str(tracking.get("missionAreaId") or ""),
                "missionAreaShape": {
                    "type": mission_shape_type,
                    "position": tracking.get("position"),
                    "rotation": tracking.get("rotation"),
                    "size": tracking.get("size"),
                    "radius": mission_radius,
                },
                "subDataParentId": tracking.get("subDataParentId"),
                "sourceFile": source_file,
                "missionAreaSourceFile": repo_rel(
                    GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
                ),
                "levelBasicInfoSourceFile": repo_rel(
                    GAMEPLAY_CONFIG_DIR / "LevelBasicInfoTable.json"
                ),
                "nativeEventOwners": event_owners,
            })
    # Multiple exact shapes/slots would prove only an ambiguous spatial set.
    return matches if len(matches) == 1 else []


def match_pos_tracking_leader_trigger_context(
    occurrence: dict,
    tracking: dict,
) -> list[dict]:
    """Match a typed quest pin to an exact Leader trigger-shape center.

    ``PosTrackingInfo`` does not describe the trigger's dimensions and is not
    a causal playback condition.  It can nevertheless prove that a quest and
    a native playback path point at the same authored place when all of the
    following original-data fields agree: level id, exact event-selected
    trigger slot, and shape center (within JSON/f32 round-trip precision).
    Mission-wide ambiguity filtering remains the caller's responsibility.
    """
    if not isinstance(occurrence, dict) or not isinstance(tracking, dict):
        return []
    if (
        str(tracking.get("type") or "") != "PosTrackingInfo"
        or str(tracking.get("sourceType") or "") != "trackingPos"
        or not isinstance(tracking.get("position"), dict)
    ):
        return []
    level_id = str(occurrence.get("levelId") or "")
    if not level_id or level_id != str(tracking.get("scene") or ""):
        return []
    event_owners = [
        owner
        for owner in occurrence.get("nativeEventOwners") or []
        if isinstance(owner, dict)
        and owner.get("status") == "exact_serialized_control_path"
        and owner.get("headerName")
        == "ScriptEvent_OnLeaderEnterTriggerVolume"
    ]
    trigger_slots = _exact_leader_trigger_slot_ids(event_owners)
    if not event_owners or not trigger_slots:
        return []

    source_file = str(occurrence.get("sourceFile") or "")
    script_id = str(occurrence.get("scriptId") or "")
    trigger_map = (
        _levelscript_binary_summary(source_file, script_id).get(
            "triggerVolumesDetails"
        )
        or {}
    )
    if (
        trigger_map.get("status") != "present"
        or trigger_map.get("parseStatus") != "decoded"
    ):
        return []

    matches: list[dict] = []
    for volume in trigger_map.get("volumes") or []:
        if (
            not isinstance(volume, dict)
            or volume.get("triggerVolumeType") != "Leader"
            or volume.get("slotId") not in trigger_slots
        ):
            continue
        for shape in (volume.get("shapeList") or {}).get("shapes") or []:
            if (
                not isinstance(shape, dict)
                or not _native_vector_close(
                    shape.get("position"),
                    tracking.get("position"),
                )
            ):
                continue
            matches.append({
                "status": "exact_same_trigger_center_context",
                "levelId": level_id,
                "scriptId": script_id,
                "triggerSlotId": volume.get("slotId"),
                "triggerVolumeType": volume.get("triggerVolumeType"),
                "triggerVolumeOffset": volume.get("offset"),
                "triggerShapeOffset": shape.get("offset"),
                "triggerShape": shape,
                "trackingPosition": tracking.get("position"),
                "sourceFile": source_file,
                "nativeEventOwners": event_owners,
            })
    return matches if len(matches) == 1 else []


def _load_world_entity_registry_index() -> dict[tuple[int, int], list[dict]]:
    """Index the registry's aligned script-entity id/brief arrays."""
    registry_path = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    cache_key = str(registry_path.resolve())
    if cache_key in _WORLD_ENTITY_REGISTRY_CACHE:
        return _WORLD_ENTITY_REGISTRY_CACHE[cache_key]
    try:
        with registry_path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
    except (OSError, json.JSONDecodeError):
        _WORLD_ENTITY_REGISTRY_CACHE[cache_key] = {}
        return {}

    id_rows = payload.get("m_scriptEntityIdList") or []
    brief_rows = payload.get("m_scriptEntityBriefInfo") or []
    if (
        not isinstance(id_rows, list)
        or not isinstance(brief_rows, list)
        or len(id_rows) != len(brief_rows)
    ):
        _WORLD_ENTITY_REGISTRY_CACHE[cache_key] = {}
        return {}

    out: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for index, (id_row, brief_row) in enumerate(zip(id_rows, brief_rows)):
        if not isinstance(id_row, dict) or not isinstance(brief_row, dict):
            continue
        script_id_global = id_row.get("scriptIdGlobal")
        slot_id = id_row.get("slotId")
        if (
            not isinstance(script_id_global, int)
            or isinstance(script_id_global, bool)
            or script_id_global <= 0
            or not isinstance(slot_id, int)
            or isinstance(slot_id, bool)
        ):
            continue
        local_script_id = script_id_global % GLOBAL_SCRIPT_ID_SCALE
        out[(local_script_id, slot_id)].append({
            "registryIndex": index,
            "scriptIdGlobal": script_id_global,
            "localScriptId": local_script_id,
            "entitySlotId": slot_id,
            "entityType": brief_row.get("entityType"),
            "entityDetailId": str(brief_row.get("detailId") or ""),
            "position": brief_row.get("position"),
            "rotation": brief_row.get("rotation"),
            "registrySourceFile": repo_rel(registry_path),
        })
    compact = dict(out)
    _WORLD_ENTITY_REGISTRY_CACHE[cache_key] = compact
    return compact


def _load_world_entity_registry_global_script_index() -> dict[int, list[dict]]:
    """Index the same validated registry arrays by exact global script id."""
    registry_path = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    cache_key = str(registry_path.resolve())
    if cache_key in _WORLD_ENTITY_REGISTRY_GLOBAL_SCRIPT_CACHE:
        return _WORLD_ENTITY_REGISTRY_GLOBAL_SCRIPT_CACHE[cache_key]
    out: dict[int, list[dict]] = defaultdict(list)
    seen: set[tuple[int, int, int]] = set()
    for rows in _load_world_entity_registry_index().values():
        for row in rows:
            global_script_id = row.get("scriptIdGlobal")
            slot_id = row.get("entitySlotId")
            registry_index = row.get("registryIndex")
            if not all(isinstance(value, int) for value in (
                global_script_id,
                slot_id,
                registry_index,
            )):
                continue
            signature = (global_script_id, slot_id, registry_index)
            if signature in seen:
                continue
            seen.add(signature)
            out[global_script_id].append(dict(row))
    compact = dict(out)
    _WORLD_ENTITY_REGISTRY_GLOBAL_SCRIPT_CACHE[cache_key] = compact
    return compact


def resolve_interactive_condition_script_entity(condition: dict) -> dict:
    """Resolve one typed interactive condition to an exact script entity.

    An equality between an interactive ``logicId`` and a LevelScript filename
    is not sufficient.  Promotion requires the current exported
    ``WorldEntityRegistry`` to classify that same 64-bit value as exactly one
    script id, plus an exact LevelScript file in the condition's authored
    level.  The result proves mission shell context only; it does not prove
    that the condition fires any action in the script.
    """
    if not isinstance(condition, dict):
        return {"status": "invalid"}
    type_name = str(condition.get("type") or "").split(",", 1)[0]
    if type_name.rsplit(".", 1)[-1] != "InteractiveCheckInt":
        return {"status": "unsupported_type"}
    level_id = str(condition.get("mapId") or "").strip()
    logic_id = condition.get("logicId")
    if (
        not level_id
        or condition.get("useSlotId") is not False
        or not isinstance(logic_id, int)
        or isinstance(logic_id, bool)
        or logic_id <= 0
        or logic_id > 0xFFFFFFFFFFFFFFFF
    ):
        return {"status": "invalid"}
    script_path = LEVELSCRIPT_DIR / level_id / f"{logic_id}.json"
    registry_rows = list(
        _load_world_entity_registry_global_script_index().get(logic_id) or []
    )
    candidates = [
        {
            **row,
            "levelId": level_id,
            "scriptId": str(logic_id),
            "levelScriptSourceFile": repo_rel(script_path),
        }
        for row in registry_rows
        if script_path.is_file()
    ]
    if len(candidates) != 1:
        return {
            "status": "ambiguous" if len(candidates) > 1 else "missing",
            "levelId": level_id,
            "scriptId": str(logic_id),
            "logicId": logic_id,
            "candidates": candidates,
        }
    return {"status": "unique", "logicId": logic_id, **candidates[0]}


def resolve_entity_tracking_script(hint: dict) -> dict:
    """Resolve an EntityTrackingInfo local script/slot to one native script.

    The recovered binary computes a global script id from ``sceneId`` and the
    local ``scriptId`` before resolving ``entitySlotId``. We use the exported
    registry as the authoritative mapping and require the resulting global id
    to exist as a LevelScript file in that exact scene. The result proves a
    tracking target, not a quest-to-Story playback edge.
    """
    if (
        not isinstance(hint, dict)
        or str(hint.get("type") or "") != "EntityTrackingInfo"
        or hint.get("trackScriptEntity") is not True
    ):
        return {"status": "not_script_entity"}
    scene_id = str(hint.get("scene") or hint.get("sceneId") or "").strip()
    local_script_id = hint.get("scriptId")
    entity_slot_id = hint.get("entitySlotId")
    entity_logic_id = hint.get("entityLogicId")
    if (
        not scene_id
        or not isinstance(local_script_id, int)
        or isinstance(local_script_id, bool)
        or local_script_id <= 0
        or not isinstance(entity_slot_id, int)
        or isinstance(entity_slot_id, bool)
        or entity_slot_id <= 0
    ):
        return {"status": "invalid"}

    candidates = []
    for row in _load_world_entity_registry_index().get(
        (local_script_id, entity_slot_id),
        [],
    ):
        script_id_global = int(row["scriptIdGlobal"])
        script_path = LEVELSCRIPT_DIR / scene_id / f"{script_id_global}.json"
        if not script_path.is_file():
            continue
        candidates.append({
            **row,
            "entityLogicId": entity_logic_id,
            "levelId": scene_id,
            "scriptId": str(script_id_global),
            "levelScriptSourceFile": repo_rel(script_path),
        })
    if len(candidates) != 1:
        return {
            "status": "ambiguous" if candidates else "missing",
            "levelId": scene_id,
            "localScriptId": local_script_id,
            "entitySlotId": entity_slot_id,
            "entityLogicId": entity_logic_id,
            "candidates": candidates,
        }
    return {"status": "unique", **candidates[0]}


def _read_required_memorypack_string(
    data: bytes,
    offset: int,
    *,
    max_length: int,
) -> tuple[str, int] | None:
    decoded = _read_leveldata_i32(data, offset)
    if decoded is None:
        return None
    length, cursor = decoded
    if length < 0 or length > max_length or cursor + length > len(data):
        return None
    try:
        value = data[cursor : cursor + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return value, cursor + length


def _parse_interactive_object_template_index(data: bytes) -> dict:
    """Decode the exact two-member native InteractiveTable layout."""
    if not data or data[0] != 2:
        return {}
    cursor = 1
    core_count_decoded = _read_leveldata_count(
        data,
        cursor,
        max_count=10_000,
    )
    if core_count_decoded is None or core_count_decoded[0] < 0:
        return {}
    core_count, cursor = core_count_decoded
    core_paths: dict[str, str] = {}
    for _ in range(core_count):
        key_decoded = _read_required_memorypack_string(
            data,
            cursor,
            max_length=512,
        )
        if key_decoded is None:
            return {}
        template_id, cursor = key_decoded
        path_decoded = _read_required_memorypack_string(
            data,
            cursor,
            max_length=2_048,
        )
        if path_decoded is None or template_id in core_paths:
            return {}
        template_path, cursor = path_decoded
        core_paths[template_id] = template_path

    interactive_count_decoded = _read_leveldata_count(
        data,
        cursor,
        max_count=50_000,
    )
    if interactive_count_decoded is None or interactive_count_decoded[0] < 0:
        return {}
    interactive_count, cursor = interactive_count_decoded
    object_to_template: dict[str, str] = {}
    for _ in range(interactive_count):
        object_decoded = _read_required_memorypack_string(
            data,
            cursor,
            max_length=512,
        )
        if object_decoded is None:
            return {}
        object_id, cursor = object_decoded
        if cursor >= len(data) or data[cursor] != 1:
            return {}
        cursor += 1
        template_decoded = _read_required_memorypack_string(
            data,
            cursor,
            max_length=512,
        )
        if template_decoded is None or object_id in object_to_template:
            return {}
        template_id, cursor = template_decoded
        object_to_template[object_id] = template_id
    if cursor != len(data):
        return {}
    if any(template_id not in core_paths for template_id in object_to_template.values()):
        return {}
    return {
        "memberCount": 2,
        "coreTemplateCount": core_count,
        "interactiveDataCount": interactive_count,
        "coreTemplatePaths": core_paths,
        "objectToTemplate": object_to_template,
    }


def _load_interactive_object_template_index() -> dict:
    global _INTERACTIVE_OBJECT_TEMPLATE_CACHE
    if _INTERACTIVE_OBJECT_TEMPLATE_CACHE is not None:
        return _INTERACTIVE_OBJECT_TEMPLATE_CACHE
    source_path = DATA_JSON_DIR / "Interactive" / "InteractiveTable.json"
    mirror_path = (
        EXPORT_ROOT
        / "structured"
        / "Persistent"
        / "Data"
        / "Json"
        / "Interactive"
        / "InteractiveTable.json"
    )
    try:
        data = read_bytes_cached(source_path)
        if mirror_path.is_file() and read_bytes_cached(mirror_path) != data:
            _INTERACTIVE_OBJECT_TEMPLATE_CACHE = {}
            return {}
    except OSError:
        _INTERACTIVE_OBJECT_TEMPLATE_CACHE = {}
        return {}
    parsed = _parse_interactive_object_template_index(data)
    if parsed:
        parsed["sourceFile"] = repo_rel(source_path)
        if mirror_path.is_file():
            parsed["verifiedMirrorFile"] = repo_rel(mirror_path)
    _INTERACTIVE_OBJECT_TEMPLATE_CACHE = parsed
    return parsed


def extract_tracked_interactive_story_targets(resolution: dict) -> list[dict]:
    """Decode exact ``interactives[slot].properties[type_id]`` Story ids.

    This deliberately supports only objects whose exact InteractiveTable
    template is ``int_narrative_mission``. It never scans arbitrary strings:
    the registry detail must resolve through the fully validated native table,
    the exact slot entry must be unique, and the MemoryPack property key/value
    encoding must occur exactly once within that serialized interactive entry.
    """
    if (
        not isinstance(resolution, dict)
        or resolution.get("status") != "unique"
    ):
        return []
    interactive_index = _load_interactive_object_template_index()
    entity_detail_id = str(resolution.get("entityDetailId") or "")
    entity_template_id = str(
        (interactive_index.get("objectToTemplate") or {}).get(entity_detail_id)
        or ""
    )
    if entity_template_id != "int_narrative_mission":
        return []
    level_id = str(resolution.get("levelId") or "")
    script_id = str(resolution.get("scriptId") or "")
    slot_id = resolution.get("entitySlotId")
    if not level_id or not script_id or not isinstance(slot_id, int):
        return []

    info = _load_levelscript_binding_data(level_id)
    file_info = next((
        row
        for row in info.get("files") or []
        if str(row.get("fileStem") or "") == script_id
    ), None)
    if not file_info:
        return []
    source_file = str(file_info.get("file") or "")
    try:
        data = read_bytes_cached(ROOT / source_file)
    except OSError:
        return []

    # The serialized interactive dictionary entry begins with its int slot key
    # followed by the current 25-member InteractiveData object marker.
    entry_marker = int(slot_id).to_bytes(4, "little", signed=True) + b"\x19\x00\x00\x00"
    entry_offsets = _find_exact_bytes_offsets(data, entry_marker)
    if len(entry_offsets) != 1:
        return []
    entry_offset = entry_offsets[0]

    # Bound the entry before the next registry-backed interactive slot or the
    # first decoded UID/action record. This prevents a later getter/task string
    # from being mistaken for a property of the tracked entity.
    end_candidates = [
        int(record.get("start") or 0)
        for record in file_info.get("records") or []
        if int(record.get("start") or 0) > entry_offset
    ]
    script_id_global = int(resolution.get("scriptIdGlobal") or 0)
    for rows in _load_world_entity_registry_index().values():
        for row in rows:
            if int(row.get("scriptIdGlobal") or 0) != script_id_global:
                continue
            other_slot = row.get("entitySlotId")
            if not isinstance(other_slot, int) or other_slot == slot_id:
                continue
            other_marker = other_slot.to_bytes(4, "little", signed=True) + b"\x19\x00\x00\x00"
            end_candidates.extend(
                offset
                for offset in _find_exact_bytes_offsets(data, other_marker)
                if offset > entry_offset
            )
    entry_end = min(end_candidates) if end_candidates else len(data)
    if entry_end <= entry_offset:
        return []

    property_marker = (
        b"\x02\x07\x00\x00\x00type_id"
        b"\x02\x07\x00\x00\x00\x01\x00\x00\x00"
        b"\x02\x00\x00\x00\x00\x00\x00\x00\x00"
    )
    region = data[entry_offset:entry_end]
    relative_offsets = _find_exact_bytes_offsets(region, property_marker)
    if len(relative_offsets) != 1:
        return []
    property_offset = entry_offset + relative_offsets[0]
    length_offset = property_offset + len(property_marker)
    decoded_length = _read_leveldata_i32(data, length_offset)
    if not decoded_length:
        return []
    story_length, story_offset = decoded_length
    if story_length <= 0 or story_length > 256 or story_offset + story_length > entry_end:
        return []
    try:
        story_key = data[story_offset : story_offset + story_length].decode("ascii")
    except UnicodeDecodeError:
        return []
    if not story_key.startswith(LEVELSCRIPT_STORY_KEY_PREFIXES):
        return []
    return [{
        "storyKey": story_key,
        "relation": "entity_tracking_interactive_story_target",
        "levelId": level_id,
        "scriptId": script_id,
        "localScriptId": resolution.get("localScriptId"),
        "entitySlotId": slot_id,
        "entityDetailId": resolution.get("entityDetailId"),
        "entityTemplateId": entity_template_id,
        "entityTemplatePath": str(
            (interactive_index.get("coreTemplatePaths") or {}).get(
                entity_template_id
            )
            or ""
        ),
        "interactiveTableSourceFile": str(
            interactive_index.get("sourceFile") or ""
        ),
        "interactiveTableVerifiedMirrorFile": str(
            interactive_index.get("verifiedMirrorFile") or ""
        ),
        "interactiveEntryOffset": entry_offset,
        "propertyOffset": property_offset,
        "storyOffset": story_offset,
        "propertyKey": "type_id",
        "sourceFile": source_file,
        "registryIndex": resolution.get("registryIndex"),
        "registrySourceFile": resolution.get("registrySourceFile"),
    }]


def build_entity_tracking_native_event_story_context(
    resolution: dict,
    native_story_playback_index: dict[str, list[dict]],
) -> list[dict]:
    """Bridge a tracked entity through an exact native event producer.

    The tracked slot must be the typed ScriptEntityPtr operand of EntityCompare,
    that getter must be the IfElse condition on a header-to-
    RaiseCustomLevelEvent path, and the raised string must have one same-level
    LevelEvent_OnCustomEvent Story target. This proves quest context around a
    client playback route, not an objective completion or server exchange.
    """
    if resolution.get("status") != "unique":
        return []
    level_id = str(resolution.get("levelId") or "")
    script_id = str(resolution.get("scriptId") or "")
    slot_id = resolution.get("entitySlotId")
    if not level_id or not script_id or not isinstance(slot_id, int):
        return []
    cache_key = (level_id, script_id, slot_id)
    if cache_key in _ENTITY_TRACKING_NATIVE_EVENT_CACHE:
        return list(_ENTITY_TRACKING_NATIVE_EVENT_CACHE[cache_key])

    source_file = str(resolution.get("levelScriptSourceFile") or "")
    try:
        data = read_bytes_cached(ROOT / source_file)
    except OSError:
        _ENTITY_TRACKING_NATIVE_EVENT_CACHE[cache_key] = []
        return []
    file_info = next((
        row
        for row in (_load_levelscript_binding_data(level_id).get("files") or [])
        if str(row.get("fileStem") or "") == script_id
    ), None)
    if not file_info:
        _ENTITY_TRACKING_NATIVE_EVENT_CACHE[cache_key] = []
        return []
    records = sorted(
        list(file_info.get("records") or []),
        key=lambda row: int(row.get("start") or 0),
    )
    _action_map, membership = levelscript_action_map_membership(data, records)
    control_context = _prepare_levelscript_native_control_context(
        data,
        records,
        membership,
    )
    next_starts = {
        int(record.get("start") or 0): (
            int(records[index + 1].get("start") or len(data))
            if index + 1 < len(records)
            else len(data)
        )
        for index, record in enumerate(records)
    }

    def role(record: dict) -> str:
        return str(membership.get(int(record.get("start") or 0)) or "")

    action_buckets: dict[int, list[dict]] = defaultdict(list)
    getter_buckets: dict[int, list[dict]] = defaultdict(list)
    for record in records:
        local_id = record.get("localId")
        if not isinstance(local_id, int):
            continue
        if role(record).startswith("actionList#"):
            action_buckets[local_id].append(record)
        elif role(record).startswith("getterList#"):
            getter_buckets[local_id].append(record)
    unique_actions = {
        local_id: bucket[0]
        for local_id, bucket in action_buckets.items()
        if len(bucket) == 1
    }
    unique_getters = {
        local_id: bucket[0]
        for local_id, bucket in getter_buckets.items()
        if len(bucket) == 1
    }

    listener_rows_by_event: dict[str, list[dict]] = defaultdict(list)
    for story_key, occurrences in native_story_playback_index.items():
        for occurrence in occurrences:
            if str(occurrence.get("levelId") or "") != level_id:
                continue
            for owner in occurrence.get("nativeEventOwners") or []:
                if owner.get("headerName") != "LevelEvent_OnCustomEvent":
                    continue
                literals = [
                    str(value)
                    for value in owner.get("headerTexts") or []
                    if value and not str(value).startswith("$")
                ]
                if len(literals) == 1:
                    listener_rows_by_event[literals[0]].append({
                        "storyKey": story_key,
                        "occurrence": occurrence,
                        "owner": owner,
                    })

    matches: list[dict] = []
    for raise_record in records:
        if (
            not role(raise_record).startswith("actionList#")
            or levelscript_record_semantic_key(raise_record) != (0x037E, 0x0A)
        ):
            continue
        control_paths = _levelscript_native_control_paths_to_record(
            data,
            records,
            membership,
            raise_record,
            prepared=control_context,
        )
        for control_path in control_paths:
            if control_path.get("headerName") != "LevelEvent_OnTravelPoleBegin":
                continue
            header_local_id = control_path.get("headerLocalId")
            if not isinstance(header_local_id, int):
                continue
            bridge_rows: list[dict] = []
            for step in control_path.get("path") or []:
                if step.get("actionName") != "IfElseAction":
                    continue
                if_else = unique_actions.get(step.get("localId"))
                if not if_else:
                    continue
                if_else_detail = decode_levelscript_record_payload(
                    data,
                    if_else,
                    next_start=next_starts.get(int(if_else.get("start") or 0)),
                    action_map_role=role(if_else),
                )
                getter_local_id = if_else_detail.get("conditionGetterLocalId")
                getter = unique_getters.get(getter_local_id)
                if not getter:
                    continue
                getter_detail = decode_levelscript_record_payload(
                    data,
                    getter,
                    next_start=next_starts.get(int(getter.get("start") or 0)),
                    action_map_role=role(getter),
                )
                entity_compare = getter_detail.get("entityCompare") or {}
                script_entity = entity_compare.get("scriptEntity") or {}
                property_refs = entity_compare.get("propertyOutputRefs") or []
                if (
                    script_entity.get("slotId") != slot_id
                    or not script_entity.get("useSlotId")
                    or not any(
                        ref.get("localId") == header_local_id
                        and ref.get("field") == "entityOutput"
                        for ref in property_refs
                    )
                ):
                    continue
                tracked_logic_id = resolution.get("entityLogicId")
                if (
                    isinstance(tracked_logic_id, int)
                    and script_entity.get("logicId") != tracked_logic_id
                ):
                    continue
                bridge_rows.append({
                    "ifElseLocalId": if_else.get("localId"),
                    "ifElseOffset": if_else.get("start"),
                    "conditionGetterLocalId": getter_local_id,
                    "conditionGetterOffset": getter.get("start"),
                    "entityCompare": entity_compare,
                })
            if len(bridge_rows) != 1:
                continue
            event_literals = [
                value
                for value in _levelscript_record_texts(raise_record)
                if value and not value.startswith("$")
            ]
            if len(event_literals) != 1:
                continue
            event_key = event_literals[0]
            listeners = listener_rows_by_event.get(event_key) or []
            target_story_keys = {str(row.get("storyKey") or "") for row in listeners}
            target_story_keys.discard("")
            if len(target_story_keys) != 1:
                continue
            matches.append({
                "storyKey": next(iter(target_story_keys)),
                "levelId": level_id,
                "producerScriptId": script_id,
                "producerSourceFile": source_file,
                "trackedEntitySlotId": slot_id,
                "trackedEntityLogicId": resolution.get("entityLogicId"),
                "producerHeaderName": control_path.get("headerName"),
                "producerHeaderLocalId": header_local_id,
                "producerControlPath": control_path,
                "entityCompareBridge": bridge_rows[0],
                "raiseActionLocalId": raise_record.get("localId"),
                "raiseActionOffset": raise_record.get("start"),
                "raisedEventKey": event_key,
                "listenerScriptIds": sorted({
                    str(row["occurrence"].get("scriptId") or "")
                    for row in listeners
                    if row["occurrence"].get("scriptId")
                }),
                "listenerSourceFiles": sorted({
                    str(row["occurrence"].get("sourceFile") or "")
                    for row in listeners
                    if row["occurrence"].get("sourceFile")
                }),
                "listenerEventOwners": [row["owner"] for row in listeners],
            })

    deduped: dict[tuple, dict] = {}
    for match in matches:
        signature = (
            match.get("storyKey"),
            match.get("producerScriptId"),
            match.get("producerHeaderLocalId"),
            match.get("raiseActionLocalId"),
            match.get("raisedEventKey"),
        )
        deduped[signature] = match
    result = list(deduped.values())
    _ENTITY_TRACKING_NATIVE_EVENT_CACHE[cache_key] = result
    return list(result)


def build_levelscript_travel_pole_custom_event_story_routes(
    native_playback_index: dict[str, list[dict]],
) -> list[dict]:
    """Return exact TravelPole -> custom-level-event -> Story routes.

    This is deliberately mission-agnostic.  It proves only a local native
    playback route: a typed TravelPole event entity is compared to one
    slot-backed ScriptEntityPtr, the true branch reaches a typed
    RaiseCustomLevelEvent action, and that exact literal has one same-level
    LevelEvent_OnCustomEvent Story target.  Mission scope is applied later
    through the producer script's complete validated LevelData shell.

    A repeated listener occurrence is allowed when every occurrence resolves
    to the same Story key.  A repeated producer signature, multiple producer
    scripts for one ``(level, event)`` literal, or multiple Story targets all
    fail closed.
    """
    listener_rows_by_event: dict[tuple[str, str], list[dict]] = defaultdict(list)
    listener_levels: set[str] = set()
    for story_key, occurrences in native_playback_index.items():
        for occurrence in occurrences:
            level_id = str(occurrence.get("levelId") or "")
            if not level_id:
                continue
            for owner in occurrence.get("nativeEventOwners") or []:
                if owner.get("headerName") != "LevelEvent_OnCustomEvent":
                    continue
                literals = [
                    str(value)
                    for value in owner.get("headerTexts") or []
                    if value and not str(value).startswith("$")
                ]
                if len(literals) != 1:
                    continue
                listener_levels.add(level_id)
                listener_rows_by_event[(level_id, literals[0])].append({
                    "storyKey": str(story_key or ""),
                    "occurrence": occurrence,
                    "owner": owner,
                })
    if not listener_levels:
        return []

    matches: list[dict] = []
    for level_id in sorted(listener_levels):
        info = _load_levelscript_binding_data(level_id)
        for file_info in info.get("files") or []:
            source_file = str(file_info.get("file") or "")
            script_id = str(file_info.get("fileStem") or "")
            if not source_file or not script_id:
                continue
            try:
                data = read_bytes_cached(ROOT / source_file)
            except OSError:
                continue
            records = sorted(
                list(file_info.get("records") or []),
                key=lambda row: int(row.get("start") or 0),
            )
            if not records:
                continue
            _action_map, membership = levelscript_action_map_membership(
                data,
                records,
            )
            control_context = _prepare_levelscript_native_control_context(
                data,
                records,
                membership,
            )
            next_starts = {
                int(record.get("start") or 0): (
                    int(records[index + 1].get("start") or len(data))
                    if index + 1 < len(records)
                    else len(data)
                )
                for index, record in enumerate(records)
            }

            def role(record: dict) -> str:
                return str(membership.get(int(record.get("start") or 0)) or "")

            action_buckets: dict[int, list[dict]] = defaultdict(list)
            getter_buckets: dict[int, list[dict]] = defaultdict(list)
            for record in records:
                local_id = record.get("localId")
                if not isinstance(local_id, int):
                    continue
                if role(record).startswith("actionList#"):
                    action_buckets[local_id].append(record)
                elif role(record).startswith("getterList#"):
                    getter_buckets[local_id].append(record)
            unique_actions = {
                local_id: bucket[0]
                for local_id, bucket in action_buckets.items()
                if len(bucket) == 1
            }
            unique_getters = {
                local_id: bucket[0]
                for local_id, bucket in getter_buckets.items()
                if len(bucket) == 1
            }

            for raise_record in records:
                if (
                    not role(raise_record).startswith("actionList#")
                    or levelscript_record_semantic_key(raise_record)
                    != (0x037E, 0x0A)
                ):
                    continue
                event_literals = [
                    value
                    for value in _levelscript_record_texts(raise_record)
                    if value and not value.startswith("$")
                ]
                if len(event_literals) != 1:
                    continue
                event_key = event_literals[0]
                listeners = listener_rows_by_event.get((level_id, event_key)) or []
                target_story_keys = {
                    str(row.get("storyKey") or "")
                    for row in listeners
                    if row.get("storyKey")
                }
                if len(target_story_keys) != 1:
                    continue
                for control_path in _levelscript_native_control_paths_to_record(
                    data,
                    records,
                    membership,
                    raise_record,
                    prepared=control_context,
                ):
                    if control_path.get("headerName") != "LevelEvent_OnTravelPoleBegin":
                        continue
                    header_local_id = control_path.get("headerLocalId")
                    if not isinstance(header_local_id, int):
                        continue
                    bridge_rows: list[dict] = []
                    for step in control_path.get("path") or []:
                        if step.get("actionName") != "IfElseAction":
                            continue
                        if_else = unique_actions.get(step.get("localId"))
                        if not if_else:
                            continue
                        if_else_detail = decode_levelscript_record_payload(
                            data,
                            if_else,
                            next_start=next_starts.get(
                                int(if_else.get("start") or 0)
                            ),
                            action_map_role=role(if_else),
                        )
                        getter_local_id = if_else_detail.get(
                            "conditionGetterLocalId"
                        )
                        getter = unique_getters.get(getter_local_id)
                        if not getter:
                            continue
                        getter_detail = decode_levelscript_record_payload(
                            data,
                            getter,
                            next_start=next_starts.get(
                                int(getter.get("start") or 0)
                            ),
                            action_map_role=role(getter),
                        )
                        entity_compare = getter_detail.get("entityCompare") or {}
                        script_entity = entity_compare.get("scriptEntity") or {}
                        property_refs = entity_compare.get("propertyOutputRefs") or []
                        if (
                            not script_entity.get("useSlotId")
                            or not isinstance(script_entity.get("slotId"), int)
                            or not isinstance(script_entity.get("logicId"), int)
                            or not any(
                                ref.get("localId") == header_local_id
                                and ref.get("field") == "entityOutput"
                                for ref in property_refs
                            )
                        ):
                            continue
                        bridge_rows.append({
                            "ifElseLocalId": if_else.get("localId"),
                            "ifElseOffset": if_else.get("start"),
                            "conditionGetterLocalId": getter_local_id,
                            "conditionGetterOffset": getter.get("start"),
                            "entityCompare": entity_compare,
                        })
                    if len(bridge_rows) != 1:
                        continue
                    matches.append({
                        "storyKey": next(iter(target_story_keys)),
                        "levelId": level_id,
                        "producerScriptId": script_id,
                        "producerSourceFile": source_file,
                        "producerHeaderName": control_path.get("headerName"),
                        "producerHeaderLocalId": header_local_id,
                        "producerControlPath": control_path,
                        "entityCompareBridge": bridge_rows[0],
                        "raiseActionLocalId": raise_record.get("localId"),
                        "raiseActionOffset": raise_record.get("start"),
                        "raisedEventKey": event_key,
                        "listenerScriptIds": sorted({
                            str(row["occurrence"].get("scriptId") or "")
                            for row in listeners
                            if row["occurrence"].get("scriptId")
                        }),
                        "listenerSourceFiles": sorted({
                            str(row["occurrence"].get("sourceFile") or "")
                            for row in listeners
                            if row["occurrence"].get("sourceFile")
                        }),
                        "listenerEventOwners": [row["owner"] for row in listeners],
                    })

    deduped: dict[tuple, dict] = {}
    for match in matches:
        signature = (
            match.get("levelId"),
            match.get("producerScriptId"),
            match.get("producerHeaderLocalId"),
            match.get("raiseActionLocalId"),
            match.get("raisedEventKey"),
            match.get("storyKey"),
            tuple(
                (step.get("edge"), step.get("localId"))
                for step in (
                    (match.get("producerControlPath") or {}).get("path") or []
                )
            ),
        )
        deduped[signature] = match
    routes_by_event: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for match in deduped.values():
        routes_by_event[(
            str(match.get("levelId") or ""),
            str(match.get("raisedEventKey") or ""),
        )].append(match)
    return [
        routes[0]
        for _event, routes in sorted(routes_by_event.items())
        if len(routes) == 1
    ]


def decode_levelscript_mission_state_control_gates(
    data: bytes,
    records: list[dict],
    membership: dict[int, str],
    control_path: dict,
) -> list[dict]:
    """Decode exact MissionState predicates traversed by one Story path.

    The current PureGetter union uses ``0x013a/8`` for ``GetMissionState``
    and ``0x001f/10`` for ``CompareMissionState``.  A gate is accepted only
    when the IfElse action, comparison getter, and mission-state getter each
    resolve to one physical record and every subtype payload consumes to EOF.
    The returned branch semantics come from the installed native enum and
    ``CompareMissionState.GetResult`` implementation; they do not infer
    chronology from Story names or record adjacency.
    """
    ordered = sorted(records or [], key=lambda row: int(row.get("start") or 0))
    next_starts = {
        int(record.get("start") or 0): (
            int(ordered[index + 1].get("start") or len(data))
            if index + 1 < len(ordered)
            else len(data)
        )
        for index, record in enumerate(ordered)
    }
    action_buckets: dict[int, list[dict]] = defaultdict(list)
    getter_buckets: dict[int, list[dict]] = defaultdict(list)
    for record in ordered:
        local_id = record.get("localId")
        if not isinstance(local_id, int):
            continue
        role = str(membership.get(int(record.get("start") or 0)) or "")
        if role.startswith("actionList#"):
            action_buckets[local_id].append(record)
        elif role.startswith("getterList#"):
            getter_buckets[local_id].append(record)
    actions = {
        local_id: bucket[0]
        for local_id, bucket in action_buckets.items()
        if len(bucket) == 1
    }
    getters = {
        local_id: bucket[0]
        for local_id, bucket in getter_buckets.items()
        if len(bucket) == 1
    }

    def decoded(record: dict) -> dict:
        start = int(record.get("start") or 0)
        return decode_levelscript_record_payload(
            data,
            record,
            next_start=next_starts.get(start),
            action_map_role=str(membership.get(start) or ""),
        )

    path = list(control_path.get("path") or [])
    gates: list[dict] = []
    for index, step in enumerate(path[:-1]):
        if step.get("actionName") != "IfElseAction":
            continue
        next_step = path[index + 1]
        selected_edge = str(next_step.get("edge") or "")
        if selected_edge not in {
            "IfElseAction.trueAction",
            "IfElseAction.falseAction",
        }:
            continue
        if_else = actions.get(step.get("localId"))
        if not if_else or levelscript_record_semantic_key(if_else) != (0x00FF, 0x0B):
            continue
        if_else_detail = decoded(if_else)
        compare_local_id = if_else_detail.get("conditionGetterLocalId")
        compare_record = getters.get(compare_local_id)
        if not compare_record:
            continue
        compare = decoded(compare_record).get("compareMissionState") or {}
        mission_getter_local_id = compare.get("valueAGetterLocalId")
        mission_record = getters.get(mission_getter_local_id)
        if not mission_record:
            continue
        mission_getter = decoded(mission_record).get("getMissionState") or {}
        comparer_raw = compare.get("comparerRaw")
        state_raw = compare.get("valueBStateRaw")
        if (
            comparer_raw not in {0, 1}
            or state_raw not in {0, 1, 2, 3, 4, 5}
            or not mission_getter.get("missionId")
        ):
            continue
        branch_result = selected_edge == "IfElseAction.trueAction"
        comparison_holds = branch_result
        state_relation = ""
        if state_raw == 3:
            state_equals_completed = (
                comparison_holds if comparer_raw == 0 else not comparison_holds
            )
            state_relation = (
                "completed" if state_equals_completed else "not_completed"
            )
        gates.append({
            "status": "exact_native_mission_state_control_gate",
            "missionId": str(mission_getter["missionId"]),
            "ifElseLocalId": if_else.get("localId"),
            "ifElseOffset": if_else.get("start"),
            "conditionGetterLocalId": compare_local_id,
            "conditionGetterOffset": compare_record.get("start"),
            "missionStateGetterLocalId": mission_getter_local_id,
            "missionStateGetterOffset": mission_record.get("start"),
            "selectedBranch": "true" if branch_result else "false",
            "selectedEdge": selected_edge,
            "comparerRaw": comparer_raw,
            "comparerName": compare.get("comparerName"),
            "expectedStateRaw": state_raw,
            "expectedStateName": compare.get("valueBStateName"),
            "selectedStateRelation": state_relation,
            "nativeMappingId": compare.get("nativeMappingId"),
            "executionSide": "client",
            "networkRole": "reads_synchronized_local_mission_state",
            "serverExchange": False,
        })
    return gates


def build_levelscript_mission_state_story_routes(
    native_playback_index: dict[str, list[dict]],
) -> list[dict]:
    """Return exact native mission-state gates for Story playback paths.

    ``gateMissionIds`` retains every mission whose state directly determines
    the path. ``missionId`` is only a convenience classification for the
    narrower case where every path selects one identical ``not_completed``
    mission. Completed missions earlier in a nested path remain explicit
    prerequisites rather than being discarded or mislabeled as ownership.
    """
    binary_cache: dict[str, tuple[bytes, list[dict], dict[int, str]]] = {}
    routes_by_story: dict[str, list[dict]] = defaultdict(list)
    for story_key, occurrences in native_playback_index.items():
        for occurrence in occurrences:
            source_file = str(occurrence.get("sourceFile") or "")
            if not source_file:
                continue
            if source_file not in binary_cache:
                try:
                    data = read_bytes_cached(ROOT / source_file)
                except OSError:
                    binary_cache[source_file] = (b"", [], {})
                else:
                    records = extract_levelscript_uid_records(data)
                    _action_map, membership = levelscript_action_map_membership(
                        data,
                        records,
                    )
                    binary_cache[source_file] = (data, records, membership)
            data, records, membership = binary_cache[source_file]
            if not records:
                continue
            for owner in occurrence.get("nativeEventOwners") or []:
                if not isinstance(owner, dict) or not str(
                    owner.get("status") or ""
                ).startswith("exact_serialized_control_path"):
                    continue
                gates = decode_levelscript_mission_state_control_gates(
                    data,
                    records,
                    membership,
                    owner,
                )
                if not gates:
                    continue
                active_missions = sorted({
                    str(gate.get("missionId") or "")
                    for gate in gates
                    if gate.get("selectedStateRelation") == "not_completed"
                } - {""})
                routes_by_story[str(story_key or "")].append({
                    "storyKey": str(story_key or ""),
                    "levelId": str(occurrence.get("levelId") or ""),
                    "scriptId": str(occurrence.get("scriptId") or ""),
                    "sourceFile": source_file,
                    "storyAction": str(occurrence.get("actionName") or ""),
                    "storyActionLocalId": occurrence.get("localId"),
                    "storyActionOffset": occurrence.get("recordOffset"),
                    "headerName": str(owner.get("headerName") or ""),
                    "headerLocalId": owner.get("headerLocalId"),
                    "controlPath": owner,
                    "missionStateGates": gates,
                    "notCompletedMissionCandidates": active_missions,
                })

    out: list[dict] = []
    for story_key, paths in sorted(routes_by_story.items()):
        gate_mission_ids = sorted({
            str(gate.get("missionId") or "")
            for path in paths
            for gate in path.get("missionStateGates") or []
            if gate.get("missionId")
        })
        path_candidates = [
            list(path.get("notCompletedMissionCandidates") or [])
            for path in paths
        ]
        candidate_union = sorted({
            mission_id
            for candidates in path_candidates
            for mission_id in candidates
            if mission_id
        })
        unique = bool(path_candidates) and all(
            len(candidates) == 1 for candidates in path_candidates
        ) and len(candidate_union) == 1
        out.append({
            "status": (
                "unique_native_not_completed_mission_gate"
                if unique
                else "mission_state_gate_without_unique_active_mission"
            ),
            "storyKey": story_key,
            "missionId": candidate_union[0] if unique else "",
            "candidateMissionIds": candidate_union,
            "gateMissionIds": gate_mission_ids,
            "gatePathCount": len(paths),
            "gatePaths": paths,
            "nativeMappingId": (
                "gameassembly-2026-07-11-puregetter-mission-state"
            ),
            "executionSide": "client",
            "networkRole": "reads_synchronized_local_mission_state",
            "serverExchange": False,
        })
    return out


def build_levelscript_task_mission_state_story_dependencies(
    native_playback_index: dict[str, list[dict]],
) -> list[dict]:
    """Return same-script task conditions that depend on mission completion.

    A top-level LevelScript task-map condition and a Story playback action in
    the same authored script are useful dependency context, but the task is not
    on the playback action's serialized control path.  These rows therefore
    never establish Story ownership or a mission attachment.
    """
    decoded_by_script: dict[tuple[str, str], list[dict]] = {}
    out: list[dict] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for story_key, occurrences in sorted(native_playback_index.items()):
        for occurrence in occurrences or []:
            if not isinstance(occurrence, dict):
                continue
            source_file = str(occurrence.get("sourceFile") or "")
            script_id = str(occurrence.get("scriptId") or "")
            if not source_file or not script_id or not script_id.isdigit():
                continue
            cache_key = (source_file, script_id)
            if cache_key not in decoded_by_script:
                try:
                    data = read_bytes_cached(ROOT / source_file)
                except OSError:
                    decoded_by_script[cache_key] = []
                else:
                    decoded_by_script[cache_key] = (
                        decode_levelscript_task_mission_state_dependencies(
                            data,
                            script_id,
                        )
                    )
            for task in decoded_by_script[cache_key]:
                condition = task.get("condition") or {}
                mission_id = str(condition.get("missionId") or "")
                if (
                    condition.get("nativeMappingId")
                    != LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID
                    or condition.get("type") != "CheckMissionState"
                    or condition.get("conditionUnionTag") != "0x0067"
                    or condition.get("serializedMemberCount") != 7
                    or condition.get("comparerRaw") != 0
                    or condition.get("comparerName") != "Equal"
                    or condition.get("targetMissionStateRaw") != 3
                    or condition.get("targetMissionStateName") != "Completed"
                    or not mission_id
                ):
                    continue
                signature = (
                    str(story_key or ""),
                    mission_id,
                    source_file,
                    str(task.get("taskKey") or ""),
                    str(task.get("conditionKey") or ""),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                out.append({
                    "status": "exact_same_script_task_mission_state_dependency",
                    "storyKey": str(story_key or ""),
                    "missionId": mission_id,
                    "levelId": str(occurrence.get("levelId") or ""),
                    "scriptId": script_id,
                    "sourceFile": source_file,
                    "storyAction": str(occurrence.get("actionName") or ""),
                    "storyActionLocalId": occurrence.get("localId"),
                    "storyActionOffset": occurrence.get("recordOffset"),
                    "taskKey": str(task.get("taskKey") or ""),
                    "conditionKey": str(task.get("conditionKey") or ""),
                    "taskEntryOffset": task.get("taskEntryOffset"),
                    "taskEntryOffsetHex": str(
                        task.get("taskEntryOffsetHex") or ""
                    ),
                    "conditionOffset": condition.get("conditionOffset"),
                    "conditionOffsetHex": str(
                        condition.get("conditionOffsetHex") or ""
                    ),
                    "predicate": (
                        f"{mission_id} Equal Completed"
                    ),
                    "condition": copy.deepcopy(condition),
                    "task": copy.deepcopy(task),
                    "nativeMappingId": LEVELSCRIPT_TASK_MISSION_STATE_MAPPING_ID,
                    "sameScriptOnly": True,
                    "controlPathLinked": False,
                    "storyBinding": False,
                    "ownership": False,
                    "dependencyOnly": True,
                    "executionSide": "client",
                    "networkRole": "reads_synchronized_local_mission_state",
                    "serverExchange": False,
                    "clientRequest": False,
                    "expectedClientReply": False,
                })
    return out


def build_levelscript_custom_event_story_producer_routes(
    native_playback_index: dict[str, list[dict]],
) -> list[dict]:
    """Return exact serialized custom-event producer -> Story listener routes.

    This is local runtime causality, not mission ownership.  A producer is
    accepted only when the current ActionBase formatter identifies a typed
    ``RaiseCustomLevelEvent`` or ``RaiseCustomScriptEvent`` action, its literal
    event key matches a typed custom-event playback header, and the listener
    resolves to one Story key.  Script-event producers additionally require an
    exactly decoded current-script or constant-script receiver.
    """
    level_listeners: dict[tuple[str, str], list[dict]] = defaultdict(list)
    script_listeners: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    listener_levels: set[str] = set()
    for story_key, occurrences in native_playback_index.items():
        for occurrence in occurrences:
            if not isinstance(occurrence, dict):
                continue
            level_id = str(occurrence.get("levelId") or "")
            listener_script_id = str(occurrence.get("scriptId") or "")
            if not level_id:
                continue
            for owner in occurrence.get("nativeEventOwners") or []:
                if (
                    not isinstance(owner, dict)
                    or owner.get("status") != "exact_serialized_control_path"
                ):
                    continue
                header_name = str(owner.get("headerName") or "")
                if header_name not in {
                    "LevelEvent_OnCustomEvent",
                    "ScriptEvent_OnCustomEvent",
                }:
                    continue
                event_detail = owner.get("eventDetail") or {}
                if (
                    event_detail.get("type") != header_name
                    or event_detail.get("payloadSchemaStatus")
                    != "exact_current_build_memorypack_fields"
                ):
                    continue
                event_key = str(event_detail.get("eventKey") or "").strip()
                if not event_key or event_key.startswith("$"):
                    continue
                row = {
                    "storyKey": str(story_key or ""),
                    "occurrence": occurrence,
                    "owner": owner,
                    "listenerHeaderName": header_name,
                    "listenerScriptId": listener_script_id,
                }
                listener_levels.add(level_id)
                if header_name == "LevelEvent_OnCustomEvent":
                    level_listeners[(level_id, event_key)].append(row)
                elif listener_script_id:
                    script_listeners[(
                        level_id,
                        listener_script_id,
                        event_key,
                    )].append(row)
    if not listener_levels:
        return []

    matches: list[dict] = []
    for level_id in sorted(listener_levels):
        info = _load_levelscript_binding_data(level_id)
        for file_info in info.get("files") or []:
            producer_source_file = str(file_info.get("file") or "")
            producer_script_id = str(file_info.get("fileStem") or "")
            if not producer_source_file or not producer_script_id:
                continue
            try:
                data = read_bytes_cached(ROOT / producer_source_file)
            except OSError:
                continue
            records = sorted(
                list(file_info.get("records") or []),
                key=lambda row: int(row.get("start") or 0),
            )
            if not records:
                continue
            _action_map, membership = levelscript_action_map_membership(data, records)
            control_context = _prepare_levelscript_native_control_context(
                data,
                records,
                membership,
            )
            for index, record in enumerate(records):
                pair = levelscript_record_semantic_key(record)
                if pair not in {(0x037E, 0x0A), (0x0380, 0x0B)}:
                    continue
                record_start = int(record.get("start") or 0)
                role = str(membership.get(record_start) or "")
                if not role.startswith("actionList#"):
                    continue
                next_start = (
                    int(records[index + 1].get("start") or len(data))
                    if index + 1 < len(records)
                    else len(data)
                )
                receiver_mode = "level"
                target_script_id = ""
                if pair == (0x037E, 0x0A):
                    event_literals = [
                        text
                        for text in _levelscript_record_texts(record)
                        if text and not text.startswith("$")
                    ]
                    if len(event_literals) != 1:
                        continue
                    event_key = event_literals[0]
                    listeners = level_listeners.get((level_id, event_key)) or []
                else:
                    detail = decode_levelscript_record_payload(
                        data,
                        record,
                        next_start=next_start,
                        action_map_role=role,
                    ).get("raiseCustomScriptEvent") or {}
                    event_key = str(detail.get("eventKey") or "")
                    receiver_mode = str(detail.get("receiverMode") or "")
                    if receiver_mode == "current_script":
                        target_script_id = producer_script_id
                    elif receiver_mode == "constant_script":
                        target_script_id = str(detail.get("targetScriptId") or "")
                    else:
                        continue
                    listeners = script_listeners.get((
                        level_id,
                        target_script_id,
                        event_key,
                    )) or []
                target_story_keys = sorted({
                    str(row.get("storyKey") or "")
                    for row in listeners
                    if row.get("storyKey")
                })
                if len(target_story_keys) != 1:
                    continue
                producer_control_paths = _levelscript_native_control_paths_to_record(
                    data,
                    records,
                    membership,
                    record,
                    prepared=control_context,
                )
                matches.append({
                    "status": "exact_serialized_local_producer",
                    "storyKey": target_story_keys[0],
                    "levelId": level_id,
                    "raisedEventKey": event_key,
                    "producerAction": LEVELSCRIPT_NATIVE_ACTION_NAMES.get(pair, ""),
                    "producerActionCode": f"0x{pair[0]:04x}/0x{pair[1]:02x}",
                    "producerActionLocalId": record.get("localId"),
                    "producerActionOffset": record.get("start"),
                    "producerActionMapRole": role,
                    "producerScriptId": producer_script_id,
                    "producerSourceFile": producer_source_file,
                    "producerControlPaths": producer_control_paths,
                    "receiverMode": receiver_mode,
                    "targetScriptId": target_script_id,
                    "listenerHeaderNames": sorted({
                        str(row.get("listenerHeaderName") or "")
                        for row in listeners
                        if row.get("listenerHeaderName")
                    }),
                    "listenerScriptIds": sorted({
                        str(row.get("listenerScriptId") or "")
                        for row in listeners
                        if row.get("listenerScriptId")
                    }),
                    "listenerSourceFiles": sorted({
                        str((row.get("occurrence") or {}).get("sourceFile") or "")
                        for row in listeners
                        if (row.get("occurrence") or {}).get("sourceFile")
                    }),
                    "listenerEventOwners": [row.get("owner") for row in listeners],
                    "listenerRoutes": [
                        {
                            "listenerScriptId": str(
                                row.get("listenerScriptId") or ""
                            ),
                            "listenerSourceFile": str(
                                (row.get("occurrence") or {}).get(
                                    "sourceFile"
                                )
                                or ""
                            ),
                            "listenerPlaybackActionOffset": (
                                row.get("occurrence") or {}
                            ).get("recordOffset"),
                            "listenerEventOwner": row.get("owner"),
                        }
                        for row in listeners
                    ],
                    "nativeMappingId": LEVELSCRIPT_NATIVE_ACTION_MAPPING_ID,
                    "executionSide": "client",
                    "networkRole": "local_levelscript_event_dispatch",
                    "serverExchange": False,
                    "serializedMissionOrQuestId": False,
                })

    deduped: dict[tuple, dict] = {}
    for match in matches:
        signature = (
            match.get("storyKey"),
            match.get("levelId"),
            match.get("producerScriptId"),
            match.get("producerActionOffset"),
            match.get("raisedEventKey"),
            match.get("receiverMode"),
            match.get("targetScriptId"),
        )
        deduped[signature] = match
    return sorted(
        deduped.values(),
        key=lambda row: (
            str(row.get("storyKey") or ""),
            str(row.get("levelId") or ""),
            str(row.get("producerScriptId") or ""),
            int(row.get("producerActionOffset") or 0),
        ),
    )


def build_levelscript_manual_guide_group_story_routes(
    native_playback_index: dict[str, list[dict]],
) -> list[dict]:
    """Return exact manual-guide-start -> guide-complete Story routes.

    The installed-build ActionBase union identifies tag/member-count
    ``0x0304/0x09`` as ``ManuallyStartGuideGroup``.  This join requires one
    exact serialized guide-group literal on that action and the same literal
    on an exact ``LevelEvent_OnGuideGroupComplete`` playback owner.  A guide
    group with multiple producer records or multiple Story targets fails
    closed.  Mission ownership is deliberately applied later through the
    producer script's validated LevelData host.
    """
    listener_rows_by_group: dict[str, list[dict]] = defaultdict(list)
    for story_key, occurrences in native_playback_index.items():
        for occurrence in occurrences:
            for owner in occurrence.get("nativeEventOwners") or []:
                if (
                    owner.get("status") != "exact_serialized_control_path"
                    or owner.get("headerName")
                    != "LevelEvent_OnGuideGroupComplete"
                ):
                    continue
                detail = owner.get("eventDetail") or {}
                guide_id = str(detail.get("guideIdFilter") or "").strip()
                if not guide_id:
                    literals = sorted({
                        str(value).strip()
                        for value in owner.get("headerTexts") or []
                        if str(value).strip().startswith("guide_")
                        and not str(value).strip().startswith("$")
                    })
                    if len(literals) != 1:
                        continue
                    guide_id = literals[0]
                if not guide_id.startswith("guide_"):
                    continue
                listener_rows_by_group[guide_id].append({
                    "storyKey": str(story_key or ""),
                    "occurrence": occurrence,
                    "owner": owner,
                })
    if not listener_rows_by_group or not LEVELSCRIPT_DIR.is_dir():
        return []

    producers_by_group: dict[str, list[dict]] = defaultdict(list)
    target_group_ids = set(listener_rows_by_group)
    for level_dir in sorted(LEVELSCRIPT_DIR.iterdir()):
        if not level_dir.is_dir():
            continue
        level_id = level_dir.name
        info = _load_levelscript_binding_data(level_id)
        for file_info in info.get("files") or []:
            source_file = str(file_info.get("file") or "")
            script_id = str(file_info.get("fileStem") or "")
            if not source_file or not script_id:
                continue
            try:
                data = read_bytes_cached(ROOT / source_file)
            except OSError:
                continue
            records = sorted(
                list(file_info.get("records") or []),
                key=lambda row: int(row.get("start") or 0),
            )
            if not records:
                continue
            _action_map, membership = levelscript_action_map_membership(
                data,
                records,
            )
            next_starts = {
                int(record.get("start") or 0): (
                    int(records[index + 1].get("start") or len(data))
                    if index + 1 < len(records)
                    else len(data)
                )
                for index, record in enumerate(records)
            }
            for record in records:
                start = int(record.get("start") or 0)
                role = str(membership.get(start) or "")
                if (
                    not role.startswith("actionList#")
                    or levelscript_record_semantic_key(record)
                    != (0x0304, 0x09)
                ):
                    continue
                decoded = decode_levelscript_record_payload(
                    data,
                    record,
                    next_start=next_starts.get(start),
                    action_map_role=role,
                )
                guide_id = str(decoded.get("guideId") or "").strip()
                if (
                    decoded.get("actionBaseAction")
                    != "ManuallyStartGuideGroup"
                    or guide_id not in target_group_ids
                ):
                    continue
                producers_by_group[guide_id].append({
                    "levelId": level_id,
                    "producerScriptId": script_id,
                    "producerSourceFile": source_file,
                    "producerActionLocalId": record.get("localId"),
                    "producerActionOffset": record.get("start"),
                    "guideGroupId": guide_id,
                    "nativeAction": "ManuallyStartGuideGroup",
                    "opcode": "0x0304/0x09",
                })

    routes: list[dict] = []
    for guide_id, raw_producers in sorted(producers_by_group.items()):
        deduped_producers = {
            (
                str(row.get("levelId") or ""),
                str(row.get("producerScriptId") or ""),
                row.get("producerActionLocalId"),
                row.get("producerActionOffset"),
            ): row
            for row in raw_producers
        }
        listeners = listener_rows_by_group.get(guide_id) or []
        target_story_keys = {
            str(row.get("storyKey") or "")
            for row in listeners
            if row.get("storyKey")
        }
        if len(deduped_producers) != 1 or len(target_story_keys) != 1:
            continue
        producer = next(iter(deduped_producers.values()))
        routes.append({
            **producer,
            "storyKey": next(iter(target_story_keys)),
            "listenerLevelIds": sorted({
                str(row["occurrence"].get("levelId") or "")
                for row in listeners
                if row["occurrence"].get("levelId")
            }),
            "listenerScriptIds": sorted({
                str(row["occurrence"].get("scriptId") or "")
                for row in listeners
                if row["occurrence"].get("scriptId")
            }),
            "listenerSourceFiles": sorted({
                str(row["occurrence"].get("sourceFile") or "")
                for row in listeners
                if row["occurrence"].get("sourceFile")
            }),
            "listenerEventOwners": [row["owner"] for row in listeners],
        })
    return routes


def select_leveldata_native_event_story_context(
    routes: list[dict],
    authoritative_shell_index: dict[tuple[str, str], dict],
    preexisting_by_mission: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Apply unique producer-shell mission scope to exact native routes.

    Every producer shell must name one mission, and every qualifying route for
    a Story key must agree on that same mission.  ``preexisting_by_mission``
    makes this safe to run after stronger direct/tracked connections: those
    Story keys are omitted instead of gaining a weaker duplicate shell edge.
    """
    candidates_by_story: dict[str, list[dict]] = defaultdict(list)
    for route in routes:
        story_key = str(route.get("storyKey") or "")
        pair = (
            str(route.get("levelId") or ""),
            str(route.get("producerScriptId") or ""),
        )
        shell = authoritative_shell_index.get(pair)
        if (
            not story_key
            or not shell
            or shell.get("status") != "unique"
            or len(shell.get("hostMissionIds") or []) != 1
        ):
            continue
        candidates_by_story[story_key].append({
            **route,
            "missionId": str(shell["hostMissionIds"][0]),
            "levelDataHosts": list(shell.get("hosts") or []),
        })

    selected: list[dict] = []
    preexisting = preexisting_by_mission or {}
    for story_key, candidates in sorted(candidates_by_story.items()):
        mission_ids = {
            str(candidate.get("missionId") or "")
            for candidate in candidates
            if candidate.get("missionId")
        }
        if len(mission_ids) != 1:
            continue
        mission_id = next(iter(mission_ids))
        if story_key in preexisting.get(mission_id, set()):
            continue
        selected.extend(candidates)
    return selected


def _parse_leveldata_mission_host_name(
    filename: str,
    level_id: str,
    mission_runtime_ids: set[str],
) -> str:
    """Return the exact MissionRuntime token authored into a LevelData name.

    Mission-scoped LevelData exports use
    ``<level>_lv_data_sub_(mission_)?<mission>[_v...].json``.  The filename is
    only accepted when its level component matches the LevelScript level and
    its complete token exists in the exported MissionRuntime corpus.
    """
    if not filename.endswith(".json"):
        return ""
    marker = "_lv_data_sub_"
    stem = filename[:-5]
    if marker not in stem:
        return ""
    parsed_level, raw_token = stem.split(marker, 1)
    if parsed_level != level_id:
        return ""
    if raw_token.startswith("mission_"):
        raw_token = raw_token[len("mission_") :]
    raw_token = raw_token.lstrip("_")
    token = re.sub(r"_v[0-9A-Za-z]+$", "", raw_token)
    return token if token in mission_runtime_ids else ""


def _find_exact_bytes_offsets(data: bytes, needle: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while needle and start <= len(data) - len(needle):
        offset = data.find(needle, start)
        if offset < 0:
            break
        offsets.append(offset)
        start = offset + 1
    return offsets


def _read_leveldata_i32(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 4 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 4], "little", signed=True), offset + 4


def _read_leveldata_u64(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset < 0 or offset + 8 > len(data):
        return None
    return int.from_bytes(data[offset : offset + 8], "little", signed=False), offset + 8


def _skip_leveldata_memorypack_string(data: bytes, offset: int) -> int | None:
    decoded = _read_leveldata_i32(data, offset)
    if decoded is None:
        return None
    length, offset = decoded
    if length == -1:
        return offset
    if length < 0 or offset + length > len(data):
        return None
    try:
        data[offset : offset + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return offset + length


def _read_leveldata_count(
    data: bytes,
    offset: int,
    *,
    max_count: int = 100_000,
) -> tuple[int, int] | None:
    decoded = _read_leveldata_i32(data, offset)
    if decoded is None:
        return None
    count, offset = decoded
    if count < -1 or count > max_count:
        return None
    return count, offset


def _read_leveldata_memorypack_string(
    data: bytes,
    offset: int,
    *,
    max_length: int = 512,
) -> tuple[str, int] | None:
    decoded = _read_leveldata_i32(data, offset)
    if decoded is None:
        return None
    length, offset = decoded
    if length == -1:
        return "", offset
    if length < 0 or length > max_length or offset + length > len(data):
        return None
    try:
        value = data[offset : offset + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return value, offset + length


def parse_level_function_area_radio_trigger_zone_entry(
    data: bytes,
    offset: int,
) -> dict | None:
    """Parse one exact LevelFunctionArea RadioTriggerZoneData union row.

    The installed-build MemoryPack union table maps
    ``FunctionAreaSpecificData`` tag 9 to ``RadioTriggerZoneData``. Its wrapper
    serializes seven alphabetically ordered members: three mission ids,
    ``prtsId``, ``radioId``, ``triggerId``, and ``useRadioTriggerOnce``.
    Current authored rows are the sole item in ``specificDatas``; requiring the
    immediately preceding list count to equal one proves the collection frame
    and rejects identical tag/member pairs from unrelated unions.
    """
    if (
        offset < 4
        or data[offset : offset + 2] != b"\x09\x07"
        or int.from_bytes(data[offset - 4 : offset], "little", signed=True) != 1
    ):
        return None
    cursor = offset + 2
    values: list[str] = []
    for _ in range(5):
        decoded = _read_leveldata_memorypack_string(data, cursor)
        if decoded is None:
            return None
        value, cursor = decoded
        values.append(value)
    trigger_decoded = _read_leveldata_u64(data, cursor)
    if trigger_decoded is None:
        return None
    trigger_id, cursor = trigger_decoded
    if trigger_id <= 0 or cursor >= len(data) or data[cursor] not in (0, 1):
        return None
    use_once = bool(data[cursor])
    cursor += 1
    (
        hide_after_mission_id,
        hide_before_mission_id,
        hide_complete_mission_id,
        prts_id,
        radio_id,
    ) = values
    if not radio_id.startswith("radio_"):
        return None
    return {
        "recordOffset": offset,
        "recordEndOffset": cursor,
        "unionTag": 9,
        "serializedMemberCount": 7,
        "specificDataListCount": 1,
        "hideAfterMissionId": hide_after_mission_id,
        "hideBeforeMissionId": hide_before_mission_id,
        "hideCompleteMissionId": hide_complete_mission_id,
        "prtsId": prts_id,
        "radioId": radio_id,
        "triggerId": str(trigger_id),
        "useRadioTriggerOnce": use_once,
    }


def build_level_function_area_radio_trigger_story_contexts(
    available_story_keys: set[str],
    mission_runtime_ids: set[str],
    *,
    leveldata_root: Path = LEVELDATA_DIR,
) -> list[dict]:
    """Recover exact radio playback contexts from typed LevelData zones.

    ``RadioTriggerZoneHandler.OnEnter`` consumes the same serialized object,
    calls ``MissionSystem.GetMissionState`` for its three mission fields, and
    calls ``GameAction.PlayRadio`` with ``radioId``. Rows establish exact
    mission-state playback context, not quest causality or Story ownership.
    """
    rows: list[dict] = []
    if not leveldata_root.exists():
        return rows
    for path in sorted(leveldata_root.rglob("*.json")):
        try:
            data = read_bytes_cached(path)
        except OSError:
            continue
        if not data or data[0] != 0x2B:
            continue
        start = 0
        while True:
            offset = data.find(b"\x09\x07", start)
            if offset < 0:
                break
            start = offset + 1
            row = parse_level_function_area_radio_trigger_zone_entry(data, offset)
            if row is None or row["radioId"] not in available_story_keys:
                continue
            mission_fields = [
                ("hideAfterMissionId", row["hideAfterMissionId"]),
                ("hideBeforeMissionId", row["hideBeforeMissionId"]),
                ("hideCompleteMissionId", row["hideCompleteMissionId"]),
            ]
            nonempty_mission_ids = {
                mission_id for _field, mission_id in mission_fields if mission_id
            }
            if (
                not nonempty_mission_ids
                or not nonempty_mission_ids.issubset(mission_runtime_ids)
            ):
                continue
            roles_by_mission: dict[str, list[str]] = defaultdict(list)
            for field_name, mission_id in mission_fields:
                if mission_id:
                    roles_by_mission[mission_id].append(field_name)
            rows.append({
                **row,
                "levelId": path.parent.name,
                "sourceFile": path.name,
                "sourcePath": str(path),
                "missionStateIds": sorted(roles_by_mission),
                "missionStateRolesById": {
                    mission_id: sorted(field_names)
                    for mission_id, field_names in sorted(roles_by_mission.items())
                },
                "source": (
                    "LevelData/43.member17:LevelFunctionAreaData.specificDatas"
                    "(tag 9, RadioTriggerZoneData/7)"
                ),
                "nativeConsumer": (
                    "RadioTriggerZoneHandler.OnEnter -> "
                    "_GetRadioTriggerMissionState -> MissionSystem.GetMissionState; "
                    "OnEnter -> GameAction.PlayRadio"
                ),
            })
    rows.sort(key=lambda row: (
        str(row.get("radioId") or ""),
        str(row.get("levelId") or ""),
        str(row.get("sourceFile") or ""),
        int(row.get("recordOffset") or 0),
    ))
    return rows


def _read_level_interactive_param_atom_string(
    data: bytes,
    offset: int,
    end_offset: int,
    *,
    max_length: int = 512,
) -> tuple[str | None, int] | None:
    decoded = _read_leveldata_i32(data, offset)
    if decoded is None:
        return None
    length, cursor = decoded
    if length == -1:
        return None, cursor
    if length < 0 or length > max_length or cursor + length > end_offset:
        return None
    try:
        value = data[cursor : cursor + length].decode("utf-8")
    except UnicodeDecodeError:
        return None
    return value, cursor + length


def _parse_level_interactive_param_value(
    data: bytes,
    offset: int,
    end_offset: int,
) -> dict | None:
    """Decode one exact two-member ``ParamValue`` and all of its atoms."""
    if offset >= end_offset or data[offset] != 2:
        return None
    type_decoded = _read_leveldata_i32(data, offset + 1)
    if type_decoded is None:
        return None
    value_type, cursor = type_decoded
    if value_type < 0 or value_type > 64:
        return None
    count_decoded = _read_leveldata_count(data, cursor, max_count=256)
    if count_decoded is None or count_decoded[0] < 0:
        return None
    atom_count, cursor = count_decoded
    atoms: list[dict] = []
    for _ in range(atom_count):
        if cursor >= end_offset or data[cursor] != 2:
            return None
        atom_offset = cursor
        bits_decoded = _read_leveldata_u64(data, cursor + 1)
        if bits_decoded is None:
            return None
        value_bits, cursor = bits_decoded
        string_decoded = _read_level_interactive_param_atom_string(
            data,
            cursor,
            end_offset,
        )
        if string_decoded is None:
            return None
        string_value, cursor = string_decoded
        atoms.append({
            "offset": atom_offset,
            "valueBits": value_bits,
            "stringValue": string_value,
        })
    if cursor > end_offset:
        return None
    return {
        "offset": offset,
        "endOffset": cursor,
        "serializedMemberCount": 2,
        "valueType": value_type,
        "atomCount": atom_count,
        "atoms": atoms,
    }


def _parse_level_interactive_param_map(
    data: bytes,
    offset: int,
    end_offset: int,
) -> dict | None:
    """Decode a complete PropertyKey-to-ParamValue map without string scans."""
    count_decoded = _read_leveldata_count(data, offset, max_count=256)
    if count_decoded is None or count_decoded[0] < 0:
        return None
    entry_count, cursor = count_decoded
    entries: dict[str, dict] = {}
    entry_offsets: dict[str, int] = {}
    for _ in range(entry_count):
        entry_offset = cursor
        if cursor >= end_offset or data[cursor] != 2:
            return None
        key_decoded = _read_required_memorypack_string(
            data,
            cursor + 1,
            max_length=256,
        )
        if key_decoded is None:
            return None
        key, cursor = key_decoded
        if not key or key in entries:
            return None
        value = _parse_level_interactive_param_value(data, cursor, end_offset)
        if value is None:
            return None
        cursor = int(value["endOffset"])
        entries[key] = value
        entry_offsets[key] = entry_offset
    return {
        "offset": offset,
        "endOffset": cursor,
        "entryCount": entry_count,
        "entries": entries,
        "entryOffsets": entry_offsets,
    }


def parse_level_interactive_world_dialog_context(
    data: bytes,
    offset: int,
    end_offset: int,
) -> dict | None:
    """Decode component 94's exact mission/Dialog configuration.

    The installed formatter has 25 members. Its inherited prefix ends 52 bytes
    after the authored detail-id string; the first derived member is
    ``componentProperties``. The accepted narrative component is key 94 and
    must contain exactly the heterogeneous PropertyKey map used by the current
    build: mission and Story strings plus integer ``TYPE=Dialog(1)``.
    """
    if (
        offset < 0
        or end_offset <= offset + 29
        or end_offset > len(data)
        or data[offset] != 25
    ):
        return None
    entity_decoded = _read_leveldata_memorypack_string(
        data,
        offset + 1 + (3 * 8),
        max_length=256,
    )
    if entity_decoded is None:
        return None
    entity_detail_id, prefix_end = entity_decoded
    component_offset = prefix_end + 52
    if (
        not entity_detail_id.startswith("int_")
        or component_offset + 4 > end_offset
    ):
        return None
    entity_type_decoded = _read_leveldata_i32(data, prefix_end)
    logic_id_decoded = _read_leveldata_u64(data, prefix_end + 6)
    if entity_type_decoded is None or logic_id_decoded is None:
        return None
    entity_type, _ = entity_type_decoded
    level_logic_id, _ = logic_id_decoded
    if entity_type <= 0 or level_logic_id <= 0:
        return None

    component_count_decoded = _read_leveldata_count(
        data,
        component_offset,
        max_count=256,
    )
    if component_count_decoded is None or component_count_decoded[0] <= 0:
        return None
    component_count, cursor = component_count_decoded
    components: dict[int, dict] = {}
    component_entry_offsets: dict[int, int] = {}
    for _ in range(component_count):
        entry_offset = cursor
        key_decoded = _read_leveldata_i32(data, cursor)
        if key_decoded is None:
            return None
        component_key, cursor = key_decoded
        if component_key < 0 or component_key in components:
            return None
        prop_map = _parse_level_interactive_param_map(data, cursor, end_offset)
        if prop_map is None:
            return None
        cursor = int(prop_map["endOffset"])
        components[component_key] = prop_map
        component_entry_offsets[component_key] = entry_offset

    narrative_map = components.get(94)
    if (
        narrative_map is None
        or narrative_map.get("entryCount") != 3
        or set(narrative_map.get("entries") or {})
        != {"fx_change_mission_id", "type", "type_id"}
    ):
        return None
    fx_value = narrative_map["entries"]["fx_change_mission_id"]
    type_value = narrative_map["entries"]["type"]
    story_value = narrative_map["entries"]["type_id"]

    def exact_string(value: dict) -> str:
        atoms = value.get("atoms") or []
        if (
            value.get("valueType") != 7
            or value.get("atomCount") != 1
            or len(atoms) != 1
            or atoms[0].get("valueBits") != 0
        ):
            return ""
        return str(atoms[0].get("stringValue") or "")

    mission_id = exact_string(fx_value)
    story_key = exact_string(story_value)
    type_atoms = type_value.get("atoms") or []
    if (
        not mission_id
        or not story_key
        or type_value.get("valueType") != 3
        or type_value.get("atomCount") != 1
        or len(type_atoms) != 1
        or type_atoms[0].get("valueBits") != 1
        or type_atoms[0].get("stringValue") is not None
    ):
        return None
    return {
        "recordOffset": offset,
        "recordEndOffset": end_offset,
        "serializedMemberCount": 25,
        "entityDetailId": entity_detail_id,
        "entityType": entity_type,
        "levelLogicId": level_logic_id,
        "componentPropertiesOffset": component_offset,
        "componentPropertiesEndOffset": cursor,
        "componentPropertiesCount": component_count,
        "componentPropertiesKey": 94,
        "componentPropertyEntryOffset": component_entry_offsets[94],
        "componentPropertyMapOffset": narrative_map["offset"],
        "componentPropertyMapEndOffset": narrative_map["endOffset"],
        "componentPropertyMapEntryCount": 3,
        "propertyEntryOffsets": narrative_map["entryOffsets"],
        "missionStateId": mission_id,
        "storyKey": story_key,
        "narrativeType": 1,
        "narrativeTypeName": "Dialog",
    }


def build_entity_tracking_world_interactive_dialog_contexts(
    available_story_keys: set[str],
    mission_runtime_ids: set[str],
    *,
    mission_runtime_root: Path = MRA_DIR,
    leveldata_root: Path = LEVELDATA_DIR,
    leveldata_mirror_root: Path = (
        PERSISTENT_ASSETS_DIR / "Data" / "Json" / "LevelData"
    ),
    world_entity_registry_path: Path = (
        GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    ),
    interactive_table_path: Path = (
        DATA_JSON_DIR / "Interactive" / "InteractiveTable.json"
    ),
    interactive_table_mirror_path: Path = (
        PERSISTENT_ASSETS_DIR
        / "Data"
        / "Json"
        / "Interactive"
        / "InteractiveTable.json"
    ),
) -> list[dict]:
    """Build exact non-owning quest navigation contexts for world Dialogs.

    Every admitted row is a unique typed ``trackScriptEntity=false`` MRA row
    joined to one exact WorldEntityRegistry global id, one same-scene counted
    LevelInteractiveData record, byte-identical source mirrors, and the exact
    ``int_narrative_common`` template. It is configuration/navigation context,
    never quest playback, completion, ownership, or a server exchange.
    """
    try:
        table_bytes = read_bytes_cached(interactive_table_path)
        if read_bytes_cached(interactive_table_mirror_path) != table_bytes:
            return []
    except OSError:
        return []
    interactive_index = _parse_interactive_object_template_index(table_bytes)
    expected_template_id = "int_narrative_common"
    expected_template_rel = (
        "Data/Json/Interactive/InteractiveData/"
        "data_int_narrative_common.json"
    )
    if (
        (interactive_index.get("coreTemplatePaths") or {}).get(
            expected_template_id
        )
        != expected_template_rel
    ):
        return []
    template_path = (
        interactive_table_path.parent
        / "InteractiveData"
        / "data_int_narrative_common.json"
    )
    template_mirror_path = (
        interactive_table_mirror_path.parent
        / "InteractiveData"
        / "data_int_narrative_common.json"
    )
    try:
        template_bytes = read_bytes_cached(template_path)
        if read_bytes_cached(template_mirror_path) != template_bytes:
            return []
    except OSError:
        return []

    tracking_by_target: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for path in sorted(mission_runtime_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        mission_id = str(payload.get("missionId") or "")
        quests = payload.get("questDic") or {}
        if (
            mission_id not in mission_runtime_ids
            or path.stem != mission_id
            or not isinstance(quests, dict)
        ):
            continue
        for quest_key, quest in quests.items():
            if (
                not isinstance(quest, dict)
                or str(quest.get("questId") or "") != str(quest_key)
            ):
                continue
            for objective_index, objective in enumerate(
                quest.get("objectiveList") or []
            ):
                if not isinstance(objective, dict):
                    continue
                for tracking_index, tracking in enumerate(
                    objective.get("trackingInfoList") or []
                ):
                    if not isinstance(tracking, dict):
                        continue
                    type_name = str(tracking.get("$type") or "").split(",", 1)[0]
                    scene_id = str(tracking.get("sceneId") or "")
                    local_logic_id = tracking.get("entityLogicId")
                    if (
                        type_name.rsplit(".", 1)[-1] != "EntityTrackingInfo"
                        or tracking.get("trackScriptEntity") is not False
                        or not scene_id
                        or not isinstance(local_logic_id, int)
                        or isinstance(local_logic_id, bool)
                        or local_logic_id <= 0
                        or tracking.get("scriptId") != 0
                        or tracking.get("entitySlotId") != 0
                    ):
                        continue
                    tracking_by_target[(scene_id, local_logic_id)].append({
                        "missionId": mission_id,
                        "questId": str(quest_key),
                        "objectiveIndex": objective_index,
                        "trackingIndex": tracking_index,
                        "sceneId": scene_id,
                        "entityLogicId": local_logic_id,
                        "missionRuntimeSourceFile": repo_rel(path),
                        "missionRuntimeSourcePath": (
                            f"$.questDic.{quest_key}.objectiveList"
                            f"[{objective_index}].trackingInfoList[{tracking_index}]"
                        ),
                    })

    try:
        registry = json.loads(world_entity_registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw_briefs = (
        registry.get("worldEntityBriefInfos")
        if isinstance(registry, dict)
        else None
    )
    if not isinstance(raw_briefs, dict):
        return []
    registry_by_local: dict[int, list[dict]] = defaultdict(list)
    tracked_local_ids = {local_id for _scene, local_id in tracking_by_target}
    for raw_global_id, brief in raw_briefs.items():
        try:
            global_id = int(raw_global_id)
        except (TypeError, ValueError):
            continue
        if (
            str(global_id) != str(raw_global_id)
            or global_id <= 0
            or global_id % GLOBAL_SCRIPT_ID_SCALE not in tracked_local_ids
            or not isinstance(brief, dict)
            or not isinstance(brief.get("entityType"), int)
            or not str(brief.get("detailId") or "")
        ):
            continue
        registry_by_local[global_id % GLOBAL_SCRIPT_ID_SCALE].append({
            "globalLogicId": global_id,
            "entityType": brief["entityType"],
            "entityDetailId": str(brief["detailId"]),
        })

    eligible_targets: dict[tuple[str, int], tuple[dict, dict]] = {}
    wanted_global_ids_by_scene: dict[str, set[int]] = defaultdict(set)
    for (scene_id, local_logic_id), tracking_rows in sorted(
        tracking_by_target.items()
    ):
        registry_rows = registry_by_local.get(local_logic_id) or []
        if len(tracking_rows) != 1 or len(registry_rows) != 1:
            continue
        target = (scene_id, local_logic_id)
        tracking = tracking_rows[0]
        registry_row = registry_rows[0]
        global_logic_id = int(registry_row["globalLogicId"])
        eligible_targets[target] = (tracking, registry_row)
        wanted_global_ids_by_scene[scene_id].add(global_logic_id)

    candidates_by_target: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for scene_id, wanted_global_ids in sorted(
        wanted_global_ids_by_scene.items()
    ):
        scene_root = leveldata_root / scene_id
        if not scene_root.is_dir():
            continue
        for path in sorted(scene_root.rglob("*.json")):
            try:
                relative_path = path.relative_to(leveldata_root)
                data = read_bytes_cached(path)
                mirror_path = leveldata_mirror_root / relative_path
                if read_bytes_cached(mirror_path) != data:
                    continue
            except (OSError, ValueError):
                continue
            if not data or data[0] != 0x2B:
                continue
            for frame in _level_interactive_data_list_frames(data):
                for record in frame.get("records") or []:
                    context = parse_level_interactive_world_dialog_context(
                        data,
                        int(record["recordOffset"]),
                        int(record["recordEndOffset"]),
                    )
                    if (
                        context is None
                        or context["levelLogicId"] not in wanted_global_ids
                    ):
                        continue
                    candidates_by_target[
                        (scene_id, int(context["levelLogicId"]))
                    ].append({
                        **context,
                        "interactiveListCount": frame["listCount"],
                        "interactiveListCountOffset": frame["listCountOffset"],
                        "recordIndex": record["recordIndex"],
                        "levelDataSourceFile": repo_rel(path),
                        "levelDataVerifiedMirrorFile": repo_rel(mirror_path),
                    })

    rows: list[dict] = []
    for (scene_id, _local_logic_id), (tracking, registry_row) in sorted(
        eligible_targets.items()
    ):
        global_logic_id = int(registry_row["globalLogicId"])
        candidates = candidates_by_target.get((scene_id, global_logic_id)) or []
        if len(candidates) != 1:
            continue
        context = candidates[0]
        mission_id = str(context.get("missionStateId") or "")
        story_key = str(context.get("storyKey") or "")
        entity_detail_id = str(context.get("entityDetailId") or "")
        template_id = str(
            (interactive_index.get("objectToTemplate") or {}).get(
                entity_detail_id
            )
            or ""
        )
        if (
            mission_id != tracking["missionId"]
            or mission_id not in mission_runtime_ids
            or story_key not in available_story_keys
            or context.get("entityType") != registry_row["entityType"]
            or entity_detail_id != registry_row["entityDetailId"]
            or template_id != expected_template_id
        ):
            continue
        rows.append({
            **context,
            **tracking,
            "relation": "entity_tracking_world_interactive_dialog_context",
            "levelId": scene_id,
            "worldEntityGlobalLogicId": str(global_logic_id),
            "entityTemplateId": template_id,
            "entityTemplatePath": expected_template_rel,
            "worldEntityRegistrySourceFile": repo_rel(
                world_entity_registry_path
            ),
            "interactiveTableSourceFile": repo_rel(interactive_table_path),
            "interactiveTableVerifiedMirrorFile": repo_rel(
                interactive_table_mirror_path
            ),
            "interactiveTemplateSourceFile": repo_rel(template_path),
            "interactiveTemplateVerifiedMirrorFile": repo_rel(
                template_mirror_path
            ),
            "ownership": False,
            "questPlayback": False,
            "questCompletion": False,
            "serverExchange": False,
        })
    rows.sort(key=lambda row: (
        str(row.get("missionId") or ""),
        str(row.get("questId") or ""),
        str(row.get("storyKey") or ""),
    ))
    return rows


_LEVEL_INTERACTIVE_PARAM_STRING_PREFIX = (
    b"\x02\x07\x00\x00\x00\x01\x00\x00\x00"
    b"\x02\x00\x00\x00\x00\x00\x00\x00\x00"
)


def _parse_level_interactive_param_string_map(
    data: bytes,
    offset: int,
    end_offset: int,
) -> dict | None:
    """Parse the exact current string-to-string ParamValue map encoding.

    Native metadata names the keys as ``Beyond.PropertyKeys`` values. Each
    key is a two-member property-key wrapper; each value is a two-member
    ParamValue whose current string discriminator is 7 and whose scalar
    payload prefix is the fixed installed-build sequence below. Keeping this
    parser deliberately narrow prevents arbitrary nearby strings from being
    treated as entity properties.
    """
    count_decoded = _read_leveldata_count(data, offset, max_count=64)
    if count_decoded is None or count_decoded[0] <= 0:
        return None
    count, cursor = count_decoded
    entries: dict[str, str] = {}
    entry_offsets: dict[str, int] = {}
    for _ in range(count):
        entry_offset = cursor
        if cursor >= end_offset or data[cursor] != 2:
            return None
        cursor += 1
        key_decoded = _read_leveldata_memorypack_string(
            data,
            cursor,
            max_length=256,
        )
        if key_decoded is None:
            return None
        key, cursor = key_decoded
        if (
            not key
            or key in entries
            or cursor + len(_LEVEL_INTERACTIVE_PARAM_STRING_PREFIX) > end_offset
            or data[
                cursor : cursor + len(_LEVEL_INTERACTIVE_PARAM_STRING_PREFIX)
            ] != _LEVEL_INTERACTIVE_PARAM_STRING_PREFIX
        ):
            return None
        cursor += len(_LEVEL_INTERACTIVE_PARAM_STRING_PREFIX)
        value_decoded = _read_leveldata_memorypack_string(
            data,
            cursor,
            max_length=512,
        )
        if value_decoded is None:
            return None
        value, cursor = value_decoded
        if cursor > end_offset:
            return None
        entries[key] = value
        entry_offsets[key] = entry_offset
    return {
        "mapOffset": offset,
        "mapEndOffset": cursor,
        "entryCount": count,
        "entries": entries,
        "entryOffsets": entry_offsets,
    }


def parse_level_interactive_narrative_mission_context(
    data: bytes,
    offset: int,
    end_offset: int,
) -> dict | None:
    """Decode one exact LevelInteractiveData narrative mission co-carrier.

    The current generated formatter uses a 25-member object header. Its base
    prefix contains three 64-bit ids followed by the authored interactive
    object id. The record boundary is supplied by the enclosing typed list,
    and the accepted ParamValue map must uniquely co-carry the canonical
    ``FX_CHANGE_MISSION_ID`` and ``TYPE_ID`` PropertyKeys.
    """
    if (
        offset < 0
        or end_offset <= offset + 29
        or end_offset > len(data)
        or data[offset] != 25
    ):
        return None
    entity_decoded = _read_leveldata_memorypack_string(
        data,
        offset + 1 + (3 * 8),
        max_length=256,
    )
    if entity_decoded is None:
        return None
    entity_detail_id, prefix_end = entity_decoded
    if not entity_detail_id.startswith("int_"):
        return None

    fx_key = b"fx_change_mission_id"
    fx_marker = b"\x02" + len(fx_key).to_bytes(4, "little") + fx_key
    map_candidates: list[dict] = []
    search_offset = prefix_end
    while True:
        key_offset = data.find(fx_marker, search_offset, end_offset)
        if key_offset < 0:
            break
        search_offset = key_offset + 1
        if key_offset < prefix_end + 4:
            continue
        parsed = _parse_level_interactive_param_string_map(
            data,
            key_offset - 4,
            end_offset,
        )
        if parsed is None:
            continue
        entries = parsed["entries"]
        if (
            entries.get("fx_change_mission_id")
            and str(entries.get("type_id") or "").startswith("rp_")
        ):
            map_candidates.append(parsed)
    unique_candidates = {
        (int(row["mapOffset"]), int(row["mapEndOffset"])): row
        for row in map_candidates
    }
    if len(unique_candidates) != 1:
        return None
    prop_map = next(iter(unique_candidates.values()))
    return {
        "recordOffset": offset,
        "recordEndOffset": end_offset,
        "serializedMemberCount": 25,
        "entityDetailId": entity_detail_id,
        "paramMapOffset": prop_map["mapOffset"],
        "paramMapEndOffset": prop_map["mapEndOffset"],
        "paramMapEntryCount": prop_map["entryCount"],
        "propertyEntryOffsets": prop_map["entryOffsets"],
        "missionStateId": prop_map["entries"]["fx_change_mission_id"],
        "readingPopupId": prop_map["entries"]["type_id"],
    }


def _level_interactive_data_list_frames(data: bytes) -> list[dict]:
    """Locate fully counted LevelInteractiveData lists in one LevelData blob."""
    candidates: list[tuple[int, str]] = []
    for offset, value in enumerate(data):
        if value != 25 or offset + 29 > len(data):
            continue
        decoded = _read_leveldata_memorypack_string(
            data,
            offset + 1 + (3 * 8),
            max_length=256,
        )
        if decoded is not None and decoded[0].startswith("int_"):
            candidates.append((offset, decoded[0]))
    frames: list[dict] = []
    for index, (offset, _entity_id) in enumerate(candidates):
        if offset < 4:
            continue
        count = int.from_bytes(data[offset - 4 : offset], "little", signed=True)
        if count <= 0 or count > 50_000 or index + count > len(candidates):
            continue
        record_starts = candidates[index : index + count]
        # A next typed record is required as an exact end boundary. The final
        # list item remains intentionally unparsed rather than borrowing the
        # unknown following LevelData member as a boundary.
        bounded_records = [
            {
                "recordIndex": record_index,
                "recordOffset": record_starts[record_index][0],
                "recordEndOffset": record_starts[record_index + 1][0],
                "entityDetailId": record_starts[record_index][1],
            }
            for record_index in range(max(0, count - 1))
        ]
        frames.append({
            "listCountOffset": offset - 4,
            "listCount": count,
            "records": bounded_records,
        })
    return frames


def parse_level_interactive_quest_progress_lock(
    data: bytes,
    offset: int,
    end_offset: int,
) -> dict | None:
    """Decode one complete quest-state progress lock from LevelInteractiveData.

    The record boundary must come from the counted 25-member
    ``LevelInteractiveData`` list.  The parser consumes ``componentProperties``
    in full and then requires the complete current-build derived suffix through
    the exact record end.  Only ``SimpleConditionCheckQuestState`` equal to
    ``QuestState.Completed`` is admitted; nearby strings or partially decoded
    records are never evidence.
    """
    if (
        offset < 0
        or end_offset <= offset + 29
        or end_offset > len(data)
        or data[offset] != 25
    ):
        return None
    detail_decoded = _read_leveldata_memorypack_string(
        data,
        offset + 1 + (3 * 8),
        max_length=256,
    )
    if detail_decoded is None:
        return None
    entity_detail_id, prefix_end = detail_decoded
    component_offset = prefix_end + 52
    if (
        not entity_detail_id.startswith("int_")
        or component_offset + 4 > end_offset
    ):
        return None
    entity_type_decoded = _read_leveldata_i32(data, prefix_end)
    logic_id_decoded = _read_leveldata_u64(data, prefix_end + 6)
    if entity_type_decoded is None or logic_id_decoded is None:
        return None
    entity_type, _ = entity_type_decoded
    level_logic_id, _ = logic_id_decoded
    if (
        not isinstance(entity_type, int)
        or entity_type <= 0
        or level_logic_id <= 0
    ):
        return None

    component_count_decoded = _read_leveldata_count(
        data,
        component_offset,
        max_count=256,
    )
    if component_count_decoded is None or component_count_decoded[0] < 0:
        return None
    component_count, cursor = component_count_decoded
    component_keys: list[int] = []
    component_entry_counts: list[int] = []
    for _ in range(component_count):
        key_decoded = _read_leveldata_i32(data, cursor)
        if key_decoded is None:
            return None
        component_key, cursor = key_decoded
        if component_key < 0 or component_key in component_keys:
            return None
        prop_map = _parse_level_interactive_param_map(data, cursor, end_offset)
        if prop_map is None:
            return None
        component_keys.append(component_key)
        component_entry_counts.append(int(prop_map["entryCount"]))
        cursor = int(prop_map["endOffset"])
    component_end = cursor

    null_collection_offsets: dict[str, int] = {}
    for field_name in ("globalIntKeyList", "globalProperties"):
        decoded = _read_leveldata_count(data, cursor, max_count=256)
        if decoded is None or decoded[0] != -1:
            return None
        null_collection_offsets[field_name] = cursor
        _, cursor = decoded
    bool_values: dict[str, bool] = {}
    for field_name in ("hideInDialog", "isClientOnly", "isLocked"):
        if cursor >= end_offset or data[cursor] not in (0, 1):
            return None
        bool_values[field_name] = bool(data[cursor])
        cursor += 1
    for field_name in ("mapIntKeyList", "mapProperties"):
        decoded = _read_leveldata_count(data, cursor, max_count=256)
        if decoded is None or decoded[0] != -1:
            return None
        null_collection_offsets[field_name] = cursor
        _, cursor = decoded
    if cursor + 4 > end_offset:
        return None
    model_scale = struct.unpack_from("<f", data, cursor)[0]
    model_scale_offset = cursor
    cursor += 4
    if not math.isfinite(model_scale):
        return None

    condition_offset = cursor
    if cursor + 10 > end_offset or data[cursor : cursor + 2] != b"\x10\x03":
        return None
    cursor += 2
    compare_operator_decoded = _read_leveldata_i32(data, cursor)
    if compare_operator_decoded is None:
        return None
    compare_operator, cursor = compare_operator_decoded
    compare_target_decoded = _read_leveldata_i32(data, cursor)
    if compare_target_decoded is None:
        return None
    compare_target, cursor = compare_target_decoded
    quest_decoded = _read_leveldata_memorypack_string(
        data,
        cursor,
        max_length=256,
    )
    if quest_decoded is None:
        return None
    quest_id, cursor = quest_decoded
    properties_decoded = _read_leveldata_count(data, cursor, max_count=256)
    if properties_decoded is None:
        return None
    properties_count, cursor = properties_decoded
    if (
        compare_operator != 0
        or compare_target != 3
        or not quest_id
        or properties_count != 0
        or cursor != end_offset
    ):
        return None
    return {
        "recordOffset": offset,
        "recordEndOffset": end_offset,
        "serializedMemberCount": 25,
        "entityDetailId": entity_detail_id,
        "entityType": entity_type,
        "levelLogicId": level_logic_id,
        "componentPropertiesOffset": component_offset,
        "componentPropertiesEndOffset": component_end,
        "componentPropertiesCount": component_count,
        "componentPropertyKeys": component_keys,
        "componentPropertyEntryCounts": component_entry_counts,
        "nullCollectionOffsets": null_collection_offsets,
        **bool_values,
        "modelScale": model_scale,
        "modelScaleOffset": model_scale_offset,
        "progressLockConditionOffset": condition_offset,
        "progressLockConditionUnionTag": 0x10,
        "progressLockConditionSerializedMemberCount": 3,
        "progressLockConditionType": "SimpleConditionCheckQuestState",
        "compareOperator": compare_operator,
        "compareOperatorName": "Equal",
        "compareTarget": compare_target,
        "compareTargetName": "QuestState.Completed",
        "questId": quest_id,
        "propertiesCount": properties_count,
    }


def _exact_interactive_state_entity_logic_id(owner: dict) -> int | None:
    """Return the exact constant world-entity receiver of one native owner."""
    if not isinstance(owner, dict):
        return None
    detail = owner.get("eventDetail")
    if not isinstance(detail, dict):
        return None
    target = detail.get("targetEntity")
    target_param = detail.get("targetEntityParam")
    logic_id = target.get("logicId") if isinstance(target, dict) else None
    if not (
        owner.get("status") == "exact_serialized_control_path"
        and owner.get("nativeHeaderMappingId")
        == LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID
        and owner.get("headerName") == "EntityEvent_OnInteractiveStateChanged"
        and owner.get("headerUnionTag") == "0x001e"
        and owner.get("headerSerializedMemberCount") == 20
        and detail.get("type") == "EntityEvent_OnInteractiveStateChanged"
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        and detail.get("entityEventScope") == "specified-entity"
        and detail.get("triggerTarget") == "SPECIFY_ENTITY"
        and isinstance(target, dict)
        and isinstance(logic_id, int)
        and not isinstance(logic_id, bool)
        and logic_id > 0
        and target.get("useSlotId") is False
        and target.get("slotId") == 0
        and isinstance(target_param, dict)
        and target_param.get("idRef") == -1
        and target_param.get("paramSource") == 0
        and target_param.get("path") is None
        and detail.get("targetEntityListPresent") is False
        and detail.get("targetEntityListOutputPresent") is False
        and detail.get("serverExchange") is False
        and detail.get("serializedMissionOrQuestId") is False
    ):
        return None
    return logic_id


def _exact_script_custom_event_owner_signature(owner: dict) -> tuple | None:
    """Return an exact literal ScriptEvent custom-listener identity."""
    if not isinstance(owner, dict):
        return None
    detail = owner.get("eventDetail")
    if not isinstance(detail, dict):
        return None
    event_key = str(detail.get("eventKey") or "").strip()
    if not (
        owner.get("status") == "exact_serialized_control_path"
        and owner.get("nativeHeaderMappingId")
        == LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID
        and owner.get("headerName") == "ScriptEvent_OnCustomEvent"
        and detail.get("type") == "ScriptEvent_OnCustomEvent"
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        and event_key
        and not event_key.startswith("$")
    ):
        return None
    return (
        owner.get("headerLocalId"),
        event_key,
        tuple(owner.get("pathLocalIds") or []),
    )


def build_quest_progress_locked_interactive_story_contexts(
    native_playback_index: dict[str, list[dict]],
    custom_event_story_producer_routes: list[dict],
    mission_runtime_ids: set[str],
    *,
    mission_runtime_root: Path = MRA_DIR,
    leveldata_root: Path = LEVELDATA_DIR,
    leveldata_mirror_root: Path = (
        PERSISTENT_ASSETS_DIR / "Data" / "Json" / "LevelData"
    ),
    world_entity_registry_path: Path = (
        GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    ),
) -> list[dict]:
    """Bind Story playback to exact quest-locked interactive context.

    This helper is deliberately all-or-nothing per Story key. Every native
    playback occurrence must be rooted either directly at an exact constant
    ``OnInteractiveStateChanged`` receiver or at a literal custom-event
    producer whose complete control path is rooted there. Every referenced
    entity must then resolve through one byte-identical counted LevelData
    record, the exact registry type/detail pair, and one real MissionRuntime
    quest. All occurrences must agree on that same quest.

    The result is non-owning local playback context. The quest's Completed
    state gates interactive progress lock; it does not prove quest activation,
    playback, completion causality, or a client/server request.
    """
    if not native_playback_index or not mission_runtime_ids:
        return []

    quest_owners: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(mission_runtime_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        mission_id = str(payload.get("missionId") or "")
        quests = payload.get("questDic")
        if (
            mission_id not in mission_runtime_ids
            or path.stem != mission_id
            or not isinstance(quests, dict)
        ):
            continue
        for raw_quest_id, quest in quests.items():
            quest_id = str(raw_quest_id or "")
            if (
                not quest_id
                or not isinstance(quest, dict)
                or str(quest.get("questId") or "") != quest_id
            ):
                continue
            quest_owners[quest_id].append({
                "missionId": mission_id,
                "questId": quest_id,
                "missionRuntimeSourceFile": repo_rel(path),
                "missionRuntimeSourcePath": f"$.questDic.{quest_id}",
            })

    try:
        registry_payload = json.loads(
            world_entity_registry_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return []
    raw_briefs = (
        registry_payload.get("worldEntityBriefInfos")
        if isinstance(registry_payload, dict)
        else None
    )
    if not isinstance(raw_briefs, dict):
        return []
    registry_by_logic_id: dict[int, dict] = {}
    for raw_logic_id, brief in raw_briefs.items():
        try:
            logic_id = int(raw_logic_id)
        except (TypeError, ValueError):
            continue
        if (
            str(logic_id) != str(raw_logic_id)
            or logic_id <= 0
            or not isinstance(brief, dict)
            or not isinstance(brief.get("entityType"), int)
            or isinstance(brief.get("entityType"), bool)
            or brief.get("entityType") <= 0
            or not str(brief.get("detailId") or "")
        ):
            continue
        registry_by_logic_id[logic_id] = {
            "levelLogicId": logic_id,
            "entityType": int(brief["entityType"]),
            "entityDetailId": str(brief["detailId"]),
            "worldEntityRegistrySourceFile": repo_rel(
                world_entity_registry_path
            ),
        }

    routes_by_listener: dict[tuple[str, str, str, object, tuple], list[dict]] = (
        defaultdict(list)
    )
    for route in custom_event_story_producer_routes:
        if not isinstance(route, dict):
            continue
        story_key = str(route.get("storyKey") or "")
        level_id = str(route.get("levelId") or "")
        if not story_key or not level_id:
            continue
        for listener_route in route.get("listenerRoutes") or []:
            if not isinstance(listener_route, dict):
                continue
            listener_script_id = str(
                listener_route.get("listenerScriptId") or ""
            )
            listener_owner = listener_route.get("listenerEventOwner")
            signature = _exact_script_custom_event_owner_signature(
                listener_owner
            )
            if signature is None or not listener_script_id:
                continue
            routes_by_listener[(
                level_id,
                listener_script_id,
                str(listener_route.get("listenerSourceFile") or ""),
                listener_route.get("listenerPlaybackActionOffset"),
                signature,
            )].append(route)

    leveldata_cache: dict[tuple[str, int], list[dict]] = {}

    def resolve_leveldata(level_id: str, logic_id: int) -> list[dict]:
        cache_key = (level_id, logic_id)
        if cache_key in leveldata_cache:
            return leveldata_cache[cache_key]
        candidates: list[dict] = []
        level_root = leveldata_root / level_id
        if level_root.is_dir():
            for path in sorted(level_root.rglob("*.json")):
                try:
                    relative_path = path.relative_to(leveldata_root)
                    data = read_bytes_cached(path)
                    mirror_path = leveldata_mirror_root / relative_path
                    if read_bytes_cached(mirror_path) != data:
                        continue
                except (OSError, ValueError):
                    continue
                if not data or data[0] != 0x2B:
                    continue
                for frame in _level_interactive_data_list_frames(data):
                    for record in frame.get("records") or []:
                        parsed = parse_level_interactive_quest_progress_lock(
                            data,
                            int(record["recordOffset"]),
                            int(record["recordEndOffset"]),
                        )
                        if parsed is None or parsed["levelLogicId"] != logic_id:
                            continue
                        candidates.append({
                            **parsed,
                            "levelId": level_id,
                            "interactiveListCount": frame["listCount"],
                            "interactiveListCountOffset": frame[
                                "listCountOffset"
                            ],
                            "recordIndex": record["recordIndex"],
                            "levelDataSourceFile": repo_rel(path),
                            "levelDataVerifiedMirrorFile": repo_rel(mirror_path),
                        })
        leveldata_cache[cache_key] = candidates
        return candidates

    rows: list[dict] = []
    for story_key, raw_occurrences in sorted(native_playback_index.items()):
        occurrences: list[dict] = []
        seen_occurrences: set[tuple] = set()
        for occurrence in raw_occurrences or []:
            if not isinstance(occurrence, dict):
                continue
            occurrence_signature = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
                str(occurrence.get("sourceFile") or ""),
                occurrence.get("recordOffset"),
                occurrence.get("localId"),
            )
            if occurrence_signature in seen_occurrences:
                continue
            seen_occurrences.add(occurrence_signature)
            occurrences.append(occurrence)
        if not story_key or not occurrences:
            continue

        route_evidence: list[dict] = []
        entity_targets: set[tuple[str, int]] = set()
        rejected = False
        for occurrence in occurrences:
            level_id = str(occurrence.get("levelId") or "")
            script_id = str(occurrence.get("scriptId") or "")
            owners = occurrence.get("nativeEventOwners") or []
            if not level_id or not script_id or not owners:
                rejected = True
                break
            occurrence_routes: list[dict] = []
            for owner in owners:
                direct_logic_id = _exact_interactive_state_entity_logic_id(owner)
                if direct_logic_id is not None:
                    entity_targets.add((level_id, direct_logic_id))
                    occurrence_routes.append({
                        "routeType": "direct_interactive_state_playback",
                        "levelId": level_id,
                        "listenerScriptId": script_id,
                        "entityLogicIds": [str(direct_logic_id)],
                        "eventOwner": owner,
                        "playbackSourceFile": str(
                            occurrence.get("sourceFile") or ""
                        ),
                        "playbackActionOffset": occurrence.get("recordOffset"),
                    })
                    continue

                listener_signature = _exact_script_custom_event_owner_signature(
                    owner
                )
                if listener_signature is None:
                    rejected = True
                    break
                matching_routes = routes_by_listener.get((
                    level_id,
                    script_id,
                    str(occurrence.get("sourceFile") or ""),
                    occurrence.get("recordOffset"),
                    listener_signature,
                )) or []
                matching_routes = [
                    route
                    for route in matching_routes
                    if str(route.get("storyKey") or "") == story_key
                    and route.get("status") == "exact_serialized_local_producer"
                    and route.get("producerAction") == "RaiseCustomScriptEvent"
                    and route.get("receiverMode")
                    in {"current_script", "constant_script"}
                    and route.get("serverExchange") is False
                    and route.get("serializedMissionOrQuestId") is False
                ]
                if not matching_routes:
                    rejected = True
                    break
                for route in matching_routes:
                    producer_owners = route.get("producerControlPaths") or []
                    producer_logic_ids = [
                        _exact_interactive_state_entity_logic_id(path)
                        for path in producer_owners
                    ]
                    if (
                        not producer_logic_ids
                        or any(logic_id is None for logic_id in producer_logic_ids)
                    ):
                        rejected = True
                        break
                    exact_logic_ids = sorted({
                        int(logic_id)
                        for logic_id in producer_logic_ids
                        if logic_id is not None
                    })
                    for logic_id in exact_logic_ids:
                        entity_targets.add((level_id, logic_id))
                    occurrence_routes.append({
                        "routeType": "interactive_state_custom_event_playback",
                        "levelId": level_id,
                        "listenerScriptId": script_id,
                        "entityLogicIds": [str(value) for value in exact_logic_ids],
                        "listenerEventOwner": owner,
                        "producerRoute": route,
                        "playbackSourceFile": str(
                            occurrence.get("sourceFile") or ""
                        ),
                        "playbackActionOffset": occurrence.get("recordOffset"),
                    })
                if rejected:
                    break
            if rejected or not occurrence_routes:
                rejected = True
                break
            route_evidence.extend(occurrence_routes)
        if rejected or not entity_targets:
            continue

        entity_contexts: list[dict] = []
        quest_targets: set[tuple[str, str]] = set()
        for level_id, logic_id in sorted(entity_targets):
            candidates = resolve_leveldata(level_id, logic_id)
            registry = registry_by_logic_id.get(logic_id)
            if len(candidates) != 1 or registry is None:
                rejected = True
                break
            context = candidates[0]
            if (
                context.get("entityType") != registry.get("entityType")
                or context.get("entityDetailId")
                != registry.get("entityDetailId")
            ):
                rejected = True
                break
            quest_id = str(context.get("questId") or "")
            owners = quest_owners.get(quest_id) or []
            if len(owners) != 1:
                rejected = True
                break
            owner = owners[0]
            quest_targets.add((owner["missionId"], owner["questId"]))
            entity_contexts.append({
                **context,
                **registry,
                **owner,
            })
        if rejected or len(quest_targets) != 1:
            continue
        mission_id, quest_id = next(iter(quest_targets))
        rows.append({
            "relation": "quest_progress_locked_interactive_playback_context",
            "storyKey": story_key,
            "missionId": mission_id,
            "questId": quest_id,
            "occurrenceCount": len(occurrences),
            "routeCount": len(route_evidence),
            "levelIds": sorted({level_id for level_id, _logic_id in entity_targets}),
            "entityLogicIds": [
                str(logic_id) for _level_id, logic_id in sorted(entity_targets)
            ],
            "entityRoutes": route_evidence,
            "levelDataRecords": entity_contexts,
            "progressLockCondition": "SimpleConditionCheckQuestState",
            "compareOperator": "Equal",
            "compareTarget": "QuestState.Completed",
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "executionSide": "client",
            "networkRole": (
                "reads_synchronized_local_quest_state_and_dispatches_local_entity_event"
            ),
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
        })
    rows.sort(key=lambda row: (
        str(row.get("missionId") or ""),
        str(row.get("questId") or ""),
        str(row.get("storyKey") or ""),
    ))
    return rows


def build_level_interactive_narrative_mission_story_contexts(
    available_story_keys: set[str],
    mission_runtime_ids: set[str],
    *,
    leveldata_root: Path = LEVELDATA_DIR,
    reading_popup_path: Path = STREAMING_TABLE_DIR / "ReadingPopUpTable.json",
) -> list[dict]:
    """Recover same-entity narrative popup/mission-state dependencies.

    All joins are original-data/native: a counted LevelInteractiveData record
    co-carries the canonical PropertyKeys, InteractiveTable resolves its exact
    object template, ReadingPopUpTable resolves the popup id to Story content,
    and NarrativeComponent's installed native paths read mission state and
    invoke radio/dialog playback. This is local dependency context, never
    Story ownership, quest causality, or chronology.
    """
    try:
        reading_popup_rows = json.loads(reading_popup_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(reading_popup_rows, dict):
        return []
    interactive_index = _load_interactive_object_template_index()
    object_to_template = interactive_index.get("objectToTemplate") or {}
    core_paths = interactive_index.get("coreTemplatePaths") or {}
    rows: list[dict] = []
    seen: set[tuple] = set()
    for path in sorted(leveldata_root.rglob("*.json")):
        try:
            data = read_bytes_cached(path)
        except OSError:
            continue
        if not data or data[0] != 0x2B:
            continue
        for frame in _level_interactive_data_list_frames(data):
            for record in frame["records"]:
                context = parse_level_interactive_narrative_mission_context(
                    data,
                    record["recordOffset"],
                    record["recordEndOffset"],
                )
                if context is None:
                    continue
                mission_id = str(context.get("missionStateId") or "")
                popup_id = str(context.get("readingPopupId") or "")
                popup_row = reading_popup_rows.get(popup_id)
                story_key = str(
                    popup_row.get("contentId")
                    if isinstance(popup_row, dict)
                    else ""
                ).strip()
                entity_detail_id = str(context.get("entityDetailId") or "")
                template_id = str(object_to_template.get(entity_detail_id) or "")
                if (
                    mission_id not in mission_runtime_ids
                    or story_key not in available_story_keys
                    or template_id != "int_narrative_common"
                ):
                    continue
                signature = (
                    mission_id,
                    story_key,
                    str(path),
                    int(context["recordOffset"]),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                rows.append({
                    **context,
                    "storyKey": story_key,
                    "levelId": path.parent.name,
                    "sourceFile": path.name,
                    "sourcePath": str(path),
                    "interactiveListCount": frame["listCount"],
                    "interactiveListCountOffset": frame["listCountOffset"],
                    "recordIndex": record["recordIndex"],
                    "entityTemplateId": template_id,
                    "entityTemplatePath": str(core_paths.get(template_id) or ""),
                    "interactiveTableSourceFile": str(
                        interactive_index.get("sourceFile") or ""
                    ),
                    "interactiveTableVerifiedMirrorFile": str(
                        interactive_index.get("verifiedMirrorFile") or ""
                    ),
                    "readingPopupTableSourceFile": repo_rel(reading_popup_path),
                    "propertyKeys": ["FX_CHANGE_MISSION_ID", "TYPE_ID"],
                    "propertyKeyTokens": ["0x04000b50", "0x04000941"],
                    "nativeConsumer": (
                        "NarrativeComponent._CheckInitialFxChangeCondition -> "
                        "MissionSystem.GetMissionState; ClientCollectNarrative/"
                        "_CollectNarrative -> GameAction.PlayRadio or "
                        "StartDialogFromInteractive"
                    ),
                })
    rows.sort(key=lambda row: (
        str(row.get("storyKey") or ""),
        str(row.get("missionStateId") or ""),
        str(row.get("sourcePath") or ""),
        int(row.get("recordOffset") or 0),
    ))
    return rows


def parse_levelscript_brief_data_entry(
    data: bytes,
    offset: int,
    *,
    expected_script_id: int | None = None,
) -> dict | None:
    """Parse one native LevelData member-22 BriefData dictionary entry.

    Current GameAssembly proves ``LevelData`` is a 43-member MemoryPack object
    and serialized member 22 is the sole
    ``Dictionary<ulong, LevelScriptBriefData>``.  The BriefData formatter has
    eight members.  Requiring the final typed ``scriptId`` to repeat the
    dictionary key rejects coincidental ``<u64><0x08>`` byte patterns in other
    LevelData members.
    """
    key_decoded = _read_leveldata_u64(data, offset)
    if key_decoded is None:
        return None
    key, cursor = key_decoded
    if expected_script_id is not None and key != expected_script_id:
        return None
    if cursor >= len(data) or data[cursor] != 0x08:
        return None
    cursor += 1

    data_path_decoded = _read_leveldata_u64(data, cursor)
    if data_path_decoded is None:
        return None
    data_path_hash, cursor = data_path_decoded

    type_decoded = _read_leveldata_i32(data, cursor)
    if type_decoded is None:
        return None
    level_script_type, cursor = type_decoded
    if not 0 <= level_script_type <= 5:
        return None

    max_stage_decoded = _read_leveldata_i32(data, cursor)
    if max_stage_decoded is None:
        return None
    max_stage, cursor = max_stage_decoded
    if max_stage < 0 or max_stage > 1_000_000:
        return None

    parent_decoded = _read_leveldata_u64(data, cursor)
    if parent_decoded is None:
        return None
    parent_script_id, cursor = parent_decoded

    properties_decoded = _read_leveldata_count(data, cursor)
    if properties_decoded is None:
        return None
    property_count, cursor = properties_decoded
    properties: list[dict] = []
    for _ in range(max(0, property_count)):
        if cursor >= len(data) or data[cursor] not in (0x02, 0xFF):
            return None
        property_header = data[cursor]
        cursor += 1
        if property_header == 0xFF:
            continue
        property_name_decoded = _read_leveldata_memorypack_string(
            data,
            cursor,
            max_length=512,
        )
        if property_name_decoded is None:
            return None
        property_name, cursor = property_name_decoded
        if cursor >= len(data) or data[cursor] not in (0x02, 0xFF):
            return None
        value_header = data[cursor]
        cursor += 1
        if value_header == 0xFF:
            properties.append({"name": property_name, "value": None})
            continue
        value_type_decoded = _read_leveldata_i32(data, cursor)
        if value_type_decoded is None:
            return None
        value_type, cursor = value_type_decoded
        atoms_decoded = _read_leveldata_count(data, cursor)
        if atoms_decoded is None:
            return None
        atom_count, cursor = atoms_decoded
        atoms: list[dict | None] = []
        for _ in range(max(0, atom_count)):
            if cursor >= len(data) or data[cursor] not in (0x02, 0xFF):
                return None
            atom_header = data[cursor]
            cursor += 1
            if atom_header == 0xFF:
                atoms.append(None)
                continue
            value_bits = _read_leveldata_u64(data, cursor)
            if value_bits is None:
                return None
            value_bit64, cursor = value_bits
            atom_text_decoded = _read_leveldata_memorypack_string(
                data,
                cursor,
                max_length=4096,
            )
            if atom_text_decoded is None:
                return None
            atom_text, cursor = atom_text_decoded
            atoms.append({
                "valueBit64": value_bit64,
                "text": atom_text,
            })
        properties.append({
            "name": property_name,
            "value": {
                "valueType": value_type,
                "atomCount": max(0, atom_count),
                "atoms": atoms,
            },
        })

    property_map_decoded = _read_leveldata_count(data, cursor)
    if property_map_decoded is None:
        return None
    property_map_count, cursor = property_map_decoded
    for _ in range(max(0, property_map_count)):
        property_id_decoded = _read_leveldata_i32(data, cursor)
        if property_id_decoded is None:
            return None
        _property_id, cursor = property_id_decoded
        cursor = _skip_leveldata_memorypack_string(data, cursor)
        if cursor is None:
            return None

    world_refs_decoded = _read_leveldata_count(data, cursor)
    if world_refs_decoded is None:
        return None
    world_ref_count, cursor = world_refs_decoded
    world_entity_ids: list[str] = []
    for _ in range(max(0, world_ref_count)):
        world_ref_decoded = _read_leveldata_u64(data, cursor)
        if world_ref_decoded is None:
            return None
        world_entity_id, cursor = world_ref_decoded
        world_entity_ids.append(str(world_entity_id))

    final_script_decoded = _read_leveldata_u64(data, cursor)
    if final_script_decoded is None:
        return None
    final_script_id, cursor = final_script_decoded
    if final_script_id != key:
        return None
    return {
        "keyOffset": offset,
        "endOffset": cursor,
        "scriptId": str(key),
        "dataPathHash": str(data_path_hash),
        "levelScriptType": level_script_type,
        "maxStage": max_stage,
        "parentLevelScriptId": str(parent_script_id),
        "propertyCount": max(0, property_count),
        "properties": properties,
        "propertyMapCount": max(0, property_map_count),
        "refWorldEntityCount": max(0, world_ref_count),
        "refWorldEntityIds": world_entity_ids,
    }


def find_levelscript_brief_data_entries(data: bytes, script_id: int) -> list[dict]:
    if not data or data[0] != 0x2B:
        return []
    needle = script_id.to_bytes(8, "little", signed=False)
    out: list[dict] = []
    for offset in _find_exact_bytes_offsets(data, needle):
        entry = parse_levelscript_brief_data_entry(
            data,
            offset,
            expected_script_id=script_id,
        )
        if entry is not None:
            out.append(entry)
    return out


@lru_cache(maxsize=None)
def _parse_leveldata_levelscript_brief_dictionary_cached(
    data: bytes,
    candidate_script_ids: tuple[int, ...],
) -> dict[int, dict]:
    """Locate and validate the complete LevelData member-22 dictionary.

    Accepted BriefData values must form one contiguous key/value chain whose
    immediately preceding signed count equals the chain length.  This proves
    the member's dictionary framing without implementing the twenty unrelated
    LevelData members that precede it.
    """
    if not data or data[0] != 0x2B:
        return {}
    entries: list[dict] = []
    for script_id in candidate_script_ids:
        entries.extend(find_levelscript_brief_data_entries(data, script_id))
    if not entries:
        return {}
    entries.sort(key=lambda entry: int(entry["keyOffset"]))
    if len({int(entry["keyOffset"]) for entry in entries}) != len(entries):
        return {}
    if any(
        int(previous["endOffset"]) != int(current["keyOffset"])
        for previous, current in zip(entries, entries[1:])
    ):
        return {}
    count_offset = int(entries[0]["keyOffset"]) - 4
    count_decoded = _read_leveldata_i32(data, count_offset)
    if count_decoded is None or count_decoded[0] != len(entries):
        return {}
    by_script_id: dict[int, dict] = {}
    for entry in entries:
        script_id = int(entry["scriptId"])
        if script_id in by_script_id:
            return {}
        by_script_id[script_id] = {
            **entry,
            "dictionaryCountOffset": count_offset,
            "dictionaryEntryCount": len(entries),
        }
    return by_script_id


def parse_leveldata_levelscript_brief_dictionary(
    data: bytes,
    candidate_script_ids: set[int],
) -> dict[int, dict]:
    """Return one immutable build-scoped decode of a LevelData dictionary.

    Several independent exact-evidence passes inspect the same LevelData file
    with the same scene script set. Reusing that validated decode avoids
    rescanning every candidate u64 while preserving the fail-closed parser.
    Callers treat the returned mapping as read-only.
    """
    return _parse_leveldata_levelscript_brief_dictionary_cached(
        data,
        tuple(sorted(candidate_script_ids)),
    )


def _looks_like_npc_patrol_data_start(data: bytes, offset: int) -> bool:
    if offset < 0 or offset + 28 > len(data) or data[offset] != 0x09:
        return False
    try:
        move_style = struct.unpack_from("<i", data, offset + 1)[0]
        born_speed = struct.unpack_from("<f", data, offset + 5)[0]
        lead_name_length = struct.unpack_from("<i", data, offset + 12)[0]
        loop_type = struct.unpack_from("<i", data, offset + 16)[0]
        patrol_id = struct.unpack_from("<i", data, offset + 20)[0]
        point_count = struct.unpack_from("<i", data, offset + 24)[0]
    except struct.error:
        return False
    return bool(
        -1 <= move_style <= 64
        and math.isfinite(born_speed)
        and 0.0 <= born_speed <= 10_000.0
        and data[offset + 9] in (0, 1)
        and data[offset + 10] in (0, 1)
        and data[offset + 11] in (0, 1)
        and lead_name_length == 0
        and -1 <= loop_type <= 64
        and patrol_id > 0
        and 0 <= point_count <= 10_000
    )


def parse_leveldata_npc_patrol_data_entry(
    data: bytes,
    offset: int,
    *,
    expected_patrol_id: int | None = None,
) -> dict | None:
    """Parse one current ``NpcPatrolData/9`` row and its typed points.

    The six Story-facing patrol rows use the current fixed-null-string shape
    of the 26-member patrol-point action object.  Variable-string action rows
    are intentionally unsupported here; callers fail closed rather than
    guessing their length.  Every accepted point, action, gait, and position
    is consumed before the returned end offset.
    """
    if not _looks_like_npc_patrol_data_start(data, offset):
        return None
    cursor = offset + 1
    move_style = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    born_override_speed = struct.unpack_from("<f", data, cursor)[0]
    cursor += 4
    enable_born_action = bool(data[cursor])
    enable_born_speed_override = bool(data[cursor + 1])
    forbid_npc_interact = bool(data[cursor + 2])
    cursor += 3
    lead_config_decoded = _read_leveldata_memorypack_string(data, cursor)
    if lead_config_decoded is None:
        return None
    lead_config_name, cursor = lead_config_decoded
    loop_decoded = _read_leveldata_i32(data, cursor)
    if loop_decoded is None:
        return None
    loop_type, cursor = loop_decoded
    patrol_decoded = _read_leveldata_i32(data, cursor)
    if patrol_decoded is None:
        return None
    patrol_id, cursor = patrol_decoded
    if expected_patrol_id is not None and patrol_id != expected_patrol_id:
        return None
    points_decoded = _read_leveldata_count(data, cursor, max_count=10_000)
    if points_decoded is None:
        return None
    point_count, cursor = points_decoded
    points: list[dict] = []
    for point_index in range(max(0, point_count)):
        point_offset = cursor
        if cursor >= len(data) or data[cursor] != 0x03:
            return None
        cursor += 1
        actions_decoded = _read_leveldata_count(data, cursor, max_count=1_000)
        if actions_decoded is None:
            return None
        action_count, cursor = actions_decoded
        action_offsets: list[int] = []
        for _ in range(max(0, action_count)):
            action_offset = cursor
            if cursor + 84 > len(data):
                return None
            action = data[cursor : cursor + 84]
            if (
                action[0] != 0x1A
                or action[1:5] != b"\x00\x00\x00\x00"
                or action[27:31] != b"\xff\xff\xff\xff"
                or action[62] not in (0, 1)
                or action[75] != 0xFF
            ):
                return None
            action_offsets.append(action_offset)
            cursor += 84
        gait_decoded = _read_leveldata_i32(data, cursor)
        if gait_decoded is None:
            return None
        enter_gait, cursor = gait_decoded
        if cursor + 12 > len(data):
            return None
        position = struct.unpack_from("<fff", data, cursor)
        cursor += 12
        if not all(math.isfinite(value) for value in position):
            return None
        points.append({
            "pointIndex": point_index,
            "recordOffset": point_offset,
            "recordEndOffset": cursor,
            "serializedMemberCount": 3,
            "actionCount": max(0, action_count),
            "actionRecordOffsets": action_offsets,
            "actionSerializedMemberCount": 26 if action_offsets else None,
            "enterGait": enter_gait,
            "position": {
                "x": position[0],
                "y": position[1],
                "z": position[2],
            },
        })
    return {
        "recordOffset": offset,
        "recordEndOffset": cursor,
        "serializedMemberCount": 9,
        "patrolId": patrol_id,
        "pointCount": max(0, point_count),
        "points": points,
        "bornMoveStyle": move_style,
        "bornOverrideSpeed": born_override_speed,
        "enableBornAction": enable_born_action,
        "enableBornSpeedOverride": enable_born_speed_override,
        "forbidNpcInteract": forbid_npc_interact,
        "leadConfigSoName": lead_config_name,
        "loopType": loop_type,
        "payloadShape": (
            "npc-patrol-data-9-points-3-fixed-action-26-exact-consume"
        ),
    }


def _find_leveldata_npc_patrol_entries(
    data: bytes,
    patrol_id: int,
) -> list[dict]:
    if patrol_id <= 0:
        return []
    needle = patrol_id.to_bytes(4, "little", signed=True)
    out: list[dict] = []
    for id_offset in _find_exact_bytes_offsets(data, needle):
        entry = parse_leveldata_npc_patrol_data_entry(
            data,
            id_offset - 20,
            expected_patrol_id=patrol_id,
        )
        if entry is None:
            continue
        # Every currently promoted row is followed immediately by another
        # typed NpcPatrolData/9 row.  This proves the returned end is the list
        # boundary, instead of accepting a naked i32 occurrence.
        if not _looks_like_npc_patrol_data_start(
            data,
            int(entry["recordEndOffset"]),
        ):
            continue
        out.append(entry)
    return out


def _npc_patrol_checkpoint_owner_detail(owner: dict) -> dict:
    detail = owner.get("eventDetail") if isinstance(owner, dict) else None
    selector = detail.get("npcEntityFilter") if isinstance(detail, dict) else None
    if not (
        isinstance(detail, dict)
        and isinstance(selector, dict)
        and owner.get("status") == "exact_serialized_control_path"
        and owner.get("headerName") == "LevelEvent_OnNpcPatrolCheckpointReach"
        and owner.get("headerUnionTag") == "0x007c"
        and owner.get("headerSerializedMemberCount") == 21
        and owner.get("nativeHeaderMappingId") == LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID
        and detail.get("type") == "LevelEvent_OnNpcPatrolCheckpointReach"
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        and detail.get("payloadSchemaMappingId")
        == "gameassembly-2026-07-17-memorypack-native-event-fields"
        and detail.get("payloadShape")
        == "dynamic-npc-patrol-checkpoint-fields"
        and detail.get("transport") == "local-npc-patrol-runtime-event"
        and detail.get("serverExchange") is False
        and detail.get("serializedMissionOrQuestId") is False
        and selector.get("logicId") == 0
        and selector.get("slotId") == 0
        and selector.get("useSlotId") is False
        and selector.get("idRef") == -1
        and selector.get("paramSource") == 200
        and str(selector.get("path") or "")
        and isinstance(detail.get("patrolIdFilter"), int)
        and not isinstance(detail.get("patrolIdFilter"), bool)
        and detail.get("patrolIdFilter") > 0
        and isinstance(detail.get("checkpointIndexFilter"), int)
        and not isinstance(detail.get("checkpointIndexFilter"), bool)
        and detail.get("checkpointIndexFilter") >= 0
    ):
        return {}
    return detail


def build_npc_patrol_checkpoint_mission_contexts(
    native_story_playback_index: dict[str, list[dict]],
    mission_flows_payload: dict[str, dict],
    *,
    levelscript_root: Path = LEVELSCRIPT_DIR,
    leveldata_root: Path = LEVELDATA_DIR,
    registry_path: Path = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json",
) -> list[dict]:
    """Join patrol checkpoint playback to one tracked mission shell.

    The relation is deliberately mission-level and non-owning.  A unique
    LevelData property/entity and unique MissionRuntime mission union are
    required, while multiple candidate quests and multiple same-script patrol
    producers remain visible as evidence rather than activation claims.
    """
    try:
        registry_raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    registry_briefs = (
        registry_raw.get("worldEntityBriefInfos")
        if isinstance(registry_raw, dict)
        else None
    )
    if not isinstance(registry_briefs, dict):
        return []

    tracking_by_scene_entity: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for mission_id, flow_payload in mission_flows_payload.items():
        if not isinstance(flow_payload, dict):
            continue
        mission_source = repo_rel(MRA_DIR / f"{mission_id}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            for tracking in quest.get("tracking") or []:
                if not isinstance(tracking, dict):
                    continue
                scene = str(tracking.get("scene") or "")
                local_id = tracking.get("entityLogicId")
                if not (
                    tracking.get("type") == "EntityTrackingInfo"
                    and tracking.get("trackScriptEntity") is False
                    and scene
                    and isinstance(local_id, int)
                    and not isinstance(local_id, bool)
                    and local_id > 0
                    and tracking.get("scriptId") in (0, "0")
                    and tracking.get("entitySlotId") in (0, "0")
                ):
                    continue
                tracking_by_scene_entity[(scene, local_id)].append({
                    "missionId": str(mission_id),
                    "questId": quest_id,
                    "objectiveIndex": tracking.get("objectiveIndex"),
                    "trackingIndex": tracking.get("trackingIndex"),
                    "trackingVisibilityFilter": copy.deepcopy(
                        tracking.get("trackingVisibilityFilter")
                    ),
                    "sourceFile": mission_source,
                })

    scene_cache: dict[str, dict] = {}

    def scene_evidence(level_id: str) -> dict:
        if level_id in scene_cache:
            return scene_cache[level_id]
        levelscript_dir = levelscript_root / level_id
        leveldata_dir = leveldata_root / level_id
        if not levelscript_dir.is_dir() or not leveldata_dir.is_dir():
            scene_cache[level_id] = {}
            return {}
        script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        }
        hosts_by_script: dict[str, list[dict]] = defaultdict(list)
        global_refs: set[int] = set()
        for path in sorted(leveldata_dir.glob("*.json")):
            try:
                data = read_bytes_cached(path)
            except OSError:
                continue
            brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                data,
                script_ids,
            )
            if not brief_dictionary:
                continue
            for script_id, brief in brief_dictionary.items():
                hosts_by_script[str(script_id)].append({
                    "path": path,
                    "sourceFile": repo_rel(path),
                    "data": data,
                    "brief": brief,
                    "dictionaryEntryCount": len(brief_dictionary),
                })
                for raw_ref in brief.get("refWorldEntityIds") or []:
                    try:
                        ref = int(raw_ref)
                    except (TypeError, ValueError):
                        continue
                    if ref > 0:
                        global_refs.add(ref)
        result = {
            "hostsByScript": dict(hosts_by_script),
            "globalRefs": global_refs,
        }
        scene_cache[level_id] = result
        return result

    script_cache: dict[tuple[str, str], dict] = {}

    def matching_producers(
        level_id: str,
        script_id: str,
        alias: str,
        patrol_id: int,
    ) -> list[dict]:
        pair = (level_id, script_id)
        if pair not in script_cache:
            path = levelscript_root / level_id / f"{script_id}.json"
            try:
                data = read_bytes_cached(path)
            except OSError:
                script_cache[pair] = {}
            else:
                records = extract_levelscript_uid_records(data)
                _action_map, membership = levelscript_action_map_membership(
                    data,
                    records,
                )
                ordered = sorted(records, key=lambda row: int(row.get("start") or 0))
                next_starts = {
                    int(record.get("start") or 0): (
                        int(ordered[index + 1].get("start") or len(data))
                        if index + 1 < len(ordered)
                        else len(data)
                    )
                    for index, record in enumerate(ordered)
                }
                decoded_rows: list[dict] = []
                for record in ordered:
                    start = int(record.get("start") or 0)
                    role = str(membership.get(start) or "")
                    if (
                        levelscript_record_semantic_key(record) != (0x031E, 0x0C)
                        or not role.startswith("actionList#")
                    ):
                        continue
                    detail = decode_levelscript_record_payload(
                        data,
                        record,
                        next_start=next_starts.get(start),
                        action_map_role=role,
                    ).get("npcPatrolStart") or {}
                    if detail:
                        decoded_rows.append({
                            "recordOffset": start,
                            "localId": record.get("localId"),
                            "actionMapRole": role,
                            "detail": detail,
                        })
                script_cache[pair] = {
                    "sourceFile": repo_rel(path),
                    "rows": decoded_rows,
                }
        rows = (script_cache.get(pair) or {}).get("rows") or []
        matches: list[dict] = []
        for row in rows:
            detail = row.get("detail") or {}
            target = detail.get("targetNpc") or {}
            if (
                detail.get("payloadShape")
                == "npc-patrol-start-four-field-exact-eof"
                and detail.get("patrolId") == patrol_id
                and target.get("logicId") == 0
                and target.get("slotId") == 0
                and target.get("useSlotId") is False
                and target.get("idRef") == -1
                and target.get("paramSource") == 200
                and target.get("path") == alias
            ):
                matches.append(row)
        return matches

    contexts: list[dict] = []
    for story_key, raw_occurrences in sorted(native_story_playback_index.items()):
        occurrences = [row for row in raw_occurrences or [] if isinstance(row, dict)]
        if not occurrences:
            continue
        occurrence_evidence: list[dict] = []
        resolved_missions: set[str] = set()
        resolved_entities: set[int] = set()
        all_tracking_rows: list[dict] = []
        failed = False
        for occurrence in occurrences:
            owner_matches = [
                (owner, _npc_patrol_checkpoint_owner_detail(owner))
                for owner in occurrence.get("nativeEventOwners") or []
            ]
            owner_matches = [pair for pair in owner_matches if pair[1]]
            if len(owner_matches) != 1:
                failed = True
                break
            owner, detail = owner_matches[0]
            selector = detail["npcEntityFilter"]
            alias = str(selector["path"])
            patrol_id = int(detail["patrolIdFilter"])
            checkpoint_index = int(detail["checkpointIndexFilter"])
            level_id = str(occurrence.get("levelId") or "")
            script_id = str(occurrence.get("scriptId") or "")
            scene = scene_evidence(level_id)
            hosts = list((scene.get("hostsByScript") or {}).get(script_id) or [])
            if len(hosts) != 1:
                failed = True
                break
            host = hosts[0]
            brief = host["brief"]
            property_matches = [
                row
                for row in brief.get("properties") or []
                if isinstance(row, dict) and row.get("name") == alias
            ]
            if len(property_matches) != 1:
                failed = True
                break
            property_value = property_matches[0].get("value")
            atoms = property_value.get("atoms") if isinstance(property_value, dict) else None
            if not (
                isinstance(property_value, dict)
                and property_value.get("valueType") == 13
                and property_value.get("atomCount") == 1
                and isinstance(atoms, list)
                and len(atoms) == 1
                and isinstance(atoms[0], dict)
                and isinstance(atoms[0].get("valueBit64"), int)
                and atoms[0]["valueBit64"] > 0
            ):
                failed = True
                break
            global_entity_id = int(atoms[0]["valueBit64"])
            if str(global_entity_id) not in set(brief.get("refWorldEntityIds") or []):
                failed = True
                break
            registry_brief = registry_briefs.get(str(global_entity_id))
            same_suffix_refs = {
                ref
                for ref in scene.get("globalRefs") or set()
                if ref % GLOBAL_SCRIPT_ID_SCALE
                == global_entity_id % GLOBAL_SCRIPT_ID_SCALE
            }
            if not isinstance(registry_brief, dict) or same_suffix_refs != {global_entity_id}:
                failed = True
                break
            producers = matching_producers(
                level_id,
                script_id,
                alias,
                patrol_id,
            )
            if not producers:
                failed = True
                break
            patrol_rows = _find_leveldata_npc_patrol_entries(
                host["data"],
                patrol_id,
            )
            if len(patrol_rows) != 1:
                failed = True
                break
            patrol_row = patrol_rows[0]
            if not 0 <= checkpoint_index < int(patrol_row["pointCount"]):
                failed = True
                break
            tracking_rows = list(tracking_by_scene_entity.get((
                level_id,
                global_entity_id % GLOBAL_SCRIPT_ID_SCALE,
            )) or [])
            tracking_missions = {
                str(row.get("missionId") or "")
                for row in tracking_rows
                if row.get("missionId")
            }
            if not tracking_rows or len(tracking_missions) != 1:
                failed = True
                break
            mission_id = next(iter(tracking_missions))
            resolved_missions.add(mission_id)
            resolved_entities.add(global_entity_id)
            all_tracking_rows.extend(tracking_rows)
            occurrence_evidence.append({
                "levelId": level_id,
                "scriptId": script_id,
                "sourceFile": str(occurrence.get("sourceFile") or ""),
                "playbackRecordOffset": occurrence.get("recordOffset"),
                "nativeAction": occurrence.get("actionName"),
                "listener": owner,
                "npcEntityPropertyPath": alias,
                "worldEntityId": str(global_entity_id),
                "worldEntityBrief": copy.deepcopy(registry_brief),
                "levelDataSourceFile": host["sourceFile"],
                "levelScriptBriefData": {
                    "scriptId": brief.get("scriptId"),
                    "levelScriptType": brief.get("levelScriptType"),
                    "parentLevelScriptId": brief.get("parentLevelScriptId"),
                    "dictionaryEntryCount": host.get("dictionaryEntryCount"),
                    "propertyName": alias,
                    "propertyValueType": 13,
                    "refWorldEntityIds": brief.get("refWorldEntityIds") or [],
                },
                "patrolId": patrol_id,
                "checkpointIndex": checkpoint_index,
                "patrolData": patrol_row,
                "producerCount": len(producers),
                "producers": producers,
            })
        if (
            failed
            or not occurrence_evidence
            or len(occurrence_evidence) != len(occurrences)
            or len(resolved_missions) != 1
            or len(resolved_entities) != 1
        ):
            continue
        mission_id = next(iter(resolved_missions))
        unique_tracking: dict[tuple, dict] = {}
        for row in all_tracking_rows:
            signature = (
                row.get("missionId"),
                row.get("questId"),
                row.get("objectiveIndex"),
                row.get("trackingIndex"),
            )
            unique_tracking[signature] = row
        tracking_rows = list(unique_tracking.values())
        tracking_rows.sort(key=lambda row: (
            str(row.get("questId") or ""),
            int(row.get("objectiveIndex") or 0),
            int(row.get("trackingIndex") or 0),
        ))
        contexts.append({
            "missionId": mission_id,
            "storyKey": story_key,
            "worldEntityId": str(next(iter(resolved_entities))),
            "candidateQuestIds": sorted({
                str(row.get("questId") or "")
                for row in tracking_rows
                if row.get("questId")
            }),
            "trackingRows": tracking_rows,
            "occurrences": occurrence_evidence,
            "sourceFiles": sorted({
                *[str(row.get("sourceFile") or "") for row in tracking_rows],
                *[
                    str(row.get("sourceFile") or "")
                    for row in occurrence_evidence
                ],
                *[
                    str(row.get("levelDataSourceFile") or "")
                    for row in occurrence_evidence
                ],
                repo_rel(registry_path),
            } - {""}),
        })
    return contexts


def _leader_trigger_world_entity_owner_detail(owner: dict) -> dict:
    """Return one exact local Leader-trigger receiver selector.

    The event payload identifies only a trigger-volume slot in the owning
    LevelScript.  It contains no mission, quest, or world-entity selector, so
    callers must keep any later LevelData/MissionRuntime join contextual and
    non-owning.
    """
    detail = owner.get("eventDetail") if isinstance(owner, dict) else None
    validate_param = detail.get("validateParam") if isinstance(detail, dict) else None
    slot_id = detail.get("triggerSlotIdFilter") if isinstance(detail, dict) else None
    if not (
        isinstance(detail, dict)
        and isinstance(validate_param, dict)
        and owner.get("status") == "exact_serialized_control_path"
        and owner.get("headerName") == "ScriptEvent_OnLeaderEnterTriggerVolume"
        and owner.get("headerUnionTag") == "0x00be"
        and owner.get("headerSerializedMemberCount") == 18
        and owner.get("nativeHeaderMappingId") == LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID
        and detail.get("type") == "ScriptEvent_OnLeaderEnterTriggerVolume"
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        and detail.get("payloadSchemaMappingId")
        == "gameassembly-2026-07-17-memorypack-native-event-fields"
        and detail.get("payloadShape") == "constant-trigger-slot-selector-prefix"
        and detail.get("scriptEventScope") == "owning-level-script"
        and detail.get("triggerTarget") == "SELF"
        and detail.get("targetScriptPresent") is False
        and detail.get("transport") == "local-authored-trigger-volume-event"
        and detail.get("serverExchange") is False
        and detail.get("serializedMissionOrQuestId") is False
        and validate_param.get("constValue") is True
        and isinstance(slot_id, int)
        and not isinstance(slot_id, bool)
        and slot_id > 0
    ):
        return {}
    return detail


def _script_stage_world_entity_owner_detail(owner: dict) -> dict:
    """Return one exact owning-script stage-change receiver selector."""
    detail = owner.get("eventDetail") if isinstance(owner, dict) else None
    validate_param = detail.get("validateParam") if isinstance(detail, dict) else None
    stage_param = (
        detail.get("newStageFilterParam") if isinstance(detail, dict) else None
    )
    stage = detail.get("newStageFilter") if isinstance(detail, dict) else None
    if not (
        isinstance(detail, dict)
        and isinstance(validate_param, dict)
        and isinstance(stage_param, dict)
        and owner.get("status") == "exact_serialized_control_path"
        and owner.get("headerName") == "ScriptEvent_OnScriptStageChanged"
        and owner.get("headerUnionTag") == "0x00c9"
        and owner.get("headerSerializedMemberCount") == 18
        and owner.get("nativeHeaderMappingId") == LEVELSCRIPT_NATIVE_HEADER_MAPPING_ID
        and detail.get("type") == "ScriptEvent_OnScriptStageChanged"
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        and detail.get("payloadSchemaMappingId")
        == "gameassembly-2026-07-17-memorypack-native-event-fields"
        and detail.get("scriptEventScope") == "owning-level-script"
        and detail.get("triggerTarget") == "SELF"
        and detail.get("targetScriptPresent") is False
        and detail.get("transport") == "local-level-script-runtime-event"
        and detail.get("serializedMissionOrQuestId") is False
        and detail.get("newStageFilterPresent") is True
        and detail.get("newStageOutputPresent") is False
        and validate_param.get("constValue") is True
        and isinstance(stage, int)
        and not isinstance(stage, bool)
        and stage >= 0
        and stage_param.get("constValue") == stage
        and stage_param.get("idRef") == -1
        and stage_param.get("paramSource") == 0
        and stage_param.get("path") is None
    ):
        return {}
    return detail


def _exact_local_leader_trigger_volume(
    occurrence: dict,
    owner_detail: dict,
) -> dict:
    """Resolve the selected Leader slot to one fully decoded local volume."""
    source_file = str(occurrence.get("sourceFile") or "")
    script_id = str(occurrence.get("scriptId") or "")
    slot_id = owner_detail.get("triggerSlotIdFilter")
    if not source_file or not script_id or not isinstance(slot_id, int):
        return {}
    summary = _levelscript_binary_summary(source_file, script_id)
    trigger_map = summary.get("triggerVolumesDetails") or {}
    if not (
        trigger_map.get("status") == "present"
        and trigger_map.get("parseStatus") == "decoded"
    ):
        return {}
    matches = [
        volume
        for volume in trigger_map.get("volumes") or []
        if isinstance(volume, dict)
        and volume.get("triggerVolumeType") == "Leader"
        and volume.get("unionTag") == 1
        and volume.get("memberCount") == 8
        and volume.get("keySlotId") == slot_id
        and volume.get("slotId") == slot_id
        and volume.get("waitSrvRes") is False
        and isinstance(volume.get("shapeList"), dict)
        and volume["shapeList"].get("status") == "present"
        and volume["shapeList"].get("parseStatus") == "decoded"
        and bool(volume["shapeList"].get("shapes"))
    ]
    return copy.deepcopy(matches[0]) if len(matches) == 1 else {}


def build_mission_tracked_world_entity_levelscript_contexts(
    native_story_playback_index: dict[str, list[dict]],
    mission_flows_payload: dict[str, dict],
    *,
    receiver_family: str = "leader",
    levelscript_root: Path = LEVELSCRIPT_DIR,
    leveldata_root: Path = LEVELDATA_DIR,
    registry_path: Path = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json",
) -> list[dict]:
    """Join residual Leader-trigger playback to one tracked mission shell.

    This relation is deliberately weaker than a trigger/quest edge. The exact
    receiver proves playback from one authored Leader slot or local stage
    event; a separate exact BriefData/world-entity foreign key and same-scene
    typed ``EntityTrackingInfo`` union prove only that the containing
    LevelScript was authored in one mission's navigation context. Candidate
    quests and their filters remain evidence and are never selected as causes.
    """
    if receiver_family not in {"leader", "stage"}:
        return []
    try:
        registry_raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    registry_briefs = (
        registry_raw.get("worldEntityBriefInfos")
        if isinstance(registry_raw, dict)
        else None
    )
    if not isinstance(registry_briefs, dict):
        return []
    registry_by_local: dict[int, list[dict]] = defaultdict(list)
    for raw_global_id, brief in registry_briefs.items():
        try:
            global_id = int(raw_global_id)
        except (TypeError, ValueError):
            continue
        if (
            global_id <= 0
            or str(global_id) != str(raw_global_id)
            or not isinstance(brief, dict)
        ):
            continue
        registry_by_local[global_id % GLOBAL_SCRIPT_ID_SCALE].append({
            "globalLogicId": global_id,
            **copy.deepcopy(brief),
        })

    tracking_by_scene_entity: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for mission_id, flow_payload in mission_flows_payload.items():
        if not isinstance(flow_payload, dict):
            continue
        mission_source = repo_rel(MRA_DIR / f"{mission_id}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            for tracking in quest.get("tracking") or []:
                if not isinstance(tracking, dict):
                    continue
                scene = str(tracking.get("scene") or "")
                local_id = tracking.get("entityLogicId")
                if not (
                    tracking.get("type") == "EntityTrackingInfo"
                    and tracking.get("trackScriptEntity") is False
                    and scene
                    and isinstance(local_id, int)
                    and not isinstance(local_id, bool)
                    and local_id > 0
                    and tracking.get("scriptId") in (0, "0")
                    and tracking.get("entitySlotId") in (0, "0")
                ):
                    continue
                tracking_by_scene_entity[(scene, local_id)].append({
                    "missionId": str(mission_id),
                    "questId": quest_id,
                    "objectiveIndex": tracking.get("objectiveIndex"),
                    "trackingIndex": tracking.get("trackingIndex"),
                    "trackingVisibilityFilter": copy.deepcopy(
                        tracking.get("trackingVisibilityFilter")
                    ),
                    "sourceFile": mission_source,
                })

    scene_cache: dict[str, dict] = {}

    def scene_evidence(level_id: str) -> dict:
        if level_id in scene_cache:
            return scene_cache[level_id]
        levelscript_dir = levelscript_root / level_id
        leveldata_dir = leveldata_root / level_id
        if not levelscript_dir.is_dir() or not leveldata_dir.is_dir():
            scene_cache[level_id] = {}
            return {}
        script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        }
        hosts_by_script: dict[str, list[dict]] = defaultdict(list)
        global_refs: set[int] = set()
        for path in sorted(leveldata_dir.glob("*.json")):
            try:
                data = read_bytes_cached(path)
            except OSError:
                continue
            brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                data,
                script_ids,
            )
            if not brief_dictionary:
                continue
            for script_id, brief in brief_dictionary.items():
                hosts_by_script[str(script_id)].append({
                    "sourceFile": repo_rel(path),
                    "dictionaryEntryCount": len(brief_dictionary),
                    "briefData": copy.deepcopy(brief),
                })
                for raw_ref in brief.get("refWorldEntityIds") or []:
                    try:
                        ref = int(raw_ref)
                    except (TypeError, ValueError):
                        continue
                    if ref > 0:
                        global_refs.add(ref)
        result = {
            "hostsByScript": dict(hosts_by_script),
            "globalRefs": global_refs,
        }
        scene_cache[level_id] = result
        return result

    contexts: list[dict] = []
    for story_key, raw_occurrences in sorted(native_story_playback_index.items()):
        all_occurrences = [
            row for row in raw_occurrences or [] if isinstance(row, dict)
        ]
        preload_occurrences = [
            copy.deepcopy(row)
            for row in all_occurrences
            if row.get("recordClass") == "preload_cutscene"
            and row.get("actionName") == "PreloadCutsceneAction"
            and row.get("nativeMappingId")
            == (
                "gameassembly-2026-07-11-cr-0x18b9217d0-"
                "actionbase-0x0000-0x0520"
            )
        ]
        occurrences = [
            row
            for row in all_occurrences
            if row not in preload_occurrences
        ]
        if not occurrences:
            continue
        occurrence_evidence: list[dict] = []
        all_tracking_rows: list[dict] = []
        resolved_missions: set[str] = set()
        resolved_entities: set[int] = set()
        failed = False
        for occurrence in occurrences:
            owner_decoder = (
                _leader_trigger_world_entity_owner_detail
                if receiver_family == "leader"
                else _script_stage_world_entity_owner_detail
            )
            owner_matches = [
                (owner, owner_decoder(owner))
                for owner in occurrence.get("nativeEventOwners") or []
            ]
            owner_matches = [pair for pair in owner_matches if pair[1]]
            if len(owner_matches) != 1:
                failed = True
                break
            owner, owner_detail = owner_matches[0]
            trigger_volume = {}
            if receiver_family == "leader":
                trigger_volume = _exact_local_leader_trigger_volume(
                    occurrence,
                    owner_detail,
                )
                if not trigger_volume:
                    failed = True
                    break
            level_id = str(occurrence.get("levelId") or "")
            script_id = str(occurrence.get("scriptId") or "")
            scene = scene_evidence(level_id)
            hosts = list((scene.get("hostsByScript") or {}).get(script_id) or [])
            if len(hosts) != 1:
                failed = True
                break
            host = hosts[0]
            brief = host.get("briefData") or {}
            matched_entities: list[dict] = []
            matched_tracking: list[dict] = []
            entity_candidates: list[dict] = []
            brief_refs = {
                str(raw_ref)
                for raw_ref in brief.get("refWorldEntityIds") or []
            }
            if receiver_family == "leader":
                entity_candidates.extend({
                    "globalLogicId": raw_ref,
                    "resolutionMode": "levelscript_brief_world_entity_ref",
                    "propertyName": "",
                } for raw_ref in sorted(brief_refs, key=int))
            else:
                for prop in brief.get("properties") or []:
                    value = prop.get("value") if isinstance(prop, dict) else None
                    atoms = value.get("atoms") if isinstance(value, dict) else None
                    if not (
                        isinstance(value, dict)
                        and value.get("valueType") == 13
                        and value.get("atomCount") == 1
                        and isinstance(atoms, list)
                        and len(atoms) == 1
                        and isinstance(atoms[0], dict)
                        and isinstance(atoms[0].get("valueBit64"), int)
                        and not isinstance(atoms[0].get("valueBit64"), bool)
                        and atoms[0]["valueBit64"] > 0
                        and str(atoms[0]["valueBit64"]) in brief_refs
                    ):
                        continue
                    entity_candidates.append({
                        "globalLogicId": atoms[0]["valueBit64"],
                        "resolutionMode": "levelscript_brief_type13_property_ref",
                        "propertyName": str(prop.get("name") or ""),
                    })
                try:
                    direct_global_id = int(script_id)
                except (TypeError, ValueError):
                    direct_global_id = 0
                if direct_global_id > 0:
                    entity_candidates.append({
                        "globalLogicId": direct_global_id,
                        "resolutionMode": "levelscript_id_is_world_entity_global_id",
                        "propertyName": "",
                    })
            deduped_candidates: dict[tuple[int, str, str], dict] = {}
            for candidate in entity_candidates:
                try:
                    candidate_id = int(candidate.get("globalLogicId") or 0)
                except (TypeError, ValueError):
                    continue
                signature = (
                    candidate_id,
                    str(candidate.get("resolutionMode") or ""),
                    str(candidate.get("propertyName") or ""),
                )
                deduped_candidates[signature] = candidate
            matched_resolutions: list[dict] = []
            for candidate in deduped_candidates.values():
                raw_global_id = candidate.get("globalLogicId")
                try:
                    global_id = int(raw_global_id)
                except (TypeError, ValueError):
                    continue
                if global_id <= 0 or str(global_id) != str(raw_global_id):
                    continue
                local_id = global_id % GLOBAL_SCRIPT_ID_SCALE
                tracking_rows = list(
                    tracking_by_scene_entity.get((level_id, local_id)) or []
                )
                if not tracking_rows:
                    continue
                registry_rows = registry_by_local.get(local_id) or []
                same_suffix_refs = {
                    ref
                    for ref in scene.get("globalRefs") or set()
                    if ref % GLOBAL_SCRIPT_ID_SCALE == local_id
                }
                requires_brief_ref = (
                    candidate.get("resolutionMode")
                    != "levelscript_id_is_world_entity_global_id"
                )
                if (
                    len(registry_rows) != 1
                    or registry_rows[0].get("globalLogicId") != global_id
                    or (requires_brief_ref and same_suffix_refs != {global_id})
                ):
                    failed = True
                    break
                matched_entity = copy.deepcopy(registry_rows[0])
                matched_entity["resolutionMode"] = candidate.get("resolutionMode")
                matched_entity["propertyName"] = candidate.get("propertyName")
                matched_entities.append(matched_entity)
                matched_tracking.extend(copy.deepcopy(tracking_rows))
                matched_resolutions.append({
                    "globalLogicId": global_id,
                    "localLogicId": local_id,
                    "resolutionMode": candidate.get("resolutionMode"),
                    "propertyName": candidate.get("propertyName"),
                })
            if failed or not matched_entities or not matched_tracking:
                failed = True
                break
            tracking_missions = {
                str(row.get("missionId") or "")
                for row in matched_tracking
                if row.get("missionId")
            }
            if len(tracking_missions) != 1:
                failed = True
                break
            mission_id = next(iter(tracking_missions))
            if mission_id not in mission_flows_payload:
                failed = True
                break
            resolved_missions.add(mission_id)
            resolved_entities.update(
                int(row["globalLogicId"]) for row in matched_entities
            )
            all_tracking_rows.extend(matched_tracking)
            occurrence_evidence.append({
                "levelId": level_id,
                "scriptId": script_id,
                "sourceFile": str(occurrence.get("sourceFile") or ""),
                "playbackRecordOffset": occurrence.get("recordOffset"),
                "nativeAction": occurrence.get("actionName"),
                "listener": copy.deepcopy(owner),
                "triggerSlotId": owner_detail.get("triggerSlotIdFilter"),
                "stageFilter": owner_detail.get("newStageFilter"),
                "triggerVolume": trigger_volume,
                "levelDataSourceFile": str(host.get("sourceFile") or ""),
                "levelScriptBriefData": copy.deepcopy(brief),
                "matchedWorldEntities": matched_entities,
                "entityResolutions": matched_resolutions,
                "trackingRows": matched_tracking,
            })
        if (
            failed
            or not occurrence_evidence
            or len(occurrence_evidence) != len(occurrences)
            or len(resolved_missions) != 1
            or not resolved_entities
        ):
            continue
        resolved_pairs = {
            (
                str(row.get("levelId") or ""),
                str(row.get("scriptId") or ""),
            )
            for row in occurrence_evidence
        }
        if any(
            (
                str(row.get("levelId") or ""),
                str(row.get("scriptId") or ""),
            )
            not in resolved_pairs
            for row in preload_occurrences
        ):
            continue
        unique_tracking: dict[tuple, dict] = {}
        for row in all_tracking_rows:
            signature = (
                row.get("missionId"),
                row.get("questId"),
                row.get("objectiveIndex"),
                row.get("trackingIndex"),
            )
            unique_tracking[signature] = row
        tracking_rows = list(unique_tracking.values())
        tracking_rows.sort(key=lambda row: (
            str(row.get("questId") or ""),
            int(row.get("objectiveIndex") or 0),
            int(row.get("trackingIndex") or 0),
        ))
        mission_id = next(iter(resolved_missions))
        contexts.append({
            "missionId": mission_id,
            "storyKey": story_key,
            "receiverFamily": receiver_family,
            "worldEntityIds": sorted(
                (str(entity_id) for entity_id in resolved_entities),
                key=int,
            ),
            "candidateQuestIds": sorted({
                str(row.get("questId") or "")
                for row in tracking_rows
                if row.get("questId")
            }),
            "trackingRows": tracking_rows,
            "occurrences": occurrence_evidence,
            "preloadOccurrences": preload_occurrences,
            "sourceFiles": sorted({
                repo_rel(registry_path),
                *[str(row.get("sourceFile") or "") for row in tracking_rows],
                *[
                    str(row.get("sourceFile") or "")
                    for row in occurrence_evidence
                ],
                *[
                    str(row.get("sourceFile") or "")
                    for row in preload_occurrences
                ],
                *[
                    str(row.get("levelDataSourceFile") or "")
                    for row in occurrence_evidence
                ],
            } - {""}),
        })
    return contexts


def classify_world_entity_story_receiver_owner(owner: dict) -> str:
    """Return a fail-closed native receiver family for WorldEntity joins.

    The MissionRuntime/BriefData foreign key proves only shared authored
    context.  This predicate independently requires the exact current-build
    serialized receiver-to-action path before a caller may expose that context.
    """
    if not isinstance(owner, dict):
        return ""
    detail = owner.get("eventDetail")
    if not isinstance(detail, dict):
        return ""
    event_name = str(owner.get("headerName") or "")
    if not (
        owner.get("status") == "exact_serialized_control_path"
        and owner.get("nativeHeaderMappingId")
        == "gameassembly-2026-07-11-cr-0x18b9217d0-actionheader"
        and detail.get("payloadSchemaStatus")
        == "exact_current_build_memorypack_fields"
        and detail.get("payloadSchemaMappingId")
        == "gameassembly-2026-07-17-memorypack-native-event-fields"
        and event_name
        and event_name == str(detail.get("type") or "")
    ):
        return ""

    if event_name == "ScriptEvent_OnLeaderEnterTriggerVolume":
        trigger_slot_id = detail.get("triggerSlotIdFilter")
        if (
            owner.get("headerUnionTag") == "0x00be"
            and owner.get("headerSerializedMemberCount") == 18
            and detail.get("scriptEventScope") == "owning-level-script"
            and detail.get("triggerTarget") == "SELF"
            and detail.get("targetScriptPresent") is False
            and isinstance(trigger_slot_id, int)
            and not isinstance(trigger_slot_id, bool)
            and trigger_slot_id > 0
        ):
            return event_name
        return ""

    if event_name == "ScriptEvent_OnScriptStageChanged":
        if (
            owner.get("headerUnionTag") == "0x00c9"
            and owner.get("headerSerializedMemberCount") == 18
            and detail.get("scriptEventScope") == "owning-level-script"
            and detail.get("triggerTarget") == "SELF"
            and detail.get("targetScriptPresent") is False
            and detail.get("newStageFilterPresent") is True
            and detail.get("newStageOutputPresent") is False
            and isinstance(detail.get("newStageFilter"), int)
            and not isinstance(detail.get("newStageFilter"), bool)
        ):
            return event_name
        return ""

    if event_name == "EntityEvent_OnInteractiveStateChanged":
        target_entity = detail.get("targetEntity")
        if (
            owner.get("headerUnionTag") == "0x001e"
            and owner.get("headerSerializedMemberCount") == 20
            and detail.get("entityEventScope") == "specified-entity"
            and detail.get("triggerTarget") == "SPECIFY_ENTITY"
            and isinstance(target_entity, dict)
            and target_entity.get("useSlotId") is True
            and isinstance(target_entity.get("slotId"), int)
            and not isinstance(target_entity.get("slotId"), bool)
            and target_entity.get("slotId") > 0
            and detail.get("targetEntityListPresent") is False
            and detail.get("targetEntityListOutputPresent") is False
        ):
            return event_name
    return ""


def build_leveldata_world_entity_quest_script_context(
    script_pairs: set[tuple[str, str]],
    condition_groups: list[dict],
    condition_refs: list[dict],
    *,
    leveldata_root: Path = LEVELDATA_DIR,
    levelscript_root: Path = LEVELSCRIPT_DIR,
    world_entity_registry_briefs: dict[str, dict] | None = None,
) -> dict[tuple[str, str], dict]:
    """Join quest WorldEntity groups to exact LevelScript BriefData hosts.

    This is a typed foreign-key context edge, not activation causality.  A
    result is unique only when all of these current-build constraints hold:

    * the MissionRuntime condition contributes at least two logic-backed
      WorldEntity ids in one authored group;
    * every id exists in the current `WorldEntityRegistry.worldEntityBriefInfos`;
    * every id is referenced by the target script's fully decoded member-22
      ``LevelScriptBriefData.refWorldEntity`` list;
    * every target BriefData occurrence in the level contains the group;
    * each entity resolves to only that script across all validated LevelData
      dictionaries in the level; and
    * each entity is referenced by only one MissionRuntime mission/quest pair
      across the supplied typed-condition corpus.

    The caller must still prove that the target LevelScript contains the Story
    playback and decide which native event family, if any, owns that action.
    """
    targets_by_level: dict[str, set[str]] = defaultdict(set)
    for raw_level_id, raw_script_id in script_pairs:
        level_id = str(raw_level_id or "").strip()
        script_id = _exact_positive_u64_text(raw_script_id)
        if level_id and script_id:
            targets_by_level[level_id].add(script_id)
    if not targets_by_level:
        return {}

    registry_source_file = repo_rel(
        GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    )
    if world_entity_registry_briefs is None:
        try:
            registry_payload = json.loads(
                (GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json").read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, json.JSONDecodeError):
            return {}
        world_entity_registry_briefs = registry_payload.get(
            "worldEntityBriefInfos"
        )
    if not isinstance(world_entity_registry_briefs, dict):
        return {}
    registry_briefs: dict[str, dict] = {}
    for raw_entity_id, raw_brief in world_entity_registry_briefs.items():
        entity_id = _exact_positive_u64_text(raw_entity_id)
        if entity_id and isinstance(raw_brief, dict):
            registry_briefs[entity_id] = dict(raw_brief)
    if not registry_briefs:
        return {}

    refs_by_entity: dict[tuple[str, str], list[dict]] = defaultdict(list)
    owners_by_entity: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    for raw_ref in condition_refs:
        if not isinstance(raw_ref, dict):
            continue
        mission_id = str(raw_ref.get("missionId") or "").strip()
        quest_id = str(raw_ref.get("questId") or "").strip()
        level_id = str(raw_ref.get("mapId") or "").strip()
        entity_id = _exact_positive_u64_text(raw_ref.get("logicId"))
        if not mission_id or not quest_id or not level_id or not entity_id:
            continue
        key = (level_id, entity_id)
        refs_by_entity[key].append(raw_ref)
        owners_by_entity[key].add((mission_id, quest_id))

    groups_by_level: dict[str, list[dict]] = defaultdict(list)
    for raw_group in condition_groups:
        if not isinstance(raw_group, dict):
            continue
        mission_id = str(raw_group.get("missionId") or "").strip()
        quest_id = str(raw_group.get("questId") or "").strip()
        level_id = str(raw_group.get("mapId") or "").strip()
        entity_ids = [
            entity_id
            for value in raw_group.get("entityLogicIds") or []
            if (entity_id := _exact_positive_u64_text(value))
        ]
        entity_ids = list(dict.fromkeys(entity_ids))
        if not mission_id or not quest_id or not level_id or len(entity_ids) < 2:
            continue
        groups_by_level[level_id].append({
            **raw_group,
            "missionId": mission_id,
            "questId": quest_id,
            "mapId": level_id,
            "entityLogicIds": entity_ids,
        })

    target_hosts: dict[tuple[str, str], list[dict]] = defaultdict(list)
    scripts_by_entity: dict[tuple[str, str], set[str]] = defaultdict(set)
    for level_id, target_script_ids in sorted(targets_by_level.items()):
        leveldata_dir = leveldata_root / level_id
        levelscript_dir = levelscript_root / level_id
        if not leveldata_dir.is_dir() or not levelscript_dir.is_dir():
            continue
        all_level_script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        }
        if not all_level_script_ids:
            continue
        for path in sorted(leveldata_dir.glob("*.json")):
            try:
                brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                    read_bytes_cached(path),
                    all_level_script_ids,
                )
            except OSError:
                continue
            if not brief_dictionary:
                continue
            for numeric_script_id, brief_entry in brief_dictionary.items():
                script_id = str(numeric_script_id)
                for entity_id in brief_entry.get("refWorldEntityIds") or []:
                    if _exact_positive_u64_text(entity_id):
                        scripts_by_entity[(level_id, str(entity_id))].add(script_id)
                if script_id in target_script_ids:
                    target_hosts[(level_id, script_id)].append({
                        "levelId": level_id,
                        "scriptId": script_id,
                        "levelDataFile": repo_rel(path),
                        "dictionaryEntryCount": len(brief_dictionary),
                        "briefData": brief_entry,
                        "encoding": (
                            "leveldata_member22_levelscriptbriefdata_world_entities"
                        ),
                        "nativeSchema": (
                            "LevelData/43.member22:Dictionary<u64,"
                            "LevelScriptBriefData/8>.refWorldEntity"
                        ),
                    })

    out: dict[tuple[str, str], dict] = {}
    for pair, hosts in sorted(target_hosts.items()):
        level_id, script_id = pair
        candidates: list[dict] = []
        for group in groups_by_level.get(level_id) or []:
            entity_ids = list(group.get("entityLogicIds") or [])
            owner = (
                str(group.get("missionId") or ""),
                str(group.get("questId") or ""),
            )
            if any(entity_id not in registry_briefs for entity_id in entity_ids):
                continue
            if any(
                owners_by_entity.get((level_id, entity_id)) != {owner}
                for entity_id in entity_ids
            ):
                continue
            if any(
                scripts_by_entity.get((level_id, entity_id)) != {script_id}
                for entity_id in entity_ids
            ):
                continue
            entity_set = set(entity_ids)
            matching_hosts = [
                host
                for host in hosts
                if entity_set.issubset(set(
                    (host.get("briefData") or {}).get("refWorldEntityIds") or []
                ))
            ]
            if not matching_hosts or len(matching_hosts) != len(hosts):
                continue
            condition_evidence = [
                ref
                for entity_id in entity_ids
                for ref in refs_by_entity.get((level_id, entity_id)) or []
                if (
                    str(ref.get("missionId") or ""),
                    str(ref.get("questId") or ""),
                ) == owner
            ]
            candidates.append({
                "missionId": owner[0],
                "questId": owner[1],
                "levelId": level_id,
                "scriptId": script_id,
                "conditionGroup": group,
                "conditionRefs": condition_evidence,
                "entityLogicIds": entity_ids,
                "worldEntityRegistrySourceFile": registry_source_file,
                "worldEntityRegistryBriefs": [
                    {
                        "entityLogicId": entity_id,
                        **registry_briefs[entity_id],
                    }
                    for entity_id in entity_ids
                ],
                "entityScriptResolutions": [
                    {
                        "entityLogicId": entity_id,
                        "scriptIds": sorted(
                            scripts_by_entity[(level_id, entity_id)],
                            key=int,
                        ),
                        "missionQuestOwners": [
                            {"missionId": mission_id, "questId": quest_id}
                            for mission_id, quest_id in sorted(
                                owners_by_entity[(level_id, entity_id)]
                            )
                        ],
                    }
                    for entity_id in entity_ids
                ],
                "levelDataHosts": matching_hosts,
            })

        deduped: dict[tuple[str, str, tuple[str, ...]], dict] = {}
        for candidate in candidates:
            signature = (
                str(candidate.get("missionId") or ""),
                str(candidate.get("questId") or ""),
                tuple(sorted(candidate.get("entityLogicIds") or [], key=int)),
            )
            deduped.setdefault(signature, candidate)
        candidates = list(deduped.values())
        mission_quest_pairs = sorted({
            (
                str(candidate.get("missionId") or ""),
                str(candidate.get("questId") or ""),
            )
            for candidate in candidates
        })
        if not candidates:
            continue
        out[pair] = {
            "levelId": level_id,
            "scriptId": script_id,
            "status": "unique" if len(mission_quest_pairs) == 1 else "shared",
            "hostMissionIds": sorted({mission for mission, _quest in mission_quest_pairs}),
            "hostQuestIds": sorted({quest for _mission, quest in mission_quest_pairs}),
            "candidates": sorted(
                candidates,
                key=lambda row: (
                    str(row.get("missionId") or ""),
                    str(row.get("questId") or ""),
                    tuple(row.get("entityLogicIds") or []),
                ),
            ),
        }
    return out


def build_leveldata_mission_script_host_index(
    script_pairs: set[tuple[str, str]],
    mission_runtime_ids: set[str],
) -> dict[tuple[str, str], dict]:
    """Resolve exact LevelScript ids to their authored Mission LevelData hosts.

    This is a mission-shell ownership edge only.  It requires the same level,
    an exact MissionRuntime token in the LevelData filename, and the complete
    numeric LevelScript id as a fully validated member-22
    ``LevelScriptBriefData`` dictionary entry.  A pair is promotable only when
    all matching files name one MissionRuntime; shared hosts are retained as
    explicit ambiguity evidence.
    """
    targets_by_level: dict[str, set[str]] = defaultdict(set)
    for raw_level_id, raw_script_id in script_pairs:
        level_id = str(raw_level_id or "").strip()
        script_id = str(raw_script_id or "").strip()
        if not level_id or not script_id.isdigit():
            continue
        numeric_script_id = int(script_id)
        if numeric_script_id <= 0 or numeric_script_id > 0xFFFFFFFFFFFFFFFF:
            continue
        targets_by_level[level_id].add(script_id)

    matches: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for level_id, target_script_ids in sorted(targets_by_level.items()):
        leveldata_dir = LEVELDATA_DIR / level_id
        if not leveldata_dir.is_dir():
            continue
        levelscript_dir = LEVELSCRIPT_DIR / level_id
        all_level_script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        } if levelscript_dir.is_dir() else set()
        if not all_level_script_ids:
            continue
        for path in sorted(leveldata_dir.glob("*.json")):
            mission_id = _parse_leveldata_mission_host_name(
                path.name,
                level_id,
                mission_runtime_ids,
            )
            if not mission_id:
                continue
            try:
                data = read_bytes_cached(path)
            except OSError:
                continue
            brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                data,
                all_level_script_ids,
            )
            if not brief_dictionary:
                continue
            for script_id in target_script_ids:
                brief_entry = brief_dictionary.get(
                    int(script_id),
                )
                if not brief_entry:
                    continue
                brief_entries = [brief_entry]
                matches[(level_id, script_id)].append({
                    "missionId": mission_id,
                    "levelId": level_id,
                    "scriptId": script_id,
                    "levelDataFile": repo_rel(path),
                    "byteOffsets": [
                        int(entry["keyOffset"])
                        for entry in brief_entries
                    ],
                    "entryEndOffsets": [
                        int(entry["endOffset"])
                        for entry in brief_entries
                    ],
                    "briefData": brief_entries,
                    "encoding": "leveldata_member22_levelscriptbriefdata",
                    "nativeSchema": (
                        "LevelData/43.member22:Dictionary<u64,LevelScriptBriefData/8>"
                    ),
                })

    out: dict[tuple[str, str], dict] = {}
    for pair, hosts in sorted(matches.items()):
        host_mission_ids = sorted({
            str(host.get("missionId") or "")
            for host in hosts
            if host.get("missionId")
        })
        out[pair] = {
            "levelId": pair[0],
            "scriptId": pair[1],
            "status": "unique" if len(host_mission_ids) == 1 else "shared",
            "hostMissionIds": host_mission_ids,
            "hosts": sorted(
                hosts,
                key=lambda host: (
                    str(host.get("missionId") or ""),
                    str(host.get("levelDataFile") or ""),
                ),
            ),
        }
    return out


_MISSION_AREA_TRACKING_TYPE = "Beyond.Gameplay.MissionAreaTrackingInfo"
_NPC_PROXY_TRACKING_TYPE = "Beyond.Gameplay.NpcProxyTrackingInfo"


def _exact_positive_u64_text(value: object) -> str:
    if isinstance(value, dict) and "constValue" in value:
        value = value.get("constValue")
    if isinstance(value, bool):
        return ""
    text = str(value or "").strip()
    if not text.isdigit():
        return ""
    numeric = int(text)
    if numeric <= 0 or numeric > 0xFFFFFFFFFFFFFFFF:
        return ""
    return str(numeric)


def build_npc_proxy_segment_script_host_index(
    script_pairs: set[tuple[str, str]],
    tracking_consumers_by_proxy: dict[str, list[dict]],
) -> dict[tuple[str, str], dict]:
    """Scope a LevelScript through one exact authored NPC-proxy segment.

    The original-data join is deliberately narrow:

    ``MissionRuntime NpcProxyTrackingInfo.proxyId`` ->
    ``NpcProxyExDataTable.data[proxyId].missionId`` ->
    ``WorldEntityRegistry.npcProxyBriefInfos[*].segmentIdGlobal`` ->
    an identical LevelScript global id in the tracking row's exact scene.

    The registry dictionary key must equal the repeated ``segmentIdGlobal``
    field, and the typed tracking mission must agree with every nonempty
    NpcProxyEx mission owner for that proxy.  This proves only authored asset-
    segment context.  It does not prove that the tracked NPC, quest, or server
    objective activates any action in the LevelScript.
    """
    targets = {
        (str(level_id or "").strip(), _exact_positive_u64_text(script_id))
        for level_id, script_id in script_pairs
    }
    targets = {pair for pair in targets if pair[0] and pair[1]}
    if not targets or not tracking_consumers_by_proxy:
        return {}

    registry_path = GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    brief_infos = (
        registry.get("npcProxyBriefInfos")
        if isinstance(registry, dict)
        else {}
    )
    if not isinstance(brief_infos, dict):
        return {}

    npc_proxy_ex = _load_npc_proxy_ex()
    proxy_ex_data = (
        npc_proxy_ex.get("data")
        if isinstance(npc_proxy_ex, dict)
        else {}
    )
    if not isinstance(proxy_ex_data, dict):
        return {}

    ex_missions_by_proxy: dict[str, set[str]] = defaultdict(set)
    ex_rows_by_proxy: dict[str, list[dict]] = defaultdict(list)
    for raw_proxy_id, raw_rows in proxy_ex_data.items():
        proxy_id = str(raw_proxy_id or "").strip()
        rows = raw_rows if isinstance(raw_rows, list) else [raw_rows]
        for index, row in enumerate(rows):
            if not proxy_id or not isinstance(row, dict):
                continue
            mission_id = str(row.get("missionId") or "").strip()
            if not mission_id:
                continue
            ex_missions_by_proxy[proxy_id].add(mission_id)
            ex_rows_by_proxy[proxy_id].append({
                "proxyId": proxy_id,
                "missionId": mission_id,
                "rowIndex": index,
                "sourceFile": repo_rel(NPC_PROXY_EX_PATH),
            })

    hosts_by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for raw_key, raw_brief in brief_infos.items():
        if not isinstance(raw_brief, dict):
            continue
        dictionary_segment_id = _exact_positive_u64_text(raw_key)
        segment_id = _exact_positive_u64_text(
            raw_brief.get("segmentIdGlobal")
        )
        proxy_id = str(raw_brief.get("proxyId") or "").strip()
        if (
            not dictionary_segment_id
            or dictionary_segment_id != segment_id
            or not proxy_id
        ):
            continue
        ex_missions = set(ex_missions_by_proxy.get(proxy_id) or set())
        consumers = [
            row
            for row in tracking_consumers_by_proxy.get(proxy_id) or []
            if isinstance(row, dict)
            and str(row.get("type") or "")
            == _NPC_PROXY_TRACKING_TYPE.rsplit(".", 1)[-1]
        ]
        if not ex_missions or not consumers:
            continue
        for level_id, script_id in targets:
            if script_id != segment_id:
                continue
            same_scene_consumers = [
                row
                for row in consumers
                if str(row.get("scene") or "") == level_id
                and str(row.get("missionId") or "") in ex_missions
            ]
            if not same_scene_consumers:
                continue
            consumer_missions = {
                str(row.get("missionId") or "")
                for row in same_scene_consumers
                if row.get("missionId")
            }
            # A proxy with additional authored NpcProxyEx mission owners is a
            # shared segment even when only one current tracking row matched.
            host_missions = sorted(ex_missions | consumer_missions)
            hosts_by_pair[(level_id, script_id)].append({
                "levelId": level_id,
                "scriptId": script_id,
                "segmentIdGlobal": segment_id,
                "proxyId": proxy_id,
                "hostMissionIds": host_missions,
                "trackingConsumers": same_scene_consumers,
                "npcProxyExRows": list(ex_rows_by_proxy.get(proxy_id) or []),
                "registryRow": {
                    "dictionaryKey": dictionary_segment_id,
                    "proxyId": proxy_id,
                    "segmentIdGlobal": segment_id,
                    "sourceFile": repo_rel(registry_path),
                },
                "encoding": "typed_npc_proxy_segment_global_levelscript_id",
                "nativeSchema": (
                    "NpcProxyBriefInfo(proxyId,segmentIdGlobal,position)"
                ),
            })

    out: dict[tuple[str, str], dict] = {}
    for pair, hosts in sorted(hosts_by_pair.items()):
        host_mission_ids = sorted({
            str(mission_id)
            for host in hosts
            for mission_id in host.get("hostMissionIds") or []
            if mission_id
        })
        out[pair] = {
            "levelId": pair[0],
            "scriptId": pair[1],
            "status": "unique" if len(host_mission_ids) == 1 else "shared",
            "hostMissionIds": host_mission_ids,
            "hosts": sorted(
                hosts,
                key=lambda row: (
                    str(row.get("proxyId") or ""),
                    str(row.get("segmentIdGlobal") or ""),
                ),
            ),
        }
    return out


def _collect_typed_mission_area_parent_references() -> dict[str, list[dict]]:
    """Return exact MissionRuntime references grouped by sub-data parent id.

    Only typed ``MissionAreaTrackingInfo`` rows participate. A duplicated
    MissionAreaTable id with conflicting parent ids contributes a conservative
    reference to every authored parent instead of selecting one row.
    """
    table_path = GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
    try:
        table_raw = json.loads(table_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    parent_ids_by_area: dict[str, set[str]] = defaultdict(set)

    def collect_area_rows(value: object) -> None:
        if isinstance(value, dict):
            mission_area_id = str(value.get("missionAreaId") or "").strip()
            parent_id = _exact_positive_u64_text(value.get("subDataParentId"))
            if mission_area_id and parent_id:
                parent_ids_by_area[mission_area_id].add(parent_id)
            for child in value.values():
                collect_area_rows(child)
        elif isinstance(value, list):
            for child in value:
                collect_area_rows(child)

    collect_area_rows(table_raw)
    if not parent_ids_by_area or not MRA_DIR.is_dir():
        return {}

    references_by_parent: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str, str, str, str]] = set()
    for path in sorted(MRA_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        mission_id = str(raw.get("missionId") or path.stem).strip()
        if not mission_id:
            continue

        def collect_tracking_rows(value: object, quest_id: str = "") -> None:
            if isinstance(value, dict):
                next_quest_id = quest_id
                if isinstance(value.get("questId"), str):
                    next_quest_id = str(value["questId"])
                type_name = str(value.get("$type") or "").split(",", 1)[0]
                if type_name == _MISSION_AREA_TRACKING_TYPE:
                    raw_area_id = value.get("missionAreaId")
                    if isinstance(raw_area_id, dict) and "constValue" in raw_area_id:
                        raw_area_id = raw_area_id.get("constValue")
                    mission_area_id = str(raw_area_id or "").strip()
                    for parent_id in sorted(
                        parent_ids_by_area.get(mission_area_id) or []
                    ):
                        signature = (
                            parent_id,
                            mission_id,
                            next_quest_id,
                            mission_area_id,
                            repo_rel(path),
                        )
                        if signature in seen:
                            continue
                        seen.add(signature)
                        references_by_parent[parent_id].append({
                            "missionId": mission_id,
                            "questId": next_quest_id,
                            "missionAreaId": mission_area_id,
                            "subDataParentId": parent_id,
                            "trackingType": type_name,
                            "sourceFile": repo_rel(path),
                        })
                for child in value.values():
                    collect_tracking_rows(child, next_quest_id)
            elif isinstance(value, list):
                for child in value:
                    collect_tracking_rows(child, quest_id)

        collect_tracking_rows(raw)

    return {
        parent_id: sorted(
            references,
            key=lambda row: (
                str(row.get("missionId") or ""),
                str(row.get("questId") or ""),
                str(row.get("missionAreaId") or ""),
                str(row.get("sourceFile") or ""),
            ),
        )
        for parent_id, references in sorted(references_by_parent.items())
    }


def build_leveldata_mission_area_script_host_index(
    script_pairs: set[tuple[str, str]],
) -> dict[tuple[str, str], dict]:
    """Resolve LevelScripts through exact typed MissionArea parent roots.

    The join is:
    ``MissionRuntime MissionAreaTrackingInfo.missionAreaId`` ->
    ``MissionAreaTable.subDataParentId`` -> an identical root u64 in a fully
    validated same-file LevelData member-22 BriefData dictionary. Once that
    root scopes the LevelData asset shell, requested BriefData entries in the
    same dictionary inherit shell context only, never quest chronology.

    Every authored parent-root hit in a file participates. A file, and then a
    requested ``(levelId, scriptId)`` pair across all matching files, is
    promotable only when the complete mission set has exactly one member.
    Shared results remain in the index as explicit ambiguity evidence.
    LevelData filenames never contribute mission identity.
    """
    targets_by_level: dict[str, set[str]] = defaultdict(set)
    for raw_level_id, raw_script_id in script_pairs:
        level_id = str(raw_level_id or "").strip()
        script_id = _exact_positive_u64_text(raw_script_id)
        if level_id and script_id:
            targets_by_level[level_id].add(script_id)
    if not targets_by_level:
        return {}

    references_by_parent = _collect_typed_mission_area_parent_references()
    if not references_by_parent:
        return {}

    matches: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for level_id, target_script_ids in sorted(targets_by_level.items()):
        leveldata_dir = LEVELDATA_DIR / level_id
        levelscript_dir = LEVELSCRIPT_DIR / level_id
        if not leveldata_dir.is_dir() or not levelscript_dir.is_dir():
            continue
        all_level_script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        }
        if not all_level_script_ids:
            continue
        for path in sorted(leveldata_dir.glob("*.json")):
            try:
                brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                    read_bytes_cached(path),
                    all_level_script_ids,
                )
            except OSError:
                continue
            if not brief_dictionary:
                continue
            root_script_ids = sorted(
                str(script_id)
                for script_id in brief_dictionary
                if str(script_id) in references_by_parent
            )
            if not root_script_ids:
                continue
            root_references = [
                reference
                for root_script_id in root_script_ids
                for reference in references_by_parent[root_script_id]
            ]
            host_mission_ids = sorted({
                str(reference.get("missionId") or "")
                for reference in root_references
                if reference.get("missionId")
            })
            if not host_mission_ids:
                continue
            root_evidence = [
                {
                    "subDataParentId": root_script_id,
                    "briefData": brief_dictionary[int(root_script_id)],
                    "missionAreaReferences": list(
                        references_by_parent[root_script_id]
                    ),
                }
                for root_script_id in root_script_ids
            ]
            for script_id in sorted(target_script_ids):
                brief_entry = brief_dictionary.get(int(script_id))
                if not brief_entry:
                    continue
                matches[(level_id, script_id)].append({
                    "levelId": level_id,
                    "scriptId": script_id,
                    "status": (
                        "unique" if len(host_mission_ids) == 1 else "shared"
                    ),
                    "hostMissionIds": host_mission_ids,
                    "levelDataFile": repo_rel(path),
                    "rootScriptIds": root_script_ids,
                    "missionAreaReferences": root_references,
                    "rootEvidence": root_evidence,
                    "briefData": [brief_entry],
                    "encoding": "mission_area_subdata_parent_leveldata_member22",
                    "nativeSchema": (
                        "LevelData/43.member22:Dictionary<u64,LevelScriptBriefData/8>"
                    ),
                })

    out: dict[tuple[str, str], dict] = {}
    for pair, hosts in sorted(matches.items()):
        host_mission_ids = sorted({
            str(mission_id)
            for host in hosts
            for mission_id in host.get("hostMissionIds") or []
            if mission_id
        })
        out[pair] = {
            "levelId": pair[0],
            "scriptId": pair[1],
            "status": "unique" if len(host_mission_ids) == 1 else "shared",
            "hostMissionIds": host_mission_ids,
            "hosts": sorted(
                hosts,
                key=lambda host: str(host.get("levelDataFile") or ""),
            ),
        }
    return out


def build_leveldata_authoritative_scope_script_host_index(
    script_pairs: set[tuple[str, str]],
    mission_runtime_ids: set[str],
    script_scope_references: dict[tuple[str, str], list[dict]],
) -> dict[tuple[str, str], dict]:
    """Scope sibling playback scripts through one complete LevelData shell.

    A validated member-22 dictionary is an authored asset container, not a
    quest sequence.  Exact MissionRuntime condition and EntityTracking script
    references, typed MissionArea parent roots, and exact mission-named
    LevelData files can nevertheless identify that complete container's
    mission shell.  Every authoritative reference anywhere in the dictionary
    participates; a target playback script is promotable only when their union
    names exactly one mission.  The result is shell context only and never a
    quest-to-playback edge.
    """
    targets_by_level: dict[str, set[str]] = defaultdict(set)
    for raw_level_id, raw_script_id in script_pairs:
        level_id = str(raw_level_id or "").strip()
        script_id = _exact_positive_u64_text(raw_script_id)
        if level_id and script_id:
            targets_by_level[level_id].add(script_id)
    if not targets_by_level:
        return {}

    mission_area_references = _collect_typed_mission_area_parent_references()
    matches: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for level_id, target_script_ids in sorted(targets_by_level.items()):
        leveldata_dir = LEVELDATA_DIR / level_id
        levelscript_dir = LEVELSCRIPT_DIR / level_id
        if not leveldata_dir.is_dir() or not levelscript_dir.is_dir():
            continue
        all_level_script_ids = {
            int(path.stem)
            for path in levelscript_dir.glob("*.json")
            if path.stem.isdigit()
        }
        if not all_level_script_ids:
            continue
        for path in sorted(leveldata_dir.glob("*.json")):
            try:
                brief_dictionary = parse_leveldata_levelscript_brief_dictionary(
                    read_bytes_cached(path),
                    all_level_script_ids,
                )
            except OSError:
                continue
            if not brief_dictionary:
                continue

            authoritative_references: list[dict] = []
            filename_mission = _parse_leveldata_mission_host_name(
                path.name,
                level_id,
                mission_runtime_ids,
            )
            if filename_mission:
                authoritative_references.append({
                    "missionId": filename_mission,
                    "questId": "",
                    "scriptId": "",
                    "scopeKind": "exact_mission_leveldata_filename",
                    "sourceFile": repo_rel(path),
                })
            for numeric_script_id in brief_dictionary:
                script_id = str(numeric_script_id)
                for reference in script_scope_references.get(
                    (level_id, script_id),
                    [],
                ):
                    if not isinstance(reference, dict) or not reference.get("missionId"):
                        continue
                    authoritative_references.append({
                        **reference,
                        "scriptId": script_id,
                    })
                for reference in mission_area_references.get(script_id, []):
                    if not isinstance(reference, dict) or not reference.get("missionId"):
                        continue
                    authoritative_references.append({
                        **reference,
                        "scriptId": script_id,
                        "scopeKind": "typed_mission_area_parent_root",
                    })

            deduped_references: list[dict] = []
            seen_references: set[tuple[str, str, str, str, str]] = set()
            for reference in authoritative_references:
                signature = (
                    str(reference.get("missionId") or ""),
                    str(reference.get("questId") or ""),
                    str(reference.get("scriptId") or ""),
                    str(reference.get("scopeKind") or ""),
                    str(reference.get("sourceFile") or ""),
                )
                if not signature[0] or signature in seen_references:
                    continue
                seen_references.add(signature)
                deduped_references.append(reference)
            host_mission_ids = sorted({
                str(reference.get("missionId") or "")
                for reference in deduped_references
                if reference.get("missionId")
            })
            if not host_mission_ids:
                continue

            for script_id in sorted(target_script_ids):
                brief_entry = brief_dictionary.get(int(script_id))
                if not brief_entry:
                    continue
                matches[(level_id, script_id)].append({
                    "levelId": level_id,
                    "scriptId": script_id,
                    "status": (
                        "unique" if len(host_mission_ids) == 1 else "shared"
                    ),
                    "hostMissionIds": host_mission_ids,
                    "levelDataFile": repo_rel(path),
                    "dictionaryEntryCount": len(brief_dictionary),
                    "dictionaryScriptIds": sorted(
                        (str(value) for value in brief_dictionary),
                        key=lambda value: int(value),
                    ),
                    "targetBriefData": brief_entry,
                    "authoritativeReferences": deduped_references,
                    "encoding": "authoritative_scope_validated_leveldata_member22",
                    "nativeSchema": (
                        "LevelData/43.member22:Dictionary<u64,LevelScriptBriefData/8>"
                    ),
                })

    out: dict[tuple[str, str], dict] = {}
    for pair, hosts in sorted(matches.items()):
        host_mission_ids = sorted({
            str(mission_id)
            for host in hosts
            for mission_id in host.get("hostMissionIds") or []
            if mission_id
        })
        out[pair] = {
            "levelId": pair[0],
            "scriptId": pair[1],
            "status": "unique" if len(host_mission_ids) == 1 else "shared",
            "hostMissionIds": host_mission_ids,
            "hosts": sorted(
                hosts,
                key=lambda host: str(host.get("levelDataFile") or ""),
            ),
        }
    return out


def _levelscript_record_texts(record: dict) -> list[str]:
    out: list[str] = []
    for field in ("strings", "plainStrings"):
        for hit in record.get(field) or []:
            text = str(hit.get("text") if isinstance(hit, dict) else hit).strip()
            if text and text not in out:
                out.append(text)
    return out


def _build_levelscript_dialog_exit_text_pairs(level_id: str) -> list[dict]:
    """Decode raw ``OnDialogExit`` header-to-action-chain text pairs.

    This deliberately stops at text membership.  Mission-specific Story-key
    resolution and ambiguity filtering happen in
    ``_build_levelscript_dialog_exit_scene_pairs``.
    """
    if level_id in _LEVELSCRIPT_DIALOG_EXIT_TEXT_PAIR_CACHE:
        return _LEVELSCRIPT_DIALOG_EXIT_TEXT_PAIR_CACHE[level_id]

    out: list[dict] = []
    info = _load_levelscript_binding_data(level_id)
    for file_info in info.get("files") or []:
        file_ref = str(file_info.get("file") or "")
        if not file_ref:
            continue
        try:
            data = read_bytes_cached(ROOT / file_ref)
        except OSError:
            continue
        records = list(file_info.get("records") or [])
        if not records:
            continue
        _action_map, membership = levelscript_action_map_membership(data, records)
        ordered = sorted(records, key=lambda row: int(row.get("start") or 0))
        next_starts = {
            int(record.get("start") or 0): (
                int(ordered[index + 1].get("start") or len(data))
                if index + 1 < len(ordered)
                else len(data)
            )
            for index, record in enumerate(ordered)
        }
        action_buckets: dict[int, list[dict]] = defaultdict(list)
        for record in records:
            local_id = record.get("localId")
            role = str(membership.get(int(record.get("start") or 0)) or "")
            if isinstance(local_id, int) and role.startswith("actionList#"):
                action_buckets[local_id].append(record)

        for header in records:
            if levelscript_record_semantic_key(header) != LEVELSCRIPT_DIALOG_EXIT_TAG:
                continue
            start = int(header.get("start") or 0)
            if not str(membership.get(start) or "").startswith("headerList#"):
                continue
            decoded = decode_levelscript_record_payload(
                data,
                header,
                next_start=next_starts.get(start),
                action_map_role=str(membership.get(start) or ""),
            )
            action_header = decoded.get("actionHeader")
            target_id = action_header.get("nextId") if isinstance(action_header, dict) else None
            target_bucket = action_buckets.get(target_id) if isinstance(target_id, int) else None
            if not target_bucket or len(target_bucket) != 1:
                continue

            chain: list[dict] = []
            seen_ids: set[int] = set()
            current = target_bucket[0]
            while current is not None and len(chain) < 32:
                local_id = current.get("localId")
                if not isinstance(local_id, int) or local_id in seen_ids:
                    break
                seen_ids.add(local_id)
                chain.append(current)
                next_id = current.get("nextId")
                next_bucket = action_buckets.get(next_id) if isinstance(next_id, int) and next_id >= 0 else None
                current = next_bucket[0] if next_bucket and len(next_bucket) == 1 else None

            target_texts: list[str] = []
            target_text_groups: list[dict] = []
            for record in chain:
                record_texts = _levelscript_record_texts(record)
                target_text_groups.append({
                    "localId": record.get("localId"),
                    "texts": record_texts,
                })
                for text in record_texts:
                    if text not in target_texts:
                        target_texts.append(text)
            out.append({
                "levelId": level_id,
                "file": file_ref,
                "sourceScript": file_info.get("fileStem") or "",
                "headerLocalId": header.get("localId"),
                "targetLocalId": target_id,
                "sourceTexts": _levelscript_record_texts(header),
                "targetTexts": target_texts,
                "targetTextGroups": target_text_groups,
            })

    _LEVELSCRIPT_DIALOG_EXIT_TEXT_PAIR_CACHE[level_id] = out
    return out


def _build_levelscript_dialog_exit_scene_pairs(
    level_id: str,
    dialog_key_resolver,
    mission_id: str,
) -> list[dict]:
    """Return unambiguous same-mission Story edges fired on dialog exit."""
    out: list[dict] = []
    seen: set[tuple[str, str, str, int | None]] = set()
    for row in _build_levelscript_dialog_exit_text_pairs(level_id):
        source_keys = {
            payload.get("sceneKey")
            for payload in _annotate_binding_payloads(
                row.get("sourceTexts") or [], dialog_key_resolver, mission_id
            )
            if payload.get("sceneKey")
        }
        if len(source_keys) != 1:
            continue
        source_key = next(iter(source_keys))
        sequence = [source_key]
        target_local_ids: list[int | None] = []
        ambiguous = False
        for group in row.get("targetTextGroups") or []:
            group_keys = {
                payload.get("sceneKey")
                for payload in _annotate_binding_payloads(
                    group.get("texts") or [], dialog_key_resolver, mission_id
                )
                if payload.get("sceneKey")
            }
            if len(group_keys) > 1:
                ambiguous = True
                break
            if len(group_keys) == 1:
                target_key = next(iter(group_keys))
                if target_key != sequence[-1]:
                    sequence.append(target_key)
                    target_local_ids.append(group.get("localId"))
        if ambiguous or len(sequence) < 2:
            continue
        for position, (edge_source, edge_target) in enumerate(zip(sequence, sequence[1:])):
            signature = (
                edge_source,
                edge_target,
                str(row.get("file") or ""),
                row.get("headerLocalId"),
            )
            if signature in seen:
                continue
            seen.add(signature)
            out.append({
                "levelId": level_id,
                "src": edge_source,
                "dst": edge_target,
                "file": row.get("file") or "",
                "sourceScript": row.get("sourceScript") or "",
                "headerLocalId": row.get("headerLocalId"),
                "targetLocalId": target_local_ids[position] if position < len(target_local_ids) else None,
                "position": position,
                "event": "LevelEvent_OnDialogExit",
            })
    return out


def _levelscript_record_for_offset(records: list[dict], offset: int, data_len: int) -> dict | None:
    for index, record in enumerate(records):
        start = int(record.get("start") or 0)
        next_start = int(records[index + 1].get("start") or data_len) if index + 1 < len(records) else data_len
        if start <= offset < next_start:
            return record
    return None


def _compact_levelscript_uid_occurrence(
    *,
    level_id: str,
    file_info: dict,
    uid: str,
    uid_offset: int,
    record: dict | None,
) -> dict:
    row = {
        "levelId": level_id,
        "file": file_info.get("file") or "",
        "sourceScript": file_info.get("fileStem") or "",
        "uid": uid,
        "uidOffset": uid_offset,
    }
    if record:
        row.update({
            "recordUid": record.get("uid") or "",
            "recordStart": int(record.get("start") or 0),
            "recordPayloadStart": int(record.get("payloadStart", record.get("start", 0)) or 0),
            "recordClass": classify_levelscript_record(record),
            "recordCode": f"0x{int(record.get('code') or 0):04x}",
            "recordKind": f"0x{int(record.get('kind') or 0):02x}",
            "localId": record.get("localId"),
            "nextId": record.get("nextId"),
            "recordStrings": [
                hit.get("text")
                for hit in (record.get("strings") or [])[:8]
                if hit.get("text")
            ],
            "recordPlainStrings": [
                hit.get("text")
                for hit in (record.get("plainStrings") or [])[:8]
                if hit.get("text")
            ],
        })
    return row


def _dedupe_uid_record_occurrences(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    order: list[tuple] = []
    for row in rows:
        key = (
            row.get("levelId") or "",
            row.get("file") or "",
            row.get("recordStart", row.get("uidOffset")),
            row.get("recordUid") or "",
        )
        if key not in grouped:
            item = dict(row)
            item["uidOffsets"] = [row.get("uidOffset")]
            grouped[key] = item
            order.append(key)
            continue
        offsets = grouped[key].setdefault("uidOffsets", [])
        if row.get("uidOffset") not in offsets:
            offsets.append(row.get("uidOffset"))
    out = [grouped[key] for key in order]
    for row in out:
        row["uidOffsets"] = [
            offset
            for offset in sorted(row.get("uidOffsets") or [])
            if offset is not None
        ][:8]
        row.pop("uidOffset", None)
    return out


def _build_levelscript_uid_occurrence_index(level_ids: list[str]) -> dict[str, list[dict]]:
    cache_key = tuple(dict.fromkeys(str(level_id or "") for level_id in level_ids if level_id))
    if cache_key in _LEVELSCRIPT_UID_OCCURRENCE_CACHE:
        return _LEVELSCRIPT_UID_OCCURRENCE_CACHE[cache_key]

    uid_index: dict[str, list[dict]] = defaultdict(list)
    for level_id in cache_key:
        info = _load_levelscript_binding_data(level_id)
        for file_info in info.get("files") or []:
            rel_file = str(file_info.get("file") or "")
            if not rel_file:
                continue
            try:
                data = read_bytes_cached(ROOT / rel_file)
            except OSError:
                continue
            records = list(file_info.get("records") or [])
            for match in HEX_UID_RE.finditer(data):
                uid = match.group().decode("ascii")
                offset = match.start()
                record = _levelscript_record_for_offset(records, offset, len(data))
                uid_index[uid].append(
                    _compact_levelscript_uid_occurrence(
                        level_id=level_id,
                        file_info=file_info,
                        uid=uid,
                        uid_offset=offset,
                        record=record,
                    )
                )

    compact_index = {
        uid: _dedupe_uid_record_occurrences(rows)
        for uid, rows in uid_index.items()
    }
    _LEVELSCRIPT_UID_OCCURRENCE_CACHE[cache_key] = compact_index
    return compact_index


def _leveltimeline_pair_relation(source: dict, target: dict) -> str:
    if (
        source.get("levelId") == target.get("levelId")
        and source.get("file") == target.get("file")
    ):
        if (
            source.get("recordStart") is not None
            and source.get("recordStart") == target.get("recordStart")
        ):
            return "same-record"
        return "same-script"
    return "cross-script"


def _compact_leveltimeline_pair(source: dict, target: dict) -> dict:
    relation = _leveltimeline_pair_relation(source, target)
    return {
        "relation": relation,
        "levelId": source.get("levelId") if source.get("levelId") == target.get("levelId") else "",
        "sourceScript": source.get("sourceScript") or "",
        "targetScript": target.get("sourceScript") or "",
        "sourceRecordStart": source.get("recordStart"),
        "targetRecordStart": target.get("recordStart"),
        "sourceRecordClass": source.get("recordClass") or "",
        "targetRecordClass": target.get("recordClass") or "",
        "sourceStrings": list(source.get("recordStrings") or [])[:6],
        "targetStrings": list(target.get("recordStrings") or [])[:6],
        "sourcePlainStrings": list(source.get("recordPlainStrings") or [])[:6],
        "targetPlainStrings": list(target.get("recordPlainStrings") or [])[:6],
    }


def collect_leveltimeline_markers(
    level_ids: list[str],
    *,
    leveldata_files: set[str] | None = None,
) -> list[dict]:
    """Resolve LevelData ``lt:p`` / ``lt:mp`` markers to LevelScript UID records.

    LevelData may contain several named-entry tables in one file; the Story UI
    only needs the best table for search binding, but ordering recovery needs
    every marker-bearing table in authored byte order.
    """
    cache_key = (
        tuple(dict.fromkeys(str(level_id or "") for level_id in level_ids if level_id)),
        tuple(sorted(str(path).replace("\\", "/") for path in (leveldata_files or set()))),
    )
    if cache_key in _LEVELTIMELINE_MARKER_CACHE:
        return _LEVELTIMELINE_MARKER_CACHE[cache_key]

    level_key = cache_key[0]
    allowed_files = set(cache_key[1])
    uid_index = _build_levelscript_uid_occurrence_index(list(level_key))
    markers: list[dict] = []

    for level_id in level_key:
        leveldata_dir = LEVELDATA_DIR / level_id
        if not leveldata_dir.is_dir():
            continue
        for path in sorted(leveldata_dir.glob("*.json")):
            rel_path = repo_rel(path)
            if allowed_files and rel_path not in allowed_files:
                continue
            for table_index, table in enumerate(_load_leveldata_named_tables(path)):
                for entry_index, entry in enumerate(table):
                    text = str(entry.get("text") or "")
                    match = LT_BINDING_RE.match(text)
                    if not match:
                        continue

                    source_uid = match.group("uid1")
                    target_uid = match.group("uid2")
                    source_occurrences = uid_index.get(source_uid, [])
                    target_occurrences = uid_index.get(target_uid, [])
                    pairs = [
                        _compact_leveltimeline_pair(source, target)
                        for source in source_occurrences
                        for target in target_occurrences
                    ]
                    relation_rank = {"same-record": 0, "same-script": 1, "cross-script": 2}
                    pairs.sort(key=lambda pair: (
                        relation_rank.get(str(pair.get("relation") or ""), 9),
                        str(pair.get("sourceScript") or ""),
                        int(pair.get("sourceRecordStart") or 0),
                        str(pair.get("targetScript") or ""),
                        int(pair.get("targetRecordStart") or 0),
                    ))
                    if any(pair.get("relation") == "same-record" for pair in pairs):
                        status = "same-record"
                    elif any(pair.get("relation") == "same-script" for pair in pairs):
                        status = "same-script"
                    elif pairs:
                        status = "cross-script"
                    elif source_occurrences or target_occurrences:
                        status = "partial"
                    else:
                        status = "unresolved"

                    marker = {
                        "levelId": level_id,
                        "file": rel_path,
                        "marker": text,
                        "kind": match.group("kind"),
                        "sourceUid": source_uid,
                        "targetUid": target_uid,
                        "markerKey": entry.get("key"),
                        "tableIndex": table_index,
                        "entryIndex": entry_index,
                        "tableOffset": entry.get("tableOffset"),
                        "entryOffset": entry.get("entryOffset"),
                        "textOffset": entry.get("textOffset"),
                        "status": status,
                        "sourceOccurrences": source_occurrences[:8],
                        "targetOccurrences": target_occurrences[:8],
                        "resolvedPairs": pairs[:8],
                    }
                    markers.append(marker)

    markers.sort(key=lambda row: (
        str(row.get("levelId") or ""),
        str(row.get("file") or ""),
        int(row.get("tableOffset") or 0),
        int(row.get("entryIndex") or 0),
        int(row.get("markerKey") or 0),
        str(row.get("marker") or ""),
    ))
    _LEVELTIMELINE_MARKER_CACHE[cache_key] = markers
    return markers


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
    weak edges, not tight constraints.

    Each entry carries `sequence`, `levelId`, `file`, and the original
    numeric `fileStem` (if the file name was numeric) so a caller can pair
    consecutive files within the same level for cross-file ordering hints."""
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
            "fileStem": file_info.get("fileStem", ""),
        })
    return out


def _build_levelscript_cross_file_scene_pairs(
    level_id: str,
    dialog_key_resolver,
    mission_id: str = "",
) -> list[dict]:
    """Emit cross-file scene-ref pairs for consecutive numeric LS files in
    the same level (`<id>.json`, `<id+1>.json`, ...). Each pair connects the
    last story-key in file N to the first story-key in file N+1. Caller is
    responsible for treating these as weak edges only.

    A single mission scene that lives alone in its LS file does not produce
    any intra-file sequence, but the surrounding files' story refs frequently
    fire in numeric LS-file order, so this complements the per-file rule
    without flattening unrelated parallel-event records into one chain."""
    info = _load_levelscript_binding_data(level_id)
    file_keys: list[tuple[int, str, list[str]]] = []
    for file_info in info["files"]:
        stem = file_info.get("fileStem") or ""
        try:
            stem_int = int(stem)
        except (TypeError, ValueError):
            continue
        scene_keys: list[str] = []
        seen: set[str] = set()
        for hit in file_info.get("stringHits") or []:
            text = hit.get("text") or ""
            scene_key = _resolve_payload_scene_key(text, mission_id, dialog_key_resolver)
            if not scene_key or scene_key in seen:
                continue
            seen.add(scene_key)
            scene_keys.append(scene_key)
        if not scene_keys:
            continue
        file_keys.append((stem_int, file_info["file"], scene_keys))
    file_keys.sort(key=lambda row: row[0])

    out: list[dict] = []
    for idx in range(len(file_keys) - 1):
        a_stem, a_file, a_keys = file_keys[idx]
        b_stem, b_file, b_keys = file_keys[idx + 1]
        if b_stem - a_stem != 1:
            continue
        src = a_keys[-1]
        dst = b_keys[0]
        if not src or not dst or src == dst:
            continue
        out.append({
            "levelId": level_id,
            "src": src,
            "dst": dst,
            "fromFile": a_file,
            "toFile": b_file,
            "fromStem": a_stem,
            "toStem": b_stem,
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

    def quest_area_scene_refs(quest: dict) -> list[str]:
        refs: list[str] = []
        for raw_ref in _quest_area_story_refs(quest):
            resolved = resolve_entry_scene_ref(raw_ref)
            if resolved and resolved not in refs:
                refs.append(resolved)
        return refs

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
            for scene_ref in quest_area_scene_refs(quest):
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

    def quest_area_scene_refs(quest: dict) -> list[str]:
        refs: list[str] = []
        for raw_ref in _quest_area_story_refs(quest):
            resolved = resolve_entry_scene_ref(raw_ref)
            if resolved and resolved not in refs:
                refs.append(resolved)
        return refs

    def quest_scene_refs(quest: dict) -> list[str]:
        refs: list[str] = []
        for field_name in ("dialogs", "cutscenes", "remotecomms", "radios"):
            for raw_ref in quest.get(field_name) or []:
                resolved = resolve_entry_scene_ref(raw_ref)
                if resolved and resolved not in refs:
                    refs.append(resolved)
        for proxy_ref in quest.get("proxyDialogs") or []:
            raw_ref = (
                proxy_ref.get("dialogId")
                if isinstance(proxy_ref, dict)
                else proxy_ref
            )
            resolved = resolve_entry_scene_ref(raw_ref)
            if resolved and resolved not in refs:
                refs.append(resolved)
        for resolved in quest_area_scene_refs(quest):
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
