#!/usr/bin/env python3
"""Decode and compare a validated Endminf Streamline surface pair.

The analyzer is intentionally diagnostic-only. It first runs the fail-closed
capture verifier, then emits downsampled PNG previews and sampled linear-space
metrics that distinguish changes already present in the DLSS input from changes
introduced at the retail temporal output boundary.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path
from typing import Iterable

import verify_endminf_streamline_surface_capture as verifier


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_streamline_surface_analysis_latest"
)


def unsigned_float(value: int, mantissa_bits: int) -> float:
    """Decode one unsigned DXGI shared-exponent-style float component."""
    exponent = value >> mantissa_bits
    mantissa = value & ((1 << mantissa_bits) - 1)
    if exponent == 0:
        return math.ldexp(float(mantissa), 1 - 15 - mantissa_bits)
    if exponent == 31:
        return math.inf if mantissa == 0 else math.nan
    return math.ldexp(1.0 + mantissa / float(1 << mantissa_bits), exponent - 15)


def decode_r11g11b10(raw: bytes, offset: int) -> tuple[float, float, float]:
    packed = struct.unpack_from("<I", raw, offset)[0]
    return (
        unsigned_float(packed & 0x7FF, 6),
        unsigned_float((packed >> 11) & 0x7FF, 6),
        unsigned_float((packed >> 22) & 0x3FF, 5),
    )


def decode_rgba16f(raw: bytes, offset: int) -> tuple[float, float, float]:
    red, green, blue, _ = struct.unpack_from("<4e", raw, offset)
    return float(red), float(green), float(blue)


def finite_rgb(value: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(component if math.isfinite(component) else 0.0
                 for component in value)  # type: ignore[return-value]


def linear_to_byte(value: float, exposure: float) -> int:
    value = max(0.0, value * exposure)
    mapped = value / (1.0 + value)
    srgb = (12.92 * mapped if mapped <= 0.0031308 else
            1.055 * mapped ** (1.0 / 2.4) - 0.055)
    return max(0, min(255, round(srgb * 255.0)))


def preview_pixel(value: tuple[float, float, float], exposure: float) -> bytes:
    return bytes(linear_to_byte(component, exposure) for component in value) + b"\xff"


def difference_pixel(
    left: tuple[float, float, float], right: tuple[float, float, float],
    gain: float = 4.0,
) -> bytes:
    return preview_pixel(tuple(abs(a - b) * gain for a, b in zip(left, right)), 1.0)


def png_bytes(width: int, height: int, rows: Iterable[bytes]) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + kind + payload +
                struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))

    scanlines = bytearray()
    count = 0
    expected = width * 4
    for row in rows:
        if len(row) != expected:
            raise ValueError(f"PNG row has {len(row)} bytes; expected {expected}")
        scanlines.append(0)
        scanlines.extend(row)
        count += 1
    if count != height:
        raise ValueError(f"PNG has {count} rows; expected {height}")
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(bytes(scanlines), 9)) +
            chunk(b"IEND", b""))


def write_png(path: Path, width: int, height: int, rows: list[bytes]) -> None:
    path.write_bytes(png_bytes(width, height, rows))


def load_surface(frame_root: Path, name: str, expected_bytes: int) -> bytes:
    path = frame_root / name
    raw = path.read_bytes()
    if len(raw) != expected_bytes:
        raise RuntimeError(
            f"{path}: expected {expected_bytes} bytes, found {len(raw)}")
    return raw


def analyze_pair(
    capture: Path, output: Path, sample_step: int, exposure: float,
) -> dict:
    verification = verifier.build_report(capture)
    if verification.get("status") != "validated":
        errors = verification.get("errors") or ["unknown verification failure"]
        raise RuntimeError("capture verification failed: " + "; ".join(errors[:8]))
    width, height = verifier.WIDTH, verifier.HEIGHT
    sampled_width = (width + sample_step - 1) // sample_step
    sampled_height = (height + sample_step - 1) // sample_step
    frames = []
    for index in range(2):
        root = capture / "graphics/streamline_surfaces" / f"frame{index}"
        frames.append({
            "input": load_surface(root, "input_color.bin", width * height * 4),
            "output": load_surface(root, "output_color.bin", width * height * 8),
        })

    preview_rows = [{"input": [], "output": [], "difference": []}
                    for _ in range(2)]
    input_delta_sum = output_delta_sum = pre_post_sum = 0.0
    input_delta_max = output_delta_max = pre_post_max = 0.0
    output_amplified = 0
    sample_count = 0
    for y in range(0, height, sample_step):
        rows = [{"input": bytearray(), "output": bytearray(),
                 "difference": bytearray()} for _ in range(2)]
        for x in range(0, width, sample_step):
            pixel = y * width + x
            decoded = []
            for index in range(2):
                before = finite_rgb(decode_r11g11b10(frames[index]["input"], pixel * 4))
                after = finite_rgb(decode_rgba16f(frames[index]["output"], pixel * 8))
                decoded.append((before, after))
                rows[index]["input"].extend(preview_pixel(before, exposure))
                rows[index]["output"].extend(preview_pixel(after, exposure))
                rows[index]["difference"].extend(difference_pixel(before, after))
                difference = sum(abs(a - b) for a, b in zip(before, after)) / 3.0
                pre_post_sum += difference
                pre_post_max = max(pre_post_max, difference)
            input_delta = sum(abs(a - b) for a, b in zip(
                decoded[0][0], decoded[1][0])) / 3.0
            output_delta = sum(abs(a - b) for a, b in zip(
                decoded[0][1], decoded[1][1])) / 3.0
            input_delta_sum += input_delta
            output_delta_sum += output_delta
            input_delta_max = max(input_delta_max, input_delta)
            output_delta_max = max(output_delta_max, output_delta)
            if output_delta > input_delta + 1e-4:
                output_amplified += 1
            sample_count += 1
        for index in range(2):
            for name in ("input", "output", "difference"):
                preview_rows[index][name].append(bytes(rows[index][name]))

    output.mkdir(parents=True, exist_ok=True)
    previews = []
    for index in range(2):
        for name in ("input", "output", "difference"):
            path = output / f"frame{index}_{name}.png"
            write_png(path, sampled_width, sampled_height,
                      preview_rows[index][name])
            previews.append(path.name)
        comparison_rows = [
            preview_rows[index]["input"][row] +
            preview_rows[index]["output"][row] +
            preview_rows[index]["difference"][row]
            for row in range(sampled_height)
        ]
        path = output / f"frame{index}_input_output_difference.png"
        write_png(path, sampled_width * 3, sampled_height, comparison_rows)
        previews.append(path.name)

    denominator = max(1, sample_count)
    report = {
        "schema": "endfield.charinfo.endminf-streamline-surface-analysis.v1",
        "status": "diagnostic_complete",
        "capture": str(capture.resolve()),
        "verificationStatus": verification["status"],
        "sourceDimensions": [width, height],
        "sampleStep": sample_step,
        "sampledDimensions": [sampled_width, sampled_height],
        "sampleCount": sample_count,
        "previewExposure": exposure,
        "differencePreviewGain": 4.0,
        "metrics": {
            "meanAbsoluteInputToOutputLinearRgb": pre_post_sum / (denominator * 2),
            "maximumAbsoluteInputToOutputLinearRgb": pre_post_max,
            "meanAbsoluteConsecutiveInputLinearRgb": input_delta_sum / denominator,
            "maximumAbsoluteConsecutiveInputLinearRgb": input_delta_max,
            "meanAbsoluteConsecutiveOutputLinearRgb": output_delta_sum / denominator,
            "maximumAbsoluteConsecutiveOutputLinearRgb": output_delta_max,
            "outputTemporalChangeAmplification": (
                output_delta_sum / input_delta_sum if input_delta_sum > 0 else None),
            "outputChangeGreaterThanInputFraction": output_amplified / denominator,
        },
        "interpretationBoundary": (
            "Previews are fixed-exposure diagnostic tonemaps. Sampled metrics show "
            "whether consecutive output changes exceed consecutive input changes; "
            "they do not alone identify DLSS internals or certify Unity parity."
        ),
        "previews": previews,
    }
    (output / "analysis.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-step", type=int, default=4)
    parser.add_argument("--exposure", type=float, default=1.0)
    args = parser.parse_args()
    if args.sample_step < 1 or args.sample_step > 32:
        parser.error("--sample-step must be between 1 and 32")
    if not math.isfinite(args.exposure) or args.exposure <= 0:
        parser.error("--exposure must be finite and positive")
    try:
        report = analyze_pair(
            args.capture.resolve(), args.output.resolve(),
            args.sample_step, args.exposure)
    except (OSError, RuntimeError, ValueError, struct.error) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(report["metrics"], indent=2))
    print(f"Wrote {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
