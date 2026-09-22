"""Find the MonoBehaviour fields whose values are keys into an exported Table.

[`monobehaviour_field_semantics.py`](monobehaviour_field_semantics.py) says
which fields hold strings and what those strings look like. It deliberately
stops there: calling a string an id is a reading, and the field census refuses
to make one from a field's name. This module supplies the evidence that reading
needs, by asking whether a field's observed values are actually keys of one of
the 724 exported tables.

**The join has one hard boundary, and it is measured rather than assumed.** Of
the 269,570 distinct table keys, 178,582 are purely numeric and only 0.5% of
those belong to a single table -- ``"1"`` is a key in 94 of them. Non-numeric
keys behave the opposite way: 90.5% of the 90,988 name exactly one table. So a
numeric match carries almost no information and a non-numeric match carries a
great deal, and the two must not be pooled. Numeric value sets are reported as
``numeric_unusable`` rather than matched, which is the difference between a
bounded candidate list and several thousand invented table references.

Three further refusals:

- **Every observed value must be a key of the same table** for a ``key_of``.
  Anything short of that is reported by how much its best table covers:
  ``mostly_key_of`` when one table holds most of the values, which makes the
  remainder a finding worth chasing, and ``partial`` when no table comes close,
  which makes the field an unrelated name space that collided rather than a key
  field with exceptions.
- **A match to several tables stays several.** 9.5% of non-numeric keys appear
  in more than one table, so a field can legitimately match more than one and
  the row names them all instead of choosing.
- **A match is a candidate, not a proven reference.** It says the values are
  drawn from that table's key set. It does not establish that anything reads
  the field as a key, and the evidence order in
  ``memory/game_data/unity_assets.md`` is what decides how far that goes.

The values checked are the ones the field census recorded, which is a bounded
sample of each field's distinct values, taken in sorted order. Every row
carries how many values were available to check, because a field matched on two
values is not a field matched on sixty-four.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.monobehaviour-table-keys.v1"

DEFAULT_TABLE_ROOT = REPO_ROOT / "export_full" / "game" / "Table"
DEFAULT_SEMANTICS_REPORT = REPO_ROOT / "reports" / "assets" / "monobehaviour_field_semantics.json"

#: Below this many checked values a match is reported but flagged, because a
#: short value set hits a large key space easily.
WEAK_EVIDENCE_VALUES = 3

#: The share of a field's values one table must hold before the field is read
#: as that table's key with exceptions, rather than as an unrelated name space
#: that happens to collide. The distinction is not cosmetic: a field where 63
#: of 64 values belong to no table is not a key field with dangling ids, it is
#: an internal name space whose single hit is noise. Only above this line are
#: the unresolved values worth chasing.
MOSTLY_ONE_TABLE_SHARE = 0.75


class TableKeyError(RuntimeError):
    """An input this join needs could not be read."""


def is_numeric_key(value: str) -> bool:
    """Is this the kind of key that names no table?

    Purely numeric keys are shared across tables so heavily that a match is
    uninformative. Anything with a non-digit character behaves differently and
    is kept.
    """

    return value.lstrip("-").isdigit()


def load_table_keys(table_root: Path = DEFAULT_TABLE_ROOT) -> dict[str, frozenset[str]]:
    """Read every exported table's key set.

    A table is a JSON object keyed by id, so its keys *are* its primary key
    column and need no schema knowledge to collect. A file that is not an
    object is skipped rather than coerced: it is not a keyed table.
    """

    root = Path(table_root)
    if not root.is_dir():
        raise TableKeyError(f"exported Table root not found: {root}")
    tables: dict[str, frozenset[str]] = {}
    for path in sorted(root.glob("*.json")):
        try:
            document = json.loads(path.read_bytes().decode("utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(document, dict):
            continue
        tables[path.stem] = frozenset(k for k in document if isinstance(k, str))
    if not tables:
        raise TableKeyError(f"no keyed tables under {root}")
    return tables


def key_ownership(tables: dict[str, frozenset[str]]) -> dict[str, Any]:
    """Measure how much a match can possibly be worth, before matching."""

    owners: Counter = Counter()
    for keys in tables.values():
        for key in keys:
            owners[key] += 1
    numeric = [key for key in owners if is_numeric_key(key)]
    named = [key for key in owners if not is_numeric_key(key)]
    return {
        "tables": len(tables),
        "distinctKeys": len(owners),
        "numericKeys": len(numeric),
        "numericKeysUniqueToOneTable": sum(1 for key in numeric if owners[key] == 1),
        "namedKeys": len(named),
        "namedKeysUniqueToOneTable": sum(1 for key in named if owners[key] == 1),
    }


def match_values(
    values: list[str],
    tables: dict[str, frozenset[str]],
) -> dict[str, Any]:
    """Decide what, if anything, a field's observed values are keys of.

    A field no table fully covers is split by *how much* its best table covers,
    which is the axis that separates two different things. Above
    `MOSTLY_ONE_TABLE_SHARE` the field is that table's key with exceptions, and
    the exceptions are the finding -- this is how the unresolved cutscene and
    FMV subtitle ids surfaced. Below it the field is an unrelated name space
    that collided: `states[].stateName` matches one table on one value out of
    sixty-one, and calling its other sixty "unresolved ids" would be noise
    presented as evidence. Only the first kind lists its unresolved values.
    """

    usable = [value for value in values if value and not is_numeric_key(value)]
    numeric = [value for value in values if value and is_numeric_key(value)]
    if not usable:
        return {
            "status": "numeric_unusable" if numeric else "no_values",
            "checkedValues": 0,
            "numericValues": len(numeric),
        }

    owners = {value: [] for value in usable}
    for name, keys in tables.items():
        for value in usable:
            if value in keys:
                owners[value].append(name)

    hits_by_table: Counter = Counter()
    for names in owners.values():
        hits_by_table.update(names)
    full = [name for name, hits in hits_by_table.items() if hits == len(usable)]

    row: dict[str, Any] = {
        "checkedValues": len(usable),
        "numericValues": len(numeric),
    }
    if full:
        row["status"] = "key_of" if len(full) == 1 else "key_of_several"
        row["tables"] = sorted(full)
        if len(usable) < WEAK_EVIDENCE_VALUES:
            row["weakEvidence"] = f"matched on {len(usable)} value(s)"
        return row

    if not hits_by_table:
        row["status"] = "no_table"
        return row

    unowned = sorted(value for value, names in owners.items() if not names)
    dominant, dominant_hits = hits_by_table.most_common(1)[0]
    share = dominant_hits / len(usable)
    row["bestTables"] = [
        {"table": name, "hits": hits, "of": len(usable)}
        for name, hits in hits_by_table.most_common(5)
    ]
    row["dominantTable"] = dominant
    row["dominantShare"] = round(share, 4)
    row["valuesInNoTable"] = len(unowned)
    row["valuesInSomeTable"] = len(usable) - len(unowned)
    # A field one table almost covers is that table's key with exceptions, and
    # the exceptions are the finding. A field one table barely touches is an
    # unrelated name space, and its single hit is a collision -- reporting its
    # 63 unmatched values as unresolved ids would be noise dressed as evidence.
    row["status"] = "mostly_key_of" if share >= MOSTLY_ONE_TABLE_SHARE else "partial"
    if unowned and row["status"] == "mostly_key_of":
        row["unresolvedExamples"] = unowned[:8]
        row["unresolvedPrefixes"] = dict(
            Counter(value.split("_")[0] for value in unowned).most_common(5)
        )
    return row


def build_report(
    semantics_report: Path = DEFAULT_SEMANTICS_REPORT,
    table_root: Path = DEFAULT_TABLE_ROOT,
    *,
    min_objects: int = 0,
) -> dict[str, Any]:
    """Join every recorded string field against the exported table key sets."""

    try:
        semantics = json.loads(Path(semantics_report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TableKeyError(f"unreadable field-semantics report {semantics_report}: {exc}") from exc

    tables = load_table_keys(table_root)
    ownership = key_ownership(tables)

    rows: list[dict[str, Any]] = []
    status_counts: Counter = Counter()
    for entry in semantics.get("classes") or []:
        objects = entry.get("objects") or 0
        if objects < min_objects:
            continue
        for field in entry.get("fields") or []:
            string_block = field.get("string")
            if not isinstance(string_block, dict):
                continue
            samples = [s for s in string_block.get("samples") or [] if isinstance(s, str)]
            if not samples:
                continue
            match = match_values(samples, tables)
            status_counts[match["status"]] += 1
            if match["status"] in ("no_table", "no_values", "numeric_unusable"):
                continue
            rows.append(
                {
                    "scriptClass": entry.get("scriptClass"),
                    "objects": objects,
                    "path": field.get("path"),
                    "declaredType": field.get("declaredType"),
                    "classification": field.get("classification"),
                    "distinctSampled": string_block.get("distinctSampled"),
                    "distinctCapped": string_block.get("distinctCapped"),
                    "nonEmpty": string_block.get("nonEmpty"),
                    **match,
                }
            )

    rows.sort(key=lambda row: (-row["objects"], str(row["scriptClass"]), str(row["path"])))
    return {
        "schema": SCHEMA,
        "semanticsReport": str(semantics_report),
        "tableRoot": str(table_root),
        "keyOwnership": ownership,
        "summary": {
            "stringFieldsConsidered": sum(status_counts.values()),
            "byStatus": dict(status_counts.most_common()),
            "reportedFields": len(rows),
            "evidenceBoundary": (
                "values are the field census's bounded sample of each field's "
                "distinct values; a match says those values are drawn from the "
                "table's key set, not that any consumer reads the field as a key"
            ),
        },
        "fields": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Join recorded MonoBehaviour string field values against the "
            "exported Table key sets, refusing numeric keys."
        )
    )
    parser.add_argument("--semantics-report", type=Path, default=DEFAULT_SEMANTICS_REPORT)
    parser.add_argument("--table-root", type=Path, default=DEFAULT_TABLE_ROOT)
    parser.add_argument(
        "--min-objects",
        type=int,
        default=0,
        help="skip classes smaller than this, to work the corpus down by size",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        report = build_report(
            args.semantics_report, args.table_root, min_objects=args.min_objects
        )
    except TableKeyError as exc:
        print(f"MonoBehaviour table-key join unavailable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        summary = report["summary"]
        print(
            f"checked {summary['stringFieldsConsidered']} string fields, "
            f"reported {summary['reportedFields']} table-key candidates "
            f"-> {args.report}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.monobehaviour_table_keys")
    raise SystemExit(main())
