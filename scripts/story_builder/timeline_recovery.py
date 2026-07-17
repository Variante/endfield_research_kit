"""Recover dialog line order from Unity Timeline assets in one pass.

This module is the canonical Timeline recovery pipeline for the WebUI Story
build:

1. Discover AnimeStudio CLI AssetMaps under export_full/recovered/AnimeStudio-cli.
2. Select dialog Timeline asset folders in a general way (`dlgtl_*`, `f_dlgtl_*`,
   and `m_dlgtl_*` under gameplay/dialog/timeline).
3. Prefer the full AnimeStudio MonoBehaviour JSON export when it already
   contains the needed Timeline tracks and is small enough to scan cheaply.
4. Fall back to filtered AnimeStudio CLI `--filter_data` exports for focused
   diagnostics or when the full export has no recoverable Timeline tracks.

The main output is:
  export_full/recovered/AnimeStudio-cli/timeline_line_orders.json

`scripts/story_builder/build.py` imports that JSON directly when present, using
line clips for conversation order and option clips/bindings for authored choice
placement.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "export_full"
DEFAULT_RECOVERY_ROOT = EXPORT_ROOT / "recovered" / "AnimeStudio-cli"
DEFAULT_EXTRACT_DIR = DEFAULT_RECOVERY_ROOT / "timeline_extract"
DEFAULT_ORDER_OUT = DEFAULT_RECOVERY_ROOT / "timeline_line_orders.json"

TIMELINE_CONTAINER_RE = re.compile(r"(?:^|/)timeline/(?P<stem>(?:[fm]_)?dlgtl_[^/]+)(?:/|$)", re.IGNORECASE)
TIMELINE_STEM_RE = re.compile(r"^(?:[fm]_)?dlgtl_.+(?:_sub_\d+|_\d+)$", re.IGNORECASE)
TIMELINE_SUB_NAME_RE = re.compile(r"^(?P<timeline>(?:[fm]_)?dlgtl_.+?_sub_\d+)(?:_|$)")
TIMELINE_NO_SUB_NAME_RE = re.compile(r"^(?P<timeline>(?:[fm]_)?dlgtl_.+_\d+)(?:_|$)")
TIMELINE_ROOT_NAME_TAIL_RE = re.compile(
    r"^(?:_(?:copy|\d+))?_Actor$",
    re.IGNORECASE,
)
DIALOG_TIMELINE_WALK_RE = re.compile(
    r"^(?:Common|FemaleOnly|MaleOnly)$|Dialog Trunk Track|Runtime Jump Track|"
    r"Dialog Skeletal Morph Track|^Option(?:\s|\d|$)",
    re.IGNORECASE,
)
LINE_ID_RE = re.compile(r"^.+_\d+(?:_\d+)?$")
IGNORED_DISPLAY_PREFIXES = ("option_", "au_", "audio_", "bgm_", "se_")
OPTION_ID_PREFIX = "option_dlg_"
META_PATH_ID_RE = re.compile(r'"pathId"\s*:\s*(-?\d+)')
META_SOURCE_FILE_RE = re.compile(r'"sourceFile"\s*:\s*"((?:\\.|[^"\\])*)"')
META_NAME_RE = re.compile(r'"name"\s*:\s*"((?:\\.|[^"\\])*)"')
TOP_LEVEL_NAME_RE = re.compile(r'(?m)^\s*"m_Name"\s*:\s*"((?:\\.|[^"\\])*)"')
TOP_LEVEL_PARENT_RE = re.compile(
    r'(?ms)^\s*"m_Parent"\s*:\s*\{\s*"m_FileID"\s*:\s*-?\d+\s*,\s*"m_PathID"\s*:\s*(-?\d+)'
)
TOP_LEVEL_TRACKS_RE = re.compile(r'(?m)^\s*"m_Tracks"\s*:')
TOP_LEVEL_CHILDREN_RE = re.compile(r'(?m)^\s*"m_Children"\s*:')
TOP_LEVEL_CLIPS_RE = re.compile(r'(?m)^\s*"m_Clips"\s*:')
PATH_ID_SUFFIX_RE = re.compile(r"_p([0-9A-Fa-f]{16})$")


def path_id_suffix_from_stem(stem: str) -> str:
    match = PATH_ID_SUFFIX_RE.search(str(stem or ""))
    return match.group(1).upper() if match else ""


def strip_path_id_suffix(stem: str) -> str:
    return PATH_ID_SUFFIX_RE.sub("", str(stem or ""))


@dataclass
class TimelineRecoveryConfig:
    export_root: Path = EXPORT_ROOT
    cli: Path | None = None
    maps: list[Path] | None = None
    extract_dir: Path | None = None
    order_out: Path | None = None
    target_report: Path | None = None
    target_statuses: set[str] = field(default_factory=lambda: {"fallback", "partial"})
    include_sibling_prefixes: bool = False
    timeline_regex: str | None = None
    timeline_list: Path | None = None
    keep_extract: bool = False
    parse_only: bool = False
    dry_run: bool = False
    limit_chks: int = 0
    min_lines: int = 1
    copy_to_webui: Path | None = None
    prefer_full_monobehaviour: bool = True
    full_monobehaviour_scan_limit: int = 200_000


def recovery_root(export_root: Path = EXPORT_ROOT) -> Path:
    return export_root / "recovered" / "AnimeStudio-cli"


def default_extract_dir(export_root: Path = EXPORT_ROOT) -> Path:
    return recovery_root(export_root) / "timeline_extract"


def default_order_out(export_root: Path = EXPORT_ROOT) -> Path:
    return recovery_root(export_root) / "timeline_line_orders.json"


def rel_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def log(message: str) -> None:
    print(f"[timeline-recovery] {message}")


def resolve_cli(cli: Path | None = None) -> Path:
    if cli:
        candidate = cli if cli.is_absolute() else ROOT / cli
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"AnimeStudio CLI not found: {candidate}")

    env_value = os.environ.get("ANIMESTUDIO_CLI")
    if env_value:
        candidate = Path(env_value)
        if candidate.exists():
            return candidate

    cli_root = ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin"
    candidates = [
        cli_root / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe",
        cli_root / "Debug" / "net9.0-windows" / "AnimeStudio.CLI.exe",
        *sorted((cli_root / "Release").glob("*/AnimeStudio.CLI.exe")),
        *sorted((cli_root / "Debug").glob("*/AnimeStudio.CLI.exe")),
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "AnimeStudio CLI not found. Build tools/AnimeStudio/AnimeStudio.CLI "
        "or set ANIMESTUDIO_CLI."
    )


def discover_asset_maps(export_root: Path = EXPORT_ROOT) -> list[Path]:
    maps: list[Path] = []
    for source_name in ("StreamingAssets", "Persistent"):
        map_dir = recovery_root(export_root) / source_name / "maps"
        if not map_dir.is_dir():
            continue
        maps.extend(sorted(map_dir.glob("*_assets.json")))
    seen: set[Path] = set()
    out: list[Path] = []
    for path in maps:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return out


def timeline_order_is_current(order_out: Path, maps: list[Path] | None = None) -> bool:
    if not order_out.exists():
        return False
    inputs = [Path(__file__)]
    inputs.extend(path for path in (maps or []) if path.exists())
    if not inputs:
        return True
    output_mtime = order_out.stat().st_mtime
    return all(path.stat().st_mtime <= output_mtime for path in inputs)


def load_json(path: Path):
    try:
        with path.open(encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log(f"skip {rel_path(path)}: {exc}")
        return None


def decode_json_string_fragment(value: str) -> str:
    try:
        decoded = json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value
    return decoded if isinstance(decoded, str) else value


def extract_monobehaviour_metadata(path: Path) -> dict | None:
    """Read just enough of a MonoBehaviour JSON file to build a lazy graph index."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        log(f"skip {rel_path(path)}: {exc}")
        return None

    path_match = META_PATH_ID_RE.search(text)
    source_match = META_SOURCE_FILE_RE.search(text)
    if not path_match or not source_match:
        return None
    path_id = as_path_id(path_match.group(1))
    source_file = decode_json_string_fragment(source_match.group(1))
    if path_id is None or not source_file:
        return None

    name_match = TOP_LEVEL_NAME_RE.search(text) or META_NAME_RE.search(text)
    name = decode_json_string_fragment(name_match.group(1)) if name_match else path.stem
    parent_match = TOP_LEVEL_PARENT_RE.search(text)
    parent_id = as_path_id(parent_match.group(1)) if parent_match else None
    return {
        "pathId": path_id,
        "sourceFile": source_file,
        "name": name,
        "parentId": parent_id,
        "hasTracks": bool(TOP_LEVEL_TRACKS_RE.search(text)),
        "hasChildren": bool(TOP_LEVEL_CHILDREN_RE.search(text)),
        "hasClips": bool(TOP_LEVEL_CLIPS_RE.search(text)),
    }


def record_payload(record: dict) -> dict:
    payload = record.get("payload")
    if isinstance(payload, dict):
        return payload
    loaded = load_json(record["path"])
    payload = loaded if isinstance(loaded, dict) else {}
    record["payload"] = payload
    return payload


def load_entries(map_path: Path) -> list[dict]:
    with map_path.open(encoding="utf-8-sig") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("AssetEntries"), list):
        return data["AssetEntries"]
    if isinstance(data, list):
        return data
    return []


def timeline_stem_from_container(container: str) -> str:
    match = TIMELINE_CONTAINER_RE.search(str(container or "").replace("\\", "/"))
    return match.group("stem") if match else ""


def is_timeline_stem(stem: str) -> bool:
    return bool(stem and TIMELINE_STEM_RE.match(stem))


def normalize_timeline_body(stem: str) -> str:
    value = str(stem or "")
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return re.sub(r"_sub_\d+$", "", value)


def timeline_body_prefix(body: str) -> str:
    return re.sub(r"_\d+$", "", str(body or ""))


def scene_body_from_key(key: str) -> str:
    value = str(key or "").strip()
    if value.startswith("dlg_"):
        return value[len("dlg_"):]
    if value.startswith("misc_"):
        value = value[len("misc_"):]
        if value.startswith("dlg_"):
            return value[len("dlg_"):]
        return value
    return ""


