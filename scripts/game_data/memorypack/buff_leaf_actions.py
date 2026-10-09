"""Named Buff actions whose serialized payload has no recursive children.

Four inherited fields still do not establish a no-op or sequence behavior.
Every named action requires its independent source and dispatcher proof.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named

LABEL="buffLeafActions"
CONTRACT_PATH=CONTRACTS_DIR / "buff_leaf_actions_native.json"
READ_ORDER=[{"fieldName":"isEnable","kind":"byte"},{"fieldName":"priorityLevel","kind":"scalar32"},
            {"fieldName":"priorityOffset","kind":"scalar32"},{"fieldName":"serverActionIndex","kind":"scalar32"}]


def _contract() -> dict[str,Any]:
    value,_=read_reviewed_contract(CONTRACT_PATH,schema="endfield.buff-leaf-actions-native-contract.v5",
        status="exact-current-build",label=LABEL)
    if (set(value.get("records",{}))!={"notNextCheck","pauseBuffTime","abnormalStartFinish","refreshBuffAttrModifier","squadInFight","moveGait"}
            or len(value["actionDispatch"])!=6 or set(value["actionDispatch"].values())!=set(value["records"])
            or any(r.get("inheritedMemberCount")!=4 or [{"fieldName":m["fieldName"],"kind":m["kind"]} for m in r["members"][:4]]!=READ_ORDER
                   or any(m["kind"] not in {"byte","scalar32"} for m in r["members"])
                   for r in value["records"].values())):raise ValueError(f"{LABEL}.contract:shape")
    return value


def _members(contract: dict) -> dict:
    return {k:[{"fieldName":m["fieldName"],"kind":m["kind"]} for m in r["members"]]
            for k,r in contract["records"].items()}


def supported_tags() -> frozenset[int]:return frozenset(map(int,_contract()["actionDispatch"]))


def _fail(check: str, expected: Any, actual: Any, *, record: str="", field: str="") -> None:
    contract=_contract();source=contract["records"][record]["sourceContract"] if record else CONTRACT_PATH.name
    error=CensusGateError(f"{LABEL}.{check}",source=(CONTRACTS_DIR/source).as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=record,field=field,nativeInputs=contract["nativeInputs"])
    raise error


def validate_current_native_contract() -> dict[str,Any]:
    contract=_contract();expected=contract["nativeInputs"]
    gate=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"])
    if gate.status!="validated":return {"status":gate.status,"detail":gate.detail,"nativeInputs":expected}
    unity=Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll",expected["UnityPlayer.dll"],"missing-or-mismatched")
    image=open_native_image(gate.gameassembly,gate.metadata);proved={}
    for key,record in contract["records"].items():
        path=CONTRACTS_DIR / record["sourceContract"];source=json.loads(path.read_bytes())
        buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,
            source=str(gate.gameassembly),contract_path=path)
        proved.update(named.validate_named_records(image,source,{key:record},label=LABEL,fail=_fail))
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    for tag,key in contract["actionDispatch"].items():
        record=contract["records"][key];route=routes.get(int(tag))
        if (audit.get("status")!="validated" or route is None or route.status!="resolved"
                or route.wrapper_name!=record["wrapperTypeName"]
                or list(route.member_order)!=[m["fieldName"] for m in record["members"]]
                or list(route.member_declared_types)!=[m["declaredType"] for m in record["members"]]):
            _fail("dispatcher-members",record["wrapperTypeName"],None if route is None else route.row(),record=key)
    after=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!="validated":return {"status":after.status,"detail":after.detail,"nativeInputs":expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll-after",expected["UnityPlayer.dll"],"mismatched")
    return {"status":"validated","nativeInputs":expected,"recordMembers":proved,"actionDispatch":contract["actionDispatch"],"evidenceBoundary":contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str,Any]) -> dict[str,Any]:
    contract=_contract();native=native_validation.get("children",{}).get("leafActions",{})
    if (native_validation.get("status")!="validated" or native.get("status")!="validated"
            or native_validation.get("nativeInputs")!=contract["nativeInputs"] or native.get("nativeInputs")!=contract["nativeInputs"]
            or native.get("recordMembers")!=_members(contract) or native.get("actionDispatch")!=contract["actionDispatch"]
            or str(tag) not in contract["actionDispatch"] or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper() or type(start) is not int or type(end) is not int
            or not 0<=start<end<=len(data)):raise ValueError(f"{LABEL}.decode:native-source-or-span")
    physical=bytes([tag]) if tag<250 else b"\xfa"+struct.pack("<H",tag)
    if data[start:start+len(physical)]!=physical:
        raise ValueError(f"{LABEL}.decode:physical-union-tag")
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),"leaf-action")!=tag:raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    record=contract["records"][contract["actionDispatch"][str(tag)]];fields=[]
    if reader.peek()==255:reader.take(1,"null-leaf-wrapper")
    else:
        reader.header(len(record["members"]))
        for member in record["members"]:
            begin=reader.pos;raw=reader.take(1 if member["kind"]=="byte" else 4,member["fieldName"])
            fields.append({"fieldName":member["fieldName"],"declaredType":member["declaredType"],"kind":member["kind"],
                           "start":begin,"end":reader.pos,"rawHex":raw.hex().upper()})
    if reader.pos!=end:raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema":"endfield.buff-leaf-action-receipt.v1","source":source,"logicalSha256":digest.upper(),
            "tag":tag,"typeName":record["runtimeTypeName"],"start":start,"end":end,"namedFields":fields,
            "recursiveStoredSchemaExact":True,"runtimeMeaningExact":False}
