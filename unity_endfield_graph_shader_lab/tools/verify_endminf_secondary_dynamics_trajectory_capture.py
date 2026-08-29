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


def load_summary(capture: Path) -> dict[str, Any]:
    path = capture / "secondary-dynamics/summary.json"
    require(path.is_file(), f"dynamics summary is absent: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_first_loop_wrap_ns(capture: Path) -> int:
    path = capture / "graphics/endminf_animator/metadata.json"
    require(path.is_file(), f"Endminf animator metadata is absent: {path}")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    require(metadata.get("schema") ==
            "endfieldCapture.endminfAnimatorTimeline.v3" and
            metadata.get("sequenceComplete") is True,
            "Endminf animator timeline does not certify a complete sequence")
    indices = metadata.get("indices")
    samples = metadata.get("samples")
    require(isinstance(indices, dict) and isinstance(samples, list),
            "Endminf animator timeline structure is incomplete")
    wrap = int(indices.get("firstWrap", -1))
    require(0 <= wrap < len(samples),
            "Endminf animator first-wrap index is outside the sample array")
    sample = samples[wrap]
    tick = int(sample.get("qpcTick", 0))
    frequency = int(sample.get("qpcFrequency", 0))
    require(tick > 0 and frequency > 0,
            "Endminf animator first-wrap clock is invalid")
    return (tick * 1_000_000_000 + frequency - 1) // frequency


def build_report(capture: Path, minimum_writebacks: int = 60) -> dict[str, Any]:
    first_loop_wrap_ns = load_first_loop_wrap_ns(capture)
    summary = load_summary(capture)
    require(summary.get("schema") ==
            "endfieldCapture.secondaryDynamicsSummary.v3",
            "secondary-dynamics summary schema is not v3")
    for field in ("hooksInstalled", "clothUpdateHookInstalled",
                  "alwaysTeamUpdateHookInstalled", "writeTransformHookInstalled",
                  "completeMasterJobHookInstalled", "addClothHookInstalled",
                  "removeClothHookInstalled", "addTransformHookInstalled",
                  "quiescentCleanup",
                  "automaticTriggerCallbackQuiescent", "complete"):
        require(summary.get(field) is True,
                f"secondary-dynamics summary {field} is not true")
    windows_completed = int(summary.get("windowsCompleted", -1))
    require(windows_completed == 1,
            f"expected one completed dynamics window, observed {windows_completed}")
    require(int(summary.get("windowsFailed", -1)) == 0,
            "secondary-dynamics window finalization reported a failure")
    require(int(summary.get("evidenceCompleteWindows", -1)) ==
            windows_completed and
            int(summary.get("evidenceIncompleteWindows", -1)) == 0,
            "secondary-dynamics evidence-window counts are incomplete")
    require(int(summary.get("automaticTriggerArmFailures", -1)) == 0 and
            int(summary.get("automaticTriggerLifecycleFailures", -1)) == 0,
            "secondary-dynamics trigger lifecycle reported a failure")
    window = load_last_window(capture)
    require(window.get("schema") ==
            "endfieldCapture.secondaryDynamicsWindow.v3",
            "secondary-dynamics window schema is not v3")
    prior_present = int(window.get("automaticTriggerPriorPresent", 0))
    graphics_present = int(window.get("automaticTriggerGraphicsPresent", 0))
    require(window.get("automaticTriggerComplete") is True and
            prior_present > 0 and graphics_present > prior_present and
            graphics_present - prior_present <= 2,
            "window is not joined to the exact Animator/graphics trigger")
    require(window.get("trajectoryComplete") is True,
            "window does not certify complete trajectory retention")
    require(window.get("registrationLifecycleJoinComplete") is True,
            "window does not join every sample to its cloth registration")
    require(window.get("effectivePostJobPoseComplete") is True,
            "window does not contain every effective post-job Transform pose")
    scheduled = int(window.get("transformScheduledCalls", -1))
    completed = int(window.get("transformCompletedCalls", -1))
    recorded = int(window.get("transformWriteCalls", -1))
    require(scheduled > 0 and scheduled == completed == recorded,
            "scheduled, completed, and recorded transform writebacks differ")
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
            require(row.get("schema") ==
                    "endfieldCapture.secondaryDynamicsTransform.v2",
                    f"line {line_number} trajectory schema is not v2")
            require(row.get("registrationJoined") is True,
                    f"line {line_number} has no registration lifecycle join")
            require(row.get("effectivePoseReadable") is True,
                    f"line {line_number} has no effective post-job pose")
            finite_vector(row, "effectivePosition", 3)
            finite_vector(row, "effectiveRotation", 4)
            finite_vector(row, "effectiveLocalPosition", 3)
            finite_vector(row, "effectiveLocalRotation", 4)
            for pointer in ("clothProcess", "clothComponent", "clothTransform",
                            "registeredTransform", "liveTransform"):
                value = row.get(pointer)
                require(isinstance(value, str) and value.startswith("0x") and
                        int(value, 16) != 0,
                        f"line {line_number} {pointer} is absent")
            require(row["liveTransform"] == row["registeredTransform"],
                    f"line {line_number} live Transform differs from registration")
            require(int(row.get("registrationStart", -1)) ==
                    int(row.get("transformIndex", -2)) and
                    int(row.get("registrationLength", -1)) == 1,
                    f"line {line_number} registration chunk does not name its row")
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
    require(timestamps[-1] >= first_loop_wrap_ns,
            "secondary-dynamics trajectory ends before the first settled loop wrap")

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
        candidate_rows = [row for rows in by_candidate[
            (owner, team_id, component_id)].values() for row in rows]
        cloth_processes = {row["clothProcess"] for row in candidate_rows}
        cloth_components = {row["clothComponent"] for row in candidate_rows}
        cloth_transforms = {row["clothTransform"] for row in candidate_rows}
        require(len(cloth_processes) == len(cloth_components) ==
                len(cloth_transforms) == 1,
                f"{owner} registration identity changes across writebacks")
        registered_by_index: dict[int, set[str]] = defaultdict(set)
        for row in candidate_rows:
            registered_by_index[int(row["transformIndex"])].add(
                row["registeredTransform"])
        require(all(len(values) == 1 for values in registered_by_index.values()) and
                len({next(iter(values)) for values in
                     registered_by_index.values()}) == length,
                f"{owner} registered Transform identity is not stable and unique")
        owners[owner] = {
            "teamId": team_id,
            "componentId": component_id,
            "proxyTransformStart": chunk_start,
            "proxyTransformLength": length,
            "sampleCount": length * len(ordered_writebacks),
            "clothProcess": next(iter(cloth_processes)),
            "clothComponent": next(iter(cloth_components)),
            "clothTransform": next(iter(cloth_transforms)),
        }

    require(len({row["clothProcess"] for row in owners.values()}) == 4 and
            len({row["clothComponent"] for row in owners.values()}) == 4 and
            len({row["clothTransform"] for row in owners.values()}) == 4,
            "the four chunk candidates do not map to four distinct cloth owners")

    return {
        "schema": "endfield.endminf-secondary-dynamics-trajectory-capture.v2",
        "status": "validated_four_lifecycle_joined_post_job_trajectories",
        "capture": str(capture.resolve()),
        "windowId": window_id,
        "automaticTriggerPriorPresent": prior_present,
        "automaticTriggerGraphicsPresent": graphics_present,
        "writebackCount": len(ordered_writebacks),
        "scheduledWritebackCount": scheduled,
        "firstTimestampNs": timestamps[0],
        "lastTimestampNs": timestamps[-1],
        "firstSettledLoopWrapNs": first_loop_wrap_ns,
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
