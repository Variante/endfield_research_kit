"""What one installed-game extraction run exports.

Two independent vocabularies decide an export:

* **Structured blocks** are final VFS files the AnimeStudio ``dump`` command
  writes under ``game/`` (``table`` -> ``game/Table``, ``json-data`` ->
  ``game/Json``, ...). ``terrain-height`` is the ``terrain`` block limited to
  the ``_H`` height grids map recovery reads; ``terrain`` takes the block whole.
* **Unity classes** are objects AnimeStudio exports from asset bundles: JSON
  documents (``json_by_type``, published into ``game/Unity.sqlite``) and
  converted media (``convert_by_type``, ``game/Unity/<Type>/`` plus ``.anim``
  documents and Sprite crop documents in the store). A Sprite is exported as a
  crop of its exported Texture2D, so selecting Sprite selects Texture2D whole.

An :class:`ExtractionScope` is one selection from each vocabulary. Scopes
combine with ``|``, so a run that serves several consumers exports exactly what
any of them reads. The WebUI declares what each build task reads
(``scripts/webui/pages.py``); the named levels below are presets for direct
exporter use, and :data:`EVERYTHING` is the debug export.

Decoded blocks publish into ``game/``. The blocks no reader decodes into the
export (``RAW_BLOCKS``: Streaming, DynamicStreaming, IV, ExtendData, IFixPatch
and the bundle manifest) publish byte-for-byte into ``raw/``. The Data page
shows their bytes and may publish native/source-authenticated component views
through maintained readers. Bundles and audio packages are never dumped:
AnimeStudio decodes their contents into Unity objects and decoded audio.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

#: Every structured block the exporter can dump, in dump order.
STRUCTURED_BLOCKS: tuple[str, ...] = (
    "table",
    "json-data",
    "video",
    "audit-video",
    # Lua is about 16 MB decoded; the exporter already removes its
    # base64+XXTEA wrapper and writes `Lua/<name>.lua`.
    "lua",
    "terrain-height",
    "terrain",
    "streaming",
    "audit-streaming",
    "dynamic-streaming",
    "audit-dynamic-streaming",
    "iv",
    "audit-iv",
    "extend-data",
    "initial-extend-data",
    "i-fix-patch",
    "bundle-manifest",
)
#: Final VFS files no reader decodes into the export; they publish under raw/.
RAW_BLOCKS: tuple[str, ...] = (
    "streaming",
    "audit-streaming",
    "dynamic-streaming",
    "audit-dynamic-streaming",
    "iv",
    "audit-iv",
    "extend-data",
    "initial-extend-data",
    "i-fix-patch",
    "bundle-manifest",
)
#: Blocks that publish into one folder. Publishing replaces a whole folder, so
#: selecting one member selects them all.
SHARED_FOLDER_BLOCKS: tuple[frozenset[str], ...] = (
    frozenset({"video", "audit-video"}),
    frozenset({"streaming", "audit-streaming"}),
    frozenset({"dynamic-streaming", "audit-dynamic-streaming"}),
    frozenset({"iv", "audit-iv"}),
    frozenset({"extend-data", "initial-extend-data"}),
)
#: The pseudo-block that dumps only the Terrain `_H` height grids (about
#: 64 MiB of Terrain's 1.19 GB).
TERRAIN_HEIGHT_BLOCK = "terrain-height"
TERRAIN_HEIGHT_FILE_REGEX = r"^Data/Terrain/PC/[^/]+/Terrain_[0-9]+_[0-9]+_[0-9]+_H\.bytes$"

#: Tables, JsonData, video and Lua: the Story export.
FOCUSED_STRUCTURED_BLOCKS: tuple[str, ...] = ("table", "json-data", "video", "audit-video", "lua")
#: Named structured levels. Each contains the one below it: `default` adds the
#: Terrain height grids, `full` all of Terrain (about 1.19 GB) and the
#: undecoded blocks (about 4.9 GB).
STRUCTURED_LEVELS: dict[str, tuple[str, ...]] = {
    "focused": FOCUSED_STRUCTURED_BLOCKS,
    "default": FOCUSED_STRUCTURED_BLOCKS + (TERRAIN_HEIGHT_BLOCK,),
    "full": FOCUSED_STRUCTURED_BLOCKS + ("terrain",) + RAW_BLOCKS,
}

#: Every Unity class exported as JSON, in export order.
UNITY_JSON_TYPES: tuple[str, ...] = (
    "TextAsset",
    "MonoBehaviour",
    "PlayableDirector",
    "Material",
    "AnimatorController",
    "AnimatorOverrideController",
    "AssetBundle",
    "IndexObject",
    "MonoScript",
    "PlayerSettings",
    "ResourceManager",
    "SpriteAtlas",
    "NapAssetBundleIndexAsset",
    # PreloadData (ClassID 150) carries per-bundle asset cohorts; AvatarMask
    # (319) the body-part transform masks. Both use the generic TypeTree path.
    "PreloadData",
    "AvatarMask",
)
#: Every Unity class exported through Convert, in export order. Endfield's
#: asset maps hold no GameObject, AudioClip, VideoClip, MovieTexture or
#: MiHoYoBinData entries, so those are not offered.
UNITY_CONVERT_TYPES: tuple[str, ...] = (
    "Texture2D",
    "Shader",
    "TextAsset",
    "Font",
    "Mesh",
    "Sprite",
    "Animator",
    "AnimationClip",
)
#: JSON classes that carry Story: TextAsset DialogTree sources, MonoBehaviour
#: Timeline/dialog carriers and PlayableDirector bindings. Any of them keeps the
#: JSON stage on the broad load, because a map-filtered MonoBehaviour load
#: loses script names and cross-bundle PPtr targets.
STORY_JSON_TYPES: tuple[str, ...] = ("TextAsset", "MonoBehaviour", "PlayableDirector")
#: JSON classes the original-data object index covers. The index is merged from
#: one run's JSON jobs, so a consumer selects both or the index loses the other.
OBJECT_INDEX_JSON_TYPES: frozenset[str] = frozenset({"MonoBehaviour", "PlayableDirector"})


@dataclass(frozen=True)
class ExtractionScope:
    """One structured-block selection plus one Unity-class selection."""

    structured: frozenset[str] = field(default_factory=frozenset)
    json_types: frozenset[str] = field(default_factory=frozenset)
    convert_types: frozenset[str] = field(default_factory=frozenset)
    #: Limit Texture2D to the names the generated WebUI references. Valid only
    #: while Texture2D is the sole Convert class, because AnimeStudio applies
    #: a name filter to the whole Convert stage.
    webui_textures_only: bool = False

    def __post_init__(self) -> None:
        for name, values, known in (
            ("structured block", self.structured, STRUCTURED_BLOCKS),
            ("Unity JSON class", self.json_types, UNITY_JSON_TYPES),
            ("Unity Convert class", self.convert_types, UNITY_CONVERT_TYPES),
        ):
            unknown = sorted(set(values) - set(known))
            if unknown:
                raise ValueError(f"unknown {name}(s): {', '.join(unknown)}; expected {', '.join(known)}")
        if self.webui_textures_only and self.convert_types != frozenset({"Texture2D"}):
            raise ValueError("the WebUI Texture2D name filter needs Texture2D as the only Convert class")
        if "Sprite" in self.convert_types and "Texture2D" not in self.convert_types:
            raise ValueError("Sprite exports as crops of the exported Texture2D, so it needs Texture2D whole")

    @classmethod
    def of(
        cls,
        structured: Iterable[str] = (),
        json_types: Iterable[str] = (),
        convert_types: Iterable[str] = (),
        *,
        webui_textures_only: bool = False,
    ) -> "ExtractionScope":
        convert = frozenset(convert_types)
        if "Sprite" in convert:
            # A Sprite is a crop document over an exported texture.
            convert |= {"Texture2D"}
        return cls(
            frozenset(structured),
            frozenset(json_types),
            convert,
            webui_textures_only,
        )

    def __or__(self, other: "ExtractionScope") -> "ExtractionScope":
        convert = self.convert_types | other.convert_types
        # A filtered Texture2D survives only while nothing else needs Texture2D
        # whole and no other Convert class shares the stage.
        filtered = (
            convert == frozenset({"Texture2D"})
            and all(
                scope.webui_textures_only or "Texture2D" not in scope.convert_types
                for scope in (self, other)
            )
        )
        return ExtractionScope(
            self.structured | other.structured,
            self.json_types | other.json_types,
            convert,
            filtered,
        )

    @property
    def structured_blocks(self) -> tuple[str, ...]:
        """The selected blocks in dump order; whole Terrain absorbs the height grids."""
        selected = set(self.structured)
        for group in SHARED_FOLDER_BLOCKS:
            if selected & group:
                selected |= group
        if "terrain" in selected:
            selected.discard(TERRAIN_HEIGHT_BLOCK)
        return tuple(block for block in STRUCTURED_BLOCKS if block in selected)

    @property
    def json_classes(self) -> tuple[str, ...]:
        return tuple(name for name in UNITY_JSON_TYPES if name in self.json_types)

    @property
    def convert_classes(self) -> tuple[str, ...]:
        return tuple(name for name in UNITY_CONVERT_TYPES if name in self.convert_types)

    @property
    def exports_unity(self) -> bool:
        return bool(self.json_types or self.convert_types)

    @property
    def exports_story_carriers(self) -> bool:
        """Whether the JSON stage must keep the broad, dependency-loading path."""
        return any(name in self.json_types for name in STORY_JSON_TYPES)

    @property
    def exports_object_index_types(self) -> bool:
        return bool(self.json_types & OBJECT_INDEX_JSON_TYPES)

    def exporter_args(self) -> list[str]:
        """The ``export_full_from_game`` arguments that select exactly this scope."""
        args: list[str] = []
        blocks = self.structured_blocks
        args += ["--structured", *blocks] if blocks else ["--skip-structured"]
        if self.exports_unity:
            if self.json_types:
                args += ["--unity-json", *self.json_classes]
            if self.convert_types:
                args += ["--unity-convert", *self.convert_classes]
            if self.webui_textures_only:
                args.append("--webui-textures-only")
        else:
            args.append("--skip-animestudio")
        return args

    def describe(self) -> str:
        parts = [f"structured: {', '.join(self.structured_blocks) or 'none'}"]
        parts.append(f"Unity JSON: {', '.join(self.json_classes) or 'none'}")
        convert = ", ".join(self.convert_classes) or "none"
        if self.webui_textures_only:
            convert += " (WebUI-referenced names only)"
        parts.append(f"Unity Convert: {convert}")
        return "; ".join(parts)


#: Named Unity selections: the Story carriers, and the three asset levels
#: (`focused` WebUI-referenced Texture2D, `default` WebUI-facing media plus the
#: audio callback-ownership inputs, `debug` every class).
UNITY_LEVELS: dict[str, ExtractionScope] = {
    "story": ExtractionScope.of(json_types=STORY_JSON_TYPES),
    "focused": ExtractionScope.of(convert_types=("Texture2D",), webui_textures_only=True),
    "default": ExtractionScope.of(
        json_types=("Material", "AnimatorController", "AnimatorOverrideController"),
        convert_types=("Texture2D", "Mesh", "Sprite", "Animator", "AnimationClip"),
    ),
    "debug": ExtractionScope.of(json_types=UNITY_JSON_TYPES, convert_types=UNITY_CONVERT_TYPES),
}

#: Everything the exporter can reach: the debug export.
EVERYTHING = ExtractionScope.of(
    structured=STRUCTURED_LEVELS["full"],
    json_types=UNITY_JSON_TYPES,
    convert_types=UNITY_CONVERT_TYPES,
)


def structured_dump_steps(blocks: Iterable[str]) -> list[dict[str, object]]:
    """The AnimeStudio ``dump`` calls for a block selection.

    Unfiltered blocks share one call. The Terrain height grids need their own
    call because its file regex would otherwise filter every block in it, and a
    selection with whole Terrain drops the height step so no grid is dumped twice.
    """
    selected = ExtractionScope.of(structured=blocks).structured_blocks
    unfiltered = tuple(block for block in selected if block != TERRAIN_HEIGHT_BLOCK)
    steps: list[dict[str, object]] = []
    if unfiltered:
        steps.append({"name": "blocks", "block_types": unfiltered, "file_regexes": ()})
    if TERRAIN_HEIGHT_BLOCK in selected:
        steps.append({
            "name": "terrain_height",
            "block_types": ("terrain",),
            "file_regexes": (TERRAIN_HEIGHT_FILE_REGEX,),
        })
    return steps
