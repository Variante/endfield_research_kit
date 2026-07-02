# Scripts

Active scripts in this directory support the WebUI export/package workflow.

## Active Wrappers

From the repo root:

```bat
notepad endfield_paths.bat
.\setup_first_time.bat
.\export.bat
.\export.bat --with-assets
.\export.bat --export-from-game
.\build_updates.bat
.\export_assets.bat
.\pack_webui.bat
```

For a fresh checkout, edit `endfield_paths.bat` first, then prefer the root
`setup_first_time.bat` wrapper. It initializes and builds the required external
tools, runs the installed-game Story/Gameplay/Text Tables export, prints optional
Assets/media and Updates follow-up commands, and starts or reuses the default
WebUI server. Pass `--no-serve` if the setup should stop after the build/export
steps.

The root wrappers load `endfield_paths.bat` before parsing arguments. It sets
`ENDFIELD_GAME_ROOT`, `ENDFIELD_PREVIOUS_EXPORT_ROOT`, and
`ENDFIELD_EXPORT_ROOT` for repeated local runs. Explicit flags such as
`--game-root`, `--previous-export-root`, and `--export-root` still take
precedence for one-off commands.

`export.bat` is the normal Story, Gameplay, and Text Tables WebUI rebuild path from an existing
`export_full/`. It runs:

- `scripts/verify_export_freshness.py`
- `scripts/story_builder/refresh_evidence.py`
- `scripts/story_builder/build.py --languages CN --default-language CN --skip-audio-link`
- `scripts/build_gameplay_data.py --languages CN --default-language CN`

The freshness verifier uses a fast non-empty check for required generated output
folders by default; pass `--full-output-counts` directly to
`verify_export_freshness.py` only when exact file counts are needed for an
audit. `refresh_evidence.py` runs the DialogIdTable registry, narrative video
bindings, and story source-link refresh in parallel before the Story builder
loads those generated files.

