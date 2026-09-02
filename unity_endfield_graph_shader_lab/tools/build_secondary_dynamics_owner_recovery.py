#!/usr/bin/env python3
"""Build the hash-pinned Character Info secondary-dynamics recovery contract.

This builder intentionally consumes only current installed files plus the
targeted AnimeStudio/native-code evidence under the character recovery lab.
It does not launch Unity or the game.
"""

from __future__ import annotations

import hashlib
import json
import struct
import argparse
from collections import Counter
from pathlib import Path

from character_import.controllers import recover_main_overview_controller


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
EVIDENCE_ROOT = LAB_ROOT / "scratch/character_recovery/secondary_dynamics_owner"
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/secondary_dynamics_owner_recovery.json"
)

GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
ASSET_MAP = (
    REPO_ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json"
)
IFIX_CONTRACT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/installed_ifix_patch_state.json"
)
SCRIPT_TYPES = {
    -4499696877219864329: "BeyondDynamicBone.BeyondBoneCloth",
    -8854559673020325403: "BeyondDynamicBone.BeyondBoneCapsuleCollider",
    -7738307689003339598: "BeyondDynamicBone.BeyondBoneSphereCollider",
    7481586941717068173: "BeyondDynamicBone.BeyondBonePlaneCollider",
}

ACTORS = {
    "endminf": {
        "character_id": "chr_0003_endminf",
        "display_name": "Endministrator",
        "manifest_dir": "Endminf",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0003_endminf_postmodel.prefab",
    },
    "pelica": {
        "character_id": "chr_0004_pelica",
        "display_name": "Perlica",
        "manifest_dir": "Pelica",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0004_pelica_postmodel.prefab",
    },
    "chen": {
        "character_id": "chr_0005_chen",
        "display_name": "Chen Qianyu",
        "manifest_dir": "Chen",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0005_chen_postmodel.prefab",
    },
    "lastrite": {
        "character_id": "chr_0026_lastrite",
        "display_name": "Last Rite",
        "manifest_dir": "Lastrite",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0026_lastrite_postmodel.prefab",
    },
    "wulfa": {
        "character_id": "chr_0028_wulfa",
        "display_name": "Wulfa",
        "manifest_dir": "Wulfa",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0028_wulfa_postmodel.prefab",
    },
    "zhuangfy": {
        "character_id": "chr_0030_zhuangfy",
        "display_name": "Zhuang Fangyi",
        "manifest_dir": "Zhuangfy",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0030_zhuangfy_postmodel.prefab",
    },
    "lizhiyan": {
        "character_id": "chr_0032_lizhiyan",
        "display_name": "Li Zhiyan",
        "manifest_dir": "Lizhiyan",
        "container": "assets/beyond/dynamicassets/gameplay/actors/postmodels/characters/chr_0032_lizhiyan_postmodel.prefab",
    },
}


def prepare_actor_filters() -> None:
    asset_map = load_json(ASSET_MAP)
    entries = asset_map.get("AssetEntries") or []
    for token, actor in ACTORS.items():
        selected = [
            row
            for row in entries
            if row.get("Container") == actor["container"]
            and row.get("Type") == "MonoBehaviour"
        ]
        if not selected:
            raise ValueError(f"no MonoBehaviour AssetMap rows for {token}")
        selected.sort(key=lambda row: (row["Source"], int(row["Offset"]), int(row["PathID"])))
        output = EVIDENCE_ROOT / f"{token}_postmodel_monobehaviour_filter.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(selected, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {output} ({len(selected)} rows)")

