# Scripts

Maintained scripts support the static WebUI, installed-data export, update
tracking, Story recovery, source graph, and Unity character lab. Use the root
wrappers for normal work; call Python builders directly for focused iteration.

## Root workflows

| Task | Command |
| --- | --- |
| First setup | `.\setup_first_time.bat` |
| Rebuild from current `export_full/` | `.\export.bat` |
| Refresh Story from the installed game | `.\export.bat --from-game` |
| Refresh Story and assets | `.\export.bat --from-game --with-assets` |
| Story/Mission recovery loop | `.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference` |
| Mission Pipeline data only | `.\export.bat --mission-pipeline-data-only` |
| Asset/audio maintenance | `.\export_assets.bat` |
| Build Updates feed | `.\build_updates.bat` |
| Apply installed-game patch | `.\build_updates_by_patch.bat` |
| Serve WebUI | `python serve.py` |
| Package WebUI | `python scripts\pack_webui.py` |

Root wrappers load repeated local defaults from `endfield_paths.bat`; explicit
path flags override them for one run.

## Export rules

- `export.bat` reuses and freshness-checks `export_full/` by default.
- Use `--from-game` only for an intentional installed-game refresh.
- Add `--with-assets` when image/model/material indexes and CN audio must also
  refresh. Combining both flags uses one AnimeStudio export.
- Use `--full-source-graph` only for exhaustive Unity-object/PathID work. The
  default graph retains only exact original AssetMap rows consumed by WebUI
  material, shader, texture, and FMV edges.
- Use `--mission-pipeline-data-only` only when generated Story bundles and
  evidence are current.
- Mission Pipeline external-result recovery is family/schema-driven: it derives
  the native enum/static-port contract from the installed binary and performs
  one complete targeted installed-VFS Lua dump to validate shared result
  defaults and producers. Do not add mission, panel, or object allowlists.
- Reuse Timeline order and localized reference outputs only when their source
  inputs did not change; reference reuse is rejected with `--from-game`.
- Post-Story semantic views run in dependency-safe parallel phases. Use
  `--webui-jobs N` to cap builder concurrency; the latest per-step timings live
  in `reports/export/webui_build_steps_latest.md/json`.
- The default AnimeStudio type-job mode is `auto`: broad Story JSON families
  run sequentially in isolated processes while map-filtered asset conversion
  remains sharded. Reduce `--asset-jobs N` (the wrapper name for
  `--animestudio-jobs`) when memory is constrained.
- `TextAsset` json loads through the generated asset map instead of every
  bundle: byte-identical output, 508s -> 27s. All other json types stay broad.
  Filtering is sound only for types that resolve nothing outside their own
  bundle; equal object counts are not evidence. `MonoBehaviour` has complete
  map coverage yet was rejected -- filtering renamed 128,181 of 174,133 files
  (lost MonoScript class names) and dropped 2,709 external PPtr targets.
  Diff the bytes both ways before adding a type;
  `--no-animestudio-json-map-filter` forces the broad path.
- Broad Story JSON is the export's long pole. Sharding it does not help and
  was rejected by measurement: on identical object sets `Convert` Texture2D
  scales 4.03x across 8 shards, while `JSON` Material runs 0.92-0.95x. Convert
  is CPU-bound decode (~37 ms/object); JSON export is ~3.55 ms/object and
  bound on single-disk small-file creation. Keep `convert_by_type` sharding;
  do not shard JSON. `--animestudio-broad-json-jobs N` bounds concurrent broad
  loads and defaults to 1; values above 1 have no supporting measurement.
- Direct Story builds can take several minutes. Allow 10–15 minutes for
  multi-language or forced recovery runs.

During Story recovery, batch at least three independently validated edits or a
coherent 30–60 minute work session before a canonical Mission Pipeline build.
Prefer focused tests, direct probes, and data-only builds during the batch.

## Main WebUI builders

| Builder | Output or purpose |
| --- | --- |
| `verify_export_freshness.py` | Validate `export_full/` against installed data |
| `build_webui_views.py` | Dependency-safe post-Story builder orchestration and timing report |
| `story_builder/refresh_evidence.py` | Refresh Story evidence inputs |
| `story_builder/source_links.py` | Rebuild original-source links |
| `story_builder/build.py` | Story, mission, and Text payloads |
| `build_character_data.py` | Characters identity catalog |
| `build_mission_pipeline_data.py` | Experimental mission/quest evidence view |
| `build_gameplay.py` | Every Gameplay page dataset: base index, projectiles, Assets sidecar, combat relationships. Stages live in `gameplay_builder/`. |
| `build_economy_data.py` | Legacy Economy semantic data; tab removed, not in `export.bat` |
| `build_world_data.py` | Legacy World semantic data; tab removed, not in `export.bat` |
| `build_presentation_data.py` | Legacy Presentation semantic data; tab removed, not in `export.bat` |
| `build_assets.py` | Assets, Story media, and Gameplay asset indexes |
| `build_audio.py` | Lossless FLAC audio decode/relink and Gameplay SFX sidecar |
| `build_audio_semantics.py` | Audio runtime/event/media semantic payloads |
| `convert_audio_to_flac.py` | Standalone WAV-to-FLAC migration helper |
| `pack_webui.py` | Static package plus FLAC-only audio/media archives |

