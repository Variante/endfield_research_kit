#!/usr/bin/env python3
"""Build the local WebUI index for AnimeStudio decoded JSON outputs."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
from itertools import islice
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXPORT_ROOT, OUT_DIR, ROOT, normalize_posix, write_json

DEFAULT_INPUT_REL = Path("recovered") / "AnimeStudio-cli"
DEFAULT_OUTPUT = OUT_DIR / "decoded"
DEFAULT_SOURCES = ("StreamingAssets", "Persistent")
DEFAULT_TYPES = ("MonoBehaviour",)
AUTO_LOAD_ALL_FILE_LIMIT = 50_000
DEFAULT_MAX_GROUP_SIZE = 10_000
LIST_LIMIT = 14
COMMON_UNITY_FIELDS = {"m_GameObject", "m_Enabled", "m_Script", "m_Name"}

MARKER_LITERALS = {
    '"$decoded"': "decoded",
    '"$partial"': "partial",
    '"$unparsed"': "unparsed",
    '"$heuristic"': "heuristic",
}
ERROR_LITERALS = ('"decodeError"', '"serializedTypeTreeError"', '"typeTreeDecodeError"')
TOKEN_RE = re.compile(r"[A-Za-z0-9#]+")
CAMEL_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+")
PATH_ID_STEM_RE = re.compile(r"^(?P<name>.+)_p(?P<pathid>[0-9A-Fa-f]{16})$")
TOP_LEVEL_KEY_RE = re.compile(r'(?m)^  "((?:\\.|[^"])*)":')
CLASS_RE = re.compile(r'"class"\s*:\s*"((?:\\.|[^"])*)"')
LAYOUT_RE = re.compile(r'"layout"\s*:\s*"((?:\\.|[^"])*)"')
STRING_FIELD_RE_CACHE: dict[str, re.Pattern[str]] = {}
NUMBER_FIELD_RE_CACHE: dict[str, re.Pattern[str]] = {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the WebUI decoded-file browser index.")
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT, help="Export root. Defaults to export_full.")
    parser.add_argument("--input-root", type=Path, default=None, help="Decoded AnimeStudio root. Defaults to EXPORT_ROOT/recovered/AnimeStudio-cli.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output directory. Defaults to webui/data/decoded.")
    parser.add_argument("--sources", nargs="*", default=list(DEFAULT_SOURCES), help="Decoded sources to scan, or 'all'.")
    parser.add_argument("--types", nargs="*", default=list(DEFAULT_TYPES), help="Decoded json_by_type folders to scan, or 'all'.")
    parser.add_argument("--max-group-size", type=int, default=DEFAULT_MAX_GROUP_SIZE, help="Split logical groups above this entry count.")
    parser.add_argument("--limit", type=int, default=0, help="Optional development limit on scanned files.")
    parser.add_argument("--jobs", type=int, default=8, help="Parallel file readers for index scanning. Defaults to 8.")
    return parser.parse_args(argv)


def rel_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def detect_sources(input_root: Path) -> list[str]:
    return sorted(path.name for path in input_root.iterdir() if path.is_dir() and (path / "json_by_type").is_dir())


def detect_types(input_root: Path, sources: list[str]) -> list[str]:
    values: set[str] = set()
    for source in sources:
        root = input_root / source / "json_by_type"
        if root.exists():
            values.update(path.name for path in root.iterdir() if path.is_dir())
    return sorted(values)


def resolve_requested(values: list[str], available: list[str], *, default: tuple[str, ...]) -> list[str]:
    requested = [str(value).strip() for value in values or [] if str(value).strip()] or list(default)
    if any(value.lower() == "all" for value in requested):
        return available
    available_set = set(available)
    return [value for value in requested if value in available_set]


def strip_path_id_suffix(stem: str) -> str:
    match = PATH_ID_STEM_RE.match(stem)
    return match.group("name") if match else stem


def path_id_suffix(stem: str) -> str:
    match = PATH_ID_STEM_RE.match(stem)
    return match.group("pathid") if match else ""


def compact_string(value: Any, limit: int = 220) -> str:
    text = str(value if value is not None else "").replace("\r", " ").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "..."


def decode_json_string(value: str) -> str:
    try:
        return str(json.loads(f'"{value}"'))
    except json.JSONDecodeError:
        return value.replace(r'\"', '"').replace(r"\\", "\\")


def string_field(text: str, field: str) -> str:
    pattern = STRING_FIELD_RE_CACHE.get(field)
    if pattern is None:
        pattern = re.compile(rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"])*)"')
        STRING_FIELD_RE_CACHE[field] = pattern
    match = pattern.search(text)
    return decode_json_string(match.group(1)) if match else ""


def number_field(text: str, field: str) -> str:
    pattern = NUMBER_FIELD_RE_CACHE.get(field)
    if pattern is None:
        pattern = re.compile(rf'"{re.escape(field)}"\s*:\s*(-?\d+)')
        NUMBER_FIELD_RE_CACHE[field] = pattern
    match = pattern.search(text)
    return match.group(1) if match else ""


def unique_limited(values: list[str], limit: int = LIST_LIMIT) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = compact_string(value, 180)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def marker_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for literal, name in MARKER_LITERALS.items():
        value = text.count(literal)
        if value:
            counts[name] = value
    error_count = sum(text.count(literal) for literal in ERROR_LITERALS)
    if error_count:
        counts["errors"] = error_count
    return counts


def top_level_fields(text: str) -> list[str]:
    values = [decode_json_string(value) for value in TOP_LEVEL_KEY_RE.findall(text)]
    return [value for value in values if value != "$animestudio"][:LIST_LIMIT]


def managed_ref_classes(text: str) -> list[str]:
    return unique_limited([decode_json_string(value) for value in CLASS_RE.findall(text)])


def layout_values(text: str) -> list[str]:
    return unique_limited([decode_json_string(value) for value in LAYOUT_RE.findall(text)])


def source_chunk(source_original_path: str) -> str:
    raw = str(source_original_path or "").replace("\\", "/")
    return raw.rsplit("/", 1)[-1] if raw else ""


def clean_prefix_segment(value: str, fallback: str = "decoded") -> str:
    text = str(value or "").replace("\\", "/").replace("/", "_")
    text = re.sub(r"\s+", " ", text).strip(" ._-")
    return compact_string(text, 96) or fallback


def single_token_prefix(token: str, typ: str, depth: int = 2) -> str:
    value = token.strip() or typ or "decoded"
    lower = value.lower()
    if lower.startswith("monobehaviour#"):
        return "MonoBehaviour#"
    if value.isdigit() or len(value) <= 4:
        return clean_prefix_segment(value, typ or "decoded")
    pieces = CAMEL_TOKEN_RE.findall(value)
    if len(pieces) > 1:
        count = min(max(1, depth), len(pieces))
        return clean_prefix_segment("".join(pieces[:count]), typ or "decoded")
    if len(value) > 14:
        return clean_prefix_segment(value[:8], typ or "decoded")
    return clean_prefix_segment(value, typ or "decoded")


def filename_prefix(stem: str, typ: str, depth: int = 2) -> str:
    text = strip_path_id_suffix(stem or "").strip() or typ or "decoded"
    matches = list(TOKEN_RE.finditer(text))
    if not matches:
        return clean_prefix_segment(text, typ or "decoded")
    if len(matches) == 1:
        return single_token_prefix(matches[0].group(0), typ, depth)
    index = min(max(1, depth), len(matches)) - 1
    return clean_prefix_segment(text[: matches[index].end()], typ or "decoded")


def stable_entry_key(entry: dict[str, Any]) -> str:
    value = "\0".join([
        str(entry.get("p") or ""),
        str(entry.get("pathIdHex") or ""),
        str(entry.get("pathId") or ""),
        str(entry.get("file") or ""),
    ])
    return hashlib.sha1(value.encode("utf-8", "replace")).hexdigest()

def semantic_meaning(typ: str, stem: str, prefix: str, classes: list[str], layouts: list[str], fields: list[str], status: str) -> dict[str, Any]:
    text = " ".join([typ, stem, prefix, *classes, *layouts, *fields]).lower()
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    tags: list[str] = []

    def tagged(label: str, *values: str) -> dict[str, Any]:
        for value in values:
            if value and value not in tags:
                tags.append(value)
        if status in {"partial", "unparsed", "metadata-only", "json-error"} and "partial-decode" not in tags:
            tags.append("partial-decode")
        return {"label": label, "tags": tags[:8]}

    if typ == "Material":
        return tagged("Unity material JSON", "material", "rendering")
    if typ == "PlayableDirector":
        return tagged("Timeline director binding", "timeline", "playable")
    if typ == "TextAsset":
        return tagged("Text or binary asset JSON", "text-asset")
    if "dialog" in text or stem.startswith("dlg_") or stem.startswith("misc_dlg_"):
        return tagged("Dialog timeline/action data", "story", "dialog", "timeline")
    if "beyondfmv" in text or "cutscene" in text or "fmv" in text or "narrativevideo" in text:
        return tagged("Cutscene/video playable data", "story", "cutscene", "video")
    if "cinemachine" in text or "camera" in text or "impulse" in text:
        return tagged("Camera or cinematic behaviour", "camera", "timeline")
    if "activation track" in text or "activatetrack" in text or "trackasset" in text or "playableasset" in text or "timeline" in text:
        return tagged("Timeline/playable object", "timeline", "playable")
    if "data_projectile" in text or "projectile" in text:
        return tagged("Projectile gameplay config", "gameplay", "projectile")
    if "data_abilityentity" in text or "abilityentity" in text:
        return tagged("Ability entity runtime config", "gameplay", "ability")
    if "skilldatabundle" in text or "skill" in text or "ability" in text:
        return tagged("Ability/skill config", "gameplay", "ability")
    if prefix.lower().startswith("bb") or "blackboard" in text or "aibrain" in text or "ai_" in text:
        return tagged("AI blackboard/behaviour config", "gameplay", "ai")
    if "targetsettings" in text or "selectordata" in text or "selector" in text:
        return tagged("Target selection rules", "gameplay", "targeting")
    if "buff" in text or "statuseffect" in text or "modifier" in text:
        return tagged("Buff/status-effect config", "gameplay", "status")
    if "weapon" in text:
        return tagged("Weapon gameplay config", "gameplay", "weapon")
    if "enemy" in text or "monster" in text or "npc" in text:
        return tagged("NPC/enemy gameplay config", "gameplay", "npc")
    if "character" in text or stem.startswith("chr_") or "_chr_" in stem.lower():
        return tagged("Character gameplay config", "gameplay", "character")
    if "canvas" in text or "recttransform" in text or "widget" in text or "ui" in tokens or any(token.startswith("ui") and len(token) > 2 for token in tokens):
        return tagged("UI behaviour/config", "ui")
    if "3dconnexion" in text or "8bitdo" in text or "gamepad" in text or "controller" in text or "input" in text:
        return tagged("Input-device mapping", "input")
    if "table" in text:
        return tagged("Table-backed config object", "config", "table")
    if status in {"metadata-only", "unparsed", "json-error"}:
        return tagged("Preserved Unity object metadata", "metadata")
    if "references" in fields or classes or layouts:
        return tagged("Managed-reference object graph", "managed-reference")
    return tagged(f"Unity {typ or 'decoded'} JSON", "unity-json")


def semantic_domain(label: str, tags: list[str], typ: str) -> str:
    tag_set = {str(tag) for tag in tags or []}
    if "story" in tag_set and "dialog" in tag_set:
        return "story/dialog"
    if "story" in tag_set and "cutscene" in tag_set:
        return "story/cutscene"
    if "story" in tag_set:
        return "story"
    if "gameplay" in tag_set:
        for value in ("projectile", "ability", "ai", "targeting", "status", "weapon", "npc", "character"):
            if value in tag_set:
                return f"gameplay/{value}"
        return "gameplay"
    if "camera" in tag_set:
        return "camera/cinematic"
    if "timeline" in tag_set or "playable" in tag_set:
        return "timeline/playable"
    if "ui" in tag_set:
        return "ui"
    if "input" in tag_set:
        return "input"
    if "material" in tag_set or "rendering" in tag_set:
        return "rendering/material"
    if "config" in tag_set or "table" in tag_set:
        return "config/table"
    if "managed-reference" in tag_set:
        return "managed-reference"
    if "metadata" in tag_set:
        return "metadata-only"
    if typ:
        return f"unity/{typ}"
    return "unity/decoded"


def field_set_id(fields: list[str]) -> str:
    text = "\0".join(str(field) for field in fields or [])
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:10] if text else "none"


def field_set_label(fields: list[str]) -> str:
    values = set(fields or [])
    if {"m_Material", "m_Color", "m_RaycastTarget", "m_Sprite"}.issubset(values):
        return "ui-image-fields"
    if "m_text" in values or "m_Text" in values:
        return "ui-text-fields"
    if {"m_Clip", "m_Position", "m_EulerAngles"}.issubset(values):
        return "animation-playable-fields"
    if {"m_Version", "m_AnimClip", "uiBindingType"}.issubset(values):
        return "timeline-track-fields"
    if {"m_IgnoreLayout", "m_MinWidth", "m_PreferredWidth"}.issubset(values):
        return "ui-layout-fields"
    if "references" in values or "refDict" in values or "subReferences" in values:
        return "reference-graph-fields"
    if {"m_Priority", "m_LookAt", "m_Follow"}.issubset(values) or "_ignoreLookAtBlend" in values:
        return "cinemachine-fields"
    if "bboxMode" in values and ("effectLogicCfg" in values or "effectFunc" in values):
        return "effect-logic-fields"
    if "m_LightColor" in values or "enableLightMeshForReflectionProbe" in values:
        return "lighting-fields"
    if fields:
        first_raw = next((str(field) for field in fields if str(field) not in COMMON_UNITY_FIELDS), str(fields[0]))
        first = clean_prefix_segment(first_raw, "fields")
        return f"fields-{first}"
    return "metadata-only-fields"


def short_type_name(value: str) -> str:
    text = str(value or "")
    if "." in text:
        text = text.rsplit(".", 1)[-1]
    return clean_prefix_segment(text.replace("$", ""), "schema")


def schema_signal(classes: list[str], layouts: list[str], fields: list[str]) -> dict[str, str]:
    fid = field_set_id(fields)
    flabel = field_set_label(fields)
    if classes:
        primary = short_type_name(classes[0])
        return {"kind": "class", "name": primary, "group": f"class_{primary}", "fieldSet": flabel, "fieldSetId": fid}
    if layouts:
        primary = short_type_name(layouts[0])
        return {"kind": "layout", "name": primary, "group": f"layout_{primary}", "fieldSet": flabel, "fieldSetId": fid}
    return {"kind": "fields", "name": flabel, "group": f"{flabel}_{fid}", "fieldSet": flabel, "fieldSetId": fid}

def status_for_entry(fields: list[str], flags: dict[str, int], registry_status: str) -> str:
    if not fields:
        return "metadata-only"
    if flags.get("unparsed") and not flags.get("decoded") and not flags.get("partial"):
        return "unparsed"
    if (
        flags.get("partial")
        or flags.get("unparsed")
        or flags.get("heuristic")
        or flags.get("errors")
        or registry_status in {"heuristic", "partialDecoded", "recovered"}
    ):
        return "partial"
    return "decoded"


def ref_count_hint(text: str) -> int:
    start = text.find('"RefIds"')
    if start < 0:
        return 0
    return text.count('"rid"', start)


def extract_entry(path: Path, export_root: Path, source: str, typ: str) -> dict[str, Any]:
    stat = path.stat()
    rel = rel_to_root(path, export_root)
    filename_stem = strip_path_id_suffix(path.stem)
    path_hex = path_id_suffix(path.stem)
    prefix = filename_prefix(filename_stem, typ)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        status = "json-error"
        meaning = semantic_meaning(typ, filename_stem, prefix, [], [], [], status)
        domain = semantic_domain(meaning["label"], meaning["tags"], typ)
        schema = schema_signal([], [], [])
        return {
            "p": rel,
            "source": source,
            "type": typ,
            "file": path.name,
            "filenameStem": filename_stem,
            "name": filename_stem,
            "prefix": prefix,
            "family": prefix,
            "meaning": meaning["label"],
            "domain": domain,
            "schemaKind": schema["kind"],
            "schema": schema["name"],
            "schemaGroup": schema["group"],
            "fieldSet": schema["fieldSet"],
            "fieldSetId": schema["fieldSetId"],
            "tags": meaning["tags"],
            "status": status,
            "size": stat.st_size,
            "pathIdHex": path_hex,
            "flags": {"errors": 1},
            "error": compact_string(exc),
        }

    flags = marker_counts(text)
    recovery_index = text.find('"managedReferencesRegistryRecovery"')
    registry_status = ""
    if recovery_index >= 0:
        match = re.search(r'"status"\s*:\s*"((?:\\.|[^"])*)"', text[recovery_index:recovery_index + 1200])
        if match:
            registry_status = compact_string(decode_json_string(match.group(1)))
    if not registry_status and '"managedReferencesRegistryFullyDecoded": true' in text:
        registry_status = "fullyDecoded"
    elif not registry_status and '"managedReferencesRegistryRecovered": true' in text:
        registry_status = "recovered"

    fields = top_level_fields(text)
    entry_type = compact_string(string_field(text, "type") or typ)
    name = compact_string(string_field(text, "name") or string_field(text, "m_Name") or filename_stem, 260)
    raw_size = number_field(text, "rawDataLength") or number_field(text, "byteSize")
    class_id = number_field(text, "classId")
    source_original_path = string_field(text, "sourceOriginalPath")
    classes = managed_ref_classes(text)
    layouts = layout_values(text)
    status = status_for_entry(fields, flags, registry_status)
    meaning = semantic_meaning(entry_type, filename_stem, prefix, classes, layouts, fields, status)
    domain = semantic_domain(meaning["label"], meaning["tags"], entry_type)
    schema = schema_signal(classes, layouts, fields)
    entry = {
        "p": rel,
        "source": source,
        "type": entry_type,
        "file": path.name,
        "filenameStem": filename_stem,
        "name": name,
        "prefix": prefix,
        "family": prefix,
        "meaning": meaning["label"],
        "domain": domain,
        "schemaKind": schema["kind"],
        "schema": schema["name"],
        "schemaGroup": schema["group"],
        "fieldSet": schema["fieldSet"],
        "fieldSetId": schema["fieldSetId"],
        "tags": meaning["tags"],
        "status": status,
        "size": stat.st_size,
        "rawSize": int(raw_size or 0),
        "pathId": compact_string(number_field(text, "pathId"), 80),
        "pathIdHex": path_hex,
        "classId": int(class_id) if class_id else None,
        "sourceFile": compact_string(string_field(text, "sourceFile"), 120),
        "chunk": compact_string(source_chunk(source_original_path), 120),
        "registry": registry_status,
        "refCount": ref_count_hint(text),
        "classes": classes,
        "layouts": layouts,
        "fields": fields,
        "flags": flags,
    }
    error = string_field(text, "serializedTypeTreeError") or string_field(text, "typeTreeDecodeError") or string_field(text, "decodeError")
    if error:
        entry["error"] = compact_string(error)
    return {key: value for key, value in entry.items() if value not in (None, "", [], {})}


def group_base(entry: dict[str, Any]) -> str:
    return "/".join([
        str(entry.get("type") or "Decoded"),
        str(entry.get("source") or "Unknown"),
        str(entry.get("domain") or "unity/decoded"),
        str(entry.get("schemaGroup") or entry.get("schema") or "schema-unknown"),
    ])


def split_oversized_group(base: str, items: list[dict[str, Any]], max_group_size: int, groups: dict[str, list[dict[str, Any]]]) -> None:
    if len(items) <= max_group_size:
        groups[base] = items
        return

    ordered = sorted(items, key=lambda entry: (stable_entry_key(entry), str(entry.get("p") or "")))
    total_parts = (len(ordered) + max_group_size - 1) // max_group_size
    width = max(3, len(str(total_parts)))
    for index, start in enumerate(range(0, len(ordered), max_group_size), 1):
        groups[f"{base}/part-{index:0{width}d}-of-{total_parts:0{width}d}"] = ordered[start:start + max_group_size]


def split_groups(entries: list[dict[str, Any]], max_group_size: int) -> dict[str, list[dict[str, Any]]]:
    by_base: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_base[group_base(entry)].append(entry)
    groups: dict[str, list[dict[str, Any]]] = {}
    for base, items in by_base.items():
        split_oversized_group(base, items, max_group_size, groups)
    return groups

def safe_group_filename(group: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", group).strip("_")[:96] or "group"
    digest = hashlib.sha1(group.encode("utf-8", "replace")).hexdigest()[:10]
    return f"{base}_{digest}.json"


def update_counter(counter: Counter[str], values: Any) -> None:
    if isinstance(values, list):
        counter.update(str(value) for value in values if value)
    elif values:
        counter[str(values)] += 1


def group_payload(group_id: str, filename: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    counter_keys = (
        "statuses", "sources", "types", "domains", "schemas", "schemaGroups", "schemaKinds",
        "fieldSets", "prefixes", "families", "meanings", "tags", "registries", "classes", "layouts", "flags"
    )
    counters = {key: Counter() for key in counter_keys}
    total_bytes = 0
    for entry in entries:
        total_bytes += int(entry.get("size") or 0)
        update_counter(counters["statuses"], entry.get("status"))
        update_counter(counters["sources"], entry.get("source"))
        update_counter(counters["types"], entry.get("type"))
        update_counter(counters["domains"], entry.get("domain"))
        update_counter(counters["schemas"], entry.get("schema"))
        update_counter(counters["schemaGroups"], entry.get("schemaGroup"))
        update_counter(counters["schemaKinds"], entry.get("schemaKind"))
        update_counter(counters["fieldSets"], entry.get("fieldSet"))
        update_counter(counters["prefixes"], entry.get("prefix"))
        update_counter(counters["families"], entry.get("family"))
        update_counter(counters["meanings"], entry.get("meaning"))
        update_counter(counters["tags"], entry.get("tags"))
        update_counter(counters["registries"], entry.get("registry"))
        update_counter(counters["classes"], entry.get("classes"))
        update_counter(counters["layouts"], entry.get("layouts"))
        for key, value in (entry.get("flags") or {}).items():
            counters["flags"][str(key)] += int(value or 0)
    return {
        "id": group_id,
        "file": f"groups/{filename}",
        "files": len(entries),
        "bytes": total_bytes,
        "statuses": dict(sorted(counters["statuses"].items())),
        "sources": dict(sorted(counters["sources"].items())),
        "types": dict(sorted(counters["types"].items())),
        "domains": dict(counters["domains"].most_common(24)),
        "schemas": dict(counters["schemas"].most_common(24)),
        "schemaGroups": dict(counters["schemaGroups"].most_common(24)),
        "schemaKinds": dict(sorted(counters["schemaKinds"].items())),
        "fieldSets": dict(counters["fieldSets"].most_common(24)),
        "prefixes": dict(counters["prefixes"].most_common(24)),
        "families": dict(counters["families"].most_common(20)),
        "meanings": dict(counters["meanings"].most_common(24)),
        "tags": dict(counters["tags"].most_common(24)),
        "registries": dict(sorted(counters["registries"].items())),
        "classes": dict(counters["classes"].most_common(24)),
        "layouts": dict(counters["layouts"].most_common(24)),
        "flags": dict(sorted(counters["flags"].items())),
    }


def aggregate_counts(groups: list[dict[str, Any]]) -> dict[str, Any]:
    totals: dict[str, Any] = {"files": 0, "bytes": 0}
    counter_keys = (
        "statuses", "sources", "types", "domains", "schemas", "schemaGroups", "schemaKinds",
        "fieldSets", "prefixes", "families", "meanings", "tags", "registries", "classes", "layouts", "flags"
    )
    for key in counter_keys:
        totals[key] = Counter()
    for group in groups:
        totals["files"] += int(group.get("files") or 0)
        totals["bytes"] += int(group.get("bytes") or 0)
        for key in counter_keys:
            totals[key].update({str(k): int(v) for k, v in (group.get(key) or {}).items()})
    return {
        "files": totals["files"],
        "bytes": totals["bytes"],
        "statuses": dict(sorted(totals["statuses"].items())),
        "sources": dict(sorted(totals["sources"].items())),
        "types": dict(sorted(totals["types"].items())),
        "domains": dict(totals["domains"].most_common(120)),
        "schemas": dict(totals["schemas"].most_common(120)),
        "schemaGroups": dict(totals["schemaGroups"].most_common(120)),
        "schemaKinds": dict(sorted(totals["schemaKinds"].items())),
        "fieldSets": dict(totals["fieldSets"].most_common(120)),
        "prefixes": dict(totals["prefixes"].most_common(120)),
        "families": dict(totals["families"].most_common(80)),
        "meanings": dict(totals["meanings"].most_common(80)),
        "tags": dict(totals["tags"].most_common(80)),
        "registries": dict(sorted(totals["registries"].items())),
        "classes": dict(totals["classes"].most_common(80)),
        "layouts": dict(totals["layouts"].most_common(80)),
        "flags": dict(sorted(totals["flags"].items())),
    }

def iter_files(input_root: Path, sources: list[str], types: list[str]):
    for source in sources:
        for typ in types:
            root = input_root / source / "json_by_type" / typ
            if not root.exists():
                continue
            for path in sorted(root.glob("*.json")):
                if path.is_file():
                    yield source, typ, path


def build_index(export_root: Path, input_root: Path, output: Path, sources: list[str], types: list[str], max_group_size: int, limit: int = 0, jobs: int = 8) -> dict[str, Any]:
    source_iter = iter_files(input_root, sources, types)
    tasks = list(islice(source_iter, limit)) if limit else list(source_iter)

    def build_one(item):
        source, typ, path = item
        return extract_entry(path, export_root, source, typ)

    if jobs and jobs > 1 and len(tasks) > 1:
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as executor:
            entries = list(executor.map(build_one, tasks))
    else:
        entries = [build_one(item) for item in tasks]

    groups = split_groups(entries, max(1, max_group_size))
    groups_dir = output / "groups"
    groups_dir.mkdir(parents=True, exist_ok=True)
    for stale in groups_dir.glob("*.json"):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass

    group_records: list[dict[str, Any]] = []
    for group_id, group_entries in sorted(groups.items()):
        group_entries.sort(key=lambda item: (str(item.get("name") or "").lower(), str(item.get("file") or "")))
        filename = safe_group_filename(group_id)
        write_json(groups_dir / filename, {"group": group_id, "entries": group_entries})
        group_records.append(group_payload(group_id, filename, group_entries))

    counts = aggregate_counts(group_records)
    try:
        source_root = input_root.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        source_root = input_root.resolve().as_posix()
    try:
        export_root_rel = export_root.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        export_root_rel = export_root.resolve().as_posix()
    payload = {
        "generated": int(time.time()),
        "sourceRoot": source_root,
        "exportRoot": export_root_rel,
        "rawRoute": "/export_full/",
        "indexScope": "animestudio_json_by_type",
        "sources": sources,
        "types": types,
        "counts": counts,
        "requiresGroupSelection": int(counts.get("files") or 0) > AUTO_LOAD_ALL_FILE_LIMIT,
        "autoLoadAllLimit": AUTO_LOAD_ALL_FILE_LIMIT,
        "maxGroupSize": max_group_size,
        "groups": group_records,
    }
    write_json(output / "index.json", payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_root = args.export_root
    input_root = args.input_root or (export_root / DEFAULT_INPUT_REL)
    if not input_root.exists():
        raise SystemExit(f"Decoded AnimeStudio root not found: {input_root}")
    available_sources = detect_sources(input_root)
    sources = resolve_requested(args.sources, available_sources, default=DEFAULT_SOURCES)
    if not sources:
        raise SystemExit("No matching decoded sources found.")
    available_types = detect_types(input_root, sources)
    types = resolve_requested(args.types, available_types, default=DEFAULT_TYPES)
    if not types:
        raise SystemExit("No matching decoded json_by_type folders found.")
    args.output.mkdir(parents=True, exist_ok=True)
    payload = build_index(export_root, input_root, args.output, sources, types, args.max_group_size, args.limit, args.jobs)
    counts = payload["counts"]
    print(
        "Decoded index written:",
        normalize_posix(args.output),
        f"({counts['files']:,} files; {counts['bytes'] / (1024 * 1024):.1f} MiB; {len(payload['groups']):,} group(s))",
    )
    for typ, count in counts.get("types", {}).items():
        print(f"  {typ}: {count:,} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())