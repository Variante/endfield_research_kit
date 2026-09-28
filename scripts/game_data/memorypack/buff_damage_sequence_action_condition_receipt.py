"""Selected native and bounded reader for zero-action damage conditions."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.buff_damage_modifier_receipt import validate_current_native_contract as validate_damage_modifier_native

CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_sequence_action_condition_native.json"
SCHEMA = "endfield.buff-damage-sequence-action-condition-receipt.v1"
LABEL = "buffDamageSequenceActionCondition"


def _contract() -> dict[str, Any]:
    value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "endfield.buff-damage-sequence-action-condition-native-contract.v1":
        raise ValueError(f"{LABEL}.contract:schema")
    if value.get("status") != "exact-current-build":
        raise ValueError(f"{LABEL}.contract:status")
    return value


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity)}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    image = open_native_image(gate.gameassembly, gate.metadata)
    provider = contract["conditionProvider"]
    parent = json.loads((CONTRACTS_DIR / "buff_damage_modifier_child_native.json").read_text(encoding="utf-8"))
    if parent.get("nativeInputs") != expected:
        raise ValueError(f"{LABEL}.native:parent-input-drift")
    parent_validation = validate_damage_modifier_native()
    if parent_validation.get("status") != "validated":
        return {"status": parent_validation.get("status", "failed"), "parent": parent_validation}
    image.validate_method_row(contract["sequenceMethods"][0], label=LABEL)
    image.validate_method_row(contract["sequenceMethods"][1], label=LABEL)
    image.check_windows(contract["sequenceCodeWindows"], label=LABEL)
    image.check_instruction_windows(contract["sequenceInstructionWindows"], label=LABEL)
    parent_sites = {
        row[2]: (row[0], row[1]) for row in parent["childSourceInstructions"]
    }
    selected_labels = (
        "condition source context",
        "condition source read",
        "condition setter call",
    )
    selected_sites = [parent_sites[label] for label in selected_labels]
    for rva, expected_hex in selected_sites:
        raw = image.pe.bytes_at_va(
            image.pe.image_base + rva, len(bytes.fromhex(expected_hex))
        )
        if raw.hex().upper() != expected_hex:
            raise ValueError(f"{LABEL}.native:parent-source-window={rva:#x}")
    if not (selected_sites[0][0] < selected_sites[1][0] < selected_sites[2][0]):
        raise ValueError(f"{LABEL}.native:parent-condition-order")
    if provider["instructionRva"] != selected_sites[0][0]:
        raise ValueError(f"{LABEL}.native:provider-parent-context")
    raw = image.pe.bytes_at_va(image.pe.image_base + provider["instructionRva"], 7)
    if raw.hex().upper() != provider["instructionHex"]:
        raise ValueError(f"{LABEL}.native:condition-source-instruction")
    cell = image.pe.image_base + provider["instructionRva"] + 7 + struct.unpack_from("<i", raw, 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=str(image.gameassembly), offset=cell)
    if index != provider["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index")
    spec = list(struct.unpack("<iii", image.pe.bytes_at_va(int(image.registration["methodSpecs"], 16) + index * 12, 12)))
    if spec != provider["methodSpec"]:
        raise ValueError(f"{LABEL}.native:method-spec")
    inst = image.instantiations.resolve(spec[2])
    if len(inst.arguments) != 1 or inst.arguments[0].raw_type_record_hex != provider["argumentRawHex"]:
        raise ValueError(f"{LABEL}.native:provider-argument")
    type_definition = struct.unpack_from("<I", bytes.fromhex(provider["argumentRawHex"]))[0]
    if image.type_name(type_definition) != provider["typeName"]:
        raise ValueError(f"{LABEL}.native:provider-type")
    wrappers = [row for row in image.metadata.types
                if image.metadata.type_full_name(row) == contract["wrapperType"]]
    if len(wrappers) != 1:
        raise ValueError(f"{LABEL}.native:wrapper-type")
    setters = image.setter_methods(wrappers[0], parameter="typeName", label=LABEL)
    if setters != contract["wrapperSetters"]:
        raise ValueError(f"{LABEL}.native:wrapper-setters")
    return {"status": "validated", "provider": provider, "wrapperType": contract["wrapperType"],
            "serializedReadOrder": contract["serializedReadOrder"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_zero_action_condition(data: bytes, *, source: str, start: int, end: int,
                                 logical_sha256: str, native_validation: dict[str, Any]) -> dict[str, Any]:
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper():
        raise ValueError(f"{LABEL}.logical-source-hash")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.range")
    if data[start] == 0xFF:
        if end != start + 1:
            raise ValueError(f"{LABEL}.null-span")
        return {"schema": SCHEMA, "status": "exact-null-sequence", "source": source,
                "start": start, "end": end, "actionCount": None, "terminal": [],
                "wholeStoredSpanExact": True}
    if end - start < 7 or data[start] != 3:
        raise ValueError(f"{LABEL}.header-or-length")
    count = struct.unpack_from("<i", data, start + 1)[0]
    if count != 0:
        raise ValueError(f"{LABEL}.action-count={count}")
    terminal_start = start + 5
    if end != terminal_start + 2:
        raise ValueError(f"{LABEL}.terminal-span")
    return {"schema": SCHEMA, "status": "exact-empty-sequence", "source": source,
            "start": start, "end": end, "actionCount": 0,
            "terminal": list(data[terminal_start:end]), "wholeStoredSpanExact": True}


__all__ = ["decode_zero_action_condition", "validate_current_native_contract"]


def audit_current_child_report(report_path: Path, *, native_validation: dict[str, Any]) -> dict[str, Any]:
    """Replay report-backed condition spans without widening BuffData scope."""
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if report.get("status") != "complete" or report.get("inputSetSha256") is None:
        raise ValueError(f"{LABEL}.report:provenance")
    rows = []
    for row in report.get("rows", []):
        receipt = row.get("receipt") or {}
        if receipt.get("conditionActionUnionCount") != 0:
            continue
        elements = receipt.get("elements") or []
        if len(elements) != 1:
            raise ValueError(f"{LABEL}.report:element-count")
        fields = elements[0].get("fields") or []
        condition = next((field for field in fields if field.get("name") == "condition"), None)
        if condition is None:
            raise ValueError(f"{LABEL}.report:condition-missing")
        source = row.get("source")
        if not isinstance(source, str) or not row.get("logicalSha256"):
            raise ValueError(f"{LABEL}.report:source-hash")
        virtual = PurePosixPath(source)
        if (
            virtual.is_absolute()
            or virtual.parts[:3] != ("Data", "Json", "BuffData")
            or len(virtual.parts) < 4
            or ".." in virtual.parts
        ):
            raise ValueError(f"{LABEL}.report:source-path={source}")
        path = Path("export_full/game/Json/BuffData").joinpath(*virtual.parts[3:])
        if not path.is_file():
            raise ValueError(f"{LABEL}.report:source-missing={source}")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest().upper() != row["logicalSha256"].upper():
            raise ValueError(f"{LABEL}.report:source-hash-mismatch={source}")
        decoded = decode_zero_action_condition(
            data, source=source, start=condition["start"], end=condition["end"],
            logical_sha256=row["logicalSha256"], native_validation=native_validation,
        )
        rows.append(decoded)
    return {"schema": SCHEMA, "status": "complete", "sourceReport": str(report_path),
            "inputSetSha256": report["inputSetSha256"], "summary": {"rows": len(rows)},
            "rows": rows, "evidenceBoundary": (
                "Current child receipt source identities and logical hashes are replayed "
                "at the named condition spans. This report does not promote BuffData roots "
                "or claim live formatter choice.")}


__all__ += ["audit_current_child_report"]
