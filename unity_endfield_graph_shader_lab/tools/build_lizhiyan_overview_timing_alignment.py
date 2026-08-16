#!/usr/bin/env python3
"""Join source timing facts to the non-admitting Li Zhiyan retail visual oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
CHARACTER = LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan"
PREFAB = CHARACTER / "Prefabs/Lizhiyan.prefab"
START_CLIP = CHARACTER / "Animations/A_actor_lizhiyan_ui_overview_start_01.anim"
EFFECT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_finger_effect.json"
STATIC_START01 = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_01_effect.json"
STATIC_SIBLINGS = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_02_03_effects.json"
STATIC_ANIMATION = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/A_fxui__lizhiyan_overview_start_01.anim"
ORACLE = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_retail_visual_oracle.json"
)
OUTPUT = ORACLE.with_name("lizhiyan_overview_timing_alignment.json")
SCHEMA = "endfield.lizhiyan-overview-timing-alignment.v1"


class TimingAlignmentError(RuntimeError):
    pass


def require(value: bool, check: str, expected: Any, actual: Any) -> None:
    if not value:
        raise TimingAlignmentError(
            f"validator=lizhiyan_overview_timing_alignment; check={check}; "
            f"expected={expected}; actual={actual}"
        )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def unique_float(text: str, name: str) -> float:
    matches = re.findall(rf"^  {re.escape(name)}: ([0-9.]+)$", text, re.MULTILINE)
    require(len(matches) == 1, f"prefab_{name}_count", 1, len(matches))
    return float(matches[0])


def material_curve_windows(
    text: str, target_roots: dict[str, str], candidate_restart: int
) -> list[dict[str, Any]]:
    curves: list[dict[str, Any]] = []
    times: list[float] = []
    values: list[float] = []
    attribute = ""
    path = ""
    for line in text.splitlines():
        if line == "  - curve:":
            times, values, attribute, path = [], [], "", ""
        elif line.startswith("        time: "):
            times.append(float(line.split(": ", 1)[1]))
        elif line.startswith("        value: "):
            values.append(float(line.split(": ", 1)[1]))
        elif line.startswith("    attribute: "):
            attribute = line.split(": ", 1)[1]
        elif line.startswith("    path: "):
            path = line.split(": ", 1)[1]
        elif line == "    classID: 23":
            require(path in target_roots, "static_curve_target_root", "known path", path)
            require(len(times) == len(values) and len(times) >= 2,
                    "static_curve_key_shape", "paired keys", [len(times), len(values)])
            curves.append({"path": path, "effectRoot": target_roots[path],
                           "property": attribute, "times": times, "values": values})
    require(len(curves) == 53, "static_material_curve_count", 53, len(curves))
    rows = []
    for path in sorted(target_roots):
        target_curves = [row for row in curves if row["path"] == path]
        dynamic = [row for row in target_curves
                   if max(row["values"]) - min(row["values"]) > 1e-9]
        require(dynamic, "static_dynamic_curve_presence", True, path)
        first = min(min(row["times"]) for row in dynamic)
        last = max(max(row["times"]) for row in dynamic)
        rows.append({
            "effectRoot": target_roots[path],
            "targetPath": path,
            "curveCount": len(target_curves),
            "dynamicCurveCount": len(dynamic),
            "firstDynamicKeySeconds": round(first, 9),
            "lastDynamicKeySeconds": round(last, 9),
            "candidateDynamicWindowPts": [
                round(candidate_restart + first * 1000.0),
                round(candidate_restart + last * 1000.0),
            ],
            "properties": sorted({row["property"] for row in target_curves}),
            "visibleAdmission": False,
        })
    return rows


def build() -> dict[str, Any]:
    for path in (PREFAB, START_CLIP, EFFECT, ORACLE, STATIC_START01,
                 STATIC_SIBLINGS, STATIC_ANIMATION):
        require(path.is_file(), "source_exists", True, path)
    prefab_text = PREFAB.read_text(encoding="utf-8")
    clip_text = START_CLIP.read_text(encoding="utf-8")
    effect = json.loads(EFFECT.read_text(encoding="utf-8"))
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    static_start01 = json.loads(STATIC_START01.read_text(encoding="utf-8"))
    static_siblings = json.loads(STATIC_SIBLINGS.read_text(encoding="utf-8"))

    entry = unique_float(prefab_text, "entryNormalizedOffset")
    exit_time = unique_float(prefab_text, "exitNormalizedTime")
    transition = unique_float(prefab_text, "normalizedTransitionDuration")
    clip_lengths = re.findall(r"^    m_StopTime: ([0-9.]+)$", clip_text, re.MULTILINE)
    require(clip_lengths == ["10.7"], "start_clip_stop_time", ["10.7"], clip_lengths)
    require("  m_Events: []" in clip_text, "start_clip_events", "empty", "nonempty_or_missing")
    require(oracle.get("schema") == "endfield.lizhiyan-retail-visual-oracle.v1",
            "oracle_schema", "endfield.lizhiyan-retail-visual-oracle.v1", oracle.get("schema"))
    boundary = oracle["transitionBoundary"]
    require(boundary["candidateRestartStatus"] ==
            "visual_alignment_candidate_not_original_event_proof",
            "candidate_status", "visual_alignment_candidate_not_original_event_proof",
            boundary["candidateRestartStatus"])

    lifecycle = effect["effectSetting"]["timing"]
    delay = float(lifecycle["delay"])
    duration = float(lifecycle["duration"])
    clip_length = 10.7
    entry_seconds = entry * clip_length
    exit_seconds = exit_time * clip_length
    transition_seconds = transition * clip_length
    effect_start = delay
    effect_end = delay + duration
    candidate_restart = int(boundary["candidateRestartPts"])
    binding_rows = static_start01["animation"]["startAnimationClip"]["floatCurveBindings"]
    target_roots = {row["path"]: row["effectRoot"] for row in binding_rows["targetPaths"]}
    require(len(target_roots) == 10, "static_target_path_count", 10, len(target_roots))
    static_windows = material_curve_windows(
        STATIC_ANIMATION.read_text(encoding="utf-8"), target_roots, candidate_restart)
    candidate_effect_start_pts = round(candidate_restart + effect_start * 1000.0)
    candidate_effect_end_pts = round(candidate_restart + effect_end * 1000.0)
    mapped_samples = []
    for sample in oracle["samples"]:
        pts = int(sample["pts"])
        elapsed = (pts - candidate_restart) / 1000.0
        mapped_samples.append({
            "retailPts": pts,
            "phase": sample["phase"],
            "candidateElapsedSinceRestartSeconds": round(elapsed, 6),
            "candidateStartClipLocalSeconds": round(entry_seconds + elapsed, 9),
            "compatibilityFingerEffectWindow":
                "active" if effect_start <= elapsed <= effect_end else "inactive",
            "visibleAdmission": False,
        })

    return {
        "schema": SCHEMA,
        "status": "source_timing_closed_retail_request_epoch_pending",
        "visibleAdmission": False,
        "sources": {
            "prefab": {"path": PREFAB.relative_to(REPO).as_posix(), "sha256": sha256(PREFAB)},
            "startClip": {"path": START_CLIP.relative_to(REPO).as_posix(), "sha256": sha256(START_CLIP)},
            "effect": {"path": EFFECT.relative_to(REPO).as_posix(), "sha256": sha256(EFFECT)},
            "visualOracle": {"path": ORACLE.relative_to(REPO).as_posix(), "sha256": sha256(ORACLE)},
            "staticStart01": {"path": STATIC_START01.relative_to(REPO).as_posix(), "sha256": sha256(STATIC_START01)},
            "staticSiblings": {"path": STATIC_SIBLINGS.relative_to(REPO).as_posix(), "sha256": sha256(STATIC_SIBLINGS)},
            "staticAnimation": {"path": STATIC_ANIMATION.relative_to(REPO).as_posix(), "sha256": sha256(STATIC_ANIMATION)},
        },
        "sourceClosedControllerTiming": {
            "startClip": "A_actor_lizhiyan_ui_overview_start_01",
            "startClipLengthSeconds": clip_length,
            "animationEvents": [],
            "entryNormalizedOffset": entry,
            "entryClipLocalSeconds": round(entry_seconds, 9),
            "exitNormalizedTime": exit_time,
            "exitClipLocalSeconds": round(exit_seconds, 9),
            "normalizedTransitionDuration": transition,
            "transitionDurationSeconds": round(transition_seconds, 9),
            "loopDestinationNormalizedOffset": 0.0,
        },
        "sourceClosedEffectLocalTiming": {
            "effect": "P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub",
            "mount": "Bip001_R_Finger2Nub",
            "delaySeconds": delay,
            "durationSeconds": duration,
            "randomDelaySeconds": float(lifecycle["randomDelay"]),
            "looping": bool(lifecycle["isLoop"]),
        },
        "labCompatibilityChronology": {
            "evidenceClass": "current_lab_policy_not_original_request_chronology",
            "publishRelativeToRestart": "same call after start clip Play and entry-time assignment",
            "effectCreateElapsedSeconds": round(effect_start, 5),
            "effectDestroyElapsedSeconds": round(effect_end, 5),
            "effectCreateClipLocalSeconds": round(entry_seconds + effect_start, 9),
            "effectDestroyClipLocalSeconds": round(entry_seconds + effect_end, 9),
            "usesScaledWaitForSeconds": True,
            "finishWhenExit": False,
        },
        "sourceClosedStaticEffectMaterialChronology": {
            "sharedClip": "A_fxui__lizhiyan_overview_start_01",
            "sampleRate": 30.0,
            "stopTimeSeconds": 6.366667,
            "curveCount": 53,
            "effectLifetimesSeconds": {
                "P_fxui_lizhiyan_overview_start_01": 2.2,
                "P_fxui_lizhiyan_overview_start_02": 5.0,
                "P_fxui_lizhiyan_overview_start_03": 7.0,
            },
            "targetWindows": static_windows,
            "candidateEpochStatus": "visual_alignment_candidate_not_original_event_proof",
            "visibleAdmission": False,
        },
        "retailVisualAlignment": {
            "evidenceClass": "candidate_only",
            "candidateRestartPts": candidate_restart,
            "candidateBasis": "first Li Zhiyan visible exact-PTS frame",
            "candidateCompatibilityEffectWindowPts": [
                candidate_effect_start_pts, candidate_effect_end_pts
            ],
            "mappedSamples": mapped_samples,
            "diagnosticMismatch": (
                "PTS 42000 retains measured teal after the compatibility finger-effect root "
                f"would have been destroyed at candidate PTS {candidate_effect_end_pts}; "
                "the one recovered finger "
                "effect cannot explain the full retail teal chronology by itself."
            ),
        },
        "remainingEvidence": [
            "original retail producer and timestamp for the entrance-effect request",
            "the other eleven serialized Li Zhiyan entrance-effect bindings",
            "same-generation Unity capture keyed to an explicit restart PTS",
            "HGMesh-to-descriptor/draw/present identity for visible material admission",
        ],
        "nonClaims": [
            "first visible Li Zhiyan frame is not proof of the retail controller restart event",
            "the lab's same-call request publication is compatibility behavior, not recovered retail chronology",
            "timing alignment never admits the fail-closed VFX materials",
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
        require(args.output.read_text(encoding="utf-8") == rendered,
                "output_current", "generated bytes", "drifted")
        print("Li Zhiyan overview timing alignment verified: retail request epoch pending")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
