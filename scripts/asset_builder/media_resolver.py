"""Resolve Story and wiki media references against exported asset indexes."""
from __future__ import annotations

from dataclasses import dataclass
import html
import json
from pathlib import Path
import re
from typing import Iterable

try:
    from common import (
        normalize_posix,
        path_id_export_base_stem,
        path_id_export_path_id,
        rel_requires_path_id_export_name,
    )
except ModuleNotFoundError:  # imported as ``scripts.asset_builder``
    from scripts.common import (
        normalize_posix,
        path_id_export_base_stem,
        path_id_export_path_id,
        rel_requires_path_id_export_name,
    )


IMAGE_TOKEN_RE = re.compile(
    r"<image\b(?!\s*=)[^>]*>[\s\S]*?</image>"
    r"|<image\s*=[^>]+>"
    r"|<image\b(?=[^>]*(?:src|source|path|name|id)\s*=)[^>]*>",
    re.IGNORECASE,
)

ENV_EMOJI_PREFAB_ALIASES: dict[str, str] = {
    "envemoji_common_adaptationwork": "emoji_adaptationwork",
    "envemoji_common_dislike": "emoji_newdislike",
    "envemoji_common_empty": "emoji_empty",
    "envemoji_common_exhaustion": "emoji_exhaustion",
    "envemoji_common_happy": "emoji_newhappy",
    "envemoji_common_love": "emoji_love",
    "envemoji_common_newworkhard": "emoji_newworkhard",
    "envemoji_common_normal": "emoji_normal",
    "envemoji_common_sad": "emoji_newsad",
    "envemoji_common_sigh": "emoji_newsigh",
    "envemoji_common_surprise": "emoji_newsurprise",
    "envemoji_common_think": "emoji_think",
    "envemoji_common_thumbsup": "emoji_thumbsup",
    "envemoji_common_unhappywork": "emoji_unhappywork",
    "envemoji_common_workhard": "emoji_newworkhard",
}

ENV_EMOJI_PREFAB_LAYER_STEMS: dict[str, tuple[str, ...]] = {
    "emoji_adaptationwork": (
        "emoji_newbg",
        "emoji_workhardcircle",
        "emoji_workhardcircleblue",
        "emoji_newdeco",
        "emoji_workhardeye",
        "emoji_workhardeyeright",
        "emoji_workhardmouth",
    ),
    "emoji_newdislike": (
        "emoji_newbg",
        "emoji_unhappyworkcircle",
        "emoji_sigheyenew",
        "emoji_newdislike_mouth",
    ),
    "emoji_newworkhard": (
        "emoji_newbg",
        "emoji_unhappyworkcircle",
        "emoji_newworkhard_deco",
        "emoji_newworkhard_deco1",
        "emoji_newworkhard_deco2",
    ),
    "emoji_empty": (
        "emoji_newbg",
        "emoji_surprisecircle",
        "emoji_emptyeye",
    ),
    "emoji_exhaustion": (
        "emoji_exhaustioncircle",
        "emoji_exhaustioneye",
        "emoji_exhaustionmouth",
    ),
    "emoji_love": (
        "emoji_love",
        "emoji_circle_1",
        "emoji_circle",
    ),
    "emoji_newhappy": (
        "emoji_newbg",
        "emoji_circle_1",
        "emoji_newhappyeye",
        "emoji_happymouth",
    ),
    "emoji_newsad": (
        "emoji_newbg",
        "emoji_newsad_circle",
        "emoji_newsad_eye",
        "emoji_newsad_deco",
        "emoji_newsad_decobg",
    ),
    "emoji_newsigh": (
        "emoji_newbg",
        "emoji_sighcirclenew",
        "emoji_sigheyenew",
        "emoji_sighmouthnew",
    ),
    "emoji_newsurprise": (
        "emoji_newbg",
        "emoji_circle_1",
        "emoji_newsurpriseeyebg",
        "emoji_happyeye",
        "emoji_surprisemouthnew",
    ),
    "emoji_normal": (
        "emoji_newbg",
        "emoji_circle_1",
        "emoji_circle",
        "emoji_happyeye",
    ),
    "emoji_think": (
        "emoji_workhardcircle",
        "emoji_workhardcircleblue",
        "emoji_thinkpoint",
    ),
    "emoji_thumbsup": (
        "emoji_newbg",
        "emoji_unhappyworkcircle",
        "emoji_hand_2",
        "emoji_hand_1",
    ),
    "emoji_unhappywork": (
        "emoji_newbg",
        "emoji_unhappyworkcircle",
        "emoji_circle_1",
        "emoji_unhappyworkcircle_1",
        "emoji_newdeco",
        "emoji_sigheyenew",
    ),
}

