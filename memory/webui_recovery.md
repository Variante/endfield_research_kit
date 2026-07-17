# WebUI Recovery

The static WebUI is recovered from an installed Endfield client through the
repo's active export/build pipeline. This note keeps the durable recovery
conclusions in one flat file; user-facing usage stays in `README.md`, script
contracts in `scripts/README.md`, and frontend scope in `webui/README.md`.

## Canonical Refresh

From the repo root:

```bat
.\export.bat
python serve.py
```

`export.bat` currently:

1. reuses the existing `export_full/` by default;
2. verifies `export_full/` freshness against the installed game data;
3. rebuilds `export_full/recovered/dialog_id_table_index.json`;
4. rebuilds narrative video/source-link evidence;
5. builds CN Story and Reference data;
6. builds the experimental Mission Pipeline plus the authored Progression,
   Projectile, Factory, and World semantic views;
7. leaves asset indexes and CN audio relinking to `export_assets.bat` unless
   `--with-assets` is passed;
8. rebuilds the local source graph after any requested asset/audio work;
9. builds Presentation and Combat from the fresh graph, with Combat also using
   direct AnimeStudio evidence; and
10. leaves the OCR-managed Story order override untouched.

Combat performs its own input-mtime guard and degrades with a visible stale
reason if invoked directly against an older graph. This prevents old graph
edges from retaining `direct` confidence after a newer export.

Use `--export-from-game` only when refreshing `export_full/` from the installed
game data. Add `--with-assets` when the same command should also run a combined
Story+asset AnimeStudio export, rebuild asset indexes, and decode/relink CN
audio. Without `--export-from-game`, `--with-assets` reuses existing decoded
assets and relinks audio after the Story rebuild. Run `.\build_updates.bat`
separately for the Updates feed. Use `.\export_assets.bat` separately when only
asset indexes or audio need maintenance.

Generated conversation audio links resolve through the served
`/export_full/structured/Audio/...` route. The frontend normalizes equivalent
relative export/audio forms, and audio-only rows count as visible media when
empty-text rows are hidden, so a recovered playable line is not filtered out.

The game does not need to be running. If it is open, close it before export so
files are not locked.

## Generated Data

Expected browser data:

```text
webui/data/
  manifest.json
  index.json
  actors.json
  lang/CN/index.json
  lang/CN/actors.json
  lang/CN/conv/*.json
  lang/CN/mission/*.json
  mission_pipeline/index.json
  mission_pipeline/missions/*.json
  lang/CN/reference/index.json
  lang/CN/reference/<source>/<table>.json
  lang/CN/presentation/index.json
  updates/latest.json
  assets/index.json
  assets/story_media.json
  assets/videos.json
  assets/bundles/index.json
```

Generated diagnostics and summaries are outputs, not active WebUI inputs.
Keep them under `reports/`.

## Page Contracts

Mission Pipeline:

- Debug-only and read-only; built by `python scripts\build_mission_pipeline_data.py`.
- Displays `MissionRuntimeAsset` predecessor topology and quest-state condition
  dependencies without treating `flowIndex` as an exclusive route selector.
- Routes authored predecessor edges through a visible server-authority gateway.
  The selected-quest trace distinguishes native-proven objective/dialog
  messages and state pushes from the unavailable server successor policy.
- Uses language-neutral lazy graph payloads, then merges mission names and
  objective text from the selected language's existing Story sidecars.
- Organizes its left browser like Story: collapsible mission-type groups with
  naturally ordered mission rows. Graph dragging suppresses node selection
  after a movement threshold, and the unmodified wheel controls graph scale.
- Each graph block combines its short objective with the effective localized
  mission description. `overrideMissionDesc` / `descriptionOverride` replace
  the base description only for the authored quest. Story links are attached
  per quest only from direct runtime references or uniquely resolved
  LevelData/NPC evidence, never from mission-id co-membership alone.

Story:

- Built by `python scripts\story_builder\build.py --languages CN --default-language CN`.
- Uses structured dialog/SNS/radio/remote/env talk tables, recovered
  AnimeStudio/Timeline data, `dialog_id_table_index.json`, and
  `story_source_links.json`.
