"""Selected exact nested children of BuffData ModifyDynamicBlackboard actions.

It checks the selected native tag-236 ten-member action with exact simple
TargetSettings and BlackboardDouble child endpoints on current logical source
bytes. The reached children close inside compound conditions that stay
partial, so this receipt makes no whole-root promotion.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_modify_dynamic_blackboard_child_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.buff_residual_actions import _ResidualReader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as target
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as action


LABEL = "buffDamageModifyDynamicBlackboardChild"
SCHEMA = "endfield.buff-damage-modify-dynamic-blackboard-child-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-modify-dynamic-blackboard-child-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_modify_dynamic_blackboard_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    if (
        contract.get("unionTag") != action.TAG
        or len(contract.get("reviewedDependencies", [])) != 4
        or len(contract.get("selectedFieldNames", [])) != contract.get("memberCount")
        or len(contract.get("selectedReadKinds", [])) != contract.get("memberCount")
        or any(type(contract.get(key)) is not int or not 0 <= contract[key] < contract["memberCount"]
               for key in ("targetFieldIndex", "blackboardFieldIndex"))
        or contract["targetFieldIndex"] == contract["blackboardFieldIndex"]
        or contract["selectedFieldNames"][contract["targetFieldIndex"]] != "calculationTarget"
        or contract["selectedFieldNames"][contract["blackboardFieldIndex"]] != "value"
        or contract.get("selectedTargetShapeRef")
        != f"{contract['reviewedDependencies'][2]}.selectedTargetShape"
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None,
                                    target_parent_tags: tuple[int, ...] | None = None) -> dict[str, Any]:
    """Compose the selected wrapper, simple target, and BlackboardDouble gates."""
    contract = _contract()
    source, catalog, target_contract, blackboard_contract = [
        json.loads((CONTRACTS_DIR / name).read_bytes())
        for name in contract["reviewedDependencies"]
    ]
    expected = contract["nativeInputs"]
    if (
        source.get("schemaVersion") != 1
        or source.get("anonymousReadOrder", {}).get("member10")
        != contract["selectedReadKinds"]
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or catalog["families"]["AbilityActionData"][contract["unionTag"]]
        .get("memberCount") != contract["memberCount"]
        or target_contract.get("nativeInputs") != expected
        or blackboard_contract.get("nativeInputs") != expected
        or blackboard_contract.get("selectedReadOrder")
        != ["blackboardKey", "useBlackboardKey", "value"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    paths = {key: value for key, value in (("gameassembly", gameassembly), ("metadata", metadata)) if value is not None}
    selected = {
        "action": action.validate_current_native_contract(**paths),
        "target": target.validate_current_native_contract(target_parent_tags=target_parent_tags, **paths),
        "blackboard": blackboard.validate_current_native_contract(**paths),
    }
    if any(row.get("status") != "validated" for row in selected.values()):
        failed = next(row for row in selected.values()
                      if row.get("status") != "validated")
        return {"status": failed.get("status", "failed"), "detail": failed.get("detail")}
    if (
        selected["action"].get("unionTag") != contract["unionTag"]
        or selected["action"].get("memberCount") != contract["memberCount"]
        or selected["action"].get("memberNames") != contract["selectedFieldNames"]
        or selected["action"].get("readKinds") != contract["selectedReadKinds"]
        or selected["action"].get("nativeInputs") != {
            "GameAssembly.dll": expected["GameAssembly.dll"],
            "global-metadata.dat": expected["global-metadata.dat"],
        }
        or selected["target"].get("nativeInputs") != expected
        or selected["target"].get("selectedTargetShape")
        != target_contract["selectedTargetShape"]
        or selected["target"].get("nestedNative") != {
            "target": "validated", "direction": "validated",
            "selector": "validated", "query": "validated",
        }
        or selected["blackboard"].get("status") != "validated"
        or selected["blackboard"].get("selectedReadOrder")
        != blackboard_contract["selectedReadOrder"]
    ):
        raise ValueError(f"{LABEL}.native:selected-child-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"],
        "memberCount": contract["memberCount"],
        "selectedFieldNames": contract["selectedFieldNames"],
        "selectedReadKinds": contract["selectedReadKinds"],
        "targetFieldIndex": contract["targetFieldIndex"],
        "blackboardFieldIndex": contract["blackboardFieldIndex"],
        "selectedTargetShape": contract["selectedTargetShapeRef"],
        "actionNative": selected["action"],
        "targetNative": selected["target"],
        "blackboardNative": selected["blackboard"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_modify_dynamic_blackboard_child(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name all ten members and reparse both nested values on source bytes."""
    contract = _contract()
    native = native_validation
    if (
        native.get("status") != "validated"
        or native.get("nativeInputs") != contract["nativeInputs"]
        or native.get("unionTag") != contract["unionTag"]
        or native.get("memberCount") != contract["memberCount"]
        or native.get("selectedFieldNames") != contract["selectedFieldNames"]
        or native.get("selectedReadKinds") != contract["selectedReadKinds"]
        or native.get("targetFieldIndex") != contract["targetFieldIndex"]
        or native.get("blackboardFieldIndex") != contract["blackboardFieldIndex"]
        or native.get("actionNative", {}).get("status") != "validated"
        or native.get("targetNative", {}).get("status") != "validated"
        or native.get("blackboardNative", {}).get("status") != "validated"
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
    wrapper = action.decode_modify_dynamic_blackboard_action_receipt(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, native_validation=native["actionNative"],
    )
    fields = wrapper.get("namedFields") or []
    if (
        wrapper.get("status") != "named-wrapper-exact-span"
        or wrapper.get("wholeActionByteSpanExact") is not True
        or [field.get("fieldName") for field in fields]
        != contract["selectedFieldNames"]
        or [field.get("kind") for field in fields]
        != contract["selectedReadKinds"]
    ):
        raise ValueError(f"{LABEL}.wrapper:selected-shape")
    target_field = fields[native["targetFieldIndex"]]
    target_reader = Reader(data, source, target_field["end"])
    target_reader.pos = target_field["start"]
    target_child = target._simple_target(target_reader, native["targetNative"])
    if (
        target_child.get("status") != "exact-simple-target"
        or target_child.get("recursiveNamedSchemaExact") is not True
        or target_child.get("start") != target_field["start"]
        or target_child.get("end") != target_field["end"]
        or target_reader.pos != target_field["end"]
    ):
        raise ValueError(f"{LABEL}.target:selected-shape")
    value_field = fields[native["blackboardFieldIndex"]]
    value_child = blackboard.decode_adding_cooldown(
        data, value_field["start"], value_field["end"],
        native_validation=native["blackboardNative"],
    )
    if (
        value_child.get("wholeValueExact") is not True
        or value_child.get("startOffset") != value_field["start"]
        or value_child.get("consumedEnd") != value_field["end"]
    ):
        raise ValueError(f"{LABEL}.blackboard:selected-shape")
    named = [
        {**field, "namedChild": target_child} if index == native["targetFieldIndex"]
        else {**field, "namedChild": value_child} if index == native["blackboardFieldIndex"]
        else field
        for index, field in enumerate(fields)
    ]
    return {
        "schema": SCHEMA, "status": "named-direct-members-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "unionTag": native["unionTag"], "start": start, "end": end,
        "memberCount": len(named), "namedFields": named,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False, "evidenceBoundary": native["evidenceBoundary"],
    }


def audit_current_remaining_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Replay reached tag-236 spans in the current residual damage frontier."""
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
        condition = parent["elements"][0]["fields"][0]
        if native["unionTag"] not in condition.get("actionTags", []):
            continue
        structural = _ResidualReader(data, source, condition["end"])
        structural.pos = condition["start"]
        structural.sequence()
        if structural.pos != condition["end"]:
            raise ValueError(f"{LABEL}.condition:structural-end:{source}")
        spans = [row for row in structural.records
                 if row.get("kind") == "union" and row.get("tag") == native["unionTag"]]
        children = [decode_modify_dynamic_blackboard_child(
            data, source=source, logical_sha256=digest,
            start=span["start"], end=span["end"], native_validation=native,
        ) for span in spans]
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionStart": condition["start"], "conditionEnd": condition["end"],
            "actionChildren": children, "wholeBuffDataPromoted": False,
        })
    return {
        "schema": "endfield.buff-damage-modify-dynamic-blackboard-child-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "selectedFiles": len(rows),
            "selectedActionChildren": sum(len(row["actionChildren"]) for row in rows),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Selected current VFS identities and original source bytes rejoin exact "
            "nested action children. Compound condition and whole root proof remain open."
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
    result = audit_current_remaining_frames(
        args.buff_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
