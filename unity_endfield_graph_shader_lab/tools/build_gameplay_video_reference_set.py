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
import shutil
import subprocess
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
VIDEO_SEGMENTS_MANIFEST_NAME = "gameplay_video_segments.json"
BOUNDARY_MANIFEST_NAME = "video_segment_boundaries.json"
BOUNDARY_ROOT = os.path.join(
    PROJECT_ROOT, "scratch", "character_recovery", "gameplay_reference"
)
DEFAULT_BOUNDARY_MANIFEST = os.path.join(BOUNDARY_ROOT, BOUNDARY_MANIFEST_NAME)

# Left stat/name panel. Constant within a character, changes on switch.
PANEL_BOX = (60, 300, 820, 1300)
PANEL_SIGNATURE_SIZE = (76, 100)
PANEL_CHANGE_THRESHOLD = 3.0

# Name plate inside the detail view.
NAME_BOX = (150, 420, 1200, 660)

SAMPLE_HZ = 2.0
MINIMUM_SEGMENT_SAMPLES = 6  # about three seconds; shorter spans are transitions
EXPECTED_RESOLUTION = (3840, 2160)

# This is the validated central character band used by
# refine_gameplay_video_boundaries.py. It excludes the left/right foreground UI
# while retaining the full character from head to feet.
CHARACTER_BAND_BOX = (1400, 200, 2500, 2100)
KNOWN_UNRESOLVED_ACTORS = {
    "endmin": "endmin identity is ambiguous: no prefab/gender evidence is present",
    "endminf": "endminf cannot be selected without explicit prefab/gender evidence",
    "endminm": "endminm cannot be selected without explicit prefab/gender evidence",
}


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


def _load_boundary_manifest(path: str, video_size: int, video_sha256: str) -> dict:
    if not os.path.isfile(path):
        raise ReferenceSetError(f"refined boundary manifest not found: {path}")
    try:
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, ValueError) as error:
        raise ReferenceSetError(f"could not read refined boundary manifest: {error}")
    if report.get("schema") != "endfield.gameplay-video.boundaries.v2":
        raise ReferenceSetError(
            "unsupported refined boundary manifest schema: "
            + str(report.get("schema"))
        )
    pinned = report.get("video") or {}
    if pinned.get("bytes") != video_size or str(pinned.get("sha256", "")).upper() != video_sha256:
        raise ReferenceSetError("refined boundary manifest is for a different video pin")
    if not isinstance(report.get("boundaries"), list):
        raise ReferenceSetError("refined boundary manifest has no boundaries list")
    return report