- Conversation JSON is lazy-loaded from `webui/data/lang/<code>/conv/`.
- Recovery uncertainty should stay visible through warnings. Detailed issue
  filters, source/debug blocks, mission timeline evidence, cutscene debug
  panels, and manual order-edit controls are available from the Story
  `Show debug info` toggle.
- Timeline-inferred option responses are promoted only when source evidence
  binds each option index to a distinct candidate response. The known
  source-backed strict `trunkClipOptionIndex` case is `dlg_c28m3_10` group 1;
  the remaining unresolved groups stay inferred.

Reference:

- Built by the Story builder.
- Keeps rows close to exported structured tables and resolves localized display
  text where possible.
- Avoid story-specific interpretation; tables that should not become Story
  conversations can remain Reference-only.

Gameplay:

- Built by `python scripts\build_gameplay_data.py` from authored structured
  tables and localized text.
- Curates characters, weapons, equipment, enemies, and usable items rather
  than exposing arbitrary decoded JSON. Current safe display semantics include
  progression costs/checkpoints, skill text and blackboard values, equipment
  formulas/suits, enemy variants/stat curves/abilities/scalars/buffs/drops, and
  usable-item actions/chest rewards.
- Raw authored values and normalized display aliases must remain distinguishable
  where a formatter transforms the source value. Static data does not establish
  live inventory, server availability, runtime formula order, or encounter state.

Display additions roadmap and current status:

1. Landed: a projectile inspector backed by exact AnimeStudio payloads. It presents
   collision, lifetime/range, movement segments, effect lists, alert behavior,
   and sound references; keep inferred enum/hash labels visibly qualified.
2. Landed: a combat relationship explorer that joins curated gameplay records to
   source-graph evidence across characters, enemies, abilities, selectors,
   buffs, projectiles, effects, audio, and assets. Direct and inferred edges
   remain distinguishable, and raw authored values remain available. It now
   also exposes all 162 byte-proven AbilityEntity inherited prefixes and 833
   direct component RID links while excluding the unresolved tails; 135
   character/enemy identifier matches are explicitly inferred. The guarded
   opening through `useFrameTick` is split into
   five exact mirrored fields and six visibly qualified metadata-order fields;
   the following 92-byte `surroundingConfig` is exact-consumed in all 162 roots.
   Fourteen linked SurroundingMovementData mirrors and ten non-consuming
   BaseRotationData next-boundary mirrors match. Enum/hash meanings remain
   qualified, and bytes from `followMountPointConfig` onward stay excluded.
   Character targeting now adds 68 exact-consumed TargetSettings records and
   four non-null finder/validator links proven reachable through component RIDs.
   Six records from two avatar templates without curated Gameplay roots are
   reported but deliberately left unattached.
3. Landed: a factory/economy browser for recipes, items, machines, technology,
   logistics, power, fuel, mining, shops, rewards, and activities. It describes
   authored static configuration, not live throughput, availability, or account
   state. Machine-technology edges resolve building-item ids through
   FactoryBuildingItemTable before targeting machines; unresolved mappings do
   not become dangling edges, and detail panels expose the endpoint-valid
   relation graph.
4. Landed: a static world explorer for levels, placed entities, interactives,
   spawners, models, audio slots, and authored references. Keep runtime world
   state and simulation explicitly out of scope.
5. Landed: a progression/reward graph with 9,836 browsable roots, 15,691 typed
   nodes, and 37,970 direct endpoint-valid relationships across upgrade curves,
   costs, breakthroughs, talents, potentials, item use/obtain paths, rewards,
   and drops. Every edge retains table/row/path evidence and the UI avoids live
   state, probability, and optimal-planner claims.
6. Landed: an entity Presentation explorer with 3,084 curated roots, 7,452
   nodes, and 16,857 endpoint-valid relationships across model configs,
   prefabs, controllers, bounded asset entities, materials, shaders, animation
   configs/states/clips, effects, and representative browser assets. Direct and
   inferred edges remain separate; caps and omissions are explicit, and the
   view does not claim runtime renderer choice, transitions, effect timing, or
   shader behavior.