ENV_EMOJI_FALLBACK_LAYER_STEMS: dict[str, tuple[str, ...]] = {}


@dataclass(frozen=True)
class AssetCandidate:
    rel: str
    name: str
    stem: str
    score: int
    entry: dict


def clean_inline_image_id_value(value: str) -> str:
    text = html.unescape(str(value or "")).strip()
    text = text.replace(r"\"", '"').replace(r"\'", "'")
    for _ in range(3):
        unwrapped = re.sub(r'^[\'"]+|[\'"]+$', "", text).strip()
        if unwrapped == text:
            break
        text = unwrapped
    return text


def normalize_inline_image_id(value: str) -> str:
    trimmed = clean_inline_image_id_value(value).replace("\\", "/")
    if not trimmed:
        return ""
    without_prefix = re.sub(r"^SNS/Emoji/", "", trimmed, flags=re.IGNORECASE)
    last_segment = without_prefix.split("/")[-1] or without_prefix
    return re.sub(r"\.[^.]+$", "", last_segment, flags=re.IGNORECASE).lower()


def inline_image_number_key(value: str) -> str:
    match = re.search(r"(?:^|[_-])(\d{1,3})$", str(value or ""))
    return str(int(match.group(1))) if match else ""


def resolve_env_emoji_prefab_key(value: str) -> str:
    normalized = normalize_inline_image_id(value)
    aliased = ENV_EMOJI_PREFAB_ALIASES.get(normalized, normalized)
    return aliased if aliased in ENV_EMOJI_PREFAB_LAYER_STEMS else ""


