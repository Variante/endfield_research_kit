"""Buff-owned composition receipts; cursor closure is not recursive naming proof.

This layer deliberately cannot promote the legacy suffix's endpoint searches or
the anonymous native profiles into a whole named schema. It records the next
proof obligations separately from physical bytes still opaque after composition.
"""
from __future__ import annotations

from collections import Counter


def _merge(ranges, length):
    result = []
    for start, end in sorted(ranges):
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= length:
            raise ValueError(f"buff-receipt:invalid-range={start!r},{end!r}; length={length}")
        if start == end:
            continue
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def suffix_opaque_ranges(decoded, *, length):
    """Retain nested bodies even when the enclosing suffix reaches EOF."""
    ranges = []
    for name, owner in [(name, decoded) for name in (
        "igniteEventAction", "poiseModifier", "shieldConfigs", "timelineActions"
    )] + [("stackEffects", decoded.get("stackingSettings") or {})]:
        if not owner.get(name + "BodyStatus") or owner.get(name + "BodyStatus") == "skipped-zero-action-items":
            continue
        start = owner.get(name + "BodyOffset")
        size = owner.get(name + "BodyBytes")
        if isinstance(start, str):
            start = int(start, 0)
        if type(start) is not int or type(size) is not int:
            raise ValueError(f"buff-receipt:missing-opaque-body-range={name}")
        _merge([(start, start + size)], length)
        ranges.append({"start": start, "end": start + size,
                       "field": "stackingSettings.stackEffects" if name == "stackEffects" else name,
                       "kind": "opaque-nested-body"})
    return ranges


def compose_opaque_ranges(candidate, *, length):
    """Subtract downstream cursor coverage from stage-local remainders once.

Opaque nested bodies are then restored. Anonymous but exactly framed scalar
bytes are accounted by the naming receipt, not mislabeled unconsumed bytes.
"""
    covered = []
    for key in ("currentEventPrefix", "currentRootContinuation"):
        covered.extend((r["start"], r["end"]) for r in (candidate.get(key) or {}).get("ranges", []))
    middle = candidate.get("currentNamedMiddle") or {}
    covered.extend((f["start"], f["end"]) for f in middle.get("namedFields", [])
                   if f.get("boundaryClass") == "exact-cursor")
    suffix = candidate.get("currentNamedSuffix") or {}
    if suffix.get("status") == "named-exact-to-eof":
        if suffix.get("endOffset") != length:
            raise ValueError("buff-receipt:suffix-not-at-physical-eof")
        covered.append((suffix["startOffset"], length))
    merged = _merge(covered, length)
    unresolved = []
    cursor = 0
    for start, end in merged:
        if cursor < start:
            unresolved.append((cursor, start))
        cursor = end
    if cursor < length:
        unresolved.append((cursor, length))
    unresolved.extend((r["start"], r["end"]) for r in middle.get("opaqueNestedRanges", []))
    unresolved.extend((r["start"], r["end"]) for r in suffix.get("opaqueNestedRanges", []))
    return [{"start": start, "end": end, "kind": "composed-unresolved"}
            for start, end in _merge(unresolved, length)]


