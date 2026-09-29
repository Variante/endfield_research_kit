"""Isolate the selected DiceFloat action in current SkillData sources.

This reader names seven stored members and preserves the two nested
BlackboardDouble payloads as authored values. It does not establish a live
random roll, branch execution, or runtime target behavior. The CLI accepts
only current VFS-authenticated sparse source rows and writes a diagnostic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import (
    _fingerprint, _guard_partial_output, verify_current_report_inputs,
)
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineDiceFloat"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_dice_float_native.json"
SCHEMA = "endfield.skillTimelineDiceFloatIsolation.v1"
STOP = re.compile(
    r"offset=(?P<offset>\d+) expected='supported current union tag' actual=(?P<tag>\d+)"
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "byte-payload",
    "blackboard-double", "blackboard-double",
)
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "key", "max", "min",
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-dice-float-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    reads = contract.get("orderedSourceReads")
    if (
        contract.get("serializedMemberCount") != 7
        or not isinstance(reads, list) or len(reads) != 7
        or [row.get("memberIndex") for row in reads] != list(range(7))
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or contract.get("primitiveReadContract")
        != "skill_timeline_check_hit_collider_options_native.json"
        or contract.get("bytePayloadReadContract") != "buff_10c_native.json"
        or contract.get("blackboardReadContract") != "buff_ec_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
        or [row.get("memberIndex") for row in contract.get("nestedContexts", [])]
        != [5, 6]
    ):
        raise ValueError(f"{LABEL}.contract:read-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Recheck selected native inputs, route, complete reader and child contexts."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll-missing-or-mismatched")
    primitive, _ = read_reviewed_contract(
        CONTRACTS_DIR / contract["primitiveReadContract"],
        schema="endfield.skill-timeline-check-hit-collider-options-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    byte_reader = json.loads((CONTRACTS_DIR / contract["bytePayloadReadContract"]).read_bytes())
    double_reader = json.loads((CONTRACTS_DIR / contract["blackboardReadContract"]).read_bytes())
    reads = contract["orderedSourceReads"]
    byte_window = next((row for row in byte_reader.get("codeWindows", [])
                        if row.get("startRva") == reads[4]["sourceTargetRva"]), None)
    double_methods = [row for row in double_reader.get("methods", [])
                      if "Beyond_Blackboard_BlackboardDoubleForMemoryPack" in row[1]
                      and row[2] == "Deserialize"]
    double_windows = [row for row in double_reader.get("codeWindows", [])
                      if any(row.get("startRva") == method[3] for method in double_methods)]
    if (
        expected != primitive.get("nativeInputs")
        or contract["dispatcher"]["switchTableRva"] != primitive["dispatcher"]["switchTableRva"]
        or [row["sourceTargetRva"] for row in reads[:4]]
        != [row["sourceTargetRva"] for row in primitive["orderedSourceReads"][:4]]
        or byte_reader.get("schemaVersion") != 1 or byte_window is None
        or double_reader.get("schemaVersion") != 1 or len(double_methods) != 2
        or len(double_windows) != 2
        or reads[5]["sourceTargetRva"] != reads[6]["sourceTargetRva"]
    ):
        raise ValueError(f"{LABEL}.native:dependency-shape")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    for row in contract["methods"] + double_methods:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_windows(primitive["codeWindows"], label=LABEL)
    image.check_windows([byte_window] + double_windows, label=LABEL)
    count = contract["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    start, end = (contract["codeWindows"][1][key] for key in ("startRva", "endRva"))
    previous = -1
    for row in reads:
        rva = row["sourceCallsiteRva"]
        if not start <= rva < end - 4 or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != row["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call:{rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target:{rva:#x}")
    for context in contract["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
        )
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        instance = image.instantiations.resolve(spec[2])
        if (
            index != context["methodSpecIndex"] or list(spec) != context["methodSpec"]
            or len(instance.arguments) != 1
            or instance.arguments[0].raw_type_record_hex.upper() != context["argumentRawHex"]
            or struct.unpack_from("<Q", bytes.fromhex(context["argumentRawHex"]))[0]
            != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
            or context["typeName"] != "Beyond.Blackboard+BlackboardDouble"
        ):
            raise ValueError(f"{LABEL}.native:nested-context:{context['memberIndex']}")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    tag = contract["dispatcher"]["unionTag"]
    selected = routes.get(tag, {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or selected.get("status") != "determined" or selected.get("evidenceTier") != "direct"
        or selected.get("wrapperName") != contract["dispatcher"]["wrapperName"]
        or definition != contract["dispatcher"]["wrapperTypeDefinition"]
        or not isinstance(plan, tuple) or len(plan) != 7
        or [member.name for member in plan] != list(FIELD_NAMES)
        or [(member.width, member.scalar) for member in plan[:4]]
        != [(1, "bool"), (4, "scalar32"), (4, "scalar32"), (4, "scalar32")]
        or plan[4].kind != "string"
        or any(member.kind != "object" or member.ref not in resolver.wrappers
               or resolver.wrappers[member.ref].wrapped_type != "Beyond.Blackboard+BlackboardDouble"
               for member in plan[5:])
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "nativeInputs": expected,
            "unionTag": tag, "sourceReads": len(reads),
            "evidenceBoundary": contract["evidenceBoundary"]}


def _consume_action(reader: Reader) -> dict[str, Any]:
    """Consume only the selected nonnull wrapper; the caller owns native gating."""
    contract = _contract()
    tag = contract["dispatcher"]["unionTag"]
    offset = reader.pos
    data = reader.data
    if reader.peek() != tag:
        raise ValueError(f"{LABEL}.source:tag")
    reader.take(1, "selected-union-tag")
    reader.header(contract["serializedMemberCount"])
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        start = reader.pos
        if kind == "bool-byte":
            reader.take(1, name)
        elif kind in ("enum32", "scalar32"):
            reader.take(4, name)
        elif kind == "byte-payload":
            reader.byte_payload()
        elif kind == "blackboard-double":
            reader.scalar_payload()
        else:
            raise AssertionError(kind)
        fields.append({"name": name, "kind": kind, "start": start,
                       "end": reader.pos, "rawHex": data[start:reader.pos].hex().upper()})
    return {"status": "exact-stored-action-span", "start": offset,
            "end": reader.pos, "tag": tag,
            "typeName": contract["dispatcher"]["wrapperName"],
            "fields": fields, "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    """Consume one selected action after explicit current-native validation."""
    tag = _contract()["dispatcher"]["unionTag"]
    if validation.get("status") != "validated" or validation.get("unionTag") != tag:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Read a shared-parser action after its composite native gate validates."""
    del depth
    if tag != _contract()["dispatcher"]["unionTag"] or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader)


