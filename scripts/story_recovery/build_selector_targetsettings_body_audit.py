#!/usr/bin/env python3
"""Write a focused GameAssembly body audit for selector target settings.

FindTargetAction payload recovery depends on nested TargetSettings and
SelectorData MemoryPack records. This wrapper keeps the IL2CPP metadata and
GameAssembly body evidence reproducible without relying on a hand-filtered
catalog JSON.

Output:

    reports/mission_order/selector_targetsettings_body_targets_gameassembly.json
    reports/mission_order/selector_targetsettings_body_targets_gameassembly.md
    reports/mission_order/selector_targetsettings_chain_summary.json
    reports/mission_order/selector_targetsettings_chain_summary.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
BODY_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_CATALOG_TMP = ROOT / "tmp" / "selector_targetsettings_body_catalog.json"
DEFAULT_RAW_JSON = REPORT_DIR / "selector_targetsettings_body_targets_gameassembly.json"
DEFAULT_RAW_MD = REPORT_DIR / "selector_targetsettings_body_targets_gameassembly.md"
DEFAULT_SUMMARY_JSON = REPORT_DIR / "selector_targetsettings_chain_summary.json"
DEFAULT_SUMMARY_MD = REPORT_DIR / "selector_targetsettings_chain_summary.md"
TAG_AUDIT_JSON = REPORT_DIR / "selector_formatter_tag_audit.json"

TYPE_RE = r"(FindTargetAction|TargetSettings|Selector).*ForMemoryPack"
MEMBER_RE = (
    r"(Deserialize|set____|set___|finderData|validatorData|postProcessorData|"
    r"selectorData|targetSettings|targetGroupKey|contextKey|target|direction|"
    r"owner|center)"
)
BODY_TARGET_RE = r"^(Deserialize|set____.*|set___.*)$"
BODY_TARGET_TYPE_RE = (
    r"(^|_)(FindTargetAction|Selector)(_|\\+|$)|TargetSettingsForMemoryPack|"
    r"ContinuousFindTargetAction|EffectFindTargetAction"
)
IMAGE_RE = r"MemoryPack\.Beyond\.dll"
BODY_SUMMARY_RE = r"Deserialize|set____|set___"
FIELD_STORE_RE = re.compile(r"mov[a-z]* \[(?P<base>[a-z0-9]+)\+0x(?P<offset>[0-9a-f]+)\],", re.IGNORECASE)

INTERESTING_DESERIALIZE_TYPES = (
    "Beyond_Gameplay_Core_ContinuousFindTargetAction_DataForMemoryPack",
    "Beyond_Gameplay_Core_EffectFindTargetAction_DataForMemoryPack",
    "Beyond_Gameplay_Core_FindTargetAction_FindTargetActionDataForMemoryPack",
    "Beyond_Gameplay_Core_Selector_SelectorDataForMemoryPack",
    "Beyond_Gameplay_Core_TargetSettingsForMemoryPack",
)
INTERESTING_SETTER_TYPE_TERMS = (
    "ContinuousFindTargetAction",
    "EffectFindTargetAction",
    "FindTargetAction_FindTargetActionDataForMemoryPack",
    "Selector_SelectorDataForMemoryPack",
    "TargetSettingsForMemoryPack",
)


def load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def build_trimmed_catalog(
    catalog_helper: Any,
    metadata: Any,
    *,
    body_context: int,
) -> dict[str, Any]:
    catalog = catalog_helper.build_catalog(
        metadata,
        re.compile(TYPE_RE, re.IGNORECASE),
        re.compile(MEMBER_RE, re.IGNORECASE),
        re.compile(BODY_TARGET_RE, re.IGNORECASE),
        re.compile(BODY_TARGET_TYPE_RE, re.IGNORECASE),
        re.compile(IMAGE_RE, re.IGNORECASE),
        only_focus=False,
        include_all_members=True,
        body_context=body_context,
    )
    body_targets = catalog.get("bodyTargets") or []
    body_target_types = sorted({str(row.get("type") or "") for row in body_targets})
    return {
        "metadata": catalog.get("metadata") or {},
        "settings": catalog.get("settings") or {},
        "summary": {
            **(catalog.get("summary") or {}),
            "bodyTargetTypeCount": len(body_target_types),
        },
        "bodyTargetTypes": body_target_types,
        "bodyTargets": body_targets,
    }


def compact_resolved(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "methodIndex": row.get("methodIndex"),
        "type": row.get("type"),
        "method": row.get("method"),
    }


def setter_candidates(call: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for resolved in call.get("resolved") or []:
        method = str(resolved.get("method") or "")
        type_name = str(resolved.get("type") or "")
        if not method.startswith(("set___", "set____")):
            continue
        if not any(term in type_name for term in INTERESTING_SETTER_TYPE_TERMS):
            continue
        rows.append(compact_resolved(resolved))
    return rows


def extract_setter_sequences(mapped_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sequences = []
    for row in mapped_targets:
        if row.get("method") != "Deserialize":
            continue
        if row.get("type") not in INTERESTING_DESERIALIZE_TYPES:
            continue
        calls = []
        for call in row.get("directCalls") or []:
            candidates = setter_candidates(call)
            if not candidates:
                continue
            calls.append(
                {
                    "offset": call.get("offset"),
                    "targetVa": call.get("targetVa"),
                    "candidates": candidates,
                }
            )
        sequences.append(
            {
                "type": row.get("type"),
                "method": row.get("method"),
                "methodIndex": row.get("methodIndex"),
                "methodPointerVa": row.get("methodPointerVa"),
                "setterCallCount": len(calls),
                "setterCalls": calls,
            }
        )
    return sequences


def candidate_labels(call: dict[str, Any]) -> list[str]:
    labels = []
    for candidate in call.get("candidates") or []:
        type_name = str(candidate.get("type") or "").split(".")[-1]
        labels.append(f"{type_name}.{candidate.get('method')}")
    return labels


def sequence_methods(sequence: dict[str, Any], *, type_term: str) -> list[str]:
    methods = []
    for call in sequence.get("setterCalls") or []:
        for candidate in call.get("candidates") or []:
            if type_term not in str(candidate.get("type") or ""):
                continue
            method = str(candidate.get("method") or "")
            if method and method not in methods:
                methods.append(method)
    return methods


def setter_field_name(method: str) -> str:
    if method in {"set___instance", "set____instance"}:
        return ""
    for prefix in ("set___", "set____"):
        if method.startswith(prefix) and method.endswith("__"):
            return method[len(prefix):-2]
    return ""


def extract_store(summary: dict[str, Any]) -> dict[str, Any]:
    for item in (summary.get("paramFlow") or {}).get("param:value") or []:
        text = str(item.get("text") or "")
        match = FIELD_STORE_RE.search(text)
        if match:
            offset = int(match.group("offset"), 16)
            return {
                "offset": f"0x{offset:x}",
                "base": match.group("base"),
                "instruction": text,
                "instructionOffset": item.get("offset"),
                "source": "paramFlow.param:value",
            }
    for access in summary.get("fieldAccesses") or []:
        if access.get("kind") != "write":
            continue
        text = str(access.get("text") or "")
        match = FIELD_STORE_RE.search(text)
        if match:
            offset = int(match.group("offset"), 16)
            return {
                "offset": f"0x{offset:x}",
                "base": match.group("base"),
                "instruction": text,
                "instructionOffset": access.get("offset"),
                "source": "fieldAccesses",
            }
    return {}


def extract_setter_store_offsets(mapped_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in mapped_targets:
        type_name = str(row.get("type") or "")
        method = str(row.get("method") or "")
        if not method.startswith("set_"):
            continue
        if not any(term in type_name for term in INTERESTING_SETTER_TYPE_TERMS):
            continue
        field = setter_field_name(method)
        if not field:
            continue
        store = extract_store(row.get("methodBodySummary") or {})
        rows.append(
            {
                "type": type_name,
                "method": method,
                "field": field,
                "methodIndex": row.get("methodIndex"),
                "methodPointerVa": row.get("methodPointerVa"),
                "store": store,
            }
        )
    return sorted(rows, key=lambda row: (str(row["type"]), str(row["field"])))


def extract_call_alias_warnings(sequences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = []
    for sequence in sequences:
        for call in sequence.get("setterCalls") or []:
            candidates = call.get("candidates") or []
            if len(candidates) < 2:
                continue
            aliases.append(
                {
                    "callerType": sequence.get("type"),
                    "callerMethod": sequence.get("method"),
                    "offset": call.get("offset"),
                    "targetVa": call.get("targetVa"),
                    "candidates": candidates,
                }
            )
    return aliases


def load_selector_tag_maps() -> dict[str, Any]:
    if not TAG_AUDIT_JSON.is_file():
        return {
            "source": repo_rel(TAG_AUDIT_JSON),
            "available": False,
            "summary": {},
            "tables": [],
        }
    payload = json.loads(TAG_AUDIT_JSON.read_text(encoding="utf-8"))
    tables = []
    for table in payload.get("selectorTables") or []:
        tables.append(
            {
                "id": table.get("id"),
                "label": table.get("label"),
                "type": table.get("type"),
                "summary": table.get("summary") or {},
                "tags": [
                    {
                        "tagHex": row.get("tagHex"),
                        "actionName": row.get("actionName"),
                        "formatterName": row.get("formatterName"),
                    }
                    for row in table.get("formatterTags") or []
                ],
            }
        )
    return {
        "source": repo_rel(TAG_AUDIT_JSON),
        "available": True,
        "summary": payload.get("summary") or {},
        "tables": tables,
    }


def selected_target_summaries(mapped_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = []
    for row in mapped_targets:
        if row.get("method") != "Deserialize":
            continue
        if row.get("type") not in INTERESTING_DESERIALIZE_TYPES:
            continue
        summary = row.get("methodBodySummary") or {}
        selected.append(
            {
                "type": row.get("type"),
                "method": row.get("method"),
                "methodIndex": row.get("methodIndex"),
                "mappingStatus": row.get("mappingStatus"),
                "methodPointerVa": row.get("methodPointerVa"),
                "scanBytes": row.get("scanBytes"),
                "directCallCount": len(row.get("directCalls") or []),
                "unresolvedDirectCallCount": row.get("unresolvedDirectCallCount"),
                "instructionCount": summary.get("instructionCount"),
                "unknownInstructionCount": summary.get("unknownInstructionCount"),
            }
        )
    return selected


def build_key_findings(
    report: dict[str, Any],
    catalog: dict[str, Any],
    sequences: list[dict[str, Any]],
) -> list[str]:
    summary = report.get("summary") or {}
    findings = [
        (
            f"Mapped {summary.get('mappedTargetCount')} of "
            f"{summary.get('catalogBodyTargetCount')} focused selector body targets "
            f"from {catalog.get('summary', {}).get('bodyTargetTypeCount')} MemoryPack types."
        ),
        (
            f"Resolved {summary.get('resolvedDirectCallCount')} direct calls, including "
            f"{summary.get('catalogTargetDirectCallCount')} calls back into focused catalog targets."
        ),
    ]

    by_type = {row.get("type"): row for row in sequences}
    continuous = by_type.get("Beyond_Gameplay_Core_ContinuousFindTargetAction_DataForMemoryPack")
    if continuous:
        methods = sequence_methods(continuous, type_term="FindTargetAction_FindTargetActionDataForMemoryPack")
        findings.append(
            "ContinuousFindTargetAction.Deserialize calls FindTargetAction setters in body order: "
            + ", ".join(methods)
            + "."
        )
    effect = by_type.get("Beyond_Gameplay_Core_EffectFindTargetAction_DataForMemoryPack")
    if effect:
        methods = sequence_methods(effect, type_term="FindTargetAction_FindTargetActionDataForMemoryPack")
        findings.append(
            "EffectFindTargetAction.Deserialize reaches the broader FindTargetAction setter set, "
            "including: "
            + ", ".join(methods[:16])
            + ("." if len(methods) <= 16 else ", ...")
        )
    selector = by_type.get("Beyond_Gameplay_Core_Selector_SelectorDataForMemoryPack")
    if selector:
        selector_methods = sequence_methods(selector, type_term="Selector_SelectorDataForMemoryPack")
        target_settings_methods = sequence_methods(selector, type_term="TargetSettingsForMemoryPack")
        findings.append(
            "SelectorData.Deserialize resolves nested selector setter calls: "
            + ", ".join(selector_methods)
            + "."
        )
        if target_settings_methods:
            findings.append(
                "The same SelectorData body also resolves TargetSettingsForMemoryPack calls: "
                + ", ".join(target_settings_methods)
                + "."
            )
    target_settings = by_type.get("Beyond_Gameplay_Core_TargetSettingsForMemoryPack")
    if target_settings:
        methods = sequence_methods(target_settings, type_term="TargetSettingsForMemoryPack")
        findings.append(
            "TargetSettingsForMemoryPack.Deserialize resolves its own setter calls in body order: "
            + ", ".join(methods)
            + "."
        )
    findings.append(
        "This is body-wiring evidence, not a safe payload-boundary proof. "
        "FindTargetAction chain consumption still needs sample-byte validation for nested "
        "SelectorData/TargetSettings reader lengths before it should be enabled."
    )
    return findings


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    lines = [
        "# Selector TargetSettings GameAssembly Body Audit",
        "",
        "## Summary",
        "",
        f"- Metadata: `{md_escape(payload['metadata'].get('metadataPath', ''))}`",
        f"- GameAssembly: `{md_escape(payload['metadata'].get('gameAssembly', ''))}`",
        f"- Catalog body targets: `{summary.get('catalogBodyTargetCount')}`",
        f"- Mapped body targets: `{summary.get('mappedTargetCount')}`",
        f"- Focused MemoryPack types: `{summary.get('bodyTargetTypeCount')}`",
        f"- Resolved direct calls: `{summary.get('resolvedDirectCallCount')}`",
        f"- Direct calls to focused targets: `{summary.get('catalogTargetDirectCallCount')}`",
        "",
        "## Interpretation",
        "",
    ]
    for finding in payload.get("keyFindings") or []:
        lines.append(f"- {md_escape(finding)}")

    lines.extend(["", "## Setter Call Sequences", ""])
    for sequence in payload.get("setterSequences") or []:
        title = f"{sequence.get('type')}.{sequence.get('method')}"
        lines.extend(
            [
                f"### `{md_escape(title)}`",
                "",
                f"- methodIndex: `{sequence.get('methodIndex')}`; VA: `{md_escape(sequence.get('methodPointerVa', ''))}`",
                f"- setter calls: `{sequence.get('setterCallCount')}`",
            ]
        )
        for call in (sequence.get("setterCalls") or [])[:32]:
            labels = "; ".join(candidate_labels(call))
            lines.append(
                f"- +0x{int(call.get('offset') or 0):x} -> `{md_escape(labels)}`"
            )
        if len(sequence.get("setterCalls") or []) > 32:
            lines.append(f"- ... and {len(sequence.get('setterCalls') or []) - 32} more")
        lines.append("")

    lines.extend(["## Setter Store Offsets", ""])
    offsets = payload.get("setterStoreOffsets") or []
    if not offsets:
        lines.append("- None extracted.")
    for row in offsets:
        store = row.get("store") or {}
        lines.append(
            f"- `{md_escape(row.get('type', ''))}.{md_escape(row.get('method', ''))}` "
            f"field=`{md_escape(row.get('field', ''))}` "
            f"store=`{md_escape(store.get('offset', '') or '?')}` "
            f"instr=`{md_escape(store.get('instruction', '') or '-')}`"
        )

    lines.extend(["", "## Call Alias Warnings", ""])
    aliases = payload.get("callAliasWarnings") or []
    if not aliases:
        lines.append("- None.")
    for alias in aliases:
        labels = "; ".join(
            f"{candidate.get('type', '').split('.')[-1]}.{candidate.get('method')}"
            for candidate in alias.get("candidates") or []
        )
        lines.append(
            f"- `{md_escape(alias.get('callerType', ''))}.{md_escape(alias.get('callerMethod', ''))}` "
            f"+0x{int(alias.get('offset') or 0):x} -> `{md_escape(labels)}`"
        )

    tag_maps = payload.get("selectorTagMaps") or {}
    lines.extend(["", "## Selector Tag Maps", ""])
    if not tag_maps.get("available"):
        lines.append(f"- Not available at `{md_escape(tag_maps.get('source', ''))}`.")
    else:
        tag_summary = tag_maps.get("summary") or {}
        lines.append(
            "- Source: "
            f"`{md_escape(tag_maps.get('source', ''))}`; "
            f"finder `{tag_summary.get('finderRange')}`, "
            f"validator `{tag_summary.get('validatorRange')}`, "
            f"postProcessor `{tag_summary.get('postProcessorRange')}`."
        )
        for table in tag_maps.get("tables") or []:
            table_summary = table.get("summary") or {}
            lines.append(
                f"- {md_escape(table.get('label', ''))}: "
                f"{table_summary.get('tagCount')} tags `{table_summary.get('tagRange')}`"
            )

    lines.extend(["", "## Selected Targets", ""])
    for row in payload.get("selectedTargets") or []:
        title = f"{row.get('type')}.{row.get('method')}"
        lines.append(
            f"- `{md_escape(title)}` methodIndex=`{row.get('methodIndex')}` "
            f"mapping=`{md_escape(row.get('mappingStatus', ''))}` "
            f"VA=`{md_escape(row.get('methodPointerVa', ''))}` "
            f"calls=`{row.get('directCallCount')}` unresolved=`{row.get('unresolvedDirectCallCount')}` "
            f"decode=`{row.get('instructionCount')}` instructions/{row.get('unknownInstructionCount')} unknown"
        )

    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            f"- Trimmed catalog: `{md_escape(payload['settings'].get('catalogTmp', ''))}`",
            f"- Raw body JSON: `{md_escape(payload['settings'].get('rawReportJson', ''))}`",
            f"- Raw body Markdown: `{md_escape(payload['settings'].get('rawReportMarkdown', ''))}`",
            "- Source helpers: "
            f"`{md_escape(repo_rel(CATALOG_HELPER))}`, `{md_escape(repo_rel(BODY_HELPER))}`",
        ]
    )
    write_text_if_changed(path, "\n".join(lines).rstrip() + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--catalog-tmp", type=Path, default=DEFAULT_CATALOG_TMP)
    parser.add_argument("--raw-json", type=Path, default=DEFAULT_RAW_JSON)
    parser.add_argument("--raw-markdown", type=Path, default=DEFAULT_RAW_MD)
    parser.add_argument("--json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_SUMMARY_MD)
    parser.add_argument("--body-context", type=int, default=8)
    parser.add_argument("--max-scan-bytes", type=int, default=0x8000)
    parser.add_argument("--body-summary-max-instructions", type=int, default=240)
    parser.add_argument(
        "--skip-unresolved-calls",
        dest="include_unresolved_calls",
        action="store_false",
        help="Omit unresolved direct-call rows from the mapped body report.",
    )
    parser.set_defaults(include_unresolved_calls=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog_helper = load_module(CATALOG_HELPER, "endfield_il2cpp_catalog")
    body_helper = load_module(BODY_HELPER, "endfield_il2cpp_body_map")
    metadata_path = catalog_helper.resolve_metadata_path(args.metadata, prefer_cache=True)
    metadata = catalog_helper.Metadata(metadata_path)
    catalog = build_trimmed_catalog(
        catalog_helper,
        metadata,
        body_context=max(0, args.body_context),
    )
    args.catalog_tmp.parent.mkdir(parents=True, exist_ok=True)
    args.catalog_tmp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    map_args = SimpleNamespace(
        metadata=metadata_path,
        gameassembly=args.gameassembly,
        catalog=args.catalog_tmp,
        code_registration=hex(body_helper.DEFAULT_CODE_REGISTRATION),
        head_bytes=32,
        max_scan_bytes=args.max_scan_bytes,
        include_unresolved_calls=args.include_unresolved_calls,
        arg_context_window=96,
        body_summary_method_regex=BODY_SUMMARY_RE,
        body_summary_max_instructions=args.body_summary_max_instructions,
    )
    raw_report = body_helper.build_report(map_args)
    args.raw_json.parent.mkdir(parents=True, exist_ok=True)
    args.raw_json.write_text(json.dumps(raw_report, ensure_ascii=False, indent=2), encoding="utf-8")
    body_helper.write_markdown(args.raw_markdown, raw_report)

    mapped_targets = raw_report.get("bodyTargets") or []
    sequences = extract_setter_sequences(mapped_targets)
    store_offsets = extract_setter_store_offsets(mapped_targets)
    alias_warnings = extract_call_alias_warnings(sequences)
    tag_maps = load_selector_tag_maps()
    summary = {
        **(raw_report.get("summary") or {}),
        "bodyTargetTypeCount": catalog.get("summary", {}).get("bodyTargetTypeCount"),
        "setterStoreOffsetCount": len(store_offsets),
        "callAliasWarningCount": len(alias_warnings),
    }
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "metadata": raw_report.get("metadata") or {},
        "settings": {
            **(raw_report.get("settings") or {}),
            "catalogTmp": repo_rel(args.catalog_tmp),
            "rawReportJson": repo_rel(args.raw_json),
            "rawReportMarkdown": repo_rel(args.raw_markdown),
            "catalogSettings": catalog.get("settings") or {},
        },
        "summary": summary,
        "keyFindings": build_key_findings(raw_report, catalog, sequences),
        "setterSequences": sequences,
        "setterStoreOffsets": store_offsets,
        "callAliasWarnings": alias_warnings,
        "selectorTagMaps": tag_maps,
        "selectedTargets": selected_target_summaries(mapped_targets),
        "directCallEdges": raw_report.get("directCallEdges") or [],
    }
    write_report_json(args.json, payload)
    write_markdown(args.markdown, payload)
    print(f"Selector TargetSettings chain summary: {args.json}")
    print(f"Selector TargetSettings chain report: {args.markdown}")
    print(f"Raw body JSON: {args.raw_json}")
    print(f"Raw body Markdown: {args.raw_markdown}")
    print(
        "mapped="
        f"{summary.get('mappedTargetCount')}/{summary.get('catalogBodyTargetCount')} "
        f"directTargetCalls={summary.get('catalogTargetDirectCallCount')} "
        f"sequences={len(sequences)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
