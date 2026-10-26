"""Resolve authored map ids to their transform-bearing streaming art scenes.

Some gameplay maps are variants of one shared scene.  In particular, the
blackbox tutorials publish distinct map ids while their own map config points
at either ``blackbox01_dg001`` or ``blackbox02_dg001``.  Keeping this join in
one place prevents the preview builder and the WebUI data builder from guessing
relationships from similarly named levels.
"""

from __future__ import annotations
from scripts.common import EXPORT_LAYOUT, WEBUI_BUILD_DIR

import re
from functools import lru_cache
from pathlib import Path

from scripts.game_data.levelconfig_binary import decode_level_config
from scripts.game_data.string_pool import export_string_pool
from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT
LEVEL_CONFIG_ROOT = EXPORT_LAYOUT.json_dir / "LevelConfig"
STREAMING_INSTANCE_ROOT = WEBUI_BUILD_DIR / "map" / "world_placements"

_SCENE_PATH_RE = re.compile(r"([A-Za-z0-9_]+)/([A-Za-z0-9_]+?)(?:_art)?_streaming[.]asset")
_ART_LEVEL_RE = re.compile(r"([A-Za-z0-9_]+_lv[0-9]+)_art")


class LevelConfigSourceError(ValueError):
    """A present LevelConfig could not be read or decoded for the selected export."""


def _source_label(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)


@lru_cache(maxsize=1024)
def level_config(level_id: str, *, level_config_root: Path = LEVEL_CONFIG_ROOT) -> dict | None:
    """Decode one level's LevelConfig, or ``None`` when the export has none.

    Strings are inline or StringPool indices depending on whether the export
    ships ``Json/StringPool``. A present file that fails to decode raises
    ``LevelConfigSourceError`` instead of resolving to no scene, so a format
    change cannot silently empty every map.
    """
    if not re.fullmatch(r"[A-Za-z0-9_]+", str(level_id or "")):
        return None
    path = level_config_root / f"{level_id}.json"
    if not path.is_file():
        return None
    try:
        decoded = decode_level_config(
            path.read_bytes(), strings=export_string_pool(level_config_root.parent)
        )
    except (OSError, ValueError) as exc:
        raise LevelConfigSourceError(f"{_source_label(path)}: {exc}") from exc
    return {**decoded, "source": _source_label(path)}


def _string_members(config: dict) -> list[str]:
    state = config["defaultState"]
    values = (
        state["exportedSceneConfigPath"], state["name"], state["sourceSceneName"],
        config["dimensionSourceLevelId"], config["id"], config["mapIdStr"],
        config["waterStartAudio"], config["waterStopAudio"],
    )
    return [value for value in values if value]


@lru_cache(maxsize=1024)
def authored_streaming_scene(
    level_id: str,
    *,
    level_config_root: Path = LEVEL_CONFIG_ROOT,
) -> dict | None:
    """Return the exact shared art-scene id declared by a level's config.

    The current contract reads ``defaultState.exportedSceneConfigPath`` from
    the directly addressed decoded LevelConfig and accepts only a bounded path
    whose folder and asset names agree. No name prefix, TextAsset fallback, or
    tutorial sequence is used as evidence.
    """
    config = level_config(level_id, level_config_root=level_config_root)
    if not config:
        return None
    matched = _SCENE_PATH_RE.search(config["defaultState"]["exportedSceneConfigPath"] or "")
    if matched and matched.group(1).lower() == matched.group(2).lower():
        return {
            "sceneId": matched.group(1),
            "method": "level_config_embedded_streaming_path",
            "source": config["source"],
        }
    return None


def projection_streaming_scene(
    level_id: str,
    *,
    instance_root: Path = STREAMING_INSTANCE_ROOT,
    level_config_root: Path = LEVEL_CONFIG_ROOT,
) -> dict | None:
    """Resolve a published level to an available exact-transform sidecar."""
    authored = authored_streaming_scene(
        level_id,
        level_config_root=level_config_root,
    )
    # Regional sidecars are deliberately partitioned to member level ids by
    # the exact HLOD key/member-suffix join. Standalone aliases instead follow
    # LevelConfig, even when another art scene produced a same-name sidecar.
    regional_member = bool(
        authored and authored["sceneId"] in {"map01", "map02"}
        and re.fullmatch(r"map0[12]_lv\d+", level_id, re.IGNORECASE)
    )
    direct = instance_root / f"{level_id}.json"
    if direct.is_file() and (not authored or authored["sceneId"] == level_id or regional_member):
        return {
            "sceneId": level_id,
            "method": "level_init_chunk_data",
            "source": str(direct.relative_to(ROOT)).replace("\\", "/") if direct.is_relative_to(ROOT) else str(direct),
            "instanceSource": direct,
        }
    if authored:
        sidecar = instance_root / f"{authored['sceneId']}.json"
        if sidecar.is_file():
            return {
                **authored,
                "instanceSource": sidecar,
            }
    # Large-region danger/challenge levels declare both the common streaming
    # root (for example map01) and the exact art-level member they instantiate.
    # The exporter publishes per-member InitChunkData sidecars, not a synthetic
    # common-root sidecar, so use that authored member instead of falling back
    # to an inferred HLOD grid crop.
    art = isolated_art_source(level_id, level_config_root=level_config_root)
    if not art:
        return None
    sidecar = instance_root / f"{art['levelId']}.json"
    if not sidecar.is_file():
        return None
    return {
        "sceneId": art["levelId"],
        "method": "level_config_embedded_art_level_init_chunk_data",
        "source": art["source"],
        "instanceSource": sidecar,
    }


@lru_cache(maxsize=1024)
def authored_art_level(
    level_id: str,
    *,
    level_config_root: Path = LEVEL_CONFIG_ROOT,
) -> dict | None:
    """Return one exact source art level embedded in a compact LevelConfig.

    Non-seamless boss/danger maps can reuse a large-region streaming root while
    selecting one authored ``mapNN_lvNNN_art`` scene. That art-level identity
    is a source relation, not permission to merge the gameplay map into the
    source level's WebUI region.
    """
    config = level_config(level_id, level_config_root=level_config_root)
    if not config:
        return None
    matches = {
        value for member in _string_members(config) for value in _ART_LEVEL_RE.findall(member)
    }
    if len(matches) != 1:
        return None
    return {
        "levelId": next(iter(matches)),
        "method": "level_config_embedded_art_level",
        "source": config["source"],
    }


def isolated_art_source(level_id: str, *, level_config_root: Path = LEVEL_CONFIG_ROOT) -> dict | None:
    """Resolve dungeon source art without merging its independent gameplay map."""
    if not re.fullmatch(r"dung[0-9]+_[A-Za-z0-9_]+", str(level_id or ""), re.IGNORECASE):
        return None
    return authored_art_level(level_id, level_config_root=level_config_root)
