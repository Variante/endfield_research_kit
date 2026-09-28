"""Native-gated one-BlackboardDouble damage processor children (tags 0, 2, 3 and 4).

It checks the selected native one-member routes and their exact
BlackboardDouble child spans, joined to current VFS logical hashes. The
reader admits tags 0, 2, 3 and 4; this audit reports sole tag-0, tag-2 and
tag-3 processors. ``memorypack.buff_corpus`` admits tag two with one
``CheckDamageDecorateMask`` action, tags zero or three with that action or a
simple ``CheckTagMatch``, and tag four only with the
NotNextCheckAction/main-character condition, proving all 30 root fields
through source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_scalar_processor_current_latest.json``.
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


LABEL = "buffDamageScalarProcessorChild"
SCHEMA = "endfield.buff-damage-scalar-processor-child-receipt.v3"
NATIVE_SCHEMA = "endfield.buff-damage-scalar-processor-child-native-contract.v3"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_scalar_processor_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    if contract.get("reviewedDependencies") != [
        "buff_damage_lists_native.json", "buff_damage_modifier_child_native.json",
        "buff_adding_cooldown_ownership_native.json",
    ]:
        raise ValueError(f"{LABEL}.contract:dependencies")
    if contract.get("blackboardChildReadOrder") != [
        "blackboardKey", "useBlackboardKey", "value"
    ]:
        raise ValueError(f"{LABEL}.contract:blackboard-order")
    routes = contract.get("routes")
    if not isinstance(routes, list) or [row.get("unionTag") for row in routes] != [0, 2, 3, 4]:
        raise ValueError(f"{LABEL}.contract:routes")
    for route in routes:
        plan = route.get("fieldPlan")
        calls = route.get("sourceCalls")
        if (
            not isinstance(route.get("wrapperType"), str)
            or route.get("serializedMemberCount") != 1
            or route.get("sourceReadOrderRef")
            != f"anonymousReadOrder.processor{route['unionTag']}"
            or not isinstance(route.get("sourceReadOrder"), list)
            or len(route["sourceReadOrder"]) != 3
            or not isinstance(plan, list) or len(plan) != 1
            or plan[0].get("kind") != "blackboard-double"
            or plan[0].get("declaredType") != "Beyond.Blackboard+BlackboardDouble"
            or not isinstance(plan[0].get("name"), str)
            or route.get("setterMethod", [None, None, None])[1:3]
            != [f"set___{plan[0]['name']}__", plan[0]["declaredType"]]
            or not isinstance(calls, list) or len(calls) != 3
            or [row.get("role") for row in calls]
            != ["header", f"{plan[0]['name']}Source", f"{plan[0]['name']}Setter"]
            or route.get("headerCompare", [None, None])[1] != "4080FF01"
        ):
            raise ValueError(f"{LABEL}.contract:route-shape")
    return contract


def validate_current_native_contract(
    *, modifier_native: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check selected union routes, direct setter slots and generic child contexts."""
    if modifier_native is None:
        modifier_native = modifier.validate_current_native_contract()
    if modifier_native.get("status") != "validated":
        return {"status": modifier_native.get("status", "missing"),
                "detail": "damage-modifier parent is not validated"}
    contract = _contract()
    expected = contract["nativeInputs"]
    base = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes())
    parent = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][1]).read_bytes())
    blackboard_contract = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][2]).read_bytes()
    )
    if (
        base.get("schemaVersion") != 1
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
    native_routes = []
    for route in contract["routes"]:
        tag = route["unionTag"]
        if base.get("anonymousReadOrder", {}).get(f"processor{tag}") != route["sourceReadOrder"]:
            raise ValueError(f"{LABEL}.contract:source-read-order={tag}")
        wrapper = route["wrapperType"]
        methods = [row for row in base["methods"]
                   if row[1] == wrapper or row[1].startswith(wrapper + "+")]
        windows = [row for row in base["codeWindows"]
                   if row["boundary"].startswith(f"tag{tag} formatter")
                   or row["boundary"].startswith(f"tag{tag} header1 ")]
        data_windows = [row for row in base["dataWindows"]
                        if row["boundary"].startswith(f"union tag {tag} table entry routes")]
        source_windows = [row for row in windows if row["boundary"].startswith(f"tag{tag} header1 ")]
        if (
            len(methods) != 2 or len(windows) != 2 or len(data_windows) != 1
            or len(source_windows) != 1
            or methods[0][1] != wrapper + "+" + wrapper.rsplit(".", 1)[-1] + "Formatter"
            or methods[1][1] != wrapper
        ):
            raise ValueError(f"{LABEL}.contract:selected-route={tag}")
        for row in methods:
            image.validate_method_row(row, label=LABEL)
        image.check_windows(windows, label=LABEL)
        image.check_windows(data_windows, gate="union-data-window", label=LABEL)
        source_window = source_windows[0]
        start, end = source_window["startRva"], source_window["endRva"]
        compare = route["headerCompare"]
        if not start <= compare[0] < end:
            raise ValueError(f"{LABEL}.contract:header-window={tag}")
        image.check_instruction_windows([compare], label=LABEL)
        owners = [row for row in image.metadata.types
                  if image.metadata.type_full_name(row) == wrapper]
        setter = route["setterMethod"]
        if (
            len(owners) != 1
            or image.setter_methods(owners[0], parameter="typeName", label=LABEL)
            != [setter[:3]]
        ):
            raise ValueError(f"{LABEL}.native:wrapper-setter={tag}")
        image.validate_method_row([setter[0], wrapper, setter[1], setter[3]], label=LABEL)
        context_rows = [row for row in base["nestedContexts"]
                        if start <= row["instructionRva"] < end]
        if len(context_rows) != 1 or context_rows[0]["typeName"] != setter[2]:
            raise ValueError(f"{LABEL}.contract:blackboard-context={tag}")
        context = context_rows[0]
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index={tag}")
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
        ):
            raise ValueError(f"{LABEL}.native:method-context={tag}")
        calls = route["sourceCalls"]
        positions = [calls[0]["instructionRva"], compare[0], context["instructionRva"]]
        positions += [row["instructionRva"] for row in calls[1:]]
        if positions != sorted(positions) or len(set(positions)) != len(positions):
            raise ValueError(f"{LABEL}.contract:source-call-order={tag}")
        for row in calls:
            rva = row["instructionRva"]
            raw = bytes.fromhex(row["rawHex"])
            if (
                not start <= rva < end or len(raw) != 5 or raw[0] != 0xE8
                or image.pe.bytes_at_va(image.pe.image_base + rva, 5) != raw
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["targetRva"]
            ):
                raise ValueError(f"{LABEL}.native:source-call={tag}:{row['role']}")
        if calls[-1]["targetRva"] != setter[3]:
            raise ValueError(f"{LABEL}.native:setter-call-target={tag}")
        native_routes.append({
            "unionTag": tag, "wrapperType": wrapper,
            "fieldPlan": route["fieldPlan"],
            "sourceReadOrder": route["sourceReadOrder"],
        })
    if len({route["sourceCalls"][1]["targetRva"] for route in contract["routes"]}) != 1:
        raise ValueError(f"{LABEL}.contract:blackboard-source-target")
    blackboard_native = blackboard_double.validate_current_native_contract()
    if (
        blackboard_native.get("status") != "validated"
        or blackboard_native.get("selectedReadOrder")
        != contract["blackboardChildReadOrder"]
    ):
        raise ValueError(f"{LABEL}.native:blackboard-child")
    return {
        "status": "validated", "nativeInputs": expected,
        "routes": native_routes,
        "blackboardChildNative": blackboard_native,
        "blackboardChildReadOrder": contract["blackboardChildReadOrder"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_scalar_processor_span(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay one selected processor child without promoting its parent root."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("routes") != [
            {"unionTag": route["unionTag"], "wrapperType": route["wrapperType"],
             "fieldPlan": route["fieldPlan"], "sourceReadOrder": route["sourceReadOrder"]}
            for route in contract["routes"]
        ]
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
    tag = reader.nested_union_tag((0, 2, 3, 4), "damage-processor")
    routes = {route["unionTag"]: route for route in native_validation["routes"]}
    if tag not in routes or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.processor:selected-nonnull-wrapper")
    reader.header(1)
    child_start = reader.pos
    reader.scalar_payload()
    child_end = reader.pos
    child = blackboard_double.decode_adding_cooldown(
        data, child_start, child_end,
        native_validation=native_validation["blackboardChildNative"],
    )
    if (
        child.get("wholeValueExact") is not True
        or child.get("startOffset") != child_start
        or child.get("consumedEnd") != child_end
        or (child["fields"] and [row["name"] for row in child["fields"]]
            != native_validation["blackboardChildReadOrder"])
        or reader.pos != end
    ):
        raise ValueError(f"{LABEL}.blackboard-child:boundary")
    route = routes[tag]
    return {
        "schema": SCHEMA, "status": "named-direct-members-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "unionTag": tag,
        "wrapperType": route["wrapperType"],
        "namedFields": [{
            "name": route["fieldPlan"][0]["name"],
            "declaredType": route["fieldPlan"][0]["declaredType"],
            "start": child_start, "end": child_end,
            "namedChild": child, "childBoundary": "named-exact",
        }],
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join current VFS identities to exact selected scalar processor spans."""
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
        if len(processors) != 1 or processors[0].get("tag") not in (0, 2, 3):
            continue
        processor = processors[0]
        decoded = decode_scalar_processor_span(
            data, source=source, logical_sha256=digest,
            start=processor["start"], end=processor["end"],
            native_validation=native,
        )
        condition_tags = fields[0].get("actionTags") or []
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionTags": condition_tags, "processorReceipt": decoded,
            "projectedRootWithSelectedCondition": (
                condition_tags in ([91], [124]) if processor["tag"] in (0, 3)
                else condition_tags == [91]
            ),
        })
    tags = Counter((row["processorReceipt"]["unionTag"], tuple(row["conditionTags"]))
                   for row in rows)
    return {
        "schema": "endfield.buff-damage-scalar-processor-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "selectedProcessorExact": len(rows),
            "processorAndConditionTags": {
                f"{tag}:{','.join(map(str, condition))}": count
                for (tag, condition), count in sorted(tags.items())
            },
            "projectedRootWithSelectedCondition": sum(
                row["projectedRootWithSelectedCondition"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS-verified logical source bytes rejoin selected tag-zero, "
            "tag-two and tag-three processor children. Root projection remains a frontier rank, "
            "not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_scalar_processor_span",
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
