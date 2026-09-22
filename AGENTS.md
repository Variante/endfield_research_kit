Agent notes for this repo. User-facing usage belongs in `README.md`.

## Active Scope

Keep root-level docs and workflow guidance focused on:

- the static WebUI in `webui/`

Keep the active documentation hierarchy concise:

- `README.md` is the short user-facing entry point. Preserve its screenshot
  gallery, Chinese links, acknowledgements, quick start, common commands, and
  headline Story/character progress.
- `scripts/README.md` is a compact maintained command/script map, not an
  exhaustive implementation narrative.
- `webui/README.md` documents only frontend scope, data layout, and behavior
  contracts.
- `memory/webui_recovery.md` documents only the shared WebUI export/publication
  flow and cross-page contracts.
- `memory/webui/` contains one recovery guide per active page.
- `memory/game_data_recovery.md` is the game-data entry point: shared evidence
  rules and the detail index. `memory/game_data/` contains one file per
  installed-data evidence family.
- `memory/game_data/` contains one file per installed-data evidence lane,
  including the extraction pipeline and Unity object identity.

Fold durable observations, conclusions, and recovery status into the existing
topic documents under `memory/`. Do not recreate one-file-per-investigation or
dated status snapshots. Generated inventories belong in `reports/`, and
disposable evidence belongs in `scratch/` or `tmp/`.

### Tracked versus local-only paths

`.gitignore` keeps the generated and disposable surface out of version control.
Know which side a path is on before routing content to it:

| Path | State | Consequence for an agent |
| --- | --- | --- |
| `AGENTS.md`, `README.md`, `memory/`, `.codex/skills/` | tracked | the durable record; a conclusion survives only here |
| `scripts/`, `webui/` sources | tracked, except `scripts/tests/` | code, docs, and reviewed contracts |
| `scripts/tests/` | ignored, stays in place | the suite still runs locally; it is not part of the repo |
| `webui/overrides/*.json`, `scripts/**/*.json` | tracked | the correction layer and the reviewed data-structure contracts |
| every other `*.json` | ignored | generated data and run output, regenerated not committed |
| `reports/` | ignored | generated reports are local-only; writing one does not commit it |
| `webui/data/`, `export*/` | ignored | generated data, never reviewable output |
| `scratch/`, `tmp/`, `tools/` (except tracked helpers) | ignored | disposable; may vanish between sessions |
| `CLAUDE.md` | ignored symlink to `AGENTS.md` | edit `AGENTS.md`; the symlink needs no separate update |

Because `reports/` is not tracked, "move it to a report" removes a fact from
the repository. Route a changing count, inventory, or per-build hash to
`reports/`, but keep the durable interpretation, and any conclusion a later
session must not re-derive, in the owning `memory/` topic. Do not cite a
`reports/`, `scratch/`, or `tmp/` path as the sole evidence for a documented
conclusion.

### What gets tracked

One rule decides it: **track a file only if it is reusable and general enough to
explain the data.** Everything else stays local.

| Tracked | Not tracked |
| --- | --- |
| format readers, builders, codecs | whatever a tool run emits |
| the tools that sweep or audit a build | generated page data and exports |
| contracts documenting a data structure | tests, trials, probes, run output |
| docs, memory topics, skills, overrides | anything regenerated, not reviewed |

Three consequences worth stating outright:

- **A tool is reusable; its output is not.** A corpus gate, native validator,
  or audit script is tracked. Its report, ledger, or receipt is not, and belongs
  under `reports/`.
- **A contract that documents a data structure is tracked**, even though it
  pins one build. `scripts/**/*.json` records field layouts, read orders, and
  proved boundaries; the RVAs and hashes beside them are the provenance for
  those facts, not the point of the file. Keeping them in git is what makes a
  format conclusion reviewable and diffable, and what makes build drift visible
  -- the alternative leaves the conclusion on one machine. Tool *output* stays
  out regardless of format.
- **Tests and trials are not tracked.** `scripts/tests/` stays where it is and
  still runs, but it is local: see the Tests section.

A build-locked constant block inside a tracked `.py` is still the wrong shape.
A module whose body is mostly pinned hashes and addresses is a data file with a
`.py` extension; keep the algorithm in code and put the declarations in a
contract the module loads.

### Which JSON is tracked

`.gitignore` says nothing about `*.json`. JSON is governed by **where it
lives**, not by its extension: the generated roots are ignored as directories
(`reports/`, `webui/data/`, `export*`, `scratch`, `tmp`,
`scripts/tests/`), and JSON anywhere else is tracked. In practice that is the
reviewed contracts under `scripts/` and the correction layer in
`webui/overrides/`.

- The consequence of location-based rules: a JSON file written somewhere that
  is *not* an ignored root shows up as an ordinary untracked file, with no
  extension rule to catch it. So keep every generated artifact inside an
  ignored root -- a builder that starts writing JSON into `scripts/` or the
  repo root is the bug, not the `.gitignore`.
- A new manual correction layer belongs in `webui/overrides/`; a new reviewed
  contract belongs in `scripts/game_data/contracts/`.
  Anything a tool writes belongs in `reports/`.
- **Contract JSON is byte-pinned, so it must never be EOL-converted.** Readers
  hash the file's exact bytes and fail closed on a mismatch. 217 of these files
  are CRLF on disk and three are deliberately mixed, so `.gitattributes` marks
  `scripts/**/*.json -text`. Never change that to `eol=lf`: it would rewrite
  the bytes on checkout and break every pin with no other visible symptom.
- Prose still must not carry per-build addresses and hashes. They belong in the
  contract JSON, with the durable interpretation in the owning `memory/` topic.
- A contract pins one build. When the installed build differs its consumers
  correctly produce nothing, and tracking the contract makes that drift
  reviewable without making a stale row current. Check a contract's
  `nativeInputs` against the selected build before trusting its rows or
  reading a consumer's empty result as current.

### Audio recovery documentation boundary

Keep Audio documentation split by audience and do not repeat the same
build-specific catalog across files:

- `scripts/README.md` owns maintained Audio commands, module ownership, and
  builder/output contracts.
- `webui/README.md` owns only Audio page behavior, generated-data layout, and
  frontend evidence/filter contracts.
