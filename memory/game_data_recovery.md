# Game-data recovery

## Current status

The project can read the current exported tables, MemoryPack/FlatBuffer payloads,
selected Unity objects, Wwise banks, Lua, IL2CPP metadata, and bounded native
code paths. These sources feed Story, Characters, Gameplay, Audio, Assets, and
the local evidence graph.

The strongest recovered semantics cover stock-client combat formulas, skill and
buff action structures, enemy level points, projectile records, audio Event
graphs and consumers, and typed joins between gameplay records and assets.
Server behavior, active IFix replacements, live blackboard values, and runtime
branch selection remain outside the proven boundary unless separately captured.

## Refresh

```bat
.\export.bat --from-game
.\export.bat --from-game --with-assets
python scripts\build_gameplay.py
python scripts\build_audio.py
python tools\endfield_source_graph.py build
```

Steps using installed native binaries validate `GameAssembly.dll` and
`global-metadata.dat` against their recorded fingerprints. Missing or mismatched
inputs skip only the affected native step and leave its previous report
untouched. Set `ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1` for a hard audit gate.

## Evidence rules

Prefer, in order:

1. exact table keys, serialized fields, and versioned binary layouts;
2. source-scoped PathID/PPtr and authored foreign-key relations;
3. typed IL2CPP fields and fingerprint-locked native data flow;
4. exact hashes and normalized identifiers with a documented namespace;
5. labeled name or token similarity.

Never treat a global PathID, filename resemblance, native address order, or one
same-name asset as unique ownership. Preserve source layer, container, offset,
schema version, and validation status.

Map streaming recovery preserves exact InitChunkData entity ids, names,
transforms, and observed ECS component columns. The validated schema exposes no
known prefab Source+PathID/hash field, so names, positions, meshes, and basename
similarity never establish prefab-to-level ownership. The next gap is an exact
StreamingChunkData or component identity joined to a unique AssetMap row.

## Known data model

- StreamingAssets and Persistent table layers must be merged according to each
  dataset’s overlay contract; selecting the first matching file can lose patch
  rows.
- MemoryPack and FlatBuffer parsers are versioned by observed member/layout
  counts and fail visibly on drift.
- SkillData resolves phased actions, DamageUnits, targeting, child skills, and
  authored timing where decoded.
- BuffData composes modifiers, shields, tags, stacking, events, actions, and
  child buffs. Undecoded nested bodies remain byte-bounded diagnostics.
- `GameplayTagPredefineTable.json` is a current-build exact registry for 175
  predefined tag names, plus named predefined queries and immunity contexts.
  Its signed `Int32` ids normalize to the same unsigned-hex form used by
  BuffData `applyTags`. The serialized `GameplayTagConfig` objects in the
  AnimeStudio object index provide additional full tag paths; their IDs match
  CRC32 of the UTF-8 path against the predefined table, so this is an
  evidence-backed join rather than a Buff-name guess. The Gameplay builder
  keeps both sources and never replaces raw ids. The current object-index
  snapshot matches 26 current-build config objects and 2,577 serialized tag
  paths, yielding 2,536 config IDs (2,584 unique IDs after merging the
  predefined table). IDs absent from that serialized registry are published
  with `unresolvedReason=not-in-current-serialized-gameplay-tag-config` rather
  than being inferred from a Buff name; a context-only match may still retain
  its exact immunity/query context. One additional static recovery is now
  enabled: when a `Status/Immobilized/<suffix>` or
  `Status/Unmovable/<suffix>` context contains the CRC32 of
  `Immune/<suffix>`, the missing name is labeled `exact-context-derived` and
  the proof context is retained. This currently recovers `0x1a17c9aa` as
  `Immune/BlowOff`, and the exact enemy-infliction context similarly recovers
  `0xcd587d66` as `Immune/SpellInflictOnChar/CrystInflictOnChar`.
  Arbitrary Buff-name candidates such as `EnemyCate/Settlement` remain
  unresolved until an equivalent source proof is found.
  If a current build still has unresolved applied-tag IDs, the maintained
  `scripts.gameplay_builder.capture_runtime_tags` Frida capture can observe
  `GameplayTag` request/name and config-build calls while the installed client
  starts. Its JSONL is not consumed implicitly: pass it explicitly to
  `build_gameplay.py --runtime-tag-capture`. The capture and loader both fail
  closed on the selected build's `GameAssembly.dll` and `global-metadata.dat`
  hashes, and runtime-only names are labeled `exact-runtime` rather than
  replacing serialized evidence. The hook manifest and agent are the durable
  build-specific contract; capture inventories stay under `scratch/`.
- The active Gameplay Buff catalog now decodes the exact post-id lifecycle,
  stacking, trigger interval, and trigger-count tail for referenced rows. A
  unique keyed `duration` value may be surfaced as a schema-ordered anchor;
  other keyed pre-id BlackboardDouble values remain exact numbers with their
  owning nested action unresolved. When `abilityEventAction` is empty, the
  pre-id prefix is also exact through `addingCooldown`, packed `applyTags`, and
  `AttributeModifierData`; attribute, formula, and target-scope names are
  attached only from the gated current native enums. Non-empty action lists
  are published only when every map, sequence, and union item is consumed to
  an exact boundary. The AbilityAction union ids and member counts come from
  the selected current formatter registration rather than a previous-build
  ordinal table. Current consumed families cover skill-id/cooldown operations,
  super-armor and damage-decoration conditions, main-character checks, timed
  markers, effects, CreateBuff/FinishBuff, selectors, and bounded DamageAction
  payloads. Unsupported unions still stop after the exact list count rather
  than accepting a guessed boundary. When an authored Buff id also occurs
  inside its own action body, the pre-id decoder uses the post-tail-validated
  top-level id marker instead of the first matching string. The current exact
  consumers also cover Buff-id/stack/HP/poise/damage/tag/distance conditions,
  global cooldowns, resource changes, skill casts, blackboard transfers and
  calculations, advanced Buff removal, and interactive coin creation. Common
  TargetSettings envelopes now also expose their 13 typed selector,
  owner/target, context-key, and target-group fields; unknown nested selector
  subtypes still fall back to the bounded raw envelope. The remaining
  ModifyDynamicBlackboard operation names are now mapped from the current
  native enum (Assign, Add, Multiply, Divide, Floor, Ceil, RoundToInt), and
  its declared calculation type is HpRatio; unknown future enum values remain
  fail-closed. ConvertToTargetContext operation and translation-rotation names
  are likewise attached from the current native enums when that action is
  encountered. CompareFloat now exposes the current Beyond.CompareType name
  (LT, LE, GT, GE, Equals) and is rendered as a visible exact action.
  SimpleCalcBBAction reuses the same named operation enum, so its display no
  longer assumes division. The remaining
  SpellInfliction uses the current EnergyShardType names (Fire, Pulse, Cryst,
  Natural, Enum) whenever that action is present. The remaining high-value
  boundary is concentrated in large entity-spawn, projectile,
  heal-calculation, DamageUnit, EffectActionCfg, and complex selector/config
  payloads rather than additional fieldless or primitive-only action families.
- Exact gameplay IDs prove ownership only in their authored namespace. Family,
  filename, animation, or prefix joins remain inferred.
- Legacy broad indexes under `webui/data/game_data/` are diagnostic previews,
  not active page or formula sources.

## Enemy stats and variants

Enemy level values come from exact authored rows in
`EnemyAttributeTemplateTable.levelDependentAttributes`. The WebUI shows only
levels present in source data; it does not infer a level from row position or
interpolate missing points.

Each enemy variant names an `attrTemplateId`. Variants sharing a template share
its raw HP/ATK/DEF curve, but may still differ through modifiers, born buffs,
AI, models, and other configuration. Shared displayed stats do not imply
identical live behavior.

`EnemyTable.attrModifiers` carries authored values plus `ModifierType` and
`ModifyAttributeType`. Their names are read from the explicitly selected,
gated IL2CPP metadata. The runtime `Attributes` path includes other active
modifiers and an IFix branch, so the WebUI reports base points and modifier
inputs without claiming a reconstructed final enemy value.

## Combat formula boundary

For the shipped stock client, ordinary damage has the recovered shape:

```text
finalAttackValue
* weaknessDamageScalar
* criticalFactor
* defenseFactor
* (1 - shelterDamageScalar)
* max(0, elementalResistanceFactor)
* abnormalStatusFactor
* physicalInflictionFactor
```

Critical success uses `1 + CriticalDamageIncrease`. With the shipped
`efficiencyOfDEF = 0.01`, defense is:

```text
DEF >= 0: 1 / (1 + 0.01 * DEF)
DEF < 0:  2 - 0.99 ^ (-DEF)
```

For ordinary elemental types, the resistance term is
`(1 - resistance / 100) * typeDamageTakenScalar`. Real damage uses neutral
defense and elemental factors but still traverses other ordinary multipliers.
LifeDrain is a distinct early-return path using `finalAttackValue`.

DamageUnits, zones, modifiers, abnormal/physical infliction decorators, guard,
healing, shields, poise, and event processors add typed behavior outside this
single scalar. The browser must show their authored phase and conditions rather
than presenting the scalar as a complete combat simulator.

These conclusions describe the fingerprinted stock binary plus shipped tables.
They do not prove active IFix/server corrections, live target selection,
probability outcomes, evaluator order, or blackboard values.

## Projectiles and effects

Projectile records preserve template identity, movement, effects, hit behavior,
sound IDs, and source identity where decoded. A projectile template’s skill
bundle describes behavior owned by that template; it does not prove which
playable skill spawns it. A ranged-looking skill may use direct actions,
hitboxes, summons, or another system and need no projectile template.

Nonzero projectile sound values are direct Wwise Event IDs. HIRC traversal can
link possible media leaves, but switch/random/layer selection and actual
playback remain unobserved.

## Audio evidence

The audio pipeline separates:

- raw Wwise Event, Action, container, Sound, and media identity;
- exact Event-to-media graph relations;
- authored contexts from tables, Timeline, Lua, gameplay data, serialized
  components, and native consumers;
- runtime activation, selected branch, and heard media.

