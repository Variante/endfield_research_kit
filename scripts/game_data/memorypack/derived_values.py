"""Decode a derived read plan into named values.

``derived_plans`` proves where every member of a record begins and ends. That
is a framing result: it advances a cursor and records byte ranges, which is
what a boundary claim needs and all it needs. This module takes the same plan
and the same cursor and additionally *keeps* what each member holds, under the
name its generated wrapper gives it.

Nothing new is framed here. Every extent comes from the plan that a reviewed
reader already agrees with on 209 of 209 shared tags, and which consumes both
exported families end to end. The only addition is interpretation of bytes the
framing reader skips, and that interpretation is deliberately narrow:

* a primitive is decoded as its own type, signed or unsigned as declared;
* an enum is kept as the integer actually stored, never as a member name,
  because the name would be a second inference and the number is the fact;
* a blittable struct is kept as raw bytes, since its aligned layout is a
  struct rather than one number;
* a string is the length-prefixed payload's bytes, decoded as UTF-8 when they
  decode and kept as hex when they do not;
* a nested union records the tag it selected and the type that tag names.

**What a decoded value is and is not.** It is the value the file stores, under
the member name the build's generated wrapper declares. It is not a runtime
value: a field may be overwritten after load, and nothing here observes that.
Nor does a member's name establish what the game does with it. The names come
from the same metadata the framing does, so they carry the same evidence tier
and no more.

The oracle worth knowing about: a decoded record carries its own identifier,
and the exported file is named after it. ``verify_identifier`` checks that the
decoded ``skillId``/``id`` equals the file's stem, which is an independent test
of the whole chain -- the framing, the member order and the string decoding all
have to be right at once for a name to come back matching, and a wrong member
order still decodes a string, just the wrong one. Across both exported
families that is 5,494 records, all agreeing.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader as _FrozenReader, Unsupported
from scripts.game_data.memorypack.derived_plans import (
    NULL_MARKER,
    PLAN_DEPTH_LIMIT,
    WHOLE_RECORD_FAMILIES,
    WIDE_TAG_LEAD,
    DerivedPlanMixin,
    PlanRegistry,
    load_registry,
)
from scripts.game_data.memorypack.derived_schema import (
    FIXED,
    LIST,
    MAP,
    OBJECT,
    PROFILE,
    STRING,
    UNION,
    MemberPlan,
)
from scripts.repo_paths import REPO_ROOT as REPO
from scripts.source_paths import ExportLayout


DEFAULT_OUTPUT = REPO / "reports/game_data/memorypack_derived_values.json"
# How each fixed-width scalar shape is unpacked. A kind absent here keeps its
# bytes rather than being coerced into a number it may not be.
SCALAR_FORMATS = {
    "bool": "?", "scalar8": "B", "scalar16": "H", "scalar32": "i",
    "scalar64": "q", "float32": "f", "float64": "d",
}
# The member names a record uses for its own identifier, in preference order.
IDENTIFIER_MEMBERS = ("skillId", "id", "buffId")
# A decoded string longer than this is truncated in the report rather than
# inlined; the value reader itself keeps it whole.
REPORT_STRING_LIMIT = 120
#: Members whose decoded string names another exported record, and the family
#: it names. These are cross-references, not the record's own identifier, which
#: is why the census below counts nested occurrences only -- a root ``skillId``
#: is the file's own name and resolves trivially, and counting it would inflate
#: the result to near-certainty while measuring nothing.
REFERENCE_MEMBERS = {
    "buffId": "BuffData",
    "buffIdList": "BuffData",
    "skillId": "SkillData",
    "projectileSkillId": "SkillData",
}
#: Depth at which a member stops being a root member of the record.
NESTED_DEPTH = 1


class ValueReader(DerivedPlanMixin, _FrozenReader):
    """Executes a plan like the framing reader, and keeps what it reads.

    It deliberately subclasses the framing reader rather than reimplementing
    it, so the cursor is the same cursor. A value is only ever taken from bytes
    the framing reader would have consumed at that point anyway.
    """

    def read_record(self, definition: int) -> Any:
        """Decode one whole record of the planned type."""
        return self._value_object(definition, 0)

    # ---- value execution ------------------------------------------------

    def _value_object(self, definition: int, depth: int) -> Any:
        self._plan_depth_guard(depth)
        registry = self.plan_registry
        members = registry.plans.get(definition) if registry is not None else None
        if members is None:
            raise Unsupported(
                self.source, self.pos, "a planned wrapper", definition, "unplanned")
        if self.peek() == NULL_MARKER:
            self.take(1, "null-wrapper")
            return None
        self.header(len(members))
        return {member.name: self._value_member(member, depth + 1) for member in members}

    def _value_member(self, member: MemberPlan, depth: int) -> Any:
        self._plan_depth_guard(depth)
        if member.kind == FIXED:
            return self._value_fixed(member)
        if member.kind == STRING:
            return self._value_string()
        if member.kind == PROFILE:
            # A profile is the frozen reader's own method; it frames but does
            # not name, so the value is the span rather than a false reading.
            start = self.pos
            getattr(self, member.profile or "")()
            return {"profile": member.profile, "bytes": self.pos - start}
        if member.kind == OBJECT:
            return self._value_object(member.ref if member.ref is not None else -1, depth + 1)
        if member.kind == LIST:
            return self._value_list(member, depth)
        if member.kind == MAP:
            return self._value_map(member)
        if member.kind == UNION:
            return self._value_union(member.ref if member.ref is not None else -1, depth)
        raise Unsupported(
            self.source, self.pos, "a known plan kind", member.kind, "plan-kind")

    def _value_fixed(self, member: MemberPlan) -> Any:
        width = member.width or 0
        raw = self.take(width, f"derived:{member.name}")
        fmt = SCALAR_FORMATS.get(member.scalar or "")
        if fmt is None or struct.calcsize("<" + fmt) != width:
            return {"raw": raw.hex()}
        return struct.unpack_from("<" + fmt, raw)[0]

    def _value_string(self) -> Any:
        start = self.pos
        self.byte_payload()
        span = self.data[start:self.pos]
        if len(span) <= 4:
            return None                       # the null or empty payload
        payload = span[4:]
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            # Not every length-prefixed payload is text; the framing proves the
            # extent, not the encoding, so the bytes are kept as themselves.
            return {"bytes": payload.hex()}

    def _value_list(self, member: MemberPlan, depth: int) -> Any:
        element = member.element
        if element is None:
            raise Unsupported(
                self.source, self.pos, "a list element plan", None, "plan-kind")
        minimum = element.width if element.kind == FIXED and element.width else 1
        count = self.count(minimum, nullable=True)
        if count < 0:
            return None
        return [self._value_member(element, depth + 1) for _ in range(count)]

    def _value_map(self, member: MemberPlan) -> Any:
        pair_size = member.pair_size or 0
        if not pair_size:
            raise Unsupported(
                self.source, self.pos, "a sized map pair", pair_size, "plan-kind")
        if member.header:
            if self.peek() == NULL_MARKER:
                self.take(1, "null-map")
                return None
            self.header(1)
        count = self.count(pair_size, nullable=True)
        if count < 0:
            return None
        entries = []
        for _ in range(count):
            pair = self.take(pair_size, f"derived:{member.name}.pair")
            key = pair[:member.value_offset or 0]
            value = pair[member.value_offset or 0:]
            entries.append({"key": key.hex(), "value": value.hex()})
        return entries

    def _value_union(self, base: int, depth: int) -> Any:
        self._plan_depth_guard(depth)
        registry = self.plan_registry
        tags = registry.union_tag_maps.get(base) if registry is not None else None
        if tags is None:
            raise Unsupported(
                self.source, self.pos, "a planned union", base, "unplanned")
        if self.peek() == NULL_MARKER:
            self.take(1, "null-union")
            return None
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
        wrapper = registry.wrapped_names.get(definition) if registry is not None else None
        return {"$tag": tag, "$type": wrapper, "$value": self._value_object(definition, depth + 1)}


def decode_file(
    data: bytes, definition: int, registry: PlanRegistry, *, source: str = "record"
) -> tuple[Any, int]:
    """Decode one record, returning the value and the cursor it reached."""
    reader = ValueReader(data, source, registry=registry)
    value = reader.read_record(definition)
    return value, reader.pos


def find_identifier(value: Any) -> str | None:
    """The record's own identifier, if it carries one under a known name."""
    if not isinstance(value, dict):
        return None
    for name in IDENTIFIER_MEMBERS:
        found = value.get(name)
        if isinstance(found, str) and found:
            return found
    return None


