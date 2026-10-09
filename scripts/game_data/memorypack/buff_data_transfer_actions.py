"""Named stored skill, signal, target-Buff, stack and scalar data transfers.

Complete selected reader windows, ordered result-to-setter transfers and
closed field types prove the parent layouts. Original-span composition keeps
nullable lists, null elements and independently null targets and blackboards.
Stored keys remain bytes; evaluated blackboards, skill-setting lookup/output
writes, battle-signal dispatch and mission ownership are unresolved. A parent
action never establishes whole BuffData EOF.
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
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as strings
from scripts.game_data.memorypack import buff_find_settings_child_receipt as find

LABEL = "buffDataTransferActions"
CONTRACT_PATH = CONTRACTS_DIR / "buff_data_transfer_actions_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-data-transfer-actions-native-contract.v4",
        status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != {"signal", "skillSetting", "readData", "targetBuffBlackboard", "attributeValue", "saveStack", "simpleCalc", "readAiTrans"}
            or set(value.get("actionDispatch", {}).values()) != {"signal", "skillSetting", "targetBuffBlackboard", "attributeValue", "saveStack", "simpleCalc", "readAiTrans"}
            or len(value["actionDispatch"]) != 7):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in row["members"]]
            for key, row in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    contract = _contract(); spec = contract["records"].get(record, {})
    error = CensusGateError(f"{LABEL}.{check}",
        source=(CONTRACTS_DIR / spec["sourceContract"]).as_posix() if spec else CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update({"validator": LABEL, "record": record, "field": field,
        "nativeInputs": contract["nativeInputs"]})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in ("target", "effectVectors", "blackboardString", "findSettings"):
        child = children.get(name, {})
        if child.get("status") != "validated" or child.get("nativeInputs") != expected:
            _fail("shared-child", expected, {"name": name, "status": child.get("status"),
                                           "nativeInputs": child.get("nativeInputs")})
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata); proved = {}
    sources = sorted({r["sourceContract"] for r in contract["records"].values()})
    for name in sources + ["buff_b4_native.json"]:
        path = CONTRACTS_DIR / name; source = json.loads(path.read_bytes())
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        selected = {k: r for k, r in contract["records"].items() if r["sourceContract"] == name}
        if selected:
            proved.update(records_native.validate_named_records(image, source, selected, label=LABEL, fail=_fail))
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract["actionDispatch"].items():
        route = routes.get(int(tag)); record = contract["records"][key]
        if (audit.get("status") != "validated" or route is None or route.status != "resolved"
                or route.wrapper_name != record["wrapperTypeName"]
                or list(route.member_order) != [m["fieldName"] for m in record["members"]]
                or list(route.member_declared_types) != [m["declaredType"] for m in record["members"]]):
            _fail("dispatcher-members", record["wrapperTypeName"], None if route is None else route.row(), record=key)
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": contract["actionDispatch"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get("children", {}); native = context.get("dataTransfer", {})
    key = contract["actionDispatch"].get(str(tag))
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native.get("nativeInputs") != contract["nativeInputs"] or native.get("recordMembers") != _members(contract)
            or native.get("actionDispatch") != contract["actionDispatch"] or key is None
            or any(context.get(k, {}).get("status") != "validated"
                   or context[k].get("nativeInputs") != contract["nativeInputs"]
                   for k in ("target", "effectVectors", "blackboardString", "findSettings"))
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start
    args = {"source": source, "logical_sha256": digest}

    def record(record_key: str) -> dict[str, Any]:
        begin = reader.pos; members = contract["records"][record_key]["members"]
        if reader.peek() == 255:
            reader.take(1, "null-" + record_key)
            return {"start": begin, "end": reader.pos, "status": "exact-null", "namedFields": [],
                    "recursiveStoredSchemaExact": True}
        reader.header(len(members)); fields = []
        for member in members:
            a = reader.pos; kind = member["kind"]; value = {}
            if kind in ("byte", "scalar32"):
                value["rawHex"] = reader.take(1 if kind == "byte" else 4, member["fieldName"]).hex().upper()
            elif kind in ("scalarPayload", "scalar-payload"):
                reader.scalar_payload()
                child = scalar.decode_adding_cooldown(data, a, reader.pos,
                    native_validation=context["effectVectors"]["scalarNative"])
                if child.get("wholeValueExact") is not True or [child.get("startOffset"), child.get("consumedEnd")] != [a, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:scalar-span at={a}")
                value["child"] = child
            elif kind == "pairedPayload":
                reader.paired_payload()
                child = strings.decode_blackboard_string_value(data, **args, start=a, end=reader.pos,
                    native_validation=context["blackboardString"])
                if child.get("wholeStoredSpanExact") is not True or [child.get("start"), child.get("end")] != [a, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:string-span at={a}")
                value["child"] = child
            elif kind in ("byte-payload", "bytePayload"):
                reader.byte_payload()
                value.update(rawHex=data[a:reader.pos].hex().upper(), payloadEncoding="unresolved")
            elif kind in ("target-profile", "target"):
                reader.target_profile(); span = {"start": a, "end": reader.pos, "fieldName": member["fieldName"]}
                child = ({**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                    if data[a:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
                if child.get("recursiveStoredSchemaExact") is not True or [child.get("start"), child.get("end")] != [a, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:target-span at={a}")
                value["child"] = child
            elif kind in ("finder", "finder-profile"):
                reader.finder_profile()
                child = find.decode_find_settings_child_receipt(data, **args, start=a, end=reader.pos,
                    native_validation=context["findSettings"])
                if child.get("wholeChildSpanExact") is not True or [child.get("start"), child.get("end")] != [a, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:finder-span at={a}")
                value["child"] = child
            elif kind == "counted-member4-profiles":
                count = reader.count(1, nullable=True)
                value.update(count=count, elements=[record("readData") for _ in range(max(0, count))])
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            fields.append({"fieldName": member["fieldName"], "kind": kind, "declaredType": member["declaredType"],
                           "start": a, "end": reader.pos, **value})
        return {"start": begin, "end": reader.pos, "namedFields": fields, "recursiveStoredSchemaExact": True}

    if reader.nested_union_tag((tag,), "data-transfer-action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    parent = record(key)
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-data-transfer-action-receipt.v1", "source": source, "logicalSha256": digest.upper(),
            "tag": tag, "start": start, "end": end, "parent": parent,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