Wwise Event traversal proves possible library output, not a live caller or
audibility. Managed literals and lookup keys remain identity-only until exact
data flow reaches a typed playback API. Conditional and selector-based native
paths preserve their branch condition, method, callsite, target binding, and
binary fingerprints.
Scene-background recovery now has a fail-closed static catalog in
`webui/data/lang/CN/audio/scene_backgrounds.json`. It consumes the real
AnimeStudio AssetMap object root in one bounded streaming pass and uses exact
AssetMap `Source` + `PathID` identities when joining authored objects. Prefab-
local containment and scene-asset candidates are retained as separate evidence;
only unique containment with an authoritative scene ID is promoted to scene
ownership. Missing, malformed, or unreadable AssetMap input fails closed.
`AudioMapData._sceneNames`, `AudioLevel` rows, scene-emitter component fields,
and `MissionRuntimeAsset.acceptMode.levelId` still describe authored source
data. The current scene-emitter evidence is therefore a source prefab
definition, not a recovered level instance. Recovering placed scene instances
requires a structured scene-streaming/instance-relation join. The catalog does
not infer runtime scene activation, current State/RTPC values, selector choice,
listener state, playback, or audibility.
The durable scene-emitter blocker is now explicit: the validated offline
sidecars and object index prove authored prefab-local emitter definitions but
do not provide a placed scene-instance relation. Compact status projection
therefore stays prefabLocalSceneUnresolved with unavailablePrefabIdentity; no
scene ID may come from candidate paths, levelId-only rows, GameObject names,
positions, or Meshes. Recovery remains queued behind a future exact
SceneAsset/Level containment or prefab Source+PathID-to-level join. When an
explicit component-identity route and an exact prefab-path route disagree,
reconciliation fails closed with `conflictingPrefabInstanceIdentityJoins`.
The current streaming sidecars still do not produce the required prefab
Source+PathID, so the next step is exporter/sidecar production of that exact
identity, not more filename/path inference.
Scene-global Event compact attribution is emitted only after every direct
scene-global context validates its source/owner shape, exact evidence, runtime
boundary statuses, and membership in the merged catalog scene set. It retains
all scene IDs and original semantic-role field names; partial, malformed,
non-direct, truncated, or out-of-catalog contexts fail closed with bounded
diagnostics and do not change Event category or `foundInWwise` status.
Where the authored scene/Event join is available, the catalog still traverses
matching Wwise Events to possible media leaves. For c35, the mission metadata
selects `map01_lv001`; `map01_audio` names that scene, and its outdoor room-tone
Event `0x7ac43e5e` reaches shared media `593335165`. The separately decoded
`955778167792087661` asset is `au_voice_c35m3_3_001`, an external voice/path
identity rather than that room-tone Event or media. These examples remain
authored identity/possible-media evidence, not placed-instance or playback
proof.
RemoteCommon lifecycle recovery now uses an exact Persistent-over-Streaming
row overlay for non-empty `startAudioEvent`/`endAudioEvent` fields. `voiceId`
remains a separate dialogue identity, and the authored lifecycle request does
not prove runtime execution or a playable media leaf.
Decoded media now carries a separate coarse-ownership projection from exact
scene roles, Event contexts, component fields, and recovered external paths.
Outdoor room-tone and authored ambient-emitter leaves can be classified as
ambience; generic scene emitters retain scene-object ownership without a
guessed SFX/music category. `955778167792087661` therefore has mission-
narration ownership while its concrete trigger and playback placement remain
unknown.
Serialized `monoBehaviourAudioIdField` rows now retain the raw serialized path
and field spelling while `audio_semantics.managed_literals` projects only a
narrow authored role: sound spawn/finish, hit/start/rotation/enable callbacks,
animation-state audio config, particle and water fields, or the generic
serialized-field boundary (with an audio-key hint). `componentLayout`, component
type, and exact existing GameObject placement are separate evidence fields.
These projections do not imply component execution, Event posting, selected
Wwise media, or audibility; generated stats carry role/layout/Event coverage.
Character audio naming is a second exact ownership boundary. A delimited
current `CharacterTable` key inside a Wwise Event id assigns that authored
namespace to the character; a shortened `chr_NNNN_*` form is accepted only
when the numeric id is unique in the same table. An Event-leading internal
token such as `lastrite_*`, `lizhiyan_*`, or `pograni_*` is accepted only when
it has one exact table owner. Possible media inherit the complete named-
character set, so cross-character Wwise leaf reuse stays explicit. This does
not identify an action, runtime caller, selected leaf, playback position, or
audibility, and generic `chr_*` templates remain unowned.
Serialized AnimationClip audio callbacks are independently sufficient to link
an Event to the exact clips and character/enemy owner recorded by the callback
context. The Event and clip names need not match. AnimatorController membership
is retained when recovered, but execution, callback timing, Wwise selection,
audibility, and SFX category remain separate evidence.
The callback identity surface is built from a fail-closed CharacterTable,
EnemyTable, and EnemyTemplateTable overlay. Persistent rows are authoritative;
a malformed Persistent layer does not fall back to the StreamingAssets identity
surface. Each supported Clip keeps exact resolved entity IDs separate from
candidate IDs: exact table owners can resolve, while unique-token or multi-match
identities remain candidate/ambiguous. Multiple authored callback owners remain
shared, and missing, malformed, or unsupported identity evidence remains
unresolved. This is static table/callback evidence only, not Animator execution,
callback timing, selected Wwise media, playback, or audibility.
The same static callback path can recover an NPC owner without treating it as a
playable CharacterTable row: one `NpcInfoTable` row must provide identical
non-empty `voActor` and `wwiseId`, and its `npcId`/`templateId` must agree with
`NpcTemplateGroupTable` `npcNameId`/`templateId` in the current overlays. The
same token must also be a unique exact `AudioDialogChannel` key with matching
typed narrating/radio Event suffixes. The published identity is `ownerKind=npc`
plus NPC id, template id, and actor token.
Duplicate tokens, conflicting or malformed overlays, and template mismatches
fail closed; generic archetypes remain unresolved. A mixed Event keeps a valid
NPC identity only at occurrence/Clip level. This still does not prove Animator
execution, playback, media selection, or audibility.
Animation action names provide another bounded ownership route. A normalized
AnimationClip name may classify an unknown Wwise Event as action SFX only when
the same clip already carries a supported `PostAudioEvent` callback for that
Event. `wulfa_relax_sp_02`, for example, matches
`A_actor_wulfa_relax_sp_02` and retains `chr_0028_wulfa` as the recovered
animation owner. Similar names without an exact callback-backed match remain
unknown; live Animator execution and the selected Wwise leaf are not inferred.
`AudioCueTable` `behaviourExpr` and `conditionExpr` trees are serialized,
validated, bounded AST evidence rather than an evaluator. The projection keeps
the complete tree's cue/handler scope, expression side, source path,
parent/depth, `exprType`, four scalar fields, child paths, node class, and
bounded diagnostics. A non-empty behavior `exprType=3` string leaf is an
authored Event request; a non-empty `exprType=8` string leaf is a
`runtimeCueVariable`; non-empty children are `compositeOpaque`; all other
nodes remain opaque. The selected native `EAudioExprType` and operator names
are published only after the exact `global-metadata.dat` + `GameAssembly.dll`
hash gate validates; missing or mismatched native inputs leave those names
absent. `childrenLimit` rejects the parent before any child projection.
Handler evaluation and its indirect dispatch/callback boundary remain separate
`AudioCueSystem` evidence: serialized expressions do not prove handler
selection, condition truth, runtime variable values or mutation, cue
invocation, Event execution, branch selection, or audibility.
When a hash-only Event has a complete final-media leaf set identical to authored
Events whose broad category agrees, the projection recovers that category for
85 rows (56 SFX, 21 UI, 6 voice, 2 control). This is library-output evidence
only; caller, trigger, branch selection, and runtime purpose remain unresolved.
Separate name-pattern evidence now covers 954 named Events (enemy, actor/UI,
LevelSequence, and Gameplay-SFX families). Where an enemy name also has an
exact voice context, the voice evidence wins while the weak name evidence stays
recorded.
The Timeline and voice string+callback callers now have an additional exact
native join: a current-build helper preserves the event name/object/callback
arguments, computes the Wwise event id, and tail-enters the existing
`AudioAdapter._PostEvent` preparation path. The helper is absent from both the
ordinary and generic IL2CPP method-pointer catalogs, so the model records it as
an unnamed native entry point rather than inventing a managed owner. Its exact
address, build fingerprint, and decoded body are kept in the versioned audio
recovery report and runtime contract.
The voice response path adds a second static join into the external-source
route: an unnamed helper validates the voice Event/path context, prepares the
external callback payload, and calls the named `PostEventExternal` bridge with
the recovered callback mask before external-source cleanup. A preceding helper
resolves a voice-dependent external-source key/path into an out slot. The same
native target is shared by VoiceI18n and VFS path callers, so it is not
promoted to an AudioObject-specific name; neither helper is assigned a guessed
managed owner, and neither proves a live voice request.
The external route is now closed through Wwise's typed external-source post:
the bridge creates one `AkExternalSourceInfo` entry (cookie, file key, codec),
wraps the temporary playing mapping in an `EventCallbackPackage`, posts with
one external source, and routes EndOfEvent through the user callback before
removing the playing mapping and releasing the temporary audio object. This is
still static argument/cleanup evidence; it does not prove a live request or
the selected external file.
The durable static closure now spans the VoicePlayer external key and
descriptor through native manager retention, provider preparation, file/read
transport, and decoder/PCM conversion. It remains a possible transport chain,
not a per-request runtime identity. The importer fails closed: without one
complete hash-verified capture session it publishes no `nativePairing`, even
when isolated keys, paths, pointers, handles, or decoder records overlap.
ModelView normal audio is separately authored when a non-custom normal behavior
(`behaviorTag=0x0001`) has a nonzero `normalAudioId`; its controller,
model/layer/state chain, and `behaviorTime` are retained. The fingerprint-locked
`AudioBehavior.Execute` → `AudioManager.PostEvent` route is static evidence
only; state entry, execution, selected branch, and audibility remain unobserved.
Positioned ModelView audio (`behaviorTag=0x0002`) has three stable authored
branches. For the direct-position event with nonzero `normalAudioId`, the
`PlaySoundAtPosition` endpoints and the `m_audioHandle` store are independently
statically audited; those facts do not prove one runtime call chain. Custom and
entity forms remain control-only, and `_SwitchState` has no recovered playback
sink. The managed `PostAndForget` → `AudioAdapter._PostEvent` route is
statically verified through the managed internal playing id, Adapter guards,
and the `LoadBank`/`PrepareEvent` boundary. The runtime completion delegate,
final `AkSoundEngine.PostEvent`/native playing-id handoff, Wwise selection,
execution, and audibility remain unresolved.
The selected `GameAssembly.dll` body also exposes the native call frame:
`AkSoundEngine.PostEvent` receives `eventId`, `audioObjectId`, callback flags,
callback pointer, cookie, `cExternals=1`, the external-source array, and a null
playing-id out pointer. The call goes through the lazily resolved Wwise wrapper
at `0x183abeee0`; operation-4 manager callbacks later forward the descriptor's
cookie, codec, key pointer, and auxiliary field. The unresolved boundary is
therefore downstream descriptor/codec consumption, not whether the managed
codec reaches a one-element native external-source post. See
`reports/story/recovery/audio/managed_external_source_argument_flow.md`.
The managed boundary is also separated from the helper naming: the metadata
mapped `VoicePlayer._PlayExternal` body and the unnamed helper entered directly
by `_PlayVoice` are sibling current-build bodies, and both preserve the
resolved key/event/object/callback/codec state into the same named
`PostEventExternal` overload. The remaining identity gap starts after that
managed argument propagation, at native descriptor/source-state selection.
The callback queue boundary is separate from the native source-manager resolver
queue: the managed Wwise pump constructs typed callback-info objects and invokes
the stored event-package delegate, while the external adapter callback receives
its mapping cookie and callback info rather than the resolver descriptor,
UTF-16 source path, or codec. The exact queue/dispatch disassembly is kept in
`reports/story/recovery/audio/unmapped_string_callback_helper_gameassembly.md`;
the importer now exposes `managedExternalCallbackChains` when a capture's
parent chain includes both managed Wwise pump and callback-info dispatch. This
remains callback-delivery evidence and does not replace a live request capture
or a key-to-file/decoder/PCM join.
The native resolver pointer is also statically bounded: external `PostEvent`
wrapper `0x1800285d0` supplies fixed bridge `0x180002da0`, which reaches manager
entry `+0x50` through the shared registration wrappers. Its operation `0x10`
lookup branch is a no-op, while operation `0x20` queues a callback record; the
bridge does not itself select a UTF-16 path or perform file I/O. The remaining
static gap is the runtime identity between sourceInfo/provider state and the
copied external descriptor, followed by open/read/decode/PCM evidence.
The current build-specific Frida audio manifest passes its explicit native
hash gate, but a live capture in this session could not reach the hook: direct
`Endfield.exe` launch and the official Hypergryph Launcher entry point both
failed to create an `Endfield.exe` process before the bounded wait expired.
No runtime event stream was emitted, so this is an environment/startup
boundary rather than negative playback evidence; the external-key-to-file,
decoder, and PCM join remains the highest-value recovery gap.
The installed tree has no matching PDB or separate `AkOpus`/`Vorbis` codec DLL;
the selected `AkSoundEngine.dll` is the only Wwise engine binary, so the
remaining codec consumer must be an imported/runtime-computed target in this
engine or a callback crossing into GameAssembly.
The current `VoiceContext` layout also closes the request-input side: `+0x18`
is the audio-object id, `+0x20` the Wwise Event, and the inline
`RuntimeVoiceData` block at `+0x48` supplies the localized `data` key at
`+0x60` and codec at `+0x68` (with dev-stage and speaker-channel fields at
`+0x4c`/`+0x50`). `_PlayVoice` resolves that `data` key, then passes the
resolved external key, Event, object id, handle id, and codec into the external
route. The offsets are current-build evidence retained in the audio recovery
report, not a portable ABI.
The previously unnamed resolver target is now understood as shared formatter
`0x182f25040`: it activates a per-language temporary slot, expands UTF-16
`{...}` placeholders through a manager callback, allocates/copies the resulting
managed string, and releases the temporary slot. `VoicePlayer`'s helper
`0x183abe750` forwards `VoiceContext.voiceData.data` into this formatter and
passes the returned string as `PostEventExternal.externalSourceKey`; the same
formatter is called by `VoiceI18n.GetVoicePath`/`GetDebugVoicePath` at
`0x186b02b1c`/`0x186b0296c` (method-pointer order verified from the current
CodeGenModule map; the method/cctor evidence is consolidated in
`reports/story/recovery/audio/voice_i18n_method_pointer_and_cctor.md`) and by
VFS path helpers. The current metadata-usage decoder recovers the exact normal
arguments `{0}/{1}/{2}`, `Voice`, `s_languagePrefix`, and the input path, so
the native candidate is `Voice/<Chinese|English|Japanese|Korean>/<path>`.
The actual VoicePlayer resolver `0x183abe750` loads the current
`VoiceI18n` metadata type and its static `+0x10` language prefix, then calls
the formatter with `rcx=format`, `rdx=Voice`, `r8=s_languagePrefix`, and
`r9=VoiceContext.voiceData.data`. Thus the normal external-source key is
statically closed as `Voice/<language>/<VoiceData.path>` at the playback entry,
not only at the standalone `GetVoicePath` helper.
Debug stage 1 selects `RawBuildVoice`; stage 2 strips
`^v\d+d\d+(d\d+)?/` with `System.String.Empty` and selects
`PlaceholderVoice`; other non-formal stages use `Voice`.
The formatter does not itself open a PCK, read media bytes, decode PCM, or
post to Wwise. Thus static evidence now closes the key/path construction layer:
`_PostEventWithExternalSource` forwards that same value directly to
`AkExternalSourceInfo.set_szFile` before native descriptor copying. The actual
file open/read, live external-source callback, decoder buffer, and audibility
remain separate evidence gaps. The static constructor pins the default
language to `Chinese` and `s_currentLanguage=0`; WebUI `CN`/`EN`/`JP`/`KR` and
`voice/<language>/*.flac` paths remain derived aliases rather than native-key
evidence.
The selected metadata also gives an exact native-descriptor codec boundary:
`Beyond.Audio.AudioCodec` has
`PCM=-1`, `ADPCM=1`, `VORBIS=2`, `ATRAC9=6`, and `OPUS_WEM=10`. In the current
`_PostEventWithExternalSource` body, the eighth stack argument (`codec`) is
loaded unchanged at `GameAssembly.dll+0x3abeb69` and passed as the value
argument to `AkExternalSourceInfo.set_idCodec` (`0x183abe9c0`). The same-build
`AkSoundEngine` constants instead expose `AKCODECID_PCM=1`,
`AKCODECID_VORBIS=4`, `AKCODECID_ATRAC9=12`, and
`AKCODECID_AKOPUS_WEM=20`. The setter's resolved AkSoundEngine export is
`CSharp_ada48f7e7181c770` at RVA `0x335c0`, which jumps to `0x180006050` and
stores `edx` directly at native descriptor `+0x04`; there is no conversion in
the setter/PInvoke target. Therefore the managed enum values are the raw
values written into this build's external-source descriptor. The downstream
native interpretation of those raw Beyond values, and why the public
`AKCODECID_*` constants differ, remains an unresolved consumer-level question;
the two domains must not be equated.
The serialized `StreamingAssets/Table/AudioDialog.json` voice rows currently
carry codec values `4` and `20`, which numerically match the native Vorbis and
Opus-WEM constants. The selected build now closes the intervening read path:
`RuntimeVoiceData.FromSparkBuffer` calls the shared SparkBuffer integer reader
with serialized offset `0x14`, and `VoiceData.get_codec` is the same raw
`Int32` getter (`mov edx, 0x14` into that reader); `FromSparkBuffer` copies the
returned `eax` into the runtime value's codec slot without arithmetic or enum
conversion. Therefore the census is no longer merely source-table evidence:
the serialized `VoiceData.codec -> RuntimeVoiceData.codec` edge is raw integer
propagation. The table row's field name/schema agrees with this serialized
field. The selected build now also joins `Tables.get_audioDialog`,
`LoadAllSync -> LoadTableSync`, the resource/path lookup, virtual table
`Load`, and the shared `JsonTable<T>.Load` JSON-deserialization body to the
concrete `AudioDialog` map/config methods. The exact generic row-iteration
handoff is still deliberately unclaimed; see
`reports/story/recovery/audio/audio_dialog_table_loader_flow.md`. The managed
handoff is typed: the installed runtime table resolves both
`RuntimeVoiceData.codec` (type index `122666`) and
`_PostEventWithExternalSource.codec` (type index `122667`) to
`Beyond.Audio.AudioCodec`. The native consumer interpretation of descriptor
`+0x04` remains unresolved. The pinned row census is kept in
`reports/story/recovery/audio/codec_enum_and_native_id_boundary.md`.
The adjacent sourceInfo/provider path is a separate metadata domain, not a
codec conversion. In `0x1801af7a0`, the non-flag-9 fallback copies
`sourceInfo +0x04` into a local provider descriptor `+0x08`; `0x1800b8eb0`
copies that field to provider `+0xb8`, and provider stream helpers use `+0xb8`
as a byte-position/stream-bound value. The managed `idCodec` remains in the
copied external-source record payload (`+0x04`, record `+0x0c` relative to the
list base). No static dataflow joins these fields to a decoder-selection
branch, so neither field may be relabeled as the other without runtime
evidence.
The selected native copy path now narrows that boundary further: the managed
descriptor's `+0x04` is retained unchanged in the copied record's `+0x0c`,
while manager registration keeps the descriptor allocation, source-list
identity, callback, and callback cookie separately. The inspected copy,
in-memory RIFF validation, manager lookup/callback/teardown, and provider
preparation paths do not interpret the copied `+0x0c`. This is a negative
boundary only, not proof that the codec is unused; the concrete decoder
selection or native codec callback still needs runtime or deeper indirect-call
evidence.
The manager's separate operation-4 dispatchers (`0x1800e2120` and
`0x1800e2240`) copy incoming descriptor fields, including the input `+0x04`,
into a callback payload and invoke the registered callback; the fixed bridge
`0x180002ea3` only serializes that payload into the callback queue. A complete
executable-section scan of the selected `AkSoundEngine.dll` found no direct
scalar read of the external descriptor's `+0x04` (or a local pointer adjusted
by four) outside generic callback-record serialization. This strengthens the
negative consumer boundary while preserving the possibility of an indirect
callback/other-module consumer. The exact forwarding and scan are kept in
`reports/story/recovery/audio/native_manager_callback_payload_and_codec_scan.md`.
A bounded `.pdata`/direct-call traversal of the selected registration,
manager, provider, and decoder roots reaches 66 functions (depth five) but
still finds no direct path that reads that descriptor field in decoder setup;
provider `sourceInfo +0x04` and RIFF/Opus header reads remain separate layouts.
Vtable and callback targets remain unresolved, so runtime capture is still the
authoritative next step for the codec-to-decoder join.
The same build's `AudioLang` enum is `Chinese=0`, `English=1`, `Japanese=2`,
and `Korean=3`; `GetLanguageName` performs a metadata-backed indexed lookup
into that language table before storing `s_languagePrefix`, while
`VFSDefine.GetAudioLangPath` has a separate four-branch `AudioChinese` /
`AudioEnglish` / `AudioJapanese` / `AudioKorean` selector. This narrows the
native language segment and audio-PCK naming without promoting WebUI `CN` /
`EN` / `JP` / `KR` aliases to native-path evidence. See
`reports/story/recovery/audio/voice_i18n_method_pointer_and_cctor.md` for the
build-pinned method and default-value evidence.
The serialized voice input is now joined to that key without a guessed table
mapping: the three voice entry paths (`VoiceManager._Speak`,
`_SpeakNarrative`, and sequence-sentence playback) all call
`RuntimeVoiceData.FromSparkBuffer`. Its typed getter sequence reads
`VoiceData.path` at serialized offset `0x24` and places it in the
`RuntimeVoiceData.data` slot, while `overrideWwiseEvent` is read separately at
`0x20`; the same getter sequence reads `VoiceData.codec` at serialized offset
`0x14` into `RuntimeVoiceData.codec`. The codec read is a raw `Int32` copy, not
a numeric conversion. Runtime type resolution confirms that the destination
field and later adapter parameter are both `Beyond.Audio.AudioCodec`; only the
native descriptor consumer remains unresolved. The metadata field order and
the 0x40-byte value copy make the path/event roles distinct.
The selected-build addresses and method tokens are kept in
`reports/story/recovery/audio/runtime_voice_data_path_flow.md`. This closes
`VoiceData` SparkBuffer → runtime `data` provenance and the VoiceI18n template
join, but not any native file/decoder observation.
LevelScript voice is a separate, more direct selection route: the recovered
`PlayVoice`/`PlayVoiceNarrative` records use their constant `_voId` as an
`AudioDialog` path stem, rather than selecting a Wwise Event. The current CN
`webui/data/lang/CN/audio/trigger_contexts.json` index contains four such rows;
all four join an exact decoded
`AudioDialog` media file and mark Wwise Event evidence as `notApplicable`.
This closes the serialized selection and decoded-media join for those rows,
while level-script action execution and runtime playback are still unobserved.
LevelScript audio actions remain keyed by validated union tags/member shapes and
retain durable authored fields: `PlayAudiAtPosition.key`, `PlayAudio.key`,
`PlayAudioAndWait.eventName`, `PlayAudioOnTarget.audioKey`,
`PlayStandaloneMusic.startEvent`/`stopEvent`,
`PostAudioStatusEvent.statusEnterEvent`/`statusExitEvent`,
`PostMusicEvent.musicEvent`/`musicEventOnRelease`, and
`PostAudioCue`/`PostAudioCueOnRelease.name`. Lifecycle fields are
`PlayAudio.audioPlayingId`, `PlayVoice`/`PlayVoiceNarrative.voiceHandle`,
`BlockAutoMusicChange.blockHandle`, and
`PostAudioCue`/`PostAudioCueOnRelease.cueHandlerId`, consumed by
`StopAudio.audioId`, `StopVoice.voiceHandle`, and
`BlockAutoMusicChangeCancel.blockHandle`. A lifecycle producer requires an
explicit serialized output path (`ParamSource=0`), while a consumer requires
an explicit dynamic path; a join additionally requires the exact same
LevelScript, source root, source path, lifecycle kind, and output path with one
active final serialized slot. `ParamSource=100` is a runtime lookup and does
not create a static handle; property and unknown sources remain unresolved.
Producer-only rows remain producer-only, so this closes authored handle
topology rather than live handle values, state, or execution.
The native action topology is local static control flow: event roots are
independently invoked listeners and are not sorted into chronology. Physical
list order and listener priority are not Story or runtime execution order; only
an explicit serialized edge within one LevelScript supplies a static next
relation, and the serialized action ordinal identifies its authored slot.
The serialized Wwise side now supplies an exact cookie join for this route:
the current CN v150 HIRC corpus has 1,712 `Wwise External Source`
(`pluginId=0x00080001`) source records, all with `sourceId=0x24db9834`, and
the current VoicePlayer external helper writes the same `externalCookie`
constant at `0x183abefd9` before `PostEventExternal`. This closes callback-
family/source-cookie selection, but not the per-request native descriptor/
`sourceInfo +0x10` instance selected for the statically recovered
`externalSourceKey` path, or a live callback, file-handle, or PCM observation.
A separate identity join over the current Wwise Event inventory makes the
remaining distinction explicit: the 1,712 External Source Event ids overlap
the typed voice-table routing aliases, but none overlap the narrower
AudioDialog path-hash/Event-id aliases. The Event therefore selects a voice
route/template, while the per-request media identity remains the formatted
`VoiceContext.voiceData.data` path passed as `externalSourceKey`; an Event id
must not be substituted for that file key. The generated audit is kept in
`reports/story/recovery/audio/external_source_event_identity_audit.{json,md}`;
all 1,712 External Source Event records also have zero decoded-media leaves and
zero serialized media relations, so a static Event-to-WEM join cannot recover
the file selection. This remains a static identity join, not proof of branch
selection or file I/O.
The typed `AudioDialog.overrideWwiseEvent` fields provide one more bounded
layer: 30 of the External Source route Events map to 1,723 table rows and 864
distinct authored `AudioDialog.path` candidates, of which 859 are decoded in
the CN index. Four route Events have a unique candidate, but the other routes
are shared templates; this proves route-to-candidate-path provenance, not the
runtime row/template choice or the native key-to-handle join. Counts and route
hashes are kept in `reports/story/recovery/audio/external_source_override_path_audit.*`.
The typed `AudioDialogChannel` narrating/radio fields provide a broader but
weaker route join: 1,298 External Source Events cover 27,535 unique speaker-
channel path candidates, with 26,582 decoded in CN. Because these routes are
shared by many rows and narration/radio selection is runtime state, this is
candidate coverage only; the 414 Events without a channel candidate and the
per-request native key/handle join remain explicit gaps. Counts are kept in
`reports/story/recovery/audio/external_source_channel_path_audit.*`.
A selected-build negative check narrows that boundary further: an exact scan of
`AkSoundEngine.dll` finds no little-endian `0x24db9834` literal. The native
manager's callback cookie/context at entry `+0x58` is therefore input-driven,
while its exact lookup key at `+0x4c` is the separately generated registration
serial. The cookie join is established by managed `GameAssembly` plus the HIRC
records, not by a baked native constant; only runtime argument capture can show
which native input carries the managed cookie and whether a source-state key
matches the registration serial.
The native ABI now separates the two meanings of “cookie” too. External
PostEvent stub `0x1800285d0` forwards stack `pCookie` through
`0x1800c38b0 -> 0x1800c3990 -> 0x1800e12e0`, where the constructor stores it at
manager `+0x58`; this is the callback-mapping object. The Wwise
`AkExternalSourceInfo.iExternalSrcCookie` remains inside the copied descriptor
allocation retained at manager `+0x38`, alongside `szFile` and codec, while the
registration serial is `+0x4c`. These three values are now statically distinct,
so no equality is inferred between callback mapping cookie and `0x24db9834`.
The temporary managed mapping also has its own user-cookie slot at `+0x28`,
which carries the voice handle id; it is distinct from both the mapping-object
pointer passed as native `pCookie` and the Wwise external-source cookie. The
callback lifecycle probe compares only the mapping pointer across native and
managed callback boundaries, never these three numeric domains as aliases.
The adapter return is a fourth identity boundary: `_PostEventWithExternalSource`
calls `_GetInternalPlayingId` at `0x18328a810` and keeps its result in `edi`,
calls native `AkSoundEngine.PostEvent` at `0x183abed90` and keeps that result in
`ebx`, passes both to telemetry, then returns `edi`. The managed `System.UInt32`
return is therefore not the native `0x1800c3990` registration serial stored at
manager `+0x4c`; a VoicePlayer handle or managed playback return cannot be used
as a static alias for the source-manager key. The exact selected-build flow is
recorded in `reports/story/recovery/audio/managed_external_source_argument_flow.{json,md}`.
The native constructor ABI is now explicit in the versioned audio report and
hook manifest: register arguments carry manager/source/descriptor values, and
three stack slots separately carry the resolver function, callback-mapping
pointer, and operation flags. The manifest decodes those slots for a future
pointer-identity capture without treating the three cookie domains as aliases.
For 40,421 media files whose physical category is `unknown`, exact evidence now
supports a separate semantic label (34,458 SFX, 5,645 voice, 188 UI, 66
ambience, 48 control, 13 music, 3 cue): 40,217 uniform related-Event joins,
four trigger-context Event categories, and 200 MonoBehaviour audio-field roles.
The physical path label is not rewritten, and 276 mixed known-category joins
stay unresolved.

