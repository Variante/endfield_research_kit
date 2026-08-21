"""Validate and record the pinned Endminm identity-comparison render.

The render is produced by the existing Unity
``EndfieldRecoveredOverviewPhaseSweep.RenderFromEnvironment`` harness at the
same 3840x2160 ``t=0.133`` loop sample used by the Endminf ECC comparison.
This tool never starts Unity and never writes the PNG; it rebuilds all small
JSON/hash/score evidence around the existing scratch render and is therefore
safe for audit checkers and hostile mutation tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
REPORT_PATH = PROJECT_ROOT / "tools" / "endminm_comparable_capture_evidence.json"
CAPTURE_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "endminm_comparable_capture" / "endminm_candidate_t0p133.png"
REFERENCE_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "settled" / "endmin_settled_frame10300.png"
MANIFEST_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "endminm_ui_recovery_manifest.json"
PREFAB_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Prefabs" / "Endminm.prefab"
START_CLIP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Animations" / "A_actor_endminm_ui_overview_start.anim"
LOOP_CLIP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "Characters" / "Playable" / "Endminm" / "Animations" / "A_actor_endminm_ui_overview_loop.anim"
CONTROLLER_AUDIT_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "overview_controller_native" / "controller_asset_audit.json"
CAMERA_CONTRACT_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Generated" / "OriginalData" / "CharInfoPresentation" / "charinfo_overview_camera_contract.json"
OVERVIEW_CAMERAS_PATH = PROJECT_ROOT / "scratch" / "character_recovery" / "gameplay_reference" / "charinfo_prefabs" / "overview_cameras.json"
PHASE_SWEEP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldRecoveredOverviewPhaseSweep.cs"
RENDER_SETUP_PATH = PROJECT_ROOT / "Assets" / "EndfieldGraphShaderLab" / "Editor" / "CharacterRecovery" / "EndfieldManifestCharacterSetup.cs"
PROJECT_VERSION_PATH = PROJECT_ROOT / "ProjectSettings" / "ProjectVersion.txt"
UNITY_PATH = Path(r"D:\Program Files\2022.3.62f3\Editor\Unity.exe")
TARGET_RENDER_PATH = REPO_ROOT / "scratch" / "charinfo_phase_sweep" / "endmin_t0p133.png"
EXPECTED_CAPTURE_SHA256 = "F306E6998D96661C4B6044B2B3B83637FE8CA77594A1993E8C8E9E3E6F519B88"
EXPECTED_TARGET_RENDER_SHA256 = "112EEF6858F7DDB8209BFFA546E861E4843FD4084DD9B9EBD9D36BF286E2B90D"
EXPECTED_REFERENCE_SHA256 = "2167B9754703B3AA40AD6C573ADCF77339A422E1AF455AB66B4ADB64F467531F"
EXPECTED_MANIFEST_SHA256 = "AFB49559DC470D1BE7C5DB1BF7054D49C432B18718E4B691F7951C3212EFDBF9"
EXPECTED_PREFAB_SHA256 = "E44CFBEB32E5F3B10C54B625951CB870AECCAB031215F35740092BFB9796BD7C"
EXPECTED_CONTROLLER_AUDIT_SHA256 = "FB1C7AE062299FCF22587AF20A0F40C0CAE2F7201B93D26EB5FD3A71F84C1E7D"
EXPECTED_CAMERA_CONTRACT_SHA256 = "F7DF587923FD848C828C44E39BF11A98F5376EB2DA73D7642EFCA10E40EB43A0"
EXPECTED_OVERVIEW_CAMERAS_SHA256 = "3EE6E8C448B240D111116C149FC161D24E3D1EFC0A3D8A89473C953F3AEA78CA"
EXPECTED_UNITY_SHA256 = "02E80B2C1D7F983375C97B612655BE9F8ED852121E3A4EEDF1570701C48EA5CD"
EXPECTED_SAMPLE_TIME = 0.133
EXPECTED_SIZE = (3840, 2160)
CHARACTER_BAND = (1400, 200, 2500, 2100)
SCHEMA = "endfield.character-recovery.endminm-comparable-capture.v1"


class CaptureEvidenceError(RuntimeError):
    """Raised when the comparable Endminm render is stale or incomplete."""


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


def _controller_evidence() -> dict[str, Any]:
    audit_file = _file_evidence(CONTROLLER_AUDIT_PATH, "controller audit", EXPECTED_CONTROLLER_AUDIT_SHA256)
    audit = _json(CONTROLLER_AUDIT_PATH, "controller audit")
    rows = [row for row in audit.get("actors", []) if isinstance(row, dict) and row.get("character_id") == "chr_0002_endminm"]
    if len(rows) != 1:
        raise CaptureEvidenceError(f"controller audit has {len(rows)} Endminm rows")
    row = rows[0]
    overview = row.get("main_overview")
    if not isinstance(overview, dict):
        raise CaptureEvidenceError("Endminm controller audit has no main_overview")
    expected = {
        "controller_name": "chr_0002_endminm_controller",
        "start_clip": "A_actor_endminm_ui_overview_start",
        "loop_clip": "A_actor_endminm_ui_overview_loop",
    }
    if any(overview.get(key) != value for key, value in expected.items()):
        raise CaptureEvidenceError(f"Endminm controller clip contract mismatch: {overview}")
    return audit_file | {
        "characterId": row.get("character_id"),
        "actorToken": row.get("actor_token"),
        "controllerName": overview.get("controller_name"),
        "sourceJson": overview.get("source_json"),
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
    entry = ((contract.get("characters") or {}).get("chr_0002_endminm"))
    if not isinstance(entry, dict) or entry.get("track") != "track_chr_0002_endminm":
        raise CaptureEvidenceError("camera contract lacks exact chr_0002_endminm track")
    cameras = _json(OVERVIEW_CAMERAS_PATH, "overview cameras")
    track = cameras.get("track_chr_0002_endminm")
    if not isinstance(track, dict):
        raise CaptureEvidenceError("overview cameras lacks track_chr_0002_endminm")
    if entry.get("actor") != "endminm":
        raise CaptureEvidenceError("camera contract actor is not endminm")
    return {
        "contract": contract_file | {"track": entry.get("track"), "actor": entry.get("actor"), "entry": entry},
        "overviewCameras": cameras_file | {"track": entry.get("track"), "entry": track},
    }


def _score(reference: Path, render: Path) -> float:
    reference_image = cv2.imread(str(reference), cv2.IMREAD_COLOR)
    render_image = cv2.imread(str(render), cv2.IMREAD_COLOR)
    if reference_image is None or render_image is None or reference_image.shape != render_image.shape:
        raise CaptureEvidenceError("reference and Endminm render dimensions do not match")
    x0, y0, x1, y1 = CHARACTER_BAND
    ref_gray = cv2.cvtColor(reference_image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype("float32")
    render_gray = cv2.cvtColor(render_image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY).astype("float32")
    warp = cv2.getRotationMatrix2D((ref_gray.shape[1] / 2.0, ref_gray.shape[0] / 2.0), 0.0, 1.0).astype("float32")
    warp[:, 2] = 0.0
    try:
        value, _ = cv2.findTransformECC(
            ref_gray,
            render_gray,
            warp,
            cv2.MOTION_TRANSLATION,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-6),
            inputMask=None,
            gaussFiltSize=5,
        )
    except cv2.error as error:
        raise CaptureEvidenceError(f"could not compute Endminm ECC: {error}") from error
    return round(float(value), 6)


def build_report() -> dict[str, Any]:
    capture = _file_evidence(CAPTURE_PATH, "Endminm comparable capture", EXPECTED_CAPTURE_SHA256)
    target_render = _file_evidence(TARGET_RENDER_PATH, "Endminf target render", EXPECTED_TARGET_RENDER_SHA256)
    reference = _file_evidence(REFERENCE_PATH, "Endminf settled reference", EXPECTED_REFERENCE_SHA256)
    capture_image = cv2.imread(str(CAPTURE_PATH), cv2.IMREAD_UNCHANGED)
    target_image = cv2.imread(str(TARGET_RENDER_PATH), cv2.IMREAD_UNCHANGED)
    reference_image = cv2.imread(str(REFERENCE_PATH), cv2.IMREAD_UNCHANGED)
    if capture_image is None or capture_image.shape[:2] != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]) or capture_image.ndim != 3 or capture_image.shape[2] != 4:
        raise CaptureEvidenceError("Endminm comparable capture is not 3840x2160 RGBA")
    if target_image is None or target_image.shape[:2] != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]) or target_image.ndim != 3 or target_image.shape[2] != 4:
        raise CaptureEvidenceError("Endminf target render is not 3840x2160 RGBA")
    if reference_image is None or reference_image.shape[:2] != (EXPECTED_SIZE[1], EXPECTED_SIZE[0]) or reference_image.ndim != 3 or reference_image.shape[2] != 3:
        raise CaptureEvidenceError("Endminf settled reference is not 3840x2160 RGB")
    manifest = _file_evidence(MANIFEST_PATH, "Endminm source manifest", EXPECTED_MANIFEST_SHA256)
    prefab = _file_evidence(PREFAB_PATH, "Endminm prefab", EXPECTED_PREFAB_SHA256)
    start_clip = _file_evidence(START_CLIP_PATH, "Endminm overview start clip")
    loop_clip = _file_evidence(LOOP_CLIP_PATH, "Endminm overview loop clip")
    controller = _controller_evidence()
    cameras = _camera_evidence()
    phase_sweep = _file_evidence(PHASE_SWEEP_PATH, "phase sweep harness")
    render_setup = _file_evidence(RENDER_SETUP_PATH, "runtime render setup")
    project_version = _file_evidence(PROJECT_VERSION_PATH, "Unity project version")
    unity = _file_evidence(UNITY_PATH, "Unity editor", EXPECTED_UNITY_SHA256) | {"version": "2022.3.62f3 (96770f904ca7)"}
    score = _score(REFERENCE_PATH, CAPTURE_PATH)
    if not math.isfinite(score):
        raise CaptureEvidenceError("Endminm ECC score is not finite")
    return {
        "schema": SCHEMA,
        "status": "ok",
        "pathBase": "repo_root",
        "identity": {"characterId": "chr_0002_endminm", "actorToken": "endminm", "displayName": "Endministrator (endminm)"},
        "capture": {
            "method": "EndfieldGraphShaderLabEditor.EndfieldRecoveredOverviewPhaseSweep.RenderFromEnvironment",
            "phaseSweepScript": phase_sweep,
            "renderSetupScript": render_setup,
            "unityEditor": unity,
            "projectVersion": project_version,
            "environment": {
                "actor": "Endminm",
                "clip": "A_actor_endminm_ui_overview_loop",
                "timesSeconds": [EXPECTED_SAMPLE_TIME],
                "stem": "endminm_candidate",
            },
            "output": capture | {"width": EXPECTED_SIZE[0], "height": EXPECTED_SIZE[1], "channels": 4, "format": "PNG RGBA"},
        },
        "sourceAssets": {
            "manifest": manifest,
            "prefab": prefab,
            "controllerAudit": controller,
            "overviewStartClip": start_clip,
            "overviewLoopClip": loop_clip,
            "camera": cameras,
        },
        "comparison": {
            "reference": reference | {"frame": 10300, "dimensions": list(EXPECTED_SIZE), "format": "PNG RGB"},
            "targetRender": target_render | {"dimensions": list(EXPECTED_SIZE), "format": "PNG RGBA", "sampleTimeSeconds": EXPECTED_SAMPLE_TIME},
            "cameraTrack": "track_chr_0002_endminm",
            "cameraContractTemplateId": "chr_0002_endminm",
            "sameCameraContract": True,
            "sameRenderSettingsContract": True,
            "resolution": list(EXPECTED_SIZE),
            "renderTexture": {"format": "ARGB32", "depthBits": 24, "antiAliasing": 1, "textureFormat": "RGBA32", "linear": False, "mipMaps": False},
            "alignment": "ECC translation over pinned character band",
            "characterBand": list(CHARACTER_BAND),
            "sampleTimeSeconds": EXPECTED_SAMPLE_TIME,
            "eccTranslation": score,
            "scoreMetric": "ECC translation over pinned Endminf settled character band",
        },
        "publication": {
            "comparableCompetitorAllowed": True,
            "reason": "same harness, resolution, render target contract, and actor-specific overview camera contract are pinned",
        },
    }


def check_report(path: Path = REPORT_PATH) -> dict[str, Any]:
    expected = build_report()
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CaptureEvidenceError(f"cannot read durable Endminm capture evidence: {error}") from error
    if actual != expected:
        raise CaptureEvidenceError("durable Endminm capture evidence is stale; run --write")
    return actual


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write durable capture evidence")
    parser.add_argument("--check", action="store_true", help="rebuild and compare durable capture evidence")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args(argv)
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    try:
        report = build_report()
        if args.check:
            check_report(args.report)
            print(f"Endminm comparable capture verified: {args.report}")
        else:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.report.with_suffix(".partial.json")
            temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(args.report)
            print(f"Endminm comparable capture evidence written: {args.report}")
        print(f"ecc={report['comparison']['eccTranslation']} render={report['capture']['output']['sha256']}")
        return 0
    except CaptureEvidenceError as error:
        print(f"Endminm comparable capture evidence failed: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
