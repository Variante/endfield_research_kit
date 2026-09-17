# Terrain: the `LAYER_*` arrays

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, world lane.** The first payload family to decode end to end, and the
one that supplied the container in
[`shared_containers.md`](shared_containers.md). It is also a worked example
of asking the engine's own field names before running byte statistics.

## What the `LAYER_*` families are, from the engine's own field names


The second-largest `.bytes` family after IrradianceVolume, and untouched until now:
**345 `LAYER_N_*` (469 MB) + 345 `LAYER_D_*` (414 MB) + 54 `LAYER_C_*` (57 MB)**, 940 MB
in all. Asking the metadata first this time, rather than after seven byte-statistic
eliminations.

`HG.Rendering.Runtime.VirtualTextureRenderer` has 93 fields, and four of them settle it:

```
m_splatsDiffuseArray      m_splatIndexMap        m_terrainNormalMap
m_splatsNormalArray       m_splatControlMap      m_terrainHeightmap
                          m_colorVariationTex    m_deformableControlMap
VT_CLIPMAP_BASE_WIDTH, VT_CACHE_PAGE_RESOLUTION, VT_CACHE_PAGE_BUFFER_SIDE_SIZE,
VT_INDIRECT_TEX_BUFFER_COUNT, VT_GPU_FEEDBACK_BUFFER_COUNT, VT_WORK_GROUP_COUNT
```

- **`LAYER_D` is the splat diffuse array and `LAYER_N` the splat normal array.** The
  counts agree: **345 each, exactly paired**, which is what two texture arrays over the
  same layer set look like. `LAYER_C` at 54 files is a control or colour map --
  `m_splatControlMap` and `m_colorVariationTex` are both candidates and it is not
  settled which.

## The `LAYER_*` families

All three share the container above, verified on **105 files with no exceptions**:

| field | value |
| --- | --- |
| `+0` magic | **`TRET`** (105/105) |
| `+4` version | 1 (105/105) |
| `+8`, `+10` | width, height = **1024 x 1024** (105/105) |
| `+12` | **11** -- the mip-level count (105/105) |
| `+14` | format code: **5** = `C`, **108** = `D`, **109** = `N` |
| body | a **full mip chain, 1 byte per texel** |

***The size equation closes exactly:*** `header + sum((1024 >> i)^2 for i in 0..10)` equals the
file length in **105 of 105 files, with zero trailing bytes**. The chain sums to 1,398,101.
*The `+12` field is not inferred to be a mip count -- 11 is exactly the number of levels the size
equation requires.*

***The header is 20 bytes for every family.*** The u32 at `+16` equals **file length - 20 in 105
of 105 files**, which fixes the header at 20 and makes that field a payload size.

## `C` is uncompressed; `D`/`N` are block-compressed

***There is no 27-byte prefix.*** That number was an artefact of assuming an uncompressed layout
for all three. Block-compressed formats are 1 byte per texel but **pad every mip below 4x4 to a
full 16-byte block**, so the two tails differ by exactly 27 bytes:

| chain | bytes |
| --- | --- |
| uncompressed, 1024^2 down to 1x1 at 1 B/texel | 1,398,101 |
| block, 1024^2 down to 4x4 plus two 16-byte mips | **1,398,128** |

| family | uncompressed chain | block chain |
| --- | --- | --- |
| `C` (7 files) | **7 / 7** | 0 / 7 |
| `D` (49 files) | 0 / 49 | **49 / 49** |
| `N` (49 files) | 0 / 49 | **49 / 49** |

***Perfect separation, no crossover***, and it explains three things that did not previously fit:

* **`C` is a real image and `D`/`N` are not, byte-wise.** Downsampling L0 and comparing to L1
  gives a mean error of **4.5 for `C`** and **72-75 for `D`/`N` at every candidate offset** --
  block-compressed data cannot be box-filtered at byte level.
* **Entropy and adjacency agree.** `C` reads **6.12 bits/byte with +0.973 adjacent-byte
  correlation** -- a natural image; `D`/`N` read **7.56/7.83 bits with +0.09/+0.12** -- the
  signature of compressed blocks.
* The `D`/`N` level means sitting at ~128 at *every* level, which looked like signed encoding,
  is just compressed data looking random.

**So format code 5 is uncompressed 8-bit and 108/109 are two block-compressed formats** -- and
the earlier note that `C` "holds a different kind of quantity" was right for the wrong reason.

