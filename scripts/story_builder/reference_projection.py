"""Pure projection helpers for Story reference and collection payloads."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection

if __package__ in {"story_builder", "scripts.story_builder"}:
    from .bundle_primitives import brace_text
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.story_builder.reference_projection")


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
    return " ".join(
        word[:1].upper() + word[1:] if word else "" for word in raw.split(" ")
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


def collection_bucket_from_key(row_id: str) -> str:
    value = str(row_id or "")
    if not value:
        return "misc"
    if value.isupper() and "_" in value:
        parts = [part for part in value.split("_") if part]
        return "_".join(parts[:2]) if len(parts) >= 2 else parts[0]
    if "_" in value:
        parts = [part for part in value.split("_") if part]
        if len(parts) >= 2 and parts[0] in {
            "activity", "battle", "bp", "char", "chr", "dung", "item",
            "npc", "radio", "skill", "sns", "system", "task", "wiki",
        }:
            return "_".join(parts[:2])
        return parts[0]
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", value)
    if words:
        return "_".join(words[:2])
    return value[:24]


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


def collection_bucket_token(bucket: str) -> str:
    slug = collection_slug(bucket)
    checksum = sum((idx + 1) * ord(ch) for idx, ch in enumerate(str(bucket or ""))) % 104729
    return f"{slug}_{checksum:x}" if checksum else slug


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


collection_story_mission_pattern = re.compile(
    r"(?<![a-z0-9])((?:gm|sm|db|dm|[acefm])\d+(?:[a-z]\d+)*(?:d\d+)?)(?![a-z0-9])",
    re.IGNORECASE,
)
collection_map_pattern = re.compile(r"map\d+_lv\d+", re.IGNORECASE)


def collection_story_ref_from_identifiers(
    *values: str,
    parse_mission_id: Callable[[str], tuple[str, int]],
    mission_story_types: Collection[str],
) -> tuple[str, int, str] | None:
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
            type_key, _act = parse_mission_id(mission_id)
            if type_key in mission_story_types:
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


def collection_story_ref_from_bucket(
    bucket: str,
    *,
    parse_mission_id: Callable[[str], tuple[str, int]],
    mission_story_types: Collection[str],
) -> tuple[str, int, str] | None:
    candidates: set[str] = set()
    for match in collection_story_mission_pattern.finditer(str(bucket or "").lower()):
        mission_id = match.group(1)
        type_key, _act = parse_mission_id(mission_id)
        if type_key in mission_story_types:
            candidates.add(mission_id)
    if len(candidates) != 1:
        return None
    mission_id = next(iter(candidates))
    type_key, _act = parse_mission_id(mission_id)
    return (mission_id, 0, type_key)


def collection_source_label(table_source: str) -> str:
    return {
        "streaming": "StreamingAssets/Table",
        "persistent": "Persistent/Table",
    }.get(table_source, table_source)


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


def collection_text_fingerprint(text_nodes: list[dict]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for node in text_nodes:
        text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
        if text:
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


def responsive_summary_rows(
    label: str, values: list[str], *, chunk_size: int = 8
) -> list[dict]:
    tokens = [str(value) for value in values if str(value)]
    rows: list[dict] = []
    for idx, start in enumerate(range(0, len(tokens), chunk_size), start=1):
        prefix = label if idx == 1 else f"{label} (cont.)"
        rows.append({"text": f"{prefix}: {', '.join(tokens[start:start + chunk_size])}"})
    return rows


def sim_duplicate_actor_from_key(key: str) -> str:
    raw = str(key or "")
    if match := re.match(r"^misc_sim_(?:gift|talk|rest|work)_([^_]+)", raw):
        return str(match.group(1) or "").lower()
    if match := re.match(r"^env_greetEnvTalk_([^_]+)", raw):
        return str(match.group(1) or "").lower()
    return ""


def normalized_duplicate_line_texts(payload: dict) -> list[str]:
    out: list[str] = []
    for line in payload.get("lines") or []:
        text = " ".join(str(line.get("text") or "").split()).strip()
        if text:
            out.append(text)
    return out


__all__ = [
    "append_reference_line",
    "collection_bucket",
    "collection_bucket_from_key",
    "collection_bucket_token",
    "collection_display_name",
    "collection_hint_from_path",
    "collection_map_ref_from_identifiers",
    "collection_row_title",
    "collection_scene_suffix",
    "collection_scene_value",
    "collection_slug",
    "collection_source_label",
    "collection_story_ref_from_bucket",
    "collection_story_ref_from_identifiers",
    "collection_summary_rows",
    "collection_tags",
    "collection_table_name_tokens",
    "collection_text_fingerprint",
    "normalized_duplicate_line_texts",
    "normalized_reference_tags",
    "prts_archive_category_from_collection_ids",
    "prts_archive_category_from_identifier",
    "prts_archive_category_from_row",
    "prts_attachment_aliases",
    "reference_kind_from_tags",
    "reference_row_texts",
    "responsive_preview_values",
    "responsive_sort_values",
    "responsive_summary_rows",
    "sim_duplicate_actor_from_key",
]
