from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.repo_paths import REPO_ROOT

# ---------------------------------------------------------------------------
# Export root layout v2
#
# An export root holds exactly two roles:
#
#   game/   final, exactly decoded game data, one tree = what the client loads
#           (Persistent overlaid on StreamingAssets). Flat: native VFS names
#           with the leading ``Data/`` dropped, plus one folder per decoded
#           family (Audio, Unity).
#   meta/   indexes and provenance that describe game/. Never game data.
#           Per installed layer (meta/<Layer>/...), because each index,
#           asset map and fingerprint describes one physical root, and the
#           base catalogue is what proves which bundles a hot update replaced.
#
# Builder output never lives here (it goes to webui/data), and run
# intermediates never live here (they go to tmp/). Every path into an export
# root is built by ExportLayout; do not join export-root segments by hand.
# ---------------------------------------------------------------------------

EXPORT_LAYOUT_SCHEMA = "endfield.export-layout.v2"
EXPORT_LAYOUT_FILE = "layout.json"
EXPORT_LAYOUT_MIGRATE_COMMAND = "python -m scripts.game_data.extraction.migrate_export_layout"

# The installed roots, in overlay order: a later layer overrides an earlier one.
INSTALLED_LAYERS: tuple[str, ...] = ("StreamingAssets", "Persistent")

EXPORT_LAYOUT_STATE_WRITING = "writing"
EXPORT_LAYOUT_STATE_COMPLETE = "complete"

# Native VFS logical prefix -> folder under game/. A logical path that matches
# none of these is not a final file and has no place in game/. Only native VFS
# files are mapped here; decoded families (Audio, Unity) have their own paths.
# Add a prefix only after confirming the VFS logical name it carries.
_GAME_NATIVE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("Table/", "Table"),
    # The Lua block has no Data/ prefix: the dumper and the changed-only
    # exporter both write it as Lua/<name>.lua (export_changed_game_data).
    ("Lua/", "Lua"),
    ("Data/Json/", "Json"),
    ("Data/Video/", "Video"),
    ("Data/Terrain/", "Terrain"),
)


class ExportLayoutError(RuntimeError):
    """An export root is missing, unversioned, or uses another layout."""


def _repo_relative(path: Path) -> Path:
    # Relative export roots are repo-relative, as in endfield_paths.bat, not
    # relative to whatever directory a script happens to run from.
    return path if path.is_absolute() else REPO_ROOT / path


def configured_export_root() -> Path:
    """The export root selected by ENDFIELD_EXPORT_ROOT, else ``export_full``."""
    value = os.environ.get("ENDFIELD_EXPORT_ROOT", "").strip().strip('"')
    return _repo_relative(Path(value or "export_full"))


def game_relative_path(logical_path: str) -> PurePosixPath:
    """Map a native VFS logical path (``Data/Json/x.json``) to its path under game/."""
    normalized = str(logical_path).replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or normalized.startswith("/") or ":" in parts[0] or ".." in parts or "." in parts:
        raise ExportLayoutError(f"VFS path is not a relative logical path: {logical_path}")
    normalized = "/".join(parts)
    for prefix, folder in _GAME_NATIVE_PREFIXES:
        if normalized.lower().startswith(prefix.lower()) and len(normalized) > len(prefix):
            return PurePosixPath(folder, normalized[len(prefix):])
    raise ExportLayoutError(f"VFS path is not a final game file: {logical_path}")