Pass `--export-from-game` when you explicitly want to refresh `export_full/`
from installed game data before rebuilding Story/Gameplay/Text Tables data. Pass
`--with-assets` to also run the asset index builder and CN audio relinker after
Story is rebuilt. When `--export-from-game` and `--with-assets` are combined,
the wrapper runs one AnimeStudio Story+asset export so the source scan, maps
stage, and VFS index work are not repeated by a second wrapper invocation.
Set `ENDFIELD_GAME_ROOT` in `endfield_paths.bat` when the installed game is not
under the default `D:\Program Files\Endfield Game\Endfield_Data`. The path must
be the installed `Endfield_Data` directory. For one-off runs, pass
`--game-root PATH`; an explicit argument takes precedence over the config file.
Fresh clones must initialize and build the AnimeStudio submodule before this
installed-game refresh path can run:

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
```

The exporter expects
`tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`.

`build_updates.bat` writes `webui/data/updates/latest.json` from the saved
previous export and current `export_full/`. Use `.\build_updates.bat
--init-build` for initial or baseline-only update feeds. By default it compares
the exported text JSON that feeds Story and Text Tables plus exported image/model/video
assets and decoded audio using fast size fingerprints; pass
`--hash-asset-updates` for slower same-size binary modification detection,
`--skip-audio-updates` to omit decoded audio while keeping other asset entries,
or `--skip-asset-updates` for a text-only feed. The wrapper reads
`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT` from
`endfield_paths.bat`; pass `--previous-export-root PATH` and
`--export-root PATH` only for one-off comparisons. Most runs do not need
`--game-root`; pass it only for optional decoded-impact mapping from a
non-default installed
`Endfield_Data` root. It does not choose the export trees.

`export_assets.bat` runs `scripts/build_assets.py` for the compact WebUI media
indexes, then runs `scripts/build_audio.py --skip-decode` to relink existing
decoded CN audio into generated conversations. Pass `--export-from-game` to run
the full WebUI-facing AnimeStudio image/model export plus `Material` JSON after
first writing a lightweight AnimeStudio `vfs-index` bundle metadata snapshot,
and decode CN audio first. Pass `--webui-assets` when only WebUI-referenced
Texture2D media is needed, or `--debug-assets` for exhaustive AnimeStudio
conversion/JSON diagnostics. When Story also needs an installed-game refresh,
prefer `export.bat --export-from-game --with-assets` so one exporter invocation
covers Story and assets. It accepts the same `endfield_paths.bat`
`ENDFIELD_GAME_ROOT` fallback and `--game-root PATH` override when refreshing
decoded assets/audio from a non-default install root.

Both installed-game wrappers pass `--animestudio-jobs N` through to
`export_full_from_game.py`. The default is now `8`; AnimeStudio subprocess
tasks for a source go through a shared worker pool, and asset shards are queued
round-robin by type so one large type does not monopolize workers. Use a lower
value such as `1`, `2`, or `4` for low-RAM or first-time runs.
Non-sharded JSON type exports use `--animestudio-type-job-mode auto` by default,
which merges matching JSON types into one AnimeStudio process instead of loading
the same source files once per type. Pass `--animestudio-type-job-mode parallel`
for the older one-process-per-type behavior, or `merged` to combine every
non-sharded type set. Earlier testing on the 64 GiB workstation found
`--animestudio-jobs 2` improved the pre-merge Story JSON slice by about 21%,
while the old full asset refresh peaked at about 27 GiB observed process-tree
working set. Full-mode `AnimationClip` and `Texture2D` workers dominate both
memory and wall time.

Both wrappers can pass `--animestudio-dummy-dlls PATH` through when
`--export-from-game` is present. Use this only for optional IL2CPP DummyDll
folders that improve AnimeStudio MonoBehaviour schema recovery during Story JSON
export. If the flag is omitted, `export_full_from_game.py` checks
`ANIMESTUDIO_DUMMY_DLLS`, then known local locations such as `tools\DummyDll`;
it only adds AnimeStudio's `--dummy_dlls` option when the selected directory
exists and contains `.dll` files. Missing or stale DummyDll paths warn and
continue without DummyDlls instead of failing the export.

For targeted MonoBehaviour recovery experiments, pass
`--animestudio-mono-behaviour-type-tree-priority script-first` to make
AnimeStudio try a DummyDll script-derived TypeTree before the embedded
serialized TypeTree. The default `serialized-first` preserves the normal export
order and only uses script-derived trees as a fallback after serialized decode
failure. Script-first only improves body decoding when the relevant external
`MonoScript` bundle is loaded and the DummyDll set contains a usable script
type with real field nodes. Without DummyDlls, or when the script type is absent
or only resolves to a base-only tree, AnimeStudio records the script-derived
status when applicable and keeps the serialized/partial decode result.

When MonoBehaviour TypeTree decoding fails inside a managed-reference registry,
AnimeStudio now emits partial JSON instead of collapsing to metadata-only JSON
when safe fields were already read. The partial output keeps decoded fields such
as `m_Name` and `actionsData`, then recovers
`$animestudio.recoveredManagedReferences.RefIds` headers (`rid`, managed type,
raw payload offset, raw payload length, and validated inferred
`DialogMainFlowData` `leadRid`/`linkedRids` when that layout matches exactly) so
downstream tools can still join decoded `rid` references to their runtime
managed types. It also names validated string fields for common dialog action
payloads, including `lineId`, `animationPath`, `facialMorphPath`, and
`poseControlNames`, records inferred transform-like fields for validated
`DialogTeleportEntityActionData` payloads, names small validated empty-tail and
flag/index-like dialog actions, records validated motion/camera/post-process
scalar blocks for action payloads such as `DialogMoveToActData`,
`DialogLookAtActData`, `DialogTurnToActData`, `DialogCamDOFActionData`,
`DialogMaskActionData`, `DialogCamPPActionData`, and the common
`DialogCamActData` layout, and records a conservative `inferredActionTimingPrefix`
for dialog action payloads (`value0Seconds`, `value1Seconds`, and `actionCode`).
Still-unparsed payloads may include
`heuristicStringHints` and `heuristicRidLinks`; those fields are advisory
clues, not a typed managed-reference schema decode.

`export_full_from_game.py` writes detailed stage logs and summaries under
`../reports/`. Nonzero AnimeStudio subprocesses now make the wrapper return
nonzero after the summary is written, so `export.bat` and `export_assets.bat`
stop on partial type-sliced failure. Metadata-only MonoBehaviour JSON is a
bounded fallback for objects with impossible schema fields. Per-asset
`Export ... error` log entries are skipped converted assets and should be
reviewed separately from wrapper-level failures.

`scripts/build_audio.py` can still be run directly for non-CN languages or
audio-only maintenance. It indexes shared files under
`export_full/structured/Audio/shared/` plus language voice files under
`export_full/structured/Audio/<LANG>/`, adds playable `audioSrc` links to
generated conversation JSON when a line's `audio` id matches a decoded file,
streams Wwise bank HIRC metadata from VFS `*banks.pck` payloads via AnimeStudio
`stream`, and links cutscene audio events such as `au_sfx_*`/`au_vo_*` when
the event graph reaches decoded media.

`pack_webui.bat` runs `scripts/pack_webui.py` and creates split
shareable zips. The main story zip contains `serve.py`, `webui/`, generated
story and text-table data, WebUI code, and emoji images. The companion assets
zip contains larger displayed image/video media resolved from `export_full/`,
and the standalone audio zip contains decoded story audio from `export_full/`.
Extract the story zip first, then extract the assets and audio zips into the
same directory when media or audio is wanted. Packaging excludes 3D/model
payloads and does not include
`scratch/`, `reports/`, or `tmp/`.

## Folder Contract

The active WebUI export/package workflow should not require inputs from
`../scratch/`, `../reports/`, or `../tmp/`.

Expected active inputs and outputs:

- `../webui/`: static browser app plus generated WebUI data under
  `webui/data/`.
- `../export_full/`: generated export data used by Story, Text Tables, Assets,
  and package media resolution.
- `../.game-data-tracker/`: persistent state for exported WebUI text JSON and
  asset update tracking.
- `../reports/`: durable generated reports and summaries written by exporters
  or builders. These are outputs, not package inputs, and should not contain
  agent investigation conclusions.
- `../videos/`: local gameplay video inputs used by the optional OCR/audio
  story-order recovery tools. Completed `.mp4` files are inputs to
  `story_recovery/build_gameplay_video_ocr_audit.py`; downloader `.m4s` parts
  and `.lock` files are ignored as incomplete work.
- `../memory/`: observations, conclusions, older exploration notes, status
  snapshots, and archived scripts.
- `../scratch/`: disposable probes, temporary prototypes, logs, generated
  previews, and experiment output that has not become part of a maintained
  workflow.
- `../tmp/`: disposable intermediate output and temporary files.
- `../tools/`: the tracked source-graph helper, tracked IL2CPP diagnostics
  used by optional recovery audits, and ignored local vendor/tool caches. If a
  workflow needs reusable helper data such as AnimeStudio DummyDlls, place it
  here or pass it explicitly rather than relying on `scratch/` or `tmp`. New
  promoted tools need intentional tracking and documentation because this
  directory is ignored by default.

## WebUI

- `export_full_from_game.py`: export data from the installed Endfield client.
  The normal WebUI wrapper is `..\export.bat`, which skips raw VFS, source
  inventory, raw asset bundles, audio PCK/media files, world-streaming bytes,
  irradiance volumes, extend-data bins, patch bytes, Lua, and heavy
  2D/3D/animation asset conversion unless `--with-assets` is passed. The
  structured dump defaults to `--structured-dump-mode webui`, and
  `scripts\build_audio.py` streams Wwise bank metadata directly from VFS for
  event relinking. `--structured-dump-mode full` keeps the same production skip
  rules, and `--structured-dump-mode debug` is the broad VFS diagnostic mode.
  `..\export_assets.bat` runs those heavier asset passes separately. Summaries
  are written under `..\reports\`, but the workflow does not require `reports`,
  `scratch`, or `tmp` as active inputs.
- `verify_export_freshness.py`: compares the latest export summary with
  the current installed `Endfield_Data` source fingerprints and verifies the
  WebUI-required export folders are present. `export.bat` runs it immediately
  after `export_full_from_game.py` so game updates do not silently reuse stale
  `export_full/` data.
- `track_export_changes.py`: generic file-tree scanner used by the WebUI
  Updates builder.
- `build_updates.py`: writes `webui/data/updates/latest.json` by comparing
  WebUI-facing text JSON roots and exported asset roots in a previous exported
  game-data tree, default `..\export_1d2\`, with the current `..\export_full\`.
  Scanner cache lives under `..\.game-data-tracker\`;
  generated summary reports live under `..\reports\`, and non-empty feed
  snapshots are written as `..\.game-data-tracker\history\update-feed-*.json`.
  The root `..\build_updates.bat` wrapper runs this standalone update step.
  Pass `--previous-export-root PATH` to compare a different saved export,
  `--export-root PATH` to compare a different current export,
  `--game-root PATH` only for optional decoded-impact mapping,
  `--refresh-previous-export-baseline` after replacing the saved previous
  export, `--baseline-only` to write an empty feed, `--skip-audio-updates` to
  omit decoded audio while keeping image/model/video asset entries, or
  `--skip-asset-updates` to skip the full exported asset diff. Asset
  modifications use fast size fingerprints by default; pass
  `--hash-asset-updates` for slower
  content-hash detection of same-size binary changes. Pass
  `--full-export-scan` only for an intentional all-files audit of the export
  roots. Pass
  `--dry-run-prune-previous-export-untracked` to preview previous-export files
  that already exist byte-identically at the same relative paths in the current
  export, and `--prune-previous-export-untracked` to delete those old duplicate
  copies after confirming the preview. Cached tracker and asset baselines keep
  later comparisons from treating those pruned files as newly added.
- `story_builder/build.py`: builds CN Story/Text Tables data by default,
  with optional extra languages. The builder reads from `..\export_full\`, stamps dialog convs
  with DialogIdTable runtime registry evidence, links narrative
  Cutscene/RemoteComm video files to matching story entries, promotes
  mission-shaped ReadingPopUp/RichContent `text_*` rows into story text
  conversations, and writes generated WebUI data plus durable reports.
  The static frontend currently
  treats SNS emoji ids such as `sns_emoji_*` as inline emoji, while non-emoji
  SNS media such as `sns_image_*` and `sns_sticker_*` render as normal images.
  The command entry stays small: `build_args.py` owns CLI flags,
  `timeline_orders.py` owns the pre-build Timeline recovery check,
  `timeline_action_evidence.py` owns the pre-build managed-reference action
  evidence pass, `build_pipeline.py` owns bundle orchestration and manifest writing, and
  `audio_relink.py` owns the post-build decoded-audio relink pass.
- `build_assets.py`: builds the compact WebUI Story/Wiki media index by
  default, or the broad Assets browser index and optional demo bundle zips with
  `--mode full`. It is run by `..\export_assets.bat` and by
  `..\export.bat --with-assets`, not the story-only `..\export.bat`.
- `build_gameplay_data.py`: builds the compact Gameplay tab payload under
  `webui/data/lang/<LANG>/gameplay/index.json` from structured tables such as
  `WeaponBasicTable`, `WeaponUpgradeTemplate*`, `WeaponBreakThroughTemplateTable`,
  `WeaponTalentTemplateTable`, `ItemTable`, `EquipTable`, `EquipFormulaTable`,
  `EquipSuitTable`, `CharacterTable`, `CharGrowthTable`, `CharLevelUpTable`,
  `CharBreak*`, `CharacterPotentialTable`, `SkillPatchTable`, and
  talent/profession/type lookup tables. It resolves localized display names,
  default weapon links, skill blackboard values, level-up costs, weapon upgrade
  checkpoints, weapon base-ATK stat checkpoints, breakthrough material costs,
  equipment display/property stat curves, domain/formula/suit context,
  character break-stage caps, capped character stat checkpoints from
  `CharacterTable.attributes`, character breakthrough costs, potential unlock
  effects, and Story wiki cross-links when a matching `wiki_*` Story page exists.
  It is run by `..\export.bat` after the Story builder and can be run
  directly for extra languages with `--languages CN EN JP --default-language CN`.
- `build_data_index.py`: builds a legacy local decoded-config index from final
  decoded config files under `export_full/structured/StreamingAssets/Data/Json`
  and `export_full/structured/Persistent/Data/Json` by default. It writes
  lazy-loaded shards under `webui/data/game_data/`, splits
  JSON entries by clear directory structure before falling back to filename
  prefixes, parses real text JSON, identifies known MemoryPack binary `.json`
  families with IL2CPP-recovered top-level field names, and decodes stable
  `LipSync` and `LevelScriptData` preview facts. Raw `.ab` bundles, packed
  audio, video/media, streaming, irradiance, and extend-data payloads are
  intentionally excluded; the Assets/export tooling owns richer media and asset
  browsing. The current WebUI no longer loads this as a tab.
- `build_decoded_index.py`: builds a legacy local AnimeStudio decoded JSON index from
  AnimeStudio JSON outputs under
  `export_full/recovered/AnimeStudio-cli/<source>/json_by_type/`. It defaults to
  MonoBehaviour, writes lazy-loaded shards under `webui/data/decoded/`, groups
  entries by semantic domain and schema signal, splits only oversized
  semantic/schema groups into balanced lazy-loaded parts, records `$animestudio`
  metadata, decode status markers, managed-reference classes/layouts, semantic
  meaning/tags, schema/field-set IDs, and links raw previews back to
  `export_full/` without copying decoded files. The current WebUI no longer loads this as a tab.
- `build_audio.py`: decodes audio via AnimeStudio CLI, stores shared
  SFX/music once under `export_full/structured/Audio/shared/`, indexes
  language voice files under `export_full/structured/Audio/<LANG>/`, parses Wwise bank
  event-to-media links, and post-processes generated conversation JSON so
  dialog/cutscene lines and recoverable cutscene audio events can render native
  browser audio controls. It accepts scalar or list-valued audio path fields
  (`audioPath`, `audioPaths`, `audioDialogPath`, `audioDialogPaths`) from Story
  payloads and their `_debug.source` blocks.
- `hash_export_pngs.py`: hashes every `.png` file under `..\export_full\` with
  parallel readers and writes `path,hash` CSV rows to
  `..\reports\export_full_png_hashes.csv` by default.
- `find_duplicate_dialog_lines.py`: scans generated
  `webui/data/lang/<LANG>/conv/*.json` files for exact repeated spoken line
  text across different missions, reporting the speaker, mission, scene, and
  line ids. It defaults to `dlg` conversations and can emit text, JSON, or CSV.
- `asset_builder/`: shared asset-browser indexing, story-media selection, and
  demo bundle helpers used by `build_assets.py` and the Updates builder.
- `pack_webui.py`: packages split shareable WebUI zips from
  `serve.py`, `..\webui\`, and displayed media files under `..\export_full\`.
  The primary zip is story/gameplay/reference code/data plus emoji, including
  the full `envEmoji_common_*` prefab layer sprite set; the companion assets zip
  carries larger images and videos; the standalone audio zip carries decoded
  story audio. Legacy local index folders are excluded by default because
  they point back to the local export tree.
- `download_bilibili_video.py`: optional gameplay-video intake helper for the
  OCR/audio story-order workflow. It downloads Bilibili pages into the flat
  `..\videos\` folder using browser-exported cookies, resumable `.m4s` parts,
  per-file `.lock` guards, and `ffmpeg` stream muxing. It intentionally uses
  the external `requests` package and is not part of the stdlib-only export
  path or any normal `export.bat` run.
- `common.py`: small shared constants and JSON/path helpers for the
  WebUI builders.
- `recover_envemoji_prefabs.py`: regenerates the `envEmoji_common_*` prefab
  registry consumed by the Story builder's EnvTalk emoji rows. Merges the
  AnimeStudio JSON pass (RectTransform layer geometry, colors, enter
  animation curves) with the Dump pass (GameObject PathID active state) so
  duplicate child names inside emoji bundles do not collide. Not part of
  `export.bat`; run it after Endfield updates that touch emoji prefab data.
- AnimeStudio CLI file exports are expected to use
  `{name}_p<PathID>` names. The export wrapper includes this naming contract in
  its cache signature and clears refreshed type folders before rerunning them,
  so stale files from older naming contracts are removed by a forced refresh of
  the affected stage/type. AnimeStudio-derived WebUI inputs that do not carry
  the PathID suffix are ignored.
## WebUI Story Helpers

These are kept because the WebUI story builders import or use them:

- `story_builder/timeline_recovery.py`: parses `dlgtl_*` Timeline MonoBehaviour
  data into authored line orders. It prefers the full AnimeStudio
  `json_by_type/MonoBehaviour` export and only falls back to filtered
  `timeline_extract` CLI exports for focused diagnostics or when the full
  export has no recoverable Timeline tracks; pass
  `--extract-timeline-assets` to force the old extraction path. Backs the
  `dialogTimeline` recovery mode, which corresponds to the runtime path
  `Beyond.Gameplay.Core.DialogTimelineManager.PlayDialogTimeline`.
- `story_builder/timeline_action_evidence.py`: scans AnimeStudio
  MonoBehaviour JSON for recovered managed-reference action payloads, follows
  `DialogMainFlowData` RID links to trunk line actions, compares the recovered
  action-flow line sequence against `timeline_line_orders.json`, and writes
  `export_full/recovered/AnimeStudio-cli/timeline_action_evidence.json`.
  The Story builder attaches compact results under
  `conv._debug.timelineActions` for WebUI `Show debug info`; it is evidence
  only and does not reorder Story rows by itself. Rich output requires a
  refreshed AnimeStudio Story JSON export that includes
  `$animestudio.recoveredManagedReferences.RefIds`.
- `story_builder/mission_recovery.py`: reconstructs mission-level quest/scene
  ordering evidence from `MissionRuntimeAsset`.
- `story_builder/dialog_registry.py`: extracts
  `Beyond.Gameplay.DialogIdTable` (the runtime's authoritative dialog
  registry) into a sceneKey index used by `scene_order_gap_shared.py` for
  evidence-grounded "registered vs cut content" classification. Runs as
  part of `export.bat` between the main export step and the build steps.
- `story_builder/source_links.py`: scans `MissionRuntimeAsset`,
  `LevelScriptData`, and `LevelScriptTemplateData` for `dlg_*`, `radio_*`,
  `sns_*`, `cutscene_*`, `remotecomm_*`, and reading-popup references. It
  writes `export_full/recovered/story_source_links.json`; the Story builder
  stamps matching conv files and index entries with source evidence and
  writes per-language coverage/orphan reports.
- `story_builder/levelscript_binary.py`: shared raw LevelScriptData helpers.
  It verifies serialized script ids against file names and decodes the
  top-level MemoryPack tail fields that are currently stable, including
  `startType` when the adjacent `startShapeList` can be skipped safely. It
  also decodes the three serialized `ActionSerializedMap` UID-list boundaries
  in the GameAssembly/MetadataRegistration-backed order (`actionList`,
  `getterList`, `headerList`) and diagnostic action payload hints, including
  `0x0bed/0x00` terminal-branch tail refs as local LevelScript action ids and
  compact `ActionHeader.nextId` prefixes on high-code header/event rows.
  When a two-block action map has an omitted/empty getter block followed by a
  header-shaped final block, it labels that final block as `headerList`.
- `story_builder/video_bindings.py` builds the narrative video binding evidence used
  by the Story builder. It scans dialog `timeline_extract` outputs plus the
  full story-scoped AnimeStudio `json_by_type/MonoBehaviour` exports, so
  gameplay cutscene playables such as `*_cutscene_*_actor.playable` can bind
  `BeyondFMVPlayableAsset.fmvId` back to a cutscene entry. Timeline-backed
  links are preserved into
  `webui/data/lang/<LANG>/narrative_video_evidence.json` so a WebUI video can
  be traced to the exact `BeyondFMVPlayableAsset` / Timeline source instead of
  relying on filename matching. Narrative videos that only match by name are
  emitted as standalone `video` story files grouped by mission, while resolved
  mappings attach to the dialog, cutscene, remotecomm, or other story file and
  keep the standalone row adjacent in Story sort. Timeline / playable evidence
  supplies authored inline placement when available. Manual attach and
  suppression rules in `webui/overrides/narrative_videos.json` cover known
  filename mismatches and known false attachments while keeping standalone
  video rows. An attach rule can also set `audioFrom` to copy source cutscene
  audio events into the attached target during the audio relink step.
- `story_builder/` also scans narrative video folders under
  `Data/Video/PC/Narrative/Cutscene` and `RemoteComm`, attaches matching
  `narrativeVideos` to dialog/cutscene/remotecomm conv JSON, and writes
  `reports/narrative_videos_<LANG>.json` / `.md`.
- `story_recovery/build_narrative_video_override_audit.py` validates
  `webui/overrides/narrative_videos.json` against the generated Story video
  report, `narrative_video_evidence.json`, video indexes, and conv payloads.
  It reports missing override stems/targets, missing `audioFrom` source keys,
  stale attach/suppress rules, filename-only attachment candidates, and
  unresolved video candidate keys.
- `story_recovery/build_option_override_coverage_audit.py` validates
  current `inferredOptionLayout` and `inferredOptionResponse` warning records
  against `webui/overrides/options.json`. It writes
  `reports/option_override_coverage_<LANG>.json` / `.md` and distinguishes
  raw recovery uncertainty from manual WebUI display coverage.
- `webui/overrides/options.json` is a runtime WebUI-only manual
  override file for known option recovery gaps. It can pin option groups with
  `positions.after.<lineId>: ["<group>"]` or `positions.pre`, and can map
  inferred option replies with `responses.<optionId>: ["<lineId>"]`. Edit it
  and refresh the browser; no Story rebuild is needed. Overrides do not promote
  new automatic evidence, and overridden rows are tagged in the Story view.

## Story Recovery Tools

These tools are not part of `export.bat`. Most live under
`scripts/story_recovery/` so the root export/package commands stay easy to
scan; the root-level Bilibili downloader is listed here because it feeds the
gameplay-video OCR/audio workflow.

- `story_recovery/build_runtime_jump_option_route_audit.py`: audits remaining
  live `inferredOptionResponse` warning groups against nearby Runtime Jump
  Track clips, including forward skip ranges, reverse/directional ranges, and
  `needChangeOptionAfterJump` markers. It writes
  `reports/runtime_jump_option_route_audit_<LANG>.json` / `.md`. Use it
  before promoting any new automatic option-route rule. Pass
  `--include-promoted-risk-groups` only when you intentionally want to inspect
  already anchored diagnostic `optionBranchRisk` rows.
- `story_recovery/build_option_route_evidence_controls.py`: summarizes
  positive Runtime Jump route controls from `timeline_line_orders.json` beside
  the current negative-control `runtime_jump_option_route_audit` queue. It
  writes `reports/option_route_evidence_controls_<LANG>_priority.json` / `.md`
  and documents the evidence bar for promoting inferred option responses.
- `story_recovery/build_priority_story_order_audit.py`: summarizes the current
  main-story, event, major-mission, and character-story recovery surface from
  the built WebUI data. It writes `reports/priority_story_order_<LANG>.json` /
  `.md`, including ordered/unknown totals, remaining inferred responses,
  non-runtime option-layout rows, uncovered line warnings, and top unknown
  missions.
- `download_bilibili_video.py`: optional downloader for collecting gameplay
  videos before OCR. It accepts BVIDs directly or from `--bvid-file`, defaults
  to the repo-local cookie export at
  `cookies/www.bilibili.com.cookies.json`, writes flat `.mp4` outputs under
  `videos/`, prefers AVC for local playback, adopts matching legacy nested
  video files unless `--no-adopt-existing` is passed, and skips completed files
  unless `--overwrite` is used. Use `--dry-run` to inspect planned filenames
  without downloading. It requires network access, `requests`, valid Bilibili
  cookies, and `ffmpeg`; keep partial `.m4s` and `.lock` files out of the OCR
  corpus until the muxed `.mp4` is complete.
- `story_recovery/build_gameplay_video_ocr_audit.py`: lower-level OCR worker
  used by the full gameplay video story-order pipeline. It samples final
  gameplay videos from `videos/`, crops the subtitle/options band of every 10th
  frame by default (`13%-100%` width, `50%-97%` height) at source resolution,
  and runs OCR on that crop. The default engine is **PaddleOCR PP-OCRv5**
  (`--ocr-engine paddleocr`, `server` variant), which is markedly more accurate
  on Chinese subtitle text and, on a CUDA build, far faster (~0.13 s/frame on an
  RTX 5080) than the legacy **EasyOCR** engine (`--ocr-engine easyocr`). EasyOCR
  uses a Story-derived character dictionary by default, built from CN
  conversation text, speaker labels, summaries, and options; pass
  `--disable-ocr-dictionary` for unconstrained recognition (the dictionary
  allowlist applies to EasyOCR only - PaddleOCR's recognizer has a fixed
  dictionary and relies on downstream Story matching to filter). It writes
  per-video reports plus an aggregate index under
  `reports/gameplay_video_ocr/`. The runner skips `.lock`, `.m4s`, zero-byte,
  and other partial downloads, and it skips already completed videos when a
  complete per-video OCR report already exists for the same source file. Use
  `--frame-step 10` for the current default cadence, `--dry-run` to inspect
  pending videos, `--limit-frames` for smoke tests, and `--force` only when
  intentionally reprocessing completed videos. Decoded sampled-frame JPEGs are
  kept by default under `tmp/gameplay_video_ocr/frames/`; reruns reuse existing
  frame files and append only missing sampled frames. Pass `--discard-frames`
  only for a disposable run. The default OCR language is Simplified Chinese
  (`chi_sim`; for EasyOCR mapped to `ch_sim`). PP-OCRv5 weights are cached under
  `~/.paddlex/official_models/`; EasyOCR weights live under `tools/easyocr/`.
  Both recognizers also support ASCII letters, digits, and common punctuation.
  OCR output
  is filtered before it becomes a segment: UID/latency overlays are stripped,
  Chinese-rich spans are extracted from mixed junk lines, short lines are
  dropped unless they look like short Chinese speaker names, and mostly-symbol
  lines are rejected. The default recognition and line filters are
  intentionally permissive so short subtitle fragments, speaker names, and
  lower-confidence OCR boxes are kept for matching. Mostly-black sampled
  frames bypass the normal subtitle crop and are replaced in the decoded-frame
  cache by a near-full-frame OCR crop (`10%-97%` height) that avoids the top
  HUD and bottom UID strip. Archive-box frames and detected SNS interface
  prompts, such as the first-frame P11 SNS option panel, get a second exact
  source-frame OCR pass using the same near-full ROI and are recorded as
  `archive-box` or `sns-interface` observations. The script logs OCR
  configuration, report output location, pending/skip reasons, pending video
  order, ffprobe metadata, black-frame scan stats, frame extraction status,
  EasyOCR image groups, OCR dictionary size/hash, per-batch OCR timing,
  kept/filtered frame counts, dark-frame/archive/SNS near-full crop counts,
  the full filtered per-frame timeline in each per-video markdown
  report, per-video elapsed/remaining/ETA lines, an overall video progress bar,
  and a live status index at
  `reports/gameplay_video_ocr/gameplay_video_ocr_index.md`. It orchestrates
  external `ffmpeg`/`ffprobe` plus the OCR engine (PaddleOCR/Paddle on CUDA, or
  EasyOCR/PyTorch). ffmpeg tries CUDA/NVDEC decode automatically when the local
  ffmpeg build supports it, with CPU fallback if hardware decode fails. Both OCR
  engines use CUDA when available unless `--easyocr-cpu` (the shared force-CPU
  switch) is passed. The PaddleOCR GPU path uses a locally built
  `paddlepaddle-gpu` wheel with Blackwell `sm_120` support; it imports `torch`
  first so paddle reuses torch's bundled CUDA 12.8 / cuDNN 9 runtime DLLs (see
  `memory/` notes / `scratch/paddle_build/`). The PP-OCRv5 server default
  `--paddleocr-frame-batch-size 40` was benchmarked on cached P10 gameplay
  crops on an RTX 5080; batch 56 was effectively tied, while 64+ regressed.
- `story_recovery/build_gameplay_video_story_order.py`: full OCR/audio-to-order
  promotion pipeline. It can run the OCR sampler first with `--run-ocr`, then
  matches completed OCR segments against current CN Story text rows, summaries,
  and option text, and matches decoded Story audio templates against each
  gameplay video's audio track. Story file titles are excluded from OCR segment
  matching so mission-title overlays do not place SNS, archive, or other story
  files by title alone.
  Audio matching uses ffmpeg to build cached mono speech-band RMS/delta
  fingerprints under `tmp/gameplay_video_ocr/audio/`. A sparse landmark
  prefilter keeps the expensive normalized correlation pass to the strongest
  candidate offsets instead of scanning every video window for every template.
  `au_music*` templates are skipped by default so gameplay BGM is treated as
  background, and accepted audio-template hits are preferred over OCR spans
  when both place the same Story key. Pass `--disable-audio-match` for an
  OCR-only run or `--audio-include-music` only when music-event matching is
  intentional. The
  matcher reads the current user-managed order in
  `webui/overrides/story_order.json`,
  uses missions marked `locked: true` as controls for an OCR threshold sweep,
  then rebuilds final observed sequences with the selected effective threshold.
  Each gameplay video's search scope includes its inferred mission plus the
  inferred missions for adjacent parts in the same video series, so a `P10`
  report can also match Story files from `P9` and `P11`.
  By default it only moves recognized Story files to the front of each mission
  order and does not infer order from numeric file indexes; pass
  `--infer-index-gaps` only when indexed gap insertion is intentional. Pass
  `--old-videos-only` to limit both OCR sampling and loaded OCR reports to the
  original gameplay BVIDs. Synthetic archive-to-map-dialog companion matches
  are disabled by default because they are not direct gameplay observations.
  The terminal output and markdown report include locked-order mismatch counts
  per mission. Each matching run refreshes both
  `reports/gameplay_video_ocr/story_order_ocr_matches.json` and `.md` with a
  shared generated timestamp. It emits
  a proposed full-list story order at
  `reports/gameplay_video_ocr/story_order_ocr_proposed_story_order.json`.
  It also writes a WebUI debug reference at
  `webui/data/story_order_ocr.json` via `build_webui_ocr_order.py`, so debug
  mode can compare the OCR order with static recovery and the current override.
  A full all-video OCR/order refresh is
  `python scripts\story_recovery\build_gameplay_video_story_order.py --run-ocr`;
  it always leaves `webui/overrides/story_order.json` untouched while refreshing
  the standalone reports and WebUI OCR reference. Users review OCR, static
  recovery, and manual evidence before saving the final active order through the
  WebUI or by editing the override. Mission locks are preserved in the proposed
  OCR output. Smoke OCR reports made with `--limit-frames` are
  ignored unless `--include-smoke` is passed. The matcher logs corpus/index
  loading, OCR report scan skip/load counts, report match order, and per-video
  OCR-segment matching progress. It ignores stale OCR reports from older filter
  versions unless `--include-stale-ocr` is passed. The wrapper intentionally
  exposes only the practical OCR controls:
  `--ocr-engine` (default `paddleocr`), `--frame-step`, `--ocr-crop`,
  `--ocr-limit`, `--ocr-limit-frames`, `--paddleocr-frame-batch-size`,
  `--easyocr-cpu`, `--disable-ocr-dictionary`, and `--force-ocr`.
- `story_recovery/build_webui_ocr_order.py`: distills
  `reports/gameplay_video_ocr/story_order_ocr_proposed_story_order.json` into
  the small WebUI-served reference `webui/data/story_order_ocr.json`. Run it
  directly when the proposed OCR order already exists and only the debug compare
  reference needs to be refreshed.
- `story_recovery/show_gameplay_video_order_comparison.py`: focused review
  helper for selected OCR reports. It defaults to current P10 OCR outputs,
  reruns the text-only Story matcher for those reports, and writes a
  side-by-side comparison of matched mission order against
  `webui/overrides/story_order.json` to
  `reports/gameplay_video_ocr/p10_story_order_comparison.json` / `.md`.
  Pass `--include-stale-ocr` to include older P10 reports that the current
  matcher normally skips.
- `story_recovery/build_levelscript_opcode_shape_audit.py`: scans all
  decoded `LevelScriptData` action records and groups opcode/kind pairs by
  payload shape, actionMap role, strings, property keys, trigger slots,
  compact script pointers, decoded compact gate/terminal local refs, and
  ManualStart-like `levelId+scriptId` payloads.
  It writes `reports/mission_order/levelscript_opcode_shape_audit.json` /
  `.md` and is the first stop before naming new setter/start opcodes. It
  reports serialized-map membership separately for `actionList`, `getterList`,
  and `headerList`, with only residual UID records treated as outside the
  serialized map.
- `story_recovery/build_levelscript_action_map_list_audit.py`: audits the
  three physical `ActionSerializedMap` UID-list blocks against GameAssembly
  setter dispatch, MetadataRegistration type resolution, and observed opcode
  content. It writes
  `reports/mission_order/levelscript_action_map_list_audit.json` / `.md` and
  documents omitted-getter/header-only two-block cases; current recovery moves
  derived `ScriptEventHeader`-band rows into `headerList` rather than
  `getterList`.
- `story_recovery/build_levelscript_manual_control_audit.py`: follows the
  now-named ActionBase manual control records (`0x02f1/0x0a`
  `ManualStartLevelScript`, `0x02ec/0x0a` `ManualEndLevelScript`), checks for
  literal target operands, and records the common adjacent trigger-event
  pattern. It writes
  `reports/mission_order/levelscript_manual_control_audit.json` / `.md`;
  current recovery finds `84` manual control rows, `74` trigger-adjacent
  activation pairs, only `4` rows with literal script-id operands, and `0`
  literal cross-script targets.
- `story_recovery/build_levelscript_property_setter_candidate_audit.py`:
  follows the MissionRuntime property-check bridges into the target
  `LevelScriptData` files, keeps exact key-bearing UID records separate from
  offset-only/top-level property data, and ranks local setter/gate/listener
  opcode candidates by chain position and decoded payload hints. It writes
  `reports/mission_order/levelscript_property_setter_candidates_<LANG>.json`
  / `.md`; the output is diagnostic and not direct order-promotion evidence.
- `story_recovery/build_levelscript_gate_audit.py`: follows `0x0a03/0x00`
  compact condition/gate records. The shared binary decoder now exposes the
  stable shape as a property key, type code, post-key flag, and optional tail
  local action ref. The audit walks that local ref separately from ordinary
  `nextId`, then cross-checks MissionRuntime property bridges. It writes
  `reports/mission_order/levelscript_gate_audit_<LANG>.json` / `.md`;
  current CN recovery finds `219` gate rows, `171` decoded property-key rows,
  `41` rows with tail local refs, and `10` MissionRuntime-bridged rows.
- `story_recovery/build_levelscript_terminal_branch_audit.py`: follows
  `0x0bed/0x00` terminal-branch records through their decoded tail local-id
  refs, then walks `nextId`, split-list refs, and nested terminal refs to
  expose the story/play records reachable after a compact property terminal.
  It writes
  `reports/mission_order/levelscript_terminal_branch_audit_<LANG>.json` /
  `.md`; current CN recovery finds `1,529` terminal rows, `6` MissionRuntime
  property-bridged rows, `156` rows with story-key targets, and `154` rows
  with play-action targets.
- `story_recovery/build_levelscript_setter_overlap_audit.py`: compares
  MissionRuntime `CheckLevelScriptProperty*` triples against named ActionBase
  setters (`0x03b8/0x0a` `SetBool`, `0x03e7/0x0a` `SetInt`,
  `0x03ea/0x0a` `SetIntIncrease`). It writes
  `reports/mission_order/levelscript_setter_overlap_<LANG>.json` / `.md`;
  current CN recovery finds `1,331` decoded setter-key rows but `0` exact
  `(mapId, scriptId, key)` matches to MissionRuntime property checks.
- `story_recovery/build_levelscript_action_metadata_audit.py`: extracts a
  focused IL2CPP metadata view for LevelScript action/event classes, including
  ManualStart/ManualEnd, property getter, property-change listener, and
  trigger-volume event shapes, plus the generic `Set<T>` / `SetList<T>` and
  ParamBlackboard/ParamVariable property-storage surfaces. It also keeps the
  `ActionMapAssetRaw -> ActionSerializedMap` layer visible. Runtime fields are
  `headerList`, `actionList`, and `getterList`; the body audit shows setter
  dispatch in `actionList`, `getterList`, `headerList` order, and the list
  audit checks that against binary content signatures. This is the current
  best lead for unnamed compact records such as `0x0a03/0x00` and
  `0x0bed/0x00`. It writes
  `reports/mission_order/levelscript_action_runtime_metadata.json` / `.md`
  and is used to reject property-key records that only match read/gate/listener
  families while keeping the generic setter family visible.
- `story_recovery/build_levelscript_action_map_type_audit.py`: resolves the
  ActionSerializedMap and ActionMapRuntime type indexes that the metadata-only
  catalog leaves as `<type-index:N>`. It reads GameAssembly
  `Il2CppMetadataRegistration` and writes
  `reports/mission_order/levelscript_action_map_type_indices.json` / `.md`;
  current recovery resolves `actionList` to `List<ActionBase>`, `getterList`
  to `List<PureGetter>`, `headerList` to `List<ActionHeader>`, and the runtime
  arrays to `ActionBase[]`, `PureGetter[]`, and `ActionHeader[]`.
- `story_recovery/build_levelscript_action_body_audit.py`: maps the focused
  LevelScript action/runtime metadata targets to `GameAssembly.dll` and writes
  a compact body report at
  `reports/mission_order/levelscript_action_body_targets_gameassembly.json`
  / `.md`. It confirms manual start/end calls, property getter reads,
  property-change listener registration, and the runtime
  `UpdateRuntimeState -> ModuleResetUpdateProperty` path. It also checks the
  generic setter follow-up: concrete MemoryPack wrappers deserialize
  `set____key__` before `set____value__`, and their generic wrapper setters
  store key/value at the real instance offsets `+0xd0`/`+0xd8`. It also maps
  `ActionSerializedMapForMemoryPack.Deserialize`, confirming calls to
  `set___actionList__`, `set___getterList__`, and `set___headerList__` in
  that order; the setters write ActionSerializedMap fields at `+0x18`,
  `+0x20`, and `+0x10`. It also tracks `ActionHeaderForMemoryPack` setter
  bodies, including `set____nextID__` at runtime field `+0x60`, which backs
  the compact payload `ActionHeader.nextId` decode used by the header-chain
  audit. Use the ActionBase formatter tag audit below for the opcode-to-class
  bridge.
- `story_recovery/build_levelscript_actionbase_tag_audit.py`: extracts the
  generated `ActionBaseForMemoryPackFormatter..cctor` union tag table from
  `GameAssembly.dll`, also checks the tiny `FinalActionBase` formatter, and
  decodes runtime-metadata type slots back through `global-metadata.dat`. It writes
  `reports/mission_order/levelscript_actionbase_formatter_tags.json` / `.md`
  and cross-references `levelscript_opcode_shape_audit`: current recovery finds
  contiguous ActionBase tags `0x0000..0x04dc`, names common playback records
  (`0x034a` `PlayRadio`, `0x046c` `StartDialogAction`), and confirms
  manual control opcodes (`0x02f1/0x0a` `ManualStartLevelScript`,
  `0x02ec/0x0a` `ManualEndLevelScript`) and setter-class opcodes such as
  `0x03b8/0x0a` `SetBool`,
  `0x03e7/0x0a` `SetInt`, and `0x03ea/0x0a` `SetIntIncrease`. High
  event/gate/terminal records such as `0x0a03/0x00`, `0x0bed/0x00`,
  `0x12a1/0x00`, `0x12a3/0x00`, and `0x13a5/0x00` are outside that
  ActionBase tag range.
- `story_recovery/build_memorypack_union_tag_audit.py`: scans all generated
  MemoryPack formatter `.cctor` union registrations and writes
  `reports/mission_order/memorypack_union_formatter_tag_audit.json` / `.md`
  plus an all-image variant. Current recovery finds no raw union tag above
  `0x04dc`, but derives `110` ActionHeader/header mappings from extracted
  formatter tags and observed high-code banks, including low `0x0e**` /
  `0x0f**` ActionHeader banks, custom events, dialog enter/exit, quest-state
  changes, trigger-volume enter/leave, script-stage changes, and train-level
  events. `0x0a03/0x00` is now
  structurally decoded as a compact condition/gate record with a type code,
  post flag, and optional tail local action ref; `0x0bed/0x00` is now decoded
  as a compact terminal branch carrier with local action refs, though both
  runtime class families are still unnamed.
- `story_recovery/build_selector_formatter_tag_audit.py`: extracts selector
  Finder/Validator/PostProcessor MemoryPack formatter evidence from
  `GameAssembly.dll`. It writes
  `reports/mission_order/selector_formatter_tag_audit.json` / `.md`; current
  recovery resolves Finder tags `0x0000..0x0013`, Validator tags
  `0x0000..0x000a`, and PostProcessor tags `0x0000..0x0008` to concrete
  selector formatter names.
- `story_recovery/build_selector_targetsettings_body_audit.py`: regenerates the
  focused selector/TargetSettings IL2CPP metadata catalog, maps it to
  `GameAssembly.dll`, preserves the raw body report, and writes
  `reports/mission_order/selector_targetsettings_chain_summary.json` / `.md`.
  The compact summary records FindTargetAction/SelectorData/TargetSettings
  setter call order, setter store offsets, aliasing warnings, selector tag-map
  evidence, and the current "parser still missing" gate before FindTargetAction
  chain consumption can be enabled.
- `story_recovery/build_findtarget_selector_boundary_audit.py`: scans exported
  BuffData through the existing WebUI data decoder and writes
  `reports/mission_order/findtarget_selector_boundary_audit.json` / `.md`. It
  groups real FindTargetAction body-middle byte shapes, checks whether the
  current TargetSettings envelope parser accepts any middle-byte candidates,
  stores complete body-middle hex for parser replay in JSON, lists ambiguous
  first-FindTarget records, and keeps selector tag byte hits as non-proof
  prioritization hints.
- `story_recovery/build_findtarget_selector_replay_audit.py`: replays the saved
  FindTargetAction body-middle byte shapes against the current TargetSettings
  envelope helper and selector formatter tag maps. It writes
  `reports/mission_order/findtarget_selector_replay_audit.json` / `.md`, keeps
  selector matches as tag-only hints, consumes only locally proven empty-payload
  selector prefixes, and reports exact boundary proof and chain-safe FindTarget
  counters separately from noisy union-tag candidates.
- `story_recovery/build_findtarget_selector_payload_priority_audit.py`: ranks
  nonzero FindTarget selector tag hints against MemoryPack metadata setter
  complexity. It writes
  `reports/mission_order/findtarget_selector_payload_priority_audit.json` /
  `.md` and identifies empty-payload selector targets for bounded byte-probe
  follow-up work.
- `story_recovery/build_lua_consumer_reference_audit.py`: scans extracted Lua
  roots and writes `reports/mission_order/lua_consumer_reference_audit.json` /
  `.md`. It deduplicates Persistent/StreamingAssets modules by relative Lua
  path, extracts `Tables.*`, `GEnums.*`, `CS.Beyond.*`, `contentParam`,
  dialog/RemoteComm ids, sprite/video/audio helper references, checks
  `Tables.*` names against exported Table JSON roots, emits graph-ready
  Lua module-to-table edge candidates, and summarizes focus areas such as
  SNS, RemoteComm, Dialog, map marks, and mission UI.
- `story_recovery/build_skipped_vfs_block_audit.py`: summarizes an
  AnimeStudio/fluffy-dumper `vfs-index` JSON for WebUI-skipped VFS blocks such
  as Lua, ExtendData, Streaming, DynamicStreaming, and BundleManifest. It
  writes `reports/mission_order/skipped_vfs_block_audit.json` / `.md` with
  counts, sizes, top directories, largest files, and story/SNS/UI signal
  samples so broad raw dumps can be prioritized.
- `story_recovery/build_levelscript_header_chain_audit.py`: uses the compact
  `ActionHeader.nextId` payload field on `headerList` rows to walk from
  event/listener records into `actionList` chains. It writes
  `reports/mission_order/levelscript_header_chain_audit.json` / `.md`;
  current recovery finds `10,085` header rows, all `10,085` named, `9,961`
  rows targeting `actionList`, `123` duplicate-local-id ambiguous action
  targets, `0` missing positive targets, `1,647` event chains with named play
  actions, and `1,791` chains with scene-like text.
- `story_recovery/build_option_playable_semantics_audit.py`: audits remaining
  `inferredOptionResponse` groups against decoded
  `DialogOptionPlayableAsset` fields such as `logicId`, `trunkId`,
  `dialogId`, `conditionRid`, `changeFinishNum`, and `targetFinishNum`. Use
  `--only-interesting` to focus on groups where `logicId` is the only
  non-default semantic clue, or `--story <key> --group <n>` for a targeted
  scene check.
- `story_recovery/build_option_logic_id_audit.py`: follows up on the `logicId` queue by
  scanning structured tables, `MissionRuntimeAsset`, `LevelScriptData`,
  `LevelScriptTemplateData`, gameplay config, and Lua consumer terms for exact
  references to option `logicId` values. Same-mission mission/level-script
  matches would be high-value evidence; table/config-only matches are
  diagnostic unless another source links them to the dialog.
- `story_recovery/build_dialog_tree_option_route_audit.py`: audits remaining
  `inferredOptionResponse` groups against decoded AnimeStudio DialogTree
  routes, related scene links, target fragments, and cinematic wrappers. Use it
  after the option-playable and `logicId` audits to separate cases where
  the Story builder could promote authored tree evidence from the larger queue
  that needs deeper Timeline/runtime option-target decoding.
- `story_recovery/build_timeline_option_flow_audit.py`: audits remaining
  `inferredOptionResponse` groups against raw Timeline trunk clips. It reports
  whether candidate response clips carry useful non-default `optionIndex`
  values, resolves `misc_dlg_*` WebUI aliases to underlying `dlg_*` Timeline
  entries, and separates promotable `trunkClipOptionIndexRoute` cases from the
  common default `optionIndex=0` adjacent layouts that are diagnostic only.
- `story_recovery/build_timeline_binding_audit.py`: checks whether unresolved
  option responses separate cleanly by Timeline track, track binding, actor
  binding, or option-clip placement.
- `scene_order_gap_shared.py`: classifies each scene's line-order and
  option-layout recovery quality. Consumes the DialogIdTable registry above
  to upgrade `lineIdSuffix`-mode scenes to one of:
  - `unregisteredScene`: sceneKey is absent from `DialogIdTable`, so the
    runtime cannot load this scene at all (cut/dead content; the only order
    that exists is `DialogTextTable` layout).
  - `dialogTrunkRowIteration`: sceneKey IS registered but no Timeline or
    dialogTree source matched; `DialogTrunkBehaviour` would iterate
    `DialogTextTable` rows by sceneKey prefix, which produces the same
    sequence we already emit.
- `story_recovery/annotate_conv_with_registry.py`: standalone refresher for stamping each
  dialog conv JSON's `_debug` block with a `runtimeRegistry` evidence record
  (registered flag, trunk count, per-trunk line ids from `DialogIdTable`).
  The Story builder does this during normal exports; the refresher is useful
  when updating existing conv files without a full rebuild. Pure evidence
  surfacing; no inference.
- `story_recovery/rewrite_scene_order_warnings.py`: one-shot warning rebuild for conv
  JSONs without re-running the Story builder. Useful after tightening
  `scene_order_gap_shared.py` criteria.

### IL2CPP-derived evidence (out-of-band)

The C# class hierarchy backing the recovery modes was confirmed by scanning
`global-metadata.dat` from the game's IL2CPP runtime. The maintained helpers
under `tools/endfield-il2cpp/` validate/cache the metadata artifact, catalog
option-flow fields and method targets, and map focused body targets to
`GameAssembly.dll` addresses. They write drift/evidence reports outside the
normal WebUI build.
Relevant runtime types:

- `Beyond.Gameplay.Core.DialogManager` (partial across `.DialogTree.cs`,
  `.Level.cs`, `.LifeCycle.cs`, `.Timeline.cs`) -- routes every dialog load
- `Beyond.Gameplay.Core.DialogTrunkBehaviour` -- per-trunk playback driver
- `Beyond.Gameplay.Core.DialogTimelineManager` -- Timeline-driven path
- `Beyond.Gameplay.Core.DialogTreeController` -- tree/branch navigation
- `Beyond.Gameplay.Core.DialogOptionBehaviour` -- option/choice nodes
- `Beyond.Gameplay.DialogIdTable` -- runtime dialog registry (extracted by
  `story_builder/dialog_registry.py`)

There is **no** separate document / letter / memo / consent-form UI loader
class anywhere in the runtime. Every dialog scene -- including the "letter"
and "consent form" content -- goes through `DialogTrunkBehaviour
._TryInitDialogText`, with `DialogTimelineManager` and `DialogTreeController`
overlaid when applicable.

## Archived

The old archived-script bucket has been retired. UE5 pose-demo helpers live
with the UE project under `../ue5_zhuangfy_pose_demo 5.3/Scripts/`.
Put new experiments in `../scratch/` or `../tmp/`, and move observations or
conclusions to `../memory/` when they need to be kept.
