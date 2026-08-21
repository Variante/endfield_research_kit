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
they are not treated as a segmentation loss.  The only transition exemptions
are the actor-specific measured source intervals below.  Any missing component while
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
from functools import lru_cache
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
EXPECTED_SOURCE_FRAME_COUNT = 22702

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
    # The header's selection underline is visible below the filled header.
    # Its inclusive source rows are y=183..187, hence the half-open box end
    # at 188.  Keep this separate so boundary tests and reports cannot lose it.
    ("header_selection_underline", (0, 183, 3840, 188)),
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
MIN_COMPONENT_AREA = 120
KEYFRAME_INTERVAL = 4
DEEPLAB_WEIGHT_SHA256 = "CD0A25694C4A0F7106B38F4938BF90A874F2F241CC410B8F63C7024399538F06"
DEEPLAB_WEIGHT_FILENAME = "deeplabv3_resnet50_coco-cd0a2569.pth"
UNPUBLISHED_ACTOR_REASON = "retained unpublished; source or matte validation did not pass publication gates"
MANIFEST_SCHEMA = "endfield.character-recovery.actor-matte.v1"
AUDIT_REPORT_SCHEMA = "endfield.character-recovery.actor-matte.audit.v2"

# Evidence-backed source transition in the pinned recording.  The interval
# is intentionally actor-specific: it must not become a guessed Chen rule.
PELICA_SOURCE_TRANSITION_RANGE = (12560, 12601)
PELICA_STABLE_START_FRAME = 12602
PELICA_TRANSITION_REASON = (
    "pinned-source model-swap/glitch interval measured in the phase evidence; "
    "no stable Pelica actor component is present"
)
CHEN_SOURCE_TRANSITION_RANGE = (11958, 11969)
CHEN_STABLE_START_FRAME = 11970
CHEN_TRANSITION_REASON = (
    "pinned-source horizontal decode-corruption interval measured frame-by-frame "
    "through frame 11969; first clean Chen source frame is 11970"
)

# Temporal/component purity is measured at work resolution.  A small dilation
# permits ordinary sub-frame motion, while a disjoint component still fails.
TEMPORAL_DILATION_KERNEL = 9
MIN_TEMPORAL_IOU = 0.08
MIN_TEMPORAL_DILATED_SUPPORT = 0.30

_DEEPLAB_CONTEXT: tuple[object, object, object, str] | None = None


class MatteError(RuntimeError):
    """A fail-closed source, mask, or publication failure."""


def _mask_bbox(mask: np.ndarray | None) -> tuple[int, int, int, int] | None:
    if mask is None:
        return None
    ys, xs = np.where(mask > 0)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)


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


def _transition_contract(actor: str) -> tuple[tuple[int, int], int, str] | None:
    if actor == "pelica":
        return PELICA_SOURCE_TRANSITION_RANGE, PELICA_STABLE_START_FRAME, PELICA_TRANSITION_REASON
    if actor == "chen":
        return CHEN_SOURCE_TRANSITION_RANGE, CHEN_STABLE_START_FRAME, CHEN_TRANSITION_REASON
    return None


def _expected_transition_frame(actor: str, frame_number: int) -> bool:
    """Return whether a frame is covered by an evidence-backed gap rule."""
    contract = _transition_contract(actor)
    if contract is None:
        return False
    start, end = contract[0]
    return start <= frame_number <= end


def _expected_transition_frames(actor: str, window: ActorWindow) -> list[int]:
    contract = _transition_contract(actor)
    if contract is None:
        return []
    start, end = contract[0]
    return [
        frame
        for frame in range(window.start_frame, window.end_frame_exclusive)
        if start <= frame <= end
    ]


def _requested_windows_contract() -> dict:
    return {
        actor: {
            "seconds": list(ACTOR_WINDOWS[actor]),
            "framesExclusive": [_actor_window(actor).start_frame, _actor_window(actor).end_frame_exclusive],
        }
        for actor in ACTOR_WINDOWS
    }


def _excluded_actor_contract(actor_set: Iterable[str]) -> list[dict]:
    selected = set(actor_set)
    return [
        {
            "actor": actor,
            "status": "unpublished",
            "reason": UNPUBLISHED_ACTOR_REASON,
        }
        for actor in ACTOR_WINDOWS
        if actor not in selected
    ]


def _transition_policy_contract() -> dict:
    return {
        "pelicaRangeInclusive": list(PELICA_SOURCE_TRANSITION_RANGE),
        "pelicaStableStartFrame": PELICA_STABLE_START_FRAME,
        "pelicaReason": PELICA_TRANSITION_REASON,
        "chenRangeInclusive": list(CHEN_SOURCE_TRANSITION_RANGE),
        "chenStableStartFrame": CHEN_STABLE_START_FRAME,
        "chenReason": CHEN_TRANSITION_REASON,
        "actorSpecificOnly": True,
    }


def _transition_diagnostics(actor: str, frame_number: int) -> dict:
    contract = _transition_contract(actor)
    if contract is None:
        raise MatteError(f"no source-transition contract for actor {actor}")
    (start, end), _stable_start, reason = contract
    return {
        "frame": frame_number,
        "workSeedPixels": 0,
        "workMaskPixels": 0,
        "workMaskCoverage": 0.0,
        "workBbox": None,
        "sourceTransition": True,
        "transitionReason": reason,
        "transitionRangeInclusive": [start, end],
        "componentCount": 0,
        "keptComponentCount": 0,
        "detachedComponentCount": 0,
        "purityFailure": False,
        "temporalIoU": None,
        "temporalDilatedSupport": None,
        "temporalFailure": False,
    }


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest().upper()


@lru_cache(maxsize=1)
def _current_pinned_weight() -> tuple[Path, str]:
    """Resolve and hash the exact torchvision checkpoint used for publication."""
    try:
        import torch
    except ImportError as error:
        raise MatteError("cannot validate the pinned DeepLab weight file: torch is unavailable") from error
    path = Path(torch.hub.get_dir()) / "checkpoints" / DEEPLAB_WEIGHT_FILENAME
    if not path.is_file():
        raise MatteError(f"pinned DeepLab weight file is missing: {path}")
    _size, digest = _sha256(path)
    if digest != DEEPLAB_WEIGHT_SHA256:
        raise MatteError(
            f"pinned DeepLab weight file hash mismatch: {digest} != {DEEPLAB_WEIGHT_SHA256}"
        )
    return path, digest


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


