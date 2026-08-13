from __future__ import annotations

from .context import *

def clean_media_id_value(value: object) -> str:
    text = html.unescape(str(value or "")).strip()
    text = text.replace(r"\"", '"').replace(r"\'", "'")
    for _ in range(3):
        unwrapped = re.sub(r'^[\'"]+|[\'"]+$', "", text).strip()
        if unwrapped == text:
            break
        text = unwrapped
    return text

def written_path_key(path: Path) -> str:
    return str(path).lower()

def norm_id(id_value) -> str:
    if id_value is None:
        return ""
    s = str(id_value)
    return "" if s == "0" else s

def pick_fields(obj: dict | None, *keys: str) -> dict:
    if not obj:
        return {}
    return {k: obj.get(k) for k in keys if k in obj}

def source_ref(table: str, row_id: str, source: dict, **extra) -> dict:
    out = {
        "table": table,
        "rowId": row_id,
        "source": source,
    }
    for k, v in extra.items():
        if is_present(v):
            out[k] = v
    return out

def inline_image_tag(image_id: str) -> str:
    clean = str(image_id or "").strip()
    return f'<image="{clean}">' if clean else ""

def text_sequence_fingerprint(nodes: list[dict]) -> tuple[str, ...]:
    rows: list[str] = []
    for node in nodes:
        text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
        if text:
            rows.append(text)
    return tuple(rows)

def brace_text(text: str) -> str:
    """Return the content inside the first {...} when present."""
    if not text:
        return ""
    m = re.search(r"\{([^{}]+)\}", text)
    return m.group(1) if m else text

def sns_raw_title(out_key: str) -> str:
    """Show `foo_...` instead of the stored `sns_foo_...` key."""
    return out_key[4:] if out_key.startswith("sns_") else out_key

def normalize_blackbox_id(value: str) -> str:
    mission_id = re.sub(r"\s+", "", value or "")
    alias_prefixes = {
        "blackbox_storage": "blackbox_storager",
        "blackbox_xiranite_oven": "blackbox_xiraniteoven",
    }
    for src, dst in alias_prefixes.items():
        if mission_id == src or mission_id.startswith(f"{src}_"):
            return f"{dst}{mission_id[len(src):]}"
    return mission_id

def norm_template_id(value: str) -> str:
    if value.startswith("npc_tpl_"):
        return value[len("npc_tpl_"):]
    return value

def icon_basename(icon_path: str) -> str:
    if not icon_path:
        return ""
    return icon_path.rsplit("/", 1)[-1]

def env_group(env_id: str) -> str:
    """Bucket ambient-talk ids into browser groups."""
    if env_id.startswith("greetEnvTalk"):
        return "greetEnvTalk"
    if env_id.startswith("envEmoji"):
        return "envEmoji"
    if env_id.startswith("charGiftTalkid"):
        return "charGiftTalkid"
    m = re.match(r"^envTalk_([^_]+(?:_lv\d+(?:_env)?)?)(?:_|$)", env_id)
    if m:
        token = m.group(1)
        if token.startswith("base") and re.match(r"^base\d+_lv\d+(?:_env)?$", token):
            return "map" + token[len("base"):]
        return token
    return "envTalk"

def env_story_mission(env_id: str, known_missions: set[str]) -> str:
    """Return the mission bucket encoded by an env-talk id when possible.

    Supports both story-shaped ids like `envTalk_e0m2_7` and map/base ids
    like `envTalk_map01_lv001_env_11` or `envTalk_base01_lv001_env_11`.
    """
    direct = re.match(r"^envTalk_([^_]+)(?:_|$)", env_id)
    if direct:
        mission = direct.group(1)
        if mission in known_missions:
            return mission

    map_like = re.match(r"^envTalk_((?:map|base)\d+_lv\d+(?:_env)?)_\d+$", env_id)
    if not map_like:
        return ""

    mission = map_like.group(1)
    if mission in known_missions:
        return mission
    if mission.startswith("base"):
        mapped = "map" + mission[len("base"):]
        if mapped in known_missions:
            return mapped
    return ""

