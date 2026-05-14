"""Small shared helpers for WebUI builder scripts."""
from __future__ import annotations

import json
import fnmatch
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "export_full"
OUT_DIR = ROOT / "webui" / "data"
LANG_DIR = OUT_DIR / "lang"
ASSET_DIR = OUT_DIR / "assets"
REPORTS_DIR = ROOT / "reports"
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


def normalize_posix(value: str | Path) -> str:
    return str(value or "").replace("\\", "/").strip("/")


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
    try:
        if path.exists() and path.read_text(encoding="utf-8") == text:
            return False
    except OSError:
        pass
    path.write_text(text, encoding="utf-8")
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
        return raw_path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
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
