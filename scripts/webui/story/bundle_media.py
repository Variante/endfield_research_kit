"""Pure media parsing and classification for localized Story bundles."""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection

from .bundle_primitives import clean_media_id_value, inline_image_tag


_INLINE_IMAGE_TAG_RE = re.compile(
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
    body_match = re.match(
        r"^<image\b(?!\s*=)[^>]*>([\s\S]*?)</image>$",
        raw,
        flags=re.IGNORECASE,
    )
    if body_match:
        return clean_media_id_value(body_match.group(1))
    quoted_direct = re.match(
        r'''^<image\s*=\s*(["'])([\s\S]*?)\1''',
        raw,
        flags=re.IGNORECASE,
    )
    if quoted_direct:
        return clean_media_id_value(quoted_direct.group(2))
    loose_direct = re.match(
        r"^<image\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE
    )
    if loose_direct:
        return clean_media_id_value(loose_direct.group(1))
    quoted_attr = re.search(
        r'''\b(?:src|source|path|name|id)\s*=\s*(["'])([\s\S]*?)\1''',
        raw,
        flags=re.IGNORECASE,
    )
    if quoted_attr:
        return clean_media_id_value(quoted_attr.group(2))
    loose_attr = re.search(
        r"\b(?:src|source|path|name|id)\s*=\s*([^>\s]+)",
        raw,
        flags=re.IGNORECASE,
    )
    return clean_media_id_value(loose_attr.group(1)) if loose_attr else ""


def image_ids_from_text(text: object) -> list[str]:
    source = str(text or "")
    if "<image" not in source.lower():
        return []
    return [
        image_id
        for image_id in (
            inline_image_id_from_tag(match.group(0))
            for match in _INLINE_IMAGE_TAG_RE.finditer(source)
        )
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


def media_id_looks_like_media(
    value: object,
    *,
    parse_mission: Callable[[str], tuple[str, int]],
    mission_story_types: Collection[str],
) -> bool:
    normalized = normalize_media_id(value)
    if not normalized or normalized.isdigit():
        return False
    mission_type, _mission_act = parse_mission(normalized)
    return mission_type not in mission_story_types


def sns_media_text_from_params(
    params: object,
    *,
    parse_mission: Callable[[str], tuple[str, int]],
    mission_story_types: Collection[str],
) -> str:
    image_ids = [
        str(value or "").strip()
        for value in (params or [])
        if media_id_looks_like_media(
            value,
            parse_mission=parse_mission,
            mission_story_types=mission_story_types,
        )
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


def collect_payload_media_tags(
    payload: dict,
    *,
    parse_mission: Callable[[str], tuple[str, int]],
    mission_story_types: Collection[str],
) -> set[str]:
    tags: set[str] = set()

    def add_media_id(value: object) -> None:
        if not media_id_looks_like_media(
            value,
            parse_mission=parse_mission,
            mission_story_types=mission_story_types,
        ):
            return
        normalized = normalize_media_id(value)
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
                    if key in {
                        "image",
                        "imageResPath",
                        "emoji",
                        "emojiResPath",
                        "optionResPath",
                    }:
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


__all__ = [
    "collect_payload_media_tags",
    "image_ids_from_text",
    "inline_image_id_from_tag",
    "media_id_is_emoji",
    "media_id_is_sticker",
    "media_id_looks_like_media",
    "normalize_media_id",
    "sns_media_text_from_params",
]
