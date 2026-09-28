"""Native-gated tag-six DamageTextProcessor child and selected [5,6] list join.

It checks the selected native tag-six two-member route and replays ordered
tag-five/tag-six processor lists against current VFS logical hashes.
``memorypack.buff_corpus`` admits the pair with an empty condition through
all 30 root fields, source ID and EOF.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_text_processor_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_scale_processor_child_receipt as scale


LABEL = "buffDamageTextProcessorChild"
SCHEMA = "endfield.buff-damage-text-processor-child-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-text-processor-child-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_text_processor_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    plan = contract.get("fieldPlan")
    setters = contract.get("setterMethods")
    calls = contract.get("sourceCalls")
    if (
        contract.get("reviewedDependencies") != [
            "buff_damage_lists_native.json", "buff_damage_modifier_child_native.json",
        ]
        or contract.get("unionTag") != 6
        or contract.get("serializedMemberCount") != 2
        or contract.get("sourceReadOrderRef") != "anonymousReadOrder.processor6"
        or not isinstance(contract.get("sourceReadOrder"), list)
        or len(contract["sourceReadOrder"]) != 4
        or not isinstance(plan, list) or len(plan) != 2
        or [row.get("kind") for row in plan] != ["enum32", "bool-byte"]
        or [row.get("width") for row in plan] != [4, 1]
        or not isinstance(setters, list) or len(setters) != 2
        or [row[1:3] for row in setters]
        != [[f"set___{member['name']}__", member["declaredType"]] for member in plan]
        or not isinstance(calls, list) or len(calls) != 5
        or [row.get("role") for row in calls]
        != ["header", "damageTextStyleSource", "damageTextStyleSetter",
            "useHpChangeAsDisplayValueSource", "useHpChangeAsDisplayValueSetter"]
        or contract.get("headerCompare", [None, None])[1] != "4080FF02"
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(
    *, modifier_native: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check selected route and both direct source-to-setter assignments."""
    if modifier_native is None:
        modifier_native = modifier.validate_current_native_contract()
    if modifier_native.get("status") != "validated":
        return {"status": modifier_native.get("status", "missing"),
                "detail": "damage-modifier parent is not validated"}
    contract = _contract()
    expected = contract["nativeInputs"]
    base = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes())
    parent = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][1]).read_bytes())
    if (
        base.get("schemaVersion") != 1
        or base.get("anonymousReadOrder", {}).get("processor6")
        != contract["sourceReadOrder"]
        or parent.get("schema")
        != "endfield.buff-damage-modifier-child-native-contract.v1"
        or parent.get("nativeInputs") != expected
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
    wrapper = contract["wrapperType"]
    methods = [row for row in base["methods"]
               if row[1] == wrapper or row[1].startswith(wrapper + "+")]
    dispatcher = [row for row in base["methods"]
                  if row[1].endswith("DamageProcessorBaseForMemoryPackFormatter")]
    windows = [row for row in base["codeWindows"]
               if row["boundary"].startswith("tag6 ")
               or row["boundary"].startswith("dispatcher tag6 ")]
    data_windows = [row for row in base["dataWindows"]
                    if row["boundary"].startswith("union tag 6 table entry routes")]
    source_windows = [row for row in windows if row["boundary"].startswith("tag6 header2 ")]
    if (
        len(methods) != 2 or len(dispatcher) != 1
        or len(windows) != 3 or len(data_windows) != 1 or len(source_windows) != 1
        or methods[0][1] != wrapper + "+" + wrapper.rsplit(".", 1)[-1] + "Formatter"
        or methods[1][1] != wrapper
    ):
        raise ValueError(f"{LABEL}.contract:selected-route")
    for row in dispatcher + methods:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(windows, label=LABEL)
    image.check_windows(data_windows, gate="union-data-window", label=LABEL)
    source_window = source_windows[0]
    start, end = source_window["startRva"], source_window["endRva"]
    compare = contract["headerCompare"]
    if not start <= compare[0] < end:
        raise ValueError(f"{LABEL}.contract:header-window")
    image.check_instruction_windows([compare], label=LABEL)
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == wrapper]
    setters = contract["setterMethods"]
    if (
        len(owners) != 1
        or image.setter_methods(owners[0], parameter="typeName", label=LABEL)
        != [row[:3] for row in setters]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-setters")
    for row in setters:
        image.validate_method_row([row[0], wrapper, row[1], row[3]], label=LABEL)
    calls = contract["sourceCalls"]
    positions = [calls[0]["instructionRva"], compare[0]]
    positions += [row["instructionRva"] for row in calls[1:]]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError(f"{LABEL}.contract:source-call-order")
    for row in calls:
        rva = row["instructionRva"]
        raw = bytes.fromhex(row["rawHex"])
        if (
            not start <= rva < end or len(raw) != 5 or raw[0] != 0xE8
            or image.pe.bytes_at_va(image.pe.image_base + rva, 5) != raw
            or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["targetRva"]
        ):
            raise ValueError(f"{LABEL}.native:source-call={row['role']}")
    if [calls[index]["targetRva"] for index in (2, 4)] != [row[3] for row in setters]:
        raise ValueError(f"{LABEL}.native:setter-call-targets")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"], "wrapperType": wrapper,
        "fieldPlan": contract["fieldPlan"],
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_damage_text_processor_span(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name both direct fields and preserve their stored bits."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("unionTag") != contract["unionTag"]
        or native_validation.get("wrapperType") != contract["wrapperType"]
        or native_validation.get("fieldPlan") != contract["fieldPlan"]
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
        raw = reader.take(member["width"], member["name"])
        fields.append({
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": member["kind"], "start": field_start, "end": reader.pos,
            "rawHex": raw.hex().upper(),
            "storedInt32": struct.unpack("<i", raw)[0] if member["kind"] == "enum32" else None,
            "storedByte": raw[0] if member["kind"] == "bool-byte" else None,
        })
    if reader.pos != end or fields[-1]["end"] != end:
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "named-direct-members-exact-span",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "unionTag": tag,
        "wrapperType": native_validation["wrapperType"],
        "namedFields": fields,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Replay the reached exact [5,6] processor pair without root promotion."""
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
    scale_native = scale.validate_current_native_contract(modifier_native=modifier_native)
    if native.get("status") != "validated" or scale_native.get("status") != "validated":
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
            native_validation=modifier_native, processor_native_validation=scale_native,
        )
        if parent.get("count") != 1 or len(parent.get("elements", [])) != 1:
            continue
        fields = parent["elements"][0]["fields"]
        processors = fields[1]["processors"]
        if [item["tag"] for item in processors] != [5, 6]:
            continue
        first = processors[0].get("namedChild") or {}
        second = decode_damage_text_processor_span(
            data, source=source, logical_sha256=digest,
            start=processors[1]["start"], end=processors[1]["end"],
            native_validation=native,
        )
        if (
            fields[1].get("count") != 2
            or processors[0]["start"] != fields[1]["start"] + 4
            or processors[0]["end"] != processors[1]["start"]
            or processors[1]["end"] != fields[1]["end"]
            or first.get("status") != "named-direct-members-exact-span"
            or first.get("wholeStoredSpanExact") is not True
            or first.get("start") != processors[0]["start"]
            or first.get("end") != processors[0]["end"]
            or second.get("wholeStoredSpanExact") is not True
        ):
            raise ValueError(f"{LABEL}.processor-list:tiling:{source}")
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionTags": fields[0]["actionTags"],
            "processorListStart": fields[1]["start"],
            "processorListEnd": fields[1]["end"],
            "processorChildren": [first, second],
            "projectedRootWithSelectedCondition": fields[0]["actionTags"] == [],
        })
    return {
        "schema": "endfield.buff-damage-text-processor-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native, "scaleNativeValidation": scale_native,
        "summary": {
            "selectedProcessorPairExact": len(rows),
            "projectedRootWithSelectedCondition": sum(
                row["projectedRootWithSelectedCondition"] for row in rows
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS identity and logical bytes rejoin selected two-processor "
            "list spans. Root projection is a rank, not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_damage_text_processor_span",
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
