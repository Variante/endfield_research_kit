"""Exact selected CheckMainCharacterCondition simple-target damage condition.

It checks the selected native five-member action and simple
TargetSettings/DirectionSettings/SelectorData children, then replays one
``CheckMainCharacterCondition`` condition against current VFS logical hashes.
``memorypack.buff_corpus`` admits its sole tag-five processor through all 30
root fields, source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_check_main_character_condition_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as tag_match
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier


LABEL = "buffDamageCheckMainCharacterCondition"
SCHEMA = "endfield.buff-damage-check-main-character-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-check-main-character-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_check_main_character_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    plan = contract.get("actionMemberPlan")
    if (
        contract.get("reviewedDependencies") != [
            "levelscript_union_tags.json", "buff_68_native.json",
            "buff_damage_sequence_action_condition_native.json",
            "buff_damage_check_tag_match_condition_native.json",
        ]
        or contract.get("unionFamily") != "AbilityActionData"
        or contract.get("unionTag") != 104
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or not isinstance(plan, list) or len(plan) != 5
        or [row.get("kind") for row in plan]
        != ["bool-byte", "enum32", "int32", "int32", "target-settings"]
        or [row.get("width") for row in plan[:4]] != [1, 4, 4, 4]
        or [row.get("name") for row in plan]
        != ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
            "checkTarget"]
        or len(contract.get("sourceMethodIndices", [])) != 2
        or len(contract.get("sourceWindowStarts", [])) != 3
        or type(contract.get("sourceContextRva")) is not int
        or contract.get("simpleTargetShapeRef")
        != "buff_damage_check_tag_match_condition_native.json.selectedTargetShape"
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Check selected action reader and reuse the checked simple target shape."""
    contract = _contract()
    catalog = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes()
    )
    source = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][1]).read_bytes()
    )
    selected_sequence = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][2]).read_bytes()
    )
    selected_target = tag_match._contract()
    expected = contract["nativeInputs"]
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or source.get("schemaVersion") != 1
        or source.get("anonymousReadOrder", {}).get("member5")
        != ["byte", "scalar32", "scalar32", "scalar32", "target-profile"]
        or selected_sequence.get("schema")
        != "endfield.buff-damage-sequence-action-condition-native-contract.v1"
        or selected_sequence.get("nativeInputs") != expected
        or selected_sequence.get("memberCount") != contract["sequenceMemberCount"]
        or selected_sequence.get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or selected_target.get("nativeInputs") != expected
        or contract["actionMemberPlan"][:4]
        != selected_target["actionMemberPlan"][:4]
        or contract["actionMemberPlan"][4]
        != selected_target["actionMemberPlan"][4]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    reviewed = [row for row in catalog["families"][contract["unionFamily"]]
                if row.get("tag") == contract["unionTag"]]
    methods = [row for row in source["methods"]
               if row[0] in contract["sourceMethodIndices"]]
    windows = [row for row in source["codeWindows"]
               if row["startRva"] in contract["sourceWindowStarts"]]
    contexts = [row for row in source["nestedContexts"]
                if row["instructionRva"] == contract["sourceContextRva"]]
    if (
        len(reviewed) != 1
        or reviewed[0].get("wrapperName") != contract["wrapperType"]
        or reviewed[0].get("wrappedType") != contract["wrappedType"]
        or reviewed[0].get("memberCount") != len(contract["actionMemberPlan"])
        or [row[0] for row in methods] != contract["sourceMethodIndices"]
        or [row["startRva"] for row in windows] != contract["sourceWindowStarts"]
        or len(contexts) != 1
    ):
        raise ValueError(f"{LABEL}.contract:route-or-source")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "detail": gate.detail}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity)}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    routes, route_audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    route = routes.get(contract["unionTag"])
    plan = contract["actionMemberPlan"]
    compatible = {"bool-byte": ("bool", 1), "enum32": ("enum", 4),
                  "int32": ("scalar32", 4), "target-settings": ("object", None)}
    if (
        route_audit.get("status") != "validated"
        or {name: str(value).upper() for name, value in
            route_audit.get("nativeInputs", {}).items()} != {
                "GameAssembly.dll": expected["GameAssembly.dll"],
                "global-metadata.dat": expected["global-metadata.dat"],
            }
        or route is None or route.status != "resolved"
        or route.wrapper_name != contract["wrapperType"]
        or route.inherited_member_count != 4
        or list(route.member_order) != [row["name"] for row in plan]
        or list(route.member_declared_types) != [row["declaredType"] for row in plan]
        or list(zip(route.member_kinds, route.member_widths, strict=True))
        != [compatible[row["kind"]] for row in plan]
    ):
        raise ValueError(f"{LABEL}.native:dispatcher-or-wrapper-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    for row in methods:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(windows, label=LABEL)
    context = contexts[0]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(image.gameassembly), offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index")
    spec = list(struct.unpack(
        "<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12
        ),
    ))
    arguments = image.instantiations.resolve(spec[2]).arguments
    if (
        spec != context["methodSpec"] or len(arguments) != 1
        or arguments[0].raw_type_record_hex != context["argumentRawHex"]
        or image.type_name(context["typeDefinition"]) != context["typeName"]
        or context["typeName"] != plan[4]["declaredType"]
    ):
        raise ValueError(f"{LABEL}.native:target-context")
    target_native = tag_match.validate_current_native_contract()
    if (
        target_native.get("status") != "validated"
        or target_native.get("nativeInputs") != expected
        or target_native.get("selectedTargetShape")
        != selected_target["selectedTargetShape"]
        or target_native.get("nestedNative") != {
            "target": "validated", "direction": "validated",
            "selector": "validated", "query": "validated",
        }
    ):
        raise ValueError(f"{LABEL}.native:simple-target-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"], "wrapperType": contract["wrapperType"],
        "wrappedType": contract["wrappedType"],
        "actionMemberPlan": plan,
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "targetPlan": target_native["targetPlan"],
        "directionPlan": target_native["directionPlan"],
        "selectorPlan": target_native["selectorPlan"],
        "selectedTargetShape": target_native["selectedTargetShape"],
        "nestedNative": {"target": "validated", "direction": "validated",
                         "selector": "validated"},
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_check_main_character_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay one action and the selected simple target to its endpoint."""
    contract = _contract()
    selected_target = tag_match._contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("unionTag") != contract["unionTag"]
        or native_validation.get("actionMemberPlan") != contract["actionMemberPlan"]
        or native_validation.get("selectedTargetShape")
        != selected_target["selectedTargetShape"]
        or native_validation.get("nestedNative") != {
            "target": "validated", "direction": "validated", "selector": "validated"
        }
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
    if count != 1:
        raise ValueError(f"{LABEL}.sequence:action-count={count}")
    action_start = reader.pos
    tag = reader.nested_union_tag((native_validation["unionTag"],), "condition-action")
    if tag != native_validation["unionTag"] or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.action:selected-nonnull-wrapper")
    tag_end = reader.pos
    plan = native_validation["actionMemberPlan"]
    reader.header(len(plan))
    fields = []
    for member in plan[:4]:
        field_start = reader.pos
        raw = reader.take(member["width"], member["name"])
        fields.append({
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": member["kind"], "start": field_start, "end": reader.pos,
            "rawHex": raw.hex().upper(),
        })
    target_start = reader.pos
    target_child = tag_match._simple_target(reader, native_validation)
    fields.append({
        "name": plan[4]["name"], "declaredType": plan[4]["declaredType"],
        "kind": plan[4]["kind"], "start": target_start,
        "end": reader.pos, "namedChild": target_child,
    })
    action_end = reader.pos
    terminal = reader.take(native_validation["sequenceTerminalByteCount"],
                           "sequence-terminals")
    if (
        reader.pos != end or fields[0]["start"] != tag_end + 1
        or fields[-1]["end"] != action_end
        or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
        or target_child["end"] != fields[4]["end"]
    ):
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "exact-one-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": 1,
        "sequenceMemberCount": native_validation["sequenceMemberCount"],
        "action": {
            "tag": tag, "start": action_start, "end": action_end,
            "wrapperType": native_validation["wrapperType"],
            "wrappedType": native_validation["wrappedType"],
            "memberCount": len(fields), "namedFields": fields,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        },
        "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join current VFS identity to exact sole 0x0068 condition spans."""
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
            or condition.get("actionTags") != [native["unionTag"]]
            or condition.get("actionUnionCount") != 1
        ):
            continue
        decoded = decode_check_main_character_condition(
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
        "schema": "endfield.buff-damage-check-main-character-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "oneActionConditionExact": len(rows),
            "projectedRootWithSelectedProcessor": sum(
                row["projectedRootWithSelectedProcessor"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS-verified logical bytes rejoin a sole selected 0x0068 "
            "simple-target condition. Root projection is not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_check_main_character_condition",
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
