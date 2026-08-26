#!/usr/bin/env python3
"""Measure the isolated M14 change from admitting its exact native mip chain."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


STAGES = (
    "before_temporal",
    "after_temporal_bloom_input",
    "bloom_prefilter_mip0",
    "bloom_reconstructed_mip0",
    "final_uber",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pixel_delta(left: bytes, right: bytes, bytes_per_pixel: int) -> dict:
    if len(left) != len(right) or len(left) % bytes_per_pixel:
        raise ValueError("raw stage payload sizes are incompatible")
    changed_pixels = 0
    changed_bytes = 0
    rgb_absolute_delta = 0
    for offset in range(0, len(left), bytes_per_pixel):
        left_pixel = left[offset : offset + bytes_per_pixel]
        right_pixel = right[offset : offset + bytes_per_pixel]
        if left_pixel != right_pixel:
            changed_pixels += 1
        for channel, (a, b) in enumerate(zip(left_pixel, right_pixel)):
            if a != b:
                changed_bytes += 1
            if bytes_per_pixel == 4 and channel < 3:
                rgb_absolute_delta += abs(a - b)
    return {
        "changedPixels": changed_pixels,
        "changedBytes": changed_bytes,
        "rgbAbsoluteByteDelta": rgb_absolute_delta,
    }


def stage_payload(root: Path, frame: int, stage: str) -> tuple[dict, bytes]:
    stage_root = root / "post_stages" / f"frame_{frame:06d}"
    metadata = load_json(stage_root / f"{stage}.json")
    payload = (stage_root / f"{stage}.raw").read_bytes()
    if metadata["status"] != "ok" or len(payload) != metadata["byteLength"]:
        raise ValueError(f"incomplete stage payload: {stage_root / stage}")
    if sha256(payload) != metadata["sha256"]:
        raise ValueError(f"stage payload hash drifted: {stage_root / stage}")
    return metadata, payload


def analyze(old_full: Path, old_excluded: Path, native_full: Path,
            native_excluded: Path) -> dict:
    rows = []
    for frame in range(3, 9):
        for stage in STAGES:
            old_meta, old_full_bytes = stage_payload(old_full, frame, stage)
            _, old_excluded_bytes = stage_payload(old_excluded, frame, stage)
            native_meta, native_full_bytes = stage_payload(native_full, frame, stage)
            _, native_excluded_bytes = stage_payload(native_excluded, frame, stage)
            if old_excluded_bytes != native_excluded_bytes:
                raise ValueError(
                    f"negative-control drift at frame {frame}, stage {stage}")
            if old_meta["sampleTime"] != native_meta["sampleTime"]:
                raise ValueError(f"sample-time drift at frame {frame}, stage {stage}")
            bpp = int(native_meta["bytesPerPixel"])
            rows.append({
                "frame": frame,
                "sampleTime": native_meta["sampleTime"],
                "stage": stage,
                "graphicsFormat": native_meta["graphicsFormat"],
                "negativeControlByteIdentical": True,
                "decodedPngM14Contribution": pixel_delta(
                    old_full_bytes, old_excluded_bytes, bpp),
                "nativeMipM14Contribution": pixel_delta(
                    native_full_bytes, native_excluded_bytes, bpp),
                "decodedPngToNativeMipFullFrame": pixel_delta(
                    old_full_bytes, native_full_bytes, bpp),
            })
    return {
        "schema": "endfield.endminf-m14-native-mip-delta.v1",
        "status": "source_closed_native_mip_effect_measured",
        "scope": "M14 only; deterministic raised-hand frames 3-8",
        "sourceTexture": {
            "name": "T_fx_glow_105_D",
            "pathId": -3516386400929143739,
            "format": "BC7",
            "width": 256,
            "height": 128,
            "mipCount": 9,
            "payloadBytes": 43728,
            "payloadSha256":
                "ffd3a6f707d0d0a6c92d3012bec11a41b59ab4949e377558f426ead4ad22d672",
        },
        "method": (
            "The old and native full cohorts are each differenced against an "
            "M14-excluded cohort. Excluded outputs are required byte-identical "
            "across builds before attributing any full-frame change to the mip chain."
        ),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-full", type=Path, required=True)
    parser.add_argument("--old-excluded", type=Path, required=True)
    parser.add_argument("--native-full", type=Path, required=True)
    parser.add_argument("--native-excluded", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        args.old_full, args.old_excluded, args.native_full,
        args.native_excluded)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(report['rows'])} stage comparisons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
