"""Authenticate the selected native spawner-library lookup and AI override route.

The static route is conditional. It does not prove that an authored enemyId
becomes a live SCENE_MONSTER templateid or that any override asset was loaded.

The checked routes (contract ``extend_data_spawner_library_native.json``):

- ``SpawnerConfigData.get_enemyLibraryDict`` enumerates ``enemyLibrary`` and
  keys each item by its ``key`` field, separately from ``enemyId``.
- ``GameplayNetwork._Handle_EnemySpawnerObjectEnd`` copies
  ``SC_SCENE_MONSTER_SPAWNER_OBJECT_DATA_END.details[]`` object, action and
  spawn indexes into ``SpawnDataDetail`` records;
  ``SpawnerManager.OnEnemySpawnerObjectEnd`` passes them to
  ``SpawnerRuntime.SetupSpawnData``, which installs the server object ID to
  action ID mapping in ``m_entityId2ActionIdDict``. This is a static client
  consumer of a server message, not a captured message.
- ``SpawnerManager.TryGetLibraryItem`` maps an entity's server ID to its
  spawner action, reads ``SpawnMonsterFromTemplateV2.libraryKey`` and selects
  from the key-indexed dictionary. On the unpatched synchronous path
  ``EnemyAIComponent._InitSync`` supplies the entity's server ID and the enemy
  root's parent spawner. A nonempty ``overrideAIConfig`` can cause a distinct
  ``AIConfig/Override/{name}.asset`` load and a typed
  ``EnemyAIRuntimeCfg.SetOverrideData(EnemyAIConfigDataOverride)`` call: an
  override layer beside the default ``EnemyTable.aiTemplateId`` route, which
  does not itself select a base graph.
- ``EnemyAIComponent.TryGetRuntimeBornData`` prefers entity-provided born data;
  otherwise its ``_TryGetSpawnerLibraryItem`` branch reaches the same keyed
  lookup and copies ``bornTemplateId`` and ``bornBehaviorData`` as separate
  outputs, never the item's ``enemyId``.
- The ``EnemyServerData`` constructor copies
  ``SCENE_MONSTER.commonInfo.templateid`` into ``enemyId`` and the separate
  ``SCENE_MONSTER.monsterLibraryKey`` into ``subgameLibraryKey``. That
  protocol key is a candidate for a spawner selection join, but no selected
  client route compares it with an authored action's ``libraryKey``.

The audit checks installed native hashes, metadata field identities, exact
code windows, decisive instructions, call targets and the path literal, and
returns no route when those inputs differ. The protocol-message producer, its
binding to one action and library item, and a live override load remain
open; an ID intersection alone cannot close them.

Pass the explicit ``--gameassembly``/``--metadata`` pair; the audit prints
JSON, and ``--out
reports/animestudio/extend_data_spawner_library_native_latest.json`` also
saves it.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.extend_data_spawner_library_native")

import argparse
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.call_graph import CallGraph, loaded_literals
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name


CONTRACT = CONTRACTS_DIR / "extend_data_spawner_library_native.json"
SCHEMA = "endfield.extend-data-spawner-library-native-contract.v2"
AUDIT_SCHEMA = "endfield.extend-data-spawner-library-native-audit.v2"
LABEL = "extend-data-spawner-library-native"


def _require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError(f"{LABEL}:{detail}")


def _branch_target(image: Any, rva: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    _require(raw[0] == 0xE8, f"call-opcode:{rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _check_native(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    pe, metadata = image.pe, image.metadata
    runtime_types = int(image.registration["types"], 16)
    for typ in contract["types"]:
        _require(image.type_name(typ["index"]) == typ["name"], f"type:{typ['name']}")
        definition = metadata.types[typ["index"]]
        offsets = runtime_type_field_offsets(metadata, pe, image.registration, typ["index"])
        fields = {metadata.string(field.name_index): field for field in metadata.fields_for(definition)}
        for name, offset, type_name in typ["fields"]:
            _require(name in fields and offsets.get(name) == offset,
                     f"field-offset:{typ['name']}.{name}")
            pointer = pe.u64_at_va(runtime_types + fields[name].type_index * 8)
            _require(runtime_type_name(pe, metadata, pointer) == type_name,
                     f"field-type:{typ['name']}.{name}")

    for row in contract["methods"]:
        image.validate_method_row(row, label=LABEL)
    for method_index, expected in contract["methodParameterTypes"]:
        method = metadata.methods[method_index]
        actual = [
            runtime_type_name(pe, metadata, pe.u64_at_va(runtime_types + parameter.type_index * 8))
            for parameter in metadata.parameters_for(method)
        ]
        _require(actual == expected, f"method-parameters:{method_index}")

    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_instruction_windows(contract["instructionWindows"], label=LABEL)
    for source, target in contract["directCalls"]:
        _require(_branch_target(image, source) == target, f"direct-call:{source:#x}")

    graph = CallGraph(image)
    for target_rva, expected_name in contract["namedTargets"]:
        names = graph.names_by_pointer.get(pe.image_base + target_rva, ())
        _require(expected_name in names, f"named-target:{target_rva:#x}")
    init_sync = next(row for row in contract["methods"] if row[2] == "_InitSync")
    found_literals = loaded_literals(graph, pe.image_base + init_sync[3], 0x750)
    _require(set(contract["pathLiterals"]) <= set(found_literals), "override-path-literals")

    return {
        "serverMapping": "SC_SCENE_MONSTER_SPAWNER_OBJECT_DATA_END.details[].objId/actionId/spawnIdx -> SpawnDataDetail.serverId/actionId/spawnIndex -> SpawnerManager.m_entityId2ActionIdDict[serverId] = actionId",
        "selection": "entity.serverId -> SpawnerManager entityId2ActionId -> SpawnMonsterFromTemplateV2.libraryKey -> SpawnerConfigData.enemyLibraryDict[item.key]",
        "override": "item.overrideAIConfig -> AIConfig/Override/{name}.asset -> EnemyAIConfigDataOverride -> EnemyAIRuntimeCfg.SetOverrideData",
        "bornData": "EnemyAIComponent.TryGetRuntimeBornData -> _TryGetSpawnerLibraryItem -> SpawnerManager.TryGetLibraryItem -> item.bornTemplateId/item.bornBehaviorData, if entity-provided born data did not take precedence",
        "protocolIdentity": "SCENE_MONSTER.commonInfo.templateid -> EnemyServerData.enemyId; SCENE_MONSTER.monsterLibraryKey -> EnemyServerData.subgameLibraryKey",
        "methodCount": len(contract["methods"]),
        "codeWindowCount": len(contract["codeWindows"]),
        "instructionWindowCount": len(contract["instructionWindows"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def audit_extend_data_spawner_library_native(
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
    report = audit_extend_data_spawner_library_native(
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
