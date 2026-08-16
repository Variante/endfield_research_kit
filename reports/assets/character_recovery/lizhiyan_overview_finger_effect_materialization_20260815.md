# Li Zhiyan Overview finger-effect materialization

## Result

`P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub` is now materialized and
bound in the Unity recovery lab. It is the strongest current non-Zhuangfy
source-plus-video candidate because it has an exact standalone AssetMap prefab,
a unique serialized actor mount, and a hand-adjacent teal light/ribbon layer in
the retail recording near 40 seconds.

Focused AnimeStudio extraction closed:

- 8 GameObject/Transform nodes;
- 7 ParticleSystem/ParticleSystemRenderer pairs;
- 1 EffectSetting with non-looping `delay=0.83333`, `duration=2.33333`;
- 6 exact Material objects;
- 8 unique Texture2D PathIDs, all uniquely resolved through AssetMap with
  current converted PNG hashes;
- every material uses `HGRP/Effect/VFXBaseV2`, shader PathID
  `-1430105248647086886`, queue 3700.

The controller-owned `FromOveview` record declares 12 ordered requests. Unity
now serializes all 12 on Li Zhiyan's Overview playback, binds this effect at the
unique `Bip001_R_Finger2Nub`, and explicitly rejects the other 11 as unbound.

## Evidence boundary

All hierarchy, transform, particle/renderer payload, material payload, texture
identity, mount, and timing data are source-closed in
`lizhiyan_overview_finger_effect.json`. The recording's 38–47 second slot and
40-second identity frame provide a useful visual acceptance window, but do not
alone prove pixel ownership.

The six materials remain on the ColorMask-0 unavailable shader. Existing
VFXBaseV2 compatibility code does not yet prove this exact retail draw's PSO,
descriptor table, native BC/mip sampling, ForwardOnly dual-MRT attachments,
scene-depth handoff, or render-graph scheduling. No approximate teal ribbon was
introduced.

## Validation

Unity 2022.3.62f3 batch validation passed for:

- source contract import: 8 nodes, 7 particle pairs, 6 fail-closed materials;
- actor binding: 12 ordered requests, unique finger mount, one exact binding,
  11 explicitly unbound requests.

Wulfa's `bishou_wind3` remains the next ranked candidate, but it mixes recovered
VFXRefract and VFXBaseV2 families and currently has a weaker decoded component
closure than this Li Zhiyan effect.