def named_schema_receipt(candidate, *, source, length):
    """Explain why the composed outer frame does not yet own all named leaves."""
    prefix = candidate.get("currentEventPrefix") or {}
    root = candidate.get("currentRootContinuation") or {}
    middle = candidate.get("currentNamedMiddle") or {}
    suffix = candidate.get("currentNamedSuffix") or {}
    fields = [dict(field) for profile in (prefix, root, middle)
              for field in profile.get("namedFields", [])]
    blockers = []

    def block(field, category, start=None, end=None):
        blockers.append({"field": field, "category": category,
                         "start": start, "end": end})

    unions = [record for profile in (prefix, root)
              for record in profile.get("completedRecords", []) if record.get("kind") == "union"]
    for field in fields:
        name = field["name"]
        nested_unions = [record for record in unions
                         if field["start"] <= record["start"] < field["end"]]
        child = field.get("nestedProfile") or {}
        field["recursiveNamedSchemaExact"] = (
            (name == "iconConfig" and middle.get("iconConfigStatus") == "exact")
            or (name == "addingCooldown" and child.get("wholeValueExact") is True
                and child.get("status") in ("exact", "exact-null")
                and child.get("startOffset") == field["start"]
                and child.get("consumedEnd") == field["end"])
            or (name == "dispelConfig" and child.get("wholeValueExact") is True
                and child.get("status") == "exact"
                and child.get("startOffset") == field["start"]
                and child.get("consumedEnd") == field["end"])
        )
        if nested_unions:
            block(name, "anonymous-action-interior", field["start"], field["end"])
        if name in ("damageModifier", "globalModifier", "healModifier") and field.get("count", 0) > 0:
            block(name, "positive-modifier-recursive-proof", field["start"], field["end"])
        if name == "addingCooldown" and field["end"] - field["start"] > 1 and not field["recursiveNamedSchemaExact"]:
            block(name, "anonymous-blackboard-member-ownership", field["start"], field["end"])
        if name == "dispelConfig" and not field["recursiveNamedSchemaExact"]:
            block(name, "raw8-member-ownership", field["start"], field["end"])
    for field in suffix.get("opaqueNestedFields", []):
        block(field, "opaque-suffix-interior")
    if suffix:
        stacking_child = suffix.get("stackingSettingsNativeChild") or {}
        tag_child = suffix.get("tagArrayNativeChild") or {}
        if (stacking_child.get("status") != "exact-child-cursor"
                or tag_child.get("status") != "exact-raw-array"
                or stacking_child.get("consumedEnd") != tag_child.get("startOffset")):
            block("stackingSettings", "compact-branch-native-ownership")
        if (tag_child.get("status") != "exact-raw-array"
                or stacking_child.get("consumedEnd") != tag_child.get("startOffset")):
            block("tagsAfterTriggerExtendBuffAction", "alternate-representation-native-ownership")
        timeline_child = suffix.get("timelineEmptyNativeChild") or {}
        if (timeline_child.get("status") != "exact-null-or-empty-list-to-eof"
                or timeline_child.get("count") not in (-1, 0)
                or timeline_child.get("startOffset") != tag_child.get("consumedEnd")
                or timeline_child.get("consumedEnd") != timeline_child.get("startOffset", -5) + 4
                or timeline_child.get("consumedEnd") != timeline_child.get("followingStart")
                or timeline_child.get("followingEnd") != length):
            block("timelineActions", "suffix-fallback-ownership")
    if len(fields) != 15 or [field["index"] for field in fields] != list(range(15)):
        block("root", "incomplete-forward-prefix")
    if not suffix:
        block("id", "suffix-not-closed")
    # Existing contracts authenticate anonymous reads and the icon wrapper.
    # They do not authenticate all other named leaves. Do not fabricate a
    # successful branch merely from the lack of action/modifier frontiers.
    block("root", "recursive-name-authentication-incomplete")
    opaque = compose_opaque_ranges(candidate, length=length)
    return {
        "schema": "endfield.buff-named-schema-receipt.v1",
        "source": source,
        "status": "blocked",
        "wholeSchemaExact": False,
        "physicalEof": length,
        "forwardNamedFields": fields,
        "suffixFieldOrder": suffix.get("namedFieldOrder", []),
        "actionUnionCount": len(unions),
        "hasConservativeSuffixFrontier": bool(suffix.get("opaqueNestedFields")),
        "composedOpaqueBytes": sum(row["end"] - row["start"] for row in opaque),
        "blockers": blockers,
        "firstBlocker": blockers[0],
        "evidenceBoundary": "Composed cursor coverage and explicit naming obligations; no new native facts or whole-schema promotion.",
    }


def summarize_receipts(rows):
    receipts = [candidate["namedSchemaReceipt"] for row in rows
                for candidate in row.get("candidates", []) if candidate.get("namedSchemaReceipt")]
    simple = [r for r in receipts if not r["actionUnionCount"] and not r["hasConservativeSuffixFrontier"]]
    return {
        "receipts": len(receipts),
        "wholeSchemaExact": sum(r["wholeSchemaExact"] for r in receipts),
        "withoutActionOrSuffixFrontier": len(simple),
        "firstBlockerCounts": dict(sorted(Counter(r["firstBlocker"]["category"] for r in receipts).items())),
        "blockerCounts": dict(sorted(Counter(b["category"] for r in receipts for b in r["blockers"]).items())),
        "simpleSubsetModifierBlockers": dict(sorted(Counter(
            b["field"] for r in simple for b in r["blockers"]
            if b["category"] == "positive-modifier-recursive-proof").items())),
    }
