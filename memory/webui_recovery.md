# WebUI recovery

## Current status

The static WebUI is the primary project surface. Normal navigation exposes
Story, Characters, Gameplay, Assets, Text, and Updates. Mission Pipeline
appears only with `Show debug info`; Mission Pipeline and Audio carry visible
under-construction banners.

Story, localized reference data, character identities, gameplay semantics,
assets, and update comparisons build reproducibly from `export_full/`.
User-managed Story order remains outside generated data in
`webui/overrides/story_order.json`.

Standalone Progression and Combat & Projectiles views are retired. Progression
requirements and useful projectile/audio summaries live in Gameplay; raw
combat, matching, and unresolved-ownership evidence remains debug-only.
The Audio tab is a normal public semantic view (`debugOnly:false`), while raw
identities remain behind its debug toggle. Gameplay sound cards use one flat
event stream with all decoded candidates listed together; shared animation
events are labeled as global Wwise graphs rather than character-owned files.
Audio players are expanded by default; a playback-root/relation group starts
collapsed only when it has more than 20 bound media candidates. Authored Event
references unresolved to Wwise objects and playable media with unknown playback
locations are separate visible states; neither is promoted into a runtime edge.
They are also first-class recovery-status filters and overview counts. Media
placement uses four mutually exclusive generated states: direct dialog,
authored Event context, Event relation only, and unknown.
An exact generated Story-line binding is a terminal purpose result: media rows
record the binding count and no longer receive deeper purpose-recovery
priority. The Media list defaults to unknown-purpose-first order; unlinked
playable media comes first, Event-graph-only media is secondary, and exact
Story-line bindings sort last.
Audio Event type and Media purpose remain separate facets because they are
derived from different evidence. Media rows expose related Event types as
secondary evidence without overwriting their path-based purpose classification.
The seven former Sound-definition-only rows were fixed by decoding the complete
variable-length Wwise v150 NodeBase FX/metadata prefix before `DirectParentID`.
All seven now have exact Event paths; the current inventory has no decoded
Sound definition without an Event path.
The Audio HIRC inventory now exposes the SHA-256-locked nine-PCK scan set and
per-package Event-object coverage, including Persistent HotfixAudio. Unresolved
Event details carry the exact authored hash and scanned-set fingerprint. The
normal shared-media inventory now includes all 402 decoded Hotfix ids and keeps
their HotfixAudio provenance even when a patch replaces a base-package media
id. Nineteen lack a Hotfix-local Event; 12 are recovered through named Events
in other scanned banks, while the final seven are reached through four unnamed
base-bank Event hashes. All 402 now have an exact Event-object relation. The 165 unnamed
Hotfix Events are separately labeled as media-playback, control-only, partial
object graph, or no-media-leaf roles.
Exact decrypted Lua `PostEvent` callsites now appear as their own authored
runtime-context family with source line and expression. RTPC, AudioCue, and
indirect literals stay distinct, and every Lua row preserves the unobserved
runtime-branch boundary.
The Audio view now includes every raw Wwise Event object: 21,712 occurrences,
21,124 unique hashes. Exact `AudioDialog` path-hash/voice-id/Event-id equality
recovers 1,213 aliases, including 1,199 names that were previously missing;
typed `AudioDialogConfigs`, `AudioDialogChannel`, `AudioDialog`, and
`ResponsiveTriggers` Wwise Event fields recover another 1,397 exact aliases,
including 1,393 previously missing names. Current metadata getters plus exact
decrypted-Lua consumers recover 21 more Events for activity BGM, panel-open
audio, synchronized UI video audio, region switching, and domain-upgrade
animation stages. Two additional SNS Voice nodes recover their exact Events from
metadata `Voice=5`, `contentParam[0]`, and the decrypted-Lua click handler,
and six exact `skill_id.dic`/same-name `SkillData`/current-Wwise-hash matches
recover Event identity without inventing a skill playback route. Authored
context names are now joined back to anonymous raw HIRC rows by exact Event
hash, leaving 10,829 hashes without a recovered authored identity and no
duplicate named/hash-only Event rows.
These use stable hash identities and a separate recovery state rather than
being conflated with authored references absent from Wwise. Event purpose is
now ranked independently. Complete Wwise v150 Action lists distinguish 17,574
playback, 942 mixed playback/control, 2,138 control-only, and 470 empty Event
definitions; another 267 authored requests absent from current banks remain
role-unresolved. The current Story-focused export leaves 881 consumer-unresolved
control Events and 140 consumer-unresolved empty definitions at secondary
priority. All 10,335 highest-priority rows contain Play/Post Event,
so pause/resume, mute/unmute, RTPC/Switch/State/Trigger control, Stop, and empty
definitions no longer pollute the unknown-audio queue. Details show exact
operation labels/types and name-collection provenance while preserving the
unknown external caller.
Schema 51 adds 502 exact serialized MonoBehaviour `AudioId` placements across
61 current Event hashes. The Audio detail/search surface labels the field role,
component, GameObject/hierarchy/position when available, serialized object and
source evidence, and the explicit unobserved component/state-execution
boundary. All 61 Events newly leave the unknown-purpose queue; no RTPC,
generic integer, PathID/raw word, voice-tone selection, or responsive-choice
membership is promoted by this pass.
Schema 52 restores `AudioGlobalConfig` from exact object-index scalars when the
Story-focused export omits its raw MonoBehaviour JSON. Audio now exposes 66
global lifecycle placements across 58 Event hashes, including entity init,
state enter/exit, persistent preparation, local/remote, and leave-main-game
roles. Eleven mixed Play/control Events leave `unknownUse`. The unified trigger
catalog retains state direction/mask and entity kind/id while labeling runtime
lifecycle activation, Event posting, and media selection as unobserved.
Schema 53 adds the current IL2CPP-validated 24-byte
`Beyond.Gameplay.PlayLineSound` managed-reference layout. Two exact effect
objects bind `soundSpawn=0x33952647` and `soundFinish=0x518abe42`; this moves one
playback Event out of the highest unknown-use queue and gives the control Event
an authored purpose. The object index keeps the managed type, GameObject,
PathID, field role, and decode status visible. Component/state execution and
actual Event posting remain unobserved. The current MonoBehaviour total is 506
placements across 63 Event hashes.
Within the highest-priority set, 82 Events share an exact same-bank complete
Wwise Play-target set with a named authored-context Event. Their library output
is classified as 55 UI, 26 SFX, and one voice, while their external caller and
trigger placement remain unknown/highest priority. Event details and the source
graph expose this as library-output equivalence rather than a trigger edge.
Another 122 highest-priority Events share an exact complete Wwise media-ID set
with an authored-context Event in the same PCK after excluding the 82 stronger
Play-target matches. Audio details expose this as media-leaf equivalence only:
109 remain `unknownUse`, 13 remain `identityOnlyNoConsumer`, and none inherit
the matched Event's category, trigger, owner, placement, or resolved-purpose
state. The source graph records 142 such forward edges and no contextual edge.
As a result,
20,295 decoded media are Event-related with authored placement unknown, 38,816
have a recovered authored Event context, and one remains without a recovered
playback location. That CN External Source file has the uniquely recovered authored
identity `au_voice_c35m3_3_001`, but no current AudioDialog row, speaker,
Event, or trigger placement. Same-mission crowd-loop Events are retained only
as investigation candidates because no bank or selector edge connects them to
the file. Its source-graph node therefore carries only authored identity,
numeric media, and decoded-file edges, with no inferred ownership edge. The
builder suppresses 2,237 byte-identical
`wwise/unknown` occurrences when a stronger same-storage categorized copy is
already indexed, without deleting either file. Two same-id music collisions
have different bytes and remain visible as Hotfix replacements under
`au_music_main`, rather than being mislabeled unknown. It separately suppresses
607 numeric External Source path copies only after exact FNV-1a-64
AudioDialog-path equality and identical SHA-256 content; all physical files
remain on disk. The view exposes
1,084 responsive-voice Events
across 4,020 authored response positions and 81 tone variants. Response
membership is a possible trigger family, tone membership is a selection
transform, and neither is shown as observed runtime playback. The newly named
channel/default/override/template Events are also shown as authored routes with
live branch selection unobserved; 1,396 use Wwise External Source and therefore
do not invent decoded media links or change the media-placement totals.
The typed UI routes move 22 decoded media from Event-relation-only to authored
context. Video routes retain all possible Wwise leaves and show the
`PostEvent`/playing-id stop/seek contract without claiming which video ran;
three music-control Events contain only typed Set State / Reset Game Parameter
Actions and are shown as control Events rather than missing-media playback.
Across the complete inventory, typed root Actions classify 17,828 Events as
playback, 688 as mixed playback/control, and 1,727 as control-only; 2,530 remain
unresolved instead of being guessed.
The two SNS voice messages each bind one decoded leaf to the exact dialog,
content node, speaker, authored four-second duration, click-to-PostEvent route,
timer/disable stop-by-playing-id behavior, and an unobserved-click boundary.
Audio's runtime panel now exposes compact authored trigger-context coverage,
including the separate greeting EnvTalk and RemoteCommon auto-play routes;
it also surfaces scalar Timeline runtime-contract counts while keeping the
detail shard lazy, including serialized AudioMusic action/skip-policy counts.
All rows retain the static/runtime evidence boundary.

