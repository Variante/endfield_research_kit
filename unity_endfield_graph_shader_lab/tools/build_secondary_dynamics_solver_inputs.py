#!/usr/bin/env python3
"""Build exact secondary-dynamics inputs for three priority Character Info actors.

This is an evidence contract, not a solver.  It copies the serialized
BeyondDynamicBone data that a source-compatible implementation would consume
and joins collider/root references to the existing hierarchy contract.  It
does not invent a spring integrator or claim retail-equivalent execution.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/secondary_dynamics_owner"
OWNER_CONTRACT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "secondary_dynamics_owner_recovery.json"
)
PLAYER_LOOP_CONTRACT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "playerloop_recovery_contract.json"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "secondary_dynamics_solver_inputs.json"
)

TARGET_ACTORS = ("endminf", "pelica", "chen")
PLAYER_LOOP_EVIDENCE_PATHS = {
    "nativeEvidence": "unity_endfield_graph_shader_lab/scratch/character_recovery/secondary_dynamics_owner/runtime_native.json",
    "playerLoopMetadata": "unity_endfield_graph_shader_lab/scratch/character_recovery/secondary_dynamics_owner/playerloop_metadata.json",
}
SCRIPT_TYPES = {
    -4499696877219864329: "BeyondDynamicBone.BeyondBoneCloth",
    -8854559673020325403: "BeyondDynamicBone.BeyondBoneCapsuleCollider",
    -7738307689003339598: "BeyondDynamicBone.BeyondBoneSphereCollider",
    7481586941717068173: "BeyondDynamicBone.BeyondBonePlaneCollider",
}

REQUIRED_SERIALIZED_FIELDS = {
    # Mesh/paint inputs are intentionally checked even though the convenience
    # views below do not reinterpret them.
    "sourceRenderers",
    "paintMaps",
    "paintMode",
    "meshWriteMode",
    "rootBones",
    "ignoreFromRootBones",
    "colliderCollisionConstraint",
    "damping",
    "radius",
    "inertiaConstraint",
    "tetherConstraint",
    "distanceConstraint",
    "triangleBendingConstraint",
    "angleRestorationConstraint",
    "angleLimitConstraint",
    "motionConstraint",
    "selfCollisionConstraint",
    "wind",
    "springConstraint",
}
REQUIRED_SERIALIZED2_FIELDS = {
    "selectionData",
    "preBuildData",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_sha(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "repo_path": path.relative_to(REPO_ROOT).as_posix(),
        "size": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def _path_id(value: Any) -> int:
    if not isinstance(value, dict) or "m_PathID" not in value:
        raise ValueError(f"expected serialized PPtr, got {value!r}")
    return int(value["m_PathID"])


def _script_name(payload: dict[str, Any]) -> str:
    return SCRIPT_TYPES.get(_path_id(payload["m_Script"]), "")


def _object_index(export_root: Path) -> dict[int, dict[str, Any]]:
    objects: dict[int, dict[str, Any]] = {}
    for path in sorted(export_root.glob("*.json")):
        payload = load_json(path)
        path_id = int(payload["$animestudio"]["pathId"])
        if path_id in objects:
            raise ValueError(f"duplicate MonoBehaviour path ID {path_id} in {export_root}")
        objects[path_id] = payload
    if not objects:
        raise ValueError(f"no serialized MonoBehaviour objects in {export_root}")
    return objects


def _manifest_maps(actor_contract: dict[str, Any]) -> tuple[dict[int, str], dict[int, str]]:
    """Return current Transform/GameObject maps for the exact owner character."""

    record = actor_contract["hierarchy_name_map"]
    path = REPO_ROOT / record["repo_path"]
    if not path.is_file():
        raise ValueError(f"missing hierarchy evidence: {record['repo_path']}")
    manifest = load_json(path)
    if manifest.get("character_id") != actor_contract["character_id"]:
        raise ValueError(
            "hierarchy evidence character drift: "
            f"{manifest.get('character_id')!r} != {actor_contract['character_id']!r}"
        )
    transforms: dict[int, str] = {}
    game_objects: dict[int, str] = {}
    for row in manifest.get("transforms", []):
        if "path_id" in row and "path" in row:
            path_id = int(row["path_id"])
            if path_id in transforms and transforms[path_id] != row["path"]:
                raise ValueError(f"conflicting hierarchy Transform path ID {path_id}")
            transforms[path_id] = row["path"]
        if "game_object_path_id" in row and "path" in row:
            path_id = int(row["game_object_path_id"])
            if path_id in game_objects and game_objects[path_id] != row["path"]:
                raise ValueError(f"conflicting hierarchy GameObject path ID {path_id}")
            game_objects[path_id] = row["path"]
    if not transforms or not game_objects:
        raise ValueError("hierarchy evidence has no transform/GameObject maps")
    return transforms, game_objects


def _source_evidence_check(payload: dict[str, Any], actor_contract: dict[str, Any]) -> None:
    raw = payload["$animestudio"]
    if Path(raw["sourceOriginalPath"]).name != actor_contract["source_chunk"]:
        raise ValueError(
            f"source chunk drift for {raw['pathId']}: "
            f"{raw['sourceOriginalPath']} != {actor_contract['source_chunk']}"
        )
    if int(raw["sourceOffset"]) != int(actor_contract["source_offset"]):
        raise ValueError(f"source offset drift for {raw['pathId']}")


def _validate_actor_rows(
    token: str,
    actor_contract: dict[str, Any],
    objects: dict[int, dict[str, Any]],
) -> None:
    """Cross-check every dynamic row against serialized and hierarchy evidence."""

    transform_paths, game_object_paths = _manifest_maps(actor_contract)
    filter_record = actor_contract["target_filter"]
    expected_filter_path = (
        f"unity_endfield_graph_shader_lab/scratch/character_recovery/"
        f"secondary_dynamics_owner/{token}_postmodel_monobehaviour_filter.json"
    )
    if filter_record.get("repo_path") != expected_filter_path:
        raise ValueError(f"{token}: target filter path spoof/drift")
    filter_path = REPO_ROOT / expected_filter_path
    if not filter_path.is_file() or file_sha256(filter_path) != filter_record["sha256"] or filter_path.stat().st_size != filter_record["size"]:
        raise ValueError(f"{token}: target filter hash/size drift")
    filter_rows = load_json(filter_path)
    filter_ids = {int(row["PathID"]) for row in filter_rows}
    if filter_ids != set(objects):
        raise ValueError(f"{token}: target filter PathID set differs from export objects")
    cloth_rows = {int(row["path_id"]): row for row in actor_contract["cloths"]}
    collider_rows = {int(row["path_id"]): row for row in actor_contract["colliders"]}
    expected_ids = set(cloth_rows) | set(collider_rows)
    observed_dynamic: dict[int, tuple[str, dict[str, Any]]] = {}
    for path_id, payload in objects.items():
        script_id = _path_id(payload["m_Script"])
        if script_id in SCRIPT_TYPES:
            observed_dynamic[path_id] = (SCRIPT_TYPES[script_id], payload)
    if set(observed_dynamic) != expected_ids:
        raise ValueError(
            f"{token}: owner drift in dynamic path IDs; "
            f"expected {sorted(expected_ids)}, observed {sorted(observed_dynamic)}"
        )

    for path_id, row in cloth_rows.items():
        type_name, payload = observed_dynamic[path_id]
        if type_name != "BeyondDynamicBone.BeyondBoneCloth":
            raise ValueError(f"{token}/{path_id}: unknown or wrong cloth script type {type_name!r}")
        if row["type"] != type_name:
            raise ValueError(f"{token}/{path_id}: owner script type drift")
        if int(payload["m_Enabled"]) != int(row["enabled"]):
            raise ValueError(f"{token}/{path_id}: enabled state drift")
        _source_evidence_check(payload, actor_contract)
        serialized = payload.get("serializeData")
        serialized2 = payload.get("serializeData2")
        if not isinstance(serialized, dict) or not REQUIRED_SERIALIZED_FIELDS <= set(serialized):
            missing = sorted(REQUIRED_SERIALIZED_FIELDS - set(serialized or {}))
            raise ValueError(f"{token}/{path_id}: missing serialized fields {missing}")
        if not isinstance(serialized2, dict) or not REQUIRED_SERIALIZED2_FIELDS <= set(serialized2):
            missing = sorted(REQUIRED_SERIALIZED2_FIELDS - set(serialized2 or {}))
            raise ValueError(f"{token}/{path_id}: missing serialized2 fields {missing}")
        go_id = _path_id(payload["m_GameObject"])
        if game_object_paths.get(go_id) != row["game_object_path"]:
            raise ValueError(f"{token}/{path_id}: owner GameObject path/PPtr drift")
        root_ids = [_path_id(value) for value in serialized["rootBones"]]
        expected_roots = [int(value["path_id"]) for value in row["root_bones"]]
        if root_ids != expected_roots:
            raise ValueError(f"{token}/{path_id}: root PPtr list drift")
        ignored_ids = [_path_id(value) for value in serialized["ignoreFromRootBones"]]
        expected_ignored = [int(value["path_id"]) for value in row["ignored_root_bones"]]
        if ignored_ids != expected_ignored:
            raise ValueError(f"{token}/{path_id}: ignored-root PPtr list drift")
        for root in row["root_bones"] + row["ignored_root_bones"]:
            if transform_paths.get(int(root["path_id"])) != root["path"]:
                raise ValueError(f"{token}/{path_id}: hierarchy root evidence drift")
        collider_ids = [_path_id(value) for value in serialized["colliderCollisionConstraint"]["colliderList"]]
        expected_colliders = [int(value["path_id"]) for value in row["colliders"]]
        if collider_ids != expected_colliders:
            raise ValueError(f"{token}/{path_id}: collider PPtr list drift")
        for collider in row["colliders"]:
            collider_id = int(collider["path_id"])
            if collider_id not in collider_rows:
                raise ValueError(f"{token}/{path_id}: owner references unknown collider {collider_id}")
            if game_object_paths.get(_path_id(objects[collider_id]["m_GameObject"])) != collider["game_object_path"]:
                raise ValueError(f"{token}/{path_id}: collider hierarchy/PPtr drift")

    for path_id, row in collider_rows.items():
        type_name, payload = observed_dynamic[path_id]
        if not type_name.endswith("Collider") or type_name != row["type"]:
            raise ValueError(f"{token}/{path_id}: unknown or wrong collider script type {type_name!r}")
        if int(payload["m_Enabled"]) != int(row["enabled"]):
            raise ValueError(f"{token}/{path_id}: collider enabled state drift")
        _source_evidence_check(payload, actor_contract)
        if payload["$animestudio"]["rawDataSha256"] != row["raw_data_sha256"]:
            raise ValueError(f"{token}/{path_id}: collider raw hash drift")
        if int(payload["$animestudio"]["rawDataLength"]) != int(row["raw_data_length"]):
            raise ValueError(f"{token}/{path_id}: collider raw length drift")
        go_id = _path_id(payload["m_GameObject"])
        if game_object_paths.get(go_id) != row["game_object_path"]:
            raise ValueError(f"{token}/{path_id}: collider GameObject path/PPtr drift")


def _copy(value: Any) -> Any:
    """Make the output independent of the parsed source object."""

    return copy.deepcopy(value)


def _constraint_view(serialized: dict[str, Any]) -> dict[str, Any]:
    names = (
        "damping",
        "radius",
        "inertiaConstraint",
        "tetherConstraint",
        "distanceConstraint",
        "triangleBendingConstraint",
        "angleRestorationConstraint",
        "angleLimitConstraint",
        "motionConstraint",
        "colliderCollisionConstraint",
        "selfCollisionConstraint",
        "wind",
        "springConstraint",
    )
    return {name: _copy(serialized[name]) for name in names}


def _parameter_view(serialized: dict[str, Any]) -> dict[str, Any]:
    names = (
        "clothType",
        "connectionMode",
        "rotationalInterpolation",
        "rootRotation",
        "updateMode",
        "clothAnimatorAbilityLODThreshold",
        "clothAnimatorLODThreshold",
        "clothLodFadeTime",
        "clothSimulateWeight",
        "resetSimulationToAnimationPoseWhenWeightLow",
        "resetSimulationToAnimationPoseWeightThreshold",
        "animationPoseRatio",
        "reductionSetting",
        "customSkinningSetting",
        "normalAlignmentSetting",
        "cullingSettings",
        "normalAxis",
        "gravity",
        "gravityDirection",
        "gravityFalloff",
        "stablizationTimeAfterReset",
        "blendWeight",
    )
    return {name: _copy(serialized[name]) for name in names}


def _proxy_transform_bindings(
    serialized2: dict[str, Any],
    transform_paths: dict[int, str],
) -> list[dict[str, Any]]:
    """Resolve the authored proxy transform array without inferring writeback."""

    try:
        transform_array = serialized2["preBuildData"]["uniquePreBuildData"][
            "proxyMesh"
        ]["transformData"]["transformArray"]
    except (KeyError, TypeError) as exc:
        raise ValueError("proxy transform array is missing") from exc
    if not isinstance(transform_array, list) or not transform_array:
        raise ValueError("proxy transform array is empty or malformed")

    bindings: list[dict[str, Any]] = []
    seen_ids: dict[int, int] = {}
    seen_paths: dict[str, int] = {}
    for array_index, value in enumerate(transform_array):
        path_id = _path_id(value)
        if path_id == 0:
            continue
        if path_id in seen_ids:
            raise ValueError(
                "proxy transform array repeats path ID "
                f"{path_id} at indices {seen_ids[path_id]} and {array_index}"
            )
        path = transform_paths.get(path_id)
        if path is None:
            raise ValueError(
                f"proxy transform array index {array_index} has unknown path ID {path_id}"
            )
        if path in seen_paths:
            raise ValueError(
                "proxy transform hierarchy path conflict "
                f"{path!r} at indices {seen_paths[path]} and {array_index}"
            )
        seen_ids[path_id] = array_index
        seen_paths[path] = array_index
        bindings.append(
            {
                "array_index": array_index,
                "path_id": path_id,
                "path": path,
            }
        )
    if not bindings:
        raise ValueError("proxy transform array has no non-null bindings")
    return bindings


def _collider_view(
    payload: dict[str, Any],
    contract_rows: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    path_id = int(payload["$animestudio"]["pathId"])
    type_name = _script_name(payload)
    row = contract_rows.get(path_id)
    if row is None:
        raise ValueError(f"collider {path_id} is absent from owner contract")
    result: dict[str, Any] = {
        "path_id": path_id,
        "type": type_name,
        "game_object_path": row["game_object_path"],
        "enabled": int(payload["m_Enabled"]),
        "center": _copy(payload["center"]),
        "size": _copy(payload["size"]),
        "source": {
            "raw_data_sha256": payload["$animestudio"]["rawDataSha256"],
            "raw_data_length": payload["$animestudio"]["rawDataLength"],
        },
    }
    if type_name.endswith("CapsuleCollider"):
        result.update(
            {
                "direction": int(payload["direction"]),
                "reverse_direction": int(payload["reverseDirection"]),
                "radius_separation": float(payload["radiusSeparation"]),
                "aligned_on_center": int(payload["alignedOnCenter"]),
            }
        )
    return result


def _cloth_view(
    payload: dict[str, Any],
    contract_row: dict[str, Any],
    contract_colliders: dict[int, dict[str, Any]],
    transform_paths: dict[int, str],
) -> dict[str, Any]:
    if _script_name(payload) != "BeyondDynamicBone.BeyondBoneCloth":
        raise ValueError("non-cloth payload passed to _cloth_view")
    raw = payload["$animestudio"]
    serialized = payload["serializeData"]
    serialized2 = payload["serializeData2"]
    if raw["rawDataSha256"] != contract_row["raw_data_sha256"]:
        raise ValueError(f"raw data changed for cloth {contract_row['path_id']}")
    if raw["rawDataLength"] != contract_row["raw_data_length"]:
        raise ValueError(f"raw data length changed for cloth {contract_row['path_id']}")
    if canonical_sha(serialized) != contract_row["serialize_data_sha256"]:
        raise ValueError(f"serializeData changed for cloth {contract_row['path_id']}")
    if canonical_sha(serialized2) != contract_row["serialize_data2_sha256"]:
        raise ValueError(f"serializeData2 changed for cloth {contract_row['path_id']}")

    refs = []
    for value in serialized["colliderCollisionConstraint"]["colliderList"]:
        collider_id = _path_id(value)
        collider = contract_colliders.get(collider_id)
        if collider is None:
            raise ValueError(
                f"cloth {contract_row['path_id']} references unknown collider {collider_id}"
            )
        refs.append(
            {
                "path_id": collider_id,
                "type": collider["type"],
                "game_object_path": collider["game_object_path"],
            }
        )

    proxy_transform_bindings = _proxy_transform_bindings(
        serialized2,
        transform_paths,
    )

    return {
        "path_id": int(raw["pathId"]),
        "game_object_path": contract_row["game_object_path"],
        "enabled": int(payload["m_Enabled"]),
        "root_bones": _copy(contract_row["root_bones"]),
        "ignored_root_bones": _copy(contract_row["ignored_root_bones"]),
        "collider_references": refs,
        "proxy_transform_bindings": proxy_transform_bindings,
        "source": {
            "raw_data_sha256": raw["rawDataSha256"],
            "raw_data_length": raw["rawDataLength"],
            "serialize_data_sha256": contract_row["serialize_data_sha256"],
            "serialize_data2_sha256": contract_row["serialize_data2_sha256"],
        },
        # Keep the exact Unity serialization available for a source-compatible
        # loader.  The views below are convenience projections only.
        "serialized_data": _copy(serialized),
        "serialized_data2": _copy(serialized2),
        "solver_input": {
            "parameters": _parameter_view(serialized),
            "constraints": _constraint_view(serialized),
            "selection_data": _copy(serialized2["selectionData"]),
            "prebuild_data": _copy(serialized2["preBuildData"]),
            "collider_references": refs,
            "proxy_transform_bindings": proxy_transform_bindings,
            "boundary": (
                "These are authored/static inputs. No runtime solver, Burst job, "
                "or transform writeback is implied by this record."
            ),
        },
    }


def _native_lifecycle(owner: dict[str, Any], player_loop: dict[str, Any]) -> dict[str, Any]:
    runtime = owner["runtime"]
    method_types = (
        "Beyond.Gameplay.View.CharUIModelMono",
        "BeyondDynamicBone.BeyondBoneCloth",
        "BeyondDynamicBone.ClothProcess",
        "BeyondDynamicBone.ColliderComponent",
        "BeyondDynamicBone.MagicaManager",
        "BeyondDynamicBone.ClothManager",
        "BeyondDynamicBone.TimeManager",
        "BeyondDynamicBone.WindManager",
        "BeyondDynamicBone.MagicaManager+<>c",
    )
    methods = [
        _copy(row)
        for row in runtime["method_bodies"]
        if row["type"] in method_types
    ]
    player_loop_output = _copy(player_loop)
    # Published evidence paths are always repo-relative, never a basename or
    # machine-local absolute path.
    for key, relative_path in PLAYER_LOOP_EVIDENCE_PATHS.items():
        player_loop_output.setdefault("source", {})[key] = relative_path
    return {
        "evidence": _copy(runtime["evidence"]),
        "method_bodies": methods,
        "charui_model_owner": _copy(runtime["charui_model_owner"]),
        "component_lifecycle": _copy(runtime["component_lifecycle"]),
        "manager": _copy(runtime["manager"]),
        "player_loop": player_loop_output,
        "unresolved_boundary": [
            "The ordinal-1 EarlyUpdate system TypeInfo static field is not joined "
            "to its exact string literal.",
            "BeyondDynamicBone/Burst constraint numerics, job scheduling, and "
            "transform writeback are not recovered from static evidence.",
            "No lab solver is implemented or marked retail-equivalent.",
        ],
    }


def _validate_player_loop(owner: dict[str, Any], player_loop: dict[str, Any]) -> None:
    if player_loop.get("schema") != "endfieldPlayerLoopRecoveryContract.v1":
        raise ValueError(f"unexpected PlayerLoop schema: {player_loop.get('schema')!r}")
    if player_loop.get("status") != "partial_unresolved_first_system_anchor":
        raise ValueError(f"unexpected PlayerLoop status: {player_loop.get('status')!r}")
    source_build = owner["source_build"]
    source_hashes = player_loop.get("sourceHashes", {})
    if source_hashes.get("GameAssembly.dll") != source_build["game_assembly"]["sha256"]:
        raise ValueError("PlayerLoop GameAssembly hash is not bound to owner contract")
    if source_hashes.get("global-metadata.dat") != source_build["global_metadata"]["sha256"]:
        raise ValueError("PlayerLoop metadata hash is not bound to owner contract")
    evidence_hashes = player_loop.get("evidenceHashes", {})
    source = player_loop.get("source", {})
    for source_key, expected_path in PLAYER_LOOP_EVIDENCE_PATHS.items():
        absolute_path = str((REPO_ROOT / expected_path).resolve()).replace("\\", "/")
        normalized_source = str(source.get(source_key, "")).replace("\\", "/")
        if normalized_source not in (expected_path, absolute_path):
            raise ValueError(f"PlayerLoop source path spoof/drift for {source_key}")
    for evidence_key, source_key in (
        ("runtime_native.json", "nativeEvidence"),
        ("playerloop_metadata.json", "playerLoopMetadata"),
    ):
        source_path = source.get(source_key)
        if not source_path:
            raise ValueError(f"PlayerLoop source missing {source_key}")
        evidence_path = REPO_ROOT / PLAYER_LOOP_EVIDENCE_PATHS[source_key]
        if not evidence_path.is_file():
            raise ValueError(f"missing PlayerLoop evidence {evidence_path}")
        expected_hash = evidence_hashes.get(evidence_key)
        if not expected_hash or file_sha256(evidence_path) != expected_hash:
            raise ValueError(f"PlayerLoop evidence hash drift for {evidence_key}")


def build_contract() -> dict[str, Any]:
    owner = load_json(OWNER_CONTRACT)
    if owner.get("schema") != "endfield.charinfo.secondary-dynamics-owner.v1":
        raise ValueError("unexpected owner contract schema")
    player_loop = load_json(PLAYER_LOOP_CONTRACT)
    _validate_player_loop(owner, player_loop)
    actors: dict[str, Any] = {}

    for token in TARGET_ACTORS:
        actor_contract = owner["actors"].get(token)
        if actor_contract is None:
            raise ValueError(f"owner contract has no target actor {token}")
        export_root = EVIDENCE_ROOT / f"{token}_postmodel_export/MonoBehaviour"
        objects = _object_index(export_root)
        _validate_actor_rows(token, actor_contract, objects)
        transform_paths, _ = _manifest_maps(actor_contract)
        actor_colliders = {
            int(row["path_id"]): row for row in actor_contract["colliders"]
        }
        colliders = []
        for path_id, row in sorted(actor_colliders.items()):
            payload = objects.get(path_id)
            if payload is None:
                raise ValueError(f"{token}: missing collider payload {path_id}")
            colliders.append(_collider_view(payload, actor_colliders))

        cloths = []
        for row in actor_contract["cloths"]:
            path_id = int(row["path_id"])
            payload = objects.get(path_id)
            if payload is None:
                raise ValueError(f"{token}: missing cloth payload {path_id}")
            cloths.append(
                _cloth_view(payload, row, actor_colliders, transform_paths)
            )

        actors[token] = {
            "character_id": actor_contract["character_id"],
            "display_name": actor_contract["display_name"],
            "container": actor_contract["container"],
            "overview_controller": _copy(actor_contract["overview_controller"]),
            "source": {
                "owner_contract": file_record(OWNER_CONTRACT),
                "target_filter": _copy(actor_contract["target_filter"]),
                # The seven-actor owner snapshot predates additive hierarchy
                # manifest enrichment. Pin the exact current three-target file
                # after its character identity and every consumed path resolve.
                "hierarchy_name_map": file_record(
                    REPO_ROOT / actor_contract["hierarchy_name_map"]["repo_path"]
                ),
                "export_root": export_root.relative_to(REPO_ROOT).as_posix(),
                "exported_object_count": len(objects),
            },
            "colliders": colliders,
            "cloths": cloths,
        }

    return {
        "schema": "endfield.charinfo.secondary-dynamics-solver-inputs.v1",
        "recovered_at": "2026-08-20",
        "scope": (
            "Endminf, Pelica, and Chen Character Info postmodel serialized inputs "
            "plus pinned static native lifecycle evidence; no Unity/game launch."
        ),
        "status": "static_inputs_recovered_solver_unimplemented",
        "source_build": _copy(owner["source_build"]),
        "script_identity": _copy(owner["script_identity"]),
        "actors": actors,
        "native_lifecycle": _native_lifecycle(owner, player_loop),
        "implementation_boundary": {
            "solver_implemented": False,
            "retail_equivalent": False,
            "reason": (
                "The repository has no BeyondDynamicBone/Burst runtime. This "
                "contract exposes source-authored inputs and lifecycle evidence "
                "without substituting a spring approximation."
            ),
        },
    }


def main() -> int:
    payload = build_contract()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT}")
    print(
        json.dumps(
            {
                token: {
                    "cloths": len(actor["cloths"]),
                    "colliders": len(actor["colliders"]),
                    "selection_points": sum(
                        len(row["solver_input"]["selection_data"]["positions"])
                        for row in actor["cloths"]
                    ),
                }
                for token, actor in payload["actors"].items()
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
