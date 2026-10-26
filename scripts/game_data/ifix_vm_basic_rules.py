"""Authenticate and project the selected IFix VM's basic stack operations.

The caller owns selected-native, complete Execute-body and referenced parent
method authentication. This module proves a finite instruction dispatch and reviewed effect windows, then
projects authored operands. It never interprets arbitrary VM code or claims
execution. Conv_I8 branches are conditional on the tag after the selected
reference resolver returns normally; hardware exception state stays unresolved.
"""
from __future__ import annotations

import hashlib
import struct
from typing import Any

from scripts.game_data.il2cpp.protocol import enum_members, field_defaults


class BasicRuleEvidenceError(ValueError):
    """The supplied native bytes or basic-rule declaration did not validate."""


_EFFECTS = {
    "Ldc_I4": "push-int32-operand",
    "Ldnull": "push-null-object",
    "Pop": "discard-and-clear-slot",
    "Nop": "advance-only",
    "Conv_I8": "convert-resolved-numeric-value-to-long-or-enter-runtime-exception",
}
_CONTROL_EDGES = {
    "pcAdvance": ("call", "advancePointer"), "pushAdvance": ("call", "advancePointer"),
    "popSubtract": ("call", "subtractSlot"), "clearPointerDifference": ("call", "pointerDifference"),
    "clearManagedStore": ("call", "managedStore"), "nullPointerDifference": ("call", "pointerDifference"),
    "nullManagedStore": ("call", "managedStore"), "literalTail": ("jump", "integerStore"),
    "literalPushTail": ("jump", "pushAdvance"), "nullPushTail": ("jump", "integerStore"),
    "popClearTail": ("jump", "managedClear"), "clearPcTail": ("jump", "pcAdvance"),
    "integerPcTail": ("jump", "pcAdvance"), "preconversionCall": ("call", "preconversionMethod"),
    "integerTypeBranch": ("je", "integerConversion"),
    "longTypeBranch": ("je", "longAdvance"), "floatTypeBranch": ("je", "floatingConversion"),
    "doubleTypeBranch": ("je", "floatingConversion"),
    "floatingConversionCall": ("call", "truncateDoubleToInt64"),
    "doubleFloatingJoin": ("jump", "floatingConversion"),
    "floatingStoreJoin": ("jump", "integerConversion"),
    "longAdvanceCall": ("call", "advancePointer"), "longPcTail": ("jump", "loopState"),
    "unsupportedRuntimeException": ("call", "runtimeExceptionMethod"),
    "unsupportedStoreJoin": ("jump", "floatingConversion"),
}
_CONVERSION_BRANCHES = {
    "Integer": "sign-extend-int32-and-store-Long",
    "Long": "advance-without-conversion-store",
    "Float": "widen-low-float-to-double-then-truncate-to-int64-and-store-Long",
    "Double": "truncate-low-double-to-int64-and-store-Long",
    "other": "runtime-exception-route-then-zero-Long-only-if-it-returns-normally",
}


def _rva(value: Any) -> int:
    return int(value, 16) if isinstance(value, str) else int(value)


def _slice(body: bytes, body_rva: int, rva: int, count: int, label: str) -> bytes:
    offset = rva - body_rva
    if count <= 0 or not 0 <= offset <= len(body) - count:
        raise BasicRuleEvidenceError(
            f"basic-rules {label}: outside body rva=0x{rva:x} bytes={count}"
        )
    return body[offset:offset + count]


