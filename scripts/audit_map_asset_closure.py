#!/usr/bin/env python3
"""Audit a map's candidate AssetMap closure without loading the full map."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json"


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_asset_entries(path: Path, chunk_size: int = 1 << 20):
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as stream:
        buffer = ""
        while '"AssetEntries"' not in buffer:
            chunk = stream.read(chunk_size)
            if not chunk:
                raise ValueError(f"AssetEntries array not found in {path}")
            buffer += chunk
        buffer = buffer.split('"AssetEntries"', 1)[1]
        while "[" not in buffer:
            buffer += stream.read(chunk_size)
        buffer = buffer.split("[", 1)[1]
        cursor = 0
        while True:
            while cursor < len(buffer) and buffer[cursor] in " \t\r\n,":
                cursor += 1
            if cursor < len(buffer) and buffer[cursor] == "]":
                return
            try:
                value, cursor = decoder.raw_decode(buffer, cursor)
            except json.JSONDecodeError:
                chunk = stream.read(chunk_size)
                if not chunk:
                    raise
                buffer = buffer[cursor:] + chunk
                cursor = 0
                continue
            if not isinstance(value, dict):
                raise ValueError("AssetEntries contains a non-object value")
            yield value
            if cursor >= chunk_size:
                buffer = buffer[cursor:]
                cursor = 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--needle", default="indie/dg002")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    needle = args.needle.casefold()
    matches = []
    source_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for entry in iter_asset_entries(args.asset_map):
        searchable = "\n".join(str(entry.get(key, "")) for key in ("Name", "Container"))
        if needle not in searchable.casefold():
            continue
        row = {key: entry.get(key) for key in ("Source", "Offset", "Name", "PathID", "Type", "Container", "Hash")}
        matches.append(row)
        source_counts[str(row["Source"])] += 1
        type_counts[str(row["Type"])] += 1

    payload = {
        "schemaVersion": 1,
        "assetMap": str(args.asset_map),
        "assetMapSha256": sha256_file(args.asset_map),
        "needle": args.needle,
        "matchCount": len(matches),
        "typeCounts": dict(sorted(type_counts.items())),
        "physicalSourceCounts": dict(sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))),
        "entries": matches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("matchCount", "typeCounts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
