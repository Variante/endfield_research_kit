"""Compose the proved CheckHp/CheckPoiseValue fields in shared event actions.

The selected-condition owner proves the parent read order and typed child
slots. This reader lifts the single-action restriction without changing that
proof: every reached TargetSettings and BlackboardDouble must independently
close on its original span. Runtime comparisons and provider selection remain
unresolved.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable

from scripts.game_data.memorypack import buff_damage_check_vitals_condition_receipt as parent
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack.buff_actions import Reader

LABEL = "buffVitalsActions"
CONTRACT_PATH = parent.CONTRACT_PATH


def supported_tags() -> frozenset[int]:
    return frozenset(row["unionTag"] for row in parent._contract()["routes"])


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    contract = parent._contract()
    context = native_validation.get("children", {})
    proof = context.get("vitals", {})
    expected_routes = [{k: row[k] for k in ("unionTag", "wrapperType", "wrappedType", "actionMemberPlan")}
                       for row in contract["routes"]]
    if (native_validation.get("status") != "validated" or proof.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or proof.get("nativeInputs") != contract["nativeInputs"]
            or proof.get("routes") != expected_routes
            or any(proof.get(k, {}).get("status") != "validated" for k in ("targetNative", "blackboardNative"))
            or any(context.get(k, {}).get("status") != "validated"
                   or context[k].get("nativeInputs") != contract["nativeInputs"] for k in ("target", "blackboard"))
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    selected = next((row for row in expected_routes if row["unionTag"] == tag), None)
    if selected is None:
        raise ValueError(f"{LABEL}.decode:unsupported-tag={tag}")
    reader = Reader(data, source, end)
    reader.pos = start
    if reader.nested_union_tag((tag,), "vitals-action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    plan = selected["actionMemberPlan"]
    reader.header(len(plan))
    fields = []
    for member in plan:
        begin = reader.pos
        kind = member["kind"]
        value = {}
        if kind in ("bool-byte", "enum32", "int32"):
            value["rawHex"] = reader.take(member["width"], member["name"]).hex().upper()
        elif kind == "target-settings":
            reader.target_profile()
            span = {"fieldName": member["name"], "start": begin, "end": reader.pos}
            child = ({**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                     if data[begin:reader.pos] == b"\xff"
                     else target_decoder(data, source, digest, span, context))
            if (child.get("recursiveStoredSchemaExact") is not True
                    or [child.get("start"), child.get("end")] != [begin, reader.pos]):
                raise ValueError(f"{LABEL}.decode:incomplete-child={member['name']} at={begin}")
            value["child"] = child
        elif kind == "blackboard-double":
            reader.scalar_payload()
            child = scalar.decode_adding_cooldown(data, begin, reader.pos,
                native_validation=proof["blackboardNative"])
            if (child.get("wholeValueExact") is not True or child.get("startOffset") != begin
                    or child.get("consumedEnd") != reader.pos):
                raise ValueError(f"{LABEL}.decode:incomplete-child={member['name']} at={begin}")
            value["child"] = {**child, "recursiveStoredSchemaExact": True}
        else:
            raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
        fields.append({"fieldName": member["name"], "declaredType": member["declaredType"],
                       "kind": kind, "start": begin, "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-vitals-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": tag, "start": start, "end": end,
            "typeName": selected["wrappedType"], "namedFields": fields,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