Decoding the levels confirms a real image pyramid: `LAYER_C`'s level means fall monotonically
**37.97 -> 1.00**, which is what repeated downsampling does.

**One statistical difference.** `D` and `N` sit at level means of **~124 and ~131**, hovering
around 128 across every level, whereas `C` starts at **38** and decays. *Data centred on 128 is
signed or offset-encoded; `C`'s is not*, so **`C` holds a different kind of quantity from
`D`/`N`.**

## `LAYER_C` is not a splat control map

The file *counts* settle what the byte statistics could not. Over **744 LAYER files in 38
directories**:

| | |
| --- | --- |
| directories where `D` and `N` index sets are identical | **38 / 38** |
| directories where `C`'s index set is a subset of `D`'s | **22 / 22** |
| directories with **no** `C` file at all | **16 / 38** |
| `C` files per directory where present | 1, 2 or 4 -- *never a fixed one* |

***A splat control map is terrain-wide: exactly one per terrain, always present.*** `C` is
neither. Its indices are drawn from the same per-layer numbering as `D`/`N` (`C[4,5,13]` against
`D[0..7]`), most terrains have none, and those that do have a handful. **So `C` is a per-layer
optional map, and the `m_splatControlMap` reading is eliminated** -- leaving the
`m_colorVariationTex` sort of per-layer extra, which is what an optional third texture attached
to *some* layers looks like.

**The `D`/`N` pairing claim is independently confirmed** by the same census: identical index sets
in every one of the 38 directories, which is stronger than the matching file counts it rested on
before.
- The surrounding machinery is named too: `HGASMVirtualTextureAllocator` with
  `AllocateTile` and `GetVTData`, `ASMTileManager` with an LRU tile cache,
  `HGTerrainGroundLayerClipmap` with `Initialize`/`Render`/`SetPlayerCenter`, and
  `HGTerrainGroundLayer` carrying `TEXTURE_SIZE` and
  `TERRAIN_GROUND_LAYER_CLIPMAP_NUM` with base, normal, wet and height render targets.
- So this family is **GPU texture data for a virtual-texture terrain splat system**,
  the same shape of answer the IrradianceVolume payload turned out to have.

## The engine's constants are readable, and they decode as compressed integers

`fieldDefaultValues` in `global-metadata.dat` holds every `const` in the image, and the
blob is **ECMA-335 compressed unsigned integers** -- not raw 4-byte values. Reading it
as raw int32 gives garbage like `TEXTURE_SIZE = 262280`; decoded properly:

| constant | value | | constant | value |
| --- | --- | --- | --- | --- |
| `HGTerrainGroundLayer.TEXTURE_SIZE` | **2048** | | `VT_CACHE_PAGE_RESOLUTION` | **512** |
| `TERRAIN_GROUND_LAYER_CLIPMAP_NUM` | **4** | | `VT_CACHE_PAGE_BUFFER_SIDE_SIZE` | **128** |
| `ASMTileManager.MAX_TILE_COUNT` | **512** | | `VT_CACHE_PAGE_BUFFER_SIZE` | **8192** |
| `VT_CLIPMAP_BASE_WIDTH` | **16** | | `VT_INDIRECT_TEX_BUFFER_COUNT` | **6** |
| `VT_WORK_GROUP_COUNT` | **64** | | `VT_GPU_FEEDBACK_BUFFER_COUNT` | **8** |
| `VT_COMPRESS_LOCAL_THREAD_COUNT` | **32** | | `VT_CPU_FEEDBACK_RAYCAST_DIST` | **1000.0f** |

**Three things check the decoder at once.** Every integer comes out a power of two or a
small round number; the one float reads exactly `1000.0`; and each field's `dataIndex`
advances by exactly the width the decoder consumed -- 1 byte for values under 0x80, 2
above. A wrong decoding satisfies none of those. *This is reusable: any `const` in the
image is now readable the same way.*

## The `LAYER_*` files are NOT raw texture slices

With `TEXTURE_SIZE = 2048` in hand the prediction was testable, and it fails:

| family | files | distinct sizes | typical |
| --- | --- | --- | --- |
| `LAYER_N` | 345 | **67** | ~1.33 MiB |
| `LAYER_D` | 345 | ~60 | ~1.20 MiB |
| `LAYER_C` | 54 | 9 | 0.86-1.11 MiB |

