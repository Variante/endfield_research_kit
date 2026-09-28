"""Exact selected NotNextCheckAction/main-character damage condition."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_check_main_character_condition_receipt as main_character
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as target
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence


LABEL = "buffDamageNotNextMainCondition"
SCHEMA = "endfield.buff-damage-not-next-main-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-not-next-main-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_not_next_main_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    if (
        contract.get("reviewedDependencies") != [
            "buff_fd_native.json", "levelscript_union_tags.json",
            "buff_damage_check_main_character_condition_native.json",
            "buff_damage_sequence_action_condition_native.json",
        ]
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or contract.get("selectedActionTags") != [253, 104]
        or [row.get("name") for row in contract.get("notNextActionMemberPlan", [])]
        != ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex"]
        or [row.get("kind") for row in contract["notNextActionMemberPlan"]]
        != ["bool-byte", "enum32", "int32", "int32"]
        or [row.get("width") for row in contract["notNextActionMemberPlan"]]
        != [1, 4, 4, 4]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(
    *, main_character_native: dict[str, Any] | None = None,
    sequence_native: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check the selected build, fieldless wrapper and nested target route."""
    contract = _contract()
    names = contract["reviewedDependencies"]
    fd, catalog, main_contract, sequence_contract = [
        json.loads((CONTRACTS_DIR / name).read_bytes()) for name in names
    ]
    expected = contract["nativeInputs"]
    if (
        fd.get("schemaVersion") != 1
        or fd.get("anonymousReadOrder", {}).get("member4")
        != ["byte", "scalar32", "scalar32", "scalar32"]
        or len(fd.get("methods", [])) != 2
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or main_contract.get("nativeInputs") != expected
        or main_contract.get("unionTag") != contract["selectedActionTags"][1]
        or sequence_contract.get("nativeInputs") != expected
        or sequence_contract.get("memberCount") != contract["sequenceMemberCount"]
        or sequence_contract.get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
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
    image = open_native_image(gate.gameassembly, gate.metadata)
    for row in fd["methods"]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(fd["codeWindows"], label=LABEL)
    selected = (
        main_character_native if main_character_native is not None
        else main_character.validate_current_native_contract()
    )
    selected_sequence = (
        sequence_native if sequence_native is not None
        else sequence.validate_current_native_contract()
    )
    if any(row.get("status") != "validated" for row in (selected, selected_sequence)):
        failed = next(row for row in (selected, selected_sequence)
                      if row.get("status") != "validated")
        return {"status": failed.get("status", "failed"), "detail": failed.get("detail")}
    routes, audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    tag = contract["selectedActionTags"][0]
    route = routes.get(tag)
    catalog_route = catalog["families"]["AbilityActionData"][tag]
    plan = contract["notNextActionMemberPlan"]
    if (
        audit.get("status") != "validated"
        or {key: str(value).upper() for key, value in
            audit.get("nativeInputs", {}).items()} != {
                "GameAssembly.dll": expected["GameAssembly.dll"],
                "global-metadata.dat": expected["global-metadata.dat"],
            }
        or route is None or route.status != "resolved"
        or route.wrapper_name != fd["methods"][1][1]
        or route.inherited_member_count != len(plan)
        or list(route.member_order) != [row["name"] for row in plan]
        or list(route.member_declared_types) != [row["declaredType"] for row in plan]
        or list(route.member_kinds) != ["bool", "enum", "scalar32", "scalar32"]
        or list(route.member_widths) != [row["width"] for row in plan]
        or catalog_route.get("tag") != tag
        or catalog_route.get("wrapperName") != route.wrapper_name
        or catalog_route.get("memberCount") != len(plan)
        or selected.get("nativeInputs") != expected
        or selected.get("unionTag") != contract["selectedActionTags"][1]
        or selected_sequence.get("serializedReadOrder") != [
            "actionData", "onlyExecuteWhenSourceIsGuard",
            "onlyExecuteWhenSourceIsMainChar",
        ]
    ):
        raise ValueError(f"{LABEL}.native:selected-route-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "selectedActionTags": contract["selectedActionTags"],
        "notNextActionMemberPlan": plan,
        "mainCharacterNative": selected,
        "sequenceNative": selected_sequence,
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_not_next_main_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay selected two-action condition to its supplied source endpoint."""
    contract = _contract()
    native = native_validation
    if (
        native.get("status") != "validated"
        or native.get("nativeInputs") != contract["nativeInputs"]
        or native.get("selectedActionTags") != contract["selectedActionTags"]
        or native.get("notNextActionMemberPlan")
        != contract["notNextActionMemberPlan"]
        or native.get("sequenceMemberCount") != contract["sequenceMemberCount"]
        or native.get("sequenceTerminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or native.get("mainCharacterNative", {}).get("status") != "validated"
        or native.get("mainCharacterNative", {}).get("unionTag") != 104
        or native.get("sequenceNative", {}).get("status") != "validated"
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
    if count != 2:
        raise ValueError(f"{LABEL}.sequence:action-count={count}")
    actions = []
    for index, tag in enumerate(native["selectedActionTags"]):
        action_start = reader.pos
        if reader.nested_union_tag((tag,), "condition-action") != tag or reader.peek() == 0xFF:
            raise ValueError(f"{LABEL}.action:selected-nonnull-wrapper={tag}")
        tag_end = reader.pos
        plan = (native["notNextActionMemberPlan"] if index == 0
                else native["mainCharacterNative"]["actionMemberPlan"])
        reader.header(len(plan))
        fields = []
        for member in plan:
            field_start = reader.pos
            if member["kind"] == "target-settings":
                child = target._simple_target(reader, native["mainCharacterNative"])
                if child.get("recursiveNamedSchemaExact") is not True:
                    raise ValueError(f"{LABEL}.target:recursive-child")
                detail = {"namedChild": child}
            else:
                raw = reader.take(member["width"], member["name"])
                if member["kind"] == "bool-byte" and raw[0] not in (0, 1):
                    raise ValueError(f"{LABEL}.action:bool-byte={tag}")
                detail = {"rawHex": raw.hex().upper()}
            fields.append({
                "name": member["name"], "declaredType": member["declaredType"],
                "kind": member["kind"], "start": field_start,
                "end": reader.pos, **detail,
            })
        if (
            fields[0]["start"] != tag_end + 1
            or any(left["end"] != right["start"]
                   for left, right in zip(fields, fields[1:]))
            or fields[-1]["end"] != reader.pos
        ):
            raise ValueError(f"{LABEL}.action:field-tiling={tag}")
        actions.append({
            "tag": tag, "start": action_start, "end": reader.pos,
            "memberCount": len(plan), "namedFields": fields,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        })
    terminal = reader.take(native["sequenceTerminalByteCount"], "sequence-terminal")
    if (
        reader.pos != end or actions[0]["start"] != start + 5
        or actions[0]["end"] != actions[1]["start"]
        or actions[1]["end"] + len(terminal) != end
    ):
        raise ValueError(f"{LABEL}.sequence:cursor={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA, "status": "exact-two-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": count,
        "actions": actions, "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False, "evidenceBoundary": native["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Rejoin the selected source identity and positive damage child frame."""
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
        if source_row.get("rootPositiveDamageFrameCandidate") is not True:
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
        condition = fields[0]
        if condition.get("actionTags") != native["selectedActionTags"]:
            continue
        decoded = decode_not_next_main_condition(
            data, source=source, logical_sha256=digest,
            start=condition["start"], end=condition["end"], native_validation=native,
        )
        processor_tags = [row["tag"] for row in fields[1]["processors"]]
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionReceipt": decoded, "processorTags": processor_tags,
            "projectedRootWithSelectedProcessor": processor_tags == [4],
            "wholeBuffDataAlreadyExact": source_row.get("rootPositiveDamageCandidate") is True,
        })
    return {
        "schema": "endfield.buff-damage-not-next-main-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "selectedConditionExact": len(rows),
            "projectedRootWithSelectedProcessor": sum(
                row["projectedRootWithSelectedProcessor"] for row in rows),
            "wholeBuffDataAlreadyExact": sum(
                row["wholeBuffDataAlreadyExact"] for row in rows),
        },
        "rows": rows,
        "evidenceBoundary": (
            "Selected current VFS identities, source bytes and native condition routes "
            "close the condition only. Root projection awaits independent EOF proof."
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
