"""Selected two-CheckTwoDirectionAngle Buff damage condition on original bytes.

It checks the selected native tag-130 twelve-member action, with four simple
TargetSettings and one BlackboardDouble per action, and the exact two-action
condition on current logical source bytes. For whole-root composition in
``memorypack.buff_corpus`` it pairs only with the ordered tag-five/tag-six
damage processors.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_two_direction_angle_condition_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.buff_frontiers_native import load_rows
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as target
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence


LABEL = "buffDamageTwoDirectionAngleCondition"
SCHEMA = "endfield.buff-damage-two-direction-angle-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-two-direction-angle-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_two_direction_angle_condition_native.json"

_COMPATIBLE = {
    "byte": ("bool", 1), "scalar32": ("scalar32", 4),
    "enum32": ("enum", 4), "target-settings": ("object", None),
    "blackboard-double": ("object", None),
}


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    dependencies = contract.get("reviewedDependencies") or []
    tags = contract.get("selectedActionTags") or []
    if (
        len(dependencies) != 4 or not all(isinstance(name, str) for name in dependencies)
        or type(contract.get("unionTag")) is not int
        or type(contract.get("actionMemberCount")) is not int
        or len(contract.get("selectedActionFieldNames") or []) != contract["actionMemberCount"]
        or len(contract.get("selectedActionReadKinds") or []) != contract["actionMemberCount"]
        or type(contract.get("sequenceMemberCount")) is not int
        or type(contract.get("sequenceTerminalByteCount")) is not int
        or tags != [contract["unionTag"]] * 2
        or contract.get("sourceReadOrderRef")
        != f"{dependencies[0]}.actions[unionTag={contract['unionTag']}].readOrder"
        or contract.get("selectedTargetShapeRef")
        != f"{dependencies[2]}.selectedTargetShape"
        or len(contract.get("selectedTargetMemberNames") or []) != 4
        or not isinstance(contract.get("selectedBlackboardMemberName"), str)
        or not isinstance(contract.get("selectedTerminalRawHex"), str)
        or len(bytes.fromhex(contract["selectedTerminalRawHex"]))
        != contract["sequenceTerminalByteCount"]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Compose the selected dispatcher, source order, sequence and child gates."""
    contract = _contract()
    expected = contract["nativeInputs"]
    frontier_contract, sequence_contract, target_contract, blackboard_contract = [
        json.loads((CONTRACTS_DIR / name).read_bytes())
        for name in contract["reviewedDependencies"]
    ]
    action_contract = next(
        (row for row in frontier_contract["actions"]
         if row.get("unionTag") == contract["unionTag"]), None,
    )
    if (
        frontier_contract.get("nativeInputs") != expected
        or any(row.get("nativeInputs") != expected for row in
               (sequence_contract, target_contract, blackboard_contract))
        or action_contract is None
        or action_contract.get("serializedMemberCount") != contract["actionMemberCount"]
        or sequence_contract.get("memberCount") != contract["sequenceMemberCount"]
        or sequence_contract.get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or blackboard_contract.get("selectedReadOrder")
        != ["blackboardKey", "useBlackboardKey", "value"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    frontier_rows, frontier_audit = load_rows("frontier9")
    routes, route_audit = load_action_routes()
    selected = {
        "target": target.validate_current_native_contract(),
        "blackboard": blackboard.validate_current_native_contract(),
        "sequence": sequence.validate_current_native_contract(),
    }
    if (
        frontier_audit.get("status") != "validated"
        or route_audit.get("status") != "validated"
        or contract["unionTag"] not in frontier_rows
        or contract["unionTag"] not in routes
        or any(row.get("status") != "validated" for row in selected.values())
    ):
        return {"status": "mismatched", "detail": "selected native dependency did not validate"}
    action = frontier_rows[contract["unionTag"]]
    route = routes[contract["unionTag"]]
    names = list(route.member_order)
    read_order = action["readOrder"]
    setter_names = [row[2].removeprefix("set___").removesuffix("__")
                    for row in action["setterMethods"][1:]]
    if (
        action != action_contract or route.status != "resolved"
        or route.wrapper_name != action["wrapperName"]
        or len(names) != contract["actionMemberCount"]
        or len(read_order) != len(names)
        or names != contract["selectedActionFieldNames"]
        or read_order != contract["selectedActionReadKinds"]
        or names[4:] != setter_names
        or set(setter_names) != set(action["generatedOwnFields"])
        or any(kind not in _COMPATIBLE for kind in read_order)
        or any(
            width != _COMPATIBLE[kind][1]
            or not (member_kind == _COMPATIBLE[kind][0]
                    or kind == "scalar32" and member_kind == "enum")
            for kind, member_kind, width in zip(
                read_order, route.member_kinds, route.member_widths, strict=True,
            )
        )
        or [name for name, kind in zip(names, read_order, strict=True)
            if kind == "target-settings"] != contract["selectedTargetMemberNames"]
        or [name for name, kind in zip(names, read_order, strict=True)
            if kind == "blackboard-double"]
            != [contract["selectedBlackboardMemberName"]]
        or any(route.member_declared_types[names.index(name)]
               != "Beyond.Gameplay.Core.TargetSettings"
               for name in contract["selectedTargetMemberNames"])
        or route.member_declared_types[names.index(
            contract["selectedBlackboardMemberName"])]
            != "Beyond.Blackboard+BlackboardDouble"
        or selected["target"].get("nativeInputs") != expected
        or selected["target"].get("selectedTargetShape")
            != target_contract["selectedTargetShape"]
        or selected["blackboard"].get("selectedReadOrder")
            != blackboard_contract["selectedReadOrder"]
        or selected["sequence"].get("serializedReadOrder")
            != sequence_contract["serializedReadOrder"]
    ):
        raise ValueError(f"{LABEL}.native:selected-route-drift")
    field_plan = [
        {"name": name, "kind": kind, "width": width,
         "declaredType": declared}
        for name, kind, width, declared in zip(
            names, read_order, route.member_widths,
            route.member_declared_types, strict=True,
        )
    ]
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"],
        "actionMemberCount": contract["actionMemberCount"],
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "selectedActionTags": contract["selectedActionTags"],
        "selectedTerminalRawHex": contract["selectedTerminalRawHex"],
        "selectedTargetMemberNames": contract["selectedTargetMemberNames"],
        "selectedBlackboardMemberName": contract["selectedBlackboardMemberName"],
        "wrapperType": action["wrapperName"],
        "wrappedType": action["actualTypeName"],
        "fieldPlan": field_plan,
        "targetNative": selected["target"],
        "blackboardNative": selected["blackboard"],
        "sequenceNative": selected["sequence"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_two_direction_angle_condition(
    data: bytes, *, source: str, start: int, end: int,
    logical_sha256: str, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse exactly two selected actions and their nested original bytes."""
    contract = _contract()
    native = native_validation
    if (
        native.get("status") != "validated"
        or native.get("nativeInputs") != contract["nativeInputs"]
        or native.get("unionTag") != contract["unionTag"]
        or native.get("actionMemberCount") != contract["actionMemberCount"]
        or native.get("sequenceMemberCount") != contract["sequenceMemberCount"]
        or native.get("sequenceTerminalByteCount")
            != contract["sequenceTerminalByteCount"]
        or native.get("selectedActionTags") != contract["selectedActionTags"]
        or native.get("selectedTerminalRawHex")
            != contract["selectedTerminalRawHex"]
        or native.get("selectedTargetMemberNames")
            != contract["selectedTargetMemberNames"]
        or native.get("selectedBlackboardMemberName")
            != contract["selectedBlackboardMemberName"]
        or [row.get("name") for row in native.get("fieldPlan") or []]
            != contract["selectedActionFieldNames"]
        or [row.get("kind") for row in native.get("fieldPlan") or []]
            != contract["selectedActionReadKinds"]
        or len(native.get("fieldPlan") or []) != contract["actionMemberCount"]
        or any(native.get(name, {}).get("status") != "validated"
               for name in ("targetNative", "blackboardNative", "sequenceNative"))
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes) or not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}.source:sha256")
    if not isinstance(source, str):
        raise ValueError(f"{LABEL}.source:path")
    virtual = PurePosixPath(source)
    if (
        virtual.is_absolute() or virtual.parts[:3] != ("Data", "Json", "BuffData")
        or len(virtual.parts) != 4 or ".." in virtual.parts
        or not source.endswith(".json")
    ):
        raise ValueError(f"{LABEL}.source:path")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.source:range")
    reader = Reader(data, source, end)
    reader.pos = start
    reader.header(native["sequenceMemberCount"])
    if reader.count(1, reserve=native["sequenceTerminalByteCount"]) != len(native["selectedActionTags"]):
        raise ValueError(f"{LABEL}.sequence:action-count")
    actions = []
    for selected_tag in native["selectedActionTags"]:
        action_start = reader.pos
        tag = reader.nested_union_tag((selected_tag,), "condition-action")
        if tag != selected_tag or reader.peek() == 0xFF:
            raise ValueError(f"{LABEL}.action:tag-or-null")
        reader.header(native["actionMemberCount"])
        fields = []
        for member in native["fieldPlan"]:
            field_start = reader.pos
            kind = member["kind"]
            if kind in ("byte", "scalar32", "enum32"):
                raw = reader.take(member["width"], member["name"])
                child = None
            elif kind == "target-settings":
                reader.target_profile()
                nested = Reader(data, source, reader.pos)
                nested.pos = field_start
                child = target._simple_target(nested, native["targetNative"])
                if (
                    child.get("status") != "exact-simple-target"
                    or child.get("recursiveNamedSchemaExact") is not True
                    or child.get("start") != field_start
                    or child.get("end") != reader.pos
                    or nested.pos != reader.pos
                ):
                    raise ValueError(f"{LABEL}.target:selected-shape")
            elif kind == "blackboard-double":
                reader.scalar_payload()
                child = blackboard.decode_adding_cooldown(
                    data, field_start, reader.pos,
                    native_validation=native["blackboardNative"],
                )
                if (
                    child.get("wholeValueExact") is not True
                    or child.get("startOffset") != field_start
                    or child.get("consumedEnd") != reader.pos
                ):
                    raise ValueError(f"{LABEL}.blackboard:selected-shape")
            else:
                raise ValueError(f"{LABEL}.action:unsupported-kind={kind}")
            field = {
                "name": member["name"], "declaredType": member["declaredType"],
                "kind": kind, "start": field_start, "end": reader.pos,
            }
            if child is not None:
                field["namedChild"] = child
            else:
                field["rawHex"] = raw.hex().upper()
            fields.append(field)
        if (
            fields[0]["start"] != action_start + 2
            or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
            or fields[-1]["end"] != reader.pos
        ):
            raise ValueError(f"{LABEL}.action:field-tiling")
        actions.append({
            "tag": tag, "start": action_start, "end": reader.pos,
            "wrapperType": native["wrapperType"],
            "wrappedType": native["wrappedType"],
            "memberCount": len(fields), "namedFields": fields,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        })
    terminal = reader.take(native["sequenceTerminalByteCount"], "sequence-terminals")
    if (
        terminal.hex().upper() != native["selectedTerminalRawHex"]
        or reader.pos != end
        or actions[0]["end"] != actions[1]["start"]
        or actions[-1]["end"] + len(terminal) != end
    ):
        raise ValueError(f"{LABEL}.sequence:terminal-or-end")
    return {
        "schema": SCHEMA, "status": "exact-two-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": len(actions),
        "actions": actions, "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False, "evidenceBoundary": native["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join selected source identities to exact two-angle condition children."""
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    expected_set = expected_input_set_sha256.upper()
    if (
        len(expected_set) != 64
        or any(char not in "0123456789ABCDEF" for char in expected_set)
        or report.get("inputSetSha256") != expected_set
        or report.get("status") != "complete"
        or report.get("publicationEligible") is not True
        or report.get("provenance", {}).get("buffPositiveDamageNativeValidation", {}).get("status")
            != "validated"
    ):
        raise ValueError(f"{LABEL}.report:current-provenance")
    native = validate_current_native_contract()
    modifier_native = modifier.validate_current_native_contract()
    if native.get("status") != "validated" or modifier_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    rows = []
    for source_row in report["files"]:
        if (
            source_row.get("rootPositiveDamageFrameCandidate") is not True
            or source_row.get("rootPositiveDamageCandidate") is True
        ):
            continue
        identity = source_row["identity"]
        source = identity["fileName"]
        virtual = PurePosixPath(source)
        if (
            identity.get("status") != "verified"
            or identity.get("inputSetSha256") != expected_set
            or virtual.parts[:3] != ("Data", "Json", "BuffData")
            or len(virtual.parts) != 4
        ):
            raise ValueError(f"{LABEL}.report:identity:{source}")
        accepted = [row for row in source_row["candidates"]
                    if row.get("readerAcceptedThroughEof") is True]
        if len(accepted) != 1:
            raise ValueError(f"{LABEL}.report:accepted-candidate:{source}")
        blocker = accepted[0]["namedSchemaReceipt"]["firstBlocker"]
        if (
            blocker.get("field") != "damageModifier"
            or blocker.get("category") != "positive-modifier-recursive-proof"
        ):
            raise ValueError(f"{LABEL}.report:damage-first-blocker:{source}")
        data = (export_root / virtual.name).read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != identity["length"] or digest != source_row["logicalSha256"]:
            raise ValueError(f"{LABEL}.source:logical-bytes:{source}")
        parent = modifier.decode_damage_modifier_collection(
            data, blocker["start"], blocker["end"], source=source,
            native_validation=modifier_native,
        )
        if parent.get("count") != 1 or len(parent.get("elements", [])) != 1:
            continue
        fields = parent["elements"][0]["fields"]
        condition, processors = fields[:2]
        if (
            condition.get("actionTags") != native["selectedActionTags"]
            or condition.get("actionUnionCount") != len(native["selectedActionTags"])
            or [item.get("tag") for item in processors.get("processors") or []] != [5, 6]
        ):
            continue
        decoded = decode_two_direction_angle_condition(
            data, source=source, start=condition["start"], end=condition["end"],
            logical_sha256=digest, native_validation=native,
        )
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionReceipt": decoded, "processorTags": [5, 6],
            "projectedRootWithSelectedProcessorPair": True,
        })
    return {
        "schema": "endfield.buff-damage-two-direction-angle-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "twoActionConditionExact": len(rows),
            "projectedRootWithSelectedProcessorPair": len(rows),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS identity and logical source bytes rejoin the selected "
            "two-action condition. Separate processor and whole-root gates must agree."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_current_positive_frames(
        args.buff_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
