"""Small shared helpers for WebUI builder scripts."""
from __future__ import annotations

import json
import fnmatch
import hashlib
import os
import re
import sys
from dataclasses import dataclass
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


@lru_cache(maxsize=512)
def _read_json_cached_absolute(path_text: str) -> Any:
    return json.loads(Path(path_text).read_text(encoding="utf-8"))


def read_json_cached(path: str | Path) -> Any:
    """Parse one immutable build input once per Python process.

    Caching is limited to ``export_full/`` for the same reason as
    ``read_bytes_cached``: the export is fixed for the duration of a build.
    The parsed object is shared between callers, so treat it as read-only.
    """
    normalized = os.path.normcase(os.path.abspath(os.fspath(path)))
    export_root = os.path.normcase(os.path.abspath(os.fspath(EXPORT_ROOT)))
    if normalized != export_root and not normalized.startswith(export_root + os.sep):
        return json.loads(Path(normalized).read_text(encoding="utf-8"))
    return _read_json_cached_absolute(normalized)


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
SPACESHIP_STORY_NON_MISSION_REPORT = (
    STORY_RECOVERY_REPORTS_DIR / "spaceship_story_content_audit.json"
)
SPACESHIP_STORY_NON_MISSION_SCHEMA = "spaceshipStoryContentAudit.v2"
SPACESHIP_STORY_NON_MISSION_MAPPING_ID = (
    "gameassembly-2026-08-02-spaceship-story-consumers-v1"
)
RECORDED_NATIVE_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
RECORDED_NATIVE_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
SPACESHIP_STORY_GAMEASSEMBLY_SHA256 = RECORDED_NATIVE_GAMEASSEMBLY_SHA256
SPACESHIP_STORY_METADATA_SHA256 = RECORDED_NATIVE_METADATA_SHA256
STORY_ROOT_PLAYBACK_ALIAS_REPORT = (
    STORY_RECOVERY_REPORTS_DIR
    / "animestudio_story_reverse_pptr_audit.json"
)
STORY_ROOT_PLAYBACK_ALIAS_SCHEMA = "animestudioStoryReversePPtrAudit.v4"
STORY_ROOT_PLAYBACK_ALIAS_MAPPING_ID = (
    "gameassembly-2026-07-28-cutscene-root-director-playback-v1"
)
STORY_ROOT_PLAYBACK_ALIAS_GAMEASSEMBLY_SHA256 = RECORDED_NATIVE_GAMEASSEMBLY_SHA256
STORY_ROOT_PLAYBACK_ALIAS_METADATA_SHA256 = RECORDED_NATIVE_METADATA_SHA256
DEFAULT_INSTALLED_GAME_DATA_ROOT = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data"
)
GLOBAL_METADATA_REL = Path("il2cpp_data") / "Metadata" / "global-metadata.dat"
NATIVE_EVIDENCE_VALIDATED = "validated"
NATIVE_EVIDENCE_MISSING = "missing"
NATIVE_EVIDENCE_MISMATCHED = "mismatched"
REQUIRE_NATIVE_EVIDENCE_ENV = "ENDFIELD_REQUIRE_NATIVE_EVIDENCE"


def _game_data_root_from_paths_bat() -> Path | None:
    """Read ENDFIELD_GAME_ROOT out of the checkout's endfield_paths.bat."""
    try:
        text = (ROOT / "endfield_paths.bat").read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError:
        return None
    match = re.search(
        r'^\s*set\s+"ENDFIELD_GAME_ROOT=([^"\r\n]+)"',
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    value = match.group(1).strip() if match else ""
    return Path(value) if value else None


def installed_game_data_root_candidates(
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
) -> list[Path]:
    """Ordered ``Endfield_Data`` roots this checkout may be built against.

    ``ENDFIELD_GAME_ROOT`` comes first and ``endfield_paths.bat`` second
    because both are deliberate statements about where the client lives; the
    wrapper scripts also set the variable from ``--game-root``. The export
    summary follows as the root the current ``export_full`` was produced from,
    which covers scripts run outside the wrappers, and the historical default
    is last.
    """
    candidates: list[Path] = []
    env_value = os.environ.get("ENDFIELD_GAME_ROOT", "").strip()
    if env_value:
        candidates.append(Path(env_value.strip('"')))
    configured = _game_data_root_from_paths_bat()
    if configured is not None:
        candidates.append(configured)
    summary = read_json(export_summary_path, {})
    if isinstance(summary, dict):
        recorded = safe_key(summary.get("game_root")).strip()
        if recorded:
            candidates.append(Path(recorded))
    candidates.append(DEFAULT_INSTALLED_GAME_DATA_ROOT)

    ordered: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).rstrip("\\/").casefold()
        if key and key not in seen:
            seen.add(key)
            ordered.append(candidate)
    return ordered


