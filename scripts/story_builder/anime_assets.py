from __future__ import annotations

from .context import *


def _anime_tree_logical_stem(path: Path) -> str:
    return path_id_export_base_stem(path.stem)


def _find_anime_tree_path(filename: str) -> Path:
    requested = Path(filename).stem
    path = _get_anime_tree_path_index().get(requested)
    if path is not None:
        return path
    fallback = (
        ANIME_RESOURCE_DIRS[0]
        if ANIME_RESOURCE_DIRS
        else EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "__missing_resource_dir__"
    )
    return fallback / "__missing_path_id_export__" / filename


def _iter_anime_tree_files(pattern: str):
    seen: set[str] = set()
    for base in ANIME_RESOURCE_DIRS:
        if not base.exists():
            continue
        for path in sorted(base.glob(pattern)):
            if not _anime_tree_logical_stem(path):
                continue
            if path.name in seen:
                continue
            seen.add(path.name)
            yield path


def _get_anime_tree_path_index() -> dict[str, Path]:
    global _ANIME_TREE_PATH_INDEX, _ANIME_TREE_SORTED_STEMS
    if _ANIME_TREE_PATH_INDEX is None:
        index: dict[str, Path] = {}
        for path in _iter_anime_tree_files("*.json"):
            if path.name.endswith("_extra_config.json"):
                continue
            logical_stem = _anime_tree_logical_stem(path)
            if logical_stem:
                index.setdefault(logical_stem, path)
        _ANIME_TREE_PATH_INDEX = index
        _ANIME_TREE_SORTED_STEMS = sorted(index.keys())
    return _ANIME_TREE_PATH_INDEX


def _iter_sorted_stems_with_prefix(sorted_stems: list[str], prefix: str):
    index = bisect_left(sorted_stems, prefix)
    while index < len(sorted_stems):
        stem = sorted_stems[index]
        if not stem.startswith(prefix):
            break
        yield stem
        index += 1


def _iter_related_dialog_tree_paths(conv_key: str):
    seen: set[str] = set()
    exact_stems = [conv_key]
    prefix_stems = [conv_key]
    if conv_key.startswith("dlg_"):
        bare = conv_key[4:]
        if bare not in exact_stems:
            exact_stems.append(bare)
        if bare not in prefix_stems:
            prefix_stems.append(bare)
        if bare.startswith("blackbox_"):
            gpl = f"dlg_gpl_{bare}"
            if gpl not in exact_stems:
                exact_stems.append(gpl)
            if gpl not in prefix_stems:
                prefix_stems.append(gpl)

    path_index = _get_anime_tree_path_index()
    for stem in exact_stems:
        path = path_index.get(stem)
        if path is None:
            continue
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        yield path
    all_stems = _ANIME_TREE_SORTED_STEMS or sorted(path_index.keys())
    for stem in prefix_stems:
        prefix = f"{stem}_"
        for candidate_stem in _iter_sorted_stems_with_prefix(all_stems, prefix):
            path = path_index[candidate_stem]
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path


def _load_anime_resource_payload(path: Path):
    try:
        with path.open(encoding="utf-8-sig") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return payload

    script = payload.get("m_Script")
    if not isinstance(script, str) or not script:
        return payload

    try:
        decoded = base64.b64decode(script)
        decoded_text = decoded.decode("utf-8-sig")
        decoded_payload = json.loads(decoded_text)
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return payload

    if isinstance(decoded_payload, dict):
        asset_name = str(payload.get("Name") or payload.get("m_Name") or "").strip()
        if asset_name:
            decoded_payload = dict(decoded_payload)
            decoded_payload["_assetName"] = asset_name

    return decoded_payload


