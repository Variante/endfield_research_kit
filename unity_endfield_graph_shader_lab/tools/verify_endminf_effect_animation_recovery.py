#!/usr/bin/env python3
"""Verify Endminf clip 03 visibility stays separate from effect_nanguan clip 04."""

from __future__ import annotations

import json
from pathlib import Path

from unity_muscleclip_sampler import ClipSampler, load_hierarchy


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
SOURCE = REPO / "scratch/character_recovery/endminf_overview_effect_stage"
CLIP = SOURCE / "AnimationClip/A_fx_endminf_ui_overview_03_p74482923CB70A4E8.json"
IMPORTER = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfEffectAnimationImporter.cs"
)
CONTRACT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/endminf_overview_rock_visibility.json"
)
EXPECTED_PATHS = {
    "effect_nanguan/Sphere002/Dummy002/P_endminf_ui_overview_01_rock_01",
    "effect_nanguan/Sphere003/Dummy005/P_endminf_ui_overview_01_rock_02",
    "effect_nanguan/Sphere004/Dummy004/P_endminf_ui_overview_01_rock_03",
    "effect_nanguan/Sphere005/Dummy003/P_endminf_ui_overview_01_rock_04",
}
ACTIVE_ATTRIBUTE = 2086281974


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load(path: Path) -> dict:
    require(path.is_file(), f"missing source evidence: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"source evidence is not an object: {path}")
    return value


def validate() -> dict:
    hierarchy = load_hierarchy(SOURCE, "P_fxui_endminm003_overview_01")
    payload = ClipSampler(load(CLIP), hierarchy).sample(CLIP, include_frames=False)
    require(abs(float(payload["duration"]) - 1.5) < 1.0e-6, "visibility duration drifted")
    require(abs(float(payload["sample_rate"]) - 30.0) < 1.0e-6, "visibility rate drifted")

    active = payload.get("game_object_active_curves") or []
    require(len(active) == 4, "resolved rock active-curve census drifted")
    require({str(row.get("path") or "") for row in active} == EXPECTED_PATHS,
            "resolved rock active paths drifted")
    for row in active:
        keys = row.get("keys") or []
        require(len(keys) == 46, f"active sample count drifted: {row.get('path')}")
        for index, key in enumerate(keys):
            expected_value = 0.0 if index == 45 else 1.0
            require(abs(float(key["time"]) - index / 30.0) < 1.0e-6,
                    f"active sample time drifted: {row.get('path')}[{index}]")
            require(abs(float(key["value"]) - expected_value) < 1.0e-6,
                    f"active sample value drifted: {row.get('path')}[{index}]")

    scalars = [
        row for row in payload.get("unapplied_scalar_curves") or []
        if row.get("type_id") == "GameObject" and int(row.get("attribute") or 0) == ACTIVE_ATTRIBUTE
    ]
    require(len(scalars) == 5, "source GameObject-active scalar census drifted")
    constant_zero = [
        row for row in scalars
        if not row.get("varying")
        and all(abs(float(row.get(field) or 0.0)) < 1.0e-6
                for field in ("minimum", "maximum", "first", "last"))
    ]
    require(len(constant_zero) == 1,
            "unresolved constant-zero active binding is no longer exactly one")

    contract = load(CONTRACT)
    require(contract.get("schema") == "endfield.endminf-overview-rock-visibility.v1",
            "published rock visibility contract schema drifted")
    require((contract.get("source") or {}).get("sha256") ==
            "81ee25bc86197850e8c9fbf45e23d99a77da958ac9c0258e0ebfede1ab421426",
            "published source hash drifted")
    resolved = contract.get("resolvedBindings") or []
    require({"effect_nanguan/" + str(row.get("path") or "") for row in resolved} ==
            EXPECTED_PATHS, "published resolved paths drifted")
    require(all(float(row.get("initialValue")) == 1.0 and
                float(row.get("finalValue")) == 0.0 for row in resolved),
            "published active values drifted")
    unresolved = contract.get("unresolvedBindings") or []
    require(len(unresolved) == 1 and
            unresolved[0].get("policy") == "fail_closed_do_not_fabricate_target" and
            float(unresolved[0].get("constantValue")) == 0.0,
            "published fail-closed binding drifted")

    importer = IMPORTER.read_text(encoding="utf-8")
    for token in (
        'EffectNanguanClipName = "A_fx_endminf_ui_overview_04"',
        'AnimationRoot + "/" + EffectNanguanClipName + ".anim"',
        'rockBindings.Length == 28',
        '!rockBindings.Any(binding => binding.type == typeof(GameObject)',
        'binding.propertyName == "m_IsActive"',
    ):
        require(token in importer, f"Unity importer lost required contract token: {token}")
    for token in (
        'A_fx_endminf_ui_overview_03_04',
        'endminf_overview_rock_visibility.json',
        'AddRockVisibilityCurves',
        'CopyClip',
    ):
        require(token not in importer,
                f"Unity importer retained forbidden cross-owner composition token: {token}")

    return {
        "resolvedActiveCurves": len(active),
        "unresolvedConstantZeroBindings": len(constant_zero),
        "durationSeconds": payload["duration"],
        "sampleRate": payload["sample_rate"],
    }


def main() -> int:
    result = validate()
    print("verify_endminf_effect_animation_recovery: OK " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
