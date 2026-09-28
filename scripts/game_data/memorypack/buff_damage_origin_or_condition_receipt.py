"""Selected OriginSkillType and OrConditionAction damage-condition receipts.

This reader names two finite compound conditions. It does not promote their
enclosing BuffData roots; the root reader performs that independent proof.

It checks the selected native ``CheckOriginSkillType`` and
``OrConditionAction`` routes on two exact compound damage-condition source
spans, including the nested PoiseValue and BuffStackNumAdvanced sequences.
``memorypack.buff_corpus`` admits both with processor tag five through 30
root fields, source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_origin_or_condition_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_check_buff_stack_condition_receipt as stack
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as target
from scripts.game_data.memorypack import buff_damage_check_vitals_condition_receipt as vitals
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import skill_timeline_check_origin_skill_type as origin


LABEL = "buffDamageOriginOrCondition"
SCHEMA = "endfield.buff-damage-origin-or-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-origin-or-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_origin_or_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    if (
        contract.get("reviewedDependencies") != [
            "skill_timeline_check_origin_skill_type_native.json",
            "buff_48_native.json", "buff_87_native.json",
            "buff_damage_sequence_action_condition_native.json",
            "buff_damage_check_vitals_condition_native.json",
            "buff_damage_check_buff_stack_condition_native.json",
            "levelscript_union_tags.json",
        ]
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or contract.get("originUnionTag") != 72
        or contract.get("orUnionTag") != 135
        or contract.get("originMemberReadKinds") != [
            "bool-byte", "enum32", "scalar32", "scalar32", "enum32",
            "counted-scalar32",
        ]
        or contract.get("orSourceReadOrder") != [
            "byte", "scalar32", "scalar32", "scalar32", "nullable-sequence-list",
        ]
        or contract.get("originSelectedListCount") != 1
        or contract.get("simpleActionTags") != [72, 110]
        or contract.get("nestedActionTags") != [72, 135]
        or contract.get("orNestedSequenceTags") != [[110], [60]]
        or contract.get("orNestedFinderShape") != {
            "buffIdListCount": 0, "tagCount": 1,
            "queryStatus": "named-direct-members-exact-span",
        }
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    plan = contract.get("orActionMemberPlan")
    if (
        not isinstance(plan, list) or len(plan) != 5
        or [row.get("name") for row in plan] != [
            "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
            "conditionList",
        ]
        or [row.get("kind") for row in plan] != [
            "bool-byte", "enum32", "int32", "int32", "sequence-list",
        ]
        or [row.get("width") for row in plan] != [1, 4, 4, 4, None]
    ):
        raise ValueError(f"{LABEL}.contract:or-plan")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove selected action routes, direct source readers and list elements."""
    contract = _contract()
    names = contract["reviewedDependencies"]
    origin_contract, origin_source, or_source, seq_contract, vitals_contract, stack_contract, catalog = [
        json.loads((CONTRACTS_DIR / name).read_bytes()) for name in names
    ]
    expected = contract["nativeInputs"]
    if (
        origin_contract.get("nativeInputs") != expected
        or seq_contract.get("nativeInputs") != expected
        or vitals_contract.get("nativeInputs") != expected
        or stack_contract.get("nativeInputs") != expected
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or origin_contract.get("sourceContract") != names[1]
        or origin_source.get("anonymousReadOrder", {}).get("member6")
        != ["byte", "scalar32", "scalar32", "scalar32", "scalar32", "counted-scalar32"]
        or or_source.get("anonymousReadOrder", {}).get("member5")
        != contract["orSourceReadOrder"]
        or seq_contract.get("memberCount") != contract["sequenceMemberCount"]
        or seq_contract.get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or or_source.get("nestedContexts", [None, None])[1]
        .get("generic", {}).get("elementArguments")
        != [seq_contract["conditionProvider"]["argumentRawHex"]]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    selected = {
        "origin": origin.validate_current_native_contract(),
        "vitals": vitals.validate_current_native_contract(),
        "stack": stack.validate_current_native_contract(),
        "sequence": sequence.validate_current_native_contract(),
    }
    if any(value.get("status") != "validated" for value in selected.values()):
        failed = next(value for value in selected.values()
                      if value.get("status") != "validated")
        return {"status": failed.get("status", "failed"), "detail": failed.get("detail")}
    if (
        any(selected[key].get("nativeInputs") != expected
            for key in ("origin", "vitals", "stack"))
        or selected["origin"].get("sourceReadCount") != 6
        or selected["sequence"].get("serializedReadOrder") != [
            "actionData", "onlyExecuteWhenSourceIsGuard",
            "onlyExecuteWhenSourceIsMainChar",
        ]
        or [row.get("unionTag") for row in selected["vitals"]["routes"]] != [101, 110]
        or selected["stack"].get("unionTag") != 60
    ):
        raise ValueError(f"{LABEL}.native:selected-child-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
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
    if route_audit.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:dispatcher")
    image = open_native_image(gate.gameassembly, gate.metadata)
    for tag in (contract["originUnionTag"], contract["orUnionTag"]):
        native_route = routes.get(tag)
        registered = catalog["families"]["AbilityActionData"][tag]
        if (
            native_route is None or native_route.status != "resolved"
            or native_route.wrapper_name != registered["wrapperName"]
            or registered["tag"] != tag
            or registered["memberCount"] != len(native_route.member_order)
        ):
            raise ValueError(f"{LABEL}.native:selected-route={tag}")
    origin_route = routes[contract["originUnionTag"]]
    origin_reads = origin_contract["orderedSourceReads"]
    if (
        list(origin_route.member_order) != [row["fieldName"] for row in origin_reads]
        or [row["readKind"] for row in origin_reads]
        != contract["originMemberReadKinds"]
        or list(origin_route.member_kinds)
        != ["bool", "enum", "scalar32", "scalar32", "enum", "list"]
    ):
        raise ValueError(f"{LABEL}.native:origin-plan")
    or_route = routes[contract["orUnionTag"]]
    or_plan = contract["orActionMemberPlan"]
    if (
        list(or_route.member_order) != [row["name"] for row in or_plan]
        or list(or_route.member_declared_types)
        != [row["declaredType"] for row in or_plan]
        or list(or_route.member_kinds)
        != ["bool", "enum", "scalar32", "scalar32", "list"]
        or list(or_route.member_widths) != [row["width"] for row in or_plan]
    ):
        raise ValueError(f"{LABEL}.native:or-plan")
    for method in or_source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(or_source["codeWindows"], label=LABEL)
    source_audit = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / names[2],
    )
    if source_audit.get("anonymousReadOrder") != or_source["anonymousReadOrder"]:
        raise ValueError(f"{LABEL}.native:or-source-order")
    origin_plan = [
        {"name": row["fieldName"], "declaredType": declared,
         "kind": row["readKind"], "width": width}
        for row, declared, width in zip(
            origin_reads, origin_route.member_declared_types,
            origin_route.member_widths, strict=True,
        )
    ]
    return {
        "status": "validated", "nativeInputs": expected,
        "originUnionTag": contract["originUnionTag"],
        "originActionMemberPlan": origin_plan,
        "orUnionTag": contract["orUnionTag"],
        "orActionMemberPlan": or_plan,
        "simpleActionTags": contract["simpleActionTags"],
        "nestedActionTags": contract["nestedActionTags"],
        "orNestedSequenceTags": contract["orNestedSequenceTags"],
        "orNestedFinderShape": contract["orNestedFinderShape"],
        "vitalsNative": selected["vitals"], "stackNative": selected["stack"],
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _find_settings(reader: Reader, *, source: str, digest: str,
                   native: dict[str, Any], shape: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    reader.header(3)
    count = reader.count(4, reserve=5, nullable=True)
    for _ in range(max(0, count)):
        reader.byte_payload()
    reader.take(4, "buffSettings.checkType")
    if reader.peek() == 0xFF:
        reader.take(1, "buffSettings.nullQuery")
    else:
        reader.header(2)
        reader.take(4, "buffSettings.queryType")
        tags = reader.count(4, nullable=True)
        reader.take(max(0, tags) * 4, "buffSettings.tags")
    child = stack.finder.decode_find_settings_child_receipt(
        reader.data, source=source, logical_sha256=digest,
        start=start, end=reader.pos, native_validation=native,
    )
    if (
        child.get("status") != "named-direct-members-exact-span"
        or child.get("wholeChildSpanExact") is not True
        or child.get("buffIdListCount") != shape["buffIdListCount"]
        or child.get("tagCount") != shape["tagCount"]
        or child.get("namedFields", [None, None, None])[2].get("queryStatus")
        != shape["queryStatus"]
    ):
        raise ValueError(f"{LABEL}.finder:unsupported-shape")
    return child


def _decode_action(reader: Reader, tag: int, *, source: str, digest: str,
                   native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    if reader.nested_union_tag((tag,), "condition-action") != tag or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.action:selected-nonnull-wrapper")
    if tag == native["originUnionTag"]:
        plan = native["originActionMemberPlan"]
    elif tag == 110:
        plan = native["vitalsNative"]["routes"][1]["actionMemberPlan"]
    elif tag == 60:
        plan = native["stackNative"]["actionMemberPlan"]
    elif tag == native["orUnionTag"]:
        plan = native["orActionMemberPlan"]
    else:
        raise ValueError(f"{LABEL}.action:unsupported-tag={tag}")
    reader.header(len(plan))
    fields = []
    for member in plan:
        field_start = reader.pos
        kind = member["kind"]
        width = member.get("width")
        if width is not None:
            detail = {"rawHex": reader.take(width, member["name"]).hex().upper()}
        elif kind == "counted-scalar32":
            count = reader.count(4, nullable=True)
            reader.take(max(0, count) * 4, member["name"])
            if count != _contract()["originSelectedListCount"]:
                raise ValueError(f"{LABEL}.origin:unsupported-list-count={count}")
            detail = {"count": count, "rawHex": reader.data[field_start:reader.pos].hex().upper()}
        elif kind == "target-settings":
            child_native = (native["stackNative"] if tag == 60
                            else native["vitalsNative"])["targetNative"]
            child = target._simple_target(reader, child_native)
            if child.get("recursiveNamedSchemaExact") is not True:
                raise ValueError(f"{LABEL}.target:child")
            detail = {"namedChild": child}
        elif kind == "blackboard-double":
            reader.scalar_payload()
            child_native = (native["stackNative"] if tag == 60
                            else native["vitalsNative"])["blackboardNative"]
            child = blackboard.decode_adding_cooldown(
                reader.data, field_start, reader.pos,
                native_validation=child_native,
            )
            if child.get("wholeValueExact") is not True:
                raise ValueError(f"{LABEL}.blackboard:child")
            detail = {"namedChild": child}
        elif kind == "buff-find-settings" and tag == 60:
            child = _find_settings(
                reader, source=source, digest=digest,
                native=native["stackNative"]["finderNative"],
                shape=native["orNestedFinderShape"],
            )
            detail = {"namedChild": child}
        elif kind == "sequence-list" and tag == native["orUnionTag"]:
            tags = native["orNestedSequenceTags"]
            count = reader.count(1, nullable=True)
            if count != len(tags):
                raise ValueError(f"{LABEL}.or:unsupported-list-count={count}")
            children = [_decode_sequence(reader, selected, source=source,
                                         digest=digest, native=native)
                        for selected in tags]
            detail = {"count": count, "namedChildren": children}
        else:
            raise ValueError(f"{LABEL}.action:unsupported-member:{member['name']}")
        fields.append({
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": kind, "start": field_start, "end": reader.pos, **detail,
        })
    if (
        fields[0]["start"] != start + 2
        or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
        or fields[-1]["end"] != reader.pos
    ):
        raise ValueError(f"{LABEL}.action:field-tiling")
    return {
        "tag": tag, "start": start, "end": reader.pos,
        "memberCount": len(plan), "namedFields": fields,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
    }


def _decode_sequence(reader: Reader, tags: list[int], *, source: str,
                     digest: str, native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    reader.header(native["sequenceMemberCount"])
    count = reader.count(1, reserve=native["sequenceTerminalByteCount"], nullable=True)
    if count != len(tags):
        raise ValueError(f"{LABEL}.sequence:unsupported-action-count={count}")
    actions = [_decode_action(reader, tag, source=source, digest=digest, native=native)
               for tag in tags]
    terminal = reader.take(native["sequenceTerminalByteCount"], "sequence-terminal")
    if (
        actions[0]["start"] != start + 5
        or any(a["end"] != b["start"] for a, b in zip(actions, actions[1:]))
        or actions[-1]["end"] + len(terminal) != reader.pos
    ):
        raise ValueError(f"{LABEL}.sequence:field-tiling")
    return {
        "status": "exact-selected-sequence", "start": start, "end": reader.pos,
        "actionCount": count, "actions": actions,
        "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
    }


def decode_origin_or_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay either selected compound condition on original logical bytes."""
    contract = _contract()
    native = native_validation
    origin_rows = origin._contract()["orderedSourceReads"]
    origin_plan = native.get("originActionMemberPlan") or []
    vitals_native = native.get("vitalsNative") or {}
    stack_native = native.get("stackNative") or {}
    if (
        native.get("status") != "validated"
        or native.get("nativeInputs") != contract["nativeInputs"]
        or native.get("originUnionTag") != contract["originUnionTag"]
        or native.get("orUnionTag") != contract["orUnionTag"]
        or native.get("orActionMemberPlan") != contract["orActionMemberPlan"]
        or native.get("simpleActionTags") != contract["simpleActionTags"]
        or native.get("nestedActionTags") != contract["nestedActionTags"]
        or native.get("orNestedSequenceTags") != contract["orNestedSequenceTags"]
        or native.get("orNestedFinderShape") != contract["orNestedFinderShape"]
        or [row.get("name") for row in origin_plan]
        != [row["fieldName"] for row in origin_rows]
        or [row.get("kind") for row in origin_plan]
        != contract["originMemberReadKinds"]
        or [row.get("width") for row in origin_plan] != [1, 4, 4, 4, 4, None]
        or vitals_native.get("status") != "validated"
        or vitals_native.get("nativeInputs") != contract["nativeInputs"]
        or vitals_native.get("routes", [None, None])[1].get("actionMemberPlan")
        != vitals._contract()["routes"][1]["actionMemberPlan"]
        or vitals_native.get("targetNative", {}).get("status") != "validated"
        or vitals_native.get("blackboardNative", {}).get("status") != "validated"
        or stack_native.get("status") != "validated"
        or stack_native.get("nativeInputs") != contract["nativeInputs"]
        or stack_native.get("actionMemberPlan") != stack._contract()["actionMemberPlan"]
        or stack_native.get("finderNative", {}).get("status") != "validated"
        or stack_native.get("targetNative", {}).get("status") != "validated"
        or stack_native.get("blackboardNative", {}).get("status") != "validated"
        or native.get("sequenceMemberCount") != contract["sequenceMemberCount"]
        or native.get("sequenceTerminalByteCount")
        != contract["sequenceTerminalByteCount"]
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
    reader.header(contract["sequenceMemberCount"])
    count = reader.count(1, reserve=contract["sequenceTerminalByteCount"], nullable=True)
    if count != 2:
        raise ValueError(f"{LABEL}.sequence:unsupported-action-count={count}")
    first = _decode_action(
        reader, contract["originUnionTag"], source=source,
        digest=logical_sha256.upper(), native=native,
    )
    second_tag = data[reader.pos] if reader.pos < end else None
    if second_tag == contract["simpleActionTags"][1]:
        tags = contract["simpleActionTags"]
        branch = "origin-poise"
    elif second_tag == contract["nestedActionTags"][1]:
        tags = contract["nestedActionTags"]
        branch = "origin-or"
    else:
        raise ValueError(f"{LABEL}.sequence:unsupported-second-tag={second_tag}")
    second = _decode_action(
        reader, tags[1], source=source,
        digest=logical_sha256.upper(), native=native,
    )
    terminal = reader.take(contract["sequenceTerminalByteCount"], "sequence-terminal")
    if (
        reader.pos != end or first["start"] != start + 5
        or first["end"] != second["start"]
        or second["end"] + len(terminal) != end
    ):
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "exact-two-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "branch": branch,
        "actionCount": 2, "actions": [first, second],
        "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join selected report identities to two original-byte condition receipts."""
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
        if condition.get("actionTags") not in ([72, 110], [72, 110, 60, 135]):
            continue
        decoded = decode_origin_or_condition(
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
        "schema": "endfield.buff-damage-origin-or-condition-corpus.v1",
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
