# Environment native publication: gated result

Date: 2026-08-15

Scope: read-only native audit for the selected `Env_gachaRoom_01` and
`CharInfo_Env` environment phases. This report records the narrowest
implementable field and the native boundary; it does not change lab code or
memory documentation.

## Exact gate

All native claims below use the same selected installed build:

- `GameAssembly.dll`, 280,436,712 bytes, SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`.
- `global-metadata.dat`, 62,925,560 bytes, SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`.
- Metadata version 29; 63,987 types, 494,830 methods, 311,628 fields.

The focused catalog and body mapping are disposable evidence in
`scratch/character_recovery/environment_native_publish/`.

## Source identities

The serialized phase identities are source-closed independently of native
execution:

| scene | phase | PathID | raw serialized SHA-256 |
|---|---|---:|---|
| GachaRoom | `Env_gachaRoom_01` | `6627355437943792087` | `cc84bc63c3f0c8da08559282f04df1cb2a2056a6427848dd35a3e5f4624d5bb7` |
| CharacterInfo | `CharInfo_Env` | `1201129019072041203` | `f9d1384c29f1e54599cd55e5f9c5c6d7eb9bd6f678d9fd104c7c329e6f1a66f9` |

Both authored holders are enabled global environment volumes at priority 600,
manual blend factor 1, and zero blend/fade distances. Their phase payloads
must not be merged: the direct light values differ, and Gacha's
`directIntensityDividePi` is exactly zero.

## Native facts

The selected metadata resolves these managed types in
`HG.RenderPipelines.Runtime.dll`:

- `HGEnvironmentPhase` has the serialized config fields
  `lightConfig`, `skyConfig`, `atmosphereConfig`, `fogConfig`,
  `heightFogConfig`, `volumetricFogConfig`, `colorGradingConfig`,
  `autoExposureConfig`, `shadowConfig`, and the remaining environment groups.
- `HGEnvironmentManager` owns active/sorted volumes, interpolated phase and
  volume-factor buffers, and the per-camera update path.
- `HGEnvironmentVolumeCameraComponent` owns the camera-local
  `m_interpolatedPhase`, volume list/factors, trigger position, and the
  `UseDirLightDataFromEnvDirectly(UnityEngine.Light)` query.

The exact mapped bodies are:

| method | VA | body scan bytes | body SHA-256 |
|---|---:|---:|---|
| `HGEnvironmentManager.PipelineUpdate` | `0x182edfc60` | 144 | not separately used for semantic claim |
| `HGEnvironmentManager._PipelineUpdate` | `0x182ee0f70` | 5440 | `b22214bdaa8915fc9502e19dd06ad06a03237da36c2bd141a911576254f79f4d` |
| `HGEnvironmentManager._InterpolateVolumesImpl` | `0x1832764a0` | 6688 | `8fb073da169993a60a9cf47b83708dc484ebf2d85b35b5c34f85d9e67ff265f8` |
| `HGEnvironmentPhase.AssignFrom` | `0x183636a20` | 4704 | `98ac52642ac6008b760129dcd7256f1cfcc1b04497eecfeb1bf3309a45ff099d` |
| `HGEnvironmentPhase.CopyFrom` | `0x1839bf590` | 6944 | `72eb2f8438d518b937bfe2b91d75153379cd0caaa407eb72f7a21f6741f837ec` |
| `HGEnvironmentPhase.Lerp` | `0x183a493b0` | 6176 | `a6ba7b63d6be2b2f2cfd6853318487282290fae8e5002230ae28c1a607de3380` |
| `HGEnvironmentVolumeCameraComponent.get_interpolatedPhase` | `0x1831064d0` | 96 | mapped getter |
| `HGEnvironmentVolumeCameraComponent.UseDirLightDataFromEnvDirectly` | `0x189ce39e4` | 148 | `98a0f11b83b694b8b71809953813880f609e62d7e9d739875a70a12d55caae1c` |

The direct native edge chain is closed as:

```text
HGEnvironmentManager.PipelineUpdate
  -> HGEnvironmentManager._PipelineUpdate
  -> HGEnvironmentManager._InterpolateVolumesImpl
  -> HGEnvironmentPhase.Lerp / CopyFrom / AssignFrom
  -> HGEnvironmentVolumeCameraComponent.m_interpolatedPhase
```

`_PipelineUpdate` obtains the camera component's interpolated phase and the
interpolation path writes the phase object. `HGEnvironmentPhase.ActivateAllEnvConfig`
also calls the `active` setters for `HGLightConfig`, `HGSkyConfig`,
`HGAutoExposureConfig`, and the other config groups. This proves phase/config
selection and copying, not GPU global publication of every leaf.

`UseDirLightDataFromEnvDirectly` calls `Light.GetSunSourceLight`, compares the
result with the supplied directional light, then consults
`get_useEnvVolumeInterpolatedPhase`. It does not read `lightConfig` fields and
does not write a shader global. Its native meaning is a boolean source-selection
gate, not a direct-light payload publisher.

## Narrow implementable field

The safest field to implement next is `directPitchYaw` (with selected direct
color/mode and temperature as the same carrier):

- Gacha `Env_gachaRoom_01`: pitch/yaw `(23.2, 137.4)`, direct color
  `(1, 0.82839394, 0.6482222, 1)`, color mode 0, temperature 4000,
  `directEV100=14.1`, `directIntensityDividePi=0`.
- CharacterInfo `CharInfo_Env`: pitch/yaw `(40, -181.6)`, white direct color,
  color mode 1, temperature 7000, `directEV100=13.5`,
  `directIntensityDividePi=2.7475471`.

The existing editor importer already reads these fields in
`EndfieldOriginalRenderParameterImporter.TryReadEnvironmentLight` (lines
286-313) and the runtime volume converts pitch/yaw into its main-light
direction before `ApplyGlobals` (`EndfieldHGRPCharacterLightingVolume.cs`,
lines 200-233 and 488-506). Therefore a scene-keyed phase snapshot can select
this field without inventing a native shader contract. Keep Gacha's zero
intensity-divide-pi disabled; do not substitute CharacterInfo's positive value.

## Classification

### Facts

- The selected build gate and hashes above are exact.
- Both phase identities, PathIDs, raw hashes, priority/blend metadata, and
  direct-light values are source-backed.
- Native registration/interpolation returns a camera-local phase object and
  copies/lerps its config groups.
- `UseDirLightDataFromEnvDirectly` is a source-selection boolean gate; it does
  not publish direct-light fields.
- The current lab has a direct-light consumer for pitch/yaw, color, mode,
  temperature, EV (diagnostic), and intensity-divide-pi.

### Inference

- `directPitchYaw` is the narrowest useful source-backed publication field:
  it can be selected by scene/phase identity and fed into the existing main
  light without claiming that the native phase body writes Unity shader
  globals.
- The native chain supports the existing `EndfieldRecoveredEnvironmentPhaseSnapshot`
  carrier model: phase selection is native-consistent, while lab publication
  remains an explicit compatibility consumer.

### Unclosed

- No gated evidence here maps `HGLightConfig` leaves to a final GPU global or
  proves the exact EV-to-lux/intensity conversion. Do not map `directEV100` to
  Unity light intensity.
- `HGAutoExposureConfig` is copied/activated by the phase path, but its final
  camera-history/exposure publisher is not closed here. Preserve exposure
  carry-in and adaptation state.
- Sky/SH, fog, volumetric, CSM, punctual shadows, and reflection PPtrs remain
  live-resource paths; serialized phase values alone do not justify publishing
  fabricated globals.

Verdict: **phase selection/interpolation is native-closed; directPitchYaw is
implementable through the existing source-backed carrier; native direct-light
payload publication and exposure GPU semantics remain intentionally
fail-closed.**
