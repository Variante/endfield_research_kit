#!/usr/bin/env python3
"""Stream-filter AnimeStudio Endfield AssetMap JSON into reusable filter files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSET_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "maps"
    / "endfield_streamingassets_assets.json"
)


def _compile_many(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def _matches_any(value: str, patterns: list[re.Pattern[str]]) -> bool:
    return not patterns or any(pattern.search(value) for pattern in patterns)


def iter_asset_entries(path: Path):
    inside_entries = False
    buffer: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not inside_entries:
                if stripped == '"AssetEntries": [':
                    inside_entries = True
                continue

            if stripped == "]":
                break

            if not buffer:
                if stripped.startswith("{"):
                    buffer.append(line)
                continue

            buffer.append(line)
            if stripped.startswith("}") or stripped.startswith("},"):
                text = "".join(buffer).rstrip().rstrip(",")
                buffer = []
                yield json.loads(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--term", action="append", default=[], help="Regex matched against Name and Container")
    parser.add_argument("--name", action="append", default=[], help="Regex matched against Name")
    parser.add_argument("--container", action="append", default=[], help="Regex matched against Container")
    parser.add_argument("--source", action="append", default=[], help="Regex matched against source filename")
    parser.add_argument("--type", action="append", default=[], help="Exact Unity type to keep")
    parser.add_argument("--limit", type=int, default=0, help="Stop after this many matches")
    parser.add_argument("--summary", action="store_true", help="Print match counts by type and source")
    parser.add_argument("--output", type=Path, help="Write matching entries as JSON filter data")
    args = parser.parse_args(argv)

    term_patterns = _compile_many(args.term)
    name_patterns = _compile_many(args.name)
    container_patterns = _compile_many(args.container)
    source_patterns = _compile_many(args.source)
    wanted_types = set(args.type)

    matches = []
    type_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for entry in iter_asset_entries(args.asset_map):
        name = str(entry.get("Name") or "")
        container = str(entry.get("Container") or "")
        source = Path(str(entry.get("Source") or "")).name
        entry_type = str(entry.get("Type") or "")
        haystack = f"{name}\n{container}"

        if wanted_types and entry_type not in wanted_types:
            continue
        if not _matches_any(haystack, term_patterns):
            continue
        if not _matches_any(name, name_patterns):
            continue
        if not _matches_any(container, container_patterns):
            continue
        if not _matches_any(source, source_patterns):
            continue

        matches.append(entry)
        type_counts[entry_type] += 1
        source_counts[source] += 1
        if args.limit and len(matches) >= args.limit:
            break

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            json.dump(matches, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    if args.summary:
        print(f"matches: {len(matches)}")
        print("types:")
        for key, count in type_counts.most_common():
            print(f"  {key}: {count}")
        print("sources:")
        for key, count in source_counts.most_common():
            print(f"  {key}: {count}")

    if not args.output:
        json.dump(matches, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