def _dialog_tree_semantic_signature(record: dict) -> str:
    """Return a stable signature for DialogTree evidence, ignoring asset aliases."""

    ignored_keys = {"assetName", "file", "sourceKey"}

    def scrub(value):
        if isinstance(value, dict):
            return {
                key: scrub(value[key])
                for key in sorted(value)
                if key not in ignored_keys
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return json.dumps(
        scrub(record),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _extract_ref_strings(node, field_names: tuple[str, ...]) -> list[str]:
    return unique_strings(
        value
        for field_name in field_names
        for value in _walk_const_values(node, field_name)
    )


_EMBEDDED_STORY_REF_RE = re.compile(
    r"(?:dlg|sns|cutscene|black|remotecomm|radio)_[A-Za-z0-9_]+"
)
_LEVELDATA_STORY_REF_RE = re.compile(
    rb"\b(?:dlg|sns|cutscene|black|remotecomm|radio)_[A-Za-z0-9_]{2,120}"
)
_LEVELDATA_QUEST_ID_RE = re.compile(
    rb"\b[A-Za-z0-9][A-Za-z0-9_]*_q#[A-Za-z0-9_]+\b"
)
_LEVELDATA_ASCII_RE = re.compile(rb"[ -~]{3,}")
_LEVELDATA_STORY_MISSION_RE = re.compile(r"^([a-z]+\d+m\d+(?:d\d+)?)(?:_|$)", re.I)
_LEVELDATA_PRIORITY_STORY_TYPES = {"e", "a", "gm", "c"}


def _extract_embedded_story_refs(text: str) -> list[str]:
    value = str(text or "")
    if not value:
        return []
    return _unique_preserve(match.group(0) for match in _EMBEDDED_STORY_REF_RE.finditer(value))


def _mission_from_story_ref(ref: str) -> str:
    value = str(ref or "").strip()
    if value.startswith("misc_"):
        value = value[5:]
    for prefix in ("dlg_", "sns_", "cutscene_", "black_", "remotecomm_", "radio_"):
        if not value.startswith(prefix):
            continue
        rest = value[len(prefix):]
        if match := _LEVELDATA_STORY_MISSION_RE.match(rest):
            return match.group(1)
    return ""


def _mission_parent_id(mission_id: str) -> str:
    return re.sub(r"d\d+$", "", str(mission_id or ""))


def _mission_story_type(mission_id: str) -> str:
    match = re.match(r"^([a-z]+)", str(mission_id or "").lower())
    return match.group(1) if match else ""


def _quest_id_mission(quest_id: str) -> str:
    value = str(quest_id or "")
    return value.split("_q#", 1)[0] if "_q#" in value else ""


def _leveldata_story_ref_matches_quest(story_ref: str, quest_id: str) -> bool:
    story_mission = _mission_from_story_ref(story_ref)
    quest_mission = _quest_id_mission(quest_id)
    if not story_mission or not quest_mission:
        return False
    if (
        _mission_story_type(story_mission) not in _LEVELDATA_PRIORITY_STORY_TYPES
        and _mission_story_type(quest_mission) not in _LEVELDATA_PRIORITY_STORY_TYPES
    ):
        return False
    return (
        story_mission == quest_mission
        or story_mission == _mission_parent_id(quest_mission)
        or _mission_parent_id(story_mission) == _mission_parent_id(quest_mission)
    )


def _leveldata_hit_distance(story_start: int, story_end: int, quest_start: int, quest_end: int) -> int:
    if quest_start <= story_start <= quest_end:
        return 0
    return min(abs(quest_start - story_start), abs(quest_end - story_end))


def _leveldata_context_strings(raw: bytes, start: int, end: int) -> list[str]:
    context = raw[max(0, start - 220) : min(len(raw), end + 220)]
    return [
        match.group().decode("ascii", "ignore").strip()
        for match in _LEVELDATA_ASCII_RE.finditer(context)
    ]


def _leveldata_quest_story_refs_by_mission() -> dict[str, dict[str, list[dict]]]:
    global _LEVELDATA_QUEST_STORY_REF_CACHE
    if _LEVELDATA_QUEST_STORY_REF_CACHE is not None:
        return _LEVELDATA_QUEST_STORY_REF_CACHE

    by_mission: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, str, str, str]] = set()
    if not LEVELDATA_DIR.is_dir():
        _LEVELDATA_QUEST_STORY_REF_CACHE = {}
        return _LEVELDATA_QUEST_STORY_REF_CACHE

    source_fields = {
        "require_quest",
        "radio_await_start",
        "radio_escape_start",
        "use_level_event_click",
        "level_event_id_click",
        "click_option_name_list",
        "lang_int_trigger_dialog_option",
        "isFinished",
    }

    for path in sorted(LEVELDATA_DIR.rglob("*.json")):
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        story_hits = [
            (match.start(), match.end(), match.group().decode("ascii", "ignore"))
            for match in _LEVELDATA_STORY_REF_RE.finditer(raw)
        ]
        if not story_hits:
            continue
        quest_hits = [
            (match.start(), match.end(), match.group().decode("ascii", "ignore"))
            for match in _LEVELDATA_QUEST_ID_RE.finditer(raw)
        ]
        if not quest_hits:
            continue
        file_ref = repo_rel(path)
        for story_start, story_end, story_ref in story_hits:
            context_start = max(0, story_start - 220)
            context_end = min(len(raw), story_end + 220)
            candidates = [
                (quest_start, quest_end, quest_id)
                for quest_start, quest_end, quest_id in quest_hits
                if context_start <= quest_start < context_end
                and _leveldata_story_ref_matches_quest(story_ref, quest_id)
            ]
            if not candidates:
                continue
            quest_start, quest_end, quest_id = candidates[-1]
            quest_mission = _quest_id_mission(quest_id)
            if not quest_mission:
                continue
            signature = (quest_mission, quest_id, story_ref, file_ref)
            if signature in seen:
                continue
            seen.add(signature)

            strings = _leveldata_context_strings(raw, min(story_start, quest_start), max(story_end, quest_end))
            fields = _unique_preserve(
                text
                for text in strings
                if (
                    text in source_fields
                    or text.startswith((
                        "dlg_",
                        "sns_",
                        "cutscene_",
                        "black_",
                        "remotecomm_",
                        "radio_",
                    ))
                )
            )
            entity = next((text for text in reversed(strings) if text.startswith("int_")), "")
            row = {
                "storyRef": story_ref,
                "questId": quest_id,
                "levelId": path.parent.name,
                "file": file_ref,
                "distance": _leveldata_hit_distance(
                    story_start,
                    story_end,
                    quest_start,
                    quest_end,
                ),
                "storyOffset": story_start,
                "questOffset": quest_start,
                "source": "LevelData quest/story byte-string context",
            }
            if entity:
                row["entity"] = entity
            if fields:
                row["fields"] = fields[:12]
            by_mission[quest_mission][quest_id].append(row)

    _LEVELDATA_QUEST_STORY_REF_CACHE = {
        mission: {
            quest_id: sorted(
                rows,
                key=lambda row: (
                    int(row.get("storyOffset") or 0),
                    str(row.get("storyRef") or ""),
                ),
            )
            for quest_id, rows in sorted(quests.items())
        }
        for mission, quests in sorted(by_mission.items())
    }
    return _LEVELDATA_QUEST_STORY_REF_CACHE


def _leveldata_quest_story_refs_for_mission(mission_id: str) -> dict[str, list[dict]]:
    return _leveldata_quest_story_refs_by_mission().get(str(mission_id or ""), {})


def _quest_area_story_refs(quest: dict) -> list[str]:
    refs: list[str] = []
    for anchor in quest.get("objectiveAnchors") or []:
        for ref in anchor.get("areaStoryRefs") or []:
            if ref and ref not in refs:
                refs.append(ref)
        for leaf in anchor.get("conditionLeaves") or []:
            for ref in leaf.get("areaStoryRefs") or []:
                if ref and ref not in refs:
                    refs.append(ref)
    return refs


def _extract_client_action_refs(raw: dict, field_names: tuple[str, ...]) -> dict[str, list[str]]:
    action_list = (((raw.get("actionMapRaw") or {}).get("dataMap") or {}).get("actionList") or [])
    actions_by_id: dict[int, dict] = {}
    for action in action_list:
        action_id = action.get("_ID")
        if not isinstance(action_id, int):
            continue
        actions_by_id[action_id] = action

    def action_chain_refs(action_id: int) -> list[str]:
        refs: list[str] = []
        seen: set[int] = set()
        current = action_id
        while isinstance(current, int) and current in actions_by_id and current not in seen:
            seen.add(current)
            action = actions_by_id[current]
            for ref in _extract_ref_strings(action, field_names):
                if ref not in refs:
                    refs.append(ref)
            next_id = action.get("_nextID")
            if not isinstance(next_id, int) or next_id < 0:
                break
            current = next_id
        return refs

    out: dict[str, list[str]] = {}
    for key_row, action_id in zip(raw.get("clientActionMapKey") or [], raw.get("clientActionMapValue") or []):
        if not isinstance(key_row, dict) or not isinstance(action_id, int):
            continue
        quest_id = key_row.get("questId")
        if not isinstance(quest_id, str) or not quest_id:
            continue
        refs = action_chain_refs(action_id)
        if not refs:
            continue
        bucket = out.setdefault(quest_id, [])
        for ref in refs:
            if ref not in bucket:
                bucket.append(ref)
    return out


def _condition_short_type(full_type: str) -> str:
    # "Beyond.Gameplay.CheckMissionIntProperty, Gameplay.Beyond" -> "CheckMissionIntProperty"
    head = full_type.split(",", 1)[0]
    return head.rsplit(".", 1)[-1] if head else ""


