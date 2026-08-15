# Zhuang Fanyi Overview Animator-effect Unity binding

Date: 2026-08-15

The actor-specific Character Info owner is the serialized
`AnimatorBehaviourPlayEffect._effects[]` list on the Overview controller, not
an AnimationEvent and not the Gacha Timeline. The Unity lab now binds the four
exact Zhuang Fanyi records:

| effect | mount | delay / duration | Unity recovery |
|---|---|---:|---|
| `P_fxui_zhuangfy_ui_overview_start_01_piaodai` | actor root | `0 / 11.5 s` source lifetime | existing recovered animated actor prop |
| `P_fxui_zhuangfy_ui_overview_start_01_01` | actor root | `0 / 8 s` | exact generated particle prefab |
| `P_fxui_zhuangfy_ui_overview_start_01_baofa` | actor root | `6.1 / 3 s` | exact generated particle prefab; renderer gate remains fail-closed |
| `P_fxui_zhuangfy_ui_overview_start_01_finger_lightning` | `Bip001_R_Finger2Nub` | `4.4333334 / 2 s` | exact generated particle prefab |

`EndfieldRecoveredCharEffectSpawner` now preserves delayed creation,
duration-based cleanup, state-exit cancellation, and exact nested mount
resolution. A bare mount name must resolve to exactly one descendant; a path
must resolve exactly through `Transform.Find`; ambiguity fails closed.

`piaodai` is not forced through the particle contract because its source root
has no ParticleSystem and is already reconstructed as the actor-relative
`RecoveredProps/P_fxui_zhuangfy_ui_overview_start_01_piaodai` animation object.
The binding verifies that exact path instead of silently accepting an unbound
request. `trail01` and `jianqiang` remain absent because they are not in the
Overview controller behaviour list.

The maintained builder
`EndfieldZhuangfyOverviewEffectBindingBuilder.BuildAndValidate` verifies all
four request names, exact source marker schemas, effect-root identities,
durations, delays, the existing piaodai path, and uniqueness of the finger
mount. Unity batch validation passed with the four serialized bindings.

The separate runtime-admission verifier admits `_01` and
`finger_lightning`. It rejects `baofa` because the exact
`all/daoguang_light (1)` renderer (material PathID `6070151493152993176`,
serialized as little-endian bytes `98ef303a9f823d54`) still depends on
unrecovered `HGRP/Effect/VFXBaseV2` behavior. The owner, mount, delay, duration, particle,
renderer, mesh, material, and shader identity are therefore preserved, but the
visual is intentionally not spawned until that shader contract closes.
