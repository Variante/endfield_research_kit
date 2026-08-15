# Character Info Overview VFX owner: Animator/Effect runtime census

Date: 2026-08-15
Scope: fixed installed client, Character Info/Overview entry and character switch
Status: the generic Animator/Effect routes are mapped, and the actual Character Info actor-specific owner is now closed as serialized `AnimatorBehaviourPlayEffect._effects` entries. The shared `CharEffect` remains a separate common switch effect.

## Native gate

All native statements below use the same installed build:

- `GameAssembly.dll`: `D:\Program Files\Endfield Game\GameAssembly.dll`, SHA-256 `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`.
- `global-metadata.dat`: `D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat`, SHA-256 `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`.
- `CodeRegistration`: `0x18B9217D0`.

Evidence is the focused metadata catalog and body mapping in
`scratch/character_recovery/overview_effect_owner/effect_runtime_metadata_exact.json`
and
`scratch/character_recovery/overview_effect_owner/effect_native_body_targets.json`.
These scratch catalogs are build-specific evidence, not a portable method catalog.
The actor-controller PPtr joins and decoded `_effects[]` records are in
`scratch/character_recovery/overview_animator_controllers/controller_audit.json`
and the exported MonoBehaviour object index
`export_full/recovered/AnimeStudio-cli/StreamingAssets/object_index/parts/StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl`.

## What the Animator StateMachineBehaviour route actually does

The fixed-client bodies resolve the following generic lifecycle:

| Method | VA | Observed behavior |
|---|---:|---|
| `Beyond.Gameplay.AnimatorBehaviourPlayEffect.OnStateEnter` | `0x186B85E54` | Clears transition-finish effects, then calls `AnimatorBehaviourPlayEffectHelper.Add`; traverses an effect item and creates/plays the generic effect instance. |
| `Beyond.Gameplay.AnimatorBehaviourPlayEffect.OnStateExit` | `0x186B8644C` | Calls Helper.Remove, clears transition effects, and calls `EffectInstance.DestroyImmediate`. |
| `AnimatorBehaviourPlayEffectHelper.Add` | `0x186B859F4` | List/ownership bookkeeping for the `playEffect` item (`this + 0x28` and `playEffect + 0x18`). |
| `AnimatorBehaviourPlayEffectHelper.Remove` | `0x186B85D34` | Removes that bookkeeping entry and clears the item owner. |
| `AnimatorBehaviourPlayEffectHelper.ClearAll` | `0x186B85A94` | Dispatches to `AnimatorBehaviourPlayEffect.ClearAllEffects`. |

This is the serialized owner used by the Character Info actor controllers. The
Overview controller `m_StateMachineBehaviours` PPtrs resolve to the
`AnimatorBehaviourPlayEffect` MonoScript (`Beyond.Gameplay`,
Gameplay.Beyond.dll; script PathID `-395751038302444156`). Its serialized
`_effects[]` entries carry the authored effect key and mount point directly.

The fixed client has 31 catalog-enabled Overview controllers. Their resolved
state-behaviour records contain 165 decoded entries in this export; this is the
actor-specific producer census (some controllers have additional non-Overview
entries). The entries are effect-name/mount-point data, not color inference.

`CharInfoSwitchChar.Execute` is still not the effect constructor. It only
resolves `_charId` and publishes the global change event; the selected actor
controller's `AnimatorBehaviourPlayEffect.OnStateEnter/Exit` consumes the
authored `_effects` records while the Overview state is entered/exited.

`CharInfoSwitchChar.Execute` (`0x18764EA60`) only resolves `_charId` at `this +
0xD0`, reads `GUIDE_CHAR_INFO_CHANGE_CHAR`, and publishes the global event;
it does not instantiate a prefab or an effect.

## EffectSetting and EffectAnimation are generic consumers

The same exact-gate mapping gives:

- `EffectSetting.PlayEffect` (`0x1834FC4D0`) -> `EffectLodCfg.Play`
  (`0x1834FC5E0`) and `SetParticleSystemGrounded` (`0x187455300`).
- `EffectSetting.StopEffect` (`0x18339C0E0`) -> `EffectLodCfg.Stop`
  (`0x18339BE80`).
- `EffectAnimation.Play` (`0x1831DDA80`) -> `_CreatePlayableGraph`
  (`0x183437F90`), which builds a PlayableGraph/AnimationPlayableOutput/
  AdvancedAnimationMixerPlayable for effect animation clips.

These are valid runtime paths for prefabs that actually carry
`EffectSetting`, `EffectAnimation`, or an Animator state behaviour. A method
body mapping alone is not evidence that a Character Info actor uses one.

## Serialized Character Info boundary

The shared Character Info prefab is
`assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab`.
The exact serialized hierarchy in
`scratch/character_recovery/charinfo_generic_entry_effect/` is:

- root GameObject `CharEffect` (PathID `803616490075416323`), with one
  `ParticleSystem` and one disabled/null-material `ParticleSystemRenderer`;
