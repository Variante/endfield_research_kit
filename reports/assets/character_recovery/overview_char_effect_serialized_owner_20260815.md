# Character Info shared `CharEffect` serialized owner (2026-08-15)

## Result

The common Character Info entry effect is source-closed to
`assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab`,
serialized file `CAB-45edfbd38d2a68534810c905ce39aff4`.
`PhaseCharInfo._PlayModelEffect` owns playback: it reparents
`sceneObject.view.charEffect` under `singleEffects/effect<height>`, resets the
local transform, activates the object, and calls `Play()` after the character
Animator has been force-updated.

This is a shared scene effect. It is not evidence that Gacha-owned effect
requests such as `baofa`, `piaodai`, or `finger_lightning` belong to Character
Info, and it does not account for the character-specific large effects visible
in the retail recording.

## Exact serialized hierarchy

| Object | PathID | Relevant components |
|---|---:|---|
| `CharEffect` GameObject | `803616490075416323` | Transform `6247092020272195331`; ParticleSystem `1486060241363822339`; disabled ParticleSystemRenderer `-112050695421729021` |
| `CharEffect/trail` GameObject | `3013782730707986179` | Transform `5011724371637462787`; ParticleSystem `8113670769548486403`; enabled ParticleSystemRenderer `5757248678484338435` |

The enabled child renderer is trail mode and uses:

- Material `M_UI_charChoose_12`, PathID `4388811075012960551`.
- Shader `HGRP/Effect/VFXRefract`, PathID `7766268189260370413`.
- Transparent custom render queue `3000` and keyword `_USE_RBOFFSET`.
- `_RefractTex` = `T_fx_mask_01_M`, PathID `-7046954404783675798`.

The exact texture is already decoded at
`export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/T_fx_mask_01_M_p9E34304E227EA66A.png`.

## Evidence boundary

The targeted AnimeStudio JSON extraction was bounded by exact AssetMap rows
from the source prefab's VFS blocks. It proves hierarchy, component, material,
shader, texture, and renderer-enable identities. It does not reproduce the
HGRP `VFXRefract` shader, prove Unity-lab pixel parity, or recover the separate
character-specific Overview effect consumers. Until that execution boundary
is closed, the lab must not substitute an approximate particle material and
claim the shared trail is recovered.

## Validation

- The hierarchy walker resolved the root and its sole child without missing
  local PPtrs.
- Unity 2022.3.62f3 batch compilation passed after adding the old-actor
  disable/cleanup lifecycle to `EndfieldOverviewPlayback`.
- The pinned native owner verification passes its binary hashes, while the
  full 31-controller audit is currently blocked because the active export no
  longer contains the former StreamingAssets AnimatorController JSON root;
  only ten Persistent overlay controllers are present. This is a missing
  evidence input, not a `transition_duration_fixed` code-schema regression.
