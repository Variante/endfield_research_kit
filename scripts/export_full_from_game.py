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

from pack_webui import (
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
DEFAULT_REPORTS = ROOT / "reports" / "export"
DEFAULT_REPORT_RUNS_TO_KEEP = 5
DEFAULT_ANIMESTUDIO = ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"
DEFAULT_STRUCTURED_DUMPER = DEFAULT_ANIMESTUDIO
SOURCES = ("StreamingAssets", "Persistent")
ANIMESTUDIO_STAGES = ("maps", "convert_by_type", "json_by_type")
ANIMESTUDIO_SCOPES = ("story", "assets", "all")
ANIMESTUDIO_ASSET_MODES = ("webui", "full", "debug")
STRUCTURED_DUMP_MODES = ("webui", "full", "debug")
WEBUI_STRUCTURED_REQUIRED_BLOCK_TYPES = (
    "table",
    "json-data",
    "video",
    "audit-video",
)
ANIMESTUDIO_STAGE_MERGE_MODES = ("auto", "never", "aggressive")
ANIMESTUDIO_STAGE_MERGE_PRIMARY_STAGE = "convert_by_type"
ANIMESTUDIO_STAGE_MERGE_SECONDARY_STAGE = "json_by_type"
ANIMESTUDIO_STAGE_MERGE_FLAG_ENV_PREFIX = "ANIMESTUDIO_STAGE_MERGE"
ANIMESTUDIO_SECONDARY_EXPORT_FLAGS = {
    "output": os.environ.get(
        f"{ANIMESTUDIO_STAGE_MERGE_FLAG_ENV_PREFIX}_OUTPUT_FLAG",
        "--secondary_export_path",
    ),
    "export_type": os.environ.get(
        f"{ANIMESTUDIO_STAGE_MERGE_FLAG_ENV_PREFIX}_EXPORT_TYPE_FLAG",
        "--secondary_export_type",
    ),
    "types": os.environ.get(
        f"{ANIMESTUDIO_STAGE_MERGE_FLAG_ENV_PREFIX}_TYPES_FLAG",
        "--secondary_types",
    ),
}
ANIMESTUDIO_STAGE_MERGE_SHARED_OPTION_KEYS = (
    "map_op",
    "map_type",
    "map_name",
    "names",
    "containers",
    "filter_data",
)
ANIMESTUDIO_GAME = "ArknightsEndfield"
ANIMESTUDIO_LOGGER_FLAGS = ("Warning", "Error")
ANIMESTUDIO_DEFAULT_JOBS = 8
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
    "Animator": ".fbx",
}
ANIMESTUDIO_CONVERT_OUTPUT_MARKER_SUFFIXES = {
    "Texture2D": (f"{ANIMESTUDIO_TEXTURE_EXTENSION}.empty.json",),
    "Animator": (".fbx.empty.json",),
}
ANIMESTUDIO_OUTPUT_BASE_RE = re.compile(r"^(?P<base>.+)_p[0-9A-Fa-f]{16}(?: \(\d+\))?(?:\..*)?$")
ANIMESTUDIO_HEX_HASH_NAME_RE = re.compile(r"^[0-9a-fA-F]{8,}$")
ANIMESTUDIO_CONVERT_PARSE_DEPENDENCIES = {
    # Animator FBX export starts from the linked GameObject hierarchy and only
    # emits geometry when Transform, renderer, Mesh, Material/Texture, Avatar,
    # controller, and clip dependencies are parsed alongside the Animator.
    "Animator": (
        "GameObject:Parse",
        "Transform:Parse",
        "RectTransform:Parse",
        "MeshFilter:Parse",
        "MeshRenderer:Parse",
        "SkinnedMeshRenderer:Parse",
        "Mesh:Parse",
        "Texture2D:Parse",
        "Material:Parse",
        "Avatar:Parse",
        "AnimatorController:Parse",
        "AnimatorOverrideController:Parse",
        "AnimationClip:Parse",
    ),
    # Sprite.GetImage resolves a backing texture directly or through a SpriteAtlas.
    # Parse these dependencies while keeping Sprite as the only export target.
    "Sprite": ("Texture2D:Parse", "SpriteAtlas:Parse"),
}
# Missing convert outputs must be explained by structured exporter warnings.
ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES = frozenset()
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
ANIMESTUDIO_EXPORT_ERROR_RE = re.compile(r"^\[Error\]\s+Export\s+(?P<asset>.+?)\s+error(?:\s+.*)?$")
ANIMESTUDIO_METADATA_ONLY_JSON_RE = re.compile(
    r"^\[Warning\]\s+Exporting MonoBehaviour (?P<asset>.+?) as metadata-only JSON after (?P<exception>[^:]+): (?P<reason>.+)$"
)
ANIMESTUDIO_PARTIAL_MONO_BEHAVIOUR_RE = re.compile(
    r"^\[Warning\]\s+Partially decoded MonoBehaviour (?P<asset>.+?) with (?P<decoder>.+?) after (?P<exception>[^:]+): (?P<reason>.+)$"
)
ANIMESTUDIO_PARTIAL_MONO_REASON_OFFSET_RE = re.compile(r"\s+at position 0x[0-9A-Fa-f]+\.?$")
ANIMESTUDIO_TEXTURE2D_NO_OUTPUT_RE = re.compile(r"^\[Warning\]\s+Texture2D no output (?P<fields>.*)$")
ANIMESTUDIO_MESH_NO_OUTPUT_RE = re.compile(r"^\[Warning\]\s+Mesh no output (?P<fields>.*)$")
ANIMESTUDIO_ANIMATOR_NO_OUTPUT_RE = re.compile(r"^\[Warning\]\s+Animator no output (?P<fields>.*)$")
ANIMESTUDIO_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ANIMESTUDIO_LOG_KEY_VALUE_RE = re.compile(
    r'(?P<key>[A-Za-z][A-Za-z0-9_]*)=(?:"(?P<quoted>(?:\\.|[^"\\])*)"|(?P<bare>\S*))'
)
ANIMESTUDIO_TEXTURE2D_NO_PAYLOAD_REASONS = frozenset({"font_placeholder_zero_size_texture"})
ANIMESTUDIO_MESH_EXPECTED_NO_OUTPUT_REASONS = frozenset({"zero_vertex_count"})
ANIMESTUDIO_ANIMATOR_EXPECTED_NO_OUTPUT_REASONS = frozenset({"no_mesh"})
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


@dataclass(frozen=True)
class AnimeStudioSecondaryExport:
    stage: str
    output_path: Path
    export_type: str
    types: tuple[str, ...]


class AnimeStudioCallPool:
    def __init__(self, max_workers: int):
        self.max_workers = max(1, max_workers)
        self._executor: ThreadPoolExecutor | None = None

    def __enter__(self) -> "AnimeStudioCallPool":
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None

    def submit_stage(self, **kwargs: Any):
        if self._executor is None:
            raise RuntimeError("AnimeStudioCallPool must be used as a context manager")
        return self._executor.submit(run_animestudio_stage, **kwargs)


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
    write_json(path, payload, compact=True)


def animestudio_asset_cache_path(output_root: Path) -> Path:
    return animestudio_work_dir(output_root) / "animestudio_asset_cache.json"


def animestudio_asset_status_path(output_root: Path, source: str, stage: str, type_name: str) -> Path:
    return animestudio_source_root(output_root, source) / "asset_status" / f"{stage}_{type_name}.json"


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
    write_json(path, payload, compact=True)


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


def normalized_container_leaf_stem(value: Any) -> str:
    text = str(value or "").replace("\\", "/").rstrip("/")
    if not text:
        return ""
    leaf = text.rsplit("/", 1)[-1]
    return leaf.rsplit(".", 1)[0] if "." in leaf else leaf


def animestudio_output_base_name(path: Any) -> str:
    if path is None:
        return ""
    name = Path(str(path)).name
    match = ANIMESTUDIO_OUTPUT_BASE_RE.match(name)
    if match:
        return match.group("base")
    return Path(name).stem


def animestudio_map_name_source_hint(value: Any) -> str:
    name = str(value or "").strip()
    if not name:
        return "map_name_empty"
    normalized = name.replace("\\", "/")
    if "/" in normalized or normalized.casefold().endswith(".ab"):
        return "map_name_bundle_path"
    if ANIMESTUDIO_HEX_HASH_NAME_RE.fullmatch(name):
        return "map_name_hex_hash"
    return "map_name_other"


def asset_output_name_mismatch_details(record: dict[str, Any]) -> dict[str, Any]:
    entry = record["entry"]
    actual_base = animestudio_output_base_name(record.get("output_path"))
    predicted_base = animestudio_output_base_name(record.get("predicted_output_path"))
    map_name = str(entry.get("Name") or "")
    container_leaf = normalized_container_leaf_stem(entry.get("Container"))
    fixed_container_leaf = fix_animestudio_file_name(container_leaf)
    map_case_normalized = bool(
        map_name
        and actual_base
        and actual_base.casefold() == map_name.casefold()
        and actual_base != map_name
    )
    container_leaf_case_normalized = bool(
        fixed_container_leaf
        and actual_base
        and actual_base.casefold() == fixed_container_leaf.casefold()
        and actual_base != fixed_container_leaf
    )
    case_normalized = map_case_normalized or container_leaf_case_normalized
    if record.get("output_is_marker"):
        reason = "marker_suffix"
    elif not map_name.strip():
        reason = "empty_map_name"
    elif map_case_normalized:
        reason = "case_normalization"
    elif actual_base and fixed_container_leaf and actual_base.casefold() == fixed_container_leaf.casefold():
        reason = "container_leaf"
    else:
        reason = "runtime_asset_name"
    return {
        "actual_output_base": actual_base,
        "predicted_output_base": predicted_base,
        "map_name": map_name,
        "container_leaf_stem": container_leaf,
        "name_mismatch_reason": reason,
        "name_source_hint": animestudio_map_name_source_hint(map_name),
        "case_normalized": case_normalized,
        "map_case_normalized": map_case_normalized,
        "container_leaf_case_normalized": container_leaf_case_normalized,
        "resolved_by_path_id": True,
    }


def format_animestudio_path_id(value: Any) -> str:
    return f"{int(value) & ((1 << 64) - 1):016X}"


def animestudio_convert_output_extension(type_name: str) -> str | None:
    return ANIMESTUDIO_CONVERT_OUTPUT_EXTENSIONS.get(type_name)


def animestudio_convert_output_suffixes(type_name: str) -> tuple[str, ...]:
    extension = animestudio_convert_output_extension(type_name)
    if extension is None:
        return ()
    return (extension, *ANIMESTUDIO_CONVERT_OUTPUT_MARKER_SUFFIXES.get(type_name, ()))


def animestudio_convert_output_marker_suffixes(type_name: str) -> tuple[str, ...]:
    return ANIMESTUDIO_CONVERT_OUTPUT_MARKER_SUFFIXES.get(type_name, ())


def animestudio_path_has_output_suffix(path: Path, type_name: str) -> bool:
    name = path.name.casefold()
    return any(name.endswith(suffix.casefold()) for suffix in animestudio_convert_output_suffixes(type_name))


def animestudio_marker_output_path(primary_path: Path, marker_suffix: str) -> Path:
    primary_suffix = "".join(primary_path.suffixes[-1:])
    if primary_suffix and marker_suffix.casefold().startswith(primary_suffix.casefold()):
        return primary_path.with_name(primary_path.name[: -len(primary_suffix)] + marker_suffix)
    return primary_path.with_name(primary_path.name + marker_suffix)


def animestudio_candidate_convert_output_paths(
    output_root: Path,
    source: str,
    stage: str,
    entry: dict[str, Any],
) -> tuple[Path, ...]:
    primary_path = predict_animestudio_convert_output_path(output_root, source, stage, entry)
    if primary_path is None:
        return ()
    type_name = str(entry.get("Type") or "")
    markers = tuple(
        animestudio_marker_output_path(primary_path, marker_suffix)
        for marker_suffix in animestudio_convert_output_marker_suffixes(type_name)
    )
    return (primary_path, *markers)


def animestudio_is_marker_output_path(path: Path, type_name: str) -> bool:
    name = path.name.casefold()
    return any(name.endswith(suffix.casefold()) for suffix in animestudio_convert_output_marker_suffixes(type_name))


def animestudio_convert_parse_dependencies(stage: str, export_type: str | None, type_spec: str | None) -> tuple[str, ...]:
    if stage != "convert_by_type" or export_type != "Convert" or type_spec is None:
        return ()
    return ANIMESTUDIO_CONVERT_PARSE_DEPENDENCIES.get(animestudio_type_name(type_spec), ())


def animestudio_type_specs_for_export(
    stage: str,
    export_type: str | None,
    type_specs: tuple[str, ...],
) -> tuple[str, ...]:
    expanded: list[str] = []
    for type_spec in type_specs:
        expanded.append(type_spec)
        expanded.extend(animestudio_convert_parse_dependencies(stage, export_type, type_spec))
    return ordered_unique(tuple(expanded))


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


def animestudio_output_path_id_suffix(path: Path, type_name: str) -> str | None:
    stem = path.name
    for output_suffix in sorted(animestudio_convert_output_suffixes(type_name), key=len, reverse=True):
        if stem.casefold().endswith(output_suffix.casefold()):
            stem = stem[: -len(output_suffix)]
            break
    else:
        return None
    try:
        suffix = stem.rsplit("_p", 1)[1]
    except IndexError:
        return None
    if len(suffix) != 16:
        return None
    try:
        int(suffix, 16)
    except ValueError:
        return None
    return suffix.upper()


def build_animestudio_output_path_id_index(
    output_root: Path,
    source: str,
    stage: str,
    type_name: str,
) -> dict[str, list[Path]]:
    type_dir = animestudio_stage_dir(output_root, source, stage) / type_name
    if not animestudio_convert_output_suffixes(type_name) or not type_dir.is_dir():
        return {}
    index: dict[str, list[Path]] = {}
    for path in type_dir.iterdir():
        if not path.is_file() or not animestudio_path_has_output_suffix(path, type_name):
            continue
        path_id_suffix = animestudio_output_path_id_suffix(path, type_name)
        if path_id_suffix is not None:
            index.setdefault(path_id_suffix, []).append(path)
    return index


def resolve_animestudio_convert_output_path(
    output_root: Path,
    source: str,
    stage: str,
    entry: dict[str, Any],
    output_path_id_index: dict[str, list[Path]],
) -> dict[str, Any]:
    predicted_path = predict_animestudio_convert_output_path(output_root, source, stage, entry)
    if predicted_path is None:
        return {
            "output_path": None,
            "predicted_output_path": None,
            "output_exists": False,
            "output_name_mismatch": False,
            "path_id_output_candidate_count": 0,
            "output_is_marker": False,
        }
    if predicted_path.is_file():
        return {
            "output_path": predicted_path,
            "predicted_output_path": predicted_path,
            "output_exists": True,
            "output_name_mismatch": False,
            "path_id_output_candidate_count": 1,
            "output_is_marker": False,
        }
    path_id = format_animestudio_path_id(entry.get("PathID") or 0)
    candidates = sorted(output_path_id_index.get(path_id, []))
    if len(candidates) == 1:
        output_is_marker = animestudio_is_marker_output_path(candidates[0], str(entry.get("Type") or ""))
        return {
            "output_path": candidates[0],
            "predicted_output_path": predicted_path,
            "output_exists": True,
            "output_name_mismatch": candidates[0] != predicted_path,
            "path_id_output_candidate_count": 1,
            "output_is_marker": output_is_marker,
        }
    return {
        "output_path": predicted_path,
        "predicted_output_path": predicted_path,
        "output_exists": False,
        "output_name_mismatch": False,
        "path_id_output_candidate_count": len(candidates),
        "output_is_marker": False,
    }


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
        "parse_dependencies": stage_signature.get("parse_dependencies"),
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
    write_json(filter_data_path, filter_items, compact=True)
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
    # Predicted outputs and dir entries are all under the resolved output_root, so
    # normcase(abspath) normalizes for comparison without a filesystem-touching
    # resolve() per path (matters for large Texture2D sets pruned every export).
    expected = {
        os.path.normcase(os.path.abspath(path))
        for entry in entries
        for path in animestudio_candidate_convert_output_paths(output_root, source, stage, entry)
    }
    removed = 0
    for path in type_dir.iterdir():
        if not path.is_file():
            continue
        if os.path.normcase(os.path.abspath(path)) in expected:
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
    seen: set[str] = set()
    for entry in entries:
        for path in animestudio_candidate_convert_output_paths(output_root, source, stage, entry):
            key = os.path.normcase(os.path.abspath(path))
            if key in seen:
                continue
            seen.add(key)
            if not path.is_file():
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
        if any(path.is_file() for path in animestudio_candidate_convert_output_paths(output_root, source, stage, entry))
    )



