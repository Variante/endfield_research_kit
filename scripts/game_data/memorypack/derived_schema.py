"""Resolve a derived action tag into a recursive read plan.

``derived_actions`` consumes a tag whose members are all fixed-width or strings.
Most tags are not that shape: their members hold nested records, lists, and
nested unions.  Those are resolvable too, because the derivation already
supplies every part -- ``wrapper_members`` names each member and the type it
holds, ``wrapped_type_index`` maps that type to the wrapper that frames it, and
``union_subtypes`` supplies the tag assignment for a nested union.

A plan is a tree of member reads, built once per wrapper and referenced by
definition so a recursive type is a cycle in the registry rather than an
infinite expansion.  Recursion is bounded when the plan is *executed*, by a
depth limit, exactly as the frozen reader bounds its own nested sequences; a
recursive type is not undeterminable, it merely has no static width.

Evidence tiers differ by member kind and a plan carries the weakest one it
contains.  A nested record read from its generated members is ``direct``; a
nested union is ``structuralOnly``, because its tag assignment is the inferred
ordering that ``union_subtypes`` corroborates rather than a walked route.

A type whose framing is not its member list is never read from that list.  Such
a type registers its own ``MemoryPackFormatter``, and this module takes one of
two routes for it:

* **modelled**, when a reviewed reader already proves what the formatter writes.
  The counted-map family is the case that matters here.  ``Dictionary<K,V>``
  writes a nullable count and then that many ``KeyValuePair<K,V>`` structs laid
  out with .NET's own padding, and the ``SerializeFieldDictionary`` family
  writes a one-member object header before exactly that.  Both framings come
  from ``codecs.levelscript.action_map``, whose CharInteractPerform reader
  reaches EOF on all 202 current owners reading them, and the
  ``<GroundedMoveGait, float>`` instantiation is separately walked by the
  ``buff_residual_actions`` exact-build contract.  Only an unmanaged key *and*
  value are modelled, because that is the shape the pair layout is proven for;
* **refused**, for every other formatter-backed type.
  ``levelscript_union_layouts.FORMATTER_BACKED_TYPES`` enumerates them from the
  managed image, and that lane records that the ones outside the two settled
  cases "are read from their field lists on the strength of nothing".  Reading
  such a member list here would desynchronise the stream, so the route is left
  open with the type named rather than resolved on a guess.

Anything else whose type does not resolve to a wrapper, a primitive, a counted
map or a list of those is likewise reported undetermined, with the blocking
member named.
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
from typing import Any

from scripts.game_data.levelscript_union_layouts import FORMATTER_BACKED_TYPES
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.union_subtypes import children_index, union_tags
from scripts.game_data.memorypack.wrapper_members import (
    KIND_WIDTHS,
    PRIMITIVE_KINDS,
    DerivedTables,
    WrapperType,
    load_derived_tables,
    wrapped_type_index,
)
from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_derived_schema.json"
LIST_PATTERN = re.compile(r"^System\.Collections\.Generic\.List`1<(?P<element>.+)>$")
# Counted-map families, by whether the formatter writes the one-member object
# header before the count. ``SerializeFieldDictionary`` and its Paired/Sorted
# siblings do; a plain ``Dictionary`` does not. Both are modelled rather than
# refused because ``action_map`` proves each framing; see the module docstring.
COUNTED_MAP_HEADS = {
    "Beyond.SerializeFieldDictionary": True,
    "Beyond.SerializeFieldDictionaryPaired": True,
    "Beyond.SerializeFieldDictionarySorted": True,
    "System.Collections.Generic.Dictionary": False,
}
# ``SerializeReferenceDictionary`` is deliberately absent: no reviewed reader
# routes it, so it falls through to the formatter-backed refusal below.
CUSTOM_FORMATTER_FAMILIES = ("Beyond.SerializeReferenceDictionary",)
# Formatter-backed types this module models anyway, each on its own recorded
# evidence: ``AnimationCurve`` through the frozen reader's proven profile,
# ``StringPathHash`` because its formatter matches its one int64 field, which
# SpawnerConfig and LevelConfig corroborate by closing every file, and
# ``AudioId`` because its ``Deserialize`` body is a class-init guard, one
# ``MethodInfo``-carrying call into a reader generic instance, one 32-bit store
# into the value, and a return -- no null-marker test, no member-count byte, no
# second call, no loop, so no framing but the value itself fits in it.
# ``StringPathHashFormatter.Deserialize`` is the same body shape differing only
# in the int64 instantiation and an eight-byte store, so the settled case is
# what fixes what the shape means. Their widths come from the build's own
# value-size table like any other struct.
MODELLED_FORMATTER_TYPES = frozenset({"AnimationCurve", "StringPathHash", "AudioId"})
REFUSED_FORMATTER_TYPES = frozenset(FORMATTER_BACKED_TYPES) - MODELLED_FORMATTER_TYPES
# A blittable struct's width is read from the build's own type-size table by
# ``wrapper_members.unmanaged_value_sizes_from_image``, which records the
# evidence for it. That table replaces the hand-maintained Unity and formatter
# width lists this module used to carry: it reproduces every value they held
# and corrects ``CameraControlStateInitialParam``, whose members sum to 16
# while the struct is 24. ``UnityEngine.AnimationCurve`` is not in it, because
# it is not blittable; it is a plan kind of its own, executed by the frozen
# reader's proven ``curve_profile``.
# Variable-length types the frozen reader already has a proven profile for.
# The plan names the profile; the reader calls that reader's own method, so no
# framing is restated here.
PROFILE_TYPES = {"UnityEngine.AnimationCurve": "curve_profile"}
FIXED, STRING, OBJECT, LIST, UNION, PROFILE, MAP = (
    "fixed", "string", "object", "list", "union", "profile", "map")
DIRECT, STRUCTURAL_ONLY = "direct", "structuralOnly"


def _split_generic_arguments(arguments: str) -> list[str]:
    """Split ``K,V`` at depth zero.

    A generic argument is itself a generic spelling often enough that a plain
    ``split(",")`` cuts one in half, so the depth of ``<...>`` and ``[...]`` is
    tracked. ``action_map`` splits the same shape, but from the short type names
    its declaration table carries rather than from these metadata full names.
    """
    parts: list[str] = []
    depth = 0
    current = ""
    for character in arguments:
        if character in "<[":
            depth += 1
        elif character in ">]":
            depth -= 1
        elif character == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += character
    if current:
        parts.append(current)
    return parts


def _align_up(offset: int, alignment: int) -> int:
    return offset if alignment <= 1 else -(-offset // alignment) * alignment


@dataclass(frozen=True)
class MemberPlan:
    """How to read one member. ``ref`` points into the plan registry."""

    name: str
    kind: str
    width: int | None = None
    ref: int | None = None
    element: "MemberPlan | None" = None
    profile: str | None = None
    key: "MemberPlan | None" = None
    value: "MemberPlan | None" = None
    # A counted map's pair geometry: where the value sits inside the
    # ``KeyValuePair<K,V>`` struct and how long the whole struct is, both
    # including .NET's layout padding. ``header`` records whether the
    # formatter writes the one-member object header before the count.
    value_offset: int | None = None
    pair_size: int | None = None
    header: bool | None = None

    def row(self) -> dict[str, Any]:
        row: dict[str, Any] = {"name": self.name, "kind": self.kind}
        if self.width is not None:
            row["width"] = self.width
        if self.ref is not None:
            row["ref"] = self.ref
        if self.element is not None:
            row["element"] = self.element.row()
        if self.profile is not None:
            row["profile"] = self.profile
        if self.key is not None:
            row["key"] = self.key.row()
        if self.value is not None:
            row["value"] = self.value.row()
        if self.value_offset is not None:
            row["valueOffset"] = self.value_offset
        if self.pair_size is not None:
            row["pairSize"] = self.pair_size
        if self.header is not None:
            row["header"] = self.header
        return row


class Resolver:
    """Builds read plans over the derived wrapper tables."""

    def __init__(
        self,
        wrappers: dict[int, WrapperType],
        tables: DerivedTables | None = None,
    ) -> None:
        tables = tables or DerivedTables({}, {})
        self.value_sizes = tables.value_sizes
        self.wrappers = wrappers
        self.by_type = wrapped_type_index(wrappers)
        self.children = children_index(wrappers)
        self.plans: dict[int, tuple[MemberPlan, ...]] = {}
        self.tiers: dict[int, str] = {}
        self.blockers: dict[int, str] = {}
        # Per union base, the tag assignment its concrete subtypes take. Kept
        # from planning so an executor reads the same assignment the plan was
        # built against rather than deriving a second one.
        self.union_tag_maps: dict[int, dict[int, int]] = {}
        # Every enum's width, read from its own ``value__`` field. An enum that
        # appears only as a list element or a map key is declared by no member,
        # so deriving the table from the members would not see it.
        self.enum_widths: dict[str, int] = dict(tables.enum_widths)
        for wrapper in wrappers.values():
            for member in wrapper.members:
                if member.kind == "enum" and member.declared_type and member.width:
                    self.enum_widths.setdefault(member.declared_type, member.width)

    # ---- type classification -------------------------------------------

    def _is_union(self, definition: int) -> bool:
        """Whether a nested member of this type is preceded by a union tag.

        Having a subclass is not enough, and reading it that way was wrong: a
        concrete base is written as the plain object its member list describes.
        ``WrapperType.frames_as_union`` carries the actual test and records the
        evidence for it.
        """
        wrapper = self.wrappers.get(definition)
        return bool(self.children.get(definition)) and bool(
            wrapper and wrapper.frames_as_union)

    def _refused(self, declared: str | None) -> bool:
        """Whether a formatter-backed type must be left unresolved.

        The simple name is what ``FORMATTER_BACKED_TYPES`` enumerates, so a
        nested or generic spelling is reduced to its last segment before the
        membership test.
        """
        if not declared:
            return False
        if declared.startswith(CUSTOM_FORMATTER_FAMILIES):
            return True
        simple = declared.split("`")[0].replace("+", ".").rsplit(".", 1)[-1]
        return simple in REFUSED_FORMATTER_TYPES

    def _plan_counted_map(self, name: str, declared: str) -> MemberPlan | None:
        """A ``Dictionary`` or ``SerializeFieldDictionary`` member, or None.

        Only an unmanaged key and value are modelled.  The pair is a
        ``KeyValuePair<K,V>`` written as raw memory, so it carries .NET's
        layout padding: the value is aligned to its own width and the struct is
        padded to the wider of the two.  That is the rule ``action_map`` proves,
        and it is self-checking at read time because the padding must be zero.
        A managed side is refused -- its element framing is not established for
        this family, and guessing it would desynchronise the stream.
        """
        head, separator, rest = declared.partition("`2<")
        if not separator or not rest.endswith(">") or head not in COUNTED_MAP_HEADS:
            return None
        arguments = _split_generic_arguments(rest[:-1])
        if len(arguments) != 2:
            return None
        key = self._plan_for_type("key", arguments[0])
        value = self._plan_for_type("value", arguments[1])
        if key is None or value is None:
            return None
        if key.kind != FIXED or value.kind != FIXED or not key.width or not value.width:
            return None
        value_offset = _align_up(key.width, value.width)
        pair_size = _align_up(value_offset + value.width, max(key.width, value.width))
        return MemberPlan(
            name, MAP, key=key, value=value,
            value_offset=value_offset, pair_size=pair_size,
            header=COUNTED_MAP_HEADS[head],
        )

    def _plan_for_type(
        self, name: str, declared: str | None, *, as_element: bool = False
    ) -> MemberPlan | None:
        """A plan for a member holding ``declared``, or None when unresolved.

        ``as_element`` marks a collection element, which is framed differently
        from a member of the same type. A blittable struct is raw memory where
        it is embedded directly -- the frozen reader takes ``GameplayTag`` as
        four raw bytes in the tag-7 route -- but a collection writes each
        element through that type's own generated formatter, which emits the
        member header first. The reviewed ``_skill_read_gameplay_tag_list``
        records exactly that: every element is five bytes, a member-count byte
        of one and then four. ``_skill_read_buff_id_list`` frames ``BuffId``
        the same way, calling it the retained nested one-member wrapper.

        The distinction is whether the type has a generated wrapper at all. A
        Unity value type has none, so nothing can write a header for it and it
        stays raw in either position.
        """
        if declared is None or self._refused(declared):
            return None
        if as_element and declared in self.value_sizes:
            # Only the raw-struct case is redirected. Everything else keeps its
            # normal route, or this would preempt the primitives and the
            # AnimationCurve profile, which a collection frames no differently.
            definition = self.by_type.get(declared)
            if definition is not None:
                kind = UNION if self._is_union(definition) else OBJECT
                return MemberPlan(name, kind, ref=definition)
        primitive = PRIMITIVE_KINDS.get(declared)
        if primitive == "string":
            return MemberPlan(name, STRING)
        if primitive is not None:
            return MemberPlan(name, FIXED, width=KIND_WIDTHS.get(primitive))
        if declared in self.enum_widths:
            return MemberPlan(name, FIXED, width=self.enum_widths[declared])
        if declared in self.value_sizes:
            # A blittable struct is raw memory: no null marker, no member
            # header, and its aligned size rather than its members' sum.
            return MemberPlan(name, FIXED, width=self.value_sizes[declared])
        if declared in PROFILE_TYPES:
            return MemberPlan(name, PROFILE, profile=PROFILE_TYPES[declared])
        counted_map = self._plan_counted_map(name, declared)
        if counted_map is not None:
            return counted_map
        # ``List<T>`` and ``T[]`` share a framing: a nullable count, then that
        # many elements read by the element plan. For a fixed-width element that
        # is byte-identical to the frozen reader's bulk ``count*width`` copy; for
        # an object element each one carries its own header, as its nested
        # collection profiles do.
        match = LIST_PATTERN.match(declared)
        element_type = match.group("element") if match else (
            declared[:-2] if declared.endswith("[]") else None)
        if element_type is not None:
            # Only ``List<T>`` writes each element through T's own formatter.
            # ``T[]`` of an unmanaged T is a packed array, so its elements keep
            # the raw width they have as a member.
            element = self._plan_for_type(
                "item", element_type, as_element=match is not None)
            return MemberPlan(name, LIST, element=element) if element else None
        definition = self.by_type.get(declared)
        if definition is None:
            return None
        kind = UNION if self._is_union(definition) else OBJECT
        return MemberPlan(name, kind, ref=definition)

    # ---- plan construction ---------------------------------------------

    def plan(self, definition: int, stack: frozenset[int] = frozenset()) -> bool:
        """Build and register one wrapper's plan; True when it is complete."""
        if definition in self.plans:
            return True
        if definition in self.blockers:
            return False
        if definition in stack:
            # A cycle is legitimate recursion; the registry reference closes it.
            return True
        wrapper = self.wrappers.get(definition)
        if wrapper is None or not wrapper.members:
            self.blockers[definition] = "no-members"
            return False
        members: list[MemberPlan] = []
        tier = DIRECT
        for member in wrapper.members:
            if member.width is not None:
                members.append(MemberPlan(member.name, FIXED, width=member.width))
                continue
            built = self._plan_for_type(member.name, member.declared_type)
            if built is None:
                self.blockers[definition] = f"{member.name}:{member.declared_type}"
                return False
            members.append(built)
        self.plans[definition] = tuple(members)
        nested = stack | {definition}
        for built in members:
            for reference in (built, built.element):
                if reference is None or reference.ref is None:
                    continue
                if reference.kind == UNION:
                    tier = STRUCTURAL_ONLY
                    if not self._plan_union(reference.ref, nested):
                        del self.plans[definition]
                        # Carry the underlying reason so a cascade names its
                        # root cause rather than the nearest parent.
                        self.blockers[definition] = self.blockers.get(
                            reference.ref, f"{reference.name}:union-unresolved")
                        return False
                elif not self.plan(reference.ref, nested):
                    del self.plans[definition]
                    self.blockers[definition] = self.blockers.get(
                        reference.ref, f"{reference.name}:nested-unresolved")
                    return False
                tier = STRUCTURAL_ONLY if self.tiers.get(reference.ref) == STRUCTURAL_ONLY else tier
        self.tiers[definition] = tier
        return True

    def _plan_union(self, base: int, stack: frozenset[int]) -> bool:
        """Every concrete subtype of a union base needs its own plan."""
        tags = union_tags(self.wrappers, self.children, base)
        if not tags:
            self.blockers[base] = "union-unorderable"
            return False
        for wrapper in tags.values():
            if not wrapper.members:
                # A subtype that adds no members is not unresolvable: it writes
                # a header byte of zero and nothing else. The reviewed
                # ``selector_finder_profile`` records exactly that, with a
                # header of 0 for seven of its fifteen tags, so an empty plan
                # is the right answer rather than a skip.
                self.plans.setdefault(wrapper.type_definition, ())
                self.tiers.setdefault(wrapper.type_definition, DIRECT)
                continue
            if not self.plan(wrapper.type_definition, stack):
                self.blockers[base] = self.blockers.get(
                    wrapper.type_definition, "union-subtype-unresolved")
                return False
        self.union_tag_maps[base] = {
            tag: wrapper.type_definition for tag, wrapper in tags.items()
        }
        self.tiers[base] = STRUCTURAL_ONLY
        return True


