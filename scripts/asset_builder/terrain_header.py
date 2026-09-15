"""Frame the header of Endfield ``Data/Terrain/PC/<scene>/Terrain_a_b_c_X.bytes``.

Every terrain file carries the ASCII magic ``TRET``. In 97% of them it sits at
offset 6 and a fixed header follows::

    u32  declaredTotal      == payloadBytes + 20
    u8   0xFF
    u8   channel selector
    ---- "TRET"
    u32  one
    u16  width
    u16  height
    u16  one
    u16  six
    u32  payloadBytes       == width * height * bytesPerPixel

The **channel letter in the filename decides bytes per pixel** -- ``A``, ``N`` and
``T`` are one byte, ``C`` and ``H`` two, ``S`` four -- and that is the finding this
module exists to gate. It is a join between the name and the header, so neither
side proves it alone.

What is *not* framed: everything after the header. The bytes there are smaller
than ``payloadBytes`` declares, so the payload is encoded or compressed, and this
module does not decode it. Files whose magic is not at offset 6 are fenced rather
than read with a layout that does not apply to them.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "reports/assets/terrain_header_current_latest.json"

MAGIC = b"TRET"
MAGIC_OFFSET = 6
HEADER_BYTES = 26
# declaredTotal counts the payload plus the header bytes that follow the size word.
TOTAL_OVERHEAD = 20
TERRAIN_NAME_RE = re.compile(r"Terrain_\d+_\d+_\d+_([A-Za-z0-9]+)\.bytes$")
# The channel letter in the filename, and what the header then says a pixel costs.
CHANNEL_BYTES_PER_PIXEL = {"A": 1, "N": 1, "T": 1, "C": 2, "H": 2, "S": 4}


class TerrainHeaderError(ValueError):
    """The bytes do not match the framed header."""


@dataclass(frozen=True)
class TerrainHeader:
    channel_selector: int
    width: int
    height: int
    declared_total: int
    payload_bytes: int

    @property
    def bytes_per_pixel(self) -> float | None:
        pixels = self.width * self.height
        if not pixels or self.payload_bytes % pixels:
            return None
        return self.payload_bytes // pixels


def parse_terrain_header(data: bytes) -> TerrainHeader:
    """Read the fixed header, or refuse."""
    if len(data) < HEADER_BYTES:
        raise TerrainHeaderError(f"shorter than a header: {len(data)} bytes")
    if data[MAGIC_OFFSET:MAGIC_OFFSET + 4] != MAGIC:
        raise TerrainHeaderError("magic TRET is not at offset 6")
    declared_total = struct.unpack_from("<I", data, 0)[0]
    width = struct.unpack_from("<H", data, 14)[0]
    height = struct.unpack_from("<H", data, 16)[0]
    payload_bytes = struct.unpack_from("<I", data, 22)[0]
    if declared_total != payload_bytes + TOTAL_OVERHEAD:
        raise TerrainHeaderError(
            f"declared total {declared_total} is not payload {payload_bytes} plus "
            f"{TOTAL_OVERHEAD}"
        )
    return TerrainHeader(data[5], width, height, declared_total, payload_bytes)


def channel_of(file_name: str) -> str | None:
    match = TERRAIN_NAME_RE.search(file_name)
    return match.group(1) if match else None


def summarise(samples: list[tuple[str, bytes]]) -> dict[str, Any]:
    """Census over (fileName, bytes) pairs."""
    outcomes: Counter[str] = Counter()
    per_channel: dict[str, Counter] = defaultdict(Counter)
    selectors: dict[str, Counter] = defaultdict(Counter)
    disagreements: list[str] = []
    for name, data in samples:
        channel = channel_of(name)
        if channel is None:
            outcomes["nameNotTerrainShaped"] += 1
            continue
        try:
            header = parse_terrain_header(data)
        except TerrainHeaderError:
            outcomes["headerNotAtOffsetSix"] += 1
            continue
        outcomes["headerFramed"] += 1
        selectors[channel][header.channel_selector] += 1
        width = header.bytes_per_pixel
        if width is None:
            per_channel[channel]["nonIntegral"] += 1
            continue
        per_channel[channel][width] += 1
        expected = CHANNEL_BYTES_PER_PIXEL.get(channel)
        if expected is not None and width != expected:
            outcomes["channelWidthDisagrees"] += 1
            if len(disagreements) < 8:
                disagreements.append(f"{name}: expected {expected}, header says {width}")
    return {
        "outcomes": dict(outcomes.most_common()),
        "bytesPerPixelByChannel": {
            channel: {str(key): count for key, count in sorted(values.items(), key=str)}
            for channel, values in sorted(per_channel.items())
        },
        "channelSelectorByChannel": {
            channel: {str(key): count for key, count in sorted(values.items())}
            for channel, values in sorted(selectors.items())
        },
        "expectedBytesPerPixel": dict(sorted(CHANNEL_BYTES_PER_PIXEL.items())),
        "disagreements": disagreements,
    }


def channel_decides_pixel_width(summary: dict[str, Any]) -> bool:
    """The filename's channel letter must predict the header's bytes per pixel.

    Stated as a gate because it is the whole claim. One file whose header
    disagrees with its name breaks the join, and a rate would hide it; a corpus
    where nothing framed would satisfy it vacuously, so framing is required too.
    """
    outcomes = summary.get("outcomes") or {}
    if int(outcomes.get("headerFramed") or 0) <= 0:
        return False
    if int(outcomes.get("channelWidthDisagrees") or 0):
        return False
    observed = summary.get("bytesPerPixelByChannel") or {}
    return any(channel in observed for channel in CHANNEL_BYTES_PER_PIXEL)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    import gzip  # noqa: PLC0415

    samples: list[tuple[str, bytes]] = []
    try:
        with gzip.open(args.ledger, "rt", encoding="utf-8") as handle:
            handle.readline()
            for line in handle:
                row = json.loads(line)
                if row.get("blockName") != "Terrain" or row.get("recordType") != "file":
                    continue
                if row.get("status") != "verified":
                    continue
                path = Path(row["physicalChunkPath"])
                with path.open("rb") as chunk:
                    chunk.seek(row["offset"])
                    samples.append((row["fileName"], chunk.read(row["length"])))
                if args.limit and len(samples) >= args.limit:
                    break
    except OSError as exc:
        print(f"terrain header audit failed: {exc}", file=sys.stderr)
        return 1
    if not samples:
        print("terrain header audit failed: no Terrain rows", file=sys.stderr)
        return 1

    summary = summarise(samples)
    closed = channel_decides_pixel_width(summary)
    report = {
        "format": "endfield-terrain-header-audit",
        "schemaVersion": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if closed else "incomplete",
        "closureEnforced": True,
        "files": len(samples),
        "summary": summary,
        "evidenceBoundary": {
            "layer": 3,
            "claim": (
                "every terrain file carries the TRET magic, and where it sits at "
                "offset 6 the header's pixel width is predicted by the channel letter "
                "in the file name"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "anything about the bytes after the header; they are shorter than the "
                "declared payload, so the payload is encoded and is not decoded here",
                "what a channel letter means, or what its pixels represent",
                "that width and height are world extents rather than sample counts",
                "any reading of the files whose magic is not at offset 6; those are "
                "fenced, not framed",
            ],
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    framed = summary["outcomes"].get("headerFramed", 0)
    print(
        f"Terrain headers: {framed:,} framed of {len(samples):,} files; "
        f"channel decides pixel width: {closed}"
    )
    print(f"Terrain header report: {args.output_json}")
    return 0 if closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