def line_haystack(lines: list[dict], *fields: str) -> str:
    parts: list[str] = []
    for line in lines:
        for field in fields:
            value = line.get(field)
            if value:
                parts.append(str(value))
    return " ".join(parts)

def line_identity_haystack(lines: list[dict]) -> str:
    parts: list[str] = []
    for line in lines:
        line_id = line.get("id")
        if line_id:
            parts.append(str(line_id))
        cid = line.get("cid")
        if cid is not None and cid != "":
            parts.append(f"cid:{cid}")
    return " ".join(parts)

def line_option_haystack(lines: list[dict]) -> str:
    parts: list[str] = []
    for line in lines:
        for option in line.get("options") or []:
            if not isinstance(option, dict):
                continue
            for field in ("id", "optionId", "text", "image", "emoji"):
                value = option.get(field)
                if value:
                    parts.append(str(value))
    return " ".join(parts)

def parse_level_ref_name(name: str) -> dict | None:
    if not name.endswith(".json"):
        return None
    stem = name[:-5]
    marker = "_lv_data_sub_"
    if marker not in stem:
        return None
    level_id, rest = stem.split(marker, 1)
    kind = "plain"
    if rest.startswith("mission_"):
        kind = "mission"
        rest = rest[len("mission_") :]
    rest = rest.lstrip("_")
    if not level_id or not rest:
        return None
    token = re.sub(r"_v[0-9A-Za-z]+$", "", rest)
    return {
        "level": level_id,
        "kind": kind,
        "token": token,
    }

def level_host_type(level_id: str) -> str:
    if level_id.startswith(("map", "base")):
        return "map"
    if level_id.startswith("dung"):
        return "dungeon"
    if level_id.startswith("indie"):
        return "indie"
    if level_id.startswith("blackbox"):
        return "blackbox"
    return "other"

def merge_search_text(base: str, extra: str) -> str:
    base = base.strip()
    extra = extra.strip()
    if not base:
        return extra
    if not extra:
        return base
    return f"{base} {extra}"

def format_webui_timeline_seconds(value: float) -> str:
    seconds = max(0.0, float(value))
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes}:{remaining:04.1f}"

def graph_fragments_text(fragments: list[dict]) -> str:
    parts: list[str] = []
    for fragment in fragments or []:
        if fragment.get("sourceKey"):
            parts.append(str(fragment["sourceKey"]))
        if fragment.get("lineIds"):
            parts.extend(str(line_id) for line_id in fragment["lineIds"] if line_id)
        terminals = fragment.get("terminalCounts") or {}
        for label, count in terminals.items():
            if count:
                parts.append(f"{label}:{count}")
        for group in fragment.get("optionGroups") or []:
            if group.get("after"):
                parts.append(str(group["after"]))
            parts.extend(str(opt_id) for opt_id in group.get("optionIds") or [] if opt_id)
            for branch_lines in (group.get("branches") or {}).values():
                parts.extend(str(line_id) for line_id in branch_lines if line_id)
            parts.extend(
                str(line_id)
                for line_id in (group.get("merge") or {}).values()
                if line_id
            )
    return " ".join(parts)

