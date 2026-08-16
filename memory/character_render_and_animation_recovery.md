# Character rendering and animation recovery

## Current status

The Unity lab is a source-backed reconstruction of Endfield character models
and Character Info presentation. It is useful for asset and shader research but
is not the retail renderer.

| Layer | Current status |
| --- | --- |
| Playable models | 31/31 imported and rendered |
| Canonical post-model identities | 156/156 have generated prefab paths |
| Static playable Overview assets | strong |
| Selected CharacterNPR equations | partial but source-backed |
| Complete HGRP/CharInfo frame | partial |
| Playable UI clips | complete for the selected `all-ui` scope |
| Runtime animation behavior | partial |
| Retail visual parity | not reached |

The canonical identities are 31 playables, one NPC character, one cutscene
clone, 94 enemies, and 29 ability/prop actors. Six modular ambient-NPC
archetypes are imported as labeled source kits rather than finished characters.

## What is recovered

- Playable post-models, LOD0 mesh bindings, materials, textures, cameras,
  profiles, lights, portraits, and Overview animation sources.
- Dependency-safe static prefab baselines for every canonical non-playable
  post-model identity.
- Current Persistent patch-layer roster/controller data alongside base
  StreamingAssets models. Liino validates that cross-layer boundary.
- Playable UI body and private item/deco clips for the selected scope.
- The Endfield 101-muscle Avatar contract and selected exact clip/Avatar paths.
- Narrow verified behaviors for blink, facial, and physical-transform fixtures.
- Selected CharacterNPR, eye, hair, shadow, material, particle, gacha, depth,
  GBuffer, light, cookie, and irradiance diagnostics.
- Fail-closed native texture payload recovery for the admitted playable set.
- Native ECS component slot 67 is now source-pinned as a 24-byte LOD/culling
  state record: `0x181038D00` tests high-mask bit 3, and its LOD jobs and list
  builders are bounded by direct xrefs. Its standalone native name remains
  unresolved; it must not be merged with managed `RenderObjectLODInfo` (ID 6)
  or `HGTreeComponent` (ID 80). See
  `reports/assets/character_recovery/native_component67_lod_renderer_list_boundary.md`.
- The managed HGTree renderer-list creation edge is pinned through the
  dedicated 729-entry HyperGryph internal-call table
  (`0x1820E6E90` names / `0x1820E8560` functions): indexes 564/565/566 map to
  wrappers `0x1801D9D10/0x1801D9F10/0x1801D9FA0`, which read the graphics
  context through `0x180FC5E60` at `context+0xC0` and call cores
  `0x18107EE40/0x18107FCF0/0x181080190`. The normal core builds
  context-owned renderer/resource records and reaches graphics-context vtable
  slot `+0xEA0` (`0x18107F13F`); fallback builders `0x18107E2E0` and
  `0x181080730` produce the result record and per-renderer arrays. This closes
  the native creation/resource-record boundary. The `+0xEA0` target is now
  resolved through the TLS graphics context: getter `0x180725DC0` uses TLS
  index `0x182111300`, backend setup `0x18072F3EB -> 0x180929430 ->
  0x1809258C0` writes vtable `0x181DCB360`, and setter `0x1807303B5 ->
  0x180727EA0` stores that context. Vtable `+0xEA0` is
  `0x1809324E0`, which records opcode `0x273B`; the normal/child/PreZ
  callbacks are `0x181060D90 -> 0x18107AD80`,
  `0x181060D20 -> 0x1810794D0`, and `0x181060D00 -> 0x181079320`.
  Interpreter table `0x1813BB574` maps `0x273B` to `0x1813B1110`, which
  invokes those callback records. Their 0x18-byte list items, 0x30-byte
  result records, and `+0x20` writeback are now bounded; the shared fallback
  builder reaches the internal renderer-resource pool
  (`0x180555A30/0x180555D30 -> 0x1805592B0 -> 0x1805582A0`, 0x80-byte nodes).
  The resource callbacks then call record builders (`0x18106BEF0` /
  `0x18106D020`) which install callback thunks `0x181060EA0` /
  `0x181060EB0`; those enter `0x18107AE60` / `0x18107B3A0`, obtain the TLS
  graphics context, walk renderer records, and invoke graphics-context vtable
  slots. The TLS getter returns the front-end `0x2A00` context (`0x181DCB360`),
  while the API-specific backend is stored at `context+0x2708`; the callback
  calls therefore enter front-end wrappers first. For API id `2`, the
  front-end `+0xDA0`/`+0x380` wrappers (`0x180931980`/`0x18092C320`) record
  `0x2734`/`0x27B6` when enabled and tail-dispatch to backend
  `+0xDA0`/`+0x380` (`0x18083E720`/`0x1808350E0`) otherwise. The backend
  vtable is `0x181DBC098`, whose resource/state methods include
  `0x1808539D0`, `0x180842370`, `0x180853A00`, `0x180854A30`,
  `0x180853F90`, `0x1808553B0`, and the `0x18083E720` resource-array builder.
  API id `4` uses vtable `0x181DCA338`, whose corresponding backend callback
  slots are deliberate no-ops (`0x180076890`). The resolved methods mutate
  backend resource/state records and counters but contain no direct graphics
  API or final draw call; keep this front-end/backend boundary separate from
  component 67 and the CommandBuffer validation route. A pinned direct-code
  xref census finds only
  `0x1805583B0` and the two retry
  sites in `0x1805592B0` calling the 0x80-byte node allocator; the population
  body contains only resource callbacks/allocator helpers, while the shared
   `0x180555D30` helper has 110 unrelated callers. Thus the remaining target is
   a later/runtime-indirect consumer of populated resource nodes, not another
   allocator ingress. On the concrete table-A `0x18107AB10` ingress, the pool
   tuple is now bounded as `0x180557650` (contained-object cleanup dispatcher)
   plus `0x180557750` (field setter), copied by `0x1805592B0` into node
   `+0x30..+0x40` and invoked by `0x1805598C0`; this path has no graphics,
   opcode, Vulkan, draw, or queue-submit operation. This does not classify
   unrelated producers of the shared pool. A separate positive producer edge
  is now bounded: `0x181080730` registers a pool record whose node callback
  is `0x181065190` or `0x181067A70`; pool worker sites reach
  `0x1805598C0`, which invokes that callback, and the callback builders
  `0x18106BEF0`/`0x18106D020` write `outResult+8` plus callback thunks
  `0x181060EA0`/`0x181060EB0`. The focused consumer pass shows that
  `0x180555D30 -> 0x1805573D0 -> 0x180559520 -> 0x1805592B0` is the 0x80-byte
  node allocation path; the node's `+0x30` callback is invoked by the pool
  worker, while no direct static read from the builder's `outResult+0x10`
  reaches `+0xDA8`, `+0xDE8`, `+0xF10`, Vulkan, or queue submission. This
  joins the shared pool to the resource-callback producers without claiming
  final HGTree draw ownership. See
  `reports/assets/character_recovery/hgtree_renderer_list_command_submission_boundary.md`.
  Separately, `DrawECSRendererList` is reached from
  `HGRendererListUtils.DrawTreeECSRendererList` (`0x189C0A130`) and has two
  parallel UnityPlayer internal-call implementations. The maintained
  UnityPlayer binding audit identifies table A as the global active array (its
  known `CullLights` entry maps to `0x1800FBCE0`); table B is the alternate
  duplicate. The active table-A body `0x180064580` preserves the renderer-list id and writes high-level
  opcode `0x55` through `0x1804C7930`; the high-level interpreter calls
  `0x18106AAE0`, whose context `+0xEA0` records low-level `0x273B`; the
  low-level interpreter entry `0x1813B1110` calls the parsed callback
  `0x181060D70 -> 0x18107AB10` directly. The adjacent API-2 `+0xEA8`
  (`0x18083F530`) belongs to the separate low-level `0x273C` case, not this
  HGTree `0x273B` edge. That callback is a resource/list lifetime boundary,
  not the front-end
  `+0xDA0` handler; `+0xDA0/+0x380` are reached by the separately installed
  resource callbacks `0x181060EA0/0x181060EB0 -> 0x18107AE60/0x18107B3A0`.
  The parallel table-B body `0x1801719B0` roots local managed-pointer state
  through slot `0x1821BE708` and calls `0x180A5C5C0` for payload/hash
  validation; it is not the complete tree writer. The final HGTree
  callback-to-`+0xDA8`/`+0xDE8` draw ownership remains fail-closed. Keep
  component 67 as LOD/list state rather than merging it with these handles.
  See
  `reports/assets/character_recovery/hgtree_renderer_list_command_submission_boundary.md`.

  Low-level dispatch indexing was rechecked: `0x1813BB574[0x273B-0x2711]`
  lands at `0x1813B1110`, whose case calls the parsed HGTree callback directly
  at `0x1813B12B0-0x1813B12B6`. API-2 `+0xEA8` (`0x18083F530`) is emitted by
  the adjacent `0x273C` case at `0x1813B12BB`, not by HGTree `0x273B`.
  A raw call-slot census also finds generic `+0xDE8`/`+0xF10` sites only
  outside the HGTree handler range `0x181060000-0x181081000`. Indirect draw,
  flush ordering, and queue-submit ownership therefore remain fail-closed
  after the direct callback.

  The async record identity is now bounded more tightly: `0x18107E2E0`'s
  `0x18107E9C0` family allocates a 0x30-byte item record at `item+0x10` and a
  separate 0x98-byte task descriptor at `item+8`; all inspected callers copy
  the returned pair to a record's `+0x20`, while workers write callback fields
  through task-context `+0x68`. The Windows x64 stack mapping now proves that
  task-context `+0x68` contains the same arg5 renderer record, and the worker
  writes its callback/result pair before the opcode-`0x55` fallback loads that
  record's `+8/+0x10` fields. The record identity is therefore closed;
  only its later indirect-draw/flush/queue ownership remains unresolved and
  fail-closed.

The corrected `0x273B` callback now has one more bounded negative edge:
`0x18107AB10` registers `0x1810865C0` and `0x1810685A0` as pool callbacks.
`0x1810865C0` only initializes/inserts a metadata object through
`0x18042C1B0`/`0x181074F10`. `0x1810685A0` is a chained-`.pdata` resource
worker through `0x1810694CC`; its direct calls are resource/registry and
bitset/format helpers, with only API-2 `+0xB0/+0xC0` interface calls. Those
targets (`0x180833470/0x180833630 -> 0x180822180/0x1808224F0`) are atomic
resource-handle operations, not command recording or Vulkan. Neither
callback reaches `+0xDA8`, `+0xDE8`, `+0xF10`, `+0xEA8`, a draw opcode, or
queue submission, so this concrete AB10-to-worker path is now classified as
resource/state lifetime only; the runtime record-to-final-draw consumer
remains unresolved and fail-closed.

The latest exact-slot census closes a potential false positive around
indirect draw: global `+0xDA8` sites are `0x180932245`, `0x1804D2A31`,
`0x1804D492C`, and low-level `0x1813B057F`. The `0x1813B057F` call is in a
neighboring low-level case; the `0x2734` dispatch target
(`0x1813BB574 -> 0x1813AFFF7`) reaches front `+0xDA0` at `0x1813B03DA`,
while HGTree's writer emits `0x273B`
(`0x1809324E0 -> 0x1813B1110 -> 0x181060D70`). The generic front-end
writers for `0x2734`/`0x2743` are `0x180931980`/`0x1809318F0`, and the
`+0xDA8` helper's recording twin writes `0x27B9`; no direct static HGTree
callsite reaches the `+0xDA8` sites. The high-level jump table maps opcode
`0x55` only to `0x1804CE4BD`, not the owners of the other `+0xDA8` sites.
Therefore indirect-draw, flush ordering, and queue ownership for HGTree
remain unresolved and fail-closed.

Generated mesh identity is source-scoped. Chen and Chenpast remain separate
model families with distinct containers, Animator identities, VFS sources, and
generated mesh GUID sets. Shared facial or animation bases do not merge their
mesh ownership.

Material identity is likewise PathID-scoped. Playable Chen has two exported
materials named `M_actor_chen_body_01`; renderer PathID must win over a
name-only lookup. The exact body material and hashed Texture2D fallback remove
the unrelated body texture that previously appeared across Chen's legs.
The canonical selectable viewer keeps only the active actor resident, centers
each newly selected root on the shared CharInfo stage, and chains a state
transition into its destination loop rather than leaving the transition pose
active.

The 4K/60 retail reference capture at
`videos/2026-08-15_10-32-32.mkv` bounds the shared Character Info selection
sequence across roughly 31 entries as previous-presentation clearing, actor
entrance, character-owned action/VFX, effect decay, and settled idle. The
recording is Character Info/Overview rather than the blue GachaRoom presentation.
Zhuang Fangyi's representative interval is `01:43.0-01:50.0`: horizontal
glitch/dissolve, white ribbon sweep and turn, green cube/orb plus orbiting trails,
then retained cube with frontal idle. Other entries range from strong teal or
purple-red weapon trails to body-only entrances and prop-dominant actions, so a
single global VFX substitute is contradicted by the capture. The resident
viewer now restarts each selected actor's exact generated Overview
`start -> transition -> loop` chain, including its recovered entry offset and
private item/deco bindings, instead of selecting an already-advanced resident
animation. Re-selecting the same active row does not restart it. This closes
the body/widget selection lifecycle only. A strict
`IEndfieldOverviewEffectSpawner` now exists for explicitly bound generated
particle prefabs, but the Dapan/Zhuang Fangyi request lists remain unbound
because their proven owners are not Character Info. The shared Character Info
effect uses its separate scene-owned path below. The physical `ExternalCamera`,
secondary-motion, and final rendered-frame ordering remain fail-closed.

The pinned native/Lua owner chain now closes the shared Character Info entry
route more tightly: `CharInfoSwitchChar.Execute` emits the GUIDE event,
`PhaseCharInfo.OnSelectCharChange` removes prior phase items and cancels
pending loads, the async replacement is created, and
`_SwitchCharacterControllerState(FromIndex, ToIndex, EnableSwitch)` drives the
body plus private-deco Animators before `ForceUpdateAnimator`. `_PlayModelEffect`
then reparents the scene-owned `charEffect` beneath
`singleEffects/effect<height>`, resets its local transform, activates it, and
calls `Play()`. This is a parameter-driven Animator route, not the Gacha
PlayableDirector route; the misspelled `FromOveview` state remains an
identity-bearing source fact. The viewer now also restores recovered Overview
parameters and finishes spawned entrance effects whenever an old resident actor
is disabled, matching the native remove/clear ownership boundary.

The exact serialized shared effect in
`assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab`
(`CAB-45edfbd38d2a68534810c905ce39aff4`) is a two-node hierarchy. Root
`CharEffect` GameObject PathID `803616490075416323` has a disabled renderer;
its sole child `trail` GameObject PathID `3013782730707986179` owns the enabled
ParticleSystem/renderer PathIDs `8113670769548486403` and
`5757248678484338435`. The renderer uses `M_UI_charChoose_12` PathID
`4388811075012960551`, shader `HGRP/Effect/VFXRefract`, queue 3000, and exact
texture `T_fx_mask_01_M` PathID `-7046954404783675798`. This closes ownership
and resource identity. The selected `HG_ENABLE_MV + _USE_RBOFFSET` fragment
(DXBC hash `f905de094d0261d5`) is now implemented in the existing Distortion MRT
shader as two SceneColor samples followed by the exact serialized channel-mask,
max, and `_RBIntensity` combine. The generated prefab replays both complete
ParticleSystem/renderer payloads; the root stays renderer-disabled with its
null material PPtr, while only `trail` binds the exact queue-3000 material and
texture. The shared Viewer reuses one scene-owned effect after the Overview
Animator restart, under the serialized `SingleEffects` transform
`position=(-0.3,0,0.05)`, `scale=(0.5,1,0.5)`. All four height buckets are
local identity, so the lab preserves their proven spatial result without
inventing a missing table height classification. Contract rebuild, Unity
import, serialized-payload verification, resource admission, runtime play, and
teardown all pass. Parsed shader `m_State` closes the formerly ambiguous
fixed-function ownership: Target0/Target1 color blend, ZTest, ZWrite, and Cull
are material-property-bound, while the alpha blend lanes remain fixed. The
converted ShaderLab's `Zero/Off` text is only a lossy default and must not
replace `_SrcBlend=5/_DstBlend=10`, `_MVSrcColorBlend=3/_MVDstColorBlend=6`,
`_ZTest=4`, `_ZWrite=0`, and `_CullMode=2`. `_VFXParams0` is source-closed to
player-center XYZ plus `fmod(Time.time,1024)` in W. A D3D12 pixel capture of
the final PSO, survivor list, physical aliases, and live descriptors remains
open, so this is executable source-closed structure, not yet pixel-parity
proof. The shared trail alone does not explain the character-specific layers;
their separate controller owner follows below.

An isolated Unity Direct3D12 replay now proves the generated shared trail is
actually draw-admitted: at `0.125 s` it has 3,572 survivors and changes both
the exact `B10G11R11_UFloatPack32` SceneColor and
`A2B10G10R10_UNormPack32` SceneMV attachments. The diagnostic records the
material state, descriptors, survivor rows, and GPU-readback hashes and labels
itself `unity_command_buffer_replay_not_retail_capture`. This closes Unity MRT
execution, not the retail camera's survivor list, RenderStateBlock override,
physical aliases, live globals, or presentation pixels.

