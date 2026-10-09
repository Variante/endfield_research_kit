"""Named IgniteBuffText storage, including an explicit raw Vector2 transfer.

Raw bytes do not evaluate energy, target selection or displayed text.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Callable
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native

LABEL="buffIgniteTextAction"
CONTRACT_PATH=CONTRACTS_DIR / "buff_ignite_text_action_native.json"
CHILDREN=("target",)


def _contract() -> dict[str,Any]:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema="endfield.buff-ignite-text-action-native-contract.v1",
        status="exact-current-build",label=LABEL)
    if (set(c.get("records",{}))!={"igniteText"} or c.get("actionDispatch")!={"207":"igniteText"}
            or len(c["records"]["igniteText"]["members"])!=11):
        raise ValueError(f"{LABEL}.contract:shape")
    raw=[m for m in c["records"]["igniteText"]["members"] if m["kind"]=="raw8"]
    if (len(raw)!=1 or raw[0]["fieldName"]!="offset" or raw[0]["declaredType"]!="UnityEngine.Vector2"
            or (raw[0].get("unmanagedOutputSource") or {}).get("mode")!="unmanaged-return64-float-pair"):
        raise ValueError(f"{LABEL}.contract:raw8-proof")
    targets=[m for m in c["records"]["igniteText"]["members"] if m["kind"]=="target-profile"]
    if (len(targets)!=1 or targets[0]["fieldName"]!="targetSettings"
            or targets[0]["declaredType"]!="Beyond.Gameplay.Core.TargetSettings" or targets[0].get("sourceContextInstructionRva") is None):
        raise ValueError(f"{LABEL}.contract:typed-target")
    return c


def supported_tags() -> frozenset[int]:
    return frozenset(map(int,_contract()["actionDispatch"]))


def _members(c: dict) -> dict:
    return {k:[{"fieldName":m["fieldName"],"kind":m["kind"]} for m in r["members"]] for k,r in c["records"].items()}


def _fail(check: str,expected: Any,actual: Any,*,record: str="igniteText",field: str="") -> None:
    c=_contract();source=c["records"][record]["sourceContract"]
    error=CensusGateError(f"{LABEL}.{check}",source=(CONTRACTS_DIR/source).as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=record,field=field,nativeInputs=c["nativeInputs"])
    raise error


def validate_current_native_contract(*,children: dict[str,Any]) -> dict[str,Any]:
    c=_contract();pins=c["nativeInputs"]
    gate=check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"])
    if gate.status!="validated":return {"status":gate.status,"detail":gate.detail,"nativeInputs":pins}
    for key in CHILDREN:
        child=children.get(key,{})
        if child.get("status")!="validated" or child.get("nativeInputs")!=pins:_fail("shared-child",{"name":key,"nativeInputs":pins},child)
    unity=Path(gate.gameassembly).parent/"UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll",pins["UnityPlayer.dll"],"missing-or-mismatched")
    image=open_native_image(gate.gameassembly,gate.metadata);record=c["records"]["igniteText"]
    path=CONTRACTS_DIR/record["sourceContract"];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,
        source=str(gate.gameassembly),contract_path=path)
    proved=records_native.validate_named_records(image,source,c["records"],label=LABEL,fail=_fail)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(207)
    if (audit.get("status")!="validated" or route is None or route.status!="resolved"
            or route.wrapper_name!=record["wrapperTypeName"]
            or list(route.member_order)!=[m["fieldName"] for m in record["members"]]
            or list(route.member_declared_types)!=[m["declaredType"] for m in record["members"]]):
        _fail("dispatcher-members",record["wrapperTypeName"],None if route is None else route.row())
    after=check_installed_native_inputs(pins["GameAssembly.dll"],pins["global-metadata.dat"],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!="validated":return {"status":after.status,"detail":after.detail,"nativeInputs":pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins["UnityPlayer.dll"]:_fail("UnityPlayer.dll-after",pins["UnityPlayer.dll"],"mismatched")
    return {"status":"validated","nativeInputs":pins,"recordMembers":proved,"actionDispatch":c["actionDispatch"],"evidenceBoundary":c["evidenceBoundary"]}


def decode_action(data: bytes,*,source: str,digest: str,start: int,end: int,tag: int,
                  native_validation: dict[str,Any],target_decoder: Callable[...,dict[str,Any]]) -> dict[str,Any]:
    c=_contract();context=native_validation.get("children",{});native=context.get("igniteText",{})
    if (native_validation.get("status")!="validated" or native.get("status")!="validated"
            or native_validation.get("nativeInputs")!=c["nativeInputs"] or native.get("nativeInputs")!=c["nativeInputs"]
            or native.get("recordMembers")!=_members(c) or native.get("actionDispatch")!=c["actionDispatch"]
            or any(context.get(k,{}).get("status")!="validated" or context[k].get("nativeInputs")!=c["nativeInputs"] for k in CHILDREN)
            or type(tag) is not int or tag!=207 or not isinstance(data,bytes) or not source
            or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    if data[start:start+1]!=bytes([tag]):raise ValueError(f"{LABEL}.decode:physical-union-tag")
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),"igniteText-action")!=tag:raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    record=c["records"]["igniteText"];fields=[]
    if reader.peek()==255:reader.take(1,"null-action-wrapper")
    else:
        reader.header(len(record["members"]))
        for m in record["members"]:
            at=reader.pos;kind=m["kind"];value={}
            if kind in {"byte","scalar32","raw8"}:
                value["rawHex"]=reader.take({"byte":1,"scalar32":4,"raw8":8}[kind],m["fieldName"]).hex().upper()
            elif kind=="byte-payload":
                reader.byte_payload();value.update(rawHex=data[at:reader.pos].hex().upper(),payloadEncoding="unresolved")
            elif kind=="target-profile":
                reader.target_profile();span={"start":at,"end":reader.pos,"fieldName":m["fieldName"]}
                proof=({**span,"status":"exact-null-wrapper","recursiveStoredSchemaExact":True} if data[at:reader.pos]==b"\xff"
                    else target_decoder(data,source,digest,span,context))
                if proof.get("recursiveStoredSchemaExact") is not True or [proof.get("start"),proof.get("end")]!=[at,reader.pos]:
                    raise ValueError(f"{LABEL}.decode:target-child-span at={at}")
                value["child"]=proof
            else:raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            fields.append({"fieldName":m["fieldName"],"declaredType":m["declaredType"],"kind":kind,"start":at,"end":reader.pos,**value})
    if reader.pos!=end:raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema":"endfield.buff-ignite-text-action-receipt.v1","source":source,"logicalSha256":digest.upper(),
        "tag":tag,"typeName":record["runtimeTypeName"],"start":start,"end":end,"namedFields":fields,
        "recursiveStoredSchemaExact":True,"runtimeMeaningExact":False}
