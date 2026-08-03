#!/usr/bin/env python3
"""Audit extracted Lua consumers for table, enum, CS, and UI/media references.

The VFS Lua block is already decrypted into plaintext under the structured
export roots. This report turns those scripts into a compact recovery map so
story/UI/table relationships can be prioritized without changing the normal
WebUI export path.

Output:

    reports/mission_order/lua_consumer_reference_audit.json
    reports/mission_order/lua_consumer_reference_audit.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_JSON = REPORT_DIR / "lua_consumer_reference_audit.json"
DEFAULT_MD = REPORT_DIR / "lua_consumer_reference_audit.md"
DEFAULT_LUA_ROOTS = (
    ROOT / "export_full" / "structured" / "Persistent" / "Lua",
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Lua",
)
DEFAULT_TABLE_ROOTS = (
    ROOT / "export_full" / "structured" / "Persistent" / "Table",
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Table",
)
DEFAULT_STORY_INDEX = ROOT / "webui" / "data" / "lang" / "CN" / "index.json"

GAME_ACTION_CALL_RE = re.compile(
    r"\b(?:CS\.Beyond\.Gameplay\.Actions\.)?GameAction\s*\.\s*"
    r"([A-Za-z_]\w*)\s*\("
)
LUA_STRING_ASSIGNMENT_RE = re.compile(
    r"(?m)^\s*(?:local\s+)?([A-Za-z_]\w*)\s*=\s*([\"'])(.*?)\2\s*$"
)
LUA_TABLE_LOOKUP_RE = re.compile(
    r"(?m)^\s*local\s+(?:(?P<ok>[A-Za-z_]\w*)\s*,\s*)?"
    r"(?P<row>[A-Za-z_]\w*)\s*=\s*Tables\.(?P<table>[A-Za-z_]\w*)"
    r"\s*:\s*(?:TryGetValue|GetValue)\s*\((?P<key>[^\r\n]*)\)\s*$"
)
LUA_TABLE_FIELD_ASSIGNMENT_RE = re.compile(
    r"(?m)^\s*(?:local\s+)?(?P<value>[A-Za-z_]\w*)\s*=\s*"
    r"(?P<row>[A-Za-z_]\w*)\.(?P<field>[A-Za-z_]\w*)\s*$"
)
LUA_TABLE_FIELD_EXPRESSION_RE = re.compile(
    r"(?P<row>[A-Za-z_]\w*)\.(?P<field>[A-Za-z_]\w*)"
)
STORY_ID_RE = re.compile(
    r"^(?:dlg|cutscene|radio|remotecomm|sns|black|text)_[A-Za-z0-9_]+$",
    re.IGNORECASE,
)

# Calls that either accept a Story id directly or dispatch an already-created
# cinematic handle. The audit reports every GameAction call separately, but
# this bounded set is the Story-playback recovery frontier.
STORY_PLAYBACK_GAME_ACTIONS: dict[str, dict[str, str]] = {
    "StartDialog": {"kind": "dialog", "argument": "story_id"},
    "PlayCutscene": {"kind": "cutscene", "argument": "story_id"},
    "PlayCutsceneAndGetHandle": {"kind": "cutscene", "argument": "story_id"},
    "PlayRadio": {"kind": "radio", "argument": "story_id"},
    "PlayRadioAndWait": {"kind": "radio", "argument": "story_id"},
    "StartRemoteComm": {"kind": "remotecomm", "argument": "story_id"},
    "StartForceSNS": {"kind": "sns", "argument": "story_id"},
    "ShowNarrativeBlackScreen": {"kind": "black", "argument": "story_id_or_data"},
    "DoPlayDialogByHandle": {"kind": "dialog", "argument": "cinematic_handle"},
    "DoPlayCutsceneByHandle": {"kind": "cutscene", "argument": "cinematic_handle"},
    "PlayCGByHandle": {"kind": "cutscene", "argument": "cinematic_handle"},
    "StartRemoteCommByHandle": {"kind": "remotecomm", "argument": "cinematic_handle"},
    "ShowNarrativeBlackScreenByHandle": {
        "kind": "black",
        "argument": "cinematic_handle",
    },
    "ShowUIReadingPopPanelByHandle": {
        "kind": "reading",
        "argument": "cinematic_handle",
    },
    "DoPlayForceSNSByHandle": {"kind": "sns", "argument": "cinematic_handle"},
}

REFERENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("tables", re.compile(r"\bTables\.([A-Za-z_]\w*)")),
    ("gEnums", re.compile(r"\bGEnums\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)")),
    ("csBeyond", re.compile(r"\bCS\.Beyond(?:\.[A-Za-z_]\w*)+")),
    ("contentParam", re.compile(r"\bcontentParam\s*\[\s*([^\]\r\n]+?)\s*\]")),
    ("dialogContentData", re.compile(r"\bdialogContentData\b")),
    ("remoteCommonData", re.compile(r"\bRemoteCommonData\b")),
    ("middleId", re.compile(r"\bmiddleId\b")),
    ("loadSprite", re.compile(r"\b(?:LoadSprite|LoadSpriteAsync|UIUtils\.getSpritePath)\b")),
    ("videoHelper", re.compile(r"\b(?:Video|PlayVideo|OpenVideo|SetVideo|Timeline)\w*\b", re.IGNORECASE)),
    ("audioHelper", re.compile(r"\b(?:Audio|PlayAudio|PostEvent|PlayVoice|voiceId|audioId)\w*\b", re.IGNORECASE)),
)

FOCUS_PATTERNS: dict[str, re.Pattern[str]] = {
    "sns": re.compile(
        r"\bSNS\b|PhaseSNS|SNSUtils|sNS(?:Dialog|Chat)Table|\bfriend\b|\bFriend\b|\bmoment\b",
        re.IGNORECASE,
    ),
    "remotecomm": re.compile(r"RemoteComm|REMOTE_COMM|remote\s*_?\s*comm|\bradio\b|\b[Rr]adio[A-Za-z_]\w*|radioTable", re.IGNORECASE),
    "dialog": re.compile(r"\bDialog\b|\bDIALOG\b|dialogue|contentParam|middleId|dialogContentData|DialogConst", re.IGNORECASE),
    "mapmark": re.compile(r"map\s*_?\s*mark|mapmark|MarkType|MapResource|MapUtils|UI_SPRITE_MAP_MARK", re.IGNORECASE),
    "mission": re.compile(r"\bMission\b|\bMISSION\b|missionTable|MissionSystem|\bquest\b|\btask\b|TaskTrack", re.IGNORECASE),
}


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def parse_csv(values: str) -> list[str]:
    out: list[str] = []
    for value in values.split(","):
        item = value.strip().lower()
        if item and item not in out:
            out.append(item)
    return out


def root_label(root: Path) -> str:
    parts = root.resolve().parts
    for name in ("Persistent", "StreamingAssets"):
        if name in parts:
            return name
    return root.name


def lua_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("**/*.lua"))


def table_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def module_key(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return repo_rel(path)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def line_text(text: str, offset: int) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end < 0:
        end = len(text)
    return text[start:end].strip()[:240]


def add_example(bucket: list[dict[str, Any]], row: dict[str, Any], limit: int) -> None:
    if len(bucket) >= limit:
        return
    bucket.append(row)


def first_lua_argument(text: str, open_paren: int) -> str:
    """Return the first call argument with strings/nested delimiters respected."""
    depth = 0
    quote = ""
    escaped = False
    start = open_paren + 1
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in "({[":
            depth += 1
        elif char in ")}]":
            if depth == 0:
                return text[start:index].strip()
            depth -= 1
        elif char == "," and depth == 0:
            return text[start:index].strip()
    return text[start:].strip()


def load_story_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(row.get("k") or "")
        for row in payload.get("entries") or []
        if isinstance(row, dict) and row.get("k")
    }


def load_table_payloads(
    table_index: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Load one effective original JSON table per case-insensitive table name."""
    payloads: dict[str, dict[str, Any]] = {}
    for folded_name, index_row in sorted(table_index.items()):
        paths = [ROOT / str(value) for value in index_row.get("paths") or []]
        source_path = next((path for path in paths if path.is_file()), None)
        if source_path is None:
            continue
        try:
            raw = source_path.read_bytes()
            payload = json.loads(raw.decode("utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        payloads[folded_name] = {
            "table": str(index_row.get("table") or source_path.stem),
            "sourcePath": repo_rel(source_path),
            "sourceSha256": hashlib.sha256(raw).hexdigest(),
            "rows": payload,
        }
    return payloads


def table_field_resolution(
    text: str,
    argument: str,
    *,
    table_payloads: dict[str, dict[str, Any]],
    story_keys: set[str],
) -> dict[str, Any] | None:
    """Resolve a simple Lua table-row field flowing into a GameAction call.

    The rule is structural rather than table-specific: a local row returned by
    ``Tables.<name>:TryGetValue`` may flow either directly or through one local
    field assignment into the first GameAction argument.  A Story id is exact
    only when the current original table has one possible non-empty value for
    that field. Multiple current rows remain candidates because the lookup key
    has not been resolved.
    """
    row_origins = {
        match.group("row"): {
            "table": match.group("table"),
            "keyExpression": match.group("key").strip(),
        }
        for match in LUA_TABLE_LOOKUP_RE.finditer(text)
    }
    value_origins = {
        match.group("value"): {
            "row": match.group("row"),
            "field": match.group("field"),
        }
        for match in LUA_TABLE_FIELD_ASSIGNMENT_RE.finditer(text)
    }
    origin = value_origins.get(argument.strip())
    if origin is None:
        direct = LUA_TABLE_FIELD_EXPRESSION_RE.fullmatch(argument.strip())
        if direct:
            origin = {"row": direct.group("row"), "field": direct.group("field")}
    if origin is None:
        return None
    lookup = row_origins.get(origin["row"])
    if lookup is None:
        return None
    table = table_payloads.get(str(lookup["table"]).casefold())
    if table is None:
        return None

    field = str(origin["field"])
    folded_story_keys = {key.casefold(): key for key in story_keys}
    candidates: list[dict[str, Any]] = []
    nonempty_values: set[str] = set()
    for table_key, raw_row in sorted((table.get("rows") or {}).items()):
        if not isinstance(raw_row, dict):
            continue
        raw_value = raw_row.get(field)
        if not isinstance(raw_value, str) or not raw_value:
            continue
        nonempty_values.add(raw_value)
        canonical = (
            raw_value if raw_value in story_keys
            else folded_story_keys.get(raw_value.casefold(), "")
        )
        if not canonical:
            continue
        candidates.append({
            "tableKey": str(table_key),
            "rawValue": raw_value,
            "canonicalStoryKey": canonical,
            "registryStatus": (
                "exact_registry_match"
                if raw_value == canonical
                else "case_mismatch_registry_match"
            ),
            "rowFields": {
                str(key): value
                for key, value in raw_row.items()
                if isinstance(value, (str, int, float, bool)) or value is None
            },
        })
    exact_singleton = (
        len(nonempty_values) == 1
        and len(candidates) == 1
        and candidates[0]["registryStatus"] == "exact_registry_match"
    )
    mismatch_singleton = (
        len(nonempty_values) == 1
        and len(candidates) == 1
        and candidates[0]["registryStatus"] == "case_mismatch_registry_match"
    )
    return {
        "table": table["table"],
        "tableSourcePath": table["sourcePath"],
        "tableSourceSha256": table["sourceSha256"],
        "rowVariable": origin["row"],
        "field": field,
        "lookupKeyExpression": lookup["keyExpression"],
        "candidateRows": candidates,
        "nonemptyValueCount": len(nonempty_values),
        "exactSingleton": exact_singleton,
        "caseMismatchSingleton": mismatch_singleton,
    }


def scan_game_action_calls(
    text: str,
    *,
    rel: str,
    story_keys: set[str],
    table_payloads: dict[str, dict[str, Any]] | None = None,
    source_path: str = "",
    source_sha256: str = "",
) -> list[dict[str, Any]]:
    assignments = {
        match.group(1): match.group(3)
        for match in LUA_STRING_ASSIGNMENT_RE.finditer(text)
    }
    story_keys_folded = {key.casefold(): key for key in story_keys}
    rows: list[dict[str, Any]] = []
    for match in GAME_ACTION_CALL_RE.finditer(text):
        method = match.group(1)
        argument = first_lua_argument(text, match.end() - 1)
        resolved = ""
        resolution = "unresolved_expression"
        direct = re.fullmatch(r"\s*([\"'])(.*?)\1\s*", argument, re.DOTALL)
        if direct:
            resolved = direct.group(2)
            resolution = "direct_literal"
        elif re.fullmatch(r"[A-Za-z_]\w*", argument or "") and argument in assignments:
            resolved = assignments[argument]
            resolution = "module_constant"

        table_resolution = table_field_resolution(
            text,
            argument,
            table_payloads=table_payloads or {},
            story_keys=story_keys,
        )
        if not resolved and table_resolution:
            candidates = table_resolution["candidateRows"]
            if table_resolution["exactSingleton"]:
                resolved = str(candidates[0]["rawValue"])
                resolution = "table_field_singleton"
            elif table_resolution["caseMismatchSingleton"]:
                resolved = str(candidates[0]["rawValue"])
                resolution = "table_field_singleton"
            else:
                resolution = "table_field_candidates"

        registry_status = "not_story_shaped"
        canonical_key = ""
        if resolved and STORY_ID_RE.fullmatch(resolved):
            if resolved in story_keys:
                registry_status = "exact_registry_match"
                canonical_key = resolved
            elif resolved.casefold() in story_keys_folded:
                registry_status = "case_mismatch_registry_match"
                canonical_key = story_keys_folded[resolved.casefold()]
            else:
                registry_status = "story_shaped_not_in_registry"

        window = text[max(0, match.start() - 1200): min(len(text), match.end() + 1200)]
        nearby_tables = sorted(set(re.findall(r"\bTables\.([A-Za-z_]\w*)", window)))
        playback = STORY_PLAYBACK_GAME_ACTIONS.get(method)
        rows.append(
            {
                "module": rel,
                "sourcePath": source_path or None,
                "sourceSha256": source_sha256 or None,
                "line": line_number(text, match.start()),
                "method": method,
                "classification": "story_playback" if playback else "other_game_action",
                "playbackKind": playback.get("kind") if playback else None,
                "argumentSemantics": playback.get("argument") if playback else None,
                "firstArgument": argument[:300],
                "literalResolution": resolution,
                "resolvedLiteral": resolved or None,
                "registryStatus": registry_status,
                "canonicalStoryKey": canonical_key or None,
                "nearbyTables": nearby_tables,
                "tableFieldResolution": table_resolution,
                "context": line_text(text, match.start()),
            }
        )
    return rows


def scan_references(
    text: str,
    *,
    rel: str,
    example_limit: int,
) -> tuple[dict[str, Counter[str]], dict[str, list[dict[str, Any]]]]:
    counts: dict[str, Counter[str]] = {name: Counter() for name, _pattern in REFERENCE_PATTERNS}
    examples: dict[str, list[dict[str, Any]]] = {name: [] for name, _pattern in REFERENCE_PATTERNS}
    for category, pattern in REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            value = value.strip()
            counts[category][value] += 1
            add_example(
                examples[category],
                {
                    "path": rel,
                    "line": line_number(text, match.start()),
                    "value": value,
                    "context": line_text(text, match.start()),
                },
                example_limit,
            )
    return counts, examples


def focus_hits(text: str, rel: str, focus_names: list[str], example_limit: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in focus_names:
        pattern = FOCUS_PATTERNS.get(name)
        if not pattern:
            continue
        path_matches = list(pattern.finditer(rel))
        text_matches = list(pattern.finditer(text))
        if not path_matches and not text_matches:
            continue
        examples = []
        for match in path_matches[:example_limit]:
            examples.append(
                {
                    "line": None,
                    "term": match.group(0),
                    "context": f"[path] {rel}",
                }
            )
        for match in text_matches[: max(0, example_limit - len(examples))]:
            examples.append(
                {
                    "line": line_number(text, match.start()),
                    "term": match.group(0),
                    "context": line_text(text, match.start()),
                }
            )
        out[name] = {"hitCount": len(path_matches) + len(text_matches), "examples": examples}
    return out


def counter_rows(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def build_table_index(table_roots: list[Path]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    summaries = []
    for root in table_roots:
        files = table_files(root)
        label = root_label(root)
        summaries.append({"root": repo_rel(root), "label": label, "fileCount": len(files)})
        for path in files:
            stem = path.stem
            key = stem.casefold()
            row = index.setdefault(key, {"table": stem, "roots": [], "paths": []})
            row["roots"].append(label)
            row["paths"].append(repo_rel(path))
    return index, summaries


def table_reference_availability(
    table_refs: Counter[str],
    table_index: dict[str, dict[str, Any]],
    *,
    limit: int,
) -> dict[str, Any]:
    matched = []
    unmatched = []
    for value, count in table_refs.most_common():
        row = table_index.get(value.casefold())
        out = {"value": value, "count": count}
        if row:
            out.update({"table": row["table"], "roots": sorted(set(row["roots"])), "paths": row["paths"][:4]})
            matched.append(out)
        else:
            unmatched.append(out)
    return {
        "availableTableCount": len(table_index),
        "referencedTableCount": len(table_refs),
        "matchedReferencedTableCount": len(matched),
        "unmatchedReferencedTableCount": len(unmatched),
        "matchedReferenceUseCount": sum(int(row["count"]) for row in matched),
        "unmatchedReferenceUseCount": sum(int(row["count"]) for row in unmatched),
        "topMatched": matched[:limit],
        "topUnmatched": unmatched[:limit],
    }


def merge_counter_dicts(target: dict[str, Counter[str]], source: dict[str, Counter[str]]) -> None:
    for category, counter in source.items():
        target[category].update(counter)


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    focus_names = parse_csv(args.focus)
    unknown_focus = sorted(name for name in focus_names if name not in FOCUS_PATTERNS)
    focus_names = [name for name in focus_names if name in FOCUS_PATTERNS]

    lua_roots = [root.resolve() for root in (args.lua_root or list(DEFAULT_LUA_ROOTS))]
    table_roots = [root.resolve() for root in (args.table_root or list(DEFAULT_TABLE_ROOTS))]
    story_index = args.story_index.resolve()
    story_keys = load_story_keys(story_index)
    table_index, table_root_summaries = build_table_index(table_roots)
    table_payloads = load_table_payloads(table_index)
    modules: dict[str, dict[str, Any]] = {}
    root_summaries = []
    read_errors = []

    for root in lua_roots:
        files = lua_files(root)
        label = root_label(root)
        byte_total = 0
        for path in files:
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8-sig", errors="replace")
            except OSError as exc:
                read_errors.append({"path": repo_rel(path), "error": str(exc)})
                continue
            byte_total += len(raw)
            rel = module_key(path, root)
            sha = hashlib.sha256(raw).hexdigest()
            row = modules.setdefault(
                rel,
                {
                    "module": rel,
                    "roots": [],
                    "sha256ByRoot": {},
                    "byteLengthByRoot": {},
                    "text": text,
                    "canonicalPath": repo_rel(path),
                    "canonicalSha256": sha,
                },
            )
            row["roots"].append(label)
            row["sha256ByRoot"][label] = sha
            row["byteLengthByRoot"][label] = len(raw)
            if label == "Persistent" or "Persistent" not in row["roots"]:
                row["text"] = text
                row["canonicalPath"] = repo_rel(path)
                row["canonicalSha256"] = sha
        root_summaries.append(
            {
                "root": repo_rel(root),
                "label": label,
                "fileCount": len(files),
                "byteLength": byte_total,
            }
        )

    global_counts: dict[str, Counter[str]] = {name: Counter() for name, _pattern in REFERENCE_PATTERNS}
    global_examples: dict[str, list[dict[str, Any]]] = {name: [] for name, _pattern in REFERENCE_PATTERNS}
    focus_counters: dict[str, dict[str, Counter[str]]] = {
        name: {category: Counter() for category, _pattern in REFERENCE_PATTERNS}
        for name in focus_names
    }
    focus_module_counts: Counter[str] = Counter()
    focus_files: dict[str, list[dict[str, Any]]] = {name: [] for name in focus_names}
    module_findings = []
    table_module_edges = []
    game_action_calls: list[dict[str, Any]] = []

    for rel, row in sorted(modules.items()):
        text = str(row.get("text") or "")
        game_action_calls.extend(
            scan_game_action_calls(
                text,
                rel=rel,
                story_keys=story_keys,
                table_payloads=table_payloads,
                source_path=str(row.get("canonicalPath") or ""),
                source_sha256=str(row.get("canonicalSha256") or ""),
            )
        )
        counts, examples = scan_references(text, rel=rel, example_limit=args.example_limit)
        merge_counter_dicts(global_counts, counts)
        for category, rows in examples.items():
            for item in rows:
                add_example(global_examples[category], item, args.example_limit)

        hits = focus_hits(text, rel, focus_names, args.focus_example_limit)
        for table_name, count in counts["tables"].items():
            table_row = table_index.get(table_name.casefold())
            edge = {
                "module": rel,
                "path": row.get("canonicalPath"),
                "value": table_name,
                "count": count,
                "focus": sorted(hits.keys()),
                "matched": bool(table_row),
            }
            if table_row:
                edge.update({
                    "table": table_row["table"],
                    "roots": sorted(set(table_row["roots"])),
                    "paths": table_row["paths"][:4],
                })
            table_module_edges.append(edge)

        if hits:
            for focus_name in hits:
                focus_module_counts[focus_name] += 1
                merge_counter_dicts(focus_counters[focus_name], counts)
                focus_files[focus_name].append(
                    {
                        "module": rel,
                        "path": row.get("canonicalPath"),
                        "roots": sorted(row.get("roots") or []),
                        "hitCount": hits[focus_name]["hitCount"],
                        "topTables": counter_rows(counts["tables"], 8),
                        "topEnums": counter_rows(counts["gEnums"], 8),
                        "topCsBeyond": counter_rows(counts["csBeyond"], 8),
                        "examples": hits[focus_name]["examples"],
                    }
                )
            module_findings.append(
                {
                    "module": rel,
                    "path": row.get("canonicalPath"),
                    "roots": sorted(row.get("roots") or []),
                    "focus": {name: data["hitCount"] for name, data in sorted(hits.items())},
                    "referenceCounts": {category: sum(counter.values()) for category, counter in counts.items()},
                    "topTables": counter_rows(counts["tables"], 8),
                    "topEnums": counter_rows(counts["gEnums"], 8),
                    "topCsBeyond": counter_rows(counts["csBeyond"], 8),
                }
            )

    module_findings.sort(
        key=lambda row: (
            -sum(int(value) for value in (row.get("focus") or {}).values()),
            str(row.get("module") or ""),
        )
    )
    table_module_edges.sort(
        key=lambda row: (
            not bool(row.get("matched")),
            -int(row.get("count") or 0),
            str(row.get("table") or row.get("value") or ""),
            str(row.get("module") or ""),
        )
    )

    focus_payload = {}
    for name in focus_names:
        top_focus_files = sorted(
            focus_files[name],
            key=lambda row: (-int(row.get("hitCount") or 0), str(row.get("module") or "")),
        )[: args.max_focus_files]
        focus_payload[name] = {
            "fileCount": focus_module_counts[name],
            "topFiles": top_focus_files,
            "topReferences": {
                category: counter_rows(counter, args.top_limit)
                for category, counter in focus_counters[name].items()
                if counter
            },
        }

    table_availability = table_reference_availability(global_counts["tables"], table_index, limit=args.top_limit)

    duplicate_modules = [
        {
            "module": rel,
            "roots": sorted(row.get("roots") or []),
            "sha256ByRoot": row.get("sha256ByRoot"),
            "sameContent": len(set((row.get("sha256ByRoot") or {}).values())) == 1,
        }
        for rel, row in sorted(modules.items())
        if len(row.get("roots") or []) > 1
    ]
    same_content_count = sum(1 for row in duplicate_modules if row["sameContent"])
    playback_calls = [
        row for row in game_action_calls
        if row["classification"] == "story_playback"
    ]
    playback_method_counts = Counter(row["method"] for row in playback_calls)
    playback_resolution_counts = Counter(
        row["literalResolution"] for row in playback_calls
    )
    playback_registry_counts = Counter(row["registryStatus"] for row in playback_calls)

    return {
        "schemaVersion": "luaConsumerReferenceAudit.v3",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "luaRoots": [repo_rel(root) for root in lua_roots],
            "tableRoots": [repo_rel(root) for root in table_roots],
            "focus": focus_names,
            "unknownFocus": unknown_focus,
            "storyIndex": repo_rel(story_index),
            "storyRegistryKeys": len(story_keys),
        },
        "settings": {
            "topLimit": args.top_limit,
            "exampleLimit": args.example_limit,
            "focusExampleLimit": args.focus_example_limit,
            "maxFocusFiles": args.max_focus_files,
            "maxModuleFindings": args.max_module_findings,
            "maxTableModuleEdges": args.max_table_module_edges,
        },
        "summary": {
            "rootCount": len(lua_roots),
            "rootFileCount": sum(row["fileCount"] for row in root_summaries),
            "uniqueModuleCount": len(modules),
            "duplicateModuleCount": len(duplicate_modules),
            "duplicateSameContentCount": same_content_count,
            "readErrorCount": len(read_errors),
            "referenceCounts": {category: sum(counter.values()) for category, counter in global_counts.items()},
            "matchedTableReferenceCount": table_availability["matchedReferencedTableCount"],
            "unmatchedTableReferenceCount": table_availability["unmatchedReferencedTableCount"],
            "tableModuleEdgeCount": len(table_module_edges),
            "focusFileCounts": {name: focus_module_counts[name] for name in focus_names},
            "gameActionCallCount": len(game_action_calls),
            "gameActionMethodCount": len({row["method"] for row in game_action_calls}),
            "storyPlaybackCallCount": len(playback_calls),
            "storyPlaybackModuleCount": len({row["module"] for row in playback_calls}),
            "storyPlaybackMethodCounts": dict(sorted(playback_method_counts.items())),
            "storyPlaybackResolutionCounts": dict(
                sorted(playback_resolution_counts.items())
            ),
            "storyPlaybackRegistryCounts": dict(
                sorted(playback_registry_counts.items())
            ),
        },
        "rootSummaries": root_summaries,
        "tableRootSummaries": table_root_summaries,
        "tableReferenceAvailability": table_availability,
        "topReferences": {
            category: counter_rows(counter, args.top_limit)
            for category, counter in global_counts.items()
            if counter
        },
        "examples": global_examples,
        "focusAreas": focus_payload,
        "moduleFindings": module_findings[: args.max_module_findings],
        "tableModuleEdges": table_module_edges[: args.max_table_module_edges],
        "gameActionAudit": {
            "evidencePolicy": {
                "scope": (
                    "All direct GameAction.* calls in each unique Lua module are "
                    "enumerated. The Story subset is a bounded allowlist of native "
                    "playback entry points."
                ),
                "literalResolution": (
                    "Direct quoted arguments and simple local string assignments are "
                    "resolved. A simple Tables.<name> row field is also resolved when "
                    "the current original table has exactly one non-empty candidate; "
                    "multi-row fields, function parameters, handles, concatenation, and "
                    "general control flow remain unresolved."
                ),
                "case": (
                    "Exact registry spelling is proven separately from a case-folded "
                    "candidate. A case mismatch is never promoted to a Story binding."
                ),
                "ownership": (
                    "A Lua call proves that the controller owns playback. It creates no "
                    "mission/quest attachment unless the same consumed route carries an "
                    "exact mission or quest identity."
                ),
                "nearbyTables": (
                    "Table names within a bounded source window are triage hints, not "
                    "data-flow proof."
                ),
            },
            "methodCounts": dict(sorted(Counter(
                row["method"] for row in game_action_calls
            ).items())),
            "storyPlaybackCalls": playback_calls,
            "allCalls": game_action_calls,
        },
        "duplicateModulesSample": duplicate_modules[: args.top_limit],
        "readErrors": read_errors[:100],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    settings = payload.get("settings") or {}
    top_limit = int(settings.get("topLimit") or 20)
    lines = [
        "# Lua Consumer Reference Audit",
        "",
        f"- Lua roots scanned: `{summary.get('rootCount')}`",
        f"- Lua files scanned across roots: `{summary.get('rootFileCount')}`",
        f"- unique Lua modules: `{summary.get('uniqueModuleCount')}`",
        f"- duplicate modules with identical bytes: `{summary.get('duplicateSameContentCount')}` / `{summary.get('duplicateModuleCount')}`",
        f"- read errors: `{summary.get('readErrorCount')}`",
        "",
        "## Focus Areas",
        "",
    ]

    focus_counts = summary.get("focusFileCounts") or {}
    for name, count in focus_counts.items():
        lines.append(f"- `{md_escape(name)}` files: `{count}`")

    table_availability = payload.get("tableReferenceAvailability") or {}
    lines.extend(["", "## Table Reference Availability", ""])
    lines.append(f"- Exported table files indexed: `{table_availability.get('availableTableCount')}`")
    lines.append(f"- Referenced Lua table names: `{table_availability.get('referencedTableCount')}`")
    lines.append(f"- Matched referenced table names: `{table_availability.get('matchedReferencedTableCount')}`")
    lines.append(f"- Unmatched referenced table names: `{table_availability.get('unmatchedReferencedTableCount')}`")
    lines.append(f"- Lua module-to-table edge candidates: `{summary.get('tableModuleEdgeCount')}`")
    unmatched = table_availability.get("topUnmatched") or []
    if unmatched:
        compact_unmatched = ", ".join(f"{item['value']} ({item['count']})" for item in unmatched[:10])
        lines.append(f"- Top unmatched: {md_escape(compact_unmatched)}")

    game_action = payload.get("gameActionAudit") or {}
    lines.extend(["", "## GameAction Story Playback Census", ""])
    lines.append(
        f"- all direct `GameAction.*` calls: `{summary.get('gameActionCallCount')}` "
        f"across `{summary.get('gameActionMethodCount')}` methods"
    )
    lines.append(
        f"- Story-playback calls: `{summary.get('storyPlaybackCallCount')}` "
        f"across `{summary.get('storyPlaybackModuleCount')}` modules"
    )
    lines.append(
        f"- registry keys used for exact-case validation: "
        f"`{(payload.get('metadata') or {}).get('storyRegistryKeys')}`"
    )
    for name, value in (summary.get("storyPlaybackRegistryCounts") or {}).items():
        lines.append(f"- `{md_escape(name)}`: `{value}`")
    lines.extend(
        [
            "",
            "| module | line | GameAction | first argument | resolution | registry | nearby tables |",
            "| --- | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for row in game_action.get("storyPlaybackCalls") or []:
        tables = ", ".join(row.get("nearbyTables") or [])
        lines.append(
            "| `{module}` | {line} | `{method}` | `{argument}` | `{resolution}` | "
            "`{registry}` | {tables} |".format(
                module=md_escape(str(row.get("module") or "")),
                line=row.get("line") or "",
                method=md_escape(str(row.get("method") or "")),
                argument=md_escape(str(row.get("firstArgument") or "")),
                resolution=md_escape(str(row.get("literalResolution") or "")),
                registry=md_escape(str(row.get("registryStatus") or "")),
                tables=md_escape(tables),
            )
        )
    policy = game_action.get("evidencePolicy") or {}
    lines.extend(["", "Evidence boundary:", ""])
    lines.extend(f"- **{md_escape(key)}:** {md_escape(value)}" for key, value in policy.items())

    lines.extend(["", "## Top References", ""])
    for category, rows in (payload.get("topReferences") or {}).items():
        compact = ", ".join(f"{item['value']} ({item['count']})" for item in rows[:10])
        lines.append(f"- `{md_escape(category)}`: {md_escape(compact)}")

    for name, area in (payload.get("focusAreas") or {}).items():
        lines.extend(["", f"## Focus: {md_escape(name)}", ""])
        lines.append(f"- Files: `{area.get('fileCount')}`")
        refs = area.get("topReferences") or {}
        for category in ("tables", "gEnums", "csBeyond", "contentParam", "loadSprite", "videoHelper", "audioHelper"):
            rows = refs.get(category) or []
            if not rows:
                continue
            compact = ", ".join(f"{item['value']} ({item['count']})" for item in rows[:8])
            lines.append(f"- `{category}`: {md_escape(compact)}")
        lines.append("")
        lines.append("Top files:")
        for row in (area.get("topFiles") or [])[:top_limit]:
            focus_examples = "; ".join(
                f"{'path' if ex.get('line') is None else 'L' + str(ex.get('line'))} {ex.get('term')}"
                for ex in (row.get("examples") or [])[:3]
            )
            lines.append(
                f"- `{md_escape(row.get('module', ''))}` hits=`{row.get('hitCount')}` "
                f"roots=`{','.join(row.get('roots') or [])}`"
            )
            if focus_examples:
                lines.append(f"  - examples: {md_escape(focus_examples)}")

    lines.extend(["", "## Interpretation", ""])
    lines.append(
        "- Lua scripts provide concrete consumer evidence for table rows, enum branches, CS API calls, and UI/media helpers. "
        "This report does not alter WebUI export behavior; it identifies where source graph or Story/WebUI builders can add edges next."
    )
    lines.append(
        "- Persistent and StreamingAssets Lua modules are expected to duplicate heavily. Use unique module counts for semantic coverage and root file counts for VFS coverage."
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lua-root", type=Path, action="append", help="Lua root to scan; repeatable")
    parser.add_argument("--table-root", type=Path, action="append", help="Exported Table JSON root for Tables.* availability checks; repeatable")
    parser.add_argument(
        "--story-index",
        type=Path,
        default=DEFAULT_STORY_INDEX,
        help="Generated Story index used only for exact-case literal validation",
    )
    parser.add_argument("--focus", default="sns,remotecomm,dialog,mapmark,mission")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--top-limit", type=int, default=30)
    parser.add_argument("--example-limit", type=int, default=20)
    parser.add_argument("--focus-example-limit", type=int, default=4)
    parser.add_argument("--max-focus-files", type=int, default=30)
    parser.add_argument("--max-module-findings", type=int, default=300)
    parser.add_argument("--max-table-module-edges", type=int, default=2500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(f"Lua consumer reference audit: {args.json}")
    print(f"Lua consumer reference report: {args.markdown}")
    print(
        "uniqueModules="
        f"{summary['uniqueModuleCount']} "
        f"rootFiles={summary['rootFileCount']} "
        f"focusFiles={json.dumps(summary['focusFileCounts'], sort_keys=True)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
