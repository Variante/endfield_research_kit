#!/usr/bin/env python3
"""Verify an unbound Endminf Uber-shaped candidate in the shared CB ring."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path


LINE = re.compile(r"^cb1\[(\d+)\]\.([xyzw]): (.+)$")
COMPONENT = {"x": 0, "y": 1, "z": 2, "w": 3}
EXPECTED = {
    "centerX": 0.509984434,
    "centerY": 0.532905281,
    "radial": 0.101738632,
    "power": 1.0,
    "mode": 3.0,
    "chromatic": 0.0942715853,
}


def close(actual: float, expected: float, tolerance: float = 1.0e-7) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--capture",
        type=Path,
        default=Path(
            "scratch/character_recovery/3dmigoto-dev-v1.0.0/package/"
            "FrameAnalysis-2026-08-24-182850"
        ),
    )
    args = parser.parse_args()
    matches = sorted(
        args.capture.glob(
            "*-ps-cb1=*-vs=833324977c629596-ps=bcbd3cc174bf08dc.txt"
        )
    )
    if len(matches) != 1:
        raise ValueError(f"expected one active Uber pass cbuffer, found {len(matches)}")

    vectors: dict[int, list[float]] = {}
    with matches[0].open("r", encoding="utf-8") as handle:
        for text in handle:
            match = LINE.match(text.rstrip())
            if not match:
                continue
            index = int(match.group(1))
            vector = vectors.setdefault(index, [math.nan] * 4)
            vector[COMPONENT[match.group(2)]] = float(match.group(3))

    candidates = []
    for index, radial in vectors.items():
        params2 = vectors.get(index + 25)
        if params2 is None or any(math.isnan(value) for value in radial + params2):
            continue
        if not (
            0.0 <= radial[0] <= 1.0
            and 0.0 <= radial[1] <= 1.0
            and 0.05 <= radial[2] <= 0.15
            and close(radial[3], 1.0)
            and close(params2[0], round(params2[0]))
            and 1.0 <= params2[0] <= 7.0
            and 0.05 <= params2[1] <= 0.15
            and close(params2[2], 0.0)
            and close(params2[3], 0.0)
        ):
            continue
        candidates.append((index, radial, params2))

    if len(candidates) != 1:
        raise ValueError(f"expected one radial/chromatic c0/c25 pair, found {candidates}")
    index, radial, params2 = candidates[0]
    actual = {
        "centerX": radial[0],
        "centerY": radial[1],
        "radial": radial[2],
        "power": radial[3],
        "mode": params2[0],
        "chromatic": params2[1],
    }
    failures = [
        f"{name}: expected {EXPECTED[name]}, got {actual[name]}"
        for name in EXPECTED
        if not close(actual[name], EXPECTED[name])
    ]
    if failures:
        raise ValueError("; ".join(failures))
    print(
        "endminf_uber_unbound_ring_candidate_ok: "
        f"cb1[{index}]=({radial[0]:.9f},{radial[1]:.9f},"
        f"{radial[2]:.9f},{radial[3]:.1f}), "
        f"cb1[{index + 25}]=({params2[0]:.0f},{params2[1]:.9f},0,0)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
