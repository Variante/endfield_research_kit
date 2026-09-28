"""Strict, bounded cohort receipt for simple BuffData damage modifiers.

This is intentionally a child receipt.  It does not promote the BuffData
root: callers must still authenticate the other twenty-nine root members and
the physical EOF.  The accepted cohort has one DamageModifier.Data, an empty
SequenceActionData condition, one tag-five DamageScaleProcessor, and the
four-byte enableSide tail.  Every decision is tied to the current corpus
report and logical source hash.
"""
from __future__ import annotations

import json
import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.buff_damage_modifier_receipt import (
    decode_damage_modifier_collection,
    validate_current_native_contract as validate_damage_native,
)
from scripts.game_data.memorypack.buff_damage_scale_processor_child_receipt import (
    validate_current_native_contract as validate_processor_native,
)


LABEL = "buffDamageFrontier"
SCHEMA = "endfield.buff-damage-frontier-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_frontier_native.json"


def _contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "endfield.buff-damage-frontier-native-contract.v2":
        raise ValueError(f"{LABEL}.contract:schema")
    if value.get("status") != "derived-current-build":
        raise ValueError(f"{LABEL}.contract:status")
    if value.get("unionTag") != 5 or value.get("conditionActionUnionCount") != 0:
        raise ValueError(f"{LABEL}.contract:cohort")
    if value.get("reviewedDependencies") != [
        "buff_damage_modifier_child_native.json",
        "buff_damage_scale_processor_child_native.json",
    ]:
        raise ValueError(f"{LABEL}.contract:dependencies")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck the selected-build parent and tag-five native routes."""
    contract = _contract()
    parent = validate_damage_native()
    if parent.get("status") != "validated":
        return {"status": parent.get("status", "failed"), "parent": parent}
    processor = validate_processor_native(modifier_native=parent)
    if processor.get("status") != "validated":
        return {"status": processor.get("status", "failed"),
                "parent": parent, "processor": processor}
    if processor.get("unionTag") != contract["unionTag"]:
        raise ValueError(f"{LABEL}.native:union-tag")
    # Authenticate the concrete generic provider at the DamageModifier
    # condition callsite.  The broad SkillData sequence contract is a
    # different caller and cannot be reused for this join.
    provider = contract["conditionProvider"]
    parent_contract = json.loads((CONTRACTS_DIR / "buff_damage_modifier_child_native.json").read_bytes())
    if contract.get("nativeInputs") != parent_contract.get("nativeInputs"):
        raise ValueError(f"{LABEL}.contract:native-inputs-drift")
    gate = check_installed_native_inputs(
        contract["nativeInputs"]["GameAssembly.dll"],
        contract["nativeInputs"]["global-metadata.dat"],
    )
    if gate.status != "validated":
        return {"status": gate.status, "parent": parent, "processor": processor}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity),
                "parent": parent, "processor": processor}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != contract["nativeInputs"]["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs",
                "parent": parent, "processor": processor}
    image = open_native_image(gate.gameassembly, gate.metadata)
    rva = provider["instructionRva"]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 7)
    if raw.hex().upper() != provider["instructionHex"]:
        raise ValueError(f"{LABEL}.native:condition-source-instruction")
    cell = image.pe.image_base + rva + 7 + struct.unpack_from("<i", raw, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(image.gameassembly), offset=cell,
    )
    if index != provider["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:condition-method-spec-index")
    spec = struct.unpack(
        "<iii", image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12
        )
    )
    if list(spec) != provider["methodSpec"]:
        raise ValueError(f"{LABEL}.native:condition-method-spec")
    inst = image.instantiations.resolve(spec[2])
    if (len(inst.arguments) != 1
            or inst.arguments[0].raw_type_record_hex != provider["argumentRawHex"]):
        raise ValueError(f"{LABEL}.native:condition-provider-argument")
    type_definition = struct.unpack_from(
        "<I", bytes.fromhex(provider["argumentRawHex"])
    )[0]
    if image.type_name(type_definition) != provider["typeName"]:
        raise ValueError(f"{LABEL}.native:condition-provider-type")
    return {
        "status": "validated",
        "parent": parent,
        "processor": processor,
        "conditionProvider": provider,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _accepted_candidate(row: dict[str, Any]) -> dict[str, Any]:
    candidates = [c for c in row.get("candidates", [])
                  if c.get("readerAcceptedThroughEof") is True]
    if len(candidates) != 1:
        raise ValueError(f"{LABEL}.candidate-count:{len(candidates)}")
    return candidates[0]


def _is_clean_root(candidate: dict[str, Any]) -> bool:
    receipt = candidate.get("namedSchemaReceipt") or {}
    blockers = receipt.get("blockers") or []
    if len(blockers) != 2:
        return False
    damage, root = blockers
    return (
        damage.get("field") == "damageModifier"
        and damage.get("category") == "positive-modifier-recursive-proof"
        and type(damage.get("start")) is int
        and type(damage.get("end")) is int
        and damage["start"] < damage["end"]
        and root == {
            "field": "root",
            "category": "recursive-name-authentication-incomplete",
            "start": None,
            "end": None,
        }
    )


def audit_report(
    report_path: Path, child_receipt_path: Path, *,
    expected_input_set_sha256: str,
    native_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit the bounded 0-condition/tag-five cohort without a corpus sweep."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    child = json.loads(child_receipt_path.read_text(encoding="utf-8"))
    expected = expected_input_set_sha256.upper()
    if report.get("status") != "complete" or report.get("inputSetSha256") != expected:
        raise ValueError(f"{LABEL}.report:input-set")
    if child.get("inputSetSha256") != expected:
        raise ValueError(f"{LABEL}.child-report:input-set")
    if native_validation is None:
        native_validation = validate_current_native_contract()
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")

    child_rows = {row["source"]: row for row in child.get("rows", [])}
    accepted = []
    for row in report.get("files", []):
        source = row.get("identity", {}).get("fileName")
        if source not in child_rows:
            continue
        candidate = _accepted_candidate(row)
        if not _is_clean_root(candidate):
            continue
        receipt = child_rows[source].get("receipt") or {}
        if receipt.get("conditionActionUnionCount") != 0:
            continue
        elements = receipt.get("elements") or []
        if receipt.get("count") != 1 or len(elements) != 1:
            continue
        element = elements[0]
        fields = element.get("fields") or []
        if element.get("status") != "named-direct-child-spans":
            continue
        if [field.get("name") for field in fields] != [
            "condition", "damageProcessors", "enableSide"
        ]:
            continue
        if (fields[0].get("actionUnionCount") != 0
                or fields[1].get("count") != 1
                or fields[2].get("end", 0) - fields[2].get("start", 0) != 4):
            continue
        blocker = (candidate.get("namedSchemaReceipt") or {}).get("blockers", [])[0]
        if [blocker.get("start"), blocker.get("end")] != [
            receipt.get("startOffset"), receipt.get("consumedEnd")
        ]:
            raise ValueError(f"{LABEL}.span-blocker:{source}")
        processors = [p for element in receipt.get("elements", [])
                      for field in element.get("fields", [])
                      if field.get("name") == "damageProcessors"
                      for p in field.get("processors", [])]
        if (len(processors) != 1 or processors[0].get("tag") != 5
                or processors[0].get("namedChild", {}).get("unionTag") != 5
                or processors[0].get("namedChild", {}).get("wholeStoredSpanExact") is not True):
            continue
        logical_sha = row.get("logicalSha256", "").upper()
        if child_rows[source].get("logicalSha256", "").upper() != logical_sha:
            raise ValueError(f"{LABEL}.logical-sha:{source}")
        if not all(element.get("end") > element.get("start")
                   for element in receipt.get("elements", [])):
            raise ValueError(f"{LABEL}.span:{source}")
        accepted.append({
            "source": source,
            "logicalSha256": logical_sha,
            "damageSpan": [receipt["startOffset"], receipt["consumedEnd"]],
            "receipt": receipt,
        })
    return {
        "schema": SCHEMA,
        "status": "complete",
        "publicationEligible": False,
        "inputSetSha256": expected,
        "nativeValidation": native_validation,
        "summary": {"files": len(accepted),
                    "expectedCleanCohort": 21,
                    "conditionActionUnionCount": 0,
                    "processorTags": [5]},
        "rows": accepted,
        "evidenceBoundary": (
            "Selected current-build parent and tag-five processor ownership, "
            "zero-action condition framing, bounded nested stored spans, and "
            "logical source hashes. This receipt does not prove runtime effect, "
            "generic-provider selection, or whole BuffData EOF ownership."
        ),
    }


__all__ = ["audit_report", "validate_current_native_contract"]
