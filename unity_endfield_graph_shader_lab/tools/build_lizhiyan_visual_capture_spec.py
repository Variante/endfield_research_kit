#!/usr/bin/env python3
"""Build a fail-closed deterministic Li Zhiyan visual comparison spec."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
ORACLE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_retail_visual_oracle.json"
)
ALIGNMENT = ORACLE.with_name("lizhiyan_overview_timing_alignment.json")
OUTPUT = ORACLE.with_name("lizhiyan_visual_capture_spec.json")

SCHEMA = "endfield.lizhiyan-visual-capture-spec.v1"
RESTART_PTS = 37967
ORACLE_SAMPLE_PTS = (38000, 40000, 42000, 43000, 44000, 46000)
ORACLE_TRANSITION_PTS = (37667, 37683, 37700, 37950, 37967, 38167, 38183)
MINIMAL_CAPTURE_PTS = (
    37967,
    38000,
    38167,
    38183,
    39934,
    40000,
    40167,
    40834,
    40867,
    41967,
    42000,
    42467,
    42967,
    43000,
    43900,
    44000,
    44334,
    44967,
    46000,
)
EFFECT_LIFETIMES = {
    "P_fxui_lizhiyan_overview_start_01": 2.2,
    "P_fxui_lizhiyan_overview_start_02": 5.0,
    "P_fxui_lizhiyan_overview_start_03": 7.0,
}
CAPTURE_PHASES = {
    37967: "candidate_restart",
    38000: "lizhiyan_transition_visible_pre_distinct_teal",
    38167: "start_01_first_dynamic_key_candidate",
    38183: "start_01_first_unambiguous_teal_slab",
    39934: "start_01_last_dynamic_key_candidate",
    40000: "broad_teal_peak",
    40167: "start_01_lifetime_end",
    40834: "start_02_first_dynamic_key_candidate_path_3",
    40867: "start_02_first_dynamic_key_candidate_paths_0_1",
    41967: "start_02_last_dynamic_key",
    42000: "broad_effect_late",
    42467: "start_03_next_material_wave",
    42967: "start_02_lifetime_end",
    43000: "compact_teal_trail",
    43900: "start_03_tail_dynamic_key",
    44000: "trail_decay",
    44334: "shared_material_clip_end_nearest_frame",
    44967: "start_03_lifetime_end",
    46000: "settled_no_substantial_teal",
}


class CaptureSpecError(RuntimeError):
    """Raised when a source contract is missing or has drifted."""


def require(value: bool, check: str, expected: Any, actual: Any) -> None:
    if not value:
        raise CaptureSpecError(
            f"validator=lizhiyan_visual_capture_spec; check={check}; "
            f"expected={expected}; actual={actual}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), "input_exists", True, path)
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "input_object", True, type(value).__name__)
    return value


def resolve_repo_path(relative_path: str) -> Path:
    candidate = (REPO / relative_path).resolve()
    try:
        candidate.relative_to(REPO.resolve())
    except ValueError as exc:
        raise CaptureSpecError(
            f"validator=lizhiyan_visual_capture_spec; check=source_under_repo; "
            f"expected={REPO}; actual={candidate}"
        ) from exc
    return candidate


def validate_oracle(oracle: dict[str, Any]) -> dict[str, Any]:
    require(oracle.get("schema") == "endfield.lizhiyan-retail-visual-oracle.v1", "oracle_schema", "endfield.lizhiyan-retail-visual-oracle.v1", oracle.get("schema"))
    require(oracle.get("status") == "diagnostic_only", "oracle_status", "diagnostic_only", oracle.get("status"))
    require(oracle.get("visibleAdmission") is False, "oracle_visible_admission", False, oracle.get("visibleAdmission"))
    source = oracle.get("source")
    require(isinstance(source, dict), "oracle_source_object", True, type(source).__name__)
    require(source.get("dimensions") == [3840, 2160], "oracle_dimensions", [3840, 2160], source.get("dimensions"))
    require(source.get("timeBase") == "1/1000", "oracle_time_base", "1/1000", source.get("timeBase"))
    require(oracle.get("decode", {}).get("pixelFormat") == "rgb24", "oracle_pixel_format", "rgb24", oracle.get("decode", {}).get("pixelFormat"))
    require(oracle.get("decode", {}).get("scaledDimensions") == [960, 540], "oracle_scaled_dimensions", [960, 540], oracle.get("decode", {}).get("scaledDimensions"))
    require(oracle.get("decode", {}).get("exactInputPts") is True, "oracle_exact_input_pts", True, oracle.get("decode", {}).get("exactInputPts"))
    sample_pts = tuple(int(row["pts"]) for row in oracle.get("samples", []))
    require(sample_pts == ORACLE_SAMPLE_PTS, "oracle_sample_pts", ORACLE_SAMPLE_PTS, sample_pts)
    transition_pts = tuple(int(row["pts"]) for row in oracle.get("transitionAnchors", []))
    require(transition_pts == ORACLE_TRANSITION_PTS, "oracle_transition_pts", ORACLE_TRANSITION_PTS, transition_pts)
    boundary = oracle.get("transitionBoundary", {})
    require(boundary.get("candidateRestartPts") == RESTART_PTS, "oracle_candidate_restart", RESTART_PTS, boundary.get("candidateRestartPts"))
    require(
        boundary.get("candidateRestartStatus") == "visual_alignment_candidate_not_original_event_proof",
        "oracle_candidate_status",
        "visual_alignment_candidate_not_original_event_proof",
        boundary.get("candidateRestartStatus"),
    )
    require(oracle.get("annotations", {}).get("intervalPts") == [38000, 47000], "oracle_interval", [38000, 47000], oracle.get("annotations", {}).get("intervalPts"))

    video_path = resolve_repo_path(str(source.get("path")))
    require(video_path.is_file(), "oracle_video_exists", True, video_path)
    video_bytes = video_path.stat().st_size
    video_sha256 = sha256_file(video_path)
    require(video_bytes == source.get("bytes"), "oracle_video_bytes", source.get("bytes"), video_bytes)
    require(video_sha256 == str(source.get("sha256")).upper(), "oracle_video_sha256", source.get("sha256"), video_sha256)
    return {
        "path": str(source["path"]),
        "bytes": video_bytes,
        "sha256": video_sha256,
        "dimensions": list(source["dimensions"]),
        "timeBase": source["timeBase"],
        "oraclePath": ORACLE.relative_to(REPO).as_posix(),
        "oracleSha256": sha256_file(ORACLE),
    }


def _source_hash_rows(alignment: dict[str, Any], oracle_info: dict[str, Any]) -> list[dict[str, Any]]:
    source_rows = alignment.get("sources")
    require(isinstance(source_rows, dict), "alignment_sources_object", True, type(source_rows).__name__)
    rows: list[dict[str, Any]] = []
    for name in sorted(source_rows):
        row = source_rows[name]
        require(isinstance(row, dict), f"alignment_source_{name}_object", True, type(row).__name__)
        relative_path = str(row.get("path"))
        path = resolve_repo_path(relative_path)
        require(path.is_file(), f"alignment_source_{name}_exists", True, path)
        actual = sha256_file(path)
        expected = str(row.get("sha256")).upper()
        require(actual == expected, f"alignment_source_{name}_sha256", expected, actual)
        if name == "visualOracle":
            require(actual == oracle_info["oracleSha256"], "alignment_visual_oracle_sha256", oracle_info["oracleSha256"], actual)
        rows.append({"name": name, "path": relative_path, "sha256": actual})
    return rows


def _compact_dynamic_windows(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    chronology = alignment["sourceClosedStaticEffectMaterialChronology"]
    windows = chronology.get("targetWindows")
    require(isinstance(windows, list), "alignment_target_windows_array", True, type(windows).__name__)
    result: list[dict[str, Any]] = []
    for effect_root in EFFECT_LIFETIMES:
        rows = [row for row in windows if row.get("effectRoot") == effect_root]
        require(bool(rows), f"dynamic_windows_{effect_root}", True, rows)
        first = min(float(row["firstDynamicKeySeconds"]) for row in rows)
        last = max(float(row["lastDynamicKeySeconds"]) for row in rows)
        result.append(
            {
                "effectRoot": effect_root,
                "firstDynamicKeySeconds": round(first, 6),
                "firstDynamicKeyCandidatePts": round(RESTART_PTS + first * 1000.0),
                "lastDynamicKeySeconds": round(last, 6),
                "lastDynamicKeyCandidatePts": round(RESTART_PTS + last * 1000.0),
            }
        )
    return result


def validate_alignment(alignment: dict[str, Any], oracle_info: dict[str, Any]) -> dict[str, Any]:
    require(alignment.get("schema") == "endfield.lizhiyan-overview-timing-alignment.v1", "alignment_schema", "endfield.lizhiyan-overview-timing-alignment.v1", alignment.get("schema"))
    require(alignment.get("status") == "source_timing_closed_retail_request_epoch_pending", "alignment_status", "source_timing_closed_retail_request_epoch_pending", alignment.get("status"))
    require(alignment.get("visibleAdmission") is False, "alignment_visible_admission", False, alignment.get("visibleAdmission"))
    source_timing = alignment.get("sourceClosedControllerTiming", {})
    require(source_timing.get("startClipLengthSeconds") == 10.7, "alignment_start_clip_length", 10.7, source_timing.get("startClipLengthSeconds"))
    require(source_timing.get("animationEvents") == [], "alignment_animation_events", [], source_timing.get("animationEvents"))
    visual = alignment.get("retailVisualAlignment", {})
    require(visual.get("candidateRestartPts") == RESTART_PTS, "alignment_candidate_restart", RESTART_PTS, visual.get("candidateRestartPts"))
    require(visual.get("evidenceClass") == "candidate_only", "alignment_evidence_class", "candidate_only", visual.get("evidenceClass"))
    require(visual.get("candidateCompatibilityEffectWindowPts") == [38800, 41134], "alignment_compatibility_window", [38800, 41134], visual.get("candidateCompatibilityEffectWindowPts"))
    chronology = alignment.get("sourceClosedStaticEffectMaterialChronology", {})
    require(chronology.get("sharedClip") == "A_fxui__lizhiyan_overview_start_01", "alignment_shared_clip", "A_fxui__lizhiyan_overview_start_01", chronology.get("sharedClip"))
    require(chronology.get("sampleRate") == 30.0, "alignment_shared_clip_rate", 30.0, chronology.get("sampleRate"))
    require(chronology.get("stopTimeSeconds") == 6.366667, "alignment_shared_clip_stop", 6.366667, chronology.get("stopTimeSeconds"))
    require(chronology.get("effectLifetimesSeconds") == EFFECT_LIFETIMES, "alignment_effect_lifetimes", EFFECT_LIFETIMES, chronology.get("effectLifetimesSeconds"))
    require(alignment.get("remainingEvidence", []) and "original retail producer" in alignment["remainingEvidence"][0], "alignment_event_origin_gap", True, alignment.get("remainingEvidence"))
    return {
        "path": ALIGNMENT.relative_to(REPO).as_posix(),
        "sha256": sha256_file(ALIGNMENT),
        "schema": alignment["schema"],
        "status": alignment["status"],
        "visibleAdmission": False,
        "sourceHashes": _source_hash_rows(alignment, oracle_info),
    }


def build() -> dict[str, Any]:
    oracle = load_json(ORACLE)
    alignment = load_json(ALIGNMENT)
    oracle_info = validate_oracle(oracle)
    alignment_info = validate_alignment(alignment, oracle_info)
    restart = RESTART_PTS

    captures = [
        {
            "retailPts": pts,
            "timeBase": "1/1000",
            "localSeconds": round((pts - restart) / 1000.0, 6),
            "phase": CAPTURE_PHASES[pts],
        }
        for pts in MINIMAL_CAPTURE_PTS
    ]
    lifecycles = []
    for effect_root, duration in EFFECT_LIFETIMES.items():
        lifecycles.append(
            {
                "effectRoot": effect_root,
                "durationSeconds": duration,
                "startRetailPts": restart,
                "endRetailPts": restart + round(duration * 1000.0),
                "startLocalSeconds": 0.0,
                "endLocalSeconds": duration,
            }
        )
    clip_seconds = 6.366667
    clip_end_pts = restart + clip_seconds * 1000.0
    return {
        "schema": SCHEMA,
        "status": "diagnostic_only",
        "comparisonOnly": True,
        "eventOriginProven": False,
        "eventOriginStatus": "visual_alignment_candidate_not_original_event_proof",
        "visibleAdmission": False,
        "sources": {
            "retailOracle": oracle_info,
            "timingAlignment": alignment_info,
        },
        "clock": {
            "retailTimeBase": "1/1000",
            "restartCandidatePts": restart,
            "restartCandidateLocalSeconds": 0.0,
            "localTimeMapping": "localSeconds=(retailPts-37967)/1000",
            "mappingPrecision": "integer retail milliseconds mapped to six-decimal local seconds",
        },
        "effectLifetimes": lifecycles,
        "sharedMaterialClip": {
            "name": "A_fxui__lizhiyan_overview_start_01",
            "sampleRate": 30.0,
            "lengthSeconds": clip_seconds,
            "endRetailPts": clip_end_pts,
            "nearestCapturePts": round(clip_end_pts),
            "nearestCaptureLocalSeconds": round((round(clip_end_pts) - restart) / 1000.0, 6),
        },
        "dynamicKeyWindows": _compact_dynamic_windows(alignment),
        "minimalCapturePts": list(MINIMAL_CAPTURE_PTS),
        "captures": captures,
        "diagnosticNotes": [
            "Capture points are comparison anchors, not proof of the original effect-request event.",
            "The current compatibility finger effect is active only at candidate PTS 38800..41134 and cannot explain measured teal at PTS 42000.",
            "The oracle hashes scaled RGB frames and fixed ROI measurements; they do not identify material, renderer-list, descriptor, draw, or submit ownership.",
        ],
        "nonClaims": [
            "event origin and request timestamp remain unproven",
            "visible retail admission remains false",
            "ordinary Renderer identity is not equated with an HGTree survivor/resource identity",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    contract = build()
    rendered = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file(), "output_exists", True, args.output)
        require(args.output.read_text(encoding="utf-8") == rendered, "output_current", "generated bytes", "drifted")
        print(f"Li Zhiyan visual capture spec verified: captures={len(contract['captures'])}, visibleAdmission=false")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: captures={len(contract['captures'])}, visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
