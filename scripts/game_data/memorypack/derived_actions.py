"""Consume root action bodies whose members are all fixed-width.

The frozen reader in ``buff_actions`` admits an explicit set of union tags and
stops at the first byte of any other, which is the correct default: an
unreviewed tag has no proven body and guessing one would desynchronise the rest
of the record.  For one class of tag, though, the body is not a guess.

``action_dispatcher`` resolves every tag in the selected build's dispatcher to
its generated wrapper, and ``wrapper_members`` gives that wrapper's members in
read order with a width for each member whose size is fixed by its type.  Where
every member is fixed, the whole body is a known-length sequence of known-width
fields, and the framing around it is the one the frozen reader already proves
everywhere else::

    union tag (1 byte, or 3 when the lead is 0xFA)
      -> 0xFF null wrapper, or
      -> one header byte equal to the serialized member count
      -> each member, in generated setter order

This reader admits exactly those tags, and names each field instead of taking
it anonymously.  Every other tag is delegated to the frozen reader unchanged.

Two properties keep that safe:

* it is strictly additive.  A tag the frozen reader admits is never
  intercepted, so no reviewed route changes behaviour;
* it fails closed.  Without the installed build there are no derived routes and
  the reader is the frozen reader.

Admitting a formerly unknown route can still change a previously bounded row
elsewhere in a record, so this module is opt-in and is not wired into the
corpus gates.  Validate a whole-corpus run before adopting it anywhere.

``derived_plans`` is the superset and is the one to reach for.  It executes the
recursive ``derived_schema`` plans, so it admits every tag this module does and
310 more, including the nested records, lists, counted maps and unions a flat
body cannot express, and it has been measured against the exported BuffData
family.  This module remains as the narrow, flat-body case: it needs no plan
registry, which keeps it the simpler thing to reason about when only a
fixed-width body is in question.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader as _FrozenReader, Unsupported
from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_derived_actions.json"
NULL_WRAPPER = 0xFF
# A union tag of 0xFA or above is written as this lead byte plus a
# little-endian unsigned 16-bit tag, matching the frozen reader.
WIDE_TAG_LEAD = 0xFA


# A member this reader can consume: either a type-fixed width, or the
# length-prefixed byte payload the frozen reader already proves for a string.
FIXED = "fixed"
STRING = "string"


@dataclass(frozen=True)
class DerivedMember:
    name: str
    kind: str
    width: int | None = None

    def row(self) -> dict[str, Any]:
        row: dict[str, Any] = {"name": self.name, "kind": self.kind}
        if self.width is not None:
            row["width"] = self.width
        return row


@dataclass(frozen=True)
class DerivedRoute:
    """One tag whose whole body this reader can consume."""

    tag: int
    wrapper_name: str
    member_count: int
    members: tuple[DerivedMember, ...]

    @property
    def fixed_body_width(self) -> int | None:
        """The body's byte width, when no member is variable-length."""
        if any(member.kind != FIXED for member in self.members):
            return None
        return sum(member.width or 0 for member in self.members)

    @property
    def has_variable_member(self) -> bool:
        return any(member.kind != FIXED for member in self.members)

    def row(self) -> dict[str, Any]:
        return {
            "unionTag": self.tag,
            "wrapperName": self.wrapper_name,
            "serializedMemberCount": self.member_count,
            "memberWidthSum": self.fixed_body_width,
            "hasVariableMember": self.has_variable_member,
            "members": [member.row() for member in self.members],
        }


