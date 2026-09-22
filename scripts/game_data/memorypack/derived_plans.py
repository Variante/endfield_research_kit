"""Execute a derived read plan against the frozen reader's proven primitives.

``derived_schema`` resolves every dispatcher tag into a tree of member reads.
A plan is a description, not a cursor: it says what shape a body has, not that
any real payload has it.  This module is what turns the one into the other, by
walking a plan with the frozen ``buff_actions`` reader's own primitives so that
every byte a plan consumes is consumed by a framing that reader already proves
somewhere else -- the null marker, the member-count header, the nullable count,
the length-prefixed byte payload, the 28-byte keyframe curve.

Nothing here invents a framing.  Each plan kind maps to one primitive:

* ``fixed`` -- ``take(width)``;
* ``string`` -- ``byte_payload()``, the proven length-prefixed payload;
* ``profile`` -- the frozen reader's own method of that name;
* ``object`` -- a null marker, or a member-count header and the nested members;
* ``list`` -- a nullable count, then that many elements;
* ``map`` -- the counted-map framing ``action_map`` proves, with the
  ``SerializeFieldDictionary`` object header when the plan says it carries one;
* ``union`` -- a null marker, or a tag and the concrete subtype's members.

Recursion is bounded here rather than in the plan, exactly as the frozen reader
bounds its own nested sequences: a recursive type is a cycle in the plan
registry, and the depth limit is what makes executing it terminate.

The same two safety properties as ``derived_actions`` hold, and for the same
reasons.  It is strictly additive -- a tag the frozen reader admits is always
delegated and never intercepted -- and it fails closed, so without the installed
build there are no plans and the reader is the frozen reader.

**What a successful read does and does not prove.**  For a tag the frozen
reader also admits, agreement is real evidence: the frozen routes are reviewed
and corpus-validated, so a record the two framings both consume to the same
offset means the derivation reproduces a proven framing.  For a tag only this
reader admits, reaching the end of a synthesized record is self-consistency,
and a whole-corpus run against real payloads is the adoption gate.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.buff import (
    buff_post_id_result_is_exact_tail,
    decode_buff_post_id_prefix_at,
    frame_buff_named_middle,
)
from scripts.game_data.memorypack import buff_actions
from scripts.game_data.memorypack.buff_actions import Reader as _FrozenReader, Unsupported
from scripts.game_data.memorypack.derived_schema import (
    FIXED,
    LIST,
    MAP,
    OBJECT,
    PROFILE,
    STRING,
    UNION,
    MemberPlan,
    Resolver,
    resolve_routes,
)
from scripts.repo_paths import REPO_ROOT as REPO
from scripts.source_paths import ExportLayout


DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_derived_plans.json"
NULL_MARKER = 0xFF
WIDE_TAG_LEAD = 0xFA
# A plan may legitimately recurse; this is what makes executing one terminate.
# It bounds nesting, not record size, and a body deeper than this is reported
# unsupported rather than read on a guess.
PLAN_DEPTH_LIMIT = 24
# The exported family the frozen reader is built for, and the only one whose
# root framing is reachable without a corpus gate. Its first byte is the root
# wrapper's member count.
BUFFDATA_DIRECTORY = "BuffData"
BUFFDATA_ROOT_MEMBER_COUNT = 30
# A file with more id anchors than this is not selected between; the census
# refuses it rather than picking one.
MAX_ID_ANCHORS = 64
# The named middle's status when fields 6-14 reach the accepted id anchor.
NAMED_MIDDLE_CLOSED = "named-through-iconConfig"
# How deep synthesis goes before closing a nullable construct. Synthesis only
# has to exercise the framing, and every type here is reachable well inside it.
SYNTHESIS_DEPTH = 6


class PlanRegistry:
    """The plans, union tag maps and root routes one build resolved to."""

    def __init__(
        self,
        plans: dict[int, tuple[MemberPlan, ...]],
        union_tag_maps: dict[int, dict[int, int]],
        roots: dict[int, int],
    ) -> None:
        self.plans = plans
        self.union_tag_maps = union_tag_maps
        self.roots = roots

    @classmethod
    def from_resolver(
        cls, resolver: Resolver, resolved: dict[int, dict[str, Any]]
    ) -> "PlanRegistry":
        roots = {
            tag: row["wrapperTypeDefinition"]
            for tag, row in resolved.items()
            if row.get("status") == "determined" and "wrapperTypeDefinition" in row
        }
        return cls(dict(resolver.plans), dict(resolver.union_tag_maps), roots)

    def __len__(self) -> int:
        return len(self.roots)


def load_registry(
    *, gameassembly: Path | None = None, metadata: Path | None = None
) -> tuple[PlanRegistry, dict[str, Any]]:
    """Resolve the selected build's plans, or an empty registry and the gate."""
    resolved, resolver, audit = resolve_routes(
        gameassembly=gameassembly, metadata=metadata)
    if resolver is None:
        return PlanRegistry({}, {}, {}), audit
    registry = PlanRegistry.from_resolver(resolver, resolved)
    return registry, dict(audit, determinedRoutes=len(registry))


