"""Selected-build ownership and bounded child spans for BuffData field one."""
from __future__ import annotations

import hashlib
import json
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dummydll_metadata import DEFAULT_DUMMYDLL_ROOT, load
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets


CONTRACT_PATH = CONTRACTS_DIR / "buff_adding_cooldown_ownership_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_prefix_native.json"
CHILD_CONTRACT_PATH = CONTRACTS_DIR / "buff_35_native.json"
SCHEMA = "endfield.buff-adding-cooldown-ownership-native-contract.v1"
LABEL = "buffAddingCooldown"


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL
    )
    return value


def _selected_type(image: Any, name: str) -> Any:
    matches = [row for row in image.metadata.types
               if image.metadata.type_full_name(row) == name]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.native:type={name}; matches={len(matches)}")
    return matches[0]


def _check_wrapper_declarations(contract: dict[str, Any]) -> dict[str, str]:
    """Gate optional generated declarations without discarding native ownership."""
    manifest_path = DEFAULT_DUMMYDLL_ROOT / "generation.json"
    assembly_path = DEFAULT_DUMMYDLL_ROOT / "MemoryPack.Beyond.dll"
    recovery = (
        "Run python -m scripts.game_data.extraction.animestudio.generate_dummydll "
        "--dry-run, then --replace if the installed build needs regeneration."
    )
    if not manifest_path.is_file():
        return {"status": "missing", "detail": f"Missing {manifest_path}. {recovery}"}
    if not assembly_path.is_file():
        return {"status": "missing", "detail": f"Missing {assembly_path}. {recovery}"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        game = manifest["game"]
        expected = contract["nativeInputs"]
        if (game["gameAssemblySha256"].upper() != expected["GameAssembly.dll"]
                or game["metadataSha256"].upper() != expected["global-metadata.dat"]):
            return {"status": "mismatched", "detail": f"{manifest_path} describes a different installed build. {recovery}"}
        assembly_rows = [row for row in manifest["assemblies"]["files"]
                         if row["name"] == assembly_path.name]
        if len(assembly_rows) != 1:
            raise ValueError("MemoryPack.Beyond.dll missing or duplicated in generation manifest")
        assembly_bytes = assembly_path.read_bytes()
        if (len(assembly_bytes) != assembly_rows[0]["bytes"]
                or hashlib.sha256(assembly_bytes).hexdigest().upper() != assembly_rows[0]["sha256"].upper()):
            return {"status": "mismatched", "detail": f"{assembly_path} differs from {manifest_path}. {recovery}"}
        metadata = load(assembly_path)
        definitions = {row["name"]: row for row in metadata.type_defs()}
        root = definitions[contract["rootWrapper"]]
        root_setters = [(name, metadata.setter_parameter_type(index))
                        for index, name in metadata.setters(root["row"])
                        if name not in ("set____instance", "set___instance")]
        if root_setters[contract["rootFieldIndex"]] != tuple(contract["rootSetter"]):
            raise ValueError("root-setter-order")
        nested = definitions[contract["nestedWrapper"]]
        if metadata.type_def_or_ref_name(nested["extendsCode"]) != contract["nestedBaseWrapper"]:
            raise ValueError("nested-base-wrapper")
        base = definitions[contract["nestedBaseWrapper"]]
        nested_setters = [(name, metadata.setter_parameter_type(index))
                          for index, name in metadata.setters(base["row"])
                          if name not in ("set____instance", "set___instance")]
        if nested_setters != [tuple(row) for row in contract["nestedSetters"]]:
            raise ValueError("nested-setter-order")
        if [row[0].removeprefix("set___").removesuffix("__") for row in nested_setters] != contract["selectedReadOrder"]:
            raise ValueError("child-read-order")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, IndexError) as exc:
        return {"status": "invalid", "detail": f"Cannot verify {assembly_path} declarations: {exc}. {recovery}"}
    return {"status": "validated", "detail": f"{assembly_path} setters match the selected build"}