A fresh isolated AnimeStudio broad load restored 1,269 StreamingAssets
AnimatorController JSON files without changing the production wrapper scope.
The audit again closes all 31 playable main Overview controllers, with four
fixed-duration and 27 normalized-duration handoffs plus 636 controller-proven
body/private-deco state compositions. The earlier audio-only event census was
not the actor-effect owner: controller `m_StateMachineBehaviours` resolve to
`Gameplay.Beyond.AnimatorBehaviourPlayEffect`, whose `_effects[]` directly
store `effectName + mountPoint`; 31 controllers contain 165 decoded records.
Its exact Enter/Exit helper owns creation, removal, and immediate teardown.
Zhuang Fangyi therefore has four source-owned Overview effects: `piaodai`,
`_01`, `baofa`, and `finger_lightning`, the last mounted uniquely at
`Bip001_R_Finger2Nub`. The lab now binds `piaodai` to its existing recovered
animated prop and serializes the three exact particle-prefab bindings with
their EffectSetting timing: `_01=0/8 s`, `baofa=6.1/3 s`, and
`finger_lightning=4.4333334/2 s`. `_01` and `finger_lightning` pass the
source-closed renderer gate; `baofa` remains deliberately non-executable
because its `all/daoguang_light (1)` renderer, material
`M_fx_ui_zhuangfy_lightning_901` PathID `6070151493152993176`, still lacks a
retail-equivalent `HGRP/Effect/VFXBaseV2` execution proof. Existing D3D12
same-input probes use a transient compatibility shader, force both admission
globals, and test nonzero coverage rather than retail pixel equality. The lab
now validates the exact sole fail-closed renderer/material/shader tuple so it
cannot silently drift or become admitted. This remains independent of the Gacha
Timeline owner even though the underlying effect assets are shared.

Across all 31 controllers, the 165 behaviour records contain 369 entries and
304 unique effect names. The MonoBehaviour object index repeats 223 unique
names/288 entries in controller scalar rows, which is not independent prefab
availability evidence; only exact AssetMap container/object rows can close
that boundary. Unity currently materializes only the three
standalone Zhuang Fangyi particle prefabs plus embedded `piaodai`. Of 228
non-root mounts, 217 resolve uniquely, 11 are ambiguous, and none are missing.
Last Rite's head effect now has an independently proven standalone AssetMap
prefab; Camille remains a controller-workload candidate rather than a proven
prefab batch. Li Zhiyan (`38-47 s`) and Wulfa (`48-55 s`) have the
strongest next retail-video acceptance joins, while Dapan (`283-296 s`) is the
low-VFX prop-animation regression target.

The video identity join now closes 27 of 28 stable visible slots against exact
localized names plus token-specific manifest/prefab evidence. In particular,
the previously unresolved Luoxi/Rossi slot is `chr_0028_wulfa`; only the video
label `伊玛` has no matching current CharacterTable/catalog actor and remains
unresolved. Endminm's missing facial Avatar was recovered as
`data_facemorph_avatar_endminm`, allowing its prefab to rebuild with 11 skinned
meshes, 410 transforms, and 24 clips. The full native verifier now passes all
31 actor prefabs, 4 fixed and 27 normalized handoffs, and 636 widget states.

A frame-indexed audit places the first clear Zhuang Fangyi presentation at
about video `102.8 s`; the preceding `102.5-102.7 s` corruption is a streaming/UI
transition and not VFX timing. Relative to that clear start, the white ribbon/
shard silhouette is strongest around `0.3-2.3 s` and rapidly leaves the main
outline by `2.3-2.8 s`; green hand/body-local energy persists around `0.3-3.1 s`,
with a later local flare around `5.2-5.9 s` decaying by roughly `6.0-6.7 s`.
The recording shows no defensible global exposure step. A full-video identity
index closes 27 of 28 stable slots, but no color, shape, or timing overlap is
promoted to an effect owner without the corresponding controller/prefab chain.
These intervals are retail visual acceptance bounds, not proof of particle
seed or exact presentation-frame lifetime.

The four Zhuang Fangyi request names still do not license wholesale reuse of
the GachaRoom Timeline: their Overview ownership comes specifically from the
controller behaviour records. `trail01` and `jianqiang` remain Gacha-only
because they are absent from that list. The Overview spawner now carries exact
source domain, binding, delay/duration, unique mount resolution, and teardown;
`piaodai` uses the already recovered animated actor prop rather than being
misrepresented as a particle prefab.

The Zhuang Fangyi gacha helper's multi-Director start protocol is now bounded
more tightly from plaintext Lua, serialized Director/Timeline rows, and the
pinned GameAssembly wrappers. Source order is `Actor`, `Audio`, `Effect`,
`Light`, `Others`. `SampleToBeginning` performs `Stop -> time=0 -> Evaluate`
for each role in that order. Delayed `PlayFromStart` first calls
`RebuildGraph` for every collected Director, then walks the same order again
for `time=0 -> Evaluate -> Play`. The zero-delay `TailTick` after each phase is
now closed from plaintext Lua: it ignores its delta argument, reads only the
Actor Director time, toggles the loop-track state at the authored loop start,
and fires one optional time callback exactly once. It has no camera, follower,
VFX, Timeline, or render-refresh work. The lab executes that state machine and
the two-pass protocol for the exact recovered
Actor and Effect PlayableAssets. The complete object index closes both Light
and Others as structural empty TimelineAssets: each has only its exact name and
editor preview setting, with no tracks, clips, or bindings. The lab therefore
admits source-identified empty Light/Others helpers without inventing payloads.
Audio is now recovered as the fifth helper Director. Its source Timeline PathID
is `6159943924586262679`: exact 2D seek-enabled events are
`Au_Gcaha_zhuangfy_overview` at `[0,5]` and
`Au_UI_Gacha_Chrshow_Light6` at `[7.75,10.1166666667]`; the serialized `Gcaha`
typo is identity-bearing. Neither clip stops its event at clip end. Exact Wwise
joins resolve them to media IDs `256896424` and `787269389` and verified decoded
FLACs of 9.688 s and 5.287292 s, so playback overlaps from 7.75 to 9.688 s under
zero-latency posting. The recovered Audio Playable remains silent during
`SampleToBeginning` through an explicit arm gate, then arms only after the
delayed `RebuildGraph -> time=0 -> Evaluate` pass and before `Play`; public Unity
evaluation state alone does not distinguish the source helper's silent zero
sample. Runtime Wwise onset/callback latency remains uncaptured, but Timeline
identity, timing, flags, event hashes, media, and local playback are source-closed.
Current-gated native bodies refine the lifetime: `OnBehaviourPlay` and
`PrepareFrame` only update required actions; `_DoPlayEvent` hashes the key and
reaches `AudioAdapter._PostEvent`, `_TrySeek` requires an existing playing ID,
and `OnGraphStop` calls `_TryStop` before an optional exit event. Thus a clip end
with `_stopEventAtClipEnd=false` does not stop playback, while stopping or
destroying the Audio graph does. The lab mirrors both edges and no longer lets
the second media continue beyond the Audio Timeline graph lifetime by default.
The individual native
`Stop`/`set_time`/`Evaluate`/`RebuildGraph`/`Play` wrappers contain no hidden
cross-Director or render-submit edge. Same-frame versus next-rendered-frame
visibility therefore remains a runtime-capture question. The disabled
`ExternalCamera` stays an animated Cinemachine data source; it is not promoted
to the physical viewer Camera, and its exposure/history is not reset by the
Director coordinator.

The empty Light Timeline is also a negative ownership result: gacha lighting
does not come from Timeline light curves. Installed Lua independently loads
`AdditionalLights/light_<charId>.prefab`, activates only `light_overview`,
initializes its follower components, loads `CameraTracks/track_<charId>.prefab`,
and applies only `VolumeModifiers/volume_overview` to the room override Volume.
The lab keeps one camera-local operator-light/HGRP publisher and does not create
a second Unity-Light population. For Zhuang Fangyi the known authored culling
input remains six `light_overview` rows plus eleven admitted rarity-6 room rows;
target-frame carry-in, full `LightCullResult`, and final publication remain
capture-only.

The light/Volume activation epoch is now source-bounded and executable in the
Zhuang Fangyi capture path. Lua instantiates the character prefab, constructs
the helper, then creates `AdditionalLights/light_<charId>` and activates only
`light_overview`; `InitLightFollower` runs once before the first
`SampleToBeginning`. It next creates `CameraTracks/track_<charId>`, activates
only `VolumeModifiers/volume_overview`, applies its modifier to the room Volume,
sets the gacha layer, and only then samples the Directors. Native evidence
separates initialization from motion: `InitCharLightFollower` stores the target
and enables its custom tick, while continuous fixed-offset/parent following
runs in `LateTick` after animation/Timeline sampling. Pinned native evidence
plus the recovered HGRP source closes `UseDataOnVolume` as a call-time snapshot:
it resolves the destination Volume's instantiated profile, obtains its
`HGCharacterVolume`, and copies value plus `overrideState` for exactly 30
`CharLightVolumeData` lighting parameters. It stores no destination reference
and has no Update/Tick path;
the modifier's half-second tween duration is separate state, not proof of a live
binding. Current generated capture data preserves both serialized modifier
parameters and the post-call destination snapshot. The authored gacha stack has
two global, enabled, weight-one layers: `GachaRoom_Volume` at priority 30000 and
`charOverrideVolume` at priority 30001. The room profile actively overrides 14
of the 30 character-light fields; notably it sets `charIgnoreSceneEnv=true`,
where the older Character Info profile differs. `UseDataOnVolume` copies all 30
actor value/state pairs into the instantiated priority-30001 profile, but the
Volume manager contributes only fields whose resulting `overrideState` is true.
An inactive actor field is therefore a no-op at priority 30001 and falls through
to the priority-30000 room value when active there, then to a lower world/phase
Volume or the constructor default. The generator records both source layers,
models the exact assignment, composes only active overrides, and rejects missing
or extra modifier fields. The lab keeps the 30 raw value/state pairs as evidence
and resolves the two known authored layers once at gacha `Begin`, before
`SampleToBeginning`; it preserves lower-stack inputs for fields inactive in both
layers, and delayed play or per-frame publishing does not replay the modifier.
The lower environment registry is now bounded for both presentation scenes.
GachaRoom registers one enabled global `HGEnvironmentVolume` at priority 600,
manual factor 1, zero distance/fade, selecting the fully serialized
`Env_gachaRoom_01` phase (PathID `6627355437943792087`); a priority-200 migrated
row has a null phase and is not an additional environment. Character Info uses
the same priority-600 registration shape but selects the distinct `CharInfo_Env`
phase (PathID `1201129019072041203`). Current-gated native flow is
`Register/_Register -> CompareTo` and
`PipelineUpdate -> _InterpolateVolumesImpl -> HGEnvironmentPhase.Lerp/CopyFrom`,
with camera-local interpolated phase, volume list/factors, and trigger position.
The exact same-priority tie break, active-list mutation order, override trigger,
and streamed phase replacement timing remain open; do not substitute one scene's
phase for the other.

The generated Gacha runtime now carries this selection in
`EndfieldRecoveredEnvironmentPhaseSnapshot`. It records the priority-600 holder,
phase identity/hash, direct-light, indirect-factor, and exposure fields without
publishing the entire phase as shader globals. This preserves two important
fail-closed differences: Gacha `directIntensityDividePi=0` cannot reuse
Character Info's `2.7475471`, and Gacha indirect factors `(1,1)` cannot silently
replace Character Info's `(.28772247,.28772247)`. Sky/SH, fog, volumetrics, CSM,
and punctual-shadow publication still require individual consumer evidence.
The capture camera now owns an explicit phase reference and a hash-gated
consumer. It applies the selected color mode, color/temperature, and the existing
pitch/yaw-to-direction transform to the scene main light while leaving Unity
light intensity neutral; it also disables the recovered source-main descriptor
for Gacha's zero divide-pi value instead of retaining the Character Info
descriptor. Native `UseDirLightDataFromEnvDirectly` is only a light-source
selection gate and does not justify EV-to-lux conversion or broad shader-global
publication. A standalone D3D12 capture after this correction passes all 13
canonical frames: every frame is non-black, all hashes are distinct across 13
samples, the source camera remains disabled, all 752 runtime scope objects retain
Gacha layer 30, and four fail-closed material identities remain unchanged. The
result is visibly recognizable and includes the early ribbon/cube composition,
but the lab's blue isolated backdrop and current camera/pose composition still
differ materially from the retail Character Info recording; this is evidence of
working transport, not parity.

On character switch, Lua detaches UI, clears timers, removes the TailTick owner,
nils the helper, destroys the old character root, and creates the replacement on
a later timer/coroutine. There is no same rendered frame containing both actor
roots. The shared priority-30001 profile can retain the old snapshot until the
new character calls `UseDataOnVolume`, but that is retained data rather than a
second Volume stack. A same-update old `LateTick` immediately before destruction
remains a narrow scheduling boundary; it cannot produce a rendered dual actor.
The lab capture now starts with its
single operator-light publisher and character Volume gated closed, opens them
immediately before `SampleToBeginning`, and closes the runtime-owned publication
idempotently on failure, disable, destroy, or explicit end. Closing restores the
Volume component's pre-bind enabled state, publishes zero operator-light count/
cluster/binning state, and does not touch exposure history or create a second
Unity Light population.

The native `HGRenderPath` slot roles are now corrected from the installed
UnityPlayer registration: wrapper `+0x8` is the BeforeCulling setup
(`0x1812fdb20` → `0x1813022d0`), `+0x10` is the Render forwarding wrapper
(`0x1812fdd80` → `0x1813018c0` → `0x1813042d0`), and `+0x18` is Destroy
(`0x1812fddc0` → `0x181300ab0`). The bounded BeforeCulling/Render bodies still
show no factory staging, CommandBuffer/Compute upload, or kernel-7 edge; the
factory-record-to-`_UploadBuffer` link remains fail-closed.

The follow-up RenderGraph census separates the shared graphics-context
dispatch slot `+0xab8` (used by the immediate ComputeShader helper family)
from the HGRenderPath graph-record lifecycle slots `+0xcd0`, `+0xea0`, and
`+0xeb0`. The checked Render, helper, and graph-state bodies contain no
`+0xab8` call and no direct factory staging or GPUDriven dispatch target, so
the factory-record-to-`UploadPerDrawParams` kernel-7 edge remains unproven.
The complete UnityPlayer `+0xab8` census has ten sites: fixed kernel `1`
resource passes, dynamic generic helpers, and one command-stream interpreter;
none statically identifies kernel `7` or binds factory channel-2 `+0xd0`, so
the dynamic command/resource record remains the only open bridge.
The current GameAssembly PData-scoped dispatch census finds 110 direct
`CommandBuffer.Internal_DispatchCompute` calls from 37 named built-in render
passes, with no `factory`, `perdraw`, `upload`, or character producer; the only
direct `ComputeShader.Dispatch` caller is unrelated MagicaCloth physics code.
This closes the direct managed dispatch candidates, while leaving the native
command-stream record feeding the generic interpreter open and fail-closed.
The native Unity CommandBuffer layer is now separated from that low-level
interpreter: the recovered internal-call table maps
`CommandBuffer.Internal_DispatchCompute` to `0x180119fc0`, which calls
`0x1804c73e0` to record opcode `0x11`; buffer binding maps to
`0x180116180` and `0x1804cb1a0`, which records opcode `0x0d`. A separate
GameAssembly census found 47 direct compute-buffer binding calls from eight
named bodies and 35 texture-binding calls; they are built-in passes or
CommandBuffer overload wrappers, with no factory/per-draw/character hits.
The consumer is now bounded by the complete UnityPlayer internal-call table.
`ScriptableRenderContext.ExecuteCommandBuffer_Internal_Injected` is table
index `3645` -> `0x1800b6f40`, which reaches `0x18052d730` -> `0x1804cdf70`
-> the high-level opcode interpreter `0x1804ce0a0`. Opcode `0x11`
(`0x1804cf455`) resolves its
resource handle and calls `0x1805e7a10`, which reaches graphics-context slot
`+0xab8` at `0x1805e7a8b`; its indirect-dispatch branch calls
`0x1805e7bc0` -> slot `+0xab0`. Opcode `0x0d` (`0x1804cf350`) resolves the
same record kind and calls `0x1805f84a0` for resource-state binding, with no
direct `+0xab8` or low-level `0x27ef` call. Thus high-level records do reach
the generic immediate-compute sink, but remain a separate stream from the
native `0x27ef` record, and neither path identifies the factory channel-2 /
kernel-7 upload producer. The same table maps `Graphics::ExecuteCommandBuffer`
at index `924` to `0x18005c0d0`; its inspected body resolves resource/object
handles but has no direct interpreter edge. `Submit_Internal_Injected` is index
`3636` -> `0x1800b4a40` -> `0x1805385a0` -> `0x18052e0b0`; the submit body
iterates command records and contains a direct `0x1804cdf70` call for one
record kind, making it a separate flush/submit candidate rather than proof of
the API-2 draw owner. The async/no-copy entries resolve to distinct helpers
(`0x18052d8f0`, `0x18052db50`, and `0x18052da20`) and must not be collapsed
into the old state-only attribution.
The Submit record loop is now decoded: `0x18052e0b0` reads a 16-byte record
array at `context+0x10030`, dispatches its type through the table at
`0x18052f25c`, and maps type `2` to `0x18052e869` and type `3` to
`0x18052e8f7`. Both cases load the deferred command-buffer pointer from
`context+0x10128[index]` and call `0x1804cdf70` (type 3 supplies the buffer's
`+0x170` mode field). The helpers `0x18052d730`/`0x18052db50` enqueue type 2,
while `0x18052d8f0`/`0x18052da20` enqueue type 3. Thus `Submit` is a concrete
deferred consumer of the same high-level command buffer that table-A
`0x180064580 -> 0x1804c7930` writes; opcode `0x55` can reach the known HGTree
callback there, and opcode `0x6A` can reach generic API-2 `+0xF10`. This still
does not statically connect HGTree's callback-produced records to `+0xDE8`,
`+0xF10`, or the final queue owner.
An expanded UnityPlayer direct-call census covers the two high-level writers:
`0x1804cb1a0` (opcode `0x0d`) has 58 direct callsites in 20 PData bodies and
`0x1804c73e0` (opcode `0x11`) has 42 callsites in 18 bodies, 27 unique bodies
in the union. The bounded caller set has no direct call to the factory
`0x8c`/`0x100` staging functions, the custom-resource resolver
`0x1804255f0`, or the immediate dispatch helpers; the only known
factory-adjacent bodies are the already-separated generic GPUDriven V1/V2
binders (`0x1810eece0`, `0x1810fb5a0`). This closes the direct native writer
surface as a factory producer while leaving virtual/table-dispatched callers
and the channel-2 resource upload edge fail-closed.
The native command-stream pair is now bounded for one dispatch opcode: writer
`0x18092bed0..0x18092c123` stores opcode `0x27ef`, a resource/handle qword, and
three 32-bit dispatch values (`0x18092bf54`, `0x18092bfb6`, `0x18092c00a`,
`0x18092c05d`, `0x18092c0aa`). Interpreter case `0x27ef` begins at
`0x1813b805b`, consumes the same four-field shape, and reaches graphics
context slot `+0xab8` at `0x1813b819f`; the writer also has an immediate
fallback at `0x18092c10e`. This closes the generic native command-record
boundary, but the record is not tied to factory channel-2/resource `+0xd0` or
`UploadPerDrawParams` kernel 7, so the character upload edge remains
fail-closed.

