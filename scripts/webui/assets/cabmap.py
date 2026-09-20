"""Read AnimeStudio's CABMap ``.bin`` container index.

The map is a .NET ``BinaryWriter`` stream, and the framing here is taken from the
writer that produces it -- ``AssetsHelper.DumpCABMap`` in the AnimeStudio
submodule -- rather than inferred from the bytes::

    string  BaseFolder
    int32   entryCount
    entryCount times:
        string  cabName
        string  path
        int64   offset
        int32   dependencyCount
        dependencyCount times: string cabName

Strings carry .NET's 7-bit encoded length prefix. Nothing here is a guess, which
is why the reader can insist on consuming every file exactly to EOF: a file that
ends early or late is not a weaker result, it means the writer is not the one
documented above and the caller should stop.

What this gives a caller is the container index: which CAB lives in which file, at
what offset, and which other CABs it depends on. It is not an asset inventory --
it says nothing about the objects inside a CAB, their types or their names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from scripts.repo_paths import REPO_ROOT
from scripts.common import EXPORT_LAYOUT

ROOT = REPO_ROOT
DEFAULT_MAPS = EXPORT_LAYOUT.cab_map_dir
DEFAULT_OUTPUT = ROOT / "reports/assets/cabmap_current_latest.json"

# .NET writes a 7-bit encoded length in at most five bytes.
MAX_LENGTH_BYTES = 5
# A single entry is at least two empty strings, an int64 and an int32.
MINIMUM_ENTRY_BYTES = 1 + 1 + 8 + 4
# A logical file holds one CAB; two is the most this corpus shows.
MAXIMUM_CABS_PER_LOGICAL_FILE = 2


class CabMapError(ValueError):
    """The bytes do not match the documented writer."""


@dataclass(frozen=True)
class CabEntry:
    cab: str
    path: str
    offset: int
    dependencies: tuple[str, ...]


def _read_7bit_length(data: bytes, cursor: int) -> tuple[int, int]:
    value = 0
    shift = 0
    for _ in range(MAX_LENGTH_BYTES):
        if cursor >= len(data):
            raise CabMapError(f"truncated 7-bit length at {cursor}")
        byte = data[cursor]
        cursor += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, cursor
        shift += 7
    raise CabMapError(f"unterminated 7-bit length at {cursor - MAX_LENGTH_BYTES}")


def _read_string(data: bytes, cursor: int) -> tuple[str, int]:
    length, cursor = _read_7bit_length(data, cursor)
    if length < 0 or length > len(data) - cursor:
        raise CabMapError(f"string of {length} bytes runs past the end at {cursor}")
    try:
        return data[cursor:cursor + length].decode("utf-8"), cursor + length
    except UnicodeDecodeError as exc:
        raise CabMapError(f"string at {cursor} is not UTF-8") from exc


def _read_int(data: bytes, cursor: int, fmt: str, width: int, what: str) -> tuple[int, int]:
    if cursor + width > len(data):
        raise CabMapError(f"truncated {what} at {cursor}")
    return struct.unpack_from(fmt, data, cursor)[0], cursor + width


def parse_cabmap(data: bytes) -> tuple[str, list[CabEntry]]:
    """Parse one CABMap, requiring the whole file to be consumed."""
    base_folder, cursor = _read_string(data, 0)
    count, cursor = _read_int(data, cursor, "<i", 4, "entry count")
    if count < 0:
        raise CabMapError(f"negative entry count: {count}")
    # A count larger than the bytes could hold is a corrupt header, not a big map.
    if count > (len(data) - cursor) // MINIMUM_ENTRY_BYTES + 1:
        raise CabMapError(f"entry count {count} cannot fit in {len(data) - cursor} bytes")
    entries: list[CabEntry] = []
    for index in range(count):
        cab, cursor = _read_string(data, cursor)
        path, cursor = _read_string(data, cursor)
        offset, cursor = _read_int(data, cursor, "<q", 8, f"offset of entry {index}")
        if offset < 0:
            raise CabMapError(f"negative offset in entry {index}: {offset}")
        dependency_count, cursor = _read_int(
            data, cursor, "<i", 4, f"dependency count of entry {index}"
        )
        if dependency_count < 0:
            raise CabMapError(f"negative dependency count in entry {index}")
        dependencies: list[str] = []
        for _ in range(dependency_count):
            dependency, cursor = _read_string(data, cursor)
            dependencies.append(dependency)
        entries.append(CabEntry(cab, path, offset, tuple(dependencies)))
    if cursor != len(data):
        raise CabMapError(
            f"trailing bytes: consumed {cursor} of {len(data)}"
        )
    return base_folder, entries


def summarise(path: Path, base_folder: str, entries: list[CabEntry]) -> dict[str, Any]:
    dependency_counts: Counter[int] = Counter(len(entry.dependencies) for entry in entries)
    known = {entry.cab for entry in entries}
    referenced = {dep for entry in entries for dep in entry.dependencies}
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        "bytes": path.stat().st_size,
        "baseFolder": base_folder,
        "entries": len(entries),
        "distinctCabNames": len(known),
        "distinctSourceFiles": len({entry.path for entry in entries}),
        "dependencyEdges": sum(len(entry.dependencies) for entry in entries),
        "dependenciesNamingAKnownCab": len(referenced & known),
        "dependenciesNamingNothingHere": len(referenced - known),
        "entriesWithNoDependency": dependency_counts.get(0, 0),
        "maximumDependencies": max(dependency_counts, default=0),
    }


def cabmap_is_closed(summary: dict[str, Any]) -> bool:
    """Every entry parsed, and CAB names unique within the file.

    Exact consumption is asserted while parsing, so what is left to check here is
    that the map is a map: a repeated CAB name would make lookups ambiguous, and
    an empty file claims nothing.
    """
    return (
        int(summary.get("entries") or 0) > 0
        and int(summary.get("entries") or 0) == int(summary.get("distinctCabNames") or 0)
    )


DEFAULT_LEDGER = ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"


def ledger_block_names(ledger_path: Path) -> set[str]:
    """Block directories the VFS understanding ledger enumerates.

    Resolve by block, never by chunk filename. The same block ships a *different*
    chunk file in each VFS root -- block ``0CE8FA57`` is ``4B06191A...chk`` under
    StreamingAssets and ``F047E09F...chk`` under Persistent -- and the ledger
    resolves each block from the primary root while a CABMap built against the
    fallback root names the fallback file. Comparing filenames reports a 222 MB
    chunk as unenumerated when every one of its 1,053 containers is covered.
    """
    import gzip  # noqa: PLC0415

    names: set[str] = set()
    if not ledger_path.is_file():
        return names
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            row = json.loads(line)
            if row.get("recordType") != "file":
                continue
            physical = row.get("physicalChunkPath")
            if physical:
                names.add(Path(physical).parent.name.upper())
    return names


def blocks_missing_from_ledger(
    entries_by_map: dict[str, list[CabEntry]], ledger: set[str]
) -> dict[str, dict[str, int]]:
    """Blocks a CABMap references that the ledger never enumerates.

    Both indexes are produced independently -- one by AnimeStudio walking
    containers, one by the VFS audit walking blocks -- so a block in the first and
    not the second is a real coverage gap. A *chunk* in the first and not the
    second is not: see ``ledger_block_names`` for why that comparison is wrong.
    """
    out: dict[str, dict[str, int]] = {}
    if not ledger:
        return out
    for name, entries in entries_by_map.items():
        counts: Counter[str] = Counter()
        for entry in entries:
            block = Path(entry.path).parent.name.upper()
            if block not in ledger:
                counts[block] += 1
        if counts:
            out[name] = dict(counts.most_common())
    return out


def ledger_spans_by_chunk(ledger_path: Path) -> dict[str, list[tuple[int, int, str]]]:
    """Logical-file spans per chunk file, sorted by offset.

    Keyed on the **chunk file**, deliberately. Coverage is keyed on the block --
    see ``ledger_block_names`` -- but an offset only means anything inside one
    chunk, and a block can hold forty of them. Sharing one key between the two
    questions merges unrelated offset spaces and invents matches.
    """
    import gzip  # noqa: PLC0415

    spans: dict[str, list[tuple[int, int, str]]] = {}
    if not ledger_path.is_file():
        return spans
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        handle.readline()
        for line in handle:
            row = json.loads(line)
            if row.get("recordType") != "file" or row.get("status") != "verified":
                continue
            physical = row.get("physicalChunkPath")
            offset, length = row.get("offset"), row.get("length")
            if not physical or offset is None or length is None:
                continue
            spans.setdefault(Path(physical).name.upper(), []).append(
                (int(offset), int(offset) + int(length), str(row.get("fileName")))
            )
    for values in spans.values():
        values.sort()
    return spans


def join_cabs_to_logical_files(
    entries_by_map: dict[str, list[CabEntry]],
    spans: dict[str, list[tuple[int, int, str]]],
) -> dict[str, Any]:
    """Name each CAB by the logical file its offset falls inside."""
    import bisect  # noqa: PLC0415

    outcomes: Counter[str] = Counter()
    per_file: Counter[str] = Counter()
    starts = {key: [start for start, _, _ in value] for key, value in spans.items()}
    for entries in entries_by_map.values():
        for entry in entries:
            key = Path(entry.path).name.upper()
            value = spans.get(key)
            if not value:
                # The block is enumerated from the other VFS root under a different
                # chunk file, so this chunk's offsets cannot be checked here.
                outcomes["chunkNotEnumeratedInThisRoot"] += 1
                continue
            index = bisect.bisect_right(starts[key], entry.offset) - 1
            if index >= 0 and entry.offset < value[index][1]:
                outcomes["namedByALogicalFile"] += 1
                per_file[value[index][2]] += 1
            else:
                outcomes["insideNoLogicalFile"] += 1
    shape = Counter(per_file.values())
    return {
        "outcomes": dict(outcomes.most_common()),
        "distinctLogicalFiles": len(per_file),
        "logicalFilesHoldingOneCab": shape.get(1, 0),
        "maximumCabsInOneLogicalFile": max(shape, default=0),
    }


def cab_coverage_across_maps(
    entries_by_map: dict[str, list[CabEntry]],
    spans: dict[str, list[tuple[int, int, str]]],
) -> dict[str, Any]:
    """Whether each CAB *name* is covered somewhere, not just at each location.

    A CAB can appear in both maps, once per VFS root. One occurrence may sit in a
    gap the ledger does not enumerate while the other sits inside an enumerated
    span, because the ledger enumerates each block from one root only. Judging an
    occurrence in isolation reports hundreds of uncovered containers; judging the
    name reports the truth.
    """
    import bisect  # noqa: PLC0415

    starts = {key: [start for start, _, _ in value] for key, value in spans.items()}

    def inside(entry: CabEntry) -> bool | None:
        value = spans.get(Path(entry.path).name.upper())
        if not value:
            return None
        index = bisect.bisect_right(starts[Path(entry.path).name.upper()], entry.offset) - 1
        return index >= 0 and entry.offset < value[index][1]

    covered: set[str] = set()
    occurrences: list[CabEntry] = []
    for entries in entries_by_map.values():
        for entry in entries:
            state = inside(entry)
            if state:
                covered.add(entry.cab)
            elif state is False:
                occurrences.append(entry)
    uncovered = {entry.cab for entry in occurrences if entry.cab not in covered}
    return {
        "occurrencesInNoSpan": len(occurrences),
        "occurrencesCoveredElsewhere": sum(1 for e in occurrences if e.cab in covered),
        "cabNamesCoveredNowhere": len(uncovered),
        "uncoveredCabNames": sorted(uncovered)[:8],
    }


def cab_join_is_essentially_one_to_one(join: dict[str, Any]) -> bool:
    """Each logical file holds one CAB, give or take a countable few.

    Stated as a gate rather than an observation because the 1:1 shape is what a
    caller would rely on, and because a wrong join key produced a "42 CABs in one
    bundle" result that looked like structure and was an artifact.
    """
    named = int((join.get("outcomes") or {}).get("namedByALogicalFile") or 0)
    files = int(join.get("distinctLogicalFiles") or 0)
    single = int(join.get("logicalFilesHoldingOneCab") or 0)
    # Two bounds, because either alone passes a case it should not. Allowing one
    # non-single file is meaningless on a corpus of one file, so the per-file
    # maximum is bounded as well: a bundle holding many CABs is the artifact shape
    # a wrong join key produces.
    return (
        named > 0
        and files > 0
        and single >= files - 1
        and int(join.get("maximumCabsInOneLogicalFile") or 0) <= MAXIMUM_CABS_PER_LOGICAL_FILE
    )


def dependency_graph_shape(entries_by_map: dict[str, list[CabEntry]]) -> dict[str, Any]:
    """Shape of the CAB dependency relation: acyclicity, roots, leaves, duplicates.

    Acyclicity is the load-bearing part. A cycle would leave load order undefined,
    so it is measured rather than assumed, with an iterative walk because the graph
    is deep enough to blow a recursive one.
    """
    edges: dict[str, set[str]] = {}
    raw_edges = 0
    for entries in entries_by_map.values():
        for entry in entries:
            raw_edges += len(entry.dependencies)
            edges.setdefault(entry.cab, set()).update(entry.dependencies)
    nodes = set(edges) | {dep for targets in edges.values() for dep in targets}
    distinct_edges = sum(len(targets) for targets in edges.values())
    in_degree: Counter[str] = Counter()
    for targets in edges.values():
        for target in targets:
            in_degree[target] += 1
    colour: dict[str, int] = {}
    back_edges = 0
    for start in edges:
        if colour.get(start):
            continue
        colour[start] = 1
        stack = [(start, iter(edges.get(start, ())))]
        while stack:
            node, walker = stack[-1]
            nxt = next(walker, None)
            if nxt is None:
                colour[node] = 2
                stack.pop()
                continue
            state = colour.get(nxt, 0)
            if state == 1:
                back_edges += 1
            elif state == 0:
                colour[nxt] = 1
                stack.append((nxt, iter(edges.get(nxt, ()))))
    return {
        "nodes": len(nodes),
        "rawDependencyEntries": raw_edges,
        "distinctEdges": distinct_edges,
        "duplicateDependencyEntries": raw_edges - distinct_edges,
        "nodesNothingDependsOn": sum(1 for node in nodes if not in_degree.get(node)),
        "nodesWithNoDependency": sum(1 for node in nodes if not edges.get(node)),
        "backEdges": back_edges,
        "acyclic": back_edges == 0,
    }


def dependency_graph_is_acyclic(shape: dict[str, Any]) -> bool:
    """A cycle would make load order undefined, so it must be observed absent."""
    return bool(shape.get("acyclic")) and int(shape.get("distinctEdges") or 0) > 0


def iter_maps(directory: Path) -> Iterator[Path]:
    yield from sorted(directory.glob("*.bin"))


def run(
    *,
    maps_directory: Path,
    output_json: Path,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    files = list(iter_maps(maps_directory))
    if not files:
        raise CabMapError(f"no CABMap files under {maps_directory}")
    summaries = []
    problems: list[str] = []
    parsed: dict[str, list[CabEntry]] = {}
    for path in files:
        base_folder, entries = parse_cabmap(path.read_bytes())
        parsed[path.name] = entries
        summary = summarise(path, base_folder, entries)
        if not cabmap_is_closed(summary):
            problems.append(
                f"{path.name}: {summary['entries']} entries but "
                f"{summary['distinctCabNames']} distinct CAB names"
            )
        summaries.append(summary)
    # A dependency naming nothing in its own map is not necessarily dangling: the
    # persistent map leans on the streaming one. Resolve across every map before
    # calling an edge unresolved.
    everything = {entry.cab for entries in parsed.values() for entry in entries}
    cross: dict[str, Any] = {}
    unresolved_total = 0
    edge_total = 0
    for name, entries in parsed.items():
        own = {entry.cab for entry in entries}
        refs = {dep for entry in entries for dep in entry.dependencies}
        edges = sum(len(entry.dependencies) for entry in entries)
        edge_total += edges
        unresolved = refs - everything
        unresolved_total += len(unresolved)
        cross[name] = {
            "dependencyEdges": edges,
            "distinctTargets": len(refs),
            "namingItsOwnMap": len(refs & own),
            "namingAnotherMap": len((refs - own) & everything),
            "namingNothingAnywhere": len(unresolved),
        }
    ledger = ledger_block_names(ledger_path)
    join = join_cabs_to_logical_files(parsed, ledger_spans_by_chunk(ledger_path))
    coverage = cab_coverage_across_maps(parsed, ledger_spans_by_chunk(ledger_path))
    graph = dependency_graph_shape(parsed)
    if not dependency_graph_is_acyclic(graph):
        problems.append(
            f"the CAB dependency graph is not acyclic: {graph['backEdges']} back edges"
        )
    if join["distinctLogicalFiles"] and not cab_join_is_essentially_one_to_one(join):
        problems.append(
            "the CAB-to-logical-file join is not one to one: "
            f"{join['logicalFilesHoldingOneCab']} of {join['distinctLogicalFiles']} "
            f"files hold a single CAB, maximum {join['maximumCabsInOneLogicalFile']}"
        )
    missing_blocks = blocks_missing_from_ledger(parsed, ledger)
    report = {
        "format": "animestudio-cabmap-container-index",
        "schemaVersion": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if not problems else "incomplete",
        "closureEnforced": True,
        "maps": summaries,
        "ledgerCoverage": {
            "ledgerPath": str(ledger_path),
            "ledgerEnumeratesBlocks": len(ledger),
            "blocksReferencedButNotEnumerated": missing_blocks,
        },
        "logicalFileJoin": join,
        "dependencyGraphShape": graph,
        "cabCoverage": coverage,
        "dependencyResolution": {
            "distinctCabNames": len(everything),
            "dependencyEdges": edge_total,
            "targetsNamingNothingAnywhere": unresolved_total,
            "byMap": cross,
        },
        "problems": problems,
        "evidenceBoundary": {
            "layer": 2,
            "claim": (
                "each CABMap is consumed exactly to EOF under the framing its own "
                "writer uses, and names each CAB once"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "what objects a CAB contains, or their types, names or path ids",
                "that a dependency edge implies load order, ownership or containment; "
                "the graph being acyclic makes a load order possible, not actual",
                "that the three targets naming nothing are errors; this corpus simply "
                "does not contain whatever declares them",
                "that a chunk filename absent from the ledger means missing coverage; "
                "each block ships a different chunk file per VFS root, so coverage is "
                "resolved by block",
                "that an offset points at a readable object without the container "
                "format that sits at it",
            ],
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if problems:
        raise CabMapError("; ".join(problems))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", type=Path, default=DEFAULT_MAPS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = run(maps_directory=args.maps, output_json=args.output_json)
    except (OSError, CabMapError) as exc:
        print(f"CABMap audit failed: {exc}", file=sys.stderr)
        return 1
    total = sum(row["entries"] for row in report["maps"])
    byte_total = sum(row["bytes"] for row in report["maps"])
    print(
        f"CABMap: {len(report['maps'])} maps, {total:,} entries, "
        f"{byte_total:,} bytes, all consumed exactly"
    )
    print(f"CABMap report: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