`build_data_index.py` is a legacy local index helper, not an active WebUI
builder. Its combat decoders gate the current 47-member SkillData and 30-member
BuffData schemas and emit an explicit unsupported-member-count result on schema
drift. Current Buff/Skill post-id tails reach exact boundaries across the merged
export, including current member-17 stack effects, energy-shard nested blocks,
packed Buff tag ids, and member-1 Skill tag ids. Nested action/config semantics
that are not proven remain visibly partial. The resulting
`webui/data/game_data/` tree is a large diagnostic preview, not a runtime-formula
source; use the maintained Gameplay builders and binary-backed evidence for
active pages.

Typical focused commands:

```bat
python scripts\verify_export_freshness.py
python scripts\animestudio\generate_dummydll.py --dry-run
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay.py
python scripts\build_gameplay.py --stage projectiles --stage combat
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\pack_webui.py
```

`animestudio/generate_dummydll.py` is the maintained optional IL2CPP schema
regeneration path. Run `--dry-run` after an installed-game update; use
`--replace` only when the reported registrations validate and script-derived
MonoBehaviour recovery is needed. It stages and validates the complete set,
writes `tools/DummyDll/generation.json`, and retains the previous set as a
timestamped sibling.

`pack_webui.bat` and `pack_webui.py` include only the current decoded `.flac`
files in the standalone audio archive. Older `.wav` and `.wem` files are
ignored even if they remain beside an export.

`build_gameplay.py --stage projectiles` (via `gameplay_builder/projectiles.py`
`--require-exact`) fails if an emitted projectile does
not consume its validated managed-reference boundary. Missing playable-skill
ownership remains explicit; identifier similarity is not promoted to a runtime
spawn proof.

## Story recovery

Maintained Story components live in `scripts/story_builder/`; focused audits
live in `scripts/story_recovery/` and are not all part of `export.bat`.

High-value entry points:

- `dialog_registry.py`: DialogIdTable registration.
- `video_bindings.py`: narrative video definitions and attachments.
- `timeline_recovery.py` and `timeline_action_evidence.py`: Timeline order,
  action, and control evidence.
- `mission_recovery.py`: mission/quest relationships.
- `build_source_story_gap_queue.py`: source-only recovery queue.
- `dialog_tree_control_flow.py`: reusable installed-metadata/GameAssembly
  decoder for enum-selected static port maps and serialized multi-output
  control projection; it has no mission, Story, object, OCR, or override
  allowlist.
- `build_levelscript_actionbase_tag_audit.py`: hash-pinned native ActionBase
  names.
- `build_callserver_callback_contract.py` and
  `build_callserver_callback_audit.py`: exact local callback graphs.
- `build_cinematic_queue_runtime_audit.py`: native cinematic handle and
  producer routes.
- `build_native_value_carrier_audit.py`: type/field-driven installed-binary
  producer, consumer, nested-container, direct-callsite, and local-initializer
  census for any managed value carrier. Pass `--carrier-type` and repeat
  `--focus-field`; the code never takes mission, Story, object, OCR, or override
  identities.

For the maintained Bilibili Story-order intake:

```bat
python scripts\download_bilibili_video.py --season-url "https://space.bilibili.com/609095014/lists/7246850?type=season" --output-dir videos\bilibili_season_7246850
python scripts\story_recovery\run_bilibili_season_ocr.py --limit 1 --limit-frames 20
python scripts\story_recovery\run_bilibili_season_ocr.py
python scripts\story_recovery\build_gameplay_video_story_order.py --ocr-report-dir reports\gameplay_video_ocr\bilibili_season_7246850
python scripts\story_recovery\build_gameplay_video_ocr_override_disagreement.py --ocr webui\data\story_order_ocr.json --override webui\overrides\story_order.json --output-dir reports\gameplay_video_ocr\bilibili_season_7246850
```

The matcher writes `story_order_ocr_matches.json`, its Markdown summary, and
`story_order_ocr_proposed_story_order.json` beside the supplied OCR report
directory, while the WebUI reference remains `webui/data/story_order_ocr.json`.

