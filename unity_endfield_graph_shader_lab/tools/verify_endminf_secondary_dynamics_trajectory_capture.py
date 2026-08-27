#!/usr/bin/env python3
"""Verify a bounded Endminf four-owner TransformAccess trajectory capture."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_secondary_dynamics_trajectory_capture_latest.json"
)
OWNER_LENGTHS = {"Ribbon2": 6, "Hair": 30, "Ribbon": 20, "Coat": 70}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def finite_vector(row: dict[str, Any], key: str, lanes: int) -> None:
    value = row.get(key)
    require(isinstance(value, list) and len(value) == lanes,
            f"{key} is not a {lanes}-lane vector")
    require(all(isinstance(item, (int, float)) and math.isfinite(item)
                for item in value), f"{key} contains a non-finite lane")


def load_last_window(capture: Path) -> dict[str, Any]:
    path = capture / "secondary-dynamics/windows.jsonl"
    require(path.is_file(), f"dynamics window file is absent: {path}")
    rows = [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    require(rows, "dynamics window file is empty")
    return json.loads(rows[-1])


def build_report(capture: Path, minimum_writebacks: int = 60) -> dict[str, Any]:
    window = load_last_window(capture)
    require(window.get("trajectoryComplete") is True,
            "window does not certify complete trajectory retention")
    require(window.get("endminfTrajectoryFourChunkCandidateCoverage") is True,
            "window does not contain all four Endminf chunk candidates")
    require(window.get("endminfTrajectoryFourOwnerCoverage") is not True,
            "capture must not claim owner identity from chunk length alone")
    require(int(window.get("transformWriteUnreadableCalls", -1)) == 0,
            "one or more transform writes was unreadable")
    require(int(window.get("transformSampleOverflow", -1)) == 0,
            "transform sample capacity overflowed")
    window_id = int(window["windowId"])

    path = capture / "secondary-dynamics/trajectories.jsonl"
    require(path.is_file(), f"trajectory file is absent: {path}")
    by_candidate: dict[tuple[str, int, int], dict[int, list[dict[str, Any]]]] = (
        defaultdict(lambda: defaultdict(list)))
    writeback_timestamps: dict[int, int] = {}
    retained_rows = 0
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if int(row.get("windowId", -1)) != window_id:
                continue
            owner = row.get("endminfOwnerCandidate")
            if owner not in OWNER_LENGTHS:
                continue
            require(int(row.get("proxyTransformLength", -1)) == OWNER_LENGTHS[owner],
                    f"line {line_number} owner length drifted")
            finite_vector(row, "position", 3)
            finite_vector(row, "rotation", 4)
            finite_vector(row, "localPosition", 3)
            finite_vector(row, "localRotation", 4)
            writeback = int(row["writebackId"])
            timestamp = int(row["timestampNs"])
            prior = writeback_timestamps.setdefault(writeback, timestamp)
            require(prior == timestamp,
                    f"writeback {writeback} has inconsistent timestamps")
            key = (owner, int(row["teamId"]), int(row["componentId"]))
            by_candidate[key][writeback].append(row)
            retained_rows += 1

    require(retained_rows == int(window.get("transformSampleCount", -1)),
            "trajectory rows do not match the certified sample count")
    require(len(writeback_timestamps) >= minimum_writebacks,
            f"only {len(writeback_timestamps)} writebacks were retained")
    ordered_writebacks = sorted(writeback_timestamps)
    require(ordered_writebacks == list(range(ordered_writebacks[0],
                                              ordered_writebacks[-1] + 1)),
            "writeback IDs are not contiguous")
    timestamps = [writeback_timestamps[item] for item in ordered_writebacks]
    require(all(right > left for left, right in zip(timestamps, timestamps[1:])),
            "writeback timestamps are not strictly increasing")

    owners: dict[str, dict[str, Any]] = {}
    for owner, length in OWNER_LENGTHS.items():
        candidates = []
        for (candidate_owner, team_id, component_id), writebacks in by_candidate.items():
            if candidate_owner != owner or set(writebacks) != set(ordered_writebacks):
                continue
            valid = True
            chunk_start = None
            for rows in writebacks.values():
                if len(rows) != length:
                    valid = False
                    break
                starts = {int(row["proxyTransformStart"]) for row in rows}
                indices = sorted(int(row["transformIndex"]) for row in rows)
                if len(starts) != 1:
                    valid = False
                    break
                start = next(iter(starts))
                if indices != list(range(start, start + length)):
                    valid = False
                    break
                if chunk_start is None:
                    chunk_start = start
                elif chunk_start != start:
                    valid = False
                    break
            if valid:
                candidates.append((team_id, component_id, chunk_start))
        require(len(candidates) == 1,
                f"{owner} has {len(candidates)} complete team candidates")
        team_id, component_id, chunk_start = candidates[0]
        owners[owner] = {
            "teamId": team_id,
            "componentId": component_id,
            "proxyTransformStart": chunk_start,
            "proxyTransformLength": length,
            "sampleCount": length * len(ordered_writebacks),
        }

    return {
        "schema": "endfield.endminf-secondary-dynamics-trajectory-capture.v2",
        "status": "validated_unique_four_chunk_candidate_trajectory",
        "capture": str(capture.resolve()),
        "windowId": window_id,
        "writebackCount": len(ordered_writebacks),
        "firstTimestampNs": timestamps[0],
        "lastTimestampNs": timestamps[-1],
        "sampleCount": retained_rows,
        "owners": owners,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--minimum-writebacks", type=int, default=60)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve(), args.minimum_writebacks)
    except (OSError, ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
