#!/usr/bin/env python3
"""Fail-closed validation for the three source-owned Endminf Overview effects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGE = ROOT / "scratch/character_recovery/endminf_overview_effect_stage"
DEFAULT_CLOSURE = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/ExternalUiEffects/endminf_animator_playback_closure.json"
)

ROOTS = {
    "P_fxui_endminm003_overview_01": (-5644653936686109575, 772927267),
    "P_fxui_endminm003_overview_02": (4503240569034685938, 373845082),
    "P_fxui_endminm003_overview_06": (9136045329807905267, 446888048),
}
CLIPS = {
    "A_fx_endminf_ui_overview_01": (-3167253468417284386, 446888048),
    "A_fx_endminf_ui_overview_02": (8413816528141668220, 772927267),
    "A_fx_endminf_ui_overview_03": (8378992340436559080, 373845082),
    "A_fx_endminf_ui_overview_04": (-2625895420410042749, 772927267),
}
UNBOUND_FX_RIG_CLIP = "A_actor_endminf_ui_overview_02"
STAGE_FINGERPRINT = "3c42f62962eae9d67ddbc530d0f4146f3325c4f650fe66ab53490671a3d491d4"


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load(path: Path) -> dict:
    require(path.is_file(), f"missing JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def metadata(path: Path) -> tuple[str, int]:
    value = load(path)
    source = value.get("$animestudio") or {}
    encoded = path.stem.rsplit("_p", 1)[-1]
    unsigned = int(encoded, 16)
    filename_path_id = unsigned if unsigned < (1 << 63) else unsigned - (1 << 64)
    return (
        str(value.get("m_Name") or value.get("Name") or ""),
        int(source.get("pathId") or filename_path_id),
    )


def validate(stage: Path, closure_path: Path) -> dict:
    report = load(stage / "external_ui_effect_stage.json")
    require(report.get("status") == "ok", "external effect stage is not complete")
    validation = report.get("validation") or {}
    require(validation.get("stage_fingerprint") == STAGE_FINGERPRINT, "stage fingerprint drifted")
    require(report.get("expected_root_count") == 3, "expected root count drifted")
    require(report.get("expected_clip_count") == 4, "expected clip count drifted")
    summaries = validation.get("object_index_summaries") or []
    require(len(summaries) == 1 and summaries[0].get("complete") is True, "object index is incomplete")
    counts = summaries[0].get("counts") or {}
    require(counts.get("errors") == 0 and counts.get("suppressedErrors") == 0, "object index contains errors")

    for type_name, expected in (("Animator", ROOTS), ("AnimationClip", CLIPS)):
        found: dict[str, int] = {}
        for path in sorted((stage / type_name).glob("*.json")):
            name, path_id = metadata(path)
            if name in expected:
                require(name not in found, f"duplicate exact {type_name}: {name}")
                found[name] = path_id
        require(set(found) == set(expected), f"exact {type_name} set drifted")
        for name, (path_id, _) in expected.items():
            require(found[name] == path_id, f"{type_name} PathID drifted: {name}")

    closure = load(closure_path)
    require(closure.get("status") == "incomplete_missing_artifacts", "animator closure status drifted")
    missing = closure.get("missingArtifacts") or []
    require(len(missing) == 1 and missing[0].get("name") == UNBOUND_FX_RIG_CLIP,
            "unresolved FX-rig clip boundary drifted")
    proof = closure.get("playbackProof") or {}
    require(proof.get("startToLoopProven") is False and proof.get("endProven") is False,
            "one-shot playback boundary drifted")
    for row in proof.get("effectAnimationRows") or []:
        require((row.get("loop") or {}).get("isNull") is True, "EffectAnimation loop became non-null")
        require((row.get("end") or {}).get("isNull") is True, "EffectAnimation end became non-null")
    return {"roots": len(ROOTS), "clips": len(CLIPS), "unboundFxRigClip": UNBOUND_FX_RIG_CLIP}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    args = parser.parse_args()
    result = validate(args.stage.resolve(), args.closure.resolve())
    print("verify_endminf_overview_effect_stage: OK " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