## Build and serve

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` before starting another server.

Useful variants:

```bat
.\export.bat --from-game
.\export.bat --with-assets
.\export.bat --from-game --with-assets
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python scripts\pack_webui.py
```

`export.bat` freshness-checks `export_full/`. Installed-game refreshes require
`--from-game`; asset indexes and CN audio require `--with-assets` or
`export_assets.bat`.

After Story is current, `export.bat` runs independent semantic builders through
`scripts/build_webui_views.py`. Mission Pipeline, Gameplay, projectiles,
economy, world, and eligible Assets/Characters work overlap without crossing
their output boundaries. Joined Gameplay asset references wait for both source
indexes; the source graph waits for every producer; Presentation and Combat
then overlap. Use `--webui-jobs N` to cap concurrency. Per-task wall times and
measured overlap savings are written under `reports/export/`.
Mission-Pipeline-only runs no longer rebuild the unrelated Characters payload.
The source graph keeps its uniqueness indexes as the lookup indexes for edge
sources and aliases instead of maintaining duplicate one-column indexes; graph
rows and query behavior are unchanged.

Repeated installed-game updates should use `build_updates_by_patch.bat` after
its baseline is initialized. Its logical VFS comparison is the lossless
incremental path; full AnimeStudio extraction intentionally does not reuse the
retired weak cross-run file-count/size/mtime cache.

## Stable data contracts

Primary generated roots are:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/{index,conv,mission,reference}/
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/
webui/data/lang/<LANG>/{economy,world,presentation}/
webui/data/gameplay/projectiles.json
webui/data/mission_pipeline/
webui/data/assets/
webui/data/updates/latest.json
```