def _parse_actor_filter(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    values = []
    for value in raw.split(","):
        actor = value.strip().lower()
        if not actor:
            continue
        if actor not in values:
            values.append(actor)
    if not values:
        raise ReferenceSetError("--actors must contain at least one actor token")
    return values


def _roi_contract() -> dict:
    x0, y0, x1, y1 = CHARACTER_BAND_BOX
    frame_width, frame_height = EXPECTED_RESOLUTION
    return {
        "contract": "strict_character_band.v1",
        "kind": "strict_character_band",
        "box": list(CHARACTER_BAND_BOX),
        "alphaMask": None,
        "excludedRectangles": [
            {
                "name": "top_foreground_ui",
                "box": [0, 0, frame_width, y0],
                "evidence": "outside the validated character band",
            },
            {
                "name": "left_foreground_ui_and_character_info_panel",
                "box": [0, y0, x0, y1],
                "evidence": {
                    "panelBox": list(PANEL_BOX),
                    "nameBox": list(NAME_BOX),
                    "source": "build_gameplay_video_reference_set.py",
                },
            },
            {
                "name": "right_foreground_ui",
                "box": [x1, y0, frame_width - x1, y1],
                "evidence": "outside the validated character band",
            },
            {
                "name": "bottom_foreground_ui",
                "box": [0, y1, frame_width, frame_height - y1],
                "evidence": "outside the validated character band",
            },
        ],
        "evidence": {
            "source": "unity_endfield_graph_shader_lab/tools/refine_gameplay_video_boundaries.py",
            "sourceConstant": "BAND_BOX",
            "visualComparisonRoi": "config/visual_comparison_rois.json",
            "pixelMaskVerified": False,
            "note": (
                "This is a strict, auditable central band, not an alpha "
                "segmentation mask. Pixels inside the band are not claimed "
                "to be a per-pixel character matte."
            ),
        },
        "deliveryAllowed": False,
        "deliveryBlocker": "no verified character alpha/mask evidence",
    }


def _endmin_identity(row: dict) -> str | None:
    """Resolve endmin only from explicit prefab/gender evidence in the row."""
    evidence = row.get("identityEvidence") or row.get("identity")
    if not isinstance(evidence, dict):
        return None
    prefab = str(evidence.get("prefab") or evidence.get("prefabPath") or "").lower()
    gender = str(evidence.get("gender") or "").lower()
    if "endminf" in prefab and gender in {"f", "female"}:
        return "endminf"
    if "endminm" in prefab and gender in {"m", "male"}:
        return "endminm"
    return None


def _independent_overview_phases(
    row: dict,
    slot_index: int,
    actor: str,
    video_size: int,
    video_sha256: str,
) -> tuple[dict, dict] | None:
    """Read only an explicit, evidence-backed start/loop boundary contract."""
    phases = row.get("overviewPhases")
    evidence = row.get("loopBoundaryEvidence")
    if not isinstance(phases, dict) or not isinstance(evidence, dict):
        return None
    if not evidence.get("source") or not evidence.get("method"):
        return None
    if evidence.get("slotIndex") != slot_index:
        return None
    if str(evidence.get("actor") or "").strip().lower() != actor:
        return None
    if str(evidence.get("videoPath") or "") != VIDEO_RELATIVE:
        return None
    if str(evidence.get("videoSha256") or "").upper() != video_sha256:
        return None
    if evidence.get("videoBytes") != video_size:
        return None
    source_frames = evidence.get("sourceFrameRange")
    source_times = evidence.get("sourceTimeRangeSeconds")
    if not (
        isinstance(source_frames, list)
        and len(source_frames) == 2
        and all(isinstance(value, int) and not isinstance(value, bool) for value in source_frames)
        and isinstance(source_times, list)
        and len(source_times) == 2
        and all(isinstance(value, (int, float)) for value in source_times)
        and source_frames[0] <= source_frames[1]
        and source_times[0] <= source_times[1]
    ):
        return None
    start = phases.get("overview_start") or phases.get("start")
    loop = phases.get("overview_loop") or phases.get("loop")
    if not isinstance(start, dict) or not isinstance(loop, dict):
        return None
    values = [
        start.get("startSeconds"),
        start.get("endSeconds"),
        loop.get("startSeconds"),
        loop.get("endSeconds"),
    ]
    if not all(isinstance(value, (int, float)) for value in values):
        return None
    if not start["startSeconds"] < start["endSeconds"]:
        return None
    if start["endSeconds"] != loop["startSeconds"]:
        return None
    if not loop["startSeconds"] < loop["endSeconds"]:
        return None
    if start["startSeconds"] < source_times[0] or loop["endSeconds"] > source_times[1]:
        return None
    if start["startSeconds"] * 60.0 < source_frames[0] - 1:
        return None
    if loop["endSeconds"] * 60.0 > source_frames[1] + 1:
        return None
    return start, loop


def _verified_character_mask(
    report: dict,
    video_path: str,
    video_size: int,
    video_sha256: str,
    roi_contract: dict,
) -> dict | None:
    """Validate a frame-aligned mask before allowing any character delivery."""
    evidence = report.get("characterMaskEvidence")
    if not isinstance(evidence, dict) or evidence.get("verified") is not True:
        return None
    required = ("source", "method", "path", "sha256", "videoPath", "videoSha256", "videoBytes")
    if not all(str(evidence.get(key) or "").strip() for key in required):
        return None
    if str(evidence.get("videoPath")) != VIDEO_RELATIVE:
        return None
    if str(evidence.get("videoSha256")).upper() != video_sha256:
        return None
    if evidence.get("videoBytes") != video_size:
        return None
    raw_path = str(evidence["path"])
    mask_path = raw_path if os.path.isabs(raw_path) else os.path.join(REPO_ROOT, raw_path)
    if not os.path.isfile(mask_path):
        return None
    digest = hashlib.sha256()
    try:
        with open(mask_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 22), b""):
                digest.update(chunk)
    except OSError:
        return None
    if digest.hexdigest().upper() != str(evidence["sha256"]).upper():
        return None

    source_capture = cv2.VideoCapture(video_path)
    mask_capture = cv2.VideoCapture(mask_path)
    try:
        if not source_capture.isOpened() or not mask_capture.isOpened():
            return None
        source_fps = source_capture.get(cv2.CAP_PROP_FPS)
        source_frames = int(round(source_capture.get(cv2.CAP_PROP_FRAME_COUNT)))
        mask_fps = mask_capture.get(cv2.CAP_PROP_FPS)
        mask_frames = int(round(mask_capture.get(cv2.CAP_PROP_FRAME_COUNT)))
        mask_width = int(mask_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        mask_height = int(mask_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if source_frames <= 0 or mask_frames <= 0:
            return None
        if abs(source_fps - 60.0) > 0.01 or abs(mask_fps - source_fps) > 0.01:
            return None
        full_resolution = EXPECTED_RESOLUTION
        band_resolution = (
            CHARACTER_BAND_BOX[2] - CHARACTER_BAND_BOX[0],
            CHARACTER_BAND_BOX[3] - CHARACTER_BAND_BOX[1],
        )
        if (mask_width, mask_height) not in {full_resolution, band_resolution}:
            return None
        if mask_frames != source_frames:
            return None

        excluded_boxes: list[tuple[int, int, int, int]] = []
        for item in roi_contract.get("excludedRectangles") or []:
            raw_box = item.get("box") if isinstance(item, dict) else None
            if not (
                isinstance(raw_box, list)
                and len(raw_box) == 4
                and all(isinstance(value, int) and not isinstance(value, bool) for value in raw_box)
            ):
                return None
            box = tuple(int(value) for value in raw_box)
            if not box[0] < box[2] or not box[1] < box[3]:
                return None
            excluded_boxes.append(box)
        if not excluded_boxes:
            return None

        band_x0, band_y0, band_x1, band_y1 = CHARACTER_BAND_BOX
        mask_full_frame = (mask_width, mask_height) == EXPECTED_RESOLUTION
        mask_origin_x, mask_origin_y = (0, 0) if mask_full_frame else (band_x0, band_y0)
        coverage_box = (
            band_x0 - mask_origin_x,
            band_y0 - mask_origin_y,
            band_x1 - mask_origin_x,
            band_y1 - mask_origin_y,
        )
        if not (
            0 <= coverage_box[0] < coverage_box[2] <= mask_width
            and 0 <= coverage_box[1] < coverage_box[3] <= mask_height
        ):
            return None

        checked_frames = 0
        intersection_total = 0
        intersection_max = 0
        intersection_frame_count = 0
        coverage_min: int | None = None
        coverage_max = 0
        coverage_total = 0
        coverage_zero_frame_count = 0
        for _ in range(source_frames):
            source_ok, _source_frame = source_capture.read()
            mask_ok, mask_frame = mask_capture.read()
            if not source_ok or not mask_ok or mask_frame is None:
                return None
            if mask_frame.ndim == 2:
                mask_gray = mask_frame
            else:
                mask_gray = cv2.cvtColor(mask_frame, cv2.COLOR_BGR2GRAY)

            coverage = int(
                cv2.countNonZero(
                    mask_gray[
                        coverage_box[1] : coverage_box[3],
                        coverage_box[0] : coverage_box[2],
                    ]
                )
            )
            coverage_min = coverage if coverage_min is None else min(coverage_min, coverage)
            coverage_max = max(coverage_max, coverage)
            coverage_total += coverage
            if coverage == 0:
                coverage_zero_frame_count += 1

            intersection = 0
            for x0, y0, x1, y1 in excluded_boxes:
                ix0 = max(x0, mask_origin_x)
                iy0 = max(y0, mask_origin_y)
                ix1 = min(x1, mask_origin_x + mask_width)
                iy1 = min(y1, mask_origin_y + mask_height)
                if ix0 >= ix1 or iy0 >= iy1:
                    continue
                intersection += int(
                    cv2.countNonZero(
                        mask_gray[
                            iy0 - mask_origin_y : iy1 - mask_origin_y,
                            ix0 - mask_origin_x : ix1 - mask_origin_x,
                        ]
                    )
                )
            checked_frames += 1
            intersection_total += intersection
            intersection_max = max(intersection_max, intersection)
            if intersection:
                intersection_frame_count += 1

        source_extra_ok, _source_extra_frame = source_capture.read()
        mask_extra_ok, _mask_extra_frame = mask_capture.read()
        if source_extra_ok or mask_extra_ok:
            return None
        if (
            checked_frames != source_frames
            or checked_frames != mask_frames
            or coverage_min is None
            or coverage_zero_frame_count
            or intersection_max
        ):
            return None
    finally:
        source_capture.release()
        mask_capture.release()

    validated = dict(evidence)
    validated["resolvedPath"] = mask_path
    validated["measuredResolution"] = [mask_width, mask_height]
    validated["measuredFrameCount"] = mask_frames
    validated["measuredFps"] = mask_fps
    validated["fullFrameMask"] = mask_full_frame
    validated["intersectionPixels"] = intersection_max
    validated["checkedFrameCount"] = checked_frames
    validated["pixelAuditSummary"] = {
        "method": "actual cv2 mask pixels against roiContract.excludedRectangles",
        "checkedFrameCount": checked_frames,
        "expectedFrameCount": source_frames,
        "intersectionPixels": intersection_max,
        "intersectionPixelsTotal": intersection_total,
        "intersectionFrameCount": intersection_frame_count,
        "coveragePixelsMin": coverage_min,
        "coveragePixelsMax": coverage_max,
        "coveragePixelsTotal": coverage_total,
        "coverageZeroFrameCount": coverage_zero_frame_count,
        "summary": (
            f"checked {checked_frames} frames; max excluded-UI intersection "
            f"{intersection_max} pixels; coverage min {coverage_min} pixels"
        ),
    }
    return validated


def _emit_clip(
    ffmpeg_path: str,
    video_path: str,
    mask_path: str,
    mask_full_frame: bool,
    output_path: str,
    start_seconds: float,
    end_seconds: float,
) -> dict:
    x0, y0, x1, y1 = CHARACTER_BAND_BOX
    width = x1 - x0
    height = y1 - y0
    duration = end_seconds - start_seconds
    if duration <= 0:
        raise ReferenceSetError(
            f"invalid clip range {start_seconds:.4f}-{end_seconds:.4f}s"
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    mask_crop = (
        f"crop={width}:{height}:{x0}:{y0},format=gray"
        if mask_full_frame
        else f"format=gray,scale={width}:{height}:flags=neighbor"
    )
    filter_graph = (
        f"[0:v]crop={width}:{height}:{x0}:{y0},format=rgba[base];"
        f"[1:v]{mask_crop}[mask];"
        "[base][mask]alphamerge,format=yuva444p10le[v]"
    )
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start_seconds:.6f}",
        "-i",
        video_path,
        "-ss",
        f"{start_seconds:.6f}",
        "-i",
        mask_path,
        "-t",
        f"{duration:.6f}",
        "-filter_complex",
        filter_graph,
        "-map",
        "[v]",
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
        "-slicecrc",
        "1",
        "-fps_mode",
        "cfr",
        output_path,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise ReferenceSetError(f"could not execute ffmpeg: {error}")
    if completed.returncode != 0:
        try:
            os.unlink(output_path)
        except FileNotFoundError:
            pass
        detail = (completed.stderr or "").strip().replace("\n", " ")
        raise ReferenceSetError(
            f"ffmpeg failed for {os.path.basename(output_path)} "
            f"(exit {completed.returncode}): {detail[:1000]}"
        )
    try:
        size = os.path.getsize(output_path)
    except OSError as error:
        raise ReferenceSetError(
            f"ffmpeg reported success but clip is missing: {output_path}: {error}"
        )
    if size <= 0:
        raise ReferenceSetError(f"ffmpeg produced an empty clip: {output_path}")
    digest = hashlib.sha256()
    with open(output_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return {"path": os.path.basename(output_path), "bytes": size, "sha256": digest.hexdigest()}


def _build_video_segments(
    output_root: str,
    video_path: str,
    video_size: int,
    video_sha256: str,
    reference_segments: list[dict],
    actors: list[str] | None,
    emit_clips: bool,
    boundary_manifest_path: str,
) -> dict:
    boundaries_report = _load_boundary_manifest(
        boundary_manifest_path, video_size, video_sha256
    )
    boundaries = boundaries_report["boundaries"]
    roi_contract = _roi_contract()
    mask_evidence = _verified_character_mask(
        boundaries_report,
        video_path,
        video_size,
        video_sha256,
        roi_contract,
    )
    if mask_evidence is not None:
        roi_contract["alphaMask"] = mask_evidence
        roi_contract["evidence"]["pixelMaskVerified"] = True
        roi_contract["evidence"]["pixelMaskAudit"] = mask_evidence["pixelAuditSummary"]
        roi_contract["deliveryAllowed"] = True
        roi_contract["deliveryBlocker"] = None
    discovered = {
        str(row.get("actor", "")).strip().lower()
        for row in boundaries
        if row.get("actor")
    }
    if actors is None:
        selected = None
    else:
        unknown = set(actors) - discovered - set(KNOWN_UNRESOLVED_ACTORS)
        if unknown:
            raise ReferenceSetError(
                "unknown actor token(s) in --actors: " + ", ".join(sorted(unknown))
            )
        selected = set(actors)

    ffmpeg_path = None

    entries = []
    for row in boundaries:
        source_actor = str(row.get("actor") or "").strip().lower()
        if not source_actor:
            continue
        actor = source_actor
        if source_actor == "endmin":
            resolved_endmin = _endmin_identity(row)
            if resolved_endmin is None:
                if selected is None or "endmin" in selected:
                    entries.append(
                        {
                            "slotIndex": int(row.get("index", -1)),
                            "actor": "endmin",
                            "sourceActor": "endmin",
                            "templateId": row.get("templateId"),
                            "status": "unresolved",
                            "reason": KNOWN_UNRESOLVED_ACTORS["endmin"],
                            "phaseOrder": None,
                            "clip": None,
                        }
                    )
                continue
            actor = resolved_endmin
        if selected is not None and actor not in selected:
            continue
        if not roi_contract["deliveryAllowed"]:
            entries.append(
                {
                    "slotIndex": int(row.get("index", -1)),
                    "actor": actor,
                    "sourceActor": source_actor,
                    "templateId": row.get("templateId"),
                    "status": "unresolved",
                    "reason": (
                        "character mask evidence is absent or fails the actual "
                        "frame/pixel audit (zero excluded-UI intersection and "
                        "complete per-frame coverage are required); strict "
                        "central ROI is audit-only and no clip is emitted"
                    ),
                    "phaseOrder": None,
                    "clip": None,
                }
            )
            continue
        index = int(row.get("index", -1))
        if index < 0 or index >= len(reference_segments):
            raise ReferenceSetError(f"boundary index out of range: {index}")
        reference = reference_segments[index]
        phases = _independent_overview_phases(
            row,
            index,
            actor,
            video_size,
            video_sha256,
        )
        if phases is None:
            entries.append(
                {
                    "slotIndex": index,
                    "actor": actor,
                    "sourceActor": source_actor,
                    "templateId": row.get("templateId"),
                    "status": "unresolved",
                    "reason": (
                        "no independent, evidence-backed overview loop boundary; "
                        "settledSeconds is only a reference frame and is not used "
                        "as an animation transition"
                    ),
                    "phaseOrder": None,
                    "clip": None,
                }
            )
            continue
        start_phase, loop_phase = phases
        start_seconds = float(start_phase["startSeconds"])
        loop_start_seconds = float(loop_phase["startSeconds"])
        end_seconds = float(loop_phase["endSeconds"])
        if not start_seconds < loop_start_seconds < end_seconds:
            raise ReferenceSetError(
                f"invalid overview phase order for {actor} slot {index}: "
                f"{start_seconds:.4f} < {loop_start_seconds:.4f} < {end_seconds:.4f}"
            )
        entry = {
            "slotIndex": index,
            "actor": actor,
            "sourceActor": source_actor,
            "templateId": row.get("templateId"),
            "status": "prepared",
            "slot": {
                "startSeconds": round(start_seconds, 4),
                "endSeconds": round(end_seconds, 4),
                "durationSeconds": round(end_seconds - start_seconds, 4),
            },
            "overviewStart": {
                "startSeconds": round(start_seconds, 4),
                "endSeconds": round(loop_start_seconds, 4),
                "durationSeconds": round(loop_start_seconds - start_seconds, 4),
            },
            "overviewLoop": {
                "startSeconds": round(loop_start_seconds, 4),
                "endSeconds": round(end_seconds, 4),
                "durationSeconds": round(end_seconds - loop_start_seconds, 4),
            },
            "phaseOrder": ["overview_start", "overview_loop"],
            "clip": None,
        }
        entries.append(entry)

    existing_unresolved = {
        entry.get("actor")
        for entry in entries
        if entry.get("status") == "unresolved"
    }
    unresolved = [
        {
            "actor": actor,
            "status": "unresolved",
            "reason": reason,
            "clip": None,
        }
        for actor, reason in KNOWN_UNRESOLVED_ACTORS.items()
        if (selected is None or actor in selected) and actor not in existing_unresolved
    ]
    emit_error = None
    if emit_clips:
        blockers = [
            entry for entry in entries if entry.get("status") != "prepared"
        ] + unresolved
        if blockers:
            labels = ", ".join(
                str(item.get("actor") or item.get("slotIndex"))
                for item in blockers[:12]
            )
            emit_error = (
                "--emit-clips cannot deliver every requested actor; unresolved "
                "mask/phase/identity contract(s): " + labels
            )
        else:
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                emit_error = "--emit-clips requested but ffmpeg was not found"
            else:
                try:
                    for entry in entries:
                        clip_path = os.path.join(
                            output_root,
                            "clips",
                            f"{entry['actor']}_slot_{entry['slotIndex']:02d}.mkv",
                        )
                        entry["clip"] = _emit_clip(
                            ffmpeg_path,
                            video_path,
                            mask_evidence["resolvedPath"],
                            bool(mask_evidence["fullFrameMask"]),
                            clip_path,
                            float(entry["slot"]["startSeconds"]),
                            float(entry["slot"]["endSeconds"]),
                        )
                        entry["status"] = "clip_emitted"
                except Exception as error:
                    detail = str(error).strip().replace("\n", " ")
                    emit_error = (
                        "--emit-clips failed while writing FFV1 Matroska/MKV output: "
                        + (detail[:1000] or error.__class__.__name__)
                    )

    if emit_clips and emit_error is not None:
        for entry in entries:
            if entry.get("status") != "prepared":
                continue
            entry["status"] = "unresolved"
            entry["reason"] = emit_error
            entry["clip"] = None
            unresolved.append(
                {
                    "slotIndex": entry.get("slotIndex"),
                    "actor": entry.get("actor"),
                    "status": "unresolved",
                    "reason": emit_error,
                    "clip": None,
                }
            )

    result = {
        "schema": "endfield.gameplay-video-character-slots.v1",
        "boundary": "refined_recorded_video_measurement",
        "video": {
            "path": VIDEO_RELATIVE,
            "bytes": video_size,
            "sha256": video_sha256,
        },
        "filter": {
            "requestedActors": sorted(selected) if selected is not None else None,
            "endminIdentityPolicy": (
                "ambiguous unless a boundary row contains explicit prefab and "
                "gender evidence; no endmin->endminf alias is applied"
            ),
        },
        "roiContract": roi_contract,
        "phasePolicy": {
            "order": ["overview_start", "overview_loop"],
            "overviewStart": "explicit overviewPhases.start boundary only",
            "overviewLoop": "explicit overviewPhases.loop boundary only",
            "note": (
                "Rows without overviewPhases plus loopBoundaryEvidence remain "
                "unresolved. settledSeconds and modelSwapSeconds are never used "
                "as a substitute for an authored loop transition."
            ),
        },
        "clipEncoding": {
            "requested": emit_clips,
            "enabled": bool(
                emit_clips
                and emit_error is None
                and roi_contract["deliveryAllowed"]
            ),
            "videoCodec": "ffv1" if emit_clips else None,
            "lossless": True,
            "container": "matroska",
            "codecContract": "FFV1 level 3, coder 1, context 1, g 1, slice CRC",
            "audio": "omitted" if emit_clips else None,
        },
        "emitError": emit_error,
        "segments": entries,
        "unresolved": unresolved,
        "segmentCount": len(entries),
        "clipCount": sum(1 for entry in entries if entry["clip"]),
    }
    manifest_path = os.path.join(output_root, VIDEO_SEGMENTS_MANIFEST_NAME)
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    if emit_clips and emit_error is not None:
        raise ReferenceSetError(emit_error)
    return result


def build(
    output_root: str,
    use_ocr: bool,
    actors: list[str] | None = None,
    emit_clips: bool = False,
    boundary_manifest_path: str = DEFAULT_BOUNDARY_MANIFEST,
) -> dict:
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
    # The existing frame set remains the primary output. If refined boundaries
    # are present, add the character-slot list; explicit actor/clip requests
    # make a missing or stale refined manifest a hard error.
    if actors is not None or emit_clips or os.path.isfile(boundary_manifest_path):
        video_segments = _build_video_segments(
            output_root,
            video_path,
            size,
            digest,
            entries,
            actors,
            emit_clips,
            boundary_manifest_path,
        )
        manifest["videoSegmentsManifest"] = VIDEO_SEGMENTS_MANIFEST_NAME
        manifest["videoSegmentCount"] = video_segments["segmentCount"]
        manifest["videoClipCount"] = video_segments["clipCount"]
    with open(os.path.join(output_root, MANIFEST_NAME), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT)
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument(
        "--actors",
        help=(
            "comma-separated actor tokens to emit, e.g. endminf,pelica,chen; "
            "endmin is ambiguous and never aliases to endminf"
        ),
    )
    parser.add_argument(
        "--emit-clips",
        action="store_true",
        help="emit central-band FFV1 Matroska/MKV clips with ffmpeg; failure is fatal",
    )
    parser.add_argument(
        "--boundary-manifest",
        default=DEFAULT_BOUNDARY_MANIFEST,
        help="refined video_segment_boundaries.json path",
    )
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
        actors = _parse_actor_filter(args.actors)
        manifest = build(
            args.output_root,
            not args.no_ocr,
            actors=actors,
            emit_clips=args.emit_clips,
            boundary_manifest_path=args.boundary_manifest,
        )
    except ReferenceSetError as error:
        print(f"reference set failed: {error}", file=sys.stderr)
        return 2

    print(
        f"segments {manifest['segmentCount']}, "
        f"identified {manifest['identifiedCount']}"
    )
    if "videoSegmentsManifest" in manifest:
        print(
            f"video slots {manifest['videoSegmentCount']}, "
            f"clips {manifest['videoClipCount']} "
            f"({manifest['videoSegmentsManifest']})"
        )
    for item in manifest["segments"]:
        label = item["displayName"] or "(unidentified)"
        print(f"  {item['index']:>2} {item['settledSeconds']:>8.2f}s  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