def asset_entry_ab_identity(entry: dict[str, Any]) -> dict[str, Any]:
    source_path = str(entry.get("Source") or "")
    source_file = Path(source_path) if source_path else None
    return {
        "source_path": source_path,
        "source_name": source_file.name if source_file is not None else "",
        "source_block": source_file.parent.name if source_file is not None else "",
        "offset": normalized_asset_offset(entry.get("Offset")),
    }


def asset_entry_ab_key(entry: dict[str, Any]) -> str:
    return stable_hash(asset_entry_ab_identity(entry))


def parse_log_int(value: Any) -> int | None:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return None


def normalized_log_int(value: Any) -> int:
    parsed = parse_log_int(value)
    return parsed if parsed is not None else -1


def normalized_source_leaf(value: Any) -> str:
    source = str(value or "").replace("\\", "/").strip()
    return source.rsplit("/", 1)[-1].casefold() if source else ""


def texture2d_no_payload_log_indexes(log_issues: dict[str, Any] | None) -> tuple[set[tuple[int, int, str]], set[tuple[int, int]]]:
    exact_keys: set[tuple[int, int, str]] = set()
    fallback_keys: set[tuple[int, int]] = set()
    for sample in (log_issues or {}).get("texture2d_no_output_records") or (log_issues or {}).get("texture2d_no_output_samples") or []:
        if sample.get("reason") not in ANIMESTUDIO_TEXTURE2D_NO_PAYLOAD_REASONS:
            continue
        path_id = parse_log_int(sample.get("PathID"))
        source_offset = parse_log_int(sample.get("SourceOffset"))
        if path_id is None or source_offset is None or source_offset < 0:
            continue
        source_names = {
            normalized_source_leaf(sample.get("SourceOriginalPath")),
            normalized_source_leaf(sample.get("SourceFile")),
        }
        source_names.discard("")
        if source_names:
            for source_name in source_names:
                exact_keys.add((path_id, source_offset, source_name))
        else:
            fallback_keys.add((path_id, source_offset))
    return exact_keys, fallback_keys


def texture2d_record_matches_no_payload_log(
    record: dict[str, Any],
    exact_keys: set[tuple[int, int, str]],
    fallback_keys: set[tuple[int, int]],
) -> bool:
    entry = record["entry"]
    path_id = parse_log_int(entry.get("PathID"))
    source_offset = normalized_asset_offset(entry.get("Offset"))
    if path_id is None or source_offset < 0:
        return False
    source_leaf = normalized_source_leaf(entry.get("Source"))
    if source_leaf and (path_id, source_offset, source_leaf) in exact_keys:
        return True
    return (path_id, source_offset) in fallback_keys


def mesh_expected_no_output_log_indexes(log_issues: dict[str, Any] | None) -> tuple[set[tuple[int, int, str]], set[tuple[int, int]]]:
    exact_keys: set[tuple[int, int, str]] = set()
    fallback_keys: set[tuple[int, int]] = set()
    for sample in (log_issues or {}).get("mesh_no_output_records") or (log_issues or {}).get("mesh_no_output_samples") or []:
        if sample.get("reason") not in ANIMESTUDIO_MESH_EXPECTED_NO_OUTPUT_REASONS:
            continue
        path_id = parse_log_int(sample.get("PathID"))
        source_offset = parse_log_int(sample.get("SourceOffset"))
        if path_id is None or source_offset is None or source_offset < 0:
            continue
        source_names = {
            normalized_source_leaf(sample.get("SourceOriginalPath")),
            normalized_source_leaf(sample.get("SourceFile")),
        }
        source_names.discard("")
        if source_names:
            for source_name in source_names:
                exact_keys.add((path_id, source_offset, source_name))
        else:
            fallback_keys.add((path_id, source_offset))
    return exact_keys, fallback_keys


def mesh_record_matches_expected_no_output_log(
    record: dict[str, Any],
    exact_keys: set[tuple[int, int, str]],
    fallback_keys: set[tuple[int, int]],
) -> bool:
    entry = record["entry"]
    path_id = parse_log_int(entry.get("PathID"))
    source_offset = normalized_asset_offset(entry.get("Offset"))
    if path_id is None or source_offset < 0:
        return False
    source_leaf = normalized_source_leaf(entry.get("Source"))
    if source_leaf and (path_id, source_offset, source_leaf) in exact_keys:
        return True
    return (path_id, source_offset) in fallback_keys


def asset_output_record_sample(record: dict[str, Any]) -> dict[str, Any]:
    entry = record["entry"]
    sample = {
        "name": entry.get("Name"),
        "path_id": entry.get("PathID"),
        "type": entry.get("Type"),
        "container": entry.get("Container"),
        "hash": entry.get("Hash"),
        "output_path": str(record["output_path"]) if record.get("output_path") is not None else None,
        "output_exists": bool(record.get("output_exists")),
    }
    predicted_output_path = record.get("predicted_output_path")
    if record.get("output_name_mismatch") and predicted_output_path is not None:
        sample["predicted_output_path"] = str(predicted_output_path)
        sample["output_name_mismatch"] = True
        sample.update(asset_output_name_mismatch_details(record))
    if record.get("output_is_marker"):
        sample["output_marker"] = True
    candidate_count = int(record.get("path_id_output_candidate_count") or 0)
    if candidate_count > 1:
        sample["path_id_output_candidate_count"] = candidate_count
    return sample


def asset_output_collision_identity(record: dict[str, Any], *, include_hash: bool) -> tuple[str, Any, str, str]:
    entry = record["entry"]
    parsed_path_id = parse_log_int(entry.get("PathID"))
    path_id: Any = parsed_path_id if parsed_path_id is not None else str(entry.get("PathID") or "")
    digest = str(entry.get("Hash") or "").casefold() if include_hash else ""
    return (
        str(entry.get("Type") or ""),
        path_id,
        str(entry.get("Name") or ""),
        digest,
    )


def classify_output_path_collision(records: list[dict[str, Any]]) -> str:
    source_group_count = len({record["ab_key"] for record in records})
    if source_group_count <= 1:
        return "duplicate_output_path"
    identities = {asset_output_collision_identity(record, include_hash=True) for record in records}
    if len(identities) == 1:
        return "shared_output_reference"
    identities_without_hash = {
        asset_output_collision_identity(record, include_hash=False)
        for record in records
    }
    if len(identities_without_hash) == 1:
        if {str(record["entry"].get("Type") or "") for record in records} == {"Texture2D"}:
            return "same_asset_id_output_reference"
        return "raw_hash_output_collision"
    return "identity_output_collision"