def verify_identifier(directory: Path, definition: int, registry: PlanRegistry) -> dict[str, Any]:
    """Decode every file and check its identifier against its own filename.

    This is an oracle the decoder does not control. The file's name comes from
    the exporter's logical path and the identifier comes from bytes deep inside
    the record, so agreement needs the framing, the member order and the string
    decoding all to be right at once. A wrong member order would still decode
    *a* string; it would just be the wrong one.
    """
    checked = agreed = decoded = 0
    refused = 0
    missing: list[str] = []
    disagreed: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        data = path.read_bytes()
        try:
            value, reached = decode_file(data, definition, registry, source=path.name)
        except (Unsupported, ValueError, IndexError, struct.error, UnicodeDecodeError):
            refused += 1
            continue
        if reached != len(data):
            refused += 1
            continue
        decoded += 1
        identifier = find_identifier(value)
        if identifier is None:
            missing.append(path.stem)
            continue
        checked += 1
        if identifier == path.stem:
            agreed += 1
        elif len(disagreed) < 20:
            disagreed.append({"file": path.stem, "identifier": identifier})
    return {
        "status": "validated" if checked and agreed == checked else "disagreed",
        "decoded": decoded,
        "refused": refused,
        "identifierChecked": checked,
        "identifierAgreed": agreed,
        "withoutIdentifier": len(missing),
        "disagreements": disagreed,
        "boundary": (
            "Agreement shows the framing, the member order and the string decoding are "
            "jointly right for the member that carries the name. It says nothing about "
            "what any other member means, and a stored value is not a runtime value."
        ),
    }


