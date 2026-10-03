"""Audit entry snapshots at the reviewed native owner/carrier control boundary.

The selected native loader supplies the declaration. This pure projection never
opens binaries, joins separate pointer generations or reads media/path bytes.
"""
from __future__ import annotations

from collections import Counter
import json
import math
import re
import sys
from typing import Any, Callable


SCHEMA = "endfield.audio-owner-carrier-relations.v1"
DECLARATION_SCHEMA = "endfield.wwise-owner-carrier-observer.v1"
MAX_SAMPLES = 48
BOUNDARY = (
    "Entry-only fixed-field snapshots at the reviewed command-4 control callsite. "
    "A captured decoder owner equals the captured primary-owner argument, whose selected address point "
    "and stored source are checked in that same entry. Snapshots are not atomic and do not prove which "
    "internal branch executed. No cross-call generation/lifetime, managed request ownership, decoder "
    "creation, file identity, text/media interpretation, codec/decode success or audibility is established."
)


def _pointer(value: Any) -> int | None:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-fA-F]{1,16}", value) is None:
        return None
    number = int(value, 16)
    return number if number < 0x800000000000 else None


def _rva(value: Any) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-fA-F]{1,8}", value) is None:
        raise ValueError("expected bounded hexadecimal RVA")
    return int(value, 16)