def resolve_routes(
    *, gameassembly: Path | None = None, metadata: Path | None = None
) -> tuple[dict[int, dict[str, Any]], Resolver | None, dict[str, Any]]:
    """Resolve every dispatcher tag into a read plan, or nothing."""
    wrappers, tables, audit = load_derived_tables(
        gameassembly=gameassembly, metadata=metadata)
    if audit["status"] != "validated":
        return {}, None, audit
    routes, route_audit = load_action_routes(gameassembly=gameassembly, metadata=metadata)
    if route_audit["status"] != "validated":
        return {}, None, route_audit
    resolver = Resolver(wrappers, tables)
    resolved: dict[int, dict[str, Any]] = {}
    for tag, route in sorted(routes.items()):
        definition = route.wrapper_type_definition
        if route.status != "resolved" or definition is None:
            resolved[tag] = {"status": route.status}
            continue
        if resolver.plan(definition):
            resolved[tag] = {
                "status": "determined",
                "wrapperTypeDefinition": definition,
                "wrapperName": route.wrapper_name,
                "evidenceTier": resolver.tiers.get(definition, DIRECT),
            }
        else:
            resolved[tag] = {
                "status": "open",
                "wrapperName": route.wrapper_name,
                "blockedBy": resolver.blockers.get(definition),
            }
    return resolved, resolver, dict(audit, routeAudit=route_audit["status"])


