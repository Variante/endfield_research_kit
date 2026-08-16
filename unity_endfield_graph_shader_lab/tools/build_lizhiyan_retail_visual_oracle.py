#!/usr/bin/env python3
"""Build deterministic, non-admitting visual measurements for Li Zhiyan retail video."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_retail_visual_oracle.json"
)
SCHEMA = "endfield.lizhiyan-retail-visual-oracle.v1"
VIDEO_SHA256 = "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7"
VIDEO_BYTES = 1_678_613_397
WIDTH = 960
HEIGHT = 540
SAMPLES = (
    (38000, "broad_effect_active"),
    (40000, "broad_teal_peak"),
    (42000, "broad_effect_late"),
    (43000, "compact_teal_trail"),
    (44000, "trail_decay"),
    (46000, "settled_no_substantial_teal"),
)
TRANSITION_ANCHORS = (
    (37650, "prior_actor_visible"),
    (37683, "prior_actor_last_residual"),
    (37700, "blank_transition_first"),
    (37867, "blank_transition_last"),
    (37883, "lizhiyan_first_visible"),
    (37950, "lizhiyan_opaque"),
)
ROIS = {
    "actorBody": (1350, 300, 2600, 2050),
    "broadTeal": (500, 450, 3100, 1800),
    "raisedHand": (2150, 650, 2950, 1350),
    "lowerLeftRibbon": (650, 950, 1800, 1750),
}


class VisualOracleError(RuntimeError):
    pass


def require(value: bool, check: str, expected: Any, actual: Any) -> None:
    if not value:
        raise VisualOracleError(
            f"validator=lizhiyan_retail_visual_oracle; check={check}; "
            f"expected={expected}; actual={actual}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _select_expression(samples: Iterable[tuple[int, str]]) -> str:
    return "+".join(f"eq(pts,{pts})" for pts, _ in samples)


def decode_samples(video: Path, ffmpeg: str,
                   samples: tuple[tuple[int, str], ...] = SAMPLES) -> list[bytes]:
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-ss", "37.5", "-copyts", "-i", str(video), "-an",
        "-vf",
        f"select='{_select_expression(samples)}',"
        f"scale={WIDTH}:{HEIGHT}:flags=lanczos,format=rgb24",
        "-fps_mode", "passthrough", "-frames:v", str(len(samples)),
        "-f", "rawvideo", "-",
    ]
    completed = subprocess.run(command, check=False, capture_output=True)
    require(completed.returncode == 0, "ffmpeg_exit", 0, completed.returncode)
    frame_bytes = WIDTH * HEIGHT * 3
    require(
        len(completed.stdout) == frame_bytes * len(samples),
        "decoded_byte_count",
        frame_bytes * len(samples),
        len(completed.stdout),
    )
    return [
        completed.stdout[offset:offset + frame_bytes]
        for offset in range(0, len(completed.stdout), frame_bytes)
    ]


def _scaled_roi(bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bounds
    return (x0 // 4, y0 // 4, x1 // 4, y1 // 4)


def measure_roi(frame: bytes, bounds: tuple[int, int, int, int]) -> dict[str, Any]:
    x0, y0, x1, y1 = _scaled_roi(bounds)
    count = (x1 - x0) * (y1 - y0)
    teal = 0
    red = green = blue = 0
    for y in range(y0, y1):
        row = y * WIDTH * 3
        for x in range(x0, x1):
            index = row + x * 3
            r, g, b = frame[index:index + 3]
            red += r
            green += g
            blue += b
            # Diagnostic chroma predicate, fixed before comparison. It is not
            # a material, draw-ownership, or after-DOF admission test.
            if g >= 80 and b >= 80 and g - r >= 20 and b - r >= 10:
                teal += 1
    return {
        "sourceBoundsXyxy": list(bounds),
        "scaledBoundsXyxy": [x0, y0, x1, y1],
        "pixelCount": count,
        "meanRgb": [round(red / count, 6), round(green / count, 6), round(blue / count, 6)],
        "tealPixelCount": teal,
        "tealCoverage": round(teal / count, 9),
    }


def build(video: Path, ffmpeg: str) -> dict[str, Any]:
    require(video.is_file(), "video_exists", True, video)
    require(video.stat().st_size == VIDEO_BYTES, "video_bytes", VIDEO_BYTES, video.stat().st_size)
    digest = sha256_file(video)
    require(digest == VIDEO_SHA256, "video_sha256", VIDEO_SHA256, digest)
    requested = tuple(sorted(set(SAMPLES + TRANSITION_ANCHORS)))
    frames = decode_samples(video, ffmpeg, requested)
    by_pts = {sample[0]: frame for sample, frame in zip(requested, frames, strict=True)}
    samples = []
    for pts, phase in SAMPLES:
        frame = by_pts[pts]
        samples.append({
            "pts": pts,
            "timeBase": "1/1000",
            "phase": phase,
            "scaledRgb24Sha256": hashlib.sha256(frame).hexdigest().upper(),
            "scaledDimensions": [WIDTH, HEIGHT],
            "rois": {name: measure_roi(frame, bounds) for name, bounds in ROIS.items()},
        })
    transition_anchors = []
    for pts, classification in TRANSITION_ANCHORS:
        frame = by_pts[pts]
        transition_anchors.append({
            "pts": pts,
            "timeBase": "1/1000",
            "classification": classification,
            "scaledRgb24Sha256": hashlib.sha256(frame).hexdigest().upper(),
            "broadTeal": measure_roi(frame, ROIS["broadTeal"]),
        })
    return {
        "schema": SCHEMA,
        "status": "diagnostic_only",
        "visibleAdmission": False,
        "source": {
            "path": video.relative_to(REPO).as_posix(),
            "bytes": VIDEO_BYTES,
            "sha256": digest,
            "dimensions": [3840, 2160],
            "timeBase": "1/1000",
        },
        "decode": {
            "pixelFormat": "rgb24",
            "scaledDimensions": [WIDTH, HEIGHT],
            "scaleFilter": "lanczos",
            "exactInputPts": True,
        },
        "annotations": {
            "method": "bounded visual annotation over exact-PTS decoded frames",
            "intervalPts": [38000, 47000],
            "cameraCutObserved": False,
            "stableUiAndBackground": True,
            "notes": [
                "Li Zhiyan is already visible and the entrance motion is already active at PTS 38000.",
                "Broad teal ribbons peak near PTS 40000; a smaller compact teal trail remains near PTS 43000.",
                "The broad trails decay by PTS 44000 and no substantial teal layer remains at PTS 46000.",
            ],
        },
        "transitionBoundary": {
            "evidenceClass": "exact_pts_frame_hash_plus_bounded_visual_annotation",
            "lastPriorActorResidualPts": 37683,
            "firstBlankPts": 37700,
            "lastBlankPts": 37867,
            "firstLiZhiyanVisiblePts": 37883,
            "firstLiZhiyanOpaquePts": 37950,
            "candidateRestartPts": 37883,
            "candidateRestartStatus": "visual_alignment_candidate_not_original_event_proof",
        },
        "tealPredicateRgb24": "g>=80 && b>=80 && g-r>=20 && b-r>=10",
        "transitionAnchors": transition_anchors,
        "samples": samples,
        "nonClaims": [
            "ROI teal coverage does not identify a material, renderer-list record, descriptor, draw, or submit.",
            "The scaled RGB hashes are visual-regression anchors, not hashes of native render targets.",
            "This contract does not admit the fail-closed Li Zhiyan VFX materials.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=REPO / "videos/2026-08-15_10-32-32.mkv")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    contract = build(args.video.resolve(), args.ffmpeg)
    rendered = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file(), "output_exists", True, args.output)
        require(args.output.read_text(encoding="utf-8") == rendered,
                "output_current", "generated bytes", "drifted")
        print(f"Li Zhiyan retail visual oracle verified: samples={len(contract['samples'])}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: samples={len(contract['samples'])}, visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
