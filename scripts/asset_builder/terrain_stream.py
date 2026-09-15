"""Decode the compressed stream inside an Endfield terrain ``.bytes`` file.

The container is settled elsewhere (:mod:`scripts.asset_builder.terrain_header`):
a leading ``u32`` giving the decompressed record size, then a compressed stream
whose first literal run is the 20-byte ``TRET`` record itself.

That stream is **LZ4-shaped with one deviation: the match offset is big-endian.**
Everything else is ordinary LZ4 block format -- a token whose high nibble is the
literal length and low nibble the match length, ``0xFF`` extension bytes that are
summed and include their terminator, a match base of four, and a closing run of
literals. The offset endianness was not guessed: the grid of conventions
(endianness x which nibble is the literal length x whether the extension byte is
included x match base x tail rule) was searched exhaustively, and only the
big-endian reading produces files that close at all.

"Close" is the whole standard here, and it is deliberately severe: the output must
be *exactly* the size the file declares **and** the input must be *exactly*
consumed. A decoder that stops early, or that leaves bytes over, has not decoded
anything.

What is **not** established: streams that use more than one sequence. They stop at
the second match, whose offset field is only sensible read little-endian -- the
opposite of the first. Both cannot be true, so one of the two sequence boundaries
is misplaced and the layout after the first match is unresolved. Those files are
fenced by reason, never partially decoded into a result. A preset dictionary was
tested as an explanation and eliminated: priming the window with 64 KB does not
raise the closure count by a single file.
"""

from __future__ import annotations

import argparse
import gzip
import json
import struct
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "reports/assets/terrain_stream_current_latest.json"
DEFAULT_LEDGER = ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"

# The stream begins after the leading decompressed-size word.
STREAM_START = 4
# LZ4 requires the block to end with literals; these streams end with one token
# byte and exactly five, which is the minimum a well-formed LZ4 block may carry.
TAIL_LITERALS = 5
MATCH_BASE = 4
EXTENSION_ESCAPE = 0xFF
# The record whose header the first literal run must reproduce.
RECORD_BYTES = 20
MAGIC = b"TRET"


class TerrainStreamError(ValueError):
    """The stream does not close: wrong output size, or input left over."""


def decode_stream(data: bytes, expected: int) -> bytes:
    """Decode one terrain stream, or refuse.

    ``expected`` is the file's own leading word. It is required rather than
    inferred: a decoder that stops when it feels finished cannot tell a correct
    decode from a desynchronised one that happened to run out of input.
    """
    if len(data) < STREAM_START:
        raise TerrainStreamError(f"shorter than the size word: {len(data)} bytes")
    out = bytearray()
    cursor = STREAM_START
    end = len(data)

    def extend(value: int, cur: int) -> tuple[int, int]:
        while True:
            if cur >= end:
                raise TerrainStreamError("length extension runs past the end")
            extra = data[cur]
            cur += 1
            value += extra
            if extra != EXTENSION_ESCAPE:
                return value, cur

    while cursor < end:
        if end - cursor == TAIL_LITERALS + 1:
            # The closing run: one token byte, then the final literals.
            out += data[cursor + 1:end]
            cursor = end
            break
        token = data[cursor]
        cursor += 1
        literal = token >> 4
        if literal == 15:
            literal, cursor = extend(literal, cursor)
        if cursor + literal > end:
            raise TerrainStreamError("literal run runs past the end")
        out += data[cursor:cursor + literal]
        cursor += literal
        if cursor + 2 > end:
            raise TerrainStreamError("no room for a match offset")
        offset = struct.unpack_from(">H", data, cursor)[0]
        cursor += 2
        if offset == 0 or offset > len(out):
            raise TerrainStreamError(
                f"match offset {offset} reaches before the output ({len(out)} bytes so far)"
            )
        match = (token & 0x0F) + MATCH_BASE
        if (token & 0x0F) == 15:
            match, cursor = extend(match, cursor)
        for _ in range(match):
            out.append(out[len(out) - offset])
    if cursor != end:
        raise TerrainStreamError(f"input not consumed: {end - cursor} bytes left")
    if len(out) != expected:
        raise TerrainStreamError(f"produced {len(out)} bytes, the file declares {expected}")
    return bytes(out)


def payload_period(payload: bytes, limit: int = 4) -> int | None:
    """The smallest period that reproduces the payload, if it is that regular."""
    for period in range(1, limit + 1):
        if len(payload) > period and payload[:-period] == payload[period:]:
            return period
    return None


def check_decoded(data: bytes, out: bytes) -> list[str]:
    """Agreements between a decode and facts read independently from the file.

    A decode that only agrees with itself proves nothing, so this compares against
    the file's leading size word and the header the file carries in the clear.
    """
    problems: list[str] = []
    if out[:4] != MAGIC:
        problems.append("decoded output does not begin with TRET")
        return problems
    declared_total = struct.unpack_from("<I", data, 0)[0]
    payload = struct.unpack_from("<I", out, 16)[0]
    if payload + RECORD_BYTES != declared_total:
        problems.append("decoded payload size disagrees with the leading size word")
    if len(out) - RECORD_BYTES != payload:
        problems.append("decoded body is not the length the decoded header declares")
    at = data.find(MAGIC)
    if at >= STREAM_START and at + RECORD_BYTES <= len(data):
        if data[at:at + RECORD_BYTES] != out[:RECORD_BYTES]:
            problems.append("decoded header differs from the one legible in the file")
    return problems


