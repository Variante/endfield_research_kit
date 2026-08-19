"""Extract reference frames from the settled overview loop, not the entry.

The original reference set took each segment's middle frame. That frame catches
the character inside its ui_overview_start clip, where the Character Info camera
is still moving -- the track prefab carries lookat_overview_ani plus a
DollyCart and Paths, none of which the recovered static vcam_overview
reproduces. Comparing against those frames measures that camera difference and
nothing else: alignment correlation sits near 0.35 against a 0.5 trust floor,
with 6 to 7 degrees of residual rotation.

A frame taken after the start clip finishes has both the camera and the
character settled, so the recovered static camera is the right one and the
comparison measures shading. This picks such a frame per actor, where the
recording lingered long enough to contain one.

The animation phase at that frame is a position in the looping clip:

    phase = (frameTime - selection - startClipLength) mod loopClipLength

Two things that carries. Selection is pinned to a frame by
video_segment_boundaries.json, but animation t=0 is not: the model swap leads
the panel settle by a variable amount, leaving about +/- 0.7 s. The loop clips
run 1.7 to 3.3 s, so that residual is a large fraction of a loop and the phase
here is a starting point for a short sweep rather than an answer. It also
assumes the loop begins at t=0 the moment the start clip ends, with no blend;
the controller transitions were not recovered.

Usage:
    python tools/build_settled_reference_frames.py
    python tools/build_settled_reference_frames.py --actors pelica,chen,endmin
    python tools/build_settled_reference_frames.py --check
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import sys

import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
REFERENCE_ROOT = os.path.join(
    PROJECT_ROOT, "scratch", "character_recovery", "gameplay_reference"
)
MANIFEST_PATH = os.path.join(REFERENCE_ROOT, "gameplay_reference_manifest.json")
BOUNDARIES_PATH = os.path.join(REFERENCE_ROOT, "video_segment_boundaries.json")
CLIP_CONTRACT_PATH = os.path.join(
    PROJECT_ROOT, "Assets", "EndfieldGraphShaderLab", "Generated", "OriginalData",
    "CharInfoPresentation", "charinfo_overview_clip_contract.json",
)
PLAYABLE_ROOT = os.path.join(
    PROJECT_ROOT, "Assets", "EndfieldGraphShaderLab", "Generated", "Characters",
    "Playable",
)
OUTPUT_ROOT = os.path.join(REFERENCE_ROOT, "settled")
OUTPUT_PATH = os.path.join(REFERENCE_ROOT, "settled_reference_frames.json")

# Clearance after the start clip ends, so any unrecovered blend into the loop
# has finished, and before the segment ends, so the next transition is clear.
SETTLE_CLEARANCE_SECONDS = 1.0
SEGMENT_TAIL_CLEARANCE_SECONDS = 0.5
# operator_lights.json and the camera contract carry the same alias.
ACTOR_ALIASES = {"endmin": "Endminf"}


class SettledFrameError(RuntimeError):
    """Fail-closed extraction error."""


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stop_time(path):
    for line in io.open(path, encoding="utf-8", errors="replace"):
        if "m_StopTime:" in line:
            return float(line.split(":")[1].strip())
    raise SettledFrameError("no m_StopTime in " + path)


def _start_clip(actor_dir):
    base = os.path.join(PLAYABLE_ROOT, actor_dir, "Animations")
    lowered = actor_dir.lower()
    for suffix in ("_ui_overview_start_01", "_ui_overview_start"):
        for path in glob.glob(os.path.join(base, "*.anim")):
            if os.path.basename(path)[:-5].lower() == "a_actor_" + lowered + suffix:
                return path
    raise SettledFrameError("no overview start clip for " + actor_dir)


def plan(selected=None):
    manifest = json.load(io.open(MANIFEST_PATH, encoding="utf-8"))
    boundaries = json.load(io.open(BOUNDARIES_PATH, encoding="utf-8"))
    clips = json.load(io.open(CLIP_CONTRACT_PATH, encoding="utf-8"))
    segments = {s["index"]: s for s in manifest["segments"]}
    by_dir = {e["actor"].lower(): e for e in clips["entries"]}

    rows, skipped = [], []
    for row in boundaries["boundaries"]:
        if not row.get("isCharacterSwitch"):
            continue
        actor = row["actor"]
        if selected and actor not in selected:
            continue
        actor_dir = ACTOR_ALIASES.get(actor)
        if actor_dir is None:
            entry = by_dir.get(actor)
            actor_dir = entry["actor"] if entry else None
        if actor_dir is None:
            skipped.append({"actor": actor, "reason": "no lab actor directory"})
            continue
        loop_clip = by_dir[actor_dir.lower()]["clip"]
        loop_length = _stop_time(
            os.path.join(PLAYABLE_ROOT, actor_dir, "Animations", loop_clip + ".anim")
        )
        start_path = _start_clip(actor_dir)
        start_length = _stop_time(start_path)

        segment = segments[row["index"]]
        selection = row["settleSeconds"]
        window_lo = selection + start_length + SETTLE_CLEARANCE_SECONDS
        window_hi = segment["endSeconds"] - SEGMENT_TAIL_CLEARANCE_SECONDS
        if window_hi <= window_lo:
            skipped.append({
                "actor": actor,
                "reason": "recording never shows this character settled",
                "startClipSeconds": round(start_length, 4),
                "availableSeconds": round(
                    segment["endSeconds"] - selection, 4),
            })
            continue

        frame_seconds = (window_lo + window_hi) / 2.0
        frame_index = int(round(frame_seconds * 60.0))
        frame_seconds = frame_index / 60.0
        elapsed = frame_seconds - selection
        phase = (elapsed - start_length) % loop_length
        rows.append({
            "actor": actor,
            "actorDirectory": actor_dir,
            "segmentIndex": row["index"],
            "selectionSeconds": selection,
            "startClip": os.path.basename(start_path)[:-5],
            "startClipSeconds": round(start_length, 4),
            "loopClip": loop_clip,
            "loopClipSeconds": round(loop_length, 4),
            "settledWindowSeconds": [round(window_lo, 4), round(window_hi, 4)],
            "frameIndex": frame_index,
            "frameSeconds": round(frame_seconds, 4),
            "elapsedSinceSelectionSeconds": round(elapsed, 4),
            "loopPhaseSeconds": round(phase, 4),
        })
    return rows, skipped


def extract(rows, video_path):
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise SettledFrameError("could not open video: " + video_path)
    try:
        for row in rows:
            capture.set(cv2.CAP_PROP_POS_FRAMES, row["frameIndex"])
            ok, frame = capture.read()
            if not ok:
                raise SettledFrameError(
                    "could not read frame %d for %s" % (row["frameIndex"], row["actor"])
                )
            name = "%s_settled_frame%d.png" % (row["actor"], row["frameIndex"])
            path = os.path.join(OUTPUT_ROOT, name)
            if not cv2.imwrite(path, frame):
                raise SettledFrameError("could not write " + path)
            row["image"] = name
            row["imageSha256"] = _sha256(path)
            row["imageBytes"] = os.path.getsize(path)
    finally:
        capture.release()
    return rows


def build(selected, video_path):
    rows, skipped = plan(selected)
    if not rows:
        raise SettledFrameError("no actor has a settled frame available")
    rows = extract(rows, video_path)
    return {
        "schema": "endfield.charinfo.settled-reference-frames.v1",
        "boundary": "recorded_video_measurement",
        "video": json.load(io.open(MANIFEST_PATH, encoding="utf-8"))["video"],
        "selection": {
            "settleClearanceSeconds": SETTLE_CLEARANCE_SECONDS,
            "segmentTailClearanceSeconds": SEGMENT_TAIL_CLEARANCE_SECONDS,
            "note": (
                "Frame taken at the middle of the window where the start clip "
                "has finished and the segment has not yet ended, so both the "
                "camera and the character are settled and the recovered static "
                "vcam_overview is the correct camera."
            ),
        },
        "phaseNote": (
            "loopPhaseSeconds = (frameTime - selection - startClipLength) mod "
            "loopClipLength. Selection is frame-accurate but animation t=0 is "
            "not, leaving about +/- 0.7 s; loop clips run 1.7 to 3.3 s, so this "
            "is a sweep starting point rather than an answer. It also assumes "
            "the loop starts at t=0 when the start clip ends, with no blend."
        ),
        "totals": {"extracted": len(rows), "skipped": len(skipped)},
        "skipped": skipped,
        "frames": rows,
    }


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actors", help="comma-separated actor names")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    selected = None
    if args.actors:
        selected = set(a.strip().lower() for a in args.actors.split(",") if a.strip())

    manifest = json.load(io.open(MANIFEST_PATH, encoding="utf-8"))
    video_path = os.path.join(REPO_ROOT, manifest["video"]["path"])
    if not os.path.isfile(video_path):
        print("missing video: " + video_path, file=sys.stderr)
        return 2

    if args.check:
        rows, skipped = plan(selected)
        if not os.path.isfile(OUTPUT_PATH):
            print("missing report: " + OUTPUT_PATH, file=sys.stderr)
            return 2
        existing = json.load(io.open(OUTPUT_PATH, encoding="utf-8"))
        for row in existing["frames"]:
            path = os.path.join(OUTPUT_ROOT, row["image"])
            if not os.path.isfile(path):
                print("missing frame: " + path, file=sys.stderr)
                return 1
            if _sha256(path) != row["imageSha256"]:
                print("frame changed: " + row["image"], file=sys.stderr)
                return 1
        print("settled frames match: %d" % len(existing["frames"]))
        return 0

    try:
        report = build(selected, video_path)
    except SettledFrameError as error:
        print("settled frame extraction failed: %s" % error, file=sys.stderr)
        return 2

    merged = report
    if selected and os.path.isfile(OUTPUT_PATH):
        existing = json.load(io.open(OUTPUT_PATH, encoding="utf-8"))
        keep = [f for f in existing["frames"]
                if f["actor"] not in {r["actor"] for r in report["frames"]}]
        merged["frames"] = sorted(keep + report["frames"], key=lambda r: r["actor"])
        merged["totals"]["extracted"] = len(merged["frames"])

    with io.open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print("wrote " + os.path.relpath(OUTPUT_PATH, PROJECT_ROOT))
    for row in report["frames"]:
        print("  %-10s frame %6d at %7.3fs  loop %-34s phase %.4fs of %.2fs" % (
            row["actor"], row["frameIndex"], row["frameSeconds"],
            row["loopClip"], row["loopPhaseSeconds"], row["loopClipSeconds"]))
    for row in report["skipped"]:
        print("  skipped %-10s %s" % (row["actor"], row["reason"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