Generated payloads are never manual inputs. Gameplay loads optional combat,
projectile, audio, and asset sidecars independently and degrades to its base
record when one is missing. Presentation and combat payloads record an
explicit degraded reason when the source graph is absent or stale.

Runtime overrides:

- `story_order.json`, `options.json`, and `narrative_videos.json` require a
  Story rebuild.
- `character_merges.json` and `character_name_overrides.json` are edited live
  through `serve.py`, use stable canonical character ids, and expose their
  Characters-page editing controls only in debug mode.

## Stable frontend behavior

- Views with multiple rendered audio/video files expose one shared simultaneous
  playback chooser. Exact equal-duration audio groups are selected by default,
  while users may select any active-view media for simultaneous or sequential
  playback. An audio-only toggle selects or unselects every audio clip while
  preserving video choices; every visible label and playback status follows the
  shared zh/en UI locale.
- Audio Media rows, detail headings, and player cards use the unique related
  Event id as their title when exactly one Event is known; ambiguous or unlinked
  media retains its existing file/media title. Media supports ascending and
  descending duration sorting, with duration and average file bitrate visible
  in detail facts. The left Media file list keeps duration, size, and bitrate
  right-aligned opposite the filename, with purpose and evidence below.
- Recovery issue/method filters remain visible in normal and debug modes.
- Story source panels, manual order controls, and Characters name/identity
  override controls stay behind debug mode.
- Reset restores Story sort while preserving expanded mission groups.
- Enabling debug does not reposition the top navigation bar.
- Disabling debug from Mission Pipeline returns to a visible page and URL.
- `sns_emoji_*` stays small and inline without hover/modal behavior;
  non-emoji SNS media preserves normal proportions and bounded previews.
- The compact Story media index imports one preferred Sprite per logical
  `cg_image_*`; the duplicate Texture2D export is byte-identical but has its
  own Unity PathID. The frontend groups `_f`/`_m` variants into one selectable
  `CG Image` / `剧情CG` row driven by the shared Endministrator gender selector,
  while single-gender rows stay visibly labeled and CG media remains opaque.
- The Story file-image families are `cg_image_*`, `dlg_biglogo_*`, and
  `remotecomm_image_*`. A full-name audit found no additional BigLogo or
  remote-communication image prefix. `cg_image_e2m6_1_m` is intentionally
  excluded in favor of the authored `dlg_biglogo_e2m6_14_f/m` pair. The two
  `e7m3` BigLogo default-plus-`_m` pairs are also treated as female/male pairs.
