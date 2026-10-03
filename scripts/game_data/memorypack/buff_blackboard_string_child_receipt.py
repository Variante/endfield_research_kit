"""Named bounded BlackboardString values and selected typed parent joins.

Raw payload bytes and the original flag byte are retained. This stored child
receipt does not decode text or choose a runtime Blackboard provider.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import struct
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.context_audit_memorypack import buff_tag76_read_order, buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.core import CONTRACTS_DIR

LABEL = "buffBlackboardStringChild"
SCHEMA = "endfield.buff-blackboard-string-child-receipt.v1"
CONTRACT_SCHEMA = "endfield.buff-blackboard-string-child-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_blackboard_string_child_native.json"
READ_ORDER = ("blackboardKey", "useBlackboardKey", "value")
READ_KINDS = ("byte-payload", "byte", "byte-payload")
STRING_TYPE = "Beyond.Blackboard+BlackboardString"

def _contract() -> dict[str, Any]:
    # Current bytes, rather than the path, identify cached parsed validation.
    return _parse_contract(CONTRACT_PATH.read_bytes())


@lru_cache(maxsize=4)
def _parse_contract(raw: bytes) -> dict[str, Any]:
    c = json.loads(raw)
    if not isinstance(c, dict) or c.get("schema") != CONTRACT_SCHEMA:
        raise ValueError(f"{LABEL}.contract:unsupported-schema")
    if c.get("status") != "exact-current-build":
        raise ValueError(f"{LABEL}.contract:unsupported-status")
    if (tuple(c.get("selectedReadOrder", ())) != READ_ORDER
            or tuple(c.get("readKinds", ())) != READ_KINDS
            or c.get("contextContract") != "il2cpp_context_audit_native.json"
            or c.get("contextReadOrder") != "selectedBuffTag76ReadOrder"
            or c.get("parentContract") != "buff_11f_native.json"
            or c.get("catalogContract") != "levelscript_union_tags.json"
            or [r.get("fieldName") for r in c.get("sourceReads", [])] != list(READ_ORDER)
            or [r.get("readKind") for r in c.get("sourceReads", [])] != list(READ_KINDS)
            or [r.get("methodName") for r in c.get("wrapper", {}).get("setterMethods", [])]
            != [f"set___{name}__" for name in READ_ORDER]):
        raise ValueError(f"{LABEL}.contract:shape-or-read-order")
    return c

def _call(image: Any, row: dict[str, Any]) -> None:
    raw = image.pe.bytes_at_va(image.pe.image_base + row["rva"], 5)
    if (raw[:1] != b"\xe8" or raw.hex().upper() != row["hex"]
            or row["rva"] + 5 + struct.unpack_from("<i", raw, 1)[0] != row["targetRva"]):
        raise ValueError(f"{LABEL}.native:source-or-setter-call")

def _setters(image: Any, definition: int, expected: list[dict[str, Any]]) -> None:
    actual = image.setter_methods(image.metadata.types[definition], parameter="typeIndex")
    if actual != [[r["methodIndex"], r["methodName"], r["typeIndex"]] for r in expected]:
        raise ValueError(f"{LABEL}.native:setter-order")
    for row in expected:
        ptr = image.pe.u64_at_va(int(image.registration["types"], 16) + row["typeIndex"] * 8)
        if (ptr != row["typePointerVa"]
                or image.pe.bytes_at_va(ptr, 16).hex().upper() != row["rawTypeHex"]
                or runtime_type_name(image.pe, image.metadata, ptr) != row["typeName"]):
            raise ValueError(f"{LABEL}.native:setter-type")

def validate_current_native_contract(*, gameassembly: Path | None = None,
                                     metadata: Path | None = None) -> dict[str, Any]:
    c = _contract(); pins = c["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
                                        gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins["UnityPlayer.dll"]:
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    context = json.loads((CONTRACTS_DIR / c["contextContract"]).read_bytes())
    if context["nativeInputs"] != pins:
        raise ValueError(f"{LABEL}.native:context-build-drift")
    selected = context["pins"][c["contextReadOrder"]]
    image = open_native_image(gate.gameassembly, gate.metadata)
    wrapper = c["wrapper"]; image.check_wrapper_inheritance(wrapper, label=LABEL)
    _setters(image, wrapper["typeDefinition"], [])
    _setters(image, wrapper["parentTypeDefinition"], wrapper["setterMethods"])
    for row in c["methods"]: image.validate_method_row(row, label=LABEL)
    image.check_windows(c["codeWindows"], label=LABEL)
    selected_audit = buff_tag76_read_order(image.pe, image.metadata, image.registration,
        image.instantiations, image.modules, image.owners, source=str(gate.gameassembly))
    for row, reference in zip(c["sourceReads"], selected["orderedCalls"][6:], strict=True):
        if [row["sourceCall"]["rva"], row["sourceCall"]["targetRva"]] != [int(x, 16) for x in reference]:
            raise ValueError(f"{LABEL}.native:child-source-order")
        _call(image, row["sourceCall"])
        image.check_instruction_windows([row["sourceResultStore"], row["setterWrite"]], label=LABEL)
    routes, route_audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    if route_audit.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:parent-routes-unvalidated")
    check = c["parents"]["checkSkillId"]; r = routes.get(check["unionTag"])
    if (r is None or r.wrapper_name != check["wrapperTypeName"]
            or list(r.member_order) != check["memberNames"] or r.inherited_member_count != 4
            or r.member_declared_types[-1] != check["fieldBinding"]["typeName"]
            or check["fieldBinding"]["elementTypeName"] != STRING_TYPE):
        raise ValueError(f"{LABEL}.native:check-skill-id-route")
    _setters(image, check["inheritedWrapperTypeDefinition"], check["inheritedSetterMethods"])
    _setters(image, check["wrapperTypeDefinition"], check["setterMethods"])
    for row in check["methods"]: image.validate_method_row(row, label=LABEL)
    image.check_windows(check["codeWindows"], label=LABEL)
    setters = check["inheritedSetterMethods"] + check["setterMethods"]
    for index, (read, write, setter, reference) in enumerate(zip(check["sourceCalls"], check["setterCalls"], setters, selected["orderedCalls"][1:6], strict=True)):
        if ([read["rva"], read["targetRva"]] != [int(x, 16) for x in reference]
                or read["rva"] >= write["rva"]
                or (index < 4 and write["rva"] >= check["sourceCalls"][index + 1]["rva"])
                or image.method_pointer_va(image.metadata.methods[setter["methodIndex"]]) != image.pe.image_base + write["targetRva"]):
            raise ValueError(f"{LABEL}.native:parent-source-setter-order")
        _call(image, read); _call(image, write)
    raise_c = c["parents"]["raiseTrainLevelEvent"]; r = routes.get(raise_c["unionTag"])
    if r is None or r.wrapper_name != raise_c["wrapperTypeName"] or r.inherited_member_count != 4:
        raise ValueError(f"{LABEL}.native:raise-train-route")
    _setters(image, raise_c["wrapperTypeDefinition"], raise_c["setterMethods"])
    source = json.loads((CONTRACTS_DIR / c["parentContract"]).read_bytes())
    parent_audit = buff_action_read_order(image.pe, image.metadata, image.registration,
        image.instantiations, image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / c["parentContract"])
    for binding in raise_c["fieldBindings"]:
        index = binding["memberIndex"]; ctx = source["nestedContexts"][binding["contextIndex"]]
        if (r.member_order[index] != binding["fieldName"] or r.member_declared_types[index] != STRING_TYPE
                or binding["typeName"] != STRING_TYPE or ctx["typeName"] != STRING_TYPE
                or ctx["typeDefinition"] != selected["elementDefinitionIndex"]
                or source["anonymousReadOrder"]["member8"][index] != "paired-payload"):
            raise ValueError(f"{LABEL}.native:raise-train-string-binding")
    return {"status":"validated", "nativeInputs":pins, "selectedReadOrder":list(READ_ORDER),
        "selectedReadOrderProof":selected_audit, "parents":{
            "checkSkillId":{"status":"validated", "unionTag":check["unionTag"],
                "memberNames":check["memberNames"], "readKinds":check["readKinds"],
                "fieldBinding":check["fieldBinding"]},
            "raiseTrainLevelEvent":{"status":"validated", "unionTag":raise_c["unionTag"],
                "fieldBindings":raise_c["fieldBindings"], "sourceReadOrderProof":parent_audit}},
        "evidenceBoundary":c["evidenceBoundary"]}

def decode_blackboard_string_value(data: bytes, *, source: str, logical_sha256: str,
        start: int, end: int, native_validation: dict[str, Any]) -> dict[str, Any]:
    c = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != c["nativeInputs"]
            or native_validation.get("selectedReadOrder") != list(READ_ORDER)):
        raise ValueError(f"{LABEL}:native-not-validated-or-drifted")
    if hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper():
        raise ValueError(f"{LABEL}:source-sha256-mismatch")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}:invalid-span")
    pos = start
    def take(length: int) -> bytes:
        nonlocal pos
        if length < 0 or pos + length > end: raise ValueError(f"{LABEL}:truncated-value")
        raw = data[pos:pos + length]; pos += length; return raw
    header = take(1)[0]; fields = []
    if header != 255:
        if header != 3: raise ValueError(f"{LABEL}:member-count")
        for name, kind in zip(READ_ORDER, READ_KINDS, strict=True):
            begin = pos
            if kind == "byte":
                raw = take(1); value = raw[0]
            else:
                length = struct.unpack("<i", take(4))[0]
                if length < -1: raise ValueError(f"{LABEL}:negative-payload-length")
                raw = take(max(0, length)); value = None if length == -1 else raw.hex().upper()
            fields.append({"fieldName":name,"kind":kind,"start":begin,"end":pos,"value":value,
                           "payloadEncoding":"unresolved"} if kind == "byte-payload" else
                          {"fieldName":name,"kind":kind,"start":begin,"end":pos,"value":value})
    if pos != end: raise ValueError(f"{LABEL}:trailing-bytes")
    return {"schema":SCHEMA,"status":"exact-null-wrapper" if header == 255 else "named-three-member-exact-span",
        "source":source,"logicalSha256":logical_sha256.upper(),"start":start,"end":end,
        "isNull":header == 255,"namedFields":fields,"wholeStoredSpanExact":True,
        "evidenceBoundary":c["evidenceBoundary"]}
