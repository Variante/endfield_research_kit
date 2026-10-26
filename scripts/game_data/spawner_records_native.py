"""Prove reviewed Spawner root read/setter order on the selected build.

This records typed source calls and the pooled-string/Boolean leaves. It does
not prove collection formatter selection, live pool contents or spawn behavior.
"""
from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Use python -m scripts.game_data.spawner_records_native")

import argparse
import json
import struct
from dataclasses import replace
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR

CONTRACT = CONTRACTS_DIR / "spawner_records_native.json"
SCHEMA = "endfield.spawner-record-sources-native.v2"


def read_contract():
    contract = json.loads(CONTRACT.read_bytes())
    if contract.get("schema") != SCHEMA or contract.get("status") != "validated":
        raise ValueError(f"spawnerRecords.contract:schema/status:{CONTRACT}")
    if not contract.get("records") or any(not row.get("codeWindows") or not row.get("orderedReads")
            or len(row["orderedReads"]) != len(row["fields"]) for row in contract["records"]):
        raise ValueError(f"spawnerRecords.contract:incomplete-source-facts:{CONTRACT}")
    return contract


def check_spawner_records_native_inputs(*, gameassembly=None, metadata=None):
    pins = read_contract()["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"], gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return gate
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return replace(gate, status="missing", detail=f"UnityPlayer.dll missing: {unity}")
    if sha256_file_upper(unity) != pins["UnityPlayer.dll"]:
        return replace(gate, status="mismatched", detail="UnityPlayer.dll hash differs")
    return gate


def regenerate(contract):
    from scripts.game_data.levelscript_family_regenerate import Build, open_selected_build
    from scripts.game_data.memorypack.record_sources import ordered_record
    image,pins = open_selected_build()
    build = Build(image,pins)
    records = [ordered_record(build,row) for row in contract["records"]]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"],
                                        gameassembly=image.gameassembly,metadata=image.metadata_path)
    if gate.status != "validated" or sha256_file_upper(image.gameassembly.parent/"UnityPlayer.dll") != pins["UnityPlayer.dll"]:
        raise ValueError(f"spawnerRecords.inputsChanged:{gate.status}:{gate.detail}")
    return {**contract,"nativeInputs":pins,"records":records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--report", type=Path, default=Path("reports/game_data/spawner_record_sources_native.json"))
    args = parser.parse_args()
    if args.write and not args.regenerate:
        parser.error("--write requires --regenerate")
    report = {"validator":"spawnerRecords", "source":str(CONTRACT), "status":"validation_failed"}
    try:
        contract = read_contract()
        if not args.regenerate:
            gate = check_spawner_records_native_inputs()
            if gate.status != "validated":
                raise ValueError(f"native-inputs:{gate.status}:{gate.detail}")
        current = regenerate(contract)
        if not args.regenerate and current != contract:
            raise ValueError("spawnerRecords.source: reviewed facts differ")
        if args.write:
            CONTRACT.write_text(json.dumps(current, indent=2)+"\n", encoding="utf8")
        report.update(status="validated", nativeInputs=current["nativeInputs"], recordCount=len(current["records"]))
    except (ValueError, OSError, KeyError, TypeError, IndexError, struct.error) as exc:
        report.update(failedCheck=str(exc).split(":",1)[0], detail=str(exc)[:1000])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("Spawner source validation: "+report["status"]+(": "+report["detail"] if "detail" in report else ""))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
