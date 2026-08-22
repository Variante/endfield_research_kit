#!/usr/bin/env python3
"""Decode Unity streamed/dense/constant scalar curves with exact bindings."""

from __future__ import annotations

import argparse
import json
import math
import struct
from collections import defaultdict
from pathlib import Path
from typing import Any


def _float(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def binding_dimension(binding: dict[str, Any]) -> int:
    if binding.get("typeID") != "Transform":
        return 1
    return {1: 3, 2: 4, 3: 3, 4: 3}.get(int(binding.get("attribute") or 0), 1)


def binding_lookup(bindings: list[dict[str, Any]]) -> dict[int, tuple[int, int]]:
    result: dict[int, tuple[int, int]] = {}
    curve = 0
    for binding_index, binding in enumerate(bindings):
        for component in range(binding_dimension(binding)):
            result[curve] = (binding_index, component)
            curve += 1
    return result


def streamed_frames(data: list[int]) -> list[tuple[float, list[tuple[int, float]]]]:
    frames = []
    offset = 0
    while offset < len(data):
        if offset + 2 > len(data):
            raise ValueError("truncated streamed frame header")
        time, count = _float(data[offset]), int(data[offset + 1])
        offset += 2
        if count < 0 or offset + count * 5 > len(data):
            raise ValueError("truncated streamed curve keys")
        keys = []
        for _ in range(count):
            keys.append((int(data[offset]), _float(data[offset + 4])))
            offset += 5
        frames.append((time, keys))
    return frames


def decode_scalar_curves(clip: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = ((clip.get("m_ClipBindingConstant") or {}).get("genericBindings") or [])
    raw = (((clip.get("m_MuscleClip") or {}).get("m_Clip")) or {})
    streamed = raw.get("m_StreamedClip") or {}
    dense = raw.get("m_DenseClip") or {}
    constant = raw.get("m_ConstantClip") or {}
    lookup = binding_lookup(bindings)
    expected = len(lookup)
    stream_count = int(streamed.get("curveCount") or 0)
    dense_count = int(dense.get("m_CurveCount") or 0)
    constant_data = constant.get("data") or []
    if stream_count + dense_count + len(constant_data) != expected:
        raise ValueError("binding scalar count does not match clip curve storage")

    events: dict[int, list[dict[str, float]]] = defaultdict(list)
    for time, keys in streamed_frames(streamed.get("data") or []):
        if not math.isfinite(time) or time < 0:
            continue
        for curve, value in keys:
            if curve >= stream_count:
                raise ValueError("streamed curve index exceeds streamed curveCount")
            events[curve].append({"time": time, "value": value})

    frame_count = int(dense.get("m_FrameCount") or 0)
    sample_rate = float(dense.get("m_SampleRate") or 0)
    samples = dense.get("m_SampleArray") or []
    if dense_count:
        if frame_count <= 0 or sample_rate <= 0 or len(samples) != frame_count * dense_count:
            raise ValueError("dense sample dimensions are inconsistent")
        for frame in range(frame_count):
            for curve in range(dense_count):
                events[stream_count + curve].append(
                    {"time": frame / sample_rate, "value": float(samples[frame * dense_count + curve])}
                )
    for index, value in enumerate(constant_data):
        events[stream_count + dense_count + index].append({"time": 0.0, "value": float(value)})

    rows = []
    for curve, (binding_index, component) in lookup.items():
        rows.append({
            "curveIndex": curve,
            "bindingIndex": binding_index,
            "component": component,
            "binding": bindings[binding_index],
            "keys": events[curve],
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    clip = json.loads(args.clip.read_text(encoding="utf-8"))
    payload = {"schema": "unity.animation-clip-scalar-curves.v1", "clip": clip.get("m_Name"), "curves": decode_scalar_curves(clip)}
    text = json.dumps(payload, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