def scene_links_text(links: list[dict]) -> str:
    parts: list[str] = []
    for link in links or []:
        if link.get("sourceKey"):
            parts.append(str(link["sourceKey"]))
        if link.get("after"):
            parts.append(str(link["after"]))
        for opt in link.get("options") or []:
            if opt.get("optionId"):
                parts.append(str(opt["optionId"]))
            if opt.get("firstLineId"):
                parts.append(str(opt["firstLineId"]))
            if opt.get("firstSceneKey"):
                parts.append(str(opt["firstSceneKey"]))
            if opt.get("terminal"):
                parts.append(str(opt["terminal"]))
            if opt.get("outcomeKind"):
                parts.append(str(opt["outcomeKind"]))
            loop = opt.get("loop") or {}
            if isinstance(loop, dict):
                if loop.get("kind"):
                    parts.append(str(loop["kind"]))
                parts.extend(str(scene_key) for scene_key in (loop.get("sceneKeys") or []) if scene_key)
            parts.extend(str(line_id) for line_id in (opt.get("pathLineIds") or []) if line_id)
            parts.extend(str(scene_key) for scene_key in (opt.get("sceneKeys") or []) if scene_key)
            parts.extend(str(scene_key) for scene_key in (opt.get("submenuSceneKeys") or []) if scene_key)
            for target in opt.get("submenuTargets") or []:
                if not isinstance(target, dict):
                    continue
                parts.extend(
                    str(target.get(key) or "")
                    for key in ("sceneKey", "optionId", "text")
                    if target.get(key)
                )
    return " ".join(parts)

def scene_link_option_payload(raw_option: dict) -> dict:
    entry = {
        "optionId": raw_option.get("optionId") or "",
    }
    for key in ("firstLineId", "firstSceneKey", "terminal"):
        if raw_option.get(key):
            entry[key] = raw_option[key]
    for key in ("pathLineIds", "sceneKeys", "submenuSceneKeys"):
        if raw_option.get(key):
            entry[key] = raw_option[key]
    if raw_option.get("conditionalOutcomes"):
        entry["conditionalOutcomes"] = raw_option["conditionalOutcomes"]
    if raw_option.get("loop"):
        entry["loop"] = raw_option["loop"]
    if raw_option.get("outcomeKind"):
        entry["outcomeKind"] = raw_option["outcomeKind"]
    if raw_option.get("_debug"):
        entry["_debug"] = raw_option["_debug"]
    return entry







def append_reference_line(
    lines: list[dict],
    seen_texts: set[tuple[str, str, str]],
    line_id: str,
    text: str,
    *,
    hint: str = "",
    actor: str = "",
    aid: str = "",
    debug: dict | None = None,
) -> None:
    normalized = (text or "").strip()
    if not normalized:
        return
    key = (hint, actor, normalized)
    if key in seen_texts:
        return
    seen_texts.add(key)
    line = {"id": line_id, "text": normalized}
    if hint:
        line["hint"] = hint
    if actor:
        line["actor"] = actor
    if aid:
        line["aid"] = aid
    if debug:
        line["_debug"] = debug
    lines.append(line)

def reference_kind_from_tags(tags: list[str] | None = None) -> str:
    for tag in tags or []:
        value = str(tag or "")
        if value.startswith("table_"):
            return value
    return "wiki"

def normalized_reference_tags(tags: list[str] | None, mission_id: str) -> list[str]:
    move_to_other = {"loadingTip", "task", "tip"}
    normalized_mission_id = str(mission_id or "").lower()
    if normalized_mission_id.startswith("wiki_collection_"):
        move_to_other.update({"collection", "worldtext"})
    if normalized_mission_id == "snschattable":
        move_to_other.add("snsChat")
    out: list[str] = []
    for raw_tag in tags or ["wiki"]:
        tag = str(raw_tag or "")
        if not tag:
            continue
        if tag in move_to_other:
            tag = "other"
        if tag not in out:
            out.append(tag)
    return out or ["wiki"]

def collection_slug(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z]+", "_", str(value or ""))
    return value.strip("_").lower() or "misc"

def collection_display_name(value: str) -> str:
    raw = str(value or "").strip().replace("_", " ")
    if not raw:
        return "Misc"
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.isupper():
        return raw
    words = raw.split(" ")
    return " ".join(word[:1].upper() + word[1:] if word else "" for word in words)

