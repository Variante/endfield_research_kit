"""Frame the header of Endfield ``Data/Terrain/PC/<scene>/Terrain_a_b_c_X.bytes``.

A terrain file is **not** a header followed by pixels. Its leading ``u32`` equals
``payloadBytes + 20``, which is the size of the *decompressed* record -- twenty
header bytes plus every mip level -- while the file itself is one to two hundred
times smaller. The magic ``TRET`` then sits at offset 6 in most files but at 7, 8,
9, 10, 11, 17, 31 and further in 1,322 others. Both facts say the same thing: the
file is a compressed stream, and the header is legible only because the compressor
emitted it as literals. Where it emitted part of it as a match instead, the header
is not contiguous in the file and cannot be read at all.

So the header is located by its magic, never by a fixed offset::

    u32  declaredTotal      == payloadBytes + 20   (decompressed record size)
    ---- "TRET"
    u32  one
    u16  width
    u16  height
    u16  mipLevels
    u16  formatCode
    u32  payloadBytes

``payloadBytes`` is the **whole mip chain**, not one image: for the 1024x1024
layer textures ``mipLevels`` is 11 and the payload is 4/3 of the base level. That
is what this module gates -- the payload must equal the chain computed from
``width``, ``height``, ``mipLevels`` and the layout the format code implies, under
exactly one of two layouts (a linear bytes-per-pixel, or 4x4 blocks of a fixed
size). Codes 100 and 101 are reported **ambiguous** rather than resolved: they are
only ever seen at 132x132, and 132 is a multiple of 4, so one byte per pixel and
sixteen-byte blocks predict the same total there.

The compressed stream is read by :mod:`scripts.webui.assets.terrain_stream`: it is
an LZ4 block whose match offset is big-endian, which is why every stock codec --
lz4 block, zlib, raw deflate, lzma, bzip2 and brotli, from offsets 4, 5 and 6 --
refused every file. Streams using a single sequence decode to the byte; the rest
are fenced there and nothing in this module depends on them.

Two name shapes ship here: ``Terrain_a_b_c_X.bytes`` tiles, whose channel is the
last token, and ``LAYER_X_n.bytes`` textures, whose last token is a layer index and
whose channel sits in the middle. The layer textures are the only files carrying a
mip chain, and so the only ones whose payload size can tell a block layout from a
linear one.
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

from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT
DEFAULT_OUTPUT = ROOT / "reports/assets/terrain_header_current_latest.json"

MAGIC = b"TRET"
# "TRET", a word, two dimensions, two 16-bit fields and the payload size.
HEADER_BYTES = 20
# declaredTotal counts those header bytes plus the payload.
TOTAL_OVERHEAD = HEADER_BYTES
# The leading size word must precede the magic, so the magic cannot start before 4.
MINIMUM_MAGIC_OFFSET = 4
# A bound on the mip count so a stray "TRET" inside compressed bytes cannot be read
# as a header: 16 levels already covers a 32768-pixel texture.
MAXIMUM_MIP_LEVELS = 16
# Two name shapes ship in this block. The per-tile files carry their channel last;
# the 1024x1024 layer textures carry it in the middle and a layer index last, so
# taking the trailing token would read the index as a channel.
TERRAIN_TILE_NAME_RE = re.compile(r"Terrain_\d+_\d+_\d+_([A-Za-z0-9]+)\.bytes$")
TERRAIN_LAYER_NAME_RE = re.compile(r"LAYER_([A-Za-z]+)_\d+\.bytes$")
# Candidate layouts the payload size is tested against. Nothing here is named after
# a graphics format: these are the only two ways the observed totals can arise.
LINEAR_BYTES_PER_PIXEL = (1, 2, 4, 8, 16)
BLOCK_BYTES = (8, 16)
BLOCK_SIDE = 4


class TerrainHeaderError(ValueError):
    """The bytes do not match the framed header."""


@dataclass(frozen=True)
class TerrainHeader:
    magic_offset: int
    width: int
    height: int
    mip_levels: int
    format_code: int
    declared_total: int
    payload_bytes: int


def linear_chain(width: int, height: int, mip_levels: int, bytes_per_pixel: int) -> int:
    """Total bytes of a mip chain stored as plain pixels."""
    total = 0
    for level in range(mip_levels):
        total += max(1, width >> level) * max(1, height >> level) * bytes_per_pixel
    return total


def block_chain(width: int, height: int, mip_levels: int, block_bytes: int) -> int:
    """Total bytes of a mip chain stored as 4x4 blocks.

    The last levels matter: a 2x2 or 1x1 level still costs a whole block, so a
    block chain is slightly larger than four thirds of its base. That difference is
    what separates a block layout from a linear one at 1024x1024.
    """
    total = 0
    for level in range(mip_levels):
        wide = max(1, width >> level)
        high = max(1, height >> level)
        total += ((wide + BLOCK_SIDE - 1) // BLOCK_SIDE) * ((high + BLOCK_SIDE - 1) // BLOCK_SIDE) * block_bytes
    return total


def fit_payload(header: TerrainHeader) -> tuple[str, int | None, int | None]:
    """Which layout accounts for ``payloadBytes`` exactly.

    Returns one of ``linear``, ``block``, ``ambiguous`` or ``neither`` together
    with the widths that fit. ``ambiguous`` is a real outcome, not a failure: at a
    dimension that is a multiple of four, one byte per pixel and sixteen-byte
    blocks predict the same total, and nothing in these bytes separates them.
    """
    linear = next(
        (b for b in LINEAR_BYTES_PER_PIXEL
         if linear_chain(header.width, header.height, header.mip_levels, b) == header.payload_bytes),
        None,
    )
    block = next(
        (b for b in BLOCK_BYTES
         if block_chain(header.width, header.height, header.mip_levels, b) == header.payload_bytes),
        None,
    )
    if linear is not None and block is not None:
        return "ambiguous", linear, block
    if linear is not None:
        return "linear", linear, None
    if block is not None:
        return "block", None, block
    return "neither", None, None


def parse_terrain_header(data: bytes) -> TerrainHeader:
    """Locate the header by its magic and read it, or refuse.

    Every occurrence of the magic is tried, because a compressed stream can carry
    the four bytes by chance before the real header appears. An occurrence is
    accepted only if the two size words agree -- ``declaredTotal`` against
    ``payloadBytes`` -- which is two independent statements about the same record.
    """
    if len(data) < MINIMUM_MAGIC_OFFSET + HEADER_BYTES:
        raise TerrainHeaderError(f"shorter than a header: {len(data)} bytes")
    declared_total = struct.unpack_from("<I", data, 0)[0]
    at = data.find(MAGIC)
    while at != -1:
        if at >= MINIMUM_MAGIC_OFFSET and at + HEADER_BYTES <= len(data):
            one = struct.unpack_from("<I", data, at + 4)[0]
            width, height = struct.unpack_from("<HH", data, at + 8)
            mip_levels, format_code = struct.unpack_from("<HH", data, at + 12)
            payload_bytes = struct.unpack_from("<I", data, at + 16)[0]
            if (
                one == 1
                and width > 0
                and height > 0
                and 0 < mip_levels <= MAXIMUM_MIP_LEVELS
                and declared_total == payload_bytes + TOTAL_OVERHEAD
            ):
                return TerrainHeader(
                    at, width, height, mip_levels, format_code, declared_total, payload_bytes
                )
        at = data.find(MAGIC, at + 1)
    raise TerrainHeaderError(
        "no occurrence of TRET is followed by a header whose sizes agree"
    )


def channel_of(file_name: str) -> str | None:
    """The channel token, from whichever of the two name shapes applies."""
    match = TERRAIN_TILE_NAME_RE.search(file_name)
    if match:
        return match.group(1)
    match = TERRAIN_LAYER_NAME_RE.search(file_name)
    return f"LAYER_{match.group(1)}" if match else None


def summarise(samples: list[tuple[str, bytes]]) -> dict[str, Any]:
    """Census over (fileName, bytes) pairs."""
    outcomes: Counter[str] = Counter()
    magic_offsets: Counter[int] = Counter()
    fits: dict[str, Counter] = defaultdict(Counter)
    widths: dict[str, Counter] = defaultdict(Counter)
    formats_by_channel: dict[str, Counter] = defaultdict(Counter)
    dimensions: dict[str, Counter] = defaultdict(Counter)
    disagreements: list[str] = []
    for name, data in samples:
        channel = channel_of(name)
        if channel is None:
            outcomes["nameNotTerrainShaped"] += 1
            continue
        try:
            header = parse_terrain_header(data)
        except TerrainHeaderError:
            # The header is not contiguous in the file. That is a property of the
            # compressed stream, not a malformed file, so it is fenced by name.
            outcomes["headerNotLegibleInTheStream"] += 1
            continue
        outcomes["headerFramed"] += 1
        magic_offsets[header.magic_offset] += 1
        code = str(header.format_code)
        verdict, linear, block = fit_payload(header)
        outcomes[f"payload_{verdict}"] += 1
        fits[code][verdict] += 1
        dimensions[code][f"{header.width}x{header.height}"] += 1
        formats_by_channel[channel][f"mips{header.mip_levels}_format{header.format_code}"] += 1
        if verdict == "neither":
            if len(disagreements) < 8:
                disagreements.append(
                    f"{name}: {header.width}x{header.height} mips {header.mip_levels} "
                    f"format {header.format_code} payload {header.payload_bytes} fits no layout"
                )
            continue
        widths[code][f"linear_{linear}" if linear is not None else "linear_none"] += 1
        widths[code][f"block_{block}" if block is not None else "block_none"] += 1
    return {
        "outcomes": dict(outcomes.most_common()),
        "magicOffsets": {str(key): value for key, value in sorted(magic_offsets.items())},
        "payloadFitByFormat": {
            code: dict(sorted(values.items())) for code, values in sorted(fits.items(), key=lambda x: int(x[0]))
        },
        "layoutByFormat": {
            code: dict(sorted(values.items())) for code, values in sorted(widths.items(), key=lambda x: int(x[0]))
        },
        "dimensionsByFormat": {
            code: dict(sorted(values.items())) for code, values in sorted(dimensions.items(), key=lambda x: int(x[0]))
        },
        "formatByChannel": {
            channel: dict(sorted(values.items())) for channel, values in sorted(formats_by_channel.items())
        },
        "disagreements": disagreements,
    }


def payload_is_the_mip_chain(summary: dict[str, Any]) -> bool:
    """Every framed payload must be the mip chain its header describes.

    This is the whole claim, and it is an equality over four header fields at once:
    width, height, mip level count and format code together predict an exact byte
    total. A file that fits neither layout breaks it, and a rate would hide that
    file. A corpus where nothing framed satisfies it vacuously, so framing is
    required as well.

    ``ambiguous`` counts as accounted for -- the total *is* predicted, just by two
    layouts that these dimensions cannot separate -- and is reported so the
    ambiguity is not mistaken for a resolution.
    """
    outcomes = summary.get("outcomes") or {}
    framed = int(outcomes.get("headerFramed") or 0)
    if framed <= 0:
        return False
    if int(outcomes.get("payload_neither") or 0):
        return False
    accounted = sum(
        int(outcomes.get(f"payload_{verdict}") or 0)
        for verdict in ("linear", "block", "ambiguous")
    )
    return accounted == framed


def channel_decides_the_format(summary: dict[str, Any]) -> bool:
    """The channel in the file name must pick exactly one (mips, format) pair.

    Two pairs under one channel would mean the name does not determine the format,
    which is the join this report exists to state. Digit channels are pooled by the
    caller only for reporting; here each channel string stands on its own.
    """
    by_channel = summary.get("formatByChannel") or {}
    if not by_channel:
        return False
    return all(len(values) == 1 for values in by_channel.values())


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
    closed = payload_is_the_mip_chain(summary) and channel_decides_the_format(summary)
    report = {
        "format": "endfield-terrain-header-audit",
        "schemaVersion": 2,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete" if closed else "incomplete",
        "closureEnforced": True,
        "files": len(samples),
        "summary": summary,
        "evidenceBoundary": {
            "layer": 3,
            "claim": (
                "a terrain file is a compressed stream of a 20-byte TRET record plus "
                "its payload; where the header survives as literals it can be located "
                "by its magic, and its payload size is exactly the mip chain implied "
                "by width, height, mip level count and format code"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "anything about the compressed stream's contents; it is decoded by "
                "scripts.webui.assets.terrain_stream, where only single-sequence "
                "streams close and the rest are fenced",
                "which graphics format a format code names; only the byte layout its "
                "payload size implies is established, and for codes 100 and 101 even "
                "that is ambiguous because they appear only at 132x132",
                "what a channel letter means, or what its pixels represent",
                "that width and height are world extents rather than sample counts",
                "any reading of the files whose header is not contiguous in the "
                "stream; those are fenced, not framed",
            ],
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    framed = summary["outcomes"].get("headerFramed", 0)
    print(
        f"Terrain headers: {framed:,} framed of {len(samples):,} files; "
        f"payload is the mip chain: {payload_is_the_mip_chain(summary)}; "
        f"channel decides the format: {channel_decides_the_format(summary)}"
    )
    print(f"Terrain header report: {args.output_json}")
    return 0 if closed else 1


if __name__ == "__main__":
    raise SystemExit(main())
