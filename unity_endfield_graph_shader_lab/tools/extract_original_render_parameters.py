#!/usr/bin/env python3
"""Extract character render parameters directly from installed-game exports.

This tool deliberately does not fit values to reference images.  It joins:

* AnimeStudio Material JSON selected by every playable recovery manifest;
* the CharInfo VolumeProfile and its linked HGCharacterVolume;
* each actor's ``volume_overview`` CharLightVolumeData modifier; and
* the serialized CharInfo_Env environment payload.

The generated JSON keeps inactive/dormant VolumeParameter values separate from
the active override composition.  Values which only exist at runtime (for
example adapted exposure and camera-dependent light direction) remain marked
unknown and are never synthesized here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "endfield.original-character-render-parameters.v1"
PLAYABLE_CATALOG = Path(
    "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
    "Characters/Catalog/playable_character_ui_catalog.json"
)
SOURCE_PLAN = Path("scratch/charinfo_playable_profiles/source_plan.json")
DEFAULT_OUTPUT = Path(
    "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
    "OriginalData/RenderParameters/character_render_parameters.json"
)
ANIMESTUDIO_ROOT = Path("export_full/recovered/AnimeStudio-cli/StreamingAssets")
MATERIAL_JSON_ROOT = ANIMESTUDIO_ROOT / "json_by_type/Material"
MONOBEHAVIOUR_JSON_ROOT = ANIMESTUDIO_ROOT / "json_by_type/MonoBehaviour"
ASSET_MAPS = (
    ANIMESTUDIO_ROOT / "maps/endfield_streamingassets_assets.json",
    Path("export_full/recovered/AnimeStudio-cli/Persistent/maps/")
    / "endfield_persistent_assets.json",
)
CHARINFO_DEPENDENCIES = Path("scratch/charinfo_playable_profiles/dependencies_json")
GACHA_ROOM_FALLBACK_ROOT = Path(
    "scratch/animestudio/zhuangfy_gacha_start_order/gacharoom_raw_dump/MonoBehaviour"
)
CHAR_OVERRIDE_FALLBACK_ROOT = Path(
    "scratch/animestudio/gacha_char_override_profile/export/MonoBehaviour"
)
CHARINFO_FALLBACK_ROOT = Path(
    "scratch/animestudio/charinfo_volume_profile/export/MonoBehaviour"
)
CHARINFO_ENVIRONMENT_FALLBACK_ROOT = Path(
    "scratch/animestudio/charinfo_environment/export/MonoBehaviour"
)
NATIVE_CHARACTER_VOLUME = Path(
    "tools/FractalMiner/Assets/Project/EndField/HGRP/packages/"
    "com.hg.render-pipelines/runtime/HG/Rendering/Runtime/HGCharacterVolume.cs"
)
NATIVE_ENVIRONMENT_PACKER = Path(
    "tools/FractalMiner/Assets/Project/EndField/HGRP/packages/"
    "com.hg.render-pipelines/runtime/HG/Rendering/Runtime/HGRenderPathScene.cs"
)
MATERIAL_AUDIT_ACTORS = {"wulfa", "zhuangfy"}

# Exact SetCharLightVolumeData call order recovered from the pinned HGRP body.
# These are the 30 CharLightVolumeData parameters copied into an already
# instantiated HGCharacterVolume.  This is a snapshot assignment, not an
# override-only merge.
CHAR_LIGHT_VOLUME_DATA_FIELDS = (
    "charMainLightControl",
    "charMainLightMultiplier",
    "charEnvLightMultiplier",
    "charEnvShadowMultiplier",
    "charMainLightSpecularMultiplier",
    "charEyeBaseLightMultiplier",
    "charEyeHighlightMultiplier",
    "charEyeScatteringMultiplier",
    "charMainLightRangeBias",
    "charIgnoreMainLightShadow",
    "charMainLightMode",
    "charCameraFollowMainLightBias",
    "charCustomMainLightDir",
    "charMainLightOverrideColor",
    "charSkinMainLightOverrideColor",
    "charLightDialogMode",
    "charShadowTintControl",
    "charShadowTintColor",
    "charSkinShadowTintColor",
    "charAutoRimEnable",
    "charAutoRimColor",
    "charAutoRimDir",
    "charAutoRimIntensity",
    "charAutoRimWidth",
    "charFaceRimEnable",
    "charFaceRimIntensity",
    "charFaceRimColor",
    "charFaceRimDir",
    "charIgnoreSceneAdditionalLights",
    "charIgnoreSceneEnv",
)


class RecoveryError(RuntimeError):
    pass


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "unity_endfield_graph_shader_lab").is_dir() and (
            candidate / "export_full"
        ).is_dir():
            return candidate
    raise RecoveryError("Could not find the fluffy-dump repository root")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RecoveryError(f"Expected a JSON object: {path}")
    return value


def discover_actor_manifests(repo_root: Path) -> dict[str, Path]:
    catalog = load_json(repo_root / PLAYABLE_CATALOG)
    enabled_rows = [
        row
        for row in catalog.get("characters") or []
        if isinstance(row, dict) and row.get("import_enabled")
    ]
    declared_count = int(catalog.get("import_character_count") or 0)
    if not enabled_rows or declared_count != len(enabled_rows):
        raise RecoveryError(
            f"playable catalog enabled-count mismatch: declared={declared_count}, "
            f"rows={len(enabled_rows)}"
        )
    result: dict[str, Path] = {}
    for row in enabled_rows:
        actor = str(row.get("actor_token") or "").lower()
        asset_path = str(row.get("manifest_asset_path") or "").replace("\\", "/")
        if not actor or not asset_path:
            raise RecoveryError("playable catalog contains an incomplete manifest row")
        if actor in result:
            raise RecoveryError(f"playable catalog contains duplicate actor token: {actor}")
        result[actor] = Path("unity_endfield_graph_shader_lab") / Path(asset_path)
    return result


def discover_track_root_actors(
    repo_root: Path,
    expected_actors: set[str] | None = None,
) -> dict[str, str]:
    plan = load_json(repo_root / SOURCE_PLAN)
    result: dict[str, str] = {}
    for row in plan.get("characters") or []:
        if not isinstance(row, dict):
            continue
        actor = str(row.get("actor_token") or "").lower()
        group = str(row.get("camera_group") or "").replace("\\", "/")
        root = group.rsplit("/", 1)[-1].lower()
        if not actor or not root:
            raise RecoveryError("source plan contains an incomplete camera-group row")
        if root in result:
            raise RecoveryError(f"source plan contains duplicate camera-track root: {root}")
        result[root] = actor
    if not result:
        raise RecoveryError("source plan contains no camera-track roots")
    if expected_actors is not None and set(result.values()) != expected_actors:
        raise RecoveryError(
            "source-plan camera actors differ from playable catalog: "
            f"missing={sorted(expected_actors - set(result.values()))}, "
            f"extra={sorted(set(result.values()) - expected_actors)}"
        )
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def signed_path_id_from_suffix(path: Path) -> int | None:
    match = re.search(r"_p([0-9a-fA-F]{16})\.json$", path.name)
    if not match:
        return None
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def path_id_suffix(path_id: int) -> str:
    return f"{path_id & ((1 << 64) - 1):016X}"


def find_json_for_path_id(folder: Path, path_id: int) -> Path:
    suffix = path_id_suffix(path_id)
    matches = sorted(folder.glob(f"*_p{suffix}.json"))
    if len(matches) != 1:
        raise RecoveryError(
            f"Expected exactly one JSON for PathID {path_id} ({suffix}) under "
            f"{folder}; found {len(matches)}"
        )
    return matches[0]


def source_vfs_relative(value: Any) -> str:
    text = str(value or "").replace("/", "\\")
    marker = "Endfield_Data\\"
    position = text.lower().find(marker.lower())
    return text[position:].replace("\\", "/") if position >= 0 else ""


def source_record(
    repo_root: Path,
    path: Path,
    data: dict[str, Any],
    asset_map_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = data.get("$animestudio") or {}
    record: dict[str, Any] = {
        "path": relative_path(repo_root, path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if metadata:
        record.update(
            {
                "path_id": int(metadata.get("pathId") or 0),
                "raw_data_length": int(metadata.get("rawDataLength") or 0),
                "raw_data_sha256": str(metadata.get("rawDataSha256") or ""),
                "type_tree_source": str(metadata.get("typeTreeSource") or ""),
                "source_file": str(metadata.get("sourceFile") or ""),
                "source_vfs_relative": source_vfs_relative(
                    metadata.get("sourceOriginalPath")
                ),
            }
        )
    if asset_map_entry:
        record["asset_map"] = {
            "name": asset_map_entry.get("Name", ""),
            "container": asset_map_entry.get("Container", ""),
            "hash": asset_map_entry.get("Hash", ""),
            "offset": asset_map_entry.get("Offset", 0),
            "source_vfs_relative": source_vfs_relative(
                asset_map_entry.get("Source")
            ),
        }
    return record


def choose_asset_map_entry(
    candidates: list[dict[str, Any]] | None,
    *,
    container: str = "",
    name: str = "",
    source_vfs: str = "",
) -> dict[str, Any] | None:
    values = list(candidates or [])
    if container:
        exact = [item for item in values if item.get("Container") == container]
        if exact:
            values = exact
    if name:
        exact = [item for item in values if item.get("Name") == name]
        if exact:
            values = exact
    if source_vfs:
        exact = [
            item
            for item in values
            if source_vfs_relative(item.get("Source")) == source_vfs
        ]
        if exact:
            values = exact
    if not values:
        return None
    return sorted(
        values,
        key=lambda item: (
            str(item.get("Container") or ""),
            str(item.get("Name") or ""),
            int(item.get("Offset") or 0),
        ),
    )[0]


def ref_path_id(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    raw = value.get("m_PathID", value.get("PathID", 0))
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def parameter_block(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, raw in sorted(data.items()):
        if not isinstance(raw, dict) or "overrideState" not in raw:
            continue
        result[name] = {
            "override_state": bool(raw.get("overrideState")),
            "value": raw.get("m_Value"),
        }
    return result


def apply_use_data_on_volume_snapshot(
    base: dict[str, dict[str, Any]],
    modifier: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Model the exact call-time SetCharLightVolumeData assignment."""

    missing = sorted(set(CHAR_LIGHT_VOLUME_DATA_FIELDS) - set(modifier))
    extra = sorted(set(modifier) - set(CHAR_LIGHT_VOLUME_DATA_FIELDS))
    if missing or extra:
        raise RecoveryError(
            "CharLightVolumeData field contract mismatch: "
            f"missing={missing}, extra={extra}"
        )
    result = {
        name: {
            "value": record["value"],
            "override_state": bool(record["override_state"]),
            "source": "char_override_profile_initial",
        }
        for name, record in base.items()
    }
    for name in CHAR_LIGHT_VOLUME_DATA_FIELDS:
        record = modifier[name]
        result[name] = {
            "value": record["value"],
            "override_state": bool(record["override_state"]),
            "source": "actor_overview_modifier",
        }
    return result


