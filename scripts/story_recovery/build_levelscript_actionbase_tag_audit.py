#!/usr/bin/env python3
"""Recover the ActionBase MemoryPack union tag table from GameAssembly.

The raw LevelScriptData action records carry a numeric `code` plus a payload
`kind`. For normal action-map records, `code` matches the MemoryPack union tag
registered by
`Beyond_Gameplay_Actions_ActionBaseForMemoryPack+...Formatter..cctor`.

This script extracts that generated tag table directly from GameAssembly.dll,
decodes the runtime-metadata type slots back through global-metadata.dat, and
cross-references the global LevelScript opcode-shape audit when available.

Output:

    reports/mission_order/levelscript_actionbase_formatter_tags.json
    reports/mission_order/levelscript_actionbase_formatter_tags.md
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_NAME_CONTRACT = REPORT_DIR / "levelscript_actionbase_formatter_names.json"
CATALOG_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
BODY_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_CODE_REGISTRATION = "0x18b9217d0"
ACTIONBASE_FORMATTER_TYPE = (
    "Beyond_Gameplay_Actions_ActionBaseForMemoryPack+"
    "Beyond_Gameplay_Actions_ActionBaseForMemoryPackFormatter"
)
ACTIONBASE_FORMATTER_METHOD = ".cctor"
FINALACTIONBASE_FORMATTER_TYPE = (
    "Beyond_Gameplay_FinalActionBaseForMemoryPack+"
    "Beyond_Gameplay_FinalActionBaseForMemoryPackFormatter"
)

FORMATTER_TARGETS = (
    {
        "id": "actionBase",
        "label": "ActionBase",
        "type": ACTIONBASE_FORMATTER_TYPE,
        "method": ACTIONBASE_FORMATTER_METHOD,
        "primary": True,
    },
    {
        "id": "finalActionBase",
        "label": "FinalActionBase",
        "type": FINALACTIONBASE_FORMATTER_TYPE,
        "method": ACTIONBASE_FORMATTER_METHOD,
        "primary": False,
    },
)
SLOT_TARGET_RE = re.compile(r"=> 0x([0-9a-f]+)\]", re.IGNORECASE)
OPCODE_RE = re.compile(r"^0x([0-9a-f]+)/0x([0-9a-f]+)$", re.IGNORECASE)

SELECTED_OPCODE_KEYS = (
    "0x034a/0x14",  # Play3DRadio
    "0x034b/0x14",  # Play3DRadioAndWait
    "0x0357/0x14",  # PlayCutsceneAction
    "0x0358/0x14",  # PlayCutsceneIgnoreCinematicQueue
    "0x035a/0x0f",  # PlayDialogAndHideSceneObjectAction
    "0x0360/0x0f",  # PlayLevelSequenceAction
    "0x0361/0x12",  # PlayLevelSequenceAndControlSceneObjectsAction
    "0x0363/0x0d",  # PlayRadio
    "0x0364/0x0d",  # PlayRadioAndWait
    "0x049b/0x13",  # StartCutsceneAndControlSceneObjectAction
    "0x049c/0x12",  # StartCutsceneAndHideSceneObjectAction
    "0x049d/0x16",  # StartCutsceneAndTeleportAction
    "0x049e/0x0f",  # StartDialogAction
    "0x049f/0x10",  # StartDialogAndTeleportAction
    "0x0455/0x0a",  # SetOverrideInteractDialog
    "0x045d/0x0a",  # SetScriptTaskPtr
    "0x04bd/0x09",  # SwitchInt
    "0x04be/0x0c",  # SwitchIntLarger
    "0x0308/0x0a",  # ManualStartLevelScript
    "0x0302/0x0a",  # ManualEndLevelScript
    "0x03da/0x0a",  # SetBool
    "0x0410/0x0a",  # SetInt
    "0x0413/0x0a",  # SetIntIncrease
    "0x0a03/0x00",  # high property gate family, absent from ActionBase
    "0x0bed/0x00",  # high terminal family, absent from ActionBase
    "0x12be/0x00",  # current leader-enter header, absent from ActionBase
    "0x12c0/0x00",  # current leader-leave header, absent from ActionBase
    "0x1355/0x00",  # current dialog-exit header, absent from ActionBase
    "0x1385/0x00",  # current quest-state header, absent from ActionBase
)


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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


def parse_opcode_key(value: str) -> tuple[int, int] | None:
    match = OPCODE_RE.match(value)
    if not match:
        return None
    return int(match.group(1), 16), int(match.group(2), 16)


def compact_counts(values: dict[str, Any] | None, *, limit: int = 6) -> dict[str, Any]:
    if not values:
        return {}
    return dict(list(values.items())[:limit])


def action_name_from_formatter_type(type_name: str) -> str:
    clean = type_name[:-1] if type_name.endswith("&") else type_name
    action_type = clean.split("+", 1)[0]
    for prefix in (
        "Beyond_Gameplay_Actions_",
        "Beyond_Gameplay_",
        "Beyond_",
    ):
        if action_type.startswith(prefix):
            action_type = action_type[len(prefix):]
            break
    if action_type.endswith("_ForMemoryPack"):
        action_type = action_type[:-len("_ForMemoryPack")]
    elif action_type.endswith("ForMemoryPack"):
        action_type = action_type[:-len("ForMemoryPack")]
    return action_type


def formatter_name_from_type(type_name: str) -> str:
    clean = type_name[:-1] if type_name.endswith("&") else type_name
    if "+" in clean:
        return clean.split("+", 1)[1]
    return clean


def metadata_slot_row(pe: Any, md: Any, slot_va: int) -> dict[str, Any] | None:
    try:
        encoded = pe.u64_at_va(slot_va)
    except Exception:
        return None
    kind = encoded >> 29
    index = (encoded & 0x1FFFFFFE) >> 1
    type_name = md.metadata_type_name(index) if kind == 2 else ""
    return {
        "slotVa": f"0x{slot_va:x}",
        "encoded": f"0x{encoded:x}",
        "metadataKind": kind,
        "metadataTypeIndex": index,
        "typeName": type_name,
        "formatterName": formatter_name_from_type(type_name) if type_name else "",
        "actionName": action_name_from_formatter_type(type_name) if type_name else "",
    }


def is_formatter_slot(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    type_name = str(row.get("typeName") or "")
    return (
        row.get("metadataKind") == 2
        and "ForMemoryPack" in type_name
        and "Formatter" in type_name
    )


def parse_immediate(value: Any) -> int | None:
    text = str(value or "")
    if text == "0":
        return 0
    if re.fullmatch(r"0x[0-9a-f]+", text, flags=re.IGNORECASE):
        return int(text, 16)
    return None


def find_formatter_cctor(md: Any, *, type_name: str, method_name: str) -> tuple[Any, Any, str]:
    for type_def in md.types:
        full_name = md.type_full_name(type_def)
        if full_name != type_name:
            continue
        for method in md.methods_for(type_def):
            if md.string(method.name_index) == method_name:
                image_name = md.image_name_by_type_index.get(type_def.index, "")
                return type_def, method, image_name
    raise RuntimeError(f"method not found: {type_name}.{method_name}")


def method_pointer_for(
    *,
    method: Any,
    image_name: str,
    ranges: dict[str, dict[str, int]],
    pointers_by_image: dict[str, list[int]],
    target_name: str,
) -> tuple[int, int]:
    image_range = ranges.get(image_name)
    if not image_range:
        raise RuntimeError(f"missing IL2CPP image range for {image_name}")
    slot = method.index - image_range["methodStart"]
    pointers = pointers_by_image.get(image_name) or []
    if slot < 0 or slot >= len(pointers):
        raise RuntimeError(
            f"method slot {slot} outside pointer table for {image_name} "
            f"(methodIndex={method.index})"
        )
    pointer = pointers[slot]
    if not pointer:
        raise RuntimeError(f"null method pointer for {target_name}")
    return pointer, slot


def extract_formatter_tags(
    *,
    pe: Any,
    md: Any,
    body_helper: Any,
    pointer: int,
    scan_size: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = pe.bytes_at_va(pointer, scan_size)
    instructions = body_helper.decode_x64_subset(data, pointer, stop_offset=len(data))
    unknown_count = sum(
        1 for instr in instructions
        if str(instr.get("text") or "").startswith("db ")
    )
    pending_formatter: dict[str, Any] | None = None
    last_arg_writes: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    registration_targets = Counter()

    for instr in instructions:
        text = str(instr.get("text") or "")
        write = instr.get("write") or {}
        value = str(write.get("value") or "")
        slot_match = SLOT_TARGET_RE.search(value)
        if slot_match:
            slot_va = int(slot_match.group(1), 16)
            slot = metadata_slot_row(pe, md, slot_va)
            if is_formatter_slot(slot):
                pending_formatter = {
                    **slot,
                    "loadOffset": int(instr.get("offset") or 0),
                    "loadVa": instr.get("va") or "",
                    "loadInstruction": text,
                }

        if text.startswith("call "):
            tag = None
            tag_write = last_arg_writes.get("r8")
            if tag_write:
                tag = parse_immediate((tag_write.get("write") or {}).get("value"))
            if tag is not None and pending_formatter:
                call_offset = int(instr.get("offset") or 0)
                load_offset = int(pending_formatter.get("loadOffset") or 0)
                # The generated registration block loads a formatter slot,
                # instantiates it, then calls RegisterFormatter with tag in r8.
                if 0 <= tag <= 0xFFFF and 0 < call_offset - load_offset <= 0x80:
                    target = text.split(" ", 1)[1]
                    registration_targets[target] += 1
                    rows.append(
                        {
                            "tag": tag,
                            "tagHex": f"0x{tag:04x}",
                            "codeHex": f"0x{tag:04x}",
                            "typeName": pending_formatter.get("typeName"),
                            "formatterName": pending_formatter.get("formatterName"),
                            "actionName": pending_formatter.get("actionName"),
                            "metadataSlot": {
                                "slotVa": pending_formatter.get("slotVa"),
                                "encoded": pending_formatter.get("encoded"),
                                "metadataKind": pending_formatter.get("metadataKind"),
                                "metadataTypeIndex": pending_formatter.get("metadataTypeIndex"),
                            },
                            "evidence": {
                                "loadOffset": f"0x{load_offset:x}",
                                "loadInstruction": pending_formatter.get("loadInstruction"),
                                "tagOffset": f"0x{int(tag_write.get('offset') or 0):x}",
                                "tagInstruction": tag_write.get("text"),
                                "registrationCallOffset": f"0x{call_offset:x}",
                                "registrationCallTarget": target,
                            },
                        }
                    )
                    pending_formatter = None
            last_arg_writes.clear()
            continue

        if write:
            reg = body_helper.canonical_arg_register(str(write.get("register") or ""))
            if reg:
                last_arg_writes[reg] = instr

    rows.sort(key=lambda row: int(row["tag"]))
    diagnostics = {
        "instructionCount": len(instructions),
        "unknownInstructionCount": unknown_count,
        "decodedBytes": len(data),
        "registrationCallTargets": dict(registration_targets.most_common()),
    }
    return rows, diagnostics


def load_opcode_audit(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def opcode_summary_row(opcode_row: dict[str, Any], tag_row: dict[str, Any] | None) -> dict[str, Any]:
    out = {
        "opcode": opcode_row.get("opcode"),
        "count": opcode_row.get("count"),
        "actionMapRoles": compact_counts(opcode_row.get("actionMapRoles")),
        "classes": compact_counts(opcode_row.get("classes")),
        "hints": compact_counts(opcode_row.get("hints")),
        "propertyRoles": compact_counts(opcode_row.get("propertyRoles")),
        "fieldSignatures": compact_counts(opcode_row.get("fieldSignatures"), limit=4),
        "propertyKeys": compact_counts(opcode_row.get("propertyKeys"), limit=6),
    }
    if tag_row:
        out.update(
            {
                "actionBaseTag": tag_row.get("tagHex"),
                "actionName": tag_row.get("actionName"),
                "formatterName": tag_row.get("formatterName"),
                "formatterType": tag_row.get("typeName"),
                "status": "mapped-actionbase-tag",
            }
        )
    else:
        out["status"] = "absent-from-actionbase-tags"
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def cross_reference_opcodes(
    opcode_audit: dict[str, Any],
    tag_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_tag = {int(row["tag"]): row for row in tag_rows}
    opcode_rows = list(opcode_audit.get("opcodeRows") or [])
    matched_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    observed_codes = Counter()

    for row in opcode_rows:
        parsed = parse_opcode_key(str(row.get("opcode") or ""))
        if not parsed:
            continue
        code, _kind = parsed
        observed_codes[code] += int(row.get("count") or 0)
        tag_row = by_tag.get(code)
        if tag_row:
            matched_rows.append(opcode_summary_row(row, tag_row))

    row_by_opcode = {str(row.get("opcode")): row for row in opcode_rows}
    for key in SELECTED_OPCODE_KEYS:
        parsed = parse_opcode_key(key)
        tag_row = by_tag.get(parsed[0]) if parsed else None
        opcode_row = row_by_opcode.get(key)
        if opcode_row:
            selected_rows.append(opcode_summary_row(opcode_row, tag_row))
        else:
            selected_rows.append(
                {
                    "opcode": key,
                    "count": 0,
                    "actionBaseTag": tag_row.get("tagHex") if tag_row else "",
                    "actionName": tag_row.get("actionName") if tag_row else "",
                    "formatterName": tag_row.get("formatterName") if tag_row else "",
                    "formatterType": tag_row.get("typeName") if tag_row else "",
                    "status": "tag-exists-no-observed-row" if tag_row else "absent-from-actionbase-tags",
                }
            )

    matched_rows.sort(key=lambda row: (-int(row.get("count") or 0), str(row.get("opcode") or "")))
    max_tag = max((int(row["tag"]) for row in tag_rows), default=-1)
    high_selected_absent = [
        row for row in selected_rows
        if row.get("status") == "absent-from-actionbase-tags"
        and (parse_opcode_key(str(row.get("opcode") or "")) or (0, 0))[0] > max_tag
    ]
    return {
        "opcodeAuditPath": repo_rel(REPORT_DIR / "levelscript_opcode_shape_audit.json")
        if opcode_audit else "",
        "opcodeAuditSummary": opcode_audit.get("summary") or {},
        "matchedObservedOpcodeCount": len(matched_rows),
        "matchedObservedRecordCount": sum(int(row.get("count") or 0) for row in matched_rows),
        "matchedObservedOpcodes": matched_rows[:120],
        "selectedOpcodes": selected_rows,
        "selectedHighOpcodesAbsentFromActionBase": high_selected_absent,
        "observedCodeCount": len(observed_codes),
    }


def tag_table_summary(tag_rows: list[dict[str, Any]], diagnostics: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    tags = [int(row["tag"]) for row in tag_rows]
    duplicate_tags = [
        {"tag": f"0x{tag:04x}", "count": count}
        for tag, count in Counter(tags).items()
        if count > 1
    ]
    missing_tags = [
        f"0x{tag:04x}"
        for tag in range(min(tags), max(tags) + 1)
        if tag not in set(tags)
    ] if tags else []
    summary = {
        "tagCount": len(tag_rows),
        "minTag": min(tags) if tags else None,
        "minTagHex": f"0x{min(tags):04x}" if tags else "",
        "maxTag": max(tags) if tags else None,
        "maxTagHex": f"0x{max(tags):04x}" if tags else "",
        "duplicateTagCount": len(duplicate_tags),
        "missingTagCountInsideRange": len(missing_tags),
        **diagnostics,
    }
    return duplicate_tags, missing_tags, summary


def build_formatter_table(
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
    target_type = str(target["type"])
    target_method_name = str(target["method"])
    type_def, method, image_name = find_formatter_cctor(
        md,
        type_name=target_type,
        method_name=target_method_name,
    )
    pointer, slot = method_pointer_for(
        method=method,
        image_name=image_name,
        ranges=ranges,
        pointers_by_image=pointers_by_image,
        target_name=f"{target_type}.{target_method_name}",
    )
    scan_size, next_pointer = body_helper.estimate_scan_size(pointer, sorted_all_pointers, max_scan_bytes)
    tag_rows, diagnostics = extract_formatter_tags(
        pe=pe,
        md=md,
        body_helper=body_helper,
        pointer=pointer,
        scan_size=scan_size,
    )
    duplicate_tags, missing_tags, summary = tag_table_summary(tag_rows, diagnostics)
    return {
        "id": target.get("id"),
        "label": target.get("label"),
        "primary": bool(target.get("primary")),
        "targetMethod": {
            "type": target_type,
            "method": target_method_name,
            "image": image_name,
            "typeIndex": type_def.index,
            "typeToken": f"0x{type_def.token:08x}",
            "methodIndex": method.index,
            "methodToken": f"0x{method.token:08x}",
            "moduleMethodSlot": slot,
            "methodPointerVa": f"0x{pointer:x}",
            "scanBytes": scan_size,
            "nextMethodPointerVa": f"0x{next_pointer:x}" if next_pointer else "",
        },
        "summary": summary,
        "duplicateTags": duplicate_tags,
        "missingTagsInsideRange": missing_tags[:200],
        "formatterTags": tag_rows,
    }


def key_findings(payload: dict[str, Any]) -> list[str]:
    tag_summary = payload.get("summary") or {}
    by_opcode = {
        row.get("opcode"): row
        for row in (payload.get("opcodeCrossReference") or {}).get("selectedOpcodes") or []
    }
    findings = [
        (
            "ActionBase formatter tags were recovered from the generated "
            f"MemoryPack cctor: {tag_summary.get('tagCount')} contiguous tags "
            f"{tag_summary.get('minTagHex')}..{tag_summary.get('maxTagHex')}."
        ),
        (
            "For normal action-map records, the raw LevelScript record code now "
            "bridges directly to an ActionBase formatter class; the separate "
            "kind byte remains payload-shape evidence."
        ),
    ]
    final_table = next(
        (
            table for table in payload.get("formatterTables") or []
            if table.get("id") == "finalActionBase"
        ),
        {},
    )
    if final_table:
        final_summary = final_table.get("summary") or {}
        final_actions = ", ".join(
            row.get("actionName", "")
            for row in final_table.get("formatterTags") or []
            if row.get("actionName")
        )
        findings.append(
            "FinalActionBase formatter was checked separately: it registers "
            f"{final_summary.get('tagCount')} tags "
            f"{final_summary.get('minTagHex')}..{final_summary.get('maxTagHex')}"
            + (f" ({final_actions})." if final_actions else ".")
        )
    for opcode in ("0x03da/0x0a", "0x0410/0x0a", "0x0413/0x0a"):
        row = by_opcode.get(opcode) or {}
        if row.get("actionName"):
            findings.append(
                f"{opcode} is named by the ActionBase table as {row.get('actionName')} "
                f"({row.get('count')} observed records)."
            )
    row_0176 = by_opcode.get("0x0176/0x08") or {}
    if row_0176.get("actionName"):
        findings.append(
            f"0x0176/0x08 maps to {row_0176.get('actionName')}, so its property-key "
            "payload is a list-clear target, not setter proof."
        )
    for opcode in ("0x0a03/0x00", "0x0bed/0x00", "0x12be/0x00", "0x12c0/0x00", "0x1355/0x00", "0x1385/0x00"):
        row = by_opcode.get(opcode) or {}
        if row.get("status") == "absent-from-actionbase-tags":
            findings.append(
                f"{opcode} is absent from the ActionBase union tag range; keep it in the "
                "LevelScript event/gate/terminal family until that separate table is decoded."
            )
    return findings


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog_helper = load_module(CATALOG_HELPER, "endfield_catalog_option_flow")
    body_helper = load_module(BODY_HELPER, "endfield_body_targets")
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
    formatter_tables = [
        build_formatter_table(
            target=target,
            pe=pe,
            md=md,
            body_helper=body_helper,
            ranges=ranges,
            pointers_by_image=pointers_by_image,
            sorted_all_pointers=sorted_all_pointers,
            max_scan_bytes=args.max_scan_bytes,
        )
        for target in FORMATTER_TARGETS
    ]
    primary_table = next((table for table in formatter_tables if table.get("primary")), formatter_tables[0])
    tag_rows = list(primary_table.get("formatterTags") or [])
    opcode_cross_ref = cross_reference_opcodes(load_opcode_audit(args.opcode_audit), tag_rows)
    summary = dict(primary_table.get("summary") or {})
    summary.update(
        {
            "opcodeAuditMatchedRows": opcode_cross_ref.get("matchedObservedOpcodeCount"),
            "opcodeAuditMatchedRecords": opcode_cross_ref.get("matchedObservedRecordCount"),
            "checkedFormatterTableCount": len(formatter_tables),
            "additionalFormatterTables": [
                {
                    "id": table.get("id"),
                    "label": table.get("label"),
                    "tagCount": (table.get("summary") or {}).get("tagCount"),
                    "minTagHex": (table.get("summary") or {}).get("minTagHex"),
                    "maxTagHex": (table.get("summary") or {}).get("maxTagHex"),
                }
                for table in formatter_tables
                if not table.get("primary")
            ],
        }
    )
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metadata": {
            "metadataPath": str(metadata_path),
            "metadataSha256": sha256_file(metadata_path),
            "gameAssembly": str(args.gameassembly),
            "gameAssemblySha256": sha256_file(args.gameassembly),
            "imageBase": f"0x{pe.image_base:x}",
            "codeRegistration": f"0x{code_reg:x}",
        },
        "settings": {
            "maxScanBytes": args.max_scan_bytes,
            "opcodeAudit": repo_rel(args.opcode_audit),
        },
        "targetMethod": primary_table.get("targetMethod") or {},
        "summary": summary,
        "duplicateTags": primary_table.get("duplicateTags") or [],
        "missingTagsInsideRange": primary_table.get("missingTagsInsideRange") or [],
        "formatterTags": tag_rows,
        "formatterTables": formatter_tables,
        "opcodeCrossReference": opcode_cross_ref,
    }
    payload["keyFindings"] = key_findings(payload)
    return payload


def markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join(md_escape(value) for value in values) + " |"


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary") or {}
    target = payload.get("targetMethod") or {}
    cross_ref = payload.get("opcodeCrossReference") or {}
    lines: list[str] = [
        "# LevelScript ActionBase Formatter Tag Audit",
        "",
        "## Summary",
        "",
        f"- Metadata: `{md_escape(payload['metadata'].get('metadataPath', ''))}`",
        f"- GameAssembly: `{md_escape(payload['metadata'].get('gameAssembly', ''))}`",
        f"- Target: `{md_escape(target.get('type', ''))}.{md_escape(target.get('method', ''))}`",
        f"- Method VA: `{md_escape(target.get('methodPointerVa', ''))}`; scan bytes: `{target.get('scanBytes')}`",
        f"- Tags: `{summary.get('tagCount')}` (`{summary.get('minTagHex')}`..`{summary.get('maxTagHex')}`)",
        f"- Checked formatter tables: `{summary.get('checkedFormatterTableCount', 1)}`",
        f"- Opcode audit matched rows: `{summary.get('opcodeAuditMatchedRows')}` / records: `{summary.get('opcodeAuditMatchedRecords')}`",
        f"- Duplicate tags: `{summary.get('duplicateTagCount')}`; missing tags inside range: `{summary.get('missingTagCountInsideRange')}`",
        "",
        "## Interpretation",
        "",
    ]
    for finding in payload.get("keyFindings") or []:
        lines.append(f"- {md_escape(finding)}")

    additional_tables = [
        table for table in payload.get("formatterTables") or []
        if not table.get("primary")
    ]
    lines.extend(["", "## Additional Formatter Tables", ""])
    if additional_tables:
        lines.append(markdown_table_row(["table", "method VA", "tags", "registered actions"]))
        lines.append(markdown_table_row(["---", "---:", "---", "---"]))
        for table in additional_tables:
            table_summary = table.get("summary") or {}
            table_target = table.get("targetMethod") or {}
            actions = ", ".join(
                f"{row.get('tagHex')}:{row.get('actionName')}"
                for row in table.get("formatterTags") or []
            )
            lines.append(
                markdown_table_row(
                    [
                        table.get("label", ""),
                        table_target.get("methodPointerVa", ""),
                        (
                            f"{table_summary.get('tagCount')} "
                            f"({table_summary.get('minTagHex')}..{table_summary.get('maxTagHex')})"
                        ),
                        actions,
                    ]
                )
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Selected Opcode Cross-Reference", ""])
    selected = cross_ref.get("selectedOpcodes") or []
    if selected:
        lines.append(markdown_table_row(["opcode", "count", "status", "ActionBase action", "classes", "hints", "roles"]))
        lines.append(markdown_table_row(["---", "---:", "---", "---", "---", "---", "---"]))
        for row in selected:
            lines.append(
                markdown_table_row(
                    [
                        row.get("opcode", ""),
                        row.get("count", ""),
                        row.get("status", ""),
                        row.get("actionName", ""),
                        ", ".join(f"{k}:{v}" for k, v in (row.get("classes") or {}).items()),
                        ", ".join(f"{k}:{v}" for k, v in (row.get("hints") or {}).items()),
                        ", ".join(f"{k}:{v}" for k, v in (row.get("actionMapRoles") or {}).items()),
                    ]
                )
            )
    else:
        lines.append("- Opcode audit was not available.")

    lines.extend(["", "## Top Observed ActionBase Matches", ""])
    matched = cross_ref.get("matchedObservedOpcodes") or []
    if matched:
        lines.append(markdown_table_row(["opcode", "count", "ActionBase action", "classes", "hints"]))
        lines.append(markdown_table_row(["---", "---:", "---", "---", "---"]))
        for row in matched[:40]:
            lines.append(
                markdown_table_row(
                    [
                        row.get("opcode", ""),
                        row.get("count", ""),
                        row.get("actionName", ""),
                        ", ".join(f"{k}:{v}" for k, v in (row.get("classes") or {}).items()),
                        ", ".join(f"{k}:{v}" for k, v in (row.get("hints") or {}).items()),
                    ]
                )
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Tag Samples", ""])
    sample_tags = [
        0,
        1,
        0x034A,
        0x0357,
        0x0360,
        0x0363,
        0x0455,
        0x045D,
        0x049E,
        0x049F,
        0x04BD,
        0x0520,
    ]
    by_tag = {int(row["tag"]): row for row in payload.get("formatterTags") or []}
    lines.append(markdown_table_row(["tag", "ActionBase action", "formatter type"]))
    lines.append(markdown_table_row(["---:", "---", "---"]))
    for tag in sample_tags:
        row = by_tag.get(tag)
        if not row:
            continue
        lines.append(markdown_table_row([f"0x{tag:04x}", row.get("actionName", ""), row.get("typeName", "")]))

    write_text_if_changed(path, "\n".join(lines).rstrip() + "\n")


def build_name_contract(payload: dict[str, Any], audit_path: Path) -> dict[str, Any]:
    metadata = payload.get("metadata") or {}
    return {
        "schema": "levelScriptActionBaseFormatterNames.v1",
        "sourceAudit": repo_rel(audit_path),
        "metadata": {
            key: metadata.get(key)
            for key in (
                "metadataSha256",
                "gameAssemblySha256",
                "imageBase",
                "codeRegistration",
            )
        },
        "targetMethod": payload.get("targetMethod") or {},
        "summary": payload.get("summary") or {},
        "actionNames": [
            str(row.get("actionName") or "")
            for row in payload.get("formatterTags") or []
        ],
        "evidenceBoundary": (
            "Indexed names come from the installed ActionBaseForMemoryPack "
            "formatter cctor. Consumers must validate every source/table gate "
            "and use compact unionTag plus serializedMemberCount; raw combined "
            "opcodes, filenames, OCR, and manual order are not tag evidence."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--code-registration", default=DEFAULT_CODE_REGISTRATION)
    parser.add_argument("--max-scan-bytes", type=int, default=0x40000)
    parser.add_argument(
        "--opcode-audit",
        type=Path,
        default=REPORT_DIR / "levelscript_opcode_shape_audit.json",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=REPORT_DIR / "levelscript_actionbase_formatter_tags.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=REPORT_DIR / "levelscript_actionbase_formatter_tags.md",
    )
    parser.add_argument(
        "--name-contract",
        type=Path,
        default=DEFAULT_NAME_CONTRACT,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_report(args)
    write_report_json(args.json, payload)
    write_markdown(args.markdown, payload)
    write_report_json(
        args.name_contract,
        build_name_contract(payload, args.json),
    )
    summary = payload.get("summary") or {}
    print(
        "wrote "
        f"{repo_rel(args.json)}, {repo_rel(args.markdown)}, and "
        f"{repo_rel(args.name_contract)} "
        f"(tags={summary.get('tagCount')}, matchedRows={summary.get('opcodeAuditMatchedRows')})"
    )


if __name__ == "__main__":
    main()