- `memory/game_data/audio_overview.md` owns durable Wwise conclusions, with the
  HIRC parser/graph/`0x0B`/bank-section files beside it; serialized-data and
  native-consumer conclusions stay in the other `memory/game_data/` files, and
  `memory/game_data_recovery.md` owns the shared evidence rules plus the
  highest-value recovery gaps.
- `memory/webui/audio.md` owns the current user-visible Audio recovery state and
  UI-facing evidence boundary; `memory/webui_recovery.md` owns only shared
  cross-page and export contracts.
- Per-build addresses, method tokens, hashes, mapping tables, and full
  inventories belong in a contract JSON or a generated report, not in
  `AGENTS.md`, active READMEs, or memory prose. Keep the durable interpretation
  in the owning memory topic either way, since a report is not tracked.
  Changing counts belong in reports; disposable before/after evidence belongs
  in `tmp/audio/<task>/`.

Audio code follows the same ownership boundary. `build_audio.py` owns decode,
Wwise indexing, relinking, and Gameplay sidecars;
`build_audio_semantics.py` owns orchestration and publication only; reusable
semantic domains live under `scripts/webui/audio/semantics/`. Add logic to its
domain owner instead of growing either entry point or importing the entry
point as a helper library. Native claims must use the explicit selected
`global-metadata.dat` plus `GameAssembly.dll` gate, fail closed on
missing/mismatched inputs, and never fall back to a module-global game root.
Do not add compatibility re-exports, duplicate native catalogs, broad
`ImportError` import fallbacks, or a second scan when one collected context
index can supply both names and hashes.

### Raw-format ownership in `scripts/game_data/`

`scripts/game_data/` is the first of the two script lines: it owns extraction
from the installed client and installed-format decoding below any page or
semantic view. It reads bytes and proves framing, and it does not publish
WebUI data. Its durable conclusions belong to the owning `memory/game_data/`
file under `memory/game_data_recovery.md`; its commands belong to
`scripts/README.md`. Modules are grouped by role:

- `extraction/` runs AnimeStudio and writes `export_full/`: the full and
  changed-file exporters, the freshness guard, the object index, and the
  `animestudio/` maintenance commands;
- exact framing readers, one per payload family: `streaming/framing.py`,
  `irradiance_volume.py`, `extend_data_binary.py`, `bundle_manifest.py`,
  `ifix_patch.py`, `inverted_lz4.py`, `terrain_tret.py`, `terrain_height.py`,
  `dynamic_streaming.py`, and the serialized-gameplay readers
  `levelscript_binary.py`, `leveldata_binary.py`, `ability_binary.py`,
  `interactive_binary.py`, `spawner_binary.py`,
  `char_interact_perform_binary.py` and `animation_config_binary.py`, with
  their per-record codecs under `codecs/`. Put a new reader in the package,
  never beside the page builder that first needs it;
- `*_native.py` loaders for the reviewed native facts that Story, Mission
  Pipeline, Map and the recovery tools consume, one per contract, each
  reaching its byte-pinned JSON in `contracts/`;
- `media_resolver.py`, game-media naming (inline image tags, env-emoji prefab
  layers, SNS and video naming) and asset-candidate resolution;
- `*_corpus.py` current-corpus gates, which sweep the installed set and fail
  closed on an `--input-set-sha256`/`--expected-input-set-sha256` mismatch. The
  AnimeStudio VFS audit is the only producer of that value
  (`EndfieldVfsAudit.cs`), and it is not a data-only fingerprint: it hashes the
  normalized absolute asset roots plus the path, length and SHA256 of
  `app.info`, `GameAssembly.dll`, `Endfield.exe`, `global-metadata.dat`, and
  the running `AnimeStudio.CLI` binary. Reinstalling the game elsewhere or
  rebuilding the exporter therefore changes it with the game data untouched, so
  a corpus gate can report a mismatch that is neither a client update nor a
  regression. Re-run the audit for a current value instead of hand-editing a
  recorded one;
- `*_native.py` native validators, which authenticate a reviewed contract
  against the selected build;
- `memorypack/` for serialized gameplay payloads, with `core.py`/`schemas.py`
  shared and one module per domain;
- `il2cpp_context.py` and `il2cpp_context_audit.py` for generic-instantiation
  pointer tables, and `il2cpp_protocol.py` for the shared IL2CPP and protobuf
  primitives that validators and page builders both read.

Keep a new family in its own reader plus its own corpus gate. Do not widen an
existing reader to a second framing, and do not let a corpus gate infer a
schema the reader has not proven.

The gate, validator, and audit scripts here are tracked because the sweep is
reusable, and so are the contracts under `contracts/`, because those record a
data structure. What a run emits is not: reports go to `reports/`. A script in
this package that cannot run against a future build without being rewritten
belongs in `scratch/`, not here.

### Native contracts are versioned data with pinned hashes

The `scripts/game_data/contracts/*_native.json` files are the versioned contracts that
the rules above mean when they route per-build addresses and hashes out of
prose. They are tracked, because what they record is a data structure; the
per-build anchors beside each field are its provenance. Two families, with
different shapes:

- **Named consumer contracts** carry a dotted `schema` token
  (`endfield.terrain-tret-native-contract.v1`), a `status`, a `nativeInputs`
  block pinning the `GameAssembly.dll`, `global-metadata.dat`, and
  `UnityPlayer.dll` SHA256s, and an `evidenceBoundary`. Their matching
  `*_native.py` module reads them.
- **MemoryPack formatter windows** (`buff_*`, `finder_*`, `validator_*`,
  `postprocessor_*`, `streaming_*`) carry `schemaVersion`, `methods` as
  `[metadata index, type name, method, RVA]`, and `codeWindows` with a
  per-window `sha256` and `boundary`. `memorypack/` and the audit read them.

A third set, the native facts the Story, Mission Pipeline and Map builders
consume, is loaded by the `*_native.py` modules beside the readers, each from
its JSON in `scripts/game_data/contracts/`. Every loader except
`mission_task_paths_native` gates on the installed native inputs itself. That contract is validated by its
consumers, the protocol registry and the mission trace hook manifest. Where a
loader declares a `CONTRACT_SHA256`, the same edit-requires-pin rule below
applies.