METHODS = {
    ("Beyond.Gameplay.View.CharUIModelMono", "_UpdateMagicaClothWeight"): 0xA6FC,
    ("Beyond.Gameplay.View.CharUIModelMono", "OnAwake"): 0xA6FD,
    ("Beyond.Gameplay.View.CharUIModelMono", "Tick"): 0xA701,
    ("Beyond.Gameplay.View.CharUIModelMono", "OnRelease"): 0xA70B,
    ("BeyondDynamicBone.BeyondBoneCloth", "Awake"): 0x2A,
    ("BeyondDynamicBone.BeyondBoneCloth", "OnEnable"): 0x74,
    ("BeyondDynamicBone.BeyondBoneCloth", "OnDisable"): 0x9E,
    ("BeyondDynamicBone.BeyondBoneCloth", "Start"): 0xA0,
    ("BeyondDynamicBone.BeyondBoneCloth", "OnDestroy"): 0x181,
    ("BeyondDynamicBone.BeyondBoneCloth", "Initialize"): 0x184,
    ("BeyondDynamicBone.BeyondBoneCloth", "SetClothSimulateWeight"): None,
    ("BeyondDynamicBone.ClothProcess", "StartUse"): 0x75,
    ("BeyondDynamicBone.ClothProcess", "EndUse"): 0x9F,
    ("BeyondDynamicBone.ColliderComponent", "OnEnable"): 0x208,
    ("BeyondDynamicBone.ColliderComponent", "OnDisable"): 0x20A,
    ("BeyondDynamicBone.ColliderComponent", "OnDestroy"): 0x20B,
    ("BeyondDynamicBone.MagicaManager", ".cctor"): None,
    ("BeyondDynamicBone.MagicaManager", "Initialize"): 0x3CF,
    ("BeyondDynamicBone.MagicaManager", "InitCustomGameLoop"): 0x3D1,
    ("BeyondDynamicBone.MagicaManager", "SetCustomGameLoop"): 0x3D5,
    ("BeyondDynamicBone.ClothManager", "Initialize"): 0x330,
    ("BeyondDynamicBone.ClothManager", "ClothUpdate"): None,
    ("BeyondDynamicBone.TimeManager", "Initialize"): 0x473,
    ("BeyondDynamicBone.WindManager", "Initialize"): 0x478,
    ("BeyondDynamicBone.WindManager", "AlwaysWindUpdate"): 0x307,
    ("BeyondDynamicBone.MagicaManager+<>c", "<InitCustomGameLoop>b__39_0"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_0"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_1"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_2"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_3"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_4"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_5"): None,
    ("BeyondDynamicBone.MagicaManager+<>c", "<SetCustomGameLoop>b__40_6"): None,
}

MANAGER_INIT_ORDER = [
    "BeyondDynamicBone.ClothManager.Initialize",
    "BeyondDynamicBone.PreBuildManager.Initialize",
    "BeyondDynamicBone.DynamicBoneTransformManager.Initialize",
    "BeyondDynamicBone.TeamManager.Initialize",
    "BeyondDynamicBone.VirtualMeshManager.Initialize",
    "BeyondDynamicBone.RenderManager.Initialize",
    "BeyondDynamicBone.ColliderManager.Initialize",
    "BeyondDynamicBone.SimulationManager.Initialize",
    "BeyondDynamicBone.TimeManager.Initialize",
    "BeyondDynamicBone.WindManager.Initialize",
    "BeyondDynamicBone.MagicaManager.InitCustomGameLoop",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, *, repo_path: bool = False) -> dict:
    record = {
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }
    if repo_path:
        record["repo_path"] = path.relative_to(REPO_ROOT).as_posix()
    else:
        record["path_at_recovery"] = path.as_posix()
    return record


