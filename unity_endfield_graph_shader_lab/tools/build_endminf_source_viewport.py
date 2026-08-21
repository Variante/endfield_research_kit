"""Build the lossless Endminf source viewport and its UI-validity mask.

This is a source-pixel reference, not a matte and not an inpainting pass.  It
copies the exact decoded source pixels for frames 9783..10409 into a cropped
FFV1/BGR0 stream.  The captured mouse pointer is retained in those pixels and
is represented by a synchronized binary validity-mask stream.  Consumers must
ignore mask=0 pixels; no actor/background value is synthesized there.

The fixed viewport is deliberately the same 3840x2160 camera framing used by
the Unity comparison contract.  The outer game UI rectangles do not intersect
the crop.  A persistent pointer does, so the output is published only as
``original_bgr0 + validity_mask`` and never as a claimed clean/no-UI clip.

Usage::

    python tools/build_endminf_source_viewport.py --write
    python tools/build_endminf_source_viewport.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from build_priority_actor_mattes import (
    EXPECTED_DECODED_FRAME_COUNT,
    EXPECTED_FPS,
    EXPECTED_SIZE,
    EXPECTED_SOURCE_DURATION_SECONDS,
    EXPECTED_TIMELINE_FRAME_COUNT,
    EXPECTED_PACKET_COUNT,
    VIDEO_BYTES,
    VIDEO_RELATIVE,
    VIDEO_SHA256,
    UI_RECTANGLES,
    _expected_source_contract,
    _probe_video,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
VIDEO_PATH = REPO_ROOT / VIDEO_RELATIVE
REPORT_PATH = PROJECT_ROOT / "tools" / "endminf_source_viewport_contract.json"
SCRATCH_ROOT = PROJECT_ROOT / "scratch" / "character_recovery" / "endminf_source_viewport"
CLIP_PATH = SCRATCH_ROOT / "endminf_source_viewport_original_bgr0.mkv"
MASK_PATH = SCRATCH_ROOT / "endminf_source_viewport_validity_mask_gray.mkv"
NO_UI_VISUALIZATION_PATH = SCRATCH_ROOT / "endminf_source_viewport_no_ui_marked_bgr0.mkv"
SAMPLE_ROOT = SCRATCH_ROOT / "samples"
CAMERA_CONTRACT_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "OriginalData" / "CharInfoPresentation" / "charinfo_overview_camera_contract.json"
COMPARISON_EVIDENCE_PATH = PROJECT_ROOT / "tools" / "endminm_comparable_capture_evidence.json"
CAMERA_CONTRACT_SHA256 = "F7DF587923FD848C828C44E39BF11A98F5376EB2DA73D7642EFCA10E40EB43A0"
COMPARISON_EVIDENCE_SHA256 = "76AA472409042F42935D0CC70EF5D3574C00D12595F9F266D292899764F59755"
COMPARISON_CAMERA_ID = "chr_0003_endmin_comparison"

SOURCE_FRAME_START = 9783
SOURCE_FRAME_END = 10409
FRAME_COUNT = SOURCE_FRAME_END - SOURCE_FRAME_START + 1
CROP = (800, 188, 3000, 2120)  # source x0,y0,x1,y1, half-open
CROP_WIDTH = CROP[2] - CROP[0]
CROP_HEIGHT = CROP[3] - CROP[1]

PHASE_RANGES = {
    "start": (9783, 10028),
    "transition": (10029, 10116),
    "clean_loop": (10117, 10409),
}
SAMPLE_FRAMES = (9783, 10029, 10117, 10409)

# The pointer is fixed in the source recording.  Protection is deliberately
# larger than the observed 28x28 cursor core to include anti-aliased edges.
CURSOR_CORE = (2538, 882, 2566, 910)
CURSOR_PROTECTION = (2534, 878, 2570, 914)
CURSOR_PROTECTION_RELATIVE = (
    CURSOR_PROTECTION[0] - CROP[0],
    CURSOR_PROTECTION[1] - CROP[1],
    CURSOR_PROTECTION[2] - CROP[0],
    CURSOR_PROTECTION[3] - CROP[1],
)
CURSOR_DETECTOR = {
    "kind": "pinned_bright_cursor_core",
    "coreBoxSource": list(CURSOR_CORE),
    "minPixelsGrayAtLeast230": 200,
    "minPixelsGrayAtLeast245": 150,
    "protectionBoxSource": list(CURSOR_PROTECTION),
}
CURSOR_DETECTOR_SHA256 = hashlib.sha256(
    json.dumps(CURSOR_DETECTOR, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest().upper()

SCHEMA = "endfield.character-recovery.endminf-source-viewport.v1"
PIXEL_POLICY = "exact_decoded_source_crop_no_segmentation_no_compositing_no_inpainting"
NO_UI_VISUALIZATION_POLICY = "invalid_cursor_region_replaced_with_deterministic_magenta_black_checkerboard_only"


class ViewportError(RuntimeError):
    """Raised when source, UI validity, or artifact evidence is stale."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _write_json_lf(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".lf.partial")
    temporary.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def _run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise ViewportError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stderr[-1000:]}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ViewportError(f"invalid JSON from {' '.join(command)}: {error}") from error
    if not isinstance(value, dict):
        raise ViewportError("ffprobe JSON must be an object")
    return value