def resolve_dispatch_entry(
    body: bytes, body_rva: int, start_rva: int, opcode_id: int,
) -> int:
    """Walk only immediate ECX cmp/sub and signed/equality conditional branches.

    The first instruction outside this finite dispatch grammar is the selected
    entry. Unsupported arithmetic, branches, repeated PCs, or out-of-body paths
    fail closed. The caller checks the returned entry against its reviewed rule.
    No inferred jump-table order or opcode-name semantics enter this walk.
    """
    if not 0 <= opcode_id <= 0x7FFFFFFF:
        raise BasicRuleEvidenceError(f"basic-dispatch: invalid opcode id={opcode_id}")
    pc, value, flags, seen = start_rva, opcode_id, None, set()
    for _ in range(64):
        if pc in seen:
            raise BasicRuleEvidenceError(f"basic-dispatch: repeated rva=0x{pc:x}")
        seen.add(pc)
        prefix = _slice(body, body_rva, pc, 2, "dispatch")
        if prefix in (b"\x83\xf9", b"\x83\xe9", b"\x81\xf9", b"\x81\xe9"):
            width = 1 if prefix[0] == 0x83 else 4
            raw = _slice(body, body_rva, pc, 2 + width, "dispatch-immediate")
            immediate = int.from_bytes(raw[2:], "little", signed=True)
            difference = value - immediate
            flags = {"equal": difference == 0, "greater": value > immediate}
            if prefix[1] == 0xE9:
                value = ((difference + 0x80000000) & 0xFFFFFFFF) - 0x80000000
            pc += len(raw)
            continue
        if prefix in (b"\x0f\x84", b"\x0f\x85", b"\x0f\x8f", b"\x0f\x8e"):
            if flags is None:
                raise BasicRuleEvidenceError(f"basic-dispatch: branch before flags rva=0x{pc:x}")
            raw = _slice(body, body_rva, pc, 6, "dispatch-branch")
            condition = {0x84: flags["equal"], 0x85: not flags["equal"],
                         0x8F: flags["greater"], 0x8E: not flags["greater"]}[raw[1]]
            pc = pc + 6 + struct.unpack_from("<i", raw, 2)[0] if condition else pc + 6
            continue
        if prefix[0] in (0x74, 0x75, 0x7F, 0x7E):
            if flags is None:
                raise BasicRuleEvidenceError(f"basic-dispatch: branch before flags rva=0x{pc:x}")
            condition = {0x74: flags["equal"], 0x75: not flags["equal"],
                         0x7F: flags["greater"], 0x7E: not flags["greater"]}[prefix[0]]
            pc = pc + 2 + struct.unpack_from("<b", prefix, 1)[0] if condition else pc + 2
            continue
        # The selected entries begin with a reviewed move or pointer setup.
        # A foreign dispatch opcode cannot masquerade as a normal entry.
        if prefix in (b"\x49\x8b", b"\x48\x8b", b"\x8b\xd6", b"\x4c\x8b"):
            return pc
        raise BasicRuleEvidenceError(
            f"basic-dispatch: unsupported shape rva=0x{pc:x} bytes={prefix.hex()}"
        )
    raise BasicRuleEvidenceError("basic-dispatch: step bound exceeded")