`evidenceBoundary` is the vocabulary to use when recording what a contract
proves, in both the JSON and any memory prose that cites it: `exact` for what
the pinned inputs establish byte-for-byte, `direct` for an observed consumer
read, `structuralOnly` for a stored representation whose meaning is anonymous,
`conditional` for a claim that holds only under a stated selection, and
`unresolved` for the named open join. Do not promote a row between tiers on a
name match, an address ordering, or a proximity argument.

Editing one of these JSON files is a code change:

- the reviewed contract's digest is pinned as `CONTRACT_SHA256` in its
  `*_native.py` module and re-checked at load, and the MemoryPack audit hashes
  its contracts the same way. A JSON edit without the matching pin update fails
  closed rather than silently taking effect;
- the pin covers the file's exact bytes, so never let a tool or editor rewrite
  its line endings; `.gitattributes` keeps git from doing so;
- change the `schema`/`schemaVersion` token when the shape changes, and update
  every reader in the same commit;
- never carry a registration index, RVA, or code-window hash over from a
  previous installed build; regenerate it against the selected build;

A contract whose pinned build differs from the installed one returns
`mismatched`, and its consumers correctly produce nothing. Check a contract's
recorded `nativeInputs` against the selected build before treating its rows,
or a consumer's empty result, as current.

## Commands

**The command surface lives in [`scripts/README.md`](scripts/README.md)** --
entry points, flags, and what each one writes. Every wrapper also prints
`--help`. Do not maintain a second option catalog here. What follows is only
what a reader of that file would still get wrong.

**Running them.**

- Export and rebuild commands are long-running. Give them a generous timeout
  and wait; do not poll or re-check while one is still running.
- `scripts/webui/story/build.py` takes about 3 minutes for the default CN
  lean build. Multi-language or forced timeline recovery takes longer -- allow
  10-15 minutes (`timeout_ms` of at least `900000`).
- Before starting a WebUI server, check whether the default
  `http://127.0.0.1:8765/` server is already running and reuse it. Do not start
  a second `serve.py` on `8765` or another port unless asked.
- The Python tooling stays stdlib-only unless a task explicitly requires
  otherwise.

**Choosing a wrapper.**

- Pass `--from-game` only when the user explicitly asks to refresh
  `export_full/` from the installed client. `export.bat` reads the existing
  export by default.
- Prefer `export.bat --from-game --with-assets` when Story and assets both need
  an installed-game refresh; it runs one AnimeStudio pass instead of two.
- For a focused Mission Pipeline edit loop use the direct Python sequences in
  `.codex/skills/endfield-mission-pipeline-build/SKILL.md`. The wrapper no
  longer owns a Mission Pipeline scope.

**Invariants a caller must not break.**

- `endfield_paths.bat` loads before argument parsing and supplies the
  `ENDFIELD_GAME_ROOT` / `ENDFIELD_PREVIOUS_EXPORT_ROOT` /
  `ENDFIELD_EXPORT_ROOT` defaults; explicit path flags still override it.
- Installed-game-only options are rejected with an explanation when
  `--from-game` is absent, never silently dropped.
- Asset-only extraction preserves the previous structured Story/Table source
  fingerprints and records its asset scan separately. It must never make
  untouched structured data appear fresh after a client update.
- Reject `--animestudio-object-index` in any scope that skips Story evidence,
  because such a scope cannot refresh its Story consumer report.
- `export.bat` does not refresh `webui/overrides/story_order.json`; active
  Story order is user-managed there, while OCR recovery writes proposals to
  `webui/data/story_order_ocr.json`.
- The Combat builder refuses graph edges when the database predates its
  Gameplay/manifest/asset/AbilityEntity/CharacterTemplate inputs, and records a
  visible degraded-mode reason rather than treating stale edges as direct.
- Batch wrappers are CRLF. `cmd.exe` mis-resolves backward `goto` in LF-only
  batch files, which breaks their argument loops.
- Story reference reuse belongs to the direct Story builder and must not be
  used after an installed-game refresh.


### Mission Recovery Edit-Loop Policy

Do not run a canonical Story/Mission Pipeline rebuild after every individual
recovery edit. Work in small validated batches:

- accumulate at least three independently validated recovery changes before
  running the direct Mission Pipeline Python sequence, or run it at the end of
  a coherent 30-60 minute recovery batch;
- during the batch, use focused unit tests and direct parser/builder probes;
- focused commits may be made after targeted validation; run the canonical
  rebuild once at the batch boundary before publishing generated WebUI data,
  documenting final counts, or declaring the batch complete;
- run an earlier canonical rebuild only when one cross-cutting parser/schema
  change cannot be validated safely with focused tests, installed-game inputs
  changed, generated Story/evidence is known stale, or the user explicitly
  requests it.

Treat generic validator failures as tooling gaps instead of repeatedly running
the expensive pipeline. Validators used by Story recovery must fail closed and
report actionable diagnostics:

- identify the validator, failed gate/check, affected mission or Story key, and
  source path;
- include bounded expected-versus-actual values and relevant source hashes;
- report at least the first failure deterministically, and preferably all
  independent bounded failures;
- expose the diagnostic in both structured report data and the CLI summary;
- add tests for the successful gate and for representative failure
  diagnostics whenever validator behavior changes.

Improve a validator's diagnostics before another full rebuild when its current
result is only a generic status such as `validation_failed`.

Steps that read the installed IL2CPP binaries gate on
`common.check_installed_native_inputs`, which resolves `GameAssembly.dll` and
`global-metadata.dat` from `ENDFIELD_GAME_ROOT`, then `endfield_paths.bat`,
then the export summary's `game_root`. Recorded native facts (method virtual
addresses, body hashes, field offsets) describe one specific client build, so
the gate reports `missing`, `mismatched`, or `validated`:

- an absent or different build skips only that step, with a one-line reason on
  stderr, and leaves its published report untouched; the rest of the pipeline
  is build-independent and still builds;
- a skipped step never emits unvalidated classifications, and each report's own
  source hashes still decide whether its recorded rows describe current data,
  so consumers stay fail-closed;
- set `ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1` to restore hard failure when
  auditing the pinned build.


