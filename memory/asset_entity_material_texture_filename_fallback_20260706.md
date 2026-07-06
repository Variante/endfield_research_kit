# Asset Entity Material/Texture Filename Fallback - 2026-07-06

## Change

`tools/endfield_source_graph.py` now has a conservative asset-entity fallback
for material and material-like texture filenames. During WebUI asset ingest, if
a material or texture filename normalizes exactly to an existing exported model
entity base, it is attached to that entity group before `asset_entity` nodes are
emitted.

This is intended for cases where the flat asset index clearly contains matching
material/texture assets, but the relation table does not link them from the
model LOD assets.

## Normalization

The fallback:

- Removes exported PathID suffixes such as `_p8B217C88B3577E43`.
- Strips one-letter asset prefixes such as `M_` and `T_`.
- Converts Unity-style plus separators to underscores.
- Removes common texture channel suffixes such as `_D`, `_E`, `_MRO`, `_N`, and
  `_rgb_E`.
- Only attaches the material/texture when the normalized base exactly matches
  an already-created model `asset_entity` key for the same source root.

It does not create new entities and does not use substring matching.

## Validation

`python -m py_compile tools\endfield_source_graph.py` passed.

A full temp graph build was attempted with:

```bat
python tools\endfield_source_graph.py build --db %TEMP%\endfield_source_graph_asset_entity_validate.sqlite --skip-gameplay --skip-asset-maps --skip-reference-rows --skip-followups
```

The build hit the 5-minute timeout and left a malformed temp SQLite file, so it
was not used as evidence.

Targeted validation against `webui/data/assets/index.json` showed the new
normalizers map existing files to existing entity groups:

### `interactive_organdoor_1_001_01`

Existing model entity group:

```text
StreamingAssets / interactive_organdoor_1_001_01
```

Fallback material:

```text
StreamingAssets-materials/Material/M_interactive_organdoor+1_001_01_p8B217C88B3577E43.json
```

Fallback textures:

```text
StreamingAssets/Texture2D/T_interactive_organdoor+1_001_01_D_pC46AB6DC9F6756EE.png
StreamingAssets/Texture2D/T_interactive_organdoor+1_001_01_E_p03668CCC3F94E482.png
StreamingAssets/Texture2D/T_interactive_organdoor+1_001_01_MRO_pBBCC9B247BB5DD44.png
StreamingAssets/Texture2D/T_interactive_organdoor+1_001_01_N_p40943A3EAFC12306.png
```

### `interactive_universalswitch_1_001_01`

Existing model entity group:

```text
StreamingAssets / interactive_universalswitch_1_001_01
```

Fallback material:

```text
StreamingAssets-materials/Material/M_interactive_universalswitch+1_001_01_pC4C71F6AB801EEBA.json
```

Fallback textures:

```text
StreamingAssets/Texture2D/T_interactive_universalswitch+1_001_01_D_pBC282A4585AD81E4.png
StreamingAssets/Texture2D/T_interactive_universalswitch+1_001_01_MRO_p8EC512CB700E355C.png
StreamingAssets/Texture2D/T_interactive_universalswitch+1_001_01_N_p3D2156F1E699B19C.png
StreamingAssets/Texture2D/T_interactive_universalswitch+1_001_01_rgb_E_pAE5B0A8C02A9F382.png
```

## Why It Matters

The door and switch controller-alias investigations both point unresolved
gameplay model ids at exported visual-family entities:

- `int_door_experbase_v2_postmodel` aliases to
  `interactive_organdoor_1_001_01`.
- `int_switch_union_v2` aliases to
  `interactive_universalswitch_1_001_01`.

Before this change, `entity-assets` for those visual-family entities could show
mesh LODs but not same-family material/texture files visible in the flat asset
index. The fallback should make future source-graph refreshes present a more
complete renderable asset package for these alias targets.

## Next Checks

- Run a normal source-graph refresh when practical and confirm
  `entity-assets interactive_organdoor_1_001_01` reports nonzero material and
  texture counts.
- Check whether other plus-separated visual families, especially doorframe and
  ZMD-machine aliases, gain expected materials/textures without false matches.
- Keep controller aliases separate from promoted renderable bindings until
  prefab or AnimeStudio map evidence confirms the relationship.