7. Next: deepen Combat from the `followMountPointConfig` boundary;
   structurally complete selector/target-settings fields stay semantically
   qualified until enum/hash labels and evaluator behavior are proven.

The landed views use isolated generated-data builders and frontend modules with
shared tab navigation, packaging, and `export.bat` integration. The World view
also deduplicates mirrored registry instances while preserving compact source
provenance. Reuse that split so new semantic surfaces do not expand the Story
or Gameplay builders into unrelated domains.

The semantic explorers share a newcomer-facing landing contract: state what a
page answers and why it matters, use plain-language record and relationship
labels, and keep detailed confidence/provenance boundaries in expandable help.
Normal navigation exposes Gameplay. Progression, Combat & Projectiles, the
retained standalone Combat graph, Factory, World, and Presentation are gated by
`Show debug info`; disabling debug normalizes an active hidden view to Gameplay
or Assets as appropriate.
The asset-excluding package replaces `assets.js` with a navigation shim, so the
shim must mirror the same debug-view gating and hash/keyboard fallbacks rather
than exposing hidden pages in packaged builds.
Their feature styles must use the shared light-surface tokens (`--panel`,
`--surface`, and `--panel-bg`) rather than dark fallback colors. Dark surfaces
are reserved for media letterboxing or content that genuinely needs them, not
for ordinary cards, filters, lists, or evidence blocks.
Combat & Projectiles groups its 310 templates by sender. Exact exported
projectile-to-skill ownership edges are direct evidence; derived skill-family
or unique character/enemy identifier matches are inferred, and unsupported or
ambiguous records remain unresolved. World groups records by
authored level ID with localized LevelDesc names and plots coordinate-bearing
records for the selected level on a bounded SVG X/Z map. Global registry rows
without an exported level ID stay unassigned rather than being inferred from
coordinates or entity numbers. These defaults improve orientation without
promoting inferred runtime behavior.

Deferred-view recovery queue:

- keep Combat & Projectiles and the retained standalone Combat graph debug-only
  until sender/skill ownership is semantically trustworthy, ambiguous ownership
  is reduced, and the page presents a quieter task-oriented summary instead of
  a dense recovery graph;
- keep World debug-only until level association and placement semantics have
  stronger evidence, unassigned/global records no longer dominate exploration,
  and the 2D map communicates useful authored structure without noisy sampling.

Candidate follow-on displays, in evidence-first order:

- deepen Combat from `followMountPointConfig` and the remaining BuffData action
  chains, then show more target/filter/action structure without inventing
  evaluator order;
- add an audio cue/event browser across Wwise event/media links, story voices,
  gameplay cues, factory/world audio, and playable decoded media;
- add a mission/quest structure view for authored tasks, conditions, actions,
  areas, level scripts, and map markers while keeping runtime completion state
  out of scope;
- add semantic update drill-down that groups exported changes by these recovered
  entities while retaining the existing previous-export/current-export boundary;
- keep recovery coverage, unresolved layouts, and source-graph provenance as a
  debug-only evidence view rather than mixing diagnostics into normal browsing.

Updates:

- Built by `.\build_updates.bat` or `python scripts\build_updates.py`.
- Reads the saved previous and current export roots from `endfield_paths.bat`;
  the underlying script falls back to `export_1d2/` and `export_full/` when no
  wrapper configuration or explicit paths are supplied.
- Stores scanner cache and feed history under `.game-data-tracker/`.
- Never point the comparison at `webui/`, `reports/`, `memory/`, `scratch/`, or
  `tmp/`.
- Tracks WebUI-facing exported JSON plus exported image/model/video assets and
  decoded audio by default. Use `--skip-audio-updates` to omit audio while
  retaining other assets, or `--skip-asset-updates` for a text-only feed.
- Use `--baseline-only` only when an intentionally empty first/baseline feed is
  desired. Refresh the cached previous baseline after replacing that folder.