def _rules(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if (spec.get("schema") != "endfield.ifix-vm-basic-rules.v2"
            or spec.get("evidenceBoundary") != "conditional"
            or spec.get("executionBoundary") != "unobserved"
            or spec.get("slotBytes") != 12 or spec.get("instructionBytes") != 8):
        raise BasicRuleEvidenceError("basic-rules: unsupported schema/boundary/width")
    rows = spec.get("rules", [])
    rules = {row.get("opcode"): row for row in rows}
    if len(rows) != len(rules) or set(rules) != set(_EFFECTS):
        raise BasicRuleEvidenceError("basic-rules: missing/duplicate/unknown opcode rule")
    for name, row in rules.items():
        if row.get("effect") != _EFFECTS[name]:
            raise BasicRuleEvidenceError(f"basic-rules {name}: unsupported effect")
        expected_windows = {"entry", "integerConversion", "floatingConversion", "longAdvance", "unsupportedTag"} if name == "Conv_I8" else {"entry"}
        names = [window.get("name") for window in row.get("windows", [])]
        if len(names) != len(set(names)) or set(names) != expected_windows:
            raise BasicRuleEvidenceError(f"basic-rules {name}: unsupported effect windows")
        if name == "Conv_I8" and row.get("tagBranches") != _CONVERSION_BRANCHES:
            raise BasicRuleEvidenceError("basic-rules Conv_I8: unsupported tag effects")
    return rules


def validate_basic_rules(
    image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], contract: dict[str, Any],
) -> dict[str, Any]:
    """Check selected dispatch, exact effect windows, helper bytes and type tags."""
    rules = _rules(spec)
    members = enum_members(image.metadata, field_defaults(image.metadata), "IFix.Core.ValueType")
    actual_types = {row["name"]: int(row["id"]) for row in members}
    expected_types = spec.get("valueTypeMembers")
    compiled_tags = {"Integer": 0, "Long": 1, "Float": 2, "Double": 3, "Object": 8}
    if (expected_types != compiled_tags
            or any(actual_types.get(name) != value for name, value in expected_types.items())):
        raise BasicRuleEvidenceError(
            f"basic-rules ValueType: expected={expected_types} actual="
            f"{ {name: actual_types.get(name) for name in ('Integer', 'Long', 'Float', 'Double', 'Object')} }"
        )
    shared = spec.get("sharedWindows", [])
    names = [window.get("name") for window in shared]
    if len(names) != len(set(names)) or set(names) != {
        "loopState", "zeroRegister", "slotWidth", "pcAdvance", "pushAdvance", "pushTopCommit", "integerStore", "managedClear",
    }:
        raise BasicRuleEvidenceError("basic-rules: unsupported shared windows")
    checked = []
    for label, windows in [("shared", shared)] + [(name, row["windows"]) for name, row in rules.items()]:
        for window in windows:
            rva, count = _rva(window["rva"]), int(window["byteCount"])
            raw = _slice(body, body_rva, rva, count, f"{label}.{window['name']}")
            actual = hashlib.sha256(raw).hexdigest().upper()
            if actual != str(window["sha256"]).upper():
                raise BasicRuleEvidenceError(
                    f"basic-rules {label}.{window['name']}: mismatched rva=0x{rva:x} "
                    f"expectedSha256={window['sha256']} actualSha256={actual}"
                )
            checked.append({"name": f"{label}.{window['name']}", "rva": hex(rva), "byteCount": count, "sha256": actual})
    helpers = spec.get("helpers", [])
    helper_names = [row.get("name") for row in helpers]
    if len(helper_names) != len(set(helper_names)) or set(helper_names) != {
        "subtractSlot", "pointerDifference", "advancePointer", "managedStore", "truncateDoubleToInt64",
    }:
        raise BasicRuleEvidenceError("basic-rules: unsupported helpers")
    for helper in helpers:
        rva, count = _rva(helper["rva"]), int(helper["byteCount"])
        if count <= 0:
            raise BasicRuleEvidenceError(f"basic-rules helper {helper['name']}: empty")
        raw = image.pe.bytes_at_va(image.pe.image_base + rva, count)
        actual = hashlib.sha256(raw).hexdigest().upper()
        if actual != str(helper["sha256"]).upper():
            raise BasicRuleEvidenceError(f"basic-rules helper {helper['name']}: mismatched rva=0x{rva:x} expectedSha256={helper['sha256']} actualSha256={actual}")
        if helper['name'] == 'truncateDoubleToInt64' and raw != bytes.fromhex('f2480f2cc0c3'):
            raise BasicRuleEvidenceError('basic-rules floating conversion: unsupported CVTTSD2SI helper')
    conversion = rules['Conv_I8']
    widen = _slice(body, body_rva, _rva(conversion['floatWidenRva']), 3, 'float-widen')
    if widen != bytes.fromhex('0f5ac0'):
        raise BasicRuleEvidenceError('basic-rules floating conversion: unsupported CVTPS2PD widening')
    if conversion.get('runtimeExceptionMethodRef') != 'delegateConstruction.methodCalls.nullFallbackException':
        raise BasicRuleEvidenceError('basic-rules conversion: unsupported exception method reference')
    exception_rows = [row for row in contract['delegateConstruction']['methodCalls'] if row['role'] == 'nullFallbackException']
    if len(exception_rows) != 1 or (exception_rows[0]['type'], exception_rows[0]['method']) != ('IFix.Core.VirtualMachine', 'throwRuntimeException'):
        raise BasicRuleEvidenceError('basic-rules conversion: parent exception identity differs')
    resolver = spec["preconversionMethod"]
    method_index = image.validate_method_row([
        resolver["methodIndex"], resolver["type"], resolver["method"], _rva(resolver["rva"]),
    ], label="basic-rules preconversion")
    method = image.metadata.methods[method_index]
    parameter_names = [image.metadata.string(row.name_index)
                       for row in image.metadata.parameters_for(method)]
    if (resolver["type"] != "IFix.Core.VirtualMachine"
            or resolver["method"] != "resolveStackReference"
            or parameter_names != ["value", "stackBase", "managedStack"]
            or method.parameter_count != resolver["parameterCount"]
            or f"0x{method.token:08x}" != resolver["token"]):
        raise BasicRuleEvidenceError("basic-rules preconversion: method identity/parameters differ")
    resolver_body = image.pe.bytes_at_va(image.pe.image_base + _rva(resolver["rva"]), resolver["bodyBytes"])
    actual_hash = hashlib.sha256(resolver_body).hexdigest().upper()
    if actual_hash != resolver["bodySha256"]:
        raise BasicRuleEvidenceError(f"basic-rules preconversion: mismatched expectedSha256={resolver['bodySha256']} actualSha256={actual_hash}")
    edges = spec.get("controlEdges", [])
    edge_names = [edge.get("name") for edge in edges]
    if len(edge_names) != len(set(edge_names)) or set(edge_names) != set(_CONTROL_EDGES):
        raise BasicRuleEvidenceError("basic-rules: unsupported control edges")
    targets = {row["name"]: _rva(row["rva"]) for row in helpers + shared}
    targets.update({"preconversionMethod": _rva(resolver["rva"]),
                    'runtimeExceptionMethod': _rva(exception_rows[0]['rva'])})
    targets.update({row['name']: _rva(row['rva']) for row in conversion['windows'] if row['name'] != 'entry'})
    for edge in edges:
        rva = _rva(edge["rva"])
        kind = edge["kind"]
        if (kind, edge["targetRef"]) != _CONTROL_EDGES[edge["name"]]:
            raise BasicRuleEvidenceError(f"basic-rules {edge['name']}: unsupported edge declaration")
        first = _slice(body, body_rva, rva, 1, edge['name'])[0]
        short = (kind == 'je' and first == 0x74) or (kind == 'jump' and first == 0xeb)
        width = 2 if short else (6 if kind == "je" else 5)
        raw = _slice(body, body_rva, rva, width, edge["name"])
        prefix = ({'je': b'\x74', 'jump': b'\xeb'}[kind] if short
                  else {"call": b"\xe8", "jump": b"\xe9", "je": b"\x0f\x84"}.get(kind))
        if prefix is None or not raw.startswith(prefix):
            raise BasicRuleEvidenceError(f"basic-rules {edge['name']}: unsupported edge shape rva=0x{rva:x}")
        expected = targets[edge["targetRef"]] + int(edge.get("targetOffset", 0))
        actual = rva + width + int.from_bytes(raw[len(prefix):], 'little', signed=True)
        if actual != expected:
            raise BasicRuleEvidenceError(f"basic-rules {edge['name']}: edge target expected=0x{expected:x} actual=0x{actual:x}")
    entries = []
    for name, row in rules.items():
        if opcode_ids.get(name) != row.get("opcodeId"):
            raise BasicRuleEvidenceError(f"basic-rules {name}: opcode id expected={row.get('opcodeId')} actual={opcode_ids.get(name)}")
        actual = resolve_dispatch_entry(body, body_rva, _rva(spec["dispatchStartRva"]), opcode_ids[name])
        expected = _rva(row["entryRva"])
        if actual != expected:
            raise BasicRuleEvidenceError(f"basic-rules {name}: dispatch entry expected=0x{expected:x} actual=0x{actual:x}")
        entries.append({"opcode": name, "opcodeId": opcode_ids[name], "entryRva": hex(actual)})
    return {"status": "validated_basic_rules", "entries": entries, "checkedWindows": checked,
            'conversionTagBranches': dict(conversion['tagBranches']),
            'conversionExceptionIdentityRef': conversion['runtimeExceptionMethodRef'],
            "evidenceBoundary": "conditional", "executionBoundary": "unobserved"}


