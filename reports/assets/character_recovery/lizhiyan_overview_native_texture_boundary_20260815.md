# Li Zhiyan Overview native-texture boundary

## Result

The eight Texture2D PathIDs referenced by
`P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub` now have exact native
payload evidence from the installed VFS. A focused AnimeStudio export produced
eight target BC7 payloads and manifests; one additionally exported dependency
was excluded by exact PathID membership.

For every target, the native manifest proves a single 2D image, zero stripped
mips, a complete largest-to-smallest BC7 mip chain, exporter-validated byte
layout, dimensions, color space, and serialized filter/aniso/mip-bias/wrap
settings. Payload size and SHA-256 are revalidated by the contract builder.

`lizhiyan_overview_finger_effect.json` is now schema v2. Its deterministic
file SHA-256 is
`DD142A7A093644FD548FBA18601791CCC7D6C4E83060035DADAC31BC30312375`;
the aggregate over serialized effect evidence, converted PNGs, native payloads,
and native manifests is
`ED06C415C6C2F630FE76D7382156F1D2AF413829371BB48E011F664A3CDC6E33`.

## Admission boundary

This closes missing native texture bytes and sampler metadata, not retail draw
ownership. The six exact materials use only three serialized keyword sets:
no valid keyword, `_USE_SOFTBLEND`, and
`_SAMPLE_TEX0 + _USE_SOFTBLEND`. Those material selections are now joined
separately to the installed Persistent-VFS shader's three exact compiled
VFXBaseV2 pairs. They still do not prove a retail live descriptor table, PSO overrides,
ForwardOnly dual-MRT attachments, scene-depth handoff, ordering, or final
compositing. All six generated materials therefore remain on ColorMask-0.

## Validation

- Targeted installed-VFS Texture2D export completed successfully.
- Contract generation completed twice byte-identically.
- Unity 2022.3.62f3 batch import completed successfully with 8 hierarchy nodes,
  7 particle pairs, 6 fail-closed materials, and exactly 8 native evidence rows.

The next useful step is a retail draw capture or equivalent descriptor/PSO
trace within the `38-47 s` Li Zhiyan Overview window, with the hand-adjacent
teal layer near 40 seconds as an acceptance oracle.