def _select_person_components(
    mask: np.ndarray,
    prior: np.ndarray | None,
    future: np.ndarray | None = None,
) -> tuple[np.ndarray, dict]:
    """Select the actor support and report detached-component purity evidence.

    A connected component is retained only when it is the dominant person
    component or has current/prior/future actor-envelope evidence.  A
    substantial detached component is a hard failure; it is never silently
    turned into a black pixel or accepted as an effect/UI island.
    """
    count, labels, stats, _centres = cv2.connectedComponentsWithStats(mask, 8)
    x0, y0, x1, y1 = WORK_ROI
    candidates: list[tuple[int, int]] = []
    for index in range(1, count):
        px, py, pw, ph, area = (int(value) for value in stats[index])
        if area < MIN_COMPONENT_AREA:
            continue
        if px + pw <= x0 or px >= x1 or py + ph <= y0 or py >= y1:
            continue
        candidates.append((area, index))
    if not candidates:
        return np.zeros_like(mask), {
            "componentCount": 0,
            "keptComponentCount": 0,
            "detachedComponentCount": 0,
            "detachedComponents": [],
            "purityFailure": False,
        }

    candidates.sort(reverse=True)
    largest_area, largest_index = candidates[0]
    largest = np.where(labels == largest_index, 255, 0).astype(np.uint8)
    largest_envelope = cv2.dilate(
        largest,
        np.ones((TEMPORAL_DILATION_KERNEL, TEMPORAL_DILATION_KERNEL), np.uint8),
        iterations=1,
    )
    prior_envelope = None
    prior_bbox = _mask_bbox(prior)
    if prior is not None and np.count_nonzero(prior) > 0:
        prior_envelope = cv2.dilate(
            prior,
            np.ones((TEMPORAL_DILATION_KERNEL, TEMPORAL_DILATION_KERNEL), np.uint8),
            iterations=1,
        )
    future_envelope = None
    if future is not None and np.count_nonzero(future) > 0:
        future_envelope = cv2.dilate(
            future,
            np.ones((TEMPORAL_DILATION_KERNEL, TEMPORAL_DILATION_KERNEL), np.uint8),
            iterations=1,
        )

    keep = np.zeros_like(mask)
    keep[labels == largest_index] = 255
    detached: list[dict] = []
    kept_count = 1
    # Any component admitted by the old 1/20 rule is substantial enough to
    # audit.  Smaller specks are discarded as noise and do not become actor
    # pixels, which keeps the output fail-closed.
    substantial_floor = max(MIN_COMPONENT_AREA, largest_area // 20)
    for area, index in candidates[1:]:
        component = np.where(labels == index, 255, 0).astype(np.uint8)
        if area < substantial_floor:
            continue
        near_largest = bool(np.count_nonzero(cv2.bitwise_and(component, largest_envelope)))
        near_prior = bool(
            prior_envelope is not None
            and np.count_nonzero(cv2.bitwise_and(component, prior_envelope))
        )
        future_support = 0.0
        if future_envelope is not None:
            future_support = int(np.count_nonzero(cv2.bitwise_and(component, future_envelope))) / float(area)
        near_future = future_support >= MIN_TEMPORAL_DILATED_SUPPORT
        component_x, component_y, component_w, component_h, _ = (int(value) for value in stats[index])
        component_bbox = (
            component_x,
            component_y,
            component_x + component_w,
            component_y + component_h,
        )
        # A real limb/garment can enter the frame beside a torso component
        # without sharing pixels at this work resolution.  Bounding-box
        # intersection with the previous accepted actor envelope is a
        # temporal evidence path for that case; a detached island outside
        # both envelopes remains a hard purity failure.
        near_prior_bbox = bool(
            prior_bbox is not None
            and component_bbox[0] < prior_bbox[2]
            and component_bbox[2] > prior_bbox[0]
            and component_bbox[1] < prior_bbox[3]
            and component_bbox[3] > prior_bbox[1]
        )
        if near_largest or near_prior or near_prior_bbox or near_future:
            keep[labels == index] = 255
            kept_count += 1
            continue
        ys, xs = np.where(component > 0)
        detached.append(
            {
                "area": int(area),
                "bbox": [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)],
            }
        )

    return keep, {
        "componentCount": len(candidates),
        "keptComponentCount": kept_count,
        "detachedComponentCount": len(detached),
        "detachedComponents": detached,
        "purityFailure": bool(detached),
    }


def _temporal_metrics(mask: np.ndarray, prior: np.ndarray | None) -> dict:
    """Measure continuity against the preceding accepted actor mask."""
    if prior is None or np.count_nonzero(prior) == 0:
        return {
            "temporalIoU": None,
            "temporalDilatedSupport": None,
            "temporalFailure": False,
        }
    current = mask > 0
    previous = prior > 0
    intersection = int(np.count_nonzero(current & previous))
    union = int(np.count_nonzero(current | previous))
    iou = intersection / float(union) if union else 0.0
    dilated = cv2.dilate(
        prior,
        np.ones((TEMPORAL_DILATION_KERNEL, TEMPORAL_DILATION_KERNEL), np.uint8),
        iterations=1,
    ) > 0
    support = int(np.count_nonzero(current & dilated)) / float(np.count_nonzero(current)) if np.count_nonzero(current) else 0.0
    failure = iou < MIN_TEMPORAL_IOU and support < MIN_TEMPORAL_DILATED_SUPPORT
    return {
        "temporalIoU": round(iou, 8),
        "temporalDilatedSupport": round(support, 8),
        "temporalFailure": bool(failure),
    }


