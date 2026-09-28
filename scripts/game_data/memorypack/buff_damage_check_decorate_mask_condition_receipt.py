"""Exact selected one-action CheckDamageDecorateMask damage condition span.

This reader certifies a stored SequenceActionData child. Its enclosing
DamageModifier and BuffData require their own composed cursor proof.
"""
from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier


LABEL = "buffDamageCheckDecorateMaskCondition"
SCHEMA = "endfield.buff-damage-check-decorate-mask-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-check-decorate-mask-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_check_decorate_mask_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    plan = contract.get("actionMemberPlan")
    if (
        contract.get("reviewedDependencies") != [
            "levelscript_union_tags.json", "buff_5b_native.json",
            "buff_damage_sequence_action_condition_native.json",
        ]
        or contract.get("unionFamily") != "AbilityActionData"
        or type(contract.get("unionTag")) is not int
        or not 0 <= contract["unionTag"] <= 65535
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or not isinstance(plan, list) or len(plan) != 6
        or [row.get("kind") for row in plan]
        != ["bool-byte", "enum32", "int32", "int32", "enum32", "int64"]
        or [row.get("width") for row in plan] != [1, 4, 4, 4, 4, 8]
        or len({row.get("name") for row in plan}) != len(plan)
        or any(not row.get("name") or not row.get("declaredType") for row in plan)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    """Check the current route, source reader, and selected sequence parent."""
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
    expected = contract["nativeInputs"]
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or source.get("schemaVersion") != 1
        or source.get("anonymousReadOrder", {}).get("member6")
        != ["byte", "scalar32", "scalar32", "scalar32", "scalar32", "scalar64"]
        or selected_sequence.get("schema")
        != "endfield.buff-damage-sequence-action-condition-native-contract.v1"
        or selected_sequence.get("nativeInputs") != expected
        or selected_sequence.get("memberCount") != contract["sequenceMemberCount"]
        or selected_sequence.get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    reviewed = [row for row in catalog["families"][contract["unionFamily"]]
                if row.get("tag") == contract["unionTag"]]
    if (
        len(reviewed) != 1
        or reviewed[0].get("wrapperName") != contract["wrapperType"]
        or reviewed[0].get("wrappedType") != contract["wrappedType"]
        or reviewed[0].get("memberCount") != len(contract["actionMemberPlan"])
        or len(source.get("methods", [])) != 2
        or not source.get("codeWindows")
    ):
        raise ValueError(f"{LABEL}.contract:route-or-source")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "detail": gate.detail}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity)}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    sequence_native = sequence.validate_current_native_contract()
    if sequence_native.get("status") != "validated":
        return {"status": sequence_native.get("status", "failed"),
                "sequence": sequence_native}
    routes, route_audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    route = routes.get(contract["unionTag"])
    plan = contract["actionMemberPlan"]
    compatible = {
        "bool-byte": ("bool", 1),
        "enum32": ("enum", 4),
        "int32": ("scalar32", 4),
        "int64": ("scalar64", 8),
    }
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
    for method in source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"], "wrapperType": contract["wrapperType"],
        "wrappedType": contract["wrappedType"],
        "actionMemberPlan": plan,
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "sequenceNative": sequence_native,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_check_decorate_mask_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay exactly one tagged action and both terminal bytes to end."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("unionTag") != contract["unionTag"]
        or native_validation.get("actionMemberPlan") != contract["actionMemberPlan"]
        or native_validation.get("sequenceNative", {}).get("status") != "validated"
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper():
        raise ValueError(f"{LABEL}.source:sha256")
    virtual = PurePosixPath(source)
    if (
        not isinstance(source, str) or virtual.is_absolute()
        or virtual.parts[:3] != ("Data", "Json", "BuffData")
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
    reader.header(len(native_validation["actionMemberPlan"]))
    fields = []
    for member in native_validation["actionMemberPlan"]:
        field_start = reader.pos
        raw = reader.take(member["width"], member["name"])
        fields.append({
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": member["kind"], "start": field_start, "end": reader.pos,
            "rawHex": raw.hex().upper(),
        })
    action_end = reader.pos
    terminal = reader.take(native_validation["sequenceTerminalByteCount"], "sequence-terminals")
    if reader.pos != end or fields[0]["start"] != tag_end + 1 or fields[-1]["end"] != action_end:
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
    """Join current VFS identities to exact stored condition spans."""
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
        path = export_root / virtual.name
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != identity["length"] or digest != source_row["logicalSha256"]:
            raise ValueError(f"{LABEL}.source:logical-bytes:{source}")
        parent = modifier.decode_damage_modifier_collection(
            data, blocker["start"], blocker["end"], source=source,
            native_validation=modifier_native,
        )
        if parent.get("count") != 1 or len(parent.get("elements", [])) != 1:
            continue
        element = parent["elements"][0]
        fields = element["fields"]
        condition = fields[0]
        if (
            condition.get("name") != "condition"
            or condition.get("actionTags") != [native["unionTag"]]
            or condition.get("actionUnionCount") != 1
        ):
            continue
        decoded = decode_check_decorate_mask_condition(
            data, source=source, logical_sha256=digest,
            start=condition["start"], end=condition["end"],
            native_validation=native,
        )
        processor_field = fields[1]
        processor_tags = [item["tag"] for item in processor_field["processors"]]
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionReceipt": decoded, "processorTags": processor_tags,
            "projectedRootWithSelectedProcessor": processor_tags == [5],
        })
    tags = Counter(tuple(row["processorTags"]) for row in rows)
    return {
        "schema": "endfield.buff-damage-check-decorate-mask-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "oneActionConditionExact": len(rows),
            "processorTags": {",".join(map(str, key)): value for key, value in sorted(tags.items())},
            "projectedRootWithSelectedProcessor": sum(
                row["projectedRootWithSelectedProcessor"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS-verified source identities and logical hashes join selected "
            "one-action condition child spans. Root projection is a frontier rank, "
            "not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_check_decorate_mask_condition",
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
