"""Selected sword damage condition: exact stored-byte tiling, partial schema.

Every top-level action is independently source-bound and native-gated before
its span can advance the six-action sequence cursor. This proves the selected
condition's storage endpoint, while nested scalar/target/blackboard interiors
and the enclosing BuffData root remain partial.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_sword_condition_prefix as prefix
from scripts.game_data.memorypack import buff_damage_check_entity_num_child as entity
from scripts.game_data.memorypack import buff_damage_sword_if_else_child as if_else
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify


LABEL = "buffDamageSwordConditionStorage"
SCHEMA = "endfield.buff-damage-sword-condition-storage-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-sword-condition-storage-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_sword_condition_storage_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    source = contract.get("selectedSource", {})
    spans = source.get("actionSpans", [])
    dependencies = contract.get("reviewedDependencies")
    path = source.get("path")
    if (
        not isinstance(dependencies, list) or len(dependencies) != 4
        or any(not isinstance(name, str) or PurePosixPath(name).name != name
               or not name.endswith(".json") for name in dependencies)
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4 or not path.endswith(".json")
        or not isinstance(source.get("sha256"), str)
        or len(source["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in source["sha256"])
        or type(source.get("conditionStart")) is not int
        or type(source.get("conditionEnd")) is not int
        or type(source.get("sequenceMemberCount")) is not int
        or type(source.get("actionCount")) is not int
        or type(source.get("terminalByteCount")) is not int
        or source["sequenceMemberCount"] != 3
        or source["terminalByteCount"] != 2
        or not isinstance(spans, list) or len(spans) != source["actionCount"]
        or len(spans) != 6
        or any(type(row.get(key)) is not int for row in spans
               for key in ("tag", "start", "end"))
        or spans[0]["start"] != source["conditionStart"] + 5
        or spans[-1]["end"] + source["terminalByteCount"] != source["conditionEnd"]
        or any(left["end"] != right["start"]
               for left, right in zip(spans, spans[1:]))
        or any(not 0 <= row["tag"] <= 255 or row["start"] >= row["end"]
               for row in spans)
        or spans[-1]["tag"] != spans[-2]["tag"]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(audit_report_path: Path) -> dict[str, Any]:
    """Compose only native gates for the selected six child actions."""
    contract = _contract()
    expected = contract["nativeInputs"]
    selected = contract["selectedSource"]
    dependencies = [json.loads((CONTRACTS_DIR / name).read_bytes())
                    for name in contract["reviewedDependencies"]]
    if (
        any(row.get("nativeInputs") != expected for row in dependencies)
        or any(row.get("selectedSource", {}).get("path") != selected["path"]
               or row.get("selectedSource", {}).get("sha256") != selected["sha256"]
               for row in dependencies[:3])
        or dependencies[0]["selectedSource"]["selectedActions"] != selected["actionSpans"][:2]
        or {key: dependencies[1]["selectedSource"]["action"].get(key)
            for key in ("tag", "start", "end")} != selected["actionSpans"][2]
        or dependencies[2]["selectedSource"]["parentAction"] != selected["actionSpans"][3]
        or dependencies[3].get("memberCount") != selected["sequenceMemberCount"]
        or dependencies[3].get("terminalByteCount") != selected["terminalByteCount"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    selected_prefix = prefix.validate_current_native_contract(audit_report_path)
    if selected_prefix.get("status") != "validated":
        return {"status": selected_prefix.get("status", "failed"),
                "detail": selected_prefix.get("detail", "prefix native gate failed")}
    selected_entity = entity.validate_current_native_contract(audit_report_path)
    if selected_entity.get("status") != "validated":
        return {"status": selected_entity.get("status", "failed"),
                "detail": selected_entity.get("detail", "entity native gate failed")}
    selected_if_else = if_else.validate_current_native_contract()
    nested = selected_if_else.get("children")
    if (
        any(row.get("nativeInputs") != expected for row in
            (selected_prefix, selected_entity, selected_if_else))
        or selected_prefix.get("mask", {}).get("sequenceNative", {}).get("status")
        != "validated"
        or not isinstance(nested, list) or len(nested) != 2
        or nested[1].get("status") != "validated"
        or nested[1].get("unionTag")
        != selected["actionSpans"][4]["tag"]
    ):
        raise ValueError(f"{LABEL}.native:dependency-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "prefix": selected_prefix, "entity": selected_entity,
        "ifElse": selected_if_else,
        "source": selected, "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_selected_condition(data: bytes, *, source: str,
                              native_validation: dict[str, Any]) -> dict[str, Any]:
    """Replay all six selected actions and both terminal bytes to the end."""
    contract = _contract()
    selected = contract["selectedSource"]
    spans = selected["actionSpans"]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("source") != selected
        or any(native_validation.get(key, {}).get("status") != "validated"
               for key in ("prefix", "entity", "ifElse"))
        or not isinstance(native_validation.get("ifElse", {}).get("children"), list)
        or len(native_validation["ifElse"]["children"]) != 2
        or native_validation["ifElse"]["children"][1].get("status") != "validated"
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes) or source != selected["path"]
        or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]
        or len(data) < selected["conditionEnd"]
    ):
        raise ValueError(f"{LABEL}.source:path-or-sha256")
    first = prefix.decode_selected_prefix(
        data, source=source, native_validation=native_validation["prefix"],
    )
    third = entity.decode_selected_child(
        data, source=source, native_validation=native_validation["entity"],
    )
    fourth = if_else.decode_selected_child(
        data, source=source, native_validation=native_validation["ifElse"],
    )
    modify_native = native_validation["ifElse"]["children"][1]
    last = [modify.decode_modify_dynamic_blackboard_action_receipt(
        data, source=source, logical_sha256=selected["sha256"],
        start=row["start"], end=row["end"], native_validation=modify_native,
    ) for row in spans[4:]]
    actions = first["actions"] + [third, fourth] + last
    if (
        first.get("status") != "exact-selected-condition-prefix"
        or first.get("prefixEnd") != spans[1]["end"]
        or any((row.get("tag"), row.get("start"), row.get("end"))
               != (span["tag"], span["start"], span["end"])
               for row, span in zip(actions, spans, strict=True))
        or any(row.get("wholeStoredSpanExact") is not True
               and row.get("wholeActionByteSpanExact") is not True
               and row.get("wholeActionExact") is not True for row in actions)
    ):
        raise ValueError(f"{LABEL}.actions:receipt-drift")
    reader = Reader(data, source, selected["conditionEnd"])
    reader.pos = selected["conditionStart"]
    reader.header(selected["sequenceMemberCount"])
    count = reader.count(1, reserve=selected["terminalByteCount"], nullable=True)
    if count != selected["actionCount"]:
        raise ValueError(f"{LABEL}.sequence:action-count={count}")
    for span in spans:
        if reader.pos != span["start"] or data[reader.pos] != span["tag"]:
            raise ValueError(f"{LABEL}.sequence:action-gap-or-tag={reader.pos}")
        reader.pos = span["end"]
    terminals = reader.take(selected["terminalByteCount"], "sequence-terminal-booleans")
    if reader.pos != selected["conditionEnd"] or any(value not in (0, 1) for value in terminals):
        raise ValueError(f"{LABEL}.sequence:terminal-or-end")
    return {
        "schema": SCHEMA, "status": "exact-stored-condition-partial-schema",
        "source": source, "logicalSha256": selected["sha256"],
        "start": selected["conditionStart"], "end": selected["conditionEnd"],
        "sequenceMemberCount": selected["sequenceMemberCount"],
        "actionCount": count, "actions": actions,
        "terminalRawHex": terminals.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": False,
        "wholeConditionExact": False, "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }
