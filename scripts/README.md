# Scripts

Maintained scripts support the static WebUI, installed-data export, update
tracking, Story recovery, source graph, and Unity character lab. Prefer the
root wrappers for normal use.

## Root workflows

| Task | Command |
| --- | --- |
| First setup | `.\setup_first_time.bat` |
| Rebuild from current `export_full/` | `.\export.bat` |
| Refresh from installed game | `.\export.bat --export-from-game` |
| Refresh Story and assets | `.\export.bat --export-from-game --with-assets` |
| Story/Mission iteration | `.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference` |
| Mission data only | `.\export.bat --mission-pipeline-data-only` |
| Asset/audio maintenance | `.\export_assets.bat` |
| Build Updates feed | `.\build_updates.bat` |
| Apply installed-game patch | `.\build_updates_by_patch.bat` |
| Serve WebUI | `python serve.py` |
| Package WebUI | `python scripts\pack_webui.py` |

Root wrappers load defaults from `endfield_paths.bat`. Explicit path flags
override those defaults for one run.

## Export rules

- `export.bat` reuses and freshness-checks `export_full/` by default.
- Use `--export-from-game` only for an intentional installed-game refresh.
- Add `--with-assets` when asset indexes and CN audio must refresh too.
- Use `--full-source-graph` only for exhaustive Unity-object/PathID work.
- Use `--mission-pipeline-data-only` only when generated Story evidence is
  already current.
- Canonical `export.bat` runs refresh and validate the source Story gap queue
  after current partial-order and coverage reports are published, before
  Mission Pipeline recovery cards are projected. Data-only runs reuse it.
- Mission Pipeline builds also ensure the protocol registry audit matches the
  exact installed `GameAssembly.dll` and metadata hashes. Its state-update
  census discovers message shapes, typed handlers, runtime field offsets, and
  lifecycle argument flow generically; stale or missing reports are rebuilt.
- Mission Pipeline resolves exact native receiver playback gates generically
  through serialized `ActionHeader._validate` getter references. The resolver
  walks reusable AND/OR/NOT/ALL and comparison trees to exact leaves; unknown,
  missing, cyclic, and malformed children fail closed instead of receiving
  object-specific rules.
- Shipped-Lua Story playback is likewise corpus-driven: the Lua consumer audit
  enumerates typed `GameAction` calls, exact literals, and simple
  `Tables.<name>` row-field flows. A table field resolves only when the current
  original table has one possible non-empty value; mission/quest ownership is
  admitted only from the same resolved row. Mission Pipeline validates Lua and
  table hashes and admits no case-folded match without a matching
  installed-binary case-resolution audit. The cinematic-queue runtime audit
  structurally discovers the native base/handle/payload contract, mapped
  one-handle dispatchers, and enqueue edge; handle branches are one runtime
  family rather than unresolved authored Story references.
- Reuse Timeline/reference outputs only when their original inputs did not
  change.
- The direct Story builder can take several minutes; allow 10–15 minutes for
  multi-language or forced recovery runs.

## Main WebUI builders

```bat
python scripts\verify_export_freshness.py
python scripts\story_builder\refresh_evidence.py
python scripts\story_builder\source_links.py
python scripts\story_builder\build.py --languages CN --default-language CN
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay_data.py
python scripts\build_progression_data.py
python scripts\build_projectile_data.py
python scripts\build_combat_relationships.py --languages CN
python scripts\build_economy_data.py --languages CN --default-language CN
python scripts\build_world_data.py --languages CN --default-language CN
python scripts\build_presentation_data.py --languages CN
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\pack_webui.py
```

Story helpers live under `scripts/story_builder/`. Recovery audits live under
`scripts/story_recovery/` and are not all part of the canonical export.

Important Story components:

- `dialog_registry.py`: DialogIdTable registration.
- `video_bindings.py`: FMV/video definitions and attachments.
- `timeline_recovery.py`: Timeline evidence.
- `timeline_action_evidence.py`: typed action/control evidence.
- `mission_recovery.py`: mission and quest relationships.
- `build_source_story_gap_queue.py`: actionable source-only recovery queue.
- `story_recovery/build_levelscript_actionbase_tag_audit.py`: recovers the
  complete ActionBase MemoryPack formatter table from installed
  GameAssembly/metadata and refreshes the compact hash-pinned runtime name
  contract under `reports/mission_order/`.
- `story_recovery/build_callserver_callback_contract.py` and
  `build_callserver_callback_audit.py`: hash-pin the installed native
  `CallServer` possible-subexecutor contract, then recover every exact
  same-file callback-header control graph across the LevelScript corpus without
  mission, object, or Story allowlists.
- `story_recovery/build_cinematic_queue_runtime_audit.py`: repeatable installed
  metadata/GameAssembly audit that structurally discovers the cinematic handle,
  enqueue/producer call graph, and typed action-to-producer routes without
  per-object allowlists.
- `build_spaceship_story_content_audit.py`: exact typed spacecraft DialogTree
  and character profile-voice non-mission classification, refreshed by
  `refresh_evidence.py`.

## Updates

```bat
python scripts\build_updates.py
python scripts\build_updates.py --baseline-only
python scripts\build_updates.py --skip-asset-updates
python scripts\build_updates.py --skip-audio-updates
python scripts\build_updates.py --refresh-previous-export-baseline
```

Normal Updates scope includes exported Story/Text JSON, images, models, videos,
and decoded audio. Use `--full-export-scan` only for a broad audit. Never use
`webui/`, `reports/`, `memory/`, or `scratch/` as comparison roots.

## Assets and audio

`build_assets.py` creates the Assets tab indexes and compact Story-media lookup.
`build_audio.py` writes shared audio once under
`export_full/structured/Audio/shared/`, language voice under
`export_full/structured/Audio/<LANG>/`, and relinks playable conversation
audio.

Use `export_assets.bat --export-from-game` for installed-game image/model/
Material/CN-audio refresh. Asset modes, from narrowest to broadest, are
`--focused-assets`, `--default-assets`, and `--debug-assets`.

## Source graph

```bat
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
```

The default WebUI graph keeps only exact AssetMap source/PathID rows consumed
by material, shader, texture, and FMV edges. Full graph builds are for
investigation.

## Output locations

- `webui/data/`: generated browser payloads.
- `reports/export/`: export summaries, runs, and benchmarks.
- `reports/story/build/`: canonical Story build reports.
- `reports/story/recovery/`: recovery audits.
- `reports/mission_order/`: partial-order and gap reports.
- `reports/updates/`: Updates comparisons.
- `reports/assets/`: asset diagnostics.
- `reports/source_graph/`: SQLite graph and graph reports.

Put revisitable experiments in `scratch/<topic>/<task>/` and disposable work in
`tmp/<topic>/<run>/`. Do not add one-off scripts to `scripts/` unless they
become maintained WebUI or character-lab workflow code.

## Validation policy

During Story recovery, batch several independently validated edits before a
canonical rebuild. Prefer focused tests, direct probes, and
`--mission-pipeline-data-only` during iteration.

Validators must fail closed and report:

- validator and failed gate;
- affected mission or Story key;
- source path and relevant hashes;
- bounded expected versus actual values;
- deterministic failure details in structured data and CLI output.

Add tests for successful and representative failure cases when validator
behavior changes.
