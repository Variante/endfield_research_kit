#!/usr/bin/env python3
"""Fail-closed validation for the four behavior-owned Endminf Overview effects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGE = ROOT / "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_external_fx_rig/exact_four_root_stage"
DEFAULT_CLOSURE = (
    ROOT
    / "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_external_fx_rig/exact_four_root_closure.json"
)
IMPORTER = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfOverviewEffectImporter.cs"
)
CAPTURE = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfViewerPlayModeCapture.cs"
)

ROOTS = {
    "P_fxui_endminm003_overview_01": (644358100928130169, 772927267),
    "P_fxui_endminm003_overview_02": (7701914037140635122, 373845082),
    "P_fxui_endminm003_overview_03": (6277198576094749248, 67616247),
    "P_fxui_endminm003_overview_04": (-3166230417407544182, 241640789),
}
CLIPS = {
    "A_fx_endminf_ui_overview_02": (8413816528141668220, 772927267),
    "A_fx_endminf_ui_overview_03": (8378992340436559080, 373845082),
    "A_fx_endminf_ui_overview_04": (-2625895420410042749, 772927267),
    "A_actor_endminf_ui_overview_02": (-7994037904239017215, 937624865),
}
STAGE_FINGERPRINT = "130cf736dcc4c4f031e9a4f15521157e90bc7fed9085b9354cc61748f6249ea3"


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
    require(report.get("expected_root_count") == 4, "expected root count drifted")
    require(report.get("expected_clip_count") == 1, "expected rig clip count drifted")
    summaries = validation.get("object_index_summaries") or []
    require(len(summaries) == 2 and all(row.get("complete") is True for row in summaries),
            "object index is incomplete")
    for row in summaries:
        counts = row.get("counts") or {}
        require(counts.get("errors") == 0 and counts.get("suppressedErrors") == 0,
                "object index contains errors")

    for type_name, expected in (("GameObject", ROOTS), ("AnimationClip", CLIPS)):
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
    require(closure.get("status") == "incomplete_ambiguous", "PPtr closure status drifted")
    identities = closure.get("identities") or []
    ambiguous = [row for row in identities if row.get("status") == "ambiguous"]
    require(ambiguous and all(row.get("targetType") == "MonoScript" for row in ambiguous),
            "non-script PPtr closure became ambiguous")
    require(all(row.get("status") == "resolved" for row in identities
                if row.get("targetType") in {"Material", "Mesh", "Texture2D"}),
            "render dependency closure is incomplete")
    require(not any("overview_06" in path.name for path in (stage / "GameObject").glob("*.json")),
            "obsolete overview_06 root remains staged")
    importer = IMPORTER.read_text(encoding="utf-8")
    capture = CAPTURE.read_text(encoding="utf-8")
    for token in (
        f'ExpectedStageFingerprint =\n            "{STAGE_FINGERPRINT}"',
        '"Endminf exact effect stage provenance drifted"',
    ):
        require(token in importer, f"Unity stage gate missing {token!r}")
    require(
        "EndfieldEndminfOverviewEffectImporter.BuildAndValidate();" in capture,
        "targeted/canonical capture does not rebuild the exact effect stage",
    )
    return {"roots": len(ROOTS), "clips": len(CLIPS), "ambiguousMonoScripts": len(ambiguous)}


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
