#!/usr/bin/env python3
"""Recover the general native cinematic-queue handle contract.

The shipped Lua ``CinematicSystem`` receives a polymorphic queue handle and
dispatches it by ``queueItemType``.  This audit deliberately discovers that
contract from the installed IL2CPP metadata and GameAssembly method bodies;
it does not contain a list of Story ids or per-object exceptions.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "endfield-il2cpp"
DEFAULT_GAMEASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_JSON = ROOT / "reports" / "story" / "recovery" / "cinematic_queue_runtime_audit.json"
DEFAULT_MD = ROOT / "reports" / "story" / "recovery" / "cinematic_queue_runtime_audit.md"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def method_signature(row: dict[str, Any]) -> dict[str, Any]:
    body = row.get("methodBodySummary") or {}
    return {
        "type": row.get("type"),
        "method": row.get("method"),
        "methodIndex": row.get("methodIndex"),
        "token": row.get("token"),
        "parameters": row.get("parameterDetails") or [],
        "mappingStatus": row.get("mappingStatus"),
        "va": row.get("methodPointerVa"),
        "rva": row.get("methodPointerRva"),
        "fileOffset": row.get("fileOffset"),
        "bodyEvidence": {
            "instructionCount": body.get("instructionCount"),
            "firstRetOffset": body.get("firstRetOffset"),
            "fieldLikeOrigins": body.get("fieldLikeOrigins") or {},
            "fieldAccesses": body.get("fieldAccesses") or [],
            "paramFlow": body.get("paramFlow") or {},
            "calls": [
                {
                    "offset": call.get("offset"),
                    "targetVa": call.get("targetVa"),
                    "resolved": call.get("resolved") or [],
                }
                for call in body.get("calls") or []
            ],
        },
    }


def analyze_contract(catalog: dict[str, Any], body_map: dict[str, Any]) -> dict[str, Any]:
    """Find the queue contract by shape rather than a per-subtype allowlist."""
    types = catalog.get("matchedTypes") or []
    base_candidates = []
    handle_candidates = []
    for row in types:
        fields = {str(field.get("name") or "") for field in row.get("fields") or []}
        methods = {str(method.get("name") or "") for method in row.get("methods") or []}
        if "cinematicId" in fields and "get_queueItemType" in methods:
            base_candidates.append(row)
        if {"id", "data"}.issubset(fields) and "Finish" in methods:
            handle_candidates.append(row)
    if len(base_candidates) != 1 or len(handle_candidates) != 1:
        raise RuntimeError(
            "validator=cinematic_queue_runtime failed: gate=structural_types "
            f"expected=base:1,handle:1 actual=base:{len(base_candidates)},"
            f"handle:{len(handle_candidates)}"
        )

    base = base_candidates[0]
    handle = handle_candidates[0]
    base_name = str(base["fullName"])
    handle_name = str(handle["fullName"])
    mapped = body_map.get("bodyTargets") or []
    dispatchers = []
    for row in mapped:
        params = row.get("parameterDetails") or []
        if (
            str(row.get("method") or "").endswith("ByHandle")
            and len(params) == 1
            and params[0].get("typeName") == handle_name
        ):
            dispatchers.append(method_signature(row))
    dispatchers.sort(key=lambda row: (str(row["type"]), str(row["method"])))
    if not dispatchers or any(row.get("mappingStatus") != "mapped" for row in dispatchers):
        raise RuntimeError(
            "validator=cinematic_queue_runtime failed: gate=dispatcher_bodies "
            f"expected=one_or_more_mapped actual={len(dispatchers)}"
        )

    payloads = []
    for row in types:
        methods = row.get("methods") or []
        if row.get("fullName") == base_name:
            continue
        if not any(method.get("name") == "get_queueItemType" for method in methods):
            continue
        id_getters = sorted(
            str(method.get("name") or "")
            for method in methods
            if str(method.get("name") or "").startswith("get_")
            and method.get("name") != "get_queueItemType"
            and str(method.get("returnTypeName") or "").startswith("System.String")
        )
        fields = sorted(
            str(field.get("name") or "")
            for field in row.get("fields") or []
        )
        payloads.append({
            "type": row.get("fullName"),
            "token": row.get("token"),
            "idGetters": id_getters,
            "declaredFields": fields,
        })
    payloads.sort(key=lambda row: str(row["type"]))

    enqueue_edges = []
    for edge in body_map.get("directCallEdges") or []:
        caller = edge.get("caller") or {}
        callees = edge.get("callees") or []
        if str(caller.get("method") or "").startswith("AddCinematic"):
            for callee in callees:
                if str(callee.get("method") or "").startswith("AddCinematic"):
                    enqueue_edges.append({
                        "caller": f"{caller.get('type')}::{caller.get('method')}",
                        "callee": f"{callee.get('type')}::{callee.get('method')}",
                        "callerOffset": edge.get("offset"),
                        "targetVa": edge.get("targetVa"),
                        "argumentRegisterWrites": (
                            (edge.get("argumentContext") or {}).get(
                                "argRegisterWrites"
                            ) or {}
                        ),
                    })
    if not enqueue_edges:
        raise RuntimeError(
            "validator=cinematic_queue_runtime failed: gate=enqueue_edge "
            "expected=native_direct_call actual=missing"
        )

    return {
        "queueBase": {
            "type": base_name,
            "token": base.get("token"),
            "fields": [field for field in base.get("fields") or []],
            "queueTypeGetter": next(
                method for method in base.get("methods") or []
                if method.get("name") == "get_queueItemType"
            ),
        },
        "queueHandle": {
            "type": handle_name,
            "token": handle.get("token"),
            "fields": [field for field in handle.get("fields") or []],
            "finishMethod": next(
                method for method in handle.get("methods") or []
                if method.get("name") == "Finish"
            ),
        },
        "payloadTypes": payloads,
        "nativeDispatchers": dispatchers,
        "nativeDispatcherMethods": [str(row["method"]) for row in dispatchers],
        "enqueueEdges": enqueue_edges,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    contract = payload["contract"]
    lines = [
        "# Cinematic Queue Runtime Audit",
        "",
        f"- GameAssembly SHA-256: `{payload['source']['gameAssemblySha256']}`",
        f"- IL2CPP metadata SHA-256: `{payload['source']['metadataSha256']}`",
        f"- queue base: `{contract['queueBase']['type']}`",
        f"- queue handle: `{contract['queueHandle']['type']}`",
        f"- native one-handle dispatchers: `{len(contract['nativeDispatchers'])}`",
        f"- polymorphic payload types: `{len(contract['payloadTypes'])}`",
        "",
        "## General Contract",
        "",
        "Every queue item inherits the original `cinematicId` carrier and a typed "
        "`queueItemType` getter. The native queue manager allocates one handle, copies "
        "the item into its `data` field, and forwards that handle to Lua. Lua dispatches "
        "the same handle by queue type; these calls are runtime execution branches, not "
        "seven independently authored Story references.",
        "",
        "## Native Dispatchers",
        "",
    ]
    for row in contract["nativeDispatchers"]:
        lines.append(
            f"- `{row['type']}::{row['method']}` token=`{row['token']}` "
            f"VA=`{row['va']}`"
        )
    lines.extend(["", "## Payload Identity Accessors", ""])
    for row in contract["payloadTypes"]:
        getters = ", ".join(f"`{value}`" for value in row["idGetters"]) or "none"
        lines.append(f"- `{row['type']}`: {getters}")
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "The original binary proves the handle and payload contract, but a Lua "
        "dispatcher call contains no static mission or quest identity. Mission ownership "
        "must be recovered from the native producer's original data row; queue order and "
        "code address order create no Story-order edge.",
        "",
    ])
    return "\n".join(lines)


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    catalog_module = load_module(
        "endfield_cinematic_catalog",
        TOOLS / "catalog_option_flow_metadata.py",
    )
    mapper = load_module(
        "endfield_cinematic_mapper",
        TOOLS / "map_body_targets_to_gameassembly.py",
    )
    metadata_path = catalog_module.resolve_metadata_path(
        args.metadata,
        prefer_cache=True,
    )
    md = catalog_module.Metadata(metadata_path)
    catalog = catalog_module.build_catalog(
        md,
        re.compile(r"CinematicQueue|GameAction", re.IGNORECASE),
        re.compile(r"cinematicId|queueItemType|ByHandle|AddCinematic|Finish", re.IGNORECASE),
        re.compile(r"ByHandle$|^AddCinematic", re.IGNORECASE),
        re.compile(r"CinematicQueue|GameAction", re.IGNORECASE),
        re.compile(r"Beyond", re.IGNORECASE),
        only_focus=False,
        include_all_members=True,
        body_context=1,
    )
    with tempfile.TemporaryDirectory(prefix="endfield-cinematic-queue-") as temp:
        catalog_path = Path(temp) / "catalog.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        body_map = mapper.build_report(SimpleNamespace(
            gameassembly=args.gameassembly,
            metadata=metadata_path,
            catalog=catalog_path,
            code_registration=args.code_registration,
            include_generic_instantiations=False,
            metadata_registration="",
            head_bytes=32,
            max_scan_bytes=0x4000,
            arg_context_window=96,
            body_summary_method_regex=(
                r"^(AddCinematicQueueItem|AddCinematicItem2Queue|.*ByHandle)$"
            ),
            body_summary_max_instructions=300,
            include_unresolved_calls=True,
        ))
    contract = analyze_contract(catalog, body_map)
    return {
        "schemaVersion": "cinematicQueueRuntimeAudit.v1",
        "source": {
            "gameAssembly": str(args.gameassembly),
            "gameAssemblySha256": sha256_path(args.gameassembly),
            "metadata": str(metadata_path),
            "metadataSha256": sha256_path(metadata_path),
            "codeRegistration": body_map.get("codeRegistration"),
        },
        "summary": {
            "payloadTypeCount": len(contract["payloadTypes"]),
            "nativeDispatcherCount": len(contract["nativeDispatchers"]),
            "mappedNativeDispatcherCount": sum(
                row.get("mappingStatus") == "mapped"
                for row in contract["nativeDispatchers"]
            ),
            "enqueueEdgeCount": len(contract["enqueueEdges"]),
        },
        "contract": contract,
        "conclusion": {
            "luaCallsAreRuntimeDispatchers": True,
            "staticMissionOwnership": False,
            "staticStoryOrder": False,
            "nextEvidence": (
                "Trace native queue-item producers back to original table/LevelScript "
                "rows that co-carry cinematicId and mission/quest identity."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--code-registration", default="0x18b9217d0")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(payload), encoding="utf-8")
    print(f"cinematic queue runtime audit: {args.json}")
    print(
        f"dispatchers={payload['summary']['nativeDispatcherCount']} "
        f"payloads={payload['summary']['payloadTypeCount']} "
        f"enqueueEdges={payload['summary']['enqueueEdgeCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
