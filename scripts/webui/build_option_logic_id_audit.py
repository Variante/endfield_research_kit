#!/usr/bin/env python3
"""Audit option `logicId` references outside dialog Timeline option clips.

`build_option_playable_semantics_audit.py` narrows the remaining inferred
option-response queue to groups where `logicId` is the only non-default decoded
field. This script asks the next question: do those `logicId` values appear in
mission, level-script, table, or Lua sources in a way that could explain branch
targets?
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import build_option_playable_semantics_audit as semantics
from common import (
    EXPORT_ROOT,
    ROOT,
    md_escape,
    parse_group_filters,
    read_json,
    rel_path,
    safe_key,
    safe_report_suffix,
    split_csv_values,
    write_report_json as write_json,
)


STRUCTURED_ROOT = EXPORT_ROOT / "structured" / "StreamingAssets"
DATA_JSON_ROOT = STRUCTURED_ROOT / "Data" / "Json"
TABLE_ROOT = STRUCTURED_ROOT / "Table"
LUA_ROOT = STRUCTURED_ROOT / "Lua" / "Data" / "LuaScripts"

DEFAULT_SCAN_TARGETS = (
    ("table", TABLE_ROOT),
    ("missionRuntime", DATA_JSON_ROOT / "MissionRuntimeAsset"),
    ("levelScript", DATA_JSON_ROOT / "LevelScriptData"),
    ("levelScriptTemplate", DATA_JSON_ROOT / "LevelScriptTemplateData"),
    ("gameplayConfig", DATA_JSON_ROOT / "GameplayConfig"),
    ("gameplayConfigFile", DATA_JSON_ROOT / "GameplayConfigWorldEntityRegistry.json"),
    ("gameplayConfigFile", DATA_JSON_ROOT / "GameplayConfigNpcProxyTable.json"),
    ("gameplayConfigFile", DATA_JSON_ROOT / "GameplayConfigMissionAreaTable.json"),
)

LUA_CONSUMER_TERMS = (
    "logicId",
    "LogicId",
    "LOGIC_ID",
    "optionId",
    "OptionId",
    "selectedFlag",
    "setGreyed",
    "targetFinishNum",
    "changeFinishNum",
)

CONTEXT_FIELDS = (
    "$type",
    "id",
    "_ID",
    "ID",
    "_uid",
    "uid",
    "key",
    "name",
    "missionId",
    "questId",
    "levelId",
    "sceneId",
    "_sceneId",
    "dialogId",
    "_dialogId",
    "snsDialogId",
    "_radioId",
    "_cutsceneId",
    "_remoteCommId",
    "markInsId",
    "markInfoId",
    "npcProxyId",
    "missionAreaId",
    "templateId",
)


def collect_logic_options(
    language: str,
    conv_dir: Path,
    timeline_orders_path: Path,
    *,
    story_filters: list[str],
    group_filters: set[int],
) -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    rows = semantics.collect_rows(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
        only_interesting=True,
    )
    logic_options: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for option in row.get("options") or []:
            best_row = option.get("bestRow") or {}
            logic_id = best_row.get("logicId")
            if not isinstance(logic_id, int) or logic_id == 0:
                continue
            logic_options[logic_id].append({
                "storyKey": row.get("storyKey"),
                "mission": row.get("mission"),
                "group": row.get("group"),
                "after": row.get("after"),
                "optionId": option.get("optionId"),
                "optionIndex": best_row.get("optionIndex"),
                "candidateLineId": option.get("candidateLineId"),
                "commonContinuationLineId": row.get("commonContinuationLineId"),
                "logicId": logic_id,
                "assetTrack": best_row.get("assetTrack"),
            })
    return rows, dict(sorted(logic_options.items()))


def iter_json_paths(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".json":
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*.json") if p.is_file())
    return []


def source_mission_for_path(path: Path, source_group: str) -> str:
    if source_group == "missionRuntime":
        return path.stem
    return ""


def source_level_for_path(path: Path, source_group: str) -> str:
    if source_group in {"levelScript", "levelScriptTemplate"}:
        parent = path.parent.name
        return parent if parent != source_group else ""
    return ""


def compact_context(stack: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for obj in reversed(stack):
        for field in CONTEXT_FIELDS:
            if field in out or field not in obj:
                continue
            value = obj.get(field)
            if isinstance(value, (str, int, float, bool)) or value is None:
                out[field] = value
            elif isinstance(value, dict) and "constValue" in value:
                const_value = value.get("constValue")
                if isinstance(const_value, (str, int, float, bool)) or const_value is None:
                    out[field] = const_value
        if len(out) >= 8:
            break
    return out


def walk_json_for_logic_ids(
    node: Any,
    *,
    json_path: str,
    stack: list[dict[str, Any]],
    source_group: str,
    source_path: Path,
    target_logic_ids: set[int],
    exact_refs: list[dict[str, Any]],
    field_counts: Counter[str],
    value_counts: Counter[str],
) -> None:
    if isinstance(node, dict):
        stack.append(node)
        for key, value in node.items():
            child_path = f"{json_path}.{key}" if json_path else str(key)
            if key == "logicId" and isinstance(value, int):
                field_counts[f"{source_group}:{child_path}"] += 1
                value_counts[f"{source_group}:{value}"] += 1
                if value in target_logic_ids:
                    exact_refs.append({
                        "logicId": value,
                        "sourceGroup": source_group,
                        "path": rel_path(source_path),
                        "jsonPath": child_path,
                        "sourceMission": source_mission_for_path(source_path, source_group),
                        "sourceLevel": source_level_for_path(source_path, source_group),
                        "context": compact_context(stack),
                    })
            walk_json_for_logic_ids(
                value,
                json_path=child_path,
                stack=stack,
                source_group=source_group,
                source_path=source_path,
                target_logic_ids=target_logic_ids,
                exact_refs=exact_refs,
                field_counts=field_counts,
                value_counts=value_counts,
            )
        stack.pop()
    elif isinstance(node, list):
        for index, item in enumerate(node):
            child_path = f"{json_path}[{index}]"
            walk_json_for_logic_ids(
                item,
                json_path=child_path,
                stack=stack,
                source_group=source_group,
                source_path=source_path,
                target_logic_ids=target_logic_ids,
                exact_refs=exact_refs,
                field_counts=field_counts,
                value_counts=value_counts,
            )


def scan_json_sources(scan_targets: list[tuple[str, Path]], target_logic_ids: set[int]) -> dict[str, Any]:
    exact_refs: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()
    value_counts: Counter[str] = Counter()
    files_by_group: Counter[str] = Counter()
    parsed_files = 0
    skipped_files = 0
    for source_group, root in scan_targets:
        for path in iter_json_paths(root):
            files_by_group[source_group] += 1
            payload = read_json(path, None)
            if payload is None:
                skipped_files += 1
                continue
            parsed_files += 1
            walk_json_for_logic_ids(
                payload,
                json_path="$",
                stack=[],
                source_group=source_group,
                source_path=path,
                target_logic_ids=target_logic_ids,
                exact_refs=exact_refs,
                field_counts=field_counts,
                value_counts=value_counts,
            )
    exact_refs.sort(key=lambda ref: (ref["logicId"], ref["sourceGroup"], ref["path"], ref["jsonPath"]))
    return {
        "parsedFileCount": parsed_files,
        "skippedFileCount": skipped_files,
        "filesByGroup": dict(sorted(files_by_group.items())),
        "exactReferences": exact_refs,
        "logicIdFieldPathCounts": field_counts.most_common(80),
        "logicIdValueCounts": value_counts.most_common(80),
    }


def scan_lua_consumers(lua_root: Path, *, limit: int = 200) -> list[dict[str, Any]]:
    if not lua_root.is_dir():
        return []
    hits: list[dict[str, Any]] = []
    for path in sorted(lua_root.rglob("*.lua")):
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            matched = [term for term in LUA_CONSUMER_TERMS if term in line]
            if not matched:
                continue
            hits.append({
                "path": rel_path(path),
                "line": line_no,
                "terms": matched,
                "text": line.strip()[:220],
            })
            if len(hits) >= limit:
                return hits
    return hits


def build_report(
    language: str,
    conv_dir: Path,
    timeline_orders_path: Path,
    reports_dir: Path,
    *,
    story_filters: list[str],
    group_filters: set[int],
    scan_lua: bool,
) -> dict[str, Any]:
    groups, logic_options = collect_logic_options(
        language,
        conv_dir,
        timeline_orders_path,
        story_filters=story_filters,
        group_filters=group_filters,
    )
    target_logic_ids = set(logic_options)
    json_scan = scan_json_sources(list(DEFAULT_SCAN_TARGETS), target_logic_ids)
    lua_hits = scan_lua_consumers(LUA_ROOT) if scan_lua else []
    dialog_lua_hits = [
        hit for hit in lua_hits
        if "/UI/Panels/Dialog/" in hit.get("path", "").replace("\\", "/")
    ]
    dialog_lua_logic_hits = [
        hit for hit in dialog_lua_hits
        if any(term.lower() == "logicid" for term in hit.get("terms") or [])
    ]
    refs_by_logic: dict[int, list[dict[str, Any]]] = defaultdict(list)
    refs_by_source = Counter()
    same_mission_refs: list[dict[str, Any]] = []
    for ref in json_scan["exactReferences"]:
        logic_id = int(ref["logicId"])
        refs_by_logic[logic_id].append(ref)
        refs_by_source[ref["sourceGroup"]] += 1
        source_mission = safe_key(ref.get("sourceMission"))
        if source_mission:
            for option in logic_options.get(logic_id, []):
                if safe_key(option.get("mission")) == source_mission:
                    same_mission_refs.append(ref | {
                        "optionStoryKey": option.get("storyKey"),
                        "optionId": option.get("optionId"),
                    })
                    break

    logic_id_summaries: list[dict[str, Any]] = []
    for logic_id, options in logic_options.items():
        refs = refs_by_logic.get(logic_id, [])
        option_stories = sorted({safe_key(option.get("storyKey")) for option in options if option.get("storyKey")})
        option_candidates = sorted({safe_key(option.get("candidateLineId")) for option in options if option.get("candidateLineId")})
        logic_id_summaries.append({
            "logicId": logic_id,
            "optionCount": len(options),
            "storyKeys": option_stories,
            "candidateLineIds": option_candidates,
            "externalReferenceCount": len(refs),
            "sourceGroups": dict(sorted(Counter(ref["sourceGroup"] for ref in refs).items())),
            "sampleReferences": refs[:8],
            "options": options[:12],
        })

    no_ref_logic_ids = [row["logicId"] for row in logic_id_summaries if not row["externalReferenceCount"]]
    weak_table_only = [
        row["logicId"]
        for row in logic_id_summaries
        if row["externalReferenceCount"]
        and set(row["sourceGroups"]) <= {"table", "gameplayConfigFile", "gameplayConfig"}
    ]
    strong_source_logic_ids = [
        row["logicId"]
        for row in logic_id_summaries
        if any(group in row["sourceGroups"] for group in ("missionRuntime", "levelScript", "levelScriptTemplate"))
    ]
    summary = {
        "language": language,
        "filters": {
            "stories": story_filters,
            "groups": sorted(group_filters),
        },
        "inferredLogicGroupCount": len(groups),
        "logicOptionCount": sum(len(options) for options in logic_options.values()),
        "uniqueLogicIdCount": len(logic_options),
        "jsonParsedFileCount": json_scan["parsedFileCount"],
        "jsonSkippedFileCount": json_scan["skippedFileCount"],
        "jsonFilesByGroup": json_scan["filesByGroup"],
        "exactExternalReferenceCount": len(json_scan["exactReferences"]),
        "exactExternalReferencesBySource": dict(sorted(refs_by_source.items())),
        "sameMissionExactReferenceCount": len(same_mission_refs),
        "strongSourceLogicIds": strong_source_logic_ids,
        "weakTableOnlyLogicIds": weak_table_only[:80],
        "logicIdsWithoutExternalReference": no_ref_logic_ids[:80],
        "luaConsumerHitCount": len(lua_hits),
        "luaConsumerFileCount": len({hit["path"] for hit in lua_hits}),
        "dialogLuaConsumerHitCount": len(dialog_lua_hits),
        "dialogLuaLogicIdHitCount": len(dialog_lua_logic_hits),
        "topLogicIdFieldPaths": json_scan["logicIdFieldPathCounts"][:30],
        "topLogicIdValues": json_scan["logicIdValueCounts"][:30],
    }
    payload = {
        "summary": summary,
        "logicIds": logic_id_summaries,
        "sameMissionExactReferences": same_mission_refs[:80],
        "exactExternalReferences": json_scan["exactReferences"][:500],
        "luaConsumerHits": lua_hits,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = safe_report_suffix(story_filters, group_filters, False)
    out_json = reports_dir / f"option_logic_id_audit_{language}{suffix}.json"
    out_md = reports_dir / f"option_logic_id_audit_{language}{suffix}.md"
    write_json(out_json, payload)
    out_md.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    return {"summary": summary, "json": out_json, "markdown": out_md}


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# Option LogicId Audit - {summary['language']}",
        "",
        f"- Logic-bearing inferred groups: `{summary['inferredLogicGroupCount']}`",
        f"- Logic-bearing option rows: `{summary['logicOptionCount']}`",
        f"- Unique nonzero `logicId`s: `{summary['uniqueLogicIdCount']}`",
        f"- JSON files parsed: `{summary['jsonParsedFileCount']}`",
        f"- Exact external references: `{summary['exactExternalReferenceCount']}`",
        f"- Same-mission exact references: `{summary['sameMissionExactReferenceCount']}`",
        f"- Lua consumer hits: `{summary['luaConsumerHitCount']}` in `{summary['luaConsumerFileCount']}` files",
        f"- Dialog Lua `logicId` hits: `{summary['dialogLuaLogicIdHitCount']}`",
        "",
        "## Reference Buckets",
        "",
        f"- External references by source: `{summary.get('exactExternalReferencesBySource', {})}`",
        f"- Strong source logicIds: `{summary.get('strongSourceLogicIds', [])}`",
        f"- Weak table/config-only logicIds: `{summary.get('weakTableOnlyLogicIds', [])}`",
        f"- No external reference logicIds: `{summary.get('logicIdsWithoutExternalReference', [])}`",
        "",
        "## Interpretation",
        "",
        "Same-mission `MissionRuntimeAsset`, `LevelScriptData`, or `LevelScriptTemplateData` matches would be the strongest evidence that a Timeline option `logicId` is meaningful for story recovery. Table/config-only matches are weaker because small `logicId` values can collide across unrelated world entities or map marks.",
        "",
        "Current Dialog Lua hits expose option UI fields such as `optionId` and `setGreyed`, but no dialog-panel `logicId` consumer. That supports treating Timeline option `logicId` as non-target evidence unless a stronger runtime consumer is found.",
        "",
        "## LogicId Rows",
        "",
        "| LogicId | Options | Stories | Candidate Lines | External Refs | Sources |",
        "| ---: | ---: | --- | --- | ---: | --- |",
    ]
    for row in payload.get("logicIds", []):
        sources = ", ".join(f"{key}:{value}" for key, value in (row.get("sourceGroups") or {}).items())
        lines.append(
            "| "
            f"{row.get('logicId')} "
            f"| {row.get('optionCount')} "
            f"| `{md_escape(', '.join(row.get('storyKeys') or []))}` "
            f"| `{md_escape(', '.join(row.get('candidateLineIds') or []))}` "
            f"| {row.get('externalReferenceCount')} "
            f"| `{md_escape(sources)}` |"
        )
    if not payload.get("logicIds"):
        lines.append("| _(none)_ |  |  |  |  |  |")

    lines.extend([
        "",
        "## Same-Mission References",
        "",
        "| LogicId | Option | Source | JSON Path | Context |",
        "| ---: | --- | --- | --- | --- |",
    ])
    for ref in payload.get("sameMissionExactReferences", []):
        lines.append(
            "| "
            f"{ref.get('logicId')} "
            f"| `{md_escape(ref.get('optionStoryKey'))}` / `{md_escape(ref.get('optionId'))}` "
            f"| `{md_escape(ref.get('path'))}` "
            f"| `{md_escape(ref.get('jsonPath'))}` "
            f"| `{md_escape(ref.get('context'))}` |"
        )
    if not payload.get("sameMissionExactReferences"):
        lines.append("| _(none)_ |  |  |  |  |")

    lines.extend([
        "",
        "## External Reference Samples",
        "",
        "| LogicId | Source | JSON Path | Context |",
        "| ---: | --- | --- | --- |",
    ])
    for ref in payload.get("exactExternalReferences", [])[:40]:
        lines.append(
            "| "
            f"{ref.get('logicId')} "
            f"| `{md_escape(ref.get('path'))}` "
            f"| `{md_escape(ref.get('jsonPath'))}` "
            f"| `{md_escape(ref.get('context'))}` |"
        )
    if not payload.get("exactExternalReferences"):
        lines.append("| _(none)_ |  |  |  |")

    lines.extend([
        "",
        "## Lua Consumer Hits",
        "",
        "| File | Line | Terms | Text |",
        "| --- | ---: | --- | --- |",
    ])
    for hit in payload.get("luaConsumerHits", [])[:80]:
        lines.append(
            "| "
            f"`{md_escape(hit.get('path'))}` "
            f"| {hit.get('line')} "
            f"| `{md_escape(', '.join(hit.get('terms') or []))}` "
            f"| `{md_escape(hit.get('text'))}` |"
        )
    if not payload.get("luaConsumerHits"):
        lines.append("| _(none)_ |  |  |  |")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--conv-dir", type=Path)
    parser.add_argument(
        "--timeline-orders",
        type=Path,
        default=EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "timeline_line_orders.json",
    )
    parser.add_argument("--reports-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--story", action="append", help="Story key, substring, glob, or comma-list to audit.")
    parser.add_argument("--group", action="append", help="Option group number or comma-list to audit.")
    parser.add_argument("--skip-lua", action="store_true", help="Skip Lua consumer term scan.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    language = args.language
    conv_dir = args.conv_dir or ROOT / "webui" / "data" / "lang" / language / "conv"
    story_filters = split_csv_values(args.story)
    try:
        group_filters = parse_group_filters(args.group)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    result = build_report(
        language,
        conv_dir,
        args.timeline_orders,
        args.reports_dir,
        story_filters=story_filters,
        group_filters=group_filters,
        scan_lua=not args.skip_lua,
    )
    summary = result["summary"]
    print(f"Option logicId audit: {result['markdown']}")
    print(f"Option logicId data:  {result['json']}")
    print(
        "Audited "
        f"{summary['logicOptionCount']} logic-bearing options across "
        f"{summary['inferredLogicGroupCount']} inferred groups; "
        f"{summary['sameMissionExactReferenceCount']} same-mission exact references."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
