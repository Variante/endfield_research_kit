"""Named DistanceValidator storage, distinct from evaluated distance predicates."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import buff_adding_cooldown as scalar

LABEL = "buffSelectorDistanceValidator"
CONTRACT_PATH = CONTRACTS_DIR / "buff_selector_distance_validator_native.json"
TAG = 4


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-selector-distance-validator-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != {"distance"}
            or value.get("dispatcher", {}).get("unionTag") != TAG
            or value["records"]["distance"]["runtimeTypeName"]
            != "Beyond.Gameplay.Core.Selector+DistanceValidator+Data"):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {"distance": [{"fieldName": m["fieldName"], "kind": m["kind"]}
                         for m in contract["records"]["distance"]["members"]]}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "distance", field: str = "") -> None:
    contract = _contract()
    error = CensusGateError(f"{LABEL}.{check}",
        source=(CONTRACTS_DIR / contract["records"]["distance"]["sourceContract"]).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, unionTag=TAG,
                            nativeInputs=contract["nativeInputs"])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in ("selector", "effectVectors"):
        child = children.get(name, {})
        if child.get("status") != "validated" or child.get("nativeInputs") != expected:
            _fail("shared-child", {"name": name, "nativeInputs": expected}, child)
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata)
    path = CONTRACTS_DIR / contract["records"]["distance"]["sourceContract"]
    source = json.loads(path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
    proved = records_native.validate_named_records(image, source, contract["records"], label=LABEL, fail=_fail)
    base = json.loads((CONTRACTS_DIR / contract["switchContract"]).read_bytes())
    if (base.get("nativeInputs") != expected
            or any(contract["dispatcher"][k] != base["dispatcher"][k]
                   for k in ("switchTableRva", "switchEntryCount", "switchTableSha256"))):
        _fail("switch-build", expected, base.get("nativeInputs"))
    route = image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    load = contract["sourceTypeLoad"]; raw = bytes.fromhex(load[1])
    window = contract["dispatcher"]["routeWindow"]
    if (len(raw) != 7 or raw[:3] != b"\x48\x8b\x15"
            or not window["startRva"] <= load[0] <= window["endRva"] - 7
            or image.pe.image_base + load[0] + 7 + struct.unpack_from("<i", raw, 3)[0] != route["usageCell"]
            or contract["dispatcher"]["wrapperTypeDefinition"] != contract["records"]["distance"]["wrapperTypeDefinition"]
            or contract["dispatcher"]["wrapperName"] != contract["records"]["distance"]["wrapperTypeName"]):
        _fail("dispatcher-type-load", "selected branch loads named DistanceValidator wrapper", load)
    image.check_instruction_windows([load], label=LABEL)
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "evidenceBoundary": contract["evidenceBoundary"]}


def decode_value(data: bytes, *, source: str, digest: str, start: int, end: int,
                 children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); native = children.get("distanceValidator", {})
    vector = children.get("effectVectors", {})
    if (native.get("status") != "validated" or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract)
            or vector.get("status") != "validated" or vector.get("nativeInputs") != contract["nativeInputs"]
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start; fields = []
    if reader.nested_union_tag((TAG,), "distance-validator") != TAG:
        raise ValueError(f"{LABEL}.decode:physical-tag")
    if reader.peek() == 255:
        reader.take(1, "null-distance-wrapper"); status = "exact-null-wrapper"
    else:
        members = contract["records"]["distance"]["members"]
        reader.header(len(members)); status = "named-distance-validator-exact-span"
        for member in members:
            begin = reader.pos; kind = member["kind"]; value = {}
            if kind in ("byte", "scalar32"):
                value["rawHex"] = reader.take(1 if kind == "byte" else 4, member["fieldName"]).hex().upper()
            elif kind == "scalar-payload":
                if member["declaredType"] != scalar._contract()["rootContextType"]:
                    raise ValueError(f"{LABEL}.decode:typed-scalar")
                reader.scalar_payload()
                child = scalar.decode_adding_cooldown(data, begin, reader.pos, native_validation=vector["scalarNative"])
                if child.get("wholeValueExact") is not True or [child.get("startOffset"), child.get("consumedEnd")] != [begin, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:scalar-span at={begin}")
                value["child"] = child
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            fields.append({"fieldName": member["fieldName"], "declaredType": member["declaredType"],
                           "kind": kind, "start": begin, "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:field-end={reader.pos}; expected={end}")
    return {"source": source, "logicalSha256": digest.upper(), "start": start, "end": end,
            "tag": TAG, "status": status, "namedFields": fields, "recursiveStoredSchemaExact": True,
            "runtimePredicateKnown": False}