def _extract_branch_flags(cond) -> list[dict]:
    if not isinstance(cond, dict):
        return []
    out: list[dict] = []
    t = cond.get("$type", "")
    short = _condition_short_type(t)
    if short == "CombineCondition":
        for sub in cond.get("subConditions", []) or []:
            out.extend(_extract_branch_flags(sub))
        return out
    if short == "CheckMissionIntProperty":
        out.append({
            "type": short,
            "key": (cond.get("_key") or {}).get("constValue"),
            "cmp": (cond.get("_comparer") or {}).get("constValue"),
            "val": (cond.get("_compareValue") or {}).get("constValue"),
        })
        return out
    if short == "CheckQuestState":
        out.append({
            "type": short,
            "key": (cond.get("_questId") or {}).get("constValue"),
            "cmp": (cond.get("_comparer") or {}).get("constValue"),
            "val": (cond.get("_targetQuestState") or {}).get("constValue"),
        })
        return out
    if short:
        # Unknown leaf — surface the type so the UI can still hint at it.
        out.append({"type": short})
    return out


def _combine_eval_string(cond) -> str:
    if not isinstance(cond, dict):
        return ""
    if _condition_short_type(cond.get("$type", "")) == "CombineCondition":
        return cond.get("conditionEvalString", "") or ""
    return ""


def _natural_key(value: str) -> tuple:
    parts = re.findall(r"\d+|\D+", value or "")
    out = []
    for part in parts:
        if part.isdigit():
            out.append((0, int(part)))
        else:
            out.append((1, part))
    return tuple(out)


def _quest_sort_key(q: dict) -> tuple:
    tail = (q.get("id") or "").split("#")[-1]
    return (q.get("flowIndex", 10**9), _natural_key(tail), q.get("id") or "")


