"""Named stored action records with independently authenticated recursive children.

Original byte spans remain authoritative; stored configuration does not prove
live provider selection, branch execution or resulting game state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native

LABEL = "buffWeaponVisualAction"
CONTRACT_PATH = CONTRACTS_DIR / "buff_weapon_visual_action_native.json"
RECORD_KEYS = {'charWeaponVisible', 'weaponVfxOverride'}
DISPATCH = {'55': 'charWeaponVisible'}
CHILD_TYPES = {'weapon-vfx-profile': 'Beyond.Gameplay.WeaponVFXOverrideConfig'}


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-weapon-visual-action-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != RECORD_KEYS
            or value.get("actionDispatch") != DISPATCH
            or value.get("childTypes") != CHILD_TYPES):
        raise ValueError(f"{LABEL}.contract:shape")
    parent = value["records"]["charWeaponVisible"]
    child = value["records"]["weaponVfxOverride"]
    if (parent.get("inheritedMemberCount") != 4 or len(parent["members"]) != 10
            or child.get("inheritedMemberCount") != 0 or len(child["members"]) != 18):
        raise ValueError(f"{LABEL}.contract:record-counts")
    for key, record in value["records"].items():
        for member in record["members"]:
            kind = member["kind"]
            if kind == "weapon-vfx-profile":
                if (key != "charWeaponVisible" or member["fieldName"] != "vfxOverrideConfig"
                        or member["declaredType"] != CHILD_TYPES[kind]
                        or member.get("sourceContextInstructionRva") is None):
                    raise ValueError(f"{LABEL}.contract:typed-vfx-child")
            elif (kind == "byte" and member["declaredType"] == "bool"
                    or kind == "byte-payload" and key == "weaponVfxOverride" and member["declaredType"] == "string"
                    or kind == "scalar32" and key == "charWeaponVisible"):
                continue
            else:
                raise ValueError(f"{LABEL}.contract:member-kind={key}.{member['fieldName']}")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in row["members"]]
            for key, row in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    contract = _contract()
    source = contract["records"][record]["sourceContract"] if record else CONTRACT_PATH.name
    error = CensusGateError(f"{LABEL}.{check}", source=(CONTRACTS_DIR / source).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract["nativeInputs"])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract() -> dict[str, Any]:
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata)
    proved = {}
    for name in sorted({record["sourceContract"] for record in contract["records"].values()}):
        path = CONTRACTS_DIR / name; source = json.loads(path.read_bytes())
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        selected = {k: r for k, r in contract["records"].items() if r["sourceContract"] == name}
        proved.update(records_native.validate_named_records(image, source, selected, label=LABEL, fail=_fail))
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract["actionDispatch"].items():
        record = contract["records"][key]; route = routes.get(int(tag))
        if (audit.get("status") != "validated" or route is None or route.status != "resolved"
                or route.wrapper_name != record["wrapperTypeName"]
                or list(route.member_order) != [m["fieldName"] for m in record["members"]]
                or list(route.member_declared_types) != [m["declaredType"] for m in record["members"]]):
            _fail("dispatcher-members", record["wrapperTypeName"], None if route is None else route.row(), record=key)
    after = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        return {"status": after.status, "detail": after.detail, "nativeInputs": expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll-after", expected["UnityPlayer.dll"], "mismatched")
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": contract["actionDispatch"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); native = native_validation.get("children", {}).get("weaponVisual", {})
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract)
            or native.get("actionDispatch") != DISPATCH or tag != 55
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), "weapon-visual-action") != tag:
        raise ValueError(f"{LABEL}.decode:physical-tag")

    def record(key: str) -> dict[str, Any]:
        at = reader.pos; plan = contract["records"][key]; fields = []
        if reader.peek() == 255:
            reader.take(1, "null-" + key)
            return {"start": at, "end": reader.pos, "status": "exact-null-wrapper",
                    "typeName": plan["runtimeTypeName"], "namedFields": [], "recursiveStoredSchemaExact": True}
        reader.header(len(plan["members"]))
        for member in plan["members"]:
            begin = reader.pos; kind = member["kind"]; value = {}
            if kind in {"byte", "scalar32"}:
                value["rawHex"] = reader.take(1 if kind == "byte" else 4, member["fieldName"]).hex().upper()
            elif kind == "byte-payload":
                reader.byte_payload()
                value.update(rawHex=data[begin:reader.pos].hex().upper(), payloadEncoding="unresolved")
            elif kind == "weapon-vfx-profile":
                value["child"] = record("weaponVfxOverride")
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if "child" in value and (value["child"].get("recursiveStoredSchemaExact") is not True
                    or [value["child"].get("start"), value["child"].get("end")] != [begin, reader.pos]):
                raise ValueError(f"{LABEL}.decode:child-span={member['fieldName']} at={begin}")
            fields.append({"fieldName": member["fieldName"], "declaredType": member["declaredType"],
                           "kind": kind, "start": begin, "end": reader.pos, **value})
        return {"start": at, "end": reader.pos, "typeName": plan["runtimeTypeName"],
                "namedFields": fields, "recursiveStoredSchemaExact": True}

    parent = record("charWeaponVisible")
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-weapon-visual-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": tag, "start": start, "end": end,
            "typeName": contract["records"]["charWeaponVisible"]["runtimeTypeName"], "parent": parent,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
