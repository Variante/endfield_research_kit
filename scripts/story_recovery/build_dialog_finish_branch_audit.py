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

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.story_builder.dialog_tree_option_routes import (
    DIALOG_TREE_RUNTIME_DEFAULTS,
    recover_dialog_tree_option_routes,
    resolve_serialized_field,
    short_type as _short_type,
)
from scripts.story_builder.dialog_tree_finish_endpoints import (
    recover_dialog_tree_finish_endpoints,
)
from scripts.story_builder.levelscript_binary import (
    decode_levelscript_task_conditions,
    scan_levelscript_task_condition_fragments,
)


ROOT = _REPO_ROOT
DEFAULT_PIPELINE_ROOT = ROOT / "webui" / "data" / "mission_pipeline"
DEFAULT_TIMELINE_ORDERS = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "timeline_line_orders.json"
)
DEFAULT_DIALOG_TREE_ROOT = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "TextAsset"
)
DEFAULT_LEVELSCRIPT_ROOTS = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "LevelScriptData",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "LevelScriptData",
)
DEFAULT_SUBGAME_TABLE = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "GameplayConfig"
    / "SubGameInstanceDataTable.json"
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
EXPECTED_METADATA_REGISTRATION = 0x18B921C30
EXPECTED_RUNTIME_FIELD_OFFSETS = {
    "Beyond.Gameplay.DialogTreeOptionBase": {
        "<doNext>k__BackingField": 0x54,
    },
    "Beyond.Gameplay.NormalOptionData": {
        "main": 0x70,
        "index": 0x80,
    },
    "Beyond.Gameplay.DialogTreeOptionNode": {
        "_normalOptions": 0xA0,
        "_hasExOption": 0xA8,
    },
}
NATIVE_METHODS = {
    "DialogTree.ImportFromJson": {
        "token": "0x06003a7f",
        "va": 0x1872A946C,
        "bytes": 144,
        "sha256": "0e2c39227f5f81f5d96e8ef8d04984540f1deb5d773963191d5e0d0dc751498b",
        "contract": "passes the authored JSON to NodeCanvas Graph.Deserialize",
    },
    "NodeCanvas.Framework.Graph.get_primeNode": {
        "token": "0x06001109",
        "va": 0x18306D980,
        "bytes": 112,
        "sha256": "327d2c5ab57cf630fa0dd3e72ffc9596fa2761f97a6d02b5b62b099a5d4af85e",
        "contract": "returns allNodes[0] when the serialized node list is nonempty",
    },
    "DialogTree.OnGraphStarted": {
        "token": "0x06003a77",
        "va": 0x1872A969C,
        "bytes": 352,
        "sha256": "833998a346f36ea53a4d79c5e123b0e02905e5d376ec15db527c73ed5d389592",
        "contract": (
            "uses Graph.primeNode when no current node exists and tail-enters "
            "that exact node through DialogTree.EnterNode"
        ),
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
    "DialogTreeOptionNode.get_maxOutConnections": {
        "token": "0x06003b8f",
        "va": 0x1872A721C,
        "bytes": 80,
        "sha256": "b5cba6675adf30a99f4751b3b00bfeb7a4bbf86d4830b1037e663a26c4cd846c",
        "contract": (
            "returns ten rather than the normal-option count, so unequal "
            "option/connection counts are an allowed serialized shape"
        ),
    },
    "DialogTreeOptionNode.get_exOptionIndex": {
        "token": "0x06003b90",
        "va": 0x1872A70A4,
        "bytes": 220,
        "sha256": "059f36a29c0cff656135384abcf5fcfd8f22db2935f30f84ef3338f5dd9998ef",
        "contract": (
            "scans the physical outgoing connection list and returns the "
            "first target whose runtime node type is DialogTreeExOptionNode"
        ),
    },
    "DialogTreeOptionNode.GetNextIndex": {
        "token": "0x06003b98",
        "va": 0x1872A6B7C,
        "bytes": 120,
        "sha256": "470f865abaa215a04d82fdcc4faf8a5b4972bec7215c00d80fab85de6cd5f32a",
        "contract": (
            "shifts the default normal-option ordinal over an earlier "
            "DialogTreeExOptionNode connection"
        ),
    },
    "DialogTreeOptionBase..ctor": {
        "token": "0x06003a06",
        "va": 0x1872A6544,
        "bytes": 112,
        "sha256": "54f809b09e6662c82aff3d38f018de4dc8dac5c6a0e534c4ff83b92577b47dcb",
        "contract": (
            "initializes doNext true on constructed option data before runtime "
            "option display"
        ),
    },
    "DialogManager.ShowOptions": {
        "token": "0x0600f789",
        "va": 0x186E19790,
        "bytes": 1064,
        "sha256": "096e5a7226944be950d98ceac9efaa715f2f091f424def60091bc80a577ae119",
        "contract": (
            "writes DialogTreeOptionBase.doNext true while registering each "
            "normal option; the one false write belongs to the bounded "
            "auto-selected default path before SelectIndex"
        ),
    },
    "NormalOptionHandler.OnSelectWhenOptionEnd": {
        "token": "0x0600fa1e",
        "va": 0x186E512B0,
        "bytes": 176,
        "sha256": "10fac7b20f31417754dd81e2ec8955cc50ac369f9348e4a05e96cee675213416",
        "contract": (
            "checks DialogTreeOptionBase.doNext, then reads NormalOptionData.index "
            "at the MetadataRegistration-backed 0x80 field and passes it to "
            "DialogManager.SelectDialogTreeIndex"
        ),
    },
    "DialogManager.SelectDialogTreeIndex": {
        "token": "0x0600f7dc",
        "va": 0x186E18578,
        "bytes": 112,
        "sha256": "37976498f3a1ee76a34ee8134da4bc24cc8652e65eb040995e14002e992470b4",
        "contract": "passes the selected NormalOptionData.index unchanged to the controller",
    },
    "DialogTreeController.SelectIndex": {
        "token": "0x06003a9e",
        "va": 0x1872A2F9C,
        "bytes": 176,
        "sha256": "fe722e939949c4907f2362ff716a9d67ee76ad6995fb6fbf2fc36514a5484d3b",
        "contract": "calls currentNode.GetRealIndex and then DialogTree.Continue",
    },
    "DialogTreeNode.GetRealIndex": {
        "token": "0x06003b04",
        "va": 0x1872A56E0,
        "bytes": 88,
        "sha256": "ee0588ce28b0c7f7b261f1490213d2a56b0d0f2707c7bd4e1c6adc1259a989d5",
        "contract": "returns the supplied connection index unchanged on the native path",
    },
    "DialogTree.Continue": {
        "token": "0x06003a74",
        "va": 0x1872A8CE8,
        "bytes": 492,
        "sha256": "e26813edbe2614638bbd8039571b830460cec7e129bbccd9c0eb6d3a12e8bf99",
        "contract": (
            "bounds-checks the supplied index against outConnections.Count "
            "and enters exactly outConnections[index]"
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
    catalog_module = mapper.load_catalog_module()
    metadata_image = catalog_module.Metadata(metadata)
    registration = mapper.metadata_registration_summary(
        pe, EXPECTED_METADATA_REGISTRATION
    )
    offsets_table = int(registration["fieldOffsets"], 16)
    runtime_field_offsets: dict[str, dict[str, int]] = {}
    type_by_name = {
        metadata_image.type_full_name(type_def): type_def
        for type_def in metadata_image.types
    }
    for type_name, expected_offsets in EXPECTED_RUNTIME_FIELD_OFFSETS.items():
        type_def = type_by_name.get(type_name)
        if type_def is None:
            raise AuditValidationError(
                f"validator={validator} gate=runtimeFieldOwner "
                f"expected={type_name} actual=missing source={metadata}"
            )
        row_va = pe.u64_at_va(offsets_table + type_def.index * 8)
        if not row_va:
            raise AuditValidationError(
                f"validator={validator} gate=runtimeFieldOffsetRow "
                f"expected=nonzero actual=0 owner={type_name} source={game_assembly}"
            )
        actual_offsets = {
            metadata_image.string(field.name_index): pe.u32_at_va(
                row_va + ordinal * 4
            )
            for ordinal, field in enumerate(
                metadata_image.fields[
                    type_def.field_start : type_def.field_start + type_def.field_count
                ]
            )
        }
        selected = {
            field_name: actual_offsets.get(field_name)
            for field_name in expected_offsets
        }
        if selected != expected_offsets:
            raise AuditValidationError(
                f"validator={validator} gate=runtimeFieldOffsets owner={type_name} "
                f"expected={expected_offsets} actual={selected} "
                f"source={game_assembly}"
            )
        runtime_field_offsets[type_name] = selected

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
        "metadataRegistration": {
            "address": f"0x{EXPECTED_METADATA_REGISTRATION:x}",
            "fieldOffsets": runtime_field_offsets,
        },
        "serializedFieldDefaults": {
            "status": "validated",
            "scope": "FullSerializer reflected fields omitted from authored JSON",
            "initialization": "FormatterServices.GetSafeUninitializedObject",
            "assignmentGate": "JSON-name dictionary lookup must succeed",
            "managedValueTypeDefaults": {
                "System.Int32": 0,
                "System.Boolean": False,
            },
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


def decode_dialog_tree_finish_routes(
    outer: Any,
    *,
    source_file: str,
    runtime_defaults: dict[str, Any] | None = None,
    route_coverage: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Decode exact option-to-finish routes from authored physical indexes.

    The installed selection path passes ``NormalOptionData.index`` unchanged
    to ``DialogTree.Continue``. Option-list ordinal is never substituted for a
    missing, invalid, or out-of-bounds physical connection index.
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

    option_route_recovery = recover_dialog_tree_option_routes(
        payload["nodes"],
        payload["connections"],
        runtime_defaults=runtime_defaults,
    )
    if route_coverage is not None:
        route_coverage.update(
            {
                "schemaVersion": option_route_recovery.get("schemaVersion"),
                "sourceFile": source_file,
                "counts": option_route_recovery.get("counts") or {},
                "nodes": option_route_recovery.get("nodes") or [],
                "issues": option_route_recovery.get("issues") or [],
            }
        )

    rows: list[dict[str, Any]] = []
    for node_summary in option_route_recovery.get("nodes") or []:
        node_id = str(node_summary.get("nodeId") or "")
        node = nodes.get(node_id) or {}
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
        for route in node_summary.get("routes") or []:
            option_ordinal = route.get("optionOrdinal")
            option_id = str(route.get("optionId") or "")
            if route.get("status") != "validated":
                rejected.append(
                    {
                        "sourceFile": source_file,
                        "routingClass": node_summary.get("routingClass"),
                        "failureClass": route.get("failureClass"),
                        **(route.get("issue") or {}),
                    }
                )
                continue
            start_id = str(route.get("targetNodeId") or "")
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
                                "connectionIndex": route.get("connectionIndex"),
                                "connectionIndexSource": route.get(
                                    "connectionIndexSource"
                                ),
                                "producerScope": {
                                    "kind": "dialog_tree_option_node",
                                    "key": f"node:{node_id}:option:{option_ordinal}",
                                    "optionNodeId": node_id,
                                    "optionOrdinal": option_ordinal,
                                    "connectionIndex": route.get(
                                        "connectionIndex"
                                    ),
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


def decode_dialog_tree_finish_endpoints(
    outer: Any,
    *,
    source_file: str,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Decode exact prime-reachable finish endpoints from one TextAsset."""
    if not isinstance(outer, dict) or not isinstance(outer.get("m_Script"), str):
        failure = {"sourceFile": source_file, "gate": "textAssetScript"}
        return [], [failure], {}
    try:
        payload = json.loads(
            base64.b64decode(outer["m_Script"], validate=True).decode("utf-8-sig")
        )
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        failure = {"sourceFile": source_file, "gate": "dialogTreeDecode"}
        return [], [failure], {}
    if (
        not isinstance(payload, dict)
        or payload.get("type") != "Beyond.Gameplay.DialogTree"
        or not isinstance(payload.get("nodes"), list)
        or not isinstance(payload.get("connections"), list)
    ):
        failure = {"sourceFile": source_file, "gate": "dialogTreeSchema"}
        return [], [failure], {}
    dialog_id = str(outer.get("m_Name") or outer.get("Name") or "").strip()
    if not dialog_id:
        failure = {"sourceFile": source_file, "gate": "dialogIdentity"}
        return [], [failure], {}

    recovered = recover_dialog_tree_finish_endpoints(
        payload["nodes"],
        payload["connections"],
        runtime_defaults=runtime_defaults,
    )
    coverage = {
        "schemaVersion": recovered.get("schemaVersion"),
        "sourceFile": source_file,
        "primeNodeId": recovered.get("primeNodeId"),
        "counts": recovered.get("counts") or {},
        "endpoints": recovered.get("endpoints") or [],
        "issues": recovered.get("issues") or [],
    }
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for endpoint in recovered.get("endpoints") or []:
        if endpoint.get("status") != "validated":
            rejected.append(
                {
                    "sourceFile": source_file,
                    "nodeId": endpoint.get("nodeId"),
                    "nodeOrdinal": endpoint.get("nodeOrdinal"),
                    "failureClass": endpoint.get("failureClass"),
                    **(endpoint.get("issue") or {}),
                }
            )
            continue
        rows.append(
            {
                "dialogId": dialog_id,
                "finishId": endpoint.get("finishId"),
                "finishIdSource": endpoint.get("finishIdSource"),
                "producerFamily": "dialog_tree_prime_reachable_finish_endpoint",
                "finishNodeId": endpoint.get("nodeId"),
                "finishNodeOrdinal": endpoint.get("nodeOrdinal"),
                "primeNodeId": endpoint.get("primeNodeId"),
                "incomingConnectionCount": endpoint.get(
                    "incomingConnectionCount"
                ),
                "predecessorNodeIds": endpoint.get("predecessorNodeIds") or [],
                "predecessorNodeTypes": endpoint.get("predecessorNodeTypes") or [],
                "nodePath": endpoint.get("nodePath") or [],
                "connectionPath": endpoint.get("connectionPath") or [],
                "sourceFiles": [
                    {
                        "kind": "dialog_tree_text_asset",
                        "sourceFile": source_file,
                        "relationship": "exact_prime_reachable_finish_endpoint",
                    }
                ],
            }
        )
    return rows, rejected, coverage


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


def _validate_levelscript_task_contracts(
    index: dict[str, Any],
    native_contract: dict[str, Any],
) -> dict[str, Any]:
    """Validate the binary-derived task and SubGame activation contracts."""
    validator = "dialog_finish_levelscript_task_contract"
    runtime = index.get("runtimeContract") or {}
    task = runtime.get("levelScriptTaskAuthorityAudit") or {}
    task_shape = {
        "schema": task.get("schema"),
        "status": (task.get("validation") or {}).get("status"),
        "identityFields": task.get("identityFields"),
        "missionQuestIdentityFields": task.get("missionQuestIdentityFields"),
        "conditionResultToken": (
            (task.get("nativePaths") or {}).get("conditionResultChanged") or {}
        ).get("token"),
    }
    expected_task_shape = {
        "schema": "levelScriptTaskAuthority.v1",
        "status": "validated",
        "identityFields": ["sceneNumId", "scriptId", "taskId"],
        "missionQuestIdentityFields": [],
        "conditionResultToken": "0x060121fe",
    }
    if task_shape != expected_task_shape:
        raise AuditValidationError(
            f"validator={validator} gate=taskAuthorityShape "
            f"expected={expected_task_shape!r} actual={task_shape!r} "
            f"source={task.get('source') or 'mission_pipeline/index.json'}"
        )

    activation = runtime.get("levelScriptActivationControlAudit") or {}
    interaction = activation.get("subGameInteractionFlow") or {}
    methods = activation.get("methods") or {}
    activation_shape = {
        "schema": activation.get("schema"),
        "status": (activation.get("validation") or {}).get("status"),
        "subGameIdFieldRead": interaction.get("subGameIdFieldRead"),
        "bindScriptIdFieldRead": interaction.get("bindScriptIdFieldRead"),
        "callsInCarrierOrder": interaction.get("callsInCarrierOrder"),
        "manualStartCallCount": interaction.get("manualStartCallCount"),
        "challengeToken": (methods.get("ChallengeOnInteract") or {}).get("token"),
        "manualStartToken": (methods.get("ManualStart") or {}).get("token"),
    }
    expected_activation_shape = {
        "schema": "levelScriptActivationControl.v6",
        "status": "validated",
        "subGameIdFieldRead": True,
        "bindScriptIdFieldRead": True,
        "callsInCarrierOrder": True,
        "manualStartCallCount": 1,
        "challengeToken": "0x0600231a",
        "manualStartToken": "0x0601218f",
    }
    if activation_shape != expected_activation_shape:
        raise AuditValidationError(
            f"validator={validator} gate=subGameActivationShape "
            f"expected={expected_activation_shape!r} actual={activation_shape!r} "
            f"source={activation.get('source') or 'mission_pipeline/index.json'}"
        )

    expected_hashes = {
        str(native_contract["gameAssembly"]["sha256"]).lower(),
        str(native_contract["globalMetadata"]["sha256"]).lower(),
    }
    for label, contract in (("task", task), ("activation", activation)):
        actual_hashes = {
            str(row.get("sha256") or "").lower()
            for row in contract.get("relatedOriginalFiles") or []
            if isinstance(row, dict) and row.get("sha256")
        }
        if not expected_hashes <= actual_hashes:
            raise AuditValidationError(
                f"validator={validator} gate={label}BinaryHashAgreement "
                f"expected={sorted(expected_hashes)!r} "
                f"actual={sorted(actual_hashes)!r} "
                f"source={contract.get('source') or 'mission_pipeline/index.json'}"
            )
    return {
        "taskAuthority": {
            "schema": task["schema"],
            "source": task.get("source") or "",
            "identityFields": task["identityFields"],
            "missionQuestIdentityFields": [],
            "conditionResultChanged": (
                task.get("nativePaths") or {}
            ).get("conditionResultChanged") or {},
            "evidenceBoundary": task.get("evidenceBoundary") or "",
        },
        "subGameActivation": {
            "schema": activation["schema"],
            "source": activation.get("source") or "",
            "subGameInteractionFlow": interaction,
            "manualStart": methods.get("ManualStart") or {},
            "challengeOnInteract": methods.get("ChallengeOnInteract") or {},
            "evidenceBoundary": activation.get("evidenceBoundary") or "",
        },
    }


def _constant_param_value(param: Any, value_type: type) -> Any:
    """Return a constant MemoryPack Param value, or ``None`` when indirect."""
    if (
        not isinstance(param, dict)
        or param.get("idRef") != -1
        or param.get("paramSource") != 0
        or param.get("path") is not None
    ):
        return None
    value = param.get("value")
    if value_type is int and isinstance(value, bool):
        return None
    return value if isinstance(value, value_type) else None


def _levelscript_overlay(
    roots: Iterable[Path],
) -> tuple[list[tuple[str, str, Path]], dict[str, Any]]:
    """Resolve the installed serialized overlay without per-file choices.

    Roots are ordered from fallback to override.  The current export contract
    is StreamingAssets followed by Persistent, so the latter wins for an
    identical relative LevelScript identity.
    """
    validator = "dialog_finish_levelscript_task_census"
    active: dict[str, tuple[str, str, Path, str]] = {}
    physical_files = 0
    shadowed = 0
    changed_overrides = 0
    root_rows: list[dict[str, Any]] = []
    for priority, root in enumerate(roots):
        if not root.is_dir():
            raise AuditValidationError(
                f"validator={validator} gate=levelScriptRoot expected=directory "
                f"actual=missing source={root}"
            )
        root_count = 0
        for path in sorted(root.rglob("*.json")):
            try:
                int(path.stem)
            except ValueError:
                continue
            relative = path.relative_to(root).as_posix()
            digest = sha256_file(path)
            root_count += 1
            physical_files += 1
            previous = active.get(relative)
            if previous is not None:
                shadowed += 1
                changed_overrides += previous[3] != digest
            active[relative] = (path.parent.name, path.stem, path, digest)
        root_rows.append({
            "priority": priority,
            "sourceRoot": source_label(root),
            "fileCount": root_count,
        })
    rows = [
        (level_id, script_id, path)
        for level_id, script_id, path, _digest in active.values()
    ]
    rows.sort(key=lambda row: (row[0], int(row[1]), source_label(row[2])))
    return rows, {
        "roots": root_rows,
        "overlayRule": "later root wins; Persistent overrides StreamingAssets",
        "physicalFileCount": physical_files,
        "activeLogicalFileCount": len(rows),
        "shadowedPathCount": shadowed,
        "changedOverrideCount": changed_overrides,
    }


def _collect_levelscript_task_finish_consumers(
    roots: Iterable[Path] = DEFAULT_LEVELSCRIPT_ROOTS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Scan the active LevelScript corpus for exact finish consumers."""
    active_files, overlay = _levelscript_overlay(roots)
    rows: list[dict[str, Any]] = []
    complete_rows = 0
    fragment_rows = 0
    rejected_param_shapes = 0
    files_with_consumers: set[str] = set()
    for level_id, script_id, path in active_files:
        data = path.read_bytes()
        source_file = source_label(path)
        source_hash = hashlib.sha256(data).hexdigest()
        complete_signatures: set[tuple[str, int]] = set()
        candidates: list[tuple[str | None, dict[str, Any], dict[str, Any], str]] = []
        for host in decode_levelscript_task_conditions(data, script_id):
            for task in host.get("tasks") or []:
                for condition_row in task.get("conditions") or []:
                    condition = condition_row.get("condition") or {}
                    if condition.get("type") != "CheckTalkOptionFinish":
                        continue
                    signature = (
                        str(condition_row.get("conditionKey") or ""),
                        int(condition.get("conditionOffset") or -1),
                    )
                    complete_signatures.add(signature)
                    candidates.append(
                        (
                            str(task.get("taskKey") or ""),
                            condition_row,
                            condition,
                            "complete_task_map",
                        )
                    )
        for fragment in scan_levelscript_task_condition_fragments(
            data,
            script_id,
            condition_types={"CheckTalkOptionFinish"},
        ):
            condition = fragment.get("condition") or {}
            signature = (
                str(fragment.get("conditionKey") or ""),
                int(condition.get("conditionOffset") or -1),
            )
            if signature in complete_signatures:
                continue
            candidates.append(
                (None, fragment, condition, "bounded_condition_fragment")
            )
        for task_id, condition_row, condition, decode_status in candidates:
            dialog_id = _constant_param_value(condition.get("dialogId"), str)
            finish_id = _constant_param_value(condition.get("finishId"), int)
            if not dialog_id or finish_id is None:
                rejected_param_shapes += 1
                continue
            complete_rows += decode_status == "complete_task_map"
            fragment_rows += decode_status == "bounded_condition_fragment"
            files_with_consumers.add(source_file)
            rows.append({
                "dialogId": dialog_id,
                "finishId": finish_id,
                "levelId": level_id,
                "scriptId": script_id,
                "taskId": task_id,
                "conditionId": str(condition_row.get("conditionKey") or ""),
                "taskMapDecodeStatus": decode_status,
                "taskIdentityStatus": (
                    "exact_complete_task_map"
                    if task_id
                    else "unresolved_in_mixed_task_map"
                ),
                "conditionOffsetHex": condition.get("conditionOffsetHex"),
                "conditionUnionTag": condition.get("conditionUnionTag"),
                "nativeMappingId": condition.get("nativeMappingId"),
                "sourceFile": source_file,
                "sourceSha256": source_hash,
            })
    rows.sort(
        key=lambda row: (
            row["dialogId"],
            row["finishId"],
            row["levelId"],
            int(row["scriptId"]),
            row.get("taskId") or "",
            row["conditionId"],
        )
    )
    return rows, {
        **overlay,
        "filesWithFinishConsumers": len(files_with_consumers),
        "finishConsumerCount": len(rows),
        "completeTaskMapConsumerCount": complete_rows,
        "boundedFragmentConsumerCount": fragment_rows,
        "exactNonnegativeConsumerCount": sum(row["finishId"] >= 0 for row in rows),
        "anyFinishConsumerCount": sum(row["finishId"] < 0 for row in rows),
        "rejectedIndirectOrMalformedParamCount": rejected_param_shapes,
        "evidenceBoundary": (
            "The active Persistent-over-Streaming serialized overlay is scanned. "
            "Complete task maps retain exact task ids; individually bounded "
            "fragments retain exact condition identity but deliberately leave the "
            "surrounding task id unresolved. Unsupported neighboring condition "
            "types cannot create a consumer."
        ),
    }


def _load_subgame_task_owners(
    table_path: Path = DEFAULT_SUBGAME_TABLE,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    """Load unique mission/SubGame/script/task co-carriers from typed rows."""
    validator = "dialog_finish_subgame_task_owner"
    if not table_path.is_file():
        raise AuditValidationError(
            f"validator={validator} gate=subGameTable expected=file "
            f"actual=missing source={table_path}"
        )
    payload = read_json(table_path)
    table = payload.get("dataTable") if isinstance(payload, dict) else None
    if not isinstance(table, dict):
        raise AuditValidationError(
            f"validator={validator} gate=dataTable expected=object "
            f"actual={type(table).__name__} source={table_path}"
        )
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    malformed: list[dict[str, Any]] = []
    mission_script_rows = 0
    for subgame_id, raw in sorted(table.items()):
        if not isinstance(raw, dict):
            continue
        mission_id = raw.get("dungeonMissionId")
        script_id = raw.get("bindScriptId")
        if not isinstance(mission_id, str) or not mission_id:
            continue
        if not isinstance(script_id, int) or isinstance(script_id, bool) or script_id <= 0:
            continue
        mission_script_rows += 1
        if str(raw.get("id") or "") != str(subgame_id):
            malformed.append({
                "subGameId": str(subgame_id),
                "gate": "rowKeyEqualsId",
                "expected": str(subgame_id),
                "actual": raw.get("id"),
            })
            continue
        for lane_field, lane in (
            ("mainTasks", "main"),
            ("extraTasks", "extra"),
            ("failTasks", "fail"),
        ):
            task_rows = raw.get(lane_field)
            if not isinstance(task_rows, list):
                malformed.append({
                    "subGameId": str(subgame_id),
                    "gate": "taskLaneArray",
                    "expected": "array",
                    "actual": type(task_rows).__name__,
                    "lane": lane,
                })
                continue
            for task in task_rows:
                task_id = str(task.get("taskId") or "") if isinstance(task, dict) else ""
                if not re.fullmatch(r"[0-9a-f]{8}", task_id):
                    malformed.append({
                        "subGameId": str(subgame_id),
                        "gate": "taskId",
                        "expected": "eight lowercase hex characters",
                        "actual": task_id,
                        "lane": lane,
                    })
                    continue
                candidates[(str(script_id), task_id)].append({
                    "missionId": mission_id,
                    "subGameId": str(subgame_id),
                    "scriptId": str(script_id),
                    "taskId": task_id,
                    "taskLane": lane,
                    "runtimeType": str(raw.get("$type") or "").split(",", 1)[0],
                    "sourceFile": source_label(table_path),
                })
    ambiguous = [
        {
            "scriptId": key[0],
            "taskId": key[1],
            "candidates": value,
        }
        for key, value in sorted(candidates.items())
        if len(value) != 1
    ]
    accepted = {
        key: value[0]
        for key, value in candidates.items()
        if len(value) == 1
    }
    return accepted, {
        "sourceFile": source_label(table_path),
        "sourceSha256": sha256_file(table_path),
        "rowCount": len(table),
        "missionScriptRowCount": mission_script_rows,
        "uniqueTaskOwnerCount": len(accepted),
        "ambiguousTaskOwners": ambiguous,
        "malformedRows": malformed,
        "evidenceBoundary": (
            "Only one typed row that co-carries dungeonMissionId, bindScriptId, "
            "and the exact taskId in an authored task lane can identify a mission "
            "shell for that task. It does not prove the script started or that its "
            "Story playback belongs to the mission."
        ),
    }


def _collect_dialog_tree_producers(
    payloads: dict[str, dict[str, Any]],
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
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
    route_coverage: list[dict[str, Any]] = []
    endpoint_rows: list[dict[str, Any]] = []
    endpoint_rejected: list[dict[str, Any]] = []
    endpoint_coverage: list[dict[str, Any]] = []
    for source_file in source_files:
        path = resolve_source(source_file)
        if not path.is_file():
            raise AuditValidationError(
                "validator=dialog_finish_branch_recovery gate=dialogTreeSource "
                f"expected=file actual=missing source={path}"
            )
        source_route_coverage: dict[str, Any] = {}
        outer = read_json(path)
        decoded, failures = decode_dialog_tree_finish_routes(
            outer,
            source_file=source_label(path),
            runtime_defaults=runtime_defaults,
            route_coverage=source_route_coverage,
        )
        decoded_endpoints, endpoint_failures, source_endpoint_coverage = (
            decode_dialog_tree_finish_endpoints(
                outer,
                source_file=source_label(path),
                runtime_defaults=runtime_defaults,
            )
        )
        rows.extend(decoded)
        rejected.extend(failures)
        route_coverage.append(source_route_coverage)
        endpoint_rows.extend(decoded_endpoints)
        endpoint_rejected.extend(endpoint_failures)
        endpoint_coverage.append(source_endpoint_coverage)
    return (
        rows,
        rejected,
        route_coverage,
        endpoint_rows,
        endpoint_rejected,
        endpoint_coverage,
    )


def _summarize_dialog_tree_route_coverage(
    sources: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate exact per-file route diagnostics without discarding bounds."""
    source_rows = list(sources)
    totals: Counter[str] = Counter()
    mismatch_nodes: list[dict[str, Any]] = []
    invalid_routes: list[dict[str, Any]] = []
    extra_option_nodes: list[dict[str, Any]] = []
    for source in source_rows:
        source_file = str(source.get("sourceFile") or "")
        totals.update(source.get("counts") or {})
        for node in source.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            bounded = {
                "sourceFile": source_file,
                "nodeId": node.get("nodeId"),
                "nodeOrdinal": node.get("nodeOrdinal"),
                "routingClass": node.get("routingClass"),
                "serializedReferenceIdentity": node.get(
                    "serializedReferenceIdentity"
                ),
                "incomingConnectionCount": node.get("incomingConnectionCount"),
                "normalOptionCount": node.get("normalOptionCount"),
                "outgoingConnectionCount": node.get("outgoingConnectionCount"),
                "extraOptionConnectionIndices": node.get(
                    "extraOptionConnectionIndices"
                )
                or [],
            }
            if (
                isinstance(node.get("normalOptionCount"), int)
                and isinstance(node.get("outgoingConnectionCount"), int)
                and node.get("normalOptionCount")
                != node.get("outgoingConnectionCount")
            ):
                mismatch_nodes.append(bounded)
            if node.get("extraOptionConnectionIndices"):
                extra_option_nodes.append(bounded)
            for route in node.get("routes") or []:
                if isinstance(route, dict) and route.get("status") != "validated":
                    invalid_routes.append(
                        {
                            **bounded,
                            "optionId": route.get("optionId"),
                            "optionOrdinal": route.get("optionOrdinal"),
                            "connectionIndex": route.get("connectionIndex"),
                            "connectionIndexSource": route.get(
                                "connectionIndexSource"
                            ),
                            "failureClass": route.get("failureClass"),
                            "issue": route.get("issue") or {},
                        }
                    )
    return {
        "sourceFileCount": len(source_rows),
        "counts": dict(sorted(totals.items())),
        "connectionCountMismatchNodes": mismatch_nodes,
        "extraOptionNodes": extra_option_nodes,
        "invalidNormalOptionRoutes": invalid_routes,
        "evidenceBoundary": (
            "Counts describe only exact original DialogTree files observed by "
            "Mission Pipeline. Unequal option/connection counts are retained "
            "when serialized indexes validate. Unreferenced definitions, linked "
            "nodes without outgoing edges, and out-of-bounds indexes remain "
            "separate fail-closed classes."
        ),
    }


def _summarize_dialog_tree_finish_endpoint_coverage(
    sources: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate bounded prime-reachable finish diagnostics by source file."""
    source_rows = list(sources)
    totals: Counter[str] = Counter()
    rejected: list[dict[str, Any]] = []
    for source in source_rows:
        source_file = str(source.get("sourceFile") or "")
        totals.update(source.get("counts") or {})
        for endpoint in source.get("endpoints") or []:
            if not isinstance(endpoint, dict) or endpoint.get("status") == "validated":
                continue
            rejected.append(
                {
                    "sourceFile": source_file,
                    "nodeId": endpoint.get("nodeId"),
                    "nodeOrdinal": endpoint.get("nodeOrdinal"),
                    "finishId": endpoint.get("finishId"),
                    "finishIdSource": endpoint.get("finishIdSource"),
                    "failureClass": endpoint.get("failureClass"),
                    "issue": endpoint.get("issue") or {},
                }
            )
    return {
        "sourceFileCount": len(source_rows),
        "counts": dict(sorted(totals.items())),
        "rejectedFinishEndpoints": rejected,
        "evidenceBoundary": (
            "Only finish nodes reachable from the binary-proven serialized "
            "prime node through exact DialogTreeConnection references are "
            "accepted. A matching endpoint proves the authored finish value, "
            "not the route taken to reach it."
        ),
    }


def _collect_dialog_tree_corpus_coverage(
    root: Path,
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate option routes and finish endpoints over every DialogTree."""
    if not root.is_dir():
        raise AuditValidationError(
            "validator=dialog_finish_branch_recovery gate=dialogTreeCorpusRoot "
            f"expected=directory actual=missing source={root}"
        )
    coverage_sources: list[dict[str, Any]] = []
    finish_endpoint_sources: list[dict[str, Any]] = []
    scanned_json_files = 0
    for path in sorted(root.rglob("*.json")):
        scanned_json_files += 1
        outer = read_json(path)
        if not isinstance(outer, dict) or not isinstance(outer.get("m_Script"), str):
            continue
        try:
            payload = json.loads(
                base64.b64decode(outer["m_Script"], validate=True).decode(
                    "utf-8-sig"
                )
            )
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            continue
        if (
            not isinstance(payload, dict)
            or payload.get("type") != "Beyond.Gameplay.DialogTree"
            or not isinstance(payload.get("nodes"), list)
            or not isinstance(payload.get("connections"), list)
        ):
            continue
        recovered = recover_dialog_tree_option_routes(
            payload["nodes"],
            payload["connections"],
            runtime_defaults=runtime_defaults,
        )
        finish_endpoints = recover_dialog_tree_finish_endpoints(
            payload["nodes"],
            payload["connections"],
            runtime_defaults=runtime_defaults,
        )
        coverage_sources.append(
            {
                "sourceFile": source_label(path),
                "counts": recovered.get("counts") or {},
                "nodes": recovered.get("nodes") or [],
                "issues": recovered.get("issues") or [],
            }
        )
        finish_endpoint_sources.append(
            {
                "sourceFile": source_label(path),
                "counts": finish_endpoints.get("counts") or {},
                "endpoints": finish_endpoints.get("endpoints") or [],
                "issues": finish_endpoints.get("issues") or [],
            }
        )
    route_summary = _summarize_dialog_tree_route_coverage(coverage_sources)
    endpoint_summary = _summarize_dialog_tree_finish_endpoint_coverage(
        finish_endpoint_sources
    )
    shared = {
        "sourceRoot": source_label(root),
        "scannedJsonFiles": scanned_json_files,
        "dialogTreeFileCount": len(coverage_sources),
    }
    route_summary.update(shared)
    endpoint_summary.update(shared)
    return route_summary, endpoint_summary


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
    dialog_tree_root: Path = DEFAULT_DIALOG_TREE_ROOT,
    *,
    native_contract: dict[str, Any] | None = None,
    levelscript_roots: Iterable[Path] = DEFAULT_LEVELSCRIPT_ROOTS,
    subgame_table_path: Path = DEFAULT_SUBGAME_TABLE,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    validator = "dialog_finish_branch_recovery"
    native_contract = native_contract or validate_native_contract()
    levelscript_runtime_contract = _validate_levelscript_task_contracts(
        index,
        native_contract,
    )
    consumers, payloads = _collect_mission_consumers(index, pipeline_root)
    levelscript_consumers, levelscript_census = (
        _collect_levelscript_task_finish_consumers(levelscript_roots)
    )
    subgame_task_owners, subgame_owner_census = _load_subgame_task_owners(
        subgame_table_path
    )
    runtime_defaults = native_contract.get("serializedFieldDefaults") or {}
    (
        tree_rows,
        tree_rejected,
        tree_route_sources,
        finish_endpoint_rows,
        finish_endpoint_rejected,
        finish_endpoint_sources,
    ) = _collect_dialog_tree_producers(payloads, runtime_defaults=runtime_defaults)
    tree_route_coverage = _summarize_dialog_tree_route_coverage(
        tree_route_sources
    )
    tree_route_counts = tree_route_coverage.get("counts") or {}
    finish_endpoint_coverage = _summarize_dialog_tree_finish_endpoint_coverage(
        finish_endpoint_sources
    )
    finish_endpoint_counts = finish_endpoint_coverage.get("counts") or {}
    corpus_route_coverage, corpus_finish_endpoint_coverage = (
        _collect_dialog_tree_corpus_coverage(
            dialog_tree_root,
            runtime_defaults=runtime_defaults,
        )
    )
    corpus_route_counts = corpus_route_coverage.get("counts") or {}
    corpus_finish_endpoint_counts = (
        corpus_finish_endpoint_coverage.get("counts") or {}
    )
    timeline_payload = read_json(timeline_orders_path) if timeline_orders_path.is_file() else {}
    timeline_rows, timeline_rejected = decode_timeline_finish_routes(timeline_payload)
    producers, conflicts = _normalize_producers([*tree_rows, *timeline_rows])
    reused_option_scopes = _collect_reused_option_scopes(producers)
    producers_by_finish: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for producer in producers:
        producers_by_finish[(producer["dialogId"], producer["finishId"])].append(producer)
    finish_endpoints_by_finish: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = defaultdict(list)
    for endpoint in finish_endpoint_rows:
        finish_endpoints_by_finish[
            (endpoint["dialogId"], endpoint["finishId"])
        ].append(endpoint)

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
    endpoint_dependencies: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for consumer in consumers:
        matches = producers_by_finish.get((consumer["dialogId"], consumer["finishId"]), [])
        if matches:
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
            continue

        endpoint_matches = finish_endpoints_by_finish.get(
            (consumer["dialogId"], consumer["finishId"]), []
        )
        if endpoint_matches:
            source_rows = [
                source
                for row in endpoint_matches
                for source in row.get("sourceFiles") or []
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
            endpoint_dependencies.append(
                {
                    **consumer,
                    "classification": "authored_finish_endpoint_dependency",
                    "producerFamilies": [
                        "dialog_tree_prime_reachable_finish_endpoint"
                    ],
                    "producerEvidence": endpoint_matches,
                    "relatedOriginalFiles": _hash_source_rows(
                        source_rows, hash_cache, validator=validator
                    ),
                    "evidenceBoundary": (
                        "An exact finish node is reachable from the binary-proven "
                        "serialized prime node and emits the value required by this "
                        "quest objective. This proves an authored endpoint dependency, "
                        "not the route or player choice that reaches it, dialog "
                        "activation, server successor choice, or total Story-file order."
                    ),
                }
            )
            continue

        unresolved.append(consumer)

    dependencies.sort(
        key=lambda row: (
            row["missionId"], row["questId"], row["objectiveIndex"] or 0,
            row["dialogId"], row["finishId"], row["optionIds"],
        )
    )
    endpoint_dependencies.sort(
        key=lambda row: (
            row["missionId"],
            row["questId"],
            row["objectiveIndex"] or 0,
            row["dialogId"],
            row["finishId"],
        )
    )

    exact_levelscript_consumers = [
        row for row in levelscript_consumers if row["finishId"] >= 0
    ]
    levelscript_by_finish: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in exact_levelscript_consumers:
        owner = (
            subgame_task_owners.get((row["scriptId"], row["taskId"]))
            if row.get("taskId")
            else None
        )
        if owner:
            row["missionShellOwner"] = owner
        levelscript_by_finish[(row["dialogId"], row["finishId"])].append(row)

    resolved_mission_dependencies = [*dependencies, *endpoint_dependencies]
    shared_task_dependencies: list[dict[str, Any]] = []
    matched_levelscript_signatures: set[tuple[Any, ...]] = set()
    for mission_dependency in resolved_mission_dependencies:
        task_matches = levelscript_by_finish.get(
            (
                mission_dependency["dialogId"],
                mission_dependency["finishId"],
            ),
            [],
        )
        for task_consumer in task_matches:
            owner = task_consumer.get("missionShellOwner")
            owner_relationship = (
                "same_mission_shell"
                if owner
                and owner.get("missionId") == mission_dependency["missionId"]
                else "different_mission_shell"
                if owner
                else "mission_shell_unresolved"
            )
            source_rows = [
                *(
                    mission_dependency.get("relatedOriginalFiles") or []
                ),
                {
                    "kind": "level_script",
                    "sourceFile": task_consumer["sourceFile"],
                    "relationship": "exact_dialog_finish_task_consumer",
                },
            ]
            if owner:
                source_rows.append({
                    "kind": "subgame_instance_table",
                    "sourceFile": owner["sourceFile"],
                    "relationship": "exact_mission_script_task_co_carrier",
                })
            row = {
                "missionId": mission_dependency["missionId"],
                "questId": mission_dependency["questId"],
                "objectiveIndex": mission_dependency["objectiveIndex"],
                "missionConditionId": mission_dependency["conditionId"],
                "dialogId": mission_dependency["dialogId"],
                "finishId": mission_dependency["finishId"],
                "producerClassification": mission_dependency["classification"],
                "producerFamilies": mission_dependency.get("producerFamilies") or [],
                "optionIds": mission_dependency.get("optionIds") or [],
                "producerEvidence": mission_dependency.get("producerEvidence") or [],
                "levelId": task_consumer["levelId"],
                "scriptId": task_consumer["scriptId"],
                "taskId": task_consumer.get("taskId"),
                "taskConditionId": task_consumer["conditionId"],
                "taskMapDecodeStatus": task_consumer["taskMapDecodeStatus"],
                "taskIdentityStatus": task_consumer["taskIdentityStatus"],
                "conditionOffsetHex": task_consumer.get("conditionOffsetHex"),
                "missionShellOwner": owner,
                "missionShellRelationship": owner_relationship,
                "classification": "shared_exact_dialog_finish_consumer_dependency",
                "relatedOriginalFiles": _hash_source_rows(
                    source_rows,
                    hash_cache,
                    validator=validator,
                ),
                "evidenceBoundary": (
                    "The binary-proven CheckTalkOptionFinish state is consumed by "
                    "both this MissionRuntime objective and this original "
                    "LevelScript task condition. This proves a shared branch-state "
                    "fan-out, not that the task was active, that the mission owns "
                    "the LevelScript, which option a player selected, or any "
                    "cross-file chronology. Mission-shell ownership is shown only "
                    "when one typed SubGame row also co-carries the exact script "
                    "and task ids."
                ),
            }
            shared_task_dependencies.append(row)
            matched_levelscript_signatures.add((
                task_consumer["levelId"],
                task_consumer["scriptId"],
                task_consumer.get("taskId"),
                task_consumer["conditionId"],
                task_consumer["dialogId"],
                task_consumer["finishId"],
            ))
    shared_task_dependencies.sort(
        key=lambda row: (
            row["missionId"],
            row["questId"],
            row["objectiveIndex"] or 0,
            row["levelId"],
            int(row["scriptId"]),
            row.get("taskId") or "",
            row["taskConditionId"],
        )
    )
    unmatched_levelscript_consumers = [
        row
        for row in exact_levelscript_consumers
        if (
            row["levelId"],
            row["scriptId"],
            row.get("taskId"),
            row["conditionId"],
            row["dialogId"],
            row["finishId"],
        )
        not in matched_levelscript_signatures
    ]
    report = {
        "schemaVersion": "dialogFinishMissionBranchAudit.v6",
        "status": "validated",
        "validator": validator,
        "evidencePolicy": (
            "Only exact nonnegative dialog finish IDs shared by an original "
            "MissionRuntime objective and either an authored option producer or a "
            "prime-reachable DialogTree finish endpoint are admitted. Option-routed "
            "and endpoint-only dependencies remain separate. A DialogTree normal "
            "option selects the physical outgoing "
            "edge stored in NormalOptionData.index. An omitted DialogTree Int32 "
            "is admitted as zero only under the hash-locked FullSerializer "
            "reflected-field default contract. ShowOptions sets doNext before "
            "selection, so missing physical successors are retained as failures, "
            "not reclassified as terminal choices. Exact LevelScript task "
            "conditions that consume the same finish state are published as "
            "fan-out dependencies without inferring task activation or ownership. "
            "OCR and manual overrides are not read."
        ),
        "nativeContract": native_contract,
        "levelScriptRuntimeContract": levelscript_runtime_contract,
        "sources": {
            "timelineOrders": source_label(timeline_orders_path),
            "pipelineIndex": source_label(pipeline_root / "index.json"),
            "subGameTable": source_label(subgame_table_path),
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
            "dialogTreeRouteSourceFiles": tree_route_coverage.get(
                "sourceFileCount", 0
            ),
            "dialogTreeValidatedNormalOptionRoutes": tree_route_counts.get(
                "validatedNormalOptionRoutes", 0
            ),
            "dialogTreeRejectedNormalOptionRoutes": tree_route_counts.get(
                "rejectedNormalOptionRoutes", 0
            ),
            "dialogTreeRuntimeDefaultConnectionIndexes": tree_route_counts.get(
                "runtimeDefaultConnectionIndexes", 0
            ),
            "dialogTreeExplicitConnectionIndexes": tree_route_counts.get(
                "explicitConnectionIndexes", 0
            ),
            "dialogTreeConnectionCountMismatchNodes": tree_route_counts.get(
                "connectionCountMismatchNodes", 0
            ),
            "dialogTreeExtraOptionNodes": tree_route_counts.get(
                "extraOptionNodes", 0
            ),
            "dialogTreeFinishEndpointSourceFiles": finish_endpoint_coverage.get(
                "sourceFileCount", 0
            ),
            "dialogTreeAuthoredFinishNodes": finish_endpoint_counts.get(
                "authoredFinishNodes", 0
            ),
            "dialogTreeValidatedFinishEndpoints": finish_endpoint_counts.get(
                "validatedFinishEndpoints", 0
            ),
            "dialogTreeRejectedFinishEndpoints": finish_endpoint_counts.get(
                "rejectedFinishEndpoints", 0
            ),
            "dialogTreeExplicitFinishEndpoints": finish_endpoint_counts.get(
                "explicitFinishIds", 0
            ),
            "dialogTreeRuntimeDefaultFinishEndpoints": finish_endpoint_counts.get(
                "runtimeDefaultFinishIds", 0
            ),
            "dialogTreeUnreferencedOptionDefinitionNodes": tree_route_counts.get(
                "unreferencedOptionDefinitionNodes", 0
            ),
            "dialogTreeLinkedOptionNodesWithoutOutgoingConnections": tree_route_counts.get(
                "linkedOptionNodesWithoutOutgoingConnections", 0
            ),
            "dialogTreeLinkedOptionNodesWithPartialIndexCoverage": tree_route_counts.get(
                "linkedOptionNodesWithPartialIndexCoverage", 0
            ),
            "corpusDialogTreeFiles": corpus_route_coverage.get(
                "dialogTreeFileCount", 0
            ),
            "corpusDialogTreeOptionNodes": corpus_route_counts.get(
                "authoredOptionNodes", 0
            ),
            "corpusDecodableDialogTreeOptionNodes": corpus_route_counts.get(
                "optionNodes", 0
            ),
            "corpusAuthoredNormalOptions": corpus_route_counts.get(
                "authoredNormalOptions", 0
            ),
            "corpusUnrecoverableOptionNodes": corpus_route_counts.get(
                "unrecoverableOptionNodes", 0
            ),
            "corpusUnreferencedOptionDefinitionNodes": corpus_route_counts.get(
                "unreferencedOptionDefinitionNodes", 0
            ),
            "corpusUnreferencedOptionDefinitionRoutes": corpus_route_counts.get(
                "unreferencedOptionDefinitionRoutes", 0
            ),
            "corpusLinkedOptionNodesWithoutOutgoingConnections": corpus_route_counts.get(
                "linkedOptionNodesWithoutOutgoingConnections", 0
            ),
            "corpusLinkedNormalOptionsWithoutOutgoingConnections": corpus_route_counts.get(
                "linkedNormalOptionsWithoutOutgoingConnections", 0
            ),
            "corpusLinkedOptionNodesWithPartialIndexCoverage": corpus_route_counts.get(
                "linkedOptionNodesWithPartialIndexCoverage", 0
            ),
            "corpusSerializedConnectionIndexesOutOfBounds": corpus_route_counts.get(
                "serializedConnectionIndexesOutOfBounds", 0
            ),
            "corpusValidatedNormalOptionRoutes": corpus_route_counts.get(
                "validatedNormalOptionRoutes", 0
            ),
            "corpusRejectedNormalOptionRoutes": corpus_route_counts.get(
                "rejectedNormalOptionRoutes", 0
            ),
            "corpusConnectionCountMismatchNodes": corpus_route_counts.get(
                "connectionCountMismatchNodes", 0
            ),
            "corpusExtraOptionNodes": corpus_route_counts.get(
                "extraOptionNodes", 0
            ),
            "corpusAuthoredFinishNodes": corpus_finish_endpoint_counts.get(
                "authoredFinishNodes", 0
            ),
            "corpusValidatedFinishEndpoints": corpus_finish_endpoint_counts.get(
                "validatedFinishEndpoints", 0
            ),
            "corpusRejectedFinishEndpoints": corpus_finish_endpoint_counts.get(
                "rejectedFinishEndpoints", 0
            ),
            "corpusUnreferencedFinishDefinitions": corpus_finish_endpoint_counts.get(
                "unreferencedFinishDefinitions", 0
            ),
            "corpusUnreachableFinishNodes": corpus_finish_endpoint_counts.get(
                "unreachableFinishNodes", 0
            ),
            "timelineProducerRows": len(timeline_rows),
            "acceptedOptionProducers": len(producers),
            "finishEndpointProducerRows": len(finish_endpoint_rows),
            "publishedDependencies": len(dependencies),
            "publishedEndpointDependencies": len(endpoint_dependencies),
            "totalPublishedDependencies": len(dependencies)
            + len(endpoint_dependencies),
            "exactConsumerCoverage": len(dependencies)
            + len(endpoint_dependencies),
            "uniqueOptionDependencies": sum(
                row["classification"] == "unique_option_outcome_dependency"
                for row in dependencies
            ),
            "missions": len({row["missionId"] for row in dependencies}),
            "quests": len({row["questId"] for row in dependencies}),
            "endpointMissions": len(
                {row["missionId"] for row in endpoint_dependencies}
            ),
            "endpointQuests": len(
                {row["questId"] for row in endpoint_dependencies}
            ),
            "unresolvedExactConsumers": len(unresolved),
            "rejectedProducerShapes": len(tree_rejected) + len(timeline_rejected),
            "conflictingOptionProducers": len(conflicts),
            "reusedOptionIdsAcrossScopes": len(reused_option_scopes),
            "levelScriptTaskFinishConsumers": len(levelscript_consumers),
            "levelScriptTaskExactFinishConsumers": len(
                exact_levelscript_consumers
            ),
            "levelScriptTaskAnyFinishConsumers": sum(
                row["finishId"] < 0 for row in levelscript_consumers
            ),
            "levelScriptTaskSharedConsumerDependencies": len(
                shared_task_dependencies
            ),
            "levelScriptTaskSharedConsumerRows": len(
                matched_levelscript_signatures
            ),
            "levelScriptTaskSharedConsumerMissions": len({
                row["missionId"] for row in shared_task_dependencies
            }),
            "levelScriptTaskSharedConsumerCompleteMaps": sum(
                row["taskMapDecodeStatus"] == "complete_task_map"
                for row in shared_task_dependencies
            ),
            "levelScriptTaskSharedConsumerFragments": sum(
                row["taskMapDecodeStatus"] == "bounded_condition_fragment"
                for row in shared_task_dependencies
            ),
            "levelScriptTaskMissionShellOwners": sum(
                bool(row.get("missionShellOwner"))
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskSameMissionShellDependencies": sum(
                row["missionShellRelationship"] == "same_mission_shell"
                for row in shared_task_dependencies
            ),
            "levelScriptTaskUnmatchedExactConsumers": len(
                unmatched_levelscript_consumers
            ),
        },
        "producerFamilyCounts": dict(
            sorted(Counter(family for row in producers for family in row["producerFamilies"]).items())
        ),
        "dialogTreeOptionRouteCoverage": tree_route_coverage,
        "dialogTreeOptionRouteCorpusCoverage": corpus_route_coverage,
        "dialogTreeFinishEndpointCoverage": finish_endpoint_coverage,
        "dialogTreeFinishEndpointCorpusCoverage": corpus_finish_endpoint_coverage,
        "levelScriptTaskConsumerCensus": {
            **levelscript_census,
            "exactConsumers": exact_levelscript_consumers,
            "unmatchedExactConsumers": unmatched_levelscript_consumers,
        },
        "subGameTaskOwnerCensus": subgame_owner_census,
        "dependencies": dependencies,
        "endpointDependencies": endpoint_dependencies,
        "levelScriptTaskSharedConsumerDependencies": shared_task_dependencies,
        "unresolvedExactConsumers": unresolved,
        "rejectedProducerShapes": [*tree_rejected, *timeline_rejected],
        "rejectedFinishEndpointShapes": finish_endpoint_rejected,
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
    endpoint_by_quest: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in report.get("endpointDependencies") or []:
        endpoint_by_quest[(row["missionId"], row["questId"])].append(row)
    task_by_quest: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in report.get("levelScriptTaskSharedConsumerDependencies") or []:
        task_by_quest[(row["missionId"], row["questId"])].append(row)
    published = 0
    published_endpoints = 0
    published_task_dependencies = 0
    published_owned_task_dependencies = 0
    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        payload = payloads.get(mission_id)
        if not payload:
            continue
        mission_rows: list[dict[str, Any]] = []
        mission_endpoint_rows: list[dict[str, Any]] = []
        mission_task_rows: list[dict[str, Any]] = []
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node.pop("dialogFinishBranchDependencies", None)
            node.pop("dialogFinishEndpointDependencies", None)
            node.pop("dialogFinishLevelScriptTaskDependencies", None)
            rows = by_quest.get((mission_id, str(node.get("id") or "")), [])
            endpoint_rows = endpoint_by_quest.get(
                (mission_id, str(node.get("id") or "")), []
            )
            task_rows = task_by_quest.get(
                (mission_id, str(node.get("id") or "")), []
            )
            if rows:
                node["dialogFinishBranchDependencies"] = rows
                mission_rows.extend(rows)
            if endpoint_rows:
                node["dialogFinishEndpointDependencies"] = endpoint_rows
                mission_endpoint_rows.extend(endpoint_rows)
            if task_rows:
                node["dialogFinishLevelScriptTaskDependencies"] = task_rows
                mission_task_rows.extend(task_rows)
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                objective.pop("dialogFinishBranchDependencies", None)
                objective.pop("dialogFinishEndpointDependencies", None)
                objective.pop("dialogFinishLevelScriptTaskDependencies", None)
                objective_rows = [
                    row for row in rows
                    if row.get("objectiveIndex") == objective.get("index")
                    and row.get("conditionId") == str(objective.get("conditionId") or "")
                ]
                objective_endpoint_rows = [
                    row
                    for row in endpoint_rows
                    if row.get("objectiveIndex") == objective.get("index")
                    and row.get("conditionId")
                    == str(objective.get("conditionId") or "")
                ]
                objective_task_rows = [
                    row
                    for row in task_rows
                    if row.get("objectiveIndex") == objective.get("index")
                    and row.get("missionConditionId")
                    == str(objective.get("conditionId") or "")
                ]
                if objective_rows:
                    objective["dialogFinishBranchDependencies"] = objective_rows
                if objective_endpoint_rows:
                    objective["dialogFinishEndpointDependencies"] = (
                        objective_endpoint_rows
                    )
                if objective_task_rows:
                    objective["dialogFinishLevelScriptTaskDependencies"] = (
                        objective_task_rows
                    )
        for binding in (payload.get("mission") or {}).get(
            "nativeRuntimeBindings", []
        ):
            if not isinstance(binding, dict):
                continue
            binding.pop("dialogFinishTaskDependencies", None)
            binding_rows = [
                row
                for row in mission_task_rows
                for owner in [row.get("missionShellOwner")]
                if isinstance(owner, dict)
                and owner.get("missionId") == mission_id
                and owner.get("subGameId") == binding.get("subGameId")
                and owner.get("scriptId") == binding.get("bindScriptId")
            ]
            if binding_rows:
                binding["dialogFinishTaskDependencies"] = binding_rows
        payload["dialogFinishBranchRecovery"] = {
            "schema": report.get("schemaVersion"),
            "status": report.get("status"),
            "dependencyCount": len(mission_rows),
            "endpointDependencyCount": len(mission_endpoint_rows),
            "exactConsumerCoverageCount": len(mission_rows)
            + len(mission_endpoint_rows),
            "levelScriptTaskSharedConsumerDependencyCount": len(
                mission_task_rows
            ),
            "levelScriptTaskMissionShellDependencyCount": sum(
                row.get("missionShellRelationship") == "same_mission_shell"
                for row in mission_task_rows
            ),
            "evidenceBoundary": report.get("evidencePolicy"),
        }
        summary["dialogFinishBranchDependencyCount"] = len(mission_rows)
        summary["dialogFinishEndpointDependencyCount"] = len(
            mission_endpoint_rows
        )
        summary["dialogFinishLevelScriptTaskDependencyCount"] = len(
            mission_task_rows
        )
        write_json(pipeline_root / str(summary.get("file") or ""), payload)
        published += len(mission_rows)
        published_endpoints += len(mission_endpoint_rows)
        published_task_dependencies += len(mission_task_rows)
        published_owned_task_dependencies += sum(
            row.get("missionShellRelationship") == "same_mission_shell"
            for row in mission_task_rows
        )
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
    index["counts"]["dialogFinishEndpointDependencies"] = published_endpoints
    index["counts"]["dialogFinishExactConsumerCoverage"] = (
        published + published_endpoints
    )
    index["counts"]["dialogFinishLevelScriptTaskDependencies"] = (
        published_task_dependencies
    )
    index["counts"]["dialogFinishOwnedLevelScriptTaskDependencies"] = (
        published_owned_task_dependencies
    )
    return published + published_endpoints + published_task_dependencies


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
        f"- Validated / rejected normal-option routes: {counts.get('dialogTreeValidatedNormalOptionRoutes', 0)} / {counts.get('dialogTreeRejectedNormalOptionRoutes', 0)}",
        f"- Explicit / runtime-default connection indexes: {counts.get('dialogTreeExplicitConnectionIndexes', 0)} / {counts.get('dialogTreeRuntimeDefaultConnectionIndexes', 0)}",
        f"- Unequal option/connection nodes admitted by exact index / extra-option nodes: {counts.get('dialogTreeConnectionCountMismatchNodes', 0)} / {counts.get('dialogTreeExtraOptionNodes', 0)}",
        f"- Mission-linked validated / rejected finish endpoints: {counts.get('dialogTreeValidatedFinishEndpoints', 0)} / {counts.get('dialogTreeRejectedFinishEndpoints', 0)}",
        f"- Mission-linked explicit / runtime-default finish endpoints: {counts.get('dialogTreeExplicitFinishEndpoints', 0)} / {counts.get('dialogTreeRuntimeDefaultFinishEndpoints', 0)}",
        f"- Full typed corpus: {counts.get('corpusDialogTreeFiles', 0)} DialogTrees, {counts.get('corpusDialogTreeOptionNodes', 0)} authored option nodes, {counts.get('corpusAuthoredNormalOptions', 0)} normal options",
        f"- Full-corpus validated / rejected routes: {counts.get('corpusValidatedNormalOptionRoutes', 0)} / {counts.get('corpusRejectedNormalOptionRoutes', 0)}; unrecoverable-identity option nodes: {counts.get('corpusUnrecoverableOptionNodes', 0)}",
        f"- Full-corpus rejected-route structure: {counts.get('corpusUnreferencedOptionDefinitionRoutes', 0)} unreferenced definition options; {counts.get('corpusLinkedNormalOptionsWithoutOutgoingConnections', 0)} options on linked zero-edge nodes; {counts.get('corpusSerializedConnectionIndexesOutOfBounds', 0)} out-of-bounds indexes on partially connected nodes",
        f"- Full-corpus unequal-count / extra-option nodes: {counts.get('corpusConnectionCountMismatchNodes', 0)} / {counts.get('corpusExtraOptionNodes', 0)}",
        f"- Full-corpus validated / rejected finish endpoints: {counts.get('corpusValidatedFinishEndpoints', 0)} / {counts.get('corpusRejectedFinishEndpoints', 0)}",
        f"- Published option-routed / endpoint-only dependencies: {counts.get('publishedDependencies', 0)} / {counts.get('publishedEndpointDependencies', 0)}",
        f"- Exact consumer coverage: {counts.get('exactConsumerCoverage', 0)} / {counts.get('exactMissionConsumers', 0)}",
        f"- Option-routed missions / quests: {counts.get('missions', 0)} / {counts.get('quests', 0)}",
        f"- Endpoint-only missions / quests: {counts.get('endpointMissions', 0)} / {counts.get('endpointQuests', 0)}",
        f"- Unresolved exact consumers: {counts.get('unresolvedExactConsumers', 0)}",
        f"- Rejected / conflicting producer shapes: {counts.get('rejectedProducerShapes', 0)} / {counts.get('conflictingOptionProducers', 0)}",
        f"- Localization option IDs reused across runtime scopes: {counts.get('reusedOptionIdsAcrossScopes', 0)}",
        f"- Active LevelScript finish consumers: {counts.get('levelScriptTaskFinishConsumers', 0)} total; {counts.get('levelScriptTaskExactFinishConsumers', 0)} exact / {counts.get('levelScriptTaskAnyFinishConsumers', 0)} any-finish",
        f"- Shared MissionRuntime/LevelScript finish dependencies: {counts.get('levelScriptTaskSharedConsumerDependencies', 0)} placements across {counts.get('levelScriptTaskSharedConsumerMissions', 0)} missions",
        f"- Shared dependencies from complete maps / bounded mixed-map fragments: {counts.get('levelScriptTaskSharedConsumerCompleteMaps', 0)} / {counts.get('levelScriptTaskSharedConsumerFragments', 0)}",
        f"- Exact SubGame mission-shell task owners: {counts.get('levelScriptTaskMissionShellOwners', 0)} consumers; {counts.get('levelScriptTaskSameMissionShellDependencies', 0)} same-mission dependency placements",
        f"- Exact LevelScript consumers without a MissionRuntime finish match: {counts.get('levelScriptTaskUnmatchedExactConsumers', 0)}",
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
    lines.extend(["", "## Recovered endpoint-only dependencies", ""])
    endpoint_rows = report.get("endpointDependencies") or []
    if endpoint_rows:
        lines.extend(
            [
                "| Mission | Quest | Dialog finish | Finish node | Prime path | Value source |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in endpoint_rows:
            evidence = row.get("producerEvidence") or []
            finish_nodes = sorted(
                {str(item.get("finishNodeId") or "") for item in evidence}
            )
            paths = sorted(
                {
                    " -> ".join(str(value) for value in item.get("nodePath") or [])
                    for item in evidence
                }
            )
            sources = sorted(
                {str(item.get("finishIdSource") or "") for item in evidence}
            )
            lines.append(
                f"| `{row['missionId']}` | `{row['questId']}` | "
                f"`{row['dialogId']}` / `{row['finishId']}` | "
                f"{', '.join(f'`{value}`' for value in finish_nodes)} | "
                f"{', '.join(f'`{value}`' for value in paths)} | "
                f"{', '.join(f'`{value}`' for value in sources)} |"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Shared LevelScript task consumers", ""])
    task_rows = report.get("levelScriptTaskSharedConsumerDependencies") or []
    if task_rows:
        lines.extend(
            [
                "| Mission | Quest | Dialog finish | LevelScript task consumer | Decode | Mission shell |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in task_rows:
            task_id = row.get("taskId") or "task-id-unresolved"
            owner = row.get("missionShellOwner") or {}
            owner_text = (
                f"`{owner.get('missionId')}` / `{owner.get('subGameId')}` / "
                f"`{owner.get('taskLane')}`"
                if owner
                else "unresolved"
            )
            lines.append(
                f"| `{row['missionId']}` | `{row['questId']}` | "
                f"`{row['dialogId']}` / `{row['finishId']}` | "
                f"`{row['levelId']}/{row['scriptId']}` / `{task_id}` / "
                f"`{row['taskConditionId']}` | "
                f"`{row['taskMapDecodeStatus']}` | {owner_text} |"
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
    lines.extend(["", "## Invalid original normal-option routes", ""])
    invalid_routes = (
        report.get("dialogTreeOptionRouteCoverage") or {}
    ).get("invalidNormalOptionRoutes") or []
    if invalid_routes:
        for row in invalid_routes:
            issue = row.get("issue") or {}
            lines.append(
                f"- `{row.get('sourceFile')}` node `{row.get('nodeId')}` option "
                f"`{row.get('optionId')}` uses connection index "
                f"`{row.get('connectionIndex')}` ({row.get('connectionIndexSource')}); "
                f"gate `{issue.get('gate')}`, expected `{issue.get('expected')}`."
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
    parser.add_argument("--dialog-tree-root", type=Path, default=DEFAULT_DIALOG_TREE_ROOT)
    parser.add_argument(
        "--streaming-levelscript-root",
        type=Path,
        default=DEFAULT_LEVELSCRIPT_ROOTS[0],
    )
    parser.add_argument(
        "--persistent-levelscript-root",
        type=Path,
        default=DEFAULT_LEVELSCRIPT_ROOTS[1],
    )
    parser.add_argument("--subgame-table", type=Path, default=DEFAULT_SUBGAME_TABLE)
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
        args.dialog_tree_root,
        native_contract=native,
        levelscript_roots=(
            args.streaming_levelscript_root,
            args.persistent_levelscript_root,
        ),
        subgame_table_path=args.subgame_table,
    )
    write_json(args.json, report)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    if args.publish:
        publish_to_pipeline_index(index, report, payloads, args.pipeline_root)
        write_json(index_path, index)
    print(
        "dialog finish branch audit: "
        f"{report['counts']['publishedDependencies']} option dependencies, "
        f"{report['counts']['publishedEndpointDependencies']} endpoint-only dependencies, "
        f"{report['counts']['levelScriptTaskSharedConsumerDependencies']} shared LevelScript task dependencies, "
        f"{report['counts']['unresolvedExactConsumers']} unresolved exact consumers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