def _extract_tracking_hints(quest) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for obj in (quest.get("objectiveList") or []):
        for info in (obj.get("trackingInfoList") or []):
            if not isinstance(info, dict):
                continue
            hint: dict = {}
            typ = _condition_short_type(info.get("$type", ""))
            if typ:
                hint["type"] = typ
            scene_id = info.get("sceneId")
            if isinstance(scene_id, str) and scene_id:
                hint["scene"] = scene_id
            npc_proxy_id = info.get("npcProxyId")
            if isinstance(npc_proxy_id, str) and npc_proxy_id:
                hint["npcProxyId"] = npc_proxy_id
            mission_area_id = info.get("missionAreaId")
            if isinstance(mission_area_id, str) and mission_area_id:
                hint["missionAreaId"] = mission_area_id
                area_story_refs = _extract_embedded_story_refs(mission_area_id)
                if area_story_refs:
                    hint["areaStoryRefs"] = area_story_refs
            jump_id = info.get("jumpId")
            if isinstance(jump_id, str) and jump_id:
                hint["jumpId"] = jump_id
            tracking_pos = info.get("trackingPos")
            if isinstance(tracking_pos, dict):
                try:
                    hint["trackingPos"] = {
                        "x": float(tracking_pos.get("x", 0.0)),
                        "y": float(tracking_pos.get("y", 0.0)),
                        "z": float(tracking_pos.get("z", 0.0)),
                    }
                except (TypeError, ValueError):
                    pass
            if not hint:
                continue
            key = (
                hint.get("type", ""),
                hint.get("scene", ""),
                hint.get("npcProxyId", ""),
                hint.get("missionAreaId", ""),
                hint.get("jumpId", ""),
                tuple(
                    round(float(hint["trackingPos"][axis]), 3)
                    for axis in ("x", "y", "z")
                ) if hint.get("trackingPos") else (),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(hint)
    return out


def _extract_objective_tracking_hints(obj: dict) -> list[dict]:
    quest_like = {"objectiveList": [obj]}
    return _extract_tracking_hints(quest_like)


def _extract_condition_anchor_leaves(cond) -> list[dict]:
    if not isinstance(cond, dict):
        return []
    short = _condition_short_type(cond.get("$type", ""))
    if short == "CombineCondition":
        out: list[dict] = []
        for sub in cond.get("subConditions") or []:
            out.extend(_extract_condition_anchor_leaves(sub))
        return out

    leaf: dict = {"type": short or "Unknown"}
    story_refs = _extract_ref_strings(
        cond,
        (*_DIALOG_REF_FIELDS, *_CUTSCENE_REF_FIELDS, *_REMOTECOMM_REF_FIELDS, *_RADIO_REF_FIELDS),
    )
    if story_refs:
        leaf["storyRefs"] = story_refs

    area_story_refs = _unique_preserve(
        ref
        for field_name in ("_areaId", "areaId", "missionAreaId")
        for value in _walk_field_values(cond, field_name)
        if isinstance(value, str)
        for ref in _extract_embedded_story_refs(value)
    )
    if area_story_refs:
        leaf["areaStoryRefs"] = area_story_refs

    level_ids = unique_strings(
        value
        for field_name in ("_sceneId", "sceneId", "_levelId", "levelId", "_mapId", "mapId")
        for value in _walk_field_values(cond, field_name)
    )
    if level_ids:
        leaf["sceneIds"] = level_ids

    script_ids: list[int] = []
    for field_name in ("_scriptId", "scriptId"):
        for value in _walk_field_values(cond, field_name):
            script_id = None
            if isinstance(value, dict):
                script_id = value.get("scriptId")
            elif isinstance(value, int):
                script_id = value
            if isinstance(script_id, int) and script_id > 0 and script_id not in script_ids:
                script_ids.append(script_id)
    if script_ids:
        leaf["scriptIds"] = script_ids

    logic_ids: list[int] = []
    for value in _walk_field_values(cond, "_entityId"):
        if isinstance(value, dict):
            logic_id = value.get("logicId")
            if isinstance(logic_id, int) and logic_id not in logic_ids:
                logic_ids.append(logic_id)
    if logic_ids:
        leaf["logicIds"] = logic_ids

    quest_refs: list[dict] = []
    quest_ids = unique_strings(_walk_field_values(cond, "_questId"))
    target_states = list(_walk_field_values(cond, "_targetQuestState"))
    target_state = target_states[0] if target_states else None
    for quest_id in quest_ids:
        quest_ref = {"questId": quest_id}
        if isinstance(target_state, (int, float, str)):
            quest_ref["targetState"] = target_state
        quest_refs.append(quest_ref)
    if quest_refs:
        leaf["questStateRefs"] = quest_refs

    compare_keys = unique_strings(_walk_field_values(cond, "_key"))
    if compare_keys:
        leaf["keys"] = compare_keys
    compare_values = list(_walk_field_values(cond, "_compareValue"))
    if compare_values:
        leaf["compareValues"] = _unique_preserve(compare_values)
    finish_ids = list(_walk_field_values(cond, "_finishId"))
    if finish_ids:
        leaf["finishIds"] = _unique_preserve(finish_ids)
    trigger_slot_ids = list(_walk_field_values(cond, "_triggerSlotIdOutput"))
    if trigger_slot_ids:
        leaf["triggerSlotIds"] = _unique_preserve(trigger_slot_ids)
    succeed_ids = list(_walk_field_values(cond, "_succeedId"))
    if succeed_ids:
        leaf["succeedIds"] = _unique_preserve(succeed_ids)
    new_states = list(_walk_field_values(cond, "_newState"))
    if new_states:
        leaf["newStates"] = _unique_preserve(new_states)
    old_states = list(_walk_field_values(cond, "_oldState"))
    if old_states:
        leaf["oldStates"] = _unique_preserve(old_states)
    event_trigger_ids = list(_walk_field_values(cond, "level_event_id_trigger"))
    if event_trigger_ids:
        leaf["eventTriggerIds"] = _unique_preserve(event_trigger_ids)

    return [leaf]


def _extract_objective_anchors(quest: dict) -> list[dict]:
    out: list[dict] = []
    for index, obj in enumerate(quest.get("objectiveList") or [], start=1):
        if not isinstance(obj, dict):
            continue
        tracking = [_resolve_tracking_hint(hint) for hint in _extract_objective_tracking_hints(obj)]
        leaves = _extract_condition_anchor_leaves(obj.get("condition"))

        anchor: dict = {
            "index": index,
            "tracking": tracking,
            "conditionLeaves": leaves,
        }
        description = obj.get("description")
        if isinstance(description, dict) and description.get("key"):
            anchor["descriptionKey"] = str(description["key"])
        multiple_description = [
            str(item.get("key"))
            for item in (obj.get("multipleDescription") or [])
            if isinstance(item, dict) and item.get("key")
        ]
        if multiple_description:
            anchor["multipleDescriptionKeys"] = _unique_preserve(multiple_description)
        if obj.get("muteTrack"):
            anchor["muteTrack"] = True
        if obj.get("isBlockObjective"):
            anchor["isBlockObjective"] = True

        condition_types = _unique_preserve([
            str(leaf.get("type") or "")
            for leaf in leaves
            if leaf.get("type")
        ])
        if condition_types:
            anchor["conditionTypes"] = condition_types

        tracking_types = _unique_preserve([
            str(hint.get("type") or "")
            for hint in tracking
            if hint.get("type")
        ])
        if tracking_types:
            anchor["trackingTypes"] = tracking_types

        story_refs = _unique_preserve([
            str(ref)
            for leaf in leaves
            for ref in (leaf.get("storyRefs") or [])
            if ref
        ])
        if story_refs:
            anchor["storyRefs"] = story_refs

        area_story_refs = _unique_preserve([
            str(ref)
            for ref in (
                [ref for leaf in leaves for ref in (leaf.get("areaStoryRefs") or [])]
                + [ref for hint in tracking for ref in (hint.get("areaStoryRefs") or [])]
            )
            if ref
        ])
        if area_story_refs:
            anchor["areaStoryRefs"] = area_story_refs

        scene_ids = _unique_preserve([
            str(scene_id)
            for value in (
                [scene_id for leaf in leaves for scene_id in (leaf.get("sceneIds") or [])]
                + [hint.get("scene") for hint in tracking if hint.get("scene")]
            )
            if value
            for scene_id in [value]
        ])
        if scene_ids:
            anchor["sceneIds"] = scene_ids

        mission_area_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("missionAreaId") for hint in tracking if hint.get("missionAreaId")])
            if value
        ])
        if mission_area_ids:
            anchor["missionAreaIds"] = mission_area_ids

        npc_proxy_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("npcProxyId") for hint in tracking if hint.get("npcProxyId")])
            if value
        ])
        if npc_proxy_ids:
            anchor["npcProxyIds"] = npc_proxy_ids

        jump_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("jumpId") for hint in tracking if hint.get("jumpId")])
            if value
        ])
        if jump_ids:
            anchor["jumpIds"] = jump_ids

        script_ids = _unique_preserve([
            int(value)
            for leaf in leaves
            for value in (leaf.get("scriptIds") or [])
            if isinstance(value, int)
        ])
        if script_ids:
            anchor["scriptIds"] = script_ids

        logic_ids = _unique_preserve([
            int(value)
            for leaf in leaves
            for value in (leaf.get("logicIds") or [])
            if isinstance(value, int)
        ])
        if logic_ids:
            anchor["logicIds"] = logic_ids

        quest_state_refs = []
        seen_quest_state_refs: set[tuple[str, str]] = set()
        for leaf in leaves:
            for row in (leaf.get("questStateRefs") or []):
                quest_id = str(row.get("questId") or "")
                if not quest_id:
                    continue
                state_value = row.get("targetState")
                dedup = (quest_id, str(state_value))
                if dedup in seen_quest_state_refs:
                    continue
                seen_quest_state_refs.add(dedup)
                quest_ref = {"questId": quest_id}
                if state_value is not None:
                    quest_ref["targetState"] = state_value
                quest_state_refs.append(quest_ref)
        if quest_state_refs:
            anchor["questStateRefs"] = quest_state_refs

        if (
            anchor.get("tracking")
            or anchor.get("conditionTypes")
            or anchor.get("storyRefs")
            or anchor.get("areaStoryRefs")
            or anchor.get("sceneIds")
            or anchor.get("missionAreaIds")
            or anchor.get("npcProxyIds")
            or anchor.get("jumpIds")
            or anchor.get("scriptIds")
            or anchor.get("logicIds")
            or anchor.get("questStateRefs")
        ):
            out.append(anchor)
    return out


def _load_mission_areas() -> dict[str, dict]:
    global _MISSION_AREA_CACHE
    if _MISSION_AREA_CACHE is not None:
        return _MISSION_AREA_CACHE
    out: dict[str, dict] = {}
    path = GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _MISSION_AREA_CACHE = out
        return out

    def walk(node) -> None:
        if isinstance(node, dict):
            mission_area_id = node.get("missionAreaId")
            if isinstance(mission_area_id, str) and mission_area_id and mission_area_id not in out:
                out[mission_area_id] = node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(raw.get("m_areas") if isinstance(raw, dict) else raw)
    _MISSION_AREA_CACHE = out
    return out


def _load_npc_proxy_table() -> dict[str, dict]:
    global _NPC_PROXY_TABLE_CACHE
    if _NPC_PROXY_TABLE_CACHE is not None:
        return _NPC_PROXY_TABLE_CACHE
    path = NPC_PROXY_TABLE_PATH
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _NPC_PROXY_TABLE_CACHE = {}
        return {}
    table = raw.get("dataTable") if isinstance(raw, dict) else None
    _NPC_PROXY_TABLE_CACHE = table if isinstance(table, dict) else {}
    return _NPC_PROXY_TABLE_CACHE


