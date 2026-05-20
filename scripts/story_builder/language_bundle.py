from __future__ import annotations

import json as _radio_cont_json
from functools import lru_cache as _radio_cont_lru_cache
from pathlib import Path as _RadioContPath

from .context import *
from .anime_assets import *
from .scene_graph import *
from .level_bindings import *
from .mission_flow import *
from .dialog_tree import *
from .bundle_support import *
from .language_helpers import *


_RADIO_CONTINUATION_REPORT_PATH = (
    _RadioContPath(__file__).resolve().parents[2]
    / "reports" / "mission_order" / "radio_continuation_CN.json"
)

_FMV_CLIP_BY_KEY_REPORT_PATH = (
    _RadioContPath(__file__).resolve().parents[2]
    / "reports" / "playable_director" / "fmv_clip_by_webui_key.json"
)

_MANUAL_OPTION_OVERRIDES_PATH = (
    _RadioContPath(__file__).resolve().parent / "manual_option_overrides.json"
)


@_radio_cont_lru_cache(maxsize=2)
def _load_manual_option_overrides(path_str: str) -> dict:
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {}
    try:
        data = _radio_cont_json.loads(path.read_text(encoding="utf-8-sig"))
    except (_radio_cont_json.JSONDecodeError, OSError) as exc:
        print(f"[story] warning: failed to read manual option overrides {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        print(f"[story] warning: manual option overrides must be a JSON object: {path}")
        return {}
    scenes = data.get("scenes")
    return scenes if isinstance(scenes, dict) else {}


def _manual_option_group_override(conv_key: str, group_id: int) -> dict:
    scenes = _load_manual_option_overrides(str(_MANUAL_OPTION_OVERRIDES_PATH))
    key = str(conv_key or "")
    scene = scenes.get(key)
    if not isinstance(scene, dict) and key.startswith("dlg_"):
        scene = scenes.get(f"misc_{key}")
    if not isinstance(scene, dict):
        return {}
    groups = scene.get("groups")
    if not isinstance(groups, dict):
        return {}
    group = groups.get(str(group_id))
    return group if isinstance(group, dict) else {}


@_radio_cont_lru_cache(maxsize=2)
def _load_radio_continuation_candidates_by_mission(
    path_str: str,
) -> dict[str, list[dict]]:
    """Load the radio-continuation audit report keyed by mission id.

    Each value is a list of `(predecessor, radio, match, levelId, file)` dicts.
    Returns an empty dict when the report has not been generated yet, so the
    builder degrades to its prior behavior cleanly.
    """
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {}
    try:
        payload = _radio_cont_json.loads(path.read_text(encoding="utf-8"))
    except (OSError, _radio_cont_json.JSONDecodeError):
        return {}
    out: dict[str, list[dict]] = {}
    for result in payload.get("results") or []:
        mission = result.get("mission") or ""
        if not mission:
            continue
        out.setdefault(mission, []).extend(result.get("candidates") or [])
    return out


@_radio_cont_lru_cache(maxsize=2)
def _load_fmv_clips_by_webui_key(path_str: str) -> dict[str, list[dict]]:
    """Load `reports/playable_director/fmv_clip_by_webui_key.json`.

    Returns `{webui_key: [{fmvId, clipStart, clipDuration, ...}, ...]}` or
    an empty dict when the report has not been generated yet. The builder
    surfaces these as per-conv `fmvClips` meta so the WebUI can display
    authored FMV timing for cutscene/dialog stories that bind to a
    `BeyondFMVPlayableAsset` clip.
    """
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {}
    try:
        payload = _radio_cont_json.loads(path.read_text(encoding="utf-8"))
    except (OSError, _radio_cont_json.JSONDecodeError):
        return {}
    mappings = payload.get("mappings")
    return mappings if isinstance(mappings, dict) else {}


def build_language_bundle(
    language_code: str,
    out_dir: Path,
    *,
    profile: str = DEFAULT_BUILD_PROFILE,
    write_reference: bool = True,
) -> dict:
    if profile not in BUILD_PROFILES:
        raise ValueError(f"unknown build profile: {profile}")
    include_reference_in_story_index = profile == "full"
    i18n_table_name = f"I18nTextTable_{language_code}.json"
    i18n_table_key = i18n_table_name.removesuffix(".json")
    t0 = time.time()
    conv_dir = out_dir / "conv"
    reference_dir = out_dir / "reference"
    mission_dir = out_dir / "mission"
    out_dir.mkdir(parents=True, exist_ok=True)
    conv_dir.mkdir(parents=True, exist_ok=True)
    if write_reference:
        reference_dir.mkdir(parents=True, exist_ok=True)
    else:
        shutil.rmtree(reference_dir, ignore_errors=True)
    dialog_id_registry = shared_load_dialog_id_registry()
    story_source_links = load_story_source_links()
    narrative_video_assets = _load_narrative_video_assets()
    fmv_clips_by_key = _load_fmv_clips_by_webui_key(str(_FMV_CLIP_BY_KEY_REPORT_PATH))
    written_conv_paths: set[str] = set()
    written_reference_paths: set[str] = set()
    written_mission_paths: set[str] = set()
    conv_media_tags_by_key: dict[str, set[str]] = defaultdict(set)

    inline_image_tag_re = re.compile(
        r"<image\b(?!\s*=)[^>]*>[\s\S]*?</image>"
        r"|<image\s*=[^>]+>"
        r"|<image\b(?=[^>]*(?:src|source|path|name|id)\s*=)[^>]*>",
        flags=re.IGNORECASE,
    )


    def normalize_media_id(value: object) -> str:
        trimmed = clean_media_id_value(value).replace("\\", "/")
        if not trimmed:
            return ""
        without_prefix = re.sub(r"^SNS/Emoji/", "", trimmed, flags=re.IGNORECASE)
        last_segment = without_prefix.split("/")[-1] or without_prefix
        return re.sub(r"\.[^.]+$", "", last_segment, flags=re.IGNORECASE).lower()

    def inline_image_id_from_tag(raw_tag: str) -> str:
        raw = str(raw_tag or "").strip()
        if not raw:
            return ""
        body_match = re.match(r"^<image\b(?!\s*=)[^>]*>([\s\S]*?)</image>$", raw, flags=re.IGNORECASE)
        if body_match:
            return clean_media_id_value(body_match.group(1))
        quoted_direct = re.match(r"""^<image\s*=\s*(["'])([\s\S]*?)\1""", raw, flags=re.IGNORECASE)
        if quoted_direct:
            return clean_media_id_value(quoted_direct.group(2))
        loose_direct = re.match(r"^<image\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
        if loose_direct:
            return clean_media_id_value(loose_direct.group(1))
        quoted_attr = re.search(
            r"""\b(?:src|source|path|name|id)\s*=\s*(["'])([\s\S]*?)\1""",
            raw,
            flags=re.IGNORECASE,
        )
        if quoted_attr:
            return clean_media_id_value(quoted_attr.group(2))
        loose_attr = re.search(r"\b(?:src|source|path|name|id)\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
        return clean_media_id_value(loose_attr.group(1)) if loose_attr else ""

    def image_ids_from_text(text: object) -> list[str]:
        source = str(text or "")
        if "<image" not in source.lower():
            return []
        return [
            image_id
            for image_id in (inline_image_id_from_tag(match.group(0)) for match in inline_image_tag_re.finditer(source))
            if image_id
        ]

    def media_id_is_emoji(value: object) -> bool:
        normalized = normalize_media_id(value)
        return "emoji" in normalized or "emoiji" in normalized

    def media_id_is_sticker(value: object) -> bool:
        normalized = normalize_media_id(value)
        if not normalized or media_id_is_emoji(normalized):
            return False
        return normalized.startswith("sns_sticker_") or "sticker" in normalized

    def collect_payload_media_tags(payload: dict) -> set[str]:
        tags: set[str] = set()

        def add_media_id(value: object) -> None:
            normalized = normalize_media_id(value)
            if not normalized:
                return
            if media_id_is_emoji(normalized):
                tags.add("mediaEmoji")
                return
            tags.add("mediaSticker" if media_id_is_sticker(normalized) else "mediaImage")

        def add_text_images(value: object) -> None:
            for image_id in image_ids_from_text(value):
                add_media_id(image_id)

        def source_from_debug(debug: object) -> dict:
            if not isinstance(debug, dict):
                return {}
            source = debug.get("source") or {}
            if isinstance(source, dict) and isinstance(source.get("source"), dict):
                return source["source"]
            return source if isinstance(source, dict) else {}

        def add_media_from_source(source: dict) -> None:
            if not isinstance(source, dict):
                return
            for field in ("image", "emoji", "emojiResPath", "optionResPath"):
                add_media_id(source.get(field))
            for image_id in source.get("contentParam") or []:
                add_media_id(image_id)

            raw_content_params = source.get("contentParams")
            if not isinstance(raw_content_params, str) or not raw_content_params.strip():
                return
            try:
                content_params = json.loads(raw_content_params)
            except json.JSONDecodeError:
                return

            def visit_content_param(node: object) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key in {"image", "imageResPath", "emoji", "emojiResPath", "optionResPath"}:
                            add_media_id(value)
                        elif isinstance(value, (dict, list)):
                            visit_content_param(value)
                elif isinstance(node, list):
                    for item in node:
                        visit_content_param(item)

            visit_content_param(content_params)

        def visit_line(line: object) -> None:
            if not isinstance(line, dict):
                return
            add_text_images(line.get("text"))
            add_media_id(line.get("image"))
            add_media_id(line.get("emoji"))
            for image_id in line.get("images") or []:
                add_media_id(image_id)
            source = source_from_debug(line.get("_debug"))
            add_media_from_source(source)
            if source.get("video"):
                tags.add("mediaVideo")
            for option in line.get("options") or []:
                if not isinstance(option, dict):
                    continue
                add_text_images(option.get("text"))
                add_media_id(option.get("image"))
                add_media_id(option.get("emoji"))
                add_media_from_source(source_from_debug(option.get("_debug")))

        for line in payload.get("lines") or []:
            visit_line(line)
        for row in payload.get("summary") or []:
            if isinstance(row, dict):
                add_text_images(row.get("text"))
        if payload.get("narrativeVideos"):
            tags.add("mediaVideo")
        cutscene = payload.get("cutscene")
        if isinstance(cutscene, dict) and cutscene.get("videoRefs"):
            tags.add("mediaVideo")
        return tags


    def remember_written(path: Path, bucket: set[str]) -> Path:
        bucket.add(written_path_key(path))
        return path

    def write_conv_payload(out_key: str, payload: dict) -> Path:
        path = conv_dir / f"{out_key}.json"
        write_json(path, payload)
        media_tags = collect_payload_media_tags(payload)
        if media_tags:
            conv_media_tags_by_key[out_key].update(media_tags)
        return remember_written(path, written_conv_paths)

    def write_reference_payload(rel_file: str, payload: dict) -> Path:
        path = reference_dir / rel_file
        write_json(path, payload)
        return remember_written(path, written_reference_paths)

    def write_mission_payload(rel_file: str, payload: dict) -> Path:
        path = out_dir / rel_file
        write_json(path, payload)
        return remember_written(path, written_mission_paths)

    def cleanup_stale_json(root: Path, written_paths: set[str]) -> None:
        if not root.exists():
            return
        for path in sorted(root.rglob("*.json")):
            if written_path_key(path) not in written_paths:
                path.unlink()
        for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass

    print(f"\n[{language_code}] Loading tables...")
    i18n_by_source = {
        "streaming": load(i18n_table_name),
        "persistent": load_optional_table_json(
            PERSISTENT_TABLE_DIR,
            i18n_table_name,
            f"Persistent/{i18n_table_name}",
        ),
    }

    def apply_i18n_hotfixes() -> dict[str, dict[str, int]]:
        hotfix_type = I18N_HOTFIX_LANGUAGE_TYPES.get(language_code)
        stats: dict[str, dict[str, int]] = {}
        if hotfix_type is None:
            return stats

        for source_name, table_dir in (
            ("streaming", STREAMING_TABLE_DIR),
            ("persistent", PERSISTENT_TABLE_DIR),
        ):
            target = i18n_by_source.get(source_name)
            if not isinstance(target, dict):
                continue
            hotfix_rows = load_optional_table_json(
                table_dir,
                I18N_HOTFIX_TABLE,
                f"{source_name}/{I18N_HOTFIX_TABLE}",
            )
            patched = 0
            added = 0
            for row_id, row in hotfix_rows.items():
                if not isinstance(row, dict):
                    continue
                for item in row.get("list") or []:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != hotfix_type:
                        continue
                    text = item.get("text")
                    if text is None:
                        continue
                    text_id = str(item.get("id") or row_id)
                    if not text_id:
                        continue
                    if text_id not in target:
                        added += 1
                    target[text_id] = str(text)
                    patched += 1
            if patched or added:
                stats[source_name] = {"patched": patched, "added": added}
        return stats

    hotfix_stats = apply_i18n_hotfixes()
    if hotfix_stats:
        summary = ", ".join(
            f"{source}: {row['patched']} patched ({row['added']} new)"
            for source, row in sorted(hotfix_stats.items())
        )
        print(f"  applied {I18N_HOTFIX_TABLE}: {summary}")

    text_table = load("TextTable.json")
    dialogs = load("DialogTextTable.json")
    sns = load("SNSDialogTable.json")
    sns_chats = load("SNSChatTable.json")
    sns_opts = load("SNSDialogOptionTable.json")
    sns_topics = load("SNSDialogTopicTable.json")
    dlg_opts = load("DialogOptionTable.json")
    summaries = load("DialogSummaryTable.json")
    mission_extra_info = load("MissionExtraInfoTable.json")
    dungeons = load("DungeonTable.json")
    skill_patches = load("SkillPatchTable.json")
    char_growth = load("CharGrowthTable.json")
    game_mechanics = load("GameMechanicTable.json")
    loading_tips = load("LoadingTipsTable.json")
    error_codes = load("ErrorCodeTable.json")
    achievements = load("AchievementTable.json")
    achievement_types = load("AchievementTypeTable.json")
    mail_senders = load("MailSenderTable.json")
    mail_templates = load("MailTemplateTable.json")
    character_rows = load("CharacterTable.json")
    item_rows = load("ItemTable.json")
    weapon_basic = load("WeaponBasicTable.json")
    enemy_display_info = load("EnemyDisplayInfoTable.json")
    enemy_template_display = load("EnemyTemplateDisplayInfoTable.json")
    enemy_ability_desc = load("EnemyAbilityDescTable.json")
    npc_rows = load("NpcTable.json")
    npc_templates = load("NpcTemplateGroupTable.json")
    npc_proxy_rows = load_json_path(NPC_PROXY_TABLE_PATH, "NpcProxyTable.json").get("dataTable") or {}
    npc_proxy_ex = _load_npc_proxy_ex()
    npc_proxy_info = npc_proxy_ex.get("proxyInfoData") or {}
    npc_proxy_info = npc_proxy_info if isinstance(npc_proxy_info, dict) else {}
    atmos_cluster_rows = load_json_path(
        ATMOS_CLUSTER_TABLE_PATH, "AtmosphericNpcClusterDataTable.json"
    ).get("dataTable") or {}
    radios = load("RadioTable.json")
    remote_common = load("RemoteCommonTable.json")
    env_talks = load("EnvTalkTable.json")
    ai_bark_text = load("AIBarkText.json")
    audio_dialog = load("AudioDialog.json")
    responsive_dialog = load("ResponsiveDialog.json")
    rich_content = load("RichContentTable.json")
    prts_all_items = load("PrtsAllItem.json")
    prts_first_lv = load("PrtsFirstLv.json")
    prts_page = load("PrtsPage.json")
    prts_notes = load("PrtsNote.json")
    prts_categories = load("PrtsCategory.json")
    prts_investigate_categories = load("PrtsInvestigateCategory.json")
    wiki_categories = load("WikiCategoryTable.json")
    wiki_groups = load("WikiGroupTable.json")
    wiki_entry_data = load("WikiEntryDataTable.json")
    wiki_tutorial_pages = load("WikiTutorialPageTable.json")
    wiki_tutorial_pages_by_entry = load("WikiTutorialPageByEntryTable.json")
    wiki_craft_jump = load("WikiCraftJumpTable.json")
    wiki_default_craft = load("WikiDefaultCraftTable.json")


    def t(id_value, preferred_source: str = "streaming") -> str:
        s = norm_id(id_value)
        if not s:
            return ""
        lookup_order = [preferred_source]
        for source_name in ("streaming", "persistent"):
            if source_name not in lookup_order:
                lookup_order.append(source_name)
        for source_name in lookup_order:
            text = (i18n_by_source.get(source_name) or {}).get(s, "")
            if text:
                return text
        return ""


    referenced_texttable_row_ids: set[str] = set()

    def remember_texttable_row_usage(row_id) -> None:
        row_key = str(row_id or "").strip()
        if row_key:
            referenced_texttable_row_ids.add(row_key)

    def text_trace(
        table: str,
        row_id: str,
        field: str,
        raw_value,
        *,
        preferred_source: str = "streaming",
        transform: str = "",
    ) -> dict:
        i18n_id = norm_id(raw_value.get("id") if isinstance(raw_value, dict) else raw_value)
        resolved = t(i18n_id, preferred_source=preferred_source)
        trace = {
            "table": table,
            "rowId": row_id,
            "field": field,
            "raw": raw_value,
            "lookup": [],
            "text": resolved,
        }
        if preferred_source != "streaming":
            trace["preferredSource"] = preferred_source
        if i18n_id:
            trace["lookup"].append({
                "from": f"{table}[{row_id}].{field}",
                "value": i18n_id,
            })
            trace["lookup"].append({
                "from": f"{i18n_table_key}[{i18n_id}]",
                "value": resolved,
            })
        if transform:
            trace["transform"] = transform
        return trace

    def named_text_trace(table: str, row_id: str, field: str, raw_value) -> dict:
        trace = text_trace(table, row_id, field, raw_value)
        trace["braceText"] = brace_text(trace["text"])
        if trace["text"]:
            trace["lookup"].append({
                "from": f"brace_text({field})",
                "value": trace["braceText"],
            })
        return trace


    def rich_content_trace(row_id: str, field: str, raw_value) -> dict:
        return text_trace("RichContentTable", row_id, field, raw_value)

    def rich_content_title_text(content_id: str) -> str:
        row = rich_content.get(content_id)
        if not isinstance(row, dict):
            return ""
        return t((row.get("title") or {}).get("id"))

    def rich_content_lines(content_id: str) -> list[dict]:
        row = rich_content.get(content_id)
        if not isinstance(row, dict):
            return []
        out: list[dict] = []
        for idx, item in enumerate(row.get("contentList") or [], start=1):
            content = (item or {}).get("content") or {}
            text = t(content.get("id"))
            out.append({
                "id": f"{content_id}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        content_id,
                        pick_fields(item, "content"),
                        nodeId=idx,
                    ),
                    "fields": {
                        "text": rich_content_trace(content_id, "content", content),
                    },
                },
            })
        return out


    def sns_media_text_from_params(params) -> str:
        image_ids = [
            str(value or "").strip()
            for value in (params or [])
            if str(value or "").strip()
        ]
        if not image_ids:
            return ""

        if len(image_ids) == 2:
            by_gender: dict[str, str] = {}
            for image_id in image_ids:
                lower = image_id.lower()
                if lower.endswith("_m"):
                    by_gender["M"] = image_id
                elif lower.endswith("_f"):
                    by_gender["F"] = image_id
            if by_gender.get("M") and by_gender.get("F"):
                return (
                    f'{{M}}{inline_image_tag(by_gender["M"])}'
                    f'{{F}}{inline_image_tag(by_gender["F"])}'
                )

        return " ".join(inline_image_tag(image_id) for image_id in image_ids)

    def sns_content_text(node: dict) -> str:
        text = t(node.get("content", {}).get("id"))
        if text:
            return text
        if node.get("contentType") == 2:
            return sns_media_text_from_params(node.get("contentParam"))
        return ""

    def sns_option_display_text(opt: dict) -> str:
        text = t(opt.get("optionDesc", {}).get("id"))
        if text:
            return text
        res_path = str(opt.get("optionResPath") or "").strip()
        if res_path:
            return inline_image_tag(res_path)
        return ""




    mission_name_cache: dict[str, str] = {}
    chat_name_cache: dict[str, str] = {}
    topic_name_cache: dict[str, str] = {}
    topic_id_cache: dict[str, str] = {}
    blackbox_title_cache: dict[str, str] = {}
    topic_base_index: dict[str, list[str]] = defaultdict(list)
    blackbox_base_titles: dict[str, list[dict]] = defaultdict(list)
    blackbox_exact_titles: dict[str, dict] = {}
    for topic_key in sns_topics:
        base_key = re.sub(r"_\d+$", "", topic_key)
        topic_base_index[base_key].append(topic_key)
    for topic_ids in topic_base_index.values():
        topic_ids.sort(key=lambda key: [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", key)])


    for dungeon_id, row in dungeons.items():
        scene_id = normalize_blackbox_id(str(row.get("sceneId") or ""))
        if not scene_id.startswith("blackbox_"):
            continue
        title = brace_text(t((row.get("dungeonName") or {}).get("id")))
        if not title:
            continue
        info = {
            "dungeonId": dungeon_id,
            "sceneId": scene_id,
            "title": title,
            "row": row,
        }
        blackbox_exact_titles[scene_id] = info
        blackbox_base_titles[re.sub(r"_\d+$", "", scene_id)].append(info)

    def mission_name(mission_id: str) -> str:
        """Resolve a mission id like `a1m6d3` to a localized display name."""
        if not mission_id:
            return ""
        if mission_id in mission_name_cache:
            return mission_name_cache[mission_id]
        if mission_id.startswith("topic_"):
            chat_id = mission_chat_id(mission_id)
            if chat_id:
                name = chat_name(chat_id)
                mission_name_cache[mission_id] = name
                return name
        row = text_table.get(f"{mission_id}_name")
        if row:
            remember_texttable_row_usage(f"{mission_id}_name")
            name = brace_text(t(row.get("id")))
            mission_name_cache[mission_id] = name
            return name
        normalized_blackbox_id = normalize_blackbox_id(mission_id)
        if normalized_blackbox_id.startswith("blackbox_"):
            if normalized_blackbox_id in blackbox_title_cache:
                name = blackbox_title_cache[normalized_blackbox_id]
                mission_name_cache[mission_id] = name
                return name
            if exact := blackbox_exact_titles.get(normalized_blackbox_id):
                name = exact["title"]
                blackbox_title_cache[normalized_blackbox_id] = name
                mission_name_cache[mission_id] = name
                return name
            titles = [info["title"] for info in blackbox_base_titles.get(normalized_blackbox_id, [])]
            if titles:
                name = " / ".join(dict.fromkeys(titles))
                blackbox_title_cache[normalized_blackbox_id] = name
                mission_name_cache[mission_id] = name
                return name
        mission_name_cache[mission_id] = ""
        return ""

    def mission_name_trace(mission_id: str) -> dict | None:
        if not mission_id:
            return None
        if mission_id.startswith("topic_"):
            chat_id = mission_chat_id(mission_id)
            if chat_id:
                trace = chat_name_trace(chat_id)
                if trace:
                    trace = dict(trace)
                    trace["source"] = dict(trace.get("source") or {})
                    trace["source"]["derivedMissionId"] = mission_id
                    return trace
        row_id = f"{mission_id}_name"
        row = text_table.get(row_id)
        if row:
            remember_texttable_row_usage(row_id)
            return {
                **source_ref("TextTable", row_id, pick_fields(row, "id")),
                "value": brace_text(t(row.get("id"))),
                "trace": named_text_trace("TextTable", row_id, "id", row.get("id")),
            }
        normalized_blackbox_id = normalize_blackbox_id(mission_id)
        if not normalized_blackbox_id.startswith("blackbox_"):
            return None
        if exact := blackbox_exact_titles.get(normalized_blackbox_id):
            return {
                **source_ref(
                    "DungeonTable",
                    exact["dungeonId"],
                    pick_fields(exact["row"], "sceneId", "dungeonName"),
                    normalizedMissionId=normalized_blackbox_id,
                ),
                "value": exact["title"],
                "trace": named_text_trace(
                    "DungeonTable",
                    exact["dungeonId"],
                    "dungeonName",
                    (exact["row"].get("dungeonName") or {}),
                ),
            }
        infos = blackbox_base_titles.get(normalized_blackbox_id, [])
        if not infos:
            return None
        titles = [info["title"] for info in infos]
        return {
            "table": "DungeonTable",
            "rowId": normalized_blackbox_id,
            "source": {
                "normalizedMissionId": normalized_blackbox_id,
                "variants": [
                    {
                        "dungeonId": info["dungeonId"],
                        "sceneId": info["sceneId"],
                        "title": info["title"],
                    }
                    for info in infos
                ],
            },
            "value": " / ".join(dict.fromkeys(titles)),
            "trace": {
                "raw": titles,
                "lookup": [
                    {
                        "from": f"DungeonTable[{info['dungeonId']}].dungeonName",
                        "value": info["title"],
                    }
                    for info in infos
                ],
            },
        }

    def resolve_topic_id(topic_id: str) -> str:
        """Resolve base SNS topic ids like `topic_chr_0004_pelica` to a table row."""
        if not topic_id:
            return ""
        if topic_id in topic_id_cache:
            return topic_id_cache[topic_id]
        if topic_id in sns_topics:
            topic_id_cache[topic_id] = topic_id
            return topic_id
        matches = topic_base_index.get(topic_id, [])
        resolved = matches[0] if matches else ""
        topic_id_cache[topic_id] = resolved
        return resolved

    def mission_chat_id(mission_id: str) -> str:
        if not mission_id.startswith("topic_"):
            return ""
        chat_id = mission_id.removeprefix("topic_")
        if not chat_id:
            return ""
        if chat_id in sns_chats:
            return chat_id
        prefixed = f"sns_{chat_id}"
        return prefixed if prefixed in sns_chats else ""

    def chat_name(chat_id: str) -> str:
        if not chat_id:
            return ""
        if chat_id in chat_name_cache:
            return chat_name_cache[chat_id]
        row = sns_chats.get(chat_id)
        if not row:
            chat_name_cache[chat_id] = ""
            return ""
        name = brace_text(t((row.get("name") or {}).get("id")))
        chat_name_cache[chat_id] = name
        return name

    def chat_name_trace(chat_id: str) -> dict | None:
        if not chat_id:
            return None
        row = sns_chats.get(chat_id)
        if not row:
            return None
        return {
            **source_ref("SNSChatTable", chat_id, pick_fields(row, "chatId", "name", "owner", "chatType")),
            "value": brace_text(t((row.get("name") or {}).get("id"))),
            "trace": named_text_trace("SNSChatTable", chat_id, "name", row.get("name")),
        }

    def chat_type(chat_id: str) -> int:
        if not chat_id:
            return 0
        row = sns_chats.get(chat_id)
        if not isinstance(row, dict):
            return 0
        try:
            return int(row.get("chatType") or 0)
        except (TypeError, ValueError):
            return 0

    def topic_name(topic_id: str) -> str:
        """Resolve an SNS topic id like `topic_chr_0004_pelica` to its localized title."""
        if not topic_id:
            return ""
        if topic_id in topic_name_cache:
            return topic_name_cache[topic_id]
        resolved_topic_id = resolve_topic_id(topic_id)
        row = sns_topics.get(resolved_topic_id)
        if not row:
            topic_name_cache[topic_id] = ""
            return ""
        name = brace_text(t(row.get("topicName", {}).get("id")))
        topic_name_cache[topic_id] = name
        return name

    def topic_name_trace(topic_id: str) -> dict | None:
        if not topic_id:
            return None
        resolved_topic_id = resolve_topic_id(topic_id)
        row = sns_topics.get(resolved_topic_id)
        if not row:
            return None
        return {
            **source_ref(
                "SNSDialogTopicTable", resolved_topic_id, pick_fields(row, "topicName")
            ),
            "value": brace_text(t(row.get("topicName", {}).get("id"))),
            "trace": named_text_trace(
                "SNSDialogTopicTable", resolved_topic_id, "topicName", row.get("topicName")
            ),
        }

    def named_text(name_key: str) -> str:
        if not name_key:
            return ""
        row = text_table.get(name_key)
        if not row:
            return ""
        remember_texttable_row_usage(name_key)
        return t(row.get("id"))

    def named_text_key_trace(name_key: str) -> dict | None:
        if not name_key:
            return None
        row = text_table.get(name_key)
        if not row:
            return None
        return {
            **source_ref("TextTable", name_key, pick_fields(row, "id")),
            "value": named_text(name_key),
            "trace": text_trace("TextTable", name_key, "id", row.get("id")),
        }


    def localized_objective_instruction(key: object) -> dict | None:
        text_key = str(key or "").strip()
        if not text_key:
            return None
        return {
            "key": text_key,
            "text": named_text(text_key),
        }

    def objective_instruction_keys(anchor: dict) -> list[str]:
        keys: list[str] = []
        if anchor.get("descriptionKey"):
            keys.append(str(anchor.get("descriptionKey") or ""))
        keys.extend(str(key) for key in (anchor.get("multipleDescriptionKeys") or []))
        return _unique_preserve(key for key in keys if key)

    def localize_mission_flow(flow: dict | None) -> dict | None:
        if not isinstance(flow, dict):
            return flow
        localized = copy.deepcopy(flow)
        for quest in localized.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            quest_instructions: list[dict] = []
            for anchor in quest.get("objectiveAnchors") or []:
                if not isinstance(anchor, dict):
                    continue
                instructions = [
                    entry
                    for key in objective_instruction_keys(anchor)
                    if (entry := localized_objective_instruction(key))
                ]
                if not instructions:
                    continue
                anchor["objectiveInstructions"] = instructions
                index = anchor.get("index")
                for entry in instructions:
                    row = dict(entry)
                    if index not in (None, ""):
                        row["objectiveIndex"] = index
                    quest_instructions.append(row)
            if quest_instructions:
                quest["objectiveInstructions"] = quest_instructions
        return localized


    npc_templates_by_template_id: dict[str, list[str]] = defaultdict(list)
    for template_row_id, row in npc_templates.items():
        template_id = str(row.get("templateId") or "")
        for candidate in {template_row_id, template_id, norm_template_id(template_id)}:
            if candidate:
                npc_templates_by_template_id[candidate].append(template_row_id)

    npc_data_key_by_id: dict[str, str] = {}
    npc_data_keys_by_group: dict[str, list[str]] = defaultdict(list)
    for npc_row_id, row in npc_rows.items():
        if not isinstance(row, dict):
            continue
        data_key = str(row.get("dataKey") or "").strip()
        if not data_key:
            continue
        for key in (
            str(npc_row_id or "").strip(),
            str(row.get("npcId") or "").strip(),
            str(row.get("normalCfg") or "").strip(),
        ):
            if key and key not in npc_data_key_by_id:
                npc_data_key_by_id[key] = data_key
        group_id = str(row.get("npcGroupId") or "").strip()
        if group_id and data_key not in npc_data_keys_by_group[group_id]:
            npc_data_keys_by_group[group_id].append(data_key)

    def npc_template_row_id_for_candidate(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        candidates = _unique_preserve([raw, norm_template_id(raw)])
        for candidate in candidates:
            if candidate in npc_templates:
                return candidate
            template_row_ids = npc_templates_by_template_id.get(candidate) or []
            if template_row_ids:
                return template_row_ids[0]
        return ""

    def resolve_npc_template_row(row_id: str, row: dict) -> tuple[str, dict | None]:
        candidates: list[str] = []

        def add_candidate(value: str) -> None:
            if not value or value in candidates:
                return
            candidates.append(value)
            norm = norm_template_id(value)
            if norm and norm not in candidates:
                candidates.append(norm)

        add_candidate(row_id)
        for key in ("npcId", "dataKey", "npcGroupId", "normalCfg"):
            value = str(row.get(key) or "")
            add_candidate(value)
            group_base = re.sub(r"_g\d+$", "", value)
            add_candidate(group_base)

        for candidate in candidates:
            if candidate in npc_templates:
                return (candidate, npc_templates[candidate])
            if candidate in npc_templates_by_template_id:
                template_row_id = npc_templates_by_template_id[candidate][0]
                return (template_row_id, npc_templates[template_row_id])
        return ("", None)

    env_npc_meta: dict[str, dict] = {}
    for npc_row_id, row in npc_rows.items():
        env_ids = row.get("envTalkIds") or []
        if not env_ids:
            continue

        template_row_id, template_row = resolve_npc_template_row(npc_row_id, row)
        template_name_key = str((template_row or {}).get("name") or "")
        template_title_key = str((template_row or {}).get("title") or "")

        direct_name = t((row.get("name") or {}).get("id")) if isinstance(row.get("name"), dict) else ""
        direct_title = t((row.get("title") or {}).get("id")) if isinstance(row.get("title"), dict) else ""
        name = direct_name or named_text(template_name_key)
        title = direct_title or named_text(template_title_key)

        meta = {
            "npcId": row.get("npcId") or npc_row_id,
            "npcGroupId": row.get("npcGroupId") or "",
            "dataKey": row.get("dataKey") or "",
            "name": name,
            "title": title,
            "dialogSelector": row.get("dialogSelector") or "",
            "_debug": {
                **source_ref(
                    "NpcTable",
                    npc_row_id,
                    pick_fields(
                        row,
                        "npcId",
                        "npcGroupId",
                        "dataKey",
                        "dialogSelector",
                        "envTalkIds",
                        "name",
                        "title",
                    ),
                ),
                "fields": {
                    "name": text_trace("NpcTable", npc_row_id, "name", row.get("name")),
                    "title": text_trace("NpcTable", npc_row_id, "title", row.get("title")),
                },
            },
        }
        if template_row:
            meta["_debug"]["template"] = source_ref(
                "NpcTemplateGroupTable",
                template_row_id,
                pick_fields(template_row, "npcNameId", "templateId", "name", "title"),
            )
            if template_name_key:
                meta["_debug"]["fields"]["templateName"] = named_text_key_trace(template_name_key)
            if template_title_key:
                meta["_debug"]["fields"]["templateTitle"] = named_text_key_trace(template_title_key)

        for env_id in env_ids:
            env_npc_meta.setdefault(env_id, meta)

    env_story_binding_hints: dict[str, dict[str, set[str] | list[dict]]] = defaultdict(
        lambda: {"levels": set(), "proxies": set(), "sources": []}
    )

    def add_env_story_binding_hint(
        env_id: str,
        *,
        level_id: str = "",
        proxy_id: str = "",
        source: dict | None = None,
    ) -> None:
        env_id = (env_id or "").strip()
        if not env_id:
            return
        hints = env_story_binding_hints[env_id]
        if level_id:
            hints["levels"].add(level_id)
        if proxy_id:
            hints["proxies"].add(proxy_id)
        if source:
            hints["sources"].append(source)

    for row_id, row in npc_proxy_rows.items():
        if not isinstance(row, dict):
            continue
        level_id = str(row.get("levelId") or "")
        proxy_id = str(row.get("proxyId") or row_id or "")
        for env_id in row.get("envTalkIds") or []:
            add_env_story_binding_hint(
                env_id,
                level_id=level_id,
                proxy_id=proxy_id,
                source={
                    "table": "NpcProxyTable",
                    "rowId": row_id,
                    "proxyId": proxy_id,
                    "levelId": level_id,
                },
            )

    for row_id, row in atmos_cluster_rows.items():
        if not isinstance(row, dict):
            continue
        env_id = str(row.get("envTalkId") or "").strip()
        if not env_id:
            continue
        level_id = str(row.get("levelId") or "")
        proxy_id = str(row.get("clusterId") or row_id or "")
        add_env_story_binding_hint(
            env_id,
            level_id=level_id,
            proxy_id=proxy_id,
            source={
                "table": "AtmosphericNpcClusterDataTable",
                "rowId": row_id,
                "clusterId": proxy_id,
                "levelId": level_id,
            },
        )

    # ---------- Story dialog groups ----------
    groups: dict[str, list[tuple[int, str, dict]]] = defaultdict(list)
    misc: list[tuple[str, dict]] = []
    for dlg_id, entry in dialogs.items():
        m = DLG_RE.match(dlg_id)
        if not m:
            misc.append((dlg_id, entry))
            continue
        mission, scene, line = m.group(1), int(m.group(2)), int(m.group(3))
        groups[f"dlg__{mission}__{scene}"].append((line, dlg_id, entry))

    # Build actor display name table.
    # Each actorNameId may have multiple variant names across the game
    # (alias, masked persona, "前缀{真名}", etc.). Keep all distinct ones,
    # but drop the "？？？" / "???" placeholder used for unrevealed identities.
    PLACEHOLDER_NAMES = {"？？？", "???"}
    actor_name_sets: dict[str, set[str]] = defaultdict(set)

    def add_actor_text(aid: str, name: str) -> None:
        if not aid or not name or name in PLACEHOLDER_NAMES:
            return
        actor_name_sets[aid].add(name)

    def add_actor_name(aid: str, name_id) -> None:
        if not aid:
            return
        add_actor_text(aid, t(name_id))

    def scoped_actor_base_candidates(actor_id: str) -> list[str]:
        """Return canonical actor-id candidates from map/base-scoped ids.

        EnvTalk actor ids sometimes encode the speaker as a scoped proxy such
        as `chen_map01_e2m5`. The prefix is still the real speaker id, while
        the suffix only tells us which map/mission proxy emitted the bark.
        Some ids instead use NPC template/group ids, such as
        `npc_spl_andrew_01_g01_map01_lv001_e1m3_001`; resolve those through
        NpcTable and NpcTemplateGroupTable so the browser can show the real
        display name.
        """
        raw = str(actor_id or "").strip()
        if not raw:
            return []
        out: list[str] = []

        def add_candidate(value: str) -> None:
            value = str(value or "").strip()
            if value and value not in out:
                out.append(value)

        add_candidate(raw)
        for marker in ("_map", "_base", "_dung", "_data_sub"):
            idx = raw.find(marker)
            if idx > 0:
                add_candidate(raw[:idx])

        index = 0
        while index < len(out):
            current = out[index]
            index += 1

            if current.startswith("npc_tpl_"):
                add_candidate(norm_template_id(current))

            data_key = npc_data_key_by_id.get(current)
            if data_key:
                add_candidate(data_key)
            for data_key in npc_data_keys_by_group.get(current, []):
                add_candidate(data_key)

            group_base = re.sub(r"_g\d+$", "", current)
            if group_base != current:
                add_candidate(group_base)

            template_row_id = npc_template_row_id_for_candidate(current)
            if template_row_id:
                add_candidate(template_row_id)
                template_row = npc_templates.get(template_row_id) or {}
                add_candidate(str(template_row.get("npcNameId") or ""))

        return out

    def npc_proxy_actor_candidates(proxy_id: str) -> list[str]:
        raw = str(proxy_id or "").strip()
        if not raw:
            return []
        out: list[str] = []
        info = npc_proxy_info.get(raw)
        if isinstance(info, dict):
            for field in ("npcNameId", "npcId"):
                value = str(info.get(field) or "").strip()
                if not value:
                    continue
                out.append(value)
                out.extend(scoped_actor_base_candidates(value))
        out.extend(scoped_actor_base_candidates(raw))
        return _unique_preserve(out)

    def add_actor_template_name(aid: str) -> None:
        if not aid:
            return
        template_row_id = npc_template_row_id_for_candidate(aid)
        row = npc_templates.get(template_row_id) if template_row_id else None
        if not isinstance(row, dict):
            return
        canonical_aid = str(row.get("npcNameId") or "").strip()
        for target_aid in _unique_preserve([aid, canonical_aid]):
            add_actor_text(target_aid, named_text(str(row.get("name") or "")))
            add_actor_text(target_aid, named_text(str(row.get("title") or "")))
        if canonical_aid and actor_name_sets.get(canonical_aid):
            actor_name_sets[aid].update(actor_name_sets[canonical_aid])

    for entry in dialogs.values():
        add_actor_name(entry.get("actorNameId") or "", entry.get("actorName", {}).get("id"))

    for radio in radios.values():
        for item in radio.get("radioSingleDataList", []) or []:
            aid = item.get("actorNameId") or ""
            add_actor_name(aid, item.get("actorName", {}).get("id"))
            add_actor_name(aid, item.get("infoActorName", {}).get("id"))

    # Mail senders cover characters that only surface in inbox/SNS data, so
    # seed the canonical actor table from them before expanding SNS aliases.
    for sender_id, row in mail_senders.items():
        if not isinstance(row, dict):
            continue
        add_actor_name(sender_id, row.get("senderName", {}).get("id"))

    # SNS chat rows provide the visible display name for synthetic ids like
    # `sns_chat_daniel` and a small number of non-`sns_` chat owners that do
    # not correspond to a regular story actor id.
    for sns_id, row in sns_chats.items():
        if not isinstance(row, dict):
            continue
        add_actor_name(sns_id, row.get("name", {}).get("id"))


    # Reuse exported icon metadata instead of guessing SNS aliases from the raw
    # chat id alone. Mail sender data already maps icon asset -> canonical
    # actor key like `pelica` / `andrew`, and SNS chat rows reuse those icons.
    sns_related_ids: dict[str, list[str]] = {}
    icon_to_actor_id: dict[str, str] = {}
    for sender_id, row in mail_senders.items():
        if not isinstance(row, dict):
            continue
        icon = icon_basename(str(row.get("senderIcon") or ""))
        if icon and sender_id:
            icon_to_actor_id.setdefault(icon, sender_id)

    for sns_id, row in sns_chats.items():
        if not sns_id.startswith("sns_") or not isinstance(row, dict):
            continue
        related: list[str] = []

        for icon_field in ("icon", "listIcon"):
            icon = icon_basename(str(row.get(icon_field) or ""))
            mapped = icon_to_actor_id.get(icon)
            if mapped and mapped not in related:
                related.append(mapped)

        core = sns_id[len("sns_"):]
        if core.startswith("chr_"):
            parts = core.split("_")
            if parts and parts[-1] not in related:
                related.append(parts[-1])
        elif core.startswith("npc_"):
            npc_name = core[len("npc_"):]
            if npc_name and npc_name not in related:
                related.append(npc_name)
        elif core and core not in related:
            related.append(core)

        if related:
            sns_related_ids[sns_id] = related

    for sns_id, related_ids in sns_related_ids.items():
        for related_id in related_ids:
            names = actor_name_sets.get(related_id)
            if names:
                actor_name_sets[sns_id].update(names)
                break

    # The generic player/admin id and the female presentation id should share
    # the same resolved display name in the browser data.
    if actor_name_sets.get("endminf"):
        actor_name_sets["endmin"].update(actor_name_sets["endminf"])

    npc_proxy_rows_by_proxy_id: dict[str, tuple[str, dict]] = {}
    env_talk_proxy_ids_by_env: dict[str, list[str]] = defaultdict(list)
    for row_id, row in npc_proxy_rows.items():
        if not isinstance(row, dict):
            continue
        proxy_id = str(row.get("proxyId") or row_id or "").strip()
        if not proxy_id:
            continue
        npc_proxy_rows_by_proxy_id[proxy_id] = (str(row_id), row)
        env_ids = [
            str(env_id).strip()
            for env_id in (row.get("envTalkIds") or [])
            if env_id is not None and str(env_id).strip()
        ]
        if not env_ids:
            continue

        override_name_key = str(((row.get("overrideNpcNameId") or {}).get("key")) or "")
        if row.get("ifOverrideNpcName") and override_name_key:
            add_actor_text(proxy_id, named_text(override_name_key))

        for base_actor_id in npc_proxy_actor_candidates(proxy_id):
            add_actor_template_name(base_actor_id)
            if actor_name_sets.get(base_actor_id):
                actor_name_sets[proxy_id].update(actor_name_sets[base_actor_id])
                break

        for env_id in env_ids:
            env_talk_proxy_ids_by_env[env_id].append(proxy_id)

    for entry in env_talks.values():
        for item in entry.get("envTalkDataList", []) or []:
            scoped_actor_id = str(item.get("actorId") or "")
            for base_actor_id in npc_proxy_actor_candidates(scoped_actor_id):
                add_actor_template_name(base_actor_id)
                if actor_name_sets.get(base_actor_id):
                    actor_name_sets[scoped_actor_id].update(actor_name_sets[base_actor_id])
                    break

    actor_names: dict[str, list[str]] = {
        aid: sorted(names) for aid, names in actor_name_sets.items()
    }

    def speaker_display_name(speaker_id: str) -> str:
        """Best-effort display name for dialog/SNS speaker ids."""
        if not speaker_id:
            return ""

        candidates: list[str] = [speaker_id]
        if speaker_id.startswith("sns_"):
            candidates.append(speaker_id[len("sns_"):])

        core = candidates[-1]
        candidates.extend(npc_proxy_actor_candidates(core))
        if core.startswith("npc_"):
            candidates.append(core[len("npc_"):])
        if core.startswith("chr_"):
            candidates.append(core)
            parts = core.split("_")
            if parts:
                candidates.append(parts[-1])
        elif "_" in core:
            candidates.append(core.split("_")[-1])

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            names = actor_names.get(candidate)
            if names:
                return names[0]

        return ""

    def speaker_actor_id(speaker_id: str) -> str:
        """Resolve a speaker/channel id back to the browser's actor id when possible."""
        if not speaker_id:
            return ""

        candidates: list[str] = [speaker_id]
        if speaker_id.startswith("sns_"):
            candidates.append(speaker_id[len("sns_"):])

        core = candidates[-1]
        candidates.extend(npc_proxy_actor_candidates(core))
        if core.startswith("npc_"):
            candidates.append(core[len("npc_"):])
        if core.startswith("chr_"):
            candidates.append(core)
            parts = core.split("_", 2)
            if len(parts) >= 3:
                candidates.append(parts[2])
        elif "_" in core:
            candidates.append(core.split("_")[-1])

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate in actor_names or re.fullmatch(r"endmin[fm]?", candidate):
                return candidate
        return ""



    def env_index_slot(env_id: str) -> tuple[str, str, str, list[str]]:
        """Return browser slot info for an env-talk entry.

        Most env talks are browsed with the open-world text bucket, while
        operator greeting lines (`greetEnvTalk*`) stay alongside other
        operator-interaction content.
        """
        if env_id.startswith("greetEnvTalk"):
            return ("misc", "greet", "sim", ["envTalk"])
        mission = env_group(env_id)
        return ("env", mission, "worldtext", ["envTalk"])




    def indexed_line_haystack(lines: list[dict], *fields: str) -> str:
        return " ".join(
            part
            for part in (
                line_identity_haystack(lines),
                line_haystack(lines, *fields),
                line_option_haystack(lines),
            )
            if part
        )

    # ---------- SNS dialogs ----------
    sns_groups: dict[str, dict] = {}
    for sns_id, entry in sns.items():
        sns_groups[sns_id] = entry

    # ---------- Extras: summary / options + standalone radio ----------
    # Each attaches to a conversation out_key. Regular dialog scenes emit as
    # `dlg_<mission>_<scene>` (scene is int). Sub-scene dialogs like
    # `dlg_c16m1_4d5_001` end up in misc bucket `misc_dlg_<mission>_<scene>`.
    # We build both possible target keys so extras route correctly.
    dlg_out_keys: set[str] = set()
    for key in groups:
        _, mission, scene_str = key.split("__")
        dlg_out_keys.add(f"dlg_{mission}_{int(scene_str)}")
    sns_out_keys: set[str] = set(sns_groups)
    radio_out_keys: set[str] = set()
    black_out_keys: set[str] = set()
    remotecomm_out_keys: set[str] = set()
    cutscene_out_keys: set[str] = set()
    misc_bucket_keys: set[str] = set()
    for did, _ in misc:
        bkey = re.sub(r"_\d+(_\d+)?$", "", did) or "_misc"
        misc_bucket_keys.add(f"misc_{bkey}")
    known_missions: set[str] = {key.split("__")[1] for key in groups}
    known_missions.update(m.group(1) for sid in sns_groups if (m := SNS_RE.match(sid)))
    for did, _ in misc:
        type_, _act, mission, _scene = slot_misc(re.sub(r"_\d+(_\d+)?$", "", did) or "_misc")
        if type_ != "x" and mission:
            known_missions.add(mission)
    for radio_id in radios:
        if m := RADIO_RE.match(radio_id):
            known_missions.add(m.group(1))
    for remote_id in remote_common:
        if m := REMOTECOMM_RE.match(remote_id):
            known_missions.add(m.group(1))

    env_story_missions: dict[str, str] = {}
    for env_id in env_talks:
        if story_mission := env_story_mission(env_id, known_missions):
            env_story_missions[env_id] = story_mission

    mission_note_by_mission: dict[str, list[dict]] = defaultdict(list)
    for mission_id, row in mission_extra_info.items():
        text = t((row.get("extraInfoDesc") or {}).get("id"))
        if not text:
            continue
        mission_note_by_mission[mission_id].append({
            "missionId": mission_id,
            "type": row.get("extraInfoType", 0),
            "text": text,
            "_debug": {
                **source_ref(
                    "MissionExtraInfoTable",
                    mission_id,
                    pick_fields(row, "missionId", "extraInfoType", "extraInfoDesc"),
                ),
                "fields": {
                    "text": text_trace(
                        "MissionExtraInfoTable",
                        mission_id,
                        "extraInfoDesc",
                        row.get("extraInfoDesc"),
                    ),
                },
            },
        })



    mission_level_refs: dict[str, list[dict]] = defaultdict(list)
    mission_leveldata_host_refs: dict[str, list[dict]] = defaultdict(list)
    seen_leveldata_host_refs: set[tuple[str, str, str, str]] = set()

    def add_leveldata_host_ref(mission_id: str, ref_meta: dict, path: Path, relation: str) -> None:
        if mission_id not in known_missions:
            return
        file_ref = repo_rel(path)
        level_id = ref_meta["level"]
        seen_key = (mission_id, level_id, file_ref, relation)
        if seen_key in seen_leveldata_host_refs:
            return
        seen_leveldata_host_refs.add(seen_key)
        mission_leveldata_host_refs[mission_id].append({
            "levelId": level_id,
            "hostType": level_host_type(level_id),
            "kind": ref_meta["kind"],
            "file": file_ref,
            "token": ref_meta["token"],
            "relation": relation,
        })

    if LEVELDATA_DIR.is_dir():
        for path in LEVELDATA_DIR.rglob("*.json"):
            ref_meta = parse_level_ref_name(path.name)
            if not ref_meta:
                continue
            mission_id = ref_meta["token"]
            add_leveldata_host_ref(mission_id, ref_meta, path, "exact")
            parent_mission_id = re.sub(r"d\d+$", "", mission_id)
            if parent_mission_id != mission_id:
                add_leveldata_host_ref(parent_mission_id, ref_meta, path, "parentVariant")
            if mission_id in known_missions:
                level_id = ref_meta["level"]
                mission_level_refs[mission_id].append({
                    "levelId": level_id,
                    "hostType": level_host_type(level_id),
                    "kind": ref_meta["kind"],
                    "file": repo_rel(path),
                    "_debug": {
                        "source": {
                            "file": repo_rel(path),
                            "levelId": level_id,
                            "kind": ref_meta["kind"],
                            "missionId": mission_id,
                        },
                    },
                })
    for refs in mission_level_refs.values():
        refs.sort(key=lambda ref: (ref["hostType"], ref["levelId"], ref["kind"], ref["file"]))
    for refs in mission_leveldata_host_refs.values():
        refs.sort(key=lambda ref: (ref["hostType"], ref["levelId"], ref["relation"], ref["kind"], ref["file"]))

    def mission_context_text(mission_id: str) -> str:
        if not mission_id:
            return ""
        parts: list[str] = []
        for note in mission_note_by_mission.get(mission_id, []):
            if note.get("text"):
                parts.append(note["text"])
        for ref in mission_level_refs.get(mission_id, []):
            if ref.get("levelId"):
                parts.append(ref["levelId"])
        return " ".join(parts)


    extra_mission_names: dict[str, str] = {}

    def entry_tags(out_key: str, mission: str = "") -> list[str]:
        tags: list[str] = []
        if out_key in summary_by_key:
            tags.append("summary")
        return tags

    def attach_target(mission: str, scene: str, *, allow_sns: bool = False) -> str | None:
        """Pick the out_key that owns (mission, scene), or None if orphan."""
        if re.fullmatch(r"\d+", scene):
            cand = f"dlg_{mission}_{int(scene)}"
            if cand in dlg_out_keys:
                return cand
            if allow_sns:
                cand = f"sns_{mission}_{int(scene)}"
                if cand in sns_out_keys:
                    return cand
        cand = f"misc_dlg_{mission}_{scene}"
        if cand in misc_bucket_keys:
            return cand
        return None

    def dialog_scene_out_key(dialog_id: str) -> str | None:
        if dialog_id in sns_out_keys:
            return dialog_id
        if dialog_id in radio_out_keys:
            return dialog_id
        if dialog_id in black_out_keys or dialog_id in remotecomm_out_keys:
            return dialog_id
        if canonical_cutscene := _canonical_cutscene_key(dialog_id):
            if canonical_cutscene in cutscene_out_keys:
                return canonical_cutscene
        m = re.match(rf"^dlg_(.+)_({SCENE_TOK})$", dialog_id)
        if not m:
            if dialog_id.startswith("dlg_"):
                payload = dialog_id[4:]
                if "_" in payload:
                    mission, scene = payload.split("_", 1)
                    return attach_target(mission, scene)
            return None
        return attach_target(m.group(1), m.group(2))

    summary_by_key: dict[str, list[dict]] = defaultdict(list)
    summary_orphans = 0
    for sid, entry in summaries.items():
        m = SUMMARY_RE.match(sid)
        if not m:
            summary_orphans += 1
            continue
        mission, scene, _idx = m.group(1), m.group(2), m.group(3)
        target = attach_target(mission, scene)
        text = t(entry.get("id"))
        if not text:
            continue
        if target is None:
            summary_orphans += 1
            continue
        summary_by_key[target].append({
            "text": text,
            "_debug": {
                **source_ref("DialogSummaryTable", sid, pick_fields(entry, "id")),
                "fields": {
                    "text": text_trace("DialogSummaryTable", sid, "id", entry.get("id")),
                },
            },
        })

    options_by_key: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    dialog_option_text_by_id: dict[str, str] = {}
    dialog_option_signature_by_id: dict[str, tuple[str, str]] = {}
    dialog_option_payload_by_id: dict[str, dict] = {}
    dialog_option_ids_by_scene_group: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
    option_orphans = 0
    for raw_oid, entry in dlg_opts.items():
        oid = DIALOG_OPTION_ID_CORRECTIONS.get(raw_oid, raw_oid)
        m = OPTION_RE.match(oid)
        if not m:
            # `dlg_spaceship_*` UI options have no scene; skip.
            continue
        mission, scene, grp, idx = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        option_text = t(entry.get("optionText", {}).get("id"))
        option_icon = entry.get("iconType", "") or ""
        option_scene_key = f"dlg_{mission}_{scene}"
        dialog_option_text_by_id[oid] = option_text
        dialog_option_signature_by_id[oid] = (_option_text_signature(option_text), option_icon)
        if oid != raw_oid:
            dialog_option_text_by_id[raw_oid] = option_text
            dialog_option_signature_by_id[raw_oid] = (_option_text_signature(option_text), option_icon)
        dialog_option_ids_by_scene_group[(option_scene_key, grp)].append((idx, oid))
        target = attach_target(mission, scene)
        if target is None:
            option_orphans += 1
            continue
        option_debug = {
            **source_ref(
                "DialogOptionTable",
                raw_oid,
                pick_fields(entry, "optionText", "iconType"),
            ),
            "fields": {
                "text": text_trace(
                    "DialogOptionTable", raw_oid, "optionText", entry.get("optionText")
                ),
            },
        }
        if oid != raw_oid:
            option_debug["idCorrection"] = {
                "from": raw_oid,
                "to": oid,
                "reason": "DialogOptionTable group number disagrees with recovered env_12 menu order.",
            }
        option_entry = {
            "id": oid,
            "i": idx,
            "text": option_text,
            "icon": option_icon,
            "_debug": option_debug,
        }
        options_by_key[target][grp].append(option_entry)
        dialog_option_payload_by_id[oid] = option_entry
    dialog_option_group_ids_by_key: dict[tuple[str, int], list[str]] = {
        key: [oid for _idx, oid in sorted(entries)]
        for key, entries in dialog_option_ids_by_scene_group.items()
    }

    radio_rows: list[dict] = []
    radio_orphans = 0
    radio_targets_seen: set[str] = set()
    for rid, entry in radios.items():
        m = RADIO_RE.match(rid)
        if not m:
            radio_orphans += 1
            continue
        mission, scene = m.group(1), m.group(2)
        target = attach_target(mission, scene, allow_sns=True)
        if target is None:
            radio_orphans += 1
        items = []
        actors: set[str] = set()
        prev_text = ""
        for item in entry.get("radioSingleDataList", []) or []:
            actor_id = item.get("actorNameId", "") or ""
            actor = t(item.get("actorName", {}).get("id"))
            text = t(item.get("radioText", {}).get("id"))
            if actor_id:
                actors.add(actor_id)
            if not prev_text and text:
                prev_text = text
            items.append({
                "id": item.get("id", "") or "",
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "audio": item.get("audioOverride", "") or "",
                "emo": item.get("emotionType", 0),
                "_debug": {
                    **source_ref(
                        "RadioTable.radioSingleDataList",
                        item.get("id", "") or "",
                        pick_fields(
                            item,
                            "id",
                            "actorNameId",
                            "actorName",
                            "infoActorName",
                            "radioText",
                            "audioOverride",
                            "emotionType",
                        ),
                    ),
                    "fields": {
                        "actor": text_trace(
                            "RadioTable.radioSingleDataList",
                            item.get("id", "") or "",
                            "actorName",
                            item.get("actorName"),
                        ),
                        "text": text_trace(
                            "RadioTable.radioSingleDataList",
                            item.get("id", "") or "",
                            "radioText",
                            item.get("radioText"),
                        ),
                    },
                },
            })
        if target:
            radio_targets_seen.add(target)
        type_, act = parse_mission(mission)
        radio_rows.append({
            "k": rid,
            "m": mission,
            "scene": scene,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": sorted(actors),
            "p": preview(prev_text),
            "lines": items,
            "radioType": entry.get("radioType", 0),
            "target": target or "",
            "_debug": source_ref(
                "RadioTable",
                rid,
                pick_fields(entry, "radioType"),
            ),
        })

    def pack_options(
        groups_map: dict[int, list[dict]],
        lines: list[dict] | None = None,
        conv_key: str | None = None,
    ) -> dict:
        """Return option groups sorted by group number, each annotated with an
        `after` field naming the line id after which it should render.

        Primary signal (when available): the AnimeStudio DialogTree graph at
        `exported/AnimeStudio/main/TextAsset/<conv_key>.json`, which stores
        the authoritative option→trunk wiring. Falls back to a gap heuristic:
        DialogTextTable lines are numbered sparsely — slots are reserved for
        player-response audio that isn't stored as dialog text — so a line
        sequence like `_001..006, _008..013, _016..025, _030..041` has three
        gaps where choices happen, and option groups `g=1`, `g=2`, `g=3`
        attach to those gaps in order.
        """
        tree_meta: dict = {}
        tree_after: dict[str, str] = {}
        tree_after_sources: dict[str, list[str]] = {}
        tree_branches: dict[str, list[str]] = {}
        tree_merge: dict[str, str] = {}
        tree_converge: dict[str, str] = {}
        tree_pre: set[str] = set()
        tree_pre_sources: dict[str, list[str]] = {}
        scene_link_after: dict[str, str] = {}
        scene_link_authored_option_ids: set[str] = set()
        scene_link_sources: set[str] = set()
        cinematic_finish_groups: list[dict] = []
        cinematic_after_by_group: dict[int, str] = {}
        cinematic_sources_by_group: dict[int, list[str]] = {}
        cinematic_authored_option_ids: set[str] = set()
        cinematic_sources: set[str] = set()
        text_alias_after_by_group: dict[int, str] = {}
        text_alias_pre_by_group: set[int] = set()
        text_alias_sources_by_group: dict[int, list[str]] = {}
        text_alias_foreign_option_ids_by_group: dict[int, list[str]] = {}
        text_alias_authored_option_ids: set[str] = set()
        text_alias_sources: set[str] = set()
        timeline_entries: list[dict] = []
        timeline_after: dict[str, str] = {}
        timeline_after_line_ids: dict[str, list[str]] = {}
        timeline_after_line_timings: dict[str, dict[str, dict]] = {}
        timeline_option_rows: dict[str, list[dict]] = defaultdict(list)
        timeline_option_routes: dict[str, list[dict]] = defaultdict(list)
        timeline_pre: set[str] = set()
        timeline_authored_option_ids: set[str] = set()
        timeline_sources: set[str] = set()
        if conv_key:
            tree_meta = load_dialog_tree(conv_key) or {}
            tree_after = tree_meta.get("after", {}) or {}
            tree_after_sources = tree_meta.get("afterSources", {}) or {}
            tree_branches = tree_meta.get("branches", {}) or {}
            tree_merge = tree_meta.get("merge", {}) or {}
            tree_converge = tree_meta.get("converge", {}) or {}
            tree_pre_sources = tree_meta.get("preSources", {}) or {}
            cinematic_finish_groups = [
                group
                for group in (tree_meta.get("cinematicFinishGroups") or [])
                if isinstance(group, dict)
            ]
            tree_pre = {
                opt_id
                for opt_id in (tree_meta.get("pre") or [])
                if isinstance(opt_id, str) and opt_id
            }
            for link in load_dialog_tree_scene_links(conv_key) or []:
                source_key = link.get("sourceKey") or ""
                if source_key:
                    scene_link_sources.add(source_key)
                group_after = link.get("after") or ""
                for opt in link.get("options") or []:
                    opt_id = opt.get("optionId") or ""
                    if not opt_id:
                        continue
                    if group_after:
                        scene_link_authored_option_ids.add(opt_id)
                        if opt_id not in scene_link_after:
                            scene_link_after[opt_id] = group_after
            timeline_entries = load_dialog_timeline_line_orders(conv_key)
            for timeline in timeline_entries:
                if not timeline.get("optionAnchors"):
                    continue
                source_key = timeline.get("sourceKey") or timeline.get("timeline") or ""
                file_path = timeline.get("file") or ""
                timeline_line_ids = [
                    str(line_id)
                    for line_id in (timeline.get("lineIds") or [])
                    if str(line_id).strip()
                ]
                timeline_line_timing_by_id = {
                    str(row.get("id") or ""): row
                    for row in (timeline.get("lineTimings") or [])
                    if isinstance(row, dict) and str(row.get("id") or "").strip()
                }
                if source_key:
                    timeline_sources.add(source_key)
                if file_path:
                    timeline_sources.add(file_path)
                for row in timeline.get("optionRows") or []:
                    if not isinstance(row, dict):
                        continue
                    opt_id = str(row.get("id") or "")
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    timeline_option_rows[opt_id].append(row)
                for opt_id, route in (timeline.get("optionRoutes") or {}).items():
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    if isinstance(route, dict):
                        timeline_option_routes[opt_id].append(route)
                for opt_id, anchor in (timeline.get("optionAnchors") or {}).items():
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    if not isinstance(anchor, dict):
                        continue
                    after_id = str(anchor.get("after") or "")
                    if after_id:
                        timeline_authored_option_ids.add(opt_id)
                        timeline_after.setdefault(opt_id, after_id)
                        if timeline_line_ids and opt_id not in timeline_after_line_ids:
                            timeline_after_line_ids[opt_id] = timeline_line_ids
                            timeline_after_line_timings[opt_id] = timeline_line_timing_by_id
                    elif anchor.get("position") == "pre":
                        timeline_authored_option_ids.add(opt_id)
                        timeline_pre.add(opt_id)

        line_idxs: list[tuple[int, str]] = []
        valid_line_ids: set[str] = set()
        if lines:
            for ln in lines:
                lid = ln.get("id") or ""
                if lid:
                    valid_line_ids.add(lid)
                m = re.search(r"_(\d+)$", lid)
                if m:
                    line_idxs.append((int(m.group(1)), lid))
        line_idxs.sort()

        # Fallback anchors when DialogTree/timeline data leaves option groups
        # unanchored. Four signals, in priority order:
        #   1. sparse-gap boundaries — between two contiguous numbering runs,
        #      the player choice plays during the missing slot.
        #   2. timeline option-clip positions — when this conv shares a Unity
        #      Timeline with another scene (e.g. dlg_e2m6_11 + dlg_e2m6_19),
        #      the option clip's start time tells us which of THIS conv's
        #      lines plays just before the choice. We surface that even when
        #      the recorded `_optionId` belongs to the sibling scene.
        #   3. exact group/line number — in contiguous table-only scenes,
        #      option group g=1 follows line _001 by key convention. This is
        #      promoted to a source-keyed anchor rather than a warning-only
        #      fallback because both sides carry the same authored group index.
        #   4. dialog last line — for cinematic-finish patterns where one
        #      option clip drives end-of-arc finish-num branches.
        # All four write to optionGroups[].after; `inferredAnchorMode` in the
        # warning's groupDetails records which signal won.
        fallback_after_ids: list[str] = []
        fallback_group_line_ids: dict[int, str] = {}
        last_line_fallback_id = ""
        if line_idxs:
            fallback_group_line_ids = {
                idx: line_id
                for idx, line_id in line_idxs
            }
            runs: list[list[tuple[int, str]]] = [[line_idxs[0]]]
            for prev, nxt in zip(line_idxs, line_idxs[1:]):
                if nxt[0] == prev[0] + 1:
                    runs[-1].append(nxt)
                else:
                    runs.append([nxt])
            gap_after_ids: list[str] = []
            for run_idx, run in enumerate(runs):
                if run_idx > 0:
                    prev_run = runs[run_idx - 1]
                    if prev_run:
                        gap_after_ids.append(prev_run[-1][1])
            fallback_after_ids.extend(gap_after_ids)
            last_line_fallback_id = line_idxs[-1][1]

        sibling_position_anchors = collect_option_position_anchors(conv_key) if conv_key else []

        group_option_ids_by_group: dict[int, list[str]] = {
            group_id: [
                opt.get("id") or ""
                for opt in sorted(group_opts, key=lambda o: o.get("i", 0))
                if isinstance(opt, dict) and opt.get("id")
            ]
            for group_id, group_opts in groups_map.items()
        }
        option_count_hist = Counter(
            len(group_opt_ids)
            for group_opt_ids in group_option_ids_by_group.values()
            if group_opt_ids
        )

        def cinematic_finish_anchor(finish_group: dict, option_count: int) -> tuple[str, list[str]]:
            finish_nums = finish_group.get("finishNums") or []
            if not isinstance(finish_nums, list) or len(finish_nums) != option_count:
                return "", []
            target_count = finish_group.get("targetCount")
            if isinstance(target_count, int) and target_count and target_count != option_count:
                return "", []
            timeline_name = str(finish_group.get("timeline") or "").strip()
            if not timeline_name:
                return "", []
            source_bits = [
                str(value)
                for value in (
                    finish_group.get("sourceKey"),
                    finish_group.get("file"),
                    timeline_name,
                )
                if str(value or "").strip()
            ]
            for timeline in timeline_entries:
                entry_names = {
                    str(timeline.get("sourceKey") or "").strip(),
                    str(timeline.get("timeline") or "").strip(),
                }
                if timeline_name not in entry_names:
                    continue
                timeline_line_ids = [
                    str(line_id)
                    for line_id in (timeline.get("lineIds") or [])
                    if str(line_id).strip()
                ]
                for line_id in reversed(timeline_line_ids):
                    if line_id in valid_line_ids:
                        if file_path := str(timeline.get("file") or "").strip():
                            source_bits.append(file_path)
                        return line_id, _unique_preserve(source_bits)
            after_id = str(finish_group.get("after") or "").strip()
            if after_id in valid_line_ids:
                return after_id, _unique_preserve(source_bits)
            return "", []

        # Cinematic finish-number branches describe timeline outcomes, not
        # explicit option UI placement. Keep them out of authored option
        # anchoring unless an extracted option clip/node names the current
        # option ids directly.

        def option_signature_sequence(option_ids: list[str]) -> list[tuple[str, str]]:
            signatures: list[tuple[str, str]] = []
            for opt_id in option_ids:
                signature = dialog_option_signature_by_id.get(opt_id)
                if not signature or not signature[0]:
                    return []
                signatures.append(signature)
            return signatures

        def option_signatures_compatible(left_ids: list[str], right_ids: list[str]) -> bool:
            if len(left_ids) != len(right_ids) or not left_ids:
                return False
            for left_id, right_id in zip(left_ids, right_ids):
                left_text, left_icon = dialog_option_signature_by_id.get(left_id, ("", ""))
                right_text, right_icon = dialog_option_signature_by_id.get(right_id, ("", ""))
                if not left_text or not right_text:
                    return False
                if left_icon and right_icon and left_icon != right_icon:
                    return False
                if left_text == right_text:
                    continue
                if left_text in right_text or right_text in left_text:
                    continue
                if SequenceMatcher(None, left_text, right_text).ratio() < 0.92:
                    return False
            return True

        def dialog_line_text_signature(line_id: str) -> str:
            row = dialogs.get(line_id)
            if not isinstance(row, dict):
                return ""
            text_value = t((row.get("dialogText") or {}).get("id"))
            return _option_text_signature(text_value)

        def sibling_scene_text_branch_for_group(
            group_opt_ids: list[str],
            after_id: str,
            sibling_anchor_record: dict | None,
            group_id: int,
        ) -> dict:
            if (
                not group_opt_ids
                or len(group_opt_ids) < 2
                or not after_id
                or not sibling_anchor_record
            ):
                return {}
            sibling_scenes = [
                str(scene_key)
                for scene_key in (sibling_anchor_record.get("siblingScenes") or [])
                if str(scene_key or "").strip() and str(scene_key) != conv_key
            ]
            if not sibling_scenes:
                return {}
            local_line_ids = [line_id for _idx, line_id in line_idxs if line_id in valid_line_ids]
            if after_id in local_line_ids:
                local_candidate_line_ids = local_line_ids[local_line_ids.index(after_id) + 1:]
            else:
                local_candidate_line_ids = local_line_ids
            if not local_candidate_line_ids:
                return {}
            local_signature_by_line_id = {
                line_id: _option_text_signature(str(line.get("text") or ""))
                for line in (lines or [])
                if (line_id := str(line.get("id") or "")) in valid_line_ids
            }
            if not local_signature_by_line_id:
                return {}
            for sibling_scene in sibling_scenes:
                sibling_opt_ids = dialog_option_group_ids_by_key.get((sibling_scene, group_id)) or []
                if not option_signatures_compatible(group_opt_ids, sibling_opt_ids):
                    continue
                sibling_tree = load_dialog_tree(sibling_scene) or {}
                sibling_branches = sibling_tree.get("branches") or {}
                branch_line_ids_by_option: dict[str, list[str]] = {}
                sibling_line_ids_by_option: dict[str, list[str]] = {}
                used_local_line_ids: set[str] = set()
                for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids):
                    sibling_branch_line_ids = [
                        str(line_id)
                        for line_id in (sibling_branches.get(sibling_opt_id) or [])
                        if str(line_id or "").strip()
                    ]
                    if not sibling_branch_line_ids:
                        branch_line_ids_by_option = {}
                        break
                    mapped_line_ids: list[str] = []
                    for sibling_line_id in sibling_branch_line_ids:
                        sibling_signature = dialog_line_text_signature(sibling_line_id)
                        if not sibling_signature:
                            mapped_line_ids = []
                            break
                        matches = [
                            local_line_id
                            for local_line_id in local_candidate_line_ids
                            if local_line_id not in used_local_line_ids
                            and local_signature_by_line_id.get(local_line_id) == sibling_signature
                        ]
                        if len(matches) != 1:
                            mapped_line_ids = []
                            break
                        mapped_line_id = matches[0]
                        used_local_line_ids.add(mapped_line_id)
                        mapped_line_ids.append(mapped_line_id)
                    if not mapped_line_ids:
                        branch_line_ids_by_option = {}
                        break
                    branch_line_ids_by_option[local_opt_id] = mapped_line_ids
                    sibling_line_ids_by_option[local_opt_id] = sibling_branch_line_ids
                if len(branch_line_ids_by_option) != len(group_opt_ids):
                    continue
                if len({tuple(line_ids) for line_ids in branch_line_ids_by_option.values()}) < 2:
                    continue
                sibling_option_ids_by_option = {
                    local_opt_id: sibling_opt_id
                    for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids)
                }
                source_bits = _unique_preserve([
                    str(value)
                    for value in (
                        sibling_scene,
                        sibling_tree.get("sourceKey") or "",
                        sibling_tree.get("file") or "",
                        sibling_anchor_record.get("timeline") or "",
                    )
                    if str(value or "").strip()
                ])
                return {
                    "code": "siblingSceneTextBranches",
                    "reason": "siblingSceneTextMatch",
                    "detail": (
                        "A sibling scene on the same dialog Timeline has authored "
                        "SceneGraph option branches whose branch texts exactly "
                        "match local lines after this fallback option anchor."
                    ),
                    "after": after_id,
                    "optionIds": group_opt_ids,
                    "branchLineIdsByOption": branch_line_ids_by_option,
                    "siblingScene": sibling_scene,
                    "siblingOptionIdsByOption": sibling_option_ids_by_option,
                    "siblingBranchLineIdsByOption": sibling_line_ids_by_option,
                    "source": "siblingSceneGraphText",
                    "sources": source_bits,
                }
            return {}

        def sibling_scene_template_branch_for_group(
            group_opt_ids: list[str],
            after_id: str,
            group_id: int,
        ) -> dict:
            if not group_opt_ids or len(group_opt_ids) < 2:
                return {}
            local_line_ids = [line_id for _idx, line_id in line_idxs if line_id in valid_line_ids]
            if len(local_line_ids) < 3:
                return {}
            local_signature_by_line_id = {
                line_id: _option_text_signature(str(line.get("text") or ""))
                for line in (lines or [])
                if (line_id := str(line.get("id") or "")) in valid_line_ids
            }
            if not local_signature_by_line_id:
                return {}
            local_option_signatures = option_signature_sequence(group_opt_ids)
            if not local_option_signatures:
                return {}
            sibling_group_keys = [
                key
                for key in dialog_option_group_ids_by_key
                if key[1] == group_id and key[0] != conv_key
            ]
            sibling_group_keys.sort(key=lambda key: key[0])
            for sibling_scene, _sibling_group_id in sibling_group_keys:
                sibling_opt_ids = dialog_option_group_ids_by_key.get((sibling_scene, group_id)) or []
                if len(sibling_opt_ids) != len(group_opt_ids):
                    continue
                sibling_signatures = option_signature_sequence(sibling_opt_ids)
                if not sibling_signatures:
                    continue
                compatible_positions = 0
                icons_compatible = True
                for (local_text, local_icon), (sibling_text, sibling_icon) in zip(local_option_signatures, sibling_signatures):
                    if local_icon and sibling_icon and local_icon != sibling_icon:
                        icons_compatible = False
                        break
                    if local_text == sibling_text or local_text in sibling_text or sibling_text in local_text:
                        compatible_positions += 1
                    elif SequenceMatcher(None, local_text, sibling_text).ratio() >= 0.92:
                        compatible_positions += 1
                if not icons_compatible or compatible_positions < max(2, len(group_opt_ids) - 1):
                    continue

                sibling_tree = load_dialog_tree(sibling_scene) or {}
                sibling_branches = sibling_tree.get("branches") or {}
                sibling_after = sibling_tree.get("after") or {}
                if not sibling_branches:
                    continue
                sibling_after_ids = [
                    str(sibling_after.get(opt_id) or "")
                    for opt_id in sibling_opt_ids
                    if str(sibling_after.get(opt_id) or "").strip()
                ]
                if len(set(sibling_after_ids)) != 1:
                    continue
                sibling_after_id = sibling_after_ids[0]
                sibling_after_text = dialog_line_text_signature(sibling_after_id)
                if not sibling_after_text:
                    continue
                local_after_candidates = [
                    local_line_id
                    for local_line_id in local_line_ids
                    if (
                        local_signature_by_line_id.get(local_line_id) == sibling_after_text
                        or SequenceMatcher(
                            None,
                            local_signature_by_line_id.get(local_line_id) or "",
                            sibling_after_text,
                        ).ratio() >= 0.80
                    )
                ]
                if not local_after_candidates:
                    continue

                branch_line_ids_by_option: dict[str, list[str]] = {}
                sibling_line_ids_by_option: dict[str, list[str]] = {}
                used_local_line_ids: set[str] = set()
                missing_options: list[tuple[str, str, list[str]]] = []
                for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids):
                    sibling_branch_line_ids = [
                        str(line_id)
                        for line_id in (sibling_branches.get(sibling_opt_id) or [])
                        if str(line_id or "").strip()
                    ]
                    if not sibling_branch_line_ids:
                        branch_line_ids_by_option = {}
                        break
                    mapped_line_ids: list[str] = []
                    for sibling_line_id in sibling_branch_line_ids:
                        sibling_signature = dialog_line_text_signature(sibling_line_id)
                        if not sibling_signature:
                            mapped_line_ids = []
                            break
                        matches = [
                            local_line_id
                            for local_line_id in local_line_ids
                            if local_line_id not in used_local_line_ids
                            and local_signature_by_line_id.get(local_line_id) == sibling_signature
                        ]
                        if len(matches) != 1:
                            mapped_line_ids = []
                            break
                        mapped_line_id = matches[0]
                        used_local_line_ids.add(mapped_line_id)
                        mapped_line_ids.append(mapped_line_id)
                    if mapped_line_ids:
                        branch_line_ids_by_option[local_opt_id] = mapped_line_ids
                        sibling_line_ids_by_option[local_opt_id] = sibling_branch_line_ids
                    else:
                        missing_options.append((local_opt_id, sibling_opt_id, sibling_branch_line_ids))
                if not branch_line_ids_by_option or len(missing_options) > 1:
                    continue

                mapped_indices = [
                    local_line_ids.index(line_id)
                    for mapped_lines in branch_line_ids_by_option.values()
                    for line_id in mapped_lines
                    if line_id in local_line_ids
                ]
                if not mapped_indices:
                    continue
                earliest_mapped_index = min(mapped_indices)
                local_after_id = ""
                for candidate in reversed(local_after_candidates):
                    candidate_index = local_line_ids.index(candidate)
                    if candidate_index < earliest_mapped_index:
                        local_after_id = candidate
                        break
                if not local_after_id:
                    continue
                after_index = local_line_ids.index(local_after_id)
                if after_id and after_id in local_line_ids and local_line_ids.index(after_id) > after_index:
                    continue
                if missing_options:
                    local_opt_id, sibling_opt_id, sibling_branch_line_ids = missing_options[0]
                    inferred_lines = [
                        line_id
                        for line_id in local_line_ids[after_index + 1:earliest_mapped_index]
                        if line_id not in used_local_line_ids
                    ]
                    if not inferred_lines:
                        continue
                    branch_line_ids_by_option[local_opt_id] = inferred_lines
                    sibling_line_ids_by_option[local_opt_id] = sibling_branch_line_ids
                if len(branch_line_ids_by_option) != len(group_opt_ids):
                    continue
                if len({tuple(line_ids) for line_ids in branch_line_ids_by_option.values()}) < 2:
                    continue
                sibling_option_ids_by_option = {
                    local_opt_id: sibling_opt_id
                    for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids)
                }
                source_bits = _unique_preserve([
                    str(value)
                    for value in (
                        sibling_scene,
                        sibling_tree.get("sourceKey") or "",
                        sibling_tree.get("file") or "",
                    )
                    if str(value or "").strip()
                ])
                return {
                    "code": "siblingSceneTextBranches",
                    "reason": "siblingSceneTemplate",
                    "detail": (
                        "A sibling scene has authored SceneGraph option branches "
                        "with matching option layout and repeated local branch text; "
                        "unmatched local lines between the sibling-matched anchor and "
                        "the first matched branch are assigned to the remaining option."
                    ),
                    "after": local_after_id,
                    "previousAfter": after_id,
                    "optionIds": group_opt_ids,
                    "branchLineIdsByOption": branch_line_ids_by_option,
                    "siblingScene": sibling_scene,
                    "siblingOptionIdsByOption": sibling_option_ids_by_option,
                    "siblingBranchLineIdsByOption": sibling_line_ids_by_option,
                    "source": "siblingSceneGraphText",
                    "sources": source_bits,
                }
            return {}

        def source_bits_for_options(option_ids: list[str], source_map: dict[str, object]) -> list[str]:
            source_bits: list[str] = []
            for opt_id in option_ids:
                raw_sources = source_map.get(opt_id) if isinstance(source_map, dict) else None
                if isinstance(raw_sources, list):
                    source_bits.extend(str(source) for source in raw_sources if str(source or "").strip())
                elif raw_sources:
                    source_bits.append(str(raw_sources))
            return _unique_preserve(source_bits)

        def complete_foreign_option_group(
            group_key: tuple[str, int],
            raw_entries: list[tuple[int, str]],
        ) -> list[str]:
            foreign_ids = [
                opt_id
                for _idx, opt_id in sorted(raw_entries, key=lambda item: item[0])
                if opt_id
            ]
            if not foreign_ids or len(set(foreign_ids)) != len(foreign_ids):
                return []
            full_foreign_ids = dialog_option_group_ids_by_key.get(group_key) or []
            if not full_foreign_ids or foreign_ids != full_foreign_ids:
                return []
            return foreign_ids

        foreign_after_groups: dict[tuple[str, int], list[tuple[int, str, str]]] = defaultdict(list)
        for foreign_opt_id, raw_after in tree_after.items():
            parts = _option_id_group_parts(foreign_opt_id)
            candidate_after = str(raw_after or "")
            if not parts or not candidate_after or candidate_after not in valid_line_ids:
                continue
            scene_key, foreign_group_id, foreign_index = parts
            if scene_key == conv_key:
                continue
            foreign_after_groups[(scene_key, foreign_group_id)].append(
                (foreign_index, foreign_opt_id, candidate_after)
            )

        foreign_pre_groups: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
        for foreign_opt_id in tree_pre:
            parts = _option_id_group_parts(foreign_opt_id)
            if not parts:
                continue
            scene_key, foreign_group_id, foreign_index = parts
            if scene_key == conv_key:
                continue
            foreign_pre_groups[(scene_key, foreign_group_id)].append((foreign_index, foreign_opt_id))

        for group_id, group_opt_ids in group_option_ids_by_group.items():
            local_signature = option_signature_sequence(group_opt_ids)
            if not local_signature:
                continue

            after_matches: list[tuple[str, list[str], list[str]]] = []
            for foreign_group_key, raw_entries in foreign_after_groups.items():
                ordered_entries = sorted(raw_entries, key=lambda item: item[0])
                foreign_ids = complete_foreign_option_group(
                    foreign_group_key,
                    [(idx, opt_id) for idx, opt_id, _after in ordered_entries],
                )
                if len(foreign_ids) != len(group_opt_ids):
                    continue
                anchors = {after for _idx, _opt_id, after in ordered_entries}
                if len(anchors) != 1:
                    continue
                if option_signature_sequence(foreign_ids) != local_signature:
                    continue
                source_bits = source_bits_for_options(foreign_ids, tree_after_sources)
                after_matches.append((next(iter(anchors)), foreign_ids, source_bits))

            # Exact text/icon aliases are useful investigation hints, but they
            # are not firm authored placement for the current option ids.
            # Only direct extracted references may anchor options.
            if len(after_matches) == 1:
                continue

            pre_matches: list[tuple[list[str], list[str]]] = []
            for foreign_group_key, raw_entries in foreign_pre_groups.items():
                foreign_ids = complete_foreign_option_group(foreign_group_key, raw_entries)
                if len(foreign_ids) != len(group_opt_ids):
                    continue
                if option_signature_sequence(foreign_ids) != local_signature:
                    continue
                source_bits = source_bits_for_options(foreign_ids, tree_pre_sources)
                pre_matches.append((foreign_ids, source_bits))

            if len(pre_matches) == 1:
                continue

        out: list[dict] = []
        authored_option_ids = (
            set(tree_after)
            | set(tree_branches)
            | set(tree_merge)
            | tree_pre
            | scene_link_authored_option_ids
            | timeline_authored_option_ids
        )
        authored_group_count = 0
        pre_group_count = 0
        keyed_group_count = 0
        sibling_text_group_count = 0
        fallback_group_count = 0
        unanchored_group_count = 0
        fallback_group_labels: list[str] = []
        group_details: list[dict] = []
        option_response_risks: list[dict] = []
        manual_option_response_overrides: list[dict] = []

        def preferred_timeline_option_row(opt_id: str) -> dict:
            rows = timeline_option_rows.get(opt_id) or []
            if not rows:
                return {}
            return min(
                rows,
                key=lambda row: (
                    0 if row.get("anchorMode") == "trunkBinding" else 1,
                    float(row.get("start") or 0.0),
                    row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
                    row.get("assetTrack") or "",
                ),
            )

        def preferred_timeline_option_route(opt_id: str) -> dict:
            routes = timeline_option_routes.get(opt_id) or []
            if not routes:
                return {}
            return max(
                routes,
                key=lambda route: (
                    len(route.get("pathLineIds") or []),
                    -float(route.get("start") or 0.0),
                    str(route.get("source") or ""),
                ),
            )

        def timeline_route_branch_for_group(group_opt_ids: list[str], after_id: str) -> dict:
            if len(group_opt_ids) < 2 or not after_id:
                return {}
            if any(tree_branches.get(opt_id) for opt_id in group_opt_ids):
                return {}
            anchors = [timeline_after.get(opt_id) or "" for opt_id in group_opt_ids]
            if not all(anchor == after_id for anchor in anchors):
                return {}
            routes = [preferred_timeline_option_route(opt_id) for opt_id in group_opt_ids]
            # A route is acceptable when either it lists per-option lines OR it
            # flags `terminatesSlot` — the latter means the option's Runtime
            # Jump skip range covers the whole post-anchor window so no in-slot
            # lines play.
            if not all(
                route.get("pathLineIds") or route.get("terminatesSlot")
                for route in routes
            ):
                return {}
            branch_line_ids_by_option: dict[str, list[str]] = {}
            skipped_line_ids_by_option: dict[str, list[str]] = {}
            reverse_range_line_ids_by_option: dict[str, list[str]] = {}
            terminating_option_ids: list[str] = []
            for opt_id, route in zip(group_opt_ids, routes):
                path_line_ids = [
                    str(line_id)
                    for line_id in (route.get("pathLineIds") or [])
                    if line_id in valid_line_ids
                ]
                terminates_slot = bool(route.get("terminatesSlot"))
                if terminates_slot and not path_line_ids:
                    terminating_option_ids.append(opt_id)
                elif not path_line_ids:
                    return {}
                branch_line_ids_by_option[opt_id] = path_line_ids
                skipped_line_ids_by_option[opt_id] = [
                    str(line_id)
                    for line_id in (route.get("skippedLineIds") or [])
                    if line_id in valid_line_ids
                ]
                reverse_range_line_ids_by_option[opt_id] = [
                    str(line_id)
                    for line_id in (route.get("reverseRangeLineIds") or [])
                    if line_id in valid_line_ids
                ]
            distinct_branch_signatures = {
                ("__terminatesSlot__",) if opt_id in terminating_option_ids else tuple(value)
                for opt_id, value in branch_line_ids_by_option.items()
            }
            if len(distinct_branch_signatures) < 2:
                return {}
            continuation_option_ids = _unique_preserve([
                str(option_id)
                for route in routes
                for option_id in (route.get("continuationOptionIds") or [])
                if str(option_id or "").strip()
            ])
            payload = {
                "code": "timelineRouteBranches",
                "reason": "runtimeJumpTrack",
                "detail": (
                    "Runtime Jump Track clips in the dialog Timeline mark "
                    "which time ranges each selected optionIndex skips or "
                    "re-enters; branch lines are recovered from those "
                    "directional route windows."
                ),
                "after": after_id,
                "optionIds": group_opt_ids,
                "branchLineIdsByOption": branch_line_ids_by_option,
                "skippedLineIdsByOption": skipped_line_ids_by_option,
                "reverseRangeLineIdsByOption": {
                    opt_id: line_ids
                    for opt_id, line_ids in reverse_range_line_ids_by_option.items()
                    if line_ids
                },
                "continuationOptionIds": continuation_option_ids,
                "source": "dialogTimeline",
                "optionIndex": [
                    route.get("optionIndex")
                    for route in routes
                ],
                "assetTracks": _unique_preserve([
                    str(raw_range.get("track") or raw_range.get("assetTrack") or "")
                    for route in routes
                    for raw_range in ((route.get("skipRanges") or []) + (route.get("reverseRanges") or []))
                    if str(raw_range.get("track") or raw_range.get("assetTrack") or "").strip()
                ]),
            }
            if terminating_option_ids:
                payload["terminatingOptionIds"] = terminating_option_ids
            return payload

        def following_line_risk_for_group(group_opt_ids: list[str], after_id: str) -> dict:
            if len(group_opt_ids) < 2 or not after_id:
                return {}
            if any(tree_branches.get(opt_id) for opt_id in group_opt_ids):
                return {}
            anchors = [timeline_after.get(opt_id) or "" for opt_id in group_opt_ids]
            if not all(anchor == after_id for anchor in anchors):
                return {}
            # Dialog tree shows all options converge to the same response trunk.
            # Only emit cosmeticChoice when Timeline anchors already matched (so this
            # is a group that would otherwise have become inferredFollowingLines).
            if all(opt_id in tree_converge for opt_id in group_opt_ids):
                trunk_ids = {tree_converge[opt_id] for opt_id in group_opt_ids}
                if len(trunk_ids) == 1:
                    common_trunk = next(iter(trunk_ids))
                    if common_trunk in valid_line_ids:
                        return {
                            "code": "cosmeticChoice",
                            "reason": "treeSourcedConvergence",
                            "detail": (
                                "Dialog tree shows all options in this group lead to the "
                                "same response trunk; the choice affects only the player's "
                                "displayed text, not which line plays next."
                            ),
                            "after": after_id,
                            "optionIds": group_opt_ids,
                            "candidateLineIds": [],
                            "commonContinuationLineId": common_trunk,
                            "source": "dialogTree",
                        }
            timeline_line_ids: list[str] = []
            timeline_line_timing_by_id: dict[str, dict] = {}
            for opt_id in group_opt_ids:
                candidate_order = timeline_after_line_ids.get(opt_id) or []
                if after_id in candidate_order:
                    timeline_line_ids = candidate_order
                    timeline_line_timing_by_id = timeline_after_line_timings.get(opt_id) or {}
                    break
            if not timeline_line_ids or after_id not in timeline_line_ids:
                return {}
            after_index = timeline_line_ids.index(after_id)
            candidate_line_ids = [
                line_id
                for line_id in timeline_line_ids[after_index + 1 : after_index + 1 + len(group_opt_ids)]
                if line_id in valid_line_ids
            ]
            if len(candidate_line_ids) != len(group_opt_ids):
                return {}
            common_continuation_id = ""
            for line_id in timeline_line_ids[after_index + 1 + len(group_opt_ids) :]:
                if line_id in valid_line_ids:
                    common_continuation_id = line_id
                    break
            preferred_rows = [preferred_timeline_option_row(opt_id) for opt_id in group_opt_ids]
            option_indices = [
                row.get("optionIndex") if isinstance(row.get("optionIndex"), int) else None
                for row in preferred_rows
            ]
            candidate_clip_indices = [
                (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
                for line_id in candidate_line_ids
            ]
            def index_pattern(values: list[object]) -> str:
                ints = [value for value in values if isinstance(value, int)]
                if not ints:
                    return "missing"
                if len(ints) < len(values):
                    return "partialMissing"
                has_zero = any(value == 0 for value in ints)
                has_nonzero = any(value != 0 for value in ints)
                if has_zero and has_nonzero:
                    return "mixedZeroNonzero"
                if has_zero:
                    return "allZero"
                if has_nonzero:
                    return "strictNonzero"
                return "other"

            if (
                candidate_clip_indices
                and len(candidate_clip_indices) == len(candidate_line_ids)
                and all(value == 0 for value in candidate_clip_indices)
            ):
                option_index_pattern = index_pattern(option_indices)
                candidate_clip_index_pattern = index_pattern(candidate_clip_indices)
                if option_index_pattern in {"allZero", "mixedZeroNonzero"}:
                    reason = "defaultTrunkClipContinuation"
                    detail = (
                        "Runtime selection maps the selected UI option through "
                        "DialogTimelineOptionData.optionIndex before advancing "
                        "the Timeline. The adjacent trunk candidate clips all "
                        "carry clipOptionIndex 0, and no Runtime Jump route was "
                        "recovered for this group, so the window is kept as a "
                        "shared Timeline continuation instead of inferred "
                        "per-option branch replies."
                    )
                    if option_index_pattern == "allZero":
                        reason = "rawOptionIndexConverges"
                        detail = (
                            "Runtime selection maps the selected UI option through "
                            "DialogTimelineOptionData.optionIndex before advancing "
                            "the Timeline. All option rows in this group resolve to "
                            "raw optionIndex 0, so the adjacent trunk lines are kept "
                            "as shared continuation instead of inferred per-option "
                            "branch replies."
                        )
                    return {
                        "code": "sharedTimelineContinuation",
                        "reason": reason,
                        "detail": detail,
                        "after": after_id,
                        "optionIds": group_opt_ids,
                        "candidateLineIds": [],
                        "candidateWindowLineIds": candidate_line_ids,
                        "commonContinuationLineId": candidate_line_ids[0],
                        "source": "dialogTimeline",
                        "optionIndex": option_indices,
                        "candidateLineClipOptionIndex": candidate_clip_indices,
                        "optionIndexPattern": option_index_pattern,
                        "candidateLineClipOptionIndexPattern": candidate_clip_index_pattern,
                    }
            candidate_mapping = ""
            branch_line_ids_by_option: dict[str, list[str]] = {}
            branch_clip_indices_by_option: dict[str, list[int]] = {}
            if (
                len(candidate_clip_indices) == len(candidate_line_ids) == len(option_indices)
                and all(isinstance(value, int) for value in candidate_clip_indices)
                and all(isinstance(value, int) for value in option_indices)
                and len(set(candidate_clip_indices)) == len(candidate_clip_indices)
                and set(candidate_clip_indices) == set(option_indices)
            ):
                line_id_by_clip_index = {
                    clip_index: line_id
                    for line_id, clip_index in zip(candidate_line_ids, candidate_clip_indices)
                }
                reordered_candidate_line_ids = [
                    line_id_by_clip_index.get(option_index)
                    for option_index in option_indices
                ]
                if (
                    len(reordered_candidate_line_ids) == len(candidate_line_ids)
                    and all(line_id in valid_line_ids for line_id in reordered_candidate_line_ids)
                ):
                    candidate_line_ids = [str(line_id) for line_id in reordered_candidate_line_ids]
                    candidate_mapping = "trunkClipOptionIndex"
                    candidate_clip_indices = [
                        (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
                        for line_id in candidate_line_ids
                    ]
                    option_index_set = {value for value in option_indices if isinstance(value, int) and value != 0}
                    branch_line_ids_by_index: dict[int, list[str]] = {value: [] for value in option_index_set}
                    branch_clip_indices_by_index: dict[int, list[int]] = {value: [] for value in option_index_set}
                    branch_window_end_index = after_index + len(candidate_line_ids)
                    for index, line_id in enumerate(timeline_line_ids[after_index + 1 :], start=after_index + 1):
                        if line_id not in valid_line_ids:
                            continue
                        clip_index = (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
                        if isinstance(clip_index, int) and clip_index in option_index_set:
                            branch_line_ids_by_index.setdefault(clip_index, []).append(line_id)
                            branch_clip_indices_by_index.setdefault(clip_index, []).append(clip_index)
                            branch_window_end_index = index
                            continue
                        break
                    for opt_id, option_index in zip(group_opt_ids, option_indices):
                        if not isinstance(option_index, int):
                            continue
                        branch_lines = [
                            line_id
                            for line_id in (branch_line_ids_by_index.get(option_index) or [])
                            if line_id in valid_line_ids
                        ]
                        if not branch_lines:
                            branch_lines = [
                                line_id
                                for line_id in [line_id_by_clip_index.get(option_index)]
                                if line_id in valid_line_ids
                            ]
                        if branch_lines:
                            branch_line_ids_by_option[opt_id] = branch_lines
                            branch_clip_indices_by_option[opt_id] = [
                                int(value)
                                for value in (branch_clip_indices_by_index.get(option_index) or [option_index])
                                if isinstance(value, int)
                            ]
                    for line_id in timeline_line_ids[branch_window_end_index + 1 :]:
                        if line_id in valid_line_ids:
                            common_continuation_id = line_id
                            break
            detail = (
                "Timeline option metadata anchors this group to a trunk line, "
                "but the option entries do not name explicit target trunk ids; "
                "the following line candidates are inferred from Timeline order."
            )
            if candidate_mapping:
                detail = (
                    "Timeline option metadata anchors this group to a trunk line, "
                    "but the option entries do not name explicit target trunk ids; "
                    "candidate response lines and same-index branch continuations "
                    "are matched to options by the raw trunk clip optionIndex values."
                )
            risk = {
                "code": "inferredFollowingLines",
                "reason": "optionTargetsMissing",
                "detail": detail,
                "after": after_id,
                "optionIds": group_opt_ids,
                "candidateLineIds": candidate_line_ids,
                "commonContinuationLineId": common_continuation_id,
                "source": "dialogTimeline",
                "optionIndex": [
                    row.get("optionIndex")
                    for row in preferred_rows
                ],
                "assetTracks": _unique_preserve([
                    str(row.get("assetTrack") or "")
                    for row in preferred_rows
                    if row.get("assetTrack")
                ]),
            }
            if candidate_mapping:
                risk["candidateMapping"] = candidate_mapping
                risk["candidateLineIdsByOption"] = {
                    opt_id: branch_line_ids_by_option.get(opt_id) or [line_id]
                    for opt_id, line_id in zip(group_opt_ids, candidate_line_ids)
                }
                risk["candidateLineClipOptionIndex"] = candidate_clip_indices
                if branch_line_ids_by_option:
                    risk["branchLineIdsByOption"] = branch_line_ids_by_option
                if branch_clip_indices_by_option:
                    risk["branchLineClipOptionIndexByOption"] = branch_clip_indices_by_option
            return risk

        def option_risk_line_ids(following_line_risk: dict, option_count: int) -> list[str]:
            option_ids = [
                str(option_id)
                for option_id in (following_line_risk.get("optionIds") or [])
                if str(option_id or "").strip()
            ]
            candidate_lines_by_option = following_line_risk.get("candidateLineIdsByOption")
            if isinstance(candidate_lines_by_option, dict) and len(option_ids) == option_count:
                mapped_line_ids: list[str] = []
                for option_id in option_ids:
                    mapped_value = candidate_lines_by_option.get(option_id)
                    if isinstance(mapped_value, list):
                        line_id = next(
                            (
                                str(value)
                                for value in mapped_value
                                if str(value or "") in valid_line_ids
                            ),
                            "",
                        )
                    else:
                        line_id = str(mapped_value or "")
                    if line_id not in valid_line_ids:
                        break
                    mapped_line_ids.append(line_id)
                if len(mapped_line_ids) == option_count:
                    return mapped_line_ids
            candidate_line_ids = [
                str(line_id)
                for line_id in (following_line_risk.get("candidateLineIds") or [])
                if line_id in valid_line_ids
            ]
            if len(candidate_line_ids) == option_count:
                return candidate_line_ids
            common_line_id = str(following_line_risk.get("commonContinuationLineId") or "")
            if common_line_id in valid_line_ids:
                return [common_line_id for _ in range(option_count)]
            return []

        def all_option_response_risk_line_ids(following_line_risk: dict) -> list[str]:
            out: list[str] = []

            def push(line_id: object) -> None:
                value = str(line_id or "")
                if value and value in valid_line_ids and value not in out:
                    out.append(value)

            for line_id in following_line_risk.get("candidateLineIds") or []:
                push(line_id)
            branch_lines_by_option = following_line_risk.get("branchLineIdsByOption")
            if isinstance(branch_lines_by_option, dict):
                for line_ids in branch_lines_by_option.values():
                    if isinstance(line_ids, list):
                        for line_id in line_ids:
                            push(line_id)
                    else:
                        push(line_ids)
            return out

        sorted_group_ids = sorted(groups_map)
        sorted_group_index = {group_id: idx for idx, group_id in enumerate(sorted_group_ids)}
        local_ordered_line_ids = [line_id for _idx, line_id in line_idxs if line_id in valid_line_ids]
        local_line_order_index = {
            line_id: idx for idx, line_id in enumerate(local_ordered_line_ids)
        }
        trusted_group_after_cache: dict[int, tuple[str, dict]] = {}
        recovered_single_option_line_ids: set[str] = set()

        def previous_visible_line_id(line_id: str) -> str:
            idx = local_line_order_index.get(line_id)
            if idx is None or idx <= 0:
                return ""
            return local_ordered_line_ids[idx - 1]

        def trusted_recovered_group_after(group_id: int) -> tuple[str, dict]:
            if group_id in trusted_group_after_cache:
                return trusted_group_after_cache[group_id]
            group_ids = group_option_ids_by_group.get(group_id, [])
            result: tuple[str, dict] = ("", {})
            if len(group_ids) >= 2:
                candidate = sibling_scene_template_branch_for_group(
                    group_ids,
                    fallback_group_line_ids.get(group_id, ""),
                    group_id,
                )
                candidate_after = str(candidate.get("after") or "")
                if candidate_after in valid_line_ids:
                    result = (candidate_after, candidate)
            elif len(group_ids) == 1:
                group_pos = sorted_group_index.get(group_id)
                if group_pos is not None:
                    for later_group_id in sorted_group_ids[group_pos + 1:]:
                        later_after, later_risk = trusted_recovered_group_after(later_group_id)
                        if later_after not in valid_line_ids:
                            continue
                        inferred_after = previous_visible_line_id(later_after)
                        if inferred_after in valid_line_ids:
                            result = (
                                inferred_after,
                                {
                                    "code": "siblingSceneTextBranches",
                                    "reason": "singleOptionSpanBeforeRecoveredAnchor",
                                    "detail": (
                                        "A later option group is recovered from sibling SceneGraph "
                                        "branch evidence; this single-option group occupies the "
                                        "contiguous line span immediately before that recovered anchor."
                                    ),
                                    "after": inferred_after,
                                    "nextRecoveredGroup": later_group_id,
                                    "nextRecoveredAfter": later_after,
                                    "nextRecoveredReason": later_risk.get("reason") or "",
                                    "source": later_risk.get("source") or "siblingSceneGraphText",
                                    "sources": later_risk.get("sources") or [],
                                },
                            )
                        break
            trusted_group_after_cache[group_id] = result
            return result

        def single_option_span_before_recovered_anchor(
            group_id: int,
            group_opt_ids: list[str],
            after_id: str,
        ) -> dict:
            if len(group_opt_ids) != 1 or after_id not in valid_line_ids:
                return {}
            group_pos = sorted_group_index.get(group_id)
            if group_pos is None:
                return {}
            next_after = ""
            next_group_id = 0
            next_risk: dict = {}
            for later_group_id in sorted_group_ids[group_pos + 1:]:
                candidate_after, candidate_risk = trusted_recovered_group_after(later_group_id)
                if candidate_after in valid_line_ids:
                    next_after = candidate_after
                    next_group_id = later_group_id
                    next_risk = candidate_risk
                    break
            if next_after not in valid_line_ids:
                return {}
            start_index = local_line_order_index.get(after_id)
            end_index = local_line_order_index.get(next_after)
            if start_index is None or end_index is None or end_index <= start_index:
                return {}
            candidate_lines = [
                line_id
                for line_id in local_ordered_line_ids[start_index + 1:end_index + 1]
                if line_id not in recovered_single_option_line_ids
            ]
            if not candidate_lines:
                return {}
            inferred_after = previous_visible_line_id(candidate_lines[0])
            if inferred_after not in valid_line_ids:
                return {}
            return {
                "code": "siblingSceneTextBranches",
                "reason": "singleOptionSpanBeforeRecoveredAnchor",
                "detail": (
                    "A later option group is recovered from sibling SceneGraph "
                    "branch evidence; this single-option group consumes the "
                    "remaining contiguous line span before that recovered anchor."
                ),
                "after": inferred_after,
                "previousAfter": after_id,
                "optionIds": group_opt_ids,
                "branchLineIdsByOption": {group_opt_ids[0]: candidate_lines},
                "nextRecoveredGroup": next_group_id,
                "nextRecoveredAfter": next_after,
                "nextRecoveredReason": next_risk.get("reason") or "",
                "source": next_risk.get("source") or "siblingSceneGraphText",
                "sources": next_risk.get("sources") or [],
            }

        for order, g in enumerate(sorted(groups_map), start=1):
            opts = sorted(groups_map[g], key=lambda o: o["i"])
            group_opt_ids = group_option_ids_by_group.get(g, [])
            placement_override = DIALOG_OPTION_GROUP_POSITION_OVERRIDES.get((conv_key or "", g), "")
            manual_override = _manual_option_group_override(conv_key or "", g)
            cinematic_after_candidate = cinematic_after_by_group.get(g, "")
            cinematic_group_sources = cinematic_sources_by_group.get(g, [])
            text_alias_after_candidate = text_alias_after_by_group.get(g, "")
            text_alias_group_sources = text_alias_sources_by_group.get(g, [])
            text_alias_foreign_option_ids = text_alias_foreign_option_ids_by_group.get(g, [])
            group = {"g": g, "options": opts}
            after = None
            tree_after_option_ids: list[str] = []
            scene_link_after_option_ids: list[str] = []
            timeline_after_option_ids: list[str] = []
            cinematic_after_option_ids: list[str] = []
            text_alias_after_option_ids: list[str] = []
            for opt in opts:
                opt_id = opt.get("id") or ""
                tree_after_candidate = tree_after.get(opt_id) or ""
                scene_link_after_candidate = scene_link_after.get(opt_id) or ""
                timeline_after_candidate = timeline_after.get(opt_id) or ""
                if timeline_after_candidate and timeline_after_candidate not in valid_line_ids:
                    timeline_after_candidate = _nearest_visible_timeline_anchor(
                        timeline_after_candidate,
                        timeline_after_line_ids.get(opt_id) or [],
                        valid_line_ids,
                    )
                if tree_after_candidate and tree_after_candidate in valid_line_ids:
                    tree_after_option_ids.append(opt_id)
                if scene_link_after_candidate and scene_link_after_candidate in valid_line_ids:
                    scene_link_after_option_ids.append(opt_id)
                if timeline_after_candidate and timeline_after_candidate in valid_line_ids:
                    timeline_after_option_ids.append(opt_id)
                if cinematic_after_candidate and cinematic_after_candidate in valid_line_ids:
                    cinematic_after_option_ids.append(opt_id)
                if text_alias_after_candidate and text_alias_after_candidate in valid_line_ids:
                    text_alias_after_option_ids.append(opt_id)
                authored_after_candidates = [
                    tree_after_candidate,
                    scene_link_after_candidate,
                    timeline_after_candidate,
                ]
                after = next(
                    (
                        candidate_after
                        for candidate_after in authored_after_candidates
                        if candidate_after and candidate_after in valid_line_ids
                    ),
                    None,
                )
                if after:
                    break
            if (
                after == cinematic_after_candidate
                and cinematic_after_candidate
                and cinematic_after_candidate in valid_line_ids
            ):
                cinematic_after_option_ids = list(group_opt_ids)
            if (
                after == text_alias_after_candidate
                and text_alias_after_candidate
                and text_alias_after_candidate in valid_line_ids
            ):
                text_alias_after_option_ids = list(group_opt_ids)
            after_is_authored = bool(after)
            for opt in opts:
                opt_id = opt.get("id") or ""
                branch_lines = [
                    lid for lid in (tree_branches.get(opt_id) or [])
                    if lid in valid_line_ids
                ]
                if branch_lines:
                    opt["branchLines"] = branch_lines
            pre_option_ids = [opt_id for opt_id in group_opt_ids if opt_id in tree_pre]
            timeline_pre_option_ids = [opt_id for opt_id in group_opt_ids if opt_id in timeline_pre]
            text_alias_pre_option_ids = list(group_opt_ids) if g in text_alias_pre_by_group else []
            authored_group_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id in authored_option_ids
            ]
            unauthored_group_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id and opt_id not in authored_option_ids
            ]
            direct_pre_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id in tree_pre or opt_id in timeline_pre
            ]
            group_is_authored_pre = bool(group_opt_ids) and all(
                opt_id in tree_pre or opt_id in timeline_pre
                for opt_id in group_opt_ids
            )
            used_group_fallback = False
            used_group_keyed = False
            group_status = "unanchored"
            fallback_anchor_id = ""
            inferred_anchor_mode = ""
            sibling_anchor_record: dict | None = None
            if after_is_authored:
                authored_group_count += 1
                group_status = "authoredAfter"
            elif group_is_authored_pre:
                group["position"] = "pre"
                pre_group_count += 1
                group_status = "authoredPre"
            elif placement_override == "pre" and direct_pre_option_ids:
                group["position"] = "pre"
                pre_group_count += 1
                group_status = "correctedPre"
            elif order - 1 < len(fallback_after_ids):
                fallback_anchor_id = fallback_after_ids[order - 1]
                used_group_fallback = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "sparseGap"
            elif (
                order - 1 < len(sibling_position_anchors)
                and sibling_position_anchors[order - 1].get("afterLineId") in valid_line_ids
            ):
                sibling_anchor_record = sibling_position_anchors[order - 1]
                fallback_anchor_id = sibling_anchor_record["afterLineId"]
                used_group_fallback = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "siblingTimelinePosition"
            elif g in fallback_group_line_ids:
                fallback_anchor_id = fallback_group_line_ids[g]
                used_group_keyed = True
                keyed_group_count += 1
                group_status = "keyedAfter"
                inferred_anchor_mode = "lineNumber"
            elif last_line_fallback_id:
                fallback_anchor_id = last_line_fallback_id
                used_group_fallback = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "lastLine"
            else:
                unanchored_group_count += 1
            if after_is_authored and after:
                group["after"] = after
            elif used_group_keyed and fallback_anchor_id:
                group["after"] = fallback_anchor_id
            elif used_group_fallback and fallback_anchor_id:
                group["after"] = fallback_anchor_id
            layout_override = (
                manual_override.get("layout")
                if isinstance(manual_override.get("layout"), dict)
                else {}
            )
            manual_layout_applied = False
            if layout_override:
                override_after = str(layout_override.get("after") or "").strip()
                override_position = str(layout_override.get("position") or "").strip()
                can_apply_layout_override = (
                    (after_is_authored or group_status in {"fallbackAfter", "keyedAfter", "unanchored"})
                    and (
                        override_position == "pre"
                        or (override_after and override_after in valid_line_ids)
                    )
                )
                if can_apply_layout_override:
                    if override_position == "pre":
                        group.pop("after", None)
                        group["position"] = "pre"
                    else:
                        group.pop("position", None)
                        group["after"] = override_after
                        fallback_anchor_id = override_after
                    manual_layout_applied = True
                    group["manualOverride"] = {
                        "kind": "optionLayout",
                        "source": repo_rel(_MANUAL_OPTION_OVERRIDES_PATH),
                        "note": str(manual_override.get("note") or layout_override.get("note") or ""),
                    }
            timeline_route_branch = timeline_route_branch_for_group(group_opt_ids, group.get("after") or "")
            route_branch_lines_by_option = timeline_route_branch.get("branchLineIdsByOption") or {}
            sibling_text_branch = {}
            if timeline_route_branch.get("continuationOptionIds"):
                group["continuationOptionIds"] = timeline_route_branch["continuationOptionIds"]
            for opt in opts:
                opt_id = opt.get("id") or ""
                if opt.get("branchLines"):
                    continue
                route_branch_lines = [
                    line_id
                    for line_id in (route_branch_lines_by_option.get(opt_id) or [])
                    if line_id in valid_line_ids
                ]
                if route_branch_lines:
                    opt["branchLines"] = route_branch_lines
            if not any(opt.get("branchLines") for opt in opts):
                sibling_text_branch = sibling_scene_text_branch_for_group(
                    group_opt_ids,
                    group.get("after") or "",
                    sibling_anchor_record
                    if not manual_layout_applied and inferred_anchor_mode == "siblingTimelinePosition"
                    else None,
                    g,
                )
                if not sibling_text_branch:
                    sibling_text_branch = sibling_scene_template_branch_for_group(
                        group_opt_ids,
                        group.get("after") or "",
                        g,
                    )
                if not sibling_text_branch:
                    sibling_text_branch = single_option_span_before_recovered_anchor(
                        g,
                        group_opt_ids,
                        group.get("after") or "",
                    )
                sibling_branch_lines_by_option = sibling_text_branch.get("branchLineIdsByOption") or {}
                sibling_after = str(sibling_text_branch.get("after") or "")
                if sibling_after in valid_line_ids:
                    group["after"] = sibling_after
                    fallback_anchor_id = sibling_after
                for opt in opts:
                    opt_id = opt.get("id") or ""
                    branch_lines = [
                        line_id
                        for line_id in (sibling_branch_lines_by_option.get(opt_id) or [])
                        if line_id in valid_line_ids
                    ]
                    if branch_lines:
                        opt["branchLines"] = branch_lines
                        if sibling_text_branch.get("reason") == "singleOptionSpanBeforeRecoveredAnchor":
                            recovered_single_option_line_ids.update(branch_lines)
            if placement_override == "pre":
                corrected_opts_without_branch = [
                    opt
                    for opt in opts
                    if opt.get("id") in CORRECTED_DIALOG_OPTION_IDS and not opt.get("branchLines")
                ]
                if len(corrected_opts_without_branch) == 1:
                    covered_line_ids = {
                        line_id
                        for opt in opts
                        for line_id in (opt.get("branchLines") or [])
                        if line_id in valid_line_ids
                    }
                    remaining_line_ids = [
                        line_id
                        for _idx, line_id in line_idxs
                        if line_id in valid_line_ids and line_id not in covered_line_ids
                    ]
                    if remaining_line_ids:
                        corrected_opt = corrected_opts_without_branch[0]
                        corrected_opt["branchLines"] = remaining_line_ids
                        corrected_opt.setdefault("_debug", {})["branchLineCorrection"] = {
                            "mode": "remainingLinesForCorrectedPreGroup",
                            "reason": "The corrected pre-scene option uses the only line span not covered by authored DialogTree branches.",
                            "lineIds": remaining_line_ids,
                        }
            following_line_risk = (
                timeline_route_branch
                or sibling_text_branch
                or following_line_risk_for_group(group_opt_ids, group.get("after") or "")
            )
            original_following_line_risk = dict(following_line_risk) if following_line_risk else {}
            response_override = (
                manual_override.get("responses")
                if isinstance(manual_override.get("responses"), dict)
                else {}
            )
            manual_response_applied = False
            if response_override:
                option_set = {opt_id for opt_id in group_opt_ids if opt_id}
                branch_line_ids_by_option: dict[str, list[str]] = {}
                for raw_opt_id, raw_response in response_override.items():
                    opt_id = str(raw_opt_id or "")
                    if opt_id not in option_set or not isinstance(raw_response, dict):
                        continue
                    raw_lines = raw_response.get("branchLines")
                    if raw_lines is None:
                        raw_lines = raw_response.get("lineIds")
                    if raw_lines is None:
                        raw_lines = [raw_response.get("lineId")]
                    if not isinstance(raw_lines, list):
                        raw_lines = [raw_lines]
                    line_ids = [
                        str(line_id)
                        for line_id in raw_lines
                        if str(line_id or "") in valid_line_ids
                    ]
                    if line_ids:
                        branch_line_ids_by_option[opt_id] = _unique_preserve(line_ids)
                if branch_line_ids_by_option:
                    override_detail = (
                        "Manual WebUI-only override supplies option response "
                        "line mapping for this group."
                    )
                    if following_line_risk.get("code") == "inferredFollowingLines":
                        override_detail = (
                            "Manual WebUI-only override supplies option response "
                            "line mapping for a group that otherwise used inferred "
                            "Timeline-order candidates."
                        )
                    following_line_risk = {
                        **following_line_risk,
                        "code": "manualOptionResponseOverride",
                        "reason": "manualOverride",
                        "detail": override_detail,
                        "branchLineIdsByOption": branch_line_ids_by_option,
                        "candidateLineIdsByOption": branch_line_ids_by_option,
                        "manualOverride": {
                            "kind": "optionResponse",
                            "source": repo_rel(_MANUAL_OPTION_OVERRIDES_PATH),
                            "note": str(manual_override.get("note") or ""),
                        },
                    }
                    if original_following_line_risk:
                        following_line_risk["overriddenRisk"] = original_following_line_risk
                    for opt in opts:
                        opt_id = opt.get("id") or ""
                        if opt_id in branch_line_ids_by_option:
                            opt["branchLines"] = branch_line_ids_by_option[opt_id]
                    manual_response_applied = True
            if following_line_risk.get("code") == "siblingSceneTextBranches":
                if used_group_fallback:
                    used_group_fallback = False
                    if fallback_group_count > 0:
                        fallback_group_count -= 1
                    fallback_group_labels = [
                        label for label in fallback_group_labels if label != f"g{g}"
                    ]
                if used_group_keyed:
                    used_group_keyed = False
                    if keyed_group_count > 0:
                        keyed_group_count -= 1
                group_status = "siblingSceneText"
                sibling_text_group_count += 1
            if following_line_risk:
                group["optionBranchRisk"] = following_line_risk
                if following_line_risk.get("code") == "inferredFollowingLines":
                    strong_raw_index_mapping = (
                        following_line_risk.get("candidateMapping") == "trunkClipOptionIndex"
                        and bool(following_line_risk.get("branchLineIdsByOption"))
                    )
                    if not strong_raw_index_mapping:
                        option_response_risks.append({
                            "group": g,
                            **following_line_risk,
                        })
                    tag_code = "rawOptionIndexMatchedLine" if strong_raw_index_mapping else "inferredFollowingLine"
                    for opt, line_id in zip(opts, option_risk_line_ids(following_line_risk, len(opts))):
                        tag = {
                            "code": tag_code,
                            "lineId": line_id,
                            "reason": following_line_risk["reason"],
                            "branchRiskCode": following_line_risk.get("code") or "",
                            "source": following_line_risk.get("source") or "",
                        }
                        if strong_raw_index_mapping:
                            tag["candidateMapping"] = following_line_risk.get("candidateMapping") or ""
                        opt.setdefault("riskTags", []).append(tag)
                elif following_line_risk.get("code") == "manualOptionResponseOverride":
                    manual_option_response_overrides.append({
                        "group": g,
                        **following_line_risk,
                    })
                    if original_following_line_risk.get("code") == "inferredFollowingLines":
                        strong_raw_index_mapping = (
                            original_following_line_risk.get("candidateMapping") == "trunkClipOptionIndex"
                            and bool(original_following_line_risk.get("branchLineIdsByOption"))
                        )
                        if not strong_raw_index_mapping:
                            option_response_risks.append({
                                "group": g,
                                **original_following_line_risk,
                            })
                        tag_code = "rawOptionIndexMatchedLine" if strong_raw_index_mapping else "inferredFollowingLine"
                        for opt, line_id in zip(opts, option_risk_line_ids(original_following_line_risk, len(opts))):
                            tag = {
                                "code": tag_code,
                                "lineId": line_id,
                                "reason": original_following_line_risk["reason"],
                                "branchRiskCode": original_following_line_risk.get("code") or "",
                                "source": original_following_line_risk.get("source") or "",
                            }
                            if strong_raw_index_mapping:
                                tag["candidateMapping"] = original_following_line_risk.get("candidateMapping") or ""
                            opt.setdefault("riskTags", []).append(tag)
                    for opt in opts:
                        opt_id = opt.get("id") or ""
                        line_ids = (following_line_risk.get("branchLineIdsByOption") or {}).get(opt_id) or []
                        if not line_ids:
                            continue
                        opt.setdefault("riskTags", []).append({
                            "code": "manualOptionResponseOverride",
                            "lineId": line_ids[0],
                            "reason": "manualOverride",
                            "branchRiskCode": following_line_risk.get("code") or "",
                            "source": repo_rel(_MANUAL_OPTION_OVERRIDES_PATH),
                        })
            if sibling_anchor_record and sibling_anchor_record.get("siblingScenes"):
                group["branchHint"] = {
                    "scenes": sibling_anchor_record["siblingScenes"],
                    "timeline": sibling_anchor_record.get("timeline") or "",
                }
            group_detail = {
                "group": g,
                "status": group_status,
                "after": after or fallback_anchor_id or "",
                "position": group.get("position") or "",
                "inferredAnchorMode": inferred_anchor_mode,
                "optionIds": group_opt_ids,
                "authoredOptionIds": authored_group_option_ids,
                "unauthoredOptionIds": unauthored_group_option_ids,
                "treeAfterOptionIds": tree_after_option_ids,
                "sceneLinkAfterOptionIds": scene_link_after_option_ids,
                "timelineAfterOptionIds": timeline_after_option_ids,
                "cinematicAfterOptionIds": cinematic_after_option_ids,
                "textAliasAfterOptionIds": text_alias_after_option_ids,
                "textAliasPreOptionIds": text_alias_pre_option_ids,
                "textAliasSourceOptionIds": text_alias_foreign_option_ids,
                "preOptionIds": pre_option_ids,
                "timelinePreOptionIds": timeline_pre_option_ids,
                "fallbackAnchorId": fallback_anchor_id,
                "positionOverride": placement_override,
                "cinematicSources": cinematic_group_sources,
                "textAliasSources": text_alias_group_sources,
            }
            group_manual_override = group.get("manualOverride") or (
                following_line_risk.get("manualOverride") if manual_response_applied else {}
            )
            if group_manual_override:
                group_detail["manualOverride"] = group_manual_override
            if manual_layout_applied:
                group_detail["manualLayoutOverride"] = True
            if manual_response_applied:
                group_detail["manualResponseOverride"] = True
            group_details.append(group_detail)
            out.append(group)
        has_meaningful_option_text = any(
            str(opt.get("text") or "").strip()
            for group in out
            for opt in (group.get("options") or [])
            if isinstance(opt, dict)
        )
        has_layout_warning_groups = (
            keyed_group_count > 0
            or fallback_group_count > 0
            or unanchored_group_count > 0
        )
        warnings: list[dict] = []
        if has_meaningful_option_text and has_layout_warning_groups:
            total_groups = len(out)
            if not authored_option_ids:
                reason_short = "noTreeReference"
                reason_text = (
                    "no AnimeStudio tree references any option for this scene; "
                    "group positions are unanchored and fallback candidates are diagnostic only"
                )
            elif authored_group_count + pre_group_count == 0:
                reason_short = "noAuthoredGroupAnchor"
                reason_text = (
                    "tree data exists for this scene's options but no group "
                    "received an authored anchor; fallback candidates are "
                    "diagnostic only"
                )
            else:
                reason_short = "partialAuthoredCoverage"
                reason_text = (
                    f"{authored_group_count + pre_group_count} of {total_groups} option "
                    f"groups anchored from tree data; {fallback_group_count} only have "
                    f"diagnostic fallback candidates ({', '.join(fallback_group_labels)})"
                )
            warnings.append({
                "code": "inferredOptionLayout",
                "reason": reason_short,
                "detail": reason_text,
                "groupBreakdown": {
                    "total": total_groups,
                    "authoredAfter": authored_group_count,
                    "authoredPre": pre_group_count,
                    "keyedAfter": keyed_group_count,
                    "siblingSceneText": sibling_text_group_count,
                    "fallbackAfter": fallback_group_count,
                    "unanchored": unanchored_group_count,
                },
                "fallbackGroups": fallback_group_labels,
                "fallbackAnchorIds": fallback_after_ids,
                "groupDetails": group_details,
                "treeSources": tree_meta.get("sources") or [],
                "sceneLinkSources": sorted(scene_link_sources),
                "timelineSources": sorted(timeline_sources),
                "cinematicSources": sorted(cinematic_sources),
                "textAliasSources": sorted(text_alias_sources),
                "authoredOptionCount": len(authored_option_ids),
            })
        if option_response_risks:
            warnings.append({
                "code": "inferredOptionResponse",
                "reason": "optionTargetsMissing",
                "detail": (
                    "one or more option responses are inferred from Timeline order "
                    "because the option metadata does not name explicit target trunk ids"
                ),
                "groups": option_response_risks,
                "optionIds": _unique_preserve([
                    option_id
                    for risk in option_response_risks
                    for option_id in (risk.get("optionIds") or [])
                    if option_id
                ]),
                "lineIds": _unique_preserve([
                    line_id
                    for risk in option_response_risks
                    for line_id in all_option_response_risk_line_ids(risk)
                    if line_id
                ]),
            })
        if manual_option_response_overrides:
            warnings.append({
                "code": "manualOptionResponseOverride",
                "reason": "manualOverride",
                "detail": (
                    "manual WebUI-only overrides supply option response line "
                    "mappings for these groups"
                ),
                "groups": manual_option_response_overrides,
                "optionIds": _unique_preserve([
                    option_id
                    for risk in manual_option_response_overrides
                    for option_id in (risk.get("optionIds") or [])
                    if option_id
                ]),
                "lineIds": _unique_preserve([
                    line_id
                    for risk in manual_option_response_overrides
                    for line_id in all_option_response_risk_line_ids(risk)
                    if line_id
                ]),
            })
        return {
            "groups": out,
            "warnings": warnings,
        }

    def attach_runtime_registry_debug(payload: dict) -> None:
        debug = payload.setdefault("_debug", {})
        if not isinstance(debug, dict):
            debug = {}
            payload["_debug"] = debug
        block = shared_build_runtime_registry_debug(
            payload, dialog_id_registry=dialog_id_registry
        )
        if block is None:
            debug.pop("runtimeRegistry", None)
            return
        debug["runtimeRegistry"] = block

    def attach_scene_order_warning(payload: dict) -> None:
        warning = shared_build_scene_order_disorder_warning(
            payload, dialog_id_registry=dialog_id_registry
        )
        if warning is None:
            return
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "sceneOrderDisorder"
        ]
        payload["warnings"] = [warning, *existing_warnings]


    def build_duplicate_timestamp_warning(payload: dict) -> dict | None:
        buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            ts = line.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            timing_debug = debug.get("timelineTiming") if isinstance(debug, dict) else {}
            timeline = str(timing_debug.get("timeline") or "") if isinstance(timing_debug, dict) else ""
            buckets[(timeline, format_webui_timeline_seconds(ts))].append(line)

        groups: list[dict] = []
        for (timeline, label), lines_for_ts in sorted(
            buckets.items(),
            key=lambda item: min(float(line.get("ts") or 0.0) for line in item[1]),
        ):
            if len(lines_for_ts) < 2:
                continue
            group = {
                "timestamp": label,
                "lineIds": [str(line.get("id") or "") for line in lines_for_ts if line.get("id")],
                "lines": [
                    {
                        "id": str(line.get("id") or ""),
                        "actor": str(line.get("actor") or line.get("aid") or ""),
                        "ts": line.get("ts"),
                        "dur": line.get("dur"),
                    }
                    for line in lines_for_ts
                    if line.get("id")
                ],
            }
            if timeline:
                group["timeline"] = timeline
            groups.append(group)
        if not groups:
            return None
        line_ids: list[str] = []
        for group in groups:
            for line_id in group["lineIds"]:
                if line_id not in line_ids:
                    line_ids.append(line_id)
        return {
            "code": "duplicateTimestamps",
            "reason": "duplicateDisplayTimestamp",
            "detail": "two or more lines share the same WebUI timeline timestamp label within one timeline segment",
            "groups": groups,
            "lineIds": line_ids,
        }

    def attach_duplicate_timestamp_warning(payload: dict) -> None:
        warning = build_duplicate_timestamp_warning(payload)
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "duplicateTimestamps"
        ]
        if warning is None:
            if existing_warnings:
                payload["warnings"] = existing_warnings
            else:
                payload.pop("warnings", None)
            return
        payload["warnings"] = [*existing_warnings, warning]

    def extras_text(out_key: str) -> str:
        """Concatenate all extras text for an out_key so the index entry's
        search haystack covers summaries / dialog options."""
        parts: list[str] = []
        if out_key in summary_by_key:
            parts.extend(s["text"] for s in summary_by_key[out_key] if s.get("text"))
        if out_key in options_by_key:
            for opts in options_by_key[out_key].values():
                for o in opts:
                    for id_field in ("id", "optionId"):
                        if o.get(id_field):
                            parts.append(str(o[id_field]))
                    if o["text"]:
                        parts.append(o["text"])
        return " ".join(parts)



    def attach_submenu_targets(links: list[dict]) -> None:
        for link in links or []:
            for opt in link.get("options") or []:
                if not isinstance(opt, dict):
                    continue
                submenu_scene_keys = [
                    str(scene_key)
                    for scene_key in (opt.get("submenuSceneKeys") or [])
                    if str(scene_key).strip()
                ]
                if not submenu_scene_keys:
                    continue
                debug = opt.get("_debug") if isinstance(opt.get("_debug"), dict) else {}
                return_option_ids = [
                    str(option_id)
                    for option_id in (debug.get("returnOptionIds") or [])
                    if str(option_id).strip()
                ]
                targets: list[dict] = []
                seen_targets: set[tuple[str, str]] = set()
                for idx, option_id in enumerate(return_option_ids):
                    scene_key = _dialog_tree_option_prefix(option_id) or ""
                    if not scene_key and idx < len(submenu_scene_keys):
                        scene_key = submenu_scene_keys[idx]
                    if not scene_key:
                        continue
                    key = (scene_key, option_id)
                    if key in seen_targets:
                        continue
                    seen_targets.add(key)
                    target = {
                        "sceneKey": scene_key,
                        "optionId": option_id,
                    }
                    if text := dialog_option_text_by_id.get(option_id):
                        target["text"] = text
                    targets.append(target)
                for scene_key in submenu_scene_keys:
                    if any(target.get("sceneKey") == scene_key for target in targets):
                        continue
                    target = {"sceneKey": scene_key}
                    targets.append(target)
                if targets:
                    opt["submenuTargets"] = targets

    def clone_dialog_option_for_hub(option_id: str, hub_index: int, target_scene_key: str = "") -> dict | None:
        option_id = str(option_id or "").strip()
        if not option_id:
            return None
        base = dialog_option_payload_by_id.get(option_id)
        if base:
            option = copy.deepcopy(base)
        else:
            text, icon = dialog_option_signature_by_id.get(option_id, ("", ""))
            option = {
                "id": option_id,
                "i": hub_index,
                "text": text,
                "icon": icon or "",
                "_debug": {
                    "table": "DialogOptionTable",
                    "rowId": option_id,
                    "source": {},
                    "hubOnly": True,
                },
            }
        option["i"] = hub_index
        if target_scene_key:
            option["targetSceneKey"] = target_scene_key
            option.setdefault("_debug", {})["hubTargetSceneKey"] = target_scene_key
        return option


    def source_hub_option_groups(conv_key: str, valid_line_ids: set[str]) -> tuple[list[dict], list[dict]]:
        source = _load_dialog_tree_source(conv_key)
        if not source:
            return [], []
        raw_links = [
            link
            for link in (source.get("sceneLinks") or [])
            if isinstance(link, dict)
            and (link.get("sourceKey") or "") == conv_key
        ]
        if not raw_links:
            return [], []

        nodes_by_id = {
            str(node.get("id") or ""): node
            for node in ((source.get("lineGraph") or {}).get("nodes") or [])
            if isinstance(node, dict) and node.get("id") is not None
        }
        by_source_node: dict[str, list[dict]] = defaultdict(list)
        for link in raw_links:
            link_debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
            source_node_id = str(link_debug.get("sourceOptionNodeId") or "").strip()
            group_scene_keys = [
                str(scene_key)
                for scene_key in (link_debug.get("groupSceneKeys") or [])
                if str(scene_key or "").strip()
            ]
            if source_node_id and conv_key in group_scene_keys and len(set(group_scene_keys)) > 1:
                by_source_node[source_node_id].append(link)

        hub_groups: list[dict] = []
        hub_scene_links: list[dict] = []
        for source_node_id, links in sorted(by_source_node.items()):
            local_after = next(
                (
                    str(link.get("after") or "")
                    for link in links
                    if (link.get("sceneKey") or "") == conv_key
                    and str(link.get("after") or "") in valid_line_ids
                ),
                "",
            )
            if not local_after:
                continue
            node_option_ids = [
                str(option_id)
                for option_id in (nodes_by_id.get(source_node_id, {}).get("optionIds") or [])
                if str(option_id or "").strip()
            ]
            if len(node_option_ids) < 2:
                continue
            raw_option_by_id: dict[str, dict] = {}
            target_scene_by_option: dict[str, str] = {}
            group_scene_keys: list[str] = []
            target_scene_keys: list[str] = []
            for link in links:
                link_debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
                group_scene_keys.extend(
                    str(scene_key)
                    for scene_key in (link_debug.get("groupSceneKeys") or [])
                    if str(scene_key or "").strip()
                )
                target_scene_keys.extend(
                    str(scene_key)
                    for scene_key in (link_debug.get("targetSceneKeys") or [])
                    if str(scene_key or "").strip()
                )
                scene_key = str(link.get("sceneKey") or "")
                for raw_option in link.get("options") or []:
                    if not isinstance(raw_option, dict):
                        continue
                    option_id = str(raw_option.get("optionId") or "").strip()
                    if not option_id:
                        continue
                    raw_option_by_id.setdefault(option_id, raw_option)
                    if scene_key:
                        target_scene_by_option.setdefault(option_id, scene_key)
            ordered_option_ids = [
                option_id
                for option_id in node_option_ids
                if option_id in raw_option_by_id or option_id in dialog_option_payload_by_id
            ]
            if len(ordered_option_ids) < 2:
                continue
            group_ids = [
                parts[1]
                for option_id in ordered_option_ids
                if (parts := _option_id_group_parts(option_id))
            ]
            group_id = group_ids[0] if group_ids else 1
            options = [
                option
                for option in (
                    clone_dialog_option_for_hub(
                        option_id,
                        hub_index,
                        target_scene_by_option.get(option_id, ""),
                    )
                    for hub_index, option_id in enumerate(ordered_option_ids, start=1)
                )
                if option is not None
            ]
            if len(options) < 2:
                continue
            hub_groups.append({
                "g": group_id,
                "after": local_after,
                "options": options,
                "hubMenu": {
                    "sourceKey": conv_key,
                    "sourceOptionNodeId": source_node_id,
                    "sourceFile": source.get("file") or "",
                    "sceneKeys": _unique_preserve(group_scene_keys),
                },
            })
            hub_scene_links.append({
                "sourceKey": conv_key,
                "file": source.get("file") or "",
                "after": local_after,
                "options": [
                    scene_link_option_payload(raw_option_by_id[option_id])
                    for option_id in ordered_option_ids
                    if option_id in raw_option_by_id
                ],
                "sceneSpan": True,
                "sourceSceneKeys": source.get("sourceSceneKeys") or sorted(set(group_scene_keys)),
                "_debug": {
                    "source": {
                        "targetKey": conv_key,
                        "sourceKey": conv_key,
                        "file": source.get("file") or "",
                    },
                    "link": {
                        "sourceOptionNodeId": source_node_id,
                        "groupSceneKeys": _unique_preserve(group_scene_keys),
                        "targetSceneKeys": _unique_preserve(target_scene_keys),
                        "sourceHubMenu": True,
                    },
                },
            })
        return hub_groups, hub_scene_links

    def apply_source_hub_option_groups(payload: dict, scene_graph_links: list[dict]) -> list[dict]:
        def group_after_suffix(group: dict) -> int:
            match = re.search(r"_(\d+)$", str(group.get("after") or ""))
            return int(match.group(1)) if match else -1

        def link_source_node_id(link: dict) -> str:
            debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
            link_debug = debug.get("link") if isinstance(debug.get("link"), dict) else {}
            return str(link_debug.get("sourceOptionNodeId") or "")

        def link_option_ids(link: dict) -> set[str]:
            return {
                str(option.get("optionId") or "")
                for option in (link.get("options") or [])
                if isinstance(option, dict) and str(option.get("optionId") or "")
            }

        conv_key = str(payload.get("key") or "")
        valid_line_ids = {
            str(line.get("id") or "")
            for line in (payload.get("lines") or [])
            if isinstance(line, dict) and str(line.get("id") or "")
        }
        hub_groups, hub_links = source_hub_option_groups(conv_key, valid_line_ids)
        if not hub_groups:
            return scene_graph_links
        groups = [
            group
            for group in (payload.get("optionGroups") or [])
            if isinstance(group, dict)
        ]
        for hub_group in hub_groups:
            hub_g = hub_group.get("g")
            replaced = False
            for idx, existing_group in enumerate(groups):
                if existing_group.get("g") == hub_g and existing_group.get("after") == hub_group.get("after"):
                    groups[idx] = hub_group
                    replaced = True
                    break
            if not replaced:
                groups.append(hub_group)
        groups.sort(key=lambda group: (group_after_suffix(group), group.get("g") or 0))
        payload["optionGroups"] = groups
        for hub_link in hub_links:
            if hub_link.get("options"):
                hub_debug = hub_link.get("_debug") if isinstance(hub_link.get("_debug"), dict) else {}
                hub_link_debug = hub_debug.get("link") if isinstance(hub_debug.get("link"), dict) else {}
                hub_source_node_id = str(hub_link_debug.get("sourceOptionNodeId") or "")
                hub_after = str(hub_link.get("after") or "")
                hub_option_ids = link_option_ids(hub_link)
                scene_graph_links[:] = [
                    existing
                    for existing in scene_graph_links
                    if not (
                        str(existing.get("after") or "") == hub_after
                        and link_source_node_id(existing) == hub_source_node_id
                        and link_option_ids(existing).issubset(hub_option_ids)
                    )
                ]
                scene_graph_links.append(hub_link)
        return scene_graph_links



    def dialog_recovery_methods(payload: dict) -> list[str]:
        methods: list[str] = []

        def add(method: str) -> None:
            if method and method not in methods:
                methods.append(method)

        debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
        line_order = debug.get("lineOrder") if isinstance(debug.get("lineOrder"), dict) else {}
        line_order_mode = str(line_order.get("mode") or "")
        if line_order_mode == "lineIdSuffix":
            registry = debug.get("runtimeRegistry") if isinstance(debug.get("runtimeRegistry"), dict) else {}
            original_line_ids = line_order.get("originalLineIds") or []
            ordered_line_ids = line_order.get("orderedLineIds") or []
            if registry.get("registered") is True and _line_id_list_equal(original_line_ids, ordered_line_ids):
                add("lineOrder:runtimeRowIteration")
            elif registry.get("registered") is False:
                add("lineOrder:unregisteredScene")
            else:
                add("lineOrder:lineIdSuffix")
        elif line_order_mode:
            add(f"lineOrder:{line_order_mode}")
        elif len(payload.get("lines") or []) > 1:
            add("lineOrder:missing")

        option_groups = [
            group
            for group in (payload.get("optionGroups") or [])
            if isinstance(group, dict)
        ]
        warnings = [
            warning
            for warning in (payload.get("warnings") or [])
            if isinstance(warning, dict)
        ]
        layout_warning = next(
            (warning for warning in warnings if warning.get("code") == "inferredOptionLayout"),
            None,
        )
        if layout_warning:
            reason = str(layout_warning.get("reason") or "")
            if reason == "partialAuthoredCoverage":
                add("optionLayout:partialAuthoredCoverage")
            elif reason == "noAuthoredGroupAnchor":
                add("optionLayout:noAuthoredGroupAnchor")
            else:
                add("optionLayout:fallback")
        elif option_groups:
            add("optionLayout:authored")

        if payload.get("sceneGraphLinks"):
            add("optionBranch:sceneGraph")
        if payload.get("graphFragments"):
            add("optionBranch:dialogTreeFragment")

        for group in option_groups:
            if group.get("continuationOptionIds"):
                add("optionBranch:continuationOption")
            if group.get("branchHint"):
                add("optionBranch:siblingSceneHint")
            risk = group.get("optionBranchRisk") if isinstance(group.get("optionBranchRisk"), dict) else {}
            if not risk:
                continue

            def add_option_branch_methods(branch_risk: dict) -> None:
                if branch_risk.get("code") == "timelineRouteBranches":
                    add("optionBranch:runtimeJump")
                elif branch_risk.get("code") == "siblingSceneTextBranches":
                    add("optionBranch:siblingSceneText")
                elif branch_risk.get("candidateMapping") == "trunkClipOptionIndex":
                    add("optionBranch:rawIndexMatched")
                elif branch_risk.get("code") == "inferredFollowingLines":
                    add("optionBranch:timelineAdjacent")
                elif branch_risk.get("code") == "manualOptionResponseOverride":
                    add("optionBranch:manualOverride")
                elif branch_risk.get("code") == "sharedTimelineContinuation":
                    add("optionBranch:commonContinuation")
                if branch_risk.get("commonContinuationLineId"):
                    add("optionBranch:commonContinuation")
                if branch_risk.get("continuationOptionIds"):
                    add("optionBranch:continuationOption")

            overridden_risk = (
                risk.get("overriddenRisk")
                if isinstance(risk.get("overriddenRisk"), dict)
                else {}
            )
            if overridden_risk:
                add_option_branch_methods(overridden_risk)
            add_option_branch_methods(risk)

        return methods

    print(
        f"Extras: summary={len(summary_by_key)} scenes ({summary_orphans} orphans), "
        f"options={len(options_by_key)} scenes ({option_orphans} orphans), "
        f"radioTargets={len(radio_targets_seen)} scenes, "
        f"radioStandalone={len(radio_rows)} conversations ({radio_orphans} orphans)"
    )

    index_entries: list[dict] = []
    story_env_entries_by_mission: dict[str, list[dict]] = defaultdict(list)
    scene_graph_links_by_key: dict[str, list[dict]] = {}

    # Emit dialog conversations
    print(f"Writing {len(groups)} dialog conversations...")
    for key, items in groups.items():
        items.sort(key=lambda x: x[0])
        _, mission, scene_str = key.split("__")
        scene = int(scene_str)
        type_, act = parse_mission(mission)

        lines = []
        actors: set[str] = set()
        for _line, dlg_id, e in items:
            actor_id = e.get("actorNameId") or ""
            actor = t(e.get("actorName", {}).get("id"))
            text = t(e.get("dialogText", {}).get("id"))
            hint = t(e.get("hint", {}).get("id"))
            audio = e.get("audioOverride") or ""
            emo = e.get("emotionType", 0)
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": dlg_id,
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "hint": hint,
                "audio": audio,
                "emo": emo,
                "_debug": {
                    **source_ref(
                        "DialogTextTable",
                        dlg_id,
                        pick_fields(
                            e,
                            "actorNameId",
                            "actorName",
                            "dialogText",
                            "hint",
                            "audioOverride",
                            "emotionType",
                        ),
                    ),
                    "fields": {
                        "actor": text_trace("DialogTextTable", dlg_id, "actorName", e.get("actorName")),
                        "text": text_trace("DialogTextTable", dlg_id, "dialogText", e.get("dialogText")),
                        "hint": text_trace("DialogTextTable", dlg_id, "hint", e.get("hint")),
                    },
                },
            })

        out_key = f"dlg_{mission}_{scene}"
        ordered_line_ids, line_order_debug = resolve_scene_line_order(
            out_key,
            [line.get("id") or "" for line in lines],
        )
        if ordered_line_ids:
            line_order_index = {line_id: idx for idx, line_id in enumerate(ordered_line_ids)}
            lines = [
                line
                for _idx, line in sorted(
                    enumerate(lines),
                    key=lambda item: (
                        line_order_index.get(item[1].get("id") or "", len(ordered_line_ids) + item[0]),
                        item[0],
                    ),
                )
            ]
        prev_text = next((line.get("text") or "" for line in lines if line.get("text")), "")
        payload = {
            "key": out_key,
            "kind": "dlg",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "_debug": {
                "title": mission_name_trace(mission),
            },
        }
        if line_order_debug:
            payload["_debug"]["lineOrder"] = line_order_debug
        # Attach Unity Timeline timing per line so the conv view can render a
        # 00:54-style gutter alongside each line. Only sets "ts" / "dur" when
        # the recovery JSON actually has a timestamp for the line.
        line_timings = collect_line_timings(out_key)
        if line_timings:
            for line in lines:
                timing = line_timings.get(line.get("id") or "")
                if not timing:
                    continue
                if isinstance(timing.get("start"), (int, float)):
                    line["ts"] = timing["start"]
                if isinstance(timing.get("duration"), (int, float)):
                    line["dur"] = timing["duration"]
                timing_debug = {
                    key: timing[key]
                    for key in ("timeline", "start", "duration")
                    if timing.get(key) not in (None, "")
                }
                if timing_debug:
                    line.setdefault("_debug", {})["timelineTiming"] = timing_debug
        # Cross-link with other dialog scenes that share this scene's Unity
        # Timeline. Surfaces cases like dlg_e2m6_11 + dlg_e2m6_19 where a single
        # cinematic recording is split into two DialogTextTable scenes.
        related = collect_related_scenes(out_key)
        if related:
            payload["relatedScenes"] = related
        if out_key in summary_by_key:
            payload["summary"] = summary_by_key[out_key]
        if out_key in options_by_key:
            packed_options = pack_options(options_by_key[out_key], lines, out_key)
            payload["optionGroups"] = packed_options["groups"]
            if packed_options["warnings"]:
                payload["warnings"] = packed_options["warnings"]
        line_graph = build_dialog_tree_line_graph_payload(
            out_key,
            [line.get("id") or "" for line in lines],
        )
        if line_graph:
            payload["lineGraph"] = line_graph
        graph_fragments = build_dialog_tree_fragment_payload(out_key)
        if graph_fragments:
            payload["graphFragments"] = graph_fragments
        scene_graph_links = build_dialog_tree_scene_link_payload(out_key)
        scene_graph_links = apply_source_hub_option_groups(payload, scene_graph_links)
        if scene_graph_links:
            attach_submenu_targets(scene_graph_links)
            payload["sceneGraphLinks"] = scene_graph_links
            scene_graph_links_by_key[out_key] = scene_graph_links
        attach_runtime_registry_debug(payload)
        attach_scene_order_warning(payload)
        attach_duplicate_timestamp_warning(payload)
        story_issue_codes = dialog_story_issue_codes(payload)
        recovery_methods = dialog_recovery_methods(payload)
        if fmv_clips_by_key.get(out_key):
            payload["fmvClips"] = fmv_clips_by_key[out_key]
        write_conv_payload(out_key, payload)

        entry = {
            "k": out_key,                # key
            "d": "dlg",                  # kind
            "m": mission,                # mission id
            "s": scene,                  # scene number
            "t": type_,                  # type prefix (a/c/e/f/m)
            "a": act,                    # act number
            "c": sorted(actors),         # actor ids
            "n": len(lines),             # line count
            "p": preview(prev_text),     # text preview
        }
        if (tags := entry_tags(out_key, mission)):
            entry["tags"] = tags
        entry["x"] = merge_search_text(
            indexed_line_haystack(lines, "text", "actor", "aid", "hint"),
            extras_text(out_key),
        )
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        entry["x"] = merge_search_text(entry.get("x", ""), graph_fragments_text(graph_fragments))
        entry["x"] = merge_search_text(entry.get("x", ""), scene_links_text(scene_graph_links))
        if graph_fragments:
            tags = entry.setdefault("tags", [])
            if "graphFragment" not in tags:
                tags.append("graphFragment")
        if scene_graph_links:
            tags = entry.setdefault("tags", [])
            if "sceneGraph" not in tags:
                tags.append("sceneGraph")
        if story_issue_codes:
            entry["storyIssues"] = story_issue_codes
        if recovery_methods:
            entry["recoveryMethods"] = recovery_methods
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    # Emit SNS conversations
    print(f"Writing {len(sns_groups)} SNS conversations...")
    for sns_id, entry in sns_groups.items():
        m = SNS_RE.match(sns_id)
        mission = m.group(1) if m else sns_id
        scene = int(m.group(2)) if m else 0
        chat_id = str(entry.get("chatId") or "")
        is_topic_chat = sns_id.startswith("sns_topic_") and bool(chat_id)
        if is_topic_chat:
            mission = f"topic_{chat_id}"
        type_, act = parse_mission(mission)

        # Reconstruct order by following nextContentId from -1's preContentId backwards,
        # then forwards from the first node whose preContentId == 0.
        cdata = entry.get("dialogContentData", {})
        # The "-1" sentinel marks the end; its preContentId is the last real node.
        # Find the start: the node whose preContentId == 0 (or 1 if absent).
        start = None
        for cid, node in cdata.items():
            if node.get("preContentId") == 0 and cid != "-1":
                start = cid
                break
        ordered = []
        seen = set()
        cur = start or "1"
        while cur and cur in cdata and cur not in seen:
            seen.add(cur)
            node = cdata[cur]
            if str(node.get("contentId")) == "-1":
                break
            ordered.append((cur, node))
            nxt = node.get("nextContentId")
            cur = str(nxt) if nxt not in (None, 0, -1) else None

        # Fallback: if traversal looks incomplete, append remaining numeric nodes by id.
        if len(ordered) < sum(1 for cid in cdata if cid not in ("-1",)):
            for cid in sorted((c for c in cdata if c not in ("-1",)), key=lambda x: int(x)):
                if cid not in seen:
                    seen.add(cid)
                    ordered.append((cid, cdata[cid]))

        lines = []
        speakers: list[str] = []
        seen_speakers: set[str] = set()
        prev_text = ""
        for order_idx, (cid, node) in enumerate(ordered, start=1):
            speaker = node.get("speaker") or ""
            text = sns_content_text(node)
            options = []
            for opt_id in node.get("dialogOptionIds", []) or []:
                opt = sns_opts.get(opt_id)
                if not opt:
                    continue
                option_text = sns_option_display_text(opt)
                option_res_path = str(opt.get("optionResPath") or "").strip()
                option_entry = {
                    "id": opt_id,
                    "text": option_text,
                    "next": opt.get("optionNextContentId"),
                    "_debug": {
                        **source_ref(
                            "SNSDialogOptionTable",
                            opt_id,
                            pick_fields(
                                opt,
                                "optionDesc",
                                "optionNextContentId",
                                "optionResPath",
                            ),
                        ),
                        "fields": {
                            "text": text_trace(
                                "SNSDialogOptionTable", opt_id, "optionDesc", opt.get("optionDesc")
                            ),
                        },
                    },
                }
                if option_res_path:
                    option_entry["image"] = option_res_path
                    option_entry["emoji"] = option_res_path
                    option_entry["_debug"]["fields"]["image"] = {
                        "table": "SNSDialogOptionTable",
                        "rowId": opt_id,
                        "field": "optionResPath",
                        "raw": option_res_path,
                        "lookup": [
                            {
                                "from": f"SNSDialogOptionTable[{opt_id}].optionResPath",
                                "value": option_res_path,
                            }
                        ],
                        "text": option_text,
                    }
                options.append(option_entry)
            if speaker and speaker not in seen_speakers:
                seen_speakers.add(speaker)
                speakers.append(speaker)
            line_entry = {
                "cid": int(cid),
                "speaker": speaker,
                "text": text,
                "type": node.get("contentType", 1),
                "options": options,
                "linkMission": node.get("linkMissionId") or "",
                "_debug": {
                    **source_ref(
                        "SNSDialogTable.dialogContentData",
                        sns_id,
                        pick_fields(
                            node,
                            "contentId",
                            "preContentId",
                            "nextContentId",
                            "speaker",
                            "content",
                            "contentParam",
                            "contentParams",
                            "contentType",
                            "dialogOptionIds",
                            "linkMissionId",
                            "optionType",
                        ),
                        nodeId=cid,
                        order=order_idx,
                    ),
                    "fields": {
                        "text": text_trace(
                            "SNSDialogTable.dialogContentData", sns_id, "content", node.get("content")
                        ),
                    },
                },
            }
            if node.get("contentType") == 2:
                image_ids = [
                    str(value or "").strip()
                    for value in (node.get("contentParam") or [])
                    if str(value or "").strip()
                ]
                if image_ids:
                    line_entry["images"] = image_ids
                    line_entry["_debug"]["fields"]["images"] = {
                        "table": "SNSDialogTable.dialogContentData",
                        "rowId": sns_id,
                        "field": "contentParam",
                        "raw": node.get("contentParam"),
                        "lookup": [
                            {
                                "from": f"SNSDialogTable.dialogContentData[{sns_id}].contentParam",
                                "value": image_ids,
                            }
                        ],
                        "text": text,
                    }
            lines.append(line_entry)
            if not prev_text and text:
                prev_text = text

        # Keep each SNS conversation keyed by its original table row id so
        # topic chats can share a chat-based mission bucket without colliding
        # in the index or overwriting each other's conv JSON files.
        out_key = sns_id
        title_topic_id = entry.get("topicId") or mission.removeprefix("topic_")
        topic_title_trace = topic_name_trace(title_topic_id)
        chat_title_trace = chat_name_trace(chat_id)
        mission_title_trace = mission_name_trace(mission)
        chat_title = chat_name(chat_id)
        chat_type_value = chat_type(chat_id)
        mission_title = mission_name(mission)
        topic_title = topic_name(title_topic_id)

        title_choices: list[tuple[str, dict | None]] = []
        if is_topic_chat:
            title_choices.extend([
                (topic_title, topic_title_trace),
                (chat_title, chat_title_trace),
            ])
        else:
            title_choices.append((topic_title, topic_title_trace))
        title_choices.extend([
            (mission_title, mission_title_trace),
            (chat_title, chat_title_trace),
            (sns_raw_title(out_key), {"source": sns_raw_title(out_key)}),
        ])

        display_title = ""
        display_title_debug: dict | None = None
        for title_value, title_debug in title_choices:
            if title_value:
                display_title = title_value
                display_title_debug = title_debug or {"source": title_value}
                break
        if not display_title:
            display_title = sns_raw_title(out_key)
            display_title_debug = {"source": display_title}

        def is_admin_sns_speaker(speaker_id: str) -> bool:
            return (speaker_actor_id(speaker_id) or speaker_id).lower() in ADMIN_ACTOR_IDS

        primary_speaker = speakers[0] if speakers else ""
        if primary_speaker and is_admin_sns_speaker(primary_speaker):
            primary_speaker = speakers[1] if len(speakers) > 1 else ""
        if primary_speaker and is_admin_sns_speaker(primary_speaker):
            primary_speaker = next(
                (speaker for speaker in speakers if not is_admin_sns_speaker(speaker)),
                "",
            )
        if not primary_speaker and chat_id and not is_admin_sns_speaker(chat_id):
            primary_speaker = chat_id
        index_speakers = (
            [primary_speaker] + [speaker for speaker in speakers if speaker != primary_speaker]
            if primary_speaker else speakers
        )

        sns_payload = {
            "key": out_key,
            "kind": "sns",
            "mission": mission,
            "scene": scene,
            "title": display_title,
            "chatId": chat_id,
            "chatTitle": chat_title,
            "chatType": chat_type_value,
            "chatGroupSpeaker": primary_speaker,
            "relatedMissionId": entry.get("relatedMissionId", ""),
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "SNSDialogTable",
                    sns_id,
                    pick_fields(entry, "chatId", "relatedMissionId", "topicId", "dialogContentData"),
                ),
                "title": display_title_debug,
                "chat": chat_title_trace,
            },
        }
        write_conv_payload(out_key, sns_payload)

        entry = {
            "k": out_key,
            "d": "sns",
            "m": mission,
            "s": scene,
            "t": type_,
            "a": act,
            "title": display_title,
            "chatId": chat_id,
            "chatTitle": chat_title,
            "chatType": chat_type_value,
            "chatGroupSpeaker": primary_speaker,
            "c": index_speakers,
            "n": len(lines),
            "p": preview(prev_text),
        }
        if (tags := entry_tags(out_key, mission)):
            entry["tags"] = tags
        sns_line_text = indexed_line_haystack(lines, "text", "speaker", "linkMission")
        entry["x"] = display_title
        for title_text in (chat_title, topic_title, mission_title):
            if title_text and title_text != display_title:
                entry["x"] = merge_search_text(entry["x"], title_text)
        entry["x"] = merge_search_text(entry["x"], sns_line_text)
        entry["x"] = merge_search_text(
            entry["x"],
            extras_text(out_key),
        )
        entry["x"] = merge_search_text(
            entry["x"],
            mission_context_text(mission),
        )
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    # Emit radio conversations as standalone entries. Radio is no longer
    # embedded into dlg/sns/misc pages; the browser should navigate to the
    # explicit radio scene instead.
    print(f"Writing {len(radio_rows)} radio conversations...")
    for radio in sorted(
        radio_rows,
        key=lambda item: (item["t"], item["a"], item["m"], item["s"], item["k"]),
    ):
        out_key = radio["k"]
        payload = {
            "key": out_key,
            "kind": "radio",
            "mission": radio["m"],
            "scene": radio["scene"],
            "radioType": radio["radioType"],
            "lines": radio["lines"],
            "_debug": {
                "source": radio["_debug"],
                "title": mission_name_trace(radio["m"]),
            },
        }
        if radio["target"]:
            payload["_debug"]["attachedTo"] = {
                "source": {
                    "key": radio["target"],
                }
            }
        write_conv_payload(out_key, payload)
        radio_out_keys.add(out_key)

        entry = {
            "k": out_key,
            "d": "radio",
            "m": radio["m"],
            "s": radio["s"],
            "t": radio["t"],
            "a": radio["a"],
            "c": radio["c"],
            "n": len(radio["lines"]),
            "p": radio["p"],
            "tags": ["radio"],
        }
        if (xt := indexed_line_haystack(radio["lines"], "text", "actor", "aid")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(radio["m"]))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    radio_row_lookup = {row["k"]: row for row in radio_rows}

    black_groups: dict[str, dict] = {}
    for text_id, text_entry in text_table.items():
        m = BLACK_RE.match(text_id)
        if not m:
            continue
        mission, scene, line_str = m.group(1), m.group(2), m.group(3)
        out_key = f"black_{mission}_{scene}"
        bucket = black_groups.setdefault(
            out_key,
            {
                "mission": mission,
                "scene": scene,
                "items": [],
            },
        )
        bucket["items"].append((int(line_str), text_id, text_entry))

    print(f"Writing {len(black_groups)} black-screen conversations...")
    for out_key, bucket in sorted(
        black_groups.items(),
        key=lambda item: (
            parse_mission(item[1]["mission"])[0],
            parse_mission(item[1]["mission"])[1],
            item[1]["mission"],
            scene_sort_value(item[1]["scene"]),
            item[0],
        ),
    ):
        mission = bucket["mission"]
        scene = bucket["scene"]
        type_, act = parse_mission(mission)
        lines = []
        prev_text = ""
        for _order, text_id, text_entry in sorted(bucket["items"], key=lambda item: (item[0], item[1])):
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
            lines.append({
                "id": text_id,
                "text": text,
                "_debug": {
                    **source_ref(
                        "TextTable",
                        text_id,
                        pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                    ),
                    "fields": {
                        "text": text_trace("TextTable", text_id, "id", text_entry),
                    },
                },
            })
            if not prev_text and text:
                prev_text = text

        payload = {
            "key": out_key,
            "kind": "black",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "_debug": {
                "title": mission_name_trace(mission),
            },
        }
        write_conv_payload(out_key, payload)
        black_out_keys.add(out_key)

        entry = {
            "k": out_key,
            "d": "black",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": [],
            "n": len(lines),
            "p": preview(prev_text),
        }
        if (xt := indexed_line_haystack(lines, "text")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    remote_rows: list[dict] = []
    for remote_id, remote_entry in remote_common.items():
        m = REMOTECOMM_RE.match(remote_id)
        if not m:
            continue
        mission = m.group(1)
        scene = m.group(2) or "0"
        type_, act = parse_mission(mission)
        lines = []
        actors: set[str] = set()
        prev_text = ""

        for item in sorted(
            remote_entry.get("remoteCommSingleDataList", []) or [],
            key=lambda row: row.get("index", 0),
        ):
            actor_list = [str(actor_id) for actor_id in (item.get("actorList") or []) if actor_id]
            actor_id = str(item.get("middleId") or (actor_list[0] if actor_list else ""))
            actor = t(item.get("actorName", {}).get("id"))
            text = t(item.get("remoteCommText", {}).get("id"))
            hint = t(item.get("hint", {}).get("id"))
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": item.get("singleId") or remote_id,
                "cid": item.get("index"),
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "hint": hint,
                "audio": item.get("audioId") or "",
                "voice": item.get("voiceId") or "",
                "_debug": {
                    **source_ref(
                        "RemoteCommonTable.remoteCommSingleDataList",
                        item.get("singleId") or remote_id,
                        pick_fields(
                            item,
                            "actorList",
                            "actorName",
                            "audioId",
                            "hint",
                            "imageList",
                            "index",
                            "isVideoLoop",
                            "middleId",
                            "musicId",
                            "remoteCommText",
                            "singleId",
                            "voiceId",
                        ),
                        rowId=remote_id,
                    ),
                    "fields": {
                        "actor": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "actorName",
                            item.get("actorName"),
                        ),
                        "text": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "remoteCommText",
                            item.get("remoteCommText"),
                        ),
                        "hint": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "hint",
                            item.get("hint"),
                        ),
                    },
                },
            })
            if not prev_text and text:
                prev_text = text

        remote_rows.append({
            "key": remote_id,
            "mission": mission,
            "scene": scene,
            "type": type_,
            "act": act,
            "actors": sorted(actors),
            "lines": lines,
            "preview": prev_text,
            "source": remote_entry,
        })

    print(f"Writing {len(remote_rows)} remote communication conversations...")
    for remote in sorted(
        remote_rows,
        key=lambda item: (
            item["type"],
            item["act"],
            item["mission"],
            scene_sort_value(item["scene"]),
            item["key"],
        ),
    ):
        payload = {
            "key": remote["key"],
            "kind": "remotecomm",
            "mission": remote["mission"],
            "scene": remote["scene"],
            "lines": remote["lines"],
            "_debug": {
                "source": source_ref(
                    "RemoteCommonTable",
                    remote["key"],
                    pick_fields(remote["source"], "autoPlay", "endAudioEvent", "remoteCommSingleDataList"),
                ),
                "title": mission_name_trace(remote["mission"]),
            },
        }
        write_conv_payload(remote["key"], payload)
        remotecomm_out_keys.add(remote["key"])

        entry = {
            "k": remote["key"],
            "d": "remotecomm",
            "m": remote["mission"],
            "s": scene_sort_value(remote["scene"]),
            "t": remote["type"],
            "a": remote["act"],
            "c": remote["actors"],
            "n": len(remote["lines"]),
            "p": preview(remote["preview"]),
        }
        if (xt := indexed_line_haystack(remote["lines"], "text", "actor", "aid", "hint")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(remote["mission"]))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    known_cutscene_missions = sorted(
        {
            path.stem
            for path in MRA_DIR.glob("*.json")
            if path.stem and not path.stem.endswith("_meta")
        }
        | {
            entry["m"]
            for entry in index_entries
            if entry.get("m")
        },
        key=lambda mission: (-len(mission), mission),
    )


    def resolve_cutscene_text_group(group: str, asset_keys: set[str], raw_groups: set[str]) -> str:
        if group in asset_keys:
            return group
        normalized = normalize_cutscene_text_group(group)
        if normalized != group:
            if normalized in asset_keys:
                return normalized
            if normalized in raw_groups:
                return group
        if normalized in asset_keys:
            return normalized
        for candidate in sorted(asset_keys, key=lambda key: (-len(key), key)):
            if not group.startswith(candidate):
                continue
            rest = group[len(candidate):]
            if rest and re.fullmatch(r"d\d+(?:_.*)?", rest):
                return candidate
        return normalized

    def subtitle_locale_tokens(code: str) -> tuple[str, ...]:
        return {
            "CN": ("CHI", "CN"),
            "EN": ("ENG", "EN"),
            "JP": ("JP",),
            "KR": ("KR", "KO"),
            "TC": ("CHT", "TC"),
            "MX": ("MX", "ES"),
            "BR": ("BR", "PT"),
        }.get(str(code or "").upper(), (str(code or "").upper(),))

    def subtitle_track_language_score(track: dict) -> int:
        name = str(track.get("parentName") or "").upper()
        desired = subtitle_locale_tokens(language_code)

        def first_desired_index(tokens: list[str]) -> int | None:
            matches = [
                desired.index(token)
                for token in tokens
                if token in desired
            ]
            return min(matches) if matches else None

        env_tokens = re.findall(r"_ENV_([A-Z]+)", name)
        audio_tokens = re.findall(r"_AU_([A-Z]+)", name)
        if env_tokens:
            env_index = first_desired_index(env_tokens)
            if env_index is None:
                return 100
            audio_index = first_desired_index(audio_tokens)
            return env_index if audio_index is not None else 10 + env_index
        if audio_tokens:
            audio_index = first_desired_index(audio_tokens)
            return 20 + audio_index if audio_index is not None else 80
        return 50

    def subtitle_tracks_for_language(tracks: list[dict]) -> list[dict]:
        scored = [
            (subtitle_track_language_score(track), track)
            for track in tracks
            if isinstance(track, dict)
        ]
        if not scored:
            return []
        best_score = min(score for score, _track in scored)
        return [
            track for score, track in scored
            if score == best_score
        ]

    def cutscene_text_lines(
        asset_keys: set[str],
        subtitle_tracks_by_key: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        raw_groups: set[str] = set()
        matched_rows: list[tuple[str, dict, re.Match[str]]] = []
        for row_id, text_entry in text_table.items():
            row_key = str(row_id or "")
            if not row_key.startswith("cutscene_"):
                continue
            match = CUTSCENE_TEXT_ROW_RE.match(row_key)
            if not match:
                continue
            raw_groups.add(match.group("group"))
            matched_rows.append((row_key, text_entry, match))

        grouped: dict[str, list[tuple[tuple[int, int, int, str, str], dict]]] = defaultdict(list)
        lines_by_row_id: dict[str, dict] = {}

        def build_cutscene_texttable_line(
            row_key: str,
            text_entry,
            match: re.Match[str],
            cutscene_key: str,
            raw_group: str,
        ) -> dict:
            line_num = int(match.group("line"))
            sub = match.group("sub") or ""
            gender = (match.group("gender") or "").strip("_").upper()
            cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
            line = {
                "id": row_key,
                "cid": cid,
                "text": text,
                "_debug": {
                    **source_ref(
                        "TextTable",
                        row_key,
                        pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                        cutsceneKey=cutscene_key,
                        textGroup=raw_group,
                        line=line_num,
                    ),
                    "fields": {
                        "text": text_trace("TextTable", row_key, "id", text_entry),
                    },
                },
            }
            if raw_group != cutscene_key:
                line["textGroup"] = raw_group
            if sub:
                line["sub"] = sub
                line["_debug"]["source"]["sub"] = sub
            if gender:
                line["gender"] = gender
                line["_debug"]["source"]["gender"] = gender
            return line

        def remember_cutscene_line_usage(line: dict) -> None:
            remember_texttable_row_usage(line.get("id"))
            for duplicate in line.get("mergedDuplicateRows") or []:
                if isinstance(duplicate, dict):
                    remember_texttable_row_usage(duplicate.get("id"))

        def subtitle_start_key(value) -> float:
            return round(float(value), 6) if isinstance(value, (int, float)) else 0.0

        def subtitle_slot_key(ref: dict, timing_index: int) -> tuple[float, float, int]:
            duration = ref.get("duration")
            return (
                subtitle_start_key(ref.get("start")),
                round(float(duration), 6) if isinstance(duration, (int, float)) else 0.0,
                timing_index,
            )

        def subtitle_clip_debug(track: dict, ref: dict) -> dict:
            debug = {
                "source": "animeSubtitleTrack",
                "file": track.get("file"),
                "parent": track.get("parentName"),
                "parentFile": track.get("parentFile"),
                "textId": ref.get("textId"),
                "start": ref.get("start"),
                "duration": ref.get("duration"),
                "clipIndex": ref.get("clipIndex"),
                "assetPathId": ref.get("assetPathId"),
            }
            if track.get("gender"):
                debug["assetGender"] = track["gender"]
            if track.get("pathId") not in (None, ""):
                debug["trackPathId"] = track["pathId"]
            if track.get("parentPathId") not in (None, ""):
                debug["parentPathId"] = track["parentPathId"]
            return debug

        def line_matches_cutscene_key(line: dict, cutscene_key: str) -> bool:
            row_id = str(line.get("id") or "")
            if row_id.startswith(f"{cutscene_key}_"):
                return True
            if str(line.get("textGroup") or "") == cutscene_key:
                return True
            debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            if str(debug.get("cutsceneKey") or "") == cutscene_key:
                return True
            source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
            return str(source.get("textGroup") or "") == cutscene_key

        def subtitle_gender_rank(gender: str) -> int:
            return {"": 0, "F": 1, "M": 2}.get(str(gender or "").upper(), 3)

        def line_has_explicit_gender_switch(line: dict) -> bool:
            text = str(line.get("text") or "")
            return "{F}" in text or "{M}" in text

        def subtitle_candidate_rank(cutscene_key: str, candidate: dict) -> tuple[int, int, int, int, str]:
            line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
            return (
                0 if line_has_explicit_gender_switch(line) else 1,
                0 if line_matches_cutscene_key(line, cutscene_key) else 1,
                subtitle_gender_rank(candidate.get("gender") or ""),
                int(candidate.get("clipIndex") or 0),
                str(candidate.get("rowKey") or ""),
            )

        def subtitle_alternate_line_debug(candidate: dict) -> dict:
            line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
            out = {
                "id": line.get("id"),
                "cid": line.get("cid"),
                "text": line.get("text"),
                "track": candidate.get("trackDebug"),
            }
            if line.get("textGroup"):
                out["textGroup"] = line.get("textGroup")
            if candidate.get("gender"):
                out["assetGender"] = candidate.get("gender")
            return out

        def build_fallback_track_line(cutscene_key: str, row_key: str, ref: dict) -> dict:
            match = CUTSCENE_TEXT_ROW_RE.match(row_key)
            text_entry = text_table.get(row_key)
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry) if text_entry else ""
            source = source_ref(
                "AnimeStudioSubtitleTrack",
                row_key,
                {"textId": row_key},
                cutsceneKey=cutscene_key,
            )
            if match:
                raw_group = match.group("group")
                line_num = int(match.group("line"))
                sub = match.group("sub") or ""
                gender = (match.group("gender") or "").strip("_").upper()
                source["source"]["textGroup"] = raw_group
                source["source"]["line"] = line_num
                if sub:
                    source["source"]["sub"] = sub
                if gender:
                    source["source"]["gender"] = gender
                cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
            else:
                cid = str(ref.get("clipIndex") or "")
            return {
                "id": row_key,
                "cid": cid,
                "text": text,
                "_debug": {
                    **source,
                    "fields": {
                        "text": text_trace("TextTable", row_key, "id", text_entry) if text_entry else {
                            "table": "TextTable",
                            "rowId": row_key,
                            "field": "id",
                            "raw": None,
                            "lookup": [],
                            "text": "",
                        },
                    },
                },
            }

        for row_key, text_entry, match in matched_rows:
            raw_group = match.group("group")
            cutscene_key = resolve_cutscene_text_group(raw_group, asset_keys, raw_groups)
            line_num = int(match.group("line"))
            sub = match.group("sub") or ""
            gender = (match.group("gender") or "").strip("_").upper()
            line = build_cutscene_texttable_line(row_key, text_entry, match, cutscene_key, raw_group)
            lines_by_row_id[row_key] = line
            sub_order = int(sub[1:]) if sub else -1
            alias_order = 1 if raw_group != cutscene_key else 0
            grouped[cutscene_key].append(((line_num, sub_order, alias_order, gender, row_key), line))

        merged_by_key: dict[str, list[dict]] = {}
        for cutscene_key, subtitle_tracks in subtitle_tracks_by_key.items():
            subtitle_tracks = subtitle_tracks_for_language(subtitle_tracks)
            slot_candidates: dict[tuple[float, float, int], list[dict]] = defaultdict(list)
            for track in subtitle_tracks:
                timing_counts: dict[tuple[float, float], int] = defaultdict(int)
                for ref in track.get("lines") or []:
                    row_key = str(ref.get("textId") or "").strip()
                    if not row_key:
                        continue
                    start = subtitle_start_key(ref.get("start"))
                    duration = ref.get("duration")
                    timing_key = (
                        start,
                        round(float(duration), 6) if isinstance(duration, (int, float)) else 0.0,
                    )
                    timing_index = timing_counts[timing_key]
                    timing_counts[timing_key] += 1
                    slot_key = subtitle_slot_key(ref, timing_index)
                    track_debug = subtitle_clip_debug(track, ref)

                    line = copy.deepcopy(lines_by_row_id.get(row_key))
                    if line is None:
                        line = build_fallback_track_line(cutscene_key, row_key, ref)
                    line_debug = line.setdefault("_debug", {})
                    line_debug["subtitleTrack"] = track_debug
                    line_debug.setdefault("subtitleTracks", []).append(track_debug)
                    line_debug.setdefault("source", {})["subtitleTrackFile"] = track.get("file")
                    if track.get("gender"):
                        line_debug["source"]["subtitleAssetGender"] = track["gender"]
                    remember_cutscene_line_usage(line)
                    slot_candidates[slot_key].append({
                        "rowKey": row_key,
                        "slotKey": slot_key,
                        "gender": str(track.get("gender") or "").upper(),
                        "clipIndex": int(ref.get("clipIndex") or 0),
                        "sortKey": (slot_key[0], timing_index, int(ref.get("clipIndex") or 0), row_key),
                        "line": line,
                        "trackDebug": track_debug,
                    })

            ordered_lines: list[tuple[tuple[float, int, int, str], dict]] = []
            for slot_key, candidates in slot_candidates.items():
                genders = {candidate["gender"] for candidate in candidates if candidate.get("gender")}
                if len(genders) > 1 and all(candidate.get("gender") for candidate in candidates):
                    ranked = sorted(
                        candidates,
                        key=lambda candidate: subtitle_candidate_rank(cutscene_key, candidate),
                    )
                    chosen = ranked[0]
                    chosen_line = chosen["line"]
                    chosen_debug = chosen_line.setdefault("_debug", {})
                    chosen_tracks = chosen_debug.setdefault("subtitleTracks", [])
                    alternates: list[dict] = []
                    by_gender: dict[str, dict] = {}
                    chosen_text = chosen_line.get("text")
                    chosen_id = chosen_line.get("id")
                    explicit_switch = line_has_explicit_gender_switch(chosen_line)
                    if chosen.get("gender"):
                        by_gender.setdefault(chosen["gender"], chosen)
                    for candidate in ranked[1:]:
                        if candidate.get("gender"):
                            by_gender.setdefault(candidate["gender"], candidate)
                        candidate_track = candidate.get("trackDebug")
                        if candidate_track:
                            chosen_tracks.append(candidate_track)
                        candidate_line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
                        if candidate_line.get("id") != chosen_id or candidate_line.get("text") != chosen_text:
                            alternates.append(subtitle_alternate_line_debug(candidate))
                    if not explicit_switch and "F" in by_gender and "M" in by_gender:
                        f_line = by_gender["F"].get("line") if isinstance(by_gender["F"].get("line"), dict) else {}
                        m_line = by_gender["M"].get("line") if isinstance(by_gender["M"].get("line"), dict) else {}
                        f_text = str(f_line.get("text") or "")
                        m_text = str(m_line.get("text") or "")
                        if f_text != m_text:
                            chosen_line["text"] = f"{{F}}{f_text}{{M}}{m_text}"
                            chosen_debug["subtitleGenderSwitch"] = {
                                "source": "animeSubtitleTrackAlignment",
                                "F": {"id": f_line.get("id"), "text": f_text},
                                "M": {"id": m_line.get("id"), "text": m_text},
                            }
                    if alternates:
                        chosen_debug["subtitleAlternateLines"] = alternates
                    ordered_lines.append((chosen["sortKey"], chosen_line))
                    continue

                by_row_key: dict[str, dict] = {}
                for candidate in sorted(candidates, key=lambda c: (c["sortKey"], c["rowKey"])):
                    existing = by_row_key.get(candidate["rowKey"])
                    if existing is not None:
                        existing_line = existing["line"]
                        existing_debug = existing_line.setdefault("_debug", {})
                        candidate_track = candidate.get("trackDebug")
                        if candidate_track:
                            existing_debug.setdefault("subtitleTracks", []).append(candidate_track)
                        continue
                    by_row_key[candidate["rowKey"]] = candidate
                    ordered_lines.append((candidate["sortKey"], candidate["line"]))
            if ordered_lines:
                merged_by_key[cutscene_key] = [
                    line for _sort_key, line in sorted(ordered_lines, key=lambda item: item[0])
                ]

        for cutscene_key, rows in grouped.items():
            if cutscene_key in merged_by_key:
                continue
            lines = merge_duplicate_cutscene_rows(rows)
            for line in lines:
                remember_cutscene_line_usage(line)
            merged_by_key[cutscene_key] = lines
        return merged_by_key

    def ensure_cutscene_asset(cutscene_key: str) -> dict:
        return cutscene_assets.setdefault(
            cutscene_key,
            {
                "variants": [],
                "componentCounts": {},
                "levels": [],
                "actorLabels": [],
                "paths": [],
                "versions": [],
                "audioEvents": [],
                "tags": [],
                "metadata": {},
                "keepCameraPaths": [],
                "useBlackScreen": False,
                "isTransition": False,
                "hasSubtitleTrack": False,
                "textOnly": True,
            },
        )

    cutscene_assets = _load_cutscene_assets()
    cutscene_text_by_key = cutscene_text_lines(set(cutscene_assets), _load_cutscene_subtitle_tracks())
    for cutscene_key in cutscene_text_by_key:
        ensure_cutscene_asset(cutscene_key)
    print(f"Writing {len(cutscene_assets)} cutscene conversations...")
    for cutscene_key, cutscene in sorted(cutscene_assets.items()):
        mission, scene = _infer_cutscene_mission_and_scene(cutscene_key, known_cutscene_missions)
        type_, act = parse_mission(mission)
        if type_ not in MISSION_STORY_TYPES:
            type_, act = "x", 0
        lines = cutscene_text_by_key.get(cutscene_key, [])
        text_groups = cutscene_line_text_groups(cutscene_key, lines)
        summary_rows: list[dict] = []
        if cutscene.get("paths"):
            summary_rows.append({"text": f"AnimeStudio path: {cutscene['paths'][0]}"})
        if cutscene.get("levels"):
            summary_rows.append({"text": f"Levels: {', '.join(cutscene['levels'])}"})
        if cutscene.get("audioEvents"):
            summary_rows.append({"text": "Audio events: " + ", ".join(cutscene["audioEvents"][:8])})
        if cutscene.get("tags"):
            summary_rows.append({"text": "Tags: " + ", ".join(cutscene["tags"][:8])})
        metadata = cutscene.get("metadata") or {}
        if isinstance(metadata, dict) and metadata:
            metadata_parts = []
            for meta_key, values in list(metadata.items())[:8]:
                if isinstance(values, list):
                    metadata_parts.append(f"{meta_key}={', '.join(str(value) for value in values[:3])}")
                else:
                    metadata_parts.append(f"{meta_key}={values}")
            if metadata_parts:
                summary_rows.append({"text": "Metadata: " + "; ".join(metadata_parts)})
        component_summary = _cutscene_component_summary(cutscene)
        if component_summary:
            summary_rows.append({"text": f"Components: {component_summary}"})
        if cutscene.get("variants"):
            summary_rows.append({"text": f"Files: {len(cutscene['variants'])} exported asset(s)"})
        if cutscene.get("actorLabels"):
            summary_rows.append({
                "text": "Actors: " + ", ".join(cutscene["actorLabels"]),
            })
        flags: list[str] = []
        if cutscene.get("isTransition"):
            flags.append("transition")
        if cutscene.get("useBlackScreen"):
            flags.append("black-screen")
        if cutscene.get("hasSubtitleTrack"):
            flags.append("subtitle-track")
        if cutscene.get("keepCameraPaths"):
            flags.append("keep-camera")
        if flags:
            summary_rows.append({"text": "Flags: " + ", ".join(flags)})
        if lines:
            summary_rows.append({"text": f"TextTable rows: {len(lines)} localized cutscene text row(s)"})
        if len(text_groups) > 1:
            summary_rows.append({"text": "Text groups: " + ", ".join(text_groups[:8])})

        payload = {
            "key": cutscene_key,
            "kind": "cutscene",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "summary": summary_rows,
            "cutscene": {
                "variants": cutscene.get("variants") or [],
                "levels": cutscene.get("levels") or [],
                "actorLabels": cutscene.get("actorLabels") or [],
                "paths": cutscene.get("paths") or [],
                "versions": cutscene.get("versions") or [],
                "audioEvents": cutscene.get("audioEvents") or [],
                "tags": cutscene.get("tags") or [],
                "textGroups": text_groups,
                "metadata": cutscene.get("metadata") or {},
                "componentCounts": cutscene.get("componentCounts") or {},
                "variantCount": len(cutscene.get("variants") or []),
                "keepCameraPaths": cutscene.get("keepCameraPaths") or [],
                "useBlackScreen": bool(cutscene.get("useBlackScreen")),
                "isTransition": bool(cutscene.get("isTransition")),
                "hasSubtitleTrack": bool(cutscene.get("hasSubtitleTrack")),
            },
            "_debug": {
                "title": mission_name_trace(mission),
                "source": {
                    "canonicalKey": cutscene_key,
                    "variants": cutscene.get("variants") or [],
                },
            },
        }
        if fmv_clips_by_key.get(cutscene_key):
            payload["fmvClips"] = fmv_clips_by_key[cutscene_key]
        write_conv_payload(cutscene_key, payload)
        cutscene_out_keys.add(cutscene_key)

        search_text = " ".join(part for part in [
            cutscene_key,
            mission,
            scene,
            " ".join(cutscene.get("levels") or []),
            " ".join(cutscene.get("actorLabels") or []),
            " ".join(cutscene.get("paths") or []),
            " ".join(cutscene.get("audioEvents") or []),
            " ".join(cutscene.get("tags") or []),
            " ".join(text_groups),
            indexed_line_haystack(lines, "text"),
            component_summary,
            " ".join(variant["name"] for variant in (cutscene.get("variants") or [])),
            " ".join(cutscene.get("keepCameraPaths") or []),
        ] if part)
        line_preview = next((line.get("text") or "" for line in lines if line.get("text")), "")
        entry = {
            "k": cutscene_key,
            "d": "cutscene",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": [],
            "n": len(lines),
            "p": preview(line_preview or " | ".join(part for part in (
                component_summary,
                (cutscene.get("paths") or [""])[0] if cutscene.get("paths") else "",
                (", ".join(cutscene.get("levels") or []) if cutscene.get("levels") else ""),
                (", ".join(cutscene.get("actorLabels")[:3]) if cutscene.get("actorLabels") else ""),
            ) if part)),
            "tags": ["cutscene", *(["cutsceneText"] if lines else [])],
        }
        if search_text:
            entry["x"] = search_text
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)

    env_talk_speaker_hints_by_env: dict[str, list[dict]] = defaultdict(list)
    for env_id, proxy_ids in env_talk_proxy_ids_by_env.items():
        seen_hint_keys: set[tuple[str, str]] = set()
        for proxy_id in proxy_ids:
            row_id, proxy_row = npc_proxy_rows_by_proxy_id.get(proxy_id, ("", {}))
            proxy_info = npc_proxy_info.get(proxy_id) if isinstance(npc_proxy_info, dict) else None
            candidates = [*npc_proxy_actor_candidates(proxy_id), proxy_id]
            actor_id = ""
            speaker_name = ""
            for candidate in _unique_preserve(candidates):
                actor_id = speaker_actor_id(candidate) or (candidate if candidate in actor_names else "")
                speaker_name = speaker_display_name(candidate)
                if speaker_name:
                    break

            if not speaker_name and isinstance(proxy_row, dict):
                override_name_key = str(((proxy_row.get("overrideNpcNameId") or {}).get("key")) or "")
                if proxy_row.get("ifOverrideNpcName") and override_name_key:
                    speaker_name = named_text(override_name_key)
                    actor_id = actor_id or proxy_id

            if not speaker_name:
                continue
            hint_key = (actor_id or proxy_id, speaker_name)
            if hint_key in seen_hint_keys:
                continue
            seen_hint_keys.add(hint_key)
            env_talk_speaker_hints_by_env[env_id].append({
                "actorId": actor_id or proxy_id,
                "speakerName": speaker_name,
                "proxyId": proxy_id,
                "source": {
                    "table": "NpcProxyTable",
                    "rowId": row_id or proxy_id,
                    "fields": pick_fields(
                        proxy_row if isinstance(proxy_row, dict) else {},
                        "proxyId",
                        "levelId",
                        "envTalkIds",
                        "ifOverrideNpcName",
                        "overrideNpcNameId",
                    ),
                    "proxyInfoData": pick_fields(
                        proxy_info if isinstance(proxy_info, dict) else {},
                        "npcId",
                        "npcNameId",
                        "mapId",
                        "npcProxyType",
                    ),
                },
            })

    # Emit environment conversations
    print(f"Writing {len(env_talks)} environment conversations...")
    for env_id in sorted(env_talks):
        entry = env_talks[env_id]
        env_npc = env_npc_meta.get(env_id)
        env_speaker_hints = env_talk_speaker_hints_by_env.get(env_id) or []
        lines = []
        actors: set[str] = set()
        prev_text = ""
        for item in sorted(entry.get("envTalkDataList", []) or [], key=lambda x: x.get("index", 0)):
            raw_actor_id = str(item.get("actorId") or "").strip()
            raw_actor_name = speaker_display_name(raw_actor_id)
            speaker_hint = env_speaker_hints[0] if env_speaker_hints and not raw_actor_name else None
            actor_id = (
                (raw_actor_id if raw_actor_name or not speaker_hint else "")
                or ((speaker_hint or {}).get("actorId") if speaker_hint else "")
                or raw_actor_id
                or (env_npc.get("npcId") if env_npc else "")
                or ""
            )
            actor = (
                raw_actor_name
                or ((speaker_hint or {}).get("speakerName") if speaker_hint else "")
                or speaker_display_name(actor_id)
                or (env_npc.get("name") if env_npc else "")
                or (env_npc.get("title") if env_npc else "")
            )
            text = t(item.get("text", {}).get("id"))
            audio = item.get("audio") or ""
            emoji = item.get("emojiId") or ""
            duration = item.get("duration")
            slot = item.get("slotId")
            index = item.get("index")
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": item.get("envTalkId") or env_id,
                "cid": index,
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "audio": audio,
                "emoji": emoji,
                "duration": duration,
                "slot": slot,
                "_debug": {
                    **source_ref(
                        "EnvTalkTable.envTalkDataList",
                        item.get("envTalkId") or env_id,
                        pick_fields(
                            item,
                            "actorId",
                            "audio",
                            "duration",
                            "emojiId",
                            "envTalkId",
                            "index",
                            "slotId",
                            "text",
                        ),
                        nodeId=index,
                    ),
                    "fields": {
                        "text": text_trace(
                            "EnvTalkTable.envTalkDataList",
                            item.get("envTalkId") or env_id,
                            "text",
                            item.get("text"),
                        ),
                    },
                },
            })
            if speaker_hint:
                lines[-1]["_debug"]["speakerHint"] = speaker_hint
            if not prev_text and text:
                prev_text = text

        out_key = f"env_{env_id}"
        kind, mission, mission_type, index_tags = env_index_slot(env_id)
        env_payload = {
            "key": out_key,
            "kind": kind,
            "mission": mission,
            "title": env_id,
            "cooldown": entry.get("envTalkCd"),
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "EnvTalkTable",
                    env_id,
                    pick_fields(entry, "envTalkCd", "envTalkDataList", "envTalkId"),
                ),
            },
        }
        if env_speaker_hints:
            env_payload["_debug"]["speakerHints"] = env_speaker_hints
        if env_npc:
            env_payload["npc"] = env_npc
            env_payload["_debug"]["npc"] = env_npc["_debug"]
        write_conv_payload(out_key, env_payload)

        index_entry = {
            "k": out_key,
            "d": kind,
            "m": mission,
            "s": 0,
            "t": mission_type,
            "a": 0,
            "title": env_id,
            "c": sorted(actors),
            "n": len(lines),
            "p": preview(prev_text),
            "tags": index_tags,
        }
        if (xt := indexed_line_haystack(lines, "text", "actor", "aid", "emoji")):
            index_entry["x"] = xt
        index_entry["x"] = merge_search_text(index_entry.get("x", ""), mission_context_text(mission))
        if not index_entry["x"]:
            index_entry.pop("x")
        index_entries.append(index_entry)

        if story_mission := env_story_missions.get(env_id):
            env_entry = {
                "key": out_key,
                "id": env_id,
                "cooldown": entry.get("envTalkCd"),
                "lines": lines,
                "_debug": {
                    "source": source_ref(
                        "EnvTalkTable",
                        env_id,
                        pick_fields(entry, "envTalkCd", "envTalkDataList", "envTalkId"),
                    ),
                },
            }
            if env_speaker_hints:
                env_entry["_debug"]["speakerHints"] = env_speaker_hints
            if env_npc:
                env_entry["npc"] = env_npc
                env_entry["_debug"]["npc"] = env_npc["_debug"]
            if hints := env_story_binding_hints.get(env_id):
                levels = sorted(hints["levels"])
                proxies = sorted(hints["proxies"])
                if levels or proxies:
                    env_entry["_attachHints"] = {
                        "levels": levels,
                        "proxies": proxies,
                    }
                    env_entry["_debug"]["bindingHints"] = {
                        "source": {
                            "levels": levels,
                            "proxyIds": proxies,
                            "refs": hints["sources"],
                        }
                    }
            story_env_entries_by_mission[story_mission].append(env_entry)

    wiki_category_names: dict[str, str] = {}
    wiki_group_names: dict[str, str] = {}
    wiki_group_to_category: dict[str, str] = {}
    for category_id, category_row in sorted(
        wiki_categories.items(),
        key=lambda item: (int((item[1] or {}).get("categoryPriority") or 0), item[0]),
    ):
        if not isinstance(category_row, dict):
            continue
        category_name = brace_text(t((category_row.get("categoryName") or {}).get("id"))) or category_id
        wiki_category_names[category_id] = category_name
        extra_mission_names.setdefault(category_id, category_name)
        group_rows = ((wiki_groups.get(category_id) or {}).get("list") or [])
        for group_row in group_rows:
            if not isinstance(group_row, dict):
                continue
            group_id = str(group_row.get("groupId") or "")
            if not group_id:
                continue
            group_name = brace_text(t((group_row.get("groupName") or {}).get("id"))) or group_id
            wiki_group_names[group_id] = group_name
            wiki_group_to_category[group_id] = category_id
            extra_mission_names.setdefault(group_id, group_name)

    def wiki_category_id(row_id: str, row: dict) -> str:
        group_id = str(row.get("groupId") or "")
        if group_id in wiki_group_to_category:
            return wiki_group_to_category[group_id]
        if row_id.startswith("wiki_tut_"):
            return "wiki_type_tutorial"
        if str(row.get("refMonsterTemplateId") or ""):
            return "wiki_type_monster"
        ref_item_id = str(row.get("refItemId") or "")
        if ref_item_id.startswith("wpn_"):
            return "wiki_type_weapon"
        if group_id.startswith("wiki_group_building_"):
            return "wiki_type_building"
        if group_id.startswith("wiki_group_weapon_"):
            return "wiki_type_weapon"
        if group_id.startswith("wiki_group_monster_"):
            return "wiki_type_monster"
        if group_id.startswith("wiki_group_tutorial_"):
            return "wiki_type_tutorial"
        if group_id.startswith("wiki_group_equip_") or group_id.startswith("suit_") or group_id.startswith("domain_"):
            return "wiki_type_equip"
        return "wiki_type_item"

    wiki_text_fingerprints: set[tuple[str, ...]] = set()

    print(f"Writing {len(wiki_entry_data)} wiki entries...")
    for row_id, row in sorted(
        wiki_entry_data.items(),
        key=lambda item: (
            wiki_category_id(item[0], item[1] if isinstance(item[1], dict) else {}),
            str((item[1] or {}).get("groupId") or ""),
            int((item[1] or {}).get("order") or 0),
            item[0],
        ),
    ):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("groupId") or "")
        category_id = wiki_category_id(row_id, row)
        category_name = wiki_category_names.get(category_id, category_id)
        group_name = wiki_group_names.get(group_id, group_id or category_name)
        mission_id = group_id or category_id
        if mission_id:
            extra_mission_names.setdefault(mission_id, group_name if group_id else category_name)

        row_desc = t((row.get("desc") or {}).get("id"))
        ref_item_id = str(row.get("refItemId") or "")
        ref_monster_id = str(row.get("refMonsterTemplateId") or "")
        prts_id = str(row.get("prtsId") or "")
        item_row = item_rows.get(ref_item_id) if isinstance(item_rows.get(ref_item_id), dict) else {}
        weapon_row = weapon_basic.get(ref_item_id) if isinstance(weapon_basic.get(ref_item_id), dict) else {}
        enemy_row = (
            enemy_template_display.get(ref_monster_id)
            if isinstance(enemy_template_display.get(ref_monster_id), dict)
            else enemy_display_info.get(ref_monster_id)
            if isinstance(enemy_display_info.get(ref_monster_id), dict)
            else {}
        )

        title = row_id
        lines: list[dict] = []
        summary_rows: list[dict] = []
        seen_texts: set[tuple[str, str]] = set()

        def add_line(line_id: str, text: str, *, hint: str = "", debug: dict | None = None) -> None:
            normalized = (text or "").strip()
            if not normalized:
                return
            key = (hint, normalized)
            if key in seen_texts:
                return
            seen_texts.add(key)
            line = {"id": line_id, "text": normalized}
            if hint:
                line["hint"] = hint
            if debug:
                line["_debug"] = debug
            lines.append(line)

        if category_id in {"wiki_type_item", "wiki_type_equip", "wiki_type_building", "wiki_type_weapon"}:
            title = brace_text(t((item_row.get("name") or {}).get("id"))) or title
            item_desc = t((item_row.get("desc") or {}).get("id"))
            deco_desc = t((item_row.get("decoDesc") or {}).get("id"))
            add_line(
                f"{row_id}_desc",
                item_desc,
                debug={
                    **source_ref("ItemTable", ref_item_id, pick_fields(item_row, "desc", "decoDesc", "id", "name", "obtainWayIds", "rarity", "type")),
                    "fields": {
                        "text": text_trace("ItemTable", ref_item_id, "desc", item_row.get("desc")),
                    },
                } if item_row else None,
            )
            add_line(
                f"{row_id}_deco",
                deco_desc,
                hint="Flavor",
                debug={
                    **source_ref("ItemTable", ref_item_id, pick_fields(item_row, "desc", "decoDesc", "id", "name")),
                    "fields": {
                        "text": text_trace("ItemTable", ref_item_id, "decoDesc", item_row.get("decoDesc")),
                    },
                } if item_row else None,
            )
            if category_id == "wiki_type_weapon":
                weapon_desc = t((weapon_row.get("weaponDesc") or {}).get("id"))
                add_line(
                    f"{row_id}_weapon",
                    weapon_desc,
                    hint="Weapon",
                    debug={
                        **source_ref("WeaponBasicTable", ref_item_id, pick_fields(weapon_row, "rarity", "weaponDesc", "weaponId", "weaponSkillList", "weaponType")),
                        "fields": {
                            "text": text_trace("WeaponBasicTable", ref_item_id, "weaponDesc", weapon_row.get("weaponDesc")),
                        },
                    } if weapon_row else None,
                )
                if weapon_row.get("weaponSkillList"):
                    summary_rows.append({"text": "Skills: " + ", ".join(str(skill_id) for skill_id in weapon_row.get("weaponSkillList") or [])})
            if item_row.get("rarity") is not None:
                summary_rows.append({"text": f"Rarity: {item_row['rarity']}"})
            if craft_row := (wiki_craft_jump.get(ref_item_id) if isinstance(wiki_craft_jump.get(ref_item_id), dict) else {}):
                if craft_row.get("blueprintId"):
                    summary_rows.append({"text": f"Blueprint: {craft_row['blueprintId']}"})
                if craft_row.get("blackboxId"):
                    summary_rows.append({"text": f"Blackbox: {craft_row['blackboxId']}"})
            if default_craft := str(wiki_default_craft.get(ref_item_id) or ""):
                summary_rows.append({"text": f"Default craft: {default_craft}"})
        elif category_id == "wiki_type_monster":
            title = (
                brace_text(t((enemy_row.get("name") or {}).get("id")))
                or brace_text(t((enemy_row.get("nickname") or {}).get("id")))
                or title
            )
            enemy_desc = t((enemy_row.get("description") or {}).get("id"))
            add_line(
                f"{row_id}_desc",
                enemy_desc,
                debug={
                    **source_ref(
                        "EnemyTemplateDisplayInfoTable",
                        ref_monster_id,
                        pick_fields(enemy_row, "abilityDescIds", "description", "name", "nickname", "templateId"),
                    ),
                    "fields": {
                        "text": text_trace("EnemyTemplateDisplayInfoTable", ref_monster_id, "description", enemy_row.get("description")),
                    },
                } if enemy_row else None,
            )
            nickname = brace_text(t((enemy_row.get("nickname") or {}).get("id")))
            if nickname and nickname != title:
                summary_rows.append({"text": f"Alias: {nickname}"})
            for ability_id in enemy_row.get("abilityDescIds") or []:
                ability_row = enemy_ability_desc.get(ability_id) if isinstance(enemy_ability_desc.get(ability_id), dict) else {}
                ability_name = brace_text(t((ability_row.get("name") or {}).get("id"))) or str(ability_id)
                ability_text = t((ability_row.get("description") or {}).get("id"))
                summary_rows.append({
                    "text": f"Ability: {ability_name}" + (f" - {ability_text}" if ability_text else ""),
                    "_debug": source_ref(
                        "EnemyAbilityDescTable",
                        str(ability_id),
                        pick_fields(ability_row, "abilityId", "description", "name"),
                    ) if ability_row else None,
                })
        elif category_id == "wiki_type_tutorial":
            page_ids = []
            page_ref_row = (
                wiki_tutorial_pages_by_entry.get(row_id)
                if isinstance(wiki_tutorial_pages_by_entry.get(row_id), dict)
                else {}
            )
            page_ids = [str(page_id) for page_id in (page_ref_row.get("pageIds") or []) if str(page_id)]
            page_title_candidates: list[str] = []
            for page_id in page_ids:
                page_row = wiki_tutorial_pages.get(page_id) if isinstance(wiki_tutorial_pages.get(page_id), dict) else {}
                page_title = brace_text(t((page_row.get("title") or {}).get("id")))
                page_text = t((page_row.get("content") or {}).get("id"))
                if page_title:
                    page_title_candidates.append(page_title)
                add_line(
                    page_id,
                    page_text,
                    hint=page_title,
                    debug={
                        **source_ref(
                            "WikiTutorialPageTable",
                            page_id,
                            pick_fields(page_row, "content", "id", "image", "order", "refWikiEntryIds", "title", "tutorialId", "video", "videoDeviceType"),
                        ),
                        "fields": {
                            "title": text_trace("WikiTutorialPageTable", page_id, "title", page_row.get("title")),
                            "text": text_trace("WikiTutorialPageTable", page_id, "content", page_row.get("content")),
                        },
                    } if page_row else None,
                )
                media_bits = []
                if page_row.get("image"):
                    media_bits.append(f"image={page_row['image']}")
                if page_row.get("video"):
                    media_bits.append(f"video={page_row['video']}")
                if media_bits:
                    summary_rows.append({"text": f"{page_title or page_id}: " + ", ".join(media_bits)})
            title = next((candidate for candidate in page_title_candidates if candidate), row_id)

        if row_desc:
            add_line(
                f"{row_id}_wiki",
                row_desc,
                hint="Wiki",
                debug={
                    **source_ref("WikiEntryDataTable", row_id, pick_fields(row, "desc", "groupId", "id", "order", "prtsId", "refItemId", "refMonsterTemplateId")),
                    "fields": {
                        "text": text_trace("WikiEntryDataTable", row_id, "desc", row.get("desc")),
                    },
                },
            )

        summary_rows.insert(0, {"text": f"Category: {category_name}"})
        if group_name and group_name != category_name:
            summary_rows.insert(1, {"text": f"Group: {group_name}"})
        if prts_id:
            summary_rows.append({"text": f"PRTS: {prts_id}"})
        if ref_item_id:
            summary_rows.append({"text": f"Ref item: {ref_item_id}"})
        if ref_monster_id:
            summary_rows.append({"text": f"Ref enemy: {ref_monster_id}"})

        wiki_fp = text_sequence_fingerprint(lines)
        if wiki_fp:
            wiki_text_fingerprints.add(wiki_fp)

        payload = {
            "key": row_id,
            "kind": "wiki",
            "mission": mission_id,
            "scene": int(row.get("order") or 0),
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "WikiEntryDataTable",
                    row_id,
                    pick_fields(row, "desc", "groupId", "id", "order", "prtsId", "refItemId", "refMonsterTemplateId"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        if group_id:
            payload["_debug"]["group"] = {
                "categoryId": category_id,
                "categoryName": category_name,
                "groupId": group_id,
                "groupName": group_name,
            }
        write_conv_payload(row_id, payload)
        entry = {
            "k": row_id,
            "d": "wiki",
            "m": mission_id,
            "s": int(row.get("order") or 0),
            "t": "wiki",
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": ["wiki", category_id, group_id or category_id],
        }
        search_text = " ".join(
            part
            for part in [
                row_id,
                category_id,
                category_name,
                group_id,
                group_name,
                title,
                row_desc,
                ref_item_id,
                ref_monster_id,
                prts_id,
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    operator_archive_rows = [row for row in character_rows.values() if isinstance(row, dict) and ((row.get("profileRecord") or []) or (row.get("profileVoice") or []))]
    print(f"Writing {len(operator_archive_rows)} operator archive pages...")
    for char_id, row in sorted(
        ((char_id, row) for char_id, row in character_rows.items() if isinstance(row, dict)),
        key=lambda item: (int((item[1] or {}).get("sortOrder") or 0), item[0]),
    ):
        profile_records = [item for item in (row.get("profileRecord") or []) if isinstance(item, dict)]
        profile_voice = [item for item in (row.get("profileVoice") or []) if isinstance(item, dict)]
        if not profile_records and not profile_voice:
            continue

        actor_id = char_id.split("_", 2)[-1] if char_id.startswith("chr_") else char_id
        char_name = (
            brace_text(t((row.get("name") or {}).get("id")))
            or speaker_display_name(actor_id)
            or speaker_display_name(char_id)
            or char_id
        )
        extra_mission_names[char_id] = char_name

        title = char_name
        summary_rows: list[dict] = []
        summary_rows.append({"text": f"Profile sections: {len(profile_records)}"})
        summary_rows.append({"text": f"Voice entries: {len(profile_voice)}"})
        if department := str(row.get("department") or ""):
            summary_rows.append({"text": f"Department: {department}"})
        if cv_name := brace_text(t((((row.get("cvName") or {}).get("ChiCVName") or {}).get("id")))):
            summary_rows.append({"text": f"CV: {cv_name}"})
        if row.get("rarity") is not None:
            summary_rows.append({"text": f"Rarity: {row['rarity']}"})
        if char_type := str(row.get("charTypeId") or ""):
            summary_rows.append({"text": f"Type: {char_type}"})
        if weapon_type := row.get("weaponType"):
            summary_rows.append({"text": f"Weapon type: {weapon_type}"})
        if default_weapon_id := str(row.get("defaultWeaponId") or ""):
            weapon_item_row = item_rows.get(default_weapon_id) if isinstance(item_rows.get(default_weapon_id), dict) else {}
            weapon_name = brace_text(t((weapon_item_row.get("name") or {}).get("id"))) or default_weapon_id
            summary_rows.append({"text": f"Default weapon: {weapon_name}"})

        lines: list[dict] = []
        for record in sorted(profile_records, key=lambda item: (int(item.get("recordIndex") or 0), str(item.get("id") or ""))):
            record_text = t((record.get("recordDesc") or {}).get("id"))
            if not record_text:
                continue
            record_title = brace_text(t((record.get("recordTitle") or {}).get("id"))) or str(record.get("recordID") or record.get("id") or "")
            lines.append({
                "id": str(record.get("id") or record.get("recordID") or f"{char_id}_record"),
                "text": record_text,
                "hint": record_title,
                "_debug": {
                    **source_ref(
                        "CharacterTable.profileRecord",
                        char_id,
                        pick_fields(record, "charId", "id", "recordDesc", "recordID", "recordIndex", "recordTitle", "unlockType", "unlockValue"),
                        nodeId=record.get("recordIndex"),
                    ),
                    "fields": {
                        "title": text_trace("CharacterTable.profileRecord", str(record.get("id") or char_id), "recordTitle", record.get("recordTitle")),
                        "text": text_trace("CharacterTable.profileRecord", str(record.get("id") or char_id), "recordDesc", record.get("recordDesc")),
                    },
                },
            })
        for voice in sorted(profile_voice, key=lambda item: (int(item.get("voiceIndex") or 0), str(item.get("id") or ""))):
            voice_text = t((voice.get("voiceDesc") or {}).get("id"))
            if not voice_text:
                continue
            voice_title = brace_text(t((voice.get("voiceTitle") or {}).get("id"))) or str(voice.get("voId") or voice.get("id") or "")
            lines.append({
                "id": str(voice.get("id") or voice.get("voId") or f"{char_id}_voice"),
                "aid": actor_id,
                "actor": char_name,
                "text": voice_text,
                "hint": voice_title,
                "_debug": {
                    **source_ref(
                        "CharacterTable.profileVoice",
                        char_id,
                        pick_fields(voice, "charId", "id", "unlockType", "unlockValue", "voId", "voiceDesc", "voiceIndex", "voiceTitle"),
                        nodeId=voice.get("voiceIndex"),
                    ),
                    "fields": {
                        "title": text_trace("CharacterTable.profileVoice", str(voice.get("id") or char_id), "voiceTitle", voice.get("voiceTitle")),
                        "text": text_trace("CharacterTable.profileVoice", str(voice.get("id") or char_id), "voiceDesc", voice.get("voiceDesc")),
                    },
                },
            })
        if not lines:
            continue

        out_key = f"wiki_{char_id}"
        payload = {
            "key": out_key,
            "kind": "table_charactertable",
            "mission": char_id,
            "scene": 0,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "CharacterTable",
                    char_id,
                    pick_fields(row, "charId", "cvName", "defaultWeaponId", "department", "name", "profileRecord", "profileVoice", "rarity", "sortOrder"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": "table_charactertable",
            "m": char_id,
            "s": 0,
            "t": "table_charactertable",
            "a": 0,
            "title": title,
            "c": [actor_id] if actor_id else [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": ["wiki", "character", "archive", "table_charactertable"],
        }
        search_text = " ".join(
            part
            for part in [
                char_id,
                actor_id,
                char_name,
                str(row.get("department") or ""),
                str(row.get("charTypeId") or ""),
                str(row.get("defaultWeaponId") or ""),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)



    story_reference_only_tags = {
        "achievement",
        "enemyAbility",
        "errorCode",
        "gameMechanic",
        "growth",
        "skillPatch",
        "snsChat",
        "tip",
    }


    def write_reference_page(
        out_key: str,
        mission_id: str,
        scene: int,
        title: str,
        lines: list[dict],
        *,
        kind: str | None = None,
        type_key: str | None = None,
        source_debug: dict | None = None,
        summary_rows: list[dict] | None = None,
        tags: list[str] | None = None,
        search_parts: list[str] | None = None,
        actors: list[str] | None = None,
        preview_text: str | None = None,
        debug_extra: dict | None = None,
    ) -> None:
        if not title and not lines and not summary_rows:
            return
        raw_tags = [str(tag or "") for tag in (tags or ["wiki"]) if str(tag or "")]
        if (
            not include_reference_in_story_index
            and story_reference_only_tags & set(raw_tags)
        ):
            return
        entry_tags = normalized_reference_tags(raw_tags, mission_id)
        ref_kind = str(kind or reference_kind_from_tags(tags))
        ref_type = str(type_key or ref_kind)
        payload = {
            "key": out_key,
            "kind": ref_kind,
            "mission": mission_id,
            "scene": scene,
            "title": title or out_key,
            "lines": lines,
            "_debug": {},
        }
        if source_debug:
            payload["_debug"]["source"] = source_debug
        if summary_rows:
            payload["summary"] = summary_rows
        if debug_extra:
            payload["_debug"].update(debug_extra)
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": ref_kind,
            "m": mission_id,
            "s": scene,
            "t": ref_type,
            "a": 0,
            "title": title or out_key,
            "c": list(actors or []),
            "n": len(lines),
            "p": preview(
                preview_text
                or next((line.get("text") or "" for line in lines if line.get("text")), title or out_key)
            ),
            "tags": entry_tags,
        }
        search_text = " ".join(
            part
            for part in [
                *(search_parts or []),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("actor") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
                " ".join(row.get("text") or "" for row in (summary_rows or [])),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    def character_page_title(char_id: str) -> str:
        row = character_rows.get(char_id) if isinstance(character_rows.get(char_id), dict) else {}
        actor_id = char_id.split("_", 2)[-1] if char_id.startswith("chr_") else char_id
        return (
            brace_text(t((row.get("name") or {}).get("id")))
            or speaker_display_name(actor_id)
            or speaker_display_name(char_id)
            or char_id
        )



    def collection_hint_from_path(path: str) -> str:
        tokens: list[str] = []
        raw = str(path or "")
        if raw.startswith("$."):
            raw = raw[2:]
        elif raw == "$":
            raw = ""
        for piece in [part for part in raw.split(".") if part]:
            base = re.sub(r"\[\d+\]", "", piece)
            idx_matches = [int(match) + 1 for match in re.findall(r"\[(\d+)\]", piece)]
            label = collection_display_name(base)
            if idx_matches:
                label = f"{label} {idx_matches[-1]}"
            if label:
                tokens.append(label)
        return " / ".join(tokens[-2:])


    def collection_bucket(table_name: str, row_id: str, row: dict | None) -> str:
        if table_name == "CommonDeathTips.json":
            return "common_death_tips"
        if table_name == "DisplayEnemyTypeTable.json":
            return "display_enemy_type"
        if table_name == "TextTable.json":
            return collection_bucket_from_key(row_id)
        if isinstance(row, dict):
            for field in (
                "groupId",
                "categoryId",
                "formulaGroupId",
                "gameCategory",
                "machineId",
                "owner",
                "charId",
                "charTypeId",
                "profession",
                "weaponType",
                "roomType",
                "pageType",
                "tagType",
                "type",
            ):
                value = row.get(field)
                if isinstance(value, str) and value and len(value) <= 48:
                    return value
                if isinstance(value, int | float) and field in {"roomType", "pageType", "tagType"}:
                    return f"{field}_{int(value)}"
        return collection_bucket_from_key(row_id)

    def collection_reading_story_ref(
        table_name: str,
        row_id: str,
        row: dict | None,
    ) -> tuple[str, int, str] | None:
        if table_name not in {"PrtsReading.json", "ReadingPopUpTable.json", "RichContentTable.json"}:
            return None

        candidates: list[str] = []
        if table_name == "PrtsReading.json" and isinstance(row, dict):
            items = row.get("list") or {}
            if isinstance(items, dict):
                sorted_items = sorted(
                    ((node_id, node) for node_id, node in items.items() if isinstance(node, dict)),
                    key=lambda item: (int((item[1] or {}).get("order") or 0), str(item[0])),
                )
                for _node_id, node in sorted_items:
                    content_id = str(node.get("contentId") or "").strip()
                    if content_id:
                        candidates.append(content_id)
        elif table_name == "ReadingPopUpTable.json" and isinstance(row, dict):
            content_id = str(row.get("contentId") or "").strip()
            if content_id:
                candidates.append(content_id)
        elif table_name == "RichContentTable.json" and isinstance(row, dict):
            title_text = rich_content_title_text(str(row_id or ""))
            if title_text:
                candidates.append(title_text)

        candidates.append(str(row_id or ""))

        return (
            collection_story_ref_from_identifiers(*candidates)
            or collection_map_ref_from_identifiers(*candidates)
        )

    collection_story_mission_pattern = re.compile(
        r"(?<![a-z0-9])((?:gm|sm|db|dm|[acefm])\d+(?:[a-z]\d+)*(?:d\d+)?)(?![a-z0-9])",
        re.IGNORECASE,
    )
    collection_map_pattern = re.compile(r"map\d+_lv\d+", re.IGNORECASE)


    def collection_story_ref_from_identifiers(*values: str) -> tuple[str, int, str] | None:
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered.startswith("topic_"):
                return (value, 0, "topic")
            if lowered.startswith("sr_"):
                return (value, 0, "f")
            if match := collection_story_mission_pattern.findall(lowered):
                mission_id = match[-1]
                type_key, _act = parse_mission(mission_id)
                if type_key in MISSION_STORY_TYPES:
                    return (mission_id, collection_scene_suffix(value), type_key)
        return None

    def collection_map_ref_from_identifiers(*values: str) -> tuple[str, int, str] | None:
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if match := collection_map_pattern.findall(lowered):
                return (match[-1], collection_scene_suffix(value), "map")
        return None

    def collection_story_ref_from_bucket(bucket: str) -> tuple[str, int, str] | None:
        candidates: set[str] = set()
        for match in collection_story_mission_pattern.finditer(str(bucket or "").lower()):
            mission_id = match.group(1)
            type_key, _act = parse_mission(mission_id)
            if type_key in MISSION_STORY_TYPES:
                candidates.add(mission_id)
        if len(candidates) != 1:
            return None

        mission_id = next(iter(candidates))
        type_key, _act = parse_mission(mission_id)
        return (mission_id, 0, type_key)

    def collection_bucket_token(bucket: str) -> str:
        slug = collection_slug(bucket)
        checksum = sum((idx + 1) * ord(ch) for idx, ch in enumerate(str(bucket or ""))) % 104729
        return f"{slug}_{checksum:x}" if checksum else slug




    prts_archive_categories = ("collection", "digital", "document", "media", "paper", "report")

    def prts_archive_category_from_identifier(value) -> str:
        raw = re.sub(r"[^0-9A-Za-z]+", "_", str(value or "")).strip("_").lower()
        if not raw:
            return ""
        if raw.startswith("nar_"):
            raw = raw[4:]
        if raw.startswith("multi_media"):
            return "media"
        for category_key in prts_archive_categories:
            if raw == category_key or raw.startswith(f"{category_key}_"):
                return category_key
        return ""

    def prts_archive_category_from_collection_ids(collection_ids) -> str:
        counts: dict[str, int] = {}
        first_seen: dict[str, int] = {}
        for idx, raw_id in enumerate(collection_ids or []):
            category_key = prts_archive_category_from_identifier(raw_id)
            if not category_key:
                continue
            counts[category_key] = counts.get(category_key, 0) + 1
            first_seen.setdefault(category_key, idx)
        if not counts:
            return ""
        return min(
            counts,
            key=lambda category_key: (-counts[category_key], first_seen.get(category_key, 0), category_key),
        )

    def prts_archive_category_from_row(
        table_name: str,
        row_id: str,
        row: dict | None,
    ) -> str:
        if table_name == "PrtsCategory.json":
            if isinstance(row, dict):
                return prts_archive_category_from_identifier(row.get("categoryId"))
            return prts_archive_category_from_identifier(row_id)

        if isinstance(row, dict):
            for field in ("categoryId", "firstLvId", "id", "type"):
                category_key = prts_archive_category_from_identifier(row.get(field))
                if category_key:
                    return category_key
            if table_name in {"PrtsInvestigate.json", "PrtsInvestigateCategory.json"}:
                collection_ids: list[str] = []
                for field in ("collectionIdList",):
                    values = row.get(field) or []
                    if isinstance(values, list):
                        collection_ids.extend(str(value) for value in values if str(value))
                for field in ("categoryDataList", "list"):
                    groups = row.get(field) or []
                    if not isinstance(groups, list):
                        continue
                    for group_row in groups:
                        if not isinstance(group_row, dict):
                            continue
                        values = group_row.get("collectionIdList") or []
                        if isinstance(values, list):
                            collection_ids.extend(str(value) for value in values if str(value))
                category_key = prts_archive_category_from_collection_ids(collection_ids)
                if category_key:
                    return category_key

        return prts_archive_category_from_identifier(row_id)

    def prts_category_display_name(category_key: str) -> str:
        row = prts_categories.get(category_key) if isinstance(prts_categories.get(category_key), dict) else {}
        return (
            brace_text(t((row.get("name") or {}).get("id")))
            or str(category_key or "").replace("_", " ").strip().title()
        )

    prts_note_metadata: dict[str, dict] = {}
    for research_id, research_row in sorted(prts_investigate_categories.items()):
        if not isinstance(research_row, dict):
            continue
        for list_index, list_row in enumerate(research_row.get("list") or [], start=1):
            if not isinstance(list_row, dict):
                continue
            note_title = brace_text(t((list_row.get("name") or {}).get("id")))
            category_key = prts_archive_category_from_collection_ids(list_row.get("collectionIdList") or [])
            collection_ids = [
                str(value)
                for value in (list_row.get("collectionIdList") or [])
                if str(value)
            ]
            for note_id in (list_row.get("noteIdList") or []):
                note_key = str(note_id or "").strip()
                if not note_key:
                    continue
                meta = prts_note_metadata.setdefault(note_key, {})
                if note_title and not meta.get("title"):
                    meta["title"] = note_title
                if category_key and not meta.get("category"):
                    meta["category"] = category_key
                meta.setdefault("researchId", str(research_id))
                meta.setdefault("index", int(list_row.get("index") or list_index))
                if collection_ids and not meta.get("collectionIds"):
                    meta["collectionIds"] = list(collection_ids)

    prts_content_ids = {
        str((row or {}).get("contentId") or "")
        for row in prts_all_items.values()
        if isinstance(row, dict) and str((row or {}).get("contentId") or "")
    }
    prts_investigate_metadata_by_unlock_prts: dict[str, list[dict]] = defaultdict(list)
    for research_id, research_row in sorted(load("PrtsInvestigate.json").items()):
        if not isinstance(research_row, dict):
            continue
        unlock_prts = str(research_row.get("unlockPrts") or "").strip()
        if not unlock_prts:
            continue
        research_name = brace_text(t((research_row.get("name") or {}).get("id")))
        research_desc = t((research_row.get("desc") or {}).get("id"))
        if not research_name and not research_desc:
            continue
        prts_investigate_metadata_by_unlock_prts[unlock_prts].append({
            "researchId": str(research_id),
            "title": research_name,
            "desc": research_desc,
        })

    def collection_tags(
        table_name: str,
        row_id: str,
        bucket: str,
        row: dict | None = None,
        *,
        table_source: str = "streaming",
        variant: bool = False,
    ) -> list[str]:
        stem = table_name.removesuffix(".json")
        tags = [
            "wiki",
            "collection",
            f"table_{collection_slug(stem)}",
            f"source_{collection_slug(table_source)}",
        ]
        lower = stem.lower()
        for needle, tag in (
            ("activity", "activity"),
            ("achievement", "achievement"),
            ("battlepass", "battlePass"),
            ("char", "character"),
            ("dungeon", "dungeon"),
            ("enemy", "enemy"),
            ("factory", "factory"),
            ("item", "item"),
            ("jump", "systemJump"),
            ("mail", "mail"),
            ("money", "money"),
            ("picture", "picture"),
            ("radio", "radio"),
            ("skill", "skill"),
            ("system", "system"),
            ("task", "other"),
            ("tip", "other"),
            ("weapon", "weapon"),
        ):
            if tag == "system" and lower.startswith("systemjump"):
                continue
            if needle in lower and tag not in tags:
                tags.append(tag)
        if variant:
            tags.append("variant")
        bucket_slug = collection_slug(bucket)
        if bucket_slug and bucket_slug != "misc":
            tags.append(f"group_{bucket_slug}")
        if isinstance(row, dict):
            if isinstance(row.get("groupId"), str) and row.get("groupId"):
                tags.append(f"group_{collection_slug(row['groupId'])}")
            if isinstance(row.get("categoryId"), str) and row.get("categoryId"):
                tags.append(f"category_{collection_slug(row['categoryId'])}")
        prts_category_key = prts_archive_category_from_row(table_name, row_id, row)
        if prts_category_key:
            tags.append(f"category_{collection_slug(prts_category_key)}")
        deduped: list[str] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    def collect_reference_text_nodes(
        table_name: str,
        row_id: str,
        raw_value,
        *,
        preferred_source: str = "streaming",
        path: str = "$",
        out: list[dict] | None = None,
    ) -> list[dict]:
        if out is None:
            out = []
        if isinstance(raw_value, dict):
            if "id" in raw_value and "text" in raw_value:
                text = t(raw_value.get("id"), preferred_source=preferred_source)
                if text:
                    field_name = re.sub(r"\[\d+\]", "", path.rsplit(".", 1)[-1] if "." in path else path)
                    out.append({
                        "field": field_name or "text",
                        "hint": collection_hint_from_path(path),
                        "path": path,
                        "raw": raw_value,
                        "text": text,
                    })
            for key, value in raw_value.items():
                child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                collect_reference_text_nodes(
                    table_name,
                    row_id,
                    value,
                    preferred_source=preferred_source,
                    path=child_path,
                    out=out,
                )
            return out
        if isinstance(raw_value, list):
            for idx, value in enumerate(raw_value):
                child_path = f"{path}[{idx}]"
                collect_reference_text_nodes(
                    table_name,
                    row_id,
                    value,
                    preferred_source=preferred_source,
                    path=child_path,
                    out=out,
                )
        return out

    def collection_row_title(
        table_name: str,
        row_id: str,
        text_nodes: list[dict],
        *,
        preferred_source: str = "streaming",
    ) -> str:
        preferred_fields = {
            "name",
            "title",
            "talentName",
            "gameName",
            "dungeonName",
            "tipsTitle",
            "topicName",
            "recordTitle",
            "voiceTitle",
            "iconDesc",
            "effectTitle",
        }
        for node in text_nodes:
            if node.get("field") in preferred_fields:
                return brace_text(node.get("text") or "") or (node.get("text") or "")
        if table_name == "TextTable.json":
            return row_id
        return row_id

    def collection_summary_rows(
        table_name: str,
        row_id: str,
        row: dict | None,
        bucket: str,
        *,
        table_source: str = "streaming",
        variant: bool = False,
    ) -> list[dict]:
        rows = [
            {"text": f"Table: {collection_display_name(table_name.removesuffix('.json'))}"},
            {"text": f"Row: {row_id}"},
        ]
        if table_source != "streaming":
            rows.append({"text": f"Source: {collection_source_label(table_source)}"})
        if variant:
            rows.append({"text": "Variant: differs from StreamingAssets row"})
        bucket_label = collection_display_name(bucket)
        if bucket_label and bucket_label != "Misc":
            rows.append({"text": f"Group: {bucket_label}"})
        if isinstance(row, dict):
            for field in ("groupId", "categoryId", "type", "gameCategory", "profession", "weaponType", "machineId", "roomType", "unlockMissionId"):
                value = row.get(field)
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, list):
                    preview_value = ", ".join(str(item) for item in value[:4])
                    if len(value) > 4:
                        preview_value += ", ..."
                else:
                    preview_value = str(value)
                rows.append({"text": f"{collection_display_name(field)}: {preview_value}"})
                if len(rows) >= 6:
                    break
        return rows

    def collect_exported_texttable_row_ids() -> set[str]:
        referenced = set(referenced_texttable_row_ids)

        def visit(value) -> None:
            if isinstance(value, dict):
                if value.get("table") == "TextTable" and value.get("rowId"):
                    remember_texttable_row_usage(value.get("rowId"))
                    referenced.add(str(value.get("rowId")))
                for nested in value.values():
                    visit(nested)
                return
            if isinstance(value, list):
                for nested in value:
                    visit(nested)

        for conv_path in sorted(written_conv_paths):
            if conv_path.stem.startswith("wiki_collection_texttable_"):
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            visit(payload)
        return referenced

    def write_texttable_collection_pages(excluded_row_ids: set[str] | None = None) -> None:
        excluded = {str(row_id) for row_id in (excluded_row_ids or set()) if str(row_id or "").strip()}
        chunks_by_bucket: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for row_id, row in sorted(text_table.items()):
            if not isinstance(row, dict):
                continue
            if row_id in excluded:
                continue
            text = t(row.get("id"))
            if not text:
                continue
            chunks_by_bucket[collection_bucket("TextTable.json", row_id, row)].append((row_id, row))

        total_pages = 0
        total_rows = 0
        chunk_size = 200
        for bucket, entries in sorted(chunks_by_bucket.items()):
            total_rows += len(entries)
            bucket_token = collection_bucket_token(bucket)
            story_ref = collection_story_ref_from_bucket(bucket)
            if story_ref:
                mission_id, _forced_scene_value, forced_type_key = story_ref
                extra_mission_names.setdefault(mission_id, collection_display_name(mission_id))
            else:
                mission_id = f"wiki_collection_texttable_{bucket_token}"
                forced_type_key = None
            for chunk_index, start in enumerate(range(0, len(entries), chunk_size), start=1):
                chunk = entries[start:start + chunk_size]
                lines: list[dict] = []
                for row_id, row in chunk:
                    text = t(row.get("id"))
                    if not text:
                        continue
                    lines.append({
                        "id": row_id,
                        "text": text,
                        "hint": row_id,
                        "_debug": {
                            **source_ref("TextTable", row_id, pick_fields(row, "id")),
                            "fields": {
                                "text": text_trace("TextTable", row_id, "id", row.get("id")),
                            },
                        },
                    })
                if not lines:
                    continue
                total_pages += 1
                title = f"TextTable / {collection_display_name(bucket)}"
                if len(entries) > chunk_size:
                    title += f" ({chunk_index})"
                out_key = f"wiki_collection_texttable_{bucket_token}_{chunk_index}"
                summary_rows = [
                    {"text": "Table: TextTable"},
                    {"text": f"Group: {collection_display_name(bucket)}"},
                    {"text": f"Entries: {len(lines)}"},
                ]
                write_reference_page(
                    out_key,
                    mission_id,
                    chunk_index,
                    title,
                    lines,
                    type_key=forced_type_key,
                    source_debug=source_ref("TextTable", bucket_token, {"entries": len(lines), "bucket": bucket}),
                    summary_rows=summary_rows,
                    tags=["wiki", "collection", "table_texttable", "source_streaming", f"group_{bucket_token}", "text"],
                    search_parts=[bucket, title, " ".join(line["id"] for line in lines[:50])],
                )
        skipped_rows = len(excluded & {str(row_id) for row_id in text_table})
        print(
            f"Writing {total_pages} text-table collection pages for {total_rows} entries "
            f"({skipped_rows} referenced rows skipped)..."
        )

    print(f"Writing {len(skill_patches)} skill patch reference pages...")
    for skill_id, row in sorted(skill_patches.items()):
        if not isinstance(row, dict):
            continue
        bundles = [bundle for bundle in (row.get("SkillPatchDataBundle") or []) if isinstance(bundle, dict)]
        if not bundles:
            continue
        title = next(
            (
                brace_text(t((bundle.get("skillName") or {}).get("id")))
                for bundle in bundles
                if brace_text(t((bundle.get("skillName") or {}).get("id")))
            ),
            skill_id,
        )
        summary_rows: list[dict] = []
        level_count = len([bundle for bundle in bundles if int(bundle.get("level") or 0) > 0])
        if level_count:
            summary_rows.append({"text": f"Levels: {level_count}"})
        icon_id = next((str(bundle.get("iconId") or "") for bundle in bundles if str(bundle.get("iconId") or "")), "")
        if icon_id:
            summary_rows.append({"text": f"Icon: {icon_id}"})
        tag_id = next((str(bundle.get("tagId") or "") for bundle in bundles if str(bundle.get("tagId") or "")), "")
        if tag_id:
            summary_rows.append({"text": f"Tag: {tag_id}"})
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        for bundle in sorted(bundles, key=lambda item: (int(item.get("level") or 0), str(item.get("skillId") or skill_id))):
            level = int(bundle.get("level") or 0)
            level_hint = f"Level {level}" if level else ""
            description = t((bundle.get("description") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{skill_id}_desc_{level}",
                description,
                hint=level_hint,
                debug={
                    **source_ref(
                        "SkillPatchTable.SkillPatchDataBundle",
                        skill_id,
                        pick_fields(bundle, "coolDown", "description", "iconId", "level", "skillId", "skillName", "subDescList", "subDescNameList", "tagId"),
                        nodeId=level,
                    ),
                    "fields": {
                        "title": text_trace("SkillPatchTable.SkillPatchDataBundle", skill_id, "skillName", bundle.get("skillName")),
                        "text": text_trace("SkillPatchTable.SkillPatchDataBundle", skill_id, "description", bundle.get("description")),
                    },
                } if description else None,
            )
            raw_sub_names = bundle.get("subDescNameList") or []
            raw_sub_values = bundle.get("subDescList") or []
            for idx, raw_name in enumerate(raw_sub_names, start=1):
                label = t((raw_name or {}).get("id"))
                if not label:
                    continue
                value = str(raw_sub_values[idx - 1] or "").strip() if idx - 1 < len(raw_sub_values) else ""
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{skill_id}_sub_{level}_{idx}",
                    label,
                    hint=" ".join(part for part in [level_hint, value] if part),
                    debug={
                        **source_ref(
                            "SkillPatchTable.SkillPatchDataBundle",
                            skill_id,
                            pick_fields(bundle, "level", "skillId", "subDescList", "subDescNameList"),
                            nodeId=level,
                            nodeIndex=idx - 1,
                        ),
                        "fields": {
                            "text": text_trace(
                                "SkillPatchTable.SkillPatchDataBundle",
                                skill_id,
                                f"subDescNameList[{idx - 1}]",
                                raw_name,
                            ),
                        },
                    },
                )
        if title == skill_id and not lines:
            continue
        write_reference_page(
            f"wiki_skill_{skill_id}",
            "SkillPatchTable",
            0,
            title,
            lines,
            source_debug=source_ref("SkillPatchTable", skill_id, pick_fields(row, "SkillPatchDataBundle")),
            summary_rows=summary_rows,
            tags=["wiki", "skillPatch", "table_skillpatchtable"],
            search_parts=[skill_id, title, tag_id],
        )

    print(f"Writing {len(char_growth)} character growth reference pages...")
    for char_id, row in sorted(char_growth.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or character_page_title(char_id)
        extra_mission_names.setdefault(char_id, title)
        summary_rows: list[dict] = []
        if row.get("rarity") is not None:
            summary_rows.append({"text": f"Rarity: {row['rarity']}"})
        if profession := str(row.get("profession") or ""):
            summary_rows.append({"text": f"Profession: {profession}"})
        if weapon_type := str(row.get("weaponType") or ""):
            summary_rows.append({"text": f"Weapon type: {weapon_type}"})
        if default_weapon_id := str(row.get("defaultWeaponId") or ""):
            summary_rows.append({"text": f"Default weapon: {default_weapon_id}"})
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("charBreakCostMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: (int((item[1] or {}).get("breakStage") or 0), item[0]),
        ):
            node_name = brace_text(t((node.get("name") or {}).get("id")))
            node_desc = t((node.get("description") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.charBreakCostMap",
                        char_id,
                        pick_fields(node, "breakStage", "charId", "description", "equipTierLimit", "name", "nodeId", "nodeType", "requiredItem"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.charBreakCostMap", char_id, "name", node.get("name")),
                        "text": text_trace("CharGrowthTable.charBreakCostMap", char_id, "description", node.get("description")),
                    },
                } if (node_desc or node_name) else None,
            )
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("skillGroupMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: item[0],
        ):
            node_name = brace_text(t((node.get("name") or {}).get("id")))
            node_desc = t((node.get("desc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.skillGroupMap",
                        char_id,
                        pick_fields(node, "desc", "name", "skillId", "skillType", "unlockLevel"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.skillGroupMap", char_id, "name", node.get("name")),
                        "text": text_trace("CharGrowthTable.skillGroupMap", char_id, "desc", node.get("desc")),
                    },
                } if (node_desc or node_name) else None,
            )
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("talentNodeMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: item[0],
        ):
            attr_node = node.get("attributeNodeInfo") if isinstance(node.get("attributeNodeInfo"), dict) else {}
            node_name = brace_text(t((attr_node.get("title") or {}).get("id")))
            node_desc = t((attr_node.get("desc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.talentNodeMap",
                        char_id,
                        pick_fields(node, "attributeNodeInfo", "nodeId", "nodeType", "preNodeId", "requiredItem", "unlockLevel"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.talentNodeMap", char_id, "attributeNodeInfo.title", attr_node.get("title")),
                        "text": text_trace("CharGrowthTable.talentNodeMap", char_id, "attributeNodeInfo.desc", attr_node.get("desc")),
                    },
                } if (node_desc or node_name) else None,
            )
        if title == char_id and not lines:
            continue
        write_reference_page(
            f"wiki_growth_{char_id}",
            char_id,
            0,
            title,
            lines,
            source_debug=source_ref(
                "CharGrowthTable",
                char_id,
                pick_fields(row, "charId", "charBreakCostMap", "defaultWeaponId", "name", "profession", "rarity", "skillGroupMap", "talentNodeMap", "weaponType"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "character", "growth", "table_chargrowthtable"],
            search_parts=[char_id, title, str(row.get("profession") or ""), str(row.get("weaponType") or "")],
            actors=[char_id.split("_", 2)[-1]] if char_id.startswith("chr_") else [],
        )

    print(f"Writing {len(game_mechanics)} game mechanic reference pages...")
    for mechanic_id, row in sorted(game_mechanics.items()):
        if not isinstance(row, dict):
            continue
        game_category = str(row.get("gameCategory") or "misc")
        mission_id = f"wiki_game_mechanic_{game_category}"
        title = brace_text(t((row.get("gameName") or {}).get("id"))) or mechanic_id
        desc = t((row.get("desc") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            mechanic_id,
            desc,
            debug={
                **source_ref(
                    "GameMechanicTable",
                    mechanic_id,
                    pick_fields(row, "conditionIds", "costStamina", "desc", "difficulty", "gameCategory", "gameMechanicsId", "gameName", "rewardId"),
                ),
                "fields": {
                    "title": text_trace("GameMechanicTable", mechanic_id, "gameName", row.get("gameName")),
                    "text": text_trace("GameMechanicTable", mechanic_id, "desc", row.get("desc")),
                },
            } if desc else None,
        )
        if title == mechanic_id and not lines:
            continue
        summary_rows: list[dict] = []
        if row.get("difficulty") is not None:
            summary_rows.append({"text": f"Difficulty: {row['difficulty']}"})
        if row.get("costStamina") is not None:
            summary_rows.append({"text": f"Stamina: {row['costStamina']}"})
        write_reference_page(
            f"wiki_mechanic_{mechanic_id}",
            mission_id,
            int(row.get("difficulty") or 0),
            title,
            lines,
            source_debug=source_ref(
                "GameMechanicTable",
                mechanic_id,
                pick_fields(row, "conditionIds", "costStamina", "desc", "difficulty", "gameCategory", "gameMechanicsId", "gameName", "rewardId"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "gameMechanic", game_category, "table_gamemechanictable"],
            search_parts=[mechanic_id, game_category, title, desc],
        )

    print(f"Writing {len(loading_tips)} loading-tip reference pages...")
    for tip_id, row in sorted(loading_tips.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("tipsTitle") or {}).get("id"))) or tip_id
        text = t((row.get("text") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            tip_id,
            text,
            debug={
                **source_ref(
                    "LoadingTipsTable",
                    tip_id,
                    pick_fields(row, "key", "mapTag", "text", "tipsTitle", "typeTag", "unlockMissionId"),
                ),
                "fields": {
                    "title": text_trace("LoadingTipsTable", tip_id, "tipsTitle", row.get("tipsTitle")),
                    "text": text_trace("LoadingTipsTable", tip_id, "text", row.get("text")),
                },
            } if text else None,
        )
        if title == tip_id and not lines:
            continue
        summary_rows: list[dict] = []
        if unlock_mission := str(row.get("unlockMissionId") or ""):
            summary_rows.append({"text": f"Unlock mission: {unlock_mission}"})
        if row.get("typeTag") is not None:
            summary_rows.append({"text": f"Type: {row['typeTag']}"})
        write_reference_page(
            f"wiki_tip_{tip_id}",
            "LoadingTipsTable",
            int(row.get("typeTag") or 0),
            title,
            lines,
            kind="table_loadingtipstable",
            type_key="table_loadingtipstable",
            source_debug=source_ref(
                "LoadingTipsTable",
                tip_id,
                pick_fields(row, "key", "mapTag", "text", "tipsTitle", "typeTag", "unlockMissionId"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "table_loadingtipstable"],
            search_parts=[tip_id, title, text, str(row.get("unlockMissionId") or "")],
        )

    print(f"Writing {len(error_codes)} error-code reference pages...")
    for code, row in sorted(error_codes.items(), key=lambda item: int(item[0]) if re.fullmatch(r"-?\d+", str(item[0])) else 0):
        if not isinstance(row, dict):
            continue
        text = t((row.get("text") or {}).get("id"))
        if not text:
            continue
        write_reference_page(
            f"wiki_error_{code}",
            "ErrorCodeTable",
            int(code) if re.fullmatch(r"-?\d+", str(code)) else 0,
            str(code),
            [{
                "id": str(code),
                "text": text,
                "_debug": {
                    **source_ref("ErrorCodeTable", str(code), pick_fields(row, "text")),
                    "fields": {
                        "text": text_trace("ErrorCodeTable", str(code), "text", row.get("text")),
                    },
                },
            }],
            source_debug=source_ref("ErrorCodeTable", str(code), pick_fields(row, "text")),
            tags=["wiki", "errorCode", "table_errorcodetable"],
            search_parts=[str(code), text],
        )

    achievement_group_names: dict[str, str] = {}
    achievement_group_category_ids: dict[str, str] = {}
    achievement_category_names: dict[str, str] = {}
    for category_id, category_row in sorted(
        achievement_types.items(),
        key=lambda item: (int((item[1] or {}).get("categoryPriority") or 0), item[0]),
    ):
        if not isinstance(category_row, dict):
            continue
        category_name = brace_text(t((category_row.get("categoryName") or {}).get("id"))) or category_id
        achievement_category_names[category_id] = category_name
        for group_row in (category_row.get("achievementGroupData") or []):
            if not isinstance(group_row, dict):
                continue
            group_id = str(group_row.get("groupId") or "")
            if not group_id:
                continue
            group_name = brace_text(t((group_row.get("groupName") or {}).get("id"))) or category_name
            achievement_group_names[group_id] = group_name
            achievement_group_category_ids[group_id] = category_id

    def achievement_group_meta(group_id: str) -> tuple[str, str, str]:
        category_id = achievement_group_category_ids.get(group_id, "")
        category_name = achievement_category_names.get(category_id, category_id)
        group_name = achievement_group_names.get(group_id) or category_name or group_id
        return group_name, category_id, category_name

    print(f"Writing {len(achievements)} achievement reference pages...")
    for achieve_id, row in sorted(
        achievements.items(),
        key=lambda item: (str((item[1] or {}).get("groupId") or ""), int((item[1] or {}).get("order") or 0), item[0]),
    ):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("groupId") or "misc")
        group_name, category_id, category_name = achievement_group_meta(group_id)
        mission_id = f"wiki_achievement_{group_id}"
        extra_mission_names.setdefault(mission_id, group_name)
        title = brace_text(t((row.get("name") or {}).get("id"))) or achieve_id
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        desc = t((row.get("desc") or {}).get("id"))
        append_reference_line(
            lines,
            seen_texts,
            f"{achieve_id}_desc",
            desc,
            hint="Description" if desc else "",
            debug={
                **source_ref("AchievementTable", achieve_id, pick_fields(row, "achieveId", "desc", "groupId", "levelInfos", "name", "order")),
                "fields": {
                    "title": text_trace("AchievementTable", achieve_id, "name", row.get("name")),
                    "text": text_trace("AchievementTable", achieve_id, "desc", row.get("desc")),
                },
            } if desc else None,
        )
        level_infos = row.get("levelInfos") or {}
        for level_key, level_row in sorted(
            ((level_key, level_row) for level_key, level_row in level_infos.items() if isinstance(level_row, dict)),
            key=lambda item: int(item[0]) if re.fullmatch(r"\d+", str(item[0])) else 0,
        ):
            complete_desc = t((level_row.get("completeDesc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{achieve_id}_complete_{level_key}",
                complete_desc,
                hint=f"Level {level_key} completion" if complete_desc else "",
                debug={
                    **source_ref(
                        "AchievementTable.levelInfos",
                        achieve_id,
                        pick_fields(level_row, "achieveLevel", "completeDesc", "conditions"),
                        nodeId=level_key,
                    ),
                    "fields": {
                        "text": text_trace("AchievementTable.levelInfos", achieve_id, "completeDesc", level_row.get("completeDesc")),
                    },
                } if complete_desc else None,
            )
            for idx, condition in enumerate((level_row.get("conditions") or []), start=1):
                if not isinstance(condition, dict):
                    continue
                condition_desc = t((condition.get("desc") or {}).get("id"))
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{achieve_id}_condition_{level_key}_{idx}",
                    condition_desc,
                    hint=f"Level {level_key} condition {idx}" if condition_desc else "",
                    debug={
                        **source_ref(
                            "AchievementTable.levelInfos.conditions",
                            achieve_id,
                            pick_fields(condition, "conditionId", "desc", "progressToCompare"),
                            nodeId=f"{level_key}:{idx}",
                        ),
                        "fields": {
                            "text": text_trace("AchievementTable.levelInfos.conditions", achieve_id, "desc", condition.get("desc")),
                        },
                    } if condition_desc else None,
                )
        if title == achieve_id and not lines:
            continue
        write_reference_page(
            f"wiki_achievement_{achieve_id}",
            mission_id,
            int(row.get("order") or 0),
            title,
            lines,
            source_debug=source_ref(
                "AchievementTable",
                achieve_id,
                pick_fields(row, "achieveId", "desc", "groupId", "levelInfos", "name", "order"),
            ),
            debug_extra={
                "achievementGroup": {
                    "groupId": group_id,
                    "groupName": group_name,
                    "categoryId": category_id,
                    "categoryName": category_name,
                }
            },
            summary_rows=[{"text": f"Levels: {len(level_infos)}"}] if level_infos else None,
            tags=["wiki", "achievement", group_id, "table_achievementtable"],
            search_parts=[achieve_id, group_id, group_name, category_id, category_name, title, desc],
        )

    print(f"Writing {len(sns_chats)} SNS chat reference pages...")
    for chat_id, row in sorted(sns_chats.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or chat_id
        desc = t((row.get("desc") or {}).get("id"))
        tag_label = brace_text(t((row.get("tagLabel") or {}).get("id")))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            f"{chat_id}_desc",
            desc,
            debug={
                **source_ref(
                    "SNSChatTable",
                    chat_id,
                    pick_fields(row, "chatId", "chatType", "desc", "memberRawNum", "name", "owner", "tagLabel", "tagType"),
                ),
                "fields": {
                    "title": text_trace("SNSChatTable", chat_id, "name", row.get("name")),
                    "text": text_trace("SNSChatTable", chat_id, "desc", row.get("desc")),
                    "tag": text_trace("SNSChatTable", chat_id, "tagLabel", row.get("tagLabel")),
                },
            } if desc else None,
        )
        append_reference_line(
            lines,
            seen_texts,
            f"{chat_id}_tag",
            tag_label,
            hint="Tag" if tag_label else "",
            debug={
                **source_ref(
                    "SNSChatTable",
                    chat_id,
                    pick_fields(row, "chatId", "name", "tagLabel", "tagType"),
                ),
                "fields": {
                    "text": text_trace("SNSChatTable", chat_id, "tagLabel", row.get("tagLabel")),
                },
            } if tag_label else None,
        )
        if title == chat_id and not lines:
            continue
        summary_rows: list[dict] = []
        if row.get("chatType") is not None:
            summary_rows.append({"text": f"Chat type: {row['chatType']}"})
        if owner := str(row.get("owner") or ""):
            summary_rows.append({"text": f"Owner: {owner}"})
        if row.get("memberRawNum") is not None:
            summary_rows.append({"text": f"Members: {row['memberRawNum']}"})
        write_reference_page(
            f"wiki_chat_{chat_id}",
            "SNSChatTable",
            int(row.get("chatType") or 0),
            title,
            lines,
            type_key="other",
            source_debug=source_ref(
                "SNSChatTable",
                chat_id,
                pick_fields(row, "chatId", "chatType", "desc", "memberRawNum", "name", "owner", "tagLabel", "tagType"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "snsChat", "table_snschattable"],
            search_parts=[chat_id, title, desc, tag_label, str(row.get("owner") or "")],
        )

    print(f"Writing {len(enemy_ability_desc)} enemy ability reference pages...")
    for ability_id, row in sorted(enemy_ability_desc.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or ability_id
        desc = t((row.get("description") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            ability_id,
            desc,
            debug={
                **source_ref("EnemyAbilityDescTable", ability_id, pick_fields(row, "abilityId", "description", "name")),
                "fields": {
                    "title": text_trace("EnemyAbilityDescTable", ability_id, "name", row.get("name")),
                    "text": text_trace("EnemyAbilityDescTable", ability_id, "description", row.get("description")),
                },
            } if desc else None,
        )
        if title == ability_id and not lines:
            continue
        write_reference_page(
            f"wiki_enemyability_{ability_id}",
            "EnemyAbilityDescTable",
            0,
            title,
            lines,
            source_debug=source_ref("EnemyAbilityDescTable", ability_id, pick_fields(row, "abilityId", "description", "name")),
            tags=["wiki", "enemyAbility", "table_enemyabilitydesctable"],
            search_parts=[ability_id, title, desc],
        )

    training_death_tips = load_optional_table_json(
        STREAMING_TABLE_DIR,
        "TrainingDeathTips.json",
        "StreamingAssets/Table/TrainingDeathTips.json",
    )
    training_type_info = load_optional_table_json(
        STREAMING_TABLE_DIR,
        "TrainingTypeInfoTable.json",
        "StreamingAssets/Table/TrainingTypeInfoTable.json",
    )
    if isinstance(training_death_tips, dict) or isinstance(training_type_info, dict):
        training_death_tips = training_death_tips if isinstance(training_death_tips, dict) else {}
        training_type_info = training_type_info if isinstance(training_type_info, dict) else {}
        training_keys = sorted(
            set(training_death_tips) | set(training_type_info),
            key=lambda key: (
                int((training_type_info.get(key) or {}).get("priority") or 9999)
                if isinstance(training_type_info.get(key), dict)
                else 9999,
                str(key),
            ),
        )
        for row_index, row_id in enumerate(training_keys, start=1):
            tip_row = training_death_tips.get(row_id)
            info_row = training_type_info.get(row_id)
            tip_row = tip_row if isinstance(tip_row, dict) else {}
            info_row = info_row if isinstance(info_row, dict) else {}

            title = (
                brace_text(t((info_row.get("progressBarLabel") or {}).get("id")))
                or row_id
            )
            lines: list[dict] = []
            seen_texts: set[tuple[str, str, str]] = set()

            tip_contents = tip_row.get("tipContents") or []
            if isinstance(tip_contents, list):
                for idx, tip_ref in enumerate(tip_contents, start=1):
                    text = t((tip_ref or {}).get("id"))
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_tip_{idx}",
                        text,
                        hint=f"Tip {idx}",
                        debug={
                            **source_ref(
                                "TrainingDeathTips",
                                row_id,
                                {"path": f"$.tipContents[{idx-1}]"},
                                nodeId=idx,
                                tableSource="StreamingAssets/Table",
                            ),
                            "fields": {
                                "text": text_trace(
                                    "TrainingDeathTips",
                                    row_id,
                                    f"$.tipContents[{idx-1}]",
                                    tip_ref,
                                ),
                            },
                        } if text else None,
                    )

            label_text = brace_text(t((info_row.get("progressBarLabel") or {}).get("id")))
            if not lines and label_text:
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_label",
                    label_text,
                    hint="Type Label",
                    debug={
                        **source_ref(
                            "TrainingTypeInfoTable",
                            row_id,
                            {"path": "$.progressBarLabel"},
                            tableSource="StreamingAssets/Table",
                        ),
                        "fields": {
                            "text": text_trace(
                                "TrainingTypeInfoTable",
                                row_id,
                                "$.progressBarLabel",
                                info_row.get("progressBarLabel"),
                            ),
                        },
                    },
                )

            if not title and not lines:
                continue

            summary_rows = [
                {"text": "Table: TrainingDeathTips / TrainingTypeInfoTable"},
                {"text": f"Row: {row_id}"},
            ]
            if label_text and label_text != title:
                summary_rows.append({"text": f"Label: {label_text}"})
            if info_row.get("priority") is not None:
                summary_rows.append({"text": f"Priority: {info_row['priority']}"})
            if info_row.get("trainingThresholdFactor") is not None:
                summary_rows.append({"text": f"Threshold Factor: {info_row['trainingThresholdFactor']}"})

            source_debug = source_ref(
                "TrainingDeathTips",
                row_id,
                {"table": "TrainingDeathTips / TrainingTypeInfoTable"},
                tableSource="StreamingAssets/Table",
            )
            debug_extra = {
                "mergedSources": [
                    source_ref(
                        "TrainingDeathTips",
                        row_id,
                        pick_fields(tip_row, "tipContents"),
                        tableSource="StreamingAssets/Table",
                    ),
                    source_ref(
                        "TrainingTypeInfoTable",
                        row_id,
                        pick_fields(info_row, "priority", "progressBarLabel", "trainingThresholdFactor", "trainingType"),
                        tableSource="StreamingAssets/Table",
                    ),
                ],
            }
            write_reference_page(
                f"wiki_trainingtip_{collection_slug(row_id)}",
                "TrainingDeathTips",
                int(info_row.get("priority") or row_index),
                title,
                lines,
                kind="table_trainingdeathtips",
                type_key="other",
                source_debug=source_debug,
                summary_rows=summary_rows,
                tags=[
                    "wiki",
                    "table_trainingdeathtips",
                    "table_trainingtypeinfotable",
                    "group_training_death_tips",
                ],
                search_parts=[
                    "TrainingDeathTips",
                    "TrainingTypeInfoTable",
                    row_id,
                    title,
                    label_text,
                ],
                debug_extra=debug_extra,
            )

    collection_omit_tables = {
        "AchievementTable.json",
        "AchievementTypeTable.json",
        "AIBarkText.json",
        "BlocDataTable.json",
        "CheckInRewardTable.json",
        "DialogOptionTable.json",
        "DialogSummaryTable.json",
        "DialogTextTable.json",
        "GamepadImplicitSettingItemTable.json",
        "GamepadSettingItemTable.json",
        "GamepadSettingOptionTable.json",
        "GameSystemConfigTable.json",
        "GiftpackCashShopIdTable.json",
        I18N_HOTFIX_TABLE,
        "MissionExtraInfoTable.json",
        "MoneyConfigTable.json",
        "MoneyConsumeTable.json",
        "MoneyExchangeTable.json",
        "MoneyGainTable.json",
        "MoneyRecordTable.json",
        "PrtsCategory.json",
        "PrtsDocument.json",
        "PrtsInvestigate.json",
        "PrtsInvestigateCategory.json",
        "PrtsMultimedia.json",
        "PrtsRecord.json",
        "QualitySubSettingOptionTable.json",
        "QualitySubSettingTable.json",
        "ReportTable.json",
        "SceneCollectableItemTable.json",
        "ShareChannelTable.json",
        "SNSDialogTopicTable.json",
        "SettingTabTable.json",
        "TowerDefenseGroupTable.json",
        "TrainingDeathTips.json",
        "TrainingTypeInfoTable.json",
        "WeaponBasicTable.json",
    }
    collection_omit_prefixes = (
        "Attribute",
        "CompositeAttributeShow",
        "SocialBuilding",
    )
    collection_skip_tables = {
        "DialogTextTable.json",
        "SNSDialogTable.json",
        "SNSDialogOptionTable.json",
        "RadioTable.json",
        "RemoteCommonTable.json",
        "EnvTalkTable.json",
        "ResponsiveDialog.json",
        "MailSenderTable.json",
        "MailTemplateTable.json",
        "PrtsAllItem.json",
        "PrtsFirstLv.json",
        "PrtsPage.json",
        "PrtsNote.json",
        "WikiCategoryTable.json",
        "WikiGroupTable.json",
        "WikiEntryDataTable.json",
        "WikiTutorialPageTable.json",
        "WikiTutorialPageByEntryTable.json",
        "WikiCraftJumpTable.json",
        "WikiDefaultCraftTable.json",
        "MissionAreaTable.json",
        "NpcProxyTable.json",
        "NpcProxyExDataTable.json",
        "AtmosphericNpcClusterDataTable.json",
        "SkillPatchTable.json",
        "GameMechanicTable.json",
        "DungeonCharTutorialStepTable.json",
        "LoadingTipsTable.json",
        "ErrorCodeTable.json",
        "SNSChatTable.json",
        "EnemyAbilityDescTable.json",
        "TextTable.json",
    }
    collection_preloaded_tables: dict[str, dict] = {
        "AchievementTable.json": achievements,
        "AIBarkText.json": ai_bark_text,
        "AudioDialog.json": audio_dialog,
        "CharGrowthTable.json": char_growth,
        "CharacterTable.json": character_rows,
        "DialogOptionTable.json": dlg_opts,
        "DungeonTable.json": dungeons,
        "EnemyDisplayInfoTable.json": enemy_display_info,
        "EnemyTemplateDisplayInfoTable.json": enemy_template_display,
        "ItemTable.json": item_rows,
        "MissionExtraInfoTable.json": mission_extra_info,
        "NpcTable.json": npc_rows,
        "NpcTemplateGroupTable.json": npc_templates,
        "ResponsiveDialog.json": responsive_dialog,
        "RichContentTable.json": rich_content,
        "WeaponBasicTable.json": weapon_basic,
    }
    collection_table_cache: dict[tuple[str, str], dict] = {
        ("streaming", table_name): payload
        for table_name, payload in collection_preloaded_tables.items()
    }


    def collection_is_redundant_support_table(table_name: str) -> bool:
        tokens = set(collection_table_name_tokens(table_name))
        return bool({"tag", "title", "label"} & tokens)

    def collection_table_payload(table_source: str, table_name: str) -> dict:
        cache_key = (table_source, table_name)
        if cache_key in collection_table_cache:
            return collection_table_cache[cache_key]
        table_dir = STREAMING_TABLE_DIR if table_source == "streaming" else PERSISTENT_TABLE_DIR
        payload = load_optional_table_json(
            table_dir,
            table_name,
            f"{collection_source_label(table_source)}/{table_name}",
        )
        collection_table_cache[cache_key] = payload if isinstance(payload, dict) else {}
        return collection_table_cache[cache_key]


    def write_raw_reference_bundle() -> dict:
        reference_dir.mkdir(parents=True, exist_ok=True)
        generated = int(time.time())
        table_index: list[dict] = []
        base_reference_rows: dict[str, list[dict]] = {}
        base_reference_files: dict[str, str] = {}
        total_rows = 0
        total_texts = 0
        total_bytes = 0

        for table_source, table_dir in (
            ("streaming", STREAMING_TABLE_DIR),
            ("persistent", PERSISTENT_TABLE_DIR),
        ):
            if not table_dir.exists():
                continue
            source_out_dir = reference_dir / table_source
            source_out_dir.mkdir(parents=True, exist_ok=True)

            for table_path in sorted(table_dir.glob("*.json")):
                table_name = table_path.name
                if table_name.startswith("I18nTextTable_") or table_name == I18N_HOTFIX_TABLE:
                    continue
                payload = collection_table_payload(table_source, table_name)
                if not isinstance(payload, dict) or not payload:
                    continue

                row_payloads: list[dict] = []
                table_texts = 0
                for row_index, (row_id, row) in enumerate(
                    sorted(payload.items(), key=lambda item: str(item[0])),
                    start=1,
                ):
                    row_key = str(row_id)
                    text_nodes = collect_reference_text_nodes(
                        table_name,
                        row_key,
                        row,
                        preferred_source=table_source,
                    )
                    if not text_nodes:
                        continue

                    texts = reference_row_texts(text_nodes)
                    table_texts += len(texts)
                    bucket = collection_bucket(
                        table_name,
                        row_key,
                        row if isinstance(row, dict) else None,
                    )
                    row_payload = {
                        "id": row_key,
                        "title": collection_row_title(
                            table_name,
                            row_key,
                            text_nodes,
                            preferred_source=table_source,
                        ),
                        "bucket": bucket,
                        "order": collection_scene_value(
                            row if isinstance(row, dict) else None,
                            row_index,
                        ),
                        "texts": texts,
                    }
                    row_payloads.append(row_payload)

                if not row_payloads:
                    continue

                rel_file = f"{table_source}/{table_path.stem}.json"
                out_payload = {
                    "generated": generated,
                    "language": language_code,
                    "source": collection_source_label(table_source),
                    "table": table_name,
                    "label": collection_display_name(table_path.stem),
                    "rows": row_payloads,
                }
                storage = "full"
                base_file = ""
                overlay_rows = 0
                removed_rows = 0

                if table_source == "persistent" and table_name in base_reference_rows:
                    base_rows = base_reference_rows.get(table_name) or []
                    base_file = base_reference_files.get(table_name) or ""
                    base_by_id = {str(row.get("id") or ""): row for row in base_rows}
                    current_by_id = {str(row.get("id") or ""): row for row in row_payloads}
                    removed_ids = sorted(row_id for row_id in base_by_id if row_id not in current_by_id)
                    changed_rows = [
                        row for row in row_payloads
                        if base_by_id.get(str(row.get("id") or "")) != row
                    ]
                    overlay_rows = len(changed_rows)
                    removed_rows = len(removed_ids)
                    if not changed_rows and not removed_ids and base_file:
                        rel_file = base_file
                        storage = "shared"
                        file_bytes = 0
                    else:
                        rel_file = f"overlays/{table_source}/{table_path.stem}.json"
                        out_payload = {
                            "generated": generated,
                            "language": language_code,
                            "source": collection_source_label(table_source),
                            "table": table_name,
                            "label": collection_display_name(table_path.stem),
                            "baseFile": base_file,
                            "rowOrder": [str(row.get("id") or "") for row in row_payloads],
                            "removedRows": removed_ids,
                            "rows": changed_rows,
                        }
                        out_path = write_reference_payload(rel_file, out_payload)
                        file_bytes = out_path.stat().st_size
                        storage = "overlay"
                else:
                    out_path = write_reference_payload(rel_file, out_payload)
                    file_bytes = out_path.stat().st_size
                    if table_source == "streaming":
                        base_reference_rows[table_name] = row_payloads
                        base_reference_files[table_name] = rel_file

                total_bytes += file_bytes
                total_rows += len(row_payloads)
                total_texts += table_texts
                table_row = {
                    "source": table_source,
                    "sourceLabel": collection_source_label(table_source),
                    "table": table_name,
                    "label": collection_display_name(table_path.stem),
                    "file": rel_file,
                    "rows": len(row_payloads),
                    "texts": table_texts,
                    "bytes": file_bytes,
                    "storage": storage,
                }
                if base_file:
                    table_row["baseFile"] = base_file
                if overlay_rows:
                    table_row["overlayRows"] = overlay_rows
                if removed_rows:
                    table_row["removedRows"] = removed_rows
                table_index.append(table_row)

        table_index.sort(key=lambda row: (row["source"], row["label"], row["table"]))
        index_payload = {
            "generated": generated,
            "language": language_code,
            "tables": table_index,
            "stats": {
                "tables": len(table_index),
                "rows": total_rows,
                "texts": total_texts,
                "bytes": total_bytes,
            },
        }
        write_reference_payload("index.json", index_payload)

        print(
            f"Raw reference bundle written: {len(table_index)} tables; "
            f"{total_rows} rows; {total_texts} localized text node(s)"
        )
        return index_payload["stats"]

    ai_bark_reference_cache: dict[str, dict[str, dict[str, str]]] = {}

    def collection_ai_bark_refs(table_source: str) -> dict[str, dict[str, str]]:
        if table_source in ai_bark_reference_cache:
            return ai_bark_reference_cache[table_source]

        refs: dict[str, dict[str, str]] = {}
        responsive_payload = collection_table_payload(table_source, "ResponsiveDialog.json")
        for set_id, top_row in sorted(responsive_payload.items(), key=lambda item: str(item[0])):
            if not isinstance(top_row, dict):
                continue
            speakers = top_row.get("speakers") or {}
            if not isinstance(speakers, dict):
                continue
            for speaker_id, speaker_row in sorted(speakers.items()):
                if not isinstance(speaker_row, dict):
                    continue
                actor_id = speaker_actor_id(str(speaker_id))
                speaker_name = speaker_display_name(str(speaker_id)) or actor_id or str(speaker_id)
                triggers = speaker_row.get("triggers") or {}
                if not isinstance(triggers, dict):
                    continue
                for trigger_key, trigger_row in sorted(triggers.items()):
                    if not isinstance(trigger_row, dict):
                        continue
                    for response_id in (trigger_row.get("response") or []):
                        row_id = str(response_id)
                        current = refs.get(row_id)
                        if current and current.get("source") == "ResponsiveDialog":
                            continue
                        refs[row_id] = {
                            "actorId": actor_id,
                            "speakerId": str(speaker_id),
                            "speakerName": speaker_name,
                            "source": "ResponsiveDialog",
                            "setId": str(set_id),
                            "triggerKey": str(trigger_key),
                        }

        audio_payload = collection_table_payload(table_source, "AudioDialog.json")
        for row_id, audio_row in sorted(audio_payload.items(), key=lambda item: str(item[0])):
            if row_id in refs:
                continue
            if not isinstance(audio_row, dict):
                continue
            speaker_id = str(audio_row.get("speakerChannel") or "")
            actor_id = speaker_actor_id(speaker_id)
            if not actor_id:
                continue
            refs[str(row_id)] = {
                "actorId": actor_id,
                "speakerId": speaker_id,
                "speakerName": speaker_display_name(speaker_id) or actor_id or speaker_id,
                "source": "AudioDialog",
                "audioPath": str(audio_row.get("path") or ""),
            }

        ai_bark_reference_cache[table_source] = refs
        return refs

    def rich_content_row_for_source(content_id: str, table_source: str) -> dict:
        content_key = str(content_id or "").strip()
        if not content_key:
            return {}
        payload = collection_table_payload(table_source, "RichContentTable.json")
        row = payload.get(content_key) if isinstance(payload, dict) else None
        if not isinstance(row, dict) and table_source != "streaming":
            row = rich_content.get(content_key)
        return row if isinstance(row, dict) else {}

    def rich_content_title_text_for_source(content_id: str, table_source: str) -> str:
        row = rich_content_row_for_source(content_id, table_source)
        return t((row.get("title") or {}).get("id"), preferred_source=table_source) if row else ""

    def rich_content_lines_for_source(content_id: str, table_source: str) -> list[dict]:
        row = rich_content_row_for_source(content_id, table_source)
        if not row:
            return []
        out: list[dict] = []
        for idx, item in enumerate(row.get("contentList") or [], start=1):
            if not isinstance(item, dict):
                continue
            content = item.get("content") or {}
            text = t(content.get("id"), preferred_source=table_source)
            out.append({
                "id": f"{content_id}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        str(content_id),
                        pick_fields(item, "content"),
                        nodeId=idx,
                        tableSource=collection_source_label(table_source),
                    ),
                    "fields": {
                        "text": text_trace(
                            "RichContentTable",
                            str(content_id),
                            "content",
                            content,
                            preferred_source=table_source,
                        ),
                    },
                },
            })
        return out

    def reading_content_refs(table_name: str, row_id: str, row: dict | None, *, table_source: str) -> list[dict]:
        if not isinstance(row, dict):
            return []
        refs: list[dict] = []
        if table_name == "PrtsReading.json":
            items = row.get("list") or {}
            if not isinstance(items, dict):
                return []
            sorted_items = sorted(
                ((node_id, node) for node_id, node in items.items() if isinstance(node, dict)),
                key=lambda item: (int((item[1] or {}).get("order") or 0), str(item[0])),
            )
            for node_id, node in sorted_items:
                content_id = str(node.get("contentId") or "").strip()
                if not content_id:
                    continue
                name = brace_text(t((node.get("name") or {}).get("id"), preferred_source=table_source))
                subtitle = brace_text(t((node.get("subtitle") or {}).get("id"), preferred_source=table_source))
                refs.append({
                    "contentId": content_id,
                    "label": name or subtitle or content_id,
                    "subtitle": subtitle,
                    "path": f"$.list.{node_id}.contentId",
                    "nodeId": node_id,
                    "source": pick_fields(node, "contentId", "name", "order", "subtitle", "uniqId"),
                })
        elif table_name == "ReadingPopUpTable.json":
            content_id = str(row.get("contentId") or "").strip()
            if content_id:
                refs.append({
                    "contentId": content_id,
                    "label": brace_text(t((row.get("title") or {}).get("id"), preferred_source=table_source)) or content_id,
                    "path": "$.contentId",
                    "nodeId": 1,
                    "source": pick_fields(row, "bgType", "contentId", "iconType", "id", "title"),
                })
        return refs

    def append_linked_reading_content_lines(
        table_name: str,
        row_id: str,
        row: dict | None,
        *,
        table_source: str,
        lines: list[dict],
        seen_texts: set[tuple[str, str, str]],
    ) -> tuple[list[dict], str]:
        linked_refs: list[dict] = []
        preview_text = ""
        for ref_index, ref in enumerate(
            reading_content_refs(table_name, row_id, row, table_source=table_source),
            start=1,
        ):
            content_id = str(ref.get("contentId") or "").strip()
            if not content_id:
                continue
            label = str(ref.get("label") or content_id)
            linked_from = source_ref(
                table_name.removesuffix(".json"),
                row_id,
                {
                    "path": ref.get("path") or "$.contentId",
                    "contentId": content_id,
                    **(ref.get("source") or {}),
                },
                nodeId=ref.get("nodeId"),
                tableSource=collection_source_label(table_source),
            )

            rich_title = rich_content_title_text_for_source(content_id, table_source)
            rich_lines = rich_content_lines_for_source(content_id, table_source)
            if rich_title and rich_title != label:
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_linked_{ref_index}_title",
                    rich_title,
                    hint=f"{label} / Title",
                    debug={
                        **source_ref(
                            "RichContentTable",
                            content_id,
                            {"title": (rich_content_row_for_source(content_id, table_source).get("title") or {})},
                            tableSource=collection_source_label(table_source),
                        ),
                        "linkedFrom": linked_from,
                        "fields": {
                            "text": text_trace(
                                "RichContentTable",
                                content_id,
                                "title",
                                (rich_content_row_for_source(content_id, table_source).get("title") or {}),
                                preferred_source=table_source,
                            ),
                        },
                    },
                )
                preview_text = preview_text or rich_title

            if rich_lines:
                linked_refs.append({
                    "contentId": content_id,
                    "source": "RichContentTable",
                    "lineCount": len(rich_lines),
                    "label": label,
                })
                for content_index, content_line in enumerate(rich_lines, start=1):
                    text = str(content_line.get("text") or "")
                    debug = dict(content_line.get("_debug") or {})
                    debug["linkedFrom"] = linked_from
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_linked_{ref_index}_{content_index}",
                        text,
                        hint=rich_title or label,
                        debug=debug,
                    )
                    if text:
                        preview_text = preview_text or text
                continue

            radio_row = radio_row_lookup.get(content_id)
            if radio_row:
                radio_lines = [line for line in (radio_row.get("lines") or []) if isinstance(line, dict)]
                linked_refs.append({
                    "contentId": content_id,
                    "source": "RadioTable",
                    "lineCount": len(radio_lines),
                    "label": label,
                })
                for content_index, radio_line in enumerate(radio_lines, start=1):
                    text = str(radio_line.get("text") or "")
                    debug = dict(radio_line.get("_debug") or {})
                    debug["linkedFrom"] = linked_from
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_linked_{ref_index}_{content_index}",
                        text,
                        hint=label,
                        actor=str(radio_line.get("actor") or ""),
                        aid=str(radio_line.get("aid") or ""),
                        debug=debug,
                    )
                    if text:
                        preview_text = preview_text or text

        return linked_refs, preview_text

    def write_generic_collection_pages(
        table_source: str,
        *,
        dedupe_against_streaming: bool = False,
    ) -> tuple[int, int]:
        table_dir = STREAMING_TABLE_DIR if table_source == "streaming" else PERSISTENT_TABLE_DIR
        if not table_dir.exists():
            return (0, 0)
        generic_collection_paths = [
            path
            for path in sorted(table_dir.glob("*.json"))
            if not path.name.startswith("I18nTextTable_")
            and path.name not in collection_omit_tables
            and not path.name.startswith(collection_omit_prefixes)
            and not collection_is_redundant_support_table(path.name)
            and (table_source != "streaming" or path.name not in collection_skip_tables)
        ]
        label = "generic" if table_source == "streaming" else "supplemental persistent"
        print(
            f"Writing {label} collection pages from {len(generic_collection_paths)} tables..."
        )
        generic_collection_pages = 0
        generic_collection_tables = 0
        for table_path in generic_collection_paths:
            table_name = table_path.name
            payload = collection_table_payload(table_source, table_name)
            if not isinstance(payload, dict) or not payload:
                continue

            table_pages = 0
            table_label = collection_display_name(table_path.stem)
            streaming_payload = (
                collection_table_payload("streaming", table_name)
                if dedupe_against_streaming
                else {}
            )
            for row_index, (row_id, row) in enumerate(sorted(payload.items(), key=lambda item: str(item[0])), start=1):
                row_key = str(row_id)
                if table_name == "RichContentTable.json" and row_key in prts_content_ids:
                    continue
                forced_kind = None
                text_nodes = collect_reference_text_nodes(
                    table_name,
                    row_key,
                    row,
                    preferred_source=table_source,
                )
                if not text_nodes:
                    continue
                if (
                    table_name == "RichContentTable.json"
                    and text_sequence_fingerprint(text_nodes) in wiki_text_fingerprints
                ):
                    continue

                variant = False
                if dedupe_against_streaming:
                    streaming_row = streaming_payload.get(row_key) if isinstance(streaming_payload, dict) else None
                    if streaming_row is not None:
                        streaming_nodes = collect_reference_text_nodes(
                            table_name,
                            row_key,
                            streaming_row,
                            preferred_source="streaming",
                        )
                        if collection_text_fingerprint(streaming_nodes) == collection_text_fingerprint(text_nodes):
                            continue
                        variant = bool(streaming_nodes)

                bucket = collection_bucket(table_name, row_key, row if isinstance(row, dict) else None)
                bucket_token = collection_bucket_token(bucket)
                story_ref = collection_reading_story_ref(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                ) or collection_story_ref_from_bucket(bucket)
                if story_ref:
                    mission_id, forced_scene_value, forced_type_key = story_ref
                    if not forced_scene_value:
                        forced_scene_value = collection_scene_value(row if isinstance(row, dict) else None, row_index)
                    extra_mission_names.setdefault(mission_id, collection_display_name(mission_id))
                else:
                    mission_id = (
                        f"wiki_collection_{collection_slug(table_source)}_"
                        f"{collection_slug(table_path.stem)}_{bucket_token}"
                    )
                    forced_scene_value = collection_scene_value(row if isinstance(row, dict) else None, row_index)
                    forced_type_key = forced_kind

                title = collection_row_title(
                    table_name,
                    row_key,
                    text_nodes,
                    preferred_source=table_source,
                )
                lines: list[dict] = []
                seen_texts: set[tuple[str, str, str]] = set()
                for node_index, node in enumerate(text_nodes, start=1):
                    hint = node.get("hint") or collection_display_name(node.get("field") or "text")
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_key}_{node_index}",
                        node.get("text") or "",
                        hint=hint,
                        debug={
                            **source_ref(
                                table_path.stem,
                                row_key,
                                {
                                    "path": node.get("path") or "$",
                                },
                                nodeId=node_index,
                                tableSource=collection_source_label(table_source),
                            ),
                            "fields": {
                                "text": text_trace(
                                    table_path.stem,
                                    row_key,
                                    str(node.get("path") or "$"),
                                    node.get("raw"),
                                    preferred_source=table_source,
                                ),
                            },
                        },
                    )
                linked_content_refs, linked_preview_text = append_linked_reading_content_lines(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                    table_source=table_source,
                    lines=lines,
                    seen_texts=seen_texts,
                )
                if not lines:
                    continue

                out_key = (
                    f"wiki_collection_{collection_slug(table_source)}_"
                    f"{collection_slug(table_path.stem)}_{row_key}"
                )
                summary_rows = collection_summary_rows(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                    bucket,
                    table_source=table_source,
                    variant=variant,
                )
                debug_extra = {}
                if linked_content_refs:
                    total_linked_lines = sum(int(ref.get("lineCount") or 0) for ref in linked_content_refs)
                    summary_rows.append({
                        "text": f"Linked content: {len(linked_content_refs)} ref(s), {total_linked_lines} line(s)",
                    })
                    debug_extra["linkedContent"] = linked_content_refs
                search_parts = [
                    table_label,
                    row_key,
                    bucket,
                    table_source,
                ]
                if isinstance(row, dict):
                    for field in ("groupId", "categoryId", "type", "gameCategory", "charId", "profession", "weaponType", "owner"):
                        value = row.get(field)
                        if is_present(value):
                            search_parts.append(str(value))
                page_tags = collection_tags(
                    table_name,
                    row_key,
                    bucket,
                    row if isinstance(row, dict) else None,
                    table_source=table_source,
                    variant=variant,
                )
                write_reference_page(
                    out_key,
                    mission_id,
                    forced_scene_value,
                    title,
                    lines,
                    kind=forced_kind,
                    type_key=forced_type_key,
                    source_debug=source_ref(
                        table_path.stem,
                        row_key,
                        {"table": table_name},
                        tableSource=collection_source_label(table_source),
                        variantOf="StreamingAssets/Table" if variant else None,
                    ),
                    summary_rows=summary_rows,
                    tags=page_tags,
                    search_parts=search_parts,
                    preview_text=linked_preview_text or None,
                    debug_extra=debug_extra or None,
                )
                table_pages += 1
                generic_collection_pages += 1

            if table_pages:
                generic_collection_tables += 1
                print(f"  collection {table_source} {table_name}: {table_pages} pages")

        return generic_collection_pages, generic_collection_tables

    if include_reference_in_story_index:
        generic_collection_pages, generic_collection_tables = write_generic_collection_pages("streaming")
        persistent_collection_pages, persistent_collection_tables = write_generic_collection_pages(
            "persistent",
            dedupe_against_streaming=True,
        )

        print(
            f"Generic collection pages written: {generic_collection_pages + persistent_collection_pages} "
            f"across {generic_collection_tables + persistent_collection_tables} tables"
        )
    else:
        print("Skipping generic table collection pages for lean story profile.")

    reference_stats: dict = {}
    if write_reference:
        reference_stats = write_raw_reference_bundle()

    print(f"Writing {len(mail_templates)} mail conversations...")
    for template_id, row in sorted(mail_templates.items()):
        if not isinstance(row, dict):
            continue
        sender_id = str(row.get("senderId") or "system")
        sender_row = mail_senders.get(sender_id) if isinstance(mail_senders.get(sender_id), dict) else {}
        sender_name = (
            brace_text(t((sender_row.get("senderName") or {}).get("id")))
            or speaker_display_name(sender_id)
            or sender_id
        )
        title = brace_text(t((row.get("title") or {}).get("id"))) or template_id
        body = t((row.get("mailContent") or {}).get("id"))
        out_key = f"mail_{template_id}"
        if sender_name:
            extra_mission_names[sender_id] = sender_name
        summary: list[dict] = []
        if row.get("rewardId"):
            summary.append({"text": f"Reward: {row['rewardId']}"})
        if row.get("duration") is not None:
            summary.append({"text": f"Duration: {row['duration']}"})
        if row.get("type") is not None:
            summary.append({"text": f"Type: {row['type']}"})
        lines = [{
            "id": template_id,
            "aid": sender_id,
            "actor": sender_name,
            "text": body,
            "_debug": {
                **source_ref(
                    "MailTemplateTable",
                    template_id,
                    pick_fields(row, "duration", "mailContent", "rewardId", "senderId", "templateId", "title", "type"),
                ),
                "fields": {
                    "title": text_trace("MailTemplateTable", template_id, "title", row.get("title")),
                    "text": text_trace("MailTemplateTable", template_id, "mailContent", row.get("mailContent")),
                },
            },
        }]
        payload = {
            "key": out_key,
            "kind": "mail",
            "mission": sender_id,
            "scene": 0,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "MailTemplateTable",
                    template_id,
                    pick_fields(row, "duration", "mailContent", "rewardId", "senderId", "templateId", "title", "type"),
                ),
            },
        }
        if summary:
            payload["summary"] = summary
        if sender_row:
            payload["_debug"]["sender"] = source_ref(
                "MailSenderTable",
                sender_id,
                pick_fields(sender_row, "id", "senderIcon", "senderName"),
            )
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": "mail",
            "m": sender_id,
            "s": 0,
            "t": "mail",
            "a": 0,
            "title": title,
            "c": [sender_id] if sender_id else [],
            "n": len(lines),
            "p": preview(body or title),
            "tags": ["mail"],
        }
        search_text = " ".join(part for part in [
            template_id,
            sender_id,
            sender_name,
            title,
            body,
            str(row.get("rewardId") or ""),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    embedded_prts_notes_by_entry: dict[str, list[dict]] = defaultdict(list)
    embedded_prts_note_ids: set[str] = set()
    for note_id, note_meta in sorted(prts_note_metadata.items()):
        note_key = str(note_id or "").strip()
        if not note_key.startswith("hint_research"):
            continue
        note_row = prts_notes.get(note_key)
        if not isinstance(note_row, dict):
            continue
        linked_entry_ids = [
            str(value)
            for value in (note_meta.get("collectionIds") or [])
            if str(value)
        ]
        if not linked_entry_ids:
            continue
        note_text = t((note_row.get("desc") or {}).get("id"))
        if not note_text:
            continue
        embedded_prts_note_ids.add(note_key)
        embedded_note = {
            "id": note_key,
            "title": str(note_meta.get("title") or note_key),
            "text": note_text,
            "researchId": str(note_meta.get("researchId") or ""),
            "index": int(note_meta.get("index") or 0),
        }
        for linked_entry_id in linked_entry_ids:
            linked_key = str(linked_entry_id or "").strip()
            if not linked_key:
                continue
            embedded_prts_notes_by_entry[linked_key].append(dict(embedded_note))

    def resolve_prts_payload(content_id: str) -> tuple[list[dict], list[dict], dict]:
        lines = rich_content_lines(content_id)
        summary_rows: list[dict] = []
        debug_extra: dict = {}
        if rich_row := rich_content.get(content_id):
            rich_title = rich_content_title_text(content_id)
            if rich_title:
                summary_rows.append({"text": f"Content: {rich_title}"})
            debug_extra["content"] = source_ref(
                "RichContentTable",
                content_id,
                pick_fields(rich_row, "title", "contentList"),
            )
        elif radio_row := radio_row_lookup.get(content_id):
            lines = list(radio_row.get("lines") or [])
            summary_rows.append({"text": f"Linked radio: {content_id}"})
        else:
            summary_rows.append({"text": f"Content ref: {content_id}"})
        return lines, summary_rows, debug_extra


    def prts_row_attachment_aliases(
        row_id: str,
        content_id: str,
        first_lv_id: str,
        first_lv_row: dict,
    ) -> set[str]:
        aliases: set[str] = set()
        for value in (row_id, content_id, first_lv_id, first_lv_row.get("icon")):
            aliases.update(prts_attachment_aliases(str(value or "")))
        return aliases

    prts_attachment_story_refs: dict[str, tuple[str, int, str]] = {}
    for sns_id, sns_entry in sns_groups.items():
        match = SNS_RE.match(sns_id)
        if not match:
            continue
        mission_id = match.group(1)
        scene_value = int(match.group(2))
        type_key, _act = parse_mission(mission_id)
        if type_key not in MISSION_STORY_TYPES:
            continue
        story_ref = (mission_id, scene_value, type_key)
        cdata = sns_entry.get("dialogContentData") or {}
        if not isinstance(cdata, dict):
            continue
        for node in cdata.values():
            if not isinstance(node, dict):
                continue
            values: list[str] = []
            content_param = node.get("contentParam")
            if isinstance(content_param, list):
                values.extend(str(value) for value in content_param if str(value))
            elif is_present(content_param):
                values.append(str(content_param))
            content_params = node.get("contentParams")
            if isinstance(content_params, list):
                values.extend(str(value) for value in content_params if str(value))
            elif is_present(content_params):
                values.append(str(content_params))
            for value in values:
                for alias in prts_attachment_aliases(value):
                    prts_attachment_story_refs.setdefault(alias, story_ref)

    standalone_prts_note_count = sum(
        1
        for note_id, row in prts_notes.items()
        if isinstance(row, dict) and str(note_id) not in embedded_prts_note_ids
    )
    print(f"Writing {len(prts_all_items) + standalone_prts_note_count} PRTS entries...")
    for row_id, row in sorted(prts_all_items.items(), key=lambda item: (
        str(item[1].get("firstLvId") or ""),
        int(item[1].get("order") or 0),
        item[0],
    )):
        if not isinstance(row, dict):
            continue
        content_id = str(row.get("contentId") or "")
        first_lv_id = str(row.get("firstLvId") or row.get("type") or "prts")
        first_lv_row = prts_first_lv.get(first_lv_id) if isinstance(prts_first_lv.get(first_lv_id), dict) else {}
        category_id = str(first_lv_row.get("categoryId") or row.get("type") or "prts")
        page_row = prts_page.get(category_id) if isinstance(prts_page.get(category_id), dict) else {}
        mission_label = brace_text(t((first_lv_row.get("name") or {}).get("id"))) or first_lv_id
        if mission_label:
            extra_mission_names[first_lv_id] = mission_label
        story_ref = collection_story_ref_from_identifiers(
            content_id,
            row_id,
            first_lv_id,
        )
        if not story_ref:
            for alias in prts_row_attachment_aliases(row_id, content_id, first_lv_id, first_lv_row):
                story_ref = prts_attachment_story_refs.get(alias)
                if story_ref:
                    break
        if not story_ref:
            story_ref = collection_map_ref_from_identifiers(content_id, row_id, first_lv_id)
        entry_mission_id = first_lv_id
        entry_scene = int(row.get("order") or 0)
        entry_type = "prts"
        if story_ref:
            entry_mission_id, story_scene, entry_type = story_ref
            entry_scene = story_scene or entry_scene
            extra_mission_names.setdefault(entry_mission_id, collection_display_name(entry_mission_id))
        title = (
            brace_text(t((row.get("name") or {}).get("id")))
            or rich_content_title_text(content_id)
            or row_id
        )
        subtitle = brace_text(t((first_lv_row.get("subName") or {}).get("id")))
        desc = t((row.get("desc") or {}).get("id"))
        lines, summary_rows, debug_extra = resolve_prts_payload(content_id)
        page_label = brace_text(t((page_row.get("name") or {}).get("id"))) or category_id
        if page_label:
            summary_rows.insert(0, {"text": f"Page: {page_label}"})
        if subtitle:
            summary_rows.append({"text": f"Section: {subtitle}"})
        if desc:
            summary_rows.append({"text": desc})
        linked_research_rows = prts_investigate_metadata_by_unlock_prts.get(str(row_id)) or []
        if linked_research_rows:
            for research_row in linked_research_rows:
                research_title = str(research_row.get("title") or "").strip()
                research_desc = str(research_row.get("desc") or "").strip()
                if research_title:
                    summary_rows.append({"text": f"Research: {research_title}"})
                if research_desc:
                    summary_rows.append({"text": research_desc})
            debug_extra["linkedResearch"] = [
                {
                    "researchId": str(research_row.get("researchId") or ""),
                    "title": str(research_row.get("title") or ""),
                    "desc": str(research_row.get("desc") or ""),
                }
                for research_row in linked_research_rows
            ]
        linked_notes = embedded_prts_notes_by_entry.get(str(row_id)) or []
        if linked_notes:
            summary_rows.append({"text": f"Archive notes: {len(linked_notes)}"})
            seen_note_lines: set[tuple[str, str, str]] = set()
            for line in lines:
                normalized = re.sub(r"\s+", " ", str(line.get("text") or "")).strip()
                if not normalized:
                    continue
                seen_note_lines.add((str(line.get("hint") or ""), str(line.get("actor") or ""), normalized))
            linked_note_debug: list[dict] = []
            for note in linked_notes:
                note_id = str(note.get("id") or "")
                note_row = prts_notes.get(note_id) if isinstance(prts_notes.get(note_id), dict) else {}
                note_title = str(note.get("title") or note_id or "Archive Note")
                append_reference_line(
                    lines,
                    seen_note_lines,
                    note_id or row_id,
                    str(note.get("text") or ""),
                    hint=note_title,
                    debug={
                        **source_ref(
                            "PrtsNote",
                            note_id,
                            {
                                "linkedEntry": row_id,
                                "researchId": str(note.get("researchId") or ""),
                            },
                        ),
                        "fields": {
                            "text": text_trace("PrtsNote", note_id, "desc", note_row.get("desc")),
                        },
                    },
                )
                linked_note_debug.append({
                    "noteId": note_id,
                    "title": note_title,
                    "researchId": str(note.get("researchId") or ""),
                    "index": int(note.get("index") or 0),
                })
            if linked_note_debug:
                debug_extra["linkedNotes"] = linked_note_debug
        payload = {
            "key": row_id,
            "kind": "prts",
            "mission": entry_mission_id,
            "scene": entry_scene,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "PrtsAllItem",
                    row_id,
                    pick_fields(row, "contentId", "desc", "firstLvId", "id", "name", "order", "type"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        if first_lv_row:
            payload["_debug"]["firstLevel"] = source_ref(
                "PrtsFirstLv",
                first_lv_id,
                pick_fields(first_lv_row, "categoryId", "firstLvId", "icon", "itemIds", "name", "order", "subName"),
            )
        if page_row:
            payload["_debug"]["page"] = source_ref(
                "PrtsPage",
                category_id,
                pick_fields(page_row, "icon", "name", "pageType"),
            )
        payload["_debug"].update(debug_extra)
        write_conv_payload(row_id, payload)
        entry = {
            "k": row_id,
            "d": "prts",
            "m": entry_mission_id,
            "s": entry_scene,
            "t": entry_type,
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": [str(row.get("type") or "prts"), category_id],
        }
        search_text = " ".join(part for part in [
            row_id,
            content_id,
            first_lv_id,
            category_id,
            page_label,
            mission_label,
            subtitle,
            title,
            desc,
            " ".join(line.get("text") or "" for line in lines),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    for note_id, row in sorted(prts_notes.items()):
        if not isinstance(row, dict):
            continue
        if str(note_id) in embedded_prts_note_ids:
            continue
        text = t((row.get("desc") or {}).get("id"))
        note_meta = prts_note_metadata.get(note_id) or {}
        note_title = str(note_meta.get("title") or note_id)
        note_category = str(note_meta.get("category") or "")
        note_collection_ids = [
            str(value)
            for value in (note_meta.get("collectionIds") or [])
            if str(value)
        ]
        summary_rows: list[dict] = []
        if note_category:
            summary_rows.append({"text": f"Category: {prts_category_display_name(note_category)}"})
        if note_collection_ids:
            preview_ids = ", ".join(note_collection_ids[:3])
            if len(note_collection_ids) > 3:
                preview_ids += ", ..."
            summary_rows.append({"text": f"Linked entries: {preview_ids}"})
        payload = {
            "key": note_id,
            "kind": "prts",
            "mission": "PrtsNote",
            "scene": 0,
            "title": note_title,
            "lines": [{
                "id": note_id,
                "text": text,
                "_debug": {
                    **source_ref("PrtsNote", note_id, pick_fields(row, "desc", "id")),
                    "fields": {
                        "text": text_trace("PrtsNote", note_id, "desc", row.get("desc")),
                    },
                },
            }],
            "_debug": {
                "source": source_ref("PrtsNote", note_id, pick_fields(row, "desc", "id")),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        write_conv_payload(note_id, payload)
        note_tags = ["note"]
        if note_category:
            note_tags.extend([note_category, f"category_{collection_slug(note_category)}"])
        entry = {
            "k": note_id,
            "d": "prts",
            "m": "PrtsNote",
            "s": 0,
            "t": "prts",
            "a": 0,
            "title": note_title,
            "c": [],
            "n": 1,
            "p": preview(text or note_title),
            "tags": note_tags,
        }
        search_parts = [note_id, note_title, note_category, prts_category_display_name(note_category)]
        if text:
            search_parts.append(text)
        if note_collection_ids:
            search_parts.extend(note_collection_ids)
        entry["x"] = " ".join(part for part in search_parts if part)
        index_entries.append(entry)




    responsive_refs = collection_ai_bark_refs("streaming")
    responsive_people: dict[str, dict] = {}
    for response_id, bark_row in sorted(ai_bark_text.items(), key=lambda item: str(item[0])):
        if not isinstance(bark_row, dict):
            continue
        response_key = str(response_id)
        ref = responsive_refs.get(response_key) or {}
        speaker_id = str(ref.get("speakerId") or "")
        actor_id = str(ref.get("actorId") or speaker_actor_id(speaker_id) or "")
        person_key = actor_id or speaker_id or response_key
        display_name = (
            str(ref.get("speakerName") or "")
            or speaker_display_name(speaker_id)
            or speaker_display_name(actor_id)
            or actor_id
            or speaker_id
            or person_key
        )
        group = responsive_people.setdefault(
            person_key,
            {
                "displayName": display_name,
                "actorId": actor_id,
                "speakerIds": set(),
                "setIds": set(),
                "triggerKeys": set(),
                "responseIds": [],
                "audioOnlyResponseIds": set(),
                "audioPaths": set(),
                "linesByText": {},
            },
        )
        if display_name and (not group.get("displayName") or group["displayName"] == person_key):
            group["displayName"] = display_name
        if actor_id and not group.get("actorId"):
            group["actorId"] = actor_id

        if speaker_id:
            group["speakerIds"].add(speaker_id)
        if ref.get("setId"):
            group["setIds"].add(str(ref["setId"]))
        if ref.get("triggerKey"):
            group["triggerKeys"].add(str(ref["triggerKey"]))
        if ref.get("audioPath"):
            group["audioPaths"].add(str(ref["audioPath"]))
        group["responseIds"].append(response_key)

        bark_text = t((bark_row.get("barkText") or {}).get("id"))
        normalized_text = re.sub(r"\s+", " ", str(bark_text or "")).strip()
        if not normalized_text:
            if ref.get("audioPath"):
                group["audioOnlyResponseIds"].add(response_key)
            continue

        set_id = str(ref.get("setId") or "")
        set_sort = int(set_id) if set_id.lstrip("-").isdigit() else 10**9
        trigger_key = str(ref.get("triggerKey") or "")
        source_payload = {
            "responseId": response_key,
            "speakerId": speaker_id,
            "actorId": actor_id,
            "setId": set_id,
            "triggerKey": trigger_key,
            "audioPath": str(ref.get("audioPath") or ""),
            "source": str(ref.get("source") or ""),
        }

        line_info = group["linesByText"].get(normalized_text)
        if line_info is None:
            line_info = {
                "id": response_key,
                "text": bark_text,
                "speakerIds": set([speaker_id]) if speaker_id else set(),
                "setIds": set([set_id]) if set_id else set(),
                "triggerKeys": set([trigger_key]) if trigger_key else set(),
                "responseIds": [response_key],
                "audioPaths": set([str(ref.get("audioPath") or "")]) if ref.get("audioPath") else set(),
                "sourceRefs": [source_payload],
                "fieldTrace": text_trace("AIBarkText", response_key, "barkText", bark_row.get("barkText")),
                "sortKey": (set_sort, trigger_key or "~", response_key),
            }
            group["linesByText"][normalized_text] = line_info
        else:
            if speaker_id:
                line_info["speakerIds"].add(speaker_id)
            if set_id:
                line_info["setIds"].add(set_id)
            if trigger_key:
                line_info["triggerKeys"].add(trigger_key)
            if ref.get("audioPath"):
                line_info["audioPaths"].add(str(ref["audioPath"]))
            line_info["responseIds"].append(response_key)
            line_info["sourceRefs"].append(source_payload)
            line_info["sortKey"] = min(line_info["sortKey"], (set_sort, trigger_key or "~", response_key))

    print(f"Writing {len(responsive_people)} responsive conversations...")
    for person_key, group in sorted(
        responsive_people.items(),
        key=lambda item: ((item[1].get("displayName") or item[0]).lower(), item[0]),
    ):
        display_name = str(group.get("displayName") or person_key)
        actor_id = str(group.get("actorId") or person_key)
        mission_id = actor_id or person_key
        if display_name:
            extra_mission_names[mission_id] = display_name

        lines: list[dict] = []
        for line_info in sorted(group["linesByText"].values(), key=lambda item: item["sortKey"]):
            trigger_keys = sorted(line_info["triggerKeys"])
            set_ids = responsive_sort_values(line_info["setIds"])
            hint_bits: list[str] = []
            if trigger_keys:
                hint_bits.append(f"Triggers: {responsive_preview_values(trigger_keys)}")
            if set_ids:
                hint_bits.append(f"Sets: {responsive_preview_values(set_ids)}")
            if not trigger_keys and line_info["audioPaths"]:
                hint_bits.append("Audio fallback")
            if len(line_info["responseIds"]) > 1:
                hint_bits.append(f"Responses: {len(line_info['responseIds'])}")
            line = {
                "id": line_info["id"],
                "aid": actor_id,
                "actor": display_name,
                "text": line_info["text"],
                "_debug": {
                    "source": {
                        "table": "AIBarkText",
                        "actorId": actor_id,
                        "speakerIds": sorted(line_info["speakerIds"]),
                        "setIds": set_ids,
                        "triggerKeys": trigger_keys,
                        "responseIds": responsive_sort_values(line_info["responseIds"]),
                        "audioPaths": sorted(line_info["audioPaths"]),
                        "refs": line_info["sourceRefs"],
                    },
                    "fields": {
                        "text": line_info["fieldTrace"],
                    },
                },
            }
            if hint_bits:
                line["hint"] = " | ".join(hint_bits)
            lines.append(line)

        duplicate_count = max(0, len(group["responseIds"]) - len(lines))
        summary_rows = [
            {"text": f"Speaker: {display_name}"},
            {"text": f"Actor ID: {actor_id}"},
            {"text": f"Unique lines: {len(lines)}"},
            {"text": f"Source bark rows: {len(group['responseIds'])}"},
        ]
        if duplicate_count:
            summary_rows.append({"text": f"Duplicate bark rows merged: {duplicate_count}"})
        if group["audioOnlyResponseIds"]:
            summary_rows.append({"text": f"Audio fallback rows: {len(group['audioOnlyResponseIds'])}"})
        summary_rows.extend(
            responsive_summary_rows("Speaker IDs", sorted(group["speakerIds"]), chunk_size=6)
        )
        summary_rows.extend(
            responsive_summary_rows("Trigger sets", responsive_sort_values(group["setIds"]), chunk_size=12)
        )
        summary_rows.extend(
            responsive_summary_rows("Trigger keys", sorted(group["triggerKeys"]), chunk_size=8)
        )

        out_key = f"responsive_{person_key}"
        payload = {
            "key": out_key,
            "kind": "responsive",
            "mission": mission_id,
            "scene": 0,
            "title": display_name,
            "lines": lines,
            "summary": summary_rows,
            "_debug": {
                "source": {
                    "table": "AIBarkText",
                    "personKey": person_key,
                    "actorId": actor_id,
                    "speakerIds": sorted(group["speakerIds"]),
                    "setIds": responsive_sort_values(group["setIds"]),
                    "triggerKeys": sorted(group["triggerKeys"]),
                    "responseIds": responsive_sort_values(group["responseIds"]),
                    "audioOnlyResponseIds": responsive_sort_values(group["audioOnlyResponseIds"]),
                    "audioPaths": sorted(group["audioPaths"]),
                },
            },
        }
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": "responsive",
            "m": mission_id,
            "s": 0,
            "t": "responsive",
            "a": 0,
            "title": payload["title"],
            "c": [actor_id],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), payload["title"])),
            "tags": ["responsive"],
        }
        search_text = " ".join(
            part
            for part in [
                person_key,
                actor_id,
                display_name,
                " ".join(sorted(group["speakerIds"])),
                " ".join(responsive_sort_values(group["setIds"])),
                " ".join(sorted(group["triggerKeys"])),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    # Emit unmatched dialog ids (utility/spaceship/etc.) as a single bucket per prefix.
    if misc:
        misc_groups: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for did, e in misc:
            # Group on the substring up to the last underscore-then-digits.
            key = re.sub(r"_\d+(_\d+)?$", "", did) or "_misc"
            misc_groups[key].append((did, e))
        print(f"Writing {len(misc_groups)} misc dialog buckets...")
        for key, items in misc_groups.items():
            items.sort(key=lambda x: x[0])
            lines = []
            actors: set[str] = set()
            for did, e in items:
                actor_id = e.get("actorNameId") or ""
                text = t(e.get("dialogText", {}).get("id"))
                if actor_id:
                    actors.add(actor_id)
                lines.append({
                    "id": did,
                    "aid": actor_id,
                    "actor": t(e.get("actorName", {}).get("id")),
                    "text": text,
                    "hint": t(e.get("hint", {}).get("id")),
                    "audio": e.get("audioOverride") or "",
                    "emo": e.get("emotionType", 0),
                    "_debug": {
                        **source_ref(
                            "DialogTextTable",
                            did,
                            pick_fields(
                                e,
                                "actorNameId",
                                "actorName",
                                "dialogText",
                                "hint",
                                "audioOverride",
                                "emotionType",
                            ),
                        ),
                        "fields": {
                            "actor": text_trace("DialogTextTable", did, "actorName", e.get("actorName")),
                            "text": text_trace("DialogTextTable", did, "dialogText", e.get("dialogText")),
                            "hint": text_trace("DialogTextTable", did, "hint", e.get("hint")),
                        },
                    },
                })
            out_key = f"misc_{key}"
            type_, act, mission, scene = slot_misc(key)
            ordered_line_ids, line_order_debug = resolve_scene_line_order(
                key,
                [line.get("id") or "" for line in lines],
            )
            if ordered_line_ids:
                line_order_index = {line_id: idx for idx, line_id in enumerate(ordered_line_ids)}
                lines = [
                    line
                    for _idx, line in sorted(
                        enumerate(lines),
                        key=lambda item: (
                            line_order_index.get(item[1].get("id") or "", len(ordered_line_ids) + item[0]),
                            item[0],
                        ),
                    )
                ]
            prev_text = next((line.get("text") or "" for line in lines if line.get("text")), "")
            payload = {
                "key": out_key, "kind": "dlg",
                "mission": mission, "scene": scene,
                "lines": lines,
                "_debug": {
                    "title": mission_name_trace(mission),
                },
            }
            if line_order_debug:
                payload["_debug"]["lineOrder"] = line_order_debug
            if out_key in summary_by_key:
                payload["summary"] = summary_by_key[out_key]
            if out_key in options_by_key:
                packed_options = pack_options(options_by_key[out_key], lines, key)
                payload["optionGroups"] = packed_options["groups"]
                if packed_options["warnings"]:
                    payload["warnings"] = packed_options["warnings"]
            line_graph = build_dialog_tree_line_graph_payload(
                key,
                [line.get("id") or "" for line in lines],
            )
            if line_graph:
                payload["lineGraph"] = line_graph
            graph_fragments = build_dialog_tree_fragment_payload(key)
            if graph_fragments:
                payload["graphFragments"] = graph_fragments
            scene_graph_links = build_dialog_tree_scene_link_payload(key)
            if scene_graph_links:
                payload["sceneGraphLinks"] = scene_graph_links
                scene_graph_links_by_key[out_key] = scene_graph_links
            attach_runtime_registry_debug(payload)
            attach_scene_order_warning(payload)
            story_issue_codes = dialog_story_issue_codes(payload)
            recovery_methods = dialog_recovery_methods(payload)
            write_conv_payload(out_key, payload)
            entry = {
                "k": out_key, "d": "dlg", "m": mission, "s": scene,
                "t": type_, "a": act, "c": sorted(actors),
                "n": len(lines), "p": preview(prev_text),
            }
            if (tags := entry_tags(out_key, mission)):
                entry["tags"] = tags
            entry["x"] = merge_search_text(
                indexed_line_haystack(lines, "text", "actor", "aid", "hint"),
                extras_text(out_key),
            )
            entry["x"] = merge_search_text(
                entry.get("x", ""),
                mission_context_text(mission),
            )
            entry["x"] = merge_search_text(entry.get("x", ""), graph_fragments_text(graph_fragments))
            entry["x"] = merge_search_text(entry.get("x", ""), scene_links_text(scene_graph_links))
            if graph_fragments:
                tags = entry.setdefault("tags", [])
                if "graphFragment" not in tags:
                    tags.append("graphFragment")
            if scene_graph_links:
                tags = entry.setdefault("tags", [])
                if "sceneGraph" not in tags:
                    tags.append("sceneGraph")
            if story_issue_codes:
                entry["storyIssues"] = story_issue_codes
            if recovery_methods:
                entry["recoveryMethods"] = recovery_methods
            if not entry["x"]:
                entry.pop("x")
            index_entries.append(entry)



    def mark_duplicate_sim_operator_entries() -> None:
        archive_text_by_actor: dict[str, str] = {}
        for entry in index_entries:
            if entry.get("d") != "table_charactertable":
                continue
            actor_ids = [str(actor_id or "").lower() for actor_id in (entry.get("c") or []) if actor_id]
            actor_id = actor_ids[0] if actor_ids else ""
            if not actor_id:
                continue
            conv_path = conv_dir / f"{entry.get('k')}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            line_texts = normalized_duplicate_line_texts(payload)
            if not line_texts:
                continue
            archive_text_by_actor[actor_id] = "\n".join([
                archive_text_by_actor.get(actor_id, ""),
                *line_texts,
            ]).strip()

        for entry in index_entries:
            key = str(entry.get("k") or "")
            if not (key.startswith("misc_sim_") or key.startswith("env_greetEnvTalk_")):
                continue
            actor_id = sim_duplicate_actor_from_key(key)
            archive_blob = archive_text_by_actor.get(actor_id, "")
            if not actor_id or not archive_blob:
                continue
            conv_path = conv_dir / f"{key}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            line_texts = normalized_duplicate_line_texts(payload)
            if line_texts and all(text in archive_blob for text in line_texts):
                entry["omitSimDuplicate"] = True

    mark_duplicate_sim_operator_entries()

    for mission in {entry["m"] for entry in index_entries if entry.get("m")}:
        mission_name(mission)
    if include_reference_in_story_index:
        write_texttable_collection_pages(collect_exported_texttable_row_ids())

    def merge_conv_hint_search_text(entry: dict) -> None:
        key = str(entry.get("k") or "")
        if not key:
            return
        conv_path = conv_dir / f"{key}.json"
        if not conv_path.exists():
            return
        try:
            payload = json.loads(conv_path.read_text(encoding="utf-8"))
        except Exception:
            return
        hint_text = line_haystack(payload.get("lines") or [], "hint")
        if hint_text:
            entry["x"] = merge_search_text(entry.get("x", ""), hint_text)
            if not entry["x"]:
                entry.pop("x", None)

    for entry in index_entries:
        merge_conv_hint_search_text(entry)




    def story_source_link_report_rows(keys: set[str]) -> list[dict]:
        rows: list[dict] = []
        for key in sorted(keys):
            links = story_source_links.get(key) or []
            source_counts = Counter(str(link.get("source") or "") for link in links)
            rows.append({
                "key": key,
                "kind": str((links[0] if links else {}).get("kind") or ""),
                "references": len(links),
                "sources": {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                },
                "files": _unique_preserve(
                    str(link.get("file") or "")
                    for link in links
                    if link.get("file")
                )[:8],
            })
        return rows

    def render_story_source_link_report_md(report: dict) -> str:
        summary = report.get("summary") or {}
        lines = [
            f"# Story Source Links ({language_code})",
            "",
            "## Summary",
            "",
            f"- Source-link keys: `{summary.get('sourceLinkKeys', 0)}`",
            f"- Source references: `{summary.get('sourceReferences', 0)}`",
            f"- Attached WebUI keys: `{summary.get('attachedKeys', 0)}`",
            f"- Attached references: `{summary.get('attachedReferences', 0)}`",
            f"- Referenced but missing in WebUI: `{summary.get('referencedMissingKeys', 0)}`",
            f"- Story entries without source links: `{summary.get('storyEntriesWithoutSourceLinks', 0)}`",
            "",
            "## Missing Referenced Keys",
            "",
        ]
        for row in (report.get("referencedMissing") or [])[:80]:
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('references')}` refs)")
        if not report.get("referencedMissing"):
            lines.append("- None")
        lines.extend(["", "## Story Entries Without Source Links", ""])
        for row in (report.get("storyEntriesWithoutSourceLinks") or [])[:80]:
            label = row.get("mission") or ""
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}{', ' + label if label else ''})")
        if not report.get("storyEntriesWithoutSourceLinks"):
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def attach_story_source_links_to_outputs() -> dict:
        if not story_source_links:
            return {}
        available_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }
        def resolve_source_link_key(source_key: str) -> str:
            if source_key in available_keys:
                return source_key
            if source_key.startswith("dlg_"):
                misc_key = f"misc_{source_key}"
                if misc_key in available_keys:
                    return misc_key
                match = re.match(r"^(dlg_.+_\d+)d\d+$", source_key)
                if match and match.group(1) in available_keys:
                    return match.group(1)
            if source_key.startswith("cutscene_") and source_key.endswith("_start"):
                base_key = source_key.removesuffix("_start")
                if base_key in available_keys:
                    return base_key
            return ""

        resolved_source_links: dict[str, list[dict]] = defaultdict(list)
        unresolved_source_keys: set[str] = set()
        for source_key, links in story_source_links.items():
            resolved_key = resolve_source_link_key(source_key)
            if not resolved_key:
                unresolved_source_keys.add(source_key)
                continue
            for link in links:
                resolved_link = dict(link)
                if source_key != resolved_key:
                    resolved_link["sourceKey"] = source_key
                resolved_source_links[resolved_key].append(resolved_link)

        def unique_story_source_link_mission(links: list[dict]) -> str:
            missions: set[str] = set()
            for link in links:
                mission_id = str(link.get("mission") or "").strip()
                if not mission_id:
                    source = link.get("source") if isinstance(link.get("source"), dict) else {}
                    mission_id = str(source.get("mission") or "").strip()
                if not mission_id:
                    continue
                type_key, _act = parse_mission(mission_id)
                if type_key in MISSION_STORY_TYPES:
                    missions.add(mission_id)
            return next(iter(missions)) if len(missions) == 1 else ""

        attached_keys: set[str] = set()
        attached_refs = 0
        for entry in index_entries:
            key = str(entry.get("k") or "")
            links = resolved_source_links.get(key) or []
            if not links:
                continue
            attached_keys.add(key)
            attached_refs += len(links)
            compact_links = [compact_story_source_link(link) for link in links[:12]]
            omitted = max(0, len(links) - len(compact_links))
            entry["src"] = story_source_link_index_summary(links)
            entry["x"] = merge_search_text(entry.get("x", ""), story_source_link_search_text(links))
            if entry.get("d") == "sns":
                story_mission = unique_story_source_link_mission(links)
                if story_mission and story_mission != entry.get("m"):
                    entry["storyMission"] = story_mission
            tags = entry.setdefault("tags", [])
            if "sourceLinked" not in tags:
                tags.append("sourceLinked")

            conv_path = conv_dir / f"{key}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            payload["sourceLinks"] = compact_links
            if omitted:
                payload["sourceLinksOmitted"] = omitted
            debug = payload.setdefault("_debug", {})
            debug["sourceLinks"] = {
                "source": {
                    "index": repo_rel(STORY_SOURCE_LINKS_PATH),
                    "key": key,
                    "count": len(links),
                    "shown": len(compact_links),
                    "omitted": omitted,
                },
            }
            write_json(conv_path, payload)
            remember_written(conv_path, written_conv_paths)

        referenced_missing = unresolved_source_keys
        source_link_candidate_kinds = set(MISSION_SCENE_ENTRY_KINDS) | {"env", "misc"}

        story_entries_without_links = [
            {
                "key": str(entry.get("k") or ""),
                "kind": str(entry.get("d") or ""),
                "mission": str(entry.get("m") or ""),
            }
            for entry in index_entries
            if entry.get("k")
            and entry.get("d") in source_link_candidate_kinds
            and entry.get("k") not in resolved_source_links
        ]
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "sourceIndex": repo_rel(STORY_SOURCE_LINKS_PATH),
            "summary": {
                "sourceLinkKeys": len(story_source_links),
                "sourceReferences": sum(len(rows) for rows in story_source_links.values()),
                "attachedKeys": len(attached_keys),
                "attachedReferences": attached_refs,
                "referencedMissingKeys": len(referenced_missing),
                "storyEntriesWithoutSourceLinks": len(story_entries_without_links),
            },
            "referencedMissing": sorted(
                story_source_link_report_rows(referenced_missing),
                key=lambda row: (-int(row.get("references") or 0), row.get("key") or ""),
            )[:300],
            "storyEntriesWithoutSourceLinks": story_entries_without_links[:500],
        }
        report_json = REPORTS_DIR / f"story_source_links_{language_code}.json"
        report_md = REPORTS_DIR / f"story_source_links_{language_code}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(report_json, report, indent=2, compact=False)
        report_md.write_text(render_story_source_link_report_md(report), encoding="utf-8")
        report["report"] = {
            "json": repo_rel(report_json),
            "markdown": repo_rel(report_md),
        }
        return report

    story_source_link_report = attach_story_source_links_to_outputs()





    def render_narrative_video_report_md(report: dict) -> str:
        summary = report.get("summary") or {}
        lines = [
            f"# Narrative Videos ({language_code})",
            "",
            "## Summary",
            "",
            f"- Scanned video files: `{summary.get('scannedVideos', 0)}`",
            f"- Attached WebUI keys: `{summary.get('attachedKeys', 0)}`",
            f"- Attached video refs: `{summary.get('attachedVideos', 0)}`",
            f"- Timeline-backed evidence rows: `{summary.get('authoritativeEvidenceRows', 0)}`",
            f"- Standalone video files: `{summary.get('standaloneVideoKeys', 0)}`",
            f"- Standalone video refs: `{summary.get('standaloneVideoRefs', 0)}`",
            f"- Unresolved video refs: `{summary.get('unresolvedVideos', 0)}`",
            "",
            "## Attached Keys",
            "",
        ]
        for row in (report.get("attached") or [])[:120]:
            names = ", ".join((row.get("files") or [])[:4])
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('videos')}` refs): {names}")
        if not report.get("attached"):
            lines.append("- None")
        lines.extend(["", "## Standalone Videos", ""])
        for row in (report.get("standalone") or [])[:120]:
            names = ", ".join((row.get("files") or [])[:4])
            lines.append(f"- `{row.get('key')}` ({row.get('mission')}, `{row.get('videos')}` refs): {names}")
        if not report.get("standalone"):
            lines.append("- None")
        lines.extend(["", "## Unresolved Videos", ""])
        for row in (report.get("unresolved") or [])[:120]:
            candidates = ", ".join(f"`{candidate}`" for candidate in (row.get("keyCandidates") or [])[:4])
            lines.append(f"- `{row.get('name')}` ({row.get('kind')}) -> {candidates}")
        if not report.get("unresolved"):
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def attach_narrative_videos_to_outputs() -> dict:
        if not narrative_video_assets:
            return {}
        available_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }

        def resolve_video_key(ref: dict) -> str:
            authoritative_keys = list(ref.get("authoritativeKeys") or [])
            candidate_list = list(ref.get("keyCandidates") or [])
            if authoritative_keys:
                for candidate in authoritative_keys:
                    candidate = str(candidate or "")
                    if candidate in available_keys:
                        return candidate
                return ""
            for candidate in candidate_list:
                candidate = str(candidate or "")
                if candidate in available_keys:
                    return candidate
                if candidate.startswith("dlg_"):
                    misc_key = f"misc_{candidate}"
                    if misc_key in available_keys:
                        return misc_key
                    match = re.match(r"^(dlg_.+_\d+)d\d+$", candidate)
                    if match and match.group(1) in available_keys:
                        return match.group(1)
            return ""

        resolved_videos: dict[str, list[dict]] = defaultdict(list)
        standalone_videos: dict[str, list[dict]] = defaultdict(list)
        unresolved_videos: list[dict] = []

        def video_has_authoritative_story_binding(ref: dict) -> bool:
            return bool(ref.get("authoritativeKeys"))

        # Index entry kind for each WebUI key. The video distribution rules read
        # this so cutscene-bound FMVs stay out of the cutscene bundle while
        # dlg-bound FMVs still embed inline.
        entry_kind_by_key: dict[str, str] = {
            str(entry.get("k") or ""): str(entry.get("d") or "")
            for entry in index_entries
            if entry.get("k")
        }

        def standalone_video_key(ref: dict) -> str:
            stem = str(ref.get("baseStem") or ref.get("stem") or ref.get("name") or "").strip()
            stem = re.sub(r"\.[^.]+$", "", stem, flags=re.IGNORECASE)
            stem = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_").lower()
            return f"video_{stem or 'unknown'}"

        def strip_video_gender_prefix(stem: str) -> tuple[str, str]:
            match = re.match(r"^(?P<gender>f|m|fm)_(?P<rest>cs_video_.+)$", stem or "", flags=re.IGNORECASE)
            if not match:
                return "", stem or ""
            return match.group("gender").lower(), match.group("rest")

        def video_scene_hint(refs: list[dict]) -> str:
            for ref in refs:
                binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                scene = str(binding.get("scene") or "").strip()
                if scene and not binding.get("isHint"):
                    return strip_video_scene_prefix(scene)
            for ref in refs:
                _gender, base = strip_video_gender_prefix(str(ref.get("baseStem") or ref.get("stem") or ""))
                for prefix in ("cs_video_dlg_", "cs_video_cutscene_", "cs_video_remotecomm_", "cs_video_"):
                    if base.startswith(prefix):
                        return strip_video_scene_prefix(base[len(prefix):])
                if base:
                    return strip_video_scene_prefix(base)
            return ""

        def strip_video_scene_prefix(scene: str) -> str:
            value = str(scene or "")
            for prefix in ("dlg_", "cutscene_", "remotecomm_", "radio_", "black_"):
                if value.startswith(prefix):
                    return value[len(prefix):]
            return value

        def video_mission_scene(refs: list[dict]) -> tuple[str, int]:
            scene_hint = video_scene_hint(refs)
            match = re.match(
                r"^(?P<mission>[a-z]+\d+m\d+(?:d\d+)?)(?:_(?P<scene>\d+).*)?$",
                scene_hint,
                flags=re.IGNORECASE,
            )
            if not match:
                return (scene_hint.split("_", 1)[0].lower() if scene_hint else "video", 0)
            return match.group("mission").lower(), int(match.group("scene") or 0)

        def video_title(refs: list[dict]) -> str:
            base_names = _unique_preserve(
                str(ref.get("baseStem") or ref.get("stem") or "")
                for ref in refs
                if ref.get("baseStem") or ref.get("stem")
            )
            if base_names:
                return base_names[0]
            names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
            return names[0] if names else "Narrative video"

        for ref in narrative_video_assets:
            resolved_key = resolve_video_key(ref)
            has_authoritative = bool(resolved_key) and video_has_authoritative_story_binding(ref)
            resolved_kind = entry_kind_by_key.get(resolved_key, "") if has_authoritative else ""
            # Rule: a video is always emitted as a standalone `video_*` bundle.
            # When the FMV is bound to a dialog (dlg/remotecomm) it ALSO embeds
            # inline so the dlg keeps its FMV preview. Cutscene-bound FMVs only
            # go standalone — the cutscene bundle never carries the video.
            standalone_ref = dict(ref)
            standalone_ref["_resolvedKey"] = resolved_key
            standalone_ref["_resolvedKind"] = resolved_kind
            if has_authoritative and resolved_kind in {"dlg", "remotecomm"}:
                resolved_ref = dict(ref)
                resolved_ref["resolvedKey"] = resolved_key
                resolved_videos[resolved_key].append(resolved_ref)
            standalone_videos[standalone_video_key(ref)].append(standalone_ref)
            if not resolved_key:
                unresolved_videos.append(ref)

        authoritative_evidence: list[dict] = []

        def timeline_video_evidence_rows(key: str, refs: list[dict]) -> list[dict]:
            rows: list[dict] = []
            seen: set[tuple[str, str, str]] = set()
            for ref in refs:
                binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                if not binding or binding.get("isHint"):
                    continue
                source_kinds = set(binding.get("sourceKinds") or [])
                if "timelinePlayable" not in source_kinds:
                    continue
                evidence_sources = [
                    source for source in (binding.get("evidence") or [])
                    if isinstance(source, dict) and source.get("kind") == "timelinePlayable"
                ]
                clips = [
                    clip for clip in (binding.get("clips") or [])
                    if isinstance(clip, dict)
                ]
                evidence_key = (
                    str(binding.get("fmvId") or ref.get("stem") or ""),
                    str(ref.get("rel") or ""),
                    key,
                )
                if evidence_key in seen:
                    continue
                seen.add(evidence_key)
                rows.append({
                    "webuiKey": key,
                    "webuiFile": f"data/lang/{language_code}/conv/{key}.json",
                    "video": {
                        "name": str(ref.get("name") or ""),
                        "rel": str(ref.get("rel") or ""),
                        "source": str(ref.get("source") or ""),
                        "format": str(ref.get("format") or ""),
                        "size": int(ref.get("size") or 0),
                    },
                    "binding": {
                        "fmvId": str(binding.get("fmvId") or ref.get("stem") or ""),
                        "scene": str(binding.get("scene") or ""),
                        "mission": str(binding.get("mission") or ""),
                        "sourceKinds": sorted(source_kinds),
                    },
                    "evidence": {
                        "method": "timelinePlayable",
                        "why": (
                            "Timeline FMV clip references a BeyondFMVPlayableAsset; "
                            "that playable's fmvId selects this narrative video."
                        ),
                        "sources": evidence_sources,
                        "clips": clips[:8],
                    },
                })
            return rows

        def standalone_binding_summary(refs: list[dict]) -> tuple[str, str]:
            for ref in refs:
                binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                if not binding or binding.get("isHint"):
                    continue
                scene = str(binding.get("scene") or "")
                if not scene:
                    continue
                resolved_kind = str(ref.get("_resolvedKind") or "")
                resolved_key = str(ref.get("_resolvedKey") or "")
                if resolved_kind == "cutscene":
                    label, target = "cutscene", resolved_key or scene
                elif resolved_kind == "dlg":
                    label, target = "dialog", resolved_key or scene
                elif resolved_kind == "remotecomm":
                    label, target = "remotecomm", resolved_key or scene
                elif scene.startswith("cutscene_"):
                    label, target = "cutscene", scene
                elif scene.startswith("dlg_"):
                    label, target = "dialog", scene
                elif scene.startswith("remotecomm_"):
                    label, target = "remotecomm", scene
                else:
                    label, target = "scene", scene
                attached_note = "" if resolved_kind == "cutscene" or not resolved_kind else " (also embedded inline)"
                return (
                    f"Attachment status: timeline-bound to {label} `{target}`{attached_note}; kept standalone in WebUI",
                    "standaloneVideoBoundButKeptSeparate",
                )
            return (
                "Attachment status: no non-name binding found for a dialog or cutscene",
                "standaloneVideoNoAuthoritativeStoryBinding",
            )

        def emit_standalone_video_outputs() -> list[dict]:
            entries: list[dict] = []
            for key, raw_refs in sorted(standalone_videos.items()):
                refs = sorted(raw_refs, key=narrative_video_sort_key)
                if not refs:
                    continue
                compact_refs = [compact_narrative_video_ref(ref) for ref in refs[:16]]
                omitted = max(0, len(refs) - len(compact_refs))
                mission, scene = video_mission_scene(refs)
                type_, act = parse_mission(mission)
                title = video_title(refs)
                names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
                source_counts = Counter(str(ref.get("source") or "") for ref in refs)
                format_counts = Counter(str(ref.get("format") or "") for ref in refs)
                attachment_text, attachment_reason = standalone_binding_summary(refs)
                # `title` is the asset baseStem (e.g. cs_video_e0m0_3); the game
                # ships no localized title for FMVs. Keep it as a search hint
                # and as the lead summary label, but don't expose it as a
                # `title` field — that would mislead the WebUI into treating
                # the stem as a human-readable name. cutscene/dlg/radio bundles
                # also omit the field.
                #
                # We do NOT pull `cs_video_<scene>_NN` TextTable rows into the
                # standalone video bundle. Those rows share a name with the FMV
                # but the game's FMV subtitle pipeline doesn't reference them
                # by id, and no timeline subtitle track inside the FMV's
                # playable carries those keys either. Surfacing them here would
                # be name-only inference, not evidence-backed.
                summary_rows = [
                    {"text": f"Standalone narrative video: {title}"},
                    {"text": f"Mission: {mission}"},
                    {"text": f"Files: {len(refs)} exported variant(s)"},
                    {"text": attachment_text},
                ]
                payload = {
                    "key": key,
                    "kind": "video",
                    "mission": mission,
                    "scene": scene,
                    "lines": [],
                    "summary": summary_rows,
                    "narrativeVideos": compact_refs,
                    "_debug": {
                        "title": mission_name_trace(mission),
                        "narrativeVideos": {
                            "source": {
                                "key": key,
                                "count": len(refs),
                                "shown": len(compact_refs),
                                "omitted": omitted,
                                "reason": attachment_reason,
                            },
                        },
                    },
                }
                if omitted:
                    payload["narrativeVideosOmitted"] = omitted
                write_conv_payload(key, payload)
                entry = {
                    "k": key,
                    "d": "video",
                    "m": mission,
                    "s": scene,
                    "t": type_ if type_ != "?" else "other",
                    "a": act,
                    "c": [],
                    "n": 0,
                    "p": preview(", ".join(names) or title),
                    "tags": ["narrativeVideo"],
                    "vid": narrative_video_index_summary(refs),
                    "x": merge_search_text(
                        " ".join([
                            key,
                            title,
                            mission,
                            " ".join(names),
                            " ".join(str(ref.get("rel") or "") for ref in refs),
                            " ".join(str(ref.get("stem") or "") for ref in refs),
                        ]),
                        mission_context_text(mission),
                    ),
                }
                entry["videoSources"] = {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                }
                entry["videoFormats"] = {
                    fmt: format_counts[fmt]
                    for fmt in sorted(format_counts)
                    if fmt
                }
                if not entry["x"]:
                    entry.pop("x", None)
                entries.append(entry)
            return entries

        attached_rows: list[dict] = []
        attached_refs = 0
        for entry in index_entries:
            key = str(entry.get("k") or "")
            refs = sorted(resolved_videos.get(key) or [], key=narrative_video_sort_key)
            if not refs:
                continue
            attached_refs += len(refs)
            authoritative_evidence.extend(timeline_video_evidence_rows(key, refs))
            compact_refs = [compact_narrative_video_ref(ref) for ref in refs[:16]]
            omitted = max(0, len(refs) - len(compact_refs))
            entry["vid"] = narrative_video_index_summary(refs)
            entry["x"] = merge_search_text(entry.get("x", ""), narrative_video_search_text(refs))
            tags = entry.setdefault("tags", [])
            if "narrativeVideo" not in tags:
                tags.append("narrativeVideo")
            conv_media_tags_by_key[key].add("mediaVideo")

            conv_path = conv_dir / f"{key}.json"
            if conv_path.exists():
                try:
                    payload = json.loads(conv_path.read_text(encoding="utf-8"))
                except Exception:
                    payload = None
                if isinstance(payload, dict):
                    payload["narrativeVideos"] = compact_refs
                    if omitted:
                        payload["narrativeVideosOmitted"] = omitted
                    if isinstance(payload.get("cutscene"), dict):
                        payload["cutscene"]["videoRefs"] = compact_refs
                    debug = payload.setdefault("_debug", {})
                    debug["narrativeVideos"] = {
                        "source": {
                            "key": key,
                            "count": len(refs),
                            "shown": len(compact_refs),
                            "omitted": omitted,
                        },
                    }
                    unplaced_video_stems = sorted({
                        str(ref.get("baseStem") or ref.get("stem") or ref.get("name") or "")
                        for ref in refs
                        if not any(
                            isinstance(clip, dict) and isinstance(clip.get("start"), (int, float))
                            for clip in (((ref.get("binding") or {}).get("clips")) or [])
                        )
                    })
                    if unplaced_video_stems and str(entry.get("d") or "") in ("cutscene", "remotecomm"):
                        unplaced_video_stems = []
                    if unplaced_video_stems:
                        existing_warnings = [
                            warning for warning in (payload.get("warnings") or [])
                            if isinstance(warning, dict)
                            and warning.get("code") != "narrativeVideoUnplaced"
                        ]
                        existing_warnings.append({
                            "code": "narrativeVideoUnplaced",
                            "status": "missing",
                            "videoStems": unplaced_video_stems,
                            "videoCount": len(unplaced_video_stems),
                        })
                        payload["warnings"] = existing_warnings
                    write_json(conv_path, payload)
                    remember_written(conv_path, written_conv_paths)

            source_counts = Counter(str(ref.get("source") or "") for ref in refs)
            attached_rows.append({
                "key": key,
                "kind": str(entry.get("d") or ""),
                "mission": str(entry.get("m") or ""),
                "videos": len(refs),
                "sources": {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                },
                "files": _unique_preserve(
                    str(ref.get("name") or "")
                    for ref in refs
                    if ref.get("name")
                )[:12],
            })

        standalone_entries = emit_standalone_video_outputs()
        for entry in standalone_entries:
            index_entries.append(entry)
            conv_media_tags_by_key[str(entry.get("k") or "")].add("mediaVideo")

        unresolved_rows = [
            {
                "name": str(ref.get("name") or ""),
                "kind": str(ref.get("kind") or ""),
                "rel": str(ref.get("rel") or ""),
                "keyCandidates": list(ref.get("keyCandidates") or []),
            }
            for ref in unresolved_videos
        ]
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "summary": {
                "scannedVideos": len(narrative_video_assets),
                "attachedKeys": len(attached_rows),
                "attachedVideos": attached_refs,
                "authoritativeEvidenceRows": len(authoritative_evidence),
                "standaloneVideoKeys": len(standalone_entries),
                "standaloneVideoRefs": sum(len(rows) for rows in standalone_videos.values()),
                "unresolvedVideos": len(unresolved_videos),
                "cutsceneVideoFiles": sum(1 for ref in narrative_video_assets if ref.get("kind") == "cutscene"),
                "remotecommVideoFiles": sum(1 for ref in narrative_video_assets if ref.get("kind") == "remotecomm"),
            },
            "attached": sorted(
                attached_rows,
                key=lambda row: (-int(row.get("videos") or 0), row.get("key") or ""),
            )[:500],
            "standalone": [
                {
                    "key": str(entry.get("k") or ""),
                    "mission": str(entry.get("m") or ""),
                    "videos": int((entry.get("vid") or {}).get("n") or 0),
                    "files": list((entry.get("vid") or {}).get("files") or []),
                }
                for entry in standalone_entries[:500]
            ],
            "unresolved": unresolved_rows[:500],
        }
        report_json = REPORTS_DIR / f"narrative_videos_{language_code}.json"
        report_md = REPORTS_DIR / f"narrative_videos_{language_code}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        evidence_payload = {
            "generated": report["generated"],
            "language": language_code,
            "summary": {
                "rows": len(authoritative_evidence),
                "webuiKeys": len({row.get("webuiKey") for row in authoritative_evidence}),
                "method": "timelinePlayable",
            },
            "rows": sorted(
                authoritative_evidence,
                key=lambda row: (
                    str(row.get("webuiKey") or ""),
                    str(((row.get("binding") or {}).get("fmvId")) or ""),
                    str(((row.get("video") or {}).get("rel")) or ""),
                ),
            ),
        }
        evidence_path = out_dir / "narrative_video_evidence.json"
        write_json(evidence_path, evidence_payload)
        write_json(report_json, report, indent=2, compact=False)
        report_md.write_text(render_narrative_video_report_md(report), encoding="utf-8")
        report["report"] = {
            "json": repo_rel(report_json),
            "markdown": repo_rel(report_md),
            "evidence": repo_rel(evidence_path),
        }
        return report

    narrative_video_report = attach_narrative_videos_to_outputs()

    def normalize_index_entry_defaults(entry: dict) -> None:
        type_key = str(entry.get("t") or "").strip()
        if not type_key or type_key in {"?", "x"}:
            entry["t"] = "other"

        raw_tags = list(entry.get("tags") or [])
        raw_tags.extend(sorted(conv_media_tags_by_key.get(str(entry.get("k") or ""), set())))
        tags = []
        for raw_tag in raw_tags:
            tag = str(raw_tag or "").strip()
            if tag and tag not in tags:
                tags.append(tag)
        entry["tags"] = tags or ["other"]

    for entry in index_entries:
        normalize_index_entry_defaults(entry)

    # Sort index by type, act, mission, scene
    index_entries.sort(key=lambda e: (e["d"], e["t"], e["a"], e["m"], e["s"]))
    mission_names = {
        mission: name
        for mission in sorted({e["m"] for e in index_entries if e.get("m")})
        if (name := mission_name(mission))
    }
    present_missions = {e["m"] for e in index_entries if e.get("m")}
    for mission, name in sorted(extra_mission_names.items()):
        if mission in present_missions and name:
            mission_names.setdefault(mission, name)

    def env_entry_search_text(env_entry: dict) -> str:
        parts: list[str] = []
        if env_entry.get("id"):
            parts.append(str(env_entry["id"]))
        if env_entry.get("lines"):
            parts.append(indexed_line_haystack(env_entry["lines"], "text", "actor", "aid", "emoji"))
        npc = env_entry.get("npc") or {}
        for field in ("npcId", "name", "title", "dialogSelector"):
            value = npc.get(field)
            if value:
                parts.append(str(value))
        return " ".join(part for part in parts if part)

    index_entry_by_key = {
        entry["k"]: entry
        for entry in index_entries
        if entry.get("k")
    }
    scene_bindings_by_mission: dict[str, dict[str, dict]] = defaultdict(dict)
    for mission, refs in mission_level_refs.items():
        scene_targets = {
            entry["k"]
            for entry in index_entries
            if entry.get("m") == mission and entry.get("d") in SCENE_BINDING_TARGET_KINDS
        }
        if not scene_targets:
            continue

        processed_chain_levels: set[str] = set()
        for ref in refs:
            level_id = ref.get("levelId") or ""
            if not level_id:
                continue

            leveldata_path = ROOT / ref["file"]
            named_entries = _load_leveldata_named_entries(leveldata_path)
            if any(LT_BINDING_RE.match(entry["text"]) for entry in named_entries):
                levelscript_info = _load_levelscript_binding_data(level_id)
                binding_groups = _build_level_binding_groups(
                    named_entries,
                    levelscript_info["uidPayloads"],
                    dialog_scene_out_key,
                    mission,
                )
                for group in binding_groups:
                    group_scene_keys = {
                        payload["sceneKey"]
                        for row in group["rows"]
                        for payload in row.get("payloads") or []
                        if payload.get("sceneKey")
                    }
                    for scene_key in sorted(group_scene_keys & scene_targets):
                        scene_entry = scene_bindings_by_mission[mission].setdefault(
                            scene_key,
                            {"groups": [], "chains": []},
                        )
                        scene_entry["groups"].append({
                            "label": group["label"],
                            "levelId": level_id,
                            "hostType": ref.get("hostType") or "",
                            "levelKind": ref.get("kind") or "",
                            "levelDataFile": ref["file"],
                            "rows": group["rows"],
                            "_debug": {
                                "source": {
                                    "file": ref["file"],
                                    "levelId": level_id,
                                    "hostType": ref.get("hostType") or "",
                                    "kind": ref.get("kind") or "",
                                },
                            },
                        })

            if level_id in processed_chain_levels:
                continue
            processed_chain_levels.add(level_id)
            level_chain_map = _build_levelscript_scene_chain_map(level_id, dialog_scene_out_key, mission)
            for scene_key, chains in level_chain_map.items():
                if scene_key not in scene_targets:
                    continue
                scene_entry = scene_bindings_by_mission[mission].setdefault(
                    scene_key,
                    {"groups": [], "chains": []},
                )
                scene_entry["chains"].extend(chains)

    for mission, scene_map in scene_bindings_by_mission.items():
        for scene_key, scene_entry in scene_map.items():
            scene_entry["groups"].sort(
                key=lambda group: (
                    group.get("levelId") or "",
                    group.get("label") or "",
                    group.get("levelDataFile") or "",
                )
            )
            scene_entry["chains"].sort(
                key=lambda chain: (
                    chain.get("levelId") or "",
                    chain.get("file") or "",
                    (chain.get("steps") or [{}])[0].get("localId", 0),
                )
            )

            index_entry = index_entry_by_key.get(scene_key)
            if not index_entry:
                continue
            index_entry["x"] = merge_search_text(
                index_entry.get("x", ""),
                _scene_binding_search_text(scene_entry),
            )
            tags = index_entry.setdefault("tags", [])
            if "levelBinding" not in tags:
                tags.append("levelBinding")

    scene_env_talks_by_mission: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for mission, env_entries in story_env_entries_by_mission.items():
        scene_targets = {
            entry["k"]
            for entry in index_entries
            if entry.get("m") == mission and entry.get("d") in ("dlg", "misc")
        }
        if not scene_targets:
            continue

        scene_tracking: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: {"levels": set(), "proxies": set()}
        )
        if flow := load_mission_flow(mission):
            for quest in flow.get("quests") or []:
                quest_targets: list[str] = []
                for dialog_id in quest.get("dialogs") or []:
                    out_key = dialog_scene_out_key(dialog_id)
                    if out_key and out_key in scene_targets and out_key not in quest_targets:
                        quest_targets.append(out_key)
                if not quest_targets:
                    continue

                quest_levels = {
                    hint["scene"]
                    for hint in (quest.get("tracking") or [])
                    if hint.get("scene")
                }
                quest_proxies = {
                    hint["npcProxyId"]
                    for hint in (quest.get("tracking") or [])
                    if hint.get("npcProxyId")
                }
                for out_key in quest_targets:
                    scene_tracking[out_key]["levels"].update(quest_levels)
                    scene_tracking[out_key]["proxies"].update(quest_proxies)

        only_scene_target = next(iter(scene_targets)) if len(scene_targets) == 1 else ""

        for env_entry in env_entries:
            hints = env_entry.pop("_attachHints", None) or {}
            env_levels = set(hints.get("levels") or [])
            env_proxies = set(hints.get("proxies") or [])

            proxy_hits = {
                out_key
                for out_key, tracking in scene_tracking.items()
                if env_proxies and env_proxies & tracking["proxies"]
            }
            level_hits = {
                out_key
                for out_key, tracking in scene_tracking.items()
                if env_levels and env_levels & tracking["levels"]
            }

            target_key = ""
            binding_source: dict = {}
            if len(proxy_hits) == 1:
                target_key = next(iter(proxy_hits))
                binding_source = {
                    "mode": "npcProxyId",
                    "targetKey": target_key,
                    "matchedProxyIds": sorted(
                        env_proxies & scene_tracking[target_key]["proxies"]
                    ),
                    "candidateSceneKeys": sorted(proxy_hits),
                }
            elif not proxy_hits and len(level_hits) == 1:
                target_key = next(iter(level_hits))
                binding_source = {
                    "mode": "sceneLevel",
                    "targetKey": target_key,
                    "matchedLevels": sorted(
                        env_levels & scene_tracking[target_key]["levels"]
                    ),
                    "candidateSceneKeys": sorted(level_hits),
                }
            elif not proxy_hits and not level_hits and only_scene_target:
                target_key = only_scene_target
                binding_source = {
                    "mode": "onlySceneInMission",
                    "targetKey": target_key,
                }

            if not target_key:
                continue

            env_entry["_debug"]["sceneBinding"] = {"source": binding_source}
            scene_env_talks_by_mission[mission][target_key].append(env_entry)

            if env_index_entry := index_entry_by_key.get(env_entry.get("key") or ""):
                env_index_entry["attachTo"] = target_key

            index_entry = index_entry_by_key.get(target_key)
            if not index_entry:
                continue
            index_entry["x"] = merge_search_text(
                index_entry.get("x", ""),
                env_entry_search_text(env_entry),
            )
            tags = index_entry.setdefault("tags", [])
            if "envTalk" not in tags:
                tags.append("envTalk")

    mission_extras_payload: dict[str, dict] = {}
    for mission in sorted(
        set(scene_env_talks_by_mission)
        | set(scene_bindings_by_mission)
        | set(mission_note_by_mission)
        | set(mission_level_refs)
    ):
        extra: dict[str, list[dict]] = {}
        if mission in mission_note_by_mission:
            extra["notes"] = mission_note_by_mission[mission]
        if mission in mission_level_refs:
            extra["levelRefs"] = mission_level_refs[mission]
        if mission in scene_bindings_by_mission:
            extra["sceneBindings"] = {
                out_key: scene_bindings_by_mission[mission][out_key]
                for out_key in sorted(scene_bindings_by_mission[mission])
            }
        if mission in scene_env_talks_by_mission:
            extra["sceneEnvTalk"] = {
                out_key: scene_env_talks_by_mission[mission][out_key]
                for out_key in sorted(scene_env_talks_by_mission[mission])
            }
        mission_extras_payload[mission] = extra

    # Mission flow graphs from MissionRuntimeAsset. Story-gated dialog
    # ordering + choice-branches live here; pure-env ambient scenes do not.
    scene_keys_by_mission: dict[str, set[str]] = defaultdict(set)
    for entry in index_entries:
        if entry.get("d") in MISSION_SCENE_ENTRY_KINDS:
            scene_keys_by_mission[entry["m"]].add(entry["k"])
    present_index_missions = sorted({e["m"] for e in index_entries if e.get("m")})
    mission_variant_ids_by_parent: dict[str, list[str]] = defaultdict(list)
    for path in sorted(MRA_DIR.glob("*.json")):
        stem = path.stem
        if stem.endswith("_meta"):
            continue
        parent_mission = re.sub(r"d\d+$", "", stem)
        if parent_mission != stem and parent_mission in scene_keys_by_mission:
            mission_variant_ids_by_parent[parent_mission].append(stem)

    def resolve_scene_ref_out_key(raw_ref: str, available_scene_keys: set[str]) -> str:
        if not raw_ref:
            return ""
        for candidate in _unique_preserve([
            str(raw_ref or "").strip(),
            *_scene_ref_alias_candidates(raw_ref),
        ]):
            if not candidate:
                continue
            if candidate in available_scene_keys:
                return candidate
            if out_key := dialog_scene_out_key(candidate):
                if out_key in available_scene_keys:
                    return out_key
            if canonical_cutscene := _canonical_cutscene_key(candidate):
                if canonical_cutscene in available_scene_keys:
                    return canonical_cutscene
        return ""

    def quest_area_scene_refs(quest: dict, available_scene_keys: set[str]) -> list[str]:
        refs: list[str] = []
        for raw_ref in _quest_area_story_refs(quest):
            resolved = resolve_scene_ref_out_key(raw_ref, available_scene_keys)
            if resolved and resolved not in refs:
                refs.append(resolved)
        return refs

    def quest_leveldata_scene_refs(quest: dict, available_scene_keys: set[str]) -> list[str]:
        refs: list[str] = []
        for row in quest.get("levelDataStoryRefs") or []:
            raw_ref = row.get("storyRef") if isinstance(row, dict) else row
            resolved = resolve_scene_ref_out_key(raw_ref or "", available_scene_keys)
            if resolved and resolved not in refs:
                refs.append(resolved)
        return refs

    def flow_has_available_scene_ref(flow: dict | None, available_scene_keys: set[str]) -> bool:
        if not flow or not available_scene_keys:
            return False
        for quest in flow.get("quests") or []:
            for field_name in ("dialogs", "cutscenes", "remotecomms", "radios", "failStoryRefs"):
                for raw_ref in quest.get(field_name) or []:
                    if resolve_scene_ref_out_key(raw_ref, available_scene_keys):
                        return True
            if quest_area_scene_refs(quest, available_scene_keys):
                return True
            if quest_leveldata_scene_refs(quest, available_scene_keys):
                return True
            for proxy_ref in quest.get("proxyDialogs") or []:
                raw_ref = (
                    proxy_ref.get("dialogId")
                    if isinstance(proxy_ref, dict)
                    else proxy_ref
                )
                if resolve_scene_ref_out_key(raw_ref or "", available_scene_keys):
                    return True
        return False

    def mission_graph_flow(mission: str, flow: dict | None) -> dict | None:
        """Return the flow used only for scene-graph ordering.

        Some playable mission variants (`c16m4d5`, `e10m4d5`, etc.) carry
        MissionRuntime quest refs for parent story keys. The parent mission is
        where those story files live in the WebUI, so fold matching variant
        quests into the graph pass only when their refs resolve to actual
        parent nodes.
        """
        available = scene_keys_by_mission.get(mission, set())
        if not available:
            return flow
        variant_quests: list[dict] = []
        variant_missions: list[str] = []
        for variant_mission in mission_variant_ids_by_parent.get(mission) or []:
            variant_flow = load_mission_flow(variant_mission)
            if not flow_has_available_scene_ref(variant_flow, available):
                continue
            variant_missions.append(variant_mission)
            for quest in (variant_flow or {}).get("quests") or []:
                variant_quest = copy.deepcopy(quest)
                variant_quest["variantMission"] = variant_mission
                variant_quests.append(variant_quest)
        if not variant_quests:
            return flow
        graph_flow = copy.deepcopy(flow or {"quests": []})
        graph_flow["quests"] = [
            *list(graph_flow.get("quests") or []),
            *variant_quests,
        ]
        graph_flow["variantMissionIds"] = variant_missions
        return graph_flow


    def build_mission_scene_pins(
        flow: dict | None,
        available_scene_keys: set[str],
    ) -> dict[str, list[dict]]:
        if not flow or not available_scene_keys:
            return {}

        scene_rows: dict[str, dict[tuple, dict]] = defaultdict(dict)
        for quest in flow.get("quests") or []:
            # Prefer stronger authored/runtime scene refs for spatial pinning.
            # Radios are only used when a quest has no dialog/cutscene/remotecomm target.
            primary_scene_refs = _unique_preserve([
                *(
                    resolved
                    for dialog_id in (quest.get("dialogs") or [])
                    if (resolved := resolve_scene_ref_out_key(dialog_id, available_scene_keys))
                ),
                *(
                    resolved
                    for cutscene_id in (quest.get("cutscenes") or [])
                    if (resolved := resolve_scene_ref_out_key(cutscene_id, available_scene_keys))
                ),
                *(
                    resolved
                    for remote_id in (quest.get("remotecomms") or [])
                    if (resolved := resolve_scene_ref_out_key(remote_id, available_scene_keys))
                ),
            ])
            radio_scene_refs = _unique_preserve([
                resolved
                for radio_id in (quest.get("radios") or [])
                if (resolved := resolve_scene_ref_out_key(radio_id, available_scene_keys))
            ])
            area_scene_refs = quest_area_scene_refs(quest, available_scene_keys)
            scene_refs = primary_scene_refs or radio_scene_refs or area_scene_refs
            if len(scene_refs) != 1:
                continue
            scene_key = scene_refs[0]

            for pin in quest.get("pins") or []:
                position = pin.get("position") or {}
                key = (
                    pin.get("scene") or "",
                    pin.get("sourceType") or "",
                    pin.get("trackingType") or "",
                    pin.get("missionAreaId") or "",
                    pin.get("npcProxyId") or "",
                    round(float(position.get("x", 0.0)), 3),
                    round(float(position.get("y", 0.0)), 3),
                    round(float(position.get("z", 0.0)), 3),
                )
                row = scene_rows[scene_key].get(key)
                if row is None:
                    row = {
                        "scene": pin.get("scene") or "",
                        "sourceType": pin.get("sourceType") or "",
                        "trackingType": pin.get("trackingType") or "",
                        "position": {
                            "x": float(position.get("x", 0.0)),
                            "y": float(position.get("y", 0.0)),
                            "z": float(position.get("z", 0.0)),
                        },
                        "questIds": [],
                        "flowIndices": [],
                    }
                    if pin.get("missionAreaId"):
                        row["missionAreaId"] = pin["missionAreaId"]
                    if pin.get("npcProxyId"):
                        row["npcProxyId"] = pin["npcProxyId"]
                    if pin.get("radius") is not None:
                        row["radius"] = pin["radius"]
                    if pin.get("routePointCount") is not None:
                        row["routePointCount"] = pin["routePointCount"]
                    scene_rows[scene_key][key] = row
                quest_id = quest.get("id") or ""
                if quest_id and quest_id not in row["questIds"]:
                    row["questIds"].append(quest_id)
                flow_index = quest.get("flowIndex")
                if flow_index is not None and flow_index not in row["flowIndices"]:
                    row["flowIndices"].append(flow_index)

        return {
            scene_key: sorted(
                rows.values(),
                key=lambda row: (
                    min(row.get("flowIndices") or [10**9]),
                    row.get("scene") or "",
                    row.get("sourceType") or "",
                    row["position"]["x"],
                    row["position"]["z"],
                ),
            )
            for scene_key, rows in sorted(scene_rows.items())
            if rows
        }

    def build_mission_scene_graph(mission: str, flow: dict | None) -> dict | None:
        available = scene_keys_by_mission.get(mission, set())
        ui_nodes: set[str] = set()
        chain_nodes: set[str] = set()
        chain_sequences: list[dict] = []
        scene_chain_sequences: list[dict] = []
        story_call_items_by_file: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)
        seen_story_call_items: set[tuple[str, str, int, int, str]] = set()
        hash_terminal_contexts: list[dict] = []
        seen_hash_terminal_contexts: set[tuple] = set()
        if flow:
            for quest in flow.get("quests") or []:
                for hint in quest.get("tracking") or []:
                    jump_id = hint.get("jumpId") or ""
                    if jump_id:
                        ui_nodes.add(f"ui:{jump_id}")
        seen_chain_signatures: set[tuple[str, tuple[str, ...]]] = set()
        def compact_levelscript_step(step: dict, node_key: str, payload_text: str) -> dict:
            source_info = (step.get("_debug") or {}).get("source") or {}
            row = {
                "nodeKey": node_key,
                "payloadText": payload_text,
                "localId": step.get("localId"),
                "nextId": step.get("nextId"),
            }
            compact_source = {
                key: source_info.get(key)
                for key in ("layout", "code", "kind", "uid", "start")
                if source_info.get(key) not in (None, "", [], {})
            }
            if compact_source:
                row["source"] = compact_source
            return {
                key: value
                for key, value in row.items()
                if value not in (None, "", [], {})
            }

        for scene_entry in (scene_bindings_by_mission.get(mission) or {}).values():
            for chain in scene_entry.get("chains") or []:
                sequence: list[str] = []
                sequence_steps: list[dict] = []
                for step in chain.get("steps") or []:
                    source_info = (step.get("_debug") or {}).get("source") or {}
                    start = source_info.get("start")
                    if not isinstance(start, int):
                        start = 10**9
                    for payload_index, payload in enumerate(step.get("payloads") or []):
                        raw_text = str(payload.get("text") or "")
                        node_key = str(
                            resolve_scene_ref_out_key(raw_text, available)
                            or payload.get("nodeKey")
                            or _scene_graph_runtime_payload_key(
                                raw_text,
                                mission,
                                dialog_scene_out_key,
                            )
                        )
                        if not node_key:
                            continue
                        file_ref = chain.get("file") or ""
                        level_id = chain.get("levelId") or ""
                        if file_ref and _is_story_scene_graph_key(node_key, available):
                            signature = (file_ref, level_id, start, payload_index, node_key)
                            if signature not in seen_story_call_items:
                                seen_story_call_items.add(signature)
                                story_call_items_by_file[(file_ref, level_id)].append(
                                    (start, payload_index, node_key)
                                )
                        if not sequence or sequence[-1] != node_key:
                            sequence.append(node_key)
                            sequence_steps.append(
                                compact_levelscript_step(step, node_key, raw_text)
                            )
                if not sequence:
                    continue
                signature = (chain.get("file") or "", tuple(sequence))
                if signature in seen_chain_signatures:
                    continue
                seen_chain_signatures.add(signature)
                chain_nodes.update(sequence)
                scene_sequence = _compact_scene_graph_sequence(sequence, available)
                if scene_sequence:
                    scene_chain_sequences.append({
                        "file": chain.get("file") or "",
                        "levelId": chain.get("levelId") or "",
                        "sequence": scene_sequence,
                    })
                if len(sequence) < 2:
                    continue
                chain_sequences.append({
                    "file": chain.get("file") or "",
                    "levelId": chain.get("levelId") or "",
                    "sequence": sequence,
                })
                for pos, (src, dst) in enumerate(zip(sequence, sequence[1:])):
                    src_kind = _scene_graph_node_kind(src, available)
                    dst_kind = _scene_graph_node_kind(dst, available)
                    if src_kind == "levelscriptHash" and _is_story_scene_graph_kind(dst_kind):
                        scene_key = dst
                        hash_key = src
                        direction = "hash->story"
                    elif _is_story_scene_graph_kind(src_kind) and dst_kind == "levelscriptHash":
                        scene_key = src
                        hash_key = dst
                        direction = "story->hash"
                    else:
                        continue
                    file_ref = chain.get("file") or ""
                    level_id = chain.get("levelId") or ""
                    terminal_signature = (
                        file_ref,
                        level_id,
                        scene_key,
                        hash_key,
                        direction,
                        pos,
                    )
                    if terminal_signature in seen_hash_terminal_contexts:
                        continue
                    seen_hash_terminal_contexts.add(terminal_signature)
                    hash_terminal_contexts.append({
                        "kind": "levelscriptHashTerminal",
                        "file": file_ref,
                        "levelId": level_id,
                        "sceneKey": scene_key,
                        "hash": hash_key,
                        "direction": direction,
                        "sourceStep": sequence_steps[pos] if pos < len(sequence_steps) else {},
                        "hashStep": sequence_steps[pos + 1] if pos + 1 < len(sequence_steps) else {},
                    })
        story_call_contexts: list[dict] = []
        for (file_ref, level_id), items in sorted(story_call_items_by_file.items()):
            sequence: list[str] = []
            for _, __, node_key in sorted(items):
                if not sequence or sequence[-1] != node_key:
                    sequence.append(node_key)
            if sequence:
                story_call_contexts.append({
                    "kind": "levelscriptFileStoryCallOrder",
                    "file": file_ref,
                    "levelId": level_id,
                    "sequence": sequence,
                })
        all_nodes = set(available) | ui_nodes | chain_nodes
        if not all_nodes:
            return None

        mission_entries = [entry for entry in index_entries if entry.get("m") == mission]
        scene_file_order = build_mission_scene_file_order(
            mission_entries,
            flow,
        )
        mission_runtime_order_map = {
            str(key): int(value)
            for key, value in (scene_file_order.get("orderMap") or {}).items()
            if str(key)
        }
        fallback_order_map = infer_mission_dialog_order(
            mission,
            mission_entries,
            flow,
            mission_level_refs.get(mission),
        )
        order_map = dict(mission_runtime_order_map)
        fallback_base = (max(order_map.values()) + 1000) if order_map else 0
        for key, value in fallback_order_map.items():
            order_map.setdefault(key, fallback_base + value)
        node_entries = sorted(
            (entry for entry in mission_entries if entry.get("k") in available),
            key=lambda entry: (
                order_map.get(entry["k"], 10**9),
                entry.get("s", 10**9),
                entry.get("k") or "",
            ),
        )
        mission_entry_by_key = {
            entry["k"]: entry
            for entry in node_entries
            if entry.get("k")
        }

        edges_by_key: dict[tuple[str, str, str], dict] = {}

        def ensure_edge(src: str, dst: str, kind: str) -> dict | None:
            if not src or not dst or src == dst:
                return None
            if src not in all_nodes or dst not in all_nodes:
                return None
            edge = edges_by_key.get((src, dst, kind))
            if edge is None:
                edge = {"from": src, "to": dst, "kind": kind}
                edges_by_key[(src, dst, kind)] = edge
            return edge

        for source_edge in scene_file_order.get("edges") or []:
            edge = ensure_edge(
                source_edge.get("from") or "",
                source_edge.get("to") or "",
                source_edge.get("kind") or "questPrev",
            )
            if not edge:
                continue
            edge["source"] = source_edge.get("source") or scene_file_order.get("source")
            for quest_id in source_edge.get("questIds") or []:
                refs = edge.setdefault("questIds", [])
                if quest_id and quest_id not in refs:
                    refs.append(quest_id)

        if flow:
            quest_by_id = {
                quest.get("id") or "": quest
                for quest in flow.get("quests") or []
                if quest.get("id")
            }
            quest_scene_refs: dict[str, list[str]] = {}
            quest_scene_meta: dict[str, dict] = defaultdict(lambda: {
                "questIds": [],
                "rootQuestIds": [],
                "flowIndices": [],
            })
            quest_leveldata_refs: dict[str, list[str]] = {}

            def gather_upstream_scene_refs(quest_id: str, seen: set[str] | None = None) -> list[str]:
                if not quest_id:
                    return []
                if seen is None:
                    seen = set()
                if quest_id in seen:
                    return []
                seen.add(quest_id)
                scene_refs = quest_scene_refs.get(quest_id, [])
                if scene_refs:
                    return scene_refs
                out: list[str] = []
                for prev_id in (quest_by_id.get(quest_id) or {}).get("prev") or []:
                    for scene_ref in gather_upstream_scene_refs(prev_id, seen):
                        if scene_ref not in out:
                            out.append(scene_ref)
                return out

            script_scene_ref_cache: dict[tuple[str, str], list[str]] = {}

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
                            scene_ref = resolve_scene_ref_out_key(hit.get("text") or "", available)
                            if not scene_ref:
                                continue
                            hits.append((
                                record_start,
                                int(hit.get("offset") or record_start),
                                scene_ref,
                            ))
                refs = _unique_preserve([scene_ref for _, __, scene_ref in sorted(hits)])
                script_scene_ref_cache[cache_key] = refs
                return refs

            def quest_condition_script_scene_refs(quest: dict) -> list[str]:
                refs: list[str] = []
                default_scene_ids = list(quest.get("scenes") or [])
                for anchor in quest.get("objectiveAnchors") or []:
                    anchor_scene_ids = list(anchor.get("sceneIds") or default_scene_ids)
                    for script_id in normalized_script_ids(anchor.get("scriptIds")):
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

            def quest_field_scene_refs(quest: dict, field_name: str) -> list[str]:
                refs: list[str] = []
                for raw_ref in quest.get(field_name) or []:
                    resolved = resolve_scene_ref_out_key(raw_ref, available)
                    if resolved and resolved not in refs:
                        refs.append(resolved)
                return refs

            def add_leveldata_edge_meta(edge: dict, quest: dict, scene_refs: list[str]) -> None:
                quest_id = quest.get("id") or ""
                refs = edge.setdefault("questIds", [])
                if quest_id and quest_id not in refs:
                    refs.append(quest_id)
                scene_ref_set = set(scene_refs)
                for row in quest.get("levelDataStoryRefs") or []:
                    if not isinstance(row, dict):
                        continue
                    resolved = resolve_scene_ref_out_key(row.get("storyRef") or "", available)
                    if scene_ref_set and resolved not in scene_ref_set:
                        continue
                    file_ref = row.get("file") or ""
                    if file_ref:
                        source_files = edge.setdefault("sourceFiles", [])
                        if file_ref not in source_files:
                            source_files.append(file_ref)
                    level_id = row.get("levelId") or ""
                    if level_id:
                        level_ids = edge.setdefault("levelIds", [])
                        if level_id not in level_ids:
                            level_ids.append(level_id)
                    entity = row.get("entity") or ""
                    if entity:
                        entities = edge.setdefault("entities", [])
                        if entity not in entities:
                            entities.append(entity)
                    for field in row.get("fields") or []:
                        fields = edge.setdefault("fields", [])
                        if field and field not in fields:
                            fields.append(field)

            for quest in flow.get("quests") or []:
                proxy_dialog_refs: list[str] = []
                for proxy_ref in quest.get("proxyDialogs") or []:
                    raw_ref = (
                        proxy_ref.get("dialogId")
                        if isinstance(proxy_ref, dict)
                        else proxy_ref
                    )
                    resolved = resolve_scene_ref_out_key(raw_ref or "", available)
                    if resolved and resolved not in proxy_dialog_refs:
                        proxy_dialog_refs.append(resolved)
                scene_refs = _unique_preserve([
                    *quest_condition_script_scene_refs(quest),
                    *quest_field_scene_refs(quest, "dialogs"),
                    *proxy_dialog_refs,
                    *quest_field_scene_refs(quest, "cutscenes"),
                    *quest_field_scene_refs(quest, "remotecomms"),
                    *quest_field_scene_refs(quest, "radios"),
                    *quest_area_scene_refs(quest, available),
                ])
                quest_id = quest.get("id") or ""
                flow_index = quest.get("flowIndex", 0)
                leveldata_scene_refs = quest_leveldata_scene_refs(quest, available)
                if leveldata_scene_refs:
                    quest_leveldata_refs[quest_id] = leveldata_scene_refs
                if scene_refs:
                    quest_scene_refs[quest_id] = scene_refs
                    first_scene = scene_refs[0]
                    meta = quest_scene_meta[first_scene]
                    if quest_id and quest_id not in meta["questIds"]:
                        meta["questIds"].append(quest_id)
                    if isinstance(flow_index, int | float) and flow_index not in meta["flowIndices"]:
                        meta["flowIndices"].append(int(flow_index))
                    if quest_id and not (quest.get("prev") or []) and quest_id not in meta["rootQuestIds"]:
                        meta["rootQuestIds"].append(quest_id)
                for src, dst in zip(scene_refs, scene_refs[1:]):
                        if edge := ensure_edge(src, dst, "questSequence"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
                if leveldata_scene_refs:
                    sources = scene_refs[:]
                    if not sources:
                        for prev_id in quest.get("prev") or []:
                            for scene_ref in gather_upstream_scene_refs(prev_id):
                                if scene_ref not in sources:
                                    sources.append(scene_ref)
                    if sources:
                        src = _unique_preserve(sources)[-1]
                        if edge := ensure_edge(src, leveldata_scene_refs[0], "levelDataQuestRef"):
                            add_leveldata_edge_meta(edge, quest, leveldata_scene_refs[:1])
                    for src, dst in zip(leveldata_scene_refs, leveldata_scene_refs[1:]):
                        if edge := ensure_edge(src, dst, "levelDataQuestRef"):
                            add_leveldata_edge_meta(edge, quest, [src, dst])
                jump_nodes = [
                    f"ui:{hint.get('jumpId')}"
                    for hint in (quest.get("tracking") or [])
                    if hint.get("jumpId")
                ]
                sources = scene_refs[:]
                if not sources:
                    for prev_id in quest.get("prev") or []:
                        for scene_ref in gather_upstream_scene_refs(prev_id):
                            if scene_ref not in sources:
                                sources.append(scene_ref)
                    for jump_node in jump_nodes:
                        for src in _unique_preserve(sources):
                            if edge := ensure_edge(src, jump_node, "uiJump"):
                                refs = edge.setdefault("questIds", [])
                                if quest_id and quest_id not in refs:
                                    refs.append(quest_id)
            children_by_prev: dict[str, list[str]] = defaultdict(list)
            for quest in flow.get("quests") or []:
                child_id = quest.get("id") or ""
                for prev_id in quest.get("prev") or []:
                    if prev_id and child_id:
                        children_by_prev[prev_id].append(child_id)
            for quest in flow.get("quests") or []:
                quest_id = quest.get("id") or ""
                leveldata_scene_refs = quest_leveldata_refs.get(quest_id) or []
                if not leveldata_scene_refs:
                    continue
                for child_id in children_by_prev.get(quest_id) or []:
                    child_targets = (
                        quest_scene_refs.get(child_id)
                        or quest_leveldata_refs.get(child_id)
                        or []
                    )
                    if not child_targets:
                        continue
                    if edge := ensure_edge(
                        leveldata_scene_refs[-1],
                        child_targets[0],
                        "levelDataQuestRef",
                    ):
                        add_leveldata_edge_meta(edge, quest, leveldata_scene_refs[-1:])
            for quest in flow.get("quests") or []:
                quest_id = quest.get("id") or ""
                scene_refs = quest_scene_refs.get(quest_id, [])
                if not scene_refs:
                    continue
                first_scene = scene_refs[0]
                for prev_id in quest.get("prev") or []:
                    for prev_scene in gather_upstream_scene_refs(prev_id):
                        if edge := ensure_edge(prev_scene, first_scene, "questPrev"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
                            if prev_id and prev_id not in refs:
                                refs.append(prev_id)
                fail_scene_refs = _unique_preserve([
                    resolved
                    for raw_ref in (quest.get("failStoryRefs") or [])
                    if (resolved := resolve_scene_ref_out_key(raw_ref, available))
                ])
                guard_sources = scene_refs[-1:] or _unique_preserve([
                    upstream
                    for prev_id in quest.get("prev") or []
                    for upstream in gather_upstream_scene_refs(prev_id)
                ])
                for guard_src in guard_sources:
                    for fail_scene in fail_scene_refs:
                        if edge := ensure_edge(guard_src, fail_scene, "questFailGuard"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
        else:
            quest_scene_meta = defaultdict(lambda: {
                "questIds": [],
                "rootQuestIds": [],
                "flowIndices": [],
            })

        for scene_key, links in scene_graph_links_by_key.items():
            if scene_key not in available:
                continue
            for link in links:
                source_key = link.get("sourceKey") or ""
                for opt in link.get("options") or []:
                    option_id = opt.get("optionId") or ""
                    if first_scene := opt.get("firstSceneKey"):
                        if first_scene != scene_key:
                            if edge := ensure_edge(scene_key, first_scene, "authoredDirect"):
                                if option_id:
                                    edge.setdefault("optionIds", [])
                                    if option_id not in edge["optionIds"]:
                                        edge["optionIds"].append(option_id)
                                if source_key:
                                    edge.setdefault("sourceKeys", [])
                                    if source_key not in edge["sourceKeys"]:
                                        edge["sourceKeys"].append(source_key)
                    for submenu_scene in opt.get("submenuSceneKeys") or []:
                        if submenu_scene == scene_key or submenu_scene == opt.get("firstSceneKey"):
                            continue
                        if edge := ensure_edge(scene_key, submenu_scene, "authoredMenu"):
                            if option_id:
                                edge.setdefault("optionIds", [])
                                if option_id not in edge["optionIds"]:
                                    edge["optionIds"].append(option_id)
                            if source_key:
                                edge.setdefault("sourceKeys", [])
                                if source_key not in edge["sourceKeys"]:
                                    edge["sourceKeys"].append(source_key)

        for chain in chain_sequences:
            sequence = chain.get("sequence") or []
            for src, dst in zip(sequence, sequence[1:]):
                if edge := ensure_edge(src, dst, "levelscriptChain"):
                    file_ref = chain.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    level_id = chain.get("levelId") or ""
                    if level_id:
                        refs = edge.setdefault("levelIds", [])
                        if level_id not in refs:
                            refs.append(level_id)

        chain_start_meta: dict[str, dict] = defaultdict(lambda: {
            "sourceFiles": [],
            "levelIds": [],
            "positions": [],
        })
        for chain in scene_chain_sequences:
            sequence = chain.get("sequence") or []
            if sequence:
                first_scene = sequence[0]
                meta = chain_start_meta[first_scene]
                file_ref = chain.get("file") or ""
                if file_ref and file_ref not in meta["sourceFiles"]:
                    meta["sourceFiles"].append(file_ref)
                level_id = chain.get("levelId") or ""
                if level_id and level_id not in meta["levelIds"]:
                    meta["levelIds"].append(level_id)
                meta["positions"].append(0)
            for pos, (src, dst) in enumerate(zip(sequence, sequence[1:])):
                if edge := ensure_edge(src, dst, "levelscriptSceneChain"):
                    file_ref = chain.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    level_id = chain.get("levelId") or ""
                    if level_id:
                        refs = edge.setdefault("levelIds", [])
                        if level_id not in refs:
                            refs.append(level_id)
                    edge.setdefault("positions", [])
                    if pos not in edge["positions"]:
                        edge["positions"].append(pos)

        # Levelscript file-order edges (weak ordering hints).
        # File-order tokens within a single SerializeReference dump usually
        # track authored event flow even when the records aren't UID-linked,
        # so we mine every level the mission actually touches — including
        # levels that share a LevelData host file with another mission
        # (mission_level_refs misses these because it keys off filename).
        flow_level_ids: list[str] = []
        if re.match(r"^map\d+_lv\d+$", mission or "", re.I):
            flow_level_ids.append(mission)
        for candidate in [(flow or {}).get("level")] + [
            scene_id
            for quest in ((flow or {}).get("quests") or [])
            for scene_id in (quest.get("scenes") or [])
        ] + [ref.get("levelId") for ref in (mission_level_refs.get(mission) or [])] + [
            ref.get("levelId") for ref in (mission_leveldata_host_refs.get(mission) or [])
        ]:
            if candidate and candidate not in flow_level_ids:
                flow_level_ids.append(candidate)
        for level_id in flow_level_ids:
            for file_seq in _build_levelscript_file_order_scene_sequences(
                level_id, dialog_scene_out_key, mission
            ):
                filtered = [k for k in file_seq["sequence"] if k in available]
                if len(filtered) < 2:
                    continue
                for pos, (src, dst) in enumerate(zip(filtered, filtered[1:])):
                    if edge := ensure_edge(src, dst, "levelscriptFileOrder"):
                        file_ref = file_seq.get("file") or ""
                        if file_ref:
                            refs = edge.setdefault("sourceFiles", [])
                            if file_ref not in refs:
                                refs.append(file_ref)
                        seq_level_id = file_seq.get("levelId") or ""
                        if seq_level_id:
                            refs = edge.setdefault("levelIds", [])
                            if seq_level_id not in refs:
                                refs.append(seq_level_id)
                        edge.setdefault("positions", [])
                        if pos not in edge["positions"]:
                            edge["positions"].append(pos)
            for pair in _build_levelscript_cross_file_scene_pairs(
                level_id, dialog_scene_out_key, mission
            ):
                src = pair.get("src") or ""
                dst = pair.get("dst") or ""
                if src not in available or dst not in available:
                    continue
                if edge := ensure_edge(src, dst, "levelscriptCrossFileOrder"):
                    for key in ("fromFile", "toFile"):
                        file_ref = pair.get(key) or ""
                        if file_ref:
                            refs = edge.setdefault("sourceFiles", [])
                            if file_ref not in refs:
                                refs.append(file_ref)
                    pair_level_id = pair.get("levelId") or ""
                    if pair_level_id:
                        refs = edge.setdefault("levelIds", [])
                        if pair_level_id not in refs:
                            refs.append(pair_level_id)
                    stems = edge.setdefault("fileStems", [])
                    stem_pair = [pair.get("fromStem"), pair.get("toStem")]
                    if stem_pair not in stems:
                        stems.append(stem_pair)

        # PRTS collection rows expose authored page order inside a single
        # reading/collection item. Treat that as weak ordering only, and only
        # when each ordered slot maps to exactly one story node.
        prts_buckets: dict[str, dict[int, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
        for row_id, row in prts_all_items.items():
            if not isinstance(row, dict):
                continue
            first_lv_id = str(row.get("firstLvId") or "")
            order = row.get("order")
            content_id = str(row.get("contentId") or "")
            if not first_lv_id or not isinstance(order, int) or not content_id.startswith("text_"):
                continue
            suffix = content_id[len("text_"):]
            candidates = [
                key
                for key in (
                    f"dlg_{suffix}",
                    f"black_{suffix}",
                    f"misc_dlg_{suffix}",
                )
                if key in available
            ]
            if len(candidates) != 1:
                continue
            prts_buckets[first_lv_id][order].append((candidates[0], str(row_id)))
        for first_lv_id, order_map_by_bucket in prts_buckets.items():
            ordered_slots = [
                (order, rows[0])
                for order, rows in sorted(order_map_by_bucket.items())
                if len(rows) == 1
            ]
            if len(ordered_slots) < 2:
                continue
            for pos, ((_, (src, src_row)), (__, (dst, dst_row))) in enumerate(zip(ordered_slots, ordered_slots[1:])):
                if edge := ensure_edge(src, dst, "prtsCollectionOrder"):
                    edge["firstLvId"] = first_lv_id
                    refs = edge.setdefault("prtsRows", [])
                    for row_ref in (src_row, dst_row):
                        if row_ref and row_ref not in refs:
                            refs.append(row_ref)
                    edge.setdefault("positions", [])
                    if pos not in edge["positions"]:
                        edge["positions"].append(pos)

        # Radio-continuation edges (authored continueAfterDialog/Radio flags
        # combined with LevelScript file-offset adjacency, audited offline by
        # scripts/story_recovery/build_radio_continuation_audit.py). Silent
        # no-op when the audit report has not been generated yet.
        radio_cont_candidates = _load_radio_continuation_candidates_by_mission(
            str(_RADIO_CONTINUATION_REPORT_PATH)
        ).get(mission) or []
        for cand in radio_cont_candidates:
            predecessor = cand.get("predecessor") or ""
            radio = cand.get("radio") or ""
            if not predecessor or not radio:
                continue
            if predecessor not in available or radio not in available:
                continue
            if predecessor == radio:
                continue
            edge = ensure_edge(predecessor, radio, "radioContinuation")
            if not edge:
                continue
            file_ref = cand.get("file") or ""
            if file_ref:
                refs = edge.setdefault("sourceFiles", [])
                if file_ref not in refs:
                    refs.append(file_ref)
            level_id = cand.get("levelId") or ""
            if level_id:
                refs = edge.setdefault("levelIds", [])
                if level_id not in refs:
                    refs.append(level_id)
            match = cand.get("match") or ""
            if match:
                kinds = edge.setdefault("continuationKinds", [])
                if match not in kinds:
                    kinds.append(match)

        graph_order_map = _refine_scene_graph_order(
            all_nodes,
            list(edges_by_key.values()),
            order_map,
            available,
        )
        chained_node_keys: set[str] = {
            k
            for edge in edges_by_key.values()
            for k in (edge.get("from") or "", edge.get("to") or "")
            if k
        }
        mission_runtime_ordered_keys = set(mission_runtime_order_map)

        strong_order_edge_kinds = {
            "questSequence",
            "questPrev",
            "questFailGuard",
            "authoredDirect",
            "authoredMenu",
            "levelscriptSceneChain",
            # Authored continueAfterDialog/Radio flag combined with a
            # LevelScript file-offset adjacency is stronger than file-order
            # alone because the flag asserts the radio is meant to follow the
            # preceding dialog/radio.
            "radioContinuation",
        }
        weak_order_edge_kinds = {
            "levelscriptFileOrder",
            "levelscriptCrossFileOrder",
            "levelDataQuestRef",
            "prtsCollectionOrder",
        }
        strong_ordered_keys = set(mission_runtime_ordered_keys)
        weak_ordered_keys: set[str] = set()
        for edge in edges_by_key.values():
            kind = edge.get("kind") or ""
            if kind in strong_order_edge_kinds:
                target = strong_ordered_keys
            elif kind in weak_order_edge_kinds:
                target = weak_ordered_keys
            else:
                continue
            for node_key in (edge.get("from") or "", edge.get("to") or ""):
                if node_key:
                    target.add(node_key)

        def order_strength(node_key: str) -> str:
            if node_key in strong_ordered_keys:
                return "strong"
            if node_key in weak_ordered_keys:
                return "weak"
            return "unknown"

        nodes = [
            {
                "key": node_key,
                "kind": (
                    (mission_entry_by_key.get(node_key) or {}).get("d")
                    or _scene_graph_node_kind(node_key, available)
                ),
                "order": graph_order_map.get(node_key, -1),
                **(
                    {"orderSource": "MissionRuntimeAsset.questDic[*].prevQuestIdList"}
                    if node_key in mission_runtime_ordered_keys
                    else {}
                ),
                "orderStrength": order_strength(node_key),
                **(
                    {"orderConfirmed": False}
                    if node_key not in chained_node_keys and node_key not in mission_runtime_ordered_keys
                    else {}
                ),
            }
            for node_key in sorted(
                all_nodes,
                key=lambda key: (
                    graph_order_map.get(key, 10**9),
                    order_map.get(key, 10**9),
                    _scene_graph_node_kind(key, available),
                    key,
                ),
            )
        ]
        edges = sorted(
            edges_by_key.values(),
            key=lambda edge: (
                graph_order_map.get(edge["from"], 10**9),
                graph_order_map.get(edge["to"], 10**9),
                edge.get("kind") or "",
                edge["from"],
                edge["to"],
            ),
        )
        scene_entry = _detect_scene_graph_entries(
            nodes,
            edges,
            dict(quest_scene_meta),
            dict(chain_start_meta),
            order_map,
            graph_order_map,
            available,
        )
        payload = {"nodes": nodes, "edges": edges}
        if scene_entry:
            payload.update(scene_entry)
        if story_call_contexts:
            payload["levelscriptStoryCallContexts"] = story_call_contexts
        if hash_terminal_contexts:
            payload["levelscriptHashTerminals"] = hash_terminal_contexts
        if scene_file_order:
            payload["sceneFileOrder"] = {
                key: value
                for key, value in scene_file_order.items()
                if key != "orderMap"
            }
        return payload


    mission_flows_payload: dict[str, dict] = {}
    mission_scene_graphs: dict[str, dict] = {}
    for mission in present_index_missions:
        flow = load_mission_flow(mission)
        localized_flow = localize_mission_flow(flow)
        graph_flow = mission_graph_flow(mission, flow)
        scene_graph = build_mission_scene_graph(mission, graph_flow)
        if not localized_flow and not scene_graph:
            continue
        payload = {"quests": (localized_flow or {}).get("quests") or []}
        if localized_flow:
            referenced: set[str] = set()
            for q in localized_flow["quests"]:
                referenced.update(q.get("dialogs") or [])
                referenced.update(q.get("cutscenes") or [])
                referenced.update(q.get("remotecomms") or [])
                referenced.update(q.get("radios") or [])
            available = scene_keys_by_mission.get(mission, set())
            for q in localized_flow["quests"]:
                referenced.update(quest_area_scene_refs(q, available))
                referenced.update(quest_leveldata_scene_refs(q, available))
            unlinked = sorted(available - referenced)
            if localized_flow.get("level"):
                payload["level"] = localized_flow["level"]
            if unlinked:
                payload["unlinked"] = unlinked
            map_pins = build_mission_map_pins(localized_flow)
            if map_pins:
                payload["mapPins"] = map_pins
            scene_pins = build_mission_scene_pins(localized_flow, available)
            if scene_pins:
                payload["scenePins"] = scene_pins
        if scene_graph:
            payload["sceneGraph"] = scene_graph
            if graph_flow and graph_flow.get("variantMissionIds"):
                payload["sceneGraphVariantMissions"] = graph_flow["variantMissionIds"]
            mission_scene_graphs[mission] = scene_graph
        mission_flows_payload[mission] = payload

    mission_timeline_recovery_payload = build_mission_timeline_recovery_report(
        mission_scene_graphs,
        mission_flows=mission_flows_payload,
    )
    mission_timelines_by_mission = {
        mission.get("mission") or "": mission
        for mission in mission_timeline_recovery_payload.get("missions") or []
        if mission.get("mission")
    }
    mission_timeline_json = REPORTS_DIR / f"mission_timeline_recovery_{language_code}.json"
    mission_timeline_md = REPORTS_DIR / f"mission_timeline_recovery_{language_code}.md"
    write_mission_timeline_recovery_json(
        mission_timeline_json,
        mission_timeline_recovery_payload,
    )
    mission_timeline_md.parent.mkdir(parents=True, exist_ok=True)
    mission_timeline_md.write_text(
        render_mission_timeline_markdown(mission_timeline_recovery_payload),
        encoding="utf-8",
    )
    mission_timeline_report = {
        "json": repo_rel(mission_timeline_json),
        "markdown": repo_rel(mission_timeline_md),
        "summary": mission_timeline_recovery_payload["summary"],
        "evidencePolicy": MISSION_TIMELINE_EVIDENCE_POLICY,
    }


    mission_data_files: dict[str, str] = {}
    mission_data_bytes = 0
    mission_data_missions = sorted(
        set(mission_extras_payload)
        | set(mission_flows_payload)
        | set(mission_timelines_by_mission)
    )
    if mission_data_missions:
        mission_dir.mkdir(parents=True, exist_ok=True)
        used_mission_filenames: set[str] = set()
        for mission in mission_data_missions:
            filename = safe_mission_data_filename(mission, used_mission_filenames)
            rel_file = f"mission/{filename}"
            payload = {"mission": mission}
            if mission in mission_extras_payload:
                payload["extras"] = mission_extras_payload[mission]
            if mission in mission_flows_payload:
                payload["flow"] = mission_flows_payload[mission]
            if mission in mission_timelines_by_mission:
                payload["timelineRecovery"] = mission_timelines_by_mission[mission]
            out_path = write_mission_payload(rel_file, payload)
            mission_data_files[mission] = rel_file
            mission_data_bytes += out_path.stat().st_size

    generated = int(time.time())
    search_entries: list[dict] = []
    for entry in index_entries:
        search_text = str(entry.pop("x", "") or "").strip()
        if search_text:
            search_entries.append({
                "k": str(entry.get("k") or ""),
                "x": search_text,
            })

    write_json(out_dir / "actors.json", {
        "generated": generated,
        "language": language_code,
        "actorNames": actor_names,
    })
    write_json(out_dir / "missions.json", {
        "generated": generated,
        "language": language_code,
        "missionNames": mission_names,
    })
    write_json(out_dir / "search.json", {
        "generated": generated,
        "language": language_code,
        "entries": search_entries,
    })

    index_payload = {
        "generated": generated,
        "profile": profile,
        "actors": "actors.json",
        "missions": "missions.json",
        "search": "search.json",
        "entries": index_entries,
    }
    if write_reference and reference_stats:
        index_payload["reference"] = {
            "index": "reference/index.json",
            "stats": reference_stats,
        }
    if mission_data_files:
        index_payload["missionData"] = {
            "files": mission_data_files,
            "missions": len(mission_data_files),
            "bytes": mission_data_bytes,
        }
    index_payload["missionTimelineRecovery"] = mission_timeline_report
    if story_source_link_report:
        index_payload["storySourceLinks"] = {
            "sourceIndex": story_source_link_report.get("sourceIndex"),
            "summary": story_source_link_report.get("summary"),
            "report": story_source_link_report.get("report"),
        }
    if narrative_video_report:
        index_payload["narrativeVideos"] = {
            "summary": narrative_video_report.get("summary"),
            "report": narrative_video_report.get("report"),
        }
    if include_reference_in_story_index:
        index_payload["missionExtras"] = mission_extras_payload
        index_payload["missionFlows"] = mission_flows_payload
    write_json(out_dir / "index.json", index_payload)

    cleanup_stale_json(conv_dir, written_conv_paths)
    cleanup_stale_json(mission_dir, written_mission_paths)
    if write_reference:
        cleanup_stale_json(reference_dir, written_reference_paths)

    total_size = sum(p.stat().st_size for p in conv_dir.glob("*.json"))
    conv_count = len(list(conv_dir.glob("*.json")))
    index_path = out_dir / "index.json"
    scene_order_report = shared_write_scene_order_gap_reports(ROOT, REPORTS_DIR, language_code, conv_dir)
    inferred_anchor_report = shared_write_inferred_option_anchors_report(REPORTS_DIR, language_code, conv_dir)
    print(f"\n[{language_code}] Done in {time.time()-t0:.1f}s")
    print(f"  profile:       {profile}")
    print(f"  conversations: {len(index_entries)}")
    print(f"  actors:        {len(actor_names)}")
    print(f"  conv data:     {total_size/1024/1024:.1f} MB across {conv_count} files")
    if mission_data_files:
        print(f"  mission data:  {mission_data_bytes/1024/1024:.1f} MB across {len(mission_data_files)} files")
    print(
        "  mission timelines: "
        f"{mission_timeline_recovery_payload['summary']['missionCount']} missions, "
        f"{mission_timeline_recovery_payload['summary']['questCount']} quests"
    )
    if story_source_link_report:
        source_summary = story_source_link_report.get("summary") or {}
        print(
            "  source links:  "
            f"{source_summary.get('attachedKeys', 0)} keys, "
            f"{source_summary.get('attachedReferences', 0)} refs attached"
        )
    if narrative_video_report:
        video_summary = narrative_video_report.get("summary") or {}
        print(
            "  narrative vid: "
            f"{video_summary.get('attachedKeys', 0)} keys, "
            f"{video_summary.get('attachedVideos', 0)} refs attached"
        )
    if reference_stats:
        print(f"  reference:     {reference_stats.get('bytes', 0)/1024/1024:.1f} MB across {reference_stats.get('tables', 0)} tables")
    print(f"  index:         {index_path.stat().st_size/1024:.1f} KB")
    return {
        "language": language_code,
        "profile": profile,
        "conversations": len(index_entries),
        "actors": len(actor_names),
        "convBytes": total_size,
        "convFiles": conv_count,
        "missionDataBytes": mission_data_bytes,
        "missionDataFiles": len(mission_data_files),
        "missionTimelineRecoveryReport": mission_timeline_report["markdown"],
        "missionTimelineRecoveryData": mission_timeline_report["json"],
        "missionTimelineRecoveryMissions": mission_timeline_recovery_payload["summary"]["missionCount"],
        "missionTimelineRecoveryUnresolved": mission_timeline_recovery_payload["summary"].get("unresolvedByKind", {}),
        "referenceBytes": int(reference_stats.get("bytes", 0)) if reference_stats else 0,
        "referenceTables": int(reference_stats.get("tables", 0)) if reference_stats else 0,
        "referenceRows": int(reference_stats.get("rows", 0)) if reference_stats else 0,
        "indexBytes": index_path.stat().st_size,
        "sceneOrderGapReport": repo_rel(scene_order_report["markdown"]),
        "sceneOrderGapData": repo_rel(scene_order_report["json"]),
        "sceneOrderGapCount": scene_order_report["summary"]["totalFlaggedScenes"],
        "inferredOptionAnchorsReport": repo_rel(inferred_anchor_report["markdown"]),
        "inferredOptionAnchorsData": repo_rel(inferred_anchor_report["json"]),
        "inferredOptionAnchorsScenes": inferred_anchor_report["summary"]["totalScenes"],
        "inferredOptionAnchorsGroups": inferred_anchor_report["summary"]["totalInferredGroups"],
        "narrativeVideoReport": str((narrative_video_report.get("report") or {}).get("markdown") or ""),
        "narrativeVideoData": str((narrative_video_report.get("report") or {}).get("json") or ""),
        "narrativeVideoKeys": int((narrative_video_report.get("summary") or {}).get("attachedKeys", 0)),
        "narrativeVideoRefs": int((narrative_video_report.get("summary") or {}).get("attachedVideos", 0)),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
