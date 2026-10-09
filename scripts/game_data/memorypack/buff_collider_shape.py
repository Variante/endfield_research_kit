"""Named ColliderShapeData storage with complete raw Vector3 source proofs.

The three vectors each occupy twelve original bytes. They are distinct from
the blackboard vectors in HitBoxFinder.ShapeData. Keys, floats, enum and flags
remain stored operands; collider construction and hit results are not evaluated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL = "buffColliderShape"
CONTRACT_PATH = CONTRACTS_DIR / "buff_collider_shape_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-collider-shape-native-contract.v1", status="exact-current-build", label=LABEL)
    record = contract.get("records", {}).get("colliderShape", {})
    members = record.get("members", [])
    if (set(contract.get("records", {})) != {"colliderShape"}
            or record.get("runtimeTypeName") != "Beyond.Gameplay.ColliderShapeData"
            or len(members) != 16 or record.get("sourceContract") != "buff_7c_native.json"
            or len([m for m in members if m["kind"] == "raw12"]) != 3
            or any(m["declaredType"] != "UnityEngine.Vector3"
                   or m.get("unmanagedOutputSource", {}).get("destinationMode") != "direct-wrapper-instance-rcx"
                   for m in members if m["kind"] == "raw12")):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _members(contract: dict) -> dict:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in record["members"]]
            for key, record in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, **details: Any) -> None:
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, nativeInputs=_contract()["nativeInputs"], **details)
    raise error


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    contract = _contract(); pins = contract["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": pins}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != pins["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", pins["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata)
    path = CONTRACTS_DIR / contract["records"]["colliderShape"]["sourceContract"]
    source = json.loads(path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
    proved = named.validate_named_records(image, source, contract["records"], label=LABEL, fail=_fail)
    after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        return {"status": after.status, "detail": after.detail, "nativeInputs": pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll-after", pins["UnityPlayer.dll"], "mismatched")
    return {"status": "validated", "nativeInputs": pins, "recordMembers": proved,
        "evidenceBoundary": contract["evidenceBoundary"]}


def decode_value(data: bytes, *, source: str, digest: str, start: int, end: int,
                 native: dict[str, Any]) -> dict[str, Any]:
    contract = _contract()
    if (native.get("status") != "validated" or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract)
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start; fields = []
    members = contract["records"]["colliderShape"]["members"]
    if reader.peek() == 255:
        reader.take(1, "null-collider-shape"); status = "exact-null"
    else:
        reader.header(len(members)); status = "named-collider-exact-span"
        for member in members:
            begin = reader.pos; kind = member["kind"]; value = {}
            if kind in ("byte", "scalar32", "raw12"):
                width = {"byte": 1, "scalar32": 4, "raw12": 12}[kind]
                value["rawHex"] = reader.take(width, member["fieldName"]).hex().upper()
            elif kind == "byte-payload":
                reader.byte_payload()
                value.update(rawHex=data[begin:reader.pos].hex().upper(), payloadEncoding="unresolved")
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            fields.append({"fieldName": member["fieldName"], "declaredType": member["declaredType"],
                "kind": kind, "start": begin, "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:child-end={reader.pos}; expected={end}")
    return {"source": source, "logicalSha256": digest.upper(), "start": start, "end": end,
        "typeName": contract["records"]["colliderShape"]["runtimeTypeName"], "status": status,
        "namedFields": fields, "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
