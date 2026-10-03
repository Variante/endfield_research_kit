"""Native-gated named BlackboardDouble operands of a stored CompareFloat action.

The parent reader owns each valueA/valueB field and its physical endpoint.
The independent addingCooldown reader owns the same three-member
BlackboardDouble wire shape and generated setter order. This composition
replays the parent and both children from source-hash-checked bytes. It
closes stored member ownership only: key/value bytes stay raw, and neither
runtime comparison nor the enclosing condition or BuffData root is admitted.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack import buff_adding_cooldown as child
from scripts.game_data.memorypack import buff_compare_float_action_receipt as parent


SCHEMA = "endfield.buff-compare-float-blackboard-children-receipt.v1"
LABEL = "buffCompareFloatBlackboardChildren"
DOUBLE_TYPE = "Beyond.Blackboard+BlackboardDouble"


def _bindings(parent_native: dict[str, Any]) -> list[str]:
    source, _catalog = parent._contracts()
    names = parent_native.get("memberNames", [])
    kinds = parent_native.get("readKinds", [])
    if len(names) != len(kinds) or kinds != source["anonymousReadOrder"]["member7"]:
        raise ValueError(f"{LABEL}.native:parent-read-order")
    fields = [name for name, kind in zip(names, kinds, strict=True)
              if kind == "scalar-payload"]
    contexts = source["nestedContexts"]
    joins = parent_native.get("scalarChildren", [])
    if (len(fields) != 2 or len(set(fields)) != len(fields)
            or len(contexts) != len(fields) or len(joins) != len(fields)
            or any(context["typeName"] != DOUBLE_TYPE
                   or join.get("fieldName") != name
                   or join.get("typeName") != context["typeName"]
                   or join.get("methodSpecIndex") != context["methodSpecIndex"]
                   or join.get("instructionRva") != context["instructionRva"]
                   for name, context, join in zip(fields, contexts, joins, strict=True))):
        raise ValueError(f"{LABEL}.native:typed-child-join")
    return fields


def validate_current_native_contract(*, gameassembly: Path | None = None,
                                    metadata: Path | None = None) -> dict[str, Any]:
    """Require independently authenticated parent calls and child field order."""
    child_native = child.validate_current_native_contract(gameassembly=gameassembly, metadata=metadata)
    if child_native.get("status") != "validated":
        raise ValueError(
            f"{LABEL}.native:child expected=validated "
            f"actual={child_native.get('status')} detail={str(child_native.get('detail', ''))[:500]}"
        )
    contract = child._contract()
    if child_native.get("selectedReadOrder") != contract["selectedReadOrder"]:
        raise ValueError(f"{LABEL}.native:child-setter-order")
    parent_native = parent.validate_current_native_contract(gameassembly=gameassembly, metadata=metadata)
    expected = {name: contract["nativeInputs"][name]
                for name in ("GameAssembly.dll", "global-metadata.dat")}
    if (parent_native.get("status") != "validated"
            or parent_native.get("unionTag") != parent.TAG
            or parent_native.get("nativeInputs") != expected):
        raise ValueError(f"{LABEL}.native:parent-or-build-drift")
    return {"status": "validated", "nativeInputs": expected,
            "parentNative": parent_native, "childNative": child_native,
            "bindings": _bindings(parent_native),
            "memberNames": list(child_native["selectedReadOrder"])}


def decode_compare_float_blackboard_children(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse a certified CompareFloat and name both exact operand spans."""
    child_native = native_validation.get("childNative", {})
    parent_native = native_validation.get("parentNative", {})
    if (native_validation.get("status") != "validated"
            or child_native.get("status") != "validated"
            or parent_native.get("status") != "validated"):
        raise ValueError(
            f"{LABEL}.native:expected=validated actual={native_validation.get('status')} "
            f"source={source} range=[{start},{end})"
        )
    expected = {name: child._contract()["nativeInputs"][name]
                for name in ("GameAssembly.dll", "global-metadata.dat")}
    names = child._contract()["selectedReadOrder"]
    bindings = _bindings(parent_native)
    if (native_validation.get("nativeInputs") != expected
            or parent_native.get("nativeInputs") != expected
            or native_validation.get("bindings") != bindings
            or native_validation.get("memberNames") != names
            or child_native.get("selectedReadOrder") != names):
        raise ValueError(f"{LABEL}.native:composition-drift source={source}")
    try:
        receipt = parent.decode_compare_float_action_receipt(
            data, source=source, logical_sha256=logical_sha256,
            start=start, end=end, native_validation=parent_native,
        )
    except ValueError as exc:
        raise ValueError(
            f"{LABEL}:parent source={source} range=[{start},{end}) "
            f"sha256Expected={str(logical_sha256)[:64]} "
            f"sha256Actual={hashlib.sha256(data).hexdigest().upper()} "
            f"detail={str(exc)[:500]}"
        ) from exc
    if (receipt.get("status") != "named-wrapper-exact-span"
            or receipt.get("schema") != parent.SCHEMA
            or receipt.get("tag") != parent.TAG
            or receipt.get("wholeActionByteSpanExact") is not True
            or receipt.get("start") != start or receipt.get("end") != end
            or receipt.get("source") != source
            or receipt.get("logicalSha256") != logical_sha256.upper()):
        raise ValueError(f"{LABEL}:parent-receipt-drift source={source}")
    children = []
    for binding in bindings:
        matches = [row for row in receipt["namedFields"]
                   if row["fieldName"] == binding and row["kind"] == "scalar-payload"]
        if len(matches) != 1:
            raise ValueError(f"{LABEL}:operand-field field={binding} source={source}")
        field = matches[0]
        try:
            decoded = child.decode_adding_cooldown(
                data, field["start"], field["end"], native_validation=child_native,
            )
        except ValueError as exc:
            raise ValueError(
                f"{LABEL}:operand field={binding} source={source} "
                f"sha256={logical_sha256.upper()} range=[{field['start']},{field['end']}) "
                f"detail={str(exc)[:500]}"
            ) from exc
        if (decoded.get("wholeValueExact") is not True
                or decoded.get("startOffset") != field["start"]
                or decoded.get("consumedEnd") != field["end"]
                or (decoded.get("fields")
                    and [row["name"] for row in decoded["fields"]] != names)):
            raise ValueError(f"{LABEL}:operand-end field={binding} source={source}")
        children.append({"parentField": binding,
                         "start": field["start"], "end": field["end"],
                         "providerType": DOUBLE_TYPE, "child": decoded,
                         "wholeStoredSpanExact": True})
    if children[0]["end"] != children[1]["start"] or children[-1]["end"] != end:
        raise ValueError(f"{LABEL}:operand-tiling source={source}")
    return {"schema": SCHEMA, "status": "named-stored-operands-exact-span",
            "source": source, "logicalSha256": logical_sha256.upper(),
            "parentTag": parent.TAG, "parentActionRange": [start, end],
            "parent": receipt, "children": children,
            "wholeOperandByteSpansExact": True,
            "wholeActionRecursiveSchemaExact": False,
            "wholeConditionExact": False, "wholeBuffDataExact": False,
            "evidenceBoundary": (
                "Direct stored operand ownership and exact member spans from the "
                "independent parent typed calls and child native reader/setter order. "
                "Key, flag and scalar bytes stay raw; no runtime provider, comparison, "
                "condition result or whole BuffData admission."
            )}
