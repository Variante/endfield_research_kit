"""Resolve a reviewed anonymous assignment ABI for pure entry identities.

The caller and helper are re-proved on the selected NativeImage. No inferred
generic layout, arbitrary address selection or pointer dereference is admitted.
"""
from __future__ import annotations

from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import ClaimError
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.virtual_assignment import check_virtual_assignment


def resolve_assignment_entry(index: Any, hook: dict[str, Any], *,
                             caller_index: int, caller_pointer: int) -> dict[str, Any]:
    if hook.get("anonymousEntry") != {"kind": "virtualAssignment"} or hook.get("genericEntry") is not None:
        raise ClaimError("anonymous assignment requires an explicit virtualAssignment selection")
    contract, _ = read_reviewed_contract(CONTRACTS_DIR / "buff_action_consumers_native.json",
        schema="endfield.buff-action-consumer-claims.v2", status="reviewed", label="assignment_entry")
    candidates = [item for group in contract["groups"].values() for item in group["methods"].values()
                  if item["type"] == hook["type"] and item["method"] == hook["method"]
                  and item.get("parameters") == [p["type"] for p in hook["parameters"]]]
    claims = [claim["dispatchesVirtualAssignment"] for item in candidates for claim in item["claims"]
              if "dispatchesVirtualAssignment" in claim]
    if len(claims) != 1 or claims[0].get("dataIsCallerReceiver") is not True:
        raise ClaimError("anonymous assignment requires one reviewed caller/data/environment claim")
    spec = claims[0]
    body = index.body(hook["type"], hook["method"], parameters=[p["type"] for p in hook["parameters"]])
    if body.pointer != caller_pointer:
        raise ClaimError("anonymous assignment caller pointer differs from exact selected signature")
    proof: dict[str, Any] = {}
    failure = check_virtual_assignment(index, body, spec, proof=proof)
    if failure:
        raise ClaimError(failure)
    pointer = proof["pointer"]
    if index.names_of(pointer):
        raise ClaimError("anonymous assignment entry acquired a named alias")
    base_type = spec["base"].rsplit(".", 1)[0]
    data_type, environment_type = spec["implementation"]["parameters"]
    if data_type != hook["type"] or hook["static"] or len(hook["parameters"]) != 1 or hook["parameters"][0] != {
            "name": spec["environmentParameter"], "type": environment_type}:
        raise ClaimError("anonymous assignment caller receiver/environment signature drift")
    abi = {"name": hook["name"], "type": hook["type"], "static": True,
           "parameters": [{"name": "unusedContext", "type": "ulong"},
                          {"name": "action", "type": base_type},
                          {"name": "data", "type": data_type},
                          {"name": "environment", "type": environment_type}]}
    expected = {"suppliedActionIdentity": ("action", base_type),
                "suppliedDataIdentity": ("data", data_type),
                "suppliedEnvironmentIdentity": ("environment", environment_type)}
    fields = hook["fields"]
    if len(fields) != 3 or {field["label"] for field in fields} != set(expected):
        raise ClaimError("anonymous assignment requires exactly the three reviewed identity fields")
    for field in fields:
        if (expected[field["label"]] != (field["argument"], field["type"])
                or field.get("valueRepresentation") != "referenceIdentity"
                or field.get("path") or field.get("argumentRepresentation") is not None):
            raise ClaimError("anonymous assignment accepts pure register identities only; field/ABI drift")
    proof["callerMethodIndex"] = caller_index
    return {"pointer": pointer, "abi": abi, "proof": proof}
