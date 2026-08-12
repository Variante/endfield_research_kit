# WebUI

`webui/` is the primary supported interface: a static browser over generated
Endfield research data.

## Run

From the repository root:

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` when it is already running. Generated payloads
under `webui/data/` are builder outputs and must not be edited by hand.

## Pages

Normal navigation exposes:

- **Story:** dialog, radio, SNS, cutscenes, options, media, recovery labels,
  and evidence-aware ordering.
- **Characters:** grouped names, source evidence, aliases, linked assets, and
  ascending or descending sorting by name and evidence volume.
- **Gameplay:** characters, weapons, equipment, enemies, usable items,
  progression requirements, skills, projectiles, assets, and recovered audio.
- **Assets:** exported images, models, materials, video, and metadata.
- **Text:** searchable localized table rows.
- **Updates:** differences between previous and current exported game data.

**Mission Pipeline** appears only with `Show debug info` and carries an under-
construction banner. **Audio** is a normal page and carries the same banner.
It exposes the current binary-validated runtime
model, Wwise HIRC object families, authored event contexts, typed possible
media leaves, the cross-system `trigger_contexts.json` rows, and the physical
decoded-media inventory without presenting the offline graph as a live
 playback trace. Trigger contexts keep authored definition, ownership or
selection, media availability, and runtime execution as separate evidence
 states. Timeline rows may therefore show an exact serialized clip request
 with timing and no playable media when its authored key is absent from the
 current Wwise index.
The Audio runtime panel also summarizes trigger-context coverage by authored
route, including `envTalkGreeting` and `remoteCommonAudio`, and shows scalar
Timeline runtime-contract counts plus `AudioMusicPlayable` action/skip-policy
counts without eagerly loading the large trigger-context detail shard.

The standalone Progression and Combat & Projectiles pages are retired. Their
useful player-facing data now appears in Gameplay; raw combat relationships,
projectile matching evidence, and unresolved ownership remain debug-only.

## Frontend map

- `index.html`: application shell and page containers.
- `style.css`: shared layout, controls, cards, and media presentation.
- `app.js`, `app_tree.js`, `app_labels.js`: Story loading, rendering, tree,
  labels, filters, and shared media behavior.
- `reference.js`, `assets.js`, `updates.js`: Text, Assets, and Updates pages.
- `src/features/characters/`: Characters page and live override editing.
- `src/features/gameplay/`: Gameplay page and integrations.
- `src/features/audio/`: lazy, virtualized Audio page.
- `src/features/mission_pipeline/`: debug-only mission evidence view.

## Data contract

Important generated roots:

```text
data/manifest.json
data/lang/<LANG>/index.json
data/lang/<LANG>/conv/
data/lang/<LANG>/mission/
data/lang/<LANG>/reference/
data/lang/<LANG>/characters/index.json
data/lang/<LANG>/gameplay/index.json
data/lang/<LANG>/gameplay/sound_effects.json
data/lang/<LANG>/audio/{index,events,media,trigger_contexts}.json
data/gameplay/projectiles.json
data/mission_pipeline/
data/assets/index.json
data/assets/gameplay_refs.json
data/assets/story_media.json
data/updates/latest.json
```

Gameplay loads its base index and optional combat, projectile, audio, and asset
sidecars independently. Missing optional sidecars must degrade to the base
record instead of breaking the page. The combat builder exposes a
visible degraded reason when its source graph is absent or stale.

The standalone Factory, World, and Presentation pages are retired alongside
Combat & Projectiles. `export.bat` no longer runs
`build_economy_data.py`, `build_world_data.py`, or `build_presentation_data.py`,
and `data/lang/<LANG>/{economy,world,presentation}/` is no longer generated.

Legacy `data/game_data/` is not an active semantic-page input. Its local
decoder recognizes the current 47-member SkillData and 30-member BuffData
schemas, fails visibly on member-count drift, and now reaches exact post-id tail
boundaries for the current merged export. The output remains a broad diagnostic
preview: byte-bounded stack/ignite/smart-target action bodies may still be
semantically partial. Do not surface it as observed runtime combat evidence.

The Audio overview and Event inventory load only when its debug view is opened;
the larger media inventory remains deferred until the Media mode is selected.
Both lists are virtualized, and selecting an Event fetches only its keyed detail
shard before rendering contexts, branch evidence, and players. Selected records
show only record-specific evidence and playable media; corpus-wide runtime
statistics remain on the unselected Audio overview.
Media rows and player cards use the Event id as their display title when the
file has exactly one known related Event; files with zero or multiple related
Events retain their normal media/file title. Media defaults to unknown-purpose-
first order and can also be sorted by file title or duration in either
direction. Exact generated Story-line bindings are terminal purpose evidence,
record their binding count, and sort after unresolved-purpose media. Detail
facts include duration and average file bitrate. In the left Media file list,
duration, size, and bitrate stay right-aligned opposite the filename while the
second row is reserved for purpose and evidence. Playable recovered audio is served from
`/export_full/structured/Audio/{shared,<LANG>}/`. AnimeStudio and the normal
builder default to lossless `.flac` files and write those paths into Story, cutscene, projectile,
and Gameplay sound payloads; the frontend uses the same native audio control
for FLAC and WAV links. Event and Media selections are deep-linkable, including
restoring the Media dataset after a reload, and expanded players expose the
resolved source file as a direct link. Players stay expanded by default; only
a playback-root/relation group with more than 20 bound media files starts
collapsed, bounding unusually large Wwise fan-outs without hiding ordinary
Event players. Legacy WEM files remain indexable for diagnostics but
are not a browser-playable output format. Event details list every typed
possible media leaf together and group it by Play root and Random, Sequence,
Switch/State, Layer, or direct-Sound evidence. Partial typed graphs and
byte-identical decoded content under distinct media ids remain explicit. Events
whose typed root Actions contain only control operations are labeled as control
Events instead of being presented as playback Events with missing media.
Authored Event names that do not resolve to a Wwise Event object and decoded
media whose playback location is unknown remain separate visible states: the
former retains its authored trigger contexts, while the latter does not imply
an Event, owner, or runtime trigger that has not been recovered.
The Audio recovery-status filter exposes Wwise-object resolution for Events and
placement coverage for Media. Media placement is partitioned into direct dialog
media, recovered authored Event context, Event relation only, and unknown; the
overview reports the same generated counts. A byte-identical
Event type and Media purpose are deliberately separate facets: Event type is
derived from Event semantics and authored evidence, while Media purpose comes
from the decoded media path. Media rows show the types of their related Events
as secondary evidence without replacing their own purpose classification.
`wwise/unknown/<mediaId>` occurrence is omitted from the logical inventory when
the same storage root already has a stronger categorized copy. The files remain
on disk, while different-byte and cross-storage same-id collisions remain
visible.
Decoded media can also resolve to a typed Wwise Sound codec-media object while
no Event reaches its parent container branch. That is shown as a resolved
library definition with unknown playback location, distinct from both an Event
relation and a completely unidentified decoded file. HotfixAudio same-ID
replacements inherit the exact Event relation while retaining separate players
when their bytes differ.
When such an unreachable definition shares an independently packaged bank with
a named Event, the UI may show that Event as a bank-colocation purpose hint.
This never becomes a playback edge unless the Event action tree reaches the
definition's Sound/container branch.
The current dataset has no such definition-only rows: seven former cases were
resolved after the v150 container parser began consuming variable-length
NodeBase FX/metadata prefixes before reading `DirectParentID`.
SNS Voice message Events retain their exact dialog/content/speaker/duration
placement and click-to-PostEvent plus stop-by-playing-id route; the static
handler does not claim that the user clicked the message.
The HIRC inventory lists the fingerprint-locked scanned PCK set, including
HotfixAudio packages discovered from the Persistent VFS index. An unresolved
authored Event shows its exact current AudioHashGenerator hash and means that
hash is absent from the scanned Event objects; it is not merely a failed
filename lookup. Hotfix media uses the normal shared browser paths and retains
its `HotfixAudio` source label, including replacements whose numeric media id
already existed in the base package.
Every raw Event object is now represented, including hashes with no recovered
authored name or trigger. Those records expose exact typed library/media
relations under stable `hashed-event:0x...` identities and are labeled
separately from both named Events and authored references absent from Wwise.
Authored names recovered later from LevelScript, Timeline, or other semantic
contexts merge into the same raw HIRC row by exact Event hash, so the Audio
view does not duplicate a named row and a `hashed-event:*` row.
Their media is classified as Event-related with authored placement unknown,
not as having no playback relation.
LevelScript `PlayVoice`/`PlayVoiceNarrative` `_voId` values are kept outside
the Wwise Event namespace and joined by exact `AudioDialog` path stem to their
playable voice media. This proves the authored selection and script location,
not that the LevelScript action executed.
Exact `AudioDialog` path-hash/voice-id/Event-id matches recover voice Event
names without guessing. The Event detail keeps an `AudioDialog` definition,
each `ResponsiveDialog` speaker/trigger response, and each `AudioVoTone`
variant as separate contexts. A response row means the Event is an authored
possible choice for that trigger family; a tone row is only a possible id
substitution. Neither is displayed as an observed runtime selection, and a
definition or tone row alone does not upgrade media to a known playback
placement.
Exact `skill_id.dic` names that also have a same-name `SkillData` file and hash
to a current Wwise Event recover identity only. They are labeled as SFX but do
not gain a skill trigger, owner, or playback location unless a separate audio
consumer edge is recovered.
Typed voice-table fields also recover exact current Wwise names for voice
defaults, narrating/radio channel selection, per-voice overrides, and response
templates. Their Event details retain the table field, bounded logical row
samples, and native selection route while explicitly marking the live voice
and branch choice unobserved. External Source Events do not acquire a decoded
player merely because their authored route is now known.
Numeric External Source paths use 64-bit FNV-1a authored-path identities. The
builder omits one from the logical Media inventory only when the id exactly
matches the current language/AudioDialog path and the canonical file has the
same SHA-256 bytes. A bounded unique path preimage may recover media identity,
but without a current AudioDialog row or trigger it remains an unknown playback
location and does not acquire a speaker, dialog, or Event.
Activity/UI table Events are promoted only when the field has a current
metadata getter, the decrypted Lua consumer reaches `PostEvent`, `PlayAudio`,
or `SetAudioOnOpen`, and the exact hash is a current Wwise Event object. Event
details distinguish activity and popup BGM, panel-open audio,
video-synchronized audio, region switching, and domain-upgrade animation
stages. Video audio retains its possible Wwise leaves and playing-id stop/seek
contract while marking the selected video and branch execution unobserved.
Decrypted installed-Lua callsites are shown as a separate runtime-context
family. Direct `PostEvent` string literals can resolve a Wwise Event name and
retain their exact VFS source, line, and expression; RTPC, AudioCue, and
indirect literals are not promoted to playback Events. These rows explicitly
say that branch execution was not observed.
Managed string-pool names recover Event identity only when their exact hash is
a current Wwise Event object. Without a typed consumer they do not establish a
playback location; literals absent from both the current Event inventory and
all typed consumers are not emitted as unresolved Event requests.
Event rows use the same purpose-first investigation order as Media: no recovered
consumer context sorts first, identity/definition-only evidence stays at
unknown placement, and authored trigger contexts sort after those gaps. Bank
resolution is separate—a missing current Wwise object does not mean unknown use
when a Timeline, Lua, animation, table, or other typed trigger is already known.
Pure control Events are also separate from playback gaps: exact Wwise actions
such as `setState` establish their library-side role, while the still-missing
external caller remains visible as an unresolved placement.
The v150 Action classifier also treats Pause, Resume, Mute, Unmute, Stop,
Game Parameter, Switch, Trigger, and any other completely typed non-Play Action
as library control. A complete zero-Action Event is a separate empty definition.
Neither state becomes a known caller or observed execution. Event details show
the exact operation types and the current collection surfaces that supplied an
authored name; stale names present only in an earlier generated index are not
retained as unresolved requests.
Exact serialized MonoBehaviour `AudioId` fields are a separate authored-config
context. The builder prefilters TypeTree schemas in the StreamingAssets and
Persistent object indexes, opens only their exact raw PathID objects when the
compact scalar index omitted a value, and accepts hashes present in the current
Wwise Event inventory. Event details expose the field role, component,
GameObject hierarchy/position when available, and serialized source. This
identifies a component/state/effect placement but does not claim component
instantiation, callback/state execution, Event posting, selected media, or
audibility. RTPCs, generic integers, PathIDs/raw words, tone-selection rows,
and responsive-choice membership are excluded. The sole typed raw-word
compatibility path is the current IL2CPP-validated six-field/24-byte
`Beyond.Gameplay.PlayLineSound` managed-reference payload; it requires exact
class, namespace, assembly, layout, and length identity. A future exporter
output with named `soundSpawn`/`soundFinish` fields uses the same evidence
contract.
`AudioGlobalConfig` lifecycle `AudioId` values use the same exact-identity
boundary. When its raw MonoBehaviour JSON is absent from a Story-focused
export, the builder reconstructs only the scalar paths retained by the complete
object index. The trigger surface keeps state direction/mask, entity kind/id,
and serialized identity, but does not claim that the lifecycle condition ran,
the Event was posted, or a Wwise media leaf played.
Anonymous Events may also show an exact shared Play-target-set relation when a
named authored-context Event in the same bank reaches the identical complete
set of Wwise targets. This can recover the broad output category and avoid
re-investigating identical library topology, but it does not copy the named
Event's trigger, owner, Story placement, or resolved-purpose status. Partial
target overlap is not enough.
When the stronger target-set relation is unavailable, an Event may instead
show that its complete decoded Wwise media-ID set exactly matches an
authored-context Event within the same PCK. This is a final-media-leaf relation
only: Event/Action/container behavior may differ, so the UI does not inherit
category, trigger, owner, playback location, or resolved-purpose status.
Partial media-set overlap is likewise rejected.
Version-150 music Events use the same evidence boundary but additionally show
typed Music Switch, playlist, segment, track, and track-source nodes; these are
possible authored paths, not an observed current track.
Skill contexts separately tag exact Gameplay-action-to-SkillData dependencies and
inferred child-skill-family ownership. Their evidence records whether the Event
was found as a complete length-prefixed reference in SkillData or through an
exact BuffData chain; the generic scan does not recover a field/callsite, and
runtime condition/timing remains explicitly unresolved for dependency-only
rows. Decoded BuffData `PlaySoundActionData` adds exact authored frame windows,
stop/fade lifetime, routing, selector hints, and time-dilation controls for the
recovered subset; `TargetSettings`, live activation, and Wwise branch selection
remain explicit gaps. Exact PlaySound actions have their own Audio Event filter
and stay visible even when no displayed skill owner is proven. All trigger tags
and source/action fields are searchable.
Interactive-object contexts keep global model/sub-template defaults separate
from per-entity `InteractiveData` component overrides. Both expose exact
lifecycle/custom state, identity, source path, and Event evidence; global audio
policy adds entity-init and enter/exit state-mask Event mappings. These are
authored state-entry requests, not live traces or Wwise SetState operations.
Projectile contexts expose each exact nonzero launch, loop, reach, hit, block,
finish, or proximity-sizzle Event field with projectile identity and source
PathID. Skill ids stored by the projectile remain template references rather
than proof that a displayed skill spawned it; lifecycle execution and Wwise
branch selection remain unresolved.
The Audio control catalog keeps cue and parameter entities separate from Wwise
Events. Only AudioCue behavior expressions with `exprType=3` become Event
contexts; `exprType=8` operands, Global `musicCue*` IDs, and RTPC names retain
their own typed records and missing-definition state. LevelScript `PostAudioCue`
names are joined through the shipped exact string hash to cue definitions; the
script action, handler condition, and Wwise branch remain separate runtime gates.

## Runtime overrides

Manual inputs live under `webui/overrides/`:

- `story_order.json`: complete user-managed order for each mission.
- `options.json`: manual option positions and response routes.
- `narrative_videos.json`: explicit video attachment, suppression, and audio
  inheritance rules.
- `character_merges.json`: additive identity merges and a `flagged` queue.
- `character_name_overrides.json`: replacement display names keyed by the same
  canonical character ids.

Story overrides require a Story rebuild. Character merges and display names
are edited live from the Characters page through `serve.py`; their editing
controls appear only with `Show debug info`, and they do not require rebuilding
generated character data. Self-merges and cycles are rejected, and merging a
flagged source clears that flag.

## Behavior contract

### Shared navigation

- Recovery issue and method filters remain visible in normal and debug modes.
- Source panels, mission evidence, Story order editing, and Characters name or
  identity override controls stay behind `Show debug info`.
- Story reset returns to Story sort while preserving expanded mission groups.
- Enabling debug reveals Mission Pipeline without repositioning the navigation
  bar. Disabling debug while Mission Pipeline is active moves to Gameplay and
  normalizes the URL.

### Story and media

- Every view with at least two rendered audio/video files exposes a shared
  `Play together` chooser. Users can select any files in the active view and
  play them simultaneously or sequentially, or stop either playback mode;
  audio files with exactly equal browser-reported durations are selected by
  default, and one toggle selects or unselects every audio clip without changing
  video selections. The chooser follows the shared Chinese or English
  interface-language switch.
- Story uses the same persisted female/male segmented selector as Gameplay.
  Gender-authored dialogue text, voice, images, video, and gender-only cutscene
  lines update together, and the selection stays synchronized across both
  pages.
- Character Reactions use the same per-line catalog layout as character Wiki
  voice entries: each reaction shows its authored trigger as the row label;
  response ids, trigger sets, audio paths, and fallback evidence remain in the
  generated payload and debug trace.
- `sns_emoji_*` renders as small inline emoji with no hover or modal.
- `sns_image_*`, `sns_sticker_*`, `cg_image_*`, and related non-emoji media
  preserve normal image proportions. The compact index keeps one preferred
  Sprite export per logical CG; the byte-identical Texture2D wrapper has a
  different Unity PathID but is not shown as a duplicate Story row. `_f` and
  `_m` files share one selectable `CG Image` / `剧情CG` row and follow the
  Endministrator gender selector. Media-only CG rows render at full opacity.
- `dlg_biglogo_*` uses the same `剧情CG` rows and gender-token grouping;
  `cg_image_e2m6_1_m` is excluded because `dlg_biglogo_e2m6_14_f/m` are the
  actual authored gender pair. `remotecomm_image_*` appears as Remote Comm
  image rows grouped by the mission id encoded in each filename. The two
  `e7m3` BigLogo pairs use an unsuffixed default/female file plus `_m`; these
  are grouped as gender variants too.
- Hover and modal previews remain inside their frame and the viewport.
- Definition-only rows, non-owning context, exact playback, and mission
  ownership remain visibly distinct.
- Mission or scene order is never inferred from registration, source-list
  order, file order, or code addresses.

Useful inline-media fixtures:

```text
test_sns_emojicomment
test_sns_sticker
sns_topic_map02_lv005_12002
```

### Characters and Gameplay

- Character groups use canonical ids derived from constituent table/asset ids,
  not localized display text, so overrides survive language builds.
- Filename-derived identities pass documented exclusion lists in
  `scripts/build_character_data.py`; add exclusions only after tracing the
  exact false-positive source family.
- Playable-character details keep breakthrough requirements, skill/talent
  costs, potential art, stats, and identity assets in their owning sections.
- Gameplay keeps the Endministrator as one canonical character and exposes a
  persisted female/male variant switch for portraits, active action rows,
  Story voice links, potential pictures, and recovered skill sound effects.
  Shared stats, skills, talents, and potentials remain sourced from
  `chr_9000_endmin`.
- Skill glyphs stay centered in circular controls. Normal-skill, Ultimate, and
  Combo discs use the owning character's exact `CharTypeTable.json` color:
  Cryst `#21C6D0`, Fire `#FF623D`, Natural `#9EDC23`, Physical `#888888`, and
  Pulse `#FFC000`; Normal Attack remains neutral.