- `build_updates_by_patch.bat --init-baseline` seeds a separate original-data
  VFS snapshot from only the current installed version and attaches it to the
  current export. `--check` is detection-only. Default apply mode preserves the
  no-change/version-only/repack-only invariant, while logical changes are built
  in a complete cloned staging export. Direct structured VFS files are dumped
  selectively; affected AnimeStudio and audio scopes refresh before rotation.
- Only `build_updates.bat` generates `webui/data/updates/latest.json`. For two
  explicit extracted roots, use `build_updates.bat --previous-export-root OLD
  --export-root NEW --refresh-previous-export-baseline`; the original-VFS
  detector does not generate the page by itself.
- Patch publication now uses sibling staging and same-volume archive/current
  renames. The previous export is preserved, occupied preferred archive names
  receive a snapshot suffix, WebUI data is backed up for handled rollback, and
  `build_updates.bat` compares the published archive/current roots. The source
  baseline advances only after extraction stability, WebUI rebuild, and feed
  generation succeed. A journal blocks new work after an unhandled interruption;
  failed published candidates are retained under the operational state root.

Assets:

- Built by `python scripts\build_assets.py`.
- Indexes exported images, models, materials, videos, story media, related
  files, browser previews, and optional demo bundles.
- Keep heavyweight recovery/debugger views out of the static frontend unless a
  new recovery view is intentionally designed.

Serving and packaging:

- Serve locally with `python serve.py` at `http://127.0.0.1:8765/`, or pass a
  port such as `python serve.py 9000`.
- Before starting a default server, check whether `127.0.0.1:8765` is already
  running and reuse it.
- Package with `python scripts\pack_webui.py` or `.\pack_webui.bat`.
- Pass `--skip-audio` to omit the standalone decoded-audio zip.
- Package inputs are `serve.py`, `webui/`, and selected media from
  `export_full/`. `reports/`, `scratch/`, and `tmp/` are not package inputs.

## Inline Media Rules

- `sns_emoji_*` assets render as inline emoji. They do not open hover popovers
  or the full-screen modal. Their resolver only uses exact or emoji-family
  sprite matches; missing emoji sprites stay unresolved instead of falling back
  to numbered sticker or SNS decoration assets.
- `envEmoji_common_*` rows render line-level `emoji` fields using recovered
  Unity prefab aliases, RectTransform layer data, and enter animation curves in
  `story_media.json`.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and related
  `cg_image_*` assets keep normal image proportions. Exact non-emoji SNS media
  does not borrow numbered sticker, decoration, or emoji fallbacks.
- When a line has both an inline `<image=...>` token and matching line-level
  `image`/`images` metadata, the inline token owns the visible display and the
  media strip dedupes it.
- Popovers and the modal preview must stay inside their visual frame and the
  viewport.

Regenerate envEmoji prefab data with:

```bat
python scripts\recover_envemoji_prefabs.py
```

## DialogIdTable Registry

The Story builder uses Endfield's runtime dialog registry,
`Beyond.Gameplay.DialogIdTable`, as offline evidence. The source file is
exported to:

```text
export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json
```

The extractor does not infer placement or branch fields from the MemoryPack
records. It extracts standalone ASCII dialog roots and option identifiers,
which is enough to build:

```text
export_full/recovered/dialog_id_table_index.json
```

Current baseline:

- `3,849` registered dialog roots.
- `0` per-line/trunk tokens in the table.
- `1,407` registered scenes with option identifiers.
- `4,681` option IDs.
- `0` radio entries; radio remains sourced from `RadioTable.json`.

The earlier `4,496`/`1,058` baseline was invalid: the extractor matched the
embedded `dlg_*` substring inside `option_dlg_*` and treated option-only rows
as fake dialog lines. Option IDs now contribute option vocabulary only and can
never register a scene. `DialogBriefInfo` contains no option anchor, branch
target, or per-trunk line list.

Registry-backed reason codes:

- `unregisteredScene`: scene key absent from `DialogIdTable`; the runtime has
  no standard dialog entry point for it.