def collection_bucket_from_key(row_id: str) -> str:
    value = str(row_id or "")
    if not value:
        return "misc"
    if value.isupper() and "_" in value:
        parts = [part for part in value.split("_") if part]
        return "_".join(parts[:2]) if len(parts) >= 2 else parts[0]
    if "_" in value:
        parts = [part for part in value.split("_") if part]
        if len(parts) >= 2 and parts[0] in {"activity", "battle", "bp", "char", "chr", "dung", "item", "npc", "radio", "skill", "sns", "system", "task", "wiki"}:
            return "_".join(parts[:2])
        return parts[0]
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", value)
    if words:
        return "_".join(words[:2])
    return value[:24]

def collection_scene_suffix(value: str) -> int:
    match = re.search(r"_(\d+)$", str(value or ""))
    return int(match.group(1)) if match else 0

def collection_scene_value(row: dict | None, fallback: int = 0) -> int:
    if not isinstance(row, dict):
        return fallback
    for field in ("order", "sortId", "sortOrder", "level", "priority", "stage", "step", "index"):
        value = row.get(field)
        if isinstance(value, int | float):
            return int(value)
    return fallback

def collection_source_label(table_source: str) -> str:
    return {
        "streaming": "StreamingAssets/Table",
        "persistent": "Persistent/Table",
    }.get(table_source, table_source)

