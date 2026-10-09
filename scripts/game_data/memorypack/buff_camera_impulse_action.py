"""Named camera impulse storage with independent envelope, curve and target joins.

Raw vectors, flags and enum bits remain stored values. Provider selection,
curve evaluation and the resulting camera impulse remain separate obligations.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import animation_curve as curves
from scripts.game_data.memorypack.value_wrapper_sources import validate_inline_wrapper_fields

LABEL="buffCameraImpulseAction"
CONTRACT_PATH=CONTRACTS_DIR / "buff_camera_impulse_action_native.json"
CHILDREN=("target","animationCurve")


def _contract() -> dict[str, Any]:
    value,_=read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-camera-impulse-action-native-contract.v1",status="exact-current-build",label=LABEL)
    if (set(value.get("records",{}))!={"cameraImpulse","impulseDefinition","envelopeDefinition"}
            or value.get("actionDispatch")!={"36":"cameraImpulse"}
            or {k:len(v["members"]) for k,v in value["records"].items()}!={
                "cameraImpulse":12,"impulseDefinition":18,"envelopeDefinition":7}):
        raise ValueError(f"{LABEL}.contract:shape")
    camera=value["records"]["cameraImpulse"];impulse=value["records"]["impulseDefinition"]
    vector=next(m for m in camera["members"] if m["fieldName"]=="_positionOffset")
    if (vector.get("inlineSource",{}).get("mode")!="inline-cursor-struct12"
            or impulse["members"][-1].get("providerOutputSource",{}).get("mode")!="provider-output32"
            or value["records"]["envelopeDefinition"].get("inlineValueFlow",{}).get("mode")!=
                "reader-and-inline-wrapper-field-flow"
            or value.get("childTypes")!={"member18":"Beyond.Gameplay.Core.CameraImpulseAction+ImpulseDefinitionData",
                "member7":"Cinemachine.CinemachineImpulseManager+EnvelopeDefinition",
                "curve":"UnityEngine.AnimationCurve","target":"Beyond.Gameplay.Core.TargetSettings"}):
        raise ValueError(f"{LABEL}.contract:child-or-source-shape")
    for record in value["records"].values():
        for member in record["members"]:
            if member["kind"] in value["childTypes"] and (
                    member["declaredType"]!=value["childTypes"][member["kind"]]
                    or member.get("sourceContextInstructionRva") is None):
                raise ValueError(f"{LABEL}.contract:typed-child={member['fieldName']}")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int,_contract()["actionDispatch"]))


def _members(contract: dict) -> dict:
    return {k:[{"fieldName":m["fieldName"],"kind":m["kind"]} for m in r["members"]]
            for k,r in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str="", field: str="") -> None:
    contract=_contract();source=contract["records"][record]["sourceContract"] if record else CONTRACT_PATH.name
    error=CensusGateError(f"{LABEL}.{check}",source=(CONTRACTS_DIR/source).as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=record,field=field,nativeInputs=contract["nativeInputs"])
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract=_contract();expected=contract["nativeInputs"]
    gate=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"])
    if gate.status!="validated":return {"status":gate.status,"detail":gate.detail,"nativeInputs":expected}
    for name in CHILDREN:
        child=children.get(name,{})
        if child.get("status")!="validated" or child.get("nativeInputs")!=expected:
            _fail("shared-child",{"name":name,"nativeInputs":expected},child)
    unity=Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll",expected["UnityPlayer.dll"],"missing-or-mismatched")
    image=open_native_image(gate.gameassembly,gate.metadata)
    path=CONTRACTS_DIR / contract["records"]["cameraImpulse"]["sourceContract"]
    source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,
        image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    proved=named.validate_named_records(image,source,
        {k:v for k,v in contract["records"].items() if k!="envelopeDefinition"},label=LABEL,fail=_fail)
    proved["envelopeDefinition"]=validate_inline_wrapper_fields(image,source,contract["records"]["envelopeDefinition"],
        label=LABEL,fail=lambda check,expected,actual:_fail(check,expected,actual,record="envelopeDefinition"))
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    record=contract["records"]["cameraImpulse"];route=routes.get(36)
    if (audit.get("status")!="validated" or route is None or route.status!="resolved"
            or route.wrapper_name!=record["wrapperTypeName"]
            or list(route.member_order)!=[m["fieldName"] for m in record["members"]]
            or list(route.member_declared_types)!=[m["declaredType"] for m in record["members"]]):
        _fail("dispatcher-members",record["wrapperTypeName"],None if route is None else route.row(),record="cameraImpulse")
    after=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!="validated":return {"status":after.status,"detail":after.detail,"nativeInputs":expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll-after",expected["UnityPlayer.dll"],"mismatched")
    return {"status":"validated","nativeInputs":expected,"recordMembers":proved,
            "actionDispatch":contract["actionDispatch"],"evidenceBoundary":contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    contract=_contract();context=native_validation.get("children",{});native=context.get("cameraImpulse",{})
    if (native_validation.get("status")!="validated" or native.get("status")!="validated"
            or native_validation.get("nativeInputs")!=contract["nativeInputs"]
            or native.get("nativeInputs")!=contract["nativeInputs"]
            or native.get("recordMembers")!=_members(contract) or native.get("actionDispatch")!=contract["actionDispatch"]
            or any(context.get(n,{}).get("status")!="validated" or context[n].get("nativeInputs")!=contract["nativeInputs"] for n in CHILDREN)
            or str(tag) not in contract["actionDispatch"] or not isinstance(data,bytes) or not source
            or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),"camera-impulse-action")!=tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    def record(key: str) -> dict[str, Any]:
        at=reader.pos;plan=contract["records"][key];fields=[]
        if reader.peek()==255:
            reader.take(1,"null-"+key)
            return {"start":at,"end":reader.pos,"status":"exact-null-wrapper","namedFields":[],"recursiveStoredSchemaExact":True}
        reader.header(len(plan["members"]))
        for member in plan["members"]:
            begin=reader.pos;kind=member["kind"];value={}
            if kind in {"byte","scalar32","raw12"}:
                value["rawHex"]=reader.take({"byte":1,"scalar32":4,"raw12":12}[kind],member["fieldName"]).hex().upper()
            elif kind=="byte-payload":
                reader.byte_payload();value.update(rawHex=data[begin:reader.pos].hex().upper(),payloadEncoding="unresolved")
            elif kind in {"member18","member7"}:
                value["child"]=record("impulseDefinition" if kind=="member18" else "envelopeDefinition")
            elif kind=="curve":
                reader.curve_profile()
                value["child"]=curves.decode_curve(data,source=source,digest=digest,start=begin,end=reader.pos,native_validation=context["animationCurve"])
            elif kind=="target":
                reader.target_profile();span={"start":begin,"end":reader.pos,"fieldName":member["fieldName"]}
                value["child"]=({**span,"status":"exact-null-wrapper","recursiveStoredSchemaExact":True}
                    if data[begin:reader.pos]==b"\xff" else target_decoder(data,source,digest,span,context))
            else:raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if "child" in value and (value["child"].get("recursiveStoredSchemaExact") is not True
                    or [value["child"].get("start"),value["child"].get("end")]!=[begin,reader.pos]):
                raise ValueError(f"{LABEL}.decode:child-span at={begin}")
            fields.append({"fieldName":member["fieldName"],"declaredType":member["declaredType"],"kind":kind,"start":begin,"end":reader.pos,**value})
        return {"start":at,"end":reader.pos,"typeName":plan["runtimeTypeName"],"namedFields":fields,"recursiveStoredSchemaExact":True}
    parent=record("cameraImpulse")
    if reader.pos!=end:raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema":"endfield.buff-camera-impulse-action-receipt.v1","source":source,"logicalSha256":digest.upper(),
            "tag":tag,"typeName":contract["records"]["cameraImpulse"]["runtimeTypeName"],"start":start,"end":end,
            "parent":parent,"recursiveStoredSchemaExact":True,"runtimeMeaningExact":False}