Bank version 150 NodeBase prefixes now preserve ordered direct effect slots,
inheritance/bypass fields, metadata slots, explicit output-bus IDs, and parent
IDs. Referenced effect objects expose their exact plug-in class, custom versus
ShareSet object kind, parameter length/hash, and physical PCK scope; built-in
names are pinned by registrations and factory source paths embedded in the
shipped `AkSoundEngine.dll`. Its fingerprinted `SetParamsBlock` implementations
now fix the packed authored-base-value layouts for Gain, Delay, Compressor,
Expander, three-band Parametric EQ, Meter, variable-length Matrix Reverb, Pitch
Shifter, two-voice Harmonizer, and Stereo Delay. Exact sizes, finite floats,
booleans, enums, Harmonizer window sizes, and Matrix delay-array length all fail
closed. Same embedded-bank/effect IDs in Audit and Hotfix remain separate when
their parameter bytes differ. RoomVerb's 186-byte block now identifies all 37
public authoring controls. Its ER pattern ID indexes the DLL's exact 31-entry,
40-byte-stride pattern/name table; DSP control flow separately proves that room
size drives exponential pattern-time scaling and rear delay sizes the rear
channel delay lines. SetParam IDs 100..110 remain exact finite values but have
no public names. The native contract now bounds their use without inventing
authoring labels: IDs 100..104 feed early-reflection tap-pattern synthesis,
with endpoint pairs, seeded per-tap variation, and ER-grid normalization; ID
108 participates in six-channel coefficient derivation, and IDs 109..110 feed
a seeded second reflection-pattern generator. IDs 105..107 have exact
SetParam/default/copy coverage but no direct read in the audited RoomVerb
update helpers. Convolution Reverb's 57-byte block identifies all 13 public
runtime controls across 7 unique definitions. SetParam ID 34 is now bounded as
an exact private scalar: it is copied from serialized offset 52 to native +0x3c,
then wrapper +0x4c, and forwarded as the fifth floating-point argument on both
convolution processing paths (0x00254a83/0x00254bd8); the current CPU engine body
at 0x00258520 does not expose a read of that argument, so no gain/threshold name
or DSP effect is inferred. Serialized byte 56 is copied to native +0x40, wrapper
+0x50, and runtime state +0x8c at 0x00254d27; its public name and final DSP role
remain unresolved. The v150
plug-in-media prefix independently proves 7 unique impulse-response media IDs
across 20 definition occurrences; none is projected as a playable Sound/WEM
leaf. Guitar Distortion's 126-byte block adds exact public semantics for three
pre-distortion and three post-distortion EQ bands plus Type, Drive, Tone,
Rectification, Output Gain, and Wet/Dry Mix; the sole definition authors Clip
at 61% drive with three enabled EQ bands. Mastering Suite's packed 304-byte
block now identifies all four output-device modules: six Parametric EQ bands,
four Multiband Compressor bands and their crossover/link controls, overall and
12 serialized channel gains, and the Soft/Hard/Advanced Limiter settings.
SetParam IDs 100 and 200 remain exact uint32 codes without public names. The
shipped Mastering Suite binary also proves their native storage path (serialized
offsets 4/110 to native +0x18/+0x88), but the audited runtime region has no
stable direct read for either field; they are therefore labeled storage-only,
not assigned a guessed processing-order or profile meaning. The 12 channel
slots are mapped exactly by SetParamsBlock from serialized 235..279 to native
+0x118..+0x144 (stride 4), but retain Wwise serialization order without inferred
speaker names, so those rows are explicitly partial-semantic. Current CN output
interprets 732/732 unique direct effect definitions (100%: 698 exact semantics,
34 partial semantics) and 1,338/1,344 direct references (99.6%: 1,238 exact,
100 partial); the remaining six references have no effect definition in the
scanned bank set rather than an opaque parameter payload. Guitar Distortion and
Mastering Suite are definition-only in the current traversed event graph, so
neither changes reference coverage. Field labels and authoring units follow the
matching Wwise plug-in contracts, while byte offsets and primitive widths
remain pinned to the shipped binary. v150 FX-slot flags are now decoded from
their raw bit vectors: direct NodeBase slots contain 12 authored bypass bits,
279 ShareSet bits, and 890 rendered bits; cross-correlated Audio/Aux Bus slots
contain 8 bypass bits and 89 ShareSet bits, with no unknown bits in either
corpus. These flags describe authored slot policy, not a proof of runtime DSP
execution or audibility; they remain separate from node-level bypassAll and
dynamic BypassFX controls. Type-8 Audio Bus and type-18 Auxiliary Bus
payloads now add a complete reciprocal parent hierarchy: 279 unique definitions,
276 non-root parent edges, three roots, and 279 exact root paths. Typed v150
`CAkBus` parsing consumes the property, positioning, Aux, duck, and bus-state
fields before InitialFX and proves the serialized effect count on all 279
buses: 128 explicit zero-count lists and 151 non-empty lists with 247 ordered
slots, all 247 resolving to decoded plug-in schemas. The same rows retain exact
duck records and authored Bus property values; parent inheritance, live control
changes, and runtime DSP remain separate boundaries. The current corpus proves
119 type-18 Auxiliary Bus IDs. The Bus suffix is now
decoded in its actual v150 order after metadata:
InitialRTPC precedes StateChunk, and all 279 Bus payloads consume that suffix
exactly. It yields 92 authored curves with 265 points, 15 State groups, 32
States, and 34 State values. The standard v150 property table is only the
low numeric range; the published corpus separately records 90 node curves for
`parameter6146` (`0x1802`) and 90 for `parameter6148` (`0x1804`), plus eight
Bus State-property references (six `0x1802`, two `0x1804`) and one Bus RTPC
curve for `0x1804`. These high IDs are proven serialized control targets; the
observed raw instances use boolean accumulation where that field is present,
but their DSP property names are not proven. They remain explicit
custom/internal IDs rather than guessed labels. These are authored
response mappings only: the live GameParameter/State value, inherited effective
property, bypass decision, platform DSP, and audibility are not serialized
observations.
The same index now publishes a hash-pinned IL2CPP metadata cross-match for six
game-side GameParameter symbols: `AU_RTPC_CINE_CTRL_VOL_AMB` (`0x6b7dc358`,
3 node/4 Bus curves), `...VOL_MU` (`0x590f4cd1`, 2 Bus curves), `...VOL_SFX`
(`0x52aabb05`, 11 Bus curves), `...IS_MUTE_BY_SDK_WEBVIEW` (`0xba4a40b7`,
1 Bus curve), `...IS_SURROUND_CHANNELS` (`0x7ec2f9aa`, 2 Bus curves), and
`...GLOBAL_VOL_MASTER_IOS_WORKAROUND` (`0x3794392f`, 1 Bus curve). This is
symbol-to-ID evidence only; it intentionally leaves `0x1802`/`0x1804` as
custom/internal Wwise property IDs and does not claim live updates.
The semantic Event projection additionally recovers 25 unique `AU_*` IL2CPP
field symbols whose exact AudioHashGenerator hashes match current Wwise Event
objects. Declaring type, field token, and the metadata hash are retained as
static identity evidence; name-prefix categories are conservative and do not
claim a runtime caller, trigger, branch selection, execution, or audibility.
Observed-string Event-name sources are now exhausted and must not be
re-attempted. Hashing every one of the 65,756 IL2CPP string literals, rather
than only the `au_`/`bark_`/`radio_`/`vo_` prefixed ones, resolves three more
hash-only Events (`vo_raw_alert`, `vo_placeholder_alert`, and the generic word
`Stop`); hashing all 268,354 metadata type and field names resolves only `Stop`
and `StopAll`. Both generic words are coincidental preimages, not names, so the
prefix filters stay closed and only `vo_` was added. The authored names of the
remaining hash-only Events are not shipped in the binary at all. Bank identity
gives no grouping either: the client emits one bank per Event and the bank ID
equals the Event ID (19,312 of 19,401 banks hold exactly one Event), and a
sampled sweep of `unknownUse` Event IDs finds zero occurrences anywhere in the
exported gameplay JSON tree.
Hash-only Event names are therefore recovered by grammar-directed preimage
search in `scripts/audio_semantics/name_recovery.py`. Recovered names are
strongly templated (`au_eny_0094_hsfly_skill03_charge`), so the module mines
head/tail template slots per naming family from names already proven by exact
evidence, regenerates sibling names, and keeps candidates whose
AudioHashGenerator hash equals a current hash-only Event id. A hash equality on
a generated string is weaker than one on a shipped string, because a 32-bit
space admits coincidental preimages in proportion to candidate volume. Two
guards apply: a hash with two distinct generated spellings is dropped, and a
name is promoted only when its head and its tail each recur across other
recovered Events at one shared split boundary. Independent best-head and
best-tail counts would pass on the family prefix that every candidate shares by
construction, so the shared boundary is required. Uncorroborated hits are
retained as `isolatedEntries` and never become an Event name. The current CN
corpus mines 10,766 seed names against 10,739 hash-only Events, tries ~4.48M
candidates over two passes, and promotes 864 names (348 isolated, 2 ambiguous)
with a reported ~10.6 coincidental-preimage expectation over all matches. A
recovered name carries the owner and category its spelling encodes and nothing
more: `eventIdentityStatus` is `grammarHashPreimageNameRecovered`, and no
caller, trigger, execution, selected Wwise branch, or audibility is implied.
The same current-build native audit now resolves 18 authored custom-state
contexts from `InteractiveLogicBase.SwitchAudioCustomState` across
rotate-platform, crane, electric-fence, ForgeIron, LifterButton, and
MovingPlatform state machines. Exact method callsites and metadata usage words
are retained only after joining their `InteractiveData` Event rows.
`RotateNormalStart` and `RotateOverStart` are separate branch-specific states
at one callsite. This is a static native trigger contract with runtime
branch/object execution and audibility left unresolved. The same
fingerprint-locked catalog places the pause/resume control Events
`au_gameplay_pause_spidle` and `au_gameplay_resume_spidle` at exact
`SnapshotSystem` `PostEvent` callsites; action-entity ownership and runtime
execution remain unobserved.
The semantic media shard now joins each possible decoded media leaf to the
serialized Event output-bus paths that reach it, retaining effect-bus and
unresolved-bus IDs as references into this catalog; it does not claim runtime
branch selection or effective DSP. The same media rows now carry a bounded
exact `trigger_contexts.json` `mediaRefs` join for trigger semantic kinds,
roles, owner/situation values, and selection/activation statuses; it does not
upgrade authored requests into observed playback.
When a typed NodeBase summary has `outputBusNodeCount=0`, the media row carries
`noExplicitOutputBusSerialized`; this is an explicit absence of a serialized
output-bus node, not a claim about default routing, silence, or no effects.
The same media projection now keeps bounded direct NodeBase effect slots from
Event `postProcessSummary.effectNodes` separate from output-Bus effects,
preserving effect/plugin, node/slot, authored parameter summaries, and flags.
This exact serialized join does not establish live DSP execution or audibility.
Media rows also expose the exact serialized Wwise leaf-edge types and selection
paths (`directSound`, `layerChild`, `randomAlternative`, `switchCandidate`,
sequence/music edges) plus root Action IDs. CN currently publishes this graph
evidence on 59,109 media rows with 39,619 path summaries, making candidate
construction visible without inventing runtime branch choice or caller identity.
The same media join now carries Event-level authored context kinds, roles,
owner values, and situations on 44,442 media rows (367,317 context
occurrences). This broader Event-to-possible-media relation is kept separate
from exact `mediaRefs`, so it does not imply a selected leaf or observed call.
The current CN projection contains 1,879 media rows and 471,281 direct-slot
occurrences; per-media summaries are bounded to 32 entries with explicit
truncation. A second bounded projection combines those direct slots with
serialized leaf-to-root Bus paths into 573,360 authored effect-chain stages on
32,044 media rows (64 stages per row maximum). Direct-node slots precede each
Bus path and Bus slots retain serialized order; this is not observed runtime
DSP order, inherited values, branch selection, or audibility.
The same media rows carry compact references to Bus InitialRTPC/State controls:
31,523 rows expose 135,375 controlled-Bus occurrences, 332,954 RTPC curve
occurrences, and 5,616 State values. Full points and plug-in parameters remain
in the unique typed Bus catalog and are resolved by Bus ID rather than copied
into every media leaf.
Serialized Bus ducking is projected similarly: 1,909 CN media rows reach 2,249
ducking Bus definitions and 4,453 authored duck slots, preserving target Bus,
attenuation, fade, and target-property fields. This proves possible authored
duck routes only; runtime activation and audibility remain unknown.
Exact User-Defined Aux send slots are also joined to possible media leaves:
20,588 CN media rows expose 27,592 unique Aux Bus/slot targets and 698,886
underlying send occurrences. Source-node types, flags, root Actions, and target
Bus IDs remain visible while Game-Defined IDs and live send levels stay
runtime-only.
Each target also retains its exact serialized Aux Bus parent path and effect-Bus
IDs, allowing the possible send route to be followed through the typed Bus/DSP
catalog; this remains authored possible-route evidence.
The same media projection summarizes NodeBase authored properties and ranges:
53,882 CN rows expose 715,175 distinct property signatures across 18,436,139
occurrences, while 21,526 rows expose 48,721 range signatures across 113,639
occurrences. Raw U32 forms and complete node provenance remain in Event
evidence.
The same media rows now carry bounded exact StateChunk override values and
InitialRTPC curve shapes from each possible serialized Event path: 4,300 media
rows expose 20,254 RTPC control summaries and 1,292 expose 2,339 State-value
overrides. Up to eight curve points are retained per summary, with truncation
visible in the data and UI. This is authored control evidence only; live
GameParameter/State setters, branch choice, inherited values, platform DSP,
and audibility remain unobserved.
unique-payload audit parses the v150 NodeBase tail through Priority,
property/range bundles, Positioning, and AuxParams for 188,964/188,964 audio
nodes with zero failures and zero invalid bus references. It recovers 7,492
populated User-Defined send slots targeting 25 unique Aux Buses; every target
can use the same exact bus-parent/DSP path as an output route. It also finds
30,162 nodes with the authored Game-Defined send Use bit, but those Bus IDs,
listeners, and control values are supplied at runtime and are not serialized,
so no static wet path is inferred. No populated Early Reflections Aux Bus ID
occurs in the current corpus. Across traversed event occurrences, the same
exact AkPropID v150 bundle contains 90,639 nodes with 165,161 authored base
values and 1,650 min/max ranges; labels include Volume, LPF/HPF, BusVolume,
OutputBusVolume, Aux send levels/filters, positioning, Priority, and
InitialDelay. Each row preserves the property ID, raw U32, and finite float
interpretation; typed ID/integer unions such as AttenuationID and Loop retain
their integer display class so raw IDs are not mistaken for effective gains.
No current occurrence contains the initial-property BypassFX/BypassAllFX IDs;
the direct NodeBase bypass flag is still exact, while dynamic bypass controls
remain unresolved. Effective inherited sends, live RTPC/State values, platform
DSP, and audibility remain unresolved. The
same counted NodeBase parser now continues through the six-byte AdvSettings
block, StateChunk, and InitialRTPC. An independent full-corpus implementation
matches production on all 188,964 unique node payloads, including every end
offset; all 128,954 Sound payloads end exactly at the recovered RTPC boundary.
Static banks contain 1,278 State Group occurrences across seven group IDs,
5,709 RTPC curves, and 15,599 curve points. Current event traversal projects
1,784 State Group references, 1,640 authored State property values, and 19,001
RTPC curves with 67,327 points. Parameter IDs identify controls such as Volume,
LPF, BusVolume, OutputBusVolume, User Aux send filters/levels, and HDR
threshold/release. Known hashes are joined fail-closed: `0xf6699cf4` is the
native-evidenced gamepad motion-output backend, with `0x1a9fc91f` = XInput and
`0x1b9abdb1` = ScePad; the same catalog now labels the ten exact music State
groups and current metadata enum values (for example `0xe414d158` =
`music_state`, `0x468283e1` = `CUTSCENE`, and `0x36752fa3` = `NARRATING`).
Known `au_rtpc_*` names resolve through exact FNV-1 hashes. These rows describe
authored response curves and State overrides, not the live control value,
effective inheritance, selected platform backend, or audible result.

