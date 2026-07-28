"""Small shared helpers for WebUI builder scripts."""
from __future__ import annotations

import json
import fnmatch
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "export_full"
OUT_DIR = ROOT / "webui" / "data"
LANG_DIR = OUT_DIR / "lang"
ASSET_DIR = OUT_DIR / "assets"
REPORTS_DIR = ROOT / "reports"
EXPORT_REPORTS_DIR = REPORTS_DIR / "export"
STORY_REPORTS_DIR = REPORTS_DIR / "story" / "build"
STORY_RECOVERY_REPORTS_DIR = REPORTS_DIR / "story" / "recovery"
STORY_OPTION_REPORTS_DIR = STORY_RECOVERY_REPORTS_DIR / "options"
UPDATES_REPORTS_DIR = REPORTS_DIR / "updates"
ASSET_REPORTS_DIR = REPORTS_DIR / "assets"
SAFE_REPORT_REPLACEMENTS = str.maketrans({
    "\\": "_",
    "/": "_",
    ":": "_",
    "*": "_",
    "?": "_",
    "\"": "_",
    "<": "_",
    ">": "_",
    "|": "_",
    ",": "_",
})
PATH_ID_EXPORT_STEM_RE = re.compile(r"^(?P<base>.+)_p(?P<path_id>[0-9A-Fa-f]{16})$")
PATH_ID_EXPORT_SOURCE_FAMILIES = frozenset({"streamingassets", "persistent"})


@lru_cache(maxsize=None)
def _read_bytes_cached_absolute(path_text: str) -> bytes:
    return Path(path_text).read_bytes()


def read_bytes_cached(path: str | Path) -> bytes:
    """Read one immutable build input once per Python process."""
    normalized = os.path.normcase(os.path.abspath(os.fspath(path)))
    export_root = os.path.normcase(os.path.abspath(os.fspath(EXPORT_ROOT)))
    if normalized != export_root and not normalized.startswith(export_root + os.sep):
        return Path(normalized).read_bytes()
    return _read_bytes_cached_absolute(normalized)


