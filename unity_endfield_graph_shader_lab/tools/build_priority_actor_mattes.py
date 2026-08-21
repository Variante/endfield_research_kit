"""Build actor-only black-background clips from the pinned gameplay recording.

This is deliberately independent from ``build_gameplay_video_reference_set.py``.
The latter owns roster stills and is often being edited during recovery work;
this tool owns only the two priority actor windows used by the character lab.

The input is a source-pinned 3840x2160/60fps recording.  A pinned
DeepLabV3-ResNet50 person-class model runs at small resolution and is bounded
by hard UI exclusion rectangles.  The output is lossless FFV1 with all pixels
outside the actor matte set to black.  UI exclusions are hard constraints,
not a post-hoc visual claim.  The older colour/GrabCut path remains in the
module for diagnostic probes but is refused by the publication CLI.

The model-swap portions of a requested window can contain no actor at all.
Those frames are retained as black frames and recorded as source transitions;
they are not treated as a segmentation loss.  Any missing component while
the source visibly contains the requested actor, malformed source timing, or
non-zero UI overlap prevents publication.

Usage::

    python tools/build_priority_actor_mattes.py --actor chen --output-root \
        scratch/character_recovery/actor_clips
    python tools/build_priority_actor_mattes.py --actor all --allow-source-transition-gaps
    python tools/build_priority_actor_mattes.py --check-manifest \
        scratch/character_recovery/actor_clips/actor_matte_manifest.json

The generated clips and per-frame JSON are scratch artifacts and must not be
committed.  The script writes only a compact manifest/report to the requested
output root after every gate passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
VIDEO_RELATIVE = Path("videos/2026-08-15_10-32-32.mkv")
VIDEO_BYTES = 1_678_613_397
VIDEO_SHA256 = "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7"
EXPECTED_SIZE = (3840, 2160)
EXPECTED_FPS = 60.0

# These are exact source-window boundaries in seconds from the phase contract.
# End is exclusive at the 60-Hz frame boundary.
ACTOR_WINDOWS = {
    "chen": (199.3000, 209.3333),
    "pelica": (209.3333, 220.6167),
}

# A central actor-safe work region.  It deliberately leaves enough room for
# Chen's hair/weapon and Pelica's extended hand, while excluding the left and
# right information panels.  The bottom band is the fixed foreground status
# area; legs hidden under it are not guessed back into the matte.
ACTOR_ROI = (800, 180, 3000, 2120)  # x0, y0, x1, y1, full-resolution pixels
UI_RECTANGLES = (
    ("top_header", (0, 0, 180, 180)),
    ("left_foreground_panel", (0, 180, 800, 2120)),
    ("right_foreground_panel", (3000, 180, 3840, 2120)),
    ("bottom_foreground_status", (0, 2120, 3840, 2160)),
)

WORK_SIZE = (480, 270)
WORK_ROI = tuple(
    int(round(value * WORK_SIZE[0 if index % 2 == 0 else 1] / EXPECTED_SIZE[0 if index % 2 == 0 else 1]))
    for index, value in enumerate(ACTOR_ROI)
)
BACKGROUND_FRAME = 12567  # known model-swap blank in the pinned recording
FRAME_MISSING_THRESHOLD = 8000  # stable actor support in the 480x270 work frame
TRANSITION_MOTION_THRESHOLD = 4.5  # mean BGR delta at work resolution
MIN_COMPONENT_AREA = 120
KEYFRAME_INTERVAL = 4
DEEPLAB_WEIGHT_SHA256 = "CD0A25694C4A0F7106B38F4938BF90A874F2F241CC410B8F63C7024399538F06"

_DEEPLAB_CONTEXT: tuple[object, object, object, str] | None = None


class MatteError(RuntimeError):
    """A fail-closed source, mask, or publication failure."""


@dataclass(frozen=True)
class ActorWindow:
    actor: str
    start_seconds: float
    end_seconds: float

    @property
    def start_frame(self) -> int:
        return int(round(self.start_seconds * EXPECTED_FPS))

    @property
    def end_frame_exclusive(self) -> int:
        return int(round(self.end_seconds * EXPECTED_FPS))


def _actor_window(actor: str) -> ActorWindow:
    try:
        start, end = ACTOR_WINDOWS[actor]
    except KeyError as error:
        raise MatteError(f"unsupported actor: {actor!r}") from error
    window = ActorWindow(actor, start, end)
    if window.end_frame_exclusive <= window.start_frame:
        raise MatteError(f"invalid source window for {actor}")
    return window


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest().upper()


def verify_source(path: Path) -> dict:
    if not path.is_file():
        raise MatteError(f"source video not found: {path}")
    size, digest = _sha256(path)
    if size != VIDEO_BYTES or digest != VIDEO_SHA256:
        raise MatteError(
            "source video pin mismatch: "
            f"bytes={size} sha256={digest} expected={VIDEO_BYTES}/{VIDEO_SHA256}"
        )
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise MatteError(f"could not open source video: {path}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        width = int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)))
        height = int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        frames = int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    finally:
        capture.release()
    if abs(fps - EXPECTED_FPS) > 0.01 or (width, height) != EXPECTED_SIZE:
        raise MatteError(
            f"source timing/resolution mismatch: {width}x{height} {fps}fps; "
            f"expected {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]} {EXPECTED_FPS}fps"
        )
    for actor in ACTOR_WINDOWS:
        window = _actor_window(actor)
        if window.end_frame_exclusive > frames:
            raise MatteError(f"{actor} window exceeds source frame count {frames}")
    return {
        "path": VIDEO_RELATIVE.as_posix(),
        "bytes": size,
        "sha256": digest,
        "width": width,
        "height": height,
        "fps": fps,
        "frameCount": frames,
    }


def _rect_area(rect: tuple[int, int, int, int]) -> int:
    x0, y0, x1, y1 = rect
    return max(0, x1 - x0) * max(0, y1 - y0)


def apply_hard_exclusions(mask: np.ndarray) -> np.ndarray:
    """Zero every pixel outside the actor ROI and return a copied uint8 mask."""
    if mask.ndim != 2 or mask.shape != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]):
        raise MatteError(f"full mask shape mismatch: {mask.shape}")
    result = np.where(mask > 0, 255, 0).astype(np.uint8)
    x0, y0, x1, y1 = ACTOR_ROI
    constrained = np.zeros_like(result)
    constrained[y0:y1, x0:x1] = result[y0:y1, x0:x1]
    for _name, (rx0, ry0, rx1, ry1) in UI_RECTANGLES:
        constrained[ry0:ry1, rx0:rx1] = 0
    return constrained


def _work_roi_mask() -> np.ndarray:
    x0, y0, x1, y1 = WORK_ROI
    mask = np.zeros((WORK_SIZE[1], WORK_SIZE[0]), np.uint8)
    mask[y0:y1, x0:x1] = 1
    return mask


def _component_filter(mask: np.ndarray, prior: np.ndarray | None) -> np.ndarray:
    """Keep central, temporally consistent components and fill their silhouettes."""
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    # The recording's animated lower backdrop can differ from the blank
    # reference as a single horizontal stripe.  It is not an actor edge.  Cut
    # only long, thin runs before connected-component selection; a character's
    # sword or arm is shorter/thicker and remains evidence-backed.
    x0, _y0, x1, _y1 = WORK_ROI
    row_counts = np.count_nonzero(mask[:, x0:x1] > 0, axis=1)
    stripe_rows = np.flatnonzero(row_counts >= int((x1 - x0) * 0.65))
    if len(stripe_rows):
        # Only erase a short, nearly full-width stripe.  This avoids treating
        # a broad torso row as background while removing the known backdrop
        # band that otherwise joins every candidate to the ROI edges.
        for start, end in _contiguous_ranges(stripe_rows.tolist()):
            if end - start + 1 <= 15:
                mask[max(0, start - 1) : min(mask.shape[0], end + 2), x0:x1] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    if prior is not None and np.count_nonzero(prior) > 0:
        # At 60 Hz the actor moves only a bounded number of work pixels.  This
        # prior is used as a seed, never as a blind copy.
        expanded = cv2.dilate(prior, np.ones((11, 11), np.uint8), iterations=1)
        mask = cv2.bitwise_or(mask, cv2.bitwise_and(expanded, mask))

    count, labels, stats, _centres = cv2.connectedComponentsWithStats(mask, 8)
    candidates: list[tuple[int, int]] = []
    x0, y0, x1, y1 = WORK_ROI
    for index in range(1, count):
        px, py, pw, ph, area = (int(value) for value in stats[index])
        if area < MIN_COMPONENT_AREA:
            continue
        if px + pw <= x0 or px >= x1 or py + ph <= y0 or py >= y1:
            continue
        candidates.append((area, index))
    if not candidates:
        return np.zeros_like(mask)
    # Actor appendages can be separate components.  Retain every substantial
    # component that overlaps the actor envelope; UI is already outside ROI.
    candidates.sort(reverse=True)
    largest = candidates[0][0]
    keep = np.zeros_like(mask)
    for area, index in candidates:
        if area >= max(MIN_COMPONENT_AREA, largest // 24):
            keep[labels == index] = 255
    # Keep the GrabCut support rather than filling an external contour.  A
    # contour can surround a large low-contrast wall wedge behind a moving
    # actor; filling it would turn background into claimed actor pixels.  The
    # small close above restores local cloth continuity without that guess.
    filled = keep
    # Apply the stripe test again after component selection: a backdrop stripe
    # can be connected to the actor before it is selected.
    final_counts = np.count_nonzero(filled[:, x0:x1] > 0, axis=1)
    final_stripes = np.flatnonzero(
        (np.arange(filled.shape[0]) >= WORK_ROI[1] + 40)
        & (final_counts >= int((x1 - x0) * 0.55))
    )
    for start, end in _contiguous_ranges(final_stripes.tolist()):
        if end - start + 1 <= 18 or end >= WORK_ROI[3] - 1:
            filled[max(0, start - 1) : min(filled.shape[0], end + 2), x0:x1] = 0
    return cv2.bitwise_and(filled, (_work_roi_mask() * 255).astype(np.uint8))


def _foreground_mask(
    frame: np.ndarray,
    background: np.ndarray,
    prior: np.ndarray | None,
    frame_number: int,
) -> tuple[np.ndarray, dict]:
    """Extract a work-resolution binary mask and diagnostics for one frame."""
    work = cv2.resize(frame, WORK_SIZE, interpolation=cv2.INTER_AREA)
    bg = background
    lab = cv2.cvtColor(work, cv2.COLOR_BGR2LAB).astype(np.int16)
    lab_bg = cv2.cvtColor(bg, cv2.COLOR_BGR2LAB).astype(np.int16)
    distance = np.linalg.norm(lab - lab_bg, axis=2)
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    grey = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    roi = _work_roi_mask().astype(bool)

    # The blank model is intentionally used only for seeds.  Large static
    # differences (the lower UI gradient) are removed by the hard ROI.
    strong = ((distance > 22.0) | (hsv[:, :, 1] > 42) | (grey < 145)) & roi
    strong_u8 = (strong.astype(np.uint8) * 255)
    strong_u8 = cv2.morphologyEx(strong_u8, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    seed_components, seed_labels, seed_stats, _ = cv2.connectedComponentsWithStats(strong_u8, 8)
    seed_area = int(np.count_nonzero(strong_u8))
    seed_box = None
    if seed_components > 1:
        areas = []
        for index in range(1, seed_components):
            x, y, w, h, area = (int(value) for value in seed_stats[index])
            if area >= 8 and x + w > WORK_ROI[0] and x < WORK_ROI[2] and y + h > WORK_ROI[1] and y < WORK_ROI[3]:
                areas.append((area, x, y, w, h, index))
        if areas:
            area, x, y, w, h, _ = max(areas)
            seed_box = [x, y, x + w, y + h]

    # Build a conservative GrabCut mask.  Unlike a rectangle-only grab, these
    # sure-background seeds keep the blank wall out of the actor silhouette.
    gc = np.full(work.shape[:2], cv2.GC_BGD, dtype=np.uint8)
    x0, y0, x1, y1 = WORK_ROI
    gc[y0:y1, x0:x1] = cv2.GC_PR_BGD
    if prior is not None and np.count_nonzero(prior) > 0:
        prior_expanded = cv2.dilate(prior, np.ones((13, 13), np.uint8), iterations=1)
        gc[prior_expanded > 0] = cv2.GC_PR_FGD
    gc[strong] = cv2.GC_FGD
    # Avoid letting a narrow border/grid line become the only actor component.
    if seed_box is not None:
        sx0, sy0, sx1, sy1 = seed_box
        gc[max(y0, sy0 - 10) : min(y1, sy1 + 10), max(x0, sx0 - 10) : min(x1, sx1 + 10)] = np.where(
            gc[max(y0, sy0 - 10) : min(y1, sy1 + 10), max(x0, sx0 - 10) : min(x1, sx1 + 10)]
            == cv2.GC_BGD,
            cv2.GC_PR_FGD,
            gc[max(y0, sy0 - 10) : min(y1, sy1 + 10), max(x0, sx0 - 10) : min(x1, sx1 + 10)],
        )
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    if seed_area >= FRAME_MISSING_THRESHOLD:
        cv2.grabCut(work, gc, None, bg_model, fg_model, 1, cv2.GC_INIT_WITH_MASK)
        candidate = np.where(
            (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0
        ).astype(np.uint8)
        work_mask = _component_filter(candidate, prior)
    else:
        work_mask = np.zeros((WORK_SIZE[1], WORK_SIZE[0]), np.uint8)

    area = int(np.count_nonzero(work_mask))
    ys, xs = np.where(work_mask > 0)
    bbox = None
    if len(xs):
        bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    diagnostics = {
        "frame": frame_number,
        "workSeedPixels": seed_area,
        "workMaskPixels": area,
        "workMaskCoverage": round(area / float(WORK_SIZE[0] * WORK_SIZE[1]), 8),
        "workBbox": bbox,
        "sourceTransition": area < FRAME_MISSING_THRESHOLD,
    }
    return work_mask, diagnostics


def _load_deeplab() -> tuple[object, object, object, str]:
    """Load the pinned person-segmentation model, preferring CUDA."""
    global _DEEPLAB_CONTEXT
    if _DEEPLAB_CONTEXT is not None:
        return _DEEPLAB_CONTEXT
    try:
        import torch
        from PIL import Image
        from torchvision.models.segmentation import (
            DeepLabV3_ResNet50_Weights,
            deeplabv3_resnet50,
        )
    except ImportError as error:
        raise MatteError(
            "DeepLab segmentation requires torch, torchvision, and Pillow; "
            "refusing the less reliable colour-only fallback"
        ) from error
    try:
        weights = DeepLabV3_ResNet50_Weights.DEFAULT
        model = deeplabv3_resnet50(weights=weights).eval()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        weight_url = str(weights.url)
        cache_path = Path(torch.hub.get_dir()) / "checkpoints" / Path(weight_url).name
        if not cache_path.is_file():
            raise MatteError(f"DeepLab weight cache is missing after load: {cache_path}")
        _size, weight_hash = _sha256(cache_path)
        if weight_hash != DEEPLAB_WEIGHT_SHA256:
            raise MatteError(
                f"DeepLab weight hash mismatch: {weight_hash} != {DEEPLAB_WEIGHT_SHA256}"
            )
        _DEEPLAB_CONTEXT = (torch, Image, weights, device)
        # Keep the model attached to the context without changing the public
        # tuple shape used by the caller.
        _DEEPLAB_CONTEXT = (torch, Image, (weights, model), device)
        return _DEEPLAB_CONTEXT
    except MatteError:
        raise
    except Exception as error:
        raise MatteError(f"could not load pinned DeepLab model: {error}") from error


def _deeplab_mask(
    frame: np.ndarray,
    frame_number: int,
    previous_frame: np.ndarray | None = None,
) -> tuple[np.ndarray, dict]:
    """Segment the person class at work resolution with the pinned model."""
    torch, Image, model_context, device = _load_deeplab()
    weights, model = model_context
    resized = cv2.resize(frame, WORK_SIZE, interpolation=cv2.INTER_AREA)
    motion = 0.0 if previous_frame is None else float(cv2.absdiff(resized, previous_frame).mean())
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    tensor = weights.transforms()(Image.fromarray(rgb)).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits = model(tensor)["out"][0]
        probability = logits.softmax(dim=0)[15].detach().float().cpu().numpy()
    raw = cv2.resize(probability, WORK_SIZE, interpolation=cv2.INTER_LINEAR)
    mask = ((raw >= 0.30).astype(np.uint8) * 255)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.bitwise_and(mask, (_work_roi_mask() * 255).astype(np.uint8))
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(mask, 8)
    candidates: list[tuple[int, int]] = []
    x0, y0, x1, y1 = WORK_ROI
    for index in range(1, count):
        px, py, pw, ph, area = (int(value) for value in stats[index])
        if area < MIN_COMPONENT_AREA:
            continue
        if px + pw <= x0 or px >= x1 or py + ph <= y0 or py >= y1:
            continue
        candidates.append((area, index))
    keep = np.zeros_like(mask)
    if candidates:
        candidates.sort(reverse=True)
        largest = candidates[0][0]
        for area, index in candidates:
            if area >= max(MIN_COMPONENT_AREA, largest // 20):
                keep[labels == index] = 255
    area = int(np.count_nonzero(keep))
    ys, xs = np.where(keep > 0)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)] if len(xs) else None
    return keep, {
        "frame": frame_number,
        "workSeedPixels": area,
        "workMaskPixels": area,
        "workMaskCoverage": round(area / float(WORK_SIZE[0] * WORK_SIZE[1]), 8),
        "workBbox": bbox,
        "sourceTransition": area < FRAME_MISSING_THRESHOLD,
        "frameMotion": round(motion, 5),
        "segmentation": "deeplabv3_resnet50_person_class_15",
        "personProbabilityThreshold": 0.30,
    }


def _full_mask(work_mask: np.ndarray) -> np.ndarray:
    full = cv2.resize(work_mask, EXPECTED_SIZE, interpolation=cv2.INTER_NEAREST)
    # A one-pixel full-resolution feather removes staircase edges without
    # inventing non-black pixels outside the binary support.
    full = cv2.GaussianBlur(full, (3, 3), 0)
    return apply_hard_exclusions(full)


def _masked_frame(frame: np.ndarray, full_mask: np.ndarray) -> np.ndarray:
    alpha = full_mask.astype(np.float32) / 255.0
    return np.round(frame.astype(np.float32) * alpha[:, :, None]).astype(np.uint8)


def _ffmpeg_path() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise MatteError("ffmpeg is required to publish FFV1 matte clips")
    return path


def _open_encoder(path: Path) -> subprocess.Popen:
    command = [
        _ffmpeg_path(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-s",
        f"{EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}",
        "-r",
        "60",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "ffv1",
        "-level",
        "3",
        "-coder",
        "1",
        "-context",
        "1",
        "-g",
        "1",
        "-pix_fmt",
        "bgr24",
        str(path),
        "-y",
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _read_frame(capture: cv2.VideoCapture, expected_index: int) -> np.ndarray:
    ok, frame = capture.read()
    if not ok or frame is None:
        raise MatteError(f"could not decode source frame {expected_index}")
    if frame.shape[:2] != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]):
        raise MatteError(f"source frame {expected_index} has shape {frame.shape}")
    return frame


def _frame_report_row(frame_number: int, diagnostics: dict, full_mask: np.ndarray) -> dict:
    ys, xs = np.where(full_mask > 8)
    bbox = None
    if len(xs):
        bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    coverage = float(np.count_nonzero(full_mask > 8)) / float(EXPECTED_SIZE[0] * EXPECTED_SIZE[1])
    return {
        "frame": frame_number,
        "timeSeconds": round(frame_number / EXPECTED_FPS, 6),
        "bbox": bbox,
        "coverage": round(coverage, 8),
        "workSeedPixels": diagnostics["workSeedPixels"],
        "workMaskPixels": diagnostics["workMaskPixels"],
        "frameMotion": diagnostics.get("frameMotion"),
        "sourceTransition": bool(diagnostics["sourceTransition"]),
        "uiOverlapPixels": _ui_overlap_pixels(full_mask),
    }


def _ui_overlap_pixels(mask: np.ndarray) -> int:
    total = 0
    for _name, (x0, y0, x1, y1) in UI_RECTANGLES:
        total += int(np.count_nonzero(mask[y0:y1, x0:x1] > 8))
    return total


def _verify_clip(path: Path, expected_frames: int) -> dict:
    if not path.is_file() or path.stat().st_size <= 0:
        raise MatteError(f"encoded clip missing or empty: {path}")
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise MatteError("ffprobe is required to verify encoded matte clips")
    command = [
        ffprobe,
        "-v",
        "error",
        "-count_frames",
        "-select_streams",
        "v:0",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    try:
        raw = subprocess.check_output(command, text=True)
        stream = (json.loads(raw).get("streams") or [None])[0]
    except (OSError, subprocess.CalledProcessError, ValueError, TypeError) as error:
        raise MatteError(f"could not verify encoded clip: {error}") from error
    if not isinstance(stream, dict):
        raise MatteError("encoded clip has no video stream")
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    frames = int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0)
    fps_text = str(stream.get("avg_frame_rate") or "0/1")
    try:
        numerator, denominator = (int(part) for part in fps_text.split("/", 1))
        fps = numerator / denominator
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    if (width, height) != EXPECTED_SIZE or abs(fps - EXPECTED_FPS) > 0.01 or frames != expected_frames:
        raise MatteError(
            f"encoded clip contract mismatch: {width}x{height} {fps}fps {frames} frames; "
            f"expected {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]} {EXPECTED_FPS}fps {expected_frames}"
        )
    size, digest = _sha256(path)
    return {"bytes": size, "sha256": digest, "width": width, "height": height, "fps": fps, "frames": frames}


def _background_frame(source_path: Path) -> np.ndarray:
    capture = cv2.VideoCapture(str(source_path))
    try:
        if not capture.isOpened():
            raise MatteError(f"could not open source for background frame: {source_path}")
        if not capture.set(cv2.CAP_PROP_POS_FRAMES, BACKGROUND_FRAME):
            raise MatteError(f"could not seek background frame {BACKGROUND_FRAME}")
        return cv2.resize(_read_frame(capture, BACKGROUND_FRAME), WORK_SIZE, interpolation=cv2.INTER_AREA)
    finally:
        capture.release()


def build_actor(
    window: ActorWindow,
    source_path: Path,
    output_root: Path,
    segmentation: str = "deeplab",
) -> dict:
    background = _background_frame(source_path)
    output_root.mkdir(parents=True, exist_ok=True)
    partial = output_root / f"{window.actor}_actor_only.partial.mkv"
    clip = output_root / f"{window.actor}_actor_only.mkv"
    rows: list[dict] = []
    transition_frames: list[int] = []
    component_loss_frames: list[int] = []
    previous: np.ndarray | None = None
    previous_frame: np.ndarray | None = None
    stable_run = 0
    stable_seen = False
    capture = cv2.VideoCapture(str(source_path))
    encoder: subprocess.Popen | None = None
    try:
        if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, window.start_frame):
            raise MatteError(f"could not seek {window.actor} start frame {window.start_frame}")
        encoder = _open_encoder(partial)
        assert encoder.stdin is not None
        for frame_number in range(window.start_frame, window.end_frame_exclusive):
            frame = _read_frame(capture, frame_number)
            if segmentation == "deeplab":
                work_mask, diagnostics = _deeplab_mask(frame, frame_number, previous_frame)
            else:
                work_mask, diagnostics = _foreground_mask(frame, background, previous, frame_number)
            if segmentation == "deeplab":
                bbox = diagnostics.get("workBbox") or []
                bbox_height = int(bbox[3] - bbox[1]) if len(bbox) == 4 else 0
                stable_candidate = (
                    diagnostics["workMaskPixels"] >= FRAME_MISSING_THRESHOLD
                    and bbox_height >= 120
                    and diagnostics.get("frameMotion", 0.0) <= TRANSITION_MOTION_THRESHOLD
                )
                stable_run = stable_run + 1 if stable_candidate else 0
                if stable_run >= 3:
                    stable_seen = True
                diagnostics["sourceTransition"] = not stable_seen
            full_mask = _full_mask(work_mask)
            row = _frame_report_row(frame_number, diagnostics, full_mask)
            rows.append(row)
            if row["sourceTransition"]:
                transition_frames.append(frame_number)
            elif row["bbox"] is None or row["coverage"] <= 0.0001:
                component_loss_frames.append(frame_number)
            if row["uiOverlapPixels"] != 0:
                raise MatteError(f"frame {frame_number} has UI overlap {row['uiOverlapPixels']}")
            previous = work_mask
            previous_frame = cv2.resize(frame, WORK_SIZE, interpolation=cv2.INTER_AREA)
            try:
                encoder.stdin.write(_masked_frame(frame, full_mask).tobytes())
            except (BrokenPipeError, OSError) as error:
                raise MatteError(f"ffmpeg encoder failed on frame {frame_number}: {error}") from error
        encoder.stdin.close()
        returncode = encoder.wait()
        if returncode != 0:
            stderr = encoder.stderr.read().decode("utf-8", errors="replace") if encoder.stderr else ""
            raise MatteError(f"ffmpeg returned {returncode}: {stderr[-1000:]}")
        if component_loss_frames:
            raise MatteError(
                f"{window.actor} actor component missing on {len(component_loss_frames)} non-transition frames; "
                f"first={component_loss_frames[0]}"
            )
        os.replace(partial, clip)
    except Exception:
        if encoder is not None and encoder.poll() is None:
            try:
                encoder.kill()
            except OSError:
                pass
            try:
                encoder.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if partial.exists():
            partial.unlink()
        raise
    finally:
        capture.release()
    encoded = _verify_clip(clip, window.end_frame_exclusive - window.start_frame)
    return {
        "actor": window.actor,
        "sourceFrameRange": [window.start_frame, window.end_frame_exclusive - 1],
        "sourceTimeRangeSeconds": [window.start_seconds, window.end_seconds],
        "frameCount": len(rows),
        "fps": EXPECTED_FPS,
        "resolution": list(EXPECTED_SIZE),
        "clip": clip.relative_to(REPO_ROOT).as_posix(),
        "clipEncoding": "FFV1 lossless BGR24 black background",
        "segmentation": segmentation,
        "transitionFrameCount": len(transition_frames),
        "transitionFrameRanges": [list(item) for item in _contiguous_ranges(transition_frames)],
        "componentLossFrameCount": len(component_loss_frames),
        "uiOverlapPixels": sum(int(row["uiOverlapPixels"]) for row in rows),
        "coverage": {
            "min": min(float(row["coverage"]) for row in rows),
            "max": max(float(row["coverage"]) for row in rows),
            "mean": round(sum(float(row["coverage"]) for row in rows) / len(rows), 8),
        },
        "encoded": encoded,
        "frames": rows,
    }


def _contiguous_ranges(values: Iterable[int]) -> Iterable[tuple[int, int]]:
    ordered = sorted(set(int(value) for value in values))
    if not ordered:
        return []
    ranges: list[tuple[int, int]] = []
    first = last = ordered[0]
    for value in ordered[1:]:
        if value == last + 1:
            last = value
        else:
            ranges.append((first, last))
            first = last = value
    ranges.append((first, last))
    return ranges


def write_manifest(source: dict, actor_reports: list[dict], output_root: Path) -> Path:
    report = {
        "schema": "endfield.character-recovery.actor-matte.v1",
        "status": "ok",
        "source": source,
        "algorithm": {
            "name": "deeplabv3_resnet50_person_class_with_hard_ui_exclusions",
            "model": "torchvision.deeplabv3_resnet50",
            "modelClass": 15,
            "modelWeightsSha256": DEEPLAB_WEIGHT_SHA256,
            "workResolution": list(WORK_SIZE),
            "actorRoi": list(ACTOR_ROI),
            "uiRectangles": [{"name": name, "box": list(box)} for name, box in UI_RECTANGLES],
            "backgroundFrame": BACKGROUND_FRAME,
            "keyframeInterval": KEYFRAME_INTERVAL,
            "transitionMotionThreshold": TRANSITION_MOTION_THRESHOLD,
            "maskOutput": "black_background",
            "uiOverlapPolicy": "hard_zero_and_measured_zero",
            "transitionPolicy": "source-model-swap-empty-frames-are-retained-as-black-and-reported",
        },
        "actors": actor_reports,
        "publicationGates": {
            "sourcePin": True,
            "sourceResolutionFps": True,
            "fullFrameMask": True,
            "nonTransitionComponentLoss": sum(item["componentLossFrameCount"] for item in actor_reports) == 0,
            "uiOverlapPixels": sum(item["uiOverlapPixels"] for item in actor_reports),
            "clipsVerified": True,
        },
    }
    path = output_root / "actor_matte_manifest.json"
    temporary = path.with_suffix(".partial.json")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


def check_manifest(path: Path) -> None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MatteError(f"could not read manifest: {error}") from error
    if report.get("schema") != "endfield.character-recovery.actor-matte.v1":
        raise MatteError("unsupported actor matte manifest schema")
    if report.get("status") != "ok":
        raise MatteError(f"manifest status is not ok: {report.get('status')!r}")
    algorithm = report.get("algorithm") or {}
    if algorithm.get("name") != "deeplabv3_resnet50_person_class_with_hard_ui_exclusions":
        raise MatteError("manifest does not use the publishable DeepLab segmentation")
    if str(algorithm.get("modelWeightsSha256", "")).upper() != DEEPLAB_WEIGHT_SHA256:
        raise MatteError("manifest DeepLab weight pin mismatch")
    source = report.get("source") or {}
    if source.get("bytes") != VIDEO_BYTES or str(source.get("sha256", "")).upper() != VIDEO_SHA256:
        raise MatteError("manifest source pin mismatch")
    if report.get("publicationGates", {}).get("uiOverlapPixels") != 0:
        raise MatteError("manifest records non-zero UI overlap")
    for actor in report.get("actors") or []:
        clip = REPO_ROOT / str(actor.get("clip", ""))
        if not clip.is_file():
            raise MatteError(f"manifest clip missing: {clip}")
        size, digest = _sha256(clip)
        encoded = actor.get("encoded") or {}
        if size != encoded.get("bytes") or digest != str(encoded.get("sha256", "")).upper():
            raise MatteError(f"manifest clip hash mismatch: {clip}")
        if actor.get("uiOverlapPixels") != 0 or actor.get("componentLossFrameCount") != 0:
            raise MatteError(f"manifest actor gate failed: {actor.get('actor')}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", choices=["chen", "pelica", "all"], default="all")
    parser.add_argument("--video", type=Path, default=REPO_ROOT / VIDEO_RELATIVE)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "scratch" / "character_recovery" / "actor_clips",
    )
    parser.add_argument("--allow-source-transition-gaps", action="store_true")
    parser.add_argument(
        "--segmentation",
        choices=["deeplab", "opencv"],
        default="deeplab",
        help="segmentation engine; deeplab is the only engine allowed for publication",
    )
    parser.add_argument("--check-manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv if argv is not None else sys.argv[1:]))
    try:
        if args.check_manifest:
            check_manifest(args.check_manifest)
            print(f"actor matte manifest verified: {args.check_manifest}")
            return 0
        source = verify_source(args.video.resolve())
        actors = list(ACTOR_WINDOWS) if args.actor == "all" else [args.actor]
        reports = []
        for actor in actors:
            if args.segmentation != "deeplab":
                raise MatteError("opencv colour-only segmentation is diagnostic-only and cannot publish")
            report = build_actor(
                _actor_window(actor),
                args.video.resolve(),
                args.output_root.resolve(),
                segmentation=args.segmentation,
            )
            if report["transitionFrameCount"] and not args.allow_source_transition_gaps:
                clip_path = REPO_ROOT / report["clip"]
                if clip_path.exists():
                    clip_path.unlink()
                raise MatteError(
                    f"{actor} contains {report['transitionFrameCount']} source-transition frames; "
                    "rerun with --allow-source-transition-gaps to publish them as black"
                )
            reports.append(report)
        manifest = write_manifest(source, reports, args.output_root.resolve())
        print(f"actor matte manifest: {manifest}")
        for report in reports:
            print(
                f"{report['actor']}: frames={report['frameCount']} "
                f"transitions={report['transitionFrameCount']} "
                f"coverage={report['coverage']['min']:.6f}..{report['coverage']['max']:.6f} "
                f"clip={report['clip']}"
            )
        return 0
    except MatteError as error:
        print(f"actor matte failed closed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