class DerivedPlanMixin:
    """Adds the derived plan routes to whatever reader it is mixed into.

    Kept separate from a concrete base for the same reason
    ``DerivedFixedWidthMixin`` is: the census constructs its readers by name,
    and layering lets the same behaviour reach both without either being
    edited.
    """

    plan_registry: "PlanRegistry | None" = None
    #: Optional per-run accumulators the corpus sweep installs on the subclass.
    #: A run that closes every file still only exercises the routes its files
    #: contain, so what was actually walked has to be counted rather than
    #: inferred from the plan count. Left None here: a reader used on its own
    #: records nothing extra.
    exercised_roots: "set[int] | None" = None
    exercised_unions: "set[tuple[int, int]] | None" = None

    def __init__(
        self, *args: Any, registry: "PlanRegistry | None" = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.plan_registry = registry if registry is not None else type(self).plan_registry
        self.plan_tags_read: list[int] = []

    def _action(self, depth: int, tag: int, width: int) -> None:
        registry = self.plan_registry
        definition = registry.roots.get(tag) if registry else None
        if definition is None:
            super()._action(depth, tag, width)
            return
        # The frozen reader owns every tag it admits. Its rejection happens
        # before it consumes the tag bytes, so an unsupported tag leaves the
        # cursor exactly where it was and this reader can take over.
        start = self.pos
        try:
            super()._action(depth, tag, width)
            return
        except Unsupported:
            if self.pos != start:
                raise
        self.take(width, "union-tag")
        self._plan_object(definition, depth)
        self.plan_tags_read.append(tag)
        if self.exercised_roots is not None:
            self.exercised_roots.add(tag)

    # ---- plan execution -------------------------------------------------

    def _plan_depth_guard(self, depth: int) -> None:
        if depth > PLAN_DEPTH_LIMIT:
            raise Unsupported(
                self.source, self.pos,
                f"plan nesting <= {PLAN_DEPTH_LIMIT}", depth, "depth-limit")

    def _plan_object(self, definition: int, depth: int) -> None:
        """A wrapper body: a null marker, or a member header and the members."""
        self._plan_depth_guard(depth)
        registry = self.plan_registry
        members = registry.plans.get(definition) if registry else None
        if members is None:
            raise Unsupported(
                self.source, self.pos, "a planned wrapper", definition, "unplanned")
        if self.peek() == NULL_MARKER:
            self.take(1, "null-wrapper")
            return
        self.header(len(members))
        for member in members:
            self._plan_member(member, depth + 1)

    def _plan_member(self, member: MemberPlan, depth: int) -> None:
        self._plan_depth_guard(depth)
        if member.kind == FIXED:
            self.take(member.width or 0, f"derived:{member.name}")
        elif member.kind == STRING:
            self.byte_payload()
        elif member.kind == PROFILE:
            getattr(self, member.profile or "")()
        elif member.kind == OBJECT:
            self._plan_object(member.ref if member.ref is not None else -1, depth + 1)
        elif member.kind == LIST:
            self._plan_list(member, depth)
        elif member.kind == MAP:
            self._plan_map(member)
        elif member.kind == UNION:
            self._plan_union(member.ref if member.ref is not None else -1, depth)
        else:
            raise Unsupported(
                self.source, self.pos, "a known plan kind", member.kind, "plan-kind")

    def _plan_list(self, member: MemberPlan, depth: int) -> None:
        """A nullable count, then that many elements read by the element plan."""
        element = member.element
        if element is None:
            raise Unsupported(
                self.source, self.pos, "a list element plan", None, "plan-kind")
        # The per-element minimum keeps the frozen reader's count bound honest:
        # a count larger than the remaining bytes can hold is a framing error,
        # not a large list.
        minimum = element.width if element.kind == FIXED and element.width else 1
        for _ in range(max(0, self.count(minimum, nullable=True))):
            self._plan_member(element, depth + 1)

    def _plan_map(self, member: MemberPlan) -> None:
        """The counted map, with the object header the plan says it carries.

        The pair is raw memory, so the whole struct including its padding is
        taken at once; the plan already carries the padded size.
        """
        pair_size = member.pair_size or 0
        if not pair_size:
            raise Unsupported(
                self.source, self.pos, "a sized map pair", pair_size, "plan-kind")
        if member.header:
            if self.peek() == NULL_MARKER:
                self.take(1, "null-map")
                return
            self.header(1)
        for _ in range(max(0, self.count(pair_size, nullable=True))):
            self.take(pair_size, f"derived:{member.name}.pair")

    def _plan_union(self, base: int, depth: int) -> None:
        """A null marker, or a tag and the concrete subtype's body."""
        self._plan_depth_guard(depth)
        registry = self.plan_registry
        tags = registry.union_tag_maps.get(base) if registry else None
        if tags is None:
            raise Unsupported(
                self.source, self.pos, "a planned union", base, "unplanned")
        if self.peek() == NULL_MARKER:
            self.take(1, "null-union")
            return
        lead = self.peek()
        if lead == WIDE_TAG_LEAD:
            tag = struct.unpack_from("<H", self.take(3, "union-tag"), 1)[0]
        elif lead > WIDE_TAG_LEAD:
            raise Unsupported(
                self.source, self.pos, "a union tag below 0xFA", lead, "union-marker")
        else:
            self.take(1, "union-tag")
            tag = lead
        definition = tags.get(tag)
        if definition is None:
            raise Unsupported(
                self.source, self.pos, "a planned union subtype", tag, "union-subtype")
        if self.exercised_unions is not None:
            self.exercised_unions.add((base, tag))
        self._plan_object(definition, depth + 1)


class DerivedPlanReader(DerivedPlanMixin, _FrozenReader):
    """The frozen reader plus every route a derived plan describes."""


def reader_subclass(
    base: type,
    registry: PlanRegistry,
    *,
    exercised_roots: set[int] | None = None,
    exercised_unions: set[tuple[int, int]] | None = None,
) -> type:
    """A subclass of ``base`` that also admits ``registry``'s routes.

    The two optional sets accumulate what a whole run walked, which is how the
    corpus report states its own reach rather than implying the plan count.
    """
    return type(
        f"Planned{base.__name__}", (DerivedPlanMixin, base),
        {"plan_registry": registry,
         "exercised_roots": exercised_roots,
         "exercised_unions": exercised_unions},
    )


# ---- synthesis and cross-check -----------------------------------------


def synthesize(registry: PlanRegistry, definition: int, depth: int = 0) -> bytes:
    """One body in the framing a plan describes, as filler bytes.

    The bytes carry no meaning; only the record's framing is under test. Every
    nullable construct is written non-null so the deepest path is the one
    exercised, except past the synthesis depth, where a null closes the
    recursion a recursive type would otherwise continue forever.
    """
    members = registry.plans.get(definition)
    if members is None or depth > SYNTHESIS_DEPTH:
        return bytes([NULL_MARKER])
    body = bytearray([len(members)])
    for index, member in enumerate(members):
        body += _synthesize_member(registry, member, index, depth)
    return bytes(body)


def _synthesize_member(
    registry: PlanRegistry, member: MemberPlan, index: int, depth: int
) -> bytes:
    if member.kind == FIXED:
        # The frozen reader requires a leading boolean to be 0 or 1.
        if index == 0 and member.width == 1:
            return bytes([1])
        return bytes(member.width or 0)
    if member.kind == STRING or member.kind == LIST:
        return struct.pack("<i", 0)
    if member.kind == PROFILE:
        return bytes([NULL_MARKER])
    if member.kind == OBJECT:
        return synthesize(registry, member.ref if member.ref is not None else -1, depth + 1)
    if member.kind == MAP:
        return (bytes([1]) if member.header else b"") + struct.pack("<i", 0)
    if member.kind == UNION:
        tags = registry.union_tag_maps.get(member.ref if member.ref is not None else -1) or {}
        if not tags or depth > SYNTHESIS_DEPTH:
            return bytes([NULL_MARKER])
        tag = min(tags)
        lead = (bytes([tag]) if tag < WIDE_TAG_LEAD
                else bytes([WIDE_TAG_LEAD]) + struct.pack("<H", tag))
        return lead + synthesize(registry, tags[tag], depth + 1)
    return b""


def synthesize_record(registry: PlanRegistry, tag: int) -> bytes:
    lead = (bytes([tag]) if tag < WIDE_TAG_LEAD
            else bytes([WIDE_TAG_LEAD]) + struct.pack("<H", tag))
    return lead + synthesize(registry, registry.roots[tag])


def _consume(reader: _FrozenReader) -> tuple[str, int]:
    """Read one action, returning the outcome and the cursor it reached."""
    try:
        reader.action(0)
    except Unsupported:
        return "unsupported", reader.pos
    except Exception:
        return "failed", reader.pos
    return "read", reader.pos


def cross_check(registry: PlanRegistry) -> dict[str, Any]:
    """Check each plan's framing against the frozen reader, tag by tag.

    A tag the frozen reader admits is the real test: a record built from the
    plan that the reviewed reader consumes to exactly the plan's own end means
    the two framings agree. A tag only this reader admits is shown to be
    self-consistent, which a corpus run, not this probe, turns into evidence.
    """
    shared = {"checked": 0, "agreed": 0, "disagreed": 0}
    new = {"checked": 0, "selfConsistent": 0, "inconsistent": 0}
    failures: list[dict[str, Any]] = []
    for tag in sorted(registry.roots):
        record = synthesize_record(registry, tag)
        expected = len(record)
        frozen_outcome, frozen_pos = _consume(_FrozenReader(record, f"tag-{tag:#x}"))
        if frozen_outcome == "unsupported":
            new["checked"] += 1
            outcome, pos = _consume(
                DerivedPlanReader(record, f"tag-{tag:#x}", registry=registry))
            key = "selfConsistent" if outcome == "read" and pos == expected else "inconsistent"
            new[key] += 1
            if key == "inconsistent":
                failures.append({"unionTag": tag, "class": "derived",
                                 "outcome": outcome, "reached": pos, "expected": expected})
            continue
        shared["checked"] += 1
        if frozen_outcome == "read" and frozen_pos == expected:
            shared["agreed"] += 1
        else:
            shared["disagreed"] += 1
            failures.append({"unionTag": tag, "class": "frozen", "outcome": frozen_outcome,
                             "reached": frozen_pos, "expected": expected})
    return {"frozenAdmittedTags": shared, "derivedOnlyTags": new,
            "failures": failures[:40], "failureCount": len(failures)}


# ---- corpus run --------------------------------------------------------


def _framed_extent(data: bytes, source: str, stem: str) -> tuple[int, int] | None:
    """How far one BuffData file frames, or None when it stops early.

    This is the census's own chain -- the accepted id anchor, the event prefix,
    the root continuation over members 2-6, then the named middle over fields
    6-14 -- driven straight off exported bytes. It is the ungated part: it
    establishes nothing about which corpus these files are, only how far the
    reader gets in each one, which is what a before-and-after comparison on one
    fixed set of files needs.

    The pair returned is the middle's end offset and the root continuation's
    range count, which together move if any framing decision changes.
    """
    encoded = stem.encode("utf-8")
    marker = len(encoded).to_bytes(4, "little") + encoded
    anchors: list[int] = []
    start = 1
    while (start := data.find(marker, start)) >= 0:
        anchors.append(start)
        start += 1
        if len(anchors) > MAX_ID_ANCHORS:
            return None
    for anchor in anchors:
        if not buff_post_id_result_is_exact_tail(
                decode_buff_post_id_prefix_at(data, stem, anchor)):
            continue
        try:
            prefix = buff_actions.event_prefix(data, source=source, limit=anchor)
            if prefix["status"] != "supported-prefix":
                continue
            continuation = buff_actions.root_continuation(
                data, source=source, start=prefix["consumedEnd"], limit=anchor)
            if continuation["status"] != "supported-prefix":
                continue
            middle = frame_buff_named_middle(data, continuation["consumedEnd"], anchor)
        except (ValueError, KeyError, IndexError, struct.error):
            continue
        if middle.get("status") == NAMED_MIDDLE_CLOSED:
            return anchor, len(continuation["ranges"])
    return None


def _sweep(files: list[Path]) -> dict[str, tuple[int, int]]:
    closed: dict[str, tuple[int, int]] = {}
    for path in files:
        data = path.read_bytes()
        if not data or data[0] != BUFFDATA_ROOT_MEMBER_COUNT:
            continue
        reached = _framed_extent(data, path.name, path.stem)
        if reached is not None:
            closed[path.name] = reached
    return closed


def corpus_run(export_root: Path | None = None) -> dict[str, Any]:
    """Compare the frozen reader against the plan reader over exported BuffData.

    This is the adoption gate the cross-check cannot be: it reads real payloads
    rather than synthesized ones. Two results decide it -- how many more files
    close, and whether every file that already closed still ends at exactly the
    same cursor. The second is what makes "strictly additive" a measurement
    instead of a design claim.
    """
    started = time.perf_counter()
    layout = (ExportLayout(root=export_root) if export_root is not None
              else ExportLayout.configured())
    directory = layout.json_dir / BUFFDATA_DIRECTORY
    if not directory.is_dir():
        return {"status": "missing-export", "detail": str(directory)}
    files = sorted(directory.glob("*.json"))
    before = _sweep(files)
    registry, audit = load_registry()
    if not len(registry):
        return {"status": audit.get("status", "unresolved"), "files": len(files)}
    roots: set[int] = set()
    unions: set[tuple[int, int]] = set()
    original = buff_actions.Reader
    buff_actions.Reader = reader_subclass(
        original, registry, exercised_roots=roots, exercised_unions=unions)
    try:
        after = _sweep(files)
    finally:
        buff_actions.Reader = original
    shared = sorted(set(before) & set(after))
    unchanged = sum(1 for name in shared if before[name] == after[name])
    moved = [name for name in shared if before[name] != after[name]]
    return {
        "status": "validated" if not moved and not (set(before) - set(after)) else "regressed",
        "audit": audit,
        "files": len(files),
        "frozenClosed": len(before),
        "planClosed": len(after),
        "gained": len(set(after) - set(before)),
        "lost": len(set(before) - set(after)),
        "cursorUnchanged": unchanged,
        "cursorChecked": len(shared),
        "cursorMoved": moved[:20],
        "planTagsExercised": len(roots),
        "planTagsAvailable": len(registry),
        "nestedUnionPlacementsExercised": len(unions),
        "nestedUnionBasesExercised": len({base for base, _ in unions}),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
        "boundary": (
            "Closure here is the root's members 2-6 and then the named middle's fields "
            "6-14 reaching the accepted id anchor, not a whole-file EOF claim. The "
            "named suffix beyond that anchor and the opaque nested bodies inside these "
            "fields are unchanged, and BuffData is one family: the SkillData timeline "
            "readers sit behind their own inputSetSha256 gates and are not covered. "
            "Closing every file is not validating every plan: planTagsExercised and "
            "nestedUnionPlacementsExercised are what this run actually walked, and the "
            "rest of the routes are untouched by it."
        ),
    }


def probe() -> dict[str, Any]:
    started = time.perf_counter()
    registry, audit = load_registry()
    result = cross_check(registry) if len(registry) else {}
    shared = result.get("frozenAdmittedTags", {})
    new = result.get("derivedOnlyTags", {})
    return {
        "schema": "endfield.memorypack-derived-plans-probe.v1",
        "audit": audit,
        "summary": {
            "status": audit.get("status"),
            "routes": len(registry),
            "planRegistrySize": len(registry.plans),
            "frozenChecked": shared.get("checked"),
            "frozenAgreed": shared.get("agreed"),
            "derivedOnlyChecked": new.get("checked"),
            "derivedOnlySelfConsistent": new.get("selfConsistent"),
            "failures": result.get("failureCount", 0),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "crossCheck": result,
        "boundary": (
            "Agreement on the tags the frozen reader admits shows a plan reproduces a "
            "reviewed, corpus-validated framing. The remaining tags are only shown to "
            "be self-consistent; that a real payload has this shape is established by "
            "a whole-corpus run, not by this probe."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--corpus", action="store_true",
                        help="run the plan reader over exported BuffData and compare")
    parser.add_argument("--export-root", type=Path, default=None)
    args = parser.parse_args()
    if args.corpus:
        try:
            result = corpus_run(args.export_root)
        except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
            print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
            return 1
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") == "validated" else 2
    output = args.output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        print(json.dumps({"status": "failed", "detail": f"output-must-be-under={reports}"}),
              file=sys.stderr)
        return 1
    try:
        report = probe()
    except (OSError, ValueError, KeyError, TypeError, struct.error, RecursionError) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