def _deeplab_raw_mask(frame: np.ndarray) -> np.ndarray:
    """Return the thresholded pinned-person candidate before component filtering."""
    torch, Image, model_context, device = _load_deeplab()
    weights, model = model_context
    resized = cv2.resize(frame, WORK_SIZE, interpolation=cv2.INTER_AREA)
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
    return mask


def _deeplab_from_raw_mask(
    mask: np.ndarray,
    frame_number: int,
    previous_mask: np.ndarray | None = None,
    future_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, dict]:
    """Apply actor component and temporal gates to a pinned-person candidate."""
    seed_pixels = int(np.count_nonzero(mask))
    keep, component_diagnostics = _select_person_components(mask, previous_mask, future_mask)
    temporal_diagnostics = _temporal_metrics(keep, previous_mask)
    area = int(np.count_nonzero(keep))
    ys, xs = np.where(keep > 0)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)] if len(xs) else None
    return keep, {
        "frame": frame_number,
        "workSeedPixels": seed_pixels,
        "workMaskPixels": area,
        "workMaskCoverage": round(area / float(WORK_SIZE[0] * WORK_SIZE[1]), 8),
        "workBbox": bbox,
        "sourceTransition": False,
        "segmentation": "deeplabv3_resnet50_person_class_15",
        "personProbabilityThreshold": 0.30,
        **component_diagnostics,
        **temporal_diagnostics,
    }


def _deeplab_mask(
    frame: np.ndarray,
    frame_number: int,
    previous_mask: np.ndarray | None = None,
    future_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, dict]:
    """Segment the person class at work resolution with the pinned model."""
    raw_mask = _deeplab_raw_mask(frame)
    work_mask, diagnostics = _deeplab_from_raw_mask(
        raw_mask,
        frame_number,
        previous_mask,
        future_mask,
    )
    # Kept internal for a one-frame look-ahead retry when a component first
    # enters from an image boundary.  It is removed before JSON row creation.
    diagnostics["_rawMask"] = raw_mask
    return work_mask, diagnostics


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
        # Pin the encoded stream rate as well as the raw input cadence.
        "-r",
        "60",
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
        "sourceTransition": bool(diagnostics["sourceTransition"]),
        "transitionReason": diagnostics.get("transitionReason"),
        "transitionRangeInclusive": diagnostics.get("transitionRangeInclusive"),
        "componentCount": diagnostics.get("componentCount", 0),
        "keptComponentCount": diagnostics.get("keptComponentCount", 0),
        "detachedComponentCount": diagnostics.get("detachedComponentCount", 0),
        "purityFailure": bool(diagnostics.get("purityFailure", False)),
        "temporalIoU": diagnostics.get("temporalIoU"),
        "temporalDilatedSupport": diagnostics.get("temporalDilatedSupport"),
        "temporalFailure": bool(diagnostics.get("temporalFailure", False)),
        "uiOverlapPixels": _ui_overlap_pixels(full_mask),
    }


def _ui_overlap_pixels(mask: np.ndarray) -> int:
    total = 0
    for _name, (x0, y0, x1, y1) in UI_RECTANGLES:
        total += int(np.count_nonzero(mask[y0:y1, x0:x1] > 8))
    return total


def _parse_fps(text: object) -> float:
    fps_text = str(text or "0/1")
    try:
        numerator, denominator = (int(part) for part in fps_text.split("/", 1))
        return numerator / denominator
    except (ValueError, ZeroDivisionError):
        return 0.0


def _duration_seconds(metadata: dict) -> float:
    value = metadata.get("duration")
    try:
        if value is not None and float(value) > 0:
            return float(value)
    except (TypeError, ValueError):
        pass
    tags = metadata.get("tags") or {}
    tagged = str(tags.get("DURATION") or tags.get("duration") or "")
    parts = tagged.split(":")
    if len(parts) == 3:
        try:
            hours, minutes, seconds = parts
            return float(hours) * 3600.0 + float(minutes) * 60.0 + float(seconds)
        except ValueError:
            pass
    return 0.0