def derived_fixed_width_routes(
    *, gameassembly: Path | None = None, metadata: Path | None = None,
    include_strings: bool = True,
) -> tuple[dict[int, DerivedRoute], dict[str, Any]]:
    """Every dispatcher tag this reader can consume end to end, or nothing.

    A member qualifies when its width is fixed by its type, or when it is a
    string, whose length-prefixed framing the frozen reader already proves. A
    tag with any other member kind is left to the frozen reader.
    """
    routes, audit = load_action_routes(gameassembly=gameassembly, metadata=metadata)
    if audit["status"] != "validated":
        return {}, audit
    selected: dict[int, DerivedRoute] = {}
    for tag, route in routes.items():
        if route.status != "resolved" or not route.member_order:
            continue
        members: list[DerivedMember] = []
        for name, kind, width in zip(
            route.member_order, route.member_kinds, route.member_widths
        ):
            if width is not None:
                members.append(DerivedMember(name, FIXED, width))
            elif kind == "string" and include_strings:
                members.append(DerivedMember(name, STRING))
            else:
                break
        if len(members) != len(route.member_order):
            continue
        selected[tag] = DerivedRoute(
            tag=tag,
            wrapper_name=route.wrapper_name or "",
            member_count=len(route.member_order),
            members=tuple(members),
        )
    audit = dict(
        audit,
        derivedRoutes=len(selected),
        fixedWidthRoutes=sum(
            1 for route in selected.values() if not route.has_variable_member
        ),
    )
    return selected, audit


