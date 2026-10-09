"""Shared SequenceActionData evidence below maps and recursive action parents.

The reviewed declaration remains in the shared-event contract. A caller proves
its own field's closed type independently; this reader then certifies every
positive action against its original span. Stored terminal flags stay raw.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT

LABEL = "buffSequence"
CONTRACT_PATH = CONTRACTS_DIR / "buff_event_maps_native.json"
TYPE_NAME = "Beyond.Gameplay.Core.SequenceActionData"
READ_ORDER = ["actionData", "onlyExecuteWhenSourceIsGuard", "onlyExecuteWhenSourceIsMainChar"]


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-shared-event-maps-native-contract.v1", status="exact-current-build", label=LABEL)
    if value["sequence"]["runtimeType"]["typeName"] != TYPE_NAME:
        raise ValueError(f"{LABEL}.contract:type")
    return value


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, family="sequence", nativeInputs=_contract()["nativeInputs"])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_selected_source(image: Any, contract: dict[str, Any]) -> list[str]:
    sequence = contract["sequence"]
    dependency = json.loads((CONTRACTS_DIR / sequence["dependency"]).read_bytes())
    if dependency.get("nativeInputs") != contract["nativeInputs"]:
        _fail("dependency-build", contract["nativeInputs"], dependency.get("nativeInputs"))
    source = dependency[sequence["section"]]
    for row in source["methods"]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    owner = image.metadata.types[source["wrapperTypeDefinition"]]
    if (image.type_name(source["wrapperTypeDefinition"]) != source["wrapperName"]
            or image.setter_methods(owner, parameter="typeName", label=LABEL) != source["setterMethods"]
            or [r[0] for r in source["setterMethods"]] != [r["setterMethodIndex"] for r in sequence["parameterTypes"]]):
        _fail("setters", source["setterMethods"], image.setter_methods(owner, parameter="typeName", label=LABEL))
    records_native.check_runtime_shape(image, sequence, label=LABEL, fail=_fail)
    order = [row[1].removeprefix("set___").removesuffix("__") for row in source["setterMethods"]]
    if order != READ_ORDER or sequence["parameterTypes"][0]["typeName"] != "Beyond.Gameplay.Core.AbilityAction+AbilityActionData[]":
        _fail("ordered-typed-plan", READ_ORDER, order)
    return order


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    order = validate_selected_source(open_native_image(gate.gameassembly, gate.metadata), contract)
    after = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        return {"status": after.status, "detail": after.detail, "nativeInputs": expected}
    return {"status": "validated", "nativeInputs": expected, "typeName": TYPE_NAME, "readOrder": order}


def decode_value(data: bytes, source: str, digest: str, start: int, end: int,
                 native: dict[str, Any], depth: int, *, require_end: bool = True) -> dict[str, Any]:
    from scripts.game_data.memorypack import buff_recursive_actions as actions
    proof = native.get("children", {}).get("sequence", {}); expected = _contract()["nativeInputs"]
    if (native.get("status") != "validated" or proof.get("status") != "validated"
            or proof.get("nativeInputs") != expected or proof.get("typeName") != TYPE_NAME
            or proof.get("readOrder") != READ_ORDER or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    if depth > SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f"{LABEL}.decode:depth-limit")
    reader = Reader(data, source, end); reader.pos = start
    if reader.peek() == 255:
        reader.take(1, "null-sequence")
        result = {"status": "exact-null", "namedFields": []}
    else:
        reader.header(3); count = reader.count(1, reserve=2, nullable=True); elements = []
        for _ in range(max(0, count)):
            begin = reader.pos; lead = reader.peek()
            if lead == 255:
                reader.take(1, "null-action")
                elements.append({"start": begin, "end": reader.pos, "status": "exact-null", "recursiveStoredSchemaExact": True})
                continue
            tag = int.from_bytes(data[begin+1:begin+3], "little") if lead == 250 else lead
            if tag not in actions.SUPPORTED_TAGS:
                raise ValueError(f"{LABEL}.decode:unsupported-action-at={begin}; tag={tag}")
            reader.action(depth + 1)
            child = actions.decode_action(data, source=source, digest=digest, start=begin, end=reader.pos,
                tag=tag, native_validation=native, depth=depth + 1)
            if child.get("recursiveStoredSchemaExact") is not True or [child.get("start"), child.get("end")] != [begin, reader.pos]:
                raise ValueError(f"{LABEL}.decode:incomplete-action at={begin}")
            elements.append(child)
        flags = []
        for name in READ_ORDER[1:]:
            at = reader.pos; raw = reader.take(1, name)[0]
            flags.append({"name": name, "start": at, "end": reader.pos, "rawByte": raw})
        result = {"status": "named-sequence-exact", "count": count, "actions": elements, "flags": flags}
    if require_end and reader.pos != end:
        raise ValueError(f"{LABEL}.decode:end={reader.pos}; expected={end}")
    return {"start": start, "end": reader.pos, "typeName": TYPE_NAME, **result,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