The managed compute-shader surface is now separately bounded. In the installed
GameAssembly, `ComputeShader.Internal_HGSetBuffer` (`0x18b3d75bc`) has exactly
two direct callsites, both inside
`MagicaCloth.PhysicsManagerMeshData::DispatchWriting[431943]`; that body also
dispatches at `0x18b3d74a8` and sources its buffer IDs from MagicaCloth state.
`ComputeShader.HGSetBuffer` (`0x18b3d75ac`) and the raw
`Internal_SetBuffer`/`Internal_SetGraphicsBuffer` wrappers have no direct
callsite. The GPU-scene setup wrapper (`0x1839454d0` -> UnityPlayer
`0x1801ee4c0`) therefore has no static managed `ComputeBuffer`/`Dispatch` edge;
its remaining resource/context bridge is runtime-indirect. Do not promote the
MagicaCloth binding path to the character upload route. Details are in
`reports/assets/character_recovery/gpu_scene_compute_buffer_callsite_census.md`.

The shared context path now has a more precise CPU-side boundary: accessor
`0x180fc5e60` obtains slot `0x14`; its companion helper `0x180fc5ec0`
obtains that context, runs `0x1810d36b0` on `context+0x110`, and then forwards
`context+0x200` to `0x180e75000`. `0x1810d36b0` walks
`this+0x38 + index*0x8c`, checks `record+0x74`, and routes active entries
through `0x1810d4020 -> 0x1810d8d40 -> 0x1810ccd20`, where persistent resource
records are cloned/copied. This is adjacent to the persistent per-draw sink,
and the alias is now closed: `0x1810d8c30` calls the same context helper and
returns `[context+0x110]` for the `HGFactoryRenderManager.SetEntitySharedData*`
wrappers. Thus this is a confirmed factory `0x8c` record to persistent
resource-maintenance edge, not merely a matching layout. No GPU API or
dispatch is present in the chain, so retain only the persistent-resource to
GPU-upload edge as runtime-indirect. `HGRenderPath` BeforeCulling and the
GPUDriven binders do share the same global context `+0xe8` selector path
(`0x1810e6310`), but their checked bodies do not read global `context+0x110`;
that common resource origin does not merge the factory CPU records into the
GPU upload surface. The V1/V2 distinction is now bounded too: V1 selects
`context+0xe8` entry 0, V2 selects entry 1; V2 rendering emits opcode `0x0d`
through `0x1804cb1a0` from runtime descriptor fields through `+0xd0`, while
V1/V2 dispatch reaches graphics-context vtable slot `+0xab0`. Those runtime
descriptor fields are not the factory channel-2 `+0xd0` without a proven
alias. V1's command formats are separately bounded: rendering records opcode
`0x2b` through `0x1804cb730` after `0x180fd96c0` resource-index mapping, while
culling records opcode `0x57` through `0x1804cd7d0`; both remain runtime
resource paths without a factory-record load. Details are in
`reports/assets/character_recovery/gpu_scene_native_icall_split.md`.

The literal `0x100` record in the GPUDriven V2 renderer-list path is now
separated from the factory staging scratch as well. The installed internal-call
table maps `GPUDrivenRendererV2::CreateRendererList` and
`CreateRendererListWithPreZ` to wrappers `0x1801e9680/0x1801e9770`, which call
`0x1810fd1b0/0x1810fd7d0` after selecting V2 runtime resources through
`0x1810fe120`. Those bodies read V2-owned descriptors from `object+0x50`, and
`0x18041ed50` fills a CPU renderer-list record with runtime descriptor lanes
`+0xc0..+0xf0`; the command path reaches vtable `+0xea0` and opcode `0x273b`.
No factory `manager+0x38 + index*0x8c` record, `_UploadBuffer`/84-byte pack, or
`UploadPerDrawParams` kernel-7 edge appears. Keep this genuine `0x100` record
separate from both the callback-local factory scratch and the unresolved
channel-2 upload resource. Details are in
`reports/assets/character_recovery/gpudriven_v2_renderer_list_descriptor_boundary.md`.

The only direct UnityPlayer caller of the factory-linked persistent-resource
copy `0x1810d8d40` is now bounded at `0x1810d3f27`. It runs from the frame-step
resource loop, resolves active `0x8c` entries through `0x1810d4020`, immediately
passes the returned pair to `0x1810c7a30`, and recycles the companion arrays.
`0x1810d8d40` itself only copies descriptor metadata and a 0x100-byte CPU block;
it has no graphics-context dispatch, command opcode, ComputeBuffer, or kernel
selection. This is a resource-maintenance/reclamation consumer, not the missing
84-byte `_UploadBuffer`/kernel-7 producer. Keep the persistent-resource-to-GPU
upload edge fail-closed; details are in
`reports/assets/character_recovery/factory_resource_maintenance_consumer_boundary.md`.

The UnityPlayer internal-call/native upstream boundary is also closed for the
known GPUDriven route: V2 `PopulatePerFrameData` wrapper `0x1801e98f0` calls
`0x1810ff600`, with upstreams `0x18127c730` and `0x181280530` selecting V1/V2
branches and passing `xor r9d,r9d` into their dispatch helpers. The checked
route therefore selects GPUDriven kernel 0; it does not load factory `0x8c`
records, pack `_UploadBuffer`'s 84-byte payload, or select `UploadPerDrawParams`
kernel 7. This is a negative producer result, not a channel-2 binding proof;
the resource-to-descriptor upload edge remains fail-closed. Details are in
`reports/assets/character_recovery/gpudriven_native_upstream_kernel_zero_boundary.md`.

The indirect GPUDriven tail is now resolved for the installed graphics-context
constructor. `0x180725dc0` reads TLS index `0x182111300` and resolves the
context through `TlsGetValue` (`0x181cb0980`); setter `0x180727ea0` stores the
same pointer and calls `TlsSetValue` (`0x181cb0970`) during backend/device
initialization at `0x1807303b5`. The normal `0x180929430` path allocates a
`0x2a00`-byte context through `0x1809258c0`, writes vtable `0x181dcb360`, and
thus resolves vtable `+0xea0` to `0x1809324e0` and `+0x850` to `0x180934850`.
The former emits command-stream opcode `0x273b` through the context's
`+0x2720` arena; the latter emits opcode `0x2798` and updates `+0x29bc`.
Context binding `0x180939c80` stores backend state and capabilities but does
not load factory `context+0x110` or `manager+0x38 + index*0x8c` records. The
static TLS command tail is therefore recovered, while the factory-record to
GPU-upload edge remains fail-closed; backend-state `0/5` construction remains
an explicit alternate branch.

The command-stream tail now has an interpreter-side mapping as well.
`0x1813aee90..0x1813bb9bc` dispatches the `0x2711..0x2822` opcode range through
`0x1813bb574`; `0x273b` lands at `0x1813b1110`, `0x2798` at `0x1813b55ea`,
and `0x27ef` at `0x1813b805b`. The V1 culling `0x273b` record carries the
`0x1810e6450` E9 trampoline targeting `0x18115d810`; the internal-call table
shows that the shared `context+0x190` object is `HGGpuClothManagerV2`, with
setup/cleanup and clear/upload/render-data wrappers at `0x1801ed2b0..0x1801ed770`.
The target obtains that object and calls `0x1810e3b40`, which allocates/reuses
cloth buffer records through `0x1810e1ea0` and copies 0x80-byte rows via
`0x1810e0a30`. These bodies still never load the factory `context+0x110` or
`manager+0x38 + index*0x8c` records. The result is a bounded GPU-cloth
resource/cache tail, not evidence for the character per-draw or
`UploadPerDrawParams` bridge; the factory-to-character-upload alias remains
unresolved.

The generic `HGConstantBufferPool` upload candidate is now source-closed as a
false positive. `HGConstantBufferPool::.ctor` (`0x189b6aa28`) creates a
`count=0x80000`, byte-stride-1, type-8 `ComputeBuffer` at `this+0x10`, while
`ApplyPendingUpload` (`0x189b6a7c0`) only walks metadata-backed
`Segment(offset,size,data)` rows and calls `ComputeBuffer.SetData<byte>` at
`0x187af05e0`. The image-wide census finds no direct caller of
`ApplyPendingUpload` and no factory, `_UploadBuffer`, `UploadPerDrawParams`,
dispatch, or resource `+0xd0` edge in its body. It therefore cannot supply the
missing 84-byte factory upload; details are in
`reports/assets/character_recovery/gpu_scene_constant_buffer_pool_contract.md`.

The native `_RTPerDrawParamsBuffer` property-name path is also source-closed
as a RayTracing false positive. UnityPlayer's property registry stores that ID
at registry `+0x130c`, adjacent to `_RTMaterialLevelBuffer` and
`_RTRAccelStruct`; the only direct field consumer copies these IDs into a
RayTracing resource object and initializes its metadata. The checked bodies
contain no factory `0x8c` record, `context+0x110`, `_UploadBuffer`, Compute/
CommandBuffer dispatch, or kernel-7 edge. Do not promote this property name
to evidence for character per-draw upload; details are in
`reports/assets/character_recovery/rt_perdraw_property_false_positive.md`.

The current protected `Gameplay.Beyond` IFix payload is now structurally
bounded beyond its 32 target signatures: its 330-entry external-method table
contains only factory LOD/quality references (`SetFactoryLodTier` and
`FacQuality.Apply`) plus unrelated dynamic-scene buffer helpers, with no
`ComputeShader`, `ComputeBuffer`, `CommandBuffer`, `GPUDriven`, per-draw,
`UploadPerDrawParams`, or dispatch API. The `0x7301`
`RemoteFactoryGameWorldController.FrameUpdateEntitiesJobForward` target is
also absent from this on-disk table. This strengthens the static negative but
does not expose runtime wrapper-array slots or another loaded patch payload;
the IFix route and factory-record-to-`_UploadBuffer` edge stay fail-closed.

The installed Burst AOT library now provides a positive CPU-side factory
record producer. Its resolver binds `SetEntitySharedDataPartial` to slot
`0x1803c4440`, `GetEntityDirtyFlags` to `0x1803c43f0`, and
`SetEntityDirtyFlags` to `0x1803c4420`. The per-entity range
`0x1801d0140..0x1801d045c` calls `0x1801cf3c0..0x1801d013c`, which writes
partial fields at offsets `0x50/0x1c/0x18/0x60/0x14` with sizes
`0x20/4/4/0x10/4`, then marks the entity dirty. The managed wrapper
`0x183d689c0` reaches UnityPlayer `0x1801eb9a0` -> `0x1810d91f0`, whose core
computes `manager+0x38 + index*0x8c + offset` and copies the requested bytes.
This closes a real Burst-to-native `0x8c` record update edge, but the Burst
image contains no ComputeBuffer/ComputeShader/CommandBuffer/GPUDriven/
UploadPerDraw/_UploadBuffer/Dispatch identity. It therefore remains CPU
record maintenance, not proof of the 84-byte pack or kernel-7/channel-2
upload; durable details are in
`reports/assets/character_recovery/burst_shared_data_producer_contract.md`.

The first native consumer after that dirty-record edge is now bounded as
well. UnityPlayer `0x1810d25c0..0x1810d3198` resolves each entity to the same
`0x8c` record, checks `record+0x70`, and copies `record+0x00..+0x40` as five
16-byte lanes into callback-local scratch at `entry*0x100 + 0xb0..+0xf0`.
This preserves the exact 80-byte shared per-draw payload width, but it is not
a persistent `0x100`-stride render staging allocation. The native internal-call
table separately maps factory full/partial setters to `0x1810d9170` and
`0x1810d91f0`, while GPU-driven buffer binders and `SetupGpuSceneUploadCs`
resolve runtime resource/context slots without a static factory-record edge.
The persistent `0x100`-to-`0x54` `_UploadBuffer` conversion, kernel-7 dispatch,
and channel-2 resource `+0xd0` binding therefore remain fail-closed. Keep the
numeric scratch `+0xd0` lane separate from the renderer resource's channel-2
`+0xd0`; details are in
`reports/assets/character_recovery/factory_record_to_100_staging_contract.md`
and `reports/assets/character_recovery/gpu_scene_native_icall_split.md`.

A bounded UnityPlayer follow-up found two genuine native near-matches,
`0x1812117ec..0x181211c02` and `0x1812145af..0x181214888`, that walk a
`0x54` source array while updating a separate `0x100`-stride record. They
preserve destination `+0x00..+0x30` into `+0x60..+0x90` and update
`+0x30..+0x38`; they do not read the factory manager `+0x38`/`0x8c` record,
the dirty byte at `+0x70`, or the confirmed staging lanes `+0xb0..+0xf0`, and
have no direct GPU upload or kernel-7 call. This proves the literal strides
coexist in other native layouts but does not identify the missing
factory-to-`_UploadBuffer` pack. Keep that edge fail-closed; evidence is in
`reports/assets/character_recovery/native_54_to_100_near_match_followup.md`.

The next `+0x100` census adds three sibling UnityPlayer variant writers,
`0x181758280`, `0x18175ba50`, and `0x181760960`, selected through the type
dispatcher at `0x181757f8a`. They walk an unrelated `0x220` source family and
emit CPU-side effect/record data; their apparent `+0xb0..+0xf0` fields are
local output, with no factory `0x8c` record, dirty test, upload, or kernel-7
edge. They are therefore additional false positives, not the missing
`0x100`-to-`0x54` pack. See
`reports/assets/character_recovery/native_100_stride_variant_followup.md`.

The exact native `0x54` helpers are now classified as a separate false-positive
family. `0x1800a5fe0`/`0x18067606c` copy five Vector4 lanes plus a trailing dword
for indexed `StatusSingleEffect`/VFX and generic container data; their callers
do not touch the factory `0x8c` record, `+0xb0..+0xf0` staging, or
`GpuSceneDirtyUpdateCS.UploadPerDrawParams`. The shader source also puts its
index dword first, so this is not the missing `_UploadBuffer` record. The
factory `0x100 -> 0x54` pack, kernel-7 dispatch, and channel-2/resource `+0xd0`
binding remain fail-closed. See
`reports/assets/character_recovery/native_84_helpers_status_vfx_followup.md`.

The factory staging consumer now has a positive indirect registration edge.
`0x1810d33a3` creates the per-factory job object and passes the exact callback
pointer `0x1810d25c0` at `0x1810d356f` into Unity's native scheduler
`0x180555e50`; `0x1805572f0 -> 0x180559240` packages and links that callback in
the worker descriptor. This closes the static “unreferenced callback” gap and
confirms the `0x8c -> 0x100` producer is job-driven. The scheduler has no GPU
upload/dispatch edge, so the later `0x100 -> 0x54` pack, kernel-7 selection, and
channel-2/resource `+0xd0` binding remain fail-closed. Details:
`reports/assets/character_recovery/factory_staging_job_callback_chain.md`.

