"""Named projectile storage with independently owned vector and list children.

Stored counts, enums, flags and provider bytes do not evaluate gameplay effects.
Every child receipt must close its own original source span.
"""
from __future__ import annotations
import hashlib, json, struct
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
from scripts.game_data.memorypack import buff_create_input_child_receipt as assignments

LABEL = "buffLaunchProjectileAction"
CONTRACT_PATH = CONTRACTS_DIR / "buff_launch_projectile_action_native.json"
CHILDREN = ("target", "createInput")


def _contract() -> dict[str, Any]:
    c, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-launch-projectile-action-native-contract.v1", status="exact-current-build", label=LABEL)
    if ({k: len(v["members"]) for k, v in c.get("records", {}).items()} != {"launchProjectile":37,"presetPoint":2}
            or c.get("actionDispatch")!={"222":"launchProjectile"}
            or c.get("childTypes")!={"target":"Beyond.Gameplay.Core.TargetSettings",
                "assignmentList":"System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>",
                "targetBytesList":"System.Collections.Generic.List`1<Beyond.Gameplay.Core.LaunchProjectile+PresetPointDef>"}
            or len([m for m in c["records"]["launchProjectile"]["members"] if m["kind"]=="raw12"])!=4):
        raise ValueError(f"{LABEL}.contract:shape")
    for key, record in c["records"].items():
        for member in record["members"]:
            if member["kind"] in c["childTypes"] and (
                    member["declaredType"] != c["childTypes"][member["kind"]]
                    or member.get("sourceContextInstructionRva") is None):
                raise ValueError(f"{LABEL}.contract:typed-child={key}.{member['fieldName']}")
    return c


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(c: dict) -> dict:
    return {k: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in r["members"]]
            for k, r in c["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    c = _contract(); source = c["records"][record]["sourceContract"] if record else CONTRACT_PATH.name
    e = CensusGateError(f"{LABEL}.{check}", source=(CONTRACTS_DIR / source).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    e.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=c["nativeInputs"])
    raise e


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    c = _contract(); expected = c["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in CHILDREN:
        child = children.get(name, {})
        if child.get("status") != "validated" or child.get("nativeInputs") != expected:
            _fail("shared-child", {"name": name, "nativeInputs": expected}, child)
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], "missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata); proved = {}
    for source_name in dict.fromkeys(r["sourceContract"] for r in c["records"].values()):
        path = CONTRACTS_DIR / source_name; source = json.loads(path.read_bytes())
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        proved.update(named.validate_named_records(image, source,
            {k: r for k, r in c["records"].items() if r["sourceContract"] == source_name}, label=LABEL, fail=_fail))
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in c["actionDispatch"].items():
        r = c["records"][key]; route = routes.get(int(tag))
        if (audit.get("status") != "validated" or route is None or route.status != "resolved"
                or route.wrapper_name != r["wrapperTypeName"]
                or list(route.member_order) != [m["fieldName"] for m in r["members"]]
                or list(route.member_declared_types) != [m["declaredType"] for m in r["members"]]):
            _fail("dispatcher-members", r["wrapperTypeName"], None if route is None else route.row(), record=key)
    after = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        return {"status": after.status, "detail": after.detail, "nativeInputs": expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll-after", expected["UnityPlayer.dll"], "mismatched")
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": c["actionDispatch"], "evidenceBoundary": c["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    c = _contract(); context = native_validation.get("children", {}); native = context.get("launchProjectile", {})
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native_validation.get("nativeInputs") != c["nativeInputs"] or native.get("nativeInputs") != c["nativeInputs"]
            or native.get("recordMembers") != _members(c) or native.get("actionDispatch") != c["actionDispatch"]
            or any(context.get(n, {}).get("status") != "validated" or context[n].get("nativeInputs") != c["nativeInputs"] for n in CHILDREN)
            or str(tag) not in c["actionDispatch"] or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    physical = bytes([tag]) if tag < 250 else b"\xfa" + struct.pack("<H", tag)
    if data[start:start + len(physical)] != physical:
        raise ValueError(f"{LABEL}.decode:physical-union-tag")
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), "launch-projectile-action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")

    def record(key: str) -> dict[str, Any]:
        at = reader.pos; plan = c["records"][key]; fields = []
        if reader.peek() == 255:
            reader.take(1, "null-" + key)
            return {"start": at, "end": reader.pos, "status": "exact-null-wrapper", "typeName": plan["runtimeTypeName"],
                    "namedFields": [], "recursiveStoredSchemaExact": True}
        reader.header(len(plan["members"]))
        for m in plan["members"]:
            begin = reader.pos; kind = m["kind"]; value = {}
            if kind in {"byte", "scalar32", "raw12"}:
                value["rawHex"] = reader.take({"byte":1,"scalar32":4,"raw12":12}[kind], m["fieldName"]).hex().upper()
            elif kind == "bytePayload":
                reader.byte_payload(); value.update(rawHex=data[begin:reader.pos].hex().upper(), payloadEncoding="unresolved")
            elif kind == "target":
                reader.target_profile(); span = {"start": begin, "end": reader.pos, "fieldName": m["fieldName"]}
                value["child"] = ({**span, "status": "exact-null-wrapper", "recursiveStoredSchemaExact": True}
                    if data[begin:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
            elif kind == "assignmentList":
                count=reader.count(1,nullable=True)
                for _ in range(max(0,count)):reader.assignment_profile()
                value["child"]=assignments.decode_assignment_list(data,source=source,logical_sha256=digest,
                    start=begin,end=reader.pos,native_validation=context["createInput"])
            elif kind == "targetBytesList":
                count=reader.count(1,nullable=True)
                elements=[record("presetPoint") for _ in range(max(0,count))]
                value["child"]={"start":begin,"end":reader.pos,"count":count,"elements":elements,
                    "recursiveStoredSchemaExact":True}
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if "child" in value and (value["child"].get("recursiveStoredSchemaExact") is not True
                    or [value["child"].get("start"), value["child"].get("end")] != [begin, reader.pos]):
                raise ValueError(f"{LABEL}.decode:child-span at={begin}")
            fields.append({"fieldName": m["fieldName"], "declaredType": m["declaredType"], "kind": kind,
                           "start": begin, "end": reader.pos, **value})
        return {"start": at, "end": reader.pos, "typeName": plan["runtimeTypeName"], "namedFields": fields,
                "recursiveStoredSchemaExact": True}

    parent = record(c["actionDispatch"][str(tag)])
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-launch-projectile-action-receipt.v1", "source": source, "logicalSha256": digest.upper(),
            "tag": tag, **parent, "start": start, "runtimeMeaningExact": False}