@dataclass(frozen=True)
class ExportLayout:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", _repo_relative(Path(self.root)))

    @classmethod
    def configured(cls) -> "ExportLayout":
        return cls(configured_export_root())

    # -- roles ---------------------------------------------------------------
    @property
    def game(self) -> Path:
        return self.root / "game"

    @property
    def meta(self) -> Path:
        return self.root / "meta"

    @property
    def layout_file(self) -> Path:
        return self.root / EXPORT_LAYOUT_FILE

    # -- game/ ---------------------------------------------------------------
    @property
    def table_dir(self) -> Path:
        return self.game / "Table"

    @property
    def json_dir(self) -> Path:
        return self.game / "Json"

    @property
    def video_dir(self) -> Path:
        return self.game / "Video"

    @property
    def terrain_dir(self) -> Path:
        return self.game / "Terrain"

    @property
    def lua_dir(self) -> Path:
        return self.game / "Lua"

    @property
    def audio_dir(self) -> Path:
        return self.game / "Audio"

    @property
    def unity_dir(self) -> Path:
        return self.game / "Unity"

    def unity_type_dir(self, type_name: str) -> Path:
        return self.unity_dir / type_name

    def game_file(self, logical_path: str) -> Path:
        return self.game.joinpath(*game_relative_path(logical_path).parts)

    # -- meta/ ---------------------------------------------------------------
    def layer_meta(self, layer: str) -> Path:
        if layer not in INSTALLED_LAYERS:
            raise ExportLayoutError(f"unknown installed layer: {layer!r}")
        return self.meta / layer

    def vfs_index_dir(self, layer: str) -> Path:
        return self.layer_meta(layer) / "vfs_index"

    def asset_map_dir(self, layer: str) -> Path:
        return self.layer_meta(layer) / "asset_map"

    def object_index_dir(self, layer: str) -> Path:
        return self.layer_meta(layer) / "object_index"

    def asset_status_dir(self, layer: str) -> Path:
        return self.layer_meta(layer) / "asset_status"

    def renderer_index_dir(self, layer: str) -> Path:
        """AnimeStudio ``--renderer_index_jsonl`` output for one layer."""
        return self.layer_meta(layer) / "renderer_index"

    @property
    def cab_map_dir(self) -> Path:
        return self.meta / "cab_map"

    @property
    def extraction_failures_dir(self) -> Path:
        return self.meta / "extraction" / "failures"

    @property
    def extraction_incremental_dir(self) -> Path:
        return self.meta / "extraction" / "incremental"

    # -- run intermediates (never inside the export root) --------------------
    @property
    def work_dir(self) -> Path:
        # Keyed by name plus a digest of the full path, so two roots that share
        # a folder name (or a root that has no name) never share a work dir.
        identity = os.path.normcase(os.path.abspath(self.root))
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        return REPO_ROOT / "tmp" / "game_data" / "export" / f"{self.root.name or 'root'}-{digest}"

    # -- version marker ------------------------------------------------------
    def read_marker(self) -> dict[str, Any] | None:
        """The parsed marker, or None when the root has none (a v1 root)."""
        try:
            text = self.layout_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ExportLayoutError(f"cannot read {self.layout_file}: {exc}") from exc
        try:
            payload = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExportLayoutError(f"{self.layout_file} is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ExportLayoutError(f"{self.layout_file} is not a JSON object")
        return payload

    def require(self) -> "ExportLayout":
        """Fail closed unless this root is a v2 root whose last write completed."""
        if not self.root.is_dir():
            raise ExportLayoutError(f"export root does not exist: {self.root}")
        marker = self.read_marker()
        if marker is None:
            raise ExportLayoutError(
                f"{self.root} has no {EXPORT_LAYOUT_FILE}; it predates layout v2. "
                f"Run: {EXPORT_LAYOUT_MIGRATE_COMMAND} --export-root \"{self.root}\""
            )
        if marker.get("schema") != EXPORT_LAYOUT_SCHEMA:
            raise ExportLayoutError(
                f"{self.layout_file} declares schema {marker.get('schema')!r}; "
                f"expected {EXPORT_LAYOUT_SCHEMA!r}"
            )
        if marker.get("state") != EXPORT_LAYOUT_STATE_COMPLETE:
            raise ExportLayoutError(
                f"{self.root} is mid-write (state {marker.get('state')!r}); "
                "the last export or migration did not finish"
            )
        return self

    def begin_write(self, **fields: Any) -> None:
        """Mark the root as being rewritten. Writers call this first."""
        self._publish_marker(EXPORT_LAYOUT_STATE_WRITING, fields)

    def finish_write(self, **fields: Any) -> None:
        """Mark the root complete. Writers call this last, after game/ and meta/."""
        self._publish_marker(EXPORT_LAYOUT_STATE_COMPLETE, fields)

    def _publish_marker(self, state: str, fields: dict[str, Any]) -> None:
        payload = {"schema": EXPORT_LAYOUT_SCHEMA, "state": state, **fields}
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.layout_file.with_name(self.layout_file.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.layout_file)


# ---------------------------------------------------------------------------
# Browsable asset sources. Published asset references are "<label>/<path>";
# the WebUI resolves each label through the sourceRoots map built from these.
# ---------------------------------------------------------------------------

ASSET_SOURCE_UNITY = "Unity"  # game/Unity: decoded Unity objects and conversions
ASSET_SOURCE_GAME = "Game"  # game/: final VFS files (Table, Json, Video, ...)
# Folders directly under game/ that other asset sources own. A walker of the
# Game source must prune them, or every Unity object and decoded audio file is
# indexed twice.
GAME_SOURCE_PRUNED_DIRS = frozenset({"Unity", "Audio"})


def prune_nested_source_dirs(source: str, source_root: Path, dirpath: str | Path, dirnames: list[str]) -> None:
    """For os.walk: drop game/ folders owned by another asset source, in place."""
    if source == ASSET_SOURCE_GAME and Path(dirpath) == source_root:
        dirnames[:] = [name for name in dirnames if name not in GAME_SOURCE_PRUNED_DIRS]


def _asset_source_family(label: str) -> str:
    return str(label or "").split("-", 1)[0]


def resolve_asset_source_roots(export_root: Path) -> list[tuple[str, Path]]:
    layout = ExportLayout(export_root)
    candidates = ((ASSET_SOURCE_UNITY, layout.unity_dir), (ASSET_SOURCE_GAME, layout.game))
    return [(label, path) for label, path in candidates if path.exists()]


def resolve_material_source_roots(export_root: Path) -> list[tuple[str, Path]]:
    unity_dir = ExportLayout(export_root).unity_dir
    return [(ASSET_SOURCE_UNITY, unity_dir)] if unity_dir.exists() else []