def collection_text_fingerprint(text_nodes: list[dict]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for node in text_nodes:
        text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
        if not text:
            continue
        rows.append((str(node.get("field") or ""), text))
    return tuple(rows)

def collection_table_name_tokens(table_name: str) -> list[str]:
    stem = table_name.removesuffix(".json")
    return [
        token.lower()
        for token in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", stem)
        if token
    ]

def reference_row_texts(text_nodes: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for node in text_nodes:
        raw = node.get("raw") if isinstance(node, dict) else None
        item = {
            "field": str(node.get("field") or "text"),
            "path": str(node.get("path") or "$"),
            "text": str(node.get("text") or ""),
        }
        if node.get("hint"):
            item["hint"] = str(node["hint"])
        if isinstance(raw, dict) and raw.get("id") is not None:
            item["i18nId"] = str(raw.get("id"))
        rows.append(item)
    return rows

def prts_attachment_aliases(value: str) -> set[str]:
    raw = str(value or "").strip()
    if not raw:
        return set()
    aliases = {raw}
    lowered = raw.lower()
    if lowered.startswith("prts_") and lowered.endswith("_sns"):
        aliases.add(f"sns_{raw[5:-4]}")
    if lowered.startswith("reading_") and lowered.endswith("_sns"):
        aliases.add(f"sns_{raw[8:-4]}")
    return aliases

def responsive_sort_values(values: set[str] | list[str]) -> list[str]:
    tokens = [str(value) for value in values if str(value)]
    return sorted(
        tokens,
        key=lambda value: (0, int(value)) if value.lstrip("-").isdigit() else (1, value),
    )

def responsive_preview_values(values: list[str], *, limit: int = 4) -> str:
    tokens = [str(value) for value in values if str(value)]
    if not tokens:
        return ""
    if len(tokens) <= limit:
        return ", ".join(tokens)
    return ", ".join(tokens[:limit]) + f" +{len(tokens) - limit}"

def responsive_summary_rows(label: str, values: list[str], *, chunk_size: int = 8) -> list[dict]:
    tokens = [str(value) for value in values if str(value)]
    rows: list[dict] = []
    for idx, start in enumerate(range(0, len(tokens), chunk_size), start=1):
        prefix = label if idx == 1 else f"{label} (cont.)"
        rows.append({"text": f"{prefix}: {', '.join(tokens[start:start + chunk_size])}"})
    return rows

def sim_duplicate_actor_from_key(key: str) -> str:
    raw = str(key or "")
    if m := re.match(r"^misc_sim_(?:gift|talk|rest|work)_([^_]+)", raw):
        return str(m.group(1) or "").lower()
    if m := re.match(r"^env_greetEnvTalk_([^_]+)", raw):
        return str(m.group(1) or "").lower()
    return ""

def normalized_duplicate_line_texts(payload: dict) -> list[str]:
    out: list[str] = []
    for line in payload.get("lines") or []:
        text = " ".join(str(line.get("text") or "").split()).strip()
        if text:
            out.append(text)
    return out

def compact_narrative_video_ref(ref: dict) -> dict:
    compact = {
        "name": str(ref.get("name") or ""),
        "rel": str(ref.get("rel") or ""),
        "source": str(ref.get("source") or ""),
        "format": str(ref.get("format") or ""),
        "size": int(ref.get("size") or 0),
        "stem": str(ref.get("stem") or ""),
        "baseStem": str(ref.get("baseStem") or ""),
        "kind": str(ref.get("kind") or ""),
        "_debug": {
            "source": {
                "rel": str(ref.get("rel") or ""),
                "source": str(ref.get("source") or ""),
                "name": str(ref.get("name") or ""),
                "kind": str(ref.get("kind") or ""),
                "keyCandidates": list(ref.get("keyCandidates") or []),
            },
        },
    }
    if ref.get("gender"):
        compact["gender"] = str(ref["gender"])
        compact["_debug"]["source"]["gender"] = str(ref["gender"])
    if ref.get("resolvedKey"):
        compact["_debug"]["source"]["resolvedKey"] = str(ref["resolvedKey"])
    binding = ref.get("binding")
    if isinstance(binding, dict):
        compact["binding"] = binding
        compact["_debug"]["source"]["binding"] = binding
    definition = ref.get("definition")
    if isinstance(definition, dict):
        compact["definition"] = definition
        compact["_debug"]["source"]["definition"] = definition
    if ref.get("authoritativeKeys"):
        compact["_debug"]["source"]["authoritativeKeys"] = list(ref["authoritativeKeys"])
    attachment_override = ref.get("attachmentOverride")
    if isinstance(attachment_override, dict):
        compact["_debug"]["source"]["attachmentOverride"] = attachment_override
    return compact

def narrative_video_sort_key(ref: dict) -> tuple:
    source = str(ref.get("source") or "")
    fmt = str(ref.get("format") or "")
    source_rank = {
        "StreamingAssets-structured": 0,
        "Persistent-structured": 1,
        "raw_vfs": 2,
    }.get(source, 9)
    format_rank = {
        "mp4": 0,
        "webm": 1,
        "ogv": 2,
        "mov": 3,
        "m4v": 4,
        "avi": 5,
        "usm": 6,
    }.get(fmt, 9)
    gender = str(ref.get("gender") or "")
    gender_rank = {"": 0, "m": 1, "f": 2}.get(gender, 9)
    return (
        str(ref.get("baseStem") or ""),
        gender_rank,
        format_rank,
        source_rank,
        str(ref.get("rel") or ""),
    )

def narrative_video_search_text(refs: list[dict]) -> str:
    parts: list[str] = []
    for ref in refs:
        for field in ("name", "rel", "source", "stem", "baseStem", "gender", "format", "kind"):
            value = ref.get(field)
            if value:
                parts.append(str(value))
    return " ".join(parts)

def narrative_video_index_summary(refs: list[dict]) -> dict:
    source_counts = Counter(str(ref.get("source") or "") for ref in refs)
    format_counts = Counter(str(ref.get("format") or "") for ref in refs)
    names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
    return {
        "n": len(refs),
        "sources": {
            key: source_counts[key]
            for key in sorted(source_counts)
            if key
        },
        "formats": {
            key: format_counts[key]
            for key in sorted(format_counts)
            if key
        },
        "files": names[:5],
    }

def build_mission_map_pins(flow: dict | None) -> list[dict]:
    if not flow:
        return []
    merged: dict[tuple, dict] = {}
    for quest in flow.get("quests") or []:
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
            row = merged.get(key)
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
                merged[key] = row
            quest_id = quest.get("id") or ""
            if quest_id and quest_id not in row["questIds"]:
                row["questIds"].append(quest_id)
            flow_index = quest.get("flowIndex")
            if flow_index is not None and flow_index not in row["flowIndices"]:
                row["flowIndices"].append(flow_index)
    return sorted(
        merged.values(),
        key=lambda row: (
            min(row.get("flowIndices") or [10**9]),
            row.get("scene") or "",
            row.get("sourceType") or "",
            row["position"]["x"],
            row["position"]["z"],
        ),
    )

def build_mission_timeline_recovery_report(
    scene_graphs: dict[str, dict],
    mission_flows: dict[str, dict] | None = None,
) -> dict:
    timeline_index, timeline_meta = load_mission_timeline_index(
        timeline_recovery_order_out(EXPORT_ROOT)
    )
    recovered: list[dict] = []
    files = mission_timeline_files(MRA_DIR, set()) if MRA_DIR.is_dir() else []
    script_condition_ownership = build_mission_script_condition_ownership(files)
    mission_flows = mission_flows or {}
    for path in files:
        mission_id = path.stem
        recovered.append(
            recover_source_mission_timeline(
                path,
                timeline_index,
                None,
                source_backed_scene_edges_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                source_backed_story_call_contexts_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                source_backed_hash_terminals_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                source_backed_call_server_callbacks_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                script_condition_ownership=script_condition_ownership,
                mission_flow=mission_flows.get(mission_id),
            )
        )
    return {
        "evidencePolicy": MISSION_TIMELINE_EVIDENCE_POLICY,
        "summary": summarize_mission_timeline_recovery(
            recovered,
            timeline_meta,
            generated_by="scripts/story_builder/build.py",
        ),
        "missions": recovered,
    }

def safe_mission_data_filename(mission_id: str, used_names: set[str]) -> str:
    stem = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(mission_id or "")).strip("._")
    if not stem:
        stem = "mission"
    name = f"{stem}.json"
    if name.lower() not in used_names:
        used_names.add(name.lower())
        return name
    index = 2
    while True:
        candidate = f"{stem}_{index}.json"
        if candidate.lower() not in used_names:
            used_names.add(candidate.lower())
            return candidate
        index += 1

__all__ = [
    "clean_media_id_value",
    "written_path_key",
    "norm_id",
    "pick_fields",
    "source_ref",
    "inline_image_tag",
    "text_sequence_fingerprint",
    "brace_text",
    "sns_raw_title",
    "normalize_blackbox_id",
    "norm_template_id",
    "icon_basename",
    "env_group",
    "env_story_mission",
    "line_haystack",
    "line_identity_haystack",
    "line_option_haystack",
    "parse_level_ref_name",
    "level_host_type",
    "merge_search_text",
    "format_webui_timeline_seconds",
    "graph_fragments_text",
    "scene_links_text",
    "scene_link_option_payload",
    "append_reference_line",
    "reference_kind_from_tags",
    "normalized_reference_tags",
    "collection_slug",
    "collection_display_name",
    "collection_bucket_from_key",
    "collection_scene_suffix",
    "collection_scene_value",
    "collection_source_label",
    "collection_text_fingerprint",
    "collection_table_name_tokens",
    "reference_row_texts",
    "prts_attachment_aliases",
    "responsive_sort_values",
    "responsive_preview_values",
    "responsive_summary_rows",
    "sim_duplicate_actor_from_key",
    "normalized_duplicate_line_texts",
    "compact_narrative_video_ref",
    "narrative_video_sort_key",
    "narrative_video_search_text",
    "narrative_video_index_summary",
    "build_mission_map_pins",
    "build_mission_timeline_recovery_report",
    "safe_mission_data_filename",
]



