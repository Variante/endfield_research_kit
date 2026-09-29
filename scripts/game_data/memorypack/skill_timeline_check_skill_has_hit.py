"""Isolate a selected CheckSkillHasHit action in one SkillData source.

The reviewed native contract proves its AbilityActionData dispatcher route,
formatter/reader bodies, four ordered reads and member count. This decoder
reports stored byte spans and raw values. It cannot show that a hit occurred,
that a server action ran, or that this authored branch executed.

The CLI reads only a source whose bytes match a current sparse SkillData
report. It leaves the family corpus and its parser provenance untouched.
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
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes
from scripts.game_data.memorypack.skill_corpus import verify_current_report_inputs
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_partial_output


LABEL = "skillTimelineCheckSkillHasHit"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_check_skill_has_hit_native.json"
SCHEMA = "endfield.skillTimelineCheckSkillHasHitIsolation.v1"
STOP = re.compile(
    r"offset=(?P<offset>\d+) expected='supported current union tag' actual=(?P<tag>\d+)"
)
READ_KINDS = ("bool-byte", "enum32", "scalar32", "scalar32")


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-check-skill-has-hit-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    reads = contract.get("orderedSourceReads")
    if (
        contract.get("serializedMemberCount") != 4
        or not isinstance(reads, list) or len(reads) != 4
        or [row.get("memberIndex") for row in reads] != list(range(4))
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or contract.get("primitiveReadContract")
        != "skill_timeline_check_hit_collider_options_native.json"
        or len(contract.get("methods", [])) != 2
        or len(contract.get("codeWindows", [])) != 2
    ):
        raise ValueError(f"{LABEL}.contract:read-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Recheck the selected native files and every recorded route/read window."""
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
    reads = contract["orderedSourceReads"]
    if (primitive.get("nativeInputs") != expected
            or [(row["fieldName"], row["readKind"], row["sourceTargetRva"])
                for row in reads]
            != [(row["fieldName"], row["readKind"], row["sourceTargetRva"])
                for row in primitive["orderedSourceReads"][:4]]
            or contract["dispatcher"]["switchTableRva"]
            != primitive["dispatcher"]["switchTableRva"]):
        raise ValueError(f"{LABEL}.native:primitive-source-join")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    for row in contract["methods"]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)
    image.check_windows(primitive["codeWindows"], label=LABEL)
    instruction = contract["memberCountInstruction"]
    image.check_instruction_windows([[instruction["rva"], instruction["hex"]]], label=LABEL)
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
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    tag = contract["dispatcher"]["unionTag"]
    selected = routes.get(tag, {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or selected.get("status") != "determined"
        or selected.get("evidenceTier") != "direct"
        or selected.get("wrapperName") != contract["dispatcher"]["wrapperName"]
        or definition != contract["dispatcher"]["wrapperTypeDefinition"]
        or not isinstance(plan, tuple) or len(plan) != 4
        or [(member.name, member.width, member.scalar) for member in plan]
        != [(row["fieldName"], 1 if row["readKind"] == "bool-byte" else 4,
             "bool" if row["readKind"] == "bool-byte" else "scalar32")
            for row in reads]
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "nativeInputs": expected,
            "unionTag": tag, "sourceReads": len(reads),
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    """Consume the one nonnull action at an exact source cursor."""
    contract = _contract()
    tag = contract["dispatcher"]["unionTag"]
    if validation.get("status") != "validated" or validation.get("unionTag") != tag:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    if data[offset] != tag or data[offset + 1] != contract["serializedMemberCount"]:
        raise ValueError(f"{LABEL}.source:tag-or-member-count")
    cursor = offset + 2
    fields = []
    for row in contract["orderedSourceReads"]:
        width = 1 if row["readKind"] == "bool-byte" else 4
        if cursor + width > len(data):
            raise ValueError(f"{LABEL}.source:truncated-member:{row['fieldName']}")
        fields.append({"name": row["fieldName"], "kind": row["readKind"],
                       "start": cursor, "end": cursor + width,
                       "rawHex": data[cursor:cursor + width].hex().upper()})
        cursor += width
    return {"status": "exact-stored-action-span", "start": offset,
            "end": cursor, "tag": tag, "typeName": contract["dispatcher"]["wrapperName"],
            "fields": fields, "evidenceBoundary": "stored framing only"}


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
        gameassembly=paths["gameassembly.dll"],
        metadata=paths["global-metadata.dat"],
    )
    action = decode_action(data, int(match["offset"]), validation=native)
    return {"schema": SCHEMA, "status": "diagnostic-only",
            "publicationEligible": False,
            "virtualPath": virtual_path,
            "inputSetSha256": report["inputSetSha256"],
            "provenance": {"source": _fingerprint(source),
                           "corpusReport": _fingerprint(report_path),
                           "nativeContract": _fingerprint(CONTRACT_PATH)},
            "nativeValidation": native, "action": action,
            "evidenceBoundary": (
                "The exact current copied source reaches this selected native "
                "reader at its recorded first unsupported action tag. The four "
                "stored fields close at the reported action cursor. The later "
                "sequence and whole SkillData file remain unverified."
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
                      "action": result["action"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
