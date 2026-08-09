#!/usr/bin/env python3
"""Recover option-outcome to mission-objective dependencies from original data.

The recovery is deliberately corpus-driven.  It accepts only an exact dialog
finish number written by an authored DialogTree finish node or Timeline option
playable and consumed by a MissionRuntime ``CheckTalkOptionFinish`` objective.
It never uses filenames, numeric suffixes, OCR, or manual order overrides as an
ordering or branch signal.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIPELINE_ROOT = ROOT / "webui" / "data" / "mission_pipeline"
DEFAULT_TIMELINE_ORDERS = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "timeline_line_orders.json"
)
DEFAULT_GAME_ASSEMBLY = Path(r"D:\Program Files\Endfield Game\GameAssembly.dll")
DEFAULT_METADATA = Path(
    r"D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata"
    r"\global-metadata.dat"
)
DEFAULT_JSON = (
    ROOT / "reports" / "story" / "recovery" / "dialog_finish_branch_audit.json"
)
DEFAULT_MARKDOWN = (
    ROOT / "reports" / "story" / "recovery" / "dialog_finish_branch_audit.md"
)
MAPPER_PATH = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"

EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
NATIVE_METHODS = {
    "DialogTree.ImportFromJson": {
        "token": "0x06003a7f",
        "va": 0x1872A946C,
        "bytes": 144,
        "sha256": "0e2c39227f5f81f5d96e8ef8d04984540f1deb5d773963191d5e0d0dc751498b",
        "contract": "passes the authored JSON to NodeCanvas Graph.Deserialize",
    },
    "NodeCanvas.Graph.Deserialize": {
        "token": "0x060010c3",
        "va": 0x183114AB0,
        "bytes": 1040,
        "sha256": "6625564e124290623f307e03d2edb7dd01b59a1dc5eb410e5e82bf3d25ee2e44",
        "contract": (
            "uses JSONSerializer.TryDeserializeOverwrite for the graph source"
        ),
    },
    "JSONSerializer.TryDeserializeOverwrite<System.Object>": {
        "token": "0x06001756",
        "va": 0x183113B60,
        "bytes": 256,
        "sha256": "38cb9f2978747c9c5206efb4147e0389cd0cc7f3290eeb128681937b4ea67a72",
        "contract": "passes an existing instance to FullSerializer deserialization",
    },
    "fsReflectedConverter.TryDeserialize": {
        "token": "0x060018bf",
        "va": 0x18360DA00,
        "bytes": 880,
        "sha256": "81afac7887a0533e9faf9ecf3c2b3d39af42625fc061192cfea76aa9ee3db572",
        "contract": (
            "sets a reflected field only after its JSON-name lookup succeeds; "
            "an absent field is left at its initialized managed value"
        ),
    },
    "fsMetaType.CreateInstance": {
        "token": "0x0600183e",
        "va": 0x183604F50,
        "bytes": 128,
        "sha256": "dee02a026414a74bd96d292a6a825a224da0642717e5d425b72a16deb6223a2c",
        "contract": (
            "creates reflected objects through FormatterServices."
            "GetSafeUninitializedObject, whose managed value-type fields start "
            "at their zero/default value"
        ),
    },
    "DialogTreeFinishNode.DoExecute": {
        "token": "0x06003b86",
        "va": 0x1872A4F80,
        "bytes": 128,
        "sha256": "8545a30e2e0b2903e11dd70b7db6bc640e79c9f3fbcfb8db9e856dd76d2a3721",
        "contract": (
            "passes the serialized finishId and finish type to "
            "DialogManager.FinishDialog"
        ),
    },
    "DialogManager.FinishDialog": {
        "token": "0x0600f78b",
        "va": 0x186E0F2D4,
        "bytes": 256,
        "sha256": "616928bc9e48dd51b66b0485dbf40881b6aa1dd80a926e11d9f208e5be4d4546",
        "contract": "records the supplied finishId before exiting the dialog",
    },
    "CheckTalkOptionFinish.Check": {
        "token": "0x06004634",
        "va": 0x187345808,
        "bytes": 128,
        "sha256": "ff7a6b72974c083a797dabd17c0012362b8cb374bd0e92ef0b17196f90ed26be",
        "contract": (
            "accepts any recorded finish for a negative operand and requires "
            "exact dialogFinishInfos membership for a nonnegative operand"
        ),
    },
}


class AuditValidationError(RuntimeError):
    """Fail-closed audit error with a stable, actionable diagnostic."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return path.resolve().as_posix()