- Story and Gameplay share one persisted female/male segmented selector.
  Story gender-authored text, voice, images, video, and gender-only cutscene
  lines update together when it changes.
- Character groups remain stable across languages because overrides key on a
  constituent table/asset id rather than display text.
- Characters preserves its generated default order and can sort ascending or
  descending by alphabet, identity count, evidence groups, resource count,
  observed names, or evidence-source coverage.
- Gameplay owns breakthrough requirements, authored enemy stat points,
  selectable enemy variants, linked assets, compact projectile behavior, and
  playable Story-style sound controls. Only Events joined through the exact
  displayed Gameplay action id and its SkillData or referenced BuffData return
  to that skill row as exact Event dependencies, not generic playback claims.
  Decoded BuffData PlaySound actions add exact authored frame
  windows and stop/fade lifetime where available; activation conditions and
  Wwise selection remain unresolved. Inferred skill links, animation systems,
  profile voice, and all enemy audio stay in the final detail section. Shared
  selector events expose bank, Stop, selector-node, and child-edge evidence
  before their together-listed files. Related-sound groups, projectile phases,
  and individual Events keep their audio controls expanded unless one group
  contains more than 20 playable files. Character Normal Skill,
  Ultimate, and Combo discs preserve the exact element colors authored in
  `CharTypeTable.json`; Normal Attack remains neutral.
- Endministrator remains one canonical Gameplay character. Its persisted
  female/male switch selects concrete portraits, action rows, Story voice
  links, potential pictures, and recovered skill sounds without replacing the
  shared `chr_9000_endmin` stats, skill descriptions, talents, or potentials.
- A skill can legitimately have no separate projectile template. Exact,
  inferred, and unresolved skill/enemy/projectile ownership stay distinct.
- Mission Pipeline distinguishes exact playback, ownership, non-owning
  context, definition-only data, and unresolved activation.
- Reading-popup actions resolve their direct `_readingPopId` through
  ReadingPopUpTable. When an aligned WorldEntityRegistry script/slot and
  complete embedded interaction record raise the receiver's exact custom
  event, Mission Pipeline shows the map entity, slot, event, and coordinates;
  mission/quest ownership and order remain separate.
- Mission Pipeline spatial maps keep weak X/Z carrier proximity separate from
  exact triggers and Story order, with hover previews and a distinct
  unresolved-trigger file tray. Exact interaction anchors also show their
  nearest mission tracking point and 3D/XZ distance as explicitly non-owning,
  non-ordering spatial context. Exact native event producers with an aligned
  WorldEntityRegistry script/slot are also placed at their entity positions;
  this is a targeted runtime-map layer, not a full scene-geometry export.
- Spatial-map points are evidence-coordinate clusters, not Story instances or
  playback counts. Exact entity triggers may legitimately repeat at distinct
  authored positions. Weak LevelScript placement now separates direct carrier
  files from `levelscriptCrossFileOrder`-inherited neighbors: inherited matches
  remain auditable but are not drawn and never enter weak quest sorting. Each
  Story key draws only its nearest direct weak candidate; additional direct
  candidates are folded below the map. Exact positions suppress the same key's
  weak marker. This removes the former false visual multiplication without
  discarding the underlying diagnostic evidence.
- Quest topology, native registration, source order, and code addresses never
  become mission ownership or Story chronology by themselves.

## Updates and packaging

```bat
.\build_updates.bat --first-time
.\build_updates.bat
.\build_updates_by_patch.bat --check
.\build_updates_by_patch.bat
python scripts\pack_webui.py
```

Updates compare saved/current export roots only. Packaging includes the static
browser and optional asset/audio archives while omitting retired generated
Progression payloads.

## Highest-value gaps

- Keep optional semantic sidecars visibly degraded rather than silently stale.
- Continue improving exact Gameplay-to-asset and sound ownership.
- Preserve clear evidence labels as Mission Pipeline gains new runtime joins.
- Keep the Characters false-positive exclusions and live override data clean.
- Maintain responsive, accessible behavior across large Story, Gameplay, and
  Assets datasets.

## Verification

After frontend or data changes:

1. Check export freshness and run the smallest relevant builder.
2. Smoke-test all normal pages, the debug-only Mission Pipeline, and the
   debug-only Characters override controls.
3. Verify Story reset/filter behavior and inline SNS fixtures.
4. Open a playable character and enemy; check variants, progression,
   projectiles, sounds, and asset links.
5. Check console errors and keep generated reports in their topic folders.

Batch Story recovery changes; the default CN build takes minutes, and even a
Mission Pipeline data-only rebuild can be expensive on this checkout.
