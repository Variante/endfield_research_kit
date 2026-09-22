"""Name the exported MonoBehaviour script classes from IL2CPP metadata.

[`monobehaviour_census.py`](monobehaviour_census.py) collapses the exported
MonoBehaviour corpus to a few hundred anonymous script identities and records
the serialized field layout of each. This module supplies the missing half:
which managed class each layout belongs to, read out of the selected build's
`global-metadata.dat`.

The join is structural, not nominal. For a managed class, IL2CPP records the
fields each type in its inheritance chain declares, in declaration order. Unity
serializes a subset of that chain -- constants, statics, events, caches and
`[NonSerialized]` members are skipped -- but it never reorders what remains.
So a class's serialized TypeTree field list must be an **ordered subsequence**
of its own base-to-derived declaration chain. That is a strong necessary
condition, and it needs no field-attribute decoding, which the metadata helper
does not expose.

Selecting the right class in a chain needs one more rule. Every base of the
true class also passes the subsequence test on a shorter list, so a candidate
is accepted only when it *declares the last serialized field itself*. That
picks the most-derived class instead of an arbitrary ancestor.

Three deliberate refusals keep a name from outrunning its evidence:

- a candidate must descend from `UnityEngine.MonoBehaviour` or
  `UnityEngine.ScriptableObject`, because nothing else serializes as class 114;
- when several classes satisfy every rule, all of them are reported and the row
  stays `ambiguous`. A field-count coincidence is not an identity;
- a class whose own declared fields are all unserialized cannot satisfy the
  terminal rule, and is reported `underdetermined` rather than guessed at from
  its base.

A name from this module identifies the *layout*. It does not establish what the
object owns, when it runs, or that any instance is reachable at runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp_method_resolver import ResolverError, open_resolver
from scripts.game_data.monoscript_catalog import CatalogError, load_catalog


SCHEMA = "endfield.monobehaviour-script-names.v1"

# Unity writes these before any managed field: they come from the native
# Behaviour/MonoBehaviour base and have no metadata field declaration, so they
# are stripped before the chain is compared.
NATIVE_MONOBEHAVIOUR_HEADER = ("m_GameObject", "m_Enabled", "m_Script", "m_Name")

SERIALIZABLE_ROOTS = ("UnityEngine.MonoBehaviour", "UnityEngine.ScriptableObject")

# ``RigConstraint`3``: IL2CPP spells an open generic's arity after a backtick.
OPEN_GENERIC_NAME = re.compile(r"`\d+$")


def top_level_fields(field_paths: list[str]) -> list[str]:
    """Reduce recorded ``name:type`` paths to the top-level field names.

    The census records every node's dotted path. Only the depth-one entries are
    the class's own serialized fields; the rest describe their contents.
    """

    names: list[str] = []
    for entry in field_paths:
        path = entry.split(":", 1)[0]
        if "." in path or not path:
            continue
        if not names or names[-1] != path:
            names.append(path)
    return names


def strip_native_header(names: list[str]) -> list[str]:
    """The managed part of one layout: top-level fields after the native header."""

    index = 0
    for expected in NATIVE_MONOBEHAVIOUR_HEADER:
        if index < len(names) and names[index] == expected:
            index += 1
    return names[index:]


def is_ordered_subsequence(wanted: list[str], available: list[str]) -> bool:
    """Whether ``wanted`` appears inside ``available`` in the same order."""

    cursor = iter(available)
    return all(name in cursor for name in wanted)


class ScriptNamer:
    """Match serialized layouts against the selected build's managed classes."""

    def __init__(self, resolver: Any) -> None:
        self.metadata = resolver.metadata
        self._typedef_by_type_index: dict[int, int] = {}
        for type_def in self.metadata.types:
            byval = type_def.byval_type_index
            if byval is not None and byval >= 0:
                self._typedef_by_type_index.setdefault(byval, type_def.index)
        self._candidates = self._collect_candidates()
        self._by_full_name: dict[str, list[int]] = {}
        for index in range(len(self.metadata.types)):
            self._by_full_name.setdefault(self.full_name(index), []).append(index)

    # -- chains -----------------------------------------------------------

    def _declared_fields(self, type_index: int) -> list[str]:
        type_def = self.metadata.types[type_index]
        if type_def.field_count <= 0 or type_def.field_start < 0:
            return []
        return [
            self.metadata.string(self.metadata.fields[position].name_index)
            for position in range(
                type_def.field_start, type_def.field_start + type_def.field_count
            )
        ]

    @lru_cache(maxsize=None)
    def _ancestry(self, type_index: int) -> tuple[int, ...]:
        """Base-to-derived typedef chain, ending at ``type_index``."""

        seen: list[int] = []
        cursor: int | None = type_index
        guard = 0
        while cursor is not None and guard < 64:
            if cursor in seen:
                break
            seen.append(cursor)
            parent = self.metadata.types[cursor].parent_index
            cursor = self._typedef_by_type_index.get(parent)
            guard += 1
        return tuple(reversed(seen))

    @lru_cache(maxsize=None)
    def chain_fields(self, type_index: int) -> tuple[str, ...]:
        names: list[str] = []
        for ancestor in self._ancestry(type_index):
            names.extend(self._declared_fields(ancestor))
        return tuple(names)

    def full_name(self, type_index: int) -> str:
        return self.metadata.type_full_name(self.metadata.types[type_index])

    # -- candidates -------------------------------------------------------

    def _collect_candidates(self) -> list[int]:
        roots = {
            index
            for index in range(len(self.metadata.types))
            if self.full_name(index) in SERIALIZABLE_ROOTS
        }
        if not roots:
            return []
        candidates: list[int] = []
        for index in range(len(self.metadata.types)):
            ancestry = self._ancestry(index)
            if index in roots:
                continue
            if any(ancestor in roots for ancestor in ancestry):
                candidates.append(index)
        return candidates

    def describes_a_descendant(self, ancestor_name: str, candidate_name: str) -> bool:
        """Whether ``candidate_name`` inherits from ``ancestor_name``.

        The layout route names the most-derived class that *contributes a
        serialized field*. A subclass below it that adds none -- or adds only
        unserialized ones -- writes the same layout, so naming the ancestor is
        a less specific answer, not a wrong one. Generic bases make this common:
        a constraint deriving from ``RigConstraint`3`` serializes exactly the
        base's fields.
        """

        for index in self._by_full_name.get(candidate_name, ()):  # usually one
            if any(
                self.full_name(ancestor) == ancestor_name
                for ancestor in self._ancestry(index)
            ):
                return True
        return False

    @lru_cache(maxsize=None)
    def _silent_subclasses(self, type_index: int) -> tuple[str, ...]:
        """Descendants that declare no field beyond ``type_index``'s chain.

        Unity serializes fields, not type names, so such a subclass writes a
        byte-identical layout. It is a genuine alternative identity for the
        row, not a near miss.
        """

        base_chain = self.chain_fields(type_index)
        names: list[str] = []
        for candidate in self._candidates:
            if candidate == type_index:
                continue
            ancestry = self._ancestry(candidate)
            if type_index not in ancestry:
                continue
            if self.chain_fields(candidate) == base_chain:
                names.append(self.full_name(candidate))
        return tuple(names)

    # -- matching ---------------------------------------------------------

    def match(self, field_paths: list[str]) -> dict[str, Any]:
        return self.match_top_level(top_level_fields(field_paths))

    def match_top_level(self, top_level: list[str]) -> dict[str, Any]:
        wanted = strip_native_header(top_level)
        row: dict[str, Any] = {
            "serializedFields": wanted,
            "serializedFieldCount": len(wanted),
        }
        if not wanted:
            row["status"] = "no_serialized_fields"
            return row

        terminal = wanted[-1]
        accepted: list[int] = []
        subsequence_only: list[int] = []
        for index in self._candidates:
            chain = self.chain_fields(index)
            if terminal not in chain:
                continue
            if not is_ordered_subsequence(wanted, list(chain)):
                continue
            subsequence_only.append(index)
            if terminal in self._declared_fields(index):
                accepted.append(index)

        if len(accepted) == 1:
            index = accepted[0]
            row["scriptClass"] = self.full_name(index)
            row["declaredFields"] = self._declared_fields(index)
            row["inheritanceChain"] = [
                self.full_name(ancestor) for ancestor in self._ancestry(index)
            ]
            # A subclass that serializes nothing beyond this class produces the
            # identical layout, so layout evidence alone cannot separate them.
            # Say so instead of letting the base name stand as the identity.
            silent = self._silent_subclasses(index)
            if silent:
                row["status"] = "named_or_silent_subclass"
                # The displayed list is capped; the full set is kept so a
                # cross-check against the script PPtr tests membership rather
                # than whatever happened to fit in the report.
                row["_silentSubclassSet"] = set(silent)
                row["indistinguishableSubclasses"] = sorted(silent)[:12]
                row["indistinguishableSubclassCount"] = len(silent)
            else:
                row["status"] = "named"
            return row
        if accepted:
            row["status"] = "ambiguous"
            row["candidates"] = sorted(self.full_name(index) for index in accepted)
            return row
        if subsequence_only:
            # The layout fits these chains, but no candidate declares its last
            # field, so the most-derived class cannot be separated from a base.
            row["status"] = "underdetermined"
            row["candidates"] = sorted(
                self.full_name(index) for index in subsequence_only
            )[:12]
            row["candidateCount"] = len(subsequence_only)
            return row
        row["status"] = "unmatched"
        return row


