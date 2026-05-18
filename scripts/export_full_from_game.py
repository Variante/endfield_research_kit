from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAME_ROOT = Path(r"D:\Program Files\Endfield Game\Endfield_Data")
DEFAULT_OUTPUT = ROOT / "export_full"
DEFAULT_REPORTS = ROOT / "reports"
DEFAULT_FLUFFY = ROOT / "tools" / "fluffy-dumper-src" / "target" / "release" / "fluffy-dumper.exe"
DEFAULT_ANIMESTUDIO = ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"
SOURCES = ("StreamingAssets", "Persistent")
ANIMESTUDIO_STAGES = ("maps", "convert_by_type", "json_by_type")
ANIMESTUDIO_SCOPES = ("story", "assets", "all")
ANIMESTUDIO_GAME = "ArknightsEndfield"
ANIMESTUDIO_LOGGER_FLAGS = ("Warning", "Error")
ANIMESTUDIO_DEFAULT_JOBS = 4
ANIMESTUDIO_MANIFEST_SCHEMA_VERSION = 2
ANIMESTUDIO_MANIFEST_MAP_ITEM = "__maps__"
ANIMESTUDIO_MANIFEST_MAP_LABEL = "maps"
SOURCE_NAME_SET = frozenset(source.lower() for source in SOURCES)
# Asset maps for Endfield have no GameObject, AudioClip, VideoClip,
# MovieTexture, or MiHoYoBinData entries, so the WebUI export skips them.
ANIMESTUDIO_CONVERT_TYPES = (
    "Texture2D:Both",
    "Shader:Both",
    "TextAsset:Both",
    "Font:Both",
    "Mesh:Both",
    "Sprite:Both",
    "Animator:Both",
    "AnimationClip:Both",
)
ANIMESTUDIO_STORY_JSON_TYPES = (
    "TextAsset:Both",
    "MonoBehaviour:Both",
    "PlayableDirector:Both",
)
ANIMESTUDIO_JSON_TYPES = (
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


def animestudio_stage_options_for_scope(scope: str) -> dict[str, dict[str, Any]]:
    json_types = ANIMESTUDIO_STORY_JSON_TYPES if scope == "story" else ANIMESTUDIO_JSON_TYPES
    convert_types: tuple[str, ...] = () if scope == "story" else ANIMESTUDIO_CONVERT_TYPES
    return {
        "maps": {"map_op": "Both", "map_type": "JSON"},
        "convert_by_type": {"export_type": "Convert", "types": convert_types},
        "json_by_type": {"export_type": "JSON", "types": json_types},
    }


def animestudio_output_file_count(output_root: Path, source: str, stage: str, type_spec: str | None) -> int:
    stage_root = animestudio_stage_dir(output_root, source, stage)
    if stage == "maps":
        return count_files(stage_root)
    return count_files(stage_root / animestudio_type_name(type_spec))


def build_animestudio_stage_signature(stage: str, options: dict[str, Any], type_spec: str | None) -> dict[str, Any]:
    return {
        "stage": stage,
        "type_spec": type_spec,
        "export_type": options.get("export_type"),
        "map_op": options.get("map_op"),
        "map_type": options.get("map_type"),
        "map_name": options.get("map_name"),
        "group_assets": "ByType",
        "game": ANIMESTUDIO_GAME,
        "file_naming": "path_id_suffix_v1",
        "logger_flags": list(ANIMESTUDIO_LOGGER_FLAGS),
    }


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
        type=Path,
        default=DEFAULT_FLUFFY,
        help="Path to fluffy-dumper executable",
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
        help="Optional DummyDll directory passed to AnimeStudio for MonoBehaviour schema recovery",
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
            "`assets`/`all` include converted image/model/animation assets and the full JSON metadata set."
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
            "Maximum parallel AnimeStudio CLI processes for per-type export "
            f"(default: {ANIMESTUDIO_DEFAULT_JOBS}; use 1 for serial execution)."
        ),
    )
    parser.add_argument(
        "--skip-structured",
        action="store_true",
        help="Skip fluffy-dumper structured exports",
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


def resolve_animestudio_dummy_dlls(explicit: Path | None, game_root: Path) -> Path | None:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.extend(
        [
            game_root / "DummyDll",
            game_root.parent / "DummyDll",
            ROOT / "tools" / "DummyDll",
            ROOT / "tools" / "dummy_dlls",
        ]
    )

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if looks_like_dummy_dll_dir(candidate):
            return candidate.resolve()
    return None


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
    stage: str,
    export_type: str | None = None,
    map_op: str | None = None,
    map_type: str | None = None,
    map_name: str | None = None,
    types: tuple[str, ...] = (),
    command_name: str | None = None,
) -> CommandResult:
    work_dir = ensure_dir(animestudio_work_dir(output_root))
    stage_out = ensure_dir(animestudio_stage_dir(output_root, source, stage))
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
    if map_op is not None:
        cmd.extend(["--map_op", map_op])
    if map_type is not None:
        cmd.extend(["--map_type", map_type])
    if map_name is not None:
        cmd.extend(["--map_name", map_name])
    if types:
        cmd.append("--types")
        cmd.extend(types)
    name = command_name or f"{source}_animestudio_{stage}"
    return run_logged_command(name, cmd, work_dir, reports_dir, stream_output=True)


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
        f"Parallel AnimeStudio stage: {source} {stage}",
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
        f"Parallel AnimeStudio stage failures: {source} {stage}",
        f"failed_processes: {len(failed)}",
    ]
    for result in failed:
        err_lines.append(f"{result.name}\treturncode={result.returncode}\tstderr={result.stderr_log}")
    stderr_log.write_text("\n".join(err_lines), encoding="utf-8")
    return str(stdout_log), str(stderr_log)


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

    if stage == "maps" or jobs <= 1 or len(runnable_items) <= 1:
        clear_animestudio_stage_outputs(output_root, source, stage, runnable_items)
        result = run_animestudio_stage(
            source=source,
            input_root=input_root,
            output_root=output_root,
            reports_dir=reports_dir,
            animestudio_exe=animestudio_exe,
            animestudio_dummy_dlls=animestudio_dummy_dlls,
            stage=stage,
            export_type=options.get("export_type"),
            map_op=options.get("map_op"),
            map_type=options.get("map_type"),
            map_name=options.get("map_name"),
            types=plan.get("type_specs_to_run", ()),
        )
        succeeded = list(plan.get("run_items", [])) if result.returncode == 0 else []
        failed = [] if result.returncode == 0 else list(plan.get("run_items", []))
        plan["command_results"] = [result]
        plan["succeeded_items"] = succeeded
        plan["failed_items"] = failed
        plan["stdout_log"] = result.stdout_log
        plan["stderr_log"] = result.stderr_log
        return [result]

    max_workers = min(max(1, jobs), len(runnable_items))
    log(f"  animestudio stage {stage} for {source}: launching {len(runnable_items)} type jobs with max_workers={max_workers}")
    result_by_item: dict[str, CommandResult] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {}
        for item in runnable_items:
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
                stage=stage,
                export_type=options.get("export_type"),
                map_op=options.get("map_op"),
                map_type=options.get("map_type"),
                map_name=options.get("map_name"),
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

    ordered_results = [
        result_by_item[item["item_name"]]
        for item in runnable_items
        if item["item_name"] in result_by_item
    ]
    succeeded = [
        item["item_name"]
        for item in runnable_items
        if item["item_name"] in result_by_item and result_by_item[item["item_name"]].returncode == 0
    ]
    failed = [
        item["item_name"]
        for item in runnable_items
        if item["item_name"] in result_by_item and result_by_item[item["item_name"]].returncode != 0
    ]
    stdout_log, stderr_log = write_animestudio_parallel_log_index(source, stage, reports_dir, ordered_results)
    plan["command_results"] = ordered_results
    plan["succeeded_items"] = succeeded
    plan["failed_items"] = failed
    plan["stdout_log"] = stdout_log
    plan["stderr_log"] = stderr_log
    return ordered_results


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
        if current is not None:
            result[stage]["returncode"] = current.returncode
            result[stage]["stdout_log"] = current.stdout_log
            result[stage]["stderr_log"] = current.stderr_log
        elif plan_results:
            result[stage]["returncode"] = 0 if all(item.returncode == 0 for item in plan_results) else 1
            result[stage]["stdout_log"] = plan.get("stdout_log", result[stage].get("stdout_log"))
            result[stage]["stderr_log"] = plan.get("stderr_log", result[stage].get("stderr_log"))
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
    fluffy = args.fluffy.resolve()
    animestudio = args.animestudio.resolve()
    selected_sources = ordered_unique(args.sources)
    selected_animestudio_stages = ordered_unique(args.animestudio_stages)
    animestudio_stage_options = animestudio_stage_options_for_scope(args.animestudio_scope)
    refresh_selectors = ordered_unique(tuple(args.animestudio_refresh_types))
    if args.animestudio_jobs < 1:
        raise SystemExit("--animestudio-jobs must be at least 1")
    animestudio_jobs = args.animestudio_jobs

    if not game_root.exists():
        raise SystemExit(f"Game root not found: {game_root}")
    if not fluffy.exists() and not args.skip_structured:
        raise SystemExit(f"fluffy-dumper not found: {fluffy}")
    if not animestudio.exists() and not args.skip_animestudio:
        raise SystemExit(f"AnimeStudio CLI not found: {animestudio}")
    if args.animestudio_dummy_dlls is not None and not looks_like_dummy_dll_dir(args.animestudio_dummy_dlls):
        raise SystemExit(f"AnimeStudio DummyDll directory not found or empty: {args.animestudio_dummy_dlls}")

    animestudio_dummy_dlls = resolve_animestudio_dummy_dlls(args.animestudio_dummy_dlls, game_root)

    ensure_dir(output_root)
    log("starting full export")
    log(f"  game root: {game_root}")
    log(f"  output root: {output_root}")
    log(f"  reports root: {reports_root}")
    log(f"  reports run id: {report_run_id}")
    log(f"  reports run dir: {reports_dir}")
    log(f"  selected sources: {', '.join(selected_sources)}")
    log(f"  structured export: {'disabled' if args.skip_structured else 'enabled'}")
    log("  raw vfs export: disabled")
    log(f"  animestudio export: {'disabled' if args.skip_animestudio else 'enabled'}")
    log(f"  animestudio scope: {args.animestudio_scope}")
    log(f"  animestudio stages: {', '.join(selected_animestudio_stages)}")
    log(f"  animestudio jobs: {animestudio_jobs}")
    log(f"  animestudio refresh selectors: {', '.join(refresh_selectors) if refresh_selectors else 'none'}")
    log(f"  animestudio dummy dlls: {animestudio_dummy_dlls if animestudio_dummy_dlls else 'not configured'}")
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
        "dummy_dll_signature": animestudio_dummy_dll_signature,
        "game": ANIMESTUDIO_GAME,
        "scope": args.animestudio_scope,
        "jobs": animestudio_jobs,
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

        if not args.skip_structured and not args.report_only:
            structured_out = structured_output_dir(output_root, source)
            log(f"  structured output dir: {structured_out}")
            cmd = [str(fluffy), "dump", "-s", str(source_root), "-o", str(structured_out)]
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
                if stage == "maps":
                    options["map_name"] = f"endfield_{source.lower()}_assets"
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

    summary = {
        "game_root": str(game_root),
        "output_root": str(output_root),
        "reports_root": str(reports_root),
        "reports_run_root": str(reports_dir),
        "report_run_id": report_run_id,
        "sources_selected": list(selected_sources),
        "source_sizes": source_sizes,
        "inventory": inventory_summary,
        "commands": [asdict(item) for item in command_results] or previous_summary.get("commands", []),
        "structured": structured_summary,
        "raw_vfs": raw_summary,
        "animestudio": animestudio_summary,
        "failed_to_decode_txt": str(failed_txt),
        "manifest_reference_missing_txt": str(manifest_txt),
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
        md_lines.append(f"- Selected stages: `{', '.join(selected_animestudio_stages)}`")
        md_lines.append(f"- Parallel jobs: `{animestudio_jobs}`")
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
        f"failed_entries={sum(1 for line in failed_lines if line and not line.startswith('['))} "
        f"manifest_entries={sum(1 for line in manifest_lines if line and not line.startswith('['))}"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