## Tests

Tests live in `scripts/tests/` and use stdlib `unittest`, matching the
stdlib-only rule above. They are **not tracked**, and they are **not moved**:
the directory stays where it is so the suite keeps running locally, while
`.gitignore` keeps it out of the repo. Do not re-track it, and do not relocate
it to `scratch/` or `tmp/`.

They are the cheap validation path the recovery edit-loop policy and the
validator-diagnostics rule both depend on, so run them instead of a pipeline
rebuild whenever a focused test can decide the question. Being untracked does
not make them disposable: keep them working, and delete a test only when the
code it covers is gone.

Run them by module path from the repository root:

```bat
python -m unittest scripts.tests.test_build_assets
python -m unittest scripts.tests.test_build_audio scripts.tests.test_build_updates
```

`scripts/tests/` has no `__init__.py`, so `python -m unittest discover` cannot
reach it and reports `NO TESTS RAN` or an unimportable start directory.
Name the modules explicitly; do not add `__init__.py` or a runner config to
make discovery work without also checking every `scripts.*` import path it
would newly shadow.

Fixture and helper subdirectories (`animestudio_story_objects`, `ocr`,
`runtime_trace`, `runtime_trace_tests`, `story_gap`) belong to their owning test
modules. Add a new test beside the module it covers, named
`test_<module-or-contract>.py`, and keep fixtures bounded and in-repo rather
than reading installed game data or a generated export root.

Never let a test assert that one installed build is the valid one. A test that
expects `validated` from a real gate passes only on the machine that recorded
the contract and fails everywhere else, which is a build fingerprint committed
as an expectation. Instead, patch the consumer's own
`check_installed_native_inputs` reference to return a stub status, then assert
the fail-closed behavior. Cover `mismatched` and `missing`, not only
`validated`, so build drift is proven to empty the result and record the gate
in the audit rather than silently keeping stale rows.

```python
mismatched = SimpleNamespace(status="mismatched", detail="GameAssembly.dll hash differs")
with mock.patch.object(module, "check_installed_native_inputs", return_value=mismatched):
    names, audit = module.load_actionbase_formatter_names()
```

This is why a validator's diagnostics can be improved and verified without a
pipeline rebuild, as the edit-loop policy above requires.

## WebUI Technical Notes

Keep detailed browser/export mechanics here, in project skills, or in code
comments. Keep `scripts/README.md` as a compact maintained workflow map and the
root `README.md` short and user-facing.

Browser behavior:

- Story/Text Tables inline media treats `sns_emoji_*` as regular inline emoji
  with no popup/modal preview.
- Non-emoji SNS media such as `sns_image_*` and `sns_sticker_*` render at
  normal image proportions with bounded hover/modal previews.
- Story recovery issue and method filters stay visible in every mode.
  Source/debug blocks, mission timeline evidence, cutscene debug panels, and
  manual order-edit controls are behind `Show debug info`.
- The Story reset button returns filters to Story sort while preserving
  expanded mission groups.
- Normal semantic navigation exposes Gameplay and Characters. Mission Pipeline
  recovery is standalone and is no longer a WebUI page or export stage. The
  standalone Combat & Projectiles page is retired. Keep useful projectile
  behavior in Gameplay character skills. Do not attach audio or sound players
  to Gameplay until its ownership model is better understood; keep that
  investigation on the Audio page.
- Mission Pipeline Story cards show evidence-typed trigger chains. Preserve an
  explicit ownership gap for unlinked native playback, keep definition-only
  rows distinct, and never infer mission order from native registration or code
  address order.

Export freshness:

- `export.bat` runs `scripts/game_data/extraction/verify_export_freshness.py` before rebuilding
  from an existing `export_full/`.
- Run `python -m scripts.game_data.extraction.verify_export_freshness` directly when checking the
  guard, and pass `--game-root "...\Endfield_Data"` for non-default installs.
- If freshness reports stale source roots, rerun
  `.\export.bat --from-game` before Story or asset builders read
  `export_full/`.

Setup and export internals:

- The expected AnimeStudio CLI path is
  `tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`.
- The AnimeStudio CLI provides the WebUI VFS commands `dump`, `audio`, `stream`,
  `vfs-index`, and `list`; `dump`, `audio`, `stream`, and `vfs-index` help should include
  `--fallback-assets <FALLBACK_ASSETS>`. `dump`, `stream`, and `vfs-index` accept repeated
  `--block-type` flags plus repeated `--file-regex` filters; `stream` exposes the
  same targeted VFS filtering for JSONL byte streaming.
- **`--for story|map|pages|everything` is the one knob most callers should
  use.** It sets the structured and asset scopes together from an intent, fills
  only what the caller left unset, and is overridden by an explicit
  `--structured-dump-mode` or `--*-assets` in either argument order.
  `--show-scope` prints the resolved scopes and exits without exporting.
  `story` -> focused/no assets, `map` -> default/no assets, `pages` ->
  default/default, `everything` -> full/debug. The presets are intents, not a
  derivation from a page list: the page-to-input mapping cross-cuts (Map wants
  Terrain and no bundles, Assets wants bundles and no Terrain), so a single
  linear level would force over-export and a page-to-input table would have to
  track every builder's inputs.
- `--structured-dump-mode` has three levels and each contains the one below.
  **`focused`** is the default and dumps what the WebUI pages consume:
  `table`, `json-data`, video and `lua`. **`default`** adds the Terrain height
  grids map recovery reads, about 64 MiB of Terrain's 1.19 GB. **`full`** adds
  Terrain whole, `streaming`, `dynamic-streaming`, `iv`, `extend-data`,
  `i-fix-patch` and the bundle manifest -- roughly 6.4 GB more, and only
  recovery work reads it. A local test pins the ladder and pins that
  `export.bat` accepts exactly the modes Python defines.
  Lua is in the narrowest level deliberately: it is ~16 MB decoded and the
  Mission Pipeline already consumes the index built from it, so excluding it
  only forced a separate hand-run extraction. The exporter decodes the
  base64+XXTEA wrapper and writes `game/Lua/<name>.lua`.
  Raw asset bundles and audio PCK/media are a **separate axis** -- the
  `--*-assets` scopes and `export_assets.bat` -- and no structured level
  carries them. `build_audio.py` streams Wwise bank metadata directly from VFS
  when relinking audio events. Raw containers are still never dumped; probe
  them with a bounded `AnimeStudio.CLI dump` into `tmp/`.
