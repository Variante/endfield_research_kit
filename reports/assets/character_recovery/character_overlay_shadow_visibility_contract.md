# CharacterNPR OverlayShadow clustered visibility contract

Status: source-closed for the isolated CharInfo/Character Overview path; not a
general gameplay-lighting implementation.

## Current evidence

- Installed source is pinned by GameAssembly SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`,
  global-metadata SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`, and
  OverlayShadow fragment `0031_endfield_dxbc_1.dxbc` SHA-256
  `6997620071f0b1082abc4193cb173f410ff64cb8856ab81f2a8d1a9abb7d21d2`.
- The refreshed operator-light export is 31 exact CharInfo rigs and 273
  serialized lights. It includes Liino (`liino`) with seven lights, including
  one type-4 Fog row. The source scope is 41 type-4 Fog rows across 31 rigs:
  36 advanced-carrier rows, five convenience rows, and ten directional-falloff
  rows. Current operator contract SHA-256 is
  `a47cb146f997f2dc1ddec1994978a37cc3992103060295710fcfeed4be89a710`.
- The regenerated eye-shadow material audit now covers 29 LOD0 renderers and
  87 generated overlay materials, including Liino's
  `S_actor_liino_eyeshadow_01_lod0`. Its two shared eye-shadow materials were
  corrected to render queue 2900; the audit reports zero material failures.
- The current Texture2D import contract is now source-closed at 897 rows,
  including all 22 Liino-owned texture rows and three Persistent item-widget
  rows. Its source census resolves 897/897 AssetMap entries with 1,541
  generated copies; contract SHA-256 is
  `D8322676C26F4FE35179C2ABE722404682216423915E8F79EF3B51D4DB2A0284`.

## Closed shader/resource contract

The selected fragment consumes the clustered `_GlobalBinningBuffer` and
`_PunctualLightData` records. The recovered CharacterNPR path is:

1. `LightCharacterOnly` is read from punctual record lane `3.z`, while lane
   `3.w` is `HGLightNPRType`.
2. `CharacterParams12.z` is the inverse of
   `charIgnoreSceneAdditionalLights`; character-only rows remain admitted when
   scene additional lights are ignored.
3. Only NPR type 4 (Fog) contributes to OverlayShadow local-volume occlusion;
   type 16 is excluded. The attenuation uses `max(2*nprData.y, 0.1)`, optional
   axial directional falloff, squared spot-cone attenuation, the exact `1e-4`
   threshold, and saturating accumulation by `nprData.x`.
4. The isolated producer uses exact 32-pixel XY bins and 2048 one-unit Z slices,
   with eight 32-bit membership words. Missing rig, compute support, perspective
   camera, or membership buffer binds neutral zero occlusion.

The implementation is limited to the lab's isolated CharInfo path in
`EndfieldHGRPCharacterLighting.cginc`,
`EndfieldCharacterOverlayShadowRecovered.shader`,
`EndfieldRecoveredLightBinning.cs`, and
`EndfieldRecoveredLightBinning.compute`.

## Validation and boundary

The focused checker passes the hash-pinned fragment/decompile, native ownership
tokens, current 31-rig/273-light scope, 29-renderer audit, runtime input
verifier, face/eye/overlay chronology verifier, and the full refreshed
material/import verifier. The exact native payload contract now covers 215
objects / 420 generated PNG owners / 444,635,856 logical bytes (213 unique
payload files / 442,888,176 bytes), including 22 source-manifest-gated Liino
body/cloth/face/hair/iris/skill/item-widget rows. Jsspsi and other unselected
priority surfaces remain descriptor-only; no payloads are guessed.

The native `HGCullingSystem.CullLights` candidate producer for arbitrary
gameplay scenes remains opaque. Live interleaving with unrelated scene lights,
shadow/cache/cookie state, authored OBB/flicker/culling-distance updates,
equal-queue proprietary tie ordering, and retail pixel-difference capture are
still open.

Evidence index: `scratch/reverse_engineering/eye_shadow_cluster_visibility/`
and the regenerated audit under
`unity_endfield_graph_shader_lab/scratch/character_recovery/last_rite_zhuang_material_audit/`.
