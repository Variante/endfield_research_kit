"""Authenticate the selected EnemyTable AI key to config-asset load route.

This checks static native code under selected installed inputs. The result is
conditional on successful table lookup and the unpatched synchronous path;
it does not witness a live enemy, resource load, or graph execution.

The route (contract ``extend_data_graph_ai_native.json``), all static:

1. ``EntityDataStorage.CreateEnemyFromServer`` passes its
   ``Proto.SCENE_MONSTER`` to ``EnemyInfo.InitFromServerData``, which reads
   ``SCENE_MONSTER.commonInfo.templateid`` for a keyed ``EnemyTable`` lookup
   (``EnemyData.templateId`` for template setup) and passes the message to the
   ``EnemyServerData`` constructor, which copies the same ``templateid`` into
   ``EnemyServerData.enemyId`` and is stored as ``BaseEntityData.serverData``:
   a direct producer and a second, independent Table-key use of the field.
2. ``EntityNode._SpawnEntity`` passes ``BaseEntityData.serverData`` through
   ``ObjectContainer.SpawnEntity`` and ``LoadEntity`` into
   ``Entity.serverData`` (``Entity.AssignServerData``);
   ``EnemyRootComponent.InitSelf`` casts it to ``EnemyServerData`` and copies
   ``enemyId`` into the enemy root.
3. On the unpatched synchronous ``EnemyAIComponent`` initialization, the code
   reads ``BaseComponent.entity``, ``Entity.enemy`` and
   ``EnemyRootComponent.enemyId`` as the ``Tables.s_enemyTable`` key, reads the
   ``EnemyData`` bean's string slot zero (the selector
   ``EnemyData.get_aiTemplateId`` uses), formats an ``AIConfig`` asset path,
   calls ``LoadSingleConfig``, and stores the result in a field declared
   ``EnemyAIConfigData``.

The chain is conditional on the initialized ``EnemyInfo`` reaching the checked
``EntityNode`` spawn path, the cast, a successful lookup and a nonempty AI
field. The source of a live ``SCENE_MONSTER`` message, its relation to
installed spawn or scene records, alternate constructors, async and override
paths, and the graph instance remain open; IFix can redirect the methods.

The audit prints JSON; ``--out
reports/animestudio/extend_data_graph_ai_native_latest.json`` also saves it.
``extend_data_graph_ai_corpus`` reruns this audit before its join.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_graph_ai_native")

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.call_graph import CallGraph
from scripts.game_data.il2cpp.context import literal_record, rip_qword_load_target, unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name


CONTRACT = CONTRACTS_DIR / "extend_data_graph_ai_native.json"
SCHEMA = "endfield.extend-data-graph-ai-native-contract.v4"
AUDIT_SCHEMA = "endfield.extend-data-graph-ai-native-audit.v4"
LABEL = "extend-data-graph-ai-native"


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError(f"{LABEL}:{detail}")


def _branch_target(image: Any, rva: int, opcode: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    _require(raw[0] == opcode, f"branch-opcode:{rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _usage_cell(image: Any, load_rva: int, expected_cell_rva: int) -> int:
    load_va = image.pe.image_base + load_rva
    raw = image.pe.bytes_at_va(load_va, 7)
    cell_va = rip_qword_load_target(raw, load_va, source=str(image.gameassembly))
    _require(cell_va - image.pe.image_base == expected_cell_rva,
             f"usage-cell:{load_rva:#x}")
    return cell_va


def _selected_literal(image: Any, row: dict[str, Any]) -> str:
    cell_va = _usage_cell(image, row["loadRva"], row["usageCellRva"])
    section = image.metadata.sections["stringLiteral"]
    data = image.metadata.sections["stringLiteralData"]
    index = unresolved_usage_index(
        image.pe.bytes_at_va(cell_va, 8), section.size // 8,
        tag=5, source=str(image.gameassembly), offset=cell_va,
    )
    _require(index == row["literalIndex"], f"literal-index:{row['role']}")
    at = section.offset + index * 8
    start, size = literal_record(
        image.metadata.buf[at:at + 8], data.size,
        source=str(image.metadata_path), offset=at,
    )
    value = image.metadata.buf[data.offset + start:data.offset + start + size].decode("utf-8")
    _require(value == row["text"], f"literal-text:{row['role']}")
    return value


def _check_native(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    pe, metadata = image.pe, image.metadata
    runtime_types = int(image.registration["types"], 16)
    for typ in contract["types"]:
        _require(image.type_name(typ["index"]) == typ["name"], f"type:{typ['name']}")
        definition = metadata.types[typ["index"]]
        if "parent" in typ:
            parent_pointer = pe.u64_at_va(runtime_types + definition.parent_index * 8)
            _require(runtime_type_name(pe, metadata, parent_pointer) == typ["parent"],
                     f"parent:{typ['name']}")
        offsets = (runtime_type_field_offsets(metadata, pe, image.registration, typ["index"])
                   if typ["fields"] else {})
        fields = {metadata.string(field.name_index): field for field in metadata.fields_for(definition)}
        for name, offset, type_name in typ["fields"]:
            _require(name in fields and offsets.get(name) == offset,
                     f"field-offset:{typ['name']}.{name}")
            pointer = pe.u64_at_va(runtime_types + fields[name].type_index * 8)
            _require(runtime_type_name(pe, metadata, pointer) == type_name,
                     f"field-type:{typ['name']}.{name}")

    for row in contract["methods"]:
        image.validate_method_row(row, label=LABEL)
    for index, expected in contract["methodFirstParameters"]:
        method = metadata.methods[index]
        parameters = metadata.parameters_for(method)
        _require(bool(parameters)
                 and metadata.metadata_type_name(parameters[0].type_index) == expected,
                 f"method-first-parameter:{index}")
    for index, expected in contract["methodParameterTypes"]:
        method = metadata.methods[index]
        actual = [
            runtime_type_name(
                pe, metadata, pe.u64_at_va(runtime_types + parameter.type_index * 8),
            )
            for parameter in metadata.parameters_for(method)
        ]
        _require(actual == expected, f"method-parameter-types:{index}")
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(contract["instructionWindows"], label=LABEL)

    table = contract["tableUsage"]
    cell_va = _usage_cell(image, table["loadRva"], table["usageCellRva"])
    index = unresolved_usage_index(
        pe.bytes_at_va(cell_va, 8), image.registration["typesCount"],
        tag=1, source=str(image.gameassembly), offset=cell_va,
    )
    _require(index == table["typeIndex"], "table-type-index")
    pointer = pe.u64_at_va(runtime_types + index * 8)
    definition = struct.unpack_from("<Q", pe.bytes_at_va(pointer, 16))[0]
    _require(definition == table["typeDefinition"] == contract["types"][0]["index"],
             "table-type-definition")

    source = contract["sourceUsage"]
    cell_va = _usage_cell(image, source["loadRva"], source["usageCellRva"])
    index = unresolved_usage_index(
        pe.bytes_at_va(cell_va, 8), image.registration["typesCount"],
        tag=1, source=str(image.gameassembly), offset=cell_va,
    )
    _require(index == source["typeIndex"], "server-data-type-index")
    pointer = pe.u64_at_va(runtime_types + index * 8)
    definition = struct.unpack_from("<Q", pe.bytes_at_va(pointer, 16))[0]
    _require(definition == source["typeDefinition"]
             and image.type_name(definition) == source["typeName"],
             "server-data-type-definition")

    literals = {row["role"]: _selected_literal(image, row) for row in contract["pathLiterals"]}
    _require(set(literals) == {"assetPathPrefix", "assetPathFormat"}, "path-literal-roles")
    for source, target in contract["directCalls"]:
        _require(_branch_target(image, source, 0xE8) == target, f"direct-call:{source:#x}")
    for source, target in contract["directJumps"]:
        _require(_branch_target(image, source, 0xE9) == target, f"direct-jump:{source:#x}")
    names = CallGraph(image).names_by_pointer
    for rva, expected in contract["namedTargets"]:
        _require(expected in names.get(pe.image_base + rva, ()),
                 f"named-target:{rva:#x}")

    return {
        "table": "Beyond.Cfg.Tables.s_enemyTable",
        "protocolIdentitySource": "Proto.SCENE_MONSTER.commonInfo.templateid -> Beyond.Gameplay.EnemyServerData.enemyId",
        "templateLookupSource": "Proto.SCENE_MONSTER.commonInfo.templateid -> Beyond.Gameplay.Core.EnemyInfo.TryGetEnemyTemplateIdFromEnemyId -> Beyond.Cfg.Tables.s_enemyTable -> Beyond.Cfg.EnemyData.templateId",
        "serverDataTransferSource": "Beyond.Gameplay.Core.EntityManager+EntityNode.data.serverData -> ObjectContainer.SpawnEntity -> ObjectContainer.LoadEntity -> Beyond.Gameplay.Core.Entity.serverData",
        "lookupKeySource": "Beyond.Gameplay.EnemyServerData.enemyId -> Beyond.Gameplay.Core.EnemyRootComponent.enemyId",
        "beanField": "Beyond.Cfg.EnemyData.aiTemplateId",
        "configAssetType": "Beyond.Gameplay.AI.Config.EnemyAIConfigData",
        "assetPathPrefix": literals["assetPathPrefix"],
        "assetPathFormat": literals["assetPathFormat"],
        "methodCount": len(contract["methods"]),
        "codeWindowCount": len(contract["codeWindows"]),
        "instructionWindowCount": len(contract["instructionWindows"]),
        "directCallCount": len(contract["directCalls"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def audit_extend_data_graph_ai_native(
    *, contract_path: Path = CONTRACT, gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label=LABEL, status="validated",
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["globalMetadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": AUDIT_SCHEMA, "status": gate.status, "detail": gate.detail,
        "contractSha256": contract_sha,
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256,
            "globalMetadataSha256": gate.metadata_sha256,
        },
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return report
    unity = gate.gameassembly.with_name("UnityPlayer.dll")
    if not unity.is_file():
        report.update(status="missing", detail=f"UnityPlayer.dll missing at {unity}")
        return report
    unity_sha = sha256_file(unity).upper()
    report["nativeInputs"]["unityPlayerSha256"] = unity_sha
    if unity_sha != inputs["unityPlayerSha256"].upper():
        report.update(status="mismatched", detail="UnityPlayer.dll hash differs")
        return report
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        report["route"] = _check_native(image, contract)
    except (ValueError, RuntimeError, KeyError, IndexError, struct.error, UnicodeError) as error:
        report.update(status="mismatched", detail=f"native proof failed: {error}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = audit_extend_data_graph_ai_native(
        contract_path=args.contract, gameassembly=args.gameassembly, metadata=args.metadata,
    )
    result = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result, encoding="utf-8")
    print(result, end="")
    return 0 if report["status"] == NATIVE_EVIDENCE_VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