def is_timeline_entry(entry: dict, stem_filter: Callable[[str], bool] | None = None) -> bool:
    stem = timeline_stem_from_container(entry.get("Container") or "")
    if not is_timeline_stem(stem):
        return False
    return stem_filter(stem) if stem_filter else True


def count_timeline_stems(entries: list[dict], stem_filter: Callable[[str], bool] | None = None) -> Counter:
    counts: Counter = Counter()
    for entry in entries:
        if is_timeline_entry(entry, stem_filter):
            counts[timeline_stem_from_container(entry.get("Container") or "")] += 1
    return counts


def group_by_source(entries: list[dict], stem_filter: Callable[[str], bool] | None = None) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        if is_timeline_entry(entry, stem_filter) and entry.get("Source"):
            out[str(entry["Source"])].append(entry)
    return out


def load_timeline_list(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"Timeline list not found: {path}")
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            values = payload
        elif isinstance(payload, dict):
            values = payload.get("timelineStems") or payload.get("stems") or payload.get("timelines") or []
        else:
            values = []
    else:
        values = []
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            text = line.split("#", 1)[0].strip()
            if text:
                values.append(text)

    stems = {str(value).strip() for value in values if str(value).strip()}
    bad = sorted(stem for stem in stems if not is_timeline_stem(stem))
    if bad:
        raise ValueError(f"Timeline list contains unsupported stem(s): {', '.join(bad[:10])}")
    return stems


def derive_report_target_stems(
    report_path: Path,
    available_counts: Counter,
    statuses: set[str],
    include_sibling_prefixes: bool = False,
) -> tuple[set[str], dict]:
    payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
    scenes = payload.get("scenes") if isinstance(payload, dict) else []
    if not isinstance(scenes, list):
        raise ValueError(f"Gap report has no scenes array: {report_path}")

    by_body: dict[str, list[str]] = defaultdict(list)
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for stem in available_counts:
        body = normalize_timeline_body(stem)
        by_body[body].append(stem)
        prefix = timeline_body_prefix(body)
        if prefix:
            by_prefix[prefix].append(stem)

    matched_scenes: list[dict] = []
    unmatched_scenes: list[dict] = []
    target_stems: set[str] = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        status = str(scene.get("lineOrderStatus") or "")
        if statuses and status not in statuses:
            continue
        key = str(scene.get("key") or "")
        body = scene_body_from_key(key)
        stems = sorted(by_body.get(body, []))
        match_mode = "exact" if stems else ""
        if not stems and include_sibling_prefixes:
            prefix = timeline_body_prefix(body)
            stems = sorted(by_prefix.get(prefix, [])) if prefix else []
            match_mode = "siblingPrefix" if stems else ""
        row = {
            "key": key,
            "status": status,
            "kind": str(scene.get("kind") or ""),
            "lineCount": scene.get("lineCount"),
            "matchMode": match_mode or "unmatched",
            "timelineStems": stems,
            "entryCount": sum(available_counts[stem] for stem in stems),
        }
        if stems:
            matched_scenes.append(row)
            target_stems.update(stems)
        else:
            unmatched_scenes.append(row)

    summary = {
        "report": str(report_path),
        "statuses": sorted(statuses),
        "sceneCount": len(matched_scenes) + len(unmatched_scenes),
        "matchedSceneCount": len(matched_scenes),
        "unmatchedSceneCount": len(unmatched_scenes),
        "siblingPrefixEnabled": include_sibling_prefixes,
        "matchModeCounts": dict(Counter(row["matchMode"] for row in matched_scenes + unmatched_scenes)),
        "timelineStemCount": len(target_stems),
        "entryCount": sum(available_counts[stem] for stem in target_stems),
        "timelineStems": sorted(target_stems),
        "matchedScenes": matched_scenes,
        "unmatchedScenes": unmatched_scenes,
    }
    return target_stems, summary


