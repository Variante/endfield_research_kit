#!/usr/bin/env python3
"""Audit selector MemoryPack formatter union tags from GameAssembly.

The BuffData FindTargetAction bodies contain nested SelectorData payloads. This
script keeps the binary evidence for selector Finder, Validator, and
PostProcessor formatter tables reproducible instead of relying on one-off
inline probes.

Output:

    reports/mission_order/selector_formatter_tag_audit.json
    reports/mission_order/selector_formatter_tag_audit.md
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402
import build_levelscript_actionbase_tag_audit as actionbase_audit  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
BODY_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAMEASSEMBLY = actionbase_audit.DEFAULT_GAMEASSEMBLY
DEFAULT_CODE_REGISTRATION = actionbase_audit.DEFAULT_CODE_REGISTRATION

SELECTOR_TARGETS = (
    {
        "id": "finder",
        "label": "Finder",
        "type": (
            "Beyond_Gameplay_Core_Selector_Finder_DataForMemoryPack+"
            "Beyond_Gameplay_Core_Selector_Finder_DataForMemoryPackFormatter"
        ),
    },
    {
        "id": "validator",
        "label": "Validator",
        "type": (
            "Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPack+"
            "Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPackFormatter"
        ),
    },
    {
        "id": "postProcessor",
        "label": "PostProcessor",
        "type": (
            "Beyond_Gameplay_Core_Selector_PostProcessor_DataForMemoryPack+"
            "Beyond_Gameplay_Core_Selector_PostProcessor_DataForMemoryPackFormatter"
        ),
    },
)

SLOT_TARGET_RE = re.compile(r"=> 0x([0-9a-f]+)\]", re.IGNORECASE)
CMP_EAX_RE = re.compile(r"cmp eax, 0x([0-9a-f]+)", re.IGNORECASE)


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_int(value: str | int) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def find_method(md: Any, *, type_name: str, method_name: str) -> tuple[Any, Any, str]:
    for type_def in md.types:
        if md.type_full_name(type_def) != type_name:
            continue
        for method in md.methods_for(type_def):
            if md.string(method.name_index) == method_name:
                return type_def, method, md.image_name_by_type_index.get(type_def.index, "")
    raise RuntimeError(f"method not found: {type_name}.{method_name}")


def method_pointer(
    *,
    method: Any,
    image_name: str,
    ranges: dict[str, dict[str, int]],
    pointers_by_image: dict[str, list[int]],
    target_name: str,
) -> tuple[int, int]:
    return actionbase_audit.method_pointer_for(
        method=method,
        image_name=image_name,
        ranges=ranges,
        pointers_by_image=pointers_by_image,
        target_name=target_name,
    )



def collect_selector_formatter_slots(
    *,
    pe: Any,
    md: Any,
    body_helper: Any,
    pointer: int,
    scan_size: int,
    table_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = pe.bytes_at_va(pointer, scan_size)
    instructions = body_helper.decode_x64_subset(data, pointer, stop_offset=len(data))
    rows_by_slot: dict[str, dict[str, Any]] = {}
    unknown_count = 0
    for instr in instructions:
        text = str(instr.get("text") or "")
        if text.startswith("db "):
            unknown_count += 1
        for match in SLOT_TARGET_RE.finditer(text):
            slot_va = int(match.group(1), 16)
            slot = actionbase_audit.metadata_slot_row(pe, md, slot_va)
            if not actionbase_audit.is_formatter_slot(slot):
                continue
            type_name = str(slot.get("typeName") or "")
            action_name = str(slot.get("actionName") or "")
            if "Core_Selector_" not in type_name:
                continue
            rows_by_slot[str(slot["slotVa"])] = {
                **slot,
                "tableFamily": table_id,
                "firstLoadOffset": f"0x{int(instr.get('offset') or 0):x}",
                "firstLoadInstruction": text,
            }
    rows = sorted(rows_by_slot.values(), key=lambda row: int(str(row.get("slotVa")), 16))
    return rows, {
        "instructionCount": len(instructions),
        "unknownInstructionCount": unknown_count,
        "decodedBytes": len(data),
    }


def deserialize_dispatch_summary(
    *,
    pe: Any,
    body_helper: Any,
    pointer: int,
    scan_size: int,
) -> dict[str, Any]:
    data = pe.bytes_at_va(pointer, scan_size)
    instructions = body_helper.decode_x64_subset(data, pointer, stop_offset=len(data))
    cmp_rows: list[dict[str, Any]] = []
    for instr in instructions:
        text = str(instr.get("text") or "")
        match = CMP_EAX_RE.search(text)
        if not match:
            continue
        value = int(match.group(1), 16)
        if value > 0x100:
            continue
        cmp_rows.append({
            "offset": f"0x{int(instr.get('offset') or 0):x}",
            "va": instr.get("va") or "",
            "instruction": text,
            "maxTagCandidate": value,
            "tagCountCandidate": value + 1,
        })
    best = max(cmp_rows, key=lambda row: int(row["maxTagCandidate"])) if cmp_rows else {}
    return {
        "scanBytes": len(data),
        "cmpEaxRows": cmp_rows,
        "bestCmp": best,
        "cmpEvidence": (
            f"largest observed cmp eax immediate 0x{int(best['maxTagCandidate']):x}"
            if best else ""
        ),
    }


def tag_summary(tag_rows: list[dict[str, Any]], diagnostics: dict[str, Any]) -> dict[str, Any]:
    tags = [int(row.get("tag") or 0) for row in tag_rows]
    return {
        "tagCount": len(tag_rows),
        "tagRange": f"0x{min(tags):04x}..0x{max(tags):04x}" if tags else "",
        "minTagHex": f"0x{min(tags):04x}" if tags else "",
        "maxTagHex": f"0x{max(tags):04x}" if tags else "",
        "duplicateTagCount": sum(1 for count in Counter(tags).values() if count > 1),
        **diagnostics,
    }


def build_target_row(
    *,
    target: dict[str, Any],
    pe: Any,
    md: Any,
    body_helper: Any,
    ranges: dict[str, dict[str, int]],
    pointers_by_image: dict[str, list[int]],
    sorted_all_pointers: list[int],
    max_scan_bytes: int,
) -> dict[str, Any]:
    type_name = str(target["type"])
    type_def, cctor, image_name = find_method(md, type_name=type_name, method_name=".cctor")
    cctor_pointer, cctor_slot = method_pointer(
        method=cctor,
        image_name=image_name,
        ranges=ranges,
        pointers_by_image=pointers_by_image,
        target_name=f"{type_name}..cctor",
    )
    cctor_scan_size, cctor_next = body_helper.estimate_scan_size(
        cctor_pointer,
        sorted_all_pointers,
        max_scan_bytes,
    )
    tag_rows, tag_diagnostics = actionbase_audit.extract_formatter_tags(
        pe=pe,
        md=md,
        body_helper=body_helper,
        pointer=cctor_pointer,
        scan_size=cctor_scan_size,
    )
    slot_rows, slot_diagnostics = collect_selector_formatter_slots(
        pe=pe,
        md=md,
        body_helper=body_helper,
        pointer=cctor_pointer,
        scan_size=cctor_scan_size,
        table_id=str(target.get("id") or ""),
    )

    _deserialize_type, deserialize, deserialize_image = find_method(
        md,
        type_name=type_name,
        method_name="Deserialize",
    )
    deserialize_pointer, deserialize_slot = method_pointer(
        method=deserialize,
        image_name=deserialize_image,
        ranges=ranges,
        pointers_by_image=pointers_by_image,
        target_name=f"{type_name}.Deserialize",
    )
    dispatch = deserialize_dispatch_summary(
        pe=pe,
        body_helper=body_helper,
        pointer=deserialize_pointer,
        scan_size=min(max_scan_bytes, 0x1000),
    )
    return {
        "id": target.get("id"),
        "label": target.get("label"),
        "type": type_name,
        "image": image_name,
        "typeIndex": type_def.index,
        "typeToken": f"0x{type_def.token:08x}",
        "cctor": {
            "methodIndex": cctor.index,
            "methodToken": f"0x{cctor.token:08x}",
            "moduleMethodSlot": cctor_slot,
            "methodPointerVa": f"0x{cctor_pointer:x}",
            "scanBytes": cctor_scan_size,
            "nextMethodPointerVa": f"0x{cctor_next:x}" if cctor_next else "",
        },
        "deserialize": {
            "methodIndex": deserialize.index,
            "methodToken": f"0x{deserialize.token:08x}",
            "moduleMethodSlot": deserialize_slot,
            "methodPointerVa": f"0x{deserialize_pointer:x}",
            **dispatch,
        },
        "summary": {
            "registrationPattern": "actionbase-style-r8-tag" if tag_rows else "not-recovered",
            "tagConfidence": "high" if tag_rows else "range-only",
            "selectorFormatterSlotCount": len(slot_rows),
            **tag_summary(tag_rows, tag_diagnostics),
        },
        "formatterTags": tag_rows,
        "selectorFormatterSlots": slot_rows,
        "slotDiagnostics": slot_diagnostics,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog_helper = load_module(CATALOG_HELPER, "selector_tag_catalog")
    body_helper = load_module(BODY_HELPER, "selector_tag_body")
    metadata_path = catalog_helper.resolve_metadata_path(args.metadata, prefer_cache=True)
    md = catalog_helper.Metadata(metadata_path)
    pe = body_helper.PeImage(args.gameassembly)
    code_reg = parse_int(args.code_registration)
    modules = body_helper.parse_codegen_modules(pe, code_reg)
    ranges = body_helper.image_method_ranges(md)
    pointers_by_image, _method_by_pointer = body_helper.build_pointer_indexes(pe, md, modules, ranges)
    sorted_all_pointers = sorted(
        {
            pointer
            for pointers in pointers_by_image.values()
            for pointer in pointers
            if pointer
        }
    )
    tables = [
        build_target_row(
            target=target,
            pe=pe,
            md=md,
            body_helper=body_helper,
            ranges=ranges,
            pointers_by_image=pointers_by_image,
            sorted_all_pointers=sorted_all_pointers,
            max_scan_bytes=args.max_scan_bytes,
        )
        for target in SELECTOR_TARGETS
    ]
    finder = next((table for table in tables if table.get("id") == "finder"), {})
    validator = next((table for table in tables if table.get("id") == "validator"), {})
    post = next((table for table in tables if table.get("id") == "postProcessor"), {})
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metadata": {
            "metadataPath": str(metadata_path),
            "gameAssembly": str(args.gameassembly),
            "imageBase": f"0x{pe.image_base:x}",
            "codeRegistration": f"0x{code_reg:x}",
        },
        "settings": {
            "maxScanBytes": args.max_scan_bytes,
        },
        "summary": {
            "selectorTableCount": len(tables),
            "finderTagCount": (finder.get("summary") or {}).get("tagCount", 0),
            "finderRange": (finder.get("summary") or {}).get("tagRange", ""),
            "validatorTagCount": (validator.get("summary") or {}).get("tagCount", 0),
            "validatorRange": (validator.get("summary") or {}).get("tagRange", ""),
            "postProcessorTagCount": (post.get("summary") or {}).get("tagCount", 0),
            "postProcessorRange": (post.get("summary") or {}).get("tagRange", ""),
        },
        "selectorTables": tables,
        "interpretation": [
            "Finder, Validator, and PostProcessor cctors use ActionBase-style registration blocks with explicit r8 tag constants, so their tag-to-formatter tables are promotable binary evidence.",
            "Deserialize cmp rows are kept as secondary diagnostics only; the cctor registration tables are the tag source of truth.",
            "FindTargetAction chain consumption still needs a self-delimiting SelectorData parser before these selector facts can be used in the WebUI index builder.",
        ],
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    meta = payload.get("metadata") or {}
    summary = payload.get("summary") or {}
    lines = [
        "# Selector Formatter Tag Audit",
        "",
        "## Summary",
        "",
        f"- Global metadata: `{md_escape(meta.get('metadataPath', ''))}`",
        f"- GameAssembly: `{md_escape(meta.get('gameAssembly', ''))}`",
        f"- CodeRegistration: `{md_escape(meta.get('codeRegistration', ''))}`",
        f"- Finder tags: `{summary.get('finderTagCount')}` (`{summary.get('finderRange')}`)",
        f"- Validator tags: `{summary.get('validatorTagCount')}` (`{summary.get('validatorRange')}`)",
        f"- PostProcessor tags: `{summary.get('postProcessorTagCount')}` (`{summary.get('postProcessorRange')}`)",
        "",
        "## Interpretation",
        "",
    ]
    for item in payload.get("interpretation") or []:
        lines.append(f"- {md_escape(item)}")
    lines.extend([
        "",
        "## Recovered Tags",
        "",
        "| table | tag | selector formatter | metadata slot | evidence |",
        "| --- | ---: | --- | --- | --- |",
    ])
    for table in payload.get("selectorTables") or []:
        for row in table.get("formatterTags") or []:
            evidence = row.get("evidence") or {}
            slot = row.get("metadataSlot") or {}
            lines.append(
                f"| {md_escape(table.get('label', ''))} "
                f"| `{row.get('tagHex')}` "
                f"| `{md_escape(row.get('actionName', ''))}` "
                f"| `{slot.get('slotVa', '')}` "
                f"| `{md_escape(evidence.get('tagInstruction', ''))}` at `{evidence.get('tagOffset', '')}` |"
            )
    lines.extend([
        "",
        "## Selector Tables",
        "",
        "| table | cctor VA | deserialize VA | recovered tags | selector formatter slots | deserialize diagnostic |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ])
    for table in payload.get("selectorTables") or []:
        summ = table.get("summary") or {}
        deser = table.get("deserialize") or {}
        lines.append(
            f"| {md_escape(table.get('label', ''))} "
            f"| `{(table.get('cctor') or {}).get('methodPointerVa', '')}` "
            f"| `{deser.get('methodPointerVa', '')}` "
            f"| `{summ.get('tagCount', 0)}` "
            f"| `{summ.get('selectorFormatterSlotCount', 0)}` "
            f"| `{md_escape(deser.get('cmpEvidence', ''))}` |"
        )
    lines.extend([
        "",
        "## Selector Formatter Slot Inventory",
        "",
        "These slots are decoded formatter type handles from the cctors. They should match the recovered tag rows for tables that use the explicit registration pattern.",
        "",
        "| table | formatter | slot | first load |",
        "| --- | --- | --- | --- |",
    ])
    for table in payload.get("selectorTables") or []:
        for row in table.get("selectorFormatterSlots") or []:
            lines.append(
                f"| {md_escape(table.get('label', ''))} "
                f"| `{md_escape(row.get('actionName', ''))}` "
                f"| `{row.get('slotVa', '')}` "
                f"| `{row.get('firstLoadOffset', '')}` |"
            )
    write_text_if_changed(path, "\n".join(lines).rstrip() + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--code-registration", default=DEFAULT_CODE_REGISTRATION)
    parser.add_argument("--max-scan-bytes", type=int, default=0x3000)
    parser.add_argument("--json", type=Path, default=REPORT_DIR / "selector_formatter_tag_audit.json")
    parser.add_argument("--markdown", type=Path, default=REPORT_DIR / "selector_formatter_tag_audit.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_report(args)
    write_report_json(args.json, payload)
    write_markdown(args.markdown, payload)
    summary = payload["summary"]
    print(f"Selector formatter tag audit: {args.json}")
    print(f"Selector formatter tag report: {args.markdown}")
    print(
        "postProcessorTags="
        f"{summary.get('postProcessorTagCount')} "
        f"finderTags={summary.get('finderTagCount')} "
        f"validatorTags={summary.get('validatorTagCount')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
