# Scripts

Maintained scripts support the static WebUI, installed-data export, update
tracking, Story recovery, source graph, and Unity character lab. Use the root
wrappers for normal work; call Python builders directly for focused iteration.

## Root workflows

| Task | Command |
| --- | --- |
| First setup | `.\setup_first_time.bat` |
| Rebuild from current `export_full/` | `.\export.bat` |
| Refresh Story from the installed game | `.\export.bat --export-from-game` |
| Refresh Story and assets | `.\export.bat --export-from-game --with-assets` |
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
- Use `--export-from-game` only for an intentional installed-game refresh.
- Add `--with-assets` when image/model/material indexes and CN audio must also
  refresh. Combining both flags uses one AnimeStudio export.
- Use `--full-source-graph` only for exhaustive Unity-object/PathID work. The
  default graph retains only exact original AssetMap rows consumed by WebUI
  material, shader, texture, and FMV edges.
- Use `--mission-pipeline-data-only` only when generated Story bundles and
  evidence are current.
- Reuse Timeline order and localized reference outputs only when their source
  inputs did not change; reference reuse is rejected with `--export-from-game`.
- The default AnimeStudio type-job mode is `auto`: broad Story JSON families
  run sequentially in isolated processes while map-filtered asset conversion
  remains sharded. Reduce `--animestudio-jobs` when memory is constrained.
- Direct Story builds can take several minutes. Allow 10–15 minutes for
  multi-language or forced recovery runs.

During Story recovery, batch at least three independently validated edits or a
coherent 30–60 minute work session before a canonical Mission Pipeline build.
Prefer focused tests, direct probes, and data-only builds during the batch.

## Main WebUI builders

| Builder | Output or purpose |
| --- | --- |
| `verify_export_freshness.py` | Validate `export_full/` against installed data |
| `story_builder/refresh_evidence.py` | Refresh Story evidence inputs |
| `story_builder/source_links.py` | Rebuild original-source links |
| `story_builder/build.py` | Story, mission, and Text payloads |
| `build_character_data.py` | Characters identity catalog |
| `build_mission_pipeline_data.py` | Experimental mission/quest evidence view |
| `build_gameplay_data.py` | Gameplay base index |
| `build_gameplay_asset_refs.py` | Compact Gameplay-to-Assets sidecar |
| `build_projectile_data.py` | Exact projectile behavior payload |
| `build_combat_relationships.py` | Debug-only combat relationships |
| `build_economy_data.py` | Economy semantic data |
| `build_world_data.py` | World semantic data |
| `build_presentation_data.py` | Presentation semantic data |
| `build_assets.py` | Assets, Story media, and Gameplay asset indexes |
| `build_audio.py` | Lossless FLAC audio decode/relink and Gameplay SFX sidecar |
| `convert_audio_to_flac.py` | Standalone WAV-to-FLAC migration helper |
| `pack_webui.py` | Static package and optional media archives |

Typical focused commands:

```bat
python scripts\verify_export_freshness.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay_data.py
python scripts\build_gameplay_asset_refs.py --language CN
python scripts\build_projectile_data.py
python scripts\build_combat_relationships.py --languages CN
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\pack_webui.py
```

`build_projectile_data.py --require-exact` fails if an emitted projectile does
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
- `build_levelscript_actionbase_tag_audit.py`: hash-pinned native ActionBase
  names.
- `build_callserver_callback_contract.py` and
  `build_callserver_callback_audit.py`: exact local callback graphs.
- `build_cinematic_queue_runtime_audit.py`: native cinematic handle and
  producer routes.

For the maintained Bilibili Story-order intake:

```bat
python scripts\download_bilibili_video.py --season-url "https://space.bilibili.com/609095014/lists/7246850?type=season" --output-dir videos\bilibili_season_7246850
python scripts\story_recovery\run_bilibili_season_ocr.py --limit 1 --limit-frames 20
python scripts\story_recovery\run_bilibili_season_ocr.py
python scripts\story_recovery\build_gameplay_video_story_order.py --ocr-report-dir reports\gameplay_video_ocr\bilibili_season_7246850
```

The first OCR run is a smoke test. OCR writes a proposal under generated data;
it never edits `webui/overrides/story_order.json`.

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
and `data/assets/gameplay_refs.json`. Run `build_gameplay_asset_refs.py`
directly when Gameplay and the broad Assets index are already current.

`build_audio.py` writes shared SFX/music once under
`export_full/structured/Audio/shared/`, language voice under
`export_full/structured/Audio/<LANG>/`, relinks Story audio, and produces the
compact per-language Gameplay SFX sidecar. AnimeStudio still decodes Wwise
media to WAV internally; the builder converts the browser-facing files to
lossless FLAC and removes the temporary WAV after each successful conversion.
`ffmpeg` is required when conversion is needed. Pass `--audio-format wav` to
retain WAV, or `--format wem` to keep the legacy compact WEM output. Exact
Wwise event traversal can yield multiple media candidates; unresolved runtime
switch/random selection is preserved.

For a one-off migration of an existing export, preview first and then run:

```bat
python scripts\convert_audio_to_flac.py --audio-root export_full\structured\Audio --dry-run
python scripts\convert_audio_to_flac.py --audio-root export_full\structured\Audio --delete-source --jobs 4
python scripts\build_audio.py --skip-decode --audio-format flac --audio-conversion-jobs 4
```

Use `export_assets.bat --export-from-game` for installed-game image, model,
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