No size is a multiple of a 2048x2048 surface at any block rate -- the ratios land on
0.32, 0.64, 0.55 and similar, never a whole number or a mip chain. **Sizes that vary
file by file are not raw slices**, so the payload is compressed or variably encoded,
exactly as the IrradianceVolume payload turned out to be.

*The constant gave the prediction a number to fail against. Without it "about 1.3 MB" would have looked like agreement with almost anything.*

## CORRECTION: the `LAYER_*` files were already decoded, by the terrain lane

They are in the **Terrain** block -- 744 of them, which the CLI confirms -- and
`terrain_stream.load_samples` takes *every* file in that block rather than only
`Terrain_*`. So they have been inside the gated corpus the whole time.

- Running the maintained codec over them: **744 of 744 close**, 743 through the stream
  decoder and 1 stored, each to exactly its declared length. Every decoded payload
  begins `TRET`.
- Only **two decoded sizes** exist: 1,398,148 (x690) and 1,398,121 (x53).
- **The terrain report already names that group.** `terrain_tret_latest.json` carries
  `layer2And3.frontier108And109.files = 690`, status `exact_anonymous_record_tiling` --
  the same 690 files, already closed, already gated, counted inside the 46,164.

***I nearly reported "744 of 744 decode" as a new result.*** It is not. The decode is
the terrain lane's, done long ago; the filename triage found a family the block-level
corpus had already swallowed. *A file-name family and a block are different
partitions, and a new name for an old set is not a new set.*

**What IS new here** is the naming. The terrain report calls that group
`exact_anonymous_record_tiling` -- exact, and anonymous -- and its header report already
carries the formats:

| family | format | files | `VirtualTextureRenderer` field |
| --- | --- | --- | --- |
| `LAYER_D` | `mips11_format108` | 345 | **`m_splatsDiffuseArray`** |
| `LAYER_N` | `mips11_format109` | 345 | **`m_splatsNormalArray`** |
| `LAYER_C` | `mips11_format5` | 53 | see below |

`frontier108And109` in `terrain_tret_latest.json` is exactly **formats 108 and 109**,
which is exactly `LAYER_D` and `LAYER_N`. **690 anonymous records now have a name, and
the 940 MB they hold has a purpose.**

### `LAYER_C` is per-layer and optional, which rules out the control map

Across the **38 directories** that hold LAYER files:

- **`D` and `N` carry identical index sets in all 38** -- strictly paired, one diffuse
  and one normal per splat layer. That confirms the pairing rather than assuming it from
  the equal totals.
- **`C` appears in only 22 of the 38**, and sparsely where it does: 1 `C` against 4
  `D`/`N`, 4 against 18, 2 against 27, 1 against 7. Its indices run to 34, the same
  layer-index shape as `D` and `N`.

An **optional, per-layer** texture is `m_colorVariationTex`. It is **not**
`m_splatControlMap`: a control map is one per terrain, always present, and would not
carry a layer index nor be absent from 16 directories. *The distribution settles which
of the two candidates it is without needing to read a byte of its content.*

#### REOPENED: a rival candidate the distribution argument could not have weighed

The argument above chose `m_colorVariationTex` by eliminating `m_splatControlMap`. The
engine, read since, offers a **third** candidate with the same profile, and the choice is
no longer forced.

**A per-layer mask map is a first-class concept here.** `maskMapRemapOffset` and
`maskMapRemapScale` sit inside **`TerrainLayerInfo`** and **`SplatLayerData`** -- the
*per-layer* structs -- and the shader side carries `_MaskMapTexture`,
`_MaskMapRemapMin/Max/Offset/Scale`. An optional, layer-indexed third texture is exactly
what a mask map is.

**And the typing mildly favours the rival.** `VirtualTextureRenderer` binds three:

| field | type index |
| --- | --- |
| `m_splatsDiffuseArray` | **144608** |
| `m_splatsNormalArray` | **144608** |
| `m_colorVariationTex` | **144600** *(different)* |

*The two per-layer arrays share one type; the colour-variation binding has another* -- the
shape of `Texture2DArray` twice and `Texture2D` once. A single non-array binding is an odd
consumer for files that carry layer indices running to 34, whereas the mask map's
parameters are stored per layer.