The same v150 Action reader now follows the original bank bytes beyond the
playback edge. In the current named-event corpus it consumes 6,735 non-playback
actions exactly (0 failed control tails): 3,455 SetState, 304 SetSwitch, 158 Set/ResetGameParameter,
1,627 Stop/Pause/Resume, 122 Seek, 1,020 value/filter actions, 32 FX-slot
actions, and the remaining Trigger/ResetPlaylist controls. Rows preserve the
serialized Event→Action object paths/type labels, FNV IDs, float ranges, fade curves, active-action bit vectors,
exception buses, and FX slot numbers. Fade curves, flags, and action bit
vectors are authored inputs, not execution or current-state observations. This
is authored dispatch evidence only;
The semantic join now maps 1,601 Action group references and 1,042 value
references in the current CN projection. It covers the three native-backed
selector roles (voice identity, surface material, and local/remote routing),
the gamepad backend, and ten exact music State groups; values without an exact
native or current-metadata match remain numeric. The same 15-row selector
catalog is joined to typed type-6 selector packages, so package values such as
XInput/ScePad and music-state enum members are visible beside possible child
branches. The bank does not provide the live State/RTPC value, selected
selector branch, effective inheritance, DSP execution, or audibility. The
parser fails closed with a bounded offset/reason if an operation tail is not
fully consumed.
The Wwise v150 Type-6 tail is an authored package/association branch, not the
current runtime value: a serialized default is not evidence of the active
selector or selected child. Catalog labels marked inferred remain possible and
non-exact. Only a complete validated v150 shape with an exact same-bank
child-to-Sound/media join is accepted; malformed structures and cross-bank
matches are rejected or remain unresolved. RTPC/State curves are authored
controls, not branch predicates, so selected branch and audibility stay
runtime-unobserved.
An additional same-event join finds 12 Set/ResetGameParameter rows whose exact
`idExt` equals an `InitialRTPC.rtpcId` (2 unique IDs); this proves an authored
curve-target relationship only. The GameParameter name, live value, and final
DSP response remain unresolved.
Separately, five unique InitialRTPC IDs match exact metadata `au_rtpc_*`
literals, covering 14 serialized curve occurrences across six Event
occurrences. Their catalog rows retain authored Event/context ownership,
controlled properties, response-point counts, and interpolation labels; they
are not live RTPC traces or audible-result proof.
The schema-117 semantic `controlCatalog.staticRtpcAlignment` is the stricter
six-name canonical `AU_RTPC_*` contract. It statically aligns those names and
numeric HIRC IDs with serialized InitialRTPC curve/property evidence and
same-event Set/ResetGameParameter controls; the complete mapping remains in
`scripts/audio_semantics/rtpc_contract.py` and generated reports. The rows are
`authoredStatic` evidence only. Publication requires the explicitly selected
`global-metadata.dat` + `GameAssembly.dll` hash gate, and fails closed on a
missing/mismatched selected or source hash, malformed/incomplete rows, or stale
serialized evidence. Runtime parameter values, setter execution, target
objects, selected branches, DSP state, and audibility remain runtime-only.
The page projection is refreshed only by a formal semantic rebuild.

Native Audio evidence is evaluated against the explicitly selected client:
`global-metadata.dat` and its sibling `GameAssembly.dll` must both match the
reviewed fingerprints. A missing or different client removes only native
callsites, mappings, and addresses; authored table/component rows remain
available and visibly carry the unavailable diagnostic.

