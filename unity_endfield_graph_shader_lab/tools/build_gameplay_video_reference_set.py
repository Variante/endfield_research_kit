"""Extract a roster-wide reference frame set from the recorded gameplay video.

The lab could previously only be measured against two hand-supplied Character
Info captures. The recorded session walks the whole roster through the same
overview screen at the same 3840x2160 framing, so it can supply one settled
reference frame per character instead.

The video is the same fixture the Li Zhiyan visual oracle already pins, and this
tool re-verifies that pin before reading a frame.

Segmentation keys on the left stat panel rather than the whole frame: idle
animation keeps whole-frame differences high throughout, while the panel is
constant within a character and changes on switch. Each surviving segment
contributes its middle frame, which is settled rather than mid-transition.

Character identity comes from OCR of the name plate. A segment whose name does
not resolve is written to the manifest as unidentified rather than guessed.

Usage:
    python tools/build_gameplay_video_reference_set.py
    python tools/build_gameplay_video_reference_set.py --no-ocr
    python tools/build_gameplay_video_reference_set.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import cv2
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
VIDEO_RELATIVE = "videos/2026-08-15_10-32-32.mkv"
VIDEO_BYTES = 1678613397
VIDEO_SHA256 = "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7"

DEFAULT_OUTPUT = os.path.join(
    PROJECT_ROOT, "scratch", "character_recovery", "gameplay_reference"
)
MANIFEST_NAME = "gameplay_reference_manifest.json"

# Left stat/name panel. Constant within a character, changes on switch.
PANEL_BOX = (60, 300, 820, 1300)
PANEL_SIGNATURE_SIZE = (76, 100)
PANEL_CHANGE_THRESHOLD = 3.0

# Name plate inside the detail view.
NAME_BOX = (150, 420, 1200, 660)

SAMPLE_HZ = 2.0
MINIMUM_SEGMENT_SAMPLES = 6  # about three seconds; shorter spans are transitions
EXPECTED_RESOLUTION = (3840, 2160)


class ReferenceSetError(RuntimeError):
    """Fail-closed extraction error."""


def verify_video(path: str) -> tuple[int, str]:
    if not os.path.isfile(path):
        raise ReferenceSetError(f"video not found: {path}")
    digest = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 22)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    actual = digest.hexdigest().upper()
    if total != VIDEO_BYTES:
        raise ReferenceSetError(f"video byte count changed: {total} != {VIDEO_BYTES}")
    if actual != VIDEO_SHA256:
        raise ReferenceSetError(f"video sha256 changed: {actual} != {VIDEO_SHA256}")
    return total, actual


def _panel_signature(frame: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = PANEL_BOX
    panel = frame[y0:y1, x0:x1]
    grey = cv2.cvtColor(cv2.resize(panel, PANEL_SIGNATURE_SIZE), cv2.COLOR_BGR2GRAY)
    return grey.astype(np.float32)


def segment(video_path: str) -> list[dict]:
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ReferenceSetError(f"could not open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if (width, height) != EXPECTED_RESOLUTION:
        raise ReferenceSetError(
            f"video resolution {width}x{height} is not the expected "
            f"{EXPECTED_RESOLUTION[0]}x{EXPECTED_RESOLUTION[1]}"
        )

    # Decode sequentially and keep every step-th frame. Seeking per sample makes
    # OpenCV decode from the nearest keyframe each time, which on this 35 Mbps
    # 4K stream costs seconds per sample; a single linear pass is far cheaper.
    step = max(1, int(round(fps / SAMPLE_HZ)))
    samples: list[tuple[int, float, np.ndarray]] = []
    index = 0
    while True:
        ok = capture.grab()
        if not ok:
            break
        if index % step == 0:
            ok, frame = capture.retrieve()
            if not ok:
                break
            samples.append((index, index / fps, _panel_signature(frame)))
        index += 1
    capture.release()
    if not samples:
        raise ReferenceSetError("no samples read from the video")

    groups: list[list[tuple[int, float, np.ndarray]]] = [[samples[0]]]
    for previous, current in zip(samples, samples[1:]):
        if float(np.abs(previous[2] - current[2]).mean()) > PANEL_CHANGE_THRESHOLD:
            groups.append([current])
        else:
            groups[-1].append(current)

    segments = []
    for group in groups:
        if len(group) < MINIMUM_SEGMENT_SAMPLES:
            continue
        middle = group[len(group) // 2]
        segments.append(
            {
                "startSeconds": round(group[0][1], 3),
                "endSeconds": round(group[-1][1], 3),
                "durationSeconds": round(group[-1][1] - group[0][1], 3),
                "settledFrame": int(middle[0]),
                "settledSeconds": round(middle[1], 3),
            }
        )
    return segments


def _read_frame(video_path: str, frame_index: int) -> np.ndarray:
    capture = cv2.VideoCapture(video_path)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise ReferenceSetError(f"could not read frame {frame_index}")
    return frame


def _make_reader():
    from paddleocr import PaddleOCR

    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="ch",
    )


def read_name(reader, frame: np.ndarray) -> str | None:
    if reader is None:
        return None
    x0, y0, x1, y1 = NAME_BOX
    crop = frame[y0:y1, x0:x1]
    try:
        result = reader.predict(crop)
    except Exception:
        return None
    texts: list[tuple[float, str]] = []
    for page in result or []:
        names = page.get("rec_texts") or []
        scores = page.get("rec_scores") or []
        for text, score in zip(names, scores):
            cleaned = str(text).strip()
            if cleaned:
                texts.append((float(score), cleaned))
    if not texts:
        return None
    texts.sort(reverse=True)
    return texts[0][1]


def build(output_root: str, use_ocr: bool) -> dict:
    video_path = os.path.join(REPO_ROOT, VIDEO_RELATIVE)
    size, digest = verify_video(video_path)
    segments = segment(video_path)

    os.makedirs(output_root, exist_ok=True)
    reader = _make_reader() if use_ocr else None

    entries = []
    for position, item in enumerate(segments):
        frame = _read_frame(video_path, item["settledFrame"])
        name = read_name(reader, frame) if use_ocr else None
        slug = f"{position:02d}_frame{item['settledFrame']}"
        image_name = f"{slug}.png"
        image_path = os.path.join(output_root, image_name)
        cv2.imwrite(image_path, frame)
        with open(image_path, "rb") as handle:
            payload = handle.read()
        entries.append(
            {
                **item,
                "index": position,
                "displayName": name,
                "identified": bool(name),
                "image": image_name,
                "imageBytes": len(payload),
                "imageSha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    manifest = {
        "schema": "endfield.gameplay-video-reference-set.v1",
        "boundary": "diagnostic_reference_frames",
        "video": {
            "path": VIDEO_RELATIVE,
            "bytes": size,
            "sha256": digest,
        },
        "extraction": {
            "sampleHz": SAMPLE_HZ,
            "panelBox": list(PANEL_BOX),
            "panelChangeThreshold": PANEL_CHANGE_THRESHOLD,
            "minimumSegmentSamples": MINIMUM_SEGMENT_SAMPLES,
            "nameBox": list(NAME_BOX),
            "note": (
                "Segmentation keys on the left stat panel because idle animation "
                "keeps whole-frame differences high throughout the recording. "
                "Each segment contributes its middle frame, which is settled "
                "rather than mid-transition."
            ),
        },
        "policy": (
            "These are reference frames for comparison only. A segment whose "
            "name does not resolve is recorded as unidentified rather than "
            "guessed, and the UI overlay present in every frame means only the "
            "UI-free character band is comparable."
        ),
        "segmentCount": len(entries),
        "identifiedCount": sum(1 for e in entries if e["identified"]),
        "segments": entries,
    }
    with open(os.path.join(output_root, MANIFEST_NAME), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT)
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the video pin and report segmentation without writing frames",
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            video_path = os.path.join(REPO_ROOT, VIDEO_RELATIVE)
            verify_video(video_path)
            segments = segment(video_path)
            print(f"video pin verified; {len(segments)} settled segments")
            for item in segments:
                print(
                    f"  {item['startSeconds']:>8.2f}-{item['endSeconds']:>8.2f}s "
                    f"settled frame {item['settledFrame']}"
                )
            return 0
        manifest = build(args.output_root, not args.no_ocr)
    except ReferenceSetError as error:
        print(f"reference set failed: {error}", file=sys.stderr)
        return 2

    print(
        f"segments {manifest['segmentCount']}, "
        f"identified {manifest['identifiedCount']}"
    )
    for item in manifest["segments"]:
        label = item["displayName"] or "(unidentified)"
        print(f"  {item['index']:>2} {item['settledSeconds']:>8.2f}s  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
