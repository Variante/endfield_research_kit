"""Exact two-action damage condition child with selected 0x005B then 0x005E."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_damage_check_decorate_mask_condition_receipt as decorate_mask
from scripts.game_data.memorypack import buff_damage_check_type_mask_condition_receipt as type_mask
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier


LABEL = "buffDamageTwoActionCondition"
SCHEMA = "endfield.buff-damage-two-action-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-two-action-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_two_action_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    if (
        contract.get("reviewedDependencies") != [
            "buff_damage_sequence_action_condition_native.json",
            "buff_damage_check_decorate_mask_condition_native.json",
            "buff_damage_check_type_mask_condition_native.json",
        ]
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or contract.get("selectedActionTags") != [91, 94]
        or contract.get("selectedActionNames")
        != ["CheckDamageDecorateMask", "CheckDamageTypeMask"]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Compose the independently checked sequence and both action readers."""
    contract = _contract()
    expected = contract["nativeInputs"]
    dependencies = [json.loads((CONTRACTS_DIR / name).read_bytes())
                    for name in contract["reviewedDependencies"]]
    if (
        any(row.get("nativeInputs") != expected for row in dependencies)
        or dependencies[0].get("schema")
        != "endfield.buff-damage-sequence-action-condition-native-contract.v1"
        or dependencies[0].get("memberCount") != contract["sequenceMemberCount"]
        or dependencies[0].get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or [row.get("unionTag") for row in dependencies[1:]]
        != contract["selectedActionTags"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    selected = [
        sequence.validate_current_native_contract(),
        decorate_mask.validate_current_native_contract(),
        type_mask.validate_current_native_contract(),
    ]
    if any(row.get("status") != "validated" for row in selected):
        failed = next(row for row in selected if row.get("status") != "validated")
        return {"status": failed.get("status", "failed"), "detail": failed.get("detail"),
                "selected": selected}
    if (
        selected[0].get("serializedReadOrder")
        != ["actionData", "onlyExecuteWhenSourceIsGuard",
            "onlyExecuteWhenSourceIsMainChar"]
        or any(row.get("nativeInputs") != expected for row in selected[1:])
        or [row.get("unionTag") for row in selected[1:]]
        != contract["selectedActionTags"]
        or any(row.get("sequenceMemberCount") != contract["sequenceMemberCount"]
               or row.get("sequenceTerminalByteCount")
               != contract["sequenceTerminalByteCount"] for row in selected[1:])
        or [len(row.get("actionMemberPlan") or []) for row in selected[1:]] != [6, 5]
    ):
        raise ValueError(f"{LABEL}.native:selected-reader-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "selectedActionTags": contract["selectedActionTags"],
        "actionReaders": [
            {"unionTag": row["unionTag"], "wrapperType": row["wrapperType"],
             "wrappedType": row["wrappedType"], "actionMemberPlan": row["actionMemberPlan"]}
            for row in selected[1:]
        ],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_two_action_condition(
    data: bytes, *, source: str, start: int, end: int,
    logical_sha256: str, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay exactly two selected actions and both terminal bytes."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("sequenceMemberCount")
        != contract["sequenceMemberCount"]
        or native_validation.get("sequenceTerminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or native_validation.get("selectedActionTags")
        != contract["selectedActionTags"]
        or [row.get("unionTag") for row in native_validation.get("actionReaders", [])]
        != contract["selectedActionTags"]
        or [row.get("actionMemberPlan") for row in native_validation["actionReaders"]]
        != [decorate_mask._contract()["actionMemberPlan"],
            type_mask._contract()["actionMemberPlan"]]
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes)
        or not isinstance(logical_sha256, str)
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
    reader.header(native_validation["sequenceMemberCount"])
    count = reader.count(1, reserve=native_validation["sequenceTerminalByteCount"], nullable=True)
    if count != 2:
        raise ValueError(f"{LABEL}.sequence:action-count={count}")
    actions = []
    for route in native_validation["actionReaders"]:
        action_start = reader.pos
        tag = reader.nested_union_tag((route["unionTag"],), "condition-action")
        if tag != route["unionTag"] or reader.peek() == 0xFF:
            raise ValueError(f"{LABEL}.action:selected-nonnull-wrapper")
        tag_end = reader.pos
        reader.header(len(route["actionMemberPlan"]))
        fields = []
        for member in route["actionMemberPlan"]:
            field_start = reader.pos
            raw = reader.take(member["width"], member["name"])
            fields.append({
                "name": member["name"], "declaredType": member["declaredType"],
                "kind": member["kind"], "start": field_start, "end": reader.pos,
                "rawHex": raw.hex().upper(),
            })
        if fields[0]["start"] != tag_end + 1 or fields[-1]["end"] != reader.pos:
            raise ValueError(f"{LABEL}.action:field-tiling")
        actions.append({
            "tag": tag, "start": action_start, "end": reader.pos,
            "wrapperType": route["wrapperType"],
            "wrappedType": route["wrappedType"],
            "memberCount": len(fields), "namedFields": fields,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        })
    terminal = reader.take(native_validation["sequenceTerminalByteCount"],
                           "sequence-terminals")
    if (
        reader.pos != end or actions[0]["end"] != actions[1]["start"]
        or actions[1]["end"] + len(terminal) != end
    ):
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "exact-two-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": 2,
        "sequenceMemberCount": native_validation["sequenceMemberCount"],
        "actions": actions, "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join current VFS identity and logical bytes to selected two-action spans."""
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
        if (
            condition.get("name") != "condition"
            or condition.get("actionTags") != native["selectedActionTags"]
            or condition.get("actionUnionCount") != 2
        ):
            continue
        decoded = decode_two_action_condition(
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
    tags = Counter(tuple(row["processorTags"]) for row in rows)
    return {
        "schema": "endfield.buff-damage-two-action-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "twoActionConditionExact": len(rows),
            "processorTags": {",".join(map(str, key)): value for key, value in sorted(tags.items())},
            "projectedRootWithSelectedProcessor": sum(
                row["projectedRootWithSelectedProcessor"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS identity and logical source bytes rejoin selected two-action "
            "condition children. Root projection is a rank, not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_two_action_condition",
    "validate_current_native_contract",
]


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
