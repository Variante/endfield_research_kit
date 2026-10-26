"""Current FunctionArea base additions and the complete factory-hide reader.

Stored field/source proof only; positive building-type lists, other base fields,
provider selection and live factory visibility remain outside this contract.
"""
from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Use python -m scripts.game_data.leveldata_function_area_native")

import argparse
from dataclasses import replace
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs,sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR

CONTRACT = CONTRACTS_DIR / "leveldata_function_area_native.json"
SCHEMA = "endfield.leveldata-function-area-native.v1"


def read_contract(*, allow_pending=False):
    value = json.loads(CONTRACT.read_bytes())
    statuses = {"validated","pendingReview"} if allow_pending else {"validated"}
    if value.get("schema") != SCHEMA or value.get("status") not in statuses:
        raise ValueError(f"functionArea.contract:schema/status:{CONTRACT}")
    if not allow_pending and (not value.get("base",{}).get("fieldSources")
            or not value.get("base",{}).get("codeWindows")
            or len(value.get("description",{}).get("orderedReads",[])) != 7
            or not value.get("description",{}).get("codeWindows")):
        raise ValueError(f"functionArea.contract:incomplete-source-facts:{CONTRACT}")
    return value


def check_function_area_native_inputs():
    pins = read_contract()["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"])
    if gate.status != "validated":return gate
    unity = gate.gameassembly.parent/"UnityPlayer.dll"
    if not unity.is_file():return replace(gate,status="missing",detail=f"UnityPlayer.dll missing: {unity}")
    if sha256_file_upper(unity) != pins["UnityPlayer.dll"]:
        return replace(gate,status="mismatched",detail="UnityPlayer.dll hash differs")
    return gate


def regenerate(contract):
    from scripts.game_data.buff_frontiers_regenerate import _method_row,_type_definition
    from scripts.game_data.il2cpp import protocol
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
    from scripts.game_data.levelscript_family_regenerate import Build,open_selected_build
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.memorypack.record_sources import ordered_record,return_field_source,typed_source_context
    from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
    image,pins = open_selected_build()
    build = Build(image,pins)
    description = ordered_record(build,contract["description"])
    if NativeReferenceContext(image).is_value_type(description["typeName"]):
        raise ValueError(f"functionArea.descriptionReference:{description['typeName']}")
    for source in description["orderedReads"]:
        if source["field"] == "hideSocialFacOwner":
            prove_primitive(image,image.pe.image_base+source["targetRva"],"int32")
    enums = [build.derive_enum(row) for row in contract["enumStorage"]]
    reviewed = contract["base"]
    wrapper = build.wrappers[reviewed["wrapperName"]]
    fields = [[m.name,protocol.canonical_type_name(m.declared_type)] for m in wrapper.members]
    if (wrapper.wrapped_type != reviewed["typeName"] or fields != [[name,protocol.canonical_type_name(kind)] for name,kind in reviewed["fields"]]
            or NativeReferenceContext(image).is_value_type(wrapper.wrapped_type)):
        raise ValueError(f"functionArea.baseDeclarations:{reviewed['typeName']}")
    offsets = protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,_type_definition(image,wrapper.wrapped_type))
    holder = protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,wrapper.type_definition)
    if holder.get("__instance") != 16:raise ValueError(f"functionArea.wrapperHolder:expected=16:actual={holder.get('__instance')}")
    body = image.body_index.body(wrapper.name,"Deserialize")
    rows = decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    headers = [row for row in rows if row["text"].startswith("cmp ") and row["text"].endswith(f", {len(fields):#x}") and len(bytes.fromhex(row["bytes"])) in (4,5)]
    if len(headers) != 1:raise ValueError(f"functionArea.memberCount:expected=1:actual={len(headers)}")
    sources = []
    for field,register in (("enableFactoryHide","al"),("factoryHideDesc","rax")):
        source = return_field_source(image,rows,field,offsets[field],value_register=register)
        target = image.pe.image_base+source["targetRva"]
        if register == "al":prove_primitive(image,target,"bool-byte")
        else:
            call = next(i for i,row in enumerate(rows) if int(row["va"],16)-image.pe.image_base == source["callRva"])
            source["typedContext"] = typed_source_context(image,rows[max(0,call-4):call],field=field,method="ReadValue",argument=description["typeName"])
            build.prove_named_target(target,"MemoryPack.MemoryPackReader","ReadValue")
        sources.append(source)
    spans = {(body.pointer,body.pointer+body.size)}|{(p,p+s) for p,s in image.body_index.chained_fragments.get(body.pointer,())}
    base = {"typeName":reviewed["typeName"],"wrapperName":wrapper.name,"fields":reviewed["fields"],
            "method":_method_row(image,[0,wrapper.name,"Deserialize",0]),
            "memberCountInstruction":[int(headers[0]["va"],16)-image.pe.image_base,headers[0]["bytes"]],
            "fieldSources":sources,"codeWindows":[_window(image,a,b,"complete owned reader coverage") for a,b in sorted(spans)]}
    gate = check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"],gameassembly=image.gameassembly,metadata=image.metadata_path)
    if gate.status != "validated" or sha256_file_upper(image.gameassembly.parent/"UnityPlayer.dll") != pins["UnityPlayer.dll"]:
        raise ValueError(f"functionArea.inputsChanged:{gate.status}:{gate.detail}")
    return {**contract,"status":"validated","nativeInputs":pins,"base":base,"description":description,"enumStorage":enums}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate",action="store_true")
    parser.add_argument("--write",action="store_true")
    parser.add_argument("--report",type=Path,default=Path("reports/game_data/leveldata_function_area_native.json"))
    args = parser.parse_args()
    if args.write and not args.regenerate:parser.error("--write requires --regenerate")
    report = {"validator":"functionArea","source":str(CONTRACT),"status":"validation_failed"}
    try:
        contract = read_contract(allow_pending=args.regenerate)
        if not args.regenerate:
            gate = check_function_area_native_inputs()
            if gate.status != "validated":raise ValueError(f"native-inputs:{gate.status}:{gate.detail}")
        current = regenerate(contract)
        if not args.regenerate and current != contract:raise ValueError("functionArea.source:reviewed facts differ")
        if args.write:CONTRACT.write_text(json.dumps(current,indent=2)+"\n",encoding="utf8")
        report.update(status="validated",nativeInputs=current["nativeInputs"])
    except (ValueError,OSError,KeyError,TypeError,IndexError,RuntimeError) as exc:
        report.update(failedCheck=str(exc).split(":",1)[0],detail=str(exc)[:1000])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("FunctionArea source validation: "+report["status"]+(": "+report["detail"] if "detail" in report else ""))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