def build_animestudio_asset_output_status(
    output_root: Path,
    source: str,
    stage: str,
    type_name: str,
    entries: list[dict[str, Any]],
    *,
    missing_outputs_allowed: bool,
    log_issues: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_records: list[dict[str, Any]] = []
    records_by_output_path: dict[str, list[dict[str, Any]]] = {}
    records_by_ab: dict[str, list[dict[str, Any]]] = {}
    ab_identities: dict[str, dict[str, Any]] = {}
    output_path_id_index = build_animestudio_output_path_id_index(output_root, source, stage, type_name)

    for entry in entries:
        resolved_output = resolve_animestudio_convert_output_path(
            output_root,
            source,
            stage,
            entry,
            output_path_id_index,
        )
        output_path = resolved_output["output_path"]
        output_key = os.path.normcase(os.path.abspath(output_path)) if output_path is not None else ""
        output_exists = bool(resolved_output["output_exists"])
        ab_key = asset_entry_ab_key(entry)
        record = {
            "entry": entry,
            "ab_key": ab_key,
            "output_path": output_path,
            "output_key": output_key,
            "output_exists": output_exists,
            "predicted_output_path": resolved_output.get("predicted_output_path"),
            "output_name_mismatch": bool(resolved_output.get("output_name_mismatch")),
            "output_is_marker": bool(resolved_output.get("output_is_marker")),
            "path_id_output_candidate_count": int(resolved_output.get("path_id_output_candidate_count") or 0),
        }
        output_records.append(record)
        records_by_ab.setdefault(ab_key, []).append(record)
        ab_identities.setdefault(ab_key, asset_entry_ab_identity(entry))
        if output_key:
            records_by_output_path.setdefault(output_key, []).append(record)

    duplicate_output_keys = {
        output_key for output_key, records in records_by_output_path.items() if len(records) > 1
    }
    cross_ab_output_keys = {
        output_key
        for output_key, records in records_by_output_path.items()
        if len({record["ab_key"] for record in records}) > 1
    }
    output_collision_kind_by_key = {
        output_key: classify_output_path_collision(records)
        for output_key, records in records_by_output_path.items()
        if len(records) > 1
    }
    shared_output_reference_keys = {
        output_key
        for output_key, kind in output_collision_kind_by_key.items()
        if kind == "shared_output_reference"
    }
    same_asset_id_output_reference_keys = {
        output_key
        for output_key, kind in output_collision_kind_by_key.items()
        if kind == "same_asset_id_output_reference"
    }
    raw_hash_output_collision_keys = {
        output_key
        for output_key, kind in output_collision_kind_by_key.items()
        if kind == "raw_hash_output_collision"
    }
    identity_output_collision_keys = {
        output_key
        for output_key, kind in output_collision_kind_by_key.items()
        if kind == "identity_output_collision"
    }
    uncertain_output_collision_keys = raw_hash_output_collision_keys | identity_output_collision_keys
    uncertain_duplicate_output_keys = {
        output_key
        for output_key, kind in output_collision_kind_by_key.items()
        if kind == "duplicate_output_path"
    }
    missing_records = [record for record in output_records if not record["output_exists"]]
    missing_output_keys = {record["output_key"] for record in missing_records if record["output_key"]}
    marker_output_records = [record for record in output_records if record.get("output_is_marker")]
    name_mismatch_records = [record for record in output_records if record.get("output_name_mismatch")]
    alternate_name_records = [
        record for record in name_mismatch_records
        if not record.get("output_is_marker")
    ]
    alternate_name_reason_counts: dict[str, int] = {}
    alternate_name_source_hint_counts: dict[str, int] = {}
    alternate_name_case_normalized_count = 0
    for record in alternate_name_records:
        details = asset_output_name_mismatch_details(record)
        reason = str(details.get("name_mismatch_reason") or "unknown")
        source_hint = str(details.get("name_source_hint") or "unknown")
        alternate_name_reason_counts[reason] = alternate_name_reason_counts.get(reason, 0) + 1
        alternate_name_source_hint_counts[source_hint] = alternate_name_source_hint_counts.get(source_hint, 0) + 1
        if details.get("case_normalized"):
            alternate_name_case_normalized_count += 1
    texture2d_no_output_count = int((log_issues or {}).get("texture2d_no_output_count") or 0)
    texture2d_no_payload_count = int((log_issues or {}).get("texture2d_no_payload_count") or 0)
    texture2d_decode_failed_count = int((log_issues or {}).get("texture2d_decode_failed_count") or 0)
    texture2d_no_output_samples = list((log_issues or {}).get("texture2d_no_output_samples") or [])[:ANIMESTUDIO_LOG_SAMPLE_LIMIT]
    mesh_no_output_count = int((log_issues or {}).get("mesh_no_output_count") or 0)
    mesh_expected_no_output_count = int((log_issues or {}).get("mesh_expected_no_output_count") or 0)
    mesh_suspicious_no_output_count = int((log_issues or {}).get("mesh_suspicious_no_output_count") or 0)
    mesh_no_output_samples = list((log_issues or {}).get("mesh_no_output_samples") or [])[:ANIMESTUDIO_LOG_SAMPLE_LIMIT]
    animator_no_output_count = int((log_issues or {}).get("animator_no_output_count") or 0)
    animator_no_mesh_count = int((log_issues or {}).get("animator_no_mesh_count") or 0)
    animator_suspicious_no_output_count = int((log_issues or {}).get("animator_suspicious_no_output_count") or 0)
    animator_no_output_samples = list((log_issues or {}).get("animator_no_output_samples") or [])[:ANIMESTUDIO_LOG_SAMPLE_LIMIT]
    texture2d_no_payload_record_ids: set[int] = set()
    if type_name == "Texture2D" and missing_records and texture2d_no_payload_count:
        exact_log_keys, fallback_log_keys = texture2d_no_payload_log_indexes(log_issues)
        texture2d_no_payload_record_ids = {
            id(record)
            for record in missing_records
            if texture2d_record_matches_no_payload_log(record, exact_log_keys, fallback_log_keys)
        }
    mesh_expected_no_output_record_ids: set[int] = set()
    if type_name == "Mesh" and missing_records and mesh_expected_no_output_count:
        exact_log_keys, fallback_log_keys = mesh_expected_no_output_log_indexes(log_issues)
        mesh_expected_no_output_record_ids = {
            id(record)
            for record in missing_records
            if mesh_record_matches_expected_no_output_log(record, exact_log_keys, fallback_log_keys)
        }
    classified_no_payload_missing_output_count = 0
    if type_name == "Texture2D":
        classified_no_payload_missing_output_count = len(texture2d_no_payload_record_ids)
    classified_mesh_expected_missing_output_count = 0
    if type_name == "Mesh":
        classified_mesh_expected_missing_output_count = len(mesh_expected_no_output_record_ids)
    allowed_missing_output_count = (
        len(missing_records)
        if missing_outputs_allowed
        else classified_no_payload_missing_output_count + classified_mesh_expected_missing_output_count
    )
    suspicious_missing_output_count = max(0, len(missing_records) - allowed_missing_output_count)
    if type_name == "Texture2D" and texture2d_decode_failed_count:
        suspicious_missing_output_count = max(suspicious_missing_output_count, texture2d_decode_failed_count)
    if type_name == "Mesh" and mesh_suspicious_no_output_count:
        suspicious_missing_output_count = max(suspicious_missing_output_count, mesh_suspicious_no_output_count)
    output_path_collision_samples: list[dict[str, Any]] = []
    for output_key in sorted(cross_ab_output_keys)[:20]:
        records = records_by_output_path[output_key]
        output_path = records[0].get("output_path")
        output_path_collision_samples.append(
            {
                "output_path": str(output_path) if output_path is not None else None,
                "collision_kind": output_collision_kind_by_key.get(output_key),
                "entry_count": len(records),
                "source_group_count": len({record["ab_key"] for record in records}),
                "samples": [asset_output_record_sample(record) for record in records[:5]],
            }
        )

    status_counts: dict[str, int] = {}
    groups: list[dict[str, Any]] = []
    for ab_key, records in sorted(
        records_by_ab.items(),
        key=lambda item: (
            str(ab_identities[item[0]].get("source_path") or "").casefold(),
            int(ab_identities[item[0]].get("offset") or -1),
        ),
    ):
        entry_count = len(records)
        output_entry_count = sum(1 for record in records if record["output_exists"])
        missing_entry_count = entry_count - output_entry_count
        duplicate_entry_count = sum(1 for record in records if record["output_key"] in duplicate_output_keys)
        uncertain_duplicate_entry_count = sum(
            1 for record in records if record["output_key"] in uncertain_duplicate_output_keys
        )
        cross_ab_collision_entry_count = sum(1 for record in records if record["output_key"] in cross_ab_output_keys)
        shared_reference_entry_count = sum(
            1 for record in records if record["output_key"] in shared_output_reference_keys
        )
        same_asset_id_reference_entry_count = sum(
            1 for record in records if record["output_key"] in same_asset_id_output_reference_keys
        )
        raw_hash_collision_entry_count = sum(
            1 for record in records if record["output_key"] in raw_hash_output_collision_keys
        )
        identity_collision_entry_count = sum(
            1 for record in records if record["output_key"] in identity_output_collision_keys
        )
        uncertain_collision_entry_count = sum(
            1 for record in records if record["output_key"] in uncertain_output_collision_keys
        )
        allowed_missing_entry_count = 0
        if missing_outputs_allowed:
            allowed_missing_entry_count = missing_entry_count
        elif type_name == "Texture2D":
            allowed_missing_entry_count = sum(
                1
                for record in records
                if not record["output_exists"] and id(record) in texture2d_no_payload_record_ids
            )
        elif type_name == "Mesh":
            allowed_missing_entry_count = sum(
                1
                for record in records
                if not record["output_exists"] and id(record) in mesh_expected_no_output_record_ids
            )
        suspicious_missing_entry_count = missing_entry_count - allowed_missing_entry_count
        if suspicious_missing_entry_count:
            status = "dirty_missing_output"
        elif missing_entry_count:
            status = "allowed_missing_output"
        elif uncertain_collision_entry_count:
            status = "uncertain_output_collision"
        elif uncertain_duplicate_entry_count:
            status = "uncertain_duplicate_output_path"
        else:
            status = "clean_outputs"
        status_counts[status] = status_counts.get(status, 0) + 1
        groups.append(
            {
                "status": status,
                **ab_identities[ab_key],
                "entry_count": entry_count,
                "unique_output_path_count": len({record["output_key"] for record in records if record["output_key"]}),
                "output_entry_count": output_entry_count,
                "missing_entry_count": missing_entry_count,
                "allowed_missing_entry_count": allowed_missing_entry_count,
                "suspicious_missing_entry_count": suspicious_missing_entry_count,
                "duplicate_output_entry_count": duplicate_entry_count,
                "uncertain_duplicate_output_entry_count": uncertain_duplicate_entry_count,
                "cross_ab_output_collision_entry_count": cross_ab_collision_entry_count,
                "shared_output_reference_entry_count": shared_reference_entry_count,
                "same_asset_id_output_reference_entry_count": same_asset_id_reference_entry_count,
                "raw_hash_output_collision_entry_count": raw_hash_collision_entry_count,
                "identity_output_collision_entry_count": identity_collision_entry_count,
                "uncertain_output_collision_entry_count": uncertain_collision_entry_count,
                "missing_output_samples": [asset_output_record_sample(record) for record in records if not record["output_exists"]][:5],
                "output_collision_samples": [
                    asset_output_record_sample(record)
                    for record in records
                    if record["output_key"] in uncertain_output_collision_keys
                ][:5],
                "shared_output_reference_samples": [
                    asset_output_record_sample(record)
                    for record in records
                    if record["output_key"] in shared_output_reference_keys
                ][:5],
                "same_asset_id_output_reference_samples": [
                    asset_output_record_sample(record)
                    for record in records
                    if record["output_key"] in same_asset_id_output_reference_keys
                ][:5],
            }
        )

    type_dir = animestudio_stage_dir(output_root, source, stage) / type_name
    actual_output_file_count = sum(1 for path in type_dir.iterdir() if path.is_file()) if type_dir.is_dir() else 0
    export_error_count = int((log_issues or {}).get("export_error_count") or 0)
    summary = {
        "source": source,
        "stage": stage,
        "type": type_name,
        "matched_entry_count": len(entries),
        "source_group_count": len(groups),
        "status_counts": status_counts,
        "clean_source_group_count": status_counts.get("clean_outputs", 0),
        "dirty_source_group_count": len(groups) - status_counts.get("clean_outputs", 0),
        "output_entry_count": sum(1 for record in output_records if record["output_exists"]),
        "unique_output_path_count": len(records_by_output_path),
        "output_unique_path_count": sum(
            1 for records in records_by_output_path.values() if any(record["output_exists"] for record in records)
        ),
        "actual_output_file_count": actual_output_file_count,
        "marker_output_count": len(marker_output_records),
        "marker_output_samples": [asset_output_record_sample(record) for record in marker_output_records[:20]],
        "name_mismatch_output_count": len(name_mismatch_records),
        "name_mismatch_output_samples": [asset_output_record_sample(record) for record in name_mismatch_records[:20]],
        "alternate_name_output_count": len(alternate_name_records),
        "alternate_name_reason_counts": dict(sorted(alternate_name_reason_counts.items())),
        "alternate_name_source_hint_counts": dict(sorted(alternate_name_source_hint_counts.items())),
        "alternate_name_case_normalized_count": alternate_name_case_normalized_count,
        "alternate_name_output_samples": [asset_output_record_sample(record) for record in alternate_name_records[:20]],
        "missing_output_count": len(missing_records),
        "missing_unique_output_count": len(missing_output_keys),
        "allowed_missing_output_count": allowed_missing_output_count,
        "suspicious_missing_output_count": suspicious_missing_output_count,
        "classified_no_payload_missing_output_count": classified_no_payload_missing_output_count,
        "classified_mesh_expected_missing_output_count": classified_mesh_expected_missing_output_count,
        "texture2d_no_output_count": texture2d_no_output_count,
        "texture2d_no_payload_count": texture2d_no_payload_count,
        "texture2d_decode_failed_count": texture2d_decode_failed_count,
        "texture2d_no_output_samples": texture2d_no_output_samples,
        "mesh_no_output_count": mesh_no_output_count,
        "mesh_expected_no_output_count": mesh_expected_no_output_count,
        "mesh_suspicious_no_output_count": mesh_suspicious_no_output_count,
        "mesh_no_output_samples": mesh_no_output_samples,
        "animator_no_output_count": animator_no_output_count,
        "animator_no_mesh_count": animator_no_mesh_count,
        "animator_suspicious_no_output_count": animator_suspicious_no_output_count,
        "animator_no_output_samples": animator_no_output_samples,
        "duplicate_output_path_group_count": len(duplicate_output_keys),
        "duplicate_output_entry_count": sum(len(records_by_output_path[key]) - 1 for key in duplicate_output_keys),
        "uncertain_duplicate_output_path_group_count": len(uncertain_duplicate_output_keys),
        "uncertain_duplicate_output_entry_count": sum(
            len(records_by_output_path[key])
            for key in uncertain_duplicate_output_keys
        ),
        "cross_ab_output_collision_group_count": len(cross_ab_output_keys),
        "cross_ab_output_collision_entry_count": sum(len(records_by_output_path[key]) for key in cross_ab_output_keys),
        "shared_output_reference_group_count": len(shared_output_reference_keys),
        "shared_output_reference_entry_count": sum(
            len(records_by_output_path[key])
            for key in shared_output_reference_keys
        ),
        "same_asset_id_output_reference_group_count": len(same_asset_id_output_reference_keys),
        "same_asset_id_output_reference_entry_count": sum(
            len(records_by_output_path[key])
            for key in same_asset_id_output_reference_keys
        ),
        "raw_hash_output_collision_group_count": len(raw_hash_output_collision_keys),
        "raw_hash_output_collision_entry_count": sum(
            len(records_by_output_path[key])
            for key in raw_hash_output_collision_keys
        ),
        "identity_output_collision_group_count": len(identity_output_collision_keys),
        "identity_output_collision_entry_count": sum(
            len(records_by_output_path[key])
            for key in identity_output_collision_keys
        ),
        "uncertain_output_collision_group_count": len(uncertain_output_collision_keys),
        "uncertain_output_collision_entry_count": sum(
            len(records_by_output_path[key])
            for key in uncertain_output_collision_keys
        ),
        "unmapped_export_error_count": export_error_count,
    }
    return {
        "schema_version": 1,
        "generated_at_epoch": int(time.time()),
        "summary": summary,
        "output_path_collision_samples": output_path_collision_samples,
        "source_groups": groups,
    }


def write_animestudio_asset_status_manifest(
    output_root: Path,
    source: str,
    stage: str,
    type_name: str,
    entries: list[dict[str, Any]],
    *,
    missing_outputs_allowed: bool,
    log_issues: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = animestudio_asset_status_path(output_root, source, stage, type_name)
    status = build_animestudio_asset_output_status(
        output_root=output_root,
        source=source,
        stage=stage,
        type_name=type_name,
        entries=entries,
        missing_outputs_allowed=missing_outputs_allowed,
        log_issues=log_issues,
    )
    status["summary"]["manifest_path"] = str(path)
    ensure_dir(path.parent)
    write_json(path, status, compact=True)
    return status["summary"]


def write_animestudio_report_only_asset_statuses(
    output_root: Path,
    source: str,
    stage: str,
    plan: dict[str, Any],
    *,
    item_names: set[str] | None = None,
    skip_existing_types: bool = False,
) -> list[dict[str, Any]]:
    options = plan.get("options") or {}
    if stage != "convert_by_type" or options.get("export_type") != "Convert":
        return []
    if not options.get("asset_map_filter"):
        return []
    map_name = options.get("map_name")
    if not map_name:
        return []
    map_json = normalize_asset_map_path(map_name)
    if not map_json.exists():
        log(f"  animestudio report-only status {stage} for {source}: missing JSON map {map_json}")
        return []

    started = time.time()
    map_entries_cache = plan.setdefault("_asset_map_entries_cache", {})
    map_entries_key = str(map_json)
    map_entries = map_entries_cache.get(map_entries_key)
    if map_entries is None:
        map_entries = load_animestudio_asset_map_entries(map_json)
        map_entries_cache[map_entries_key] = map_entries

    written: list[dict[str, Any]] = []
    existing_types = {
        str(asset_info.get("type") or "")
        for asset_info in plan.get("asset_caches", [])
        if isinstance(asset_info, dict)
    }
    for item in plan.get("items", []):
        item_name = str(item.get("item_name") or "")
        if item_names is not None and item_name not in item_names:
            continue
        type_spec = item.get("type_spec")
        if type_spec is None:
            continue
        type_name = animestudio_type_name(type_spec)
        if skip_existing_types and type_name in existing_types:
            continue
        if not animestudio_asset_cache_supported(stage, options, type_name):
            continue
        matched_entries = dedupe_asset_entries(
            filter_animestudio_asset_map_entries(
                map_path=map_json,
                type_name=type_name,
                names=options.get("names"),
                containers=options.get("containers"),
                entries=map_entries,
            )
        )
        missing_outputs_allowed = type_name in ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES
        status_summary = write_animestudio_asset_status_manifest(
            output_root=output_root,
            source=source,
            stage=stage,
            type_name=type_name,
            entries=matched_entries,
            missing_outputs_allowed=missing_outputs_allowed,
        )
        asset_info = {
            "enabled": False,
            "report_only": True,
            "cache_path": None,
            "map_json": str(map_json),
            "type": type_name,
            "output_extension": animestudio_convert_output_extension(type_name),
            "matched_entry_count": len(matched_entries),
            "cached_entry_count": 0,
            "pending_entry_count": 0,
            "shard_count": 0,
            "prepare_seconds": round(time.time() - started, 3),
            "export_error_count": 0,
        }
        for key in (
            "manifest_path",
            "output_entry_count",
            "unique_output_path_count",
            "output_unique_path_count",
            "actual_output_file_count",
            "marker_output_count",
            "name_mismatch_output_count",
            "alternate_name_output_count",
            "alternate_name_reason_counts",
            "alternate_name_source_hint_counts",
            "alternate_name_case_normalized_count",
            "missing_output_count",
            "missing_unique_output_count",
            "allowed_missing_output_count",
            "duplicate_output_path_group_count",
            "duplicate_output_entry_count",
            "uncertain_duplicate_output_path_group_count",
            "uncertain_duplicate_output_entry_count",
            "cross_ab_output_collision_group_count",
            "cross_ab_output_collision_entry_count",
            "shared_output_reference_group_count",
            "shared_output_reference_entry_count",
            "same_asset_id_output_reference_group_count",
            "same_asset_id_output_reference_entry_count",
            "raw_hash_output_collision_group_count",
            "raw_hash_output_collision_entry_count",
            "identity_output_collision_group_count",
            "identity_output_collision_entry_count",
            "uncertain_output_collision_group_count",
            "uncertain_output_collision_entry_count",
            "source_group_count",
            "clean_source_group_count",
            "dirty_source_group_count",
            "unmapped_export_error_count",
        ):
            asset_info[key] = status_summary.get(key)
        plan.setdefault("asset_caches", []).append(asset_info)
        existing_types.add(type_name)
        plan.setdefault("item_file_counts", {})[type_name] = int(status_summary.get("actual_output_file_count") or 0)
        written.append(asset_info)
        log(
            f"  animestudio report-only status {stage}:{type_name} for {source}: "
            f"matched={asset_info['matched_entry_count']} "
            f"outputs={asset_info['output_entry_count']} "
            f"missing={asset_info['missing_output_count']} "
            f"manifest={asset_info['manifest_path']}"
        )

    if written:
        plan["asset_cache"] = written[-1]
    return written


def animestudio_type_name(type_spec: str | None) -> str:
    if not type_spec:
        return ANIMESTUDIO_MANIFEST_MAP_LABEL
    return str(type_spec).split(":", 1)[0]


def animestudio_known_asset_type_names() -> set[str]:
    specs = (
        ANIMESTUDIO_FULL_CONVERT_TYPES
        + ANIMESTUDIO_DEBUG_CONVERT_TYPES
        + ANIMESTUDIO_WEBUI_CONVERT_TYPES
        + ANIMESTUDIO_FULL_JSON_TYPES
        + ANIMESTUDIO_DEBUG_JSON_TYPES
        + ANIMESTUDIO_WEBUI_JSON_TYPES
    )
    return {animestudio_type_name(spec).lower() for spec in specs}


def normalize_animestudio_asset_type_filter(values: tuple[str, ...] | list[str]) -> set[str]:
    selected = {
        animestudio_type_name(value).lower()
        for value in values
        if str(value or "").strip()
    }
    known = animestudio_known_asset_type_names()
    unknown = sorted(selected - known)
    if unknown:
        known_text = ", ".join(sorted(known))
        raise SystemExit(
            f"Unknown --animestudio-asset-types value(s): {', '.join(unknown)}. "
            f"Known asset type names: {known_text}"
        )
    return selected


def apply_animestudio_asset_type_filter(
    stage_options: dict[str, dict[str, Any]],
    selected_types: set[str],
) -> None:
    if not selected_types:
        return
    for stage in ("convert_by_type", "json_by_type"):
        options = stage_options.get(stage)
        if not options:
            continue
        filtered_types = tuple(
            type_spec
            for type_spec in options.get("types", ())
            if animestudio_type_name(type_spec).lower() in selected_types
        )
        options["types"] = filtered_types
        options["asset_type_filter"] = sorted(selected_types)
        if not filtered_types:
            options["asset_map_filter"] = False
            options["webui_asset_filter"] = False


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
    else:
        if asset_mode == "webui":
            asset_json_types = ANIMESTUDIO_WEBUI_JSON_TYPES
            convert_types = ANIMESTUDIO_WEBUI_CONVERT_TYPES
        elif asset_mode == "debug":
            asset_json_types = ANIMESTUDIO_DEBUG_JSON_TYPES
            convert_types = ANIMESTUDIO_DEBUG_CONVERT_TYPES
        else:
            asset_json_types = ANIMESTUDIO_FULL_JSON_TYPES
            convert_types = ANIMESTUDIO_FULL_CONVERT_TYPES
        if scope == "all":
            json_types = ordered_unique(ANIMESTUDIO_STORY_JSON_TYPES + asset_json_types)
        else:
            json_types = asset_json_types
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
            # Story TextAssets include DialogTree sources that are not present in
            # the generated asset map.  A combined Story+asset export must keep
            # the JSON load broad just like the Story-only path; otherwise the
            # build silently loses authored option anchors and branch routes.
            "asset_map_filter": scope == "assets" and bool(json_types),
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
    dependencies = animestudio_convert_parse_dependencies(stage, options.get("export_type"), type_spec)
    if dependencies:
        signature["parse_dependencies"] = list(dependencies)
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
) -> dict[str, Any]:
    # The cross-run AnimeStudio cache has been removed: every selected item is
    # always (re)exported, so planning is just an enumeration. No manifest
    # lookups, no per-item cache_key hashing, and no planning-time count_files
    # walks (output counts are gathered once at summary time instead).
    items: list[dict[str, Any]] = []
    selected_items: list[str] = []
    run_items: list[str] = []
    type_specs_to_run: list[str] = []

    for type_spec, item_name in animestudio_stage_items(stage, options.get("types", ())):
        selected_items.append(item_name)
        items.append(
            {
                "type_spec": type_spec,
                "item_name": item_name,
                "stage_signature": build_animestudio_stage_signature(stage, options, type_spec),
                "cache_valid": False,
                "refresh_forced": False,
            }
        )
        run_items.append(item_name)
        if type_spec is not None:
            type_specs_to_run.append(type_spec)

    return {
        "stage": stage,
        "options": options,
        "items": items,
        "selected_items": selected_items,
        "cached_items": [],
        "run_items": run_items,
        "forced_refresh_items": [],
        "item_file_counts": {},
        "type_specs_to_run": tuple(type_specs_to_run),
        "should_run": bool(run_items),
        "cache_state": "no_cache",
    }


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
        "--structured-dumper",
        dest="structured_dumper",
        type=Path,
        default=DEFAULT_STRUCTURED_DUMPER,
        help="Path to AnimeStudio CLI for VFS structured exports",
    )
    parser.add_argument(
        "--structured-dump-mode",
        choices=STRUCTURED_DUMP_MODES,
        default="webui",
        help=(
            "`webui` and `full` dump only WebUI-required structured VFS data and skip audio PCK/media files. "
            "`debug` preserves the old broad dump of every dumpable block type."
        ),
    )
    parser.add_argument(
        "--fluffy",
        dest="structured_dumper",
        help=argparse.SUPPRESS,
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
            "`script-first` tries DummyDll script schemas when available and otherwise falls back."
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
            "`assets` uses --animestudio-asset-mode to choose WebUI-focused, full, or debug assets. "
            "`all` combines story JSON with the selected asset mode."
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
        "--animestudio-asset-types",
        nargs="+",
        default=(),
        help=(
            "Limit asset-scope AnimeStudio convert/json stages to one or more Unity asset type names, "
            "for example Sprite, Texture2D, Mesh, Animator, Material, Shader, or AnimationClip. "
            "Maps still run when selected."
        ),
    )
    parser.add_argument(
        "--animestudio-refresh-types",
        nargs="+",
        default=(),
        help=(
            "Deprecated no-op. The cross-run AnimeStudio cache has been removed, so "
            "every selected item is always re-exported and there is nothing to force-refresh."
        ),
    )
    parser.add_argument(
        "--animestudio-jobs",
        type=int,
        default=ANIMESTUDIO_DEFAULT_JOBS,
        help=(
            "Maximum parallel AnimeStudio CLI processes in the shared worker pool. "
            f"The default {ANIMESTUDIO_DEFAULT_JOBS} lets pooled shards/types share workers; "
            "lower it to limit peak memory."
        ),
    )
    parser.add_argument(
        "--animestudio-shards",
        type=int,
        default=ANIMESTUDIO_DEFAULT_SHARDS,
        help=(
            "Split each map-filtered deterministic asset type into this many filter_data shards. "
            f"The default {ANIMESTUDIO_DEFAULT_SHARDS} keeps per-process asset slices small; "
            f"the shared --animestudio-jobs pool consumes those shards. "
            "Use 0 to shard by --animestudio-jobs."
        ),
    )
    parser.add_argument(
        "--animestudio-type-job-mode",
        choices=("auto", "parallel", "merged"),
        default="auto",
        help=(
            "How to run non-sharded AnimeStudio type jobs. `auto` merges map-filtered "
            "json_by_type jobs but runs broad Story JSON types sequentially in isolated "
            "processes; convert_by_type stays on the pooled sharded path. `parallel` "
            "preserves the old concurrent one-process-per-type behavior. "
            "`merged` combines every non-sharded type set."
        ),
    )
    parser.add_argument(
        "--animestudio-stage-merge-mode",
        choices=ANIMESTUDIO_STAGE_MERGE_MODES,
        default="auto",
        help=(
            "Controls guarded same-process merging across AnimeStudio stages. "
            "`auto` preserves the current split Convert/JSON stage behavior, `never` disables "
            "the merge path explicitly, and `aggressive` runs a Convert primary export with "
            "a JSON secondary export only when the CLI advertises the secondary-export flags."
        ),
    )
    parser.add_argument(
        "--no-animestudio-asset-cache",
        action="store_true",
        help="Deprecated no-op. The AnimeStudio conversion cache has been removed; every run re-exports.",
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
    parser.add_argument(
        "--report-runs-to-keep",
        type=int,
        default=DEFAULT_REPORT_RUNS_TO_KEEP,
        help=(
            "Number of timestamped export report runs to retain (default: "
            f"{DEFAULT_REPORT_RUNS_TO_KEEP}; 0 disables pruning)."
        ),
    )
    args = parser.parse_args()
    if args.report_runs_to_keep < 0:
        parser.error("--report-runs-to-keep must be 0 or greater")
    return args


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any, *, compact: bool = False) -> None:
    # Human-facing reports keep indent=2; large machine-only caches/filters use
    # `compact` to cut serialized size, peak string memory, and bytes written.
    if compact:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")