def write_filter_data(items: list[dict], path: Path) -> None:
    payload = [
        {
            "Source": item["Source"],
            "Type": item.get("Type", "MonoBehaviour"),
            "Name": item.get("Name", ""),
            "PathID": item.get("PathID", 0),
            "Offset": item.get("Offset", -1),
        }
        for item in items
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_cli(cli: Path, chk: Path, out_dir: Path, filter_data: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(cli),
        str(chk),
        str(out_dir),
        "--game",
        "ArknightsEndfield",
        "--logger_flags",
        "Warning",
        "Error",
        "--group_assets",
        "ByType",
        "--export_type",
        "JSON",
        "--filter_data",
        str(filter_data),
        "--types",
        "MonoBehaviour:Both",
        "PlayableDirector:Both",
        "TextAsset:Both",
    ]
    return subprocess.call(cmd)


def as_path_id(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def ref_path_id(value) -> int | None:
    if isinstance(value, dict):
        return as_path_id(value.get("m_PathID"))
    return None


def as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def iter_structural_ref_ids(payload: dict):
    for field_name in ("m_Tracks", "m_Children"):
        refs = payload.get(field_name)
        if not isinstance(refs, list):
            continue
        for ref in refs:
            path_id = ref_path_id(ref)
            if path_id is not None:
                yield path_id


def iter_asset_ref_ids(payload: dict):
    clips = payload.get("m_Clips")
    if isinstance(clips, list):
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            path_id = ref_path_id(clip.get("m_Asset"))
            if path_id is not None:
                yield path_id
    binding = payload.get("bindingOptionAssets")
    if isinstance(binding, dict):
        yield from iter_ref_path_ids(binding)


def iter_ref_ids(payload: dict):
    yield from iter_structural_ref_ids(payload)
    yield from iter_asset_ref_ids(payload)


def line_stem(line_id: str) -> str:
    if line_id.startswith("dlg_"):
        return re.sub(r"_\d+$", "", line_id)
    if re.search(r"_\d+_\d+$", line_id):
        return re.sub(r"_\d+_\d+$", "", line_id)
    return re.sub(r"_\d+$", "", line_id) if re.search(r"_\d+$", line_id) else ""


def timeline_stem_to_dialog_key(timeline: str) -> str:
    value = str(timeline or "")
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    value = re.sub(r"_sub_\d+$", "", value)
    return f"dlg_{value}" if value else ""


def timeline_name_from_record_name(name: str) -> str:
    for pattern in (TIMELINE_SUB_NAME_RE, TIMELINE_NO_SUB_NAME_RE):
        match = pattern.match(name)
        if match:
            return match.group("timeline")
    return ""


def is_timeline_root_seed_name(stem: str) -> bool:
    # Dialog trunk and option tracks recovered so far live under the Actor
    # timeline root. Seeding Audio/Effect/Light/Others forces the graph walk
    # through large non-dialog tracks and dominates build time.
    name = strip_path_id_suffix(stem)
    timeline = timeline_name_from_record_name(name)
    if not timeline or not name.startswith(timeline):
        return False
    return bool(TIMELINE_ROOT_NAME_TAIL_RE.match(name[len(timeline):]))


def should_walk_timeline_record(record: dict) -> bool:
    name = str(record.get("name") or "")
    if is_timeline_root_seed_name(name):
        return True
    if record.get("hasChildren"):
        return True
    return bool(DIALOG_TIMELINE_WALK_RE.search(name))


def looks_like_dialog_line_id(value: str) -> bool:
    if not value or value.startswith(IGNORED_DISPLAY_PREFIXES):
        return False
    return value.startswith("dlg_") and bool(LINE_ID_RE.match(value))


def looks_like_dialog_option_id(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.strip().rsplit("_", 2)
    return len(parts) == 3 and parts[0].startswith("option_dlg_") and bool(parts[2])


def option_scene_key(option_id: str) -> str:
    if not looks_like_dialog_option_id(option_id):
        return ""
    return option_id.rsplit("_", 2)[0][len("option_"):]


def option_group_key(option_id: str) -> str:
    if not looks_like_dialog_option_id(option_id):
        return ""
    return option_id.rsplit("_", 2)[1]


def iter_ref_path_ids(value):
    path_id = ref_path_id(value)
    if path_id is not None:
        yield path_id
    if isinstance(value, dict):
        for child in value.values():
            yield from iter_ref_path_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_ref_path_ids(child)


def option_entries_from_payload(payload) -> list[dict]:
    entries: list[dict] = []
    seen: set[str] = set()

    def visit(value) -> None:
        if isinstance(value, dict):
            option_id = str(value.get("_optionId") or "").strip()
            if looks_like_dialog_option_id(option_id) and option_id not in seen:
                seen.add(option_id)
                entry = {
                    "id": option_id,
                    "groupKey": option_group_key(option_id),
                    "index": as_int(value.get("index")),
                    "optionIndex": as_int(value.get("optionIndex")),
                }
                for field in ("trunkId", "dialogId", "overrideOptionIconType"):
                    field_value = str(value.get(field) or "").strip()
                    if field_value:
                        entry[field] = field_value
                for field in (
                    "logicId",
                    "selectedFlag",
                    "setGreyed",
                    "main",
                    "isChat",
                    "changeFinishNum",
                    "targetFinishNum",
                    "useExOptionColor",
                    "overrideOptionIcon",
                ):
                    field_value = as_int(value.get(field))
                    if field_value is not None:
                        entry[field] = field_value
                condition_data = value.get("conditionData")
                if isinstance(condition_data, dict):
                    condition_rid = as_int(condition_data.get("rid"))
                    if condition_rid is not None:
                        entry["conditionRid"] = condition_rid
                entries.append(entry)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return entries


def discover_extract_dirs(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        root = root if root.is_absolute() else ROOT / root
        candidates = [root] if root.is_dir() and root.name == "MonoBehaviour" else []
        if (root / "MonoBehaviour").is_dir():
            candidates.append(root / "MonoBehaviour")
        if root.is_dir():
            candidates.extend(sorted(path for path in root.rglob("MonoBehaviour") if path.is_dir()))
        for mono_dir in candidates:
            key = str(mono_dir.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(mono_dir)
    return out


def load_monobehaviour_records(
    mono_dir: Path,
) -> tuple[dict[tuple[str, int], dict], dict[tuple[str, int], list[dict]], dict[str, list[dict]]]:
    records_by_key: dict[tuple[str, int], dict] = {}
    children_by_parent: dict[tuple[str, int], list[dict]] = defaultdict(list)
    timeline_roots: dict[str, list[dict]] = defaultdict(list)

    for path in sorted(mono_dir.glob("*.json")):
        if not path_id_suffix_from_stem(path.stem):
            continue
        meta = extract_monobehaviour_metadata(path)
        if not meta:
            continue
        path_id = as_path_id(meta.get("pathId"))
        source_file = str(meta.get("sourceFile") or "")
        if path_id is None or not source_file:
            continue
        name = str(meta.get("name") or path.stem)
        record = {
            "key": (source_file, path_id),
            "sourceFile": source_file,
            "pathId": path_id,
            "path": path,
            "name": name,
            "payload": None,
            "hasChildren": bool(meta.get("hasChildren")),
            "hasClips": bool(meta.get("hasClips")),
        }
        records_by_key.setdefault(record["key"], record)

        parent_id = as_path_id(meta.get("parentId"))
        if parent_id is not None:
            children_by_parent[(source_file, parent_id)].append(record)

        timeline = timeline_name_from_record_name(name)
        if timeline and meta.get("hasTracks"):
            timeline_roots[timeline].append(record)

    return records_by_key, children_by_parent, timeline_roots


def walk_track_tree(
    roots: list[dict],
    records_by_key: dict[tuple[str, int], dict],
    children_by_parent: dict[tuple[str, int], list[dict]],
) -> list[dict]:
    queue = deque(root["key"] for root in roots)
    seen: set[tuple[str, int]] = set()
    out: list[dict] = []

    while queue:
        key = queue.popleft()
        if key in seen:
            continue
        seen.add(key)
        record = records_by_key.get(key)
        if not record:
            continue
        out.append(record)

        source_file, _path_id = key
        payload = record_payload(record)
        for child_id in iter_structural_ref_ids(payload):
            child = records_by_key.get((source_file, child_id))
            if child and should_walk_timeline_record(child):
                queue.append(child["key"])
        for asset_id in iter_asset_ref_ids(payload):
            records_by_key.get((source_file, asset_id))
        for child in children_by_parent.get(key, []):
            if should_walk_timeline_record(child):
                queue.append(child["key"])

    out.sort(key=lambda item: rel_path(item["path"]))
    return out


def clip_asset_record(record: dict, clip: dict, records_by_key: dict[tuple[str, int], dict]) -> dict | None:
    asset_id = ref_path_id(clip.get("m_Asset"))
    if asset_id is None:
        return None
    return records_by_key.get((record["sourceFile"], asset_id))


def clip_line_identity(
    record: dict,
    clip: dict,
    records_by_key: dict[tuple[str, int], dict],
) -> dict:
    """Return the best source-backed dialog line ID for a Timeline clip."""
    display = str(clip.get("m_DisplayName") or "").strip()
    display_line_id = display if looks_like_dialog_line_id(display) else ""
    asset = clip_asset_record(record, clip, records_by_key)
    asset_trunk_id = ""
    if asset:
        asset_trunk_id = str(record_payload(asset).get("_trunkId") or "").strip()
        if not looks_like_dialog_line_id(asset_trunk_id):
            asset_trunk_id = ""

    line_id = asset_trunk_id or display_line_id
    source = "assetTrunkId" if asset_trunk_id else ("displayName" if display_line_id else "")
    out = {
        "id": line_id,
        "source": source,
        "displayLineId": display_line_id,
    }
    if asset:
        out["assetPathId"] = asset["pathId"]
        out["assetName"] = asset["name"]
        out["assetTrack"] = rel_path(asset["path"])
    return out


TINY_LINE_CLIP_SECONDS = 0.05
ROUTE_TIME_EPSILON = 0.05


def line_clip_source_priority(row: dict) -> int:
    """Prefer real dialog trunk clips over actor/lip-sync/display fallbacks."""
    asset_name = str(row.get("assetName") or "")
    if asset_name.startswith("DialogTrunkPlayableAsset"):
        return 0
    if row.get("lineIdSource") == "assetTrunkId":
        return 1
    if row.get("lineIdSource") == "displayName":
        return 2
    return 3


def line_clip_duration_priority(row: dict) -> int:
    """Treat tiny duplicate clips as Timeline placeholders, not spoken lines."""
    try:
        duration = float(row.get("duration") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    if 0.0 < duration <= TINY_LINE_CLIP_SECONDS:
        return 1
    return 0


def binding_option_records(asset: dict, records_by_key: dict[tuple[str, int], dict]) -> list[dict]:
    payload = record_payload(asset)
    binding = payload.get("bindingOptionAssets")
    if not isinstance(binding, dict):
        return []
    out: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for path_id in iter_ref_path_ids(binding):
        key = (asset["sourceFile"], path_id)
        if key in seen:
            continue
        seen.add(key)
        record = records_by_key.get(key)
        if record:
            out.append(record)
    return out


def option_clip_rows(
    timeline: str,
    record: dict,
    clip: dict,
    records_by_key: dict[tuple[str, int], dict],
    line_id: str = "",
) -> list[dict]:
    asset = clip_asset_record(record, clip, records_by_key)
    if not asset:
        return []

    rows: list[dict] = []
    base = {
        "start": as_float(clip.get("m_Start")),
        "duration": as_float(clip.get("m_Duration")),
        "track": rel_path(record["path"]),
        "trackName": record["name"],
        "trackPathId": record["pathId"],
        "sourceFile": record["sourceFile"],
        "timeline": timeline,
        "clipOptionIndex": as_int(clip.get("optionIndex")),
    }

    def add_entries(source_asset: dict, entries: list[dict], mode: str, anchor_line_id: str = "") -> None:
        for entry in entries:
            row = {
                **base,
                **entry,
                "assetName": source_asset["name"],
                "assetPathId": source_asset["pathId"],
                "assetTrack": rel_path(source_asset["path"]),
                "anchorMode": mode,
            }
            if anchor_line_id:
                row["anchorLineId"] = anchor_line_id
            rows.append(row)

    add_entries(asset, option_entries_from_payload(record_payload(asset)), "timelineClip")
    if line_id:
        for option_asset in binding_option_records(asset, records_by_key):
            add_entries(
                option_asset,
                option_entries_from_payload(record_payload(option_asset)),
                "trunkBinding",
                line_id,
            )
    return rows


def runtime_jump_clip_rows(
    timeline: str,
    records: list[dict],
    records_by_key: dict[tuple[str, int], dict],
) -> list[dict]:
    rows: list[dict] = []
    for record in records:
        if not str(record.get("name") or "").startswith("Runtime Jump Track"):
            continue
        payload = record_payload(record)
        clips = payload.get("m_Clips")
        if not isinstance(clips, list):
            continue
        track_option_index = as_int(payload.get("OptionIndex"))
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            option_index = as_int(clip.get("optionIndex"))
            if option_index is None:
                option_index = track_option_index
            if option_index is None:
                continue
            start = as_float(clip.get("m_Start"))
            duration = as_float(clip.get("m_Duration"))
            if duration <= 0.0:
                continue
            asset = clip_asset_record(record, clip, records_by_key)
            asset_payload = record_payload(asset) if asset else {}
            row = {
                "kind": "runtimeJump",
                "optionIndex": option_index,
                "start": round(start, 3),
                "duration": round(duration, 3),
                "end": round(start + duration, 3),
                "track": rel_path(record["path"]),
                "trackName": record["name"],
                "trackPathId": record["pathId"],
                "sourceFile": record["sourceFile"],
                "timeline": timeline,
                "displayName": str(clip.get("m_DisplayName") or ""),
            }
            if asset:
                row["assetName"] = asset["name"]
                row["assetPathId"] = asset["pathId"]
                row["assetTrack"] = rel_path(asset["path"])
            for field in (
                "isReverseJump",
                "needChangeOptionAfterJump",
                "optionIndexAfterJump",
                "isJumpFirst",
            ):
                value = as_int(asset_payload.get(field)) if isinstance(asset_payload, dict) else None
                if value is not None:
                    row[field] = value
            if isinstance(asset_payload, dict) and "crossFadeDurationAfterJump" in asset_payload:
                row["crossFadeDurationAfterJump"] = round(
                    as_float(asset_payload.get("crossFadeDurationAfterJump")),
                    3,
                )
            rows.append(row)
    rows.sort(key=lambda row: (row["start"], row["optionIndex"], row.get("track") or ""))
    return rows


def _line_is_in_time_range(line: dict, start: float, end: float) -> bool:
    line_start = as_float(line.get("start"))
    return line_start >= start - ROUTE_TIME_EPSILON and line_start < end - ROUTE_TIME_EPSILON


def _time_ranges_for_option(jump_clips: list[dict], option_index: int) -> list[dict]:
    return [
        clip
        for clip in jump_clips
        if clip.get("optionIndex") == option_index
        and not clip.get("isReverseJump")
        and "<" not in str(clip.get("displayName") or "")
    ]


def _reverse_time_ranges_for_option(jump_clips: list[dict], option_index: int) -> list[dict]:
    return [
        clip
        for clip in jump_clips
        if clip.get("optionIndex") == option_index
        and (
            clip.get("isReverseJump")
            or "<" in str(clip.get("displayName") or "")
        )
    ]


def _is_reverse_jump_clip(clip: dict) -> bool:
    return bool(clip.get("isReverseJump")) or "<" in str(clip.get("displayName") or "")


def _clip_in_option_route_window(clip: dict, slot: dict, route_end: float) -> bool:
    clip_start = as_float(clip.get("start"))
    clip_end = as_float(clip.get("end"))
    if _is_reverse_jump_clip(clip):
        starts_in_slot = clip_start >= slot["start"] - ROUTE_TIME_EPSILON and clip_start <= slot["end"] + ROUTE_TIME_EPSILON
        overlaps_route = clip_end > slot["end"] + ROUTE_TIME_EPSILON
        return starts_in_slot and overlaps_route and (not route_end or clip_start < route_end + ROUTE_TIME_EPSILON)
    return (
        clip_start >= slot["end"] - ROUTE_TIME_EPSILON
        and (not route_end or clip_start < route_end + ROUTE_TIME_EPSILON)
    )


def _compact_jump_range(clip: dict) -> dict:
    out = {
        "start": clip.get("start"),
        "end": clip.get("end"),
        "duration": clip.get("duration"),
        "track": clip.get("track") or "",
        "trackName": clip.get("trackName") or "",
        "assetTrack": clip.get("assetTrack") or "",
        "displayName": clip.get("displayName") or "",
    }
    for field in (
        "isReverseJump",
        "needChangeOptionAfterJump",
        "optionIndexAfterJump",
        "isJumpFirst",
        "crossFadeDurationAfterJump",
    ):
        if field in clip:
            out[field] = clip[field]
    return out


def _compact_runtime_jump_clip(clip: dict) -> dict:
    """Keep the raw option selector and time window needed by consumers.

    Completed per-option routes are emitted separately as ``optionRoutes``.
    These compact raw clips let the Story builder remain conservative when a
    Runtime Jump overlaps an otherwise zero-index shared-continuation window
    but does not form a complete recoverable route.
    """
    out = _compact_jump_range(clip)
    option_index = as_int(clip.get("optionIndex"))
    if option_index is not None:
        out["optionIndex"] = option_index
    source_file = str(clip.get("sourceFile") or "")
    if source_file:
        out["sourceFile"] = source_file
    return out


def _build_runtime_jump_candidate_routes(
    slot: dict,
    route_end: float,
    line_rows: list[dict],
    group_jump_clips: list[dict],
    continuation_slot: dict | None = None,
    source: str = "runtimeJumpTrack",
) -> dict[str, dict]:
    if not group_jump_clips:
        return {}
    if not route_end:
        route_end = max(as_float(clip.get("end")) for clip in group_jump_clips)
    if route_end <= slot["end"]:
        return {}

    scene_lines = [
        line
        for line in line_rows
        if line_stem(str(line.get("id") or "")) == slot["sceneKey"]
        and _line_is_in_time_range(line, slot["end"], route_end)
    ]
    if not scene_lines:
        return {}

    candidate_routes: dict[str, dict] = {}
    for row in slot["optionRows"]:
        option_id = str(row.get("id") or "")
        option_index = as_int(row.get("optionIndex"))
        if not option_id or option_index is None:
            continue
        skip_ranges = _time_ranges_for_option(group_jump_clips, option_index)
        skipped_line_ids: list[str] = []
        path_line_ids: list[str] = []
        for line in scene_lines:
            line_id = str(line.get("id") or "")
            if not line_id:
                continue
            if any(_line_is_in_time_range(line, as_float(skip.get("start")), as_float(skip.get("end"))) for skip in skip_ranges):
                skipped_line_ids.append(line_id)
            else:
                path_line_ids.append(line_id)
        if not path_line_ids or not skip_ranges:
            continue
        route = {
            "source": source,
            "groupKey": slot["groupKey"],
            "optionIndex": option_index,
            "start": round(slot["start"], 3),
            "end": round(route_end, 3),
            "pathLineIds": path_line_ids,
            "skippedLineIds": skipped_line_ids,
            "skipRanges": [
                _compact_jump_range(skip)
                for skip in skip_ranges
            ],
        }
        if continuation_slot:
            route["continuationGroupKey"] = continuation_slot["groupKey"]
            route["continuationOptionIds"] = [
                str(next_row.get("id") or "")
                for next_row in continuation_slot["optionRows"]
                if str(next_row.get("id") or "")
            ]
        candidate_routes[option_id] = route

    if len(candidate_routes) != len(slot["optionRows"]):
        return {}
    distinct_paths = {tuple(route.get("pathLineIds") or []) for route in candidate_routes.values()}
    if len(distinct_paths) < 2:
        return {}
    return candidate_routes


def _build_directional_runtime_jump_candidate_routes(
    slot: dict,
    route_end: float,
    line_rows: list[dict],
    group_jump_clips: list[dict],
    continuation_slot: dict | None = None,
) -> dict[str, dict]:
    if not group_jump_clips:
        return {}
    if not route_end:
        route_end = max(as_float(clip.get("end")) for clip in group_jump_clips)
    if route_end <= slot["end"]:
        return {}

    scene_lines = [
        line
        for line in line_rows
        if line_stem(str(line.get("id") or "")) == slot["sceneKey"]
        and _line_is_in_time_range(line, slot["end"], route_end)
    ]
    if not scene_lines:
        return {}

    has_forward = False
    has_reverse = False
    candidate_routes: dict[str, dict] = {}
    for row in slot["optionRows"]:
        option_id = str(row.get("id") or "")
        option_index = as_int(row.get("optionIndex"))
        if not option_id or option_index is None:
            continue
        skip_ranges = _time_ranges_for_option(group_jump_clips, option_index)
        reverse_ranges = _reverse_time_ranges_for_option(group_jump_clips, option_index)
        has_forward = has_forward or bool(skip_ranges)
        has_reverse = has_reverse or bool(reverse_ranges)
        if not skip_ranges and not reverse_ranges:
            continue

        skipped_line_ids: list[str] = []
        reverse_range_line_ids: list[str] = []
        out_of_reverse_line_ids: list[str] = []
        path_line_ids: list[str] = []
        for line in scene_lines:
            line_id = str(line.get("id") or "")
            if not line_id:
                continue
            in_skip = any(
                _line_is_in_time_range(line, as_float(skip.get("start")), as_float(skip.get("end")))
                for skip in skip_ranges
            )
            if in_skip:
                skipped_line_ids.append(line_id)
                continue
            in_reverse = any(
                _line_is_in_time_range(line, as_float(reverse.get("start")), as_float(reverse.get("end")))
                for reverse in reverse_ranges
            )
            if reverse_ranges:
                # When the option has a reverse jump, the runtime loops within
                # that range — only lines inside the range play. Lines outside
                # the reverse range belong to other options' branches or to
                # shared content reached after this slot.
                if not in_reverse:
                    out_of_reverse_line_ids.append(line_id)
                    continue
                path_line_ids.append(line_id)
                reverse_range_line_ids.append(line_id)
            else:
                path_line_ids.append(line_id)

        # A forward-only option whose skip range covers every scene line in the
        # post-slot window terminates the slot — the runtime jumps past every
        # remaining line and resumes outside this route. Source: per-option
        # Runtime Jump clip with optionIndex=N and displayName="--------->"
        # marks the range the runtime skips when option N is chosen.
        terminates_slot = False
        if not path_line_ids:
            if skip_ranges and not reverse_ranges:
                terminates_slot = True
            else:
                continue

        route = {
            "source": "runtimeJumpTrackDirectional",
            "groupKey": slot["groupKey"],
            "optionIndex": option_index,
            "start": round(slot["start"], 3),
            "end": round(route_end, 3),
            "pathLineIds": path_line_ids,
            "skippedLineIds": skipped_line_ids,
            "skipRanges": [_compact_jump_range(skip) for skip in skip_ranges],
            "reverseRangeLineIds": reverse_range_line_ids,
            "reverseRanges": [_compact_jump_range(reverse) for reverse in reverse_ranges],
        }
        if terminates_slot:
            route["terminatesSlot"] = True
        if continuation_slot:
            route["continuationGroupKey"] = continuation_slot["groupKey"]
            route["continuationOptionIds"] = [
                str(next_row.get("id") or "")
                for next_row in continuation_slot["optionRows"]
                if str(next_row.get("id") or "")
            ]
        candidate_routes[option_id] = route

    if not has_forward and not has_reverse:
        return {}
    if len(candidate_routes) != len(slot["optionRows"]):
        return {}
    non_terminating_routes = [
        route for route in candidate_routes.values() if not route.get("terminatesSlot")
    ]
    non_terminating_first_lines = [
        route["pathLineIds"][0]
        for route in non_terminating_routes
        if route.get("pathLineIds")
    ]
    if len(set(non_terminating_first_lines)) != len(non_terminating_routes):
        return {}
    distinct_paths = {
        ("__terminatesSlot__",) if route.get("terminatesSlot") else tuple(route.get("pathLineIds") or [])
        for route in candidate_routes.values()
    }
    if len(distinct_paths) < 2:
        return {}
    return candidate_routes


def build_option_routes(
    lines: list[dict],
    options: list[dict],
    jump_clips: list[dict],
) -> dict[str, dict]:
    if not lines or not options or not jump_clips:
        return {}

    line_rows = sorted(lines, key=lambda row: (as_float(row.get("start")), row.get("id") or ""))
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in options:
        option_id = str(row.get("id") or "")
        scene_key = option_scene_key(option_id)
        group_key = str(row.get("groupKey") or option_group_key(option_id) or "")
        if scene_key and group_key:
            grouped[(scene_key, group_key)].append(row)

    all_slots: list[dict] = []
    route_slots: list[dict] = []
    for (scene_key, group_key), rows in grouped.items():
        best_by_id: dict[str, dict] = {}
        for row in rows:
            option_id = str(row.get("id") or "")
            if not option_id:
                continue
            previous = best_by_id.get(option_id)
            rank = (
                0 if row.get("anchorMode") == "trunkBinding" else 1,
                as_float(row.get("start")),
                as_int(row.get("optionIndex")) if as_int(row.get("optionIndex")) is not None else 10**9,
                str(row.get("track") or ""),
            )
            previous_rank = (
                0 if previous and previous.get("anchorMode") == "trunkBinding" else 1,
                as_float(previous.get("start")) if previous else 0.0,
                as_int(previous.get("optionIndex")) if previous and as_int(previous.get("optionIndex")) is not None else 10**9,
                str(previous.get("track") or "") if previous else "",
            ) if previous is not None else None
            if previous is None or rank < previous_rank:
                best_by_id[option_id] = row
        option_rows = sorted(
            best_by_id.values(),
            key=lambda item: (
                as_float(item.get("start")),
                as_int(item.get("optionIndex")) if as_int(item.get("optionIndex")) is not None else 10**9,
                item.get("id") or "",
            ),
        )
        option_indices = [as_int(row.get("optionIndex")) for row in option_rows]
        if any(value is None for value in option_indices):
            continue
        if len(option_rows) < 2:
            all_slots.append({
                "sceneKey": scene_key,
                "groupKey": group_key,
                "optionRows": option_rows,
                "optionIndices": option_indices,
                "start": min(as_float(row.get("start")) for row in option_rows),
                "end": max(as_float(row.get("start")) + as_float(row.get("duration")) for row in option_rows),
                "sourceFiles": {
                    str(row.get("sourceFile") or "")
                    for row in option_rows
                    if str(row.get("sourceFile") or "")
                },
            })
            continue
        start = min(as_float(row.get("start")) for row in option_rows)
        end = max(as_float(row.get("start")) + as_float(row.get("duration")) for row in option_rows)
        slot = {
            "sceneKey": scene_key,
            "groupKey": group_key,
            "optionRows": option_rows,
            "optionIndices": option_indices,
            "start": start,
            "end": end,
            "sourceFiles": {
                str(row.get("sourceFile") or "")
                for row in option_rows
                if str(row.get("sourceFile") or "")
            },
        }
        all_slots.append(slot)
        route_slots.append(slot)

    routes: dict[str, dict] = {}
    for slot in sorted(route_slots, key=lambda item: (item["start"], item["sceneKey"], item["groupKey"])):
        next_slots = [
            other
            for other in all_slots
            if other is not slot
            and other["sceneKey"] == slot["sceneKey"]
            and other["start"] > slot["start"] + ROUTE_TIME_EPSILON
        ]
        next_slot = min(next_slots, key=lambda item: item["start"]) if next_slots else None
        route_end = next_slot["start"] if next_slot else 0.0
        option_index_set = set(slot["optionIndices"])
        group_jump_clips = [
            clip
            for clip in jump_clips
            if clip.get("optionIndex") in option_index_set
            and (not slot["sourceFiles"] or str(clip.get("sourceFile") or "") in slot["sourceFiles"])
            and _clip_in_option_route_window(clip, slot, route_end)
        ]
        if not group_jump_clips:
            continue

        def build_single_option_boundary_routes() -> dict[str, dict]:
            if not next_slot or len(next_slot["optionRows"]) != 1:
                return {}
            extended_jump_clips = [
                clip
                for clip in jump_clips
                if clip.get("optionIndex") in option_index_set
                and (not slot["sourceFiles"] or str(clip.get("sourceFile") or "") in slot["sourceFiles"])
                and _clip_in_option_route_window(clip, slot, next_slot["end"])
            ]
            if not extended_jump_clips:
                return {}
            extended_route_end = max(as_float(clip.get("end")) for clip in extended_jump_clips)
            return _build_runtime_jump_candidate_routes(
                slot,
                extended_route_end,
                line_rows,
                extended_jump_clips,
                next_slot,
                source="runtimeJumpTrackSingleOptionBoundary",
            )

        candidate_routes = _build_runtime_jump_candidate_routes(
            slot,
            route_end,
            line_rows,
            group_jump_clips,
            next_slot,
        )
        if candidate_routes:
            routes.update(candidate_routes)
            continue

        candidate_routes = build_single_option_boundary_routes()
        if candidate_routes:
            routes.update(candidate_routes)
            continue

        candidate_routes = _build_directional_runtime_jump_candidate_routes(
            slot,
            route_end,
            line_rows,
            group_jump_clips,
            next_slot,
        )
        if candidate_routes:
            routes.update(candidate_routes)
            continue

    return dict(sorted(routes.items()))


def collect_timeline_signals(
    timeline: str,
    records: list[dict],
    records_by_key: dict[tuple[str, int], dict],
) -> tuple[list[dict], list[dict], dict[str, dict], list[dict], int, int]:
    raw_lines: list[dict] = []
    raw_options: list[dict] = []
    for record in records:
        payload = record_payload(record)
        clips = payload.get("m_Clips")
        if not isinstance(clips, list):
            continue
        track_priority = 0 if record["name"].startswith("Dialog Trunk Track") else 1
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            line_identity = clip_line_identity(record, clip, records_by_key)
            line_id = line_identity["id"]
            if line_id:
                row = {
                    "id": line_id,
                    "actor": str(payload.get("uniqueId") or "").split("#", 1)[0],
                    "binding": str(payload.get("autoBindingPath") or ""),
                    "start": as_float(clip.get("m_Start")),
                    "duration": as_float(clip.get("m_Duration")),
                    "track": rel_path(record["path"]),
                    "trackName": record["name"],
                    "trackPriority": track_priority,
                    "trackPathId": record["pathId"],
                    "sourceFile": record["sourceFile"],
                    "timeline": timeline,
                    "lineIdSource": line_identity["source"],
                }
                if line_identity.get("assetPathId") is not None:
                    row["assetPathId"] = line_identity["assetPathId"]
                    row["assetName"] = line_identity.get("assetName") or ""
                    row["assetTrack"] = line_identity.get("assetTrack") or ""
                clip_option_index = as_int(clip.get("optionIndex"))
                if clip_option_index is not None:
                    row["clipOptionIndex"] = clip_option_index
                display_line_id = line_identity.get("displayLineId") or ""
                if display_line_id and display_line_id != line_id:
                    row["displayLineId"] = display_line_id
                raw_lines.append(row)
            raw_options.extend(option_clip_rows(timeline, record, clip, records_by_key, line_id))

    best_by_id: dict[str, dict] = {}
    for row in raw_lines:
        previous = best_by_id.get(row["id"])
        row_rank = (
            line_clip_source_priority(row),
            row["trackPriority"],
            line_clip_duration_priority(row),
            row["start"],
            row["track"],
        )
        previous_rank = (
            line_clip_source_priority(previous),
            previous["trackPriority"],
            line_clip_duration_priority(previous),
            previous["start"],
            previous["track"],
        ) if previous is not None else None
        if previous is None or row_rank < previous_rank:
            best_by_id[row["id"]] = row

    selected_rows = sorted(
        best_by_id.values(),
        key=lambda row: (row["start"], line_clip_source_priority(row), row["trackPriority"], row["track"], row["id"]),
    )

    seen_ids: set[str] = set()
    lines: list[dict] = []
    duplicate_count = len(raw_lines) - len(selected_rows)
    for row in selected_rows:
        if row["id"] in seen_ids:
            duplicate_count += 1
            continue
        seen_ids.add(row["id"])
        row = dict(row)
        row.pop("trackPriority", None)
        lines.append(row)

    best_option_rows: dict[tuple[str, str, str], dict] = {}
    for row in raw_options:
        option_id = row.get("id") or ""
        if not option_id:
            continue
        identity = (option_id, row.get("anchorLineId") or "", row.get("anchorMode") or "")
        previous = best_option_rows.get(identity)
        row_rank = (
            0 if row.get("anchorMode") == "trunkBinding" else 1,
            row["start"],
            row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
            row["track"],
        )
        if previous is None:
            best_option_rows[identity] = row
            continue
        previous_rank = (
            0 if previous.get("anchorMode") == "trunkBinding" else 1,
            previous["start"],
            previous.get("optionIndex") if previous.get("optionIndex") is not None else 10**9,
            previous["track"],
        )
        if row_rank < previous_rank:
            best_option_rows[identity] = row

    options = sorted(
        best_option_rows.values(),
        key=lambda row: (
            row["start"],
            row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
            row.get("index") if row.get("index") is not None else 10**9,
            row["id"],
        ),
    )
    duplicate_option_count = len(raw_options) - len(options)
    jump_clips = runtime_jump_clip_rows(timeline, records, records_by_key)
    option_routes = build_option_routes(lines, options, jump_clips)
    return (
        lines,
        options,
        option_routes,
        [_compact_runtime_jump_clip(clip) for clip in jump_clips],
        duplicate_count,
        duplicate_option_count,
    )


def primary_dialog_key(timeline: str, line_ids: list[str]) -> str:
    stems = [stem for line_id in line_ids if (stem := line_stem(line_id))]
    if stems:
        return Counter(stems).most_common(1)[0][0]
    return timeline_stem_to_dialog_key(timeline)


def build_option_anchors(lines: list[dict], options: list[dict]) -> dict[str, dict]:
    line_rows = sorted(lines, key=lambda row: (row.get("start", 0.0), row.get("track") or "", row.get("id") or ""))
    line_by_id = {row.get("id"): row for row in line_rows if row.get("id")}
    anchors: dict[str, dict] = {}

    def row_priority(row: dict, mode: str) -> tuple:
        mode_priority = {
            "trunkBinding": 0,
            "timelinePreviousLine": 1,
            "timelinePre": 2,
        }.get(mode, 3)
        return (
            mode_priority,
            row.get("start", 0.0),
            row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
            row.get("index") if row.get("index") is not None else 10**9,
            row.get("track") or "",
        )

    for row in sorted(options, key=lambda item: row_priority(item, item.get("anchorMode") or "")):
        option_id = str(row.get("id") or "")
        if not option_id:
            continue
        scene_key = option_scene_key(option_id)
        anchor_line_id = str(row.get("anchorLineId") or "")
        mode = str(row.get("anchorMode") or "")

        if anchor_line_id and anchor_line_id in line_by_id:
            if scene_key and line_stem(anchor_line_id) != scene_key:
                anchor_line_id = ""
            else:
                mode = mode or "trunkBinding"

        if not anchor_line_id:
            start = row.get("start", 0.0)
            candidates = [
                line
                for line in line_rows
                if line.get("start", 0.0) <= start + 1e-6
                and (not scene_key or line_stem(line.get("id") or "") == scene_key)
            ]
            if candidates:
                anchor_line_id = candidates[-1]["id"]
                mode = "timelinePreviousLine"
            else:
                mode = "timelinePre"

        anchor = {
            "mode": mode,
            "start": row.get("start", 0.0),
            "duration": row.get("duration", 0.0),
            "track": row.get("track") or "",
            "trackName": row.get("trackName") or "",
            "sourceFile": row.get("sourceFile") or "",
            "assetName": row.get("assetName") or "",
            "assetPathId": row.get("assetPathId"),
        }
        if anchor_line_id:
            anchor["after"] = anchor_line_id
        else:
            anchor["position"] = "pre"

        previous = anchors.get(option_id)
        if previous is not None:
            previous_rank = (
                {
                    "trunkBinding": 0,
                    "timelinePreviousLine": 1,
                    "timelinePre": 2,
                }.get(previous.get("mode"), 3),
                previous.get("start", 0.0),
                previous.get("track") or "",
            )
            current_rank = (
                {
                    "trunkBinding": 0,
                    "timelinePreviousLine": 1,
                    "timelinePre": 2,
                }.get(anchor.get("mode"), 3),
                anchor.get("start", 0.0),
                anchor.get("track") or "",
            )
            if previous_rank <= current_rank:
                continue
        anchors[option_id] = anchor
    return dict(sorted(anchors.items()))


def build_option_groups(options: list[dict], option_anchors: dict[str, dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in options:
        option_id = str(row.get("id") or "")
        group_key = str(row.get("groupKey") or option_group_key(option_id) or "")
        if option_id and group_key:
            grouped[group_key].append(row)

    out: list[dict] = []
    for group_key, rows in sorted(grouped.items(), key=lambda item: (as_int(item[0]) if as_int(item[0]) is not None else 10**9, item[0])):
        seen: set[str] = set()
        option_ids: list[str] = []
        for row in sorted(
            rows,
            key=lambda item: (
                item.get("start", 0.0),
                item.get("optionIndex") if item.get("optionIndex") is not None else 10**9,
                item.get("index") if item.get("index") is not None else 10**9,
                item.get("id") or "",
            ),
        ):
            option_id = row.get("id") or ""
            if option_id and option_id not in seen:
                seen.add(option_id)
                option_ids.append(option_id)
        group = {
            "groupKey": group_key,
            "optionIds": option_ids,
        }
        after_ids = [
            option_anchors[option_id]["after"]
            for option_id in option_ids
            if option_id in option_anchors and option_anchors[option_id].get("after")
        ]
        if after_ids:
            group["after"] = Counter(after_ids).most_common(1)[0][0]
        elif option_ids and all((option_anchors.get(option_id) or {}).get("position") == "pre" for option_id in option_ids):
            group["position"] = "pre"
        out.append(group)
    return out


def derive_option_positions(options: list[dict]) -> list[dict]:
    """Reduce the per-option-row list to one entry per distinct timeline clip
    start time. Each entry carries the scene keys whose option ids occur at
    that moment, so consumer scenes can place their own option group at the
    right slot even when the recorded `_optionId` belongs to a sibling.
    """
    by_start: dict[float, dict] = {}
    for row in options:
        try:
            start = round(float(row.get("start") or 0.0), 3)
        except (TypeError, ValueError):
            continue
        try:
            duration = round(float(row.get("duration") or 0.0), 3)
        except (TypeError, ValueError):
            duration = 0.0
        slot = by_start.setdefault(start, {"start": start, "duration": duration, "scenes": set(), "optionIds": []})
        slot["duration"] = max(slot["duration"], duration)
        scene = option_scene_key(row.get("id") or "")
        if scene:
            slot["scenes"].add(scene)
        opt_id = str(row.get("id") or "").strip()
        if opt_id and opt_id not in slot["optionIds"]:
            slot["optionIds"].append(opt_id)
    out: list[dict] = []
    for slot in sorted(by_start.values(), key=lambda item: item["start"]):
        out.append({
            "start": slot["start"],
            "duration": slot["duration"],
            "scenes": sorted(slot["scenes"]),
            "optionIds": list(slot["optionIds"]),
        })
    return out


def build_timeline_entries_from_roots(
    source_label: str,
    records_by_key: dict[tuple[str, int], dict],
    children_by_parent: dict[tuple[str, int], list[dict]],
    timeline_roots: dict[str, list[dict]],
    timeline_filter: re.Pattern | None = None,
) -> list[dict]:
    entries: list[dict] = []
    for timeline, roots in sorted(timeline_roots.items()):
        if timeline_filter and not timeline_filter.search(timeline):
            continue
        records = walk_track_tree(roots, records_by_key, children_by_parent)
        (
            lines,
            options,
            option_routes,
            runtime_jump_clips,
            duplicate_count,
            duplicate_option_count,
        ) = collect_timeline_signals(timeline, records, records_by_key)
        if not lines and not options:
            continue
        line_ids = [line["id"] for line in lines]
        option_ids = []
        seen_option_ids: set[str] = set()
        for row in options:
            option_id = row.get("id") or ""
            if option_id and option_id not in seen_option_ids:
                seen_option_ids.add(option_id)
                option_ids.append(option_id)
        option_anchors = build_option_anchors(lines, options)
        entry = {
            "timeline": timeline,
            "dialogKey": primary_dialog_key(timeline, line_ids),
            "lineIds": line_ids,
            "lines": lines,
            "source": source_label,
            "sourceRoots": [rel_path(root["path"]) for root in sorted(roots, key=lambda item: rel_path(item["path"]))],
            "trackCount": len(records),
            "duplicateClipCount": duplicate_count,
            # Always emit the key, including an empty list, so downstream
            # recovery can distinguish "scanned and no jump" from legacy data
            # that never preserved raw Runtime Jump evidence.
            "runtimeJumpClips": runtime_jump_clips,
        }
        if option_ids:
            entry["optionIds"] = option_ids
            entry["options"] = options
            entry["optionAnchors"] = option_anchors
            entry["optionGroups"] = build_option_groups(options, option_anchors)
            entry["optionPositions"] = derive_option_positions(options)
            entry["duplicateOptionClipCount"] = duplicate_option_count
            if option_routes:
                entry["optionRoutes"] = option_routes
        entries.append(entry)
    return entries


def parse_extract_dir(mono_dir: Path, timeline_filter: re.Pattern | None = None) -> list[dict]:
    records_by_key, children_by_parent, timeline_roots = load_monobehaviour_records(mono_dir)
    return build_timeline_entries_from_roots(
        rel_path(mono_dir),
        records_by_key,
        children_by_parent,
        timeline_roots,
        timeline_filter,
    )


def path_id_suffix(path_id: int) -> str:
    return f"{(int(path_id) & ((1 << 64) - 1)):016X}"


def discover_full_monobehaviour_dirs(export_root: Path) -> list[Path]:
    root = recovery_root(export_root)
    candidates = [
        root / "StreamingAssets" / "json_by_type" / "MonoBehaviour",
        root / "Persistent" / "json_by_type" / "MonoBehaviour",
    ]
    return [path for path in candidates if path.is_dir()]


def monobehaviour_dir_exceeds_scan_limit(mono_dir: Path, limit: int) -> bool:
    if limit <= 0:
        return False
    count = 0
    try:
        with os.scandir(mono_dir) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue
                if not entry.name.lower().endswith(".json"):
                    continue
                count += 1
                if count > limit:
                    return True
    except OSError as exc:
        log(f"skip full MonoBehaviour size check for {rel_path(mono_dir)}: {exc}")
    return False


def load_targeted_full_monobehaviour_records(
    mono_dir: Path,
    timeline_stems: set[str],
    timeline_filter: re.Pattern | None = None,
) -> tuple[dict[tuple[str, int], dict], dict[tuple[str, int], list[dict]], dict[str, list[dict]]]:
    def stem_selected(timeline: str) -> bool:
        if timeline_stems and timeline not in timeline_stems:
            return False
        if timeline_filter and not timeline_filter.search(timeline):
            return False
        return True

    records_by_key: dict[tuple[str, int], dict] = {}
    children_by_parent: dict[tuple[str, int], list[dict]] = defaultdict(list)
    timeline_roots: dict[str, list[dict]] = defaultdict(list)
    path_index: dict[str, list[Path]] = defaultdict(list)
    seed_paths: list[Path] = []

    for path in sorted(mono_dir.glob("*.json")):
        stem = path.stem
        suffix = path_id_suffix_from_stem(stem)
        if not suffix:
            continue
        path_index[suffix].append(path)
        if "dlgtl_" not in stem or not is_timeline_root_seed_name(stem):
            continue
        timeline = timeline_name_from_record_name(strip_path_id_suffix(stem))
        if timeline and stem_selected(timeline):
            seed_paths.append(path)

    def ensure_record_path(path: Path) -> dict | None:
        meta = extract_monobehaviour_metadata(path)
        if not meta:
            return None
        path_id = as_path_id(meta.get("pathId"))
        source_file = str(meta.get("sourceFile") or "")
        if path_id is None or not source_file:
            return None
        key = (source_file, path_id)
        previous = records_by_key.get(key)
        if previous:
            return previous
        record = {
            "key": key,
            "sourceFile": source_file,
            "pathId": path_id,
            "path": path,
            "name": str(meta.get("name") or path.stem),
            "payload": None,
            "hasChildren": bool(meta.get("hasChildren")),
            "hasClips": bool(meta.get("hasClips")),
        }
        records_by_key[key] = record

        parent_id = as_path_id(meta.get("parentId"))
        if parent_id is not None:
            children_by_parent[(source_file, parent_id)].append(record)

        timeline = timeline_name_from_record_name(record["name"])
        if timeline and stem_selected(timeline) and meta.get("hasTracks"):
            timeline_roots[timeline].append(record)
        return record

    def ensure_record_key(source_file: str, path_id: int) -> dict | None:
        key = (source_file, path_id)
        previous = records_by_key.get(key)
        if previous:
            return previous
        for path in path_index.get(path_id_suffix(path_id), []):
            record = ensure_record_path(path)
            if record and record["key"] == key:
                return record
        return None

    for path in seed_paths:
        ensure_record_path(path)

    queue = deque(root["key"] for roots in timeline_roots.values() for root in roots)
    seen: set[tuple[str, int]] = set()
    while queue:
        key = queue.popleft()
        if key in seen:
            continue
        seen.add(key)
        record = records_by_key.get(key)
        if not record:
            continue
        source_file, _path_id = key
        payload = record_payload(record)
        for ref_id in iter_structural_ref_ids(payload):
            child = ensure_record_key(source_file, ref_id)
            if child and should_walk_timeline_record(child):
                queue.append(child["key"])
        for ref_id in iter_asset_ref_ids(payload):
            ensure_record_key(source_file, ref_id)
        for child in children_by_parent.get(key, []):
            if should_walk_timeline_record(child):
                queue.append(child["key"])

    return records_by_key, children_by_parent, timeline_roots


def parse_full_monobehaviour_dir(
    mono_dir: Path,
    timeline_stems: set[str],
    timeline_filter: re.Pattern | None = None,
) -> list[dict]:
    records_by_key, children_by_parent, timeline_roots = load_targeted_full_monobehaviour_records(
        mono_dir,
        timeline_stems,
        timeline_filter,
    )
    return build_timeline_entries_from_roots(
        rel_path(mono_dir),
        records_by_key,
        children_by_parent,
        timeline_roots,
        timeline_filter,
    )


def collapse_by_dialog_key(entries: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        key = entry.get("dialogKey") or timeline_stem_to_dialog_key(entry.get("timeline") or "")
        if key:
            grouped[key].append(entry)

    payload: dict = {
        "_meta": {
            "generatedBy": "scripts/story_builder/timeline_recovery.py",
            "timelineCount": len(entries),
            "dialogKeyCount": len(grouped),
            "optionTimelineCount": sum(1 for entry in entries if entry.get("optionIds")),
            "optionCount": len({
                option_id
                for entry in entries
                for option_id in (entry.get("optionIds") or [])
            }),
            "optionAnchorCount": sum(len(entry.get("optionAnchors") or {}) for entry in entries),
            "optionRouteCount": sum(len(entry.get("optionRoutes") or {}) for entry in entries),
        }
    }
    for key, variants in sorted(grouped.items()):
        variants.sort(key=timeline_entry_rank)
        best = dict(variants[0])
        if len(variants) > 1:
            best["variants"] = variants
            best["variantCount"] = len(variants)
        payload[key] = best
    return payload


def payload_dialog_entries(payload: dict, key: str) -> list[dict]:
    entry = payload.get(key)
    if not isinstance(entry, dict):
        return []
    variants = entry.get("variants")
    if isinstance(variants, list) and variants:
        return [dict(variant) for variant in variants if isinstance(variant, dict)]
    return [dict(entry)]


def timeline_entry_identity(entry: dict) -> tuple:
    return (
        str(entry.get("timeline") or ""),
        tuple(sorted(str(line_id) for line_id in (entry.get("lineIds") or []))),
        tuple(str(option_id) for option_id in (entry.get("optionIds") or [])),
        json.dumps(entry.get("optionAnchors") or {}, sort_keys=True, ensure_ascii=False),
    )


def timeline_entry_has_line_sources(entry: dict) -> bool:
    return any(
        isinstance(line, dict) and bool(line.get("lineIdSource"))
        for line in (entry.get("lines") or [])
    )


def timeline_entry_has_line_clip_option_indices(entry: dict) -> bool:
    return any(
        isinstance(line, dict) and isinstance(line.get("clipOptionIndex"), int)
        for line in (entry.get("lines") or [])
    )


def timeline_entry_option_route_count(entry: dict) -> int:
    routes = entry.get("optionRoutes")
    return len(routes) if isinstance(routes, dict) else 0


def timeline_entry_rank(entry: dict) -> tuple:
    return (
        -len(entry.get("lineIds") or []),
        0 if entry.get("optionAnchors") else 1,
        -timeline_entry_option_route_count(entry),
        0 if timeline_entry_has_line_sources(entry) else 1,
        0 if timeline_entry_has_line_clip_option_indices(entry) else 1,
        str(entry.get("timeline") or ""),
        str(entry.get("source") or ""),
    )


def merge_timeline_payloads(base_payload: dict, update_payload: dict) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for payload in (base_payload, update_payload):
        if not isinstance(payload, dict):
            continue
        for key in sorted(k for k in payload if not str(k).startswith("_")):
            grouped[str(key)].extend(payload_dialog_entries(payload, str(key)))

    merged: dict = {
        "_meta": {
            "generatedBy": "scripts/story_builder/timeline_recovery.py",
            "merged": True,
        }
    }
    timeline_count = 0
    option_timeline_count = 0
    option_ids: set[str] = set()
    option_anchor_count = 0
    option_route_count = 0
    for key, entries in sorted(grouped.items()):
        deduped: dict[tuple, dict] = {}
        for entry in entries:
            identity = timeline_entry_identity(entry)
            previous = deduped.get(identity)
            if previous is None or timeline_entry_rank(entry) < timeline_entry_rank(previous):
                deduped[identity] = entry
        variants = sorted(deduped.values(), key=timeline_entry_rank)
        if not variants:
            continue
        best = dict(variants[0])
        if len(variants) > 1:
            best["variants"] = variants
            best["variantCount"] = len(variants)
        merged[key] = best
        timeline_count += len(variants)
        option_timeline_count += sum(1 for entry in variants if entry.get("optionIds"))
        for entry in variants:
            option_ids.update(str(opt_id) for opt_id in (entry.get("optionIds") or []) if opt_id)
            option_anchor_count += len(entry.get("optionAnchors") or {})
            option_route_count += timeline_entry_option_route_count(entry)

    merged["_meta"].update({
        "timelineCount": timeline_count,
        "dialogKeyCount": len([key for key in merged if not key.startswith("_")]),
        "optionTimelineCount": option_timeline_count,
        "optionCount": len(option_ids),
        "optionAnchorCount": option_anchor_count,
        "optionRouteCount": option_route_count,
    })
    return merged


def select_timeline_filter(
    available_counts: Counter,
    timeline_list: Path | None,
    target_report: Path | None,
    target_statuses: set[str],
    include_sibling_prefixes: bool,
    timeline_regex: str | None,
) -> tuple[Callable[[str], bool], dict | None, set[str]]:
    exact_stems: set[str] = set()
    report_summary = None

    if timeline_list:
        exact_stems.update(load_timeline_list(timeline_list))
        log(f"timeline list selected {len(exact_stems)} exact stem(s)")

    if target_report:
        target_report = target_report if target_report.is_absolute() else ROOT / target_report
        stems, report_summary = derive_report_target_stems(
            target_report,
            available_counts,
            target_statuses,
            include_sibling_prefixes,
        )
        exact_stems.update(stems)
        log(
            "report selected "
            f"{report_summary['matchedSceneCount']}/{report_summary['sceneCount']} scene(s), "
            f"{report_summary['timelineStemCount']} timeline stem(s)"
        )

    compiled_regex = re.compile(timeline_regex, re.IGNORECASE) if timeline_regex else None

    def selected(stem: str) -> bool:
        if exact_stems and stem not in exact_stems:
            return False
        if compiled_regex and not compiled_regex.search(stem):
            return False
        return True

    return selected, report_summary, exact_stems


def recover_timeline_line_orders(config: TimelineRecoveryConfig | None = None) -> dict:
    config = config or TimelineRecoveryConfig()
    export_root = config.export_root if config.export_root.is_absolute() else ROOT / config.export_root
    extract_dir = config.extract_dir or default_extract_dir(export_root)
    order_out = config.order_out or default_order_out(export_root)
    extract_dir = extract_dir if extract_dir.is_absolute() else ROOT / extract_dir
    order_out = order_out if order_out.is_absolute() else ROOT / order_out

    map_paths = config.maps or ([] if config.parse_only else discover_asset_maps(export_root))
    if not map_paths and not config.parse_only:
        raise FileNotFoundError(f"No AnimeStudio CLI AssetMaps found under {recovery_root(export_root)}")

    loaded_maps: list[tuple[Path, list[dict]]] = []
    available_counts: Counter = Counter()
    map_summaries: list[dict] = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    timeline_counts: Counter = Counter()
    report_summary = None
    timeline_filter = re.compile(config.timeline_regex, re.IGNORECASE) if config.timeline_regex else None
    if config.parse_only:
        target_summary = {
            "timelineFolderCount": 0,
            "assetEntryCount": 0,
            "chkCount": 0,
            "timelineFolders": {},
            "report": None,
            "parseOnly": True,
        }
    else:
        for map_path in map_paths:
            map_path = map_path if map_path.is_absolute() else ROOT / map_path
            if not map_path.exists():
                log(f"skip missing map: {rel_path(map_path)}")
                continue
            entries = load_entries(map_path)
            loaded_maps.append((map_path, entries))
            counts = count_timeline_stems(entries)
            available_counts.update(counts)
            map_summaries.append({
                "map": rel_path(map_path),
                "assetEntries": len(entries),
                "timelineFolders": len(counts),
                "timelineEntries": sum(counts.values()),
            })

        selected_stem, report_summary, _exact_stems = select_timeline_filter(
            available_counts,
            config.timeline_list,
            config.target_report,
            config.target_statuses,
            config.include_sibling_prefixes,
            config.timeline_regex,
        )

        for map_path, entries in loaded_maps:
            per_source = group_by_source(entries, selected_stem)
            for source, items in per_source.items():
                grouped[source].extend(items)
            current_counts = count_timeline_stems(entries, selected_stem)
            timeline_counts.update(current_counts)
            log(
                f"{map_path.name}: {sum(len(items) for items in per_source.values())} entries, "
                f"{len(current_counts)} timeline folder(s), across {len(per_source)} chk(s)"
            )

        target_summary = {
            "timelineFolderCount": len(timeline_counts),
            "assetEntryCount": sum(timeline_counts.values()),
            "chkCount": len(grouped),
            "timelineFolders": dict(sorted(timeline_counts.items())),
            "report": report_summary,
        }

    target_timeline_stems = {
        str(stem)
        for stem in ((target_summary.get("timelineFolders") or {}) if isinstance(target_summary, dict) else {})
        if str(stem)
    }
    if config.timeline_list:
        timeline_list = config.timeline_list if config.timeline_list.is_absolute() else ROOT / config.timeline_list
        target_timeline_stems.update(load_timeline_list(timeline_list))

    extract_summary: list[dict] = []
    entries: list[dict] = []
    parse_summary: list[dict] = []
    extract_skipped_reason: str | None = None
    t_extract = time.time()

    if config.dry_run:
        log("dry run requested; skipped full MonoBehaviour parse")
    elif not config.prefer_full_monobehaviour:
        log("filtered timeline extraction requested; skipped full MonoBehaviour parse")
        parse_summary.append({
            "source": "fullMonoBehaviour",
            "timelineCount": 0,
            "skippedReason": "filtered-extraction",
        })
    else:
        for mono_dir in discover_full_monobehaviour_dirs(export_root):
            if monobehaviour_dir_exceeds_scan_limit(
                mono_dir,
                config.full_monobehaviour_scan_limit,
            ):
                log(
                    f"{rel_path(mono_dir)}: skipped full MonoBehaviour parse; "
                    f"more than {config.full_monobehaviour_scan_limit} JSON files"
                )
                parse_summary.append({
                    "monoDir": rel_path(mono_dir),
                    "timelineCount": 0,
                    "source": "fullMonoBehaviour",
                    "skippedReason": "scan-limit",
                    "scanLimit": config.full_monobehaviour_scan_limit,
                })
                continue
            parsed = parse_full_monobehaviour_dir(mono_dir, target_timeline_stems, timeline_filter)
            parsed = [entry for entry in parsed if len(entry.get("lineIds") or []) >= config.min_lines]
            log(f"{rel_path(mono_dir)}: {len(parsed)} timeline(s) with dialog clips from full MonoBehaviour")
            parse_summary.append({
                "monoDir": rel_path(mono_dir),
                "timelineCount": len(parsed),
                "source": "fullMonoBehaviour",
            })
            entries.extend(parsed)

    full_entry_count = len(entries)
    focused_run = bool(config.target_report or config.timeline_list or config.timeline_regex or config.limit_chks > 0)
    full_monobehaviour_incomplete = any(
        item.get("skippedReason") == "scan-limit"
        for item in parse_summary
        if isinstance(item, dict)
    )
    should_process_chks = not config.parse_only
    should_run_cli = should_process_chks and not config.dry_run
    if (
        config.prefer_full_monobehaviour
        and full_entry_count
        and not focused_run
        and not full_monobehaviour_incomplete
    ):
        should_process_chks = False
        should_run_cli = False
        extract_skipped_reason = "full-monobehaviour"
        log(
            f"full MonoBehaviour supplied {full_entry_count} timeline(s); "
            "skipping filtered timeline_extract export"
        )
    elif config.prefer_full_monobehaviour and full_entry_count and full_monobehaviour_incomplete:
        log(
            f"full MonoBehaviour supplied {full_entry_count} timeline(s), but one or more "
            "MonoBehaviour roots were scan-limited; running filtered timeline_extract export"
        )
    elif config.parse_only:
        extract_skipped_reason = "parse-only"
    elif config.dry_run:
        extract_skipped_reason = "dry-run"

    cli = resolve_cli(config.cli) if should_run_cli else None
    if should_run_cli and not config.keep_extract and extract_dir.exists():
        log(f"wiping {rel_path(extract_dir)}")
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "timeline_targets.json").write_text(
        json.dumps(target_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    chks = sorted(grouped.keys())
    if config.limit_chks > 0:
        chks = chks[: config.limit_chks]

    if should_process_chks:
        for index, source in enumerate(chks, 1):
            chk_path = Path(source)
            out_dir = extract_dir / chk_path.stem
            filter_data_path = out_dir / "filter_data.json"
            write_filter_data(grouped[source], filter_data_path)
            log(f"[{index}/{len(chks)}] {chk_path.stem}: {len(grouped[source])} item(s)")
            if config.dry_run:
                extract_summary.append({
                    "chk": chk_path.stem,
                    "items": len(grouped[source]),
                    "rc": None,
                    "produced": 0,
                    "seconds": 0.0,
                })
                continue
            t0 = time.time()
            rc = run_cli(cli, chk_path, out_dir, filter_data_path) if cli else 1
            elapsed = time.time() - t0
            mono_dir = out_dir / "MonoBehaviour"
            produced = sum(1 for _ in mono_dir.glob("*.json")) if mono_dir.is_dir() else 0
            log(f"    rc={rc} produced={produced} elapsed={elapsed:.1f}s")
            extract_summary.append({
                "chk": chk_path.stem,
                "items": len(grouped[source]),
                "rc": rc,
                "produced": produced,
                "seconds": round(elapsed, 1),
            })
            if rc != 0:
                raise RuntimeError(f"AnimeStudio CLI failed for {chk_path} with rc={rc}")

    parse_extract_outputs = config.parse_only or should_run_cli
    if config.dry_run:
        log("dry run complete; skipped parse and output JSON")
    else:
        mono_dirs = discover_extract_dirs([extract_dir]) if parse_extract_outputs else []
        if parse_extract_outputs and not mono_dirs and not entries:
            raise RuntimeError(f"No MonoBehaviour directories found under {extract_dir}")
        for mono_dir in mono_dirs:
            parsed = parse_extract_dir(mono_dir, timeline_filter)
            parsed = [entry for entry in parsed if len(entry.get("lineIds") or []) >= config.min_lines]
            log(f"{rel_path(mono_dir)}: {len(parsed)} timeline(s) with dialog clips")
            parse_summary.append({"monoDir": rel_path(mono_dir), "timelineCount": len(parsed)})
            entries.extend(parsed)

        payload = collapse_by_dialog_key(entries)
        if focused_run and order_out.exists():
            existing_payload = load_json(order_out)
            if isinstance(existing_payload, dict):
                payload = merge_timeline_payloads(existing_payload, payload)
        order_out.parent.mkdir(parents=True, exist_ok=True)
        order_text = json.dumps(payload, ensure_ascii=False, indent=2)
        order_out.write_text(order_text, encoding="utf-8")
        if config.copy_to_webui:
            copy_path = config.copy_to_webui if config.copy_to_webui.is_absolute() else ROOT / config.copy_to_webui
            copy_path.parent.mkdir(parents=True, exist_ok=True)
            copy_path.write_text(order_text, encoding="utf-8")
        meta = payload["_meta"]
        log(f"wrote {rel_path(order_out)} ({meta['timelineCount']} timeline(s), {meta['dialogKeyCount']} dialog key(s))")

    summary = {
        "generatedBy": "scripts/story_builder/timeline_recovery.py",
        "generatedAt": int(time.time()),
        "exportRoot": rel_path(export_root),
        "extractDir": rel_path(extract_dir),
        "orderOut": rel_path(order_out),
        "dryRun": config.dry_run,
        "parseOnly": config.parse_only,
        "preferFullMonoBehaviour": config.prefer_full_monobehaviour,
        "maps": map_summaries,
        "targets": target_summary,
        "extractSkippedReason": extract_skipped_reason,
        "extract": extract_summary,
        "parse": parse_summary,
        "elapsedSeconds": round(time.time() - t_extract, 1),
    }
    (extract_dir / "timeline_recovery_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def csv_set(value: str) -> set[str]:
    return {part.strip() for part in str(value or "").split(",") if part.strip()}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--cli", type=Path, help="Path to AnimeStudio.CLI.exe. Defaults to ANIMESTUDIO_CLI or tools/AnimeStudio.")
    parser.add_argument("--maps", type=Path, nargs="+", help="AssetMap JSON files. Defaults to discovered AnimeStudio-cli maps.")
    parser.add_argument("--extract-dir", type=Path, help="Where filtered Timeline exports should be written.")
    parser.add_argument("--out", type=Path, help="Output timeline_line_orders.json path.")
    parser.add_argument("--timeline-regex", help="Optional regex filter applied to timeline folder stems.")
    parser.add_argument("--timeline-list", type=Path, help="Optional text/JSON list of exact timeline stems.")
    parser.add_argument("--target-report", type=Path, help="Optional scene-order gap report to focus extraction.")
    parser.add_argument("--target-statuses", default="fallback,partial", help="Comma-separated lineOrderStatus values for --target-report.")
    parser.add_argument("--include-sibling-prefixes", action="store_true", help="With --target-report, include sibling-numbered timeline folders for unmatched scenes.")
    parser.add_argument("--keep-extract", action="store_true", help="Do not wipe the extract directory before exporting.")
    parser.add_argument("--parse-only", action="store_true", help="Parse the existing extract directory without running AnimeStudio CLI.")
    parser.add_argument(
        "--extract-timeline-assets",
        action="store_true",
        help="Force filtered AnimeStudio CLI extraction even when full MonoBehaviour exports are sufficient.",
    )
    parser.add_argument("--reuse-current", action="store_true", help="Skip recovery if the output is newer than maps and this script.")
    parser.add_argument("--dry-run", action="store_true", help="Write filter_data and summaries, but do not run the CLI or parse output.")
    parser.add_argument("--limit-chks", type=int, default=0, help="Optional smoke-test limit for number of chk files.")
    parser.add_argument("--min-lines", type=int, default=1, help="Only emit parsed timelines with at least this many recovered lines.")
    parser.add_argument(
        "--full-monobehaviour-scan-limit",
        type=int,
        default=TimelineRecoveryConfig.full_monobehaviour_scan_limit,
        help=(
            "Skip full json_by_type/MonoBehaviour parsing when a source folder has "
            "more JSON files than this; use 0 to disable the limit."
        ),
    )
    parser.add_argument("--copy-to-webui", action="store_true", help="Also write webui/data/timeline_line_orders.json.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_root = args.export_root if args.export_root.is_absolute() else ROOT / args.export_root
    maps = args.maps or discover_asset_maps(export_root)
    out_path = args.out or default_order_out(export_root)
    out_path = out_path if out_path.is_absolute() else ROOT / out_path
    if args.reuse_current and timeline_order_is_current(out_path, maps):
        log(f"using current {rel_path(out_path)}")
        return 0

    copy_to_webui = ROOT / "webui" / "data" / "timeline_line_orders.json" if args.copy_to_webui else None
    config = TimelineRecoveryConfig(
        export_root=export_root,
        cli=args.cli,
        maps=maps,
        extract_dir=args.extract_dir,
        order_out=out_path,
        target_report=args.target_report,
        target_statuses=csv_set(args.target_statuses),
        include_sibling_prefixes=args.include_sibling_prefixes,
        timeline_regex=args.timeline_regex,
        timeline_list=args.timeline_list,
        keep_extract=args.keep_extract,
        parse_only=args.parse_only,
        dry_run=args.dry_run,
        limit_chks=args.limit_chks,
        min_lines=args.min_lines,
        copy_to_webui=copy_to_webui,
        prefer_full_monobehaviour=not args.extract_timeline_assets,
        full_monobehaviour_scan_limit=args.full_monobehaviour_scan_limit,
    )
    recover_timeline_line_orders(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