def resolve_source(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def _load_mapper() -> Any:
    spec = importlib.util.spec_from_file_location("dialog_finish_pe_mapper", MAPPER_PATH)
    if spec is None or spec.loader is None:
        raise AuditValidationError(
            "validator=dialog_finish_native_contract gate=mapperLoad "
            f"expected=loadable actual=missing source={source_label(MAPPER_PATH)}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_native_contract(
    game_assembly: Path = DEFAULT_GAME_ASSEMBLY,
    metadata: Path = DEFAULT_METADATA,
) -> dict[str, Any]:
    validator = "dialog_finish_native_contract"
    for label, path, expected in (
        ("GameAssembly.dll", game_assembly, EXPECTED_GAME_ASSEMBLY_SHA256),
        ("global-metadata.dat", metadata, EXPECTED_METADATA_SHA256),
    ):
        if not path.is_file():
            raise AuditValidationError(
                f"validator={validator} gate=sourceExists expected=file "
                f"actual=missing source={path}"
            )
        actual = sha256_file(path)
        if actual != expected:
            raise AuditValidationError(
                f"validator={validator} gate=sourceSha256 source={path} "
                f"expected={expected} actual={actual}"
            )
    mapper = _load_mapper()
    pe = mapper.PeImage(game_assembly)
    methods: list[dict[str, Any]] = []
    for symbol, expected in NATIVE_METHODS.items():
        body = pe.bytes_at_va(expected["va"], expected["bytes"])
        actual = hashlib.sha256(body).hexdigest()
        if actual != expected["sha256"]:
            raise AuditValidationError(
                f"validator={validator} gate=methodBodySha256 symbol={symbol} "
                f"source={game_assembly} expected={expected['sha256']} actual={actual}"
            )
        methods.append(
            {
                "symbol": symbol,
                "token": expected["token"],
                "address": f"0x{expected['va']:x}",
                "byteCount": expected["bytes"],
                "bodySha256": actual,
                "contract": expected["contract"],
            }
        )
    return {
        "status": "validated",
        "validator": validator,
        "gameAssembly": {
            "sourceFile": source_label(game_assembly),
            "sha256": EXPECTED_GAME_ASSEMBLY_SHA256,
        },
        "globalMetadata": {
            "sourceFile": source_label(metadata),
            "sha256": EXPECTED_METADATA_SHA256,
        },
        "methods": methods,
        "serializedFieldDefaults": {
            "status": "validated",
            "scope": "FullSerializer reflected fields omitted from authored JSON",
            "initialization": "FormatterServices.GetSafeUninitializedObject",
            "assignmentGate": "JSON-name dictionary lookup must succeed",
            "managedValueTypeDefaults": {"System.Int32": 0},
            "evidenceMethods": [
                "DialogTree.ImportFromJson",
                "NodeCanvas.Graph.Deserialize",
                "JSONSerializer.TryDeserializeOverwrite<System.Object>",
                "fsReflectedConverter.TryDeserialize",
                "fsMetaType.CreateInstance",
            ],
        },
        "evidenceBoundary": (
            "The installed client proves how finish numbers are produced and "
            "tested. It does not reveal which option a player selected, which "
            "successor the server started, or a total Story-file chronology."
        ),
    }


def _short_type(value: Any) -> str:
    text = str(value or "").split(",", 1)[0]
    return text.rsplit(".", 1)[-1]


def resolve_serialized_field(
    record: dict[str, Any],
    field_name: str,
    managed_type: str,
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[Any | None, str]:
    """Resolve one authored field without inventing object-specific defaults.

    Explicit values always win.  An omitted field is admitted only when the
    installed-runtime contract validated the general FullSerializer reflected
    field behavior and declared the managed value type's default.
    """
    if field_name in record:
        value = record[field_name]
        if managed_type == "System.Int32" and type(value) is int:
            return value, "serialized_explicit"
        return None, "invalid_serialized_value"
    defaults = runtime_defaults or {}
    values = defaults.get("managedValueTypeDefaults") or {}
    if defaults.get("status") == "validated" and managed_type in values:
        value = values[managed_type]
        if managed_type == "System.Int32" and type(value) is int:
            return value, "runtime_default"
    return None, "missing_without_validated_default"


def decode_dialog_tree_finish_routes(
    outer: Any,
    *,
    source_file: str,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Decode exact option-to-finish routes, rejecting ambiguous node shapes.

    Connection order is used only because the installed ``SelectIndex`` path
    indexes the option list and the outgoing connection list positionally.
    """
    rejected: list[dict[str, Any]] = []
    if not isinstance(outer, dict) or not isinstance(outer.get("m_Script"), str):
        return [], [{"sourceFile": source_file, "gate": "textAssetScript"}]
    try:
        payload = json.loads(
            base64.b64decode(outer["m_Script"], validate=True).decode("utf-8-sig")
        )
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return [], [{"sourceFile": source_file, "gate": "dialogTreeDecode"}]
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "Beyond.Gameplay.DialogTree"
        or not isinstance(payload.get("nodes"), list)
        or not isinstance(payload.get("connections"), list)
    ):
        return [], [{"sourceFile": source_file, "gate": "dialogTreeSchema"}]
    dialog_id = str(outer.get("m_Name") or outer.get("Name") or "").strip()
    if not dialog_id:
        return [], [{"sourceFile": source_file, "gate": "dialogIdentity"}]

    nodes: dict[str, dict[str, Any]] = {}
    for node in payload["nodes"]:
        if not isinstance(node, dict):
            return [], [{"sourceFile": source_file, "gate": "nodeShape"}]
        node_id = str(node.get("$id") or "")
        if not node_id:
            continue
        if node_id in nodes:
            return [], [{"sourceFile": source_file, "gate": "uniqueNodeId", "nodeId": node_id}]
        nodes[node_id] = node

    targets: dict[str, list[str]] = defaultdict(list)
    for connection in payload["connections"]:
        if not isinstance(connection, dict) or _short_type(connection.get("$type")) != "DialogTreeConnection":
            return [], [{"sourceFile": source_file, "gate": "connectionShape"}]
        source_id = str(((connection.get("_sourceNode") or {}).get("$ref")) or "")
        target_id = str(((connection.get("_targetNode") or {}).get("$ref")) or "")
        if source_id not in nodes or target_id not in nodes:
            return [], [{"sourceFile": source_file, "gate": "connectionReference"}]
        targets[source_id].append(target_id)

    rows: list[dict[str, Any]] = []
    for node_id, node in nodes.items():
        if _short_type(node.get("$type")) != "DialogTreeOptionNode":
            continue
        option_rows = node.get("_normalOptions") or []
        if not isinstance(option_rows, list):
            rejected.append({"sourceFile": source_file, "gate": "optionList", "nodeId": node_id})
            continue
        option_ids = [
            str(row.get("_optionId") or "").strip()
            for row in option_rows
            if isinstance(row, dict)
        ]
        if (
            len(option_ids) != len(option_rows)
            or not option_ids
            or any(not value for value in option_ids)
            or len(set(option_ids)) != len(option_ids)
        ):
            rejected.append({"sourceFile": source_file, "gate": "uniqueOptionIds", "nodeId": node_id})
            continue
        outgoing = targets.get(node_id, [])
        if len(outgoing) != len(option_ids):
            rejected.append(
                {
                    "sourceFile": source_file,
                    "gate": "positionalOptionConnections",
                    "nodeId": node_id,
                    "expected": len(option_ids),
                    "actual": len(outgoing),
                }
            )
            continue
        for option_ordinal, (option_id, start_id) in enumerate(
            zip(option_ids, outgoing, strict=True)
        ):
            seen: set[str] = set()
            current_id = start_id
            while current_id not in seen:
                seen.add(current_id)
                current = nodes[current_id]
                current_type = _short_type(current.get("$type"))
                if current_type == "DialogTreeFinishNode":
                    finish_id, finish_id_source = resolve_serialized_field(
                        current,
                        "finishId",
                        "System.Int32",
                        runtime_defaults=runtime_defaults,
                    )
                    if finish_id_source in {
                        "invalid_serialized_value",
                        "missing_without_validated_default",
                    }:
                        rejected.append(
                            {
                                "sourceFile": source_file,
                                "gate": "serializedFinishId",
                                "nodeId": current_id,
                                "optionId": option_id,
                                "actual": finish_id_source,
                            }
                        )
                    else:
                        rows.append(
                            {
                                "dialogId": dialog_id,
                                "optionId": option_id,
                                "finishId": finish_id,
                                "finishIdSource": finish_id_source,
                                "producerFamily": "dialog_tree_finish_node",
                                "optionNodeId": node_id,
                                "optionOrdinal": option_ordinal,
                                "producerScope": {
                                    "kind": "dialog_tree_option_node",
                                    "key": f"node:{node_id}:option:{option_ordinal}",
                                    "optionNodeId": node_id,
                                    "optionOrdinal": option_ordinal,
                                },
                                "finishNodeId": current_id,
                                "sourceFiles": [
                                    {
                                        "kind": "dialog_tree_text_asset",
                                        "sourceFile": source_file,
                                        "relationship": "exact_option_to_finish_route",
                                    }
                                ],
                            }
                        )
                    break
                if current_type != "DialogTransitionNode":
                    break
                next_ids = targets.get(current_id, [])
                if len(next_ids) != 1:
                    rejected.append(
                        {
                            "sourceFile": source_file,
                            "gate": "linearTransitionRoute",
                            "nodeId": current_id,
                            "optionId": option_id,
                            "actual": len(next_ids),
                        }
                    )
                    break
                current_id = next_ids[0]
    return rows, rejected


def decode_timeline_finish_routes(
    payload: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Decode every explicit Timeline option finish-number replacement."""
    if not isinstance(payload, dict):
        return [], [{"gate": "timelineOrderRoot", "expected": "object", "actual": type(payload).__name__}]
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for dialog_id, timeline in payload.items():
        if dialog_id == "_meta" or not isinstance(timeline, dict):
            continue
        declared_dialog = str(timeline.get("dialogKey") or "")
        if declared_dialog != dialog_id:
            rejected.append(
                {
                    "gate": "timelineDialogIdentity",
                    "dialogId": dialog_id,
                    "expected": dialog_id,
                    "actual": declared_dialog,
                }
            )
            continue
        roots = [str(value) for value in timeline.get("sourceRoots") or [] if str(value)]
        for option in timeline.get("options") or []:
            if not isinstance(option, dict) or option.get("changeFinishNum") != 1:
                continue
            option_id = str(option.get("id") or "").strip()
            finish_id = option.get("targetFinishNum")
            if not option_id or not isinstance(finish_id, int) or finish_id < 0:
                rejected.append(
                    {
                        "gate": "timelineExplicitFinish",
                        "dialogId": dialog_id,
                        "optionId": option_id,
                        "actual": finish_id,
                    }
                )
                continue
            files = [
                {
                    "kind": "timeline_option_playable",
                    "sourceFile": str(option.get("assetTrack") or option.get("track") or ""),
                    "relationship": "exact_option_finish_number_override",
                }
            ]
            files.extend(
                {
                    "kind": "timeline_root",
                    "sourceFile": root,
                    "relationship": "exact_timeline_container",
                }
                for root in roots
            )
            candidates.append(
                {
                    "dialogId": dialog_id,
                    "optionId": option_id,
                    "finishId": finish_id,
                    "finishIdSource": "serialized_explicit",
                    "producerFamily": "timeline_option_finish_override",
                    "timeline": str(timeline.get("timeline") or ""),
                    "optionIndex": option.get("optionIndex"),
                    "producerScope": {
                        "kind": "timeline_option_group",
                        "key": (
                            f"timeline:{timeline.get('timeline') or ''}:"
                            f"group:{option.get('groupKey')}:"
                            f"option:{option.get('optionIndex')}"
                        ),
                        "timeline": str(timeline.get("timeline") or ""),
                        "groupKey": option.get("groupKey"),
                        "optionIndex": option.get("optionIndex"),
                    },
                    "sourceFiles": [row for row in files if row["sourceFile"]],
                }
            )

    # Repeated clips are common.  They are safe only when every copy of the
    # same authored option agrees on one finish number.
    by_scope: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_scope[(row["dialogId"], row["producerScope"]["key"])].append(row)
    rows: list[dict[str, Any]] = []
    for (dialog_id, scope_key), group in sorted(by_scope.items()):
        finish_ids = {row["finishId"] for row in group}
        option_ids = {row["optionId"] for row in group}
        if len(finish_ids) != 1 or len(option_ids) != 1:
            rejected.append(
                {
                    "gate": "timelineOptionScopeAgreement",
                    "dialogId": dialog_id,
                    "producerScope": scope_key,
                    "optionIds": sorted(option_ids),
                    "finishIds": sorted(finish_ids),
                }
            )
            continue
        merged = dict(group[0])
        merged["sourceFiles"] = _dedupe_source_rows(
            source for row in group for source in row["sourceFiles"]
        )
        merged["serializedOccurrenceCount"] = len(group)
        rows.append(merged)
    return rows, rejected


def _dedupe_source_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        identity = (
            str(row.get("kind") or ""),
            str(row.get("sourceFile") or ""),
            str(row.get("relationship") or ""),
        )
        if not identity[1] or identity in seen:
            continue
        seen.add(identity)
        output.append(dict(row))
    return output


def _hash_source_rows(
    rows: Iterable[dict[str, Any]],
    cache: dict[Path, str],
    *,
    validator: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in _dedupe_source_rows(rows):
        path = resolve_source(str(row["sourceFile"]))
        if not path.is_file():
            raise AuditValidationError(
                f"validator={validator} gate=relatedOriginalFile expected=file "
                f"actual=missing source={path}"
            )
        if path not in cache:
            cache[path] = sha256_file(path)
        output.append({**row, "sourceFile": source_label(path), "sha256": cache[path]})
    return output


def _collect_mission_consumers(
    index: dict[str, Any],
    pipeline_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    consumers: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        mission_path = pipeline_root / str(summary.get("file") or "")
        if not mission_id or not mission_path.is_file():
            continue
        payload = read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        payloads[mission_id] = payload
        mission_source = str((payload.get("mission") or {}).get("source") or "")
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            quest_id = str(node.get("id") or "")
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                for finish in objective.get("dialogFinishes") or []:
                    if not isinstance(finish, dict):
                        continue
                    dialog_id = str(finish.get("dialogId") or "")
                    finish_id = finish.get("finishId")
                    if dialog_id and isinstance(finish_id, int) and finish_id >= 0:
                        consumers.append(
                            {
                                "missionId": mission_id,
                                "questId": quest_id,
                                "objectiveIndex": objective.get("index"),
                                "conditionId": str(objective.get("conditionId") or ""),
                                "dialogId": dialog_id,
                                "finishId": finish_id,
                                "missionSource": mission_source,
                            }
                        )
    return consumers, payloads


def _collect_dialog_tree_producers(
    payloads: dict[str, dict[str, Any]],
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_files = sorted(
        {
            str(definition.get("sourceFile") or "")
            for payload in payloads.values()
            for node in payload.get("nodes") or []
            if isinstance(node, dict)
            for definition in node.get("dialogTreeDefinitions") or []
            if isinstance(definition, dict) and definition.get("sourceFile")
        }
    )
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for source_file in source_files:
        path = resolve_source(source_file)
        if not path.is_file():
            raise AuditValidationError(
                "validator=dialog_finish_branch_recovery gate=dialogTreeSource "
                f"expected=file actual=missing source={path}"
            )
        decoded, failures = decode_dialog_tree_finish_routes(
            read_json(path),
            source_file=source_label(path),
            runtime_defaults=runtime_defaults,
        )
        rows.extend(decoded)
        rejected.extend(failures)
    return rows, rejected


def _normalize_producers(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize only within an original runtime branch scope.

    Localization option IDs can be reused by distinct option nodes.  The
    serialized current node/option slot is the runtime identity, so agreement
    is required within that scope rather than globally by display-text ID.
    """
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        scope = row.get("producerScope") or {}
        grouped[(row["dialogId"], str(scope.get("kind") or ""), str(scope.get("key") or ""))].append(row)
    accepted: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for (dialog_id, scope_kind, scope_key), group in sorted(grouped.items()):
        finish_ids = {row["finishId"] for row in group}
        option_ids = {row["optionId"] for row in group}
        if not scope_kind or not scope_key or len(finish_ids) != 1 or len(option_ids) != 1:
            conflicts.append(
                {
                    "gate": "producerScopeAgreement",
                    "dialogId": dialog_id,
                    "producerScope": {"kind": scope_kind, "key": scope_key},
                    "optionIds": sorted(option_ids),
                    "finishIds": sorted(finish_ids),
                    "producerFamilies": sorted({row["producerFamily"] for row in group}),
                }
            )
            continue
        by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in group:
            by_family[row["producerFamily"]].append(row)
        merged = dict(group[0])
        merged["producerFamilies"] = sorted(by_family)
        merged["finishIdSources"] = sorted(
            {str(row.get("finishIdSource") or "unknown") for row in group}
        )
        merged.pop("producerFamily", None)
        merged.pop("finishIdSource", None)
        merged["sourceFiles"] = _dedupe_source_rows(
            source for row in group for source in row.get("sourceFiles") or []
        )
        accepted.append(merged)
    return accepted, conflicts


def _collect_reused_option_scopes(
    rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Report localization IDs reused by distinct structural branch scopes."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["dialogId"], row["optionId"])].append(row)
    output: list[dict[str, Any]] = []
    for (dialog_id, option_id), group in sorted(grouped.items()):
        scopes = {
            (str((row.get("producerScope") or {}).get("kind") or ""),
             str((row.get("producerScope") or {}).get("key") or ""))
            for row in group
        }
        if len(scopes) <= 1:
            continue
        output.append(
            {
                "dialogId": dialog_id,
                "optionId": option_id,
                "finishIds": sorted({row["finishId"] for row in group}),
                "producerScopes": [row["producerScope"] for row in group],
                "interpretation": (
                    "The localization option ID is reused by distinct original "
                    "runtime branch scopes; it is not a global branch identity."
                ),
            }
        )
    return output


def build_report(
    index: dict[str, Any],
    pipeline_root: Path = DEFAULT_PIPELINE_ROOT,
    timeline_orders_path: Path = DEFAULT_TIMELINE_ORDERS,
    *,
    native_contract: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    validator = "dialog_finish_branch_recovery"
    native_contract = native_contract or validate_native_contract()
    consumers, payloads = _collect_mission_consumers(index, pipeline_root)
    runtime_defaults = native_contract.get("serializedFieldDefaults") or {}
    tree_rows, tree_rejected = _collect_dialog_tree_producers(
        payloads, runtime_defaults=runtime_defaults
    )
    timeline_payload = read_json(timeline_orders_path) if timeline_orders_path.is_file() else {}
    timeline_rows, timeline_rejected = decode_timeline_finish_routes(timeline_payload)
    producers, conflicts = _normalize_producers([*tree_rows, *timeline_rows])
    reused_option_scopes = _collect_reused_option_scopes(producers)
    producers_by_finish: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for producer in producers:
        producers_by_finish[(producer["dialogId"], producer["finishId"])].append(producer)

    hash_cache: dict[Path, str] = {}
    binary_files = [
        {
            "kind": "game_binary",
            "sourceFile": native_contract["gameAssembly"]["sourceFile"],
            "relationship": "runtime_finish_producer_and_consumer_contract",
        },
        {
            "kind": "il2cpp_metadata",
            "sourceFile": native_contract["globalMetadata"]["sourceFile"],
            "relationship": "typed_runtime_method_and_field_identity",
        },
    ]
    dependencies: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for consumer in consumers:
        matches = producers_by_finish.get((consumer["dialogId"], consumer["finishId"]), [])
        if not matches:
            unresolved.append(consumer)
            continue
        options = sorted({row["optionId"] for row in matches})
        source_rows = [
            source for row in matches for source in row.get("sourceFiles") or []
        ]
        if consumer["missionSource"]:
            source_rows.append(
                {
                    "kind": "mission_runtime",
                    "sourceFile": consumer["missionSource"],
                    "relationship": "exact_finish_condition_consumer",
                }
            )
        source_rows.extend(binary_files)
        dependencies.append(
            {
                **consumer,
                "classification": (
                    "unique_option_outcome_dependency"
                    if len(options) == 1
                    else "option_outcome_set_dependency"
                ),
                "optionIds": options,
                "producerFamilies": sorted(
                    {family for row in matches for family in row["producerFamilies"]}
                ),
                "producerEvidence": matches,
                "relatedOriginalFiles": _hash_source_rows(
                    source_rows, hash_cache, validator=validator
                ),
                "evidenceBoundary": (
                    "The authored option outcome produces the exact finish number "
                    "required by this quest objective. This is a causal branch "
                    "dependency, not proof of player selection, dialog activation, "
                    "server successor choice, or total Story-file order."
                ),
            }
        )

    dependencies.sort(
        key=lambda row: (
            row["missionId"], row["questId"], row["objectiveIndex"] or 0,
            row["dialogId"], row["finishId"], row["optionIds"],
        )
    )
    report = {
        "schemaVersion": "dialogFinishMissionBranchAudit.v2",
        "status": "validated",
        "validator": validator,
        "evidencePolicy": (
            "Only exact nonnegative dialog finish IDs shared by an original "
            "DialogTree/Timeline option producer and MissionRuntime objective are "
            "admitted. An omitted DialogTree Int32 is admitted as zero only under "
            "the hash-locked FullSerializer reflected-field default contract. OCR "
            "and manual overrides are not read."
        ),
        "nativeContract": native_contract,
        "sources": {
            "timelineOrders": source_label(timeline_orders_path),
            "pipelineIndex": source_label(pipeline_root / "index.json"),
        },
        "counts": {
            "exactMissionConsumers": len(consumers),
            "dialogTreeProducerRows": len(tree_rows),
            "dialogTreeExplicitFinishRows": sum(
                row.get("finishIdSource") == "serialized_explicit" for row in tree_rows
            ),
            "dialogTreeRuntimeDefaultFinishRows": sum(
                row.get("finishIdSource") == "runtime_default" for row in tree_rows
            ),
            "timelineProducerRows": len(timeline_rows),
            "acceptedOptionProducers": len(producers),
            "publishedDependencies": len(dependencies),
            "uniqueOptionDependencies": sum(
                row["classification"] == "unique_option_outcome_dependency"
                for row in dependencies
            ),
            "missions": len({row["missionId"] for row in dependencies}),
            "quests": len({row["questId"] for row in dependencies}),
            "unresolvedExactConsumers": len(unresolved),
            "rejectedProducerShapes": len(tree_rejected) + len(timeline_rejected),
            "conflictingOptionProducers": len(conflicts),
            "reusedOptionIdsAcrossScopes": len(reused_option_scopes),
        },
        "producerFamilyCounts": dict(
            sorted(Counter(family for row in producers for family in row["producerFamilies"]).items())
        ),
        "dependencies": dependencies,
        "unresolvedExactConsumers": unresolved,
        "rejectedProducerShapes": [*tree_rejected, *timeline_rejected],
        "conflictingOptionProducers": conflicts,
        "reusedOptionIdsAcrossScopes": reused_option_scopes,
    }
    return report, payloads


def publish_to_pipeline_index(
    index: dict[str, Any],
    report: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    pipeline_root: Path = DEFAULT_PIPELINE_ROOT,
) -> int:
    by_quest: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in report.get("dependencies") or []:
        by_quest[(row["missionId"], row["questId"])].append(row)
    published = 0
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        payload = payloads.get(mission_id)
        if not payload:
            continue
        mission_rows: list[dict[str, Any]] = []
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node.pop("dialogFinishBranchDependencies", None)
            rows = by_quest.get((mission_id, str(node.get("id") or "")), [])
            if not rows:
                continue
            node["dialogFinishBranchDependencies"] = rows
            mission_rows.extend(rows)
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                objective_rows = [
                    row for row in rows
                    if row.get("objectiveIndex") == objective.get("index")
                    and row.get("conditionId") == str(objective.get("conditionId") or "")
                ]
                if objective_rows:
                    objective["dialogFinishBranchDependencies"] = objective_rows
                else:
                    objective.pop("dialogFinishBranchDependencies", None)
        payload["dialogFinishBranchRecovery"] = {
            "schema": report.get("schemaVersion"),
            "status": report.get("status"),
            "dependencyCount": len(mission_rows),
            "evidenceBoundary": report.get("evidencePolicy"),
        }
        summary["dialogFinishBranchDependencyCount"] = len(mission_rows)
        write_json(pipeline_root / str(summary.get("file") or ""), payload)
        published += len(mission_rows)
    index["dialogFinishBranchRecovery"] = {
        "schema": report.get("schemaVersion"),
        "status": report.get("status"),
        "counts": report.get("counts"),
        "producerFamilyCounts": report.get("producerFamilyCounts"),
        "nativeContract": report.get("nativeContract"),
        "reportJson": source_label(DEFAULT_JSON),
        "reportMarkdown": source_label(DEFAULT_MARKDOWN),
    }
    index.setdefault("counts", {})["dialogFinishBranchDependencies"] = published
    return published


def markdown_report(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    lines = [
        "# Dialog finish mission-branch audit",
        "",
        f"Status: `{report.get('status')}`",
        "",
        str(report.get("evidencePolicy") or ""),
        "",
        "## Coverage",
        "",
        f"- Exact MissionRuntime consumers: {counts.get('exactMissionConsumers', 0)}",
        f"- Accepted option producers: {counts.get('acceptedOptionProducers', 0)}",
        f"- DialogTree explicit / runtime-default finish rows: {counts.get('dialogTreeExplicitFinishRows', 0)} / {counts.get('dialogTreeRuntimeDefaultFinishRows', 0)}",
        f"- Published dependencies: {counts.get('publishedDependencies', 0)}",
        f"- Missions / quests: {counts.get('missions', 0)} / {counts.get('quests', 0)}",
        f"- Unresolved exact consumers: {counts.get('unresolvedExactConsumers', 0)}",
        f"- Rejected / conflicting producer shapes: {counts.get('rejectedProducerShapes', 0)} / {counts.get('conflictingOptionProducers', 0)}",
        f"- Localization option IDs reused across runtime scopes: {counts.get('reusedOptionIdsAcrossScopes', 0)}",
        "",
        "## Recovered dependencies",
        "",
        "| Mission | Quest | Dialog finish | Authored option outcome | Producer | Value source |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.get("dependencies") or []:
        lines.append(
            f"| `{row['missionId']}` | `{row['questId']}` | "
            f"`{row['dialogId']}` / `{row['finishId']}` | "
            f"{', '.join(f'`{value}`' for value in row['optionIds'])} | "
            f"{', '.join(f'`{value}`' for value in row['producerFamilies'])} | "
            f"{', '.join(f'`{value}`' for value in sorted({source for producer in row.get('producerEvidence') or [] for source in producer.get('finishIdSources') or []}))} |"
        )
    lines.extend(["", "## Reused localization IDs", ""])
    reused = report.get("reusedOptionIdsAcrossScopes") or []
    if reused:
        for row in reused:
            scopes = ", ".join(
                f"`{scope.get('kind')}:{scope.get('key')}`"
                for scope in row.get("producerScopes") or []
            )
            lines.append(
                f"- `{row['dialogId']}` / `{row['optionId']}` produces finishes "
                f"{', '.join(f'`{value}`' for value in row['finishIds'])} in {scopes}."
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            str((report.get("nativeContract") or {}).get("evidenceBoundary") or ""),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline-root", type=Path, default=DEFAULT_PIPELINE_ROOT)
    parser.add_argument("--timeline-orders", type=Path, default=DEFAULT_TIMELINE_ORDERS)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    index_path = args.pipeline_root / "index.json"
    index = read_json(index_path)
    native = validate_native_contract(args.game_assembly, args.metadata)
    report, payloads = build_report(
        index,
        args.pipeline_root,
        args.timeline_orders,
        native_contract=native,
    )
    write_json(args.json, report)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    if args.publish:
        publish_to_pipeline_index(index, report, payloads, args.pipeline_root)
        write_json(index_path, index)
    print(
        "dialog finish branch audit: "
        f"{report['counts']['publishedDependencies']} dependencies, "
        f"{report['counts']['missions']} missions, "
        f"{report['counts']['unresolvedExactConsumers']} unresolved exact consumers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