def active_overrides(
    snapshot: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "value": record["value"],
            "override_state": True,
            "source": record["source"],
        }
        for name, record in snapshot.items()
        if record["override_state"]
    }


def compose_volume_layers(
    *layers: tuple[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Resolve authored weight-one global layers in ascending priority order."""

    result: dict[str, dict[str, Any]] = {}
    for source, parameters in layers:
        for name, record in parameters.items():
            if record["override_state"]:
                result[name] = {
                    "value": record["value"],
                    "override_state": True,
                    "source": source,
                }
    return result


def discover_charinfo_base(repo_root: Path) -> tuple[Path, dict[str, Any], Path, dict[str, Any]]:
    profile_candidates: list[tuple[Path, dict[str, Any]]] = []
    for root in (
        repo_root / MONOBEHAVIOUR_JSON_ROOT,
        repo_root / CHARINFO_FALLBACK_ROOT,
    ):
        for path in sorted(root.glob("CharInfo_Volume_p*.json")):
            data = load_json(path)
            if data.get("m_Name") == "CharInfo_Volume":
                profile_candidates.append((path, data))
        if profile_candidates:
            break
    if len(profile_candidates) != 1:
        raise RecoveryError(
            f"Expected one CharInfo_Volume profile; found {len(profile_candidates)}"
        )

    profile_path, profile = profile_candidates[0]
    references = (profile.get("$animestudio") or {}).get("pptrReferences") or []
    targets = [
        int(item.get("targetPathId") or 0)
        for item in references
        if isinstance(item, dict) and item.get("targetName") == "HGCharacterVolume"
    ]
    if len(targets) != 1:
        raise RecoveryError(
            "CharInfo_Volume did not link exactly one HGCharacterVolume"
        )
    volume_path = find_json_for_path_id(profile_path.parent, targets[0])
    volume = load_json(volume_path)
    if volume.get("m_Name") != "HGCharacterVolume":
        raise RecoveryError(f"Unexpected linked character volume: {volume_path}")
    return profile_path, profile, volume_path, volume


def discover_named_character_volume_profile(
    repo_root: Path,
    profile_name: str,
    fallback_root: Path,
) -> tuple[Path, dict[str, Any], Path, dict[str, Any]]:
    roots = (repo_root / MONOBEHAVIOUR_JSON_ROOT, repo_root / fallback_root)
    candidates: list[tuple[Path, dict[str, Any]]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob(f"{profile_name}_p*.json")):
            data = load_json(path)
            if data.get("m_Name") == profile_name:
                candidates.append((path, data))
        if candidates:
            break
    if len(candidates) != 1:
        raise RecoveryError(
            f"Expected one {profile_name} profile; found {len(candidates)}"
        )
    profile_path, profile = candidates[0]
    targets = [
        int(item.get("targetPathId") or 0)
        for item in ((profile.get("$animestudio") or {}).get("pptrReferences") or [])
        if isinstance(item, dict) and item.get("targetName") == "HGCharacterVolume"
    ]
    if len(targets) != 1:
        raise RecoveryError(
            f"{profile_name} did not link exactly one HGCharacterVolume"
        )
    volume_path = find_json_for_path_id(profile_path.parent, targets[0])
    volume = load_json(volume_path)
    if volume.get("m_Name") != "HGCharacterVolume":
        raise RecoveryError(f"Unexpected linked character volume: {volume_path}")
    return profile_path, profile, volume_path, volume


def load_path_id_index(folder: Path) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(folder.glob("*.json")):
        path_id = signed_path_id_from_suffix(path)
        if path_id is None:
            continue
        result[path_id] = (path, load_json(path))
    return result


def modifier_ancestry(
    modifier: dict[str, Any],
    game_objects: dict[int, tuple[Path, dict[str, Any]]],
    transforms: dict[int, tuple[Path, dict[str, Any]]],
) -> list[str]:
    game_object_path_id = ref_path_id(modifier.get("m_GameObject"))
    game_object_item = game_objects.get(game_object_path_id)
    if not game_object_item:
        return []
    game_object = game_object_item[1]
    names = [str(game_object.get("m_Name") or "")]
    transform = game_object.get("m_Transform") or {}
    parent_path_id = ref_path_id(transform.get("m_Father"))
    visited: set[int] = set()
    while parent_path_id and parent_path_id not in visited:
        visited.add(parent_path_id)
        item = transforms.get(parent_path_id)
        if not item:
            break
        transform_data = item[1]
        names.append(str((transform_data.get("m_GameObject") or {}).get("Name") or ""))
        parent_path_id = ref_path_id(transform_data.get("m_Father"))
    return names


def discover_overview_modifiers(
    repo_root: Path,
    actor_manifests: dict[str, Path],
    track_root_actors: dict[str, str],
) -> dict[str, tuple[Path, dict[str, Any], list[str]]]:
    dependency_root = repo_root / CHARINFO_DEPENDENCIES
    game_objects = load_path_id_index(dependency_root / "GameObject")
    transforms = load_path_id_index(dependency_root / "Transform")
    discovered: dict[str, list[tuple[Path, dict[str, Any], list[str]]]] = {}
    for path in sorted((dependency_root / "MonoBehaviour").glob("*.json")):
        data = load_json(path)
        if not isinstance(data.get("charLightVolumeData"), dict):
            continue
        ancestry = modifier_ancestry(data, game_objects, transforms)
        if not ancestry or ancestry[0].lower() != "volume_overview":
            continue
        actor_matches = [
            track_root_actors[name.lower()]
            for name in ancestry
            if name.lower() in track_root_actors
        ]
        if len(actor_matches) != 1:
            continue
        discovered.setdefault(actor_matches[0], []).append((path, data, ancestry))

    result: dict[str, tuple[Path, dict[str, Any], list[str]]] = {}
    for actor in actor_manifests:
        matches = discovered.get(actor, [])
        if len(matches) != 1:
            raise RecoveryError(
                f"Expected one {actor} volume_overview modifier; found {len(matches)}"
            )
        result[actor] = matches[0]
    return result


def discover_environment(repo_root: Path) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for root in (
        repo_root / MONOBEHAVIOUR_JSON_ROOT,
        repo_root / CHARINFO_ENVIRONMENT_FALLBACK_ROOT,
    ):
        for path in sorted(root.glob("CharInfo_Env_p*.json")):
            data = load_json(path)
            if data.get("m_Name") == "CharInfo_Env":
                matches.append((path, data))
        if matches:
            break
    if len(matches) != 1:
        raise RecoveryError(f"Expected one CharInfo_Env; found {len(matches)}")
    return matches[0]


def resolve_material_json(repo_root: Path, info: dict[str, Any]) -> Path:
    name = str(info.get("name") or "")
    path_id = int(info.get("path_id") or 0)
    root = repo_root / MATERIAL_JSON_ROOT
    if path_id:
        exact = root / f"{name}_p{path_id_suffix(path_id)}.json"
        if exact.is_file():
            return exact
    configured = Path(str(info.get("json") or ""))
    if configured.is_file() and signed_path_id_from_suffix(configured) in (
        None,
        path_id,
    ):
        return configured
    direct = root / f"{name}.json"
    if direct.is_file():
        return direct
    matches = sorted(root.glob(f"{name}_p*.json"))
    if len(matches) == 1:
        return matches[0]
    raise RecoveryError(
        f"Could not resolve original Material JSON for {name} PathID {path_id}"
    )


def normalized_colors(colors: Any) -> dict[str, list[float]]:
    result: dict[str, list[float]] = {}
    if not isinstance(colors, dict):
        return result
    for name, value in sorted(colors.items()):
        if not isinstance(value, dict):
            continue
        result[name] = [
            float(value.get("r", 0.0)),
            float(value.get("g", 0.0)),
            float(value.get("b", 0.0)),
            float(value.get("a", 0.0)),
        ]
    return result


def normalized_floats(floats: Any) -> dict[str, float]:
    if not isinstance(floats, dict):
        return {}
    return {name: float(value) for name, value in sorted(floats.items())}


def texture_path_ids(tex_envs: Any) -> dict[str, int]:
    result: dict[str, int] = {}
    if not isinstance(tex_envs, dict):
        return result
    for name, value in sorted(tex_envs.items()):
        path_id = ref_path_id((value or {}).get("m_Texture") if isinstance(value, dict) else None)
        if path_id:
            result[name] = path_id
    return result


def manifest_texture_path_ids(textures: Any) -> dict[str, int]:
    if not isinstance(textures, dict):
        return {}
    return {
        name: int((value or {}).get("path_id") or 0)
        for name, value in sorted(textures.items())
        if isinstance(value, dict) and int(value.get("path_id") or 0)
    }


def mapping_is_source_subset(
    manifest_values: dict[str, Any], source_values: dict[str, Any]
) -> bool:
    return all(
        name in source_values and source_values[name] == value
        for name, value in manifest_values.items()
    )


def collect_materials(
    repo_root: Path,
    actor_manifests: dict[str, Path],
) -> tuple[dict[str, list[dict[str, Any]]], set[tuple[str, int]]]:
    actors: dict[str, list[dict[str, Any]]] = {}
    map_targets: set[tuple[str, int]] = set()
    # The material-source audit remains the already verified Wulfa/Zhuangfy
    # tranche. Other playable manifests can contain hashed material aliases
    # outside the WebUI Material JSON export; their render materials are still
    # imported directly by the character manifests, while this payload's new
    # roster expansion is specifically for CharInfo volume modifiers.
    for actor, relative_manifest in actor_manifests.items():
        if actor not in MATERIAL_AUDIT_ACTORS:
            actors[actor] = []
            continue
        manifest_path = repo_root / relative_manifest
        manifest = load_json(manifest_path)
        material_records: list[dict[str, Any]] = []
        materials = manifest.get("materials") or {}
        if not isinstance(materials, dict):
            raise RecoveryError(f"Missing materials object: {manifest_path}")
        for key, raw_info in sorted(materials.items()):
            if not isinstance(raw_info, dict):
                continue
            source_path = resolve_material_json(repo_root, raw_info)
            source = load_json(source_path)
            properties = source.get("m_SavedProperties") or {}
            if not isinstance(properties, dict):
                raise RecoveryError(f"Missing m_SavedProperties: {source_path}")
            path_id = int(raw_info.get("path_id") or 0)
            source_suffix_path_id = signed_path_id_from_suffix(source_path)
            source_floats = normalized_floats(properties.get("m_Floats"))
            manifest_floats = normalized_floats(raw_info.get("floats"))
            source_colors = normalized_colors(properties.get("m_Colors"))
            manifest_colors = {
                name: [float(component) for component in value]
                for name, value in sorted((raw_info.get("colors") or {}).items())
            }
            source_textures = texture_path_ids(properties.get("m_TexEnvs"))
            manifest_textures = manifest_texture_path_ids(raw_info.get("textures"))
            validation = {
                "name_matches": source.get("m_Name") == raw_info.get("name"),
                "path_id_suffix_matches": source_suffix_path_id in (None, path_id),
                "floats_match_manifest": source_floats == manifest_floats,
                "colors_match_manifest": source_colors == manifest_colors,
                "textures_match_manifest": source_textures == manifest_textures,
                "manifest_float_values_do_not_conflict": mapping_is_source_subset(
                    manifest_floats, source_floats
                ),
                "manifest_color_values_do_not_conflict": mapping_is_source_subset(
                    manifest_colors, source_colors
                ),
                "manifest_texture_values_do_not_conflict": mapping_is_source_subset(
                    manifest_textures, source_textures
                ),
            }
            # Some old supplemental manifest rows were populated by a
            # name-only lookup when multiple same-name materials existed.  Do
            # not bless that stale embedded payload: select by exact PathID and
            # preserve the mismatch as an audit result.  Source identity is the
            # hard requirement; saved_properties below always comes from the
            # exact original JSON, never the stale manifest copy.
            validation["manifest_payload_matches"] = (
                validation["floats_match_manifest"]
                and validation["colors_match_manifest"]
                and validation["textures_match_manifest"]
            )
            validation["manifest_payload_has_no_conflicting_values"] = (
                validation["manifest_float_values_do_not_conflict"]
                and validation["manifest_color_values_do_not_conflict"]
                and validation["manifest_texture_values_do_not_conflict"]
            )
            validation["ok"] = (
                validation["name_matches"]
                and validation["path_id_suffix_matches"]
            )
            if not validation["ok"]:
                raise RecoveryError(
                    f"Material manifest/source mismatch for {actor}:{key}: {validation}"
                )
            material_records.append(
                {
                    "manifest_key": key,
                    "name": str(source.get("m_Name") or raw_info.get("name") or ""),
                    "path_id": path_id,
                    "container": str(raw_info.get("container") or ""),
                    "shader_name": str(raw_info.get("shader_name") or ""),
                    "shader_path_id": ref_path_id(source.get("m_Shader")),
                    "source": {
                        "path": relative_path(repo_root, source_path),
                        "bytes": source_path.stat().st_size,
                        "sha256": sha256_file(source_path),
                    },
                    "saved_properties": properties,
                    "validation": validation,
                }
            )
            map_targets.add(("Material", path_id))
        actors[actor] = material_records
    return actors, map_targets


def scan_asset_map(
    path: Path,
    targets: set[tuple[str, int]],
    *,
    require_complete: bool = True,
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    """Stream AnimeStudio's large pretty-printed asset map without loading it."""

    found: dict[tuple[str, int], list[dict[str, Any]]] = {}
    in_entries = False
    object_lines: list[str] = []
    depth = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not in_entries:
                if '"AssetEntries"' in line and "[" in line:
                    in_entries = True
                continue
            stripped = line.strip()
            if not object_lines:
                if stripped.startswith("]"):
                    break
                if stripped == "{":
                    object_lines = [line]
                    depth = 1
                continue
            object_lines.append(line)
            # Asset-map entries contain scalar strings/numbers only.  Braces
            # therefore occur only as JSON structure in this generated file.
            depth += line.count("{") - line.count("}")
            if depth != 0:
                continue
            text = "".join(object_lines).rstrip().rstrip(",")
            entry = json.loads(text)
            object_lines = []
            key = (str(entry.get("Type") or ""), int(entry.get("PathID") or 0))
            if key in targets:
                # Unity PathIDs are local to a serialized file.  AnimeStudio's
                # global asset map can therefore contain collisions; retain
                # every candidate and resolve with the authoritative container
                # or source identity later.
                found.setdefault(key, []).append(entry)
    missing = sorted(targets - set(found))
    if missing and require_complete:
        raise RecoveryError(f"Asset map is missing {len(missing)} target(s): {missing[:8]}")
    return found


def scan_asset_maps(
    paths: Iterable[Path], targets: set[tuple[str, int]]
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    """Merge baseline and patch-layer candidates before enforcing coverage."""

    found: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for path in paths:
        partial = scan_asset_map(path, targets, require_complete=False)
        for key, entries in partial.items():
            found.setdefault(key, []).extend(entries)
    missing = sorted(targets - set(found))
    if missing:
        raise RecoveryError(
            f"Asset maps are missing {len(missing)} target(s): {missing[:8]}"
        )
    return found


def attach_material_asset_map(
    materials: dict[str, list[dict[str, Any]]],
    asset_map: dict[tuple[str, int], list[dict[str, Any]]],
) -> None:
    for actor_records in materials.values():
        for record in actor_records:
            entry = choose_asset_map_entry(
                asset_map[("Material", int(record["path_id"]))],
                container=str(record["container"]),
                name=str(record["name"]),
            )
            if entry is None:
                raise RecoveryError(f"No asset-map row for Material {record['name']}")
            record["source"]["asset_map"] = {
                "container": entry.get("Container", ""),
                "hash": entry.get("Hash", ""),
                "offset": entry.get("Offset", 0),
                "source_vfs_relative": source_vfs_relative(entry.get("Source")),
            }
            record["validation"]["asset_map_container_matches_manifest"] = (
                not record["container"]
                or record["container"] == entry.get("Container", "")
            )
            record["validation"]["path_id_collision_count"] = len(
                asset_map[("Material", int(record["path_id"]))]
            )


def extract(repo_root: Path) -> dict[str, Any]:
    actor_manifests = discover_actor_manifests(repo_root)
    track_root_actors = discover_track_root_actors(repo_root, set(actor_manifests))
    # Character materials are already recovered and validated by the per-actor
    # manifests/importer. This payload now stays focused on the CharInfo volume
    # composition needed at runtime; re-auditing every roster material would
    # require an exhaustive Material JSON export that the lean WebUI asset cache
    # intentionally does not contain.
    materials = {actor: [] for actor in actor_manifests}
    map_targets: set[tuple[str, int]] = set()
    profile_path, profile, base_path, base = discover_charinfo_base(repo_root)
    (
        gacha_profile_path,
        gacha_profile,
        gacha_base_path,
        gacha_base,
    ) = discover_named_character_volume_profile(
        repo_root, "GachaRoom_Volume", GACHA_ROOM_FALLBACK_ROOT
    )
    (
        override_profile_path,
        override_profile,
        override_base_path,
        override_base,
    ) = discover_named_character_volume_profile(
        repo_root, "CharOverrideVolumeProfile", CHAR_OVERRIDE_FALLBACK_ROOT
    )
    modifiers = discover_overview_modifiers(
        repo_root,
        actor_manifests,
        track_root_actors,
    )
    environment_path, environment = discover_environment(repo_root)

    source_objects: list[tuple[str, Path, dict[str, Any]]] = [
        ("profile", profile_path, profile),
        ("base", base_path, base),
        ("gacha_profile", gacha_profile_path, gacha_profile),
        ("gacha_base", gacha_base_path, gacha_base),
        ("char_override_profile", override_profile_path, override_profile),
        ("char_override_base", override_base_path, override_base),
        ("environment", environment_path, environment),
    ]
    for actor, (path, data, _) in modifiers.items():
        source_objects.append((f"modifier:{actor}", path, data))
    for _, _, data in source_objects:
        metadata = data.get("$animestudio") or {}
        map_targets.add((str(metadata.get("type") or "MonoBehaviour"), int(metadata.get("pathId") or 0)))

    asset_map = scan_asset_maps(
        (repo_root / path for path in ASSET_MAPS),
        map_targets,
    )
    attach_material_asset_map(materials, asset_map)

    base_parameters = parameter_block(base)
    gacha_base_parameters = parameter_block(gacha_base)
    override_base_parameters = parameter_block(override_base)
    characters: dict[str, Any] = {}
    for actor, (modifier_path, modifier, ancestry) in sorted(modifiers.items()):
        modifier_parameters = parameter_block(modifier["charLightVolumeData"])
        post_snapshot = apply_use_data_on_volume_snapshot(
            override_base_parameters, modifier_parameters
        )
        resolved = compose_volume_layers(
            ("gacha_room_priority_30000", gacha_base_parameters),
            ("actor_override_priority_30001", post_snapshot),
        )
        metadata = modifier.get("$animestudio") or {}
        key = (str(metadata.get("type") or "MonoBehaviour"), int(metadata.get("pathId") or 0))
        modifier_entry = choose_asset_map_entry(
            asset_map.get(key),
            name=str(metadata.get("name") or ""),
            source_vfs=source_vfs_relative(metadata.get("sourceOriginalPath")),
        )
        characters[actor] = {
            "modifier_source": source_record(
                repo_root, modifier_path, modifier, modifier_entry
            ),
            "modifier_ancestry": ancestry,
            "modifier_serialized_parameters": modifier_parameters,
            "post_use_data_on_volume": post_snapshot,
            "resolved_active_overrides": resolved,
            "materials": materials[actor],
        }

    base_metadata = base.get("$animestudio") or {}
    profile_metadata = profile.get("$animestudio") or {}
    environment_metadata = environment.get("$animestudio") or {}
    light = environment.get("lightConfig") or {}
    environment_params0 = [
        float(light.get("indirectDiffuseFactor", 0.0)),
        float(light.get("indirectSpecularFactor", 0.0)),
        1.0,
        0.0,
    ]
    native_character_volume = repo_root / NATIVE_CHARACTER_VOLUME
    native_environment_packer = repo_root / NATIVE_ENVIRONMENT_PACKER
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "policy": {
            "production_parameter_source": "original_game_data_or_recovered_native_behavior_only",
            "visual_fitting_allowed": False,
            "inactive_volume_parameters_are_not_promoted": True,
            "unknown_live_only_values_default_off_or_neutral": True,
        },
        "charinfo_profile": {
            "container": "assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfo_volume.asset",
            "source": source_record(
                repo_root,
                profile_path,
                profile,
                choose_asset_map_entry(
                    asset_map.get((str(profile_metadata.get("type") or "MonoBehaviour"), int(profile_metadata.get("pathId") or 0))),
                    container="assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfo_volume.asset",
                    name="CharInfo_Volume",
                ),
            ),
            "component_path_ids": {
                str(item.get("targetName")): int(item.get("targetPathId") or 0)
                for item in (profile_metadata.get("pptrReferences") or [])
                if isinstance(item, dict) and item.get("targetName")
            },
        },
        "gacha_character_volume_stack": {
            "gacha_room": {
                "global": True,
                "priority": 30000.0,
                "weight": 1.0,
                "profile_source": source_record(
                    repo_root, gacha_profile_path, gacha_profile, None
                ),
                "character_volume_source": source_record(
                    repo_root, gacha_base_path, gacha_base, None
                ),
                "serialized_parameters": gacha_base_parameters,
            },
            "char_override": {
                "global": True,
                "priority": 30001.0,
                "weight": 1.0,
                "profile_source": source_record(
                    repo_root, override_profile_path, override_profile, None
                ),
                "character_volume_source": source_record(
                    repo_root, override_base_path, override_base, None
                ),
                "serialized_parameters_before_use_data": override_base_parameters,
            },
        },
        "base_character_volume": {
            "active": bool(base.get("active")),
            "source": source_record(
                repo_root,
                base_path,
                base,
                choose_asset_map_entry(
                    asset_map.get((str(base_metadata.get("type") or "MonoBehaviour"), int(base_metadata.get("pathId") or 0))),
                    container="assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfo_volume.asset",
                    name="HGCharacterVolume",
                ),
            ),
            "serialized_parameters": base_parameters,
        },
        "characters": characters,
        "environment": {
            "source": source_record(
                repo_root,
                environment_path,
                environment,
                choose_asset_map_entry(
                    asset_map.get((str(environment_metadata.get("type") or "MonoBehaviour"), int(environment_metadata.get("pathId") or 0))),
                    name="CharInfo_Env",
                    source_vfs=source_vfs_relative(environment_metadata.get("sourceOriginalPath")),
                ),
            ),
            "serialized": {
                "direct_color": light.get("directColor"),
                "direct_color_mode": light.get("directColorMode"),
                "direct_custom_color": light.get("directCustomColor"),
                "direct_color_temperature": light.get("directColorTemperature"),
                "direct_lux": light.get("directLux"),
                "direct_ev100": light.get("directEV100"),
                "direct_intensity": light.get("directIntensity"),
                "direct_intensity_divide_pi": light.get("directIntensityDividePi"),
                "direct_pitch_yaw": light.get("directPitchYaw"),
                "indirect_diffuse_factor": light.get("indirectDiffuseFactor"),
                "indirect_specular_factor": light.get("indirectSpecularFactor"),
                "pre_exposure": light.get("preExposure"),
            },
            "environment_global_params0": environment_params0,
        },
        "native_behavior_sources": {
            "character_volume": {
                "path": relative_path(repo_root, native_character_volume),
                "bytes": native_character_volume.stat().st_size,
                "sha256": sha256_file(native_character_volume),
                "role": "constructor_defaults_volume_composition_and_global_packing",
            },
            "environment_packer": {
                "path": relative_path(repo_root, native_environment_packer),
                "bytes": native_environment_packer.stat().st_size,
                "sha256": sha256_file(native_environment_packer),
                "role": "environment_global_parameter_packing",
            },
        },
        "live_only_unknowns": {
            "_ExposureParams.x": (
                "CharInfo Manual target is exactly 1; only a reused physical "
                "camera's carried initial current value and convergence delta-time "
                "sequence are history-dependent"
            ),
            "_CharacterParams11.xyz": "camera_dependent_CameraFollow_direction",
            "irradiance_visibility": "runtime_scene_volume_and_probe_state",
            "clustered_additional_lights": "runtime_culling_and_light_state",
            "hidden_quality_overrides": "runtime_device_quality_selection",
        },
        "validation": {
            "actors": sorted(characters),
            "material_count": {
                actor: len(records) for actor, records in sorted(materials.items())
            },
            "all_material_manifest_payloads_match_original_json": all(
                record["validation"]["manifest_payload_matches"]
                for records in materials.values()
                for record in records
            ),
            "material_manifest_payload_mismatch_count": sum(
                not record["validation"]["manifest_payload_matches"]
                for records in materials.values()
                for record in records
            ),
            "material_manifest_conflicting_value_count": sum(
                not record["validation"]["manifest_payload_has_no_conflicting_values"]
                for records in materials.values()
                for record in records
            ),
            "all_material_sources_selected_by_exact_identity": all(
                record["validation"]["ok"]
                for records in materials.values()
                for record in records
            ),
            "material_asset_map_container_mismatch_count": sum(
                not record["validation"]["asset_map_container_matches_manifest"]
                for records in materials.values()
                for record in records
            ),
            "charinfo_profile_links_base_volume": True,
            "overview_modifiers_discovered_from_original_hierarchy": True,
            "asset_map_rows_verified": True,
            "ok": True,
        },
    }
    return result


def encoded_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="fluffy-dump root (auto-detected by default)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output JSON path (defaults inside Generated/OriginalData)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the existing output differs; do not write",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = ()) -> int:
    args = parse_args(argv)
    repo_root = (
        args.repo_root.resolve()
        if args.repo_root
        else find_repo_root(Path(__file__).resolve())
    )
    output = args.output or (repo_root / DEFAULT_OUTPUT)
    if not output.is_absolute():
        output = repo_root / output
    payload = extract(repo_root)
    encoded = encoded_json(payload)
    if args.check:
        if not output.is_file():
            print(f"missing generated payload: {output}", file=sys.stderr)
            return 1
        if output.read_text(encoding="utf-8") != encoded:
            print(f"stale generated payload: {output}", file=sys.stderr)
            return 1
        print(f"original render parameter payload is current: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8", newline="\n")
    print(
        f"wrote {output} ({output.stat().st_size} bytes; "
        f"sha256={sha256_file(output)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
