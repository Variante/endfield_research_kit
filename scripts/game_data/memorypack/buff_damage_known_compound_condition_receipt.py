"""Selected compound damage conditions made from independently proved actions.

It composes the selected native readers for the ordered
StackNumAdvanced/DamageType and DecorateMask/StackNumAdvanced/TagMatch
conditions on current source bytes. ``memorypack.buff_corpus`` admits both
with processor tag five through 30 root fields, source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_known_compound_condition_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_check_buff_stack_condition_receipt as stack
from scripts.game_data.memorypack import buff_damage_check_decorate_mask_condition_receipt as decorate
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as tag_match
from scripts.game_data.memorypack import buff_damage_check_type_condition_receipt as damage_type
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence


LABEL = "buffDamageKnownCompoundCondition"
SCHEMA = "endfield.buff-damage-known-compound-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-known-compound-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_known_compound_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    if (
        contract.get("reviewedDependencies") != [
            "buff_damage_sequence_action_condition_native.json",
            "buff_damage_check_decorate_mask_condition_native.json",
            "buff_damage_check_buff_stack_condition_native.json",
            "buff_damage_check_type_condition_native.json",
            "buff_damage_check_tag_match_condition_native.json",
        ]
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or contract.get("selectedActionPatterns") != [[60, 93], [91, 60, 124]]
        or contract.get("selectedActionNames") != {
            "60": "CheckBuffStackNumAdvanced", "91": "CheckDamageDecorateMask",
            "93": "CheckDamageType", "124": "CheckTagMatch",
        }
        or contract.get("stackFinderShape") != {
            "buffIdListCount": 1, "tagCount": 0,
            "queryStatus": "named-direct-members-exact-span",
        }
        or contract.get("tagMatchQueryTagCount") != 1
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Compose five separately selected native validators without widening them."""
    contract = _contract()
    dependencies = [json.loads((CONTRACTS_DIR / name).read_bytes())
                    for name in contract["reviewedDependencies"]]
    expected = contract["nativeInputs"]
    if (
        any(row.get("nativeInputs") != expected for row in dependencies)
        or dependencies[0].get("memberCount") != contract["sequenceMemberCount"]
        or dependencies[0].get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or [dependencies[index].get("unionTag") for index in (2, 1, 3, 4)]
        != [60, 91, 93, 124]
        or [row.get("unionTag") for row in dependencies[1:]] != [91, 60, 93, 124]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    selected = {
        "sequence": sequence.validate_current_native_contract(),
        "60": stack.validate_current_native_contract(),
        "91": decorate.validate_current_native_contract(),
        "93": damage_type.validate_current_native_contract(),
        "124": tag_match.validate_current_native_contract(),
    }
    if any(row.get("status") != "validated" for row in selected.values()):
        failed = next(row for row in selected.values()
                      if row.get("status") != "validated")
        return {"status": failed.get("status", "failed"), "detail": failed.get("detail")}
    if (
        selected["sequence"].get("serializedReadOrder") != [
            "actionData", "onlyExecuteWhenSourceIsGuard",
            "onlyExecuteWhenSourceIsMainChar",
        ]
        or any(selected[str(tag)].get("nativeInputs") != expected
               for tag in (60, 91, 93, 124))
        or any(selected[str(tag)].get("unionTag") != tag
               for tag in (60, 91, 93, 124))
        or [selected[str(tag)].get("actionMemberPlan")
            for tag in (91, 60, 93, 124)]
        != [row["actionMemberPlan"] for row in dependencies[1:]]
        or selected["60"].get("finderNative", {}).get("status") != "validated"
        or selected["60"].get("targetNative", {}).get("status") != "validated"
        or selected["60"].get("blackboardNative", {}).get("status") != "validated"
        or selected["124"].get("nestedNative") != {
            "target": "validated", "direction": "validated",
            "selector": "validated", "query": "validated",
        }
    ):
        raise ValueError(f"{LABEL}.native:selected-child-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "selectedActionPatterns": contract["selectedActionPatterns"],
        "selectedActions": {str(tag): selected[str(tag)] for tag in (60, 91, 93, 124)},
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "stackFinderShape": contract["stackFinderShape"],
        "tagMatchQueryTagCount": contract["tagMatchQueryTagCount"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _decode_action(reader: Reader, tag: int, *, source: str, digest: str,
                   native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    if reader.nested_union_tag((tag,), "condition-action") != tag or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.action:selected-nonnull-wrapper")
    selected = native["selectedActions"][str(tag)]
    plan = selected["actionMemberPlan"]
    reader.header(len(plan))
    fields = []
    for member in plan:
        field_start = reader.pos
        kind = member["kind"]
        width = member.get("width")
        if width is not None:
            detail = {"rawHex": reader.take(width, member["name"]).hex().upper()}
        elif kind == "buff-find-settings" and tag == 60:
            child = stack._find_settings(
                reader, source=source, logical_sha256=digest,
                native=selected["finderNative"],
            )
            shape = native["stackFinderShape"]
            if (
                child.get("buffIdListCount") != shape["buffIdListCount"]
                or child.get("tagCount") != shape["tagCount"]
                or child.get("namedFields", [None, None, None])[2].get("queryStatus")
                != shape["queryStatus"]
            ):
                raise ValueError(f"{LABEL}.finder:unsupported-shape")
            detail = {"namedChild": child}
        elif kind == "target-settings" and tag in (60, 124):
            target_native = (selected["targetNative"] if tag == 60 else selected)
            child = tag_match._simple_target(reader, target_native)
            if child.get("recursiveNamedSchemaExact") is not True:
                raise ValueError(f"{LABEL}.target:child")
            detail = {"namedChild": child}
        elif kind == "blackboard-double" and tag == 60:
            reader.scalar_payload()
            child = blackboard.decode_adding_cooldown(
                reader.data, field_start, reader.pos,
                native_validation=selected["blackboardNative"],
            )
            if child.get("wholeValueExact") is not True:
                raise ValueError(f"{LABEL}.blackboard:child")
            detail = {"namedChild": child}
        elif kind == "gameplay-tag-query" and tag == 124:
            child = tag_match._positive_query(reader, selected)
            if (
                child.get("recursiveNamedSchemaExact") is not True
                or child.get("namedFields", [None, None])[1].get("count")
                != native["tagMatchQueryTagCount"]
            ):
                raise ValueError(f"{LABEL}.query:unsupported-shape")
            detail = {"namedChild": child}
        else:
            raise ValueError(f"{LABEL}.action:unsupported-member:{member['name']}")
        fields.append({
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": kind, "start": field_start, "end": reader.pos, **detail,
        })
    if (
        fields[0]["start"] != start + 2
        or any(a["end"] != b["start"] for a, b in zip(fields, fields[1:]))
        or fields[-1]["end"] != reader.pos
    ):
        raise ValueError(f"{LABEL}.action:field-tiling")
    return {
        "tag": tag, "start": start, "end": reader.pos,
        "memberCount": len(plan), "namedFields": fields,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
    }


def decode_known_compound_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay one selected two or three-action condition to its exact end."""
    contract = _contract()
    native = native_validation
    dependencies = [stack._contract(), decorate._contract(),
                    damage_type._contract(), tag_match._contract()]
    if (
        native.get("status") != "validated"
        or native.get("nativeInputs") != contract["nativeInputs"]
        or native.get("selectedActionPatterns") != contract["selectedActionPatterns"]
        or native.get("sequenceMemberCount") != contract["sequenceMemberCount"]
        or native.get("sequenceTerminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or native.get("stackFinderShape") != contract["stackFinderShape"]
        or native.get("tagMatchQueryTagCount") != contract["tagMatchQueryTagCount"]
        or not isinstance(native.get("selectedActions"), dict)
        or any(native["selectedActions"].get(str(tag), {}).get("status") != "validated"
               or native["selectedActions"][str(tag)].get("nativeInputs")
               != contract["nativeInputs"]
               or native["selectedActions"][str(tag)].get("actionMemberPlan")
               != selected_contract["actionMemberPlan"]
               for tag, selected_contract in zip((60, 91, 93, 124), dependencies,
                                                  strict=True))
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
    count = reader.count(1, reserve=native["sequenceTerminalByteCount"], nullable=True)
    patterns = native["selectedActionPatterns"]
    selected = next((tags for tags in patterns if len(tags) == count), None)
    if selected is None:
        raise ValueError(f"{LABEL}.sequence:unsupported-action-count={count}")
    actions = [_decode_action(reader, tag, source=source,
                              digest=logical_sha256.upper(), native=native)
               for tag in selected]
    terminal = reader.take(native["sequenceTerminalByteCount"], "sequence-terminal")
    if (
        reader.pos != end or actions[0]["start"] != start + 5
        or any(a["end"] != b["start"] for a, b in zip(actions, actions[1:]))
        or actions[-1]["end"] + len(terminal) != end
    ):
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "exact-selected-compound-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": count,
        "actions": actions, "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join the selected current VFS identities to original-byte conditions."""
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    expected_set = expected_input_set_sha256.upper()
    if (
        len(expected_set) != 64
        or any(ch not in "0123456789ABCDEF" for ch in expected_set)
        or report.get("inputSetSha256") != expected_set
        or report.get("status") != "complete"
        or report.get("publicationEligible") is not True
        or report.get("provenance", {}).get("buffPositiveDamageNativeValidation", {}).get("status")
        != "validated"
    ):
        raise ValueError(f"{LABEL}.report:current-provenance")
    native = validate_current_native_contract()
    if native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:{native.get('status')}")
    modifier_native = modifier.validate_current_native_contract()
    if modifier_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.modifier-native:{modifier_native.get('status')}")
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
        accepted = [candidate for candidate in source_row["candidates"]
                    if candidate.get("readerAcceptedThroughEof") is True]
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
        condition = fields[0]
        if condition.get("actionTags") not in native["selectedActionPatterns"]:
            continue
        decoded = decode_known_compound_condition(
            data, source=source, logical_sha256=digest,
            start=condition["start"], end=condition["end"],
            native_validation=native,
        )
        processor_tags = [item["tag"] for item in fields[1]["processors"]]
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionReceipt": decoded, "processorTags": processor_tags,
            "projectedRootWithSelectedProcessor": processor_tags == [5],
        })
    return {
        "schema": "endfield.buff-damage-known-compound-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "selectedConditionExact": len(rows),
            "projectedRootWithSelectedProcessor": sum(
                row["projectedRootWithSelectedProcessor"] for row in rows),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS identity and logical source bytes rejoin selected compound "
            "conditions. Root projection is a rank, not a whole-BuffData receipt."
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