def _validate_encoded_metadata(metadata: dict, expected_frames: int) -> dict:
    """Validate the actual FFV1 stream contract and return normalized facts."""
    codec = str(metadata.get("codec_name") or metadata.get("codec") or "").lower()
    pix_fmt = str(metadata.get("pix_fmt") or "").lower()
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    frames = int(metadata.get("nb_read_frames") or metadata.get("nb_frames") or metadata.get("frames") or 0)
    avg_rate = _parse_fps(metadata.get("avg_frame_rate") or "0/1")
    real_rate = _parse_fps(metadata.get("r_frame_rate") or "0/1")
    # Some FFV1 Matroska streams expose avg_frame_rate=0/0 while the actual
    # constant stream rate is unambiguously present as r_frame_rate=60/1.
    # Reject only when both probes fail; never turn a missing rate into 60 by
    # assumption.
    fps = avg_rate if avg_rate > 0 else real_rate
    fps_evidence = "avg_frame_rate" if avg_rate > 0 else "r_frame_rate"
    if fps <= 0:
        fps = _parse_fps(metadata.get("fps") or "0/1")
        fps_evidence = "fps"
    duration = _duration_seconds(metadata)
    if fps <= 0 and duration > 0 and frames > 0:
        fps = frames / duration
        fps_evidence = "frame_count_over_duration"
    if codec != "ffv1" or pix_fmt != "bgr0":
        raise MatteError(
            f"encoded clip is not the verified FFV1/BGR0 contract: codec={codec!r} pix_fmt={pix_fmt!r}"
        )
    if (width, height) != EXPECTED_SIZE or abs(fps - EXPECTED_FPS) > 0.01 or frames != expected_frames:
        raise MatteError(
            f"encoded clip contract mismatch: {width}x{height} {fps}fps {frames} frames; "
            f"expected {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]} {EXPECTED_FPS}fps {expected_frames}"
        )
    return {
        "codec": codec,
        "pix_fmt": pix_fmt,
        "width": width,
        "height": height,
        "fps": fps,
        "avgFrameRate": str(metadata.get("avg_frame_rate") or ""),
        "rFrameRate": str(metadata.get("r_frame_rate") or ""),
        "duration": duration,
        "fpsEvidence": fps_evidence,
        "frames": frames,
    }


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
    normalized = _validate_encoded_metadata(stream, expected_frames)
    size, digest = _sha256(path)
    return {"bytes": size, "sha256": digest, **normalized}


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
    temporal_failure_frames: list[int] = []
    purity_failure_frames: list[int] = []
    previous_mask: np.ndarray | None = None
    pending_frame: np.ndarray | None = None
    capture = cv2.VideoCapture(str(source_path))
    encoder: subprocess.Popen | None = None
    try:
        if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, window.start_frame):
            raise MatteError(f"could not seek {window.actor} start frame {window.start_frame}")
        encoder = _open_encoder(partial)
        assert encoder.stdin is not None
        for frame_number in range(window.start_frame, window.end_frame_exclusive):
            if pending_frame is not None:
                frame = pending_frame
                pending_frame = None
            else:
                frame = _read_frame(capture, frame_number)
            if _expected_transition_frame(window.actor, frame_number):
                # Do not ask the segmenter to explain a measured source glitch.
                # The intentional black gap is itself evidence and is recorded
                # exactly in every affected row and in the actor manifest.
                work_mask = np.zeros((WORK_SIZE[1], WORK_SIZE[0]), np.uint8)
                diagnostics = _transition_diagnostics(window.actor, frame_number)
            else:
                if segmentation == "deeplab":
                    work_mask, diagnostics = _deeplab_mask(frame, frame_number, previous_mask)
                else:
                    work_mask, diagnostics = _foreground_mask(frame, background, previous_mask, frame_number)
                if diagnostics.get("purityFailure"):
                    raw_mask = diagnostics.pop("_rawMask", None)
                    if (
                        segmentation == "deeplab"
                        and raw_mask is not None
                        and frame_number + 1 < window.end_frame_exclusive
                    ):
                        # A real garment/limb can first appear at an image
                        # boundary with no preceding-pixel overlap.  Decode
                        # and segment exactly one next source frame; only a
                        # component with future temporal support is retained.
                        pending_frame = _read_frame(capture, frame_number + 1)
                        future_raw = _deeplab_raw_mask(pending_frame)
                        work_mask, diagnostics = _deeplab_from_raw_mask(
                            raw_mask,
                            frame_number,
                            previous_mask,
                            future_raw,
                        )
                    if diagnostics.get("purityFailure"):
                        purity_failure_frames.append(frame_number)
                        raise MatteError(
                            f"{window.actor} detached non-actor component at frame {frame_number}: "
                            f"{diagnostics.get('detachedComponentCount')} components"
                        )
                if diagnostics.get("temporalFailure"):
                    temporal_failure_frames.append(frame_number)
                    raise MatteError(
                        f"{window.actor} temporal mask continuity failed at frame {frame_number}: "
                        f"IoU={diagnostics.get('temporalIoU')} "
                        f"dilatedSupport={diagnostics.get('temporalDilatedSupport')}"
                    )
                # DeepLab's selected connected component is the actor evidence;
                # do not turn a low-area but temporally continuous motion pose
                # into a guessed source transition.  A zero selected component
                # is the only non-transition loss accepted by this gate.
                if diagnostics.get("workMaskPixels", 0) <= 0:
                    component_loss_frames.append(frame_number)
                    raise MatteError(
                        f"{window.actor} actor component missing at stable frame {frame_number}"
                    )
            diagnostics.pop("_rawMask", None)
            full_mask = _full_mask(work_mask)
            row = _frame_report_row(frame_number, diagnostics, full_mask)
            rows.append(row)
            if row["sourceTransition"]:
                transition_frames.append(frame_number)
            elif row["bbox"] is None or row["coverage"] <= 0.0001:
                component_loss_frames.append(frame_number)
            if row["uiOverlapPixels"] != 0:
                raise MatteError(f"frame {frame_number} has UI overlap {row['uiOverlapPixels']}")
            if not row["sourceTransition"]:
                if row["bbox"] is None or row["coverage"] <= 0.0001:
                    component_loss_frames.append(frame_number)
                    raise MatteError(f"{window.actor} full-frame matte missing at frame {frame_number}")
                previous_mask = work_mask
            try:
                encoder.stdin.write(_masked_frame(frame, full_mask).tobytes())
            except (BrokenPipeError, OSError) as error:
                raise MatteError(f"ffmpeg encoder failed on frame {frame_number}: {error}") from error
        encoder.stdin.close()
        returncode = encoder.wait()
        if returncode != 0:
            stderr = encoder.stderr.read().decode("utf-8", errors="replace") if encoder.stderr else ""
            raise MatteError(f"ffmpeg returned {returncode}: {stderr[-1000:]}")
        expected_transitions = _expected_transition_frames(window.actor, window)
        if transition_frames != expected_transitions:
            raise MatteError(
                f"{window.actor} transition classification mismatch: "
                f"actual={transition_frames[:3]}..{transition_frames[-3:]} expected="
                f"{expected_transitions[:3]}..{expected_transitions[-3:]}"
            )
        transition_contract = _transition_contract(window.actor)
        if transition_contract is not None and transition_contract[1] < window.end_frame_exclusive:
            first_stable = next(
                (row for row in rows if row["frame"] >= transition_contract[1]),
                None,
            )
            if first_stable is None or first_stable["sourceTransition"]:
                raise MatteError(
                    f"{window.actor} stable actor gate did not start at frame {transition_contract[1]}"
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
    try:
        encoded = _verify_clip(clip, window.end_frame_exclusive - window.start_frame)
    except Exception:
        if clip.exists():
            clip.unlink()
        raise
    return {
        "actor": window.actor,
        "sourceFrameRange": [window.start_frame, window.end_frame_exclusive - 1],
        "sourceTimeRangeSeconds": [window.start_seconds, window.end_seconds],
        "frameCount": len(rows),
        "fps": EXPECTED_FPS,
        "resolution": list(EXPECTED_SIZE),
        "clip": _repo_relative_path(clip, f"{window.actor} clip"),
        "clipEncoding": "FFV1 lossless actual pix_fmt=bgr0 black background",
        "segmentation": segmentation,
        "transitionFrameCount": len(transition_frames),
        "transitionFrameRanges": [list(item) for item in _contiguous_ranges(transition_frames)],
        "transitionReason": _transition_contract(window.actor)[2] if transition_frames else None,
        "transitionRangeInclusive": list(_transition_contract(window.actor)[0]) if transition_frames else None,
        "componentLossFrameCount": len(component_loss_frames),
        "temporalContinuityFailureCount": len(temporal_failure_frames),
        "componentPurityFailureCount": len(purity_failure_frames),
        "rowsContiguous": [row["frame"] for row in rows] == list(range(window.start_frame, window.end_frame_exclusive)),
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


def _validate_contiguous_frame_rows(rows: object, start_frame: int, end_frame_exclusive: int, actor: str) -> None:
    if not isinstance(rows, list):
        raise MatteError(f"{actor} frame rows are missing")
    expected = list(range(start_frame, end_frame_exclusive))
    actual = [row.get("frame") if isinstance(row, dict) else None for row in rows]
    if actual != expected:
        raise MatteError(f"{actor} frame rows are discontinuous or incomplete")


def _repo_relative_path(path: Path, label: str) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as error:
        raise MatteError(f"{label} must be inside the repository: {path}") from error
    return relative.as_posix()


def _resolve_repo_relative(value: object, label: str) -> Path:
    text = str(value or "")
    candidate = Path(text)
    if not text or candidate.is_absolute():
        raise MatteError(f"{label} must be a repo-relative path: {text!r}")
    resolved = (REPO_ROOT / candidate).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as error:
        raise MatteError(f"{label} escapes the repository: {text!r}") from error
    return resolved


def _manifest_publication_gates(actor_reports: list[dict]) -> dict:
    return {
        "sourcePin": True,
        "sourceResolutionFps": True,
        "fullFrameMask": all(bool(item.get("rowsContiguous")) for item in actor_reports),
        "exactTransitionClassification": all(
            item.get("transitionFrameRanges")
            == [list(item_range) for item_range in _contiguous_ranges(
                _expected_transition_frames(item["actor"], _actor_window(item["actor"]))
            )]
            for item in actor_reports
        ),
        "temporalContinuity": sum(item.get("temporalContinuityFailureCount", 0) for item in actor_reports) == 0,
        "componentPurity": sum(item.get("componentPurityFailureCount", 0) for item in actor_reports) == 0,
        "nonTransitionComponentLoss": sum(item.get("componentLossFrameCount", 0) for item in actor_reports) == 0,
        "rowsContiguous": all(bool(item.get("rowsContiguous")) for item in actor_reports),
        "uiExclusionZero": sum(item.get("uiOverlapPixels", 0) for item in actor_reports) == 0,
        "uiOverlapPixels": sum(item.get("uiOverlapPixels", 0) for item in actor_reports),
        "ffv1Metadata": all(
            (item.get("encoded") or {}).get("codec") == "ffv1"
            and (item.get("encoded") or {}).get("pix_fmt") == "bgr0"
            for item in actor_reports
        ),
        "clipsVerified": all(bool(item.get("encoded")) for item in actor_reports),
    }


def write_manifest(source: dict, actor_reports: list[dict], output_root: Path) -> Path:
    if not actor_reports:
        raise MatteError("refusing to write an empty actor matte manifest")
    for item in actor_reports:
        clip = _resolve_repo_relative(item.get("clip"), f"{item.get('actor')} clip")
        if not clip.is_file():
            raise MatteError(f"manifest clip missing before publication: {clip}")
    gates = _manifest_publication_gates(actor_reports)
    if not all(value is True for key, value in gates.items() if key != "uiOverlapPixels") or gates["uiOverlapPixels"] != 0:
        raise MatteError(f"actor matte publication gates failed: {gates}")
    report = {
        "schema": MANIFEST_SCHEMA,
        "status": "ok",
        "pathBase": "repo_root",
        "source": source,
        "algorithm": {
            "name": "deeplabv3_resnet50_person_class_with_hard_ui_exclusions",
            "model": "torchvision.deeplabv3_resnet50",
            "modelClass": 15,
            "modelWeightsFile": DEEPLAB_WEIGHT_FILENAME,
            "modelWeightsSha256": DEEPLAB_WEIGHT_SHA256,
            "workResolution": list(WORK_SIZE),
            "actorRoi": list(ACTOR_ROI),
            "uiRectangles": [{"name": name, "box": list(box)} for name, box in UI_RECTANGLES],
            "backgroundFrame": BACKGROUND_FRAME,
            "keyframeInterval": KEYFRAME_INTERVAL,
            "maskOutput": "black_background",
            "outputCodec": "ffv1",
            "outputPixFmt": "bgr0",
            "uiOverlapPolicy": "hard_zero_and_measured_zero",
            "temporalPolicy": {
                "minRawIoU": MIN_TEMPORAL_IOU,
                "minDilatedSupport": MIN_TEMPORAL_DILATED_SUPPORT,
                "dilationKernel": TEMPORAL_DILATION_KERNEL,
                "detachedComponents": "reject_substantial_component_without_current_previous_or_next_actor_envelope_overlap",
            },
            "transitionPolicy": _transition_policy_contract(),
        },
        "actorSet": sorted(item["actor"] for item in actor_reports),
        "requestedWindows": _requested_windows_contract(),
        "actors": actor_reports,
        "excludedActors": _excluded_actor_contract(item["actor"] for item in actor_reports),
        "publicationGates": gates,
    }
    path = output_root / "actor_matte_manifest.json"
    temporary = path.with_suffix(".partial.json")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return path


def write_durable_report(
    manifest_path: Path,
    source: dict,
    actor_reports: list[dict],
    report_path: Path | None = None,
) -> Path:
    """Write the tracked audit report from the just-verified manifest/output."""
    report_path = report_path or PROJECT_ROOT / "tools" / "actor_matte_report.json"
    manifest_relative = _repo_relative_path(manifest_path, "manifest")
    manifest_size, manifest_hash = _sha256(manifest_path)
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = []
    for item in actor_reports:
        clip = _resolve_repo_relative(item["clip"], f"{item['actor']} clip")
        size, digest = _sha256(clip)
        artifacts.append(
            {
                "actor": item["actor"],
                "path": _repo_relative_path(clip, f"{item['actor']} clip"),
                "bytes": size,
                "sha256": digest,
                "codec": item["encoded"]["codec"],
                "pix_fmt": item["encoded"]["pix_fmt"],
                "frames": item["encoded"]["frames"],
            }
        )
    report = {
        "schema": AUDIT_REPORT_SCHEMA,
        "status": "ok",
        "pathBase": "repo_root",
        "generatedBy": "unity_endfield_graph_shader_lab/tools/build_priority_actor_mattes.py",
        "manifest": manifest_relative,
        "manifestBytes": manifest_size,
        "manifestSha256": manifest_hash,
        "source": source,
        "requestedWindows": _requested_windows_contract(),
        "algorithm": manifest_data["algorithm"],
        "actorSet": sorted(item["actor"] for item in actor_reports),
        "artifacts": artifacts,
        "excludedActors": manifest_data["excludedActors"],
        "publicationGates": manifest_data["publicationGates"],
        "validation": {
            "rows": {item["actor"]: item["frameCount"] for item in actor_reports},
            "publishedClips": len(artifacts),
            "largeVideoFilesCommitted": False,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(".partial.json")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, report_path)
    return report_path


def _check_manifest_data(report: dict, manifest_path: Path) -> None:
    if report.get("schema") != MANIFEST_SCHEMA:
        raise MatteError("unsupported actor matte manifest schema")
    if report.get("status") != "ok":
        raise MatteError(f"manifest status is not ok: {report.get('status')!r}")
    if report.get("pathBase") != "repo_root":
        raise MatteError("manifest pathBase must be repo_root")
    algorithm = report.get("algorithm") or {}
    if algorithm.get("name") != "deeplabv3_resnet50_person_class_with_hard_ui_exclusions":
        raise MatteError("manifest does not use the publishable DeepLab segmentation")
    if algorithm.get("modelWeightsFile") != DEEPLAB_WEIGHT_FILENAME:
        raise MatteError("manifest DeepLab weight filename pin mismatch")
    if str(algorithm.get("modelWeightsSha256", "")).upper() != DEEPLAB_WEIGHT_SHA256:
        raise MatteError("manifest DeepLab weight pin mismatch")
    _current_pinned_weight()
    if algorithm.get("transitionPolicy") != _transition_policy_contract():
        raise MatteError("manifest transition policy is stale or not actor-specific")
    source = report.get("source") or {}
    if source.get("path") != VIDEO_RELATIVE.as_posix():
        raise MatteError(f"manifest source path is stale: {source.get('path')!r}")
    if source.get("bytes") != VIDEO_BYTES or str(source.get("sha256", "")).upper() != VIDEO_SHA256:
        raise MatteError("manifest source pin mismatch")
    if source.get("width") != EXPECTED_SIZE[0] or source.get("height") != EXPECTED_SIZE[1] or abs(float(source.get("fps", 0)) - EXPECTED_FPS) > 0.01 or source.get("frameCount") != EXPECTED_SOURCE_FRAME_COUNT:
        raise MatteError("manifest source resolution/fps mismatch")
    source_path = _resolve_repo_relative(source["path"], "manifest source")
    if not source_path.is_file():
        raise MatteError(f"manifest source missing: {source_path}")
    actual_size, actual_hash = _sha256(source_path)
    if actual_size != VIDEO_BYTES or actual_hash != VIDEO_SHA256:
        raise MatteError("actual source hash does not match the pinned source")

    actor_reports = report.get("actors")
    if not isinstance(actor_reports, list) or not actor_reports:
        raise MatteError("manifest has no actor reports")
    actor_names = [str(item.get("actor")) for item in actor_reports]
    if len(set(actor_names)) != len(actor_names) or any(name not in ACTOR_WINDOWS for name in actor_names):
        raise MatteError(f"manifest actor set is invalid: {actor_names}")
    if sorted(actor_names) != report.get("actorSet"):
        raise MatteError("manifest actorSet does not match actors")

    for actor in actor_reports:
        name = actor["actor"]
        window = _actor_window(name)
        expected_frames = list(range(window.start_frame, window.end_frame_exclusive))
        if actor.get("sourceFrameRange") != [window.start_frame, window.end_frame_exclusive - 1]:
            raise MatteError(f"{name} source frame range is not exact")
        rows = actor.get("frames")
        _validate_contiguous_frame_rows(rows, window.start_frame, window.end_frame_exclusive, name)
        expected_transition = _expected_transition_frames(name, window)
        actual_transition = [row["frame"] for row in rows if row.get("sourceTransition")]
        if actual_transition != expected_transition:
            raise MatteError(f"{name} transition timing is not evidence-backed")
        expected_ranges = [list(item) for item in _contiguous_ranges(expected_transition)]
        if actor.get("transitionFrameRanges") != expected_ranges:
            raise MatteError(f"{name} transition ranges are not contiguous/exact")
        transition_contract = _transition_contract(name)
        for row in rows:
            if row.get("uiOverlapPixels") != 0:
                raise MatteError(f"{name} frame {row.get('frame')} has UI overlap")
            if row.get("sourceTransition"):
                assert transition_contract is not None
                if row.get("transitionReason") != transition_contract[2] or row.get("transitionRangeInclusive") != list(transition_contract[0]):
                    raise MatteError(f"{name} transition row lacks exact reason/range")
                if row.get("bbox") is not None or float(row.get("coverage", 0)) != 0.0:
                    raise MatteError(f"{name} transition row is not an intentional black gap")
            else:
                if row.get("bbox") is None or float(row.get("coverage", 0)) <= 0.0001:
                    raise MatteError(f"{name} has a non-transition full-frame mask loss")
                if row.get("purityFailure") or row.get("temporalFailure") or row.get("detachedComponentCount", 0) != 0:
                    raise MatteError(f"{name} has component/temporal purity failure")
        if actor.get("frameCount") != len(expected_frames) or not actor.get("rowsContiguous"):
            raise MatteError(f"{name} frame count/contiguity gate failed")
        if actor.get("componentLossFrameCount") != 0 or actor.get("temporalContinuityFailureCount") != 0 or actor.get("componentPurityFailureCount") != 0:
            raise MatteError(f"{name} actor purity gate failed")
        if actor.get("uiOverlapPixels") != 0:
            raise MatteError(f"{name} records non-zero UI overlap")
        clip = _resolve_repo_relative(actor.get("clip"), f"{name} clip")
        if not clip.is_file():
            raise MatteError(f"manifest clip missing: {clip}")
        encoded = actor.get("encoded") or {}
        _validate_encoded_metadata(encoded, len(expected_frames))
        size, digest = _sha256(clip)
        if size != encoded.get("bytes") or digest != str(encoded.get("sha256", "")).upper():
            raise MatteError(f"manifest clip hash mismatch: {clip}")

    gates = report.get("publicationGates") or {}
    required_boolean_gates = [
        "sourcePin", "sourceResolutionFps", "fullFrameMask", "exactTransitionClassification",
        "temporalContinuity", "componentPurity", "nonTransitionComponentLoss", "rowsContiguous",
        "uiExclusionZero", "ffv1Metadata", "clipsVerified",
    ]
    if any(gates.get(key) is not True for key in required_boolean_gates) or gates.get("uiOverlapPixels") != 0:
        raise MatteError(f"manifest publication gates failed: {gates}")


def _check_audit_report(report: dict, report_path: Path) -> None:
    if report.get("schema") != AUDIT_REPORT_SCHEMA:
        raise MatteError("unsupported actor matte audit report schema")
    if report.get("status") != "ok":
        raise MatteError(f"audit report status is not ok: {report.get('status')!r}")
    if report.get("pathBase") != "repo_root":
        raise MatteError("audit report pathBase must be repo_root")
    manifest_path = _resolve_repo_relative(report.get("manifest"), "audit manifest")
    if not manifest_path.is_file():
        raise MatteError(f"audit manifest missing: {manifest_path}")
    manifest_size, manifest_hash = _sha256(manifest_path)
    if manifest_size != report.get("manifestBytes") or manifest_hash != str(report.get("manifestSha256", "")).upper():
        raise MatteError("audit manifest hash mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MatteError(f"could not read audit manifest: {error}") from error
    _check_manifest_data(manifest, manifest_path)
    expected_source = {
        "path": VIDEO_RELATIVE.as_posix(),
        "bytes": VIDEO_BYTES,
        "sha256": VIDEO_SHA256,
        "width": EXPECTED_SIZE[0],
        "height": EXPECTED_SIZE[1],
        "fps": EXPECTED_FPS,
        "frameCount": EXPECTED_SOURCE_FRAME_COUNT,
    }
    if manifest.get("source") != expected_source:
        raise MatteError("manifest source fields do not match the pinned source contract")
    if report.get("source") != manifest.get("source") or report.get("source") != expected_source:
        raise MatteError("audit report source fields do not match manifest/constants")

    manifest_algorithm = manifest.get("algorithm") or {}
    report_algorithm = report.get("algorithm") or {}
    if report_algorithm != manifest_algorithm:
        raise MatteError("audit algorithm does not match manifest")
    if report_algorithm.get("name") != "deeplabv3_resnet50_person_class_with_hard_ui_exclusions":
        raise MatteError("audit algorithm name is not the publishable matte algorithm")
    if report_algorithm.get("modelWeightsFile") != DEEPLAB_WEIGHT_FILENAME:
        raise MatteError("audit model weight filename does not match the pinned checkpoint")
    if str(report_algorithm.get("modelWeightsSha256", "")).upper() != DEEPLAB_WEIGHT_SHA256:
        raise MatteError("audit model weight hash does not match the manifest/constants")
    _weight_path, current_weight_hash = _current_pinned_weight()
    if current_weight_hash != str(report_algorithm.get("modelWeightsSha256", "")).upper():
        raise MatteError("audit model weight hash does not match the current pinned weight file")

    expected_windows = _requested_windows_contract()
    if manifest.get("requestedWindows") != expected_windows:
        raise MatteError("manifest requestedWindows do not match the actor policy")
    if report.get("requestedWindows") != manifest.get("requestedWindows"):
        raise MatteError("audit requestedWindows do not match the manifest")

    if report.get("actorSet") != manifest.get("actorSet"):
        raise MatteError("audit actorSet does not match manifest")
    expected_excluded = _excluded_actor_contract(manifest.get("actorSet") or [])
    if manifest.get("excludedActors") != expected_excluded:
        raise MatteError("manifest excludedActors do not match the actor publication policy")
    if report.get("excludedActors") != manifest.get("excludedActors"):
        raise MatteError("audit excludedActors do not match the manifest")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or sorted(item.get("actor") for item in artifacts) != sorted(report.get("actorSet") or []):
        raise MatteError("audit artifacts do not match actor set")
    manifest_actors = {item["actor"]: item for item in manifest["actors"]}
    for artifact in artifacts:
        actor = artifact.get("actor")
        if actor not in manifest_actors:
            raise MatteError(f"audit artifact actor is absent from manifest: {actor}")
        if artifact.get("path") != manifest_actors[actor].get("clip"):
            raise MatteError(f"audit artifact path does not match manifest for {actor}")
        manifest_encoded = manifest_actors[actor].get("encoded") or {}
        for field, manifest_field in (
            ("bytes", "bytes"),
            ("sha256", "sha256"),
            ("codec", "codec"),
            ("pix_fmt", "pix_fmt"),
            ("frames", "frames"),
        ):
            actual = artifact.get(field)
            expected = manifest_encoded.get(manifest_field)
            if field == "sha256":
                actual = str(actual or "").upper()
                expected = str(expected or "").upper()
            if actual != expected:
                raise MatteError(f"audit artifact {field} does not match manifest for {actor}")
        clip = _resolve_repo_relative(artifact.get("path"), f"audit {actor} clip")
        size, digest = _sha256(clip)
        if size != artifact.get("bytes") or digest != str(artifact.get("sha256", "")).upper():
            raise MatteError(f"audit artifact hash mismatch for {actor}")
    validation = report.get("validation") or {}
    expected_rows = {item["actor"]: item["frameCount"] for item in manifest["actors"]}
    if validation.get("rows") != expected_rows or validation.get("publishedClips") != len(artifacts) or validation.get("largeVideoFilesCommitted") is not False:
        raise MatteError("audit validation summary does not match the manifest/artifacts")
    if report.get("publicationGates") != manifest.get("publicationGates"):
        raise MatteError("audit publication gates do not match manifest")


def _refresh_existing_report(manifest_path: Path, report_path: Path) -> Path:
    """Re-emit contract metadata/report without decoding or encoding video."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MatteError(f"could not read existing actor matte manifest: {error}") from error
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise MatteError("existing actor matte manifest has an unsupported schema")
    manifest["requestedWindows"] = _requested_windows_contract()
    algorithm = manifest.get("algorithm")
    if not isinstance(algorithm, dict):
        raise MatteError("existing actor matte manifest has no algorithm object")
    algorithm["modelWeightsFile"] = DEEPLAB_WEIGHT_FILENAME
    algorithm["transitionPolicy"] = _transition_policy_contract()
    actor_set = manifest.get("actorSet") or [item.get("actor") for item in manifest.get("actors") or []]
    manifest["actorSet"] = sorted(str(actor) for actor in actor_set)
    manifest["excludedActors"] = _excluded_actor_contract(manifest["actorSet"])
    temporary = manifest_path.with_suffix(".refresh.partial.json")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    _check_manifest_data(manifest, manifest_path)
    durable_report = write_durable_report(
        manifest_path,
        manifest["source"],
        manifest["actors"],
        report_path,
    )
    check_manifest(durable_report)
    return durable_report


def _preserved_actor_reports(manifest_path: Path, selected_actors: set[str]) -> list[dict]:
    """Load already-published actors for a single-actor regeneration.

    The existing manifest is fully checked before its rows are merged.  This
    makes ``--actor chen`` safe to run without touching the active Pelica
    clip, while still refusing to carry forward stale or unpublished data.
    """
    if not manifest_path.is_file():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MatteError(f"could not read existing actor matte manifest: {error}") from error
    _check_manifest_data(manifest, manifest_path)
    actors = manifest.get("actors")
    if not isinstance(actors, list):
        raise MatteError("existing actor matte manifest has no actor rows")
    return [item for item in actors if str(item.get("actor")) not in selected_actors]


def check_manifest(path: Path) -> None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MatteError(f"could not read manifest/report: {error}") from error
    schema = report.get("schema")
    if schema == AUDIT_REPORT_SCHEMA:
        _check_audit_report(report, path)
    else:
        _check_manifest_data(report, path)


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
    parser.add_argument(
        "--check-manifest",
        type=Path,
        help="verify a generated actor_matte_manifest.json or actor_matte_report.json",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=PROJECT_ROOT / "tools" / "actor_matte_report.json",
        help="tracked durable audit report path (written only after all gates pass)",
    )
    parser.add_argument(
        "--refresh-report",
        type=Path,
        help="rebuild manifest/report contract metadata from existing clips without re-encoding video",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv if argv is not None else sys.argv[1:]))
    try:
        if args.check_manifest:
            check_manifest(args.check_manifest)
            print(f"actor matte manifest verified: {args.check_manifest}")
            return 0
        if args.refresh_report:
            durable_report = _refresh_existing_report(
                args.refresh_report.resolve(),
                args.report_path.resolve(),
            )
            print(f"actor matte durable report refreshed: {durable_report}")
            return 0
        source = verify_source(args.video.resolve())
        actors = list(ACTOR_WINDOWS) if args.actor == "all" else [args.actor]
        output_root = args.output_root.resolve()
        preserved_reports = []
        if args.actor != "all":
            preserved_reports = _preserved_actor_reports(
                output_root / "actor_matte_manifest.json",
                set(actors),
            )
        reports = list(preserved_reports)
        built_clips: list[Path] = []
        for actor in actors:
            if args.segmentation != "deeplab":
                raise MatteError("opencv colour-only segmentation is diagnostic-only and cannot publish")
            report = build_actor(
                _actor_window(actor),
                args.video.resolve(),
                output_root,
                segmentation=args.segmentation,
            )
            built_clips.append(REPO_ROOT / report["clip"])
            if report["transitionFrameCount"] and not args.allow_source_transition_gaps:
                clip_path = REPO_ROOT / report["clip"]
                if clip_path.exists():
                    clip_path.unlink()
                raise MatteError(
                    f"{actor} contains {report['transitionFrameCount']} source-transition frames; "
                    "rerun with --allow-source-transition-gaps to publish them as black"
                )
            reports.append(report)
        manifest = write_manifest(source, reports, output_root)
        durable_report = write_durable_report(
            manifest,
            source,
            reports,
            args.report_path.resolve(),
        )
        check_manifest(durable_report)
        print(f"actor matte manifest: {manifest}")
        print(f"actor matte durable report: {durable_report}")
        for report in reports:
            print(
                f"{report['actor']}: frames={report['frameCount']} "
                f"transitions={report['transitionFrameCount']} "
                f"coverage={report['coverage']['min']:.6f}..{report['coverage']['max']:.6f} "
                f"clip={report['clip']}"
            )
        return 0
    except MatteError as error:
        # Never leave a newly generated active clip behind when a later
        # publication gate fails.  Existing *.unpublished.mkv evidence is not
        # touched and remains explicitly unpublished.
        for clip in locals().get("built_clips", []):
            try:
                if clip.exists():
                    clip.unlink()
            except OSError:
                pass
        print(f"actor matte failed closed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