Responsive voice data retains every authored response position and tone
substitution while leaving live response/tone choice unresolved. AnimationClip
`TriggerVoice` callbacks remain distinct from ordinary audio callbacks and keep
all compatible owners when animation identity is shared.

Native audio package loading is now statically separated from external voice
key formatting. The normal VFS path now closes through
`VirtualFileSystem.GetAkSoundEngineVFSBasePath` ->
`AudioVFSLoader.InitBasePaths` -> the selected-PCK loop ->
`AkSoundEngine.LoadFilePackage`; extra/debug paths add or set a base path
before the same package bridge. This closes the path-to-loaded-Wwise-package
boundary, but not the native file read/bank parse or the runtime lookup of an
external voice `szFile` key's file-open callback. Build-specific addresses and export hashes stay in
the generated audio recovery report and runtime semantic contract.

The managed-to-native export boundary for external `PostEvent` is now exact,
not an inferred suffix mapping. GameAssembly stub `0x183abeee0` lazily caches
its target in slot `0x18f361150`; its miss path `0x1800db690` asks
`0x180059520` to resolve module `AkSoundEngine` and the exact export string
`CSharp_b533bd82e4996d0c1d5686812d0f2`. The selected native export is
`0x1800285d0`, whose SWIG wrapper forwards `pCookie`, `cExternals`, and
`pExternalSources` to `0x1800c38b0` (clearing the sibling playing-id
carrier). This closes the dynamic P/Invoke-to-descriptor-copy edge; it does
not change the remaining runtime-only key-to-sourceInfo/provider, file-open,
decoder, or PCM gaps.

The installed `AkSoundEngine.dll` was checked as a separate native boundary
(its current SHA-256 is recorded in the audio recovery report). It has
obfuscated `CSharp_*` exports and no plain external-source/file-package names,
but the selected build does contain a default Wwise file-I/O object: its
`%u.bnk`/`%u.wem` table points to `CreateFileW`/`GetFileSize` open logic, and
its queued batch-read methods call `ReadFileEx` with completion callbacks.
Init-to-device wiring is also static: setup passes the default object's `+0x8`
subobject into the stream-device constructor, which stores it at device
`+0x428`; device queue code then dispatches that file-I/O vtable's batch slots.
The generated pointer-table census independently confirms the same topology:
the selected build's registered-device, default file-I/O, active stream-manager,
provider, and pump tables all contain the expected open/normalize/read/write
function pointers. It is kept in
`reports/story/recovery/audio/native_io_vtable_pointer_census.{json,md}` as
build-specific evidence. The census is static only; it does not show a live
external request selecting a slot or carrying a decoded buffer.
This proves native open/deferred-read mechanics. The external-source manager is
also now closed through its hash-table mechanics: constructor `0x1800e1320`
stores its constructor input id at object `+0x4c`, callback at `+0x50`, cookie
at `+0x58`, flags at `+0x60`, and hash-chain next at `+0x68`; all current
constructor callsites feed that id from an internally generated registration
serial written at `0x1800c3990` record `+0xc` (global lock-xadd result `+1`,
through the `0x1800c3990`/related paths), not a statically proven managed
external key. An exhaustive direct-call scan finds both constructor wrapper
families: `0x1800e12e0 -> 0x1800e1320` at `0x1800e130b` with callers
`0x1800c3516/0x1800c3b31/0x1800c3e7e`, and `0x1800e1490 -> 0x1800e1320` at
`0x1800e14d2` with callers `0x1800c41cc/0x1800c4472`. Those callers prepare
the native records and consume the c3990/related registration-serial paths
before the constructor stores the record `+8` dword into object `+0x4c`.
This closes wrapper coverage for the selected binary. Lookup `0x1800e2820`
compares the requested source-state key exactly against `+0x4c`, so a
successful join requires equality with that serial, and dispatches
`0x1800e19a0` with operation `0x10` (sibling `0x1800e28d0`
uses operation `0x20`). The `PostEvent` export stub normalizes a non-null
managed resolver to the fixed native bridge `0x180002da0`: operation `0x10`
takes the default no-op branch `0x1800030cf`, while operation `0x20` enters the
compact `0x30`-byte record builder `0x180002e05`, packages the resolver
cookie/context/key/aux fields, and queues the callback record via
`0x180003430`. Operation `0x8` uses the `0x48`-byte builder `0x180002f31`;
the extended `0x80`/`0x2000` branches use their corresponding compact or
string-bearing builders. This closes callback transport, but not the
external-key to opened-handle/read-request join, decode handoff, or live
invocation.

The runtime importer now exposes a separate `nativePairing.callbackLifecycle`
summary. It compares the native resolver/queue descriptor context pointer with
the managed `_OnExternalSourceEventCallback` `callbackCookie`; an exact match
would prove that the temporary callback mapping object crossed the native
callback boundary in that capture. This is deliberately distinct from the
Wwise `iExternalSrcCookie` (`0x24db9834`) and does not prove the external path,
file handle, decoder, PCM, or audibility.

The two source-manager callback branches are now bounded separately. Lookup
`0x1800e2820` requires object flags `+0x60` bit `0x10`, writes the resolver
descriptor (`+0` cookie/context, `+8` source context, `+0x10` requested key,
`+0x14` aux) and invokes the generic callback runner `0x1800e19a0` with
operation `0x10`. Sibling `0x1800e28d0` requires bit `0x20`, builds the stack
descriptor at `+0x20/+0x28/+0x30/+0x34`, invokes the stored callback directly
with operation `0x20`, and stores its return at manager `+0x48`. The fixed
bridge maps op `0x10` to the no-op path and op `0x20` to the callback queue.
This closes descriptor and operation transport only; it does not identify the
managed path, opened handle, or PCM consumer.

The adjacent source-manager branches are also explicit. `0x1800e25f0` repeats
the exact bucket/key walk, requires entry `+0x60` bit `0x80`, builds the
cookie/context/key/aux descriptor from entry `+0x58/+0x28` and `+0x24`, and
invokes the stored callback with operation `0x80`; its direct callsites are
`0x1800347af`, `0x1800356bf`, and `0x18003578f`. `0x1800e26f0` requires bit
`0x2000`, copies a caller payload of 0x20 bytes plus its tail, adds key/entry
metadata and callback context, and invokes operation `0x2000`; caller
`0x18004388b` supplies a range-matched slot payload. The fixed bridge maps
operation `0x80` to the common queued callback record and `0x2000` to the
string-or-generic queued-record builder. These branches extend callback
transport evidence only; they do not select the UTF-16 path, open a handle,
or deliver PCM.

The related voice/render source path `0x180188ed0 -> 0x180188fae ->
0x1800e1ed0` uses the same source key, requires source flags `+0x60` bit 3,
and invokes the stored callback with operation `0x8`. Fixed bridge
`0x180002da0` routes that operation to `0x180002f31`, which copies a
`0x48`-byte notification record and queues it through `0x180003430`. This is
source-state callback transport, not proof of a file path, opened handle, or
PCM sink.

The general VFS `ReadFileByLowIO(string, bool) -> FVFSTrackedLowIOHandle`
reader is a separate boundary: its recovered callers are Unity file-length,
scene-area, and dynamic-scene resource loaders, with no static caller from
`Beyond.Audio`. It proves that the client has a managed low-I/O asset reader,
but does not connect the voice external key to that reader. The native
source-manager lookup/callback transport is now recovered separately; the
remaining gap is how the external key/context selects an opened handle or
read request and then reaches decoding. The selected native source/media
lookup at `0x18010df60` reads the external key/hash from source-state `+0` and
calls the manager lookup (or fallback registry). In the voice/render path,
`0x1801443e0` loads context `+0x268` into a temporary dword at its local
`+0x10` and passes the address of that slot as stack argument 5 to
`0x18018a5a0` (unless its flag branch clears the argument). The
`0x18018a5a0 -> 0x1801898c0` path preserves that pointer in `r8`, and caller
`0x180189a59` passes it as `rcx` to this lookup, so that callsite reads exactly
context `+0x268` as source-state key `+0`. The same lookup has separate mixer
callers at `0x180189826`, `0x180189e18`, and `0x18018a2a8`. The unrelated
`0x1801443e0` local integer computed from temporary state/input `+0x10`
(initialized from build constant `0x200`) and context `+0x2a4` is not the key
passed at `0x189a59`. State-object initializer `0x1800d1f90` copies its
`+0x268` field from config `+0x34`; one concrete producer at `0x180034e4f`
fills that field from an upstream record `+0x14` before `0x1800365f0` calls the
initializer. Other constructors `0x1800fc9e0` and `0x18018dba0` receive their
config pointers through separate callers. Because the lookup compares exact
numeric equality, the source-state key must equal the manager serial at `+0x4c`
(`0x1800c3990` record `+0xc`). The source-construction path now supplies the
missing static edge: `0x1800350d7` passes the same parent `B +0x2c` that feeds
config `+0x34`/state `+0x268` into `0x1800e2cd0`, whose bucket walk compares it
directly with entry `+0x4c` without another hash transform. This closes the
static comparison path, but does not prove a runtime match or connect that
invocation to a selected file.
Within the child-source construction branch, `0x180034640` preserves the same
source-record `+0x14`, `0x180037740` copies it to the child source object's
`+0x2c` (`0x18003779e`), and `0x180034733` passes that value as the
`0x1800e2cd0` lookup key. This proves local same-record value identity before
the manager comparison, but the record field is still not statically aliased
to the registration serial; runtime equality and selected-file identity remain
open.
The shared helper `0x18018a5a0` receives a pointer to the key slot as stack
argument 5 and forwards it through `0x1801898c0`. Voice/render caller
`0x1801451ea` passes a local copy of `[r12+0x268]`; alternate caller
`0x180144c1f` passes `r12+0x18` under its flag, and `0x18017da06` can pass a
local zero slot. These callsites close the pointer/slot transport. The voice
source-construction path separately performs the exact key-to-entry comparison
through `0x1800350d7 -> 0x1800e2cd0`; the alternate mixer key slots still do not
have a proven runtime match or selected-file join.

The source-state callback producer is now explicit as well. `0x180143990`
tests callback state at object `+0xd8`, sets its in-flight flag at `+0x110`,
loads context `+0x08`, reads the selected key from `context +0x250`, obtains
the callback through `0x1800d0350`, and tail-jumps to sibling lookup
`0x1800e28d0`. That lookup requires manager flag bit `0x20`, copies manager
`+0x58/+0x28/+0x24` and the exact key into the callback descriptor, then
invokes operation `0x20`. The trace manifest now records the context pointer
and `+0x250` key before comparing it with sibling lookup/join observations;
this closes the static source-state/context-key to operation-0x20 callback
edge, but not the later sourceInfo/path, handle, decoder, or PCM identity.

The config producer's direct-entry coverage is now explicit. A byte-level scan
of the selected native `.text` finds one direct callsite,
`0x18003def1 -> 0x180034db0`. Its caller passes stack argument 6 from the
record returned by `0x180040350`, whose accessor returns nested
`[object +0x10] -> [+0x68] +0x18`. That return is parent `B +0x18`, so the
callee's record `+0x14` at `0x180034e4f` is exactly parent `B +0x2c`; it is
copied to config `+0x34` before entering `0x1800365f0`, and the initializer
later writes source-state `+0x268`. Sibling accessor `0x1800404f0` reads the
same `B +0x2c`; callsites `0x18003e35b` and `0x18003e486` pass that value into
source vtable `+0x138`, proving local field reuse. This closes direct producer,
callsite, and local-field-alias coverage. The subsequent source setup at
`0x1800350d7` passes the same `B +0x2c` into `0x1800e2cd0`, whose bucket walk
compares it directly with manager entry `+0x4c`; a runtime match and selected
file remain unobserved.
An exhaustive direct-call census adds two non-construction callers to the
same helper: `0x180034762` and `0x1800350d7` are the primary source/voice
paths, while `0x1800d35a8` and `0x1800e06ea` occur in broader manager state
transitions. The latter two confirm additional exact-key join consumers but
do not by themselves identify external media selection, a path open, or PCM
ownership.

The source-state metadata provenance is now explicit. Initializer
`0x1800d1f90` writes its incoming `r9` to source-state `+0x288` and config
`+0x34` to `+0x268`. In the primary voice path, `0x18003def1` supplies the
construction helper's incoming `r8` from the record returned by `0x180046580`,
and `0x180034db0 -> 0x1800365f0` forwards that pointer as the initializer's
`r9`; alternate callers `0x1800fca27` and `0x18018dbc5` use separate metadata
inputs. The external manager constructor `0x1800e1320` retains its own
incoming `r9` at entry `+0x38`, and the selected build has no direct call or
field-dataflow edge joining that allocation to the `0x180046580` record or
source-state `+0x288`. This narrows the remaining gap to sourceInfo identity,
runtime key matching, path selection, and PCM delivery.

The native writer for the sourceInfo path field is now bounded. The selected
build has one direct caller of `0x180104630`, at `0x1800e037e`. Setter
`0x180104630` stores its incoming `r8` pointer at source record `+0x10` after
copying the 16-byte identity block and writes the source mode at `+0x18`.
Sibling setter `0x1801044f0` handles the direct-path case: it measures the
incoming `r9` with `0x18026b7f8`, allocates/copies UTF-16 storage through
`0x180263808`, stores the owned pointer at `+0x10`, and sets the owned-string
flag. Caller `0x1800e037e` matches the current source key against its metadata
records and selects either `record +8 -> 0x1801044f0` or, when `record +0x18`
and `record +0x10` are present, the alias path `record +0x10 -> r8 ->
0x180104630`. This closes sourceInfo `+0x10` writer and UTF-16-storage
provenance; neither writer carries manager `+0x38`, the managed external key,
or source-state key, so exact copied-descriptor identity and runtime values
remain open.

The selected build now closes the next static hop for the direct sourceInfo
path branch. The preparation helper loads owner `+0x18` and sourceInfo
`+0x288`; when the source flags take the file/key branch, bit 9 selects
sourceInfo `+0x10` as local descriptor `+0`, while the other branch copies
sourceInfo `+4` as a numeric key. The factory's provider slot invokes the
provider's primary setup, whose allocation copies descriptor UTF-16 `+0`
into owned storage and retains descriptor metadata at `+0x08/+0x14` plus the
0x28-byte auxiliary block from descriptor `+0xc`. This is a static
sourceInfo-path-to-provider-storage edge; it still does not prove that the
value equals a managed `externalSourceKey`, a particular manager registration,
or a live opened handle/PCM stream. The exact selected-build addresses are
kept in the generated native-provider audit report.

