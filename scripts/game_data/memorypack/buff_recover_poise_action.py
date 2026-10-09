"""Named stored RecoverPoise action with typed effect, calculation and target children.

Raw flags and enums remain stored operands. Actual poise recovery and effect
playback require independent consumer and runtime evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import buff_damage_action as damage

LABEL = "buffRecoverPoiseAction"
CONTRACT_PATH = CONTRACTS_DIR / "buff_recover_poise_action_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-recover-poise-action-native-contract.v1", status="exact-current-build", label=LABEL)
    if set(value.get("records", {})) != {"recoverPoise"} or value.get("actionDispatch") != {"296":"recoverPoise"}:
        raise ValueError(f"{LABEL}.contract:shape")
    record = value['records']['recoverPoise']
    types = {m['fieldName']:m['declaredType'] for m in record['members']}
    if (types.get('effectData') != 'Beyond.Gameplay.EffectActionCfg'
            or types.get('recoverValue') != 'Beyond.Gameplay.Core.CalculationBase'
            or types.get('target') != 'Beyond.Gameplay.Core.TargetSettings'):
        raise ValueError(f'{LABEL}.contract:typed-children')
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in row["members"]]
            for key, row in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "recoverPoise", field: str = "") -> None:
    contract = _contract()
    error = CensusGateError(f"{LABEL}.{check}",
        source=(CONTRACTS_DIR / contract["records"][record]["sourceContract"]).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract["nativeInputs"])
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in ('target', 'damage'):
        child = children.get(name, {})
        if child.get("status") != "validated" or child.get("nativeInputs") != expected:
            _fail("shared-child", {"name": name, "nativeInputs": expected}, child)
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata)
    path = CONTRACTS_DIR / contract["records"]["recoverPoise"]["sourceContract"]
    source = json.loads(path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
    proved = records_native.validate_named_records(image, source, contract["records"], label=LABEL, fail=_fail)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    tag = next(iter(contract["actionDispatch"])); route = routes.get(int(tag))
    record = contract["records"]["recoverPoise"]
    if (audit.get("status") != "validated" or route is None or route.status != "resolved"
            or route.wrapper_name != record["wrapperTypeName"]
            or list(route.member_order) != [m["fieldName"] for m in record["members"]]
            or list(route.member_declared_types) != [m["declaredType"] for m in record["members"]]):
        _fail("dispatcher-members", record["wrapperTypeName"], None if route is None else route.row())
    after = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != "validated":
        return {"status": after.status, "detail": after.detail, "nativeInputs": expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll-after", expected["UnityPlayer.dll"], "mismatched")
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": contract["actionDispatch"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    contract = _contract(); context = native_validation.get("children", {})
    native = context.get("recoverPoise", {})
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract) or native.get("actionDispatch") != contract["actionDispatch"]
            or any(context.get(name, {}).get("status") != "validated"
                   or context[name].get("nativeInputs") != contract["nativeInputs"]
                   for name in ('target', 'damage'))
            or str(tag) not in contract["actionDispatch"] or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), "buff_recover_poise_action") != tag:
        raise ValueError(f"{LABEL}.decode:unexpected-null-union")
    members = contract["records"]["recoverPoise"]["members"]
    fields = []
    if reader.peek() == 255:
        reader.take(1, "null-action-wrapper")
    else:
        reader.header(len(members))
        for member in members:
            begin = reader.pos; value = {}; kind = member["kind"]
            if kind in ("byte", "scalar32"):
                value["rawHex"] = reader.take(1 if kind == "byte" else 4, member["fieldName"]).hex().upper()
            elif kind == "byte-payload":
                reader.byte_payload()
                value.update(rawHex=data[begin:reader.pos].hex().upper(), payloadEncoding="unresolved")
            elif kind in ("effect-configuration-profile", "calculation-profile"):
                if kind == "effect-configuration-profile": reader.effect_configuration_profile()
                else: reader.calculation_profile()
                child = damage.decode_child_value(data, source=source, digest=digest, start=begin,
                    end=reader.pos, child_kind="effectData" if kind == "effect-configuration-profile" else "calculation",
                    native_validation=native_validation)
                if (child.get("recursiveStoredSchemaExact") is not True
                        or [child.get("start"), child.get("end")] != [begin, reader.pos]):
                    raise ValueError(f"{LABEL}.decode:incomplete-child={member['fieldName']} at={begin}")
                value["child"] = child
            elif kind == "target-profile":
                reader.target_profile()
                span = {"start": begin, "end": reader.pos, "fieldName": member["fieldName"]}
                proof = ({**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                    if data[begin:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
                if proof.get("recursiveStoredSchemaExact") is not True or [proof.get("start"), proof.get("end")] != [begin, reader.pos]:
                    raise ValueError(f"{LABEL}.decode:target-span at={begin}")
                value["child"] = proof
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            fields.append({"fieldName": member["fieldName"], "declaredType": member["declaredType"],
                           "kind": kind, "start": begin, "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-recover-poise-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": tag, "start": start, "end": end, "typeName":contract["records"]["recoverPoise"]["runtimeTypeName"], "namedFields": fields,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
