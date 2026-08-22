"""Resolve authored map ids to their transform-bearing streaming art scenes.

Some gameplay maps are variants of one shared scene.  In particular, the
blackbox tutorials publish distinct map ids while their own map config points
at either ``blackbox01_dg001`` or ``blackbox02_dg001``.  Keeping this join in
one place prevents the preview builder and the WebUI data builder from guessing
relationships from similarly named levels.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEVEL_CONFIG_ROOT = ROOT / "export_full/structured/StreamingAssets/Data/Json/LevelConfig"
STREAMING_INSTANCE_ROOT = ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/map_streaming_instances"

_BINARY_SCENE_PATH_RE = re.compile(
    rb"([A-Za-z0-9_]+)/([A-Za-z0-9_]+?)(?:_art)?_streaming[.]asset"
)
_BINARY_ART_LEVEL_RE = re.compile(rb"([A-Za-z0-9_]+_lv[0-9]+)_art")


@lru_cache(maxsize=1024)
def authored_streaming_scene(
    level_id: str,
    *,
    level_config_root: Path = LEVEL_CONFIG_ROOT,
) -> dict | None:
    """Return the exact shared art-scene id declared by a level's config.

    The current contract reads the directly addressed compact LevelConfig and
    accepts only a bounded path whose folder and asset names agree. No name
    prefix, TextAsset fallback, or tutorial sequence is used as evidence.
    """
    if not re.fullmatch(r"[A-Za-z0-9_]+", str(level_id or "")):
        return None
    binary = level_config_root / f"{level_id}.json"
    if binary.is_file():
        try:
            matched = _BINARY_SCENE_PATH_RE.search(binary.read_bytes())
        except OSError:
            matched = None
        if matched and matched.group(1).lower() == matched.group(2).lower():
            return {
                "sceneId": matched.group(1).decode("ascii"),
                "method": "level_config_embedded_streaming_path",
                "source": str(binary.relative_to(ROOT)).replace("\\", "/") if binary.is_relative_to(ROOT) else str(binary),
            }

    return None


def projection_streaming_scene(
    level_id: str,
    *,
    instance_root: Path = STREAMING_INSTANCE_ROOT,
    level_config_root: Path = LEVEL_CONFIG_ROOT,
) -> dict | None:
    """Resolve a published level to an available exact-transform sidecar."""
    direct = instance_root / f"{level_id}.json"
    if direct.is_file():
        return {
            "sceneId": level_id,
            "method": "level_init_chunk_data",
            "source": str(direct.relative_to(ROOT)).replace("\\", "/") if direct.is_relative_to(ROOT) else str(direct),
            "instanceSource": direct,
        }
    authored = authored_streaming_scene(
        level_id,
        level_config_root=level_config_root,
    )
    if not authored:
        return None
    sidecar = instance_root / f"{authored['sceneId']}.json"
    if not sidecar.is_file():
        return None
    return {
        **authored,
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
    if not re.fullmatch(r"[A-Za-z0-9_]+", str(level_id or "")):
        return None
    path = level_config_root / f"{level_id}.json"
    try:
        matches = {
            value.decode("ascii")
            for value in _BINARY_ART_LEVEL_RE.findall(path.read_bytes())
        }
    except (OSError, UnicodeError):
        return None
    if len(matches) != 1:
        return None
    return {
        "levelId": next(iter(matches)),
        "method": "level_config_embedded_art_level",
        "source": str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path),
    }


def isolated_art_source(level_id: str, *, level_config_root: Path = LEVEL_CONFIG_ROOT) -> dict | None:
    """Resolve dungeon source art without merging its independent gameplay map."""
    if not re.fullmatch(r"dung[0-9]+_[A-Za-z0-9_]+", str(level_id or ""), re.IGNORECASE):
        return None
    return authored_art_level(level_id, level_config_root=level_config_root)
