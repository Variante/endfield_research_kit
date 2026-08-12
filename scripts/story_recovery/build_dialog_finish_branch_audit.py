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

from scripts.common import (  # noqa: E402
    NATIVE_EVIDENCE_MISSING,
    NativeEvidenceUnavailable,
    check_installed_native_inputs,
    native_evidence_required,
    native_evidence_skip_message,
    resolve_installed_game_data_root,
    sha256_file,
)
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
from scripts.story_builder.level_bindings import (
    build_leveldata_authoritative_scope_script_host_index,
    build_npc_proxy_segment_script_host_index,
    parse_leveldata_levelscript_brief_dictionary,
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
DEFAULT_LEVELDATA_ROOTS = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "LevelData",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "LevelData",
)
DEFAULT_MISSION_RUNTIME_ROOTS = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "MissionRuntimeAsset",
)
DEFAULT_TASK_CARRIER_ROOTS = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json",
)
TASK_CARRIER_DEFINITION_FAMILIES = {
    "LevelScriptData",
    "LevelScriptTemplateData",
}
DEFAULT_SUBGAME_TABLES = (
    ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "GameplayConfig"
    / "SubGameInstanceDataTable.json",
    ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Data"
    / "Json"
    / "GameplayConfig"
    / "SubGameInstanceDataTable.json",
)
DEFAULT_SUBGAME_TABLE = next(
    (path for path in reversed(DEFAULT_SUBGAME_TABLES) if path.is_file()),
    DEFAULT_SUBGAME_TABLES[0],
)
DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
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


class NativeContractUnavailable(AuditValidationError, NativeEvidenceUnavailable):
    """The installed client cannot back this audit's recorded native contract.

    It is both: an audit validation failure with the usual bounded gate
    diagnostic, and the signal that lets a build-independent caller skip this
    audit instead of failing.
    """


