from __future__ import annotations

from .context import *
from .anime_assets import *
from .level_bindings import *

def _mission_proxy_dialog_ids(mission_id: str, proxy_id: str) -> list[str]:
    if not mission_id or not proxy_id:
        return []
    rows = (_load_npc_proxy_ex().get("data") or {}).get(proxy_id) or []
    dialog_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_mission = str(row.get("missionId") or "")
        if row_mission and row_mission != mission_id:
            continue
        dialog_id = str(row.get("dialogId") or "")
        if dialog_id and dialog_id not in dialog_ids:
            dialog_ids.append(dialog_id)
    return dialog_ids


def _attach_unique_proxy_dialog_refs(mission_id: str, quests_out: list[dict]) -> None:
    proxy_quest_ids: dict[str, set[str]] = defaultdict(set)
    for quest in quests_out:
        quest_id = quest.get("id") or ""
        for proxy_id in quest.get("proxies") or []:
            if proxy_id and quest_id:
                proxy_quest_ids[proxy_id].add(quest_id)

    for quest in quests_out:
        proxy_dialogs: list[dict] = []
        seen_dialogs = set(quest.get("dialogs") or [])
        for proxy_id in quest.get("proxies") or []:
            if not proxy_id or len(proxy_quest_ids.get(proxy_id) or ()) != 1:
                continue
            dialog_ids = _mission_proxy_dialog_ids(mission_id, proxy_id)
            if len(dialog_ids) != 1:
                continue
            dialog_id = dialog_ids[0]
            if dialog_id in seen_dialogs:
                continue
            seen_dialogs.add(dialog_id)
            proxy_dialogs.append({
                "dialogId": dialog_id,
                "npcProxyId": proxy_id,
                "source": "NpcProxyExDataTable.data[*].dialogId",
            })
        if proxy_dialogs:
            quest["proxyDialogs"] = proxy_dialogs


def load_mission_flow(mission_id: str) -> dict | None:
    """Parse MissionRuntimeAsset/<mission>.json into a compact flow payload.

    Returns None when the asset is missing. Cached — the flow data is
    language-independent, so one parse serves every language bundle.
    """
    if mission_id in _MISSION_FLOW_CACHE:
        return _MISSION_FLOW_CACHE[mission_id]
    path = MRA_DIR / f"{mission_id}.json"
    if not path.exists():
        _MISSION_FLOW_CACHE[mission_id] = None
        return None
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _MISSION_FLOW_CACHE[mission_id] = None
        return None

    quests_out: list[dict] = []
    quest_entries_by_id: dict[str, dict] = {}
    for quest in (raw.get("questDic") or {}).values():
        qid = quest.get("questId")
        if not qid:
            continue
        entry: dict = {
            "id": qid,
            "flowIndex": quest.get("flowIndex", 0),
            "prev": list(quest.get("prevQuestIdList") or []),
        }
        quest_story_node = dict(quest)
        quest_story_node.pop("failedCondition", None)
        dialogs = _extract_ref_strings(quest_story_node, _DIALOG_REF_FIELDS)
        if dialogs:
            entry["dialogs"] = dialogs
        cutscenes = [
            canonical
            for cutscene_id in _extract_ref_strings(quest_story_node, _CUTSCENE_REF_FIELDS)
            if (canonical := _canonical_cutscene_key(cutscene_id))
        ]
        if cutscenes:
            entry["cutscenes"] = _unique_preserve(cutscenes)
        remotecomms = _extract_ref_strings(quest_story_node, _REMOTECOMM_REF_FIELDS)
        if remotecomms:
            entry["remotecomms"] = _unique_preserve(remotecomms)
        radios = _extract_ref_strings(quest_story_node, _RADIO_REF_FIELDS)
        if radios:
            entry["radios"] = _unique_preserve(radios)
        tracking = _extract_tracking_hints(quest)
        if tracking:
            resolved_tracking = [_resolve_tracking_hint(hint) for hint in tracking]
            entry["tracking"] = resolved_tracking
            scenes = _unique_preserve(
                [hint["scene"] for hint in resolved_tracking if hint.get("scene")]
            )
            proxies = _unique_preserve(
                [hint["npcProxyId"] for hint in resolved_tracking if hint.get("npcProxyId")]
            )
            if scenes:
                entry["scenes"] = scenes
            if proxies:
                entry["proxies"] = proxies
            pins: list[dict] = []
            seen_pins: set[tuple] = set()
            for hint in resolved_tracking:
                pin = _tracking_hint_pin(hint)
                if not pin:
                    continue
                key = (
                    pin.get("scene", ""),
                    pin.get("sourceType", ""),
                    pin.get("trackingType", ""),
                    pin.get("missionAreaId", ""),
                    pin.get("npcProxyId", ""),
                    round(float(pin["position"]["x"]), 3),
                    round(float(pin["position"]["y"]), 3),
                    round(float(pin["position"]["z"]), 3),
                )
                if key in seen_pins:
                    continue
                seen_pins.add(key)
                pins.append(pin)
            if pins:
                entry["pins"] = pins
        objective_anchors = _extract_objective_anchors(quest)
        if objective_anchors:
            entry["objectiveAnchors"] = objective_anchors
        fc = quest.get("failedCondition")
        if fc:
            flags = _extract_branch_flags(fc)
            eval_str = _combine_eval_string(fc)
            fail_story_refs: list[str] = []
            for field_name in (*_DIALOG_REF_FIELDS, *_CUTSCENE_REF_FIELDS, *_REMOTECOMM_REF_FIELDS, *_RADIO_REF_FIELDS):
                for value in _walk_field_values(fc, field_name):
                    if not isinstance(value, str) or not value:
                        continue
                    if field_name in _CUTSCENE_REF_FIELDS:
                        value = _canonical_cutscene_key(value) or value
                    if value not in fail_story_refs:
                        fail_story_refs.append(value)
            if fail_story_refs:
                entry["failStoryRefs"] = fail_story_refs
            if flags or eval_str or fail_story_refs:
                fail_entry: dict = {"flags": flags}
                if eval_str:
                    fail_entry["eval"] = eval_str
                if fail_story_refs:
                    fail_entry["storyRefs"] = fail_story_refs
                entry["fail"] = fail_entry
        quests_out.append(entry)
        quest_entries_by_id[qid] = entry

    radio_actions_by_quest = _extract_client_action_refs(raw, _RADIO_REF_FIELDS)
    for quest_id, radio_ids in radio_actions_by_quest.items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        entry["radios"] = _unique_preserve([
            *(entry.get("radios") or []),
            *radio_ids,
        ])

    for quest_id, rows in _leveldata_quest_story_refs_for_mission(mission_id).items():
        entry = quest_entries_by_id.get(quest_id)
        if not entry:
            continue
        refs = _unique_preserve(
            str(row.get("storyRef") or "")
            for row in rows
            if row.get("storyRef")
        )
        if not refs:
            continue
        entry["levelDataStoryRefs"] = [
            {
                key: value
                for key, value in row.items()
                if key in (
                    "storyRef",
                    "levelId",
                    "file",
                    "distance",
                    "entity",
                    "fields",
                    "source",
                )
                and value not in (None, "", [], {})
            }
            for row in rows
        ]

    _attach_unique_proxy_dialog_refs(mission_id, quests_out)

    quests_out = _topo_sort_quests(quests_out)

    payload = {
        "level": raw.get("levelId", ""),
        "quests": quests_out,
    }
    _MISSION_FLOW_CACHE[mission_id] = payload
    return payload


__all__ = [name for name in globals() if not name.startswith("__")]
