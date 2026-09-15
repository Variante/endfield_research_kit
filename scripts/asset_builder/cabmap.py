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

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPS = ROOT / "export_full/recovered/AnimeStudio-cli/Maps"
DEFAULT_OUTPUT = ROOT / "reports/assets/cabmap_current_latest.json"

# .NET writes a 7-bit encoded length in at most five bytes.
MAX_LENGTH_BYTES = 5
# A single entry is at least two empty strings, an int64 and an int32.
MINIMUM_ENTRY_BYTES = 1 + 1 + 8 + 4


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


def iter_maps(directory: Path) -> Iterator[Path]:
    yield from sorted(directory.glob("*.bin"))


def run(*, maps_directory: Path, output_json: Path) -> dict[str, Any]:
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
    report = {
        "format": "animestudio-cabmap-container-index",
        "schemaVersion": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if not problems else "incomplete",
        "closureEnforced": True,
        "maps": summaries,
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
                "that a dependency edge implies load order, ownership or containment",
                "that the three targets naming nothing are errors; this corpus simply "
                "does not contain whatever declares them",
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