If a Bilibili DASH representation is shorter than the page metadata, retry the
affected BVIDs with `--playback-mode durl`; the same duration/audio checks still
gate promotion to `.mp4`. The OCR runner marks its ffmpeg/Paddle child process
as no-console on Windows and does not open a second terminal window.

The first OCR run is a smoke test. OCR writes a proposal under generated data;
it never edits `webui/overrides/story_order.json`.
The disagreement helper compares the generated OCR candidate directly with
the manual override and writes a read-only JSON/Markdown review beside the
season OCR reports.

## Characters catalog

`build_character_data.py` combines `CharacterTable`, `NpcTable`,
`SNSChatTable`, `TextTable`, Story actors, and recognized exported-asset
filename families into `webui/data/lang/<LANG>/characters/index.json`.

Automatic groups use a stable canonical constituent id rather than localized
text. Two reviewed lists prevent filename false positives:

- `EXCLUDED_TOKENS`: exact captured non-character tokens.
- `EXCLUDED_FILENAME_FRAGMENTS`: non-character filename families.

Add exclusions only after tracing the exact source filenames. Rebuild the
catalog, then remove dead ids from character overrides.

`webui/overrides/character_merges.json` and
`character_name_overrides.json` are edited live by the Characters page through
`serve.py`. Merges are additive, cycles/self-merges are rejected, and the
`flagged` list records identities whose target is still unknown.

## Updates

```bat
python scripts\build_updates.py
python scripts\build_updates.py --baseline-only
python scripts\build_updates.py --skip-asset-updates
python scripts\build_updates.py --skip-audio-updates
python scripts\build_updates.py --refresh-previous-export-baseline
```

Normal scope includes exported Story/Text JSON, images, models, videos, and
decoded audio. Use `--full-export-scan` only for a broad audit. Never compare
`webui/`, `reports/`, `memory/`, or `scratch/` as game-data roots.

## Assets and audio

`build_assets.py` creates the Assets index, Story-media lookup, video index,
and `data/assets/gameplay_refs.json`. Run `build_gameplay.py --stage asset-refs`
directly when Gameplay and the broad Assets index are already current.

`build_audio.py` requests FLAC from AnimeStudio by default, writes shared SFX/music once under
`export_full/structured/Audio/shared/`, language voice under
`export_full/structured/Audio/<LANG>/`, relinks Story audio, and produces the
compact per-language Gameplay SFX sidecar. AnimeStudio streams decoded Wwise
PCM into its in-process encoder and writes lossless FLAC without an intermediate
WAV file or an `ffmpeg` dependency. Pass `--format wav` to
retain WAV, or `--format wem` to keep the legacy compact WEM output. Exact
Wwise v150 traversal follows typed Event/Action/container/Sound edges and can
yield multiple possible media leaves. Play roots, selector/layer relations,
partial traversal, and decoded-content equivalence remain separate; unresolved
runtime selection is never labeled as a set of equivalent choices.

`build_audio.py` also refreshes the Audio view. Run
`python scripts\build_audio_semantics.py --language CN` independently when the
authoritative audio index is already current and only its semantic payload or
frontend changed. The compact overview and Event data load on view activation;
the large decoded-media inventory loads only when its Media mode is selected.

For a one-off migration of an existing export, preview first and then run:

```bat
python scripts\convert_audio_to_flac.py --audio-root export_full\structured\Audio --dry-run
python scripts\convert_audio_to_flac.py --audio-root export_full\structured\Audio --delete-source --jobs 4
python scripts\build_audio.py --skip-decode --audio-format flac --audio-conversion-jobs 4
```

Use `export_assets.bat --from-game` for installed-game image, model,
Material, and CN-audio refresh. Asset modes are `--focused-assets`,
`--default-assets`, and `--debug-assets`.

## Source graph

```bat
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

Graph edges retain evidence provenance. Exact foreign keys, serialized PPtrs,
and typed native paths outrank normalized names and token similarity.

## Outputs and validation

- `webui/data/`: generated browser payloads.
- `reports/export/`: export summaries, run logs, and benchmarks.
- `reports/story/build/`: canonical Story build reports.
- `reports/story/recovery/`: focused recovery audits.
- `reports/mission_order/`: partial-order and gap reports.
- `reports/updates/`, `reports/assets/`, `reports/source_graph/`: topic outputs.

Put revisitable experiments in `scratch/<topic>/<task>/` and disposable work
in `tmp/<topic>/<run>/`.

Validators must fail closed and report the validator and gate, affected mission
or Story key, source path and hashes, bounded expected-versus-actual values,
and deterministic details in both structured data and CLI output. Add success
and representative failure tests whenever validator behavior changes.
