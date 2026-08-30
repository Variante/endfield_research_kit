#!/usr/bin/env python3
"""Extract playable-character overview lights from exact AnimeStudio JSON.

The source directory is the bounded CharInfo dependency export already joined
to the installed game's asset map.  No render/image fitting participates.  The
script discovers each light group from its serialized Light/LightInfo arrays,
walks the original Transform ancestry to the ``light_chr_*`` root, joins native
Light and HGAdditionalLightData objects by signed PathID, and reproduces the
native ``GetLightNPRData`` packing contract.  It also joins each light
GameObject's optional ``CharInfoLightFollower`` component so the lab can apply
the recovered native bone-follow formulas without fitting world transforms.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any


SCHEMA = "endfield.original-operator-lights.v1"
SOURCE_ROOT = Path("scratch/charinfo_playable_profiles/dependencies_json")
SOURCE_PLAN = Path("scratch/charinfo_playable_profiles/source_plan.json")
DEFAULT_OUTPUT = Path(
    "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
    "OriginalData/RenderParameters/operator_lights.json"
)


def runtime_semantic_sha256(row: dict[str, Any]) -> str:
    """Hash the source-authored fields consumed by the Unity light runtime."""

    tokens: list[str] = []

    def add_string(value: Any) -> None:
        encoded = base64.b64encode(str(value or "").encode("utf-8")).decode("ascii")
        tokens.append(encoded)

    def add_bool(value: Any) -> None:
        tokens.append("1" if bool(value) else "0")

    def add_int(value: Any) -> None:
        tokens.append(str(int(value or 0)))

    def add_float(value: Any) -> None:
        bits = struct.unpack("<I", struct.pack("<f", float(value or 0.0)))[0]
        tokens.append(f"{bits:08x}")

    def add_vector(value: Any, length: int) -> None:
        values = value if isinstance(value, list) else []
        for index in range(length):
            add_float(values[index] if index < len(values) else 0.0)

    follower = row.get("follower")
    has_follower = isinstance(follower, dict)
    follower = follower if has_follower else {}
    follower_source = follower.get("source")
    follower_source = follower_source if isinstance(follower_source, dict) else {}
    shadows = row.get("shadows")
    shadows = shadows if isinstance(shadows, dict) else {}

    add_string("endfield.operator-light.semantic.v1")
    add_string(row.get("name"))
    add_vector(row.get("position"), 3)
    add_vector(row.get("rotation_xyzw"), 4)
    add_vector(row.get("forward"), 3)
    add_vector(row.get("color"), 4)
    add_int(row.get("priority"))
    add_bool(row.get("use_color_temperature"))
    add_float(row.get("intensity"))
    add_bool(row.get("enabled"))
    add_float(row.get("range"))
    add_bool(int(row.get("light_type") or 0) == 0)
    add_float(row.get("outer_spot_angle"))
    add_float(row.get("inner_spot_angle"))
    add_int(row.get("npr_type"))
    add_vector(row.get("npr_data_native_packed"), 4)
    add_bool(row.get("character_only"))
    add_float(row.get("volumetric_scattering_intensity"))
    add_float(row.get("falloff_exponent"))
    add_float(row.get("linear_light_length"))
    add_float(row.get("soft_source_radius"))
    add_float(row.get("specular_intensity"))
    add_bool(row.get("use_culling_distance"))
    add_float(row.get("culling_distance"))
    add_float(row.get("falloff_distance"))
    add_float(row.get("culling_box_falloff_threshold"))
    add_bool(row.get("use_far_distance_show"))
    add_bool(row.get("enable_override_shadow_light"))
    add_int(row.get("shadow_type"))
    add_bool(shadows.get("m_UseCullingMatrixOverride"))
    add_bool(row.get("shadow_only"))
    add_bool(row.get("enable_obb_culling_box"))
    add_bool(int(row.get("cookie_path_id") or 0) != 0)
    add_bool(row.get("flicker_enabled"))
    add_bool(has_follower)
    add_bool(has_follower and follower.get("enabled"))
    add_int(follower.get("follow_type") if has_follower else 0)
    add_int(follower.get("followable_node_type") if has_follower else 0)
    add_string(follower.get("followable_node_name") if has_follower else "")
    add_vector(follower.get("position_offset") if has_follower else None, 3)
    add_vector(follower.get("local_position") if has_follower else None, 3)
    add_vector(follower.get("local_rotation_euler_degrees") if has_follower else None, 3)
    add_int(follower.get("component_path_id") if has_follower else 0)
    add_string(follower_source.get("sha256") if has_follower else "")
    add_string(follower_source.get("raw_data_sha256") if has_follower else "")
    payload = "|".join(tokens) + "|"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RecoveryError(RuntimeError):
    pass


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / SOURCE_ROOT).is_dir() and (
            candidate / "unity_endfield_graph_shader_lab"
        ).is_dir():
            return candidate
    raise RecoveryError("could not find the fluffy-dump repository root")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecoveryError(f"expected a JSON object: {path}")
    return value


def signed_path_id(path: Path, data: dict[str, Any]) -> int:
    metadata = data.get("$animestudio") or {}
    if "pathId" in metadata:
        return int(metadata["pathId"])
    match = re.search(r"_p([0-9a-fA-F]{16})\.json$", path.name)
    if not match:
        raise RecoveryError(f"cannot recover PathID from {path}")
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def source_record(repo: Path, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("$animestudio") or {}
    return {
        "path": relative(repo, path),
        "path_id": signed_path_id(path, data),
        "sha256": sha256(path),
        "raw_data_sha256": str(metadata.get("rawDataSha256") or ""),
        "raw_data_length": int(metadata.get("rawDataLength") or 0),
        "source_file": str(metadata.get("sourceFile") or ""),
        "source_original_path": str(metadata.get("sourceOriginalPath") or ""),
        "type_tree_source": str(metadata.get("typeTreeSource") or ""),
    }


def pptr_id(value: Any) -> int:
    return int(value.get("m_PathID") or 0) if isinstance(value, dict) else 0


def index_folder(folder: Path) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(folder.glob("*.json")):
        data = load_json(path)
        path_id = signed_path_id(path, data)
        if path_id in result:
            raise RecoveryError(f"duplicate PathID {path_id} in {folder}")
        result[path_id] = (path, data)
    return result


def component_owner_index(
    game_objects: dict[int, tuple[Path, dict[str, Any]]]
) -> dict[int, int]:
    result: dict[int, int] = {}
    for go_path_id, (_, data) in game_objects.items():
        for component in data.get("m_Components") or []:
            component_id = pptr_id(component)
            if component_id:
                result[component_id] = go_path_id
    return result


def ancestry_names(
    game_object_id: int,
    game_objects: dict[int, tuple[Path, dict[str, Any]]],
    component_owner: dict[int, int],
) -> list[str]:
    result: list[str] = []
    visited: set[int] = set()
    while game_object_id and game_object_id not in visited:
        visited.add(game_object_id)
        _, data = game_objects[game_object_id]
        result.append(str(data.get("m_Name") or data.get("Name") or ""))
        parent_transform_id = pptr_id((data.get("m_Transform") or {}).get("m_Father"))
        game_object_id = component_owner.get(parent_transform_id, 0)
    return result


def vector(value: Any, keys: tuple[str, ...]) -> list[float]:
    value = value if isinstance(value, dict) else {}
    return [float(value.get(key, value.get(key.upper(), 0.0)) or 0.0) for key in keys]


def quaternion_forward(quaternion: list[float]) -> list[float]:
    x, y, z, w = quaternion
    forward = [
        2.0 * (x * z + w * y),
        2.0 * (y * z - w * x),
        1.0 - 2.0 * (x * x + y * y),
    ]
    length = math.sqrt(sum(component * component for component in forward))
    if length <= 1e-12:
        raise RecoveryError("serialized light quaternion produced zero forward")
    return [component / length for component in forward]


def packed_npr_data(data: dict[str, Any]) -> list[float]:
    # HGAdditionalLightData's advanced-parameter mode publishes the serialized
    # carrier verbatim. Dapan's overview fog row is the roster case where this
    # intentionally differs from the convenience fog fields.
    if data.get("m_lightNPRAdvancedParamMode"):
        return vector(data.get("m_lightNPRData"), ("x", "y", "z", "w"))
    npr_type = int(data.get("m_lightNPRType") or 0)
    if npr_type == 0:
        return [
            float(data.get("m_lightNPRDefaultContrast") or 0.0),
            1.0 if data.get("m_lightNPRDefaultAutoLimit") else 0.0,
            0.0,
            0.0,
        ]
    if npr_type == 1:
        return [
            float(data.get("m_lightNPRRampBias") or 0.0),
            float(data.get("m_lightNPRRampShadowDimmer") or 0.0),
            float(data.get("m_lightNPRRampSDFBias") or 0.0),
            float(data.get("m_lightNPRRampSDFDramatic") or 0.0),
        ]
    if npr_type == 2:
        return [
            float(data.get("m_lightNPRSpecMaxRoughness") or 0.0),
            float(data.get("m_lightNPRSpecRoughnessBias") or 0.0),
            1.0 if data.get("m_lightNPRSpecMetalOnly") else 0.0,
            0.0,
        ]
    if npr_type == 3:
        return [
            float(data.get("m_lightNPRRimWidth") or 0.0),
            float(data.get("m_lightNPRRimAlbedoAlpha") or 0.0),
            0.0,
            0.0,
        ]
    if npr_type == 4:
        return [
            float(data.get("m_lightNPRFogAlpha") or 0.0),
            float(data.get("m_lightNPRFogFalloffFactor") or 0.0),
            1.0 if data.get("m_lightNPRFogDirectionalFalloff") else 0.0,
            float(data.get("m_lightNPRFogRampBias") or 0.0),
        ]
    if npr_type == 16:
        return [0.0, 0.0, 0.0, 0.0]
    serialized = vector(data.get("m_lightNPRData"), ("x", "y", "z", "w"))
    return serialized


def close_vector(left: list[float], right: list[float], tolerance: float = 1e-6) -> bool:
    return len(left) == len(right) and all(
        abs(a - b) <= tolerance for a, b in zip(left, right)
    )


def is_char_info_light_follower(data: dict[str, Any]) -> bool:
    """Recognize the serialized CharInfoLightFollower type-tree shape.

    The bounded dependency export contains fully decoded serialized type trees,
    but the script name itself is represented only by a PPtr.  Requiring the
    complete six-field payload avoids treating unrelated MonoBehaviours on the
    same light GameObject as followers.
    """

    return all(
        key in data
        for key in (
            "followType",
            "followableNodeType",
            "positionOffset",
            "localPosition",
            "localRotationEuler",
        )
    )


def follower_record(
    repo: Path,
    game_object_id: int,
    game_object: dict[str, Any],
    behaviours: dict[int, tuple[Path, dict[str, Any]]],
) -> dict[str, Any] | None:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for component in game_object.get("m_Components") or []:
        component_id = pptr_id(component)
        candidate = behaviours.get(component_id)
        if candidate is None:
            continue
        _, data = candidate
        if (
            is_char_info_light_follower(data)
            and pptr_id(data.get("m_GameObject")) == game_object_id
        ):
            matches.append(candidate)

    if len(matches) > 1:
        raise RecoveryError(
            f"multiple CharInfoLightFollower components on GameObject {game_object_id}"
        )
    if not matches:
        return None

    path, data = matches[0]
    follow_type = int(data.get("followType") or 0)
    node_type = int(data.get("followableNodeType") or 0)
    if follow_type not in (0, 1):
        raise RecoveryError(
            f"unsupported CharInfoLightFollower followType {follow_type} at {path}"
        )
    if node_type not in (0, 1):
        raise RecoveryError(
            f"unsupported CharInfoLightFollower node type {node_type} at {path}"
        )

    return {
        "component_path_id": signed_path_id(path, data),
        "enabled": bool(data.get("m_Enabled")),
        "follow_type": follow_type,
        "follow_type_name": {
            0: "fixed_world_position_offset",
            1: "parent_space_position_and_rotation",
        }[follow_type],
        "followable_node_type": node_type,
        "followable_node_name": {0: "BIP001", 1: "HEAD_LOCAL"}[node_type],
        "position_offset": vector(data.get("positionOffset"), ("x", "y", "z")),
        "local_position": vector(data.get("localPosition"), ("x", "y", "z")),
        "local_rotation_euler_degrees": vector(
            data.get("localRotationEuler"), ("x", "y", "z")
        ),
        "source": source_record(repo, path, data),
    }


def planned_light_roots(plan: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in plan.get("characters") or []:
        if not isinstance(item, dict):
            continue
        light_group = str(item.get("light_group") or "").replace("\\", "/")
        light_root = light_group.rsplit("/", 1)[-1]
        actor_token = str(item.get("actor_token") or "").lower()
        if not light_root or not actor_token:
            raise RecoveryError("source plan contains an incomplete light-group row")
        if light_root in result:
            raise RecoveryError(f"duplicate light root in source plan: {light_root}")
        result[light_root] = actor_token
    if not result:
        raise RecoveryError("source plan contains no playable light roots")
    return result


def build(repo: Path) -> dict[str, Any]:
    root = repo / SOURCE_ROOT
    plan = load_json(repo / SOURCE_PLAN)
    expected_light_roots = planned_light_roots(plan)
    game_objects = index_folder(root / "GameObject")
    lights = index_folder(root / "Light")
    behaviours = index_folder(root / "MonoBehaviour")
    component_owner = component_owner_index(game_objects)

    groups: list[tuple[Path, dict[str, Any]]] = []
    for path, data in behaviours.values():
        light_list = data.get("m_LightList")
        info_list = data.get("m_LightInfoList")
        if isinstance(light_list, list) and isinstance(info_list, list) and light_list:
            if len(light_list) == len(info_list):
                groups.append((path, data))

    actors: dict[str, Any] = {}
    for group_path, group in groups:
        group_game_object = pptr_id(group.get("m_GameObject"))
        group_go_path, group_go = game_objects[group_game_object]
        group_name = str(group_go.get("m_Name") or group_go.get("Name") or "")
        if group_name != "light_overview":
            continue

        # CharInfo operator prefabs contain six sibling light controllers. Some
        # actors have equal-sized overview/document groups, so ancestry and
        # light count are not sufficient selectors. Require the named overview
        # GameObject to be a direct child of the actor light root.
        parent_transform_id = pptr_id(
            (group_go.get("m_Transform") or {}).get("m_Father")
        )
        parent_game_object = component_owner.get(parent_transform_id, 0)
        if not parent_game_object:
            continue
        _, parent_go = game_objects[parent_game_object]
        direct_parent_name = str(
            parent_go.get("m_Name") or parent_go.get("Name") or ""
        )
        ancestry = ancestry_names(group_game_object, game_objects, component_owner)
        root_name = next((name for name in ancestry if name.startswith("light_chr_")), "")
        actor = expected_light_roots.get(root_name)
        if not actor or direct_parent_name != root_name:
            continue
        if actor in actors:
            raise RecoveryError(f"multiple direct light_overview groups for {actor}")
        rows: list[dict[str, Any]] = []
        for row_index, (light_ref, info) in enumerate(
            zip(group["m_LightList"], group["m_LightInfoList"])
        ):
            light_id = pptr_id(light_ref)
            hgrp_id = pptr_id(info.get("lightData"))
            light_path, light = lights[light_id]
            hgrp_path, hgrp = behaviours[hgrp_id]
            go_id = pptr_id(light.get("m_GameObject"))
            go_path, go = game_objects[go_id]
            transform = go.get("m_Transform") or {}
            quaternion = vector(transform.get("m_LocalRotation"), ("x", "y", "z", "w"))
            serialized_npr = vector(hgrp.get("m_lightNPRData"), ("x", "y", "z", "w"))
            packed_npr = packed_npr_data(hgrp)
            follower = follower_record(repo, go_id, go, behaviours)
            row = {
                    "index": row_index,
                    "name": str(go.get("m_Name") or go.get("Name") or ""),
                    "light_path_id": light_id,
                    "hgrp_path_id": hgrp_id,
                    "light_type": int(light.get("m_Type") or 0),
                    "priority": int(light.get("m_LightPriority") or 0),
                    "enabled": bool(light.get("m_Enabled")),
                    "color": vector(light.get("m_Color"), ("r", "g", "b", "a")),
                    "use_color_temperature": bool(light.get("m_UseColorTemperature")),
                    "intensity": float(info.get("intensity") or 0.0),
                    "serialized_light_intensity": float(light.get("m_Intensity") or 0.0),
                    "fog_alpha": float(info.get("fogAlpha") or 0.0),
                    "range": float(light.get("m_Range") or 0.0),
                    "outer_spot_angle": float(light.get("m_SpotAngle") or 0.0),
                    "inner_spot_angle": float(light.get("m_InnerSpotAngle") or 0.0),
                    "linear_light_length": float(light.get("m_LinearLightLength") or 0.0),
                    "soft_source_radius": float(light.get("m_SoftSourceRadius") or 0.0),
                    "specular_intensity": float(light.get("m_SpecularIntensity") or 0.0),
                    "use_culling_distance": bool(light.get("m_UseCullingDistance")),
                    "culling_distance": float(light.get("m_CullingDistance") or 0.0),
                    "falloff_distance": float(light.get("m_FalloffDistance") or 0.0),
                    "culling_box_falloff_threshold": float(
                        light.get("m_CullingBoxFalloffThreshold") or 0.0
                    ),
                    "use_far_distance_show": bool(light.get("m_UseFarDistanceShow")),
                    "enable_override_shadow_light": bool(
                        light.get("m_EnableOverrideShadowLight")
                    ),
                    "shadow_only": bool(light.get("m_ShadowOnly")),
                    "shadow_type": int(
                        ((light.get("m_Shadows") or {}).get("m_PlatformSpecificType") or {}).get(
                            "defaultParam"
                        )
                        or 0
                    ),
                    "enable_obb_culling_box": bool(light.get("m_EnableOBBCullingBox")),
                    "cookie_path_id": pptr_id(light.get("m_Cookie")),
                    "flicker_enabled": bool(
                        (((light.get("m_LightAnimationSetting") or {}).get(
                            "lightAnimatedData"
                        ) or {}).get("flickerData") or {}).get("enableFlicker")
                    ),
                    "position": vector(transform.get("m_LocalPosition"), ("x", "y", "z")),
                    "rotation_xyzw": quaternion,
                    "forward": quaternion_forward(quaternion),
                    "scale": vector(transform.get("m_LocalScale"), ("x", "y", "z")),
                    "follower": follower,
                    "shadows": light.get("m_Shadows") or {},
                    "npr_type": int(hgrp.get("m_lightNPRType") or 0),
                    "npr_data_serialized": serialized_npr,
                    "npr_data_native_packed": packed_npr,
                    "npr_data_matches_native_pack": close_vector(serialized_npr, packed_npr),
                    "character_only": bool(hgrp.get("m_LightCharacterOnly")),
                    "advanced_parameter_mode": bool(hgrp.get("m_lightNPRAdvancedParamMode")),
                    "volumetric_scattering_intensity": float(
                        hgrp.get("m_volumetricScatteringIntensity") or 0.0
                    ),
                    "falloff_exponent": float(hgrp.get("m_falloffExponent") or 0.0),
                    "sources": {
                        "light": source_record(repo, light_path, light),
                        "hgrp": source_record(repo, hgrp_path, hgrp),
                        "game_object": {
                            "path": relative(repo, go_path),
                            "path_id": go_id,
                            "sha256": sha256(go_path),
                        },
                    },
                }
            row["runtime_semantic_sha256"] = runtime_semantic_sha256(row)
            rows.append(row)
        actors[actor] = {
            "root_name": root_name,
            "group_name": group_name,
            "group_game_object": {
                "path": relative(repo, group_go_path),
                "path_id": group_game_object,
                "sha256": sha256(group_go_path),
                "parent_transform_path_id": parent_transform_id,
                "parent_game_object_path_id": parent_game_object,
            },
            "group_source": source_record(repo, group_path, group),
            "count": len(rows),
            "lights": rows,
        }

    expected_actors = sorted(expected_light_roots.values())
    if sorted(actors) != expected_actors:
        missing = sorted(set(expected_actors) - set(actors))
        extra = sorted(set(actors) - set(expected_actors))
        raise RecoveryError(
            f"playable operator-light coverage mismatch: missing={missing} extra={extra}"
        )
    invalid_counts = {
        actor: value["count"]
        for actor, value in actors.items()
        if value["count"] < 1 or value["count"] > 16
    }
    if invalid_counts:
        raise RecoveryError(
            f"operator-light counts exceed the viewer's 1..16 capacity: {invalid_counts}"
        )

    all_rows = [row for actor in actors.values() for row in actor["lights"]]
    followers = [row["follower"] for row in all_rows if row["follower"] is not None]
    direct_loop_supported = [
        row
        for row in all_rows
        if row["enabled"]
        and not row["use_culling_distance"]
        and not row["shadow_only"]
        and not row["enable_obb_culling_box"]
        and row["cookie_path_id"] == 0
        and not row["flicker_enabled"]
        and not row["use_color_temperature"]
        and abs(row["soft_source_radius"]) <= 1e-7
        and row["linear_light_length"] <= 0.0
    ]
    validation = {
        "ok": all(row["npr_data_matches_native_pack"] for row in all_rows),
        "actor_counts": {name: value["count"] for name, value in actors.items()},
        "native_npr_pack_matches": sum(
            1 for row in all_rows if row["npr_data_matches_native_pack"]
        ),
        "total_lights": len(all_rows),
        "enabled_lights": sum(1 for row in all_rows if row["enabled"]),
        "unit_cpu_culling_falloff_lights": sum(
            1 for row in all_rows if not row["use_culling_distance"]
        ),
        "zero_priority_lights": sum(1 for row in all_rows if row["priority"] == 0),
        "direct_loop_supported_lights": len(direct_loop_supported),
        "shadowless_lights": sum(1 for row in all_rows if row["shadow_type"] == 0),
        "unit_specular_intensity_lights": sum(
            1 for row in all_rows if abs(row["specular_intensity"] - 1.0) <= 1e-7
        ),
        "temperature_neutral_lights": sum(
            1 for row in all_rows if not row["use_color_temperature"]
        ),
        "serialized_intensity_matches_group_lights": sum(
            1
            for row in all_rows
            if abs(row["intensity"] - row["serialized_light_intensity"]) <= 1e-7
        ),
        "follower_lights": len(followers),
        "follower_lights_by_actor": {
            actor: sum(1 for row in value["lights"] if row["follower"] is not None)
            for actor, value in actors.items()
        },
        "enabled_followers": sum(1 for follower in followers if follower["enabled"]),
        "fixed_offset_followers": sum(
            1 for follower in followers if follower["follow_type"] == 0
        ),
        "parent_space_followers": sum(
            1 for follower in followers if follower["follow_type"] == 1
        ),
        "bip001_followers": sum(
            1 for follower in followers if follower["followable_node_type"] == 0
        ),
        "head_local_followers": sum(
            1 for follower in followers if follower["followable_node_type"] == 1
        ),
    }
    validation["actor_count"] = len(actors)
    validation["all_actor_counts_fit_runtime_capacity"] = not invalid_counts
    validation["ok"] = bool(
        validation["ok"]
        and validation["actor_count"] == len(expected_light_roots)
        and validation["all_actor_counts_fit_runtime_capacity"]
        and validation["enabled_followers"] == validation["follower_lights"]
        and validation["fixed_offset_followers"]
        + validation["parent_space_followers"]
        == validation["follower_lights"]
        and validation["bip001_followers"]
        + validation["head_local_followers"]
        == validation["follower_lights"]
    )
    return {
        "schema": SCHEMA,
        "policy": {
            "source": "installed-game AnimeStudio JSON plus native GetLightNPRData",
            "image_fitting": False,
            "runtime_unknowns": [
                "cluster tile membership for a live frame",
                "packed GPU light-buffer order after culling",
                "punctual shadow atlas contents",
                "evaluated BIP001/HEAD_LOCAL bone transforms for a live frame",
            ],
        },
        "actors": actors,
        "validation": validation,
    }


def encoded(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    repo = (args.repo_root or find_repo_root(Path.cwd())).resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    text = encoded(build(repo))
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != text:
            raise SystemExit(f"operator-light payload is stale: {output}")
        print(f"operator-light payload is current: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