def _canonical_cutscene_key(name: str) -> str:
    return mission_canonical_cutscene_key(name)


def _scene_ref_alias_candidates(name: str) -> list[str]:
    value = str(name or "").strip()
    if not value:
        return []

    aliases: list[str] = []

    def add(candidate: str) -> None:
        if candidate and candidate != value and candidate not in aliases:
            aliases.append(candidate)

    bases = [value]
    if match := re.match(r"^(?:f|m|fm)_(.+)$", value, re.IGNORECASE):
        bases.append(match.group(1))

    for base in bases:
        if base.startswith("dlg_"):
            add(f"misc_{base}")
        elif base.startswith("misc_dlg_"):
            add(base[len("misc_"):])

        if base.startswith("cs_video_"):
            add(f"cutscene_{base[len('cs_video_'):]}")

        if not base.startswith((
            "dlg_",
            "sns_",
            "misc_dlg_",
            "cutscene_",
            "black_",
            "remotecomm_",
            "radio_",
        )):
            continue

        parent = base
        while parent.count("_") >= 3:
            stem, suffix = parent.rsplit("_", 1)
            if not suffix.isdigit():
                break
            add(stem)
            parent = stem

    return aliases


def _scene_key_matches_mission(scene_key: str, mission_id: str) -> bool:
    return not mission_id or f"_{mission_id}_" in f"_{scene_key}_"


def _resolve_payload_scene_key(payload_text: str, mission_id: str, dialog_key_resolver) -> str:
    candidates = _unique_preserve([
        str(payload_text or "").strip(),
        *_scene_ref_alias_candidates(payload_text),
    ])
    for candidate in candidates:
        if not candidate:
            continue
        scene_key = dialog_key_resolver(candidate) or ""
        if scene_key and _scene_key_matches_mission(scene_key, mission_id):
            return scene_key
        canonical_cutscene = _canonical_cutscene_key(candidate) or ""
        if canonical_cutscene and _scene_key_matches_mission(canonical_cutscene, mission_id):
            scene_key = dialog_key_resolver(canonical_cutscene) or canonical_cutscene
            if _scene_key_matches_mission(scene_key, mission_id):
                return scene_key
    return ""


def _cutscene_asset_name_without_prefix(name: str) -> str:
    value = str(name or "").strip()
    if match := re.match(r"^(?:f|m|fm)_(cutscene_.+)$", value, re.IGNORECASE):
        return match.group(1)
    return value


def _cutscene_variant_part(name: str, canonical_key: str) -> str:
    value = _cutscene_asset_name_without_prefix(name)
    value = re.sub(r"_p[0-9A-Fa-f]{8,16}$", "", value)
    if canonical_key and value.startswith(canonical_key):
        remainder = value[len(canonical_key):].strip("_")
    else:
        remainder = ""
    if not remainder:
        return "root"
    first = remainder.split("_", 1)[0]
    if first in {"Actor", "Audio", "Effect", "Light", "Others"}:
        return first
    if first in {"CHI", "CN", "EN", "ENG", "JP", "KO", "KR", "ENV"}:
        return f"locale:{first}"
    return "variant"


def _decode_anime_text_asset_payload(raw: dict) -> dict:
    script = raw.get("m_Script") if isinstance(raw, dict) else None
    if not isinstance(script, str) or not script.strip():
        return {}
    try:
        decoded = base64.b64decode(script, validate=True).decode("utf-8-sig")
        payload = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _subtitle_playable_text_ids(raw: dict) -> list[str]:
    text_id = str(raw.get("_textId") or "").strip()
    if text_id:
        return [text_id]

    numbered: list[tuple[int, str]] = []
    for key, value in raw.items():
        match = re.fullmatch(r"_textId_(\d+)", str(key or ""))
        if not match:
            continue
        text = str(value or "").strip()
        if text:
            numbered.append((int(match.group(1)), text))
    return [text for _index, text in sorted(numbered)]


def _cutscene_variant_gender(name: str) -> str:
    if re.match(r"^f_", str(name or ""), re.IGNORECASE):
        return "F"
    if re.match(r"^m_", str(name or ""), re.IGNORECASE):
        return "M"
    return ""


