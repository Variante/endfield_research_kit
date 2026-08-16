#!/usr/bin/env python3
"""Build the fail-closed retail EffectAnimation playable-topology contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
BODY_TARGETS = REPO / "scratch/character_recovery/overview_effect_owner/effect_native_body_targets.json"
OWNER_REPORT = REPO / "reports/assets/character_recovery/overview_effect_owner_animator_negative_20260815.md"
STATIC_CONTRACT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_01_effect.json"
SIBLING_CONTRACT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/lizhiyan_overview_start_02_03_effects.json"
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_effect_animation_playable_topology.json"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def artifact(path: Path, kind: str) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(REPO.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "objectType": kind,
    }


def build() -> dict[str, Any]:
    for path in (BODY_TARGETS, OWNER_REPORT, STATIC_CONTRACT, SIBLING_CONTRACT):
        require(path.is_file(), f"playable topology source missing: {path}")
    start01 = json.loads(STATIC_CONTRACT.read_text(encoding="utf-8"))
    siblings = json.loads(SIBLING_CONTRACT.read_text(encoding="utf-8"))
    require(start01["animation"]["startAnimationClip"]["pathID"] == 7360398354216100382,
            "start_01 shared clip identity drifted")
    require(siblings["sharedAnimation"]["pathID"] == 7360398354216100382,
            "sibling shared clip identity drifted")
    return {
        "schema": "endfield.lizhiyan-effect-animation-playable-topology.v1",
        "status": "retail_topology_closed_editor_advanced_mixer_unavailable_visible_fail_closed",
        "visibleAdmission": False,
        "sources": {
            "nativeBodyTargets": artifact(BODY_TARGETS, "PinnedNativeBodyTargets"),
            "ownerReport": artifact(OWNER_REPORT, "NativeOwnerReport"),
            "start01Contract": artifact(STATIC_CONTRACT, "Start01EffectContract"),
            "siblingContract": artifact(SIBLING_CONTRACT, "SiblingEffectContract"),
        },
        "retailEffectAnimationTopology": {
            "updateMode": "GameTime",
            "timeScale": 1.0,
            "manualEvaluation": False,
            "clipRetiming": "not_proven_do_not_apply",
            "createPlayableGraph": {
                "token": "0x060059D0",
                "va": "0x183437F90",
                "graphCreateCallOffset": "0x74",
                "animationPlayableOutputCreateVA": "0x183438077",
                "advancedMixerCreateVA": "0x1834380BA",
            },
            "addClip": {
                "token": "0x060059CD",
                "va": "0x183437D60",
                "animationClipPlayableCreateVA": "0x183437E02",
            },
            "playAnimation": {"token": "0x060059D1", "va": "0x183436AD0"},
            "manualEvaluate": {"token": "0x060059D2", "va": "0x187431CB0"},
            "stop": {"token": "0x060059DB", "va": "0x1831DC580"},
            "mixer": {
                "type": "UnityEngine.Animations.AdvancedAnimationMixerPlayable",
                "image": "UnityEngine.AnimationModule.dll",
                "typeToken": "0x02000053",
                "inputCount": 3,
                "fields": ["m_Handle", "m_NullPlayable"],
                "methodTokens": {
                    "Create": "0x06000339",
                    "CreateHandle": "0x0600033A",
                    "constructor": "0x0600033B",
                    "GetHandle": "0x0600033C",
                    "Equals": "0x0600033D",
                    "CreateHandleInternal": "0x0600033E",
                    "staticConstructor": "0x0600033F",
                    "CreateHandleInternal_Injected": "0x06000340",
                },
            },
            "clipSlots": [
                {"index": 0, "semantic": "start", "pathID": 7360398354216100382},
                {"index": 1, "semantic": "loop", "pathID": 0},
                {"index": 2, "semantic": "end", "pathID": 0},
            ],
            "effectLifetimesSeconds": {
                "P_fxui_lizhiyan_overview_start_01": 2.2,
                "P_fxui_lizhiyan_overview_start_02": 5.0,
                "P_fxui_lizhiyan_overview_start_03": 7.0,
            },
            "clipStopTimeSeconds": 6.366667,
        },
        "labBoundary": {
            "projectEditorVersion": "2022.3.62f3",
            "retailAdvancedMixerTypeExpectedInEditor": False,
            "standardAnimationMixerPlayableIsExactSubstitute": False,
            "driverStatus": "exact_retail_mixer_type_unavailable_do_not_start_graph",
            "requiredBehavior": (
                "validate admitted source marker; create GameTime graph; target the null-controller/null-avatar "
                "Animator; use the exact three-input advanced mixer; connect only start clip at speed one; "
                "destroy graph at each EffectSetting lifetime"
            ),
            "blockedBy": [
                "retail AdvancedAnimationMixerPlayable is absent from stock Unity 2021/2022 editor AnimationModule assemblies",
                "standard AnimationMixerPlayable equivalence is not proven",
                "SetStartAnimationDuration, SetManual, and SetIgnoreGlobalTimeScale callsites are not closed for these assets",
                "static renderer identity is not joined to a final draw",
            ],
        },
        "nonClaims": [
            "the standard Unity AnimationMixerPlayable is not treated as the retail advanced mixer",
            "the shared clip is not stretched to an EffectSetting lifetime",
            "a closed managed playable topology does not admit the static renderers or shaders",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file() and args.output.read_text(encoding="utf-8") == rendered,
                "Li Zhiyan playable topology contract drifted")
        print("Li Zhiyan EffectAnimation playable topology verified: exact mixer unavailable")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: visibleAdmission=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
