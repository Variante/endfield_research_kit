from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from package_webui import (
    ENV_EMOJI_FALLBACK_LAYER_STEMS,
    ENV_EMOJI_PREFAB_LAYER_STEMS,
    collect_inline_image_ids,
    collect_wiki_media_image_ids,
    inline_image_number_key,
    normalize_inline_image_id,
    resolve_env_emoji_prefab_key,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_OUTPUT = ROOT / "export_full"
DEFAULT_REPORTS = ROOT / "reports"
DEFAULT_FLUFFY = ROOT / "tools" / "fluffy-dumper-src" / "target" / "release" / "fluffy-dumper.exe"
DEFAULT_ANIMESTUDIO = ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"
DEFAULT_STRUCTURED_DUMPER = DEFAULT_ANIMESTUDIO
SOURCES = ("StreamingAssets", "Persistent")
ANIMESTUDIO_STAGES = ("maps", "convert_by_type", "json_by_type")
ANIMESTUDIO_SCOPES = ("story", "assets", "all")
ANIMESTUDIO_ASSET_MODES = ("webui", "full", "debug")
ANIMESTUDIO_GAME = "ArknightsEndfield"
ANIMESTUDIO_LOGGER_FLAGS = ("Warning", "Error")
ANIMESTUDIO_DEFAULT_JOBS = 4
ANIMESTUDIO_DEFAULT_SHARDS = 16
ANIMESTUDIO_DUMMY_DLL_ENV = "ANIMESTUDIO_DUMMY_DLLS"
ANIMESTUDIO_MANIFEST_SCHEMA_VERSION = 2
ANIMESTUDIO_ASSET_CACHE_SCHEMA_VERSION = 1
ANIMESTUDIO_MANIFEST_MAP_ITEM = "__maps__"
ANIMESTUDIO_MANIFEST_MAP_LABEL = "maps"
SOURCE_NAME_SET = frozenset(source.lower() for source in SOURCES)
ANIMESTUDIO_TEXTURE_EXTENSION = ".png"
ANIMESTUDIO_CONVERT_OUTPUT_EXTENSIONS = {
    "Texture2D": ANIMESTUDIO_TEXTURE_EXTENSION,
    "Sprite": ANIMESTUDIO_TEXTURE_EXTENSION,
    "Mesh": ".obj",
    "Shader": ".shader",
    "AnimationClip": ".anim",
}
ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES = frozenset({
    # Some Mesh assets are accepted by AnimeStudio without producing an OBJ.
    # Cache those no-output successes so future runs do not retry them forever.
    "Mesh",
})
ANIMESTUDIO_MAX_SAFE_FILE_NAME_LENGTH = 120
ANIMESTUDIO_RESERVED_FILE_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
)
WINDOWS_INVALID_FILE_NAME_CHARS = frozenset('<>:"/\\|?*')
# Asset maps for Endfield have no GameObject, AudioClip, VideoClip,
# MovieTexture, or MiHoYoBinData entries, so the WebUI export skips them.
ANIMESTUDIO_FULL_CONVERT_TYPES = (
    "Texture2D:Both",
    "Mesh:Both",
    "Sprite:Both",
    "Animator:Both",
)
ANIMESTUDIO_DEBUG_CONVERT_TYPES = (
    "Texture2D:Both",
    "Shader:Both",
    "TextAsset:Both",
    "Font:Both",
    "Mesh:Both",
    "Sprite:Both",
    "Animator:Both",
    "AnimationClip:Both",
)
ANIMESTUDIO_WEBUI_CONVERT_TYPES = (
    "Texture2D:Both",
)
ANIMESTUDIO_STORY_JSON_TYPES = (
    "TextAsset:Both",
    "MonoBehaviour:Both",
    "PlayableDirector:Both",
)
ANIMESTUDIO_FULL_JSON_TYPES = (
    "Material:Both",
)
ANIMESTUDIO_DEBUG_JSON_TYPES = (
    "TextAsset:Both",
    "MonoBehaviour:Both",
    "Material:Both",
    "AssetBundle:Both",
    "IndexObject:Both",
    "AnimatorController:Both",
    "AnimatorOverrideController:Both",
    "MonoScript:Both",
    "PlayerSettings:Both",
    "PlayableDirector:Both",
    "ResourceManager:Both",
    "SpriteAtlas:Both",
    "NapAssetBundleIndexAsset:Both",
    # PreloadData (Unity ClassID 150) exposes per-bundle asset-cohort PPtrs,
    # useful for identifying which assets load together with each cutscene.
    # AvatarMask (319) carries body-part transform masks per animation, which
    # validates which body parts move during each cutscene. Both rely on the
    # generic TypeTree fallback in AnimeStudio (no dedicated parser needed).
    "PreloadData:Both",
    "AvatarMask:Both",
)
ANIMESTUDIO_WEBUI_JSON_TYPES: tuple[str, ...] = ()
ANIMESTUDIO_ASSET_MAP_FILTER_UNSAFE_TYPES = frozenset({
    # Animator FBX export can need related GameObject, Mesh, Material, and
    # Texture2D objects that a strict Animator-only map slice would not load.
    "Animator",
    "GameObject",
})

FAILED_EXTRACT_RE = re.compile(r"Failed to extract (?P<file>.+?): (?P<reason>.+)")
WARNING_FAIL_RE = re.compile(r"Warning:\s+(?P<count>\d+)\s+files failed")
ANIMESTUDIO_LOG_LINE_RE = re.compile(r"^\[(?P<level>Error|Warning)\]\s*(?P<message>.*)$")
ANIMESTUDIO_EXPORT_ERROR_RE = re.compile(r"^\[Error\]\s+Export\s+(?P<asset>.+?)\s+error\s*$")
ANIMESTUDIO_METADATA_ONLY_JSON_RE = re.compile(
    r"^\[Warning\]\s+Exporting MonoBehaviour (?P<asset>.+?) as metadata-only JSON after (?P<exception>[^:]+): (?P<reason>.+)$"
)
ANIMESTUDIO_STORY_HINT_RE = re.compile(
    r"(dlg|dlgtl|dialog|timeline|cutscene|option|trunk|playable)",
    re.IGNORECASE,
)
ANIMESTUDIO_LOG_SAMPLE_LIMIT = 20


@dataclass
class CommandResult:
    name: str
    argv: list[str]
    cwd: str
    returncode: int
    duration_seconds: float
    stdout_log: str
    stderr_log: str


