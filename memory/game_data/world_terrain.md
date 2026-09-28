# Terrain: `TRET` and native path families

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the lane map.

**Level 3, world lane.** Each reader, gate and validator below has its
layout and instruction detail in its module docstring, and each native one
checks a reviewed contract in
[`contracts/`](../../scripts/game_data/contracts/):

| Module | Contract | Owns |
| --- | --- | --- |
| [`terrain/tret.py`](../../scripts/game_data/terrain/tret.py), [`terrain/native.py`](../../scripts/game_data/terrain/native.py) | [`terrain_tret_native.json`](../../scripts/game_data/contracts/terrain_tret_native.json) | `TRET` framing, native consumer, formats and shapes |
| [`terrain/height.py`](../../scripts/game_data/terrain/height.py) | none | `_H` diagnostic grid for Map |
| [`terrain/corpus.py`](../../scripts/game_data/terrain/corpus.py) | uses the TRET contract | current VFS corpus gate and path-family joins |
| [`terrain/layer_paths_native.py`](../../scripts/game_data/terrain/layer_paths_native.py) | [`terrain_layer_paths_native.json`](../../scripts/game_data/contracts/terrain_layer_paths_native.json) | UnityPlayer `LAYER_C/D/N` and six-file tile path records |
| [`terrain/tile_slots_native.py`](../../scripts/game_data/terrain/tile_slots_native.py) | [`terrain_tile_slots_native.json`](../../scripts/game_data/contracts/terrain_tile_slots_native.json) | tile path-result to render-property chain |
| [`terrain/layer_slots_native.py`](../../scripts/game_data/terrain/layer_slots_native.py) | [`terrain_layer_slots_native.json`](../../scripts/game_data/contracts/terrain_layer_slots_native.json) | layer path-result to render-property chain |
| [`terrain/virtual_texture_managed_native.py`](../../scripts/game_data/terrain/virtual_texture_managed_native.py) | [`terrain_virtual_texture_managed_native.json`](../../scripts/game_data/contracts/terrain_virtual_texture_managed_native.json) | managed renderer texture copies, converter arguments |
| [`terrain/manager_bridge_native.py`](../../scripts/game_data/terrain/manager_bridge_native.py) | [`terrain_manager_bridge_native.json`](../../scripts/game_data/contracts/terrain_manager_bridge_native.json) | managed-to-native manager setup bridge |
| [`terrain/shader_sampling.py`](../../scripts/game_data/terrain/shader_sampling.py) | [`terrain_shader_sampling.json`](../../scripts/game_data/contracts/terrain_shader_sampling.json) | authored `_ConeMaps` shader sample |

Every validator gates on the selected installed binaries and withholds its
result on a missing or changed build. Changing counts, per-family formats
and receipts live in `reports/animestudio/terrain_tret_latest.json` and
under `reports/terrain/`.

## Stored structure

- **`TRET` framing (exact).** `LAYER_C/D/N` and the six-file tiles are
  Terrain VFS block members that begin with `TRET` after the envelope. The
  native consumer reads decoded `+14` as a `GraphicsFormat`, checks the
  payload length at `+16` and copies from `+20`; its ABI takes no input
  length, so the corpus gate separately checks every complete decoded file.
  `+12` behaves like a mip count, but that name is inferred.
- **Formats (direct names, anonymous values).** `LAYER_C` uses format 5 with
  a one-byte footprint; `LAYER_D` is `RGBA_BC7_SRGB` and `LAYER_N`
  `RGBA_BC7_UNorm`, tiled into exact mip-like ranges. In the tiles, `_H`
  (65 by 65) and `_C` (34 by 34) are `R8G8_UNorm`, `_N` and `_A`
  `RGBA_DXT5_UNorm`, `_T` `RGBA_DXT5_SRGB` and `_S` `R8G8B8A8_UNorm` (132 by
  132 axes). Contained values stay anonymous.
- **Path families (structural).** Every `Terrain_*` tile key has all six
  H/N/T/A/S/C members, each suffix with one header shape and format. Per
  scene, `LAYER_D` and `LAYER_N` have identical index sets and `LAYER_C`
  occurs only at indices in them.
- **`_H` composite (diagnostic).** `height.py` combines each texel as
  `byte0 + 256*byte1` for Map contrast; that is not a proved height or even
  a proved relief ordering.

## Native path and render-property routes

- **Path construction (direct).** One UnityPlayer routine loads the exact
  `{0}/Layers/LAYER_C_{1}.bytes` (and `_D_`, `_N_`) templates into one
  grouped record per numeric argument, and in a later branch splits a packed
  tile argument to format the six `Terrain_*` templates into a separate
  record family. These are two grouped path families with no join between
  them and no renderer destination by themselves.
- **Tile chain (direct, conditional).** A queue worker promotes the tile
  record; its callback resolves all six handles (staged H/N/T/S/A/C, so A
  and S swap relative to the record) and guarded copies place each in a
  distinct owner-local destination bound to a string-derived property ID:

