"""Exact selected tag-nine InstantModifyAttribute damage processor child.

It checks the selected native tag-nine two-member route, its four-member
AttributeModifier child and the exact BlackboardDouble param span, joined to
the current VFS logical hash. ``memorypack.buff_corpus`` admits it with a
sole selected ``CheckBuffStackNumAdvanced`` action through all 30 root
fields, source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_instant_modify_attribute_processor_current_latest.json``.
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
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier


LABEL = "buffDamageInstantModifyAttributeProcessor"
SCHEMA = "endfield.buff-damage-instant-modify-attribute-processor-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-instant-modify-attribute-processor-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_instant_modify_attribute_processor_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    fields = contract.get("fieldPlan")
    nested = contract.get("modifierFieldPlan")
    if (
        contract.get("reviewedDependencies") != [
            "buff_damage_lists_native.json", "buff_root_prefix_native.json",
            "buff_adding_cooldown_ownership_native.json",
        ]
        or contract.get("unionTag") != 9
        or contract.get("memberCount") != 2
        or contract.get("modifierMemberCount") != 4
        or contract.get("sourceReadOrder") != [
            "union9", "FF wrapper or header2", "modifier-element-profile",
            "required raw scalar32",
        ]
        or contract.get("modifierReadOrder") != [
            "DWORD", "DWORD", "DWORD", "scalar-payload",
        ]
        or not isinstance(fields, list) or len(fields) != 2
        or [(row.get("name"), row.get("kind"), row.get("width")) for row in fields]
        != [("modifier", "attribute-modifier", None),
            ("modifyTargetSide", "enum32", 4)]
        or not isinstance(nested, list) or len(nested) != 4
        or [(row.get("name"), row.get("kind"), row.get("width")) for row in nested]
        != [("attributeType", "enum32", 4), ("formulaItem", "enum32", 4),
            ("modifyAttributeType", "enum32", 4),
            ("param", "blackboard-double", None)]
        or not isinstance(contract.get("wrapperSetterMethods"), list)
        or len(contract["wrapperSetterMethods"]) != 2
        or [(row[1], row[2]) for row in contract["wrapperSetterMethods"]]
        != [(f"set___{field['name']}__", field["declaredType"]) for field in fields]
        or any(type(row[0]) is not int for row in contract["wrapperSetterMethods"])
        or not isinstance(contract.get("modifierSetterMethods"), list)
        or len(contract["modifierSetterMethods"]) != 4
        or [(row[1], row[2]) for row in contract["modifierSetterMethods"]]
        != [(f"set___{field['name']}__", field["declaredType"]) for field in nested]
        or any(type(row[0]) is not int for row in contract["modifierSetterMethods"])
        or len(contract.get("processorMethodIndices", [])) != 2
        or len(contract.get("processorWindowStarts", [])) != 2
        or len(contract.get("processorContextRvas", [])) != 2
        or len(contract.get("modifierMethodIndices", [])) != 2
        or len(contract.get("modifierWindowStarts", [])) != 2
        or len(contract.get("modifierContextRvas", [])) != 4
        or contract.get("blackboardChildReadOrder")
        != ["blackboardKey", "useBlackboardKey", "value"]
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _validate_contexts(image: Any, contexts: list[dict[str, Any]],
                       names: list[str]) -> None:
    for context, name in zip(contexts, names, strict=True):
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index:{name}")
        spec = list(struct.unpack(
            "<iii", image.pe.bytes_at_va(
                int(image.registration["methodSpecs"], 16) + index * 12, 12,
            ),
        ))
        arguments = image.instantiations.resolve(spec[2]).arguments
        if (
            spec != context["methodSpec"] or len(arguments) != 1
            or arguments[0].raw_type_record_hex != context["argumentRawHex"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
            or context["typeName"] != name
        ):
            raise ValueError(f"{LABEL}.native:context:{name}")


def validate_current_native_contract(
    *, modifier_native: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check selected route, two generated wrappers and nested contexts."""
    if modifier_native is None:
        modifier_native = modifier.validate_current_native_contract()
    if modifier_native.get("status") != "validated":
        return {"status": modifier_native.get("status", "missing"),
                "detail": "damage-modifier parent is not validated"}
    contract = _contract()
    expected = contract["nativeInputs"]
    base, nested, blackboard_contract = [
        json.loads((CONTRACTS_DIR / name).read_bytes())
        for name in contract["reviewedDependencies"]
    ]
    if (
        base.get("schemaVersion") != 1
        or nested.get("schemaVersion") != 1
        or base.get("anonymousReadOrder", {}).get("processor9")
        != contract["sourceReadOrder"]
        or nested.get("anonymousReadOrder", {}).get("modifierElementHeader4")
        != contract["modifierReadOrder"]
        or blackboard_contract.get("schema") != blackboard.SCHEMA
        or blackboard_contract.get("nativeInputs") != expected
        or blackboard_contract.get("selectedReadOrder")
        != contract["blackboardChildReadOrder"]
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
    dispatcher = [row for row in base["methods"]
                  if row[1].endswith("DamageProcessorBaseForMemoryPackFormatter")]
    if len(dispatcher) != 1:
        raise ValueError(f"{LABEL}.contract:dispatcher")
    image.validate_method_row(dispatcher[0], label=LABEL)
    selections = (
        (base, "processor", "wrapperType", "wrapperSetterMethods", "fieldPlan"),
        (nested, "modifier", "modifierWrapperType", "modifierSetterMethods", "modifierFieldPlan"),
    )
    for source, prefix, wrapper_key, setter_key, field_key in selections:
        wrapper = contract[wrapper_key]
        methods = [row for row in source["methods"]
                   if row[0] in contract[f"{prefix}MethodIndices"]]
        windows = [row for row in source["codeWindows"]
                   if row["startRva"] in contract[f"{prefix}WindowStarts"]]
        contexts = [row for row in source["nestedContexts"]
                    if row["instructionRva"] in contract[f"{prefix}ContextRvas"]]
        if (
            [row[0] for row in methods] != contract[f"{prefix}MethodIndices"]
            or [row["startRva"] for row in windows] != contract[f"{prefix}WindowStarts"]
            or [row["instructionRva"] for row in contexts]
            != contract[f"{prefix}ContextRvas"]
            or methods[0][1] != wrapper + "+" + wrapper.rsplit(".", 1)[-1] + "Formatter"
            or methods[1][1] != wrapper
        ):
            raise ValueError(f"{LABEL}.contract:{prefix}-route")
        for row in methods:
            image.validate_method_row(row, label=LABEL)
        image.check_windows(windows, label=LABEL)
        owners = [row for row in image.metadata.types
                  if image.metadata.type_full_name(row) == wrapper]
        if (
            len(owners) != 1
            or image.setter_methods(owners[0], parameter="typeName", label=LABEL)
            != contract[setter_key]
        ):
            raise ValueError(f"{LABEL}.native:{prefix}-setters")
        expected_names = [field["declaredType"] for field in contract[field_key]]
        _validate_contexts(image, contexts, expected_names)
    entry = [row for row in base["dataWindows"]
             if row["boundary"].startswith("union tag 9 table entry routes")]
    if len(entry) != 1:
        raise ValueError(f"{LABEL}.contract:union-entry")
    image.check_windows(entry, gate="union-data-window", label=LABEL)
    blackboard_native = blackboard.validate_current_native_contract()
    if (
        blackboard_native.get("status") != "validated"
        or blackboard_native.get("selectedReadOrder")
        != contract["blackboardChildReadOrder"]
    ):
        raise ValueError(f"{LABEL}.native:blackboard-child")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"],
        "wrapperType": contract["wrapperType"],
        "fieldPlan": contract["fieldPlan"],
        "modifierFieldPlan": contract["modifierFieldPlan"],
        "blackboardChildNative": blackboard_native,
        "blackboardChildReadOrder": contract["blackboardChildReadOrder"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_instant_modify_attribute_processor_span(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay one nonnull tag-nine child and its named modifier."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("unionTag") != contract["unionTag"]
        or native_validation.get("fieldPlan") != contract["fieldPlan"]
        or native_validation.get("modifierFieldPlan") != contract["modifierFieldPlan"]
        or native_validation.get("blackboardChildNative", {}).get("status") != "validated"
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
    tag = reader.nested_union_tag((contract["unionTag"],), "damage-processor")
    if tag != contract["unionTag"] or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.processor:selected-nonnull-wrapper")
    reader.header(contract["memberCount"])
    modifier_start = reader.pos
    if reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.modifier:null")
    reader.header(contract["modifierMemberCount"])
    inner = []
    for member in contract["modifierFieldPlan"]:
        field_start = reader.pos
        if member["kind"] == "enum32":
            raw = reader.take(member["width"], member["name"])
            detail = {"rawHex": raw.hex().upper()}
        else:
            reader.scalar_payload()
            child = blackboard.decode_adding_cooldown(
                data, field_start, reader.pos,
                native_validation=native_validation["blackboardChildNative"],
            )
            if (
                child.get("wholeValueExact") is not True
                or child.get("startOffset") != field_start
                or child.get("consumedEnd") != reader.pos
                or [row["name"] for row in child.get("fields") or []]
                != contract["blackboardChildReadOrder"]
            ):
                raise ValueError(f"{LABEL}.blackboard:child-boundary")
            detail = {"namedChild": child}
        inner.append({
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": member["kind"], "start": field_start, "end": reader.pos,
            **detail,
        })
    modifier_end = reader.pos
    if (
        inner[0]["start"] != modifier_start + 1
        or any(left["end"] != right["start"] for left, right in zip(inner, inner[1:]))
        or inner[-1]["end"] != modifier_end
    ):
        raise ValueError(f"{LABEL}.modifier:field-tiling")
    side_start = reader.pos
    side_raw = reader.take(4, "modifyTargetSide")
    if reader.pos != end:
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    fields = [{
        "name": contract["fieldPlan"][0]["name"],
        "declaredType": contract["fieldPlan"][0]["declaredType"],
        "kind": contract["fieldPlan"][0]["kind"],
        "start": modifier_start, "end": modifier_end,
        "namedChild": {
            "status": "named-direct-members-exact-span", "start": modifier_start,
            "end": modifier_end, "memberCount": len(inner), "namedFields": inner,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        },
    }, {
        "name": contract["fieldPlan"][1]["name"],
        "declaredType": contract["fieldPlan"][1]["declaredType"],
        "kind": contract["fieldPlan"][1]["kind"],
        "start": side_start, "end": reader.pos, "rawHex": side_raw.hex().upper(),
    }]
    return {
        "schema": SCHEMA, "status": "named-direct-members-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "unionTag": tag,
        "wrapperType": contract["wrapperType"],
        "namedFields": fields,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join current VFS identity to exact sole tag-nine processor spans."""
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
        processors = fields[1].get("processors") or []
        if len(processors) != 1 or processors[0].get("tag") != native["unionTag"]:
            continue
        processor = processors[0]
        decoded = decode_instant_modify_attribute_processor_span(
            data, source=source, logical_sha256=digest,
            start=processor["start"], end=processor["end"],
            native_validation=native,
        )
        condition_tags = fields[0].get("actionTags") or []
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionTags": condition_tags, "processorReceipt": decoded,
            "projectedRootWithSelectedCondition": condition_tags == [60],
        })
    return {
        "schema": "endfield.buff-damage-instant-modify-attribute-processor-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "selectedProcessorExact": len(rows),
            "projectedRootWithSelectedCondition": sum(
                row["projectedRootWithSelectedCondition"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS-verified logical bytes rejoin the selected tag-nine "
            "processor child. Root projection is not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_instant_modify_attribute_processor_span",
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