- Enemy variants are a selectable difference table. Stat controls expose only
  exact `EnemyAttributeTemplateTable` points and never interpolate missing
  levels. Variants share displayed HP/ATK/DEF when they reference the same
  `attrTemplateId`; separate templates are selected independently, while born
  buffs and attribute modifiers remain variant-specific.
- Combat details distinguish authored inputs and references from the recovered
  stock-client formula. They must not be labeled as observed live results:
  IFix patches, server corrections, runtime targets, blackboard values, and
  branch selection can change the evaluated outcome.
- Character skill rows show one compact linked-projectile summary and only the
  playable Events proven through that displayed Gameplay action id's exact
  SkillData or BuffData dependency chain. A skill may legitimately have no
  separate projectile template.
- Typed Wwise possible-media leaves are listed together, with Play roots and
  switch/state/random/sequence/layer evidence shown separately; the UI does
  not present them as equivalent choices or observed live playback. Direct and
  inferred skill/enemy ownership are labeled. Related-sound groups,
  projectile phases, and individual Event lists stay expanded unless one group
  contains more than 20 playable files.
- Character-owned animation callbacks and shared Wwise animation systems are
  separate Gameplay groups. Shared footstep/cloth/material Events show owner
  counts and global reachable leaves without presenting those leaves as the
  character's private sound library; opening one Event still lists every
  playable file together. Inferred character-skill links, animation systems,
  and profile voice remain in the final character section; enemy audio remains
  at the end of the enemy page. Compact bank, Stop, selector-node, and
  child-edge counts substantiate large Wwise fan-outs. Animation callbacks and
  controller evidence are collected from both StreamingAssets and Persistent,
  with PathID reachability isolated per VFS storage root.