@lru_cache(maxsize=1)
def _win32_find_api():
    """Initialize the Win32 filename-search bindings once per process."""
    import ctypes
    from ctypes import wintypes

    class WIN32_FIND_DATAW(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", wintypes.FILETIME),
            ("ftLastAccessTime", wintypes.FILETIME),
            ("ftLastWriteTime", wintypes.FILETIME),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("dwReserved0", wintypes.DWORD),
            ("dwReserved1", wintypes.DWORD),
            ("cFileName", wintypes.WCHAR * 260),
            ("cAlternateFileName", wintypes.WCHAR * 14),
            ("dwFileType", wintypes.DWORD),
            ("dwCreatorType", wintypes.DWORD),
            ("wFinderFlags", wintypes.WORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    find_first = kernel32.FindFirstFileW
    find_first.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(WIN32_FIND_DATAW)]
    find_first.restype = wintypes.HANDLE
    find_next = kernel32.FindNextFileW
    find_next.argtypes = [wintypes.HANDLE, ctypes.POINTER(WIN32_FIND_DATAW)]
    find_next.restype = wintypes.BOOL
    find_close = kernel32.FindClose
    find_close.argtypes = [wintypes.HANDLE]
    find_close.restype = wintypes.BOOL
    return ctypes, wintypes, WIN32_FIND_DATAW, find_first, find_next, find_close


def fast_glob_files(directory: Path, pattern: str) -> list[Path]:
    """Return matching files without a full Python directory walk on Windows.

    AnimeStudio type directories can contain more than a million files.  On
    Windows, ``Path.glob``/``os.scandir`` must materialize every directory
    entry even for a selective prefix such as ``BeyondFMVPlayableAsset*.json``.
    The Win32 find API lets NTFS apply that filename filter while preserving a
    stdlib-only implementation.  Other platforms retain the normal pathlib
    behavior.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []
    if sys.platform != "win32":
        return sorted(path for path in directory.glob(pattern) if path.is_file())

    (
        ctypes,
        wintypes,
        find_data_type,
        find_first,
        find_next,
        find_close,
    ) = _win32_find_api()

    data = find_data_type()
    search = str(directory / pattern)
    handle = find_first(search, ctypes.byref(data))
    invalid_handle = wintypes.HANDLE(-1).value
    if handle == invalid_handle:
        error = ctypes.get_last_error()
        if error in (2, 3, 18):  # file/path not found, no more files
            return []
        raise OSError(error, os.strerror(error), search)

    file_attribute_directory = 0x10
    names: list[str] = []
    try:
        while True:
            name = data.cFileName
            if (
                name not in (".", "..")
                and not data.dwFileAttributes & file_attribute_directory
            ):
                names.append(name)
            if not find_next(handle, ctypes.byref(data)):
                error = ctypes.get_last_error()
                if error != 18:
                    raise OSError(error, os.strerror(error), search)
                break
    finally:
        find_close(handle)
    return [directory / name for name in sorted(names)]


def normalize_posix(value: str | Path) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def split_path_id_export_stem(value: Any) -> tuple[str, str] | None:
    match = PATH_ID_EXPORT_STEM_RE.match(str(value or ""))
    if not match:
        return None
    return match.group("base"), match.group("path_id").upper()


def path_id_export_base_stem(value: Any) -> str:
    split = split_path_id_export_stem(value)
    return split[0] if split else ""


def path_id_export_path_id(value: Any) -> str:
    split = split_path_id_export_stem(value)
    return split[1] if split else ""


def rel_requires_path_id_export_name(rel: str | Path) -> bool:
    normalized = normalize_posix(rel)
    source = normalized.split("/", 1)[0]
    if not source:
        return False
    if source.lower().endswith("-structured") or source.lower() == "raw_vfs":
        return False
    source_family = source.split("-", 1)[0].lower()
    return source_family in PATH_ID_EXPORT_SOURCE_FAMILIES


def display_extension(value: str) -> str:
    return str(value or "").strip() or "[no extension]"


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def write_json(
    path: Path,
    payload: Any,
    *,
    indent: int | None = None,
    compact: bool = True,
    trailing_newline: bool = False,
) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    separators = (",", ":") if compact and indent is None else None
    text = json.dumps(payload, ensure_ascii=False, indent=indent, separators=separators)
    if trailing_newline:
        text += "\n"
    return write_text_if_changed(path, text)


def write_text_if_changed(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Match TextIOWrapper's historical newline translation so this faster
    # binary comparison does not rewrite platform-native generated files.
    encoded = text.replace("\n", os.linesep).encode("utf-8")
    try:
        # Generated WebUI builds compare thousands of files on every warm run.
        # Reading bytes avoids a separate ``exists`` stat plus UTF-8 decoding;
        # the newly serialized text already has to be encoded if it is written.
        if path.read_bytes() == encoded:
            return False
    except OSError:
        pass
    path.write_bytes(encoded)
    return True


def write_report_json(path: Path, payload: Any) -> bool:
    return write_json(path, payload, indent=2, compact=False, trailing_newline=True)


def safe_key(value: Any) -> str:
    return str(value if value is not None else "").strip()


def md_escape(value: Any) -> str:
    return safe_key(value).replace("|", "\\|").replace("\n", " ")


def is_present(value: Any, empty_values: tuple[Any, ...] = (None, "", [], {})) -> bool:
    return value not in empty_values


def compact_dict(values: dict[str, Any], empty_values: tuple[Any, ...] = (None, "", [], {})) -> dict[str, Any]:
    return {key: value for key, value in values.items() if is_present(value, empty_values)}


def unique_preserve(values: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def unique_strings(values: Iterable[Any]) -> list[str]:
    return unique_preserve(value for value in values if isinstance(value, str) and value)


def walk_field_values(node: Any, field_name: str, *, unwrap_const: bool = True):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == field_name:
                if unwrap_const and isinstance(value, dict) and "constValue" in value:
                    yield value["constValue"]
                else:
                    yield value
            else:
                yield from walk_field_values(value, field_name, unwrap_const=unwrap_const)
    elif isinstance(node, list):
        for item in node:
            yield from walk_field_values(item, field_name, unwrap_const=unwrap_const)


def walk_const_values(node: Any, field_name: str):
    for value in walk_field_values(node, field_name):
        if isinstance(value, str):
            yield value


def all_string_fields(node: Any, field_name: str):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == field_name and isinstance(value, str):
                yield value
            else:
                yield from all_string_fields(value, field_name)
    elif isinstance(node, list):
        for item in node:
            yield from all_string_fields(item, field_name)


def first_string_field(node: Any, field_name: str) -> str | None:
    return next(all_string_fields(node, field_name), None)


def rel_path(path: Path | str, root: Path = ROOT) -> str:
    raw_path = Path(path)
    try:
        # These are display/provenance paths, not filesystem identity checks.
        # ``os.path.relpath`` preserves the prior lexical behavior while
        # avoiding Path.relative_to's component-object churn on the tens of
        # thousands of repeated provenance rows in a Story build.
        absolute_path = os.path.abspath(raw_path)
        absolute_root = os.path.abspath(root)
        relative = os.path.relpath(absolute_path, absolute_root)
        if relative == os.pardir or relative.startswith(os.pardir + os.sep):
            return raw_path.as_posix()
        return relative.replace(os.sep, "/")
    except (OSError, TypeError, ValueError):
        return raw_path.as_posix()


def split_csv_values(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        for item in str(value).split(","):
            item = item.strip()
            if item:
                out.append(item)
    return out


def parse_group_filters(values: list[str] | None) -> set[int]:
    groups: set[int] = set()
    for value in split_csv_values(values):
        try:
            groups.add(int(value))
        except ValueError as exc:
            raise ValueError(f"group must be an integer: {value}") from exc
    return groups


def story_matches(story_key: str, filters: list[str]) -> bool:
    if not filters:
        return True
    lowered = story_key.lower()
    for item in filters:
        pattern = item.lower()
        if pattern == lowered or pattern in lowered:
            return True
        if any(ch in pattern for ch in "*?[]") and fnmatch.fnmatch(lowered, pattern):
            return True
    return False


def filtered_json_paths(json_dir: Path, filters: list[str]) -> list[Path]:
    if not filters:
        return sorted(json_dir.glob("*.json"))

    paths: dict[Path, None] = {}
    for item_filter in filters:
        if any(ch in item_filter for ch in "*?[]"):
            for path in json_dir.glob(f"{item_filter}.json"):
                paths[path] = None
            continue
        exact = json_dir / f"{item_filter}.json"
        if exact.exists():
            paths[exact] = None
            continue
        for path in json_dir.glob("*.json"):
            if story_matches(path.stem, [item_filter]):
                paths[path] = None
    return sorted(paths)


# Authored tables whose Story ids are structurally not mission narrative.
# Both are keyed by something other than a mission/scene/script and serialize no
# mission, quest, scene, or script field, so no mission can ever own their rows.
# Filename patterns are deliberately NOT used: only authored table contents may
# admit a key, because filename inference is not original-data proof.
NON_MISSION_CONTENT_TABLES = (
    {
        "table": "AudioRadioContinueTable",
        "fields": ("selfContinue", "otherContinue"),
        "keyedBy": "speaker",
        "content": "per_speaker_radio_continuation_voice",
    },
    {
        "table": "SNSDialogTopicTable",
        "fields": ("includeDialogIds",),
        "keyedBy": "topicId",
        "content": "character_sns_topic",
    },
)

GUIDE_RUNTIME_NON_MISSION_REPORT = (
    STORY_RECOVERY_REPORTS_DIR
    / "animestudio_story_guide_consumer_audit.json"
)
EXPORT_FULL_SUMMARY = EXPORT_REPORTS_DIR / "export_full_summary.json"
GUIDE_RUNTIME_NON_MISSION_SCHEMA = "animestudioStoryGuideConsumerAudit.v1"


def non_mission_content_keys(table_root: Path) -> dict[str, dict[str, str]]:
    """Collect Story keys defined only by non-mission authored content tables.

    Returns ``{sceneKey: {table, field, keyedBy, content}}``. A missing table
    yields no keys rather than an error, so callers still build on a partial
    export.
    """
    found: dict[str, dict[str, str]] = {}
    for spec in NON_MISSION_CONTENT_TABLES:
        payload = read_json(Path(table_root) / f"{spec['table']}.json", {})
        if not isinstance(payload, dict):
            continue
        for row in payload.values():
            if not isinstance(row, dict):
                continue
            for field in spec["fields"]:
                value = row.get(field)
                values = value if isinstance(value, list) else [value]
                for entry in values:
                    scene_key = safe_key(entry)
                    if scene_key and scene_key not in found:
                        found[scene_key] = {
                            "table": spec["table"],
                            "field": field,
                            "keyedBy": spec["keyedBy"],
                            "content": spec["content"],
                        }
    return found


def guide_runtime_non_mission_content_keys(
    report_path: Path = GUIDE_RUNTIME_NON_MISSION_REPORT,
    *,
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
    output_root: Path = EXPORT_ROOT,
) -> dict[str, dict[str, Any]]:
    """Load freshness-checked exact non-mission GuideRuntimeAsset consumers.

    Invalid, missing, or stale evidence yields no classifications.  The report
    must match both the currently published object-index stage signature and
    the source fingerprint recorded by the latest installed-game export.
    """
    report = read_json(Path(report_path), {})
    export_summary = read_json(Path(export_summary_path), {})
    if (
        not isinstance(report, dict)
        or report.get("_schema") != GUIDE_RUNTIME_NON_MISSION_SCHEMA
        or not isinstance(export_summary, dict)
        or (report.get("nativeEvidence") or {}).get("validated") is not True
    ):
        return {}
    source_sizes = export_summary.get("source_sizes")
    if not isinstance(source_sizes, dict):
        return {}
    sources = report.get("sources")
    if not isinstance(sources, list) or not sources:
        return {}
    for source_row in sources:
        if not isinstance(source_row, dict):
            return {}
        source = safe_key(source_row.get("source"))
        stage_signature = safe_key(
            source_row.get("stageSignatureSha256")
        )
        source_fingerprint = source_row.get("sourceFingerprint")
        export_fingerprint = source_sizes.get(source)
        summary_path = (
            Path(output_root)
            / "recovered"
            / "AnimeStudio-cli"
            / source
            / "object_index"
            / "summary.json"
        )
        current_summary = read_json(summary_path, {})
        current_stage = current_summary.get("stageSignature")
        if (
            not source
            or len(stage_signature) != 64
            or not isinstance(source_fingerprint, dict)
            or not isinstance(export_fingerprint, dict)
            or not isinstance(current_summary, dict)
            or current_summary.get("complete") is not True
            or not isinstance(current_stage, dict)
            or safe_key(current_stage.get("sha256")) != stage_signature
        ):
            return {}
        normalized_report_fingerprint = {
            "files": source_fingerprint.get("files"),
            "bytes": source_fingerprint.get("bytes"),
            "fingerprint":
                safe_key(source_fingerprint.get("fingerprint")).lower(),
        }
        normalized_export_fingerprint = {
            "files": export_fingerprint.get("files"),
            "bytes": export_fingerprint.get("bytes"),
            "fingerprint":
                safe_key(export_fingerprint.get("fingerprint")).lower(),
        }
        current_payload = current_stage.get("payload")
        normalized_current_fingerprint = (
            current_payload.get("source_fingerprint")
            if isinstance(current_payload, dict)
            else None
        )
        if (
            normalized_report_fingerprint != normalized_export_fingerprint
            or normalized_report_fingerprint != normalized_current_fingerprint
        ):
            return {}

    found: dict[str, dict[str, Any]] = {}
    evidence_path = Path(report_path)
    try:
        evidence_report = evidence_path.resolve().relative_to(
            ROOT.resolve()
        ).as_posix()
    except ValueError:
        evidence_report = str(evidence_path)
    for row in report.get("classifications") or []:
        if not isinstance(row, dict):
            continue
        story_key = safe_key(row.get("storyKey"))
        if (
            not story_key
            or safe_key(row.get("recoveryStatus"))
            != "closed_exact_guide_runtime_non_mission_content"
            or safe_key(row.get("evidenceKind")) != "guide_runtime_asset"
            or not safe_key(row.get("consumerClass"))
            or int(row.get("assetCount") or 0) <= 0
            or int(row.get("actionCount") or 0) <= 0
        ):
            continue
        found[story_key] = {
            "evidenceKind": "guide_runtime_asset",
            "content": safe_key(row.get("contentClass")),
            "assetType": safe_key(row.get("assetType")),
            "consumerClass": safe_key(row.get("consumerClass")),
            "assetCount": int(row.get("assetCount") or 0),
            "actionCount": int(row.get("actionCount") or 0),
            "assetNames": [
                safe_key(value)
                for value in row.get("assetNames") or []
                if safe_key(value)
            ],
            "guideLevelIds": [
                safe_key(value)
                for value in row.get("guideLevelIds") or []
                if safe_key(value)
            ],
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "nativeMethod": row.get("nativeMethod") or {},
            "orderBoundary": safe_key(row.get("orderBoundary")),
            "evidenceReport": evidence_report,
        }
    return found


def combined_non_mission_content_keys(
    table_root: Path,
    *,
    guide_report_path: Path = GUIDE_RUNTIME_NON_MISSION_REPORT,
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
    output_root: Path = EXPORT_ROOT,
) -> dict[str, dict[str, Any]]:
    """Merge table-defined and exact guide-runtime non-mission content."""
    found: dict[str, dict[str, Any]] = {
        key: {"evidenceKind": "authored_table", **row}
        for key, row in non_mission_content_keys(table_root).items()
    }
    for key, row in guide_runtime_non_mission_content_keys(
        guide_report_path,
        export_summary_path=export_summary_path,
        output_root=output_root,
    ).items():
        found.setdefault(key, row)
    return found


def safe_report_suffix(
    story_filters: list[str],
    group_filters: set[int],
    flag: bool = False,
    *,
    flag_label: str = "interesting",
) -> str:
    parts: list[str] = []
    if story_filters:
        parts.append("story_" + "_".join(story_filters[:4]))
        if len(story_filters) > 4:
            parts.append(f"plus_{len(story_filters) - 4}")
    if group_filters:
        parts.append("group_" + "_".join(str(value) for value in sorted(group_filters)))
    if flag:
        parts.append(flag_label)
    if not parts:
        return ""
    suffix = "_".join(parts).translate(SAFE_REPORT_REPLACEMENTS)
    return "_" + suffix[:120].strip("_")
