from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from ..source_paths import _existing_unique_paths
except ImportError:
    from source_paths import _existing_unique_paths

from .context import (
    DEFAULT_LANGUAGE,
    I18N_FILE_RE,
    LANGUAGE_INFO,
    MISC_BUCKET_RE,
    PERSISTENT_TABLE_DIR,
    STORY_SOURCE_LINKS_PATH,
    STREAMING_TABLE_DIR,
    TABLE_DIR,
    TYPE_RE,
    _JSON_FILE_CACHE,
)
from .source_links import build_source_links

def discover_languages() -> list[str]:
    found: list[str] = []
    for table_dir in _existing_unique_paths([STREAMING_TABLE_DIR, PERSISTENT_TABLE_DIR]):
        for path in table_dir.glob("I18nTextTable_*.json"):
            match = I18N_FILE_RE.match(path.name)
            if match:
                found.append(match.group(1))
    return sorted(set(found))


def normalize_language_selection(raw_values: list[str] | None, available: list[str]) -> list[str]:
    if not raw_values:
        if DEFAULT_LANGUAGE in available:
            return [DEFAULT_LANGUAGE]
        return available

    selected: list[str] = []
    for raw in raw_values:
        for part in raw.split(","):
            code = part.strip().upper()
            if not code or code in selected:
                continue
            selected.append(code)

    unknown = [code for code in selected if code not in available]
    if unknown:
        raise SystemExit(
            "Unknown language code(s): "
            + ", ".join(unknown)
            + "\nAvailable: "
            + ", ".join(available)
        )
    return selected


def language_info(code: str) -> dict:
    info = LANGUAGE_INFO.get(code, {})
    return {
        "code": code,
        "label": info.get("label", code),
        "nativeLabel": info.get("nativeLabel", info.get("label", code)),
        "htmlLang": info.get("htmlLang", code.lower()),
        "uiLocale": info.get("uiLocale", "en"),
    }


def _read_json_with_size_log(path: Path, label: str | None = None):
    name = label or path.name
    print(f"  loading {name} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load(name: str) -> dict:
    return _read_json_with_size_log(TABLE_DIR / name, name)


def load_optional_table_json(table_dir: Path, name: str, label: str | None = None) -> dict:
    path = table_dir / name
    if not path.exists():
        return {}
    return load_json_path(path, label or name)


def load_json_path(path: Path, label: str | None = None) -> dict:
    cache_key = str(path)
    if cache_key in _JSON_FILE_CACHE:
        return _JSON_FILE_CACHE[cache_key]
    data = _read_json_with_size_log(path, label)
    _JSON_FILE_CACHE[cache_key] = data if isinstance(data, dict) else {}
    return _JSON_FILE_CACHE[cache_key]


def load_json_path_uncached(path: Path, label: str | None = None) -> dict:
    data = _read_json_with_size_log(path, label)
    return data if isinstance(data, dict) else {}


def load_story_source_links() -> dict[str, list[dict]]:
    """Load or build the language-independent story source-link index."""
    if not STORY_SOURCE_LINKS_PATH.exists():
        print("  building story source links")
        build_source_links(output=STORY_SOURCE_LINKS_PATH)
    if not STORY_SOURCE_LINKS_PATH.exists():
        return {}
    try:
        payload = load_json_path_uncached(STORY_SOURCE_LINKS_PATH, "story_source_links.json")
    except (OSError, json.JSONDecodeError):
        return {}
    links = payload.get("links") if isinstance(payload, dict) else {}
    if not isinstance(links, dict):
        return {}
    return {
        str(key): rows
        for key, rows in links.items()
        if key and isinstance(rows, list)
    }


def parse_mission(mission: str) -> tuple[str, int]:
    """Split 'a1m6d1' -> ('a', 1); 'c13m2d5' -> ('c', 13)."""
    if mission.startswith("blackbox"):
        return ("timeline", 0)
    if mission.startswith("sr_"):
        return ("f", 0)
    m = TYPE_RE.match(mission)
    if not m:
        return ("?", 0)
    return (m.group(1), int(m.group(2)) if m.group(2) else 0)


def scene_sort_value(scene: str | int) -> int:
    if isinstance(scene, int):
        return scene
    lead = re.match(r"\d+", str(scene or ""))
    return int(lead.group()) if lead else 0


# Map misc export buckets into browser mission nodes. Mission-shaped `dlg_*`
# buckets are slotted back into their real story missions/scenes, while broad
# utility buckets like `sim_*` and `timeline_*` are promoted to their own
# top-level tags with coarse mission labels underneath.
def slot_misc(bucket: str) -> tuple[str, int, str, int]:
    """Slot a misc bucket key into the mission timeline.

    Returns (type, act, mission, scene_num) used by the index. Many "misc"
    dialogs (e.g. `dlg_c13m3_3d5_001`) actually belong to a real story mission
    — they fail the strict DLG_RE only because the scene token contains a
    sub-scene like `3d5`. Slot them next to the regular dialogs/SNS so the
    user finds them in context. KIND_ORDER in app.js keeps them visually after
    sns/dlg within the same scene.

    Broad utility buckets are promoted to their own top-level tags. `sim_*`
    buckets become the "帝江号" tag with coarse child groups like `gift` and
    `talk`, while `timeline_*` buckets become the "模拟空间" tag and keep the
    remainder of the bucket key as their mission label.
    """
    if bucket.startswith("sim_"):
        rest = bucket[len("sim_"):]
        family = rest.split("_", 1)[0] if rest else "sim"
        return ("sim", 0, family, 0)
    if bucket.startswith("timeline_"):
        rest = bucket[len("timeline_"):]
        return ("timeline", 0, rest or "timeline", 0)
    if bucket.startswith("sr_"):
        return ("f", 0, bucket, 0)
    if bucket.startswith("dlg_"):
        rest = bucket[len("dlg_"):]
        m = MISC_BUCKET_RE.match(rest)
        if m:
            mission, scene_str = m.group(1), m.group(2)
            type_, act = parse_mission(mission)
            if type_ != "?":
                return (type_, act, mission, scene_sort_value(scene_str))
        type_, act = parse_mission(rest)
        if type_ != "?":
            return (type_, act, rest, 0)
    return ("x", 0, bucket, 0)


def preview(text: str, n: int = 60) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n]


def safe_mission_data_filename(mission_id: str, used_names: set[str]) -> str:
    """Allocate a stable, filesystem-safe mission JSON filename."""
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
    "discover_languages",
    "normalize_language_selection",
    "language_info",
    "load",
    "load_optional_table_json",
    "load_json_path",
    "load_json_path_uncached",
    "load_story_source_links",
    "parse_mission",
    "scene_sort_value",
    "slot_misc",
    "preview",
    "safe_mission_data_filename",
]
