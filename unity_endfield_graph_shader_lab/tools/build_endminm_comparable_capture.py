"""Build and verify the common-camera Endminf/Endminm identity evidence.

The Unity capture is performed by the existing overview phase harness in one
scene/session.  Endminf and Endminm use one explicitly pinned Endminf vcam
transform, one Endminf lighting/operator-light profile, one viewer scene,
pipeline, backdrop, resolution, and render target.  This validator never
starts Unity and never writes captures; it hashes every sweep PNG and
recomputes every ECC value before admitting the maximum Endminm score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
REPORT_PATH = PROJECT_ROOT / "tools" / "endminm_comparable_capture_evidence.json"
CAPTURE_ROOT = PROJECT_ROOT / "scratch" / "character_recovery" / "endminm_common_camera_sweep_v4"
TARGET_PATH = CAPTURE_ROOT / "endminf_common_t0p133.png"
REFERENCE_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "settled" / "endmin_settled_frame10300.png"
MANIFEST_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "endminm_ui_recovery_manifest.json"
PREFAB_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Prefabs" / "Endminm.prefab"
START_CLIP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Animations" / "A_actor_endminm_ui_overview_start.anim"
LOOP_CLIP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Animations" / "A_actor_endminm_ui_overview_loop.anim"
CONTROLLER_AUDIT_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "overview_controller_native" / "controller_asset_audit.json"
CURRENT_CONTROLLER_SOURCE_PATH = REPO_ROOT / "export_full" / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "AnimatorController" / "AnimatorController#6197695_p3B3BD1391057D94F.json"
CAMERA_CONTRACT_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "OriginalData" / "CharInfoPresentation" / "charinfo_overview_camera_contract.json"
OVERVIEW_CAMERAS_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "charinfo_prefabs" / "overview_cameras.json"
VIEWER_SCENE_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Scenes" / "CharacterRecoveryViewer.unity"
PIPELINE_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "HGCompatRenderPipeline.asset"
BACKDROP_MATERIAL_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Shared" / "Materials" / "M_ReferenceBackdrop.mat"
CHARACTER_LIGHTING_PAYLOAD_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "OriginalData" / "RenderParameters" / "character_render_parameters.json"
OPERATOR_LIGHTING_PAYLOAD_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "OriginalData" / "RenderParameters" / "operator_lights.json"
MANIFEST_SETUP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldManifestCharacterSetup.cs"
PHASE_SWEEP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldRecoveredOverviewPhaseSweep.cs"
CHARACTER_LIGHTING_IMPORTER_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldOriginalRenderParameterImporter.cs"
OPERATOR_LIGHTING_IMPORTER_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldOriginalOperatorLightImporter.cs"
BACKGROUND_BUILDER_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldRecoveredCharInfoBackgroundPortraitBuilder.cs"
PROJECT_VERSION_PATH = PROJECT_ROOT / "ProjectSettings" / "ProjectVersion.txt"
UNITY_PATH = Path(r"D:\Program Files\2022.3.62f3\Editor\Unity.exe")
EXPECTED_UNITY_SHA256 = "02E80B2C1D7F983375C97B612655BE9F8ED852121E3A4EEDF1570701C48EA5CD"
EXPECTED_UNITY_VERSION = "2022.3.62f3 (96770f904ca7)"
EXPECTED_MANIFEST_SHA256 = "AFB49559DC470D1BE7C5DB1BF7054D49C432B18718E4B691F7951C3212EFDBF9"
EXPECTED_PREFAB_SHA256 = "E44CFBEB32E5F3B10C54B625951CB870AECCAB031215F35740092BFB9796BD7C"
EXPECTED_CONTROLLER_AUDIT_SHA256 = "FB1C7AE062299FCF22587AF20A0F40C0CAE2F7201B93D26EB5FD3A71F84C1E7D"
EXPECTED_CURRENT_CONTROLLER_SHA256 = "CE859C71F18ADF7D3CDF0CA0D37F62CDC5D6793CA0BB33B667FA6D78D0723792"
EXPECTED_CAMERA_CONTRACT_SHA256 = "F7DF587923FD848C828C44E39BF11A98F5376EB2DA73D7642EFCA10E40EB43A0"
EXPECTED_OVERVIEW_CAMERAS_SHA256 = "3EE6E8C448B240D111116C149FC161D24E3D1EFC0A3D8A89473C953F3AEA78CA"
EXPECTED_SIZE = (3840, 2160)
EXPECTED_FPS = 60.0
EXPECTED_LOOP_DURATION = 2.5
EXPECTED_SAMPLE_COUNT = 151
EXPECTED_TARGET_SAMPLE_TIME = 0.133
CHARACTER_BAND = (1400, 200, 2500, 2100)
MIN_TARGET_ECC = 0.80
MIN_MARGIN = 0.05
EXPECTED_CONTROLLER_SOURCE_ID = "5767187"
EXPECTED_CURRENT_CONTROLLER_SOURCE_ID = "6197695"
REJECTED_CONTROLLER_SOURCE_ID = "1476960"
EXPECTED_CAMERA_ID = "chr_0003_endmin_comparison"
EXPECTED_CAMERA_TEMPLATE = "chr_0003_endmin"
EXPECTED_LIGHTING_ACTOR = "Endminf"
EXPECTED_RENDER_TEXTURE = {
    "format": "ARGB32",
    "depthBits": 24,
    "antiAliasing": 1,
    "textureFormat": "RGBA32",
    "linear": False,
    "mipMaps": False,
}
COMMON_CAMERA = {
    "cameraId": EXPECTED_CAMERA_ID,
    "sourceTemplateId": EXPECTED_CAMERA_TEMPLATE,
    "position": [0.0, 0.998, 3.5],
    "rotation": [-0.000101754523, 0.999470794, 0.032376759, 0.0031411629],
    "fieldOfView": 20.0,
    "nearClipPlane": 0.1,
    "farClipPlane": 50.0,
}
SCHEMA = "endfield.character-recovery.common-camera-identity-sweep.v2"
STOP_TIME_RE = re.compile(r"^\s*m_StopTime:\s*([-+0-9.eE]+)\s*$", re.MULTILINE)
SAMPLE_RATE_RE = re.compile(r"^\s*m_SampleRate:\s*([-+0-9.eE]+)\s*$", re.MULTILINE)
SOURCE_ID_RE = re.compile(r"AnimatorController#([0-9]+)_")


class CaptureEvidenceError(RuntimeError):
    """Raised when common-camera capture evidence is stale or incomplete."""


_EXPECTED_REPORT_CACHE: dict[str, Any] | None = None


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 22), b""):
                total += len(chunk)
                digest.update(chunk)
    except OSError as error:
        raise CaptureEvidenceError(f"cannot hash {path}: {error}") from error
    return total, digest.hexdigest().upper()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix().replace("\\", "/")


def _file_evidence(path: Path, label: str, expected_hash: str | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise CaptureEvidenceError(f"{label} is missing: {path}")
    size, digest = _sha256(path)
    if expected_hash is not None and digest != expected_hash:
        raise CaptureEvidenceError(f"{label} hash mismatch: {digest} != {expected_hash}")
    return {"path": _relative(path), "bytes": size, "sha256": digest}


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CaptureEvidenceError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise CaptureEvidenceError(f"{label} must be a JSON object")
    return value


def _canonical_json_sha(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _close_list(actual: Any, expected: list[float], label: str, tolerance: float = 1e-7) -> None:
    if not isinstance(actual, list) or len(actual) != len(expected):
        raise CaptureEvidenceError(f"{label} is not {expected!r}: {actual!r}")
    for index, (value, target) in enumerate(zip(actual, expected)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise CaptureEvidenceError(f"{label}[{index}] is not finite: {value!r}")
        if abs(float(value) - target) > tolerance:
            raise CaptureEvidenceError(f"{label}[{index}] is {value!r}, expected {target!r}")


def _controller_evidence() -> dict[str, Any]:
    audit_file = _file_evidence(CONTROLLER_AUDIT_PATH, "controller audit", EXPECTED_CONTROLLER_AUDIT_SHA256)
    current_file = _file_evidence(
        CURRENT_CONTROLLER_SOURCE_PATH,
        "current original-data Endminm controller",
        EXPECTED_CURRENT_CONTROLLER_SHA256,
    )
    current_source = _json(CURRENT_CONTROLLER_SOURCE_PATH, "current original-data Endminm controller")
    current_name = current_source.get("m_Name")
    current_animestudio = current_source.get("$animestudio")
    if current_name != "chr_0002_endminm_controller" or not isinstance(current_animestudio, dict):
        raise CaptureEvidenceError(
            f"current controller source is not exact Endminm: m_Name={current_name!r}"
        )
    current_container_name = str(current_animestudio.get("name", ""))
    if current_container_name != f"AnimatorController#{EXPECTED_CURRENT_CONTROLLER_SOURCE_ID}":
        raise CaptureEvidenceError(
            f"current controller container ID is stale: {current_container_name!r}"
        )
    audit = _json(CONTROLLER_AUDIT_PATH, "controller audit")
    rows = [row for row in audit.get("actors", []) if isinstance(row, dict) and row.get("character_id") == "chr_0002_endminm"]
    if len(rows) != 1:
        raise CaptureEvidenceError(f"controller audit has {len(rows)} Endminm rows")
    row = rows[0]
    overview = row.get("main_overview")
    if not isinstance(overview, dict):
        raise CaptureEvidenceError("Endminm controller audit has no main_overview")
    source_json = str(overview.get("source_json", ""))
    source_match = SOURCE_ID_RE.search(source_json)
    if source_match is None or source_match.group(1) != EXPECTED_CONTROLLER_SOURCE_ID:
        raise CaptureEvidenceError(
            f"Endminm controller source ID is not #{EXPECTED_CONTROLLER_SOURCE_ID}: {source_json!r}"
        )
    if REJECTED_CONTROLLER_SOURCE_ID in source_json:
        raise CaptureEvidenceError("unproven controller source ID #1476960 was substituted")
    expected = {
        "controller_name": "chr_0002_endminm_controller",
        "start_clip": "A_actor_endminm_ui_overview_start",
        "loop_clip": "A_actor_endminm_ui_overview_loop",
    }
    if any(overview.get(key) != value for key, value in expected.items()):
        raise CaptureEvidenceError(f"Endminm controller clip contract mismatch: {overview}")
    manifest = _json(MANIFEST_PATH, "Endminm source manifest")
    recovery = manifest.get("animation_controller_recovery")
    playback = manifest.get("overview_playback")
    if not isinstance(recovery, dict) or not isinstance(playback, dict):
        raise CaptureEvidenceError("Endminm manifest lacks animation_controller_recovery")
    manifest_sources = [
        recovery.get("main_controller_source_json"),
        playback.get("controller_source_json"),
    ]
    if any(not isinstance(value, str) or not value for value in manifest_sources):
        raise CaptureEvidenceError("Endminm manifest controller source claims are incomplete")
    manifest_ids = [match.group(1) for value in manifest_sources for match in [SOURCE_ID_RE.search(value)] if match]
    if manifest_ids != [REJECTED_CONTROLLER_SOURCE_ID, REJECTED_CONTROLLER_SOURCE_ID]:
        raise CaptureEvidenceError(
            "Endminm manifest controller claim changed: " + repr(manifest_sources)
        )
    return audit_file | {
        "currentOriginalDataController": current_file | {
            "containerId": EXPECTED_CURRENT_CONTROLLER_SOURCE_ID,
            "name": current_name,
            "rawDataSha256": current_animestudio.get("rawDataSha256"),
        },
        "characterId": row.get("character_id"),
        "actorToken": row.get("actor_token"),
        "controllerName": overview.get("controller_name"),
        "sourceJson": source_json,
        "sourceContainerId": EXPECTED_CONTROLLER_SOURCE_ID,
        "rejectedManifestSourceContainerId": REJECTED_CONTROLLER_SOURCE_ID,
        "manifestClaimedSourceJson": manifest_sources,
        "manifestClaimDisposition": "conflict_only_not_used_for_capture",
        "mainOverviewSha256": _canonical_json_sha(overview),
        "startClip": overview.get("start_clip"),
        "loopClip": overview.get("loop_clip"),
        "entryNormalizedOffset": overview.get("entry_normalized_offset"),
        "exitNormalizedTime": overview.get("exit_normalized_time"),
        "transitionDuration": overview.get("transition_duration"),
        "destinationNormalizedOffset": overview.get("destination_normalized_offset"),
    }


def _camera_evidence() -> dict[str, Any]:
    contract_file = _file_evidence(CAMERA_CONTRACT_PATH, "camera contract", EXPECTED_CAMERA_CONTRACT_SHA256)
    cameras_file = _file_evidence(OVERVIEW_CAMERAS_PATH, "overview cameras", EXPECTED_OVERVIEW_CAMERAS_SHA256)
    contract = _json(CAMERA_CONTRACT_PATH, "camera contract")
    entry = ((contract.get("characters") or {}).get("chr_0003_endmin"))
    if not isinstance(entry, dict) or entry.get("track") != "track_chr_0003_endmin" or entry.get("actor") != "endmin":
        raise CaptureEvidenceError("camera contract lacks exact Endminf target track")
    _close_list(entry.get("vcamOverview", {}).get("localPosition"), COMMON_CAMERA["position"], "Endminf vcam position")
    serialized_rotation = entry.get("vcamOverview", {}).get("localRotation")
    if not isinstance(serialized_rotation, list) or len(serialized_rotation) != 4:
        raise CaptureEvidenceError("Endminf vcam serialized rotation is missing")
    lens = entry.get("lens") or {}
    for key, expected in (("fieldOfView", 20.0), ("nearClipPlane", 0.1), ("farClipPlane", 50.0)):
        if float(lens.get(key, float("nan"))) != expected:
            raise CaptureEvidenceError(f"Endminf camera lens {key} is stale: {lens.get(key)!r}")
    cameras = _json(OVERVIEW_CAMERAS_PATH, "overview cameras")
    track = cameras.get("track_chr_0003_endmin")
    if not isinstance(track, dict):
        raise CaptureEvidenceError("overview cameras lacks track_chr_0003_endmin")
    return {
        "contract": contract_file | {
            "track": entry.get("track"),
            "actor": entry.get("actor"),
            "entry": entry,
            "serializedRotation": serialized_rotation,
            "comparisonRotationDerivation": "Quaternion.LookRotation(lookAt - position), pinned in common camera override",
        },
        "overviewCameras": cameras_file | {"track": "track_chr_0003_endmin", "entry": track},
    }


def _clip_contract() -> dict[str, Any]:
    try:
        start_text = START_CLIP_PATH.read_text(encoding="utf-8", errors="replace")
        loop_text = LOOP_CLIP_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise CaptureEvidenceError(f"cannot read Endminm clips: {error}") from error
    stop_match = STOP_TIME_RE.search(loop_text)
    rate_match = SAMPLE_RATE_RE.search(loop_text)
    if stop_match is None or rate_match is None:
        raise CaptureEvidenceError("Endminm loop clip lacks stop time/sample rate")
    stop_time = float(stop_match.group(1))
    sample_rate = float(rate_match.group(1))
    if stop_time != EXPECTED_LOOP_DURATION or sample_rate != EXPECTED_FPS:
        raise CaptureEvidenceError(f"Endminm loop timing changed: rate={sample_rate}, stop={stop_time}")
    if "A_actor_endminm_ui_overview_start" not in start_text:
        raise CaptureEvidenceError("Endminm start clip name is stale")
    return {
        "overviewStartClip": _file_evidence(START_CLIP_PATH, "Endminm overview start clip"),
        "overviewLoopClip": _file_evidence(LOOP_CLIP_PATH, "Endminm overview loop clip"),
        "sampleRate": sample_rate,
        "durationSeconds": stop_time,
    }


def _image_info(path: Path, label: str, expected_channels: int = 4) -> tuple[dict[str, Any], Any]:
    evidence = _file_evidence(path, label)
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None or image.ndim != 3 or image.shape[:2] != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]) or image.shape[2] != expected_channels:
        raise CaptureEvidenceError(f"{label} is not {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]} RGBA")
    return evidence | {
        "width": EXPECTED_SIZE[0],
        "height": EXPECTED_SIZE[1],
        "channels": expected_channels,
        "format": "PNG RGBA",
    }, image


def _ecc(reference_gray: Any, image: Any, label: str) -> float:
    x0, y0, x1, y1 = CHARACTER_BAND
    gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype("float32")
    warp = cv2.getRotationMatrix2D((reference_gray.shape[1] / 2.0, reference_gray.shape[0] / 2.0), 0.0, 1.0).astype("float32")
    warp[:, 2] = 0.0
    try:
        value, _ = cv2.findTransformECC(
            reference_gray,
            gray,
            warp,
            cv2.MOTION_TRANSLATION,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-6),
            inputMask=None,
            gaussFiltSize=5,
        )
    except cv2.error as error:
        raise CaptureEvidenceError(f"could not compute ECC for {label}: {error}") from error
    value = float(value)
    if not math.isfinite(value):
        raise CaptureEvidenceError(f"ECC for {label} is not finite")
    return round(value, 6)


def _sample_times() -> list[float]:
    return [round(index / EXPECTED_FPS, 6) for index in range(EXPECTED_SAMPLE_COUNT)]


def _sample_file(time_seconds: float) -> Path:
    return CAPTURE_ROOT / (
        "endminm_common_sweep_t" +
        f"{time_seconds:.3f}".replace(".", "p") + ".png"
    )


def _common_render_contract() -> dict[str, Any]:
    camera = _camera_evidence()
    return {
        "camera": {
            "id": EXPECTED_CAMERA_ID,
            "sourceTemplateId": EXPECTED_CAMERA_TEMPLATE,
            "sourceTrack": "track_chr_0003_endmin",
            "source": camera,
            "override": COMMON_CAMERA,
            "overrideSha256": _canonical_json_sha(COMMON_CAMERA),
            "sameTransformFor": ["chr_0003_endminf", "chr_0002_endminm"],
        },
        "scene": _file_evidence(VIEWER_SCENE_PATH, "shared viewer scene"),
        "pipeline": _file_evidence(PIPELINE_PATH, "HGCompatRenderPipeline asset"),
        "backdropMaterial": _file_evidence(BACKDROP_MATERIAL_PATH, "shared backdrop material"),
        "lighting": {
            "characterProfileActor": EXPECTED_LIGHTING_ACTOR,
            "characterRenderParameters": _file_evidence(CHARACTER_LIGHTING_PAYLOAD_PATH, "character lighting payload"),
            "operatorLights": _file_evidence(OPERATOR_LIGHTING_PAYLOAD_PATH, "operator lighting payload"),
            "characterImporter": _file_evidence(CHARACTER_LIGHTING_IMPORTER_PATH, "character lighting importer"),
            "operatorImporter": _file_evidence(OPERATOR_LIGHTING_IMPORTER_PATH, "operator lighting importer"),
        },
        "captureHarness": {
            "setup": _file_evidence(MANIFEST_SETUP_PATH, "common capture setup"),
            "phaseSweep": _file_evidence(PHASE_SWEEP_PATH, "phase sweep harness"),
            "backgroundBuilder": _file_evidence(BACKGROUND_BUILDER_PATH, "background builder"),
            "unityEditor": _file_evidence(UNITY_PATH, "Unity editor", EXPECTED_UNITY_SHA256) | {"version": EXPECTED_UNITY_VERSION},
            "projectVersion": _file_evidence(PROJECT_VERSION_PATH, "Unity project version"),
            "unityMethod": "EndfieldGraphShaderLabEditor.EndfieldRecoveredOverviewPhaseSweep.RenderFromEnvironment",
            "sceneReuse": "ENDFIELD_PHASE_SWEEP_REUSE_SCENE=1",
            "sampleSchedule": "sampleIndex=0..150 inclusive; sampleTimeSeconds=sampleIndex/60; both 0 and 2.5 endpoints included",
            "sweepOutputDirectory": "unity_endfield_graph_shader_lab/scratch/character_recovery/endminm_common_camera_sweep_v4",
            "sweepStem": "endminm_common_sweep",
            "targetStem": "endminf_common_t0p133",
        },
        "environment": {
            "phaseSweepReuseScene": True,
            "comparisonCameraId": EXPECTED_CAMERA_ID,
            "comparisonLightingActor": EXPECTED_LIGHTING_ACTOR,
            "fittedCompositorTranslation": False,
            "approximateOperatorLighting": False,
            "recoveredClusteredNprLightLoop": False,
            "recoveredLightBinningMembership": False,
            "recoveredIsolatedPunctualSoftShadows": False,
            "recoveredPunctualShadowTileResolution": 1024,
            "recoveredPostExposureEV": None,
        },
        "renderSettings": {
            "resolution": list(EXPECTED_SIZE),
            "fps": EXPECTED_FPS,
            "renderTexture": EXPECTED_RENDER_TEXTURE,
            "crop": {"characterBand": list(CHARACTER_BAND), "alignment": "ECC translation over pinned character band"},
        },
    }


def build_report() -> dict[str, Any]:
    reference_evidence = _file_evidence(REFERENCE_PATH, "Endminf settled reference")
    reference_image = cv2.imread(str(REFERENCE_PATH), cv2.IMREAD_COLOR)
    if reference_image is None or reference_image.shape[:2] != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]) or reference_image.ndim != 3 or reference_image.shape[2] != 3:
        raise CaptureEvidenceError("Endminf settled reference is not 3840x2160 RGB")
    x0, y0, x1, y1 = CHARACTER_BAND
    reference_gray = cv2.cvtColor(reference_image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype("float32")

    controller = _controller_evidence()
    clip = _clip_contract()
    manifest = _file_evidence(MANIFEST_PATH, "Endminm source manifest", EXPECTED_MANIFEST_SHA256)
    prefab = _file_evidence(PREFAB_PATH, "Endminm prefab", EXPECTED_PREFAB_SHA256)
    target_info, target_image = _image_info(TARGET_PATH, "Endminf common-camera target")
    target_score = _ecc(reference_gray, target_image, "Endminf common-camera target")

    expected_times = _sample_times()
    expected_names = {_sample_file(time).name for time in expected_times}
    actual_png_names = {path.name for path in CAPTURE_ROOT.glob("*.png")}
    expected_png_names = expected_names | {TARGET_PATH.name}
    if actual_png_names != expected_png_names:
        missing = sorted(expected_png_names - actual_png_names)
        extra = sorted(actual_png_names - expected_png_names)
        raise CaptureEvidenceError(f"common-camera sweep PNG set mismatch: missing={missing[:3]}, extra={extra[:3]}")

    sweep = []
    for index, time_seconds in enumerate(expected_times):
        path = _sample_file(time_seconds)
        info, image = _image_info(path, f"Endminm sweep sample {index}")
        score = _ecc(reference_gray, image, f"Endminm sweep sample {index}")
        sweep.append({
            "index": index,
            "timeSeconds": time_seconds,
            "path": info["path"],
            "bytes": info["bytes"],
            "sha256": info["sha256"],
            "width": info["width"],
            "height": info["height"],
            "channels": info["channels"],
            "format": info["format"],
            "eccTranslation": score,
        })
    if [row["index"] for row in sweep] != list(range(EXPECTED_SAMPLE_COUNT)) or [row["timeSeconds"] for row in sweep] != expected_times:
        raise CaptureEvidenceError("common-camera sweep rows are not contiguous and ordered")
    best = max(sweep, key=lambda row: (row["eccTranslation"], -row["index"]))
    return {
        "schema": SCHEMA,
        "status": "ok",
        "pathBase": "repo_root",
        "identity": {
            "target": {"characterId": "chr_0003_endminf", "actorToken": "endminf"},
            "competitor": {"characterId": "chr_0002_endminm", "actorToken": "endminm"},
        },
        "sourceAssets": {
            "manifest": manifest,
            "prefab": prefab,
            "controllerAudit": controller,
            "overviewStartClip": clip["overviewStartClip"],
            "overviewLoopClip": clip["overviewLoopClip"],
            "camera": _common_render_contract()["camera"],
        },
        "controllerSourceResolution": {
            "auditReportedSourceContainerId": EXPECTED_CONTROLLER_SOURCE_ID,
            "manifestClaimedSourceContainerId": REJECTED_CONTROLLER_SOURCE_ID,
            "currentExportContentContainerId": EXPECTED_CURRENT_CONTROLLER_SOURCE_ID,
            "captureControllerEvidence": "current export content m_Name=chr_0002_endminm_controller plus controller audit #5767187; manifest #1476960 is retained as a conflicting claim and is not substituted",
        },
        "commonRenderContract": _common_render_contract(),
        "comparison": {
            "reference": reference_evidence | {"frame": 10300, "dimensions": list(EXPECTED_SIZE), "format": "PNG RGB"},
            "targetRender": target_info | {"sampleTimeSeconds": EXPECTED_TARGET_SAMPLE_TIME, "eccTranslation": target_score},
            "targetScore": target_score,
            "competitorScore": best["eccTranslation"],
            "competitorBestIndex": best["index"],
            "competitorBestTimeSeconds": best["timeSeconds"],
            "targetMargin": round(target_score - best["eccTranslation"], 6),
            "minimumTargetScore": MIN_TARGET_ECC,
            "minimumMargin": MIN_MARGIN,
            "sameCameraContract": True,
            "sameRenderSettingsContract": True,
            "cameraTrack": "track_chr_0003_endmin",
            "resolution": list(EXPECTED_SIZE),
            "scoreMetric": "ECC translation over pinned Endminf settled character band",
            "renderTexture": EXPECTED_RENDER_TEXTURE,
            "sweep": {
                "actor": "Endminm",
                "clip": "A_actor_endminm_ui_overview_loop",
                "sampleRate": EXPECTED_FPS,
                "durationSeconds": EXPECTED_LOOP_DURATION,
                "stepSeconds": round(1.0 / EXPECTED_FPS, 6),
                "sampleCount": EXPECTED_SAMPLE_COUNT,
                "includeStartEndpoint": True,
                "includeEndEndpoint": True,
                "endpointPolicy": "inclusive_0_to_stop_time_at_source_sample_rate",
                "rows": sweep,
            },
        },
        "admission": {
            "sameCamera": True,
            "sameRenderSettings": True,
            "sweepComplete": len(sweep) == EXPECTED_SAMPLE_COUNT,
            "targetScoreAboveThreshold": target_score > MIN_TARGET_ECC,
            "marginSatisfied": target_score > MIN_TARGET_ECC and target_score - best["eccTranslation"] >= MIN_MARGIN,
            "status": "proven" if target_score > MIN_TARGET_ECC and target_score - best["eccTranslation"] >= MIN_MARGIN else "candidate",
            "matteCandidateAllowed": target_score > MIN_TARGET_ECC and target_score - best["eccTranslation"] >= MIN_MARGIN,
        },
    }


def _canonical_report() -> dict[str, Any]:
    global _EXPECTED_REPORT_CACHE
    if _EXPECTED_REPORT_CACHE is None:
        _EXPECTED_REPORT_CACHE = build_report()
    return _EXPECTED_REPORT_CACHE


def check_report(path: Path = REPORT_PATH) -> dict[str, Any]:
    expected = _canonical_report()
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CaptureEvidenceError(f"cannot read durable common-camera evidence: {error}") from error
    if actual != expected:
        raise CaptureEvidenceError("durable common-camera evidence is stale; run --write")
    return actual


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write durable common-camera evidence")
    parser.add_argument("--check", action="store_true", help="rebuild and compare durable common-camera evidence")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    try:
        report = _canonical_report()
        if args.check:
            check_report(args.report)
            print(f"common-camera Endminf/Endminm evidence verified: {args.report}")
        else:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.report.with_suffix(".partial.json")
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(args.report)
            print(f"common-camera Endminf/Endminm evidence written: {args.report}")
        comparison = report["comparison"]
        print(
            f"target={comparison['targetScore']} competitorMax={comparison['competitorScore']} "
            f"margin={comparison['targetMargin']} samples={comparison['sweep']['sampleCount']} "
            f"status={report['admission']['status']}"
        )
        return 0
    except CaptureEvidenceError as error:
        print(f"common-camera identity evidence failed: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