- `dialogTrunkRowIteration`: scene key present, but no Timeline/DialogTree
  source was recovered; row iteration by scene key prefix is the supported
  direct fallback.

Each conversation payload can include `_debug.runtimeRegistry` so downstream
tools can inspect root registration and option IDs. Current zero trunk/line
counts are an honest schema boundary, not missing recovery work.

If a future update makes the registry extractor report near-zero scenes, inspect
whether `DialogIdTable.json` still contains ASCII `dlg_*` strings. If not, the
table format or encryption changed and needs a targeted offline decoder.

## Game Update Playbook

Most game updates need only:

```bat
.\export.bat --export-from-game
```

Then, if `global-metadata.dat` exists, refresh the IL2CPP metadata canary:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
```

Inspect these drift reports only when the metadata canary changes:

- `reports/option_flow_runtime_metadata_diff.md`
- `reports/option_flow_runtime_metadata_focus_diff.md`
- `reports/option_flow_runtime_metadata_focus.md`
- `reports/option_flow_runtime_metadata.md`

Important interpretation:

- `global-metadata.dat` is useful for runtime vocabulary and method/field drift,
  but it is not the authored story payload.
- A hash-only metadata change with no focus/body-target drift is usually
  harmless.
- A new serialized field on dialog option/tree/timeline focus types is a strong
  candidate for new recovery evidence.
- `DialogTimelineOptionData` still having only `optionIndex`,
  `changeFinishNum`, and `targetFinishNum` means unresolved option targets are
  a runtime method problem, not a hidden serialized field problem.

## Benchmarks

Every `export.bat` run writes a wall-time and process-tree RAM benchmark under
`reports/export_benchmarks/` and updates
`reports/export_benchmark_latest.{md,json}`. Use those files as current truth.
The maintained direct CN Story build is presently on the order of minutes, so
direct runs should have a 10-15 minute shell timeout.

Historical profiling found the main Story-builder costs in repeated file
opens, per-scene regex compilation, mission/LevelScript spatial comparisons,
DialogTree source loading, raw Reference generation, and reopening freshly
written conversation JSON. Prefix/path indexes delivered a large early gain;
future optimization should re-profile before acting because the recovery
surface has since expanded.

A historical EndfieldStudio comparison showed it could rapidly cross-check the
structured Table/Lua/JsonData surface and extract a classified non-material
image subset, but it did not add Story data and omitted material textures,
meshes, AnimationClips, Material JSON, bundle JSON, and AnimeStudio
relationship metadata. It remains a cross-check or preview candidate, not a
replacement for the canonical AnimeStudio export.

## Verification

After a refresh, check:

- Story tab loads and conversation detail lazy-loads.
- SNS emoji stays inline without modal/popover behavior.
- SNS stickers/photos render with normal proportions.
- EnvTalk emoji rows render with recovered prefab layers and replayable enter
  motion.
- Reference tab loads table counts and lazy-loads rows.
- Updates payload tracks the installed `Endfield_Data` root, not generated repo
  folders.
- Assets tab loads counts and can preview images/videos where supported.
- Package dry-run reports expected story media and excludes 3D/model payloads
  by default.

## Story browsing and debug surface

- The Story view now defaults to a quieter browsing surface. The `Show debug
  info` toggle exposes line-order evidence, source/debug panels, mission
  timeline recovery, cutscene debug detail, and manual Story order editing
  controls. Recovery issue and recovery method filters remain visible in both
  normal and debug modes so confidence limits are not hidden from readers.
- Resetting Story filters returns to Story sort and clears chips/search without
  collapsing already-expanded mission groups.
- The WebUI chrome moved to a light neutral palette with muted teal and orange
  accents; kind/category badges remain softly color-coded for scanning.
- The gameplay video story-order matcher now combines OCR segments with
  decoded Story audio-template matches. Audio fingerprints are cached under
  `tmp/ocr/gameplay_video_ocr/audio/`; `au_music*` templates are ignored by default,
  and locked missions are used as threshold controls before applying proposed
  order changes.
- `scripts/download_bilibili_video.py` is the maintained optional intake helper
  for public Bilibili gameplay sources. It writes complete muxed `.mp4` files
  into `videos/`; the OCR worker continues to skip partial `.m4s` and `.lock`
  files.

### Option placement confidence

`inferredOptionLayout` is the generated payload compatibility warning, not a
claim that the WebUI has no display anchor. The current CN build has zero
unplaced option groups. Its raw generated placement-warning set is 93
unregistered table-only scenes, 7 registered key-matched scenes, 1 registered
end-of-scene fallback, and 0 registered gap/unknown scenes. Runtime WebUI
override coverage changes the visible Recovery Issue queue to 73 table-only,
0 key-matched, 0 end-of-scene, and 0 gap/unknown scenes. Twenty-eight scenes
are fully covered and move to `Manual override`; the 73 still needing complete
coverage remain under `Needs manual override`. The fully covered set comprises
20 table-only scenes plus all 7 key-matched scenes and the one end fallback.

The renderer keeps recovered groups inline at their `after` line, labels the
placement method, and uses a scene-level fallback block only when no position
exists. Manual entries in `webui/overrides/options.json` stay visibly tagged
and do not become source evidence. Generated index entries carry
`optionIssueTargets`, which lets the frontend compare exact warning
groups/options with runtime overrides before building filter counts. A fully
covered issue class is removed from its raw queue and replaced by `Manual
override`; partial coverage retains the raw class plus `Needs manual override`.
Original option-layout methods stay visible as recovery provenance even when a
manual display correction wins.

The inferred-reply queue is now empty. Current native control flow proves that
adjacent trunk clips with `clipOptionIndex=0` are shared continuation, not one
reply per option. The CN builder emits 137 such shared-continuation groups: 98
with nonzero option rows, 35 with zero-valued option rows, and 4 with an
incomplete overlapping Runtime Jump retained as later-route uncertainty.
Completed Runtime Jump routes remain higher priority. The 20 former manual
response overrides for the disproven adjacent-line mappings were retired;
unrelated authored/manual response mappings remain intact.

The table-only `dlg_gm01m5_*` and `dlg_gm02m3_*` clusters demonstrate why the
categories must remain distinct: group-number matching is useful but not
universally chronological. Semantic prompt/answer structure pins groups in
those clusters through WebUI-only overrides; the registered `dlg_gm02m2_1..4`
set adds seven explicit manual placements, including two corrections that move
away from the key match. Two terminal groups in `dlg_f1m12_1` and
`dlg_f1m4_6` remain manually confirmed at their automatic end anchors. The
original tables and `DialogIdTable` provide identifiers and text, but no
surviving authored DialogTree/Timeline anchor for these table scenes.

## Narrative video attachment policy

- Story builder now embeds every resolved narrative-video mapping into its
  resolved conversation, replacing the old dialog plus one-cutscene exception.
  This
  covers cutscene, remotecomm, and any other resolved story file; non-name
  evidence such as `timelinePlayable` supplies authored inline timing when
  available.
- Standalone `video_*` rows are still emitted for direct browsing, but they
  carry `attachTo` for the resolved story key. Story sort uses that attachment
  so the standalone video row stays beside the file where the video is inserted.
- Manual rules in `webui/overrides/narrative_videos.json` cover both known
  filename mismatches and false attachments. `attachInline` manually embeds a
  matching video stem into a target story key, and can set `audioFrom` to copy
  source cutscene audio events into that target during audio relink.
  `suppressInline` keeps known false inline attachments standalone-only.
  `cutscene_e1m3_1` is suppressed for `cs_video_e1m3_1` because the filename
  match should not attach that video to the black-screen cutscene.

## Archive duplicate identity

- `radio_e1m1_2d7` and `nar_media_map01_128_1` have the same localized audio
  transcript. Keep `radio_e1m1_2d7` as the mission `e1m1` row; keep
  `nar_media_map01_128_1` available only from Archive/media grouping and from
  the bidirectional file-page link.
