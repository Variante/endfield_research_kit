"""Prove selected node string fields without admitting other fields or owners."""
from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Use python -m scripts.game_data.levelscript_node_strings_native")

import argparse
from dataclasses import replace
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR

CONTRACT = CONTRACTS_DIR / "levelscript_node_strings_native.json"
SCHEMA = "endfield.levelscript-node-string-sources-native.v4"


def read_contract(*, allow_pending=False):
    contract = json.loads(CONTRACT.read_bytes())
    statuses = {"validated","pendingReview"} if allow_pending else {"validated"}
    if contract.get("schema") != SCHEMA or contract.get("status") not in statuses:
        raise ValueError(f"nodeStrings.contract:schema/status:{CONTRACT}")
    if not allow_pending and (not contract.get("records") or any(not row.get("codeWindows") or not row.get("stringSources")
            or len(row.get("prefixReads",[]))!=4 or not row.get("primitiveWindows")
            or any(not source.get("readerArgument") or not source.get("wrapperArgument") for source in [item["source"] for item in row["stringSources"]])
            for row in contract["records"])):
        raise ValueError(f"nodeStrings.contract:incomplete-source-facts:{CONTRACT}")
    return contract


def check_node_string_native_inputs():
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


def derive_record(build, reviewed):
    """The caller owns the selected build gate; only the UID prefix is proved."""
    from scripts.game_data.levelscript_family_regenerate import select_calls
    from scripts.game_data.memorypack.record_sources import setter_reference_source,normal_source_rows
    from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
    from scripts.game_data.memorypack.struct_output_sources import check_reader_ref_wrapper_abi
    from scripts.game_data.buff_frontiers_regenerate import _method_row
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.il2cpp import protocol
    image = build.image
    wrapper = build.wrappers[reviewed["wrapperName"]]
    declared = [[m.name,protocol.canonical_type_name(m.declared_type)] for m in wrapper.members]
    expected = [[name,protocol.canonical_type_name(kind)] for name,kind in reviewed["nativeDeclaredTypes"]]
    if declared != expected:
        raise ValueError(f"nodeStrings.declarations:{wrapper.name}:expected={expected[:16]}:actual={declared[:16]}:counts={len(expected)}/{len(declared)}")
    wire_names = [name for name,kind in reviewed["fields"]]
    if len(wire_names)!=len(wrapper.members) or any(m.name not in (wire,"_"+wire)
            for wire,m in zip(wire_names,wrapper.members)):
        raise ValueError(f"nodeStrings.fieldOrder:{wrapper.name}")
    method = _method_row(image,[0,wrapper.name,"Deserialize",0])
    def fail(check, expected, actual):
        raise ValueError(f"nodeStrings.{check}:{wrapper.name}:expected={str(expected)[:200]}:actual={str(actual)[:300]}")
    check_reader_ref_wrapper_abi(image,{"readerMethod":method,"wrapperTypeDefinition":wrapper.type_definition},fail=fail)
    body = image.body_index.body(wrapper.name,"Deserialize")
    from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
    rows = decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(body.pointer,body.size),body.pointer) if reviewed.get("inlinePrefix") is True else body.rows
    selection = None
    if reviewed.get("initializedCachedPrefix") is True:
        if reviewed.get("inlinePrefix") is not True:raise ValueError("nodeStrings.cachedPrefix:requires-inline-profile")
        from scripts.game_data.memorypack.record_prefix_sources import selected_initialized_prefix
        rows,selection=selected_initialized_prefix(build,wrapper)
    elif "initializedCachedPrefix" in reviewed:raise ValueError("nodeStrings.cachedPrefix:explicit-true-profile")
    prefix = [["dontLogWarning","bool"],["ID","int32"],["releaseWhenExecutionFinished","bool"],["uid","string"]]
    if reviewed["fields"][:4] != prefix:
        raise ValueError(f"nodeStrings.prefixPlan:{wrapper.name}")
    for member,kind in zip(wrapper.members[:4],("System.Boolean","System.Int32","System.Boolean","System.String"),strict=True):
        if protocol.canonical_type_name(member.declared_type)!=kind:
            raise ValueError(f"nodeStrings.prefixDeclaration:{wrapper.name}:{member.name}:expected={kind}:actual={member.declared_type}")
    setters = [_method_row(image,[0,m.declaring_wrapper,f"set___{m.name}__",0]) for m in wrapper.members[:4]]
    inline=reviewed.get("inlinePrefix",False)
    if type(inline) is not bool:raise ValueError("nodeStrings.inlinePrefix:explicit-boolean")
    header,reads,writes,_ = select_calls(normal_source_rows(rows),len(wrapper.members),
        [image.pe.image_base+row[3] for row in setters],inline_members=range(4) if inline else (),prefix_count=4)
    prefix_reads = []
    helper_spans = set()
    for (field,kind),read,write,setter in zip(prefix,reads,writes,setters,strict=True):
        pointer = int(read["text"].split()[1],16)
        if kind != "string":
            prove_primitive(image,pointer,"bool-byte" if kind=="bool" else "int32")
            helper_spans.add((pointer,image.body_index.extents[pointer]))
            helper_spans.update((p,p+n) for p,n in image.body_index.chained_fragments.get(pointer,()))
        transfer={}
        if inline:
            from scripts.game_data.il2cpp.reference_field_programs import inlined_base_setter
            transfer["inlineSetter"]=inlined_base_setter(image,build.body,build.wrappers,wrapper.members[len(prefix_reads)],rows,read,write)
        prefix_reads.append({"field":field,"kind":kind,"callRva":int(read["va"],16)-image.pe.image_base,
            "targetRva":pointer-image.pe.image_base,"setter":setter,"setterCallRva":None if inline else int(write["va"],16)-image.pe.image_base,**transfer})
    sources = []
    for wire,native in reviewed["stringFields"]:
        if [wire,"string"] not in reviewed["fields"]:
            raise ValueError(f"nodeStrings.stringField:{wrapper.name}:{wire}")
        members = [m for m in wrapper.members if m.name==native]
        if len(members)!=1 or members[0].kind!="string":
            raise ValueError(f"nodeStrings.stringDeclaration:{wrapper.name}:{native}")
        if inline:
            from scripts.game_data.memorypack.record_sources import return_field_source
            transfer=prefix_reads[3]["inlineSetter"]
            fact={**return_field_source(image,rows,native,transfer["fieldOffset"]),"inlineSetter":transfer}
        else:fact = setter_reference_source(build,rows,members[0])
        if wire!="uid" or fact["callRva"]!=prefix_reads[3]["callRva"]:
            raise ValueError(f"nodeStrings.prefixSource:{wrapper.name}:{wire}")
        build.prove_pooled_string_target(image.pe.image_base+fact["targetRva"])
        sources.append({"field":wire,"source":fact})
    spans = {(body.pointer,body.pointer+body.size)}|{(p,p+n) for p,n in image.body_index.chained_fragments.get(body.pointer,())}
    return {**{k:reviewed[k] for k in ("wrapperName","fields","nativeDeclaredTypes","stringFields")},**({"inlinePrefix":True} if inline else {}),
        **({"initializedCachedPrefix":True,"prefixSelection":selection} if selection is not None else {}),
        "method":method,"stringSources":sources,
        "prefixReads":prefix_reads,"memberCountInstruction":[int(header['va'],16)-image.pe.image_base,header['bytes']],
        "primitiveWindows":[_window(image,a,b,"complete owned primitive bytes; buffered source proof only") for a,b in sorted(helper_spans)],
        "codeWindows":[_window(image,a,b,"complete owned reader; only listed string source programs admitted") for a,b in sorted(spans)]}