| Tile suffix | Selected render-property literal |
| --- | --- |
| `H` | `_HeightmapAtlas` |
| `N` | `_NormalmapAtlas` |
| `T` | `_TintColorAtlas` |
| `A` | `_AlbedoAtlas` |
| `S` | `_SplatCtrlAtlas` |
| `C` | `_CliffIndexAtlas` |

- **Layer chain (direct, conditional).** A separate queue promotes the layer
  record; its callback resolves the three grouped path-result handles in
  D/N/C order and forwards them through an owner subobject. D and N are
  copied to distinct owner-local resources; C only when its source is
  present and an owner availability check passes. A render-binding function
  pairs the same three resources with string-derived IDs, skipping C when
  its resource is null:

| Layer path | Selected render-property literal |
| --- | --- |
| `LAYER_D` | `_Splats` |
| `LAYER_N` | `_Normals` |
| `LAYER_C` | `_ConeMaps` |

  The property names establish the render-binding route. Stored pixel
  channels, a managed `VirtualTextureRenderer` field, shader sampling in a
  live draw, and live file selection remain open.
- **Authored shader sample (direct, authored).** In the serialized
  `HGRP/HGTerrainPS` `VTBakePage` Vulkan fragment program, `_Splats`,
  `_Normals` and `_ConeMaps` are separate array inputs; the 2D-array
  `_ConeMaps` is sampled four times, each result feeding a component-zero
  extract. The gate traces the exact SPIR-V path from a targeted conversion
  written only to `scratch/`. It does not prove that this variant ran, that
  an installed `LAYER_C` file reached it, or what the sampled value means.

## Managed side

- **Renderer copies (direct).** `HGTerrainRenderer(TerrainResource)` builds
  a `VirtualTextureRenderer` from the same value, and the child copies eight
  `runtimeResources.textures` fields (two `Texture2DArray` splat arrays and
  six `Texture2D` maps) into its own fields. A bounded direct-call census
  finds no direct call to the parent constructor, so its caller and the
  `TerrainResource` supplier are unknown.
- **Converter to native setup (direct, conditional on unpatched branches).**
  `HGTerrainConvertFunc.ConvertFrom` converts four property IDs
  (`PROP_ID_TERRAIN_CS`, `PROP_ID_TERRAIN_RTCS`, `PROP_ID_TERRAIN_PS`,
  `PROP_ID_SPLAT_INDEX_MAP`) into typed `SetupFromParams_Phase1` arguments
  (two `ComputeShader`, one `Shader`, one `Texture2D`), then reaches
  `HGTerrainManager.SetupTerrainManager`, whose internal-call trampoline
  resolves to a UnityPlayer wrapper that calls a native terrain setup entry.
- **Missing join.** No checked edge carries a `LAYER_*` or tile path-result
  handle into `TerrainResource.runtimeResources.textures`, and no converter
  argument is shown to fill a `Texture2DArray` field. `ConvertFrom` reads
  none of the three declared splat-array property IDs, and the object-index
  schema sweep has no rows for the array fields; neither unchecked result
  excludes other producers.

## Evidence boundary

- **Exact:** every current `TRET` file's framing, and the six-member tile and
  D/N/C index relations in the audited set.
- **Direct:** GraphicsFormat names and footprints, the path templates and
  record construction, both render-property chains, the managed texture
  copies, the converter-to-native-setup route and the authored `_ConeMaps`
  sample path, each conditional on its checked branches.
- **Inferred:** `+12` as a mip count.
- **Unresolved:** decoded channel meanings for every family; which installed
  paths a live scene opens; a join from the native owner-local handles to
  managed `TextureResources` fields; the shader variant of a live draw; the
  visual effect of any payload.

## Eliminated readings

- `LAYER_C` as `m_colorVariationTex` (reached by elimination, rejected on
  type, reinstated by a compositing proposal) is retracted by the direct
  `_ConeMaps` binding; the per-layer mask suggestion has no field join
  either (`terrain/layer_slots_native.py`).
- D/N/C meanings from index pairing alone are superseded by the
  render-property join.
- Tile suffixes or the `_H` composite as runtime texture roles or heights
  (`terrain/height.py`).
- A shared word such as "splat" as the missing native-to-managed edge; a
  string-derived property ID, a native owner-local handle and a managed field
  are distinct evidence.
- The single `Texture2D` splat-index argument as evidence that a `LAYER_*`
  family fills a `Texture2DArray` field
  (`terrain/virtual_texture_managed_native.py`).
- Metadata default bytes read as plain four-byte integers; constants such as
  `TEXTURE_SIZE` also name no destination (`terrain/native.py`).
- The path window as a whole function; it is a continuation after the entry
  and prelude (`terrain/layer_paths_native.py`).

## Recovery queue

1. The native setup entry's resource construction and any ownership link to
   the `LAYER_*` result handles.
2. The converter helper's returned-object identity for the four checked
   setup arguments.
3. An indirect-caller or resource-producer trace for `HGTerrainRenderer.ctor`,
   the separate route to the `TerrainResource` fields.
4. A runtime selection witness tying an installed path to a live copy and
   the shader variant used for that draw.
