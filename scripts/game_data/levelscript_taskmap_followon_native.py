"""Validate followon selected GameCondition readers for positive task maps.

This contract is isolated from the first task-map batch. Missing or changed
installed native inputs return no routes, and source receipts are optional
until a caller supplies the current JsonData export and ledger.

Routes in ``levelscript_taskmap_followon_native.json``: ``CheckMapVar``,
``CheckAliveCharNumInCurTeam``, ``CheckRemoteCommFinish``,
``CheckInteractiveIsActivated``, ``CompareInteractivePropertyBool``,
``CheckUnlockTech``, ``CheckLsmCompleted``,
``Conditions.CheckIsInFactoryMode``, ``Conditions.CheckIsItemInQuickBar``
and ``InMainHud``.  Generated fields and ordered native reads distinguish
scalar comparison parameters, signed map values, entity pointers, LSM and
LevelScript pointers, and null or authored string parameters.  Each reached
condition has an exact source cursor joined to the current JsonData ledger;
the codec is ``codecs.levelscript.taskmap_followon_conditions``.  The
sequential task-map reader still promotes only complete owners at physical
EOF, and nothing here proves runtime evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_taskmap_condition_native import (
    _validate_native as _validate_taskmap_native_routes,
    _validate_sources as _validate_taskmap_sources,
)
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-taskmap-followon-native.v1"
LABEL = "levelscriptTaskMapFollowonNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_taskmap_followon_native.json"
_FIELD_TYPES = {
    "Beyond.GEnums.ScopeName": "enum32", "string": "string", "bool": "bool",
    "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
    "Beyond.Gameplay.Actions.Param`1<bool>": "Param<bool>",
    "Beyond.Gameplay.Actions.Param`1<int>": "Param<int32>",
    "Beyond.Gameplay.Actions.Param`1<long>": "Param<int64>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.CompareOperator>": "Param<CompareOperator>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>": "Param<EntityPtr>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LsmPtr>": "Param<LsmPtr>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LevelScriptPtr>": "Param<LevelScriptPtr>",
}


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    if contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build":
        raise ValueError(f"{LABEL}.contract:schema-or-status")
    inputs = contract.get("nativeInputs") or {}
    if set(inputs) != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}:
        raise ValueError(f"{LABEL}.contract:native-inputs")
    rows = contract.get("routes")
    if not isinstance(rows, list) or not rows or len({r.get("tag") for r in rows}) != len(rows):
        raise ValueError(f"{LABEL}.contract:route-set")
    for route in rows:
        fields = route.get("fields") or []
        native = route.get("nativeDeclaredTypes") or []
        reads = route.get("orderedReads") or []
        methods = route.get("methods") or []
        windows = route.get("codeWindows") or []
        if (
            route.get("serializedMemberCount") != len(fields)
            or not isinstance(route.get("inheritedMemberCount"), int)
            or not 4 <= route["inheritedMemberCount"] <= len(fields)
            or len(native) != len(fields) or len(reads) != len(fields)
            or [r.get("memberIndex") for r in reads] != list(range(len(fields)))
            or [r.get("fieldName") for r in reads] != [f[0] for f in fields]
            or [r.get("readKind") for r in reads] != [f[1] for f in fields]
            or [[f[0], _FIELD_TYPES.get(f[1])] for f in native] != fields
            or fields[:4] != [
                ["scopeMask", "enum32"], ["uniqueId", "string"],
                ["useCurrentScope", "bool"], ["useGraphScope", "bool"],
            ]
            or len(methods) != 2 or len(windows) != 2
            or methods[0][1] != route.get("wrapperName")
            or not methods[1][1].startswith(route.get("wrapperName", "") + "+")
            or [m[2] for m in methods] != ["Deserialize", "Deserialize"]
            or any(len(r) != 5 for r in route.get("sourceReceipts") or [])
        ):
            raise ValueError(f"{LABEL}.contract:route-shape={route.get('tag')}")
    pointers = contract.get("pointerTypes") or {}
    if set(pointers) != {"EntityPtr", "LsmPtr", "LevelScriptPtr"}:
        raise ValueError(f"{LABEL}.contract:pointer-types")
    return contract


def _validate_pointers(image: Any, contract: dict[str, Any]) -> None:
    wrappers = derive_from_image(image)
    for name, pointer in contract["pointerTypes"].items():
        definition = pointer["typeDefinition"]
        actual = wrappers.get(definition)
        if (
            actual is None
            or actual.name != pointer["wrapperName"]
            or actual.wrapped_type != pointer["wrappedType"]
            or [[m.name, m.declared_type] for m in actual.members] != pointer["fields"]
        ):
            raise ValueError(f"{LABEL}.native:pointer={name}")


@lru_cache(maxsize=4)
def validate_levelscript_taskmap_followon_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Authenticate selected readers and, optionally, current source spans."""
    try:
        contract = _contract(Path(contract_path))
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        if gate.status != "validated":
            return {"status": gate.status, "detail": gate.detail,
                    "failedGate": "installed_native_inputs", "routeCount": 0}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll-sha256")
        image = open_native_image(gate.gameassembly, gate.metadata)
        _validate_taskmap_native_routes(image, contract)
        _validate_pointers(image, contract)
        source_count = 0
        if any(value is not None for value in (export_root, ledger_path, summary_path)):
            if not all(value is not None for value in (export_root, ledger_path, summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            source_count = _validate_taskmap_sources(
                contract, Path(export_root), Path(ledger_path), Path(summary_path),
            )
        return {"status": "validated", "evidenceBoundary": "exact",
                "routeCount": len(contract["routes"]), "sourceReceiptCount": source_count}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {"status": "validation_failed", "failedGate": str(error).split(":", 1)[0],
                "detail": str(error)[:400], "routeCount": 0}


@lru_cache(maxsize=1)
def validated_taskmap_followon_routes() -> dict[tuple[int, int], dict[str, Any]]:
    if validate_levelscript_taskmap_followon_native_contract()["status"] != "validated":
        return {}
    return {(r["tag"], r["serializedMemberCount"]): r for r in _contract(DEFAULT_CONTRACT)["routes"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    audit = validate_levelscript_taskmap_followon_native_contract(
        contract_path=args.contract, game_root=args.game_root,
        export_root=args.export_root, ledger_path=args.ledger,
        summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
