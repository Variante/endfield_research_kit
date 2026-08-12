# AnimeStudio recovery

## Current status

The tracked `tools/AnimeStudio` fork is a reliable extraction layer. It can:

- index StreamingAssets and Persistent VFS roots;
- dump or stream selected blocks;
- build compact VFS and asset indexes;
- export WebUI-facing Unity objects;
- decode Wwise media;
- preserve PPtr/source-offset evidence;
- export selected shader bytecode and material state;
- retain useful partial MonoBehaviour output.
- publish component-level scene context in the opt-in object index: exact
  GameObject/Transform identities, hierarchy path, local position, computed
  world position, and an explicit hierarchy-resolution status;
- publish boolean identifier/state scalars under the same strict scalar
  contract as strings and integers.

The current installed-data Story indexes are committed and hash-validated.
StreamingAssets contains 1,218,871 objects and 883 schemas; Persistent contains
175,176 objects and 326 schemas. Both summaries are complete and have no merge
errors. Story carrier and guide-consumer validators accept the current
`s:string`, `i:integer`, and `b:boolean` scalar contract and report source,
serialized file, PathID, row index, and expected/actual values on malformed
input.

Remaining work is certification and semantic depth, not basic access.

## Maintained workflow

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI

.\export.bat --from-game
.\export.bat --from-game --with-assets
.\export_assets.bat --from-game
```

Expected CLI:

```text
tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

Optional DummyDll regeneration is maintained and build-specific:

```bat
python scripts\animestudio\generate_dummydll.py --dry-run
python scripts\animestudio\generate_dummydll.py --replace
```

The generator discovers and validates CodeRegistration and
MetadataRegistration from the exact installed `GameAssembly.dll` plus metadata
image set, prepares the tested patched Cpp2IL `2022.0.7` checkout, stages the
assemblies, and atomically publishes `tools\DummyDll` with `generation.json`
provenance. The pre-generator June set has no manifest and must be treated as
unverified against later game builds. DummyDlls improve managed class identity
and script-derived TypeTrees only for types Cpp2IL actually emitted; malformed
or skipped types remain an explicit gap, and serialized-first stays the safe
default.

Direct CLI use is for bounded diagnostics:

```bat
AnimeStudio.CLI.exe dump --help
AnimeStudio.CLI.exe stream --help
AnimeStudio.CLI.exe vfs-index --help
AnimeStudio.CLI.exe audio --help
AnimeStudio.CLI.exe list --help
```

Both VFS roots must be configured as fallbacks. Missing block metadata or
chunks is an integrity error, not an omitted file.

## Export model

Keep these states distinct:

- **indexed:** VFS file exists;
- **loaded:** Unity container/object entered the parser;
- **exported:** output or intentional empty marker was written;
- **partial:** useful evidence exists but decoding is incomplete;
- **certified clean:** explicit status proves no unexplained warning, missing
  dependency, or conversion failure.

Success of a wrapper stage does not certify every asset bundle or object.

The normal type-job mode is `auto`: broad Story JSON types run in isolated
processes while map-filtered asset conversion remains sharded. Reduce
`--animestudio-jobs` when RAM is constrained.

Endfield-native HGGraphics class IDs recovered from the installed UnityPlayer
are named directly (`HGTree`, `HGTreeData`, `HGMeshRenderer`, and
`HGMeshRendererData`). An explicitly selected export-enabled generic TypeTree
class is retained in a minimal AssetMap; unselected generic objects remain
omitted, so normal production map scope does not widen.

## Important boundaries

- Combined Story+asset export must keep Story JSON broad; asset-map filtering
  can omit valid DialogTree sources.
- PPtr identity is source/CAB scoped.
- `$partial` objects remain queryable and visibly incomplete.
- Material JSON preserves keywords, queues, tags, instancing, and disabled
  passes.
- Shader bytecode recovery does not prove runtime variant selection.
- AnimationClip fixes must preserve runtime curves and fail visibly on new
  layouts.
- Audio decoding separates shared media from language voice.
- AudioDialog mapping must merge the primary Table block with the fallback
  Persistent Table overlay. The primary loader must retain fallback chunk
  resolution because Persistent Table metadata can reference audit chunks that
  exist only in StreamingAssets; a fallback-only pass should skip those absent
  shared chunks and continue with Persistent-owned chunks. The current overlay
  adds 639 CN AudioDialog definitions: 607 have real AudioChinese external
  media and 32 are zero-duration definition rows. After the patched CLI and
  CN relink pass, the index contains 29,072 AudioDialog definitions, 27,399
  playable entries, and 1,673 zero-duration/no-media rows. The 607 recovered
  files now use authored `voice/...` paths and retain `audioDialogPath`
  metadata; the old `wwise/unknown/<media-id>` placement is only a duplicate
  inventory artifact, not the canonical Story link.
