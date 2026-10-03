"""Native-gated nested IfElse action in one sword BuffData damage condition."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack import buff_compare_float_action_receipt as compare
from scripts.game_data.memorypack import buff_if_else_action_receipt as if_else
from scripts.game_data.memorypack import buff_modify_dynamic_blackboard_action_receipt as modify


LABEL = "buffDamageSwordIfElseChild"
SCHEMA = "endfield.buff-damage-sword-if-else-child-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-sword-if-else-child-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_sword_if_else_child_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    dependencies = contract.get("reviewedDependencies")
    source = contract.get("selectedSource", {})
    parent = source.get("parentAction", {})
    children = source.get("nestedActions", [])
    path = source.get("path")
    if (
        not isinstance(dependencies, list) or len(dependencies) != 4
        or any(not isinstance(name, str) or PurePosixPath(name).name != name
               or not name.endswith(".json") for name in dependencies)
        or not isinstance(path, str)
        or PurePosixPath(path).parts[:3] != ("Data", "Json", "BuffData")
        or len(PurePosixPath(path).parts) != 4 or not path.endswith(".json")
        or not isinstance(source.get("sha256"), str)
        or len(source["sha256"]) != 64
        or any(ch not in "0123456789ABCDEF" for ch in source["sha256"])
        or any(type(parent.get(key)) is not int for key in ("tag", "start", "end"))
        or not 0 <= parent["start"] < parent["end"]
        or not isinstance(children, list) or len(children) != 2
        or any(type(row.get(key)) is not int for row in children
               for key in ("tag", "start", "end"))
        or [row.get("role") for row in children] != ["conditionAction", "succeedActions"]
        or not (parent["start"] < children[0]["start"] < children[0]["end"]
                < children[1]["start"] < children[1]["end"] < parent["end"])
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    """Compose only the three already reviewed action/child native validators."""
    contract = _contract()
    source = contract["selectedSource"]
    prior = json.loads((CONTRACTS_DIR / contract["reviewedDependencies"][3]).read_bytes())
    if (
        prior.get("nativeInputs") != contract["nativeInputs"]
        or prior.get("selectedSource", {}).get("path") != source["path"]
        or prior.get("selectedSource", {}).get("sha256") != source["sha256"]
        or prior.get("selectedSource", {}).get("action", {}).get("end")
        != source["parentAction"]["start"]
    ):
        raise ValueError(f"{LABEL}.contract:prior-child-drift")
    paths = {key: value for key, value in (("gameassembly", gameassembly), ("metadata", metadata)) if value is not None}
    parent_native = if_else.validate_current_native_contract(**paths)
    compare_native = compare.validate_current_native_contract(**paths)
    modify_native = modify.validate_current_native_contract(**paths)
    expected = contract["nativeInputs"]
    children = source["nestedActions"]
    if (
        any(row.get("status") != "validated" for row in
            (parent_native, compare_native, modify_native))
        or parent_native.get("nativeInputs") != expected
        or parent_native.get("unionTag") != source["parentAction"]["tag"]
        or compare_native.get("unionTag") != children[0]["tag"]
        or modify_native.get("unionTag") != children[1]["tag"]
        or any(row.get("nativeInputs") != {
            "GameAssembly.dll": expected["GameAssembly.dll"],
            "global-metadata.dat": expected["global-metadata.dat"],
        } for row in (compare_native, modify_native))
    ):
        raise ValueError(f"{LABEL}.native:selected-route-or-build-drift")
    return {
        "status": "validated", "nativeInputs": expected,
        "parent": parent_native, "children": [compare_native, modify_native],
        "source": source, "evidenceBoundary": contract["evidenceBoundary"],
    }


def decode_selected_child(data: bytes, *, source: str,
                          native_validation: dict[str, Any]) -> dict[str, Any]:
    """Join the two selected child receipts to the IfElse parent envelope."""
    contract = _contract()
    selected = contract["selectedSource"]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("source") != selected
        or native_validation.get("parent", {}).get("status") != "validated"
        or [row.get("status") for row in native_validation.get("children", [])]
        != ["validated", "validated"]
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes) or source != selected["path"]
        or hashlib.sha256(data).hexdigest().upper() != selected["sha256"]
        or len(data) < selected["parentAction"]["end"]
    ):
        raise ValueError(f"{LABEL}.source:path-or-sha256")
    parent = selected["parentAction"]
    child_specs = selected["nestedActions"]
    child_receipts = [
        compare.decode_compare_float_action_receipt(
            data, source=source, logical_sha256=selected["sha256"],
            start=child_specs[0]["start"], end=child_specs[0]["end"],
            native_validation=native_validation["children"][0],
        ),
        modify.decode_modify_dynamic_blackboard_action_receipt(
            data, source=source, logical_sha256=selected["sha256"],
            start=child_specs[1]["start"], end=child_specs[1]["end"],
            native_validation=native_validation["children"][1],
        ),
    ]
    if any(
        receipt.get("status") != "named-wrapper-exact-span"
        or receipt.get("wholeActionByteSpanExact") is not True
        or (receipt.get("tag"), receipt.get("start"), receipt.get("end"))
        != (spec["tag"], spec["start"], spec["end"])
        for receipt, spec in zip(child_receipts, child_specs, strict=True)
    ):
        raise ValueError(f"{LABEL}.children:receipt-drift")
    certified = [
        {"tag": spec["tag"], "start": spec["start"], "end": spec["end"]}
        for spec in child_specs
    ] + [parent]
    parent_receipt = if_else.decode_if_else_action_receipt(
        data, source=source, logical_sha256=selected["sha256"],
        start=parent["start"], end=parent["end"],
        native_validation=native_validation["parent"],
        certified_action_spans=certified,
    )
    fields = {row["fieldName"]: row for row in parent_receipt["namedFields"]}
    condition = fields[child_specs[0]["role"]]
    succeed = fields[child_specs[1]["role"]]
    fail = fields["failActions"]
    if (
        parent_receipt.get("status") != "named-wrapper-exact-span"
        or parent_receipt.get("wholeActionByteSpanExact") is not True
        or not (condition["start"] < child_specs[0]["start"]
                < child_specs[0]["end"] < condition["end"])
        or not (succeed["start"] < child_specs[1]["start"]
                < child_specs[1]["end"] < succeed["end"])
        or fail["end"] - fail["start"] != 7
        or struct.unpack_from("<i", data, fail["start"] + 1)[0] != 0
    ):
        raise ValueError(f"{LABEL}.parent:nested-sequence-join")
    return {
        "schema": SCHEMA, "status": "named-nested-if-else-exact-span",
        "source": source, "logicalSha256": selected["sha256"],
        "tag": parent["tag"], "start": parent["start"], "end": parent["end"],
        "namedFields": parent_receipt["namedFields"],
        "nestedActions": [
            {"role": spec["role"], "receipt": receipt}
            for spec, receipt in zip(child_specs, child_receipts, strict=True)
        ],
        "failActionsStoredCount": 0,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": False,
        "wholeConditionExact": False, "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }
