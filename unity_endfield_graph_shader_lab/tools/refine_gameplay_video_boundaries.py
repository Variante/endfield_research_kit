"""Pin each character-selection moment in the recorded session to a single frame.

build_gameplay_video_reference_set.py samples the left stat panel at 2 Hz, so a
segment's recorded startSeconds sits on a 0.5 s grid. The source is natively
60 fps, so the same event can be located to a single frame.

What the gaps between segments actually contain, from the panel signal: not an
instantaneous switch but a continuous run of panel motion lasting 3.5 to 11 s.
The character list lives inside the panel box, so that run is the player
navigating it. The selection completes when the motion stops. So the instant to
measure is the *end* of panel activity, and matching against a settled panel
image does not work -- consecutive segments can be the same character, whose
panels then sit well inside the change threshold.

Measured against the recorded 2 Hz starts, the end of activity lands within
about a tenth of a second of them, so this refines those values rather than
correcting them.

Three boundaries are not character switches at all: camille, yvonne and dapan
each occupy two consecutive segments, so the panel changed while the character
did not. Those are tab transitions and are flagged, because no overview_start
replays across them.

This measures the recording. It does not recover animation state: the offset
between the panel settling and the character model's animation t=0 stays a free
constant.

Usage:
    python tools/refine_gameplay_video_boundaries.py
    python tools/refine_gameplay_video_boundaries.py --check
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys

import cv2
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
REFERENCE_ROOT = os.path.join(
    PROJECT_ROOT, "scratch", "character_recovery", "gameplay_reference"
)
MANIFEST_PATH = os.path.join(REFERENCE_ROOT, "gameplay_reference_manifest.json")
OUTPUT_PATH = os.path.join(REFERENCE_ROOT, "video_segment_boundaries.json")

# Identical to build_gameplay_video_reference_set.py; the two must agree or the
# refined instants are not comparable with the segments they refine.
PANEL_BOX = (60, 300, 820, 1300)
PANEL_SIGNATURE_SIZE = (96, 128)

# Validated character-only region, from config/visual_comparison_rois.json.
# The panel settle marks selection; the model swap is what animation t=0 rides
# on, so it is measured separately rather than assumed to coincide.
BAND_BOX = (1400, 200, 2500, 2100)
BAND_SIGNATURE_SIZE = (110, 190)
BAND_SEARCH_FRAMES = 90

# Consecutive-frame panel difference. Settled panels sit at 0.0 to 0.1 and
# navigation peaks between 13 and 60, so this sits far from either edge.
#
# One threshold, not two. Separate active and quiet levels leave a dead band
# that a decaying fade tail sits inside: every candidate for the last active
# frame is then followed by frames that are neither active nor quiet, and the
# scan resolves nothing. A single level resolved all 32 windows; 0.3 and 0.5
# each left two unresolved, and 2.0 left one.
PANEL_MOTION_THRESHOLD = 1.0
# Quiet must hold this long after the last active frame, so a single-frame
# blip cannot be read as the end of navigation. Raising this to 30 changes no
# result, so the signal is not marginal here.
QUIET_HOLD_FRAMES = 12
# Extra context decoded on each side of a gap.
WINDOW_MARGIN_SECONDS = 1.5


class BoundaryError(RuntimeError):
    """Fail-closed measurement error."""


def _signature(frame, box, size):
    x0, y0, x1, y1 = box
    crop = frame[y0:y1, x0:x1]
    grey = cv2.cvtColor(cv2.resize(crop, size), cv2.COLOR_BGR2GRAY)
    return grey.astype(np.float32)


def _panel_signature(frame):
    return _signature(frame, PANEL_BOX, PANEL_SIGNATURE_SIZE)


def _band_signature(frame):
    return _signature(frame, BAND_BOX, BAND_SIGNATURE_SIZE)


def _consecutive(signatures, frames):
    """Mean absolute difference between neighbouring frames, keyed by the later."""
    difference = {}
    for position in range(1, len(frames)):
        a, b = frames[position - 1], frames[position]
        if b - a == 1:
            difference[b] = float(np.abs(signatures[b] - signatures[a]).mean())
    return difference


def refine(video_path, manifest):
    segments = manifest["segments"]
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise BoundaryError("could not open video: " + video_path)
    fps = capture.get(cv2.CAP_PROP_FPS)
    if abs(fps - 60.0) > 0.01:
        raise BoundaryError("expected 60 fps, got " + str(fps))

    wanted = set()
    windows = []
    margin = int(round(WINDOW_MARGIN_SECONDS * fps))
    for index in range(1, len(segments)):
        previous = segments[index - 1]
        current = segments[index]
        lo = max(0, int(round(previous["endSeconds"] * fps)) - margin)
        hi = int(round(current["startSeconds"] * fps)) + margin
        if hi <= lo:
            raise BoundaryError("segment %d has an empty search window" % index)
        windows.append((index, lo, hi))
        wanted |= set(range(lo, hi + 1))

    # One linear pass: grab() skips cheaply, retrieve() decodes only what is
    # wanted. Seeking per frame would decode from the nearest keyframe each
    # time and cost orders of magnitude more on this 4K stream.
    signatures = {}
    band_signatures = {}
    frame_index = 0
    highest = max(wanted)
    while frame_index <= highest:
        if not capture.grab():
            break
        if frame_index in wanted:
            ok, frame = capture.retrieve()
            if not ok:
                break
            signatures[frame_index] = _panel_signature(frame)
            band_signatures[frame_index] = _band_signature(frame)
        frame_index += 1
    capture.release()

    results = []
    for index, lo, hi in windows:
        previous = segments[index - 1]
        current = segments[index]
        frames = [f for f in range(lo, hi + 1) if f in signatures]
        if len(frames) < QUIET_HOLD_FRAMES + 2:
            raise BoundaryError("segment %d decoded too few window frames" % index)

        difference = _consecutive(signatures, frames)
        band_difference = _consecutive(band_signatures, frames)
        if not difference:
            raise BoundaryError("segment %d produced no frame differences" % index)

        ordered = sorted(difference)
        # Scan backward for the end of navigation. Searching forward instead
        # would stop in the quiet tail of the previous segment, which is inside
        # the window by construction.
        settle = None
        activity_end = None
        for position in range(len(ordered) - 1, -1, -1):
            frame = ordered[position]
            if difference[frame] <= PANEL_MOTION_THRESHOLD:
                continue
            # The highest active frame must itself be followed by sustained
            # quiet. If it is not, the window ends mid-navigation and this
            # fails closed rather than reporting an earlier, wrong instant.
            tail = ordered[position + 1:position + 1 + QUIET_HOLD_FRAMES]
            if len(tail) == QUIET_HOLD_FRAMES and all(
                difference[f] <= PANEL_MOTION_THRESHOLD for f in tail
            ):
                activity_end = frame
                settle = frame + 1
            break

        # First frame of the final run of activity: the player starting to
        # navigate. Recorded for context; it is not tied to animation t=0.
        activity_start = None
        if activity_end is not None:
            activity_start = activity_end
            for position in range(ordered.index(activity_end) - 1, -1, -1):
                frame = ordered[position]
                if difference[frame] > PANEL_MOTION_THRESHOLD:
                    activity_start = frame
                else:
                    break

        # Character-model swap. The band is never static -- the character idles
        # throughout -- so this is a spike far above the idle level rather than
        # a transition into quiet. Where the spike towers over idle it is
        # unambiguous; where the band churns through the whole window it is not,
        # so the ratio is reported and the caller can judge.
        model_swap = None
        band_peak = None
        band_idle = None
        band_ratio = None
        if settle is not None and band_difference:
            band_idle = float(np.median(list(band_difference.values())))
            nearby = [
                (band_difference[f], f)
                for f in band_difference
                if abs(f - settle) <= BAND_SEARCH_FRAMES
            ]
            if nearby:
                band_peak, model_swap = max(nearby)
                band_ratio = band_peak / max(band_idle, 1e-6)

        same_actor = (
            current.get("actor") is not None
            and current.get("actor") == previous.get("actor")
        )
        row = {
            "index": index,
            "actor": current.get("actor"),
            "templateId": current.get("templateId"),
            "previousActor": previous.get("actor"),
            "sameActorAsPrevious": same_actor,
            "isCharacterSwitch": (not same_actor) and current.get("actor") is not None,
            "recordedStartSeconds": current["startSeconds"],
            "settledFrame": int(current["settledFrame"]),
            "settledSeconds": current["settledSeconds"],
            "searchWindowFrames": [lo, hi],
            "activityStartFrame": activity_start,
            "activityEndFrame": activity_end,
            "settleFrame": settle,
            "settleSeconds": round(settle / fps, 4) if settle is not None else None,
        }
        if settle is not None:
            row["elapsedToSettledSeconds"] = round(
                current["settledSeconds"] - settle / fps, 4
            )
            row["recordedStartMinusSettleSeconds"] = round(
                current["startSeconds"] - settle / fps, 4
            )
        if model_swap is not None:
            row["modelSwapFrame"] = model_swap
            row["modelSwapSeconds"] = round(model_swap / fps, 4)
            row["modelSwapMinusSettleSeconds"] = round(
                (model_swap - settle) / fps, 4
            )
            row["bandIdleMedian"] = round(band_idle, 4)
            row["bandPeak"] = round(band_peak, 4)
            row["bandPeakRatio"] = round(band_ratio, 2)
            row["elapsedToSettledFromSwapSeconds"] = round(
                current["settledSeconds"] - model_swap / fps, 4
            )
        if activity_start is not None and activity_end is not None:
            row["navigationSeconds"] = round(
                (activity_end - activity_start) / fps, 4
            )
        results.append(row)

    resolved = [r for r in results if r["settleFrame"] is not None]
    if not resolved:
        raise BoundaryError("no boundary was resolved")

    offset = [r["recordedStartMinusSettleSeconds"] for r in resolved]
    swap_offset = [
        r["modelSwapMinusSettleSeconds"] for r in resolved
        if r["isCharacterSwitch"] and "modelSwapMinusSettleSeconds" in r
    ]
    elapsed = [
        r["elapsedToSettledSeconds"] for r in resolved if r["isCharacterSwitch"]
    ]
    switches = [r for r in results if r["isCharacterSwitch"]]
    return {
        "schema": "endfield.gameplay-video.boundaries.v2",
        "boundary": "recorded_video_measurement",
        "video": manifest["video"],
        "method": {
            "panelBox": list(PANEL_BOX),
            "panelSignatureSize": list(PANEL_SIGNATURE_SIZE),
            "panelMotionThreshold": PANEL_MOTION_THRESHOLD,
            "quietHoldFrames": QUIET_HOLD_FRAMES,
            "windowMarginSeconds": WINDOW_MARGIN_SECONDS,
            "fps": fps,
            "note": (
                "The instant measured is the end of panel motion, found by "
                "scanning each gap backward. The character list is inside the "
                "panel box, so a gap is the player navigating it and the "
                "selection completes when motion stops. Matching against a "
                "settled panel image does not work: consecutive segments can "
                "hold the same character, whose panels sit inside the change "
                "threshold."
            ),
        },
        "totals": {
            "segments": len(segments),
            "windows": len(windows),
            "resolved": len(resolved),
            "unresolved": len(results) - len(resolved),
            "characterSwitches": len(switches),
            "withinCharacterBoundaries": sum(
                1 for r in results if r["sameActorAsPrevious"]
            ),
        },
        "recordedStartMinusSettleSeconds": {
            "note": (
                "How far the 2 Hz recorded start sat from the measured end of "
                "navigation. Small values mean the segmentation was already "
                "landing on this event and this refines it to a frame."
            ),
            "min": round(min(offset), 4),
            "max": round(max(offset), 4),
            "mean": round(float(np.mean(offset)), 4),
            "absMax": round(max(abs(v) for v in offset), 4),
        },
        "elapsedToSettledSeconds": {
            "note": (
                "Selection to the reference frame, for character switches only. "
                "This is the quantity the animation phase is computed from, "
                "less the still-unknown offset to animation t=0."
            ),
            "min": round(min(elapsed), 4),
            "max": round(max(elapsed), 4),
            "mean": round(float(np.mean(elapsed)), 4),
        },
        "coverage": {
            "note": (
                "Two lab actors never appear in the recording, so they have no "
                "video reference frame at any phase."
            ),
            "labActorsWithoutVideo": ["endminm", "laevat"],
        },
        "modelSwapMinusSettleSeconds": {
            "note": (
                "Character-band spike minus panel settle, for character "
                "switches. It is not a constant, so the panel settle is not a "
                "reliable stand-in for animation t=0. Where bandPeakRatio is "
                "large the spike is unambiguous and is the better estimate; "
                "the spread bounds the residual phase uncertainty."
            ),
            "min": round(min(swap_offset), 4) if swap_offset else None,
            "max": round(max(swap_offset), 4) if swap_offset else None,
            "mean": round(float(np.mean(swap_offset)), 4) if swap_offset else None,
            "median": round(float(np.median(swap_offset)), 4) if swap_offset else None,
            "std": round(float(np.std(swap_offset)), 4) if swap_offset else None,
        },
        "unrecovered": (
            "Animation t=0 itself. The panel settle and the model swap are both "
            "pinned to a frame, but they disagree by a variable amount, so "
            "neither is t=0 outright. What remains is a residual of roughly "
            "plus or minus 0.7 s, which a short local sweep around the computed "
            "phase can close -- far cheaper than sweeping an unknown phase "
            "across a whole loop."
        ),
        "boundaries": results,
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isfile(MANIFEST_PATH):
        print("missing manifest: " + MANIFEST_PATH, file=sys.stderr)
        return 2
    manifest = json.load(io.open(MANIFEST_PATH, encoding="utf-8"))
    video_path = os.path.join(REPO_ROOT, manifest["video"]["path"])
    if not os.path.isfile(video_path):
        print("missing video: " + video_path, file=sys.stderr)
        return 2

    try:
        report = refine(video_path, manifest)
    except BoundaryError as error:
        print("boundary refinement failed: %s" % error, file=sys.stderr)
        return 2

    if args.check:
        if not os.path.isfile(OUTPUT_PATH):
            print("missing report: " + OUTPUT_PATH, file=sys.stderr)
            return 2
        existing = json.load(io.open(OUTPUT_PATH, encoding="utf-8"))
        if existing != report:
            print("report differs from a fresh rescan", file=sys.stderr)
            return 1
        print("boundaries match: %d resolved" % report["totals"]["resolved"])
        return 0

    with io.open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    totals = report["totals"]
    offset = report["recordedStartMinusSettleSeconds"]
    elapsed = report["elapsedToSettledSeconds"]
    print("wrote " + os.path.relpath(OUTPUT_PATH, PROJECT_ROOT))
    print("  windows %d, resolved %d, unresolved %d" % (
        totals["windows"], totals["resolved"], totals["unresolved"]))
    print("  character switches %d, within-character boundaries %d" % (
        totals["characterSwitches"], totals["withinCharacterBoundaries"]))
    print("  recorded start vs measured settle: %s..%s s (abs max %s s)" % (
        offset["min"], offset["max"], offset["absMax"]))
    print("  selection to reference frame: %s..%s s (mean %s s)" % (
        elapsed["min"], elapsed["max"], elapsed["mean"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