- `export_assets.bat --from-game` (that is, `export.bat --assets-only
  --from-game`) passes `--skip-structured`, writes a
  lightweight VFS metadata index, runs WebUI-facing image/model/Material
  export, and decodes CN audio before relinking.
- `export.bat --from-game --with-assets` keeps the structured Story
  refresh and folds the asset export into the same AnimeStudio run.
- `tools\DummyDll` is the preferred repo-local IL2CPP DummyDll root when
  optional script-schema recovery is wanted. Wrapper flags or
  `ANIMESTUDIO_DUMMY_DLLS` can supply it, but missing or stale DummyDll paths
  must warn and continue without failing normal exports.
- `scripts\game_data\extraction\animestudio\generate_dummydll.py` is the maintained regeneration
  path. Run `--dry-run` first after a game update, then `--replace` only when
  script-derived schema recovery is needed. It discovers build-specific
  registrations, clones and verifies the pinned
  `Variante/Cpp2IL-Endfield` release, validates a staged complete DLL image
  set, retains the previous set, and writes
  `tools\DummyDll\generation.json`. Never reuse registration addresses from a
  previous installed build. Maintain Endfield Cpp2IL source changes in
  `https://github.com/Variante/Cpp2IL-Endfield` on the
  `endfield/2022.0.7` line, publish an immutable `endfield-2022.0.7-vN` tag,
  then update the generator's tag and commit pin; do not recreate a local patch.
- `--animestudio-mono-behaviour-type-tree-priority script-first` is for
  targeted MonoBehaviour schema experiments; the default is `serialized-first`.
  Script-first must fall back cleanly when no usable DummyDlls are available.
- After installed-game refreshes, check `reports/export/export_full_summary.md` for
  stage return codes and AnimeStudio export errors.

Browser data inputs and outputs:

- Active inputs are the export root's `game/` tree (layout v2, see
  `memory/game_data/extraction_pipeline.md`): `game/Table`, `game/Json`,
  `game/Video`, `game/Audio`, and decoded Unity objects under
  `game/Unity/<Type>/`, plus generated data under `webui/data/`. Builder
  evidence and comparison inputs go to `webui/data/_build/`, which is neither
  served nor packaged.
- Generated browser outputs include `webui/data/manifest.json`,
  `webui/data/lang/<code>/index.json`, `conv/*.json`, `mission/*.json`,
  `reference/**`, `webui/data/gameplay/projectiles.json`,
  `webui/data/lang/<code>/gameplay/projectile_audio.json`,
  `webui/data/lang/<code>/gameplay/sound_effects.json`,
  `webui/data/lang/<code>/characters/index.json`,
  `webui/data/lang/<code>/gameplay/combat_relationships.json`,
  `webui/data/assets/index.json`, `webui/data/assets/gameplay_refs.json`, and
  `webui/data/updates/latest.json`.
- The current `export.bat` skips raw VFS output and source inventory because
  the browser does not need them.

Tool pointers:

- `tools/AnimeStudio/` is the tracked AnimeStudio fork submodule used by
  installed-game Story and asset export paths. During audio or visual recovery,
  agents may patch this fork and its wrapper integration when doing so improves
  extraction quality, evidence coverage, or reproducibility. Keep changes
  narrowly scoped, validate them with the AnimeStudio workflow, and preserve
  existing fail-closed source/build gates.
- `tools/endfield_source_graph.py` builds/query local SQLite evidence across
  generated WebUI story/text-table data, selected tables, audio, videos,
  assets, material links, and optional AnimeStudio asset maps.
- `tools/endfield-il2cpp/` contains offline IL2CPP metadata diagnostics. It is
  not part of normal export, Updates, packaging, or serving flows.
- `tools/Endfield-map-extractor/` is an optional ignored research checkout,
  not a maintained WebUI dependency. Its BundleScanner/SceneProbe pipeline is
  a useful reference for recovering scene hierarchy, transforms, and the
  renderer-to-mesh/material/texture closure, but the current public workflow is
  specialized to Map01/Map02 and does not establish an `indie_dg002` or e0m0
  render. Review its PolyForm Noncommercial license before reusing code. Its
  game-root convention also names the directory containing `Endfield.exe`, not
  this repository's usual `Endfield_Data` value.
- Optional local vendor/tool caches may live under ignored `tools/`; keep their
  generated outputs local.

Script notes:

- `scripts/README.md` lists the maintained script map and workflow contracts.
- New one-off exploration scripts should start in `scratch/` or `tmp/`.
- Durable conclusions belong in the matching consolidated `memory/` topic;
  reusable helpers should move into maintained workflow code only with
  matching docs and intentional tracking.

## Memory Maintenance Rule

`memory/` is limited to the ownership topics indexed by `memory/README.md`,
and it is organised on two axes, each an entry point plus a folder:
`memory/webui_recovery.md` + `memory/webui/` own how original game data
reaches the WebUI; `memory/game_data_recovery.md` + `memory/game_data/` own
how the original binary is understood. `memory/webui/` holds one guide per
active page plus shared Story reconstruction; `memory/game_data/` holds one
file per installed-data lane.
Treat these documents as living sources of truth:

- update the current conclusion, evidence boundary, essential commands, and
  recovery queue in the owning topic;
- keep each top-level recovery topic concise enough to scan as a maintenance
  contract. Aim for roughly 250 lines or fewer; when a topic grows beyond that,
  remove report-like detail or split only along a genuinely independent
  ownership boundary;
- treat that target as a budget to spend on conclusions, not a cap that
  authorizes deletion. `reports/` is not tracked, so moving a fact there and
  trimming the topic removes it from the repository. A topic over budget is
  reduced by replacing superseded readings, collapsing a proof into its result,
  and moving a per-build catalog into a `scripts/` code contract -- not by
  dropping a conclusion that has no other tracked home;