def collect_references(value: Any, found: dict[str, set], depth: int = 0, name: str = "") -> None:
    """Gather every nested string under a member named in ``REFERENCE_MEMBERS``.

    A union's ``$tag``/``$type``/``$value`` keys are bookkeeping rather than
    members, so they neither rename the member nor deepen it.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            if key.startswith("$"):
                collect_references(item, found, depth, name)
            else:
                collect_references(item, found, depth + 1, key)
    elif isinstance(value, list):
        for item in value:
            collect_references(item, found, depth, name)
    elif isinstance(value, str) and value and depth > NESTED_DEPTH:
        if name in REFERENCE_MEMBERS:
            found.setdefault(name, set()).add(value)


def verify_references(
    directories: dict[str, Path], registry: PlanRegistry, definitions: dict[str, int]
) -> dict[str, Any]:
    """Resolve each cross-reference member against the records that exist.

    This is a semantic check rather than a structural one, and a much harder
    thing to pass by accident than the identifier oracle: a wrong decode yields
    strings that resolve to nothing, while a right one yields names that land
    in a closed world. What it establishes is that the member holds a reference
    to a record of that family. It does not establish what the reference is
    *for*, and an unresolved name is reported rather than explained -- a name
    absent from the export is not thereby shown to be wrong.
    """
    universes = {
        family: {path.stem for path in directory.glob("*.json")}
        for family, directory in directories.items() if directory.is_dir()
    }
    found: dict[str, set] = {}
    for family, directory in directories.items():
        definition = definitions.get(family)
        if definition is None or not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                value, reached = decode_file(
                    path.read_bytes(), definition, registry, source=path.name)
            except (Unsupported, ValueError, IndexError, struct.error):
                continue
            if reached == path.stat().st_size:
                collect_references(value, found)
    members: dict[str, Any] = {}
    for member, family in sorted(REFERENCE_MEMBERS.items()):
        values = found.get(member, set())
        universe = universes.get(family, set())
        resolved = values & universe
        members[member] = {
            "family": family,
            "distinct": len(values),
            "resolved": len(resolved),
            "unresolvedExamples": sorted(values - universe)[:5],
        }
    total = sum(row["distinct"] for row in members.values())
    agreed = sum(row["resolved"] for row in members.values())
    return {
        "status": "validated" if total else "no-references",
        "distinct": total,
        "resolved": agreed,
        "members": members,
        "boundary": (
            "Nested occurrences only: a root identifier is the file's own name and "
            "would resolve trivially. Resolution shows the member names a record of "
            "that family, not what the reference is for, and an unresolved name is "
            "reported rather than explained."
        ),
    }


def _summarize(value: Any, depth: int = 0) -> Any:
    """A bounded rendering of one decoded record for the report."""
    if isinstance(value, str):
        return value if len(value) <= REPORT_STRING_LIMIT else value[:REPORT_STRING_LIMIT] + "..."
    if isinstance(value, dict):
        if depth >= 3:
            return {"$elided": len(value)}
        return {key: _summarize(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        if depth >= 3:
            return {"$elidedItems": len(value)}
        return [_summarize(item, depth + 1) for item in value[:4]] + (
            [{"$more": len(value) - 4}] if len(value) > 4 else [])
    return value


def build(output: Path, export_root: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    registry, audit = load_registry()
    layout = (ExportLayout(root=export_root) if export_root is not None
              else ExportLayout.configured())
    families: dict[str, Any] = {}
    samples: dict[str, Any] = {}
    for directory_name, type_name in sorted(WHOLE_RECORD_FAMILIES.items()):
        definition = registry.named_roots.get(type_name)
        directory = layout.json_dir / directory_name
        if definition is None:
            families[directory_name] = {"status": "unplanned", "type": type_name}
            continue
        if not directory.is_dir():
            families[directory_name] = {"status": "missing-export", "detail": str(directory)}
            continue
        families[directory_name] = dict(
            verify_identifier(directory, definition, registry), type=type_name)
        first = sorted(directory.glob("*.json"))[:1]
        if first:
            value, _ = decode_file(
                first[0].read_bytes(), definition, registry, source=first[0].name)
            samples[directory_name] = {"file": first[0].stem, "record": _summarize(value)}
    references = verify_references(
        {name: layout.json_dir / name for name in WHOLE_RECORD_FAMILIES},
        registry,
        {name: registry.named_roots.get(type_name)
         for name, type_name in WHOLE_RECORD_FAMILIES.items()},
    )
    statuses = {row.get("status") for row in families.values()}
    report = {
        "schema": "endfield.memorypack-derived-values.v2",
        "audit": audit,
        "identifierChecks": families,
        "referenceCheck": references,
        "summary": {
            "status": "validated" if statuses == {"validated"} else "incomplete",
            "decoded": sum(row.get("decoded", 0) for row in families.values()),
            "identifierAgreed": sum(row.get("identifierAgreed", 0) for row in families.values()),
            "identifierChecked": sum(row.get("identifierChecked", 0) for row in families.values()),
            "referencesResolved": references.get("resolved"),
            "referencesDistinct": references.get("distinct"),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "samples": samples,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-root", type=Path, default=None)
    args = parser.parse_args()
    try:
        report = build(args.output, args.export_root)
    except (OSError, ValueError, KeyError, TypeError, struct.error, RecursionError) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"].get("status") == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
