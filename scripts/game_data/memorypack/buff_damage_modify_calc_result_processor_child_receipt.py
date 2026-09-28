"""Native-gated direct members of tag-ten ModifyCalcResult damage processors.

It checks the selected native tag-ten route, its three direct members and
both exact BlackboardDouble child spans, joined to current VFS logical
hashes. ``memorypack.buff_corpus`` admits this sole processor only with one
selected ``CheckDamageDecorateMask`` or ``CheckDamageType`` action, and
proves all 30 root fields through source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_modify_calc_result_processor_current_latest.json``.
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
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard_double
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier


LABEL = "buffDamageModifyCalcResultProcessorChild"
SCHEMA = "endfield.buff-damage-modify-calc-result-processor-child-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-modify-calc-result-processor-child-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_modify_calc_result_processor_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    plan = contract.get("fieldPlan")
    if (
        contract.get("reviewedDependencies") != [
            "buff_damage_lists_native.json", "buff_damage_modifier_child_native.json",
            "buff_adding_cooldown_ownership_native.json",
        ]
        or type(contract.get("unionTag")) is not int
        or not 0 <= contract["unionTag"] <= 65535
        or contract.get("serializedMemberCount") != 3
        or contract.get("sourceReadOrderRef") != "anonymousReadOrder.processor10"
        or not isinstance(contract.get("sourceReadOrder"), list)
        or len(contract["sourceReadOrder"]) != 5
        or not isinstance(plan, list) or len(plan) != 3
        or [row.get("kind") for row in plan]
        != ["blackboard-double", "enum32", "blackboard-double"]
        or len({row.get("name") for row in plan}) != 3
        or any(not row.get("name") or not row.get("declaredType") for row in plan)
        or contract.get("blackboardChildReadOrder")
        != ["blackboardKey", "useBlackboardKey", "value"]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(
    *, modifier_native: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prove selected tag ten and its three direct source members."""
    if modifier_native is None:
        modifier_native = modifier.validate_current_native_contract()
    if modifier_native.get("status") != "validated":
        return {"status": modifier_native.get("status", "missing"),
                "detail": "damage-modifier parent is not validated"}
    contract = _contract()
    expected = contract["nativeInputs"]
    base = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes()
    )
    parent = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][1]).read_bytes()
    )
    blackboard_contract = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][2]).read_bytes()
    )
    if (
        base.get("schemaVersion") != 1
        or base.get("anonymousReadOrder", {}).get("processor10")
        != contract["sourceReadOrder"]
        or parent.get("schema")
        != "endfield.buff-damage-modifier-child-native-contract.v1"
        or parent.get("nativeInputs") != expected
        or blackboard_contract.get("schema") != blackboard_double.SCHEMA
        or blackboard_contract.get("nativeInputs") != expected
        or blackboard_contract.get("selectedReadOrder")
        != contract["blackboardChildReadOrder"]
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
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
    image = open_native_image(gate.gameassembly, gate.metadata)
    wrapper = contract["wrapperType"]
    selected_methods = [row for row in base["methods"]
                        if row[1] == wrapper or row[1].startswith(wrapper + "+")]
    dispatcher_methods = [row for row in base["methods"]
                          if row[1].endswith("DamageProcessorBaseForMemoryPackFormatter")]
    windows = [row for row in base["codeWindows"]
               if row["boundary"].startswith("tag10 ")
               or row["boundary"].startswith("dispatcher tag10 ")]
    contexts = [row for row in base["nestedContexts"]
                if any(window["startRva"] <= row["instructionRva"] < window["endRva"]
                       for window in windows if window["boundary"].startswith("tag10 header"))]
    if (
        len(selected_methods) != 2
        or len(dispatcher_methods) != 1
        or len(windows) != 3
        or len(contexts) != 3
        or [row["typeName"] for row in contexts]
        != [member["declaredType"] for member in contract["fieldPlan"]]
        or [row["instructionRva"] for row in contexts]
        != sorted(row["instructionRva"] for row in contexts)
    ):
        raise ValueError(f"{LABEL}.contract:selected-route")
    for row in dispatcher_methods + selected_methods:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(windows, label=LABEL)
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == wrapper]
    if len(owners) != 1:
        raise ValueError(f"{LABEL}.native:wrapper-type")
    setters = image.setter_methods(owners[0], parameter="typeName", label=LABEL)
    if (
        len(setters) != 3
        or [row[1] for row in setters]
        != [f"set___{member['name']}__" for member in contract["fieldPlan"]]
        or [row[2] for row in setters]
        != [member["declaredType"] for member in contract["fieldPlan"]]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-setters")
    for context in contexts:
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
            spec != context["methodSpec"]
            or len(arguments) != 1
            or arguments[0].raw_type_record_hex != context["argumentRawHex"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:method-context")
    blackboard_native = blackboard_double.validate_current_native_contract()
    if (
        blackboard_native.get("status") != "validated"
        or blackboard_native.get("selectedReadOrder")
        != contract["blackboardChildReadOrder"]
    ):
        raise ValueError(f"{LABEL}.native:blackboard-child")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"],
        "wrapperType": wrapper, "wrappedType": contract["wrappedType"],
        "fieldPlan": contract["fieldPlan"],
        "blackboardChildNative": blackboard_native,
        "blackboardChildReadOrder": contract["blackboardChildReadOrder"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_modify_calc_result_processor_span(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name two BlackboardDouble members and the direct enum slot."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("unionTag") != contract["unionTag"]
        or native_validation.get("fieldPlan") != contract["fieldPlan"]
        or native_validation.get("blackboardChildNative", {}).get("status")
        != "validated"
        or native_validation.get("blackboardChildReadOrder")
        != contract["blackboardChildReadOrder"]
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
    tag = reader.nested_union_tag((native_validation["unionTag"],), "damage-processor")
    if tag != native_validation["unionTag"] or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.processor:selected-nonnull-wrapper")
    reader.header(len(native_validation["fieldPlan"]))
    fields = []
    for member in native_validation["fieldPlan"]:
        field_start = reader.pos
        if member["kind"] == "blackboard-double":
            reader.scalar_payload()
            child = blackboard_double.decode_adding_cooldown(
                data, field_start, reader.pos,
                native_validation=native_validation["blackboardChildNative"],
            )
            if (
                child.get("wholeValueExact") is not True
                or child.get("startOffset") != field_start
                or child.get("consumedEnd") != reader.pos
                or (child["fields"] and [row["name"] for row in child["fields"]]
                    != native_validation["blackboardChildReadOrder"])
            ):
                raise ValueError(f"{LABEL}.blackboard-child:boundary")
            detail = {"namedChild": child, "childBoundary": "named-exact"}
        elif member["kind"] == "enum32":
            raw = reader.take(4, member["name"])
            detail = {"storedInt32": struct.unpack("<i", raw)[0],
                      "rawHex": raw.hex().upper()}
        else:
            raise ValueError(f"{LABEL}.field:unsupported-kind")
        fields.append({"name": member["name"],
                       "declaredType": member["declaredType"],
                       "start": field_start, "end": reader.pos, **detail})
    if reader.pos != end or fields[-1]["end"] != end:
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "named-direct-members-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "unionTag": tag,
        "wrapperType": native_validation["wrapperType"],
        "wrappedType": native_validation["wrappedType"],
        "namedFields": fields,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join current VFS identities to exact tag-ten processor spans."""
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
    modifier_native = modifier.validate_current_native_contract()
    native = validate_current_native_contract(modifier_native=modifier_native)
    if native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:{native.get('status')}")
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
        if fields[1].get("name") != "damageProcessors":
            raise ValueError(f"{LABEL}.parent:processor-field:{source}")
        processors = fields[1].get("processors") or []
        if len(processors) != 1 or processors[0].get("tag") != native["unionTag"]:
            continue
        processor = processors[0]
        decoded = decode_modify_calc_result_processor_span(
            data, source=source, logical_sha256=digest,
            start=processor["start"], end=processor["end"],
            native_validation=native,
        )
        condition_tags = fields[0].get("actionTags") or []
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionTags": condition_tags, "processorReceipt": decoded,
            "projectedRootWithSelectedCondition": condition_tags in ([91], [93]),
        })
    tags = Counter(tuple(row["conditionTags"]) for row in rows)
    return {
        "schema": "endfield.buff-damage-modify-calc-result-processor-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "tagTenProcessorExact": len(rows),
            "conditionTags": {",".join(map(str, key)): value for key, value in sorted(tags.items())},
            "projectedRootWithSelectedCondition": sum(
                row["projectedRootWithSelectedCondition"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS-verified source identities and logical hashes join selected "
            "tag-ten processor child spans. Root projection is a frontier rank, "
            "not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_modify_calc_result_processor_span",
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
