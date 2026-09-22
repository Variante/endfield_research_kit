"""Predict a MemoryPack union's tag assignment from the wrapper hierarchy.

``action_dispatcher`` walks the root AbilityActionData dispatcher's switch table
and reads each tag's route out of the selected build.  Nested unions -- the
selector families, the calculation and damage-processor bases -- have no such
walked table in reach: nothing in the image addresses their jump table with a
rip-relative load, so the same walk does not reach them.

Their membership and order are recoverable from metadata alone.  A union's
members are exactly the wrapper types that descend from its base wrapper, and
the tag is the member's position when those are ordered by a case-insensitive
comparison of the type each one wraps.

That rule is not assumed.  It is derived against the one union whose tags are
walked natively and re-checked on every run: the root union's 416 walked routes
must reproduce exactly, or this module reports a broken rule and returns
nothing.  It is additionally corroborated by the reviewed nested-union rows --
the selector subtype routes a timeline contract records, and the tag each
``finder``/``validator``/``postprocessor`` contract is filed under.

Evidence tier is ``structuralOnly``, deliberately below the dispatcher's
``direct``: a predicted tag is an ordering inference corroborated against walked
routes, not a route read out of the binary.  Where a walked route exists it wins;
this fills in only the unions the walk cannot reach, and a consumer that needs a
proven route still needs a contract.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.wrapper_members import (
    WrapperType,
    load_wrapper_members,
)
from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_union_subtypes.json"
# The union whose tags are walked natively, so the ordering rule can be checked
# against real routes rather than assumed.
ROOT_UNION = (
    "Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack"
)
# Deeper than this is a metadata cycle, not a hierarchy.
MAX_DESCENT_DEPTH = 32


def _sort_key(wrapper: WrapperType) -> str:
    """The comparison the generator orders a union's members by.

    Case-insensitive on the wrapped type's full name, including the ``+``
    nested-type separators; removing them changes the order.
    """
    return (wrapper.wrapped_type or "").lower()


def children_index(rows: dict[int, WrapperType]) -> dict[int, list[int]]:
    index: dict[int, list[int]] = {}
    for definition, wrapper in rows.items():
        parent = wrapper.parent_type_definition
        if parent is not None:
            index.setdefault(parent, []).append(definition)
    return index


def descendants(
    rows: dict[int, WrapperType], children: dict[int, list[int]], base: int
) -> list[int] | None:
    """Every wrapper below ``base``, or None when the hierarchy cycles."""
    found: list[int] = []
    seen: set[int] = {base}

    def walk(definition: int, depth: int) -> bool:
        if depth > MAX_DESCENT_DEPTH:
            return False
        for child in children.get(definition, ()):
            if child in seen:
                return False
            seen.add(child)
            found.append(child)
            if not walk(child, depth + 1):
                return False
        return True

    return found if walk(base, 0) else None


def union_tags(
    rows: dict[int, WrapperType], children: dict[int, list[int]], base: int
) -> dict[int, WrapperType] | None:
    """``{tag: wrapper}`` for one union base, or None when it cannot be ordered."""
    members = descendants(rows, children, base)
    if not members:
        return None
    if any(not rows[definition].wrapped_type for definition in members):
        # Without a wrapped type there is no comparison key and therefore no
        # defensible order; the union is reported unresolved instead.
        return None
    ordered = sorted(members, key=lambda definition: _sort_key(rows[definition]))
    return {tag: rows[definition] for tag, definition in enumerate(ordered)}


def check_rule_against_walked_routes(
    rows: dict[int, WrapperType], children: dict[int, list[int]]
) -> dict[str, Any]:
    """Re-derive the walked union and compare it tag for tag.

    This is the rule's own gate. A mismatch means the ordering no longer
    describes this build, so nothing derived from it should be trusted.
    """
    walked, audit = load_action_routes()
    if audit["status"] != "validated":
        return {"status": audit["status"], "detail": "walked routes unavailable",
                "checked": 0, "agreed": 0}
    base = next(
        (definition for definition, wrapper in rows.items() if wrapper.name == ROOT_UNION),
        None,
    )
    if base is None:
        return {"status": "root-union-missing", "checked": 0, "agreed": 0}
    predicted = union_tags(rows, children, base)
    if predicted is None:
        return {"status": "root-union-unorderable", "checked": 0, "agreed": 0}
    checked = agreed = 0
    disagreements: list[dict[str, Any]] = []
    for tag, route in sorted(walked.items()):
        if route.status != "resolved":
            continue
        checked += 1
        wrapper = predicted.get(tag)
        if wrapper is not None and wrapper.type_definition == route.wrapper_type_definition:
            agreed += 1
        elif len(disagreements) < 20:
            disagreements.append({
                "unionTag": tag,
                "walkedWrapper": route.wrapper_name,
                "predictedWrapper": wrapper.name if wrapper else None,
            })
    extra = sorted(set(predicted) - set(walked))
    return {
        "status": "validated" if (checked and not disagreements and not extra) else "broken",
        "checked": checked, "agreed": agreed,
        "predictedTagsWithoutAWalkedRoute": len(extra),
        "disagreements": disagreements,
    }


SELECTOR_BASES = {
    "finder": "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_Finder_DataForMemoryPack",
    "validator": "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPack",
    "postProcessor":
        "Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_PostProcessor_DataForMemoryPack",
}
# Contract filenames are ``<family>_<hex tag>_native.json``; the family name in
# the filename is lowercase where the reviewed route category is camel case.
CONTRACT_FAMILIES = {"finder": "finder", "validator": "validator",
                     "postprocessor": "postProcessor"}
CONTRACT_TAG_PATTERN = re.compile(r"^(?P<family>[a-z]+)_(?P<tag>[0-9a-f]+)_native\.json$")


def _subtype_name(wrapper: WrapperType) -> str | None:
    """The concrete subtype name inside a nested wrapped type.

    ``Beyond.Gameplay.Core.Selector+HitBoxFinder+Data`` names ``HitBoxFinder``;
    taking the last dotted component would name the enclosing ``Selector``.
    """
    wrapped = wrapper.wrapped_type
    if not wrapped:
        return None
    parts = wrapped.split("+")
    return parts[1] if len(parts) > 1 else parts[0].split(".")[-1]


def check_reviewed_nested_rows(
    families_by_name: dict[str, UnionFamily], contracts_dir: Path
) -> dict[str, Any]:
    """Corroborate the predicted nested tags against reviewed evidence.

    Two independent sources: the selector subtype routes a timeline contract
    records, and the tag each selector contract is filed under.
    """
    checked = agreed = 0
    disagreements: list[dict[str, Any]] = []

    def compare(category: str, tag: int, expected: str, source: str) -> None:
        nonlocal checked, agreed
        family = families_by_name.get(SELECTOR_BASES.get(category, ""))
        if family is None:
            return
        checked += 1
        wrapper = family.tags.get(tag)
        actual = _subtype_name(wrapper) if wrapper else None
        if actual == expected:
            agreed += 1
        else:
            disagreements.append({"source": source, "category": category, "unionTag": tag,
                                  "reviewed": expected, "predicted": actual})

    for path in sorted(contracts_dir.glob("*.json")):
        try:
            value = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        for category, routes in (value.get("selectedSubtypeRoutes") or {}).items():
            if not isinstance(routes, dict):
                continue
            for tag, name in routes.items():
                compare(category, int(tag), name, path.name)
        match = CONTRACT_TAG_PATTERN.match(path.name)
        if match is None:
            continue
        category = CONTRACT_FAMILIES.get(match.group("family"))
        if category is None:
            continue
        family = families_by_name.get(SELECTOR_BASES[category])
        wrapper = family.tags.get(int(match.group("tag"), 16)) if family else None
        names = {row[1] for row in value.get("methods", []) if isinstance(row, list) and len(row) > 1}
        checked += 1
        if wrapper is not None and wrapper.name in names:
            agreed += 1
        else:
            disagreements.append({
                "source": path.name, "category": category,
                "unionTag": int(match.group("tag"), 16),
                "reviewed": "filed under this tag",
                "predicted": wrapper.name if wrapper else None,
            })
    return {"checked": checked, "agreed": agreed, "disagreements": disagreements}


@dataclass(frozen=True)
class UnionFamily:
    base_name: str
    base_definition: int
    tags: dict[int, WrapperType]

    def row(self) -> dict[str, Any]:
        return {
            "unionBase": self.base_name,
            "baseTypeDefinition": self.base_definition,
            "subtypeCount": len(self.tags),
            "tags": [
                {
                    "unionTag": tag,
                    "wrapperName": wrapper.name,
                    "wrappedType": wrapper.wrapped_type,
                    "serializedMemberCount": wrapper.serialized_member_count,
                    "memberOrder": [member.name for member in wrapper.members],
                }
                for tag, wrapper in sorted(self.tags.items())
            ],
        }


def union_families(
    rows: dict[int, WrapperType], *, minimum_subtypes: int = 2
) -> dict[int, UnionFamily]:
    """Every wrapper with subtypes, as a union base with its tag assignment."""
    children = children_index(rows)
    families: dict[int, UnionFamily] = {}
    for base in sorted(children):
        if base not in rows or len(children[base]) < minimum_subtypes:
            continue
        tags = union_tags(rows, children, base)
        if tags is None:
            continue
        families[base] = UnionFamily(rows[base].name, base, tags)
    return families


#: The per-tag serialized member counts the frozen ``buff_actions`` reader
#: already reads for six nested unions, keyed by the base type each one wraps.
#:
#: This is not a build fingerprint and carries no address, hash or definition
#: index: it is a transcription of what a reviewed, corpus-validated reader
#: does, keyed by managed names that survive a client update. It is the
#: sharpest available check on the ordering rule, because none of these six
#: unions is natively walked -- the rule has to place every one of these tags
#: correctly, and a wrong placement shows up as a member count that does not
#: match rather than as a plausible name.
REVIEWED_NESTED_TABLES: dict[str, dict[int, int]] = {
    "Beyond.Gameplay.Core.Selector+Finder+Data": {
        0: 0, 1: 0, 2: 0, 3: 4, 5: 0, 7: 8, 8: 0, 10: 0,
        12: 1, 13: 1, 14: 2, 16: 9, 18: 11, 19: 4, 21: 0,
    },
    "Beyond.Gameplay.Core.Selector+Validator+Data": {
        1: 2, 2: 2, 4: 3, 5: 0, 9: 0, 10: 0, 11: 1,
    },
    "Beyond.Gameplay.Core.Selector+PostProcessor+Data": {1: 1, 7: 6, 8: 2},
    "Beyond.Gameplay.Core.DamageProcessorBase": {
        0: 1, 2: 1, 3: 1, 4: 1, 5: 3, 6: 2, 9: 2, 10: 3,
    },
    "Beyond.Gameplay.Core.HealProcessorBase": {0: 2, 1: 3},
    "Beyond.Gameplay.Core.CalculationBase": {0: 1, 1: 2, 2: 3, 3: 4, 5: 4},
}


def check_reviewed_nested_tables(
    rows: dict[int, WrapperType], children: dict[int, list[int]]
) -> dict[str, Any]:
    """Re-place every tag the frozen reader's own nested tables record.

    For each base, the ordering rule assigns the tags and this compares the
    subtype it lands on against the member count the reviewed reader reads
    there. A base the selected build does not have is reported missing rather
    than skipped silently, so a rename is visible instead of shrinking the
    check.
    """
    by_wrapped = {
        wrapper.wrapped_type: definition
        for definition, wrapper in rows.items()
        if wrapper.wrapped_type
    }
    checked = agreed = 0
    disagreements: list[dict[str, Any]] = []
    missing: list[str] = []
    for base_name, table in sorted(REVIEWED_NESTED_TABLES.items()):
        definition = by_wrapped.get(base_name)
        if definition is None:
            missing.append(base_name)
            continue
        tags = union_tags(rows, children, definition)
        for tag, expected in sorted(table.items()):
            checked += 1
            wrapper = tags.get(tag)
            actual = len(wrapper.members) if wrapper is not None else None
            if actual == expected:
                agreed += 1
            else:
                disagreements.append({
                    "base": base_name, "tag": tag,
                    "expectedMemberCount": expected, "actualMemberCount": actual,
                    "landedOn": wrapper.wrapped_type if wrapper is not None else None,
                })
    return {
        "checked": checked,
        "agreed": agreed,
        "missingBases": missing,
        "disagreements": disagreements[:20],
        "boundary": (
            "Agreement re-places a tag the reviewed reader already reads. It corroborates "
            "the ordering rule at those tags; it does not walk a route, and a tag no "
            "reviewed reader covers stays an ordering inference."
        ),
    }


def build(output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    rows, audit = load_wrapper_members()
    if audit["status"] != "validated":
        report = {"schema": "endfield.memorypack-union-subtypes.v1", "audit": audit,
                  "summary": {"status": audit["status"], "unions": 0}}
    else:
        children = children_index(rows)
        rule = check_rule_against_walked_routes(rows, children)
        families = union_families(rows) if rule["status"] == "validated" else {}
        by_name = {family.base_name: family for family in families.values()}
        nested = check_reviewed_nested_rows(
            by_name, REPO / "scripts/game_data/contracts"
        ) if families else {"checked": 0, "agreed": 0, "disagreements": []}
        tables = check_reviewed_nested_tables(rows, children) if families else {
            "checked": 0, "agreed": 0, "disagreements": [], "missingBases": []}
        report = {
            "schema": "endfield.memorypack-union-subtypes.v1",
            "audit": audit,
            "ruleCheck": rule,
            "reviewedNestedCheck": nested,
            "reviewedNestedTableCheck": tables,
            "evidenceBoundary": {
                "structuralOnly": (
                    "A tag here is the member's position under a metadata ordering rule, "
                    "corroborated against the walked root union, the reviewed nested "
                    "rows, and the frozen reader's own per-tag member counts for six "
                    "nested unions it never walks. It is not a route read out of the "
                    "dispatcher."
                ),
                "conditional": (
                    "Every predicted tag is void unless the rule reproduces the walked "
                    "root union exactly on the same build."
                ),
            },
            "summary": {
                "status": "validated" if rule["status"] == "validated" else rule["status"],
                "ruleAgreed": rule.get("agreed"), "ruleChecked": rule.get("checked"),
                "nestedAgreed": nested.get("agreed"), "nestedChecked": nested.get("checked"),
                "tableAgreed": tables.get("agreed"), "tableChecked": tables.get("checked"),
                "unions": len(families),
                "subtypes": sum(len(family.tags) for family in families.values()),
                "elapsedSeconds": round(time.perf_counter() - started, 3),
            },
            "unions": [families[base].row() for base in sorted(families)],
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--union", action="append", default=[],
                        help="print one union base's tag assignment instead of a report")
    args = parser.parse_args()
    if args.union:
        rows, audit = load_wrapper_members()
        if audit["status"] != "validated":
            print(json.dumps(audit, ensure_ascii=False), file=sys.stderr)
            return 1
        children = children_index(rows)
        families = union_families(rows)
        by_name = {family.base_name: family for family in families.values()}
        for wanted in args.union:
            matched = [name for name in by_name if name.endswith(wanted) or name == wanted]
            if not matched:
                print(json.dumps({"union": wanted, "status": "not-found"}), file=sys.stderr)
                return 1
            for name in sorted(matched):
                print(json.dumps(by_name[name].row(), ensure_ascii=False))
        return 0
    try:
        report = build(args.output)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
