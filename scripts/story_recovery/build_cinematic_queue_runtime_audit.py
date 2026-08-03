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


def method_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("type") or ""), str(row.get("method") or "")


def resolved_calls(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        call
        for call in row.get("directCalls") or []
        if call.get("resolved")
    ]


def call_targets(call: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(target.get("type") or ""), str(target.get("method") or ""))
        for target in call.get("resolved") or []
    }


def discover_enqueue_family(
    base_name: str,
    handle_name: str,
    mapped: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Recover the sink and its transitive native producers from signatures/calls."""
    manager_name = handle_name.split("+", 1)[0]
    sinks = [
        row for row in mapped
        if row.get("type") == manager_name
        and any(
            parameter.get("typeName") == base_name
            for parameter in row.get("parameterDetails") or []
        )
        and row.get("mappingStatus") == "mapped"
    ]
    if len(sinks) != 1:
        raise RuntimeError(
            "validator=cinematic_queue_runtime failed: gate=enqueue_sink "
            f"expected=one_manager_method_accepting_queue_base actual={len(sinks)}"
        )

    sink = sinks[0]
    row_by_key = {method_key(row): row for row in mapped}
    family = {method_key(sink)}
    changed = True
    while changed:
        changed = False
        for row in mapped:
            key = method_key(row)
            if key in family or row.get("mappingStatus") != "mapped":
                continue
            if any(call_targets(call) & family for call in resolved_calls(row)):
                family.add(key)
                changed = True

    producers = [row_by_key[key] for key in family if key != method_key(sink)]
    producers.sort(key=lambda row: (str(row.get("type")), str(row.get("method"))))
    edges: list[dict[str, Any]] = []
    for row in [sink, *producers]:
        for call in resolved_calls(row):
            for target in sorted(call_targets(call) & family):
                edges.append({
                    "caller": f"{row.get('type')}::{row.get('method')}",
                    "callee": f"{target[0]}::{target[1]}",
                    "callerOffset": call.get("offset"),
                    "targetVa": call.get("targetVa"),
                    "argumentRegisterWrites": (
                        (call.get("argumentContext") or {}).get("argRegisterWrites")
                        or {}
                    ),
                })
    return sink, producers, edges


def analyze_action_producer_routes(
    action_rows: list[dict[str, Any]],
    producers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find serialized action methods that reach a recovered producer.

    The seed is the action framework's virtual surface (plus recursively called
    same-type helpers assembled by ``build_action_body_rows``). No action class,
    payload class, Story id, or field name is allowlisted here.
    """
    producer_by_key = {method_key(row): row for row in producers}
    routes: list[dict[str, Any]] = []
    for row in action_rows:
        hits: dict[tuple[str, str], dict[str, Any]] = {}
        for call in resolved_calls(row):
            for target in call_targets(call) & producer_by_key.keys():
                hits[target] = call
        for target, call in sorted(hits.items()):
            producer = producer_by_key[target]
            routes.append({
                "actionType": str(row.get("type") or "").rsplit(".", 1)[-1],
                "actionFullType": row.get("type"),
                "actionMethod": row.get("method"),
                "actionMethodSlot": row.get("slot"),
                "actionToken": row.get("token"),
                "actionVa": row.get("methodPointerVa"),
                "declaredFields": [
                    field.get("name") for field in row.get("typeFields") or []
                    if field.get("name")
                ],
                "producerType": producer.get("type"),
                "producerMethod": producer.get("method"),
                "producerToken": producer.get("token"),
                "producerVa": producer.get("methodPointerVa"),
                "callOffset": call.get("offset"),
                "argumentRegisterWrites": (
                    (call.get("argumentContext") or {}).get("argRegisterWrites")
                    or {}
                ),
            })
    routes.sort(key=lambda row: (
        str(row["actionFullType"]),
        str(row["actionMethod"]),
        str(row["producerMethod"]),
    ))
    return routes


def analyze_contract(
    catalog: dict[str, Any],
    body_map: dict[str, Any],
    action_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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

    enqueue_sink, native_producers, enqueue_edges = discover_enqueue_family(
        base_name,
        handle_name,
        mapped,
    )
    if not enqueue_edges or not native_producers:
        raise RuntimeError(
            "validator=cinematic_queue_runtime failed: gate=producer_family "
            "expected=transitive_native_callers actual=missing"
        )
    action_producer_routes = analyze_action_producer_routes(
        action_rows or [],
        native_producers,
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
        "enqueueSink": method_signature(enqueue_sink),
        "nativeProducers": [method_signature(row) for row in native_producers],
        "actionProducerRoutes": action_producer_routes,
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
        f"- native enqueue producers: `{len(contract['nativeProducers'])}`",
        f"- typed serialized action routes: `{len(contract['actionProducerRoutes'])}`",
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
    lines.extend(["", "## Original-Data Producer Join", ""])
    for row in contract["actionProducerRoutes"]:
        lines.append(
            f"- `{row['actionFullType']}::{row['actionMethod']}` -> "
            f"`{row['producerType']}::{row['producerMethod']}`"
        )
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "The original binary proves the handle and payload contract, but a Lua "
        "dispatcher call contains no static mission or quest identity. Mission ownership "
        "must be recovered from the serialized action row that calls the producer. "
        "Those exact LevelScript rows and their owning event/control paths may attach "
        "files to a mission; queue order and code address order create no Story-order edge.",
        "",
    ])
    return "\n".join(lines)


def mapper_args(
    args: argparse.Namespace,
    metadata_path: Path,
    catalog_path: Path,
    *,
    body_summary_method_regex: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        gameassembly=args.gameassembly,
        metadata=metadata_path,
        catalog=catalog_path,
        code_registration=args.code_registration,
        include_generic_instantiations=False,
        metadata_registration="",
        head_bytes=32,
        max_scan_bytes=0x8000,
        arg_context_window=96,
        body_summary_method_regex=body_summary_method_regex,
        body_summary_max_instructions=500,
        include_unresolved_calls=True,
    )


def build_action_body_rows(
    args: argparse.Namespace,
    metadata_path: Path,
    md: Any,
    catalog_module: Any,
    mapper: Any,
    temp_root: Path,
) -> list[dict[str, Any]]:
    """Map the general action virtual surface and recursively used helpers."""
    action_catalog = catalog_module.build_catalog(
        md,
        re.compile(r"^Beyond\.Gameplay\.Actions\."),
        re.compile(r"(?!)"),
        re.compile(r".*"),
        re.compile(r"^Beyond\.Gameplay\.Actions\."),
        re.compile(r"Beyond", re.IGNORECASE),
        only_focus=False,
        include_all_members=True,
        body_context=0,
    )
    all_targets = action_catalog.get("bodyTargets") or []
    target_by_key = {method_key(row): row for row in all_targets}
    pending = {
        key for key, row in target_by_key.items()
        if int(row.get("slot", 65535)) != 65535
    }
    mapped: dict[tuple[str, str], dict[str, Any]] = {}
    round_index = 0
    while pending:
        round_index += 1
        if round_index > 6:
            raise RuntimeError(
                "validator=cinematic_queue_runtime failed: gate=action_helper_closure "
                f"expected=converged_within_6_rounds actual=pending:{len(pending)}"
            )
        selected = [target_by_key[key] for key in sorted(pending)]
        round_catalog = {
            "metadata": action_catalog.get("metadata"),
            "settings": action_catalog.get("settings"),
            "summary": {"bodyTargetMethodCount": len(selected)},
            "bodyTargets": selected,
        }
        catalog_path = temp_root / f"action_catalog_{round_index}.json"
        catalog_path.write_text(json.dumps(round_catalog), encoding="utf-8")
        report = mapper.build_report(mapper_args(
            args,
            metadata_path,
            catalog_path,
            body_summary_method_regex=r"(?!)",
        ))
        new_rows = report.get("bodyTargets") or []
        for row in new_rows:
            mapped[method_key(row)] = row
        pending = set()
        for row in new_rows:
            caller_type = str(row.get("type") or "")
            for call in resolved_calls(row):
                for target in call_targets(call):
                    if (
                        target[0] == caller_type
                        and target in target_by_key
                        and target not in mapped
                    ):
                        pending.add(target)
    return [mapped[key] for key in sorted(mapped)]


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
        re.compile(r".*"),
        re.compile(
            r"^(?:Beyond\.Gameplay\.Actions\.GameAction|"
            r"Beyond\.Gameplay\.Core\.(?:CinematicQueueManager(?:\+.*)?|"
            r".*QueueItemData(?:Base)?))$",
            re.IGNORECASE,
        ),
        re.compile(r"Beyond", re.IGNORECASE),
        only_focus=False,
        include_all_members=True,
        body_context=1,
    )
    with tempfile.TemporaryDirectory(prefix="endfield-cinematic-queue-") as temp:
        catalog_path = Path(temp) / "catalog.json"
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        body_map = mapper.build_report(mapper_args(
            args,
            metadata_path,
            catalog_path,
            body_summary_method_regex=r".*",
        ))
        action_rows = build_action_body_rows(
            args,
            metadata_path,
            md,
            catalog_module,
            mapper,
            Path(temp),
        )
    contract = analyze_contract(catalog, body_map, action_rows)
    return {
        "schemaVersion": "cinematicQueueRuntimeAudit.v2",
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
            "nativeProducerCount": len(contract["nativeProducers"]),
            "typedActionProducerRouteCount": len(contract["actionProducerRoutes"]),
            "typedActionProducerTypeCount": len({
                row["actionFullType"]
                for row in contract["actionProducerRoutes"]
            }),
        },
        "contract": contract,
        "conclusion": {
            "luaCallsAreRuntimeDispatchers": True,
            "staticMissionOwnership": False,
            "staticStoryOrder": False,
            "nextEvidence": (
                "Join each structurally discovered action type to exact decoded "
                "LevelScript rows; attach mission ownership only from those original "
                "rows and their authored event/control paths."
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
        f"producers={payload['summary']['nativeProducerCount']} "
        f"actionRoutes={payload['summary']['typedActionProducerRouteCount']} "
        f"enqueueEdges={payload['summary']['enqueueEdgeCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
