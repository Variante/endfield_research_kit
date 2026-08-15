# Zhuang Fanyi baofa binary admission boundary

Date: 2026-08-15

The only fail-closed renderer in
`P_fxui_zhuangfy_ui_overview_start_01_baofa` is:

| fact | exact value |
|---|---|
| hierarchy | `.../all/daoguang_light (1)` |
| ParticleSystem PathID | `211230472171859223` |
| renderer PathID | `-1049115338939257577` |
| material | `M_fx_ui_zhuangfy_lightning_901` |
| material PathID | `6070151493152993176` |
| shader | `HGRP/Effect/VFXBaseV2` |
| shader PathID | `-1430105248647086886` |
| valid keywords | `_SAMPLE_TEX0`, `_SAMPLE_TEX1` |
| render queue | `3700` |
| selected native program | `ForwardOnly`, `blob1260/33` |
| outputs | `SV_Target`, `SV_Target_1` |

The prefab YAML displays the material long as little-endian bytes
`98ef303a9f823d54`; that string is not a second material PathID.

Existing D3D12 same-input probes prove that the compatibility shader compiles,
the hash-pinned meshes and textures bind, the exact row-affine indirect draw
executes, and both MRTs can receive nonzero output. They do not justify
production admission:

- the probe uses a transient compatibility/diagnostic material while the
  generated source material remains on `VFXUnavailableFailClosed`;
- it forces `_EndfieldSceneMVMRTReady` and
  `_EndfieldRecoveredVFXGlobalsReady` to `1` instead of observing their retail
  frame values;
- `nonzeroCoverageVerified` checks that something was written, not that any
  color, alpha, or SceneMV pixel equals retail output;
- the diagnostic has not closed the retail PSO, render-graph attachment,
  constant-buffer/global bindings, or the second-target compositor contract;
- both distinct frame-11 mesh rows currently produce byte-identical targets,
  which is compatible with congruent quads but is not independently proven.

Consequently `visualAdmission=false` remains correct. The smallest decisive
experiment is a same-build retail GPU/native draw capture for renderer
`-1049115338939257577`, followed by a same-camera, same-particle-row,
per-pixel comparison of both exact attachments without forcing the two
admission globals. Until that exists, the material identity and compiled
specialization are recovered diagnostic evidence, not an executable visual
replacement.

`EndfieldZhuangfyOverviewEffectBindingBuilder` now fails closed unless this
exact renderer/material/shader tuple remains the sole rejected baofa renderer.
Unity batch validation passed after adding the gate.
