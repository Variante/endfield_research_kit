"""Native selected DataPair ownership and exact child framing for BuffData."""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.core import CONTRACTS_DIR, LabelledReader

LABEL = "buffDataPair"
SCHEMA = "endfield.buff-datapair-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_datapair_native.json"
ROOT_CONTRACT_PATH = CONTRACTS_DIR / "buff_root_fifth_native.json"


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build":
        raise ValueError(f"{LABEL}.contract:identity")
    if contract.get("reviewedDependency") != ROOT_CONTRACT_PATH.name:
        raise ValueError(f"{LABEL}.contract:dependency")
    if len(contract.get("readOrder", ())) != 4 or len(contract.get("setterMethods", ())) != 4:
        raise ValueError(f"{LABEL}.contract:member-count")
    return contract


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail,
                "evidenceBoundary": "No DataPair ownership on changed native inputs."}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": f"{unity} is absent"}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    image = open_native_image(gate.gameassembly, gate.metadata)
    root = json.loads(ROOT_CONTRACT_PATH.read_text(encoding="utf-8"))
    for row in contract["methods"]:
        image.validate_method_row(row, label=LABEL)
    image.check_windows(root["codeWindows"][1:5], label=LABEL)
    context = root["nestedContexts"][0]
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell
    )
    if index != context["methodSpecIndex"]:
        raise ValueError(f"{LABEL}.native:root-list-method-spec-index")
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    if list(spec) != context["methodSpec"]:
        raise ValueError(f"{LABEL}.native:root-list-method-spec-record")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"{LABEL}.native:root-list-argument-count")
    argument = instance.arguments[0]
    argument_name = runtime_type_name(image.pe, image.metadata, argument.type_pointer_va)
    if argument.raw_type_record_hex != context["argumentRawHex"] or argument_name != (
        "System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>"
    ):
        raise ValueError(f"{LABEL}.native:root-list-argument")
    wrapper = image.metadata.types[contract["wrapperTypeDefinition"]]
    if image.metadata.type_full_name(wrapper) != contract["wrapperType"]:
        raise ValueError(f"{LABEL}.native:wrapper-type")
    setters = image.setter_methods(wrapper, parameter="typeName", label=LABEL)
    if setters != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")
    setter_names = [row[1].removeprefix("set___").removesuffix("__") for row in setters]
    read_names = [row[0] for row in contract["readOrder"]]
    if read_names != setter_names:
        raise ValueError(f"{LABEL}.native:read-order-setter-order")
    return {"status": "validated", "nativeInputs": expected,
            "wrapperType": contract["wrapperType"], "readOrder": contract["readOrder"],
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_datapair(data: bytes, start: int, *, end: int | None = None,
                    native_validation: dict[str, Any]) -> dict[str, Any]:
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-not-validated")
    limit = len(data) if end is None else end
    reader = LabelledReader(data, limit, start)
    reader.header(4, "memberHeader")
    is_dynamic = reader.boolean("isDynamic")
    key = reader.string("key")
    value_double = struct.unpack("<d", reader.raw(8, "valueDouble"))[0]
    value_str = reader.string("valueStr")
    return {"status": "datapair-exact-span", "start": start, "end": reader.pos,
            "isDynamic": is_dynamic, "key": key, "valueDouble": value_double,
            "valueStr": value_str, "ranges": reader.ranges,
            "wholeDataPairExact": True, "wholeBuffDataExact": False,
            "evidenceBoundary": _contract()["evidenceBoundary"]}


def decode_datapair_list(data: bytes, start: int, end: int, *,
                         native_validation: dict[str, Any],
                         require_end: bool = True) -> dict[str, Any]:
    """Decode one authenticated root ``List<DataPair>`` field to its bound."""
    if end - start < 4:
        raise ValueError("blackboard-list:truncated-count")
    count = struct.unpack_from("<i", data, start)[0]
    if count < -1 or count > 256:
        raise ValueError(f"blackboard-list:invalid-count={count}")
    offset = start + 4
    children = []
    for index in range(max(count, 0)):
        child = decode_datapair(data, offset, end=end,
                                native_validation=native_validation)
        child["indexInList"] = index
        children.append(child)
        offset = child["end"]
    if require_end and offset != end:
        raise ValueError(f"blackboard-list:endpoint={offset}; expected={end}")
    return {
        "status": "exact-datapair-list", "startOffset": start,
        "consumedEnd": offset, "count": count, "children": children,
        "wholeListExact": True, "positiveChildrenExact": count > 0,
    }
