"""Named AuraAction/HealAction storage under selected native evidence.

Complete reviewed normal/null windows, ordered source calls, closed field
MethodSpecs and actual runtime stores/setters prove both action layouts and
BuffInput (three members), TargetFilter, ColliderShapeData, GameplayTagList
and GameplayTag. Collider Vector3 reads join both contiguous stores, covering
all twelve bytes. BuffInput is independently typed; the five-member CreateBuff
input is a different format. Tag lists retain their element headers rather
than borrowing the root's unframed DWORD-array format.

The direct tier names stored fields. Conditional composition uses independently
typed shared AssignPair, SequenceActionData, TargetSettings, DirectionSettings,
icon-duration, query, BlackboardDouble, calculation and effect readers on the
original spans. Null wrappers/lists/elements and empty lists remain distinct.
Unsupported sequence actions, calculation routes, effect arrays or target
children refuse the complete action. Values remain raw: evaluated blackboards,
live provider/formatter selection and gameplay execution are unresolved.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import buff_create_input_child_receipt as assignments
from scripts.game_data.memorypack import buff_create_icon_duration_child_receipt as icon
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as direction
from scripts.game_data.memorypack import buff_selector_shared_children as query
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_damage_action as damage
from scripts.game_data.memorypack import buff_recursive_control_actions as control

LABEL = "buffAuraHealActions"
CONTRACT_PATH = CONTRACTS_DIR / "buff_aura_heal_actions_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-aura-heal-actions-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != {"aura", "buffInput", "targetFilter", "colliderShape",
                                          "heal", "tagList", "tagElement"}
            or set(value.get("actionDispatch", {}).values()) != {"aura", "heal"}
            or len(value["actionDispatch"]) != 2):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
                            expected=expected, actual=actual)
    error.diagnostic.update({"validator": LABEL, "record": record, "field": field,
                             "nativeInputs": _contract()["nativeInputs"]})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in record["members"]]
            for key, record in contract["records"].items()}


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    """Authenticate the selected native build, source reads and typed joins."""
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in ("createInput", "iconDuration", "direction", "target", "ifElse", "findSettings",
                 "effectVectors", "damage"):
        child = children.get(name, {})
        if (child.get("status") != "validated"
                or any(child.get("nativeInputs", {}).get(k) != expected[k]
                       for k in ("GameAssembly.dll", "global-metadata.dat"))):
            _fail("shared-child", expected, {"name": name, "status": child.get("status"),
                                           "nativeInputs": child.get("nativeInputs")})
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    actual = hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else "missing"
    if actual != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], actual)
    image = open_native_image(gate.gameassembly, gate.metadata); proved = {}
    sources = sorted({r["sourceContract"] for r in contract["records"].values()})
    for name in sources:
        source = json.loads((CONTRACTS_DIR / name).read_bytes())
        if source.get("schemaVersion") != 1:
            _fail("source-schema", 1, {"source": name, "schemaVersion": source.get("schemaVersion")})
        selected = {k: r for k, r in contract["records"].items() if r["sourceContract"] == name}
        proved.update(records_native.validate_named_records(image, source, selected, label=LABEL, fail=_fail))
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    for tag, key in contract["actionDispatch"].items():
        route = routes.get(int(tag)); record = contract["records"][key]
        if (audit.get("status") != "validated" or route is None or route.status != "resolved"
                or route.wrapper_name != record["wrapperTypeName"]
                or list(route.member_order) != [m["fieldName"] for m in record["members"]]
                or list(route.member_declared_types) != [m["declaredType"] for m in record["members"]]):
            _fail("dispatcher-members", record["wrapperTypeName"], None if route is None else route.row(), record=key)
    return {"status": "validated", "nativeInputs": expected, "recordMembers": proved,
            "actionDispatch": contract["actionDispatch"], "evidenceBoundary": contract["evidenceBoundary"]}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]],
                  depth: int = 0) -> dict[str, Any]:
    """Compose reached children after independently proving each parent field."""
    contract = _contract(); context = native_validation.get("children", {}); native = context.get("auraHeal", {})
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract)
            or native.get("actionDispatch") != contract["actionDispatch"]
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    if depth > SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f"{LABEL}.decode:depth-limit")
    if str(tag) not in contract["actionDispatch"]:
        raise ValueError(f"{LABEL}.decode:unsupported-tag={tag}")
    reader = Reader(data, source, end); reader.pos = start
    args = {"source": source, "logical_sha256": digest}

    def child_list(key: str, *, reserve: int = 0) -> dict[str, Any]:
        a = reader.pos; count = reader.count(1, reserve=reserve, nullable=True)
        elements = [record(key) for _ in range(max(0, count))]
        return {"start": a, "end": reader.pos, "count": count, "elements": elements,
                "recursiveStoredSchemaExact": True}

    def record(key: str) -> dict[str, Any]:
        a = reader.pos; members = contract["records"][key]["members"]
        if reader.peek() == 255:
            reader.take(1, "null-" + key)
            return {"start": a, "end": reader.pos, "status": "exact-null", "namedFields": [],
                    "recursiveStoredSchemaExact": True}
        reader.header(len(members)); fields = []
        for member in members:
            begin = reader.pos; kind = member["kind"]; value = {}
            if kind in ("byte", "scalar32", "raw12"):
                value["rawHex"] = reader.take({"byte": 1, "scalar32": 4, "raw12": 12}[kind], member["fieldName"]).hex().upper()
            elif kind in ("byte-payload", "bytePayload"):
                reader.byte_payload(); value["rawHex"] = data[begin:reader.pos].hex().upper()
            elif kind == "nullable-counted-buff-input-profiles":
                value["child"] = child_list("buffInput", reserve=4)
            elif kind == "nullable-counted-assignment-profiles":
                count = reader.count(1, reserve=4, nullable=True)
                for _ in range(max(0, count)):
                    reader.assignment_profile()
                value["child"] = assignments.decode_assignment_list(data, **args, start=begin, end=reader.pos,
                                                                      native_validation=context["createInput"])
            elif kind in ("collider-shape-profile", "target-filter-profile", "tagList"):
                value["child"] = record({"collider-shape-profile": "colliderShape",
                                         "target-filter-profile": "targetFilter", "tagList": "tagList"}[kind])
            elif kind == "signedCount":
                value["child"] = child_list("tagElement")
            elif kind == "scalar-payload":
                reader.scalar_payload()
                value["child"] = scalar.decode_adding_cooldown(data, begin, reader.pos,
                                                       native_validation=context["effectVectors"]["scalarNative"])
                if value["child"].get("wholeValueExact") is not True:
                    raise ValueError(f"{LABEL}.decode:scalar-child-unproved at={begin}")
                value["child"]["recursiveStoredSchemaExact"] = True
            elif kind == "scalar-bytes-profile":
                reader.scalar_bytes_profile()
                value["child"] = ({"start": begin, "end": reader.pos, "status": "exact-null",
                                    "wholeStoredSpanExact": True} if data[begin:reader.pos] == b"\xff" else
                    icon.decode_icon_duration_child(data, **args, start=begin, end=reader.pos,
                                                    native_validation=context["iconDuration"]))
                if value["child"].get("wholeStoredSpanExact") is not True:
                    raise ValueError(f"{LABEL}.decode:icon-child-unproved at={begin}")
                value["child"]["recursiveStoredSchemaExact"] = True
            elif kind == "query-profile":
                reader.query_profile()
                value["child"] = query.decode_query_value(data, source=source, digest=digest, start=begin,
                                                          end=reader.pos, native=context["findSettings"])
            elif kind == "direction-profile":
                reader.direction_profile()
                child = direction.decode_direction_settings_value(data, **args, start=begin, end=reader.pos,
                                                                   native_validation=context["direction"])
                if any(m.get("nestedTargetStatus") != "exact-null" for m in child["namedMembers"] if m["kind"] == "object"):
                    raise ValueError(f"{LABEL}.decode:positive-direction-target-unproved at={begin}")
                value["child"] = {**child, "recursiveStoredSchemaExact": True}
            elif kind in ("target-profile", "target"):
                reader.target_profile()
                span = {"start": begin, "end": reader.pos, "fieldName": member["fieldName"]}
                value["child"] = ({**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                    if data[begin:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
            elif kind == "sequence":
                reader.sequence(depth + 1)
                value["child"] = ({"start": begin, "end": reader.pos, "status": "exact-null",
                                    "recursiveStoredSchemaExact": True} if data[begin:reader.pos] == b"\xff"
                    else control.read_sequence(data, source, digest, begin, reader.pos, native_validation, depth + 1))
            elif kind in ("calculation", "effectConfiguration"):
                reader.calculation_profile() if kind == "calculation" else reader.effect_configuration_profile()
                value["child"] = damage.decode_child_value(data, source=source, digest=digest, start=begin,
                    end=reader.pos, child_kind="calculation" if kind == "calculation" else "effectData",
                    native_validation=native_validation)
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            if "child" in value and value["child"].get("recursiveStoredSchemaExact",
                                                       value["child"].get("recursiveNamedSchemaExact")) is not True:
                raise ValueError(f"{LABEL}.decode:incomplete-child={member['fieldName']} at={begin}")
            fields.append({"fieldName": member["fieldName"], "kind": kind, "start": begin,
                           "end": reader.pos, **value})
        return {"start": a, "end": reader.pos, "status": "named-stored-members-exact-span",
                "typeName": contract["records"][key]["runtimeTypeName"], "namedFields": fields,
                "recursiveStoredSchemaExact": True}

    if reader.nested_union_tag((tag,), "aura-heal-action") != tag:
        raise ValueError(f"{LABEL}.decode:physical-tag")
    parent = record(contract["actionDispatch"][str(tag)])
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-aura-heal-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": tag, "start": start, "end": end,
            "parent": parent, "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