def validate_current_native_contract() -> dict[str, Any]:
    """Validate only the new source-result-to-field join, reusing owning contracts."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != "validated":
        return {"status": gate.status, "nativeStatus": gate.status,
                "declarationGate": {"status": "not-checked"}, "detail": gate.detail,
                "evidenceBoundary": "No named child fields on missing or mismatched native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "nativeStatus": "missing",
                "declarationGate": {"status": "not-checked"}, "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "nativeStatus": "mismatched",
                "declarationGate": {"status": "not-checked"}, "detail": "UnityPlayer.dll hash differs"}
    image = open_native_image(gate.gameassembly, gate.metadata)
    dependencies = [json.loads(path.read_text(encoding="utf-8"))
                    for path in (ROOT_CONTRACT_PATH, CHILD_CONTRACT_PATH)]
    if [path.name for path in (ROOT_CONTRACT_PATH, CHILD_CONTRACT_PATH)] != contract["reviewedDependencies"]:
        raise ValueError(f"{LABEL}.native:dependency-list")
    root, child = dependencies
    if root.get("schemaVersion") != 1 or child.get("schemaVersion") != 1:
        raise ValueError(f"{LABEL}.native:dependency-schema")
    root_method = root["methods"][1]
    if f"{root_method[1]}.{root_method[2]}" != contract["rootMethod"]:
        raise ValueError(f"{LABEL}.native:root-method")
    for dependency in dependencies:
        for row in dependency["methods"]:
            image.validate_method_row(row, label=LABEL)
        image.check_windows(dependency["codeWindows"], label=LABEL)
    context = root["nestedContexts"][contract["rootContextIndex"]]
    if context["typeName"] != contract["rootContextType"]:
        raise ValueError(f"{LABEL}.native:root-context-type")
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"],
        source=str(image.gameassembly), offset=cell,
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:method-spec-index")
    spec = struct.unpack("<iii", image.pe.bytes_at_va(
        int(image.registration["methodSpecs"], 16) + index * 12, 12
    ))
    if list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:method-spec")
    argument = image.instantiations.resolve(spec[2]).arguments[0]
    if argument.raw_type_record_hex != context["argumentRawHex"] or image.type_name(context["typeDefinition"]) != context["typeName"]:
        raise ValueError(f"{LABEL}.native:method-type-argument")
    instructions = contract["sourceToFieldInstructions"]
    if not (context["instructionRva"] < instructions[0][0] < instructions[1][0] < instructions[2][0]
            < root["nestedContexts"][contract["rootContextIndex"] + 1]["instructionRva"]):
        raise ValueError(f"{LABEL}.native:source-store-order")
    image.check_instruction_windows(instructions, label=LABEL)
    wrapper_type, _, wrapper_field = contract["instanceField"].partition("::")
    owner_type, _, owner_field = contract["destinationField"].partition("::")
    wrapper = _selected_type(image, wrapper_type)
    owner = _selected_type(image, owner_type)
    wrapper_offset = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, wrapper.index
    )[wrapper_field]
    field_offset = runtime_type_field_offsets(
        image.metadata, image.pe, image.registration, owner.index
    )[owner_field]
    if not 0 <= wrapper_offset < 128 or not 0 <= field_offset < 128:
        raise ValueError(f"{LABEL}.native:field-offset-width")
    if (bytes.fromhex(instructions[1][1]) != bytes((0x48, 0x8B, 0x4B, wrapper_offset))
            or bytes.fromhex(instructions[2][1]) != bytes((0x48, 0x89, 0x41, field_offset))):
        raise ValueError(f"{LABEL}.native:field-store-offset")
    declaration_gate = _check_wrapper_declarations(contract)
    audit = {
        "status": "validated" if declaration_gate["status"] == "validated" else "declaration-unavailable",
        "nativeStatus": "validated",
        "sourceStoreValidated": True,
        "rootField": contract["destinationField"],
        "declarationGate": declaration_gate,
        "evidenceBoundary": contract["evidenceBoundary"],
    }
    if audit["status"] == "validated":
        audit["selectedReadOrder"] = contract["selectedReadOrder"]
    return audit


def decode_adding_cooldown(
    data: bytes, start: int, end: int, *, native_validation: dict[str, Any]
) -> dict[str, Any]:
    """Name child spans while preserving raw values and nullable wire states."""
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.boundary:invalid")
    if data[start] == 0xFF:
        if end != start + 1:
            raise ValueError(f"{LABEL}.null:trailing-bytes")
        return {"status": "exact-null", "startOffset": start, "consumedEnd": end,
                "memberCount": None, "fields": [], "wholeValueExact": True}
    if data[start] != 3:
        raise ValueError(f"{LABEL}.header:expected=3 actual={data[start]}")
    cursor = start + 1
    if cursor + 4 > end:
        raise ValueError(f"{LABEL}.blackboardKey:truncated-length")
    key_start = cursor
    key_length = struct.unpack_from("<i", data, cursor)[0]
    cursor += 4
    if key_length < -1 or (key_length >= 0 and key_length > end - cursor - 5):
        raise ValueError(f"{LABEL}.blackboardKey:length={key_length}")
    key_bytes = None if key_length == -1 else data[cursor:cursor + key_length]
    cursor += max(0, key_length)
    if end - cursor < 5:
        raise ValueError(f"{LABEL}.tail:truncated")
    fields = [{"name": "blackboardKey", "start": key_start, "end": cursor,
               "declaredType": "string", "isNull": key_length == -1,
               "rawPayloadHex": None if key_bytes is None else key_bytes.hex().upper(),
               "boundaryClass": "exact-cursor"}]
    flag_start = cursor
    flag = data[cursor]
    cursor += 1
    fields.append({"name": "useBlackboardKey", "start": flag_start, "end": cursor,
                   "declaredType": "bool", "rawByte": flag,
                   "boundaryClass": "exact-cursor"})
    value_start = cursor
    raw_value = data[cursor:cursor + 4]
    cursor += 4
    fields.append({"name": "value", "start": value_start, "end": cursor,
                   "declaredType": "float", "rawBitsHex": raw_value.hex().upper(),
                   "boundaryClass": "exact-cursor"})
    if cursor != end:
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={cursor}")
    return {"status": "exact", "startOffset": start, "consumedEnd": cursor,
            "memberCount": 3, "headerRange": [start, start + 1],
            "fields": fields, "wholeValueExact": True,
            "fieldOrderSource": "current generated wrapper setters and selected native source reader",
            "evidenceBoundary": "Stored child field spans; no string decoder, provider selection, or evaluated cooldown."}
