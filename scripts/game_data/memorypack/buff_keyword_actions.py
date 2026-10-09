"""Named keyword/infliction storage and independently owned edit-list elements.

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
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as strings

LABEL = "buffKeywordActions"
CONTRACT_PATH = CONTRACTS_DIR / "buff_keyword_actions_native.json"
CHILDREN = ("target", "effectVectors", "blackboardString")


def _contract() -> dict[str, Any]:
    c, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-keyword-actions-native-contract.v3", status="exact-current-build", label=LABEL)
    if ({k: len(v["members"]) for k, v in c.get("records", {}).items()} !=
            {"vulnerable": 14, "spellInflictionOnChar": 13, "keywordEnhanceEdit": 3, "shelter": 13, "slow": 13, "speedup": 13, "weak": 13, "enhanced": 14, "spellInfliction": 8}
            or set(c.get("actionDispatch", {}).values()) != {"vulnerable", "spellInflictionOnChar", "shelter", "slow", "speedup", "weak", "enhanced", "spellInfliction"}
            or len(c["actionDispatch"]) != 8
            or c.get("childTypes") != {
                "target-profile": "Beyond.Gameplay.Core.TargetSettings",
                "paired-payload": strings.STRING_TYPE,
                "scalar-payload": "Beyond.Blackboard+BlackboardDouble",
                "nullable-keyword-edit-list": "System.Collections.Generic.List`1<Beyond.Gameplay.Core.KeywordEnhanceEdit>",
                "nullable-byte-payload-list": "System.Collections.Generic.List`1<string>",
                "target": "Beyond.Gameplay.Core.TargetSettings",
                "keyword-edit-list": "System.Collections.Generic.List`1<Beyond.Gameplay.Core.KeywordEnhanceEdit>"}):
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



def _required_suffix(members: list[dict[str, Any]], member_index: int) -> int:
    """Minimum required bytes for already proved subsequent storage fields."""
    minimum = {"byte": 1, "scalar32": 4, "byte-payload": 4,
        "target-profile": 1, "target": 1, "paired-payload": 1, "scalar-payload": 1,
        "nullable-keyword-edit-list": 4, "keyword-edit-list": 4, "nullable-byte-payload-list": 4}
    return sum(minimum[member["kind"]] for member in members[member_index + 1:])


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    c = _contract(); context = native_validation.get("children", {}); native = context.get("keywordActions", {})
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
    if reader.nested_union_tag((tag,), "keyword-action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")

    def record(key: str) -> dict[str, Any]:
        at = reader.pos; plan = c["records"][key]; fields = []
        if reader.peek() == 255:
            reader.take(1, "null-" + key)
            return {"start": at, "end": reader.pos, "status": "exact-null-wrapper", "typeName": plan["runtimeTypeName"],
                    "namedFields": [], "recursiveStoredSchemaExact": True}
        reader.header(len(plan["members"]))
        for member_index, m in enumerate(plan["members"]):
            begin = reader.pos; kind = m["kind"]; value = {}
            if kind in {"byte", "scalar32"}:
                value["rawHex"] = reader.take(1 if kind == "byte" else 4, m["fieldName"]).hex().upper()
            elif kind == "byte-payload":
                reader.byte_payload(); value.update(rawHex=data[begin:reader.pos].hex().upper(), payloadEncoding="unresolved")
            elif kind == "scalar-payload":
                reader.scalar_payload(); proof = scalar.decode_adding_cooldown(data, begin, reader.pos,
                    native_validation=context["effectVectors"]["scalarNative"])
                if proof.get("wholeValueExact") is not True or [proof.get("startOffset"), proof.get("consumedEnd")] != [begin, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:scalar-span at={begin}")
                value["child"] = {**proof, "start": begin, "end": reader.pos, "recursiveStoredSchemaExact": True}
            elif kind == "paired-payload":
                reader.paired_payload(); proof = strings.decode_blackboard_string_value(data, source=source,
                    logical_sha256=digest, start=begin, end=reader.pos, native_validation=context["blackboardString"])
                if proof.get("wholeStoredSpanExact") is not True:
                    raise ValueError(f"{LABEL}.decode:string-span at={begin}")
                value["child"] = {**proof, "recursiveStoredSchemaExact": True}
            elif kind in {"target-profile", "target"}:
                reader.target_profile(); span = {"start": begin, "end": reader.pos, "fieldName": m["fieldName"]}
                value["child"] = ({**span, "status": "exact-null-wrapper", "recursiveStoredSchemaExact": True}
                    if data[begin:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
            elif kind in {"nullable-keyword-edit-list", "keyword-edit-list"}:
                count = reader.count(1, reserve=_required_suffix(plan["members"], member_index), nullable=True)
                elements = [record("keywordEnhanceEdit") for _ in range(max(0, count))]
                value["child"] = {"start": begin, "end": reader.pos, "count": count, "elements": elements,
                                  "recursiveStoredSchemaExact": True}
            elif kind == "nullable-byte-payload-list":
                count = reader.count(4, reserve=_required_suffix(plan["members"], member_index), nullable=True); elements = []
                for _ in range(max(0, count)):
                    element_start = reader.pos; reader.byte_payload()
                    elements.append({"start": element_start, "end": reader.pos,
                        "rawHex": data[element_start:reader.pos].hex().upper(), "payloadEncoding": "unresolved"})
                value["child"] = {"start": begin, "end": reader.pos, "count": count, "elements": elements,
                                  "recursiveStoredSchemaExact": True}
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
    return {"schema": "endfield.buff-keyword-action-receipt.v1", "source": source, "logicalSha256": digest.upper(),
            "tag": tag, **parent, "start": start, "runtimeMeaningExact": False}
