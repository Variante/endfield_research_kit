"""Named time-dilation and hurt-animation storage with independent children.

Curves, lists, directional values and Blackboard providers must close on their
original spans. This module does not evaluate curves or execute the actions.
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
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import animation_curve as curves
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_direction_target_children as direction_children
from scripts.game_data.memorypack import buff_super_armor_blackboard_child_receipt as armor_values

LABEL = "buffCurveActions"
CONTRACT_PATH = CONTRACTS_DIR / "buff_curve_actions_native.json"
CHILDREN = ("target", "effectVectors", "direction", "directionTargets", "selector", "selectorGeometry", "selectorPostprocessors", "armorValues", "animationCurve")


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-curve-actions-native-contract.v3", status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != {"timeDilation", "enemyHurtAnim", "hitStop", "charHurtAnim"}
            or len(value.get("actionDispatch", {})) != 4
            or set(value["actionDispatch"].values()) != set(value["records"])):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in row["members"]]
            for key, row in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    contract = _contract()
    source = contract["records"][record]["sourceContract"] if record else CONTRACT_PATH.name
    error = CensusGateError(f"{LABEL}.{check}", source=(CONTRACTS_DIR/source).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract["nativeInputs"])
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in CHILDREN:
        child = children.get(name, {})
        if child.get("status") != "validated" or child.get("nativeInputs") != expected:
            _fail("shared-child", {"name": name, "nativeInputs": expected}, child)
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata)
    proved = {}
    for key, record in contract["records"].items():
        path = CONTRACTS_DIR / record["sourceContract"]
        source = json.loads(path.read_bytes())
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        extra = contract["additionalSourceWindows"].get(path.name, [])
        image.check_windows(extra, label=LABEL)
        source["codeWindows"] += extra
        proved.update(records_native.validate_named_records(image, source, {key: record}, label=LABEL, fail=_fail))
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract["actionDispatch"].items():
        record = contract["records"][key]; route = routes.get(int(tag))
        if (audit.get("status") != "validated" or route is None or route.status != "resolved"
                or route.wrapper_name != record["wrapperTypeName"]
                or list(route.member_order) != [m["fieldName"] for m in record["members"]]
                or list(route.member_declared_types) != [m["declaredType"] for m in record["members"]]):
            _fail("dispatcher-members", record["wrapperTypeName"], None if route is None else route.row(), record=key)
    after=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!="validated":
        return {"status":after.status,"detail":after.detail,"nativeInputs":expected}
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": contract["actionDispatch"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get("children", {})
    native = context.get("curveActions", {})
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract) or native.get("actionDispatch") != contract["actionDispatch"]
            or any(context.get(name, {}).get("status") != "validated"
                   or context[name].get("nativeInputs") != contract["nativeInputs"] for name in CHILDREN)
            or str(tag) not in contract["actionDispatch"] or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), "curve-action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    record = contract["records"][contract["actionDispatch"][str(tag)]]
    fields = []
    if reader.peek() == 255:
        reader.take(1, "null-action-wrapper")
    else:
        reader.header(len(record["members"]))
        for member in record["members"]:
            begin = reader.pos; value = {}; kind = member["kind"]
            kind = {"target":"target-profile", "curve":"curve-profile", "direction":"direction-profile"}.get(kind,kind)
            if kind in ("byte", "byte-enum", "scalar32", "raw4"):
                value["rawHex"] = reader.take(1 if kind in ("byte", "byte-enum") else 4, member["fieldName"]).hex().upper()
            elif kind == "byte-payload":
                reader.byte_payload(); value.update(rawHex=data[begin:reader.pos].hex().upper(), payloadEncoding="unresolved")
            elif kind == "scalar-payload":
                reader.scalar_payload()
                proof = scalar.decode_adding_cooldown(data, begin, reader.pos, native_validation=context["effectVectors"]["scalarNative"])
                if proof.get("wholeValueExact") is not True or [proof.get("startOffset"),proof.get("consumedEnd")] != [begin,reader.pos]:
                    raise ValueError(f"{LABEL}.decode:scalar-span at={begin}")
                value["child"] = {**proof,"start":begin,"end":reader.pos,"recursiveStoredSchemaExact":True}
            elif kind == "target-profile":
                reader.target_profile()
                value["child"] = _target(data,source,digest,begin,reader.pos,context,target_decoder)
            elif kind == "counted-target-profiles":
                count = reader.count(1,nullable=True);elements=[]
                for _ in range(max(0,count)):
                    at=reader.pos;reader.target_profile()
                    elements.append(_target(data,source,digest,at,reader.pos,context,target_decoder))
                value["child"]={"start":begin,"end":reader.pos,"count":count,"elements":elements,"recursiveStoredSchemaExact":True}
            elif kind == "curve-profile":
                reader.curve_profile()
                value["child"]=curves.decode_curve(data,source=source,digest=digest,start=begin,end=reader.pos,
                    native_validation=context["animationCurve"])
            elif kind == "direction-profile":
                reader.direction_profile()
                value["child"]=direction_children.decode_direction(data,source=source,digest=digest,
                    start=begin,end=reader.pos,children=context,target_decoder=target_decoder)
            elif kind == "impact-profile":
                reader.scalar_flag_payload()
                value["child"]=armor_values.decode_blackboard_value(data,source=source,logical_sha256=digest,
                    start=begin,end=reader.pos,provider_type=member["declaredType"],native_validation=context["armorValues"])
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if "child" in value and (value["child"].get("recursiveStoredSchemaExact") is not True
                    or [value["child"].get("start"),value["child"].get("end")] != [begin,reader.pos]):
                raise ValueError(f"{LABEL}.decode:child-span at={begin}")
            fields.append({"fieldName": member["fieldName"], "declaredType": member["declaredType"],
                           "kind": member["kind"], "start": begin, "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema":"endfield.buff-curve-action-receipt.v1","source":source,"logicalSha256":digest.upper(),
        "tag":tag,"typeName":record["runtimeTypeName"],"start":start,"end":end,"namedFields":fields,
        "recursiveStoredSchemaExact":True,"runtimeMeaningExact":False}


def _target(data,source,digest,start,end,context,decoder):
    span={"start":start,"end":end}
    proof=({**span,"status":"exact-null","recursiveStoredSchemaExact":True}
            if data[start:end]==b"\xff" else decoder(data,source,digest,span,context))
    if proof.get("recursiveStoredSchemaExact") is not True or [proof.get("start"),proof.get("end")]!=[start,end]:
        raise ValueError(f"{LABEL}.decode:target-child-span at={start}")
    return proof