def extract_inline_image_id_from_tag(raw_tag: str) -> str:
    raw = str(raw_tag or "").strip()
    if not raw:
        return ""
    body_match = re.match(r"^<image\b(?!\s*=)[^>]*>([\s\S]*?)</image>$", raw, flags=re.IGNORECASE)
    if body_match:
        return clean_inline_image_id_value(body_match.group(1))
    quoted_direct = re.match(r'''^<image\s*=\s*(["'])([\s\S]*?)\1''', raw, flags=re.IGNORECASE)
    if quoted_direct:
        return clean_inline_image_id_value(quoted_direct.group(2))
    loose_direct = re.match(r"^<image\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
    if loose_direct:
        return clean_inline_image_id_value(loose_direct.group(1))
    quoted_attr = re.search(
        r'''\b(?:src|source|path|name|id)\s*=\s*(["'])([\s\S]*?)\1''',
        raw,
        flags=re.IGNORECASE,
    )
    if quoted_attr:
        return clean_inline_image_id_value(quoted_attr.group(2))
    loose_attr = re.search(r"\b(?:src|source|path|name|id)\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
    return clean_inline_image_id_value(loose_attr.group(1)) if loose_attr else ""


def _story_roots(webui_root: Path, *, missions: bool) -> list[Path]:
    names = ("conv", "mission") if missions else ("conv",)
    roots = [webui_root / "data" / name for name in names]
    lang_root = webui_root / "data" / "lang"
    if lang_root.exists():
        for lang_dir in sorted(path for path in lang_root.iterdir() if path.is_dir()):
            roots.extend(lang_dir / name for name in names)
    return roots


def _json_files(root: Path, pattern: str) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob(pattern)) if root.exists() else []


def collect_inline_image_ids(webui_root: Path) -> set[str]:
    """Collect normalized image IDs from files the Story UI renders as rich text."""
    image_ids: set[str] = set()
    for root in _story_roots(webui_root, missions=True):
        for path in _json_files(root, "*.json"):
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in IMAGE_TOKEN_RE.finditer(text):
                image_id = normalize_inline_image_id(extract_inline_image_id_from_tag(match.group(0)))
                if image_id:
                    image_ids.add(image_id)
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue

            def visit_media_fields(node: object) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key in {"image", "emoji", "emojiResPath", "optionResPath"}:
                            image_id = normalize_inline_image_id(str(value or ""))
                            if image_id:
                                image_ids.add(image_id)
                        elif key == "images" and isinstance(value, list):
                            for item in value:
                                image_id = normalize_inline_image_id(str(item or ""))
                                if image_id:
                                    image_ids.add(image_id)
                        elif isinstance(value, (dict, list)):
                            visit_media_fields(value)
                elif isinstance(node, list):
                    for item in node:
                        visit_media_fields(item)

            visit_media_fields(payload)
    return image_ids


def wiki_media_candidate_ids(value: object) -> list[str]:
    normalized = normalize_inline_image_id(str(value or ""))
    if not normalized:
        return []
    ids: list[str] = []

    def push(image_id: str) -> None:
        key = normalize_inline_image_id(image_id)
        if key and key not in ids:
            ids.append(key)

    push(normalized)
    if normalized.startswith("wiki_"):
        push(normalized[len("wiki_") :])
    if normalized.startswith("wiki_item_"):
        push(f"item_{normalized[len('wiki_item_') :]}")
    elif normalized.startswith("wiki_wpn_"):
        push(f"wpn_{normalized[len('wiki_wpn_') :]}")
    elif normalized.startswith("wiki_eny_"):
        push(f"eny_{normalized[len('wiki_eny_') :]}")
    for prefix in (
        "sketch_guide_video_",
        "guide_video_",
        "wiki_video_tut_adv_",
        "wiki_video_",
        "video_",
    ):
        if not normalized.startswith(prefix):
            continue
        suffix = normalized[len(prefix) :]
        if not suffix:
            continue
        push(suffix)
        push(f"image_{suffix}")
        push(f"wiki_pic_{suffix}")
        push(f"guide_pic_{suffix}")
        for index in range(1, 6):
            push(f"guide_pic_{suffix}_{index}")
            push(f"wiki_pic_{suffix}_{index}")
    return ids


def collect_wiki_media_image_ids(webui_root: Path) -> set[str]:
    """Collect exact image IDs inferred by the runtime wiki media resolver."""
    image_ids: set[str] = set()

    def add(value: object) -> None:
        image_ids.update(wiki_media_candidate_ids(value))

    for root in _story_roots(webui_root, missions=False):
        for path in _json_files(root, "wiki_*.json"):
            if "__pycache__" in path.parts:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("kind") != "wiki":
                continue
            debug_source = ((payload.get("_debug") or {}).get("source") or {}).get("source") or {}
            if isinstance(debug_source, dict):
                add(debug_source.get("refItemId"))
                add(debug_source.get("refMonsterTemplateId"))
            for line in payload.get("lines") or []:
                if not isinstance(line, dict):
                    continue
                source = (line.get("_debug") or {}).get("source") or {}
                if not isinstance(source, dict):
                    continue
                add(source.get("image"))
                add(source.get("video"))
                for ref_id in source.get("refWikiEntryIds") or []:
                    add(ref_id)
    return image_ids


def collect_wiki_video_refs(webui_root: Path) -> set[tuple[str, str]]:
    """Collect wiki tutorial video IDs and preferred device variants."""
    refs: set[tuple[str, str]] = set()
    for root in _story_roots(webui_root, missions=False):
        for path in _json_files(root, "wiki_*.json"):
            if "__pycache__" in path.parts:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict) or payload.get("kind") != "wiki":
                continue
            for line in payload.get("lines") or []:
                if not isinstance(line, dict):
                    continue
                source = (line.get("_debug") or {}).get("source") or {}
                if not isinstance(source, dict):
                    continue
                video_id = normalize_inline_image_id(str(source.get("video") or ""))
                if video_id:
                    refs.add((video_id, str(source.get("videoDeviceType") or "")))
    return refs


def video_device_folders(device_type: str) -> tuple[str, ...]:
    normalized = str(device_type or "").strip().lower()
    if normalized in {"mouseandkeyboard", "pc"}:
        return ("PC", "Common")
    if normalized in {"controller", "ct"}:
        return ("CT", "Common")
    if normalized in {"touch", "mobile", "mb"}:
        return ("CT", "Common", "PC")
    return ("Common", "PC", "CT")


def is_browser_playable_video(rel: str) -> bool:
    return re.search(r"\.(?:mp4|webm|ogv|ogg|mov|m4v)$", str(rel or ""), flags=re.IGNORECASE) is not None


def score_wiki_video_asset(rel: str, device_type: str = "") -> int:
    rel_normalized = normalize_posix(rel)
    rel_lower = rel_normalized.lower()
    score = 1
    for index, folder in enumerate(video_device_folders(device_type)):
        if f"/guide/{folder.lower()}/" in rel_lower:
            score += 100 - index * 10
            break
    if is_browser_playable_video(rel_normalized):
        score += 40
    if rel_lower.startswith(("streamingassets-structured/", "persistent-structured/")):
        score += 10
    elif rel_lower.startswith("raw_vfs/"):
        score += 1
    return score


