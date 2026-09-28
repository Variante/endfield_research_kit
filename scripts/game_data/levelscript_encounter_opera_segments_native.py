"""Authenticate positive Encounter opera-segment wrappers and source cursors."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.codecs.levelscript.encounter_opera_segments import (
    decode_positive_encounter_opera_segments,
)
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.levelscript-encounter-opera-segments-native.v1"
LABEL = "levelscriptEncounterOperaSegmentsNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_encounter_opera_segments_native.json"
_RECORDS = (
    "EncounterData.OperaSegment", "ParamKeyValue", "ParamValue", "ParamValueAtom",
)


def _contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    records = contract.get("records") or []
    structs = contract.get("structs") or {}
    receipts = contract.get("sourceReceipts") or []
    if (
        contract.get("schema") != SCHEMA
        or contract.get("status") != "exact-current-build"
        or set(contract.get("nativeInputs") or {})
        != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or [row.get("name") for row in records] != list(_RECORDS)
        or set(structs) != set(_RECORDS)
        or not receipts
        or any(len(row) != 5 for row in receipts)
        or len({(row[0], row[2]) for row in receipts}) != len(receipts)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    for row in records:
        name = row["name"]
        fields = row.get("nativeDeclaredTypes") or []
        methods = row.get("methods") or []
        windows = row.get("codeWindows") or []
        declared = structs[name]
        if (
            declared.get("wrapperName") != row.get("wrapperName")
            or declared.get("memberCount") != len(fields)
            or [field[0] for field in fields]
            != [field[0] for field in declared.get("fields") or []]
            or len(methods) != 2
            or [method[2] for method in methods] != ["Deserialize", "Deserialize"]
            or methods[0][1] != row["wrapperName"]
            or not methods[1][1].startswith(row["wrapperName"] + "+")
            or not windows
        ):
            raise ValueError(f"{LABEL}.contract:record={name}")
    return contract


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    base = image.pe.image_base
    wrappers = derive_from_image(image)
    extents = image.mapper.pdata_function_extents(image.pe)
    chained = BodyIndex(image).chained_fragments
    for row in contract["records"]:
        matches = [wrapper for wrapper in wrappers.values()
                   if wrapper.name == row["wrapperName"]]
        if len(matches) != 1:
            raise ValueError(f"{LABEL}.native:wrapper={row['name']}")
        wrapper = matches[0]
        if (
            wrapper.wrapped_type != row["wrappedType"]
            or [[member.name.lstrip("_"), member.declared_type]
                for member in wrapper.members] != row["nativeDeclaredTypes"]
        ):
            raise ValueError(f"{LABEL}.native:wrapper-fields={row['name']}")
        expected = []
        for method_row in row["methods"]:
            index = image.validate_method_row(method_row, label=LABEL)
            va = image.method_pointer_va(image.metadata.methods[index])
            expected.append((va - base, extents[va] - base))
            expected.extend((part - base, part + size - base)
                            for part, size in chained.get(va, ()))
        windows = row["codeWindows"]
        if [(window["startRva"], window["endRva"]) for window in windows] != expected:
            raise ValueError(f"{LABEL}.native:complete-method-windows={row['name']}")
        image.check_windows(windows, label=LABEL)


def _validate_sources(
    contract: dict[str, Any], export_root: Path, ledger_path: Path, summary_path: Path,
) -> int:
    summary = json.loads(summary_path.read_bytes())
    if (
        summary.get("status") != "complete"
        or hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()
        != summary.get("provenance", {}).get("outputFiles", {}).get("sha256", "").upper()
    ):
        raise ValueError(f"{LABEL}.source:summary-ledger-join")
    wanted = {receipt[0] for receipt in contract["sourceReceipts"]}
    ledger = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData" and row.get("exportRelativePath") in wanted:
                ledger[row["exportRelativePath"]] = row
    for path, digest, start, end, span_digest in contract["sourceReceipts"]:
        data = (export_root / path).read_bytes()
        if (
            not 0 <= start < end <= len(data)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
            or ledger.get(path, {}).get("length") != len(data)
        ):
            raise ValueError(f"{LABEL}.source:receipt={path}@{start}")
        _, actual_end = decode_positive_encounter_opera_segments(
            data, start, "encounter.operaSegments", contract,
        )
        if actual_end != end:
            raise ValueError(
                f"{LABEL}.source:cursor={path}@{start},end={actual_end},expected={end}"
            )
    return len(contract["sourceReceipts"])


@lru_cache(maxsize=4)
def validate_levelscript_encounter_opera_segments_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    export_root: Path | None = None, ledger_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on native wrapper, formatter window or requested source drift."""
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
            return {"status": gate.status, "failedGate": "installed_native_inputs",
                    "detail": gate.detail, "recordCount": 0}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            raise ValueError(f"{LABEL}.native:UnityPlayer.dll")
        _validate_native(open_native_image(gate.gameassembly, gate.metadata), contract)
        count = 0
        if any(value is not None for value in (export_root, ledger_path, summary_path)):
            if not all(value is not None for value in (export_root, ledger_path, summary_path)):
                raise ValueError(f"{LABEL}.source:incomplete-paths")
            count = _validate_sources(contract, Path(export_root), Path(ledger_path), Path(summary_path))
        return {"status": "validated", "evidenceBoundary": "exact",
                "recordCount": len(contract["records"]), "contract": contract,
                "sourceReceiptCount": count}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {"status": "validation_failed", "failedGate": str(error).split(":", 1)[0],
                "detail": str(error)[:400], "recordCount": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    result = validate_levelscript_encounter_opera_segments_native_contract(
        contract_path=args.contract, game_root=args.game_root, export_root=args.export_root,
        ledger_path=args.ledger, summary_path=args.summary,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "contract"}, indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