def inspect_source(source: Path, report_path: Path, virtual_path: str) -> dict[str, Any]:
    report = json.loads(report_path.read_bytes())
    verify_current_report_inputs(report, allow_partial=True)
    if report.get("status") != "partial" or report.get("publicationEligible") is not False:
        raise ValueError(f"{LABEL}.report:not-scoped")
    rows = [row for row in report.get("files", [])
            if row.get("virtualPath") == virtual_path]
    if len(rows) != 1 or virtual_path not in report.get("targetedVirtualPaths", []):
        raise ValueError(f"{LABEL}.report:source-not-in-scope")
    row = rows[0]
    data = source.read_bytes()
    if (len(data), hashlib.md5(data).hexdigest().upper(),
            hashlib.sha256(data).hexdigest().upper()) != (
            row.get("length"), row.get("logicalMd5"), row.get("logicalSha256")):
        raise ValueError(f"{LABEL}.source:current-logical-bytes-differ")
    reason = row.get("timelineSharedSequenceStopReason")
    match = STOP.search(reason) if isinstance(reason, str) else None
    contract = _contract()
    if match is None or int(match["tag"]) != contract["dispatcher"]["unionTag"]:
        raise ValueError(f"{LABEL}.report:first-stop-is-not-selected-route")
    paths = {Path(item["path"]).name.casefold(): Path(item["path"])
             for item in report["provenance"]["buildFingerprints"]}
    if set(("gameassembly.dll", "global-metadata.dat")) - set(paths):
        raise ValueError(f"{LABEL}.report:selected-native-paths-missing")
    native = validate_current_native_contract(
        gameassembly=paths["gameassembly.dll"], metadata=paths["global-metadata.dat"],
    )
    action = decode_action(data, int(match["offset"]), validation=native)
    return {"schema": SCHEMA, "status": "diagnostic-only",
            "publicationEligible": False, "virtualPath": virtual_path,
            "inputSetSha256": report["inputSetSha256"],
            "provenance": {"source": _fingerprint(source),
                           "corpusReport": _fingerprint(report_path),
                           "nativeContract": _fingerprint(CONTRACT_PATH),
                           "primitiveReadContract": _fingerprint(
                               CONTRACTS_DIR / contract["primitiveReadContract"]),
                           "bytePayloadReadContract": _fingerprint(
                               CONTRACTS_DIR / contract["bytePayloadReadContract"]),
                           "blackboardReadContract": _fingerprint(
                               CONTRACTS_DIR / contract["blackboardReadContract"])},
            "nativeValidation": native, "action": action,
            "evidenceBoundary": (
                "The exact current source reaches this selected native action "
                "reader at its recorded first unsupported tag. Seven stored "
                "members close at the action cursor; later actions and the "
                "whole SkillData file require separate continuation."
            )}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--corpus-report", type=Path, required=True)
    parser.add_argument("--virtual-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    _guard_partial_output(args.output)
    if args.output.resolve() in {args.source.resolve(), args.corpus_report.resolve(), CONTRACT_PATH.resolve()}:
        parser.error("output overlaps evidence input")
    try:
        result = inspect_source(args.source, args.corpus_report, args.virtual_path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"{LABEL} isolation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"],
                      "action": {key: result["action"][key] for key in ("start", "end", "tag")},
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