def _source_contract() -> dict[str, Any]:
    if not VIDEO_PATH.is_file():
        raise ViewportError(f"source video is missing: {VIDEO_PATH}")
    size, digest = _sha256_file(VIDEO_PATH)
    if size != VIDEO_BYTES or digest != VIDEO_SHA256:
        raise ViewportError(f"source hash mismatch: {size}/{digest}")
    try:
        probe = _probe_video(VIDEO_PATH)
    except Exception as error:  # the imported probe exposes a stable MatteError
        raise ViewportError(f"source probe failed: {error}") from error
    actual = {"path": VIDEO_RELATIVE.as_posix(), "bytes": size, "sha256": digest, **probe}
    if actual != _expected_source_contract():
        raise ViewportError("source timing/count/PTS contract is stale")
    if int(actual["decodedFrameCount"]) != EXPECTED_DECODED_FRAME_COUNT:
        raise ViewportError("decoded source count is not authoritative pinned count")
    return actual


def _phase(frame: int) -> str:
    for name, (start, end) in PHASE_RANGES.items():
        if start <= frame <= end:
            return name
    raise ViewportError(f"frame {frame} is outside phase contract")


def _assert_crop_contract() -> dict[str, Any]:
    if CROP[0] < 0 or CROP[1] < 0 or CROP[2] > EXPECTED_SIZE[0] or CROP[3] > EXPECTED_SIZE[1]:
        raise ViewportError(f"crop is outside source size: {CROP}")
    if CROP_WIDTH != 2200 or CROP_HEIGHT != 1932:
        raise ViewportError("crop dimensions changed")
    if CURSOR_PROTECTION[0] < CROP[0] or CURSOR_PROTECTION[1] < CROP[1]:
        raise ViewportError("cursor protection is not inside crop")
    if CURSOR_PROTECTION[2] > CROP[2] or CURSOR_PROTECTION[3] > CROP[3]:
        raise ViewportError("cursor protection exceeds crop")
    for name, (x0, y0, x1, y1) in UI_RECTANGLES:
        overlap = max(0, min(CROP[2], x1) - max(CROP[0], x0)) * max(
            0, min(CROP[3], y1) - max(CROP[1], y0)
        )
        if overlap:
            raise ViewportError(f"known UI rectangle intersects crop: {name} overlap={overlap}")
    return {
        "sourceSize": list(EXPECTED_SIZE),
        "sourceCropHalfOpen": list(CROP),
        "outputSize": [CROP_WIDTH, CROP_HEIGHT],
        "knownOuterUiRectangles": [{"name": name, "box": list(box)} for name, box in UI_RECTANGLES],
        "knownOuterUiOverlapPixels": 0,
        "bottomContact": "not_claimed_below_source_y_2120",
    }


def _camera_comparison_contract() -> dict[str, Any]:
    return {
        "fullSourceResolution": list(EXPECTED_SIZE),
        "sameCameraRequired": True,
        "sameCropRequired": True,
        "cameraId": COMPARISON_CAMERA_ID,
        "sourceCropHalfOpen": list(CROP),
        "cameraContract": {"path": _relative(CAMERA_CONTRACT_PATH), "sha256": CAMERA_CONTRACT_SHA256},
        "comparisonEvidence": {"path": _relative(COMPARISON_EVIDENCE_PATH), "sha256": COMPARISON_EVIDENCE_SHA256},
    }


