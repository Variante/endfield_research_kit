"""Audit the exact Endminf identity and overview phase in the pinned video.

The roster OCR row is intentionally only ``endmin``/``chr_9000_endmin``.  This
tool never treats that alias as the character identity.  Admission requires
the independently extracted ``chr_0003_endminf`` source manifest, its exact
controller and clips, and a reproducible visual match between the pinned
video frame and an Endminf-only render produced from those assets.

The phase contract is composite evidence: the measured video model-swap and
next model-swap frames anchor the window, while the exact Endminf controller
and AnimationClips supply the start/transition/loop boundaries.  It does not
claim that the video itself exposes an AnimationClip name.

Usage::

    python tools/audit_endminf_video_identity.py --write
    python tools/audit_endminf_video_identity.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
VIDEO_RELATIVE = Path("videos/2026-08-15_10-32-32.mkv")
VIDEO_PATH = REPO_ROOT / VIDEO_RELATIVE
VIDEO_BYTES = 1_678_613_397
VIDEO_SHA256 = "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7"
EXPECTED_FPS = 60.0
EXPECTED_SIZE = (3840, 2160)
REPORT_PATH = PROJECT_ROOT / "tools" / "endminf_video_identity_evidence.json"
BOUNDARIES_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "video_segment_boundaries.json"
REFERENCE_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "gameplay_reference_manifest.json"
SETTLED_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "settled_reference_frames.json"
SETTLED_IMAGE = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "settled" / "endmin_settled_frame10300.png"
VIDEO_IMAGE = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "13_frame10110.png"
PHASE_REPORT_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "visual_delta" / "endmin_refine_phase.json"
PHASE_RENDER_PATH = REPO_ROOT / "scratch" / "charinfo_phase_sweep" / "endmin_t0p133.png"
SOURCE_MANIFEST_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "endminf_ui_recovery_manifest.json"
ENDMINM_SOURCE_MANIFEST_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "endminm_ui_recovery_manifest.json"
ENDMINF_PREFAB_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "Prefabs" / "Endminf.prefab"
ENDMINM_PREFAB_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Prefabs" / "Endminm.prefab"
CONTROLLER_AUDIT_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "overview_controller_native" / "controller_asset_audit.json"
CAPTURE_PROBE_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "overview_capture_probe" / "Endminf" / "Endminf_overview_capture.json"
CAMERA_CONTRACT_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "OriginalData" / "CharInfoPresentation" / "charinfo_overview_camera_contract.json"
OVERVIEW_CAMERAS_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "charinfo_prefabs" / "overview_cameras.json"
START_CLIP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "Animations" / "A_actor_endminf_ui_overview_start.anim"
LOOP_CLIP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminf" / "Animations" / "A_actor_endminf_ui_overview_loop.anim"
CHARACTER_BAND = (1400, 200, 2500, 2100)
SCHEMA = "endfield.character-recovery.endminf-video-identity.v1"
EXACT_CHARACTER_ID = "chr_0003_endminf"
EXACT_ACTOR_TOKEN = "endminf"
GENERIC_VIDEO_ACTOR = "endmin"
GENERIC_VIDEO_TEMPLATE = "chr_9000_endmin"
MODEL_SWAP_FRAME = 9767
NEXT_MODEL_SWAP_FRAME = 10500
EXPECTED_VIDEO_SEGMENT_INDEX = 13
EXPECTED_RENDER_SAMPLE_TIME = 0.133
MIN_VISUAL_ECC = 0.80
CANDIDATE_MATRIX_MIN_MARGIN = 0.05
SOURCE_TRANSITION_RANGE = (9767, 9782)
SOURCE_TRANSITION_RANGES = (SOURCE_TRANSITION_RANGE, (10410, 10499))
TAIL_TRANSITION_RANGE = (10410, 10499)
LAST_CLEAN_TARGET_FRAME = 10409
TAIL_CLASSIFICATION = "evidence_bounded_target_window_exit_non_target_transition"
STABLE_START_FRAME = 9783
SOURCE_TRANSITION_REASON = (
    "pinned-source Endminf model-swap fade has no person-class component through "
    "frame 9782; first stable chr_0003_endminf component is frame 9783; "
    "target-window exit/non-target transition is classified and blacked from frame 10410 through 10499; following actor identity is not claimed"
)
_STOP_TIME_RE = re.compile(r"^\s*m_StopTime:\s*([-+0-9.eE]+)\s*$", re.MULTILINE)


class EvidenceError(RuntimeError):
    """Raised when exact identity or phase evidence is missing or stale."""


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 22), b""):
                total += len(chunk)
                digest.update(chunk)
    except OSError as error:
        raise EvidenceError(f"cannot hash {path}: {error}") from error
    return total, digest.hexdigest().upper()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"cannot read JSON evidence {path}: {error}") from error
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON evidence is not an object: {path}")
    return value


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EvidenceError(f"required evidence is missing: {path}")
    size, digest = _sha256(path)
    return {"path": _relative(path), "bytes": size, "sha256": digest}


def _require_close(actual: Any, expected: float, label: str, tolerance: float = 1e-5) -> float:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        raise EvidenceError(f"{label} is not numeric: {actual!r}")
    value = float(actual)
    if not math.isfinite(value) or abs(value - expected) > tolerance:
        raise EvidenceError(f"{label} is {actual!r}, expected {expected!r}")
    return value


def _stop_time(path: Path) -> float:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise EvidenceError(f"cannot read AnimationClip {path}: {error}") from error
    match = _STOP_TIME_RE.search(text)
    if match is None:
        raise EvidenceError(f"AnimationClip has no m_StopTime: {path}")
    return float(match.group(1))


def _load_endminf_controller() -> dict[str, Any]:
    audit = _read_json(CONTROLLER_AUDIT_PATH)
    rows = audit.get("actors")
    if not isinstance(rows, list):
        raise EvidenceError("controller audit has no actors list")
    matches = [row for row in rows if isinstance(row, dict) and row.get("character_id") == EXACT_CHARACTER_ID]
    if len(matches) != 1:
        raise EvidenceError(f"controller audit has {len(matches)} exact Endminf rows")
    row = matches[0]
    if row.get("actor_token") != EXACT_ACTOR_TOKEN:
        raise EvidenceError("exact Endminf controller row has the wrong actor token")
    overview = row.get("main_overview")
    if not isinstance(overview, dict):
        raise EvidenceError("exact Endminf controller row has no main overview")
    expected = {
        "start_clip": START_CLIP_PATH.stem,
        "loop_clip": LOOP_CLIP_PATH.stem,
        "entry_normalized_offset": 0.0058366423,
        "exit_normalized_time": 0.75,
        "transition_duration": 0.25,
        "destination_normalized_offset": 0.0,
    }
    for key, value in expected.items():
        if isinstance(value, str):
            if overview.get(key) != value:
                raise EvidenceError(f"Endminf controller {key} is stale: {overview.get(key)!r}")
        else:
            _require_close(overview.get(key), value, f"Endminf controller {key}")
    return row


def _load_video_evidence() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    boundaries = _read_json(BOUNDARIES_PATH)
    boundary_rows = boundaries.get("boundaries")
    if not isinstance(boundary_rows, list) or len(boundary_rows) < 15:
        raise EvidenceError("video boundaries do not cover the Endminf segment and following segment")
    by_index = {int(row.get("index")): row for row in boundary_rows if isinstance(row, dict) and row.get("index") is not None}
    row = by_index.get(EXPECTED_VIDEO_SEGMENT_INDEX)
    next_row = by_index.get(EXPECTED_VIDEO_SEGMENT_INDEX + 1)
    if row is None or next_row is None:
        raise EvidenceError("missing Endminf or following video boundary row")
    if row.get("actor") != GENERIC_VIDEO_ACTOR or row.get("templateId") != GENERIC_VIDEO_TEMPLATE:
        raise EvidenceError("the pinned Endminf candidate row changed; generic alias evidence is required")
    if next_row.get("actor") == GENERIC_VIDEO_ACTOR:
        raise EvidenceError("Endminf candidate does not have a unique following segment")
    _require_close(row.get("modelSwapFrame"), MODEL_SWAP_FRAME, "Endminf modelSwapFrame", tolerance=0.0)
    _require_close(next_row.get("modelSwapFrame"), NEXT_MODEL_SWAP_FRAME, "next modelSwapFrame", tolerance=0.0)
    _require_close(row.get("modelSwapSeconds"), MODEL_SWAP_FRAME / EXPECTED_FPS, "Endminf modelSwapSeconds", tolerance=1e-4)
    _require_close(next_row.get("modelSwapSeconds"), NEXT_MODEL_SWAP_FRAME / EXPECTED_FPS, "next modelSwapSeconds", tolerance=1e-4)
    reference = _read_json(REFERENCE_PATH)
    segments = reference.get("segments")
    if not isinstance(segments, list) or len(segments) != 33:
        raise EvidenceError("reference manifest does not cover all 33 video segments")
    indexes = sorted(int(item.get("index")) for item in segments if isinstance(item, dict) and item.get("index") is not None)
    if indexes != list(range(33)):
        raise EvidenceError(f"reference segment indices are not complete: {indexes}")
    endmin = [item for item in segments if item.get("index") == EXPECTED_VIDEO_SEGMENT_INDEX]
    if len(endmin) != 1 or endmin[0].get("actor") != GENERIC_VIDEO_ACTOR or endmin[0].get("templateId") != GENERIC_VIDEO_TEMPLATE:
        raise EvidenceError("reference manifest does not preserve the generic Endmin alias row")
    return boundaries, row, next_row


def _visual_match() -> dict[str, Any]:
    phase = _read_json(PHASE_REPORT_PATH)
    if phase.get("schema") != "endfield.charinfo.phase-sweep.v1" or phase.get("actor") != GENERIC_VIDEO_ACTOR:
        raise EvidenceError("Endminf visual phase evidence has the wrong schema or actor")
    reference = phase.get("reference") or {}
    if reference.get("frame") != SETTLED_IMAGE.name:
        raise EvidenceError("visual evidence does not use the pinned Endminf settled video frame")
    best = phase.get("best") or {}
    best_samples = [row for row in phase.get("samples", []) if isinstance(row, dict) and abs(float(row.get("sampleTime", -1)) - float(best.get("sampleTime", -2))) <= 1e-6]
    render_name = best_samples[0].get("file") if len(best_samples) == 1 else None
    if render_name != PHASE_RENDER_PATH.name or abs(float(best.get("sampleTime", -1)) - EXPECTED_RENDER_SAMPLE_TIME) > 1e-6:
        raise EvidenceError("visual evidence does not use the pinned Endminf-only render sample")
    reference_evidence = _file_evidence(SETTLED_IMAGE)
    render_evidence = _file_evidence(PHASE_RENDER_PATH)
    expected_reference_hash = str(reference.get("sha256", "")).upper()
    if expected_reference_hash != reference_evidence["sha256"]:
        raise EvidenceError("settled Endminf video frame hash differs from its phase evidence")
    reference_image = cv2.imread(str(SETTLED_IMAGE), cv2.IMREAD_COLOR)
    render_image = cv2.imread(str(PHASE_RENDER_PATH), cv2.IMREAD_COLOR)
    if reference_image is None or render_image is None or reference_image.shape != render_image.shape:
        raise EvidenceError("Endminf visual evidence images are missing or have different dimensions")
    x0, y0, x1, y1 = CHARACTER_BAND
    ref_gray = cv2.cvtColor(reference_image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype("float32")
    render_gray = cv2.cvtColor(render_image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype("float32")
    warp = cv2.getRotationMatrix2D((ref_gray.shape[1] / 2.0, ref_gray.shape[0] / 2.0), 0.0, 1.0).astype("float32")
    # ECC needs a 2x3 warp and is deterministic for this fixed pair.  A small
    # translation-only solve avoids treating unrelated UI pixels as identity.
    warp[:, 2] = 0.0
    try:
        ecc, solved = cv2.findTransformECC(ref_gray, render_gray, warp, cv2.MOTION_TRANSLATION, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-6), inputMask=None, gaussFiltSize=5)
    except cv2.error as error:
        raise EvidenceError(f"could not compute Endminf visual ECC: {error}") from error
    recorded = float(best.get("correlation", 0.0))
    if float(ecc) < MIN_VISUAL_ECC or abs(float(ecc) - recorded) > 0.08:
        raise EvidenceError(f"Endminf visual ECC is not reproducible/strong: {ecc} (recorded {recorded})")
    return {
        "videoFrame": reference_evidence | {"frame": 10300},
        "videoSettledPhaseReport": _file_evidence(PHASE_REPORT_PATH),
        "exactEndminfRender": render_evidence | {"sampleTimeSeconds": EXPECTED_RENDER_SAMPLE_TIME},
        "characterBand": list(CHARACTER_BAND),
        "eccTranslation": round(float(ecc), 6),
        "recordedPhaseReportCorrelation": recorded,
        "minimumEcc": MIN_VISUAL_ECC,
        "alignment": {
            "mode": "ECC translation over character band",
            "warpTranslationPixels": [round(float(solved[0, 2]), 3), round(float(solved[1, 2]), 3)],
        },
        "interpretation": "video actor pixels match the exact chr_0003_endminf render; generic endmin/chr_9000_endmin is not used as identity proof",
    }


def _source_identity() -> dict[str, Any]:
    source = _read_json(SOURCE_MANIFEST_PATH)
    expected = {
        "character_id": EXACT_CHARACTER_ID,
        "actor_token": EXACT_ACTOR_TOKEN,
        "model": "actor_endminf",
        "original_prefab_root": "chr_0003_endminf_postmodel",
    }
    for key, value in expected.items():
        if source.get(key) != value:
            raise EvidenceError(f"Endminf source manifest {key} is stale: {source.get(key)!r}")
    capture = _read_json(CAPTURE_PROBE_PATH)
    if capture.get("prefab") != "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab":
        raise EvidenceError("Endminf capture probe does not use the exact Endminf prefab")
    if capture.get("phase") != "ui_overview_start_then_ui_overview_loop":
        raise EvidenceError("Endminf capture probe is not an overview start/loop capture")
    clips = capture.get("clips")
    if not isinstance(clips, list) or not {row.get("name") for row in clips if isinstance(row, dict)} >= {START_CLIP_PATH.stem, LOOP_CLIP_PATH.stem}:
        raise EvidenceError("Endminf capture probe lacks exact overview start/loop clips")
    camera = capture.get("camera_contract")
    if not isinstance(camera, dict):
        raise EvidenceError("Endminf capture probe has no camera contract")
    expected_camera_path = CAMERA_CONTRACT_PATH.relative_to(PROJECT_ROOT).as_posix()
    if camera.get("path") != expected_camera_path or camera.get("track") != "track_chr_0003_endmin":
        raise EvidenceError("Endminf capture probe camera contract is not the exact chr_0003_endmin track")
    if camera.get("template_id") != "chr_0003_endmin" or camera.get("actor") != GENERIC_VIDEO_ACTOR:
        raise EvidenceError("Endminf capture probe camera alias is stale")
    for field, expected_value in (("width", 1920), ("height", 1080), ("fps", 2)):
        if capture.get(field) != expected_value:
            raise EvidenceError(f"Endminf capture probe {field} is {capture.get(field)!r}, expected {expected_value!r}")
    controller = _load_endminf_controller()
    controller_fields = dict(controller["main_overview"])
    if controller_fields.get("source_json"):
        controller_source = Path(str(controller_fields["source_json"]))
        controller_fields["source_json"] = _relative(controller_source)
    return {
        "characterId": EXACT_CHARACTER_ID,
        "actorToken": EXACT_ACTOR_TOKEN,
        "sourceManifest": _file_evidence(SOURCE_MANIFEST_PATH),
        "sourceFields": {key: source[key] for key in expected},
        "controllerAudit": _file_evidence(CONTROLLER_AUDIT_PATH),
        "controllerFields": controller_fields,
        "captureProbe": _file_evidence(CAPTURE_PROBE_PATH),
        "capturePrefab": capture["prefab"],
        "prefab": _file_evidence(ENDMINF_PREFAB_PATH),
        "cameraContract": _file_evidence(CAMERA_CONTRACT_PATH) | {"track": camera["track"], "templateId": camera["template_id"]},
        "overviewCameras": _file_evidence(OVERVIEW_CAMERAS_PATH),
        "captureRenderSettings": {
            "width": capture["width"],
            "height": capture["height"],
            "fps": capture["fps"],
            "transparentClearRequested": capture.get("transparent_clear_requested"),
            "transparentPipelineOverrideApplied": capture.get("transparent_pipeline_override_applied"),
            "transparentPostProcessDisabled": capture.get("transparent_post_process_disabled"),
            "referenceBackdropDisabled": capture.get("reference_backdrop_disabled"),
            "nonActorRenderersDisabled": capture.get("non_actor_renderers_disabled"),
            "nonActorUiDisabled": capture.get("non_actor_ui_disabled"),
            "actorPropsDisabled": capture.get("actor_props_disabled"),
        },
        "startClip": _file_evidence(START_CLIP_PATH) | {"durationSeconds": _stop_time(START_CLIP_PATH)},
        "loopClip": _file_evidence(LOOP_CLIP_PATH) | {"durationSeconds": _stop_time(LOOP_CLIP_PATH)},
    }


def _candidate_matrix(source_identity: dict[str, Any], visual: dict[str, Any]) -> dict[str, Any]:
    """Compare the target against every plausible roster identity under one contract.

    The repository has an exact Endminf render, but no exact chr_9000_endmin
    source prefab/controller and no same-condition Endminm capture.  Those
    missing competitors are recorded as unavailable rather than silently
    treating a single target ECC as proof.
    """
    target_score = float(visual["eccTranslation"])
    target = {
        "candidateId": EXACT_CHARACTER_ID,
        "actorToken": EXACT_ACTOR_TOKEN,
        "role": "exact_target",
        "sourceAssets": {
            "manifest": source_identity["sourceManifest"],
            "prefab": source_identity["prefab"],
            "controllerAudit": source_identity["controllerAudit"],
            "captureProbe": source_identity["captureProbe"],
        },
        "render": {
            "available": True,
            "sameCameraContract": True,
            "sameRenderSettingsContract": True,
            "image": visual["exactEndminfRender"],
            "score": target_score,
            "scoreMetric": "ECC translation over pinned character band",
        },
    }
    endminm_manifest = _file_evidence(ENDMINM_SOURCE_MANIFEST_PATH)
    endminm_prefab = _file_evidence(ENDMINM_PREFAB_PATH)
    candidates = [
        target,
        {
            "candidateId": GENERIC_VIDEO_TEMPLATE,
            "actorToken": GENERIC_VIDEO_ACTOR,
            "role": "video_alias_only",
            "sourceAssets": {"manifest": None, "prefab": None, "controllerAudit": None, "captureProbe": None},
            "render": {"available": False, "sameCameraContract": False, "sameRenderSettingsContract": False, "score": None},
            "rejection": "chr_9000_endmin/endmin exists only as the pinned roster/video alias; no original-game-derived prefab/controller/capture exists",
        },
        {
            "candidateId": "endmin",
            "actorToken": "endmin",
            "role": "video_alias_only",
            "sourceAssets": {"manifest": None, "prefab": None, "controllerAudit": None, "captureProbe": None},
            "render": {"available": False, "sameCameraContract": False, "sameRenderSettingsContract": False, "score": None},
            "rejection": "generic endmin is not an independent original-game-derived asset identity",
        },
        {
            "candidateId": "chr_0002_endminm",
            "actorToken": "endminm",
            "role": "plausible_roster_competitor",
            "sourceAssets": {"manifest": endminm_manifest, "prefab": endminm_prefab, "controllerAudit": None, "captureProbe": None},
            "render": {"available": False, "sameCameraContract": False, "sameRenderSettingsContract": False, "score": None},
            "rejection": "exact Endminm manifest/prefab exists, but no same-camera/same-render-settings capture probe or comparable render exists",
        },
    ]
    numeric_competitors = [
        float(row["render"]["score"])
        for row in candidates[1:]
        if isinstance(row.get("render", {}).get("score"), (int, float))
    ]
    best_competitor = max(numeric_competitors) if numeric_competitors else None
    margin = target_score - best_competitor if best_competitor is not None else None
    comparable_competitors = [row["candidateId"] for row in candidates[1:] if row["render"].get("available")]
    margin_satisfied = best_competitor is not None and margin >= CANDIDATE_MATRIX_MIN_MARGIN
    identity_status = "proven" if margin_satisfied else "candidate"
    return {
        "schema": "endfield.character-recovery.identity-candidate-matrix.v1",
        "comparisonContract": {
            "cameraContract": source_identity["cameraContract"],
            "overviewCameras": source_identity["overviewCameras"],
            "cameraTrack": "track_chr_0003_endmin",
            "resolution": list(EXPECTED_SIZE),
            "alignment": "ECC translation over pinned character band",
            "minimumTargetScore": MIN_VISUAL_ECC,
            "minimumMarginAboveEveryComparableCompetitor": CANDIDATE_MATRIX_MIN_MARGIN,
        },
        "candidateCount": len(candidates),
        "comparableCompetitorCount": len(comparable_competitors),
        "comparableCompetitors": comparable_competitors,
        "targetScore": target_score,
        "bestCompetitorScore": best_competitor,
        "targetMargin": margin,
        "marginSatisfied": margin_satisfied,
        "status": identity_status,
        "candidates": candidates,
        "admission": {
            "identityStatus": identity_status,
            "matteCandidateAllowed": False,
            "reason": (
                "exact Endminf score is observed, but no comparable competitor render exists; "
                "a one-candidate ECC cannot prove identity"
                if not margin_satisfied
                else "target score clears the fixed minimum margin above every comparable competitor"
            ),
        },
    }


def _phase_contract(boundary_row: dict[str, Any], next_row: dict[str, Any], source_identity: dict[str, Any]) -> dict[str, Any]:
    controller = source_identity["controllerFields"]
    start_duration = float(source_identity["startClip"]["durationSeconds"])
    loop_duration = float(source_identity["loopClip"]["durationSeconds"])
    model_swap = MODEL_SWAP_FRAME / EXPECTED_FPS
    next_swap = NEXT_MODEL_SWAP_FRAME / EXPECTED_FPS
    entry = float(controller["entry_normalized_offset"])
    exit_time = float(controller["exit_normalized_time"])
    transition = float(controller["transition_duration"]) * start_duration
    transition_start = model_swap + (exit_time - entry) * start_duration
    loop_start = transition_start + transition
    if not model_swap < transition_start < loop_start < next_swap:
        raise EvidenceError("Endminf composite phase boundaries are not ordered")
    start_frame = MODEL_SWAP_FRAME
    transition_start_frame = int(round(transition_start * EXPECTED_FPS))
    loop_start_frame = int(round(loop_start * EXPECTED_FPS))
    if transition_start_frame != 10029 or loop_start_frame != 10117:
        raise EvidenceError("Endminf phase frame rounding changed unexpectedly")
    clean_loop_end_exclusive = LAST_CLEAN_TARGET_FRAME + 1
    clean_loop_end = clean_loop_end_exclusive / EXPECTED_FPS
    clean_loop_frames = clean_loop_end_exclusive - loop_start_frame
    loop_window = clean_loop_frames / EXPECTED_FPS
    loop_frame_start = loop_start_frame / EXPECTED_FPS
    return {
        "method": "video modelSwapFrame + exact Endminf controller entry/exit/transition + next modelSwapFrame",
        "videoModelSwap": {"frame": MODEL_SWAP_FRAME, "seconds": model_swap, "boundaryActorLabel": boundary_row["actor"], "boundaryTemplateLabel": boundary_row["templateId"]},
        "videoNextModelSwap": {"frame": NEXT_MODEL_SWAP_FRAME, "seconds": next_swap, "boundaryActor": next_row["actor"], "boundaryTemplate": next_row["templateId"]},
        "start": {"clip": START_CLIP_PATH.stem, "frameRangeInclusive": [start_frame, transition_start_frame - 1], "seconds": [model_swap, transition_start], "durationSeconds": transition_start - model_swap},
        "transition": {"clip": f"{START_CLIP_PATH.stem}->{LOOP_CLIP_PATH.stem}", "frameRangeInclusive": [transition_start_frame, loop_start_frame - 1], "seconds": [transition_start, loop_start], "durationSeconds": transition},
        "loop": {"clip": LOOP_CLIP_PATH.stem, "frameRangeInclusive": [loop_start_frame, LAST_CLEAN_TARGET_FRAME], "seconds": [loop_frame_start, clean_loop_end], "durationSeconds": loop_window, "runtimeClipDurationSeconds": loop_duration, "completeRuntimePeriods": math.floor(loop_window / loop_duration), "cleanTargetOnly": True, "stateBoundarySeconds": loop_start},
        "combinedActorWindow": {"frameRangeExclusive": [MODEL_SWAP_FRAME, NEXT_MODEL_SWAP_FRAME], "seconds": [model_swap, next_swap], "frameCount": NEXT_MODEL_SWAP_FRAME - MODEL_SWAP_FRAME},
        "cleanLoop": {
            "frameRangeExclusive": [loop_start_frame, clean_loop_end_exclusive],
            "frameRangeInclusive": [loop_start_frame, LAST_CLEAN_TARGET_FRAME],
            "frameCount": clean_loop_frames,
            "durationSeconds": loop_window,
            "runtimeClipDurationSeconds": loop_duration,
            "completeRuntimePeriods": math.floor(loop_window / loop_duration),
            "publicationStatus": "identity_candidate_only",
        },
        "sourceTransition": {
            "frameRangeInclusive": list(SOURCE_TRANSITION_RANGE),
            "frameRangesInclusive": [list(item) for item in SOURCE_TRANSITION_RANGES],
            "stableStartFrame": STABLE_START_FRAME,
            "reason": SOURCE_TRANSITION_REASON,
            "evidence": "per-frame pinned DeepLab person-class source scan; zero support through 9782 and support at 9783",
        },
        "videoOnlyLoopMeasurement": "not_claimed",
    }


def _scan_source_transition() -> dict[str, Any]:
    """Measure the exact source fade with the current pinned person model."""
    tools_root = str(PROJECT_ROOT / "tools")
    if tools_root not in sys.path:
        sys.path.insert(0, tools_root)
    try:
        import build_priority_actor_mattes as matte
    except ImportError as error:
        raise EvidenceError(f"cannot load pinned matte scanner: {error}") from error
    _weight_path, weight_hash = matte._current_pinned_weight()
    capture = cv2.VideoCapture(str(VIDEO_PATH))
    if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, SOURCE_TRANSITION_RANGE[0]):
        raise EvidenceError("could not seek the pinned video for Endminf transition scan")
    rows = []
    try:
        for frame_number in range(SOURCE_TRANSITION_RANGE[0], STABLE_START_FRAME + 1):
            ok, frame = capture.read()
            if not ok:
                raise EvidenceError(f"could not decode Endminf transition frame {frame_number}")
            mask = matte._deeplab_raw_mask(frame)
            rows.append({"frame": frame_number, "workMaskPixels": int((mask > 0).sum())})
    finally:
        capture.release()
    gap_rows = [row for row in rows if row["frame"] <= SOURCE_TRANSITION_RANGE[1]]
    stable_rows = [row for row in rows if row["frame"] == STABLE_START_FRAME]
    if any(row["workMaskPixels"] != 0 for row in gap_rows) or len(stable_rows) != 1 or stable_rows[0]["workMaskPixels"] <= 0:
        raise EvidenceError(f"Endminf source-transition scan contradicts the exact gap contract: {rows}")
    tail_frames = []
    tail_capture = cv2.VideoCapture(str(VIDEO_PATH))
    if not tail_capture.isOpened():
        raise EvidenceError("could not open the pinned video for Endminf exit boundary scan")
    try:
        for frame_number in range(TAIL_TRANSITION_RANGE[0], TAIL_TRANSITION_RANGE[1] + 1):
            if not tail_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number):
                raise EvidenceError(f"could not seek Endminf exit boundary frame {frame_number}")
            ok, frame = tail_capture.read()
            if not ok:
                raise EvidenceError(f"could not decode Endminf exit boundary frame {frame_number}")
            band = frame[200:2100, 1400:2500]
            tail_frames.append({
                "frame": frame_number,
                "bgrSha256": hashlib.sha256(frame.tobytes()).hexdigest().upper(),
                "characterBandMean": round(float(band.mean()), 6),
                "characterBandNonBlackPixels": int(np.count_nonzero(np.any(band > 8, axis=2))),
                "classification": TAIL_CLASSIFICATION,
            })
    finally:
        tail_capture.release()
    return {
        "weightSha256": weight_hash,
        "rows": rows,
        "tailBoundaryFrames": [
            {
                "frame": LAST_CLEAN_TARGET_FRAME,
                "classification": "last_clean_endminf_target_frame",
                "evidence": "the preceding frame is the last target frame before the pinned non-target transition range",
            },
            *tail_frames[:1],
            *tail_frames[-1:],
        ],
        "tailTransition": {
            "frameRangeInclusive": list(TAIL_TRANSITION_RANGE),
            "frameCount": TAIL_TRANSITION_RANGE[1] - TAIL_TRANSITION_RANGE[0] + 1,
            "classification": TAIL_CLASSIFICATION,
            "followingActorIdentity": "not_proven",
            "nextSegmentBoundaryFrame": NEXT_MODEL_SWAP_FRAME,
            "perFrame": tail_frames,
        },
    }


def build_report() -> dict[str, Any]:
    source_size, source_hash = _sha256(VIDEO_PATH)
    if source_size != VIDEO_BYTES or source_hash != VIDEO_SHA256:
        raise EvidenceError(f"pinned source changed: {source_size}/{source_hash}")
    boundaries, boundary_row, next_row = _load_video_evidence()
    source_identity = _source_identity()
    visual = _visual_match()
    settled = _read_json(SETTLED_PATH)
    settled_rows = [row for row in settled.get("frames", []) if isinstance(row, dict) and row.get("actor") == GENERIC_VIDEO_ACTOR]
    if len(settled_rows) != 1 or settled_rows[0].get("frameIndex") != 10300:
        raise EvidenceError("settled Endminf evidence frame is missing or ambiguous")
    phase = _phase_contract(boundary_row, next_row, source_identity)
    transition_scan = _scan_source_transition()
    phase["sourceTransition"]["perFramePinnedDeepLabScan"] = transition_scan
    phase["tailTransition"] = transition_scan["tailTransition"]
    candidate_matrix = _candidate_matrix(source_identity, visual)
    segment_sequence = []
    reference = _read_json(REFERENCE_PATH)
    for item in reference["segments"]:
        if 10 <= int(item["index"]) <= 16:
            segment_sequence.append({key: item.get(key) for key in ("index", "actor", "templateId", "displayName", "settledFrame")})
    return {
        "schema": SCHEMA,
        "status": "ok",
        "pathBase": "repo_root",
        "source": {"path": VIDEO_RELATIVE.as_posix(), "bytes": source_size, "sha256": source_hash, "fps": EXPECTED_FPS, "resolution": list(EXPECTED_SIZE)},
        "videoSearch": {
            "referenceSegmentCount": len(reference["segments"]),
            "boundaryRowCount": len(boundaries["boundaries"]),
            "searchedAllReferenceSegments": True,
            "genericAliasRow": {"segmentIndex": EXPECTED_VIDEO_SEGMENT_INDEX, "actor": GENERIC_VIDEO_ACTOR, "templateId": GENERIC_VIDEO_TEMPLATE, "visibleName": reference["segments"][EXPECTED_VIDEO_SEGMENT_INDEX].get("displayName")},
            "neighborSequence": segment_sequence,
            "identityAliasRejected": True,
        },
        "identity": {
            "status": candidate_matrix["status"],
            "characterId": EXACT_CHARACTER_ID,
            "actorToken": EXACT_ACTOR_TOKEN,
            "source": source_identity,
            "visibleVideo": {"settledFrame": _file_evidence(SETTLED_IMAGE) | {"frame": 10300}, "referenceFrame": _file_evidence(VIDEO_IMAGE) | {"frame": 10110}, "visibleAlias": GENERIC_VIDEO_ACTOR, "visibleTemplateAlias": GENERIC_VIDEO_TEMPLATE},
            "visualMatch": visual,
            "candidateMatrix": candidate_matrix,
            "proofRule": "exact source prefab/controller/clip provenance plus ECC >= 0.80 and a fixed >= 0.05 margin above every comparable competitor; generic alias is never substituted",
        },
        "phase": phase,
        "publication": {"matteCandidateAllowed": candidate_matrix["admission"]["matteCandidateAllowed"], "published": False, "reason": candidate_matrix["admission"]["reason"]},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the durable evidence report")
    parser.add_argument("--check", action="store_true", help="rebuild and compare the durable evidence report")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if not args.write and not args.check:
        parser.error("choose --write or --check")
    try:
        report = build_report()
        if args.check:
            if not args.report.is_file():
                raise EvidenceError(f"evidence report is missing: {args.report}")
            current = _read_json(args.report)
            if current != report:
                raise EvidenceError("durable Endminf evidence report is stale")
            print(f"Endminf identity/phase evidence verified: {args.report}")
        else:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.report.with_suffix(".partial.json")
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(args.report)
            print(f"Endminf identity/phase evidence written: {args.report}")
        print(f"identity={report['identity']['status']} window={report['phase']['combinedActorWindow']['frameRangeExclusive']} ecc={report['identity']['visualMatch']['eccTranslation']}")
        return 0
    except EvidenceError as error:
        print(f"Endminf identity/phase audit failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