class DerivedFixedWidthMixin:
    """Adds the derived fixed-width routes to whatever reader it is mixed into.

    Kept separate from a concrete base so the same behaviour can be layered onto
    the frozen reader for a direct decode and onto the residual reader the
    corpus census drives, without either being edited.
    """

    derived_routes: dict[int, DerivedRoute] = {}

    def __init__(self, *args: Any, routes: dict[int, DerivedRoute] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.derived_routes = routes if routes is not None else type(self).derived_routes
        self.derived_tags_read: list[int] = []

    def _action(self, depth: int, tag: int, width: int) -> None:
        route = self.derived_routes.get(tag)
        if route is None:
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
        self._read_fixed_width(route, width)

    def _read_fixed_width(self, route: DerivedRoute, width: int) -> None:
        self.take(width, "union-tag")
        if self.peek() == NULL_WRAPPER:
            self.take(1, "null-wrapper")
            return
        self.header(route.member_count)
        for member in route.members:
            if member.kind == FIXED:
                self.take(member.width or 0, f"derived:{member.name}")
            else:
                # The frozen reader's proven length-prefixed payload framing.
                self.byte_payload()
        self.derived_tags_read.append(route.tag)


class DerivedActionReader(DerivedFixedWidthMixin, _FrozenReader):
    """The frozen reader plus the derived fixed-width routes."""


def reader_subclass(base: type, routes: dict[int, DerivedRoute]) -> type:
    """A subclass of ``base`` that also admits ``routes``.

    Used to substitute a reader the census constructs by name, so the census
    runs unchanged against the derived routes.
    """
    return type(
        f"Derived{base.__name__}", (DerivedFixedWidthMixin, base),
        {"derived_routes": routes},
    )


@contextlib.contextmanager
def derived_reader_patches(routes: dict[int, DerivedRoute]) -> Iterable[None]:
    """Substitute the readers the BuffData census constructs, for one run.

    This is how the derived routes are exercised by the authenticated census
    without editing it: both reader names it builds through are replaced by
    subclasses that add the routes and delegate everything else.
    """
    from scripts.game_data.memorypack import buff_actions, buff_residual_actions

    targets = (
        (buff_actions, "Reader"),
        (buff_residual_actions, "_ResidualReader"),
    )
    originals = [(module, name, getattr(module, name)) for module, name in targets]
    try:
        for module, name, original in originals:
            setattr(module, name, reader_subclass(original, routes))
        yield
    finally:
        for module, name, original in originals:
            setattr(module, name, original)


def synthesize(route: DerivedRoute) -> bytes:
    """One record in the derived framing: tag, header, then each member.

    Member bytes are filler except the leading boolean, which the frozen
    reader requires to be 0 or 1. The bytes carry no meaning; only the
    record's framing is under test.
    """
    body = bytearray()
    for index, member in enumerate(route.members):
        if member.kind != FIXED:
            body += struct.pack("<i", 0)      # an empty length-prefixed payload
        elif index == 0 and member.width == 1:
            body += bytes([1])
        else:
            body += bytes(member.width or 0)
    tag = (bytes([route.tag]) if route.tag < WIDE_TAG_LEAD
           else bytes([WIDE_TAG_LEAD]) + struct.pack("<H", route.tag))
    return bytes(tag) + bytes([route.member_count]) + bytes(body)


def _consume(reader: _FrozenReader) -> tuple[str, int]:
    """Read one action, returning the outcome and the cursor it reached."""
    try:
        reader.action(0)
    except Unsupported:
        return "unsupported", reader.pos
    except Exception:
        return "failed", reader.pos
    return "read", reader.pos


def cross_check(routes: dict[int, DerivedRoute]) -> dict[str, Any]:
    """Check the derived framing against the frozen reader, tag by tag.

    A tag the frozen reader already admits is the real test: the frozen
    routes are reviewed and corpus-validated, so if a record built from the
    derived member count and widths is consumed by the frozen reader and ends
    exactly where the derivation says it should, the two framings agree.

    A tag the frozen reader rejects cannot be checked this way. For those the
    derived reader is only shown to be self-consistent, which is not evidence
    that the bytes in a real payload have that shape.
    """
    shared = {"checked": 0, "agreed": 0, "disagreed": 0}
    new = {"checked": 0, "selfConsistent": 0, "inconsistent": 0}
    failures: list[dict[str, Any]] = []
    for tag in sorted(routes):
        route = routes[tag]
        record = synthesize(route)
        expected = len(record)
        frozen_outcome, frozen_pos = _consume(_FrozenReader(record, f"tag-{tag:#x}"))
        if frozen_outcome == "unsupported":
            new["checked"] += 1
            outcome, pos = _consume(
                DerivedActionReader(record, f"tag-{tag:#x}", routes=routes)
            )
            if outcome == "read" and pos == expected:
                new["selfConsistent"] += 1
            else:
                new["inconsistent"] += 1
                failures.append({"unionTag": tag, "wrapperName": route.wrapper_name,
                                 "class": "derived", "outcome": outcome,
                                 "reached": pos, "expected": expected})
            continue
        shared["checked"] += 1
        if frozen_outcome == "read" and frozen_pos == expected:
            shared["agreed"] += 1
        else:
            shared["disagreed"] += 1
            failures.append({"unionTag": tag, "wrapperName": route.wrapper_name,
                             "class": "frozen", "outcome": frozen_outcome,
                             "reached": frozen_pos, "expected": expected})
    return {"frozenAdmittedTags": shared, "derivedOnlyTags": new, "failures": failures}


def probe() -> dict[str, Any]:
    """Derive the routes and cross-check their framing against the frozen reader."""
    started = time.perf_counter()
    routes, audit = derived_fixed_width_routes()
    result = cross_check(routes) if routes else {}
    return {
        "schema": "endfield.memorypack-derived-actions-probe.v2",
        "audit": audit,
        "routeCount": len(routes),
        "crossCheck": result,
        "summary": {
            "status": audit["status"],
            "routes": len(routes),
            "frozenAgreed": result.get("frozenAdmittedTags", {}).get("agreed"),
            "frozenChecked": result.get("frozenAdmittedTags", {}).get("checked"),
            "derivedOnly": result.get("derivedOnlyTags", {}).get("checked"),
            "failures": len(result.get("failures", [])),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "routes": [routes[tag].row() for tag in sorted(routes)],
        "boundary": (
            "Agreement on the tags the frozen reader admits shows the derived member "
            "count and widths reproduce a reviewed, corpus-validated framing. The "
            "remaining tags are only shown to be self-consistent; that a real payload "
            "has this shape is established by a whole-corpus run, not by this probe."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--list-routes", action="store_true",
                        help="print the derived fixed-width routes and exit")
    args = parser.parse_args()
    if args.list_routes:
        routes, audit = derived_fixed_width_routes()
        if audit["status"] != "validated":
            print(json.dumps(audit, ensure_ascii=False), file=sys.stderr)
            return 1
        for tag in sorted(routes):
            print(json.dumps(routes[tag].row(), ensure_ascii=False))
        return 0
    output = args.output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        print(json.dumps({"status": "failed", "detail": f"output-must-be-under={reports}"}),
              file=sys.stderr)
        return 1
    try:
        report = probe()
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