def _cursor_mask() -> np.ndarray:
    mask = np.full((CROP_HEIGHT, CROP_WIDTH), 255, dtype=np.uint8)
    x0, y0, x1, y1 = CURSOR_PROTECTION_RELATIVE
    mask[y0:y1, x0:x1] = 0
    return mask


def _no_ui_visualization(raw_bgr0: bytes) -> bytes:
    """Mark invalid pixels conspicuously without inventing actor/background."""
    array = np.frombuffer(raw_bgr0, dtype=np.uint8).reshape((CROP_HEIGHT, CROP_WIDTH, 4)).copy()
    x0, y0, x1, y1 = CURSOR_PROTECTION_RELATIVE
    height, width = y1 - y0, x1 - x0
    yy, xx = np.indices((height, width))
    checker = ((xx // 4 + yy // 4) % 2).astype(bool)
    marker = np.zeros((height, width, 3), dtype=np.uint8)
    marker[checker] = (255, 0, 255)  # conspicuous BGR magenta
    array[y0:y1, x0:x1, :3] = marker
    array[:, :, 3] = 0
    return array.tobytes()


def _cursor_detected(frame_bgr0: bytes) -> tuple[bool, dict[str, int]]:
    array = np.frombuffer(frame_bgr0, dtype=np.uint8).reshape((CROP_HEIGHT, CROP_WIDTH, 4))
    x0, y0, x1, y1 = (value - offset for value, offset in zip(CURSOR_CORE, (CROP[0], CROP[1], CROP[0], CROP[1])))
    core = array[y0:y1, x0:x1, :3]
    gray = cv2.cvtColor(core, cv2.COLOR_BGR2GRAY)
    bright230 = int(np.count_nonzero(gray >= 230))
    bright245 = int(np.count_nonzero(gray >= 245))
    facts = {"grayAtLeast230": bright230, "grayAtLeast245": bright245}
    return bright230 >= 200 and bright245 >= 150, facts


def _decoder() -> subprocess.Popen[bytes]:
    filter_graph = (
        f"select=between(n\\,{SOURCE_FRAME_START}\\,{SOURCE_FRAME_END}),"
        f"crop={CROP_WIDTH}:{CROP_HEIGHT}:{CROP[0]}:{CROP[1]},format=bgr0"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(VIDEO_PATH),
        "-map", "0:v:0", "-vf", filter_graph, "-vsync", "0", "-f", "rawvideo",
        "-pix_fmt", "bgr0", "-",
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _encoder(path: Path, pix_fmt: str) -> subprocess.Popen[bytes]:
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pixel_format", pix_fmt,
        "-video_size", f"{CROP_WIDTH}x{CROP_HEIGHT}", "-framerate", "60",
        "-i", "-", "-an", "-c:v", "ffv1", "-level", "3", "-coder", "1",
        "-g", "1", "-pix_fmt", pix_fmt, "-f", "matroska", str(path),
    ]
    return subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)


def _artifact_probe(path: Path, expected_pix_fmt: str) -> dict[str, Any]:
    if not path.is_file():
        raise ViewportError(f"artifact is missing: {path}")
    data = _run_json([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-count_packets",
        "-show_entries", "stream=codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_read_frames,nb_read_packets",
        "-show_entries", "format=duration,size", "-of", "json", str(path),
    ])
    stream = (data.get("streams") or [{}])[0]
    frames = int(stream.get("nb_read_frames") or 0)
    packets = int(stream.get("nb_read_packets") or 0)
    fps = str(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "")
    codec = str(stream.get("codec_name") or "").lower()
    pix_fmt = str(stream.get("pix_fmt") or "").lower()
    if codec != "ffv1" or pix_fmt != expected_pix_fmt:
        raise ViewportError(f"artifact metadata mismatch: codec={codec} pix_fmt={pix_fmt}")
    if (int(stream.get("width") or 0), int(stream.get("height") or 0)) != (CROP_WIDTH, CROP_HEIGHT):
        raise ViewportError("artifact dimensions mismatch")
    if frames != FRAME_COUNT or packets != FRAME_COUNT or fps not in {"60/1", "60/1"}:
        raise ViewportError(f"artifact count/rate mismatch: frames={frames} packets={packets} fps={fps}")
    size, digest = _sha256_file(path)
    return {
        "path": _relative(path), "bytes": size, "sha256": digest,
        "codec": codec, "pixFmt": pix_fmt, "width": CROP_WIDTH, "height": CROP_HEIGHT,
        "frames": frames, "packets": packets, "fps": fps,
        "durationSeconds": float((data.get("format") or {}).get("duration") or 0.0),
    }


def _decode_raw(path: Path, pix_fmt: str) -> Iterable[bytes]:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-map", "0:v:0",
        "-f", "rawvideo", "-pix_fmt", pix_fmt, "-vsync", "0", "-",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_bytes = CROP_WIDTH * CROP_HEIGHT * (4 if pix_fmt == "bgr0" else 1)
    assert process.stdout is not None
    try:
        while True:
            # Do not ask Windows' buffered pipe reader for a 17-MB single
            # read.  FFmpeg can retain a large decoded queue while that call
            # waits for the requested size, making a checker look hung.  The
            # bounded reads below preserve exact frame boundaries and keep
            # back-pressure moving through the pipe.
            chunks: list[bytes] = []
            remaining = frame_bytes
            while remaining:
                chunk = process.stdout.read(min(1 << 20, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            frame = b"".join(chunks)
            if not frame:
                break
            if len(frame) != frame_bytes:
                raise ViewportError(f"truncated {pix_fmt} artifact frame")
            yield frame
    finally:
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        code = process.wait()
        if code:
            raise ViewportError(f"artifact decode failed ({code}): {stderr[-500:]}")


def _decode_cv2(path: Path, pix_fmt: str) -> Iterable[bytes]:
    """Read an artifact sequentially without a second Windows raw pipe.

    OpenCV's FFV1 reader is used only for checker readback.  It returns BGR
    for BGR0 and often expands gray to three channels; restoring the explicit
    zero byte (or selecting channel zero) makes the comparison byte-defined.
    """
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ViewportError(f"cannot open artifact with OpenCV: {path}")
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[:2] != (CROP_HEIGHT, CROP_WIDTH):
                raise ViewportError(f"artifact frame dimensions changed: {path} {frame.shape}")
            if pix_fmt == "bgr0":
                zero = np.zeros((CROP_HEIGHT, CROP_WIDTH, 1), dtype=np.uint8)
                yield np.concatenate((frame[:, :, :3], zero), axis=2).tobytes()
            else:
                yield frame[:, :, 0].tobytes()
    finally:
        capture.release()


def _build() -> dict[str, Any]:
    source = _source_contract()
    crop_contract = _assert_crop_contract()
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    SAMPLE_ROOT.mkdir(parents=True, exist_ok=True)
    clip_partial = CLIP_PATH.with_suffix(".partial.mkv")
    mask_partial = MASK_PATH.with_suffix(".partial.mkv")
    visualization_partial = NO_UI_VISUALIZATION_PATH.with_suffix(".partial.mkv")
    for path in (clip_partial, mask_partial, visualization_partial):
        if path.exists():
            path.unlink()
    decoder = _decoder()
    clip_encoder = _encoder(clip_partial, "bgr0")
    mask_encoder = _encoder(mask_partial, "gray")
    visualization_encoder = _encoder(visualization_partial, "bgr0")
    assert decoder.stdout is not None
    assert clip_encoder.stdin is not None and mask_encoder.stdin is not None and visualization_encoder.stdin is not None
    frame_bytes = CROP_WIDTH * CROP_HEIGHT * 4
    rows: list[dict[str, Any]] = []
    cursor_hits = 0
    mask = _cursor_mask()
    mask_bytes = mask.tobytes()
    try:
        for output_index, source_frame in enumerate(range(SOURCE_FRAME_START, SOURCE_FRAME_END + 1)):
            raw = decoder.stdout.read(frame_bytes)
            if len(raw) != frame_bytes:
                raise ViewportError(f"source decoder ended at frame {source_frame}")
            # FFmpeg's ``format=bgr0`` source readback uses an implementation
            # filler byte (255 here), while the FFV1/BGR0 decoder emits zero.
            # Canonicalize only that non-pixel filler byte so source rows and
            # the lossless artifact have identical hashes; B/G/R are untouched.
            raw_array = np.frombuffer(raw, dtype=np.uint8).reshape((CROP_HEIGHT, CROP_WIDTH, 4)).copy()
            raw_array[:, :, 3] = 0
            raw = raw_array.tobytes()
            detected, detector_facts = _cursor_detected(raw)
            if not detected:
                raise ViewportError(f"pinned cursor detector failed at source frame {source_frame}")
            cursor_hits += 1
            clip_encoder.stdin.write(raw)
            mask_encoder.stdin.write(mask_bytes)
            visualization_raw = _no_ui_visualization(raw)
            visualization_encoder.stdin.write(visualization_raw)
            crop_hash = _sha256_bytes(raw)
            cursor_core = np.frombuffer(raw, dtype=np.uint8).reshape((CROP_HEIGHT, CROP_WIDTH, 4))[
                CURSOR_CORE[1] - CROP[1]:CURSOR_CORE[3] - CROP[1],
                CURSOR_CORE[0] - CROP[0]:CURSOR_CORE[2] - CROP[0],
            ].tobytes()
            row = {
                "outputFrameIndex": output_index,
                "sourceFrame": source_frame,
                "sourcePtsSeconds": source_frame / EXPECTED_FPS,
                "phase": _phase(source_frame),
                "cropSha256": crop_hash,
                "cursorCoreSha256": _sha256_bytes(cursor_core),
                "cursorDetector": detector_facts,
                "validPixels": CROP_WIDTH * CROP_HEIGHT - (CURSOR_PROTECTION_RELATIVE[2] - CURSOR_PROTECTION_RELATIVE[0]) * (CURSOR_PROTECTION_RELATIVE[3] - CURSOR_PROTECTION_RELATIVE[1]),
                "invalidPixels": (CURSOR_PROTECTION_RELATIVE[2] - CURSOR_PROTECTION_RELATIVE[0]) * (CURSOR_PROTECTION_RELATIVE[3] - CURSOR_PROTECTION_RELATIVE[1]),
                "noUiVisualizationSha256": _sha256_bytes(visualization_raw),
            }
            rows.append(row)
            if source_frame in SAMPLE_FRAMES:
                array = np.frombuffer(raw, dtype=np.uint8).reshape((CROP_HEIGHT, CROP_WIDTH, 4))[:, :, :3]
                sample_path = SAMPLE_ROOT / f"source_frame_{source_frame}.png"
                if not cv2.imwrite(str(sample_path), array):
                    raise ViewportError(f"cannot write visual sample: {sample_path}")
    finally:
        decoder.stdout.close()
        decoder_stderr = decoder.stderr.read().decode("utf-8", "replace") if decoder.stderr else ""
        decoder_code = decoder.wait()
        clip_encoder.stdin.close()
        mask_encoder.stdin.close()
        visualization_encoder.stdin.close()
        clip_stderr = clip_encoder.stderr.read().decode("utf-8", "replace") if clip_encoder.stderr else ""
        mask_stderr = mask_encoder.stderr.read().decode("utf-8", "replace") if mask_encoder.stderr else ""
        visualization_stderr = visualization_encoder.stderr.read().decode("utf-8", "replace") if visualization_encoder.stderr else ""
        clip_code = clip_encoder.wait()
        mask_code = mask_encoder.wait()
        visualization_code = visualization_encoder.wait()
        if decoder_code or clip_code or mask_code or visualization_code:
            raise ViewportError(
                f"pipeline failed source={decoder_code} clip={clip_code} mask={mask_code} visualization={visualization_code}; "
                f"source={decoder_stderr[-300:]} clip={clip_stderr[-300:]} mask={mask_stderr[-300:]} visualization={visualization_stderr[-300:]}"
            )
    if len(rows) != FRAME_COUNT or cursor_hits != FRAME_COUNT:
        raise ViewportError(f"frame/cursor count mismatch: rows={len(rows)} cursor={cursor_hits}")
    os.replace(clip_partial, CLIP_PATH)
    os.replace(mask_partial, MASK_PATH)
    os.replace(visualization_partial, NO_UI_VISUALIZATION_PATH)
    clip = _artifact_probe(CLIP_PATH, "bgr0")
    validity = _artifact_probe(MASK_PATH, "gray")
    visualization = _artifact_probe(NO_UI_VISUALIZATION_PATH, "bgr0")
    samples = []
    for frame in SAMPLE_FRAMES:
        path = SAMPLE_ROOT / f"source_frame_{frame}.png"
        size, digest = _sha256_file(path)
        samples.append({"sourceFrame": frame, "path": _relative(path), "bytes": size, "sha256": digest})
    report = {
        "schema": SCHEMA,
        "status": "published_with_invalid_ui_mask",
        "pathBase": "repo_root",
        "source": source,
        "window": {
            "sourceFrameRangeInclusive": [SOURCE_FRAME_START, SOURCE_FRAME_END],
            "frameCount": FRAME_COUNT,
            "fps": EXPECTED_FPS,
            "phases": {name: {"rangeInclusive": list(bounds), "frameCount": bounds[1] - bounds[0] + 1} for name, bounds in PHASE_RANGES.items()},
        },
        "pixelPolicy": PIXEL_POLICY,
        "bgr0FillerBytePolicy": "canonical_zero_only; BGR channels are copied unchanged",
        "crop": crop_contract,
        "cameraComparisonContract": _camera_comparison_contract(),
        "uiValidity": {
            "knownPersistentOverlays": [{
                "name": "mouse_cursor",
                "sourceBox": list(CURSOR_PROTECTION),
                "cropBox": list(CURSOR_PROTECTION_RELATIVE),
                "coreBoxSource": list(CURSOR_CORE),
                "detector": CURSOR_DETECTOR,
                "detectorSha256": CURSOR_DETECTOR_SHA256,
                "detectedFrames": FRAME_COUNT,
                "invalidMaskValue": 0,
                "reason": "fixed source pointer visibly intersects viewport; retained in original pixels and excluded only by validity mask",
            }],
            "unmodeledCenterOverlayStatus": "not_claimed_clean",
            "comparisonRule": "ignore_all_mask_zero_pixels; never synthesize replacement pixels",
        },
        "artifacts": {"originalViewport": clip, "validityMask": validity, "noUiVisualization": visualization},
        "noUiVisualization": {
            "policy": NO_UI_VISUALIZATION_POLICY,
            "path": visualization["path"],
            "invalidRegionOnly": True,
            "validPixelsRemainSourceExact": True,
            "notACompleteSilhouette": True,
        },
        "visualSamples": samples,
        "frames": rows,
        "publicationGates": {
            "sourcePin": True,
            "fullFrameSourceMapping": len(rows) == FRAME_COUNT,
            "exactCropOnly": True,
            "cursorDetectedEveryFrame": cursor_hits == FRAME_COUNT,
            "validityMaskSynchronized": True,
            "noUiClaim": False,
            "completeSilhouetteClaim": False,
            "ffv1OriginalBgr0": True,
            "ffv1ValidityMask": True,
            "noUiVisualizationMarked": True,
        },
    }
    _write_json_lf(REPORT_PATH, report)
    return report


def _load_report() -> dict[str, Any]:
    try:
        value = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ViewportError(f"cannot read report: {error}") from error
    if not isinstance(value, dict):
        raise ViewportError("viewport report must be an object")
    return value


def _check() -> None:
    report = _load_report()
    if report.get("schema") != SCHEMA or report.get("status") != "published_with_invalid_ui_mask":
        raise ViewportError("viewport report status/schema is not the admitted masked source contract")
    if report.get("pathBase") != "repo_root" or report.get("pixelPolicy") != PIXEL_POLICY:
        raise ViewportError("viewport report path/pixel policy mismatch")
    if report.get("bgr0FillerBytePolicy") != "canonical_zero_only; BGR channels are copied unchanged":
        raise ViewportError("viewport BGR0 filler-byte policy is stale")
    no_ui = report.get("noUiVisualization") or {}
    if (
        no_ui.get("policy") != NO_UI_VISUALIZATION_POLICY
        or no_ui.get("invalidRegionOnly") is not True
        or no_ui.get("validPixelsRemainSourceExact") is not True
        or no_ui.get("notACompleteSilhouette") is not True
    ):
        raise ViewportError("no-UI visualization policy is stale")
    camera = report.get("cameraComparisonContract") or {}
    if camera != _camera_comparison_contract():
        raise ViewportError("Unity comparison camera/crop contract is stale")
    for path, expected_hash in ((CAMERA_CONTRACT_PATH, CAMERA_CONTRACT_SHA256), (COMPARISON_EVIDENCE_PATH, COMPARISON_EVIDENCE_SHA256)):
        size, digest = _sha256_file(path)
        if digest != expected_hash:
            raise ViewportError(f"comparison contract hash mismatch: {path} {digest} != {expected_hash}")
    source = _source_contract()
    if report.get("source") != source:
        raise ViewportError("viewport source contract is stale")
    crop = _assert_crop_contract()
    if report.get("crop") != crop:
        raise ViewportError("viewport crop contract is stale")
    window = report.get("window") or {}
    if window.get("sourceFrameRangeInclusive") != [SOURCE_FRAME_START, SOURCE_FRAME_END] or window.get("frameCount") != FRAME_COUNT:
        raise ViewportError("viewport frame range is stale")
    phases = window.get("phases") or {}
    expected_phases = {name: {"rangeInclusive": list(bounds), "frameCount": bounds[1] - bounds[0] + 1} for name, bounds in PHASE_RANGES.items()}
    if phases != expected_phases:
        raise ViewportError("viewport phase contract is stale")
    ui = report.get("uiValidity") or {}
    overlays = ui.get("knownPersistentOverlays") or []
    if len(overlays) != 1 or overlays[0].get("sourceBox") != list(CURSOR_PROTECTION) or overlays[0].get("cropBox") != list(CURSOR_PROTECTION_RELATIVE):
        raise ViewportError("cursor protection contract is stale")
    if ui.get("unmodeledCenterOverlayStatus") != "not_claimed_clean":
        raise ViewportError("center overlay status cannot be upgraded without evidence")
    rows = report.get("frames") or []
    if len(rows) != FRAME_COUNT:
        raise ViewportError("viewport frame rows are incomplete")
    for index, row in enumerate(rows):
        expected_frame = SOURCE_FRAME_START + index
        if row.get("outputFrameIndex") != index or row.get("sourceFrame") != expected_frame or row.get("phase") != _phase(expected_frame):
            raise ViewportError(f"viewport row {index} mapping is not contiguous")
        if row.get("invalidPixels") != 36 * 36 or row.get("validPixels") != CROP_WIDTH * CROP_HEIGHT - 36 * 36:
            raise ViewportError(f"viewport row {index} validity stats are stale")
        if not isinstance(row.get("cropSha256"), str) or len(row["cropSha256"]) != 64:
            raise ViewportError(f"viewport row {index} crop hash is missing")
    artifacts = report.get("artifacts") or {}
    clip = _artifact_probe(CLIP_PATH, "bgr0")
    validity = _artifact_probe(MASK_PATH, "gray")
    visualization = _artifact_probe(NO_UI_VISUALIZATION_PATH, "bgr0")
    if (
        artifacts.get("originalViewport") != clip
        or artifacts.get("validityMask") != validity
        or artifacts.get("noUiVisualization") != visualization
    ):
        raise ViewportError("viewport artifact metadata/hash is stale")
    for index, (raw, mask_raw, visualization_raw) in enumerate(
        zip(
            _decode_cv2(CLIP_PATH, "bgr0"),
            _decode_cv2(MASK_PATH, "gray"),
            _decode_cv2(NO_UI_VISUALIZATION_PATH, "bgr0"),
        )
    ):
        if _sha256_bytes(raw) != rows[index]["cropSha256"]:
            raise ViewportError(f"viewport pixel hash mismatch at output frame {index}")
        if (
            _sha256_bytes(visualization_raw) != rows[index]["noUiVisualizationSha256"]
            or visualization_raw != _no_ui_visualization(raw)
        ):
            raise ViewportError(f"no-UI visualization mismatch at output frame {index}")
        mask = np.frombuffer(mask_raw, dtype=np.uint8).reshape((CROP_HEIGHT, CROP_WIDTH))
        expected = _cursor_mask()
        if not np.array_equal(mask, expected):
            raise ViewportError(f"viewport validity mask mismatch at output frame {index}")
    print(f"Endminf source viewport verified: {REPORT_PATH}")
    print(f"crop={CROP_WIDTH}x{CROP_HEIGHT} frames={FRAME_COUNT} fps={EXPECTED_FPS} status=masked_source_reference")


def _refresh_report_contract() -> None:
    report = _load_report()
    report["cameraComparisonContract"] = _camera_comparison_contract()
    _write_json_lf(REPORT_PATH, report)
    print(f"Endminf source viewport report contract refreshed: {REPORT_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="decode source and write the viewport/mask/report")
    mode.add_argument("--check", action="store_true", help="recompute source, artifact, row, and mask evidence")
    mode.add_argument("--refresh-report", action="store_true", help="refresh only deterministic camera-contract fields; never re-encodes")
    args = parser.parse_args()
    try:
        if args.check:
            _check()
        elif args.refresh_report:
            _refresh_report_contract()
        else:
            report = _build()
            print(f"Endminf source viewport written: {REPORT_PATH}")
            print(f"status={report['status']} frames={FRAME_COUNT} cursorInvalid=1296 pixels/frame")
    except ViewportError as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