- replace superseded conclusions instead of appending investigation chronology,
  native-address catalogs, hash inventories, per-session proof logs, long
  object lists, or case-by-case current-corpus narration. A correction replaces
  the claim it corrects; do not leave both and let a reader guess which holds;
- keep changing counts, exhaustive inventories, and generated audits in
  `reports/`, with the durable interpretation and any figure a later session
  must not re-derive kept in memory, since the report itself is local-only;
- keep disposable probes and intermediate output in `scratch/` or `tmp/`;
- add a new top-level memory file only for a genuinely new durable topic;
- add or remove a `memory/webui/` guide only with the corresponding active page,
  and update `memory/README.md`, `memory/webui/README.md`, this guidance list,
  and relevant active docs together;
- keep `memory/game_data_recovery.md` itself at the entry-point size: the
  refresh and evidence rules, the installed-data model, the shared
  asset/spatial and source-graph contracts, the detail index, and the
  topic-wide remaining gaps. Per-family evidence goes in the owning
  `memory/game_data/` file, whose own budget is the same 250-line target spent
  on conclusions. Add a file there only for a genuinely separate family, and
  update `memory/README.md`, `memory/game_data/README.md`, and the parent
  file's index together.

Every `memory/webui/<page>.md` guide follows the same compact structure:

1. purpose;
2. inputs and recovery flow;
3. primary generated outputs;
4. evidence boundary;
5. focused refresh commands;
6. highest-value remaining gaps.

Do not put general frontend behavior, a complete script option catalog,
per-build counts, or long implementation narratives in a page guide. Link to
`webui/README.md`, `scripts/README.md`, the owning recovery topic, project
skill, or generated report instead. A page guide describes how evidence reaches
that page; it does not become a second source of truth for the underlying
Story, game-data, asset, or exporter semantics.

`memory/` is organised on two axes. `memory/webui_recovery.md` plus
`memory/webui/` own how original game data reaches the WebUI -- export flow,
page contracts, and Story reconstruction. `memory/game_data_recovery.md` plus
`memory/game_data/` own how the original binary is understood -- raw formats,
containers, native gates, Unity object identity, extraction, and per-lane
semantics. WebUI page contracts are owned by their page guides; cross-page
export and frontend rules remain in `memory/webui_recovery.md`.
Cross-topic improvement plans should be split into the recovery queues of those
owning files rather than maintained as a second status source.

### Documentation change routing

Update only the layers affected by a durable contract change:

| Changed contract | Required documentation owner |
| --- | --- |
| User-facing quick start or headline capability | `README.md` |
| Script command, module ownership, builder input/output | `scripts/README.md` |
| Frontend routing, controls, layout, generated-data schema consumption | `webui/README.md` |
| Shared export phases, wrapper selection, cross-page publication | `memory/webui_recovery.md` |
| One page's inputs, recovery flow, outputs, evidence boundary, or gaps | matching `memory/webui/<page>.md` |
| Story reconstruction truth conditions shared across consumers | `memory/webui/story_recovery.md` |
| Shared game-data evidence rules, installed-data model, overlays, source graph | `memory/game_data_recovery.md` |
| One installed-data family: raw format, native gate, gameplay or audio semantics | matching `memory/game_data/<family>.md` |
| Unity object identity and cross-domain asset/entity bindings | `memory/game_data/unity_assets.md` |
| AnimeStudio extraction, scheduling, DummyDll, provenance states, exporter diagnostics | `memory/game_data/extraction_pipeline.md` |
| How far one family's reader is proven | `memory/game_data/extraction_payload_boundaries.md` |

Do not touch every document after every code change. Update a memory topic only
when a durable conclusion, boundary, workflow, or recovery queue changed. A
changing count or one successful/failed run updates its generated report, not
memory prose. If a change crosses layers, update each actual owner and use links
instead of copying the same explanation.

Before deleting or merging a recovery topic, verify that its evidence and
workflow cannot exist independently of the proposed destination, search all
code/docs/skills for consumers, and update `memory/README.md` plus every
reference in the same change. The current six top-level recovery topics are
intentional; WebUI page splitting alone is not a reason to remove them.

## Current Guidance Locations

The former exploration archive has been consolidated. Do not recreate duplicate
README-shaped or dated snapshots; update the current source of truth instead:

- user-facing active workflow: `README.md`
- agent-facing repo rules: `AGENTS.md`
- script/workflow contract: `scripts/README.md`
- WebUI frontend scope: `webui/README.md`
- memory topic index and writing rules: `memory/README.md`
- WebUI export and shared recovery contract: `memory/webui_recovery.md`
- per-page WebUI recovery flows: `memory/webui/README.md`
- Story reconstruction conclusions: `memory/webui/story_recovery.md`
- game-data evidence rules and source graph: `memory/game_data_recovery.md`
- per-family installed-data evidence: `memory/game_data/README.md`
- Unity object identity and asset bindings: `memory/game_data/unity_assets.md`
- AnimeStudio exporter recovery: `memory/game_data/extraction_pipeline.md`

## Project Local Skills

Project-only skills live under `.codex/skills/`. They are registered for Codex;
any other agent reads the matching `SKILL.md` directly instead of invoking it.
`.claude/` holds settings only, so do not expect a project skill to appear in a
Claude Code skill listing, and do not duplicate one into `.claude/skills/` to
make it appear there. Either way the `SKILL.md` is the contract: open it before
acting.

- `.codex/skills/endfield-webui-frontend/`: frontend behavior, routing, labels,
  styles, and page contracts.
- `.codex/skills/endfield-webui-serve-package/`: serving, smoke tests, and
  static packaging.
- `.codex/skills/endfield-story-recovery-build/`: Story/Text Tables and Story
  evidence builders.
- `.codex/skills/endfield-mission-pipeline-build/`: Mission Pipeline and map
  recovery Python builders.
- `.codex/skills/endfield-assets-audio-build/`: asset indexes, audio links, and
  gameplay sound sidecars.
- `.codex/skills/endfield-updates-build/`: Updates comparison feed.
- `.codex/skills/endfield-source-graph/`: source graph build/query and
  graph-backed follow-up reports.
- `.codex/skills/endfield-option-overrides/`: editing and validating
  WebUI-only manual option recovery overrides in
  `webui/overrides/options.json`.