def score_inline_image_asset(rel: str, stem: str) -> int:
    rel_lower = str(rel or "").lower()
    score = 1
    if "/sprite/" in rel_lower:
        score += 40
    elif "/texture2d/" in rel_lower:
        score += 20
    if stem.startswith("deco_sns_tweet_decorate_"):
        score += 140
    elif stem.startswith("bg_sns_tweet_decorate_"):
        score += 120
    elif stem.startswith("sns_sticker_"):
        score += 90
    elif stem.startswith("emoji_"):
        score += 60
    elif "sns" in stem:
        score += 40
    elif "emoji" in stem:
        score += 30
    return score


def _remember_best(mapping: dict[str, AssetCandidate], key: str, candidate: AssetCandidate) -> None:
    if not key:
        return
    current = mapping.get(key)
    if current is None or candidate.score > current.score or (
        candidate.score == current.score and candidate.rel < current.rel
    ):
        mapping[key] = candidate


def is_sns_inline_image_stem(stem: str) -> bool:
    normalized = str(stem or "").lower()
    return "sns" in normalized or "emoji" in normalized


def is_standalone_sns_media_id(value: str) -> bool:
    normalized = normalize_inline_image_id(value)
    return normalized.startswith(
        ("sns_image_", "sns_sticker_", "cg_image_", "deco_sns_tweet_decorate_", "bg_sns_tweet_decorate_")
    )


def sns_image_fallback_asset_stems(value: str) -> tuple[str, ...]:
    normalized = normalize_inline_image_id(value)
    if not normalized.startswith("sns_image_"):
        return ()
    suffix = normalized[len("sns_image_") :]
    match = re.match(r"^(.+)_(\d+)_([mf])$", suffix)
    if not match:
        return ()
    base, index, gender = match.groups()
    return (
        f"reading_{base}_photo_{gender}",
        f"read_{base}_{index}_{gender}",
        f"reading_{base}_{index}_{gender}",
    )


def media_lookup_stem(rel: str) -> tuple[str, str] | None:
    name = normalize_posix(rel).split("/")[-1] or rel
    stem = re.sub(r"\.[^.]+$", "", name, flags=re.IGNORECASE).lower()
    base_stem = path_id_export_base_stem(stem).lower()
    path_id = path_id_export_path_id(stem)
    if rel_requires_path_id_export_name(rel):
        return (base_stem, path_id) if base_stem else None
    return base_stem or stem, path_id


def is_story_emoji_asset(rel: str) -> bool:
    rel_normalized = normalize_posix(rel).lower()
    stem_info = media_lookup_stem(rel_normalized)
    if stem_info is None:
        return False
    stem = stem_info[0]
    return (
        stem.startswith("emoji_")
        or stem.startswith("sns_emoji_")
        or "/emoji/" in rel_normalized
        or "/sns/emoji/" in rel_normalized
    )


def build_inline_image_lookup(
    entries: Iterable[dict],
) -> tuple[dict[str, AssetCandidate], dict[str, AssetCandidate]]:
    by_stem: dict[str, AssetCandidate] = {}
    by_number: dict[str, AssetCandidate] = {}
    for raw in entries:
        if not raw or raw.get("k") != "image" or not raw.get("r"):
            continue
        rel = normalize_posix(str(raw.get("r") or ""))
        if not rel:
            continue
        stem_info = media_lookup_stem(rel)
        if stem_info is None:
            continue
        stem, path_id = stem_info
        if not stem:
            continue
        candidate = AssetCandidate(
            rel=rel,
            name=rel.split("/")[-1] or rel,
            stem=stem,
            score=score_inline_image_asset(rel, stem),
            entry=raw,
        )
        if path_id:
            candidate.entry.setdefault("pid", path_id)
        _remember_best(by_stem, stem, candidate)
        number_key = inline_image_number_key(stem)
        if number_key and is_sns_inline_image_stem(stem):
            _remember_best(by_number, number_key, candidate)
    return by_stem, by_number


