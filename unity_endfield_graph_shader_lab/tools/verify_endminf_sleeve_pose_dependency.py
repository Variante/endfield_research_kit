#!/usr/bin/env python3
"""Fail-closed audit for Endminf overview sleeve-pose ownership."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
MANIFEST = LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/endminf_ui_recovery_manifest.json"
DYNAMICS = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/secondary_dynamics_owner_recovery.json"
WULFA_ORACLE = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Animation/WulfaOriginalF5FullPose/wulfa_original_f5_full_pose_contract.json"
OUTPUT = REPO / "reports/assets/endminf_sleeve_pose_dependency_audit.json"
CLIPS = {"A_actor_endminf_ui_overview_start", "A_actor_endminf_ui_overview_loop"}
EXPECTED_GAMEASSEMBLY = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
sys.path.insert(0, str(REPO))
from scripts.common import check_installed_native_inputs  # noqa: E402


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    dynamics = json.loads(DYNAMICS.read_text(encoding="utf-8-sig"))

    cloth = next((row for row in manifest["meshes"] if row["name"] == "S_actor_endminf_cloth_01_lod0"), None)
    require(cloth is not None, "Endminf cloth_01 mesh is missing")
    paths = list(cloth.get("bone_paths") or [])
    sleeve_paths = [path for path in paths if any(token in path for token in ("waixiu_", "xiuzi_", "xiuko_"))]
    twist_paths = [path for path in paths if "ForeTwist" in path]
    core_paths = [path for path in paths if path.endswith(("Bip001_L_Forearm", "Bip001_R_Forearm"))]
    require(sleeve_paths and twist_paths and core_paths, "cloth_01 sleeve/core/twist binding closure is incomplete")

    clip_rows = {row["name"]: row for row in manifest["clips"] if row["name"] in CLIPS}
    require(set(clip_rows) == CLIPS, "overview start/loop clip rows are incomplete")
    clip_evidence = {}
    for name, row in sorted(clip_rows.items()):
        bones = list(row.get("bones") or [])
        sleeve = [bone for bone in bones if any(token in bone["name"] for token in ("waixiu_", "xiuzi_", "xiuko_"))]
        twist = [bone for bone in bones if "ForeTwist" in bone["name"]]
        require(sleeve and twist, f"{name} lacks sleeve/twist tracks")
        require(not any(b["pos_animated"] or b["rot_animated"] or b["scale_animated"] for b in sleeve), f"{name} sleeve controllers are no longer constant")
        require(all(b["rot_animated"] for b in twist), f"{name} twist rotation coverage changed")
        clip_evidence[name] = {"constant_sleeve_controller_count": len(sleeve), "animated_twist_count": len(twist)}

    actor_dynamics = dynamics["actors"]["endminf"]
    owner_names = {row["game_object_path"] for row in actor_dynamics["cloths"]}
    require(owner_names == {"MC_Coat", "MC_Hair", "MC_Ribbon", "MC_Ribbon2"}, "Endminf BeyondBoneCloth owner set changed")
    implementation = dynamics["implementation_boundary"]
    require(implementation["lab_solver_implemented"] is False, "secondary-dynamics implementation boundary changed")

    native = check_installed_native_inputs(EXPECTED_GAMEASSEMBLY, EXPECTED_METADATA)
    require(native.validated, "pinned installed native inputs are unavailable: " + native.detail)
    cloth_inputs = []
    for row in sorted(actor_dynamics["cloths"], key=lambda value: value["game_object_path"]):
        parameters = row["parameters"]
        cloth_inputs.append({
            "owner": row["game_object_path"],
            "path_id": row["path_id"],
            "root_bone_count": len(row["root_bones"]),
            "collider_count": len(row["colliders"]),
            "update_mode": parameters["update_mode"],
            "simulate_weight": parameters["simulate_weight"],
            "animation_pose_ratio": parameters["animation_pose_ratio"],
            "raw_data_sha256": row["raw_data_sha256"],
            "serialize_data_sha256": row["serialize_data_sha256"],
            "serialize_data2_sha256": row["serialize_data2_sha256"],
        })

    oracle = json.loads(WULFA_ORACLE.read_text(encoding="utf-8-sig")) if WULFA_ORACLE.is_file() else {}
    oracle_text = json.dumps(oracle, sort_keys=True).lower()
    require("wulfa" in oracle_text and "endminf" not in oracle_text, "full-pose oracle scope is no longer Wulfa-only")

    result = {
        "status": "ok",
        "actor": "endminf",
        "conclusion": "sleeve coherence requires an Endminf retail-f5 physical-pose oracle before secondary-dynamics parity can be evaluated",
        "cloth_mesh": cloth["name"],
        "binding_counts": {"sleeve_controller_paths": len(sleeve_paths), "twist_paths": len(twist_paths), "core_forearm_paths": len(core_paths)},
        "clips": clip_evidence,
        "beyond_bone_cloth_owners": sorted(owner_names),
        "retail_solver_present": False,
        "endminf_full_pose_oracle_present": False,
        "native_gate": {
            "status": native.status,
            "gameassembly_sha256": native.gameassembly_sha256,
            "metadata_sha256": native.metadata_sha256,
        },
        "beyond_bone_cloth_inputs": cloth_inputs,
        "writeback_boundary": implementation["reason"],
        "oracle_attempt": {
            "status": "blocked_missing_endminf_numeric_input_fixture",
            "available_replay": "Wulfa-only Unicorn retail-instruction harness with a hash-pinned Wulfa Avatar and 33-frame custom-attribute fixture",
            "missing": [
                "Endminf overview_start/overview_loop 143-custom-attribute frame fixtures",
                "Endminf-specific replay ABI/layout validation against SK_actor_endminf_01Avatar",
                "BeyondBoneCloth Burst job code and exact PlayerLoop/writeback schedule",
                "retail numeric cloth output frames",
            ],
        },
        "next_dependency": "capture or replay retail-f5 physical local TRS for Endminf overview_start and overview_loop after humanoid solve, TwistSolve, and generic-track precedence",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
