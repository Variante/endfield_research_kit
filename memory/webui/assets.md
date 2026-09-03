# Assets page recovery

## Purpose

Assets inventories browser-visible exported images, video, JSON, OBJ, FBX, and
related resource metadata. It is a resource browser and evidence source for
other pages, not proof that an asset was used at runtime.

## Inputs and recovery flow

1. AnimeStudio builds source-scoped AssetMaps and exports the selected asset
   scope. Focused mode targets referenced textures; default adds WebUI-facing
   model/material/animation needs; debug is exhaustive diagnostics.
2. `scripts.build_assets` indexes available outputs and publishes media lookup,
   Story media, and video catalogs.
3. Gameplay's `asset-refs` stage consumes the Assets index and owns its
   consumer-specific join; the Assets builder does not write that sidecar.
4. Packaging may publish a compact normal-page media index and a complete
   resource index. Extract the resources archive last so the complete index wins.

Primary outputs: `webui/data/assets/{index,story_media,videos}.json`; Gameplay
separately owns `gameplay_refs.json`.

## Evidence boundary

- Source/CAB plus PathID is the stable Unity identity. Normalized names are
  discovery aids only.
- Indexed, loaded, exported, partial, and certified-clean are distinct states.
- Material/shader/texture presence does not establish runtime variant,
  renderer ownership, or final appearance.
- Missing optional previews remain visible and do not erase the indexed asset.

## Focused refresh

```bat
python scripts\build_assets.py
.\export_assets.bat --from-game --focused-assets
.\export_assets.bat --from-game --default-assets
```

Use `--debug-assets` only for broad investigation. Prefer
`.\export.bat --from-game --with-assets` when Story also needs refresh.

## Remaining gaps

- Improve object-level dependency and conversion diagnostics.
- Recover exact renderer/material/texture and animation ownership.
- Keep broad resource browsing packageable without inflating normal-page loads.

See [`../asset_recovery.md`](../asset_recovery.md) for durable asset semantics.