The scheduler worker path is bounded through `0x180558440 -> 0x18055865f ->
0x1805598c0`, which loads and calls a queued task entry indirectly. The final
alias from that queued-slot field back to `0x1810d25c0` is not unique in the
static image, so this remains an execution boundary rather than a fully
resolved call. The scheduler still has no GPU upload/dispatch edge.

The generic Renderer custom-per-draw path now has a separate positive
persistent-resource sink. `Renderer.SetCustomPerDrawData_Injected`
(`0x183e6e280 -> 0x1800fe590`) reaches UnityPlayer `0x180430680`, which writes
five possible Vector4 lanes to the renderer cache and, when its resource gate
is open, resolves a persistent destination through `0x1804255f0` and stores at
`resolved+0xb0+index*0x10`. The resolver walks the global context's descriptor
array and `0x240`-stride resource records; this is not callback stack scratch.
Managed `SetPerDrawData_*` channel helpers are direct users of this bridge.
The factory dirty-record callback also calls the resolver at
`0x1810d2fc4/2fd9` and copies an `0x100`-byte CPU resource block across
`+0x00..+0xf0` in two `0x80`-byte Vector4 passes, but neither
path names `_RTPerDrawParamsBuffer`, `UploadPerDrawParams`, or kernel 7. Keep
this persistent CPU resource edge separate from the factory `+0x8c` record and
the callback-local `+0x100` scratch. Details:
`reports/assets/character_recovery/persistent_perdraw_resource_bridge.md`.

The callback's apparent `+0x100` destination is now downgraded from
render-side staging to callback-local scratch: `0x1810d25e7` sets the base to
`rbp-0x80`, `[rsp+0x68]` preserves it, and the five `+0xb0..+0xf0` lane stores
are consumed by internal CPU/VFX/resource helpers. The installed GameAssembly
write-side path is nevertheless concrete: `ApplyPerDrawRender$BurstManaged`
(`0x1869d8434`) -> `GlobalSharedData+PerDrawGlobalSetting.Apply`
(`0x1869d5d30`) -> `PerDrawConfig.Apply` (`0x1869f3654`) -> wrappers
`0x1840f30e0` (4-byte scalar) or `0x1876aaefc` (16-byte vector) ->
`HGFactoryRenderManager.SetEntitySharedDataPartial` (`0x183d689c0`). This
confirms a managed per-draw write into native shared-data records, not a GPU
upload, `_UploadBuffer` pack, or kernel-7 binding. Details:
`reports/assets/character_recovery/factory_record_to_100_staging_contract.md`.

The installed `HGRenderPathDefaultDeferred` route is now pinned at the GBuffer
attachment boundary. `GBufferPassConstructor.ConstructPass` submits
`SceneColor`, neutral-cleared `SceneMV`, `GBufferA/B/C`, and writable
`SceneDepth` in that order; the renderer-list uses LightMode `GBuffer` in the
opaque `CommonOpaque` queue, while render-graph load/store remains automatic.
`OnePassDeferred` independently preserves the same MRT order and adds
`PreDepth`/`GBuffer`/`Decal` subpasses. This closes the source-side five-MRT
contract needed by `HGRP/Lit` but not the physical `SceneColor` allocation or
the channel-2 resource-to-descriptor upload. Durable details and hashes are in
`reports/assets/character_recovery/gacha_room_gbuffer_rendergraph.md`.

The upstream SceneColor contract is now source-pinned as well. A targeted
AnimeStudio export restored the current `HGRenderPipelineAsset` object that
was missing from the stale generated export, and the three deterministic
SceneColor audits now rerun successfully. The selected
`HGRenderPathDefaultDeferred` route creates SceneColor in
`HGRenderPathScene.OnPreRendering` with format
`B10G11R11_UFloatPack32`, Point/Clamp sampling, the selected Gacha clear
`(0.025, 0.07, 0.19, 0)`, and 1x MSAA/`bindTextureMS=false`. The transient
logical handle is physically created/released at compiled first-write/last-use
boundaries through the descriptor-hash `RTHandle` pool; stale entries require
an 11-frame gap before purge. The initial handle is at `+0x12e0` and the
preserved history lane at `+0x1328`. Scene dimensions are target-relative and
evenized using the live persistent-camera viewport and
`video_rendering_scale_pc`, so exact pixels, active scale, native pointer, and
alias peer remain open. The current checker verdicts are producer
`PATCH_APPLIED_WITH_RUNTIME_BOUNDARY`, physical owner
`PHYSICAL_POLICY_CLOSED_IDENTITY_LIVE`, and live state
`MSAA_CLOSED_DIMENSIONS_TARGET_RELATIVE`; keep the remaining frame-identity
boundary in `reports/assets/character_recovery/gacha_scene_color_physical_lifetime.md`.

The shared SceneMV/motion boundary is now source-closed for the isolated
selected-character CharInfo/VFX scene. `HGRenderPathScene.OnPreRendering`
creates a transient full-resolution `A2B10G10R10_UNormPack32` SceneMV target at
`+0x1300` only when `HGCamera.enableMV` is true, clears it to
`(0.5,0.5,0,0)`, and uses it as GBuffer/ForwardOpaque attachment 1; it is
current-frame data, not a history texture. The native total order is now
verified as GBuffer → ForwardOpaque character target-1 writers → main
ForwardOnly → Distortion → Phase 1 (LightShaft/Parafin/DOF/MotionBlur) →
after-DOF ForwardOnly → LensFlare → optional pre-TAAU blur → Phase 2. Sixteen
Wulfa/Zhuang Fangyi skin, cloth, hair, and eye variants write packed motion to
`SV_Target1`; selected VFX must consume that populated attachment. Camera
previous constants and paired skin-matrix ranges are also source-pinned, while
terrain/foliage target-1 enumeration, physical skin-buffer reuse, and a
source-compatible lab MRT remain open. See
`reports/assets/character_recovery/gacha_scene_mv_motion_contract.md`.

The Gacha `baofa` Glow902 transparent writer is now executable through its own
source-closed queue-3005 SceneMV lane. The exact recovered owner is
`P_fxui_zhuangfy_ui_overview_start_01_baofa/all/glow (2)`, active under the
Gacha `baofa` Control window (`5.483333..9.4`); despite the prefab name, current
evidence does not make it an Overview owner. Its original
`HGRP/Effect/VFXBaseV2` material is premultiplied transparent (`One`,
`OneMinusSrcAlpha`), front-culled, depth-read-only, and writes SceneColor plus
SceneMV. Native order is main queue 3000, exact queue 3005, Distortion, then
post processing, so the lab keeps queue 3005 out of both the ordinary
transparent lane and after-post lane. A 13-frame D3D12 capture executed all
four requesting frames with no missed request; the manifest SHA-256 is
`8e71eb8119d960aad59a5d8a36039ab523d75dd45e4188c26fb2280dc5d20d9e`.
See `reports/assets/character_recovery/glow902_native_scene_mv_queue_20260815.md`
and `scratch/character_recovery/glow902_queue3005_capture/`.

The ordinary DefaultDeferred resolver boundary is now source-pinned. The
selected route is a five-MRT producer (`SceneColor`, `SceneMV`, `GBufferA/B/C`)
followed by a separate one-RT SceneColor resolver with read-only depth and
GBuffer A/B/C as ordinary `Texture2D` SRVs; the matched Vulkan payload has no
subpass image reads. Installed state enables screen-space shadow masking and
disables the OnePass subpass bit. UnityPlayer's native best-match loop then
selects the unique serialized pass-0 pair 96/97 (screen-shadow plus subpass)
for the missing ordinary variant. Its nine-CB/25-SRV/structured-buffer ABI
and static fallback values are mapped, while live light/bin, shadow/cookie,
VisibilitySH, irradiance, AO/SSR, camera, and remaining frame contents remain
open. The current standalone diagnostic is finite and binding-compatible only;
the maintained isolated-diagnostic validator now accepts its direct-runtime
`0/0/0` callback/swap mode after the current plugin hash and GBuffer-order token
were refreshed. This does not establish retail numeric fidelity or justify
enabling a lab draw.
See `reports/assets/character_recovery/gacha_deferred_resolver_framebuffer_contract.md`.

The Gacha final-color chain is now source-pinned through post processing.
`Env_gachaRoom_01` owns Manual exposure on the persistent physical main Camera,
while CinemachineExternalCamera supplies only virtual transform/lens state.
Native Phase 1 is DepthOfField → MotionBlur → conditional AfterDOF; Phase 2 is
ColorGrading/LUT → Bloom → AutoExposure → Uber. Gacha Bloom is high quality
with threshold `0.95`, effective intensity `0.41421356`, effective scatter
`0.41`; Vignette and chromatic aberration are explicitly inactive. Exposure
recurs as `E[n+1] = Lerp(E[n], 1, clamp(0.6*Time.deltaTime[n],0,1))`, and
`_ExposureWithMiscParams` publishes current exposure, reciprocal exposure,
target aspect, and the recovered reciprocal camera field. The camera-local
Gacha Bloom selector and exposure ownership probe are validated, but physical
camera carry-in, exact deltas, AfterDOF state, lower volume ownership, and
final pixels remain runtime history. Do not force a fresh exposure reset or
selected-frame multiplier. See
`reports/assets/character_recovery/gacha_postprocess_exposure_contract.md`.

The deferred environment-global publisher boundary is now also pinned. The
Gacha path has two exact closures: `_MultiscatteringLUT` is a fixed 32x32
`RHalf` payload (raw SHA `1A15AFE2…289F030E`) published by
`PreparePCMultiscattering`, and disabled ASM binds the default shadow texture.
V2 irradiance, volumetric scattering, cloud shadow, CSM, and punctual shadow
producer/fallback ownership and shader slots are mapped, but their live branch,
camera settings, atlas/voxel contents, and frame parameters remain open.
`RenderForwardTransparent` does not publish these globals, so M02 stays
fail-closed. See
`reports/assets/character_recovery/gacha_environment_global_publishers_contract.md`.

The Gacha light cull-view boundary is now source-pinned independently of that
missing pipeline-asset export. The installed fallback has
`useFallbackLightCulling=false`, zero occlusion dimensions, and the normal
native candidate core. Active `SceneLight6Rarity` rows initialize
`mask=1<<layer` and `flags=0x701`; Gacha layer 30 intersects the camera mask
`0x40010008`, so the generic flag/mask gate is closed for all twelve authored
rows. The native point-sphere top-plane branch guarantees `Spot Light (20)` is
absent (margin `81.4967041015625`), leaving an exact conditional order for the
other eleven and an authored maximum of 11. The native scheduled cull-view
predicate is now closed: ordinary cameras test candidate AABBs against six
normalized planes at view `+0x58/+0x5C`, while only camera type `0x80` selects
the alternate distance/extent predicate. The exact selected list still
depends on live plane values, candidate bounds, camera/cull-view state,
unrelated live lights, and the native 256-row input bound. The desktop settings
audit resolves
`PunctualLightMaxCount=256`, while native `HGCullingSystem.CullLights` already
receives `maxCount=256`, so the runtime settings cap adds no further
truncation. The regenerated checkers pass with current binary hashes; details
are in
`reports/assets/character_recovery/gacha_light_cull_survivor_contract.md`.

The selected-light result's downstream HGRP publication chain is now also
source-pinned. `UpdateLightCookieAtlas` precedes
`LightCulling.PrepareCPUData`, which embeds cookie indices; then
`LightCulling.SetupGlobalConstants` publishes the 32,864-byte
`_LightDataBuffer` and 48-byte `_LightBinningConstants`.
`LightCullingGPU.PrepareGPUData` and reflection clustering share one graph
binning buffer, and the Binning pass publishes it as `_GlobalBinningBuffer`.
M02 transparency only consumes these globals and does not rebuild them. The
desktop cookie atlas is persistent 4096x4096, while cookie slots/CB and light
constant buffers are rebuilt per frame. Exact selected rows, surviving cookie
membership, shadow/CSM, ASM, irradiance, reflection contents, and original
clustering kernels remain open; details and binding slots are in
`reports/assets/character_recovery/gacha_light_global_publication_contract.md`.

The HDPLS character-shadow resource route is now source-pinned. The current
Persistent IFix table has 32 records and matches neither HDPLS wrapper gate
`0x877` nor screen-resolve gate `0x890`, so the unpatched native route is the
current static path. Its reflected 3,568-byte layout is requested/bound as
`0xDE0` bytes; the selected consumer reads `uint4[56].y` at bytes 2560..3455.
Active requests create a transient D16 `4096x2048` (request-grid-scaled)
`_HDPLSTex` atlas, then a single-sample RGBA8 resolve publishes
`_HDPLSScreenSpaceShadowMask`; inactive frames reset selectors and bind white
textures. Atlas geometry, selector formulas, and publication/lifetime are
closed, but live character/light rows, atlas pixels, and resolved mask pixels
remain capture-only. See
`reports/assets/character_recovery/hdpls_character_shadow_resource_contract.md`.

V2 irradiance ownership is now source-pinned for the updated AnimeStudio
exporter and unchanged installed game binaries. The Gacha Lua
`Data/IrradianceVolume/PC/gacha/character` files feed the older
`HGIrradianceVolumeManager.CreateGachaIV` path; they do not own M02's six V2
clipmap globals. `HGIrradianceVolumeManagerV2.PipelineUpdateV2` renders the
underlying scene's `m_defaultIV`, while `m_gachaIV` only gates update-center.
The current Gacha room is a prefab overlay with no Scene object and no
room-owned V2 IV payload: the installed VFS has 224 IV files across 60 chunks,
83 current scene indexes, 12 legacy Gacha files, and zero room files. The six
V2 clipmap slots, texture formats/dimensions, shader-global order, and missing
map zero-texture fallback are closed; the selected scene index, streamed voxel
contents, transient atlas dimensions, and live frame parameters remain open.
Keep Gacha/M02 irradiance fail-closed and do not substitute legacy files or an
arbitrary scene index. See
`reports/assets/character_recovery/gacha_irradiance_scene_ownership_contract.md`.

The CharacterNPR OverlayShadow local-volume visibility path is now source-closed
for the isolated CharInfo/Character Overview route. The refreshed operator-light
export contains 31 exact rigs and 273 lights, including Liino's seven lights;
41 type-4 Fog rows (36 advanced, five convenience, ten directional) are
character-only and match the native NPR pack. The selected retail fragment and
decompile, `LightCharacterOnly`/NPR-type lanes, inverse
`charIgnoreSceneAdditionalLights` gate, 32-pixel XY/2048 one-unit-Z membership,
Fog attenuation, and neutral-zero fallback are hash-pinned. The regenerated
eye-shadow audit now covers 29 LOD0 renderers and 87 overlay materials, with
Liino's two shared eye-shadow materials corrected to queue 2900 and zero audit
failures. The refreshed current-data Texture2D census is now 897/897 resolved
objects with 1,541 generated copies, and the import contract includes Liino's
22 owned rows plus three Persistent item-widget rows. The Unity batch refresh
and full material/import verifier pass with zero descriptor drift. The exact
native compressed-payload contract now covers 215 objects / 420 generated PNG
owners / 444,635,856 logical bytes (213 unique payload files), including 22
manifest-gated Liino body/cloth/face/hair/iris/skill/item-widget rows; Jsspsi
and other unselected surfaces remain descriptor-only. This remains an isolated producer path: the arbitrary-gameplay
`HGCullingSystem.CullLights` candidate producer, live unrelated-light/shadow
state, and retail pixel parity are open. See
`reports/assets/character_recovery/character_overlay_shadow_visibility_contract.md`
and `reports/assets/character_recovery/liino_texture_import_contract.md`.

## Evidence boundary

Every production value must come from serialized data, installed native
behavior, or a validated runtime capture. Unknown values stay neutral,
diagnostic, or disabled.

Static prefab enumeration proves admitted geometry and hierarchy, not final
appearance or runtime activation. Shader decompilation proves a selected
program’s inputs/outputs and render state, not the active keyword variant or
frame schedule. A recovered clip does not prove controller transitions,
blending, IK, facial state, physics, or effect timing.

Do not enable generic Humanoid animation for enemies or props without
actor-specific source evidence. Do not treat filename similarity, shared
materials, or controller proximity as exact actor ownership.

## Main rendering gap

The missing work is the coupled retail frame contract:

- HGRP light scheduling, culling, cookies, and irradiance;
- character shadow atlases, screen shadows, stencil, and VisibilitySH;
- shared depth, GBuffer, motion, and deferred resolve;
- exact material variants, mip payloads, and live renderer state;
- exposure, history, post-processing, and final composition;
- retail-frame validation across representative characters.

Current images are recognizable but flatter than retail, especially around
faces, pale cloth/armor, hair, dark hardware, and contact shadows.

## Main animation gap

Remaining runtime systems include:

- controller transitions, interruption, blending, and root motion;
- broader exact Avatar/clip transport;
- grounding, foot IK, hand targets, and constraints;
- facial emotion, lip sync, gaze, look-at, and animation events;
- secondary motion, wind, cloth, hair, and dynamic bones;
- item/deco/FX lifecycle and gacha timing;
- non-playable rigs, controllers, animation, and VFX execution.