- child `trail` (PathID `3013782730707986179`), with one `ParticleSystem` and
  one enabled `ParticleSystemRenderer`;
- the enabled renderer uses `M_UI_charChoose_12` (shader `VFXRefract`, queue
  3000) and the exact `T_fx_mask_01_M` mask.

There is no serialized `Animator`, `AnimatorBehaviourPlayEffect`,
`EffectSetting`, or `EffectAnimation` component in this `CharEffect` subtree.
Therefore the generic `EffectSetting`/`EffectAnimation` routes above cannot be
the owner of this shared Character Info entry effect. This is a serialized
negative, not a color-based inference. The actor-specific VFX are owned by the
separate actor AnimatorController state-behaviour records described above.

## Closed Zhuang Fanyi chain

The `chr_0030_zhuangfy` Overview controller has four decoded
`AnimatorBehaviourPlayEffect` effect records for its entry state:

Controller source: `export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController/AnimatorController#1012921_p4E9FDAF73497547E.json`.
The behavior object is PathID `9024023864256582782` in
`CAB-5e7f6f69295273549898b4a649673adb`; its raw serialized SHA-256 is
`a707e57cbbd5763cd6cf288d3188943054f91617ea112d68bad532d6baedbce3` and its
`m_Script` PPtr is `-395751038302444156` (`AnimatorBehaviourPlayEffect`).

| Authored `_effects[].effectName` | Mount point | Lifetime evidence |
|---|---|---|
| `P_fxui_zhuangfy_ui_overview_start_01_piaodai` | no mount string (root effect) | EffectSetting duration 11.5 s, delay 0 s |
| `P_fxui_zhuangfy_ui_overview_start_01_01` | no mount string (root effect) | EffectSetting duration 8 s, delay 0 s |
| `P_fxui_zhuangfy_ui_overview_start_01_baofa` | no mount string (root effect) | EffectSetting duration 3 s, delay 6.1 s |
| `P_fxui_zhuangfy_ui_overview_start_01_finger_lightning` | `Bip001_R_Finger2Nub` | EffectSetting duration 2 s, delay 4.4333334 s |

The effect keys resolve to the original prefab-side EffectSetting roots in
`scratch/character_recovery/zhuangfy_remaining_vfx/zhuangfy_remaining_vfx_report.json`:

- `P_fxui_zhuangfy_ui_overview_start_01_01` (19 ParticleSystems, 21 LOD
  entries);
- `P_fxui_zhuangfy_ui_overview_start_01_baofa` (19 ParticleSystems, 21 LOD
  entries);
- `P_fxui_zhuangfy_ui_overview_start_01_finger_lightning` (3 ParticleSystems,
  5 LOD entries);
- `P_fxui_zhuangfy_ui_overview_start_01_piaodai` (0 ParticleSystems; authored
  transform/animation effect, 44 LOD entries).

The same source report records the material/dependency closure data for the
seven Zhuang EffectSetting roots and the 16-track Timeline lifetime window:
entry control begins at 0 s; `baofa` begins at 5.483333 s; `finger_lightning`
at 3.95 s; the separate Entity-VFX dissolve/rarity tracks run through 14.033333
s. Thus the owner chain is now:

`Overview state entry -> AnimatorBehaviourPlayEffect._effects[] -> authored
effectName + mount point -> EffectSetting prefab root -> ParticleSystem /
Entity-VFX material graph -> EffectSetting delay/duration + Timeline control`.

The shared `CharEffect` trail is still the common switch flourish; it should not
be substituted for these actor-specific roots.

## Current owner boundary

The source-closed Character Info route remains:

`CharInfoSwitchChar.Execute` -> `GUIDE_CHAR_INFO_CHANGE_CHAR` ->
`PhaseCharInfo` selection/switch -> `_SwitchCharacterControllerState` (the
actor's Overview Animator parameters) and `_PlayModelEffect` (reparent the
shared `charEffect` under `singleEffects/effect<height>`, reset local transform,
activate, then call `Play()`).

The actor controllers prove the body entry/loop clips, the `FromIndex`,
`ToIndex`, `EnableSwitch` transition contract, and now the direct authored
effect keys/mount points. The large actor-specific teal/purple/ribbon/green
VFX can therefore be attributed to the serialized actor effect records when
their names/materials match; no owner is inferred from color.

## Next highest-value probe

For each remaining actor, enumerate the `PhaseCharInfo` model/prefab PPtrs and
all children mounted under the actor's `singleEffects/effect<height>` slots,
then resolve each child's serialized component type and lifetime trigger. The
Zhuang Fanyi slot is already closed through the controller effect records and
the source VFX report; the remaining gap is direct prefab PPtr identity for
each root in the retail mount graph:

`actor selection -> source prefab/PPtr -> mount path -> component or playable
trigger -> material/texture -> enable/stop lifetime`.

For the remaining actors, keep requiring the full chain:

`actor selection -> source prefab/PPtr -> mount path -> component or playable
trigger -> material/texture -> enable/stop lifetime`.