def _load_cutscene_subtitle_tracks() -> dict[str, list[dict]]:
    """Return AnimeStudio subtitle clip text IDs grouped by canonical cutscene.

    TextTable rows can contain loose aliases and unused leftovers. When a
    decoded cutscene has a real Timeline subtitle track, the clip asset
    references are the stronger source for which text IDs are actually used.
    """
    global _CUTSCENE_SUBTITLE_TRACK_CACHE
    if _CUTSCENE_SUBTITLE_TRACK_CACHE is not None:
        return _CUTSCENE_SUBTITLE_TRACK_CACHE

    parent_assets: dict[int, dict] = {}
    for path in _iter_anime_tree_files("*cutscene*.json"):
        logical_stem = _anime_tree_logical_stem(path)
        canonical_key = _canonical_cutscene_key(logical_stem)
        if not canonical_key:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        info = raw.get("$animestudio") if isinstance(raw, dict) else None
        path_id = info.get("pathId") if isinstance(info, dict) else None
        if not isinstance(path_id, int):
            continue
        parent_assets[path_id] = {
            "cutsceneKey": canonical_key,
            "name": logical_stem,
            "gender": _cutscene_variant_gender(logical_stem),
            "file": repo_rel(path),
        }

    playable_text_ids: dict[int, list[str]] = {}
    for path in _iter_anime_tree_files("*SubtitlePlayableAsset*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        info = raw.get("$animestudio") if isinstance(raw.get("$animestudio"), dict) else {}
        path_id = info.get("pathId")
        if not isinstance(path_id, int):
            continue
        text_ids = _subtitle_playable_text_ids(raw)
        if text_ids:
            playable_text_ids[path_id] = text_ids

    out: dict[str, list[dict]] = defaultdict(list)
    for path in itertools.chain(
        _iter_anime_tree_files("*Subtitle Track*.json"),
        _iter_anime_tree_files("*Left Subtitle Track*.json"),
    ):
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        clips = raw.get("m_Clips")
        if not isinstance(clips, list) or not clips:
            continue

        parent = raw.get("m_Parent") if isinstance(raw.get("m_Parent"), dict) else {}
        parent_id = parent.get("m_PathID")
        parent_asset = parent_assets.get(parent_id)
        if not parent_asset:
            continue

        track_info = raw.get("$animestudio") if isinstance(raw.get("$animestudio"), dict) else {}
        lines: list[dict] = []
        for clip_index, clip in enumerate(clips):
            if not isinstance(clip, dict):
                continue
            asset_ref = clip.get("m_Asset") if isinstance(clip.get("m_Asset"), dict) else {}
            asset_id = asset_ref.get("m_PathID")
            for text_id in playable_text_ids.get(asset_id, []):
                lines.append({
                    "textId": text_id,
                    "start": clip.get("m_Start"),
                    "duration": clip.get("m_Duration"),
                    "displayName": str(clip.get("m_DisplayName") or ""),
                    "clipIndex": clip_index,
                    "assetPathId": asset_id,
                })
        if not lines:
            continue

        lines.sort(key=lambda line: (
            float(line["start"]) if isinstance(line.get("start"), (int, float)) else 0.0,
            int(line.get("clipIndex") or 0),
            str(line.get("textId") or ""),
        ))
        out[parent_asset["cutsceneKey"]].append({
            "file": repo_rel(path),
            "pathId": track_info.get("pathId"),
            "parentPathId": parent_id,
            "parentName": parent_asset["name"],
            "parentFile": parent_asset["file"],
            "gender": parent_asset.get("gender") or "",
            "lines": lines,
        })

    for tracks in out.values():
        tracks.sort(key=lambda track: (
            str(track.get("parentName") or ""),
            str(track.get("file") or ""),
            str(track.get("pathId") or ""),
        ))

    _CUTSCENE_SUBTITLE_TRACK_CACHE = dict(out)
    return _CUTSCENE_SUBTITLE_TRACK_CACHE


def _infer_cutscene_mission_and_scene(
    canonical_key: str,
    known_missions: list[str],
) -> tuple[str, str]:
    prefix = "cutscene_"
    rest = canonical_key[len(prefix):] if canonical_key.startswith(prefix) else canonical_key
    mission = ""
    for candidate in known_missions:
        start = 0
        while True:
            idx = rest.find(candidate, start)
            if idx < 0:
                break
            end = idx + len(candidate)
            before_ok = idx == 0 or rest[idx - 1] == "_"
            after_ok = end == len(rest) or rest[end] == "_"
            if before_ok and after_ok:
                mission = candidate
                break
            start = idx + 1
        if mission:
            break

    if mission:
        idx = rest.find(mission)
        before = rest[:idx].strip("_")
        after = rest[idx + len(mission):].strip("_")
        scene = "_".join(part for part in (before, after) if part) or "0"
        return mission, scene

    parts = [part for part in rest.split("_") if part]
    if len(parts) >= 2 and parts[0].startswith("map") and parts[1].startswith("lv"):
        mission = "_".join(parts[:2])
        return mission, "_".join(parts[2:]) or "0"
    if len(parts) >= 2 and parts[0].startswith(("dung", "indie", "blackbox")):
        mission = "_".join(parts[:2])
        return mission, "_".join(parts[2:]) or "0"
    if parts:
        mission = parts[0]
        return mission, "_".join(parts[1:]) or "0"
    return canonical_key, "0"


def _relative_asset_ref(label: str, source_root: Path, path: Path) -> str:
    try:
        rel_suffix = path.relative_to(source_root).as_posix()
    except ValueError:
        rel_suffix = path.name
    return f"{label}/{rel_suffix}" if rel_suffix else label


def _iter_narrative_video_roots(kind_dir: str):
    structured_roots = (
        ("StreamingAssets-structured", STREAMING_ASSETS_DIR),
        ("Persistent-structured", PERSISTENT_ASSETS_DIR),
    )
    for label, source_root in structured_roots:
        video_dir = source_root / "Data" / "Video" / "PC" / "Narrative" / kind_dir
        if video_dir.exists():
            yield label, source_root, video_dir

    raw_vfs_root = EXPORT_ROOT / "raw_vfs"
    for source in ("StreamingAssets", "Persistent"):
        files_root = raw_vfs_root / source / "files"
        if not files_root.exists():
            continue
        for bucket_dir in sorted(files_root.iterdir()):
            if not bucket_dir.is_dir():
                continue
            video_dir = bucket_dir / "Data" / "Video" / "PC" / "Narrative" / kind_dir
            if video_dir.exists():
                yield "raw_vfs", raw_vfs_root, video_dir


def _strip_gender_video_prefix(stem: str) -> tuple[str, str]:
    value = str(stem or "").strip()
    if match := re.match(r"^(?P<gender>f|m)_(?P<rest>.+)$", value, re.IGNORECASE):
        return match.group("gender").lower(), match.group("rest")
    return "", value


def _narrative_video_key_candidates(kind: str, stem: str) -> list[str]:
    _, base = _strip_gender_video_prefix(stem)
    candidates: list[str] = []

    def add(candidate: str) -> None:
        candidate = str(candidate or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    def letter_suffix_alias(value: str) -> str:
        match = re.match(r"^(.+_\d+)[a-z]+$", str(value or ""), re.IGNORECASE)
        return match.group(1) if match else ""

    if kind == "cutscene":
        raw = base
        if raw.startswith("cs_video_"):
            raw = raw[len("cs_video_"):]
        raw_alias = letter_suffix_alias(raw)
        if raw.startswith("dlg_"):
            add(raw)
            add(raw_alias)
            add(f"misc_{raw}")
            if raw_alias:
                add(f"misc_{raw_alias}")
        if raw.startswith("cutscene_"):
            add(_canonical_cutscene_key(raw) or raw)
            if raw_alias:
                add(_canonical_cutscene_key(raw_alias) or raw_alias)
        else:
            add(_canonical_cutscene_key(f"cutscene_{raw}") or f"cutscene_{raw}")
            if raw_alias:
                add(_canonical_cutscene_key(f"cutscene_{raw_alias}") or f"cutscene_{raw_alias}")
            if not raw.startswith("dlg_"):
                add(f"dlg_{raw}")
                if raw_alias:
                    add(f"dlg_{raw_alias}")
        add(raw)
        add(raw_alias)
    elif kind == "remotecomm":
        add(base)
        if not base.startswith("remotecomm_"):
            add(f"remotecomm_{base}")
    return candidates


def _load_video_bindings_index() -> dict[str, dict]:
    """Read recovered/video_bindings.json (Graph A + Graph B) keyed by fmvId.

    Empty dict if the recovery output is missing or unreadable; downstream code
    must treat any missing entry as "no authoritative binding, fall back to
    name heuristics".
    """
    global _VIDEO_BINDINGS_CACHE
    if _VIDEO_BINDINGS_CACHE is not None:
        return _VIDEO_BINDINGS_CACHE
    try:
        payload = json.loads(VIDEO_BINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _VIDEO_BINDINGS_CACHE = {}
        return _VIDEO_BINDINGS_CACHE
    bindings = payload.get("bindings") if isinstance(payload, dict) else None
    _VIDEO_BINDINGS_CACHE = bindings if isinstance(bindings, dict) else {}
    return _VIDEO_BINDINGS_CACHE


def _video_binding_for_stem(stem: str) -> dict | None:
    bindings = _load_video_bindings_index()
    if not bindings:
        return None
    direct = bindings.get(stem)
    if isinstance(direct, dict):
        return direct
    return None


def _authoritative_scene_keys(kind: str, binding: dict) -> list[str]:
    """Convert a binding record into scene-key candidates suitable for index lookup.

    A timeline-resolved scene id like `e6m2_7` becomes the dialog key
    `dlg_e6m2_7`. For non-dialog scenes the raw id is also returned. Bindings
    that only carry a hint (no timeline asset) are skipped so the heuristic
    fallback stays in charge.
    """
    if not isinstance(binding, dict):
        return []
    if binding.get("sceneIsHint"):
        return []
    scene = str(binding.get("scene") or "").strip()
    if not scene:
        return []
    keys: list[str] = []
    if scene.startswith("dlg_"):
        keys.append(scene)
    else:
        keys.append(f"dlg_{scene}")
        if kind == "remotecomm" and not scene.startswith("remotecomm_"):
            keys.append(f"remotecomm_{scene}")
    if scene not in keys:
        keys.append(scene)
    return keys


def _load_narrative_video_assets() -> list[dict]:
    global _NARRATIVE_VIDEO_CACHE
    if _NARRATIVE_VIDEO_CACHE is not None:
        return _NARRATIVE_VIDEO_CACHE

    out: list[dict] = []
    for kind, kind_dir in (("cutscene", "Cutscene"), ("remotecomm", "RemoteComm")):
        for label, source_root, video_dir in _iter_narrative_video_roots(kind_dir):
            for path in sorted(video_dir.iterdir()):
                if not path.is_file() or path.suffix.lower() not in NARRATIVE_VIDEO_EXTENSIONS:
                    continue
                gender, base_stem = _strip_gender_video_prefix(path.stem)
                heuristic_candidates = _narrative_video_key_candidates(kind, path.stem)
                binding = _video_binding_for_stem(path.stem)
                authoritative_keys = _authoritative_scene_keys(kind, binding or {})

                candidates: list[str] = []
                seen: set[str] = set()
                for value in (*authoritative_keys, *heuristic_candidates):
                    if value and value not in seen:
                        candidates.append(value)
                        seen.add(value)
                if not candidates:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                ref = {
                    "kind": kind,
                    "name": path.name,
                    "stem": path.stem,
                    "baseStem": base_stem,
                    "gender": gender,
                    "format": path.suffix.lower().lstrip("."),
                    "size": size,
                    "source": label,
                    "rel": _relative_asset_ref(label, source_root, path),
                    "keyCandidates": candidates,
                }
                if binding:
                    binding_sources = [
                        {
                            key: source.get(key)
                            for key in ("kind", "asset", "container", "pathId", "duration", "missions")
                            if key in source
                        }
                        for source in (binding.get("sources") or [])
                        if isinstance(source, dict)
                    ]
                    ref["binding"] = {
                        "fmvId": str(binding.get("fmvId") or path.stem),
                        "scene": str(binding.get("scene") or ""),
                        "mission": str(binding.get("mission") or ""),
                        "missions": list(binding.get("missions") or []),
                        "isHint": bool(binding.get("sceneIsHint")),
                        "sourceKinds": sorted({
                            str(s.get("kind") or "")
                            for s in (binding.get("sources") or [])
                            if isinstance(s, dict) and s.get("kind")
                        }),
                        "clips": [
                            {
                                "scene": c.get("scene"),
                                "start": c.get("start"),
                                "duration": c.get("duration"),
                                "optionIndex": c.get("optionIndex"),
                            }
                            for c in (binding.get("clips") or [])
                            if isinstance(c, dict)
                        ][:8],
                    }
                    if binding_sources:
                        ref["binding"]["evidence"] = binding_sources[:8]
                if authoritative_keys:
                    ref["authoritativeKeys"] = list(authoritative_keys)
                out.append(ref)

    out.sort(key=lambda ref: (
        str(ref.get("kind") or ""),
        str((ref.get("keyCandidates") or [""])[0]),
        str(ref.get("baseStem") or ""),
        str(ref.get("gender") or ""),
        str(ref.get("source") or ""),
        str(ref.get("name") or ""),
    ))
    _NARRATIVE_VIDEO_CACHE = out
    return out


def _load_cutscene_assets() -> dict[str, dict]:
    global _CUTSCENE_ASSET_CACHE
    if _CUTSCENE_ASSET_CACHE is not None:
        return _CUTSCENE_ASSET_CACHE

    out: dict[str, dict] = {}
    for path in _iter_anime_tree_files("*cutscene*.json"):
        logical_stem = _anime_tree_logical_stem(path)
        canonical_key = _canonical_cutscene_key(logical_stem)
        if not canonical_key:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        entry = out.setdefault(
            canonical_key,
            {
                "variants": [],
                "componentCounts": Counter(),
                "levels": set(),
                "actorLabels": [],
                "paths": [],
                "versions": [],
                "audioEvents": [],
                "tags": [],
                "metadata": defaultdict(list),
                "keepCameraPaths": [],
                "useBlackScreen": False,
                "isTransition": False,
                "hasSubtitleTrack": False,
            },
        )
        payload = _decode_anime_text_asset_payload(raw) or raw
        part = _cutscene_variant_part(logical_stem, canonical_key)
        entry["componentCounts"][part] += 1
        entry["variants"].append({
            "name": logical_stem,
            "part": part,
            "file": repo_rel(path),
            "path": str(payload.get("path") or ""),
            "version": str(payload.get("version") or raw.get("m_Version") or ""),
        })
        if payload.get("path"):
            entry["paths"].append(str(payload["path"]))
        if payload.get("version"):
            entry["versions"].append(str(payload["version"]))
        elif raw.get("m_Version") not in (None, ""):
            entry["versions"].append(str(raw["m_Version"]))
        audio_events = payload.get("audioEvents") or []
        if isinstance(audio_events, list):
            entry["audioEvents"].extend(str(event) for event in audio_events if event)
        tag_group = payload.get("tagGroup") if isinstance(payload, dict) else None
        if isinstance(tag_group, dict):
            tags = tag_group.get("tags") or []
            if isinstance(tags, list):
                entry["tags"].extend(str(tag) for tag in tags if tag)
            if tag_group.get("narrativeTypeTag") not in (None, ""):
                entry["metadata"]["narrativeTypeTag"].append(tag_group["narrativeTypeTag"])
        for meta_key in (
            "targetFrameRate",
            "skipType",
            "hideSquad",
            "useBlackScreen",
            "isTransition",
            "disableKeepCameras",
            "farCameraPosition",
            "noUIDispatch",
            "npcVisibleRuleType",
        ):
            if meta_key in payload and is_present(payload.get(meta_key)):
                entry["metadata"][meta_key].append(payload[meta_key])
        keep_camera_path = str(payload.get("keepCameraPath") or "")
        if keep_camera_path:
            entry["keepCameraPaths"].append(keep_camera_path)
        entry["useBlackScreen"] = entry["useBlackScreen"] or bool(payload.get("useBlackScreen"))
        path_text = str(payload.get("path") or "")
        entry["isTransition"] = entry["isTransition"] or bool(payload.get("isTransition")) or ("CutsceneTransition/" in path_text)

        for track in payload.get("trackData") or []:
            for sub_track in track.get("subTracks") or []:
                if "SubtitleTrackData" in str(sub_track.get("$type") or ""):
                    entry["hasSubtitleTrack"] = True

        for actor in payload.get("actors") or []:
            descriptor = actor.get("descriptor") or {}
            level_id = str(descriptor.get("levelId") or "")
            if level_id:
                entry["levels"].add(level_id)
            label = (
                str(descriptor.get("entityId") or "")
                or str(descriptor.get("interactiveTemplateId") or "")
                or str(descriptor.get("name") or "")
            ).strip()
            if label and label not in entry["actorLabels"]:
                entry["actorLabels"].append(label)

    for entry in out.values():
        entry["variants"].sort(key=lambda item: item["name"])
        entry["paths"] = _unique_preserve(entry["paths"])
        entry["versions"] = _unique_preserve(entry["versions"])
        entry["audioEvents"] = _unique_preserve(entry["audioEvents"])
        entry["tags"] = _unique_preserve(entry["tags"])
        entry["metadata"] = {
            key: _unique_preserve(values)
            for key, values in sorted(entry["metadata"].items())
            if values
        }
        entry["keepCameraPaths"] = _unique_preserve(entry["keepCameraPaths"])
        entry["componentCounts"] = {
            key: entry["componentCounts"][key]
            for key in sorted(entry["componentCounts"], key=lambda item: (item != "root", item))
        }
        entry["levels"] = sorted(entry["levels"])
    _CUTSCENE_ASSET_CACHE = out
    return out


def _cutscene_component_summary(cutscene: dict, *, limit: int = 8) -> str:
    counts = cutscene.get("componentCounts") or {}
    if not isinstance(counts, dict) or not counts:
        variant_count = len(cutscene.get("variants") or [])
        return f"{variant_count} file{'s' if variant_count != 1 else ''}" if variant_count else ""
    parts = [
        f"{key} {count}"
        for key, count in counts.items()
        if count
    ]
    if len(parts) > limit:
        hidden = len(parts) - limit
        parts = [*parts[:limit], f"+{hidden} more"]
    return ", ".join(parts)


def _resolve_tracking_hint(hint: dict) -> dict:
    resolved = dict(hint)
    tracking_pos = hint.get("trackingPos")
    if isinstance(tracking_pos, dict):
        resolved["position"] = tracking_pos
        resolved["sourceType"] = "trackingPos"
        return resolved

    mission_area_id = str(hint.get("missionAreaId") or "")
    if mission_area_id:
        area = _load_mission_areas().get(mission_area_id) or {}
        shape = area.get("shape") or {}
        position = shape.get("position")
        if isinstance(position, dict):
            resolved["position"] = {
                "x": float(position.get("x", 0.0)),
                "y": float(position.get("y", 0.0)),
                "z": float(position.get("z", 0.0)),
            }
            resolved["sourceType"] = "missionArea"
            resolved["shapeType"] = shape.get("type")
            resolved["radius"] = shape.get("radius")
            sub_data_parent_id = area.get("subDataParentId")
            if sub_data_parent_id not in (None, "", [], {}):
                resolved["subDataParentId"] = sub_data_parent_id
                resolved["levelDataParentId"] = sub_data_parent_id
            if area.get("activeOnTravelLine") not in (None, "", [], {}):
                resolved["activeOnTravelLine"] = area.get("activeOnTravelLine")
            if area.get("needTrackingRoute") not in (None, "", [], {}):
                resolved["needTrackingRoute"] = area.get("needTrackingRoute")
            route_points = (((area.get("trackingRouteInfo") or {}).get("points")) or [])
            if route_points:
                resolved["routePointCount"] = len(route_points)
            return resolved

    npc_proxy_id = str(hint.get("npcProxyId") or "")
    if npc_proxy_id:
        proxy = _load_npc_proxy_table().get(npc_proxy_id) or {}
        position = proxy.get("position")
        if isinstance(position, dict):
            resolved["position"] = {
                "x": float(position.get("x", 0.0)),
                "y": float(position.get("y", 0.0)),
                "z": float(position.get("z", 0.0)),
            }
            resolved["sourceType"] = "npcProxy"
            rotation = proxy.get("rotation")
            if isinstance(rotation, dict):
                resolved["rotation"] = {
                    "x": float(rotation.get("x", 0.0)),
                    "y": float(rotation.get("y", 0.0)),
                    "z": float(rotation.get("z", 0.0)),
                }
            return resolved

    return resolved


def _tracking_hint_pin(hint: dict) -> dict | None:
    position = hint.get("position")
    if not isinstance(position, dict):
        return None
    return {
        "scene": str(hint.get("scene") or ""),
        "trackingType": str(hint.get("type") or ""),
        "sourceType": str(hint.get("sourceType") or ""),
        "position": {
            "x": float(position.get("x", 0.0)),
            "y": float(position.get("y", 0.0)),
            "z": float(position.get("z", 0.0)),
        },
        **({"missionAreaId": hint["missionAreaId"]} if hint.get("missionAreaId") else {}),
        **({"npcProxyId": hint["npcProxyId"]} if hint.get("npcProxyId") else {}),
        **({"radius": hint["radius"]} if hint.get("radius") is not None else {}),
        **({"subDataParentId": hint["subDataParentId"]} if hint.get("subDataParentId") is not None else {}),
        **({"levelDataParentId": hint["levelDataParentId"]} if hint.get("levelDataParentId") is not None else {}),
        **({"activeOnTravelLine": hint["activeOnTravelLine"]} if hint.get("activeOnTravelLine") is not None else {}),
        **({"needTrackingRoute": hint["needTrackingRoute"]} if hint.get("needTrackingRoute") is not None else {}),
        **({"routePointCount": hint["routePointCount"]} if hint.get("routePointCount") is not None else {}),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