def _native_gate_diagnostic(validator: str, native: Any) -> str:
    """Render the gate result in this repo's expected-versus-actual style."""
    if native.status == NATIVE_EVIDENCE_MISSING:
        absent = [
            path
            for path in (native.gameassembly, native.metadata)
            if not path.is_file()
        ]
        sources = ", ".join(source_label(path) for path in absent)
        return (
            f"validator={validator} gate=sourceExists expected=file "
            f"actual=missing source={sources}"
        )
    drifted = [
        (path, actual, expected)
        for path, actual, expected in (
            (
                native.gameassembly,
                native.gameassembly_sha256,
                EXPECTED_GAME_ASSEMBLY_SHA256,
            ),
            (native.metadata, native.metadata_sha256, EXPECTED_METADATA_SHA256),
        )
        if actual.casefold() != expected.casefold()
    ]
    return "; ".join(
        f"validator={validator} gate=sourceSha256 source={source_label(path)} "
        f"expected={expected} actual={actual}"
        for path, actual, expected in drifted
    )


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
    """Bind the recorded native contract to the installed binaries.

    Raises ``NativeEvidenceUnavailable`` when the client is absent or is a
    different build, so callers can skip this audit instead of failing a
    pipeline that is otherwise build-independent.
    """
    validator = "dialog_finish_native_contract"
    native = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not native.validated:
        raise NativeContractUnavailable(
            native,
            _native_gate_diagnostic(validator, native),
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


def _validated_finish_endpoint_rows(
    dialog_id: str,
    recovered: dict[str, Any],
    *,
    source_file: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize validated endpoint rows from one decoded DialogTree graph."""
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for endpoint in recovered.get("endpoints") or []:
        if endpoint.get("status") != "validated":
            rejected.append(
                {
                    "sourceFile": source_file,
                    "dialogId": dialog_id,
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
    rows, rejected = _validated_finish_endpoint_rows(
        dialog_id,
        recovered,
        source_file=source_file,
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
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    exact_consumers: list[dict[str, Any]] = []
    any_finish_consumers: list[dict[str, Any]] = []
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
                    if not dialog_id or not isinstance(finish_id, int):
                        continue
                    consumer = {
                        "missionId": mission_id,
                        "questId": quest_id,
                        "objectiveIndex": objective.get("index"),
                        "conditionId": str(objective.get("conditionId") or ""),
                        "dialogId": dialog_id,
                        "finishId": finish_id,
                        "missionSource": mission_source,
                    }
                    if finish_id >= 0:
                        exact_consumers.append(consumer)
                    elif finish_id == -1:
                        any_finish_consumers.append(consumer)
    return exact_consumers, any_finish_consumers, payloads


def _collect_mission_levelscript_contexts(
    payloads: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collect exact MissionRuntime objective-to-LevelScript identities.

    These rows are mission-to-script observation contexts.  They do not name a
    task and therefore cannot establish task activation or task ownership.
    """
    contexts: list[dict[str, Any]] = []
    for mission_id, payload in sorted(payloads.items()):
        mission_source = str((payload.get("mission") or {}).get("source") or "")
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            quest_id = str(node.get("id") or "")
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                for source in objective.get("levelScriptSources") or []:
                    if not isinstance(source, dict):
                        continue
                    level_id = str(source.get("levelId") or "")
                    script_id = str(source.get("scriptId") or "")
                    active_file = str(
                        (source.get("levelScriptOverlay") or {}).get(
                            "activeSourceFile"
                        )
                        or ""
                    )
                    active_hash = str(
                        (source.get("levelScriptOverlay") or {}).get(
                            "activeSha256"
                        )
                        or ""
                    )
                    if not level_id or not script_id:
                        continue
                    if not active_file or not active_hash:
                        raise AuditValidationError(
                            "validator=dialog_finish_mission_levelscript_context "
                            "gate=activeLevelScriptOverlay "
                            f"mission={mission_id} quest={quest_id} "
                            f"identity={level_id}/{script_id} "
                            "expected=activeSourceFile+activeSha256 "
                            f"actual={source.get('levelScriptOverlay')!r} "
                            f"source={mission_source or 'mission_pipeline'}"
                        )
                    contexts.append({
                        "missionId": mission_id,
                        "questId": quest_id,
                        "objectiveIndex": objective.get("index"),
                        "missionConditionId": str(
                            objective.get("conditionId") or ""
                        ),
                        "missionConditionType": str(
                            source.get("conditionType") or ""
                        ),
                        "levelId": level_id,
                        "scriptId": script_id,
                        "missionSource": mission_source,
                        "activeLevelScriptSourceFile": active_file,
                        "activeLevelScriptSha256": active_hash,
                        "levelScriptOverlay": source.get("levelScriptOverlay") or {},
                    })
    contexts.sort(
        key=lambda row: (
            row["missionId"],
            row["questId"],
            row.get("objectiveIndex") or 0,
            row["levelId"],
            int(row["scriptId"]),
        )
    )
    return contexts


def _collect_mission_npc_proxy_tracking_consumers(
    roots: Iterable[Path] = DEFAULT_MISSION_RUNTIME_ROOTS,
) -> dict[str, list[dict[str, Any]]]:
    """Collect typed tracking rows from the active original MissionRuntime set."""
    validator = "dialog_finish_npc_proxy_tracking_census"
    active: dict[str, Path] = {}
    for root in roots:
        if not root.is_dir():
            raise AuditValidationError(
                f"validator={validator} gate=missionRuntimeRoot "
                f"expected=directory actual=missing source={root}"
            )
        for path in sorted(root.rglob("*.json")):
            active[path.relative_to(root).as_posix()] = path

    by_proxy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for logical_path, path in sorted(active.items()):
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            raise AuditValidationError(
                f"validator={validator} gate=typedMissionRuntimeJson "
                f"identity={logical_path} expected=valid_json "
                f"actual={type(exc).__name__} source={path}"
            ) from exc
        if not isinstance(payload, dict):
            raise AuditValidationError(
                f"validator={validator} gate=missionRuntimeRootObject "
                f"identity={logical_path} expected=object "
                f"actual={type(payload).__name__} source={path}"
            )
        mission_id = str(payload.get("missionId") or "").strip()
        if not mission_id:
            raise AuditValidationError(
                f"validator={validator} gate=missionIdentity "
                f"identity={logical_path} expected=nonempty_missionId "
                f"actual={payload.get('missionId')!r} source={path}"
            )

        def visit(value: Any, json_path: str) -> None:
            if isinstance(value, dict):
                if _short_type(value.get("$type")) == "NpcProxyTrackingInfo":
                    proxy_id = str(value.get("npcProxyId") or "").strip()
                    scene = str(value.get("sceneId") or "").strip()
                    if proxy_id and scene:
                        by_proxy[proxy_id].append({
                            "type": "NpcProxyTrackingInfo",
                            "proxyId": proxy_id,
                            "scene": scene,
                            "missionId": mission_id,
                            "jsonPath": json_path,
                            "sourceFile": source_label(path),
                        })
                for key, child in value.items():
                    visit(child, f"{json_path}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{json_path}[{index}]")

        visit(payload, "$")
    for rows in by_proxy.values():
        rows.sort(
            key=lambda row: (
                row["missionId"],
                row["scene"],
                row["sourceFile"],
                row["jsonPath"],
            )
        )
    return dict(sorted(by_proxy.items()))


def _npc_proxy_segment_source_rows(
    context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for host in (context or {}).get("hosts") or []:
        registry = host.get("registryRow") or {}
        if registry.get("sourceFile"):
            rows.append({
                "kind": "world_entity_registry",
                "sourceFile": registry["sourceFile"],
                "relationship": "exact_npc_proxy_segment_global_script_id",
            })
        for proxy_ex in host.get("npcProxyExRows") or []:
            if proxy_ex.get("sourceFile"):
                rows.append({
                    "kind": "npc_proxy_ex",
                    "sourceFile": proxy_ex["sourceFile"],
                    "relationship": "exact_npc_proxy_mission_shell",
                })
        for consumer in host.get("trackingConsumers") or []:
            if consumer.get("sourceFile"):
                rows.append({
                    "kind": "mission_runtime",
                    "sourceFile": consumer["sourceFile"],
                    "relationship": "typed_npc_proxy_tracking_consumer",
                })
    return _dedupe_source_rows(rows)


def _apply_npc_proxy_segment_mission_shell(
    row: dict[str, Any],
    context: dict[str, Any] | None,
) -> None:
    """Apply one unique script-local segment owner, reconciling other tiers."""
    if not context:
        return
    row["npcProxySegmentMissionShellContext"] = context
    mission_ids = [
        str(value)
        for value in context.get("hostMissionIds") or []
        if value
    ]
    if context.get("status") != "unique" or len(mission_ids) != 1:
        return
    owner = {
        "ownerKind": "npc_proxy_segment_script_mission_shell",
        "missionId": mission_ids[0],
        "levelId": row["levelId"],
        "scriptId": row["scriptId"],
        "taskId": row.get("taskId"),
        "conditionId": row["conditionId"],
        "proxyIds": sorted({
            str(host.get("proxyId") or "")
            for host in context.get("hosts") or []
            if host.get("proxyId")
        }),
        "sourceFiles": sorted({
            source["sourceFile"]
            for source in _npc_proxy_segment_source_rows(context)
        }),
        "classification": "exact_npc_proxy_segment_unique_mission_shell",
        "evidenceBoundary": (
            "A typed MissionRuntime NpcProxyTrackingInfo proxy and scene agree "
            "with the proxy's NpcProxyEx mission and the WorldEntityRegistry "
            "segmentIdGlobal equal to this exact LevelScript id. This proves "
            "script-local authored mission-shell context, not NPC activation, "
            "quest/task ownership, dialog activation, or Story order."
        ),
    }
    existing_owner = row.get("missionShellOwner")
    if (
        existing_owner
        and existing_owner.get("missionId") != owner["missionId"]
    ):
        raise AuditValidationError(
            "validator=dialog_finish_task_mission_shell_owner "
            "gate=independentOwnerAgreement "
            f"identity={row['levelId']}/{row['scriptId']}/"
            f"{row.get('taskId') or ''}/{row['conditionId']} "
            f"expected={existing_owner.get('missionId')!r} "
            f"actual={owner['missionId']!r} "
            f"source={owner['sourceFiles']!r}"
        )
    if not existing_owner:
        row["missionShellOwner"] = owner


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

    lifecycle = runtime.get("levelScriptTaskLifecycleAudit") or {}
    lifecycle_shape = {
        "schema": lifecycle.get("schema"),
        "status": (lifecycle.get("validation") or {}).get("status"),
        "classification": lifecycle.get("classification"),
        "states": lifecycle.get("scriptTaskStateEnum"),
        "taskTypes": lifecycle.get("levelScriptTaskTypeEnum"),
        "stateArgumentForwarding": lifecycle.get("stateArgumentForwarding"),
        "conditionProgressSender": lifecycle.get("conditionProgressSender"),
        "conditionIdentityFieldReads": lifecycle.get(
            "conditionIdentityFieldReads"
        ),
    }
    expected_lifecycle_shape = {
        "schema": "levelScriptTaskLifecycle.v1",
        "status": "validated",
        "classification": "generic_server_selected_task_condition_lifecycle",
        "states": {"None": 0, "Processing": 1, "Completed": 2},
        "taskTypes": {
            "None": 0,
            "Main": 1,
            "Extra": 2,
            "Fail": 3,
            "Custom": 4,
        },
        "stateArgumentForwarding": True,
        "conditionProgressSender": (
            "Beyond.Gameplay.GameplayNetwork.SendLevelScriptUpdateTaskProgress"
        ),
        "conditionIdentityFieldReads": [
            "levelScriptPtr",
            "levelNum",
            "taskKey",
            "conditionId",
        ],
    }
    if lifecycle_shape != expected_lifecycle_shape:
        raise AuditValidationError(
            f"validator={validator} gate=taskLifecycleShape "
            f"expected={expected_lifecycle_shape!r} "
            f"actual={lifecycle_shape!r} "
            f"source={lifecycle.get('source') or 'mission_pipeline/index.json'}"
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
    for label, contract in (
        ("task", task),
        ("lifecycle", lifecycle),
        ("activation", activation),
    ):
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
        "taskLifecycle": {
            "schema": lifecycle["schema"],
            "source": lifecycle.get("source") or "",
            "scriptTaskStateEnum": lifecycle["scriptTaskStateEnum"],
            "levelScriptTaskTypeEnum": lifecycle[
                "levelScriptTaskTypeEnum"
            ],
            "serverStateApplicationChain": lifecycle.get(
                "serverStateApplicationChain"
            ) or [],
            "processingConditionCallCount": lifecycle.get(
                "processingConditionCallCount"
            ),
            "conditionProcessingOperations": lifecycle.get(
                "conditionProcessingOperations"
            ) or [],
            "conditionProgressSender": lifecycle.get(
                "conditionProgressSender"
            ),
            "evidenceBoundary": lifecycle.get("boundary") or "",
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
        candidates: list[
            tuple[
                str | None,
                dict[str, Any],
                dict[str, Any],
                str,
                dict[str, Any] | None,
            ]
        ] = []
        for host in decode_levelscript_task_conditions(data, script_id):
            for task in host.get("tasks") or []:
                task_conditions = list(task.get("conditions") or [])
                condition_type_counts = Counter(
                    str((row.get("condition") or {}).get("type") or "<unknown>")
                    for row in task_conditions
                    if isinstance(row, dict)
                )
                task_summary = {
                    "taskType": task.get("taskType"),
                    "canBeTracked": task.get("canBeTracked"),
                    "needManualCheck": task.get("needManualCheck"),
                    "conditionCount": len(task_conditions),
                    "mainObjectiveConditionCount": sum(
                        row.get("isMainObjective") is True
                        for row in task_conditions
                        if isinstance(row, dict)
                    ),
                    "objectiveEnums": sorted({
                        int(row["objectiveEnum"])
                        for row in task_conditions
                        if isinstance(row, dict)
                        and isinstance(row.get("objectiveEnum"), int)
                        and not isinstance(row.get("objectiveEnum"), bool)
                    }),
                    "conditionTypeCounts": dict(sorted(condition_type_counts.items())),
                }
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
                            task_summary,
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
                (
                    None,
                    fragment,
                    condition,
                    "bounded_condition_fragment",
                    None,
                )
            )
        for (
            task_id,
            condition_row,
            condition,
            decode_status,
            task_summary,
        ) in candidates:
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
                "taskDefinition": task_summary,
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
    exact_tasks: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        task_id = str(row.get("taskId") or "")
        definition = row.get("taskDefinition")
        if not task_id or not isinstance(definition, dict):
            continue
        key = (row["levelId"], row["scriptId"], task_id)
        previous = exact_tasks.get(key)
        if previous is not None and previous != definition:
            raise AuditValidationError(
                "validator=dialog_finish_levelscript_task_consumer "
                "gate=stableTaskDefinition "
                f"identity={'/'.join(key)} expected={previous!r} "
                f"actual={definition!r} source={row['sourceFile']}"
            )
        exact_tasks[key] = definition
    task_type_counts = Counter(
        str(definition.get("taskType")) for definition in exact_tasks.values()
    )
    task_condition_type_counts: Counter[str] = Counter()
    for definition in exact_tasks.values():
        task_condition_type_counts.update(
            definition.get("conditionTypeCounts") or {}
        )
    return rows, {
        **overlay,
        "filesWithFinishConsumers": len(files_with_consumers),
        "finishConsumerCount": len(rows),
        "completeTaskMapConsumerCount": complete_rows,
        "boundedFragmentConsumerCount": fragment_rows,
        "resolvedTaskCount": len(exact_tasks),
        "unresolvedTaskIdentityConsumerCount": sum(
            not row.get("taskId") for row in rows
        ),
        "singleConditionResolvedTaskCount": sum(
            definition.get("conditionCount") == 1
            for definition in exact_tasks.values()
        ),
        "resolvedTaskTypeCounts": dict(sorted(task_type_counts.items())),
        "resolvedTaskConditionTypeCounts": dict(
            sorted(task_condition_type_counts.items())
        ),
        "resolvedTrackedTaskCount": sum(
            definition.get("canBeTracked") is True
            for definition in exact_tasks.values()
        ),
        "resolvedManualCheckTaskCount": sum(
            definition.get("needManualCheck") is True
            for definition in exact_tasks.values()
        ),
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


def _levelscript_task_consumer_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("levelId"),
        row.get("scriptId"),
        row.get("taskId"),
        row.get("conditionId") or row.get("taskConditionId"),
        row.get("dialogId"),
        row.get("finishId"),
    )


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


def _scan_exact_task_identity_carriers(
    consumers: Iterable[dict[str, Any]],
    roots: Iterable[Path] = DEFAULT_TASK_CARRIER_ROOTS,
) -> dict[str, Any]:
    """Find minimal typed objects that co-carry an exact script/task tuple.

    This is a general field-shape census.  It does not know table names,
    mission ids, script ids, or task ids in advance; the exact task identities
    come from the active LevelScript decoder.  LevelScriptData itself and the
    task-definition families are excluded because they define or label tasks
    rather than independently carrying runtime ownership. Every other active
    structured JSON family is admitted through the same minimal-object rule.
    """
    validator = "dialog_finish_exact_task_identity_carrier_census"
    identities = sorted({
        (str(row.get("scriptId") or ""), str(row.get("taskId") or ""))
        for row in consumers
        if row.get("scriptId") and row.get("taskId")
    })
    identity_set = set(identities)
    task_ids = {task_id for _script_id, task_id in identities}
    active: dict[str, Path] = {}
    root_rows: list[dict[str, Any]] = []
    scanned_families: set[str] = set()
    physical_files = 0
    shadowed_files = 0
    for priority, root in enumerate(roots):
        if not root.is_dir():
            raise AuditValidationError(
                f"validator={validator} gate=jsonRoot expected=directory "
                f"actual=missing source={root}"
            )
        root_count = 0
        for path in sorted(root.rglob("*.json")):
            relative_path = path.relative_to(root)
            family = (
                relative_path.parts[0]
                if root.name == "Json" and len(relative_path.parts) > 1
                else root.name
            )
            if family in TASK_CARRIER_DEFINITION_FAMILIES:
                continue
            if relative_path.name == "ScriptTaskExtraInfoTable.json":
                continue
            relative = relative_path.as_posix()
            logical_relative = (
                relative
                if root.name == "Json"
                else f"{root.name}/{relative}"
            )
            root_count += 1
            physical_files += 1
            scanned_families.add(family)
            if logical_relative in active:
                shadowed_files += 1
            active[logical_relative] = path
        root_rows.append({
            "priority": priority,
            "sourceRoot": source_label(root),
            "fileCount": root_count,
        })

    id_field_re = re.compile(r"(?:script|task|mission|quest)id$", re.I)

    def field_kind(name: str) -> str | None:
        normalized = re.sub(r"[^a-z0-9]", "", name.lower())
        match = id_field_re.search(normalized)
        if not match:
            return None
        for kind in ("script", "task", "mission", "quest"):
            if normalized.endswith(kind + "id"):
                return kind
        return None

    def scalar_text(value: Any) -> str | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (str, int)):
            return str(value)
        return None

    carrier_candidates: dict[
        tuple[str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    parsed_candidate_files = 0
    typed_json_files = 0
    non_json_files = 0
    rejected_candidate_files: list[dict[str, str]] = []
    task_id_pattern = re.compile(
        b"(?:" + b"|".join(
            re.escape(task_id.encode("ascii"))
            for task_id in sorted(task_ids)
        ) + b")"
    )
    for relative, path in sorted(active.items()):
        with path.open("rb") as handle:
            prefix = handle.read(64)
            json_prefix = prefix
            if json_prefix.startswith(b"\xef\xbb\xbf"):
                json_prefix = json_prefix[3:]
            if not json_prefix.lstrip().startswith((b"{", b"[")):
                non_json_files += 1
                continue
            data = prefix + handle.read()
        typed_json_files += 1
        if not task_id_pattern.search(data):
            continue
        digest = hashlib.sha256(data).hexdigest()
        try:
            payload = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            rejected_candidate_files.append({
                "sourceFile": source_label(path),
                "sourceSha256": digest,
                "gate": "jsonDecode",
                "diagnostic": str(exc),
            })
            continue
        parsed_candidate_files += 1

        def visit(value: Any, json_path: str) -> dict[str, list[dict[str, str]]]:
            collected: dict[str, list[dict[str, str]]] = defaultdict(list)
            if isinstance(value, dict):
                direct_values: dict[str, set[str]] = defaultdict(set)
                for key, child in value.items():
                    child_path = f"{json_path}/{key}"
                    kind = field_kind(str(key))
                    scalar = scalar_text(child)
                    if kind and scalar is not None:
                        direct_values[kind].add(scalar)
                        collected[kind].append({
                            "field": str(key),
                            "path": child_path,
                            "value": scalar,
                        })
                    child_rows = visit(child, child_path)
                    for child_kind, rows in child_rows.items():
                        collected[child_kind].extend(rows)
                script_values = {
                    row["value"] for row in collected.get("script", [])
                }
                task_values = {
                    row["value"] for row in collected.get("task", [])
                }
                for script_id, task_id in sorted(
                    identity_set & {
                        (script_id, task_id)
                        for script_id in script_values
                        for task_id in task_values
                    }
                ):
                    if (
                        script_id not in direct_values.get("script", set())
                        and task_id not in direct_values.get("task", set())
                    ):
                        continue
                    carrier_candidates[(relative, script_id, task_id)].append({
                        "jsonPath": json_path,
                        "depth": json_path.count("/"),
                        "runtimeType": str(value.get("$type") or "").split(
                            ",", 1
                        )[0],
                        "identityFields": {
                            kind: [
                                row
                                for row in rows
                                if (
                                    kind not in {"script", "task"}
                                    or row["value"]
                                    == (script_id if kind == "script" else task_id)
                                )
                            ]
                            for kind, rows in sorted(collected.items())
                            if kind in {"script", "task", "mission", "quest"}
                        },
                        "sourceFile": source_label(path),
                        "sourceSha256": digest,
                    })
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    child_rows = visit(child, f"{json_path}/{index}")
                    for child_kind, rows in child_rows.items():
                        collected[child_kind].extend(rows)
            return collected

        visit(payload, "$")

    carriers: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for (relative, script_id, task_id), candidates in sorted(
        carrier_candidates.items()
    ):
        max_depth = max(row["depth"] for row in candidates)
        minimal = [row for row in candidates if row["depth"] == max_depth]
        unique = {
            (row["jsonPath"], row["runtimeType"]): row for row in minimal
        }
        selected = list(unique.values())
        if len(selected) != 1:
            ambiguous.append({
                "relativePath": relative,
                "scriptId": script_id,
                "taskId": task_id,
                "candidates": selected,
            })
            continue
        row = selected[0]
        mission_values = sorted({
            field["value"]
            for field in (row["identityFields"].get("mission") or [])
        })
        quest_values = sorted({
            field["value"]
            for field in (row["identityFields"].get("quest") or [])
        })
        carriers.append({
            **{key: value for key, value in row.items() if key != "depth"},
            "relativePath": relative,
            "scriptId": script_id,
            "taskId": task_id,
            "missionIds": mission_values,
            "questIds": quest_values,
            "classification": (
                "mission_script_task_co_carrier"
                if mission_values
                else "script_task_co_carrier"
            ),
        })
    carriers.sort(
        key=lambda row: (
            row["scriptId"],
            row["taskId"],
            row["relativePath"],
            row["jsonPath"],
        )
    )
    return {
        "schema": "exactTaskIdentityCarrierCensus.v2",
        "scope": sorted(scanned_families),
        "roots": root_rows,
        "overlayRule": "later root wins; Persistent overrides StreamingAssets",
        "physicalFileCount": physical_files,
        "activeLogicalFileCount": len(active),
        "typedJsonFileCount": typed_json_files,
        "nonJsonFileCount": non_json_files,
        "shadowedFileCount": shadowed_files,
        "resolvedTaskIdentityCount": len(identities),
        "parsedCandidateFileCount": parsed_candidate_files,
        "rejectedCandidateFileCount": len(rejected_candidate_files),
        "rejectedCandidateFiles": rejected_candidate_files,
        "carrierCount": len(carriers),
        "missionCarrierCount": sum(bool(row["missionIds"]) for row in carriers),
        "carriedTaskIdentityCount": len({
            (row["scriptId"], row["taskId"]) for row in carriers
        }),
        "un_carriedTaskIdentityCount": len(identity_set - {
            (row["scriptId"], row["taskId"]) for row in carriers
        }),
        "carriers": carriers,
        "ambiguousMinimalCarriers": ambiguous,
        "evidenceBoundary": (
            "Every active original structured JSON family except LevelScript task "
            "definitions is searched for minimal objects that structurally co-carry "
            "an exact decoded script/task tuple. A bounded prefix gate classifies "
            "typed JSON before full payload reads; serialized binary files are "
            "counted but cannot become carriers. "
            "Mission or quest identity is reported only when that same minimal object "
            "contains a typed id field. Names, numeric proximity, file order, OCR, and "
            "manual overrides never create a carrier. A carrier proves co-location, "
            "not runtime activation, Story ownership, branching, or order. Other "
            "binary-only object internals remain outside this typed-JSON census."
        ),
    }


def _leveldata_logical_relative(source_file: str) -> str:
    """Return the overlay-relative path below one LevelData family root."""
    normalized = str(source_file or "").replace("\\", "/")
    marker = "/LevelData/"
    if marker not in normalized:
        return ""
    return normalized.split(marker, 1)[1]


def _scan_leveldata_task_progress_carriers(
    consumers: list[dict[str, Any]],
    roots: tuple[Path, ...] = DEFAULT_LEVELDATA_ROOTS,
    levelscript_roots: tuple[Path, ...] = DEFAULT_LEVELSCRIPT_ROOTS,
    mission_runtime_roots: tuple[Path, ...] = DEFAULT_MISSION_RUNTIME_ROOTS,
    *,
    script_scope_references: dict[
        tuple[str, str], list[dict[str, Any]]
    ] | None = None,
    authoritative_shell_index: dict[tuple[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recover exact task-condition carriers inside serialized LevelData.

    The rule is corpus-wide and contains no mission, script, task, or filename
    exception. A carrier must be the target script's value in one completely
    framed member-22 ``LevelScriptBriefData`` dictionary and must contain both
    ``lt:p`` and ``lt:mp`` properties for the exact decoded task/condition.
    Mission shell ids come from the existing all-reference shell classifier;
    the task token and a mission-looking filename alone cannot create an owner.
    """
    validator = "dialog_finish_leveldata_task_progress_carrier_census"
    identities = sorted({
        (
            str(row.get("levelId") or ""),
            str(row.get("scriptId") or ""),
            str(row.get("taskId") or ""),
            str(row.get("conditionId") or ""),
        )
        for row in consumers
        if row.get("levelId")
        and str(row.get("scriptId") or "").isdigit()
        and row.get("taskId")
        and row.get("conditionId")
    })
    target_set = set(identities)
    targets_by_level: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for level_id, script_id, task_id, condition_id in identities:
        targets_by_level[level_id].append((script_id, task_id, condition_id))

    active_leveldata: dict[str, Path] = {}
    physical_files = 0
    shadowed_files = 0
    root_rows: list[dict[str, Any]] = []
    for priority, root in enumerate(roots):
        file_count = 0
        if root.is_dir():
            for path in sorted(root.rglob("*.json")):
                relative = path.relative_to(root).as_posix()
                physical_files += 1
                file_count += 1
                if relative in active_leveldata:
                    shadowed_files += 1
                active_leveldata[relative] = path
        root_rows.append({
            "priority": priority,
            "sourceRoot": source_label(root),
            "fileCount": file_count,
        })

    active_levelscripts: dict[str, Path] = {}
    for root in levelscript_roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            active_levelscripts[path.relative_to(root).as_posix()] = path
    script_ids_by_level: dict[str, set[int]] = defaultdict(set)
    for relative in active_levelscripts:
        parts = Path(relative).parts
        if len(parts) == 2 and Path(parts[1]).stem.isdigit():
            script_ids_by_level[parts[0]].add(int(Path(parts[1]).stem))

    mission_runtime_ids = {
        path.stem
        for root in mission_runtime_roots
        if root.is_dir()
        for path in root.glob("*.json")
        if path.is_file() and path.stem
    }
    script_pairs = {(level_id, script_id) for level_id, script_id, _task, _cond in identities}
    if authoritative_shell_index is None:
        authoritative_shell_index = (
            build_leveldata_authoritative_scope_script_host_index(
                script_pairs,
                mission_runtime_ids,
                script_scope_references or {},
            )
        )
    shell_hosts: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (level_id, script_id), entry in authoritative_shell_index.items():
        for host in entry.get("hosts") or []:
            relative = _leveldata_logical_relative(
                str(host.get("levelDataFile") or "")
            )
            if relative:
                shell_hosts[(level_id, script_id, relative)] = host

    raw_candidate_files: set[str] = set()
    validated_dictionary_files: set[str] = set()
    rejected_candidates: list[dict[str, Any]] = []
    rejected_shell_classifications: list[dict[str, Any]] = []
    carriers: list[dict[str, Any]] = []
    for relative, path in sorted(active_leveldata.items()):
        parts = Path(relative).parts
        if len(parts) < 2:
            continue
        level_id = parts[0]
        targets = targets_by_level.get(level_id) or []
        if not targets:
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            rejected_candidates.append({
                "sourceFile": source_label(path),
                "gate": "readBytes",
                "diagnostic": f"{type(exc).__name__}: {exc}",
            })
            continue
        raw_targets = [
            target
            for target in targets
            if target[1].encode("utf-8") in data
        ]
        if not raw_targets:
            continue
        raw_candidate_files.add(relative)
        candidate_script_ids = script_ids_by_level.get(level_id) or set()
        dictionary = parse_leveldata_levelscript_brief_dictionary(
            data,
            candidate_script_ids,
        )
        if not dictionary:
            rejected_candidates.append({
                "sourceFile": source_label(path),
                "gate": "completeMember22Dictionary",
                "expected": {
                    "levelId": level_id,
                    "candidateScriptCount": len(candidate_script_ids),
                },
                "actual": {"dictionaryEntryCount": 0},
                "sourceSha256": hashlib.sha256(data).hexdigest(),
            })
            continue
        validated_dictionary_files.add(relative)
        source_sha256 = hashlib.sha256(data).hexdigest()
        for script_id, task_id, condition_id in raw_targets:
            brief = dictionary.get(int(script_id))
            if not brief:
                continue
            expected_progress = f"lt:p:{task_id}:{condition_id}"
            expected_max_progress = f"lt:mp:{task_id}:{condition_id}"
            property_names = {
                str(row.get("name") or "")
                for row in brief.get("properties") or []
                if isinstance(row, dict)
            }
            if not {expected_progress, expected_max_progress}.issubset(property_names):
                continue
            shell = shell_hosts.get((level_id, script_id, relative)) or {}
            if shell:
                expected_shell_shape = {
                    "dictionaryScriptIds": sorted(
                        (str(value) for value in dictionary),
                        key=int,
                    ),
                    "targetDataPathHash": str(brief.get("dataPathHash") or ""),
                }
                shell_brief = shell.get("targetBriefData") or {}
                actual_shell_shape = {
                    "dictionaryScriptIds": shell.get("dictionaryScriptIds") or [],
                    "targetDataPathHash": str(
                        shell_brief.get("dataPathHash") or ""
                    ),
                }
                if actual_shell_shape != expected_shell_shape:
                    rejected_shell_classifications.append({
                        "sourceFile": source_label(path),
                        "gate": "activeOverlayAgreement",
                        "identity": {
                            "levelId": level_id,
                            "scriptId": script_id,
                            "taskId": task_id,
                            "conditionId": condition_id,
                        },
                        "expected": expected_shell_shape,
                        "actual": actual_shell_shape,
                        "sourceSha256": source_sha256,
                    })
                    shell = {}
            mission_ids = sorted({
                str(value)
                for value in shell.get("hostMissionIds") or []
                if value
            })
            carriers.append({
                "levelId": level_id,
                "scriptId": script_id,
                "taskId": task_id,
                "conditionId": condition_id,
                "sourceFile": source_label(path),
                "sourceSha256": source_sha256,
                "relativePath": relative,
                "dictionaryEntryCount": len(dictionary),
                "briefKeyOffset": int(brief["keyOffset"]),
                "briefEndOffset": int(brief["endOffset"]),
                "progressProperties": [
                    expected_progress,
                    expected_max_progress,
                ],
                "missionIds": mission_ids,
                "missionShellStatus": (
                    "unique" if len(mission_ids) == 1
                    else "shared" if mission_ids
                    else "unresolved"
                ),
                "authoritativeReferences": shell.get(
                    "authoritativeReferences"
                ) or [],
                "classification": (
                    "leveldata_task_progress_unique_mission_shell"
                    if len(mission_ids) == 1
                    else "leveldata_task_progress_shared_mission_shell"
                    if mission_ids
                    else "leveldata_task_progress_carrier"
                ),
            })

    carriers.sort(key=lambda row: (
        row["levelId"],
        int(row["scriptId"]),
        row["taskId"],
        row["conditionId"],
        row["relativePath"],
    ))
    carried = {
        (row["levelId"], row["scriptId"], row["taskId"], row["conditionId"])
        for row in carriers
    }
    missions_by_task_identity: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    carriers_by_task_identity: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in carriers:
        key = (row["levelId"], row["scriptId"], row["taskId"])
        missions_by_task_identity[key].update(row["missionIds"])
        carriers_by_task_identity[key].append(row)
    unique_owned_identities = {
        key for key, values in missions_by_task_identity.items() if len(values) == 1
    }
    shared_identities = {
        key for key, values in missions_by_task_identity.items() if len(values) > 1
    }
    return {
        "schema": "levelDataTaskProgressCarrierCensus.v1",
        "roots": root_rows,
        "overlayRule": "later root wins; Persistent overrides StreamingAssets",
        "physicalFileCount": physical_files,
        "activeLogicalFileCount": len(active_leveldata),
        "shadowedFileCount": shadowed_files,
        "taskConditionIdentityCount": len(target_set),
        "taskIdentityCount": len({identity[:3] for identity in target_set}),
        "rawCandidateFileCount": len(raw_candidate_files),
        "validatedDictionaryCandidateFileCount": len(validated_dictionary_files),
        "carrierCount": len(carriers),
        "carriedTaskConditionIdentityCount": len(carried),
        "carriedTaskIdentityCount": len(carriers_by_task_identity),
        "uniqueMissionShellTaskIdentityCount": len(unique_owned_identities),
        "sharedMissionShellTaskIdentityCount": len(shared_identities),
        "unresolvedMissionShellTaskIdentityCount": (
            len(carriers_by_task_identity)
            - len(unique_owned_identities)
            - len(shared_identities)
        ),
        "un_carriedTaskConditionIdentityCount": len(target_set - carried),
        "rejectedCandidateFileCount": len(rejected_candidates),
        "rejectedCandidateFiles": rejected_candidates,
        "rejectedShellClassificationCount": len(
            rejected_shell_classifications
        ),
        "rejectedShellClassifications": rejected_shell_classifications,
        "carriers": carriers,
        "evidenceBoundary": (
            "A carrier is accepted only when a complete original LevelData/43 "
            "member-22 dictionary places both exact lt:p and lt:mp properties "
            "inside the decoded script's LevelScriptBriefData entry. Mission "
            "shell identity is inherited only from the complete independent "
            "authoritative-reference set for that same LevelData shell and is "
            "unique only when that set names one mission. This proves persistent "
            "task-condition placement and mission-shell context, not activation, "
            "quest ownership, branch choice, or Story-file order. OCR and manual "
            "overrides are not read."
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
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Validate option routes and finish endpoints over every DialogTree."""
    if not root.is_dir():
        raise AuditValidationError(
            "validator=dialog_finish_branch_recovery gate=dialogTreeCorpusRoot "
            f"expected=directory actual=missing source={root}"
        )
    coverage_sources: list[dict[str, Any]] = []
    finish_endpoint_sources: list[dict[str, Any]] = []
    validated_finish_endpoint_rows: list[dict[str, Any]] = []
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
        dialog_id = str(outer.get("m_Name") or outer.get("Name") or "").strip()
        if dialog_id:
            rows, _rejected = _validated_finish_endpoint_rows(
                dialog_id,
                finish_endpoints,
                source_file=source_label(path),
            )
            validated_finish_endpoint_rows.extend(rows)
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
    validated_finish_endpoint_rows.sort(
        key=lambda row: (
            row["dialogId"],
            row["finishId"],
            row.get("finishNodeOrdinal") or 0,
            (row.get("sourceFiles") or [{}])[0].get("sourceFile") or "",
        )
    )
    return route_summary, endpoint_summary, validated_finish_endpoint_rows


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
    consumers, any_finish_mission_consumers, payloads = _collect_mission_consumers(
        index,
        pipeline_root,
    )
    mission_levelscript_contexts = _collect_mission_levelscript_contexts(payloads)
    levelscript_consumers, levelscript_census = (
        _collect_levelscript_task_finish_consumers(levelscript_roots)
    )
    task_type_names = {
        int(value): str(name)
        for name, value in (
            levelscript_runtime_contract["taskLifecycle"][
                "levelScriptTaskTypeEnum"
            ]
        ).items()
    }
    for row in levelscript_consumers:
        definition = row.get("taskDefinition")
        if not isinstance(definition, dict):
            continue
        task_type = definition.get("taskType")
        definition["taskTypeName"] = (
            task_type_names.get(task_type)
            if isinstance(task_type, int) and not isinstance(task_type, bool)
            else None
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
    (
        corpus_route_coverage,
        corpus_finish_endpoint_coverage,
        corpus_finish_endpoint_rows,
    ) = (
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
    task_identity_carrier_census = _scan_exact_task_identity_carriers(
        exact_levelscript_consumers
    )
    levelscript_scope_references: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for context in mission_levelscript_contexts:
        levelscript_scope_references[
            (context["levelId"], context["scriptId"])
        ].append({
            "missionId": context["missionId"],
            "questId": context["questId"],
            "conditionId": context["missionConditionId"],
            "conditionType": context["missionConditionType"],
            "scopeKind": "exact_mission_runtime_levelscript_condition",
            "sourceFile": context["missionSource"],
        })
    leveldata_task_progress_census = _scan_leveldata_task_progress_carriers(
        exact_levelscript_consumers,
        script_scope_references=levelscript_scope_references,
    )
    npc_proxy_tracking_consumers = (
        _collect_mission_npc_proxy_tracking_consumers()
    )
    npc_proxy_segment_contexts = build_npc_proxy_segment_script_host_index(
        {
            (row["levelId"], row["scriptId"])
            for row in exact_levelscript_consumers
        },
        npc_proxy_tracking_consumers,
    )
    npc_proxy_segment_census = {
        "status": "validated",
        "targetScriptCount": len({
            (row["levelId"], row["scriptId"])
            for row in exact_levelscript_consumers
        }),
        "typedTrackingConsumerCount": sum(
            len(rows) for rows in npc_proxy_tracking_consumers.values()
        ),
        "typedTrackingProxyCount": len(npc_proxy_tracking_consumers),
        "matchedScriptCount": len(npc_proxy_segment_contexts),
        "uniqueMissionShellScriptCount": sum(
            context.get("status") == "unique"
            for context in npc_proxy_segment_contexts.values()
        ),
        "sharedMissionShellScriptCount": sum(
            context.get("status") == "shared"
            for context in npc_proxy_segment_contexts.values()
        ),
        "contexts": [
            context
            for _identity, context in sorted(npc_proxy_segment_contexts.items())
        ],
        "evidenceBoundary": (
            "The generic join requires a typed MissionRuntime "
            "NpcProxyTrackingInfo proxy in the exact scene, an authored "
            "NpcProxyEx mission for that proxy, and a WorldEntityRegistry "
            "segmentIdGlobal identical to the LevelScript global id. A unique "
            "result is script-local mission-shell context only; shared results "
            "remain ambiguous, and neither class proves activation or order."
        ),
    }
    task_identity_carriers = defaultdict(list)
    for carrier in task_identity_carrier_census.get("carriers") or []:
        task_identity_carriers[
            (carrier["scriptId"], carrier["taskId"])
        ].append(carrier)
    leveldata_progress_carriers: dict[
        tuple[str, str, str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for carrier in leveldata_task_progress_census.get("carriers") or []:
        leveldata_progress_carriers[
            (
                carrier["levelId"],
                carrier["scriptId"],
                carrier["taskId"],
                carrier["conditionId"],
            )
        ].append(carrier)
    levelscript_by_finish: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in exact_levelscript_consumers:
        if row.get("taskId"):
            row["externalTaskIdentityCarriers"] = task_identity_carriers.get(
                (row["scriptId"], row["taskId"]),
                [],
            )
            row["levelDataTaskProgressCarriers"] = (
                leveldata_progress_carriers.get(
                    (
                        row["levelId"],
                        row["scriptId"],
                        row["taskId"],
                        row["conditionId"],
                    ),
                    [],
                )
            )
        subgame_owner = (
            subgame_task_owners.get((row["scriptId"], row["taskId"]))
            if row.get("taskId")
            else None
        )
        if subgame_owner:
            row["missionShellOwner"] = {
                **subgame_owner,
                "ownerKind": "subgame_exact_script_task_carrier",
            }
        _apply_npc_proxy_segment_mission_shell(
            row,
            npc_proxy_segment_contexts.get(
                (row["levelId"], row["scriptId"])
            ),
        )
        leveldata_carriers = row.get("levelDataTaskProgressCarriers") or []
        leveldata_mission_ids = sorted({
            mission_id
            for carrier in leveldata_carriers
            for mission_id in carrier.get("missionIds") or []
            if mission_id
        })
        if len(leveldata_mission_ids) == 1:
            leveldata_owner = {
                "ownerKind": "leveldata_task_progress_mission_shell",
                "missionId": leveldata_mission_ids[0],
                "levelId": row["levelId"],
                "scriptId": row["scriptId"],
                "taskId": row["taskId"],
                "conditionId": row["conditionId"],
                "sourceFile": leveldata_carriers[0]["sourceFile"],
                "sourceFiles": sorted({
                    carrier["sourceFile"] for carrier in leveldata_carriers
                }),
                "progressProperties": sorted({
                    value
                    for carrier in leveldata_carriers
                    for value in carrier.get("progressProperties") or []
                }),
                "classification": (
                    "exact_leveldata_task_progress_unique_mission_shell"
                ),
                "evidenceBoundary": (
                    leveldata_task_progress_census["evidenceBoundary"]
                ),
            }
            existing_owner = row.get("missionShellOwner")
            if (
                existing_owner
                and existing_owner.get("missionId")
                != leveldata_owner["missionId"]
            ):
                raise AuditValidationError(
                    "validator=dialog_finish_task_mission_shell_owner "
                    "gate=independentOwnerAgreement "
                    f"identity={row['levelId']}/{row['scriptId']}/"
                    f"{row['taskId']}/{row['conditionId']} "
                    f"expected={existing_owner.get('missionId')!r} "
                    f"actual={leveldata_owner['missionId']!r} "
                    f"source={leveldata_owner['sourceFile']!r}"
                )
            if not existing_owner:
                row["missionShellOwner"] = leveldata_owner
        elif leveldata_mission_ids:
            row["levelDataMissionShellAmbiguity"] = {
                "missionIds": leveldata_mission_ids,
                "sourceFiles": sorted({
                    carrier["sourceFile"] for carrier in leveldata_carriers
                }),
                "status": "shared",
            }
        levelscript_by_finish[(row["dialogId"], row["finishId"])].append(row)

    corpus_endpoints_by_finish: dict[
        tuple[str, int], list[dict[str, Any]]
    ] = defaultdict(list)
    for endpoint in corpus_finish_endpoint_rows:
        finish_id = endpoint.get("finishId")
        if isinstance(finish_id, int) and finish_id >= 0:
            corpus_endpoints_by_finish[
                (str(endpoint.get("dialogId") or ""), finish_id)
            ].append(endpoint)

    task_finish_dependencies: list[dict[str, Any]] = []
    unresolved_task_finish_endpoints: list[dict[str, Any]] = []
    for task_consumer in exact_levelscript_consumers:
        endpoint_matches = corpus_endpoints_by_finish.get(
            (task_consumer["dialogId"], task_consumer["finishId"]),
            [],
        )
        if not endpoint_matches:
            unresolved_task_finish_endpoints.append(task_consumer)
            continue
        source_rows = [
            source
            for endpoint in endpoint_matches
            for source in endpoint.get("sourceFiles") or []
        ]
        source_rows.append({
            "kind": "level_script",
            "sourceFile": task_consumer["sourceFile"],
            "relationship": "exact_dialog_finish_task_consumer_active_overlay",
        })
        for carrier in task_consumer.get("externalTaskIdentityCarriers") or []:
            source_rows.append({
                "kind": "structured_task_identity_carrier",
                "sourceFile": carrier["sourceFile"],
                "relationship": carrier["classification"],
            })
        for carrier in task_consumer.get("levelDataTaskProgressCarriers") or []:
            source_rows.append({
                "kind": "level_data",
                "sourceFile": carrier["sourceFile"],
                "relationship": carrier["classification"],
            })
        source_rows.extend(_npc_proxy_segment_source_rows(
            task_consumer.get("npcProxySegmentMissionShellContext")
        ))
        source_rows.extend(binary_files)
        owner = task_consumer.get("missionShellOwner")
        if owner:
            if owner.get("ownerKind") == "subgame_exact_script_task_carrier":
                source_rows.append({
                    "kind": "subgame_instance_table",
                    "sourceFile": owner["sourceFile"],
                    "relationship": "exact_mission_script_task_co_carrier",
                })
        dependency = {
            **task_consumer,
            "taskConditionId": task_consumer["conditionId"],
            "classification": "authored_finish_endpoint_to_levelscript_task",
            "producerFamilies": [
                "dialog_tree_prime_reachable_finish_endpoint"
            ],
            "producerEvidence": endpoint_matches,
            "missionShellOwner": owner,
            "missionOwnershipStatus": (
                "exact_subgame_script_task_carrier"
                if owner
                and owner.get("ownerKind")
                == "subgame_exact_script_task_carrier"
                else "exact_npc_proxy_segment_script_mission_shell"
                if owner
                and owner.get("ownerKind")
                == "npc_proxy_segment_script_mission_shell"
                else "exact_leveldata_task_progress_mission_shell"
                if owner
                else "unresolved"
            ),
            "relatedOriginalFiles": _hash_source_rows(
                source_rows,
                hash_cache,
                validator=validator,
            ),
            "evidenceBoundary": (
                "A finish node is reachable from the binary-proven serialized "
                "DialogTree prime node and emits the exact value consumed by this "
                "original LevelScript task condition. This proves an authored "
                "Story-finish-to-task dependency, not the route or player choice "
                "that reaches the endpoint, task activation, or cross-file "
                "chronology. Any displayed mission shell is a separate exact "
                "carrier classification and does not establish quest ownership."
            ),
        }
        task_finish_dependencies.append(dependency)
    task_finish_dependencies.sort(
        key=lambda row: (
            row["dialogId"],
            row["finishId"],
            row["levelId"],
            int(row["scriptId"]),
            row.get("taskId") or "",
            row["taskConditionId"],
        )
    )

    any_finish_by_dialog: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for consumer in any_finish_mission_consumers:
        any_finish_by_dialog[consumer["dialogId"]].append(consumer)
    any_finish_task_contexts: list[dict[str, Any]] = []
    for task_dependency in task_finish_dependencies:
        for mission_context in any_finish_by_dialog.get(
            task_dependency["dialogId"],
            [],
        ):
            source_rows = list(task_dependency.get("relatedOriginalFiles") or [])
            if mission_context["missionSource"]:
                source_rows.append({
                    "kind": "mission_runtime",
                    "sourceFile": mission_context["missionSource"],
                    "relationship": "same_dialog_any_finish_consumer",
                })
            any_finish_task_contexts.append({
                **{
                    key: task_dependency.get(key)
                    for key in (
                        "dialogId",
                        "finishId",
                        "levelId",
                        "scriptId",
                        "taskId",
                        "taskConditionId",
                        "taskMapDecodeStatus",
                        "taskIdentityStatus",
                        "conditionOffsetHex",
                    )
                },
                "missionId": mission_context["missionId"],
                "questId": mission_context["questId"],
                "objectiveIndex": mission_context["objectiveIndex"],
                "missionConditionId": mission_context["conditionId"],
                "missionFinishId": -1,
                "predicateRelation": (
                    "exact_task_finish_satisfies_mission_any_finish"
                ),
                "classification": (
                    "mission_any_finish_and_exact_levelscript_task_context"
                ),
                "missionOwnershipStatus": "unresolved",
                "relatedOriginalFiles": _hash_source_rows(
                    source_rows,
                    hash_cache,
                    validator=validator,
                ),
                "evidenceBoundary": (
                    "The hash-validated CheckTalkOptionFinish.Check body proves "
                    "that a negative MissionRuntime operand accepts any recorded "
                    "finish while this LevelScript task requires the displayed "
                    "exact finish. The exact task outcome therefore satisfies both "
                    "observers. This is mission dialog context, not proof that the "
                    "mission activates or owns the script/task, and not Story order."
                ),
            })
    any_finish_task_contexts.sort(
        key=lambda row: (
            row["missionId"],
            row["questId"],
            row.get("objectiveIndex") or 0,
            row["dialogId"],
            row["finishId"],
            row["levelId"],
            int(row["scriptId"]),
        )
    )

    mission_script_contexts_by_identity: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for context in mission_levelscript_contexts:
        mission_script_contexts_by_identity[
            (context["levelId"], context["scriptId"])
        ].append(context)
    mission_script_task_contexts: list[dict[str, Any]] = []
    for task_dependency in task_finish_dependencies:
        for mission_context in mission_script_contexts_by_identity.get(
            (task_dependency["levelId"], task_dependency["scriptId"]),
            [],
        ):
            actual_source = source_label(resolve_source(task_dependency["sourceFile"]))
            expected_source = source_label(
                resolve_source(mission_context["activeLevelScriptSourceFile"])
            )
            actual_hash = str(task_dependency.get("sourceSha256") or "")
            expected_hash = str(mission_context["activeLevelScriptSha256"])
            if actual_source != expected_source or actual_hash != expected_hash:
                raise AuditValidationError(
                    "validator=dialog_finish_mission_levelscript_context "
                    "gate=activeOverlayAgreement "
                    f"mission={mission_context['missionId']} "
                    f"quest={mission_context['questId']} "
                    f"identity={task_dependency['levelId']}/{task_dependency['scriptId']} "
                    f"expected={{'source':{expected_source!r},'sha256':{expected_hash!r}}} "
                    f"actual={{'source':{actual_source!r},'sha256':{actual_hash!r}}}"
                )
            source_rows = list(task_dependency.get("relatedOriginalFiles") or [])
            if mission_context["missionSource"]:
                source_rows.append({
                    "kind": "mission_runtime",
                    "sourceFile": mission_context["missionSource"],
                    "relationship": "exact_levelscript_condition_operand",
                })
            mission_script_task_contexts.append({
                **{
                    key: task_dependency.get(key)
                    for key in (
                        "dialogId",
                        "finishId",
                        "levelId",
                        "scriptId",
                        "taskId",
                        "taskConditionId",
                        "taskMapDecodeStatus",
                        "taskIdentityStatus",
                        "conditionOffsetHex",
                    )
                },
                "missionId": mission_context["missionId"],
                "questId": mission_context["questId"],
                "objectiveIndex": mission_context["objectiveIndex"],
                "missionConditionId": mission_context["missionConditionId"],
                "missionConditionType": mission_context[
                    "missionConditionType"
                ],
                "classification": "mission_exact_levelscript_context",
                "missionOwnershipStatus": "script_context_only",
                "levelScriptOverlay": mission_context["levelScriptOverlay"],
                "relatedOriginalFiles": _hash_source_rows(
                    source_rows,
                    hash_cache,
                    validator=validator,
                ),
                "evidenceBoundary": (
                    "This MissionRuntime objective references the exact active "
                    "LevelScript that contains the displayed task finish consumer. "
                    "It proves a mission-to-script observation context, not that "
                    "the mission starts the script, owns this task or dialog, "
                    "selects the finish outcome, or orders Story files."
                ),
            })
    mission_script_task_contexts.sort(
        key=lambda row: (
            row["missionId"],
            row["questId"],
            row.get("objectiveIndex") or 0,
            row["levelId"],
            int(row["scriptId"]),
            row.get("taskId") or "",
            row["taskConditionId"],
        )
    )

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
                if owner.get("ownerKind") == "subgame_exact_script_task_carrier":
                    source_rows.append({
                        "kind": "subgame_instance_table",
                        "sourceFile": owner["sourceFile"],
                        "relationship": "exact_mission_script_task_co_carrier",
                    })
            for carrier in task_consumer.get(
                "externalTaskIdentityCarriers"
            ) or []:
                source_rows.append({
                    "kind": "structured_task_identity_carrier",
                    "sourceFile": carrier["sourceFile"],
                    "relationship": carrier["classification"],
                })
            for carrier in task_consumer.get(
                "levelDataTaskProgressCarriers"
            ) or []:
                source_rows.append({
                    "kind": "level_data",
                    "sourceFile": carrier["sourceFile"],
                    "relationship": carrier["classification"],
                })
            source_rows.extend(_npc_proxy_segment_source_rows(
                task_consumer.get("npcProxySegmentMissionShellContext")
            ))
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
                "taskDefinition": task_consumer.get("taskDefinition"),
                "externalTaskIdentityCarriers": task_consumer.get(
                    "externalTaskIdentityCarriers"
                ) or [],
                "levelDataTaskProgressCarriers": task_consumer.get(
                    "levelDataTaskProgressCarriers"
                ) or [],
                "npcProxySegmentMissionShellContext": task_consumer.get(
                    "npcProxySegmentMissionShellContext"
                ),
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
                    "when either one typed SubGame row co-carries the exact script "
                    "and task ids, one typed NpcProxy segment join identifies the "
                    "exact script in one mission shell, or one validated LevelData "
                    "task-progress entry belongs to a uniquely classified mission "
                    "shell. These remain shell contexts, not quest or activation "
                    "ownership."
                ),
            }
            shared_task_dependencies.append(row)
            matched_levelscript_signatures.add(
                _levelscript_task_consumer_signature(task_consumer)
            )
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
        if _levelscript_task_consumer_signature(row)
        not in matched_levelscript_signatures
    ]
    any_contexts_by_signature: dict[
        tuple[Any, ...], list[dict[str, Any]]
    ] = defaultdict(list)
    for context in any_finish_task_contexts:
        any_contexts_by_signature[
            _levelscript_task_consumer_signature(context)
        ].append(context)
    script_contexts_by_signature: dict[
        tuple[Any, ...], list[dict[str, Any]]
    ] = defaultdict(list)
    for context in mission_script_task_contexts:
        script_contexts_by_signature[
            _levelscript_task_consumer_signature(context)
        ].append(context)
    exact_contexts_by_signature: dict[
        tuple[Any, ...], list[dict[str, Any]]
    ] = defaultdict(list)
    for context in shared_task_dependencies:
        exact_contexts_by_signature[
            _levelscript_task_consumer_signature(context)
        ].append(context)
    for dependency in task_finish_dependencies:
        signature = _levelscript_task_consumer_signature(dependency)
        dependency["missionContextSummary"] = {
            "exactFinishPlacements": len(exact_contexts_by_signature[signature]),
            "anyFinishPlacements": len(any_contexts_by_signature[signature]),
            "exactScriptPlacements": len(script_contexts_by_signature[signature]),
            "missionIds": sorted({
                row["missionId"]
                for row in [
                    *exact_contexts_by_signature[signature],
                    *any_contexts_by_signature[signature],
                    *script_contexts_by_signature[signature],
                ]
            }),
        }
    mission_exact_unmatched_task_finish_dependencies = [
        dependency
        for dependency in task_finish_dependencies
        if _levelscript_task_consumer_signature(dependency)
        not in matched_levelscript_signatures
    ]
    report = {
        "schemaVersion": "dialogFinishMissionBranchAudit.v10",
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
            "conditions are joined to prime-reachable authored finish endpoints "
            "across the full corpus. Exact MissionRuntime matches, any-finish "
            "observers, and exact mission-to-script references remain separate "
            "evidence tiers. The current binary validates the generic server-state "
            "application and Processing-time condition activation/reporting lifecycle. "
            "A field-shape census independently reports minimal exact script/task "
            "co-carriers across every active typed structured-JSON family outside "
            "LevelScript definitions. A second generic census requires paired "
            "lt:p/lt:mp properties inside the exact script entry of a completely "
            "framed LevelData member-22 dictionary, then admits a mission shell "
            "only from that shell's complete independent reference set. A third "
            "generic join requires a typed MissionRuntime NpcProxyTrackingInfo "
            "proxy and scene, an authored NpcProxyEx mission, and an identical "
            "WorldEntityRegistry segmentIdGlobal/LevelScript id; only a unique "
            "script-local mission set becomes shell context. These "
            "tiers do not infer server selection policy, task activation in a "
            "particular session, quest ownership, branch choice, or cross-file order. "
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
            "anyFinishMissionConsumers": len(any_finish_mission_consumers),
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
            "levelScriptTaskExactCompleteMapConsumers": sum(
                row["taskMapDecodeStatus"] == "complete_task_map"
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskExactBoundedFragmentConsumers": sum(
                row["taskMapDecodeStatus"] == "bounded_condition_fragment"
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskAnyFinishConsumers": sum(
                row["finishId"] < 0 for row in levelscript_consumers
            ),
            "levelScriptTaskAuthoredFinishDependencies": len(
                task_finish_dependencies
            ),
            "levelScriptTaskUnresolvedAuthoredFinishEndpoints": len(
                unresolved_task_finish_endpoints
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
            "levelScriptTaskSubGameMissionShellOwners": sum(
                (row.get("missionShellOwner") or {}).get("ownerKind")
                == "subgame_exact_script_task_carrier"
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskLevelDataMissionShellOwners": sum(
                (row.get("missionShellOwner") or {}).get("ownerKind")
                == "leveldata_task_progress_mission_shell"
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskNpcProxyMissionShellOwners": sum(
                (row.get("missionShellOwner") or {}).get("ownerKind")
                == "npc_proxy_segment_script_mission_shell"
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskNpcProxyCorroboratedLevelDataOwners": sum(
                (row.get("missionShellOwner") or {}).get("ownerKind")
                == "npc_proxy_segment_script_mission_shell"
                and len({
                    mission_id
                    for carrier in row.get("levelDataTaskProgressCarriers") or []
                    for mission_id in carrier.get("missionIds") or []
                    if mission_id
                }) == 1
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskNpcProxyRefinedAmbiguousLevelDataOwners": sum(
                (row.get("missionShellOwner") or {}).get("ownerKind")
                == "npc_proxy_segment_script_mission_shell"
                and len({
                    mission_id
                    for carrier in row.get("levelDataTaskProgressCarriers") or []
                    for mission_id in carrier.get("missionIds") or []
                    if mission_id
                }) != 1
                for row in exact_levelscript_consumers
            ),
            "levelScriptTaskSameMissionShellDependencies": sum(
                row["missionShellRelationship"] == "same_mission_shell"
                for row in shared_task_dependencies
            ),
            "levelScriptTaskUnmatchedExactConsumers": len(
                unmatched_levelscript_consumers
            ),
            "levelScriptTaskWithoutExactMissionFinishMatch": len(
                mission_exact_unmatched_task_finish_dependencies
            ),
            "levelScriptTaskAnyFinishMissionContexts": len(
                any_finish_task_contexts
            ),
            "levelScriptTaskAnyFinishMissionContextMissions": len({
                row["missionId"] for row in any_finish_task_contexts
            }),
            "levelScriptTaskMissionScriptContexts": len(
                mission_script_task_contexts
            ),
            "levelScriptTaskMissionScriptContextConsumers": len({
                _levelscript_task_consumer_signature(row)
                for row in mission_script_task_contexts
            }),
            "levelScriptTaskMissionScriptContextMissions": len({
                row["missionId"] for row in mission_script_task_contexts
            }),
            "levelScriptTaskResolvedExactTaskIdentities": (
                task_identity_carrier_census["resolvedTaskIdentityCount"]
            ),
            "levelScriptTaskExternalIdentityCarriers": (
                task_identity_carrier_census["carrierCount"]
            ),
            "levelScriptTaskExternalMissionCarriers": (
                task_identity_carrier_census["missionCarrierCount"]
            ),
            "levelScriptTaskExternalUncarriedIdentities": (
                task_identity_carrier_census["un_carriedTaskIdentityCount"]
            ),
            "levelScriptTaskCarrierActiveLogicalFiles": (
                task_identity_carrier_census["activeLogicalFileCount"]
            ),
            "levelScriptTaskCarrierTypedJsonCandidates": (
                task_identity_carrier_census["parsedCandidateFileCount"]
            ),
            "levelScriptTaskCarrierTypedJsonFiles": (
                task_identity_carrier_census["typedJsonFileCount"]
            ),
            "levelScriptTaskCarrierNonJsonFiles": (
                task_identity_carrier_census["nonJsonFileCount"]
            ),
            "levelScriptTaskLevelDataRawCandidateFiles": (
                leveldata_task_progress_census["rawCandidateFileCount"]
            ),
            "levelScriptTaskLevelDataProgressCarriers": (
                leveldata_task_progress_census["carrierCount"]
            ),
            "levelScriptTaskLevelDataCarriedIdentities": (
                leveldata_task_progress_census["carriedTaskIdentityCount"]
            ),
            "levelScriptTaskLevelDataUniqueMissionShellIdentities": (
                leveldata_task_progress_census[
                    "uniqueMissionShellTaskIdentityCount"
                ]
            ),
            "levelScriptTaskLevelDataSharedMissionShellIdentities": (
                leveldata_task_progress_census[
                    "sharedMissionShellTaskIdentityCount"
                ]
            ),
            "levelScriptTaskLevelDataUnresolvedMissionShellIdentities": (
                leveldata_task_progress_census[
                    "unresolvedMissionShellTaskIdentityCount"
                ]
            ),
            "levelScriptTaskLevelDataUncarriedConditions": (
                leveldata_task_progress_census[
                    "un_carriedTaskConditionIdentityCount"
                ]
            ),
            "levelScriptTaskLevelDataRejectedShellClassifications": (
                leveldata_task_progress_census[
                    "rejectedShellClassificationCount"
                ]
            ),
            "levelScriptTaskNpcProxyTrackingConsumers": (
                npc_proxy_segment_census["typedTrackingConsumerCount"]
            ),
            "levelScriptTaskNpcProxyTrackingProxies": (
                npc_proxy_segment_census["typedTrackingProxyCount"]
            ),
            "levelScriptTaskNpcProxyMatchedScripts": (
                npc_proxy_segment_census["matchedScriptCount"]
            ),
            "levelScriptTaskNpcProxyUniqueMissionShellScripts": (
                npc_proxy_segment_census["uniqueMissionShellScriptCount"]
            ),
            "levelScriptTaskNpcProxySharedMissionShellScripts": (
                npc_proxy_segment_census["sharedMissionShellScriptCount"]
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
            "unresolvedAuthoredFinishEndpoints": (
                unresolved_task_finish_endpoints
            ),
        },
        "subGameTaskOwnerCensus": subgame_owner_census,
        "exactTaskIdentityCarrierCensus": task_identity_carrier_census,
        "levelDataTaskProgressCarrierCensus": leveldata_task_progress_census,
        "npcProxySegmentMissionShellCensus": npc_proxy_segment_census,
        "dependencies": dependencies,
        "endpointDependencies": endpoint_dependencies,
        "levelScriptTaskAuthoredFinishDependencies": task_finish_dependencies,
        "levelScriptTaskSharedConsumerDependencies": shared_task_dependencies,
        "levelScriptTaskAnyFinishMissionContexts": any_finish_task_contexts,
        "levelScriptTaskMissionScriptContexts": mission_script_task_contexts,
        "levelScriptTaskWithoutExactMissionFinishMatch": (
            mission_exact_unmatched_task_finish_dependencies
        ),
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
    any_finish_task_by_quest: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in report.get("levelScriptTaskAnyFinishMissionContexts") or []:
        any_finish_task_by_quest[(row["missionId"], row["questId"])].append(row)
    mission_script_task_by_quest: dict[
        tuple[str, str], list[dict[str, Any]]
    ] = defaultdict(list)
    for row in report.get("levelScriptTaskMissionScriptContexts") or []:
        mission_script_task_by_quest[
            (row["missionId"], row["questId"])
        ].append(row)
    authored_task_shell_by_mission: dict[str, list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for row in report.get("levelScriptTaskAuthoredFinishDependencies") or []:
        owner = row.get("missionShellOwner")
        if isinstance(owner, dict) and owner.get("missionId"):
            authored_task_shell_by_mission[str(owner["missionId"])].append(row)
    published = 0
    published_endpoints = 0
    published_task_dependencies = 0
    published_owned_task_dependencies = 0
    published_any_finish_task_contexts = 0
    published_mission_script_task_contexts = 0
    published_authored_task_shell_dependencies = 0
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
        mission_any_finish_task_rows: list[dict[str, Any]] = []
        mission_script_task_rows: list[dict[str, Any]] = []
        mission_authored_task_shell_rows = authored_task_shell_by_mission.get(
            mission_id,
            [],
        )
        payload.pop("dialogFinishAuthoredTaskShellDependencies", None)
        if mission_authored_task_shell_rows:
            payload["dialogFinishAuthoredTaskShellDependencies"] = (
                mission_authored_task_shell_rows
            )
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            node.pop("dialogFinishBranchDependencies", None)
            node.pop("dialogFinishEndpointDependencies", None)
            node.pop("dialogFinishLevelScriptTaskDependencies", None)
            node.pop("dialogFinishLevelScriptTaskAnyFinishContexts", None)
            node.pop("dialogFinishLevelScriptTaskMissionScriptContexts", None)
            rows = by_quest.get((mission_id, str(node.get("id") or "")), [])
            endpoint_rows = endpoint_by_quest.get(
                (mission_id, str(node.get("id") or "")), []
            )
            task_rows = task_by_quest.get(
                (mission_id, str(node.get("id") or "")), []
            )
            any_finish_task_rows = any_finish_task_by_quest.get(
                (mission_id, str(node.get("id") or "")), []
            )
            mission_script_rows = mission_script_task_by_quest.get(
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
            if any_finish_task_rows:
                node["dialogFinishLevelScriptTaskAnyFinishContexts"] = (
                    any_finish_task_rows
                )
                mission_any_finish_task_rows.extend(any_finish_task_rows)
            if mission_script_rows:
                node["dialogFinishLevelScriptTaskMissionScriptContexts"] = (
                    mission_script_rows
                )
                mission_script_task_rows.extend(mission_script_rows)
            for objective in node.get("objectives") or []:
                if not isinstance(objective, dict):
                    continue
                objective.pop("dialogFinishBranchDependencies", None)
                objective.pop("dialogFinishEndpointDependencies", None)
                objective.pop("dialogFinishLevelScriptTaskDependencies", None)
                objective.pop(
                    "dialogFinishLevelScriptTaskAnyFinishContexts",
                    None,
                )
                objective.pop(
                    "dialogFinishLevelScriptTaskMissionScriptContexts",
                    None,
                )
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
                objective_any_finish_task_rows = [
                    row
                    for row in any_finish_task_rows
                    if row.get("objectiveIndex") == objective.get("index")
                    and row.get("missionConditionId")
                    == str(objective.get("conditionId") or "")
                ]
                objective_mission_script_task_rows = [
                    row
                    for row in mission_script_rows
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
                if objective_any_finish_task_rows:
                    objective[
                        "dialogFinishLevelScriptTaskAnyFinishContexts"
                    ] = objective_any_finish_task_rows
                if objective_mission_script_task_rows:
                    objective[
                        "dialogFinishLevelScriptTaskMissionScriptContexts"
                    ] = objective_mission_script_task_rows
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
            "levelScriptTaskAnyFinishMissionContextCount": len(
                mission_any_finish_task_rows
            ),
            "levelScriptTaskMissionScriptContextCount": len(
                mission_script_task_rows
            ),
            "authoredTaskMissionShellDependencyCount": len(
                mission_authored_task_shell_rows
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
        summary["dialogFinishLevelScriptTaskAnyFinishContextCount"] = len(
            mission_any_finish_task_rows
        )
        summary["dialogFinishLevelScriptTaskMissionScriptContextCount"] = len(
            mission_script_task_rows
        )
        summary["dialogFinishAuthoredTaskShellDependencyCount"] = len(
            mission_authored_task_shell_rows
        )
        write_json(pipeline_root / str(summary.get("file") or ""), payload)
        published += len(mission_rows)
        published_endpoints += len(mission_endpoint_rows)
        published_task_dependencies += len(mission_task_rows)
        published_owned_task_dependencies += sum(
            row.get("missionShellRelationship") == "same_mission_shell"
            for row in mission_task_rows
        )
        published_any_finish_task_contexts += len(mission_any_finish_task_rows)
        published_mission_script_task_contexts += len(mission_script_task_rows)
        published_authored_task_shell_dependencies += len(
            mission_authored_task_shell_rows
        )
    index["dialogFinishBranchRecovery"] = {
        "schema": report.get("schemaVersion"),
        "status": report.get("status"),
        "counts": report.get("counts"),
        "producerFamilyCounts": report.get("producerFamilyCounts"),
        "nativeContract": report.get("nativeContract"),
        "missionRuntimeUnmatchedLevelScriptTaskFinishDependencies": (
            report.get("levelScriptTaskWithoutExactMissionFinishMatch") or []
        ),
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
    index["counts"]["dialogFinishLevelScriptTaskAuthoredFinishDependencies"] = len(
        report.get("levelScriptTaskAuthoredFinishDependencies") or []
    )
    index["counts"]["dialogFinishLevelScriptTaskAnyFinishContexts"] = (
        published_any_finish_task_contexts
    )
    index["counts"]["dialogFinishLevelScriptTaskMissionScriptContexts"] = (
        published_mission_script_task_contexts
    )
    index["counts"]["dialogFinishAuthoredTaskShellDependencies"] = (
        published_authored_task_shell_dependencies
    )
    return (
        published
        + published_endpoints
        + published_task_dependencies
        + published_any_finish_task_contexts
        + published_mission_script_task_contexts
        + published_authored_task_shell_dependencies
    )


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
        f"- Exact branch-relevant task consumers: {counts.get('levelScriptTaskExactCompleteMapConsumers', 0)} complete-map rows across {counts.get('levelScriptTaskResolvedExactTaskIdentities', 0)} resolved tasks; {counts.get('levelScriptTaskExactBoundedFragmentConsumers', 0)} bounded fragments",
        f"- Generic typed external carrier census: {counts.get('levelScriptTaskExternalIdentityCarriers', 0)} carriers ({counts.get('levelScriptTaskExternalMissionCarriers', 0)} with mission identity); {counts.get('levelScriptTaskExternalUncarriedIdentities', 0)} task identities remain uncarried",
        f"- Carrier search scope: {counts.get('levelScriptTaskCarrierActiveLogicalFiles', 0)} active structured files; {counts.get('levelScriptTaskCarrierTypedJsonFiles', 0)} typed JSON / {counts.get('levelScriptTaskCarrierNonJsonFiles', 0)} serialized non-JSON; {counts.get('levelScriptTaskCarrierTypedJsonCandidates', 0)} exact-task JSON candidates",
        f"- Serialized LevelData task-progress carriers: {counts.get('levelScriptTaskLevelDataProgressCarriers', 0)} exact rows / {counts.get('levelScriptTaskLevelDataCarriedIdentities', 0)} task identities from {counts.get('levelScriptTaskLevelDataRawCandidateFiles', 0)} raw-candidate files; {counts.get('levelScriptTaskLevelDataUniqueMissionShellIdentities', 0)} unique mission shells / {counts.get('levelScriptTaskLevelDataSharedMissionShellIdentities', 0)} shared / {counts.get('levelScriptTaskLevelDataUnresolvedMissionShellIdentities', 0)} unresolved; {counts.get('levelScriptTaskLevelDataUncarriedConditions', 0)} uncarried conditions / {counts.get('levelScriptTaskLevelDataRejectedShellClassifications', 0)} rejected stale-shell classifications",
        f"- Script-local NpcProxy segment contexts: {counts.get('levelScriptTaskNpcProxyMatchedScripts', 0)} matched scripts from {counts.get('levelScriptTaskNpcProxyTrackingConsumers', 0)} typed tracking rows / {counts.get('levelScriptTaskNpcProxyTrackingProxies', 0)} proxies; {counts.get('levelScriptTaskNpcProxyUniqueMissionShellScripts', 0)} unique / {counts.get('levelScriptTaskNpcProxySharedMissionShellScripts', 0)} shared mission shells",
        f"- Authored finish endpoint -> exact LevelScript task dependencies: {counts.get('levelScriptTaskAuthoredFinishDependencies', 0)}; unresolved authored endpoints: {counts.get('levelScriptTaskUnresolvedAuthoredFinishEndpoints', 0)}",
        f"- Shared MissionRuntime/LevelScript finish dependencies: {counts.get('levelScriptTaskSharedConsumerDependencies', 0)} placements across {counts.get('levelScriptTaskSharedConsumerMissions', 0)} missions",
        f"- Shared dependencies from complete maps / bounded mixed-map fragments: {counts.get('levelScriptTaskSharedConsumerCompleteMaps', 0)} / {counts.get('levelScriptTaskSharedConsumerFragments', 0)}",
        f"- Exact mission-shell task owners: {counts.get('levelScriptTaskMissionShellOwners', 0)} consumers ({counts.get('levelScriptTaskSubGameMissionShellOwners', 0)} SubGame / {counts.get('levelScriptTaskNpcProxyMissionShellOwners', 0)} NpcProxy segment / {counts.get('levelScriptTaskLevelDataMissionShellOwners', 0)} LevelData); NpcProxy corroborates {counts.get('levelScriptTaskNpcProxyCorroboratedLevelDataOwners', 0)} unique LevelData owners and refines {counts.get('levelScriptTaskNpcProxyRefinedAmbiguousLevelDataOwners', 0)} ambiguous LevelData owners; {counts.get('levelScriptTaskSameMissionShellDependencies', 0)} same-mission dependency placements",
        f"- Mission any-finish contexts: {counts.get('levelScriptTaskAnyFinishMissionContexts', 0)} placements across {counts.get('levelScriptTaskAnyFinishMissionContextMissions', 0)} missions",
        f"- Exact mission -> active LevelScript contexts: {counts.get('levelScriptTaskMissionScriptContexts', 0)} placements for {counts.get('levelScriptTaskMissionScriptContextConsumers', 0)} task consumers across {counts.get('levelScriptTaskMissionScriptContextMissions', 0)} missions",
        f"- Authored endpoint -> task dependencies without an exact MissionRuntime finish match: {counts.get('levelScriptTaskWithoutExactMissionFinishMatch', 0)}",
        f"- Current-binary task lifecycle: `{(report.get('levelScriptRuntimeContract') or {}).get('taskLifecycle', {}).get('schema', 'missing')}` / Processing condition calls `{(report.get('levelScriptRuntimeContract') or {}).get('taskLifecycle', {}).get('processingConditionCallCount', 0)}`",
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
                f"`{owner.get('missionId')}` / `LevelData task-progress shell`"
                if owner.get("ownerKind")
                == "leveldata_task_progress_mission_shell"
                else f"`{owner.get('missionId')}` / `NpcProxy segment shell`"
                if owner.get("ownerKind")
                == "npc_proxy_segment_script_mission_shell"
                else
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
    lines.extend(["", "## Mission context for LevelScript task dependencies", ""])
    any_context_rows = report.get("levelScriptTaskAnyFinishMissionContexts") or []
    script_context_rows = report.get("levelScriptTaskMissionScriptContexts") or []
    lines.append(
        "These rows attach original mission files as bounded context only. "
        "They do not establish task activation, task ownership, player choice, "
        "or cross-file order."
    )
    lines.append("")
    lines.append(
        f"- Any-finish mission observers paired with exact task outcomes: "
        f"{len(any_context_rows)}"
    )
    lines.append(
        f"- Exact mission-to-active-LevelScript observations: "
        f"{len(script_context_rows)}"
    )
    lines.extend(["", "## MissionRuntime-unmatched authored task dependencies", ""])
    unmatched_task_rows = (
        report.get("levelScriptTaskWithoutExactMissionFinishMatch") or []
    )
    if unmatched_task_rows:
        for row in unmatched_task_rows:
            task_id = row.get("taskId") or "task-id-unresolved"
            context = row.get("missionContextSummary") or {}
            lines.append(
                f"- `{row['dialogId']}` / `{row['finishId']}` -> "
                f"`{row['levelId']}/{row['scriptId']}` / `{task_id}` / "
                f"`{row['taskConditionId']}`; mission contexts: "
                f"exact finish `{context.get('exactFinishPlacements', 0)}`, "
                f"any finish `{context.get('anyFinishPlacements', 0)}`, "
                f"exact script `{context.get('exactScriptPlacements', 0)}`."
            )
    else:
        lines.append("- None.")
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
    try:
        native = validate_native_contract(args.game_assembly, args.metadata)
    except NativeEvidenceUnavailable as exc:
        required = native_evidence_required()
        print(
            native_evidence_skip_message(
                "dialog-finish-branch", exc.result, required=required
            ),
            file=sys.stderr,
        )
        return 1 if required else 0
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
        f"{report['counts']['levelScriptTaskAuthoredFinishDependencies']} authored endpoint-to-task dependencies, "
        f"{report['counts']['levelScriptTaskSharedConsumerDependencies']} shared LevelScript task dependencies, "
        f"{report['counts']['levelScriptTaskAnyFinishMissionContexts']} any-finish contexts, "
        f"{report['counts']['levelScriptTaskMissionScriptContexts']} mission-script contexts, "
        f"{report['counts']['levelScriptTaskUnresolvedAuthoredFinishEndpoints']} unresolved task endpoints, "
        f"{report['counts']['unresolvedExactConsumers']} unresolved exact consumers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
