# Gacha post-processing and exposure contract

Date: 2026-08-14

Verdict: **SOURCE_CLOSED_POST_CHAIN; RUNTIME_HISTORY_FAIL-CLOSED**

This round closes the original binary's Gacha post-processing order, Bloom
profile, physical-camera exposure owner, and `_ExposureWithMiscParams` channel
contract. The selected-frame exposure carry-in, exact frame deltas, AfterDOF
gate, and lower volume-stack ownership remain runtime state; no constant or
fresh-camera reset is substituted.

## Evidence and checks

Installed source identities remain:

- `GameAssembly.dll` SHA-256
  `0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`;
- `UnityPlayer.dll` SHA-256
  `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`;
- `global-metadata.dat` SHA-256
  `90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`.

Focused checks passed:

- GachaRoom exposure-owner verifier: `PASS`;
- exposure/delta ownership audit: `PASS` after refreshing only its ignored
  expected hash for the current `HGCompatRenderPipeline.cs`
  (`F45851B8F682CF5FB81E7D4530E05844CCFFD18BFECFEA03A232B120E8599113`);
- Gacha post/DXBC audit: 52/52 checks passed, including the isolated forced-
  D3D12 13-frame capture. No production source was changed by the hash refresh.

Current generated evidence hashes:

- GachaRoom route JSON:
  `3A74B1BAD97415D240404B6AB90804F7E02AA41A1676B4950DA741F6FF933B7E`;
- post/DXBC audit report:
  `822E46BB1607FCC1E8226F7930366F877998530CE6B5A3B725B72D2BB3C80448`;
- exposure/delta ownership JSON:
  `393A320FAB4BCE1BB8FFAF8ED8FB237B0A014B08F4AB1F0273786E4EA407D85D`;
- `_ExposureWithMiscParams` report:
  `B2F51974EC5D891BF0B2AFC81A737683EA2BB29230AEF9CAC0C5A3F46F8F9B69`.

## Camera and exposure owner

The active environment owner is `Env_gachaRoom_01` (`HGEnvironmentPhase`),
with Manual exposure, target `1.0`, and serialized up/down rates `0.6`. The
adaptation belongs to the persistent physical main Camera managed by
`CameraManager`; the disabled Unity Camera on `CinemachineExternalCamera` is
only virtual transform/lens input. `CinemachineExternalCamera.InternalUpdateCameraState`
samples that virtual camera, `CinemachineBrain.PushStateToUnityCamera` applies
the chosen CameraState, and HGRP consumes the persistent physical camera.

Gacha entry does not construct/reset a fresh physical exposure state. Retail
adaptation is therefore exactly:

```text
E[n+1] = Lerp(E[n], 1, clamp(0.6 * Time.deltaTime[n], 0, 1))
```

The same scaled `Time.deltaTime` semantic (`UnityPlayer TimeManager+0xA8`)
feeds the selected Lightning904 particle system (`useUnscaledTime=false`,
`simulationSpeed=1`). The target, recurrence, clamp, and constructor identity
defaults are closed; the carry-in `E[0]`, presentation timestamps, discrete
delta sequence, and selected-frame multiplier are not present in offline game
data.

`HGCamera.UpdateShaderVariablesGlobalCB` publishes `_ExposureWithMiscParams`
at constant-buffer offset `0x1b0` as:

- x: `HGCamera.exposureAdaptation`;
- y: `1.0 / exposureAdaptation`;
- z: `finalRTSize.x / finalRTSize.y`, later overwritten by the scene updater;
- w: reciprocal of the camera field at object offset `+0x780`.

The adapted value is written by `UberPostPassUtils.AutoExposureUpdateData` back
to the same physical `HGCamera` after Manual zero-EV preparation.

## Post-processing order and Gacha profile

The native scene order is:

- Phase 1: DepthOfField → MotionBlur → conditional TransparentAfterDOF;
- Phase 2: ColorGrading/LUT → Bloom → AutoExposure → Uber composite.

The selected Gacha Bloom component is active at high quality with threshold
`0.95`, serialized intensity `0.5` (effective `0.41421356`), serialized
scatter `0.4` (effective `0.41`), and no separate character-Bloom control.
Vignette is inactive and the Gacha chromatic branch is explicitly disabled.
The selected tone-mapping mode is `ACES_modified` (mode `5`). The isolated
camera-local Gacha presentation selector applies this Bloom profile while
leaving generic CharInfo defaults unchanged; the 13-frame D3D12 capture proves
the selector and pass order, not retail pixel parity.

## Open boundary and recovery rule

AfterDOF remains gated by live `HGCamera.enableTransparentAfterDOF` and phase-1
state. Lower volume-stack ownership, physical-camera history at Gacha entry,
exact frame deltas, exposure carry-in, and final post-composite pixels remain
unresolved. Keep exposure neutral only as a constructor-backed startup value;
do not force a reset on Gacha activation, hard-code a selected-frame exposure,
or enable Vignette/AfterDOF from serialized absence alone.

Primary scratch evidence:

- `scratch/reverse_engineering/gacharoom_exposure/`;
- `scratch/reverse_engineering/zhuangfy_gacha_exposure_delta_ownership/`;
- `scratch/reverse_engineering/zhuangfy_gacha_post_dxbc/`;
- `scratch/reverse_engineering/exposure_misc_params/`.