def summarise(samples: list[tuple[str, bytes]]) -> dict[str, Any]:
    outcomes: Counter[str] = Counter()
    periods: Counter[str] = Counter()
    agreements: Counter[str] = Counter()
    by_channel: dict[str, Counter] = {}
    fences: Counter[str] = Counter()
    for name, data in samples:
        channel = name.split("/")[-1].rsplit("_", 1)[-1].split(".")[0]
        bucket = by_channel.setdefault(channel, Counter())
        if len(data) < STREAM_START + 4:
            outcomes["tooShortForAStream"] += 1
            bucket["fenced"] += 1
            continue
        expected = struct.unpack_from("<I", data, 0)[0]
        try:
            out = decode_stream(data, expected)
        except TerrainStreamError as exc:
            outcomes["fenced"] += 1
            bucket["fenced"] += 1
            reason = str(exc)
            fences["matchOffsetReachesBeforeTheOutput" if reason.startswith("match offset")
                   else reason.split(":")[0]] += 1
            continue
        outcomes["decodedAndClosed"] += 1
        bucket["decoded"] += 1
        problems = check_decoded(data, out)
        if problems:
            outcomes["decodedButDisagrees"] += 1
            for problem in problems:
                agreements[problem] += 1
            continue
        agreements["agreesWithTheFile"] += 1
        period = payload_period(out[RECORD_BYTES:])
        periods[f"period_{period}" if period else "notPeriodicWithinFour"] += 1
    return {
        "outcomes": dict(outcomes.most_common()),
        "fenceReasons": dict(fences.most_common()),
        "decodedPayloadAgreement": dict(agreements.most_common()),
        "decodedPayloadPeriod": dict(periods.most_common()),
        "byChannel": {
            channel: dict(sorted(counts.items()))
            for channel, counts in sorted(by_channel.items())
        },
    }


def every_decode_agrees_with_its_file(summary: dict[str, Any]) -> bool:
    """A decode must agree with facts read independently from the file.

    This is what separates "a decoder ran" from "a decoder is right". The output's
    own header carries a payload size, and the file carries one in its leading word
    and, where the compressor left it legible, in the clear; all three have to say
    the same thing. One disagreement means the decode is producing plausible
    garbage, so the check is equality, not a rate.
    """
    outcomes = summary.get("outcomes") or {}
    decoded = int(outcomes.get("decodedAndClosed") or 0)
    if decoded <= 0:
        return False
    if int(outcomes.get("decodedButDisagrees") or 0):
        return False
    agreements = summary.get("decodedPayloadAgreement") or {}
    return int(agreements.get("agreesWithTheFile") or 0) == decoded


def decoded_tiles_are_regular(summary: dict[str, Any]) -> bool:
    """Most decoded payloads should be flat.

    A terrain tile that decodes to a short repeating pattern is a flat tile, which
    is the commonest thing a terrain field contains and something random bytes do
    not produce. This is corroboration rather than a framing check, so it is stated
    as a majority and kept separate from the agreement gate above -- a decoder that
    was right about structure but produced noise would pass that one and fail this.
    """
    periods = summary.get("decodedPayloadPeriod") or {}
    total = sum(int(value) for value in periods.values())
    if total <= 0:
        return False
    regular = total - int(periods.get("notPeriodicWithinFour") or 0)
    return regular * 2 > total


def load_samples(ledger: Path, limit: int = 0) -> list[tuple[str, bytes]]:
    samples: list[tuple[str, bytes]] = []
    with gzip.open(ledger, "rt", encoding="utf-8") as handle:
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
            if limit and len(samples) >= limit:
                break
    return samples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    try:
        samples = load_samples(args.ledger, args.limit)
    except OSError as exc:
        print(f"terrain stream audit failed: {exc}", file=sys.stderr)
        return 1
    if not samples:
        print("terrain stream audit failed: no Terrain rows", file=sys.stderr)
        return 1

    summary = summarise(samples)
    agrees = every_decode_agrees_with_its_file(summary)
    regular = decoded_tiles_are_regular(summary)
    report = {
        "format": "endfield-terrain-stream-audit",
        "schemaVersion": 1,
        "generatedUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "partial",
        "closureEnforced": True,
        "files": len(samples),
        "gates": {
            "everyDecodeAgreesWithItsFile": agrees,
            "decodedTilesAreRegular": regular,
        },
        "summary": summary,
        "evidenceBoundary": {
            "layer": 3,
            "claim": (
                "the compressed stream in a terrain file is an LZ4 block whose match "
                "offset is big-endian; streams using a single sequence decode to "
                "exactly the declared size with the input exactly consumed, and the "
                "result agrees with the size word and the header the file carries"
            ),
            "semanticStatus": "structural-only",
            "nonClaims": [
                "anything about streams that use more than one sequence; they stop at "
                "the second match, whose offset is only sensible little-endian, and "
                "that contradiction is unresolved",
                "that a preset dictionary explains those files; priming a 64 KB window "
                "does not raise the closure count by one file",
                "what the decoded pixels mean, or what a channel measures",
                "the encoder that produced these streams, or its parameters",
            ],
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    decoded = summary["outcomes"].get("decodedAndClosed", 0)
    print(
        f"Terrain streams: {decoded:,} of {len(samples):,} decode and close; "
        f"every decode agrees with its file: {agrees}; decoded tiles are regular: {regular}"
    )
    print(f"Terrain stream report: {args.output_json}")
    return 0 if (agrees and regular) else 1


if __name__ == "__main__":
    raise SystemExit(main())