def _reviewed_route_rows(value: Any) -> Any:
    """Every reviewed block naming a union tag, a member count and a type."""
    if isinstance(value, dict):
        tag = value.get("tag", value.get("unionTag"))
        count = value.get("memberCount", value.get("serializedMemberCount"))
        name = value.get("typeName") or value.get("actionName") or value.get("wrapperName")
        if tag is not None and isinstance(count, int) and name:
            yield tag, count, name
        for nested in value.values():
            yield from _reviewed_route_rows(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _reviewed_route_rows(nested)


def verify_against_reviewed_routes(
    resolved: dict[int, dict[str, Any]], resolver: Resolver, contracts: Path
) -> dict[str, Any]:
    """Check resolved routes against every reviewed row that names a type.

    **The join is by type name, never by tag**, and that is the whole point. A
    union tag is only meaningful inside its own union, and this repository's
    contracts index more than one: ``action_entity_fields.json`` records tags
    for the ``Beyond.Gameplay.Actions`` family, not for the
    ``AbilityActionData`` dispatcher these plans resolve. Joining those rows on
    the tag produces confident-looking disagreements out of two unrelated
    numbering schemes -- the cross-package join this directory warns about,
    reproduced exactly: 38 of them, none real.

    Joining on the name inverts it safely. A reviewed row is matched to the
    planned route whose wrapper wraps a type of that name, and then the tag
    itself becomes something checked rather than assumed. A row naming a type
    no planned route wraps is reported unjoinable, and a name claimed by more
    than one route is reported ambiguous; neither is quietly counted as
    agreement.
    """
    by_name: dict[str, list[tuple[int, int]]] = {}
    for tag, entry in resolved.items():
        if entry.get("status") != "determined":
            continue
        definition = entry["wrapperTypeDefinition"]
        wrapper = resolver.wrappers.get(definition)
        if wrapper is None or not wrapper.wrapped_type:
            continue
        parts = wrapper.wrapped_type.replace("+", ".").split(".")
        # A nested ``...+Data`` payload is named after its owner, which is the
        # name a contract records for it.
        simple = parts[-2] if len(parts) > 1 and parts[-1] == "Data" else parts[-1]
        by_name.setdefault(simple, []).append((tag, len(resolver.plans.get(definition, ()))))

    counts = {"agreed": 0, "tagMismatch": 0, "memberCountMismatch": 0,
              "unjoinable": 0, "ambiguousName": 0, "unparsableTag": 0}
    disagreements: list[dict[str, Any]] = []
    for path in sorted(contracts.glob("*.json")):
        try:
            contract = json.loads(path.read_bytes())
        except ValueError:
            continue
        for tag, count, name in _reviewed_route_rows(contract):
            try:
                value = int(tag, 16) if isinstance(tag, str) else int(tag)
            except (TypeError, ValueError):
                counts["unparsableTag"] += 1
                continue
            hits = by_name.get(name.replace("+", ".").split(".")[-1])
            if not hits:
                counts["unjoinable"] += 1
                continue
            if len(hits) != 1:
                counts["ambiguousName"] += 1
                continue
            planned_tag, planned_count = hits[0]
            if planned_tag != value:
                counts["tagMismatch"] += 1
                disagreements.append({"contract": path.name, "typeName": name,
                                      "reviewedTag": value, "plannedTag": planned_tag})
            elif planned_count != count:
                counts["memberCountMismatch"] += 1
                disagreements.append({"contract": path.name, "typeName": name,
                                      "reviewedMemberCount": count,
                                      "plannedMemberCount": planned_count})
            else:
                counts["agreed"] += 1
    return {
        **counts,
        "checked": counts["agreed"] + counts["tagMismatch"] + counts["memberCountMismatch"],
        "disagreements": disagreements[:20],
        "boundary": (
            "Agreement re-derives a tag and member count a reviewed contract already "
            "records, joined by type name. An unjoinable row belongs to another union "
            "and is excluded rather than compared."
        ),
    }


def build(output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    resolved, resolver, audit = resolve_routes()
    counts: dict[str, int] = {}
    tiers: dict[str, int] = {}
    blockers: dict[str, int] = {}
    for row in resolved.values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        if row["status"] == "determined":
            tier = row["evidenceTier"]
            tiers[tier] = tiers.get(tier, 0) + 1
        elif row.get("blockedBy"):
            key = str(row["blockedBy"]).split(":")[-1][:60]
            blockers[key] = blockers.get(key, 0) + 1
    reviewed = (
        verify_against_reviewed_routes(resolved, resolver, CONTRACTS_DIR)
        if resolver else {"checked": 0, "agreed": 0}
    )
    report = {
        "schema": "endfield.memorypack-derived-schema.v1",
        "audit": audit,
        "reviewedRouteCheck": reviewed,
        "evidenceBoundary": {
            "direct": (
                "A nested record is read from the selected build's generated members."
            ),
            "structuralOnly": (
                "A plan containing a nested union carries that union's inferred tag "
                "assignment, which is corroborated rather than walked."
            ),
            "modelledFormatter": (
                "A counted map's framing comes from the reviewed action_map reader, not "
                "from the type's member list, and only an unmanaged key and value are "
                "modelled. AudioId's extent comes from its formatter body, whose shape "
                "the settled StringPathHash formatter fixes the meaning of."
            ),
            "conditional": (
                "No plan is a proven cursor. Resolution says a body's shape is fully "
                "described, not that a payload reads to its end; a corpus run decides that."
            ),
        },
        "summary": {
            "status": audit["status"],
            "routes": len(resolved),
            "routeStatuses": dict(sorted(counts.items())),
            "determinedByTier": dict(sorted(tiers.items())),
            "planRegistrySize": len(resolver.plans) if resolver else 0,
            "reviewedAgreed": reviewed.get("agreed"),
            "reviewedChecked": reviewed.get("checked"),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "topBlockers": dict(sorted(blockers.items(), key=lambda kv: -kv[1])[:20]),
        "routes": [{"unionTag": tag, **row} for tag, row in sorted(resolved.items())],
        "plans": (
            {str(definition): [member.row() for member in members]
             for definition, members in sorted(resolver.plans.items())}
            if resolver else {}
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build(args.output)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error, RecursionError) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