- `.codex/skills/animestudio-workflow/`: building, running, patching, and
  debugging the local `tools/AnimeStudio` exporter and its WebUI wrappers.
- `.codex/skills/map-interactive-legend/`: regenerating and reviewing the
  offline map `detailId` legend under `reports/map_recovery/`.

`tools/EndfieldCapture/README.md` is the local usage guide for the optional
native observer. No WebUI, export, or recovery workflow requires
EndfieldCapture. When an investigation chooses to use it, the local environment
needs Windows x64, Visual Studio 2022 C++ build tools, CMake 3.23+, and an exact
installed Endfield build selected by `ENDFIELD_GAME_ROOT` or
`ENDFIELD_GAME_EXE`. Build and test it from the submodule with:

```bat
cmake -S tools\EndfieldCapture -B tools\EndfieldCapture\build-local -G "Visual Studio 17 2022" -A x64 -DBUILD_TESTING=ON
cmake --build tools\EndfieldCapture\build-local --config Release --parallel
ctest --test-dir tools\EndfieldCapture\build-local -C Release --output-on-failure
```

Use `tools\EndfieldCapture\StartCapture.bat` only with Endfield closed and
follow its exact-build, prelaunch, one-attachment, bounded-session, and
collection gates. It is observation-only: do not use it for shader/resource
overrides, draw suppression, input hooks, or game modification. Treat missing
modules, hash mismatches, hook errors, lost events, and incomplete provider
summaries as failed evidence. Keep raw sessions under
`scratch/reverse_engineering/endfield_capture/` and publish only compact,
validated findings under the owning report or memory topic.
During audio or visual recovery, agents may patch EndfieldCapture itself to
improve observation coverage, event fidelity, diagnostics, or collection
reproducibility, provided it remains observation-only and the exact-build,
bounded-session, failure-reporting, build, and test gates above remain intact.

The current checkout does not ship a separate `endfield-story-recovery`
skill folder. For that workflow, use the active docs (`README.md`,
`scripts/README.md`, and `webui/README.md`) plus the existing source-graph
skill when graph evidence is relevant.

The retired exploration snapshots were collapsed because they mixed active
workflow guidance with stale conclusions and repeated generated-report status.
Keep generated reports in `reports/`, concise durable conclusions in the six
top-level recovery topics, page publication contracts in `memory/webui/`, and
disposable experiments in `scratch/` or `tmp/`.

## Update Tracking Rule

The WebUI Updates tab must report only exported game-data changes between a
saved previous export and the current export. By default it tracks the
exported JSON roots that feed Story/Text Tables display plus exported
image/model/video assets plus decoded audio. Use `--full-export-scan` only for
a broad audit of all files under the two export roots.

`build_updates.bat` reads the saved previous export and current export roots
from `endfield_paths.bat`
(`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT`). The underlying
`scripts/webui/updates/build_updates.py` defaults to comparing:

```text
export_full_1d4d1
export_full
```

when no wrapper config or explicit flags are supplied. The direct
two-extraction command that also generates the WebUI page is:

```bat
.\build_updates.bat OLD NEW
```

`OLD` is the saved extracted version and `NEW` is the current extracted
version; the pair must be the first arguments, and the wrapper adds
`--refresh-previous-export-baseline` for them. The long
`--previous-export-root PATH`/`--export-root PATH` flags remain available and
may override one side only. With no folder arguments, the wrapper uses its
configured defaults. Both complete export folders are required;
there is no first-time or installed-VFS tracking mode.
Scanner cache and feed history live under `.game-data-tracker/`; the cached
baseline is built from the previous export folder, then the current export root
is scanned against it using the same focused roots. Do not point this
comparison at `webui/`, `reports/`, `memory/`, or `scratch/`. WebUI edits and
generated output outside the export roots must not appear as game-data updates.

The builder scans exported assets in the same two export folders by default to
add image/model/video/audio asset-level entries to the Updates page. Asset
modifications use fast size fingerprints by default; pass `--exact` only when
same-size binary modifications must be detected. Use `--no-audio` when decoded
audio entries should be omitted while image/model/video entries remain
enabled. Use `--text-only` only when all asset entries should be omitted.
Use `--dry-run-prune-previous-export-untracked` to preview previous-export
files that exist byte-identically at the same relative paths in the current
export, and `--prune-previous-export-untracked` only when intentionally
deleting those old duplicate copies from the previous export folder. This
pruning must never target `export_full/` or the repo root. Through the wrapper
these are `build_updates.bat --prune-old --dry-run` and
`build_updates.bat --prune-old`.

Use `--refresh-previous-export-baseline` after replacing the saved previous
export folder so the cached scanner baseline is rebuilt.

## Repo Rules

- Prefer the layout rooted at `serve.py`, `export.bat`, `webui/`, and
  `scripts/`.
- Keep `README.md` focused on active WebUI usage and headline recovery
  progress. Preserve its screenshots, Chinese links, and acknowledgements.
- Keep active READMEs and memory topics concise. Put exhaustive implementation
  mechanics in code comments or focused generated reports, not long narrative
  appendices.
- Fold durable observations and conclusions into the matching consolidated
  `memory/` topic; do not add per-session or dated status files.
- Keep `reports/` for durable generated reports only, not agent conclusions or
  narrative writeups.
- Keep routine reports grouped by topic: exporter summaries, run logs, and
  benchmarks under `reports/export/`; Story build summaries under
  `reports/story/build/`; manual Story recovery evidence under
  `reports/story/recovery/`; update summaries under `reports/updates/`; and
  asset diagnostics under `reports/assets/`. Do not add loose report files at
  the `reports/` root.
- Keep the roots of `scratch/` and `tmp/` free of loose files and one-off run
  directories. Write experiments as `scratch/<topic>/<task>/` and disposable
  intermediates as `tmp/<topic>/<task-or-run>/`. Prefer the active topic names
  `webui`, `story`, `assets`, `animestudio`, `source_graph`,
  `character_recovery`, `game_data`, `updates`, `ocr`, and
  `reverse_engineering`; use `tests`, `tools`, or `misc` only when needed.