- Gameplay thumbnails and model paths link back to the matching Assets entry.

### Mission Pipeline

- Trigger cards preserve evidence type and original source boundaries.
- Native playback without a mission owner remains explicitly unassigned.
- Definition-only rows never become activation, ownership, or order evidence.
- Reading-popup actions use a direct serialized `_readingPopId`. Mission
  Pipeline shows the exact event/action receiver and, when recovered through
  the aligned WorldEntityRegistry script/slot plus complete embedded
  interaction record, the triggering map entity and world coordinates.
  Mission/quest ownership and Story order still require separate evidence.
- Quest topology and client-applied state do not prove server successor
  selection.
- The per-mission spatial map projects quest tracking pins and nearby
  LevelScript Story carriers onto X/Z. Positioned and unpositioned files expose
  localized hover previews; unresolved-trigger files remain a separate review
  tray. Exact interaction anchors show the nearest mission tracking point and
  3D/XZ distance for review. Spatial proximity is diagnostic only and creates
  no ownership, trigger, or Story-order edge. Exact native event producers are
  also positioned when their script/slot has one aligned WorldEntityRegistry
  entry; this reconstructs the relevant runtime-map layer without requiring a
  full scene-geometry export.
- Exact DialogTree/Timeline option finish outcomes may be shown beside the
  MissionRuntime objective that consumes the same finish ID. Each row exposes
  hash-validated original files, the structural option-node/slot scope, and
  whether the finish was explicit or the binary-validated runtime-default
  `Int32 0`. Reused localization option IDs stay separated by runtime scope.
  Each row remains a dependency, not an observed player choice or
  server-selected successor.
