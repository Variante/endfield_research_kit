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
"""
from __future__ import annotations

import argparse
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


@dataclass(frozen=True)
class FixedWidthRoute:
    """One tag whose whole body is a fixed-width field sequence."""

    tag: int
    wrapper_name: str
    member_count: int
    members: tuple[tuple[str, int], ...]

    @property
    def body_width(self) -> int:
        return sum(width for _name, width in self.members)

    def row(self) -> dict[str, Any]:
        return {
            "unionTag": self.tag,
            "wrapperName": self.wrapper_name,
            "serializedMemberCount": self.member_count,
            "memberWidthSum": self.body_width,
            "members": [{"name": name, "width": width} for name, width in self.members],
        }


def derived_fixed_width_routes(
    *, gameassembly: Path | None = None, metadata: Path | None = None
) -> tuple[dict[int, FixedWidthRoute], dict[str, Any]]:
    """Every dispatcher tag whose members are all fixed-width, or nothing."""
    routes, audit = load_action_routes(gameassembly=gameassembly, metadata=metadata)
    if audit["status"] != "validated":
        return {}, audit
    selected: dict[int, FixedWidthRoute] = {}
    for tag, route in routes.items():
        if route.status != "resolved" or route.member_width_sum is None:
            continue
        members = tuple(
            (name, width)
            for name, width in zip(route.member_order, route.member_widths)
            if width is not None
        )
        if len(members) != len(route.member_order):
            # A width the derivation could not fix means the body is not a
            # known length; such a tag is left to the frozen reader.
            continue
        selected[tag] = FixedWidthRoute(
            tag=tag,
            wrapper_name=route.wrapper_name or "",
            member_count=len(route.member_order),
            members=members,
        )
    audit = dict(audit, fixedWidthRoutes=len(selected))
    return selected, audit


class DerivedActionReader(_FrozenReader):
    """The frozen reader plus the derived fixed-width routes.

    ``routes`` is supplied by the caller rather than loaded here, so a decode
    never reaches for the installed build on its own and a test can drive the
    reader with an explicit table.
    """

    def __init__(
        self,
        data: bytes,
        source: str,
        limit: int | None = None,
        *,
        routes: dict[int, FixedWidthRoute] | None = None,
    ) -> None:
        super().__init__(data, source, limit)
        self.derived_routes = routes or {}
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

    def _read_fixed_width(self, route: FixedWidthRoute, width: int) -> None:
        self.take(width, "union-tag")
        if self.peek() == NULL_WRAPPER:
            self.take(1, "null-wrapper")
            return
        self.header(route.member_count)
        for name, member_width in route.members:
            self.take(member_width, f"derived:{name}")
        self.derived_tags_read.append(route.tag)


def synthesize(route: FixedWidthRoute) -> bytes:
    """One record in the derived framing: tag, header, then each member.

    Member bytes are filler except the leading boolean, which the frozen
    reader requires to be 0 or 1. The bytes carry no meaning; only the
    record's framing is under test.
    """
    body = bytearray()
    for index, (_name, width) in enumerate(route.members):
        body += bytes([1]) if index == 0 and width == 1 else bytes(width)
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


def cross_check(routes: dict[int, FixedWidthRoute]) -> dict[str, Any]:
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
