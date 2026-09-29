"""Selected-build SkillData AnimEventReceiver 0x0012 stored reader.

The nested SequenceActionData reuses the independently reviewed sequence
grammar. A closed event receiver is one stored action, not a fired event or
a whole SkillData record.
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


LABEL = "skillTimelineAnimEventReceiver"
TAG = 0x0012
SCHEMA = "endfield.skillTimelineAnimEventReceiverIsolation.v1"
STOP = re.compile(
    r"offset=(?P<offset>\d+) expected='supported current union tag' actual=(?P<tag>\d+)"
)
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_anim_event_receiver_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_AnimEventReceiver_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.AnimEventReceiver+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "actionOnEvent", "blackboardKey", "eventId",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "sequence-action-data",
    "bounded-byte-payload", "bounded-byte-payload",
)
PLAN = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
    ("actionOnEvent", "object", None, None),
    ("blackboardKey", "string", None, None),
    ("eventId", "string", None, None),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.skill-timeline-anim-event-receiver-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("dispatcher", {}).get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(reads)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(setters, list) or len(setters) != 3
        or [row[1] for row in setters] != [
            "set___actionOnEvent__", "set___blackboardKey__", "set___eventId__",
        ]
        or not isinstance(setter_calls, list)
        or [row.get("memberIndex") for row in setter_calls] != [4, 5, 6]
        or [row.get("methodIndex") for row in setter_calls]
        != [row[0] for row in setters]
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 4]
        or [row.get("typeName") for row in contexts] != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Gameplay.Core.SequenceActionData",
        ]
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("sequenceReadContract")
        != "buff_damage_sequence_action_condition_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7C\x24\x38" + bytes([len(FIELD_NAMES)])
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def _selected_dependency_windows(image: Any, contract: Mapping[str, Any]) -> None:
    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    header = contract["memberHeaderSourceCall"]
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"]
               if row["readKind"] != "sequence-action-data"}
    targets.add(header["sourceTargetRva"])
    windows = [row for row in primitive.get("codeWindows", [])
               if row.get("startRva") in targets]
    if (primitive.get("schemaVersion") != 1
            or targets != {row["startRva"] for row in windows}
            or len(windows) != 4):
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image.check_windows(windows, label=LABEL)

    sequence = json.loads((CONTRACTS_DIR / contract["sequenceReadContract"]).read_bytes())
    context = contract["genericContexts"][1]
    provider = sequence.get("conditionProvider", {})
    if (
        sequence.get("schema")
        != "endfield.buff-damage-sequence-action-condition-native-contract.v1"
        or sequence.get("status") != "exact-current-build"
        or sequence.get("nativeInputs") != contract["nativeInputs"]
        or sequence.get("memberCount") != 3
        or sequence.get("terminalByteCount") != 2
        or provider.get("typeName") != context["typeName"]
        or provider.get("methodSpecIndex") != context["methodSpecIndex"]
        or provider.get("methodSpec") != context["methodSpec"]
        or provider.get("argumentRawHex") != context["argumentRawHex"]
        or len(sequence.get("sequenceMethods", [])) != 2
    ):
        raise ValueError(f"{LABEL}.native:sequence-source-drift")
    for method in sequence["sequenceMethods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(sequence["sequenceCodeWindows"], label=LABEL)
    image.check_instruction_windows(sequence["sequenceInstructionWindows"], label=LABEL)


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected dispatch, source read order and nested type."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (not unityplayer.is_file()
            or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
    _selected_dependency_windows(image, contract)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    reader_window = contract["codeWindows"][0]
    header = contract["memberHeaderSourceCall"]
    source_calls = [header, *contract["orderedSourceReads"]]
    previous = -1
    for call in source_calls:
        rva = call["sourceCallsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4 or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        if raw[0] != 0xE8 or raw.hex().upper() != call["sourceCallHex"]:
            raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
        if rva + 5 + struct.unpack_from("<i", raw, 1)[0] != call["sourceTargetRva"]:
            raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    reads = contract["orderedSourceReads"]
    for setter in contract["setterCallsites"]:
        member = setter["memberIndex"]
        rva = setter["callsiteRva"]
        limit = (reads[member + 1]["sourceCallsiteRva"] if member + 1 < len(reads)
                 else reader_window["endRva"])
        if not reads[member]["sourceCallsiteRva"] < rva < limit:
            raise ValueError(f"{LABEL}.native:setter-order={member}")
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
        method = image.metadata.methods[setter["methodIndex"]]
        if (raw[0] != 0xE8 or raw.hex().upper() != setter["callHex"]
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != setter["targetRva"]
                or image.method_pointer_va(method) != image.pe.image_base + setter["targetRva"]):
            raise ValueError(f"{LABEL}.native:setter-call={member}")
    for context in contract["genericContexts"]:
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
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        definition = struct.unpack_from("<Q", argument)[0]
        if (index != context["methodSpecIndex"] or list(spec) != context["methodSpec"]
                or argument.hex().upper() != context["argumentRawHex"]
                or argument[10] != context["typeKind"]
                or definition != context["typeDefinition"]
                or image.type_name(definition) != context["typeName"]):
            raise ValueError(f"{LABEL}.native:generic-type={context['memberIndex']}")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    wrapper = resolver.wrappers.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "structuralOnly"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None or wrapper.wrapped_type != TYPE_NAME
        or not isinstance(plan, tuple)
        or tuple((member.name, member.kind, member.width, member.scalar)
                 for member in plan) != PLAN
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
            "genericContextCount": len(contract["genericContexts"])}


def _consume_action(reader: Reader, depth: int, width: int) -> dict[str, Any]:
    if width != 1 or reader.data[reader.pos:reader.pos + 1] != bytes([TAG]):
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for index, name in enumerate(FIELD_NAMES):
        field_start = reader.pos
        if index == 0:
            reader.take(1, name)
        elif index < 4:
            reader.take(4, name)
        elif index == 4:
            reader.sequence(depth + 1)
        else:
            reader.byte_payload()
        fields.append({"name": name, "kind": READ_KINDS[index],
                       "start": field_start, "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": TAG, "fields": fields,
            "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 0, 1)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, depth, width)


def inspect_source(source: Path, report_path: Path, virtual_path: str) -> dict[str, Any]:
    """Join one current sparse VFS stop to its exact source bytes and native route."""
    report = json.loads(report_path.read_bytes())
    verify_current_report_inputs(report, allow_partial=True)
    if report.get("status") != "partial" or report.get("publicationEligible") is not False:
        raise ValueError(f"{LABEL}.report:not-scoped")
    if report.get("targetedVirtualPaths") != [virtual_path]:
        raise ValueError(f"{LABEL}.report:source-not-exact-scope")
    rows = report.get("files", [])
    if len(rows) != 1 or rows[0].get("virtualPath") != virtual_path:
        raise ValueError(f"{LABEL}.report:source-row-differs")
    row = rows[0]
    data = source.read_bytes()
    if (len(data), hashlib.md5(data).hexdigest().upper(),
            hashlib.sha256(data).hexdigest().upper()) != (
            row.get("length"), row.get("logicalMd5"), row.get("logicalSha256")):
        raise ValueError(f"{LABEL}.source:current-logical-bytes-differ")
    reason = row.get("timelineSharedSequenceStopReason")
    match = STOP.search(reason) if isinstance(reason, str) else None
    if match is None or int(match["tag"]) != TAG:
        raise ValueError(f"{LABEL}.report:first-stop-is-not-selected-route")
    paths = {Path(item["path"]).name.casefold(): Path(item["path"])
             for item in report["provenance"]["buildFingerprints"]}
    if set(("gameassembly.dll", "global-metadata.dat")) - set(paths):
        raise ValueError(f"{LABEL}.report:selected-native-paths-missing")
    native = validate_current_native_contract(
        gameassembly=paths["gameassembly.dll"], metadata=paths["global-metadata.dat"],
    )
    action = decode_action(data, int(match["offset"]), validation=native)
    contract = _contract()
    return {
        "schema": SCHEMA, "status": "diagnostic-only", "publicationEligible": False,
        "virtualPath": virtual_path, "inputSetSha256": report["inputSetSha256"],
        "provenance": {
            "source": _fingerprint(source), "corpusReport": _fingerprint(report_path),
            "nativeContract": _fingerprint(CONTRACT_PATH),
            "primitiveReadContract": _fingerprint(
                CONTRACTS_DIR / contract["primitiveReadContract"]),
            "sequenceReadContract": _fingerprint(
                CONTRACTS_DIR / contract["sequenceReadContract"]),
        },
        "nativeValidation": native, "action": action,
        "evidenceBoundary": (
            "Only the selected source's first unsupported action is isolated. "
            "The selected native reader, nested sequence and two string payloads "
            "close this stored action; later actions and the whole SkillData "
            "record require separate continuation. Runtime event delivery is unobserved."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--corpus-report", type=Path, required=True)
    parser.add_argument("--virtual-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    _guard_partial_output(args.output)
    if args.output.resolve() in {
        args.source.resolve(), args.corpus_report.resolve(), CONTRACT_PATH.resolve(),
    }:
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
                      "action": {key: result["action"][key]
                                 for key in ("start", "end", "tag")},
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
