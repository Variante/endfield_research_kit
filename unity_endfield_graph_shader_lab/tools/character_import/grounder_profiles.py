#!/usr/bin/env python3
"""Recover exact per-actor Grounder profiles from targeted original exports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
MANIFEST_ROOT = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable"
)
DEFAULT_CATALOG = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/"
    "playable_character_grounder_profiles.json"
)
GROUNDER_SCRIPT_PATH_ID = 3348710443232901189
DEFAULT_PLAYABLE_CATALOG = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/"
    "playable_character_ui_catalog.json"
)

_OLDER_COMPONENT_ROOT = (
    REPO_ROOT
    / "scratch/character_recovery/retail_ik_activation_audit/"
    "roster_postmodel_components"
)
_LATE_COMPONENT_ROOT = (
    PROJECT_ROOT / "scratch/grounding_runtime/original_grounders"
)

_SOLVER_FIELDS = (
    "floorAnimTheta",
    "floorPredictTheta",
    "floorFeetThetaByFoot",
    "maxLegLength",
    "maxFeetOffset",
    "minPelvisHeight",
    "maxStep",
    "heightOffset",
    "footSpeed",
    "footRadius",
    "footCenterOffset",
    "prediction",
    "footRotationWeight",
    "footRotationSpeed",
    "maxFootRotationAngleFore",
    "maxFootRotationAngleBack",
    "maxFootRotationAngleIn",
    "maxFootRotationAngleOut",
    "rotateSolver",
    "pelvisSpeed",
    "pelvisSpeedXZ",
    "pelvisDamper",
    "lowerPelvisWeight",
    "liftPelvisWeight",
    "rootSphereCastRadius",
    "overstepFallsDown",
    "quality",
    "forwardFeetOffset",
    "isUsingLoswest",
    "isDependingLeftLeg",
)

_RUNTIME_BLOCKERS = (
    "live_FootIKWeight_controller_inputs_and_callback_order_absent",
    "source_compatible_terrain_query_provider_absent",
    "live_controller_and_continuity_state_absent",
    "pelvis_aware_foot_only_solver_surface_not_implemented",
    "numeric_original_frame_fixtures_absent",
)

_ACTIVE_IK_LAYER_MASK = 0x00300000
_ACTIVE_IK_LAYER_NAMES = ("Terrain", "IK")
_ACTIVE_MOVEMENT_SETTINGS = ("MovementSetting_Default", "MovementSetting_Aglina")


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _candidate_roots(character_id: str) -> list[Path]:
    return [
        _OLDER_COMPONENT_ROOT / character_id,
        _LATE_COMPONENT_ROOT / character_id / "components",
    ]


def find_grounder_component(character_id: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for root in _candidate_roots(character_id):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            metadata = payload.get("$animestudio") or {}
            if int(metadata.get("scriptPathId") or 0) != GROUNDER_SCRIPT_PATH_ID:
                continue
            if "maintianPelvisFootWeight" not in payload or not isinstance(
                payload.get("solver"), dict
            ):
                continue
            matches.append((path, payload))
    if len(matches) != 1:
        raise RuntimeError(
            f"{character_id}: expected one exact Grounder component, found {len(matches)}"
        )
    return matches[0]


def _pptr_path_id(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return int(value.get("m_PathID") or 0)


def _resolve_transform(manifest: dict[str, Any], path_id: int) -> dict[str, Any]:
    for key in ("transforms", "scene_transforms"):
        for transform in manifest.get(key) or []:
            if int(transform.get("path_id") or 0) != path_id:
                continue
            return {
                "path_id": path_id,
                "name": str(transform.get("name") or ""),
                "path": str(transform.get("path") or ""),
                "resolved": True,
            }
    return {"path_id": path_id, "name": "", "path": "", "resolved": False}


def _mode_status(solver: dict[str, Any]) -> str:
    if int(solver.get("quality") or 0) != 3:
        return "unsupported_quality_mode"
    if bool(solver.get("rotateSolver")):
        return "rotated_root_aligned_base_recovered_runtime_not_implemented"
    if not bool(solver.get("overstepFallsDown")):
        return "unsupported_overstep_falls_down_false"
    return "ordinary_nonrotated_base_recovered_runtime_not_implemented"


def build_grounder_profile(
    character_id: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    component_path, component = find_grounder_component(character_id)
    metadata = component["$animestudio"]
    solver = component["solver"]
    left_path_id = _pptr_path_id(solver.get("IKFootBoneL"))
    right_path_id = _pptr_path_id(solver.get("IKFootBoneR"))
    source_bytes = component_path.read_bytes()
    normalized_solver = {field: solver.get(field) for field in _SOLVER_FIELDS}
    normalized_solver["layers"] = int((solver.get("layers") or {}).get("m_Bits") or 0)

    profile = {
        "schema": "endfield_original_grounder_profile_v1",
        "character_id": character_id,
        "source": {
            "status": "exact_original_serialized_component",
            "component_json": _relative(component_path),
            "component_json_sha256": hashlib.sha256(source_bytes).hexdigest().upper(),
            "component_path_id": int(metadata.get("pathId") or 0),
            "component_raw_data_sha256": str(metadata.get("rawDataSha256") or "").upper(),
            "source_file": str(metadata.get("sourceFile") or ""),
            "source_chunk": str(metadata.get("sourceOriginalPath") or ""),
            "script_path_id": int(metadata.get("scriptPathId") or 0),
        },
        "component": {
            "enabled": bool(component.get("m_Enabled")),
            "weight": component.get("weight"),
            "maintianPelvisFootWeight": component.get("maintianPelvisFootWeight"),
            "footAdsorbWeight": component.get("footAdsorbWeight"),
            "spineBend": component.get("spineBend"),
            "spineSpeed": component.get("spineSpeed"),
        },
        "solver": normalized_solver,
        "bindings": {
            "left_foot": _resolve_transform(manifest, left_path_id),
            "right_foot": _resolve_transform(manifest, right_path_id),
            "biped_ik_path_id": _pptr_path_id(component.get("ik")),
            "orientation_reference_path_id": _pptr_path_id(
                component.get("ikOriReferenceBone")
            ),
        },
        "runtime": {
            "mode_status": _mode_status(solver),
            "quality3_base_path_native_evidence": (
                int(solver.get("quality") or 0) == 3
                and bool(solver.get("overstepFallsDown"))
            ),
            "ordinary_base_path_native_evidence": (
                int(solver.get("quality") or 0) == 3
                and not bool(solver.get("rotateSolver"))
                and bool(solver.get("overstepFallsDown"))
            ),
            "rotated_root_aligned_base_path_native_evidence": (
                int(solver.get("quality") or 0) == 3
                and bool(solver.get("rotateSolver"))
                and bool(solver.get("overstepFallsDown"))
            ),
            "conditional_redirects_recovered": False,
            "profile_bound_to_lab_runtime": False,
            "default_enabled": False,
            "serialized_layer_mask_runtime_authoritative": False,
            "runtime_layer_source": "MovementSetting._ikLayers_via_OnAnimationSetup",
            "active_movement_setting_ik_layers_recovered": True,
            "active_movement_setting_ik_layers_decimal": _ACTIVE_IK_LAYER_MASK,
            "active_movement_setting_ik_layers_hex": "0x00300000",
            "active_movement_setting_layers": list(_ACTIVE_IK_LAYER_NAMES),
            "installed_settings_with_exact_mask": list(_ACTIVE_MOVEMENT_SETTINGS),
            "movement_setting_modifiers_can_override_layer_mask": False,
            "source_compatible_terrain_query_provider_recovered": False,
            "blockers": list(_RUNTIME_BLOCKERS),
        },
    }
    for side in ("left_foot", "right_foot"):
        binding = profile["bindings"][side]
        expected = "IK_Foot_L_001" if side == "left_foot" else "IK_Foot_R_001"
        binding["expected_name"] = expected
        binding["exact_expected_name"] = binding["name"] == expected
    return profile


def attach_profile_to_runtime(
    runtime: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    """Attach exact serialized tuning without claiming runtime activation."""

    runtime["original_grounder_profile"] = json.loads(json.dumps(profile))
    foot_weight_source = runtime.setdefault("foot_weight_source", {})
    foot_weight_source["serialized_profile_binding"] = {
        "status": "exact_per_actor_grounder_component_bound_to_manifest",
        "component_json": profile["source"]["component_json"],
        "component_path_id": profile["source"]["component_path_id"],
        "animation_scalar_curves_bound": False,
        "do_not_substitute_global_defaults": True,
    }
    ordinary = runtime.setdefault("ordinary_grounding", {})
    ordinary["actor_profile_mode_status"] = profile["runtime"]["mode_status"]
    ordinary["actor_profile_runtime_ready"] = False


def manifest_paths() -> list[Path]:
    return sorted(MANIFEST_ROOT.glob("*/*_ui_recovery_manifest.json"))


def expected_roster_count(catalog: Path = DEFAULT_PLAYABLE_CATALOG) -> int:
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    rows = payload.get("characters") or []
    declared = int(payload.get("roster_count") or 0)
    if declared <= 0 or len(rows) != declared:
        raise RuntimeError(
            f"playable catalog roster mismatch: declared={declared}, rows={len(rows)}"
        )
    return declared


def build_catalog() -> dict[str, Any]:
    paths = manifest_paths()
    expected_count = expected_roster_count()
    if len(paths) != expected_count:
        raise RuntimeError(
            f"expected {expected_count} manifests, found {len(paths)}"
        )
    profiles: list[dict[str, Any]] = []
    for path in paths:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        profiles.append(
            build_grounder_profile(str(manifest.get("character_id") or ""), manifest)
        )
    profiles.sort(key=lambda item: item["character_id"])
    return {
        "schema": "endfield_original_grounder_profile_catalog_v1",
        "source": "exact_targeted_original_postmodel_component_exports",
        "profile_count": len(profiles),
        "summary": {
            "quality3_count": sum(p["solver"]["quality"] == 3 for p in profiles),
            "nonrotated_count": sum(not bool(p["solver"]["rotateSolver"]) for p in profiles),
            "rotated_count": sum(bool(p["solver"]["rotateSolver"]) for p in profiles),
            "zero_layer_mask_count": sum(p["solver"]["layers"] == 0 for p in profiles),
            "resolved_bilateral_foot_count": sum(
                p["bindings"]["left_foot"]["exact_expected_name"]
                and p["bindings"]["right_foot"]["exact_expected_name"]
                for p in profiles
            ),
            "runtime_enabled_count": sum(p["runtime"]["default_enabled"] for p in profiles),
            "active_movement_setting_ik_layers_decimal": _ACTIVE_IK_LAYER_MASK,
            "active_movement_setting_ik_layers_hex": "0x00300000",
        },
        "profiles": profiles,
    }


def refresh_catalog(
    *,
    check: bool = False,
    output: Path = DEFAULT_CATALOG,
    payload: dict[str, Any] | None = None,
) -> bool:
    payload = payload or build_catalog()
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    current = output.read_text(encoding="utf-8") if output.is_file() else ""
    stale = current != encoded
    if stale and not check:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    payload = build_catalog()
    stale = refresh_catalog(check=args.check, output=args.output, payload=payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "profile_count": payload["profile_count"],
                "summary": payload["summary"],
                "stale": stale,
                "mode": "check" if args.check else "write",
            },
            indent=2,
        )
    )
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
