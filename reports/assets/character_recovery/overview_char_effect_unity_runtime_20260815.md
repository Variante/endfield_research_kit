# Character Info shared `CharEffect` Unity runtime recovery (2026-08-15)

## Recovered unit

The lab now builds and replays the scene-owned Character Info `CharEffect`
after the selected actor's Overview Animator restart. This is independent of
the Gacha Timeline effect requests.

Source-closed inputs:

- Prefab `assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab`.
- Root/trail GameObject PathIDs `803616490075416323` /
  `3013782730707986179`.
- Trail ParticleSystem/renderer PathIDs `8113670769548486403` /
  `5757248678484338435`.
- Material `M_UI_charChoose_12` PathID `4388811075012960551`.
- Texture `T_fx_mask_01_M` PathID `-7046954404783675798`.
- Selected D3D11 fragment `HG_ENABLE_MV + _USE_RBOFFSET`, DXBC hash
  `f905de094d0261d5`.

The generated particle contract contains both complete ParticleSystem and
ParticleSystemRenderer serialized payloads. Unity preserves the disabled root
renderer and its null material PPtr; only the enabled `trail` renderer binds
the exact material.

## Shader execution

`Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT` now contains the selected
`_USE_RBOFFSET` path:

1. sample the incoming SceneColor at the ordinary refracted UV;
2. form the second UV from `_RBOffset=(5,0)` in percent space;
3. sample SceneColor again;
4. apply `_RBMainColorMask=(1,0,0)` and
   `_RBOffsetColorMask=(0,1,1)`;
5. combine with `max` and interpolate by `_RBIntensity=1`;
6. retain the Distortion MRT Target1 output `(0,0,1,0)`.

The material remains queue 3000 and uses the existing source-closed
SceneColor/SceneMV Distortion compositor. It is not routed into after-DOF.

## Runtime ownership and spatial transform

`CharacterRecoveryViewerUI` starts the shared effect only after
`EndfieldOverviewPlayback.RestartOverviewFromSelection`, matching the native
`ForceUpdateAnimator -> _PlayModelEffect` ordering. A single reusable scene
effect is parented beside the selected actor under the serialized
`SingleEffects` transform:

```text
localPosition = (-0.3, 0, 0.05)
localRotation = identity
localScale    = (0.5, 1, 0.5)
```

The original `effect1..effect4` height buckets all have identity local
transforms. The runtime therefore preserves their common spatial result while
leaving the missing table-owned height classification explicit.

Every new selection clears and restarts both source ParticleSystems. Viewer
teardown removes the shared stage. Runtime admission checks the exact schema,
root/trail identities, native payload flags, material PathID, shader, queue,
keyword, and texture name and otherwise fails closed.

## Validation

- `python unity_endfield_graph_shader_lab/tools/verify_charinfo_overview_effect_contract.py`
  passed with contract SHA-256
  `CEA5072009EA33EDAAB0BAEF78B4B0B12D787DFE3A5E1521E55DF8AB13131693`.
- Unity 2022.3.62f3 `EndfieldCharInfoParticleEffectImporter.BuildAndValidate`
  passed and exited batchmode successfully.
- Unity `EndfieldCharInfoSharedEffectRuntimeVerifier.Verify` passed:
  two ParticleSystems, two renderers, exactly one visible trail renderer,
  exact stage transform, exact MRT shader/keyword, and successful teardown.
- A fresh isolated AnimatorController export restored 1,269 controller JSON
  files. The controller audit passed 31 main Overview controllers, 4 fixed and
  27 normalized handoffs, and 636 body/private-deco state compositions.

## Remaining boundary

No D3D12 pixel capture of this exact Character Info trail exists yet. The
runtime blend-state resolution, particle culling/sort tie, live `_VFXParams0`,
and retail SceneColor alias must still be compared before claiming pixel
parity. The common trail also does not own or explain the character-specific
large visual layers in the retail recording; Li Zhiyan and Zhuang Fangyi's
audited Overview AnimationEvents are audio-only, and Luoxi's character asset
chain remains missing.
