"""Validate selected GameCondition readers used by LevelScript task maps.

The reviewed contract pins one installed client. A different or unavailable
client returns no routes; exported source receipts are checked only when the
caller requests the current corpus join.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-taskmap-condition-native.v1"
LABEL = "levelscriptTaskMapConditionNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_taskmap_condition_native.json"
_FIELD_TYPES = {
    "Beyond.GEnums.ScopeName": "enum32",
    "string": "string",
    "bool": "bool",
    "Beyond.Gameplay.Actions.Param`1<string>": "Param<string>",
    "Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.SpawnerPtr>": "Param<SpawnerPtr>",
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
    ptr = contract.get("spawnerPtr") or {}
    if (
        not isinstance(ptr.get("typeDefinition"), int)
        or not ptr.get("wrapperName") or not ptr.get("wrappedType")
        or ptr.get("fields") != [["id", "ulong"]]
    ):
        raise ValueError(f"{LABEL}.contract:SpawnerPtr-shape")
    for route in rows:
        fields = route.get("fields") or []
        native = route.get("nativeDeclaredTypes") or []
        reads = route.get("orderedReads") or []
        methods = route.get("methods") or []
        windows = route.get("codeWindows") or []
        if (
            route.get("serializedMemberCount") != len(fields)
            or route.get("inheritedMemberCount") != 4
            or len(native) != len(fields) or len(reads) != len(fields)
            or [r.get("memberIndex") for r in reads] != list(range(len(fields)))
            or [r.get("fieldName") for r in reads] != [f[0] for f in fields]
            or [r.get("readKind") for r in reads] != [f[1] for f in fields]
            or [[f[0], _FIELD_TYPES.get(f[1])] for f in native] != fields
            or fields[:4] != [
                ["scopeMask", "enum32"], ["uniqueId", "string"],
                ["useCurrentScope", "bool"], ["useGraphScope", "bool"],
            ]
            or any(f[1] not in {"Param<string>", "Param<SpawnerPtr>"} for f in fields[4:])
            or len(methods) != 2 or len(windows) != 2
            or methods[0][1] != route.get("wrapperName")
            or not methods[1][1].startswith(route.get("wrapperName", "") + "+")
            or [m[2] for m in methods] != ["Deserialize", "Deserialize"]
            or any(len(r) != 5 for r in route.get("sourceReceipts") or [])
        ):
            raise ValueError(f"{LABEL}.contract:route-shape={route.get('tag')}")
    return contract


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    dispatcher = contract["dispatcher"]
    wrappers = derive_from_image(image)
    switch = read_union_switch(
        image, "Beyond_Gameplay_GameConditionForMemoryPack", wrappers=wrappers,
    )
    if (
        switch["entryCount"] != dispatcher["entryCount"]
        or int(switch["tableVa"], 16) != base + dispatcher["tableRva"]
    ):
        raise ValueError(f"{LABEL}.native:dispatcher")
    table = image.pe.bytes_at_va(base + dispatcher["tableRva"], dispatcher["entryCount"] * 4)
    if hashlib.sha256(table).hexdigest().upper() != dispatcher["tableSha256"].upper():
        raise ValueError(f"{LABEL}.native:dispatcher-table-sha256")
    extents = image.mapper.pdata_function_extents(image.pe)
    for route in contract["routes"]:
        tag = route["tag"]
        entry = switch["entries"][tag]
        wrapper = wrappers[entry["typeDefinition"]]
        if (
            entry["wrapperName"] != route["wrapperName"]
            or entry["typeDefinition"] != route["typeDefinition"]
            or entry["registeredTypeIndex"] != route["registeredTypeIndex"]
            or int(entry["targetVa"], 16) != base + route["switchTargetRva"]
            or int(entry["bodyVa"], 16) != base + route["bodyRva"]
            or int(entry["usageCellVa"], 16) != base + route["usageCellRva"]
            or image.pe.bytes_at_va(int(entry["usageCellVa"], 16), 8).hex().upper()
            != route["usageRawHex"].upper()
        ):
            raise ValueError(f"{LABEL}.native:dispatcher-route={tag:#x}")
        if (
            wrapper.wrapped_type != route["typeName"]
            or len(wrapper.members) != route["serializedMemberCount"]
            or len(wrapper.inherited_members) != route["inheritedMemberCount"]
            or [[member.name.lstrip("_"), member.declared_type]
                for member in wrapper.members] != route["nativeDeclaredTypes"]
        ):
            raise ValueError(f"{LABEL}.native:wrapper-fields={tag:#x}")
        for method, window in zip(route["methods"], route["codeWindows"]):
            index = image.validate_method_row(method, label=LABEL)
            pointer = image.method_pointer_va(image.metadata.methods[index])
            if (
                pointer != base + window["startRva"]
                or extents.get(pointer) != base + window["endRva"]
            ):
                raise ValueError(f"{LABEL}.native:method-extent={tag:#x}")
        image.check_windows(route["codeWindows"], label=LABEL)
        reader = route["codeWindows"][0]
        previous = reader["startRva"]
        for read in route["orderedReads"]:
            site = read["callsiteRva"]
            if not previous < site < reader["endRva"] - 5:
                raise ValueError(f"{LABEL}.native:read-order={tag:#x}/{read['memberIndex']}")
            raw = image.pe.bytes_at_va(base + site, 5)
            target = site + 5 + struct.unpack_from("<i", raw, 1)[0]
            if (
                raw[0] != 0xE8 or raw.hex().upper() != read["callHex"].upper()
                or target != read["targetRva"]
            ):
                raise ValueError(f"{LABEL}.native:read-call={tag:#x}/{read['memberIndex']}")
            previous = site
    if "spawnerPtr" in contract:
        ptr = contract["spawnerPtr"]
        ptrs = [(definition, w) for definition, w in wrappers.items()
                if w.name == ptr["wrapperName"]]
        if (
            len(ptrs) != 1 or ptrs[0][0] != ptr["typeDefinition"]
            or ptrs[0][1].wrapped_type != ptr["wrappedType"]
            or [[m.name, m.declared_type] for m in ptrs[0][1].members] != ptr["fields"]
        ):
            raise ValueError(f"{LABEL}.native:SpawnerPtr-member")


def _validate_sources(contract: dict[str, Any], export_root: Path, ledger: Path,
                      summary: Path) -> int:
    summary_row = json.loads(summary.read_bytes())
    if (
        summary_row.get("status") != "complete"
        or hashlib.sha256(ledger.read_bytes()).hexdigest().upper()
        != summary_row.get("provenance", {}).get("outputFiles", {}).get("sha256", "").upper()
    ):
        raise ValueError(f"{LABEL}.source:ledger-summary-join")
    source_rows = {}
    with gzip.open(ledger, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                source_rows[row["exportRelativePath"]] = row
    checked = 0
    for route in contract["routes"]:
        tag = route["tag"]
        prefix = (bytes((tag,)) if tag < 0xFA else b"\xFA" + tag.to_bytes(2, "little"))
        prefix += bytes((route["serializedMemberCount"],))
        for path, digest, start, end, span_digest in route["sourceReceipts"]:
            data = (export_root / path).read_bytes()
            ledger_row = source_rows.get(path) or {}
            if (
                not 0 <= start < end <= len(data)
                or data[start:start + len(prefix)] != prefix
                or hashlib.sha256(data).hexdigest().upper() != digest.upper()
                or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
                or ledger_row.get("logicalSha256", "").upper() != digest.upper()
                or ledger_row.get("length") != len(data)
            ):
                raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
            checked += 1
    if checked == 0:
        raise ValueError(f"{LABEL}.source:no-receipts")
    return checked


@lru_cache(maxsize=4)
def validate_levelscript_taskmap_condition_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on client drift and optionally authenticate exported cursors."""
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
        _validate_native(image, contract)
        source_count = 0
        if any(value is not None for value in (export_root, ledger_path, summary_path)):
            if not all(value is not None for value in (export_root, ledger_path, summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            source_count = _validate_sources(
                contract, Path(export_root), Path(ledger_path), Path(summary_path),
            )
        return {"status": "validated", "evidenceBoundary": "exact",
                "routeCount": len(contract["routes"]), "sourceReceiptCount": source_count}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {"status": "validation_failed", "failedGate": str(error).split(":", 1)[0],
                "detail": str(error)[:400], "routeCount": 0}


@lru_cache(maxsize=1)
def validated_taskmap_condition_routes() -> dict[tuple[int, int], dict[str, Any]]:
    """Return reviewed current routes only after their native proof passes."""
    if validate_levelscript_taskmap_condition_native_contract()["status"] != "validated":
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
    audit = validate_levelscript_taskmap_condition_native_contract(
        contract_path=args.contract, game_root=args.game_root,
        export_root=args.export_root, ledger_path=args.ledger,
        summary_path=args.summary,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