**The census is reproduced, not disputed.** An independent count gives `C` in 22 of 38
directories, 54 files against 345 each of `D` and `N`, with `D` and `N` equal in every
directory -- matching the numbers above exactly.

***The discriminator was run, and it disconfirms the answer above.*** Resolving the indices
through `MetadataRegistration.types` in `GameAssembly.dll` (225,789 entries at VA
`0x18c472bb0`; the type enum is bits 16-23 of the `Il2CppType` bitfield):

| field | type index | declared type |
| --- | --- | --- |
| `m_splatsDiffuseArray` / `m_splatsNormalArray` | 144608 | **`UnityEngine.Texture2DArray`** |
| `m_colorVariationTex` | 144600 | **`UnityEngine.Texture2D`** |

**The arrays are per-layer; the colour-variation binding is a single texture.** And the
argument that selected it eliminated `m_splatControlMap` on the grounds that *"a control map
is one per terrain, always present, and would not carry a layer index"*. **`Texture2D` is
one per terrain too** -- so the elimination that chose this answer also rules it out. *A
distribution argument can only separate candidates it has typed; this one separated a name
from a name.*

**The rival does not simply inherit the win.** `VirtualTextureRenderer` binds exactly
`m_splatsDiffuseArray`, `m_splatsNormalArray`, `m_colorVariationTex` and
`m_decalBlockMaskLut` -- there is **no mask-map texture array**. The mask map's
`maskMapRemapOffset`/`maskMapRemapScale` are `UnityEngine.Vector4` *parameters* per layer,
which is consistent with a mask packed into the existing arrays rather than shipped as its
own files.

#### CORRECTION TO THE CORRECTION: the original identification survives

The disconfirmation above over-reached, and two further checks show why.

***There is no alternative binding.*** Across the **entire** metadata, exactly **four**
fields are declared `UnityEngine.Texture2DArray`, all on `VirtualTextureRenderer`:
`m_splatsDiffuseArray`, `m_splatsNormalArray`, `m_decalDiffuseTexArray`,
`m_decalNormalMROTexArray`. **No third splat array exists anywhere**, so "something bound
outside `VirtualTextureRenderer`" is not available -- there is nowhere else for a
per-layer terrain texture to go.

***And `LAYER_C` really is per-layer.*** Its indices are a **subset of that directory's
`D` index set in 22 of 22 directories, with zero exceptions** (`C=[5]` against `D=0..6`;
`C=[4,5,13]` against 15 layers; `C=[2,8]` against 11). The recorded claim was right and my
doubt about it was not.

**The objection dissolves rather than the answer.** The disconfirmation rested on
`m_colorVariationTex` being a `Texture2D` and therefore "one per terrain", which was taken
to exclude layer-indexed source files. *That only follows if each file is bound directly
as an array slice.* Per-layer files **composited into** one texture -- which is what a
virtual-texture renderer does, and what `HGTerrainSplatStreaming` in the engine's log
strings names -- are per-layer inputs to a single binding, with no contradiction at all.

**So `m_colorVariationTex` stands as the identification**, now on stronger ground than the
distribution argument alone: it is the only colour-carrying terrain texture binding in the
game, and the per-layer/per-terrain mismatch that seemed fatal is just the difference
between a source file and a bound result. *I disconfirmed a correct answer by assuming the
binding had to be one-to-one with the files, which is the sort of premise that never gets
stated and so never gets checked.*

`LAYER_C` also uses format **5** where `D` and `N` use 108 and 109 -- a low, presumably
standard format against two engine-specific ones, which is consistent, though the format
numbers themselves are not decoded.

*Two batches were spent eliminating containers for IrradianceVolume before asking the
metadata. This family got asked first, and the answer arrived in one read.*

**A route to `LAYER_C`'s purpose that is now closed.** `LAYER_` occurs **132** times in
`global-metadata.dat`, which looks like the obvious place to look next. It is not: every
one of those is an **animation** layer -- `LAYER_MAIN`, `LAYER_UPPER`, `LAYER_TWO_ARMS`,
`LAYER_LOOKAT_PITCH_YAW`, `LAYER_MASK2` -- plus a few concatenated string-table runs. The
terrain `LAYER_*` files share a prefix with an unrelated concept, and *a string search
that matches the wrong namespace is worse than no hits, because it returns something.*
`LAYER_C`'s purpose stays where the distribution argument left it.