- Exact finish consumers without a proven option route are shown separately as
  endpoint-only dependencies. The shared recovery walks typed original
  DialogTrees from the binary-proven first serialized node, validates exact
  connection identities, and admits only reachable finish nodes. These cards
  expose the prime-node path, predecessor types, value source, and hashed
  DialogTree, MissionRuntime, binary, and metadata files. They prove an authored
  endpoint-to-objective dependency, not the route or choice that reaches it.
- Original DialogTree definition cards expose normal-option route validation.
  The binary-proven `NormalOptionData.index` selects a physical outgoing edge,
  including positions around extra-option edges, and `ShowOptions` sets
  `doNext` before normal selection. Unequal option/connection counts are allowed
  when exact indexes resolve. Unreferenced definitions, linked zero-edge nodes,
  and out-of-bounds indexes remain visibly distinct and fail closed; a missing
  edge is not presented as a terminal choice. OCR and manual overrides are
  never route evidence.
- Multi-output external-result controls show every serialized arm. Installed
  static port names are displayed when the original binary supplies them;
  other panels remain ordinal-only. A complete installed-Lua router audit marks
  each arm as bounded-produced, dynamic-index, or lacking a current shipped
  producer and exposes exact source lines and hashes. Cards attach the original
  TextAsset, GameAssembly, metadata, relevant logical Lua payloads, and current
  IFix boundary. Detached zero-edge controls are definitions, not live
  branches. None of these rows claims an observed UI result, activation,
  permanent unreachability, or sibling Story-file order.
- Manual Story order and OCR proposals are cross-reference material, not graph
  evidence.

Detailed, changing Mission Pipeline inventories belong in generated reports;
stable Story conclusions belong in `memory/game_story_recovery.md`.

## Verification

After frontend or data changes:

1. Reuse or start the default server.
2. Confirm Story, Characters, Gameplay, Assets, Text, and Updates load.
3. Toggle debug and confirm Audio, Mission Pipeline, and the Characters
   override controls appear and hide cleanly. In Audio, confirm Events loads
   first, Media loads on demand, and disabling debug returns to Gameplay.
4. Check Story reset/filter behavior and the inline SNS fixtures.
5. Open a playable character and an enemy; verify progression, variants,
   projectiles, sounds, and linked assets degrade cleanly when optional data is
   unavailable.
6. Check the browser console for new errors.

User setup belongs in the root `README.md`, script contracts in
`scripts/README.md`, and durable recovery status in `memory/`.