def regenerate(contract):
    from scripts.game_data.levelscript_family_regenerate import open_selected_build, Build
    image,pins = open_selected_build()
    build = Build(image,pins)
    records = [derive_record(build,row) for row in contract["records"]]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"],gameassembly=image.gameassembly,metadata=image.metadata_path)
    if gate.status != "validated" or sha256_file_upper(image.gameassembly.parent/"UnityPlayer.dll") != pins["UnityPlayer.dll"]:
        raise ValueError(f"nodeStrings.inputsChanged:{gate.status}:{gate.detail}")
    return {**contract,"status":"validated","nativeInputs":pins,"records":records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regenerate",action="store_true")
    parser.add_argument("--write",action="store_true")
    parser.add_argument("--report",type=Path,default=Path("reports/game_data/levelscript_node_strings_native.json"))
    args = parser.parse_args()
    if args.write and not args.regenerate:
        parser.error("--write requires --regenerate")
    report = {"validator":"nodeStrings","source":str(CONTRACT),"status":"validation_failed"}
    try:
        contract = read_contract(allow_pending=args.regenerate)
        if not args.regenerate:
            gate = check_node_string_native_inputs()
            if gate.status != "validated":raise ValueError(f"native-inputs:{gate.status}:{gate.detail}")
        current = regenerate(contract)
        if not args.regenerate and current != contract:raise ValueError("nodeStrings.source:reviewed facts differ")
        if args.write:CONTRACT.write_text(json.dumps(current,indent=2)+"\n",encoding="utf8")
        report.update(status="validated",nativeInputs=current["nativeInputs"])
    except (ValueError,OSError,KeyError,TypeError,IndexError,RuntimeError) as exc:
        report.update(failedCheck=str(exc).split(":",1)[0],detail=str(exc)[:1000])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("Node string source validation: "+report["status"]+(": "+report["detail"] if "detail" in report else ""))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