The sourceInfo table's construction is also bounded to an internal serialized
object payload. The only direct callers of parser `0x180047120` are
`0x180039a28` and `0x180039b35`; it gates the owning object on virtual type
value `6` and consumes its serialized cursor through `0x1800f5fc0`. That
parser writes output `+4` from the first cursor dword, output `+8/+0xc` from
the second, output `+0x10` from the third, and derives output `+0x14` flags.
The caller passes output `+8` as the sourceInfo map key, output `+4` as mode,
and copies output `+8..+0x17` as the 16-byte identity block into the
`0x180045fd0`/`0x180045f30` records. This is a distinct provenance boundary
from Wwise External Source `sourceId`/cookie `0x24db9834` and the native
manager registration serial `+0x4c`; no manager table, managed
`externalSourceKey`, or source-state key is read at parser/map insertion.
The exact sourceInfo instance selected for external playback therefore remains
unresolved.

The owning HIRC family is now identified too. Bank-object dispatcher
`0x18003a5b0` routes type bytes `10/11/12/13` to the corresponding music
parsers; type `13` goes to `0x1800397b0`, and the only sourceInfo-parser calls
(`0x180039a28` and helper `0x180039b35`) are inside that type-13 path. The
type-12 MusicSwitch branch has no direct call to `0x180047120` in the selected
`.text`. With the maintained HIRC labels, this attributes the table-construction
call path to the Music Random Sequence Container family and separates it from
the direct `AkBankSourceData` external-source parser. It further separates
sourceInfo construction from the `sourceId`/cookie join, while leaving the
later runtime source-state selection unobserved.
The current CN external-source corpus reinforces that separation: its 1,712
`externalSourceCodec` records have 1,711 `event → action → sound` paths and one
ordinary HIRC type-5 Random/Sequence path; none is owned by HIRC type-13 Music
Random Sequence. Thus the type-13 sourceInfo table is not a static key map for
these external-source records, and the bank sourceId/cookie domain must not be
joined to native sourceInfo/source-state keys without runtime evidence.

SourceInfo has a separate native selection consumer. Helper `0x1800d2ed0`
dereferences source-state `+0x288` and passes sourceInfo `+0` plus mode
`((sourceInfo +0xc >> 2) & 0x1f)` to `0x1800f5030` through global slot
`0x180344a20`. That selector uses its own table at `+0x88` with bucket count
`+0x90`, compares entry `+8` exactly against sourceInfo `+0`, and fills a
candidate descriptor. Helper `0x1800f9780` makes that descriptor explicit:
`+0` is the matched table entry, `+8` is an optional type-2 context, `+0x10`
is candidate `+8`, and `+0x18` is candidate `+0x10`. The caller checks
`+0x10/+0x18` against source `+0x328 +0x18`, sends the candidate through
`0x180143de0`, then applies sourceInfo to source `+0x328` through
`0x180104720` before copying the descriptor into the source object. The slot
is distinct from the external-source manager slot `0x1803449f8` and
key-to-decoder registry slot `0x1803449d0`; therefore sourceInfo `+0` is an
internal selection key that feeds source/provider setup, not statically proven
to be the external registration serial. The runtime key value, selected
path/handle, and PCM handoff remain open.
The runtime trace contract now exposes both ends of this internal selector:
optional hook `0x1800d2ed0` reads the source object's `+0x288` pointer and
sourceInfo `+0` key, while optional hook `0x1800f5030` records the selector's
sourceInfo key/mode and its output descriptor. The consumer copies selector
output `+0x10/+0x18` into source `+0x338/+0x340`; the consumer and nested
provider-preparation hooks now sample that `+0x338` pointer after the copy.
Exact intersections with the
source-state callback key or generated registration serial would be stronger
identity evidence for one capture, but remain bounded numeric matches until
the same source object, path, provider, and read/codec chain are observed.
The provider-preparation hook also follows the nested owner `+0x18` →
sourceInfo `+0x288` pointers and records sourceInfo `+0` directly; this allows
one capture to test selector-to-provider key continuity without treating the
provider path alone as proof of external-source playback.

A complete selected-build `AkSoundEngine.dll` direct-offset/overlap audit found
one source-state `+0x268` writer: `0x1800d2055` copies config `+0x34` into the
source-state object. Exact-offset stores at `0x18008668c` and `0x1800ac3bf`
copy larger structures, `0x1800ae238` bulk-clears an `0xe38`-sized container,
and `0x18012d0fe` initializes a separate `0x310`-byte object; overlapping
16-byte zero stores at `0x18022ad9c`, `0x18022b3f5`, and `0x18022b83a` begin at
`+0x264` inside separately allocated `0x320`-byte auxiliary objects. The
remaining hits are stack locals or atomic refcount-like fields. No second
direct source-state key setter was found. The separate `0x1800350d7 ->
0x1800e2cd0` call closes the static key-to-manager-entry comparison path; the
registration serial's producer and runtime match remain separate evidence
boundaries rather than an omitted write site.

The successful branch's stored pointer is only a manager-entry attachment:
`0x1800e2cd0` appends the source-state pointer to entry `+0x10` (count `+0x18`,
capacity `+0x1c`), `0x1800e29d0` removes a matching pointer and decrements the
count before invoking `0x1800e1770`, and reset `0x1800e2e20` frees each entry's
attachment array. No consumer in this chain reads a path or bytes or calls
the codec, so the e2cd0 hit is a lifecycle/state-registration join rather than
a media-selection edge.

The registration serial storage resolves to global `0x180344988`. Its only
RIP-relative references in the selected native `.text` are lock-xadd writers at
`0x1800c3414`, `0x1800c3af2`, `0x1800c3e48`, `0x1800c418e`, and `0x1800c443d`;
there is no direct RIP-relative read at the source-state constructors. This
adds a negative data-flow boundary: the source-state `+0x268` value is not
statically shown to be loaded from the serial global.

Registration-key provenance is independently bounded: the `0x1800c3990`
families generate manager keys from lock-xadd serial slot `0x180344988`, store
serial+1 at registration record `+0xc`, and pass that record into the
constructor that retains manager entry `+0x4c`; the primary source joins
instead load `[r14+0x14]`/`[r13+0x14]` from parent-B/source-state data. The
complete `+0x268` writer audit finds no store sourced from the serial slot.
Exact comparison is therefore static evidence, not proof of equal runtime
values; path/handle selection and PCM delivery stay open.
The selected AkSoundEngine image initializes the serial slot's raw dword to
`0x002f9238`, so an otherwise unmodified first generated value would be
`0x002f9239`, distinct from HIRC external cookie `0x24db9834`. This narrows the
image-initial domains but does not prove runtime state after initialization or
counter progression; native argument capture remains authoritative.
An exact selected-build direct-call audit adds a negative boundary: only two
direct calls to `0x1800c3990` exist (`0x1800c394e` and `0x1800c3c47`), both in
registration or external-post bridges, while the primary source setup at
`0x1800350d7` calls only the exact-key join `0x1800e2cd0`. This rules out a
missing direct registration call in that source path, but not indirect or
shared-record aliasing. The build-specific census is kept in
`reports/story/recovery/audio/native_registration_serial_audit.{json,md}`.

The exact `0x1800e2cd0` body narrows the meaning of a successful hit: it
appends the supplied source-state pointer to manager entry `+0x10`, updates
the live count/capacity at `+0x18`/`+0x1c`, and may retain auxiliary state at
`+0x30`. It does not read manager `+0x38`/`+0x40` or the copied UTF-16 record,
so this edge is lifecycle/state registration rather than path selection. A
runtime-equal key, provider-owned path/handle, and codec/PCM handoff still
need execution evidence.

After provider/decoder preparation, `0x1801b0160` reads the owner `+0x268`
key and registers the active decoder through `0x18013f440` using global slot
`0x1803449d0`, distinct from the source-manager hash slot `0x1803449f8` used by
`0x1800e2cd0`. Its `+0x10` dynamic table uses 0x18-byte key/decoder/status
records; teardown `0x180189041 -> 0x18013f290` removes a key+decoder pair.
This is a durable numeric-key-to-decoder-lifetime join, not evidence that the
numeric source-state key selects the VoicePlayer UTF-16 path, the `ReadFileEx`
request, or the PCM buffer.

The lookup fills the caller's
stack descriptor at `+0x40` with object `+0x58` (callback cookie/context),
object `+0x28` (source context), the requested key at descriptor `+0x10`, and
object `+0x24` at descriptor `+0x14`, then dispatches callback operation `0x10`
through `0x1800e19a0`. This statically joins source-state key to callback
descriptor metadata, but not to the native descriptor carrying the managed
VoicePlayer UTF-16 path, file-I/O, or codec;
direct callers continue media-state processing and have no direct file-I/O or
codec edge. The initial external descriptor copy at `0x1800c08d0` is a separate
path carrier: each `AkExternalSourceInfo` record is copied, and its `szFile`
pointer (descriptor `+0`) is duplicated into native source-record storage at
`+0x10`. The copied allocation is carried through `0x1800c3990`'s event record
`+0x14`, and the `0x1800e1320` constructor retains the descriptor-info
allocation at source-manager `+0x38`. This proves retention of the copied
descriptor allocation, but not that a later source-state key selected that
exact `sourceInfo +0x10` instance.
The carrier path is now byte-level bounded for the shared external PostEvent:
`0x1800c38b0` receives the `0x1800c08d0` copied allocation, stores it at local
`[rsp+0x50]`, and passes a pointer to that carrier as `0x1800c3990` stack
argument 6. `0x1800c3990` copies 0x14 bytes into registration record
`+0x14/+0x24`; `0x1800e12e0` forwards `+0x14`, and `0x1800e1320` stores its
first qword at manager `+0x38`. Thus `+0x38` is the copied external-descriptor
allocation pointer in this path, not a raw UTF-16 string. The sourceInfo
`+0x10` instance and source-state key still lack a static identity join. The
copier also has a separate replacement path: one additional direct call
releases and replaces an object-owned descriptor-array allocation at
`object +0x10`, but never enters the external-PostEvent registration,
provider, file-open, or codec branches. It therefore expands descriptor
ownership evidence without extending the VoicePlayer playback chain; the
build-specific callsite and ABI are recorded in
`reports/story/recovery/audio/native_external_source_info_layout.md`.
Its lifetime is also bounded: exact-key detach callers `0x1800e2a5e` and
`0x1800e2a8e` enter `0x1800e1770`; after the attachment array is empty, teardown
reads manager `+0x38` only to pass the retained allocation to refcount release
`0x1800c5f60` before unlinking the entry. It never dereferences that field as a
path or provider/codec input, so `+0x38` is an ownership-retention field rather
than a direct sourceInfo/provider edge.
The runtime-trace manifest now captures the allocation pointer written by
`0x1800c08d0` and the `descriptorInfo +0` allocation consumed by
`0x1800e1320`. The importer reports their same-session pointer intersection as
`sharedDescriptorAllocationBases`; a match would prove descriptor-copy output
to manager-constructor input for one invocation, while still not proving the
source-state key, sourceInfo path selection, file handle, or decoded PCM join.
The provider input boundary is separate: `0x1801af7a0` loads owner `+0x18`
and sourceInfo from `+0x288`; its file/key branch chooses sourceInfo `+0x10`
for the local descriptor when flag bit 9 is set, then passes that descriptor
through singleton provider vtable `+0x28` to provider-owned UTF-16 storage.
That call boundary carries no explicit manager entry, manager `+0x38`, or
source-state key value. It therefore closes sourceInfo-to-provider provenance
while leaving identity with the copied external descriptor unresolved.
The only direct callers are codec setup `0x1801b0380` (callsite
`0x1801b03b8`) and alternate setup `0x1801c56b0` (callsite `0x1801c5746`).
Both pass the decoder/source object, a request/config pointer, and `r8 = 0`,
then reload owner `+0x18` and sourceInfo `+0x288`; neither reads manager
`+0x4c`, retained descriptor `+0x38`, or a source-state key. Provider
activation therefore cannot close the missing key-to-sourceInfo identity;
that selection must happen upstream. In the file/key branch the helper passes
`lea r9, [decoder +0x58]` as an output slot to provider vtable `+0x28`, and
`0x1801af960` immediately uses decoder `+0x58` for provider calls. The trace
manifest records this post-preparation provider pointer and provider pointers
at device/async-read boundaries so an equal pointer can establish one
provider object crossing setup into I/O, without claiming a key/path/PCM join.
The provider-to-file boundary is now explicit too: open wrapper `0x180024630`
passes the registered-device descriptor and returned path pointer through
`0x180004a20`/`0x180004b40`; the default I/O table dispatches slot 0 to
`0x180005030`, whose `CreateFileW`/`GetFileSize` pair stores the handle/size.
`0x180004b40` chooses the incoming path or device base path and normalizes it
through `0x180005150`. This closes provider-request to native-open transport,
but the boundary still carries no external key, source-state key, or manager
`+0x38` value.
The open wrapper's register-level ABI is explicit: `rcx` is the file-I/O
object, `rdx` the original descriptor/path argument, `r8` the caller output
slot, and the provider context returned by vtable `+0x10` reaches
`0x180004a20` in `r9`; the normalized UTF-16 path then reaches the default
open slot. This is an exact parameter boundary, not a runtime identity join.
The runtime contract now samples the default-open stack argument 5 after the
call. In this build it is the provider context whose `+0x10` receives the
`CreateFileW` handle and whose `+0` receives the file size. The async batch
descriptor's provider object also exposes `+0x10`; the importer reports an
exact `openHandle`/`descriptorProviderHandle` intersection when both values
match in one verified capture. This would close the native open-to-async-read
handle continuity, while still leaving source-key ownership, decoder choice,
PCM delivery, and audibility as separate gates. The manifest's stack-memory
read is restricted to the hash-locked native hook and is not used to infer a
handle when the provider context is absent.

Wwise exposes a separate stream-manager I/O pump over registered native device
callbacks. The selected native build statically identifies the Init/setup path,
the allocated device object and its vtable pump, the exact device `+0x428`
pointer to the default file-I/O subobject, and that object's direct
open/queued-read API path. The source-manager provider path is now joined to
that pump: codec source preparation `0x1801b03b8` calls `0x1801af7a0`, which
stores a memory or file/key provider at decoder `+0x58`;
the file provider's `+0x78` (`0x1800b85c0`) drains queued blocks and, when empty,
calls its registered device (`0x1800b8120`), while `0x1800bc1e0` passes the
provider-built request arrays to the registered-device subobject at `+0x428`
through setup/release slots `+0x28/+0x30/+0x38`. Those slots resolve to
`0x180024630`, `0x1800248e4 -> 0x1800248f0`, and `0x180024190`; they are
distinct from the later `+0x60` `ReadFileEx` batch-read entry.
The file/key descriptor itself is also bounded through factory
`0x1800b5e30`: constructor `0x1800bb160` installs primary vtable
`0x1802932e8` and secondary vtable `0x180293260` at allocation `+0x90`, then
the returned secondary interface copies descriptor `+0` as a UTF-16 path into
provider-owned storage and preserves the remaining source metadata. Source preparation at
`0x1801af7a0` reads owner `+0x18` metadata `+0x288`; flags at sourceInfo `+0xc`
choose the memory branch or file/key branch, and file/key flag bit 9 selects
sourceInfo `+0x10` as the local descriptor path pointer while `+4`, `+0x1a`,
and flag-derived fields fill the rest. The memory branch instead copies owner
`+0x338/+0x340` directly into decoder `+0x60/+0x68` before codec setup. The
remaining gaps are
which external key/context supplies that descriptor, the indirect codec
callback target and PCM decode handoff, and live invocation. This boundary is distinct
from the generic managed VFS reader.

