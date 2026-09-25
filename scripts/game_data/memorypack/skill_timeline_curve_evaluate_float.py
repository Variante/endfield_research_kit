"""Current-build SkillData CurveEvaluateFloat 0x0098 action framing.

The selected dispatcher is checked here, while the already reviewed Buff
contract supplies the full source-reader window and nested type evidence.
This reader consumes stored values only; it does not evaluate a curve.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "skillTimelineCurveEvaluateFloat"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_curve_evaluate_float_native.json"
SOURCE_PATH = CONTRACTS_DIR / "buff_98_native.json"
TAG = 0x0098
READ_ORDER = (
    "byte", "scalar32", "scalar32", "scalar32", "byte-payload",
    "curve", "scalar-payload", "byte-payload", "byte",
)
NESTED_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "UnityEngine.AnimationCurve",
    "Beyond.Blackboard+BlackboardDouble",
)


@lru_cache(maxsize=1)
def _contract() -> tuple[dict[str, Any], dict[str, Any]]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-curve-evaluate-float-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    source = json.loads(SOURCE_PATH.read_bytes())
    source_ref = contract.get("sourceContract", {})
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract.get("serializedMemberCount") != len(READ_ORDER)
        or source_ref.get("path") != SOURCE_PATH.name
        or source_ref.get("schemaVersion") != 1
        or source_ref.get("readOrderRef") != "anonymousReadOrder.member9"
        or tuple(source_ref.get("readOrder", ())) != READ_ORDER
        or tuple(source_ref.get("nestedTypes", ())) != NESTED_TYPES
        or source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member9", ())) != READ_ORDER
        or tuple(row.get("typeName") for row in source.get("nestedContexts", ())) != NESTED_TYPES
        or len(source.get("methods", ())) != 2
        or any(row[2] != "Deserialize" for row in source["methods"])
        or not all(row[1].startswith(contract["dispatcher"]["wrapperName"]) for row in source["methods"])
        or not source.get("codeWindows")
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract, source


def validate_current_native_contract() -> dict[str, Any]:
    """Reprove the selected route and source reader on installed binaries."""
    contract, source = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in source["methods"]]
    image.check_windows(source["codeWindows"], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    for context in source["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index")
        address = int(image.registration["methodSpecs"], 16) + index * 12
        spec = method_spec_record(
            image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
            image.registration["genericInstsCount"], source=LABEL, offset=address,
        )
        if list(spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:method-spec-record")
        instance = image.instantiations.resolve(spec[2])
        if len(instance.arguments) != 1:
            raise ValueError(f"{LABEL}.native:generic-arity")
        argument = bytes.fromhex(instance.arguments[0].raw_type_record_hex)
        if (
            argument.hex().upper() != context["argumentRawHex"].upper()
            or struct.unpack_from("<Q", argument)[0] != context["typeDefinition"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}.native:nested-type")
    return {
        "status": "validated",
        "nativeInputs": expected,
        "sourceContract": SOURCE_PATH.name,
        "unionTag": TAG,
        "sourceReadCount": len(READ_ORDER),
        "nestedContextCount": len(NESTED_TYPES),
        "methodIndices": methods,
    }


def decode_curve_evaluate_float_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Consume the exact nine-member route with bounded nested profiles."""
    del depth
    _contract()
    if tag != TAG or width != 1:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return
    reader.header(len(READ_ORDER))
    reader.take(1, "CurveEvaluateFloat.anonymous-byte")
    for _ in range(3):
        reader.take(4, "CurveEvaluateFloat.anonymous-scalar32")
    reader.byte_payload()
    reader.curve_profile()
    reader.scalar_payload()
    reader.byte_payload()
    reader.take(1, "CurveEvaluateFloat.anonymous-byte")
