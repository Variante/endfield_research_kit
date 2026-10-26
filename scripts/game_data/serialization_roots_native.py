"""Selected world-root counts and bounded pooled-string/list source joins.

These bounded source facts do not admit positive list elements, property
records, default formatter selection or execution of a LevelScript owner.
"""
from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Use python -m scripts.game_data.serialization_roots_native")

import argparse
from dataclasses import replace
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR

CONTRACT = CONTRACTS_DIR / "serialization_roots_native.json"
SCHEMA = "endfield.serialization-roots-native.v1"


def read_contract(*, allow_pending=False):
    contract = json.loads(CONTRACT.read_bytes())
    statuses = {"validated","pendingReview"} if allow_pending else {"validated"}
    if contract.get("schema") != SCHEMA or contract.get("status") not in statuses:
        raise ValueError(f"serializationRoots.contract:schema/status:{CONTRACT}")
    if not allow_pending and (not contract.get("records") or any(not row.get("codeWindows") or not row.get("fieldSources")
            or any(not source.get("readerArgument") or not source.get("wrapperArgument") for source in row["fieldSources"])
            for row in contract["records"])):
        raise ValueError(f"serializationRoots.contract:incomplete-source-facts:{CONTRACT}")
    return contract


def check_root_native_inputs():
    pins = read_contract()["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"])
    if gate.status != "validated":
        return gate
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return replace(gate,status="missing",detail=f"UnityPlayer.dll missing: {unity}")
    if sha256_file_upper(unity) != pins["UnityPlayer.dll"]:
        return replace(gate,status="mismatched",detail="UnityPlayer.dll hash differs")
    return gate


def regenerate(contract):
    from scripts.game_data.levelscript_family_regenerate import open_selected_build, Build
    image,pins = open_selected_build()
    build = Build(image,pins)
    from scripts.game_data.codecs.levelscript import top_level_prefix, top_level_tail
    for name, domain in (("Beyond.Gameplay.LevelScriptEndType",top_level_prefix.END_TYPE_NAMES),
                         ("Beyond.GEnums.LevelScriptType",top_level_prefix.LEVEL_SCRIPT_TYPE_NAMES),
                         ("Beyond.GEnums.LevelScriptResetModeType",top_level_prefix.RESET_MODE_NAMES),
                         ("Beyond.Gameplay.LevelScriptStartType",top_level_tail.START_TYPE_NAMES)):
        build.derive_enum({"typeName":name,"backingType":"System.Int32",
                           "members":[{"id":value,"name":label} for value,label in domain.items()]})
    from scripts.game_data.memorypack.record_sources import bounded_reference_record
    records = [bounded_reference_record(build,row) for row in contract["records"]]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"],gameassembly=image.gameassembly,metadata=image.metadata_path)
    if gate.status != "validated" or sha256_file_upper(image.gameassembly.parent/"UnityPlayer.dll") != pins["UnityPlayer.dll"]:
        raise ValueError(f"serializationRoots.inputsChanged:{gate.status}:{gate.detail}")
    return {**contract,"status":"validated","nativeInputs":pins,"records":records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate",action="store_true")
    parser.add_argument("--write",action="store_true")
    parser.add_argument("--report",type=Path,default=Path("reports/game_data/serialization_roots_native.json"))
    args = parser.parse_args()
    if args.write and not args.regenerate:
        parser.error("--write requires --regenerate")
    report = {"validator":"serializationRoots","source":str(CONTRACT),"status":"validation_failed"}
    try:
        contract = read_contract(allow_pending=args.regenerate)
        if not args.regenerate:
            gate = check_root_native_inputs()
            if gate.status != "validated":raise ValueError(f"native-inputs:{gate.status}:{gate.detail}")
        current = regenerate(contract)
        if not args.regenerate and current != contract:raise ValueError("serializationRoots.source:reviewed facts differ")
        if args.write:CONTRACT.write_text(json.dumps(current,indent=2)+"\n",encoding="utf8")
        report.update(status="validated",nativeInputs=current["nativeInputs"])
    except (ValueError,OSError,KeyError,TypeError,IndexError,RuntimeError) as exc:
        report.update(failedCheck=str(exc).split(":",1)[0],detail=str(exc)[:1000])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("Serialization root source validation: "+report["status"]+(": "+report["detail"] if "detail" in report else ""))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