The native external-source manager is a concrete registration/lookup boundary,
not an inferred filename formatter. `0x1800e2820` uses the requested numeric
key only for bucket selection (`key % bucketCount`), then compares that exact
key against object `+0x4c`; this body contains no additional hash transform.
It copies the registered cookie/context and key metadata into a resolver
descriptor, and invokes the stored callback through `0x1800e19a0`.
The export stub's fixed bridge `0x180002da0` is now exact: op `0x10` returns
through `0x1800030cf`; op `0x20` copies the descriptor into a callback record
and enqueues it at `0x180003430`. No static edge yet joins that queued
external request to the Wwise `CreateFileW`/`ReadFileEx` object or embedded
codec reader. The queue consumer is now known; the remaining join is the
virtual-I/O/source state that carries the external key into a concrete source
descriptor/path. The provider descriptor layout, the default-I/O `ReadFileEx`
implementation, and descriptor-to-path-buffer copy are separate static facts;
The active stream-manager address point at `0x18028c020` joins provider
preparation at `+0x28 -> 0x180005430` to the direct read at
`+0x30 -> 0x180024270`; there is still no live key-to-file correlation.

The queue consumer is now also closed statically. `AkCallbackManager.PostCallbacks`
at `0x18328b440` resolves `CSharp_b1b6b5807eef294` to the native detach path
`0x18002ea80 -> 0x180002d10`, then reads each record's cookie, callback type,
and info pointer through the three native getters before entering
`_ProcessEventCallback` at `0x18328cd90` and the registered managed callback
delegate. This proves native callback transport and managed dispatch for the
queued external operation; it still does not connect the external key/context
to an opened file handle, read request, codec handoff, or live playback.
The three selected native getters are exact one-instruction bridges:
`0x18002e310` returns record `+0`, `0x18002e320` returns record `+0x10`, and
`0x18002e330` returns `record +0x18`. The trace contract now records the
detached head pointer and getter record pointer/type/payload; an append/getter
pointer intersection is bounded proof that a queued node reached the managed
callback pump, and an observed type `0x20` identifies the compact source-state
callback record. It still carries no sourceInfo path or provider/file/PCM
identity, so it is not a playback join.

The request-array boundary is now one step more precise: registered-device
method `0x1800bc1e0` selects each source provider through `0x1800ba0e0` and
assembles each `0x18`-byte descriptor before dispatching the registered-device
subobject at `0x1800bc4a5`. The provider constructed by `0x1800bb160` has
primary vtable `0x1802932e8`, whose active `+0x20` is `0x1800bc660`; the
ordinary path can create a chunk/request through `0x1800bb970 -> 0x1800bb8e0`.
Its secondary address point `0x180293260 + 0x20 = 0x1800b8820` is only a
provider-field serializer and does not populate the pump candidate-context or
flag slots. On the accepted ordinary branch, descriptor `+0x10` is the
address of `candidate + 0x8` (`lea`, not a dereferenced `[local + 0x8] + 8`);
the carrier's branch-dependent provenance is still unresolved. Init
`0x180001060` installs the composite object's active vtables at
global `0x18033ddf0`; `0x180023f90` passes its `+0x8` address point (vtable
`0x18028c020`) into `0x1800b5fc0`, and `0x1800b7310` retains it at the
registered stream-manager object `+0x428`. The pump's `+0x28/+0x30/+0x38`
calls therefore resolve to `0x180005430` (provider/state dispatch),
`0x180024270` (direct `ReadFileEx` batch read), and `0x1800243e0` (direct
`WriteFileEx` batch write). The provider-filter call runs before the direct
read call: `0x180005430` invokes `0x180024200`, whose provider `+0x18`
callback is the state transition `0x1800b92c0 -> 0x1800b8b00`; the pump then
passes its separately assembled `0x18`-byte descriptor array to
`0x180024270`. The queued-read implementation consumes a matching request
pointer from descriptor `+0x10` and writes only its internal helper at request
`+0x28`; it does not initialize request `+0x18`, so callback ownership remains
upstream. The pump's provider virtual `+0x20` call at `0x1800bc369` passes an explicit
descriptor output slot (`rdx`), candidate context slot (`r8`), and flag slot
(`r9`). The active `0x1800bc660` implementation initializes those outputs and
may call `0x1800bb970 -> 0x1800bb8e0`; the alternate serializer `0x1800b8820`
only writes provider descriptor fields. The separate state-2 helper
`0x1800b97e0` enters the default-I/O filter/deferred callback path and does not
initialize the pump-local context slot. This leaves a conditional static edge
into the `ReadFileEx` request-context layout, not an edge to a particular codec
callback value.
The request-object boundary is now explicit as well: constructor `0x1800bb8e0`
reuses the stream-manager free-list object at `+0x458`, derives request `+0x8`
from the queue/chunk context and caller offset, stores stack fields at
`request +0x10/+0x14`, copies caller `r8` into `request +0x18` as buffer/source,
installs fixed callback `0x1800bf190` at `+0x20`, self at `+0x28`, and the
original queue node at `+0x48`. The ordinary pump passes candidate `+0x8` as
the ReadFileEx carrier, so carrier `+0x18` aliases request `+0x20` and is
exactly `0x1800bf190`; carrier `+0x10` aliases request `+0x18`, carrier `+8`
aliases request `+0x10`, and carrier `+0x28` aliases request `+0x30`. The two
direct callers `0x1800bbad3` and `0x1800bca20` still provide branch-specific
source/offset inputs to the segment allocator. Completion `0x1800245b0` loads
the carrier from ring slot `+0x18`, applies the post-read transform, and
tail-jumps to `0x1800bf190` with `rcx=carrier` and status 1/2.
The provider-to-decoder handoff is now exact for the concrete decoder class:
source preparation `0x1801af960` calls provider vtable `+0x78`, receives the
buffer pointer and byte count, then calls decoder vtable `+0x130`. Decoder
construction `0x1801ae5a0` installs address point `0x18029cde8`, whose `+0x130`
slot is `0x1801afc80`; that implementation stores the provider buffer at
decoder `+0x60` and updates the available/position fields at `+0x68/+0x6c/+0x70`.
Refill `0x1801afb20` uses decoder `+0x120 -> 0x1801aebf0`, while reset
`0x1801af740` releases provider `+0x80` and clears the source fields. This
closes provider-buffer ownership into the decoder. The source-manager
constructor `0x1800bb160` installs primary vtable `0x1802932e8` at the
0x110-byte allocation base and secondary vtable `0x180293260` at base `+0x90`;
source preparation returns the secondary interface to decoder `+0x58`, while
the request retains the primary base at `+0x48`. The fixed completion callback
`0x1800bf190` reads that primary base, recycles the request, and walks associated
nodes through virtual `+0x30` release/advance calls. Thus `ReadFileEx`
completion joins the same provider allocation/queue used by the codec, while
the callback remains indirect at `+0` until a descriptor is selected; the two
exact `.rdata` descriptor literals currently reached are `0x1802b09d8` (Opus)
and `0x1802b1020` (generic memory source), resolved below.
The plugin also contains an embedded codec boundary (`0x1801c9fa0` stream
callback, `0x1801cf560` OpusHead parser, `0x1801cc1b0` packet parser). Treat
this as a static provider/I/O transport plus codec boundary, not as a proven
external-key-to-PCM playback path: an address-taken indirect codec setup,
runtime source-state/sourceInfo instance identity, and live invocation remain
unproven.
The direct VoicePlayer external key-to-copied-descriptor path is statically
closed. The selected Opus parser
callbacks are static integer-array transforms. The selected Opus descriptor
and a second header-recognized generic memory descriptor both have resolved
stream callbacks. The selected decoder output path is now closed through
`0x1801c4650 -> 0x1801c7ec0 -> 0x1801c481a/0x1801c483c`: returned floats are
scaled/clamped and converted to signed PCM16 samples in the caller-owned
buffer. The selected descriptor is passed at `0x1801c5239` through
`0x1801c7df0 -> 0x1801ca710`; its stream setup reaches the RIFF/WAVE parser
`0x18011bf00`, the `OpusHead` parser `0x1801cf560`, and packet path
`0x1801cc1b0` before that PCM16 handoff. The optional decoder callback at
context `+0x2a08` remains unresolved. The exact container-to-PCM evidence is
kept in `reports/story/recovery/audio/native_decoder_container_to_pcm_flow.md`.

The codec-side callback boundary is now structurally bounded as well. The
stream reader at `0x1801c9fa0` keeps its buffered-byte counter at object `+0x48`
and an inline stream state at `+0x58` (buffer pointer `+0`, capacity `+8`,
cursor/consumed count `+0xc`); when it needs more data it loads the indirect
function pointer at object `+0` and calls it as `(context=object+0x20,
buffer, length)`. Its setup path at `0x1801ca710` copies the caller-provided
32-byte callback descriptor (`+0`, `+8`, `+0x10`, `+0x18`) and stores the
context pointer at `+0x20` before allocating the internal buffer. This proves
an explicit callback/stream handoff inside the embedded codec, but the callback
target is still indirect until each descriptor is identified. For the selected Opus path,
`0x1801c5239` passes static descriptor `0x1802b09d8`; its `+0` entry is the
memory-source copier `0x1801c44d0`, which copies from context `+0x60` while
tracking available bytes/offset at `+0x68`/`+0x6c`. When that buffer is
exhausted, the context object's indirect vtable slot `+0x80` is the matching
provider release/advance operation; the file provider's actual queued
acquisition is its `+0x78` (`0x1800b85c0`) path. This proves the codec consumes
a provider-backed prefilled source and that the provider descriptor format is
compatible with the default-I/O read boundary; the active pump's
`0x18028c020 +0x30 -> 0x180024270` call statically joins those descriptors to
`ReadFileEx`; the fixed completion callback is tied to the same provider
allocation/queue through request `+0x48` and secondary interface `+0x90`. It
still does not identify a live VoicePlayer key/path occurrence or unobserved codec
descriptors. The header-recognized generic memory path `0x1801c4650 ->
0x1801ca9a0 -> 0x1801cfe80` builds a four-entry descriptor at its local
`+0x30`: `+0 = 0x1801cfd80` copies/advances bytes, `+0x8 = 0x1801cfe00`
updates the cursor, `+0x10 = 0x18010ad90` returns the source pointer, and
`+0x18 = 0x1801cfd70` frees the wrapper. An exhaustive direct-call scan of the
selected `.text` finds only `0x1801c7e3e` and `0x1801caa1c` as calls to stream
setup `0x1801ca710`: the first receives static descriptor `0x1802b09d8` through
`0x1801c5255 -> 0x1801c7df0`, and the second receives the local generic
descriptor through `0x1801c46f9 -> 0x1801ca9a0 -> 0x1801cfe80`. No additional
direct setup callsite or direct descriptor literal is present; an address-taken
indirect caller would remain outside this scan. No direct store to decoder context
`+0x2a08` appears in the current AkSoundEngine function table; only the read at
`0x1801c8b64` is present, so that optional callback's initialization remains
unresolved. A raw selected-build scan also finds no absolute pointer literal or
RIP-relative memory operand resolving to stream setup `0x1801ca710` or generic
reader `0x1801c9fa0`; this excludes an in-image static setup reference for
another descriptor table, but not a runtime-computed or externally supplied
function pointer. A direct and overlap-aware audit of all selected `.text` memory
operands covering `+0x29f0..+0x2a10` finds stores at `+0x29f8`/`+0x29fc` and a
qword at `+0x2a00` ending at `+0x2a07`, but no write reaching `+0x2a08`.
This is a bounded negative result, not proof that the callback is never
initialized: its owner may be outside the selected function table or be
populated through an unresolved indirect path. Codec state path `0x1801c8d11` directly calls the stream reader;
an exhaustive direct-call census finds ten valid direct readers of
`0x1801c9fa0`: `0x1801c83fd`, `0x1801c8d11`,
`0x1801c96bf/0x1801c985a/0x1801c9909`, `0x1801c9adb`, `0x1801c9cca`,
`0x1801ca1eb`, and `0x1801cb8ee/0x1801cbd1b`, grouped in containing functions
`0x1801c8160`, `0x1801c8c60`, `0x1801c9670`, `0x1801c9a00`, `0x1801c9c80`,
`0x1801ca110`, and `0x1801cb270`. Each passes a stream object plus a range or
output descriptor; this closes the direct read-consumer census, but it does
not identify additional setup descriptors or indirect callback targets.
The matching direct-call census finds three valid decoder calls to
`0x1801c7ec0`: `0x1801c477b` in `0x1801c4729`, plus `0x1801c49bc` and
`0x1801c4a3e` in `0x1801c499c`. The first call's returned floats flow through
the signed-PCM16 handoff below; the latter two are the initial decode attempt
and the retry after provider refill `0x1801af960`, with return codes driving
decoder state and consumption. No other direct decoder call exists in the
selected `.text`; this expands decode-consumer coverage but does not prove an
indirect decoder target or another PCM sink.
The runtime contract now hooks the exact decoder entry `0x1801c7ec0` with its
verified ABI `(decoder, float-output slot, frame-count slot)`. It samples
decoder owner `+0x18 -> +0x268` (source-state key), provider interface `+0x58`,
the output float-buffer/frame-count slots, and native return address before
and after the call. Return address `0x1801c4780` identifies the direct caller
whose static body writes PCM16; `0x1801c49c1` and `0x1801c4a43` identify the
refill/retry callers. The importer exposes intersections with the key-to-decoder registry,
source-provider preparation, and source-state keys; these are continuity into
an actual decoder invocation. Provider preparation's `sourceOwner` and the
decoder-entry `decoderOwner` are also intersected to test one native owner
instance across the sourceInfo/provider and decode boundaries, while static
caller disassembly still supplies the float-to-signed-PCM16 interpretation.
The sourceInfo-selector hook additionally records the post-call selected table
entry key, candidate descriptor pointer (`outputDescriptor +0x10`), and
candidate auxiliary field from its output descriptor. The source-info consumer
and provider-preparation hooks record the copied source-owner descriptor at
`source +0x338` (`decoder +0x18 -> +0x338`) after the consumer returns. Matching
those pointers is a bounded selector -> source-owner continuity check. An exact
input/selected-entry key match or pointer match still does not join that entry
to an external file, handle, or PCM buffer.
The optional source-state initializer hook at `0x1800d1f90` samples the
destination source-state object, `sourceConfig +0x34`, incoming `sourceInfo`,
and post-write `sourceState +0x268/+0x288`. The importer intersects those
objects and keys with manager joins, provider owners, decoder owners, and
sourceInfo pointers. This is initialization continuity, not proof that the
managed external key selected that instance.
The constructor hook now records its native `u32` status return (`1` for the
successful registration branch, `0x34` for the allocation-failure branch in
this build) as `registrationStatuses`; this separates a failed registration
from an absent runtime key match without claiming a source-state, file, or
PCM join.
packet wrapper `0x1801c8b60` reaches `0x1801cc1b0` at `0x1801c8bda`. Its
callee-frame `+0xf0` callback slot is populated by every direct
`0x1801cc1f0` caller: `0x1801c6490` and `0x1801c6bf2` pass `0x1801c6f90`, an
integer-array transform, while wrapper `0x1801cc1e1` passes `0x1801cbff0`,
another integer-array transform. Those known callbacks are invoked at
`0x1801cc4ce/0x1801cc532/0x1801cc57e`, so this parser branch is not a PCM
sink. The
selected decoder caller `0x1801c4650-0x1801c48cc` invokes generic decoder
`0x1801c7ec0` at `0x1801c4770` with an output-pointer slot; after return it
loads float samples at `0x1801c481a`, scales/clamps and converts them with
`cvttss2si`, then writes signed 16-bit samples at `0x1801c483c` while advancing
the output byte count/pointer. This is a static decoded-float to PCM16 handoff,
not a live playback observation. The
runtime probe records both the indirect stream boundary and the bounded memory
copy/release boundary as observations only; it does not classify them as
decoded PCM.

