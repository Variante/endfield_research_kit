#!/usr/bin/env python3
"""Measure whether the opt-in exact M14 packet changes over a capture window."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from array import array
from pathlib import Path


STAGE = "before_temporal"
THRESHOLDS = (0.001, 0.01, 0.05, 0.1)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected one JSON object: {path}")
    return value


def decode_ufloat(value: int, mantissa_bits: int) -> float:
    exponent = value >> mantissa_bits
    mantissa = value & ((1 << mantissa_bits) - 1)
    if exponent == 0:
        return math.ldexp(float(mantissa), -14 - mantissa_bits)
    if exponent == 31:
        return math.inf if mantissa == 0 else math.nan
    return math.ldexp(1.0 + mantissa / float(1 << mantissa_bits), exponent - 15)


def decode_b10g11r11(value: int) -> tuple[float, float, float]:
    return (
        decode_ufloat(value & 0x7FF, 6),
        decode_ufloat((value >> 11) & 0x7FF, 6),
        decode_ufloat((value >> 22) & 0x3FF, 5),
    )


def stage_payload(root: Path, frame: int) -> tuple[dict, bytes]:
    frame_root = root / "post_stages" / f"frame_{frame:06d}"
    metadata = load_json(frame_root / f"{STAGE}.json")
    payload = (frame_root / f"{STAGE}.raw").read_bytes()
    if metadata.get("status") != "ok":
        raise ValueError(f"incomplete stage metadata: {frame_root}")
    if metadata.get("graphicsFormat") != "B10G11R11_UFloatPack32":
        raise ValueError(f"unexpected stage format: {frame_root}")
    if len(payload) != int(metadata["byteLength"]):
        raise ValueError(f"stage byte length mismatch: {frame_root}")
    if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
        raise ValueError(f"stage hash mismatch: {frame_root}")
    return metadata, payload


def analyze_frame(full: bytes, excluded: bytes, width: int, height: int) -> dict:
    if len(full) != len(excluded) or len(full) != width * height * 4:
        raise ValueError("incompatible stage payloads")
    full_values = array("I")
    excluded_values = array("I")
    full_values.frombytes(full)
    excluded_values.frombytes(excluded)
    if struct.pack("=I", 1) != struct.pack("<I", 1):
        full_values.byteswap()
        excluded_values.byteswap()

    counts = [0] * len(THRESHOLDS)
    bounds = [[width, height, -1, -1] for _ in THRESHOLDS]
    centroids = [[0.0, 0.0, 0.0] for _ in THRESHOLDS]
    support = set()
    total_delta = 0.0
    max_delta = 0.0
    for index, (left, right) in enumerate(zip(full_values, excluded_values)):
        if left == right:
            continue
        left_rgb = decode_b10g11r11(left)
        right_rgb = decode_b10g11r11(right)
        delta = max(abs(a - b) for a, b in zip(left_rgb, right_rgb))
        if not math.isfinite(delta):
            continue
        total_delta += delta
        max_delta = max(max_delta, delta)
        x = index % width
        y = index // width
        for threshold_index, threshold in enumerate(THRESHOLDS):
            if delta < threshold:
                continue
            counts[threshold_index] += 1
            row = bounds[threshold_index]
            row[0] = min(row[0], x)
            row[1] = min(row[1], y)
            row[2] = max(row[2], x)
            row[3] = max(row[3], y)
            centroid = centroids[threshold_index]
            centroid[0] += x
            centroid[1] += y
            centroid[2] += delta
            if threshold == 0.05:
                support.add(index)

    rows = []
    for threshold, count, bound, centroid in zip(
            THRESHOLDS, counts, bounds, centroids):
        rows.append({
            "threshold": threshold,
            "pixelCount": count,
            "bounds": None if count == 0 else {
                "minX": bound[0], "minY": bound[1],
                "maxX": bound[2], "maxY": bound[3],
            },
            "centroid": None if count == 0 else {
                "x": centroid[0] / count,
                "y": centroid[1] / count,
            },
            "deltaEnergy": centroid[2],
        })
    return {
        "changedPackedPixels": sum(a != b for a, b in zip(full_values, excluded_values)),
        "totalMaxChannelDelta": total_delta,
        "maximumChannelDelta": max_delta,
        "thresholds": rows,
        "support005": support,
    }


def analyze(full_root: Path, excluded_root: Path) -> dict:
    full_report = load_json(full_root / "report.json")
    excluded_report = load_json(excluded_root / "report.json")
    full_frames = full_report.get("frames", [])
    excluded_frames = excluded_report.get("frames", [])
    if len(full_frames) != len(excluded_frames) or not full_frames:
        raise ValueError("capture frame counts are incompatible")

    rows = []
    baseline_support: set[int] | None = None
    previous_support: set[int] | None = None
    for frame in range(len(full_frames)):
        full_meta, full_payload = stage_payload(full_root, frame)
        excluded_meta, excluded_payload = stage_payload(excluded_root, frame)
        if full_meta["sampleTime"] != excluded_meta["sampleTime"]:
            raise ValueError(f"sample-time mismatch at frame {frame}")
        width = int(full_meta["width"])
        height = int(full_meta["height"])
        measured = analyze_frame(full_payload, excluded_payload, width, height)
        support = measured.pop("support005")
        if baseline_support is None:
            baseline_support = support
        union = baseline_support | support
        baseline_iou = len(baseline_support & support) / len(union) if union else 1.0
        if previous_support is None:
            previous_iou = 1.0
        else:
            union = previous_support | support
            previous_iou = len(previous_support & support) / len(union) if union else 1.0
        previous_support = support
        rows.append({
            "frame": frame,
            "sampleTime": full_meta["sampleTime"],
            "support005Sha256": hashlib.sha256(
                b"".join(struct.pack("<I", value) for value in sorted(support))
            ).hexdigest(),
            "support005BaselineIoU": baseline_iou,
            "support005PreviousIoU": previous_iou,
            **measured,
        })

    baseline_hash = rows[0]["support005Sha256"]
    unique_supports = len({row["support005Sha256"] for row in rows})
    return {
        "schema": "endfield.endminf-m14-exact-temporal.v1",
        "status": "measured",
        "scope": "opt-in exact M14 contribution before temporal resolve",
        "fullCapture": str(full_root.resolve()),
        "excludedCapture": str(excluded_root.resolve()),
        "frameCount": len(rows),
        "supportThreshold": 0.05,
        "uniqueSupportMasks": unique_supports,
        "baselineSupportSha256": baseline_hash,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--excluded", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.full, args.excluded)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({report['frameCount']} frames, "
          f"{report['uniqueSupportMasks']} support masks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