def project_basic_rules(decoded: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Project authored basic operations without assuming stack state or execution."""
    rules = _rules(spec)
    result = []
    for method in decoded["methods"]:
        for instruction in method["instructions"]:
            name = instruction["name"]
            if name not in rules:
                continue
            rule = rules[name]
            if instruction["opcode"] != rule["opcodeId"]:
                raise BasicRuleEvidenceError(f"basic-rules {name}: decoded opcode differs from rule")
            operand = instruction["operandUnsigned"]
            if not isinstance(operand, int) or not 0 <= operand <= 0xFFFFFFFF:
                raise BasicRuleEvidenceError(f"basic-rules {name}: invalid unsigned operand")
            row = {"vmMethodIndex": method["index"], "instructionIndex": instruction["index"],
                   "offset": instruction["offset"], "opcode": name, "operandUnsigned": operand,
                   "operandConsumedByThisOpcode": name == "Ldc_I4", "effect": rule["effect"],
                   "evidenceBoundary": "conditional", "executionBoundary": "unobserved",
                   "normalNextInstructionDelta": 1}
            if name == "Ldc_I4":
                row.update({"literalInt32": operand if operand < 0x80000000 else operand - 0x100000000,
                            "stackDeltaSlots": 1, "resultValueType": "Integer"})
            elif name == "Ldnull":
                row.update({"stackDeltaSlots": 1, "resultValueType": "Object", "managedValue": None,
                            "objectIndexMeaning": "current-slot-minus-evaluation-base-divided-by-slot-bytes"})
            elif name == "Pop":
                row.update({"stackDeltaSlots": -1, "managedSlotCleared": "discarded-slot-evaluation-base-index"})
            elif name == "Nop":
                row["stackDeltaSlots"] = 0
                row["operandBoundary"] = "not read by Nop; another opcode may inspect the preceding instruction"
            else:
                row.update({"stackDeltaSlots": 0, "selectedWhen": "tag-after-resolveStackReference-normal-return",
                            "resultValueType": "Long-on-a-selected-normal-return-path",
                            "tagBranches": dict(rule['tagBranches']),
                            'hardwareBoundary': 'Floating-point exception mask/state and non-returning child effects are unobserved.'})
            result.append(row)
    return result