def canonical_sha(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pptr_id(value: object) -> int:
    if not isinstance(value, dict):
        raise ValueError(f"expected PPtr dictionary, got {value!r}")
    return int(value["m_PathID"])


def method_calls(row: dict) -> list[str]:
    calls: list[str] = []
    for call in row.get("directCalls", []):
        for target in call.get("resolved", []):
            name = f"{target['type']}.{target['method']}"
            if name not in calls:
                calls.append(name)
    return calls


def read_pe_value(path: Path, va: int, size: int) -> bytes:
    data = path.read_bytes()
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    image_base = struct.unpack_from("<Q", data, optional_offset + 24)[0]
    section_offset = optional_offset + optional_size
    rva = va - image_base
    for index in range(section_count):
        offset = section_offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        span = max(virtual_size, raw_size)
        if virtual_address <= rva < virtual_address + span:
            file_offset = raw_offset + rva - virtual_address
            return data[file_offset : file_offset + size]
    raise ValueError(f"VA 0x{va:x} is outside PE sections")


def actor_manifest(actor: dict) -> tuple[Path, dict]:
    root = (
        LAB_ROOT
        / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable"
        / actor["manifest_dir"]
    )
    candidates = sorted(root.glob("*_ui_recovery_manifest.json"))
    if len(candidates) != 1:
        raise ValueError(
            f"{actor['manifest_dir']}: expected one maintained UI recovery manifest, "
            f"found {len(candidates)} under {root}"
        )
    path = candidates[0]
    return path, load_json(path)


def overview_controller_path(token: str, actor: dict, manifest: dict) -> Path:
    """Resolve the source controller directly from maintained manifest inputs."""

    usage = manifest.get("original_usage") or {}
    overview = recover_main_overview_controller(
        {
            "character_id": actor["character_id"],
            "ui_animation": {
                "selected_entries": usage.get("selected_ui_clip_assets") or [],
                "selected_companion_widget_entries": (
                    usage.get("selected_ui_item_widget_clip_assets") or []
                ),
            },
        }
    )
    source = str(overview.get("source_json") or "")
    if not source:
        raise ValueError(
            f"{token}: maintained controller recovery did not resolve an Overview source JSON"
        )
    return Path(source)


def actor_contract(token: str, actor: dict) -> dict:
    filter_path = EVIDENCE_ROOT / f"{token}_postmodel_monobehaviour_filter.json"
    export_root = EVIDENCE_ROOT / f"{token}_postmodel_export/MonoBehaviour"
    filters = load_json(filter_path)
    if not filters:
        raise ValueError(f"empty filter for {token}")
    if {row["Container"] for row in filters} != {actor["container"]}:
        raise ValueError(f"container mismatch for {token}")

    manifest_path, manifest = actor_manifest(actor)
    transform_by_id = {int(row["path_id"]): row["path"] for row in manifest["transforms"]}
    game_object_by_id = {
        int(row["game_object_path_id"]): row["path"] for row in manifest["transforms"]
    }

    objects: dict[int, dict] = {}
    for path in export_root.glob("*.json"):
        payload = load_json(path)
        objects[int(payload["$animestudio"]["pathId"])] = payload
    if len(objects) != len(filters):
        raise ValueError(f"{token}: {len(objects)} exports != {len(filters)} filters")

    dynamic_objects = {
        path_id: payload
        for path_id, payload in objects.items()
        if int(payload["m_Script"]["m_PathID"]) in SCRIPT_TYPES
    }
    cloths: list[dict] = []
    colliders: list[dict] = []
    counts: Counter[str] = Counter()

    for path_id, payload in sorted(dynamic_objects.items()):
        script_id = int(payload["m_Script"]["m_PathID"])
        type_name = SCRIPT_TYPES[script_id]
        counts[type_name] += 1
        game_object_id = pptr_id(payload["m_GameObject"])
        game_object_path = game_object_by_id.get(game_object_id)
        if game_object_path is None:
            raise ValueError(f"{token}: unresolved GameObject {game_object_id}")
        raw = payload["$animestudio"]

        if type_name != "BeyondDynamicBone.BeyondBoneCloth":
            record = {
                "path_id": path_id,
                "type": type_name,
                "script_path_id": script_id,
                "game_object_path": game_object_path,
                "enabled": int(payload["m_Enabled"]),
                "center": payload["center"],
                "size": payload["size"],
                "raw_data_sha256": raw["rawDataSha256"],
                "raw_data_length": raw["rawDataLength"],
            }
            if type_name.endswith("CapsuleCollider"):
                record.update(
                    {
                        "direction": payload["direction"],
                        "reverse_direction": payload["reverseDirection"],
                        "radius_separation": payload["radiusSeparation"],
                        "aligned_on_center": payload["alignedOnCenter"],
                    }
                )
            colliders.append(record)
            continue

        serialized = payload["serializeData"]
        serialized2 = payload["serializeData2"]
        root_bones = []
        for value in serialized["rootBones"]:
            transform_id = pptr_id(value)
            if transform_id not in transform_by_id:
                raise ValueError(f"{token}: unresolved cloth root {transform_id}")
            root_bones.append(
                {"path_id": transform_id, "path": transform_by_id[transform_id]}
            )
        ignored = []
        for value in serialized["ignoreFromRootBones"]:
            transform_id = pptr_id(value)
            if transform_id not in transform_by_id:
                raise ValueError(f"{token}: unresolved ignored root {transform_id}")
            ignored.append(
                {"path_id": transform_id, "path": transform_by_id[transform_id]}
            )
        collider_refs = []
        for value in serialized["colliderCollisionConstraint"]["colliderList"]:
            collider_id = pptr_id(value)
            target = dynamic_objects.get(collider_id)
            if target is None:
                raise ValueError(f"{token}: unresolved collider component {collider_id}")
            target_script = int(target["m_Script"]["m_PathID"])
            target_go = pptr_id(target["m_GameObject"])
            collider_refs.append(
                {
                    "path_id": collider_id,
                    "type": SCRIPT_TYPES[target_script],
                    "game_object_path": game_object_by_id[target_go],
                }
            )

        selection = serialized2["selectionData"]
        prebuild = serialized2["preBuildData"]
        cloths.append(
            {
                "path_id": path_id,
                "type": type_name,
                "script_path_id": script_id,
                "game_object_path": game_object_path,
                "enabled": int(payload["m_Enabled"]),
                "root_bones": root_bones,
                "ignored_root_bones": ignored,
                "colliders": collider_refs,
                "raw_data_sha256": raw["rawDataSha256"],
                "raw_data_length": raw["rawDataLength"],
                "serialize_data_sha256": canonical_sha(serialized),
                "serialize_data2_sha256": canonical_sha(serialized2),
                "parameters": {
                    "cloth_type": serialized["clothType"],
                    "update_mode": serialized["updateMode"],
                    "animator_ability_lod_threshold": serialized[
                        "clothAnimatorAbilityLODThreshold"
                    ],
                    "animator_lod_threshold": serialized["clothAnimatorLODThreshold"],
                    "lod_fade_time": serialized["clothLodFadeTime"],
                    "simulate_weight": serialized["clothSimulateWeight"],
                    "reset_to_animation_pose_when_weight_low": serialized[
                        "resetSimulationToAnimationPoseWhenWeightLow"
                    ],
                    "reset_weight_threshold": serialized[
                        "resetSimulationToAnimationPoseWeightThreshold"
                    ],
                    "animation_pose_ratio": serialized["animationPoseRatio"],
                    "gravity": serialized["gravity"],
                    "gravity_direction": serialized["gravityDirection"],
                    "gravity_falloff": serialized["gravityFalloff"],
                    "stabilization_time_after_reset": serialized[
                        "stablizationTimeAfterReset"
                    ],
                    "blend_weight": serialized["blendWeight"],
                    "culling": serialized["cullingSettings"],
                    "wind": serialized["wind"],
                    "spring": serialized["springConstraint"],
                    "damping_sha256": canonical_sha(serialized["damping"]),
                    "radius_sha256": canonical_sha(serialized["radius"]),
                    "inertia_sha256": canonical_sha(serialized["inertiaConstraint"]),
                    "tether_sha256": canonical_sha(serialized["tetherConstraint"]),
                    "distance_sha256": canonical_sha(serialized["distanceConstraint"]),
                    "triangle_bending_sha256": canonical_sha(
                        serialized["triangleBendingConstraint"]
                    ),
                    "angle_restoration_sha256": canonical_sha(
                        serialized["angleRestorationConstraint"]
                    ),
                    "angle_limit_sha256": canonical_sha(
                        serialized["angleLimitConstraint"]
                    ),
                    "motion_sha256": canonical_sha(serialized["motionConstraint"]),
                    "collision_sha256": canonical_sha(
                        serialized["colliderCollisionConstraint"]
                    ),
                    "self_collision_sha256": canonical_sha(
                        serialized["selfCollisionConstraint"]
                    ),
                },
                "selection": {
                    "position_count": len(selection["positions"]),
                    "attribute_count": len(selection["attributes"]),
                    "max_connection_distance": selection["maxConnectionDistance"],
                    "user_edit": selection["userEdit"],
                    "prebuild_enabled": prebuild["enabled"],
                    "selection_sha256": canonical_sha(selection),
                    "prebuild_sha256": canonical_sha(prebuild),
                },
            }
        )

    controller_path = overview_controller_path(token, actor, manifest)
    source_rows = {(row["Source"], int(row["Offset"])) for row in filters}
    if len(source_rows) != 1:
        raise ValueError(f"{token}: expected one source/offset, got {source_rows}")
    source_path, source_offset = next(iter(source_rows))

    controller_record = (
        file_record(controller_path, repo_path=True)
        if controller_path.is_file()
        else {
            "status": "source_json_missing",
            "repo_path": controller_path.as_posix(),
        }
    )

    return {
        "character_id": actor["character_id"],
        "display_name": actor["display_name"],
        "container": actor["container"],
        "source_chunk": Path(source_path).name,
        "source_offset": source_offset,
        "mono_behaviour_count": len(objects),
        "dynamic_component_counts": dict(sorted(counts.items())),
        "overview_controller": {
            **controller_record,
            "magica_cloth_weight": manifest["overview_playback"][
                "magica_cloth_weight"
            ],
        },
        "hierarchy_name_map": {
            **file_record(manifest_path, repo_path=True),
            "note": "Used only to resolve current path IDs to hierarchy names; embedded prior source-chunk records are not evidence for this contract.",
        },
        "target_filter": file_record(filter_path, repo_path=True),
        "cloths": cloths,
        "colliders": colliders,
    }


def runtime_contract() -> dict:
    native_path = EVIDENCE_ROOT / "lifecycle_native.json"
    native = load_json(native_path)
    rows = {
        (row["type"], row["method"]): row for row in native["bodyTargets"]
    }
    assembly_data = GAME_ASSEMBLY.read_bytes()
    method_records = []
    for key, ifix_gate in METHODS.items():
        row = rows.get(key)
        if row is None:
            raise ValueError(f"missing native method {key}")
        offset = int(row["fileOffset"], 16)
        size = int(row["scanBytes"])
        body = assembly_data[offset : offset + size]
        if len(body) != size:
            raise ValueError(f"truncated method body {key}")
        if ifix_gate is not None and struct.pack("<I", ifix_gate) not in body:
            raise ValueError(f"IFix gate 0x{ifix_gate:x} absent from {key}")
        method_records.append(
            {
                "type": key[0],
                "method": key[1],
                "method_index": row["methodIndex"],
                "va": row["methodPointerVa"],
                "file_offset": row["fileOffset"],
                "bytes": size,
                "sha256": hashlib.sha256(body).hexdigest(),
                "ifix_gate": None if ifix_gate is None else f"0x{ifix_gate:x}",
            }
        )

    manager = rows[("BeyondDynamicBone.MagicaManager", "Initialize")]
    observed_order = [name for name in method_calls(manager) if name in MANAGER_INIT_ORDER]
    if observed_order != MANAGER_INIT_ORDER:
        raise ValueError(f"manager initialization order changed: {observed_order}")

    set_loop = rows[("BeyondDynamicBone.MagicaManager", "SetCustomGameLoop")]
    add_loop_count = sum(
        1
        for call in set_loop["directCalls"]
        for target in call.get("resolved", [])
        if target["type"] == "BeyondDynamicBone.PlayerLoopUtils"
        and target["method"] == "AddPlayerLoop"
    )
    if add_loop_count != 7:
        raise ValueError(f"expected seven PlayerLoop insertions, got {add_loop_count}")

    callbacks = []
    callback_slots = {
        "<SetCustomGameLoop>b__40_0": 0x10,
        "<SetCustomGameLoop>b__40_1": 0x18,
        "<SetCustomGameLoop>b__40_2": 0x20,
        "<SetCustomGameLoop>b__40_3": 0x28,
        "<SetCustomGameLoop>b__40_4": 0x30,
        "<SetCustomGameLoop>b__40_5": 0x38,
        "<SetCustomGameLoop>b__40_6": 0x40,
    }
    callback_roles = [
        "afterEarlyUpdateDelegate",
        "afterFixedUpdateDelegate_plus_core_ClothUpdate",
        "afterUpdateDelegate_plus_isPlaying_refresh",
        "beforeLateUpdateDelegate",
        "afterLateUpdateDelegate",
        "afterDelayedDelegate",
        "afterRenderingDelegate",
    ]
    for (method, slot), role in zip(callback_slots.items(), callback_roles):
        row = rows[("BeyondDynamicBone.MagicaManager+<>c", method)]
        operands = {
            value["operand"] for value in row["methodBodySummary"]["topMemoryOperands"]
        }
        expected_operand = f"rcx+0x{slot:x}"
        if expected_operand not in operands:
            raise ValueError(f"{method} no longer reads delegate slot {expected_operand}")
        callbacks.append(
            {
                "method": method,
                "va": row["methodPointerVa"],
                "delegate_slot": f"0x{slot:x}",
                "role": role,
            }
        )

    constants = []
    for name, va, kind in (
        ("increase_speed", 0x18B9592C8, "float"),
        ("decrease_speed", 0x18B9594E4, "float"),
        ("enabled_target", 0x18B959200, "float"),
        ("write_suppression_threshold", 0x18B9593BC, "float"),
        ("nonzero_epsilon_bits", 0x18B959458, "uint32"),
        ("absolute_value_mask", 0x18B9592D0, "uint32"),
    ):
        raw = read_pe_value(GAME_ASSEMBLY, va, 4)
        value = struct.unpack("<f" if kind == "float" else "<I", raw)[0]
        constants.append(
            {"name": name, "va": f"0x{va:x}", "kind": kind, "value": value, "bytes": raw.hex()}
        )

    charui_path = EVIDENCE_ROOT / "charui_all_native.json"
    charui = load_json(charui_path)
    dynamic_calls = []
    for row in charui["bodyTargets"]:
        for call in row.get("directCalls", []):
            for target in call.get("resolved", []):
                if target["type"].startswith(("BeyondDynamicBone", "MagicaCloth")):
                    dynamic_calls.append(
                        {
                            "caller": row["method"],
                            "caller_method_index": row["methodIndex"],
                            "callee": f"{target['type']}.{target['method']}",
                        }
                    )
    expected_dynamic_calls = [
        {
            "caller": "_UpdateMagicaClothWeight",
            "caller_method_index": 49735,
            "callee": "BeyondDynamicBone.BeyondBoneCloth.SetClothSimulateWeight",
        }
    ]
    if dynamic_calls != expected_dynamic_calls:
        raise ValueError(f"CharUI dynamic call surface changed: {dynamic_calls}")

    return {
        "evidence": {
            "metadata_catalog": file_record(
                EVIDENCE_ROOT / "lifecycle_metadata.json", repo_path=True
            ),
            "native_map": file_record(native_path, repo_path=True),
            "charui_all_methods_native_map": file_record(charui_path, repo_path=True),
        },
        "method_bodies": method_records,
        "charui_model_owner": {
            "field_offsets": {
                "m_animator": "0xc8",
                "m_boneCloths": "0xe8",
                "m_magicaCloths": "0xf0",
                "m_physicsClothWeight": "0xf8",
                "m_lastPhysicsClothWeight": "0xfc",
            },
            "animator_parameter": "MagicaClothWeight",
            "parameter_semantics": "The absolute Animator parameter is compared with float epsilon. Any nonzero authored value selects target weight 1; zero selects target weight 0.",
            "weight_constants": constants,
            "write_route": "When abs(current-last) >= 0.001, the body loops m_boneCloths and calls BeyondBoneCloth.SetClothSimulateWeight(current), then writes the same current weight to every legacy m_magicaCloths entry and updates m_lastPhysicsClothWeight.",
            "tick_order": [
                "_TrySetWeaponStateByCurveValue",
                "_TickWeaponVFX",
                "Time.deltaTime",
                "_UpdateMagicaClothWeight",
                "_UpdateEmotionShaderProperty",
                "_UpdateDecoItemVisibilityByCurveValue",
                "_UpdatePotentialEffectVisibilityByCurveValue",
                "_UpdatePotentialVfxVisibilityByCurveValue",
            ],
            "all_method_call_audit": {
                "mapped_method_count": len(charui["bodyTargets"]),
                "dynamic_system_direct_calls": dynamic_calls,
                "conclusion": "No CharUIModelMono method directly initializes, disposes, increments, or decrements a cloth suspend counter. OnRelease unloads weapons/decos/effects but has no cloth call.",
            },
        },
        "component_lifecycle": {
            "cloth": [
                "Awake initializes animation-property state.",
                "OnEnable calls ClothProcess.StartUse.",
                "OnDisable calls ClothProcess.EndUse.",
                "Start initializes ClothProcess, removes build monitoring, and calls AutoBuild when applicable.",
                "OnDestroy disposes ClothProcess.",
            ],
            "collider": [
                "Start/Register enters ColliderManager.",
                "OnEnable and OnDisable call ColliderManager.EnableCollider with the component state.",
                "OnDestroy removes the collider from ColliderManager.",
            ],
            "wind_zone": [
                "Awake adds a zone to WindManager.",
                "OnEnable/OnDisable update its enable state.",
                "OnDestroy removes it.",
            ],
        },
        "manager": {
            "initialization_order": MANAGER_INIT_ORDER,
            "player_loop_insertion_count": add_loop_count,
            "callbacks": callbacks,
            "cloth_update_wind_edge": "ClothManager.ClothUpdate directly calls WindManager.AlwaysWindUpdate before the simulation/update phases.",
            "unresolved_boundary": "The seven category/system-name string pairs and exact before/last insertion booleans have not yet been mapped from IL2CPP string-usage globals. The callback delegates and their order/slots are exact; their named Unity PlayerLoop anchor pairs remain open.",
        },
    }


def ifix_boundary_contract(state_path: Path = IFIX_CONTRACT) -> dict:
    ifix = load_json(state_path)
    overlay = ifix["vfs_state"]["persistent_overlay"]
    targets = ifix["targets"]
    if overlay["file_count"] != 1:
        raise ValueError("installed IFix contract no longer has exactly one patch file")
    if ifix["patch_format"]["target_count"] != len(targets):
        raise ValueError("installed IFix contract target count does not match its target rows")
    if any(target["type"].startswith("BeyondDynamicBone") for target in targets):
        raise ValueError("installed IFix contract unexpectedly targets BeyondDynamicBone")
    return {
        **file_record(state_path, repo_path=True),
        "persistent_patch_file_count": 1,
        "persistent_patch_assembly": "Gameplay.Beyond",
        "persistent_target_count": len(targets),
        "beyond_dynamic_bone_patch_present": False,
        "charui_model_target_present": any(
            target["type"] == "Beyond.Gameplay.View.CharUIModelMono"
            for target in targets
        ),
        "boundary": "This proves the current local snapshot only. A later Persistent or network-delivered patch requires a fresh audit.",
    }


def refresh_ifix_boundary_payload(payload: dict, state_path: Path = IFIX_CONTRACT) -> dict:
    if payload.get("schema") != "endfield.charinfo.secondary-dynamics-owner.v1":
        raise ValueError("secondary-dynamics owner report schema drifted")
    refreshed = dict(payload)
    refreshed["ifix_boundary"] = ifix_boundary_contract(state_path)
    return refreshed


def charinfo_environment_contract() -> dict:
    filter_path = EVIDENCE_ROOT / "charinfochar_monobehaviour_filter.json"
    export_root = EVIDENCE_ROOT / "charinfochar_monobehaviour_export/MonoBehaviour"
    filters = load_json(filter_path)
    objects = [load_json(path) for path in export_root.glob("*.json")]
    if len(filters) != len(objects):
        raise ValueError("CharInfo environment filter/export count mismatch")
    dynamic = []
    object_pins = []
    for payload in objects:
        script_id = int(payload["m_Script"]["m_PathID"])
        if script_id in SCRIPT_TYPES or {
            "mode",
            "size",
            "radius",
            "main",
            "turbulence",
            "directionAngleX",
            "directionAngleY",
            "attenuation",
            "isAddition",
        }.issubset(payload):
            dynamic.append(payload["$animestudio"]["pathId"])
        object_pins.append(
            (
                int(payload["$animestudio"]["pathId"]),
                payload["$animestudio"]["rawDataSha256"],
            )
        )
    if dynamic:
        raise ValueError(f"CharInfo environment gained dynamic components: {dynamic}")
    source_rows = {(row["Source"], int(row["Offset"])) for row in filters}
    if len(source_rows) != 1:
        raise ValueError("CharInfo environment spans unexpected source rows")
    source, offset = next(iter(source_rows))
    return {
        "container": "assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab",
        "source_chunk": Path(source).name,
        "source_offset": offset,
        "mono_behaviour_count": len(objects),
        "target_filter": file_record(filter_path, repo_path=True),
        "object_pin_set_sha256": canonical_sha(sorted(object_pins)),
        "cloth_component_count": 0,
        "collider_component_count": 0,
        "wind_zone_component_count": 0,
        "conclusion": "The Character Info environment prefab does not own a local secondary-dynamics component or wind zone. Dynamics arrive with the selected character postmodel.",
    }


def build_contract() -> dict:
    actor_rows = {token: actor_contract(token, actor) for token, actor in ACTORS.items()}
    chunk_names = sorted({row["source_chunk"] for row in actor_rows.values()})
    chunks = {}
    for name in chunk_names:
        path = GAME_ROOT / "Endfield_Data/StreamingAssets/VFS/7064D8E2" / name
        chunks[name] = file_record(path)

    total_counts: Counter[str] = Counter()
    for row in actor_rows.values():
        total_counts.update(row["dynamic_component_counts"])

    return {
        "schema": "endfield.charinfo.secondary-dynamics-owner.v1",
        "recovered_at": "2026-07-17",
        "scope": "Current installed original data and static native-code evidence only; no Unity/game launch and no video-fit parameters.",
        "outcome": "The current retail postmodels use the BeyondDynamicBone.dll fork, not the stale removed-chunk MagicaCloth.BoneCloth serialization. Character Info drives one model-local solver set through MagicaClothWeight and normal component enable/disable lifecycle.",
        "source_build": {
            "game_assembly": file_record(GAME_ASSEMBLY),
            "global_metadata": file_record(GLOBAL_METADATA),
            "code_registration": "0x18b9217d0",
            "asset_map": file_record(ASSET_MAP, repo_path=True),
            "vfs_chunks": chunks,
        },
        "script_identity": {
            str(key): value for key, value in SCRIPT_TYPES.items()
        },
        "script_identity_evidence": {
            "capsule": "Serialized center/size plus direction, reverseDirection, radiusSeparation, and alignedOnCenter exactly match BeyondBoneCapsuleCollider metadata.",
            "sphere": "The -7738307689003339598 script serializes only inherited center/size, always carries a positive size.x radius in these postmodels, and is referenced at spherical cape/head collision points.",
            "plane": "The 7481586941717068173 script serializes only inherited center/size, always has zero size, and Li Zhiyan names one owner PelvisPlaneCollider; this distinguishes it from BeyondBoneSphereCollider.",
        },
        "actors": actor_rows,
        "totals": dict(sorted(total_counts.items())),
        "common_serialized_invariants": {
            "cloth_type": 1,
            "cloth_type_name": "BoneCloth",
            "update_mode": 10,
            "animator_ability_lod_threshold": 2,
            "animator_lod_threshold": 9,
            "lod_fade_time": 2.0,
            "authored_simulate_weight": 1.0,
            "camera_culling_mode": 30,
            "distance_culling_enabled": 0,
            "blend_weight": 1.0,
            "prebuild_enabled": 0,
            "note": "All 50 solvers share these values. Per-solver gravity, pose ratio, reset threshold, wind, spring, curves, constraints, roots, and colliders remain actor-authored and are pinned above.",
        },
        "runtime": runtime_contract(),
        "charinfo_environment": charinfo_environment_contract(),
        "ifix_boundary": ifix_boundary_contract(),
        "implementation_boundary": {
            "lab_solver_implemented": False,
            "reason": "The project does not contain BeyondDynamicBone.dll's runtime/Burst solver. Serialized ownership, parameter bridges, lifecycle, manager construction, and callback delegates are recovered, but exact PlayerLoop anchor strings, Burst job numerics, transform writeback, cross-frame scheduling, and retail-frame numeric fixtures remain open. A substitute spring chain would not be original-game recovery.",
            "safe_current_behavior": "Keep secondary dynamics disabled/fail-closed until an equivalent source-compatible runtime is available. Do not revive the stale MagicaCloth v7 dump as current evidence.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--prepare-filters",
        action="store_true",
        help="write bounded postmodel MonoBehaviour filters and stop",
    )
    mode.add_argument(
        "--refresh-ifix-boundary",
        action="store_true",
        help="refresh only the installed IFix projection in the checked-in owner report",
    )
    args = parser.parse_args()
    if args.prepare_filters:
        prepare_actor_filters()
        return 0
    if args.refresh_ifix_boundary:
        payload = refresh_ifix_boundary_payload(load_json(OUTPUT))
    else:
        payload = build_contract()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    if args.refresh_ifix_boundary:
        print(json.dumps(payload["ifix_boundary"], indent=2))
    else:
        print(json.dumps(payload["totals"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