def name_census(
    census_report: Path,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
    monoscript_dump: Path | None = None,
) -> dict[str, Any]:
    """Name every class row of a census report against the selected build.

    With a MonoScript dump supplied, the serialized script PPtr answers the
    question outright and the structural match becomes an independent check on
    it. Two methods agreeing is worth recording; disagreement is a finding, and
    is reported rather than resolved in favour of either one.
    """

    document = json.loads(Path(census_report).read_bytes().decode("utf-8-sig"))
    resolver, receipt = open_resolver(gameassembly=gameassembly, metadata=metadata)
    namer = ScriptNamer(resolver)
    catalog = load_catalog(monoscript_dump) if monoscript_dump is not None else {}

    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    objects_by_status: dict[str, int] = {}
    for entry in document.get("classes") or []:
        top_level = entry.get("topLevelFields")
        if isinstance(top_level, list) and top_level:
            # The census records the depth-one names in full, so this route is
            # unaffected by the cap on the nested path list.
            result = namer.match_top_level(
                [name for name in top_level if isinstance(name, str)]
            )
        elif entry.get("fieldPathsTruncated"):
            # A truncated path list cannot be matched as a subsequence: the
            # missing tail is exactly what selects the derived class.
            result = {"status": "layout_truncated"}
        else:
            result = namer.match(entry.get("fieldPaths") or [])
        script_path_id = entry.get("scriptPathId")
        authoritative = catalog.get(script_path_id) if catalog else None
        if authoritative is not None:
            result["scriptPathIdClass"] = authoritative.full_name
            result["scriptAssembly"] = authoritative.assembly
            structural = result.get("scriptClass")
            if structural is None:
                result["agreement"] = "structural_silent"
            elif structural == authoritative.full_name:
                result["agreement"] = "agree"
            elif authoritative.full_name in (
                result.get("_silentSubclassSet") or set()
            ) or namer.describes_a_descendant(structural, authoritative.full_name):
                # The layout route named an ancestor; the PPtr picks the
                # subclass below it. Less specific, not contradictory.
                result["agreement"] = "subclass_selected"
            elif OPEN_GENERIC_NAME.search(structural):
                # A class deriving from a closed generic base has a generic
                # *instance* as its metadata parent, not a typedef, so the
                # ancestry walk stops at the open generic and the layout route
                # can reach no further. A known structural limit of that route,
                # not a conflict between the two.
                result["agreement"] = "generic_base_only"
            else:
                result["agreement"] = "disagree"
            result["status"] = "named_from_script_pptr"
        elif catalog:
            result["agreement"] = "script_pptr_absent"

        result.pop("_silentSubclassSet", None)
        objects = int(entry.get("objects") or 0)
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        objects_by_status[result["status"]] = (
            objects_by_status.get(result["status"], 0) + objects
        )
        rows.append(
            {
                "scriptPathId": script_path_id,
                "layoutSignature": entry.get("layoutSignature"),
                "objects": objects,
                "exampleNames": entry.get("exampleNames") or [],
                **result,
            }
        )

    rows.sort(key=lambda row: (-row["objects"], str(row.get("layoutSignature"))))
    total_objects = sum(row["objects"] for row in rows)
    named_objects = objects_by_status.get("named", 0) + objects_by_status.get(
        "named_from_script_pptr", 0
    )
    agreement: dict[str, int] = {}
    for row in rows:
        if "agreement" in row:
            agreement[row["agreement"]] = agreement.get(row["agreement"], 0) + 1
    return {
        "schema": SCHEMA,
        "censusReport": str(census_report),
        "nativeInputs": receipt,
        "summary": {
            "classes": len(rows),
            "byStatus": dict(sorted(counts.items())),
            "objectsByStatus": dict(sorted(objects_by_status.items())),
            "structuralAgreement": dict(sorted(agreement.items())),
            "objectsNamedShare": (
                round(named_objects / total_objects, 4) if total_objects else 0.0
            ),
        },
        "classes": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Name the MonoBehaviour script classes of a census report by "
            "matching each serialized layout to the selected build's managed "
            "class declaration chains."
        )
    )
    parser.add_argument("census_report", type=Path)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument(
        "--monoscript-dump",
        type=Path,
        help=(
            "MonoScript dump directory; its script PPtrs name the classes "
            "outright and the structural match becomes a cross-check"
        ),
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        report = name_census(
            args.census_report,
            gameassembly=args.gameassembly,
            metadata=args.metadata,
            monoscript_dump=args.monoscript_dump,
        )
    except (ResolverError, CatalogError) as exc:
        print(f"script naming unavailable: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"census report unreadable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        summary = report["summary"]
        print(
            f"named {summary['byStatus'].get('named', 0)} of {summary['classes']} "
            f"script classes covering {summary['objectsNamedShare']:.1%} of objects "
            f"-> {args.report}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.monobehaviour_script_names")
    raise SystemExit(main())