- Use `scratch/` for attempts, tool prototypes, and generated previews that may
  be revisited. Promote reusable helpers to maintained code or delete stale
  experiments.
- Use `tmp/` for disposable results and intermediates. Remove completed run
  directories after validation, and never cite `tmp/` as durable evidence.
- A self-contained reconstruction package ships its own guide and provenance
  sidecar instead of publishing into `webui/data/`. Its output root is ignored,
  so keep the durable conclusion in the owning memory topic and treat the
  package itself as regenerable output. Add a new package only when its output
  genuinely does not belong to an active WebUI page.
- For self-contained `ue5_*` or `unity_*` projects, prefer that project's own
  scratch/temp area instead of the repo-root work directories.
- Put durable shared helper code under the maintained script/tool surface.
  `tools/` is ignored by default except for already tracked helper scripts, so
  new promoted tools need intentional tracking and documentation.
- Local vendor/tool caches may live under ignored `tools/`. `tools/Ruri.ShaderDecompiler`
  is historical migration evidence only; do not pull it, build it, or add new
  AnimeStudio dependencies on it. Preserve it locally until the AnimeStudio
  shader-recovery fixtures and downstream verifiers certify the replacement.
- Keep `ue5_*` and `unity_*` directories self-contained. Code, assets, generated
  files, and helpers related to those projects should live inside the matching
  project folder.
- Do not commit a module whose body is mostly build-locked constants. Keep the
  algorithm in code and move its pinned hashes, addresses, and mapping ids into
  a contract the module loads, so a client update changes a declaration file
  rather than reviewed code.
- Preserve narrow, surgical changes when adjusting exporters or builders.
- Do not promote an ad-hoc script into `scripts/` unless it supports the
  WebUI.

## Active Script Groups

**The path-to-owner map is in [`scripts/README.md`](scripts/README.md)** under
`## Layout`. It has two lines that mirror the memory axes: `scripts/game_data/`
(extraction and installed formats) and `scripts/webui/` (Story reconstruction,
one folder per page, orchestration, and packaging), plus shared helpers and
tests. Do not keep a second copy here. The ownership rules that are not visible
from that layout:

- Place new code by axis. If it reads the installed client or proves a format,
  it goes under `scripts/game_data/`. If it projects exported data onto a page,
  it goes in that page's `scripts/webui/<page>/` folder. Line 1 must not write
  under `webui/data/`.
- Dependencies point one way: `common.py`, `source_paths.py` and
  `repo_paths.py` import neither line, `scripts/game_data/` imports only
  those, and `scripts/webui/` imports both. Import rather than copy. A page
  builder calls the `game_data` reader or contract. A helper both lines need
  goes into `common.py` under a name that states its behaviour
  (`sha256_file_upper`, `write_canonical_json`). Do not paste a private
  copy. When an existing helper differs even slightly (casing, key order,
  change detection), add a separately named one, because swapping it in would
  change output bytes. The only line-1 read of line-2 output is data: focused
  asset export reads published `webui/data` media references to scope its
  Texture2D filter. The local `scripts/tests/test_scripts_layout_boundaries.py`
  checks the direction statically and at import time.
- Run every entry point as `python -m scripts.…` from the repository root,
  both in wrappers and in docs. Import with absolute `from scripts.… import`.
  Resolve the repo root through `scripts.repo_paths.REPO_ROOT`, never
  `Path(__file__).parents[N]`. Do not reintroduce `__package__`-dependent
  import branches or `sys.path` bootstraps: they encode a file's location, and
  a move breaks them silently. A documented entry point guards direct file
  execution with a `SystemExit` naming its `-m` command.
- `scripts/webui/gameplay/build_gameplay.py` owns every Gameplay page dataset. Its stage modules
  sit beside it in `scripts/webui/gameplay/`, and its `asset-refs` stage is the sole
  writer of `webui/data/assets/gameplay_refs.json`.
- `scripts/webui/audio/build_audio_semantics.py` is the Audio orchestrator/publisher;
  reusable Audio evidence owners live under `scripts/webui/audio/semantics/`.
- `scripts/webui/story/lua_consumer_references.py` owns the canonical
  fingerprinted Lua consumer index that Mission Pipeline reads directly.
  Refreshing it requires an explicit complete plaintext-Lua extraction, because
  standard extraction omits Lua.
- `scripts/game_data/contracts/` holds every reviewed contract JSON, and the
  `scripts/game_data/*_native.py` loaders gate the current-build native facts
  builders consume. Recovery hooks must reference or validate those contracts
  rather than duplicate them.
- A production builder must not import or execute a `scripts/webui/story_recovery/`
  module. Recovery tools may import stable builder primitives, not the reverse.
- Native carrier audits go through the single
  `scripts/webui/story_recovery/audit_native_carriers.py` profile CLI; reusable
  scanner/profile code and versioned negative boundaries live in
  `scripts/webui/story_recovery/native_carriers/`.
- `scripts/webui/story_recovery/download_bilibili_video.py` is optional intake for the OCR/audio
  story-order workflow. It needs `requests`, `ffmpeg`, and browser-exported
  cookies, and is outside the stdlib-only export path.
- `scripts/game_data/memorypack/` holds the maintained stdlib-only MemoryPack
  codecs.
- The retired Data, Factory, World, and Presentation page builders remain
  removed. Do not restore those pages or their generated outputs, and do not
  recreate an archived-script bucket: disposable scripts go to `scratch/` or
  `tmp/`, and only maintained workflow code is promoted.

## Recovery Progress Reports

When the user asks how far recovery has progressed or how long completion may
take, keep the answer short and use this structure:

1. Lead with the current position and distinguish structural coverage, complete
   named schemas, runtime-consumer understanding, and reconstruction parity.
2. Give a small evidence-level table using current generated-report counts;
   never copy changing counts into tracked prose.
3. Name the few families or systems that concentrate the remaining work, and
   explain that file count is not the same as engineering complexity because
   one shared schema can close many files.
4. Give separate time ranges for the next bounded milestone, broad installed-
   data understanding, and behavioral or visual parity. Label them as estimates
   and state the main dependency, such as a native join or targeted capture.
5. End with the highest-value next steps. Do not describe partial framing as a
   complete schema or a stored value as an effective runtime value.