def ordered_unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def stable_hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_file_signature(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    stat = resolved.stat()
    payload = {
        "path": str(resolved),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    payload["fingerprint"] = stable_hash(payload)
    return payload


def regex_exact(value: str) -> str:
    return f"^{re.escape(value)}$"


def regex_prefix(value: str) -> str:
    return f"^{re.escape(value)}_.+"


def collect_webui_texture_name_patterns() -> list[str]:
    webui_root = ROOT / "webui"
    image_ids = collect_inline_image_ids(webui_root) | collect_wiki_media_image_ids(webui_root)
    patterns: set[str] = set()

    def add_stem(value: str, *, include_layers: bool = False) -> None:
        stem = normalize_inline_image_id(value)
        if not stem:
            return
        patterns.add(regex_exact(stem))
        patterns.add(regex_exact(f"{stem}_m"))
        patterns.add(regex_exact(f"{stem}_f"))
        if include_layers and not stem.isdigit():
            patterns.add(regex_prefix(stem))

    for image_id in sorted(image_ids):
        normalized = normalize_inline_image_id(image_id)
        if not normalized:
            continue
        add_stem(normalized, include_layers=True)

        prefab_key = resolve_env_emoji_prefab_key(normalized)
        if prefab_key:
            for stem in ENV_EMOJI_PREFAB_LAYER_STEMS.get(prefab_key, ()):
                add_stem(stem)
        for stem in ENV_EMOJI_FALLBACK_LAYER_STEMS.get(normalized, ()):
            add_stem(stem)

        if normalized.startswith("sns_image_"):
            add_stem(f"cg_image_{normalized[len('sns_image_'):]}", include_layers=True)

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
                add_stem(stem)

    return sorted(patterns)


def write_webui_texture_name_filter(output_root: Path) -> tuple[Path, dict[str, Any]]:
    filter_dir = ensure_dir(animestudio_work_dir(output_root) / "filters")
    filter_path = filter_dir / "webui_texture2d_names.txt"
    patterns = collect_webui_texture_name_patterns()
    if not patterns:
        raise SystemExit(
            "WebUI asset mode produced no Texture2D name patterns; refusing to run a broad Texture2D export. "
            "Use --animestudio-asset-mode full/debug or fix the WebUI media references."
        )
    content = "\n".join(patterns) + "\n"
    if not filter_path.exists() or filter_path.read_text(encoding="utf-8-sig") != content:
        filter_path.write_text(content, encoding="utf-8")
    signature = {
        "path": str(filter_path.resolve()),
        "pattern_count": len(patterns),
        "patterns_fingerprint": stable_hash(patterns),
    }
    return filter_path, signature


def build_dummy_dll_signature(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None

    resolved = path.resolve()
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    latest_mtime_ns = 0
    for dll_path in sorted((item for item in resolved.rglob("*.dll") if item.is_file()), key=lambda p: str(p).lower()):
        stat = dll_path.stat()
        rel = dll_path.relative_to(resolved).as_posix()
        total_bytes += stat.st_size
        latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
        entries.append(
            {
                "path": rel,
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )

    payload = {
        "path": str(resolved),
        "dll_count": len(entries),
        "bytes": total_bytes,
        "latest_mtime_ns": latest_mtime_ns,
        "fingerprint": stable_hash(entries),
    }
    return payload


def animestudio_manifest_path(output_root: Path) -> Path:
    return output_root / "recovered" / "AnimeStudio-cli" / "animestudio_type_manifest.json"


def default_animestudio_manifest() -> dict[str, Any]:
    return {
        "schema_version": ANIMESTUDIO_MANIFEST_SCHEMA_VERSION,
        "entries": {},
    }


def load_animestudio_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_animestudio_manifest()

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        log(f"unable to parse AnimeStudio manifest at {path}; starting with an empty manifest")
        return default_animestudio_manifest()

    if not isinstance(data, dict):
        return default_animestudio_manifest()

    manifest = dict(data)
    manifest["schema_version"] = ANIMESTUDIO_MANIFEST_SCHEMA_VERSION
    if not isinstance(manifest.get("entries"), dict):
        manifest["entries"] = {}
    return manifest


def save_animestudio_manifest(path: Path, manifest: dict[str, Any]) -> None:
    payload = dict(manifest)
    payload["schema_version"] = ANIMESTUDIO_MANIFEST_SCHEMA_VERSION
    payload["last_updated_epoch"] = int(time.time())
    ensure_dir(path.parent)
    write_json(path, payload)


def animestudio_asset_cache_path(output_root: Path) -> Path:
    return animestudio_work_dir(output_root) / "animestudio_asset_cache.json"


def default_animestudio_asset_cache() -> dict[str, Any]:
    return {
        "schema_version": ANIMESTUDIO_ASSET_CACHE_SCHEMA_VERSION,
        "entries": {},
    }


def load_animestudio_asset_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_animestudio_asset_cache()
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        log(f"unable to parse AnimeStudio asset cache at {path}; starting with an empty cache")
        return default_animestudio_asset_cache()
    if not isinstance(data, dict):
        return default_animestudio_asset_cache()
    payload = dict(data)
    payload["schema_version"] = ANIMESTUDIO_ASSET_CACHE_SCHEMA_VERSION
    if not isinstance(payload.get("entries"), dict):
        payload["entries"] = {}
    return payload


def save_animestudio_asset_cache(path: Path, cache: dict[str, Any]) -> None:
    payload = dict(cache)
    payload["schema_version"] = ANIMESTUDIO_ASSET_CACHE_SCHEMA_VERSION
    payload["last_updated_epoch"] = int(time.time())
    ensure_dir(path.parent)
    write_json(path, payload)


def regex_literal_body(pattern: str, suffix: str) -> str | None:
    if not pattern.startswith("^") or not pattern.endswith(suffix):
        return None
    body = pattern[1 : len(pattern) - len(suffix)]
    result: list[str] = []
    i = 0
    meta_chars = set(".^$*+?{}[]\\|()")
    while i < len(body):
        ch = body[i]
        if ch == "\\":
            if i + 1 >= len(body):
                return None
            result.append(body[i + 1])
            i += 2
            continue
        if ch in meta_chars:
            return None
        result.append(ch)
        i += 1
    return "".join(result)


class RegexListMatcher:
    def __init__(self, exacts: set[str], prefixes: set[str], regexes: list[re.Pattern[str]]) -> None:
        self.exacts = exacts
        self.prefixes = prefixes
        self.regexes = regexes

    @classmethod
    def from_path(cls, path: str | Path | None) -> "RegexListMatcher":
        if path is None:
            return cls(set(), set(), [])

        exacts: set[str] = set()
        prefixes: set[str] = set()
        regexes: list[re.Pattern[str]] = []
        for raw_line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            pattern = raw_line.strip()
            if not pattern or pattern.startswith("#"):
                continue
            exact = regex_literal_body(pattern, "$")
            if exact is not None:
                exacts.add(exact.casefold())
                continue
            prefix = regex_literal_body(pattern, "_.+")
            if prefix is not None:
                prefixes.add(f"{prefix}_".casefold())
                continue
            regexes.append(re.compile(pattern, re.IGNORECASE))
        return cls(exacts, prefixes, regexes)

    def is_empty(self) -> bool:
        return not self.exacts and not self.prefixes and not self.regexes

    def matches(self, value: str) -> bool:
        if self.is_empty():
            return True
        folded = value.casefold()
        if folded in self.exacts:
            return True
        for idx, ch in enumerate(folded):
            if ch == "_" and folded[: idx + 1] in self.prefixes and idx + 1 < len(folded):
                return True
        return any(regex.search(value) for regex in self.regexes)


def normalize_asset_map_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.suffix.lower() == ".map":
        return candidate.with_suffix(".json")
    if candidate.suffix:
        return candidate
    return candidate.with_suffix(".json")


def load_animestudio_asset_map_entries(map_path: Path) -> list[dict[str, Any]]:
    data = json.loads(map_path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        entries = data.get("AssetEntries") or []
    else:
        entries = data
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def filter_animestudio_asset_map_entries(
    map_path: Path,
    type_name: str,
    names: str | Path | None,
    containers: str | Path | None,
    entries: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    name_matcher = RegexListMatcher.from_path(names)
    container_matcher = RegexListMatcher.from_path(containers)
    result: list[dict[str, Any]] = []
    source_entries = entries if entries is not None else load_animestudio_asset_map_entries(map_path)
    for entry in source_entries:
        if str(entry.get("Type") or "") != type_name:
            continue
        if not name_matcher.matches(str(entry.get("Name") or "")):
            continue
        if not container_matcher.matches(str(entry.get("Container") or "")):
            continue
        result.append(entry)
    return result


def fix_animestudio_file_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        text = "unnamed"
    sanitized = "".join(
        "_" if ch in WINDOWS_INVALID_FILE_NAME_CHARS or ord(ch) < 32 else ch
        for ch in text
    ).strip().rstrip(". ")
    if not sanitized:
        sanitized = "unnamed"
    if sanitized.upper() in ANIMESTUDIO_RESERVED_FILE_NAMES:
        sanitized = f"_{sanitized}"
    if len(sanitized) > ANIMESTUDIO_MAX_SAFE_FILE_NAME_LENGTH:
        digest = hashlib.sha1(sanitized.encode("utf-8")).hexdigest()[:10]
        prefix_length = max(16, ANIMESTUDIO_MAX_SAFE_FILE_NAME_LENGTH - len(digest) - 1)
        sanitized = f"{sanitized[:prefix_length].rstrip('. ')}_{digest}"
    return sanitized


def format_animestudio_path_id(value: Any) -> str:
    return f"{int(value) & ((1 << 64) - 1):016X}"


def animestudio_convert_output_extension(type_name: str) -> str | None:
    return ANIMESTUDIO_CONVERT_OUTPUT_EXTENSIONS.get(type_name)


def animestudio_asset_cache_supported(stage: str, options: dict[str, Any], type_name: str) -> bool:
    return (
        stage == "convert_by_type"
        and options.get("export_type") == "Convert"
        and animestudio_convert_output_extension(type_name) is not None
    )


def predict_animestudio_convert_output_path(
    output_root: Path,
    source: str,
    stage: str,
    entry: dict[str, Any],
) -> Path | None:
    type_name = str(entry.get("Type") or "")
    if stage != "convert_by_type":
        return None
    extension = animestudio_convert_output_extension(type_name)
    if extension is None:
        return None
    file_name = fix_animestudio_file_name(entry.get("Name"))
    path_id = format_animestudio_path_id(entry.get("PathID") or 0)
    return animestudio_stage_dir(output_root, source, stage) / type_name / f"{file_name}_p{path_id}{extension}"


def asset_entry_identity(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": entry.get("Name"),
        "container": entry.get("Container"),
        "source": entry.get("Source"),
        "path_id": entry.get("PathID"),
        "type": entry.get("Type"),
        "hash": entry.get("Hash"),
        "offset": entry.get("Offset"),
    }


def stable_asset_export_signature(item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    stage_signature = item.get("stage_signature") or {}
    return {
        "stage": plan.get("stage"),
        "type_spec": item.get("type_spec"),
        "export_type": stage_signature.get("export_type"),
        "group_assets": stage_signature.get("group_assets"),
        "game": stage_signature.get("game"),
        "file_naming": stage_signature.get("file_naming"),
        "logger_flags": stage_signature.get("logger_flags"),
        "output_extension": animestudio_convert_output_extension(animestudio_type_name(item.get("type_spec"))),
    }


def asset_entry_cache_key(entry: dict[str, Any], item: dict[str, Any], plan: dict[str, Any]) -> str:
    return stable_hash(
        {
            "asset": asset_entry_identity(entry),
            "export_signature": stable_asset_export_signature(item, plan),
            "cli_signature": plan.get("cli_signature"),
            "dummy_dll_signature": plan.get("dummy_dll_signature"),
            "source_fingerprint": plan.get("source_fingerprint"),
        }
    )


def asset_entry_manifest_key(entry: dict[str, Any], item: dict[str, Any], plan: dict[str, Any]) -> str:
    return stable_hash(
        {
            "asset": asset_entry_identity(entry),
            "stage": plan.get("stage"),
            "type_spec": item.get("type_spec"),
            "file_naming": "path_id_suffix_v1",
        }
    )


def asset_cache_entry_is_valid(
    cache: dict[str, Any],
    manifest_key: str,
    cache_key: str,
    output_path: Path,
) -> bool:
    entry = (cache.get("entries") or {}).get(manifest_key)
    if not isinstance(entry, dict) or entry.get("cache_key") != cache_key:
        return False
    if not output_path.exists():
        return bool(entry.get("missing_output"))
    if entry.get("missing_output"):
        return False
    try:
        stat = output_path.stat()
    except OSError:
        return False
    cached_size = entry.get("output_size")
    if cached_size is not None and int(cached_size) != stat.st_size:
        return False
    cached_mtime_ns = entry.get("output_mtime_ns")
    return cached_mtime_ns is None or int(cached_mtime_ns) == stat.st_mtime_ns


def update_asset_cache_entries(
    cache: dict[str, Any],
    entries: list[dict[str, Any]],
    item: dict[str, Any],
    plan: dict[str, Any],
    output_root: Path,
    source: str,
    stage: str,
) -> int:
    cache_entries = cache.setdefault("entries", {})
    updated = 0
    completed_at_epoch = int(time.time())
    type_name = animestudio_type_name(item.get("type_spec"))
    allow_missing_output = type_name in ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES
    for entry in entries:
        output_path = predict_animestudio_convert_output_path(output_root, source, stage, entry)
        if output_path is None:
            continue
        manifest_key = asset_entry_manifest_key(entry, item, plan)
        if not output_path.exists():
            if not allow_missing_output:
                continue
            cache_entries[manifest_key] = {
                "cache_key": asset_entry_cache_key(entry, item, plan),
                "output_path": str(output_path),
                "missing_output": True,
                "completed_at_epoch": completed_at_epoch,
                "asset": asset_entry_identity(entry),
            }
            updated += 1
            continue
        stat = output_path.stat()
        cache_entries[manifest_key] = {
            "cache_key": asset_entry_cache_key(entry, item, plan),
            "output_path": str(output_path),
            "missing_output": False,
            "output_size": stat.st_size,
            "output_mtime_ns": stat.st_mtime_ns,
            "completed_at_epoch": completed_at_epoch,
            "asset": asset_entry_identity(entry),
        }
        updated += 1
    return updated


def dedupe_asset_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = stable_hash(asset_entry_identity(entry))
        result.setdefault(key, entry)
    return list(result.values())


def normalized_asset_offset(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def asset_entry_source_key(entry: dict[str, Any]) -> str:
    source = str(entry.get("Source") or "").strip()
    if source:
        return source
    return f"<missing-source>:{entry.get('Offset')}:{entry.get('PathID')}:{entry.get('Name')}"


def asset_source_size(source: str, cache: dict[str, int]) -> int:
    if not source or source.startswith("<missing-source>:"):
        return 0
    if source in cache:
        return cache[source]
    try:
        size = Path(source).stat().st_size
    except OSError:
        size = 0
    cache[source] = size
    return size


def asset_entry_source_stats(entries: list[dict[str, Any]]) -> tuple[int, int]:
    size_cache: dict[str, int] = {}
    sources = sorted({asset_entry_source_key(entry) for entry in entries})
    total_bytes = sum(asset_source_size(source, size_cache) for source in sources)
    return len(sources), total_bytes


def write_asset_shard_files(
    output_root: Path,
    source: str,
    stage: str,
    item_name: str,
    shard_index: int,
    shard_count: int,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    shard_dir = ensure_dir(animestudio_work_dir(output_root) / "filters" / "asset_shards" / source / stage / item_name)
    stem = f"shard_{shard_index + 1:02d}_of_{shard_count:02d}"
    filter_data_path = shard_dir / f"{stem}_filter_data.json"
    names_path = shard_dir / f"{stem}_names.txt"
    filter_items = [
        {
            "Source": entry.get("Source"),
            "Offset": normalized_asset_offset(entry.get("Offset")),
            "Name": entry.get("Name"),
            "PathID": entry.get("PathID"),
            "Type": entry.get("Type"),
        }
        for entry in entries
    ]
    write_json(filter_data_path, filter_items)
    names = sorted({str(entry.get("Name") or "") for entry in entries if str(entry.get("Name") or "")})
    names_path.write_text("\n".join(regex_exact(name) for name in names) + ("\n" if names else ""), encoding="utf-8")
    source_file_count, source_byte_count = asset_entry_source_stats(entries)
    return {
        "index": shard_index + 1,
        "count": shard_count,
        "filter_data": str(filter_data_path),
        "names": str(names_path),
        "entry_count": len(entries),
        "source_file_count": source_file_count,
        "source_byte_count": source_byte_count,
        "source_offset_group_count": len({(entry.get("Source"), entry.get("Offset")) for entry in entries}),
        "entries": entries,
    }


def split_asset_entries_into_shards(entries: list[dict[str, Any]], shard_count: int) -> list[list[dict[str, Any]]]:
    if not entries:
        return []
    if shard_count <= 1 or len(entries) <= 1:
        return [entries]
    groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        groups.setdefault(asset_entry_source_key(entry), []).append(entry)
    actual_shard_count = min(shard_count, len(groups))
    size_cache: dict[str, int] = {}
    group_records = [
        {
            "source_key": source_key,
            "entries": group,
            "entry_count": len(group),
            "source_size": asset_source_size(source_key, size_cache),
        }
        for source_key, group in groups.items()
    ]

    total_source_bytes = sum(asset_source_size(source, size_cache) for source in groups)
    target_source_bytes = max(1.0, total_source_bytes / actual_shard_count)
    target_source_files = max(1.0, len(groups) / actual_shard_count)
    target_entries = max(1.0, len(entries) / actual_shard_count)
    shards: list[dict[str, Any]] = [
        {
            "entries": [],
            "source_count": 0,
            "source_bytes": 0,
            "entry_count": 0,
        }
        for _ in range(actual_shard_count)
    ]

    def candidate_score(shard: dict[str, Any], group: dict[str, Any]) -> tuple[float, float, float, float]:
        source_bytes = shard["source_bytes"] + group["source_size"]
        source_files = shard["source_count"] + 1
        entry_count = shard["entry_count"] + group["entry_count"]
        byte_ratio = source_bytes / target_source_bytes
        file_ratio = source_files / target_source_files
        entry_ratio = entry_count / target_entries
        return (max(byte_ratio, file_ratio, entry_ratio), byte_ratio, file_ratio, entry_ratio)

    for group in sorted(
        group_records,
        key=lambda item: (-item["source_size"], -item["entry_count"], str(item["source_key"]).casefold()),
    ):
        shard = min(shards, key=lambda candidate: candidate_score(candidate, group))
        shard["entries"].extend(group["entries"])
        shard["source_count"] += 1
        shard["source_bytes"] += group["source_size"]
        shard["entry_count"] += group["entry_count"]

    return [shard["entries"] for shard in shards if shard["entries"]]


def prune_unmatched_animestudio_asset_outputs(
    output_root: Path,
    source: str,
    stage: str,
    entries: list[dict[str, Any]],
    type_name: str,
) -> int:
    type_dir = animestudio_stage_dir(output_root, source, stage) / type_name
    if not type_dir.is_dir():
        return 0
    expected = {
        str(path.resolve()).casefold()
        for entry in entries
        if (path := predict_animestudio_convert_output_path(output_root, source, stage, entry)) is not None
    }
    removed = 0
    for path in type_dir.iterdir():
        if not path.is_file():
            continue
        if str(path.resolve()).casefold() in expected:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            log(f"  warning: unable to prune stale AnimeStudio output {path}: {exc}")
    return removed


def remove_animestudio_asset_outputs(
    output_root: Path,
    source: str,
    stage: str,
    entries: list[dict[str, Any]],
) -> int:
    removed = 0
    for entry in entries:
        path = predict_animestudio_convert_output_path(output_root, source, stage, entry)
        if path is None or not path.is_file():
            continue
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            log(f"  warning: unable to remove stale AnimeStudio output {path}: {exc}")
    return removed


def count_existing_animestudio_asset_outputs(
    output_root: Path,
    source: str,
    stage: str,
    entries: list[dict[str, Any]],
) -> int:
    return sum(
        1
        for entry in entries
        if (path := predict_animestudio_convert_output_path(output_root, source, stage, entry)) is not None
        and path.is_file()
    )


def animestudio_type_name(type_spec: str | None) -> str:
    if not type_spec:
        return ANIMESTUDIO_MANIFEST_MAP_LABEL
    return str(type_spec).split(":", 1)[0]


def animestudio_log_suffix(item_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", item_name).strip("._") or "item"


def animestudio_manifest_entry_key(source: str, stage: str, type_spec: str | None) -> str:
    return f"{source}|{stage}|{type_spec or ANIMESTUDIO_MANIFEST_MAP_ITEM}"


def animestudio_stage_items(stage: str, types: tuple[str, ...]) -> list[tuple[str | None, str]]:
    if stage == "maps":
        return [(None, ANIMESTUDIO_MANIFEST_MAP_LABEL)]
    return [(type_spec, animestudio_type_name(type_spec)) for type_spec in types]


def animestudio_stage_options_for_scope(scope: str, asset_mode: str = "webui") -> dict[str, dict[str, Any]]:
    if scope == "story":
        json_types = ANIMESTUDIO_STORY_JSON_TYPES
        convert_types: tuple[str, ...] = ()
    elif asset_mode == "webui":
        json_types = ANIMESTUDIO_WEBUI_JSON_TYPES
        convert_types = ANIMESTUDIO_WEBUI_CONVERT_TYPES
    elif asset_mode == "debug":
        json_types = ANIMESTUDIO_DEBUG_JSON_TYPES
        convert_types = ANIMESTUDIO_DEBUG_CONVERT_TYPES
    else:
        json_types = ANIMESTUDIO_FULL_JSON_TYPES
        convert_types = ANIMESTUDIO_FULL_CONVERT_TYPES
    return {
        "maps": {"map_op": "Both", "map_type": "JSON,MessagePack"},
        "convert_by_type": {
            "export_type": "Convert",
            "types": convert_types,
            "asset_map_filter": scope != "story" and bool(convert_types),
            "webui_asset_filter": scope != "story" and asset_mode == "webui",
        },
        "json_by_type": {
            "export_type": "JSON",
            "types": json_types,
            "asset_map_filter": scope != "story" and bool(json_types),
        },
    }


def animestudio_output_file_count(output_root: Path, source: str, stage: str, type_spec: str | None) -> int:
    stage_root = animestudio_stage_dir(output_root, source, stage)
    if stage == "maps":
        return count_files(stage_root)
    return count_files(stage_root / animestudio_type_name(type_spec))


def animestudio_cli_type_tree_priority(value: str) -> str:
    return {
        "serialized-first": "SerializedFirst",
        "script-first": "ScriptFirst",
    }[value]


def animestudio_map_filter_is_safe(types: tuple[str, ...]) -> bool:
    return all(animestudio_type_name(type_spec) not in ANIMESTUDIO_ASSET_MAP_FILTER_UNSAFE_TYPES for type_spec in types)


def build_animestudio_stage_signature(stage: str, options: dict[str, Any], type_spec: str | None) -> dict[str, Any]:
    signature = {
        "stage": stage,
        "type_spec": type_spec,
        "export_type": options.get("export_type"),
        "map_op": options.get("map_op"),
        "map_type": options.get("map_type"),
        "map_name": options.get("map_name"),
        "names": options.get("names"),
        "containers": options.get("containers"),
        "filter_data": options.get("filter_data"),
        "asset_map_filter": bool(options.get("asset_map_filter")),
        "webui_asset_filter": bool(options.get("webui_asset_filter")),
        "webui_asset_filter_signature": options.get("webui_asset_filter_signature"),
        "group_assets": "ByType",
        "game": ANIMESTUDIO_GAME,
        "file_naming": "path_id_suffix_v1",
        "logger_flags": list(ANIMESTUDIO_LOGGER_FLAGS),
    }
    if type_spec is not None and animestudio_type_name(type_spec) == "MonoBehaviour":
        signature["mono_behaviour_type_tree_priority"] = options.get("mono_behaviour_type_tree_priority")
    return signature


def clear_animestudio_stage_outputs(
    output_root: Path,
    source: str,
    stage: str,
    items: list[dict[str, Any]],
) -> None:
    if stage == "maps":
        return
    stage_root = animestudio_stage_dir(output_root, source, stage)
    for item in items:
        type_spec = item.get("type_spec")
        if type_spec is None:
            continue
        target = stage_root / animestudio_type_name(type_spec)
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def build_animestudio_cache_key(
    source: str,
    stage_signature: dict[str, Any],
    cli_signature: dict[str, Any] | None,
    dummy_dll_signature: dict[str, Any] | None,
    source_fingerprint: dict[str, Any],
) -> str:
    return stable_hash(
        {
            "source": source,
            "stage_signature": stage_signature,
            "cli_signature": cli_signature,
            "dummy_dll_signature": dummy_dll_signature,
            "source_fingerprint": source_fingerprint,
        }
    )


def animestudio_matches_refresh_selector(selector: str, source: str, stage: str, item_name: str) -> bool:
    parts = [part.strip().lower() for part in str(selector or "").split(":") if part.strip()]
    if not parts:
        return False

    current_source = source.lower()
    current_stage = stage.lower()
    current_item = item_name.lower()

    if len(parts) == 1:
        return parts[0] in {current_stage, current_item}
    if len(parts) == 2:
        left, right = parts
        if left in SOURCE_NAME_SET:
            return left == current_source and right in {current_stage, current_item}
        return left == current_stage and right == current_item
    if len(parts) == 3:
        left, middle, right = parts
        return left == current_source and middle == current_stage and right == current_item
    return False


def animestudio_plan_cache_state(plan: dict[str, Any]) -> str:
    selected_items = plan.get("selected_items") or []
    cached_items = plan.get("cached_items") or []
    run_items = plan.get("run_items") or []
    forced_refresh_items = plan.get("forced_refresh_items") or []
    if not selected_items:
        return "empty"
    if not run_items:
        return "cached"
    if forced_refresh_items and len(run_items) == len(selected_items):
        return "forced_refresh"
    if cached_items:
        return "partial"
    return "miss"


def plan_animestudio_stage(
    source: str,
    output_root: Path,
    stage: str,
    options: dict[str, Any],
    manifest_entries: dict[str, Any],
    cli_signature: dict[str, Any] | None,
    dummy_dll_signature: dict[str, Any] | None,
    source_fingerprint: dict[str, Any],
    refresh_selectors: tuple[str, ...],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    selected_items: list[str] = []
    cached_items: list[str] = []
    run_items: list[str] = []
    forced_refresh_items: list[str] = []
    item_file_counts: dict[str, int] = {}
    type_specs_to_run: list[str] = []

    for type_spec, item_name in animestudio_stage_items(stage, options.get("types", ())):
        selected_items.append(item_name)
        item_file_count = animestudio_output_file_count(output_root, source, stage, type_spec)
        item_file_counts[item_name] = item_file_count
        manifest_key = animestudio_manifest_entry_key(source, stage, type_spec)
        stage_signature = build_animestudio_stage_signature(stage, options, type_spec)
        cache_key = build_animestudio_cache_key(
            source=source,
            stage_signature=stage_signature,
            cli_signature=cli_signature,
            dummy_dll_signature=dummy_dll_signature,
            source_fingerprint=source_fingerprint,
        )
        refresh_forced = any(
            animestudio_matches_refresh_selector(selector, source, stage, item_name)
            for selector in refresh_selectors
        )
        manifest_entry = manifest_entries.get(manifest_key) or {}
        cache_valid = (
            not refresh_forced
            and manifest_entry.get("cache_key") == cache_key
            and int(manifest_entry.get("file_count", -1)) == item_file_count
        )

        item_info = {
            "type_spec": type_spec,
            "item_name": item_name,
            "manifest_key": manifest_key,
            "stage_signature": stage_signature,
            "cache_key": cache_key,
            "file_count": item_file_count,
            "cache_valid": cache_valid,
            "refresh_forced": refresh_forced,
        }
        items.append(item_info)

        if refresh_forced:
            forced_refresh_items.append(item_name)
        if cache_valid:
            cached_items.append(item_name)
        else:
            run_items.append(item_name)
            if type_spec is not None:
                type_specs_to_run.append(type_spec)

    plan = {
        "stage": stage,
        "options": options,
        "items": items,
        "selected_items": selected_items,
        "cached_items": cached_items,
        "run_items": run_items,
        "forced_refresh_items": forced_refresh_items,
        "item_file_counts": item_file_counts,
        "type_specs_to_run": tuple(type_specs_to_run),
        "should_run": bool(run_items),
        "cli_signature": cli_signature,
        "dummy_dll_signature": dummy_dll_signature,
        "source_fingerprint": source_fingerprint,
    }
    plan["cache_state"] = animestudio_plan_cache_state(plan)
    return plan


def update_animestudio_manifest_for_stage(
    manifest: dict[str, Any],
    output_root: Path,
    source: str,
    stage: str,
    plan: dict[str, Any],
    cli_signature: dict[str, Any] | None,
    dummy_dll_signature: dict[str, Any] | None,
    source_fingerprint: dict[str, Any],
) -> None:
    entries = manifest.setdefault("entries", {})
    completed_at_epoch = int(time.time())
    for item in plan.get("items", []):
        if item["item_name"] not in plan.get("run_items", []):
            continue
        current_file_count = animestudio_output_file_count(output_root, source, stage, item["type_spec"])
        item["file_count"] = current_file_count
        plan.setdefault("item_file_counts", {})[item["item_name"]] = current_file_count
        entries[item["manifest_key"]] = {
            "source": source,
            "stage": stage,
            "type_spec": item["type_spec"],
            "item_name": item["item_name"],
            "cache_key": item["cache_key"],
            "file_count": current_file_count,
            "completed_at_epoch": completed_at_epoch,
            "cli_signature": cli_signature,
            "dummy_dll_signature": dummy_dll_signature,
            "source_fingerprint": source_fingerprint,
            "stage_signature": item["stage_signature"],
        }


def copy_animestudio_plan_for_run_items(plan: dict[str, Any], run_items: list[str]) -> dict[str, Any]:
    copied = dict(plan)
    copied["run_items"] = list(run_items)
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export all currently reachable Endfield VFS content into export_full, "
            "including structured dumps, AnimeStudio recovery outputs, and failure reports."
        )
    )
    parser.add_argument(
        "--game-root",
        type=Path,
        default=DEFAULT_GAME_ROOT,
        help="Path to the game's Endfield_Data directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output root for the full export",
    )
    parser.add_argument(
        "--fluffy",
        "--structured-dumper",
        dest="fluffy",
        type=Path,
        default=DEFAULT_STRUCTURED_DUMPER,
        help="Path to AnimeStudio CLI, or a legacy fluffy-dumper executable, for VFS structured exports",
    )
    parser.add_argument(
        "--animestudio",
        type=Path,
        default=DEFAULT_ANIMESTUDIO,
        help="Path to AnimeStudio CLI executable",
    )
    parser.add_argument(
        "--animestudio-dummy-dlls",
        type=Path,
        default=None,
        help=(
            "Optional DummyDll directory passed to AnimeStudio for MonoBehaviour schema recovery. "
            f"Overrides {ANIMESTUDIO_DUMMY_DLL_ENV}."
        ),
    )
    parser.add_argument(
        "--animestudio-mono-behaviour-type-tree-priority",
        choices=("serialized-first", "script-first"),
        default="serialized-first",
        help=(
            "MonoBehaviour TypeTree priority for AnimeStudio JSON export. "
            "`script-first` requires usable DummyDlls and is intended for targeted recovery tests."
        ),
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=SOURCES,
        default=SOURCES,
        help="Limit export work to one or more source roots (default: all)",
    )
    parser.add_argument(
        "--animestudio-stages",
        nargs="+",
        choices=ANIMESTUDIO_STAGES,
        default=ANIMESTUDIO_STAGES,
        help="Limit AnimeStudio export to one or more stages (default: all)",
    )
    parser.add_argument(
        "--animestudio-scope",
        choices=ANIMESTUDIO_SCOPES,
        default="all",
        help=(
            "`story` exports only maps plus TextAsset/MonoBehaviour/PlayableDirector JSON. "
            "`assets`/`all` use --animestudio-asset-mode to choose WebUI-focused, full, or debug assets."
        ),
    )
    parser.add_argument(
        "--animestudio-asset-mode",
        choices=ANIMESTUDIO_ASSET_MODES,
        default="webui",
        help=(
            "`webui` exports only WebUI-referenced Texture2D media by loading the AnimeStudio asset map "
            "with generated name filters. `full` exports WebUI-facing image/model assets plus Material JSON. `debug` exports the exhaustive conversion and JSON diagnostic sets."
        ),
    )
    parser.add_argument(
        "--animestudio-refresh-types",
        nargs="+",
        default=(),
        help=(
            "Force-refresh cached AnimeStudio items. Accepts selectors such as "
            "`MonoBehaviour`, `Material`, `maps`, `json_by_type:Material`, or "
            "`StreamingAssets:json_by_type:Material`."
        ),
    )
    parser.add_argument(
        "--animestudio-jobs",
        type=int,
        default=ANIMESTUDIO_DEFAULT_JOBS,
        help=(
            "Maximum parallel AnimeStudio CLI processes for per-type export. "
            f"The default {ANIMESTUDIO_DEFAULT_JOBS} runs shards/types in parallel; lower it to limit peak memory."
        ),
    )
    parser.add_argument(
        "--animestudio-shards",
        type=int,
        default=ANIMESTUDIO_DEFAULT_SHARDS,
        help=(
            "Split each map-filtered deterministic asset type into this many filter_data shards. "
            f"The default {ANIMESTUDIO_DEFAULT_SHARDS} keeps per-process asset slices small while "
            f"--animestudio-jobs defaults to {ANIMESTUDIO_DEFAULT_JOBS}. "
            "Use 0 to shard by --animestudio-jobs."
        ),
    )
    parser.add_argument(
        "--no-animestudio-asset-cache",
        action="store_true",
        help="Disable per-asset AnimeStudio conversion cache for map-filtered deterministic conversions",
    )
    parser.add_argument(
        "--skip-structured",
        action="store_true",
        help="Skip VFS structured exports",
    )
    parser.add_argument(
        "--skip-vfs-index",
        action="store_true",
        help="Skip the lightweight VFS metadata index used by asset exports",
    )
    parser.add_argument(
        "--skip-animestudio",
        action="store_true",
        help="Skip broad AnimeStudio CLI export passes",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Do not rerun exports; regenerate summary files from existing logs and outputs",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def log(message: str) -> None:
    print(f"[export_full] {message}", flush=True)


def current_report_run_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def load_previous_summary(primary_path: Path, legacy_path: Path) -> dict[str, Any]:
    for candidate in (primary_path, legacy_path):
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8-sig"))
    return {}


def structured_output_dir(output_root: Path, source: str) -> Path:
    return output_root / "structured" / source


def resolve_existing_structured_output_dir(output_root: Path, source: str) -> Path:
    preferred = structured_output_dir(output_root, source)
    legacy = output_root / source
    if preferred.exists() or not legacy.exists():
        return preferred
    return legacy


def vfs_index_dir(output_root: Path, source: str) -> Path:
    return output_root / "recovered" / "AnimeStudio-cli" / source / "vfs_index"


def vfs_index_path(output_root: Path, source: str, block_name: str = "bundle") -> Path:
    return vfs_index_dir(output_root, source) / f"{block_name.lower()}_vfs_index.json"


def summarize_vfs_index(path: Path, result: CommandResult | None = None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "index_path": str(path),
        "exists": path.exists(),
        "returncode": result.returncode if result is not None else None,
        "stdout_log": result.stdout_log if result is not None else None,
        "stderr_log": result.stderr_log if result is not None else None,
    }
    if not path.exists():
        return summary

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        summary["error"] = str(exc)
        return summary

    index_summary = data.get("summary") if isinstance(data, dict) else {}
    if isinstance(index_summary, dict):
        summary.update(
            {
                "block_count": index_summary.get("blockCount"),
                "missing_block_count": index_summary.get("missingBlockCount"),
                "chunk_count": index_summary.get("chunkCount"),
                "missing_chunk_count": index_summary.get("missingChunkCount"),
                "file_count": index_summary.get("fileCount"),
                "byte_count": index_summary.get("byteCount"),
            }
        )
    return summary


def animestudio_source_root(output_root: Path, source: str) -> Path:
    return output_root / "recovered" / "AnimeStudio-cli" / source


def animestudio_stage_dir(output_root: Path, source: str, stage: str) -> Path:
    return animestudio_source_root(output_root, source) / stage


def animestudio_work_dir(output_root: Path) -> Path:
    return output_root / "recovered" / "AnimeStudio-cli"


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def looks_like_dummy_dll_dir(path: Path) -> bool:
    return path.exists() and path.is_dir() and any(path.glob("*.dll"))


def normalize_dummy_dll_path(path: Path | str) -> Path:
    text = str(path).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1]
    return Path(text).expanduser()


def validate_dummy_dll_dir(path: Path | str, source: str) -> Path:
    candidate = normalize_dummy_dll_path(path)
    if not looks_like_dummy_dll_dir(candidate):
        raise SystemExit(
            f"AnimeStudio DummyDll directory from {source} was not found or contains no .dll files: {candidate}"
        )
    return candidate.resolve()


def resolve_animestudio_dummy_dlls(explicit: Path | None, game_root: Path) -> tuple[Path | None, str | None]:
    if explicit is not None:
        return validate_dummy_dll_dir(explicit, "--animestudio-dummy-dlls"), "--animestudio-dummy-dlls"

    env_value = os.environ.get(ANIMESTUDIO_DUMMY_DLL_ENV, "").strip()
    if env_value:
        return validate_dummy_dll_dir(env_value, ANIMESTUDIO_DUMMY_DLL_ENV), ANIMESTUDIO_DUMMY_DLL_ENV

    candidates = (
        (game_root / "DummyDll", "game root DummyDll"),
        (game_root.parent / "DummyDll", "game install DummyDll"),
        (ROOT / "tools" / "DummyDll", "tools/DummyDll"),
        (ROOT / "tools" / "dummy_dlls", "tools/dummy_dlls"),
    )

    seen: set[str] = set()
    for candidate, source in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if looks_like_dummy_dll_dir(candidate):
            return candidate.resolve(), source
    return None, None


def run_logged_command(
    name: str,
    argv: list[str],
    cwd: Path,
    reports_dir: Path,
    stream_output: bool = False,
) -> CommandResult:
    ensure_dir(reports_dir)
    stdout_log = reports_dir / f"{name}.stdout.log"
    stderr_log = reports_dir / f"{name}.stderr.log"
    log(f"starting {name}")
    log(f"  cwd: {cwd}")
    log(f"  stdout log: {stdout_log}")
    log(f"  stderr log: {stderr_log}")
    log(f"  command: {' '.join(argv)}")
    started = time.time()
    if stream_output:
        with stdout_log.open("w", encoding="utf-8", errors="replace") as stdout_handle, stderr_log.open(
            "w", encoding="utf-8", errors="replace"
        ) as stderr_handle:
            proc = subprocess.run(
                argv,
                cwd=str(cwd),
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
    else:
        proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
        stdout_log.write_text(proc.stdout, encoding="utf-8")
        stderr_log.write_text(proc.stderr, encoding="utf-8")
    duration = time.time() - started
    log(
        f"finished {name} with returncode={proc.returncode} "
        f"in {duration:.3f}s"
    )
    return CommandResult(
        name=name,
        argv=argv,
        cwd=str(cwd),
        returncode=proc.returncode,
        duration_seconds=round(duration, 3),
        stdout_log=str(stdout_log),
        stderr_log=str(stderr_log),
    )


def animestudio_cli_usage_error(result: CommandResult) -> bool:
    try:
        stdout_text = Path(result.stdout_log).read_text(encoding="utf-8", errors="replace")
        stderr_text = Path(result.stderr_log).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return (
        "Invalid Regex." in stderr_text
        or "Required command was not provided." in stderr_text
        or (
            "Usage:" in stdout_text
            and "AnimeStudio.CLI <input_path> <output_path>" in stdout_text
            and "[UnityCN]" not in stdout_text
        )
    )


def mark_command_result_failed(result: CommandResult) -> CommandResult:
    return CommandResult(
        name=result.name,
        argv=result.argv,
        cwd=result.cwd,
        returncode=1,
        duration_seconds=result.duration_seconds,
        stdout_log=result.stdout_log,
        stderr_log=result.stderr_log,
    )


def parse_structured_failures(stderr_text: str) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for line in stderr_text.splitlines():
        match = FAILED_EXTRACT_RE.search(line)
        if not match:
            continue
        failures.append(
            {
                "file": match.group("file").strip(),
                "reason": match.group("reason").strip(),
            }
        )
    return failures


def parse_warning_failure_count(stdout_text: str) -> int:
    count = 0
    for line in stdout_text.splitlines():
        match = WARNING_FAIL_RE.search(line)
        if match:
            count += int(match.group("count"))
    return count


def summarize_animestudio_log_issues(stdout_log: str | Path | None, stderr_log: str | Path | None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "error_count": 0,
        "warning_count": 0,
        "exception_count": 0,
        "end_of_stream_count": 0,
        "export_error_count": 0,
        "story_like_export_error_count": 0,
        "metadata_only_json_count": 0,
        "samples": [],
        "export_error_samples": [],
        "story_like_export_error_samples": [],
        "metadata_only_json_samples": [],
        "missing_logs": [],
    }

    def add_sample(key: str, item: dict[str, Any]) -> None:
        samples = summary.setdefault(key, [])
        if len(samples) < ANIMESTUDIO_LOG_SAMPLE_LIMIT:
            samples.append(item)

    for stream_name, raw_path in (("stdout", stdout_log), ("stderr", stderr_log)):
        if not raw_path:
            continue
        path = Path(raw_path)
        if not path.exists():
            summary["missing_logs"].append(str(path))
            continue

        pending_export_sample: dict[str, Any] | None = None
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line_number, line in enumerate(handle, 1):
                    text = line.rstrip("\r\n")
                    if pending_export_sample is not None and not pending_export_sample.get("reason"):
                        stripped = text.strip()
                        if stripped and not stripped.startswith("at "):
                            pending_export_sample["reason"] = stripped

                    level_match = ANIMESTUDIO_LOG_LINE_RE.match(text)
                    if level_match:
                        level = level_match.group("level").lower()
                        summary[f"{level}_count"] += 1
                        add_sample(
                            "samples",
                            {
                                "stream": stream_name,
                                "line": line_number,
                                "level": level,
                                "message": level_match.group("message").strip(),
                            },
                        )

                    if "Exception" in text:
                        summary["exception_count"] += 1
                    if "Unable to read beyond the end of the stream" in text:
                        summary["end_of_stream_count"] += 1

                    metadata_only_match = ANIMESTUDIO_METADATA_ONLY_JSON_RE.match(text)
                    if metadata_only_match:
                        asset = metadata_only_match.group("asset").strip()
                        summary["metadata_only_json_count"] += 1
                        add_sample(
                            "metadata_only_json_samples",
                            {
                                "stream": stream_name,
                                "line": line_number,
                                "asset": asset,
                                "exception": metadata_only_match.group("exception").strip(),
                                "reason": metadata_only_match.group("reason").strip(),
                            },
                        )

                    export_match = ANIMESTUDIO_EXPORT_ERROR_RE.match(text)
                    if not export_match:
                        continue
                    asset = export_match.group("asset").strip()
                    summary["export_error_count"] += 1
                    export_sample = {
                        "stream": stream_name,
                        "line": line_number,
                        "asset": asset,
                        "reason": "",
                    }
                    add_sample("export_error_samples", export_sample)
                    pending_export_sample = export_sample
                    if ANIMESTUDIO_STORY_HINT_RE.search(asset):
                        summary["story_like_export_error_count"] += 1
                        add_sample("story_like_export_error_samples", export_sample)
        except OSError as exc:
            add_sample(
                "samples",
                {
                    "stream": stream_name,
                    "line": None,
                    "level": "error",
                    "message": f"unable to read log {path}: {exc}",
                },
            )

    if not summary["missing_logs"]:
        summary.pop("missing_logs", None)
    if not summary["samples"]:
        summary.pop("samples", None)
    if not summary["export_error_samples"]:
        summary.pop("export_error_samples", None)
    if not summary["story_like_export_error_samples"]:
        summary.pop("story_like_export_error_samples", None)
    if not summary["metadata_only_json_samples"]:
        summary.pop("metadata_only_json_samples", None)
    return summary


def merge_animestudio_log_issues(results: list[CommandResult]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "error_count": 0,
        "warning_count": 0,
        "exception_count": 0,
        "end_of_stream_count": 0,
        "export_error_count": 0,
        "story_like_export_error_count": 0,
        "metadata_only_json_count": 0,
        "samples": [],
        "export_error_samples": [],
        "story_like_export_error_samples": [],
        "metadata_only_json_samples": [],
        "missing_logs": [],
    }
    sample_keys = (
        "samples",
        "export_error_samples",
        "story_like_export_error_samples",
        "metadata_only_json_samples",
    )
    count_keys = (
        "error_count",
        "warning_count",
        "exception_count",
        "end_of_stream_count",
        "export_error_count",
        "story_like_export_error_count",
        "metadata_only_json_count",
    )
    for result in results:
        issues = summarize_animestudio_log_issues(result.stdout_log, result.stderr_log)
        for key in count_keys:
            merged[key] += int(issues.get(key) or 0)
        for key in sample_keys:
            target = merged.setdefault(key, [])
            for sample in issues.get(key) or []:
                if len(target) >= ANIMESTUDIO_LOG_SAMPLE_LIMIT:
                    break
                enriched = dict(sample)
                enriched.setdefault("command", result.name)
                target.append(enriched)
        merged["missing_logs"].extend(issues.get("missing_logs") or [])

    for key in sample_keys + ("missing_logs",):
        if not merged.get(key):
            merged.pop(key, None)
    return merged


def is_manifest_reference_missing(source: str, reason: str) -> bool:
    if source != "Persistent":
        return False
    return (
        "chunk file not found:" in reason
        or reason == "chunk missing"
        or reason == "chk file missing on disk (listed in .blc but not present)"
    )


def split_structured_failures(
    source: str,
    failures: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    actual: list[dict[str, str]] = []
    manifest_only: list[dict[str, str]] = []
    for item in failures:
        if is_manifest_reference_missing(source, item["reason"]):
            manifest_only.append(item)
        else:
            actual.append(item)
    return actual, manifest_only


def summarize_raw_failures(log_path: Path, source: str) -> dict[str, Any]:
    if not log_path.exists():
        return {
            "summary": None,
            "actual_failures": [],
            "manifest_missing_chunks": [],
            "missing": True,
        }

    data = json.loads(log_path.read_text(encoding="utf-8"))
    actual_failures: list[dict[str, Any]] = []
    manifest_missing_chunks: list[dict[str, Any]] = []
    for block in data.get("blocks", []):
        block_name = block.get("dir")
        if block.get("blc_error"):
            actual_failures.append(
                {
                    "block": block_name,
                    "chunk": None,
                    "file": None,
                    "reason": block["blc_error"],
                }
            )
        for chunk in block.get("chunks", []):
            if not chunk.get("present", True):
                manifest_missing_chunks.append(
                    {
                        "block": block_name,
                        "chunk": chunk.get("chk"),
                        "referenced_file_count": chunk.get("file_count"),
                        "reason": "chk file missing on disk (listed in .blc but not present)",
                    }
                )
                continue
            for err in chunk.get("errors", []):
                reason = err.get("reason") or ""
                record = {
                    "block": block_name,
                    "chunk": chunk.get("chk"),
                    "file": err.get("file"),
                    "reason": reason,
                }
                if is_manifest_reference_missing(source, reason):
                    # Keep the chunk-level summary only; file-level entries are redundant.
                    continue
                actual_failures.append(record)
    return {
        "summary": data.get("summary"),
        "actual_failures": actual_failures,
        "manifest_missing_chunks": manifest_missing_chunks,
        "missing": False,
    }


def collect_source_sizes(game_root: Path, sources: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source in sources:
        base = game_root / source
        total = 0
        files = 0
        latest_mtime_ns = 0
        for path in base.rglob("*"):
            if path.is_file():
                files += 1
                stat = path.stat()
                total += stat.st_size
                latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
        fingerprint_payload = {
            "root": str(base),
            "files": files,
            "bytes": total,
            "latest_mtime_ns": latest_mtime_ns,
        }
        result[source] = {
            "root": str(base),
            "files": files,
            "bytes": total,
            "gigabytes": round(total / (1024 ** 3), 3),
            "latest_mtime_ns": latest_mtime_ns,
            "fingerprint": stable_hash(fingerprint_payload),
        }
    return result


def run_animestudio_stage(
    source: str,
    input_root: Path,
    output_root: Path,
    reports_dir: Path,
    animestudio_exe: Path,
    animestudio_dummy_dlls: Path | None,
    mono_behaviour_type_tree_priority: str | None,
    stage: str,
    export_type: str | None = None,
    map_op: str | None = None,
    map_type: str | None = None,
    map_name: str | None = None,
    names: str | Path | None = None,
    containers: str | Path | None = None,
    filter_data: str | Path | None = None,
    types: tuple[str, ...] = (),
    command_name: str | None = None,
) -> CommandResult:
    work_dir = ensure_dir(animestudio_work_dir(output_root))
    stage_out = ensure_dir(animestudio_stage_dir(output_root, source, stage))
    is_asset_map_load = map_op is not None and "AssetMap" in str(map_op) and "Load" in str(map_op)
    use_map_op = map_op is not None and (not is_asset_map_load or animestudio_map_filter_is_safe(types))
    use_map_filter = use_map_op and is_asset_map_load
    cmd = [
        str(animestudio_exe),
        str(input_root),
        str(stage_out),
        "--game",
        ANIMESTUDIO_GAME,
        "--logger_flags",
        *ANIMESTUDIO_LOGGER_FLAGS,
        "--group_assets",
        "ByType",
    ]
    if export_type is not None:
        cmd.extend(["--export_type", export_type])
    if animestudio_dummy_dlls is not None:
        cmd.extend(["--dummy_dlls", str(animestudio_dummy_dlls)])
    if mono_behaviour_type_tree_priority and any(animestudio_type_name(type_spec) == "MonoBehaviour" for type_spec in types):
        cmd.extend(["--mono_behaviour_type_tree_priority", mono_behaviour_type_tree_priority])
    if use_map_op:
        cmd.extend(["--map_op", map_op])
    if use_map_op and map_type is not None:
        cmd.extend(["--map_type", map_type])
    if use_map_op and map_name is not None:
        cmd.extend(["--map_name", map_name])
    if names is not None:
        cmd.extend(["--names", str(names)])
    if containers is not None:
        cmd.extend(["--containers", str(containers)])
    if filter_data is not None:
        cmd.extend(["--filter_data", str(filter_data)])
    if types:
        cmd.append("--types")
        cmd.extend(types)
    name = command_name or f"{source}_animestudio_{stage}"
    result = run_logged_command(name, cmd, work_dir, reports_dir, stream_output=True)
    if result.returncode == 0 and animestudio_cli_usage_error(result):
        log(f"  animestudio command {name} printed CLI usage/validation output; treating as failed")
        return mark_command_result_failed(result)
    return result


def write_animestudio_parallel_log_index(
    source: str,
    stage: str,
    reports_dir: Path,
    results: list[CommandResult],
) -> tuple[str, str]:
    ensure_dir(reports_dir)
    stdout_log = reports_dir / f"{source}_animestudio_{stage}.stdout.log"
    stderr_log = reports_dir / f"{source}_animestudio_{stage}.stderr.log"

    lines = [
        f"Type-sliced AnimeStudio stage: {source} {stage}",
        f"processes: {len(results)}",
        "",
        "returncode\tstdout_log\tstderr_log\tcommand",
    ]
    for result in results:
        lines.append(
            f"{result.returncode}\t{result.stdout_log}\t{result.stderr_log}\t"
            f"{' '.join(result.argv)}"
        )
    stdout_log.write_text("\n".join(lines), encoding="utf-8")

    failed = [result for result in results if result.returncode != 0]
    err_lines = [
        f"Type-sliced AnimeStudio stage failures: {source} {stage}",
        f"failed_processes: {len(failed)}",
    ]
    for result in failed:
        err_lines.append(f"{result.name}\treturncode={result.returncode}\tstderr={result.stderr_log}")
    stderr_log.write_text("\n".join(err_lines), encoding="utf-8")
    return str(stdout_log), str(stderr_log)


def write_animestudio_asset_cache_log(
    source: str,
    stage: str,
    reports_dir: Path,
    asset_info: dict[str, Any],
) -> tuple[str, str]:
    ensure_dir(reports_dir)
    stdout_log = reports_dir / f"{source}_animestudio_{stage}.stdout.log"
    stderr_log = reports_dir / f"{source}_animestudio_{stage}.stderr.log"
    asset_infos = asset_info.get("asset_caches")
    if not isinstance(asset_infos, list):
        asset_infos = [asset_info]
    lines = [f"AnimeStudio asset cache satisfied stage: {source} {stage}"]
    for info in asset_infos:
        lines.extend(
            [
                "",
                f"type: {info.get('type')}",
                f"output_extension: {info.get('output_extension')}",
                f"matched_entries: {info.get('matched_entry_count')}",
                f"cached_entries: {info.get('cached_entry_count')}",
                f"pending_entries: {info.get('pending_entry_count')}",
                f"pruned_outputs: {info.get('pruned_output_count', 0)}",
                f"cache_path: {info.get('cache_path')}",
            ]
        )
    stdout_log.write_text("\n".join(lines), encoding="utf-8")
    stderr_log.write_text("", encoding="utf-8")
    return str(stdout_log), str(stderr_log)


def prepare_animestudio_asset_shards(
    source: str,
    output_root: Path,
    stage: str,
    plan: dict[str, Any],
    runnable_items: list[dict[str, Any]],
    jobs: int,
) -> dict[str, Any] | None:
    if stage != "convert_by_type" or len(runnable_items) != 1:
        return None

    item = runnable_items[0]
    type_spec = item.get("type_spec")
    type_name = animestudio_type_name(type_spec)
    options = plan["options"]
    if (
        not animestudio_asset_cache_supported(stage, options, type_name)
        or not options.get("asset_map_filter")
        or not animestudio_map_filter_is_safe((type_spec,))
    ):
        return None

    map_name = options.get("map_name")
    if not map_name:
        return None
    map_json = normalize_asset_map_path(map_name)
    if not map_json.exists():
        log(f"  animestudio asset shards {stage}:{type_name} for {source}: missing JSON map {map_json}; using normal path")
        return None

    started = time.time()
    map_entries_cache = plan.setdefault("_asset_map_entries_cache", {})
    map_entries_key = str(map_json)
    map_entries = map_entries_cache.get(map_entries_key)
    if map_entries is None:
        map_entries = load_animestudio_asset_map_entries(map_json)
        map_entries_cache[map_entries_key] = map_entries
    matched_entries = dedupe_asset_entries(
        filter_animestudio_asset_map_entries(
            map_path=map_json,
            type_name=type_name,
            names=options.get("names"),
            containers=options.get("containers"),
            entries=map_entries,
        )
    )
    cache_enabled = bool(options.get("asset_cache_enabled", True))
    cache_path = animestudio_asset_cache_path(output_root)
    asset_cache = load_animestudio_asset_cache(cache_path) if cache_enabled else default_animestudio_asset_cache()
    cached_entries: list[dict[str, Any]] = []
    pending_entries: list[dict[str, Any]] = []
    for entry in matched_entries:
        output_path = predict_animestudio_convert_output_path(output_root, source, stage, entry)
        if output_path is None:
            pending_entries.append(entry)
            continue
        manifest_key = asset_entry_manifest_key(entry, item, plan)
        cache_key = asset_entry_cache_key(entry, item, plan)
        if cache_enabled and asset_cache_entry_is_valid(asset_cache, manifest_key, cache_key, output_path):
            cached_entries.append(entry)
        else:
            pending_entries.append(entry)

    requested_shards = int(options.get("asset_shards") or 0)
    if requested_shards <= 0:
        requested_shards = max(1, jobs)
    shard_entry_lists = split_asset_entries_into_shards(pending_entries, requested_shards)
    shards = [
        write_asset_shard_files(
            output_root=output_root,
            source=source,
            stage=stage,
            item_name=item["item_name"],
            shard_index=index,
            shard_count=len(shard_entry_lists),
            entries=entries,
        )
        for index, entries in enumerate(shard_entry_lists)
    ]
    elapsed = round(time.time() - started, 3)
    asset_info = {
        "enabled": cache_enabled,
        "cache_path": str(cache_path),
        "map_json": str(map_json),
        "type": type_name,
        "output_extension": animestudio_convert_output_extension(type_name),
        "matched_entry_count": len(matched_entries),
        "cached_entry_count": len(cached_entries),
        "pending_entry_count": len(pending_entries),
        "shard_count": len(shards),
        "prepare_seconds": elapsed,
    }
    plan["asset_cache"] = asset_info
    plan.setdefault("asset_caches", []).append(asset_info)
    log(
        f"  animestudio asset cache {stage}:{type_name} for {source}: "
        f"matched={len(matched_entries)} cached={len(cached_entries)} "
        f"pending={len(pending_entries)} shards={len(shards)} prepared_in={elapsed:.3f}s"
    )
    return {
        "item": item,
        "type_spec": type_spec,
        "type_name": type_name,
        "cache_enabled": cache_enabled,
        "cache_path": cache_path,
        "asset_cache": asset_cache,
        "asset_info": asset_info,
        "matched_entries": matched_entries,
        "cached_entries": cached_entries,
        "pending_entries": pending_entries,
        "shards": shards,
    }


def run_animestudio_asset_shard_work(
    source: str,
    input_root: Path,
    output_root: Path,
    reports_dir: Path,
    animestudio_exe: Path,
    animestudio_dummy_dlls: Path | None,
    stage: str,
    plan: dict[str, Any],
    jobs: int,
    asset_work: dict[str, Any],
) -> tuple[list[CommandResult], list[str], list[str]]:
    options = plan["options"]
    item = asset_work["item"]
    type_spec = asset_work["type_spec"]
    type_name = asset_work["type_name"]
    asset_info = asset_work["asset_info"]
    shards = asset_work["shards"]

    if asset_work["cache_enabled"]:
        pruned_count = prune_unmatched_animestudio_asset_outputs(
            output_root=output_root,
            source=source,
            stage=stage,
            entries=asset_work["matched_entries"],
            type_name=type_name,
        )
    else:
        clear_animestudio_stage_outputs(output_root, source, stage, [item])
        pruned_count = 0
    removed_pending_output_count = remove_animestudio_asset_outputs(
        output_root=output_root,
        source=source,
        stage=stage,
        entries=asset_work["pending_entries"],
    )
    asset_info["pruned_output_count"] = pruned_count
    asset_info["removed_pending_output_count"] = removed_pending_output_count
    if pruned_count:
        log(f"  animestudio asset cache {stage}:{type_name} for {source}: pruned {pruned_count} stale outputs")
    if removed_pending_output_count:
        log(
            f"  animestudio asset cache {stage}:{type_name} for {source}: "
            f"removed {removed_pending_output_count} stale pending outputs before shard export"
        )

    if not shards:
        output_entry_count = count_existing_animestudio_asset_outputs(
            output_root=output_root,
            source=source,
            stage=stage,
            entries=asset_work["matched_entries"],
        )
        missing_output_count = max(0, len(asset_work["matched_entries"]) - output_entry_count)
        asset_info["updated_entry_count"] = 0
        asset_info["successful_shard_count"] = 0
        asset_info["failed_shard_count"] = 0
        asset_info["output_entry_count"] = output_entry_count
        asset_info["missing_output_count"] = missing_output_count
        asset_info["export_error_count"] = 0
        missing_outputs_allowed = type_name in ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES
        asset_info["allowed_missing_output_count"] = missing_output_count if missing_outputs_allowed else 0
        if missing_output_count and not missing_outputs_allowed:
            log(
                f"  animestudio asset cache {stage}:{type_name} for {source}: "
                f"marking failed because missing_outputs={missing_output_count}"
            )
            return [], [], [item["item_name"]]
        return [], [item["item_name"]], []

    max_workers = min(max(1, jobs), len(shards))
    log(
        f"  animestudio asset shards {stage}:{type_name} for {source}: "
        f"launching {len(shards)} shard jobs with max_workers={max_workers}"
    )
    result_by_shard: dict[int, CommandResult] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_shard = {}
        for shard in shards:
            shard_index = int(shard["index"])
            command_name = (
                f"{source}_animestudio_{stage}_{animestudio_log_suffix(type_name)}_"
                f"shard{shard_index:02d}_of_{int(shard['count']):02d}"
            )
            future = executor.submit(
                run_animestudio_stage,
                source=source,
                input_root=input_root,
                output_root=output_root,
                reports_dir=reports_dir,
                animestudio_exe=animestudio_exe,
                animestudio_dummy_dlls=animestudio_dummy_dlls,
                mono_behaviour_type_tree_priority=options.get("mono_behaviour_type_tree_priority"),
                stage=stage,
                export_type=options.get("export_type"),
                names=shard["names"],
                filter_data=shard["filter_data"],
                types=(type_spec,) if type_spec is not None else (),
                command_name=command_name,
            )
            future_to_shard[future] = shard

        for future in as_completed(future_to_shard):
            shard = future_to_shard[future]
            result = future.result()
            shard_index = int(shard["index"])
            result_by_shard[shard_index] = result
            log(
                f"  animestudio asset shard {stage}:{type_name} "
                f"{shard_index}/{int(shard['count'])} for {source}: returncode={result.returncode}"
            )

    ordered_results = [
        result_by_shard[index]
        for index in sorted(result_by_shard)
    ]
    updated_cache_entries = 0
    if asset_work["cache_enabled"]:
        for shard in shards:
            result = result_by_shard.get(int(shard["index"]))
            if result is None or result.returncode != 0:
                continue
            updated_cache_entries += update_asset_cache_entries(
                cache=asset_work["asset_cache"],
                entries=shard["entries"],
                item=item,
                plan=plan,
                output_root=output_root,
                source=source,
                stage=stage,
            )
        save_animestudio_asset_cache(asset_work["cache_path"], asset_work["asset_cache"])
    asset_info["updated_entry_count"] = updated_cache_entries
    asset_info["successful_shard_count"] = sum(1 for result in ordered_results if result.returncode == 0)
    asset_info["failed_shard_count"] = sum(1 for result in ordered_results if result.returncode != 0)
    output_entry_count = count_existing_animestudio_asset_outputs(
        output_root=output_root,
        source=source,
        stage=stage,
        entries=asset_work["matched_entries"],
    )
    missing_output_count = max(0, len(asset_work["matched_entries"]) - output_entry_count)
    log_issues = merge_animestudio_log_issues(ordered_results)
    export_error_count = int(log_issues.get("export_error_count") or 0)
    asset_info["output_entry_count"] = output_entry_count
    asset_info["missing_output_count"] = missing_output_count
    asset_info["export_error_count"] = export_error_count
    missing_outputs_allowed = (
        type_name in ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES
        and export_error_count == 0
        and all(result.returncode == 0 for result in ordered_results)
    )
    asset_info["allowed_missing_output_count"] = missing_output_count if missing_outputs_allowed else 0
    all_succeeded = (
        bool(ordered_results)
        and all(result.returncode == 0 for result in ordered_results)
        and (missing_output_count == 0 or missing_outputs_allowed)
        and export_error_count == 0
    )
    if missing_output_count and missing_outputs_allowed:
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"allowed {missing_output_count} no-output Mesh entries"
        )
    if not all_succeeded and (missing_output_count or export_error_count):
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"marking failed because missing_outputs={missing_output_count} "
            f"export_errors={export_error_count}"
        )
    return (
        ordered_results,
        [item["item_name"]] if all_succeeded else [],
        [] if all_succeeded else [item["item_name"]],
    )


def run_animestudio_stage_plan(
    source: str,
    input_root: Path,
    output_root: Path,
    reports_dir: Path,
    animestudio_exe: Path,
    animestudio_dummy_dlls: Path | None,
    stage: str,
    plan: dict[str, Any],
    jobs: int,
) -> list[CommandResult]:
    options = plan["options"]
    run_item_names = set(plan.get("run_items", []))
    runnable_items = [
        item for item in plan.get("items", [])
        if item["item_name"] in run_item_names
    ]
    if not runnable_items:
        plan["command_results"] = []
        plan["succeeded_items"] = []
        plan["failed_items"] = []
        return []

    all_results: list[CommandResult] = []
    succeeded: list[str] = []
    failed: list[str] = []
    normal_items: list[dict[str, Any]] = []

    if stage != "maps":
        for item in runnable_items:
            asset_work = prepare_animestudio_asset_shards(
                source=source,
                output_root=output_root,
                stage=stage,
                plan=plan,
                runnable_items=[item],
                jobs=jobs,
            )
            if asset_work is None:
                normal_items.append(item)
                continue
            item_results, item_succeeded, item_failed = run_animestudio_asset_shard_work(
                source=source,
                input_root=input_root,
                output_root=output_root,
                reports_dir=reports_dir,
                animestudio_exe=animestudio_exe,
                animestudio_dummy_dlls=animestudio_dummy_dlls,
                stage=stage,
                plan=plan,
                jobs=jobs,
                asset_work=asset_work,
            )
            all_results.extend(item_results)
            succeeded.extend(item_succeeded)
            failed.extend(item_failed)
    else:
        normal_items = list(runnable_items)

    if normal_items and (stage == "maps" or len(normal_items) <= 1):
        clear_animestudio_stage_outputs(output_root, source, stage, normal_items)
        command_name = None
        if stage != "maps" and all_results:
            command_name = f"{source}_animestudio_{stage}_{animestudio_log_suffix(normal_items[0]['item_name'])}"
        normal_type_specs = (
            plan.get("type_specs_to_run", ())
            if stage == "maps"
            else tuple(item["type_spec"] for item in normal_items if item.get("type_spec") is not None)
        )
        result = run_animestudio_stage(
            source=source,
            input_root=input_root,
            output_root=output_root,
            reports_dir=reports_dir,
            animestudio_exe=animestudio_exe,
            animestudio_dummy_dlls=animestudio_dummy_dlls,
            mono_behaviour_type_tree_priority=options.get("mono_behaviour_type_tree_priority"),
            stage=stage,
            export_type=options.get("export_type"),
            map_op=options.get("map_op"),
            map_type=options.get("map_type"),
            map_name=options.get("map_name"),
            names=options.get("names"),
            containers=options.get("containers"),
            filter_data=options.get("filter_data"),
            types=normal_type_specs,
            command_name=command_name,
        )
        all_results.append(result)
        item_names = [item["item_name"] for item in normal_items]
        if result.returncode == 0:
            succeeded.extend(item_names)
        else:
            failed.extend(item_names)

    elif normal_items:
        max_workers = min(max(1, jobs), len(normal_items))
        log(f"  animestudio stage {stage} for {source}: launching {len(normal_items)} type jobs with max_workers={max_workers}")
        result_by_item: dict[str, CommandResult] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {}
            for item in normal_items:
                clear_animestudio_stage_outputs(output_root, source, stage, [item])
                item_name = item["item_name"]
                type_spec = item["type_spec"]
                command_name = f"{source}_animestudio_{stage}_{animestudio_log_suffix(item_name)}"
                future = executor.submit(
                    run_animestudio_stage,
                    source=source,
                    input_root=input_root,
                    output_root=output_root,
                    reports_dir=reports_dir,
                    animestudio_exe=animestudio_exe,
                    animestudio_dummy_dlls=animestudio_dummy_dlls,
                    mono_behaviour_type_tree_priority=options.get("mono_behaviour_type_tree_priority"),
                    stage=stage,
                    export_type=options.get("export_type"),
                    map_op=options.get("map_op"),
                    map_type=options.get("map_type"),
                    map_name=options.get("map_name"),
                    names=options.get("names"),
                    containers=options.get("containers"),
                    filter_data=options.get("filter_data"),
                    types=(type_spec,) if type_spec is not None else (),
                    command_name=command_name,
                )
                future_to_item[future] = item

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                result = future.result()
                result_by_item[item["item_name"]] = result
                log(
                    f"  animestudio type {stage}:{item['item_name']} for {source}: "
                    f"returncode={result.returncode}"
                )

        normal_results = [
            result_by_item[item["item_name"]]
            for item in normal_items
            if item["item_name"] in result_by_item
        ]
        all_results.extend(normal_results)
        succeeded.extend(
            item["item_name"]
            for item in normal_items
            if item["item_name"] in result_by_item and result_by_item[item["item_name"]].returncode == 0
        )
        failed.extend(
            item["item_name"]
            for item in normal_items
            if item["item_name"] in result_by_item and result_by_item[item["item_name"]].returncode != 0
        )

    default_stdout_log = str(reports_dir / f"{source}_animestudio_{stage}.stdout.log")
    default_stderr_log = str(reports_dir / f"{source}_animestudio_{stage}.stderr.log")
    if not all_results and plan.get("asset_caches"):
        stdout_log, stderr_log = write_animestudio_asset_cache_log(
            source=source,
            stage=stage,
            reports_dir=reports_dir,
            asset_info={"asset_caches": plan.get("asset_caches", [])},
        )
    elif len(all_results) == 1 and all_results[0].stdout_log == default_stdout_log:
        stdout_log = all_results[0].stdout_log
        stderr_log = all_results[0].stderr_log
    else:
        stdout_log, stderr_log = write_animestudio_parallel_log_index(source, stage, reports_dir, all_results)

    plan["command_results"] = all_results
    plan["succeeded_items"] = list(dict.fromkeys(succeeded))
    plan["failed_items"] = list(dict.fromkeys(failed))
    plan["stdout_log"] = stdout_log if all_results or plan.get("asset_caches") else default_stdout_log
    plan["stderr_log"] = stderr_log if all_results or plan.get("asset_caches") else default_stderr_log
    return all_results


def summarize_animestudio_source(
    output_root: Path,
    source: str,
    source_report_dir: Path,
    command_results_by_name: dict[str, CommandResult],
    previous_summary: dict[str, Any],
    selected_stages: tuple[str, ...],
    stage_plans: dict[str, dict[str, Any]],
    source_fingerprint: dict[str, Any],
) -> dict[str, Any]:
    previous_source = ((previous_summary.get("animestudio") or {}).get("sources") or {}).get(source, {})
    result: dict[str, Any] = {
        "root": str(animestudio_source_root(output_root, source)),
        "source_fingerprint": source_fingerprint,
        "maps": {
            "output_root": str(animestudio_stage_dir(output_root, source, "maps")),
            "file_count": count_files(animestudio_stage_dir(output_root, source, "maps")),
            "returncode": previous_source.get("maps", {}).get("returncode"),
            "stdout_log": previous_source.get("maps", {}).get(
                "stdout_log", str(source_report_dir / f"{source}_animestudio_maps.stdout.log")
            ),
            "stderr_log": previous_source.get("maps", {}).get(
                "stderr_log", str(source_report_dir / f"{source}_animestudio_maps.stderr.log")
            ),
        },
        "convert_by_type": {
            "output_root": str(animestudio_stage_dir(output_root, source, "convert_by_type")),
            "file_count": count_files(animestudio_stage_dir(output_root, source, "convert_by_type")),
            "returncode": previous_source.get("convert_by_type", {}).get("returncode"),
            "stdout_log": previous_source.get("convert_by_type", {}).get(
                "stdout_log", str(source_report_dir / f"{source}_animestudio_convert_by_type.stdout.log")
            ),
            "stderr_log": previous_source.get("convert_by_type", {}).get(
                "stderr_log", str(source_report_dir / f"{source}_animestudio_convert_by_type.stderr.log")
            ),
        },
        "json_by_type": {
            "output_root": str(animestudio_stage_dir(output_root, source, "json_by_type")),
            "file_count": count_files(animestudio_stage_dir(output_root, source, "json_by_type")),
            "returncode": previous_source.get("json_by_type", {}).get("returncode"),
            "stdout_log": previous_source.get("json_by_type", {}).get(
                "stdout_log", str(source_report_dir / f"{source}_animestudio_json_by_type.stdout.log")
            ),
            "stderr_log": previous_source.get("json_by_type", {}).get(
                "stderr_log", str(source_report_dir / f"{source}_animestudio_json_by_type.stderr.log")
            ),
        },
    }
    for stage in ANIMESTUDIO_STAGES:
        current = command_results_by_name.get(f"{source}_animestudio_{stage}")
        plan = stage_plans.get(stage)
        plan_results = plan.get("command_results", []) if plan else []
        previous_stage = previous_source.get(stage, {})
        result[stage]["selected"] = stage in selected_stages
        result[stage]["ran_this_run"] = current is not None or bool(plan_results)
        result[stage]["selected_items"] = plan.get("selected_items", []) if plan else previous_stage.get("selected_items", [])
        result[stage]["cached_items"] = plan.get("cached_items", []) if plan else previous_stage.get("cached_items", [])
        result[stage]["run_items"] = plan.get("run_items", []) if plan else previous_stage.get("run_items", [])
        result[stage]["succeeded_items"] = plan.get("succeeded_items", []) if plan else previous_stage.get("succeeded_items", [])
        result[stage]["failed_items"] = plan.get("failed_items", []) if plan else previous_stage.get("failed_items", [])
        result[stage]["forced_refresh_items"] = (
            plan.get("forced_refresh_items", []) if plan else previous_stage.get("forced_refresh_items", [])
        )
        result[stage]["item_file_counts"] = plan.get("item_file_counts", {}) if plan else previous_stage.get("item_file_counts", {})
        result[stage]["cache_state"] = plan.get("cache_state") if plan else previous_stage.get("cache_state")
        if plan and plan.get("asset_caches"):
            result[stage]["asset_caches"] = plan["asset_caches"]
        elif previous_stage.get("asset_caches"):
            result[stage]["asset_caches"] = previous_stage["asset_caches"]
        if plan and plan.get("asset_cache"):
            result[stage]["asset_cache"] = plan["asset_cache"]
        elif previous_stage.get("asset_cache"):
            result[stage]["asset_cache"] = previous_stage["asset_cache"]
        if current is not None:
            result[stage]["returncode"] = current.returncode
            result[stage]["stdout_log"] = current.stdout_log
            result[stage]["stderr_log"] = current.stderr_log
        elif plan_results:
            result[stage]["returncode"] = (
                0
                if all(item.returncode == 0 for item in plan_results) and not plan.get("failed_items")
                else 1
            )
            result[stage]["stdout_log"] = plan.get("stdout_log", result[stage].get("stdout_log"))
            result[stage]["stderr_log"] = plan.get("stderr_log", result[stage].get("stderr_log"))
        elif plan and plan.get("stdout_log"):
            result[stage]["returncode"] = 0 if not plan.get("failed_items") else 1
            result[stage]["stdout_log"] = plan.get("stdout_log", result[stage].get("stdout_log"))
            result[stage]["stderr_log"] = plan.get("stderr_log", result[stage].get("stderr_log"))
            result[stage]["ran_this_run"] = True
        if plan_results:
            result[stage]["runs"] = [asdict(item) for item in plan_results]
            result[stage]["log_issues"] = merge_animestudio_log_issues(plan_results)
        else:
            result[stage]["log_issues"] = summarize_animestudio_log_issues(
                result[stage].get("stdout_log"),
                result[stage].get("stderr_log"),
            )
    result["total_files"] = sum(item["file_count"] for item in result.values() if isinstance(item, dict) and "file_count" in item)
    return result


def build_failed_decode_text(
    structured_failures: dict[str, list[dict[str, str]]],
    raw_failures: dict[str, list[dict[str, Any]]],
    sources: tuple[str, ...],
) -> list[str]:
    lines: list[str] = []
    for source in sources:
        sf = structured_failures.get(source, [])
        rf = raw_failures.get(source, [])
        if not sf and not rf:
            continue
        lines.append(f"[{source}]")
        for item in sf:
            lines.append(f"structured\t{item['file']}\t{item['reason']}")
        for item in rf:
            file_name = item.get("file") or "<chunk>"
            chunk = item.get("chunk") or "-"
            lines.append(f"raw_vfs\t{chunk}\t{file_name}\t{item['reason']}")
        lines.append("")
    return lines


def build_manifest_missing_text(
    structured_manifest: dict[str, list[dict[str, str]]],
    raw_manifest_chunks: dict[str, list[dict[str, Any]]],
    sources: tuple[str, ...],
) -> list[str]:
    lines: list[str] = []
    for source in sources:
        structured_count = len(structured_manifest.get(source, []))
        raw_chunks = raw_manifest_chunks.get(source, [])
        if structured_count == 0 and not raw_chunks:
            continue
        lines.append(f"[{source}]")
        if structured_count:
            lines.append(f"structured_manifest_reference_count\t{structured_count}")
        for item in raw_chunks:
            lines.append(
                "raw_vfs_missing_chunk"
                f"\t{item['block']}"
                f"\t{item['chunk']}"
                f"\treferenced_files={item['referenced_file_count']}"
                f"\t{item['reason']}"
            )
        lines.append("")
    return lines


def main() -> int:
    args = parse_args()
    game_root = args.game_root.resolve()
    output_root = args.output.resolve()
    reports_root = ensure_dir(DEFAULT_REPORTS.resolve())
    report_run_id = current_report_run_id()
    reports_dir = ensure_dir(reports_root / report_run_id)
    legacy_reports_dir = output_root / "reports"
    structured_dumper = args.fluffy.resolve()
    animestudio = args.animestudio.resolve()
    selected_sources = ordered_unique(args.sources)
    selected_animestudio_stages = ordered_unique(args.animestudio_stages)
    animestudio_stage_options = animestudio_stage_options_for_scope(args.animestudio_scope, args.animestudio_asset_mode)
    vfs_index_enabled = not args.skip_vfs_index and not args.skip_animestudio and args.animestudio_scope != "story"
    webui_texture_name_filter: Path | None = None
    webui_texture_name_filter_signature: dict[str, Any] | None = None
    if not args.skip_animestudio and args.animestudio_scope != "story" and args.animestudio_asset_mode == "webui":
        webui_texture_name_filter, webui_texture_name_filter_signature = write_webui_texture_name_filter(output_root)
    refresh_selectors = ordered_unique(tuple(args.animestudio_refresh_types))
    if args.animestudio_jobs < 1:
        raise SystemExit("--animestudio-jobs must be at least 1")
    if args.animestudio_shards < 0:
        raise SystemExit("--animestudio-shards must be 0 or greater")
    animestudio_jobs = args.animestudio_jobs

    if not game_root.exists():
        raise SystemExit(f"Game root not found: {game_root}")
    if not structured_dumper.exists() and (not args.skip_structured or vfs_index_enabled):
        raise SystemExit(f"structured dumper not found: {structured_dumper}")
    if not animestudio.exists() and not args.skip_animestudio:
        raise SystemExit(f"AnimeStudio CLI not found: {animestudio}")
    if args.skip_animestudio:
        animestudio_dummy_dlls = None
        animestudio_dummy_dll_source = None
    else:
        animestudio_dummy_dlls, animestudio_dummy_dll_source = resolve_animestudio_dummy_dlls(
            args.animestudio_dummy_dlls,
            game_root,
        )
    animestudio_mono_behaviour_type_tree_priority = animestudio_cli_type_tree_priority(
        args.animestudio_mono_behaviour_type_tree_priority
    )

    ensure_dir(output_root)
    log("starting full export")
    log(f"  game root: {game_root}")
    log(f"  output root: {output_root}")
    log(f"  reports root: {reports_root}")
    log(f"  reports run id: {report_run_id}")
    log(f"  reports run dir: {reports_dir}")
    log(f"  selected sources: {', '.join(selected_sources)}")
    log(f"  structured export: {'disabled' if args.skip_structured else 'enabled'}")
    log(f"  vfs index: {'enabled' if vfs_index_enabled else 'disabled'}")
    log("  raw vfs export: disabled")
    log(f"  animestudio export: {'disabled' if args.skip_animestudio else 'enabled'}")
    log(f"  animestudio scope: {args.animestudio_scope}")
    log(f"  animestudio asset mode: {args.animestudio_asset_mode}")
    log(f"  animestudio stages: {', '.join(selected_animestudio_stages)}")
    log(f"  animestudio jobs: {animestudio_jobs}")
    log(
        "  animestudio asset shards: "
        f"{args.animestudio_shards if args.animestudio_shards else f'auto ({animestudio_jobs})'}"
    )
    log(f"  animestudio asset cache: {'disabled' if args.no_animestudio_asset_cache else 'enabled'}")
    log(f"  animestudio MonoBehaviour TypeTree priority: {animestudio_mono_behaviour_type_tree_priority}")
    log(f"  animestudio refresh selectors: {', '.join(refresh_selectors) if refresh_selectors else 'none'}")
    if webui_texture_name_filter is not None and webui_texture_name_filter_signature is not None:
        log(
            f"  animestudio WebUI texture filter: {webui_texture_name_filter} "
            f"({webui_texture_name_filter_signature.get('pattern_count', 0)} patterns)"
        )
    if animestudio_dummy_dlls:
        log(f"  animestudio dummy dlls: {animestudio_dummy_dlls} ({animestudio_dummy_dll_source})")
    else:
        log("  animestudio dummy dlls: not configured")
    log("  source inventory: disabled")
    log(f"  report-only mode: {'enabled' if args.report_only else 'disabled'}")
    previous_summary_path = reports_root / "export_full_summary.json"
    legacy_summary_path = legacy_reports_dir / "export_full_summary.json"
    previous_summary = load_previous_summary(previous_summary_path, legacy_summary_path)

    source_sizes = collect_source_sizes(game_root, selected_sources)
    for source in selected_sources:
        info = source_sizes[source]
        log(
            f"source size {source}: files={info['files']} "
            f"bytes={info['bytes']} gb={info['gigabytes']}"
        )
    inventory_summary: dict[str, Any] | None = None
    if previous_summary.get("inventory"):
        inventory_summary = previous_summary["inventory"]
        log("reusing previous inventory summary")

    command_results: list[CommandResult] = []
    command_results_by_name: dict[str, CommandResult] = {}
    vfs_index_summary: dict[str, Any] = dict(previous_summary.get("vfs_index") or {})
    structured_summary: dict[str, Any] = {}
    raw_summary: dict[str, Any] = {}
    structured_failures_by_source: dict[str, list[dict[str, str]]] = {}
    structured_manifest_by_source: dict[str, list[dict[str, str]]] = {}
    raw_failures_by_source: dict[str, list[dict[str, Any]]] = {}
    raw_manifest_chunks_by_source: dict[str, list[dict[str, Any]]] = {}
    animestudio_cli_signature = build_file_signature(animestudio) if not args.skip_animestudio else None
    animestudio_dummy_dll_signature = (
        build_dummy_dll_signature(animestudio_dummy_dlls) if not args.skip_animestudio else None
    )
    animestudio_manifest_file = animestudio_manifest_path(output_root)
    animestudio_manifest = load_animestudio_manifest(animestudio_manifest_file) if not args.skip_animestudio else default_animestudio_manifest()
    animestudio_summary: dict[str, Any] = {
        "enabled": not args.skip_animestudio,
        "exe": str(animestudio),
        "exe_signature": animestudio_cli_signature,
        "dummy_dlls": str(animestudio_dummy_dlls) if animestudio_dummy_dlls else None,
        "dummy_dlls_source": animestudio_dummy_dll_source,
        "dummy_dll_signature": animestudio_dummy_dll_signature,
        "game": ANIMESTUDIO_GAME,
        "scope": args.animestudio_scope,
        "asset_mode": args.animestudio_asset_mode,
        "webui_texture_name_filter": str(webui_texture_name_filter) if webui_texture_name_filter else None,
        "webui_texture_name_filter_signature": webui_texture_name_filter_signature,
        "mono_behaviour_type_tree_priority": animestudio_mono_behaviour_type_tree_priority,
        "jobs": animestudio_jobs,
        "asset_shards": args.animestudio_shards,
        "asset_cache_enabled": not args.no_animestudio_asset_cache,
        "type_manifest_path": str(animestudio_manifest_file),
        "type_manifest_exists": animestudio_manifest_file.exists(),
        "type_manifest_entry_count": len(animestudio_manifest.get("entries", {})),
        "refresh_selectors": list(refresh_selectors),
        "sources_selected": list(selected_sources),
        "stages_selected": list(selected_animestudio_stages),
        "sources": {},
    }

    for source in selected_sources:
        source_root = game_root / source
        source_report_dir = ensure_dir(reports_dir / source)
        log(f"processing source {source}")
        log(f"  source root: {source_root}")
        log(f"  source reports: {source_report_dir}")

        current_vfs_index_path = vfs_index_path(output_root, source, "bundle")
        if vfs_index_enabled and not args.report_only:
            log(f"  vfs index path: {current_vfs_index_path}")
            cmd = [
                str(structured_dumper),
                "vfs-index",
                "-s",
                str(source_root),
                "-o",
                str(current_vfs_index_path),
                "-b",
                "bundle",
            ]
            if source == "Persistent":
                fallback_root = game_root / "StreamingAssets"
                if fallback_root.exists():
                    cmd.extend(["--fallback-assets", str(fallback_root)])
            result = run_logged_command(f"{source}_vfs_index_bundle", cmd, ROOT, source_report_dir)
            command_results.append(result)
            command_results_by_name[result.name] = result

        if vfs_index_enabled or current_vfs_index_path.exists():
            current_vfs_index = command_results_by_name.get(f"{source}_vfs_index_bundle")
            vfs_index_summary[source] = summarize_vfs_index(current_vfs_index_path, current_vfs_index)
            if vfs_index_summary[source].get("exists"):
                log(
                    f"  vfs index summary {source}: "
                    f"files={vfs_index_summary[source].get('file_count')} "
                    f"chunks={vfs_index_summary[source].get('chunk_count')} "
                    f"missing_chunks={vfs_index_summary[source].get('missing_chunk_count')}"
                )

        if not args.skip_structured and not args.report_only:
            structured_out = structured_output_dir(output_root, source)
            log(f"  structured output dir: {structured_out}")
            cmd = [str(structured_dumper), "dump", "-s", str(source_root), "-o", str(structured_out)]
            if source == "Persistent":
                fallback_root = game_root / "StreamingAssets"
                if fallback_root.exists():
                    log(f"  using fallback assets from {fallback_root}")
                    cmd.extend(["--fallback-assets", str(fallback_root)])
            result = run_logged_command(f"{source}_structured_dump", cmd, ROOT, source_report_dir)
            command_results.append(result)
            command_results_by_name[result.name] = result

        if not args.skip_structured:
            stdout_log = source_report_dir / f"{source}_structured_dump.stdout.log"
            stderr_log = source_report_dir / f"{source}_structured_dump.stderr.log"
            stdout_text = stdout_log.read_text(encoding="utf-8") if stdout_log.exists() else ""
            stderr_text = stderr_log.read_text(encoding="utf-8") if stderr_log.exists() else ""
            all_failures = parse_structured_failures(stderr_text)
            actual_failures, manifest_only = split_structured_failures(source, all_failures)
            structured_failures_by_source[source] = actual_failures
            structured_manifest_by_source[source] = manifest_only
            previous_structured = (previous_summary.get("structured") or {}).get(source, {})
            current_structured = command_results_by_name.get(f"{source}_structured_dump")
            structured_summary[source] = {
                "output_root": str(
                    structured_output_dir(output_root, source)
                    if current_structured is not None
                    else resolve_existing_structured_output_dir(output_root, source)
                ),
                "returncode": (
                    current_structured.returncode if current_structured is not None else previous_structured.get("returncode")
                ),
                "warning_failure_count": parse_warning_failure_count(stdout_text),
                "actual_failure_count": len(actual_failures),
                "manifest_reference_count": len(manifest_only),
                "stdout_log": str(stdout_log),
                "stderr_log": str(stderr_log),
            }
            log(
                f"  structured summary {source}: "
                f"actual_failures={structured_summary[source]['actual_failure_count']} "
                f"manifest_refs={structured_summary[source]['manifest_reference_count']} "
                f"warnings={structured_summary[source]['warning_failure_count']}"
            )

        animestudio_stage_plans: dict[str, dict[str, Any]] = {}
        if not args.skip_animestudio:
            log(f"  animestudio broad export root: {animestudio_source_root(output_root, source)}")
            for stage in selected_animestudio_stages:
                options = dict(animestudio_stage_options[stage])
                options["mono_behaviour_type_tree_priority"] = animestudio_mono_behaviour_type_tree_priority
                options["asset_cache_enabled"] = not args.no_animestudio_asset_cache
                options["asset_shards"] = args.animestudio_shards
                if stage == "maps":
                    options["map_name"] = f"endfield_{source.lower()}_assets"
                if options.get("asset_map_filter"):
                    map_path = animestudio_stage_dir(output_root, source, "maps") / f"endfield_{source.lower()}_assets.map"
                    if not map_path.exists() and "maps" not in selected_animestudio_stages and not args.report_only:
                        raise SystemExit(
                            "Map-filtered AnimeStudio asset export requires an asset map. "
                            f"Include `maps` in --animestudio-stages before this stage. Missing: {map_path}"
                        )
                    options["map_op"] = "AssetMap,Load"
                    options["map_type"] = "MessagePack"
                    options["map_name"] = str(map_path)
                    if options.get("webui_asset_filter"):
                        options["names"] = str(webui_texture_name_filter) if webui_texture_name_filter else None
                        options["webui_asset_filter_signature"] = webui_texture_name_filter_signature
                plan = plan_animestudio_stage(
                    source=source,
                    output_root=output_root,
                    stage=stage,
                    options=options,
                    manifest_entries=animestudio_manifest.get("entries", {}),
                    cli_signature=animestudio_cli_signature,
                    dummy_dll_signature=animestudio_dummy_dll_signature,
                    source_fingerprint=source_sizes[source],
                    refresh_selectors=refresh_selectors,
                )
                animestudio_stage_plans[stage] = plan
                log(
                    f"  animestudio stage plan {stage}: "
                    f"selected={len(plan['selected_items'])} "
                    f"cached={len(plan['cached_items'])} "
                    f"run={len(plan['run_items'])} "
                    f"state={plan['cache_state']}"
                )
                if plan["forced_refresh_items"]:
                    log(f"    forced refresh: {', '.join(plan['forced_refresh_items'])}")
                if plan["cached_items"]:
                    log(f"    cache hits: {', '.join(plan['cached_items'])}")
                if plan["run_items"]:
                    log(f"    pending items: {', '.join(plan['run_items'])}")

            if not args.report_only:
                for stage in selected_animestudio_stages:
                    plan = animestudio_stage_plans[stage]
                    if not plan["should_run"]:
                        log(f"  animestudio stage {stage} for {source}: cache hit, skipping")
                        continue
                    log(f"  animestudio stage {stage} for {source}: running {', '.join(plan['run_items'])}")
                    stage_results = run_animestudio_stage_plan(
                        source=source,
                        input_root=source_root,
                        output_root=output_root,
                        reports_dir=source_report_dir,
                        animestudio_exe=animestudio,
                        animestudio_dummy_dlls=animestudio_dummy_dlls,
                        stage=stage,
                        plan=plan,
                        jobs=animestudio_jobs,
                    )
                    command_results.extend(stage_results)
                    for result in stage_results:
                        command_results_by_name[result.name] = result
                    succeeded_items = plan.get("succeeded_items", [])
                    failed_items = plan.get("failed_items", [])
                    if succeeded_items:
                        success_plan = copy_animestudio_plan_for_run_items(plan, succeeded_items)
                        update_animestudio_manifest_for_stage(
                            manifest=animestudio_manifest,
                            output_root=output_root,
                            source=source,
                            stage=stage,
                            plan=success_plan,
                            cli_signature=animestudio_cli_signature,
                            dummy_dll_signature=animestudio_dummy_dll_signature,
                            source_fingerprint=source_sizes[source],
                        )
                        plan["item_file_counts"] = success_plan.get("item_file_counts", plan.get("item_file_counts", {}))
                        save_animestudio_manifest(animestudio_manifest_file, animestudio_manifest)
                    if failed_items:
                        log(f"  animestudio stage {stage} for {source} failed items: {', '.join(failed_items)}")
            else:
                for stage in selected_animestudio_stages:
                    plan = animestudio_stage_plans[stage]
                    if plan["run_items"]:
                        log(
                            f"  animestudio report-only {stage} for {source}: "
                            f"would refresh {', '.join(plan['run_items'])}"
                        )
                    else:
                        log(f"  animestudio report-only {stage} for {source}: cache hit")

            animestudio_summary["sources"][source] = summarize_animestudio_source(
                output_root=output_root,
                source=source,
                source_report_dir=source_report_dir,
                command_results_by_name=command_results_by_name,
                previous_summary=previous_summary,
                selected_stages=selected_animestudio_stages,
                stage_plans=animestudio_stage_plans,
                source_fingerprint=source_sizes[source],
            )
            source_info = animestudio_summary["sources"][source]
            log(
                f"  animestudio summary {source}: "
                f"maps={source_info['maps']['file_count']} "
                f"convert={source_info['convert_by_type']['file_count']} "
                f"json={source_info['json_by_type']['file_count']}"
            )

    if not args.skip_animestudio:
        animestudio_summary["type_manifest_exists"] = animestudio_manifest_file.exists()
        animestudio_summary["type_manifest_entry_count"] = len(animestudio_manifest.get("entries", {}))

    unresolved_dir = ensure_dir(output_root / "unresolved")
    log(f"writing unresolved summaries to {unresolved_dir}")
    failed_lines = build_failed_decode_text(structured_failures_by_source, raw_failures_by_source, selected_sources)
    failed_txt = unresolved_dir / "failed_to_decode.txt"
    failed_txt.write_text("\n".join(failed_lines) if failed_lines else "", encoding="utf-8")
    manifest_lines = build_manifest_missing_text(
        structured_manifest_by_source,
        raw_manifest_chunks_by_source,
        selected_sources,
    )
    manifest_txt = unresolved_dir / "manifest_reference_missing.txt"
    manifest_txt.write_text("\n".join(manifest_lines) if manifest_lines else "", encoding="utf-8")
    command_failures = [item for item in command_results if item.returncode != 0]
    summary_commands = [asdict(item) for item in command_results]
    if args.report_only and not summary_commands:
        summary_commands = previous_summary.get("commands", [])

    summary = {
        "game_root": str(game_root),
        "output_root": str(output_root),
        "reports_root": str(reports_root),
        "reports_run_root": str(reports_dir),
        "report_run_id": report_run_id,
        "sources_selected": list(selected_sources),
        "source_sizes": source_sizes,
        "inventory": inventory_summary,
        "commands": summary_commands,
        "vfs_index": vfs_index_summary,
        "structured": structured_summary,
        "raw_vfs": raw_summary,
        "animestudio": animestudio_summary,
        "failed_to_decode_txt": str(failed_txt),
        "manifest_reference_missing_txt": str(manifest_txt),
        "command_failure_count": len(command_failures),
        "command_failures": [asdict(item) for item in command_failures],
    }
    log(f"writing json summary to {reports_dir / 'export_full_summary.json'}")
    write_json(reports_dir / "export_full_summary.json", summary)
    log(f"updating latest json summary at {reports_root / 'export_full_summary.json'}")
    write_json(reports_root / "export_full_summary.json", summary)

    md_lines = [
        "# Full Export Summary",
        "",
        f"- Game root: `{game_root}`",
        f"- Output root: `{output_root}`",
        f"- Selected sources: `{', '.join(selected_sources)}`",
        "",
        "## Source Sizes",
    ]
    for source in selected_sources:
        info = source_sizes[source]
        md_lines.append(
            f"- `{source}`: `{info['files']}` files, `{info['gigabytes']}` GB"
        )

    if inventory_summary:
        md_lines.extend(
            [
                "",
                "## Source Inventory",
                f"- Inventory JSON: `{inventory_summary['inventory_json']}`",
                f"- Top-level file copy dir: `{inventory_summary['top_level_file_copy_dir']}`",
                f"- Indexed entries: `{inventory_summary['entry_count']}`",
            ]
        )

    md_lines.extend(["", "## VFS Index"])
    if not vfs_index_enabled and not vfs_index_summary:
        md_lines.append("- Skipped")
    else:
        for source in selected_sources:
            info = vfs_index_summary.get(source, {})
            if not info:
                md_lines.append(f"- `{source}`: skipped")
                continue
            md_lines.append(
                f"- `{source}`: exists=`{info.get('exists')}`, "
                f"files=`{info.get('file_count')}`, "
                f"chunks=`{info.get('chunk_count')}`, "
                f"missing_chunks=`{info.get('missing_chunk_count')}`"
            )
            md_lines.append(f"  index: `{info.get('index_path')}`")
            if info.get("stdout_log"):
                md_lines.append(f"  stdout: `{info.get('stdout_log')}`")
            if info.get("stderr_log"):
                md_lines.append(f"  stderr: `{info.get('stderr_log')}`")

    md_lines.extend(["", "## Structured Export"])
    if args.skip_structured:
        md_lines.append("- Skipped")
    else:
        for source in selected_sources:
            info = structured_summary.get(source, {})
            md_lines.append(
                f"- `{source}`: returncode=`{info.get('returncode')}`, "
                f"actual_failures=`{info.get('actual_failure_count')}`, "
                f"manifest_refs=`{info.get('manifest_reference_count')}`"
            )
            md_lines.append(f"  stdout: `{info.get('stdout_log')}`")
            md_lines.append(f"  stderr: `{info.get('stderr_log')}`")

    md_lines.extend(["", "## Raw VFS Export"])
    md_lines.append("- Skipped")

    md_lines.extend(["", "## AnimeStudio Export"])
    if args.skip_animestudio:
        md_lines.append("- Skipped")
    else:
        md_lines.append(f"- Executable: `{animestudio}`")
        md_lines.append(f"- Game: `{ANIMESTUDIO_GAME}`")
        md_lines.append(f"- Scope: `{args.animestudio_scope}`")
        md_lines.append(f"- Asset mode: `{args.animestudio_asset_mode}`")
        md_lines.append(f"- Selected stages: `{', '.join(selected_animestudio_stages)}`")
        md_lines.append(f"- Parallel jobs: `{animestudio_jobs}`")
        md_lines.append(
            "- Asset shards: "
            f"`{args.animestudio_shards if args.animestudio_shards else f'auto ({animestudio_jobs})'}`"
        )
        md_lines.append(f"- Asset cache: `{'disabled' if args.no_animestudio_asset_cache else 'enabled'}`")
        md_lines.append(f"- MonoBehaviour TypeTree priority: `{animestudio_mono_behaviour_type_tree_priority}`")
        md_lines.append(
            f"- DummyDlls: `{animestudio_dummy_dlls}`"
            if animestudio_dummy_dlls
            else "- DummyDlls: `not configured`"
        )
        if animestudio_dummy_dll_source:
            md_lines.append(f"- DummyDll source: `{animestudio_dummy_dll_source}`")
        md_lines.append(f"- Cache manifest: `{animestudio_summary.get('type_manifest_path')}`")
        md_lines.append(
            "- Refresh selectors: "
            f"`{', '.join(animestudio_summary.get('refresh_selectors') or ['none'])}`"
        )
        for source in selected_sources:
            info = animestudio_summary["sources"].get(source, {})
            md_lines.append(
                f"- `{source}`: maps=`{info.get('maps', {}).get('file_count')}`, "
                f"convert=`{info.get('convert_by_type', {}).get('file_count')}`, "
                f"json=`{info.get('json_by_type', {}).get('file_count')}`"
            )
            md_lines.append(f"  maps log: `{info.get('maps', {}).get('stdout_log')}`")
            md_lines.append(f"  convert log: `{info.get('convert_by_type', {}).get('stdout_log')}`")
            md_lines.append(f"  json log: `{info.get('json_by_type', {}).get('stdout_log')}`")
            for stage in selected_animestudio_stages:
                stage_info = info.get(stage, {})
                md_lines.append(
                    f"  {stage}: state=`{stage_info.get('cache_state')}`, "
                    f"selected=`{len(stage_info.get('selected_items') or [])}`, "
                    f"cached=`{len(stage_info.get('cached_items') or [])}`, "
                    f"run=`{len(stage_info.get('run_items') or [])}`, "
                    f"succeeded=`{len(stage_info.get('succeeded_items') or [])}`, "
                    f"failed=`{len(stage_info.get('failed_items') or [])}`"
                )
                asset_caches = stage_info.get("asset_caches")
                if not asset_caches:
                    asset_cache = stage_info.get("asset_cache") or {}
                    asset_caches = [asset_cache] if asset_cache else []
                for asset_cache in asset_caches:
                    md_lines.append(
                        "    asset cache: "
                        f"type=`{asset_cache.get('type')}`, "
                        f"extension=`{asset_cache.get('output_extension')}`, "
                        f"matched=`{asset_cache.get('matched_entry_count')}`, "
                        f"cached=`{asset_cache.get('cached_entry_count')}`, "
                        f"pending=`{asset_cache.get('pending_entry_count')}`, "
                        f"shards=`{asset_cache.get('shard_count')}`, "
                        f"updated=`{asset_cache.get('updated_entry_count', 0)}`, "
                        f"pruned=`{asset_cache.get('pruned_output_count', 0)}`, "
                        f"removed_pending=`{asset_cache.get('removed_pending_output_count', 0)}`, "
                        f"missing_outputs=`{asset_cache.get('missing_output_count', 0)}`, "
                        f"allowed_missing=`{asset_cache.get('allowed_missing_output_count', 0)}`, "
                        f"export_errors=`{asset_cache.get('export_error_count', 0)}`, "
                        f"prepare_seconds=`{asset_cache.get('prepare_seconds')}`"
                    )
                issues = stage_info.get("log_issues") or {}
                if any(
                    int(issues.get(key) or 0)
                    for key in (
                        "error_count",
                        "warning_count",
                        "exception_count",
                        "end_of_stream_count",
                        "export_error_count",
                    )
                ):
                    md_lines.append(
                        "    log issues: "
                        f"errors=`{issues.get('error_count', 0)}`, "
                        f"warnings=`{issues.get('warning_count', 0)}`, "
                        f"exceptions=`{issues.get('exception_count', 0)}`, "
                        f"eof=`{issues.get('end_of_stream_count', 0)}`, "
                        f"export_errors=`{issues.get('export_error_count', 0)}`, "
                        f"story_like_export_errors=`{issues.get('story_like_export_error_count', 0)}`, "
                        f"metadata_only_json=`{issues.get('metadata_only_json_count', 0)}`"
                    )
                    samples = issues.get("story_like_export_error_samples") or issues.get("export_error_samples") or []
                    for sample in samples[:3]:
                        md_lines.append(
                            "    export error sample: "
                            f"`{sample.get('asset')}`"
                            + (f" - {sample.get('reason')}" if sample.get("reason") else "")
                        )
                    if not samples:
                        for sample in (issues.get("metadata_only_json_samples") or [])[:3]:
                            md_lines.append(
                                "    metadata-only sample: "
                                f"`{sample.get('asset')}`"
                                + (f" - {sample.get('exception')}" if sample.get("exception") else "")
                            )

    md_lines.extend(
        [
            "",
            "## Failed To Decode",
            f"- File: `{failed_txt}`",
            f"- Entries: `{sum(1 for line in failed_lines if line and not line.startswith('['))}`",
            "",
            "## Manifest-Only Missing References",
            f"- File: `{manifest_txt}`",
            f"- Entries: `{sum(1 for line in manifest_lines if line and not line.startswith('['))}`",
        ]
    )
    summary_md = reports_dir / "export_full_summary.md"
    summary_md.write_text("\n".join(md_lines), encoding="utf-8")
    log(f"writing markdown summary to {summary_md}")
    latest_summary_md = reports_root / "export_full_summary.md"
    latest_summary_md.write_text("\n".join(md_lines), encoding="utf-8")
    log(f"updating latest markdown summary at {latest_summary_md}")
    log(
        "finished full export: "
        f"commands={len(summary['commands'])} "
        f"command_failures={len(command_failures)} "
        f"failed_entries={sum(1 for line in failed_lines if line and not line.startswith('['))} "
        f"manifest_entries={sum(1 for line in manifest_lines if line and not line.startswith('['))}"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if command_failures:
        for failure in command_failures:
            log(
                f"command failed: {failure.name} "
                f"returncode={failure.returncode} stderr={failure.stderr_log}"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
