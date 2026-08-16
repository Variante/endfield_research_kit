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


def build() -> dict[str, Any]:
    for path in (PREFAB, START_CLIP, EFFECT, ORACLE):
        require(path.is_file(), "source_exists", True, path)
    prefab_text = PREFAB.read_text(encoding="utf-8")
    clip_text = START_CLIP.read_text(encoding="utf-8")
    effect = json.loads(EFFECT.read_text(encoding="utf-8"))
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))

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
        "retailVisualAlignment": {
            "evidenceClass": "candidate_only",
            "candidateRestartPts": candidate_restart,
            "candidateBasis": "first Li Zhiyan visible exact-PTS frame",
            "mappedSamples": mapped_samples,
            "diagnosticMismatch": (
                "PTS 42000 retains measured teal after the compatibility finger-effect root "
                "would have been destroyed at candidate PTS 41049; the one recovered finger "
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
