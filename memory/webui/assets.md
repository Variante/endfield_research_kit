# Assets page recovery

## Purpose

Assets inventories browser-visible exported images, video, JSON, OBJ, FBX, and
related resource metadata. It is a resource browser and evidence source for
other pages, not proof that an asset was used at runtime.

## Inputs and recovery flow

1. AnimeStudio builds source-scoped AssetMaps and exports the selected asset
   scope. Focused mode targets referenced textures; default adds WebUI-facing
   model/material/animation needs; debug is exhaustive diagnostics.
2. `scripts.webui.assets.build_assets` indexes available outputs and publishes media lookup,
   Story media, and video catalogs.
3. Gameplay's `asset-refs` stage consumes the Assets index and owns its
   consumer-specific join; the Assets builder does not write that sidecar.
4. `scripts.webui.assets.table_asset_owners` recovers exact table-row
   ownership: an exported Table row owns an asset when an asset-bearing field
   (`icon`, `img`, `image`, `path`, `sprite`, `bg`, `avatar`, `bust`, `logo`,
   `portrait`, `texture`, `model`, `prefab`, `pic`, `art`) holds a value equal
   to the whole normalized asset stem. It always reads the complete scan, not
   the focused projection.
5. Packaging may publish a compact normal-page media index and a complete
   resource index. Extract the resources archive last so the complete index wins.

Primary outputs: `webui/data/assets/{index,story_media,table_owners,videos}.json`;
Gameplay separately owns `gameplay_refs.json`.

## Evidence boundary

- Source/CAB plus PathID is the stable Unity identity. Normalized names are
  discovery aids only.
- Indexed, loaded, exported, partial, and certified-clean are distinct states.
- Material/shader/texture presence does not establish runtime variant,
  renderer ownership, or final appearance.
- Missing optional previews remain visible and do not erase the indexed asset.
- Table ownership requires both gates: an asset-bearing field name and a
  whole-stem value match. A shared name prefix, a family stem, or an
  identifier field that coincides with an asset name is not ownership and is
  not published as a candidate. Most exported assets therefore stay unowned,
  because UI sprites are referenced from prefabs rather than from table rows.

## Focused refresh

```bat
python -m scripts.webui.assets.build_assets
.\export_assets.bat --from-game --focused-assets
.\export_assets.bat --from-game --default-assets
```

Use `--debug-assets` only for broad investigation. Prefer
`.\export.bat --from-game --with-assets` when Story also needs refresh.

## Remaining gaps

- Improve object-level dependency and conversion diagnostics.
- Recover exact renderer/material/texture and animation ownership.
- Table rows cover only the sprites a table names directly. Activity
  background sets, achievement icons, AI-bark portraits, attachment widget
  models, and ability-entity models are referenced from prefabs and UI
  layouts, so closing them needs a prefab/UI reference pass, not a wider name
  rule.
- Keep broad resource browsing packageable without inflating normal-page loads.

See [`../game_data/unity_assets.md`](../game_data/unity_assets.md) for durable
asset identity and binding semantics.