The native default-I/O branch is now bounded without treating a mid-function
offset as a hook boundary. `0x180004a20` validates/builds the open descriptor
and calls the I/O object's virtual open slot; the `.rdata` vtable contains the
real open implementation at `0x180005030`. Its body passes the UTF-16 path to
the imported Windows file-open call and records the resulting handle, while
the device vtable separately exposes setup/release `+0x28/+0x30/+0x38`
(`0x180024630`, `0x1800248e4 -> 0x1800248f0`, `0x180024190`), dispatch
`+0x58` (`0x180024200`), `ReadFileEx` `+0x60` (`0x180024270`), and
`WriteFileEx` `+0x68` (`0x1800243e0`) on the primary address point. Init
`0x180001060` installs the composite object's active address point
`0x18028c020`; `0x180023f90` passes its `+0x8` address point into
`0x1800b5fc0`, and `0x1800b7310` stores it at stream-manager `+0x428`. The
pump's `0x1800bc45d` calls active `+0x28/+0x30/+0x38` as
`0x180005430` (provider/state dispatch), `0x180024270` (direct
`ReadFileEx`), and `0x1800243e0` (`WriteFileEx`), so the provider-to-read
transport is statically closed.
The old `0x180005080`
offset is inside the `0x180005030` mode-selection branch, so the runtime probe
now hooks only `0x5030` and decodes its path argument. This improves future
key-to-file correlation but is still not a live correlation or PCM proof.

The same binary has an alternate provider-batch wrapper at `0x180005430`. It
filters provider pointers through `0x180005870` and then calls the device
dispatch helper at `0x180024200`; that dispatch invokes each provider's
`+0x18` callback and does not itself call a Windows file API. The active pump
address point then calls `0x180024270` directly. The concrete
`0x180024270` entry has an exact ABI once entered: descriptors advance at
`0x18` bytes; descriptor `+0` is a provider object whose `+0x10` carries the
`ReadFileEx` handle, while descriptor `+0x10` is the ordinary carrier at
request `+0x8`. For request base `R`, carrier `+0` is `R+0x8`, `+8` is the
byte count at `R+0x10`, `+0x10` is the buffer/source at `R+0x18`, `+0x18` is
fixed callback `R+0x20 = 0x1800bf190`, and `+0x28` is the ring helper at
`R+0x30`. This closes provider-dispatch-to-ReadFileEx and completion-to-request
recycle/release. The request retains the primary provider base at `+0x48`,
while the decoder receives the secondary interface at allocation `+0x90`, so
completion and codec queue ownership share one provider allocation. The
selected decoder caller performs the decoded-float to signed PCM16 write; this
does not prove a live source-state-to-file correlation, any address-taken
indirect codec setup, or the optional decoder callback target. The direct
VoicePlayer external key-to-copied-descriptor path is statically closed.
The provider callback identity is now statically bounded: `0x1800b9530`
allocates the 0x70-byte state record accepted by the wrapper, and
`0x1800b9647` stores `0x1800b92c0` at record `+0x18` and its owning source at
`+0x20`. The `0x180024200` callback therefore resolves to
`0x1800b92c0 -> 0x1800b8b00`, which performs provider queue/state transitions;
it is not the codec stream object's indirect callback at `+0`. Provider
allocation identity is therefore closed. The sourceInfo provider's relevant
secondary vtable slots are now resolved (`+0x20 -> 0x1800b8820`,
`+0x28 -> 0x1800ba3e0`, `+0x58 -> 0x1800babb0`, `+0x78 -> 0x1800b85c0`,
`+0x80 -> 0x1800b9a00`), and decoder slots `+0x120/+0x130/+0x140` resolve to
`0x1801aebf0/0x1801afc80/0x1801afaf0`. Remaining static gaps are other
address-taken codec callbacks, source-state-to-provider path correlation,
and live invocation. The direct
VoicePlayer external key-to-copied-descriptor path is statically closed.

The corrected section mapping also closes a negative managed-side fact for the
external callback: `_OnExternalSourceEventCallback` at `0x1843c7930` marshals
callback-info fields into the managed callback/cleanup helper at `0x1843c7ae0`
and does not directly invoke file I/O or codec code. In the current
`_PostEventWithExternalSource` body, the only direct `AkExternalSourceInfo`
setter calls are the external cookie, `szFile`, and codec setters; the callback
body has no direct setter or I/O edge. Native descriptor copying still supports
optional in-memory pointer/size fields, so their live presence remains a
capture question rather than a managed static claim.

The recovery tree now has a reusable, fail-closed runtime probe for that last
join in `scripts/story_recovery/audio_runtime_trace_hooks.json`. It verifies
the selected `GameAssembly.dll`, metadata, and `AkSoundEngine.dll` hashes before
attaching optional native hooks at external-source lookup/descriptor transport,
Wwise source-media lookup, source-manager key join, key-to-decoder registry,
source/provider preparation, file-open, asynchronous-read, codec-stream, and
codec memory-source-copy boundaries. The join hook records both the requested
key and source-state `+0x268`; the registry hook records the key and active
decoder pointer. The provider-preparation hook follows decoder `+0x18` to owner
`+0x288` and reads the descriptor `+0x10` UTF-16 candidate. The descriptor-copy hook observes the
bounded `AkExternalSourceInfo` fields (cookie, codec, UTF-16 `szFile`, and
optional in-memory pointer/size), while the source-manager constructor hook
records the source key and descriptor allocation retained at manager `+0x38`.
The async hooks also expose the first request transfer pointer and completed
slot `+0x18` request pointer, without assuming they are the codec callback.
The codec hooks preserve indirect
callback/context and bounded source-buffer fields. Imported
`audio_native_*` rows include raw/decoded scalar arguments and bounded descriptor
snapshots both before and after the native call; the managed probe also covers
`_PostEventWithExternalSource`, callback pumping, and
`_OnExternalSourceEventCallback`. The importer also publishes bounded
`nativePairing.keyLifecycle` intersections for registration, manager join,
decoder registry, source-media lookup, descriptor path, and file-open path.
The explicit `registrationManagerJoinRequestedKeys` and
`registrationManagerJoinStateKeys268` fields directly test the unresolved
generated-registration-serial versus source-state-key equality. These are
still same-session execution observations unless pointer or managed call-chain
evidence narrows them to one request; until a real capture also correlates the
native descriptor/key with an open handle or read completion, the per-request
native key-to-file and decode claims remain unresolved.
The agent now performs a bounded hash-table scan by serial at the constructor
return and at manager join/lookup entry, publishing the registration/join
manager-entry pointer intersections. A shared pointer is stronger than a
same-session integer overlap because it identifies one native manager node;
the importer also compares the node's retained `+0x38` descriptor pointer to
the external descriptor-copy allocation when both are captured;
it still does not prove the copied descriptor, sourceInfo path, file handle,
decoder stream, or PCM belongs to that node without the later pointer/handle
chain.
The importer now also publishes `nativePairing.managedExternalPathLifecycle`.
It joins the optional `VoicePlayer.ExternalSourcePreparation` path to the
Adapter external-post path only through the captured parent-call chain, then
reports exact same-session overlaps with descriptor, provider, and default-open
path strings. Native events now carry the same-thread managed hook stack when a
synchronous bridge is active, so the importer also reports
`managedNativeContextCorrelations`; an exact descriptor/provider/open path
match in that direct stack is stronger than a same-session overlap. It still
cannot prove a later asynchronous sourceInfo instance, one file handle, codec
stream, selected branch, or PCM buffer.
Native events now also carry an exact same-thread `nativeParentCaptureId` for
attached native hooks nested synchronously inside another native hook. The
importer exposes resolved pairs as
`nativePairing.nativeCallRelations`/`synchronousNativeHookNesting`; this
separates true interceptor nesting from same-session adjacency, but remains
runtime call-structure evidence rather than an asynchronous ownership, file,
decoder, or PCM join.

The same manifest now includes an optional current-build managed hook at
`GameAssembly.dll+0x3abef40`, where `VoicePlayer._PlayVoice` enters the
external-source preparation helper. Its ABI is statically recovered as
`rcx=formatted externalSourceKey`, `rdx=wwise Event`, `r8=audio-object/game-object
argument`, and `r9=voice handle id`; the hook records the formatted key before
the helper reaches the external-post path, and samples the fifth ABI argument
(`codec` at entry stack `+0x28`) as `voicePreparationCodecs`. This closes the intended managed
path-resolution observation point for a future authorized capture, but remains
unobserved in this checkout and cannot substitute for a native key-to-open or
key-to-PCM correlation.

`AIBark` is a separate high-level request layer. The current binary proves
`BarkSystem.Bark(AIBarkType)` resolves a bark id through its runtime dictionary,
then `AIBarkManager` reads the authored `AIBark` row and forwards its trigger
key, bark voice type, and speaker type through
`VoiceManager.PostAIBarkVoiceEvent` to `VoiceBarkProcessor.AIBark`. Generated
responsive contexts carry the matching bark rows and fingerprint-locked method
addresses. Enemy `common_attack`/`common_escape` voice definitions are not
present in that trigger-key catalog and remain unresolved rather than being
inferred from their names. Current CN coverage has 1,108 unique authored
response ids: 1,069 are already terminal story-line matches, 25 more have
direct decoded media, one resolves only through an exact Wwise Event, and 13
`sentenceType=32`/`speaker=any` ids have no AudioDialog, AudioVoTone,
AIBarkText, decoded-media, or current Wwise Event object. Those 13 remain
explicit authored-response gaps rather than synthetic audio identities.

Enemy response actions have a second exact native route. The current
`EnemyTriggerVoiceAction` static dictionary maps voice types `0..4` only to
`combat_alarm`, `combat_intobattle`, `combat_fighting`,
`combat_outbattle_flee`, and `combat_kill`, then `OnExecute` passes the chosen
key to `VoiceManager.ResponseOnEntity`. Fixed native callers additionally
prove `combat_hurt_lowhp`, `combat_hurt_stun`, `combat_alarm_yell`,
`defence_running`, `defence_reachcore`, and `combat_outbattle_flee` placements.
Neither `common_attack` nor `common_escape` occurs in the action dictionary or
the complete fixed-literal caller set. Two `common_attack` definitions do have
exact ResponsiveDialog membership and are resolved at that authored trigger
level; the other 34 `common_*` definitions remain a consumer-ownership gap
rather than a semantic alias for combat/flee behavior.

AudioDialog, responsive, and other patched tables merge StreamingAssets with
Persistent overlays. Shared SFX/music and language voice stay separate. Same-id
media in different packages or roots remains separately visible.

## Source graph

Primary database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

Typical queries:

```bat
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Graph edges retain source and evidence kind. Exact foreign keys, PPtrs, typed
binary paths, and authored contexts remain distinguishable from inferred name
joins. The default export graph includes only original AssetMap rows consumed
by WebUI material, shader, texture, and FMV edges; use `--full-source-graph` for
exhaustive Unity-object investigation.

## Diagnostics

Use generated reports for changing schemas, inventories, counts, fingerprints,
addresses, and exhaustive evidence:

```text
reports/export/
reports/assets/
reports/source_graph/
reports/story/build/
reports/story/recovery/
```

Do not copy volatile inventories into this file.

## Remaining gaps

- Audio recovery queue: runtime-dynamic completion delegate/final
  `AkSoundEngine.PostEvent` and native playing-id/Wwise selection; authorized
  runtime source-state → provider/file/decoder/PCM correlation for one
  VoicePlayer request; and ownership/use evidence for `unknownUse` media, which
  remains identity-only.
- Server-side mission/property producers and activation policy.
- Active IFix/server combat overrides, live targets, evaluator chronology, and
  blackboard values.
- Additional family-specific MemoryPack and FlatBuffer schemas.
- Deeper Buff/Skill nested action semantics with fail-closed version gates.
- Broader exact world-streaming and scene decoding.
- Scene audio placement still needs a structured scene-streaming/instance
  relation: current emitter rows are source prefab definitions and do not prove
  a placed level instance, even when their AssetMap identity is exact.
- Runtime projectile spawn ownership and remaining enum/branch semantics.
- More exact gameplay-to-asset, animation-controller, effect, and audio joins.
- Runtime-selected Wwise branches and per-language playback policy.
- AudioCue condition truth, runtime variable values/mutation, handler dispatch,
  and cue/Event execution remain unobserved; the serialized AST is not a
  runtime evaluator.
- Audio native playback: per-request source-state/sourceInfo instance to the
  concrete opened handle, any address-taken indirect codec setup, optional
  decoder callback, and a live verified capture remain unobserved. The runtime
  contract can now compare the default-open provider-context `+0x10` handle
  with the async-read descriptor provider `+0x10` handle; no verified capture
  has produced that equality or the decoder-entry intersections yet. The direct
  VoicePlayer external key → `AkExternalSourceInfo.szFile` → copied-descriptor
  path is statically closed. The
  serialized Wwise source-cookie to managed external-cookie join is closed;
  the selected decoder's
  decoded-float to signed PCM16 handoff is statically closed, as are the
  provider allocation and ReadFileEx completion/recycle join.
- Public names for RoomVerb private SetParam IDs 100..110 (native use roles are
  now bounded), Convolution Reverb's two private fields (one forwarded scalar
  whose current CPU consumer read is unobserved, plus one forwarded byte), and
  Mastering Suite
SetParam IDs 100/200; downstream live Audio/Aux send chains and runtime DSP
selection remain unresolved even though all current v150 Bus InitialFX counts
and authored slots are now parsed.
- Per-system negative/certification reports that remain actionable after input
  drift.