def log(message: str) -> None:
    print(f"[export_full] {message}", flush=True)


def current_report_run_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def prune_export_report_runs(runs_root: Path, current_run: Path, runs_to_keep: int) -> None:
    if runs_to_keep < 1 or not runs_root.exists():
        return
    current_resolved = current_run.resolve()
    run_dirs = sorted(
        (
            path
            for path in runs_root.iterdir()
            if path.is_dir() and re.fullmatch(r"\d{8}_\d{6}", path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    for path in run_dirs[runs_to_keep:]:
        if path.resolve() == current_resolved:
            continue
        shutil.rmtree(path)


def load_previous_summary(primary_path: Path, legacy_path: Path) -> dict[str, Any]:
    for candidate in (primary_path, legacy_path):
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8-sig"))
    return {}


def structured_dump_steps(mode: str) -> list[dict[str, Any]]:
    if mode == "debug":
        return [{"name": "debug_all", "block_types": (), "file_regexes": ()}]
    return [
        {
            "name": "required",
            "block_types": WEBUI_STRUCTURED_REQUIRED_BLOCK_TYPES,
            "file_regexes": (),
        },
    ]


def describe_structured_dump_steps(steps: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for step in steps:
        block_types = step.get("block_types") or ()
        file_regexes = step.get("file_regexes") or ()
        block_text = ",".join(str(item) for item in block_types) if block_types else "all"
        if file_regexes:
            regex_text = ",".join(str(item) for item in file_regexes)
            parts.append(f"{step['name']}[{block_text}; files={regex_text}]")
        else:
            parts.append(f"{step['name']}[{block_text}]")
    return "; ".join(parts)


def structured_dump_command_name(source: str, step: dict[str, Any], step_count: int) -> str:
    if step_count == 1:
        return f"{source}_structured_dump"
    return f"{source}_structured_dump_{step['name']}"


def structured_output_dir(output_root: Path, source: str) -> Path:
    return output_root / "structured" / source


def reset_structured_output_dir(output_root: Path, source: str) -> Path:
    target = structured_output_dir(output_root, source)
    allowed_root = (output_root / "structured").resolve()
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise RuntimeError(f"refusing to clear structured output outside {allowed_root}: {target_resolved}") from exc
    if target_resolved == allowed_root:
        raise RuntimeError(f"refusing to clear structured root directly: {target_resolved}")

    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.mkdir(parents=True, exist_ok=True)
    return target


def resolve_existing_structured_output_dir(output_root: Path, source: str) -> Path:
    preferred = structured_output_dir(output_root, source)
    legacy = output_root / source
    if preferred.exists() or not legacy.exists():
        return preferred
    return legacy


def vfs_index_dir(output_root: Path, source: str) -> Path:
    return output_root / "recovered" / "AnimeStudio-cli" / source / "vfs_index"


VFS_INDEX_BLOCKS: tuple[tuple[str, str], ...] = (
    ("bundle", "bundle"),
    ("initial-bundle", "initial-bundle"),
)


def vfs_index_path(output_root: Path, source: str, block_name: str = "bundle") -> Path:
    return vfs_index_dir(output_root, source) / f"{block_name.lower()}_vfs_index.json"


def vfs_index_command_name(source: str, block_name: str) -> str:
    return f"{source}_vfs_index_{block_name.replace('-', '_')}"


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


def summarize_vfs_indexes(
    output_root: Path,
    source: str,
    command_results_by_name: dict[str, CommandResult] | None = None,
) -> dict[str, Any]:
    block_summaries: dict[str, dict[str, Any]] = {}
    for block_name, _cli_block_name in VFS_INDEX_BLOCKS:
        result = None
        if command_results_by_name is not None:
            result = command_results_by_name.get(vfs_index_command_name(source, block_name))
        block_summaries[block_name] = summarize_vfs_index(vfs_index_path(output_root, source, block_name), result)

    existing_blocks = {
        block_name: info
        for block_name, info in block_summaries.items()
        if info.get("exists")
    }
    summary: dict[str, Any] = {
        "exists": bool(existing_blocks),
        "blocks": block_summaries,
        "block_names": list(block_summaries),
        "index_paths": [info.get("index_path") for info in existing_blocks.values()],
    }
    if "bundle" in block_summaries:
        summary["index_path"] = block_summaries["bundle"].get("index_path")

    for key in (
        "block_count",
        "missing_block_count",
        "chunk_count",
        "missing_chunk_count",
        "file_count",
        "byte_count",
    ):
        values = [
            info.get(key)
            for info in existing_blocks.values()
            if isinstance(info.get(key), int)
        ]
        summary[key] = sum(values) if values else None

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


def validate_dummy_dll_dir(path: Path | str, source: str) -> Path | None:
    candidate = normalize_dummy_dll_path(path)
    if not looks_like_dummy_dll_dir(candidate):
        log(
            "  warning: AnimeStudio DummyDll directory from "
            f"{source} was not found or contains no .dll files: {candidate}; "
            "continuing without that DummyDll path"
        )
        return None
    return candidate.resolve()


def resolve_animestudio_dummy_dlls(explicit: Path | None, game_root: Path) -> tuple[Path | None, str | None]:
    if explicit is not None:
        resolved = validate_dummy_dll_dir(explicit, "--animestudio-dummy-dlls")
        return (resolved, "--animestudio-dummy-dlls") if resolved is not None else (None, None)

    env_value = os.environ.get(ANIMESTUDIO_DUMMY_DLL_ENV, "").strip()
    if env_value:
        resolved = validate_dummy_dll_dir(env_value, ANIMESTUDIO_DUMMY_DLL_ENV)
        if resolved is not None:
            return resolved, ANIMESTUDIO_DUMMY_DLL_ENV
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


def normalize_animestudio_option_for_compare(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return value


def detect_animestudio_stage_merge_feature(animestudio_exe: Path, mode: str) -> dict[str, Any]:
    flags = dict(ANIMESTUDIO_SECONDARY_EXPORT_FLAGS)
    feature: dict[str, Any] = {
        "contract": "secondary_export_v1",
        "requested_mode": mode,
        "effective_mode": "never",
        "primary_stage": ANIMESTUDIO_STAGE_MERGE_PRIMARY_STAGE,
        "secondary_stage": ANIMESTUDIO_STAGE_MERGE_SECONDARY_STAGE,
        "flags": flags,
        "supported": False,
        "probed": False,
        "probe_commands": [],
        "missing_flags": list(flags.values()),
        "reason": "stage merging is disabled",
    }
    if mode == "never":
        feature["reason"] = "stage merge mode is never"
        return feature
    if mode == "auto":
        feature["reason"] = "auto preserves split stages until the secondary-export CLI contract is enabled explicitly"
        return feature

    feature["probed"] = True
    help_text_parts: list[str] = []
    for probe_argv in ((str(animestudio_exe), "--help"), (str(animestudio_exe),)):
        started = time.time()
        probe_info: dict[str, Any] = {"argv": list(probe_argv)}
        try:
            proc = subprocess.run(
                list(probe_argv),
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
        except Exception as exc:  # pragma: no cover - defensive around local CLI launch failures
            probe_info["error"] = str(exc)
            probe_info["duration_seconds"] = round(time.time() - started, 3)
            feature["probe_commands"].append(probe_info)
            continue
        probe_info["returncode"] = proc.returncode
        probe_info["duration_seconds"] = round(time.time() - started, 3)
        feature["probe_commands"].append(probe_info)
        help_text_parts.extend([proc.stdout or "", proc.stderr or ""])
        combined = "\n".join(help_text_parts)
        if all(flag in combined for flag in flags.values()):
            break

    help_text = "\n".join(help_text_parts)
    missing_flags = [flag for flag in flags.values() if flag not in help_text]
    feature["missing_flags"] = missing_flags
    if missing_flags:
        feature["reason"] = "secondary-export CLI flags were not found in AnimeStudio help output"
        return feature
    feature["supported"] = True
    feature["effective_mode"] = "aggressive"
    feature["reason"] = "secondary-export CLI flags are available"
    return feature


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


def read_animestudio_log_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if data.startswith((b"\xef\xbb\xbf",)):
        return data.decode("utf-8-sig", errors="replace")
    if b"\x00" in data[:128]:
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8", errors="replace")


def normalize_animestudio_log_line(line: str) -> str:
    return ANIMESTUDIO_ANSI_ESCAPE_RE.sub("", line).strip("\ufeff\x00")


def unescape_animestudio_log_value(value: str) -> str:
    result: list[str] = []
    escaped = False
    for char in value:
        if escaped:
            result.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            result.append(char)
    if escaped:
        result.append("\\")
    return "".join(result)


def parse_animestudio_log_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in ANIMESTUDIO_LOG_KEY_VALUE_RE.finditer(text):
        if match.group("quoted") is not None:
            value = unescape_animestudio_log_value(match.group("quoted"))
        else:
            value = match.group("bare") or ""
        fields[match.group("key")] = value
    return fields


def normalize_partial_mono_behaviour_reason(reason: str) -> str:
    return ANIMESTUDIO_PARTIAL_MONO_REASON_OFFSET_RE.sub(" at position <offset>.", reason.strip())


def increment_count(mapping: dict[str, int], key: str) -> None:
    mapping[key] = mapping.get(key, 0) + 1


def summarize_animestudio_log_issues(stdout_log: str | Path | None, stderr_log: str | Path | None) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "error_count": 0,
        "warning_count": 0,
        "exception_count": 0,
        "end_of_stream_count": 0,
        "export_error_count": 0,
        "story_like_export_error_count": 0,
        "metadata_only_json_count": 0,
        "partial_mono_behaviour_count": 0,
        "partial_mono_behaviour_by_decoder": {},
        "partial_mono_behaviour_by_exception": {},
        "partial_mono_behaviour_by_reason": {},
        "texture2d_no_output_count": 0,
        "texture2d_no_payload_count": 0,
        "texture2d_decode_failed_count": 0,
        "mesh_no_output_count": 0,
        "mesh_expected_no_output_count": 0,
        "mesh_suspicious_no_output_count": 0,
        "animator_no_output_count": 0,
        "animator_no_mesh_count": 0,
        "animator_suspicious_no_output_count": 0,
        "samples": [],
        "export_error_samples": [],
        "story_like_export_error_samples": [],
        "metadata_only_json_samples": [],
        "partial_mono_behaviour_samples": [],
        "texture2d_no_output_samples": [],
        "texture2d_no_output_records": [],
        "mesh_no_output_samples": [],
        "mesh_no_output_records": [],
        "animator_no_output_samples": [],
        "animator_no_output_records": [],
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
            for line_number, line in enumerate(read_animestudio_log_text(path).splitlines(), 1):
                text = normalize_animestudio_log_line(line)
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

                texture2d_no_output_match = ANIMESTUDIO_TEXTURE2D_NO_OUTPUT_RE.match(text)
                if texture2d_no_output_match:
                    fields = parse_animestudio_log_fields(texture2d_no_output_match.group("fields"))
                    reason = fields.get("reason", "")
                    summary["texture2d_no_output_count"] += 1
                    if reason in ANIMESTUDIO_TEXTURE2D_NO_PAYLOAD_REASONS:
                        summary["texture2d_no_payload_count"] += 1
                    elif reason == "decode_failed":
                        summary["texture2d_decode_failed_count"] += 1
                    sample = {
                        "stream": stream_name,
                        "line": line_number,
                        "reason": reason,
                    }
                    for field in (
                        "name",
                        "PathID",
                        "SourceFile",
                        "SourceOriginalPath",
                        "SourceOffset",
                        "Container",
                        "Width",
                        "Height",
                        "Format",
                        "ImageSize",
                        "StreamSize",
                        "StreamOffset",
                        "StreamPath",
                    ):
                        if field in fields:
                            sample[field] = fields[field]
                    summary["texture2d_no_output_records"].append(sample)
                    add_sample("texture2d_no_output_samples", sample)
                mesh_no_output_match = ANIMESTUDIO_MESH_NO_OUTPUT_RE.match(text)
                if mesh_no_output_match:
                    fields = parse_animestudio_log_fields(mesh_no_output_match.group("fields"))
                    reason = fields.get("reason", "")
                    summary["mesh_no_output_count"] += 1
                    if reason in ANIMESTUDIO_MESH_EXPECTED_NO_OUTPUT_REASONS:
                        summary["mesh_expected_no_output_count"] += 1
                    else:
                        summary["mesh_suspicious_no_output_count"] += 1
                    sample = {
                        "stream": stream_name,
                        "line": line_number,
                        "reason": reason,
                    }
                    for field in (
                        "name",
                        "PathID",
                        "SourceFile",
                        "SourceOriginalPath",
                        "SourceOffset",
                        "Container",
                        "VertexCount",
                        "VerticesLength",
                        "SubMeshCount",
                        "IndexCount",
                        "ByteSize",
                    ):
                        if field in fields:
                            sample[field] = fields[field]
                    summary["mesh_no_output_records"].append(sample)
                    add_sample("mesh_no_output_samples", sample)
                animator_no_output_match = ANIMESTUDIO_ANIMATOR_NO_OUTPUT_RE.match(text)
                if animator_no_output_match:
                    fields = parse_animestudio_log_fields(animator_no_output_match.group("fields"))
                    reason = fields.get("reason", "")
                    summary["animator_no_output_count"] += 1
                    if reason in ANIMESTUDIO_ANIMATOR_EXPECTED_NO_OUTPUT_REASONS:
                        summary["animator_no_mesh_count"] += 1
                    else:
                        summary["animator_suspicious_no_output_count"] += 1
                    sample = {
                        "stream": stream_name,
                        "line": line_number,
                        "reason": reason,
                    }
                    for field in (
                        "name",
                        "PathID",
                        "SourceFile",
                        "SourceOriginalPath",
                        "SourceOffset",
                        "Container",
                        "GameObjectName",
                        "GameObjectPathID",
                        "GameObjectPointerPathID",
                        "AvatarPathID",
                        "ControllerPathID",
                        "HasTransformHierarchy",
                        "MeshCount",
                        "MaterialCount",
                        "TextureCount",
                        "AnimationCount",
                        "ExportPath",
                    ):
                        if field in fields:
                            sample[field] = fields[field]
                    summary["animator_no_output_records"].append(sample)
                    add_sample("animator_no_output_samples", sample)

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

                partial_mono_match = ANIMESTUDIO_PARTIAL_MONO_BEHAVIOUR_RE.match(text)
                if partial_mono_match:
                    asset = partial_mono_match.group("asset").strip()
                    decoder = partial_mono_match.group("decoder").strip()
                    exception = partial_mono_match.group("exception").strip()
                    reason = normalize_partial_mono_behaviour_reason(partial_mono_match.group("reason"))
                    summary["partial_mono_behaviour_count"] += 1
                    increment_count(summary["partial_mono_behaviour_by_decoder"], decoder)
                    increment_count(summary["partial_mono_behaviour_by_exception"], exception)
                    increment_count(summary["partial_mono_behaviour_by_reason"], reason)
                    add_sample(
                        "partial_mono_behaviour_samples",
                        {
                            "stream": stream_name,
                            "line": line_number,
                            "asset": asset,
                            "decoder": decoder,
                            "exception": exception,
                            "reason": reason,
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
    if not summary["partial_mono_behaviour_samples"]:
        summary.pop("partial_mono_behaviour_samples", None)
    for key in (
        "partial_mono_behaviour_by_decoder",
        "partial_mono_behaviour_by_exception",
        "partial_mono_behaviour_by_reason",
    ):
        if not summary[key]:
            summary.pop(key, None)
    if not summary["texture2d_no_output_samples"]:
        summary.pop("texture2d_no_output_samples", None)
    if not summary["texture2d_no_output_records"]:
        summary.pop("texture2d_no_output_records", None)
    if not summary["mesh_no_output_samples"]:
        summary.pop("mesh_no_output_samples", None)
    if not summary["mesh_no_output_records"]:
        summary.pop("mesh_no_output_records", None)
    if not summary["animator_no_output_samples"]:
        summary.pop("animator_no_output_samples", None)
    if not summary["animator_no_output_records"]:
        summary.pop("animator_no_output_records", None)
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
        "partial_mono_behaviour_count": 0,
        "partial_mono_behaviour_by_decoder": {},
        "partial_mono_behaviour_by_exception": {},
        "partial_mono_behaviour_by_reason": {},
        "texture2d_no_output_count": 0,
        "texture2d_no_payload_count": 0,
        "texture2d_decode_failed_count": 0,
        "mesh_no_output_count": 0,
        "mesh_expected_no_output_count": 0,
        "mesh_suspicious_no_output_count": 0,
        "animator_no_output_count": 0,
        "animator_no_mesh_count": 0,
        "animator_suspicious_no_output_count": 0,
        "samples": [],
        "export_error_samples": [],
        "story_like_export_error_samples": [],
        "metadata_only_json_samples": [],
        "partial_mono_behaviour_samples": [],
        "texture2d_no_output_samples": [],
        "texture2d_no_output_records": [],
        "mesh_no_output_samples": [],
        "mesh_no_output_records": [],
        "animator_no_output_samples": [],
        "animator_no_output_records": [],
        "missing_logs": [],
    }
    sample_keys = (
        "samples",
        "export_error_samples",
        "story_like_export_error_samples",
        "metadata_only_json_samples",
        "partial_mono_behaviour_samples",
        "texture2d_no_output_samples",
        "mesh_no_output_samples",
        "animator_no_output_samples",
    )
    count_keys = (
        "error_count",
        "warning_count",
        "exception_count",
        "end_of_stream_count",
        "export_error_count",
        "story_like_export_error_count",
        "metadata_only_json_count",
        "partial_mono_behaviour_count",
        "texture2d_no_output_count",
        "texture2d_no_payload_count",
        "texture2d_decode_failed_count",
        "mesh_no_output_count",
        "mesh_expected_no_output_count",
        "mesh_suspicious_no_output_count",
        "animator_no_output_count",
        "animator_no_mesh_count",
        "animator_suspicious_no_output_count",
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
        for key in (
            "partial_mono_behaviour_by_decoder",
            "partial_mono_behaviour_by_exception",
            "partial_mono_behaviour_by_reason",
        ):
            target = merged.setdefault(key, {})
            for item_key, count in (issues.get(key) or {}).items():
                target[item_key] = int(target.get(item_key) or 0) + int(count or 0)
        for key in ("texture2d_no_output_records", "mesh_no_output_records", "animator_no_output_records"):
            target = merged.setdefault(key, [])
            for sample in issues.get(key) or []:
                enriched = dict(sample)
                enriched.setdefault("command", result.name)
                target.append(enriched)
        merged["missing_logs"].extend(issues.get("missing_logs") or [])

    for key in sample_keys + (
        "texture2d_no_output_records",
        "mesh_no_output_records",
        "animator_no_output_records",
        "partial_mono_behaviour_by_decoder",
        "partial_mono_behaviour_by_exception",
        "partial_mono_behaviour_by_reason",
        "missing_logs",
    ):
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
    secondary_export: AnimeStudioSecondaryExport | None = None,
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
    expanded_types = animestudio_type_specs_for_export(stage, export_type, tuple(types))
    expanded_secondary_types: tuple[str, ...] = ()
    if secondary_export is not None:
        expanded_secondary_types = animestudio_type_specs_for_export(
            secondary_export.stage,
            secondary_export.export_type,
            tuple(secondary_export.types),
        )
    combined_type_specs = expanded_types + expanded_secondary_types
    if mono_behaviour_type_tree_priority and any(
        animestudio_type_name(type_spec) == "MonoBehaviour" for type_spec in combined_type_specs
    ):
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
    if expanded_types:
        cmd.append("--types")
        cmd.extend(expanded_types)
    if secondary_export is not None:
        ensure_dir(secondary_export.output_path)
        cmd.extend([ANIMESTUDIO_SECONDARY_EXPORT_FLAGS["output"], str(secondary_export.output_path)])
        cmd.extend([ANIMESTUDIO_SECONDARY_EXPORT_FLAGS["export_type"], secondary_export.export_type])
        if expanded_secondary_types:
            cmd.append(ANIMESTUDIO_SECONDARY_EXPORT_FLAGS["types"])
            cmd.extend(expanded_secondary_types)
    name = command_name or f"{source}_animestudio_{stage}"
    result = run_logged_command(name, cmd, work_dir, reports_dir, stream_output=True)
    if result.returncode == 0 and animestudio_cli_usage_error(result):
        log(f"  animestudio command {name} printed CLI usage/validation output; treating as failed")
        return mark_command_result_failed(result)
    return result


def run_animestudio_call_tasks(
    tasks: list[dict[str, Any]],
    jobs: int,
    call_pool: AnimeStudioCallPool | None = None,
) -> None:
    if not tasks:
        return
    worker_count = call_pool.max_workers if call_pool is not None else max(1, jobs)
    log(
        f"  animestudio call pool: queueing {len(tasks)} task(s) "
        f"with workers={worker_count}"
    )

    def drain(pool: AnimeStudioCallPool) -> None:
        future_to_task = {
            pool.submit_stage(**task["kwargs"]): task
            for task in tasks
        }
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            result = future.result()
            task["result"] = result
            kind = task.get("kind")
            if kind == "asset_shard":
                asset_work = task["asset_work"]
                shard = task["shard"]
                shard_index = int(shard["index"])
                asset_work.setdefault("result_by_shard", {})[shard_index] = result
                log(
                    f"  animestudio asset shard {task['stage']}:{task['item_name']} "
                    f"{shard_index}/{int(shard['count'])} for {task['source']}: "
                    f"returncode={result.returncode}"
                )
            elif kind == "merged_types":
                log(
                    f"  animestudio merged type task {task['stage']} "
                    f"({', '.join(task.get('item_names', []))}) for {task['source']}: "
                    f"returncode={result.returncode}"
                )
            elif kind == "type":
                log(
                    f"  animestudio type {task['stage']}:{task['item_name']} for {task['source']}: "
                    f"returncode={result.returncode}"
                )
            else:
                log(
                    f"  animestudio task {task.get('stage')} for {task.get('source')}: "
                    f"returncode={result.returncode}"
                )

    if call_pool is not None:
        drain(call_pool)
    else:
        with AnimeStudioCallPool(worker_count) as local_pool:
            drain(local_pool)


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
    asset_cache: dict[str, Any] | None = None,
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
    if cache_enabled:
        if asset_cache is None:
            asset_cache = load_animestudio_asset_cache(cache_path)
    else:
        asset_cache = default_animestudio_asset_cache()
    cached_entries: list[dict[str, Any]] = []
    pending_entries: list[dict[str, Any]] = []
    for entry in matched_entries:
        output_path = predict_animestudio_convert_output_path(output_root, source, stage, entry)
        if output_path is None:
            pending_entries.append(entry)
            continue
        # Only compute the sha256 manifest/cache keys when the cache is enabled;
        # with the cache removed every matched entry is simply re-exported.
        if cache_enabled:
            manifest_key = asset_entry_manifest_key(entry, item, plan)
            cache_key = asset_entry_cache_key(entry, item, plan)
            if asset_cache_entry_is_valid(asset_cache, manifest_key, cache_key, output_path):
                cached_entries.append(entry)
                continue
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


def begin_animestudio_asset_shard_work(
    source: str,
    output_root: Path,
    stage: str,
    asset_work: dict[str, Any],
) -> tuple[bool, list[str], list[str]]:
    item = asset_work["item"]
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

    if shards:
        return True, [], []

    missing_outputs_allowed = type_name in ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES
    status_summary = write_animestudio_asset_status_manifest(
        output_root=output_root,
        source=source,
        stage=stage,
        type_name=type_name,
        entries=asset_work["matched_entries"],
        missing_outputs_allowed=missing_outputs_allowed,
    )
    asset_info["updated_entry_count"] = 0
    asset_info["successful_shard_count"] = 0
    asset_info["failed_shard_count"] = 0
    asset_info["output_entry_count"] = status_summary["output_entry_count"]
    asset_info["missing_output_count"] = status_summary["missing_output_count"]
    asset_info["export_error_count"] = 0
    for key in (
        "manifest_path",
        "unique_output_path_count",
        "output_unique_path_count",
        "actual_output_file_count",
        "marker_output_count",
        "name_mismatch_output_count",
        "alternate_name_output_count",
        "alternate_name_reason_counts",
        "alternate_name_source_hint_counts",
        "alternate_name_case_normalized_count",
        "missing_unique_output_count",
        "allowed_missing_output_count",
        "suspicious_missing_output_count",
        "classified_no_payload_missing_output_count",
        "classified_mesh_expected_missing_output_count",
        "mesh_no_output_count",
        "mesh_expected_no_output_count",
        "mesh_suspicious_no_output_count",
        "animator_no_output_count",
        "animator_no_mesh_count",
        "animator_suspicious_no_output_count",
        "texture2d_no_output_count",
        "texture2d_no_payload_count",
        "texture2d_decode_failed_count",
        "duplicate_output_path_group_count",
        "duplicate_output_entry_count",
        "uncertain_duplicate_output_path_group_count",
        "uncertain_duplicate_output_entry_count",
        "cross_ab_output_collision_group_count",
        "cross_ab_output_collision_entry_count",
        "shared_output_reference_group_count",
        "shared_output_reference_entry_count",
        "same_asset_id_output_reference_group_count",
        "same_asset_id_output_reference_entry_count",
        "raw_hash_output_collision_group_count",
        "raw_hash_output_collision_entry_count",
        "identity_output_collision_group_count",
        "identity_output_collision_entry_count",
        "uncertain_output_collision_group_count",
        "uncertain_output_collision_entry_count",
        "source_group_count",
        "clean_source_group_count",
        "dirty_source_group_count",
    ):
        asset_info[key] = status_summary.get(key)
    missing_output_count = int(status_summary.get("missing_output_count") or 0)
    suspicious_missing_output_count = int(
        status_summary["suspicious_missing_output_count"]
        if "suspicious_missing_output_count" in status_summary
        else missing_output_count
    )
    if suspicious_missing_output_count and not missing_outputs_allowed:
        log(
            f"  animestudio asset cache {stage}:{type_name} for {source}: "
            f"marking failed because missing_outputs={missing_output_count} "
            f"suspicious_missing_outputs={suspicious_missing_output_count}"
        )
        return False, [], [item["item_name"]]
    return False, [item["item_name"]], []


def finalize_animestudio_asset_shard_work(
    source: str,
    output_root: Path,
    stage: str,
    plan: dict[str, Any],
    asset_work: dict[str, Any],
) -> tuple[list[CommandResult], list[str], list[str]]:
    item = asset_work["item"]
    type_name = asset_work["type_name"]
    asset_info = asset_work["asset_info"]
    shards = asset_work["shards"]
    result_by_shard = asset_work.get("result_by_shard", {})
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
        # The in-memory cache was loaded from disk and is only mutated by adding
        # entries, so when nothing was updated the file is unchanged; skip the write.
        if updated_cache_entries:
            save_animestudio_asset_cache(asset_work["cache_path"], asset_work["asset_cache"])
    asset_info["updated_entry_count"] = updated_cache_entries
    asset_info["successful_shard_count"] = sum(1 for result in ordered_results if result.returncode == 0)
    asset_info["failed_shard_count"] = sum(1 for result in ordered_results if result.returncode != 0)
    log_issues = merge_animestudio_log_issues(ordered_results)
    export_error_count = int(log_issues.get("export_error_count") or 0)
    missing_outputs_allowed_for_type = type_name in ANIMESTUDIO_ALLOW_MISSING_CONVERT_OUTPUT_TYPES
    status_summary = write_animestudio_asset_status_manifest(
        output_root=output_root,
        source=source,
        stage=stage,
        type_name=type_name,
        entries=asset_work["matched_entries"],
        missing_outputs_allowed=missing_outputs_allowed_for_type,
        log_issues=log_issues,
    )
    asset_info["output_entry_count"] = status_summary["output_entry_count"]
    asset_info["missing_output_count"] = status_summary["missing_output_count"]
    asset_info["export_error_count"] = export_error_count
    for key in (
        "manifest_path",
        "unique_output_path_count",
        "output_unique_path_count",
        "actual_output_file_count",
        "marker_output_count",
        "name_mismatch_output_count",
        "alternate_name_output_count",
        "alternate_name_reason_counts",
        "alternate_name_source_hint_counts",
        "alternate_name_case_normalized_count",
        "missing_unique_output_count",
        "allowed_missing_output_count",
        "suspicious_missing_output_count",
        "classified_no_payload_missing_output_count",
        "classified_mesh_expected_missing_output_count",
        "texture2d_no_output_count",
        "texture2d_no_payload_count",
        "texture2d_decode_failed_count",
        "mesh_no_output_count",
        "mesh_expected_no_output_count",
        "mesh_suspicious_no_output_count",
        "animator_no_output_count",
        "animator_no_mesh_count",
        "animator_suspicious_no_output_count",
        "duplicate_output_path_group_count",
        "duplicate_output_entry_count",
        "uncertain_duplicate_output_path_group_count",
        "uncertain_duplicate_output_entry_count",
        "cross_ab_output_collision_group_count",
        "cross_ab_output_collision_entry_count",
        "shared_output_reference_group_count",
        "shared_output_reference_entry_count",
        "same_asset_id_output_reference_group_count",
        "same_asset_id_output_reference_entry_count",
        "raw_hash_output_collision_group_count",
        "raw_hash_output_collision_entry_count",
        "identity_output_collision_group_count",
        "identity_output_collision_entry_count",
        "uncertain_output_collision_group_count",
        "uncertain_output_collision_entry_count",
        "source_group_count",
        "clean_source_group_count",
        "dirty_source_group_count",
        "unmapped_export_error_count",
    ):
        asset_info[key] = status_summary.get(key)
    missing_output_count = int(status_summary.get("missing_output_count") or 0)
    suspicious_missing_output_count = int(status_summary.get("suspicious_missing_output_count") or 0)
    texture2d_decode_failed_count = int(status_summary.get("texture2d_decode_failed_count") or 0)
    mesh_suspicious_no_output_count = int(status_summary.get("mesh_suspicious_no_output_count") or 0)
    classified_mesh_expected_missing_output_count = int(
        status_summary.get("classified_mesh_expected_missing_output_count") or 0
    )
    all_shards_returned_cleanly = (
        bool(ordered_results)
        and len(ordered_results) == len(shards)
        and all(result.returncode == 0 for result in ordered_results)
    )
    missing_outputs_allowed = (
        missing_outputs_allowed_for_type
        and export_error_count == 0
        and all_shards_returned_cleanly
    )
    texture2d_missing_outputs_explained = (
        type_name == "Texture2D"
        and missing_output_count > 0
        and suspicious_missing_output_count == 0
        and texture2d_decode_failed_count == 0
        and export_error_count == 0
        and all_shards_returned_cleanly
    )
    mesh_missing_outputs_explained = (
        type_name == "Mesh"
        and missing_output_count > 0
        and suspicious_missing_output_count == 0
        and mesh_suspicious_no_output_count == 0
        and classified_mesh_expected_missing_output_count == missing_output_count
        and export_error_count == 0
        and all_shards_returned_cleanly
    )
    if not missing_outputs_allowed and not texture2d_missing_outputs_explained and not mesh_missing_outputs_explained:
        asset_info["allowed_missing_output_count"] = 0
    all_succeeded = (
        all_shards_returned_cleanly
        and (
            missing_output_count == 0
            or missing_outputs_allowed
            or texture2d_missing_outputs_explained
            or mesh_missing_outputs_explained
        )
        and export_error_count == 0
        and texture2d_decode_failed_count == 0
        and mesh_suspicious_no_output_count == 0
    )
    if missing_output_count and missing_outputs_allowed:
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"allowed {missing_output_count} no-output {type_name} entries"
        )
    elif missing_output_count and texture2d_missing_outputs_explained:
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"allowed {asset_info.get('allowed_missing_output_count') or missing_output_count} no-payload Texture2D entries"
        )
    elif missing_output_count and mesh_missing_outputs_explained:
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"allowed {classified_mesh_expected_missing_output_count} zero-vertex Mesh no-output entries"
        )
    if not all_succeeded and (
        suspicious_missing_output_count
        or export_error_count
        or texture2d_decode_failed_count
        or mesh_suspicious_no_output_count
        or len(ordered_results) != len(shards)
    ):
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"marking failed because missing_outputs={missing_output_count} "
            f"suspicious_missing_outputs={suspicious_missing_output_count} "
            f"export_errors={export_error_count} "
            f"texture2d_decode_failed={texture2d_decode_failed_count} "
            f"mesh_suspicious_no_output={mesh_suspicious_no_output_count} "
            f"completed_shards={len(ordered_results)}/{len(shards)}"
        )
    return (
        ordered_results,
        [item["item_name"]] if all_succeeded else [],
        [] if all_succeeded else [item["item_name"]],
    )


def should_merge_animestudio_type_jobs(
    stage: str,
    normal_items: list[dict[str, Any]],
    mode: str,
    *,
    asset_map_filter: bool = False,
) -> bool:
    if stage == "maps" or len(normal_items) <= 1:
        return False
    if mode == "parallel":
        return False
    if mode == "merged":
        return True
    # A broad Endfield JSON load can retain hundreds of thousands of
    # MonoBehaviours while exporting later types.  Keep auto-mode Story types
    # in isolated processes; merging remains safe for map-filtered asset JSON.
    return stage == "json_by_type" and asset_map_filter


def animestudio_plan_runnable_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    run_item_names = set(plan.get("run_items", []))
    return [
        item for item in plan.get("items", [])
        if item["item_name"] in run_item_names
    ]


def build_animestudio_stage_merge_attempt(
    source: str,
    output_root: Path,
    selected_stages: tuple[str, ...],
    stage_plans: dict[str, dict[str, Any]],
    stage_merge_feature: dict[str, Any],
) -> dict[str, Any] | None:
    if stage_merge_feature.get("requested_mode") != "aggressive":
        return None

    primary_stage = ANIMESTUDIO_STAGE_MERGE_PRIMARY_STAGE
    secondary_stage = ANIMESTUDIO_STAGE_MERGE_SECONDARY_STAGE
    attempt: dict[str, Any] = {
        "source": source,
        "requested_mode": stage_merge_feature.get("requested_mode"),
        "effective_mode": "never",
        "supported": bool(stage_merge_feature.get("supported")),
        "mergeable": False,
        "ran_this_run": False,
        "primary_stage": primary_stage,
        "secondary_stage": secondary_stage,
        "primary_items": [],
        "secondary_items": [],
        "primary_types": [],
        "secondary_types": [],
        "secondary_output_root": str(animestudio_stage_dir(output_root, source, secondary_stage)),
        "cli_flags": dict(ANIMESTUDIO_SECONDARY_EXPORT_FLAGS),
        "reason": stage_merge_feature.get("reason"),
    }
    if not stage_merge_feature.get("supported"):
        return attempt
    if primary_stage not in selected_stages or secondary_stage not in selected_stages:
        attempt["reason"] = "both convert_by_type and json_by_type must be selected"
        return attempt

    primary_plan = stage_plans.get(primary_stage)
    secondary_plan = stage_plans.get(secondary_stage)
    if not primary_plan or not secondary_plan:
        attempt["reason"] = "both stage plans must exist"
        return attempt
    if not primary_plan.get("should_run") or not secondary_plan.get("should_run"):
        attempt["reason"] = "both stages need pending run items"
        return attempt

    primary_items = animestudio_plan_runnable_items(primary_plan)
    secondary_items = animestudio_plan_runnable_items(secondary_plan)
    primary_types = tuple(item["type_spec"] for item in primary_items if item.get("type_spec") is not None)
    secondary_types = tuple(item["type_spec"] for item in secondary_items if item.get("type_spec") is not None)
    if not primary_types or not secondary_types:
        attempt["reason"] = "both stages need concrete type specs"
        return attempt

    primary_options = primary_plan.get("options") or {}
    secondary_options = secondary_plan.get("options") or {}
    if primary_options.get("export_type") != "Convert" or secondary_options.get("export_type") != "JSON":
        attempt["reason"] = "only Convert primary plus JSON secondary exports are mergeable"
        return attempt

    unsafe_primary_types = [
        animestudio_type_name(type_spec)
        for type_spec in primary_types
        if not animestudio_map_filter_is_safe((type_spec,))
    ]
    if unsafe_primary_types:
        attempt["reason"] = "primary convert types require broad dependency loading and must stay separate"
        attempt["unsafe_primary_types"] = unsafe_primary_types
        return attempt

    cacheable_primary_types = [
        animestudio_type_name(type_spec)
        for type_spec in primary_types
        if animestudio_asset_cache_supported(primary_stage, primary_options, animestudio_type_name(type_spec))
    ]
    if cacheable_primary_types:
        attempt["reason"] = "cacheable convert types should stay on the sharded asset-cache path"
        attempt["cacheable_primary_types"] = cacheable_primary_types
        return attempt

    mismatches: dict[str, dict[str, Any]] = {}
    for key in ANIMESTUDIO_STAGE_MERGE_SHARED_OPTION_KEYS:
        primary_value = normalize_animestudio_option_for_compare(primary_options.get(key))
        secondary_value = normalize_animestudio_option_for_compare(secondary_options.get(key))
        if primary_value != secondary_value:
            mismatches[key] = {"primary": primary_value, "secondary": secondary_value}
    if mismatches:
        attempt["reason"] = "primary and secondary stage options differ"
        attempt["option_mismatches"] = mismatches
        return attempt

    attempt.update(
        {
            "effective_mode": "aggressive",
            "mergeable": True,
            "command_name": f"{source}_animestudio_{primary_stage}_{secondary_stage}_merged",
            "primary_items": [item["item_name"] for item in primary_items],
            "secondary_items": [item["item_name"] for item in secondary_items],
            "primary_types": list(primary_types),
            "secondary_types": list(secondary_types),
            "asset_cache_bypassed": bool(primary_options.get("asset_cache_enabled")),
            "reason": "Convert primary export can carry JSON as a secondary export",
        }
    )
    return attempt


def mark_animestudio_stage_plan_from_merge(
    plan: dict[str, Any],
    attempt: dict[str, Any],
    role: str,
    item_names: list[str],
    result: CommandResult,
) -> None:
    plan["command_results"] = [result]
    plan["succeeded_items"] = list(item_names) if result.returncode == 0 else []
    plan["failed_items"] = [] if result.returncode == 0 else list(item_names)
    plan["stdout_log"] = result.stdout_log
    plan["stderr_log"] = result.stderr_log
    paired_stage = attempt["secondary_stage"] if role == "primary" else attempt["primary_stage"]
    plan["stage_merge"] = {
        "requested_mode": attempt.get("requested_mode"),
        "effective_mode": attempt.get("effective_mode"),
        "role": role,
        "paired_stage": paired_stage,
        "command_name": attempt.get("command_name"),
        "reason": attempt.get("reason"),
        "asset_cache_bypassed": attempt.get("asset_cache_bypassed", False),
    }


def run_animestudio_stage_merge_plan(
    source: str,
    input_root: Path,
    output_root: Path,
    reports_dir: Path,
    animestudio_exe: Path,
    animestudio_dummy_dlls: Path | None,
    stage_plans: dict[str, dict[str, Any]],
    attempt: dict[str, Any],
    call_pool: AnimeStudioCallPool | None = None,
) -> list[CommandResult]:
    primary_stage = attempt["primary_stage"]
    secondary_stage = attempt["secondary_stage"]
    primary_plan = stage_plans[primary_stage]
    secondary_plan = stage_plans[secondary_stage]
    primary_options = primary_plan["options"]
    secondary_options = secondary_plan["options"]
    primary_items = animestudio_plan_runnable_items(primary_plan)
    secondary_items = animestudio_plan_runnable_items(secondary_plan)
    primary_types = tuple(attempt.get("primary_types") or ())
    secondary_types = tuple(attempt.get("secondary_types") or ())

    clear_animestudio_stage_outputs(output_root, source, primary_stage, primary_items)
    clear_animestudio_stage_outputs(output_root, source, secondary_stage, secondary_items)
    secondary_export = AnimeStudioSecondaryExport(
        stage=secondary_stage,
        output_path=animestudio_stage_dir(output_root, source, secondary_stage),
        export_type=secondary_options["export_type"],
        types=secondary_types,
    )
    merge_task = {
        "kind": "stage_merge",
        "source": source,
        "stage": f"{primary_stage}+{secondary_stage}",
        "kwargs": {
            "source": source,
            "input_root": input_root,
            "output_root": output_root,
            "reports_dir": reports_dir,
            "animestudio_exe": animestudio_exe,
            "animestudio_dummy_dlls": animestudio_dummy_dlls,
            "mono_behaviour_type_tree_priority": primary_options.get("mono_behaviour_type_tree_priority"),
            "stage": primary_stage,
            "export_type": primary_options.get("export_type"),
            "map_op": primary_options.get("map_op"),
            "map_type": primary_options.get("map_type"),
            "map_name": primary_options.get("map_name"),
            "names": primary_options.get("names"),
            "containers": primary_options.get("containers"),
            "filter_data": primary_options.get("filter_data"),
            "types": primary_types,
            "command_name": attempt.get("command_name"),
            "secondary_export": secondary_export,
        },
    }
    run_animestudio_call_tasks([merge_task], jobs=1, call_pool=call_pool)
    result = merge_task["result"]
    attempt["ran_this_run"] = True
    attempt["returncode"] = result.returncode
    attempt["stdout_log"] = result.stdout_log
    attempt["stderr_log"] = result.stderr_log
    mark_animestudio_stage_plan_from_merge(primary_plan, attempt, "primary", attempt["primary_items"], result)
    mark_animestudio_stage_plan_from_merge(secondary_plan, attempt, "secondary", attempt["secondary_items"], result)
    return [result]


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
    type_job_mode: str,
    call_pool: AnimeStudioCallPool | None = None,
) -> list[CommandResult]:
    options = plan["options"]
    runnable_items = animestudio_plan_runnable_items(plan)
    if not runnable_items:
        plan["command_results"] = []
        plan["succeeded_items"] = []
        plan["failed_items"] = []
        return []

    all_results: list[CommandResult] = []
    succeeded: list[str] = []
    failed: list[str] = []
    normal_items: list[dict[str, Any]] = []
    asset_works: list[dict[str, Any]] = []

    shared_asset_cache: dict[str, Any] | None = None
    if stage == "convert_by_type" and bool(options.get("asset_cache_enabled", True)):
        shared_asset_cache = load_animestudio_asset_cache(animestudio_asset_cache_path(output_root))

    if stage != "maps":
        for item in runnable_items:
            asset_work = prepare_animestudio_asset_shards(
                source=source,
                output_root=output_root,
                stage=stage,
                plan=plan,
                runnable_items=[item],
                jobs=jobs,
                asset_cache=shared_asset_cache,
            )
            if asset_work is None:
                normal_items.append(item)
            else:
                asset_works.append(asset_work)
    else:
        normal_items = list(runnable_items)

    pending_asset_works: list[dict[str, Any]] = []
    for asset_work in asset_works:
        has_tasks, item_succeeded, item_failed = begin_animestudio_asset_shard_work(
            source=source,
            output_root=output_root,
            stage=stage,
            asset_work=asset_work,
        )
        succeeded.extend(item_succeeded)
        failed.extend(item_failed)
        if has_tasks:
            pending_asset_works.append(asset_work)

    auto_sequential_type_jobs = (
        stage == "json_by_type"
        and type_job_mode == "auto"
        and not options.get("asset_map_filter")
        and len(normal_items) > 1
    )
    merge_normal_items = should_merge_animestudio_type_jobs(
        stage,
        normal_items,
        type_job_mode,
        asset_map_filter=bool(options.get("asset_map_filter")),
    )
    task_groups: list[list[dict[str, Any]]] = []
    normal_task_groups: list[dict[str, Any]] = []

    def normal_task_kwargs(
        item_names: list[str],
        type_specs: tuple[str, ...],
        command_name: str | None,
    ) -> dict[str, Any]:
        return {
            "source": source,
            "input_root": input_root,
            "output_root": output_root,
            "reports_dir": reports_dir,
            "animestudio_exe": animestudio_exe,
            "animestudio_dummy_dlls": animestudio_dummy_dlls,
            "mono_behaviour_type_tree_priority": options.get("mono_behaviour_type_tree_priority"),
            "stage": stage,
            "export_type": options.get("export_type"),
            "map_op": options.get("map_op"),
            "map_type": options.get("map_type"),
            "map_name": options.get("map_name"),
            "names": options.get("names"),
            "containers": options.get("containers"),
            "filter_data": options.get("filter_data"),
            "types": type_specs,
            "command_name": command_name,
        }

    if normal_items and (stage == "maps" or len(normal_items) <= 1 or merge_normal_items):
        clear_animestudio_stage_outputs(output_root, source, stage, normal_items)
        if merge_normal_items:
            log(
                f"  animestudio stage {stage} for {source}: merging {len(normal_items)} type jobs "
                f"({', '.join(item['item_name'] for item in normal_items)})"
            )
        normal_type_specs = (
            plan.get("type_specs_to_run", ())
            if stage == "maps"
            else tuple(item["type_spec"] for item in normal_items if item.get("type_spec") is not None)
        )
        item_names = [item["item_name"] for item in normal_items]
        item_suffix = "merged" if len(normal_items) > 1 else item_names[0]
        task = {
            "kind": "merged_types" if len(normal_items) > 1 else "type",
            "source": source,
            "stage": stage,
            "item_name": item_suffix,
            "item_names": item_names,
            "items": normal_items,
            "kwargs": normal_task_kwargs(item_names, normal_type_specs, None),
        }
        normal_task_groups.append(task)
        task_groups.append([task])

    elif normal_items:
        for item in normal_items:
            clear_animestudio_stage_outputs(output_root, source, stage, [item])
            item_name = item["item_name"]
            type_spec = item["type_spec"]
            command_name = f"{source}_animestudio_{stage}_{animestudio_log_suffix(item_name)}"
            task = {
                "kind": "type",
                "source": source,
                "stage": stage,
                "item_name": item_name,
                "item_names": [item_name],
                "items": [item],
                "kwargs": normal_task_kwargs(
                    [item_name],
                    (type_spec,) if type_spec is not None else (),
                    command_name,
                ),
            }
            normal_task_groups.append(task)
            task_groups.append([task])

    for asset_work in pending_asset_works:
        type_spec = asset_work["type_spec"]
        type_name = asset_work["type_name"]
        shards = asset_work["shards"]
        log(
            f"  animestudio asset shards {stage}:{type_name} for {source}: "
            f"queueing {len(shards)} shard job(s)"
        )
        group: list[dict[str, Any]] = []
        for shard in shards:
            shard_index = int(shard["index"])
            command_name = (
                f"{source}_animestudio_{stage}_{animestudio_log_suffix(type_name)}_"
                f"shard{shard_index:02d}_of_{int(shard['count']):02d}"
            )
            group.append(
                {
                    "kind": "asset_shard",
                    "source": source,
                    "stage": stage,
                    "item_name": type_name,
                    "item_names": [asset_work["item"]["item_name"]],
                    "asset_work": asset_work,
                    "shard": shard,
                    "kwargs": {
                        "source": source,
                        "input_root": input_root,
                        "output_root": output_root,
                        "reports_dir": reports_dir,
                        "animestudio_exe": animestudio_exe,
                        "animestudio_dummy_dlls": animestudio_dummy_dlls,
                        "mono_behaviour_type_tree_priority": options.get("mono_behaviour_type_tree_priority"),
                        "stage": stage,
                        "export_type": options.get("export_type"),
                        "names": shard["names"],
                        "filter_data": shard["filter_data"],
                        "types": (type_spec,) if type_spec is not None else (),
                        "command_name": command_name,
                    },
                }
            )
        task_groups.append(group)

    call_tasks: list[dict[str, Any]] = []
    while any(task_groups):
        for group in task_groups:
            if group:
                call_tasks.append(group.pop(0))

    if len(call_tasks) > 1:
        for task in call_tasks:
            if task["kwargs"].get("command_name") is None:
                item_suffix = task["item_name"]
                task["kwargs"]["command_name"] = f"{source}_animestudio_{stage}_{animestudio_log_suffix(item_suffix)}"

    if call_tasks and auto_sequential_type_jobs:
        log(
            f"  animestudio stage {stage} for {source}: running {len(call_tasks)} "
            "broad type jobs sequentially for process isolation"
        )
        for task in call_tasks:
            run_animestudio_call_tasks([task], jobs=1, call_pool=call_pool)
    elif call_tasks:
        run_animestudio_call_tasks(call_tasks, jobs=jobs, call_pool=call_pool)

    for asset_work in pending_asset_works:
        item_results, item_succeeded, item_failed = finalize_animestudio_asset_shard_work(
            source=source,
            output_root=output_root,
            stage=stage,
            plan=plan,
            asset_work=asset_work,
        )
        all_results.extend(item_results)
        succeeded.extend(item_succeeded)
        failed.extend(item_failed)

    for task in normal_task_groups:
        result = task.get("result")
        if result is None:
            continue
        all_results.append(result)
        item_names = task["item_names"]
        if result.returncode == 0:
            succeeded.extend(item_names)
        else:
            failed.extend(item_names)

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

    def stage_file_count(stage_name: str) -> int:
        # Output counts are informational only. They are gathered here, once per
        # stage after the run, rather than during planning (the removed cache used
        # to compute them for free). A plan may still carry counts from elsewhere;
        # use those when present, otherwise do a single recursive walk.
        plan = stage_plans.get(stage_name)
        if plan is not None:
            counts = plan.get("item_file_counts")
            if isinstance(counts, dict) and counts:
                return sum(int(value) for value in counts.values())
        return count_files(animestudio_stage_dir(output_root, source, stage_name))

    result: dict[str, Any] = {
        "root": str(animestudio_source_root(output_root, source)),
        "source_fingerprint": source_fingerprint,
        "maps": {
            "output_root": str(animestudio_stage_dir(output_root, source, "maps")),
            "file_count": stage_file_count("maps"),
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
            "file_count": stage_file_count("convert_by_type"),
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
            "file_count": stage_file_count("json_by_type"),
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
        if plan and plan.get("stage_merge"):
            result[stage]["stage_merge"] = plan["stage_merge"]
        elif previous_stage.get("stage_merge"):
            result[stage]["stage_merge"] = previous_stage["stage_merge"]
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
    reports_runs_root = ensure_dir(reports_root / "runs")
    reports_dir = ensure_dir(reports_runs_root / report_run_id)
    legacy_reports_dir = output_root / "reports"
    structured_dumper = args.structured_dumper.resolve()
    animestudio = args.animestudio.resolve()
    selected_sources = ordered_unique(args.sources)
    selected_animestudio_stages = ordered_unique(args.animestudio_stages)
    structured_dump_plan = structured_dump_steps(args.structured_dump_mode)
    animestudio_stage_options = animestudio_stage_options_for_scope(args.animestudio_scope, args.animestudio_asset_mode)
    animestudio_asset_type_filter = normalize_animestudio_asset_type_filter(tuple(args.animestudio_asset_types))
    if animestudio_asset_type_filter and args.animestudio_scope == "story":
        raise SystemExit("--animestudio-asset-types applies only to asset or all AnimeStudio scopes")
    apply_animestudio_asset_type_filter(animestudio_stage_options, animestudio_asset_type_filter)
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
    if args.skip_animestudio:
        animestudio_stage_merge_feature = {
            "contract": "secondary_export_v1",
            "requested_mode": args.animestudio_stage_merge_mode,
            "effective_mode": "disabled",
            "primary_stage": ANIMESTUDIO_STAGE_MERGE_PRIMARY_STAGE,
            "secondary_stage": ANIMESTUDIO_STAGE_MERGE_SECONDARY_STAGE,
            "flags": dict(ANIMESTUDIO_SECONDARY_EXPORT_FLAGS),
            "supported": False,
            "probed": False,
            "reason": "AnimeStudio export is skipped",
        }
    else:
        animestudio_stage_merge_feature = detect_animestudio_stage_merge_feature(
            animestudio,
            args.animestudio_stage_merge_mode,
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
    if not args.skip_structured:
        log(f"  structured dump mode: {args.structured_dump_mode}")
        log(f"  structured dump plan: {describe_structured_dump_steps(structured_dump_plan)}")
    log(f"  vfs index: {'enabled' if vfs_index_enabled else 'disabled'}")
    log("  raw vfs export: disabled")
    log(f"  animestudio export: {'disabled' if args.skip_animestudio else 'enabled'}")
    log(f"  animestudio scope: {args.animestudio_scope}")
    log(f"  animestudio asset mode: {args.animestudio_asset_mode}")
    log(
        "  animestudio asset type filter: "
        f"{', '.join(sorted(animestudio_asset_type_filter)) if animestudio_asset_type_filter else 'none'}"
    )
    log(f"  animestudio stages: {', '.join(selected_animestudio_stages)}")
    log(f"  animestudio type job mode: {args.animestudio_type_job_mode}")
    log(
        "  animestudio stage merge mode: "
        f"{args.animestudio_stage_merge_mode} "
        f"(effective: {animestudio_stage_merge_feature.get('effective_mode')})"
    )
    if animestudio_stage_merge_feature.get("missing_flags") and args.animestudio_stage_merge_mode == "aggressive":
        log(
            "  animestudio stage merge disabled; missing CLI flags: "
            f"{', '.join(animestudio_stage_merge_feature.get('missing_flags') or [])}"
        )
    log(f"  animestudio jobs: {animestudio_jobs}")
    log(
        "  animestudio asset shards: "
        f"{args.animestudio_shards if args.animestudio_shards else f'auto ({animestudio_jobs})'}"
    )
    log("  animestudio asset cache: removed (every run re-exports)")
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
        if animestudio_mono_behaviour_type_tree_priority == "ScriptFirst":
            log("  warning: script-first requested without DummyDlls; AnimeStudio will use serialized fallback behavior")
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
    # The cross-run AnimeStudio cache has been removed. Signatures and the type
    # manifest only ever fed cache keys, so they are no longer computed or read.
    animestudio_cli_signature = None
    animestudio_dummy_dll_signature = None
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
        "asset_type_filter": sorted(animestudio_asset_type_filter),
        "webui_texture_name_filter": str(webui_texture_name_filter) if webui_texture_name_filter else None,
        "webui_texture_name_filter_signature": webui_texture_name_filter_signature,
        "mono_behaviour_type_tree_priority": animestudio_mono_behaviour_type_tree_priority,
        "jobs": animestudio_jobs,
        "type_job_mode": args.animestudio_type_job_mode,
        "stage_merge_mode": args.animestudio_stage_merge_mode,
        "stage_merge_feature": animestudio_stage_merge_feature,
        "stage_merge_attempts": [],
        "asset_shards": args.animestudio_shards,
        "asset_cache_enabled": False,
        "cache_removed": True,
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

        current_vfs_index_paths = [
            vfs_index_path(output_root, source, block_name)
            for block_name, _cli_block_name in VFS_INDEX_BLOCKS
        ]
        if vfs_index_enabled and not args.report_only:
            for block_name, cli_block_name in VFS_INDEX_BLOCKS:
                current_vfs_index_path = vfs_index_path(output_root, source, block_name)
                log(f"  vfs {block_name} index path: {current_vfs_index_path}")
                cmd = [
                    str(structured_dumper),
                    "vfs-index",
                    "-s",
                    str(source_root),
                    "-o",
                    str(current_vfs_index_path),
                    "-b",
                    cli_block_name,
                ]
                fallback_source = "Persistent" if source == "StreamingAssets" else "StreamingAssets"
                fallback_root = game_root / fallback_source
                if fallback_root.exists():
                    cmd.extend(["--fallback-assets", str(fallback_root)])
                result = run_logged_command(vfs_index_command_name(source, block_name), cmd, ROOT, source_report_dir)
                command_results.append(result)
                command_results_by_name[result.name] = result

        if vfs_index_enabled or any(path.exists() for path in current_vfs_index_paths):
            vfs_index_summary[source] = summarize_vfs_indexes(output_root, source, command_results_by_name)
            if vfs_index_summary[source].get("exists"):
                log(
                    f"  vfs index summary {source}: "
                    f"files={vfs_index_summary[source].get('file_count')} "
                    f"chunks={vfs_index_summary[source].get('chunk_count')} "
                    f"missing_chunks={vfs_index_summary[source].get('missing_chunk_count')}"
                )

        if not args.skip_structured and not args.report_only:
            structured_out = reset_structured_output_dir(output_root, source)
            log(f"  structured output dir: {structured_out}")
            fallback_source = "Persistent" if source == "StreamingAssets" else "StreamingAssets"
            fallback_root = game_root / fallback_source
            if fallback_root is not None and fallback_root.exists():
                log(f"  using fallback assets from {fallback_root}")
            for step in structured_dump_plan:
                command_name = structured_dump_command_name(source, step, len(structured_dump_plan))
                cmd = [str(structured_dumper), "dump", "-s", str(source_root), "-o", str(structured_out)]
                for block_type in step.get("block_types") or ():
                    cmd.extend(["-b", str(block_type)])
                for file_regex in step.get("file_regexes") or ():
                    cmd.extend(["--file-regex", str(file_regex)])
                if fallback_root is not None and fallback_root.exists():
                    cmd.extend(["--fallback-assets", str(fallback_root)])
                result = run_logged_command(command_name, cmd, ROOT, source_report_dir)
                command_results.append(result)
                command_results_by_name[result.name] = result

        if not args.skip_structured:
            previous_structured = (previous_summary.get("structured") or {}).get(source, {})
            structured_steps: list[dict[str, Any]] = []
            stdout_parts: list[str] = []
            stderr_parts: list[str] = []
            returncodes: list[int] = []
            for step in structured_dump_plan:
                command_name = structured_dump_command_name(source, step, len(structured_dump_plan))
                stdout_log = source_report_dir / f"{command_name}.stdout.log"
                stderr_log = source_report_dir / f"{command_name}.stderr.log"
                stdout_text = stdout_log.read_text(encoding="utf-8") if stdout_log.exists() else ""
                stderr_text = stderr_log.read_text(encoding="utf-8") if stderr_log.exists() else ""
                stdout_parts.append(stdout_text)
                stderr_parts.append(stderr_text)
                current_structured_step = command_results_by_name.get(command_name)
                if current_structured_step is not None:
                    returncodes.append(current_structured_step.returncode)
                structured_steps.append(
                    {
                        "name": step["name"],
                        "command_name": command_name,
                        "returncode": current_structured_step.returncode if current_structured_step is not None else None,
                        "block_types": list(step.get("block_types") or ["all"]),
                        "file_regexes": list(step.get("file_regexes") or ()),
                        "warning_failure_count": parse_warning_failure_count(stdout_text),
                        "stdout_log": str(stdout_log),
                        "stderr_log": str(stderr_log),
                    }
                )
            stderr_text = "\n".join(part for part in stderr_parts if part)
            stdout_text = "\n".join(part for part in stdout_parts if part)
            all_failures = parse_structured_failures(stderr_text)
            actual_failures, manifest_only = split_structured_failures(source, all_failures)
            structured_failures_by_source[source] = actual_failures
            structured_manifest_by_source[source] = manifest_only
            current_structured_returncode = next((code for code in returncodes if code != 0), returncodes[-1] if returncodes else None)
            structured_summary[source] = {
                "output_root": str(
                    structured_output_dir(output_root, source)
                    if returncodes
                    else resolve_existing_structured_output_dir(output_root, source)
                ),
                "returncode": (
                    current_structured_returncode if current_structured_returncode is not None else previous_structured.get("returncode")
                ),
                "dump_mode": args.structured_dump_mode,
                "dump_plan": describe_structured_dump_steps(structured_dump_plan),
                "steps": structured_steps,
                "block_types": sorted(
                    {str(block_type) for step in structured_steps for block_type in step.get("block_types", [])}
                ),
                "warning_failure_count": sum(int(step.get("warning_failure_count") or 0) for step in structured_steps),
                "actual_failure_count": len(actual_failures),
                "manifest_reference_count": len(manifest_only),
                "stdout_log": "; ".join(step["stdout_log"] for step in structured_steps),
                "stderr_log": "; ".join(step["stderr_log"] for step in structured_steps),
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
                options["asset_cache_enabled"] = False
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

            stage_merge_attempt = build_animestudio_stage_merge_attempt(
                source=source,
                output_root=output_root,
                selected_stages=selected_animestudio_stages,
                stage_plans=animestudio_stage_plans,
                stage_merge_feature=animestudio_stage_merge_feature,
            )
            if stage_merge_attempt is not None:
                animestudio_summary.setdefault("stage_merge_attempts", []).append(stage_merge_attempt)
                if stage_merge_attempt.get("mergeable"):
                    log(
                        f"  animestudio stage merge for {source}: will merge "
                        f"{stage_merge_attempt['primary_stage']} + {stage_merge_attempt['secondary_stage']} "
                        f"({stage_merge_attempt['reason']})"
                    )
                else:
                    log(f"  animestudio stage merge for {source}: split stages ({stage_merge_attempt['reason']})")

            if not args.report_only:
                merged_stage_names: set[str] = set()

                def remember_animestudio_results(stage_results: list[CommandResult]) -> None:
                    command_results.extend(stage_results)
                    for result in stage_results:
                        command_results_by_name[result.name] = result

                def finish_animestudio_stage(stage: str) -> None:
                    plan = animestudio_stage_plans[stage]
                    succeeded_items = set(plan.get("succeeded_items", []))
                    if succeeded_items:
                        write_animestudio_report_only_asset_statuses(
                            output_root=output_root,
                            source=source,
                            stage=stage,
                            plan=plan,
                            item_names=succeeded_items,
                            skip_existing_types=True,
                        )
                    failed_items = plan.get("failed_items", [])
                    if failed_items:
                        log(f"  animestudio stage {stage} for {source} failed items: {', '.join(failed_items)}")

                def run_stage_driver(stage: str, call_pool: AnimeStudioCallPool) -> list[CommandResult]:
                    plan = animestudio_stage_plans[stage]
                    log(f"  animestudio stage {stage} for {source}: running {', '.join(plan['run_items'])}")
                    return run_animestudio_stage_plan(
                        source=source,
                        input_root=source_root,
                        output_root=output_root,
                        reports_dir=source_report_dir,
                        animestudio_exe=animestudio,
                        animestudio_dummy_dlls=animestudio_dummy_dlls,
                        stage=stage,
                        plan=plan,
                        jobs=animestudio_jobs,
                        type_job_mode=args.animestudio_type_job_mode,
                        call_pool=call_pool,
                    )

                with AnimeStudioCallPool(animestudio_jobs) as animestudio_call_pool:
                    log(f"  animestudio call pool for {source}: workers={animestudio_call_pool.max_workers}")

                    if "maps" in selected_animestudio_stages:
                        maps_plan = animestudio_stage_plans["maps"]
                        if maps_plan["should_run"]:
                            stage_results = run_stage_driver("maps", animestudio_call_pool)
                            remember_animestudio_results(stage_results)
                            finish_animestudio_stage("maps")
                        else:
                            log(f"  animestudio stage maps for {source}: cache hit, skipping")

                    if stage_merge_attempt and stage_merge_attempt.get("mergeable"):
                        stage_results = run_animestudio_stage_merge_plan(
                            source=source,
                            input_root=source_root,
                            output_root=output_root,
                            reports_dir=source_report_dir,
                            animestudio_exe=animestudio,
                            animestudio_dummy_dlls=animestudio_dummy_dlls,
                            stage_plans=animestudio_stage_plans,
                            attempt=stage_merge_attempt,
                            call_pool=animestudio_call_pool,
                        )
                        remember_animestudio_results(stage_results)
                        merged_stage_names.update(
                            (stage_merge_attempt["primary_stage"], stage_merge_attempt["secondary_stage"])
                        )
                        for stage in merged_stage_names:
                            finish_animestudio_stage(stage)

                    stages_to_run: list[str] = []
                    for stage in selected_animestudio_stages:
                        if stage == "maps" or stage in merged_stage_names:
                            continue
                        plan = animestudio_stage_plans[stage]
                        if not plan["should_run"]:
                            log(f"  animestudio stage {stage} for {source}: cache hit, skipping")
                            continue
                        stages_to_run.append(stage)

                    if len(stages_to_run) > 1:
                        log(
                            f"  animestudio stage drivers for {source}: "
                            f"sharing {animestudio_call_pool.max_workers} workers across {', '.join(stages_to_run)}"
                        )
                    if len(stages_to_run) == 1:
                        stage = stages_to_run[0]
                        stage_results = run_stage_driver(stage, animestudio_call_pool)
                        remember_animestudio_results(stage_results)
                        finish_animestudio_stage(stage)
                    elif stages_to_run:
                        with ThreadPoolExecutor(max_workers=len(stages_to_run)) as stage_executor:
                            future_to_stage = {
                                stage_executor.submit(run_stage_driver, stage, animestudio_call_pool): stage
                                for stage in stages_to_run
                            }
                            for future in as_completed(future_to_stage):
                                stage = future_to_stage[future]
                                stage_results = future.result()
                                remember_animestudio_results(stage_results)
                                finish_animestudio_stage(stage)
            else:
                for stage in selected_animestudio_stages:
                    plan = animestudio_stage_plans[stage]
                    write_animestudio_report_only_asset_statuses(
                        output_root=output_root,
                        source=source,
                        stage=stage,
                        plan=plan,
                    )
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
            block_infos = info.get("blocks") if isinstance(info, dict) else None
            if isinstance(block_infos, dict):
                for block_name in info.get("block_names", block_infos.keys()):
                    block_info = block_infos.get(block_name, {})
                    md_lines.append(
                        f"  - `{block_name}`: exists=`{block_info.get('exists')}`, "
                        f"files=`{block_info.get('file_count')}`, "
                        f"chunks=`{block_info.get('chunk_count')}`, "
                        f"missing_chunks=`{block_info.get('missing_chunk_count')}`"
                    )
                    md_lines.append(f"    index: `{block_info.get('index_path')}`")
                    if block_info.get("stdout_log"):
                        md_lines.append(f"    stdout: `{block_info.get('stdout_log')}`")
                    if block_info.get("stderr_log"):
                        md_lines.append(f"    stderr: `{block_info.get('stderr_log')}`")
            else:
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
                f"mode=`{info.get('dump_mode')}`, "
                f"actual_failures=`{info.get('actual_failure_count')}`, "
                f"manifest_refs=`{info.get('manifest_reference_count')}`"
            )
            md_lines.append(f"  plan: `{info.get('dump_plan') or 'unknown'}`")
            for step in info.get("steps") or []:
                block_types = step.get("block_types") or []
                block_type_text = ", ".join(str(item) for item in block_types) or "unknown"
                file_regexes = step.get("file_regexes") or []
                filter_text = f"; file_regexes={', '.join(str(item) for item in file_regexes)}" if file_regexes else ""
                md_lines.append(
                    f"  step `{step.get('name')}`: returncode=`{step.get('returncode')}`, "
                    f"block_types=`{block_type_text}`{filter_text}"
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
        md_lines.append(
            "- Asset type filter: "
            f"`{', '.join(sorted(animestudio_asset_type_filter)) if animestudio_asset_type_filter else 'none'}`"
        )
        md_lines.append(f"- Selected stages: `{', '.join(selected_animestudio_stages)}`")
        md_lines.append(f"- Type job mode: `{args.animestudio_type_job_mode}`")
        stage_merge_feature = animestudio_summary.get("stage_merge_feature") or {}
        md_lines.append(
            f"- Stage merge mode: `{args.animestudio_stage_merge_mode}` "
            f"(effective `{stage_merge_feature.get('effective_mode')}`)"
        )
        if stage_merge_feature.get("missing_flags") and args.animestudio_stage_merge_mode == "aggressive":
            md_lines.append(
                "- Stage merge missing CLI flags: "
                f"`{', '.join(stage_merge_feature.get('missing_flags') or [])}`"
            )
        md_lines.append(f"- Parallel jobs: `{animestudio_jobs}`")
        md_lines.append(
            "- Asset shards: "
            f"`{args.animestudio_shards if args.animestudio_shards else f'auto ({animestudio_jobs})'}`"
        )
        md_lines.append("- Asset cache: `removed` (every run re-exports)")
        md_lines.append(f"- MonoBehaviour TypeTree priority: `{animestudio_mono_behaviour_type_tree_priority}`")
        md_lines.append(
            f"- DummyDlls: `{animestudio_dummy_dlls}`"
            if animestudio_dummy_dlls
            else "- DummyDlls: `not configured`"
        )
        if animestudio_dummy_dll_source:
            md_lines.append(f"- DummyDll source: `{animestudio_dummy_dll_source}`")
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
                stage_merge = stage_info.get("stage_merge") or {}
                if stage_merge:
                    md_lines.append(
                        "    stage merge: "
                        f"role=`{stage_merge.get('role')}`, "
                        f"paired_stage=`{stage_merge.get('paired_stage')}`, "
                        f"command=`{stage_merge.get('command_name')}`, "
                        f"asset_cache_bypassed=`{stage_merge.get('asset_cache_bypassed')}`"
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
                        f"missing_unique=`{asset_cache.get('missing_unique_output_count', 0)}`, "
                        f"allowed_missing=`{asset_cache.get('allowed_missing_output_count', 0)}`, "
                        f"alternate_names=`{asset_cache.get('alternate_name_output_count', asset_cache.get('name_mismatch_output_count', 0))}`, "
                        f"cross_ab_paths=`{asset_cache.get('cross_ab_output_collision_group_count', 0)}`, "
                        f"shared_refs=`{asset_cache.get('shared_output_reference_group_count', 0)}`, "
                        f"same_asset_refs=`{asset_cache.get('same_asset_id_output_reference_group_count', 0)}`, "
                        f"raw_hash_collisions=`{asset_cache.get('raw_hash_output_collision_group_count', 0)}`, "
                        f"identity_collisions=`{asset_cache.get('identity_output_collision_group_count', 0)}`, "
                        f"uncertain_collisions=`{asset_cache.get('uncertain_output_collision_group_count', asset_cache.get('cross_ab_output_collision_group_count', 0))}`, "
                        f"dirty_abs=`{asset_cache.get('dirty_source_group_count', 0)}`, "
                        f"export_errors=`{asset_cache.get('export_error_count', 0)}`, "
                        f"prepare_seconds=`{asset_cache.get('prepare_seconds')}`, "
                        f"status_manifest=`{asset_cache.get('manifest_path')}`"
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
                        f"metadata_only_json=`{issues.get('metadata_only_json_count', 0)}`, "
                        f"partial_mono=`{issues.get('partial_mono_behaviour_count', 0)}`, "
                        f"animator_no_output=`{issues.get('animator_no_output_count', 0)}`, "
                        f"animator_no_mesh=`{issues.get('animator_no_mesh_count', 0)}`"
                    )
                    samples = issues.get("story_like_export_error_samples") or issues.get("export_error_samples") or []
                    for sample in samples[:3]:
                        md_lines.append(
                            "    export error sample: "
                            f"`{sample.get('asset')}`"
                            + (f" - {sample.get('reason')}" if sample.get("reason") else "")
                        )
                    if not samples:
                        for sample in (issues.get("partial_mono_behaviour_samples") or [])[:3]:
                            md_lines.append(
                                "    partial MonoBehaviour sample: "
                                f"`{sample.get('asset')}`"
                                + (f" - {sample.get('exception')}: {sample.get('reason')}" if sample.get("exception") else "")
                            )
                    if not samples:
                        for sample in (issues.get("metadata_only_json_samples") or [])[:3]:
                            md_lines.append(
                                "    metadata-only sample: "
                                f"`{sample.get('asset')}`"
                                + (f" - {sample.get('exception')}" if sample.get("exception") else "")
                            )
                    if not samples:
                        for sample in (issues.get("animator_no_output_samples") or [])[:3]:
                            md_lines.append(
                                "    animator no-output sample: "
                                f"`{sample.get('name')}`"
                                + (f" - {sample.get('reason')}" if sample.get("reason") else "")
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
    prune_export_report_runs(reports_runs_root, reports_dir, args.report_runs_to_keep)
    failed_entry_count = sum(1 for line in failed_lines if line and not line.startswith("["))
    manifest_entry_count = sum(1 for line in manifest_lines if line and not line.startswith("["))
    log(
        "finished full export: "
        f"commands={len(summary['commands'])} "
        f"command_failures={len(command_failures)} "
        f"failed_entries={failed_entry_count} "
        f"manifest_entries={manifest_entry_count}"
    )

    brief_summary = {
        "summary_json": str(reports_root / "export_full_summary.json"),
        "summary_md": str(latest_summary_md),
        "commands": len(summary["commands"]),
        "command_failures": len(command_failures),
        "failed_entries": failed_entry_count,
        "manifest_entries": manifest_entry_count,
    }
    print(json.dumps(brief_summary, indent=2, ensure_ascii=False))
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