def build_video_lookup(entries: Iterable[dict]) -> dict[str, list[AssetCandidate]]:
    by_stem: dict[str, list[AssetCandidate]] = {}
    for raw in entries:
        if not raw or raw.get("k") != "video" or not raw.get("r"):
            continue
        rel = normalize_posix(str(raw.get("r") or ""))
        if not rel:
            continue
        stem_info = media_lookup_stem(rel)
        if stem_info is None:
            continue
        stem, path_id = stem_info
        if not stem:
            continue
        candidate = AssetCandidate(
            rel=rel,
            name=rel.split("/")[-1] or rel,
            stem=stem,
            score=score_wiki_video_asset(rel),
            entry=raw,
        )
        if path_id:
            candidate.entry.setdefault("pid", path_id)
        by_stem.setdefault(stem, []).append(candidate)
    for candidates in by_stem.values():
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.rel))
    return by_stem


def resolve_inline_image_assets(
    image_id: str,
    by_stem: dict[str, AssetCandidate],
    by_number: dict[str, AssetCandidate],
) -> list[AssetCandidate]:
    normalized = normalize_inline_image_id(image_id)
    if not normalized:
        return []
    matches: dict[str, AssetCandidate] = {}

    def add(candidate: AssetCandidate | None) -> None:
        if candidate:
            matches[candidate.rel] = candidate

    for stem in (normalized, f"{normalized}_m", f"{normalized}_f"):
        add(by_stem.get(stem))
    prefab_key = resolve_env_emoji_prefab_key(normalized)
    if prefab_key:
        for stem in ENV_EMOJI_PREFAB_LAYER_STEMS.get(prefab_key, ()):
            add(by_stem.get(stem))
        return list(matches.values())
    for stem in ENV_EMOJI_FALLBACK_LAYER_STEMS.get(normalized, ()):
        add(by_stem.get(stem))
    for stem, candidate in by_stem.items():
        if stem.startswith(f"{normalized}_"):
            add(candidate)
    if normalized.startswith("sns_image_"):
        sns_suffix = normalized[len("sns_image_") :]
        add(by_stem.get(f"cg_image_{sns_suffix}"))
        if not matches:
            for stem in sns_image_fallback_asset_stems(normalized):
                candidate = by_stem.get(stem)
                if candidate:
                    add(candidate)
                    break
    if matches and is_standalone_sns_media_id(normalized):
        return list(matches.values())
    number_key = inline_image_number_key(normalized)
    if number_key:
        padded2 = number_key.zfill(2)
        for stem in (
            f"deco_sns_tweet_decorate_{padded2}",
            f"bg_sns_tweet_decorate_{padded2}",
            f"sns_sticker_{padded2}",
            f"emoji_02_{number_key.zfill(3)}",
            f"emoji_01_{number_key.zfill(3)}",
        ):
            add(by_stem.get(stem))
        add(by_number.get(number_key))
    return list(matches.values())


def resolve_exact_image_assets(
    image_id: str,
    by_stem: dict[str, AssetCandidate],
) -> list[AssetCandidate]:
    normalized = normalize_inline_image_id(image_id)
    if not normalized:
        return []
    matches: dict[str, AssetCandidate] = {}
    for stem in (normalized, f"{normalized}_m", f"{normalized}_f"):
        candidate = by_stem.get(stem)
        if candidate:
            matches[candidate.rel] = candidate
    return list(matches.values())


def wiki_video_candidate_stems(video_id: str) -> list[str]:
    normalized = normalize_inline_image_id(video_id)
    if not normalized:
        return []
    stems: list[str] = []

    def push(stem: str) -> None:
        key = normalize_inline_image_id(stem)
        if key and key not in stems:
            stems.append(key)

    push(normalized)
    if normalized.endswith("_mb"):
        base = normalized[:-3]
        push(f"{base}_ct")
        push(base)
        push(f"{base}_pc")
    elif normalized.endswith(("_ct", "_pc")):
        push(re.sub(r"_(?:ct|pc)$", "", normalized, flags=re.IGNORECASE))
    return stems


def resolve_exact_video_asset(
    video_id: str,
    device_type: str,
    by_stem: dict[str, list[AssetCandidate]],
) -> AssetCandidate | None:
    candidates_by_rel: dict[str, AssetCandidate] = {}
    for stem in wiki_video_candidate_stems(video_id):
        for candidate in by_stem.get(stem) or []:
            candidates_by_rel[candidate.rel] = candidate
    if not candidates_by_rel:
        return None
    return sorted(
        candidates_by_rel.values(),
        key=lambda candidate: (-score_wiki_video_asset(candidate.rel, device_type), candidate.rel),
    )[0]