def audit_owner_carrier_relations(
    admitted: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]],
    hooks: dict[str, dict[str, Any]], profile: dict[str, Any],
    module_facts: dict[str, list[dict[str, Any]]], declaration: dict[str, Any] | None,
    issue: Callable[..., None],
) -> dict[str, Any]:
    """Validate all candidates before applying the independent display cap."""
    if declaration is None:
        return {}
    spec = declaration
    try:
        if spec.get("schema") != DECLARATION_SCHEMA or spec.get("memorySamplePhase") != "entry":
            raise ValueError("missing reviewed entry-only owner/carrier declaration")
        role = spec["roles"]["carrierCommand4"]
        hook = hooks[role["sourceKind"]]
        if (hook["rva"] != role["entryRva"] or hook.get("returnKind") != role["returnKind"]
                or json.dumps(hook["args"], sort_keys=True) != json.dumps(role["args"], sort_keys=True)
                or profile["nativeModuleName"] != spec["moduleName"]):
            raise ValueError("profile differs from authenticated control role")
        _rva(role["entryRva"])
        expected_point = _rva(spec["primaryAddressPointRva"])
        callers = spec["callers"]["carrierCommand4"]
        if not isinstance(callers, list) or not 1 <= len(callers) <= 8:
            raise ValueError("missing bounded control callsites")
        expected_callers = {_rva(value) for value in callers}
        source_offset = spec["sourcePointerOffset"]
        if type(source_offset) is not int or not 0 <= source_offset <= 4096:
            raise ValueError("invalid stored-source offset")

        def field(argument: str, offset: int, kind: str, chain: list[int] | None = None) -> str:
            if type(offset) is not int or not 0 <= offset <= 4096:
                raise ValueError("unbounded field offset")
            arg = role["args"][argument]
            if arg.get("kind") != "pointer" or type(arg.get("index")) is not int or not 0 <= arg["index"] <= 3:
                raise ValueError("invalid declared pointer argument")
            found = [read["name"] for read in hook["memory"]
                     if type(read["argIndex"]) is int and read["argIndex"] == arg["index"] and read["kind"] == kind
                     and type(read["offset"]) is int and read["offset"] == offset
                     and isinstance(read.get("pointerOffsets", []), list)
                     and all(type(value) is int and 0 <= value <= 4096 for value in read.get("pointerOffsets", []))
                     and read.get("pointerOffsets", []) == (chain or [])
                     and read.get("samplePhase") == "entry"]
            if len(found) != 1:
                raise ValueError("missing or ambiguous entry field")
            return found[0]

        carrier, decoder, owner = (spec["layouts"][name] for name in ("carrier", "decoder", "primaryOwner"))
        point_field = field("primaryOwnerPointer", owner["addressPoint"]["offset"], "pointer")
        source_field = field("primaryOwnerPointer", source_offset, "pointer")
        sides = {}
        for side in ("current", "pending"):
            offset = carrier[side + "DecoderPointer"]["offset"]
            sides[side] = (field("carrierPointer", offset, "pointer"),
                           field("carrierPointer", decoder["primaryOwnerPointer"]["offset"], "pointer", [offset]))
        source_fields = spec["sourceFields"]
        if not isinstance(source_fields, list) or not 1 <= len(source_fields) <= 16:
            raise ValueError("missing bounded fixed source fields")
        source_map, source_kinds = {}, {}
        for row in source_fields:
            name = row["name"]
            if (not isinstance(name, str) or not 1 <= len(name) <= 96 or name in source_map
                    or row["kind"] not in ("u32", "pointer")):
                raise ValueError("invalid fixed source field")
            source_map[name] = field("primaryOwnerPointer", row["offset"], row["kind"], [source_offset])
            source_kinds[name] = row["kind"]
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        issue("ownerCarrierDeclaration", expected="authenticated bounded entry-only fields", actual=str(error)[:160])
        return {}

    def relative(session: str, value: Any) -> int | None:
        pointer = _pointer(value)
        if pointer is None or pointer == 0:
            return None
        found = []
        for fact in module_facts.get(session, []):
            base = _pointer(fact.get("base"))
            if fact.get("moduleName") == spec["moduleName"] and base and type(fact.get("size")) is int:
                delta = pointer - base
                if 0 <= delta < fact["size"]:
                    found.append(delta)
        return found[0] if len(found) == 1 else None

    totals, unresolved = Counter(), Counter()
    samples = []
    for (session, capture_id), (call, result) in admitted.items():
        if call.get("sourceKind") != role["sourceKind"]:
            continue
        totals["controlPairCount"] += 1
        times = [row.get("monotonicMs") for row in (call, result)]
        if (any(type(value) not in (int, float) or not 0 <= value < sys.float_info.max or not math.isfinite(value) for value in times)
                or times != sorted(times)):
            issue("ownerCarrierPairTime", call, expected="finite nondecreasing entry/result times", actual=times)
            continue
        values, args = call.get("memory"), call.get("decodedArguments")
        if not isinstance(values, dict) or not isinstance(args, dict):
            issue("ownerCarrierSnapshot", call, field="entry", expected="memory and argument objects",
                  actual={"memory": type(values).__name__, "arguments": type(args).__name__})
            continue
        malformed = False

        def check(value: Any, name: str, kind: str, active: bool = True, nonzero: bool = False) -> bool:
            nonlocal malformed
            if not active:
                valid = name in values and value is None
            elif kind == "pointer":
                pointer = _pointer(value)
                valid = pointer is not None and (not nonzero or pointer != 0)
            else:
                valid = type(value) is int and 0 <= value <= 0xffffffff
            if not valid:
                malformed = True
                issue("ownerCarrierSnapshot", call, field=name,
                      expected="explicit inactive null" if not active else "nonzero pointer" if nonzero else kind,
                      actual=repr(value)[:160])
            return valid

        for name, arg in role["args"].items():
            check(args.get(name), name, "pointer", nonzero=arg.get("allowNull") is not True)
        if malformed:
            continue
        owner_pointer = _pointer(args["primaryOwnerPointer"])
        carrier_pointer = _pointer(args["carrierPointer"])
        check(values.get(point_field), point_field, "pointer", bool(owner_pointer))
        check(values.get(source_field), source_field, "pointer", bool(owner_pointer))
        for pointer_field, owner_field in sides.values():
            if check(values.get(pointer_field), pointer_field, "pointer", bool(carrier_pointer)):
                check(values.get(owner_field), owner_field, "pointer", bool(_pointer(values.get(pointer_field))))
        source_pointer = values.get(source_field)
        for name, memory_name in source_map.items():
            check(values.get(memory_name), memory_name, source_kinds[name], bool(_pointer(source_pointer)))
        if malformed:
            continue
        if relative(session, call.get("nativeReturnAddress")) not in expected_callers:
            unresolved["outsideReviewedCommand4Callsite"] += 1
            continue
        if not owner_pointer:
            unresolved["nullPrimaryOwner"] += 1
            continue
        if relative(session, values.get(point_field)) != expected_point:
            unresolved["unreviewedPrimaryOwnerAddressPoint"] += 1
            continue
        totals["reviewedOwnerPairCount"] += 1
        side_values = {side: {"decoderPointer": values.get(fields[0]), "decoderOwnerPointer": values.get(fields[1])}
                       for side, fields in sides.items()}
        matched = [side for side, values_at_side in side_values.items()
                   if _pointer(values_at_side["decoderPointer"]) and _pointer(values_at_side["decoderOwnerPointer"]) == owner_pointer]
        if not matched:
            unresolved["noMatchingDecoderOwnerSnapshot"] += 1
            continue
        if not _pointer(source_pointer):
            unresolved["nullStoredSource"] += 1
            continue
        # Current has comparison precedence in the native handler. This labels
        # the snapshot; observing entry is not observing its later branch.
        side = matched[0]
        totals["ownerDecoderSnapshotMatchCount"] += 1
        totals[side + "SnapshotMatchCount"] += 1
        if len(samples) < MAX_SAMPLES:
            samples.append({"sessionId": session, "controlCaptureId": capture_id, "threadId": call["threadId"],
                            "sequence": [call["seq"], result["seq"]], "monotonicMs": times,
                            "callerRva": hex(relative(session, call["nativeReturnAddress"])),
                            "primaryOwnerAddressPointRva": hex(expected_point),
                            "primaryOwnerPointer": args["primaryOwnerPointer"], "carrierPointer": args["carrierPointer"],
                            "storedSourcePointer": source_pointer, "selectedSnapshotSide": side,
                            "matchingSnapshotSides": matched, "decoderSnapshots": side_values,
                            "sourceSnapshot": {name: values.get(memory_name) for name, memory_name in source_map.items()}})
    return {"schema": SCHEMA, **{name: totals[name] for name in (
                "controlPairCount", "reviewedOwnerPairCount", "ownerDecoderSnapshotMatchCount",
                "currentSnapshotMatchCount", "pendingSnapshotMatchCount")},
            "unresolvedCounts": dict(sorted(unresolved.items())), "samples": samples,
            "sampleLimit": MAX_SAMPLES,
            "samplesTruncated": totals["ownerDecoderSnapshotMatchCount"] > len(samples),
            "evidenceBoundary": BOUNDARY}
