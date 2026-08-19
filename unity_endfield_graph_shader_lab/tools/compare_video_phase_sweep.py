"""Rank swept animation phases against a recorded reference frame.

video_segment_boundaries.json pins each character selection to a frame, which
fixes the animation phase up to a residual of roughly +/- 0.7 s: the character
model swap leads the panel settle by a variable amount, so neither instant is
animation t=0 outright. EndfieldRecoveredOverviewPhaseSweep renders that
residual; this ranks the results.

Ranking is by ECC correlation inside the character band, not by colour delta.
Correlation measures whether the two frames are the same pose related by a
camera transform, which is the question here, and it is largely insensitive to
the shading error that dominates the colour delta. deltaE00 is reported
alongside so a phase is not chosen against an obvious shading regression, but a
smaller delta never on its own proves a phase is the original phase.

The reference is a video frame, not the hash-pinned front_full still that
compare_recovered_vs_original.py measures against; the two are not comparable
and their numbers must not be read against each other.

Usage:
    python tools/compare_video_phase_sweep.py --actor wulfa
    python tools/compare_video_phase_sweep.py --actor wulfa --stem wulfa
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys

import numpy as np
import cv2
from skimage import color as skcolor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare_recovered_vs_original import (  # noqa: E402
    ComparisonError,
    _apply_alignment,
    _estimate_alignment,
    _load_rgb,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
REFERENCE_ROOT = os.path.join(
    PROJECT_ROOT, "scratch", "character_recovery", "gameplay_reference"
)
MANIFEST_PATH = os.path.join(REFERENCE_ROOT, "gameplay_reference_manifest.json")
BOUNDARIES_PATH = os.path.join(REFERENCE_ROOT, "video_segment_boundaries.json")
SETTLED_PATH = os.path.join(REFERENCE_ROOT, "settled_reference_frames.json")
SETTLED_ROOT = os.path.join(REFERENCE_ROOT, "settled")
SWEEP_ROOT = os.path.join(REPO_ROOT, "scratch", "charinfo_phase_sweep")
BAND = [1400, 200, 2500, 2100]
TIME_IN_NAME = re.compile(r"_t(\d+)p(\d+)\.png$")


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _band_delta_e(reference: np.ndarray, recovered: np.ndarray) -> float:
    x0, y0, x1, y1 = BAND
    ref = skcolor.rgb2lab(reference[y0:y1, x0:x1].astype(np.float64) / 255.0)
    rec = skcolor.rgb2lab(recovered[y0:y1, x0:x1].astype(np.float64) / 255.0)
    return float(skcolor.deltaE_ciede2000(ref, rec).mean())


def _settled_reference_frame(actor: str) -> tuple[str, dict]:
    """A frame from after the start clip, where the camera is settled too.

    The entry frames are unusable for this: the Character Info camera is still
    animating through overview_start, so a comparison there measures an
    unrecovered camera path rather than shading.
    """
    if not os.path.isfile(SETTLED_PATH):
        raise ComparisonError(
            "no settled reference set; build it with "
            "tools/build_settled_reference_frames.py"
        )
    report = json.load(io.open(SETTLED_PATH, encoding="utf-8"))
    matches = [f for f in report["frames"] if f["actor"] == actor]
    if not matches:
        raise ComparisonError(
            f"no settled reference frame for '{actor}'. The recording may never "
            "show it after its start clip finishes."
        )
    row = matches[0]
    path = os.path.join(SETTLED_ROOT, row["image"])
    if not os.path.isfile(path):
        raise ComparisonError(f"missing settled frame: {path}")
    actual = _sha256(path)
    if actual != row["imageSha256"]:
        raise ComparisonError(
            f"settled frame {row['image']} does not match its pinned sha256"
        )
    segment = {
        "image": row["image"],
        "imageSha256": row["imageSha256"],
        "settledFrame": row["frameIndex"],
        "settledSeconds": row["frameSeconds"],
        "loopClip": row["loopClip"],
        "loopClipSeconds": row["loopClipSeconds"],
        "loopPhaseSeconds": row["loopPhaseSeconds"],
    }
    return path, segment


def _reference_frame(actor: str) -> tuple[str, dict]:
    manifest = json.load(io.open(MANIFEST_PATH, encoding="utf-8"))
    matches = [
        s for s in manifest["segments"]
        if s.get("actor") == actor and s.get("image")
    ]
    if not matches:
        raise ComparisonError(f"no video reference frame for actor '{actor}'")
    if len(matches) > 1:
        raise ComparisonError(
            f"actor '{actor}' has {len(matches)} reference frames; the "
            "recording holds it in more than one segment, so the phase is "
            "ambiguous. Pick one explicitly before ranking."
        )
    segment = matches[0]
    path = os.path.join(REFERENCE_ROOT, segment["image"])
    if not os.path.isfile(path):
        raise ComparisonError(f"missing reference frame: {path}")
    actual = _sha256(path)
    if actual != segment["imageSha256"]:
        raise ComparisonError(
            f"reference frame {segment['image']} does not match its pinned "
            f"sha256; expected {segment['imageSha256']}, got {actual}"
        )
    return path, segment


def _expected_phase(actor: str) -> dict:
    report = json.load(io.open(BOUNDARIES_PATH, encoding="utf-8"))
    for row in report["boundaries"]:
        if row.get("actor") == actor and row.get("isCharacterSwitch"):
            return {
                "fromPanelSettle": row.get("elapsedToSettledSeconds"),
                "fromModelSwap": row.get("elapsedToSettledFromSwapSeconds"),
                "bandPeakRatio": row.get("bandPeakRatio"),
            }
    return {}


def run(actor: str, stem: str, settled: bool = False) -> dict:
    if settled:
        reference_path, segment = _settled_reference_frame(actor)
    else:
        reference_path, segment = _reference_frame(actor)
    reference = _load_rgb(reference_path)

    pattern = os.path.join(SWEEP_ROOT, stem + "_t*.png")
    renders = sorted(glob.glob(pattern))
    if not renders:
        raise ComparisonError(f"no swept renders matched {pattern}")

    rows = []
    for path in renders:
        match = TIME_IN_NAME.search(os.path.basename(path))
        if match is None:
            raise ComparisonError(f"cannot read a sample time from {path}")
        sample_time = float(f"{match.group(1)}.{match.group(2)}")
        recovered = _load_rgb(path)
        if recovered.shape != reference.shape:
            raise ComparisonError(
                f"{os.path.basename(path)} is {recovered.shape}, reference is "
                f"{reference.shape}"
            )
        warp, alignment = _estimate_alignment(reference, recovered, BAND)
        aligned = _apply_alignment(recovered, warp)
        rows.append({
            "sampleTime": sample_time,
            "file": os.path.basename(path),
            "correlation": alignment["correlation"],
            "translationPixels": alignment["bandTranslationPixels"],
            "rotationDegrees": alignment["rotationDegrees"],
            "trustworthy": alignment["trustworthy"],
            "bandDeltaE00Mean": round(_band_delta_e(reference, aligned), 4),
        })

    rows.sort(key=lambda r: -r["correlation"])
    best = rows[0]
    if settled:
        expected = {
            "loopPhaseSeconds": segment["loopPhaseSeconds"],
            "loopClipSeconds": segment["loopClipSeconds"],
            "loopClip": segment["loopClip"],
        }
    else:
        expected = _expected_phase(actor)
    return {
        "schema": "endfield.charinfo.phase-sweep.v1",
        "boundary": "recorded_video_comparison",
        "actor": actor,
        "referenceKind": "settled_loop" if settled else "entry_midpoint",
        "reference": {
            "frame": segment["image"],
            "sha256": segment["imageSha256"],
            "settledFrame": segment["settledFrame"],
            "settledSeconds": segment["settledSeconds"],
            "note": (
                "A recorded video frame, not the hash-pinned front_full still "
                "that compare_recovered_vs_original.py uses. The two are not "
                "comparable."
            ),
        },
        "expectedPhaseSeconds": expected,
        "band": list(BAND),
        "ranking": "ecc_correlation_descending",
        "rankingNote": (
            "Correlation answers whether the pose matches; deltaE00 is reported "
            "so a phase is not chosen against an obvious shading regression. A "
            "smaller delta never on its own proves a phase is the original."
        ),
        "best": {
            "sampleTime": best["sampleTime"],
            "correlation": best["correlation"],
            "bandDeltaE00Mean": best["bandDeltaE00Mean"],
        },
        "samples": rows,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--stem")
    parser.add_argument("--report")
    parser.add_argument(
        "--settled",
        action="store_true",
        help="compare against a settled-loop frame instead of the entry frame")
    args = parser.parse_args(argv)

    stem = args.stem or args.actor
    try:
        report = run(args.actor.lower(), stem, settled=args.settled)
    except ComparisonError as error:
        print(f"phase sweep comparison failed: {error}", file=sys.stderr)
        return 2

    expected = report["expectedPhaseSeconds"]
    print(f"{report['actor']} phase sweep against {report['reference']['frame']}")
    if expected and args.settled:
        print(f"  computed loop phase: {expected.get('loopPhaseSeconds')}s "
              f"of {expected.get('loopClipSeconds')}s ({expected.get('loopClip')})")
    elif expected:
        print(f"  computed phase: panel settle {expected.get('fromPanelSettle')}s, "
              f"model swap {expected.get('fromModelSwap')}s "
              f"(band peak ratio {expected.get('bandPeakRatio')})")
    print(f"  {'t (s)':>8} {'ECC cc':>9} {'band dE00':>10}  {'translation':>18} {'rot':>8}")
    for row in sorted(report["samples"], key=lambda r: r["sampleTime"]):
        mark = "  <- best" if row["sampleTime"] == report["best"]["sampleTime"] else ""
        print(f"  {row['sampleTime']:>8.3f} {row['correlation']:>9.6f} "
              f"{row['bandDeltaE00Mean']:>10.3f}  "
              f"{str(row['translationPixels']):>18} "
              f"{row['rotationDegrees']:>8.4f}{mark}")
    best = report["best"]
    print(f"  best: t={best['sampleTime']}s, cc={best['correlation']}, "
          f"band dE00={best['bandDeltaE00Mean']}")

    if args.report:
        with io.open(args.report, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print(f"  report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
