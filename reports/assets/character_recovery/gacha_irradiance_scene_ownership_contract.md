# Gacha irradiance and V2 scene ownership contract

Date: 2026-08-14
Verdict: **NO_PATCH**

This round revalidated irradiance ownership against the currently installed
game binaries and the updated AnimeStudio CLI. No Unity or shader-lab patch is
justified: the remaining unknowns are live scene selection and streamed voxel
contents, not a proven missing bridge.

## Evidence pins

- `GameAssembly.dll` SHA-256:
  `0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`.
- `UnityPlayer.dll` SHA-256:
  `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`.
- `global-metadata.dat` SHA-256:
  `90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`.
- Current AnimeStudio CLI (length 168,960) SHA-256:
  `6B36E51895C117296814AE3C6B02FD378AA58D5DC48239CFC3C9434F3209A161`.

The two focused scratch auditors were regenerated with these current hashes
and pass closed-world validation:

- legacy Gacha ownership audit: `audit.json` SHA-256
  `DF2144C668370E35D69B828B31E9C70BBE4BFC118C1B563A28809A3457BC8F95`;
- V2 scene-stream audit: `audit.json` SHA-256
  `15F24BCF5BC088B329A6826F80D0E9BB032D9268BF32562D2679B1592CF00859`.

The expected hashes were refreshed only in ignored scratch checker files; no
production exporter or Unity source was changed.

## Ownership boundary

The installed Gacha Lua sends
`Data/IrradianceVolume/PC/gacha/character` to the older
`HGIrradianceVolumeManager.CreateGachaIV` path. The six recovered raw Gacha
character IV files therefore belong to the legacy manager and must not be
wired into M02's V2 clipmap globals.

`HGIrradianceVolumeManagerV2.PipelineUpdateV2` is a separate path. It renders
`m_defaultIV` from the underlying scene and uses `m_gachaIV` only for update
center. `StreamingInNewMapV2` builds a scene-root-relative `/v3/index.bytes`
path; native `SetMap` stores the complete index path, cancels the prior load,
and requests a reload. The Gacha room itself is a prefab overlay, not a
scene: its installed prefab container has no Scene object, and the installed
VFS contains no `gacha/room` or `gacharoom` V2 IV payload.

Installed VFS inventory is 224 IV files in 60 chunks (3,928,773,518 bytes),
including 83 current single-root scene V2 indexes, 12 explicitly legacy
`gacha/character` or `gacha/weapon` files, and zero room-owned files. No
available static evidence selects one of the 83 scene indexes for the active
Gacha overlay.

## Closed V2 resource ABI

The six V2 result slots are published in this order:

`clipmapTextureALod0`, `clipmapTextureBLod0`, `clipmapTextureALod1`,
`clipmapTextureBLod1`, `clipmapTextureALod3`, `clipmapTextureBLod3`.

The A slots are writable `B10G11R11_UFloatPack32` 3D textures of
`128x64x128`; B slots are writable `R8G8B8A8_UNorm` 3D textures of
`128x64x384` (low-quality mode uses `128x64x128`). Missing-map state releases
all full-size clipmaps, zeros `param0..param2`, sets `param3` to
`[0, 1/3, 0, 0]`, and binds the same 1x1x1 zero UnityDefault3D fallback to
all six slots. Managed publication retains ready/quality state and writes the
frame ring into `param3.z` (`curFrameIdx % 64`).

## Open boundary and recovery rule

The live scene index, selected region payloads, V2 streamed voxel decoding,
transient atlas dimensions, and per-frame `param0..param3` contents remain
unidentified without an active underlying scene/runtime capture. Keep the
irradiance path fail-closed for Gacha/M02; do not substitute legacy Gacha
character IV files or an arbitrary one of the 83 scene indexes.

Primary scratch evidence:

- `scratch/reverse_engineering/gacha_irradiance_streaming_ownership/`;
- `scratch/reverse_engineering/gacha_v2_irradiance_scene_streaming/`.
