# Gacha environment-global publisher contract

Date: 2026-08-14

Verdict: **NO_PATCH; TWO EXACT CLOSURES, REMAINDER LIVE**

The current installed binaries and Gacha-room data close two deferred
environment inputs: the fixed `_MultiscatteringLUT` and the disabled
`_ASMShadowmapTex` identity. They also pin the producer and fallback ownership
for irradiance, volumetric scattering, cloud shadow, CSM, and punctual shadow
globals, but not their selected live contents. No neutral environment globals
are published into the lab.

## Evidence pins

- `GameAssembly.dll` SHA-256:
  `0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`.
- `UnityPlayer.dll` SHA-256:
  `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`.
- `global-metadata.dat` SHA-256:
  `90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`.
- Current environment-publisher audit SHA-256:
  `C46DF06536D5BC67F399ECF832BCB92189F48E5ECD13F016E89F112D6B94EC1D`.

The focused audit reports `NO_PATCH`, `allChecksPass=True`, and verifies native
method bodies, shader-property offsets, selected Gacha state, VFS irradiance
payloads, and both D3D11/D3D12 exact-closure GPU diagnostics. Its ignored
checker was refreshed only for the current irradiance-ownership audit hash;
production source was not changed.

## Exact closures

### Multiscattering LUT

`HGRenderPathScene.PrepareData` calls `HGRenderPipeline.PreparePCMultiscattering`,
which lazily calls `SetupMultiscatteringLut` and publishes pipeline field `+0x178`
to `_MultiscatteringLUT` (shader-ID slot `+0x180`). The payload is fixed and
environment-independent:

- 32x32 `R16_UNorm` texture (`GraphicsFormat 21`);
- no mip chain, linear disabled, Clamp wrap, Bilinear filter;
- 2,048 raw bytes, SHA-256
  `1A15AFE25B25E7AA64DCF17D74F5375DD1B692B3805CD00AA4F531AD289F030E`.

The isolated lab diagnostic reproduces this raw hash on both D3D11 and D3D12.

### ASM shadow

The selected Gacha volume has `shadowConfig.disableAsm=1`. The native
`ShadowMapPassConstructor` gate routes to `HGASMManager.SkipRenderASM`; the
skip callback binds `HGRenderGraphDefaultResources.defaultShadowTexture` to
`_ASMShadowmapTex` (shader-ID slot `+0xf8`). The exact fallback is a 1x1,
one-slice, 32-bit-depth shadow RTHandle. Its depth contents are intentionally
not fabricated or cleared in the diagnostic.

## Live publishers and boundaries

- **V2 irradiance (`t34/t31`, `t33/t30`, `t32/t29`)**: six handles are
  published by `HGIrradianceVolumeManagerV2.PipelineUpdateV2` through
  `RenderRequest.irradianceVolumeResultV2`, then by
  `HGRenderPathBase.UpdateShaderVariablesIrradianceVolumeV2` to shader IDs
  `0xcac..0xcc0`. Legacy Gacha character IV files belong the older manager;
  current-room V2 scene selection, voxel decode, transient atlas, six contents,
  and `param0..param3` remain open.
- **Integrated volumetric scattering (`t35`)**: active content is produced by
  volumetric grid injection and final integration. A disabled branch binds a
  black 3D fallback, but the selected Gacha frame's dimensions, history,
  depth, light lists, and shadows decide whether active integration runs.
- **Cloud shadow (`t8`)**: `UpdateShaderVariablesGlobalCloudShadow` delegates
  to `HGSkyRenderer.SetupShaderVariablesGlobalCloudShadow`. Gacha has
  `cloudConfig.enable=0` while the cloud-shadow flag is enabled, so sampled
  contribution is disabled; the external texture identity is not serialized
  in the managed publisher.
- **CSM (`t9/t10`)**: `HGShadowManager.ShouldRenderCSMShadowMap` selects an
  active atlas or skip callback. Gacha has `disableCsm=0` and a null ramp, but
  the live HGCamera settings, directional caster, shadow distance/cascades,
  and preview state are required to select the branch. Skip identity is
  default shadow plus black ramp.
- **Punctual shadow (`t26`)**: V2 publish callbacks bind the live atlas;
  disabled pass copies `defaultShadowTexture`. Room light rows alone do not
  decide the branch; runtime camera feature flags and the surviving cull/cache
  set remain open.

`ForwardPassUtils.RenderForwardTransparent` publishes only its pass-local
SceneColor/depth/GBuffer/blit resources. It never supplies these environment
globals, so enabling M02 with fabricated neutral clipmaps, fog, or shadow
atlases would replace selected state rather than recover it.

## Recovery rule

Use the fixed LUT and ASM fallback only within their source-backed diagnostic
scope. Keep irradiance, volumetric fog, cloud identity, CSM, and punctual
shadow paths fail-closed until an active scene/runtime capture identifies the
selected branch and contents. Do not treat the authored Gacha volume flags as
proof that a live atlas or fog volume exists.

Primary scratch evidence: `scratch/reverse_engineering/gacha_m02_forward_environment_publishers/`.
