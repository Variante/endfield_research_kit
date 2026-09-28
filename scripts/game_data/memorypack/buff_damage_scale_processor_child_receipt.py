"""Native-gated direct members of DamageScaleProcessor in Buff modifiers."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard_double


LABEL = "buffDamageScaleProcessorChild"
SCHEMA = "endfield.buff-damage-scale-processor-child-receipt.v2"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_scale_processor_child_native.json"
NATIVE_SCHEMA = "endfield.buff-damage-scale-processor-child-native-contract.v2"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL
    )
    if contract.get("reviewedDependencies") != [
        "buff_damage_lists_native.json", "buff_damage_modifier_child_native.json",
        "buff_adding_cooldown_ownership_native.json", "buff_stacking_compact_native.json"
    ]:
        raise ValueError(f"{LABEL}.contract:dependencies")
    plan = contract.get("fieldPlan")
    setters = contract.get("setterMethods")
    calls = contract.get("sourceCalls")
    contexts = contract.get("nestedContexts")
    if (type(contract.get("unionTag")) is not int
            or not 0 <= contract["unionTag"] <= 65535
            or not isinstance(plan, list) or len(plan) != 3
            or contract.get("serializedMemberCount") != len(plan)
            or [row.get("kind") for row in plan]
            != ["blackboard-double", "enum32", "signed-length-bytes"]
            or not isinstance(setters, list) or len(setters) != len(plan)
            or not isinstance(calls, list) or len(calls) != 1 + 2 * len(plan)
            or not isinstance(contexts, list) or len(contexts) != 2):
        raise ValueError(f"{LABEL}.contract:shape")
    if contract.get("blackboardChildReadOrder") != [
        "blackboardKey", "useBlackboardKey", "value"
    ]:
        raise ValueError(f"{LABEL}.contract:blackboard-child-order")
    names = [row.get("name") for row in plan]
    if (len(set(names)) != len(names)
            or [row[1] for row in setters] != [f"set___{name}__" for name in names]
            or [row[2] for row in setters] != [row["declaredType"] for row in plan]
            or [row.get("role") for row in calls] != ["header"] + [
                role for name in names for role in (f"{name}Source", f"{name}Setter")
            ]
            or [row.get("role") for row in contexts] != names[:2]):
        raise ValueError(f"{LABEL}.contract:field-order")
    return contract


def validate_current_native_contract(*, modifier_native: dict[str, Any]) -> dict[str, Any]:
    """Prove the selected tag-five source and three assigned member slots."""
    if modifier_native.get("status") != "validated":
        return {"status": modifier_native.get("status", "missing"),
                "detail": "damage-modifier parent is not validated"}
    contract = _contract()
    expected = contract["nativeInputs"]
    parent = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][1]).read_bytes())
    base = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][0]).read_bytes())
    blackboard_contract = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][2]).read_bytes()
    )
    string_contract = json.loads(
        (CONTRACTS_DIR / contract["reviewedDependencies"][3]).read_bytes()
    )
    if (parent.get("schema") != "endfield.buff-damage-modifier-child-native-contract.v1"
            or parent.get("nativeInputs") != expected
            or blackboard_contract.get("schema") != blackboard_double.SCHEMA
            or blackboard_contract.get("nativeInputs") != expected
            or blackboard_contract.get("selectedReadOrder") != contract["blackboardChildReadOrder"]
            or string_contract.get("schema") != "endfield.buff-stacking-compact-native-contract.v1"
            or string_contract.get("status") != "exact-current-build"
            or string_contract.get("nativeInputs") != expected
            or base.get("schemaVersion") != 1
            or f"processor{contract['unionTag']}" not in base.get("anonymousReadOrder", {})):
        raise ValueError(f"{LABEL}.contract:base-or-parent")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "detail": gate.detail}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if (not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        return {"status": "mismatched", "detail": "UnityPlayer.dll missing or hash differs"}

    image = open_native_image(gate.gameassembly, gate.metadata)
    wrapper_name = contract["wrapperName"]
    selected_methods = [row for row in base["methods"] if row[1] == wrapper_name
                        or row[1].startswith(wrapper_name + "+")]
    dispatcher_methods = [row for row in base["methods"]
                          if row[1].endswith("DamageProcessorBaseForMemoryPackFormatter")]
    route = f"tag{contract['unionTag']} "
    windows = [row for row in base["codeWindows"]
               if row["boundary"].startswith(route)
               or row["boundary"].startswith(f"dispatcher direct {route}")]
    formatter_name = wrapper_name + "+" + wrapper_name.rsplit(".", 1)[-1] + "Formatter"
    if (len(selected_methods) != 2 or len(dispatcher_methods) != 1
            or len(windows) != 3
            or selected_methods[0][1] != formatter_name
            or selected_methods[1][1] != wrapper_name
            or not windows[1]["startRva"] <= contract["headerCompare"][0] < windows[1]["endRva"]):
        raise ValueError(f"{LABEL}.contract:selected-base-route")
    for row in dispatcher_methods + selected_methods + [
        [method[0], wrapper_name, method[1], method[3]]
        for method in contract["setterMethods"]
    ]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(windows, label=LABEL)
    string_windows = [row for row in string_contract.get("codeWindows", [])
                      if row.get("startRva") == contract["sourceCalls"][-2]["targetRva"]]
    if len(string_windows) != 1 or "signed-length string reader" not in string_windows[0].get("boundary", ""):
        raise ValueError(f"{LABEL}.contract:string-reader-window")
    image.check_windows(string_windows, label=LABEL)
    image.check_instruction_windows([contract["headerCompare"]], label=LABEL)
    if bytes.fromhex(contract["headerCompare"][1]) != (
            b"\x40\x80\xff" + bytes((contract["serializedMemberCount"],))):
        raise ValueError(f"{LABEL}.contract:header-count")
    owners = [row for row in image.metadata.types
              if image.metadata.type_full_name(row) == wrapper_name]
    if (len(owners) != 1 or image.setter_methods(
            owners[0], parameter="typeName", label=LABEL
    ) != [row[:3] for row in contract["setterMethods"]]):
        raise ValueError(f"{LABEL}.native:wrapper-setters")

    calls = contract["sourceCalls"]
    if not all(windows[1]["startRva"] <= row["instructionRva"] < windows[1]["endRva"]
               for row in calls):
        raise ValueError(f"{LABEL}.contract:source-call-window")
    positions = [calls[0]["instructionRva"], contract["headerCompare"][0]]
    positions += [row["instructionRva"] for row in calls[1:]]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError(f"{LABEL}.contract:source-call-order")
    for row in calls:
        rva = row["instructionRva"]
        raw = bytes.fromhex(row["rawHex"])
        if (len(raw) != 5 or raw[0] != 0xE8
                or image.pe.bytes_at_va(image.pe.image_base + rva, 5) != raw
                or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != row["targetRva"]):
            raise ValueError(f"{LABEL}.native:source-call={row['role']}")
    if [calls[index]["targetRva"] for index in (2, 4, 6)] != [
            row[3] for row in contract["setterMethods"]]:
        raise ValueError(f"{LABEL}.native:setter-call-targets")

    for context in contract["nestedContexts"]:
        role = context["role"]
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:{role}-spec-index")
        raw = image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + index * 12, 12
        )
        spec = struct.unpack("<iii", raw)
        args = image.instantiations.resolve(spec[2]).arguments
        if (list(spec) != context["methodSpec"] or len(args) != 1
                or args[0].raw_type_record_hex != context["argumentRawHex"]
                or image.type_name(struct.unpack_from(
                    "<I", bytes.fromhex(context["argumentRawHex"])
                )[0]) != context["typeName"]):
            raise ValueError(f"{LABEL}.native:{role}-type")
    if not (contract["headerCompare"][0] < contract["nestedContexts"][0]["instructionRva"]
            < calls[1]["instructionRva"]
            and calls[2]["instructionRva"] < contract["nestedContexts"][1]["instructionRva"]
            < calls[3]["instructionRva"]):
        raise ValueError(f"{LABEL}.contract:context-source-order")
    blackboard_native = blackboard_double.validate_current_native_contract()
    if (blackboard_native.get("status") != "validated"
            or blackboard_native.get("selectedReadOrder") != contract["blackboardChildReadOrder"]):
        raise ValueError(f"{LABEL}.native:blackboard-child-{blackboard_native.get('status')}")
    return {"status": "validated", "unionTag": contract["unionTag"],
            "nativeInputs": expected, "fieldPlan": contract["fieldPlan"],
            "wrappedType": wrapper_name, "blackboardChildNative": blackboard_native,
            "blackboardChildReadOrder": contract["blackboardChildReadOrder"],
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_damage_scale_processor_span(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name only the three directly assigned members within a certified span."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    if (native_validation.get("blackboardChildNative", {}).get("status") != "validated"
            or native_validation.get("blackboardChildReadOrder") != [
                "blackboardKey", "useBlackboardKey", "value"
            ]):
        raise ValueError(f"{LABEL}:blackboard-child-native-not-validated")
    if hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper():
        raise ValueError(f"{LABEL}:logical-source-hash")
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}:source-range")
    reader = Reader(data, source, end)
    reader.pos = start
    tag = reader.nested_union_tag((native_validation["unionTag"],), "damage-processor")
    if tag != native_validation["unionTag"]:
        raise ValueError(f"{LABEL}:selected-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-damage-scale-wrapper")
        fields = []
        status = "exact-null-wrapper"
    else:
        plan = native_validation["fieldPlan"]
        reader.header(len(plan))
        fields = []
        for member in plan:
            field_start = reader.pos
            kind = member["kind"]
            if kind == "blackboard-double":
                reader.scalar_payload()
                child = blackboard_double.decode_adding_cooldown(
                    data, field_start, reader.pos,
                    native_validation=native_validation["blackboardChildNative"],
                )
                if (child.get("wholeValueExact") is not True
                        or child.get("startOffset") != field_start
                        or child.get("consumedEnd") != reader.pos
                        or (child["fields"] and [row["name"] for row in child["fields"]]
                            != native_validation["blackboardChildReadOrder"])):
                    raise ValueError(f"{LABEL}:blackboard-child-boundary")
                field = {"namedChild": child, "childBoundary": "named-exact"}
            elif kind == "enum32":
                raw = reader.take(4, member["name"])
                field = {"storedInt32": struct.unpack("<i", raw)[0],
                         "rawHex": raw.hex().upper()}
            elif kind == "signed-length-bytes":
                reader.byte_payload()
                length = struct.unpack_from("<i", data, field_start)[0]
                payload = None if length == -1 else data[field_start + 4:reader.pos]
                if (length < -1 or (payload is not None and len(payload) != length)
                        or (length == -1 and reader.pos != field_start + 4)):
                    raise ValueError(f"{LABEL}:zone-name-length")
                field = {"childBoundary": "signed-length-byte-span",
                         "storedByteLength": length, "isNull": length == -1,
                         "rawPayloadHex": None if payload is None else payload.hex().upper()}
            else:
                raise ValueError(f"{LABEL}:unsupported-field-kind={kind}")
            fields.append({"name": member["name"], "declaredType": member["declaredType"],
                           "start": field_start, "end": reader.pos, **field})
        status = "named-direct-members-exact-span"
    if reader.pos != end:
        raise ValueError(f"{LABEL}:processor-end={reader.pos}; expected={end}")
    return {"schema": SCHEMA, "status": status, "source": source,
            "logicalSha256": logical_sha256.upper(), "start": start, "end": end,
            "unionTag": tag, "wrappedType": native_validation["wrappedType"],
            "namedFields": fields, "wholeStoredSpanExact": True,
            "recursiveNamedSchemaExact": True, "wholeBuffDataExact": False}