- Timeline dialogue audio has two authored lanes. `DialogTrunkPlayableAsset`
  clips carry voice trunk ids and exact start/duration, while C35's separate
  Audio tracks carry 21 SFX placements (18 unique `_audioEventKey` values)
  through `AudioDlgEventPlayable`/`AudioEventPlayable` assets. Track and
  PlayableDirector PPtrs prove serialized ownership and scheduling, but they
  do not prove Director activation or a Wwise post. The semantic builder now
  scans both complete `StreamingAssets` and `Persistent` object-index parts
  and joins raw Timeline JSON for exact clip timing and playable controls.
  For `dlgtl_c35m1_10_sub_1_Audio`, the 21 rows are at authored Timeline
  positions and all 18 unique keys are absent from the current CN Wwise/Event
  and media indexes (`foundInWwise=false`, no playable media). The names give
  bounded authored meanings—create/fall/landing, shimmer/wink, flight/whoosh,
  grass footsteps, Liino fly/pat-head/surprise, NPC fear/shake, Endmin landing,
  and lens-zoom light—but do not prove that any sound was posted. The sole
  `isCue=1` row is `au_sfx_dlg_foley_c35m1_10_liino_pathead`; cue/Wwise
  resolution and runtime execution remain explicit gaps.
- C35 scene-10 now has an exact serialized root-to-audio activation chain.
  `Beyond.Gameplay.View.CutsceneRootComponent` on the root GameObject
  `dlgtl_c35m1_10_sub_1` stores `_timelineName` with that Story key and its
  `_director` PPtr lands on the root `PlayableDirector` (PathID
  `63140722070379897`, GameObject `Director`). That Director points to the
  root TimelineAsset `CAB-448d4024461b89053a057b4bf5604676` / PathID
  `-2466791841398753755`. Its `Audio` control track has a single
  `ControlPlayableAsset` clip at `0.0s` for `180.583333s`, with
  `autoBindingPath=Audio`, `updateDirector=1`, and `active=1`; the binding
  targets the child GameObject `Audio`, whose `PlayableDirector` (PathID
  `79300700487540089`) points to the separate Audio TimelineAsset
  `CAB-00d4a6807b79150b0a99039e79779b68` / PathID `6744480576528724800`.
  Therefore the 21 SFX placements are a child-Director lane fed by the Story
  root's ControlTrack, not a direct `_director` target. A second tiny-bundle
  Director points to the same Audio TimelineAsset but has no current indexed
  root receiver; it is retained as a duplicate carrier, not activation proof.
  This chain proves authored binding and scheduling composition only; it does
  not prove that `CutsceneRoot` called `Play`, that the ControlTrack updated
  the child Director, or that Wwise posted an event.
- The CLI defaults to lossless FLAC. It streams vgmstream-decoded PCM into the
  in-process CUETools FLAKE encoder and publishes the completed FLAC atomically,
  without an intermediate WAV file or `ffmpeg`. Explicit `--format wav` and
  `--format wem` remain compatibility modes. AnimeStudio uses a source-vendored
  FLAKE 1.0.1 fork whose writer supports every legal 1-655350 Hz FLAC sample
  rate; 6000 Hz Audit Wwise media is covered without resampling. Unusual source
  channel layouts still need a dedicated audit before being called fully
  certified.
- AKPK entry totals are not identical to ordinary playable-audio totals:
  current Main packages include Wwise `PLUG` plugin media alongside RIFF/RIFX
  WEM streams. The known entries are 48 kHz float PCM convolution-reverb/FX
  helpers referenced by HIRC Effect objects, not dialogue/music/SFX streams.
  The audio CLI reports them separately as plugin-media skips and prints the
  media id and header for any other unsupported entry instead of silently
  incrementing an error count. Preserve raw PLUG WEM or use vgmstream r2117+
  only when exhaustive FX-media recovery or diagnostic decoding is required.
- Persistent exposes two old `AuditAudio` PCK rows whose chunks are absent
  from both VFS roots and from the launcher's verified current file inventory,
  while the higher-version `Audio` block contains the active same-path Audit
  PCKs. The CLI reports this inactive duplicate-path source gap separately
  after processing the available paths. Do not copy/rename current chunks or
  edit the old catalog: its declared lengths and hashes differ. Exact old
  chunks are useful only in a separate matching historical-client snapshot.
- Projectile managed references use current IL2CPP field order plus guarded
  path-plus-id/id-only gameplay-tag variants. A projectile component is marked
  exact only when its full prefix, movement dictionary, effect lists, alert,
  sound tail, and final scalars consume the managed-reference boundary.

## Diagnostics

Check:

```text
reports/export/export_full_summary.md
reports/export/runs/
export_full/recovered/AnimeStudio-cli/animestudio_type_manifest.json
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/unresolved/failed_to_decode.txt
export_full/unresolved/manifest_reference_missing.txt
```

## Remaining gaps

- Per-asset-bundle clean/partial/error certification.
- More managed-reference and MonoBehaviour schemas.
- Broader exact shader-container and program metadata support.
- Additional converter regression fixtures across Unity variants.
- Lower peak memory for large broad JSON/export jobs.
- Clearer object-level diagnostics when dependencies or conversion fail.
- Reduce broad Story object-index peak memory and merge scratch size without
  weakening its full-object coverage or transactional summary marker. The
  current refresh peaked near 12 GB working set and used a roughly 7 GB merge
  database before publishing the compressed outputs.
