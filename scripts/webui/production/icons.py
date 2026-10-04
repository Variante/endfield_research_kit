"""Small exact-name icon lookup over existing converted images and Sprite crops."""
from __future__ import annotations

from typing import Any

from scripts.game_data.media_resolver import icon_shape_rank, media_lookup_stem
from scripts.game_data.sprite_crops import SpriteCropError, image_name, png_size, read_sprite_crop
from scripts.game_data.unity_store import open_store_if_present
from scripts.source_paths import ExportLayout


def load_icons(layout: ExportLayout, icon_ids: set[str], *, square_icon_ids: set[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Choose full-size item icons using the shared shape preference.

    Match exact authored tokens first. Shape and resolution only choose the
    displayed variant; they do not establish which asset the runtime loads.
    """
    requested = {value.lower() for value in icon_ids}
    square_only = {value.lower() for value in square_icon_ids or ()}
    entries: list[dict[str, Any]] = []
    rejected = []
    textures = layout.unity_type_dir("Texture2D")
    store = open_store_if_present(layout.root)
    if store is not None:
        try:
            for row in store.iter_rows("Sprite"):
                if not row.name.endswith(".json"):
                    continue
                name = image_name(row.name)
                ref = f"Unity/Sprite/{name}"
                stem = media_lookup_stem(ref)
                if stem is None or stem[0] not in requested:
                    continue
                try:
                    crop = read_sprite_crop(store, name)
                except SpriteCropError as error:
                    rejected.append(str(error))
                    continue
                if crop is not None and (textures / crop.texture_file).is_file():
                    entries.append({"k": "image", "r": ref, "width": crop.width, "height": crop.height})
        finally:
            store.close()
    if textures.is_dir():
        for path in textures.glob("*.png"):
            ref = f"Unity/Texture2D/{path.name}"
            stem = media_lookup_stem(ref)
            if stem is None or stem[0] not in requested:
                continue
            size = png_size(path)
            if size:
                entries.append({"k": "image", "r": ref, "width": size[0], "height": size[1]})
    def rank(entry):
        width, height = entry["width"], entry["height"]
        return (*icon_shape_rank(width, height), -width * height, -width, -height,
                0 if "/Sprite/" in entry["r"] else 1, entry["r"])

    icons = {}
    for entry in sorted(entries, key=rank):
        stem = media_lookup_stem(entry["r"])[0]
        if stem in square_only and entry["width"] != entry["height"]:
            continue
        icons.setdefault(stem, {field: entry[field] for field in ("r", "width", "height")})
    return icons, {"requested": len(requested), "resolved": len(icons),
                   "missing": sorted(requested - icons.keys()), "rejected": rejected,
                   "evidence": "Exact authored iconId to exported image stem; shared item-icon shape preference, then highest resolution. Display selection, not runtime asset ownership."}
