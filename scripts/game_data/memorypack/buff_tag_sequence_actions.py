"""Named AddTag and ForEach parents with independently proved stored children.

Targets, tags and recursive sequences close on their original byte spans.
Stored values do not establish tag attachment, iteration order or execution.
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
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as strings
from scripts.game_data.memorypack import buff_aura_heal_actions as tags
from scripts.game_data.memorypack import buff_sequence as sequences

LABEL = "buffTagSequenceActions"
CONTRACT_PATH = CONTRACTS_DIR / "buff_tag_sequence_actions_native.json"
CHILDREN = ("target", "blackboardString", "auraHeal", "sequence")


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-tag-sequence-actions-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != {"addTag", "forEach"}
            or len(value.get("actionDispatch", {})) != 2
            or set(value["actionDispatch"].values()) != set(value["records"])
            or value.get("childTypes") != {
                "target": "Beyond.Gameplay.Core.TargetSettings",
                "paired-payload": strings.STRING_TYPE,
                "tag-elements": "System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>",
                "sequence": sequences.TYPE_NAME}):
        raise ValueError(f"{LABEL}.contract:shape")
    for key, record in value["records"].items():
        for member in record["members"]:
            kind = member["kind"]
            if kind in value["childTypes"] and (
                    member["declaredType"] != value["childTypes"][kind]
                    or member.get("sourceContextInstructionRva") is None):
                raise ValueError(f"{LABEL}.contract:typed-child={key}.{member['fieldName']}")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in row["members"]]
            for key, row in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    contract = _contract()
    source = contract["records"][record]["sourceContract"] if record else CONTRACT_PATH.name
    error = CensusGateError(f"{LABEL}.{check}", source=(CONTRACTS_DIR / source).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract["nativeInputs"])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
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
        proved.update(records_native.validate_named_records(image, source, {key: record}, label=LABEL, fail=_fail))
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract["actionDispatch"].items():
        record = contract["records"][key]; route = routes.get(int(tag))
        if (audit.get("status") != "validated" or route is None or route.status != "resolved"
                or route.wrapper_name != record["wrapperTypeName"]
                or list(route.member_order) != [m["fieldName"] for m in record["members"]]
                or list(route.member_declared_types) != [m["declaredType"] for m in record["members"]]):
            _fail("dispatcher-members", record["wrapperTypeName"], None if route is None else route.row(), record=key)
    after = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        return {"status": after.status, "detail": after.detail, "nativeInputs": expected}
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": contract["actionDispatch"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]], depth: int = 0) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get("children", {})
    native = context.get("tagSequenceActions", {})
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
    if depth > SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f"{LABEL}.decode:depth-limit")
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), "tag-sequence-action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    record = contract["records"][contract["actionDispatch"][str(tag)]]
    fields = []
    if reader.peek() == 255:
        reader.take(1, "null-action-wrapper")
    else:
        reader.header(len(record["members"]))
        for member in record["members"]:
            begin = reader.pos; value = {}; kind = member["kind"]
            if kind in ("byte", "scalar32"):
                value["rawHex"] = reader.take(1 if kind == "byte" else 4, member["fieldName"]).hex().upper()
            elif kind == "paired-payload":
                reader.paired_payload()
                proof = strings.decode_blackboard_string_value(data, source=source, logical_sha256=digest,
                    start=begin, end=reader.pos, native_validation=context["blackboardString"])
                if proof.get("wholeStoredSpanExact") is not True:
                    raise ValueError(f"{LABEL}.decode:string-span at={begin}")
                value["child"] = {**proof, "recursiveStoredSchemaExact": True}
            elif kind == "tag-elements":
                reader.tag_elements()
                value["child"] = tags.decode_tag_elements(data, source=source, digest=digest,
                    start=begin, end=reader.pos, native_validation=context["auraHeal"])
            elif kind == "sequence":
                reader.sequence(depth + 1)
                value["child"] = sequences.decode_value(data, source, digest, begin, reader.pos,
                    native_validation, depth + 1)
            elif kind == "target":
                reader.target_profile()
                span = {"start": begin, "end": reader.pos, "fieldName": member["fieldName"]}
                value["child"] = ({**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                    if data[begin:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if "child" in value and (value["child"].get("recursiveStoredSchemaExact") is not True
                    or [value["child"].get("start"), value["child"].get("end")] != [begin, reader.pos]):
                raise ValueError(f"{LABEL}.decode:child-span at={begin}")
            fields.append({"fieldName": member["fieldName"], "declaredType": member["declaredType"],
                           "kind": kind, "start": begin, "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-tag-sequence-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": tag, "typeName": record["runtimeTypeName"],
            "start": start, "end": end, "namedFields": fields,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
