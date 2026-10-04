"""Named CheckSkillType, CheckBuffStackNum and InterruptAction storage.

Reviewed complete normal/null windows, ordered source reads, generated wrapper
inheritance, actual result-to-setter/store transfers and closed MethodSpecs
prove the three parent layouts at the direct tier. Both Interrupt targets
retain independent null states. CheckBuffStackNum joins the one-member BuffId
value, not a list or the three-member BlackboardBuffId, and independently joins
TargetSettings and the stored BlackboardDouble profile.

Conditional composition reuses authenticated child readers on original spans.
The SkillType list's exact closed element type and independent four-byte source
read witness permit bounded count-times-four storage under the shared list
consumer. They do not prove live provider selection. Lists retain null/empty
states; scalars retain arbitrary raw bits. Unsupported targets, malformed
children or unconsumed tails refuse the parent. Evaluated blackboards, enum
meaning, interrupt execution and whole-root completeness remain unresolved
here; only the owning Buff root receipt can establish physical EOF.
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
from scripts.game_data.memorypack import buff_id_actions as ids
from scripts.game_data.memorypack import buff_adding_cooldown as scalar

LABEL = "buffSkillStackInterruptActions"
CONTRACT_PATH = CONTRACTS_DIR / "buff_skill_stack_interrupt_actions_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.buff-skill-stack-interrupt-actions-native-contract.v1",
        status="exact-current-build", label=LABEL)
    if (set(value.get("records", {})) != {"skillType", "buffStack", "interrupt"}
            or set(value.get("actionDispatch", {}).values()) != set(value["records"])
            or len(value["actionDispatch"]) != 3):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()["actionDispatch"]))


def _members(contract: dict[str, Any]) -> dict[str, Any]:
    return {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in record["members"]]
            for key, record in contract["records"].items()}


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    def bounded(value: Any) -> Any:
        if isinstance(value, str):
            return value[:256]
        if isinstance(value, dict):
            return {str(k): bounded(v) for k, v in list(value.items())[:16]}
        if isinstance(value, (list, tuple)):
            return [bounded(v) for v in value[:16]]
        return value
    contract = _contract(); spec = contract["records"].get(record, {})
    error = CensusGateError(f"{LABEL}.{check}",
        source=(CONTRACTS_DIR / spec["sourceContract"]).as_posix() if spec else CONTRACT_PATH.as_posix(),
        expected=bounded(expected), actual=bounded(actual))
    error.diagnostic.update({"validator": LABEL, "record": record, "field": field,
        "unionTag": next((int(t) for t, k in contract["actionDispatch"].items() if k == record), None),
        "nativeInputs": contract["nativeInputs"]})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, children: dict[str, Any]) -> dict[str, Any]:
    """Authenticate the selected build, source widths and named typed joins."""
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name in ("target", "blackboard", "buffIdActions"):
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
    for name in sources + contract["additionalSourceContracts"]:
        path = CONTRACTS_DIR / name; source = json.loads(path.read_bytes())
        buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
            image.modules, image.owners, source=str(gate.gameassembly), contract_path=path)
        selected = {k: r for k, r in contract["records"].items() if r["sourceContract"] == name}
        if selected:
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
                  native_validation: dict[str, Any],
                  target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    """Compose each independently typed child and require the original end."""
    contract = _contract(); context = native_validation.get("children", {})
    native = context.get("skillStackInterrupt", {})
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native.get("nativeInputs") != contract["nativeInputs"]
            or native.get("recordMembers") != _members(contract)
            or native.get("actionDispatch") != contract["actionDispatch"]
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    if str(tag) not in contract["actionDispatch"]:
        raise ValueError(f"{LABEL}.decode:unsupported-tag={tag}")
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), "skill-stack-interrupt-action") != tag:
        raise ValueError(f"{LABEL}.decode:physical-tag")
    record = contract["records"][contract["actionDispatch"][str(tag)]]
    reader.header(len(record["members"])); fields = []
    for member in record["members"]:
        begin = reader.pos; kind = member["kind"]; value = {}
        if kind in ("byte", "scalar32"):
            value["rawHex"] = reader.take(1 if kind == "byte" else 4, member["fieldName"]).hex().upper()
        elif kind in ("target-profile", "target"):
            reader.target_profile()
            span = {"start": begin, "end": reader.pos, "fieldName": member["fieldName"]}
            value["child"] = ({**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                if data[begin:reader.pos] == b"\xff" else target_decoder(data, source, digest, span, context))
        elif kind == "single-payload":
            reader.single_payload()
            value["child"] = ids.decode_id_value(data, source, digest, begin, reader.pos,
                                                context["buffIdActions"]["child"])
        elif kind == "scalar-payload":
            reader.scalar_payload()
            child = scalar.decode_adding_cooldown(data, begin, reader.pos,
                                                native_validation=context["blackboard"]["childNative"])
            if child.get("wholeValueExact") is not True:
                raise ValueError(f"{LABEL}.decode:scalar-child-unproved at={begin}")
            value["child"] = {**child, "recursiveStoredSchemaExact": True}
        elif kind == "counted-scalar32":
            count = reader.count(4, nullable=True)
            elements = []
            for _ in range(max(0, count)):
                a = reader.pos
                elements.append({"start": a, "end": a + 4,
                    "rawHex": reader.take(4, "skill-type-element").hex().upper()})
            value["child"] = {"start": begin, "end": reader.pos, "count": count, "elements": elements,
                              "recursiveStoredSchemaExact": True, "liveProviderSelectionKnown": False}
        else:
            raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
        if "child" in value and value["child"].get("recursiveStoredSchemaExact",
                                                   value["child"].get("recursiveNamedSchemaExact")) is not True:
            raise ValueError(f"{LABEL}.decode:incomplete-child={member['fieldName']} at={begin}")
        fields.append({"fieldName": member["fieldName"], "kind": kind, "start": begin,
                       "end": reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-skill-stack-interrupt-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": tag, "start": start, "end": end,
            "typeName": record["runtimeTypeName"], "namedFields": fields,
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}