def sha256_file(path: Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 of a file, read in bounded chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_installed_game_data_root(
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
) -> Path:
    """Return the installed ``Endfield_Data`` root this checkout builds against.

    The first candidate that exists on disk wins; otherwise the highest
    priority candidate is returned so callers report a path the user can fix.
    Edit ``endfield_paths.bat`` (or set ``ENDFIELD_GAME_ROOT``) to move it.
    """
    candidates = installed_game_data_root_candidates(export_summary_path)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def resolve_installed_native_inputs(
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
) -> tuple[Path, Path]:
    """Return the installed ``(GameAssembly.dll, global-metadata.dat)`` pair.

    The first candidate root whose files both exist wins, so a relocated
    install is found even when a stale export summary or a leftover default
    points elsewhere. When nothing exists the highest-priority candidate is
    returned so callers report the path the user is expected to fix.
    """
    fallback: tuple[Path, Path] | None = None
    for root in installed_game_data_root_candidates(export_summary_path):
        pair = (root.parent / "GameAssembly.dll", root / GLOBAL_METADATA_REL)
        if fallback is None:
            fallback = pair
        if pair[0].is_file() and pair[1].is_file():
            return pair
    assert fallback is not None  # the default candidate is always present
    return fallback


@dataclass(frozen=True)
class InstalledNativeInputs:
    """Result of gating a recovery step on the installed IL2CPP binaries.

    ``status`` is ``validated`` when every required file is present and every
    supplied expectation matches, ``missing`` when a file is absent, and
    ``mismatched`` when the installed client is a different build from the one
    the caller's recorded native facts were derived on.
    """

    gameassembly: Path
    metadata: Path
    gameassembly_sha256: str
    metadata_sha256: str
    status: str
    detail: str

    @property
    def validated(self) -> bool:
        return self.status == NATIVE_EVIDENCE_VALIDATED


class NativeEvidenceUnavailable(RuntimeError):
    """Raised when a step's recorded native facts do not describe the install.

    Carries the gate result so the caller can decide between skipping the
    step and failing, without re-running the hashes.
    """

    def __init__(
        self,
        result: "InstalledNativeInputs",
        message: str = "",
    ) -> None:
        super().__init__(message or result.detail)
        self.result = result


def native_evidence_required() -> bool:
    """Whether unusable native inputs must fail instead of skipping a step.

    Recovery steps carry native facts derived from one specific client build.
    Off by default so a different or absent install degrades to a skip and the
    rest of the pipeline still builds; set ``ENDFIELD_REQUIRE_NATIVE_EVIDENCE``
    to keep the historical fail-closed behavior when auditing that build.
    """
    value = os.environ.get(REQUIRE_NATIVE_EVIDENCE_ENV, "").strip().casefold()
    return value not in {"", "0", "false", "no", "off"}


def check_installed_native_inputs(
    expected_gameassembly_sha256: str = "",
    expected_metadata_sha256: str = "",
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
    require_metadata: bool = True,
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
) -> InstalledNativeInputs:
    """Resolve and gate the installed native inputs a recovery step needs.

    Explicit paths win over the resolved install. Expectations are optional:
    a step that only reads the current binary can pass none and still get the
    existence check plus the measured hashes for its report.
    """
    resolved_gameassembly, resolved_metadata = resolve_installed_native_inputs(
        export_summary_path
    )
    gameassembly = (
        Path(gameassembly) if gameassembly is not None else resolved_gameassembly
    )
    metadata = Path(metadata) if metadata is not None else resolved_metadata
    # Pinning the metadata hash implies the metadata is needed to check it.
    require_metadata = require_metadata or bool(expected_metadata_sha256)

    required = [("GameAssembly.dll", gameassembly)]
    if require_metadata:
        required.append(("global-metadata.dat", metadata))
    absent = [(label, path) for label, path in required if not path.is_file()]
    if absent:
        names = ", ".join(label for label, _path in absent)
        paths = ", ".join(str(path) for _label, path in absent)
        return InstalledNativeInputs(
            gameassembly=gameassembly,
            metadata=metadata,
            gameassembly_sha256="",
            metadata_sha256="",
            status=NATIVE_EVIDENCE_MISSING,
            detail=(
                f"installed {names} not found at {paths}; point "
                "endfield_paths.bat or ENDFIELD_GAME_ROOT at the installed "
                "client"
            ),
        )

    gameassembly_sha256 = sha256_file(gameassembly)
    metadata_sha256 = sha256_file(metadata) if require_metadata else ""
    drifted: list[str] = []
    for label, actual, expected in (
        ("GameAssembly.dll", gameassembly_sha256, expected_gameassembly_sha256),
        ("global-metadata.dat", metadata_sha256, expected_metadata_sha256),
    ):
        expected = safe_key(expected).strip().casefold()
        if expected and actual.casefold() != expected:
            drifted.append(
                f"{label} is {actual[:12]} but the recorded evidence was "
                f"derived on {expected[:12]}"
            )

    return InstalledNativeInputs(
        gameassembly=gameassembly,
        metadata=metadata,
        gameassembly_sha256=gameassembly_sha256,
        metadata_sha256=metadata_sha256,
        status=NATIVE_EVIDENCE_MISMATCHED if drifted else NATIVE_EVIDENCE_VALIDATED,
        detail="; ".join(drifted),
    )


NATIVE_EVIDENCE_SKIP_MARKER = "] skipped: "


def is_native_evidence_skip(stderr: str) -> bool:
    """Whether a step that exited zero reported a skip rather than work."""
    return NATIVE_EVIDENCE_SKIP_MARKER in (stderr or "")


def native_evidence_skip_message(
    tool: str,
    result: InstalledNativeInputs,
    *,
    required: bool = False,
) -> str:
    """Render the one-line reason a step is skipped or failed, for stderr."""
    outcome = "failed" if required else "skipped"
    if result.status == NATIVE_EVIDENCE_MISSING:
        return f"[{tool}] {outcome}: {result.detail}"
    return (
        f"[{tool}] {outcome}: the installed client is a different build "
        f"({result.detail}); this step's recorded native facts do not "
        "describe it"
    )


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


def spaceship_story_non_mission_content_keys(
    report_path: Path = SPACESHIP_STORY_NON_MISSION_REPORT,
    *,
    source_root: Path = ROOT,
) -> dict[str, dict[str, Any]]:
    """Load source-hash-checked operator-spacecraft Story classifications."""
    report_path = Path(report_path)
    report = read_json(report_path, {})
    native = report.get("nativeEvidence") if isinstance(report, dict) else {}
    if (
        not isinstance(report, dict)
        or report.get("_schema") != SPACESHIP_STORY_NON_MISSION_SCHEMA
        or not isinstance(native, dict)
        or native.get("validated") is not True
        or safe_key(native.get("mappingId"))
        != SPACESHIP_STORY_NON_MISSION_MAPPING_ID
        or safe_key(native.get("gameAssemblySha256")).upper()
        != SPACESHIP_STORY_GAMEASSEMBLY_SHA256
        or safe_key(native.get("metadataSha256")).upper()
        != SPACESHIP_STORY_METADATA_SHA256
    ):
        return {}

    sources = report.get("sources")
    if not isinstance(sources, list) or not sources:
        return {}
    validated_source_paths: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            return {}
        source_path = safe_key(source.get("path"))
        expected_hash = safe_key(source.get("sha256")).upper()
        expected_bytes = source.get("bytes")
        path = Path(source_root) / Path(source_path)
        if (
            not source_path
            or len(expected_hash) != 64
            or not isinstance(expected_bytes, int)
            or not path.is_file()
            or path.stat().st_size != expected_bytes
        ):
            return {}
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest().upper() != expected_hash:
            return {}
        validated_source_paths.add(source_path)

    try:
        evidence_report = report_path.resolve().relative_to(
            ROOT.resolve()
        ).as_posix()
    except ValueError:
        evidence_report = str(report_path)
    found: dict[str, dict[str, Any]] = {}
    for row in report.get("classifications") or []:
        if not isinstance(row, dict):
            continue
        story_key = safe_key(row.get("storyKey"))
        evidence_kind = safe_key(row.get("evidenceKind"))
        source_files = [
            safe_key(value)
            for value in row.get("sourceFiles") or []
            if safe_key(value)
        ]
        recovery_status = safe_key(row.get("recoveryStatus"))
        expected_status = (
            (
                "deferred_current_build_spaceship_dialog_definition_"
                "without_tree_carrier"
            )
            if evidence_kind
            == "spaceship_dialog_definition_without_tree_carrier"
            else "closed_exact_spaceship_runtime_non_mission_content"
        )
        if (
            not story_key
            or recovery_status != expected_status
            or evidence_kind not in {
                "spaceship_dialog_tree",
                "character_profile_voice",
                "spaceship_dialog_definition_without_tree_carrier",
            }
            or not source_files
            or any(
                source_file not in validated_source_paths
                for source_file in source_files
            )
            or not row.get("lineIds")
            or safe_key(row.get("nativeMappingId"))
            != SPACESHIP_STORY_NON_MISSION_MAPPING_ID
            or (
                evidence_kind == "spaceship_dialog_tree"
                and (
                    not row.get("dialogTreeRoots")
                    or not row.get("consumerClasses")
                )
            )
            or (
                evidence_kind == "character_profile_voice"
                and (
                    not row.get("characterIds")
                    or not row.get("profileVoiceIds")
                )
            )
            or (
                evidence_kind
                == "spaceship_dialog_definition_without_tree_carrier"
                and (
                    not row.get("dialogTreeRoots")
                    or not row.get("consumerClasses")
                    or not safe_key(row.get("dialogFamily"))
                    or not safe_key(row.get("actorId"))
                    or safe_key(row.get("carrierStatus"))
                    != "absent_from_all_related_typed_dialog_trees"
                    or not safe_key(row.get("consumerBoundary"))
                )
            )
        ):
            continue
        found[story_key] = {
            "evidenceKind": evidence_kind,
            "content": safe_key(row.get("contentClass")),
            "lineIds": [
                safe_key(value)
                for value in row.get("lineIds") or []
                if safe_key(value)
            ],
            "dialogTreeRoots": [
                safe_key(value)
                for value in row.get("dialogTreeRoots") or []
                if safe_key(value)
            ],
            "consumerClasses": [
                safe_key(value)
                for value in row.get("consumerClasses") or []
                if safe_key(value)
            ],
            "characterIds": [
                safe_key(value)
                for value in row.get("characterIds") or []
                if safe_key(value)
            ],
            "profileVoiceIds": [
                safe_key(value)
                for value in row.get("profileVoiceIds") or []
                if safe_key(value)
            ],
            "dialogFamily": safe_key(row.get("dialogFamily")),
            "actorId": safe_key(row.get("actorId")),
            "carrierStatus": safe_key(row.get("carrierStatus")),
            "consumerBoundary": safe_key(row.get("consumerBoundary")),
            "sourceFiles": source_files,
            "nativeMappingId": safe_key(row.get("nativeMappingId")),
            "orderBoundary": safe_key(row.get("orderBoundary")),
            "evidenceReport": evidence_report,
        }
    return found


def story_root_playback_aliases(
    report_path: Path = STORY_ROOT_PLAYBACK_ALIAS_REPORT,
    *,
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
    output_root: Path = EXPORT_ROOT,
) -> list[dict[str, Any]]:
    """Load current exact CutsceneRoot-to-TimelineAsset playback aliases.

    Missing or stale evidence yields no rows. The aliases are playback context
    only: callers must not turn them into mission ownership or Story order.
    """
    report = read_json(Path(report_path), {})
    export_summary = read_json(Path(export_summary_path), {})
    native = report.get("nativeEvidence") if isinstance(report, dict) else {}
    if (
        not isinstance(report, dict)
        or report.get("_schema") != STORY_ROOT_PLAYBACK_ALIAS_SCHEMA
        or not isinstance(export_summary, dict)
        or not isinstance(native, dict)
        or safe_key(native.get("mappingId"))
        != STORY_ROOT_PLAYBACK_ALIAS_MAPPING_ID
        or safe_key(native.get("gameAssemblySha256")).upper()
        != STORY_ROOT_PLAYBACK_ALIAS_GAMEASSEMBLY_SHA256
        or safe_key(native.get("metadataSha256")).upper()
        != STORY_ROOT_PLAYBACK_ALIAS_METADATA_SHA256
    ):
        return []
    source_sizes = export_summary.get("source_sizes")
    sources = report.get("sources")
    if (
        not isinstance(source_sizes, dict)
        or not isinstance(sources, list)
        or not sources
    ):
        return []
    for source_row in sources:
        if not isinstance(source_row, dict):
            return []
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
            return []
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
            return []

    evidence_path = Path(report_path)
    try:
        evidence_report = evidence_path.resolve().relative_to(
            ROOT.resolve()
        ).as_posix()
    except ValueError:
        evidence_report = str(evidence_path)
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for host in report.get("directorHosts") or []:
        if not isinstance(host, dict):
            continue
        for row in host.get("crossStoryPlaybackAliases") or []:
            if not isinstance(row, dict):
                continue
            root_key = safe_key(row.get("rootStoryKey"))
            playable_key = safe_key(row.get("playableAssetStoryKey"))
            director = row.get("directorObject")
            if (
                not root_key
                or not playable_key
                or root_key == playable_key
                or safe_key(row.get("relation"))
                != "cutscene_root_director_playable_asset"
                or safe_key(row.get("edgeStatus"))
                != (
                    "exact_root_playback_alias_no_chronology_or_"
                    "mission_owner"
                )
                or not isinstance(
                    row.get("cutsceneRootComponentPathId"),
                    int,
                )
                or not isinstance(director, dict)
                or not safe_key(director.get("serializedFile"))
                or not isinstance(director.get("pathId"), int)
            ):
                continue
            found[(root_key, playable_key)] = {
                "rootStoryKey": root_key,
                "playableAssetStoryKey": playable_key,
                "relation": "cutscene_root_director_playable_asset",
                "edgeStatus": safe_key(row.get("edgeStatus")),
                "cutsceneRootGameObjectPathId":
                    row.get("cutsceneRootGameObjectPathId"),
                "cutsceneRootComponentPathId":
                    row["cutsceneRootComponentPathId"],
                "directorObject": {
                    "serializedFile":
                        safe_key(director.get("serializedFile")),
                    "pathId": director["pathId"],
                    "source": safe_key(director.get("source")),
                    "sourceOffset": director.get("sourceOffset"),
                },
                "nativeMappingId":
                    STORY_ROOT_PLAYBACK_ALIAS_MAPPING_ID,
                "evidenceReport": evidence_report,
                "ownership": False,
                "chronology": False,
            }
    return [
        found[key]
        for key in sorted(found)
    ]


def combined_non_mission_content_keys(
    table_root: Path,
    *,
    guide_report_path: Path = GUIDE_RUNTIME_NON_MISSION_REPORT,
    export_summary_path: Path = EXPORT_FULL_SUMMARY,
    output_root: Path = EXPORT_ROOT,
) -> dict[str, dict[str, Any]]:
    """Merge table-defined and exact runtime non-mission content."""
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
    for key, row in spaceship_story_non_mission_content_keys().items():
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
