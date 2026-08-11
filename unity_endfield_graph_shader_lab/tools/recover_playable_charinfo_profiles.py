#!/usr/bin/env python3
"""Recover playable-character CharInfo presentation profiles from game data.

This helper deliberately separates two stages:

``prepare``
    Join the playable catalog and CharacterDisplayConfig to AnimeStudio's
    installed-game asset map, then emit bounded ``filter_data`` files for each
    catalog-enabled camera/light prefab and background-portrait Sprite.

``extract``
    Read the targeted AnimeStudio JSON outputs and emit one compact,
    machine-readable profile payload for Unity.  Every camera, look-at,
    overview-image, and Sprite-geometry value comes from serialized game data;
    no reference-image fitting is performed.

The accompanying ``recover_playable_charinfo_profiles.bat`` runs both stages
and the two bounded AnimeStudio exports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "endfield.playable-charinfo-presentation-profiles.v1"
CATALOG = Path(
    "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
    "Characters/Catalog/playable_character_ui_catalog.json"
)
CHARACTER_DISPLAY_CONFIG = Path(
    "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/"
    "MonoBehaviour/CharacterDisplayConfig_p0EEC0AFE8247A15F.json"
)
ASSET_MAPS = {
    "StreamingAssets": Path(
        "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/"
        "endfield_streamingassets_assets.json"
    ),
    "Persistent": Path(
        "export_full/recovered/AnimeStudio-cli/Persistent/maps/"
        "endfield_persistent_assets.json"
    ),
}
TEXTURE_ROOTS = {
    "StreamingAssets": Path(
        "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/"
        "Texture2D"
    ),
    "Persistent": Path(
        "export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/"
        "Texture2D"
    ),
}
DEFAULT_WORK_ROOT = Path("scratch/charinfo_playable_profiles")
DEFAULT_OUTPUT = Path(
    "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/"
    "OriginalData/CharInfoPlayableProfiles/source_profiles.json"
)
DISPLAY_CONFIG_EXPORT_FOLDER = "display_config_json"

CAMERA_SUFFIX = "/dollycart/vcam_overview"
LOOK_AT_SUFFIX = "/lookatgroup/lookat_overview/lookat_overview_ani"


class RecoveryError(RuntimeError):
    pass


def find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "unity_endfield_graph_shader_lab").is_dir() and (
            candidate / "export_full"
        ).is_dir():
            return candidate
    raise RecoveryError("could not find the fluffy-dump repository root")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RecoveryError(f"expected a JSON object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def pptr_id(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return int(value.get("m_PathID", value.get("PathID", 0)) or 0)


def signed_path_id_from_filename(path: Path) -> int:
    match = re.search(r"_p([0-9a-fA-F]{16})\.json$", path.name)
    if not match:
        raise RecoveryError(f"could not recover PathID from {path}")
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def path_id(path: Path, data: dict[str, Any]) -> int:
    metadata = data.get("$animestudio") or {}
    if "pathId" in metadata:
        return int(metadata["pathId"])
    return signed_path_id_from_filename(path)


def aligned_serialized_strings(data: bytes) -> list[tuple[int, str]]:
    """Return offset/value pairs for plausible aligned Unity strings."""
    result: list[tuple[int, str]] = []
    for offset in range(0, max(0, len(data) - 4), 4):
        length = struct.unpack_from("<I", data, offset)[0]
        if length < 1 or length > 512 or offset + 4 + length > len(data):
            continue
        raw = data[offset + 4 : offset + 4 + length]
        if any(value < 0x20 or value > 0x7E for value in raw):
            continue
        try:
            value = raw.decode("ascii")
        except UnicodeDecodeError:
            continue
        result.append((offset, value))
    return result


def recover_display_record(
    character_id: str,
    raw_data: bytes,
    offset: int,
    length: int,
) -> dict[str, Any]:
    record = raw_data[offset : offset + length]
    if len(record) != length:
        raise RecoveryError(f"raw CharacterDisplayData is truncated for {character_id}")
    strings = aligned_serialized_strings(record)
    cameras = [(position, value) for position, value in strings if value.startswith("CameraTracks/")]
    lights = [(position, value) for position, value in strings if value.startswith("AdditionalLights/")]
    ids = [value for _, value in strings if value == character_id]
    if len(cameras) != 1 or len(lights) != 1 or len(ids) != 1:
        raise RecoveryError(
            f"raw CharacterDisplayData string contract failed for {character_id}: "
            f"camera={len(cameras)} light={len(lights)} charId={len(ids)}"
        )

    camera_offset, camera_group = cameras[0]
    light_offset, light_group = lights[0]
    height_offset = camera_offset - 8
    if height_offset < 0:
        raise RecoveryError(f"raw CharacterDisplayData height is missing for {character_id}")
    height_value = struct.unpack_from("<I", record, height_offset)[0]
    height_names = {0: "GirlFlattie", 1: "GirlHighHeel", 2: "Female", 3: "Male"}
    if height_value not in height_names:
        raise RecoveryError(
            f"raw CharacterDisplayData height enum is invalid for {character_id}: {height_value}"
        )

    light_length = struct.unpack_from("<I", record, light_offset)[0]
    tail_offset = (light_offset + 4 + light_length + 3) & ~3
    overview_offset = tail_offset + 7 * 4
    if overview_offset + 12 > len(record):
        raise RecoveryError(
            f"raw CharacterDisplayData overview offset is missing for {character_id}"
        )
    overview = struct.unpack_from("<3f", record, overview_offset)
    return {
        "charId": character_id,
        "charInfoCameraGroup": camera_group,
        "charInfoLightGroup": light_group,
        "height": {"name": height_names[height_value], "value": height_value},
        "overviewImgOffset": {"x": overview[0], "y": overview[1], "z": overview[2]},
        "$rawRecovery": {
            "recordOffset": offset,
            "recordLength": length,
            "cameraStringOffset": offset + camera_offset + 4,
            "lightStringOffset": offset + light_offset + 4,
        },
    }


def display_records(
    config: dict[str, Any], raw_data: bytes | None = None
) -> dict[str, dict[str, Any]]:
    references = (config.get("references") or {}).get("RefIds") or []
    by_rid: dict[int, dict[str, Any]] = {}
    for item in references:
        if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
            continue
        by_rid[int(item.get("rid") or 0)] = item

    data = config.get("data") or {}
    keys = data.get("_keys") or []
    values = data.get("_values") or []
    if len(keys) != len(values):
        raise RecoveryError("CharacterDisplayConfig key/value counts differ")

    result: dict[str, dict[str, Any]] = {}
    for character_id, rid_record in zip(keys, values):
        rid = int((rid_record or {}).get("rid") or 0)
        reference = by_rid.get(rid)
        if reference is None:
            raise RecoveryError(
                f"CharacterDisplayConfig has no managed-reference record for {character_id}"
            )
        record = reference["data"]
        if record.get("$unparsed"):
            if raw_data is None:
                raise RecoveryError(
                    "CharacterDisplayConfig contains unresolved managed references; "
                    "run the bounded raw display-config export first"
                )
            record = recover_display_record(
                str(character_id),
                raw_data,
                int(reference.get("dataOffset", record.get("offset", 0)) or 0),
                int(reference.get("dataLength", record.get("length", 0)) or 0),
            )
        if str(record.get("charId") or character_id) != character_id:
            raise RecoveryError(f"CharacterDisplayConfig RID mismatch for {character_id}")
        result[str(character_id)] = record
    return result


def prepare_display_config_filter(repo: Path, work_root: Path) -> None:
    source_config = load_json(repo / CHARACTER_DISPLAY_CONFIG)
    metadata = source_config.get("$animestudio") or {}
    expected_path_id = int(metadata.get("pathId") or 0)
    candidates = [
        entry
        for entry in iter_asset_map_entries(repo / ASSET_MAPS["StreamingAssets"])
        if entry.get("Type") == "MonoBehaviour"
        and int(entry.get("PathID") or 0) == expected_path_id
    ]
    if len(candidates) != 1:
        raise RecoveryError(
            "expected one CharacterDisplayConfig asset-map row; "
            f"found {len(candidates)}"
        )
    write_json(work_root / "display_config_filter.json", [filter_row(candidates[0])])
    print("prepared bounded raw CharacterDisplayConfig filter")


def exported_display_config(work_root: Path) -> tuple[Path, dict[str, Any], bytes]:
    folder = work_root / DISPLAY_CONFIG_EXPORT_FOLDER / "MonoBehaviour"
    paths = sorted(folder.glob("CharacterDisplayConfig_*.json"))
    if len(paths) != 1:
        raise RecoveryError(
            f"expected one raw CharacterDisplayConfig JSON under {folder}; found {len(paths)}"
        )
    path = paths[0]
    raw_path = path.with_suffix(".raw.bin")
    if not raw_path.is_file():
        raise RecoveryError(f"raw CharacterDisplayConfig sidecar is missing: {raw_path}")
    return path, load_json(path), raw_path.read_bytes()


def enabled_catalog_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    rows = catalog.get("characters") or []
    result = [row for row in rows if isinstance(row, dict) and row.get("import_enabled")]
    declared_count = int(catalog.get("import_character_count") or 0)
    if len(result) != declared_count:
        raise RecoveryError("playable catalog enabled-count contract failed")
    if not result:
        raise RecoveryError("playable catalog has no import-enabled characters")
    return result


def prefab_container(group: str) -> str:
    normalized = str(group or "").strip().replace("\\", "/").lower()
    if not normalized:
        return ""
    return (
        "assets/beyond/dynamicassets/gameplay/prefabs/charinfo/"
        + normalized
        + ".prefab"
    )


def portrait_container(character_id: str) -> str:
    return (
        "assets/beyond/dynamicassets/gameplay/ui/sprites/charinfo/"
        f"bg_charinfo_{character_id}.png"
    )


def iter_asset_map_entries(path: Path) -> Iterable[dict[str, Any]]:
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
            depth += line.count("{") - line.count("}")
            if depth:
                continue
            yield json.loads("".join(object_lines).rstrip().rstrip(","))
            object_lines = []


def filter_row(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "Source": entry.get("Source", ""),
        "Offset": int(entry.get("Offset") or 0),
        "Name": entry.get("Name", ""),
        "PathID": int(entry.get("PathID") or 0),
        "Type": entry.get("Type", ""),
    }


def source_layer(entry: dict[str, Any]) -> str:
    source = str(entry.get("Source") or "").replace("\\", "/").casefold()
    if "/persistent/" in source:
        return "Persistent"
    if "/streamingassets/" in source:
        return "StreamingAssets"
    raise RecoveryError(f"asset row has no recognized installed source layer: {source}")


def choose_prefab_entry(entries: list[dict[str, Any]], container: str) -> dict[str, Any]:
    candidates = [entry for entry in entries if entry.get("Container") == container]
    if not candidates:
        raise RecoveryError(f"asset map has no rows for {container}")
    mono = [entry for entry in candidates if entry.get("Type") == "MonoBehaviour"]
    candidates = mono or candidates
    return sorted(
        candidates,
        key=lambda item: (
            0 if source_layer(item) == "Persistent" else 1,
            str(item.get("Source") or ""),
            int(item.get("Offset") or 0),
            int(item.get("PathID") or 0),
        ),
    )[0]


def choose_sprite_entry(entries: list[dict[str, Any]], container: str) -> dict[str, Any]:
    candidates = [
        entry
        for entry in entries
        if entry.get("Container") == container and entry.get("Type") == "Sprite"
    ]
    if not candidates:
        raise RecoveryError(
            f"expected a Sprite asset-map row for {container}; found 0"
        )
    preferred_layer = "Persistent" if any(
        source_layer(entry) == "Persistent" for entry in candidates
    ) else "StreamingAssets"
    preferred = [
        entry for entry in candidates if source_layer(entry) == preferred_layer
    ]
    if len(preferred) != 1:
        raise RecoveryError(
            f"expected one {preferred_layer} Sprite asset-map row for {container}; "
            f"found {len(preferred)}"
        )
    return preferred[0]


def build_plan(repo: Path, work_root: Path) -> dict[str, Any]:
    catalog = load_json(repo / CATALOG)
    display_path, display_config, display_raw = exported_display_config(work_root)
    display = display_records(display_config, display_raw)
    rows = enabled_catalog_rows(catalog)

    planned: list[dict[str, Any]] = []
    requested_containers: set[str] = set()
    for row in rows:
        character_id = str(row.get("character_id") or "")
        record = display.get(character_id)
        if record is None:
            raise RecoveryError(f"CharacterDisplayConfig has no row for {character_id}")
        camera_container = prefab_container(record.get("charInfoCameraGroup", ""))
        light_container = prefab_container(record.get("charInfoLightGroup", ""))
        sprite_container = portrait_container(character_id)
        if not camera_container or not light_container:
            raise RecoveryError(f"missing CharInfo camera/light group for {character_id}")
        requested_containers.update((camera_container, light_container, sprite_container))
        planned.append(
            {
                "character_id": character_id,
                "actor_token": str(row.get("actor_token") or ""),
                "root_name": str(row.get("root_name") or ""),
                "display_name": str(row.get("display_name") or ""),
                "prefab_asset_path": str(row.get("prefab_asset_path") or ""),
                "camera_group": str(record.get("charInfoCameraGroup") or ""),
                "camera_container": camera_container,
                "light_group": str(record.get("charInfoLightGroup") or ""),
                "light_container": light_container,
                "portrait_container": sprite_container,
                "overview_image_offset": record.get("overviewImgOffset") or {},
                "height": record.get("height") or {},
            }
        )

    found: dict[str, list[dict[str, Any]]] = {
        container: [] for container in requested_containers
    }
    for map_path in ASSET_MAPS.values():
        for entry in iter_asset_map_entries(repo / map_path):
            container = str(entry.get("Container") or "")
            if container in found:
                found[container].append(entry)

    for item in planned:
        camera_entry = choose_prefab_entry(found[item["camera_container"]], item["camera_container"])
        light_entry = choose_prefab_entry(found[item["light_container"]], item["light_container"])
        sprite_entry = choose_sprite_entry(found[item["portrait_container"]], item["portrait_container"])
        item["camera_filter"] = filter_row(camera_entry)
        item["light_filter"] = filter_row(light_entry)
        item["sprite_filter"] = filter_row(sprite_entry)

    dependency_filters: dict[tuple[str, int], dict[str, Any]] = {}
    sprite_filters: dict[tuple[str, int, int], dict[str, Any]] = {}
    for item in planned:
        for name in ("camera_filter", "light_filter"):
            row = item[name]
            dependency_filters[(str(row["Source"]), int(row["Offset"]))] = row
        row = item["sprite_filter"]
        sprite_filters[
            (str(row["Source"]), int(row["Offset"]), int(row["PathID"]))
        ] = row

    dependency_rows = sorted(
        dependency_filters.values(),
        key=lambda row: (str(row["Source"]), int(row["Offset"])),
    )
    sprite_rows = sorted(
        sprite_filters.values(),
        key=lambda row: (str(row["Source"]), int(row["Offset"]), int(row["PathID"])),
    )
    return {
        "schema": SCHEMA + ".plan",
        "policy": {
            "source": "installed-game asset map and raw CharacterDisplayConfig",
            "display_config_json": relative(repo, display_path),
            "managed_reference_recovery": "bounded raw serialized records",
            "image_fitting": False,
        },
        "characters": planned,
        "dependency_filters": dependency_rows,
        "sprite_filters": sprite_rows,
        "dependency_filters_by_layer": {
            layer: [row for row in dependency_rows if source_layer(row) == layer]
            for layer in ASSET_MAPS
        },
        "sprite_filters_by_layer": {
            layer: [row for row in sprite_rows if source_layer(row) == layer]
            for layer in ASSET_MAPS
        },
    }


def prepare(repo: Path, work_root: Path) -> None:
    plan = build_plan(repo, work_root)
    write_json(work_root / "source_plan.json", plan)
    write_json(work_root / "camera_light_filter.json", plan["dependency_filters"])
    write_json(work_root / "portrait_sprite_filter.json", plan["sprite_filters"])
    for layer in ASSET_MAPS:
        suffix = layer.casefold()
        write_json(
            work_root / f"camera_light_filter_{suffix}.json",
            plan["dependency_filters_by_layer"][layer],
        )
        write_json(
            work_root / f"portrait_sprite_filter_{suffix}.json",
            plan["sprite_filters_by_layer"][layer],
        )
    print(
        f"prepared {len(plan['characters'])} profiles: "
        f"prefab offsets={len(plan['dependency_filters'])}, "
        f"sprites={len(plan['sprite_filters'])}"
    )


def index_json_folder(folder: Path) -> dict[int, tuple[Path, dict[str, Any]]]:
    result: dict[int, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(folder.glob("*.json")):
        data = load_json(path)
        identifier = path_id(path, data)
        if identifier in result:
            raise RecoveryError(f"duplicate PathID {identifier} under {folder}")
        result[identifier] = (path, data)
    return result


def component_owner_index(
    game_objects: dict[int, tuple[Path, dict[str, Any]]]
) -> dict[int, int]:
    result: dict[int, int] = {}
    for game_object_id, (_, game_object) in game_objects.items():
        for component in game_object.get("m_Components") or []:
            component_id = pptr_id(component)
            if component_id:
                result[component_id] = game_object_id
    return result


def hierarchy_path(
    game_object_id: int,
    game_objects: dict[int, tuple[Path, dict[str, Any]]],
    component_owner: dict[int, int],
) -> str:
    names: list[str] = []
    visited: set[int] = set()
    while game_object_id and game_object_id not in visited:
        visited.add(game_object_id)
        item = game_objects.get(game_object_id)
        if item is None:
            break
        game_object = item[1]
        names.append(str(game_object.get("m_Name") or game_object.get("Name") or ""))
        parent_transform = pptr_id((game_object.get("m_Transform") or {}).get("m_Father"))
        game_object_id = component_owner.get(parent_transform, 0)
    return "/".join(reversed(names))


def vector(value: Any, keys: tuple[str, ...]) -> list[float]:
    value = value if isinstance(value, dict) else {}
    result: list[float] = []
    for key in keys:
        candidates = (key, key.lower(), key.upper())
        selected = next((value[name] for name in candidates if name in value), 0.0)
        result.append(float(selected or 0.0))
    return result


def quaternion_multiply(left: list[float], right: list[float]) -> list[float]:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return [
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    ]


def quaternion_normalize(value: list[float]) -> list[float]:
    length = math.sqrt(sum(component * component for component in value))
    if length <= 1e-12:
        return [0.0, 0.0, 0.0, 1.0]
    return [component / length for component in value]


def quaternion_rotate(rotation: list[float], point: list[float]) -> list[float]:
    x, y, z, w = quaternion_normalize(rotation)
    px, py, pz = point
    # q * p * conjugate(q), expanded.
    tx = 2.0 * (y * pz - z * py)
    ty = 2.0 * (z * px - x * pz)
    tz = 2.0 * (x * py - y * px)
    return [
        px + w * tx + (y * tz - z * ty),
        py + w * ty + (z * tx - x * tz),
        pz + w * tz + (x * ty - y * tx),
    ]


def multiply_components(left: list[float], right: list[float]) -> list[float]:
    return [a * b for a, b in zip(left, right)]


def add_components(left: list[float], right: list[float]) -> list[float]:
    return [a + b for a, b in zip(left, right)]


def root_relative_transform(
    game_object_id: int,
    root_id: int,
    game_objects: dict[int, tuple[Path, dict[str, Any]]],
    component_owner: dict[int, int],
) -> tuple[list[float], list[float], list[float]]:
    chain: list[dict[str, Any]] = []
    current = game_object_id
    visited: set[int] = set()
    while current and current not in visited:
        visited.add(current)
        item = game_objects.get(current)
        if item is None:
            break
        chain.append(item[1].get("m_Transform") or {})
        if current == root_id:
            break
        current = component_owner.get(pptr_id(chain[-1].get("m_Father")), 0)
    if current != root_id:
        raise RecoveryError(
            f"GameObject {game_object_id} is not below expected root {root_id}"
        )

    position = [0.0, 0.0, 0.0]
    rotation = [0.0, 0.0, 0.0, 1.0]
    scale = [1.0, 1.0, 1.0]
    # Exclude the track root's own transform; CharInfo attaches it at identity.
    for transform in reversed(chain[:-1]):
        local_position = vector(transform.get("m_LocalPosition"), ("x", "y", "z"))
        local_rotation = vector(transform.get("m_LocalRotation"), ("x", "y", "z", "w"))
        local_scale = vector(transform.get("m_LocalScale"), ("x", "y", "z"))
        position = add_components(
            position,
            quaternion_rotate(rotation, multiply_components(scale, local_position)),
        )
        rotation = quaternion_normalize(quaternion_multiply(rotation, local_rotation))
        scale = multiply_components(scale, local_scale)
    return position, rotation, scale


def source_record(repo: Path, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("$animestudio") or {}
    return {
        "path": relative(repo, path),
        "path_id": path_id(path, data),
        "sha256": sha256_file(path),
        "raw_data_sha256": str(metadata.get("rawDataSha256") or ""),
        "raw_data_length": int(metadata.get("rawDataLength") or 0),
        "source_file": str(metadata.get("sourceFile") or ""),
        "source_original_path": str(metadata.get("sourceOriginalPath") or ""),
    }


def camera_profile(
    repo: Path,
    item: dict[str, Any],
    game_objects: dict[int, tuple[Path, dict[str, Any]]],
    behaviours: dict[int, tuple[Path, dict[str, Any]]],
    component_owner: dict[int, int],
) -> dict[str, Any]:
    # The female Endministrator row is the one shipped alias where the
    # CharacterDisplayData group key (track_chr_0003_endmin) intentionally
    # differs from the playable table id (chr_0003_endminf).  The serialized
    # group binding is authoritative for hierarchy lookup.
    expected_root = str(item["camera_group"]).replace("\\", "/").rsplit("/", 1)[-1]
    roots = [
        game_object_id
        for game_object_id, (_, game_object) in game_objects.items()
        if str(game_object.get("m_Name") or game_object.get("Name") or "").lower()
        == expected_root.lower()
    ]
    if len(roots) != 1:
        raise RecoveryError(f"expected one {expected_root} root; found {len(roots)}")
    root_id = roots[0]

    paths = {
        game_object_id: hierarchy_path(game_object_id, game_objects, component_owner)
        for game_object_id in game_objects
    }
    prefix = expected_root.lower() + "/"
    vcam = [
        game_object_id
        for game_object_id, path in paths.items()
        if path.lower().startswith(prefix) and path.lower().endswith(CAMERA_SUFFIX)
    ]
    look_at = [
        game_object_id
        for game_object_id, path in paths.items()
        if path.lower().startswith(prefix) and path.lower().endswith(LOOK_AT_SUFFIX)
    ]
    if len(vcam) != 1 or len(look_at) != 1:
        raise RecoveryError(
            f"overview camera hierarchy mismatch for {expected_root}: "
            f"vcam={len(vcam)} lookAt={len(look_at)}"
        )
    vcam_id = vcam[0]
    look_at_id = look_at[0]
    camera_position, camera_rotation, _ = root_relative_transform(
        vcam_id, root_id, game_objects, component_owner
    )
    look_at_position, _, _ = root_relative_transform(
        look_at_id, root_id, game_objects, component_owner
    )

    lens_matches: list[tuple[Path, dict[str, Any]]] = []
    gyro_matches: list[tuple[Path, dict[str, Any]]] = []
    vcam_game_object = game_objects[vcam_id][1]
    for component in vcam_game_object.get("m_Components") or []:
        behaviour = behaviours.get(pptr_id(component))
        if behaviour is None:
            continue
        data = behaviour[1]
        if isinstance(data.get("m_Lens"), dict):
            lens_matches.append(behaviour)
        if "offsetX" in data and "offsetY" in data:
            gyro_matches.append(behaviour)
    if len(lens_matches) != 1:
        raise RecoveryError(f"expected one overview lens for {expected_root}")
    lens_path, lens_data = lens_matches[0]
    lens = lens_data["m_Lens"]
    gyro = gyro_matches[0] if len(gyro_matches) == 1 else None

    return {
        "track_root": expected_root,
        "vcam_path": paths[vcam_id],
        "look_at_path": paths[look_at_id],
        "position": camera_position,
        "authored_rotation_xyzw": camera_rotation,
        "look_at": look_at_position,
        "field_of_view": float(lens.get("FieldOfView") or 0.0),
        "near_clip": float(lens.get("NearClipPlane") or 0.0),
        "far_clip": float(lens.get("FarClipPlane") or 0.0),
        "dutch": float(lens.get("Dutch") or 0.0),
        "lens_shift": vector(lens.get("LensShift"), ("x", "y")),
        "sensor_size": vector(lens.get("m_SensorSize"), ("x", "y")),
        "gate_fit": int(lens.get("GateFit") or 0),
        "priority": int(lens_data.get("m_Priority") or 0),
        "standby_update": int(lens_data.get("m_StandbyUpdate") or 0),
        "gyroscope_entry_offsets": (
            [float(gyro[1].get("offsetX") or 0.0), float(gyro[1].get("offsetY") or 0.0)]
            if gyro is not None
            else [0.0, 0.0]
        ),
        "sources": {
            "vcam_game_object": source_record(
                repo, game_objects[vcam_id][0], game_objects[vcam_id][1]
            ),
            "look_at_game_object": source_record(
                repo, game_objects[look_at_id][0], game_objects[look_at_id][1]
            ),
            "lens": source_record(repo, lens_path, lens_data),
            "gyroscope": (
                source_record(repo, gyro[0], gyro[1]) if gyro is not None else None
            ),
        },
    }


def locate_texture(repo: Path, character_id: str) -> Path:
    matches_by_layer = {
        layer: sorted((repo / root).glob(f"bg_charinfo_{character_id}_p*.png"))
        for layer, root in TEXTURE_ROOTS.items()
    }
    preferred_layer = (
        "Persistent" if matches_by_layer["Persistent"] else "StreamingAssets"
    )
    matches = matches_by_layer[preferred_layer]
    if len(matches) != 1:
        raise RecoveryError(
            f"expected one decoded {preferred_layer} Texture2D for {character_id}; "
            f"found {len(matches)}"
        )
    return matches[0]


def sprite_profile(repo: Path, sprite_root: Path, character_id: str) -> dict[str, Any]:
    matches = sorted((sprite_root / "Sprite").glob(f"bg_charinfo_{character_id}_p*.json"))
    if len(matches) != 1:
        raise RecoveryError(
            f"expected one Sprite JSON for {character_id}; found {len(matches)}"
        )
    sprite_path = matches[0]
    sprite = load_json(sprite_path)
    render_data = sprite.get("m_RD") or {}
    texture_rect = render_data.get("textureRect") or {}
    logical_rect = sprite.get("m_Rect") or {}
    if not texture_rect or not logical_rect:
        raise RecoveryError(f"Sprite geometry is incomplete: {sprite_path}")
    texture_path = locate_texture(repo, character_id)
    return {
        "name": str(sprite.get("m_Name") or sprite.get("Name") or ""),
        "logical_rect": logical_rect,
        "texture_rect": texture_rect,
        "texture_rect_offset": render_data.get("textureRectOffset") or {},
        "pivot": sprite.get("m_Pivot") or {},
        "offset": sprite.get("m_Offset") or {},
        "pixels_to_units": float(sprite.get("m_PixelsToUnits") or 0.0),
        "packing": render_data.get("settingsRaw") or {},
        "texture_path_id": pptr_id(render_data.get("texture")),
        "sprite_json": {
            "path": relative(repo, sprite_path),
            "path_id": signed_path_id_from_filename(sprite_path),
            "sha256": sha256_file(sprite_path),
        },
        "texture_png": {
            "path": relative(repo, texture_path),
            "bytes": texture_path.stat().st_size,
            "sha256": sha256_file(texture_path),
        },
    }


def extract(repo: Path, work_root: Path, output: Path) -> None:
    plan = load_json(work_root / "source_plan.json")
    dependency_root = work_root / "dependencies_json"
    sprite_root = work_root / "sprites_json"
    game_objects = index_json_folder(dependency_root / "GameObject")
    behaviours = index_json_folder(dependency_root / "MonoBehaviour")
    component_owner = component_owner_index(game_objects)

    plan_characters = [item for item in plan.get("characters") or [] if isinstance(item, dict)]
    if not plan_characters:
        raise RecoveryError("source plan contains no playable characters")
    characters: list[dict[str, Any]] = []
    for item in plan_characters:
        characters.append(
            {
                "character_id": item["character_id"],
                "actor_token": item["actor_token"],
                "root_name": item["root_name"],
                "display_name": item["display_name"],
                "prefab_asset_path": item["prefab_asset_path"],
                "height": item.get("height") or {},
                "overview_image_offset": item.get("overview_image_offset") or {},
                "camera_group": item["camera_group"],
                "light_group": item["light_group"],
                "camera": camera_profile(
                    repo, item, game_objects, behaviours, component_owner
                ),
                "portrait": sprite_profile(repo, sprite_root, item["character_id"]),
                "operator_light_key": item["actor_token"],
            }
        )

    if len(characters) != len(plan_characters):
        raise RecoveryError(
            f"extracted profile count differs from source plan: "
            f"expected {len(plan_characters)}, found {len(characters)}"
        )
    payload = {
        "schema": SCHEMA,
        "policy": {
            "production_parameter_source": "serialized_original_game_data_only",
            "visual_fitting_allowed": False,
            "neutral_camera_composer": (
                "physical camera aims at serialized LookAt target; no screenshot "
                "projection translation is applied"
            ),
        },
        "character_count": len(characters),
        "characters": characters,
        "validation": {
            "ok": True,
            "all_camera_profiles_recovered": True,
            "all_portrait_sprite_geometries_recovered": True,
            "all_texture_pngs_hash_pinned": True,
        },
    }
    write_json(output, payload)
    print(
        f"wrote {output} ({output.stat().st_size} bytes; "
        f"sha256={sha256_file(output)})"
    )


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("prepare-display-config", "prepare", "extract")
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = ()) -> int:
    args = parse_args(argv)
    repo = (
        args.repo_root.resolve()
        if args.repo_root
        else find_repo_root(Path(__file__).resolve())
    )
    work_root = args.work_root or (repo / DEFAULT_WORK_ROOT)
    if not work_root.is_absolute():
        work_root = repo / work_root
    output = args.output or (repo / DEFAULT_OUTPUT)
    if not output.is_absolute():
        output = repo / output
    if args.command == "prepare-display-config":
        prepare_display_config_filter(repo, work_root)
    elif args.command == "prepare":
        prepare(repo, work_root)
    else:
        extract(repo, work_root, output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except RecoveryError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