The non-playable baselines prove enumeration and admitted dependencies only.
Runtime modular assembly, VFX, material overrides, animation, and exact
keywords/passes/queues remain incomplete.

## Maintained workflows

```bat
cd unity_endfield_graph_shader_lab

.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
.\import_playable_characters_ui.bat
.\recover_playable_charinfo_profiles.bat
.\update_character_recovery_viewer.bat
.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
.\validate_all_generic_actor_galleries.bat
.\render_playable_character_previews.bat
.\render_playable_character_widget_previews.bat
.\build_fast_render_style_viewer.bat
.\verify_fast_render_style_viewer.bat
```

Canonical viewer:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated assets are rebuildable. Fix generators, importers, runtime code, or
shaders rather than hand-editing generated prefabs.

## Durable reports

Changing inventories and exhaustive renderer/shader proof live under
`reports/assets/character_recovery/` and the lab’s own reports. This file keeps
only stable interpretation and priorities.

## Highest-value next work

1. Follow the API-2 resource/descriptor records after the HGTree front-end
   wrappers to their runtime object/queue consumer. The callback route now
   enters front-end slots `+0xDA0`/`+0x380`, which record `0x2734`/`0x27B6` or
   tail-dispatch to the selected API backend. The command-stream receiver is
   now resolved: `0x180929540` writes the selected backend returned by
   `0x18072F7E0` to both `[context+0x2700]+0x70` and `context+0x2708`, so the
   interpreter's `0x27B6` case (`0x1813B92F8`) reaches backend `+0x358`
   (`0x1808351F0`) and its `0x2734` case (`0x1813B03DA`) reaches backend
   `+0xDA0` (`0x18083E720`). This closes the recorded front-end -> backend
   receiver edge. It includes the registry paths
   `0x180822180`/`0x1808224F0`, and the shared builder `0x18083E720`; these
   remain pre-device layers. The opcode-`0x55` nested
   `+0xDB0 -> 0x2735 -> API-2 +0xDB0` branch is now
   bounded through `+0x2B60` and callback `0x180820660 -> 0x18082E3E0`,
   including Vulkan dynamic-state/descriptor commands. The remaining
   high-value question is which later flush invokes that list and whether a
   draw/queue consumer follows; do not treat the state callback as final draw
   ownership. The adjacent setup path `0x180843BF0 -> 0x18083F680` reaches
   `0x18083F71B`, where
   `[[[rdi+0x78]+0x208]]` supplies a heap/runtime vtable and `+0x48` is
   invoked. Four static `+E90` callers feed this resource initializer, while
   no static `+DC0` caller was found. The receiver is therefore currently a
   runtime resource-subobject interface, not proven device submission. An
   adjacent resource helper `0x18061FB60` dispatches the same slot shape and
   consumes its return as a NUL-terminated metadata/name string; F8F0 does not
   consume F680's returned value as a handle. F8F0 has only three direct
   callers (`0x18083F680`, `0x180840E00`, and `0x180846635`), all in the
   generic API-2 resource cluster, with no HGTree callback caller. Treat this
   as a resource metadata/name boundary until the concrete nested type is
   recovered.
   The later F8F0 record loops call through shared cell `0x1821D3898`; its
   Vulkan resolver branches pass the string `vkUpdateDescriptorSetWithTemplate`,
   so this is now a concrete descriptor-state update boundary. The API-2
   vtable's adjacent `+0xDE8 -> 0x18083F1E0 -> 0x180843D60` path now proves
   descriptor update -> `vkCmdDraw` -> `vkQueueSubmit` in the same backend
   family. The interpreter jump table `0x1813BB574` maps `0x2730` to the
   `+0xE90` case (`0x1813AFEC3`) and adjacent `0x2731` to the same receiver's
   `+0xDE8` case (`0x1813AFED9`); native writers `0x18093AE10` and
   `0x18092E350` record those literals under the shared `object+0x2711`
   command-stream flag and use the same slots for their immediate fallbacks.
   A static instruction census over the HGTree core and both callback handlers
   finds no `+0x2A0`/`+0x3E8` call, so this remains a separate command-family
   candidate rather than a recovered HGTree renderer-list order. A file-backed fallback assignment to
   `0x180861C20` is only a generic 32-byte record-copy helper, and loader order
   can overwrite the cell; capture or resolve that order before calling the
   fallback active. Keep component 67's LOD/list role and the retail culling
   survivor list separately bounded. The managed draw edge is now positive
   through the active global table-A binding: six named render
    callbacks reach `HGRendererListUtils.DrawTreeECSRendererList`
    (`0x189C0A130`) -> `HGTreeRender.DrawECSRendererList` (`0x18B3FBFA4`) ->
    active table-A `CommandBuffer::AddDrawECSTreeRendererList` (`0x180064580`).
    That body preserves the renderer-list id and calls `0x1804C7930`, which
    writes high-level opcode `0x55`; the interpreter case `0x1804CE4BD` calls
    `0x18106AAE0`, then context `+0xEA0` records low-level `0x273B`.
    The parallel table-B body `0x1801719B0` remains only the managed-root/hash
    validator and alternate duplicate. The complete UnityPlayer table instead
    maps `ScriptableRenderContext.ExecuteCommandBuffer_Internal_Injected`
    (index `3645`) to `0x1800B6F40`, whose positive
    `0x18052D730 -> 0x1804CDF70 -> 0x1804CE0A0` chain is the high-level
    playback route. `Graphics::ExecuteCommandBuffer` is index `924` ->
    `0x18005C0D0`; the inspected body is a separate resource/object path.
    `Submit_Internal_Injected` is index `3636` -> `0x1800B4A40` ->
    `0x1805385A0` -> `0x18052E0B0`. Its type-2/type-3 records reload the
    deferred command-buffer pointers from `context+0x10128` and call the same
    high-level interpreter, making it a concrete deferred consumer rather than
    an unrelated state wrapper. It still has no static HGTree/API-2 final-draw
    ownership proof. The remaining HGTree sink is now after the
    positive `0x55 -> 0x273B -> 0x1813B1110` direct-callback route: the
    callback `0x18107AB10` is invoked by the parsed low-level `0x273B` case
    and remains a resource/list lifetime callback that does not dispatch
    front-end slots. API-2 `+0xEA8` is the adjacent low-level `0x273C` case,
    not this HGTree route. The callbacks that reach
    front-end `+0xDA0`/`+0x380` are the separately installed resource-builder
    thunks `0x181060EA0/0x181060EB0 -> 0x18107AE60/0x18107B3A0`. Their
    `+0xDA0` records then pass through `context+0x2B60` -> master list
    `context+0x2B50` (`0x180841C40`) and the `0x180843D60`/`0x1808200C0`
    executors, which invoke `0x18082D6B0`/`0x18082E660` and named Vulkan
    buffer/state commands when the backend flushes the lists. Static
    HGTree-specific flush/order and dynamic command-buffer/render-graph
    ownership of the final draw and runtime-indirect resource-node consumer
    still need to be joined to the final draw. The main-table attribution is
    now corrected: `ScriptableRenderContext.ExecuteCommandBuffer_Internal_Injected`
    (index `3645`, `0x1800B6F40`) is the proven high-level interpreter entry
    (`0x18052D730 -> 0x1804CDF70 -> 0x1804CE0A0`). `Graphics::ExecuteCommandBuffer`
    (index `924`, `0x18005C0D0`) is a separate resource/object body. The
    `Submit_Internal_Injected` path (`0x1800B4A40 -> 0x1805385A0 ->
    0x18052E0B0`) is a concrete deferred consumer: its type-2/type-3 records
    reload command-buffer pointers and call the same interpreter. It still
    does not prove HGTree API-2 draw ownership. The final
    render-graph/command-buffer owner remains
    runtime-indirect and fail-closed. Ordinary
   `CommandBuffer::Internal_DrawRendererList_Injected` is a separate route:
   UnityPlayer `0x1801713D0` resolves through `0x180A60190`'s indirect
   renderer/resource-state helper, while the HGTree body `0x1801719B0` never
   calls it. Keep that ordinary resource resolver separate from HGTree tree
   submission; neither is a proven final playback sink.
   The apparent late-bound helper in the native tree body is also bounded:
   `0x180A5C5C0 -> 0x180769E20 -> 0x18065C0C0` only normalizes a bounded
   managed payload and computes its CRC/hash (shared by unrelated draw and
    texture command APIs); it emits no opcode, graphics call, or `+0xDE8`
    dispatch. This negative result applies only to table B; the unresolved edge
    now remains after the positive table-A command route, in dynamic
    CommandBuffer/render-graph playback or the runtime-indirect resource
    consumer. The main-table no-copy entries are `0x1800B7440` ->
   `0x18052DB50` and `0x1800B7AD0` -> `0x18052DA20`; the former has the same
   ready-branch `0x1804CDF70` interpreter call, while the latter queues a
   distinct record helper. They are not the previously cited `0x180158...`
   state wrappers. The API-2 `0x80`-byte resource pool
   (`0x180559B30 -> 0x1805598C0 -> 0x1805586C0`) is directly a
   refcount/bitmap lifetime collector. On the specific `AB10 -> 0x180555D30`
   ingress, its callback fields are the bounded cleanup/setter tuple
   (`0x180557650`/`0x180557750`), not a graphics callback; unrelated pool
   producers remain unresolved. The inspected bodies contain no direct
    opcode, graphics, Vulkan, or `+0xDE8` submission edge. Keep final
    HGTree draw/queue ownership fail-closed after the positive command route.
    The latest callback trace separates the Vulkan command-recording identity
    from HGTree ownership. The table-A callback route reaches low-level
    `0x273B -> 0x1813B1110 -> 0x18107AB10`, which ends at the resource/list
    lifetime boundary. The distinct resource-builder callbacks
    `0x181060EA0/0x181060EB0 -> 0x18107AE60/0x18107B3A0` dispatch API-2
   `+0xDA0`/`+0x380`, resolving to `0x18083E720`/`0x1808350E0`; their shared
   records use thunks `0x180820580 -> 0x18082D6B0` and
   `0x1808208F0 -> 0x18082E660`, whose resolver slots name buffer binds,
   dynamic state, pipeline, and descriptor commands. The adjacent
   `+0xDA8` thunk `0x180820940 -> 0x18082E820` additionally reaches
   `vkCmdDrawIndexedIndirect`/`vkCmdDrawIndirect`, but its concrete producer is
   HyperGryph table index 503, `HGTerrainManager::RenderTerrain`:
   `0x1801F4D40 -> 0x1811DDC50` writes high-level opcode `0x60`, the interpreter
   invokes callback `0x1811A5BD0 -> 0x1811AB1B0`, and the pass executor reaches
   `0x1804D4680 -> +0xDA8`. No static HGTree handler calls `+0xDA8`; therefore
   this is a generic Terrain control-path witness, not a retail HGTree draw
    proof. Managed tree-list playback is now source-pinned through opcode
    `0x55` and `0x273B`, including runtime callback execution for Vulkan
    resource/state work; HGTree-specific indirect-draw ownership, callback
    ordering, and queue submission remain fail-closed. See
   `reports/assets/character_recovery/hgtree_renderer_list_command_submission_boundary.md`.
   The neighboring generic HGMesh wrappers are also distinct: GameAssembly
   `0x18B3FA1F8` records
   `AddDrawECSMeshRendererListWithSRPRendererList_Injected` via `0x18B3E3F44`,
   while `0x18B3FA224` enters the ordinary ECS-list command path via
   `0x18B3E3FA8`; neither wrapper flushes or proves HGTree ownership.
   The generic flush family is separately source-pinned: high-level opcode
   `0x6A` (`0x1804CA0B0 -> 0x1804D178A`) and low-level opcode `0x27D5`
   (`0x1813BB574 -> 0x1813B156A`) both dispatch API-2 `+0xF10`
   (`0x18083F140`), which finalizes pending resource/state batches and enters
   `0x180841C40`; `+0xDE8` (`0x18083F1E0`) also flushes and executes the master
   list through `0x180843D60`. The direct opcode writers are generic pass or
   resource functions, and no static HGTree handler emits either flush opcode
   or `+0xF10`/`+0xDE8`; keep HGTree-specific ordering and final draw/queue
   ownership fail-closed.
   The caller census now places Tree playback inside six concrete pass lambdas
   (punctual-shadow, GBuffer, two deferred branches, HGShadow, and HGASM),
   alongside ordinary renderer/ECS/grass list calls. GBuffer's nearby
   `Add_GPUDriven_DrawRendererList` is a separate path, and HGASM's
   `ExecuteCommandBufferNoCopy` occurs before the list sequence. No caller has
   a direct Tree-specific `+0xDA8`/`+0xDE8`/`+0xF10` edge, so final
   render-graph execution and HGTree draw/queue ownership stay fail-closed.
   A complete callback-slot census narrows this boundary further: the main
   HGTree handler uses `+0x210/+0x268/+0x280/+0xC8/+0xD8/+0xD0/+0xE0/+0xE8`
   plus `+0xDA0/+0x380`, while the sibling also uses `+0xB0/+0xC0`, which map
   to API-2 resource-registry paths (`0x180833470/0x180833630` ->
   `0x180822180/0x1808224F0`). The other inspected slots are resource,
   handle, or state mutations; neither callback emits `+0xDA8`, `+0xDE8`, or
   `+0xF10`. Generic `0x2731 -> +0xDE8` is paired with `0x2730 -> +0xE90`
   in a separate render-pass/command writer (`0x18092E350`/
   `0x18093AE10`), and the managed tree wrapper (`0x189C0A130`/
   `0x18B3FBFA4`) has no flush edge. The remaining HGTree ordering/final
   draw/queue boundary therefore stays fail-closed. The latest handler census
   confirms that `0x181060EA0/0x181060EB0` only rearrange arguments into
   `0x18107AE60/0x18107B3A0`; the handlers consume a result object whose
   `[result]` is the item array and `[result+8]` is the count, then dispatch
   only `+0xDA0/+0x380` on their resource-callback tails. A full exact
   `call [register+0x10]` census in the
   API-2/resource ranges finds only ordinary vtable release/destructor calls
   plus the known `0x18106AAE0` cleanup family; none consumes builder
   `outResult+0x10`. The pool's `0x1805594BD` callback is a caller-supplied
   allocator control pair with a pool index, not the node result pair. The
   producer trace now positively joins `0x181080730 -> 0x180555D30` to pool
   callbacks `0x181065190/0x181067A70`, which call builders
   `0x18106BEF0/0x18106D020` using `context+0x58/+0x60`; those builders write
   completion thunks `0x181060EA0/0x181060EB0` at `outResult+0x10`, while
   `context+0x68` is the completion flag. A global
   `mov [pair+0x10]`/`call reg` scan found only unrelated XR-audio, refcount,
   and tagged-generic families; no HGTree/API-2/Vulkan/queue consumer. The
   runtime result-pair-to-final-draw join remains unresolved and fail-closed.
   The HGTree opcode-`0x55` fallback itself is now a confirmed indirect
   callback consumer: `0x18106AAE0` and sibling handlers load
   `[rsi+0x10]`, test/release its `+0x20` pair, and call `[record+0x10]`
   with `[record+8]` (`0x18106AC65-0x18106AC96`, with sibling sites at
   `0x18106AAC6`, `0x18106AE54`, and `0x18106B014`). This is a real
   renderer-list callback dispatch into `0x181060EA0/0x181060EB0`. The static
   identity is now proven: the async task's arg5 renderer record is copied to
   task-descriptor `+0x68`, and the worker writes the callback/result pair back
   to that same record before this fallback loads it.
   The async task route is now bounded across all three worker selections, but
   they are not one implementation: `0x18107E2E0` queues
   `0x181065FD0`, `0x181066F40`, or `0x181064100` through `0x180555D30`.
   Its Windows x64 arg5 is the renderer record; `0x18107E411` stores that
   pointer at task-descriptor `+0x68`, so the non-empty dependency branch
   `0x181065FD0 -> 0x18106B5B0` writes `[record+8]` and
   `0x181060EA0` at `[record+0x10]` (`0x18106BEC9-0x18106BECD`). The other
   two workers call `0x18106C6C0` at `0x1810678EC/0x181065056`, pass the same
   descriptor `+0x68` record as builder argument 6, and reach its shared tail
   `0x18106CFA7`/`0x18106CFC9-0x18106D003`, which writes the same record
   fields. Each caller copies the returned pair into that record's `+0x20`.
   The
   separate initial/sibling builders still
   account for `0x181060EB0` (`0x18106BEF0`'s `0x18106C639` branch and
   `0x18106D020`'s `0x18106D769` tail). The pool worker `0x1805598C0`
   invokes only the node `+0x30` worker and optional `+0x40` index setter
   before retiring through `0x1805586C0`; `0x180557650` and `0x1805592B0`
   use holder cleanup/index callbacks, not the result-pair callback. The
   renderer-record-to-HGTree-handler edge is therefore statically joined;
   only the handler's later indirect-draw/flush/queue ownership remains
   unresolved and fail-closed.
   The pool-context identity is now proven through the calling convention:
   `0x18107E2E0` passes its task context in `r9` to `0x180555D30`, which
   forwards it through `0x1805573D0` and `0x180559520` as `r8` into
   `0x1805592B0`. That allocator saves incoming `r8` and copies the saved
   value to `node+0x28`; `0x1805598C0` then calls `node+0x30` with that field
   as `rcx`. The standard wrapper's callback tuple has a zero tail, so
   `node+0x40` is null and no hidden setter consumes the task's `+0x10`
   argument-5 record/input slot after the worker. The producer/pool identity
   and record callback identity are closed; the handler's continuation into
   final indirect draw/flush/queue remains unresolved and fail-closed.
   A hash-pinned constant-driven census over all 113,390 UnityPlayer functions
   finds only four direct writes of the known HGTree callback addresses into
   record-like `+0x10` slots: `0x18106BECD` and `0x18106D003` use
   `0x181060EA0`, while `0x18106C66B` and `0x18106D79B` use `0x181060EB0`.
   No callback-valued `+8` write appears. The `0x18107EE40` alias hit is only
   zero-initialization of a new 0x30-byte record, not a binding. This closes
   the direct static callback-producer set. The renderer-list record identity
   is now proven by the arg5 → task `+0x68` mapping; final indirect-draw,
   flush ordering, and queue ownership remain unresolved and fail-closed.
   The three renderer-list creation cores are also bounded on their
   resource-ready branches: `0x18107EE40`, `0x18107FD22`, and `0x181080190`
   call `context+0xEA0` with `0x181060D90/0x181060D20/0x181060D00`, then
   `context+0x850`; the unavailable-resource branches call shared builder
   `0x181080730`. Front `+0x850` (`0x180934850`) only records `0x2798` and
   advances a command counter. A direct resolver-cell scan over
   `0x181060000-0x181081000` finds no Vulkan draw call; named indirect draws
   remain in the neighboring API-2 `+0xDA8` thunk
   (`0x180820940 -> 0x18082E820`). This strengthens the negative boundary:
   HGTree creation/callback code still has no static final draw, flush, or
   queue-submit edge, so that join remains fail-closed.
   The deferred Submit audit now closes the command-buffer consumer boundary:
   record types `2`/`3` in `0x18052E0B0` reload the pointers queued by
   `0x18052D730`/`0x18052D8F0`/`0x18052DB50`/`0x18052DA20` and execute them
   through `0x1804CDF70`. This confirms that the HGTree writer's `0x55` record
   can be consumed through Submit as well as the direct Execute/NoCopy path,
   but does not turn the generic `0x6A -> +0xF10` flush or neighboring `+0xDE8`
   master-list path into an HGTree-specific draw/queue proof. A vtable
   cross-check separates the generic `0x2730`/`0x2731` writers from that
   backend: `0x181DCB600 + 0x0/+0x148` contains
   `0x18093AE10`/`0x18092E350`, while the API-2 backend table
   `0x181DBC098 + 0xDE8` is `0x18083F1E0`; the writers immediately dispatch
   into the backend slots but are not the backend draw/submit implementations.

   The managed render-pipeline boundary is now positively joined. The mapped
   `HGRenderPipeline.Render(ScriptableRenderContext, List<Camera>)` body spans
   GameAssembly `0x183455030-0x18345A6E4`; it directly calls
   `ExecuteCommandBuffer` at `0x183457129` and `0x18345997B`, calls
   `ExecuteCommandBufferNoCopy` at `0x183459502`, `0x1834595D4`, and
   `0x183459614`, and calls `Submit` at `0x183459D69`. The six concrete pass
   lambdas that call `HGRendererListUtils.DrawTreeECSRendererList` preserve
   their render-graph context in `rsi`, `rbx`, `rdi`, or `r13` and pass that
   same context as `rcx` to `0x189C0A130`, while passing their renderer-list id
   in `edx`; the helper reads `context.fields.cmd` before forwarding to
   `HGTreeRender.DrawECSRendererList`. Therefore the table-A HGTree
   `0x55 -> 0x273B` records are recorded through the same managed
   pass-command-buffer framework that the main Render method executes and
   ultimately submits. This joins HGTree playback to the render-pipeline
   Execute/NoCopy/Submit boundary, but does not identify the HGTree-specific
   API-2 `+0xDA8` indirect-draw branch, `+0xDE8` flush order, or Vulkan queue
   owner; those remain fail-closed.
   The RenderGraph command-buffer identity is now bounded below the pass
   callbacks. `HGRenderGraph.ExecuteRenderGraph` (`0x189B2BA30`) calls
   `ExecuteCompiledPass` (`0x189B2B62C`), which passes
   `r8 = [this + 0x60]` to `PreRenderPassExecute` (`0x189B2E740`) and
   `PostRenderPassExecute` (`0x189B2E4B4`), then invokes the compiled pass
   through `HGRenderGraphPass.Execute` (`0x189B37D20`). The
   `HGRenderGraphContext` layout is source-backed as `renderContext` then
   `cmd`; native Pre loads `cmd = [rgContext + 0x18]`, passes
   `&[rgContext + 0x10]`, and calls `ExecuteCommandBufferNoCopy` at
   `0x189B2E8D4`. The six identified pass lambdas receive this same context
   shape before calling `HGRendererListUtils.DrawTreeECSRendererList`, which
   reads the same `context.fields.cmd`. Therefore HGTree `0x55 -> 0x273B`
   records are placed in the command buffer RenderGraph prepares and executes
   around the pass, and pipeline-level `Submit` remains its deferred consumer.
   This closes command-buffer identity, but not HGTree-specific `+0xDA8`
   selection, `+0xDE8` ordering, or queue ownership.
   The generic pass/delegate edge is now concrete: builder
   `SetRenderFunc<PassData>` (`0x1876BCA9C -> 0x1876BC9C4`) calls pass
   `SetupSubpass`/`SetupRenderFunc` (`0x1884756FC`/`0x1884755E0`), whose
   helper `0x188475590` stores the delegate, camera, and 16-byte payload in
   descriptor slots `+0x20/+0x40/+0x60/+0x80`. Generic
   `HGRenderGraphPass<PassData>.ExecuteInternal` (`0x188474A4C`) calls
   `ExecuteSubpassRenderFunc` (`0x188474E38`); it iterates `m_subpasses`
   (`this+0xB0`), invokes `HGRenderGraph.InvokeOwnerCallback` (`0x189B2DA6C`),
   obtains `HGRenderGraphContext` via `get_HGContext` (`0x189B3011C`), and
   invokes each stored delegate with pass `data` (`this+0xD0`) and that
   context. This closes the dynamic delegate edge into the six identified
   HGTree pass lambdas, but the generic pass body still has no static
   `+DA8/+DE8/+F10`, Vulkan draw, or queue-submit edge; final HGTree draw and
   queue ownership remain fail-closed.
   A full tail audit confirms both resource callbacks share that TLS front
   context: `0x18107AE60` calls `+0xDA0/+0x380` at `0x18107B2F0/0x18107B31B`,
   while `0x18107B3A0` makes the matching calls at `0x18107B960/0x18107B98E`.
   Front vtable `0x181DCB360` records these as `0x2734/0x27B6` (or dispatches
   immediately through `context+0x2708`); their consumers are backend
   `+0xDA0/+0x358`, not the neighboring `+0xDA8/+0xDE8` draw/flush family.
   This strengthens the fail-closed HGTree-specific draw/queue boundary.
   A direct `+0xF10` caller census further separates ownership: the only
   nearby `0x181080C30` caller is a generic per-draw/VAT/visibility batcher,
   while the other callers are DispatchCompute, mesh-buffer, or generic
   Vulkan-resource paths. None consumes an HGTree callback or renderer-list
   record. The HGTree callback front vtable `0x181DCB360+0xDE8` resolves to
   no-op `0x180076890` (the backend table's `+0xDE8` is
   `0x18083F1E0`), so generic `0x6A/0x27D5` flushing is not promoted to
   HGTree-specific ordering or draw ownership.
   One nested path is now positively bounded: opcode-`0x55` handler branches
   `0x18106A963` and `0x18106AB33` call front `+0xDB0` before their later
   `+0xEA0` callback record. Front `+0xDB0` (`0x180930C00`) records low-level
   `0x2735` (or immediate-dispatches its backend slot), and case
   `0x1813B05B6` calls the receiver `+0xDB0`. API-2 `+0xDB0`
   (`0x18083AA90`) stages `+0x2B68/+0x2B70` and appends a `+0x2B60` record
   whose callback is `0x180820660 -> 0x18082E3E0`; its resolved cells include
   `vkCmdSetDepthBias`, `vkCmdSetStencilReference`, `vkCmdBindPipeline`, and
   `vkCmdBindDescriptorSets`. The adjacent helper `0x18082E760` uses
   `vkCmdCopyImage`, but no pointer write in this trace attributes that helper
   to the exact HGTree record. This is a positive HGTree-to-Vulkan
   state/resource edge,
   and the existing master-list executor can consume the same list after a
   later flush, but neither `+0xDB0` nor `0x2735` contains `+0xDE8`, `+0xF10`,
   `vkCmdDraw*`, or `vkQueueSubmit`; final draw/queue ownership therefore
   remains fail-closed.
   The list protocol is more specific than a generic “later flush”:
   `0x180841C40` packages both working heads (`+0x2B58` and `+0x2B60`) into
   master-list callbacks `0x180820210`/`0x1808200C0` only when `dl=1`, while
   `dl=0` clears those working heads. API-2 `+0xF10` appends its own pending
   record and calls `+0xC40` with `dl=1` (package only); `+0xDE8` calls
   `+0xC40` with `dl=0` and then invokes `0x180843D60`, which walks the master
   list and calls `0x1808200C0`. Thus the HGTree `+0xDB0` record needs a
   separate packaging call before the execution call; neither step is emitted
   by the inspected HGTree handlers or callbacks.
   A fresh owner census found exactly four direct `0x6A` writer call sites
   (`0x181118AD0`, `0x18111A7D7`, `0x1811BE9BA`, `0x1811C7FFD`) in native
   owners `0x181117560`, `0x1811195E0`, `0x1811BDC37`, and `0x1811C772D`.
   None directly references the HGTree creation/callback family, front/API-2
   `+0xDB0/+0xEA0`, `+0xC40`, `+0xDE8`, `+0xF10`, or the master-list executor.
   The low `0x27D5` path is only the interpreter dispatch at
   `0x1813B156A -> +0xF10`; no static writer edge joins it to those owners or
   to HGTree. Keep generic packaging and HGTree callback execution as separate
   until a runtime trace proves the missing ordering bridge.
   The managed `ScriptableRenderContext` Submit/Execute target audit now
   separates the deferred command consumer from API-2 HGTree flush state.
   GameAssembly maps `Submit`/`Submit_Internal`/`Submit_Internal_Injected` to
   `0x183DBB470/0x183DBB4E0/0x183DBB540` and
   `ExecuteCommandBuffer`/`NoCopy` to `0x183339850/0x1834534C0` (with the
   injected NoCopy body at `0x1834535C0`); these wrappers lazy-resolve distinct
   UnityPlayer targets. The resolved Submit chain is
   `0x1800B4A40 -> 0x1805385A0 -> 0x18052E0B0`, whose command-consumer fields
   are `+0x10030/+0x10040/+0x10128/+0x10168/+0x10178`, not API-2's
   `+0x2B60/+0x2B68/+0x2B70/+0x2E48`. No tracked native function crossed both
   field families in the bounded census, so HGTree command-buffer playback is
   joined to Submit/Execute but the `+0xDE8` ordering and queue owner remain
   fail-closed. Runtime attach was denied by `WriteProcessMemory` in this pass;
   this conclusion is static. See
   `reports/assets/character_recovery/hgtree_renderer_list_command_submission_boundary.md`
   item 68.
2. Validate representative paths against accepted retail captures.
3. Extend texture/mip and material-variant recovery only where visible.
4. Generalize animation from another exact Avatar/clip oracle.
5. Recover the Character Info selection clear/hide interval and the
   `SampleToBeginning -> RebuildGraph -> Evaluate -> Play` ordering across the
   actor, `Audio`, `Light`, `Others`, and physical `ExternalCamera` Directors;
   Actor/Audio/Effect plus exact empty Light/Others ordering is executable; next
   connect the remaining individually proven phase fields beyond the now-live
   direct-light/color/descriptor subset, close the narrow same-update old-root
   `LateTick`, Audio `ProcessFrame` flag/onset, and streamed-phase boundaries.
   Queue-3005 `baofa` Glow902 is now executable only under its exact Gacha
   owner. The shared CharInfo `CharEffect/trail` is now generated and replayed
   with its selected `_USE_RBOFFSET` Distortion MRT branch and property-bound
   render state; next capture its D3D12 pixels and close final PSO overrides,
   survivor ordering, physical aliases, and live descriptors. Generalize the
   now-closed `AnimatorBehaviourPlayEffect._effects[]` owner path from Zhuang
   Fangyi to the remaining controller records. Last Rite's independently
   AssetMap-proven head effect is now executable: its 8-node hierarchy, five
   particle pairs, head mesh, exact 3.5/13.5 timing, eight ordered controller
   requests, and unique `Bip001_HeadNub` binding pass Unity validation. Its six
   VFXBaseV2 materials remain ColorMask-0 fail-closed, and the other seven
   Last Rite requests remain explicitly unbound. Their complete serialized
   Material payloads and 12/12 AssetMap-resolved converted texture PNGs are now
   pinned in contract schema v2; both compiled keyword pairs are also known.
   The remaining material gate is retail PSO/descriptor/native mip and
   ForwardOnly MRT/scene-depth scheduling, not missing converted texture
   pixels. Continue with that binary draw boundary and Li Zhiyan/Wulfa for retail
   visual acceptance, preserving each exact prefab, mount, delay, duration,
   and teardown contract; recover full hierarchy/PPtr mounts before Pograni's
   eight ambiguous entries; and
   keep Gacha-only and other queue-3005 materials fail-closed;
   use the measured early-ribbon, sustained green-local, and late-flare windows
   as visual acceptance bounds without promoting them to ownership evidence.
   use the now-complete 31-prefab Viewer catalog for the next shared-Viewer
   visual capture; generated Gacha-runtime validation remains independently
   green. RenderDoc 1.45 provides a real retail D3D12 attach/inject path, but
   no retail `.rdc` exists yet; Unity auto-capture and the Frida renderer-list
   trace are not substitutes. Stop if normal attachment is rejected and keep
   the PathID-to-draw correlation boundary explicit.
   Last Rite's retail slot is `269.25-283.25 s`, but it is a weak per-effect
   oracle: no head/hand/thigh/ear particle pass is independently visible over
   the animation, costume/weapon geometry, cyan hair, and transition haze.
   Li Zhiyan's independently AssetMap-proven finger effect is now the second
   non-Zhuangfy executable Overview prefab: 8 hierarchy nodes, 7 particle
   pairs, 6 VFXBaseV2 materials, 8 resolved texture identities, exact
   `0.83333/2.33333 s` timing, and unique `Bip001_R_Finger2Nub` binding pass
   Unity validation. A focused installed-VFS export now also closes all eight
   original BC7 payloads: every single-image 2D mip chain has zero stripped
   mips, exporter-validated byte layout, payload hash, dimensions, color-space,
   and serialized filter/aniso/bias/wrap settings pinned in contract schema v2.
   The installed Persistent-VFS override of `HGRP/Effect/VFXBaseV2` is now the
   selected shader source rather than its same-PathID StreamingAssets base
   copy. Its 1,360 compiled D3D11 keyword signatures are uniquely stage-paired;
   the six materials map exactly to three non-instanced VS/PS pairs (base,
   `_USE_SOFTBLEND`, and `_SAMPLE_TEX0+_USE_SOFTBLEND`) plus their three
   SRP-instanced pairs. Exact bytes, FXC assembly, metadata, Ruri register
   signatures, dual MRT outputs, Persistent source/chunk hashes, and the native-static queue
   `3660..3740` after-DOF attachment contract are pinned and validated in the
   Unity lab. The pixel ABI is now exact: common `b0[28]/b1[105]/b2[5]`,
   variant `b3[21/22/28]`, and one/two/three exact `tN/sN` sample pairs.
   This closes static resource semantics but not the live descriptor identity.
   The lab's after-DOF attachments match the source schedule. Exact `.pdata`
   bodies now pin the current-build renderer-list preparer, pass constructor,
   and callback, including the callback's fullscreen -> ordinary list -> ECS
   list chain. The downstream transparent descriptor is also closed before
   runtime culling: sorting `87`, named WorldUI removal, absent state block,
   null override material, and false motion-vector exclusion. Its normal
   per-object flags are now exact `15 | 32 = 47`; Unity publishes the same
   request. HGCamera defaults are ratio `0.005`, distance `30`, and a lazy mask
   over 17 named layers. The selected Viewer camera has `0xffffffff` Unity
   culling and no serialized HG override, but external mutation and the actual
   lazy mask remain runtime facts. Unity now uses
   the matching optimized transparent sorting and named-layer policy. HG
   screen-culling instance values and final survivors remain open. The
   deferred ECS producer is closed to
   `HGRenderPathDeferred.OnPreRendering`: it creates a per-camera-frame UInt32
   list with `TransparentAfterPP` mask/value `0x4400/0x4000`, stores it at
   `this+0x1388`, and writes `0xffffffff` when its feature/camera gate fails.
   The current Forward render path creates only ordinary transparent/opaque/
   pre-Z ECS lists and leaves this constructor-initialized sentinel unchanged.
   The static screen-culling writer boundary is narrower: `HGCamera..ctor` is
   the only mapped HG runtime writer of ratio `+0x9d8` (`0.005`) and distance
   `+0x9dc` (`30.0`), while mask `+0xa20` is rewritten by ECS/lightweight-camera
   culling paths and propagated through custom request/PassInput data. The
   exact UnityPlayer `HGMeshRender::CreateRendererList` registration resolves
   to adapter `0x1801f1e40`, request packer `0x18104e7a0`, and registration core
   `0x18104e300`. The core appends a 16-byte manager slot and returns its old
   count as the zero-based UInt32 handle; it does not iterate entities, write
   survivors, sort, dispatch multi-draw, or draw. Those operations remain
   downstream. The correct HGMesh consumer is CommandBuffer opcode `0x4e` ->
   singleton `+0xb0` -> `0x181005c10`, which resolves the same 16-byte slot and
   installs resource callback `0x180feade0 -> 0x181047160`; it still contains no
   survivor loop, sort, indirect draw, or queue submit. HGTree opcode `0x55`,
   singleton `+0xc0`, 24-byte slots, and `0x18106aae0` are a distinct family.
   Registration locally grows the HGMesh vector, increments its count, zeroes
   a new slot, and allocates/stores a 0x30-byte state; opcode `0x4e` reads it
   without mutating count or storage. No decrement, reset, clear loop, free, or
   reuse appears in the pinned registration/interpreter/consumer spans.
   Context replacement/teardown remains the only open lifecycle boundary, so
   do not invent per-frame handle reuse.
   That boundary is now addressable: `0x180fc5e60 -> 0x18030f100` reads
   singleton table slot `0x14` at pointer cell `0x1821688a0`; its context keeps
   HGMesh at `+0xb0` and HGTree separately at `+0xc0`. Generic setter
   `0x18030f5b0` writes the table, bulk registrar `0x180319e60` reaches slot
   `0x14`, and global teardown `0x18058cc20` necessarily cleans and clears it.
   Constructor `0x180fc21d0` installs context vtable `0x181e1c328`;
   initialization/destruction are `0x180fc3500/0x180fc2e00`.
   Initialization allocates the 0x70-byte `+0xb0`
   manager, initializes category `0xb5` through `0x1810454c0`; teardown uses
   `0x1810459f0 -> 0x18105fe30` to destroy 16-byte entries and free storage.
   Logical reset is `0x181060330`. The registry boundary is descriptor -> type
   ID (`0x1807c5240`) -> lookup (`0x18012be60`) -> dynamically initialized
   allocator callback `[descriptor+0x08]` (`0x18031a370`); its readable name
   and callback identity remain unknown.
   The next runtime proof is bounded to eight already pinned observation points:
   `0x1801f1e40`, `0x18104e300`, `0x181005c10`, `0x18105e400`, and
   `0x18105e350`, plus `0x1813b1624`, `0x18083f89d`, and `0x1813afed9`.
   Acceptance requires a same-frame handle -> opcode `0x4e` ->
   accepted/sorted record -> resolved resource -> final draw -> visible
   Li Zhiyan pixel join, plus a Li-absent or Wulfa negative control. This
   versioned contract does not authorize attaching/injecting into retail and
   fails closed on protection refusal or binary/prologue drift.
   Downstream, resolved pointers reach a CPU publication/result object and
   generic front-end handoff `0x180feaea0 -> 0x1810484e0..0x181049007`.
   Resource identity now reaches derived GPU descriptor state but not one
   particular indirect buffer/draw. The installed
   UnityPlayer explicitly says `D3D12 support not compiled in!` and carries no
   D3D12 command backend surface. A bounded 2026-08-15 `Player-prev.log`
   snapshot positively observes the installed client creating a Vulkan 1.4.341
   device on the RTX 5080. Because that log has no UnityPlayer hash and does
   not identify the Li Zhiyan frame, exact image/session and HGMesh-to-Vulkan
   command joins remain open; generic Vulkan/API-2 wrappers stay excluded
   until resource identity reaches them.
   The graphics-front context/vtable are now pinned at `0x180725dc0` and
   `0x181dcb360`; resource paths record opcodes `0x2748/0x274a`. Internal
   backend ID 2 selects factory `0x180891210` and table `0x181dbc098` (not
   Unity's public enum value). Its `+0xde8` flush reaches
   `0x18083f1e0 -> 0x180843d60` and resolves Vulkan bind/draw/indirect/submit
   commands. Backend selection is closed; the unresolved edge is the HGMesh
   resource identity reaching one specific Vulkan draw and visible pixel.
   Front opcodes `0x2748/0x274a` are now decoded through interpreter
   `0x1813aee90` and dispatch cases `0x1813b1624/0x1813b16f0`: they return to
   API-2 `+0x268/+0x280`, select modes 1/0 at `0x180842370`, and operate on
   16-byte resource/state records under context `+0x2e48`. They are not draw
   opcodes. Vulkan execution later walks a distinct master callback list at
   context `+0x2b50`; verified callback families bind vertex/index data,
   pipeline/descriptors, issue direct or indirect draws, and submit. The
   original `0x2748` pointer is preserved into backend binding state at
   `S+0x2a0/S+0x22d0`; if a later generic `0x2730` occurs on the same API-2
   context, it packages those regions through `+0xe90` and can reach
   `vkUpdateDescriptorSetWithTemplate` at `0x18083f89d`. The HGMesh handoff
   itself emits no `0x2730`, so this is conditional shared state, not a
   per-record descriptor identity.
   All four opcodes share one per-instance recorder; append order equals call
   order between begin/end recording, but no static producer edge guarantees
   `0x2748 -> 0x2730 -> 0x2731`. API-2 `+0xda0/+0xda8` construct the concrete
   resource, pipeline/descriptor, and indirect-draw child nodes, and
   `0x180841c40` packages them into the `+0x2b50` master list. The original
   pointer is not retained in those nodes, leaving derived-state association
   as the final runtime identity gap.
   Direct handoff audit proves only `0x181048848: +0x268 (0x2748)` followed by
   `0x1810488dc: +0x280 (0x274a)` for one 0x90-byte result record and front
   context. No `+0x2a0/+0x3e8` call exists there. The callback nodes are generic
   API-2 capabilities; ordinary HGMesh wrappers have no static indirect-draw
   or submit edge, so they must not be attributed to characters without live
   identity values.
   A stdlib-only offline importer now makes that runtime boundary executable:
   `tools/build_lizhiyan_retail_draw_observation_contract.py` pins the retail
   MKV (1,678,613,397 bytes, SHA-256 `2F542A3B...EBF5E7`), verifies its
   3840x2160 H.264 High/BT.709 limited-range stream and integer 1/1000 PTS,
   and publishes `lizhiyan_retail_draw_observation.json`. With no separately
   authorized traces it stays `proof_pending`, `visibleAdmission=false`.
   Admission requires an ordered same-frame/session/recorder/resource chain
   through register, opcode `0x4e`, full survivor record, publication,
   `0x2748`, derived descriptor-state hash, descriptor update/bind, `0x2731`,
   draw, submit, and exact video PTS/pixel, plus a comparable Li-absent or
   Wulfa negative control. Pointer or timestamp equality is rejected.
   Runtime values and final survivor/order/lifetime capture remain required;
   do not synthesize a `Renderer[]` bridge from the integer ECS handle.
   A separate offline visual oracle pins exact retail PTS
   `38000/40000/42000/43000/44000/46000` as deterministic 960x540 RGB24
   hashes and fixed ROI measurements. Broad teal coverage peaks at PTS 40000
   (`0.216991352`) and reaches the settled baseline at PTS 46000
   (`0.006558944`). This enables repeatable Unity camera/timing/compositing
   comparisons but remains `diagnostic_only`, `visibleAdmission=false`, and
   proves no material or draw ownership.
   Exact transition frames now bound the prior actor as last stable at PTS
   37667, first fading at 37683, the blank interval at 37700..37950, and first
   recognizable Li at 37967. The first teal edge is tentative at 38167 and the
   first unambiguous slab is PTS 38183. Source controller timing independently closes start-clip entry to
   `0.062452073 s`, exit to `10.68547903 s`, and transition duration to
   `0.014519697 s`; the 10.7-second clip has no AnimationEvents. The timing
   alignment keeps PTS 37967 candidate-only. Current lab request semantics
   would make the finger root live at candidate PTS 38800..41134, covering the
   PTS-40000 peak but not measured teal at PTS 42000. Recover the original
   request producer and the other eleven Li entrance effects instead of
   stretching or retiming the one proven finger prefab.
   The first remaining root request is now classified:
   `P_fxui_lizhiyan_overview_start_01` is a five-node, four-renderer static-mesh
   animation with zero ParticleSystems, duration `2.2`, delay `0`, shared mesh
   `S_fx_lzy_tiaodaifenwei_01`, and exact queue-3704 materials
   `M_fxui__lizhiyan_overview_09/_10/_11`. The source contract pins hierarchy,
   transforms, EffectSetting, renderer/filter payloads, converted OBJ, and
   material payloads. AnimationClip PathID `7360398354216100382` is now closed
   to `A_fxui__lizhiyan_overview_start_01` (30 Hz, 6.366667 seconds, no
   AnimationEvents), and the eight referenced Texture2D identities and
   converted PNGs are pinned. All 53 material curves are now binding-closed:
   `Animator.StringToHash` maps four paths to start_01 and six to sibling
   start_02/start_03 roots, while the AnimeStudio CRC28-plus-channel contract
   maps all seven material attributes. A generated name-complete `.anim`
   imports in Unity as exactly 53 MeshRenderer curves with the expected ten
   paths and seven properties. Native mesh/texture import parity, exact selected shaders, and a static-mesh runtime
   binding remain open; do not force it through the particle importer.
   The lab now has a separate `StaticMesh` binding kind and
   `EndfieldRecoveredStaticMeshEffectSource` provenance marker. Existing
   particle bindings remain enum value zero. Static admission requires the
   exact root/component and four renderer/filter identity sets, zero
   ParticleSystems, source contract visibility approval, applied
   EffectSetting/animation/native mesh/texture/renderer payloads, and exact
   non-fail-closed shaders. A Unity batch validator proves the current
   start_01 contract is rejected before instantiation because its source and
   visible-admission gates remain false; the actor keeps this request unbound.
   The fixed-build managed consumer is now closed from
   `AnimatorBehaviourPlayEffect.OnStateEnter` through helper/EffectInstance,
   `EffectSetting` and `EffectLodCfg`, then `EffectAnimation` creating a
   PlayableGraph/AnimationPlayableOutput/AnimationClipPlayable. This supports
   a source-faithful playable driver and rejects inventing an
   AnimatorController. The remaining native edge is the serialized
   `EffectLodCfg.renderer` identity reaching a specific renderer-list,
   descriptor/PSO, draw, submit, and visible pixel; generic HGMesh/API-2
   evidence does not prove that attribution.
   The retail playable topology is now pinned more narrowly: it creates a
   `GameTime` graph at scale one, an `AnimationPlayableOutput`, and a
   three-input `UnityEngine.Animations.AdvancedAnimationMixerPlayable` for
   start/loop/end clips. These Li roots populate only the start slot and do
   not prove clip retiming or manual evaluation. That advanced mixer is a
   retail custom AnimationModule type and is absent from both the stock
   installed 2021 editor and this lab's Unity 2022 editor. Standard
   `AnimationMixerPlayable`, Timeline mixers, and an invented controller are
   therefore rejected as exact substitutes. The generated topology contract
   and Unity validator keep graph creation and visible admission fail-closed
   until an equivalent retail backend is proven. The advanced type is also
   ABI-distinct from stock: stock `Create` accepts `normalizeWeights` and has
   an implicit Playable conversion, while the advanced type has neither.
   Its injected creation path is now native-closed as UnityPlayer internal-call
   table entry 501 (`0x180158b30`): it validates the graph, allocates custom
   playable node type `0x178`, attaches it, and returns a pointer/version
   handle. Stock mixer creation uses distinct node type `0x170` and a distinct
   initializer, proving it is not exact. Input count is applied afterward by
   `SetInputCount`. Advanced and stock share the exact count/weight virtuals:
   16-byte slots are zeroed on growth/reactivation, so each begins with a null
   playable and weight zero; there is no automatic normalization. Nonnegative
   counts are accepted subject to allocation, while negative counts diagnose.
   The advanced initializer first runs stock initialization, then installs its
   own root vtable and writes `0x0101` at node `+0x170`. Advanced-only virtual
   slots 3/4/13/18/19 actively read/write the `+0x170/+0x171` state bytes and
   gate animation-runtime calls; the corresponding stock slots are no-ops or
   different implementations. Thus even the Li start-only graph cannot claim
   exact stock-mixer equivalence. Null-state transitions and extreme
   allocation failure remain open.
   Their state protocol is now bounded: initialization starts at `1/1`; slot 3
   clears `+0x171` on its first valid evaluation and calls `0x180a5a680`, then
   computes evaluation time and calls `0x180a634d0` on later passes. Slot 4
   resets `+0x174`, sets `+0x170`, then enters stock time/speed propagation;
   slot 13 handles reset commands; slots 18/19 suppress generic callbacks only
   when both bytes are zero. Exact scheduler ownership and the two runtime
   callback semantics remain open, so a pure ScriptPlayable is not yet a
   retail-faithful replacement.
   Those callbacks are now structurally closed. `0x180a5a680` resets the
   context state record at `+0x9e8..+0xa0c` and installs packed value
   `0x00010101`. `0x180a634d0` selects a 28-byte stage record from the table at
   context `+0x748` and invokes `0x180ac4a90`, a four-mode custom animation
   timeline state machine that advances accumulated time, selects stages,
   writes time back at boundaries, and mutates node/state flags. Mode labels
   and the unique native scheduler dispatch remain unresolved. Public Playable
   APIs cannot represent this ABI; exact recovery requires a native custom
   node/shim or a complete managed behavioral rewrite labeled non-ABI-equivalent.
   Applicability is now split rather than inferred wholesale. All three Li
   roots prove the Advanced mixer creation, three-input graph, and start-only
   one-hot control. They do not serialize a producer for the native context's
   active gate, stage table, bound, or current-stage fields, so activation of
   the four-mode custom timeline remains `not_proven_fail_closed`. The
   2.2/5/7-second `EffectSetting` lifetimes are outer destruction boundaries,
   not evidence of mixer stages or clip retiming. Do not inject that stage
   behavior into Li; a stock-mixer implementation may only be an explicitly
   labeled external-behavior simulation and cannot raise visible admission.
   The lab now has that isolated simulation in
   `EndfieldLiZhiyanBehavioralAnimationSimulation`. It constructs a stock
   GameTime three-input graph, connects only slot zero, writes `[1,0,0]`,
   plays and resets the shared clip at speed one, and destroys the graph at
   the configured EffectSetting lifetime. It permanently reports
   `retailAbiEquivalent=false` and `visibleAdmission=false`. Its read-only
   renderer probe records source PathID, hierarchy, Unity instance ID, and
   frame solely to support a future compatible runtime capture; it makes no
   native/HGTree mapping claim.
   A source-scoped start_01 diagnostic prefab is now materialized separately
   from normal actor bindings. Its importer hash-checks the exact shared OBJ,
   matching Animator FBX, eight PNGs, and resolved `.anim`; rebuilds the four
   serialized child transforms and Renderer/Filter/Material PathIDs; and uses
   the Li-specific `LiZhiyanStart01Diagnostic` shader only as a labeled visual
   approximation. Its explicit routing preserves the source distinction:
   M09/M10 map Sample0/1/2 to Mask/Blend/Dissolve, while M11 maps
   Sample0/1/2/3 to Disturb/Mask/Blend/Dissolve. Unity applies 213 supported
   serialized material properties and reports 684 unsupported properties.
   Only 21 of the shared clip's 53 curves bind to start_01; the remaining paths
   belong to start_02/start_03, so the binding gate remains explicitly partial.
   Native payload, exact shader, retail ABI, HGTree ownership, and visible
   admission all remain false.
   Deterministic comparison uses candidate PTS 37967 as diagnostic local zero
   and publishes 24 capture anchors through the start_01/_02/_03 lifetime and
   shared-clip endpoints. This mapping is a repeatable video alignment, not
   proof of the original effect-request epoch.
   The GPU-backed capture harness now proves a narrow visible start_01 loop:
   D3D12 renders non-background pixels at PTS 37967--38183 (about 4.06% frame
   coverage) and the source material curves have fully dissolved by PTS 39934.
   The expanded set adds PTS 39367/41434/43200/43600/43867 at sibling UV,
   alpha-appearance, alpha-peak, primary-wave, and fade boundaries. In the
   start_01-only capture these 24 frames produce four hashes and five visible
   active frames; all post-lifetime frames are blank.
   The harness rejects Unity's Null graphics backend because `-nographics`
   produces valid-looking PNG files without executing rasterization. It keeps
   source queue 3704 and disables soft blend only in transient capture materials
   because the isolated scene has no retail depth buffer. These captures do not
   compare retail pixels and cannot raise visible admission.
   Queue 3704 itself is source-closed as the native
   `AfterPostprocessTransparent` (3660--3740) phase. The recovered SceneMV path
   likewise excludes that range from main transparent and assigns it to its
   after-post callback. The isolated Li shader does not request that exact MRT
   path, so its successful ordinary-transparent capture at 3704 proves only the
   diagnostic draw. It does not prove that Li enters the native after-DOF ECS
   renderer list or produces an accepted 64-byte HGMesh record.
   The managed graph control is now closed beyond construction. `_AddClip`
   connects each non-null clip from output port zero to mixer input
   `animationState-1`; Li's null loop/end return before connection. On every
   state change `_PlayAnimation` writes all three mixer weights one-hot, tests
   each stored clip, plays the target, pauses other valid clips, resets every
   valid clip to time zero, and retains the current playable. Li start therefore
   writes `[1,0,0]`, plays slot zero, resets it to zero, and performs no clip
   operation for slots one/two. There is no cross-fade in this path.
   The complete control ABI is now pinned as well. `ManualEvaluate(float)`
   evaluates the graph, `SyncProgress(float)` derives a time and delegates to
   it, duration/scale setters refresh root speed, `OnDisable` stops, and
   `OnRelease` destroys only a valid graph. `EffectInstance` callers are
   closed for manual update, progress sync, ignore-global-time-scale, and
   active/play-state Play/Stop. Every relevant body first checks an IFix ID,
   but the current installed Persistent patch is now hash-pinned at 86,926
   bytes (`baa28ae...172c`) and its unique terminal table contains 32 targets,
   none in `EffectAnimation`, `EffectInstance`, or `EffectLodCfg`. The decoded
   fallback bodies are therefore the effective bodies for this installed
   offline snapshot; later downloads or live table mutation remain outside
   that claim. No serialized or native caller currently
   proves that the optional manual/progress/duration controls are used by the
   three Li roots; keep their normal speed-one path and do not infer retiming.
   `P_fxui_lizhiyan_overview_start_02` and `_03` are now source-closed sibling
   static effects: each has a root Animator and three MeshRenderers with zero
   particles; their lifetimes are 5 and 7 seconds. `_02` uses one shared mesh
   and materials 12/13/14; `_03` uses two meshes and materials 15/16/17. They
   reference the same 6.366667-second material clip as `_01`, so the 2.2/5/7
   EffectSetting lifetimes select different portions without clip retiming.
   Both sibling roots now also have isolated generated diagnostic prefabs and
   validators. start_02 reconstructs three Plane009 renderers with M12/M13 in
   Mask-Blend-Dissolve mode 9 and M14 in Disturb-Mask-Blend-Dissolve mode 11;
   Plane009 remains explicitly provisional converted geometry. start_03
   reconstructs three renderers from the two PathID-matched converted OBJs and
   M15/M16/M17 in mode 9; this is exact converted-source geometry, not admitted
   native Mesh parity. Each sibling material import reports 213 supported and
   684 unsupported serialized properties. Both reuse the shared clip, retain
   false native payload/exact-shader/animation-payload gates, and remain outside
   normal actor binding with `visibleAdmission=false`.
   A combined GPU harness now instantiates all three diagnostic roots, samples
   the 24 shared-clock anchors, and applies the independent 2.2/5/7-second
   lifetimes. D3D12 produces 14 unique composite hashes. start_01 is visible in
   five active captures; start_02 becomes visible at its PTS 41434 alpha-onset
   anchor (about 0.87% root coverage); start_03 remains visible through the
   later wave, peaking near PTS 43000 at about 2.78% composite coverage and
   decaying to 0.41% by PTS 44000. The shared clip is visually empty by PTS
   44334 even though start_03 remains alive until 44967, and the all-inactive
   PTS 46000 composite is blank. Validation requires at least one visible frame
   per root and blank frames for inactive roots/all-inactive composites. These
   are deterministic standalone-camera results, not retail pixel comparisons
   or native after-DOF ownership proof.
   A separate actor-composed D3D12 harness now preserves that effects-only
   baseline while instantiating the recovered `Lizhiyan.prefab`, explicitly
   sampling the 10.7-second/60 Hz overview-start actor clip, and root-mounting
   the three static effects at identity. It uses the source overview camera
   position `(-0.177,0.998,3.5)`, hierarchy-derived LookAt
   `(0.022,1.225,0)`, FOV `20.007383`, and near/far `0.1/50`; the final
   LookRotation remains labeled inferred because gyroscope input and one legacy
   camera Animation object are not recovered. The 24-anchor real-D3D12 run
   writes actor-only, effects-only, composite, and per-root frames and validates
   all lifetimes while keeping every retail/native admission false. Its
   actor-safe four-corner background consensus fixes the old single-corner
   coverage ambiguity when the animated coat crosses pixel zero. Predicate-only
   comparison shows the source camera/actor composition is usable but the
   broad peak was still missing from the static-effect-only pass: at PTS 40000
   the retail `broadTeal` ROI is 21.699% teal versus 3.499% composite and
   1.454% effects-only; PTS 43000 is
   closer at 9.972% versus 7.618% composite. PTS 46000 has zero effects-only
   coverage while the actor remains visible. This isolates the dominant gap to
   peak effect/material/admission composition rather than gross camera or actor
   absence; the comparison is not pixel equality.
   Under the visual candidate epoch, exact first dynamic keys at PTS 38167,
   40834/40867, and 42467 align respectively with the early teal edge,
   later pillar phase, and next material wave. This is strong timing evidence
   but not screen-space renderer ownership or visible admission.
   Their `lodSetting` rows now close the managed renderer identity itself:
   start_01 names four non-null MeshRenderer PathIDs and start_02/start_03 name
   three each, all under their exact EffectSetting. `EffectLodCfg.Play/Stop`
   owns those managed references, but no static body joins a pointer or
   instance id to an accepted 64-byte HGTree survivor/resource record. Native
   ECS slot 67 is separate LOD/culling state and must not be used as that join.
   Ordinary `Renderer.get_entityID` is now pinned through internal-call table
   entry 1278 (`0x1800e6c40`) to backing native renderer `+0x268`.
   `HGMeshRenderer.GetEntity` instead returns the ECS qword at native `+0x50`
   and requires `+0x50/+0x54` nonzero. The Li fields are ordinary
   MeshRenderers, and no evidence equates these offsets, so this is a stronger
   typed boundary rather than the missing HGTree identity join.
   A complete direct-call census finds no GameAssembly `.text` caller of the
   managed `Renderer.get_entityID` wrapper. UnityPlayer HGTree sites using a
   vtable slot also numbered `+0x268` are context methods, not reads from an
   ordinary Renderer object. The required link is therefore runtime-indirect
   or absent from this managed route, not a missed direct caller.
   The ordinary `+0x268` value now has a bounded positive consumer without
   changing that conclusion. `Renderer.SetCustomPerDrawData_Injected` reaches
   `0x180430680`, stores five Vector4 lanes at renderer `+0x140..+0x180`, and
   uses `+0x268` as a component key for resolver `0x1804255f0`; the resolved
   persistent resource receives the same lanes at `+0xb0..+0xf0`. The complete
   resolver/lifecycle census finds no equality with HGTree's context-owned
   renderer/resource array and no HGTree, descriptor, or upload consumer.
   Therefore `+0x268` is useful ordinary per-draw resource identity, but not
   the missing Li-to-HGTree survivor identity.
   Downstream HGMesh workers now prove a real ordering/publication stage:
   accepted 64-byte records are sorted in place by `0x181043bd0` using
   comparator `0x180fe0740`, an unsigned lexicographic comparison over the
   first 16 record bytes. Publication skips `record+0x20 == 0xffffffff`,
   resolves IDs via `0x181059410`, and appends resource pointers through
   `0x18105e350`. Append helper `0x18105e400` copies the full record unchanged.
   The key layout is worker-family-dependent rather than one uniform field
   ABI: one family places an `asuint(float)>>15` rank in dword 0, while another
   starts with the masked 20-bit source lane and places a
   `(~asuint(float)>>17)&0x3fff` rank in dword 3. Append preserves record order;
   both layouts pack source/context/resource/type/index selectors and a
   conditional `0x01000000` marker. All workers
   share exact source/context exclusion and inclusion masks, `0x60000`,
   `0x7f00`, and `0xc0` flag gates, a view-mask hit, and bit-45 rejection;
   four variants also require signed `source+0x2c > 0` on the bit-15 path.
   Semantic field names remain unresolved, as do indirect draw and backend
   submission; do not relabel this opaque key order as transparent-depth,
   material, or batch order yet.
   The ID/resource boundary is now narrower. `0x181059410` decodes
   `record+0x20` as `key=dword>>1` and `selector=dword&1`, searches an internal
   table through `0x1801f7410`, then indexes an 0x80-byte resource table;
   selector zero returns the row base and selector one returns `+0x78`. This is
   not ordinary Renderer entityID `+0x268` or HGMeshRenderer entity `+0x50`.
   Common helper `0x1810469a0` only packs 0x90-stride CPU publication/result
   arrays, but six finalizer trampolines attach `0x180feaea0` and pass those
   arrays into `0x1810484e0`. That callback repeats the same key/selector and
   0x80-byte resource-table lookup, records `0x2748/0x274a`, invokes the
   `+0xda0/+0x380` API-2 resource-builder family, and has a positive static
   descriptor-state path `0x1810487e1 -> 0x180619cf0`. That helper branches on
   `descriptor+0x450`; only its `0x180623ef0` branch reaches the shared
   graphics-front `+0x2a0` writer for opcode `0x2730`, while Li's selected
   branch value remains unknown. The generic `0x2731` producer has a separate
   runtime-callback `(1) -> 0x2731 -> (0)` bracket on the same recorder family,
   but HGMesh has no static edge into it. The parser supplies no mandatory-next
   flag or generation joining the independent `0x2730/0x2731` cases. The first
   missing positive joins are therefore Li selecting the `0x2730` branch, a
   later `0x2731` in the same after-DOF interval, and attribution of its
   `+0x2b50` callback node to this HGMesh draw rather than another command.
   The descriptor selector is now traced back through the publication layout.
   Finalizer argument M0 owns a hash table at `M0+0x28`; shift/mask fields at
   `+0x40/+0x44` select a 0x60-stride entry, whose `+0x28` descriptor D is
   copied to each 0x90-byte publication record's `+0x10`. `0x1810484e0`
   preserves D in `r13`: `D+0x450` selects mode while `D+0x60` supplies the
   resource recorded by opcode `0x2748`. The independent M1 table uses
   0x38-stride entries and must not be conflated with D. The original 64-byte
   record's packed resolver ID instead lands at publication `+0x84`. Mode 0 chooses the only
   descriptor-state/conditional-`0x2730` branch; mode 2 chooses resource-cache
   or fallback paths and clears the result; other values also fail/clear. A
   matching 0x4e0 descriptor constructor at `0x180ac63f0` has two direct callers
   that pass mode 0, but it does not fill the M0 entry and is not statically
   aliased to D; `0x180ba21b0` and a similar 0x48-stride family are likewise
   excluded as proven producers. The chained-`.pdata` worker
   `0x180ff8020..0x180ff8702` inherits M0/M1 directly from its argument
   `+0x00/+0x08`, builds and sorts the accepted 64-byte records, then passes
   those same tables to `0x181039e90`. Its
   `0x180ff82b5 -> 0x1810442f0` helper is only a temporary 0x30-stride
   group-to-int32-index-vector map over 0x240-byte source records; it is not
   M0 and never writes M0 `entry+0x28`. Descriptor creation is now closed:
   `0x18104ef90` allocates and initializes the 0xf0-byte job object, copies
   caller `rdx/r8/r9` to object `+0x00/+0x08/+0x70`, selects the graphics
   context at `+0x10`, loads the sole confirmed `0x180ff8020` code reference,
   and registers callback plus object through
   `0x180555d30 -> 0x1805573d0 -> 0x180559520`. Its primary caller copies
   source `+0x00/+0x08/+0x10`; the parallel
   `HGMeshRender.CreateRendererListFromEntities_Injected` route reaches the
   same owner through `0x18104ec20`. This job path transports
   already-populated M0/M1 tables; it does not construct their entries.
   Those tables now have native subsystem identities as well. Slot-0x14 root
   `+0x90` is `HGShadingStateSystem`: `0x1810afc80` constructs it and
   `0x1810aeea0` initializes its `+0x28` hash table, whose finalizer access is
   0x60-stride. Root `+0xa0` is `HGGeometrySystem`: `0x181091dc0` constructs
   it and `0x1810914a0` initializes the matching 0x38-stride table. Root
   construction injects them into HGMesh manager `+0x50/+0x58`, closing the
   subsystem-to-manager-to-job-to-finalizer transport. The M0 producer is now
   closed: `0x1810b9990` performs material-handle lookup/insertion, clears a
   new 0x60-byte entry, and calls `0x18109c9d0` once at `0x1810b9c5c`. That
   core repeats the M0 `+0x28/+0x40/+0x44` hash lookup and writes its native
   material/shading-state object to `entry+0x28` at `0x18109ca2f`; it then
   dereferences the same object through `+0x10` and material state fields. The
   two direct insertion callers are `0x1811e1a24` and `0x18131b76b`.
   `GetOrCreatePerMaterialCBHandle` is therefore a downstream consumer. The
   next producer boundary is M1 concrete entry population plus a Li-specific
   M0 handle/object join; until that join, Li's `D+0x450` mode stays
   fail-closed.
   All six selected materials have `_IsSceneEffect=0` and
   `_EnableTransparentMV=0`, so `_VFXParams1` and transform history are safely
   bypassed rather than guessed. Exact inverse-VP soft depth, live
   root-signature/PSO, and renderer-list survivor identity remain missing.
   `HG_ENABLE_MV` remains an
   implicit compiled keyword, not a serialized material keyword.
   The missing PTS-40000 peak-effect source boundary is now materially
   narrower. Exact filtered AnimeStudio exports for
   `P_fxui_lizhiyan_overview_start_04`, `_04_1`, and `_04_2` recover 17
   GameObjects/Transforms, 14 ParticleSystems, 14 ParticleSystemRenderers,
   eight VFXBaseV2 materials, three distinct Mesh PathIDs, and 13 unique
   non-null texture PathIDs with no per-object export errors. All 13 texture
   identities resolve uniquely through the installed AssetMap and convert to
   PNG; the three meshes convert to OBJ, including two same-named
   `S_fx_lzy_xishou_01` objects that remain distinct by CAB and PathID. The
   recovered 35.4 MB shader source preserves exact
   `HGRP/Effect/VFXBaseV2` identity, while the selected DXBC variant and live
   draw state remain closed. A deterministic source contract now records the
   three hierarchies, particle modules, renderer-to-material/mesh ownership,
   material queues, texture bindings, hashes, and the fail-closed execution
   boundary. `p_shoulizi (9)` has a source-null Mesh and is intentionally a
   billboard/default-geometry particle, not an unresolved mesh. The remaining
   MonoScript edge is `Beyond.Gameplay.EffectSetting` from
   `Gameplay.Beyond.dll`; its absence does not block manual diagnostic
   particle sampling, but retail activation/LOD behavior cannot be claimed.
   The contract now materializes three source-identity Unity particle prefabs,
   14 renderer/module pairs, eight fail-closed source materials plus diagnostic
   SampleStack variants, three PathID-distinct meshes, and 13 textures. Filtered
   GameObject JSON omits `m_IsActive`, so the manual diagnostic explicitly
   defaults those nodes active without claiming retail `EffectSetting` or
   `EffectLodCfg` activation. Command-line ParticleSystemRenderer submission is
   blank for the paused sampled buffer; the capture therefore uses Unity
   `BakeMesh` billboard expansion, preserves source material queues, supplies
   the recovered pipeline's exposure/global gates, and keeps this transport
   named in the manifest. At PTS 40000, 26 particles are alive, the peak-only
   frame contains 15,962 non-background pixels and 4.548% `broadTeal`
   coverage, and actor-composed coverage rises to 7.572% versus 21.699%
   retail. The independently validated run remains predicate-only and
   diagnostic: native VFXBaseV2 variant/descriptor/PSO, exact activation/LOD,
   renderer-list survivor, after-DOF ownership, and final compositing are still
   open, so `visibleAdmission` stays false.
   All 12 controller requests are preserved; the other 11
   remain explicitly unbound. Its `38-47 s` retail slot, especially the
   hand-adjacent teal layer near 40 seconds, is the current strongest visual
   acceptance window, but native bytes do not identify a draw. Visible
   admission no longer lacks specialization identity or static scheduling;
   it still requires the retail live descriptor table/root signature, PSO
   overrides, renderer-list survivors/order, physical MRT/depth handles, and
   final compositing contract.
   Wulfa `bishou_wind3` is next after that boundary because its visible
   purple/red wind trail mixes VFXRefract and VFXBaseV2 families.
6. Add controller, grounding, facial, FX, and secondary systems behind
   source-validated fail-closed gates.
7. Upgrade representative non-playable families before broad parity claims.
